# -*- coding: utf-8 -*-
"""USREG-W1b 本體的【獨立路】查核。⛔ 不 import researchUSW1b／researchUSM*／us_data／research11／tradability。
只讀 ~/usdata/0043f97/data 的原始 CSV 與 ~/us_work/usw1b/（repo 外）主程式的逐顆彙總、成交紀錄、權益：
 ① 基準：自己從 macro/yahoo_SP500TR.csv、yahoo_GSPC.csv 算同窗年化／回落（ANN 252；淨股息版 ＝ GSPC 報酬 ＋ 0.7 ×（TR − GSPC））
 ② 各臂：從 seeds.csv 自己算 年化中位、回落中位、比值、標籤（條件一嚴格 ＞、條件二 ≥）⇒ 與 body_summary.json 逐臂比
 ③ 種子 102000：從 equity_seed102000_full.csv 自己算窗內年化／回落 ⇒ 與 seeds.csv 那一列比；
    從 audit_seed102000.csv 重建現金流（買 −金額、賣 ＋金額 − 成本）⇒ 模擬尾的現金 ＝ 權益末值；
    抽 30 筆成交，自己從原始價檔還原（Yahoo X × adjclose ÷ close；Tiingo adj*）⇒ 買價 ＝ 進場日開盤、賣價 ＝ 出場日收盤或延後日開盤
 ④ 訊號面板：從 panel_monthly.csv.gz 抽 60 列（在指數且 bars ≥ 120），自己算 季營收新高（容差 1e-4、8 季、140 天、value ≤ 0 當缺、
    可用日 ＝ first_filed 之後第一個 NYSE 交易日）、ma_stack、ma60_up、bars ⇒ 與面板比
輸出：resultsUSW1b/body_check.json（只有差與計數）；明細 ~/us_work/usw1b/check_detail.csv。
"""
import os, sys, json, math
import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/usdata/0043f97/data")
WORK = os.path.expanduser("~/us_work/usw1b")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSW1b")
W0, W1, ANN, COST = "2016-01-04", "2026-08-31", 252, 0.0005
CAL = pd.DatetimeIndex(sorted(pd.to_datetime(pd.read_csv(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), usecols=["date"])["date"])))


def wm(x, ann=ANN):
    x = np.asarray(x, float); y = len(x) / ann
    c = (x[-1] / x[0]) ** (1 / y) - 1
    pk = np.maximum.accumulate(x)
    return c, float(((x - pk) / pk).min())


def lab(c, m, cb, mb):
    k1 = c > cb; k2 = c / abs(m) >= cb / abs(mb)
    return "合格" if (k1 and k2) else ("另列" if k1 else "不合格")


def src_frame(src):
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(os.path.join(ROOT, "prices_yahoo", f + ".csv"), dtype={"date": str}); k = d["adjclose"] / d["close"]
        o, h, l, c = d["open"] * k, d["high"] * k, d["low"] * k, d["close"] * k
    else:
        d = pd.read_csv(os.path.join(ROOT, "prices", f + ".csv"), dtype={"date": str})
        o, h, l, c = d["adjOpen"], d["adjHigh"], d["adjLow"], d["adjClose"]
    return pd.DataFrame({"o": o.to_numpy(float), "h": h.to_numpy(float), "l": l.to_numpy(float), "c": c.to_numpy(float)},
                        index=pd.DatetimeIndex(pd.to_datetime(d["date"])))


_c = {}


def ticker_px(t):
    """面板每列 src 的同日還原 OHLC；無效列（非有限、≤0、高低矛盾）⇒ 沒有 K 棒。回 (DataFrame on panel dates, member Series)。"""
    if t in _c:
        return _c[t]
    pn = pd.read_csv(os.path.join(ROOT, "panel", t + ".csv"), dtype=str, keep_default_na=False)
    pn["date"] = pd.to_datetime(pn["date"]); pn["src0"] = pn["src"].str.rstrip("*")
    parts = []
    for s, g in pn.groupby("src0", sort=False):
        fr = src_frame(s).reindex(g["date"]); parts.append(fr)
    px = pd.concat(parts).sort_index()
    ok = np.isfinite(px).all(axis=1) & (px > 0).all(axis=1) & (px["l"] <= px[["o", "c"]].min(axis=1)) & (px[["o", "c"]].max(axis=1) <= px["h"])
    px = px[ok & px.index.isin(CAL)]
    mem = pd.Series(pn["in_index"].to_numpy() == "1", index=pn["date"])
    _c[t] = (px, mem)
    return _c[t]


