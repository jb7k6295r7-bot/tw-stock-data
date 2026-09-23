"""T1 第②步：合成教科書型態餵進偵測器，量【召回率】。

⭐ 設計要點（⛔ 不可省）：
  1. 合成的是【教科書定義】的型態，⛔ 不是照 patterns.py 的門檻反推
     （照門檻反推 ＝ 在測「偵測器認不認得自己」，那不是召回率）
  2. 雜訊用【該市值級距實測的日波動】校準 ⇒ 直接測補件 §二 的機制 (乙)
  3. ⭐⭐ σ=0 的無雜訊版【必須抓到】，否則是產生器壞了不是偵測器壞了
     ⇒ 本檔先跑 σ=0 自我檢查，沒全過就【不報召回率】（第七點）
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-stock-data"))
from backtest import patterns as P   # noqa: E402

T1 = ("/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/"
      "C--SynologyDrive---------/57a7a54c-a515-48e2-87ab-d32197791f42/scratchpad/t1")

# 實測值（t1_vol.py）：日絕對報酬中位／日高低振幅中位
TIERS = {"市值前50": (0.008186, 0.016234), "其餘": (0.008982, 0.020930)}
N = 700
VOL_BASE = 2_000_000.0          # 通過流動性閘門（≥ 500 張）
TRIALS = 300


def _frame(c, o, h, l, v):
    idx = pd.bdate_range("2015-01-05", periods=len(c))
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v,
                       "traded": True, "amount": c * v}, index=idx)
    return P.Frame(df, set())


def _ohlc(close, rng_rel, rs):
    o = np.concatenate([[close[0]], close[:-1]]) * (1 + rs.normal(0, rng_rel / 4, len(close)))
    o[0] = close[0]
    top = np.maximum(o, close)
    bot = np.minimum(o, close)
    extra = np.maximum(0.0, rng_rel * close - (top - bot))
    up = rs.uniform(0.3, 0.7, len(close))
    return o, top + extra * up, bot - extra * (1 - up)


def _noise(n, abs_ret_med, rs):
    """局部擾動：讓日報酬中位絕對值吻合實測，又不把結構（箱型／杯型）走壞。
    平坦路徑下 ret[t] 約等於 eps[t]-eps[t-1] ~ N(0, s*sqrt2) ⇒ s = 中位/(0.6745*sqrt2)。"""
    if abs_ret_med <= 0:
        return np.zeros(n)
    return rs.normal(0, abs_ret_med / (0.6745 * np.sqrt(2)), n)


def gen_box(kind, rs, ar, rr):
    """P1 箱型突破／P2 突破缺口／P3 假突破：先整理再突破。"""
    S = 600
    c = np.empty(N)
    c[:S - 20] = 80 * np.exp(np.linspace(0, np.log(100 / 80), S - 20))
    box = np.full(20, 100.0)
    box[10] = 104.0                      # 箱頂設在第 10 天 ⇒ 滿足 3 天法則
    box[3] = 96.5
    box[16] = 96.5
    c[S - 20:S] = box
    c[S:] = 100.0
    c = c * (1 + _noise(N, ar, rs))
    v = np.full(N, VOL_BASE)
    o, h, l = _ohlc(c, rr, rs)
    btop = np.maximum(o, c)[S - 20:S].max()

    if kind == "P1":
        c[S] = btop * 1.06
        c[S + 1:S + 4] = btop * 1.07
        o[S] = btop * 1.01
    elif kind == "P2":
        l[S] = h[S - 1] * 1.03
        o[S] = l[S] * 1.005
        c[S] = max(btop * 1.04, o[S] * 1.01)
    else:
        o[S] = h[S - 1] * 1.03
        c[S] = btop * 0.98
        h[S] = btop * 1.05
        l[S] = c[S] * 0.995
    if kind != "P3":
        h[S] = max(h[S], c[S], o[S]) * 1.002
        l[S] = min(l[S], c[S], o[S]) * 0.998
    v[S] = VOL_BASE * 5
    return c, o, h, l, v, S


def gen_shadow(kind, rs, ar, rr):
    """P4 錘子／流星：前段趨勢 ＋ 一根長影線。"""
    S = 600
    c = np.full(N, 100.0)
    sign = -1 if kind == "hammer" else 1
    c[S - 11:S] = 100 * np.exp(np.linspace(0, sign * np.log(1.10), 11))
    c[S:] = c[S - 1]
    c = c * (1 + _noise(N, ar, rs))
    v = np.full(N, VOL_BASE)
    o, h, l = _ohlc(c, rr, rs)
    base = c[S - 1]
    body = base * 0.010
    if kind == "hammer":
        o[S] = base * 1.001
        c[S] = o[S] + body
        h[S] = c[S] + body * 0.5
        l[S] = o[S] - body * 3.5
    else:
        o[S] = base * 0.999
        c[S] = o[S] - body
        l[S] = c[S] - body * 0.5
        h[S] = o[S] + body * 3.5
    return c, o, h, l, v, S


def gen_ma(rs, ar, rr):
    """P5 均線糾結後上穿。"""
    S = 600
    c = np.full(N, 100.0) * (1 + _noise(N, ar, rs))
    v = np.full(N, VOL_BASE)
    o, h, l = _ohlc(c, rr, rs)
    for k in range(4):
        c[S + k] = 100 * (1.05 + 0.01 * k)
        o[S + k] = c[S + k] * 0.99
        h[S + k] = c[S + k] * 1.005
        l[S + k] = o[S + k] * 0.995
    v[S] = VOL_BASE * 2.5
    return c, o, h, l, v, S


def gen_cup(rs, ar, rr):
    """P6 杯柄：先漲 → U 型杯 → 量縮的柄 → 帶量突破。"""
    L, R, HL = 150, 370, 12
    S = R + HL + 1
    cL, cB = 100.0, 80.0
    # ⛔ 前段起漲點【必須高於杯底】，否則偵測器往回看 325 日時會把「杯底」找到前段去
    #   （第一版寫 70 起漲、杯底 80 ⇒ 無雜訊版就抓不到，是產生器的錯不是偵測器的錯）
    # ⇒ 分兩段：先在杯底之下待著（供 prior_rise 的分母），再快速升到杯底之上
    c = np.empty(N)
    c[:30] = 70.0
    c[30:46] = np.linspace(70.0, 84.0, 16)
    c[46:L + 1] = np.linspace(84.0, cL, L + 1 - 46)
    t = np.linspace(-1, 1, R - L + 1)
    c[L:R + 1] = cB + (cL - cB) * t ** 4          # 平底 U 型
    c[R + 1:S] = np.linspace(cL * 0.995, cL * 0.94, S - R - 1)
    c[S:] = cL
    c = c * (1 + _noise(N, ar, rs))
    v = np.full(N, VOL_BASE)
    v[L:R + 1] = VOL_BASE * 1.3
    v[R + 1:S] = VOL_BASE * 0.6                   # 柄要量縮
    o, h, l = _ohlc(c, rr, rs)
    hh = np.nanmax(h[R + 1:S])
    c[S] = hh * 1.03
    o[S] = hh * 1.005
    h[S] = c[S] * 1.005
    l[S] = o[S] * 0.995
    v[S] = VOL_BASE * 2.2
    return c, o, h, l, v, S


GENS = {
    "P1_box_breakout":   (lambda rs, a, r: gen_box("P1", rs, a, r), "P1"),
    "P2_breakaway_gap":  (lambda rs, a, r: gen_box("P2", rs, a, r), "P2"),
    "P3_false_breakout": (lambda rs, a, r: gen_box("P3", rs, a, r), "P3"),
    "P4_hammer":         (lambda rs, a, r: gen_shadow("hammer", rs, a, r), "P4"),
    "P4_shooting_star":  (lambda rs, a, r: gen_shadow("star", rs, a, r), "P4"),
    "P5_ma_cross_up":    (lambda rs, a, r: gen_ma(rs, a, r), "P5"),
    "P6_cup_handle":     (lambda rs, a, r: gen_cup(rs, a, r), "P6"),
}


def fire(name, det_key, rs, ar, rr):
    c, o, h, l, v, S = GENS[name][0](rs, ar, rr)
    f = _frame(c, o, h, l, v)
    sigs = P.cup_handle(f, buy="handle") if det_key == "P6" else P.DETECTORS[det_key](f)
    hits = [s for s in sigs if s["pattern"] == name]
    return any(s["signal_pos"] == S for s in hits), any(abs(s["signal_pos"] - S) <= 2 for s in hits)


def main():
    print("=== 〇 ⭐⭐ 自我檢查：無雜訊的教科書型態，偵測器【必須】抓到 ===")
    bad = []
    for name, (_, key) in GENS.items():
        e, n = fire(name, key, np.random.default_rng(0), 0.0, 0.012)
        flag = "✅ 抓到（位置準確）" if e else ("⚠ 抓到但位置偏移" if n else "⛔ 沒抓到")
        print("  {:<22} {}".format(name, flag))
        if not n:
            bad.append(name)
    if bad:
        print()
        print("⛔⛔ 無雜訊版就抓不到：{}".format("、".join(bad)))
        print("   ⇒ 那是【產生器】寫錯，不是偵測器 ⇒ ⛔ 本趟不報召回率（第七點）")
        return 1

    print()
    print("=== 一 ⭐ 召回率（每格 {} 次試驗，雜訊用該級距實測日波動校準）===".format(TRIALS))
    print()
    print("  {:<22}{:>12}{:>12}{:>12}".format("型態", "市值前50", "其餘", "前50÷其餘"))
    print("  " + "-" * 58)
    rows = []
    for name, (_, key) in GENS.items():
        rec = {}
        for tier, (ar, rr) in TIERS.items():
            rs = np.random.default_rng(20260923)
            rec[tier] = sum(fire(name, key, rs, ar, rr)[1] for _ in range(TRIALS)) / TRIALS
        ratio = (rec["市值前50"] / rec["其餘"]) if rec["其餘"] else float("nan")
        print("  {:<22}{:>11.1%}{:>12.1%}{:>12}".format(
            name, rec["市值前50"], rec["其餘"],
            "{:.2f}x".format(ratio) if ratio == ratio else "n/a（分母 0）"))
        rows.append({"pattern": name, "recall_top50": rec["市值前50"],
                     "recall_rest": rec["其餘"], "ratio": ratio})
    pd.DataFrame(rows).to_csv(os.path.join(T1, "recall.csv"), index=False)
    print()
    print("  ✅ 已寫出 recall.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
