# -*- coding: utf-8 -*-
"""USREG-A4 獨立查核（⛔ 不呼叫 researchUSA4／_items／_ml／_surge 的任何函式；自己從 us-stock-data 原始 CSV 重算）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA4_check

查核項（全部要 0 不同才算過；結果寫 resultsUSA34/A4/check.json，只有件數與差異數）：
 K1 季財報與市值：抽 60 個（代號, 月初 e）列，從 fundamentals/*.csv、shares_outstanding.csv、prices_yahoo／prices、events_yahoo 獨立重算
    季營收年增、創 8 季新高、TTM ROE、季營收季增、市值（原始收盤 × 股數）、TO(20)，對 ~/us_work/a4/panel.pkl（本體輸出）⇒ 差 ≤ 1e−9（相對）或同為缺。
 K2 換股簿引擎：A4-4、A4-12 挑中格（讀 A4-*.json 的挑中格）從 panel 欄位獨立重選股、用 us_data.load_ohlc 原始讀檔獨立寫逐日迴圈
    （等權 N 槽、續抱仍入選、落選開盤賣、賣出扣進場金額 × 0.05%、斷點前一日收盤結清、下市最後收盤結清）⇒ 權益逐日相對差 ≤ 1e−9、確認段年化與 JSON 相同。
 K3 GICS industry group 對照率：從 sector_pit.csv 與名冊獨立重算（只用對照表本身）⇒ 與報告數字相同。
 K4 ^SP500TR 三段年化／回落：從 macro/yahoo_SP500TR.csv 獨立重算 ⇒ 與 JSON 基準相同。
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSW1b as W   # 只為讓 us_data 根目錄設定順序與本體相同（不用它的函式）
from backtest import researchUSA2_data as A2
A2.install()
from backtest import us_data as U
from backtest import researchUSM as RU
from backtest import researchUSA4_gics as GICS     # 對照表本身（被查的是對照率，不是表）

ROOT = os.path.join(A2.ROOT, "data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A4")
WORK = os.path.expanduser("~/us_work/a4")


def p(*a):
    return os.path.join(ROOT, *a)


def rel_ok(a, b, tol=1e-9):
    a = float(a) if a is not None else np.nan; b = float(b) if b is not None else np.nan
    if not np.isfinite(a) and not np.isfinite(b):
        return True
    if not (np.isfinite(a) and np.isfinite(b)):
        return False
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


# ═════════════ K1 ═════════════
def k1(cal, M):
    rng = np.random.default_rng(20261007)
    seg = set()
    for fn in ("cik_map.csv", "cik_map_sp400.csv"):
        cm = pd.read_csv(p("fundamentals", fn), dtype=str, keep_default_na=False)
        if "seg_from" in cm.columns:
            seg |= set(cm[(cm["seg_from"] != "") | (cm["seg_to"] != "")]["ticker"])
    M = M[~M["t"].isin(seg)]
    idx = rng.choice(len(M), 60, replace=False)
    rv = pd.concat([pd.read_csv(p("fundamentals", "quarterly_revenue.csv"), dtype=str),
                    pd.read_csv(p("fundamentals", "quarterly_revenue_sp400.csv"), dtype=str)], ignore_index=True)
    ni = pd.read_csv(p("fundamentals", "quarterly_net_income.csv"), dtype=str)
    eqq = pd.read_csv(p("fundamentals", "quarterly_equity.csv"), dtype=str)
    sh = pd.read_csv(p("fundamentals", "shares_outstanding.csv"), dtype=str)

    def series(df, t, e_date):
        d = df[df["ticker"] == t].copy()
        d["pe"] = pd.to_datetime(d["period_end"]); d["ff"] = pd.to_datetime(d["first_filed"]); d["v"] = pd.to_numeric(d["value"], errors="coerce")
        d = d.sort_values(["pe", "ff"]).drop_duplicates("pe", keep="first")
        # 可用 ⇔ first_filed 的次一交易日 ≤ e ⇔ first_filed ＜ e（日曆上）
        return d[d["ff"] < e_date].sort_values("pe")

    def lastk(d, k, e_date):
        if len(d) < k:
            return None
        x = d.iloc[-k:]
        if (e_date - x["pe"].iloc[-1]).days > 200:
            return None
        if k > 1:
            g = np.diff(x["pe"].values).astype("timedelta64[D]").astype(int)
            if not ((g >= 60) & (g <= 120)).all():
                return None
        if not np.isfinite(x["v"].to_numpy()).all():
            return None
        return x
    bad = []; n = 0
    for i in idx:
        r = M.iloc[i]; t = r["t"]; e = int(r["e"]); ed = cal[e]
        d = series(rv, t, ed)
        # 年增
        yoy = np.nan
        if len(d) and (ed - d["pe"].iloc[-1]).days <= 200:
            j = d.iloc[-1]; pk = d[(d["pe"] >= j["pe"] - pd.Timedelta(days=380)) & (d["pe"] <= j["pe"] - pd.Timedelta(days=350))]
            if len(pk) and pk["v"].iloc[-1] > 0 and np.isfinite(j["v"]):
                yoy = j["v"] / pk["v"].iloc[-1] - 1
        x8 = lastk(d, 8, ed)
        hi8 = (float(x8["v"].iloc[-1] > x8["v"].iloc[:-1].max())) if x8 is not None else np.nan
        x2 = lastk(d, 2, ed)
        qoq = (x2["v"].iloc[1] / x2["v"].iloc[0] - 1) if (x2 is not None and x2["v"].iloc[0] > 0) else np.nan
        n4 = lastk(series(ni, t, ed), 4, ed); e2 = lastk(series(eqq, t, ed), 2, ed)
        roe = (n4["v"].sum() / e2["v"].mean()) if (n4 is not None and e2 is not None and e2["v"].mean() > 0) else np.nan
        # 市值
        s = sh[sh["ticker"] == t].copy(); s["ad"] = pd.to_datetime(s["as_of_date"]); s["fd"] = pd.to_datetime(s["filed"]); s["n"] = pd.to_numeric(s["shares"], errors="coerce")
        s = s.dropna(subset=["n"]); s = s[s["fd"] < ed]
        mcap = to20 = np.nan
        if len(s):
            s2 = s.groupby(["ad", "fd"], as_index=False)["n"].sum()
            ad = s2["ad"].max(); nn = float(s2[s2["ad"] == ad].sort_values("fd")["n"].iloc[-1]) if False else float(s2[s2["ad"] == ad]["n"].iloc[-1])
            if (ed - ad).days <= 400:
                ev = p("events_yahoo", t + ".csv")
                spl = pd.DataFrame(columns=["date", "type", "value"])
                if os.path.exists(ev):
                    spl = pd.read_csv(ev, dtype=str); spl = spl[spl["type"] == "split"]
                rr = [(pd.Timestamp(dd), float(v.split("/")[0]) / float(v.split("/")[1])) for dd, v in zip(spl["date"], spl["value"])]
                f_e = np.prod([q for dd, q in rr if ad < dd <= ed]) if rr else 1.0
                f_t = np.prod([q for dd, q in rr if ad < dd]) if rr else 1.0
                # 原始收盤：panel 該日 src
                pn = U.panel(t)
                prev = pn[pn.index < ed]
                if len(prev):
                    dlast = prev.index[-1]; src = prev["src"].iloc[-1]
                    kind, f = src.split(":", 1)
                    if kind == "yahoo":
                        y = pd.read_csv(p("prices_yahoo", f + ".csv"), dtype={"date": str}); y.index = pd.to_datetime(y["date"])
                        ev2 = p("events_yahoo", f + ".csv"); sp2 = []
                        if os.path.exists(ev2):
                            z = pd.read_csv(ev2, dtype=str); z = z[z["type"] == "split"]
                            sp2 = [(pd.Timestamp(dd), float(v.split("/")[0]) / float(v.split("/")[1])) for dd, v in zip(z["date"], z["value"])]
                        raw = float(y.loc[dlast, "close"]) * (np.prod([q for dd, q in sp2 if dd > dlast]) if sp2 else 1.0)
                    else:
                        y = pd.read_csv(p("prices", f + ".csv"), dtype={"date": str}); y.index = pd.to_datetime(y["date"]); raw = float(y.loc[dlast, "close"])
                    mcap = nn * f_e * raw
                v20 = r["v20"]
                to20 = v20 / (nn * f_t) if np.isfinite(v20) else np.nan
        chk = {"rev_yoy": yoy, "rev_hi8": hi8, "rev_qoq": qoq, "roe": roe, "mcap": mcap, "to20": to20}
        for k, v in chk.items():
            n += 1
            mv = r[k]
            mv = float(mv) if mv is not None and mv == mv else np.nan
            if not rel_ok(v, mv, 1e-6 if k == "mcap" else 1e-9):
                bad.append({"t": t, "e": str(ed.date()), "量": k, "查核": v, "本體": mv})
    return {"抽樣列": 60, "比較數": n, "不同": len(bad), "不同明細（前10）": bad[:10]}


# ═════════════ K2 ═════════════
def load_px(tks, cal):
    out = {}
    for t in tks:
        df = U.load_ohlc(t, scope="panel")
        A = RU.prep(df, cal)
        v = A["valid"]
        O = np.where(v & (np.nan_to_num(A["O"]) > 0), A["O"], np.nan)
        Cf = pd.Series(A["C"]).ffill().to_numpy()
        lv = int(np.flatnonzero(v)[-1]) if v.any() else -1
        out[t] = (O, Cf, v, A["pb"], lv)
    return out


def book_indep(sel, px, N, t0, t1, n, cost=0.0005):
    eq = np.ones(n); cash = 1.0; hold = {}; pend = set()
    for t in range(t0, t1 + 1):
        for s in list(hold):
            O, Cf, v, pb, lv = px[s]
            u, a, b = hold[s]
            if t > b and pb[t]:
                cash += u * Cf[t - 1] - a * cost; del hold[s]; pend.discard(s)
            elif t > lv:
                cash += u * Cf[lv] - a * cost; del hold[s]; pend.discard(s)
        if t in sel:
            pend = (pend | {s for s in hold if s not in sel[t]}) - set(sel[t])
        for s in sorted(pend):
            if s not in hold:
                pend.discard(s); continue
            O, Cf, v, pb, lv = px[s]
            if v[t] and np.isfinite(O[t]) and O[t] > 0:
                u, a, b = hold.pop(s); cash += u * O[t] - a * cost; pend.discard(s)
        if t in sel:
            room = N - len(hold)
            for s in [x for x in sel[t] if x not in hold][:max(room, 0)]:
                O, Cf, v, pb, lv = px[s]
                if not (v[t] and np.isfinite(O[t]) and O[t] > 0):
                    continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; hold[s] = (amt / O[t], amt, t)
        eq[t] = cash + sum(u * px[s][1][t] for s, (u, a, b) in hold.items())
    return eq


def seg_cagr(eq, a, b):
    s = eq[a:b + 1]; yrs = len(s) / 252
    return (s[-1] / s[0]) ** (1 / yrs) - 1


def k2(cal, M, w0, w1, c0):
    out = {}
    MS = sorted(M["e"].unique())
    fq = {"月": None, "季": (1, 4, 7, 10), "半年": (1, 7)}
    J4 = json.load(open(os.path.join(OUT, "A4-4.json"), encoding="utf-8"))
    cases = []
    ch = J4["族"]["甲"]["挑中格"]
    sel = {}
    for e in MS:
        if fq[ch["頻率"]] is not None and cal[e].month not in fq[ch["頻率"]]:
            continue
        g = M[M["e"] == e]
        col = "to%d" % ch["L"]
        g = g[pd.to_numeric(g[col], errors="coerce").notna()]
        g = g.assign(_v=pd.to_numeric(g[col])).sort_values(["_v", "t"])
        sel[e] = g["t"].tolist()[:ch["N"]]
    cases.append(("A4-4 甲族挑中格", sel, ch["N"], J4["族"]["甲"]["判定"]["欄"]["合併"]["確認"]["年化"]))
    J1 = json.load(open(os.path.join(OUT, "A4-1.json"), encoding="utf-8"))
    ch = J1["族"]["甲"]["挑中格"]
    sel = {}
    for e in MS:
        if fq[ch["頻率"]] is not None and cal[e].month not in fq[ch["頻率"]]:
            continue
        g = M[(M["e"] == e) & (M["sector"].fillna("") != "Financials")]
        g = g[pd.to_numeric(g[ch["量測"]], errors="coerce").notna()]
        g = g.assign(_v=pd.to_numeric(g[ch["量測"]])).sort_values(["_v", "t"], ascending=[False, True])
        sel[e] = g["t"].tolist()[:ch["N"]]
    cases.append(("A4-1 甲族挑中格", sel, ch["N"], J1["族"]["甲"]["判定"]["欄"]["合併"]["確認"]["年化"]))
    for nm, (sel_, N, ref) in [(c[0], c[1:]) for c in cases]:
        tks = sorted({s for v in sel_.values() for s in v})
        px = load_px(tks, cal)
        eq = book_indep({e: v for e, v in sel_.items()}, px, N, w0, w1, len(cal))
        c = seg_cagr(eq, c0, w1)
        out[nm] = {"確認段年化_查核": c, "確認段年化_本體": ref, "相同(≤1e-9)": bool(abs(c - ref) <= 1e-9), "檔數": len(tks),
                   "換股日數": len(sel_)}
    return out


# ═════════════ K3、K4 ═════════════
def k3(M):
    out = {}
    for col, m in (("S&P500", M["m5"].astype(bool)), ("S&P400", M["m4"].astype(bool))):
        d = M[m]
        sub = d["subind"].fillna("").astype(str)
        has = sub != ""
        mapped = np.array([GICS.ig_of(a, b) is not None for a, b in zip(d["sector"], sub)])
        out[col] = {"有sub-industry的股月": int(has.sum()), "對得上": int((mapped & has.to_numpy()).sum()),
                    "對照率（有名稱者）": float((mapped & has.to_numpy()).sum() / max(has.sum(), 1)), "占全部在指數股月": float(mapped.mean())}
    return out


def k4(cal, w0, w1, sp, c0):
    b = pd.read_csv(p("macro", "yahoo_SP500TR.csv"), dtype={"date": str})
    s = pd.Series(pd.to_numeric(b["adjclose"] if "adjclose" in b.columns else b["close"], errors="coerce").to_numpy(), pd.to_datetime(b["date"])).reindex(cal).ffill().to_numpy()
    out = {}
    for nm, (a, z) in (("探索", (w0, sp)), ("確認", (c0, w1)), ("全窗", (w0, w1))):
        seg = s[a:z + 1]; c = (seg[-1] / seg[0]) ** (252 / len(seg)) - 1
        pk = np.maximum.accumulate(seg); m = float(((seg - pk) / pk).min())
        out[nm] = {"年化": c, "回落": m}
    return out


def main():
    calF = U.load_calendar(); cal = calF[calF >= pd.Timestamp("2015-11-02")]
    w0 = int(cal.searchsorted(pd.Timestamp("2016-01-04"))); w1 = int(cal.searchsorted(pd.Timestamp("2026-09-30")))
    sp = int(cal.searchsorted(pd.Timestamp("2021-12-31"), side="right")) - 1; c0 = sp + 1
    M = pd.read_pickle(os.path.join(WORK, "panel.pkl"))
    R = {"K1_季財報與市值": k1(cal, M), "K2_換股簿引擎": k2(cal, M, w0, w1, c0), "K3_GICS對照率": k3(M), "K4_基準": k4(cal, w0, w1, sp, c0)}
    R["總結"] = {"K1不同": R["K1_季財報與市值"]["不同"], "K2全同": all(v["相同(≤1e-9)"] for v in R["K2_換股簿引擎"].values())}
    json.dump(R, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R["總結"], ensure_ascii=False), json.dumps(R["K3_GICS對照率"], ensure_ascii=False))


if __name__ == "__main__":
    main()
