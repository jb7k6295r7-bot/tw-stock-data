# -*- coding: utf-8 -*-
"""researchScore 的獨立查核（⛔ 不 import researchScore）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchScore_check.py [--dates 6]

① 票：挑中格的 L，抽 --dates 個換股日，母體自己圈（panel_ext 當月量測日 eligible ∩ gate3），每檔 11 票自己算：
   ①② 自己 merge_asof panel_rev；③④⑨ 自己用 load_stock 收盤／成交量在 pandas 上算；⑤ 自己照 research11 主格條件寫；
   ⑥⑦⑩⑪ 直接讀 resultsSig 快取；⑧ 走 patterns_all.detect_calendar（完整偵測器路徑，與主程式直接呼叫 detect_lines 不同路）⇒ 對 votes_L*.csv.gz
② 挑股：從 votes 檔自己算分數、自己抽籤（default_rng([20260928, e])，依代號排序）⇒ 對 picks.csv.gz（全部換股日）
③ 換股簿：自己寫一個模擬器（同規則：強制出場、落選開盤賣、跌停／停牌延後、下市了結、漲停／停牌不買不遞補、金額 min(前日淨值÷N, 現金)、成本 0.585%）
   ⇒ 權益對 eq.npz（相對差 ≤ 1e−12）；探索／確認段年化、回落對 cells.csv
④ 挑格與判定：從 cells.csv 自己排除退化、自己挑、自己判；丙的 p 從 random.csv.gz 自己算；0050 同段自己算；判定句自己推
⇒ check.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import patterns_all as PA
from backtest import research11 as R
from backtest import tradability as TR
from backtest import universe_gate as UG
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchPatAll_freq as PF                  # 完整偵測器路徑用的原始價讀檔（freq 同一支）
RR.use_snapshot()

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsScore")
COST = 0.00585
RP = dict(float_precision="round_trip")
BEAR = ("v10", "v11")
VOTES = [f"v{i}" for i in range(1, 12)]


def wstats(eq, a, b):
    seg = eq[a:b + 1]; yrs = len(seg) / 245
    c = (seg[-1] / seg[0]) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(seg)
    return float(c), float(((seg - pk) / pk).min())


def lab(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dates", type=int, default=6); a = ap.parse_args()
    errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ck = S["探索挑格"]["挑中"]; Ls, rb, Ns = ck.split("_"); L = int(Ls[1:]); N = int(Ns[1:])
    cal = D.load_calendar(); n = len(cal)
    V = pd.read_csv(os.path.join(OUT, f"votes_L{L}.csv.gz"), dtype={"sid": str}, **RP)
    PK = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str}, **RP)
    # ── ① 票
    reb_all = sorted(V["e"].unique())
    pick_e = [reb_all[int(i)] for i in np.linspace(0, len(reb_all) - 1, a.dates)]
    U = UG.gate3(pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)); mk = U.set_index("stock_id")["market"]
    pan = pd.read_csv(os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz"), dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "eligible"],
                      parse_dates=["measure_date"])
    pan = pan[pan["eligible"].astype(str) == "True"]
    PRV = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24", "yoy"])
    SIG, _ = pickle.load(open(os.path.join(HERE, "resultsSig", "sig_cache.pkl"), "rb"))
    cache = {}

    def stock(s):
        if s not in cache:
            st = D.load_stock(s, mk.get(s, "twse"), cal)
            df = st.df
            c = df["close"].to_numpy(float); v = df["volume"].to_numpy(float)
            bars = np.flatnonzero(np.isfinite(c))
            ro, rh, rl, rc = PF.load_raw(s, cal)
            ev = PA.detect_calendar(df["open"].to_numpy(float), df["high"].to_numpy(float), df["low"].to_numpy(float), c, v, ro, rh, rl, rc)["S06"]["T"]
            B = R.load_bars(s, mk.get(s, "twse"), cal)
            cache[s] = (c, v, bars, np.asarray(ev, int), B)
        return cache[s]
    nbad = {v: 0 for v in VOTES}; nuni = 0; ncell = 0
    for e in pick_e:
        d = cal[e]
        md = pan.loc[(pan["measure_date"].dt.year == d.year) & (pan["measure_date"].dt.month == d.month), "measure_date"].max()
        uni = sorted(set(pan.loc[pan["measure_date"] == md, "stock_id"]) & set(U["stock_id"]))
        got = V[V["e"] == e].set_index("sid")
        if set(uni) != set(got.index):
            errs.append(f"① {d.date()} 母體：自圈 {len(uni)} vs 檔 {len(got)}（差 {sorted(set(uni) ^ set(got.index))[:5]}）")
        nuni += len(uni)
        vr = {}; mine = {}
        for s in got.index:
            c, v, bars, ev8, B = stock(s)
            b = bars[bars <= e - 1]
            x = {}
            g = PRV[(PRV["stock_id"] == s) & (PRV["signal_pos"] <= e - 1)]
            if len(g) and (e - 1) - int(g["signal_pos"].max()) <= 45:
                r_ = g.loc[g["signal_pos"].idxmax()]
                x["v1"] = str(r_["rev_hi24"]) == "True"; x["v2"] = bool(np.isfinite(r_["yoy"]) and r_["yoy"] >= 0.15)
            else:
                x["v1"] = x["v2"] = False
            # ③ 近 L 日內有「收盤 ≥ 含當根 250 根有效收盤最高」
            hit3 = False
            for dd in range(e - L, e):
                if dd >= 0 and np.isfinite(c[dd]):
                    k = int(np.searchsorted(bars, dd))
                    if k >= 249 and c[dd] >= c[bars[k - 249:k + 1]].max():
                        hit3 = True; break
            x["v3"] = hit3
            if len(b) >= 60:
                cb = c[b]
                m5, m10, m20, m60 = (math.fsum(cb[-w:]) / w for w in (5, 10, 20, 60))
                x["v4"] = bool(m5 > m10 > m20 > m60)
            else:
                x["v4"] = False
            vr[s] = v[b[-20:]].mean() / v[b[-250:]].mean() if len(b) >= 250 else np.nan
            # ⑤
            x5 = False
            if B is not None:
                idx = B["idx"]; k = int(np.searchsorted(idx, e - 1, side="right")) - 1
                if k >= 249:
                    cc = B["c"]; up = B["up"]; amt = B["amt"]
                    r20 = cc[k] / cc[k - 20] - 1
                    nup = int(up[k - 19:k + 1].sum())
                    ap20 = amt[k - 20:k].mean() if k >= 21 else np.nan
                    ma100 = cc[k - 99:k + 1].mean(); hi = cc[k - 249:k + 1].max()
                    sc = int(r20 >= 0.30) + int(nup >= 3) + int(amt[k] / ap20 >= 3.0) + int(cc[k] > ma100) + int(cc[k] >= hi)
                    okb = (not B["skip"][k]) and np.isfinite(ma100) and np.isfinite(amt[k] / ap20) and B["next_bad"][max(0, k - 20)] > k
                    x5 = bool(okb and sc >= 3)
            x["v5"] = x5
            sg = SIG.get(s, {})
            for vv, code in (("v6", "E:TD"), ("v7", "E:RSI"), ("v10", "X:TL"), ("v11", "X:VSc")):
                arr = np.asarray(sg.get(code, []), int); x[vv] = bool(((arr >= e - L) & (arr <= e - 1)).any())
            x["v8"] = bool(((ev8 >= e - L) & (ev8 <= e - 1)).any())
            mine[s] = x
        vs = pd.Series(vr)
        top = vs.rank(pct=True) > 0.8
        for s in got.index:
            mine[s]["v9"] = bool(top.get(s, False))
            for vv in VOTES:
                ncell += 1
                if bool(mine[s][vv]) != bool(got.at[s, vv]):
                    nbad[vv] += 1
    info["① 抽查換股日"] = [str(cal[e].date()) for e in pick_e]; info["① 抽查股-日"] = nuni; info["① 各票不同"] = nbad
    if any(nbad.values()):
        errs.append(f"① 票不同 {nbad}")
    # ── ② 挑股
    bad = 0; tot = 0
    for e, g in V.groupby("e"):
        if e not in set(PK["e"]):
            continue
        sc = np.zeros(len(g), int)
        for vv in VOTES:
            sc += np.where(g[vv].astype(bool), -1 if vv in BEAR else 1, 0)
        sids = sorted(g["sid"]); u = dict(zip(sids, np.random.default_rng([20260928, int(e)]).random(len(sids))))
        m = dict(zip(g["sid"], sc))
        top = sorted(sids, key=lambda s: (-m[s], u[s]))[:N]
        ref = PK[PK["e"] == e].sort_values("rank")["sid"].tolist()
        tot += 1; bad += top != ref
    info["② 名單不同的換股日"] = [bad, tot]
    if bad:
        errs.append(f"② 名單 {bad}／{tot}")
    # ── ③ 換股簿
    Z = np.load(os.path.join(OUT, "eq.npz"))
    t0, t1 = int(Z["t0"]), int(Z["t1"])
    sel = {int(e): g.sort_values("rank")["sid"].tolist() for e, g in PK.groupby("e")}
    sids = sorted(set(PK["sid"]))
    P = {}
    for s in sids:
        st = D.load_stock(s, mk.get(s, "twse"), cal); raw_c = st.df["close"].to_numpy(float)
        tb = TR.one(s, cal)
        P[s] = {"c": pd.Series(raw_c).ffill().to_numpy(float), "o": st.df["open"].to_numpy(float), "trd": tb["trd"], "up": tb["up_o"], "dn": tb["dn_o"],
                "last": int(np.flatnonzero(np.isfinite(raw_c))[-1])}
    dl = TR.delist_status({s: {"trd": P[s]["trd"]} for s in sids}, cal, official=TR.load_official())
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
            free = N - len(pos)
            for s in [s for s in sel[t] if s not in pos][:max(free, 0)]:
                x = P[s]; o = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or x["up"][t]:
                    continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[s] = (amt / o, amt)
        eq[t] = cash + sum(u_ * P[s]["c"][t] for s, (u_, _) in pos.items())
    rel = float(np.max(np.abs(eq[t0:t1 + 1] / Z["main"][t0:t1 + 1] - 1)))
    info["③ 自寫模擬器 vs eq.npz 最大相對差"] = rel
    if rel > 1e-12:
        errs.append(f"③ 權益相對差 {rel}")
    T = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
    segp = {nm: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for nm, (x, y) in
            {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}.items()}
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    B50 = {nm: wstats(bench, x, y) for nm, (x, y) in segp.items()}
    for nm, (x, y) in segp.items():
        c, m = wstats(eq, x, y); r_ = T[(T["格"] == ck) & (T["段"] == nm)].iloc[0]
        if abs(c - r_["年化"]) > 1e-9 or abs(m - r_["回落"]) > 1e-9:
            errs.append(f"③ {nm} 年化／回落 自算 {c}／{m} vs {r_['年化']}／{r_['回落']}")
        if abs(B50[nm][0] - S["0050"][nm]["年化"]) > 1e-12:
            errs.append(f"③ 0050 {nm}")
    # ── ④ 挑格、判定、p
    ex = T[T["段"] == "探索"].copy()
    ex["退化_"] = (ex["平均持股"] < ex["N"] / 2) | (ex["現金比例"] > 0.30)
    ex["過_"] = (ex["年化"] > B50["探索"][0]) & (ex["年化"] / ex["回落"].abs() >= B50["探索"][0] / abs(B50["探索"][1]))
    cand = ex[~ex["退化_"]]
    pool = cand[cand["過_"]] if cand["過_"].any() else cand
    pool = pool.assign(_r=pool["換股"].map({"月換": 0, "季換": 1}), _q=pool["年化"] / pool["回落"].abs())
    best = pool.sort_values(["_q", "年化", "L", "_r", "N"], ascending=[False, False, True, True, True]).iloc[0]["格"]
    if best != ck:
        errs.append(f"④ 挑格 自算 {best} vs {ck}")
    cf = T[(T["格"] == ck) & (T["段"] == "確認")].iloc[0]
    lc = lab(cf["年化"], cf["回落"], *B50["確認"])
    if lc != S["確認"]["判定"]:
        errs.append("④ 確認判定")
    ea = S["早年"]["A"]
    la = lab(ea["年化"], ea["回落"], ea["0050"]["年化"], ea["0050"]["回落"])
    sent = "只在看過的那段合格" if (lc == "合格" and la != "合格") else lc
    if la != ea["標籤"] or sent != S["判定句"]:
        errs.append("④ 早年／判定句")
    RD = pd.read_csv(os.path.join(OUT, "random.csv.gz"), **RP)
    for nm in ("探索", "確認"):
        x = RD[f"{nm}_年化"].to_numpy(float)
        p_main = float(np.mean(x >= float(T[(T["格"] == ck) & (T["段"] == nm)]["年化"].iloc[0])))
        p_b = float(np.mean(x >= S["描述臂"]["乙"][nm]["年化"]))
        if abs(p_main - S["描述臂"]["丙"][nm]["p_主版"]) > 0 or abs(p_b - S["描述臂"]["丙"][nm]["p_乙"]) > 0:
            errs.append(f"④ p {nm}")
    info["④ 挑格／確認／早年A／判定句（自算）"] = [best, lc, la, sent]
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False, default=str))
    for e_ in errs[:20]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()
