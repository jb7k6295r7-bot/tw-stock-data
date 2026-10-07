# -*- coding: utf-8 -*-
"""USREG-A4-11 機器學習改目標（台股 PREREG機器學習改目標 seq1 sha 168560f97763a287；只跑 numpy 版，seq319 Q9；seq1 78af 暫停、不計 N）。

台股原件程式：researchMLx（目標、模型、滾動、選股）＋ researchMLlite（特徵）⇒ 移植（模型函式逐式照抄、⛔ 不 import 台股資料模組）。
═══ 執行者補讀法（寫死於 2026-10-07 11:54（台北）；寫死前 ⛔ 沒看任何 A4-11 輸出）═══
 M1 換股日 ＝ G8 月初 e；頻率 月／季（1、4、7、10）／半年（1、7）；量測日 m ＝ e−1（台股 MLlite 同：日曆位置、ffill 還原收盤、m 須有有效 K 棒）。
 M2 特徵（台股 26 個 ⇒ 美股 24 個；照 prep 清單換／拿掉）：
    r1／r3／r6／r12（21／63／126／252 根）、r3s／r6s／r12s（跳過最近 21 根）、dist250、bull（收 ＞ MA20 ＞ MA60）、vol60、
    ivol60（60 日日報酬對 ^SP500TR 日報酬迴歸殘差標準差，≥ 40 筆）、vratio（20 日均量 ÷ 250 日均量）、turn20（20 日均量 ÷ 今日基準股數，＝ prep to20）、
    amihud20（20 日 |日報酬| ÷（還原收盤 × 量）平均，≥ 10 筆）、yoy（季營收年增）、hi24 ⇒ 創 8 季新高、dist24 ⇒ 距 8 季最高、yoystreak ⇒ 連續年增季數、
    Q1 ROE、Q2 營業利益÷資產、Q3 ROA、Q4 研發強度、rqoq（季營收季增）、logcap（log 市值，G10）；投信、外資近 20 日淨買 ⇒ 拿掉（籌碼）。
    每期橫斷面 rank01；缺 ⇒ 0.5 ＋ 缺值旗標（全為 0 的旗標欄丟掉，台股同）。
 M3 目標：ret ＝ CF[x] ÷ O[e] − 1（x ＝ 下一換股日前一交易日）；A ＝ ret − 基準同期（^SP500TR 收盤[x] ÷ 收盤[e−1] − 1；⚠ 基準只有收盤 ⇒ 用 e−1 收盤代 e 開盤，逐字標），
    每期 1%／99% 截尾；B ＝ 當期平均名次 ÷ 件數 ＞ 0.8；C ＝ rank01(ret)、選股時依 vol60 分五組各取 N÷5。
 M4 訓練起點 ＝ 月頻 r12s 可算比例首次 ≥ 50% 的 e（台股同規則；台股為 2016-03-02，美股價格面板 2015-12 起 ⇒ 依構造較晚，照實報）～2017-12；
    驗證 2018（訓練列 tend ＜ 該頻率 2018 第一個換股日）：每期 Spearman(預測, ret) 平均最高者（同分取 α 小／輪數少）；2019 起每年第一個換股日擴張重訓。
 M5 模型（台股 researchMLx 逐式）：嶺迴歸 α ∈ {1, 10, 100}；樹樁 深度 1、學習率 0.1、輪數 {50, 100, 200}（同一條 200 輪路徑截斷）、每葉 ≥ 200、
    切點 ＝ 排名特徵 floor(x×10)、旗標 0.5；A、C 平方損失、B 對數損失（Newton 葉值）。
 M6 訓練一次、用合併母體的列（三欄共用同一個模型）；選股時只從「該欄母體」的列取預測最高前 N（同分依代號）——⭐ 同一條規則、不同候選池（執行者補）。
 M7 組合：換股簿 sim_book（續抱仍入選）；從 2019 第一個換股日起；探索 2019-01～2021-12 挑格（去退化：平均持股 ＜ N÷2 或現金 ＞ 30%）、確認 2022-01～2026-09 判。
    36 格 ＝ 目標 3 × 模型 2 × 頻率 3 × N 2。對照：同池隨機 reps 次（挑中格頻率、N）⇒ p。必報：持股 vol60 百分位、特徵重要度前 10、樣本外 IC。
    判定上限：台股原登錄 ⇒「確認段合格（無早年段）」⇒ 合格也只進前瞻紀錄。
"""
from __future__ import annotations

