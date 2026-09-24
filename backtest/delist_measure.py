# -*- coding: utf-8 -*-
"""seq98 §二 新規則在真資料上會碰到幾筆（⛔ 描述；舊件不重跑，這只是讓裁定線知道規則的量級）。
兩種訊號：P7 門檻B（逐筆 H120）與 P12 S0 全市場（月度日曆出場 ⇒ 會出現「出場日已下市」）。
報：各檔狀態分佈；每種訊號 × 種子 0／1 的 了結／無法區分／掛到尾 筆數，與權益差。"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, researchp7 as P7, researchp1 as P1, p4_features as P4F, research11 as R, tradability as T
from backtest import researchp12 as P12

cal = D.load_calendar(); ncal = len(cal)
uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
sig_b = P7.build_sig_gate_b(panel, cal, closes, opens)
sig_all = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="ALL")
trad = T.build(set(sig_b["sid"]) | set(sig_all["sid"]), cal)
off = T.load_official()
dl = T.delist_status(trad, cal, official=off)
st = pd.Series({k: v["status"] for k, v in dl.items()})
print("=== 各檔狀態（{} 檔有 tradable 旗標；官方下市清單 {} 檔）===".format(len(dl), len(off)))
print(st.value_counts().to_string())
amb = [(k, v["gap"]) for k, v in dl.items() if v["status"] == "ambig"]
print("  ambig 的 gap 分佈：{}".format(sorted(g for _, g in amb)[:20]))

rows = []
for lab, sg in (("門檻B H120", sig_b), ("S0 全市場 H120", sig_all)):
    for seed in (0, 1):
        a = R.simulate_mtm(sg, "H120", 8, np.random.default_rng(seed), closes, opens, ncal, return_equity=True, tradable=trad)
        b = R.simulate_mtm(sg, "H120", 8, np.random.default_rng(seed), closes, opens, ncal, return_equity=True,
                           tradable=trad, delist=dl)
        rows.append(dict(訊號=lab, 種子=seed, 了結=b["tr_delist_settled"], 無法區分=b["tr_delist_ambig"],
                         舊_掛到尾=a["tr_open_at_end"], 新_掛到尾=b["tr_open_at_end"],
                         舊_年化=a["cagr"], 新_年化=b["cagr"], 年化差pp=(b["cagr"] - a["cagr"]) * 100,
                         舊_回落=a["mdd"], 新_回落=b["mdd"]))
T_ = pd.DataFrame(rows)
print()
print(T_.to_string(index=False))
os.makedirs("backtest/results_step2", exist_ok=True)
T_.to_csv("backtest/results_step2/delist_rule_effect.csv", index=False, encoding="utf-8")
st.value_counts().to_csv("backtest/results_step2/delist_status_counts.csv", encoding="utf-8")
print("⇒ 落檔 results_step2/delist_rule_effect.csv、delist_status_counts.csv（⛔ 描述，不改任何交件）")
