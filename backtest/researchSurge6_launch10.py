# -*- coding: utf-8 -*-
"""launch 追加：「漲到 1 成時可以抓到多少？」——召回（低檔發動的飆股在 1 成點以前出現幾成）與精準度（剛從低檔發動的股票出現組合後，幾成真的變飆股）
（參考，⛔ 不計 N；探索 2021-01～2023-12 找、確認 2024-01～2026-08 驗）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_launch10 [--check]

═══ 讀法（寫死於 2026-09-30 20:23（台北），在算任何數字之前）═══
 A1 五個訊號（定義、參數同 researchSurge6_launch L4，當根「發生」）：量 ≥ 前 20 根均量 2 倍｜收盤 ＞ 前 20 根最高收盤｜收盤由 ≤ 布林上軌轉 ＞（20、2σ）｜
    收盤 ＞ 前 55 根最高收盤｜KD 金叉（9 日）；「近 5 日內」＝ 當根與前 4 根有效 K 棒內有發生；組合 k ＝ 五個裡近 5 日內發生過的個數 ≥ k（k＝1～5）
 A2 召回（描述；事後）：對象 ＝ launch V2 事件（起漲日位置 ≤ 0.4），事件 ≥ 30 的格（同 launch）；1 成點 D10 ＝ launch points.npz 的 10% 點、第一頂同 launch
    某訊號在 [t, D10]（含兩端）有發生（組合：該區間內有某天近 5 日同時 ≥ k 個）⇒ 抓到；報比例（格中位，附 p10～p90）
    第一次出現那天：漲到第一頂的幾成 ＝ (c[d] − c[t]) ÷ (c[H1] − c[t])、離 t 幾天；只看 [t, H1] 內第一次出現（沒出現不計），各格事件中位再取格中位；另分探索／確認（依 t）
 A3 精準度（當下可用）：母體 ＝ 有 K 棒、d 在段內的股-日，且 L ＝ [d−59, d]（有效 K 棒）內最低收盤那根（同價取最近）的位置 pos(L) ≤ 0.4
    （pos 同 launch：含該根的 250 根區間；沒值不算）且 c[d] ÷ c[L] − 1 ∈ [5%, 30%]
    訊號日 ＝ 母體日 ∧ 組合在 d 成立 ∧ 前 20 根有效 K 棒內（不論母體）該組合都不成立（去重：只取第一天）；五個單一訊號也用「近 5 日內」＋同一去重
    基準 ＝ 母體日（不去重）；另報「基準（去重）」＝ 母體日且前 20 根不在母體
    報（探索／確認各一）：變飆股比例（grid 標籤：(d, d＋H] 內最高收盤 ≥ c[d](1＋g)(1 − 1e−9)、hdef6 ≥ H，格中位；該格母體與訊號日各 ≥ 30 才算）與倍數（÷ 同格母體基準，格中位）；
    每天平均幾檔；一年內先跌 15%（同 launch L6，d＋250 ≤ 2026-08-31）；60 日內漲 ≥ 30%（(d, d＋60] 內最高收盤 ≥ 1.3 c[d]，d＋60 ≤ 2026-08-31）
 A4 查核（--check）：召回抽 2 格逐事件迴圈重算（量 2 倍、k≥3）；精準度抽 2 格 × 150 檔逐日迴圈重算母體、k≥3 去重訊號日的母體數與標籤數 ⇒ 0 不同才算過
輸出 backtest/resultsSurge6/launch/：entry10_recall.csv、entry10_first.csv、entry10_precision.csv、entry10_meta.json、entry10_check.json、entry10_check_stock.csv.gz
"""
from __future__ import annotations

import argparse
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

D = S5.D
TIME = "2026-09-30 20:23（台北）"
OUT = LA.OUT
HS, GS = LA.HS, LA.GS
SIG5 = [(6, "量≥2倍"), (4, "20日新高"), (8, "布林上軌"), (5, "55日新高"), (1, "KD金叉")]
COLS = ["基準（母體）", "基準（去重）"] + [f"{nm}（近5日）" for _, nm in SIG5] + [f"五個同時 ≥{k} 個（近5日）" for k in range(1, 6)]
EXP, CON = LA.EXP, LA.CON
q3 = ED.q3


