# -*- coding: utf-8 -*-
"""PREREGL §四① 官方對帳閘——裁定線 seq143 §一 定字版抽樣（取代 researchL_audit.py 的 9 對 trust 全 0 版；⛔ 不看報酬）

定字（seq143 §一，逐字要點）：
  母體 ＝ 判定窗內、gate3、當日 stocks_inst 與 stocks_margin 都有列、且 trust ≠ 0 的 (股, 日)
  上市 9 對＋上櫃 3 對（上市、上櫃各自抽；不放回；種子 20260925；抽樣程式先寫、先提交 commit 再讀任何官方值）
  比兩欄：trust（股）、m_balance（張）⇒ 12 對 × 2 欄 ＝ 24 格全部完全相等才過；任一格不等 ⇒ 停、回報
本線寫死的程序細節（看任何官方值之前定）：
  ・判定窗 ＝ [2017-03-02, 2026-08-24]（PREREGL seq2 §一②）；資料 ＝ main edc6f8002f 快照（與 H2／L 同一份）
  ・gate3 ＝ researchH2.UG.gate3(meta/stocks.csv)；市場別取 gate3 表的 market 欄（twse ＝ 上市、tpex ＝ 上櫃）
  ・母體列依 (stock_id, date) 字典序排序；rng ＝ numpy default_rng(20260925)
    先從上市母體 rng.choice(不放回) 抽 9 列，再用【同一個 rng】從上櫃母體抽 3 列
  ・輸出我方值：trust（股，int）、m_balance（張，int）；官方值由資料庫線用現成官方抓取代做（seq143 §一分工）
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2

M = H2.SHA
root = os.path.expanduser(f"~/h2data/{M}/data")
W0, W1 = "2017-03-02", "2026-08-24"
stocks = pd.read_csv(os.path.join(root, "meta", "stocks.csv"), dtype=str)
U = H2.UG.gate3(stocks)
pools = {}
for mk in ("twse", "tpex"):
    rows = []
    for s in sorted(U.loc[U["market"] == mk, "stock_id"]):
        fi, fm = os.path.join(root, "stocks_inst", f"{s}.csv"), os.path.join(root, "stocks_margin", f"{s}.csv")
        if not (os.path.exists(fi) and os.path.exists(fm)):
            continue
        a = pd.read_csv(fi, usecols=["date", "trust"]).drop_duplicates("date", keep="last")
        b = pd.read_csv(fm, usecols=["date", "m_balance"]).drop_duplicates("date", keep="last")
        x = a.merge(b, on="date")
        x = x[(x["date"] >= W0) & (x["date"] <= W1) & x["trust"].notna() & x["m_balance"].notna() & (x["trust"] != 0)]
        x.insert(0, "stock_id", s)
        rows.append(x)
    pools[mk] = pd.concat(rows).sort_values(["stock_id", "date"]).reset_index(drop=True)
rng = np.random.default_rng(20260925)
out = []
for mk, k in (("twse", 9), ("tpex", 3)):
    P = pools[mk]
    idx = rng.choice(len(P), k, replace=False)
    t = P.iloc[sorted(idx)].copy()
    t.insert(0, "市場", "上市" if mk == "twse" else "上櫃")
    out.append(t)
    print(f"{mk} 母體 {len(P):,} 對（{P['stock_id'].nunique()} 檔）")
X = pd.concat(out).reset_index(drop=True)
X["trust"] = X["trust"].astype(np.int64); X["m_balance"] = X["m_balance"].astype(np.int64)
X = X.rename(columns={"trust": "我方 trust（股）", "m_balance": "我方 m_balance（張）"})
X["資料快照"] = M
os.makedirs(os.path.expanduser("~/tw-p17/backtest/resultsL"), exist_ok=True)
X.to_csv(os.path.expanduser("~/tw-p17/backtest/resultsL/audit_pairs_seq143.csv"), index=False)
print(X.to_string(index=False))
