# -*- coding: utf-8 -*-
"""稽核 ② 2 四類單獨 AD10 重測 獨立查核（⛔ 不 import researchAudit2_2、researchQuad、researchAvg、avgdown）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_2_check.py

共用只到資料層：backtest.data（快照讀檔）、backtest.tradability.one（漲跌停與有無成交）。其餘自寫。
 ① 抽 40 檔：每一筆保留持有（三個 H、兩段）自算 AD10 觸發日、成交日、d_AD10、隨機日（同一 rng 規格）、d_rand、0050 腿、X ⇒ ＝ holdings.csv.gz
 ② 抽 300 筆被觸發事件：自算同一進場批在 d 當天的前 20 日報酬十分位與配對股報酬 ⇒ ȳ ＝ holdings.csv.gz
 ③ 由 holdings.csv.gz 自算六格 × 四量的平均、CR0 CI、出口與結果 ⇒ ＝ summary.json
"""
from __future__ import annotations
import json, os, sys, zlib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR

D.DATA = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/2")
COST, COST_ETF = 0.00585, 0.00385
TOL = 1e-12


def load(sid, mk, cal):
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return None
    o = st.df["open"].to_numpy(float); c = st.df["close"].to_numpy(float); v = np.isfinite(c)
    tb = TR.one(sid, cal)
    okb = np.asarray(tb["trd"], bool) & ~np.asarray(tb["up_o"], bool) & np.isfinite(o) & (np.nan_to_num(o) > 0)
    lv = np.full(len(c), -1); last = -1
    for i in range(len(c)):
        if v[i]:
            last = i
        lv[i] = last
    bars = np.flatnonzero(v); r20 = np.full(len(c), np.nan)
    if len(bars) > 20:
        r20[bars[20:]] = c[bars[20:]] / c[bars[:-20]] - 1.0
    return {"o": o, "c": c, "v": v, "okb": okb, "lv": lv, "r20": r20}


def nxt(okb, t, x):
    for u in range(t, x):
        if okb[u]:
            return u
    return -1


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, np.sqrt((s ** 2).sum()) / n, len(s)


def verdict(m, lo, hi, neff):
    if neff < 30:
        return "出口①", "—（樣本不足以分辨）"
    ex = "出口②" if neff < 100 else "出口③"
    return (ex, "結果①") if lo <= 0 <= hi else (ex, "結果③" if m < 0 else "結果②")


