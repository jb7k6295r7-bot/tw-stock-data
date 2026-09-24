# -*- coding: utf-8 -*-
"""P12～P17 那一族的停牌退路與開盤漲停筆數（⇐ 裁定線 1714 §一末）。

⭐ 查證後的事實（⛔ 與本線先前的假設不同）：P12～P17 **全部走同一支 researchp7.build_sig_gate_b**
   ⇒ S1 ＝ signal="B"（門檻B，本線 1722 已量 ＝ 0／0）
   ⇒ S0 ＝ signal="ALL"（過閘門就算訊號）  ← ⛔ 還沒量
   ⇒ T0 ＝ P12.sig_hold_to 派生（窗內第一個訊號月整批進場、出場＝窗尾）← ⛔ 還沒量
⇒ 本支量【還沒量過的那兩種】。

兩條退路（research11.simulate_mtm）：
  進場 613–615：opens[sid][t] 非有限或 ≤ 0 ⇒ 改用 ffill 收盤成交（＝用停牌前舊價買）
  出場       ：closes[sid][exit_pos] 是 ffill 的 ⇒ 出場日沒成交就用停牌前收盤「賣出」
另量：進場日【開盤＝漲停價】的筆數（tradability 的 up_o）
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F
from backtest import researchp1 as P1, researchp7 as P7, researchp12 as P12, tradability as T

cal = D.load_calendar(); ncal = len(cal)
uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)

sig_b = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
sig_all = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="ALL")
wins = {k: P12.win_bounds(cal, k) for k in P12.WINDOWS}
sigs = {"S1 門檻B（T1）": sig_b, "S0 全市場ALL（T1）": sig_all}
for s_lab, sg in (("S1", sig_b), ("S0", sig_all)):
    for w, (w0, w1) in wins.items():
        sigs["{} T0／{}".format(s_lab, w)] = P12.sig_hold_to(sg, w0, w1, closes, opens)

allsid = set().union(*[set(v["sid"]) for v in sigs.values()])
trad = T.build(allsid, cal)
print("tradability 旗標建好 {:,} 檔\n".format(len(trad)))

rows = []
for lab, sg in sigs.items():
    n = len(sg)
    ent_bad = 0; ent_up = 0; ex_bad = 0
    for sid, e, x in zip(sg["sid"], sg["entry_pos"].astype(int), sg["xpos_H120"].astype(int)):
        o = opens[sid][e] if e < len(opens[sid]) else np.nan
        if not np.isfinite(o) or o <= 0:
            ent_bad += 1
        if trad[sid]["up_o"][e]:
            ent_up += 1
        if x < ncal and not trad[sid]["trd"][x]:
            ex_bad += 1
    rows.append({"sig": lab, "筆數": n, "進場走退路": ent_bad, "進場開盤漲停": ent_up, "出場日沒成交": ex_bad})
    print("{:<22}{:>7,} 筆｜進場走退路 {:>3}｜進場開盤漲停 {:>3}｜出場日沒成交 {:>3}".format(
        lab, n, ent_bad, ent_up, ex_bad))
df = pd.DataFrame(rows)
df.to_csv("backtest/results_step2/halt_p12_p17.csv", index=False, encoding="utf-8")
tot = df[["進場走退路", "進場開盤漲停", "出場日沒成交"]].sum()
print("\n=== ⭐ 合計（訊號層上限，⛔ 不是組合層實際成交）===")
print("  進場走退路 {}｜進場開盤漲停 {}｜出場日沒成交 {}｜總訊號 {:,}".format(
    int(tot["進場走退路"]), int(tot["進場開盤漲停"]), int(tot["出場日沒成交"]), int(df["筆數"].sum())))
print("\n⇒ 落檔 backtest/results_step2/halt_p12_p17.csv")
