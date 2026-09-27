# -*- coding: utf-8 -*-
"""PREREG低頻擇時 獨立查核（⛔ 不 import researchLowFreq；只讀它的輸出檔對數）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchLowFreq_check.py

另走一條路重算（共用的只有 researchTri.load_all 讀資料）：
 ① 合成正2、0050 指標（均線自寫 fsum、250 高與 60 日新高自寫迴圈、月底自寫）
 ② 44 格權重自寫 ⇒ 探索＋早年換手次數 ＝ pre_degenerate.csv 逐格
 ③ 自寫引擎（開盤成交、換手 × 0.385%、窗首建倉付成本、缺開盤延後）⇒ 挑中 3 格 × 3 段、一直抱正2、六四 v1 的年化／回落 ＝ cells.csv／summary.json（容差 1e-9）
 ④ 挑格（探索段年化最高、同分換手少）與讀法（兩段多賺 ⇒ 穩…）、2008 型最慘與 −70% 標記 ＝ summary.json
"""
from __future__ import annotations
import json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchTri as T

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsLowFreq")
C_ = 0.00385


def fsum_ma(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = math.fsum(x[i - n + 1:i + 1]) / n
    return out


def my_engine(W, i0, i1, O, C, R=None):
    n = i1 - i0 + 1; u = np.zeros(2); cash = 1.0; eq = []; held = None; pend = True
    for j in range(n):
        t = i0 + j; w = W[t]
        if j > 0 and ((R is not None and R[j]) or held is None or np.any(w != held)):
            pend = True
        if pend:
            o = np.array([O[0][t], O[1][t]])
            need = (u > 0) | (w > 0)
            if np.isfinite(o[need]).all():
                hv = np.array([u[k] * o[k] if u[k] > 0 else 0.0 for k in range(2)])
                V = hv.sum() + cash
                tr = 0.5 * (np.abs(w * V - hv).sum() + abs((1 - w.sum()) * V - cash))
                V -= tr * C_
                u = np.array([w[k] * V / o[k] if w[k] > 0 else 0.0 for k in range(2)]); cash = (1 - w.sum()) * V
                held = w.copy(); pend = False
        eq.append(sum(u[k] * C[k][t] for k in range(2) if u[k] > 0) + cash)
    eq = np.array(eq)
    cagr = eq[-1] ** (245 / n) - 1
    p = np.r_[1.0, eq]; mdd = float(np.min(p / np.maximum.accumulate(p) - 1))
    return float(cagr), mdd, eq


def main():
    RES = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CE = pd.read_csv(os.path.join(OUT, "cells.csv"), encoding="utf-8")
    PD = pd.read_csv(os.path.join(OUT, "pre_degenerate.csv"), encoding="utf-8")
    G = T.load_all(); cal = list(G["cal"]); N = len(cal); pos = G["pos"]
    o = G["O"]["0050"]; c = G["C"]["0050"]; cf = pd.Series(c).ffill().to_numpy()
    # ① 合成正2
    f0 = int(np.flatnonzero(np.isfinite(c))[0])
    Sc = np.full(N, np.nan); So = np.full(N, np.nan); Sc[f0] = 1.0
    for t in range(f0 + 1, N):
        r_o = o[t] / cf[t - 1] - 1 if np.isfinite(o[t]) else np.nan
        So[t] = Sc[t - 1] * (1 + 2 * r_o) if np.isfinite(r_o) else np.nan
        Sc[t] = Sc[t - 1] * (1 + 2 * (cf[t] / cf[t - 1] - 1) - 0.01 / 245)
    bars = [t for t in range(N) if np.isfinite(c[t])]
    cb = np.array([c[t] for t in bars])
    m200 = fsum_ma(cb, 200)
    hi = np.full(len(cb), np.nan); nh = np.zeros(len(cb), bool); xu = np.zeros(len(cb), bool)
    for k in range(len(cb)):
        if k >= 249:
            hi[k] = max(cb[k - 249:k + 1])
        if k >= 59:
            nh[k] = cb[k] > max(cb[k - 59:k])
        if k >= 1 and np.isfinite(m200[k - 1]) and np.isfinite(m200[k]):
            xu[k] = cb[k - 1] <= m200[k - 1] and cb[k] > m200[k]
    last = {}; j = -1
    idx_of = {t: k for k, t in enumerate(bars)}
    LB = np.zeros(N, int)
    for t in range(N):
        if t in idx_of:
            j = idx_of[t]
        LB[t] = j
    ME = [t for t in range(N - 1) if cal[t][:7] != cal[t + 1][:7]]
    MEs = set(ME); MS = set(t + 1 for t in ME)
    mc = {t: cf[t] for t in ME}

    def mma(t, k):
        i = ME.index(t)
        if i < k - 1:
            return np.nan
        v = [mc[x] for x in ME[i - k + 1:i + 1]]
        return float(np.mean(v)) if all(np.isfinite(v)) else np.nan

    def sig_series(lev, L):
        cc = G["C"][lev] if lev != "SYN" else Sc
        bb = [t for t in range(N) if np.isfinite(cc[t])]
        rr = pd.Series([cc[bb[k]] / cc[bb[k - 1]] - 1 for k in range(1, len(bb))], index=bb[1:])
        sd = rr.rolling(L).std(ddof=1) * math.sqrt(245)
        out = np.full(N, np.nan); cur = np.nan; sdd = sd.to_dict()
        for t in range(N):
            out[t] = cur
            if t in sdd:
                cur = sdd[t]
        return out
    e0, e1, c0, c1 = pos["2015-11-02"], pos["2021-12-30"], pos["2022-01-03"], pos["2026-08-24"]
    E0 = pos[S["早年段起點 E0（讀法 L1）"]]; E1 = pos["2014-12-31"]
    g0 = pos[S["丙狀態機起跑"]]
    SEG = {"探索": (e0, e1, "00631L"), "確認": (c0, c1, "00631L"), "早年": (E0, E1, "SYN")}
    SIG = {L: {"00631L": sig_series("00631L", L), "SYN": sig_series("SYN", L)} for L in (20, 60)}

    def weights(fam, key):
        W = np.full((N, 2), np.nan); p = key.split("_"); st = np.full(N, -1)
        if fam == "甲":
            cur = None
            for t in range(N):
                if cur is not None:
                    W[t], st[t] = cur
                if t in MEs:
                    ma = (m200[LB[t]] if LB[t] >= 0 else np.nan) if p[0] == "D200" else mma(t, int(p[0][1:]))
                    if np.isfinite(ma):
                        on = cf[t] > ma
                        cur = ((0.0, 1.0) if on else ((1.0, 0.0) if p[1] == "a" else (0.0, 0.0)), int(on))
        elif fam == "乙":
            s, L, v = int(p[0][1:]) / 100, int(p[1][1:]), p[2]; cur = None
            for t in range(N):
                if t in MS:
                    sg = SIG[L]["SYN" if t < e0 else "00631L"][t]
                    if np.isfinite(sg) and sg > 0:
                        w = min(1.0, s / sg); cur = ((1 - w, w) if v == "a" else (0.0, w), int(w == 1.0))
                if cur is not None:
                    W[t], st[t] = cur
        else:
            b, x, r, f = p[0], int(p[1][1:]) / 100, p[2], p[3]
            hold = (1.0, 0.0) if b == "A" else (0.0, 1.0); s_ = 1; prev_below = None; nxt = 1
            for t in range(g0, N):
                s_ = nxt; W[t] = hold if s_ == 1 else (0.0, 0.0); st[t] = s_
                isb = t in idx_of
                if (f == "D" and isb) or (f == "M" and t in MEs):
                    k = LB[t]; cc = cf[t]
                    if s_ == 1:
                        if np.isfinite(hi[k]) and cc <= hi[k] * (1 - x):
                            nxt = 0
                    else:
                        if r == "R1":
                            go = isb and nh[idx_of[t]]
                        elif f == "D":
                            go = xu[idx_of[t]]
                        else:
                            go = prev_below is True and np.isfinite(m200[k]) and cc > m200[k]
                        if go:
                            nxt = 1
                    if f == "M":
                        prev_below = bool(np.isfinite(m200[k]) and cc <= m200[k])
        return W, st
    # ②
    bad = []; WW = {}
    for _, r in PD.iterrows():
        W, st = weights(r["件"], r["格"]); WW[(r["件"], r["格"])] = (W, st)
        ch = 0
        for a, b in ((e0, e1), (E0, E1)):
            ch += int(np.sum(np.any(np.abs(W[a + 1:b + 1] - W[a:b]) > 1e-12, axis=1)))
        if ch != int(r["探索＋早年換手"]):
            bad.append((r["件"], r["格"], ch, int(r["探索＋早年換手"])))
    RES["② 換手次數（44 格）"] = {"不同": bad[:5], "過": not bad}
    print(RES["② 換手次數（44 格）"], flush=True)
    # ③
    diffs = []

    def OC(lev):
        return ([o, G["O"][lev] if lev != "SYN" else So], [cf, pd.Series(G["C"][lev]).ffill().to_numpy() if lev != "SYN" else Sc])
    for fam, key in S["挑格"].items():
        if key is None:
            continue
        W = WW[(fam, key)][0]
        for sg, (a, b, lev) in SEG.items():
            Oo, Cc = OC(lev)
            cg, md, _ = my_engine(W, a, b, Oo, Cc)
            ref = CE[(CE["件"] == fam) & (CE["格"] == key) & (CE["段"] == sg)].iloc[0]
            diffs.append(max(abs(cg - ref["年化"]), abs(md - ref["回落"])))
    for sg, (a, b, lev) in SEG.items():
        Oo, Cc = OC(lev)
        hold = np.tile([0.0, 1.0], (N, 1)); cg, md, _ = my_engine(hold, a, b, Oo, Cc)
        ref = S["基準"][sg]["一直抱正2"]; diffs.append(max(abs(cg - ref["年化"]), abs(md - ref["回落"])))
        R = np.zeros(b - a + 1, bool)
        for k in range(1, b - a + 1):
            if cal[a + k][:7] != cal[a + k - 1][:7] and cal[a + k][5:7] == "01":
                R[k] = True
        cg, md, _ = my_engine(np.tile([0.6, 0.4], (N, 1)), a, b, Oo, Cc, R)
        ref = S["基準"][sg]["六四v1"]; diffs.append(max(abs(cg - ref["年化"]), abs(md - ref["回落"])))
    RES["③ 自寫引擎（挑中格、一直抱正2、六四 v1）"] = {"比對": len(diffs), "最大差": float(max(diffs)), "過": bool(max(diffs) < 1e-9)}
    print(RES["③ 自寫引擎（挑中格、一直抱正2、六四 v1）"], flush=True)
    # ④
    mism = []
    for fam in ("甲", "乙", "丙"):
        ex = CE[(CE["件"] == fam) & (CE["段"] == "探索")].reset_index(drop=True)
        ok = ex[ex["退化"].fillna("") == ""]
        best = ok.assign(_o=range(len(ok))).sort_values(["年化", "換手次數", "_o"], ascending=[False, True, True]).iloc[0]["格"] if len(ok) else None
        if best != S["挑格"][fam]:
            mism.append((fam, best, S["挑格"][fam]))
        if best is None:
            continue
        more = {}
        for sg in ("確認", "早年"):
            r = CE[(CE["件"] == fam) & (CE["格"] == best) & (CE["段"] == sg)].iloc[0]
            more[sg] = r["年化"] > S["基準"][sg]["一直抱正2"]["年化"]
        read = "穩" if all(more.values()) else ("沒多賺" if not any(more.values()) else ("不穩，只在多頭段（確認段）有用" if more["確認"] else "不穩，只在空頭段（早年段，含 2008）有用"))
        J = S["判定"][fam]
        if read != J["讀法"]:
            mism.append((fam, read, J["讀法"]))
        r = CE[(CE["件"] == fam) & (CE["格"] == best) & (CE["段"] == "早年")].iloc[0]
        w = J["2008型最慘（早年段最大回落、100萬在高點）"]
        if abs((1 + r["回落"]) * 100 - w["剩（萬）"]) > 1e-9 or bool(r["回落"] < -0.70) != w["超過使用者上限 −70%"]:
            mism.append((fam, "2008", r["回落"], w))
    RES["④ 挑格、讀法、2008 型最慘"] = {"不同": mism, "過": not mism}
    RES["全部過"] = all(v["過"] is True for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
