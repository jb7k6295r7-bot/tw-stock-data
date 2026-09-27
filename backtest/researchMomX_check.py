# -*- coding: utf-8 -*-
"""PREREG動能改良 獨立查核（⛔ 不 import researchMomX、researchSector、research13、researchH2）。
只 import backtest.data（讀檔）、backtest.tradability（成交、漲跌停、下市狀態）、backtest.universe_gate（gate3）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchMomX_check.py

 ① 挑格：由 cells.csv 自算探索段退化排除、過判準、比值最高（平手規則）⇒ 4 件挑中格 ＝ summary；確認／早年標籤、件標籤（兩段較嚴）⇒ ＝ summary
 ② 名單：主、早年兩個世界，自寫 R(F)（跳過 m−1）、M1 剔 3%、M2 持續（含窗前上個換股日）、M3 殘差（numpy 正規方程自解）⇒ 4 件挑中格每個換股日名單 ＝ picks.csv.gz
 ③ 權益：自寫換股簿（續抱、跌停／停牌延後賣、漲停／停牌不買不遞補、金額 min(前日權益÷N, 現金)、賣出扣進場金額×0.585%、停止交易強制出場、下市了結）
    ＋ M4 覆蓋層 ⇒ 4 件 × 兩世界 各段年化／回落（自寫 window：窗首當日權益為基、(b−a+1)/245 年、峰谷回落）⇒ ＝ cells.csv
 ④ 假訊號 p：由 fake.csv.gz 自算 ⇒ ＝ summary
"""
from __future__ import annotations
import json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG

B = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(B, "resultsMomX")
SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
WORLDS = {"主": (SNAP, os.path.join(B, "resultsp9_engine/panel_ext.csv.gz"), "eligible", "2017-03-02", "2026-08-24",
                 {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}),
          "早年": (os.path.expanduser("~/earlydata/3edc0e2206/main/data"), os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz"),
                  "eligible_v", "2006-01-01", "2014-12-31", {"早年": ("2006-01-01", "2014-12-31")})}
COST, TOL = 0.00585, 1e-9
LORD = {"合格": 0, "另列": 1, "不合格": 2}


