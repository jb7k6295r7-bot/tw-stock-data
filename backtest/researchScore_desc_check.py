# -*- coding: utf-8 -*-
"""researchScore_desc 的獨立查核（⛔ 不 import researchScore_desc、⛔ 不 import researchScore）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchScore_desc_check.py

① 描述臂名單的分數：每個換股日，描述臂名單與原件名單（resultsScore/picks.csv.gz）的分數多重集合必須相同（只差同分怎麼排）；
   兩份名單不同的股票分數都等於該日名單的最低分（差異只能出在切點同分）
② 自寫模擬器（同 researchScore_check 的規則：強制出場、落選開盤賣、延後、下市了結、漲停／停牌不買不遞補、min(前日淨值÷N, 現金)、0.585%）
   用描述臂名單重算主窗權益 ⇒ 對 desc/eq.npz 的 on（相對差 ≤ 1e−12）
⇒ resultsScore/desc/check.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG

HERE = os.path.expanduser("~/tw-p17/backtest"); OUT = os.path.join(HERE, "resultsScore", "desc")
COST = 0.00585; BEAR = ("v10", "v11"); VOTES = [f"v{i}" for i in range(1, 12)]
errs = []; info = {}
PK = pd.read_csv(os.path.join(HERE, "resultsScore", "picks.csv.gz"), dtype={"sid": str})
PP = pd.read_csv(os.path.join(OUT, "picks_pref.csv.gz"), dtype={"sid": str})
V = pd.read_csv(os.path.join(HERE, "resultsScore", "votes_L20.csv.gz"), dtype={"sid": str})
sc = {}
for e, g in V.groupby("e"):
    s_ = np.zeros(len(g), int)
    for v in VOTES:
        s_ += np.where(g[v].astype(bool), -1 if v in BEAR else 1, 0)
    sc[int(e)] = dict(zip(g["sid"], s_))
nd = 0; ndiff = 0
for e, g in PP.groupby("e"):
    a = sorted(sc[int(e)][s] for s in g["sid"]); o = PK[PK["e"] == e]
    b = sorted(sc[int(e)][s] for s in o["sid"])
    if a != b:
        nd += 1
    diff = set(g["sid"]) ^ set(o["sid"])
    ndiff += len(set(g["sid"]) - set(o["sid"]))
    if diff and any(sc[int(e)][s] != min(a) for s in diff):
        nd += 1
info["① 分數多重集合不同／切點外差異的換股日"] = nd; info["① 描述臂換進的股（合計）"] = ndiff
if nd:
    errs.append("① 名單")
Z = np.load(os.path.join(OUT, "eq.npz")); t0, t1 = int(Z["t0"]), int(Z["t1"])
cal = D.load_calendar(); n = len(cal)
U = UG.gate3(pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)); mk = U.set_index("stock_id")["market"]
sel = {int(e): g.sort_values("rank")["sid"].tolist() for e, g in PP.groupby("e")}
sids = sorted(set(PP["sid"])); P = {}
for s in sids:
    st = D.load_stock(s, mk.get(s, "twse"), cal); raw = st.df["close"].to_numpy(float); tb = TR.one(s, cal)
    P[s] = {"c": pd.Series(raw).ffill().to_numpy(float), "o": st.df["open"].to_numpy(float), "trd": tb["trd"], "up": tb["up_o"], "dn": tb["dn_o"],
            "last": int(np.flatnonzero(np.isfinite(raw))[-1])}
dl = TR.delist_status({s: {"trd": P[s]["trd"]} for s in sids}, cal, official=TR.load_official())
N = 10
eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
for t in range(t0, t1 + 1):
    for s in list(pos):
        if P[s]["last"] < t1 and t == P[s]["last"] + 1:
            u_, amt = pos.pop(s); cash += u_ * P[s]["c"][t] - amt * COST; pend.discard(s)
    if t in sel:
        pend = (pend | (set(pos) - set(sel[t]))) - set(sel[t])
    for s in sorted(pend):
        x = P[s]; o = x["o"][t]
        if x["trd"][t] and not x["dn"][t] and np.isfinite(o) and o > 0:
            px = o
        elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
            px = x["c"][t]
        else:
            continue
        u_, amt = pos.pop(s); cash += u_ * px - amt * COST; pend.discard(s)
    if t in sel:
        for s in [s for s in sel[t] if s not in pos][:max(N - len(pos), 0)]:
            x = P[s]; o = x["o"][t]
            if not x["trd"][t] or not (np.isfinite(o) and o > 0) or x["up"][t]:
                continue
            amt = min(eq[t - 1] / N, cash)
            if amt <= 1e-12:
                break
            cash -= amt; pos[s] = (amt / o, amt)
    eq[t] = cash + sum(u_ * P[s]["c"][t] for s, (u_, _) in pos.items())
rel = float(np.max(np.abs(eq[t0:t1 + 1] / Z["on"][t0:t1 + 1] - 1)))
info["② 自寫模擬器 vs eq.npz(on) 最大相對差"] = rel
if rel > 1e-12:
    errs.append("② 權益")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False)); [print("  ⛔", e) for e in errs]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
