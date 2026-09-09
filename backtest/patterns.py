"""六種型態的機器定義。每個偵測器吃一個 Frame，吐訊號列表。

所有門檻與 backtest/PREREG.md 第二節一一對應；標 ［本研究補］ 的參數放在 PARAMS，方便跑敏感度。
訊號欄位：signal_pos（訊號日在日曆上的位置）、entry_pos（進場日：開盤價）、direction（+1 多／−1 空）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PARAMS = {
    "box_window": 20,        # P1/P2/P3 箱型視窗（訊號日前 N 日）
    "box_range_max": 0.20,   # 箱型高度上限
    "box_top_min_age": 3,    # 3 天法則：箱頂距訊號日至少幾天
    "breakout_pct": 0.03,    # 真突破幅度
    "breakout_vol_x": 3.0,   # 突破量 ＝ N × 20 日均量
    "confirm_days": 2,       # 站穩：訊號日之後再 N 日收盤在箱頂上
    "gap_min": 0.01,         # 缺口最小幅度
    "shadow_x": 2.0,         # 影線 ÷ 實體
    "body_min_frac": 0.10,   # 實體佔全長最小比例（排除十字線）
    "trend_days": 10,        # 影線型態的前段趨勢天數
    "trend_pct": 0.05,       # 前段趨勢幅度
    "ma_conv_max": 0.03,     # 底穿上：三條均線平均張口上限
    "ma_vol_x": 1.5,         # 底穿上：放量門檻
    "liq_min_shares": 500_000,  # 流動性：20 日均量 ≥ 500 張
    "liq_mode": "shares",       # "shares"（主表）｜"amount"（並列母體：近 20 日成交金額均值 ≥ 5,000 萬，PREREG 更正五）
    "liq_min_amount": 50_000_000,
    # 杯柄
    "cup_prior_rise": 1.30,
    "cup_len": (35, 325),
    "cup_depth": (0.12, 0.33),
    "rim_ratio": (0.92, 1.08),
    "half_min": 15,
    "u_frac": 0.35,   # 2026-09-08 更正：0.20 擋不掉直線 V 型（見 PREREG 更正一）
    "u_zone": 0.25,
    "handle_len": (5, 30),
    "handle_vol_x": 1.4,     # Kuhn：≥ 50 日均量 + 40%
    "pivot_k": 5,
    "cup_lookbacks": (325, 200, 120, 60),
    "prior_lookback": 120,
}


def max_lookback(p: dict = PARAMS) -> int:
    """訊號日往回看最遠幾個交易日（給斷點視窗的 L 用，不要寫死）。
    最長的是杯柄：杯身 ≤ max(cup_lookbacks) ＋ 左杯緣之前的 prior_lookback ＋ 柄 ≤ handle_len[1] ＋ 樞紐確認 pivot_k；
    其餘偵測器（箱型 20、均量 50、趨勢 10）與研究二的 240 日 RS 都比它短。"""
    cup = max(p["cup_lookbacks"]) + p["prior_lookback"] + p["handle_len"][1] + p["pivot_k"]
    return max(cup, p["box_window"] + p["confirm_days"], 50, 240)


class Frame:
    """一檔的日曆對齊陣列與共用指標。序列有洞（NaN）時，rolling 以 min_periods=window 讓洞傳染。"""

    def __init__(self, df: pd.DataFrame, event_dates: set, p: dict = PARAMS):
        self.p = p
        self.index = df.index
        self.o = df["open"].to_numpy(float)
        self.h = df["high"].to_numpy(float)
        self.l = df["low"].to_numpy(float)
        self.c = df["close"].to_numpy(float)
        self.v = df["volume"].to_numpy(float)
        self.n = len(self.c)
        self.is_event = np.isin(self.index.values, np.array(sorted(event_dates), dtype="datetime64[ns]")) if event_dates else np.zeros(self.n, bool)

        s = df
        W = p["box_window"]
        body_top = np.maximum(self.o, self.c)
        body_bot = np.minimum(self.o, self.c)
        self.body_top, self.body_bot = body_top, body_bot
        self.body = np.abs(self.c - self.o)
        self.upper = self.h - body_top
        self.lower = body_bot - self.l
        vol = s["volume"]
        self.vol_ma20 = vol.rolling(20, min_periods=20).mean().shift(1).to_numpy(float)
        self.vol_ma50 = vol.rolling(50, min_periods=50).mean().shift(1).to_numpy(float)
        bt = pd.Series(body_top, index=s.index)
        bb = pd.Series(body_bot, index=s.index)
        self.box_top = bt.rolling(W, min_periods=W).max().shift(1).to_numpy(float)
        self.box_bot = bb.rolling(W, min_periods=W).min().shift(1).to_numpy(float)
        # 3 天法則：箱頂不能是視窗最後 (age-1) 天設的 → max over [t-W, t-age] == box_top
        age = p["box_top_min_age"]
        self.box_top_old = bt.rolling(W - age + 1, min_periods=W - age + 1).max().shift(age).to_numpy(float)
        close = s["close"]
        self.ma5 = close.rolling(5, min_periods=5).mean().to_numpy(float)
        self.ma10 = close.rolling(10, min_periods=10).mean().to_numpy(float)
        self.ma20 = close.rolling(20, min_periods=20).mean().to_numpy(float)
        self.prev_c = close.shift(1).to_numpy(float)
        self.prev_h = s["high"].shift(1).to_numpy(float)
        # 閘門：前 20 日（含當日）皆有成交
        self.full20 = s["traded"].astype(int).rolling(20, min_periods=20).sum().to_numpy(float) == 20
        if p.get("liq_mode", "shares") == "amount":
            # 情報分析 09:55 的定義：近 20 個交易日（T−20～T−1，不含當日）成交金額算術平均 ≥ 5,000 萬元，
            # 交易日以日曆為準、沒成交的日子記 0 一起平均（不跳過）。
            amt = s["amount"].fillna(0.0) if "amount" in s else pd.Series(np.nan, index=s.index)
            self.amt_ma20 = amt.rolling(20, min_periods=20).mean().shift(1).to_numpy(float)
            self.liquid = self.amt_ma20 >= p["liq_min_amount"]
        else:
            self.liquid = self.vol_ma20 >= p["liq_min_shares"]
        self.gate = self.full20 & self.liquid
        # ATR14（用還原開高低收）
        tr = np.maximum(self.h - self.l, np.maximum(np.abs(self.h - self.prev_c), np.abs(self.l - self.prev_c)))
        self.atr14 = pd.Series(tr, index=s.index).rolling(14, min_periods=14).mean().to_numpy(float)

    def box_ok(self) -> np.ndarray:
        with np.errstate(invalid="ignore"):
            rng = (self.box_top - self.box_bot) / self.box_top
        return (rng <= self.p["box_range_max"]) & (self.box_top_old >= self.box_top)  # 等號：箱頂在舊段裡


def _sig(pattern, pos, entry, direction, **extra):
    d = {"pattern": pattern, "signal_pos": int(pos), "entry_pos": int(entry), "direction": direction}
    d.update(extra)
    return d


def box_breakout(f: Frame) -> list[dict]:
    p = f.p
    out = []
    with np.errstate(invalid="ignore"):
        cond = (f.gate & f.box_ok()
                & (f.c > f.box_top * (1 + p["breakout_pct"]))
                & (f.v >= p["breakout_vol_x"] * f.vol_ma20))
    k = p["confirm_days"]
    for t in np.flatnonzero(cond):
        if t + k + 1 >= f.n:
            continue
        seg = f.c[t + 1:t + k + 1]
        if np.isnan(seg).any() or not (seg > f.box_top[t]).all():
            continue
        out.append(_sig("P1_box_breakout", t, t + k + 1, +1,
                        box_top=f.box_top[t], vol_x=f.v[t] / f.vol_ma20[t],
                        breakout_pct=f.c[t] / f.box_top[t] - 1))
    return out


def breakaway_gap(f: Frame) -> list[dict]:
    p = f.p
    out = []
    with np.errstate(invalid="ignore"):
        cond = (f.gate & f.box_ok()
                & (f.l > f.prev_h * (1 + p["gap_min"]))
                & (f.v >= p["breakout_vol_x"] * f.vol_ma20)
                & (f.c > f.box_top) & ~f.is_event)
    for t in np.flatnonzero(cond):
        if t + 1 >= f.n:
            continue
        seg = f.c[t + 1:t + 6]
        filled = bool(np.nanmin(seg) <= f.prev_h[t]) if len(seg) and not np.isnan(seg).all() else np.nan
        out.append(_sig("P2_breakaway_gap", t, t + 1, +1,
                        gap_pct=f.l[t] / f.prev_h[t] - 1, vol_x=f.v[t] / f.vol_ma20[t], filled_5d=filled))
    return out


def false_breakout(f: Frame) -> list[dict]:
    p = f.p
    out = []
    with np.errstate(invalid="ignore"):
        cond = (f.gate & f.box_ok()
                & (f.o > f.prev_h * (1 + p["gap_min"]))
                & (f.v >= p["breakout_vol_x"] * f.vol_ma20)
                & (f.upper >= p["shadow_x"] * f.body)
                & (f.h > f.box_top) & (f.c < f.box_top))
    for t in np.flatnonzero(cond):
        if t + 1 >= f.n:
            continue
        out.append(_sig("P3_false_breakout", t, t + 1, -1,
                        vol_x=f.v[t] / f.vol_ma20[t], shadow_x=f.upper[t] / f.body[t] if f.body[t] > 0 else np.inf))
    return out


def shadow_patterns(f: Frame) -> list[dict]:
    p = f.p
    out = []
    rng = f.h - f.l
    c = pd.Series(f.c)
    trend = (c.shift(1) / c.shift(1 + p["trend_days"]) - 1).to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        body_ok = (rng > 0) & (f.body >= p["body_min_frac"] * rng)
        hammer = (f.gate & body_ok & (f.lower >= p["shadow_x"] * f.body) & (f.upper <= f.body)
                  & (trend <= -p["trend_pct"]))
        star = (f.gate & body_ok & (f.upper >= p["shadow_x"] * f.body) & (f.lower <= f.body)
                & (trend >= p["trend_pct"]))
    for t in np.flatnonzero(hammer):
        if t + 1 < f.n:
            out.append(_sig("P4_hammer", t, t + 1, +1, shadow_x=f.lower[t] / f.body[t], trend=trend[t]))
    for t in np.flatnonzero(star):
        if t + 1 < f.n:
            out.append(_sig("P4_shooting_star", t, t + 1, -1, shadow_x=f.upper[t] / f.body[t], trend=trend[t]))
    return out


def ma_cross_up(f: Frame) -> list[dict]:
    p = f.p
    out = []
    hi = np.maximum(f.ma10, f.ma20)
    hi_prev = np.roll(hi, 1); ma5_prev = np.roll(f.ma5, 1)
    hi_prev[0] = np.nan; ma5_prev[0] = np.nan
    top = np.maximum(f.ma5, hi)
    bot = np.minimum(f.ma5, np.minimum(f.ma10, f.ma20))
    with np.errstate(invalid="ignore"):
        spread = (top - bot) / f.c
    conv = pd.Series(spread).rolling(20, min_periods=20).mean().shift(1).to_numpy(float)
    with np.errstate(invalid="ignore"):
        cond = (f.gate & (f.ma5 > hi) & (ma5_prev <= hi_prev)
                & (conv <= p["ma_conv_max"]) & (f.v >= p["ma_vol_x"] * f.vol_ma20))
    for t in np.flatnonzero(cond):
        if t + 1 < f.n:
            out.append(_sig("P5_ma_cross_up", t, t + 1, +1, conv=conv[t], vol_x=f.v[t] / f.vol_ma20[t]))
    return out


def _nanargmin(a, lo):
    if np.isnan(a).all():
        return None
    return lo + int(np.nanargmin(a))


def _nanargmax(a, lo):
    if np.isnan(a).all():
        return None
    return lo + int(np.nanargmax(a))


def cup_handle(f: Frame, buy: str = "handle", u_frac: float | None = None, unit: int = 1) -> list[dict]:
    """杯柄。unit=1 日線；週線 Frame 傳 unit=5 讓所有「天數」門檻換成週數。"""
    p = f.p
    c, h, l, v = f.c, f.h, f.l, f.v
    n = f.n
    u_frac = p["u_frac"] if u_frac is None else u_frac
    k = max(1, p["pivot_k"] // unit)
    cup_lo, cup_hi = (max(1, x // unit) for x in p["cup_len"])
    half_min = max(1, p["half_min"] // unit)
    h_lo, h_hi = (max(1, x // unit) for x in p["handle_len"])
    prior_lb = max(1, p["prior_lookback"] // unit)
    lookbacks = [max(1, x // unit) for x in p["cup_lookbacks"]]
    vol_ma = f.vol_ma50 if unit == 1 else pd.Series(v).rolling(10, min_periods=10).mean().shift(1).to_numpy(float)

    # 樞紐高點：收盤 ＝ [R−k, R+k] 最高
    cs = pd.Series(c)
    roll = cs.rolling(2 * k + 1, center=True, min_periods=2 * k + 1).max().to_numpy(float)
    pivots = np.flatnonzero((c == roll) & ~np.isnan(roll))

    out = []
    last_sig = -10 ** 9
    for R in pivots:
        cR = c[R]
        found = None
        for lb in lookbacks:
            lo = max(0, R - lb)
            B = _nanargmin(c[lo:R + 1], lo)
            if B is None or B == R:
                continue
            L = _nanargmax(c[lo:B + 1], lo)
            if L is None or not (L < B):
                continue
            cL, cB = c[L], c[B]
            if B - L < half_min or R - B < half_min or not (cup_lo <= R - L <= cup_hi):
                continue
            depth = (cL - cB) / cL
            if not (p["cup_depth"][0] <= depth <= p["cup_depth"][1]):
                continue
            if not (p["rim_ratio"][0] <= cR / cL <= p["rim_ratio"][1]):
                continue
            pre = c[max(0, L - prior_lb):L + 1]
            if np.isnan(pre).all() or cL / np.nanmin(pre) < p["cup_prior_rise"]:
                continue
            seg = c[L:R + 1]
            if np.isnan(seg).mean() > 0.05:
                continue
            u = np.nanmean(seg <= cB + p["u_zone"] * (cL - cB))
            if u < u_frac:
                continue
            found = (L, B, cL, cB, depth, u)
            break
        if found is None:
            continue
        L, B, cL, cB, depth, u = found
        mid = cB + 0.5 * (cL - cB)
        vol_right = np.nanmean(v[B:R + 1])
        buy_level_cap = max(cL, cR)
        for t in range(R + h_lo + 1, min(n, R + h_hi + 2)):
            hs = slice(R + 1, t)
            if np.isnan(c[hs]).any() or np.isnan(c[t]):
                break
            hl = np.nanmin(l[hs]); hh = np.nanmax(h[hs])
            if hl <= mid:
                break                      # 柄跌破杯中點 → 型態失效
            level = hh if buy == "handle" else buy_level_cap
            if c[t] > level and v[t] >= p["handle_vol_x"] * vol_ma[t]:
                if np.nanmean(v[hs]) < vol_right and (t - R - 1) < (R - L) and f.gate[t]:
                    if t - last_sig >= max(1, 20 // unit):
                        out.append(_sig("P6_cup_handle" if buy == "handle" else "P6_cup_handle_cap", t, t + 1, +1,
                                        L=L, B=B, R=R, cup_len=R - L, handle_len=t - R - 1,
                                        depth=depth, u_frac=u, rim_ratio=cR / cL,
                                        handle_pullback_ratio=(hh - hl) / (cL - cB),
                                        handle_drop_pct=(hh - hl) / hh,
                                        cup_L=cL, cup_B=cB, handle_high=hh, handle_low=hl,
                                        vol_x=v[t] / vol_ma[t],
                                        pretty=bool((hh - hl) / (cL - cB) <= 0.33 and 0.05 <= (hh - hl) / hh <= 0.15)))
                        last_sig = t
                break                      # 突破一次就結束這個 R
    return out


DETECTORS = {
    "P1": box_breakout,
    "P2": breakaway_gap,
    "P3": false_breakout,
    "P4": shadow_patterns,
    "P5": ma_cross_up,
    "P6": cup_handle,
}