def build(uni, cal, n, bar, log):
    W, _ = S5.world(log)
    Fm = np.load(os.path.join(S5.WORK, "F.npy"), mmap_mode="r"); revhi = np.asarray(Fm[S5.FIX["d_revhi"]])
    S = len(uni); C = np.full((S, n), np.nan); POS = np.full((S, n), np.nan); B5 = np.zeros((S, n), np.uint8)
    D.DATA = S5.ST
    for s in range(S):
        sid = uni.loc[s, "stock_id"]
        o = LA.stock_signals(sid, uni.loc[s, "market"], cal, n, bar[s], W, revhi[s], LA.inst_total(sid))
        if o is None:
            continue
        c, pos, base, near, raw = o
        C[s] = c; POS[s] = pos
        for b, (j, nm) in enumerate(SIG5):
            B5[s] |= (base[j].astype(np.uint8) << b)
        if s % 400 == 0:
            log(f"[訊號] {s}/{S}")
    return C, POS, B5


def seq_features(c, pos, b5, bar_s, n):
    """有效 K 棒序列上：近 5 日各訊號、同時個數、母體（剛從低檔發動）⇒ 回傳日曆長度陣列"""
    idx = np.flatnonzero(bar_s & np.isfinite(c))
    m = len(idx); near5 = np.zeros((5, n), bool); cnt = np.zeros(n, np.int8); popu = np.zeros(n, bool)
    if m < 30:
        return near5, cnt, popu, idx
    bb = b5[idx]
    ev = np.stack([((bb >> b) & 1).astype(bool) for b in range(5)])
    nr = ev.copy()
    for sh in range(1, 5):
        nr[:, sh:] |= ev[:, :-sh]
    near5[:, idx] = nr; cnt[idx] = nr.sum(0)
    cb = c[idx]; pb = pos[idx]
    for i in range(m):
        a = max(0, i - 59); w = cb[a:i + 1]; j = a + (len(w) - 1 - int(np.argmin(w[::-1])))
        if np.isfinite(pb[j]) and pb[j] <= 0.4:
            g = cb[i] / cb[j] - 1
            popu[idx[i]] = 0.05 <= g <= 0.30
    return near5, cnt, popu, idx


def dedup(flag, idx, n):
    """flag（日曆長度 bool）⇒ 只留前 20 根有效 K 棒內都不成立的那天"""
    out = np.zeros(n, bool)
    f = flag[idx]; m = len(idx)
    cs = np.r_[0, np.cumsum(f)]
    for i in np.flatnonzero(f):
        a = max(0, i - 20)
        if cs[i] - cs[a] == 0:
            out[idx[i]] = True
    return out


