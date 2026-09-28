# -*- coding: utf-8 -*-
"""PREREG事件 seq2 獨立查核（⛔ 不 import researchEvt、avgdown、research13）。
只 import backtest.data（讀檔、還原）、tradability（漲跌停）、universe_gate（gate3）、research11（load_bars 的壞根、simulate_mtm 引擎本體）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchEvt_check.py

 ① 接合版面：抽 30 檔，自原兩版面的原始價與 adj 逐事件因子（official 優先）自乘 ⇒ 全段還原收盤 ≈ 接合版面 load_stock（相對差 ＜ 1e−6；早年 cum_factor 檔內捨入約 1e−7）
 ② 事件：自庫藏股原檔重做類型、合併（20 日）⇒ 各類型件數 ＝ summary
 ③ 單筆：抽 40 筆保留事件，自算 R_H 與當日同池十分位基準 X（自寫母體規則、r20、十分位）＝ events_treasury
 ④ 格統計：自 events 檔重算 n、平均、CR0、Bonferroni k 與 z、判定 ＝ single.csv（庫藏股與臺灣50）
 ⑤ 假訊號 p：自 fake_single 重算 ＝ single.csv
 ⑥ 組合層：自寫挑中格訊號（自算母體、可買、斷點、R）⇒ simulate_mtm 種子 0 權益 ＝ eq_pick_seed0.npy（逐位元）；
    自 port_seeds 重算各格中位、標籤、退化、挑格 ＝ port_cells、summary
"""
from __future__ import annotations
import json, math, os, sys
from statistics import NormalDist
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG
from backtest import research11 as R11

EARLY = os.path.expanduser("~/earlydata/950ad26e12/main/data")
MAIN = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_edc6f8002f/data")
OUT = "backtest/resultsEvt"
COST = 0.00585
HS = (5, 10, 20, 60, 120)


def raw_adj_close(s, cal):
    """自原兩版面：原始收盤 × Π(事件日 ＞ d 的因子)，事件 ＝ 早年 adj 全部 ＋ main adj 中 > 2014-12-31 者（逐事件因子自乘：factor_official 有值用它、否則 factor；⛔ 不用 cum_factor）。"""
    px = []; ev = []
    for root, lo, hi in ((EARLY, None, "2014-12-31"), (MAIN, "2015-01-05", None)):
        p = os.path.join(root, "stocks", s + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"date": str}, usecols=["date", "close"])
            x = x[(x["date"] <= hi) if hi else (x["date"] >= lo)]
            px.append(x)
        a = os.path.join(root, "adj", s + ".csv")
        if os.path.exists(a):
            y = pd.read_csv(a, dtype={"date": str}, usecols=["date", "factor", "factor_official"])
            y["factor"] = y["factor_official"].where(y["factor_official"].notna(), y["factor"])
            if lo:
                y = y[y["date"] > "2014-12-31"]
            ev.append(y)
    px = pd.concat(px).drop_duplicates("date").set_index("date")["close"]
    c = pd.to_numeric(px, errors="coerce"); c[c <= 0] = np.nan
    ev = pd.concat(ev) if ev else pd.DataFrame(columns=["date", "factor"])
    ed = pd.to_datetime(ev["date"]).to_numpy(); ef = ev["factor"].astype(float).to_numpy()
    dts = pd.to_datetime(c.index)
    F = np.array([np.prod(ef[ed > d]) for d in dts.to_numpy()])
    return pd.Series(c.to_numpy() * F, index=dts).reindex(cal).to_numpy(float)


