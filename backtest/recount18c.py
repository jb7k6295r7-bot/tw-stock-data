# -*- coding: utf-8 -*-
"""18 股-月之謎：**結案**。⭐ 436／30 檔【可逐數重現】。

⛔⛔ 先自陳本線前兩趟錯在哪（⭐ 留著，因為錯法比結論有用）：
  ① `recount18.py`（0932）把「真下市」定義成 universe 的 last_seen 早於資料末日
     ⇒ ⛔ 而本線【自己 0305 交件】§1-1 的定義是
        **「來源裡【整檔沒有】營收史」** ⇒ 兩個完全不同的量。
  ② `recount18b.py` 改對了定義，⛔ 但【漏了閘門】：只切窗、沒有套 `eligible`
     ⇒ 分母 113,007 列（0305 是 36,577 列）⇒ 分子當然也對不上（1,966 vs 436）。

⭐⭐ 關鍵的一步（⛔ 而且它不是「掃定義去湊 436」）：
  **先對【分母】**。0305 §1-1 白紙黑字寫了主格是「36,577 列／1,513 檔」——
  那是對方給的【錨】，⇒ 對錨是合法的對帳；
  ⛔ 對「436」本身去調參數才是湊數字（台股策略線 0951 §三 明令不可）。
  ⇒ 分母一對上（eligible ∧ 2021-01~2026-03），分子【自己掉出來】＝ 446／31 檔，
    再依 0305 自己寫的組成拆成 30 真下市 ＋ 1 TDR(9103 美德醫療-DR) ⇒ **436／30**。

⇒ ⭐ 結論：那 18 股-月的差【不存在】——它是本線 0932 用錯定義＋漏閘門造出來的。
   台股策略線 20260923-1213 §四 事前寫死的兩條出口 ⇒ 落在 **(Ⅰ)**：這一格結案。
"""
from __future__ import annotations
import os, sys
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import p4_features as P4F
from backtest import research34 as R34
from backtest import data as D

WIN_LO, WIN_HI = "2021-01", "2026-03"        # ⭐ 0305 §1-3 的主格（⛔ 不是 P12 的主格窗）
TARGET_ROWS, TARGET_SIDS = 36577, 1513       # ⭐ 0305 §1-1 寫死的分母 ⇒ 本支的【錨】
TARGET_SM, TARGET_N = 436, 30                # ⭐ 0305 §1-1 的真下市數（⛔ 不是調參目標）

panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz").copy()
rev, _rev_ly, _ind = R34.load_revenue()      # ⭐ 它回三個，⛔ 不是一個
uni = D.load_universe()

# ⭐⭐ 0305 §1-1 的「真下市（倖存者）」＝ 來源裡【整檔沒有】營收史
in_rev = set(rev.columns)
no_rev = {s for s in set(panel["stock_id"])
          if s not in in_rev or rev[s].notna().sum() == 0}

panel["ym"] = panel["measure_date"].astype(str).str.slice(0, 7)
sub = panel[(panel["ym"] >= WIN_LO) & (panel["ym"] <= WIN_HI) & (panel["eligible"] > 0)]
nan = sub[sub["rev_hi24"].isna()]
dl  = nan[nan["stock_id"].isin(no_rev)]

# ⛔ 閘門一：分母必須逐數等於 0305 §1-1
assert len(sub) == TARGET_ROWS and sub["stock_id"].nunique() == TARGET_SIDS, \
    "分母不符 0305 §1-1：{:,} 列／{:,} 檔".format(len(sub), sub["stock_id"].nunique())

g = dl.groupby("stock_id").size().sort_values(ascending=False)
tdr = [s for s in g.index if str(s).startswith("91")]      # ⭐ 台股 91x ＝ TDR
sm  = int(g.sum()) - int(g[tdr].sum() if tdr else 0)
n   = len(g) - len(tdr)

# ⛔ 閘門二：拆完之後必須逐數等於 0305 §1-1 的 436／30
assert sm == TARGET_SM and n == TARGET_N, "真下市不符：{} 股-月／{} 檔".format(sm, n)

nm = dict(zip(uni["stock_id"].astype(str), uni["name"].astype(str))) if "name" in uni.columns else {}
print("⭐ 分母        {:>7,} 列／{:>5,} 檔   ⇐ 0305 §1-1 ＝ 36,577／1,513  ⇒ ⭐ 相符".format(
      len(sub), sub["stock_id"].nunique()))
print("⭐ rev_hi24 NaN {:>6,} 股-月／{:>4} 檔   ⇐ 0305 §1-1 合計 ＝ 446／31   ⇒ ⭐ 相符".format(
      len(dl), dl["stock_id"].nunique()))
print("   ├ TDR（91x）   {:>4} 股-月／{:>3} 檔".format(int(g[tdr].sum() if tdr else 0), len(tdr)))
print("   └ 真下市       {:>4} 股-月／{:>3} 檔   ⇐ 0305 §1-1 ＝ 436／30    ⇒ ⭐⭐ 相符".format(sm, n))
print()
print("=== 那 30 檔的代號（⇐ 台股策略線 0951 §三 說名單在本線 0305 交件裡；⭐ 這是重算出來的同一份）===")
for s, k in g.items():
    if s in tdr:
        continue
    print("   {:<8}{:>4} 股-月   {}".format(s, k, nm.get(str(s), "")))
print("   ⛔ 不在 30 檔內：{} {} ＝ **TDR**，0305 §1-1 已單獨列為 1 檔／{} 股-月".format(
      tdr[0], nm.get(str(tdr[0]), ""), int(g[tdr].sum())) if tdr else "")
print()
print("⇒ ⭐ 兩道閘門皆過 ⇒ 台股策略線 1213 §四 的出口 **(Ⅰ)**：18 的差是本線口徑錯，⛔ 不是資料差。")

# =====================================================================
# ⛔⛔ 本線在【上一個 commit(16aa3559e) 的訊息裡】寫錯了一句，在此更正：
#
#   錯的那句：「5371 中光電、2888 新光金、2809 京城銀、6806 森崴能源
#              …⛔ 現在都還在交易 ⇒ 這一格不是倖存者偏誤，是資料源覆蓋缺口」
#
#   ⭐ 實際查 universe 的 last_seen（資料末日 2026-09-18）：
#      這 30 檔【全部 30 檔都已下市】，仍在市者 ＝ **0 檔**。
#      新光金 2025-07-11／京城銀 2025-09-17／三商壽 2026-08-19／
#      中光電 2026-08-21／森崴能源 2026-06-22 —— 都是【併購下市】，
#      ⇒ 名字耳熟【不等於】還在市，⛔ 而本線就是憑這個印象斷定的。
#
#   ⇒ ⭐ 0305 §1-1 的標籤「真下市（倖存者）」是**對的**，⛔ 錯的是本線的質疑。
#
# ⭐⭐ 留著這一段，因為錯法跟本線 09-23 對《01實戰檢查清單》發錯指控【同一族】：
#     ⛔ 憑印象斷定一個數字／標籤錯 ⇒ 而查一次 last_seen 只要三行。
#     ⚠ 差別只在：那次冤枉的是別線，這次差一點冤枉的是【本線自己的交件】。
# =====================================================================
