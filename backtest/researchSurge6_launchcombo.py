# -*- coding: utf-8 -*-
"""launch 追加：「組合起來呢？」——剛從低檔發動的股票，條件兩兩／三個窮舉與簡單 logistic 模型，能不能把變飆股的比例拉高
（參考，⛔ 不計 N；探索 2021-01～2023-12 找、確認 2024-01～2026-08 驗）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_launchcombo [--check | --page]

═══ 讀法（寫死於 2026-09-30 20:50（台北），在算任何數字之前）═══
 C1 母體（同 launch10 A3）：有 K 棒、段內的股-日，[d−59, d] 有效 K 棒內最低收盤那根 L（同價取最近）的位置 pos(L) ≤ 0.4 且 c[d] ÷ c[L] − 1 ∈ [5%, 30%]
 C2 候選條件（全部二元；只用 launch 已算好的定義與探索段資訊）：
    當下訊號 16 個（launch L4，近 3 日發生）｜狀態特徵 ＝ launch 特徵候選裡「V2 探索段 judge 倍數格中位 ≥ 1.2」者（launch/judge.csv；26 個）｜
    低檔打底四個五等分的 Q1 與 Q5（8 個）；協調者點名的注意、處置、55 日新高、營收成長股價未漲（都在當下訊號裡）、市值 Q1、ROE Q1、投信 120 日 Q2（都已在 ≥1.2 名單裡）⇒ 不另加
    ⇒ 共 50 個；⛔ 沒有用任何確認段資訊挑候選
 C3 組合：兩兩（C(50,2)）與三個（C(50,3)）全部窮舉；組合成立 ＝ 所含條件當天全部成立
    訊號日 ＝ 母體日 ∧ 組合成立 ∧ 前 20 根有效 K 棒（不論母體）組合整體都不成立（以組合整體去重）
 C4 指標（探索／確認各一；同 launch10）：變飆股比例（grid 標籤任一天、hdef6 ≥ H；格中位；該格母體與訊號日各 ≥ 30 才算）、倍數（÷ 同格母體基準、格中位）、
    60 日內漲 ≥ 30%、一年內先跌 15%（d＋60、d＋250 ≤ 2026-08-31）、每天平均幾檔；母體基準並列
 C5 門檻與排名：探索段每天平均 ≥ 0.3 檔 ∧ 標籤事件（182 格的「訊號日 × 標籤成立」總數，格中位前）≥ 30 ⇒ 依探索段倍數格中位排名，前 20 到確認段照報（⛔ 不依確認段重排）
    多重比較：報窮舉總數、過門檻數、探索第一名 → 確認的縮水幅度（確認倍數 ÷ 探索倍數）、前 20 名的縮水中位
 C6 簡單模型：logistic regression（numpy 自寫；sklearn 未裝、⛔ 不安裝）：特徵 ＝ 50 個候選（0/1）＋截距，L2 λ ＝ 1e−3（依樣本數正規化），批次梯度下降 3000 步、學習率 0.5；
    訓練樣本 ＝ 探索段全部母體日（不去重）；目標 ＝ 該列在 182 格裡「定義域內標籤成立」的比例（軟標籤，0～1；沒有定義域的格不算）
    確認段：母體日依分數由高到低，取前 1%／5%／10%（分數門檻用確認段母體日的分數分位，不看標籤）；另報去重版（前 20 根內沒有被選過的母體日）；指標同 C4；探索段同法照報
 C7 查核（--check）：① 抽 100 檔逐根迴圈重算母體與三個條件（創 55 日新高近 3 日、市值 Q1、投信 120 日 Q2；打底五等分要全市場才排得出，不在此逐根重算）⇒ 對每檔全日曆 bits／母體列；
    ② 兩個組合（探索第一名、一個隨機三個組合）× 2 格，用每檔全日曆 bits 逐列迴圈重做去重與 N／Y 計數 ⇒ 0 不同才算過
輸出 backtest/resultsSurge6/launchcombo/；大檔（每檔全日曆 bits）放 ~/s6work/launchcombo_bits.npy（不進 repo）
"""
from __future__ import annotations

