# -*- coding: utf-8 -*-
"""USREG-A1-1～5 【獨立路】查核。⛔ 不 import researchUSA1*／researchLev2／researchLowFreq／researchTri／researchY／researchRev／us_data。
只讀 ~/usdata/60d2f99/data 的原始 CSV 與 resultsUSA1/ 的彙總，自己重寫讀檔、指標、狀態機、引擎，抽樣重算：
 ① 基準 ^SP500TR 探索／確認同窗年化、回落 ② 合成 2 倍對帳（SSO、QLD 主利差）③ 件一：問一隨機 12 格＋問二全部格（兩段）
 ④ 件二：甲乙丙挑中格（探索、確認）⑤ 件三：#5 調降、#7 低端、#8 高端 事件數與差 ⑥ 件四 大盤層：TD9 賣／買、RSI 70 跌回、跌破／站回 60 日線 × H 5／20／60 原版
 ⑦ 件五：挑中格＋隨機 4 格（兩段）⑧ repo 結果檔：無原始欄、每檔 < 10MB。
容差：年化、回落、差 ≤ 1e-9；件數、標籤逐一相同 ⇒「0 不同」才算過。輸出 resultsUSA1/check.json。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA1_check
"""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

D = os.path.expanduser("~/usdata/60d2f99/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA1")
END = "2026-09-30"
ANN = 252
TOL = 1e-9
BAD = []


def chk(name, ok, detail=""):
    if not ok:
        BAD.append(f"{name}：{detail}")
    return bool(ok)


# ═════════ 讀檔 ═════════
cal = np.array(sorted(x for x in pd.read_csv(os.path.join(D, "macro", "yahoo_GSPC.csv"), dtype=str)["date"] if x <= END))
pos = {d: i for i, d in enumerate(cal)}
N = len(cal)


def ycsv(nm):
    d = pd.read_csv(os.path.join(D, "macro", f"yahoo_{nm}.csv"), dtype={"date": str}).drop_duplicates("date").set_index("date")
    return d.reindex(cal)


PX = {}
for k in ("SPY", "QQQ", "SSO", "QLD"):
    y = ycsv(k); f = (y["adjclose"] / y["close"]).to_numpy(float)
    PX[k] = {c: y[c].to_numpy(float) * f for c in ("open", "high", "low", "close")}
    PX[k]["volume"] = y["volume"].to_numpy(float)
trd = ycsv("SP500TR"); gsp = ycsv("GSPC")
TRc = trd["adjclose"].to_numpy(float); GSc = gsp["close"].to_numpy(float)
fr = TRc / GSc
s0spy = int(np.flatnonzero(np.isfinite(PX["SPY"]["close"]))[0]); kJ = PX["SPY"]["close"][s0spy] / TRc[s0spy]
J = {}
for c, g in (("open", gsp["open"]), ("high", gsp["high"]), ("low", gsp["low"]), ("close", None)):
    a = PX["SPY"][c].copy()
    base = TRc if c == "close" else g.to_numpy(float) * fr
    a[:s0spy] = base[:s0spy] * kJ
    J[c] = a
db = pd.read_csv(os.path.join(D, "macro", "fred_DTB3.csv"), dtype=str, keep_default_na=False)
db = db[db["date"] <= END]; db["v"] = pd.to_numeric(db["value"].replace({"": None, ".": None}), errors="coerce")
db = db.dropna(subset=["v"])
dtb = pd.Series(db["v"].to_numpy(), index=db["date"]).reindex(sorted(set(db["date"]) | set(cal))).ffill().reindex(cal).to_numpy(float)
G = np.zeros(N); G[1:] = dtb[:-1] / 100 / ANN