import math
import os
import time
from collections import defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backtest import researchUSA4 as C
from backtest import researchUSA4_items as IT

FREQ = {"月": tuple(range(1, 13)), "季": (1, 4, 7, 10), "半年": (1, 7)}
TARGETS = ("A", "B", "C")
ALPHAS = (1.0, 10.0, 100.0)
ROUNDS = (50, 100, 200)
LR, NB, MINLEAF = 0.1, 10, 200
NS = (10, 20)
FEATS = ["r1", "r3", "r6", "r12", "r3s", "r6s", "r12s", "dist250", "bull", "vol60", "ivol60", "vratio", "turn20", "amihud20",
         "yoy", "hi24", "dist24", "yoystreak", "Q1", "Q2", "Q3", "Q4", "rqoq", "logcap"]
_G: dict = {}


# ═════════════ 模型（台股 researchMLlite／researchMLx 逐式）═════════════
def rank01(x):
    x = np.asarray(x, float); out = np.full(len(x), np.nan); ok = np.isfinite(x)
    if ok.sum() >= 2:
        r = pd.Series(x[ok]).rank(method="average").to_numpy()
        out[ok] = (r - 1) / (ok.sum() - 1)
    elif ok.sum() == 1:
        out[ok] = 0.5
    return out


def ridge_fit(X, y, alpha):
    mu = X.mean(0); sd = X.std(0); sd = np.where(sd > 0, sd, 1.0); Z = (X - mu) / sd; Z[:, X.std(0) == 0] = 0.0
    ym = y.mean()
    A = Z.T @ Z + alpha * np.eye(Z.shape[1]); b = np.linalg.solve(A, Z.T @ (y - ym))
    return {"mu": mu, "sd": sd, "zero": X.std(0) == 0, "b": b, "c": ym}


def ridge_pred(M, X):
    Z = (X - M["mu"]) / M["sd"]; Z[:, M["zero"]] = 0.0
    return Z @ M["b"] + M["c"]


def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3:
        return np.nan
    return float(pd.Series(a[ok]).rank().corr(pd.Series(b[ok]).rank()))


def bins_of(X, isflag):
    B = np.empty(X.shape, np.int16)
    for j in range(X.shape[1]):
        B[:, j] = (X[:, j] >= 0.5).astype(np.int16) if isflag[j] else np.clip(np.floor(X[:, j] * NB), 0, NB - 1).astype(np.int16)
    return B


def stump_fit(B, y, isflag, logloss, nrounds=max(ROUNDS)):
    n, p = B.shape
    nbins = [2 if isflag[j] else NB for j in range(p)]
    if logloss:
        pb = float(np.clip(y.mean(), 1e-9, 1 - 1e-9)); f0 = math.log(pb / (1 - pb))
    else:
        f0 = float(y.mean())
    F = np.full(n, f0); trees = []; gain = np.zeros(p)
    cnts = [np.cumsum(np.bincount(B[:, j], minlength=nbins[j])) for j in range(p)]
    for _ in range(nrounds):
        if logloss:
            pr = 1.0 / (1.0 + np.exp(-F)); r = y - pr; h = pr * (1 - pr)
        else:
            r = y - F; h = None
        S = r.sum(); best = (-np.inf, -1, -1)
        for j in range(p):
            nb = nbins[j]
            cs = np.cumsum(np.bincount(B[:, j], weights=r, minlength=nb)); cn = cnts[j]
            for t in range(nb - 1):
                nl = cn[t]; nr = n - nl
                if nl < MINLEAF or nr < MINLEAF:
                    continue
                sl = cs[t]; g = sl * sl / nl + (S - sl) ** 2 / nr - S * S / n
                if g > best[0] + 1e-15:
                    best = (g, j, t)
        g, j, t = best
        if j < 0:
            break
        L = B[:, j] <= t
        if logloss:
            vl = r[L].sum() / max(h[L].sum(), 1e-12); vr = r[~L].sum() / max(h[~L].sum(), 1e-12)
        else:
            vl = r[L].mean(); vr = r[~L].mean()
        F = F + LR * np.where(L, vl, vr)
        trees.append((j, t, LR * vl, LR * vr)); gain[j] += g
    return {"f0": f0, "trees": trees, "gain": gain}