def main():
    cal = D.load_calendar(); ncal = len(cal)
    K = pd.read_csv(os.path.join(OUT, "holdings.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    s50 = D.load_stock("0050", "twse", cal).df
    o50 = s50["open"].to_numpy(float); c50 = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy()
    RES = {}; bad = []
    # ① 抽 40 檔
    rng = np.random.default_rng(20260928)
    allsid = sorted(K["sid"].unique())
    samp = sorted(rng.choice(allsid, size=40, replace=False))
    mkt = K.drop_duplicates("sid").set_index("sid")["market"]
    PX = {}
    mx = 0.0; nrow = 0; mism = []
    for sid in samp:
        P = load(sid, mkt[sid], cal); PX[sid] = P
        for r in K[(K["sid"] == sid) & (K["status"] == "保留")].itertuples():
            e, H = int(r.e), int(r.H); x = e + H - 1; P0 = P["o"][e]; cj = P["c"][P["lv"][x]]
            d = -1
            for t in range(e, x):
                if P["v"][t] and P["c"][t] <= P0 * 90 / 100:
                    d = t; break
            s = nxt(P["okb"], d + 1, x) if d >= 0 else -1
            dad = 0.5 * (cj / P["o"][s] - 1 - COST) if s >= 0 else 0.0
            nrow += 1
            if int(s >= 0) != int(r.t_AD10) or abs(dad - r.d_AD10) > TOL:
                mism.append((sid, e, H, "AD10")); continue
            if s < 0:
                continue
            cand = np.flatnonzero(P["okb"][e + 1:x]) + e + 1
            g = np.random.default_rng([20260928, H, zlib.crc32(sid.encode()), e])
            sr = int(cand[g.integers(len(cand))])
            drd = 0.5 * (cj / P["o"][sr] - 1 - COST)
            s50 = s
            while s50 < x and not (np.isfinite(o50[s50]) and o50[s50] > 0):
                s50 += 1
            d50 = 0.5 * (c50[x] / o50[s50] - 1 - COST_ETF) if s50 < x else np.nan
            X = cj / P["o"][s] - 1
            mx = max(mx, abs(drd - r.d_rand), abs(d50 - r.d_0050) if np.isfinite(d50) else 0.0, abs(X - r.X))
            if sr != int(r.s_rand):
                mism.append((sid, e, H, "rand"))
    RES["① 抽 40 檔逐筆（AD10、隨機日、0050 腿、X）"] = {"筆數": nrow, "不符": mism[:10], "不符數": len(mism), "最大差": mx, "過": (not mism) and mx <= TOL}
    print(RES["① 抽 40 檔逐筆（AD10、隨機日、0050 腿、X）"], flush=True)
    # ② 基準②：抽 300 筆被觸發事件
    T_ = K[(K["status"] == "保留") & (K["t_AD10"] == 1) & K["ybar"].notna()]
    pick = T_.iloc[np.sort(np.random.default_rng(7).choice(len(T_), size=300, replace=False))]
    need = set()
    for r in pick.itertuples():
        need |= set(K[(K["status"] == "保留") & (K["H"] == r.H) & (K["e"] == r.e)]["sid"])
    for sid in sorted(need - set(PX)):
        PX[sid] = load(sid, mkt[sid], cal)
    mx2 = 0.0; np_bad = 0
    for r in pick.itertuples():
        H, e, d, x = int(r.H), int(r.e), int(r.trig_d), int(r.x)
        coh = sorted(K[(K["status"] == "保留") & (K["H"] == H) & (K["e"] == e)]["sid"])
        rv = np.array([PX[s]["r20"][d] for s in coh])
        ok = np.flatnonzero(np.isfinite(rv))
        order = ok[np.lexsort((ok, rv[ok]))]
        dec = np.full(len(coh), -1); dec[order] = (np.arange(len(ok)) * 10) // len(ok)
        me = coh.index(r.sid)
        f = []
        for k, s in enumerate(coh):
            if k == me or dec[k] != dec[me]:
                continue
            P = PX[s]; t = nxt(P["okb"], d + 1, x) if d + 1 < ncal else -1
            if t < 0:
                continue
            v = P["c"][P["lv"][x]] / P["o"][t] - 1
            if np.isfinite(v):
                f.append(v)
        yb = float(np.mean(f)) if f else np.nan
        np_bad += int(len(f) != int(r.n_peer))
        mx2 = max(mx2, abs(yb - r.ybar))
    RES["② 基準② 300 筆（ȳ、配對股數）"] = {"最大差": mx2, "配對股數不符": np_bad, "過": mx2 <= TOL and np_bad == 0}
    print(RES["② 基準② 300 筆（ȳ、配對股數）"], flush=True)
    # ③ 統計
    mon = np.array([str(t)[:7] for t in cal]); b3 = []
    for key, cell in Sm["結果"].items():
        H = int(key.split("_")[0][1:]); seg = key.split("_")[1]
        G = K[(K["H"] == H) & (K["seg"] == seg) & (K["status"] == "保留")]
        for nm, col, sub in (("AD10 − 不加（原件判定量）", "d_AD10", False), ("AD10 − ①隨機日加碼", "c_rand", True),
                             ("AD10 − ②同日改買 0050", "c_0050", True), ("AD10 − ③基準②（前 20 日同分位）", "c_b2", True)):
            g = G[G["t_AD10"] == 1] if sub else G
            v = g[col].to_numpy(float); okm = np.isfinite(v)
            m, se, ng = cr0(v[okm], mon[g["e"].to_numpy(int)][okm])
            lo, hi = m - 1.96 * se, m + 1.96 * se
            ex, rs = verdict(m, lo, hi, min(int(okm.sum()), ng))
            ref = cell[nm]
            if abs(m - ref["mean"]) > 1e-12 or abs(lo - ref["lo"]) > 1e-12 or rs != ref["結果"] or ex != ref["出口"]:
                b3.append((key, nm))
    RES["③ 六格 × 四量 平均、CI、出口、結果"] = {"不符": b3, "過": not b3}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
