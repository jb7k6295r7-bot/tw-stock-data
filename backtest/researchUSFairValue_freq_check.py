# -*- coding: utf-8 -*-
"""美股合理價機械版——頻率表獨立查核（⛔ 不算任何報酬）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSFairValue_freq_check

A 獨立寫法重算幾個評估日的母體、四條門檻、合理價與分組（只共用常數與 CSV 路徑；讀檔、PIT、分割、財年、公式全部另寫），
  逐 (評估日, 代號) 對 freq 的私有明細檔，報不一致筆數（數值差 ≤ 1e−9 相對誤差判同）。
B 合理價公式：等比級數封閉式 vs freq.fair_value（隨機 2,000 組）＋一組手算。
C ★10 推得分割的驗證：同一偵測法套在 2016-06 之後，對事件檔（Yahoo split）召回率與精確率。
D Yahoo close 是否已調分割：每個事件日前後收盤比不應出現分割倍數的跳。
E 本益比點的近四季 EPS 連續性：相鄰季點比值超出 [0.4, 2.5] 的筆數（疑似漏調分割；只描述）。
私有：repo 輸出只放筆數、代號與日期；⛔ 不寫價格、財報值或其比值。
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSFairValue_freq as FQ   # noqa: E402  （只取常數、路徑與被查的函式）

D = os.path.join(FQ.ROOT, "data")
CHECK_IDX = (0, 9, 19, -1)


# ═════════════ 獨立讀檔 ═════════════
def rd(*a, **k):
    return pd.read_csv(os.path.join(D, *a), **k)


class Data:
    def __init__(self):
        g = rd("macro", "yahoo_GSPC.csv", usecols=["date"])
        self.cal = pd.to_datetime(g["date"]).sort_values().reset_index(drop=True)
        self.fund = {}
        for f in ("net_income", "eps_diluted", "diluted_shares", "dps", "equity", "equity_incl_nci", "operating_income", "cfo"):
            q = rd("fundamentals", "quarterly_%s.csv" % f, dtype=str)
            q = q.loc[q["index"].isin(["sp500", "both"]),
                      ["ticker", "period_start", "period_end", "value", "first_filed", "first_form", "tag", "derived"]].copy()
            q["pe"] = pd.to_datetime(q["period_end"])
            q["ps"] = pd.to_datetime(q["period_start"], errors="coerce")
            q["ff"] = pd.to_datetime(q["first_filed"])
            q["v"] = q["value"].astype(float)
            q["der"] = q["derived"].astype(int)
            self.fund[f] = q
        so = rd("fundamentals", "shares_outstanding.csv", dtype=str, keep_default_na=False)
        so = so[so["index"].isin(["sp500", "both"])].copy()
        so["asof"] = pd.to_datetime(so["as_of_date"])
        so["fd"] = pd.to_datetime(so["filed"])
        so["sh"] = so["shares"].astype(float)
        self.so = so
        ds = rd("fundamentals", "quarterly_diluted_shares.csv", dtype=str)
        ds = ds[ds["index"].isin(["sp500", "both"])].copy()
        ds["ff"] = pd.to_datetime(ds["first_filed"]); ds["lf"] = pd.to_datetime(ds["latest_filed"])
        ds["pe"] = pd.to_datetime(ds["period_end"])
        ds["v"] = ds["value"].astype(float); ds["lv"] = ds["latest_value"].astype(float)
        self.ds_full = ds
        self.univ = rd("membership", "universe.csv", dtype=str, keep_default_na=False)
        rm = rd("membership", "renames_manual.csv", dtype=str, keep_default_na=False)
        self.until = {o: pd.Timestamp(u) for o, u in zip(rm["old"], rm["until"]) if u}

    def qpoint(self, y, m, dd):
        qe = pd.Timestamp(y, m, dd)
        c = self.cal[self.cal < qe]
        return c.iloc[-1]


def price(src):
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        x = rd("prices_yahoo", f + ".csv")
        s = pd.Series(x["close"].values, index=pd.to_datetime(x["date"]))
        ev = []
        pth = os.path.join(D, "events_yahoo", f + ".csv")
        if os.path.exists(pth):
            e = pd.read_csv(pth, dtype=str)
            e = e[e["type"] == "split"]
            ev = [(pd.Timestamp(a), eval(b.replace("/", "/"))) for a, b in zip(e["date"], e["value"])]
        return s.dropna(), ev
    x = rd("prices", f + ".csv")
    idx = pd.to_datetime(x["date"])
    sf = x["splitFactor"].astype(float)
    # 由後往前累乘：當日之後（不含當日）的 splitFactor 乘積
    after = sf[::-1].cumprod()[::-1].shift(-1).fillna(1.0).values
    s = pd.Series(x["close"].astype(float).values / after, index=idx)
    ev = [(t, k) for t, k in zip(idx, sf) if k != 1.0]
    return s.dropna(), ev


def detect(Dd, t):
    """另寫一次 ★10：相鄰兩份申報（依 first_filed、period_end 排序）股數跳點 ＋ 早期列被重編同比。"""
    G = Dd.ds_full[Dd.ds_full["ticker"] == t].sort_values(["ff", "pe"]).reset_index(drop=True)
    g = G[G["derived"] == "0"].reset_index(drop=True)
    res = []
    cand = sorted({a / b for a in range(1, 21) for b in range(1, 21) if a != b} |
                  {float(a) for a in range(21, 101)} | {1.0 / a for a in range(21, 101)})
    for i in range(1, len(g)):
        a, b = g.iloc[i - 1], g.iloc[i]
        if a["ff"] == b["ff"] or min(a["v"], b["v"]) < 1e6:
            continue
        j = b["v"] / a["v"]
        if 0.7 <= j <= 1.4:
            continue
        m = G[(G["ff"] <= a["ff"]) & (G["lf"] >= b["ff"]) & (G["v"] >= 1e6)]
        q = (m["lv"] / m["v"]).values
        q = q[np.isfinite(q)]
        q = q[np.abs(np.log(q / j)) <= math.log(1.15)]
        if not len(q):
            continue
        med = float(np.median(q))
        best = min(cand, key=lambda c: abs(math.log(c / med)))
        if abs(math.log(best / med)) > 0.02:
            continue
        mid = G[(G["ff"] > a["ff"]) & (G["ff"] < b["ff"]) & (G["v"] >= 1e6)].sort_values(["ff", "v"])
        dte = b["ff"]
        for _, r in mid.iterrows():
            if abs(math.log(r["v"] / a["v"] / best)) <= math.log(1.15):
                dte = r["ff"]
                break
        if res and res[-1][0] == dte:
            continue
        res.append((dte, best, a["ff"]))
    return res


def splits_for(Dd, t, src):
    s, ev = price(src)
    p0 = s.index.min()
    out = list(ev)
    for dte, k, prev in detect(Dd, t):
        if prev >= p0:
            continue
        if any(abs((dte - x).days) <= 200 and abs(math.log(k / y)) <= 0.03 for x, y in ev):
            continue
        out.append((dte, k))
    return out


def fac(sp, b):
    return float(np.prod([k for x, k in sp if x > b])) if sp else 1.0


# ═════════════ 獨立分類 ═════════════
def ind_classify(Dd, t, d, panel_cache, qpts):
    pth = os.path.join(D, "panel", t + ".csv")
    if t not in panel_cache:
        panel_cache[t] = pd.read_csv(pth, dtype={"src": str}, parse_dates=["date"]).set_index("date") if os.path.exists(pth) else None
    pn = panel_cache[t]
    if pn is None or d not in pn.index or int(pn.loc[d, "in_index"]) != 1:
        return {"stage": "other"}
    if t in Dd.until and d <= Dd.until[t]:
        return {"stage": "fund_mismatch"}
    src = pn.loc[d, "src"].rstrip("*")
    cl, _ = price(src)
    if d not in cl.index:
        return {"stage": "no_close"}
    sp = splits_for(Dd, t, src)
    so = Dd.so[(Dd.so["ticker"] == t) & (Dd.so["fd"] < d)]
    if not len(so):
        return {"stage": "mcap_na"}
    f_last = so[so["fd"] == so["fd"].max()]
    f_last = f_last[f_last["asof"] == f_last["asof"].max()]
    pl = f_last[f_last["share_class"] == ""]
    if len(pl):
        sh = pl["sh"].iloc[0]
    else:
        ok = f_last["share_class"].str.contains("Common|Capital", case=False, regex=True) & \
            ~f_last["share_class"].str.contains("Preferred|Deposit|Note|Due|Subsidiar|Corporation|Company|Units|LLC|Partnership|Trust|Exchangeable",
                                                case=False, regex=True)
        if not ok.any():
            return {"stage": "mcap_na"}
        sh = f_last.loc[ok, "sh"].sum()
    mcap = sh * fac(sp, f_last["asof"].iloc[0]) * cl.loc[d]
    if mcap < FQ.MCAP_MIN:
        return {"stage": "mcap_small"}
    F = {f: q[(q["ticker"] == t) & (q["ff"] < d)] for f, q in Dd.fund.items()}
    out = {"stage": "pop"}
    ni = F["net_income"].set_index("pe")

    def chain(q4):
        qs = [q4]
        while len(qs) < 4:
            ps = ni.loc[qs[-1], "ps"]
            if pd.isna(ps):
                return None
            c = ni[(ni.index < qs[-1]) & ((ni.index - ps).days >= -8) & ((ni.index - ps).days <= 6)]
            if len(c) != 1:
                return None
            qs.append(c.index[0])
        sp_days = (q4 - ni.loc[qs[-1], "ps"]).days
        return qs if 351 <= sp_days <= 380 else None

    # 註：freq 的 fy_quarters 在【全部】淨利列上找鏈，再要求 4 季都 < d；這裡等價（先篩 < d 再找鏈：鏈上的季都 < d 才成立）
    allni = Dd.fund["net_income"]
    allni = allni[allni["ticker"] == t].set_index("pe")

    def chain_all(q4):
        qs = [q4]
        while len(qs) < 4:
            ps = allni.loc[qs[-1], "ps"]
            if pd.isna(ps):
                return None
            c = allni[(allni.index < qs[-1]) & ((allni.index - ps).days >= -8) & ((allni.index - ps).days <= 6)]
            if len(c) == 0:
                return None
            c = c.assign(_d=np.abs((c.index - (ps - pd.Timedelta(days=1))).days)).sort_values("_d", kind="stable")
            qs.append(c.index[0])
        sp_days = (q4 - allni.loc[qs[-1], "ps"]).days
        return qs if 351 <= sp_days <= 380 else None

    k10 = ni[ni["first_form"].fillna("").str.startswith("10-K")].index.sort_values(ascending=False)
    estar = None
    for pe in k10:
        qs = chain_all(pe)
        if qs is not None and all(((ni.index - x).days.map(abs) <= 5).any() for x in qs):
            estar = pe
            break
    if estar is None or (d - estar).days > 456:
        out.update(r1="na", r2="na", r3="na", r4="na", all_pass=False)
        return out
    W = [(estar, chain_all(estar))]
    for k in range(1, 5):
        tgt = estar - pd.DateOffset(years=k)
        cands = [x for x in allni.index if abs((x - tgt).days) <= 20]
        got = (tgt, None)
        for x in cands:
            c = chain_all(x)
            if c is not None:
                got = (x, c)
                break
        W.append(got)

    def val(f, pe, tol):
        q = F[f]
        if not len(q):
            return None
        x = q[(q["pe"] - pe).abs() <= pd.Timedelta(days=tol)]
        return None if not len(x) else x.sort_values("ff", kind="stable").iloc[0]

    def asum(f, qs):
        if qs is None:
            return None
        s = 0.0
        for pe in qs:
            r = val(f, pe, 5)
            if r is None:
                return None
            s += r["v"]
        return s

    def epsq(pe, asof):
        e = F["eps_diluted"] if asof == d else Dd.fund["eps_diluted"][(Dd.fund["eps_diluted"]["ticker"] == t) & (Dd.fund["eps_diluted"]["ff"] < asof)]
        n_ = F["net_income"] if asof == d else Dd.fund["net_income"][(Dd.fund["net_income"]["ticker"] == t) & (Dd.fund["net_income"]["ff"] < asof)]
        s_ = F["diluted_shares"] if asof == d else Dd.fund["diluted_shares"][(Dd.fund["diluted_shares"]["ticker"] == t) & (Dd.fund["diluted_shares"]["ff"] < asof)]
        pick = lambda q: (lambda x: None if not len(x) else x.sort_values("ff", kind="stable").iloc[0])(q[(q["pe"] - pe).abs() <= pd.Timedelta(days=5)])
        r = pick(e)
        if r is not None and r["der"] in (0, 1):
            return r["v"] / fac(sp, r["ff"])
        a, b = pick(n_), pick(s_)
        if a is not None and b is not None and b["v"] >= 1e6:
            return a["v"] / b["v"] / fac(sp, max(a["ff"], b["ff"]))
        if r is not None:
            return r["v"] / fac(sp, r["ff"])
        return None

    nis = [asum("net_income", qs) for _, qs in W]
    hit = miss = 0
    for (e, qs), n in zip(W, nis):
        eq = val("equity", e, 5) if qs is not None else None
        if eq is None and qs is not None:
            eq = val("equity_incl_nci", e, 5)
        if n is None or eq is None:
            miss += 1
        elif eq["v"] > 0 and n / eq["v"] >= 0.15:
            hit += 1
    out["r1"] = "pass" if hit >= 4 else ("fail" if hit + miss < 4 else "na")
    loss = unk = 0
    for (e, qs), n in zip(W, nis):
        if n is None:
            unk += 1
        elif n < 0:
            oi = asum("operating_income", qs)
            if oi is None:
                unk += 1
            elif oi <= 0:
                loss += 1
    out["r2"] = "fail" if loss else ("pass" if not unk else "na")

    def aeps(qs):
        if qs is None:
            return None
        v = [epsq(x, d) for x in qs]
        return None if any(x is None for x in v) else sum(v)
    a_end, a_st = aeps(W[0][1]), aeps(W[4][1])
    gh = None
    if a_end is None or a_st is None:
        out["r3"] = "na"
    elif a_st <= 0 or a_end <= 0:
        out["r3"] = "fail"
    else:
        gh = (a_end / a_st) ** 0.25 - 1
        out["r3"] = "pass" if gh >= 0.12 else "fail"
    cf = [asum("cfo", qs) for _, qs in W]
    if None in cf or None in nis:
        out["r4"] = "na"
    else:
        out["r4"] = "fail" if sum(nis) <= 0 else ("pass" if sum(cf) / sum(nis) >= 0.8 else "fail")
    out["all_pass"] = all(out[k] == "pass" for k in ("r1", "r2", "r3", "r4"))
    if not out["all_pass"]:
        return out

    grid_src = pd.concat([Dd.fund["net_income"].loc[Dd.fund["net_income"]["ticker"] == t, "pe"],
                          Dd.fund["eps_diluted"].loc[Dd.fund["eps_diluted"]["ticker"] == t, "pe"]]).drop_duplicates().sort_values()
    grid = []
    for x in grid_src:
        if not grid or (x - grid[-1]).days > 5:
            grid.append(x)

    def ttm(asof):
        cands = []
        for f in ("net_income", "eps_diluted"):
            q = Dd.fund[f]
            q = q[(q["ticker"] == t) & (q["ff"] < asof)]
            if len(q):
                cands.append(q["pe"].max())
        if not cands:
            return None, None
        lp = max(cands)
        if (asof - lp).days > 200:
            return None, None
        g0 = [x for x in grid if abs((x - lp).days) <= 5]
        if not g0:
            return None, None
        qs = [g0[0]]
        while len(qs) < 4:
            prev = [x for x in grid if 75 <= (qs[-1] - x).days <= 105]
            if not prev:
                return None, None
            qs.append(prev[-1])
        v = [epsq(x, asof) for x in qs]
        return (None if any(x is None for x in v) else sum(v)), qs

    E0, qs = ttm(d)
    if E0 is None:
        out["val"] = "E0_na"
        return out
    pes, first = [], None
    for q in qpts:
        if q > d or q < d - pd.DateOffset(years=10) or q not in cl.index:
            continue
        tt, _ = ttm(q)
        if tt is not None and tt > 0:
            pes.append(cl.loc[q] / tt)
            first = q if first is None else first
    if first is None or first > d - pd.DateOffset(years=3):
        out["val"] = "peT_na"
        return out
    peT = min(float(np.median(pes)), 25.0)
    g = min(0.8 * gh, 0.15)
    dsum = 0.0
    for x in qs:
        r = val("dps", x, 5)
        if r is not None:
            dsum += r["v"] / fac(sp, r["ff"])
    if E0 <= 0:
        out.update(val="ok", group="偏貴", multiple=float("inf"))
        return out
    po = min(max(dsum / E0, 0), 1)
    # 等比級數封閉式（與 freq 的逐年迴圈不同寫法）
    a = 1 + g
    b = 1 + g / 2
    pv1 = sum(E0 * a ** t_ * po / 1.1 ** t_ for t_ in range(1, 6))
    e5 = E0 * a ** 5
    pv2 = sum(e5 * b ** (t_ - 5) * po / 1.1 ** t_ for t_ in range(6, 11))
    fv = pv1 + pv2 + e5 * b ** 5 * peT / 1.1 ** 10
    m = cl.loc[d] / fv
    out.update(val="ok", multiple=m, group=("可買" if m <= 1.0 else ("接近" if m <= 1.15 else "偏貴")), fv=fv, E0=E0, pe_T=peT)
    return out


# ═════════════ B 公式 ═════════════
def check_formula():
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(2000):
        E0, g, pe, po = rng.uniform(0.1, 20), rng.uniform(0.0, 0.15), rng.uniform(5, 25), rng.uniform(0, 1)
        a, b = 1 + g, 1 + g / 2
        r1, r2 = a / 1.1, b / 1.1
        e5 = E0 * a ** 5
        pv = E0 * po * (r1 * (1 - r1 ** 5) / (1 - r1) if abs(1 - r1) > 1e-12 else 5)
        pv += e5 * po / 1.1 ** 5 * (r2 * (1 - r2 ** 5) / (1 - r2) if abs(1 - r2) > 1e-12 else 5)
        pv += e5 * b ** 5 * pe / 1.1 ** 10
        worst = max(worst, abs(pv / FQ.fair_value(E0, g, pe, po) - 1))
    # 手算：E0=5、g=10%、pe_T=20、配息率 0.3
    # e1..e5 = 5.5, 6.05, 6.655, 7.3205, 8.05255；e6..e10 = ×1.05 逐年：8.4551775, 8.877936375, 9.32183319375, 9.7879248534375, 10.277321096109375
    es = [5.5, 6.05, 6.655, 7.3205, 8.05255, 8.4551775, 8.877936375, 9.32183319375, 9.7879248534375, 10.277321096109375]
    hand = sum(e * 0.3 / 1.1 ** (i + 1) for i, e in enumerate(es)) + es[-1] * 20 / 1.1 ** 10
    return {"封閉式vs迴圈_最大相對差": worst, "手算": hand, "程式": FQ.fair_value(5, 0.10, 20, 0.3),
            "手算相符": abs(hand - FQ.fair_value(5, 0.10, 20, 0.3)) < 1e-9}


# ═════════════ C 推得分割驗證 ═════════════
def check_split_detect(Dd):
    tick = sorted(set(Dd.ds_full["ticker"]))
    ev_all, hit_ev = 0, 0
    inf_all, hit_inf = 0, 0
    miss_list = []
    fp_list = []
    for t in tick:
        pth = os.path.join(D, "events_yahoo", t + ".csv")
        if not os.path.exists(pth):
            continue
        e = pd.read_csv(pth, dtype=str)
        e = e[e["type"] == "split"]
        ev = [(pd.Timestamp(a), eval(b)) for a, b in zip(e["date"], e["value"])]
        ev = [(x, k) for x, k in ev if x >= pd.Timestamp("2016-06-01") and x <= pd.Timestamp("2025-12-31")
              and abs(math.log(k)) >= math.log(1.4)]          # 真分割（排除分拆等小比值調整）
        inf = [(x, k, p) for x, k, p in FQ.detect_splits(t) if p >= pd.Timestamp("2016-06-01") and x <= pd.Timestamp("2026-06-30")]
        ds_t = Dd.ds_full[Dd.ds_full["ticker"] == t]
        for x, k in ev:
            # 只算有股數資料涵蓋的事件（事件前後都有申報）
            if not ((ds_t["ff"] < x).any() and (ds_t["ff"] > x + pd.Timedelta(days=120)).any()):
                continue
            ev_all += 1
            if any(p < x <= y + pd.Timedelta(days=5) and abs(math.log(k / kk)) <= 0.03 for y, kk, p in inf):
                hit_ev += 1
            else:
                miss_list.append("%s %s ×%s" % (t, x.date(), round(k, 4)))
        for y, kk, p in inf:
            inf_all += 1
            if any(p < x <= y + pd.Timedelta(days=5) and abs(math.log(k / kk)) <= 0.03 for x, k in
                   [(pd.Timestamp(a), eval(b)) for a, b in zip(e["date"], e["value"])]):
                hit_inf += 1
            else:
                fp_list.append("%s %s ×%s" % (t, y.date(), kk))
    return {"事件數(2016-06~2025，|log k|≥log1.4，有股數涵蓋)": ev_all, "召回": hit_ev,
            "召回率": hit_ev / ev_all if ev_all else None, "推得數": inf_all, "推得命中事件": hit_inf,
            "精確率": hit_inf / inf_all if inf_all else None, "漏抓": miss_list[:40], "誤報": fp_list[:40]}


# ═════════════ D Yahoo close 已調分割 ═════════════
def check_yahoo_adjusted():
    bad, n = [], 0
    for f in sorted(os.listdir(os.path.join(D, "events_yahoo"))):
        e = pd.read_csv(os.path.join(D, "events_yahoo", f), dtype=str)
        e = e[e["type"] == "split"]
        if not len(e):
            continue
        x = rd("prices_yahoo", f)
        x["date"] = pd.to_datetime(x["date"])
        x = x.set_index("date")["close"].dropna()
        for a, b in zip(e["date"], e["value"]):
            k = eval(b)
            if abs(math.log(k)) < math.log(1.4):
                continue
            a = pd.Timestamp(a)
            if a not in x.index or x.index.get_loc(a) == 0:
                continue
            n += 1
            i = x.index.get_loc(a)
            r = x.iloc[i] / x.iloc[i - 1]
            if abs(math.log(r)) > abs(math.log(k)) / 2:
                bad.append("%s %s 分割×%s" % (f[:-4], a.date(), round(k, 3)))   # 私有：不寫價格比
    return {"分割事件(|log k|≥log1.4)": n, "收盤在事件日跳超過一半分割倍數": len(bad), "清單": bad[:20]}


def check_ttm_continuity(R):
    """E：過門檻且可估值的檔，本益比點的近四季 EPS（同基礎）相鄰季比值超出 [0.4, 2.5] 的筆數；並列與分割日相近（±200 日）者。"""
    ok = R[(R["stage"] == "pop") & (R["all_pass"] == True) & (R["val"] == "ok")]  # noqa: E712
    pairs = ok[["ticker", "src"]].drop_duplicates()
    n = jumps = near_split = 0
    lst = []
    for t, src in pairs.itertuples(index=False):
        F = FQ.fund(t)
        sp, _ = FQ.split_list(t, src)
        prev = None
        for q in FQ.quarter_points():
            v, _ = F.ttm_eps(q, sp)
            if v is None or v <= 0:
                prev = None
                continue
            if prev is not None:
                n += 1
                r = v / prev
                if not (0.4 <= r <= 2.5):
                    jumps += 1
                    ns = any(abs((q - x).days) <= 200 for x, k in sp)
                    near_split += ns
                    lst.append("%s %s%s" % (t, q.date(), "（近分割）" if ns else ""))   # 私有：不寫比值
            prev = v
    return {"相鄰季點對數": n, "比值超出[0.4,2.5]": jumps, "其中近分割日": near_split, "清單": lst[:40]}


def main():
    FQ.assert_pinned()
    Dd = Data()
    out = {"資料commit": FQ.data_commit()}
    out["B_公式"] = check_formula()
    out["D_Yahoo已調分割"] = check_yahoo_adjusted()
    out["C_推得分割驗證"] = check_split_detect(Dd)
    R = pd.read_csv(os.path.join(FQ.PRIVD, "classify_by_eval_ticker.csv"), dtype={"eval": str, "ticker": str}, low_memory=False)
    out["E_近四季EPS連續性"] = check_ttm_continuity(R)
    ev = list(FQ.eval_dates())
    qpts = []
    for y in range(2015, 2027):
        for m, dd in ((3, 31), (6, 30), (9, 30), (12, 31)):
            if pd.Timestamp(y, m, dd) > Dd.cal.iloc[-1]:
                continue
            q = Dd.qpoint(y, m, dd)
            if q >= pd.Timestamp("2015-12-01"):
                qpts.append(q)
    pc = {}
    res = {}
    mism = []
    for i in CHECK_IDX:
        d = ev[i]
        ds = str(d.date())
        sub = R[R["eval"] == ds].set_index("ticker")
        cnt = {"母體": 0, "全過": 0, "可買": 0, "接近": 0, "偏貴": 0, "r_pass": [0, 0, 0, 0]}
        nmis = 0
        for t in Dd.univ["ticker"]:
            o = ind_classify(Dd, t, d, pc, qpts)
            mine_stage = "pop" if o["stage"] == "pop" else "x"
            r = sub.loc[t] if t in sub.index else None
            fq_stage = "pop" if (r is not None and r["stage"] == "pop") else "x"
            diff = []
            if mine_stage != fq_stage:
                diff.append("stage %s/%s" % (o["stage"], None if r is None else r["stage"]))
            elif mine_stage == "pop":
                cnt["母體"] += 1
                for j, k in enumerate(("r1", "r2", "r3", "r4")):
                    cnt["r_pass"][j] += o[k] == "pass"
                    if o[k] != r[k]:
                        diff.append("%s %s/%s" % (k, o[k], r[k]))
                if o.get("all_pass"):
                    cnt["全過"] += 1
                if o.get("val") == "ok":
                    cnt[o["group"]] += 1
                if (o.get("val") or "") != (r.get("val") if isinstance(r.get("val"), str) else ""):
                    diff.append("val %s/%s" % (o.get("val"), r.get("val")))
                elif o.get("val") == "ok":
                    if o["group"] != r["group"]:
                        diff.append("group %s/%s" % (o["group"], r["group"]))
                    m1, m2 = float(o["multiple"]), float(r["multiple"])
                    if np.isfinite(m1) and abs(m1 / m2 - 1) > 1e-9:
                        diff.append("multiple 相對差 %.2e" % abs(m1 / m2 - 1))
            if diff:
                nmis += 1
                mism.append("%s %s：%s" % (ds, t, "；".join(diff)))
        fq_row = {"母體": int((sub["stage"] == "pop").sum()),
                  "全過": int((sub["all_pass"] == True).sum()),  # noqa: E712
                  **{g: int(((sub["val"] == "ok") & (sub["group"] == g)).sum()) for g in FQ.GROUPS}}
        res[ds] = {"獨立": {k: (v if k != "r_pass" else [int(x) for x in v]) for k, v in cnt.items()}, "freq": fq_row,
                   "逐檔不一致": nmis}
    out["A_獨立重算"] = res
    out["A_不一致清單"] = mism[:60]
    out["A_不一致總數"] = len(mism)
    FQ.jdump(out, os.path.join(FQ.OUTD, "freq_check.json"))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