def syn(kind, s=0.0025):
    o, c = (np.r_[J["open"][:0], (gsp["open"].to_numpy(float) * fr)], TRc) if kind == "SSO" else (PX["QQQ"]["open"], PX["QQQ"]["close"])
    fee = 0.0089 if kind == "SSO" else 0.0095
    st = int(np.flatnonzero(np.isfinite(c))[0])
    Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[st] = 1.0
    for t in range(st + 1, N):
        Lc[t] = Lc[t - 1] * (1 + 2 * (c[t] / c[t - 1] - 1) - (dtb[t - 1] / 100 + s) / ANN - fee / ANN)
        Lo[t] = Lc[t - 1] * (1 + 2 * (o[t] / c[t - 1] - 1))
    return Lo, Lc


def sim(ast, W, a, b, cost=0.0005):
    """獨立引擎：t 開盤換到 W[t]（權重變了或年度再平衡日）；換手 ＝ ½(Σ|目標值−現值| ＋ |現金差|)；現金每日 ×(1＋DTB3_{t−1}/252)。"""
    o = np.stack([ast[x][0][a:b + 1] for x in range(len(ast))], 1)
    c = np.stack([pd.Series(ast[x][1]).ffill().to_numpy()[a:b + 1] for x in range(len(ast))], 1)
    W = np.asarray(W, float); n = b - a + 1
    yr = np.array([d[:4] for d in cal[a:b + 1]]); reb = np.r_[False, yr[1:] != yr[:-1]]
    u = np.zeros(W.shape[1]); cash = 1.0; last = None; eq = np.empty(n)
    for t in range(n):
        if last is None or reb[t] or not np.array_equal(W[t], last):
            assert np.all(np.isfinite(o[t][(u > 0) | (W[t] > 0)])), "缺開盤"
            hv = u * o[t]; V = hv.sum() + cash
            tv = W[t] * V; tc = (1 - W[t].sum()) * V
            V -= 0.5 * (np.abs(tv - hv).sum() + abs(tc - cash)) * cost
            u = np.where(W[t] > 0, W[t] * V / o[t], 0.0); cash = (1 - W[t].sum()) * V; last = W[t].copy()
        if t > 0:
            cash *= 1 + G[a + t]
        eq[t] = (u * c[t]).sum() + cash
    cg = eq[-1] ** (ANN / n) - 1
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p)
    return float(cg), float(((p - pk) / pk).min())


def bperf(x, a, b):
    s = x[a:b + 1]; pk = np.maximum.accumulate(s)
    return float((s[-1] / s[0]) ** (ANN / len(s)) - 1), float(((s - pk) / pk).min())


def lab(c, m, cb, mb):
    r = c / abs(m) if m < 0 else float("nan"); rb = cb / abs(mb)
    return "合格" if (c > cb and r >= rb) else ("另列" if c > cb else "不合格")


def near(a, b):
    return abs(float(a) - float(b)) <= TOL


R = {}
SEG = {"探索": (pos["2007-04-02"], pos["2021-12-31"]), "確認": (pos["2022-01-03"], pos[END])}
BEN = {k: bperf(TRc, *v) for k, v in SEG.items()}
# ① 基準
S1 = json.load(open(os.path.join(OUT, "A1_summary.json"), encoding="utf-8"))
d1 = max(max(abs(BEN[k][0] - S1["基準"][k]["年化"]), abs(BEN[k][1] - S1["基準"][k]["回落"])) for k in SEG)
R["①基準"] = {"最大差": d1, "過": chk("①基準", d1 <= TOL, d1)}
# ② 合成對帳
REC = json.load(open(os.path.join(OUT, "A0_synth_recon.json"), encoding="utf-8"))
a, b = SEG["探索"]; d2 = 0.0
for kind in ("SSO", "QLD"):
    _, Lc = syn(kind)
    sy = Lc[a:b + 1] / Lc[a]; re = PX[kind]["close"][a:b + 1] / PX[kind]["close"][a]
    diff = (sy[-1] ** (ANN / len(sy)) - 1) - (re[-1] ** (ANN / len(re)) - 1)
    rr = [x for x in REC["結果"] if x["正2"] == kind and x["主"]][0]
    d2 = max(d2, abs(diff * 100 - rr["年化差（點）"]))
