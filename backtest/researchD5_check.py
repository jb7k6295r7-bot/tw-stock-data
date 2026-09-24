# -*- coding: utf-8 -*-
"""D5 交件前查核（⛔ 不改結果）：seed 102000 的停損事件逐筆
① 獨立重算（⛔ 不呼叫 stop_fractal）：擺動低點＝嚴格低於左右各 2 根；初始停損＝進場根以前最近「確認根 ≤ 進場根」的擺動低點；棘輪只進不退
   ⇒ 觸發根 d＝出場日前一個交易日：close(d) < 停損(d)，且前一根沒有觸發（第一次跌破）
② 出場價＝出場日開盤
③ 描述：進場到被停的持有天數、初始停損距離（1 − 停損／進場開盤）、觸發時距離"""
import os, sys, bisect
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D = H2.D
from backtest import research11 as R
cal = D.load_calendar()
uni = D.load_universe().set_index("stock_id")["market"]
ev = pd.read_csv("backtest/resultsD5/stop_events.csv", dtype={"sid": str})
ev = ev[ev["seed"] == 102000].reset_index(drop=True)
cache = {}
def bars(s):
    if s not in cache:
        st = D.load_stock(s, uni.get(s, "twse"), cal); df = st.df
        v = np.flatnonzero(np.isfinite(df["close"].to_numpy(float)))
        cache[s] = (v, df["open"].to_numpy(float), df["low"].to_numpy(float)[v], df["close"].to_numpy(float)[v])
    return cache[s]
bad = 0; hold, d0, d1 = [], [], []
for r in ev.itertuples():
    v, o_cal, lo, cl = bars(r.sid)
    e = bisect.bisect_left(v, r.entry); x = bisect.bisect_left(v, r.t) - 1          # 觸發根＝出場日前一根有效 K 棒
    sw = [s for s in range(2, len(lo) - 2) if lo[s] < lo[s - 2:s].min() and lo[s] < lo[s + 1:s + 3].min()]
    init = [s for s in sw if s + 2 <= e and s >= e - 120]
    stop = lo[init[-1]]; p0 = o_cal[r.entry]; last = init[-1]
    trig = None
    for b in range(e, x + 1):
        s_new = b - 2
        if s_new in sw and s_new > last and lo[s_new] > stop:
            stop = lo[s_new]
        if cl[b] < stop:
            trig = b; break
    ok = trig == x
    bad += int(not ok)
    hold.append(r.t - r.entry); d0.append(1 - lo[init[-1]] / p0); d1.append(stop / p0 - 1)
print("seed 102000 停損事件 {} 筆｜獨立重算觸發根不符 {} 筆".format(len(ev), bad))
print("進場到出場的日曆天數：中位 {:.0f}｜p10 {:.0f}｜p90 {:.0f}".format(np.median(hold), np.percentile(hold, 10), np.percentile(hold, 90)))
print("初始停損距離：中位 {:.2%}｜p10 {:.2%}｜p90 {:.2%}".format(np.median(d0), np.percentile(d0, 10), np.percentile(d0, 90)))
print("觸發時停損 ／ 進場價 − 1：中位 {:+.2%}｜p10 {:+.2%}｜p90 {:+.2%}".format(np.median(d1), np.percentile(d1, 10), np.percentile(d1, 90)))
print("進場當天就觸發（持有 1 天）的比例：{:.1%}".format(np.mean(np.array(hold) <= 1)))
from backtest import tradability as T
print("--- 不符的 5 筆 ---")
n_above = 0
for r in ev.itertuples():
    v, o_cal, lo, cl = bars(r.sid)
    e = bisect.bisect_left(v, r.entry); x = bisect.bisect_left(v, r.t) - 1
    sw = [s for s in range(2, len(lo) - 2) if lo[s] < lo[s - 2:s].min() and lo[s] < lo[s + 1:s + 3].min()]
    init = [s for s in sw if s + 2 <= e and s >= e - 120]
    stop = lo[init[-1]]; last = init[-1]; trig = None
    n_above += int(stop > o_cal[r.entry])
    for b in range(e, len(cl)):
        s_new = b - 2
        if s_new in sw and s_new > last and lo[s_new] > stop:
            stop = lo[s_new]
        if cl[b] < stop:
            trig = b; break
    if trig != x:
        tb = T.one(r.sid, cal)
        days = list(range(v[trig] + 1, r.t + 1))
        print(r.sid, "觸發根", cal[v[trig]].date(), "出場日", cal[r.t].date(), "其間：", [(str(cal[d].date()), "停牌" if not tb["trd"][d] else ("跌停開" if tb["dn_o"][d] else "可賣")) for d in days][:6])
print("初始停損高於進場開盤的筆數：{}／{}（{:.1%}）".format(n_above, len(ev), n_above / len(ev)))
