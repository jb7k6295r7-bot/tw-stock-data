# -*- coding: utf-8 -*-
"""營量 v1 即將達成名單：簡短查核（⛔ 不 import list_yl13_watch）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/list_yl13_watch_check.py

抽 5 檔（A／B／C 各至少 1 檔，其餘隨機），自己讀 D.load_stock（最新 main、traded 有效 K 棒、還原價）用 pandas 算
c1 近 20 日漲幅、c3 成交額倍數、c4 收盤÷MA100、c5 收盤÷250 日高；c2 漲停數用原始收盤與 research11.limit_price 自己判（還原事件日、上市前 5 根不判）
B 區另核：明天門檻 c1（1.30 × 第 k−19 根收盤）、c4（近 99 根和 ÷ 99）、c5（近 249 根最高）換回未還原價 ⇒ 對 watch_*.csv（相對差 ≤ 1e−9）
⇒ backtest/resultsYLwatch/check.json
"""
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R

OUT = "backtest/resultsYLwatch"
sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
D.DATA = os.path.expanduser(f"~/h2data/{sha}/data")
cal = D.load_calendar()
W = {z: pd.read_csv(os.path.join(OUT, f"watch_{z}.csv"), dtype={"代號": str}) for z in "ABC"}
rng = np.random.default_rng(20260928)
pick = []
for z in "ABC":
    if len(W[z]):
        pick.append((z, W[z].iloc[int(rng.integers(0, len(W[z])))]))
pool = [(z, r) for z in "ABC" for _, r in W[z].iterrows()]
while len(pick) < 5 and len(pool) > len(pick):
    z, r = pool[int(rng.integers(0, len(pool)))]
    if all(r["代號"] != p[1]["代號"] for p in pick):
        pick.append((z, r))
errs = []; info = {}
adjd = None
for z, r in pick:
    s = r["代號"]
    st = D.load_stock(s, r["市場"], cal); df = st.df
    idx = np.flatnonzero(df["traded"].to_numpy())
    c = df["close"].to_numpy(float)[idx]; amt = df["amount"].to_numpy(float)[idx]
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", s + ".csv"), dtype={"date": str}).drop_duplicates("date").set_index("date")["close"]
    rc = pd.to_numeric(raw.reindex([str(d.date()) for d in cal[idx]]), errors="coerce").to_numpy(float)
    k = len(idx) - 1
    ret20 = c[k] / c[k - 20] - 1
    ap = amt[k - 20:k].mean(); ratio = amt[k] / ap
    ma100 = c[k - 99:k + 1].mean(); hi250 = c[k - 249:k + 1].max()
    a = D.load_adj(s); ev = set()
    if a is not None:
        for d_ in a["date"]:
            j = int(np.searchsorted(cal[idx], d_))
            if j < len(idx):
                ev.add(j)
    first5 = cal[idx][0] > pd.Timestamp("2015-01-12")
    nup = 0
    for j in range(k - 19, k + 1):
        if j in ev or (first5 and j < 5) or not (np.isfinite(rc[j]) and np.isfinite(rc[j - 1]) and rc[j - 1] > 0):
            continue
        nup += abs(rc[j] - R.limit_price(rc[j - 1], True, 0.10)) < 1e-6
    mine = {"c1 近20日漲幅": ret20, "c2 近20根漲停數": float(nup), "c3 成交額倍數": ratio, "c4 收盤÷MA100": c[k] / ma100, "c5 收盤÷250日高": c[k] / hi250}
    if z == "B":
        fr = c[k] / rc[k]
        mine.update({"明天門檻 c1（收盤≥）": 1.30 * c[k - 19] / fr, "明天門檻 c4（收盤＞）": c[k - 98:k + 1].sum() / 99 / fr, "明天門檻 c5（收盤≥）": c[k - 248:k + 1].max() / fr})
    d = {}
    for kk, v in mine.items():
        ref = float(r[kk]); d[kk] = [float(v), ref]
        if not (abs(v - ref) <= 1e-9 * max(1.0, abs(ref))):
            errs.append(f"{z} {s} {kk} 自算 {v} 檔 {ref}")
    info[f"{z} {s} {r['名稱']}"] = d
# 人工驗算 c3 門檻 3 檔（B 區只差量優先）：列出前 20 個交易日（有成交）的日期與成交額
ALL = pd.concat([W[z].assign(區=z) for z in "ABC"], ignore_index=True)
cand = ALL[(ALL["區"] == "B") & (ALL.get("只差量", False) == True)] if "只差量" in ALL else ALL.iloc[0:0]
man = [r for _, r in (cand.head(3) if len(cand) >= 3 else ALL.sample(3, random_state=20260928)).iterrows()]
MAN = {}
for r in man:
    s = str(r["代號"])
    x = pd.read_csv(os.path.join(D.DATA, "stocks", s + ".csv"), dtype={"date": str}).drop_duplicates("date")
    st = D.load_stock(s, r["市場"], cal); tr = st.df["traded"].to_numpy()
    days = [str(d.date()) for d in cal[np.flatnonzero(tr)]][-20:]
    x = x.set_index("date").loc[days]
    amts = pd.to_numeric(x["amount"], errors="coerce").to_numpy(float)
    thr = 3.0 * amts.mean(); px = float(pd.to_numeric(x["close"]).iloc[-1])
    lots = int(round(thr / (px * 1000)))
    MAN[f"{s}"] = {"前 20 個交易日": list(zip(days, [int(a_) for a_ in amts])), "平均": float(amts.mean()), "×3 門檻（元）": thr, "億": round(thr / 1e8, 1),
                   "收盤": px, "張": lots, "檔：億": float(r["c3 門檻成交額（億）"]), "檔：張": int(r["c3 門檻張數（按最新收盤）"]), "檔：元": float(r["c3 門檻成交額（元）"])}
    if abs(thr - float(r["c3 門檻成交額（元）"])) > 1e-9 * thr or lots != int(r["c3 門檻張數（按最新收盤）"]) or round(thr / 1e8, 1) != float(r["c3 門檻成交額（億）"]):
        errs.append(f"人工驗算 {s}")
info["人工驗算 c3 門檻（3 檔）"] = MAN
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in info.items()}, ensure_ascii=False, default=float)[:3000]); [print("  ⛔", e) for e in errs]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
