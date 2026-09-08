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


JUMP_LO, JUMP_HI = 0.55, 1.8


def jump_days(df: pd.DataFrame, event_dates: set) -> np.ndarray:
    """對「上一個有成交日」的收盤比 < 0.55 或 > 1.8、且不是還原事件日的日子 → True。
    實測全庫 26 筆、24 檔，全部是停牌約 8 天後的面額變更換發新股（10→1 之類），data/adj/ 沒有這種事件。"""
    c = df["close"]
    prev = c.ffill().shift(1).to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = c.to_numpy(float) / prev
    m = (r < JUMP_LO) | (r > JUMP_HI)
    if event_dates:
        m &= ~np.isin(df.index.values, np.array(sorted(event_dates), dtype="datetime64[ns]"))
    return m


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
