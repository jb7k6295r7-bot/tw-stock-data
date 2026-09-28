# -*- coding: utf-8 -*-
"""researchLowTO 的獨立查核（⛔ 不 import researchLowTO、⛔ 不 import researchMomX）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchLowTO_check.py

① 周轉率：抽 30 個（換股日, 股）（主、早年各 15），自己讀原始 stocks 檔（主 main 快照；早年 950ad26e12）算 TO20／60／120 ⇒ 對 to_*.csv.gz（相對差 ≤ 1e−12）
② 選股：挑中格（兩族）每個換股日，自己從 to_*.csv.gz 排（TO 由低到高、同值依代號；乙族限營收池）取前 N ⇒ 對 sel_*.csv.gz
③ 格：自己套 0050 同段標籤、退化（平均持股 ＜ N÷2 或現金 ＞ 30%）、挑格（先合格再比值；平手 年化、月＜季＜半年、N、L）、族標籤 ⇒ 對 cells.csv／summary.json
④ 自寫換股簿（規則同 researchScore_check／researchMomX R7：強制出場、落選開盤賣、跌停延後、下市了結、漲停／停牌不買不遞補、min(前日權益÷N, 現金)、0.585%）
   用 sel_甲（主窗）重算權益 ⇒ 探索、確認年化對 cells.csv（差 ≤ 1e−12）
⑤ 同池隨機 p：從 fake_*.csv.gz 自己算 ⇒ 對 summary.json
⚠ 範圍：①② 抽查／挑中格；④ 只重算甲族主窗
⇒ backtest/resultsLowTO/check.json
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
from backtest import research13 as R13

OUT = "backtest/resultsLowTO"
RP = dict(float_precision="round_trip")
MAIN = RR.H2D; EARLYD = os.path.expanduser("~/earlydata/950ad26e12/main/data"); EPX = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
COST = 0.00585
errs = []; info = {}
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
PT = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
rng = np.random.default_rng(20260928)
TOT = {"M": pd.read_csv(os.path.join(OUT, "to_main.csv.gz"), dtype={"sid": str}, **RP), "E": pd.read_csv(os.path.join(OUT, "to_early.csv.gz"), dtype={"sid": str}, **RP)}
CAL = {"M": list(pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"]), "E": list(pd.read_csv(os.path.join(EPX, "meta", "calendar_twse.csv"))["date"])}

# ①
nb = 0
for wn, src in (("M", MAIN), ("E", EARLYD)):
    T = TOT[wn]; T = T[np.isfinite(T["TO120"])]
    for _, r in T.iloc[rng.choice(len(T), size=15, replace=False)].iterrows():
        x = pd.read_csv(os.path.join(src, "stocks", r["sid"] + ".csv"), dtype={"date": str}).drop_duplicates("date").set_index("date")
        e = CAL[wn].index(r["日期"])
        v = pd.to_numeric(x["volume"], errors="coerce").reindex(CAL[wn]).fillna(0.0).to_numpy(float)
        sh = pd.to_numeric(x["shares"], errors="coerce"); sh = sh.where(sh > 0).reindex(CAL[wn]).ffill().to_numpy(float)
        for L in (20, 60, 120):
            w = sh[e - L:e]
            mine = float(np.mean(v[e - L:e] / w)) if np.all(np.isfinite(w)) else np.nan
            ref = r[f"TO{L}"]
            if not ((np.isnan(mine) and np.isnan(ref)) or abs(mine - ref) <= 1e-12 * max(abs(ref), 1e-12)):
                nb += 1; errs.append(f"① {wn} {r['sid']} {r['日期']} TO{L} {mine} {ref}")
info["① 抽 30 筆 × 3 L 不同"] = nb

# ②
nb = 0; ncmp = 0
for fam, pk in S["挑中格"].items():
    if not pk:
        continue
    r = PT.set_index("格").loc[pk]; L = int(r["L"]); fq = r["頻率"]; N = int(r["N"])
    SEL = pd.read_csv(os.path.join(OUT, f"sel_{fam}.csv.gz"), dtype={"sid": str})
    months = {"月": None, "季": (1, 4, 7, 10), "半年": (1, 7)}[fq]
    for wn in ("M", "E"):
        T = TOT[wn]
        for d, g in T.groupby("日期"):
            if months is not None and int(d[5:7]) not in months:
                continue
            g = g[np.isfinite(g[f"TO{L}"])]
            if fam == "乙":
                g = g[g["營收池"].astype(str) == "True"]
            mine = list(g.sort_values([f"TO{L}", "sid"])["sid"].iloc[:N])
            ref = list(SEL[(SEL["世界"] == wn) & (SEL["換股日"] == d)].sort_values("名次")["sid"])
            ncmp += 1
            if mine != ref:
                nb += 1; errs.append(f"② {fam} {wn} {d}")
info["② 挑中格換股日／名單不同"] = [ncmp, nb]

# ③
B = S["0050"]; LORD = {"合格": 0, "另列": 1, "不合格": 2}
lab = lambda c, m, b: "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")
nb = 0
for _, r in PT.iterrows():
    for sg in ("探索", "確認", "早年"):
        if lab(r[f"{sg}_年化"], r[f"{sg}_回落"], B[sg]) != r[f"{sg}_標籤"]:
            nb += 1; errs.append(f"③ {r['格']} {sg}")
    if bool((r["探索_持股"] < r["N"] / 2) or (r["探索_現金"] > 0.30)) != (str(r["退化"]) == "True"):
        nb += 1; errs.append(f"③ {r['格']} 退化")
for fam in ("甲", "乙"):
    c = PT[(PT["族"] == fam) & (PT["挑法"] == "low") & (PT["退化"].astype(str) != "True")].copy()
    q = c[c["探索_標籤"] == "合格"] if (c["探索_標籤"] == "合格").any() else c
    q = q.assign(_r=q["探索_年化"] / q["探索_回落"].abs(), _f=q["頻率"].map({"月": 0, "季": 1, "半年": 2}))
    mine = q.sort_values(["_r", "探索_年化", "_f", "N", "L"], ascending=[False, False, True, True, True]).iloc[0]["格"] if len(q) else None
    if mine != S["挑中格"][fam]:
        nb += 1; errs.append(f"③ 挑格 {fam}")
    if mine:
        rr = PT.set_index("格").loc[mine]
        if max((rr["確認_標籤"], rr["早年_標籤"]), key=lambda x: LORD[x]) != S["判定"][fam]["族標籤"]:
            nb += 1; errs.append(f"③ 族標籤 {fam}")
info["③ 不同"] = nb

# ④ 甲族主窗自寫換股簿
pk = S["挑中格"]["甲"]
if pk:
    r = PT.set_index("格").loc[pk]; N = int(r["N"])
    SEL = pd.read_csv(os.path.join(OUT, "sel_甲.csv.gz"), dtype={"sid": str}); SEL = SEL[SEL["世界"] == "M"]
    cal = D.load_calendar(); n = len(cal); pos = {str(d.date()): i for i, d in enumerate(cal)}
    sel = {pos[d]: list(g.sort_values("名次")["sid"]) for d, g in SEL.groupby("換股日")}
    # 空名單的換股日也要算（落選全賣）：所有換股日 ＝ to_main 的日期中符合頻率者
    months = {"月": None, "季": (1, 4, 7, 10), "半年": (1, 7)}[r["頻率"]]
    for d in sorted(set(TOT["M"]["日期"])):
        if (months is None or int(d[5:7]) in months) and pos[d] not in sel:
            sel[pos[d]] = []
    mk = D.load_universe().set_index("stock_id")["market"]
    sids = sorted(set(s for v in sel.values() for s in v))
    P = {}
    for s in sids:
        st = D.load_stock(s, mk.get(s, "twse"), cal); raw = st.df["close"].to_numpy(float); tb = TR.one(s, cal)
        P[s] = {"c": pd.Series(raw).ffill().to_numpy(float), "o": st.df["open"].to_numpy(float), "valid": np.isfinite(raw), "trd": tb["trd"], "up": tb["up_o"], "dn": tb["dn_o"]}
    dl = TR.delist_status({s: {"trd": P[s]["trd"]} for s in sids}, cal, official=TR.load_official())
    t0 = min(sel); t1 = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    SF = {s: int(np.flatnonzero(P[s]["valid"])[-1]) for s in sids if np.flatnonzero(P[s]["valid"])[-1] < t1}
    eq = np.ones(n); cash = 1.0; hold = {}; pend = set()
    for t in range(t0, t1 + 1):
        if t in sel:
            pend = (pend | (set(hold) - set(sel[t]))) - set(sel[t])
        for s in sorted(pend | {s for s in hold if s in SF and t > SF[s]}):
            if s not in hold:
                pend.discard(s); continue
            x = P[s]; o = x["o"][t]
            if s in SF and t > SF[s]:
                px = x["c"][t]
            elif x["trd"][t] and not x["dn"][t] and np.isfinite(o) and o > 0:
                px = o
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]
            else:
                continue
            u, amt = hold.pop(s); cash += u * px - amt * COST; pend.discard(s)
        if t in sel:
            for s in [s for s in sel[t] if s not in hold][:max(N - len(hold), 0)]:
                x = P[s]; o = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or (s in SF and t > SF[s]) or x["up"][t]:
                    continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; hold[s] = (amt / o, amt)
        eq[t] = cash + sum(u * P[s]["c"][t] for s, (u, _) in hold.items())
    eq[:t0] = 1.0
    for sg, (x_, y_) in {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}.items():
        a_, b_ = int(cal.searchsorted(pd.Timestamp(x_))), int(cal.searchsorted(pd.Timestamp(y_)))   # 窗首起算（半年／季格在第一個換股日前持現金，同換股簿）
        c_, m_ = R13.window_stats(eq, 0, len(eq), a_, b_ + 1)
        info[f"④ 甲 {pk} {sg} 年化（自算／檔）"] = [float(c_), float(r[f"{sg}_年化"])]
        if abs(float(c_) - float(r[f"{sg}_年化"])) > 1e-12:
            errs.append(f"④ {sg}")

# ⑤
nb = 0
for fam, pk in S["挑中格"].items():
    if not pk:
        continue
    r = PT.set_index("格").loc[pk]
    F = pd.read_csv(os.path.join(OUT, f"fake_{fam}.csv.gz"), **RP)
    for sg, wn in (("探索", "M"), ("確認", "M"), ("早年", "E")):
        g = F[F["世界"] == wn]
        p = float(np.mean(g[f"{sg}_年化"] >= r[f"{sg}_年化"]))
        if abs(p - S["假訊號（同池隨機）"][fam][sg]["p（隨機年化 ≥ 本格）"]) > 1e-12:
            nb += 1; errs.append(f"⑤ {fam} {sg}")
info["⑤ 不同"] = nb
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:40]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:15]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
