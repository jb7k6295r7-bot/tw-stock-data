# -*- coding: utf-8 -*-
"""PREREG機器學習改目標 seq1（台股策略線 登錄 sha 168560f97763a287；裁定 seq265 §二 發號、N ＋1）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMLx [--procs 2] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchMLx_check.py

問：簡化版學會「挑低波動」而跟不上 0050；改成學「超額數值」「大贏家」或「波動中性選股」，扣成本後能不能贏 0050？
⚠ 登錄照實標：看過簡化版結果之後才設計；⭐ 判定上限 ＝「確認段合格（無早年段）」⇒ 合格也只進前瞻紀錄、不進有效清單（seq265 §二）。

═══ 照登錄（⛔ 寫死）═══
  特徵：researchMLlite（1ed9de081e）一字不動（import 其 feat_one／rev_feats／fin_feats／rank01、同一世界 MX.load_world(ML.W)）；26 特徵＋缺值旗標、每期橫斷面排名
  目標（下期 ＝ 該頻率持有期：換股日 e 開盤 ～ 下一換股日前一交易日收盤；還原、ffill 收盤）：
    A 超額數值 y ＝ ret − 0050 同期（0050 還原收盤[x] ÷ 還原開盤[e] − 1）；每期橫斷面 1%／99% 分位（numpy percentile 線性）截尾；⛔ 不排名
    B 大贏家 y ＝ 1 若 ret 的當期平均名次 ÷ 件數 ＞ 0.8（前 20%），否則 0
    C 波動中性：y ＝ rank01(ret)（同簡化版）；選股時候選依 vol60（換股日前一日 60 日波動，同特徵）排序分五組（i×5÷n，同值依代號），各組取預測最高 N÷5；vol60 缺 ⇒ 不入選（計數）
    目標期跨資料尾（最後一期）的列不進訓練（同簡化版 tend 規則）
  模型（numpy 自寫）：
    M-LIN 嶺迴歸（ML.ridge_fit／ridge_pred：標準化、截距不罰）α ∈ {1, 10, 100}
    M-GB 梯度提升樹樁：深度 1、學習率 0.1、輪數 ∈ {50, 100, 200}、每葉最少 200 筆、切點 ＝ 排名特徵 0.1…0.9（bin ＝ floor(x×10)）、缺值旗標切 0.5；
         目 A、C 平方損失（初值 ＝ 訓練 y 平均）；目 B 對數損失（初值 ＝ log(p̄÷(1−p̄))；每輪對殘差 y−σ(F) 以平方和增益選切點、葉值 ＝ Σ殘差 ÷ Σp(1−p)（Newton 一步））；
         同分取特徵序小、門檻小；⭐ 輪數 50／100／200 ＝ 同一條 200 輪路徑截在第 50、100、200 輪（決定性，等同分別訓練）
    選超參數：驗證段 2018（訓練列 tend ＜ 該頻率 2018 第一個換股日），每期 Spearman(預測, 實際下期報酬 ret) 平均最高；同分取 α 小／輪數少；⛔ 不做其他調參
  滾動：擴張式；訓練起點 2016-03-02（同簡化版，閘驗）；2019 起每年第一個換股日重訓（訓練列 tend ＜ 該日）
  頻率：月（每月）｜季（1、4、7、10 月）｜半年（1、7 月）；N ∈ {10, 20} ⇒ 格 ＝ 3 目標 × 2 模型 × 3 頻率 × 2 N ＝ 36
  組合：每期取預測最高前 N（同分依代號；目 C 照波動分組取）；等權換股簿 MX.sim_book（續抱、⭐ 停止交易強制出場：開、下市了結）；窗尾照市值 ⇒ 依構造不截斷
  段：探索 2019-01-01～2021-12-30（挑格）｜確認 2022-01-03～2026-08-24（判）；段內 R13.window_stats
  退化（事前排除）：探索段平均持股 ＜ N÷2 或現金比例 ＞ 30%
  挑格：探索段過使用者判準者取比值最高；都沒過取比值最高；平手 ⇒ 年化高
  判定：確認段使用者判準（seq141）對 0050 同段；⭐ 措辭上限「確認段合格（無早年段）」
  對照（K4）：同池隨機 1,000 次（挑中格頻率、N；每期從該頻率當期全部可預測股票不放回抽 N；default_rng([20260928, r])）｜簡化版同頻率同 N（resultsMLlite cells，
     半年無）｜合成分數同格（resultsScore，確認段）｜營量 v1（T1 版，researchT1fix build_ctx(True)＋stop_force）｜0050
  必報：挑中格持股 vol60 在「當期可預測股票」中的百分位平均（對照簡化版挑中格 RIDGE_月_N20，用本件同一份 vol60 算）；全 36 格同量；
     特徵重要度前 10（嶺迴歸 |係數| 平均、樹樁增益合計）；樣本外 IC；挑中格各年報酬；換手與成本
  新規矩 ③（登錄 §四）：挑中格確認段合格或另列 ⇒ (a) 全賣全買（sim_book mode="all"）、(b) 跌破 MA60 次日開盤賣（ma_stop）⇒ 描述
  閘：① 月、季資料集 x_ 欄與 ret ＝ resultsMLlite/dataset.csv.gz（逐位元）② 整套訓練＋預測重跑兩次 ⇒ 預測 sha256 相同
輸出 backtest/resultsMLx/
"""
from __future__ import annotations

