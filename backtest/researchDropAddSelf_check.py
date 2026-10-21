# -*- coding: utf-8 -*-
"""researchDropAddSelf 獨立查核——回測線計算子代理，2026-10-21。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDropAddSelf_check fixture   # 合成資料（⛔ 無真實報酬）
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDropAddSelf_check post      # 正式跑後：真實資料逐日迴圈重算

查核法：另寫一支「逐日狀態機」naive()（⛔ 不呼叫主程式的 overlay／lot_paths／make_hold_fn；持股挑選、權重、出場、賣回、0050 備用、T2、併入全部自己寫）
  F1 合成資料 300 組隨機情境 × 8 臂：naive 淨值 ＝ overlay 淨值（逐日、絕對差 ≤ 1e−10）
  F2 手算情境：單一持股、價格已知 ⇒ A 臂淨值逐日 ＝ 手算式
  F3 不變式：無事件 ⇒ 各臂 ＝ 對照；100% ＝ E/E_x；A、D 對同 w 對照的淨值差 ＝ Σ 事件損益
  P1 正式資料：單顆策略（營量 v1、全買版、0050、正2、六四）× 三段 × 8 臂 ⇒ naive 重算年化／回落 ＝ table.csv（%.10g）
  P2 多顆策略（營飆 v1、高10）前 20 顆 × 8 臂：naive 淨值末值 ＝ overlay 末值（≤ 1e−10）
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchDropAddSelf as M                # noqa: E402

COST_ETF = 0.00385


def naive_hold(P, CL, OP, e, d):
    out = []
    for i in range(len(P["k"])):
        if P["tb"][i] <= e and P["tpx"][i] >= d:
            r = int(P["k"][i]); mv = P["amt"][i] * CL[r, e] / P["ep"][i]; p = OP[r, d]
            if np.isfinite(p) and p > 0 and np.isfinite(mv) and mv > 0:
                out.append([r, mv, p, int(P["tpx"][i]), P["exv"][i]])
    if not out:
        return None
    tot = sum(o[1] for o in out)
    return [(o[0], o[1] / tot, o[2], o[3], o[4]) for o in out]


def naive_etf(rows, wts, CL, OP, d):
    out = []
    for r, w in zip(rows, wts):
        p = OP[r, d]
        if not (np.isfinite(p) and p > 0):
            p = CL[r, d - 1]
        out.append((r, w, p, M.BIG, np.nan))
    return out


def naive(E, x, y, evs, arm, holdf, CL, OP, cost, O50, C50, base):
    w, mode, pool = arm["w"], arm["mode"], arm["pool"]
    r0 = 1.0 - w
    Eb = E[x] if base == "close" else 1.0
    cash = r0 if pool == "cash" else 0.0
    units = (r0 / (C50[x] if base == "close" else O50[x])) if pool == "0050" else 0.0
    lots = []                        # [row, a, p, tpx, exv, alive]
    merged = 0.0
    usedB = False
    byd = {}; bys = {}; byta = {}
    if mode != "none" and r0 > 0:
        for ev in evs:
            byd[ev["d"]] = ev
            if ev["s"] is not None:
                bys[ev["s"]] = ev
            if ev["ta"] is not None:
                byta[ev["ta"] + 1] = ev
    nav = np.zeros(y - x + 1)
    for t in range(x, y + 1):
        if mode in ("A", "D") and t in bys:
            for L in lots:
                if L[5]:
                    px = OP[L[0], t]
                    if not (np.isfinite(px) and px > 0):
                        px = CL[L[0], t - 1]
                    cash += L[1] * (px / L[2] - cost); L[5] = False
            if pool == "0050":
                px = O50[t] if (np.isfinite(O50[t]) and O50[t] > 0) else C50[t - 1]
                units += cash / px; cash = 0.0
        if t in byd and not (mode == "B" and usedB):
            ev = byd[t]; H = holdf(ev["e"], t)
            if H is not None:
                if pool == "0050":
                    px = O50[t] if (np.isfinite(O50[t]) and O50[t] > 0) else C50[t - 1]
                    dep = units * px * (1 - COST_ETF) + cash; units = 0.0; cash = 0.0
                else:
                    dep = cash * (0.5 if mode == "D" else 1.0); cash -= dep
                for (r, wt, p, tpx, exv) in H:
                    lots.append([r, dep * wt, p, tpx, exv, True])
                if mode == "B":
                    usedB = True
        if mode == "D" and t in byta:
            ev = byta[t]; H = holdf(ev["ta"], t)
            first = holdf(ev["e"], ev["d"]) is not None
            if H is not None and cash * (1.0 if first else 0.5) > 1e-12:
                dep = cash * (1.0 if first else 0.5); cash -= dep
                for (r, wt, p, tpx, exv) in H:
                    lots.append([r, dep * wt, p, tpx, exv, True])
        for L in lots:
            if L[5] and L[3] == t:
                pr = L[1] * (L[4] / L[2] - cost); L[5] = False
                if mode == "B":
                    merged += pr / E[t]
                else:
                    cash += pr
        v = sum(L[1] * CL[L[0], t] / L[2] for L in lots if L[5])
        nav[t - x] = w * E[t] / Eb + cash + units * C50[t] + v + merged * E[t]
    return nav


# ═════════════ fixture ═════════════
def rand_case(rng):
    n, ns = 160, 7
    CL = np.cumprod(1 + rng.normal(0, 0.02, (ns, n)), axis=1) * rng.uniform(10, 100, (ns, 1))
    OP = np.c_[CL[:, :1], CL[:, :-1]] * (1 + rng.normal(0, 0.01, (ns, n)))
    OP[rng.random((ns, n)) < 0.05] = np.nan
    C50 = np.cumprod(1 + rng.normal(0, 0.01, n)) * 50; O50 = np.r_[C50[0], C50[:-1]] * (1 + rng.normal(0, 0.005, n))
    O50[rng.random(n) < 0.03] = np.nan
    E = np.cumprod(1 + rng.normal(0.0005, 0.015, n))
    m = rng.integers(15, 40)
    tb = rng.integers(0, n - 5, m); dur = rng.integers(1, 60, m)
    tpx = np.where(rng.random(m) < 0.15, M.BIG, np.minimum(tb + dur, n - 1)).astype(np.int64)
    k = rng.integers(0, ns, m)
    ep = CL[k, tb] * rng.uniform(0.9, 1.1, m); amt = rng.uniform(0.02, 0.2, m)
    exv = np.where(tpx < M.BIG, CL[k, np.minimum(tpx, n - 1)], np.nan)
    P = {"k": k, "tb": tb.astype(np.int64), "ep": ep, "amt": amt, "exv": exv, "tpx": tpx}
    x = int(rng.integers(0, 20)); y = n - 1 - int(rng.integers(0, 10))
    evs = []; t = x + int(rng.integers(0, 10))
    kk = 0
    while t < y - 2:
        e = t; d = e + 1
        s = e + int(rng.integers(2, 30))
        s = s if s <= y else None
        ta = None
        if rng.random() < 0.5:
            cand = e + int(rng.integers(1, 10))
            if cand + 1 <= y and (s is None or cand + 1 < s):
                ta = cand
        evs.append({"k": kk, "e": e, "d": d, "s": s, "ta": ta}); kk += 1
        if s is None:
            break
        t = s + int(rng.integers(1, 15))
    return dict(CL=CL, OP=OP, C50=C50, O50=O50, E=E, P=P, x=x, y=y, evs=evs, n=n)


def fixture():
    rng = np.random.default_rng(20261021)
    worst, cnt, ident = 0.0, 0, 0.0
    for rep in range(300):
        c = rand_case(rng)
        etf = rep % 5 == 0
        base = "open" if rep % 7 == 0 else "close"
        if etf:
            fn = M.make_etf_fn([0, 1], [0.6, 0.4], c["CL"], c["OP"])
            hf = (lambda e, d, c=c: naive_etf([0, 1], [0.6, 0.4], c["CL"], c["OP"], d))
        else:
            fn = M.make_hold_fn(c["P"], c["CL"], c["OP"])
            hf = (lambda e, d, c=c: naive_hold(c["P"], c["CL"], c["OP"], e, d))
        cost = 0.00385 if etf else 0.00585
        NE = {}
        ALL = dict(M.ARMS); ALL.update({"split " + k: v for k, v in M.ARMS_SPLIT.items()})
        for arm, cfg in ALL.items():
            a, info = M.overlay(c["E"], c["x"], c["y"], c["evs"], cfg, fn, c["CL"], c["OP"], cost, c["O50"], c["C50"], base)
            b = naive(c["E"], c["x"], c["y"], c["evs"], cfg, hf, c["CL"], c["OP"], cost, c["O50"], c["C50"], base)
            worst = max(worst, float(np.max(np.abs(a - b)))); cnt += 1
            NE[arm] = (a[-1], info)
        for arm, ct in (("A", "80%＋20%現金"), ("D", "60%＋40%現金")):
            sp = sum(r["回收"] + r["窗尾市值"] - r["投入"] for r in NE[arm][1])
            ident = max(ident, abs(NE[arm][0] - NE[ct][0] - sp))
    # F2 手算：一檔、成本 0；e＝2、d＝3、s＝6；股價 10,10,10, 開 9 收 12, 15, 15, 開 18 ⇒ A 淨值
    CL = np.array([[10, 10, 10, 12, 15, 15, 20, 20.]]); OP = np.array([[10, 10, 10, 9, 13, 15, 18, 20.]])
    E = np.array([1, 1, 1, 1.1, 1.2, 1.2, 1.3, 1.3])
    P = {"k": np.array([0]), "tb": np.array([0]), "ep": np.array([10.]), "amt": np.array([1.]), "exv": np.array([np.nan]), "tpx": np.array([M.BIG])}
    evs = [{"k": 0, "e": 2, "d": 3, "s": 6, "ta": None}]
    a, _ = M.overlay(E, 0, 7, evs, M.ARMS["A"], M.make_hold_fn(P, CL, OP), CL, OP, 0.0, None, None, "close")
    lot = 0.2 / 9
    hand = np.array([1.0, 1.0, 1.0, 0.8 * 1.1 + lot * 12, 0.8 * 1.2 + lot * 15, 0.8 * 1.2 + lot * 15, 0.8 * 1.3 + lot * 18, 0.8 * 1.3 + lot * 18])
    f2 = float(np.max(np.abs(a - hand)))
    # F3 無事件
    c = rand_case(np.random.default_rng(7)); f3 = 0.0
    fn = M.make_hold_fn(c["P"], c["CL"], c["OP"])
    for arm, cfg in M.ARMS.items():
        a, _ = M.overlay(c["E"], c["x"], c["y"], [], cfg, fn, c["CL"], c["OP"], 0.00585, c["O50"], c["C50"], "close")
        ctl = cfg["w"] * c["E"][c["x"]:c["y"] + 1] / c["E"][c["x"]] + ((1 - cfg["w"]) if cfg["pool"] == "cash" else (1 - cfg["w"]) / c["C50"][c["x"]] * c["C50"][c["x"]:c["y"] + 1])
        f3 = max(f3, float(np.max(np.abs(a - ctl))))
    R = {"F1 naive vs overlay 最大逐日差（300 情境 × 8 臂＋split 4 臂）": worst, "F1 比對次數": cnt, "F3 A／D 恆等式最大差": ident, "F2 手算最大差": f2, "F3 無事件 各臂 vs 對照 最大差": f3}
    ok = worst <= 1e-10 and ident <= 1e-10 and f2 <= 1e-12 and f3 <= 1e-12
    R["過"] = bool(ok)
    print(json.dumps(R, ensure_ascii=False, indent=1))
    os.makedirs(M.SPLIT_OUT, exist_ok=True)                  # ⛔ 不覆寫已 commit 的 resultsDropAddSelf/check_fixture.json（10/21 split 起寫到 split/）
    json.dump(R, open(os.path.join(M.SPLIT_OUT, "check_fixture.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not ok:
        raise SystemExit("⛔ fixture 不過")


# ═════════════ post ═════════════
def post():
    from backtest import benchmark_rejudge as BR
    from backtest import researchAscTri as AS
    from backtest import researchLev2 as L2
    T = pd.read_csv(os.path.join(M.OUT, "table.csv"), float_precision="round_trip")
    _, evs = M.load_events()
    R = {"P1 不同（格）": 0, "P1 比對格": 0, "P2 最大末值差": 0.0, "P2 比對": 0, "不同明細": []}
    SX = M.six4_world()
    for sg, (wn, a_, b_) in M.SEGS.items():
        Wd = M.load_world(wn); cal = Wd["cal"]; n = len(cal); x, y = BR.seg_pos(cal, a_, b_)
        m, _ = M.map_events(evs, cal, x, y)
        names = [k for k in Wd["S"]] + (["六四 v1"] if sg in ("確認", "探索") else [])
        for nm in names:
            if nm == "六四 v1":
                w0, w1 = (a_, b_) if sg == "確認" else M.SIX4_EXP
                X = SX["X"]; i0, i1 = X["pos"][w0], X["pos"][w1]
                eq, _ = BR.six4_eq(w0, w1); E = np.full(len(SX["cal"]), np.nan); E[i0:i1 + 1] = eq
                mm, _ = M.map_events(evs, SX["cal"], i0, i1)
                runs = [(E, (lambda e, d: naive_etf([0, 1], [0.6, 0.4], SX["CL"], SX["OP"], d)), None)]
                ctx = (i0, i1, mm, SX["CL"], SX["OP"], COST_ETF, SX["OP"][0], SX["CL"][0], "open")
                stat = L2.perf
            else:
                s = Wd["S"][nm]
                if s["P"] is None:
                    r_, w_ = s["etf"]
                    runs = [(s["E"][0], (lambda e, d, s=s, r_=r_, w_=w_: naive_etf(r_, w_, s["CL"], s["OP"], d)), None)]
                else:
                    K = 1 if len(s["P"]) == 1 else 20
                    runs = [(s["E"][i], (lambda e, d, s=s, i=i: naive_hold(s["P"][i], s["CL"], s["OP"], e, d)), M.make_hold_fn(s["P"][i], s["CL"], s["OP"])) for i in range(K)]
                ctx = (x, y, m, s["CL"], s["OP"], s["cost"], Wd["O50"], Wd["C50"], "close")
                stat = (lambda nav, x=x, y=y, n=n: M.stat_close(nav, x, y, n))
            for arm, cfg in M.ARMS.items():
                if nm == "0050" and arm == "C":
                    cfg = dict(cfg, mode="none")
                if len(runs) == 1:
                    nav = naive(runs[0][0], *ctx[:3], cfg, runs[0][1], *ctx[3:])
                    c, md = stat(nav)
                    q = T[(T["段"] == sg) & (T["策略"] == nm) & (T["臂"] == arm)].iloc[0]
                    R["P1 比對格"] += 1
                    if "%.10g" % c != "%.10g" % q["年化"] or "%.10g" % md != "%.10g" % q["回落"]:
                        R["P1 不同（格）"] += 1; R["不同明細"].append([sg, nm, arm, c, q["年化"], md, q["回落"]])
                else:
                    for (E_, hf, fn) in runs:
                        nb = naive(E_, *ctx[:3], cfg, hf, *ctx[3:])
                        na, _ = M.overlay(E_, *ctx[:3], cfg, fn, *ctx[3:])
                        R["P2 最大末值差"] = max(R["P2 最大末值差"], float(np.max(np.abs(na - nb)))); R["P2 比對"] += 1
            print(sg, nm, "done", flush=True)
    R["過"] = R["P1 不同（格）"] == 0 and R["P2 最大末值差"] <= 1e-10
    print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    json.dump(R, open(os.path.join(M.OUT, "check_post.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if not R["過"]:
        raise SystemExit("⛔ post 查核不過")


def post_split():
    """P3 split：單顆策略 × 三段 × 4 臂 ⇒ naive 重算加碼帳年化／回落 ＝ split/table.csv（%.10g）；多顆前 20 顆 naive ＝ overlay。"""
    from backtest import benchmark_rejudge as BR
    from backtest import researchLev2 as L2
    T = pd.read_csv(os.path.join(M.SPLIT_OUT, "table.csv"), float_precision="round_trip")
    _, evs = M.load_events()
    R = {"P3 不同（格）": 0, "P3 比對格": 0, "P4 最大差": 0.0, "P4 比對": 0, "不同明細": []}
    SX = M.six4_world()
    for sg, (wn, a_, b_) in M.SEGS.items():
        Wd = M.load_world(wn); cal = Wd["cal"]; n = len(cal); x, y = BR.seg_pos(cal, a_, b_)
        m, _ = M.map_events(evs, cal, x, y)
        names = [k for k in Wd["S"]] + (["六四 v1"] if sg in ("確認", "探索") else [])
        for nm in names:
            if nm == "六四 v1":
                w0, w1 = (a_, b_) if sg == "確認" else M.SIX4_EXP
                X = SX["X"]; i0, i1 = X["pos"][w0], X["pos"][w1]
                eq, _ = BR.six4_eq(w0, w1); E = np.full(len(SX["cal"]), np.nan); E[i0:i1 + 1] = eq
                mm, _ = M.map_events(evs, SX["cal"], i0, i1)
                runs = [(E, (lambda e, d: naive_etf([0, 1], [0.6, 0.4], SX["CL"], SX["OP"], d)), None)]
                ctx = (i0, i1, mm, SX["CL"], SX["OP"], COST_ETF, SX["OP"][0], SX["CL"][0], "open"); stat = L2.perf
            else:
                s = Wd["S"][nm]
                if s["P"] is None:
                    r_, w_ = s["etf"]
                    runs = [(s["E"][0], (lambda e, d, s=s, r_=r_, w_=w_: naive_etf(r_, w_, s["CL"], s["OP"], d)), None)]
                else:
                    K = 1 if len(s["P"]) == 1 else 20
                    runs = [(s["E"][i], (lambda e, d, s=s, i=i: naive_hold(s["P"][i], s["CL"], s["OP"], e, d)), M.make_hold_fn(s["P"][i], s["CL"], s["OP"])) for i in range(K)]
                ctx = (x, y, m, s["CL"], s["OP"], s["cost"], Wd["O50"], Wd["C50"], "close")
                stat = (lambda nav, x=x, y=y, n=n: M.stat_close(nav, x, y, n))
            for arm, cfg in M.ARMS_SPLIT.items():
                if nm == "0050" and arm == "C′":
                    cfg = dict(cfg, mode="none")
                if len(runs) == 1:
                    nav = naive(runs[0][0], *ctx[:3], cfg, runs[0][1], *ctx[3:])
                    c, md = stat(nav)
                    q = T[(T["段"] == sg) & (T["策略"] == nm) & (T["臂"] == arm)].iloc[0]
                    R["P3 比對格"] += 1
                    if "%.10g" % c != "%.10g" % q["年化"] or "%.10g" % md != "%.10g" % q["回落"]:
                        R["P3 不同（格）"] += 1; R["不同明細"].append([sg, nm, arm, c, q["年化"], md, q["回落"]])
                else:
                    for (E_, hf, fn) in runs:
                        nb = naive(E_, *ctx[:3], cfg, hf, *ctx[3:])
                        na, _ = M.overlay(E_, *ctx[:3], cfg, fn, *ctx[3:])
                        R["P4 最大差"] = max(R["P4 最大差"], float(np.max(np.abs(na - nb)))); R["P4 比對"] += 1
    R["過"] = R["P3 不同（格）"] == 0 and R["P4 最大差"] <= 1e-10
    print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    json.dump(R, open(os.path.join(M.SPLIT_OUT, "check_post.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if not R["過"]:
        raise SystemExit("⛔ post_split 查核不過")


if __name__ == "__main__":
    {"fixture": fixture, "post": post, "post_split": post_split}[sys.argv[1] if len(sys.argv) > 1 else "fixture"]()
