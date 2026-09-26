# -*- coding: utf-8 -*-
"""researchYfSlots2 的獨立查核（⛔ 不 import backtest.researchYfSlots2／researchYear1M）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfSlots2_check

  V1 閘重做：single_seeds 營飆 N10 對 regime_t1 t1 #1、營量 N20 對 rerun17_seeds main #13（逐種子逐位元）；營量四種槽數各 200 顆 eq_sha 相同；
     combo 10×20 對 resultsYfMix13/mix_seeds.csv.gz AB50 主窗（逐位元）
  V2 cells.csv：從逐種子檔自己重算中位、p10／p90、比值、標籤（自寫判準）、持有檔數與單檔占比彙總 ⇒ 逐格比對；營飆 N20 參照列 ＝ resultsN17/nslots/cells.csv
  V3 10×20 另一條路：用 resultsYfMix13/eq_main.npz 的營飆 200 條、營量一條，自寫再平衡重算年化／回落／期末 ⇒ 對 combo_seeds
  V4 持有檔數另一條路：用 resultsYfMix13/positions.csv.gz 重建持股 ⇒ 單套營飆 10／營量 20 與各半 10×20 的逐日平均、逐日最大、重疊 ⇒ 對逐種子檔
  V5 合理性：held_max ≤ 槽數合計；held_mean ≤ held_max；0 ＜ maxw ≤ 1
輸出 resultsYfSlots2/check.json
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYfSlots2")
N17 = os.path.join(HERE, "resultsN17")
M13 = os.path.join(HERE, "resultsYfMix13")
RTP = dict(float_precision="round_trip")
ANC = (0.24020209886370614, -0.3395700527611012)


def close(a, b, tol=1e-9):
    a, b = float(a), float(b)
    if np.isnan(a) and np.isnan(b):
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def same_bits(x, y):
    return sum(repr(float(p)) != repr(float(q)) for p, q in zip(x, y))


def main():
    res = {}
    S = pd.read_csv(os.path.join(OUT, "single_seeds.csv"), dtype={"eq_sha": str}, **RTP)
    C = pd.read_csv(os.path.join(OUT, "combo_seeds.csv"), **RTP)
    T = pd.read_csv(os.path.join(OUT, "cells.csv"), **RTP)
    # V1
    v1 = {}
    for arm, N, f, st, cid in (("A", 10, "regime_t1/seeds.csv", "t1", 1), ("B", 20, "rerun17_seeds.csv", "main", 13)):
        rf = pd.read_csv(os.path.join(N17, f), dtype={"eq_sha": str}, **RTP)
        rf = rf[(rf["stage"] == st) & (rf["cell"] == cid)].sort_values("r")
        g = S[(S["arm"] == arm) & (S["N"] == N)].sort_values("r")
        v1[f"{arm}{N}"] = int(sum(same_bits(g[k], rf[k]) for k in ("cagr", "mdd", "vol")) + (g["eq_sha"].to_numpy() != rf["eq_sha"].to_numpy()).sum())
    v1["營量200顆相同"] = {int(N): int(S[(S["arm"] == "B") & (S["N"] == N)]["eq_sha"].nunique()) for N in (5, 10, 15, 20)}
    rf = pd.read_csv(os.path.join(M13, "mix_seeds.csv.gz"), **RTP)
    rf = rf[(rf["scope"] == "主窗") & (rf["mix"] == "AB50")].sort_values("r")
    g = C[(C["nA"] == 10) & (C["nB"] == 20)].sort_values("r")
    v1["10x20對AB50"] = int(sum(same_bits(g[k], rf[k]) for k in ("cagr", "mdd", "end_value", "cost_sum")))
    v1["過"] = v1["A10"] == 0 and v1["B20"] == 0 and set(v1["營量200顆相同"].values()) == {1} and v1["10x20對AB50"] == 0
    res["V1_閘"] = v1
    # V2
    bad = []
    for row in T.itertuples():
        if "參照" in row.列:
            ns = pd.read_csv(os.path.join(N17, "nslots", "cells.csv"), encoding="utf-8-sig", **RTP)
            q = ns[ns["檔數N"] == 20].iloc[0]
            if not (close(q["年化中位"], row.年化中位) and close(q["回落中位"], row.回落中位) and q["標籤（對0050）"] == row.對0050標籤):
                bad.append(row.列)
            continue
        if row.列.startswith("單套"):
            g = S[(S["arm"] == ("A" if row.營飆N else "B")) & (S["N"] == (row.營飆N or row.營量N))]
        else:
            g = C[(C["nA"] == row.營飆N) & (C["nB"] == row.營量N)]
        c, m = g["cagr"].quantile(.5), g["mdd"].quantile(.5)
        ratio = c / abs(m)
        lab = ("合格" if ratio >= ANC[0] / abs(ANC[1]) else "另列") if c > ANC[0] else "不合格"
        pairs = [(c, row.年化中位), (m, row.回落中位), (ratio, row.比值), (g["cagr"].quantile(.1), row.年化p10), (g["cagr"].quantile(.9), row.年化p90),
                 (g["end_value"].quantile(.5), row.期末金額100萬中位), (g["held_mean"].quantile(.5), row.平均實際持有檔數_中位),
                 (g["held_max"].quantile(.5), row.最大同時持有_中位), (g["maxw"].quantile(.5), row.單檔最大占比_中位), (g["maxw"].quantile(.9), row.單檔最大占比_p90)]
        if not all(close(a, b) for a, b in pairs) or lab != row.對0050標籤:
            bad.append(row.列)
    res["V2_cells"] = {"列數": len(T), "不符": bad, "過": not bad}
    # V3
    Z = np.load(os.path.join(M13, "eq_main.npz"))
    YF, B13 = Z["yf"], Z["b13"]; yr = pd.DatetimeIndex(pd.to_datetime(Z["dates"])).year
    g = C[(C["nA"] == 10) & (C["nB"] == 20)].set_index("r")
    md = 0.0
    for r in range(200):
        a, b = 0.5, 0.5; out = [1.0]
        for t in range(1, len(B13)):
            a *= YF[r][t] / YF[r][t - 1]; b *= B13[t] / B13[t - 1]; v = a + b
            if yr[t] != yr[t - 1]:
                v -= abs(0.5 * v - a) * 0.00585; a = b = 0.5 * v
            out.append(v)
        V = np.array(out); n = len(V)
        cg = (V[-1] / V[0]) ** (245 / n) - 1; mdd = float((V / np.maximum.accumulate(V) - 1).min())
        md = max(md, abs(cg - g.loc[r, "cagr"]), abs(mdd - g.loc[r, "mdd"]), abs(1e6 * V[-1] / V[0] / g.loc[r, "end_value"] - 1))
    res["V3_10x20另算"] = {"最大差": md, "過": md < 1e-10}
    # V4
    P = pd.read_csv(os.path.join(M13, "positions.csv.gz"), dtype={"sid": str}, **RTP)
    w0, w1 = int(Z["w0"]), int(Z["w1"]); n = w1 - w0 + 1

    def held(df):
        H = [set() for _ in range(n)]
        for sid, tb, ts in zip(df["sid"], df["t_buy"], df["t_sell"]):
            ts = 10 ** 9 if ts < 0 else ts
            for t in range(max(tb, w0), min(ts, w1 + 1)):
                H[t - w0].add(sid)
        return H
    HB = held(P[P["cell"] == 13])
    sB = S[(S["arm"] == "B") & (S["N"] == 20)].iloc[0]
    bad4 = int(not (close(np.mean([len(h) for h in HB]), sB["held_mean"]) and max(len(h) for h in HB) == sB["held_max"]))
    sA = S[(S["arm"] == "A") & (S["N"] == 10)].set_index("r"); gC = C[(C["nA"] == 10) & (C["nB"] == 20)].set_index("r")
    for r, gp in P[P["cell"] == 1].groupby("r"):
        HA = held(gp)
        U = [len(a | b) for a, b in zip(HA, HB)]; O = [len(a & b) for a, b in zip(HA, HB)]
        ok = (close(np.mean([len(h) for h in HA]), sA.loc[r, "held_mean"]) and max(len(h) for h in HA) == sA.loc[r, "held_max"]
              and close(np.mean(U), gC.loc[r, "held_mean"]) and max(U) == gC.loc[r, "held_max"] and close(np.mean(O), gC.loc[r, "overlap_mean"]))
        bad4 += int(not ok)
    res["V4_持有檔數另算"] = {"不符": bad4, "過": bad4 == 0}
    # V5
    cap = C["nA"] + C["nB"]
    v5 = {"combo_held_max超過槽數": int((C["held_max"] > cap).sum()), "single_held_max超過槽數": int((S["held_max"] > S["N"]).sum()),
          "held_mean>held_max": int((C["held_mean"] > C["held_max"]).sum() + (S["held_mean"] > S["held_max"]).sum()),
          "maxw越界": int(((C["maxw"] <= 0) | (C["maxw"] > 1)).sum() + ((S["maxw"] <= 0) | (S["maxw"] > 1)).sum())}
    v5["過"] = all(v == 0 for v in v5.values())
    res["V5_合理性"] = v5
    res["全部過"] = all(v["過"] for v in res.values() if isinstance(v, dict))
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()