R["②合成對帳"] = {"最大差（點）": d2, "過": chk("②合成", d2 <= 1e-7, d2)}
# ③ 件一
Q1 = pd.read_csv(os.path.join(OUT, "A1_q1_cells.csv")); Q2 = pd.read_csv(os.path.join(OUT, "A1_q2_cells.csv"))
AS = {k: (PX[k]["open"], PX[k]["close"]) for k in PX}
nb = 0; nchk = 0
for i in np.random.default_rng(20261007).choice(len(Q1), 12, replace=False):
    r = Q1.iloc[int(i)]; a, b = SEG[r["段"]]; n = b - a + 1
    W = np.tile([r["ETF%"] / 100, r["正2%"] / 100], (n, 1))
    c_, m_ = sim([AS[r["ETF"]], AS[r["正2"]]], W, a, b)
    ok = near(c_, r["年化"]) and near(m_, r["回落"]) and lab(c_, m_, *BEN[r["段"]]) == r["標籤"]
    nb += not ok; nchk += 1
    chk("③問一", ok, (r["段"], r["ETF"], r["正2"], r["ETF%"], r["正2%"], c_, r["年化"]))
Jc = J["close"]
ma = {k: pd.Series(Jc).rolling(k, min_periods=k).mean().to_numpy() for k in (20, 50, 60, 200)}
raw = {"C1": Jc > ma[200], "C2": Jc > ma[60], "C3": Jc > ma[20], "C4": ma[50] > ma[200]}
cond = {}
for k, v in raw.items():
    v = np.where(np.isfinite(ma[200] if k in ("C1", "C4") else ma[{"C2": 60, "C3": 20}[k]]), v, False)
    cond[k] = np.r_[False, v[:-1]]
p1 = S1["問一"].get("挑中")
for _, r in Q2.iterrows():
    a, b = SEG[r["段"]]; n = b - a + 1; on = cond[r["條件"]][a:b + 1]
    if r["換法"] == "X1":
        ast, W = [AS[r["正2"]]], on.astype(float)[:, None]
    elif r["換法"] == "X2":
        ast, W = [AS[r["ETF"]], AS[r["正2"]]], np.stack([(~on).astype(float), on.astype(float)], 1)
    else:
        ast, W = [AS[r["ETF"]], AS[r["正2"]]], np.stack([np.full(n, p1["ETF%"] / 100), np.where(on, p1["正2%"] / 100, 0.0)], 1)
    c_, m_ = sim(ast, W, a, b)
    ok = near(c_, r["年化"]) and near(m_, r["回落"]) and lab(c_, m_, *BEN[r["段"]]) == r["標籤"]
    nb += not ok; nchk += 1
    chk("③問二", ok, (r["段"], r["條件"], r["換法"], r["ETF"], r["正2"], c_, r["年化"]))
R["③件一"] = {"抽查格": nchk, "不同": nb}
# ④ 件二
S2 = json.load(open(os.path.join(OUT, "A2_summary.json"), encoding="utf-8")); C2 = pd.read_csv(os.path.join(OUT, "A2_cells.csv"))
cj = Jc
me = np.r_[np.array([cal[t][:7] != cal[t + 1][:7] for t in range(N - 1)]), False]
mei = np.flatnonzero(me)
ma200 = np.full(N, np.nan); ma200[199:] = [math.fsum(cj[t - 199:t + 1]) / 200 for t in range(199, N)]
MK = {}
for k in (6, 10, 12):
    arr = np.full(N, np.nan)
    for j in range(k - 1, len(mei)):
        arr[mei[j]] = float(np.mean(cj[mei[j - k + 1:j + 1]]))
    MK[f"M{k}"] = arr