def main():
    S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    res = {}; det = []
    i0, i1 = CAL.get_loc(pd.Timestamp(W0)), CAL.get_loc(pd.Timestamp(W1))
    tr = pd.read_csv(os.path.join(ROOT, "macro", "yahoo_SP500TR.csv"), usecols=["date", "adjclose"])
    tr = pd.Series(tr["adjclose"].to_numpy(float), pd.to_datetime(tr["date"])).reindex(CAL).ffill().to_numpy()
    gs = pd.read_csv(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), usecols=["date", "close"])
    gs = pd.Series(gs["close"].to_numpy(float), pd.to_datetime(gs["date"])).reindex(CAL).ffill().to_numpy()
    net = np.r_[1.0, np.cumprod(gs[1:] / gs[:-1] + 0.7 * (tr[1:] / tr[:-1] - gs[1:] / gs[:-1]))]
    bc, bm = wm(tr[i0:i1 + 1]); nc, nm = wm(net[i0:i1 + 1])
    B = S["基準"]
    d1 = max(abs(bc - B["SP500TR"]["年化"]), abs(bm - B["SP500TR"]["回落"]), abs(nc - B["SP500TR_扣30%股息（描述）"]["年化"]), abs(nm - B["SP500TR_扣30%股息（描述）"]["回落"]))
    res["①基準"] = {"最大差": d1}
    print("① 基準最大差 {:.1e}".format(d1), flush=True)
    D = pd.read_csv(os.path.join(WORK, "seeds.csv"))
    d2 = 0.0; same = True
    for arm, g in D.groupby("arm"):
        cb_, mb_ = (nc, nm) if arm == "div_net30" else (bc, bm)
        c, m = float(np.median(g["cagr"])), float(np.median(g["mdd"]))
        L = lab(c, m, cb_, mb_); J = S["臂"][arm]
        d2 = max(d2, abs(c - J["年化中位"]), abs(m - J["回落中位"])); same &= (L == J["標籤"]) and len(g) == S["種子數"]
        det.append({"查核": "②", "臂": arm, "年化中位": c, "回落中位": m, "標籤": L, "主程式標籤": J["標籤"]})
    res["②各臂中位與標籤"] = {"最大差": d2, "標籤全同且種子數對": bool(same)}
    print("② 各臂中位最大差 {:.1e}｜標籤全同 {}".format(d2, same), flush=True)
    E = pd.read_csv(os.path.join(WORK, "equity_seed102000_full.csv")); eq = E["equity"].to_numpy(float)
    dates = pd.to_datetime(E["date"]); a = int(np.flatnonzero(dates == pd.Timestamp(W0))[0]); b = int(np.flatnonzero(dates == pd.Timestamp(W1))[0])
    c0, m0 = wm(eq[a:b + 1]); row = D[(D["arm"] == "main") & (D["seed"] == 102000)].iloc[0]
    d3 = max(abs(c0 - row["cagr"]), abs(m0 - row["mdd"]))
    A = pd.read_csv(os.path.join(WORK, "audit_seed102000.csv"), dtype={"sid": str})
    cash = 1.0 + float((-A.loc[A["side"] == "buy", "amt"]).sum() + (A.loc[A["side"] == "sell", "amt"] - A.loc[A["side"] == "sell", "cost"]).sum())
    nbuy, nsell = int((A["side"] == "buy").sum()), int((A["side"] == "sell").sum())
    d_cash = abs(cash - eq[-1])
    rng = np.random.default_rng(20260927); pxd = 0.0; npx = 0
    for i in rng.choice(len(A), min(30, len(A)), replace=False):
        r = A.iloc[int(i)]; px, _ = ticker_px(r["sid"]); d = pd.Timestamp(r["date"])
        if r["side"] == "buy":
            v = px.loc[d, "o"]
        else:
            v = px.loc[d, "c"] if d in px.index else np.nan
            if not (np.isfinite(v) and abs(v - r["px"]) / v < 1e-9):
                v2 = px.loc[d, "o"] if d in px.index else np.nan          # 延後出場 ⇒ 開盤
                v = v2 if (np.isfinite(v2) and abs(v2 - r["px"]) / v2 < 1e-9) else v
        e = abs(v - r["px"]) / v if np.isfinite(v) else np.inf
        pxd = max(pxd, e); npx += 1
        det.append({"查核": "③成交價", "side": r["side"], "相對差": e})
    res["③種子102000"] = {"窗內年化回落差": d3, "成交紀錄重建現金與權益末值差": d_cash, "買筆數": nbuy, "賣筆數": nsell, "抽查成交價筆數": npx, "成交價最大相對差": pxd}
    print("③ 窗內差 {:.1e}｜現金重建差 {:.1e}（買 {} 賣 {}）｜成交價 {} 筆最大相對差 {:.1e}".format(d3, d_cash, nbuy, nsell, npx, pxd), flush=True)
    P = pd.read_csv(os.path.join(WORK, "panel_monthly.csv.gz"))
    base = P[P["base"]]
    q = pd.read_csv(os.path.join(ROOT, "fundamentals", "quarterly_revenue.csv"), usecols=["ticker", "period_end", "value", "first_filed"])
    q["period_end"] = pd.to_datetime(q["period_end"]); q["first_filed"] = pd.to_datetime(q["first_filed"])
    q["avail"] = [CAL[CAL.searchsorted(x, side="right")] if CAL.searchsorted(x, side="right") < len(CAL) else pd.NaT for x in q["first_filed"]]
    bad = {"rev": 0, "ma_stack": 0, "ma60_up": 0, "bars": 0, "member": 0}; nchk = 0
    for i in rng.choice(len(base), 60, replace=False):
        r = base.iloc[int(i)]; t = r["t"]; d = pd.Timestamp(r["date"])
        qt = q[(q["ticker"] == t) & (q["avail"] <= d)].sort_values("period_end").tail(8)
        if len(qt) < 8:
            rv = False
        else:
            v = qt["value"].to_numpy(float); gap = np.diff(qt["period_end"].to_numpy("datetime64[D]")).astype(int)
            rv = bool((gap <= 140).all() and (v > 0).all() and v[-1] >= v[:-1].max() - abs(v[:-1].max()) * 1e-4)
        px, mem = ticker_px(t)
        c = px["c"].reindex(CAL[CAL >= pd.Timestamp("2015-11-02")]).ffill()
        c = c[c.index <= d]; nb = int(px.index[px.index <= d].size)
        m20, m60, m120 = c.iloc[-20:].mean(), c.iloc[-60:].mean(), c.iloc[-120:].mean()
        m60p = c.iloc[-80:-20].mean()
        ms = 100.0 if (c.iloc[-1] > m20 > m60 > m120) else 0.0
        mu = 100.0 if m60 > m60p else 0.0
        bad["rev"] += int(rv != bool(r["rev_ok"])); bad["ma_stack"] += int(ms != r["ma_stack"]); bad["ma60_up"] += int(mu != r["ma60_up"])
        bad["bars"] += int(nb != r["bars"]); bad["member"] += int(not (bool(mem.get(d, False)) and d in px.index)); nchk += 1
    res["④訊號面板"] = {"抽查列": nchk, "不符": bad}
    print("④ 面板 {} 列：{}".format(nchk, bad), flush=True)
    pd.DataFrame(det).to_csv(os.path.join(WORK, "check_detail.csv"), index=False)
    allok = d1 < 1e-12 and d2 < 1e-12 and same and d3 < 1e-12 and d_cash < 1e-9 and pxd < 1e-9 and sum(bad.values()) == 0
    res["全部通過"] = bool(allok)
    json.dump(res, open(os.path.join(OUT, "body_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部通過" if allok else "⛔ 有不符", flush=True)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
