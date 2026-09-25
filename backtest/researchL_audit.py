# -*- coding: utf-8 -*-
"""PREREGL §四① 官方對帳閘（⛔ 不看報酬）：本支只做【抽樣＋取本庫值】；官方值由瀏覽器讀 TWSE 公開頁後填入比對。

抽樣（登錄寫「以種子 20260925 在判定窗內抽 3 檔上市股 × 3 個交易日」，程序本線寫死如下，看任何值之前定）：
  母體 ＝ gate3 母體中 market＝twse、且 stocks_inst 與 stocks_margin 兩檔都存在的股票，依代號排序
  rng ＝ numpy default_rng(20260925)；先抽 3 檔（不放回），再從判定窗 [2017-03-02, 2026-08-24] 的交易日抽 3 天（不放回），日期排序
  ⇒ 9 對 ＝ 3 檔 × 3 天；若某檔某天在本庫無列 ⇒ 記錄並取該檔之後第一個有列的交易日（計數必報）
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D = H2.D
M = H2.SHA
root = os.path.expanduser(f"~/h2data/{M}/data")
stocks = pd.read_csv(os.path.join(root, "meta", "stocks.csv"), dtype=str)
U = H2.UG.gate3(stocks)
U = U[U["market"] == "twse"]
pool = sorted(s for s in U["stock_id"] if os.path.exists(os.path.join(root, "stocks_inst", f"{s}.csv")) and os.path.exists(os.path.join(root, "stocks_margin", f"{s}.csv")))
cal = D.load_calendar()
w = cal[(cal >= "2017-03-02") & (cal <= "2026-08-24")]
rng = np.random.default_rng(20260925)
sids = list(rng.choice(pool, 3, replace=False))
days = sorted(rng.choice(np.arange(len(w)), 3, replace=False))
rows = []
for s in sids:
    inst = pd.read_csv(os.path.join(root, "stocks_inst", f"{s}.csv"), dtype={"stock_id": str}).set_index("date")
    mar = pd.read_csv(os.path.join(root, "stocks_margin", f"{s}.csv"), dtype={"stock_id": str}).set_index("date")
    for di in days:
        d0 = str(w[di].date()); d = d0; k = di
        while not (d in inst.index and d in mar.index):
            k += 1; d = str(w[k].date())
        rows.append({"sid": s, "抽中日": d0, "比對日": d, "順延": d != d0, "trust（股）": int(inst.loc[d, "trust"]), "m_balance（張）": int(mar.loc[d, "m_balance"])})
X = pd.DataFrame(rows)
print("母體 {} 檔｜抽中 {}｜日 {}".format(len(pool), sids, [str(w[i].date()) for i in days]))
print(X.to_string(index=False))
os.makedirs(os.path.expanduser("~/tw-p17/backtest/resultsL"), exist_ok=True)
X.to_csv(os.path.expanduser("~/tw-p17/backtest/resultsL/audit_local.csv"), index=False)