def lab(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


def wstats(eq, a, b):
    """[a, b]：以 eq[a] 為基（窗首當日）、年數 ＝ (b − a + 1)／245、窗內峰谷回落（自寫；與原件 window 讀法相同：窗 [a, b+1)）。"""
    seg = eq[a:b + 1]
    c = (seg[-1] / seg[0]) ** (245 / (b - a + 1)) - 1
    pk = np.maximum.accumulate(seg)
    return c, float(((seg - pk) / pk).min())


def main():
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    PK = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str})
    RES = {}
    # ① 挑格
    Z = Sm["0050"]; bad = []
    ex = T[(T["世界"] == "主") & (T["段"] == "探索")]
    c0, m0 = Z["探索"]["年化"], Z["探索"]["回落"]
    for M in ("M1", "M2", "M3", "M4"):
        x = ex[ex["件"] == M].copy(); b0 = ex[ex["件"] == ("M0" if M == "M4" else M)].set_index("格")
        dg = []
        for k in x["格"]:
            kk = k.replace("M4_", "M0_") if M == "M4" else k
            N = int(k.split("_N")[1])
            dg.append(bool(b0.loc[kk, "平均持股"] < N / 2 or b0.loc[kk, "換股簿現金比例"] > 0.30))
        x["dg"] = dg; pool = x[~x["dg"]]
        ps = pool[(pool["年化"] > c0) & (pool["比值"] >= c0 / abs(m0))]
        pp = (ps if len(ps) else pool).copy(); pp["_f"] = pp["頻率"].map({"月": 0, "季": 1})
        best = pp.sort_values(["比值", "年化", "F", "_f", "N"], ascending=[False, False, True, True, True]).iloc[0]
        pk = Sm["挑格"][M]
        cf = T[(T["世界"] == "主") & (T["段"] == "確認") & (T["格"] == best["格"])].iloc[0]
        ea = T[(T["世界"] == "早年") & (T["段"] == "早年") & (T["格"] == best["格"])].iloc[0]
        l1 = lab(cf["年化"], cf["回落"], Z["確認"]["年化"], Z["確認"]["回落"]); l2 = lab(ea["年化"], ea["回落"], Z["早年"]["年化"], Z["早年"]["回落"])
        fin = max((l1, l2), key=lambda l: LORD[l])
        if best["格"] != pk["格"] or l1 != pk["確認"]["標籤"] or l2 != pk["早年"]["標籤"] or fin != pk["件標籤（兩段較嚴）"]:
            bad.append(M)
    RES["① 挑格與標籤"] = {"不符": bad, "過": not bad}
    print(RES, flush=True)
    # ②③
    nb2 = 0; nsel = 0; mx3 = 0.0; det3 = {}
    for wn, (data, panp, elr, W0, W1, segs) in WORLDS.items():
        D.DATA = data
        cal = D.load_calendar(); n = len(cal)
        pan = pd.read_csv(panp, dtype={"stock_id": str}, parse_dates=["measure_date"])
        pan["el"] = (pan["liq_ok"].astype(str).isin(["True", "1"]) & pan["bars_ok"].astype(str).isin(["True", "1"])) if elr == "eligible_v" \
            else pan["eligible"].astype(str).isin(["True", "1"])
        U = UG.gate3(pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str))
        U = U[U["stock_id"].isin(set(pan["stock_id"]))]
        P = {}
        for sid, mk in zip(U["stock_id"], U["market"]):
            st = D.load_stock(sid, mk, cal)
            if st is None:
                continue
            raw = st.df["close"].to_numpy(float); tb = TR.one(sid, cal)
            P[sid] = {"c": pd.Series(raw).ffill().to_numpy(float), "o": st.df["open"].to_numpy(float), "v": np.isfinite(raw),
                      "trd": np.asarray(tb["trd"], bool), "up": np.asarray(tb["up_o"], bool), "dn": np.asarray(tb["dn_o"], bool)}
        dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=TR.load_official())
        w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1), side="right") - 1)
        SF = {s: int(np.flatnonzero(v["v"])[-1]) for s, v in P.items() if v["v"].any() and np.flatnonzero(v["v"])[-1] < w1}
        ymk = np.asarray(cal.year * 12 + cal.month)
        me = {}
        for i, k in enumerate(ymk):
            me[int(k)] = i
        reb = {}
        for d, g in pan.groupby("measure_date"):
            mp = int(cal.searchsorted(d))
            if mp >= n - 1 or cal[mp] != d or mp + 1 > w1:
                continue
            reb[mp + 1] = sorted(s for s in g.loc[g["el"], "stock_id"] if s in P)
        allr = sorted(reb); rebs = [e for e in allr if e >= w0]; pre = [e for e in allr if e < w0][-3:]
        w0 = rebs[0]
        bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)

        def RF(e, F):
            m = int(ymk[e]); a_, b_ = m - 2 - F, m - 2
            if a_ not in me or b_ not in me:
                return {}
            out = {}
            for s in reb[e]:
                x, y = P[s]["c"][me[a_]], P[s]["c"][me[b_]]
                if np.isfinite(x) and np.isfinite(y) and x > 0 and y > 0:
                    out[s] = y / x - 1
            return out

        def M3S(e, F, R):
            m = int(ymk[e]); b_ = m - 2
            ks = [k for k in range(b_ - 36, b_ + 1) if k in me]
            if len(ks) < 25:
                return {}
            pos = [me[k] for k in ks]; bm = bench[pos]; rb = bm[1:] / bm[:-1] - 1
            out = {}
            for s in R:
                c = P[s]["c"][pos]
                with np.errstate(invalid="ignore", divide="ignore"):
                    y = c[1:] / c[:-1] - 1
                ok = np.isfinite(y) & np.isfinite(rb)
                if ok.sum() < 24:
                    continue
                xx, yy = rb[ok], y[ok]; xm, ym_ = xx.mean(), yy.mean()
                bt = ((xx - xm) * (yy - ym_)).sum() / ((xx - xm) ** 2).sum(); al = ym_ - bt * xm
                res = np.full(len(y), np.nan); res[ok] = yy - al - bt * xx
                sd = np.std(res[ok], ddof=1)
                if not sd > 0 or not np.isfinite(res[-F:]).all():
                    continue
                out[s] = res[-F:].sum() / sd
            return out

        def topn(d, N, ex_=()):
            return [s for s, _ in sorted(((s, v) for s, v in d.items() if s not in ex_), key=lambda t: (-t[1], t[0]))[:N]]
        for M in ("M1", "M2", "M3", "M4"):
            pk = Sm["挑格"][M]; F, fq, N = pk["F"], pk["頻率"], pk["N"]
            ar = [e for e in pre + rebs if fq == "月" or cal[e].month in (1, 4, 7, 10)]
            sel = {}; prev = None
            for e in ar:
                R = RF(e, F)
                if M == "M2":
                    o_ = sorted(R, key=lambda s: (-R[s], s)); cur = set(o_[:math.ceil(0.3 * len(o_))])
                    if e >= w0:
                        sel[e] = [] if prev is None else topn({s: R[s] for s in cur & prev}, N)
                    prev = cur; continue
                if e < w0:
                    continue
                if M in ("M4",):
                    sel[e] = topn(R, N)
                elif M == "M1":
                    o_ = sorted(R, key=lambda s: (-R[s], s)); k = int(math.floor(0.03 * len(o_)))
                    sel[e] = topn(R, N, set(o_[:k]) | (set(o_[len(o_) - k:]) if k else set()))
                else:
                    sel[e] = topn(M3S(e, F, R), N)
            ref = PK[(PK["世界"] == wn) & (PK["件"] == M)]
            rs = {d: list(g.sort_values("名次")["sid"]) for d, g in ref.groupby("換股日")}
            for e, s_ in sel.items():
                nsel += 1
                if s_ != rs.get(str(cal[e].date()), []):
                    nb2 += 1
            # ③ 自寫換股簿
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
            if M == "M4":
                w = {}
                for e, s_ in sel.items():
                    cc = np.column_stack([P[s]["c"][e - 61:e] for s in s_]) if s_ and e >= 61 else None
                    if cc is None:
                        w[e] = 1.0; continue
                    with np.errstate(invalid="ignore", divide="ignore"):
                        r = cc[1:] / cc[:-1] - 1
                    ew = np.nanmean(r, axis=1); ew = ew[np.isfinite(ew)]
                    v = float(np.std(ew, ddof=1) * math.sqrt(245)) if len(ew) >= 30 else float("nan")
                    w[e] = min(1.0, 0.2 / v) if (v == v and v > 0) else 1.0
                e4 = np.ones(n); sl = 0.0; cs = 1.0
                for t in range(w0, w1 + 1):
                    if t > w0:
                        sl *= eq[t] / eq[t - 1]
                    tot = sl + cs
                    if t in w:
                        tg = w[t] * tot; cs = tot - tg - abs(tg - sl) * COST; sl = tg
                    e4[t] = sl + cs
                eq = e4
            for sn, (a0, b0) in segs.items():
                a_ = max(int(cal.searchsorted(pd.Timestamp(a0))), w0); b_ = min(int(cal.searchsorted(pd.Timestamp(b0), side="right") - 1), w1)
                c, m = wstats(eq, a_, b_)
                ref = T[(T["世界"] == wn) & (T["段"] == sn) & (T["格"] == pk["格"])].iloc[0]
                d = max(abs(c - ref["年化"]), abs(m - ref["回落"])); mx3 = max(mx3, d); det3[f"{wn}_{M}_{sn}"] = d
        print(wn, "done", flush=True)
    RES["② 4 件挑中格名單（兩世界、每個換股日）"] = {"比對換股日數": nsel, "不同": nb2, "過": nb2 == 0}
    RES["③ 自寫換股簿＋M4 覆蓋層：各段年化／回落"] = {"最大差": mx3, "逐項": det3, "過": mx3 <= TOL}
    # ④
    FK = pd.read_csv(os.path.join(OUT, "fake.csv.gz"), float_precision="round_trip"); b4 = []
    for M in ("M1", "M2", "M3", "M4"):
        for nm in ("確認", "早年"):
            x = FK[(FK["件"] == M)][f"{nm}_年化"].dropna().to_numpy(float)
            p = float(np.mean(x >= Sm["挑格"][M][nm]["年化"]))
            if abs(p - Sm["挑格"][M][f"假訊號_{nm}"]["p（隨機年化 ≥ 本格）"]) > 1e-12:
                b4.append((M, nm))
    RES["④ 假訊號 p"] = {"不符": b4, "過": not b4}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
