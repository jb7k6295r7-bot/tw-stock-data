# -*- coding: utf-8 -*-
"""researchExitGen 獨立查核（回測線計算子代理，2026-10-20）。⛔ 只讀 resultsExitGen 的輸出、不改任何檔；結果寫 resultsExitGen/check.json。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExitGen_check.py

 ① 抽 20 筆（主世界 H120 段內保留；七種出場各至少 2 筆有觸發、其餘隨機；種子 20261020）逐根手算：
    自己讀 D.load_stock（還原價）、tradability.one（成交與漲跌停）、revenue_hist 原始 csv；ATR（Wilder 14）、MA50（fsum）、0050 MA200、
    可賣開盤、月營收可用日全部用迴圈重寫（⛔ 不呼叫 researchQuad／researchExitGen 的觸發函式）⇒ 對 rows_main 的 d、s、base、D 逐筆比
 ② 不前視：同 20 筆，把【正式程式】（researchExitGen.trig_all＋Quad.stock_data）餵「判定日 d 之後全部截掉」的資料（個股 OHLC、0050、營收公布）
    ⇒ 觸發日 d 必須不變；三刀值餵「T 之後截掉」⇒ 不變
 ③ 彙總重算：從 rows_{main,early} 用自己寫的 CR0（逐群迴圈）與交互的群集三明治（矩陣式 OLS）重算 H120 全部格 ⇒ 對 cells.csv；判定重算 ⇒ 對 verdict.json
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExitGen as G                                   # 只用於 ② 正式程式的截斷測試、常數
from backtest import tradability as TR
from backtest import research11 as R11

D = G.D
OUT = G.OUT
COST = 0.00585
H = 120


# ═════════ ① 逐根手算（自己的迴圈）
def wilder(h, l, c, n=14):
    m = len(c); atr = [math.nan] * m
    tr = []
    for i in range(m):
        if i == 0:
            tr.append(h[0] - l[0])
        else:
            tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    if m >= n:
        atr[n - 1] = sum(tr[:n]) / n
        for i in range(n, m):
            atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    for i in range(min(R11.ATR_MIN_BARS - 1, m)):
        atr[i] = math.nan
    return atr


def hand(sid, market, e, cal, c50, revdf):
    st = D.load_stock(sid, market, cal); df = st.df
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float); hi = df["high"].to_numpy(float); lo = df["low"].to_numpy(float)
    tb = TR.one(sid, cal)
    n = len(cal); x = e + H - 1
    valid = [bool(np.isfinite(v)) for v in c]
    bars = [i for i in range(n) if valid[i]]
    P0 = float(o[e])
    j = max(i for i in bars if i <= x)
    base = c[j] / P0 - 1 - COST
    # 有效 K 棒上的 ATR、MA50
    atr_b = wilder([hi[i] for i in bars], [lo[i] for i in bars], [c[i] for i in bars])
    atr = {b: atr_b[k] for k, b in enumerate(bars)}
    ma = {}
    for k, b in enumerate(bars):
        ma[b] = math.fsum(c[bars[q]] for q in range(k - 49, k + 1)) / 50 if k >= 49 else math.nan
    prev = {bars[k]: bars[k - 1] for k in range(1, len(bars))}

    def sell_after(d):
        for t in range(d + 1, n):
            if tb["trd"][t] and not tb["dn_o"][t] and np.isfinite(o[t]) and o[t] > 0:
                return t if t < x else -1
        return -1
    res = {}
    # X1／X3
    for code, f in (("X1", lambda v: v <= P0 * 90 / 100), ("X3", lambda v: v >= P0 * 150 / 100)):
        res[code] = next((d for d in range(e, x) if valid[d] and f(c[d])), -1)
    # X2
    kprev = prev.get(e, -1) if valid[e] else max([b for b in bars if b < e], default=-1)
    d2 = -1
    if kprev >= 0 and np.isfinite(atr[kprev]):
        L = P0 - 3 * atr[kprev]; runhi = -math.inf
        for d in range(e, x):
            if not valid[d]:
                continue
            if c[d] > runhi:
                runhi = c[d]
                if np.isfinite(atr[d]):
                    L = max(L, c[d] - 3 * atr[d])
            if c[d] < L:
                d2 = d; break
    res["X2"] = d2
    # X4（0050 ffill、MA200 迴圈）
    cf = []; last = math.nan
    for v in c50:
        last = v if np.isfinite(v) else last; cf.append(last)
    def ma200(i):
        if i < 199:
            return math.nan
        return sum(cf[i - 199:i + 1]) / 200
    res["X4"] = next((d for d in range(e, x) if np.isfinite(ma200(d - 1)) and cf[d] < ma200(d) and cf[d - 1] >= ma200(d - 1)), -1)
    # X5
    kb = [b for b in bars if b >= e]
    res["X5"] = kb[19] if len(kb) > 19 and kb[19] < x and c[kb[19]] <= P0 else -1
    # X6
    res["X6"] = next((d for d in range(e, x) if valid[d] and d in prev and np.isfinite(ma[d]) and np.isfinite(ma[prev[d]])
                      and c[d] < ma[d] and c[prev[d]] >= ma[prev[d]]), -1)
    # X7（原始 csv、可用日自己算）
    r = revdf[revdf["stock_id"] == sid].drop_duplicates(["stock_id", "period"], keep="last").sort_values("period")
    ev = []
    for p, rv, rl in zip(r["period"], pd.to_numeric(r["當月營收"], errors="coerce"), pd.to_numeric(r["去年當月營收"], errors="coerce")):
        if not np.isfinite(rv):
            continue
        y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(year=y2, month=m2, day=10 if p <= "2025-12" else 15)
        A = next((i for i in range(n) if cal[i] > cut), None)
        if A is None:
            continue
        ev.append((A, rv / rl - 1 if (np.isfinite(rl) and rl > 0) else math.nan))
    ev.sort()
    res["X7"] = next((ev[i][0] for i in range(1, len(ev)) if e <= ev[i][0] < x and np.isfinite(ev[i][1]) and np.isfinite(ev[i - 1][1])
                      and ev[i][1] < 0 <= ev[i - 1][1]), -1)
    out = {"base": base}
    for X, d in res.items():
        s = sell_after(d) if d >= 0 else -1
        out[X] = (d, s, (o[s] / P0 - 1 - COST - base) if s >= 0 else 0.0)
    return out


# ═════════ ② 不前視（正式程式吃截斷資料）
def trunc_trig(sid, market, e, cutpos, cal, c50ff_full, rev, rly, A):
    orig = D.load_stock

    def cut_load(s_, m_, cal_):
        st = orig(s_, m_, cal_)
        if st is not None and s_ == sid:
            df = st.df.copy()
            for col in ("open", "high", "low", "close"):
                if col in df:
                    v = df[col].to_numpy(float).copy(); v[cutpos + 1:] = np.nan; df[col] = v
            st.df = df
        return st
    D.load_stock = cut_load
    try:
        S = G.Q.stock_data(sid, market)
    finally:
        D.load_stock = orig
    c50 = c50ff_full.copy(); c50[cutpos + 1:] = np.nan
    x4, _, _ = G.cross_mkt(pd.Series(c50).ffill().to_numpy())
    x4[cutpos + 1:] = False
    x6 = G.cross_ma(S)
    turns, _ = G.rev_turns(sid, rev, rly, A)
    turns = turns[turns <= cutpos]
    x = e + H - 1
    P0 = float(S["o"][e])
    tg = G.trig_all(S, e, x, P0, x4, x6, turns)
    mom, vol = G.cut_vals(S, e - 1) if cutpos >= e - 1 else (None, None)
    return {k: v[0] for k, v in tg.items()}, (mom, vol)


# ═════════ ③ 彙總重算
def my_cr0(d, g):
    d = np.asarray(d, float); m = d.mean(); acc = {}
    for di, gi in zip(d, g):
        acc[gi] = acc.get(gi, 0.0) + (di - m)
    return m, math.sqrt(sum(v * v for v in acc.values())) / len(d)


def my_diff(d, side, g):
    """OLS d ＝ a ＋ b·side，群集三明治 CR0（矩陣式）。"""
    X = np.column_stack([np.ones(len(d)), side.astype(float)])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ d
    u = d - X @ beta
    meat = np.zeros((2, 2))
    for gi in np.unique(g):
        sel = g == gi
        sg = X[sel].T @ u[sel]
        meat += np.outer(sg, sg)
    V = XtX_inv @ meat @ XtX_inv
    return float(beta[1]), float(math.sqrt(V[1, 1]))


def main():
    rep = {}
    # ── ①②
    D.DATA = G.Q.RA.H2.H2D
    cal = D.load_calendar()
    K = pd.read_csv(os.path.join(OUT, "rows_main.csv.gz"), dtype={"sid": str})
    K = K[(K["st120"] == "保留") & (K["seg120"].isin(["explore", "confirm"]))]
    rng = np.random.default_rng(20261020)
    pick = []
    for X in G.EXITS:
        cand = K[(K[f"s{X}_120"] >= 0) & ~K.index.isin(pick)]
        pick += list(rng.choice(cand.index, 2, replace=False))
    rest = K[~K.index.isin(pick)]
    pick += list(rng.choice(rest.index, 20 - len(pick), replace=False))
    P = K.loc[pick]
    c50 = D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)
    c50ff = pd.Series(c50).ffill().to_numpy()
    revdf = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
                       for f in sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))])
    rev, rly, _ = G.R34.load_revenue(); A = G.avail_map(list(rev.index), cal)
    off = G.RA.TR.load_official()
    x4f, ma200, below200 = G.cross_mkt(c50ff)
    G.Q._init(cal, off, R11.regime_below(c50ff, 60), below200)
    rows = []; bad = 0; bad_lk = 0
    for r in P.itertuples():
        h = hand(r.sid, r.market, int(r.e), cal, c50, revdf)
        rec = {"sid": r.sid, "e": str(cal[int(r.e)].date()), "seg": r.seg120, "base_手算": h["base"], "base_程式": r.base120}
        ok = abs(h["base"] - r.base120) < 1e-12
        for X in G.EXITS:
            d, s, dd = h[X]
            pd_, ps, pD = int(getattr(r, f"d{X}_120")), int(getattr(r, f"s{X}_120")), float(getattr(r, f"D{X}_120"))
            same = (d == pd_) and (s == ps) and abs(dd - pD) < 1e-12
            ok &= same
            rec[X] = {"手算 d／s": [str(cal[d].date()) if d >= 0 else None, str(cal[s].date()) if s >= 0 else None],
                      "程式 d／s": [str(cal[pd_].date()) if pd_ >= 0 else None, str(cal[ps].date()) if ps >= 0 else None],
                      "手算 D": dd, "程式 D": pD, "同": bool(same)}
        # ② 不前視：每個有觸發的出場，截到 d
        lk = {}
        for X in G.EXITS:
            d = int(getattr(r, f"d{X}_120"))
            if d < 0:
                continue
            got, _ = trunc_trig(r.sid, r.market, int(r.e), d, cal, c50ff, rev, rly, A)
            lk[X] = bool(got[X] == d)
        _, cv = trunc_trig(r.sid, r.market, int(r.e), int(r.e) - 1, cal, c50ff, rev, rly, A)
        cut_same = all((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-15 for a, b in zip(cv, (r.mom, r.vol)))
        lk["三刀值（截到 T）"] = bool(cut_same)
        rec["不前視"] = lk
        bad += int(not ok); bad_lk += int(not all(lk.values()))
        rec["全同"] = bool(ok)
        rows.append(rec)
    rep["① 逐根手算 20 筆"] = {"不同筆數": bad, "筆": rows}
    rep["② 不前視"] = {"不通過筆數": bad_lk}
    print(f"① 手算不同 {bad}／20；② 不前視不通過 {bad_lk}／20", flush=True)
    # ── ③
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    mx = {"mean": 0.0, "se": 0.0, "n": 0}
    ncell = 0
    for world in ("main", "early"):
        R = pd.read_csv(os.path.join(OUT, f"rows_{world}.csv.gz"), dtype={"sid": str})
        R = R[R["st120"] == "保留"]
        for sg in sorted(set(R["seg120"].dropna()) - {""}):
            k = R[R["seg120"] == sg]
            g = k["mon"].to_numpy()
            for X in G.EXITS:
                d = k[f"D{X}_120"].to_numpy(float)
                m, se = my_cr0(d, g)
                c = C[(C.world == world) & (C.seg == sg) & (C.H == 120) & (C.exit == X) & (C.cut == "整體")].iloc[0]
                mx["mean"] = max(mx["mean"], abs(m - c["mean"])); mx["se"] = max(mx["se"], abs(se - c["se"])); ncell += 1
                for cu, (pos, neg) in G.CUTS.items():
                    v = k[cu].to_numpy(); sel = v >= 0
                    b, sb = my_diff(d[sel], v[sel], g[sel])
                    c = C[(C.world == world) & (C.seg == sg) & (C.H == 120) & (C.exit == X) & (C.cut == cu) & (C.side == f"{pos}−{neg}")].iloc[0]
                    mx["mean"] = max(mx["mean"], abs(b - c["mean"])); mx["se"] = max(mx["se"], abs(sb - c["se"])); ncell += 1
    rep["③ 彙總重算"] = {"格數": ncell, "最大差（平均）": mx["mean"], "最大差（SE）": mx["se"]}
    # 判定重算
    V = json.load(open(os.path.join(OUT, "verdict.json"), encoding="utf-8"))
    z = G.ZB; diffv = 0
    for v in V:
        sides = []
        for sg in ("explore", "confirm"):
            q = v[sg]; lo, hi = q["est"] - 0, q["est"]
            c = C[(C.world == "main") & (C.seg == sg) & (C.H == 120) & (C.exit == v["exit"]) & (C.cut == v["cut"]) & (C.side == v["side"])].iloc[0]
            lo, hi = c["mean"] - z * c["se"], c["mean"] + z * c["se"]
            sides.append("正" if (lo > 0 and c["n_eff"] >= 30) else ("負" if (hi < 0 and c["n_eff"] >= 30) else "x"))
        mine = f"成立（{sides[0]}）" if sides[0] == sides[1] and sides[0] != "x" else "分不出"
        diffv += int(mine != v["判定"])
    rep["③ 判定重算"] = {"不同": diffv, "格": len(V)}
    print(f"③ 彙總 {ncell} 格 最大差 平均 {mx['mean']:.2e} SE {mx['se']:.2e}；判定不同 {diffv}／{len(V)}", flush=True)
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
