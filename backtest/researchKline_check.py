# -*- coding: utf-8 -*-
"""researchKline 的獨立查核（⛔ 不 import researchKline）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchKline_check.py [--n 60]

① 抽 --n 檔，自己寫事件偵測（向量化 pandas，與主程式的逐根迴圈不同路）：K線 研究十二（G＋E、V）、十三（B 與五條件）、十四（X1 結局）；⚠ 研究九（三尊頭、W 底）⛔ 沒有抽查（局部點偵測只在主程式一條路）
   ⇒ 對 events.csv.gz 這些檔的列（T、旗標、結局）
② 自己讀全部 gate3 收盤、自己算 R_H 與基準①（T 日有收盤的全部股票等權）、自己做 [first, T＋H] 硬斷點剔除，重算 K線 研究十二 H20「有 V − 無 V」的兩組平均差
   ⇒ 與 cells.csv 的判定量比（兩組迴歸係數 ＝ 兩組平均差）
⇒ resultsKline/check.json
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
import researchH2 as H2

D, UG = H2.D, H2.UG
HERE = os.path.expanduser("~/tw-p17/backtest"); OUT = os.path.join(HERE, "resultsKline")
ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=60); a = ap.parse_args()
errs = []; info = {}
cal = D.load_calendar(); n = len(cal)
w0 = int(cal.searchsorted(pd.Timestamp(H2.W0))); w1 = int(cal.searchsorted(pd.Timestamp(H2.W1)))
U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)); mk = U.set_index("stock_id")["market"]
EV = pd.read_csv(os.path.join(HERE, "resultsKline", "events.csv.gz"), dtype={"sid": str}, low_memory=False)
rng = np.random.default_rng(20260928)
samp = sorted(rng.choice(sorted(EV["sid"].unique()), size=min(a.n, EV["sid"].nunique()), replace=False))


def dd(ts):
    out = []; last = -10 ** 9
    for t in ts:
        if t - last > 20:
            out.append(t); last = t
    return out


nb_ = 0; nt = 0
for s in samp:
    st = D.load_stock(s, mk[s], cal); df = st.df
    c = df["close"].to_numpy(float); valid = np.isfinite(c); b = np.flatnonzero(valid)
    s_c = pd.Series(c[b]); s_o = pd.Series(df["open"].to_numpy(float)[b]); s_l = pd.Series(df["low"].to_numpy(float)[b])
    s_a = pd.Series(pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)[b])
    ret1 = s_c.pct_change(); ma60 = s_c.rolling(60).mean(); a20 = s_a.shift(1).rolling(20).mean(); r20 = s_c / s_c.shift(20) - 1
    inw = pd.Series((b >= w0) & (b <= w1 - 5))
    ge = np.flatnonzero((inw & (ret1 >= 0.07) & (s_c > ma60) & (s_a >= 2 * a20) & (r20 < 0.15)).to_numpy())
    v1 = s_a.shift(21).rolling(40).mean(); v2 = s_a.shift(61).rolling(60).mean()
    mine12 = [(int(b[t]), bool(v1[t] <= 0.8 * v2[t])) for t in dd(ge) if np.isfinite(v1[t]) and np.isfinite(v2[t])]
    ref12 = [(int(t), bool(v)) for t, v in zip(EV.loc[(EV["sid"] == s) & (EV["研究"] == "十二"), "T"], EV.loc[(EV["sid"] == s) & (EV["研究"] == "十二"), "V"].map(lambda x: str(x) == "True"))]
    nt += 1
    if mine12 != ref12:
        nb_ += 1; errs.append(f"① {s} 研究十二")
    Bm = np.flatnonzero((inw & (pd.Series(np.arange(len(b))) >= 500) & (ret1 >= 0.07) & (s_c > ma60)).to_numpy())
    red = (s_c > s_o).to_numpy()
    mine13 = []
    for t in dd(Bm):
        seg = s_c.iloc[t - 120:t - 20]; w60 = s_c.iloc[t - 59:t + 1]
        mine13.append((int(b[t]), bool(red[t] and red[t - 1]), bool(red[t] and red[t - 1] and red[t - 2]), bool(seg.max() / seg.min() - 1 <= 0.30),
                       bool((r20.iloc[max(20, t - 499):t + 1] >= 0.5).any()), bool(s_c[t] >= w60.min() + 0.5 * (w60.max() - w60.min()))))
    e13 = EV[(EV["sid"] == s) & (EV["研究"] == "十三")]
    ref13 = [(int(r["T"]), *(str(r[k]) == "True" for k in ("R2", "R3", "Tc", "S", "W"))) for _, r in e13.iterrows()]
    nt += 1
    if mine13 != ref13:
        nb_ += 1; errs.append(f"① {s} 研究十三")
    e14 = EV[(EV["sid"] == s) & (EV["研究"] == "十四")]
    mine14 = []
    for t in dd(Bm):
        res = "6日等不到"
        for j in range(t + 1, min(t + 7, len(b))):
            if s_l[j] < s_l[t]:
                res = "跌破訊號日最低"; break
            if s_c[j] < s_c[j - 1] and s_a[j] < s_a[t]:
                res = "執行"; break
        mine14.append((int(b[t]), res))
    nt += 1
    if mine14 != [(int(t), r) for t, r in zip(e14["T"], e14["結局"])]:
        nb_ += 1; errs.append(f"① {s} 研究十四")
info["① 抽查檔數／比對組／不同"] = [len(samp), nt, nb_]
# ② K線 研究十二 H20 基準① 兩組平均差
T = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
r = T[(T["研究"] == "K線 研究十二") & (T["H"] == 20) & (T["基準"] == "基準①")].iloc[0]
import researchM_freq as RF
TR = H2.TR; off = TR.load_official()
CL = {}; CS = {}
for s_, m_ in zip(U["stock_id"], U["market"]):
    st = D.load_stock(s_, m_, cal)
    if st is None:
        continue
    c = st.df["close"].to_numpy(float); v = np.isfinite(c)
    if v.sum() < 30:
        continue
    CL[s_] = (np.where(v, c, np.nan), pd.Series(c).ffill().to_numpy())
    if s_ in set(EV.loc[EV["研究"] == "十二", "sid"]):
        pb = np.zeros(n, bool)
        for b_ in D.breakpoints(st.df, st.event_dates):
            if b_["rule"] in ("price", "price+gap"):
                pb[b_["pos"]] = True
        tb = TR.one(s_, cal); ds = TR.delist_status({s_: tb}, cal, official=off).get(s_)
        g5 = RF._g5(v, upto=ds["last"]) if (ds is not None and ds["status"].startswith("delisted")) else RF._g5(v)
        CS[s_] = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
H = 20
num = np.zeros(n); den = np.zeros(n)
for c, cf in CL.values():
    rr = np.full(n, np.nan); rr[:n - H] = cf[H:] / c[:n - H] - 1
    ok = np.isfinite(rr); num[ok] += rr[ok]; den[ok] += 1
EW = np.where(den > 0, num / np.maximum(den, 1), np.nan)
e12 = EV[EV["研究"] == "十二"]
X = []; G = []
for s_, t, f, vv in zip(e12["sid"], e12["T"].astype(int), e12["first"].astype(int), e12["V"].map(lambda x: str(x) == "True")):
    if t + H > w1 or H2.brk(CS[s_], f, t + H):
        continue
    c, cf = CL[s_]
    r_ = cf[t + H] / c[t] - 1
    if np.isfinite(r_):
        X.append(r_ - EW[t]); G.append(vv)
X = np.array(X); G = np.array(G)
Dm = float(X[G].mean() - X[~G].mean())
info["② 研究十二 H20 基準① D（自算／檔）"] = [Dm, float(r["毛_D"]), int(G.sum()), int((~G).sum()), float(r["毛_n有"]), float(r["毛_n無"])]
if abs(Dm - float(r["毛_D"])) > 1e-12 or int(G.sum()) != int(r["毛_n有"]) or int((~G).sum()) != int(r["毛_n無"]):
    errs.append("② 研究十二 D")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:20]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:10]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