def main():
    RES = {}
    D.DATA = ST
    cal = D.load_calendar(); n = len(cal)
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    SG = pd.read_csv(os.path.join(OUT, "single.csv"))
    roster = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(roster); mk = dict(zip(roster["stock_id"], roster["market"]))
    rng = np.random.default_rng(20260928)
    # ①
    sids_all = sorted(set(U["stock_id"]) & {f[:-4] for f in os.listdir(os.path.join(ST, "stocks"))})
    mx = 0.0
    for s in sorted(rng.choice(sids_all, 30, replace=False)):
        a = raw_adj_close(s, cal); b = D.load_stock(s, mk.get(s, "twse"), cal).df["close"].to_numpy(float)
        ok = np.isfinite(a) & np.isfinite(b)
        assert (np.isfinite(a) == np.isfinite(b)).all(), s
        if ok.any():
            mx = max(mx, float(np.max(np.abs(a[ok] / b[ok] - 1))))
    RES["① 接合版面 30 檔還原收盤（相對差；早年 adj 檔 cum_factor 本身存到約 1e−7 精度）"] = {"最大差": mx, "過": mx < 1e-6}
    print(RES, flush=True)
    # ②
    t = pd.read_csv(os.path.expanduser("~/evtdata/treasury_buyback.csv"), dtype={"stock_id": str, "purpose": str})
    t["T"] = cal.searchsorted(pd.to_datetime(t["board_date"]), side="right") - 1
    t = t[(t["T"] >= 0) & (t["T"] < n - 1)]
    cnt = {}
    for tn, pv in (("全部", None), ("目的1", "1"), ("目的3", "3"), ("目的2（描述）", "2")):
        e = t if pv is None else t[t["purpose"] == pv]
        kept = 0
        for s, g in e.groupby("stock_id"):
            last = None
            for T in sorted(g["T"]):
                if last is not None and T - last <= 20:
                    continue
                kept += 1; last = T
        cnt[tn] = kept
    RES["② 類型、合併件數"] = {"自算": cnt, "過": cnt == S["庫藏股合併後"]}
    # 載入全部股票（③⑥ 用）
    print("loading", flush=True)
    P = {}
    for s in sids_all:
        st = D.load_stock(s, mk.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float); o = st.df["open"].to_numpy(float)
        B = R11.load_bars(s, mk.get(s, "twse"), cal)
        raw = pd.read_csv(os.path.join(ST, "stocks", s + ".csv"), dtype={"date": str}, usecols=["date", "market", "amount"]).drop_duplicates("date")
        raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
        tb = TR.one(s, cal)
        P[s] = {"c": c, "cff": pd.Series(c).ffill().to_numpy(), "o": o, "tw": (raw["market"] == "twse").to_numpy(), "amt": pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float),
                "trd": np.asarray(tb["trd"], bool), "up": np.asarray(tb["up_o"], bool), "dn": np.asarray(tb["dn_o"], bool), "dc": np.asarray(tb["dn_c"], bool), "B": (B["idx"], B["next_bad"]) if B is not None else None}
    print("loaded", len(P), flush=True)
    sids = sorted(P)
    # 母體（自寫）
    tf = lambda x: x.astype(str).isin(["True", "1", "1.0"])
    ep = pd.read_csv(os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz"), dtype={"stock_id": str}, parse_dates=["measure_date"])
    mp = pd.read_csv("backtest/resultsp9_engine/panel_ext.csv.gz", dtype={"stock_id": str}, parse_dates=["measure_date"])
    MS = []
    for md, g in ep.groupby("measure_date"):
        m_ = tf(g["eligible"]) if md >= pd.Timestamp("2012-06-01") else (tf(g["liq_ok"]) & tf(g["bars_ok"]))
        MS.append((md, set(g["stock_id"][m_.to_numpy()])))
    for md, g in mp.groupby("measure_date"):
        if md >= pd.Timestamp("2015-08-01"):
            MS.append((md, set(g["stock_id"][tf(g["eligible"]).to_numpy()]))); continue
        pos = int(cal.searchsorted(md))

        def nb(s):
            return int(np.isfinite(P[s]["c"][:pos + 1]).sum()) if s in P else 0
        if md >= pd.Timestamp("2015-02-01"):
            m_ = tf(g["liq_ok"]) & tf(g["inst_ok"])
            MS.append((md, {s for s in g["stock_id"][m_.to_numpy()] if nb(s) >= 120}))
        else:
            ss = set()
            for s in g["stock_id"]:
                if nb(s) >= 120:
                    v = np.flatnonzero(np.isfinite(P[s]["c"][:pos + 1]))[-20:]
                    if len(v) == 20 and np.nanmean(P[s]["amt"][v]) >= 5e7:
                        ss.add(s)
            MS.append((md, ss))
    MS.sort(key=lambda x: x[0]); mdp = np.array([int(cal.searchsorted(m)) for m, _ in MS])
    gate = set(U["stock_id"])

    def elig(s, T):
        j = int(np.searchsorted(mdp, T, side="right") - 1)
        return j >= 0 and s in MS[j][1] and s in gate
    bi = int(cal.searchsorted(pd.Timestamp("2015-01-05")))

    def Rh(s, T, H):
        p = P[s]
        if not (np.isfinite(p["c"][T]) and p["trd"][T + 1] and np.isfinite(p["o"][T + 1]) and p["o"][T + 1] > 0 and not p["up"][T + 1]) or p["B"] is None:
            return np.nan
        idx, nbd = p["B"]; k = int(np.searchsorted(idx, T)); x = min(T + H, n - 1); kx = int(np.searchsorted(idx, x, side="right") - 1)
        if nbd[max(k - 19, 0)] <= kx:
            return np.nan
        return p["cff"][x] / p["o"][T + 1] - 1.0

    def r20(s, T):
        idx = np.flatnonzero(np.isfinite(P[s]["c"]))
        k = int(np.searchsorted(idx, T))
        if k >= len(idx) or idx[k] != T or k < 20:
            return np.nan
        return P[s]["c"][T] / P[s]["c"][idx[k - 20]] - 1.0
    # ③
    EVT = pd.read_csv(os.path.join(OUT, "events_treasury.csv.gz"), dtype={"stock_id": str}, float_precision="round_trip")
    smp = EVT.iloc[np.sort(rng.choice(len(EVT), 40, replace=False))]
    m3 = 0.0; bad3 = []
    for r in smp.itertuples():
        T, H = int(r.T), int(r.H)
        pool = []
        for s in sids:
            if not elig(s, T) or (T < bi and not P[s]["tw"][T]):
                continue
            rr = Rh(s, T, H); q = r20(s, T)
            if np.isfinite(rr) and np.isfinite(q):
                pool.append((q, s, rr))
        pool.sort(key=lambda z: (z[0], z[1]))
        m = len(pool); dec = {s: (i * 10) // m for i, (_, s, _) in enumerate(pool)}; Rv = {s: rr for _, s, rr in pool}
        me = r.stock_id
        if me not in dec:
            bad3.append((me, T, H, "不在池")); continue
        oth = [Rv[s] for s in dec if dec[s] == dec[me] and s != me]
        x = Rv[me] - float(np.mean(oth))
        m3 = max(m3, abs(Rv[me] - r.R), abs(x - r.X))
    RES["③ 單筆 40 筆 R 與基準② X"] = {"最大差": m3, "不符": bad3, "過": m3 < 1e-12 and not bad3}
    print(RES, flush=True)
    # ④
    def cr0(x, mon):
        mu = x.mean(); s_ = pd.Series(x - mu).groupby(mon).sum().to_numpy()
        return mu, math.sqrt(float((s_ ** 2).sum())) / len(x)
    kk = S["庫藏股可判定格數 k"]; mx4 = 0.0; bad4 = []
    for r in SG[(SG["問"] == "庫藏股") & (SG["n"] > 0)].itertuples():
        g = EVT[(EVT["類型"] == r.類型) & (EVT["H"] == r.H) & (EVT["段"] == r.段)]
        x = g["X"].to_numpy() - COST; mon = np.array([str(cal[int(t)])[:7] for t in g["T"]])
        mu, se = cr0(x, mon); z = NormalDist().inv_cdf(1 - 0.05 / (2 * max(kk[r.段], 1)))
        lo, hi = mu - z * se, mu + z * se
        v = ("依構造不可判定（n＜100）" if len(x) < 100 else ("描述" if (r.段 == "探索" or "描述" in r.類型) else ("測得出（＋）" if lo > 0 else ("測得出（−）" if hi < 0 else "測不出"))))
        mx4 = max(mx4, abs(mu - r.平均), abs(lo - r.lo), abs(hi - r.hi))
        if v != r.判定 or len(x) != r.n:
            bad4.append((r.類型, r.H, r.段))
    # 可判定格數 k 自算
    k_self = {}
    for sg in ("早年", "探索", "確認"):
        k_self[sg] = int(sum(1 for tn in ("全部", "目的1", "目的3") for H in HS if ((EVT["類型"] == tn) & (EVT["H"] == H) & (EVT["段"] == sg)).sum() >= 100))
    RES["④ 庫藏股格統計、k、判定"] = {"最大差": mx4, "不符": bad4, "k 自算": k_self, "過": mx4 < 1e-12 and not bad4 and all(k_self[s] == kk[s] for s in k_self)}
    # ⑤
    FK = pd.read_csv(os.path.join(OUT, "fake_single.csv.gz"), float_precision="round_trip"); bad5 = []
    for (tn, H, sg), g in FK.groupby(["類型", "H", "段"]):
        r = SG[(SG["問"] == "庫藏股") & (SG["類型"] == tn) & (SG["H"] == H) & (SG["段"] == sg)].iloc[0]
        p = float(np.mean(g["假平均"].to_numpy() >= r["平均"]))
        if abs(p - r["假訊號 p"]) > 1e-12:
            bad5.append((tn, H, sg))
    RES["⑤ 假訊號 p（庫藏股）"] = {"不符": bad5, "過": not bad5}
    print(RES, flush=True)
    # ⑥
    pk = S["組合層挑格"]["格"]; tn, Hs = pk.split("_H"); H = int(Hs)
    pv = {"全部": None, "目的1": "1", "目的3": "3"}[tn]
    e = t if pv is None else t[t["purpose"] == pv]
    ev = []
    for s, g in e.sort_values(["stock_id", "T", "seq"]).groupby("stock_id"):
        last = None
        for T in g["T"]:
            if last is not None and last <= T <= last + 20:
                continue
            ev.append((s, int(T))); last = T
    w0 = int(cal.searchsorted(pd.Timestamp("2005-01-03"))); w1 = int(cal.searchsorted(pd.Timestamp("2026-08-24"), side="right") - 1)
    rows = []
    for s, T in ev:
        if s not in P or not elig(s, T) or (T < bi and not P[s]["tw"][T]) or not (w0 <= T + 1 <= w1):
            continue
        rr = Rh(s, T, H)
        if np.isfinite(rr):
            rows.append((s, T + 1, T + H if T + H <= n - 1 else n, rr))
    sig = pd.DataFrame(rows, columns=["sid", "entry_pos", f"xpos_H{H}", f"g_H{H}"]).sort_values(["sid", "entry_pos"]).reset_index(drop=True)
    trad = {s: {"trd": P[s]["trd"], "up_o": P[s]["up"], "dn_o": P[s]["dn"], "dn_c": P[s]["dc"]} for s in sids}
    dl = TR.delist_status({s: {"trd": P[s]["trd"]} for s in sids}, cal, official=TR.load_official())
    SF = {s: int(np.flatnonzero(np.isfinite(P[s]["c"]))[-1]) for s in sids if np.isfinite(P[s]["c"]).any() and np.flatnonzero(np.isfinite(P[s]["c"]))[-1] < w1}
    out = R11.simulate_mtm(sig, f"H{H}", 10, np.random.default_rng([20260928, ("全部", "目的1", "目的3").index(tn), H, 0]), {s: P[s]["cff"] for s in sids}, {s: P[s]["o"] for s in sids}, n,
                           return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=trad, delist=dl, stop_force=SF)
    eq = np.asarray(out["equity"], float); ref = np.load(os.path.join(OUT, "eq_pick_seed0.npy"))
    RES["⑥a 挑中格自寫訊號 ⇒ 種子 0 權益"] = {"訊號筆": int(len(sig)), "逐位元": bool(np.array_equal(eq, ref)), "最大差": float(np.max(np.abs(eq - ref))), "過": bool(np.array_equal(eq, ref))}
    PT = pd.read_csv(os.path.join(OUT, "port_seeds.csv.gz"), float_precision="round_trip"); PC = pd.read_csv(os.path.join(OUT, "port_cells.csv"), float_precision="round_trip")
    Z = S["0050"]; bad6 = []
    for r in PC.itertuples():
        g = PT[(PT["類型"] == r.類型) & (PT["H"] == r.H)]
        c_ = g[f"{r.段}_年化"].median(); m_ = g[f"{r.段}_回落"].median(); c0, m0 = Z[r.段]["年化"], Z[r.段]["回落"]
        lab = "合格" if (c_ > c0 and c_ / abs(m_) >= c0 / abs(m0)) else ("另列" if c_ > c0 else "不合格")
        if abs(c_ - r.年化中位) > 1e-15 or abs(m_ - r.回落中位) > 1e-15 or lab != r.標籤:
            bad6.append((r.類型, r.H, r.段))
    ex = PC[PC["段"] == "探索"].copy(); ex = ex[~((ex["年均事件"] < 10) | ex["恆為0"])]
    c0, m0 = Z["探索"]["年化"], Z["探索"]["回落"]
    ps = ex[(ex["年化中位"] > c0) & (ex["比值"] >= c0 / abs(m0))]
    b = (ps if len(ps) else ex).sort_values(["比值", "年化中位"], ascending=[False, False]).iloc[0]
    RES["⑥b 組合層中位、標籤、退化、挑格"] = {"不符": bad6, "自挑": f"{b['類型']}_H{int(b['H'])}", "過": not bad6 and f"{b['類型']}_H{int(b['H'])}" == pk}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
