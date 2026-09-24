# -*- coding: utf-8 -*-
"""查：main／a_k10／b_120_240 三組事件數不同，訊號達成卻都是 736 —— 是巧合還是程式錯？
直接重建三組事件（同一支 researchH2 的函式），比對事件集合、各自 hit 總數、以及 hit＝1 的事件集合。"""
import os, sys
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import numpy as np, pandas as pd
import researchH2 as H
from multiprocessing import Pool
from backtest import data as D
cal = D.load_calendar()
w0 = int(cal.searchsorted(pd.Timestamp(H.W0))); w1 = int(cal.searchsorted(pd.Timestamp(H.W1)))
stocks = pd.read_csv(os.path.join(H.H2D, "meta", "stocks.csv"), dtype=str)
U = H.UG.gate3(stocks)
with Pool(4, initializer=H._init, initargs=(cal,)) as pool:
    res = pool.map(H.load_one, list(zip(U["stock_id"], U["market"])), chunksize=16)
ST = {r["sid"]: r for r in res if r is not None}
C = H.Ctx(ST, cal, w0, w1)
E = {}
for key in ("main", "a_k10", "b_120_240", "a_k1"):
    ev, _ = H.build_events(C, key, 20)
    E[key] = {(e["sid"], e["t"]): e["hit"] for e in ev}
    print(key, "事件", len(ev), "hit 總數", sum(E[key].values()), "hit 取值", sorted(set(E[key].values())))
hm = {k for k, v in E["main"].items() if v}
for key in ("a_k10", "b_120_240", "a_k1"):
    hk = {k for k, v in E[key].items() if v}
    print("{}：事件與 main 相同 {}／{}｜hit＝1 集合與 main 相同？{}（交集 {}、只在 {} {}、只在 main {}）".format(
        key, len(set(E[key]) & set(E["main"])), len(E[key]), hk == hm, len(hk & hm), key, len(hk - hm), len(hm - hk)))
print("--- 配對：只在一組的 hit，是否在另一組有同檔、相距 ≤ 60 日的 hit ---")
for key in ("a_k10", "b_120_240"):
    hk = {k for k, v in E[key].items() if v}
    A = sorted(hk - hm); B = sorted(hm - hk)
    bset = {}
    for s, t in B:
        bset.setdefault(s, []).append(t)
    paired = sum(1 for s, t in A if any(abs(t - u) <= 60 for u in bset.get(s, [])))
    gaps = [min(abs(t - u) for u in bset[s]) for s, t in A if s in bset]
    print("{}：只在 {} 的 {} 個 hit 裡，能在 main 找到同檔 ≤60 日 hit 的 {}｜距離中位 {}".format(key, key, len(A), paired, int(np.median(gaps)) if gaps else None))
    # 以「檔×年」為單位比 hit 總數
    ya = pd.Series([f"{s}-{cal[t].year}" for s, t in hk]).value_counts(); yb = pd.Series([f"{s}-{cal[t].year}" for s, t in hm]).value_counts()
    print("   以 檔×年 計 hit：{} {}／main {}；兩邊都有的 檔×年 {}".format(key, len(ya), len(yb), len(set(ya.index) & set(yb.index))))
print("--- 換門檻：三組的 hit 筆數是否仍相同 ---")
for key in ("main", "a_k10", "b_120_240", "a_k1"):
    ev, _ = H.build_events(C, key, 20)
    mr = []
    for e in ev:
        S = ST[e["sid"]]; t = e["t"]
        mr.append(np.nanmax(S["h"][t + 1:t + 21]) / e["P0"])
    mr = np.array(mr)
    print(key, {x: int((mr >= x * (1 - 1e-12)).sum()) for x in (1.1, 1.2, 1.25, 1.3, 1.35)}, "事件", len(ev))
