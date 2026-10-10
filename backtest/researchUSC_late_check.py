# -*- coding: utf-8 -*-
"""USREG-C 批後四件（C11、C12、C9、C2）獨立查核：⭐ 不 import 主程式的計算函式（C2 的「主程式路徑」對照段除外，見各項），
自己從原始 CSV／gzip 重讀、用逐日迴圈重算，抽樣比對 ⇒ 0 不同才算過。結果 → resultsUSC/late/check.json。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC_late_check

X1 C11 判定格：csv 模組讀 SSO／IEF／GLD／^GSPC／DTB3，逐日迴圈（年初開盤再平衡、換手 × 0.05%）⇒ 年化、回落 對 C11_summary（|差| ≤ 1e-9）。
X2 C12：逐月底重算 M、E、Sahm、主規則（自寫月底、自寫首次公布值篩選）⇒ 逐筆出場表（主規則、單用月線）與 2024 表逐列比；段三 1 倍主規則年化逐日迴圈重算。
X3 C9：自寫 3 倍合成（UPRO 早年段）＋ 200 日線 ⇒ UPRO×H、UPRO×M 早年段年化；TQQQ×M 2022 段（真實）年化。
X4 C2 Form 4：從 gzip 原始列抽 300 筆 A 級買進（合併後）重算 可用日、金額、分類、CEO 類、是否在母體與代號 ⇒ 對 c2_events.pkl。
X5 C2 異常報酬：抽 300 個 A 事件，逐檔迴圈重算 r20、前 20 日報酬、十分位、對照平均 ⇒ 對主程式矩陣路徑（researchUSC_late_c2 的 mats／past20／deciles／ctrl_mean）。
X6 C2 乙出場：抽 300 筆 B／C 進場，逐日迴圈重算出場日與原因 ⇒ 對主程式 exit_for。
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import math
import os
import pickle
import re
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
ROOT = os.path.expanduser("~/usdata/b33bde6/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSC/late")
WORK = os.path.expanduser("~/us_work/c_late")
END = "2026-09-30"
RES = {}


def rd(name):
    out = {}
    with open(os.path.join(ROOT, "macro", f"yahoo_{name}.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["date"] > END:
                continue
            try:
                c = float(r["close"]); a = float(r["adjclose"]); o = float(r["open"])
            except ValueError:
                continue
            if c > 0 and o > 0:
                out[r["date"]] = (o * a / c, a)
    return out


def calendar():
    with open(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), encoding="utf-8") as f:
        return sorted({r["date"] for r in csv.DictReader(f) if r["date"] <= END})


def dtb3(cal):
    v = {}
    with open(os.path.join(ROOT, "macro", "fred_DTB3.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                v[r["date"]] = float(r["value"])
            except ValueError:
                pass
    ks = sorted(v); out = {}; j = 0; last = None
    for d in cal:
        while j < len(ks) and ks[j] <= d:
            last = v[ks[j]]; j += 1
        out[d] = last
    return out


def stats(eq):
    n = len(eq); cagr = eq[-1] ** (252 / n) - 1
    pk = 1.0; mdd = 0.0
    for x in [1.0] + list(eq):
        pk = max(pk, x); mdd = min(mdd, x / pk - 1)
    return cagr, mdd


def sim(cal, i0, i1, px, w, rebal_days, rate):
    """px：{資產: {date: (開, 收)}}；w：{資產: 權重}；rebal_days：再平衡日集合；逐日迴圈。"""
    units = {a: 0.0 for a in w}; cash = 1.0; eq = []; last_c = {}
    for t in range(i0, i1 + 1):
        d = cal[t]
        if t == i0 or d in rebal_days:
            V = cash + sum(units[a] * px[a][d][0] for a in w)
            hold = {a: units[a] * px[a][d][0] for a in w}
            tc = (1 - sum(w.values())) * V
            tr = 0.5 * (sum(abs(w[a] * V - hold[a]) for a in w) + abs(tc - cash))
            V2 = V - tr * 0.0005
            for a in w:
                units[a] = w[a] * V2 / px[a][d][0]
            cash = (1 - sum(w.values())) * V2
        if t > i0:
            cash *= 1 + rate[cal[t - 1]] / 100 / 252
        for a in w:
            if d in px[a]:
                last_c[a] = px[a][d][1]
        eq.append(cash + sum(units[a] * last_c[a] for a in w))
    return eq


def x1(cal):
    S = json.load(open(os.path.join(OUT, "C11_summary.json"), encoding="utf-8"))
    px = {k: rd(k) for k in ("SSO", "IEF", "GLD")}
    i0 = cal.index("2006-06-21") + 200; i1 = cal.index(END)
    reb = {cal[t] for t in range(i0 + 1, i1 + 1) if cal[t][:4] != cal[t - 1][:4]}
    eq = sim(cal, i0, i1, px, {"SSO": .5, "IEF": .3, "GLD": .2}, reb, dtb3(cal))
    c, m = stats(eq)
    d1 = abs(c - S["判定"]["年化"]); d2 = abs(m - S["判定"]["回落"])
    RES["X1 C11 判定格"] = {"年化差": d1, "回落差": d2, "不同": int(d1 > 1e-6 or d2 > 1e-6)}


def month_ends(cal):
    return [cal[i] for i in range(len(cal)) if i == len(cal) - 1 or cal[i][:7] != cal[i + 1][:7]]


def x2(cal):
    tr = rd("SP500TR"); me = month_ends(cal)
    rel = []
    with open(os.path.join(ROOT, "macro", "alfred_UNRATE_first_release.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["first_value"] != "":
                rel.append((r["ref_month"], float(r["first_value"]), r["release_date"]))
    rel.sort()
    dec = {}; mon = {}; sahm = {}; Mx = {}; Ex = {}
    for j, d in enumerate(me):
        if j < 9:
            continue
        cs = [tr[x][1] for x in me[j - 9:j + 1]]
        M = cs[-1] > sum(cs) / 10
        vs = [v for (_, v, rdd) in rel if rdd <= d]
        E = vs[-1] < sum(vs[-12:]) / 12
        a = [sum(vs[i - 2:i + 1]) / 3 for i in range(len(vs) - 13, len(vs))]
        sahm[d] = a[-1] - min(a[:-1]) >= 0.5 - 1e-12
        dec[d] = M or E; mon[d] = M; Mx[d] = M; Ex[d] = E
    s1 = cal[cal.index(me[9]) + 1]
    gs0 = {}
    with open(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["date"] <= END:
                gs0[r["date"]] = (float(r["open"]), float(r["close"]))
    tro = {d: gs0[d][0] * tr[d][1] / gs0[d][1] for d in tr if d in gs0}

    def exits(D):
        ks = [d for d in me if d in D and d >= cal[cal.index(s1) - 1]]
        out = []; prev = None
        for j, d in enumerate(ks):
            cur = D[d]
            if prev is True and not cur:
                ex = cal[cal.index(d) + 1] if cal.index(d) + 1 < len(cal) else None
                if ex is None:
                    prev = cur; continue
                back = [k for k in ks[j + 1:] if D[k] and cal.index(k) + 1 < len(cal)]
                if back:
                    rr = cal[cal.index(back[0]) + 1]
                    out.append((ex, rr, round(tro[rr] / tro[ex] - 1, 9)))
                else:
                    out.append((ex, "窗尾仍出場", round(tr[END][1] / tro[ex] - 1, 9)))
            prev = cur
        return out
    mine = {"主規則": exits(dec), "單用月線": exits(mon)}
    theirs = defaultdict(list)
    with open(os.path.join(OUT, "C12_exits.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            theirs[r["規則"]].append((r["出場日"], r["回場日"], round(float(r["期間指數漲跌"]), 9)))
    diff = 0; nn = 0
    for k in mine:
        nn += len(mine[k])
        if len(mine[k]) != len(theirs[k]):
            diff += abs(len(mine[k]) - len(theirs[k]))
        for a, b in zip(mine[k], theirs[k]):
            diff += int(a[0] != b[0] or a[1] != b[1] or abs(a[2] - b[2]) > 1e-6)
    # 2024
    d24 = 0; n24 = 0
    with open(os.path.join(OUT, "C12_sahm2024.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["月底"]; n24 += 1
            d24 += int((r["Sahm觸發"] == "True") != sahm[d] or (r["主規則持有"] == "True") != dec[d] or (r["M（站上10月線）"] == "True") != Mx[d])
    # 段三 1 倍主規則
    S = json.load(open(os.path.join(OUT, "C12_summary.json"), encoding="utf-8"))
    i0 = cal.index("2022-01-03"); i1 = cal.index(END)
    rate = dtb3(cal); gs = {}
    with open(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["date"] <= END:
                gs[r["date"]] = (float(r["open"]), float(r["close"]))
    trp = {d: (gs[d][0] * tr[d][1] / gs[d][1], tr[d][1]) for d in tr if d in gs}
    hold = None; units = 0.0; cash = 1.0; eq = []
    for t in range(i0, i1 + 1):
        d = cal[t]
        prev_me = max(x for x in me if x < d)
        want = dec[prev_me]
        if want != hold:
            V = cash + units * trp[d][0]
            V2 = V if (hold is None and not want) else V * (1 - 0.0005)
            units = V2 / trp[d][0] if want else 0.0; cash = 0.0 if want else V2; hold = want
        if t > i0:
            cash *= 1 + rate[cal[t - 1]] / 100 / 252
        eq.append(cash + units * trp[d][1])
    c, m = stats(eq)
    k3 = [k for k in S["段"] if k.startswith("段三")][0]
    dd = abs(c - S["段"][k3]["1 倍×主規則"]["年化"])
    RES["X2 C12"] = {"逐筆出場列數": nn, "逐筆出場不同": diff, "2024表列數": n24, "2024表不同": d24, "段三1倍主規則年化差": dd,
                     "不同": int(diff + d24 + (dd > 1e-6))}


def x3(cal):
    S = json.load(open(os.path.join(OUT, "C9_summary.json"), encoding="utf-8"))
    tr = rd("SP500TR"); rate = dtb3(cal); f = S["費用率（SEC 497K 淨／毛）"]["UPRO"]["淨"]
    gs = {}
    with open(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["date"] <= END:
                gs[r["date"]] = (float(r["open"]), float(r["close"]))
    tro = {d: gs[d][0] * tr[d][1] / gs[d][1] for d in tr if d in gs}
    syn = {}; L = 1.0; prev = None
    for d in cal:
        if prev is None:
            syn[d] = (math.nan, 1.0); prev = d; continue
        r = tr[d][1] / tr[prev][1] - 1
        o = L * (1 + 3 * (tro[d] / tr[prev][1] - 1))
        L = L * (1 + 3 * r - 2 * (rate[prev] / 100 + 0.0025) / 252 - f / 252)
        syn[d] = (o, L); prev = d
    closes = [tr[d][1] for d in cal]
    ma = {}
    for i in range(199, len(cal)):
        ma[cal[i]] = sum(closes[i - 199:i + 1]) / 200
    first = cal[199]
    e0 = next(cal[i] for i in range(cal.index(first) + 1, len(cal)) if cal[i][:7] != cal[i - 1][:7])
    i0 = cal.index(e0); i1 = cal.index("2009-05-29")
    out = {}
    for arm in ("H", "M"):
        units = 0.0; cash = 1.0; eq = []; held = None
        for t in range(i0, i1 + 1):
            d = cal[t]; pd_ = cal[t - 1]
            want = True if arm == "H" else (closes[t - 1] > ma[pd_])
            if want != held:
                V = cash + units * syn[d][0]
                V2 = V - V * 0.0005 if (want or held) else V
                units = V2 / syn[d][0] if want else 0.0; cash = 0.0 if want else V2; held = want
            if t > i0:
                cash *= 1 + rate[pd_] / 100 / 252
            eq.append(cash + units * syn[d][1])
        out[arm] = stats(eq)[0]
    dH = abs(out["H"] - S["格"]["UPRO×H｜早年合成"]["年化"]); dM = abs(out["M"] - S["格"]["UPRO×M｜早年合成"]["年化"])
    RES["X3 C9"] = {"UPRO×H 早年年化差": dH, "UPRO×M 早年年化差": dM, "不同": int(dH > 1e-6 or dM > 1e-6)}


def x4_6(cal_full):
    import pandas as pd
    from backtest import researchUSA3_core as C3
    from backtest import researchUSC_late_c2 as K
    EVP = pickle.load(open(os.path.join(WORK, "c2_events.pkl"), "rb")); B = EVP["B"]; EV = EVP["EV"]
    meta, ST = C3.load_cache(); cal = [str(x.date()) for x in meta["cal"]]; n = len(cal); pos = {d: i for i, d in enumerate(cal)}
    rng = np.random.default_rng(777)
    # 原始列
    rows = defaultdict(list); hist = defaultdict(set)
    for y in range(2013, 2027):
        with gzip.open(os.path.join(ROOT, "insider", f"form4_{y}.csv.gz"), "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["form"] != "4" or r["trans_code"] not in ("P", "S"):
                    continue
                for o in r["owner_cik"].split(";"):
                    hist[o].add(r["trans_date"][:7])
                if r["trans_code"] == "P" and (r["is_director"] == "1" or r["is_officer"] == "1"):
                    rows[(r["issuer_cik"], r["owner_cik"].split(";")[0], r["trans_date"])].append(r)

    def av_of(acc):
        d = acc[:10]; h = acc[11:19]
        if d < cal[0]:
            return -1
        k = next((i for i, x in enumerate(cal) if x > d), None)
        if k is None:
            return -1
        k += 1 if h > "16:00:00" else 0
        return k if k < n else -1
    samp = B.iloc[rng.choice(len(B), 300, replace=False)]
    bad = 0
    for _, b in samp.iterrows():
        rr = rows[(b["issuer_cik"], b["owner1"], b["trans_date"])]
        amt = sum(float(r["shares"]) * float(r["price"]) for r in rr if r["price"] not in ("",) and r["shares"] not in ("",))
        av = max(av_of(r["filing_accepted_at"]) for r in rr)
        aff = any(r["aff10b5one"] == "1" for r in rr)
        y = int(b["trans_date"][:4]); m = b["trans_date"][5:7]; h = hist[b["owner1"]]
        if b["trans_date"] >= "2023-04-01" and aff:
            cls = "例行"
        elif not all(any(x.startswith(str(y - k)) for x in h) for k in (1, 2, 3)):
            cls = "不分類"
        else:
            cls = "例行" if all(f"{y - k}-{m}" in h for k in (1, 2, 3)) else "機會"
        t = next((x for x in rr if x["officer_title"]), {"officer_title": ""})["officer_title"].upper()
        def word(w):
            return re.search(r"(^|[^A-Z0-9_])" + w + r"([^A-Z0-9_]|$)", t) is not None
        ceo = (word("CEO") or "CHIEF EXECUTIVE" in t or word("CFO") or "CHIEF FINANCIAL" in t
               or ("PRESIDENT" in t and not (re.search(r"VICE[ \t\-]*PRES", t) or word("VP") or word("EVP") or word("SVP") or re.search(r"V\.[ ]*P\.", t))))
        tk = None
        if 0 <= av < n:
            for s in sorted(b["ticker"].split(";")):
                d = ST.get(s)
                if d is not None and d["member"][av] and d["valid"][av] and np.isfinite(d["O"][av]) and d["O"][av] > 0:
                    tk = s; break
        ok = abs(amt - b["amt"]) < 1e-6 * max(1, amt) and av == b["av"] and cls == b["cls"] and (tk == (b["sid"] if isinstance(b["sid"], str) else None))
        ok_ceo = ceo == b["ceo"]
        bad += int(not ok) + int(not ok_ceo)
    RES["X4 C2 Form4 抽 300"] = {"不同": bad}
    # X5
    F, _ = K.read_form4()
    O, valid, okO, Cf, PX, CS, MM = K.mats(ST, sorted(ST), n)
    sids = sorted(ST); sidx = {s: i for i, s in enumerate(sids)}
    w1 = pos["2026-09-30"]
    p20 = K.past20(Cf, valid, CS); r20 = K.fwd_ret(O, okO, PX, CS, 20, w1)
    insd = np.zeros((n, len(sids)), bool)
    calS = np.array(cal)
    avp = K.avail_pos(F.loc[F.trans_code == "P", "acc_date"].to_numpy(str), F.loc[F.trans_code == "P", "acc_time"].to_numpy(str), calS)
    for tk, a in zip(F.loc[F.trans_code == "P", "ticker"], avp):
        if 0 <= a < n:
            for t in tk.split(";"):
                if t in sidx:
                    insd[a, sidx[t]] = True
    dec = K.deciles(p20, MM["合併"] & okO); ct = K.ctrl_mean(r20, dec, insd)
    evA = EV["A"]; pick = rng.choice(len(evA), 300, replace=False); bad5 = 0; used = 0

    def brute_r(s, d):
        x = ST[s]
        if not (x["valid"][d] and x["O"][d] > 0) or d + 20 > w1:
            return math.nan
        if any(x["pb"][d + 1:d + 21]):
            return math.nan
        j = d + 20
        px = x["O"][j] if (x["valid"][j] and np.isfinite(x["O"][j]) and x["O"][j] > 0) else x["closes"][j]
        return px / x["O"][d] - 1

    def brute_p(s, d):
        x = ST[s]
        if d < 21 or any(x["pb"][d - 20:d]):
            return math.nan
        return x["closes"][d - 1] / x["closes"][d - 21] - 1
    for k in pick:
        s = evA["sid"].iloc[k]; d = int(evA["av"].iloc[k])
        r = brute_r(s, d)
        if not np.isfinite(r):
            continue
        used += 1
        pool = []
        for t in sids:
            x = ST[t]
            if x["member"][d] and x["valid"][d] and np.isfinite(x["O"][d]) and x["O"][d] > 0:
                p = brute_p(t, d)
                if np.isfinite(p):
                    pool.append((p, t))
        pool.sort()
        K_ = len(pool); dmap = {t: i * 10 // K_ for i, (p, t) in enumerate(pool)}
        my = dmap.get(s)
        vals = [brute_r(t, d) for t in dmap if dmap[t] == my and not insd[d, sidx[t]]]
        vals = [v for v in vals if np.isfinite(v)]
        ar_b = r - sum(vals) / len(vals)
        j = sidx[s]
        ar_m = r20[d, j] - ct[d, dec[d, j]]
        bad5 += int(not (abs(ar_b - ar_m) < 1e-10))
    RES["X5 C2 異常報酬 抽 300"] = {"可算": used, "不同": bad5}
    # X6
    sales_raw = defaultdict(set)
    hist2 = hist
    for y in range(2013, 2027):
        with gzip.open(os.path.join(ROOT, "insider", f"form4_{y}.csv.gz"), "rt", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["form"] != "4" or r["trans_code"] != "S" or not (r["is_director"] == "1" or r["is_officer"] == "1") or r["trans_date"] < "2015-01-01":
                    continue
                if r["aff10b5one"] == "1":
                    continue
                o = r["owner_cik"].split(";")[0]; yy = int(r["trans_date"][:4]); mm = r["trans_date"][5:7]
                h = hist2[o]
                if not all(any(x.startswith(str(yy - k)) for x in h) for k in (1, 2, 3)):
                    continue
                if all(f"{yy - k}-{mm}" in h for k in (1, 2, 3)):
                    continue
                a = av_of(r["filing_accepted_at"])
                if a >= 0:
                    sales_raw[r["issuer_cik"]].add(a)
    abuy = defaultdict(list)
    for iss, a in zip(B["issuer_cik"], B["av"]):
        if 0 <= a < n:
            abuy[iss].append(dt.date.fromisoformat(cal[a]))
    sales_m, _ = K.build_sales(F, calS, *K.hist_sets(F))
    abuy_m = {k: np.array(sorted(np.datetime64(x) for x in v), "datetime64[D]") for k, v in abuy.items()}
    cal_dt = np.array(cal, "datetime64[D]")
    bad6 = 0; tot6 = 0
    for c in ("B", "C"):
        ev = EV[c]
        for k in rng.choice(len(ev), 150, replace=False):
            iss = ev["issuer_cik"].iloc[k]; s = ev["sid"].iloc[k]; e = int(ev["av"].iloc[k])
            x = ST[s]; c_ = x["C"]; v = x["valid"]
            vals = []; mav = np.full(n, np.nan)
            for t in range(n):
                if v[t]:
                    vals.append(c_[t])
                    if len(vals) >= 200:
                        mav[t] = sum(vals[-200:]) / 200
            x1_ = min([a for a in sales_raw.get(iss, ()) if a > e], default=None)
            x2_ = None
            for t in range(e + 1, w1 + 1):
                if v[t] and np.isfinite(mav[t]) and c_[t] < mav[t]:
                    td = dt.date.fromisoformat(cal[t])
                    last = max([b for b in abuy[iss] if b <= td], default=dt.date(1900, 1, 1))
                    if (td - last).days >= 365:
                        x2_ = t + 1; break
            cands = [y for y in (x1_, x2_) if y is not None]
            mine = (min(cands), False) if cands and min(cands) <= w1 else (w1, True)
            got = K.exit_for(e, iss, K.ma200_below(x), sales_m, abuy_m, cal_dt, w1)
            tot6 += 1; bad6 += int(mine[0] != got[0] or mine[1] != got[1])
    RES["X6 C2 乙出場 抽 300"] = {"筆數": tot6, "不同": bad6}


def main():
    cal = calendar()
    x1(cal); print(RES, flush=True)
    x2(cal); print(RES, flush=True)
    x3(cal); print(RES, flush=True)
    x4_6(cal); print(RES, flush=True)
    RES["總不同"] = int(sum(v["不同"] for v in RES.values() if isinstance(v, dict)))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("✅ 0 不同" if RES["總不同"] == 0 else f"❌ 不同 {RES['總不同']}", flush=True)


if __name__ == "__main__":
    main()
