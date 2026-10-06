# -*- coding: utf-8 -*-
"""USREG-W1b 重跑（2026-10-07 台北）舊（0043f97，備份 ~/us_work/w1b_old/）→ 新（60d2f99）差異 ⇒ resultsUSW1b/rerun_diff.json。
⛔ 只輸出計數、代號、季數、標籤與彙總報酬（無營收值、無價格、無逐筆）。
    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSW1b_rerundiff
"""
import json, os, pandas as pd, numpy as np
O = os.path.expanduser("~/us_work/w1b_old"); N = os.path.expanduser("~/us_work/usw1b")
R = os.path.expanduser("~/tw-p17/backtest/resultsUSW1b")
po = json.load(open(f"{O}/results/pre_summary.json")); pn = json.load(open(f"{R}/pre_summary.json"))
bo = json.load(open(f"{O}/results/body_summary.json")); bn = json.load(open(f"{R}/body_summary.json"))
out = {}
keys = ["可用檔數", "無效K棒", "在指數且bars_ok的股月", "候選（在指數∧bars∧營收）股月", "訊號（再∧¬ma_stack∧ma60_up）股月", "訊號表（Z6 剔除後）", "第一個進場日", "Z5_容差版與精確版訊號差（股月）"]
out["pre計數 舊→新"] = {k: [po.get(k), pn.get(k)] for k in keys}
out["pre營收判定帳 舊→新"] = {k: [po["Z5_營收判定帳（在指數且bars_ok股月）"].get(k), pn["Z5_營收判定帳（在指數且bars_ok股月）"].get(k)] for k in set(po["Z5_營收判定帳（在指數且bars_ok股月）"]) | set(pn["Z5_營收判定帳（在指數且bars_ok股月）"])}
out["不適用 舊→新"] = {"舊": po["Z5_不適用19檔"], "新": pn["Z5_不適用19檔"],
                     "移出": sorted(set(po["Z5_不適用19檔"]) - set(pn["Z5_不適用19檔"])), "新增": sorted(set(pn["Z5_不適用19檔"]) - set(po["Z5_不適用19檔"]))}
out["Z7斷點 舊→新"] = [po["Z7_斷點"], pn["Z7_斷點"]]
out["每月訊號數 舊→新"] = [po["每月訊號數（窗內）"], pn["每月訊號數（窗內）"]]
arms = {}
for a in bn["臂"]:
    o, n = bo["臂"][a], bn["臂"][a]
    arms[a] = {"標籤": [o["標籤"], n["標籤"]], "翻轉": o["標籤"] != n["標籤"], "年化中位": [o["年化中位"], n["年化中位"]], "回落中位": [o["回落中位"], n["回落中位"]],
               "比值": [o["比值"], n["比值"]], "逐種子合格比例": [o["逐種子標籤比例"]["合格"], n["逐種子標籤比例"]["合格"]],
               "逐種子另列比例": [o["逐種子標籤比例"]["另列"], n["逐種子標籤比例"]["另列"]],
               "ANN245標籤": [o["標籤_ANN245"], n["標籤_ANN245"]], "自第一個進場日標籤": [o["自第一個進場日_標籤（描述）"], n["自第一個進場日_標籤（描述）"]]}
    ka = [k for k in n if k.startswith("標籤_ANN實際")][0]; kb = [k for k in o if k.startswith("標籤_ANN實際")][0]
    arms[a]["ANN實際標籤"] = [o[kb], n[ka]]
