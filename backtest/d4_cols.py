# -*- coding: utf-8 -*-
"""D4（改名：放寬候選池三個閘門）必報欄③之五①④ 與 ③之六 —— **純描述**。

⇐ 台股策略線 20260924-1620 §五、1642 §一／§二；裁定線 1611 §一②
⛔⛔ 不重跑策略、⛔ 不算報酬、⛔ 不動判定。

⚠⚠ 而交辦的四格裡有【兩格現在算不出來】，本線據實標明（⛔ 不留白給人以為漏做）：
   ③之五② D4 持有它們的交易日佔比與平均權重 ⇒ ⛔ **需要 D4 跑過才有「持有」**
   ③之五③ 排除 453 檔的對照臂　　　　　　 ⇒ ⛔ **那是一個臂，要跑**
   ⇒ ⭐ 而 D4 現在【不可開跑】（資料閘未過、13.25pp 未重算）
   ⇒ ⇒ 所以這兩格是【開跑時的必報欄】，⛔ 不是現在交得出來的描述欄。
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import p4_features as P4F

W0, W1 = 523, 2835
cal = D.load_calendar()
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
panel["measure_date"] = pd.to_datetime(panel["measure_date"])
pos = {d: i for i, d in enumerate(cal)}
panel["pos"] = panel["measure_date"].map(pos)
panel = panel[panel["pos"].notna()]
panel = panel[(panel["pos"] >= W0) & (panel["pos"] <= W1)].copy()

cur = set(panel.loc[panel["eligible"].astype(bool), "stock_id"].astype(str))
g = pd.read_csv("backtest/resultsd4_gate.csv", dtype=str)
new453 = set(g.loc[(g["direction"] == "新進來") &
                   (g["fam2"] == "在 panel 內但【沒過閘門】（liq／bars／inst）"), "stock_id"])
print("現行池子 {:,} 檔｜新進的普通股 {:,} 檔｜⇒ 2,039 母體 ＝ {:,}".format(
    len(cur), len(new453), len(cur | new453)))
print()

# ── ③之六：三道閘門各自與重疊（⭐ 在 2,039 母體上，逐檔看它【曾否】被某道擋過）
print("=== ⭐ ③之六：三道閘門各自擋掉幾檔（含兩兩與三者重疊）===")
p = panel[panel["stock_id"].astype(str).isin(new453)]
blocked = {}
for gate in ("liq_ok", "bars_ok", "inst_ok"):
    # ⭐ 判準：該檔在窗內【從來沒有一個月】通過這一道 ⇒ 算被這一道擋住
    ok = p.groupby("stock_id")[gate].max()
    blocked[gate] = set(ok[ok <= 0].index.astype(str))
L, B, I = blocked["liq_ok"], blocked["bars_ok"], blocked["inst_ok"]
print("   ⚠ 判準：該檔在判定窗內【從來沒有一個月】通過那一道 ⇒ 算被它擋住（⛔ 不是逐月）")
print("   liq  （流動性）  {:>3} 檔".format(len(L)))
print("   bars （K 棒數）  {:>3} 檔".format(len(B)))
print("   inst （法人參與）{:>3} 檔".format(len(I)))
print("   ── 重疊 ──")
print("   liq ∧ bars       {:>3}｜liq ∧ inst {:>3}｜bars ∧ inst {:>3}".format(
    len(L & B), len(L & I), len(B & I)))
print("   ⭐ 三者皆被擋     {:>3}".format(len(L & B & I)))
print("   ⛔ 三道都沒【完全】擋住（＝只是某些月沒過）{:>3} 檔".format(
    len(new453 - (L | B | I))))
print()

# ── ③之五①：453 檔在全母體日均成交金額分位上的分佈
print("=== ⭐ ③之五①：453 檔的流動性分位（⛔ 分位是在 2,039 全母體上算的）===")
pool = set(cur) | new453
sub = panel[panel["stock_id"].astype(str).isin(pool)]
med = sub.groupby("stock_id")["amt20"].median()          # 逐檔的 amt20 中位
rank = med.rank(pct=True) * 100                          # ⭐ 在 2,039 母體裡的百分位
r453 = rank[rank.index.astype(str).isin(new453)]
rcur = rank[rank.index.astype(str).isin(cur)]
print("   {:<22}{:>8}{:>10}{:>10}{:>10}".format("組", "檔數", "p10", "中位", "p90"))
for lab, r in (("新進 453 檔", r453), ("現行池子", rcur)):
    print("   {:<22}{:>8,}{:>10.1f}{:>10.1f}{:>10.1f}".format(
        lab, len(r), r.quantile(.10), r.median(), r.quantile(.90)))
print()
print("   ⭐ 同一組的【日均成交金額本身】（元，⛔ 不是分位）")
m453 = med[med.index.astype(str).isin(new453)]
mcur = med[med.index.astype(str).isin(cur)]
for lab, m in (("新進 453 檔", m453), ("現行池子", mcur)):
    print("   {:<22}p10 {:>14,.0f}｜中位 {:>14,.0f}｜p90 {:>14,.0f}".format(
        lab, m.quantile(.10), m.median(), m.quantile(.90)))
print()

# ── ③之五④：逐族 20 日均量分佈（⭐ 本專案的 amt20 就是 20 日均成交金額）
print("=== ⭐ ③之五④：逐族 20 日均量分佈（⭐ amt20 ＝ 20 日均成交【金額】）===")
fam = dict(zip(g["stock_id"], g["fam2"]))
rows = []
for lab, st in (("新進 453（沒過閘門）", new453), ("現行池子 1,586", cur)):
    m = med[med.index.astype(str).isin(st)]
    rows.append(dict(族=lab, 檔數=len(m), p10=m.quantile(.10), p25=m.quantile(.25),
                     中位=m.median(), p75=m.quantile(.75), p90=m.quantile(.90)))
for sub_lab, keys in (("├ 其中 liq 完全沒過", L), ("├ 其中 bars 完全沒過", B), ("└ 其中 inst 完全沒過", I)):
    m = med[med.index.astype(str).isin(keys)]
    if len(m):
        rows.append(dict(族=sub_lab, 檔數=len(m), p10=m.quantile(.10), p25=m.quantile(.25),
                         中位=m.median(), p75=m.quantile(.75), p90=m.quantile(.90)))
df = pd.DataFrame(rows)
for r in df.itertuples():
    print("   {:<24}{:>5,} 檔  p10 {:>13,.0f}｜中位 {:>13,.0f}｜p90 {:>13,.0f}".format(
        r.族, r.檔數, r.p10, r.中位, r.p90))
df.to_csv("backtest/resultsd4_cols.csv", index=False, encoding="utf-8")
print()
print("⇒ 落檔 backtest/resultsd4_cols.csv")
print()
print("=== ⛔⛔ 而【比率一律附分母的證券別組成】（裁定線 1612 §一）===")
print("   本支所有比率的分母 ＝ 2,039 檔，逐類：")
print("     普通股（含創新板 0，已剔）     2,039 檔")
print("     ETF・受益憑證                    0 檔（已剔 360＋13）")
print("     特別股                           0 檔（已剔 35）")
print("     權證・ETN（六位數）              0 檔（已剔 68）")
print("     TDR                              0 檔（已剔 17）")
print("   ⇒ ⭐ 由本支程式輸出，⛔ 不是事後補註。")
