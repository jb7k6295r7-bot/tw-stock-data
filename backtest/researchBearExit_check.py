# -*- coding: utf-8 -*-
"""researchBearExit 獨立查核（回測線計算子代理，2026-10-17）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBearExit_check [--procs 3]

獨立寫法（⛔ 不 import researchBearExit、researchExit5、researchAddOn、patterns_all、exit_signal）：
 C1 型態：抽樣股（每世界 隨機 60 檔 ＋ 有任何臂觸發列的股）自寫逐根迴圈重算 S09 下降三角向下（擺動點 R＝5 嚴格、120 日轉折集合、np.polyfit 兩線、
    相對斜率 ±0.05%／日、2% 碰觸、60 日突破窗、由內而外跌破）、S27 V 型反轉（逐 b 迴圈）、MA20 連 3 日（逐根 np.mean）⇒ 與 events_{世界}.csv.gz 逐筆比
 C2 逐列：抽樣列（每 世界×策略 隨機 50 列 ＋ 全部 X0／X1／X2 觸發列）用 C1 的事件、load_bars traded、壞根（bad_*.pkl＋早年 R8／reduce_v2 自讀）
    逐日迴圈重算 X0～X5 觸發、訊號日 d、賣出日 X、xpos、g ⇒ 與 rows 表比（g 差 ≤ 1e−9）
 C3 組合：由 rows 表自組合成收盤（逐日迴圈）⇒ 正式引擎 ⇒ 權益與 ~/bearexitwork/eq.pkl 逐位元比、自寫年化／回落與 seeds.csv.gz 比（≤ 1e−9）：
    營量全部臂；營飆 A、X0 200 顆、其餘臂前 20 顆
 C4 隨機日賣：抽中規則（每買進年筆數 ＝ 原策略持股中 X0 觸發筆數、日子在可抽集合）全部重驗；每模式前 10 次重跑引擎比 eq_sha、年化／回落
 C5 主表、判定、p 值：由 seeds.csv.gz、rand.csv.gz 自算 ⇒ 與 BearExit_main.csv、BearExit.json 比
 C6 大盤版：自寫偵測（同 C1）＋自寫進出迴圈 ⇒ 與 BearExit_market.csv 比（≤ 1e−9）
 C7 degeneracy.json 修改時間早於 seeds.csv.gz、BearExit.json
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from collections import defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import researchExit5_check as E5C             # noqa: E402  只用 Pop、early_extra、stock_bad（自讀壞根）

OUT = "backtest/resultsBearExit"
WORK = os.path.expanduser("~/bearexitwork")
AWORK = os.path.expanduser("~/addonwork")
NSEED = 200
TOL = 1e-9
STRS = {"營量": (60, 20, False), "營飆": (120, 10, True)}
VARS = ["A", "X0", "X1", "X2", "X3", "X4", "X5"]
ARMS = VARS[1:]
SEGN = {"主": ["探索", "確認", "主窗"], "早年": ["早年"]}
TAIEX = os.path.expanduser("~/us-stock-data/data/macro/twse_taiex.csv")
CS, CB = 0.002425, 0.001425
NREP = 10
if os.environ.get("BX_QUICK"):                                   # 煙霧測試（不是交件）
    OUT, WORK, NSEED, NREP = "/tmp/bx_quick", "/tmp/bx_quick/work", 3, 3
_G: dict = {}


def wstats(nav):
    yrs = len(nav) / 245
    if len(nav) < 245:
        return np.nan, np.nan
    c = (nav[-1] / nav[0]) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(nav)
    return c, float(((nav - pk) / pk).min())


def rat(c, m):
    return c / abs(m) if (np.isfinite(c) and np.isfinite(m) and m != 0) else np.nan


# ═════════ C1 自寫偵測 ═════════
def swings(x, high):
    n = len(x); out = []
    for s in range(5, n - 5):
        v = x[s]; ok = True
        for j in list(range(s - 5, s)) + list(range(s + 1, s + 6)):
            if not ((v > x[j]) if high else (v < x[j])):
                ok = False; break
        if ok:
            out.append(s)
    return out


def build_desc(piv, b):
    s_last = piv[-1][0]
    S = [p for p in piv if p[0] >= s_last - 119]
    Hs = [(s, y) for s, k, y in S if k == "H"]; Ls = [(s, y) for s, k, y in S if k == "L"]
    if len(Hs) < 2 or len(Ls) < 2:
        return None

    def fit(P):
        x = np.array([p[0] for p in P], float); y = np.array([p[1] for p in P], float)
        if np.ptp(x) == 0:
            return None
        # 一次最小平方（中心化正規方程；⚠ 不用 np.polyfit：兩點同價時 polyfit 斜率有 1e−16 雜訊，平線上剛好等價的收盤會翻判）
        xm = sum(x) / len(x); ym = sum(y) / len(y)
        bta = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y)) / sum((xi - xm) ** 2 for xi in x)
        alp = ym - bta * xm
        yh = alp + bta * x
        on = int(sum(abs(y[i] - yh[i]) <= 0.02 * yh[i] for i in range(len(y))))
        return alp, bta, bta / y.mean(), on
    fu, fl = fit(Hs), fit(Ls)
    if fu is None or fl is None:
        return None
    cu = "up" if fu[2] > 0.0005 else ("dn" if fu[2] < -0.0005 else "flat")
    cl = "up" if fl[2] > 0.0005 else ("dn" if fl[2] < -0.0005 else "flat")
    if not (cu == "dn" and cl == "flat"):
        return None
    if not (fu[0] + fu[1] * b > fl[0] + fl[1] * b):
        return None
    if not (fu[1] < fl[1]):
        return None
    if not (fu[3] >= 2 and fl[3] >= 2 and fu[3] + fl[3] >= 5):
        return None
    return {"au": fu[0], "bu": fu[1], "al": fl[0], "bl": fl[1], "conf": b, "first": S[0][0]}


def s09(h, l, c):
    n = len(c); conf = defaultdict(list)
    for s in swings(h, True):
        conf[s + 5].append((s, "H", h[s]))
    for s in swings(l, False):
        conf[s + 5].append((s, "L", l[s]))
    piv = []; G = None; ev = []
    for b in range(n):
        if G is not None:
            if b - G["conf"] > 60:
                G = None
            elif b >= G["conf"] + 1:
                lu = G["au"] + G["bu"] * b; ll = G["al"] + G["bl"] * b
                if not lu > ll:
                    G = None
                else:
                    lu1 = G["au"] + G["bu"] * (b - 1); ll1 = G["al"] + G["bl"] * (b - 1)
                    if c[b] > lu and c[b - 1] <= lu1:
                        G = None
                    elif c[b] < ll and c[b - 1] >= ll1:
                        ev.append((b, G["first"])); G = None
        if b in conf:
            piv += conf[b]; piv.sort(key=lambda p: p[0])
            G = build_desc(piv, b)
    return ev


def s27(c, v):
    n = len(c); out = {}
    for b in range(20, n):
        w = c[b - 20:b]
        if not np.all(np.isfinite(w)) or not all(c[b] <= c[j] for j in range(b - 19, b)):
            continue
        P = max(w)
        if (P - c[b]) / P < 0.25:
            continue
        vw = v[b - 20:b]
        if not (np.isfinite(v[b]) and np.all(np.isfinite(vw)) and v[b] >= 2.0 * np.mean(vw)):
            continue
        lvl = c[b] + 0.5 * (P - c[b])
        for T in range(b + 1, min(n, b + 11)):
            if c[T] >= lvl:
                first = b - 20 + int(np.argmax(w)); out[T] = (T, first); break
    return [out[t] for t in sorted(out)]


def ma_d3(c):
    n = len(c); ma = np.full(n, np.nan)
    for i in range(19, n):
        ma[i] = np.mean(c[i - 19:i + 1])
    ev = []
    for t in range(1, n):
        if np.isfinite(ma[t]) and np.isfinite(ma[t - 1]) and c[t] < ma[t] and c[t - 1] >= ma[t - 1]:
            if t + 2 < n and c[t + 1] < ma[t + 1] and c[t + 2] < ma[t + 2] and t + 2 + 1 >= 80:
                ev.append(t + 2)
    return ev


def ind_detect(h, l, c, v):
    bars = np.flatnonzero(np.isfinite(c))
    hb, lb, cb, vb = (np.asarray(x, float)[bars] for x in (h, l, c, v))
    return {"S09": [(int(bars[t]), int(bars[f])) for t, f in s09(hb, lb, cb)], "S27": [(int(bars[t]), int(bars[f])) for t, f in s27(cb, vb)],
            "MA": [int(bars[t]) for t in ma_d3(cb)]}


def c1_job(a):
    sid, mk = a
    D.DATA = _G["data"]
    st = D.load_stock(sid, mk, _G["cal"])
    df = st.df
    return sid, ind_detect(*(df[k].to_numpy(float) for k in ("high", "low", "close", "volume")))


# ═════════ C2 逐列 ═════════
def row_check(r, W, LB, bad, DV, n0, NP):
    sid = r["sid"]; e = int(r["e"]); xf = int(r["xf"]); gf = float(r["gf"]); L = int(r["L"]); L = None if L < 0 else L
    c = np.asarray(W["closes"][sid], float); o = np.asarray(W["opens"][sid], float)
    isb = np.zeros(n0, bool); isb[[int(x) for x in LB["idx"] if x < n0]] = True
    bp = o[e] if (np.isfinite(o[e]) and o[e] > 0) else c[e]
    kb = None
    for p in range(e + 1, NP):
        if bad[p]:
            kb = p; break
    db = None
    if kb is not None:
        db = e
        for p in range(e, min(kb, n0)):
            if isb[p]:
                db = p
    Xcap = xf if xf < n0 else n0 - 1
    if L is not None:
        Xcap = min(Xcap, L)

    def nxo(d):
        x = d + 1
        while x < n0:
            if isb[x] and np.isfinite(o[x]) and o[x] > 0:
                return x
            x += 1
        return None
    E9 = {t for t, _ in DV["S09"]}; E27 = {t for t, _ in DV["S27"]}; EM = set(DV["MA"])
    conds = {"X0": E9 | E27, "X1": E9, "X2": E27, "X3": E9 | E27, "X4": E9 | E27, "X5": EM}
    base_px = bp * (1 + gf); base_day = xf if xf < n0 else n0    # 'end' 的日 ＝ n0

    def forced(day):
        return kb is not None and day >= kb
    pbad = ("close", db, c[db]) if db is not None else None
    res = {}; diff = []
    for v, S_ in conds.items():
        d = None
        for t in range(e, Xcap):
            if t >= n0:
                break
            if t in S_:
                d = t; break
        X = nxo(d) if d is not None else None
        if X is not None and X > Xcap:
            X = None
        sale_ok = X is not None and not forced(X)
        trig = int(sale_ok)
        # 部分 (權重, (種類, 日, 價))；'end' 的日 ＝ n0
        bpart = (("close", xf, base_px) if xf < n0 else ("end", n0, base_px))
        bad_any = int((X is not None and forced(X)) or forced(base_day))
        if forced(base_day):
            bpart = pbad
        spart = (("open", X, o[X]) if sale_ok else pbad) if X is not None else None
        if X is None:
            parts = [(1.0, bpart)]
        elif v in ("X0", "X1", "X2", "X5"):
            parts = [(1.0, spart)]
        elif v == "X3":
            parts = [(0.5, spart), (0.5, bpart)]
        else:   # X4
            parts = [(1.0, spart), (0.0, bpart)]
        ks = [2 * n0 if p[0] == "end" else (2 * p[1] if p[0] == "open" else 2 * p[1] + 1) for _, p in parts]
        xpos = parts[int(np.argmax(ks))][1][1]
        g = sum(w * p[2] for w, p in parts) / bp - 1.0
        if not trig and not bad_any:
            xpos, g = xf, gf
        res[v] = (trig, d if d is not None else -1, X if trig else -1, xpos, g)
        rt, rd, rX, rxp, rg = int(r[f"{v}_trig"]), int(r[f"{v}_d"]), int(r[f"{v}_X"]), int(r[f"{v}_xpos"]), float(r[f"{v}_g"])
        if rt != trig or rd != res[v][1] or rX != res[v][2] or rxp != xpos or abs(rg - g) > TOL:
            diff.append((v, (rt, rd, rX, rxp, rg), res[v]))
    return diff


def c1c2(procs, log):
    out = {}
    for wn in ("主", "早年"):
        W = pickle.load(open(os.path.join(AWORK, f"world_{wn}.pkl"), "rb")); cal = W["cal"]; n0 = len(cal); NP = W["NP"]
        EV = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str, "T": str, "first": str}, keep_default_na=False)
        rows = {sn: pd.read_csv(os.path.join(OUT, f"rows_{wn}_{sn}.csv.gz"), dtype={"sid": str}, float_precision="round_trip") for sn in STRS}
        rng = np.random.default_rng(20261017)
        allsid = sorted(set(EV["sid"]) | set().union(*[set(T["sid"]) for T in rows.values()]))
        samp = set(rng.choice(allsid, min(60, len(allsid)), replace=False).tolist())
        RS = {}
        for sn, T in rows.items():
            trg = T[(T["X0_trig"] == 1) | (T["X1_trig"] == 1) | (T["X2_trig"] == 1)]
            rnd = T.sample(n=min(50, len(T)), random_state=20261017)
            RS[sn] = pd.concat([trg, rnd]).drop_duplicates("key")
            samp |= set(RS[sn]["sid"])
        samp = sorted(samp)
        _G["data"] = W["data"]; _G["cal"] = cal
        with Pool(procs) as pool:
            DET = dict(pool.map(c1_job, [(s, W["uni"].get(s, "twse")) for s in samp], chunksize=4))
        # C1
        nd = {"S09": [0, 0], "S27": [0, 0], "MA20連3日": [0, 0]}; ex = []
        for s in samp:
            e_ = EV[EV["sid"] == s]
            for typ, k in (("S09", "S09"), ("S27", "S27"), ("MA20連3日", "MA")):
                ref = set(zip(e_.loc[e_["型態"] == typ, "T"], e_.loc[e_["型態"] == typ, "first"]))
                if k == "MA":
                    mine = {(str(cal[t].date()), "") for t in DET[s]["MA"]}
                else:
                    mine = {(str(cal[t].date()), str(cal[f].date())) for t, f in DET[s][k]}
                nd[typ][0] += len(ref); nd[typ][1] += len(ref ^ mine)
                if ref ^ mine and len(ex) < 5:
                    ex.append((s, typ, sorted(ref - mine)[:3], sorted(mine - ref)[:3]))
        out[f"C1 {wn}"] = {"抽樣股": len(samp), "事件數／不同筆數": nd, "例": ex}
        log(f"[C1 {wn}] {out[f'C1 {wn}']}")
        # C2
        P = E5C.Pop("main" if wn == "主" else "early")
        EX = E5C.early_extra(W) if wn == "早年" else None
        D.DATA = W["data"]
        LBc = {}; nrow = 0; bad_rows = []
        for sn, S_ in RS.items():
            for _, r in S_.iterrows():
                sid = r["sid"]
                if sid not in LBc:
                    LBc[sid] = R.load_bars(sid, W["uni"].get(sid, "twse"), cal)
                bad = E5C.stock_bad(sid, W, P, EX, NP)
                df_ = row_check(r, W, LBc[sid], bad, DET[sid], n0, NP)
                nrow += 1
                if df_:
                    bad_rows.append((sn, r["key"], df_))
        out[f"C2 {wn}"] = {"抽樣列": nrow, "不同列": len(bad_rows), "例": [str(x) for x in bad_rows[:5]]}
        log(f"[C2 {wn}] {out[f'C2 {wn}']}")
    return out


# ═════════ C3 組合 ═════════
def synth(W, T, v, n0, NP):
    cl = dict(W["closes"]); op = dict(W["opens"]); SF = dict(W["SF"]); hm = {}
    for r in T.itertuples(index=False):
        key = r.key; sid = r.sid; hm[key] = sid
        op[key] = W["opens"][sid]
        if sid in W["SF"]:
            SF[key] = W["SF"][sid]
        orig = W["closes"][sid]
        if v == "A":
            cl[key] = orig; continue
        trig = int(getattr(r, f"{v}_trig")); bd = int(getattr(r, f"{v}_bad"))
        if not trig and not bd:
            cl[key] = orig; continue
        if bd:
            raise SystemExit("C3 遇壞根強制列（本查核未寫該路徑）：" + key)
        c = np.asarray(orig, float)
        X = int(getattr(r, f"{v}_X")); px1 = float(getattr(r, f"{v}_px1"))
        S = np.empty(NP)
        for t in range(NP):
            ct = c[t] if t < n0 else c[n0 - 1]
            sale = ct if t <= X - 1 else px1
            S[t] = 0.5 * ct + 0.5 * sale if v == "X3" else sale
        cl[key] = S
    return cl, op, SF, hm


def eng(sn, sig, cl, op, SF, hm, NP, r):
    Hh, N, G = STRS[sn]
    if sn == "營量":
        o = R.simulate_mtm(sig, f"H{Hh}", N, np.random.default_rng(7000 + r), cl, op, NP, return_equity=True, log=[], d_max=None, pick="relvol",
                           queue_days=0, stop_force=SF, held_map=hm)
    else:
        o = R.simulate_mtm(sig, f"H{Hh}", N, np.random.default_rng(1000 + r), cl, op, NP, return_equity=True, stop_force=SF, held_map=hm)
    return np.asarray(o["equity"], float)


def c3_job(a):
    wn, sn, v, r = a
    W = _G["W"][wn]; cl, op, SF, hm, sig = _G["IN"][(wn, sn, v)]
    eq = eng(sn, sig, cl, op, SF, hm, W["NP"], r)
    return a, eq, {sg: wstats(eq[x:y + 1]) for sg in SEGN[wn] for x, y in [W["segp"][sg]]}


def sig_of(W, sn, T, v):
    Hh, N, G = STRS[sn]
    sig = W["SIG"][G]; sig = sig[sig[f"xpos_H{Hh}"] >= 0].copy()
    Ti = T.set_index("key")
    keys = [f"{s}#{int(e)}" for s, e in zip(sig["sid"], sig["entry_pos"])]
    sig[f"xpos_H{Hh}"] = Ti.loc[keys, f"{v}_xpos"].to_numpy(np.int64); sig[f"g_H{Hh}"] = Ti.loc[keys, f"{v}_g"].to_numpy(float)
    sig["sid"] = keys
    return sig


def c3(procs, log):
    EQ = pickle.load(open(os.path.join(WORK, "eq.pkl"), "rb"))
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip").set_index(["世界", "策略", "臂", "r"])
    _G["W"] = {wn: pickle.load(open(os.path.join(AWORK, f"world_{wn}.pkl"), "rb")) for wn in ("主", "早年")}
    _G["IN"] = {}
    res = {"權益不同條數": 0, "年化回落差＞1e−9": 0, "比對條數": 0, "最大差": 0.0}
    for wn in ("主", "早年"):
        W = _G["W"][wn]; n0 = len(W["cal"]); NP = W["NP"]
        for sn in STRS:
            T = pd.read_csv(os.path.join(OUT, f"rows_{wn}_{sn}.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
            for v in VARS:
                cl, op, SF, hm = synth(W, T, v, n0, NP)
                _G["IN"][(wn, sn, v)] = (cl, op, SF, hm, sig_of(W, sn, T, v))
                seeds = [0] if sn == "營量" else (list(range(NSEED)) if v in ("A", "X0") else list(range(min(20, NSEED))))
                with Pool(procs) as pool:
                    rr = pool.map(c3_job, [(wn, sn, v, r) for r in seeds], chunksize=4)
                for (w_, s_, v_, r), eq, met in rr:
                    res["比對條數"] += 1
                    res["權益不同條數"] += int(not np.array_equal(eq, EQ[(w_, s_, v_, r)][0]))
                    for sg, (c_, m_) in met.items():
                        dm = max(abs(c_ - SE.loc[(w_, s_, v_, r), f"{sg}_年化"]), abs(m_ - SE.loc[(w_, s_, v_, r), f"{sg}_回落"]))
                        res["最大差"] = max(res["最大差"], float(dm)); res["年化回落差＞1e−9"] += int(dm > TOL)
                del _G["IN"][(wn, sn, v)]
                log(f"[C3 {wn}·{sn}·{v}] {len(rr)} 條｜累計 {res}")
    return res


# ═════════ C4 隨機日賣 ═════════
def c4_job(a):
    sn, mode, k = a
    W = _G["W"]["主"]; n0 = len(W["cal"]); NP = W["NP"]
    T = _G["T"][sn]; base = _G["BASE"][sn]
    sig = base.copy(); Hh = STRS[sn][0]
    ix = {kk: i for i, kk in enumerate(sig["sid"])}
    xp = sig[f"xpos_H{Hh}"].to_numpy(np.int64).copy(); g = sig[f"g_H{Hh}"].to_numpy(float).copy()
    cl, op, SF, hm = _G["SY"][sn]
    cl = dict(cl)
    seed = _G["RP"]["sel"][(sn, mode)][k]["seed"]
    for key, (xpos, gg) in _G["RP"]["sel"][(sn, mode)][k]["sel"].items():
        X = _G["SX"][(sn, mode, k, key)]
        bp = float(T.loc[key, "bp"]); c = np.asarray(W["closes"][T.loc[key, "sid"]], float); o = np.asarray(W["opens"][T.loc[key, "sid"]], float)
        S = np.array([(c[t] if t < n0 else c[n0 - 1]) if t <= X - 1 else o[X] for t in range(NP)])
        xp[ix[key]] = X; g[ix[key]] = o[X] / bp - 1.0
        cl[key] = S
    sig[f"xpos_H{Hh}"] = xp; sig[f"g_H{Hh}"] = g
    eq = eng(sn, sig, cl, op, SF, hm, NP, seed)
    import hashlib
    return a, hashlib.sha256(eq.tobytes()).hexdigest()[:16], {sg: wstats(eq[x:y + 1]) for sg in SEGN["主"] for x, y in [W["segp"][sg]]}


def c4(procs, log):
    RP = pickle.load(open(os.path.join(WORK, "rand.pkl"), "rb"))
    RD = pd.read_csv(os.path.join(OUT, "rand.csv.gz"), float_precision="round_trip", dtype={"eq_sha": str})
    W = pickle.load(open(os.path.join(AWORK, "world_主.pkl"), "rb")); n0 = len(W["cal"])
    _G["W"] = {"主": W}
    EQ = pickle.load(open(os.path.join(WORK, "eq.pkl"), "rb"))
    out = {"選取規則違反": 0, "選取檢查筆": 0, "重跑次數": 0, "eq_sha 不同": 0, "年化回落差＞1e−9": 0, "最大差": 0.0}
    _G["T"] = {}; _G["BASE"] = {}; _G["SY"] = {}; _G["RP"] = RP
    SX = {}
    for s_, mode, k, key, sid, e, d, X in RP["sales"]:
        SX[(s_, mode, k, key)] = X
    _G["SX"] = SX
    D.DATA = W["data"]
    LBc = {}
    for sn in STRS:
        T = pd.read_csv(os.path.join(OUT, f"rows_主_{sn}.csv.gz"), dtype={"sid": str}, float_precision="round_trip").set_index("key")
        _G["T"][sn] = T
        sig = sig_of(W, sn, T.reset_index(), "A"); _G["BASE"][sn] = sig
        cl, op, SF, hm = synth(W, T.reset_index(), "A", n0, W["NP"]); _G["SY"][sn] = (cl, op, SF, hm)
        x0, y0 = W["segp"]["主窗"]
        for mode in (["r0"] if sn == "營量" else ["配對", "r0"]):
            for k, blk in RP["sel"][(sn, mode)].items():
                seed = blk["seed"]
                # 原策略持股（由正式引擎 A 重跑的 audit 自取）——用 eq.pkl 只有權益 ⇒ 改由 rows＋引擎 audit
                if (sn, seed) not in _G:
                    au = []
                    Hh, N, G = STRS[sn]
                    if sn == "營量":
                        R.simulate_mtm(sig, f"H{Hh}", N, np.random.default_rng(7000 + seed), cl, op, W["NP"], return_equity=True, log=[], d_max=None,
                                       pick="relvol", queue_days=0, stop_force=SF, held_map=hm, audit=au)
                    else:
                        R.simulate_mtm(sig, f"H{Hh}", N, np.random.default_rng(1000 + seed), cl, op, W["NP"], return_equity=True, stop_force=SF,
                                       held_map=hm, audit=au)
                    _G[(sn, seed)] = sorted({a["sid"] for a in au if a["side"] == "buy" and x0 <= a["t"] <= y0})
                held = _G[(sn, seed)]
                tv = T.loc[held]
                need = tv.groupby("買進年")["X0_trig"].sum()
                sel = list(blk["sel"])
                got = T.loc[sel].groupby("買進年").size() if sel else pd.Series(dtype=int)
                for y, nn in need.items():
                    if int(got.get(y, 0)) != int(nn):
                        out["選取規則違反"] += 1
                if not set(sel) <= set(held):
                    out["選取規則違反"] += 1
                for key in sel:
                    out["選取檢查筆"] += 1
                    X = SX.get((sn, mode, k, key))
                    r = T.loc[key]; sid = r["sid"]; e = int(r["e"]); Xcap = int(r["Xcap"])
                    if sid not in LBc:
                        LBc[sid] = R.load_bars(sid, W["uni"].get(sid, "twse"), W["cal"])
                    isb = np.zeros(n0, bool); isb[[int(x) for x in LBc[sid]["idx"] if x < n0]] = True
                    o = np.asarray(W["opens"][sid], float)
                    if X is None or not (e < X <= Xcap) or not (isb[X] and np.isfinite(o[X]) and o[X] > 0):
                        out["選取規則違反"] += 1
        log(f"[C4 選取 {sn}] {out}")
    jobs = [(sn, mode, k) for sn in STRS for mode in (["r0"] if sn == "營量" else ["配對", "r0"]) for k in range(NREP)]
    with Pool(procs) as pool:
        rr = pool.map(c4_job, jobs, chunksize=2)
    RDi = RD.set_index(["策略", "模式", "k"])
    for (sn, mode, k), sh, met in rr:
        out["重跑次數"] += 1
        out["eq_sha 不同"] += int(sh != RDi.loc[(sn, mode, k), "eq_sha"])
        for sg, (c_, m_) in met.items():
            dm = max(abs(c_ - RDi.loc[(sn, mode, k), f"{sg}_年化"]), abs(m_ - RDi.loc[(sn, mode, k), f"{sg}_回落"]))
            out["最大差"] = max(out["最大差"], float(dm)); out["年化回落差＞1e−9"] += int(dm > TOL)
    log(f"[C4] {out}")
    return out


# ═════════ C5 主表、判定、p ═════════
def c5(log):
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
    MT = pd.read_csv(os.path.join(OUT, "BearExit_main.csv"), float_precision="round_trip")
    J = json.load(open(os.path.join(OUT, "BearExit.json"), encoding="utf-8"))
    DG = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
    RD = pd.read_csv(os.path.join(OUT, "rand.csv.gz"), float_precision="round_trip")
    out = {"主表格數": 0, "主表不同": 0, "判定不同": 0, "p 不同": 0}
    for _, m in MT.iterrows():
        wn = "早年" if m["段"] == "早年" else "主"
        A = SE[(SE["世界"] == wn) & (SE["策略"] == m["策略"]) & (SE["臂"] == "A")]
        V = SE[(SE["世界"] == wn) & (SE["策略"] == m["策略"]) & (SE["臂"] == m["臂"])]
        ca, ma = V[f"{m['段']}_年化"].median(), V[f"{m['段']}_回落"].median()
        co, mo = A[f"{m['段']}_年化"].median(), A[f"{m['段']}_回落"].median()
        out["主表格數"] += 1
        bad = max(abs(ca - m["臂_年化"]), abs(ma - m["臂_回落"]), abs(co - m["原_年化"]), abs(mo - m["原_回落"])) > 1e-9
        if m["臂"] != "A":
            nw = bool(ca >= co and rat(ca, ma) >= rat(co, mo))
            bad = bad or (str(nw) != str(m["不降（年化與比值）"]))
        out["主表不同"] += int(bad)
    for sn in STRS:
        g = MT[(MT["策略"] == sn) & (MT["臂"] == "X0")].set_index("段")
        okx, okc = bool(g.loc["探索", "不降（年化與比值）"]), bool(g.loc["確認", "不降（年化與比值）"])
        lit = "有效" if okx and okc else ("方向不一致" if okx != okc else "無效")
        n = float(np.median(SE[(SE["世界"] == "主") & (SE["策略"] == sn) & (SE["臂"] == "X0")]["主窗_觸發筆"]))
        dg = DG["格"][f"{sn}·X0"]["退化"]
        concl = "樣本不足、測不出" if n < 30 else ("退化、不判" if dg else lit)
        out["判定不同"] += int(concl != J["判定"][sn]["結論"] or lit != J["判定"][sn]["登錄字面結果（不看觸發數與退化）"])
        A = SE[(SE["世界"] == "主") & (SE["策略"] == sn) & (SE["臂"] == "A")].set_index("r")
        X = SE[(SE["世界"] == "主") & (SE["策略"] == sn) & (SE["臂"] == "X0")].set_index("r")
        for mode in (["r0"] if sn == "營量" else ["配對", "r0"]):
            g = RD[(RD["策略"] == sn) & (RD["模式"] == mode)]
            for sg in SEGN["主"]:
                dr = g[f"{sg}_年化"].to_numpy() - A.loc[g["seed"], f"{sg}_年化"].to_numpy()
                xc = (X.loc[0, f"{sg}_年化"] - A.loc[0, f"{sg}_年化"]) if mode == "r0" else float(np.median(X[f"{sg}_年化"] - A[f"{sg}_年化"]))
                p = float(np.mean(dr >= xc))
                out["p 不同"] += int(abs(p - J["隨機日賣"][f"{sn}·{mode}"][sg]["p 年化（隨機 ≥ X0）"]) > 1e-12)
    log(f"[C5] {out}")
    return out


# ═════════ C6 大盤版 ═════════
def c6(log):
    MK = pd.read_csv(os.path.join(OUT, "BearExit_market.csv"), float_precision="round_trip")
    tx = pd.read_csv(TAIEX, dtype={"date": str}); tx["date"] = pd.to_datetime(tx["date"]); tx = tx.drop_duplicates("date").set_index("date")
    out = {"比對格": 0, "差＞1e−9": 0, "最大差": 0.0}
    for wn in ("主", "早年"):
        W = pickle.load(open(os.path.join(AWORK, f"world_{wn}.pkl"), "rb")); cal = W["cal"]; n0 = len(cal)
        D.DATA = W["data"]
        df = D.load_stock("0050", "twse", cal).df
        o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
        ok = np.isfinite(c); cf = pd.Series(c).ffill().to_numpy(float); t0 = int(np.flatnonzero(ok)[0])
        okop = ok & np.isfinite(o) & (o > 0)
        t_ = tx.reindex(cal); tc = t_["close"].to_numpy(float); tv = t_["volume_shares"].to_numpy(float); tok = np.isfinite(tc)
        d50 = ind_detect(h, l, c, v)
        tb = np.flatnonzero(tok)
        tx27 = [int(tb[t]) for t, _ in s27(tc[tb], tv[tb])]
        tx09 = [int(tb[t]) for t, _ in s09(tc[tb], tc[tb], tc[tb])]
        spec = {"M1 加權（只V型；下降三角缺高低價）": (tx27, [], tc, tok), "M1替代 加權（下降三角以收盤代高低，⛔非逐字）": (tx27, tx09, tc, tok),
                "M2 0050本身": ([t for t, _ in d50["S27"]], [t for t, _ in d50["S09"]], c, ok)}
        for nm, (E27, E09, sc, sok) in spec.items():
            allT = sorted(set(E27) | set(E09))
            for rd, lab in (("前收", ""), ("T收", "｜另一讀法 ref＝T收盤")):
                if rd == "T收" and not E27:
                    continue
                sb = np.flatnonzero(sok)
                refs = {}
                for T in allT:
                    j = int(np.searchsorted(sb, T)) - 1
                    refs[T] = sc[T] if (rd == "T收" and T in set(E27)) else (sc[sb[j]] if j >= 0 else np.nan)
                eq = np.full(n0, np.nan); sh = 1.0 / cf[t0]; cash = 0.0; inn = True; ps = pb = None; ref = None; sold = None

                def nxt(t):
                    x = t + 1
                    while x < n0:
                        if okop[x]:
                            return x
                        x += 1
                    return None
                for t in range(t0, n0):
                    if ps is not None and t == ps:
                        cash = sh * o[t] * (1 - CS); sh = 0.0; inn = False; ps = None; sold = t
                    elif pb is not None and t == pb:
                        sh = cash * (1 - CB) / o[t]; cash = 0.0; inn = True; pb = None
                    eq[t] = sh * cf[t] + cash
                    if inn and ps is None and t > t0 and t in refs:
                        x = nxt(t)
                        if x is not None:
                            ps = x; ref = refs[t]
                    elif (not inn) and pb is None and sold is not None and t >= sold and sok[t] and np.isfinite(ref) and sc[t] >= ref:
                        x = nxt(t)
                        if x is not None:
                            pb = x
                for sg, (x, y) in W["segp"].items():
                    c_, m_ = wstats(eq[x:y + 1])
                    rr = MK[(MK["世界"] == wn) & (MK["臂"] == nm + lab) & (MK["段"] == sg)].iloc[0]
                    dm = max(abs(c_ - rr["年化"]), abs(m_ - rr["回落"]))
                    b_ = wstats(cf[x:y + 1] / cf[t0])
                    dm = max(dm, abs(b_[0] - rr["抱0050_年化"]), abs(b_[1] - rr["抱0050_回落"]))
                    out["比對格"] += 1; out["最大差"] = max(out["最大差"], float(dm)); out["差＞1e−9"] += int(dm > TOL)
    log(f"[C6] {out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    T0 = time.time()
    logf = open(os.path.join(OUT, "check.log"), "a", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    res = {"時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M") + "（台北）"}
    res["C7 degeneracy 先寫"] = bool(os.path.getmtime(os.path.join(OUT, "degeneracy.json")) < os.path.getmtime(os.path.join(OUT, "seeds.csv.gz"))
                                   < os.path.getmtime(os.path.join(OUT, "BearExit.json")))
    res["C5"] = c5(log)
    res["C6"] = c6(log)
    res.update(c1c2(a.procs, log))
    res["C4"] = c4(a.procs, log)
    res["C3"] = c3(a.procs, log)
    ok = (res["C7 degeneracy 先寫"] and all(v == 0 for k, v in res["C5"].items() if k != "主表格數") and res["C6"]["差＞1e−9"] == 0
          and all(res[f"C1 {w}"]["事件數／不同筆數"][t][1] == 0 for w in ("主", "早年") for t in ("S09", "S27", "MA20連3日"))
          and all(res[f"C2 {w}"]["不同列"] == 0 for w in ("主", "早年"))
          and res["C4"]["選取規則違反"] == 0 and res["C4"]["eq_sha 不同"] == 0 and res["C4"]["年化回落差＞1e−9"] == 0
          and res["C3"]["權益不同條數"] == 0 and res["C3"]["年化回落差＞1e−9"] == 0)
    res["全部通過"] = bool(ok); res["耗時秒"] = round(time.time() - T0)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 全部通過 {ok}")


if __name__ == "__main__":
    main()