def stump_pred(M, B, k=None):
    out = np.full(B.shape[0], M["f0"])
    for j, t, vl, vr in M["trees"][:k]:
        out = out + np.where(B[:, j] <= t, vl, vr)
    return out


# ═════════════ 特徵 ═════════════
def tech_feats(X, e, js, br):
    Wd = X["Wd"]; CF = Wd["CF"]; valid = Wd["valid"]; first = Wd["first"]
    V = Wd["V"]; Cc = Wd["C"]
    m = e - 1
    out = np.full((len(js), 14), np.nan)
    for i, j in enumerate(js):
        fb = first[j]
        if m < fb or not valid[m, j]:
            continue
        c = CF[:, j]

        def R(a, b):
            return c[b] / c[a] - 1.0 if a >= fb and c[a] > 0 else np.nan
        r = [R(m - w, m) for w in (21, 63, 126, 252)] + [R(m - 21 - w, m - 21) for w in (63, 126, 252)]
        d250 = c[m] / np.max(c[m - 249:m + 1]) - 1.0 if m - 249 >= fb else np.nan
        ma20 = c[m - 19:m + 1].mean() if m - 19 >= fb else np.nan
        ma60 = c[m - 59:m + 1].mean() if m - 59 >= fb else np.nan
        bull = float(c[m] > ma20 > ma60) if np.isfinite(ma60) else np.nan
        if m - 60 >= fb:
            dr = c[m - 59:m + 1] / c[m - 60:m] - 1.0; bb = br[m - 59:m + 1]; ok = np.isfinite(dr) & np.isfinite(bb)
            v60 = float(np.std(dr[ok], ddof=1)) if ok.sum() >= 40 else np.nan
            if ok.sum() >= 40:
                A = np.column_stack([np.ones(ok.sum()), bb[ok]]); beta, *_ = np.linalg.lstsq(A, dr[ok], rcond=None)
                iv = float(np.std(dr[ok] - A @ beta, ddof=1))
            else:
                iv = np.nan
        else:
            v60 = iv = np.nan
        vol = V[:, j].astype(float)
        vr = np.nanmean(vol[m - 19:m + 1]) / np.nanmean(vol[m - 249:m + 1]) if m - 249 >= fb and np.nanmean(vol[m - 249:m + 1]) > 0 else np.nan
        if m - 20 >= fb:
            a_ = Cc[m - 19:m + 1, j] * vol[m - 19:m + 1]; x_ = np.abs(c[m - 19:m + 1] / c[m - 20:m] - 1.0)
            ok = np.isfinite(a_) & (a_ > 0) & np.isfinite(x_)
            ami = float(np.mean(x_[ok] / a_[ok])) if ok.sum() >= 10 else np.nan
        else:
            ami = np.nan
        out[i] = r + [d250, bull, v60, iv, vr, ami, np.nan]
    return out


