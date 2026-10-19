# -*- coding: utf-8 -*-
"""researchVIXentry 獨立查核（⛔ 不 import 主檔與 researchUSC13 的計算函式；美股自讀原始 csv；台股只借 researchRev.market_series（0050）與 data.load_stock（00631L）的序列）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXentry_check

K1 觸發與回落日：fred_VIXCLS.csv 直讀自算 ≥40 段（段起 d0、段止 ≤20）、所屬 ≥30 段起日、段內第一個 ≥50、d0 之後第一個 ＜30 ⇒ 對 VIXentry_triggers.csv 逐列；
   段數 美股 9、台股期 6。
K2 全部段 × 方式 × 持有期手算：自寫買進日（市場日期 ＞ VIX 日、有效開盤）、自寫加月、自寫月初交易日、自寫 DTB3 現金（DTB3_{t−1}/100/252、前值補）與財富 ⇒
   期末財富、平均成本對觸發日收盤、買進後最深再跌、帳面最深，對 ~/us_work/vixentry/VIXentry_segments_all.csv 最大絕對差 ＜ 1e-6（該 csv 存 6 位小數）；合成 SSO 自寫 A1 seq3 式。
K3 抽樣印出：美股 2008-09-29 段 E1／E2／E3 與 0050 2020-02-28 段 E4 的買進日、買價、期末財富（逐步算式）。
K4 真實 SSO 對合成 SSO（重疊段 E1 期末財富差，描述）。
K5 策略鎖 backtest/strategy_lock.py --check。
"""
from __future__ import annotations

import calendar
import json
import os
import subprocess
from bisect import bisect_right

import numpy as np
import pandas as pd

MAC = os.path.expanduser("~/usdata/60d2f99/data/macro")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsVIXentry")
WORK = os.path.expanduser("~/us_work/vixentry")
END = "2026-09-30"; TW0 = "2003-06-30"
COST_US, COST_TW = 0.0005, 0.001425
R = {}


def rdcsv(name):
    return pd.read_csv(os.path.join(MAC, name), dtype=str, keep_default_na=False)


def num(s):
    return pd.to_numeric(s.replace({"": None, ".": None, "null": None}), errors="coerce").to_numpy(float)


def add_months(d, m):
    y, mo, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    k = y * 12 + mo - 1 + m
    y2, mo2 = k // 12, k % 12 + 1
    return f"{y2:04d}-{mo2:02d}-{min(dd, calendar.monthrange(y2, mo2)[1]):02d}"


# ── VIX ──
v = rdcsv("fred_VIXCLS.csv"); vx = num(v["value"])
vix = [(d, x) for d, x in zip(v["date"], vx) if d <= END and np.isfinite(x)]
VD = [d for d, _ in vix]; VV = [x for _, x in vix]


def segs(thr, lo=None):
    out = []; cur = None
    for i, (d, x) in enumerate(vix):
        if lo and d < lo:
            continue
        if cur is None:
            if x >= thr:
                cur = [i, None]
        elif x <= 20:
            cur[1] = i; out.append(tuple(cur)); cur = None
    if cur:
        out.append((cur[0], None))
    return out


def trig_info(lo):
    s40 = segs(40.0, lo); s30 = segs(30.0, lo); rows = []
    for a, b in s40:
        a30 = [x for x, y in s30 if y == b and x <= a][0]
        hi = b if b is not None else len(vix) - 1
        j50 = next((j for j in range(a, hi + 1) if VV[j] >= 50), None)
        j3 = next((j for j in range(a + 1, len(vix)) if VV[j] < 30), None)
        rows.append({"d0": VD[a], "end": VD[b] if b is not None else None, "d30": VD[a30],
                     "j50": VD[j50] if j50 is not None else None, "j3": VD[j3] if j3 is not None else None, "a": a, "b": b})
    return rows