MK["D200"] = ma200
e0x = SEG["探索"][0]
LEVC = {k: np.where(np.arange(N) < e0x, syn(k)[1], PX[k]["close"]) for k in ("SSO", "QLD")}
n4 = 0; b4 = 0
for fam, key in S2["挑格"].items():
    if key is None:
        continue
    p = key.split("_"); W = np.full((N, 2), np.nan)
    if fam == "甲":
        lev = p[2]; ma_ = MK[p[0]]; cur = None
        for t in range(N):
            if cur is not None:
                W[t] = cur
            if me[t] and np.isfinite(ma_[t]):
                cur = [0.0, 1.0] if cj[t] > ma_[t] else ([1.0, 0.0] if p[1] == "a" else [0.0, 0.0])
    elif fam == "乙":
        lev = p[3]; s_, L_ = int(p[0][1:]) / 100, int(p[1][1:]); cur = None
        rS = syn(lev)[1]; rS = rS[1:] / rS[:-1] - 1; rR = PX[lev]["close"][1:] / PX[lev]["close"][:-1] - 1   # 探索段起用真實正2 自己的歷史、之前用合成（台股 lev_of 同義）
        for t in range(1, N):
            if me[t - 1]:
                rr = rR if t >= e0x else rS
                x = rr[max(0, t - 1 - L_):t - 1]
                x = x[np.isfinite(x)]
                if len(x) == L_:
                    sg = float(np.std(x, ddof=1) * np.sqrt(ANN)); w = min(1.0, s_ / sg)
                    cur = [1 - w, w] if p[2] == "a" else [0.0, w]
            if cur is not None:
                W[t] = cur
    else:
        h, x_, rk, fq = p[0], int(p[1][1:]) / 100, p[2], p[3]; lev = "SSO" if h in ("SPY", "SSO") else "QLD"
        hold = [1.0, 0.0] if h == "SPY" else [0.0, 1.0]
        hi250 = np.full(N, np.nan); hi250[249:] = [cj[t - 249:t + 1].max() for t in range(249, N)]
        nh60 = np.zeros(N, bool); nh60[59:] = [cj[t] > cj[t - 59:t].max() for t in range(59, N)]
        xup = np.r_[False, (cj[:-1] <= ma200[:-1]) & (cj[1:] > ma200[1:])]
        g0 = pos[S2["丙狀態機起跑"]]; s = 1; prev = None; nxt = {}
        for t in range(g0, N):
            if not (fq == "D" or me[t]):
                continue
            below = bool(np.isfinite(ma200[t]) and cj[t] <= ma200[t])
            if s == 1:
                if np.isfinite(hi250[t]) and cj[t] <= hi250[t] * (1 - x_):
                    s = 0; nxt[t] = 0
            else:
                go = nh60[t] if rk == "R1" else (xup[t] if fq == "D" else (prev is True and np.isfinite(ma200[t]) and cj[t] > ma200[t]))
                if go:
                    s = 1; nxt[t] = 1
            if fq == "M":
                prev = below
        cur = 1; W[g0] = hold
        for t in range(g0 + 1, N):
            if t - 1 in nxt:
                cur = nxt[t - 1]
            W[t] = hold if cur == 1 else [0.0, 0.0]
    for sg in ("探索", "確認"):
        a, b = SEG[sg]
        c_, m_ = sim([AS["SPY"], AS[lev]], W[a:b + 1], a, b)
        r = C2[(C2["件"] == fam) & (C2["格"] == key) & (C2["段"] == sg)].iloc[0]
        ok = near(c_, r["年化"]) and near(m_, r["回落"]); n4 += 1; b4 += not ok
        chk("④件二", ok, (fam, key, sg, c_, r["年化"]))
R["④件二"] = {"抽查格": n4, "不同": b4}
# ⑤ 件三
C3 = pd.read_csv(os.path.join(OUT, "A3_cells.csv")); C3 = C3[C3["版"] == "主"]
w0, w1 = pos["2007-04-02"], pos[END]
oS = PX["SPY"]["open"]; R20 = np.full(N, np.nan); R20[:N - 20] = oS[20:] / oS[:-20] - 1
el = np.arange(w0, w1 - 19); el = el[np.isfinite(R20[el])]; base = R20[el].mean()


