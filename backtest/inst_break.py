# -*- coding: utf-8 -*-
"""查資料庫線 20260924-2121 §二 的口徑陷阱，在【本線實際讀的那份資料】上成不成立。

資料庫線警告的是**大盤**法人金額表（BFI82U／上櫃彙總）的列名四代，
而「外資及陸資」在 2015 是**含**外資自營商、2018 起改名並**不含**。

⭐ 本線讀的是**個股**表 `data/stocks_inst/<sid>.csv`（欄：foreign trust dealer total
   dealer_self dealer_hedge），它經 p4_features.fore20 進 inst_ok → eligible → P4 面板
   → 1,586／2,039／D4 ⇒ ⚠ 所以同一個陷阱若在這裡成立，影響的是【母體本身】。

本支驗三件（⛔ 都是可證偽的）：
  ① 全庫表頭只有一種嗎（⇒ 欄有沒有代次）
  ② 恆等式 foreign + trust + dealer ＝ total，逐年成立嗎（⛔ 若 2018 起破 ⇒ foreign 換口徑了）
  ③ 恆等式 dealer_self + dealer_hedge ＝ dealer，逐年成立嗎
"""
from __future__ import annotations
import os
import glob
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17"))
COLS = ["date", "stock_id", "foreign", "trust", "dealer", "total", "dealer_self", "dealer_hedge"]

files = sorted(glob.glob("data/stocks_inst/*.csv"))
print("=== ① 全庫 {:,} 個檔的表頭種類 ===".format(len(files)))
heads = {}
for f in files:
    with open(f, encoding="utf-8") as fh:
        h = fh.readline().strip()
    heads[h] = heads.get(h, 0) + 1
for h, n in sorted(heads.items(), key=lambda x: -x[1]):
    print("  {:5d} 個：{}".format(n, h))
main_head = ",".join(COLS)
assert heads.get(main_head, 0) >= len(files) - 5, "⛔ 主表頭不是預期那一種"
print("  ⇒ ✅ 只有一種資料表頭（另一個是 _index 之類的清單檔）⇒ ⛔ 個股表沒有欄的代次")

#  ⭐ 取一個夠大的樣本（⛔ 不是 3 檔）：前 400 個純數字代號的檔
sam = [f for f in files if os.path.basename(f)[:4].isdigit()][:400]
print()
print("=== ②③ 逐年驗兩條恆等式（樣本 {} 檔）===".format(len(sam)))
rows = []
for f in sam:
    try:
        d = pd.read_csv(f, usecols=COLS[2:] + ["date"], parse_dates=["date"])
    except Exception:
        continue
    rows.append(d)
D = pd.concat(rows, ignore_index=True)
D["y"] = D["date"].dt.year
print("  合計 {:,} 列，{} ~ {}".format(len(D), D["date"].min().date(), D["date"].max().date()))

D["e1"] = (D["foreign"] + D["trust"] + D["dealer"] - D["total"]).abs()
D["e2"] = (D["dealer_self"] + D["dealer_hedge"] - D["dealer"]).abs()
g = D.groupby("y").agg(列數=("e1", "size"),
                       破恆等式1=("e1", lambda s: int((s > 1).sum())),
                       e1最大=("e1", "max"),
                       破恆等式2=("e2", lambda s: int((s > 1).sum())),
                       e2最大=("e2", "max"))
print(g.to_string())

b1 = int((D["e1"] > 1).sum())
b2 = int((D["e2"] > 1).sum())
print()
print("  ⇒ foreign + trust + dealer ≠ total 的列數 **{:,}**／{:,}".format(b1, len(D)))
print("  ⇒ dealer_self + dealer_hedge ≠ dealer 的列數 **{:,}**／{:,}".format(b2, len(D)))

print()
print("=== ④ ⭐ 判讀 ===")
pre = g.loc[g.index <= 2017, "破恆等式1"].sum()
post = g.loc[g.index >= 2018, "破恆等式1"].sum()
print("  2017 及以前破恆等式① 的列數 {:,}｜2018 及以後 {:,}".format(int(pre), int(post)))
if b1 == 0:
    print("  ⇒ ✅ 恆等式逐年都成立 ⇒ ⭐ 本線讀的個股表在 2015~2026 內【口徑一致】")
    print("     ⇒ ⛔ 資料庫線 §二 的「同名兩口徑」陷阱在【個股表】上沒有發生")
    print("     ⚠ 但那只表示 total 與三個分項互相對得上；")
    print("       ⛔ 它【不保證】foreign 的定義沒有在某一天靜默改變（若 total 同時跟著改，恆等式仍會成立）")
    print("     ⇒ ⏳ 所以本線仍要問資料庫線一句：個股表的 foreign 欄是【哪一個】原始列？")
else:
    print("  ⇒ ⛔ 恆等式有破 ⇒ 要逐年看是不是在 2018 交界 ⇒ 若是，foreign 換過口徑")

#  ⛔ 自測：恆等式檢查必須有鑑別力 —— 故意弄壞一列，它必須被抓到
t = D.head(100).copy()
t.loc[t.index[0], "foreign"] = t.loc[t.index[0], "foreign"] + 1000
bad = int(((t["foreign"] + t["trust"] + t["dealer"] - t["total"]).abs() > 1).sum())
assert bad == 1, "⛔ 故意弄壞一列卻抓到 {} 列 ⇒ 這個檢查沒有鑑別力".format(bad)
print()
print("  ✅ 鑑別力自測：故意把一列的 foreign 加 1000 ⇒ 恰好被抓到 1 列（⛔ 否則 0 破是假的）")
