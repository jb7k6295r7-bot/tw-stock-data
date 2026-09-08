"""合成資料自我測試：每種型態造一段「教科書」序列，確認偵測器在預期那一天發訊號，且不在別處亂發。

    python3 -m backtest.selftest_patterns
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from . import patterns as P
from . import evaluate as E
from . import data as D

N = 700
rng = np.random.default_rng(0)


def base_frame(close: np.ndarray, volume: np.ndarray | None = None, spread: float = 0.005, index=None):
    n = len(close)
    o = close * (1 - spread)
    h = np.maximum(o, close) * (1 + spread)
    l = np.minimum(o, close) * (1 - spread)
    v = np.full(n, 1_000_000.0) if volume is None else volume
    idx = pd.bdate_range("2015-01-05", periods=n) if index is None else index
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": close, "volume": v}, index=idx)
    df["traded"] = True
    return df


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    return cond


def t_box_breakout():
    c = np.full(N, 100.0)
    c[:200] += rng.normal(0, 0.3, 200)          # 平盤
    v = np.full(N, 1_000_000.0)
    t = 200
    c[t] = 105.0; v[t] = 4_000_000                # 突破 +5%，量 4 倍
    c[t + 1] = 105.5; c[t + 2] = 106.0            # 站穩兩日
    c[t + 3:] = 106.0
    f = P.Frame(base_frame(c, v), set())
    s = P.box_breakout(f)
    ok = check("P1 箱型突破：在 t 發訊號、進場 t+3", len(s) == 1 and s[0]["signal_pos"] == t and s[0]["entry_pos"] == t + 3, f"{[(x['signal_pos'], x['entry_pos']) for x in s]}")
    # 3 天法則：箱頂在前一天才設 → 不算
    c2 = c.copy(); c2[t - 1] = 104.0
    s2 = P.box_breakout(P.Frame(base_frame(c2, v), set()))
    ok &= check("P1 3 天法則：箱頂在 t−1 才設 → 無訊號", len(s2) == 0)
    # 無量 → 不算
    v3 = v.copy(); v3[t] = 1_500_000
    ok &= check("P1 無量突破 → 無訊號", len(P.box_breakout(P.Frame(base_frame(c, v3), set()))) == 0)
    return ok


def t_gap_and_false():
    c = np.full(N, 100.0) + rng.normal(0, 0.3, N)
    v = np.full(N, 1_000_000.0)
    t = 300
    df = base_frame(c, v)
    # 真缺口：低點 > 前高×1.01，收在箱頂上，帶量
    df.iloc[t, df.columns.get_loc("open")] = 104
    df.iloc[t, df.columns.get_loc("low")] = 103.5
    df.iloc[t, df.columns.get_loc("high")] = 106
    df.iloc[t, df.columns.get_loc("close")] = 105.5
    df.iloc[t, df.columns.get_loc("volume")] = 4_000_000
    f = P.Frame(df, set())
    s = P.breakaway_gap(f)
    ok = check("P2 突破缺口：在 t 發訊號", len(s) == 1 and s[0]["signal_pos"] == t, f"{[x['signal_pos'] for x in s]}")
    ok &= check("P2 除權息日不算", len(P.breakaway_gap(P.Frame(df, {df.index[t]}))) == 0)
    # 假突破：跳空高開、爆量、長上影、收回箱內
    df2 = base_frame(c, v)
    df2.iloc[t, df2.columns.get_loc("open")] = 103
    df2.iloc[t, df2.columns.get_loc("high")] = 110
    df2.iloc[t, df2.columns.get_loc("low")] = 99.5
    df2.iloc[t, df2.columns.get_loc("close")] = 100.0   # 實體 3、上影 7 ≥ 2×3
    df2.iloc[t, df2.columns.get_loc("volume")] = 4_000_000
    s3 = P.false_breakout(P.Frame(df2, set()))
    ok &= check("P3 假突破：在 t 發空方訊號", len(s3) == 1 and s3[0]["signal_pos"] == t and s3[0]["direction"] == -1)
    return ok


def t_shadows():
    c = np.full(N, 110.0)
    t = 400
    c[t - 11:t] = np.linspace(110, 100, 11)      # 前 10 日跌 9% → 錘子
    c[t:] = 100.0
    df = base_frame(c)
    df.iloc[t, df.columns.get_loc("open")] = 100.5
    df.iloc[t, df.columns.get_loc("close")] = 101.5   # 實體 1
    df.iloc[t, df.columns.get_loc("high")] = 101.8    # 上影 0.3 ≤ 實體
    df.iloc[t, df.columns.get_loc("low")] = 98.0      # 下影 2.5 ≥ 2×1
    s = P.shadow_patterns(P.Frame(df, set()))
    hm = [x for x in s if x["pattern"] == "P4_hammer" and x["signal_pos"] == t]
    ok = check("P4 錘子：下跌段中出現", len(hm) == 1)
    c2 = np.full(N, 100.0)
    c2[t - 11:t] = np.linspace(100, 111, 11)     # 前 10 日漲 11% → 射擊之星
    c2[t:] = 111.0
    df2 = base_frame(c2)
    df2.iloc[t, df2.columns.get_loc("open")] = 111.5
    df2.iloc[t, df2.columns.get_loc("close")] = 110.5
    df2.iloc[t, df2.columns.get_loc("high")] = 114.0  # 上影 2.5
    df2.iloc[t, df2.columns.get_loc("low")] = 110.2   # 下影 0.3
    s2 = P.shadow_patterns(P.Frame(df2, set()))
    st = [x for x in s2 if x["pattern"] == "P4_shooting_star" and x["signal_pos"] == t]
    ok &= check("P4 射擊之星：上漲段中出現、方向為空", len(st) == 1 and st[0]["direction"] == -1)
    # 十字線：實體 < 10% 全長 → 不算
    df3 = df.copy()
    df3.iloc[t, df3.columns.get_loc("close")] = 100.55
    s3 = P.shadow_patterns(P.Frame(df3, set()))
    ok &= check("P4 十字線排除", not any(x["signal_pos"] == t for x in s3))
    return ok


def t_ma_cross():
    c = np.full(N, 100.0) + rng.normal(0, 0.15, N)   # 橫盤收斂，三線貼合
    v = np.full(N, 1_000_000.0)
    t = 300
    c[t - 6:t] = 99.7                                # 訊號前 MA5 壓在 MA10/20 之下
    c[t:] = 100 + np.arange(N - t) * 0.6             # 開始上漲
    v[t:] = 1_800_000
    s = P.ma_cross_up(P.Frame(base_frame(c, v), set()))
    pos = [x["signal_pos"] for x in s]
    ok = check("P5 底穿上：上漲起點附近一次訊號", len(pos) >= 1 and all(t <= p_ <= t + 5 for p_ in pos), f"{pos}")
    return ok


def synth_cup(handle_break_mid=False):
    """前置漲 40% → 左杯口 → U 型 20% 深、120 日 → 右杯口 → 柄 15 日回 6% → 放量突破。"""
    pre = np.linspace(100, 140, 130)
    x = np.linspace(-1, 1, 121)
    cup = 140 - 28 * (1 - x ** 2) ** 0.5 * 1.0       # 半圓，底 112（深 20%）
    cup = 140 - 28 * np.sqrt(np.clip(1 - x ** 2, 0, 1))
    handle_low = 140 * 0.94 if not handle_break_mid else 120.0
    handle = np.linspace(139, handle_low, 8).tolist() + np.linspace(handle_low, 138, 8).tolist()[1:]
    after = np.linspace(143, 160, 60)
    c = np.concatenate([np.full(300, 100.0), pre, cup, handle, [143.0], after])
    n = len(c)
    v = np.full(n, 1_000_000.0)
    hs = 300 + 130 + 121
    v[hs:hs + len(handle)] = 600_000                  # 柄量縮
    t = hs + len(handle)                              # 突破日
    v[t] = 2_000_000
    return c, v, t


def t_cup():
    c, v, t = synth_cup()
    f = P.Frame(base_frame(c, v), set())
    s = P.cup_handle(f)
    ok = check("P6 杯柄：突破日發訊號", len(s) == 1 and s[0]["signal_pos"] == t, f"{[(x['signal_pos'], x.get('cup_len'), x.get('handle_len'), round(x.get('depth', 0), 3)) for x in s]}")
    if s:
        ok &= check("P6 深度／U 型／柄長合理", 0.12 <= s[0]["depth"] <= 0.33 and s[0]["u_frac"] >= 0.2 and 5 <= s[0]["handle_len"] <= 30,
                    f"depth={s[0]['depth']:.3f} u={s[0]['u_frac']:.2f} handle={s[0]['handle_len']}")
    c2, v2, t2 = synth_cup(handle_break_mid=True)
    s2 = P.cup_handle(P.Frame(base_frame(c2, v2), set()))
    ok &= check("P6 柄跌破杯中點 → 型態失效、無訊號", len(s2) == 0, f"{[x['signal_pos'] for x in s2]}")
    v3 = v.copy(); v3[t] = 1_100_000
    ok &= check("P6 突破無量（< 50 日均量×1.4）→ 無訊號", len(P.cup_handle(P.Frame(base_frame(c, v3), set()))) == 0)
    # V 型：杯身改成尖底
    x = np.linspace(-1, 1, 121); vcup = 140 - 28 * (1 - np.abs(x))
    c4 = c.copy(); c4[430:551] = vcup
    ok &= check("P6 V 型（底部停留不足）→ 無訊號", len(P.cup_handle(P.Frame(base_frame(c4, v), set()))) == 0)
    return ok


def t_adjust_and_exit():
    # 還原因子：事件日嚴格大於 d 才乘
    dates = pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-06"])
    adj = pd.DataFrame({"date": pd.to_datetime(["2020-01-03"]), "cum_factor": [0.9]})
    F = D.cum_factor_series(dates, adj)
    ok = check("還原因子：事件日前乘 0.9，事件日當天與之後為 1", list(F) == [0.9, 1.0, 1.0], f"{F}")
    # 固定持有：第 20 日收盤
    c = np.arange(1, 101, dtype=float)
    df = base_frame(c)
    f = P.Frame(df, set())
    arr = {"o": f.o, "h": f.h, "l": f.l, "c": f.c, "prev_c": f.prev_c, "atr14": f.atr14}
    e = E.hold_exit(arr, 10)
    ok &= check("固定持有：進場位置 10 → 出場位置 29（第 20 天）", e[0] == 29, f"{e}")
    # 跌停鎖死順延
    df2 = df.copy()
    i = 29
    df2.iloc[i, df2.columns.get_loc("high")] = df2["close"].iloc[i - 1] * 0.9
    df2.iloc[i, df2.columns.get_loc("low")] = df2["close"].iloc[i - 1] * 0.9
    df2.iloc[i, df2.columns.get_loc("close")] = df2["close"].iloc[i - 1] * 0.9
    f2 = P.Frame(df2, set())
    arr2 = {"o": f2.o, "h": f2.h, "l": f2.l, "c": f2.c, "prev_c": f2.prev_c, "atr14": f2.atr14}
    ok &= check("跌停鎖死 → 順延一天", E.hold_exit(arr2, 10)[0] == 30)
    # 非重疊筆數
    sig = pd.DataFrame({"stock_id": ["A"] * 4 + ["B"], "entry_pos": [0, 5, 25, 30, 0], "x": [1.0] * 5})
    ok &= check("非重疊筆數：A 4 筆相隔 0/5/25/30 → 2，B 1 → 共 3", E.nonoverlap_count(sig) == 3)
    return ok


if __name__ == "__main__":
    results = [t_box_breakout(), t_gap_and_false(), t_shadows(), t_ma_cross(), t_cup(), t_adjust_and_exit()]
    print(f"\n{sum(results)}/{len(results)} 組通過")
    sys.exit(0 if all(results) else 1)
