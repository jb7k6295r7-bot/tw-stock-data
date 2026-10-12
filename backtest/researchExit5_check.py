# -*- coding: utf-8 -*-
"""researchExit5 獨立查核（回測線計算子代理，2026-10-12）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit5_check [--procs 3]

獨立寫法（⛔ 不 import researchExit5、⛔ 不 import researchAddOn）：
 C1 逐列抽樣（每個 世界×策略：隨機 40 列 ＋ 每個判定臂各隨機 10 列已觸發列；random_state 20261012）逐日迴圈從頭重算：
    有效 K 棒（load_bars traded）、壞根（bad_{main,early}.pkl ＋ 早年 R8／reduce_v2 自己讀檔、快取沒有的股 BARR.bad_part＋adj）、
    ATR（逐根 TR 迴圈）、MA5（逐根）、R1 母體（每日 lexsort 自取前 ⌈X×檔數⌉、X 自算）與 q99(h,d)／q2(d)（逐日抽母體向量 np.percentile）、
    營收（逐檔讀 revenue_hist、自算可得日 bisect、年增、24 月新高）⇒ 各臂 觸發、訊號日 d、賣出日 X、引擎 xpos、g、經濟 xe／ge 與 rows 表比（g 差 ≤ 1e−9）
 C2 組合層：由 rows 表的 xpos／g／X／px1／X2 自己組合成收盤（逐日迴圈）與鍵 ⇒ 跑正式引擎 ⇒ 權益與 ~/exit5work/eq.pkl 比、
    自寫年化／回落（[x, y] 段、(y−x+1)/245 年、逐日最高）與 seeds.csv.gz 比（差 ≤ 1e−9）：營量全部臂；營飆 判定臂與原策略 200 顆、描述臂前 20 顆
 C3 主表與判定：由 seeds.csv.gz 自算中位、比值、變好、逐顆變好比例 ⇒ 與 Exit5_main.csv、Exit5.json 判定比
 C4 degeneracy.json 寫入時間早於 seeds.csv.gz、Exit5.json 的修改時間
"""
from __future__ import annotations

import argparse
import bisect
import glob
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402

OUT = "backtest/resultsExit5"
WORK = os.path.expanduser("~/exit5work")
NSEED = 200
if os.environ.get("EX5_QUICK"):                                  # 煙霧測試（不是交件）
    NSEED, OUT, WORK = 3, "/tmp/exit5_quick", "/tmp/exit5_quick/work"
AWORK = os.path.expanduser("~/addonwork")
V2EXT = os.path.expanduser("~/earlydata/950ad26e12/reduce_ext_b45c9e94dc")
TOL = 1e-9
STRS = {"營量": (60, 20, False), "營飆": (120, 10, True)}
JUD = ["E1a", "E1b", "E2", "E3", "E4", "E5"]
CHK = JUD + ["D1_5", "D1_10", "D2", "D3", "D4", "D5", "N1a", "N2", "N3"]
VARS = ["A"] + JUD + ["D1_5", "D1_10", "D2", "D3", "D4", "D5", "N1a", "N1b", "N2", "N3"]
HALF = {"E4", "E5", "D2", "D4", "D5"}
SEGN = {"主": ["探索", "確認", "主窗"], "早年": ["早年"]}
COST = 0.00585
_G: dict = {}


def wstats(nav):
    yrs = len(nav) / 245
    if len(nav) < 245:
        return np.nan, np.nan
    c = (nav[-1] / nav[0]) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(nav)
    return c, float(((nav - pk) / pk).min())


