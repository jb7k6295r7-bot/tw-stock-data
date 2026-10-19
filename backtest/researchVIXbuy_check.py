# -*- coding: utf-8 -*-
"""researchVIXbuy 獨立查核（⛔ 不 import 主檔與 researchUSC13 的計算函式；美股自讀原始 csv，台股只借 researchRev.market_series 的序列）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXbuy_check

V1 觸發段：csv 直讀 fred_VIXCLS.csv（≤ 2026-09-30、丟 "."）自算段起／段止 ⇒ 30／50／75 與 C13_segments.csv 逐列相同（段起日、段止日、買進日），
   40 與 VIXbuy_events.csv 相同；段數 30＝25（台股期 18）、50＝3、75＝2。
V2 段內最深／回本：30／50／75 的 VIXbuy_events.csv 段內最深、回本交易日 ＝ C13_segments.csv（同定義）。
V3 報酬手算：每一筆事件的 5 個持有期報酬，用自建「加月」（年月進位、月底截日）＋ 原始開收重算，最大絕對差；印 3 筆樣本。
V4 台股時差：買進日 ＞ VIX 日期 d，且 d 與買進日之間沒有 0050 K 棒日。
V5 隨機對照重算：pandas 逐日自算全部日平均／中位／勝率 ⇒ 對 VIXbuy.json；百分位（觸發組平均在隨機同檔數平均中）換 seed 重抽 ⇒ 差 ≤ 3 個百分點。
V6 策略鎖 backtest/strategy_lock.py --check。
"""
from __future__ import annotations

import calendar
import csv
import json
import os
import subprocess
from bisect import bisect_right

import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/usdata/60d2f99/data/macro")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsVIXbuy")
C13 = os.path.expanduser("~/tw-p17/backtest/resultsUSC13/C13_segments.csv")
END = "2026-09-30"; TW0 = "2003-06-30"
THRS = (30.0, 40.0, 50.0, 75.0)
HM = {3: "3個月", 6: "6個月", 12: "1年", 36: "3年", 60: "5年"}
R = {}


