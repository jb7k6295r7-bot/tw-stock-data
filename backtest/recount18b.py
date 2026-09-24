# -*- coding: utf-8 -*-
"""18 股-月：**回原路**用本線 0305 那一趟的定義重數。

⛔⛔ 本線 0932 那一趟【定義用錯了】，逐字自陳：
   本線 0932 用的「真下市」＝ universe 的 last_seen 早於資料末日逾 5 日
   ⇒ ⛔ 而本線【自己 0305 交件】§1-1 的定義是：
      **「來源裡【整檔沒有】營收史」⇒ 真下市（倖存者）⇒ NaN 留在主格**
   ⇒ ⇒ 兩個完全不同的量 ⇒ 難怪 134 對不上 436。

⭐ 台股策略線 20260924-0951 §三 指出的也是這一件：
   「436 與 30 檔都出自你那一趟，⛔ 不是本線的量」
   「要關這一格，最便宜的一步是【回原路】⇒ ⛔ 不是新寫一支 recount18.py」
⇒ ⭐ 本支就是回原路。

⚠ 另一個本線 0932 也弄錯的軸：**主格的窗**
   0932 用 P12.win_bounds 的「主格窗」＝ 2023-07-03 ~ 2025-04-09
   ⛔ 而 0305 §1-3 的主格是 **2021-01 ~ 2026-03**（四型那一格的窗）
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import p4_features as P4F
from backtest import research34 as R34

cal = D.load_calendar()
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
rev, _rev_ly, _ind = R34.load_revenue()   # ⭐ 它回三個，⛔ 不是一個
print("panel {:,} 列｜rev {} 期 × {} 檔".format(len(panel), rev.shape[0], rev.shape[1]))

# ⭐⭐ 0305 §1-1 的定義：「來源裡【整檔沒有】營收史」
in_rev = set(rev.columns)
all_sids = set(panel["stock_id"])
no_rev = {s for s in all_sids if s not in in_rev or rev[s].notna().sum() == 0}
print("⭐ 來源裡【整檔沒有】營收史 ＝ {:,} 檔（0305 定義的「真下市」）".format(len(no_rev)))

panel = panel.copy()
panel["ym"] = panel["measure_date"].astype(str).str.slice(0, 7)

def count(lo, hi, label):
    m = (panel["ym"] >= lo) & (panel["ym"] <= hi)
    sub = panel[m]
    nan = sub[sub["rev_hi24"].isna()]
    dl = nan[nan["stock_id"].isin(no_rev)]
    print("  {:<32} 列 {:>7,}｜rev_hi24 NaN {:>6,}｜其中整檔無營收史 **{:>5,}** 股-月／**{:>3}** 檔"
          .format(label, len(sub), len(nan), len(dl), dl["stock_id"].nunique()))
    return len(dl), dl["stock_id"].nunique(), sorted(dl["stock_id"].unique())

print()
print("=== ⭐⭐ 用 0305 的定義重數（⛔ 不掃參數、不湊數字）===")
a = count("2021-01", "2026-03", "主格 2021-01~2026-03（0305 §1-3）")
b = count("2023-07", "2025-04", "P12 主格窗（⛔ 本線 0932 誤用的那個）")
c = count("2017-03", "2026-08", "全窗")
print()
print("=== ⇒ 對照本線 0305 §1-1 交出的【30 檔／436 股-月】===")
for v, lab in ((a, "主格 2021-01~2026-03"), (b, "P12 主格窗"), (c, "全窗")):
    n, k, _ = v
    tag = "⭐⭐ **相符**" if (n == 436 and k == 30) else ("⚠ 檔數相符、股-月不符" if k == 30 else "⛔ 不符")
    print("   {:<26} {:>5,} 股-月／{:>3} 檔  ⇒ {}".format(lab, n, k, tag))
print()
best = a if a[1] == 30 else (b if b[1] == 30 else c)
if best[1] == 30:
    print("=== ⭐ 那 30 檔的代號（⇐ 台股策略線 0951 §三 說名單在本線自己的交件裡）===")
    print("   " + "、".join(best[2]))
print()
print("⚠ 本支【沒有】去調整定義以湊出 436 —— 只把 0305 的定義原樣套回來。")
