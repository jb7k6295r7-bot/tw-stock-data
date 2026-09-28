# -*- coding: utf-8 -*-
"""researchMomX_n 的查核（⛔ 不 import researchMomX_n）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchMomX_n_check.py

① N＝10、20 兩格三段（探索、確認、早年）的年化、回落 ＝ 原件 resultsMomX/cells.csv（逐位元，自己讀兩檔比）
② 每列標籤自己用 0050 同段重判
③ N＝5 的平均持股 ≤ 5、N 越大平均持股越大（構造一致性）
⚠ 範圍：N＝5 沒有原件可比、⛔ 沒有另寫模擬器獨立重算（原件換股簿只 import 未改；N＝10／20 逐位元相同即證明接線）
⇒ resultsMomX/nsens/check.json
"""
import json
import os

import pandas as pd

HERE = os.path.expanduser("~/tw-p17/backtest"); OUT = os.path.join(HERE, "resultsMomX", "nsens")
RP = dict(float_precision="round_trip")
errs = []; info = {}
T = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP); ref = pd.read_csv(os.path.join(HERE, "resultsMomX", "cells.csv"), **RP)
nq = 0
for r in T.to_dict("records"):
    if r["N"] in (10, 20):
        q = ref[(ref["世界"] == r["世界"]) & (ref["格"] == r["格"]) & (ref["段"] == r["段"])].iloc[0]
        nq += 1
        if repr(float(q["年化"])) != repr(float(r["年化"])) or repr(float(q["回落"])) != repr(float(r["回落"])):
            errs.append(f"① {r['世界']} {r['格']} {r['段']}")
    c, m, c0, m0 = r["年化"], r["回落"], r["0050年化"], r["0050回落"]
    lab = "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")
    if lab != r["標籤"]:
        errs.append(f"② {r['世界']} {r['格']} {r['段']} 標籤")
for (w, s), g in T.groupby(["世界", "段"]):
    h = g.set_index("N")["平均持股"]
    if not (h[5] <= 5 + 1e-9 and h[5] <= h[10] <= h[20]):
        errs.append(f"③ {w} {s} 平均持股")
info["① 比對列"] = nq; info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(info, ensure_ascii=False)); [print("  ⛔", e) for e in errs]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