# ═════════ 母體 ═════════
class Pop:
    def __init__(self, part, X=None):
        Z = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{part}.pkl"), "rb"))
        self.sids = Z["sids"]; self.ix = {s: i for i, s in enumerate(self.sids)}
        self.C, self.BAR, self.A20, self.PV = Z["c"], Z["bar"], Z["a20"], Z["pv"]
        S, n = self.C.shape; self.n = n
        self.MKT = self.BAR & self.PV & np.isfinite(self.A20)
        B = pickle.load(open(os.path.expanduser(f"~/crashwork/bad_{part}.pkl"), "rb"))
        self.BAD = np.zeros((S, n), bool)
        for i, s in enumerate(self.sids):
            for arr in B[s]:
                self.BAD[i, np.asarray(arr, int)] = True
        self.X = X; self._r1 = {}

    def set_X(self, cal):
        d = int(np.flatnonzero(cal == pd.Timestamp("2016-01-04"))[0])
        m = self.MKT[:, d]
        self.X = (m & (self.A20[:, d] >= 5e7)).sum() / m.sum()

    def r1(self, d):
        if d not in self._r1:
            ii = np.flatnonzero(self.MKT[:, d])
            o = np.lexsort((ii, -self.A20[ii, d]))
            k = int(np.ceil(self.X * len(ii)))
            self._r1[d] = set(ii[o[:k]].tolist())
        return self._r1[d]

    def q(self, h, d, pct):
        mem = np.array(sorted(self.r1(d)), int)
        out = []
        for i in mem:
            if not self.BAR[i, d] or not np.isfinite(self.C[i, d - h]):
                continue
            if self.BAD[i, d - h + 1:d + 1].any():
                continue
            out.append(self.C[i, d] / self.C[i, d - h] - 1.0)
        if len(out) < 20:
            return np.nan
        return float(np.percentile(np.array(out), pct))


def early_extra(W):
    cal = W["cal"]; X = {}

    def add(sids, dates):
        for s, d in zip(sids, dates):
            s = str(s).strip(); d = str(d).strip()
            if not d:
                continue
            k = int(cal.searchsorted(pd.Timestamp(d)))
            if k < len(cal):
                X.setdefault(s, set()).add(k)
    EV = W["EV"]; add(EV["stock_id"], EV["e"])
    t = pd.read_csv(os.path.join(V2EXT, "twse_reduce_detected_2004_2010.csv"), dtype=str, keep_default_na=False); add(t["stock_id"], t["date"])
    o = pd.read_csv(os.path.join(V2EXT, "otc_reduce_detected_2007_2012.csv"), dtype=str, keep_default_na=False)
    o = o[(o["shares_down"].str.strip() == "1") & (o["exright_in_gap"].str.strip() == "0")]; add(o["stock_id"], o["resume_day"])
    u = pd.read_csv(os.path.join(V2EXT, "twse_jump_unexplained_2004_2010.csv"), dtype=str, keep_default_na=False); add(u["stock_id"], u["date"])
    return X


def stock_bad(sid, W, P, EX, NP):
    if sid in P.ix:
        b = P.BAD[P.ix[sid]].copy()
        if EX:
            for k in EX.get(sid, ()):
                b[k] = True
    else:
        from backtest import researchBARR as BARR
        b = BARR.bad_part(sid, W["data"], W["cal"]).copy()
        adj = D.load_adj(sid) if os.path.exists(os.path.join(W["data"], "stocks", f"{sid}.csv")) else None
        if adj is not None and len(adj) and "event" in adj:
            for d, e in zip(adj["date"], adj["event"].astype(str)):
                if e in ("reduce", "parvalue"):
                    k = int(W["cal"].searchsorted(d))
                    if k < len(W["cal"]):
                        b[k] = True
        if EX:
            for k in EX.get(sid, ()):
                b[k] = True
    return np.r_[b, np.zeros(NP - len(b), bool)]


# ═════════ 營收 ═════════
def revenue(data):
    fs = sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv")))
    per = set(); R_ = {}
    for f in fs:
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
        a_ = pd.to_numeric(x["當月營收"], errors="coerce").to_numpy(float); b_ = pd.to_numeric(x["去年當月營收"], errors="coerce").to_numpy(float)
        for s, p, a, b in zip(x["stock_id"], x["period"], a_, b_):
            per.add(p)
            R_[(s, p)] = (float(a), float(b))
    return sorted(per), R_