def fred_ev(nm, mode, end):
    x = pd.read_csv(os.path.join(D, "macro", f"fred_{nm}.csv"), dtype=str, keep_default_na=False)
    x = x[x["date"] <= END]; v = pd.to_numeric(x["value"].replace({"": None, ".": None}), errors="coerce"); x = x[v.notna()]; v = v[v.notna()].to_numpy(float)
    d = x["date"].to_numpy(str)
    if mode == "bp":
        vv = np.full(len(v), np.nan); vv[20:] = (v[20:] - v[:-20]) * 100; v = vv
    f0 = int(np.argmax(np.isfinite(v))); keep = []; lastk = None
    for i in range(f0 + 755, len(v)):
        w = v[i - 755:i + 1]
        hit = v[i] >= np.percentile(w, 95) if end == "高端" else v[i] <= np.percentile(w, 5)
        if hit and (lastk is None or i - lastk >= 20):
            keep.append(i); lastk = i
    out = []
    for i in keep:
        if "2007-04-02" <= d[i] <= END:
            s = int(np.searchsorted(cal, d[i], side="right"))
            if w0 <= s and s + 20 <= w1:
                out.append(s)
    return np.array(out, int)


n5 = 0; b5 = 0
for (nm, mode, key, end) in (("VIXCLS", "lvl", "#8", "高端"), ("DGS10", "bp", "#7", "低端")):
    s = fred_ev(nm, mode, end); r = C3[(C3["因素"] == key) & (C3["端"] == end)].iloc[0]
    ok = len(s) == int(r["n"]) and (not np.isfinite(r.get("D", np.nan)) or near(R20[s].mean() - base, r["D"])); n5 += 1; b5 += not ok
    chk("⑤件三", ok, (key, end, len(s), r["n"]))
fm = pd.read_csv(os.path.join(D, "macro", "fomc_rate_changes.csv"), dtype=str, keep_default_na=False)
dn = ~fm["decrease_bp"].str.strip().isin(["", "...", "0"])
ss = np.searchsorted(cal, fm.loc[dn, "statement_date"].to_numpy(str), side="right"); kept = []; lk = None
for s_ in ss:
    if lk is None or s_ - lk >= 20:
        kept.append(s_); lk = s_
kept = [s_ for s_ in kept if s_ < N and "2007-04-02" <= cal[s_] <= END and s_ + 20 <= w1]
r = C3[(C3["因素"] == "#5") & (C3["端"] == "調降")].iloc[0]
ok = len(kept) == int(r["n"]); n5 += 1; b5 += not ok; chk("⑤件三#5", ok, (len(kept), r["n"]))
R["⑤件三"] = {"抽查格": n5, "不同": b5}
# ⑥ 件四 大盤層
C4 = pd.read_csv(os.path.join(OUT, "A4_cells.csv"))
so, sc = PX["SPY"]["open"], PX["SPY"]["close"]; val = np.isfinite(sc); bars = np.flatnonzero(val)
lvi = np.maximum.accumulate(np.where(val, np.arange(N), -1)); cb_ = sc[bars]


def rsi_w(c, n=14):
    out = np.full(len(c), np.nan); d = np.diff(c); g = np.maximum(d, 0); l_ = np.maximum(-d, 0)
    ag, al = g[:n].mean(), l_[:n].mean(); out[n] = 100 - 100 / (1 + ag / al) if al else 100
    for t in range(n + 1, len(c)):
        ag = (ag * (n - 1) + g[t - 1]) / n; al = (al * (n - 1) + l_[t - 1]) / n
        out[t] = 100 - 100 / (1 + ag / al) if al else 100
    return out


def td(up):
    ev = []; run = 0
    for t in range(len(cb_)):
        okk = t >= 4 and ((cb_[t] > cb_[t - 4]) if up else (cb_[t] < cb_[t - 4]))
        run = run + 1 if okk else 0
        if run == 9:
            ev.append(t)
    return ev


