# -*- coding: utf-8 -*-
"""researchSigRe 的獨立查核（⛔ 不 import researchSigRe）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSigRe_check.py

① 從 resultsSigRe/cells.csv 自己套退化門檻（觸發 ＜ 1 次／年 或 段尾未出場 ＞ 50%）、自己照原件挑法（合格取比值最高，否則比值最高、同分年化高）重挑 ⇒ 對 summary.json
② 確認段標籤自己用 0050 同段判
③ 接線：自己組原件的 E1〔黃昏之星〕探索段格，強制出場【關】跑 200 顆 ⇒ 年化中位 ＝ resultsSig/cells.csv（原件）逐位元；
   同一格強制出場【開】⇒ 年化中位 ＝ resultsSigRe/cells.csv
⇒ resultsSigRe/check.json
"""
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
import researchSig as RS
from backtest import listexit_lines as L
from backtest import rerun17 as RR
from backtest import research11 as R11

HERE = os.path.expanduser("~/tw-p17/backtest"); OUT = os.path.join(HERE, "resultsSigRe")
RP = dict(float_precision="round_trip")
errs = []; info = {}
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
T = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
ex = T[(T["段"] == "探索") & (T["停損"] == "無") & (T["停利"] == "無") & T["出場"].isin(RS.EXITS)]
for E in ("E1", "E2"):
    g = ex[ex["E"] == E].copy()
    g["bad"] = (g["每檔出場觸發_次每年"] < 1.0) | (g["段尾未出場比例"] > 0.5)
    for _, r in g.iterrows():
        if bool(r["bad"]) != S["退化排除（強制出場開）"][f"{E}_{r['出場']}"]["排除"]:
            errs.append(f"① {E} {r['出場']} 排除旗標")
    ok = g[~g["bad"]]
    if len(ok):
        pool = ok[ok["label"] == "合格"] if (ok["label"] == "合格").any() else ok
        mine = pool.sort_values(["ratio", "cagr_med"], ascending=[False, False]).iloc[0]["出場"]
    else:
        mine = None
    info[f"① {E} 自挑"] = mine
    if mine != S["探索段挑出場（事後重挑）"][E]:
        errs.append(f"① {E} 挑")
B = S["0050同段"]["確認"]
for E in ("E1", "E2"):
    ch = S["探索段挑出場（事後重挑）"][E]
    if ch is None:
        continue
    q = T[(T["段"] == "確認") & (T["E"] == E) & (T["出場"] == ch) & (T["停損"] == "無") & (T["停利"] == "無")].iloc[0]
    c, m = q["cagr_med"], q["mdd_med"]
    lab = "合格" if (c > B["cagr"] and c / abs(m) >= B["cagr"] / abs(B["mdd"])) else ("另列" if c > B["cagr"] else "不合格")
    if lab != q["label"]:
        errs.append(f"② {E} 標籤")
    info[f"② {E} 確認"] = [float(c), float(m), lab]
# ③ 接線
D = RS.D
cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
s0, s1 = int(cal.searchsorted(pd.Timestamp(RS.SEG["探索"][0]))), int(cal.searchsorted(pd.Timestamp(RS.SEG["探索"][1])))
sids, elig, mk = RS.stock_universe(cal, RS.PANEL, os.path.join(RS.RV.H2.H2D, "meta", "stocks.csv"))
SIG, VAL = pickle.load(open(os.path.join(HERE, "resultsSig", "sig_cache.pkl"), "rb"))
RR.use_snapshot()
cz, oz = RR.load_prices(sorted(SIG), cal, mk, "branch")
R, _, _ = RS.build_rows(SIG, elig, mon, "E1", "EVE", s0, s1); R = R.reset_index(drop=True)
SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
sig, kw, reason = RS.make_cell(R, SD, s1, "無", "無", cz, oz)
valid = {s: np.unpackbits(VAL[s])[:ncal].astype(bool) for s in SIG}
SF = {}
for s, v in valid.items():
    b = np.flatnonzero(v)
    if len(b) and b[-1] < s1:
        SF[s] = int(b[-1])
for tag, sf, ref in (("關", None, pd.read_csv(os.path.join(HERE, "resultsSig", "cells.csv"), **RP)), ("開", SF, T)):
    cs = []
    for r in range(200):
        o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, stop_force=sf, **kw)
        c_, _, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)
        cs.append(float(c_))
    med = float(np.median(cs))
    q = ref[(ref["段"] == "探索") & (ref["E"] == "E1") & (ref["出場"] == "EVE") & (ref["停損"] == "無") & (ref["停利"] == "無")].iloc[0]
    info[f"③ E1 黃昏之星 探索 強制出場{tag} 年化中位（自跑／檔）"] = [med, float(q["cagr_med"])]
    if repr(med) != repr(float(q["cagr_med"])):
        errs.append(f"③ 強制出場{tag}")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
