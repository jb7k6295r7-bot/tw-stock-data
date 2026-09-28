# -*- coding: utf-8 -*-
"""researchYLtrend 的獨立查核（⛔ 不 import researchYLtrend）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLtrend_check.py

① 趨勢旗標：抽 30 筆主窗營量 AND 列，自己讀 D.load_stock（main 快照）、自己在有效 K 棒上算 MA5／10／20／60、250 根最高、月底動能 ⇒ T1／T2／T3、mom 對 sig_and_main；
   T4：抽 2 筆，自己讀當月 panel_ext eligible 全部股票的月底動能、自己排前 30% ⇒ 旗標相同
② 乙族訊號：抽 5 檔，自己算 eligible 根（≥ 249、非 skip、MA100 與 amt_ratio 有值、前 20 根無壞根；skip／next_bad 取 research11.load_bars）、
   自己套營收旗標（panel_rev 最新一期、≤ 45 根、rev_hi24）、自己算 T2、自己 20 根去重 ⇒ 窗內 (sid, k) 集合對 sig_b_main 的 T2
③ 格：自己套退化、先合格再比值、0050 同段標籤、件標籤、對營量 v1 的判句、219 百分位（resultsYLretest/b2_rand219.csv）⇒ 對 cells.csv／summary.json
④ 種子 0：挑中格與營量 v1 自己組訊號（讀 sig_*_main）、自己呼叫 research11.simulate_mtm ⇒ 探索、確認年化對 seeds_main.csv.gz（repr）
⑤ 配對差：從 pairdiff.npz 自己做月分群 CR0 ⇒ 對 cells.csv 的配對差年化與 CI（差 ≤ 1e−12）
⚠ 範圍：早年世界只核 ③⑤（⛔ 沒重跑早年引擎、沒重算早年旗標）
⇒ backtest/resultsYLtrend/check.json
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

OUT = "backtest/resultsYLtrend"
RP = dict(float_precision="round_trip")
errs = []; info = {}
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
PT = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
cal = D.load_calendar(); n = len(cal)
w0, w1 = RR.win_bounds(cal)
mk = D.load_universe().set_index("stock_id")["market"]
rng = np.random.default_rng(20260928)
SA = pd.read_csv(os.path.join(OUT, "sig_and_main.csv.gz"), dtype={"sid": str}, **RP)
SB = pd.read_csv(os.path.join(OUT, "sig_b_main.csv.gz"), dtype={"sid": str}, **RP)


def bars_of(sid):
    st = D.load_stock(sid, mk.get(sid, "twse"), cal); df = st.df
    idx = np.flatnonzero(df["traded"].to_numpy())
    c = df["close"].to_numpy(float)[idx]
    return idx, c, df


def mom_of(idx, c):
    d = cal[idx]; mi = d.year * 12 + d.month - 1
    s = pd.Series(c, index=mi.to_numpy()); me = s.groupby(level=0).last()
    return mi.to_numpy(), me


# ① T1–T3、mom
smp = SA.iloc[rng.choice(len(SA), size=30, replace=False)]
nb1 = 0
for _, r in smp.iterrows():
    idx, c, _ = bars_of(r["sid"]); k = int(r["k"])
    s = pd.Series(c)
    ma = {w: s.rolling(w).mean().to_numpy() for w in (5, 10, 20, 60)}
    hi = s.rolling(250).max().to_numpy()
    t1 = bool(ma[5][k] > ma[10][k] > ma[20][k] > ma[60][k]); t2 = bool(c[k] > ma[20][k] > ma[60][k]); t3 = bool(c[k] >= 0.9 * hi[k]) if np.isfinite(hi[k]) else False
    mi, me = mom_of(idx, c); m = mi[k]
    mm = me.get(m - 2, np.nan) / me.get(m - 8, np.nan) - 1.0
    for nm, a_, b_ in (("T1", t1, str(r["T1"]) == "True"), ("T2", t2, str(r["T2"]) == "True"), ("T3", t3, str(r["T3"]) == "True")):
        if a_ != b_:
            nb1 += 1; errs.append(f"① {r['sid']} k{k} {nm}")
    if not ((np.isnan(mm) and np.isnan(r["mom"])) or abs(mm - r["mom"]) <= 1e-12 * max(1, abs(mm))):
        nb1 += 1; errs.append(f"① {r['sid']} k{k} mom {mm} {r['mom']}")
info["① 抽 30 筆 T1–T3／mom 不同"] = nb1
# T4
mp = pd.read_csv("backtest/resultsp9_engine/panel_ext.csv.gz", dtype={"stock_id": str}, parse_dates=["measure_date"])
nb4 = 0
for _, r in SA.iloc[rng.choice(len(SA), size=2, replace=False)].iterrows():
    d = cal[int(r["pos"])]; m = d.year * 12 + d.month - 1
    g = mp[(mp["measure_date"].dt.year == d.year) & (mp["measure_date"].dt.month == d.month) & mp["eligible"].astype(str).isin(["True", "1", "1.0"])]
    vals = {}
    for s in sorted(g["stock_id"]):
        try:
            idx, c, _ = bars_of(s)
        except Exception:
            continue
        mi, me = mom_of(idx, c)
        v = me.get(m - 2, np.nan) / me.get(m - 8, np.nan) - 1.0
        if np.isfinite(v):
            vals[s] = v
    ss = sorted(vals); vv = np.array([vals[s] for s in ss])
    o_ = np.lexsort((np.array(ss), vv)); dq = np.empty(len(ss), int); dq[o_] = (np.arange(len(ss)) * 10) // len(ss)
    if r["sid"] in vals:
        mine = bool(dq[ss.index(r["sid"])] >= 7)
    else:
        mine = bool(np.isfinite(r["mom"]) and r["mom"] >= vv[dq >= 7].min())
    if mine != (str(r["T4"]) == "True"):
        nb4 += 1; errs.append(f"① T4 {r['sid']} {d.date()}")
info["① T4 抽 2 筆不同"] = nb4

# ② 乙族 T2
rev = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
cand_s = sorted(set(SB.loc[SB["Tk"] == "T2", "sid"]))
nb2 = 0; ncmp = 0
for sid in list(rng.choice(cand_s, size=5, replace=False)):
    B = R11.load_bars(sid, mk.get(sid, "twse"), cal)
    idx, o, c, amt, skip, nbar = B["idx"], B["o"], B["c"], B["amt"], B["skip"], B["next_bad"]
    nn = len(idx); ar = np.arange(nn); s = pd.Series(c)
    ma20, ma60, ma100 = (np.array(s.rolling(w).mean().to_numpy(), dtype=float) for w in (20, 60, 100))
    ap = np.array(pd.Series(np.roll(amt, 1)).rolling(20).mean().to_numpy(), dtype=float); ap[:21] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = amt / ap
    el = (ar >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(ratio) & (nbar[np.maximum(ar - 20, 0)] > ar)
    g = rev[rev["stock_id"] == sid].sort_values("signal_pos")
    sp, hi = g["signal_pos"].to_numpy(int), g["rev_hi24"].fillna(False).astype(bool).to_numpy()
    rf = np.zeros(nn, bool)
    for k in range(nn):
        j = np.searchsorted(sp, idx[k], side="right") - 1
        rf[k] = j >= 0 and idx[k] - sp[j] <= 45 and hi[j]
    with np.errstate(invalid="ignore"):
        t2 = (c > ma20) & (ma20 > ma60)
    cand = np.flatnonzero(el & rf & t2 & (ar + 1 < nn))
    keep = []; last = -10 ** 9
    for k in cand:
        if k - last > 20:
            keep.append(k); last = k
    mine = {int(k) for k in keep if w0 <= idx[k + 1] <= w1}
    ref = set(SB.loc[(SB["Tk"] == "T2") & (SB["sid"] == sid), "k"].astype(int))
    ncmp += 1
    if mine != ref:
        nb2 += 1; errs.append(f"② {sid} T2 自算 {len(mine)} 檔 {len(ref)}")
info["② 抽 5 檔 乙族 T2 訊號集合不同"] = nb2

# ③ 格
B50 = S["0050"]
lab = lambda c, m, b: "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")
nb3 = 0
for _, r in PT.iterrows():
    for sg in ("探索", "確認", "早年"):
        if lab(r[f"{sg}_年化"], r[f"{sg}_回落"], B50[sg]) != r[f"{sg}_標籤"]:
            nb3 += 1; errs.append(f"③ {r['格']} {sg} 標籤")
deg = PT[(PT["格"] != "營量v1") & ((PT["探索_持股"] < 10) | (PT["探索_現金"] > 0.30))]["格"].tolist()
cand = PT[(PT["格"] != "營量v1") & ~PT["格"].isin(deg)].copy()
q = cand[cand["探索_標籤"] == "合格"] if (cand["探索_標籤"] == "合格").any() else cand
q = q.assign(r_=q["探索_年化"] / q["探索_回落"].abs())
pk = q.sort_values(["r_", "探索_年化"], ascending=[False, False]).iloc[0]["格"] if len(q) else None
if deg != S["退化（挑前排除）"] or pk != S["挑中格"]:
    nb3 += 1; errs.append("③ 挑格")
J = S["判定"]
if pk:
    pr = PT.set_index("格").loc[pk]
    o = {"不合格": 0, "另列": 1, "合格": 2}
    if min((pr["確認_標籤"], pr["早年_標籤"]), key=lambda x: o[x]) != J["件標籤"]:
        nb3 += 1; errs.append("③ 件標籤")
    lo, hi, ed = pr["確認_配對差lo"], pr["確認_配對差hi"], pr["早年_配對差年化"]
    v = ("比營量 v1 好" if ed > 0 else "不穩") if lo > 0 else (("比營量 v1 差" if ed < 0 else "不穩") if hi < 0 else "分不出")
    if not J["對營量v1"].startswith(v):
        nb3 += 1; errs.append(f"③ 對營量v1 {v} vs {J['對營量v1']}")
    R219 = pd.read_csv("backtest/resultsYLretest/b2_rand219.csv")
    mx = R219.groupby("r")["ratio"].max()
    pc = float((mx <= pr["主窗_年化"] / abs(pr["主窗_回落"])).mean())
    info["③ 219 百分位（自算／檔）"] = [pc, J["219 每顆最大比值分佈百分位（≤ 的比例）"]]
    if abs(pc - J["219 每顆最大比值分佈百分位（≤ 的比例）"]) > 1e-12:
        nb3 += 1; errs.append("③ 219")
info["③ 退化／挑中（自算）"] = [deg, pk]; info["③ 不同"] = nb3

# ④ 種子 0
SEED = pd.read_csv(os.path.join(OUT, "seeds_main.csv.gz"), **RP)
nb5 = 0
if pk:
    fam, tk, hh = pk.split("_"); H = int(hh[1:])
    sigp = SA[SA[tk].astype(str) == "True"] if fam == "甲" else SB[SB["Tk"] == tk]
    jobs = [(pk, sigp, H), ("營量v1", SA, 60)]
    sids = sorted(set(sigp["sid"]) | set(SA["sid"]))
    cl, op = RR.load_prices(sids, cal, mk, "branch"); cl, op = RR.pad_px_t1(cl, op)
    SF = R11.stop_force_days(R11.valid_from_data(sids, mk, cal), w1)
    segp = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
    for key, sg_, H_ in jobs:
        sg2 = sg_.copy()
        for c_ in ("relvol",):
            sg2[c_] = sg2[c_].fillna(0.0)
        oo = R11.simulate_mtm(sg2, f"H{H_}", 20, np.random.default_rng(7000), cl, op, n + 1, return_equity=True, log=[], d_max=None, pick="relvol",
                              queue_days=0, stop_force=SF)
        eq = np.asarray(oo["equity"], float)
        for sg, (x, y) in segp.items():
            a_, b_ = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))
            c_, m_, _ = RR.win_metrics(eq, oo["first"], oo["end"], a_, b_)
            ref = SEED[(SEED["格"] == key) & (SEED["r"] == 0)].iloc[0]
            info[f"④ 種子0 {key} {sg}（自跑／檔）"] = [float(c_), float(ref[f"{sg}_年化"])]
            if repr(float(c_)) != repr(float(ref[f"{sg}_年化"])):
                nb5 += 1; errs.append(f"④ {key} {sg}")
info["④ 不同"] = nb5

# ⑤ 配對差 CR0
Z = np.load(os.path.join(OUT, "pairdiff.npz"))
ecal = None
nb6 = 0
segd = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
for _, r in PT[PT["格"] != "營量v1"].iterrows():
    for sg in ("探索", "確認"):
        d = Z[f"{r['格']}|{sg}"]
        x, y = int(cal.searchsorted(pd.Timestamp(segd[sg][0]))), int(cal.searchsorted(pd.Timestamp(segd[sg][1])))
        mon = np.array([str(t)[:7] for t in cal[x + 1:y + 1]])
        m = d.mean(); u = d - m; s_ = pd.Series(u).groupby(mon).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(d)
        for nm, v in (("配對差年化", m * 245), ("配對差lo", (m - 1.96 * se) * 245), ("配對差hi", (m + 1.96 * se) * 245)):
            if abs(v - r[f"{sg}_{nm}"]) > 1e-12:
                nb6 += 1; errs.append(f"⑤ {r['格']} {sg} {nm}")
info["⑤ 配對差（探索、確認）不同"] = nb6
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:40]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:15]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
