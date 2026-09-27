# -*- coding: utf-8 -*-
"""researchAudit5_4 的獨立查核（⛔ 不 import researchAudit5_4）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit5_4_check.py

① 強勢類股：從 resultsSector/cells.csv 自己標退化（平均持股 ＜ 5 或現金 ＞ 30%，探索段月換續抱）、自己照原挑法重挑 ⇒ 對 Sector_summary.json；
   新格確認段標籤自己用 body.json 的 0050 判；對照臂 p 從 Sector_controls.csv.gz 自己算
② 跌深加碼：自己寫階的上膛／觸發（D2：250 日新高重新上膛；D3 (b)：窗首前已跌破的階視為已觸發）走 0050 距一年高序列，
   主窗探索段各梯每階觸發次數 ⇒ 對 Dip_explore_cells.csv（同梯各格應相同）
⇒ resultsAudit5/4/check.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
HERE = os.path.expanduser("~/tw-p17/backtest"); OUT = os.path.join(HERE, "resultsAudit5", "4")
RP = dict(float_precision="round_trip")
errs = []; info = {}
# ①
T = pd.read_csv(os.path.join(HERE, "resultsSector", "cells.csv"), **RP)
J = json.load(open(os.path.join(HERE, "resultsSector", "body.json"), encoding="utf-8"))
S = json.load(open(os.path.join(OUT, "Sector_summary.json"), encoding="utf-8"))
ex = T[(T["段"] == "探索") & (T["版本"] == "月換續抱")].copy()
deg = sorted(ex.loc[(ex["平均持股"] < 5) | (ex["現金比例"] > 0.30), "格"])
if deg != sorted(S["退化格"]):
    errs.append("① 退化格清單")
z = J["0050"]
nd = ex[~ex["格"].isin(deg)].copy()
passed = nd[(nd["年化"] > z["探索"]["年化"]) & (nd["比值"] >= z["探索"]["比值"])]
pool = passed if len(passed) else nd
pool = pool.assign(_p=(pool["挑法"] == "b").astype(int))
best = pool.sort_values(["比值", "年化", "L", "k", "_p"], ascending=[False, False, True, True, True]).iloc[0]["格"]
info["① 自挑"] = best
if best != S["新挑中"]["格"]:
    errs.append("① 重挑")
cf = S["新格結果"]["確認_強制出場開"]
lab = "合格" if (cf["年化"] > z["確認"]["年化"] and cf["年化"] / abs(cf["回落"]) >= z["確認"]["年化"] / abs(z["確認"]["回落"])) else ("另列" if cf["年化"] > z["確認"]["年化"] else "不合格")
if lab != cf["標籤"]:
    errs.append("① 標籤")
CT = pd.read_csv(os.path.join(OUT, "Sector_controls.csv.gz"), **RP)
for arm in ("c", "fake"):
    x = CT[CT["arm"] == arm]["確認_年化"].to_numpy(float)
    p = float(np.mean(x >= cf["年化"]))
    info[f"① p_{arm}"] = p
    if abs(p - S["對照"][arm]["p（年化 ≥ 本格）"]) > 0 or len(x) != 1000:
        errs.append(f"① p {arm}")
# ②
from backtest import researchTri as T_
from backtest import researchDip as DP
G = T_.load_all(); pos = G["pos"]
dd, NH, _ = DP.dd_series(G)
i0, i1 = pos[DP.EXP[0]], pos[DP.EXP[1]]
X = pd.read_csv(os.path.join(OUT, "Dip_explore_cells.csv"))
for L, th in DP.LADDER.items():
    armed = [not (dd[i0 - 1] <= -x) for x in th]; cnt = [0] * len(th)
    for t in range(i0 + 1, i1 + 1):
        if NH[t - 1]:
            armed = [True] * len(th)
        for j, x in enumerate(th):
            if armed[j] and dd[t - 1] <= -x:
                armed[j] = False; cnt[j] += 1
    info[f"② {L} 各階觸發（自算）"] = cnt
    sub = X[(X["窗"] == "主窗") & (X["梯"] == L)]
    got = [sorted(set(sub[f"觸發−{int(x * 100)}%"])) for x in th]
    info[f"② {L} 各階觸發（檔）"] = got
    if any(g != [c] for g, c in zip(got, cnt)):
        errs.append(f"② {L}：自算 {cnt} vs 檔 {got}")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
