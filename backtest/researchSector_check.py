# -*- coding: utf-8 -*-
"""PREREG強勢類股 本體的獨立查核（⛔ 不 import researchSector；只讀它的輸出檔對數）。

    python -m backtest.researchSector_check [--procs 2]

另走一條路重算：
 ① U4 對帳：merge 兩份面板（量測日 ≤ 2026-03-02）逐列比 eligible／market，另數兩邊多出的列
 ② 換股日：自己從交易日曆找「每月 10 日之後第一個交易日」，對 picks.csv.gz 的換股日
 ③ 名單：用 pandas groupby 另算類股強度與排名，挑中格【全部】換股日＋另 17 格抽 8 個換股日（含 panel_ext 才有的 2026-04～08），逐名次比 picks.csv.gz
 ④ 權益：自己寫的逐日帳（持股與待賣分開記、下市狀態自己判）用 picks.csv.gz 的名單重模擬挑中格（續抱）與（全賣全買），對 eq_cells.npz
 ⑤ 指標：自己寫年化／回落（245 日、窗首收盤為基）重算挑中格兩段、0050 兩段、判定與探索挑格
 ⑥ 對照：(c) 與假訊號臂各重跑 r＝0、1、2（自己算的排名＋同一個 rng 呼叫序），對 controls.csv.gz
共用（⛔ 沒有另寫）：data.load_stock（還原價）、tradability.one（漲跌停旗標）、p4_features.rev_hi24_flags（營收 24 月新高）、research34.load_revenue。
"""
from __future__ import annotations
import os, sys, json, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D, TR, UG = H2.D, H2.TR, H2.UG
from backtest import research34 as R34
from backtest import p4_features as P4F

OUT = "backtest/resultsSector"
COST = 0.00585
_G = {}


def _load(args):
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    tb = TR.one(sid, cal)
    return sid, (pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(float), st.df["open"].to_numpy(float), tb["trd"], tb["up_o"], tb["dn_o"])


def _init(cal):
    _G["cal"] = cal


def my_stats(eq, a, b):
    seg = np.asarray(eq[a:b + 1], float)
    cagr = (seg[-1] / seg[0]) ** (245.0 / len(seg)) - 1
    mdd = float(np.min(seg / np.maximum.accumulate(seg) - 1))
    return float(cagr), mdd


def my_sim(picks, px, st, t0, t1, allmode=False):
    """獨立逐日帳：book ＝ {sid: (股數, 進場金額)}，queue ＝ 待賣。"""
    n = len(next(iter(px.values()))[0])
    eq = np.ones(n); cash = 1.0; book = {}; queue = []
    for t in range(t0, t1 + 1):
        if t in picks:
            want = picks[t]
            queue = sorted(set(book)) if allmode else sorted((set(queue) | set(book)) - set(want))
        left = []
        for s in queue:
            c, o, trd, up, dn = px[s]
            if trd[t] and not dn[t] and o[t] == o[t] and o[t] > 0:
                p = o[t]
            elif (not trd[t]) and st[s][1].startswith("delisted") and t > st[s][0]:
                p = c[t]
            else:
                left.append(s); continue
            u, amt = book.pop(s)
            cash = cash + u * p - amt * COST
        queue = left
        if t in picks:
            room = 10 - len(book); todo = [s for s in picks[t] if s not in book][:max(room, 0)]
            for s in todo:
                c, o, trd, up, dn = px[s]
                if not trd[t] or not (o[t] == o[t] and o[t] > 0) or up[t]:
                    continue
                amt = min(eq[t - 1] / 10.0, cash)
                if amt <= 1e-12:
                    break
                book[s] = (amt / o[t], amt); cash -= amt
        eq[t] = cash + sum(u * px[s][0][t] for s, (u, _) in book.items())
    return eq


