# -*- coding: utf-8 -*-
"""PREREG品質 獨立查核（⛔ 不 import researchQual、researchMomX、research13、research34、p4_features、researchH2）。
只 import backtest.data（讀檔）、backtest.tradability（成交、漲跌停、下市）、backtest.universe_gate（gate3）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchQual_check.py

 ① 由 cells.csv 自算退化排除、挑格、確認／早年標籤、件標籤 ⇒ ＝ summary
 ② 自寫 Q1～Q4（fin_hist TTM、近兩期平均、母公司欄空改總額）、A2 可用日、金融排除、月營收 24 月新高旗標（三種缺值規則、對稱容差）、
    乙族池 ⇒ 兩族挑中格三個世界每個換股日名單 ＝ picks.csv.gz
 ③ 自寫換股簿（停止交易強制出場、下市了結、漲停不買、跌停延後、續抱）⇒ 主窗兩段、早年串接的年化／回落 ＝ cells.csv
 ④ 假訊號 p ⇒ ＝ summary
"""
from __future__ import annotations
import glob, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG

B = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(B, "resultsQual")
SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
FD = os.path.expanduser("~/msdata/a2dadbca4ad165fc31f76edf67be34ee8ee7bc38/data")
WORLDS = {"主": (SNAP, os.path.join(B, "resultsp9_engine/panel_ext.csv.gz"), "2017-03-02", "2026-08-24", False),
          "早年甲": (EARLY, os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz"), "2014-06-01", "2014-12-31", False),
          "早年乙": (SNAP, os.path.join(B, "resultsp9_engine/panel_ext.csv.gz"), "2015-08-01", "2016-12-30", True)}
FREQ = {"月": None, "季": (1, 4, 7, 10), "半年": (1, 7)}
COST, TOL = 0.00585, 1e-9
FIN = {"金融保險業", "金融業", "金融保險"}


def lab(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


def wst(seg):
    c = (seg[-1] / seg[0]) ** (245 / len(seg)) - 1
    pk = np.maximum.accumulate(seg)
    return c, float(((seg - pk) / pk).min())


def fin_table():
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}) for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv")))])
    F = F.drop_duplicates(["stock_id", "period"], keep="last")
    K = {(r["stock_id"], int(r["period"][:4]), int(r["period"][-1])): r for r in F.to_dict("records")}
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    ts = {}
    for s, y, q, u in zip(fd["stock_id"], fd["year"], fd["season"], fd["uploaded_at"]):
        d = pd.to_datetime(str(u)[:10], errors="coerce")
        if not pd.isna(d):
            k = (s, int(y), int(q)); ts[k] = min(ts.get(k, d), d)

    def g(s, y, q, c):
        v = K.get((s, y, q), {}).get(c, np.nan)
        return float(v) if v is not None and v == v else np.nan

    def ttm(s, y, q, c):
        if q == 4:
            return g(s, y, 4, c)
        return g(s, y - 1, 4, c) + g(s, y, q, c) - g(s, y - 1, q, c)
    out = []
    for (s, y, q) in K:
        py, pq = (y, q - 1) if q > 1 else (y - 1, 4)
        a2 = lambda c: (g(s, y, q, c) + g(s, py, pq, c)) / 2
        nip, ni, opi, rev, rd = ttm(s, y, q, "nip_ytd"), ttm(s, y, q, "ni_ytd"), ttm(s, y, q, "opi_ytd"), ttm(s, y, q, "rev_ytd"), ttm(s, y, q, "rd_ytd")
        if np.isfinite(nip) and np.isfinite(a2("equity_parent")):
            q1 = nip / a2("equity_parent") if a2("equity_parent") > 0 else np.nan
        else:
            q1 = ni / a2("equity_total") if (np.isfinite(ni) and np.isfinite(a2("equity_total")) and a2("equity_total") > 0) else np.nan
        A = g(s, y, q, "assets")
        q2 = opi / A if np.isfinite(opi) and np.isfinite(A) and A > 0 else np.nan
        q3 = ni / a2("assets") if np.isfinite(ni) and np.isfinite(a2("assets")) and a2("assets") > 0 else np.nan
        q4 = rd / rev if np.isfinite(rd) and np.isfinite(rev) and rev > 0 else np.nan
        out.append((s, y, q, q1, q2, q3, q4, ts.get((s, y, q))))
    return pd.DataFrame(out, columns=["sid", "y", "q", "Q1", "Q2", "Q3", "Q4", "ts"]).sort_values(["sid", "y", "q"]).reset_index(drop=True)