# ── 美股原始 ──
gs = rdcsv("yahoo_GSPC.csv").drop_duplicates("date").set_index("date").sort_index()
tr = rdcsv("yahoo_SP500TR.csv").drop_duplicates("date").set_index("date").sort_index()
cal = [d for d in gs.index if d <= END]
gso = num(gs["open"].reindex(cal).fillna("")); gsc = num(gs["close"].reindex(cal).fillna(""))
trc = num(tr["adjclose"].reindex(cal).fillna(""))
uo = gso * trc / gsc; uc = trc
dt = rdcsv("fred_DTB3.csv"); dtv = pd.Series(num(dt["value"]), index=dt["date"]); dtv = dtv[dtv.index <= END].dropna()
dts = dtv.reindex(sorted(set(dtv.index) | set(cal))).ffill().reindex(cal).to_numpy(float)
g = np.zeros(len(cal)); g[1:] = dts[:-1] / 100 / 252
CIu = np.cumprod(1 + g)
ss = rdcsv("yahoo_SSO.csv").drop_duplicates("date").set_index("date").sort_index()
kf = num(ss["adjclose"].reindex(cal).fillna("")) / num(ss["close"].reindex(cal).fillna(""))
so = num(ss["open"].reindex(cal).fillna("")) * kf; sc = num(ss["adjclose"].reindex(cal).fillna(""))
# 合成 SSO（A1 seq3：自寫）
Lc = np.full(len(cal), np.nan); Lo = np.full(len(cal), np.nan); Lc[0] = 1.0
for t in range(1, len(cal)):
    r = uc[t] / uc[t - 1] - 1
    Lc[t] = Lc[t - 1] * (1 + 2 * r - (dts[t - 1] / 100 + 0.0025) / 252 - 0.0089 / 252)
    Lo[t] = Lc[t - 1] * (1 + 2 * (uo[t] / uc[t - 1] - 1))

# ── 台股 ──
from backtest import researchRev as RV
_, spl, _ = RV.market_series()
vv_ = spl["valid"]
twd = [str(x) for x in np.asarray(spl["dates"])[vv_]]
two = np.asarray(spl["o"], float)[vv_]; twc = np.asarray(spl["c"], float)[vv_]
D = RV.D
calm = D.load_calendar(); st = D.load_stock("00631L", "twse", calm)
ld = np.array([str(x.date()) for x in calm]); lo_ = st.df["open"].to_numpy(float); lc_ = st.df["close"].to_numpy(float)
m_ = np.isfinite(lc_)


def mk(dates, o, c, CI, cost, lo):
    dates = list(dates); o = np.asarray(o, float); c = np.asarray(c, float)
    ok = np.isfinite(o) & (o > 0) & np.isfinite(c) & (c > 0)
    cf = pd.Series(np.where(np.isfinite(c) & (c > 0), c, np.nan)).ffill().to_numpy()
    return {"d": dates, "o": o, "cf": cf, "ok": ok, "CI": CI, "cost": cost, "lo": lo, "first": dates[int(np.flatnonzero(ok)[0])]}


MK = {"美股 ^SP500TR": mk(cal, uo, uc, CIu, COST_US, None),
      "台股 0050": mk(twd, two, twc, np.ones(len(twd)), COST_TW, TW0),
      "00631L 元大台灣50正2": mk(ld[m_], lo_[m_], lc_[m_], np.ones(int(m_.sum())), COST_TW, TW0),
      "美股 SSO（真實 2 倍）": mk(cal, so, sc, CIu, COST_US, None),
      "美股 合成 SSO（⚠ 合成、非實際 ETF）": mk(cal, Lo, Lc, CIu, COST_US, None)}


def buy_pos(X, vdate):
    if vdate is None:
        return None
    i = bisect_right(X["d"], vdate)
    while i < len(X["d"]) and not X["ok"][i]:
        i += 1
    return i if i < len(X["d"]) else None


def month_first(X, b, k):
    y, m = int(X["d"][b][:4]), int(X["d"][b][5:7])
    kk = y * 12 + m - 1 + k
    pref = f"{kk // 12:04d}-{kk % 12 + 1:02d}"
    for i in range(b, len(X["d"])):
        if X["d"][i][:7] == pref:
            while i < len(X["d"]) and not X["ok"][i]:
                i += 1
            return i if i < len(X["d"]) else None
        if X["d"][i][:7] > pref:
            return None
    return None