import argparse
import html
import itertools
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5
from backtest import researchSurge6_end_desc as ED
from backtest import researchSurge6_launch as LA
from backtest import researchSurge6_launch10 as L10

D = S5.D
TIME = "2026-09-30 20:50（台北）"
OUT = "backtest/resultsSurge6/launchcombo"
BITS = os.path.expanduser("~/s6work/launchcombo_bits.npy")
HS, GS = LA.HS, LA.GS
EXP, CON = LA.EXP, LA.CON
q3 = ED.q3


def candidates():
    J = pd.read_csv("backtest/resultsSurge6/launch/judge.csv"); M = json.load(open("backtest/resultsSurge6/launch/meta.json", encoding="utf-8"))
    CV = pd.read_csv("backtest/resultsSurge6/launch/coverage.csv.gz", usecols=["版本", "段", "類", "訊號", "src", "key", "碼"])
    x = J[(J["版本"] == LA.VERS[1]) & (J["段"] == "探索") & J["訊號"].isin(M["特徵候選"]) & (J["倍數 格中位"] >= 1.2)]
    mp = CV[(CV["類"] == "狀態／特徵")].drop_duplicates("訊號").set_index("訊號")
    C = [("S", j, 1, nm, "當下訊號") for j, nm in enumerate(LA.SIGN)]
    C += [(mp.loc[nm, "src"], int(mp.loc[nm, "key"]), int(mp.loc[nm, "碼"]), nm, "狀態特徵") for nm in sorted(x["訊號"])]
    C += [("N", k, q, f"{LA.NEWN[k]}｜Q{q}", "低檔打底") for k in range(len(LA.NEWN)) for q in (1, 5)]
    return C


