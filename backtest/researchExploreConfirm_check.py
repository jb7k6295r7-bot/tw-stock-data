# -*- coding: utf-8 -*-
"""PREREG探索批 確認段 A 查核——⛔ 不 import 主程式或回測庫任何模組；只讀 confirmA 輸出與原始資料檔。

    python3 backtest/researchExploreConfirm_check.py

① 0050 窗 A（2023-01-03～2026-08-24）自算：data/stocks/0050.csv × 檔內 cum_factor（事件日 ＞ d 的第一筆），交易日曆上 ffill
② 從 seeds.csv 重算 5 條線索／S0／W1ref／W1full 的年化中位、回落中位、比值、標籤 ⇒ 對 cells.csv
③ S0 逐顆合格比例 p、5p、⚠ 旗標 ⇒ 對 summary.json；種子集（線索 200、S0 1,000）
"""
import json
import os
import sys

import numpy as np
import pandas as pd

DATA = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
O = "backtest/resultsExplore/confirmA"
W0, W1 = "2023-01-03", "2026-08-24"
CLUES = ["F09+F17", "F11+F13", "F09+F13", "F06+F11", "F04+F18"]


def med(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return x[n // 2] if n % 2 else (x[n // 2 - 1] + x[n // 2]) / 2.0


def z0050():
    cal = pd.read_csv(os.path.join(DATA, "meta", "calendar_twse.csv"))["date"].astype(str).str[:10].tolist()
    assert "2026-09-25" not in cal
    px = pd.read_csv(os.path.join(DATA, "stocks", "0050.csv"), dtype=str).drop_duplicates("date").set_index("date")["close"].astype(float)
    adj = pd.read_csv(os.path.join(DATA, "adj", "0050.csv"), dtype=str).sort_values("date")
    ev = list(zip(adj["date"].str[:10], adj["cum_factor"].astype(float)))
    c, last = [], np.nan
    for d in cal:
        f = next((cf for ed, cf in ev if ed > d), 1.0)
        v = px.get(d, np.nan)
        if np.isfinite(v) and v > 0:
            last = v * f
        c.append(last)
    c = np.array(c); i0, i1 = cal.index(W0), cal.index(W1)
    seg = c[i0:i1 + 1] / c[i0]
    return seg[-1] ** (245.0 / len(seg)) - 1, float((seg / np.maximum.accumulate(seg) - 1).min())


def main():
    os.chdir(os.path.expanduser("~/tw-p17"))
    fails = []
    S = pd.read_csv(os.path.join(O, "seeds.csv"), dtype={"cell": str}, float_precision="round_trip")
    C = pd.read_csv(os.path.join(O, "cells.csv"), dtype={"cell": str}, float_precision="round_trip").set_index("cell")
    J = json.load(open(os.path.join(O, "summary.json"), encoding="utf-8"))
    a50, d50 = z0050(); r50 = a50 / abs(d50)
    e = max(abs(a50 - J["0050同窗"]["年化"]), abs(d50 - J["0050同窗"]["回落"]))
    print(f"① 0050 窗 A 自算 年化 {a50:+.6%} 回落 {d50:+.6%} 比值 {r50:.6f}｜主程式差 {e:.1e}")
    if e > 1e-9:
        fails.append("0050")
    dmax, lab_ok = 0.0, True
    for k in CLUES + ["S0", "W1ref", "W1full"]:
        g = S[S["cell"] == k]
        n = 1000 if k == "S0" else 200
        if sorted(g["seed"]) != list(range(102000, 102000 + n)):
            fails.append(f"種子集 {k}")
        A, D = med(g["cagr"]), med(g["mdd"]); ratio = A / abs(D)
        lab = ("Q" if ratio >= r50 else "R") if A > a50 else "F"
        dmax = max(dmax, abs(A - C.loc[k, "A"]), abs(D - C.loc[k, "D"]), abs(ratio - C.loc[k, "ratio"]))
        if k in CLUES:
            lab_ok &= lab == C.loc[k, "label"]
        print(f"   {k:<8} A {A:+.4%} D {D:+.4%} 比值 {ratio:.4f} 標籤 {lab}")
    print(f"② 中位與比值最大差 {dmax:.1e}｜線索標籤全同 {lab_ok}")
    if dmax > 1e-12 or not lab_ok:
        fails.append("逐格")
    s0 = S[S["cell"] == "S0"]
    p = float(((s0["cagr"] > a50) & (s0["cagr"] / s0["mdd"].abs() >= r50)).mean())
    js = J["S0"]
    ok3 = abs(p - js["合格比例p（逐顆）"]) < 1e-15 and abs(5 * p - js["純運氣預期合格條數5p"]) < 1e-12 and (p >= 0.05) == js["p≥5%⇒⚠"]
    print(f"③ S0 p {p:.4f}（5p {5 * p:.2f}；⚠ {p >= 0.05}）與 summary 相同 {ok3}")
    if not ok3:
        fails.append("S0 p")
    print("查核結果：" + ("✅ 全部一致" if not fails else f"⛔ {fails}"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