def hand(X, s, buys, e):
    """buys：[(位置, 比例)]（位置 ≤ e）；逐日財富。"""
    o, cf, CI, cost = X["o"], X["cf"], X["CI"], X["cost"]
    cash = 1.0; last = s - 1; sh = 0.0; amts = []; path = []
    bmap = {}
    for t, f in buys:
        bmap.setdefault(t, []).append(f)
    for t in range(s, e + 1):
        for f in bmap.get(t, []):
            cash = cash * CI[t - 1] / CI[last]; last = t - 1
            a = cash * f; cash -= a; sh += a * (1 - cost) / o[t]; amts.append((t, a))
        path.append(sh * cf[t] + cash * CI[t] / CI[last])
    return path, amts


ref = pd.read_csv(os.path.join(WORK, "VIXentry_segments_all.csv"), dtype={"段起日d0": str})
trg = pd.read_csv(os.path.join(OUT, "VIXentry_triggers.csv"), dtype=str)

# ── K1 ──
mis = []; cnt = {}
for lbl, X in MK.items():
    T = trig_info(X["lo"]); cnt[lbl] = len(T)
    t = trg[trg["標的"] == lbl]
    mine = [(r["d0"], r["d30"], r["j3"]) for r in T if r["d0"] >= X["first"]]
    theirs = list(zip(t["段起日d0"], t["E5的≥30段起日"], t["E3回落<30日"]))
    if mine != theirs:
        mis.append(lbl)
    for r, (_, row) in zip([r for r in T if r["d0"] >= X["first"]], t.iterrows()):
        exp2 = r["j50"] if r["j50"] else r["end"]
        if str(row["E2第二筆依據"]).split(" ")[-1] != str(exp2) and not (exp2 is None and "段未止" in str(row["E2第二筆依據"])):
            mis.append((lbl, r["d0"], "E2"))
R["K1_觸發與回落日"] = {"≥40段數": cnt, "不一致": mis, "對": (not mis) and cnt["美股 ^SP500TR"] == 9 and cnt["台股 0050"] == 6,
                    "≥40段（美股）": [(r["d0"], r["d30"], r["j50"], r["j3"], r["end"]) for r in trig_info(None)]}

# ── K2 ──
diffs = {}; rows = []; samples = []
for lbl, X in MK.items():
    for r in trig_info(X["lo"]):
        if r["d0"] < X["first"]:
            continue
        b0 = buy_pos(X, r["d0"])
        iref = bisect_right(X["d"], r["d0"]) - 1; rp = X["cf"][iref]
        ended = r["end"] is not None
        b2 = buy_pos(X, r["j50"]) if r["j50"] else (buy_pos(X, r["end"]) if ended else None)
        b3 = buy_pos(X, r["j3"]); b5 = buy_pos(X, r["d30"])
        P = {"E1": (b0, [(b0, 1.0)]), "E2": (b0, [(b0, 0.5), (b2, 1.0)]), "E3": (b0, [(b3, 1.0)]),
             "E4": (b0, [(b0, 1 / 3), (month_first(X, b0, 1), 0.5), (month_first(X, b0, 2), 1.0)]), "E5": (b5, [(b5, 1.0)])}
        for hm, hn in ((12, "1年"), (36, "3年")):
            tg = add_months(r["d0"], hm)
            if tg > X["d"][-1]:
                continue
            e = bisect_right(X["d"], tg) - 1
            for m, (s, bb) in P.items():
                if m == "E5" and r["d30"] < X["first"]:
                    continue
                bb = [(t, f) for t, f in bb if t is not None and t <= e]
                path, am = hand(X, s, bb, e)
                W = path[-1]
                tot = sum(a for _, a in am)
                avg = tot / sum(a / X["o"][t] for t, a in am) if am else np.nan
                ddb = sum(a * min(0, X["cf"][t:e + 1].min() / X["o"][t] - 1) for t, a in am) / tot if am else np.nan
                acct = min(0.0, min(path) - 1)
                x = ref[(ref["標的"] == lbl) & (ref["段起日d0"] == r["d0"]) & (ref["持有"] == hn) & (ref["方式"] == m)]
                if len(x) != 1:
                    diffs.setdefault(lbl, []).append(("缺列", r["d0"], hn, m)); continue
                x = x.iloc[0]
                rows.append({"標的": lbl, "d": [abs(W - x["期末財富"]), abs(avg / rp - 1 - x["平均成本對觸發日收盤"]), abs(ddb - x["買進後最深再跌"]), abs(acct - x["帳面最深"])]})
                if (lbl == "美股 ^SP500TR" and r["d0"] == "2008-09-29" and hn == "1年" and m in ("E1", "E2", "E3")) or \
                   (lbl == "台股 0050" and r["d0"] == "2020-02-28" and hn == "1年" and m == "E4"):
                    samples.append({"標的": lbl, "d0": r["d0"], "方式": m, "持有": hn, "結束日": X["d"][e], "期末收盤": round(float(X["cf"][e]), 4),
                                    "各筆": [(X["d"][t], round(float(X["o"][t]), 4), round(a, 6)) for t, a in am],
                                    "手算期末財富": round(W, 6), "主檔": round(float(x["期末財富"]), 6),
                                    "觸發日收盤": round(float(rp), 4), "平均成本": round(float(avg), 4)})
