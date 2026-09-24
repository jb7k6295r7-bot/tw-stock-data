# -*- coding: utf-8 -*-
"""C2 交件前查核（⛔ 不改任何結果）：
① 結算日歸屬與名目：funding.cashflow（已驗 SOL 2022-11 的 5.679914）逐筆算 qty＝1 的現金流，按 UTC 日加總
   vs 引擎的寫法「−Σ當日 rate × close(前一日)」⇒ 六幣全窗逐日比對
② 強平當天攤開：引擎重跑並記下該日的 q、M′、強平價 Lp、前一日收盤、日低、跌幅"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc2 as C2
from backtest import funding as F

man = F.load_manifest(path=os.path.join(C2.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
worst = 0.0; n_cmp = 0
for sym in C2.COINS:
    d = C2.load_px(sym)
    i0 = int(np.flatnonzero(d["date"].to_numpy() == C2.W_START[sym])[0]); i1 = int(np.flatnonzero(d["date"].to_numpy() == C2.W_END)[0])
    dates = d["date"].to_numpy()[i0:i1 + 1]; close = d["close"].to_numpy(float)[i0:i1 + 1]
    fbd, full = C2.fund_days(sym, dates, man)
    px = pd.Series(d["close"].to_numpy(float), index=pd.to_datetime(d["date"]))
    sub = full[(full["ts"] > pd.Timestamp(dates[0], tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)) &
               (full["ts"] < pd.Timestamp(dates[-1], tz="UTC") + pd.Timedelta(days=1))]
    sub = sub[sub["ts"].dt.strftime("%Y-%m-%d") > dates[0]]
    cf = F.cashflow(sub, px, qty=1.0)
    by_day = pd.Series(cf, index=sub["ts"].dt.strftime("%Y-%m-%d").to_numpy()).groupby(level=0).sum()
    for k in range(len(dates) - 1):
        eng = float(-(fbd[k + 1] * close[k]).sum()) if len(fbd[k + 1]) else 0.0
        ref = float(by_day.get(dates[k + 1], 0.0))
        worst = max(worst, abs(eng - ref)); n_cmp += 1
print("① 引擎的日資金費（qty＝1）vs funding.cashflow 逐日：比對 {:,} 天，最大絕對差 {:.2e}".format(n_cmp, worst))

print("② 強平當天（N200、E3、MMR 2%）：")
for sym in ("ETH", "BNB", "XRP", "DOGE"):
    d = C2.load_px(sym)
    c_all = d["close"].to_numpy(float); lo_all = d["low"].to_numpy(float); da = d["date"].to_numpy()
    sig = c_all > C2.C.sma(c_all, 200)
    i0 = int(np.flatnonzero(da == C2.W_START[sym])[0]); i1 = int(np.flatnonzero(da == C2.W_END)[0])
    close, low, dates = c_all[i0:i1 + 1], lo_all[i0:i1 + 1], da[i0:i1 + 1]; held = sig[i0:i1]
    fbd, _ = C2.fund_days(sym, dates, man)
    eq, M, q, inpos, ent = 1.0, 0.0, 0.0, False, None
    for k in range(len(held)):
        c0 = close[k]
        if held[k] and not inpos:
            q = 3 * eq / c0; M = eq - 0.0005 * 3 * eq; inpos = True; ent = dates[k]
        elif (not held[k]) and inpos:
            eq = M - 0.0005 * q * c0; inpos = False
        if inpos:
            Mp = M - float((fbd[k + 1] * c0 * q).sum())
            Lp = (q * c0 - Mp) / (q * 0.98)
            if low[k + 1] <= Lp:
                print("   {} 進場 {}｜強平日 {}｜前一日收盤 {:.6g}、日低 {:.6g}（跌 {:.1%}）｜保證金／名目 {:.1%}｜強平價 {:.6g}（距前收 {:.1%}）".format(
                    sym, ent, dates[k + 1], c0, low[k + 1], low[k + 1] / c0 - 1, Mp / (q * c0), Lp, Lp / c0 - 1))
                break
            M = Mp + q * (close[k + 1] - c0)
