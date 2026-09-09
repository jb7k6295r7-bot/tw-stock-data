"""資料層：讀 tw-stock-data 資料庫、還原價、母體、閘門。

規則出處：docs/READ_CONTRACT.md、tw-stock-db skill。
- 價格權威來源 data/stocks/，未還原；還原因子 data/adj/（事件日嚴格大於 d 的因子連乘）。
- 日檔只收當天有成交的證券 → 序列有洞；本層把每檔 reindex 到交易日曆，洞留 NaN。
- 處置要用 start_date ~ end_date 區間判，sec_kind 過濾權證。
- 母體用 first_seen / last_seen，不用今天的清單。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

PRICE_COLS = ["open", "high", "low", "close"]


def load_calendar() -> pd.DatetimeIndex:
    cal = pd.read_csv(os.path.join(DATA, "meta", "calendar_twse.csv"))
    return pd.DatetimeIndex(pd.to_datetime(cal["date"])).sort_values()


def load_universe() -> pd.DataFrame:
    """上市＋上櫃普通股，含已下市；興櫃排除。"""
    mk = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    mk = mk[(mk["kind"] == "stock") & (mk["market"].isin(["twse", "tpex"]))].copy()
    mk["first_seen"] = pd.to_datetime(mk["first_seen"])
    mk["last_seen"] = pd.to_datetime(mk["last_seen"])
    return mk.reset_index(drop=True)


def load_adj(stock_id: str) -> pd.DataFrame | None:
    p = os.path.join(DATA, "adj", f"{stock_id}.csv")
    if not os.path.exists(p):
        return None
    a = pd.read_csv(p, dtype={"date": str})
    a["date"] = pd.to_datetime(a["date"])
    return a.sort_values("date").reset_index(drop=True)


def cum_factor_series(dates: pd.DatetimeIndex, adj: pd.DataFrame | None) -> np.ndarray:
    """F(d) = 事件日嚴格大於 d 的因子連乘。adj.cum_factor 已是「該列（含）之後所有因子的連乘」。"""
    F = np.ones(len(dates))
    if adj is None or adj.empty:
        return F
    ev_dates = adj["date"].values.astype("datetime64[ns]")
    cum = adj["cum_factor"].values.astype(float)
    # 第一個事件日 > d 的位置：searchsorted(side='right') 給的是「> d」的第一個索引
    pos = np.searchsorted(ev_dates, dates.values.astype("datetime64[ns]"), side="right")
    mask = pos < len(ev_dates)
    F[mask] = cum[pos[mask]]
    return F


@dataclass
class Stock:
    stock_id: str
    market: str
    df: pd.DataFrame          # index = 交易日曆（全期），洞為 NaN；價格已還原
    event_dates: set          # 還原事件日（除權息／減資）


def load_stock(stock_id: str, market: str, cal: pd.DatetimeIndex) -> Stock | None:
    p = os.path.join(DATA, "stocks", f"{stock_id}.csv")
    if not os.path.exists(p):
        return None
    raw = pd.read_csv(p, dtype={"stock_id": str, "date": str},
                      usecols=["date", "open", "high", "low", "close", "volume"])
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for c in PRICE_COLS + ["volume"]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    # 零價視為缺（極少數列來源是空值填 0）
    bad = (raw[PRICE_COLS] <= 0).any(axis=1)
    raw.loc[bad, PRICE_COLS] = np.nan
    adj = load_adj(stock_id)
    F = cum_factor_series(raw.index, adj)
    for c in PRICE_COLS:
        raw[c] = raw[c] * F
    df = raw.reindex(cal)
    df["traded"] = df["close"].notna()
    ev = set(adj["date"].tolist()) if adj is not None else set()
    return Stock(stock_id, market, df, ev)


# ── 斷點：序列無法被還原因子接起來（K線線 2026-09-09 三訂，必守第 7 條） ──
# 門檻是**非嚴格**不等式（≤ 0.55、≥ 1.8）：復牌首日常常直接漲停／跌停，比值會剛好貼在門檻上
# （4946 剛好 1.800、6613 是 0.544）；寫成嚴格不等式會把最常見的那種情形排除掉。
# 相鄰兩個有成交日之間，有漲跌幅限制的證券單日跌不到 0.55、漲不到 1.8，所以不會增加誤判。
JUMP_LO, JUMP_HI = 0.55, 1.8
GAP_MIN = 5   # ② 時間：連續缺 ≥ 5 個交易日（面額變更實測停 6～8 個；8101 停 59 個）
# ② 的流動性前提（K線線 2026-09-09 05:00 裁定）：只在「洞之前 60 個交易日的中位數日量 ≥ 500 張」時成立；
#   沒通過的洞不是斷點，退回缺漏處理（rolling min_periods 讓洞傳染），不套污染窗。
#   500 張是**實測分界，非推導**：全庫 2,129 檔量到 N≥5 無事件的洞 99% 在中位數日量 < 500 張的冷門股，
#   ≥ 500 張那一組 11 檔全是真停牌、零偽陽性。不要讀成「499 張就一定是無成交」。
GAP_LIQ_SHARES = 500_000
GAP_LIQ_WINDOW = 60


def breakpoints(df: pd.DataFrame, event_dates: set) -> list[dict]:
    """找斷點。對每個有成交日 t 與它的上一個有成交日 p：
       ① 價格：close(t)/close(p) ≤ 0.55 或 ≥ 1.8
       ② 時間：p 與 t 之間連續缺 ≥ 5 個交易日，且 p 之前 60 個交易日的中位數成交量 ≥ 500 張（流動性前提）
    任一成立、且區間 (p, t] 內沒有 data/adj/ 的事件 → t 是斷點（T ＝ 復牌後第一個有成交日）。
    區間內有可還原事件（含 parvalue、etfsplit）→ 不是斷點，走缺漏處理。
    ⚠ 事件用**日期區間**判，不用「±N 個交易日」容錯：data/adj/ 的事件日不保證是交易日
    （3293 2024-07-24 除權息當天颱風停市，沿交易日曆數容錯永遠數不到它）。
    ⚠ 一定要對「上一個有成交日」：換發新股前停牌 6～8 日，日曆對齊序列裡 t−1 是空的，相鄰日比會一筆都抓不到。
    回傳每個斷點 {pos, prev_pos, ratio, gap, rule}；gap ＝ 缺掉的交易日數（missing_trading_days）；rule ∈ {price, gap, price+gap}。"""
    c = df["close"].to_numpy(float)
    traded = np.flatnonzero(~np.isnan(c))
    if len(traded) < 2:
        return []
    p, t = traded[:-1], traded[1:]
    ratio = c[t] / c[p]
    gap = t - p - 1
    price = (ratio <= JUMP_LO) | (ratio >= JUMP_HI)
    long_gap = gap >= GAP_MIN
    # 資料層不帶流動性條件（K線線 12:00：過濾放在「使用」時，不放在「記錄」時）；liq_ok 只是附註，
    # 由 breakpoint_window 在判讀層決定要不要套污染窗。
    liq = np.ones(len(p), bool)
    if long_gap.any():
        v = df["volume"].to_numpy(float) if "volume" in df else np.full(len(c), np.nan)
        for k in np.flatnonzero(long_gap):
            w = v[max(0, p[k] - GAP_LIQ_WINDOW + 1):p[k] + 1]
            w = w[~np.isnan(w)]
            liq[k] = len(w) > 0 and np.median(w) >= GAP_LIQ_SHARES
    cand = price | long_gap
    if event_dates and cand.any():
        ev = np.array(sorted(pd.Timestamp(x) for x in event_dates), dtype="datetime64[ns]")
        idx = df.index.values.astype("datetime64[ns]")
        n_upto_p = np.searchsorted(ev, idx[p], side="right")   # 事件日 ≤ p 的個數
        n_upto_t = np.searchsorted(ev, idx[t], side="right")   # 事件日 ≤ t 的個數
        cand &= ~(n_upto_t > n_upto_p)                          # (p, t] 內有事件 → 可解釋
    out = []
    for k in np.flatnonzero(cand):
        rule = "price+gap" if (price[k] and long_gap[k]) else ("price" if price[k] else "gap")
        out.append({"pos": int(t[k]), "prev_pos": int(p[k]), "ratio": float(ratio[k]), "gap": int(gap[k]), "rule": rule,
                    "liq_ok": bool(liq[k])})
    return out


def applies(b: dict) -> bool:
    """判讀層：這個斷點要不要套污染窗。價格規則一律套；純 gap 規則只在流動性前提成立時套（K線線 05:00／12:00）。"""
    return b["rule"] != "gap" or b["liq_ok"]


def breakpoint_window(bps: list[dict], n: int, H: int, L: int) -> np.ndarray:
    """以訊號日 s 為單位的剔除遮罩：s ∈ [T−H, T+L−1] → True。只套 applies() 為真的斷點。
    方向不要寫反：前瞻報酬的污染在 T **之前**（s ∈ [T−H, T−1]，斷點落在持有期內）；
    回看指標的污染在 T **之後**（s ∈ [T, T+L−1]，回看窗跨過斷點）。
    H ＝ 該研究最長的前瞻天數、L ＝ 最長回看天數，由呼叫端從自己的參數算，不要寫死。"""
    w = np.zeros(n, bool)
    for b in bps:
        if not applies(b):
            continue
        T = b["pos"]
        w[max(0, T - H):min(n, T + L)] = True
    return w


def load_disposal_intervals() -> dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]]:
    """處置區間（含權證以外的普通股），鍵＝代號。"""
    d = pd.read_csv(os.path.join(DATA, "meta", "disposal.csv"), dtype=str)
    d = d[d["sec_kind"] == "普通股"]
    out: dict[str, list] = {}
    for sid, s, e in zip(d["stock_id"], d["start_date"], d["end_date"]):
        out.setdefault(sid, []).append((pd.Timestamp(s), pd.Timestamp(e)))
    return out


def disposal_mask(stock_id: str, cal: pd.DatetimeIndex, intervals: dict, after_days: int = 5) -> np.ndarray:
    """True ＝ 該日在處置期間內，或處置結束後 after_days 個交易日內。"""
    m = np.zeros(len(cal), dtype=bool)
    for s, e in intervals.get(stock_id, []):
        i0 = cal.searchsorted(s, side="left")
        i1 = cal.searchsorted(e, side="right")  # exclusive
        m[i0:min(len(cal), i1 + after_days)] = True
    return m


def load_attention_dates() -> dict[str, set]:
    a = pd.read_csv(os.path.join(DATA, "meta", "attention.csv"), dtype=str, usecols=["stock_id", "sec_kind", "date"])
    a = a[a["sec_kind"] == "普通股"]
    out: dict[str, set] = {}
    for sid, d in zip(a["stock_id"], a["date"]):
        out.setdefault(sid, set()).add(pd.Timestamp(d))
    return out


def load_benchmark(cal: pd.DatetimeIndex) -> pd.DataFrame:
    """0050 還原價，當同窗基準。"""
    s = load_stock("0050", "twse", cal)
    return s.df
