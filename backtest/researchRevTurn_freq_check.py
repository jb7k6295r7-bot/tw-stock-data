# -*- coding: utf-8 -*-
"""營收轉強驗證 seq2 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevTurn_freq_check [--dry]

K1 登錄 sha 獨立重算（信箱根目錄＋_封存-*，去 pw1 行 sha256 前 16 碼）＋ 裁定 seq447 信在。
K2 轉強（bigrun_monthly.rev_metrics）平移 ＋7 年 vs 不平移：抽 2012-07 以後 8 期、全部代號逐值相同（accel、hi24、hi24_prev、up、up_prev、yoy、mom、flag_mom2）；
   另以 pandas 直接讀月營收檔自算（另一條路：年增 ＝ 當月 ÷ 去年當月 − 1、近 3／12 月平均、24 月新高）抽 400 列對 accel、hi24。
K3 可用日：自算「次月 10 日（2026-01 起 15 日）之後第一個交易日」⇒ events 的 A、e（e ＝ A 下一交易日）逐列相同。
K4 事件：由 rv 快取自算 起點 ∧ 面板 ∧ G[A−1] ∧ 12 個月去重 ⇒ （代號, 期別）集合與 events.csv 完全相同。
K5 配對：抽 300 個配到事件，對照每一檔自驗 同期 up 假、同產業、過閘、e 可進場、市值十分位與前 12 月三分位相同（自寫 numpy 排名）；候選數自算相同。
K6 freq_段.csv 主要欄由 events.csv.gz 自算相同；重疊表 ① 自算相同。
K7 輸出無報酬欄；策略鎖 25 支相符；git 工作樹相對開跑前只多本件新檔與結果夾。
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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    out = os.path.join(RT.WORK, "dry_rt") if a.dry else RT.OUT
    CK = {}
    # ── K1
    fs = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{RT.REG_SHA}" in os.path.basename(f)]
    rul = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if "seq447" in os.path.basename(f)]
    CK["K1_登錄sha"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == RT.REG_SHA for f in fs), "裁定seq447": [os.path.basename(f) for f in rul]}
    log(f"[K1] {CK['K1_登錄sha']}")
    if not CK["K1_登錄sha"]["相符"] or not rul:
        raise SystemExit("⛔ K1")
    J = json.load(open(os.path.join(out, "freq.json"), encoding="utf-8")); sha = J["origin/main"]
    sha_, DN, MD = RT.ensure_data(sha)
    tag = "all" if not a.dry else f"dry{J['乾跑股數']}"
    Z = pickle.load(open(os.path.join(RT.WORK, f"rv_{tag}_s{RT.SHIFT_Y}.pkl"), "rb")); RV = Z["RV"]; codes = Z["codes"]
    # ── K2 平移 vs 不平移
    L, _ = BM.load_rev_pit(MD)
    L = L[L["period"].str.fullmatch(r"\d{4}-\d{2}")].copy()
    allp = sorted(L["period"].unique())
    rng = np.random.default_rng(7)
    cand = [p for p in allp if "2012-07" <= p <= allp[-1]]
    samp = sorted(rng.choice(cand, 8, replace=False).tolist())
    bad = 0; n = 0
    keyc = ["accel", "hi24", "hi24_prev", "up", "up_prev", "yoy", "mom", "flag_mom2"]
    RVi = RV.set_index(["sid", "period"])
    for P in samp:
        res, Pr = BM.rev_metrics(L, codes, BM.pub10(P) + pd.Timedelta(days=1), {})
        assert Pr == P
        for sid, r in res.items():
            if r.get("rev_period") != P:
                if (sid, P) in RVi.index:
                    bad += 1
                continue
            n += 1
            if (sid, P) not in RVi.index:
                bad += 1; continue
            q = RVi.loc[(sid, P)]
            mine = [RT._f(r["accel"]), RT._b(r["hi24"]), RT._b(r["hi24_prev"]), float(bool(r["up"])), float(bool(r["up_prev"])), RT._f(r["yoy"]), RT._f(r["mom"]), RT._b(r["flag_mom2"])]
            theirs = [float(q[c]) for c in keyc]
            if not all(eqf(x, y) for x, y in zip(mine, theirs)):
                bad += 1
    CK["K2_平移vs不平移"] = {"期": samp, "比對列": n, "不同": bad}
    log(f"[K2a] {CK['K2_平移vs不平移']}")
    # K2b 直接讀檔自算
    fr = []
    for f in sorted(glob.glob(os.path.join(MD, "revenue_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"]); fr.append(x)
    H = pd.concat(fr).drop_duplicates(["stock_id", "period"], keep="last")
    for f in sorted(glob.glob(os.path.join(MD, "revenue", "*.csv"))):
        b = os.path.basename(f)[:-4]
        if len(b) != 7 or b[4] != "-" or not (b[:4] + b[5:]).isdigit():
            continue                                    # _esb 等不用（同 load_rev_pit）
        x = pd.read_csv(f, dtype=str)
        x = x[x["資料年月"].astype(str).str.strip() == BM.roc(b)]
        if "period" in x.columns:
            x = x[x["period"].astype(str) == b]
        y = pd.DataFrame({"stock_id": x["stock_id"], "period": b, "當月營收": x["營業收入-當月營收"], "去年當月營收": x["營業收入-去年當月營收"]})
        H = pd.concat([H[~H.set_index(["stock_id", "period"]).index.isin(y.set_index(["stock_id", "period"]).index)], y])
    H["r"] = pd.to_numeric(H["當月營收"], errors="coerce"); H["ly"] = pd.to_numeric(H["去年當月營收"], errors="coerce")
    Hd = {s: g.set_index("period")[["r", "ly"]] for s, g in H[H["stock_id"].isin(set(codes))].groupby("stock_id")}
    sub = RV.sample(min(400, len(RV)), random_state=11)

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
        y3 = yy[:3]; y12 = yy[:12]
        acc = (y3.mean() - y12.mean()) if (np.isfinite(y3).all() and np.isfinite(y12).all()) else np.nan
        hist = r[1:25]
        hh = (float(r[0] >= hist.max()) if (np.isfinite(hist).all() and np.isfinite(r[0])) else np.nan)
        if not (eqf(acc, ac, 1e-9) and eqf(hh, h24)):
            b2 += 1
    CK["K2b_直接讀檔自算"] = {"抽列": len(sub), "不同": b2}
    log(f"[K2b] {CK['K2b_直接讀檔自算']}")
    # ── K3 可用日
    EV = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype={"sid": str, "期別": str}, keep_default_na=True)
    PX = RT.prices(sha, DN, a.procs)
    CAL = PX["CAL"]
    b3 = 0
    for P, A_, e_ in zip(EV["期別"], EV["A"], EV["e"]):
        y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10)
        k = int(np.searchsorted(CAL.values, np.datetime64(cut), "right"))
        if str(CAL[k].date()) != A_ or (k + 1 < len(CAL) and str(CAL[k + 1].date()) != e_):
            b3 += 1
    CK["K3_可用日"] = {"列": len(EV), "不同": b3}
    log(f"[K3] {CK['K3_可用日']}")
    # ── K4 事件集合
    ix = PX["ix"]; G = PX["G"]; CEND = len(CAL) - 1
    st = RV[RV["up"] & ~RV["up_prev"]].sort_values(["sid", "period"])
    keep = []; lastk = {}
    for sid, P in zip(st["sid"], st["period"]):
        i = ix.get(sid, -1)
        if i < 0:
            continue
        y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        k = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10)), "right"))
        if k > CEND or k < 1 or not G[i, k - 1]:
            continue
        mm = y * 12 + m
        if sid in lastk and mm - lastk[sid] < RT.DEDUP_M:
            continue
        lastk[sid] = mm; keep.append((sid, P))
    mine = set(keep); theirs = set(zip(EV["sid"], EV["期別"]))
    CK["K4_事件集合"] = {"自算": len(mine), "events": len(theirs), "只在自算": len(mine - theirs), "只在events": len(theirs - mine)}
    log(f"[K4] {CK['K4_事件集合']}")
    # ── K5 配對抽驗
    pit = IMF.load_pit(DN)
    RVi2 = RV.set_index(["sid", "period"])
    MC, C, VP, CB = PX["MC"], PX["C"], PX["VP"], PX["CB"]

    def r12(i, p1):
        vp = VP[i]
        if not np.isfinite(C[i, p1]):
            return np.nan
        d0 = CAL[p1] - pd.DateOffset(months=12)
        p0 = int(np.searchsorted(CAL.values, np.datetime64(d0), "right")) - 1
        cand_ = vp[vp <= p0]
        if p0 < 0 or not len(cand_):
            return np.nan
        a0 = int(cand_[-1])
        if CB[i, p1] - CB[i, a0] > 0:
            return np.nan
        return C[i, p1] / C[i, a0] - 1

    def ranks_of(vals):
        v = np.asarray(vals, float); ok = np.isfinite(v); out_ = np.full(len(v), np.nan)
        vv = v[ok]
        # average rank 自寫：小於數 ＋ (等於數＋1)/2
        s = np.sort(vv)
        lo = np.searchsorted(s, vv, "left"); hi = np.searchsorted(s, vv, "right")
        out_[ok] = (lo + (hi - lo + 1) / 2.0) / len(vv)
        return out_
    M = EV[EV["配到"] == True].sample(min(300, int((EV["配到"] == True).sum())), random_state=5)  # noqa: E712
    b5 = {"對照不符": 0, "候選數不符": 0, "抽驗事件": len(M), "對照檔": 0}
    memo = {}
    for _, r in M.iterrows():
        P = r["期別"]; A_ = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["A"])))); p1 = A_ - 1
        if P not in memo:
            U = np.flatnonzero(G[:, p1])
            mc = MC[U, p1]; mc = np.where(np.isfinite(mc) & (mc > 0), mc, np.nan)
            rr = np.array([r12(int(i), p1) for i in U])
            pm, pr = ranks_of(mc), ranks_of(rr)
            dec = {int(i): (int(math.ceil(x * 10)) if np.isfinite(x) else -1) for i, x in zip(U, pm)}
            ter = {int(i): (int(math.ceil(x * 3)) if np.isfinite(x) else -1) for i, x in zip(U, pr)}
            memo[P] = (dec, ter)
        dec, ter = memo[P]
        i0 = ix[r["sid"]]
        if dec.get(i0) != int(r["市值十分位"]) or ter.get(i0) != int(r["前12月三分位(配對特徵)"]):
            b5["對照不符"] += 1; continue
        ind = pit.at(r["sid"], CAL[A_])[0] or ""
        # 候選數自算
        sub_ = RV[(RV["period"] == P) & (~RV["up"])]
        nc = 0
        for s in sub_["sid"]:
            j = ix.get(s, -1)
            if j < 0 or not G[j, p1]:
                continue
            if dec.get(j) != dec[i0] or ter.get(j) != ter[i0] or dec[j] < 0 or ter[j] < 0:
                continue
            if (pit.at(s, CAL[A_])[0] or "") != ind:
                continue
            if IMF.entry_flag(PX, j, A_, A_ + 1) != "保留":
                continue
            nc += 1
        if nc != int(r["候選數"]):
            b5["候選數不符"] += 1
        for s in str(r["對照"]).split():
            b5["對照檔"] += 1
            j = ix[s]
            ok = (not bool(RVi2.loc[(s, P), "up"])) and G[j, p1] and dec.get(j) == dec[i0] and ter.get(j) == ter[i0] \
                and (pit.at(s, CAL[A_])[0] or "") == ind and IMF.entry_flag(PX, j, A_, A_ + 1) == "保留"
            if not ok:
                b5["對照不符"] += 1
    CK["K5_配對抽驗"] = b5
    log(f"[K5] {b5}")
    # ── K6 段表自算
    FR = pd.read_csv(os.path.join(out, "freq_段.csv"), encoding="utf-8-sig")
    k6 = []
    for _, r in FR.iterrows():
        d = EV[EV["段"] == r["段"]]; m = d[(d["配到"] == True) & (d["H250走得完"] == True)]  # noqa: E712
        mine_ = [len(d), int((d["進場"] == "保留").sum()), int((d["配到"] == True).sum()), len(m), int(m["月"].nunique())]  # noqa: E712
        theirs_ = [r["事件(過閘去重)"], r["e可進場"], r["配到"], r["主格事件"], r["主格月數=n_eff"]]
        if [int(x) for x in mine_] != [int(x) for x in theirs_]:
            k6.append((r["段"], mine_, theirs_))
    OV = pd.read_csv(os.path.join(out, "overlap.csv"), encoding="utf-8-sig")
    g1 = pd.read_csv(RT.G1_CSV, dtype={"stock_id": str}, usecols=["stock_id", "period", "gate", "rev_hi24"])
    g1 = g1[g1["gate"].astype(str) == "True"]
    lo_, hi_ = g1["period"].min(), g1["period"].max()
    Gs = set(zip(g1["stock_id"], g1["period"])); G1t = set(zip(g1.loc[g1["rev_hi24"].astype(str) == "True", "stock_id"], g1.loc[g1["rev_hi24"].astype(str) == "True", "period"]))
    rv_ = RV[(RV["period"] >= lo_) & (RV["period"] <= hi_)]
    gate_ok = []
    for sid, P in zip(rv_["sid"], rv_["period"]):
        i = ix.get(sid, -1)
        y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        k = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10)), "right"))
        gate_ok.append(bool(i >= 0 and 1 <= k <= CEND and G[i, k - 1]))
    rv_ = rv_[np.array(gate_ok)]
    yi_ = (rv_["hi24"] == 1.0) & ~(rv_["hi24_prev"] == 1.0)
    both = set(zip(rv_["sid"], rv_["period"])) & Gs
    Y = {k for k in zip(rv_.loc[yi_, "sid"], rv_.loc[yi_, "period"]) if k in both}; Gb = {k for k in G1t if k in both}
    r0 = OV.iloc[0]
    k6b = [int(r0["本件乙列"]) == len(Y), int(r0["G1列"]) == len(Gb), int(r0["交集"]) == len(Y & Gb)]
    CK["K6_段表與重疊自算"] = {"段表不符": k6, "重疊①相同": all(k6b), "自算": [len(Y), len(Gb), len(Y & Gb)]}
    log(f"[K6] {CK['K6_段表與重疊自算']}")
    # ── K7
    cols = list(EV.columns) + [c for f in glob.glob(os.path.join(out, "*.csv")) for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns]
    badc = [c for c in cols if any(w in c for w in ("報酬", "年化", "淨值", "回落", "價格", "收盤", "開盤價", "R值", "d值")) and "配對特徵" not in c]
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(RT.WORK, "git_before.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    allowed = ("researchRevTurn_freq", "researchShortageExit_freq", "resultsRevTurn", "resultsShortageExit")
    CK["K7"] = {"報酬類欄": badc, "策略鎖": lock, "git 新增（相對開跑前）": extra, "git 只多本件": all(any(w in x for w in allowed) for x in extra)}
    ok = (CK["K1_登錄sha"]["相符"] and bad == 0 and b2 == 0 and b3 == 0 and CK["K4_事件集合"]["只在自算"] == 0 and CK["K4_事件集合"]["只在events"] == 0
          and b5["對照不符"] == 0 and b5["候選數不符"] == 0 and not k6 and all(k6b) and not badc and "相符" in "".join(lock) and CK["K7"]["git 只多本件"])
    CK["全過"] = bool(ok)
    log(f"[K7] {CK['K7']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
