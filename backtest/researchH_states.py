# -*- coding: utf-8 -*-
"""PREREGH seq2 開跑前的狀態盤點（⛔ 不看任何報酬）：判定窗內每個訊號月的市場狀態（CGH 2004：過去 L 個月市場累積報酬 < 0 ⇒ DOWN）。
指數＝0050 還原收盤（快照 edc6f8002f）；月 m 的狀態用「前一個完整月末」往回 L 個月末的報酬（只用 t 以前）。
主格 L＝36；描述 L＝12、24。報 UP／DOWN 月數與切換次數；DOWN < 3 ⇒ 依裁定線 seq122 §四 不開跑。"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D = H2.D
cal = D.load_calendar()
st = D.load_stock("0050", "twse", cal)
c = st.df["close"].dropna()
me = c.groupby(c.index.to_period("M")).last()                      # 月末還原收盤
months = pd.period_range("2017-03", "2026-08", freq="M")            # 判定窗內的訊號月
for L in (36, 24, 12):
    st_ = []
    for m in months:
        prev = m - 1
        if prev - L not in me.index or prev not in me.index:
            st_.append("缺"); continue
        st_.append("DOWN" if me[prev] / me[prev - L] - 1 < 0 else "UP")
    s = pd.Series(st_, index=months)
    sw = int(((s != s.shift()) & s.shift().notna()).sum())
    down = list(s[s == "DOWN"].index.astype(str))
    print("L＝{}：UP {}｜DOWN {}｜缺 {}｜切換 {} 次｜DOWN 月：{}".format(L, int((s == "UP").sum()), int((s == "DOWN").sum()), int((s == "缺").sum()), sw, down[:40]))
