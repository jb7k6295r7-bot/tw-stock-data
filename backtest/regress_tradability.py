# -*- coding: utf-8 -*-
"""simulate_mtm 新參數 tradable 的【回歸閘門】：tradable=None 時必須與改動前逐位元相同。
用法：record（改動前錄基準）／check（改動後比對）
覆蓋路徑：原版、stop（P7）、log、queue_days＋d_max（P1）、cash_mode=bench（P3）
⭐ 錨在本線自己的改動上：同一棵樹、同一批資料、同一組種子 ⇒ 唯一的差別是引擎那幾行。"""
import os, sys, json, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, researchp7 as P7, researchp1 as P1, p4_features as P4F, research11 as R

mode = sys.argv[1]
BASE = "backtest/results_step2/regress_tradability_base.json"
cal = D.load_calendar(); ncal = len(cal)
uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
sig = P7.build_sig_gate_b(panel, cal, closes, opens)
bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
CFG = {
    "plain": dict(),
    "stop_fix": dict(stop=("fix", 0.10)),
    "stop_trail": dict(stop=("trail", 0.15)),
    "log": dict(log=True),
    "queue": dict(d_max=2, queue_days=3, log=True),
    "bench": dict(cash_mode="bench", bench=bench),
}
def run(cfg, seed, **extra):
    kw = dict(cfg); lg = None
    if kw.pop("log", False):
        lg = []; kw["log"] = lg
    out = R.simulate_mtm(sig, "H120", 8, np.random.default_rng(seed), closes, opens, ncal, return_equity=True, **kw, **extra)
    h = hashlib.sha256(np.asarray(out["equity"], float).tobytes()).hexdigest()[:16]
    scal = {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else None) for k, v in out.items()
            if k not in ("equity", "hold_val", "stop_days")}
    lh = hashlib.sha256(json.dumps([sorted((k, str(v)) for k, v in r.items()) for r in lg]).encode()).hexdigest()[:16] if lg is not None else ""
    return {"eq": h, "scal": scal, "log": lh}
res = {f"{name}/{s}": run(cfg, s) for name, cfg in CFG.items() for s in (0, 1, 2)}
if mode == "record":
    json.dump(res, open(BASE, "w"), ensure_ascii=False, indent=1)
    print("✅ 已錄基準 {} 組 ⇒ {}".format(len(res), BASE))
else:
    base = json.load(open(BASE))
    bad = [k for k in base if json.dumps(base[k], sort_keys=True) != json.dumps(res[k], sort_keys=True)]
    print("回歸 {} 組｜不同 {} 組 {}".format(len(base), len(bad), bad[:5]))
    assert not bad, "⛔ tradable=None 不是逐位元相同"
    print("✅ tradable=None 與改動前逐位元相同（equity sha、全部純量輸出、log 內容）")
