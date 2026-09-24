# -*- coding: utf-8 -*-
"""delist_measure.py 在 4 次模擬裡量到「了結 0／無法區分 0」⇒ ⛔ 0 要先說清楚是哪一種 0：
   是「訊號表裡根本沒有出場落在最後成交之後的列」，還是「有，但 8 槽隨機沒挑到」？
⇒ 本支直接數訊號表（⛔ 不跑模擬）：xpos_H120 > 該檔最後成交位置 的列，依狀態分。"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, researchp7 as P7, researchp1 as P1, p4_features as P4F, tradability as T
from backtest import researchp12 as P12

cal = D.load_calendar()
uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
sig_b = P7.build_sig_gate_b(panel, cal, closes, opens)
sig_all = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="ALL")
trad = T.build(set(sig_b["sid"]) | set(sig_all["sid"]), cal)
dl = T.delist_status(trad, cal, official=T.load_official())
rows = []
for lab, sg in (("門檻B H120", sig_b), ("S0 全市場 H120", sig_all)):
    last = sg["sid"].map(lambda s: dl.get(s, {}).get("last", 10 ** 9))
    stt = sg["sid"].map(lambda s: dl.get(s, {}).get("status", "無旗標"))
    after = sg["xpos_H120"] > last
    halted = [not trad[s]["trd"][int(x)] if s in trad and 0 <= int(x) < len(cal) else False
              for s, x in zip(sg["sid"], sg["xpos_H120"])]
    halted = np.array(halted)
    r = dict(訊號=lab, 列數=len(sg), 出場在最後成交之後=int(after.sum()),
             出場日沒成交但之後有成交=int((halted & ~after.to_numpy()).sum()))
    for k, v in stt[after].value_counts().items():
        r["之後且_" + k] = int(v)
    rows.append(r)
X = pd.DataFrame(rows).fillna(0)
print(X.to_string(index=False))
X.to_csv("backtest/results_step2/delist_exposure.csv", index=False, encoding="utf-8")
print("⇒ 落檔 backtest/results_step2/delist_exposure.csv")
