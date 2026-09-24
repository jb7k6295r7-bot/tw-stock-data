# -*- coding: utf-8 -*-
"""simulate_mtm 新參數 delist（裁定線 20260924-2319 seq98 §二）的【回歸閘門】：
tradable 開啟、delist=None 時，必須與改動前逐位元相同（既有 regress_tradability.py 只管 tradable=None）。
用法：record（改動前錄基準）／check（改動後比對）
⭐ 錨在本線自己的改動上：同一棵樹、同一批資料、同一組種子、同一份 tradable 旗標 ⇒ 唯一的差別是引擎那幾行。
"""
import os, sys, json, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, researchp7 as P7, researchp1 as P1, p4_features as P4F, research11 as R, tradability as T
from backtest import researchp12 as P12

mode = sys.argv[1]
BASE = "backtest/results_step2/regress_delist_base.json"
cal = D.load_calendar(); ncal = len(cal)
uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
#  ⭐ 兩種訊號：P7 門檻B（逐筆 H120 出場）與 P12 S0 全市場（月度日曆出場 ⇒ 會出現「出場日已下市」）
sig_b = P7.build_sig_gate_b(panel, cal, closes, opens)
sig_all = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="ALL")
sids = set(sig_b["sid"]) | set(sig_all["sid"])
trad = T.build(sids, cal)
CFG = {
    "B_H120_plain": (sig_b, "H120", dict()),
    "B_H120_stop": (sig_b, "H120", dict(stop=("fix", 0.10))),
    "ALL_H120_plain": (sig_all, "H120", dict()),
}


def run(sig, rule, cfg, seed):
    out = R.simulate_mtm(sig, rule, 8, np.random.default_rng(seed), closes, opens, ncal, return_equity=True,
                         tradable=trad, **cfg)
    h = hashlib.sha256(np.asarray(out["equity"], float).tobytes()).hexdigest()[:16]
    scal = {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else None) for k, v in out.items()
            if k not in ("equity", "hold_val", "stop_days")}
    return {"eq": h, "scal": scal}


for n, (s_, r_, _) in CFG.items():
    assert "xpos_" + r_ in s_.columns, "⛔ {} 的訊號表沒有 xpos_{}".format(n, r_)
res = {"{}/{}".format(n, s): run(sig, r, cfg, s) for n, (sig, r, cfg) in CFG.items() for s in (0, 1)}
if mode == "record":
    json.dump(res, open(BASE, "w"), ensure_ascii=False, indent=1)
    print("✅ 已錄基準 {} 組 ⇒ {}".format(len(res), BASE))
else:
    base = json.load(open(BASE))
    #  ⛔ 第一版用 dict 直接比 ⇒ delay_med 是 NaN、NaN ≠ NaN ⇒ 6 組全部假紅（引擎其實沒變）
    #  ✅ 照既有 regress_tradability.py 的比法：json.dumps(sort_keys) 後比字串（NaN 序列化成同一個字）
    bad = [k for k in base if json.dumps(base[k], sort_keys=True) != json.dumps(res.get(k), sort_keys=True)]
    for k in base:
        print("  {:20s} 權益 sha 基準 {}｜現在 {}".format(k, base[k]["eq"], res[k]["eq"]))
    for k in bad:
        print("  ⛔ {}：基準 {} ／ 現在 {}".format(k, base[k]["eq"], res[k]["eq"]))
    assert not bad, "⛔ tradable 開、delist=None 的路徑變了 {} 組".format(len(bad))
    print("✅ tradable 開、delist=None：{} 組逐位元相同（權益雜湊＋全部純量輸出）".format(len(base)))