rs = rsi_w(cb_); m60 = np.full(len(cb_), np.nan); m60[59:] = [math.fsum(cb_[t - 59:t + 1]) / 60 for t in range(59, len(cb_))]
DET = {"H_TD": td(True), "L_TD": td(False), "H_RSI": [t for t in range(1, len(cb_)) if rs[t - 1] > 70 and rs[t] < 70],
       "H_MA": [t for t in range(1, len(cb_)) if np.isfinite(m60[t - 1]) and cb_[t] < m60[t] and cb_[t - 1] >= m60[t - 1]],
       "L_MA": [t for t in range(1, len(cb_)) if np.isfinite(m60[t - 1]) and cb_[t] > m60[t] and cb_[t - 1] <= m60[t - 1]]}
lo, hi = pos["2007-04-02"], pos[END]; n6 = 0; b6 = 0
for H in (5, 20, 60):
    bd = [d for d in range(lo, hi - H + 1) if val[d] and np.isfinite(so[d + 1])]
    bm = np.mean([sc[lvi[d + H]] / so[d + 1] - 1 for d in bd])
    for code, evb in DET.items():
        T = [int(bars[t]) for t in evb]; T = [t for t in T if lo <= t <= hi - H]; kept = []; t0 = -10 ** 9
        for t in T:
            if not (t0 < t <= t0 + 20):
                kept.append(t); t0 = t
        kept = [t for t in kept if np.isfinite(so[t + 1])]
        X = np.array([sc[lvi[t + H]] / so[t + 1] - 1 for t in kept]) - bm
        r = C4[(C4["層"] == "大盤") & (C4["段"] == "主窗") & (C4["code"] == code) & (C4["版"] == "原版") & (C4["H"] == H)].iloc[0]
        ok = len(kept) == int(r["事件"]) and (len(kept) == 0 or near(X.mean(), r["mean"])); n6 += 1; b6 += not ok
        chk("⑥件四", ok, (code, H, len(kept), r["事件"]))
R["⑥件四大盤"] = {"抽查格": n6, "不同": b6}
# ⑦ 件五
S5 = json.load(open(os.path.join(OUT, "A5_summary.json"), encoding="utf-8")); C5 = pd.read_csv(os.path.join(OUT, "A5_cells.csv.gz"))
c, h, l = J["close"], J["high"], J["low"]


def mafs(x, n):
    o = np.full(len(x), np.nan); o[n - 1:] = [math.fsum(x[t - n + 1:t + 1]) / n for t in range(n - 1, len(x))]
    return o


m20, m60_, m200 = mafs(c, 20), mafs(c, 60), mafs(c, 200)
e12 = pd.Series(c).ewm(span=12, adjust=False).mean().to_numpy(); e26 = pd.Series(c).ewm(span=26, adjust=False).mean().to_numpy()
dif = e12 - e26; dif[:25] = np.nan; dea = np.full(N, np.nan); dea[25:] = pd.Series(dif[25:]).ewm(span=9, adjust=False).mean().to_numpy()
K = np.full(N, np.nan); Dd = np.full(N, np.nan); k_ = d_ = 50.0
for t in range(8, N):
    hh, ll = h[t - 8:t + 1].max(), l[t - 8:t + 1].min(); rsv = 50.0 if hh == ll else (c[t] - ll) / (hh - ll) * 100
    k_ = k_ * 2 / 3 + rsv / 3; d_ = d_ * 2 / 3 + k_ / 3; K[t] = k_; Dd[t] = d_