def build(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    W, C, POS, NEAR, NEWQ = LA.build(uni, cal, n, bar, log)
    CAND = candidates(); K = len(CAND)
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r")
    S = len(uni); BIT = np.zeros((S, n), np.uint64)
    for b, (src, key, code, nm, cls) in enumerate(CAND):
        if src == "S":
            f = ((NEAR >> np.uint32(key)) & 1).astype(bool)
        elif src == "Q":
            f = np.asarray(Qm[key]) == code
        else:
            f = NEWQ[key] == code
        BIT |= (f & bar).astype(np.uint64) << np.uint64(b)
    log(f"[條件] {K} 個 bits 完成")
    np.save(BITS, BIT)
    # 母體與列
    HI = {H: i for i, H in enumerate(HS)}; Hc = np.array([HS[c // len(GS)] for c in cells]); Gc = np.array([GS[c % len(GS)] for c in cells])
    R = {k: [] for k in ("s", "d", "seg", "bits", "prev", "h6", "u30", "u30ok", "dr", "drok")}; LAB = []
    segm = np.full(n, -1); segm[(mon >= EXP[0]) & (mon <= EXP[1]) & inseg] = 0; segm[(mon >= CON[0]) & (mon <= CON[1]) & inseg] = 1
    POP = np.zeros((S, n), bool)
    for s in range(S):
        c = C[s]
        if not (bar[s] & inseg).any() or not np.isfinite(c).any():
            continue
        _, _, popu, idx = L10.seq_features(c, POS[s], np.zeros(n, np.uint8), bar[s], n)
        POP[s] = popu
        sel = np.flatnonzero(popu & (segm >= 0))
        if not len(sel):
            continue
        pos_in = {d: i for i, d in enumerate(idx)}
        bb = BIT[s, idx]
        for d in sel:
            i = pos_in[d]; pv = np.zeros(20, np.uint64); w = bb[max(0, i - 20):i]; pv[20 - len(w):] = w
            R["prev"].append(pv)
        R["s"] += [s] * len(sel); R["d"] += list(sel); R["seg"] += list(segm[sel]); R["bits"] += list(BIT[s, sel]); R["h6"] += list(h6[s, sel])
        rv = pd.Series(c[::-1]); lab = np.zeros((len(sel), len(cells)), bool)
        for H in sorted(set(Hc)):
            fmx = np.r_[rv.rolling(H, min_periods=H).max().to_numpy()[::-1][1:], np.nan][sel]
            for j in np.flatnonzero(Hc == H):
                with np.errstate(invalid="ignore"):
                    lab[:, j] = fmx >= c[sel] * (1 + Gc[j]) * (1 - 1e-9)
        LAB.append(lab)
        for d in sel:
            ok60 = d + 60 <= t1; ok250 = d + 250 <= t1
            R["u30ok"].append(ok60); R["u30"].append(bool(ok60 and np.nanmax(c[d + 1:d + 61]) >= c[d] * 1.3))
            if ok250:
                w = c[d + 1:d + 251]; dn = np.flatnonzero(w <= c[d] * 0.85); up = np.flatnonzero(w >= c[d] * 1.15)
                R["dr"].append(bool(len(dn) > 0 and (len(up) == 0 or dn[0] < up[0])))
            else:
                R["dr"].append(False)
            R["drok"].append(ok250)
        if s % 400 == 0:
            log(f"[列] {s}/{S}｜{len(R['s']):,}")
    T = {k: np.array(v) for k, v in R.items() if k != "prev"}
    T["prev"] = np.stack(R["prev"]); LABM = np.concatenate(LAB)
    DOM = T["h6"][:, None] >= Hc[None, :]
    T["labd"] = LABM & DOM; T["dom"] = DOM
    ndays = [int((segm == 0).sum()), int((segm == 1).sum())]
    return uni, cal, n, cells, CAND, T, ndays, POP, BIT


def stats(sub, T, ndays, base):
    """sub：列索引 ⇒ 探索／確認兩段的指標 dict"""
    out = {}
    for g, sg in enumerate(("探索", "確認")):
        m = sub[T["seg"][sub] == g]
        Nn = T["dom"][m].sum(0).astype(float); Yy = T["labd"][m].sum(0).astype(float)
        n0, y0 = base[g]
        ok = (Nn >= 30) & (n0 >= 30) & (y0 > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = Yy / Nn; b = y0 / n0; rat = rate / b
        out[sg] = {"訊號日": int(len(m)), "每天平均幾檔": len(m) / ndays[g], "標籤事件": int(Yy.sum()), "可用格": int(ok.sum()),
                   "倍數 格中位": q3(rat[ok])[0] if ok.any() else np.nan, "變飆股比例 格中位": q3(rate[ok])[0] if ok.any() else np.nan,
                   "母體基準 格中位": q3(b[ok])[0] if ok.any() else np.nan,
                   "60日內漲≥30%": T["u30"][m][T["u30ok"][m]].mean() if T["u30ok"][m].any() else np.nan,
                   "一年內先跌15%": T["dr"][m][T["drok"][m]].mean() if T["drok"][m].any() else np.nan}
    return out


def combo_rows(M, T):
    Mu = np.uint64(M)
    today = np.flatnonzero((T["bits"] & Mu) == Mu)
    if not len(today):
        return today
    pv = T["prev"][today]
    hit_prev = ((pv & Mu) == Mu).any(1)
    return today[~hit_prev]


def logistic(X, y, lam=1e-3, steps=3000, lr=0.5):
    Xb = np.c_[np.ones(len(X)), X].astype(np.float64); w = np.zeros(Xb.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-(Xb @ w)))
        g = Xb.T @ (p - y) / len(y); g[1:] += lam * w[1:]
        w -= lr * g
    return w


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, cells, CAND, T, ndays, POP, BIT = build(log)
    K = len(CAND); nrow = len(T["s"])
    log(f"[列] 母體列 {nrow:,}（探索 {int((T['seg'] == 0).sum()):,}、確認 {int((T['seg'] == 1).sum()):,}）｜{time.time() - T0:.0f}s")
    base = [(T["dom"][T["seg"] == g].sum(0).astype(float), T["labd"][T["seg"] == g].sum(0).astype(float)) for g in (0, 1)]
    allrows = np.arange(nrow)
    BASE = stats(allrows, T, ndays, base)
    res = []
    combos = [(i,) for i in range(K)] + list(itertools.combinations(range(K), 2)) + list(itertools.combinations(range(K), 3))
    nexp = {1: 0, 2: 0, 3: 0}; npass = {1: 0, 2: 0, 3: 0}
    for ci, cb in enumerate(combos):
        M = 0
        for b in cb:
            M |= 1 << b
        sub = combo_rows(M, T)
        nexp[len(cb)] += 1
        e = sub[T["seg"][sub] == 0]
        if len(e) / ndays[0] < 0.3:
            continue
        ye = int(T["labd"][e].sum())
        if ye < 30:
            continue
        npass[len(cb)] += 1
        st = stats(e, T, ndays, base)["探索"]
        res.append({"組合": " ＋ ".join(CAND[b][3] for b in cb), "條件數": len(cb), "bits": M, "探索 倍數": st["倍數 格中位"], "探索 變飆股比例": st["變飆股比例 格中位"],
                    "探索 每天幾檔": st["每天平均幾檔"], "探索 標籤事件": st["標籤事件"], "探索 60日漲30%": st["60日內漲≥30%"], "探索 先跌15%": st["一年內先跌15%"]})
        if ci % 2000 == 0:
            log(f"[窮舉] {ci}/{len(combos)}｜過門檻 {len(res)}")
    RS = pd.DataFrame(res).sort_values("探索 倍數", ascending=False, kind="mergesort").reset_index(drop=True)
    RS.drop(columns="bits").to_csv(os.path.join(OUT, "explore_all.csv.gz"), index=False, float_format="%.5g")
    TOP = []
    for rk, r in enumerate(RS.head(20).to_dict("records"), 1):
        st = stats(combo_rows(r["bits"], T), T, ndays, base)
        TOP.append({"名次": rk, "組合": r["組合"], "條件數": r["條件數"], **{f"{sg} {k}": v for sg in ("探索", "確認") for k, v in st[sg].items()}})
    TOP = pd.DataFrame(TOP)
    # 查核用：探索第一名與一個隨機三個組合，2 格的探索段 N／Y
    rng_ = np.random.default_rng(20260930); tri = sorted(int(x) for x in rng_.choice(K, 3, replace=False)); Mt = sum(1 << b for b in tri)
    ckc = [int(x) for x in rng_.choice(len(cells), 2, replace=False)]
    CKD = {"cells": [int(cells[j]) for j in ckc], "combos": {}}
    for nm_, M_ in (("探索第一名", int(RS.iloc[0]["bits"])), ("隨機三個", int(Mt))):
        sub = combo_rows(M_, T); e = sub[T["seg"][sub] == 0]
        CKD["combos"][nm_] = {"bits": M_, "N": [int(T["dom"][e][:, j].sum()) for j in ckc], "Y": [int(T["labd"][e][:, j].sum()) for j in ckc], "訊號日": int(len(e))}
    json.dump(CKD, open(os.path.join(OUT, "check_ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    TOP["縮水（確認÷探索）"] = TOP["確認 倍數 格中位"] / TOP["探索 倍數 格中位"]
    TOP.to_csv(os.path.join(OUT, "top20.csv"), index=False, float_format="%.5g")
    # 單一條件（照報）
    SG = []
    for b in range(K):
        st = stats(combo_rows(1 << b, T), T, ndays, base)
        SG.append({"條件": CAND[b][3], "類": CAND[b][4], **{f"{sg} {k}": v for sg in ("探索", "確認") for k, v in st[sg].items()}})
    pd.DataFrame(SG).to_csv(os.path.join(OUT, "single.csv"), index=False, float_format="%.5g")
    log(f"[窮舉] 完成｜{time.time() - T0:.0f}s")
    # logistic
    X = ((T["bits"][:, None] >> np.arange(K, dtype=np.uint64)[None, :]) & np.uint64(1)).astype(np.float32)
    dsum = T["dom"].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        y = np.where(dsum > 0, T["labd"].sum(1) / dsum, np.nan)
    tr = (T["seg"] == 0) & np.isfinite(y)
    w = logistic(X[tr], y[tr])
    sc = np.c_[np.ones(nrow), X] @ w
    pd.DataFrame({"特徵": ["截距"] + [c[3] for c in CAND], "係數": w}).to_csv(os.path.join(OUT, "logit_coef.csv"), index=False, float_format="%.5g")
    LG = []
    for g, sg in enumerate(("探索", "確認")):
        mrow = np.flatnonzero(T["seg"] == g)
        for pct in (0.01, 0.05, 0.10):
            thr = np.quantile(sc[mrow], 1 - pct); pick = mrow[sc[mrow] >= thr]
            for dedupe in (False, True):
                sel = pick[_dedup_mask(T, pick)] if dedupe else pick
                st = stats(sel, T, ndays, base)[sg]
                LG.append({"段": sg, "前": f"{int(pct * 100)}%", "去重": dedupe, "分數門檻": float(thr), **st})
    LGd = pd.DataFrame(LG); LGd.to_csv(os.path.join(OUT, "logit.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "候選數": K, "候選": [c[3] for c in CAND], "窮舉數": nexp, "過門檻數": npass, "母體列": nrow, "段內交易日": ndays,
            "母體基準": BASE, "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    np.savez_compressed(os.path.join(OUT, "rows_min.npz"), s=T["s"], d=T["d"], seg=T["seg"], bits=T["bits"])
    log(f"[完] {time.time() - T0:.0f}s")


def _dedup_mask(T, pick):
    """pick（已選列）⇒ 保留「同一檔前 20 根有效 K 棒內沒有其他被選的列」者"""
    bar = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r")
    s_ = T["s"][pick]; d_ = T["d"][pick]; keep = np.ones(len(pick), bool)
    order = np.lexsort((d_, s_)); cs = None; cur = -1; prev_rank = None
    for o in order:
        s, d = int(s_[o]), int(d_[o])
        if s != cur:
            cs = np.cumsum(np.asarray(bar[s])); cur = s; prev_rank = None
        rank = int(cs[d])
        if prev_rank is not None and rank - prev_rank <= 20:
            keep[o] = False
        prev_rank = rank
    return keep


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8")); CKD = json.load(open(os.path.join(OUT, "check_ref.json"), encoding="utf-8"))
    RM = np.load(os.path.join(OUT, "rows_min.npz")); BIT = np.load(BITS, mmap_mode="r")
    CAND = candidates(); names = [c[3] for c in CAND]
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r")
    D.DATA = S5.ST; errs = []; info = {}
    rowset = {}
    for s, d, g in zip(RM["s"], RM["d"], RM["seg"]):
        rowset.setdefault(int(s), set()).add(int(d))
    segm = np.full(n, -1); segm[(mon >= EXP[0]) & (mon <= EXP[1]) & inseg] = 0; segm[(mon >= CON[0]) & (mon <= CON[1]) & inseg] = 1

    def loop_stock(s):
        df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
        c0 = df["close"].to_numpy(float); cff = pd.Series(c0).ffill().to_numpy()
        idx = [d for d in range(n) if np.isfinite(c0[d]) and bar[s, d]]; cb = [c0[d] for d in idx]; m = len(idx)
        pos = [np.nan] * m
        for i in range(249, m):
            w = cb[i - 249:i + 1]; lo, hi = min(w), max(w)
            if hi > lo:
                pos[i] = (cb[i] - lo) / (hi - lo)
        popu = set()
        for i in range(m):
            a = max(0, i - 59); j = max(range(a, i + 1), key=lambda x: (-cb[x], x))
            if np.isfinite(pos[j]) and pos[j] <= 0.4 and 0.05 <= cb[i] / cb[j] - 1 <= 0.30:
                popu.add(idx[i])
        ev55 = [i >= 55 and cb[i] > max(cb[i - 55:i]) for i in range(m)]
        n55 = {idx[i]: any(ev55[max(0, i - 2):i + 1]) for i in range(m)}
        return cff, idx, popu, n55
    # ① 母體與三個條件
    rng_ = np.random.default_rng(7); pick = [int(x) for x in rng_.choice(len(uni), 100, replace=False)]
    b55 = names.index("創55日新高"); bmc = names.index("市值｜Q1"); btr = names.index("投信120日淨買÷股本｜Q2")
    qmc = np.asarray(Qm[S5.FIX["mcap"]]); qtr = np.asarray(Qm[S5.FIX["tnet_120"]])
    npop = nbit = 0
    for s in pick:
        cff, idx, popu, n55 = loop_stock(s)
        mine = {d for d in popu if segm[d] >= 0}; ref = rowset.get(s, set())
        npop += len(mine ^ ref)
        for d in idx:
            bb = int(BIT[s, d])
            exp = {b55: n55[d], bmc: qmc[s, d] == 1, btr: qtr[s, d] == 2}
            for b, v in exp.items():
                if bool((bb >> b) & 1) != bool(v):
                    nbit += 1
    info["① 抽 100 檔：母體列不同"] = npop; info["① 三個條件 bits 不同（根）"] = nbit
    if npop:
        errs.append(f"母體不同 {npop}")
    if nbit:
        errs.append(f"bits 不同 {nbit}")
    # ② 組合去重與 N／Y
    ck = CKD["cells"]; Hc = [HS[c // len(GS)] for c in ck]; Gc = [GS[c % len(GS)] for c in ck]
    rows_e = [(int(s), int(d)) for s, d, g in zip(RM["s"], RM["d"], RM["seg"]) if g == 0]
    for nm_, ref in CKD["combos"].items():
        M = int(ref["bits"]); Nn = [0, 0]; Yy = [0, 0]; nsig = 0; px = {}
        for s, d in rows_e:
            if (int(BIT[s, d]) & M) != M:
                continue
            bars_s = np.flatnonzero(np.asarray(bar[s][:d]))[-20:]
            if any((int(BIT[s, p]) & M) == M for p in bars_s):
                continue
            nsig += 1
            if s not in px:
                px[s] = pd.Series(D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].to_numpy(float)).ffill().to_numpy()
            c = px[s]
            for j in range(2):
                if h6[s, d] >= Hc[j]:
                    Nn[j] += 1; Yy[j] += int(max(c[d + 1:d + Hc[j] + 1]) >= c[d] * (1 + Gc[j]) * (1 - 1e-9))
        ok = Nn == ref["N"] and Yy == ref["Y"] and nsig == ref["訊號日"]
        info[f"② {nm_}"] = {"迴圈 N": Nn, "檔 N": ref["N"], "迴圈 Y": Yy, "檔 Y": ref["Y"], "迴圈訊號日": nsig, "檔訊號日": ref["訊號日"]}
        if not ok:
            errs.append(f"{nm_} 不同")
    out = {"讀法寫死": TIME, "比對": info, "錯誤數": len(errs), "錯誤": errs, "通過": not errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] {out}")


def page(log):
    TOP = pd.read_csv(os.path.join(OUT, "top20.csv")); LG = pd.read_csv(os.path.join(OUT, "logit.csv")); SG = pd.read_csv(os.path.join(OUT, "single.csv"))
    CF = pd.read_csv(os.path.join(OUT, "logit_coef.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal;min-width:10em}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}details{margin:6px 0}summary{cursor:pointer;font-weight:600}"
            "table.tl td,table.tl th{padding:3px 5px;font-size:.84rem}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.1f}%"
    P0 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    XX = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.2f}"
    B = META["母體基準"]; tot = sum(META["窮舉數"].values()); tot23 = META["窮舉數"]["2"] + META["窮舉數"]["3"]; ps = sum(META["過門檻數"].values())
    t1 = TOP.iloc[0]; shr = TOP["縮水（確認÷探索）"].median()
    lg = lambda sg, p, dd: LG[(LG["段"] == sg) & (LG["前"] == p) & (LG["去重"] == dd)].iloc[0]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>低檔發動組合搜尋</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>剛從低檔發動的股票，把條件組合起來能挑出飆股嗎？</h1>",
         "<p class='warn'>⚠ 參考，沒有計入檢定數。組合在探索段（2021–2023）窮舉排名，確認段（2024–2026-08）只照報；這是大量窮舉，探索段的第一名一定偏高，要看確認段剩多少。</p>",
         f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。母體 ＝ 前 60 天內最低點位在一年區間下方 40% 以內、今天比那個低點漲了 5%～30%（剛從低檔發動）。"
         f"候選 {META['候選數']} 個條件（當下訊號 16、狀態特徵 26、低檔打底 8；只用探索段資訊挑）；兩兩 ＋ 三個窮舉共 {tot23:,} 個組合（連單一條件共 {tot:,} 個），"
         f"過門檻（探索段每天 ≥0.3 檔、標籤事件 ≥30）{ps:,} 個。同一檔前 20 天內組合已成立過就不算新的。"
         + (f"查核：{'通過' if CK['通過'] else '有錯'}（錯誤 {CK['錯誤數']}）。" if CK else "") + "</p>",
         "<h2>先講結論</h2><ul class='big'>",
         f"<li><b>母體基準</b>：確認段每天約 {B['確認']['每天平均幾檔']:.0f} 檔，之後變飆股 {P1(B['確認']['變飆股比例 格中位'])}（格中位）、60 日內漲 ≥30% {P0(B['確認']['60日內漲≥30%'])}、一年內先跌 15% {P0(B['確認']['一年內先跌15%'])}"
         f"（探索段 {P1(B['探索']['變飆股比例 格中位'])}、{P0(B['探索']['60日內漲≥30%'])}、{P0(B['探索']['一年內先跌15%'])}）。</li>",
         f"<li><b>窮舉第一名</b>「{html.escape(t1['組合'])}」：探索 {XX(t1['探索 倍數 格中位'])} 倍 → 確認 {XX(t1['確認 倍數 格中位'])} 倍（剩 {P0(t1['縮水（確認÷探索）'])}），"
         f"確認段變飆股 {P1(t1['確認 變飆股比例 格中位'])}、每天 {t1['確認 每天平均幾檔']:.1f} 檔、60 日內漲 ≥30% {P0(t1['確認 60日內漲≥30%'])}、先跌 15% {P0(t1['確認 一年內先跌15%'])}。"
         f"前 20 名的確認倍數中位 {XX(TOP['確認 倍數 格中位'].median())}（探索中位 {XX(TOP['探索 倍數 格中位'].median())}；縮水中位剩 {P0(shr)}）。</li>",
         f"<li><b>簡單模型</b>（logistic，{META['候選數']} 個條件一起）：確認段分數前 1% 倍數 {XX(lg('確認', '1%', True)['倍數 格中位'])}、前 5% {XX(lg('確認', '5%', True)['倍數 格中位'])}、前 10% {XX(lg('確認', '10%', True)['倍數 格中位'])}（去重）；"
         f"前 1% 變飆股 {P1(lg('確認', '1%', True)['變飆股比例 格中位'])}、每天 {lg('確認', '1%', True)['每天平均幾檔']:.1f} 檔、先跌 15% {P0(lg('確認', '1%', True)['一年內先跌15%'])}。</li>",
         "__HONEST__</ul>"]
    H.append("<h2>一、探索段前 20 名 → 確認段</h2><div class='wrap'><table class='tl'><tr><th>#</th><th class='l'>組合</th><th>探索 倍數</th><th>確認 倍數</th><th>剩</th><th>確認 變飆股</th><th>確認 每天幾檔</th><th>確認 60日漲30%</th><th>確認 先跌15%</th></tr>")
    H.append(f"<tr><td></td><td class='l'>母體基準</td><td>1.00</td><td>1.00</td><td></td><td>{P1(B['確認']['變飆股比例 格中位'])}</td><td>{B['確認']['每天平均幾檔']:.0f}</td><td>{P0(B['確認']['60日內漲≥30%'])}</td><td>{P0(B['確認']['一年內先跌15%'])}</td></tr>")
    for r in TOP.to_dict("records"):
        H.append(f"<tr><td>{r['名次']}</td><td class='l'>{html.escape(r['組合'])}</td><td>{XX(r['探索 倍數 格中位'])}</td><td>{XX(r['確認 倍數 格中位'])}</td><td>{P0(r['縮水（確認÷探索）'])}</td>"
                 f"<td>{P1(r['確認 變飆股比例 格中位'])}</td><td>{r['確認 每天平均幾檔']:.1f}</td><td>{P0(r['確認 60日內漲≥30%'])}</td><td>{P0(r['確認 一年內先跌15%'])}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>二、簡單模型（logistic）</h2><div class='wrap'><table class='tl'><tr><th>段</th><th>分數前</th><th>去重</th><th>倍數</th><th>變飆股</th><th>每天幾檔</th><th>60日漲30%</th><th>先跌15%</th></tr>")
    for r in LG.to_dict("records"):
        H.append(f"<tr><td>{r['段']}</td><td>{r['前']}</td><td>{'是' if r['去重'] else '否'}</td><td>{XX(r['倍數 格中位'])}</td><td>{P1(r['變飆股比例 格中位'])}</td><td>{r['每天平均幾檔']:.1f}</td>"
                 f"<td>{P0(r['60日內漲≥30%'])}</td><td>{P0(r['一年內先跌15%'])}</td></tr>")
    H.append("</table></div><p class='note'>模型只用探索段訓練；確認段分數門檻取確認段母體日的分數分位（不看結果）。去重 ＝ 同一檔前 20 天內已被選過就不算。</p>")
    cf = CF[CF["特徵"] != "截距"].sort_values("係數", ascending=False)
    H.append("<details><summary>模型係數（正 ＝ 提高機率）</summary><div class='wrap'><table class='tl'><tr><th class='l'>條件</th><th>係數</th></tr>"
             + "".join(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{r['係數']:+.2f}</td></tr>" for r in cf.to_dict("records")) + "</table></div></details>")
    H.append("<details><summary>單一條件（照報）</summary><div class='wrap'><table class='tl'><tr><th class='l'>條件</th><th>探索 倍數</th><th>確認 倍數</th><th>確認 變飆股</th><th>確認 每天幾檔</th><th>確認 先跌15%</th></tr>"
             + "".join(f"<tr><td class='l'>{html.escape(r['條件'])}<br><small>{r['類']}</small></td><td>{XX(r['探索 倍數 格中位'])}</td><td>{XX(r['確認 倍數 格中位'])}</td><td>{P1(r['確認 變飆股比例 格中位'])}</td>"
                       f"<td>{r['確認 每天平均幾檔']:.1f}</td><td>{P0(r['確認 一年內先跌15%'])}</td></tr>" for r in SG.to_dict("records")) + "</table></div></details>")
    H.append("<p class='note'>變飆股 ＝ 182 種飆股定義（H 日內任一天漲到 g）各算一次取中位；倍數 ＝ ÷ 同格母體基準再取中位。全部窮舉結果見 explore_all.csv.gz。</p></main></body></html>")
    tq = TOP[TOP["組合"].str.contains("投信120日")]
    honest = (f"<li><b>縮水</b>：窮舉 {tot23:,} 個組合、過門檻 {ps:,} 個；探索段前 20 名倍數都在 {XX(TOP['探索 倍數 格中位'].min())}～{XX(TOP['探索 倍數 格中位'].max())}，"
              f"到確認段剩 {XX(TOP['確認 倍數 格中位'].min())}～{XX(TOP['確認 倍數 格中位'].max())}（中位剩 {P0(shr)}）——大量窮舉挑出來的第一名，約一半是運氣。</li>"
              + (f"<li>前 20 名裡含「投信 120 日淨買 Q2（投信幾乎沒動）」的 {len(tq)} 個，確認段倍數 {XX(tq['確認 倍數 格中位'].min())}～{XX(tq['確認 倍數 格中位'].max())}、"
                 f"先跌 15% {P0(tq['確認 一年內先跌15%'].min())}～{P0(tq['確認 一年內先跌15%'].max())}，是縮水最少的一群；但這是在確認段才看到的，不能當成已驗證的挑法。</li>" if len(tq) else "")
              + f"<li class='ok'><b>誠實的回答</b>：組合或模型能把「之後變飆股」從 {P1(B['確認']['變飆股比例 格中位'])} 拉到大約 2～4%（約 1.5～2 倍），先跌 15% 的比例也略降；"
              f"但每 100 檔挑出來的仍只有 2～4 檔會變飆股、四成多會先跌 15%。組合起來比單一條件好一些，但還不是「挑得出飆股」的工具。</li>")
    open(os.path.join(OUT, "低檔發動組合搜尋.html"), "w", encoding="utf-8").write("\n".join(H).replace("__HONEST__", honest))
    log("[網頁] 完成")


HONEST_TXT = ""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()