def rev_list(sid, PER, RV, dates):
    out = []
    for k, p in enumerate(PER):
        v = RV.get((sid, p))
        if v is None or not np.isfinite(v[0]):
            continue
        y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(year=y2, month=m2, day=10 if p <= "2025-12" else 15)
        A = bisect.bisect_right(dates, cut)
        if A >= len(dates):
            continue
        yoy = v[0] / v[1] - 1 if (np.isfinite(v[1]) and v[1] > 0) else np.nan
        hist = []
        for j in range(max(0, k - 24), k):
            w = RV.get((sid, PER[j]))
            hist.append(w[0] if w is not None else np.nan)
        hist = np.array(hist, float)
        hi = bool(v[0] >= hist.max()) if (len(hist) == 24 and np.isfinite(hist).all()) else None
        out.append((A, yoy, hi))
    out.sort(key=lambda z: z[0])
    return out


# ═════════ 逐列迴圈 ═════════
def row_check(r, W, LB, bad, P, REV, n0, NP):
    sid = r["sid"]; e = int(r["e"]); xf = int(r["xf"]); gf = float(r["gf"]); L = int(r["L"]); L = None if L < 0 else L
    c = np.asarray(W["closes"][sid], float); o = np.asarray(W["opens"][sid], float)
    idx = [int(x) for x in LB["idx"] if x < n0]; isb = np.zeros(n0, bool); isb[idx] = True
    bp = o[e] if (np.isfinite(o[e]) and o[e] > 0) else c[e]

    def nxo(d):
        x = d + 1
        while x < n0:
            if isb[x] and np.isfinite(o[x]) and o[x] > 0:
                return x
            x += 1
        return None
    kb = None
    for p in range(e + 1, NP):
        if bad[p]:
            kb = p; break
    if xf < n0:
        Xcap = xf
    else:
        Xcap = n0 - 1
    if L is not None:
        Xcap = min(Xcap, L)
    XcapN = n0 - 1 if L is None else min(n0 - 1, L)
    # ATR
    pos = int(r["e"]) - 1
    k = list(LB["idx"]).index(int(W["SIG_POS"][(sid, e)]))
    trs = []
    for j in range(k - 19, k + 1):
        hj, lj, cp = LB["h"][j], LB["l"][j], LB["c"][j - 1]
        trs.append(max(hj, cp) - min(lj, cp))
    atr = sum(trs) / 20.0
    # 逐日序列
    ma5 = {}; below = {}
    for t, d in enumerate(idx):
        if t >= 4:
            ma5[d] = sum(c[idx[t - j]] for j in range(5)) / 5.0
            below[d] = c[d] < ma5[d]
    prev = {idx[t]: idx[t - 1] for t in range(1, len(idx))}

    def scan(cond, lo, hi):
        """⇒ 第一個成立日 d（lo..hi）及其 X（沒有可賣開盤 ⇒ None）。"""
        for d in range(lo, hi + 1):
            if d >= n0:
                break
            if cond(d):
                return d
        return None
    M = {}; m_ = -np.inf
    for d in range(e, n0):
        if isb[d]:
            m_ = max(m_, c[d])
        M[d] = m_
    nbars = {}; cnt = 0
    for d in range(e, n0):
        cnt += int(isb[d]); nbars[d] = cnt
    conds = {
        "E1a": lambda d: isb[d] and c[d] <= M[d] - 2 * atr, "E1b": lambda d: isb[d] and c[d] <= M[d] - 4 * atr,
        "D1_5": lambda d: isb[d] and c[d] <= 0.95 * M[d], "D1_10": lambda d: isb[d] and c[d] <= 0.90 * M[d],
        "E2": lambda d: isb[d] and nbars[d] >= 6 and below.get(d, False),
        "D4": lambda d: isb[d] and c[d] / bp - 1.0 >= 1.0,
        "D5": lambda d: d >= e + 1 and isb[d] and not bad[d] and (c[d] / c[d - 1] - 1.0) < -0.05,
    }

    def c4(d):
        if d < e + 9 or not isb[d] or (kb is not None and kb <= d):
            return False
        q = P.q(d - e + 1, d, 99.0) if d < P.n else np.nan
        return bool(np.isfinite(q) and c[d] / bp - 1.0 >= q)

    def c5(d):
        if d < e + 1 or not isb[d] or bad[d]:
            return False
        q = P.q(1, d, 2.0) if d < P.n else np.nan
        rr = c[d] / c[d - 1] - 1.0
        return bool(np.isfinite(q) and np.isfinite(rr) and rr <= q and rr < 0)
    conds["E4"] = c4; conds["E5"] = c5
    pf = ("close", xf, bp * (1 + gf)) if xf < n0 else ("end", n0, bp * (1 + gf))
    pend = ("end", n0, c[n0 - 1])
    order = lambda p: 2 * p[1] + (1 if p[0] == "close" else 0) if p[0] != "end" else 2 * n0
    db = None
    if kb is not None:
        db = max([d for d in idx if e <= d < kb], default=e)

    def badfix(p):
        day = p[1] if p[0] != "end" else n0
        if kb is not None and day >= kb:
            return ("close", db, c[db]), True
        return p, False

    def sale(d, cap):
        if d is None:
            return None
        X = nxo(d)
        return X if (X is not None and X <= cap) else None
    res = {}
    for v in CHK:
        nmax = v.startswith("N")
        base = pend if nmax else pf; cap = XcapN if nmax else Xcap
        cv = {"N1a": "E1a", "N2": "E2", "N3": "E3", "D2": "E2"}.get(v, v)
        if cv in ("E3", "D3"):
            d = None
            for A, yoy, hi in REV:
                if A < e or A > cap - 1:
                    continue
                if (cv == "E3" and np.isfinite(yoy) and yoy <= 0) or (cv == "D3" and hi is False):
                    d = A; break
        else:
            d = scan(conds[cv], e, cap - 1)
        X = sale(d, cap)
        parts = []
        if v in HALF:
            if X is not None and order(("open", X)) < order(base):
                parts = [(0.5, ("open", X, o[X])), (0.5, base)]
                if v == "D2":
                    d2 = None
                    for dd in range(d + 1, cap):
                        if isb[dd] and below.get(dd, False) and dd in prev and not below.get(prev[dd], False):
                            d2 = dd; break
                    X2 = sale(d2, cap)
                    if X2 is not None and order(("open", X2)) < order(base):
                        parts[1] = (0.5, ("open", X2, o[X2]))
            else:
                X = None; parts = [(0.5, base), (0.5, base)]
        else:
            if X is not None and order(("open", X)) < order(base):
                parts = [(1.0, ("open", X, o[X]))]
            else:
                X = None; parts = [(1.0, base)]
        fx = [(w, badfix(p)) for w, p in parts]
        isbad = any(f[1] for _, f in fx); parts = [(w, f[0]) for w, f in fx]
        trig = int(X is not None and any(p[0] == "open" and p[1] == X for _, p in parts))
        fin = max(parts, key=lambda wp: order(wp[1]))[1]
        if (not trig) and (not isbad) and not nmax:
            xp, g = xf, gf
        else:
            xp = fin[1]; g = sum(w * p[2] for w, p in parts) / bp - 1.0
        # 經濟口徑（停止交易）
        xe, ge = xp, g
        if L is not None and xp > L + 1:
            val = 0.0
            for w, p in parts:
                dl = p[1] - 1 if p[0] == "open" else (p[1] if p[0] == "close" else n0 - 1)
                val += w * (c[L] if L <= dl else p[2])
            xe, ge = L + 1, val / bp - 1.0
        res[v] = {"trig": trig, "d": -1 if d is None else d, "X": X if trig else -1, "xpos": xp, "g": g, "xe": xe, "ge": ge, "bad": int(isbad)}
    return res


