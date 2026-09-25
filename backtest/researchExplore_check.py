# -*- coding: utf-8 -*-
"""PREREG探索批【探索段】查核——⛔ 不 import 主程式（researchExplore）、⛔ 不 import 回測庫任何模組；只讀輸出檔與原始資料檔。

    python3 backtest/researchExplore_check.py [--out backtest/resultsExplore]

從逐種子檔（seeds.csv）重算：每格年化中位、回落中位、比值、對 0050 的標籤、排名、候選序、5 條線索的挑選、
運氣分位（F̂^171）；0050 同窗從 data/stocks/0050.csv＋data/adj/0050.csv 自己算（as-of 2022-12-30 的還原因子）；
另從 features.csv 自己重做「逐量測日前 10%」的挑選，核對 cands.csv（⊆ 挑選集，差額 ＝ 進場開盤剔除數）。
比對：與主程式輸出逐項相同（浮點 ⇒ 列出最大差；排名、標籤、線索 ⇒ 要完全一致）。
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

DATA = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
CUT = "2022-12-30"
W0 = "2017-03-02"
CONDS = [f"F{i:02d}" for i in range(1, 19)]
CELLS = [a for a in CONDS] + [f"{a}+{b}" for i, a in enumerate(CONDS) for b in CONDS[i + 1:]]


def z0050():
    cal = pd.read_csv(os.path.join(DATA, "meta", "calendar_twse.csv"))["date"].astype(str).str[:10]
    cal = sorted(d for d in cal if d <= CUT)
    px = pd.read_csv(os.path.join(DATA, "stocks", "0050.csv"), dtype=str)
    px = px.drop_duplicates("date").set_index("date")["close"].astype(float)
    px = px[px > 0]
    adj = pd.read_csv(os.path.join(DATA, "adj", "0050.csv"), dtype=str)
    adj = adj[adj["date"].str[:10] <= CUT]
    ev = []
    for r in adj.itertuples():
        fo = pd.to_numeric(r.factor_official, errors="coerce") if "factor_official" in adj.columns else np.nan
        ev.append((r.date[:10], float(fo) if np.isfinite(fo) else float(r.factor)))
    c = []
    last = np.nan
    for d in cal:
        f = 1.0
        for ed, fe in ev:
            if ed > d:
                f *= fe
        v = px.get(d, np.nan)
        if np.isfinite(v):
            last = v * f
        c.append(last)
    c = np.array(c)
    i0 = cal.index(W0)
    seg = c[i0:] / c[i0]
    yrs = len(seg) / 245.0
    a = seg[-1] ** (1 / yrs) - 1
    d = float((seg / np.maximum.accumulate(seg) - 1).min())
    return a, d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="backtest/resultsExplore"); a = ap.parse_args()
    o = a.out
    fails = []
    S = pd.read_csv(os.path.join(o, "seeds.csv"), dtype={"cell": str}, float_precision="round_trip")
    RK = pd.read_csv(os.path.join(o, "ranking_171.csv"), dtype={"cell": str}, float_precision="round_trip")
    CL = pd.read_csv(os.path.join(o, "clues.csv"), dtype={"cell": str})
    SM = json.load(open(os.path.join(o, "summary.json"), encoding="utf-8"))
    # ① 0050
    a50, d50 = z0050()
    s50 = SM["0050同窗"]
    e50 = max(abs(a50 - s50["年化"]), abs(d50 - s50["回落"]))
    print(f"① 0050 同窗（自算）年化 {a50:+.6%} 回落 {d50:+.6%} 比值 {a50 / abs(d50):.6f}｜主程式 {s50['年化']:+.6%} {s50['回落']:+.6%}｜最大差 {e50:.2e}")
    if e50 > 1e-9:
        fails.append("0050")
    r50 = a50 / abs(d50)
    # ② 逐格
    rows = []
    for i, nm in enumerate(CELLS):
        g = S[S["cell"] == nm]
        seeds = sorted(g["seed"].tolist())
        if seeds != list(range(102000, 102200)):
            fails.append(f"種子集 {nm}")
        cg = np.sort(g["cagr"].to_numpy(float)); mg = np.sort(g["mdd"].to_numpy(float))
        A = (cg[99] + cg[100]) / 2.0; Dd = (mg[99] + mg[100]) / 2.0
        ratio = A / abs(Dd)
        lab = ("Q" if ratio >= r50 else "R") if A > a50 else "F"
        rows.append((i, nm, A, Dd, ratio, lab))
    s0 = S[S["cell"] == "S0"]
    if sorted(s0["seed"]) != list(range(102000, 103000)):
        fails.append("S0 種子集")
    X = pd.DataFrame(rows, columns=["idx", "cell", "A", "D", "ratio", "label"])
    X = X.sort_values(["ratio", "idx"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    X["rank"] = np.arange(1, len(X) + 1)
    M = X.merge(RK[["cell", "rank", "A", "D", "ratio", "label", "cand_order", "luck_q"]], on="cell", suffixes=("", "_m"))
    dA = float((M["A"] - M["A_m"]).abs().max()); dD = float((M["D"] - M["D_m"]).abs().max()); dR = float((M["ratio"] - M["ratio_m"]).abs().max())
    same_rank = bool((M["rank"] == M["rank_m"]).all()); same_lab = bool((M["label"] == M["label_m"]).all())
    print(f"② 171 格：年化中位最大差 {dA:.2e}｜回落中位 {dD:.2e}｜比值 {dR:.2e}｜排名全同 {same_rank}｜標籤全同 {same_lab}")
    if dA > 1e-12 or dD > 1e-12 or dR > 1e-9 or not same_rank or not same_lab:
        fails.append("逐格")
    # ③ 候選序與線索（獨立的貪婪）
    cand = X[X["A"] > a50]
    co = {nm: j + 1 for j, nm in enumerate(cand["cell"])}
    mco = M.set_index("cell")["cand_order"]
    ok_co = all((co.get(nm) == (int(v) if np.isfinite(v) else None)) for nm, v in mco.items())
    cnt = {f: 0 for f in CONDS}; picks = []
    for nm in cand["cell"]:
        fs = nm.split("+")
        if max(cnt[f] for f in fs) >= 2:
            continue
        for f in fs:
            cnt[f] += 1
        picks.append(nm)
        if len(picks) == 5:
            break
    same_clue = picks == CL["cell"].tolist()
    print(f"③ 年化>0050 {len(cand)} 格｜候選序全同 {ok_co}｜線索（查核）{picks}｜與主程式相同 {same_clue}")
    if not ok_co or not same_clue:
        fails.append("線索")
    # ④ 運氣分位
    rs = np.sort((s0["cagr"] / s0["mdd"].abs()).to_numpy(float))
    lq = {nm: (np.searchsorted(rs, x, side="right") / len(rs)) ** 171 for nm, x in zip(X["cell"], X["ratio"])}
    dq = max(abs(lq[nm] - q) for nm, q in zip(M["cell"], M["luck_q"]))
    print(f"④ 運氣分位（F̂^171）最大差 {dq:.2e}；線索：" + "、".join(f"{nm} {lq[nm]:.4f}" for nm in picks))
    if dq > 1e-12:
        fails.append("運氣分位")
    # ⑤ 候選挑選（從 features.csv 獨立重做）
    F = pd.read_csv(os.path.join(o, "features.csv"), dtype={"sid": str, "rev_period": str}, float_precision="round_trip")
    C = pd.read_csv(os.path.join(o, "cands.csv"), dtype={"sid": str, "cell": str})
    CS = pd.read_csv(os.path.join(o, "cand_stats.csv"), dtype={"cell": str}).set_index("cell")
    mine = {nm: set() for nm in CELLS}
    for t, g in F.groupby("pos"):
        g = g.sort_values("sid")
        sids = g["sid"].to_numpy()
        pc = {}
        for f in CONDS:
            v = g[f].to_numpy(float); ok = np.isfinite(v); xs = np.sort(v[ok])
            p = np.full(len(v), np.nan); p[ok] = np.searchsorted(xs, v[ok], side="left") / len(xs) * 100.0
            pc[f] = p
        for nm in CELLS:
            fs = nm.split("+")
            s = pc[fs[0]] if len(fs) == 1 else (pc[fs[0]] + pc[fs[1]]) / 2.0
            ok = np.flatnonzero(np.isfinite(s))
            if not len(ok):
                continue
            k = math.ceil(0.10 * len(ok))
            order = sorted(ok, key=lambda j: (-s[j], sids[j]))[:k]
            mine[nm].update((int(t) + 1, sids[j]) for j in order)
    bad = []
    for nm in CELLS:
        got = set(zip(C.loc[C["cell"] == nm, "entry_pos"].astype(int), C.loc[C["cell"] == nm, "sid"]))
        if not got <= mine[nm] or len(mine[nm]) - len(got) != int(CS.loc[nm, "dropped_entry_open"]) or len(mine[nm]) != int(CS.loc[nm, "selected"]):
            bad.append(nm)
    print(f"⑤ 前 10% 挑選（獨立重做）：171 格中不一致 {len(bad)} 格 {bad[:5]}")
    if bad:
        fails.append("挑選")
    print("查核結果：" + ("✅ 全部一致" if not fails else f"⛔ 不一致：{fails}"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
