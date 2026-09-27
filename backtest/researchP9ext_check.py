# -*- coding: utf-8 -*-
"""P9run K5 截斷補跑 獨立查核（⛔ 不 import researchP9ext／researchP9run／researchYear1M；只讀輸出＋共用引擎）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchP9ext_check

 ① V3 訊號自寫（panel_ext：eligible ∧ rev_hi24＝100 ∧ ma60_up＝100 ∧ ma_stack＝0、量測日 ≥ 2017-01-01、進場＝量測日＋1、出場＝進場＋119；
    出場超過資料尾 ⇒ 墊檔日出場、報酬＝最後收盤÷進場開盤−1；只留進場 ∈ 主窗）⇒ ＝ sig_v3.csv.gz 逐列
 ② 停止交易日自寫（主窗尾前最後一根有效收盤）⇒ 檔數 ＝ summary
 ③ 共用引擎 research11.simulate_mtm，用自寫的訊號、墊檔價格、自寫 MA 狀態（0050 < 含當日 n 日均）與 stop_force，
    重跑 V3 的 基準、2-B ⓐ、2-C ⓒ、2-C ⓕ、By 各 2 顆 ⇒ 年化／回落 ＝ seeds_arms.csv.gz
 ④ 由 seeds 自算四版每臂中位、比值、標籤（seq141）、假訊號 x／30，與原件比的翻不翻 ⇒ ＝ summary.json、flip_table.csv
"""
from __future__ import annotations
import json, os
import numpy as np
import pandas as pd

from . import research11 as R
from . import research13 as R13
from . import data as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsP9ext")
SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
W0, W1 = "2017-03-02", "2026-08-24"


