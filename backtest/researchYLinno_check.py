# -*- coding: utf-8 -*-
"""researchYLinno 簡短查核（⛔ 不 import researchYLinno）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLinno_check.py

① audit_seed0 買進列自己數：每筆用原始 stocks/<代號>.csv 該日（含之前最後一列）的 name 判「-創」⇒ 筆數對 summary
② 剔除後的訊號數：自己從 resultsN17/sig_edc6f/and_signals.csv.gz 主窗列、同法判名稱 ⇒ 剔除筆數對 summary
③ summary 的差 ＝ 剔除 − 原版；≥ 0.5 點旗標自己重判
"""
import csv
import re
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D

OUT = "backtest/resultsYLinno"
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
cal = [str(d.date()) for d in D.load_calendar()]
cache = {}


def name_at(sid, d):
    if sid not in cache:
        rows = list(csv.DictReader(open(os.path.join(D.DATA, "stocks", sid + ".csv"), encoding="utf-8")))
        cache[sid] = [(r["date"], r["name"]) for r in rows]
    nm = ""
    for dd, n_ in cache[sid]:
        if dd <= d:
            nm = n_
        else:
            break
    return nm


errs = []; info = {}
au = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str})
b = au[au["side"] == "buy"]
k = sum(bool(re.search(r"-(?:KY)?創", name_at(s, cal[int(t)]))) for s, t in zip(b["sid"], b["t"]))
info["① 買進筆／創新板（自算／檔）"] = [len(b), k, S["① 主窗實際成交（audit_seed0 買進）"]["創新板（當天名稱）"]]
if k != S["① 主窗實際成交（audit_seed0 買進）"]["創新板（當天名稱）"] or len(b) != S["① 主窗實際成交（audit_seed0 買進）"]["筆"]:
    errs.append("①")
A = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), dtype={"sid": str})
w0, w1 = cal.index("2017-03-02"), cal.index("2026-08-24")
A = A[(A["entry_pos"] >= w0) & (A["entry_pos"] <= w1)]
k2 = sum(bool(re.search(r"-(?:KY)?創", name_at(s, cal[int(p)]))) for s, p in zip(A["sid"], A["pos"]))
info["② 主窗訊號／創新板（自算／檔）"] = [len(A), k2, S["主窗訊號"]["創新板（當天名稱）"]]
if k2 != S["主窗訊號"]["創新板（當天名稱）"]:
    errs.append("②")
for seg, (dc, dm) in S["差（剔除 − 原版；[年化, 回落]）"].items():
    a_, b_ = S["剔除創新板（當天名稱）"][seg], S["原版（種子 0）"][seg]
    if abs((a_[0] - b_[0]) - dc) > 1e-15 or abs((a_[1] - b_[1]) - dm) > 1e-15:
        errs.append(f"③ {seg} 差")
    if (abs(dc) >= 0.005 or abs(dm) >= 0.005) != S["差 ≥ 0.5 點"][seg]:
        errs.append(f"③ {seg} 旗標")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(info, ensure_ascii=False)); [print("  ⛔", e) for e in errs]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
