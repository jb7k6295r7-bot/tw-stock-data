# -*- coding: utf-8 -*-
"""稽核 ② 5 G1／G3 重測 獨立查核（⛔ 不 import researchAudit2_5、research34、evaluate、patterns、avgdown）。只 import backtest.data（讀檔）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_5_check.py

 ① 每段抽 40 檔：逐列自算 ret5／ret10／ret20／ret60（第 n 日收盤、跌停鎖死（h＝l 且 c ≤ 前收×0.905）或無收盤就順延 ≤ 10 日、
    仍不行 ⇒ 窗內最後一根收盤）與 r20（有效 K 棒 20 根前收盤）⇒ ＝ panel_*.csv.gz
 ② 由面板自算：X1（同換股日平均）、X2（同換股日前 20 日報酬十分位，rank×10//n、同值依股票代號序；自己不算）、段、G1／G3／C1 遮罩、
    兩種成本口徑、CR0（換股月）、n_eff、出口、結果；G3 − C1 同月配對；下市月營收下界（−100％／0％）⇒ ＝ summary.json
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/5")
SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
HS = (5, 10, 20, 60)
COST, TOL = 0.00585, 1e-12


def hold(o, h, l, c, pc, e0, n):
    e = e0 + n - 1; N = len(c)
    if e >= N:
        return np.nan
    j = e; k = 0
    while j < N and (np.isnan(c[j]) or ((not np.isnan(h[j])) and h[j] == l[j] and (not np.isnan(pc[j])) and c[j] <= pc[j] * 0.905)) and k < 10:
        j += 1; k += 1
    if j >= N or np.isnan(c[j]):
        seg = c[e0:e + 1]
        if np.isnan(seg).all():
            return np.nan
        j = e0 + int(np.flatnonzero(~np.isnan(seg))[-1])
    return c[j] / o[e0] - 1


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, np.sqrt((s ** 2).sum()) / n, len(s)


def judge(x, g):
    x = np.asarray(x, float); ok = np.isfinite(x); x, g = x[ok], np.asarray(g)[ok]
    m, se, ng = cr0(x, g); ne = min(len(x), ng); lo, hi = m - 1.96 * se, m + 1.96 * se
    rs = "樣本不足以分辨" if ne < 30 else ("結果①" if lo <= 0 <= hi else ("結果②" if m > 0 else "結果③"))
    return m, lo, rs


def dec(r):
    d = np.full(len(r), -1); ok = np.flatnonzero(np.isfinite(r)); n = len(ok)
    if n:
        order = ok[np.lexsort((ok, r[ok]))]; d[order] = (np.arange(n) * 10) // n
    return d


def main():
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES = {}
    PAN = {"主": pd.read_csv(os.path.join(OUT, "panel_main.csv.gz"), dtype={"stock_id": str, "period": str}, float_precision="round_trip"),
           "早年": pd.read_csv(os.path.join(OUT, "panel_early.csv.gz"), dtype={"stock_id": str, "period": str}, float_precision="round_trip")}
    # ①
    rng = np.random.default_rng(20260928); m1 = 0.0; nr = 0
    for nm, data in (("主", SNAP), ("早年", EARLY)):
        D.DATA = data; cal = D.load_calendar(); P = PAN[nm]
        for sid in rng.choice(sorted(P["stock_id"].unique()), 40, replace=False):
            g = P[P["stock_id"] == sid]
            st = D.load_stock(sid, g["market"].iloc[0], cal); df = st.df
            o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
            pc = df["close"].shift(1).to_numpy(float)
            b = np.flatnonzero(np.isfinite(c)); r20 = np.full(len(c), np.nan)
            if len(b) > 20:
                r20[b[20:]] = c[b[20:]] / c[b[:-20]] - 1
            for r in g.itertuples():
                for H in HS:
                    v = hold(o, h, l, c, pc, int(r.entry_pos), H); w = getattr(r, f"ret{H}")
                    if not (np.isnan(v) and np.isnan(w)):
                        m1 = max(m1, abs(v - w))
                w = r.r20; v = r20[int(r.signal_pos)]
                if not (np.isnan(v) and np.isnan(w)):
                    m1 = max(m1, abs(v - w))
                nr += 1
    RES["① 抽 80 檔逐列 ret5／10／20／60、r20"] = {"列數": nr, "最大差": m1, "過": m1 <= TOL}
    print(RES, flush=True)
    # ②
    bad = []
    for nm, P in PAN.items():
        P = P.copy()
        for c_ in ("rev_hi24", "bull"):
            P[c_] = P[c_].map({"True": True, "False": False, True: True, False: False})
        y = pd.to_datetime(P["signal_date"]).dt.year
        for H in HS:
            col = f"ret{H}"
            Q = P[np.isfinite(P[col].astype(float))].sort_values(["period", "stock_id"]).reset_index(drop=True)
            Q["b1"] = Q.groupby("period")[col].transform("mean"); Q["X1"] = Q[col] - Q["b1"]
            x2 = np.full(len(Q), np.nan)
            for p, g in Q.groupby("period", sort=False):
                idx = g.index.to_numpy(); d = dec(g["r20"].to_numpy(float)); v = g[col].to_numpy(float)
                for k in range(10):
                    mk = d == k
                    if mk.sum() >= 2:
                        x2[idx[mk]] = v[mk] - (v[mk].sum() - v[mk]) / (mk.sum() - 1)
            Q["X2"] = x2
            ok_end = (Q["entry_pos"] + H - 1) <= Q["w_end"]
            yy = pd.to_datetime(Q["signal_date"]).dt.year
            segs = ({"探索 2016～2020": ok_end & (yy >= 2016) & (yy <= 2020), "確認 2021～2026": ok_end & (yy >= 2021)} if nm == "主"
                    else {"早年 2012～2014": ok_end & (yy >= 2012) & (yy <= 2014)})
            for sn, sm in segs.items():
                G = Q[sm]; ref = Sm["結果"][f"{sn}｜H{H}"]
                g1 = G["rev_hi24"] == True; c1 = G["bull"] == True; g3 = g1 & c1
                for tag, m in (("G1", g1), ("G3", g3), ("C1（描述）", c1)):
                    X = G[m]
                    for xn in ("X1", "X2"):
                        for cn, sh in (("甲互抵", 0.0), ("乙對成本", COST)):
                            mm, lo, rs = judge(X[xn] - sh, X["period"])
                            rr = ref[tag][f"{xn} {cn}"]
                            if abs(mm - rr["mean"]) > TOL or abs(lo - rr["lo"]) > TOL or rs != rr["結果"]:
                                bad.append((sn, H, tag, xn, cn))
                a3 = G[g3].groupby("period")[col].mean(); ac = G[c1].groupby("period")[col].mean(); dd = (a3 - ac).dropna()
                if len(dd) >= 2 and abs(dd.mean() - ref["G3 − C1 同月配對"]["mean"]) > TOL:
                    bad.append((sn, H, "G3−C1"))
                miss = G[G["rev_hi24"].isna()]
                for tag, m in (("G1", g1), ("G3", g3)):
                    add = miss if tag == "G1" else miss[miss["bull"] == True]
                    for v, lab in ((-1.0, "−100％"), (0.0, "0％")):
                        x = np.r_[G[m]["X1"].to_numpy(float), v - add["b1"].to_numpy(float)]
                        gg = np.r_[G[m]["period"].to_numpy(), add["period"].to_numpy()]
                        mm, lo, rs = judge(x, gg); rr = ref["下市月營收下界"][f"{tag} 下界 {lab}（X1 甲）"]
                        if abs(mm - rr["mean"]) > TOL or rs != rr["結果"]:
                            bad.append((sn, H, tag, lab))
    RES["② 全部格（G1／G3／C1 × X1／X2 × 兩口徑、G3−C1、下界）"] = {"不符": bad[:20], "不符數": len(bad), "過": not bad}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
