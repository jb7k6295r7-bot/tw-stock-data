# -*- coding: utf-8 -*-
"""researchExitGen_x7b 獨立查核（seq395 (c) 描述件；回測線計算子代理，2026-10-20）。⛔ 只讀 resultsExitGen/x7b 的輸出、不改任何檔；結果寫 x7b/check.json。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExitGen_x7b_check.py

 ① 抽 20 筆（主世界 H120 段內保留；X7b 有觸發 ≥7、X7c 有觸發 ≥6、「X7b 觸發而 X7 沒觸發」≥3、其餘隨機；種子 20261020）逐筆手算：
    自己讀 revenue_hist 原始 csv、可用日用迴圈（10／15 日之後第一個交易日）、連負用「計數器」寫法（⛔ 不呼叫 x7b 的 run_events／seq6 的 rev_turns）、
    可賣開盤用 tradability.one 迴圈、基準用 D.load_stock 還原收盤 ⇒ 對 x7b/rows_main 的 d、s、base、D 逐筆比（X7、X7b、X7c 三種）
 ② 彙總重算：從 x7b/rows_{main,early} 用自己寫的 CR0（逐群迴圈）重算整體 d、SE、與 X7 配對差 ⇒ 對 x7b/cells.csv
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
import researchExitGen as G                                   # 只取 D、資料路徑常數
from backtest import tradability as TR

D = G.D
OUT = os.path.join(G.OUT, "x7b")
COST = 0.00585
H = 120
KS = {"X7": 1, "X7b": 2, "X7c": 3}


def hand(sid, market, e, cal, revdf):
    st = D.load_stock(sid, market, cal); df = st.df
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    tb = TR.one(sid, cal)
    n = len(cal); x = e + H - 1
    P0 = float(o[e])
    j = max(i for i in range(e, x + 1) if np.isfinite(c[i]))
    base = c[j] / P0 - 1 - COST

    def sell_after(d):
        for t in range(d + 1, n):
            if tb["trd"][t] and not tb["dn_o"][t] and np.isfinite(o[t]) and o[t] > 0:
                return t if t < x else -1
        return -1
    r = revdf[revdf["stock_id"] == sid].drop_duplicates(["stock_id", "period"], keep="last")
    ev = []
    for p, rv, rl in zip(r["period"], pd.to_numeric(r["當月營收"], errors="coerce"), pd.to_numeric(r["去年當月營收"], errors="coerce")):
        if not np.isfinite(rv):
            continue
        y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(year=y2, month=m2, day=10 if p <= "2025-12" else 15)
        A = next((i for i in range(n) if cal[i] > cut), None)
        if A is None or A == 0:
            continue
        ev.append((A, p, rv / rl - 1 if (np.isfinite(rl) and rl > 0) else math.nan))
    ev.sort()
    out = {"base": base, "序列": []}
    for X, k in KS.items():
        run = None; d = -1                                      # run：None ＝ 未武裝（還沒看到 ≥0 或剛遇不可算）
        for A, p, yy in ev:
            if not np.isfinite(yy):
                run = None; continue
            if yy >= 0:
                run = 0; continue
            if run is None:
                continue
            run += 1
            if run == k and e <= A < x:
                d = A; break
        s = sell_after(d) if d >= 0 else -1
        out[X] = (d, s, (o[s] / P0 - 1 - COST - base) if s >= 0 else 0.0)
    # 給人看的：持有期前後的年增序列
    out["序列"] = [(str(cal[A].date()), p, None if not np.isfinite(yy) else round(yy, 4)) for A, p, yy in ev if e - 130 <= A < x + 5]
    return out


def my_cr0(d, g):
    d = np.asarray(d, float); m = d.mean(); acc = {}
    for di, gi in zip(d, g):
        acc[gi] = acc.get(gi, 0.0) + (di - m)
    return m, math.sqrt(sum(v * v for v in acc.values())) / len(d)


def main():
    rep = {}
    D.DATA = G.Q.RA.H2.H2D
    cal = D.load_calendar()
    K = pd.read_csv(os.path.join(OUT, "rows_main.csv.gz"), dtype={"sid": str})
    K = K[(K["st"] == "保留") & (K["seg"].isin(["explore", "confirm"]))]
    rng = np.random.default_rng(20261020)
    pick = []
    for cond, m in (((K["sX7b"] >= 0) & (K["sX7"] < 0), 3), (K["sX7b"] >= 0, 4), (K["sX7c"] >= 0, 6)):
        cand = K[cond & ~K.index.isin(pick)]
        pick += list(rng.choice(cand.index, m, replace=False))
    rest = K[~K.index.isin(pick)]
    pick += list(rng.choice(rest.index, 20 - len(pick), replace=False))
    P = K.loc[pick]
    revdf = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
                       for f in sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))])
    rows = []; bad = 0; ntrig = {X: 0 for X in KS}
    for r in P.itertuples():
        h = hand(r.sid, r.market, int(r.e), cal, revdf)
        rec = {"sid": r.sid, "e": str(cal[int(r.e)].date()), "seg": r.seg, "base_手算": h["base"], "base_程式": r.base}
        ok = abs(h["base"] - r.base) < 1e-12
        for X in KS:
            d, s, dd = h[X]
            pd_, ps, pD = int(getattr(r, f"d{X}")), int(getattr(r, f"s{X}")), float(getattr(r, f"D{X}"))
            same = (d == pd_) and (s == ps) and abs(dd - pD) < 1e-12
            ok &= same; ntrig[X] += int(ps >= 0)
            rec[X] = {"手算 d／s": [str(cal[d].date()) if d >= 0 else None, str(cal[s].date()) if s >= 0 else None],
                      "程式 d／s": [str(cal[pd_].date()) if pd_ >= 0 else None, str(cal[ps].date()) if ps >= 0 else None],
                      "手算 D": dd, "程式 D": pD, "同": bool(same)}
        rec["年增序列（可用日, 期別, yoy）"] = h["序列"]
        rec["全同"] = bool(ok); bad += int(not ok)
        rows.append(rec)
    rep["① 抽 20 筆手算"] = {"不同筆數": bad, "20 筆中有觸發": ntrig, "筆": rows}
    print(f"① 手算不同 {bad}／20；有觸發 {ntrig}", flush=True)
    # ── ②
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    mx = {"mean": 0.0, "se": 0.0, "trig_frac": 0.0, "vsX7_mean": 0.0, "vsX7_se": 0.0}; ncell = 0
    for world in ("main", "early"):
        R = pd.read_csv(os.path.join(OUT, f"rows_{world}.csv.gz"), dtype={"sid": str})
        R = R[R["st"] == "保留"]
        for sg in sorted(set(R["seg"].dropna()) - {""}):
            k = R[R["seg"] == sg]; g = k["mon"].to_numpy()
            for X in KS:
                d = k[f"D{X}"].to_numpy(float)
                m, se = my_cr0(d, g)
                c = C[(C.world == world) & (C.seg == sg) & (C.exit == X)].iloc[0]
                mx["mean"] = max(mx["mean"], abs(m - c["mean"])); mx["se"] = max(mx["se"], abs(se - c["se"]))
                mx["trig_frac"] = max(mx["trig_frac"], abs(float((k[f"s{X}"] >= 0).mean()) - c["trig_frac"]))
                if X != "X7":
                    m2, se2 = my_cr0(d - k["DX7"].to_numpy(float), g)
                    mx["vsX7_mean"] = max(mx["vsX7_mean"], abs(m2 - c["vsX7_mean"])); mx["vsX7_se"] = max(mx["vsX7_se"], abs(se2 - c["vsX7_se"]))
                ncell += 1
    rep["② 彙總重算"] = {"格數": ncell, "最大差": mx}
    print(f"② 彙總 {ncell} 格 最大差 {mx}", flush=True)
    rep["摘要"] = {"抽 20 筆手算 d／s／base／D 不同": f"{bad}／20", "20 筆中有觸發": ntrig, "彙總重算格數": ncell,
                 "彙總最大差": {k: f"{v:.1e}" for k, v in mx.items()}}
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
