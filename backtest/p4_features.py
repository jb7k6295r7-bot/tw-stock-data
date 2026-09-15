"""PREREGP4 v2 的特徵層——同一件事只有一份實作：researchp4（主格）與 forward_p4（前瞻檔）都 import 這裡。
判準 backtest/PREREGP4.md（v2，策略線 09-14 18:38；⛔ 中心 C[0..3]／mu／sd 尚未投遞 ⇒ assign() 只收參數、不內建）。

13 條特徵（順序固定）：
  同日橫截面百分位（0～100）：ret_120 ret_20 dist_hi120 dist_lo120 vol60 vr_20_120 amt20 turn20 fore20 trust20
  布林 ×100：ma_stack ma60_up rev_hi24
機器定義（v2 §4-3）：
  ret_120   close_t / close_{t-120} − 1（還原、ffill）      ret_20 同
  dist_hi120 close_t / max(close, 120 日, min_periods=60) − 1   dist_lo120 對 min
  vol60     日報酬 60 日標準差（min_periods=30）× sqrt(245)
  vr_20_120 amount 20 日均 / amount 120 日均           amt20 amount 20 日均（元）
  turn20    volume 20 日均 / 1000 / (shares_t / 1000)
  fore20    foreign 20 日累計 / (shares_t / 1000)       trust20 trust 同（⚠ 欄位＝data/stocks_inst 的日淨買超股數，待策略線確認）
  shares_t  data/stocks/<code>.csv 當日 shares，依交易日曆 reindex 後【只 ffill、⛔ 不 bfill】；NaN 或 ≤ 0 ⇒ 該三欄 NaN（補 50、計入放棄組）
  ma_stack  close > MA20 > MA60 > MA120                ma60_up MA60_t > MA60_{t−20}
  rev_hi24  另算一欄 rev_hi24_p4：當期月營收 ≥ 近 24 期最高 × 0.9999；近 24 期有效期數 < 18 ⇒ NaN（⛔ 不是 False）；
            可得性＝期別次月 10 日後第一個交易日（research34.rebalance_dates）；⛔ 不動研究三／十三的 rev_hi24
缺值一律補 50；標準化 (x − mu) / sd；歸型取歐氏距離最近的中心。
量測日＝每月第一個交易日；進場＝次一交易日開盤還原價；出場＝H 個交易日後收盤（H = 20 / 60 / 120）。
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import data as D
from . import research34 as R34

HERE = os.path.dirname(os.path.abspath(__file__))
PCT_FEATURES = ["ret_120", "ret_20", "dist_hi120", "dist_lo120", "vol60", "vr_20_120", "amt20", "turn20", "fore20", "trust20"]
BOOL_FEATURES = ["ma_stack", "ma60_up", "rev_hi24"]
FEATURES = PCT_FEATURES + BOOL_FEATURES
FILL = 50.0
LIQ_MIN = 50_000_000     # 近 20 日均額 ≥ 5,000 萬（v2 §三）
HOLDS = (20, 60, 120)
REV_WIN, REV_MIN_VALID, REV_TOL = 24, 18, 0.9999


def measurement_days(cal: pd.DatetimeIndex, start: str | None = None, end: str | None = None) -> np.ndarray:
    """每月第一個交易日的日曆位置。"""
    per = cal.to_period("M")
    first = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    if start:
        first = first[cal[first] >= pd.Timestamp(start)]
    if end:
        first = first[cal[first] <= pd.Timestamp(end)]
    return first


def load_shares(sid: str, cal: pd.DatetimeIndex) -> pd.Series:
    """當日 shares，reindex 到日曆後只 ffill；NaN／≤0 ⇒ NaN。"""
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return pd.Series(np.nan, index=cal)
    s = pd.read_csv(p, usecols=["date", "shares"], parse_dates=["date"]).drop_duplicates("date").set_index("date")["shares"]
    s = pd.to_numeric(s, errors="coerce").reindex(cal).ffill()
    return s.where(s > 0)


def load_inst(sid: str, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """三大法人日淨買超股數（foreign／trust），reindex 到日曆；沒有檔 ⇒ 全 NaN。"""
    p = os.path.join(D.DATA, "stocks_inst", f"{sid}.csv")
    if not os.path.exists(p):
        return pd.DataFrame({"foreign": np.nan, "trust": np.nan}, index=cal)
    df = pd.read_csv(p, usecols=["date", "foreign", "trust"], parse_dates=["date"]).drop_duplicates("date").set_index("date")
    return df.apply(pd.to_numeric, errors="coerce").reindex(cal)


def rev_hi24_flags(rev: pd.DataFrame, cal: pd.DatetimeIndex, pub_day: int = 10) -> pd.DataFrame:
    """rev：period × stock_id 的月營收（research34.load_revenue）。回傳 cal × stock_id 的 0／100／NaN，
    每期在可得日（次月 pub_day 日後第一個交易日）生效、延續到下一期可得日前。"""
    periods = list(rev.index)
    rd = R34.rebalance_dates(periods, cal, pub_day)
    flags = {}
    vals = rev.to_numpy(float)
    for j, sid in enumerate(rev.columns):
        col = np.full(len(periods), np.nan)
        for k in range(len(periods)):
            if k < REV_WIN or np.isnan(vals[k, j]):
                continue
            hist = vals[k - REV_WIN:k, j]
            valid = hist[~np.isnan(hist)]
            if len(valid) < REV_MIN_VALID:
                continue
            col[k] = 100.0 if vals[k, j] >= valid.max() * REV_TOL else 0.0
        flags[sid] = col
    F = pd.DataFrame(flags, index=periods)
    # 攤到日曆：每期在 entry_pos 生效
    out = pd.DataFrame(np.nan, index=cal, columns=rev.columns)
    for p, (_, e) in rd.items():
        if p in F.index:
            out.iloc[e] = F.loc[p].to_numpy()
    return out.ffill()


def stock_raw(sid: str, market: str, cal: pd.DatetimeIndex, rev_flags: pd.Series | None = None) -> pd.DataFrame | None:
    """一檔的逐日原始特徵（尚未百分位化）＋ 進出場價與流動性閘門。全部只看 t 及之前。"""
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    c = df["close"].ffill()
    o = df["open"]
    vol = pd.to_numeric(df["volume"], errors="coerce"); amt = pd.to_numeric(df["amount"], errors="coerce")
    shares = load_shares(sid, cal); inst = load_inst(sid, cal)
    ma20, ma60, ma120 = c.rolling(20).mean(), c.rolling(60).mean(), c.rolling(120).mean()
    out = pd.DataFrame(index=cal)
    out["ret_120"] = c / c.shift(120) - 1
    out["ret_20"] = c / c.shift(20) - 1
    out["dist_hi120"] = c / c.rolling(120, min_periods=60).max() - 1
    out["dist_lo120"] = c / c.rolling(120, min_periods=60).min() - 1
    out["vol60"] = c.pct_change().rolling(60, min_periods=30).std() * np.sqrt(245)
    out["vr_20_120"] = amt.rolling(20).mean() / amt.rolling(120).mean()
    out["amt20"] = amt.rolling(20).mean()
    k = shares / 1000.0
    out["turn20"] = vol.rolling(20).mean() / 1000.0 / k
    out["fore20"] = inst["foreign"].rolling(20).sum() / k
    out["trust20"] = inst["trust"].rolling(20).sum() / k
    out["ma_stack"] = ((c > ma20) & (ma20 > ma60) & (ma60 > ma120)).astype(float) * 100
    out["ma60_up"] = (ma60 > ma60.shift(20)).astype(float) * 100
    out.loc[ma120.isna(), "ma_stack"] = np.nan; out.loc[ma60.shift(20).isna(), "ma60_up"] = np.nan
    out["rev_hi24"] = rev_flags.reindex(cal).to_numpy(float) if rev_flags is not None else np.nan
    out["shares_ok"] = shares.notna().astype(int)
    out["close"] = c; out["open"] = o; out["traded"] = df["traded"].astype(bool)
    return out


def cross_section(day: pd.DataFrame) -> pd.DataFrame:
    """同一量測日的合格母體（列＝stock_id）：百分位特徵 → 0～100（pandas rank(pct=True)×100：平均名次、NaN 不進分母），布林照舊；缺值補 50。⚠ 百分位的算法（平均名次 vs 最小名次、含不含自己）待策略線確認與中心同一套。"""
    X = pd.DataFrame(index=day.index)
    for f in PCT_FEATURES:
        X[f] = day[f].rank(pct=True) * 100
    for f in BOOL_FEATURES:
        X[f] = day[f]
    return X.fillna(FILL)


def assign(X: pd.DataFrame, centers: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """標準化後取歐氏距離最近的中心。centers：(4, 13) ⚠ 在【標準化空間】（KMeans 擬合的那個空間）；mu／sd：(13,) 是百分位／布林特徵的均值與標準差。⛔ 中心由登錄給，這裡不擬合。"""
    Z = (X[FEATURES].to_numpy(float) - np.asarray(mu, float)) / np.asarray(sd, float)
    C = np.asarray(centers, float)
    d = ((Z[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    return d.argmin(axis=1)


def forward_returns(raw: pd.DataFrame, pos: int, holds=HOLDS) -> dict:
    """量測日 pos：次日開盤進、H 日後收盤出的毛報酬（開盤 NaN ⇒ NaN）。"""
    o = raw["open"].to_numpy(float); c = raw["close"].to_numpy(float); n = len(o)
    e = pos + 1
    out = {"entry_pos": e}
    if e >= n or np.isnan(o[e]):
        return {**out, **{f"ret_{H}": np.nan for H in holds}}
    for H in holds:
        x = e + H
        out[f"ret_{H}"] = (c[x] / o[e] - 1) if x < n else np.nan
    return out