mx = {}
for lbl in MK:
    d = np.array([z["d"] for z in rows if z["標的"] == lbl])
    mx[lbl] = {"筆數": int(len(d)), "期末財富最大差": float(np.nanmax(d[:, 0])), "平均成本差最大差": float(np.nanmax(d[:, 1])),
               "買進後最深再跌最大差": float(np.nanmax(d[:, 2])), "帳面最深最大差": float(np.nanmax(d[:, 3]))}
nmain = int((ref["狀態"] == "ok").sum())
R["K2_手算全部"] = {"各標的": mx, "缺列": diffs, "手算筆數": len(rows), "主檔 ok 列數": nmain,
                 "對": (not diffs) and len(rows) == nmain and all(max(v_["期末財富最大差"], v_["平均成本差最大差"], v_["買進後最深再跌最大差"], v_["帳面最深最大差"]) < 1e-6 for v_ in mx.values())}
R["K3_抽樣（存 us_work，含美股價）"] = "見 ~/us_work/vixentry/check_samples.json"
json.dump(samples, open(os.path.join(WORK, "check_samples.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
R["K3_抽樣_財富絕對差"] = [{"標的": s_["標的"], "d0": s_["d0"], "方式": s_["方式"], "差": abs(s_["手算期末財富"] - s_["主檔"])} for s_ in samples]

# ── K4 真實 vs 合成 SSO（E1）──
a = ref[(ref["方式"] == "E1") & (ref["狀態"] == "ok")]
re_ = a[a["標的"] == "美股 SSO（真實 2 倍）"].set_index(["段起日d0", "持有"])["期末財富"]
sy_ = a[a["標的"] == "美股 合成 SSO（⚠ 合成、非實際 ETF）"].set_index(["段起日d0", "持有"])["期末財富"]
j = pd.concat([re_, sy_], axis=1, keys=["真實", "合成"]).dropna()
R["K4_真實對合成SSO_E1"] = {"重疊格數": int(len(j)), "期末財富差（真實−合成，萬）_中位": float((j["真實"] - j["合成"]).median() * 100),
                         "最大絕對差（萬）": float((j["真實"] - j["合成"]).abs().max() * 100)}

# ── K5 ──
p = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], cwd=os.path.expanduser("~/tw-p17"),
                   capture_output=True, text=True, env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
R["K5_策略鎖"] = {"rc": p.returncode, "尾": (p.stdout + p.stderr).strip().splitlines()[-3:]}
R["全部對"] = R["K1_觸發與回落日"]["對"] and R["K2_手算全部"]["對"] and p.returncode == 0
json.dump(R, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
print(json.dumps(samples, ensure_ascii=False, indent=1))