def recall(uni, cal, E, cells, C, B5, bar, VM, PT, H1, mon, log, ck_cells):
    es, ed, ec = E["s"].astype(int), E["d"].astype(int), E["cell"].astype(int)
    v2 = VM[1][es, ed]; D10 = PT[1]; n = C.shape[1]
    names = [nm for _, nm in SIG5] + [f"五個同時 ≥{k} 個（近5日）" for k in range(1, 6)]
    got = np.zeros((len(names), len(es)), bool); fprog = np.full((len(names), len(es)), np.nan); fday = np.full((len(names), len(es)), np.nan)
    for s in np.unique(es[v2]):
        near5, cnt, popu, idx = seq_features(C[s], np.full(n, np.nan), B5[s], bar[s], n)
        ev = np.stack([((B5[s] >> b) & 1).astype(bool) for b in range(5)])
        rows = list(ev) + [cnt >= k for k in range(1, 6)]; c = C[s]
        for i in np.flatnonzero(v2 & (es == s)):
            t, d10, h1 = ed[i], D10[i], H1[i]
            for j, f in enumerate(rows):
                got[j, i] = f[t:d10 + 1].any()
                wf = np.flatnonzero(f[t:h1 + 1])
                if len(wf):
                    d = t + int(wf[0]); fday[j, i] = d - t
                    fprog[j, i] = (c[d] - c[t]) / (c[h1] - c[t]) if c[h1] > c[t] else np.nan
    CKV = {S5.cell_name(c): {nm: float(got[names.index(nm), v2 & (ec == c)].mean()) for nm in ("量≥2倍", "五個同時 ≥3 個（近5日）")} for c in ck_cells}
    REC = []; FIR = []
    for sg, sm in (("全部", np.ones(len(es), bool)), ("探索", (mon[ed] >= EXP[0]) & (mon[ed] <= EXP[1])), ("確認", mon[ed] >= CON[0])):
        m = v2 & sm; cntc = np.bincount(ec[m], minlength=250); cl = [c for c in cells if cntc[c] >= 30]
        for j, nm in enumerate(names):
            r = q3([got[j, m & (ec == c)].mean() for c in cl])
            REC.append({"段": sg, "訊號": nm, "格數": len(cl), "1成點以前抓到 格中位": r[0], "p10": r[1], "p90": r[2]})
            fp = [np.nanmedian(fprog[j, m & (ec == c)]) for c in cl]; fd = [np.nanmedian(fday[j, m & (ec == c)]) for c in cl]
            FIR.append({"段": sg, "訊號": nm, "第一次出現時漲到第一頂的幾成 格中位": q3(fp)[0], "p10": q3(fp)[1], "p90": q3(fp)[2],
                        "第一次出現離t天數 格中位": q3(fd)[0], "在第一頂前有出現 格中位": q3([np.isfinite(fday[j, m & (ec == c)]).mean() for c in cl])[0]})
    return pd.DataFrame(REC), pd.DataFrame(FIR), CKV


def precision(uni, cal, n, inseg, bar, h6, cells, C, POS, B5, mon, t1, log, chk=None):
    J = len(COLS); HI = {H: i for i, H in enumerate(HS)}; cellset = set(cells)
    N = np.zeros((2, len(HS), J)); Y = np.zeros((2, 250, J)); CNT = np.zeros((2, J)); DRn = np.zeros((2, J)); DRd = np.zeros((2, J)); U30n = np.zeros((2, J)); U30d = np.zeros((2, J))
    segm = [(mon >= EXP[0]) & (mon <= EXP[1]) & inseg, (mon >= CON[0]) & (mon <= CON[1]) & inseg]
    CHK = []
    for s in range(len(uni)):
        c = C[s]
        if not (bar[s] & inseg).any() or not np.isfinite(c).any():
            continue
        near5, cnt, popu, idx = seq_features(c, POS[s], B5[s], bar[s], n)
        if not popu.any():
            continue
        cols = [popu, popu & dedup(popu, idx, n)]
        for b in range(5):
            cols.append(popu & dedup(near5[b], idx, n))
        for k in range(1, 6):
            cols.append(popu & dedup(cnt >= k, idx, n))
        dd = np.flatnonzero(bar[s] & inseg); rng = np.arange(dd[0], dd[-1] + 1)
        X = np.stack([x[rng] for x in cols], 1).astype(np.float32)
        grp = np.stack([segm[g][rng] & bar[s, rng] for g in range(2)]).astype(np.float32)
        CNT += grp @ X
        cr = c[rng]; h6s = h6[s, rng]; rv = pd.Series(c[::-1])
        for H in HS:
            fmx = np.r_[rv.rolling(H, min_periods=H).max().to_numpy()[::-1][1:], np.nan][rng]
            G = grp * (h6s >= H).astype(np.float32)[None, :]
            N[:, HI[H], :] += G @ X
            gl = [gi for gi in range(len(GS)) if HI[H] * len(GS) + gi in cellset]
            if not gl:
                continue
            with np.errstate(invalid="ignore"):
                Lb = np.stack([fmx >= cr * (1 + GS[gi]) * (1 - 1e-9) for gi in gl]).astype(np.float32)
            YY = ((G[:, None, :] * Lb[None, :, :]).reshape(-1, len(rng)) @ X).reshape(2, len(gl), J)
            for a_, gi in enumerate(gl):
                Y[:, HI[H] * len(GS) + gi, :] += YY[:, a_, :]
            if chk is not None and s in chk["stocks"]:
                for cc in chk["cells"]:
                    if cc // len(GS) == HI[H]:
                        a_ = gl.index(cc % len(GS))
                        for jn in ("基準（母體）", "五個同時 ≥3 個（近5日）"):
                            jj = COLS.index(jn); CHK.append({"s": s, "cell": cc, "j": jn, "N": float(G[0] @ X[:, jj]), "Y": float(YY[0, a_, jj])})
        # 60 日漲 30%、一年內先跌 15%
        any_ = X.any(1)
        ok60 = (rng + 60 <= t1); ok250 = (rng + 250 <= t1)
        u30 = np.zeros(len(rng), np.float32); dr = np.zeros(len(rng), np.float32)
        for i_ in np.flatnonzero(any_):
            d = rng[i_]
            if ok60[i_]:
                u30[i_] = float(np.nanmax(c[d + 1:d + 61]) >= c[d] * 1.3)
            if ok250[i_]:
                w = c[d + 1:d + 251]; dn = np.flatnonzero(w <= c[d] * 0.85); up = np.flatnonzero(w >= c[d] * 1.15)
                dr[i_] = float(len(dn) > 0 and (len(up) == 0 or dn[0] < up[0]))
        G60 = grp * ok60[None, :]; G250 = grp * ok250[None, :]
        U30d += G60 @ X; U30n += (G60 * u30[None, :]) @ X; DRd += G250 @ X; DRn += (G250 * dr[None, :]) @ X
        if s % 400 == 0:
            log(f"[精準度] {s}/{len(uni)}")
    return N, Y, CNT, DRn, DRd, U30n, U30d, pd.DataFrame(CHK)


