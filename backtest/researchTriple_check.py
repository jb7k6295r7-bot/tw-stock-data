# -*- coding: utf-8 -*-
"""找下一個大漲股 3 年 3 倍命中率 seq1 正式跑【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 main/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple_check [--dry0]

K1 登錄 seq1、seq2 sha 獨立重算 ＋ 裁定 seq449、450、451 信在。
K2 頻率表重建：~/trpwork/rebuild 與已 commit 的 resultsTriple/freq 逐檔逐字再比一次（rebuild.json 之外另算）。
K3 結果變數另路重算：S1 抽 400 事件、V 季判與月判全部事件，事件與每檔對照的 H3、2 倍、仍 3 倍、腰斬、R3（pandas 另寫：壞根截斷、下市末根）逐值相同；
   乾跑 ⇒ 驗全為 0。
K4 格表：cells.csv 由 events_R 自算（n、n_eff、命中率、差、se 自寫月分群公式、CI95、倍數）相同。
K5 V 月判事件另路全量重算（判日 ＝ 每月最後交易日、目標季 ＝ 法定期限 ＜ J、上傳時戳直接讀、fs_xbrl 直接讀、近 4 季 YTD 加減、距一年低點、自寫排名、
   J 過閘、36 月去重）⇒（代號, J）集合與 events_Vm 相同；配到事件的對照逐檔驗條件、候選數相同。
K6 全母體同月命中率：S1 抽 15 個 e、V 月判抽 5 個 e 另路重算相同（乾跑 ⇒ 0）。
K7 召回率分子：S1 無閘、V 季判過閘 另路重算相同。
K8 策略鎖相符（25 支）；git 工作樹相對正式跑前只多本件新檔與結果夾。
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
from backtest import researchTriple as TM                   # noqa: E402
from backtest import researchTriple_freq as TP              # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SM             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []
KEYS = ["H3", "H2_500", "仍3倍", "腰斬", "R3"]


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def eqf(a, b, tol=1e-9):
    a = float(a) if a not in ("", None) else np.nan; b = float(b) if b not in ("", None) else np.nan
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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry0", action="store_true"); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    out = os.path.join(TP.TW, "dry0") if a.dry0 else TM.OUT
    CK = {}
    dirs = [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*")))
    allmd = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md"))]
    k1 = {}
    for s in (TP.REG_SHA, TM.REG2_SHA):
        fs = [f for f in allmd if f"sha{s}" in os.path.basename(f)]
        k1[s] = bool(fs) and all(sha_of(f) == s for f in fs)
    k1["裁定"] = {q: [os.path.basename(f) for f in allmd if q in os.path.basename(f) and "裁定線-" in os.path.basename(f)] for q in ("seq449", "seq450", "seq451")}
    CK["K1"] = k1; log(f"[K1] {k1}")
    ok1 = k1[TP.REG_SHA] and k1[TM.REG2_SHA] and all(k1["裁定"].values())
    # ── K2
    k2 = {}
    for f in TM.FILES:
        x = pd.read_csv(os.path.join(TM.REB, f), dtype=str, keep_default_na=False); y = pd.read_csv(os.path.join(TP.OUT, f), dtype=str, keep_default_na=False)
        k2[f] = bool(x.shape == y.shape and list(x.columns) == list(y.columns) and (x.values == y.values).all())
    CK["K2_重建逐字"] = k2; log(f"[K2] {k2}")
    MJ = json.load(open(os.path.join(out, "main.json"), encoding="utf-8")); sha = MJ["origin/main"]
    sha_, DN, MD = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL, ix, SIDS = PX["CAL"], PX["ix"], PX["SIDS"]; CEND = len(CAL) - 1
    C, BAD, LASTV = PX["C"], PX["BAD"], PX["LASTV"]
    O, _ = SM.seam_open(PX)
    G = PX["G"]; VALID = np.isfinite(C)

    def oc2(i, e):
        P0 = O[i, e]
        if not (np.isfinite(P0) and P0 > 0):
            return None
        rr = {}
        for H in (500, 750):
            end = e + H
            b = np.nonzero(BAD[i, e + 1:end + 1])[0]
            if b.size:
                end = e + b[0]
            if LASTV[i] < end and CEND - LASTV[i] >= 5:
                end = int(LASTV[i])
            s = pd.Series(C[i, e:end + 1]).dropna()
            if s.empty:
                return None
            rr[H] = (s.max(), s.min(), s.iloc[-1])
        return {"H3": float(rr[750][0] >= 3 * P0), "H2_500": float(rr[500][0] >= 2 * P0), "仍3倍": float(rr[750][2] >= 3 * P0),
                "腰斬": float(rr[750][1] <= 0.5 * P0), "R3": rr[750][2] / P0 - 1 - TM.COST}
    # ── K3
    k3 = {"列": 0, "不同": 0, "例": []}
    srcs = {"S1": ("events_R_S1.csv.gz", "events_S1.csv.gz", TP.OUT), "V季判": ("events_R_Vq.csv.gz", "events_V.csv.gz", TP.OUT), "V月判": ("events_R_Vm.csv.gz", "events_Vm.csv.gz", out)}
    RS = {}
    for sig, (fr, fe, d0) in srcs.items():
        R = pd.read_csv(os.path.join(out, fr), dtype={"sid": str}, keep_default_na=False)
        RS[sig] = R
        E = pd.read_csv(os.path.join(d0, fe), dtype={"sid": str}, keep_default_na=False)
        E = E[E["主格"].astype(str) == "True"]
        ctl = dict(zip(zip(E["sid"], E["e"]), E["對照"]))
        if len(R) != len(E):
            k3["不同"] += 1; k3["例"].append(f"{sig} 列數 {len(R)}≠{len(E)}")
        sub = R.sample(min(400, len(R)), random_state=3) if sig == "S1" else R
        for r in sub.to_dict("records"):
            k3["列"] += 1
            i = ix[r["sid"]]; e = int(CAL.searchsorted(pd.Timestamp(r["e"])))
            if a.dry0:
                if any(float(r[f"{k}事件"]) != 0.0 for k in KEYS):
                    k3["不同"] += 1
                continue
            me = oc2(i, e)
            cs = [oc2(ix[s], e) for s in str(ctl[(r["sid"], r["e"])]).split()]
            bad = []
            for k in KEYS:
                if not eqf(me[k] if me else np.nan, r[f"{k}事件"]):
                    bad.append(k)
                v = [c[k] for c in cs if c is not None]
                if not eqf(np.mean(v) if v else np.nan, r[f"{k}對照平均"]):
                    bad.append("對照" + k)
            if bad:
                k3["不同"] += 1
                if len(k3["例"]) < 5:
                    k3["例"].append((sig, r["sid"], r["e"], bad))
    CK["K3_結果另路"] = k3; log(f"[K3] {k3}")
    # ── K4
    CE = pd.read_csv(os.path.join(out, "cells.csv"), encoding="utf-8-sig")
    k4 = []
    mp = {"S1": "S1", "V季判(原登錄)": "V季判", "V月判(seq451)": "V月判"}
    for r in CE.to_dict("records"):
        if r["訊號"] in mp:
            R = RS[mp[r["訊號"]]]
            d = R[R["未看過期間"].astype(str) == "True"] if r["段"].startswith("2005") else R[R["段"] == r["段"]]
        else:
            R = RS["S1"]; d = R[(R["段"] == r["段"]) & (R["同產業同月S1事件數"].astype(int) >= 3)]
        x = pd.to_numeric(d["X"], errors="coerce"); m = d["月"][x.notna()].to_numpy(); x = x.dropna().to_numpy()
        n = len(x); mean = x.mean() if n else np.nan
        se = float(np.sqrt((pd.Series(x - mean).groupby(m).sum() ** 2).sum()) / n) if n else np.nan
        mine = [n, len(set(m)), mean, se, mean - 1.96 * se, mean + 1.96 * se, pd.to_numeric(d["H3事件"]).mean(), pd.to_numeric(d["H3對照平均"]).mean()]
        theirs = [r["主格事件"], r["n_eff"], r["差(點)"], r["se"], r["CI95下"], r["CI95上"], r["命中率_訊號"], r["命中率_對照"]]
        if not all(eqf(p, q) for p, q in zip(mine, theirs)):
            k4.append((r["訊號"], r["段"], mine, theirs))
    CK["K4_格表自算"] = {"不符": k4}; log(f"[K4] {CK['K4_格表自算']}")
    # ── K5 V 月判另路全量
    fd = pd.read_csv(os.path.join(DN, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce").dt.normalize(); fd = fd.dropna(subset=["d"])
    fd["qk"] = fd["year"].astype(int) * 4 + fd["season"].astype(int) - 1
    FDm = fd.groupby(["stock_id", "qk"])["d"].min().to_dict(); FDm.update(fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "qk"])["d"].min().to_dict())
    byS = {}
    for (s, q), d in FDm.items():
        byS.setdefault(s, []).append((d, q))
    X = pd.concat([pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "total_equity", "operating_cash_flow_ytd", "capex_ytd"])
                   for f in sorted(glob.glob(os.path.join(DN, "meta", "fs_xbrl", "fs_xbrl_*.csv")))])
    X = X.assign(_o=(X["report"] != "cr").astype(int)).sort_values(["stock_id", "period", "_o"]).groupby(["stock_id", "period"], as_index=False).first()
    X["qk"] = X["period"].str[:4].astype(int) * 4 + X["period"].str[5].astype(int) - 1
    XD = {(r.stock_id, r.qk): (float(r.operating_cash_flow_ytd), float(r.capex_ytd), float(r.total_equity)) for r in X.itertuples(index=False)}

    def ttm2(s, k, j):
        need = range(k - 3, k + 1) if k % 4 == 3 else range(k - 4, k + 1)
        vals = {q: XD.get((s, q), (np.nan,) * 3)[j] for q in need}
        if not all(np.isfinite(v) for v in vals.values()):
            return np.nan
        return vals[k] if k % 4 == 3 else vals[k] + vals[k - (k % 4) - 1] - vals[k - 4]

    def low2(i, p1):
        if not np.isfinite(C[i, p1]):
            return np.nan
        p0 = int(np.searchsorted(CAL.values, np.datetime64(CAL[p1] - pd.DateOffset(years=1)), "left"))
        prior = np.flatnonzero(np.isfinite(C[i, :p0 + 1]))
        if not len(prior) or prior[-1] >= p1 or BAD[i, prior[-1] + 1:p1 + 1].any():
            return np.nan
        return C[i, p1] / np.nanmin(C[i, p0:p1 + 1]) - 1

    def dl(y, q):
        return pd.Timestamp(*{1: (y, 5, 15), 2: (y, 8, 14), 3: (y, 11, 14), 4: (y + 1, 3, 31)}[q])
    me_ = pd.Series(np.arange(len(CAL)), index=CAL).groupby([CAL.year, CAL.month]).max()
    vst = []; vj = {}
    for (y, m), J in me_.items():
        if (y, m) < (2013, 5) or (y, m) > (2026, 8) or J + 1 > CEND:
            continue
        J = int(J); dJ = CAL[J]
        tq = max(yy * 4 + q - 1 for yy in range(2012, 2027) for q in range(1, 5) if dl(yy, q) < dJ and (yy, q) <= (2026, 2))
        U0 = np.flatnonzero(VALID[:, J]); gm = G[U0, J]
        cf = np.full(len(U0), np.nan); bm = cf.copy(); mc = cf.copy(); lw = cf.copy()
        for k_, i in enumerate(U0):
            s = SIDS[i]; m_ = PX["MC"][i, J]
            if np.isfinite(m_) and m_ > 0:
                mc[k_] = m_
            lw[k_] = low2(int(i), J)
            ql = [qq for d, qq in byS.get(s, []) if d < dJ]
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
            vj[(int(i), J)] = (bool(jd), v, int(math.ceil(pm[k_] * 10)) if np.isfinite(pm[k_]) else -1)
            if v:
                vst.append((SIDS[i], J))
    keep = []; last = {}
    for s, J in sorted(vst):
        mm = CAL[J].year * 12 + CAL[J].month - 1
        if s in last and mm - last[s] < 36:
            continue
        last[s] = mm; keep.append((s, str(CAL[J].date())))
    E3 = pd.read_csv(os.path.join(out, "events_Vm.csv.gz"), dtype={"sid": str}, keep_default_na=False)
    mine = set(keep); theirs = set(zip(E3["sid"], E3["J"]))
    k5 = {"自算": len(mine), "events": len(theirs), "只在自算": len(mine - theirs), "只在events": len(theirs - mine), "對照檔": 0, "對照不符": 0, "候選數不符": 0}
    byA = {}
    for (i, J), (jd, v, dd) in vj.items():
        if jd and not v:
            byA.setdefault((J, dd), []).append(i)
    for r in E3[E3["配到"].astype(str) == "True"].to_dict("records"):
        J = int(CAL.searchsorted(pd.Timestamp(r["J"]))); d0 = vj[(ix[r["sid"]], J)][2]
        cands = [SIDS[i] for i in byA.get((J, d0), []) if IMF.entry_flag(PX, i, J, J + 1) == "保留"]
        if len(cands) != int(r["候選數"]) or d0 != int(r["市值十分位"]):
            k5["候選數不符"] += 1
        for s in str(r["對照"]).split():
            k5["對照檔"] += 1
            if s not in cands:
                k5["對照不符"] += 1
    CK["K5_V月判另路"] = k5; log(f"[K5] {k5}")
    # ── K6 全母體同月
    k6 = {"抽e": 0, "不同": 0}
    for sig, n, p1off in (("S1", 15, 2), ("V月判", 5, 1)):
        R = RS[sig]
        es = sorted(set(R["e"]))
        rng = np.random.default_rng(9)
        for ee in rng.choice(es, min(n, len(es)), replace=False):
            ee = str(ee)
            e =int(CAL.searchsorted(pd.Timestamp(ee))); p1 = e - p1off
            hs = []
            for j in np.flatnonzero(G[:, p1]):
                if IMF.entry_flag(PX, int(j), e - 1, e) != "保留":
                    continue
                if a.dry0:
                    hs.append(0.0); continue
                c = oc2(int(j), e); hs.append(c["H3"] if c else np.nan)
            v = np.nanmean(hs) if len(hs) else np.nan
            th = R.loc[R["e"] == ee, "H3全母體同月"].astype(float).iloc[0]
            k6["抽e"] += 1
            if not eqf(v, th):
                k6["不同"] += 1
    CK["K6_全母體同月"] = k6; log(f"[K6] {k6}")
    # ── K7 召回分子
    RC = pd.read_csv(os.path.join(out, "recall.csv"), encoding="utf-8-sig")
    Zc = pickle.load(open(os.path.join(RT.WORK, f"rv_{TP.RV_TAG}_s{RT.SHIFT_Y}.pkl"), "rb")); RV = Zc["RV"]
    s1 = RV[(RV["accel"] >= 0.05) & (RV["hi24"] == 1.0) & ~(RV["hi24_prev"] == 1.0)]
    jud = RV[np.isfinite(RV["accel"]) & np.isfinite(RV["hi24"])]

    def adate(P):
        y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        k = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10)), "right"))
        return CAL[k] if k <= CEND else None
    pm_ = {p: adate(p) for p in RV["period"].unique()}
    d1 = {}; dj = {}
    for s, p in zip(s1["sid"], s1["period"]):
        if pm_[p] is not None:
            d1.setdefault(s, []).append(pm_[p])
    for s, p in zip(jud["sid"], jud["period"]):
        if pm_[p] is not None:
            dj.setdefault(s, []).append(pm_[p])
    X3 = pd.read_csv(TP.X3_CSV, dtype={"代號": str}, usecols=["代號", "起點"])
    den = 0; num = 0
    for s, st in zip(X3["代號"], pd.to_datetime(X3["起點"])):
        lo = st - pd.DateOffset(months=12)
        if any(lo <= x <= st for x in dj.get(s, [])):
            den += 1
            if any(lo <= x <= st for x in d1.get(s, [])):
                num += 1
    r0 = RC[(RC["3倍段範圍"] == "全部") & (RC["訊號"] == "S1") & (RC["閘"] == "無閘")].iloc[0]
    k7 = {"S1無閘 自算": [num if not a.dry0 else 0, den], "檔": [int(r0["分子(窗內出現)"]), int(r0["分母(可判段)"])]}
    k7["相同"] = k7["S1無閘 自算"] == k7["檔"]
    CK["K7_召回"] = k7; log(f"[K7] {k7}")
    # ── K8
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(TP.TW, "git_before_main.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    CK["K8"] = {"策略鎖": lock, "git 新增（相對正式跑前）": extra,
                "git 只多本件": all(any(w in x for w in ("researchTriple.py", "researchTriple_check.py", "resultsTriple/main", "resultsTriple/")) for x in extra)}
    ok = (ok1 and all(k2.values()) and k3["不同"] == 0 and not k4 and k5["只在自算"] == 0 and k5["只在events"] == 0 and k5["對照不符"] == 0
          and k5["候選數不符"] == 0 and k6["不同"] == 0 and k7["相同"] and "相符" in "".join(lock) and CK["K8"]["git 只多本件"])
    CK["全過"] = bool(ok)
    log(f"[K8] {CK['K8']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