def main():
    t00 = time.time()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    J = json.load(open(os.path.join(OUT, "body.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    PK = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str})
    Z = np.load(os.path.join(OUT, "eq_cells.npz"))
    CT = pd.read_csv(os.path.join(OUT, "controls.csv.gz"))
    R = {}
    cal = D.load_calendar(); n = len(cal)
    t0 = int(np.flatnonzero(cal == pd.Timestamp("2017-03-02"))[0]); t1 = int(np.flatnonzero(cal == pd.Timestamp("2026-08-24"))[0])
    # ① 對帳
    c4 = ["measure_date", "stock_id", "market", "eligible"]
    A = pd.read_csv("backtest/resultsAFC/panel.csv.gz", dtype=str, usecols=c4)
    E = pd.read_csv("backtest/resultsp9_engine/panel_ext.csv.gz", dtype=str, usecols=c4)
    A = A[A["measure_date"] <= "2026-03-02"]; E2 = E[E["measure_date"] <= "2026-03-02"]
    M = A.merge(E2, on=["measure_date", "stock_id"], how="outer", suffixes=("_a", "_e"), indicator=True)
    R["① 對帳"] = {"只在AFC": int((M["_merge"] == "left_only").sum()), "只在ext": int((M["_merge"] == "right_only").sum()),
                  "eligible不同": int((M["eligible_a"] != M["eligible_e"]).sum()), "market不同": int((M["market_a"] != M["market_e"]).sum()),
                  "列數": len(M), "主程式 recon": J["U4 對帳"]["逐列相同（measure_date、stock_id、market、eligible）"]}
    R["① 對帳"]["過"] = R["① 對帳"]["只在AFC"] == 0 and R["① 對帳"]["只在ext"] == 0 and R["① 對帳"]["eligible不同"] == 0 and R["① 對帳"]["market不同"] == 0 and R["① 對帳"]["主程式 recon"]
    # ② 換股日
    reb = []
    for y in range(2017, 2027):
        for m in range(1, 13):
            k = int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(y, m, 10)), side="right"))
            if k < n and t0 <= k <= t1:
                reb.append(k)
    reb = sorted(set(reb))
    got = sorted(set(PK["換股日"]))
    R["② 換股日"] = {"自算": len(reb), "picks": len(got), "過": [str(cal[e].date()) for e in reb] == got}
    # 資料
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    with Pool(procs, initializer=_init, initargs=(cal,)) as pool:
        px = dict(pool.map(_load, list(zip(G["stock_id"], G["market"])), chunksize=16))
    px = {s: v for s, v in px.items() if v is not None}
    off = set(pd.read_csv(os.path.join(H2.H2D, "meta", "delisted.csv"), dtype=str)["stock_id"])
    st = {}
    for s, v in px.items():
        tt = np.flatnonzero(v[2])
        if len(tt) == 0:
            continue
        g = n - 1 - int(tt[-1])
        st[s] = (int(tt[-1]), "delisted_official" if s in off else "delisted_gap" if g >= 60 else "live" if g == 0 else "ambig")
    ind = pd.read_csv(os.path.join(H2.H2D, "meta", "industry.csv"), dtype=str)
    fill = ind["industry_code"].map({"32": "文化創意業", "33": "農業科技", "91": "存託憑證"})
    ind["industry_name"] = ind["industry_name"].where(ind["industry_name"].notna(), fill)
    assert ind["industry_name"].notna().all()
    ind = ind[ind["industry_name"] != "存託憑證"].copy()
    ind["cls"] = ind["industry_name"].replace({"金融業": "金融保險", "金融保險業": "金融保險"})
    R["產業別"] = {"類股數": int(ind["cls"].nunique()), "主程式": J["產業別"]["類股數"], "過": int(ind["cls"].nunique()) == J["產業別"]["類股數"]}
    clsS = ind.set_index("stock_id")["cls"]
    rev, _, _ = R34.load_revenue()
    rf = P4F.rev_hi24_flags(rev, cal)
    print(f"[資料] {len(px):,} 檔｜{time.time() - t00:.0f}s", flush=True)
    # ③ 名單
    ck = J["探索挑格"]["挑中"]; Lc, kc, pkc = J["探索挑格"]["L"], J["探索挑格"]["k"], J["探索挑格"]["挑法"]
    firstday = {}
    for d in cal:
        firstday.setdefault((d.year, d.month), d)

    def ranking(e, L):
        md = firstday[(cal[e].year, cal[e].month)].strftime("%Y-%m-%d")
        el = E[(E["measure_date"] == md) & (E["eligible"] == "True")]["stock_id"]
        df = pd.DataFrame({"sid": [s for s in el if s in px and s in clsS.index]})
        df["cls"] = df["sid"].map(clsS)
        a_ = np.array([px[s][0][e - 1 - L] for s in df["sid"]]); b_ = np.array([px[s][0][e - 1] for s in df["sid"]])
        df["r"] = b_ / a_ - 1.0
        df = df[np.isfinite(a_) & np.isfinite(b_) & (a_ > 0)]
        g = df.groupby("cls")["r"].agg(["mean", "size"])
        g = g[g["size"] >= 5].reset_index().sort_values(["mean", "cls"], ascending=[False, True])
        return df, list(g["cls"])

    def pick(df, order, top, pk, e):
        u = df[df["cls"].isin(top)]
        if pk == "b":
            fl = rf.iloc[e]
            u = u[u["sid"].map(lambda s: s in fl.index and fl[s] == 100)]
        return list(u.sort_values(["r", "sid"], ascending=[False, True])["sid"].head(10))

    bad = []; nchk = 0
    samp = [reb[i] for i in np.linspace(0, len(reb) - 1, 5).astype(int)] + [e for e in reb if cal[e] >= pd.Timestamp("2026-04-01")][:3]
    cache = {}
    for L in (20, 60, 120):
        for k in (1, 3, 5):
            for pk in ("a", "b"):
                key = f"L{L}_k{k}_{pk}"
                es = reb if key == ck else samp
                sub = PK[PK["格"] == key]
                for e in es:
                    if (e, L) not in cache:
                        cache[(e, L)] = ranking(e, L)
                    df, order = cache[(e, L)]
                    mine = pick(df, order, order[:k], pk, e)
                    theirs = list(sub[sub["換股日"] == str(cal[e].date())].sort_values("名次")["sid"])
                    nchk += 1
                    if mine != theirs:
                        bad.append((key, str(cal[e].date()), mine[:3], theirs[:3]))
    R["③ 名單"] = {"比對（格×換股日）": nchk, "不同": len(bad), "例": bad[:5], "過": not bad}
    # ④ 權益
    picks = {}
    for d, g in PK[PK["格"] == ck].groupby("換股日"):
        picks[int(np.flatnonzero(cal == pd.Timestamp(d))[0])] = list(g.sort_values("名次")["sid"])
    for e in reb:
        picks.setdefault(e, [])
    need = {s for v in picks.values() for s in v}
    pxs = {s: px[s] for s in need}
    eq_h = my_sim(picks, pxs, st, t0, t1, False); eq_a = my_sim(picks, pxs, st, t0, t1, True)
    dh = float(np.max(np.abs(eq_h[t0:t1 + 1] - Z[f"{ck}__月換續抱"]))); da = float(np.max(np.abs(eq_a[t0:t1 + 1] - Z[f"{ck}__月換全賣全買"])))
    R["④ 權益"] = {"續抱 最大差": dh, "全賣全買 最大差": da, "過": dh < 1e-9 and da < 1e-9}
    # ⑤ 指標、判定、探索挑格
    segs = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
    sp = {nm: (int(np.flatnonzero(cal == pd.Timestamp(a))[0]), int(np.flatnonzero(cal == pd.Timestamp(b))[0])) for nm, (a, b) in segs.items()}
    b0050 = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    z = {nm: my_stats(b0050, a, b) for nm, (a, b) in sp.items()}
    mine = {nm: my_stats(eq_h, a, b) for nm, (a, b) in sp.items()}
    d5 = max(abs(mine[nm][0] - T[(T["格"] == ck) & (T["版本"] == "月換續抱") & (T["段"] == nm)]["年化"].iloc[0]) for nm in sp)
    d5 = max(d5, max(abs(mine[nm][1] - T[(T["格"] == ck) & (T["版本"] == "月換續抱") & (T["段"] == nm)]["回落"].iloc[0]) for nm in sp))
    dz = max(max(abs(z[nm][0] - J["0050"][nm]["年化"]), abs(z[nm][1] - J["0050"][nm]["回落"])) for nm in sp)
    c, m = mine["確認"]; c0, m0 = z["確認"]
    lab = "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")
    ex = T[(T["版本"] == "月換續抱") & (T["段"] == "探索")].copy()
    ex["ok"] = (ex["年化"] > z["探索"][0]) & (ex["比值"] >= z["探索"][0] / abs(z["探索"][1]))
    cand = ex[ex["ok"]] if ex["ok"].any() else ex
    cand = sorted(cand.itertuples(), key=lambda r: (-r.比值, -r.年化, r.L, r.k, r.挑法))
    R["⑤ 指標與判定"] = {"挑中格兩段 最大差": float(d5), "0050 兩段 最大差": float(dz), "自算判定": lab, "主程式判定": J["確認"]["判定"],
                      "自算挑格": cand[0].格, "主程式挑格": ck, "過判準格數（自算）": int(ex["ok"].sum()),
                      "過": d5 < 1e-12 and dz < 1e-12 and lab == J["確認"]["判定"] and cand[0].格 == ck}
    # ⑥ 對照重跑
    dd = []
    for arm in ("c", "fake"):
        for r in (0, 1, 2):
            rng = np.random.default_rng(20260925 + r); pk_ = {}
            for e in reb:
                df, order = cache.get((e, Lc)) or ranking(e, Lc)
                cache[(e, Lc)] = (df, order)
                if arm == "fake":
                    top = [order[i] for i in rng.choice(len(order), size=kc, replace=False)]
                    pk_[e] = pick(df, order, top, pkc, e)
                else:
                    u = [s for c_ in order[:kc] for s in sorted(df[df["cls"] == c_]["sid"])]
                    mm = min(10, len(u))
                    pk_[e] = [u[i] for i in rng.choice(len(u), size=mm, replace=False)] if mm else []
            q = my_sim(pk_, {s: px[s] for s in {x for v in pk_.values() for x in v}}, st, t0, t1, False)
            row = CT[(CT["arm"] == arm) & (CT["r"] == r)].iloc[0]
            for nm, (a, b) in sp.items():
                dd.append(abs(my_stats(q, a, b)[0] - row[f"{nm}_年化"]))
    R["⑥ 對照重跑"] = {"比對": len(dd), "最大差": float(max(dd)), "過": bool(max(dd) < 1e-12)}
    R["全部過"] = all(v["過"] is True for v in R.values() if isinstance(v, dict))
    json.dump(R, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    print(f"查核完成 {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