def build_dataset(X):
    Wd, cal = X["Wd"], X["cal"]
    bench = C.bench_series(cal)
    br = np.r_[np.nan, bench[1:] / bench[:-1] - 1.0]
    MS = list(X["MS"])
    rows = []
    for fq, mo in FREQ.items():
        rb = [e for e in MS if cal[e].month in mo]
        for i, e in enumerate(rb):
            nxt = rb[i + 1] if i + 1 < len(rb) else None
            x = nxt - 1 if nxt is not None else None
            g = X["ME"].get(e)
            if g is None:
                continue
            js = g["j"].to_numpy()
            TF = tech_feats(X, e, js, br)
            bret = bench[x] / bench[e - 1] - 1.0 if x is not None else np.nan
            for k, (j, rw) in enumerate(zip(js, g.itertuples(index=False))):
                o = Wd["O"][e, j]
                ret = Wd["CF"][x, j] / o - 1.0 if x is not None and np.isfinite(o) and o > 0 else np.nan
                tf = TF[k]
                mc = float(rw.mcap) if rw.mcap is not None else np.nan
                rows.append({"freq": fq, "e": e, "year": cal[e].year, "j": int(j), "t": rw.t, "m4": bool(rw.m4), "m5": bool(rw.m5),
                             "ret": ret, "bret": bret, "tend": x if x is not None else 10 ** 9,
                             "r1": tf[0], "r3": tf[1], "r6": tf[2], "r12": tf[3], "r3s": tf[4], "r6s": tf[5], "r12s": tf[6], "dist250": tf[7],
                             "bull": tf[8], "vol60": tf[9], "ivol60": tf[10], "vratio": tf[11], "amihud20": tf[12],
                             "turn20": float(rw.to20) if rw.to20 is not None else np.nan,
                             "yoy": rw.rev_yoy, "hi24": float(rw.rev_hi8) if rw.rev_hi8 is not None and rw.rev_hi8 == rw.rev_hi8 else np.nan,
                             "dist24": rw.rev_dist8, "yoystreak": rw.rev_streak, "Q1": rw.roe, "Q2": rw.oia, "Q3": rw.roa, "Q4": rw.rnd_int,
                             "rqoq": rw.rev_qoq, "logcap": math.log(mc) if (mc == mc and mc > 0) else np.nan})
    DS = pd.DataFrame(rows)
    for c in FEATS:
        DS[c] = pd.to_numeric(DS[c], errors="coerce").astype(float)
    cov = DS[DS["freq"] == "月"].groupby("e")["r12s"].apply(lambda z: z.notna().mean())
    start = int(cov[cov >= 0.5].index.min())
    DS = DS[DS["e"] >= start].reset_index(drop=True)
    parts = []
    for (fq, e), g in DS.groupby(["freq", "e"], sort=False):
        g = g.copy()
        for c in FEATS:
            rk = rank01(g[c].to_numpy(float)); miss = ~np.isfinite(rk)
            g["x_" + c] = np.where(miss, 0.5, rk); g["x_miss_" + c] = miss.astype(float)
        r = g["ret"].to_numpy(float); ok = np.isfinite(r)
        ex = r - g["bret"].to_numpy(float)
        yA = np.full(len(g), np.nan); yB = np.full(len(g), np.nan)
        if ok.sum() >= 2:
            lo, hi = np.percentile(ex[ok], [1, 99]); yA[ok] = np.clip(ex[ok], lo, hi)
            pr = pd.Series(r[ok]).rank(method="average").to_numpy() / ok.sum(); yB[ok] = (pr > 0.8).astype(float)
        g["yA"] = yA; g["yB"] = yB; g["yC"] = rank01(r)
        parts.append(g)
    DS = pd.concat(parts, ignore_index=True)
    dropm = ["x_miss_" + c for c in FEATS if DS["x_miss_" + c].sum() == 0]
    DS = DS.drop(columns=dropm)
    return DS, start


