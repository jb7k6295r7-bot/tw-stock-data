# -*- coding: utf-8 -*-
"""PREREG機器學習改目標 獨立查核（⛔ 不 import researchMLx、researchMLlite、researchMomX、research13）。
只 import backtest.data（讀檔）、backtest.tradability（成交、漲跌停、下市）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchMLx_check.py

 ① 目標：自 dataset.csv.gz 重算 yA（ret − bret 截尾 1%／99%）、yB（前 20%）、yC（排名）；bret 抽 30 期自 0050 原檔重算
 ② 模型：挑中格的（目標, 頻率）＋（B, 季）自寫嶺迴歸（增廣 lstsq）與樹樁（每葉 ≥ 200、10 等分、平方／對數損失）⇒ 驗證選參 ＝ summary、預測 ＝ predictions.csv.gz
 ③ 名單：挑中格＋全部目 C 格自排 ＝ picks.csv.gz
 ④ 權益：自寫換股簿 ⇒ 挑中格兩段年化／回落 ＝ cells.csv
 ⑤ 挑格、退化、標籤自 cells.csv 重算；假訊號 p；vol60 百分位（挑中格、簡化版 RIDGE_月_N20）
"""
from __future__ import annotations
import json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
D.DATA = SNAP
OUT = "backtest/resultsMLx"
COST = 0.00585
SEG = {"探索": ("2019-01-01", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}


def wst(seg):
    c = (seg[-1] / seg[0]) ** (245 / len(seg)) - 1
    pk = np.maximum.accumulate(seg)
    return c, float(((seg - pk) / pk).min())


def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(pd.Series(a[ok]).rank().corr(pd.Series(b[ok]).rank())) if ok.sum() >= 10 else np.nan


def ridge(X, y, a, Xt):
    mu = X.mean(0); sd = X.std(0); z0 = sd == 0; sd[z0] = 1.0
    Z = (X - mu) / sd; Z[:, z0] = 0.0
    b = np.linalg.lstsq(np.vstack([Z, math.sqrt(a) * np.eye(Z.shape[1])]), np.r_[y - y.mean(), np.zeros(Z.shape[1])], rcond=None)[0]
    Zt = (Xt - mu) / sd; Zt[:, z0] = 0.0
    return Zt @ b + y.mean()


def stumps(X, y, flag, logloss, rounds, Xts):
    """回：{k: [每個 Xt 的預測]}，k ∈ rounds（同一條路徑截斷）。"""
    def bz(M):
        return np.where(flag[None, :], (M >= 0.5).astype(int), np.clip(np.floor(M * 10), 0, 9).astype(int))
    B = bz(X); Bts = [bz(x) for x in Xts]; n = len(y)
    if logloss:
        p0 = min(max(y.mean(), 1e-9), 1 - 1e-9); f0 = math.log(p0 / (1 - p0))
    else:
        f0 = y.mean()
    F = np.full(n, f0); Ft = [np.full(len(x), f0) for x in Xts]; out = {}
    for it in range(1, max(rounds) + 1):
        if logloss:
            pr = 1 / (1 + np.exp(-F)); r = y - pr; h = pr * (1 - pr)
        else:
            r = y - F
        S = float(r.sum()); best = None
        for j in range(B.shape[1]):
            nb = 2 if flag[j] else 10
            sb = np.zeros(nb); cb = np.zeros(nb, int); np.add.at(sb, B[:, j], r); np.add.at(cb, B[:, j], 1)
            for t in range(nb - 1):
                nl = int(cb[:t + 1].sum())
                if nl < 200 or n - nl < 200:
                    continue
                sl = float(sb[:t + 1].sum()); g = sl * sl / nl + (S - sl) ** 2 / (n - nl) - S * S / n
                if best is None or g > best[0] + 1e-15:
                    best = (g, j, t)
        if best is None:
            break
        _, j, t = best; L = B[:, j] <= t
        if logloss:
            vl = r[L].sum() / max(h[L].sum(), 1e-12); vr = r[~L].sum() / max(h[~L].sum(), 1e-12)
        else:
            vl = r[L].mean(); vr = r[~L].mean()
        F = F + 0.1 * np.where(L, vl, vr)
        Ft = [f + 0.1 * np.where(bt[:, j] <= t, vl, vr) for f, bt in zip(Ft, Bts)]
        if it in rounds:
            out[it] = [f.copy() for f in Ft]
    for k in rounds:
        out.setdefault(k, [f.copy() for f in Ft])
    return out


def main():
    RES = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    DS = pd.read_csv(os.path.join(OUT, "dataset.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    PR = pd.read_csv(os.path.join(OUT, "predictions.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    T = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    cal = D.load_calendar(); n = len(cal)
    # ①
    mx = 0.0; badB = 0
    for (fq, e), g in DS.groupby(["freq", "e"]):
        r = g["ret"].to_numpy(float); ok = np.isfinite(r); ex = r - g["bret"].to_numpy(float)
        if ok.sum() >= 2:
            lo, hi = np.percentile(ex[ok], [1, 99]); ya = np.clip(ex[ok], lo, hi)
            mx = max(mx, float(np.max(np.abs(ya - g["yA"].to_numpy(float)[ok]))))
            rk = pd.Series(r[ok]).rank().to_numpy() / ok.sum()
            badB += int(np.sum((rk > 0.8).astype(float) != g["yB"].to_numpy(float)[ok]))
            rc = (pd.Series(r[ok]).rank().to_numpy() - 1) / (ok.sum() - 1)
            mx = max(mx, float(np.max(np.abs(rc - g["yC"].to_numpy(float)[ok]))))
    b = D.load_stock("0050", "twse", cal).df; bc = pd.Series(b["close"].to_numpy(float)).ffill().to_numpy(); bo = b["open"].to_numpy(float)
    mb = 0.0
    for fq in ("月", "季", "半年"):
        es = sorted(DS.loc[DS["freq"] == fq, "e"].unique())
        for i in range(0, len(es) - 1, max(1, len(es) // 10)):
            e, nx = int(es[i]), int(es[i + 1]); v = DS[(DS["freq"] == fq) & (DS["e"] == e)]["bret"].iloc[0]
            mb = max(mb, abs(bc[nx - 1] / bo[e] - 1 - v))
    RES["① 目標 A／B／C 與 0050 同期報酬"] = {"A、C 最大差": mx, "B 不符": badB, "bret 最大差": mb, "過": mx < 1e-15 and badB == 0 and mb < 1e-15}
    print(RES, flush=True)
    # ②
    pk = S["挑格"]["格"]; ptg, pmdl, pfq, pN = pk.split("_"); pN = int(pN[1:])
    cols = [c for c in DS.columns if c.startswith("x_")]; flag = np.array([c.startswith("x_miss_") for c in cols])
    jobs = [(ptg, pfq)] + ([("B", "季")] if (ptg, pfq) != ("B", "季") else [])
    m2 = 0.0; bad2 = []
    for tg, fq in jobs:
        d = DS[DS["freq"] == fq]; yf = d.groupby("year")["e"].min().to_dict(); yc = f"y{tg}"
        info = S["模型"][f"{tg}_{fq}"]
        tr = d[(d["tend"] < yf[2018]) & d[yc].notna()]; va = d[d["year"] == 2018]
        X, y, Xv = tr[cols].to_numpy(float), tr[yc].to_numpy(float), va[cols].to_numpy(float)

        def ic(pv):
            return float(np.nanmean([sp(pv[(va["e"] == e).to_numpy()], va.loc[va["e"] == e, "ret"].to_numpy(float)) for e in sorted(va["e"].unique())]))
        icr = {a: ic(ridge(X, y, a, Xv)) for a in (1.0, 10.0, 100.0)}
        sg = stumps(X, y, flag, tg == "B", (50, 100, 200), [Xv]); icg = {k: ic(sg[k][0]) for k in (50, 100, 200)}
        al = sorted(icr, key=lambda a: (-icr[a], a))[0]; kr = sorted(icg, key=lambda k: (-icg[k], k))[0]
        if al != info["α"] or kr != info["輪數"]:
            bad2.append((tg, fq, "選參", al, kr))
        for yy in sorted(k for k in yf if k >= 2019):
            tr = d[(d["tend"] < yf[yy]) & d[yc].notna()]; te = d[d["year"] == yy]
            X, y, Xt = tr[cols].to_numpy(float), tr[yc].to_numpy(float), te[cols].to_numpy(float)
            ref = PR[(PR["target"] == tg) & (PR["freq"] == fq) & PR["e"].isin(te["e"].unique())]
            m2 = max(m2, float(np.max(np.abs(ridge(X, y, al, Xt) - ref["LIN"].to_numpy(float)))))
            g_ = stumps(X, y, flag, tg == "B", (kr,), [Xt])[kr][0]
            m2 = max(m2, float(np.max(np.abs(g_ - ref["GB"].to_numpy(float)))))
        print(tg, fq, "done", m2, bad2, flush=True)
    RES["② 自寫嶺迴歸、樹樁（選參＋預測）"] = {"組": jobs, "最大差": m2, "不符": bad2, "過": m2 < 1e-9 and not bad2}
    print(RES, flush=True)
    # ③
    PK = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str})
    x0 = int(cal.searchsorted(pd.Timestamp("2019-01-01")))
    chk = [pk] + [k for k in PK["格"].unique() if k.startswith("C_")]
    n3 = b3 = 0
    for key in sorted(set(chk)):
        tg, mdl, fq, N = key.split("_"); N = int(N[1:])
        ref = {d_: list(g.sort_values("名次")["sid"]) for d_, g in PK[PK["格"] == key].groupby("換股日")}
        for e, g in PR[(PR["target"] == tg) & (PR["freq"] == fq) & (PR["e"] >= x0)].groupby("e"):
            if tg != "C":
                mine = [s for s, _ in sorted(zip(g["sid"], g[mdl]), key=lambda t: (-t[1], t[0]))[:N]]
            else:
                ok = g[np.isfinite(g["vol60"])].sort_values(["vol60", "sid"]); m = len(ok); mine = []
                q = (np.arange(m) * 5) // m
                for qq in range(5):
                    sub = ok[q == qq]
                    mine += [s for s, _ in sorted(zip(sub["sid"], sub[mdl]), key=lambda t: (-t[1], t[0]))[:N // 5]]
            n3 += 1; b3 += int(mine != ref.get(str(cal[int(e)].date()), []))
    RES["③ 名單（挑中格＋全部目 C 格）"] = {"比對": n3, "不同": b3, "過": b3 == 0}
    # ④
    g = PK[PK["格"] == pk]; sel = {int(cal.searchsorted(pd.Timestamp(d_))): list(gg.sort_values("名次")["sid"]) for d_, gg in g.groupby("換股日")}
    st = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
    sids = sorted({s for v in sel.values() for s in v}); P = {}
    for s in sids:
        x = D.load_stock(s, st.get(s, "twse"), cal); raw = x.df["close"].to_numpy(float); tb = TR.one(s, cal)
        P[s] = {"c": pd.Series(raw).ffill().to_numpy(), "o": x.df["open"].to_numpy(float), "v": np.isfinite(raw), "trd": np.asarray(tb["trd"], bool),
                "up": np.asarray(tb["up_o"], bool), "dn": np.asarray(tb["dn_o"], bool)}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=TR.load_official())
    w1 = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    SF = {s: int(np.flatnonzero(v["v"])[-1]) for s, v in P.items() if np.flatnonzero(v["v"])[-1] < w1}
    eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    for t in range(min(sel), w1 + 1):
        if t in sel:
            pend = (pend | (set(pos) - set(sel[t]))) - set(sel[t])
        for s in sorted(pend | {s for s in pos if s in SF and t > SF[s]}):
            if s not in pos:
                pend.discard(s); continue
            x = P[s]
            if s in SF and t > SF[s]:
                px = x["c"][t]
            elif x["trd"][t] and not x["dn"][t] and np.isfinite(x["o"][t]) and x["o"][t] > 0:
                px = x["o"][t]
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]
            else:
                continue
            u, amt = pos.pop(s); cash += u * px - amt * COST; pend.discard(s)
        if t in sel:
            for s in [s for s in sel[t] if s not in pos][:max(pN - len(pos), 0)]:
                x = P[s]; o = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or (s in SF and t > SF[s]) or x["up"][t]:
                    continue
                amt = min(eq[t - 1] / pN, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[s] = [amt / o, amt]
        eq[t] = cash + sum(u * P[s]["c"][t] for s, (u, _) in pos.items())
    m4 = 0.0
    for nm, (a0, b0) in SEG.items():
        a_ = int(cal.searchsorted(pd.Timestamp(a0))); b_ = int(cal.searchsorted(pd.Timestamp(b0), side="right") - 1)
        c, m = wst(eq[a_:b_ + 1]); ref = T[(T["格"] == pk) & (T["段"] == nm)].iloc[0]
        m4 = max(m4, abs(c - ref["年化"]), abs(m - ref["回落"]))
    RES["④ 自寫換股簿（挑中格）"] = {"最大差": m4, "過": m4 <= 1e-9}
    # ⑤
    Z = S["0050"]; ex = T[T["段"] == "探索"].copy()
    ex = ex[~((ex["平均持股"] < ex["N"] / 2) | (ex["現金比例"] > 0.30))]
    c0, m0 = Z["探索"]["年化"], Z["探索"]["回落"]
    ps = ex[(ex["年化"] > c0) & (ex["年化"] / ex["回落"].abs() >= c0 / abs(m0))]
    best = (ps if len(ps) else ex).sort_values(["比值", "年化"], ascending=[False, False]).iloc[0]["格"]
    bad5 = []
    for r in T.to_dict("records"):
        c0, m0 = Z[r["段"]]["年化"], Z[r["段"]]["回落"]
        lab = "合格" if (r["年化"] > c0 and r["年化"] / abs(r["回落"]) >= c0 / abs(m0)) else ("另列" if r["年化"] > c0 else "不合格")
        if lab != r["標籤"]:
            bad5.append((r["格"], r["段"]))
    FK = pd.read_csv(os.path.join(OUT, "fake.csv.gz"), float_precision="round_trip")
    for nm in SEG:
        real = T[(T["格"] == pk) & (T["段"] == nm)]["年化"].iloc[0]
        if abs(float(np.mean(FK[f"{nm}_年化"] >= real)) - S["假訊號（同池隨機，挑中格頻率與 N）"][nm]["p（隨機年化 ≥ 本格）"]) > 1e-12:
            bad5.append(("假訊號", nm))
    pv = {int(e): gg.set_index("sid")["vol60"] for e, gg in DS[DS["freq"] == "月"].groupby("e")}

    def vp(sl):
        v = []
        for e, names in sl.items():
            s_ = pv.get(e)
            if s_ is None:
                continue
            ok = s_.dropna(); r = ok.rank() / len(ok)
            v += [float(r[x]) for x in names if x in r.index]
        return float(np.mean(v))
    L = pd.read_csv("backtest/resultsMLlite/picks.csv.gz", dtype={"sid": str}); L = L[L["格"] == "RIDGE_月_N20"]
    sl = {int(cal.searchsorted(pd.Timestamp(d_))): list(gg["sid"]) for d_, gg in L.groupby("換股日")}
    V = S["持股 vol60 百分位（全窗平均；0.5 ＝ 當期中位）"]
    dv = max(abs(vp(sel) - V["挑中格"]), abs(vp(sl) - V["簡化版挑中格 RIDGE_月_N20"]))
    RES["⑤ 挑格、標籤、假訊號 p、vol60 百分位"] = {"自挑": best, "不符": bad5, "vol60 百分位差": dv, "過": best == pk and not bad5 and dv < 1e-12}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
