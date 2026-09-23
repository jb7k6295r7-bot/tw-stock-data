"""T1 附：診斷 P5（召回 56%）與 P3（召回 62–69%）漏在哪裡。

⛔ 不猜。對每一次漏掉的試驗，逐條檢查偵測器的每一個子條件，統計是哪一條擋掉的。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-stock-data"))
from backtest import patterns as P   # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t1_synth import GENS, TIERS, _frame   # noqa: E402

TRIALS = 300


def diag_p5(rs, ar, rr):
    c, o, h, l, v, S = GENS["P5_ma_cross_up"][0](rs, ar, rr)
    f = _frame(c, o, h, l, v)
    p = f.p
    hi = np.maximum(f.ma10, f.ma20)
    hi_prev = np.roll(hi, 1)
    ma5_prev = np.roll(f.ma5, 1)
    top = np.maximum(f.ma5, hi)
    bot = np.minimum(f.ma5, np.minimum(f.ma10, f.ma20))
    with np.errstate(invalid="ignore"):
        spread = (top - bot) / f.c
    conv = pd.Series(spread).rolling(20, min_periods=20).mean().shift(1).to_numpy(float)
    return {
        "上穿(ma5>上軌)": bool(f.ma5[S] > hi[S]),
        "前一日未上穿": bool(ma5_prev[S] <= hi_prev[S]),
        "糾結(conv<=3%)": bool(conv[S] <= p["ma_conv_max"]),
        "放量(>=1.5x)": bool(f.v[S] >= p["ma_vol_x"] * f.vol_ma20[S]),
        "閘門": bool(f.gate[S]),
    }, S, f, hi, ma5_prev, hi_prev


def diag_p3(rs, ar, rr):
    c, o, h, l, v, S = GENS["P3_false_breakout"][0](rs, ar, rr)
    f = _frame(c, o, h, l, v)
    p = f.p
    return {
        "箱型OK": bool(f.box_ok()[S]),
        "開高(>前高1%)": bool(f.o[S] > f.prev_h[S] * (1 + p["gap_min"])),
        "放量(>=3x)": bool(f.v[S] >= p["breakout_vol_x"] * f.vol_ma20[S]),
        "長上影(>=2x實體)": bool(f.upper[S] >= p["shadow_x"] * f.body[S]),
        "高過箱頂": bool(f.h[S] > f.box_top[S]),
        "收在箱內": bool(f.c[S] < f.box_top[S]),
        "閘門": bool(f.gate[S]),
    }, S, f


print("=== P5_ma_cross_up：{} 次試驗，逐條子條件的【不成立】次數 ===".format(TRIALS))
for tier, (ar, rr) in TIERS.items():
    rs = np.random.default_rng(20260923)
    fails = {}
    shift = []
    for _ in range(TRIALS):
        d, S, f, hiarr, ma5p, hip = diag_p5(rs, ar, rr)
        for k, ok in d.items():
            if not ok:
                fails[k] = fails.get(k, 0) + 1
        if not d["前一日未上穿"]:
            # 真正的上穿日跑到哪去了
            cross = np.flatnonzero((f.ma5[1:] > hiarr[1:]) & (ma5p[1:] <= hip[1:])) + 1
            near = cross[(cross > S - 15) & (cross <= S)]
            if len(near):
                shift.append(int(S - near[-1]))
    print("  [{}]".format(tier))
    for k, n in sorted(fails.items(), key=lambda x: -x[1]):
        print("     {:<18} 不成立 {:>3} 次（{:.1%}）".format(k, n, n / TRIALS))
    if shift:
        print("     ⇒ ⭐ 真正的上穿日比預期【早】了 {:.1f} 日（中位），範圍 {}~{} 日".format(
            float(np.median(shift)), min(shift), max(shift)))

print()
print("=== P3_false_breakout：{} 次試驗 ===".format(TRIALS))
for tier, (ar, rr) in TIERS.items():
    rs = np.random.default_rng(20260923)
    fails = {}
    for _ in range(TRIALS):
        d, S, f = diag_p3(rs, ar, rr)
        for k, ok in d.items():
            if not ok:
                fails[k] = fails.get(k, 0) + 1
    print("  [{}]".format(tier))
    for k, n in sorted(fails.items(), key=lambda x: -x[1]):
        print("     {:<18} 不成立 {:>3} 次（{:.1%}）".format(k, n, n / TRIALS))
    if not fails:
        print("     （訊號日本身每一條都成立 ⇒ 漏掉的原因在別處）")