def fit_one(job):
    tg, fq = job
    DS = _G["DS"]; cols = _G["cols"]
    d = DS[DS["freq"] == fq]
    isflag = [c.startswith("x_miss_") for c in cols]
    yc = "y" + tg
    yf = d.groupby("year")["e"].min().to_dict()
    logloss = tg == "B"

    def ic(pv, g):
        return float(np.nanmean([spearman(pv[(g["e"] == e).to_numpy()], g.loc[g["e"] == e, "ret"].to_numpy(float)) for e in sorted(g["e"].unique())]))
    tr = d[(d["tend"] < yf[2018]) & d[yc].notna()]; va = d[d["year"] == 2018]
    Xm, y, Xv = tr[cols].to_numpy(float), tr[yc].to_numpy(float), va[cols].to_numpy(float)
    icr = {a: ic(ridge_pred(ridge_fit(Xm, y, a), Xv), va) for a in ALPHAS}
    Ms = stump_fit(bins_of(Xm, isflag), y, isflag, logloss); Bv = bins_of(Xv, isflag)
    icg = {k: ic(stump_pred(Ms, Bv, k), va) for k in ROUNDS}
    al = sorted(ALPHAS, key=lambda a: (-icr[a], a))[0]; kr = sorted(ROUNDS, key=lambda k: (-icg[k], k))[0]
    PRED = []; coef = []; gains = np.zeros(len(cols)); yrs = {}
    for yy in sorted(k for k in yf if k >= 2019):
        tr = d[(d["tend"] < yf[yy]) & d[yc].notna()]; te = d[d["year"] == yy]
        Xm, y, Xt = tr[cols].to_numpy(float), tr[yc].to_numpy(float), te[cols].to_numpy(float)
        Mr = ridge_fit(Xm, y, al); Mg = stump_fit(bins_of(Xm, isflag), y, isflag, logloss, nrounds=kr)
        PRED.append(pd.DataFrame({"target": tg, "freq": fq, "e": te["e"].to_numpy(), "j": te["j"].to_numpy(), "t": te["t"].to_numpy(),
                                  "m4": te["m4"].to_numpy(), "m5": te["m5"].to_numpy(), "LIN": ridge_pred(Mr, Xt),
                                  "GB": stump_pred(Mg, bins_of(Xt, isflag)), "ret": te["ret"].to_numpy(float), "vol60": te["vol60"].to_numpy(float)}))
        coef.append(np.abs(Mr["b"])); gains += Mg["gain"]; yrs[int(yy)] = {"訓練列": int(len(tr)), "預測列": int(len(te)), "樹數": len(Mg["trees"])}
    info = {"α 驗證 IC": icr, "α": al, "輪數 驗證 IC": icg, "輪數": kr, "年": yrs, "訓練列（驗證用）": int(len(d[(d["tend"] < yf[2018])])),
            "嶺迴歸 |係數| 平均前 10": [(cols[i][2:], float(v)) for i, v in sorted(enumerate(np.mean(coef, 0)), key=lambda t: -t[1])[:10]],
            "樹樁 增益合計前 10": [(cols[i][2:], float(v)) for i, v in sorted(enumerate(gains), key=lambda t: -t[1])[:10]]}
    return (tg, fq), pd.concat(PRED, ignore_index=True), info