RS = rsi_w(c)
sd = np.full(N, np.nan); sd[19:] = [np.std(c[t - 19:t + 1]) for t in range(19, N)]
lower = m20 - 2 * sd; bias = c / m60_ - 1
hi5 = np.full(N, np.nan); hi5[249:] = [c[t - 249:t + 1].max() for t in range(249, N)]; dd = c / hi5 - 1
Kp = np.r_[np.nan, K[:-1]]
with np.errstate(invalid="ignore"):
    def dn_(a, b):
        return np.r_[False, (a[1:] < b[1:]) & (a[:-1] >= b[:-1])]

    def up_(a, b):
        return np.r_[False, (a[1:] > b[1:]) & (a[:-1] <= b[:-1])]
    SG5 = {"W1": dn_(c, m20), "W2": dn_(c, m60_), "W3": dn_(c, m200), "W4": dn_(m20, m60_), "W5": dn_(dif, dea), "W6": dn_(K, Dd) & (Kp > 80),
           "W7": np.r_[False, (RS[:-1] > 50) & (RS[1:] < 50)], "W8": np.r_[False, (bias[:-1] > 0.10) & (bias[1:] <= 0.10)],
           "P1": dd <= -0.15, "P2": dd <= -0.20, "P3": dd <= -0.30, "P4": RS < 30, "P5": K < 20, "P6": dn_(c, lower), "P7": bias < -0.10,
           "U1": up_(c, m20), "U2": up_(c, m60_), "U3": up_(m20, m60_), "U4": up_(dif, dea), "U5": up_(K, Dd) & (Kp < 20),
           "U6": np.r_[False, (RS[:-1] < 50) & (RS[1:] > 50)], "U7": up_(c, m20)}
s0 = pos[S5["狀態機起跑"]]


def mach(w, p_, u):
    st = np.full(N, -1, np.int8); st[s0] = 0
    for t in range(s0 + 1, N):
        a_, j = st[t - 1], t - 1
        st[t] = (1 if SG5[w][j] else 0) if a_ == 0 else ((0 if SG5[u][j] else (2 if SG5[p_][j] else 1)) if a_ == 1 else (0 if SG5[u][j] else 2))
    return st


n7 = 0; b7 = 0
rows = [S5["挑法乙"]["格"]] + [list(C5.iloc[int(i)][["轉弱", "跌深", "反彈", "A態", "B態", "C態"]]) for i in np.random.default_rng(7).choice(len(C5), 4, replace=False)]
for w, p_, u, av, bv, cv in rows:
    if not all(k in SG5 for k in (w, p_, u)):
        continue
    st = mach(w, p_, u)
    W = np.zeros((N, 3)); W[st == 0, 2] = 1
    if bv != "現金":
        W[st == 1, ("SPY", "QQQ").index(bv)] = 1
    W[st == 2, ("SPY", "QQQ").index(cv)] = 1
    for sg in ("探索", "確認"):
        a, b = SEG[sg]
        c_, m_ = sim([AS["SPY"], AS["QQQ"], AS[av]], W[a:b + 1], a, b)
        r = C5[(C5["段"] == sg) & (C5["轉弱"] == w) & (C5["跌深"] == p_) & (C5["反彈"] == u) & (C5["A態"] == av) & (C5["B態"] == bv) & (C5["C態"] == cv)].iloc[0]
        ok = near(c_, r["年化"]) and near(m_, r["回落"]); n7 += 1; b7 += not ok
        chk("⑦件五", ok, (w, p_, u, av, bv, cv, sg, c_, r["年化"]))
R["⑦件五"] = {"抽查格": n7, "不同": b7}
# ⑧ repo 檔
forbid = {"open", "high", "low", "close", "adjclose", "volume", "R20", "R", "Rc", "date"}
fz = []
for f in sorted(glob.glob(os.path.join(OUT, "*"))):
    sz = os.path.getsize(f); bad = []
    if f.endswith((".csv", ".csv.gz")):
        cols = set(pd.read_csv(f, nrows=1).columns)
        bad = sorted(cols & forbid)
    fz.append({"檔": os.path.basename(f), "bytes": sz, "原始欄": bad})
    chk("⑧檔", sz < 10 * 2 ** 20 and not bad, (os.path.basename(f), sz, bad))
R["⑧repo檔"] = {"檔數": len(fz), "最大bytes": max(x["bytes"] for x in fz), "有原始欄": [x["檔"] for x in fz if x["原始欄"]]}
R["不同"] = BAD
R["全部通過"] = not BAD
json.dump(R, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
print("全部通過" if not BAD else f"⛔ 有 {len(BAD)} 處不同")
sys.exit(0 if not BAD else 1)