def lab(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


def main():
    D.DATA = SNAP
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES = {}
    cal = D.load_calendar(); n = len(cal); pos = {d: i for i, d in enumerate(cal)}
    w0, w1 = int(cal.searchsorted(pd.Timestamp(W0))), int(cal.searchsorted(pd.Timestamp(W1)))
    p = pd.read_csv(os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz"), dtype={"stock_id": str}, parse_dates=["measure_date"])
    afc = pd.read_csv(os.path.join(HERE, "resultsAFC", "panel.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id"])
    uni = D.load_universe().set_index("stock_id")["market"]
    C, O, V = {}, {}, {}
    for s in sorted(set(p["stock_id"]) | set(afc["stock_id"])):
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy()
        C[s] = pd.Series(c).ffill().to_numpy(np.float32); O[s] = st.df["open"].to_numpy(np.float32); V[s] = np.isfinite(c.astype(float))
    q = p[(p["measure_date"] >= pd.Timestamp("2017-01-01")) & (p["eligible"].astype(str).isin(["True", "1", "1.0"]))]
    m = (q["rev_hi24"] == 100) & (q["ma60_up"] == 100) & (q["ma_stack"] == 0)
    rows = []
    for d, s in zip(q.loc[m, "measure_date"], q.loc[m, "stock_id"]):
        if d not in pos or s not in C:
            continue
        e = pos[d] + 1; x = e + 119
        if e >= n or not (w0 <= e <= w1):
            continue
        o = float(O[s][e])
        if not (np.isfinite(o) and o > 0):
            continue
        if x >= n:
            rows.append((s, e, n, float(C[s][n - 1]) / o - 1.0)); continue
        c = float(C[s][x])
        if np.isfinite(c):
            rows.append((s, e, x, c / o - 1.0))
    mine = pd.DataFrame(rows, columns=["sid", "entry_pos", "xpos_H120", "g_H120"]).sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    sig = pd.read_csv(os.path.join(OUT, "sig_v3.csv.gz"), dtype={"sid": str})
    same = len(mine) == len(sig) and (mine["sid"].values == sig["sid"].values).all() and (mine["entry_pos"].values == sig["entry_pos"].values).all() \
        and (mine["xpos_H120"].values == sig["xpos_H120"].values).all() and float(np.abs(mine["g_H120"].values - sig["g_H120"].values).max()) <= 1e-12
    vk3 = [k for k in S if k.startswith("V3")][0]
    RES["① V3 訊號自寫"] = {"筆（自算／主程式）": [len(mine), len(sig)], "墊檔日出場筆": int((mine["xpos_H120"] == n).sum()),
                         "主程式墊檔日出場筆": S[vk3]["訊號"]["墊檔日出場筆"], "逐列相同": bool(same),
                         "過": bool(same and int((mine["xpos_H120"] == n).sum()) == S[vk3]["訊號"]["墊檔日出場筆"])}
    print(RES["① V3 訊號自寫"], flush=True)
    SF = {s: int(np.flatnonzero(v)[-1]) for s, v in V.items() if v.any() and np.flatnonzero(v)[-1] < w1}
    RES["② 停止交易日"] = {"自算": len(SF), "主程式": S["停止交易日（主窗尾前停止）"], "過": len(SF) == S["停止交易日（主窗尾前停止）"]}
    # ③ 引擎重跑
    b = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    bP = np.r_[b, b[-1]]
    ma = pd.Series(bP).rolling(60, min_periods=60).mean().to_numpy()
    below60 = np.isfinite(ma) & np.isfinite(bP) & (bP < ma)
    RES["③a 自寫 MA60 狀態 ＝ research11.regime_below"] = {"不同天數": int((below60 != R.regime_below(bP, 60)).sum())}
    RES["③a 自寫 MA60 狀態 ＝ research11.regime_below"]["過"] = RES["③a 自寫 MA60 狀態 ＝ research11.regime_below"]["不同天數"] == 0
    CP = {s: np.r_[v, v[-1]].astype(v.dtype) for s, v in C.items()}; OP = {s: np.r_[v, np.float32(np.nan)].astype(v.dtype) for s, v in O.items()}
    KW = {"base": {}, "Ba": {"add_rule": {"kind": "gain", "x": 0.15}}, "Cc": {"size_mult_by_regime": {"mult": 1.5, "below": below60}},
          "Cf": {"regime_trim": {"hold": 0.5, "below": below60}}, "By": {"add_rule": {"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}}}
    SD = pd.read_csv(os.path.join(OUT, "seeds_arms.csv.gz"), float_precision="round_trip")
    d3 = []
    for k, kw in KW.items():
        for r in (0, 1):
            o = R.simulate_mtm(mine, "H120", 8, np.random.default_rng(99000 + r), CP, OP, n + 1, return_equity=True, report_maxw=True, stop_force=SF, **kw)
            c_, m_ = R13.window_stats(o["equity"], min(o["first"], w0), max(o["end"], w1 + 1), w0, w1 + 1)
            ref = SD[(SD["ver"] == "V3") & (SD["arm"] == k) & (SD["r"] == r)].iloc[0]
            d3.append(max(abs(float(c_) - ref["cagr"]), abs(float(m_) - ref["mdd"])))
    RES["③ 引擎重跑（V3 五臂 × 2 顆）"] = {"最大差": float(max(d3)), "過": bool(max(d3) <= 2.3e-16)}
    print(RES["③ 引擎重跑（V3 五臂 × 2 顆）"], flush=True)
    # ④
    c50, m50 = S["0050"]["主窗"]
    bad = []
    vnames = [k for k in S if k[:2] in ("V0", "V1", "V2", "V3") and isinstance(S[k], dict) and "格" in S[k]]
    FK = pd.read_csv(os.path.join(OUT, "seeds_fake.csv.gz"), float_precision="round_trip")
    for vn in vnames:
        x = SD[SD["ver"] == vn[:2]]
        for k, ref in S[vn]["格"].items():
            g = x[x["arm"] == k]
            c, mm = float(g["cagr"].median()), float(g["mdd"].median())
            if abs(c - ref["cagr"]) > 1e-15 or abs(mm - ref["mdd"]) > 1e-15 or lab(c, mm, c50, m50) != ref["label"]:
                bad.append((vn[:2], k))
        if "假訊號臂" in S[vn]:
            f = FK[FK["ver"] == vn[:2]]
            for k, ref in S[vn]["假訊號臂"].items():
                med = f[f["cell"] == k].groupby("j").agg(c=("cagr", "median"), m=("mdd", "median"))
                xq = int(sum(lab(c, mm, c50, m50) == "合格" for c, mm in zip(med["c"], med["m"])))
                if xq != ref["x_Q"]:
                    bad.append((vn[:2], k, "假訊號"))
    FT = pd.read_csv(os.path.join(OUT, "flip_table.csv"))
    oc = pd.read_csv(os.path.join(HERE, "resultsP9run", "cells.csv")).set_index("arm")
    ob = pd.read_csv(os.path.join(HERE, "resultsAvg", "B_cells.csv")).set_index("arm")
    for _, t in FT.iterrows():
        src = ob if t["arm"] == "By" else oc
        l0 = lab(float(src.at[t["arm"], "cagr"]), float(src.at[t["arm"], "mdd"]), c50, m50)
        g = SD[(SD["ver"] == "V3") & (SD["arm"] == t["arm"])]
        l3 = lab(float(g["cagr"].median()), float(g["mdd"].median()), c50, m50)
        flip = f"{l0}→{l3}" if l0 != l3 else "不翻"
        if flip != t["翻"] or l0 != t["原件_標籤"]:
            bad.append(("翻不翻", t["arm"]))
        if t["arm"] != "By" and isinstance(src.at[t["arm"], "label"], str) and src.at[t["arm"], "label"] and src.at[t["arm"], "label"] != l0:
            bad.append(("原件標籤 ≠ cells.csv", t["arm"]))
    RES["④ 中位、標籤、假訊號、翻不翻"] = {"不同": bad, "過": not bad}
    RES["全部過"] = all(v["過"] is True for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