def c1(log):
    out = {}; bad_rows = []
    for wn in ("主", "早年"):
        W = pickle.load(open(os.path.join(AWORK, f"world_{wn}.pkl"), "rb")); cal = W["cal"]; n0 = len(cal); NP = W["NP"]
        P = Pop("main" if wn == "主" else "early", _G.get("X"))
        if P.X is None:
            P.set_X(cal); _G["X"] = P.X
        EX = early_extra(W) if wn == "早年" else None
        D.DATA = W["data"]
        PER, RV = revenue(W["data"]); dates = list(cal)
        W["SIG_POS"] = {}
        for G in (False, True):
            for s, e, p in zip(W["SIG"][G]["sid"], W["SIG"][G]["entry_pos"], W["SIG"][G]["pos"]):
                W["SIG_POS"][(s, int(e))] = int(p)
        for sn in STRS:
            T = pd.read_csv(os.path.join(OUT, f"rows_{wn}_{sn}.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
            smp = [T.sample(40, random_state=20261012)]
            for v in JUD:
                t_ = T[T[f"{v}_trig"] == 1]
                if len(t_):
                    smp.append(t_.sample(min(10, len(t_)), random_state=20261012))
            S = pd.concat(smp).drop_duplicates("key")
            nd = 0; nchk = 0; LBc = {}
            for _, r in S.iterrows():
                sid = r["sid"]
                if sid not in LBc:
                    LBc[sid] = R.load_bars(sid, W["uni"].get(sid, "twse"), cal)
                bad = stock_bad(sid, W, P, EX, NP)
                REV = rev_list(sid, PER, RV, dates)
                res = row_check(r, W, LBc[sid], bad, P, REV, n0, NP)
                for v, z in res.items():
                    nchk += 1
                    why = []
                    for k in ("trig", "d", "X", "xpos", "xe", "bad"):
                        if int(z[k]) != int(r[f"{v}_{k}"]):
                            why.append(f"{k} {z[k]}≠{r[f'{v}_{k}']}")
                    for k in ("g", "ge"):
                        if abs(z[k] - float(r[f"{v}_{k}"])) > TOL:
                            why.append(f"{k} {z[k]}≠{r[f'{v}_{k}']}")
                    if why:
                        nd += 1; bad_rows.append(f"{wn}·{sn} {r['key']} {v}: {'; '.join(why)}")
            out[f"{wn}·{sn}"] = {"抽樣列": int(len(S)), "比對（列×臂）": nchk, "不同": nd}
            log(f"[C1 {wn}·{sn}] {out[f'{wn}·{sn}']}")
    out["例"] = bad_rows[:20]
    return out


# ═════════ C2 ═════════
def synth(W, T, v, n0, NP):
    H = None
    cl = dict(W["closes"]); op = dict(W["opens"]); SF = dict(W["SF"]); hm = {}
    for r in T.itertuples(index=False):
        key = r.key; sid = r.sid; hm[key] = sid
        op[key] = W["opens"][sid]
        if sid in W["SF"]:
            SF[key] = W["SF"][sid]
        orig = W["closes"][sid]
        if v == "A":
            cl[key] = orig; continue
        trig = int(getattr(r, f"{v}_trig")); xp = int(getattr(r, f"{v}_xpos")); bd = int(getattr(r, f"{v}_bad"))
        if not trig and not bd and not v.startswith("N"):
            cl[key] = orig; continue
        c = np.asarray(orig, float)
        S = np.empty(NP)
        X = int(getattr(r, f"{v}_X")); px1 = float(getattr(r, f"{v}_px1"))
        for t in range(NP):
            ct = c[t] if t < n0 else c[n0 - 1]
            if v in HALF and trig and t >= X:
                S[t] = 0.5 * ct + 0.5 * px1
            else:
                S[t] = ct
        cl[key] = S
    return cl, op, SF, hm


def c2_job(a):
    wn, sn, v, r = a
    W = _G["W"][wn]; cl, op, SF, hm, sig = _G["IN"][(wn, sn, v)]
    Hh, N, G = STRS[sn]
    if sn == "營量":
        o = R.simulate_mtm(sig, f"H{Hh}", N, np.random.default_rng(7000 + r), cl, op, W["NP"], return_equity=True, log=[], d_max=None, pick="relvol",
                           queue_days=0, stop_force=SF, held_map=hm)
    else:
        o = R.simulate_mtm(sig, f"H{Hh}", N, np.random.default_rng(1000 + r), cl, op, W["NP"], return_equity=True, stop_force=SF, held_map=hm)
    eq = np.asarray(o["equity"], float)
    met = {}
    for sg in SEGN[wn]:
        x, y = W["segp"][sg]
        met[sg] = wstats(eq[x:y + 1])
    return a, eq, met


def c2(procs, log):
    EQ = pickle.load(open(os.path.join(WORK, "eq.pkl"), "rb"))
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
    SEi = SE.set_index(["世界", "策略", "臂", "r"])
    _G["W"] = {wn: pickle.load(open(os.path.join(AWORK, f"world_{wn}.pkl"), "rb")) for wn in ("主", "早年")}
    _G["IN"] = {}
    res_all = {"權益不同條數": 0, "年化回落差＞1e−9": 0, "比對條數": 0, "最大差": 0.0}
    for wn in ("主", "早年"):
        W = _G["W"][wn]; n0 = len(W["cal"]); NP = W["NP"]
        for sn, (Hh, N, G) in STRS.items():
            T = pd.read_csv(os.path.join(OUT, f"rows_{wn}_{sn}.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
            sig = W["SIG"][G]; sig = sig[sig[f"xpos_H{Hh}"] >= 0].copy()
            Ti = T.set_index("key")
            keys = [f"{s}#{int(e)}" for s, e in zip(sig["sid"], sig["entry_pos"])]
            for v in VARS:
                s2 = sig.copy()
                s2[f"xpos_H{Hh}"] = Ti.loc[keys, f"{v}_xpos"].to_numpy(np.int64); s2[f"g_H{Hh}"] = Ti.loc[keys, f"{v}_g"].to_numpy(float)
                s2["sid"] = keys
                cl, op, SF, hm = synth(W, T, v, n0, NP)
                _G["IN"][(wn, sn, v)] = (cl, op, SF, hm, s2)
                seeds = [0] if sn == "營量" else (list(range(NSEED)) if v in ["A"] + JUD else list(range(min(20, NSEED))))
                with Pool(procs) as pool:
                    rr = pool.map(c2_job, [(wn, sn, v, r) for r in seeds], chunksize=4)
                for (w_, s_, v_, r), eq, met in rr:
                    res_all["比對條數"] += 1
                    e0 = EQ[(w_, s_, v_, r)][0]
                    if not np.array_equal(eq, e0):
                        res_all["權益不同條數"] += 1
                    for sg, (c_, m_) in met.items():
                        rc, rm = SEi.loc[(w_, s_, v_, r), f"{sg}_年化"], SEi.loc[(w_, s_, v_, r), f"{sg}_回落"]
                        dmax = max(abs(c_ - rc), abs(m_ - rm))
                        res_all["最大差"] = max(res_all["最大差"], float(dmax))
                        res_all["年化回落差＞1e−9"] += int(dmax > TOL)
                del _G["IN"][(wn, sn, v)]
                log(f"[C2 {wn}·{sn}·{v}] {len(rr)} 條｜累計 {res_all}")
    return res_all


def c3(log):
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
    MT = pd.read_csv(os.path.join(OUT, "Exit5_main.csv"), float_precision="round_trip")
    S = json.load(open(os.path.join(OUT, "Exit5.json"), encoding="utf-8"))
    DG = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
    nd = 0; n = 0; ex = []
    rat = lambda c, m: c / abs(m)
    MED = {}
    for (wn, sn, v), g in SE.groupby(["世界", "策略", "臂"]):
        for sg in SEGN[wn]:
            MED[(sn, v, sg)] = (float(np.median(g[f"{sg}_年化"])), float(np.median(g[f"{sg}_回落"])))
    for r in MT.itertuples(index=False):
        ca, ma = MED[(r.策略, r.臂, r.段)]; co, mo = MED[(r.策略, "A", r.段)]
        n += 1
        bad = abs(ca - r.臂_年化) > TOL or abs(ma - r.臂_回落) > TOL or abs(co - r.原_年化) > TOL
        if r.臂 != "A":
            bt = ca > co and rat(ca, ma) >= rat(co, mo)
            bad = bad or (bool(bt) != (str(r.變好) == "True"))
        if bad:
            nd += 1; ex.append(f"{r.策略}·{r.臂}·{r.段}")
    # 判定
    vd = 0
    for sn in ("營量", "營飆"):
        for mth, cells in {"法1": ["E1a", "E1b"], "法2": ["E2"], "法3": ["E3"], "法4": ["E4"], "法5": ["E5"]}.items():
            nde = [c for c in cells if not DG["格"][f"{sn}·{c}"]["退化"]]
            pool_ = nde if nde else cells
            pk = sorted(pool_, key=lambda c: (-rat(*MED[(sn, c, "探索")]), -MED[(sn, c, "探索")][0], cells.index(c)))[0]
            ok = {}
            for sg in ("探索", "確認"):
                ca, ma = MED[(sn, pk, sg)]; co, mo = MED[(sn, "A", sg)]
                ok[sg] = ca > co and rat(ca, ma) >= rat(co, mo)
            dg = DG["格"][f"{sn}·{pk}"]["退化"]
            con = "退化、不判" if dg else ("變好（暫定）" if ok["探索"] and ok["確認"] else ("沒有變好（探索段就沒變好）" if not ok["探索"] else "沒有變好（確認段沒變好）"))
            V = S["判定"][f"{sn}·{mth}"]
            if V["挑中格"] != pk or V["結論"] != con:
                vd += 1; ex.append(f"判定 {sn}·{mth}: {V['挑中格']}/{V['結論']} vs {pk}/{con}")
    out = {"主表列": n, "主表不同": nd, "判定不同": vd, "例": ex[:10]}
    log(f"[C3] {out}")
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    T0 = time.time()
    log = lambda m: print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)
    res = {"時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M") + "（台北）"}
    dg = os.path.getmtime(os.path.join(OUT, "degeneracy.json"))
    res["C4 degeneracy.json 早於 seeds.csv.gz、Exit5.json"] = bool(dg < os.path.getmtime(os.path.join(OUT, "seeds.csv.gz")) and dg < os.path.getmtime(os.path.join(OUT, "Exit5.json")))
    res["C3"] = c3(log)
    res["C1"] = c1(log)
    if os.environ.get("EX5_NOC2"):                                   # 只供除錯（交件跑 ⛔ 不設）
        res["C2"] = {"權益不同條數": -1, "年化回落差＞1e−9": -1}
    else:
        res["C2"] = c2(a.procs, log)
    ok = (res["C4 degeneracy.json 早於 seeds.csv.gz、Exit5.json"] and res["C3"]["主表不同"] == 0 and res["C3"]["判定不同"] == 0
          and all(v["不同"] == 0 for k, v in res["C1"].items() if k != "例") and res["C2"]["權益不同條數"] == 0 and res["C2"]["年化回落差＞1e−9"] == 0)
    res["通過"] = bool(ok); res["耗時秒"] = round(time.time() - T0)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] {json.dumps(res, ensure_ascii=False, default=str)[:3000]}")


if __name__ == "__main__":
    main()