def select(g, mdl, N, tg):
    if tg != "C":
        return [int(s) for s, _, _ in sorted(zip(g["j"], g[mdl], g["t"]), key=lambda t: (-t[1], t[2]))[:N]]
    ok = g[np.isfinite(g["vol60"].to_numpy(float))]
    rows = sorted(zip(ok["vol60"], ok["t"], ok["j"], ok[mdl]), key=lambda t: (t[0], t[1]))
    n = len(rows); k = N // 5; out = []
    for q in range(5):
        grp = [(s, p, tk) for i, (_, tk, s, p) in enumerate(rows) if (i * 5) // n == q]
        out += [int(s) for s, _, _ in sorted(grp, key=lambda t: (-t[1], t[2]))[:k]]
    return out


def run(a):
    t0 = time.time()
    X = IT.context(bool(a.lim))
    DS, start = build_dataset(X)
    cols = [c for c in DS.columns if c.startswith("x_")]
    IT.log("A4-11 資料集 %d 列｜訓練起點 %s｜特徵欄 %d" % (len(DS), X["cal"][start].date(), len(cols)))
    _G.update(DS=DS, cols=cols)
    jobs = [(tg, fq) for tg in TARGETS for fq in FREQ]
    with Pool(min(a.procs, len(jobs))) as pool:
        out = pool.map(fit_one, jobs)
    PRED = {k: p for k, p, _ in out}; INFO = {"%s|%s" % k: inf for k, _, inf in out}
    IT.log("A4-11 模型完成 %.0fs" % (time.time() - t0))
    Wd, cal, w1, sp, c0 = X["Wd"], X["cal"], X["w1"], X["sp"], X["c0"]
    e19 = int(cal.searchsorted(pd.Timestamp("2019-01-01")))
    segs = {"探索": (e19, sp), "確認": (c0, w1)}
    BM = C.bench_metrics(cal, segs)

    def sel_of(tg, mdl, fq, N, pop):
        P = PRED[(tg, fq)]
        sel = {}
        for e, g in P.groupby("e"):
            g = g if pop == "合併" else g[g["m4"] if pop == "只400" else g["m5"]]
            sel[int(e)] = select(g, mdl, N, tg)
        return sel
    rows = []; grid = []
    for tg in TARGETS:
        for mdl in ("LIN", "GB"):
            for fq in FREQ:
                for N in NS:
                    s = sel_of(tg, mdl, fq, N, "合併")
                    res = C.sim_book(s, Wd, N, min(s), w1)
                    st = C.book_stats(res, *segs["探索"]); st["退化"] = IT.degenerate(st, N)
                    l_ = C.lab(st["年化"], st["回落"], BM["探索"]["年化"], BM["探索"]["回落"])
                    rows.append(((tg, mdl, fq, N), st, l_))
                    grid.append({"目標": tg, "模型": mdl, "頻率": fq, "N": N, "探索": st, "探索標籤": l_, "確認（描述）": C.book_stats(res, *segs["確認"])})
    ch = IT.pick_cell(rows)
    tg, mdl, fq, N = ch
    J = {"格": "目%s %s %s N%d" % ch, "欄": {}}
    for pop in C.COLS:
        s = sel_of(tg, mdl, fq, N, pop)
        tr = []
        res = C.sim_book(s, Wd, N, min(s), w1, trades_out=tr)
        Rr = {nm: C.book_stats(res, a_, b_, trades=tr) for nm, (a_, b_) in segs.items()}
        for nm in Rr:
            Rr[nm]["標籤"] = C.lab(Rr[nm]["年化"], Rr[nm]["回落"], BM[nm]["年化"], BM[nm]["回落"])
        Rr["窗尾仍持有（檔）"] = len(res["open"])
        if pop != "只500":
            for cs in C.COST_SENS:
                r2 = C.sim_book(s, Wd, N, min(s), w1, cost=cs)
                Rr["成本%.2f%%" % (cs * 100)] = {nm: C.seg_metrics(r2["eq"], a_, b_) for nm, (a_, b_) in segs.items()}
            r3 = C.sim_book(s, Wd, N, min(s), w1, brk=Wd["pb"] | Wd["f50"])
            Rr["ret50剔除"] = {nm: C.seg_metrics(r3["eq"], a_, b_) for nm, (a_, b_) in segs.items()}
            Rr["固定天數（描述）"] = {}
            for H in C.FIXH:
                r4 = C.sim_book(s, Wd, N, min(s), w1, fixed_h=H)
                Rr["固定天數（描述）"]["H%d" % H] = {nm: C.book_stats(r4, a_, b_) for nm, (a_, b_) in segs.items()}
        J["欄"][pop] = Rr
    lc = J["欄"]["合併"]["確認"]["標籤"]; l4 = J["欄"]["只400"]["確認"]["標籤"]
    fl = C.final_label(lc, l4)
    if lc in ("合格", "另列"):                     # seq242 ②：跟進出場敏感度（描述）
        ma60 = pd.DataFrame(Wd["CF"]).rolling(60, min_periods=60).mean().to_numpy()
        fu = {}
        for pop in ("合併", "只400"):
            o = {}
            for NN in (5, 20):
                s = sel_of(tg, mdl, fq, NN, pop); r5 = C.sim_book(s, Wd, NN, min(s), w1)
                m = C.seg_metrics(r5["eq"], *segs["確認"]); m["標籤"] = C.lab(m["年化"], m["回落"], BM["確認"]["年化"], BM["確認"]["回落"]); o["N%d" % NN] = m
            s = sel_of(tg, mdl, fq, N, pop); r6 = C.sim_book(s, Wd, N, min(s), w1, ma_stop=ma60)
            m = C.seg_metrics(r6["eq"], *segs["確認"]); m["標籤"] = C.lab(m["年化"], m["回落"], BM["確認"]["年化"], BM["確認"]["回落"]); o["跌破MA60次日賣"] = m
            fu[pop] = o
        J["跟進出場敏感度（描述）"] = fu
    # 同池隨機
    P = PRED[(tg, fq)]
    pools = {int(e): g["j"].tolist() for e, g in P.groupby("e")}
    IT._X["ctx"] = X
    rb = IT.rand_books({"r": {"pools": pools, "N": N, "t0": min(pools), "item": 11, "arm": 1}}, a.reps, a.procs)["r"]
    # 持股 vol60 百分位、樣本外 IC
    s = sel_of(tg, mdl, fq, N, "合併")
    vp = []
    for e, g in P.groupby("e"):
        r = g["vol60"].rank(pct=True)
        m = g["j"].isin(s.get(int(e), [])).to_numpy()
        vp += list(r[m].dropna())
    ic = {}
    for (tg_, fq_), P_ in PRED.items():
        for mdl_ in ("LIN", "GB"):
            v = [spearman(g[mdl_], g["ret"]) for _, g in P_.groupby("e")]
            ic["%s|%s|%s" % (tg_, mdl_, fq_)] = float(np.nanmean(v))
    R = {"件": "A4-11", "名稱": "機器學習選股改目標（numpy 版 168560）", "N": 1, "seq1（78af）": "暫停、不計 N（seq319 Q9）",
         "訓練起點": str(cal[start].date()), "資料集列數": {fq: int((DS["freq"] == fq).sum()) for fq in FREQ}, "特徵欄": len(cols),
         "挑中格": {"目標": tg, "模型": mdl, "頻率": fq, "N": N}, "判定": J, "標籤": fl, "合併確認": lc, "只400確認": l4,
         "判定上限": "確認段合格（無早年段）⇒ 合格也只進前瞻紀錄", "全表": grid, "模型資訊": INFO, "樣本外IC（2019～）": ic,
         "持股vol60百分位平均": float(np.mean(vp)) if vp else np.nan,
         "同池隨機": {"次數": a.reps, "p_確認": IT.p_of(rb, "確認", J["欄"]["合併"]["確認"]["年化"]), "隨機年化中位_確認": float(rb["確認_年化"].median())},
         "基準": BM, "附註": [C.IDEA, "籌碼特徵拿掉（特徵不全）", "基準報酬用 ^SP500TR 收盤（e−1 代 e 開盤）", C.SURV]}
    R["耗時秒"] = round(time.time() - t0, 1); R["算於"] = C.now_tpe(); R["讀法寫死"] = C.READ_TS; R["台股原登錄"] = C.TW_REG["A4-11"]
    C.jdump(R, os.path.join(C.OUT, "A4-11.json"))
    IT.log("A4-11 完成 ⇒ %s（%s）" % (fl, J["格"]))