def run(log):
    T0 = time.time()
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    C, POS, B5 = build(uni, cal, n, bar, log)
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(S5.WORK, "F.npy"), mmap_mode="r")
    VM = LA.version_masks(POS, np.asarray(Qm[S5.FIX["r_120"]]), np.asarray(Fm[S5.FIX["lu_20"]]))
    PZ = np.load(os.path.join(OUT, "points.npz")); H1, PT = PZ["H1"], PZ["PT"]
    rng_ = np.random.default_rng(20260930); ck_cells = [int(x) for x in rng_.choice(cells, 2, replace=False)]; ck_st = set(int(x) for x in rng_.choice(len(uni), 150, replace=False))
    REC, FIR, CKV = recall(uni, cal, E, cells, C, B5, bar, VM, PT, H1, mon, log, ck_cells)
    REC.to_csv(os.path.join(OUT, "entry10_recall.csv"), index=False, float_format="%.5g"); FIR.to_csv(os.path.join(OUT, "entry10_first.csv"), index=False, float_format="%.5g")
    log(f"[召回] 完成 {time.time() - T0:.0f}s")
    N, Y, CNT, DRn, DRd, U30n, U30d, CHK = precision(uni, cal, n, inseg, bar, h6, cells, C, POS, B5, mon, t1, log, chk={"cells": ck_cells, "stocks": ck_st})
    CHK.to_csv(os.path.join(OUT, "entry10_check_stock.csv.gz"), index=False)
    ndays = [int(((mon >= a) & (mon <= b) & inseg).sum()) for a, b in (EXP, CON)]
    out = []
    for g, sg in enumerate(("探索", "確認")):
        for j, nm in enumerate(COLS):
            rat = []; rate = []; base = []
            for c in cells:
                h = c // len(GS); n0, y0 = N[g, h, 0], Y[g, c, 0]; n1, y1 = N[g, h, j], Y[g, c, j]
                if n0 >= 30 and n1 >= 30 and y0 > 0:
                    rate.append(y1 / n1); base.append(y0 / n0); rat.append((y1 / n1) / (y0 / n0))
            out.append({"段": sg, "訊號": nm, "可用格": len(rat), "倍數 格中位": q3(rat)[0], "倍數 p10": q3(rat)[1], "倍數 p90": q3(rat)[2],
                        "變飆股比例 格中位": q3(rate)[0], "母體基準 格中位": q3(base)[0], "每天平均幾檔": CNT[g, j] / ndays[g],
                        "一年內先跌15%": DRn[g, j] / DRd[g, j] if DRd[g, j] else np.nan, "60日內漲≥30%": U30n[g, j] / U30d[g, j] if U30d[g, j] else np.nan})
    PR = pd.DataFrame(out); PR.to_csv(os.path.join(OUT, "entry10_precision.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "查核格": ck_cells, "查核格召回（各格原值）": CKV, "V2 事件": int(VM[1][E["s"].astype(int), E["d"].astype(int)].sum()), "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "entry10_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[完] {time.time() - T0:.0f}s")


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    meta = json.load(open(os.path.join(OUT, "entry10_meta.json"), encoding="utf-8")); ck = meta["查核格"]
    PZ = np.load(os.path.join(OUT, "points.npz")); PT = PZ["PT"]
    CHK = pd.read_csv(os.path.join(OUT, "entry10_check_stock.csv.gz"))
    REC = pd.read_csv(os.path.join(OUT, "entry10_recall.csv"))
    D.DATA = S5.ST; memo = {}; errs = []; info = {}

    def stock(s):
        """逐根迴圈：還原收盤、量、KD、五訊號（近 5 日）、個數、位置"""
        if s in memo:
            return memo[s]
        df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
        c0 = df["close"].to_numpy(float); h0 = df["high"].to_numpy(float); l0 = df["low"].to_numpy(float); v0 = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
        cff = pd.Series(c0).ffill().to_numpy()
        idx = [d for d in range(n) if np.isfinite(c0[d]) and bar[s, d]]
        cb = [c0[d] for d in idx]; hb = [h0[d] if np.isfinite(h0[d]) else c0[d] for d in idx]; lb = [l0[d] if np.isfinite(l0[d]) else c0[d] for d in idx]
        vb = [0.0 if not np.isfinite(v0[d]) else v0[d] for d in idx]; m = len(idx)
        ev = [[False] * m for _ in range(5)]
        K = [np.nan] * m; Dd = [np.nan] * m; k0 = d0 = 50.0
        for i in range(8, m):
            lo, hi = min(lb[i - 8:i + 1]), max(hb[i - 8:i + 1]); rsv = 50.0 if hi - lo <= 0 else (cb[i] - lo) / (hi - lo) * 100
            k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3; K[i] = k0; Dd[i] = d0
        for i in range(1, m):
            if i >= 20:
                vm = sum(vb[i - 20:i]) / 20; ev[0][i] = vm > 0 and vb[i] >= 2 * vm
                ev[1][i] = cb[i] > max(cb[i - 20:i])
                ma = sum(cb[i - 19:i + 1]) / 20; sd = float(np.std(cb[i - 19:i + 1]))
                if i >= 20:
                    map_ = sum(cb[i - 20:i]) / 20; sdp = float(np.std(cb[i - 20:i]))
                    ev[2][i] = cb[i] > ma + 2 * sd and cb[i - 1] <= map_ + 2 * sdp and i - 1 >= 19
            if i >= 55:
                ev[3][i] = cb[i] > max(cb[i - 55:i])
            if i >= 9 and np.isfinite(K[i - 1]):
                ev[4][i] = K[i] > Dd[i] and K[i - 1] <= Dd[i - 1]
        near = [[any(ev[b][max(0, i - 4):i + 1]) for i in range(m)] for b in range(5)]
        cntk = [sum(near[b][i] for b in range(5)) for i in range(m)]
        pos = [np.nan] * m
        for i in range(249, m):
            w = cb[i - 249:i + 1]; lo, hi = min(w), max(w)
            if hi > lo:
                pos[i] = (cb[i] - lo) / (hi - lo)
        popu = [False] * m
        for i in range(m):
            a = max(0, i - 59); j = max(range(a, i + 1), key=lambda x: (-cb[x], x))
            if np.isfinite(pos[j]) and pos[j] <= 0.4:
                g = cb[i] / cb[j] - 1; popu[i] = 0.05 <= g <= 0.30
        memo[s] = (cff, idx, ev, near, cntk, popu); return memo[s]
    # 召回：量 2 倍、k≥3
    es, ed, ec = E["s"].astype(int), E["d"].astype(int), E["cell"].astype(int)
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r")
    for c in ck:
        k = np.flatnonzero(ec == c); hv = {"量≥2倍": [], "五個同時 ≥3 個（近5日）": []}
        for i in k:
            s, t = int(es[i]), int(ed[i]); cff, idx, ev, near, cntk, popu = stock(s); pos_t = None
            ix = {d: j for j, d in enumerate(idx)}
            if t not in ix or ix[t] < 249:
                continue
            j = ix[t]; w = [cff[d] for d in idx[j - 249:j + 1]]; lo, hi = min(w), max(w)
            if not (hi > lo and (cff[t] - lo) / (hi - lo) <= 0.4):
                continue
            d10 = int(PT[1, i]); js = [ix[d] for d in range(t, d10 + 1) if d in ix]
            hv["量≥2倍"].append(any(ev[0][q] for q in js)); hv["五個同時 ≥3 個（近5日）"].append(any(cntk[q] >= 3 for q in js))
        ref = meta["查核格召回（各格原值）"][S5.cell_name(c)]
        for kk, v in hv.items():
            mine = float(np.mean(v)) if v else None
            if mine is None or not np.isclose(mine, ref[kk], rtol=1e-9):
                errs.append(f"召回 {S5.cell_name(c)} {kk}：迴圈 {mine} 檔 {ref[kk]}")
        info[f"召回 格 {S5.cell_name(c)}"] = {kk: (float(np.mean(v)) if v else None, len(v)) for kk, v in hv.items()}
    # 精準度：探索段、母體與 k≥3 去重
    nb = 0
    for (s, cc), g in CHK.groupby(["s", "cell"]):
        s = int(s); cc = int(cc); cff, idx, ev, near, cntk, popu = stock(s); H = HS[cc // len(GS)]; gg = GS[cc % len(GS)]
        res = {"基準（母體）": [0, 0], "五個同時 ≥3 個（近5日）": [0, 0]}
        for j, d in enumerate(idx):
            if not (inseg[d] and EXP[0] <= mon[d] <= EXP[1] and h6[s, d] >= H and popu[j]):
                continue
            lab = max(cff[d + 1:d + H + 1]) >= cff[d] * (1 + gg) * (1 - 1e-9)
            res["基準（母體）"][0] += 1; res["基準（母體）"][1] += int(lab)
            if cntk[j] >= 3 and not any(cntk[q] >= 3 for q in range(max(0, j - 20), j)):
                res["五個同時 ≥3 個（近5日）"][0] += 1; res["五個同時 ≥3 個（近5日）"][1] += int(lab)
        for r in g.to_dict("records"):
            a = res[r["j"]]
            if not (a[0] == int(r["N"]) and a[1] == int(r["Y"])):
                nb += 1; errs.append(f"股 {s} 格 {S5.cell_name(cc)} {r['j']}：迴圈 {a} 檔 {r['N']:.0f}/{r['Y']:.0f}")
    info["精準度抽樣 股×格×欄"] = int(len(CHK)); info["精準度不同"] = nb
    out = {"讀法寫死": TIME, "比對": info, "錯誤數": len(errs), "錯誤": errs[:20], "通過": len(errs) == 0}
    json.dump(out, open(os.path.join(OUT, "entry10_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 錯誤 {len(errs)}｜{errs[:3]}｜{info}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    T0 = time.time(); logf = open(os.path.join(OUT, "entry10_run_check.log" if a.check else "entry10_run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
