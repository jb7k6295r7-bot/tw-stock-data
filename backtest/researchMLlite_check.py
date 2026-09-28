# -*- coding: utf-8 -*-
"""機器學習 簡化版試跑 獨立查核（⛔ 不 import researchMLlite、researchMomX、researchQual、research13、p4_features、researchH2）。
只 import backtest.data（讀檔）、backtest.tradability（成交、漲跌停、下市）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchMLlite_check.py

 ① 特徵抽 40 列自原始檔重算：r1、r12、r6s、距 250 日高、60 日波動、周轉率、規模、營收年增、距 24 月高
 ② 模型：由 dataset.csv.gz 自寫嶺迴歸（增廣最小平方 lstsq）、驗證 α、樹樁提升（自寫逐門檻掃描）⇒ 全部預測 ＝ predictions.csv.gz
 ③ 名單：由 predictions 自排 8 格前 N ＝ picks.csv.gz
 ④ 權益：自寫換股簿（停止交易強制出場、下市了結、續抱）⇒ 描述挑中格兩段年化／回落 ＝ cells.csv
 ⑤ 假訊號 p ＝ summary
"""
from __future__ import annotations
import glob, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
D.DATA = SNAP
OUT = os.path.expanduser("~/tw-p17/backtest/resultsMLlite")
EARLY_REV = os.path.expanduser("~/earlydata/3edc0e2206/main/data/mops/revenue_hist")
COST = 0.00585


def wst(seg):
    c = (seg[-1] / seg[0]) ** (245 / len(seg)) - 1
    pk = np.maximum.accumulate(seg)
    return c, float(((seg - pk) / pk).min())


def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(pd.Series(a[ok]).rank().corr(pd.Series(b[ok]).rank())) if ok.sum() >= 10 else np.nan