out["各臂 舊→新"] = arms
out["基準 舊→新"] = {k: [bo["基準"][k]["年化"], bn["基準"][k]["年化"], bo["基準"][k]["回落"], bn["基準"][k]["回落"]] for k in bn["基準"]}
out["訊號表筆數 舊→新"] = [bo["訊號表筆數"], bn["訊號表筆數"]]
# 面板逐檔
Po = pd.read_csv(f"{O}/work/panel_monthly.csv.gz"); Pn = pd.read_csv(f"{N}/panel_monthly.csv.gz")
w = ["t", "date"]
M = Po[w + ["base", "cand", "sig"]].merge(Pn[w + ["base", "cand", "sig"]], on=w, how="outer", suffixes=("_o", "_n"), indicator=True)
out["面板列 只在舊／只在新／兩邊"] = M["_merge"].value_counts().to_dict()
for c in ("base", "cand", "sig"):
    M[c + "_o"] = M[c + "_o"].fillna(False).astype(bool); M[c + "_n"] = M[c + "_n"].fillna(False).astype(bool)
win = (M["date"] >= "2015-11-01")
chg = {}
for c in ("base", "cand", "sig"):
    d = M[M[c + "_o"] != M[c + "_n"]]
    g = d.groupby("t").apply(lambda x: {"+": int((~x[c + "_o"] & x[c + "_n"]).sum()), "-": int((x[c + "_o"] & ~x[c + "_n"]).sum())}).to_dict()
    chg[c] = {"變動股月": int(len(d)), "增": int((~d[c + "_o"] & d[c + "_n"]).sum()), "減": int((d[c + "_o"] & ~d[c + "_n"]).sum()), "檔數": int(d["t"].nunique()), "逐檔": g}
out["股月變動（全量測日）"] = chg
# 只在新面板的量測日（日曆延長）
out["新有價格的檔"] = sorted(M.loc[M["_merge"] == "right_only", "t"].unique().tolist())
# 季營收逐檔差
def q(root):
    d = pd.read_csv(f"{root}/data/fundamentals/quarterly_revenue.csv", usecols=["ticker", "cik", "period_end", "value", "first_filed"], dtype={"cik": str})
    return d
qo, qn = q(os.path.expanduser("~/usdata/0043f97")), q(os.path.expanduser("~/usdata/60d2f99"))
co = qo.groupby("ticker").size(); cn = qn.groupby("ticker").size()
J = qo.merge(qn, on=["ticker", "period_end"], how="outer", suffixes=("_o", "_n"), indicator=True)
J["值或日變"] = (J["_merge"] == "both") & ((J["value_o"] != J["value_n"]) | (J["first_filed_o"] != J["first_filed_n"]))
J["cik變"] = (J["_merge"] == "both") & (J["cik_o"] != J["cik_n"])
aff = []
for t, g in J.groupby("ticker"):
    a = {"季_舊": int(co.get(t, 0)), "季_新": int(cn.get(t, 0)), "只在新": int((g["_merge"] == "right_only").sum()), "只在舊": int((g["_merge"] == "left_only").sum()),
         "同季值或公布日變": int(g["值或日變"].sum()), "cik變": bool(g["cik變"].any())}
    if a["只在新"] or a["只在舊"] or a["同季值或公布日變"] or a["cik變"]:
        aff.append({"ticker": t, **a})
aff = pd.DataFrame(aff)
uni = set(pd.read_csv(os.path.expanduser("~/usdata/60d2f99/data/membership/universe.csv"), dtype=str)["ticker"])
aff["在S&P500母體"] = aff["ticker"].isin(uni)
cand_t = set(chg["cand"]["逐檔"]); sig_t = set(chg["sig"]["逐檔"])
aff["候選股月有變"] = aff["ticker"].isin(cand_t); aff["訊號股月有變"] = aff["ticker"].isin(sig_t)
out["季營收受影響檔（S&P500母體）"] = aff[aff["在S&P500母體"]].to_dict("records")
out["季營收受影響檔（母體外，S&P400 等）數"] = int((~aff["在S&P500母體"]).sum())
out["候選有變但季營收沒變的檔"] = sorted(cand_t - set(aff["ticker"]))
json.dump(out, open(f"{R}/rerun_diff.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("寫出 rerun_diff.json：受影響季營收檔 {}、新有價格 {}".format(int(aff["在S&P500母體"].sum()), len(out["新有價格的檔"])))