import argparse
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
from backtest import researchMLlite as ML
from backtest import researchMomX as MX
from backtest import research13 as R13
D, H2 = ML.D, ML.H2

OUT = "backtest/resultsMLx"
SEGS = {"探索": ("2019-01-01", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
FREQ = {"月": tuple(range(1, 13)), "季": (1, 4, 7, 10), "半年": (1, 7)}
TARGETS = ("A", "B", "C")
ALPHAS = (1.0, 10.0, 100.0)
ROUNDS = (50, 100, 200)
LR, NB, MINLEAF = 0.1, 10, 200
NS = (10, 20)
_G: dict = {}


# ═════════════ 樹樁 ═════════════
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
    for _ in range(nrounds):
        if logloss:
            pr = 1.0 / (1.0 + np.exp(-F)); r = y - pr; h = pr * (1 - pr)
        else:
            r = y - F; h = None
        S = r.sum(); best = (-np.inf, -1, -1)
        for j in range(p):
            nb = nbins[j]
            cs = np.cumsum(np.bincount(B[:, j], weights=r, minlength=nb)); cn = np.cumsum(np.bincount(B[:, j], minlength=nb))
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


# ═════════════ 訓練＋預測（一個 目標×頻率）═════════════
def fit_one(job):
    tg, fq = job
    d = _G["DS"][_G["DS"]["freq"] == fq]
    cols = _G["cols"]; isflag = [c.startswith("x_miss_") for c in cols]
    yc = f"y{tg}"
    yf = d.groupby("year")["e"].min().to_dict()
    logloss = tg == "B"

    def ic(pv, g):
        return float(np.nanmean([ML.spearman(pv[(g["e"] == e).to_numpy()], g.loc[g["e"] == e, "ret"].to_numpy(float)) for e in sorted(g["e"].unique())]))
    tr = d[(d["tend"] < yf[2018]) & d[yc].notna()]; va = d[d["year"] == 2018]
    X, y, Xv = tr[cols].to_numpy(float), tr[yc].to_numpy(float), va[cols].to_numpy(float)
    icr = {a: ic(ML.ridge_pred(ML.ridge_fit(X, y, a), Xv), va) for a in ALPHAS}
    Ms = stump_fit(bins_of(X, isflag), y, isflag, logloss); Bv = bins_of(Xv, isflag)
    icg = {k: ic(stump_pred(Ms, Bv, k), va) for k in ROUNDS}
    al = sorted(ALPHAS, key=lambda a: (-icr[a], a))[0]; kr = sorted(ROUNDS, key=lambda k: (-icg[k], k))[0]
    PRED = []; coef = []; gains = np.zeros(len(cols)); yrs = {}
    for yy in sorted(k for k in yf if k >= 2019):
        tr = d[(d["tend"] < yf[yy]) & d[yc].notna()]; te = d[d["year"] == yy]
        X, y, Xt = tr[cols].to_numpy(float), tr[yc].to_numpy(float), te[cols].to_numpy(float)
        Mr = ML.ridge_fit(X, y, al); Mg = stump_fit(bins_of(X, isflag), y, isflag, logloss, nrounds=kr)
        PRED.append(pd.DataFrame({"target": tg, "freq": fq, "e": te["e"].to_numpy(), "sid": te["sid"].to_numpy(), "LIN": ML.ridge_pred(Mr, Xt),
                                  "GB": stump_pred(Mg, bins_of(Xt, isflag)), "ret": te["ret"].to_numpy(float), "vol60": te["vol60"].to_numpy(float)}))
        coef.append(np.abs(Mr["b"])); gains += Mg["gain"]; yrs[int(yy)] = {"訓練列": int(len(tr)), "預測列": int(len(te)), "樹數": len(Mg["trees"])}
    info = {"α 驗證 IC": icr, "α": al, "輪數 驗證 IC": icg, "輪數": kr, "年": yrs,
            "嶺迴歸 |係數| 平均前 10": [(cols[i][2:], float(v)) for i, v in sorted(enumerate(np.mean(coef, 0)), key=lambda t: -t[1])[:10]],
            "樹樁 增益合計前 10": [(cols[i][2:], float(v)) for i, v in sorted(enumerate(gains), key=lambda t: -t[1])[:10]]}
    return (tg, fq), pd.concat(PRED, ignore_index=True), info


def select(g, mdl, N, tg):
    """一期：回 (名單, vol60 缺而不入選數)。"""
    if tg != "C":
        return [s for s, _ in sorted(zip(g["sid"], g[mdl]), key=lambda t: (-t[1], t[0]))[:N]], 0
    ok = g[np.isfinite(g["vol60"].to_numpy(float))]
    rows = sorted(zip(ok["vol60"], ok["sid"], ok[mdl]), key=lambda t: (t[0], t[1]))
    n = len(rows); k = N // 5; out = []
    for q in range(5):
        grp = [(s, p) for i, (_, s, p) in enumerate(rows) if (i * 5) // n == q]
        out += [s for s, _ in sorted(grp, key=lambda t: (-t[1], t[0]))[:k]]
    return out, int(len(g) - len(ok))


def _fake(args):
    fq, N, r = args
    rng = np.random.default_rng([20260928, r])
    sel = {e: list(rng.choice(p_, size=min(N, len(p_)), replace=False)) if len(p_) else [] for e, p_ in _G["pool"][fq].items()}
    res = MX.sim_book(sel, _G["Wd"], N, t0=min(sel))
    out = {"r": r}
    for nm, (a, b) in _G["SEGP"].items():
        c, m = R13.window_stats(res["eq"], 0, len(res["eq"]), a, b + 1); out[f"{nm}_年化"] = float(c); out[f"{nm}_回落"] = float(m)
    return out


def volpct(sel, pool_vol):
    """持股 vol60 在當期可預測股票中的百分位（平均名次 ÷ 件數；vol60 缺的持股不計）。"""
    v = []
    for e, names in sel.items():
        s = pool_vol.get(e)
        if s is None:
            continue
        r = s.rank(pct=True)
        v += [float(r[x]) for x in names if x in r.index and np.isfinite(s[x])]
    return float(np.mean(v)) if v else np.nan


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchMLx {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜PREREG機器學習改目標 seq1 sha 168560f97763a287 =====")
    S = {"登錄": "PREREG機器學習改目標 seq1 sha 168560f97763a287（裁定 seq265；N ＋1）", "判定上限": "確認段合格（無早年段）⇒ 合格也只進前瞻紀錄", "閘": {}}
    Wd = MX.load_world(ML.W, a.procs, log)
    cal, n, P = Wd["cal"], Wd["n"], Wd["P"]
    rebs = Wd["rebs"]
    st = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
    br = np.r_[np.nan, Wd["bench"][1:] / Wd["bench"][:-1] - 1.0]
    ms = np.array([e - 1 for e in rebs])
    sids = Wd["sids"]
    with Pool(a.procs, initializer=ML._init, initargs=(cal, H2.H2D, ms, br)) as pool:
        TF = dict(pool.map(ML.feat_one, [(s, st.get(s, "twse")) for s in sids], chunksize=16))
    RV = ML.rev_feats(cal, rebs, sids); FF = ML.fin_feats(cal, rebs, sids, log)
    log(f"[特徵] 技術 {len(TF):,} 檔｜營收、財報完成")
    bo = D.load_stock("0050", "twse", cal).df["open"].to_numpy(float); bc = Wd["bench"]
    fq_rebs = {fq: [e for e in rebs if cal[e].month in mo] for fq, mo in FREQ.items()}
    rows = []
    for fq, rb in fq_rebs.items():
        for i, e in enumerate(rb):
            nxt = rb[i + 1] if i + 1 < len(rb) else None
            x = nxt - 1 if nxt is not None else None
            ii = int(np.searchsorted(ms, e - 1))
            bret = bc[x] / bo[e] - 1.0 if x is not None else np.nan
            for s in Wd["reb"][e]:
                tf = TF.get(s)
                if tf is None:
                    continue
                o = P[s]["o"][e]
                ret = P[s]["c"][x] / o - 1.0 if x is not None and np.isfinite(o) and o > 0 else np.nan
                rv = RV.get((e, s), (np.nan,) * 4); ff = FF.get((e, s), (np.nan,) * 5)
                v = dict(zip(ML.TECH, tf[ii])); v.update({"yoy": rv[0], "dist24": rv[1], "yoystreak": rv[2], "hi24": rv[3], "Q1": ff[0], "Q2": ff[1], "Q3": ff[2], "Q4": ff[3], "rqoq": ff[4]})
                rows.append({"freq": fq, "e": e, "year": cal[e].year, "sid": s, "ret": ret, "bret": bret, "tend": x if x is not None else 10 ** 9, **v})
    DS = pd.DataFrame(rows)
    cov = DS[DS["freq"] == "月"].groupby("e")["r12s"].apply(lambda z: z.notna().mean())
    start = int(cov[cov >= 0.5].index.min())
    DS = DS[DS["e"] >= start].reset_index(drop=True)
    assert str(cal[start].date()) == "2016-03-02", cal[start]
    parts = []
    for (fq, e), g in DS.groupby(["freq", "e"], sort=False):
        g = g.copy()
        for c in ML.FEATS:
            rk = ML.rank01(g[c].to_numpy(float)); miss = ~np.isfinite(rk)
            g[f"x_{c}"] = np.where(miss, 0.5, rk); g[f"x_miss_{c}"] = miss.astype(float)
        r = g["ret"].to_numpy(float); ok = np.isfinite(r)
        ex = r - g["bret"].to_numpy(float)
        yA = np.full(len(g), np.nan); yB = np.full(len(g), np.nan)
        if ok.sum() >= 2:
            lo, hi = np.percentile(ex[ok], [1, 99]); yA[ok] = np.clip(ex[ok], lo, hi)
            pr = pd.Series(r[ok]).rank(method="average").to_numpy() / ok.sum(); yB[ok] = (pr > 0.8).astype(float)
        g["yA"] = yA; g["yB"] = yB; g["yC"] = ML.rank01(r)
        parts.append(g)
    DS = pd.concat(parts, ignore_index=True)
    dropm = [f"x_miss_{c}" for c in ML.FEATS if DS[f"x_miss_{c}"].sum() == 0]
    DS = DS.drop(columns=dropm)
    cols = [c for c in DS.columns if c.startswith("x_")]
    S["資料集"] = {"列": {fq: int((DS["freq"] == fq).sum()) for fq in FREQ}, "訓練起點": str(cal[start].date()), "特徵欄": len(cols), "缺值旗標欄": len([c for c in cols if c.startswith("x_miss_")])}
    log(f"[資料集] {S['資料集']}")
    # 閘 ①
    ref = pd.read_csv("backtest/resultsMLlite/dataset.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    mine = DS[DS["freq"].isin(["月", "季"])].reset_index(drop=True)
    same = len(ref) == len(mine) and all(np.array_equal(ref[c].to_numpy(), mine[c].to_numpy(), equal_nan=True) for c in ["e", "ret"] + [c for c in ref.columns if c.startswith("x_")]) \
        and list(ref["sid"]) == list(mine["sid"]) and sorted(c for c in ref.columns if c.startswith("x_")) == sorted(cols)
    S["閘"]["① 月季資料集 ＝ resultsMLlite dataset（x_ 欄、ret、sid、e 逐位元）"] = bool(same)
    log(f"[閘①] {same}")
    if not same:
        raise SystemExit("⛔ 資料集與簡化版不同")
    DS[["freq", "e", "year", "sid", "ret", "bret", "tend", "vol60", "yA", "yB", "yC"] + cols].to_csv(os.path.join(OUT, "dataset.csv.gz"), index=False, float_format="%.17g")
    # 模型
    _G.update(DS=DS, cols=cols)
    jobs = [(tg, fq) for tg in TARGETS for fq in FREQ]
    with Pool(a.procs) as pool:
        R1 = pool.map(fit_one, jobs)
    with Pool(a.procs) as pool:
        R2 = pool.map(fit_one, jobs)
    PR = pd.concat([p for _, p, _ in R1], ignore_index=True); PR2 = pd.concat([p for _, p, _ in R2], ignore_index=True)
    h1 = hashlib.sha256(PR[["LIN", "GB"]].to_numpy().tobytes()).hexdigest(); h2 = hashlib.sha256(PR2[["LIN", "GB"]].to_numpy().tobytes()).hexdigest()
    S["閘"]["② 重跑兩次預測逐位元相同"] = {"sha1": h1[:16], "sha2": h2[:16], "相同": h1 == h2}
    log(f"[閘②] {S['閘']['② 重跑兩次預測逐位元相同']}")
    if h1 != h2:
        raise SystemExit("⛔ 重跑不同")
    PR.to_csv(os.path.join(OUT, "predictions.csv.gz"), index=False, float_format="%.17g")
    S["模型"] = {f"{tg}_{fq}": info for (tg, fq), _, info in R1}
    for k, v in S["模型"].items():
        log(f"  [模型 {k}] α {v['α']}（{ {a_: round(b_, 4) for a_, b_ in v['α 驗證 IC'].items()} }）｜輪數 {v['輪數']}（{ {a_: round(b_, 4) for a_, b_ in v['輪數 驗證 IC'].items()} }）")
    SEGP = {nm: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y), side="right") - 1)) for nm, (x, y) in SEGS.items()}
    IC = {}
    for (tg, fq), g0 in PR.groupby(["target", "freq"]):
        for mdl in ("LIN", "GB"):
            for nm, (x, y) in SEGP.items():
                g = g0[(g0["e"] >= x) & (g0["e"] <= y)]
                v = [ML.spearman(gg[mdl].to_numpy(float), gg["ret"].to_numpy(float)) for _, gg in g.groupby("e")]
                IC[f"{tg}_{mdl}_{fq}_{nm}"] = {"平均 IC": float(np.nanmean(v)), "IC＞0 比例": float(np.nanmean(np.array(v) > 0)), "期數": len(v)}
    S["樣本外 IC（對實際下期報酬）"] = IC
    Z = {nm: R13.window_stats(bc, 0, n, x, y + 1) for nm, (x, y) in SEGP.items()}
    S["0050"] = {nm: {"年化": float(v[0]), "回落": float(v[1]), "比值": float(v[0]) / abs(float(v[1]))} for nm, v in Z.items()}
    pool_vol = {int(e): g.set_index("sid")["vol60"] for e, g in DS[DS["freq"] == "月"].groupby("e")}
    rows = []; SEL = {}; RES = {}
    x0 = SEGP["探索"][0]
    for tg in TARGETS:
        for mdl in ("LIN", "GB"):
            for fq in FREQ:
                g0 = PR[(PR["target"] == tg) & (PR["freq"] == fq) & (PR["e"] >= x0)]
                for N in NS:
                    key = f"{tg}_{mdl}_{fq}_N{N}"; sel = {}; nmiss = 0
                    for e, g in g0.groupby("e"):
                        sel[int(e)], mm = select(g, mdl, N, tg); nmiss += mm
                    res = MX.sim_book(sel, Wd, N, t0=min(sel)); SEL[key] = sel; RES[key] = res
                    vp = volpct(sel, pool_vol)
                    for nm, (x, y) in SEGP.items():
                        c, m = R13.window_stats(res["eq"], 0, n, x, y + 1)
                        rs = [e for e in sorted(sel) if x <= e <= y]
                        tv = [res["buys"][e] / N for e in rs[1:] if e in res["buys"]]
                        cy = float(sum(res["costd"][t] / res["eq"][t - 1] for t in range(x, y + 1) if res["costd"][t] > 0) / ((y - x + 1) / 245))
                        rows.append({"格": key, "目標": tg, "模型": mdl, "頻率": fq, "N": N, "段": nm, "年化": float(c), "回落": float(m), "比值": float(c) / abs(float(m)),
                                     "標籤": MX.label(float(c), float(m), *Z[nm]), "換手": float(np.mean(tv)) if tv else np.nan, "成本／年": cy,
                                     "平均持股": float(np.mean(res["npos"][x:y + 1])), "現金比例": float(np.nanmean(res["cashf"][x:y + 1])), "強制出場": res["cnt"]["stop_force"],
                                     "vol60 百分位（全窗）": vp, "vol60 缺不入選": nmiss})
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    ex = T[T["段"] == "探索"].copy()
    ex["退化"] = (ex["平均持股"] < ex["N"] / 2) | (ex["現金比例"] > 0.30)
    ok = ex[~ex["退化"]]
    c0, m0 = Z["探索"]; ps = ok[(ok["年化"] > c0) & (ok["比值"] >= c0 / abs(m0))]
    best = (ps if len(ps) else ok).sort_values(["比值", "年化"], ascending=[False, False]).iloc[0]
    pk = best["格"]; cf = T[(T["格"] == pk) & (T["段"] == "確認")].iloc[0]
    S["挑格"] = {"格": pk, "退化排除": ex.loc[ex["退化"], "格"].tolist(), "探索過判準格數": int(len(ps)),
               "探索": {k: float(best[k]) for k in ("年化", "回落", "比值")},
               "確認": {k: (cf[k] if k == "標籤" else float(cf[k])) for k in ("年化", "回落", "比值", "換手", "成本／年", "平均持股", "現金比例", "標籤")},
               "措辭": ("確認段合格（無早年段）⇒ 只進前瞻紀錄" if cf["標籤"] == "合格" else f"確認段{cf['標籤']}")}
    log(f"[挑格] {pk}｜探索 {best['年化']:+.2%}／{best['回落']:+.2%}｜確認 {cf['年化']:+.2%}／{cf['回落']:+.2%} {cf['標籤']}")
    # 波動分位（必報）
    PKL = pd.read_csv("backtest/resultsMLlite/picks.csv.gz", dtype={"sid": str})
    lite = PKL[PKL["格"] == "RIDGE_月_N20"]
    sel_l = {int(cal.searchsorted(pd.Timestamp(d_))): list(g.sort_values("名次")["sid"]) for d_, g in lite.groupby("換股日")}
    S["持股 vol60 百分位（全窗平均；0.5 ＝ 當期中位）"] = {"挑中格": float(best["vol60 百分位（全窗）"]), "簡化版挑中格 RIDGE_月_N20": volpct(sel_l, pool_vol),
                                                "判讀": None}
    vv = S["持股 vol60 百分位（全窗平均；0.5 ＝ 當期中位）"]
    vv["判讀"] = "低波動傾向已改掉（挑中格高於簡化版且 ≥ 0.5）" if (vv["挑中格"] > vv["簡化版挑中格 RIDGE_月_N20"] and vv["挑中格"] >= 0.5) else \
        ("比簡化版高、但仍低於中位" if vv["挑中格"] > vv["簡化版挑中格 RIDGE_月_N20"] else "沒有改掉（不高於簡化版）")
    log(f"[波動分位] {vv}")
    # 各年
    res = RES[pk]; yrs = {}
    for y in range(2019, 2027):
        idx = [t for t in range(SEGP["探索"][0], SEGP["確認"][1] + 1) if cal[t].year == y]
        if idx:
            b0 = res["eq"][idx[0] - 1] if idx[0] > SEGP["探索"][0] else res["eq"][idx[0]]
            yrs[str(y)] = [float(res["eq"][idx[-1]] / b0 - 1), float(bc[idx[-1]] / bc[idx[0] - 1] - 1)]
    S["挑中格各年（本格／0050）"] = yrs
    # 假訊號
    fq, N = best["頻率"], int(best["N"])
    pool = {fq_: {int(e): sorted(g["sid"]) for e, g in PR[(PR["freq"] == fq_) & (PR["target"] == "A")].groupby("e") if e >= x0} for fq_ in FREQ}
    _G.update(Wd=Wd, pool=pool, SEGP=SEGP)
    with Pool(a.procs) as pp:
        FK = pd.DataFrame(pp.map(_fake, [(fq, N, r) for r in range(a.reps)], chunksize=20))
    FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
    S["假訊號（同池隨機，挑中格頻率與 N）"] = {nm: {"p（隨機年化 ≥ 本格）": float(np.mean(FK[f"{nm}_年化"] >= T[(T["格"] == pk) & (T["段"] == nm)]["年化"].iloc[0])),
                                           "隨機年化中位": float(FK[f"{nm}_年化"].median())} for nm in SEGP}
    log(f"[假訊號] {S['假訊號（同池隨機，挑中格頻率與 N）']}")
    # 並列
    LC = pd.read_csv("backtest/resultsMLlite/cells.csv")
    S["簡化版同頻率同 N（resultsMLlite）"] = {f"{r['格']}_{r['段']}": [float(r["年化"]), float(r["回落"]), r["標籤（描述）"]] for r in LC[(LC["頻率"] == fq) & (LC["N"] == N)].to_dict("records")} if fq in ("月", "季") else "半年無（簡化版只跑月、季）"
    SC = pd.read_csv("backtest/resultsScore/cells.csv")
    SC = SC[(SC["換股"] == {"月": "月換", "季": "季換"}.get(fq, "—")) & (SC["N"] == N) & (SC["段"] == "確認")]
    S["合成分數同格（resultsScore 確認段）"] = {f"L{int(r.L)}": [float(r.年化), float(r.回落), r.標籤] for r in SC.itertuples()} if len(SC) else "無同頻率格"
    try:
        from backtest import researchT1fix as T1
        from backtest import research11 as R11
        from backtest import rerun17 as RR
        ctx = T1.build_ctx(True)
        SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), ctx["mk"], ctx["cal"]), ctx["w1"])
        o = R11.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0), ctx["closes"], ctx["opens"], ctx["ncal"], log=[], d_max=None,
                             pick="relvol", queue_days=0, return_equity=True, stop_force=SF)
        eq13 = np.asarray(o["equity"], float)
        S["營量 v1（T1 版、stop_force 開、種子 0）"] = {nm: dict(zip(("年化", "回落"), map(float, R13.window_stats(eq13, 0, len(eq13), x, y + 1)))) for nm, (x, y) in SEGP.items()}
    except Exception as ex_:
        S["營量 v1（T1 版、stop_force 開、種子 0）"] = f"⚠ 沒算成：{ex_!r}"
    D.DATA = H2.H2D
    # 新規矩 ③
    if cf["標籤"] in ("合格", "另列"):
        sel = SEL[pk]
        ra = MX.sim_book(sel, Wd, N, mode="all", t0=min(sel)); rm = MX.sim_book(sel, Wd, N, ma_stop=MX.ma_table(Wd, Wd["sids"], 60), t0=min(sel))
        S["新規矩③ 出場敏感度（描述）"] = {nm: {"原格": [float(v) for v in R13.window_stats(res["eq"], 0, n, x, y + 1)],
                                              "全賣全買": [float(v) for v in R13.window_stats(ra["eq"], 0, n, x, y + 1)],
                                              "跌破MA60次日賣": [float(v) for v in R13.window_stats(rm["eq"], 0, n, x, y + 1)]} for nm, (x, y) in SEGP.items()}
    else:
        S["新規矩③ 出場敏感度（描述）"] = "不適用（挑中格確認段非合格／另列）"
    rows = []
    for key, sel in SEL.items():
        for e, s_ in sel.items():
            for i, s in enumerate(s_):
                rows.append({"格": key, "換股日": str(cal[e].date()), "名次": i + 1, "sid": s})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "picks.csv.gz"), index=False)
    np.save(os.path.join(OUT, "eq_pick.npy"), res["eq"])
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
