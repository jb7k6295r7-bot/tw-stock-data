# -*- coding: utf-8 -*-
"""挑一筆 k=5 訊號供台股策略線做 TradingView 實作對帳。

⛔⛔ 挑法必須【與結果無關】—— 挑一筆「好看的」就是依結果選（〈九十七〉）。
⭐ 事前寫死的挑法（⛔ 寫下就不改）：
   ① 主樣本 ＝ 判定窗內【日期最早】的那一筆；同日多筆 ⇒ 取 stock_id 字典序最小
   ② 另附兩筆備用 ＝ 同規則的第 2、第 3 筆
   ⇒ ⭐ 三筆都由「最早」這個與未來報酬無關的鍵決定
⛔ 本支【不】計算、⛔ 不印出訊號日之後的任何價格（⭐ 連本線自己都不看）
   ⇒ 理由：台股策略線 1307 §4-2 自己指出「K 線圖上訊號的右邊就是答案」
     ⇒ 而本線若在挑的時候看了後續報酬，⛔ 那個偷看一樣查不出來。
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D

W0, W1, K = 523, 2835, 5
LONG, SHORT, MIN_BARS = 200, 144, 200
cal = D.load_calendar()
uni = D.load_universe()
hits = []
for sid, mkt in zip(uni["stock_id"].astype(str), uni["market"].astype(str)):
    st = D.load_stock(sid, mkt, cal)
    if st is None:
        continue
    c = st.df["close"].to_numpy(float)
    if np.isfinite(c).sum() < MIN_BARS:
        continue
    m144 = pd.Series(c).rolling(SHORT, min_periods=SHORT).mean().to_numpy()
    m200 = pd.Series(c).rolling(LONG, min_periods=LONG).mean().to_numpy()
    mx = np.fmax(m144, m200)
    up = np.zeros(len(c), bool); up[K:] = (m144[K:] > m144[:-K]) & (m200[K:] > m200[:-K])
    fi = np.zeros(len(c), bool); fi[1:] = (c[1:] >= mx[1:]) & (c[:-1] < mx[:-1])
    idx = np.flatnonzero(up & fi & np.isfinite(c) & np.isfinite(mx))
    for p in idx[(idx >= W0) & (idx <= W1)]:
        hits.append((int(p), sid, mkt))

hits.sort(key=lambda t: (t[0], t[1]))        # ⭐ 最早優先，同日取代號字典序最小
nm = dict(zip(uni["stock_id"].astype(str), uni["name"].astype(str))) if "name" in uni.columns else {}
print("k=5 訊號共 {:,} 筆（判定窗 [{},{}]）".format(len(hits), W0, W1))
print()
print("=== ⭐ 交給台股策略線對帳的三筆（⛔ 挑法事前寫死：日期最早；同日取代號最小）===")
for r, (p, sid, mkt) in enumerate(hits[:3], 1):
    d = cal[p]
    ticker = ("TWSE:" if mkt == "twse" else "TPEX:") + sid
    print("  {}. **{}**（{}）　訊號日 **{}**　⇒ TradingView 代碼 `{}`"
          .format(r, sid, nm.get(sid, "?"), d.strftime("%Y-%m-%d"), ticker))
    print("     ⭐ 該日 cal 位置 pos={}｜⛔ 本支不印任何價格（含當日），⛔ 免得順便看到後續".format(p))
print()
print("⇒ ⭐ 主樣本 ＝ 第 1 筆；第 2、3 筆備用（若 TradingView 沒有該檔的足夠歷史）")
print("⛔ 本支沒有計算、也沒有印出任何報酬或訊號日之後的價格。")

# ============================================================================
# ⛔⛔ 規則①（日期最早）的結果：三筆【全落在判定窗的第一天】2017-03-02（pos=523）。
#
# ⭐ 本線【不刪】上面那個結果 —— 事前寫死的規則跑出不喜歡的答案就換規則，
#    ⛔ 那正是〈九十七〉禁的事。所以規則① 的輸出照留。
#
# ⚠ 但它對「實作對帳」是一個**弱樣本**，理由與報酬無關：
#    ⭐ 它在窗的【邊界】上 ⇒ ⛔ 分不出「實作正確」與「窗的起點差一天」
#      —— 兩種情形在這一筆上會給出同樣的答案。
#    ⚠ 而且窗第一天本來就容易堆事件（見下面印出的當日筆數）。
#
# ⇒ ✅ 所以本線【加】一條規則，⛔ 而不是換掉規則①，並把兩者都交出去：
#    規則② ＝ 同一個 (日期, 代號) 排序下的【中位序位】那一筆（index ⌊N/2⌋）
#    ⭐ 它同樣與未來報酬無關（只用序位），⛔ 而且落在窗的中間 ⇒ 邊界問題不存在。
#
# ⭐⭐ 據實聲明本線做了什麼判斷：換樣本的理由是【窗邊界】這個
#    在看到任何報酬之前就知道的性質，⛔ 不是因為結果好不好看
#    —— 而本線把兩條規則的輸出都交出去，讓對方自己看得出有沒有被挑過。
# ============================================================================
same_day = sum(1 for p, _, _ in hits if p == hits[0][0])
print()
print("⚠ 窗第一天（{}）當日的 k=5 訊號筆數 ＝ **{:,}**（全窗 {:,} 筆）".format(
    cal[hits[0][0]].strftime("%Y-%m-%d"), same_day, len(hits)))
mid = len(hits) // 2
print()
print("=== ⭐ 規則②（中位序位，index {}）⇒ 這一筆才是建議的主樣本 ===".format(mid))
for r, (p, sid, mkt) in enumerate(hits[mid:mid + 3], 1):
    d = cal[p]
    ticker = ("TWSE:" if mkt == "twse" else "TPEX:") + sid
    print("  {}. **{}**（{}）　訊號日 **{}**　⇒ TradingView 代碼 `{}`　（pos={}）".format(
        r, sid, nm.get(sid, "?"), d.strftime("%Y-%m-%d"), ticker, p))
print()
print("⇒ ⭐ 建議主樣本 ＝ 規則② 第 1 筆；⛔ 規則① 的三筆照留在上面，⭐ 供對方判斷有沒有被挑過。")
