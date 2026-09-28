# -*- coding: utf-8 -*-
"""機器學習 簡化版試跑（使用者 09-28：先簡單跑跑看）；超參數與訓練窗為本線暫定、未經登錄；⛔ 不判、不計 N。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMLlite [--procs 2] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchMLlite_check.py

依據：PREREG機器學習 seq1 登錄（sha 78af43d3df5bd042）的特徵、目標、段落；協調者 09-28 指示（使用者「先簡單跑跑看，有需要再安裝！」）⇒ ⛔ 不裝套件，只用 numpy／pandas。
⭐ 這一版 ⛔ 不是 PREREG機器學習 的判定版：超參數、訓練窗、模型都是本線暫定、未經登錄、未經裁定。
═══ 本線暫定（⭐ 看任何模型輸出前寫死）═══
  模型：
    RIDGE  閉式解（特徵以訓練集平均／標準差標準化、標準差 0 的欄設 0；截距不罰；min ||y − Xb||² ＋ α||b||²）；α ∈ {0.1, 1, 10} 在驗證段 2018 以平均 IC 挑 1 個（同分取小）
    STUMP  numpy 梯度提升樹樁：depth 1、100 棵、學習率 0.1、平方損失、初值 ＝ 訓練目標平均；分割點 ＝ 連續特徵 0.05、0.10、…、0.95（排名後的 20 等分），缺值旗標 0.5（多頭排列、創 24 月新高排名後只有兩個值 ⇒ 照 20 等分）；
           同分取特徵序小、門檻小（依構造決定性，無亂數）
  段：訓練起點 ＝ 特徵全可算的第一個換股月（12 個月跳過 1 個月報酬要 273 根 ⇒ 2016-02）；驗證 2018；每年 1 月擴張式重訓（驗證段之後的年份含 2018）；
      探索 2019～2021、確認 2022-01～2026-08；⭐ 訓練樣本只收「目標期已結束於重訓那年第一個換股日之前」的列（不前視）
  目標：下一個持有期（月換 ＝ 到下個月換股日前一交易日收盤；季換 ＝ 到下季）報酬 ＝ ffill 還原收盤(下期換股日 − 1) ÷ 還原開盤(e) − 1 的當期橫斷面排名（0～1）
  換股日 e ＝ 當月 W1 量測日次一交易日；季 ＝ 1、4、7、10 月；母體 ＝ panel_ext W1 eligible（含已下市）
  特徵（登錄 §一；量測日 m ＝ e − 1 以前；ffill 還原收盤；未定處照本線 ④ 暫定）：
    價格 r1／r3／r6／r12（21／63／126／252 根）、r3s／r6s／r12s（跳過最近 21 根）、距 250 日高、多頭排列（close ＞ MA20 ＞ MA60）、60 日波動、
         特有波動（60 日日報酬對 0050 迴歸殘差標準差）
    量能 20 日均量 ÷ 250 日均量、周轉率（20 日均量 ÷ shares）、Amihud（20 日 |日報酬| ÷ 成交金額 平均）
    營收 最新可用月營收年增率、是否創 24 月新高（p4_features.rev_hi24_flags）、距 24 月高、連續年增月數（月營收接早年版面 2003～2014，原始值）
    財報（A2 暫定，researchQual 同式）ROE、營業利益÷資產、ROA、研發強度、營收季增（單季營收 ÷ 前一季 − 1）
    籌碼 投信、外資近 20 日淨買 ÷ shares｜規模 log(原始收盤 × shares)
    缺值：當期橫斷面排名（0～1）後以 0.5（中位）補，另加「是否缺值」旗標
  組合：每期取預測最高前 N（同分依代號）；N ∈ {10, 20}；月／季；換股簿 researchMomX.sim_book（續抱、⭐ 停止交易強制出場：開）；窗尾照市值 ⇒ 不截斷
  描述挑格（⛔ 不判）：探索段去退化（平均持股 ＜ N÷2 或現金 ＞ 30%）後，過使用者判準者取比值最高，都沒過取比值最高
  並列：0050、營量 v1（T1 版：researchT1fix 的 build_ctx(True)＋stop_force，#13 relvol H60 N20）、合成分數同格（resultsScore，786147154e）、同池隨機 1,000 次
  閘：整套訓練＋預測重跑第二次 ⇒ 全部預測值 sha256 相同（逐位元）
輸出 backtest/resultsMLlite/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchMomX as MX
from backtest import researchQual as QL
from backtest import research13 as R13
from backtest import p4_features as P4F
D, TR, H2 = MX.D, MX.TR, MX.H2

OUT = "backtest/resultsMLlite"
TAG = "簡化版試跑（使用者 09-28：先簡單跑跑看）；超參數與訓練窗為本線暫定、未經登錄；⛔ 不判、不計 N"
W = {"data": H2.H2D, "panel": "backtest/resultsp9_engine/panel_ext.csv.gz", "elig": "eligible", "w": ("2016-02-01", "2026-08-24"), "segs": {}}
EARLY_REV = os.path.expanduser("~/earlydata/3edc0e2206/main/data/mops/revenue_hist")
SEGS = {"探索": ("2019-01-01", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
FEATS = ["r1", "r3", "r6", "r12", "r3s", "r6s", "r12s", "dist250", "bull", "vol60", "ivol60", "vratio", "turn20", "amihud20",
         "yoy", "hi24", "dist24", "yoystreak", "Q1", "Q2", "Q3", "Q4", "rqoq", "trust20", "foreign20", "logcap"]
ALPHAS = (0.1, 1.0, 10.0)
NT, LR, NB = 100, 0.1, 20
_G: dict = {}


# ═════════════ 每檔技術面特徵 ═════════════
def _init(cal, data, ms, br):
    D.DATA = data
    _G.update(cal=cal, ms=ms, br=br)


def feat_one(args):
    sid, mk = args
    cal, ms, br = _G["cal"], _G["ms"], _G["br"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    raw_c = df["close"].to_numpy(float); valid = np.isfinite(raw_c)
    c = pd.Series(raw_c).ffill().to_numpy(float)
    vol = df["volume"].to_numpy(float); amt = df["amount"].to_numpy(float)
    rp = pd.read_csv(os.path.join(D.DATA, "stocks", sid + ".csv"), usecols=["date", "close"], dtype={"date": str}).drop_duplicates("date")
    rawp = pd.Series(pd.to_numeric(rp["close"], errors="coerce").to_numpy(), pd.to_datetime(rp["date"])).reindex(cal).ffill().to_numpy(float)
    sh = P4F.load_shares(sid, cal).to_numpy(float)
    ip = os.path.join(D.DATA, "stocks_inst", sid + ".csv")
    if os.path.exists(ip):
        ins = pd.read_csv(ip, usecols=["date", "foreign", "trust"], dtype={"date": str}).drop_duplicates("date")
        ins.index = pd.to_datetime(ins["date"]); ins = ins.reindex(cal)
        fo = pd.to_numeric(ins["foreign"], errors="coerce").to_numpy(float); tr = pd.to_numeric(ins["trust"], errors="coerce").to_numpy(float)
    else:
        fo = tr = np.full(n, np.nan)
    ma20 = pd.Series(c).rolling(20, min_periods=20).mean().to_numpy(); ma60 = pd.Series(c).rolling(60, min_periods=60).mean().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        dr = np.r_[np.nan, c[1:] / c[:-1] - 1.0]
    fb = int(np.flatnonzero(valid)[0]) if valid.any() else n
    out = np.full((len(ms), 17), np.nan)
    for i, m in enumerate(ms):
        if m < fb or not valid[m]:
            continue

        def R(a, b):
            return c[b] / c[a] - 1.0 if a >= fb and c[a] > 0 else np.nan
        r = [R(m - w, m) for w in (21, 63, 126, 252)] + [R(m - 21 - w, m - 21) for w in (63, 126, 252)]
        d250 = c[m] / np.max(c[m - 249:m + 1]) - 1.0 if m - 249 >= fb else np.nan
        bull = float(c[m] > ma20[m] > ma60[m]) if np.isfinite(ma60[m]) else np.nan
        if m - 60 >= fb:
            x = dr[m - 59:m + 1]; bb = br[m - 59:m + 1]; ok = np.isfinite(x) & np.isfinite(bb)
            v60 = float(np.std(x[ok], ddof=1)) if ok.sum() >= 40 else np.nan
            if ok.sum() >= 40:
                X = np.column_stack([np.ones(ok.sum()), bb[ok]]); beta, *_ = np.linalg.lstsq(X, x[ok], rcond=None)
                iv = float(np.std(x[ok] - X @ beta, ddof=1))
            else:
                iv = np.nan
        else:
            v60 = iv = np.nan
        vr = np.nanmean(vol[m - 19:m + 1]) / np.nanmean(vol[m - 249:m + 1]) if m - 249 >= fb and np.nanmean(vol[m - 249:m + 1]) > 0 else np.nan
        tn = np.nanmean(vol[m - 19:m + 1]) / sh[m] if np.isfinite(sh[m]) and sh[m] > 0 else np.nan
        a_ = amt[m - 19:m + 1]; x_ = np.abs(dr[m - 19:m + 1]); ok = np.isfinite(a_) & (a_ > 0) & np.isfinite(x_)
        ami = float(np.mean(x_[ok] / a_[ok])) if ok.sum() >= 10 else np.nan
        t20 = np.nansum(tr[m - 19:m + 1]) / sh[m] if np.isfinite(sh[m]) and sh[m] > 0 and np.isfinite(tr[m - 19:m + 1]).sum() >= 10 else np.nan
        f20 = np.nansum(fo[m - 19:m + 1]) / sh[m] if np.isfinite(sh[m]) and sh[m] > 0 and np.isfinite(fo[m - 19:m + 1]).sum() >= 10 else np.nan
        cap = math.log(rawp[m] * sh[m]) if np.isfinite(rawp[m]) and np.isfinite(sh[m]) and rawp[m] > 0 and sh[m] > 0 else np.nan
        out[i] = r + [d250, bull, v60, iv, vr, tn, ami, t20, f20, cap]
    return sid, out.astype(np.float64)


TECH = ["r1", "r3", "r6", "r12", "r3s", "r6s", "r12s", "dist250", "bull", "vol60", "ivol60", "vratio", "turn20", "amihud20", "trust20", "foreign20", "logcap"]


# ═════════════ 營收、財報特徵 ═════════════
def rev_feats(cal, rebs, sids):
    fs = sorted(glob.glob(os.path.join(EARLY_REV, "*.csv"))) + sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    per = list(rev.index)
    pidx = {p: i for i, p in enumerate(per)}
    rd = {p: e for p, (_, e) in __import__("backtest.research34", fromlist=["x"]).rebalance_dates(per, cal, 10).items()}
    flag = P4F.rev_hi24_flags(rev, cal)
    V = rev.to_numpy(float); col = {s: j for j, s in enumerate(rev.columns)}
    out = {}
    for e in rebs:
        avail = [p for p in per if p in rd and rd[p] <= e]
        k = pidx[avail[-1]] if avail else None
        rowf = flag.iloc[e]
        for s in sids:
            j = col.get(s)
            if j is None or k is None:
                out[(e, s)] = (np.nan, np.nan, np.nan, np.nan); continue
            # 最新可用 ＝ 該檔 ≤ k 的最後一個有值期
            kk = k
            while kk >= 0 and not np.isfinite(V[kk, j]):
                kk -= 1
            if kk < 0:
                out[(e, s)] = (np.nan, np.nan, np.nan, float(rowf.get(s, np.nan)) if s in rowf.index else np.nan); continue
            v = V[kk, j]
            yoy = v / V[kk - 12, j] - 1.0 if kk >= 12 and np.isfinite(V[kk - 12, j]) and V[kk - 12, j] > 0 else np.nan
            h = V[max(kk - 24, 0):kk, j]; h = h[np.isfinite(h)]
            d24 = v / h.max() - 1.0 if kk >= 24 and len(h) >= 18 and h.max() > 0 else np.nan
            stk = 0; q = kk
            while q >= 12 and np.isfinite(V[q, j]) and np.isfinite(V[q - 12, j]) and V[q - 12, j] > 0 and V[q, j] > V[q - 12, j]:
                stk += 1; q -= 1
            hv = rowf.get(s, np.nan)
            out[(e, s)] = (yoy, d24, float(stk), float(hv) / 100.0 if np.isfinite(hv) else np.nan)
    return out


def fin_feats(cal, rebs, sids, log):
    Q = QL.load_fin(log)
    pos, _ = QL.avail_pos(Q, cal)
    fs = sorted(glob.glob(os.path.join(QL.FD, "mops", "fin_hist", "*.csv")))
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "rev_ytd"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
    yt = {(s, int(p[:4]), int(p[-1])): v for s, p, v in zip(F["stock_id"], F["period"], F["rev_ytd"])}

    def rq(s, y, q):
        a = yt.get((s, y, q), np.nan)
        if q == 1:
            return a
        b = yt.get((s, y, q - 1), np.nan)
        return a - b if np.isfinite(a) and np.isfinite(b) else np.nan
    qoq = []
    for s, y, q in zip(Q["sid"], Q["y"], Q["q"]):
        py, pq = (y, q - 1) if q > 1 else (y - 1, 4)
        a, b = rq(s, y, q), rq(s, py, pq)
        qoq.append(a / b - 1.0 if np.isfinite(a) and np.isfinite(b) and b > 0 else np.nan)
    Q["rqoq"] = qoq
    out = {}; ss = set(sids)
    for e in rebs:
        last = Q[pos <= e].groupby("sid").tail(1)
        for s, a, b, c_, d_, r_ in zip(last["sid"], last["Q1"], last["Q2"], last["Q3"], last["Q4"], last["rqoq"]):
            if s in ss:
                out[(e, s)] = (a, b, c_, d_, r_)
    return out


# ═════════════ 模型 ═════════════
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


def bins_of(X, isflag):
    B = np.empty(X.shape, np.int16)
    for j in range(X.shape[1]):
        B[:, j] = (X[:, j] >= 0.5).astype(np.int16) if isflag[j] else np.clip(np.floor(X[:, j] * NB), 0, NB - 1).astype(np.int16)
    return B


def stump_fit(B, y, isflag):
    n, p = B.shape; f = np.full(n, y.mean()); trees = []; gain_tot = np.zeros(p)
    nbins = [2 if isflag[j] else NB for j in range(p)]
    for _ in range(NT):
        r = y - f; S = r.sum(); best = (-np.inf, -1, -1, 0.0, 0.0)
        for j in range(p):
            nb = nbins[j]
            cs = np.cumsum(np.bincount(B[:, j], weights=r, minlength=nb)); cn = np.cumsum(np.bincount(B[:, j], minlength=nb))
            for t in range(nb - 1):
                nl = cn[t]; nr = n - nl
                if nl == 0 or nr == 0:
                    continue
                sl = cs[t]; g = sl * sl / nl + (S - sl) ** 2 / nr - S * S / n
                if g > best[0] + 1e-15:
                    best = (g, j, t, sl / nl, (S - sl) / nr)
        g, j, t, vl, vr = best
        if j < 0:
            break
        f = f + LR * np.where(B[:, j] <= t, vl, vr)
        trees.append((j, t, LR * vl, LR * vr)); gain_tot[j] += g
    return {"f0": y.mean(), "trees": trees, "gain": gain_tot}


def stump_pred(M, B):
    out = np.full(B.shape[0], M["f0"])
    for j, t, vl, vr in M["trees"]:
        out = out + np.where(B[:, j] <= t, vl, vr)
    return out


def spearman(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 10:
        return np.nan
    return float(pd.Series(a[ok]).rank().corr(pd.Series(b[ok]).rank()))


def model_pass(DS, freqs_reb, years, log):
    """整套訓練＋預測；回 預測表、α、IC、重要度。"""
    cols = [c for c in DS.columns if c.startswith("x_")]
    isflag = [c.startswith("x_miss_") for c in cols]                     # 旗標（0／1）；多頭排列、創高是排名後的二值 ⇒ 走 20 等分（兩個值各落一格）
    PRED = []; INFO = {}
    for fq, rebs in freqs_reb.items():
        d = DS[DS["freq"] == fq]
        yrfirst = d.groupby("year")["e"].min().to_dict()
        # 驗證：挑 α
        tr = d[(d["tend"] < yrfirst[2018]) & d["y"].notna()]; va = d[d["year"] == 2018]
        Xt = tr[cols].to_numpy(float); yt_ = tr["y"].to_numpy(float)
        ics = {}
        for a in ALPHAS:
            M = ridge_fit(Xt, yt_, a); pv = ridge_pred(M, va[cols].to_numpy(float))
            ics[a] = float(np.nanmean([spearman(pv[(va["e"] == e).to_numpy()], va.loc[va["e"] == e, "ret"].to_numpy(float)) for e in sorted(va["e"].unique())]))
        alpha = sorted(ALPHAS, key=lambda a: (-ics[a], a))[0]
        INFO[fq] = {"α 驗證 IC": ics, "α": alpha, "訓練起點": str(pd.Timestamp(d["date"].min()).date()), "年": {}}
        coefs = []; gains = np.zeros(len(cols))
        for y in [y for y in years if y >= 2019 and y in yrfirst]:
            tr = d[(d["tend"] < yrfirst[y]) & d["y"].notna()]; te = d[d["year"] == y]
            Xt = tr[cols].to_numpy(float); yt_ = tr["y"].to_numpy(float)
            Mr = ridge_fit(Xt, yt_, alpha); Ms = stump_fit(bins_of(Xt, isflag), yt_, isflag)
            pr = ridge_pred(Mr, te[cols].to_numpy(float)); ps = stump_pred(Ms, bins_of(te[cols].to_numpy(float), isflag))
            PRED.append(pd.DataFrame({"freq": fq, "e": te["e"].to_numpy(), "sid": te["sid"].to_numpy(), "RIDGE": pr, "STUMP": ps, "ret": te["ret"].to_numpy(float)}))
            coefs.append(np.abs(Mr["b"])); gains += Ms["gain"]
            INFO[fq]["年"][int(y)] = {"訓練列": int(len(tr)), "預測列": int(len(te)), "樹數": len(Ms["trees"])}
        INFO[fq]["嶺迴歸 |係數| 平均前 10"] = [(cols[i][2:], float(v)) for i, v in sorted(enumerate(np.mean(coefs, 0)), key=lambda t: -t[1])[:10]]
        INFO[fq]["樹樁 增益合計前 10"] = [(cols[i][2:], float(v)) for i, v in sorted(enumerate(gains), key=lambda t: -t[1])[:10]]
        log(f"  [模型 {fq}] α {alpha}（驗證 IC {ics}）｜重訓 {list(INFO[fq]['年'])}")
    P = pd.concat(PRED, ignore_index=True)
    return P, INFO


def _fake(args):
    fq, N, r = args
    Wd = _G["Wd"]; pool = _G["pool"][fq]
    rng = np.random.default_rng([20260928, {"月": 1, "季": 2}[fq], N, r])
    sel = {e: list(rng.choice(p_, size=min(N, len(p_)), replace=False)) if p_ else [] for e, p_ in pool.items()}
    res = MX.sim_book(sel, Wd, N, t0=min(sel))
    out = {"r": r}
    for nm, (a, b) in _G["SEGP"].items():
        c, m = R13.window_stats(res["eq"], 0, len(res["eq"]), a, b + 1); out[f"{nm}_年化"] = float(c); out[f"{nm}_回落"] = float(m)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchMLlite {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    S = {"身分": TAG, "登錄參照": "PREREG機器學習 seq1 sha 78af43d3df5bd042（⛔ 本件不是其判定版）", "閘": {}}
    Wd = MX.load_world(W, a.procs, log)
    cal, n, P = Wd["cal"], Wd["n"], Wd["P"]
    rebs = Wd["rebs"]
    st = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
    br = np.r_[np.nan, Wd["bench"][1:] / Wd["bench"][:-1] - 1.0]
    ms = np.array([e - 1 for e in rebs])
    sids = Wd["sids"]
    with Pool(a.procs, initializer=_init, initargs=(cal, H2.H2D, ms, br)) as pool:
        TF = dict(pool.map(feat_one, [(s, st.get(s, "twse")) for s in sids], chunksize=16))
    log(f"[技術面特徵] {len(TF):,} 檔")
    RV = rev_feats(cal, rebs, sids); log("[營收特徵] 完成")
    FF = fin_feats(cal, rebs, sids, log); log("[財報特徵] 完成")
    # ── 資料集
    fq_rebs = {"月": rebs, "季": [e for e in rebs if cal[e].month in (1, 4, 7, 10)]}
    rows = []
    for fq, rb in fq_rebs.items():
        for i, e in enumerate(rb):
            nxt = rb[i + 1] if i + 1 < len(rb) else None
            x = nxt - 1 if nxt is not None else None
            ii = int(np.searchsorted(ms, e - 1))
            for s in Wd["reb"][e]:
                tf = TF.get(s)
                if tf is None:
                    continue
                o = P[s]["o"][e]
                ret = P[s]["c"][x] / o - 1.0 if x is not None and np.isfinite(o) and o > 0 else np.nan
                rv = RV.get((e, s), (np.nan,) * 4); ff = FF.get((e, s), (np.nan,) * 5)
                v = dict(zip(TECH, tf[ii])); v.update({"yoy": rv[0], "dist24": rv[1], "yoystreak": rv[2], "hi24": rv[3], "Q1": ff[0], "Q2": ff[1], "Q3": ff[2], "Q4": ff[3], "rqoq": ff[4]})
                rows.append({"freq": fq, "e": e, "date": cal[e], "year": cal[e].year, "sid": s, "ret": ret, "tend": x if x is not None else 10 ** 9, **v})
    DS = pd.DataFrame(rows)
    # 完整可算的第一個換股月（r12s）
    cov = DS[DS["freq"] == "月"].groupby("e")["r12s"].apply(lambda z: z.notna().mean())
    start = int(cov[cov >= 0.5].index.min())
    DS = DS[DS["e"] >= start].reset_index(drop=True)
    S["訓練起點（r12s 可算 ≥ 五成的第一個換股日）"] = str(cal[start].date())
    for c in FEATS:
        DS[f"x_miss_{c}"] = 0.0
    parts = []
    for (fq, e), g in DS.groupby(["freq", "e"], sort=False):
        g = g.copy()
        for c in FEATS:
            rk = rank01(g[c].to_numpy(float))
            miss = ~np.isfinite(rk)
            g[f"x_{c}"] = np.where(miss, 0.5, rk); g[f"x_miss_{c}"] = miss.astype(float)
        g["y"] = rank01(g["ret"].to_numpy(float))
        parts.append(g)
    DS = pd.concat(parts, ignore_index=True)
    DS = DS[[c for c in DS.columns if not (c.startswith("x_miss_") and False)]]
    miss_cols = [f"x_miss_{c}" for c in FEATS if DS[f"x_miss_{c}"].sum() > 0]
    dropm = [f"x_miss_{c}" for c in FEATS if f"x_miss_{c}" not in miss_cols]
    DS = DS.drop(columns=dropm)
    S["特徵"] = {"數": len(FEATS), "缺值旗標欄": len(miss_cols), "資料集列": int(len(DS)), "缺值率": {c: float(DS[c].isna().mean()) for c in FEATS}}
    log(f"[資料集] {len(DS):,} 列｜訓練起點 {cal[start].date()}｜缺值旗標 {len(miss_cols)} 欄")
    DS.drop(columns=["date"]).to_csv(os.path.join(OUT, "dataset.csv.gz"), index=False, float_format="%.17g")
    years = sorted(DS["year"].unique())
    fqr = {fq: [e for e in rb if e >= start] for fq, rb in fq_rebs.items()}
    P1, INFO = model_pass(DS, fqr, years, log)
    P2, _ = model_pass(DS, fqr, years, lambda m: None)
    h1 = hashlib.sha256(P1[["RIDGE", "STUMP"]].to_numpy().tobytes()).hexdigest(); h2 = hashlib.sha256(P2[["RIDGE", "STUMP"]].to_numpy().tobytes()).hexdigest()
    S["閘"]["重跑兩次預測逐位元相同"] = {"sha1": h1[:16], "sha2": h2[:16], "相同": h1 == h2}
    log(f"[閘] {S['閘']}")
    if h1 != h2:
        raise SystemExit("⛔ 重跑不同")
    P1.to_csv(os.path.join(OUT, "predictions.csv.gz"), index=False, float_format="%.17g")
    S["模型"] = INFO
    # ── IC
    SEGP = {nm: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y), side="right") - 1)) for nm, (x, y) in SEGS.items()}
    IC = {}
    for fq in ("月", "季"):
        for mdl in ("RIDGE", "STUMP"):
            for nm, (x, y) in SEGP.items():
                g = P1[(P1["freq"] == fq) & (P1["e"] >= x) & (P1["e"] <= y)]
                v = [spearman(gg[mdl].to_numpy(float), gg["ret"].to_numpy(float)) for _, gg in g.groupby("e")]
                IC[f"{mdl}_{fq}_{nm}"] = {"平均 IC": float(np.nanmean(v)), "IC＞0 比例": float(np.nanmean(np.array(v) > 0)), "期數": len(v)}
    S["樣本外 IC"] = IC
    # ── 組合
    Z = {nm: R13.window_stats(Wd["bench"], 0, n, x, y + 1) for nm, (x, y) in SEGP.items()}
    S["0050"] = {nm: {"年化": float(v[0]), "回落": float(v[1]), "比值": float(v[0]) / abs(float(v[1]))} for nm, v in Z.items()}
    rows = []; SEL = {}; RES = {}
    for mdl in ("RIDGE", "STUMP"):
        for fq in ("月", "季"):
            for N in (10, 20):
                key = f"{mdl}_{fq}_N{N}"
                g = P1[P1["freq"] == fq]
                sel = {int(e): [s for s, _ in sorted(zip(gg["sid"], gg[mdl]), key=lambda t: (-t[1], t[0]))[:N]] for e, gg in g.groupby("e") if e >= SEGP["探索"][0]}
                res = MX.sim_book(sel, Wd, N, t0=min(sel)); SEL[key] = sel; RES[key] = res
                for nm, (x, y) in SEGP.items():
                    c, m = R13.window_stats(res["eq"], 0, n, x, y + 1)
                    rs = [e for e in sorted(sel) if x <= e <= y]
                    tv = [res["buys"][e] / N for e in rs[1:] if e in res["buys"]]
                    cy = float(sum(res["costd"][t] / res["eq"][t - 1] for t in range(x, y + 1) if res["costd"][t] > 0) / ((y - x + 1) / 245))
                    rows.append({"格": key, "模型": mdl, "頻率": fq, "N": N, "段": nm, "年化": float(c), "回落": float(m), "比值": float(c) / abs(float(m)),
                                 "標籤（描述）": MX.label(float(c), float(m), *Z[nm]), "換手": float(np.mean(tv)) if tv else np.nan, "成本／年": cy,
                                 "平均持股": float(np.mean(res["npos"][x:y + 1])), "現金比例": float(np.nanmean(res["cashf"][x:y + 1])), "強制出場": res["cnt"]["stop_force"]})
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    ex = T[T["段"] == "探索"].copy()
    ex = ex[~((ex["平均持股"] < ex["N"] / 2) | (ex["現金比例"] > 0.30))]
    c0, m0 = Z["探索"]; ps = ex[(ex["年化"] > c0) & (ex["比值"] >= c0 / abs(m0))]
    best = (ps if len(ps) else ex).sort_values(["比值", "年化"], ascending=[False, False]).iloc[0]
    pk = best["格"]; cf = T[(T["格"] == pk) & (T["段"] == "確認")].iloc[0]
    S["描述挑格（⛔ 不判）"] = {"格": pk, "探索過判準格數": int(len(ps)), "探索": {k: float(best[k]) for k in ("年化", "回落", "比值")},
                           "確認": {k: (cf[k] if k == "標籤（描述）" else float(cf[k])) for k in ("年化", "回落", "比值", "換手", "成本／年", "平均持股", "標籤（描述）")}}
    log(f"[描述挑格] {pk}｜探索 {best['年化']:+.2%}／{best['回落']:+.2%}｜確認 {cf['年化']:+.2%}／{cf['回落']:+.2%} {cf['標籤（描述）']}")
    # 各年
    res = RES[pk]; yrs = {}
    for y in range(2019, 2027):
        idx = [t for t in range(SEGP["探索"][0], SEGP["確認"][1] + 1) if cal[t].year == y]
        if idx:
            b0 = res["eq"][idx[0] - 1] if idx[0] > SEGP["探索"][0] else res["eq"][idx[0]]
            yrs[str(y)] = [float(res["eq"][idx[-1]] / b0 - 1), float(Wd["bench"][idx[-1]] / Wd["bench"][idx[0] - 1] - 1)]
    S["挑中格各年（本格／0050）"] = yrs
    # 假訊號
    fq, N = best["頻率"], int(best["N"])
    pool = {fq_: {int(e): sorted(g["sid"]) for e, g in P1[P1["freq"] == fq_].groupby("e") if e >= SEGP["探索"][0]} for fq_ in ("月", "季")}
    _G.update(Wd=Wd, pool=pool, SEGP=SEGP)
    with Pool(a.procs) as pp:
        FK = pd.DataFrame(pp.map(_fake, [(fq, N, r) for r in range(a.reps)], chunksize=20))
    FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
    S["假訊號（同池隨機，挑中格）"] = {nm: {"p（隨機年化 ≥ 本格）": float(np.mean(FK[f"{nm}_年化"] >= T[(T["格"] == pk) & (T["段"] == nm)]["年化"].iloc[0])),
                                         "隨機年化中位": float(FK[f"{nm}_年化"].median())} for nm in SEGP}
    # 並列：合成分數同格、營量 v1 T1
    SC = pd.read_csv("backtest/resultsScore/cells.csv")
    SC = SC[(SC["換股"] == ("月換" if fq == "月" else "季換")) & (SC["N"] == N)]
    S["合成分數同格（resultsScore，786147154e；各 L）"] = {f"L{int(r.L)}_{r.段}": [float(r.年化), float(r.回落), r.標籤] for r in SC.itertuples()}
    try:
        from backtest import researchT1fix as T1
        from backtest import research11 as R11
        from backtest import rerun17 as RR
        ctx = T1.build_ctx(True)
        SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), ctx["mk"], ctx["cal"]), ctx["w1"])
        o = R11.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0), ctx["closes"], ctx["opens"], ctx["ncal"], log=[], d_max=None,
                             pick="relvol", queue_days=0, return_equity=True, stop_force=SF)
        eq13 = np.asarray(o["equity"], float)
        S["營量 v1（T1 版、stop_force 開）"] = {nm: dict(zip(("年化", "回落"), map(float, R13.window_stats(eq13, 0, len(eq13), x, y + 1)))) for nm, (x, y) in SEGP.items()}
    except Exception as ex_:
        S["營量 v1（T1 版、stop_force 開）"] = f"⚠ 沒算成：{ex_!r}"
    log(f"[並列] 營量 v1 T1 {S['營量 v1（T1 版、stop_force 開）']}")
    rows = []
    for key, sel in SEL.items():
        for e, s_ in sel.items():
            for i, s in enumerate(s_):
                rows.append({"格": key, "換股日": str(cal[e].date()), "名次": i + 1, "sid": s})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "picks.csv.gz"), index=False)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
