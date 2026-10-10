# -*- coding: utf-8 -*-
"""PREREG急跌錯殺 seq1 —— 抽樣獨立查核（回測線計算子代理）。
⭐ 獨立寫法：⛔ 不 import researchCrashOversold、researchRevLimitUp、researchBARR、researchIndRev_prereg、research34、data.load_stock（價格）；
   直接讀 csv 自己算還原價、amt20、R1、產業、r10、同產業中位、最低 2%、壞根、重大訊息、月營收、季報、出場。
   共用（照報）：universe_gate（gate3、pit_valid 閘）、data.breakpoints／applies（斷點定義）；壞根另拿正式引擎 research11.load_bars 當對照。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchCrashOversold_check [--days 12] [--edays 6] [--n 80] [--procs 4]

查：① 壞根：自己寫的壞根（幽靈事件 ∪ 缺口 ≥ 5 ∪ applies 斷點）對 research11.load_bars（≥ 260 根的股票全部）
    ② R1 的 X（2016-01-04）
    ③ 抽 days＋edays 個交易日：當天母體、r10、同產業中位、ex、最低 2% 名單 ⇒ 對 bottom2.csv.gz
    ④ 全部事件：同檔 20 日去重（由 bottom2 的 r10＜0 列重算）、公司事件旗標、F1、F2（main）⇒ 對 events.csv.gz
    ⑤ 抽 n 筆事件：X1a（修復／營收轉壞）、X1b（＋EPS 轉壞）、X2（回落 20%）的出場種類、位置、原因（含壞根前收盤強制出）
輸出 backtest/resultsCrashOversold/check.json
事後註：第一次跑 F2 有 14 筆不同，全是查核程式自己的錯（2015-05-15 第一季可用日之前，季索引 −1 繞到最後一季）；修查核程式後重跑，主程式未改。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402  只用 breakpoints／applies 與 load_bars 對照
from backtest import universe_gate as UG                    # noqa: E402
from backtest import research11 as R                        # noqa: E402

UG.set_gate_v2(True)
H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsCrashOversold")
KW = ["訴訟", "起訴", "搜索", "檢調", "退票", "扣押", "強制執行", "駭客", "資安", "撤銷", "停工", "火災", "裁罰", "變更交易", "全額交割", "重編", "保留意見", "繼續經營"]
FB_MAP = {"金融業": "金融保險", "證券": "金融保險", "金融保險業": "金融保險", "建材營建": "建材營造", "生物科技": "生技醫療業", "農業科技": "農業科技業",
          "通訊網路": "通信網路業", "軟體": "資訊服務業"}
FB_NONE = {"管理股票", "之合計數", "電子(二)", "塑化紡織(二)", "水泥窯製營造", ""}
DEAD = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}
_G: dict = {}


def tw_dir():
    ds = sorted(glob.glob(os.path.expanduser("~/crashwork/tw_*/data")))
    assert len(ds) == 1, ds
    return ds[0]


def calendar(DATA):
    return pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(DATA, "meta", "calendar_twse.csv"))["date"])).sort_values()


def okcode(s):
    return isinstance(s, str) and len(s) == 4 and s.isdigit() and s[0] in "123456789" and not s.startswith("91")


def stock_job(args):
    sid, mk = args
    DATA, cal = _G["DATA"], _G["cal"]; n = len(cal)
    p = os.path.join(DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return sid, None
    raw = pd.read_csv(p, dtype=str).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.sort_index()
    num = {k: pd.to_numeric(raw[k], errors="coerce") for k in ("open", "high", "low", "close", "volume", "amount")}
    badp = (num["open"] <= 0) | (num["high"] <= 0) | (num["low"] <= 0) | (num["close"] <= 0)
    for k in ("open", "high", "low", "close"):
        num[k] = num[k].where(~badp)
    ap = os.path.join(DATA, "adj", f"{sid}.csv")
    adj = pd.read_csv(ap, dtype={"date": str}).sort_values("date") if os.path.exists(ap) else None
    F = np.ones(len(raw))
    if adj is not None and len(adj):
        ad = pd.to_datetime(adj["date"]).to_numpy(); cf = adj["cum_factor"].astype(float).to_numpy()
        j = np.searchsorted(ad, raw.index.to_numpy(), side="right"); m = j < len(ad)
        F[m] = cf[j[m]]
    df = pd.DataFrame({k: (num[k] * F if k in ("open", "high", "low", "close") else num[k]) for k in num}, index=raw.index).reindex(cal)
    rc = num["close"].reindex(cal).to_numpy(float)
    c0 = df["close"].to_numpy(float); o = df["open"].to_numpy(float); bar = np.isfinite(c0)
    idx = np.flatnonzero(bar)
    if len(idx) < 2:
        return sid, None
    amt = df["amount"].to_numpy(float)
    a20 = np.full(n, np.nan); a20[idx] = pd.Series(amt[idx]).rolling(20, min_periods=20).mean().to_numpy()
    # 壞根（自己寫）：幽靈事件、缺口 ≥ 5、applies 斷點；另 adj 減資／面額
    dates = cal[idx]; nb = len(idx); bad = np.zeros(nb, bool)
    rcv = rc[idx]
    ev = set()
    rd = []
    if adj is not None and len(adj):
        for d, f, e in zip(pd.to_datetime(adj["date"]), adj["factor"].astype(float), adj["event"].astype(str) if "event" in adj else [""] * len(adj)):
            ev.add(d)
            k = int(np.searchsorted(dates, d))
            if k < nb and k > 0 and np.isfinite(rcv[k]) and np.isfinite(rcv[k - 1]) and f > 0:
                r = rcv[k] / (rcv[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    bad[k] = True
            if e in ("reduce", "parvalue"):
                kk = int(cal.searchsorted(d))
                if kk < n:
                    rd.append(kk)
    bad[1:] |= (np.diff(idx) - 1) >= 5
    dfb = pd.DataFrame({"close": c0, "volume": df["volume"].to_numpy(float)}, index=cal)
    for b in D.breakpoints(dfb, ev):
        if D.applies(b):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < nb:
                bad[k] = True
    mybad = set(idx[bad].tolist())
    # 對照：research11.load_bars
    D.DATA = DATA
    lb = None
    B = R.load_bars(sid, mk, cal)
    if B is not None:
        nbad = B["next_bad"]; kk = np.flatnonzero(nbad[:len(B["idx"])] == np.arange(len(B["idx"])))
        lb = set(B["idx"][kk].tolist())
    BAD = np.zeros(n, bool); BAD[list(mybad | set(rd))] = True
    pv = np.asarray(UG.pit_valid(sid, cal, DATA), bool)
    mkt = raw["market"].reindex(cal).ffill().fillna("").to_numpy() if "market" in raw else np.full(n, "")
    c = pd.Series(c0).ffill().to_numpy(float)
    return sid, {"c": c.astype(np.float64), "o": o, "bar": bar, "a20": a20, "BAD": BAD, "pv": pv, "lbdiff": None if lb is None else len(lb ^ mybad), "nlb": None if lb is None else len(lb)}


def load_layout(DATA, procs):
    cal = calendar(DATA)
    st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(st); U = U[U["stock_id"].map(okcode)]
    _G.update(DATA=DATA, cal=cal)
    out = {}
    with Pool(procs) as pool:
        for sid, v in pool.imap_unordered(stock_job, list(zip(U["stock_id"], U["market"])), chunksize=8):
            if v is not None:
                out[sid] = v
    return cal, out


def ind_tools(TW):
    p = pd.read_csv(os.path.join(TW, "meta", "industry_hist", "industry_pit.csv"), dtype=str)
    seg = {}
    for sid, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
        a_ = pd.Timestamp(a) if isinstance(a, str) and a else pd.Timestamp.min
        b_ = pd.Timestamp(b) if isinstance(b, str) and b else pd.Timestamp.max
        seg.setdefault(sid, []).append((a_, b_, ind))
    for k in seg:
        seg[k].sort(key=lambda z: z[0])
    fs = sorted(glob.glob(os.path.join(TW, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(TW, "mops", "revenue_hist", "*.csv")))
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "產業別", "當月營收", "去年當月營收"]) for f in fs], ignore_index=True)
    rv["產業別"] = rv["產業別"].fillna("")
    rv["_old"] = rv["產業別"].isin({"電子工業", "化學生技醫療"})
    cat = rv.sort_values(["stock_id", "period", "_old"], kind="stable").drop_duplicates(["stock_id", "period"], keep="first")
    fb = {}
    for sid, g in cat.groupby("stock_id"):
        fb[sid] = (g["period"].tolist(), [None if c in FB_NONE else FB_MAP.get(c, c) for c in g["產業別"]])
    val = rv.drop_duplicates(["stock_id", "period"], keep="last")
    REV = {(s, p_): (pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")) for s, p_, a, b in zip(val["stock_id"], val["period"], val["當月營收"], val["去年當月營收"])}
    periods = sorted(val["period"].unique())

    def mshift(m, k):
        y, mm = int(m[:4]), int(m[5:]); t = y * 12 + mm - 1 + k
        return f"{t // 12:04d}-{t % 12 + 1:02d}"

    def ind_at(sid, d):
        if sid in seg:
            sg = seg[sid]
            for a, b, ind in sg:
                if a <= d <= b:
                    return ind
            if d > sg[-1][1]:
                return sg[-1][2]
            if d < sg[0][0]:
                return sg[0][2]
            return [z for z in sg if z[1] < d][-1][2]
        if sid in fb:
            pers, cats = fb[sid]
            lim = mshift(f"{d.year:04d}-{d.month:02d}", -1 if d.day > 10 else -2)
            k = int(np.searchsorted(np.array(pers), lim, side="right")) - 1
            if k >= 0:
                return cats[k]
        return None
    return ind_at, REV, periods, mshift


def month_first(cal, d):
    m = cal[d].strftime("%Y-%m")
    k = d
    while k > 0 and cal[k - 1].strftime("%Y-%m") == m:
        k -= 1
    return cal[k]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=12); ap.add_argument("--edays", type=int, default=6)
    ap.add_argument("--n", type=int, default=80); ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    t0 = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    TW = tw_dir()
    ind_at, REV, periods, mshift = ind_tools(TW)
    EV = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str})
    B2 = pd.read_csv(os.path.join(OUT, "bottom2.csv.gz"), dtype={"sid": str})
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    rng = np.random.default_rng(20261011)
    res = {"執行時間": t0 + "（台北）", "寫法": "獨立（見檔頭）"}
    total = 0
    L = {}
    for part, DATA in (("main", H2D), ("早年", EOTC)):
        cal, ST = load_layout(DATA, a.procs)
        sids = sorted(ST); n = len(cal)
        lbd = [v["lbdiff"] for v in ST.values() if v["lbdiff"] is not None]
        res.setdefault("① 壞根對 load_bars", {})[part] = {"比對檔數（≥260 根）": len(lbd), "不同（股-日，對稱差合計）": int(sum(lbd)),
                                                        "load_bars 壞根合計": int(sum(v["nlb"] for v in ST.values() if v["nlb"] is not None))}
        total += int(sum(lbd))
        L[part] = (cal, ST, sids)
    # ② X
    cal, ST, sids = L["main"]
    d16 = int(cal.searchsorted(pd.Timestamp("2016-01-04")))
    fin = np.array([ind_at(s, month_first(cal, d16)) == "金融保險" for s in sids])
    mk = np.array([ST[s]["bar"][d16] and ST[s]["pv"][d16] and np.isfinite(ST[s]["a20"][d16]) for s in sids]) & ~fin
    nu = int((mk & np.array([ST[s]["a20"][d16] >= 5e7 if np.isfinite(ST[s]["a20"][d16]) else False for s in sids])).sum()); nm = int(mk.sum())
    X = nu / nm
    res["② X"] = {"獨立": [nu, nm, X], "主程式": S["meta"]["R1"], "相同": bool(abs(X - S["meta"]["R1"]["X"]) < 1e-15)}
    total += int(not res["② X"]["相同"])
    # ③ 抽樣日
    out3 = []
    for part, k_ in (("main", a.days), ("早年", a.edays)):
        cal, ST, sids = L[part]; n = len(cal)
        bd = B2[B2["版面"] == part]
        lo = int(cal.searchsorted(pd.Timestamp("2005-01-03" if part == "早年" else "2015-06-01")))
        days = sorted(rng.choice(np.arange(max(lo, 80), n - 1), size=k_, replace=False).tolist())
        for d in days:
            mf = month_first(cal, d)
            rows = []
            for s in sids:
                v = ST[s]
                if not (v["bar"][d] and v["pv"][d] and np.isfinite(v["a20"][d])):
                    continue
                ind = ind_at(s, mf)
                if ind == "金融保險":
                    continue
                rows.append((s, v["a20"][d], ind))
            SP = {s_: i_ for i_, s_ in enumerate(sids)}
            rows.sort(key=lambda z: (-z[1], SP[z[0]]))
            kk = int(np.ceil(X * len(rows)))
            R1 = rows[:kk]
            U = []
            for s, _, ind in R1:
                v = ST[s]
                if not (v["bar"][d] and v["bar"][d - 10]) or v["BAD"][d - 9:d + 1].any():
                    continue
                U.append((s, v["c"][d] / v["c"][d - 10] - 1, ind))
            if len(U) < 20:
                continue
            vals = np.array([u[1] for u in U])
            groups = {}
            for i_, u in enumerate(U):
                groups.setdefault(u[2], []).append(i_)
            mall = float(np.median(vals))
            ind10 = np.array([float(np.median(vals[groups[u[2]]])) if (u[2] is not None and len(groups[u[2]]) >= 5) else mall for u in U])
            ex = vals - ind10
            k2 = int(np.ceil(0.02 * len(U)))
            o = np.argsort(ex, kind="stable")[:k2]
            mine = {U[i][0]: ex[i] for i in o}
            th = bd[bd["t"] == d]
            theirs = dict(zip(th["sid"], th["ex"]))
            diff = len(set(mine) ^ set(theirs)) + sum(1 for s in mine if s in theirs and abs(mine[s] - theirs[s]) > 1e-6)
            out3.append({"版面": part, "日": str(cal[d].date()), "R1 檔數": len(R1), "r10 可算": len(U), "k": k2, "不同": int(diff)})
            total += int(diff)
    res["③ 抽樣日最低 2%"] = out3
    # ④ 去重、公司事件、F1、F2（全部事件）
    out4 = {}
    NWf = sorted(glob.glob(os.path.join(TW, "mops", "news", "*.csv")))
    NW = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in NWf if re.fullmatch(r"\d{4}\.csv", os.path.basename(f)) and int(os.path.basename(f)[:4]) >= 2004],
                   ignore_index=True).drop_duplicates(["date", "time", "stock_id", "serial"])
    NW = NW[[any(k in s for k in KW) for s in NW["subject"]]]
    # 季報（自己讀）
    QQ = {}
    for f in sorted(glob.glob(os.path.join(TW, "mops", "fs_hist", "*_ci_*.csv"))):
        m = re.fullmatch(r"(\d{4})Q([1-4])_ci_(twse|tpex)\.csv", os.path.basename(f))
        if not m:
            continue
        x = pd.read_csv(f, dtype=str, keep_default_na=False)
        ec = [c for c in x.columns if c.startswith("基本每股盈餘")][0]
        qi = int(m[1]) * 4 + int(m[2]) - 1
        g = lambda c: pd.to_numeric(x[c].str.replace(",", "").str.strip(), errors="coerce") if c in x else pd.Series(np.nan, index=x.index)
        for s, e_, r_, p_ in zip(x["stock_id"].str.strip(), g(ec), g("營業收入"), g("營業毛利（毛損）")):
            QQ.setdefault((s, qi), (e_, r_, p_))

    def qsingle(s, qi):
        cur = QQ.get((s, qi))
        if cur is None:
            return np.nan, np.nan
        if qi % 4 == 0:
            e_, r_, p_ = cur
        else:
            pr = QQ.get((s, qi - 1))
            if pr is None:
                return np.nan, np.nan
            e_, r_, p_ = cur[0] - pr[0], cur[1] - pr[1], cur[2] - pr[2]
        gm = p_ / r_ if (np.isfinite(r_) and r_ > 0 and np.isfinite(p_)) else np.nan
        return e_, gm

    def yoy(s, M):
        v = REV.get((s, M))
        if v is None or not (np.isfinite(v[0]) and np.isfinite(v[1]) and v[1] > 0):
            return np.nan
        return v[0] / v[1] - 1

    def yoy3(s, M):
        a_ = b_ = 0.0
        for k in range(3):
            v = REV.get((s, mshift(M, -k)))
            if v is None or not (np.isfinite(v[0]) and np.isfinite(v[1]) and v[1] > 0):
                return np.nan
            a_ += v[0]; b_ += v[1]
        return a_ / b_ - 1

    for part in ("main", "早年"):
        cal, ST, sids = L[part]; n = len(cal)
        E = EV[EV["版面"] == part]
        bd = B2[(B2["版面"] == part) & (B2["r10"] < 0)].sort_values(["sid", "t"])
        keep = set()
        for s, g in bd.groupby("sid"):
            last = -10 ** 9
            for t in g["t"]:
                if t - last > 20:
                    keep.add((s, int(t))); last = t
        keep = {x for x in keep if x[1] + 1 < n}
        mine = set(zip(E["sid"], E["t"].astype(int)))
        dd = len(keep ^ mine)
        # 公司事件
        calv = cal.values
        dt = pd.to_datetime(NW["date"]).values
        p0 = np.searchsorted(calv, dt, side="left")
        istd = (p0 < n) & (calv[np.minimum(p0, n - 1)] == dt)
        late = NW["time"].str.slice(0, 5).to_numpy() > "13:30"
        ep = np.where(istd & ~late, p0, np.where(istd, p0 + 1, p0))
        NP = {}
        for s, p_ in zip(NW["stock_id"].str.strip(), ep):
            NP.setdefault(s, []).append(int(p_))
        nd = 0
        for s, t, f in zip(E["sid"], E["t"].astype(int), E["公司事件"]):
            mineF = any(t - 10 <= p_ <= t for p_ in NP.get(s, []))
            nd += int(mineF != bool(f))
        # 月營收可用日
        av = []
        for M in periods:
            y, m = int(M[:4]), int(M[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            j = int(cal.searchsorted(pd.Timestamp(y2, m2, 10 if M <= "2025-12" else 15), side="right"))
            if 0 < j < n:
                av.append((j, M))
        avP = np.array([x[0] for x in av]); avM = [x[1] for x in av]
        qav = []
        for qi in range(2015 * 4, 2026 * 4 + 4):
            y, q = qi // 4, qi % 4 + 1; dy, mo, d_ = DEAD[q]
            j = int(cal.searchsorted(pd.Timestamp(y + dy, mo, d_), side="right"))
            if j < n:
                qav.append((j, qi))
        qP = np.array([x[0] for x in qav]); qQ = [x[1] for x in qav]
        n1 = n2 = 0
        for s, t, f1, f2 in zip(E["sid"], E["t"].astype(int), E["F1"], E["F2"]):
            k = int(np.searchsorted(avP, t, side="right")) - 1
            M = avM[k] if k >= 0 else None
            y1, y3 = (yoy(s, M), yoy3(s, M)) if M else (np.nan, np.nan)
            F1 = 0.0 if ((np.isfinite(y1) and y1 <= 0) or (np.isfinite(y3) and y3 <= 0)) else (1.0 if (np.isfinite(y1) and np.isfinite(y3)) else np.nan)
            n1 += int(not ((np.isnan(F1) and np.isnan(f1)) or F1 == f1))
            if part == "main":
                kq = int(np.searchsorted(qP, t, side="right")) - 1; qs = qQ[kq] if kq >= 0 else -999
                eps, gm = qsingle(s, qs); gm4 = qsingle(s, qs - 4)[1]
                ci = (s, qs) in QQ
                if F1 == 0.0 or (ci and ((np.isfinite(eps) and eps <= 0) or (np.isfinite(gm) and np.isfinite(gm4) and gm < gm4))):
                    F2 = 0.0
                elif F1 == 1.0 and ci and np.isfinite(eps) and np.isfinite(gm) and np.isfinite(gm4):
                    F2 = 1.0
                else:
                    F2 = np.nan
                bad2 = not ((np.isnan(F2) and np.isnan(f2)) or F2 == f2)
                n2 += int(bad2)
                if bad2:
                    res.setdefault("F2 不同明細", []).append({"sid": s, "t": str(cal[t].date()), "獨立": [F1, F2, qs, eps, gm, gm4, ci], "主程式": f2})
        out4[part] = {"事件": int(len(E)), "去重不同": int(dd), "公司事件旗標不同": int(nd), "F1 不同": int(n1), "F2 不同": int(n2) if part == "main" else "不適用（早年不可判定）"}
        total += dd + nd + n1 + (n2 if part == "main" else 0)
        L[part] = (cal, ST, sids, avP, avM, qP, qQ)
    res["④ 全部事件"] = out4
    # ⑤ 出場抽樣
    out5 = []; nd5 = 0
    for part, k_ in (("main", int(a.n * 0.75)), ("早年", a.n - int(a.n * 0.75))):
        cal, ST, sids, avP, avM, qP, qQ = L[part]; n = len(cal)
        E = EV[(EV["版面"] == part) & (EV["X2_xk"] != "none")]
        pick = E.iloc[sorted(rng.choice(len(E), size=min(k_, len(E)), replace=False))]
        for r in pick.itertuples(index=False):
            s, t = r.sid, int(r.t); e = t + 1; v = ST[s]
            c, bar, BAD = v["c"], v["bar"], v["BAD"]
            okb = np.flatnonzero(bar & np.isfinite(v["o"]))
            ref = c[t - 10]
            rep = next((k for k in range(e, n) if bar[k] and c[k] >= ref * (1 - 1e-12)), None)
            rv_ = next((int(p_) for p_, M in zip(avP, avM) if p_ > t and np.isfinite(yoy(s, M)) and yoy(s, M) <= 0), None)
            ep_ = None
            if part == "main":
                ep_ = next((int(p_) for p_, qi in zip(qP, qQ) if p_ > t and np.isfinite(qsingle(s, qi)[0]) and qsingle(s, qi)[0] <= 0), None)
            mx = -np.inf; dd_ = None
            for k in range(e, n):
                mx = max(mx, c[k])
                if c[k] <= mx * 0.8 + 1e-12:
                    dd_ = k; break
            kb = next((k for k in range(e + 1, n) if BAD[k]), None)
            for x, trig in (("X1a", [(rep, "修復"), (rv_, "轉壞（營收）")]), ("X1b", [(rep, "修復"), (rv_, "轉壞（營收）"), (ep_, "轉壞（EPS）")]),
                            ("X2", [(dd_, "回落20%")])):
                if x == "X1b" and part != "main":
                    continue
                tr = [z for z in trig if z[0] is not None]
                k_t, why = min(tr, key=lambda z: z[0]) if tr else (None, None)
                sell = None
                if k_t is not None and k_t + 1 < n:
                    q = okb[okb >= k_t + 1]; sell = int(q[0]) if len(q) else None
                if kb is not None and (sell is None or kb <= sell):
                    y = max(k for k in range(e, kb) if bar[k]); mine = ("close", y, "壞根前收盤強制出")
                elif k_t is not None and k_t + 1 < n:
                    mine = ("open", k_t + 1, why)
                else:
                    mine = ("open", -1, "未完")
                theirs = (getattr(r, f"{x}_xk"), int(getattr(r, f"{x}_x")), getattr(r, f"{x}_why"))
                ok = mine == theirs
                nd5 += int(not ok)
                if not ok:
                    out5.append({"版面": part, "sid": s, "t": str(cal[t].date()), "格出場": x, "獨立": list(mine), "主程式": list(theirs)})
    res["⑤ 出場抽樣"] = {"抽筆": int(a.n), "不同": int(nd5), "不同明細": out5[:20]}
    total += nd5
    res["總不同"] = int(total)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