def main():
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    DS = pd.read_csv(os.path.join(OUT, "dataset.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    PR = pd.read_csv(os.path.join(OUT, "predictions.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    T = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    cal = D.load_calendar(); n = len(cal)
    RES = {}
    # ①
    st = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
    fs = sorted(glob.glob(os.path.join(EARLY_REV, "*.csv"))) + sorted(glob.glob(os.path.join(SNAP, "mops", "revenue_hist", "*.csv")))
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
    rv["v"] = pd.to_numeric(rv["當月營收"], errors="coerce"); RV = rv.pivot(index="period", columns="stock_id", values="v").sort_index(); per = list(RV.index)
    ent = {}
    for p in per:
        y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        e = int(cal.searchsorted(pd.Timestamp(y2, m2, 10), side="right"))
        if 0 < e < n:
            ent[p] = e
    rng = np.random.default_rng(20260928)
    sm = DS[DS["freq"] == "月"].iloc[np.sort(rng.choice((DS["freq"] == "月").sum(), 40, replace=False))]
    mx1 = 0.0; det = {}
    for r in sm.itertuples():
        s = D.load_stock(r.sid, st.get(r.sid, "twse"), cal); df = s.df; m = int(r.e) - 1
        c = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy(); vol = df["volume"].to_numpy(float)
        raw = pd.read_csv(os.path.join(SNAP, "stocks", r.sid + ".csv"), dtype={"date": str}).drop_duplicates("date"); raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
        shr = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float); rc = pd.to_numeric(raw["close"], errors="coerce").ffill().to_numpy(float)
        fb = int(np.flatnonzero(np.isfinite(df["close"].to_numpy(float)))[0])
        mine = {"r1": c[m] / c[m - 21] - 1 if m - 21 >= fb else np.nan, "r12": c[m] / c[m - 252] - 1 if m - 252 >= fb else np.nan,
                "r6s": c[m - 21] / c[m - 147] - 1 if m - 147 >= fb else np.nan, "dist250": c[m] / c[m - 249:m + 1].max() - 1 if m - 249 >= fb else np.nan,
                "turn20": np.nanmean(vol[m - 19:m + 1]) / shr[m] if shr[m] > 0 else np.nan, "logcap": math.log(rc[m] * shr[m]) if rc[m] > 0 and shr[m] > 0 else np.nan}
        d = np.r_[np.nan, c[1:] / c[:-1] - 1][m - 59:m + 1]
        mine["vol60"] = float(np.std(d[np.isfinite(d)], ddof=1)) if m - 60 >= fb else np.nan
        col = RV[r.sid].to_numpy(float) if r.sid in RV.columns else None
        av = [i for i, p in enumerate(per) if p in ent and ent[p] <= int(r.e)]
        if col is not None and av:
            k = av[-1]
            while k >= 0 and not np.isfinite(col[k]):
                k -= 1
            mine["yoy"] = col[k] / col[k - 12] - 1 if k >= 12 and col[k - 12] > 0 else np.nan
            h = col[max(k - 24, 0):k]; h = h[np.isfinite(h)]
            mine["dist24"] = col[k] / h.max() - 1 if k >= 24 and len(h) >= 18 else np.nan
        for kf, v in mine.items():
            w = getattr(r, kf)
            if not (np.isnan(v) and np.isnan(w)):
                dd = abs(v - w); mx1 = max(mx1, dd if np.isfinite(dd) else 9.0); det[kf] = max(det.get(kf, 0.0), dd if np.isfinite(dd) else 9.0)
    RES["① 特徵 40 列自原始檔重算"] = {"最大差": mx1, "逐項": det, "過": mx1 <= 1e-9}
    print(RES, flush=True)
    # ②
    cols = [c for c in DS.columns if c.startswith("x_")]
    flag = np.array([c.startswith("x_miss_") for c in cols])
    mxr = mxs = 0.0; alpha_ok = True
    for fq in ("月", "季"):
        d = DS[DS["freq"] == fq]; yf = d.groupby("year")["e"].min().to_dict()

        def ridge(tr, te, a):
            X = tr[cols].to_numpy(float); y = tr["y"].to_numpy(float)
            mu = X.mean(0); sd = X.std(0); z0 = sd == 0; sd[z0] = 1.0
            Z = (X - mu) / sd; Z[:, z0] = 0.0
            A = np.vstack([Z, math.sqrt(a) * np.eye(Z.shape[1])]); bb = np.r_[y - y.mean(), np.zeros(Z.shape[1])]
            b = np.linalg.lstsq(A, bb, rcond=None)[0]
            Zt = (te[cols].to_numpy(float) - mu) / sd; Zt[:, z0] = 0.0
            return Zt @ b + y.mean()
        tr = d[(d["tend"] < yf[2018]) & d["y"].notna()]; va = d[d["year"] == 2018]
        ic = {}
        for a in (0.1, 1.0, 10.0):
            pv = ridge(tr, va, a)
            ic[a] = float(np.nanmean([sp(pv[(va["e"] == e).to_numpy()], va.loc[va["e"] == e, "ret"].to_numpy(float)) for e in sorted(va["e"].unique())]))
        al = sorted(ic, key=lambda a: (-ic[a], a))[0]
        alpha_ok &= al == Sm["模型"][fq]["α"]
        for y in sorted(k for k in yf if k >= 2019):
            tr = d[(d["tend"] < yf[y]) & d["y"].notna()]; te = d[d["year"] == y]
            ref = PR[(PR["freq"] == fq) & PR["e"].isin(te["e"].unique())]
            mxr = max(mxr, float(np.max(np.abs(ridge(tr, te, al) - ref["RIDGE"].to_numpy(float)))))
            X = tr[cols].to_numpy(float); yy = tr["y"].to_numpy(float); Xe = te[cols].to_numpy(float)

            def binz(M):
                return np.where(flag[None, :], (M >= 0.5).astype(int), np.clip(np.floor(M * 20), 0, 19).astype(int))
            Bt, Be = binz(X), binz(Xe)
            f = np.full(len(yy), yy.mean()); fe = np.full(len(Xe), yy.mean())
            nn = len(yy)
            for _ in range(100):
                r = yy - f; S = float(np.sum(r)); best = None
                for j in range(len(cols)):
                    nb = 2 if flag[j] else 20
                    sb = np.zeros(nb); cb = np.zeros(nb, int)
                    np.add.at(sb, Bt[:, j], r); np.add.at(cb, Bt[:, j], 1)
                    for t in range(nb - 1):
                        nl = int(cb[:t + 1].sum())
                        if nl == 0 or nl == nn:
                            continue
                        sl = float(sb[:t + 1].sum()); g = sl * sl / nl + (S - sl) ** 2 / (nn - nl) - S * S / nn
                        if best is None or g > best[0] + 1e-15:
                            best = (g, j, t, sl / nl, (S - sl) / (nn - nl))
                if best is None:
                    break
                _, j, t, vl, vr = best
                f = f + 0.1 * np.where(Bt[:, j] <= t, vl, vr); fe = fe + 0.1 * np.where(Be[:, j] <= t, vl, vr)
            mxs = max(mxs, float(np.max(np.abs(fe - ref["STUMP"].to_numpy(float)))))
        print(fq, "models done", mxr, mxs, flush=True)
    RES["② 自寫嶺迴歸（lstsq）、α、樹樁 ⇒ 預測"] = {"嶺迴歸最大差": mxr, "樹樁最大差": mxs, "α 相同": bool(alpha_ok), "過": mxr <= 1e-9 and mxs <= 1e-9 and alpha_ok}
    print(RES, flush=True)
    # ③
    PK = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str}); nb3 = 0; n3 = 0
    x0 = int(cal.searchsorted(pd.Timestamp("2019-01-01")))
    for key, g in PK.groupby("格"):
        mdl, fq, N = key.split("_"); N = int(N[1:])
        pr = PR[(PR["freq"] == fq) & (PR["e"] >= x0)]
        ref = {d_: list(gg.sort_values("名次")["sid"]) for d_, gg in g.groupby("換股日")}
        for e, gg in pr.groupby("e"):
            mine = [s for s, _ in sorted(zip(gg["sid"], gg[mdl]), key=lambda t: (-t[1], t[0]))[:N]]
            n3 += 1; nb3 += int(mine != ref.get(str(cal[int(e)].date()), []))
    RES["③ 8 格名單"] = {"比對": n3, "不同": nb3, "過": nb3 == 0}
    # ④
    pk = Sm["描述挑格（⛔ 不判）"]["格"]; mdl, fq, Ns = pk.split("_"); N = int(Ns[1:])
    g = PK[PK["格"] == pk]; sel = {int(cal.searchsorted(pd.Timestamp(d_))): list(gg.sort_values("名次")["sid"]) for d_, gg in g.groupby("換股日")}
    sids = sorted({s for v in sel.values() for s in v})
    P = {}
    for s in sids:
        x = D.load_stock(s, st.get(s, "twse"), cal); raw = x.df["close"].to_numpy(float); tb = TR.one(s, cal)
        P[s] = {"c": pd.Series(raw).ffill().to_numpy(), "o": x.df["open"].to_numpy(float), "v": np.isfinite(raw), "trd": np.asarray(tb["trd"], bool),
                "up": np.asarray(tb["up_o"], bool), "dn": np.asarray(tb["dn_o"], bool)}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=TR.load_official())
    w1 = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    SF = {s: int(np.flatnonzero(v["v"])[-1]) for s, v in P.items() if np.flatnonzero(v["v"])[-1] < w1}
    w0 = min(sel); eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    for t in range(w0, w1 + 1):
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
            for s in [s for s in sel[t] if s not in pos][:max(N - len(pos), 0)]:
                x = P[s]; o = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or (s in SF and t > SF[s]) or x["up"][t]:
                    continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[s] = [amt / o, amt]
        eq[t] = cash + sum(u * P[s]["c"][t] for s, (u, _) in pos.items())
    mx4 = 0.0
    for nm, (a0, b0) in (("探索", ("2019-01-01", "2021-12-30")), ("確認", ("2022-01-03", "2026-08-24"))):
        a_ = int(cal.searchsorted(pd.Timestamp(a0))); b_ = int(cal.searchsorted(pd.Timestamp(b0), side="right") - 1)
        c, m = wst(eq[a_:b_ + 1]); ref = T[(T["格"] == pk) & (T["段"] == nm)].iloc[0]
        mx4 = max(mx4, abs(c - ref["年化"]), abs(m - ref["回落"]))
    RES["④ 自寫換股簿（描述挑中格）"] = {"最大差": mx4, "過": mx4 <= 1e-9}
    FK = pd.read_csv(os.path.join(OUT, "fake.csv.gz"), float_precision="round_trip"); b5 = []
    for nm in ("探索", "確認"):
        real = T[(T["格"] == pk) & (T["段"] == nm)]["年化"].iloc[0]
        if abs(float(np.mean(FK[f"{nm}_年化"] >= real)) - Sm["假訊號（同池隨機，挑中格）"][nm]["p（隨機年化 ≥ 本格）"]) > 1e-12:
            b5.append(nm)
    RES["⑤ 假訊號 p"] = {"不符": b5, "過": not b5}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