def rd(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def add_months(d, m):
    y, mo, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    k = y * 12 + mo - 1 + m
    y2, mo2 = k // 12, k % 12 + 1
    return f"{y2:04d}-{mo2:02d}-{min(dd, calendar.monthrange(y2, mo2)[1]):02d}"


# ── 原始資料 ──
vix = [(r["date"], fnum(r["value"])) for r in rd("fred_VIXCLS.csv") if r["date"] <= END]
vix = [(d, v) for d, v in vix if v is not None]
gs = {r["date"]: r for r in rd("yahoo_GSPC.csv") if r["date"] <= END}
tr = {r["date"]: r for r in rd("yahoo_SP500TR.csv") if r["date"] <= END}
cal = sorted(gs)
us_o, us_c = {}, {}
for d in cal:
    t = tr.get(d); g = gs[d]
    if t is None:
        continue
    tc, go, gc = fnum(t["adjclose"]), fnum(g["open"]), fnum(g["close"])
    if tc and gc:
        us_c[d] = tc
        if go:
            us_o[d] = go * tc / gc
us_cd = sorted(us_c)

from backtest import researchRev as RV
_, spl, _ = RV.market_series()
v = spl["valid"]
tw_d = [str(x) for x in np.asarray(spl["dates"])[v]]
tw_oa = np.asarray(spl["o"], float)[v]; tw_ca = np.asarray(spl["c"], float)[v]
tw_o = {d: o for d, o in zip(tw_d, tw_oa) if np.isfinite(o) and o > 0}
tw_c = {d: c for d, c in zip(tw_d, tw_ca) if np.isfinite(c) and c > 0}
tw_cd = sorted(tw_c)

MK = {"美股（^SP500TR）": (cal, us_o, us_c, us_cd), "台股（0050）": (tw_d, tw_o, tw_c, tw_cd)}


def buy_date(days, opn, d):
    i = bisect_right(days, d)
    while i < len(days) and days[i] not in opn:
        i += 1
    return days[i] if i < len(days) else None


def close_on_or_before(cd, cl, d):
    i = bisect_right(cd, d) - 1
    return cl[cd[i]]


def ret(mk, b, m):
    days, opn, cl, cd = MK[mk]
    tg = add_months(b, m)
    if tg > days[-1]:
        return None
    return close_on_or_before(cd, cl, tg) / opn[b] - 1


# ── V1 段 ──
def segs(thr, lo=None):
    out = []; cur = None
    for d, x in vix:
        if lo and d < lo:
            continue
        if cur is None:
            if x >= thr:
                cur = [d, None]
        elif x <= 20:
            cur[1] = d; out.append(tuple(cur)); cur = None
    if cur:
        out.append((cur[0], "資料末仍 ＞ 20"))
    return out


c13 = pd.read_csv(C13, dtype=str)
ev = pd.read_csv(os.path.join(OUT, "VIXbuy_events.csv"), dtype=str)
mis = []; cnt = {}
for mk, lo in (("美股（^SP500TR）", None), ("台股（0050）", TW0)):
    days, opn, _, _ = MK[mk]
    for thr in THRS:
        sg = segs(thr, lo); cnt[f"{mk}≥{thr:.0f}"] = len(sg)
        mine = [(a, b, buy_date(days, opn, a) or "無資料") for a, b in sg]
        e = ev[(ev["市場"] == mk) & (ev["門檻"].astype(float) == thr)]
        evl = list(zip(e["段起日"], e["段止日（VIX≤20）"], e["買進日"]))
        if mine != evl:
            mis.append(("events", mk, thr))
        if thr != 40.0:
            c = c13[(c13["市場"] == mk) & (c13["門檻"].astype(float) == thr)]
            if mine != list(zip(c["段起日"], c["段止日（VIX≤20）"], c["買進日"])):
                mis.append(("C13", mk, thr))
R["V1_觸發段"] = {"段數": cnt, "不一致": mis, "對": not mis and cnt["美股（^SP500TR）≥30"] == 25 and cnt["台股（0050）≥30"] == 18
                 and cnt["美股（^SP500TR）≥50"] == 3 and cnt["美股（^SP500TR）≥75"] == 2}

# ── V2 段內最深／回本 對 C13 ──
mx = 0.0; bad_rc = 0; n2 = 0
for thr in (30.0, 50.0, 75.0):
    for mk in MK:
        e = ev[(ev["市場"] == mk) & (ev["門檻"].astype(float) == thr)].reset_index(drop=True)
        c = c13[(c13["市場"] == mk) & (c13["門檻"].astype(float) == thr)].reset_index(drop=True)
        for i in range(len(e)):
            if e.loc[i, "買進日"] == "無資料":
                continue
            n2 += 1
            mx = max(mx, abs(float(e.loc[i, "段內最深"]) - float(c.loc[i, "最深（收盤÷買價−1）"])))
            bad_rc += str(int(float(e.loc[i, "段內最深_回本交易日"]))) != str(int(float(c.loc[i, "回本交易日"])))
R["V2_段內最深回本對C13"] = {"筆數": n2, "最深最大差": mx, "回本日數不一致": bad_rc, "對": mx < 1e-4 and bad_rc == 0}

# ── V3 報酬手算 ──
mx = 0.0; n3 = 0; samp = []
for _, r in ev.iterrows():
    if r["買進日"] == "無資料":
        continue
    for m, nm in HM.items():
        mine = ret(r["市場"], r["買進日"], m)
        got = r[f"報酬_{nm}"]
        if mine is None or pd.isna(got) or got == "":
            if not (mine is None and (pd.isna(got) or got == "")):
                mx = max(mx, 9.0)
            continue
        n3 += 1; mx = max(mx, abs(mine - float(got)))
    if (r["段起日"], float(r["門檻"])) in {("2008-09-15", 30.0), ("2020-03-16", 75.0), ("2011-08-08", 40.0)}:
        samp.append({"市場": r["市場"], "門檻": r["門檻"], "段起日": r["段起日"], "買進日": r["買進日"],
                     "1年出場日（≤）": add_months(r["買進日"], 12), "手算1年": ret(r["市場"], r["買進日"], 12), "主檔1年": float(r["報酬_1年"])})
R["V3_報酬手算"] = {"格數": n3, "最大絕對差（四位小數存檔）": mx, "對": mx < 6e-5, "樣本": samp}

# ── V4 台股時差 ──
bad = 0; n4 = 0
for _, r in ev[ev["市場"] == "台股（0050）"].iterrows():
    d, b = r["段起日"], r["買進日"]
    n4 += 1; i = bisect_right(tw_d, d)
    bad += not (b > d and tw_d[i] == b)
R["V4_台股時差"] = {"筆數": n4, "違反": bad, "對": bad == 0}

# ── V5 隨機對照重算 ──
J = json.load(open(os.path.join(OUT, "VIXbuy.json"), encoding="utf-8"))
mx = 0.0; pdiff = 0.0; rows5 = []
for mk, key, d0 in (("美股（^SP500TR）", "美股", "1990-01-02"), ("台股（0050）", "台股", "2004-02-11")):
    days, opn, cl, cd = MK[mk]
    base = [d for d in days if d >= d0 and d in opn]
    for m, nm in HM.items():
        x = np.array([ret(mk, d, m) for d in base], dtype=object)
        x = np.array([y for y in x if y is not None], float)
        s = pd.Series(x)
        mine = {"平均": s.mean(), "中位": s.median(), "勝率": (s > 0).mean(), "n": len(s)}
        got = J[key]["≥30"][nm]["全部日"]
        for k in ("平均", "中位", "勝率"):
            mx = max(mx, abs(mine[k] - got[k]))
        if mine["n"] != got["n"]:
            mx = max(mx, 9.0)
        rng = np.random.default_rng(12345)
        for thr in THRS:
            c = J[key][f"≥{thr:.0f}"][nm]
            k_ = c["觸發組"]["n"]
            if k_ == 0:
                continue
            means = np.array([x[rng.choice(len(x), k_, replace=False)].mean() for _ in range(4000)])
            p = float(((means < c["觸發組"]["平均"]).sum() + 0.5 * (means == c["觸發組"]["平均"]).sum()) / len(means))
            pdiff = max(pdiff, abs(p - c["觸發組平均在隨機同檔數平均中的百分位"]))
            rows5.append((key, thr, nm, round(p, 3), round(c["觸發組平均在隨機同檔數平均中的百分位"], 3)))
R["V5_隨機對照重算"] = {"全部日統計最大差": mx, "百分位換seed最大差": pdiff, "對": mx < 1e-9 and pdiff <= 0.03}

# ── V6 策略鎖 ──
r = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], cwd=os.path.expanduser("~/tw-p17"),
                   capture_output=True, text=True)
R["V6_策略鎖"] = {"exit": r.returncode, "輸出末行": (r.stdout.strip().splitlines() or [""])[-1][:200], "對": r.returncode == 0}

R["總結"] = {k: v["對"] for k, v in R.items() if isinstance(v, dict) and "對" in v}
R["全對"] = all(R["總結"].values())
json.dump(R, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
