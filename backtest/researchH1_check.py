# -*- coding: utf-8 -*-
"""PREREGH1 獨立驗算（⛔ 不經 researchH1／researchH2 的函式）：直接讀 data/stocks＋data/adj 重算。
① 抽 30 個保留事件：SMA20 上揚（k5）、首次跌破、分組（t0+1..3 有無收盤 ≥ SMA20）、P0＝還原 open(t0+4)、R＝close(t0+23)/P0−1
② 抽 2 個進場日：gate3 等權報酬（d 日有有效開盤者，close(≤d+19 最後一根)/open(d) − 1）與 X＝R−EW 對得上"""
import os
import numpy as np, pandas as pd
SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
DD = os.path.expanduser(f"~/h2data/{SHA}/data")
cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(DD, "meta", "calendar_twse.csv"))["date"])).sort_values()
pos = {d: i for i, d in enumerate(cal)}


def adj_series(sid):
    raw = pd.read_csv(os.path.join(DD, "stocks", f"{sid}.csv"), dtype={"date": str})
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for k in ("open", "close"):
        raw[k] = pd.to_numeric(raw[k], errors="coerce"); raw.loc[raw[k] <= 0, k] = np.nan
    F = np.ones(len(raw))
    ap = os.path.join(DD, "adj", f"{sid}.csv")
    if os.path.exists(ap):
        a = pd.read_csv(ap); a["date"] = pd.to_datetime(a["date"]); a = a.sort_values("date")
        ev = a["date"].values; cf = a["cum_factor"].values.astype(float)
        k = np.searchsorted(ev, raw.index.values, side="right")
        m = k < len(ev); F[m] = cf[k[m]]
    return raw["open"] * F, raw["close"] * F


X = pd.read_csv(os.path.expanduser("~/tw-p17/backtest/resultsH1/main_events.csv"), dtype={"sid": str})
bad = 0
for r in X.sample(30, random_state=7).itertuples():
    o, c = adj_series(r.sid)
    cv = c.dropna(); sma = cv.rolling(20).mean()
    t0 = cal[r.t]; j = cv.index.get_loc(t0)
    up = sma.iloc[j] > sma.iloc[j - 5]
    brk = cv.iloc[j] < sma.iloc[j] and cv.iloc[j - 1] >= sma.iloc[j - 1]
    back = any(cv.loc[cal[r.t + s]] >= sma.loc[cal[r.t + s]] for s in (1, 2, 3))
    P0 = o.loc[cal[r.t + 4]]
    cE = c.reindex(cal).ffill().iloc[r.t + 23]
    R = cE / P0 - 1
    ok = up and brk and (int(back) == r.站回) and abs(R - r.R) < 1e-9
    bad += int(not ok)
    if not ok:
        print("⛔", r.sid, t0.date(), up, brk, back, r.站回, R, r.R)
print("① 30 個事件：不符 {}".format(bad))
# ② EW
st = pd.read_csv(os.path.join(DD, "meta", "stocks.csv"), dtype=str)
u = st[(st["kind"] == "stock") & st["market"].isin(["twse", "tpex"])]
u = u[~u["name"].str.contains("-DR", na=False) & ~u["name"].str.contains("-創", na=False, regex=False)]
for rr in X.sample(2, random_state=3).itertuples():
    d = rr.t + 4; vals = []
    for sid in u["stock_id"]:
        p = os.path.join(DD, "stocks", f"{sid}.csv")
        if not os.path.exists(p):
            continue
        o, c = adj_series(sid)
        od = o.get(cal[d], np.nan)
        if not np.isfinite(od):
            continue
        ce = c.reindex(cal).ffill().iloc[d + 19]
        if np.isfinite(ce):
            vals.append(ce / od - 1)
    ew = float(np.mean(vals))
    print("② 進場日 {}：獨立 EW {:.10f}｜程式 X＝R−EW ⇒ 反推 EW {:.10f}｜差 {:.2e}（n＝{}）".format(cal[d].date(), ew, rr.R - rr.X, ew - (rr.R - rr.X), len(vals)))
