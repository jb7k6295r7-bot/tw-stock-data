# -*- coding: utf-8 -*-
"""PREREGH2 訊號的獨立驗算：抽 30 個保留事件，直接從 data/stocks＋data/adj 重算（⛔ 不經 researchH2 的函式），
逐條驗：MA144、MA200 上揚（k＝5，依有效 K 棒）、close(t) ≥ max(MA)、前一根 close < max(MA)、P0 ＝ 還原 open(t+1)。"""
import os, sys
import numpy as np, pandas as pd
SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
DD = os.path.expanduser(f"~/h2data/{SHA}/data")
cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(DD, "meta", "calendar_twse.csv"))["date"])).sort_values()
X = pd.read_csv(os.path.expanduser("~/tw-p17/backtest/resultsH2/main_events.csv"), dtype={"sid": str})
smp = X.sample(30, random_state=1)
bad = 0
for r in smp.itertuples():
    raw = pd.read_csv(os.path.join(DD, "stocks", f"{r.sid}.csv"), dtype={"date": str})
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for k in ("open", "close"):
        raw[k] = pd.to_numeric(raw[k], errors="coerce"); raw.loc[raw[k] <= 0, k] = np.nan
    ap = os.path.join(DD, "adj", f"{r.sid}.csv")
    F = pd.Series(1.0, index=raw.index)
    if os.path.exists(ap):
        a = pd.read_csv(ap); a["date"] = pd.to_datetime(a["date"]); a = a.sort_values("date")
        for i, d in enumerate(raw.index):
            later = a[a["date"] > d]
            F.iloc[i] = float(later["cum_factor"].iloc[0]) if len(later) else 1.0
    c = (raw["close"] * F).dropna()
    d_t = cal[int(r.t)]
    j = c.index.get_loc(d_t)
    m144 = c.rolling(144).mean(); m200 = c.rolling(200).mean()
    up = m144.iloc[j] > m144.iloc[j - 5] and m200.iloc[j] > m200.iloc[j - 5]
    now = c.iloc[j] >= max(m144.iloc[j], m200.iloc[j])
    prev = c.iloc[j - 1] < max(m144.iloc[j - 1], m200.iloc[j - 1])
    o1 = float(raw["open"].get(cal[int(r.t) + 1], np.nan) * F.get(cal[int(r.t) + 1], np.nan))
    ok = up and now and prev
    bad += int(not ok)
    print("{} {} 上揚{} 站上{} 前一根未站上{} ⇒ {}".format(r.sid, d_t.date(), up, now, prev, "✅" if ok else "⛔"))
print("⇒ 30 個抽樣裡條件不成立：{}".format(bad))
