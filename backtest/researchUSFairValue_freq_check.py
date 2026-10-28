# -*- coding: utf-8 -*-
"""美股合理價機械版——頻率表獨立查核（⛔ 不算任何報酬）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSFairValue_freq_check

A 獨立寫法重算幾個評估日的母體、四條門檻、合理價與分組（只共用常數與 CSV 路徑；讀檔、PIT、分割、財年、公式全部另寫），
  逐 (評估日, 代號) 對 freq 的私有明細檔，報不一致筆數（數值差 ≤ 1e−9 相對誤差判同）。
B 合理價公式：等比級數封閉式 vs freq.fair_value（隨機 2,000 組）＋一組手算。
C ★10 推得分割的驗證：同一偵測法套在 2016-06 之後，對事件檔（Yahoo split）召回率與精確率。
D Yahoo close 是否已調分割：每個事件日前後收盤比不應出現分割倍數的跳。
E 本益比點的近四季 EPS 連續性：相鄰季點比值超出 [0.4, 2.5] 的筆數（疑似漏調分割；只描述）。
G 裁定 seq481（資料 89d9f8550）新規則的定點查核：★19 依評估日挑 CIK（IR 2020-03-02 前＝0001466258 等）、
  ★20 多類股類別（BRK.B 2017 前 ＝ Class A ÷ 1500、HSY 永不用 Class B、6 檔只用指定類別）、★21 補值開關、V 4:1 分割推得、
  其餘檔主檔列與原檔逐列相同。A 的獨立重算也照 ★19～★21 另寫一次（不呼叫 freq 的函式）。
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


# ★20（另寫）：代號 ⇒ [(類別, period_end 下限, 上限（不含）, EPS 乘數)]；同一檔無日期限者同一級
PICK = {"V": [("CommonClassAMember", None, None, 1.0)], "STZ": [("CommonClassAMember", None, None, 1.0)],
        "GOOGL": [("CommonClassAMember", None, None, 1.0)], "GOOG": [("CapitalClassCMember", None, None, 1.0)],
        "HSY": [("CommonStockMember", None, None, 1.0), ("HersheyCommonStockMember", None, None, 1.0)],
        "BRK.B": [("EquivalentClassBMember", "2017-01-01", None, 1.0), ("CommonClassAMember", None, "2017-01-01", 1 / 1500.0)]}


def class_rows(fname, is_eps):
    c = rd("fundamentals", fname, dtype=str, keep_default_na=False)
    parts = []
    for t, rules in PICK.items():
        for j, (cl, lo, hi, k) in enumerate(rules):
            x = c[(c["ticker"] == t) & (c["share_class"] == cl)].copy()
            if lo:
                x = x[x["period_end"] >= lo]
            if hi:
                x = x[x["period_end"] < hi]
            mul = k if is_eps else 1.0 / k
            x["v"] = x["value"].astype(float) * mul
            if "latest_value" in x:
                x["lv"] = pd.to_numeric(x["latest_value"], errors="coerce") * mul
            x["prio"] = 0 if not (lo or hi) else j
            parts.append(x)
    x = pd.concat(parts, ignore_index=True)
    x["pe"] = pd.to_datetime(x["period_end"])
    # 同級兩標籤同季相差 > 2% ⇒ 兩列都丟
    bad = set()
    for t, g in x[x["prio"] == 0].groupby("ticker"):
        for i, a in g.iterrows():
            for j2, b in g.iterrows():
                if j2 <= i or a["share_class"] == b["share_class"] or abs((a["pe"] - b["pe"]).days) > 5:
                    continue
                if (b["v"] == 0 and a["v"] != 0) or (b["v"] != 0 and abs(a["v"] / b["v"] - 1) > 0.02):
                    bad.update([i, j2])
    return x.drop(index=list(bad))


class Data:
    def __init__(self):
        g = rd("macro", "yahoo_GSPC.csv", usecols=["date"])
        self.cal = pd.to_datetime(g["date"]).sort_values().reset_index(drop=True)
        self.fund = {}
        for f in ("net_income", "eps_diluted", "diluted_shares", "dps", "equity", "equity_incl_nci", "operating_income", "cfo"):
            q = rd("fundamentals", "quarterly_%s.csv" % f, dtype=str)
            cols = ["ticker", "cik", "period_start", "period_end", "value", "first_filed", "first_form", "tag", "derived"]
            q = q.loc[q["index"].isin(["sp500", "both"]), cols].copy()
            q["v"] = q["value"].astype(float)
            q["prio"] = q["ticker"].map(lambda t: 9 if t in PICK else 0)
            if f in ("eps_diluted", "diluted_shares"):
                c = class_rows("quarterly_%s_class.csv" % f, f == "eps_diluted")
                q = pd.concat([q, c[cols + ["v", "prio"]]], ignore_index=True)
            q["pe"] = pd.to_datetime(q["period_end"])
            q["ps"] = pd.to_datetime(q["period_start"], errors="coerce")
            q["ff"] = pd.to_datetime(q["first_filed"])
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
        ds["v"] = ds["value"].astype(float); ds["lv"] = ds["latest_value"].astype(float)
        ds["pe"] = pd.to_datetime(ds["period_end"])
        dc = class_rows("quarterly_diluted_shares_class.csv", False)
        keep = []
        for t, g in ds.groupby("ticker"):            # 6 檔：主檔只補類別沒有的季
            if t in PICK:
                cp = dc.loc[dc["ticker"] == t, "pe"]
                g = g[[not ((cp - x).abs() <= pd.Timedelta(days=5)).any() for x in g["pe"]]]
            keep.append(g)
        ds = pd.concat(keep + [dc[[c for c in ds.columns if c in dc.columns]]], ignore_index=True)
        ds["ff"] = pd.to_datetime(ds["first_filed"]); ds["lf"] = pd.to_datetime(ds["latest_filed"])
        self.ds_full = ds
        self.univ = rd("membership", "universe.csv", dtype=str, keep_default_na=False)
        rm = rd("membership", "renames_manual.csv", dtype=str, keep_default_na=False)
        self.until = {o: pd.Timestamp(u) for o, u in zip(rm["old"], rm["until"]) if u}
        cm = rd("fundamentals", "cik_map.csv", dtype=str, keep_default_na=False)
        self.seg = {}
        for t, g in cm.groupby("ticker"):
            if len(g) > 1 and ((g["seg_from"] != "") | (g["seg_to"] != "")).any():
                self.seg[t] = list(zip(g["cik"], g["seg_from"], g["seg_to"]))
        cp = rd("fundamentals", "cik_predecessor.csv", dtype=str, keep_default_na=False)
        cp = cp[(cp["verdict"] == "ok") & (cp["pred_cik"] != "")]
        self.pred = {}
        for a, b in zip(cp["cik_now"], cp["pred_cik"]):
            self.pred.setdefault(a, set()).add(b)
        self.fill_ok = {}
        for t in PICK:                                 # ★21 另寫
            E, S_, N = (self.fund[f][self.fund[f]["ticker"] == t] for f in ("eps_diluted", "diluted_shares", "net_income"))
            E = E[E["prio"] < 9].sort_values(["prio", "ff"]).drop_duplicates("pe")
            E = E[E["der"] == 0]
            S_ = S_[S_["prio"] < 9].sort_values(["prio", "ff"]).drop_duplicates("pe")
            N = N.sort_values("ff").drop_duplicates("pe")
            rr = []
            for pe, ev in zip(E["pe"], E["v"]):
                a = S_[(S_["pe"] - pe).abs() <= pd.Timedelta(days=5)]
                b = N[(N["pe"] - pe).abs() <= pd.Timedelta(days=5)]
                if len(a) and len(b) and ev and a["v"].iloc[0] > 0:
                    rr.append(b["v"].iloc[0] / a["v"].iloc[0] / ev)
            self.fill_ok[t] = bool(rr) and abs(float(np.median(rr)) - 1) <= 0.02

    def cik_of(self, t, d):
        """★19 另寫：→ (允許的 CIK 集合或 None, ok)。"""
        if t not in self.seg:
            return None, True
        for ck, a, b in self.seg[t]:
            if (not a or pd.Timestamp(a) <= d) and (not b or d < pd.Timestamp(b)):
                return {ck} | self.pred.get(ck, set()), True
        return None, False

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


def detect(Dd, t, ciks=None):
    """另寫一次 ★10：相鄰兩份申報（依 first_filed、period_end 排序）股數跳點 ＋ 早期列被重編同比。"""
    G = Dd.ds_full[Dd.ds_full["ticker"] == t]
    if ciks is not None:
        G = G[G["cik"].isin(ciks)]
    G = G.sort_values(["ff", "pe"]).reset_index(drop=True)
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


def splits_for(Dd, t, src, ciks=None):
    s, ev = price(src)
    p0 = s.index.min()
    out = list(ev)
    for dte, k, prev in detect(Dd, t, ciks):
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
    ciks, okc = Dd.cik_of(t, d)
    if not okc:
        return {"stage": "fund_mismatch"}
    if ciks is None and t in Dd.until and d <= Dd.until[t]:
        return {"stage": "fund_mismatch"}
    src = pn.loc[d, "src"].rstrip("*")
    cl, _ = price(src)
    if d not in cl.index:
        return {"stage": "no_close"}
    sp = splits_for(Dd, t, src, ciks)
    so = Dd.so[(Dd.so["ticker"] == t) & (Dd.so["fd"] < d)]
    if ciks is not None:
        so = so[so["cik"].isin(ciks)]
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
    FT = {}
    for f, q in Dd.fund.items():
        q = q[q["ticker"] == t]
        FT[f] = q[q["cik"].isin(ciks)] if ciks is not None else q
    F = {f: q[q["ff"] < d] for f, q in FT.items()}
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
    allni = FT["net_income"].set_index("pe")

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
        return None if not len(x) else x.sort_values(["prio", "ff"], kind="stable").iloc[0]

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
        e = F["eps_diluted"] if asof == d else FT["eps_diluted"][FT["eps_diluted"]["ff"] < asof]
        n_ = F["net_income"] if asof == d else FT["net_income"][FT["net_income"]["ff"] < asof]
        s_ = F["diluted_shares"] if asof == d else FT["diluted_shares"][FT["diluted_shares"]["ff"] < asof]
        pick = lambda q: (lambda x: None if not len(x) else x.sort_values(["prio", "ff"], kind="stable").iloc[0])(q[(q["pe"] - pe).abs() <= pd.Timedelta(days=5)])
        r = pick(e)
        if r is not None and r["der"] in (0, 1):
            return r["v"] / fac(sp, r["ff"])
        a, b = pick(n_), (pick(s_) if Dd.fill_ok.get(t, True) else None)
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

    grid_src = pd.concat([FT["net_income"]["pe"], FT["eps_diluted"]["pe"]]).drop_duplicates().sort_values()
    grid = []
    for x in grid_src:
        if not grid or (x - grid[-1]).days > 5:
            grid.append(x)

    def ttm(asof):
        cands = []
        for f in ("net_income", "eps_diluted"):
            q = FT[f]
            q = q[q["ff"] < asof]
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
    ok = ok.assign(cik=ok["cik"] if "cik" in ok else None)
    pairs = ok[["ticker", "src", "cik"]].drop_duplicates()
    n = jumps = near_split = 0
    lst = []
    for t, src, ck in pairs.itertuples(index=False):
        ck = ck if isinstance(ck, str) else None
        F = FQ.fund(t, ck)
        sp, _ = FQ.split_list(t, src, ck)
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


def check_seq481(Dd, R):
    """G：裁定 seq481 新規則定點查核。→ dict（每項 ok／筆數）。"""
    out = {}
    cik = R.dropna(subset=["cik"]) if "cik" in R else R.iloc[0:0]
    ir = cik[cik["ticker"] == "IR"]
    pre = ir[pd.to_datetime(ir["eval"]) < pd.Timestamp("2020-03-02")]
    post = ir[pd.to_datetime(ir["eval"]) >= pd.Timestamp("2020-03-02")]
    out["G1_IR_2020-03-02前用0001466258"] = {"筆": int(len(pre)), "ok": bool(len(pre) > 0 and (pre["cik"] == "0001466258").all())}
    out["G1_IR_之後用0001699150"] = {"筆": int(len(post)), "ok": bool(len(post) > 0 and (post["cik"] == "0001699150").all())}
    out["G1_IR不再判財報對不上"] = {"ok": bool(not (R.loc[R["ticker"] == "IR", "stage"] == "fund_mismatch").any())}
    for t, ck0, cut in (("DD", "0001666700", "2017-09-01"), ("BHGE", "0001701605", "2017-07-03"), ("FTI", "0001681459", "2017-01-17")):
        x = cik[cik["ticker"] == t]
        out["G1_%s_評估日全在%s後用%s" % (t, cut, ck0)] = {"筆": int(len(x)), "ok": bool((x["cik"] == ck0).all())}
    # 另寫的 cik_of 與 freq 明細一致（全部分段代號、全部評估日）
    mis = []
    for t, d, ck in cik[["ticker", "eval", "cik"]].itertuples(index=False):
        s_, _ = Dd.cik_of(t, pd.Timestamp(d))
        if s_ is None or ck not in s_:
            mis.append("%s %s" % (t, d))
    out["G1_另寫cik_of與freq一致"] = {"筆": int(len(cik)), "不一致": mis[:20], "ok": not mis}
    f_old = FQ.fund("IR", "0001466258")
    f_new = FQ.fund("IR", "0001699150")
    out["G1_IR財報物件CIK純度"] = {"ok": all(g is None or set(g["cik"]) <= {"0001466258"} for g in f_old.F.values())
                               and all(g is None or set(g["cik"]) <= {"0001699150"} for g in f_new.F.values())}
    # G2 BRK.B：2017 前 ＝ Class A ÷ 1500；2017 起只 EquivalentClassBMember
    raw = rd("fundamentals", "quarterly_eps_diluted_class.csv", dtype=str, keep_default_na=False)
    ra = raw[(raw["ticker"] == "BRK.B") & (raw["share_class"] == "CommonClassAMember") & (raw["period_end"] < "2017-01-01")]
    fe = FQ.field("eps_diluted")["BRK.B"]
    fc = fe[fe["prio"] < FQ.PRIO_MAIN]
    pre17 = fc[fc["period_end"] < pd.Timestamp("2017-01-01")]
    m = pre17.merge(ra.assign(period_end=pd.to_datetime(ra["period_end"]), first_filed=pd.to_datetime(ra["first_filed"]),
                              a=ra["value"].astype(float))[["period_end", "first_filed", "a"]], on=["period_end", "first_filed"])
    out["G2_BRK.B_2017前=A÷1500"] = {"列": int(len(pre17)), "對到原A列": int(len(m)),
                                   "ok": bool(len(pre17) > 0 and len(m) == len(pre17) and np.allclose(m["value"], m["a"] / 1500.0)
                                              and set(pre17["cls"]) == {"CommonClassAMember/1500"})}
    post17 = fc[fc["period_end"] >= pd.Timestamp("2017-01-01")]
    out["G2_BRK.B_2017起只EquivalentClassB"] = {"列": int(len(post17)), "ok": bool(len(post17) > 0 and set(post17["cls"]) == {"EquivalentClassBMember"})}
    fs = FQ.field("diluted_shares")["BRK.B"]
    fs = fs[(fs["prio"] < FQ.PRIO_MAIN) & (fs["period_end"] < pd.Timestamp("2017-01-01"))]
    rs = rd("fundamentals", "quarterly_diluted_shares_class.csv", dtype=str, keep_default_na=False)
    rs = rs[(rs["ticker"] == "BRK.B") & (rs["share_class"] == "CommonClassAMember") & (rs["period_end"] < "2017-01-01")]
    m2 = fs.merge(rs.assign(period_end=pd.to_datetime(rs["period_end"]), first_filed=pd.to_datetime(rs["first_filed"]),
                            a=rs["value"].astype(float))[["period_end", "first_filed", "a"]], on=["period_end", "first_filed"])
    out["G2_BRK.B_2017前股數=A×1500"] = {"列": int(len(fs)), "ok": bool(len(m2) == len(fs) and np.allclose(m2["value"], m2["a"] * 1500.0))}
    # G3 6 檔只用指定類別；HSY 永不 Class B；未裁定的檔不讀類別檔
    allowed = {t: {cl if k == 1.0 else cl + "/1500" for cl, _, _, k in v} for t, v in PICK.items()}
    bad = []
    for f in ("eps_diluted", "diluted_shares"):
        for t in PICK:
            g = FQ.field(f).get(t)
            if g is None:
                continue
            used = set(g.loc[g["prio"] < FQ.PRIO_MAIN, "cls"])
            if not used <= allowed[t]:
                bad.append("%s %s %s" % (f, t, sorted(used - allowed[t])))
    out["G3_6檔只用指定類別"] = {"ok": not bad, "違反": bad}
    hsyb = [f for f in ("eps_diluted", "diluted_shares") if FQ.field(f)["HSY"]["cls"].str.contains("ClassB").any()]
    out["G3_HSY永不用ClassB"] = {"ok": not hsyb, "違反": hsyb}
    others = set(rd("fundamentals", "quarterly_eps_diluted_class.csv", dtype=str)["ticker"]) - set(PICK)
    leak = [t for t in others for f in ("eps_diluted", "diluted_shares")
            if FQ.field(f).get(t) is not None and (FQ.field(f)[t]["cls"] != "").any()]
    out["G3_未裁定類別的檔不讀類別檔"] = {"ok": not leak, "違反": leak}
    conf = [k for k in FQ._CLASS_LOG if k.startswith("conflict_eps_diluted_HSY")]
    hs = FQ.field("eps_diluted")["HSY"]
    out["G3_HSY衝突季兩列都丟"] = {"衝突": sorted(FQ._CLASS_LOG), "ok": all(
        not ((hs["period_end"] == pd.Timestamp(k.rsplit("_", 1)[1])) & (hs["prio"] < FQ.PRIO_MAIN)).any() for k in conf)}
    # G4 ★21 開關：freq 與另寫一致
    out["G4_淨利÷股數補值開關"] = {"freq": {t: FQ.class_fill_ok(t)[0] for t in PICK}, "另寫": dict(Dd.fill_ok),
                              "ok": all(FQ.class_fill_ok(t)[0] == Dd.fill_ok[t] for t in PICK)}
    # G5 V 4:1 分割（2015-03）由 ★10 推得
    vs = FQ.detect_splits("V")
    out["G5_V_4:1推得"] = {"推得": [(str(a.date()), k) for a, k, _ in vs],
                         "ok": any(abs(k - 4.0) < 1e-9 and pd.Timestamp("2015-03-01") <= a <= pd.Timestamp("2015-06-30") for a, k, _ in vs)}
    # G6 其餘檔：freq 主檔列與原檔列數一致、prio 全 0、無類別
    bad6 = []
    for f in ("eps_diluted", "diluted_shares", "net_income"):
        q = rd("fundamentals", "quarterly_%s.csv" % f, dtype=str)
        q = q[q["index"] != "sp400"]
        cnt = q.groupby("ticker").size()
        fd = FQ.field(f)
        for t, n in cnt.items():
            if t in PICK:
                continue
            g = fd.get(t)
            if g is None or len(g) != n or (g["prio"] != 0).any() or (g["cls"] != "").any():
                bad6.append("%s %s" % (f, t))
    out["G6_非6檔主檔列不變"] = {"ok": not bad6, "違反": bad6[:20]}
    out["G_全部通過"] = all(v.get("ok", True) for v in out.values() if isinstance(v, dict))
    return out


def main():
    FQ.assert_pinned()
    Dd = Data()
    out = {"資料commit": FQ.data_commit()}
    out["B_公式"] = check_formula()
    out["D_Yahoo已調分割"] = check_yahoo_adjusted()
    out["C_推得分割驗證"] = check_split_detect(Dd)
    R = pd.read_csv(os.path.join(FQ.PRIVD, "classify_by_eval_ticker.csv"), dtype={"eval": str, "ticker": str, "cik": str}, low_memory=False)
    out["E_近四季EPS連續性"] = check_ttm_continuity(R)
    out["G_seq481新規則"] = check_seq481(Dd, R)
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
