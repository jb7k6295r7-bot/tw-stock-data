# -*- coding: utf-8 -*-
"""researchAudit5_1 的獨立查核（⛔ 不 import 主程式）：
① M1：自己用 csv 模組讀 layer1.csv、自己挑 7 個判定格（原件 summary.md §二 表的列），自己扣成本、自己判 ⇒ 對 rejudge.csv
② 門檻B：從原件 md 文字自己用正規式抓「全期／除四月／2021-01~2026-03／2017-2020」四列的 pp 與 CI ⇒ 對主程式抄錄值；自己扣 0.585% 判
⇒ check.json
"""
import csv
import json
import os
import re

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsAudit5", "1")
DOC = "/mnt/c/SynologyDrive/投資/台股策略用/專案搬出_20260925/門檻B全期回測與五問登錄地圖_策略線_20260920.md"
errs = []; info = {}
R = list(csv.DictReader(open(os.path.join(OUT, "rejudge.csv"), encoding="utf-8")))
lines = [ln for ln in open(os.path.join(HERE, "resultsm1", "layer1.csv"), encoding="utf-8") if not ln.startswith("#")]
M = list(csv.DictReader(lines))
sel = [m for m in M if m["H"] == "120" and ((m["signal"] == "a" and m["window"] == "主判定 2001 起") or (m["signal"] in ("c", "d") and m["window"] == "全期"))]
info["M1 判定格"] = len(sel)
if len(sel) != 7:
    errs.append("M1 判定格數")
rm = [r for r in R if r["件"] == "PREREGM1 層一"]
for m in sel:
    key = f"{m['label']}｜{m['state']}｜{m['window']}｜H120"
    r = [x for x in rm if x["格"] == key]
    if len(r) != 1:
        errs.append(f"M1 {key} 找不到"); continue
    r = r[0]
    for cn, c in (("0.385%", 0.00385), ("0.585%", 0.00585)):
        lo, hi = float(m["ci_lo"]) - c, float(m["ci_hi"]) - c
        j = "扣成本後判得出（CI 下緣 ＞ 0）" if lo > 0 else ("扣成本後判得出（為負）" if hi < 0 else "扣成本後判不出（CI 含 0）")
        if j != r[f"扣{cn}_判定"] or abs((float(m["diff"]) - c) * 100 - float(r[f"扣{cn}_差pp"])) > 1e-9:
            errs.append(f"M1 {key} {cn}")
txt = open(DOC, encoding="utf-8").read()
pat = {"全期": r"全期\s+98 月\s+\+([\d.]+)pp\s+CI \[\+([\d.]+),\s+\+([\d.]+)\]", "除四月": r"除四月\s+97 月\s+\+([\d.]+)pp\s+CI \[\+([\d.]+),\s+\+([\d.]+)\]",
       "2021-01~2026-03": r"2021-01~2026-03\s+57 月\s+\+([\d.]+)pp\s+CI \[\+([\d.]+),\s+\+([\d.]+)\]",
       "2017-2020（中心擬合段）": r"2017-2020（中心擬合段）\s*41 月\s+\+([\d.]+)pp\s+CI \[\+([\d.]+),\s+\+([\d.]+)\]"}
rg = {r["格"]: r for r in R if r["件"] != "PREREGM1 層一"}
for k, p in pat.items():
    m = re.search(p, txt)
    if not m:
        errs.append(f"門檻B 原件抓不到 {k}"); continue
    pp, lo, hi = map(float, m.groups())
    r = rg.get(k)
    if r is None or abs(float(r["原_差pp"]) - pp) > 1e-12:
        errs.append(f"門檻B {k} 抄錄")
        continue
    lo2 = lo - 0.585
    j = "扣成本後判得出（CI 下緣 ＞ 0）" if lo2 > 0 else ("扣成本後判得出（為負）" if hi - 0.585 < 0 else "扣成本後判不出（CI 含 0）")
    if j != r["扣0.585%_判定"] or f"{lo2:+.2f}～{hi - 0.585:+.2f}" != r["扣0.585%_CI"]:
        errs.append(f"門檻B {k} 判定")
    info[f"門檻B {k}"] = [pp, lo, hi, j]
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(info, ensure_ascii=False)); print("查核：" + ("全過" if not errs else f"⛔ {errs}"))
