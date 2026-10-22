# -*- coding: utf-8 -*-
"""找下一個大漲股 3 年 3 倍命中率 seq1 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple_freq_check [--dry]

C1 登錄 sha 獨立重算（信箱根目錄＋_封存-*，去 pw1 行 sha256 前 16 碼）＋ 裁定 seq449 信在。
C2 甲、乙：直接讀月營收檔自算（年增 ＝ 當月 ÷ 去年當月 − 1、近 3／12 月平均、24 月新高）抽 400 列對 accel、hi24（＝ 營收轉強驗證 K2b 同式）。
C3 可用日：S1 自算「次月 10 日（2026-01 起 15 日）之後第一個交易日」、V 自算「法定期限（5/15、8/14、11/14、次年 3/31）之後第一個交易日」⇒ events 的 A、e 逐列相同。
C4 S1 事件：由月營收快取自算 accel ≥ 0.05 ∧ hi24 ∧ ¬hi24_prev ∧ 面板 ∧ G[A−1] ∧ 36 月去重 ⇒（代號, 期別）集合與 events_S1 完全相同。
C5 V 事件：另一條路全量重算 —— filing_dates.csv 直接讀（AI1 優先最早）、fs_xbrl 直接讀（cr 優先）、近 4 季用「YTD(k) ＋ YTD(去年Q4) − YTD(k−4)」
   （Q4 ＝ YTD）、距一年低點用 BAD 陣列直接判壞根、分位自寫 average rank ⇒ 每判日 V 狀態 ⇒ 36 月去重 ⇒（代號, A）集合與 events_V 完全相同。
C6 配對：S1 抽 300 個配到事件、V 全部配到事件，對照每一檔自驗條件、候選數自算相同。
C7 freq_段.csv 主要欄由 events 自算相同；召回率分母「S1可判(無閘)」「V可判(過閘)」自算相同。
C8 輸出無報酬類欄；策略鎖 25 支相符；git 工作樹相對開跑前只多本件新檔與結果夾。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTriple_freq as TP              # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import bigrun_monthly as BM                   # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def eqf(a, b, tol=1e-12):
    fa, fb = np.isfinite(a), np.isfinite(b)
    return bool(fa == fb and (not fa or abs(a - b) <= tol * max(1.0, abs(a))))


def ranks_of(vals):
    v = np.asarray(vals, float); ok = np.isfinite(v); out_ = np.full(len(v), np.nan)
    vv = v[ok]
    if not len(vv):
        return out_
    s = np.sort(vv)
    lo = np.searchsorted(s, vv, "left"); hi = np.searchsorted(s, vv, "right")
    out_[ok] = (lo + (hi - lo + 1) / 2.0) / len(vv)
    return out_


def first_after(CAL, d):
    return int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(d)), "right"))


def rev_A(CAL, P):
    y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return first_after(CAL, pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10))


def dl(y, q):
    return {1: (y, 5, 15), 2: (y, 8, 14), 3: (y, 11, 14), 4: (y + 1, 3, 31)}[q]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    out = os.path.join(TP.TW, "dry") if a.dry else TP.OUT
    CK = {}
    # ── C1
    dirs = [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*")))
    fs = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md")) if f"sha{TP.REG_SHA}" in os.path.basename(f)]
    rul = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md")) if "seq449" in os.path.basename(f)]
    CK["C1_登錄sha"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == TP.REG_SHA for f in fs), "裁定seq449": [os.path.basename(f) for f in rul]}
    log(f"[C1] {CK['C1_登錄sha']}")
    if not CK["C1_登錄sha"]["相符"] or not rul:
        raise SystemExit("⛔ C1")
    J = json.load(open(os.path.join(out, "freq.json"), encoding="utf-8")); sha = J["origin/main"]
    sha_, DN, MD = RT.ensure_data(sha)
    tag = TP.RV_TAG if not a.dry else f"dry{J['乾跑股數']}"
    Z = pickle.load(open(os.path.join(RT.WORK, f"rv_{tag}_s{RT.SHIFT_Y}.pkl"), "rb")); RV = Z["RV"]; codes = Z["codes"]
    # ── C2 直接讀檔自算
    fr = []
    for f in sorted(glob.glob(os.path.join(MD, "revenue_hist", "*.csv"))):
        fr.append(pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"]))
    H = pd.concat(fr).drop_duplicates(["stock_id", "period"], keep="last")
    for f in sorted(glob.glob(os.path.join(MD, "revenue", "*.csv"))):
        b = os.path.basename(f)[:-4]
        if len(b) != 7 or b[4] != "-" or not (b[:4] + b[5:]).isdigit():
            continue
        x = pd.read_csv(f, dtype=str)
        x = x[x["資料年月"].astype(str).str.strip() == BM.roc(b)]
        if "period" in x.columns:
            x = x[x["period"].astype(str) == b]
        y = pd.DataFrame({"stock_id": x["stock_id"], "period": b, "當月營收": x["營業收入-當月營收"], "去年當月營收": x["營業收入-去年當月營收"]})
        H = pd.concat([H[~H.set_index(["stock_id", "period"]).index.isin(y.set_index(["stock_id", "period"]).index)], y])
    H["r"] = pd.to_numeric(H["當月營收"], errors="coerce"); H["ly"] = pd.to_numeric(H["去年當月營收"], errors="coerce")
    Hd = {s: g.set_index("period")[["r", "ly"]] for s, g in H[H["stock_id"].isin(set(codes))].groupby("stock_id")}
    sub = RV.sample(min(400, len(RV)), random_state=13)

    def shift_m(p, k):
        m = int(p[:4]) * 12 + int(p[5:7]) - 1 + k
        return f"{m // 12:04d}-{m % 12 + 1:02d}"
    b2 = 0
    for sid, P, ac, h24 in zip(sub["sid"], sub["period"], sub["accel"], sub["hi24"]):
        g = Hd.get(sid)
        ps = [shift_m(P, -k) for k in range(0, 25)]
        r = np.array([g["r"].get(p, np.nan) if g is not None else np.nan for p in ps], float)
        ly = np.array([g["ly"].get(p, np.nan) if g is not None else np.nan for p in ps], float)
        yy = np.where(ly > 0, r / np.where(ly > 0, ly, 1) - 1, np.nan)
        acc = (yy[:3].mean() - yy[:12].mean()) if (np.isfinite(yy[:3]).all() and np.isfinite(yy[:12]).all()) else np.nan
        hist = r[1:25]
        hh = (float(r[0] >= hist.max()) if (np.isfinite(hist).all() and np.isfinite(r[0])) else np.nan)
        if not (eqf(acc, ac, 1e-9) and eqf(hh, h24)):
            b2 += 1
    CK["C2_甲乙直接讀檔"] = {"抽列": len(sub), "不同": b2}
    log(f"[C2] {CK['C2_甲乙直接讀檔']}")
    # ── 價格
    PX = RT.prices(sha, DN, a.procs)
    CAL = PX["CAL"]; ix = PX["ix"]; SIDS = PX["SIDS"]; CEND = len(CAL) - 1
    SUB = np.array([s in set(codes) for s in SIDS])
    G = PX["G"] & SUB[:, None]; VALID = np.isfinite(PX["C"]) & SUB[:, None]
    E1 = pd.read_csv(os.path.join(out, "events_S1.csv.gz"), dtype={"sid": str, "期別": str})
    E2 = pd.read_csv(os.path.join(out, "events_V.csv.gz"), dtype={"sid": str})
    # ── C3
    b3 = 0
    for P, A_, e_ in zip(E1["期別"], E1["A"], E1["e"]):
        k = rev_A(CAL, P)
        if str(CAL[k].date()) != A_ or (k + 1 <= CEND and str(CAL[k + 1].date()) != e_):
            b3 += 1
    b3v = 0
    for qs, A_, e_ in zip(E2["財報季(目標)"], E2["A"], E2["e"]):
        k = first_after(CAL, pd.Timestamp(*dl(int(qs[:4]), int(qs[5]))))
        if str(CAL[k].date()) != A_ or (k + 1 <= CEND and str(CAL[k + 1].date()) != e_):
            b3v += 1
    CK["C3_可用日"] = {"S1列": len(E1), "S1不同": b3, "V列": len(E2), "V不同": b3v}
    log(f"[C3] {CK['C3_可用日']}")
    # ── C4 S1 事件集合
    s1 = RV[(RV["accel"] >= 0.05) & (RV["hi24"] == 1.0) & ~(RV["hi24_prev"] == 1.0)].sort_values(["sid", "period"])
    keep = []; lastk = {}
    for sid, P in zip(s1["sid"], s1["period"]):
        i = ix.get(sid, -1)
        if i < 0:
            continue
        k = rev_A(CAL, P)
        if k > CEND or k < 1 or not G[i, k - 1]:
            continue
        mm = int(P[:4]) * 12 + int(P[5:7])
        if sid in lastk and mm - lastk[sid] < 36:
            continue
        lastk[sid] = mm; keep.append((sid, P))
    mine = set(keep); theirs = set(zip(E1["sid"], E1["期別"]))
    CK["C4_S1事件集合"] = {"自算": len(mine), "events": len(theirs), "只在自算": len(mine - theirs), "只在events": len(theirs - mine)}
    log(f"[C4] {CK['C4_S1事件集合']}")
    # ── C5 V 全量另路重算
    fd = pd.read_csv(os.path.join(DN, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce").dt.normalize()
    fd = fd.dropna(subset=["d"])
    fd["qk"] = fd["year"].astype(int) * 4 + fd["season"].astype(int) - 1
    ai = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "qk"])["d"].min()
    an = fd.groupby(["stock_id", "qk"])["d"].min()
    FDm = an.to_dict(); FDm.update(ai.to_dict())
    byS = {}
    for (s, q), d in FDm.items():
        byS.setdefault(s, []).append((d, q))
    xs = []
    for f in sorted(glob.glob(os.path.join(DN, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        xs.append(pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "total_equity", "operating_cash_flow_ytd", "capex_ytd"]))
    X = pd.concat(xs)
    X = X.assign(_o=(X["report"] != "cr").astype(int)).sort_values(["stock_id", "period", "_o"]).groupby(["stock_id", "period"], as_index=False).first()
    X["qk"] = X["period"].str[:4].astype(int) * 4 + X["period"].str[5].astype(int) - 1
    XD = {}
    for r in X.itertuples(index=False):
        XD[(r.stock_id, r.qk)] = (float(r.operating_cash_flow_ytd), float(r.capex_ytd), float(r.total_equity))

    def ttm2(s, k, j):
        need = range(k - 3, k + 1) if k % 4 == 3 else range(k - 4, k + 1)
        vals = {q: XD.get((s, q), (np.nan,) * 3)[j] for q in need}
        if not all(np.isfinite(v) for v in vals.values()):
            return np.nan
        if k % 4 == 3:
            return vals[k]
        return vals[k] + vals[k - (k % 4) - 1] - vals[k - 4]
    C = PX["C"]; BAD = PX["BAD"]; MC = PX["MC"]

    def low2(i, p1):
        if not np.isfinite(C[i, p1]):
            return np.nan
        d0 = CAL[p1] - pd.DateOffset(years=1)
        p0 = int(np.searchsorted(CAL.values, np.datetime64(d0), "left"))
        prior = np.flatnonzero(np.isfinite(C[i, :p0 + 1]))
        if not len(prior) or prior[-1] >= p1:
            return np.nan
        a0 = int(prior[-1])
        if BAD[i, a0 + 1:p1 + 1].any():
            return np.nan
        w = C[i, p0:p1 + 1]
        return C[i, p1] / np.nanmin(w) - 1
    vstate = []
    vjud = {}
    for y in range(2013, 2027):
        for q in range(1, 5):
            if (y, q) > (2026, 2):
                continue
            A_ = first_after(CAL, pd.Timestamp(*dl(y, q)))
            if not (1 <= A_ <= CEND):
                continue
            tq = y * 4 + q - 1; p1 = A_ - 1
            U0 = np.flatnonzero(VALID[:, p1]); gm = G[U0, p1]
            cf = np.full(len(U0), np.nan); bm = np.full(len(U0), np.nan); mc = np.full(len(U0), np.nan); lw = np.full(len(U0), np.nan)
            for k_, i in enumerate(U0):
                s = SIDS[i]
                m_ = MC[i, p1]
                if np.isfinite(m_) and m_ > 0:
                    mc[k_] = m_
                lw[k_] = low2(int(i), p1)
                ql = [qq for d, qq in byS.get(s, []) if d < CAL[A_]]
                if not ql:
                    continue
                kq = max(ql)
                if tq - kq >= 2 or (s, kq) not in XD:
                    continue
                o = ttm2(s, kq, 0); c_ = ttm2(s, kq, 1); eq = XD[(s, kq)][2]
                if np.isfinite(o) and np.isfinite(mc[k_]):
                    cf[k_] = ((o + c_) if np.isfinite(c_) else o) / mc[k_]
                if np.isfinite(eq) and np.isfinite(mc[k_]):
                    bm[k_] = eq / mc[k_]
            pc = ranks_of(np.where(gm, cf, np.nan)); pb = ranks_of(np.where(gm, bm, np.nan)); pm = ranks_of(np.where(gm, mc, np.nan))
            for k_, i in enumerate(U0):
                if not gm[k_]:
                    continue
                jd = np.isfinite(pc[k_]) and np.isfinite(pb[k_]) and np.isfinite(pm[k_]) and np.isfinite(lw[k_])
                v = bool(jd and pc[k_] > 0.7 and pb[k_] > 0.7 and pm[k_] <= 0.5 and lw[k_] <= 0.20)
                vjud[(int(i), A_)] = (bool(jd), v, int(math.ceil(pm[k_] * 10)) if np.isfinite(pm[k_]) else -1)
                if v:
                    vstate.append((SIDS[i], A_))
    keep = []; lastk = {}
    for s, A_ in sorted(vstate):
        mm = CAL[A_].year * 12 + CAL[A_].month - 1
        if s in lastk and mm - lastk[s] < 36:
            continue
        lastk[s] = mm; keep.append((s, str(CAL[A_].date())))
    mine = set(keep); theirs = set(zip(E2["sid"], E2["A"]))
    CK["C5_V事件集合(另路全量)"] = {"V狀態(過閘)": len(vstate), "自算事件": len(mine), "events": len(theirs), "只在自算": len(mine - theirs), "只在events": len(theirs - mine),
                                "例_只在自算": sorted(mine - theirs)[:5], "例_只在events": sorted(theirs - mine)[:5]}
    log(f"[C5] {CK['C5_V事件集合(另路全量)']}")
    # ── C6 配對
    pit = IMF.load_pit(DN)
    RVi = RV.set_index(["sid", "period"])

    def r12(i, p1):
        vp = PX["VP"][i]
        if not np.isfinite(C[i, p1]):
            return np.nan
        p0 = int(np.searchsorted(CAL.values, np.datetime64(CAL[p1] - pd.DateOffset(months=12)), "right")) - 1
        cand_ = vp[vp <= p0]
        if p0 < 0 or not len(cand_):
            return np.nan
        a0 = int(cand_[-1])
        if PX["CB"][i, p1] - PX["CB"][i, a0] > 0:
            return np.nan
        return C[i, p1] / C[i, a0] - 1
    s1set = set(zip(RV.loc[(RV["accel"] >= 0.05) & (RV["hi24"] == 1.0) & ~(RV["hi24_prev"] == 1.0), "sid"],
                    RV.loc[(RV["accel"] >= 0.05) & (RV["hi24"] == 1.0) & ~(RV["hi24_prev"] == 1.0), "period"]))
    M = E1[E1["配到"] == True]  # noqa: E712
    M = M.sample(min(300, len(M)), random_state=5)
    b6 = {"S1抽驗事件": len(M), "S1對照檔": 0, "S1對照不符": 0, "S1候選數不符": 0}
    memo = {}
    for _, r in M.iterrows():
        P = r["期別"]; A_ = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["A"])))); p1 = A_ - 1
        if P not in memo:
            U = np.flatnonzero(G[:, p1])
            mcv = MC[U, p1]; mcv = np.where(np.isfinite(mcv) & (mcv > 0), mcv, np.nan)
            rr = np.array([r12(int(i), p1) for i in U])
            pm_, pr_ = ranks_of(mcv), ranks_of(rr)
            memo[P] = ({int(i): (int(math.ceil(x * 10)) if np.isfinite(x) else -1) for i, x in zip(U, pm_)},
                       {int(i): (int(math.ceil(x * 3)) if np.isfinite(x) else -1) for i, x in zip(U, pr_)})
        dec, ter = memo[P]
        i0 = ix[r["sid"]]
        if dec.get(i0) != int(r["市值十分位"]) or ter.get(i0) != int(r["前12月三分位(配對特徵)"]):
            b6["S1對照不符"] += 1; continue
        ind = pit.at(r["sid"], CAL[A_])[0] or ""
        nc = 0
        for s in RV.loc[RV["period"] == P, "sid"]:
            if (s, P) in s1set:
                continue
            j = ix.get(s, -1)
            if j < 0 or not G[j, p1] or dec.get(j, -1) < 0 or ter.get(j, -1) < 0 or dec[j] != dec[i0] or ter[j] != ter[i0]:
                continue
            if (pit.at(s, CAL[A_])[0] or "") != ind or IMF.entry_flag(PX, j, A_, A_ + 1) != "保留":
                continue
            nc += 1
        if nc != int(r["候選數"]):
            b6["S1候選數不符"] += 1
        for s in str(r["對照"]).split():
            b6["S1對照檔"] += 1
            j = ix[s]
            ok = ((s, P) not in s1set) and (s, P) in RVi.index and G[j, p1] and dec.get(j) == dec[i0] and ter.get(j) == ter[i0] \
                and (pit.at(s, CAL[A_])[0] or "") == ind and IMF.entry_flag(PX, j, A_, A_ + 1) == "保留"
            if not ok:
                b6["S1對照不符"] += 1
    MV = E2[E2["配到"] == True]  # noqa: E712
    b6.update({"V事件": len(MV), "V對照檔": 0, "V對照不符": 0, "V候選數不符": 0})
    byA = {}
    for (i, AA), (jd, v, dd) in vjud.items():
        if jd and not v:
            byA.setdefault((AA, dd), []).append(i)
    cmemo = {}
    for _, r in MV.iterrows():
        A_ = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["A"])))); i0 = ix[r["sid"]]
        d0 = vjud.get((i0, A_), (False, False, -1))[2]
        if d0 != int(r["市值十分位"]):
            b6["V對照不符"] += 1; continue
        if (A_, d0) not in cmemo:
            cmemo[(A_, d0)] = [SIDS[i] for i in byA.get((A_, d0), []) if IMF.entry_flag(PX, i, A_, A_ + 1) == "保留"]
        cands = cmemo[(A_, d0)]
        if len(cands) != int(r["候選數"]):
            b6["V候選數不符"] += 1
        for s in str(r["對照"]).split():
            b6["V對照檔"] += 1
            if s not in cands:
                b6["V對照不符"] += 1
    CK["C6_配對"] = b6
    log(f"[C6] {b6}")
    # ── C7 段表、召回率分母
    FR = pd.read_csv(os.path.join(out, "freq_段.csv"), encoding="utf-8-sig")
    k7 = []
    for _, r in FR.iterrows():
        Ex = E1 if r["訊號"] == "S1" else E2
        d = Ex[Ex["未看過期間"] == True] if (r["訊號"] == "S1" and r["段"].startswith("2005")) else Ex[Ex["段"] == r["段"]]  # noqa: E712
        m = d[(d["配到"] == True) & (d["H750走得完"] == True)]  # noqa: E712
        mine_ = [len(d), int((d["進場"] == "保留").sum()), int((d["配到"] == True).sum()), len(m), int(m["月"].nunique())]  # noqa: E712
        theirs_ = [r["事件(過閘去重)"], r["e可進場"], r["配到"], r["主格事件"], r["主格月數=n_eff"]]
        if [int(x) for x in mine_] != [int(x) for x in theirs_]:
            k7.append((r["訊號"], r["段"], mine_, theirs_))
    RD = pd.read_csv(os.path.join(out, "recall_denom.csv"), encoding="utf-8-sig")
    X3 = pd.read_csv(TP.X3_CSV, dtype={"代號": str}, usecols=["代號", "起點"])
    X3 = X3[X3["代號"].isin(set(codes))]
    RVa = RV.assign(A=[rev_A(CAL, p) for p in RV["period"]])
    RVa = RVa[(RVa["A"] >= 1) & (RVa["A"] <= CEND)]
    RVa = RVa[np.isfinite(RVa["accel"]) & np.isfinite(RVa["hi24"])]
    RVa["d"] = CAL[RVa["A"].to_numpy()]
    byd = {s: g["d"].to_numpy() for s, g in RVa.groupby("sid")}
    vj = {}
    for (i, AA), (jd, v, dd) in vjud.items():
        if jd:
            vj.setdefault(SIDS[i], []).append(CAL[AA])
    n_s1 = 0; n_v = 0
    for s, st in zip(X3["代號"], pd.to_datetime(X3["起點"])):
        lo = st - pd.DateOffset(months=12)
        dd = byd.get(s)
        if dd is not None and ((dd >= np.datetime64(lo)) & (dd <= np.datetime64(st))).any():
            n_s1 += 1
        if any(lo <= x <= st for x in vj.get(s, [])):
            n_v += 1
    r0 = RD[RD["3倍段範圍"] == "全部"].iloc[0]
    k7b = {"S1可判(無閘)": [n_s1, int(r0["S1可判(無閘)"])], "V可判(過閘)": [n_v, int(r0["V可判(過閘)"])], "段數": [len(X3), int(r0["段數"])]}
    CK["C7_段表與召回分母"] = {"段表不符": k7, "召回分母(自算,檔內)": k7b, "召回分母相同": all(x == y for x, y in k7b.values())}
    log(f"[C7] {CK['C7_段表與召回分母']}")
    # ── C8
    cols = list(E1.columns) + list(E2.columns) + [c for f in glob.glob(os.path.join(out, "*.csv")) for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns]
    badc = [c for c in cols if any(w in c for w in ("報酬", "年化", "回落", "價格", "收盤", "開盤價", "倍數", "命中", "腰斬", "R值", "d值"))]
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(TP.TW, "git_before.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    allowed = ("researchTriple_freq", "resultsTriple")
    CK["C8"] = {"報酬類欄": badc, "策略鎖": lock, "git 新增（相對開跑前）": extra, "git 只多本件": all(any(w in x for w in allowed) for x in extra)}
    ok = (CK["C1_登錄sha"]["相符"] and b2 == 0 and b3 == 0 and b3v == 0 and CK["C4_S1事件集合"]["只在自算"] == 0 and CK["C4_S1事件集合"]["只在events"] == 0
          and CK["C5_V事件集合(另路全量)"]["只在自算"] == 0 and CK["C5_V事件集合(另路全量)"]["只在events"] == 0
          and b6["S1對照不符"] == 0 and b6["S1候選數不符"] == 0 and b6["V對照不符"] == 0 and b6["V候選數不符"] == 0
          and not k7 and CK["C7_段表與召回分母"]["召回分母相同"] and not badc and "相符" in "".join(lock) and CK["C8"]["git 只多本件"])
    CK["全過"] = bool(ok)
    log(f"[C8] {CK['C8']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
