# -*- coding: utf-8 -*-
"""researchYLtrend_ma 的獨立查核（⛔ 不 import researchYLtrend_ma、⛔ 不 import researchYLtrend）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLtrend_ma_check.py

① 抽 40 筆主窗營量 AND 列：自己讀 D.load_stock（main 快照）、有效 K 棒上 pandas rolling 算 MA20／MA60 ⇒ T2a、T2b（並核原 T2）對 ma/sig_and_main
② 抽 5 檔：自己算 eligible 根、營收旗標、T2a、20 根去重 ⇒ 窗內 (sid, k) 集合對 ma/sig_b_main 的 T2a
③ 原 T2 的 6 格與營量 v1：ma/cells.csv 的三段年化、回落 ＝ resultsYLtrend/cells.csv（repr）
④ 標籤（0050 同段）、退化旗標自己重判；配對差從 ma/pairdiff.npz 自己做月分群 CR0 ⇒ 對 ma/cells.csv（差 ≤ 1e−12）
⑤ 種子 0：甲_T2a_H60 與乙_T2b_H60 自己組訊號、自己呼叫 research11.simulate_mtm ⇒ 探索、確認年化對 ma/seeds_main（repr）
⚠ 範圍：早年世界只核 ③④（⛔ 沒重跑早年引擎、沒重算早年旗標）
⇒ backtest/resultsYLtrend/ma/check.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import research11 as R11

OUT = "backtest/resultsYLtrend/ma"; REF = "backtest/resultsYLtrend"
RP = dict(float_precision="round_trip")
errs = []; info = {}
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
PT = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
cal = D.load_calendar(); n = len(cal); w0, w1 = RR.win_bounds(cal)
mk = D.load_universe().set_index("stock_id")["market"]
rng = np.random.default_rng(20260928)
SA = pd.read_csv(os.path.join(OUT, "sig_and_main.csv.gz"), dtype={"sid": str}, **RP)
SB = pd.read_csv(os.path.join(OUT, "sig_b_main.csv.gz"), dtype={"sid": str}, **RP)
T = lambda v: str(v) == "True"

# ①
nb = 0
for _, r in SA.iloc[rng.choice(len(SA), size=40, replace=False)].iterrows():
    df = D.load_stock(r["sid"], mk.get(r["sid"], "twse"), cal).df
    idx = np.flatnonzero(df["traded"].to_numpy()); c = pd.Series(df["close"].to_numpy(float)[idx]); k = int(r["k"])
    m20, m60 = c.rolling(20).mean().to_numpy(), c.rolling(60).mean().to_numpy()
    for nm, v in (("T2a", c[k] > m20[k]), ("T2b", c[k] > m60[k]), ("T2", c[k] > m20[k] > m60[k])):
        if bool(v) != T(r[nm]):
            nb += 1; errs.append(f"① {r['sid']} k{k} {nm}")
info["① 抽 40 筆 T2／T2a／T2b 不同"] = nb

# ②
rev = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
nb = 0
for sid in rng.choice(sorted(set(SB.loc[SB["Tk"] == "T2a", "sid"])), size=5, replace=False):
    B = R11.load_bars(sid, mk.get(sid, "twse"), cal)
    idx, c, amt, skip, nbar = B["idx"], B["c"], B["amt"], B["skip"], B["next_bad"]
    nn = len(idx); ar = np.arange(nn); s = pd.Series(c)
    ma20, ma100 = (np.array(s.rolling(w).mean().to_numpy(), dtype=float) for w in (20, 100))
    ap = np.array(pd.Series(np.roll(amt, 1)).rolling(20).mean().to_numpy(), dtype=float); ap[:21] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = amt / ap; t2a = c > ma20
    el = (ar >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(ratio) & (nbar[np.maximum(ar - 20, 0)] > ar)
    g = rev[rev["stock_id"] == sid].sort_values("signal_pos")
    sp, hi = g["signal_pos"].to_numpy(int), g["rev_hi24"].fillna(False).astype(bool).to_numpy()
    rf = np.zeros(nn, bool)
    for k in range(nn):
        j = np.searchsorted(sp, idx[k], side="right") - 1
        rf[k] = j >= 0 and idx[k] - sp[j] <= 45 and hi[j]
    keep = []; last = -10 ** 9
    for k in np.flatnonzero(el & rf & t2a & (ar + 1 < nn)):
        if k - last > 20:
            keep.append(k); last = k
    mine = {int(k) for k in keep if w0 <= idx[k + 1] <= w1}
    ref = set(SB.loc[(SB["Tk"] == "T2a") & (SB["sid"] == sid), "k"].astype(int))
    if mine != ref:
        nb += 1; errs.append(f"② {sid} 自算 {len(mine)} 檔 {len(ref)}")
info["② 抽 5 檔 乙 T2a 訊號集合不同"] = nb

# ③
RC = pd.read_csv(os.path.join(REF, "cells.csv"), **RP).set_index("格"); M = PT.set_index("格")
nb = 0
for k in [x for x in M.index if x == "營量v1" or "_T2_" in x]:
    for sg in ("探索", "確認", "早年"):
        for c_ in (f"{sg}_年化", f"{sg}_回落"):
            if repr(float(M.loc[k, c_])) != repr(float(RC.loc[k, c_])):
                nb += 1; errs.append(f"③ {k} {c_}")
info["③ 原 T2 與營量 v1 格 不同"] = nb

# ④
B50 = S["0050"]
lab = lambda c, m, b: "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")
Z = np.load(os.path.join(OUT, "pairdiff.npz"))
ecal = None
nb = 0
segd = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
for k, r in M.iterrows():
    for sg in ("探索", "確認", "早年"):
        if lab(r[f"{sg}_年化"], r[f"{sg}_回落"], B50[sg]) != r[f"{sg}_標籤"]:
            nb += 1; errs.append(f"④ {k} {sg} 標籤")
    dg = (k != "營量v1") and (r["探索_持股"] < 10 or r["探索_現金"] > 0.30)
    if bool(dg) != T(r["退化"]):
        nb += 1; errs.append(f"④ {k} 退化")
    if k == "營量v1":
        continue
    for sg in ("探索", "確認"):
        d = Z[f"{k}|{sg}"]
        x, y = int(cal.searchsorted(pd.Timestamp(segd[sg][0]))), int(cal.searchsorted(pd.Timestamp(segd[sg][1])))
        mon = np.array([str(t)[:7] for t in cal[x + 1:y + 1]])
        m = d.mean(); s_ = pd.Series(d - m).groupby(mon).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(d)
        for nm, v in (("配對差年化", m * 245), ("配對差lo", (m - 1.96 * se) * 245), ("配對差hi", (m + 1.96 * se) * 245)):
            if abs(v - r[f"{sg}_{nm}"]) > 1e-12:
                nb += 1; errs.append(f"④ {k} {sg} {nm}")
info["④ 標籤／退化／配對差 不同"] = nb

# ⑤
SEED = pd.read_csv(os.path.join(OUT, "seeds_main.csv.gz"), **RP)
jobs = [("甲_T2a_H60", SA[SA["T2a"].map(T)], 60), ("乙_T2b_H60", SB[SB["Tk"] == "T2b"], 60)]
sids = sorted(set().union(*[set(j[1]["sid"]) for j in jobs]))
cl, op = RR.load_prices(sids, cal, mk, "branch"); cl, op = RR.pad_px_t1(cl, op)
SF = R11.stop_force_days(R11.valid_from_data(sids, mk, cal), w1)
nb = 0
for key, sg_, H in jobs:
    o = R11.simulate_mtm(sg_.copy(), f"H{H}", 20, np.random.default_rng(7000), cl, op, n + 1, return_equity=True, log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)
    eq = np.asarray(o["equity"], float)
    for sg, (x, y) in segd.items():
        a_, b_ = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], a_, b_)
        ref = SEED[(SEED["格"] == key) & (SEED["r"] == 0)].iloc[0]
        info[f"⑤ 種子0 {key} {sg}（自跑／檔）"] = [float(c_), float(ref[f"{sg}_年化"])]
        if repr(float(c_)) != repr(float(ref[f"{sg}_年化"])):
            nb += 1; errs.append(f"⑤ {key} {sg}")
info["⑤ 不同"] = nb
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:40]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:15]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