def main():
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    PKF = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str})
    RES = {}; Z = Sm["0050"]
    # ①
    bad = []
    for fam in ("甲", "乙"):
        ex = T[(T["族"] == fam) & (T["段"] == "探索") & T["判定格"]].copy()
        ex = ex[~((ex["平均持股"] < ex["N"] / 2) | (ex["現金比例"] > 0.30))]
        c0, m0 = Z["探索"]["年化"], Z["探索"]["回落"]
        ps = ex[(ex["年化"] > c0) & (ex["比值"] >= c0 / abs(m0))]
        pp = (ps if len(ps) else ex).copy(); pp["_f"] = pp["頻率"].map({"月": 0, "季": 1, "半年": 2}); pp["_q"] = pp["量測"].map({"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3})
        best = pp.sort_values(["比值", "年化", "_f", "N", "_q"], ascending=[False, False, True, True, True]).iloc[0]
        cf = T[(T["格"] == best["格"]) & (T["段"] == "確認")].iloc[0]; ea = T[(T["格"] == best["格"]) & (T["段"] == "早年")].iloc[0]
        l1 = lab(cf["年化"], cf["回落"], Z["確認"]["年化"], Z["確認"]["回落"]); l2 = lab(ea["年化"], ea["回落"], Z["早年"]["年化"], Z["早年"]["回落"])
        pk = Sm["挑格"][fam]
        if best["格"] != pk["格"] or l1 != pk["確認"]["標籤"] or l2 != pk["早年"]["標籤"]:
            bad.append(fam)
    RES["① 挑格與標籤"] = {"不符": bad, "過": not bad}
    print(RES, flush=True)
    Q = fin_table()
    nsel = nbad = 0; EQ = {}; det = {}
    for wn, (data, panp, W0, W1, twse) in WORLDS.items():
        D.DATA = data; cal = D.load_calendar(); n = len(cal)
        pan = pd.read_csv(panp, dtype={"stock_id": str}, parse_dates=["measure_date"])
        pan["el"] = pan["eligible"].astype(str).isin(["True", "1"])
        st_ = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
        U = UG.gate3(st_); U = U[U["stock_id"].isin(set(pan["stock_id"]))]
        mk = st_.set_index("stock_id")["market"]
        ind = pd.read_csv(os.path.join(data, "meta", "industry.csv"), dtype=str)
        fin = set(ind.loc[ind["industry_name"].isin(FIN), "stock_id"])
        P = {}
        for sid, m_ in zip(U["stock_id"], U["market"]):
            s = D.load_stock(sid, m_, cal)
            if s is None:
                continue
            raw = s.df["close"].to_numpy(float); tb = TR.one(sid, cal)
            P[sid] = {"c": pd.Series(raw).ffill().to_numpy(float), "o": s.df["open"].to_numpy(float), "v": np.isfinite(raw),
                      "trd": np.asarray(tb["trd"], bool), "up": np.asarray(tb["up_o"], bool), "dn": np.asarray(tb["dn_o"], bool)}
        dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=TR.load_official())
        w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1), side="right") - 1)
        SF = {s: int(np.flatnonzero(v["v"])[-1]) for s, v in P.items() if v["v"].any() and np.flatnonzero(v["v"])[-1] < w1}
        reb = {}
        for d, g in pan.groupby("measure_date"):
            mp = int(cal.searchsorted(d))
            if mp >= n - 1 or cal[mp] != d or mp + 1 > w1 or mp + 1 < w0:
                continue
            reb[mp + 1] = sorted(s for s in g.loc[g["el"], "stock_id"] if s in P and (not twse or mk.get(s) == "twse"))
        rebs = sorted(reb); w0 = rebs[0]
        # 可用日
        dlm = {1: (5, 15), 2: (8, 14), 3: (11, 14)}
        av = np.array([int(cal.searchsorted(pd.Timestamp(t), side="right")) if (t is not None and not pd.isna(t)) else
                       int(cal.searchsorted(pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, *dlm[q]), side="right")) + 5
                       for y, q, t in zip(Q["y"], Q["q"], Q["ts"])])
        # 營收旗標
        fs = (sorted(glob.glob(os.path.join(EARLY, "mops", "revenue_hist", "*.csv"))) if wn == "早年乙" else []) + sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv")))
        rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
        rv["v"] = pd.to_numeric(rv["當月營收"], errors="coerce")
        RV = rv.pivot(index="period", columns="stock_id", values="v").sort_index()
        per = list(RV.index); Vv = RV.to_numpy(float)
        ent = {}
        for p in per:
            y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            e = int(cal.searchsorted(pd.Timestamp(y2, m2, 10), side="right"))
            if 0 < e < n:
                ent[p] = e
        flag = {}
        for j, sid in enumerate(RV.columns):
            rep = np.flatnonzero(~np.isnan(Vv[:, j])); fk = int(rep[0]) if len(rep) else None
            col = {}
            for k in range(len(per)):
                if np.isnan(Vv[k, j]):
                    continue
                if fk is not None and fk > 0 and k - fk < 24:
                    col[k] = 0.0; continue
                h = Vv[max(k - 24, 0):k, j]; h = h[~np.isnan(h)]
                if len(h) < 18 or k < 24:
                    continue
                mx = h.max(); col[k] = 100.0 if Vv[k, j] >= mx - abs(mx) * 1e-4 else 0.0
            flag[sid] = col

        placed = sorted((ent[p], k) for k, p in enumerate(per) if p in ent)
        pe = [x for x, _ in placed]

        def rflag(sid, e):
            """日曆 ffill 同義：e 以前（含）最後一個已生效、且該檔旗標有值的期（NaN 期不覆蓋）。"""
            import bisect
            i = bisect.bisect_right(pe, e) - 1
            f = flag.get(sid)
            if f is None:
                return None
            while i >= 0:
                k = placed[i][1]
                if k in f:
                    return f[k]
                i -= 1
            return None
        for fam in ("甲", "乙"):
            pk = Sm["挑格"][fam]; k, fq, N = pk["量測"], pk["頻率"], pk["N"]
            sel = {}
            for e in rebs:
                if FREQ[fq] is not None and cal[e].month not in FREQ[fq]:
                    continue
                sub = Q[av <= e].groupby("sid").tail(1)
                qv = {s: v for s, v in zip(sub["sid"], sub[k]) if np.isfinite(v)}
                el = [s for s in reb[e] if s not in fin]
                cand = {s: qv[s] for s in el if s in qv}
                if fam == "乙":
                    cand = {s: v for s, v in cand.items() if rflag(s, e) == 100.0}
                sel[e] = [s for s, _ in sorted(cand.items(), key=lambda t: (-t[1], t[0]))[:N]]
            ref = PKF[(PKF["族"] == fam) & (PKF["世界"] == wn)]
            rs = {d: list(g.sort_values("名次")["sid"]) for d, g in ref.groupby("換股日")}
            for e, s_ in sel.items():
                nsel += 1; nbad += int(s_ != rs.get(str(cal[e].date()), []))
            eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
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
            EQ[(fam, wn)] = (eq, w0, w1, cal)
        print(wn, "done", flush=True)
    RES["② 兩族挑中格三世界名單"] = {"比對換股日數": nsel, "不同": nbad, "過": nbad == 0}
    mx = 0.0
    for fam in ("甲", "乙"):
        eq, w0, w1, cal = EQ[(fam, "主")]
        for sn, (a0, b0) in (("探索", ("2017-03-02", "2021-12-30")), ("確認", ("2022-01-03", "2026-08-24"))):
            a_ = max(int(cal.searchsorted(pd.Timestamp(a0))), w0); b_ = min(int(cal.searchsorted(pd.Timestamp(b0), side="right") - 1), w1)
            c, m = wst(eq[a_:b_ + 1]); ref = T[(T["格"] == Sm["挑格"][fam]["格"]) & (T["段"] == sn)].iloc[0]
            d = max(abs(c - ref["年化"]), abs(m - ref["回落"])); mx = max(mx, d); det[f"{fam}_{sn}"] = d
        (ea, a0, a1, _), (eb, b0_, b1, _) = EQ[(fam, "早年甲")], EQ[(fam, "早年乙")]
        sa = ea[a0:a1 + 1] / ea[a0]; sb = eb[b0_:b1 + 1] / eb[b0_] * sa[-1]
        c, m = wst(np.r_[sa, sb]); ref = T[(T["格"] == Sm["挑格"][fam]["格"]) & (T["段"] == "早年")].iloc[0]
        d = max(abs(c - ref["年化"]), abs(m - ref["回落"])); mx = max(mx, d); det[f"{fam}_早年"] = d
    RES["③ 自寫換股簿：主窗兩段、早年串接"] = {"最大差": mx, "逐項": det, "過": mx <= TOL}
    FK = pd.read_csv(os.path.join(OUT, "fake.csv.gz"), float_precision="round_trip"); b4 = []
    for fam in ("甲", "乙"):
        for nm in ("確認", "早年"):
            x = FK[FK["族"] == fam][f"{nm}_年化"].to_numpy(float)
            if abs(float(np.mean(x >= Sm["挑格"][fam][nm]["年化"])) - Sm["挑格"][fam][f"假訊號_{nm}"]["p（隨機年化 ≥ 本格）"]) > 1e-12:
                b4.append((fam, nm))
    RES["④ 假訊號 p"] = {"不符": b4, "過": not b4}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
