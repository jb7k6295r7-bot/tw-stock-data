# -*- coding: utf-8 -*-
"""停牌退路筆數（純描述，⇐ 裁定線 1714 §一「決定舊件的『初步』標籤要多大聲」）。
範圍：門檻B 訊號集（researchp7.build_sig_gate_b；P7／P8／P9 等共用）。⛔ 不改引擎、⛔ 不重跑策略。
兩條退路：
  進場：opens[sid][entry_pos] 非有限 ⇒ 引擎 613–615 改用 ffill 收盤成交
  出場：exit_pos 那天沒成交（traded＝False）⇒ closes 是 ffill ⇒ 用停牌前收盤「賣出」
"""
import os, sys, inspect
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, researchp7 as P7, researchp1 as P1, p4_features as P4F
print("build_sig_gate_b 簽名：", inspect.signature(P7.build_sig_gate_b))

cal = D.load_calendar(); ncal = len(cal)
uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
sig = P7.build_sig_gate_b(panel, cal, closes, opens)
print("門檻B 訊號 {:,} 筆／{:,} 檔".format(len(sig), sig["sid"].nunique()))
xcols = [c for c in sig.columns if c.startswith("xpos_")]
print("出場欄：", xcols)
ent_bad = sum(1 for s, e in zip(sig["sid"], sig["entry_pos"]) if not np.isfinite(opens[s][int(e)]) or opens[s][int(e)] <= 0)
print("\n① 進場日 open 非有限（會走 613–615 退路）＝ {} 筆".format(ent_bad))
for xc in xcols:
    xs = sig[xc].astype(int)
    ok = xs < ncal
    bad = sum(1 for s, x in zip(sig.loc[ok, "sid"], xs[ok]) if not np.isfinite(opens[s][x]))
    print("② 出場日沒成交（{}；會用停牌前 ffill 收盤『賣出』）＝ {:,} 筆／{:,}（{:.2f}%）".format(
        xc, bad, int(ok.sum()), bad / max(1, int(ok.sum())) * 100))
print("\n⚠ 以上是【訊號層】的筆數 ＝ 上限；組合層實際成交的是其中被選進槽位的那些（依種子而異）")
