"""出場、成本、統計。對應 backtest/PREREG.md 第三～五節。"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

COST = 0.00585          # 來回：手續費 0.1425%×2 ＋ 證交稅 0.3%
HOLD = 20               # 固定持有：進場日算第 1 天，第 20 天收盤出場
ATR_X = 2.0
ATR_CAP = 120
TARGET_WINDOW = 120
DEFER_MAX = 10          # 跌停鎖死順延上限


def _limit_down_locked(o, h, l, c, prev_c, i) -> bool:
    return (not np.isnan(h[i])) and h[i] == l[i] and (not np.isnan(prev_c[i])) and c[i] <= prev_c[i] * 0.905


def _next_tradable_open(o, i, n):
    """從 i 起第一個有開盤價的日子。"""
    j = i
    while j < n and np.isnan(o[j]):
        j += 1
    return j if j < n else None


def hold_exit(arr: dict, entry: int):
    """固定持有 20 日；出場日鎖跌停則順延。回傳 (exit_pos, exit_price) 或 None。"""
    o, h, l, c, pc = arr["o"], arr["h"], arr["l"], arr["c"], arr["prev_c"]
    n = len(c)
    e = entry + HOLD - 1
    if e >= n:
        return None
    j = e
    k = 0
    while j < n and (np.isnan(c[j]) or _limit_down_locked(o, h, l, c, pc, j)) and k < DEFER_MAX:
        j += 1; k += 1
    if j >= n or np.isnan(c[j]):
        # 20 日內就沒有可成交日：用視窗內最後一個收盤
        seg = c[entry:e + 1]
        if np.isnan(seg).all():
            return None
        j = entry + int(np.flatnonzero(~np.isnan(seg))[-1])
    return j, c[j]


def atr_trail_exit(arr: dict, entry: int, direction: int = 1):
    """2×ATR 追蹤停損：停損線 ＝ 進場後最高收盤 − 2×ATR14（逐日更新），只升不降；收盤跌破 → 次日開盤出場；最長 120 日。
    空方（direction=−1）鏡像：進場後最低收盤 ＋ 2×ATR，只降不升；收盤突破 → 出場。"""
    o, c, atr = arr["o"], arr["c"] * direction, arr["atr14"]
    n = len(c)
    hi = -np.inf
    stop = -np.inf
    last = min(n - 1, entry + ATR_CAP - 1)
    for i in range(entry, last + 1):
        if np.isnan(c[i]):
            continue
        if c[i] > hi:
            hi = c[i]
        a = atr[i]
        if not np.isnan(a):
            stop = max(stop, hi - ATR_X * a)
        if c[i] < stop:
            j = _next_tradable_open(o, i + 1, n)
            if j is None:
                return i, c[i] * direction, True, i - entry + 1
            return j, o[j], True, j - entry + 1
    # 到期：最後一個有收盤的日子
    seg = c[entry:last + 1]
    if np.isnan(seg).all():
        return None
    j = entry + int(np.flatnonzero(~np.isnan(seg))[-1])
    return j, c[j] * direction, False, j - entry + 1


def level_stop_exit(arr: dict, entry: int, stop_level: float):
    """技術式固定停損（不上移）：收盤 < stop_level → 次日開盤出場；否則 20 日固定持有出場。"""
    o, c = arr["o"], arr["c"]
    n = len(c)
    e = entry + HOLD - 1
    for i in range(entry, min(n, e + 1)):
        if not np.isnan(c[i]) and c[i] < stop_level:
            j = _next_tradable_open(o, i + 1, n)
            if j is None:
                return i, c[i], True
            return j, o[j], True
    r = hold_exit(arr, entry)
    if r is None:
        return None
    return r[0], r[1], False


def targets_hit(arr: dict, entry: int, levels: dict[str, float]) -> dict[str, bool]:
    h = arr["h"]
    seg = h[entry:entry + TARGET_WINDOW]
    mx = np.nanmax(seg) if len(seg) and not np.isnan(seg).all() else np.nan
    return {k: bool(mx >= v) if not np.isnan(mx) else False for k, v in levels.items()}


def evaluate_signal(arr: dict, bench: dict, sig: dict) -> dict | None:
    """一筆訊號的所有出場模式。回傳附加欄位；進場日沒有開盤價 → None。"""
    o = arr["o"]
    entry = sig["entry_pos"]
    n = len(o)
    if entry >= n or np.isnan(o[entry]):
        return None
    ep = o[entry]
    d = sig["direction"]
    r = {"entry_price": ep}
    he = hold_exit(arr, entry)
    if he is None:
        return None
    r["exit_pos_hold"] = he[0]
    gross = he[1] / ep - 1
    r["ret_hold_gross"] = gross
    r["ret_hold_net"] = gross - COST
    r["ret_hold_signed"] = d * gross - COST
    # 0050 同窗
    bo, bc = bench["o"], bench["c"]
    if not np.isnan(bo[entry]) and not np.isnan(bc[he[0]]):
        r["bench_hold"] = bc[he[0]] / bo[entry] - 1
    else:
        r["bench_hold"] = np.nan
    ae = atr_trail_exit(arr, entry, d)
    if ae is not None:
        r["ret_atr_net"] = ae[1] / ep - 1 - COST
        r["ret_atr_signed"] = d * (ae[1] / ep - 1) - COST
        r["atr_stopped"] = ae[2]
        r["atr_days"] = ae[3]
    if sig["pattern"].startswith("P6"):
        depth_px = sig["cup_L"] - sig["cup_B"]
        levels = {"tgt_half": ep + 0.5 * depth_px, "tgt_full": ep + depth_px, "tgt_pct": ep * sig["cup_L"] / sig["cup_B"]}
        r.update(targets_hit(arr, entry, levels))
        s1 = level_stop_exit(arr, entry, sig["handle_low"])
        if s1 is not None:
            r["ret_stop_handle_net"] = s1[1] / ep - 1 - COST
            r["stop_handle_hit"] = s1[2]
        s2 = level_stop_exit(arr, entry, ep * 0.92)
        if s2 is not None:
            r["ret_stop_8pct_net"] = s2[1] / ep - 1 - COST
            r["stop_8pct_hit"] = s2[2]
    return r


def nonoverlap_count(df: pd.DataFrame, gap: int = HOLD) -> int:
    """同檔訊號相隔 < gap 日者合併計 1 筆（貪婪）。"""
    cnt = 0
    for _, g in df.groupby("stock_id"):
        last = -10 ** 9
        for e in np.sort(g["entry_pos"].to_numpy()):
            if e - last >= gap:
                cnt += 1
                last = e
    return cnt


def stats(df: pd.DataFrame, col: str, baseline: float = 0.0) -> dict:
    x = df[col].dropna().to_numpy(float)
    n = len(x)
    if n == 0:
        return {"n": 0}
    n_no = nonoverlap_count(df.loc[df[col].notna()])
    mean = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    se = sd / math.sqrt(max(1, n_no)) if n > 1 else float("nan")
    wins = x[x > 0]; losses = x[x <= 0]
    wr = len(wins) / n
    return {
        "n": n, "n_nonoverlap": n_no, "overlap_pct": 1 - n_no / n,
        "mean": mean, "median": float(np.median(x)), "sd": sd, "se": se,
        "ci_lo": mean - 1.96 * se, "ci_hi": mean + 1.96 * se,
        "excess": mean - baseline,
        "excess_ci_lo": mean - baseline - 1.96 * se, "excess_ci_hi": mean - baseline + 1.96 * se,
        "win_rate": wr,
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "best": float(x.max()), "worst": float(x.min()),
        "pct_gt20": float((x > 0.20).mean()),
    }


def baseline_returns(arr: dict, gate: np.ndarray, lo: int, hi: int, cond: np.ndarray | None = None) -> np.ndarray:
    """母體基準：每個通過閘門的股票日 d，次日開盤進、第 20 日收盤出，扣成本。位置 lo..hi 為訊號日範圍。
    cond：額外的條件（例：前 10 日跌 ≥ 5%），給條件式控制組用。"""
    o, c = arr["o"], arr["c"]
    n = len(c)
    idx = np.arange(max(lo, 0), min(hi, n - HOLD - 1) + 1)
    idx = idx[gate[idx]]
    if cond is not None:
        idx = idx[cond[idx]]
    if len(idx) == 0:
        return np.empty(0)
    ep = o[idx + 1]
    xp = c[idx + HOLD]
    r = xp / ep - 1 - COST
    return r[~np.isnan(r)]
