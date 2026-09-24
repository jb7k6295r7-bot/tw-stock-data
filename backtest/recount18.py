# -*- coding: utf-8 -*-
"""回台股策略線 20260923-1213 §四：重數「真下市且 rev_hi24 缺」的股-月。

⛔ 逐字照它寫的口徑（⛔ 本線不自訂）：
  「在【09-20 00:41 之後的同一份 data】上，用【策略線 v8 的 pool 定義】
    （liq_ok ∧ bars_ok ∧ (c)、主格窗）重數『真下市且 rev_hi24 缺』」

⭐ 兩個可能【事前寫在它的信裡】（⛔ 免得量完才挑解釋）：
  (Ⅰ) ＝ 436 ⇒ 那 18 是【資料版本差】的殘留 ⇒ 這一格結案
  (Ⅱ) ≠ 436 ⇒ 真的口徑差 ⇒ 再往下切【窗】（主格窗 vs 全窗）

⚠⚠ 本線要先指出一個【它沒寫、而本線不能自己挑】的軸：
  researchp7 第 87 行逐字：「候選母體＝過閘門股-月（`eligible` ＝ liq_ok ∧ bars_ok ∧ **inst_ok**，(c) 已套）」
  ⇒ ⭐ 而 1213 §四 寫的 pool 是「liq_ok ∧ bars_ok ∧ (c)」——**沒有 inst_ok**
  ⇒ ⇒ ⛔ 這兩個不是同一個母體 ⇒ 本線【兩個都算、都報】（〈一百〇八〉：軸沒指定就都要交代）
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import p4_features as P4F
from backtest import researchp12 as P12

cal = D.load_calendar()
uni = D.load_universe()
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
w0, w1 = P12.win_bounds(cal, "主格窗")
wf0, wf1 = P12.win_bounds(cal, "全窗")
print("主格窗 [{},{}] {} ~ {}".format(w0, w1, cal[w0].date(), cal[w1].date()))
print("全窗   [{},{}] {} ~ {}".format(wf0, wf1, cal[wf0].date(), cal[wf1].date()))
print("panel {:,} 列".format(len(panel)))

pos = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(cal)}
panel = panel.copy()
panel["pos"] = panel["measure_date"].astype(str).map(pos)
panel = panel[panel["pos"].notna()].copy()
panel["pos"] = panel["pos"].astype(int)

# ⭐「真下市」＝ universe 的 last_seen 早於資料末日（⛔ 不是「窗內沒出現」）
last_day = cal[-1]
uni["last_seen"] = pd.to_datetime(uni["last_seen"])
delisted = set(uni.loc[uni["last_seen"] < last_day - pd.Timedelta(days=5), "stock_id"])
print("⭐ 真下市（last_seen 早於資料末日 {} 逾 5 日）＝ {:,} 檔".format(last_day.date(), len(delisted)))
print()

def count(df, lo, hi, use_inst, label):
    m = (df["pos"] >= lo) & (df["pos"] <= hi) & (df["liq_ok"] > 0) & (df["bars_ok"] > 0)
    if use_inst:
        m &= (df["inst_ok"] > 0)
    pool = df[m]
    miss = pool[pool["rev_hi24"].isna()]
    dl = miss[miss["stock_id"].isin(delisted)]
    print("  {:<40} pool {:>7,}｜rev_hi24 缺 {:>6,}｜其中真下市 **{:>5,}** 股-月／{:>3} 檔"
          .format(label, len(pool), len(miss), len(dl), dl["stock_id"].nunique()))
    return len(dl)

print("=== ⭐⭐ 重數結果（⛔ 兩個軸都報）===")
a = count(panel, w0, w1, False, "主格窗・liq∧bars（＝1213 §四 的字面）")
b = count(panel, w0, w1, True,  "主格窗・liq∧bars∧inst（＝ researchp7 的 eligible）")
c = count(panel, wf0, wf1, False, "全窗・liq∧bars")
d_ = count(panel, wf0, wf1, True,  "全窗・liq∧bars∧inst")
print()
print("=== ⇒ 對照 1213 §四 事前寫死的兩條出口 ===")
for v, lab in ((a, "主格窗・liq∧bars（字面）"), (b, "主格窗・加 inst"),
               (c, "全窗・liq∧bars"), (d_, "全窗・加 inst")):
    if v == 436:
        print("   {:<26} ＝ 436 ⇒ ⭐ **(Ⅰ) 資料版本差的殘留 ⇒ 這一格結案**".format(lab))
    else:
        print("   {:<26} ＝ {:,}　（⛔ ≠436 ⇒ 落在 (Ⅱ)）".format(lab, v))
print()
print("⚠ 而 1213 §四 自己也寫了：不論哪一種，區間那一版（+6.37~+7.37）【早已作廢】")
print("  ⇒ ⭐ 這一格【不擋任何判定】，只是不關掉就會有人再引一次舊數字。")
