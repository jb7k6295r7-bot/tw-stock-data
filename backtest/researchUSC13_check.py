# -*- coding: utf-8 -*-
"""USREG-C13 獨立查核（researchUSC13.py 的對帳；⛔ 不 import 主檔的計算函式，只讀它的輸出與同一份原始檔）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC13_check

K1 登錄全文 sha（去 pw1 行）＝ d72fc2fdccf2c4c0
K2 觸發段手算：csv 模組直讀 fred_VIXCLS.csv（≤ 2026-09-30、丟 "."）⇒ 段起／段止日與 C13_segments.csv 逐列相同
K3 起點觸發手算：自建 ^GSPC 日曆的每月第一個交易日 ⇒ 各層「第一個 VIX 日 ≥ 起點、收盤 ≥ 門檻、次一交易日買進在窗內」計數 ＝ C13_trigger_used.csv
K4 時差不前視：台股每個買進日 ＞ VIX 日期 d，且 d 與買進日之間沒有任何 0050 K 棒日（＝ d＋1 含之後第一個）；美股買進日 ＝ ^GSPC 日曆上 d 之後第一日
K5 抽樣起點手算：封閉式（各份 w_k × 現金指數成長 ÷ 開盤 × (1−成本) × 期末收盤 ＋ 未用份 × 現金成長）重算 V／L／D 期末財富與 V 閒置比例，對主檔逐起點值
K6 DTB3 計息驗算：自讀 fred_DTB3.csv、前值填補、g_t ＝ DTB3_{t−1}/100/252 ⇒ 現金指數對 researchUSA1_data.load_market 全期最大相對差；一年期手算
K7 判語重算：由起點表重算中位差、贏的比例、月分群 Bonferroni CI 與判語，對 C13.json
K8 VIX 休市日列（2022 起 34 列）拿掉 ⇒ 觸發會改的起點數
K9 策略鎖 backtest/strategy_lock.py --check
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
from bisect import bisect_left, bisect_right
from collections import Counter
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/usdata/60d2f99/data/macro")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSC13")
WORK = os.path.expanduser("~/us_work/usc13")
REGF = "/mnt/c/SynologyDrive/跨線信箱/登錄全文-USREG-C13_VIX分層進場_seq1_美股策略線_shad72fc2fdccf2c4c0-3535B-20261019-2234.md"
END = "2026-09-30"
THR = (30.0, 50.0, 75.0); W = (0.2, 0.3, 0.5)
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


# K1
lines = io.open(REGF, encoding="utf-8").read().splitlines(keepends=True)
h = hashlib.sha256("".join(l for l in lines if "pw1" not in l).encode("utf-8")).hexdigest()[:16]
R["K1_登錄sha"] = {"值": h, "對": h == "d72fc2fdccf2c4c0", "位元組": os.path.getsize(REGF)}

# 原始資料
vix = [(r["date"], fnum(r["value"])) for r in rd("fred_VIXCLS.csv") if r["date"] <= END]
vix = [(d, v) for d, v in vix if v is not None]
vd = [d for d, _ in vix]; vv = [v for _, v in vix]
gs = {r["date"]: r for r in rd("yahoo_GSPC.csv") if r["date"] <= END}
tr = {r["date"]: r for r in rd("yahoo_SP500TR.csv") if r["date"] <= END}
cal = sorted(gs)
n = len(cal)
O = np.full(n, np.nan); Cc = np.full(n, np.nan)
for i, d in enumerate(cal):
    t = tr.get(d); g = gs[d]
    if t is None:
        continue
    tc, go, gc = fnum(t["adjclose"]), fnum(g["open"]), fnum(g["close"])
    if tc and gc:
        Cc[i] = tc
        if go:
            O[i] = go * tc / gc
Cf = pd.Series(Cc).ffill().to_numpy()
# DTB3
dt = sorted((r["date"], fnum(r["value"])) for r in rd("fred_DTB3.csv") if r["date"] <= END)
dtv = [(d, v) for d, v in dt if v is not None]
dd_ = [d for d, _ in dtv]
lvl = np.array([dtv[bisect_right(dd_, d) - 1][1] if bisect_right(dd_, d) > 0 else np.nan for d in cal])
g = np.zeros(n); g[1:] = lvl[:-1] / 100.0 / 252.0
CI = np.cumprod(1.0 + g)

# K6
import sys
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSA1_data as A
M = A.load_market()
ci_main = np.cumprod(1.0 + M["cash_g"])
assert list(M["cal"]) == cal, "日曆不同"
i90 = cal.index("1990-02-01"); j90 = cal.index("1991-01-31")
hand = 1.0
for t in range(i90 + 1, j90 + 1):
    hand *= 1.0 + lvl[t - 1] / 100.0 / 252.0
R["K6_DTB3計息"] = {"全期現金指數最大相對差": float(np.max(np.abs(CI / ci_main - 1))),
                   "手算 1990-02-01 收→1991-01-31 收 現金成長": hand, "主檔同段": float(ci_main[j90] / ci_main[i90]),
                   "同段 DTB3 平均（%）": float(np.mean(lvl[i90:j90])), "同段交易日": j90 - i90,
                   "對": bool(np.max(np.abs(CI / ci_main - 1)) < 1e-12 and abs(hand / (ci_main[j90] / ci_main[i90]) - 1) < 1e-12)}

# K2 段
def segs(lo=None):
    out = {}
    for thr in THR:
        rows = []; cur = None
        for d, v in vix:
            if lo and d < lo:
                continue
            if cur is None and v >= thr:
                cur = [d, None]
            elif cur is not None and v <= 20.0:
                cur[1] = d; rows.append(tuple(cur)); cur = None
        if cur is not None:
            rows.append((cur[0], "資料末仍 ＞ 20"))
        out[thr] = rows
    return out


S = pd.read_csv(os.path.join(OUT, "C13_segments.csv"), dtype=str)
okseg = True; segn = {}
for mkt, lo in (("美股（^SP500TR）", None), ("台股（0050）", "2003-06-30")):
    mine = segs(lo)
    for thr in THR:
        x = S[(S["市場"] == mkt) & (S["門檻"].astype(float) == thr)]
        got = list(zip(x["段起日"], x["段止日（VIX≤20）"]))
        okseg &= got == mine[thr]
        segn[f"{mkt}≥{thr:.0f}"] = len(mine[thr])
R["K2_觸發段手算"] = {"段數": segn, "逐列相同": bool(okseg),
                   "段起日（美股）": {f"≥{t:.0f}": [a for a, _ in segs()[t]] for t in THR}}

# K3 起點觸發計數（美股 10 年）
first, last = {}, {}
for i, d in enumerate(cal):
    k = int(d[:4]) * 12 + int(d[5:7]) - 1
    first.setdefault(k, i); last[k] = i


def nxt_us(d):
    i = bisect_right(cal, d)
    while i < n and not np.isfinite(O[i]):
        i += 1
    return i


def first_trig(sdate, thr, e, vlist):
    j = bisect_left([a for a, _ in vlist], sdate)
    for d, v in vlist[j:]:
        b = nxt_us(d)
        if b > e:
            return None
        if v >= thr:
            return d, b
    return None


cnt = Counter(); starts = []
for k in range(1990 * 12 + 1, 2016 * 12 + 9):
    s = first[k]; e = last[k + 119]
    if (k + 120) not in first:
        continue
    starts.append((k, s, e))
    for ti, thr in enumerate(THR):
        r = first_trig(cal[s], thr, e, vix)
        if r:
            cnt[(ti + 1, r[0])] += 1
U = pd.read_csv(os.path.join(OUT, "C13_trigger_used.csv"), dtype={"VIX日期": str})
u = U[U["窗"] == "美股10年"]
theirs = Counter({(int(a), b): int(c) for a, b, c in zip(u["層"], u["VIX日期"], u["用到的起點數"])})
R["K3_起點觸發計數"] = {"起點數": len(starts), "與 C13_trigger_used.csv 相同": cnt == theirs,
                    "各層觸發起點數": {f"層{t}": sum(c for (a, _), c in cnt.items() if a == t) for t in (1, 2, 3)}}

# K8 拿掉休市日列
calset = set(cal)
vix_nh = [(d, v) for d, v in vix if d in calset]
chg = 0
for k, s, e in starts:
    for thr in THR:
        if first_trig(cal[s], thr, e, vix) != first_trig(cal[s], thr, e, vix_nh):
            chg += 1; break
R["K8_休市日VIX列"] = {"列數": len(vix) - len(vix_nh), "拿掉後觸發改變的美股10年起點數": chg}

# K4 時差（台股）
from backtest import researchRev as RV
_, spl, _ = RV.market_series()
tw_d = [str(x) for x in np.asarray(spl["dates"])[spl["valid"]]]
tw_o = np.asarray(spl["o"], float)[spl["valid"]]; tw_c = np.asarray(spl["c"], float)[spl["valid"]]
bad = 0; chk = 0
for _, row in S.iterrows():
    if row["買進日"] == "無資料":
        continue
    d, b = row["段起日"], row["買進日"]
    if row["市場"].startswith("台股"):
        chk += 1
        i = bisect_right(tw_d, d)
        bad += not (b > d and tw_d[i] == b)
    else:
        chk += 1
        bad += not (b == cal[nxt_us(d)])
used_tw = U[U["窗"] == "台股10年"]
for d in used_tw["VIX日期"]:
    i = bisect_right(tw_d, d); chk += 1
    bad += not (tw_d[i] > d and (i == 0 or tw_d[i - 1] <= d))
R["K4_時差不前視"] = {"檢查筆數": chk, "違反": int(bad), "例：2018-12-21（美五）⇒ 台股買進日": tw_d[bisect_right(tw_d, "2018-12-21")],
                  "例：2020-02-27（美四）⇒ 台股買進日": tw_d[bisect_right(tw_d, "2020-02-27")]}

# K5 抽樣起點封閉式重算
D10 = pd.read_pickle(os.path.join(WORK, "c13_starts_US10.pkl")).set_index("起點")
T10 = pd.read_pickle(os.path.join(WORK, "c13_starts_TW10.pkl")).set_index("起點")
rng = np.random.default_rng(20261020)
pick_us = sorted(set(["2000-03", "2007-10", "2008-10", "1990-02", "2016-09"]) | set(rng.choice(D10.index.to_numpy(), 5, replace=False)))
pick_tw = sorted(set(["2007-10", "2008-10", "2016-09", "2004-03"]) | set(rng.choice(T10.index.to_numpy(), 4, replace=False)))


def closed_form(o, cf, ci, s, e, buys, cost, w):
    """buys：各份 (買進位置 或 None)；w：各份比例。"""
    V = 0.0; inv = []
    for bk, wk in zip(buys, w):
        if bk is None:
            V += wk * ci[e] / ci[s - 1]
        else:
            amt = wk * ci[bk - 1] / ci[s - 1]
            V += amt * (1 - cost) / o[bk] * cf[e]; inv.append(amt)
    return V


def idle_closed(o, cf, ci, s, e, buys, cost, w):
    tot = 0.0
    for t in range(s, e + 1):
        cash = sum(wk * ci[t] / ci[s - 1] for bk, wk in zip(buys, w) if bk is None or bk > t)
        stk = sum(wk * ci[bk - 1] / ci[s - 1] * (1 - cost) / o[bk] * cf[t] for bk, wk in zip(buys, w) if bk is not None and bk <= t)
        tot += cash / (cash + stk)
    return tot / (e - s + 1)


rows5 = []; mx = 0.0
for st in pick_us:
    k = int(st[:4]) * 12 + int(st[5:7]) - 1; s = first[k]; e = last[k + 119]
    bk = []
    for thr in THR:
        r = first_trig(cal[s], thr, e, vix); bk.append(r[1] if r else None)
    v = closed_form(O, Cf, CI, s, e, bk, 0.0005, W)
    l_ = closed_form(O, Cf, CI, s, e, [s], 0.0005, [1.0])
    db = [first[k + i] for i in range(12)]
    d_ = closed_form(O, Cf, CI, s, e, db, 0.0005, [1 / 12] * 12)
    idl = idle_closed(O, Cf, CI, s, e, bk, 0.0005, W)
    rec = D10.loc[st]
    dif = max(abs(v - rec["W_V"]), abs(l_ - rec["W_L"]), abs(d_ - rec["W_D"]), abs(idl - rec["閒置_V"]))
    mx = max(mx, dif)
    rows5.append({"市場": "美股", "起點": st, "各層買進日": [cal[b] if b is not None else "窗內沒觸發" for b in bk],
                  "各層投入（萬，含等待利息）": [round(wk * CI[b - 1] / CI[s - 1] * 100, 3) if b is not None else None for b, wk in zip(bk, W)],
                  "V−L（萬）手算": round((v - l_) * 100, 4), "V−L（萬）主檔": round((rec["W_V"] - rec["W_L"]) * 100, 4), "最大絕對差": dif})
ci1 = np.ones(len(tw_d))
twf, twl = {}, {}
for i, d in enumerate(tw_d):
    k = int(d[:4]) * 12 + int(d[5:7]) - 1
    twf.setdefault(k, i); twl[k] = i
for st in pick_tw:
    k = int(st[:4]) * 12 + int(st[5:7]) - 1; s = twf[k]; e = twl[k + 119]
    bk = []
    for thr in THR:
        j = bisect_left(vd, tw_d[s]); b = None
        for jj in range(j, len(vd)):
            bb = bisect_right(tw_d, vd[jj])
            if bb > e:
                break
            if vv[jj] >= thr:
                b = bb; break
        bk.append(b)
    v = closed_form(tw_o, tw_c, ci1, s, e, bk, 0.001425, W)
    l_ = closed_form(tw_o, tw_c, ci1, s, e, [s], 0.001425, [1.0])
    d_ = closed_form(tw_o, tw_c, ci1, s, e, [twf[k + i] for i in range(12)], 0.001425, [1 / 12] * 12)
    idl = idle_closed(tw_o, tw_c, ci1, s, e, bk, 0.001425, W)
    rec = T10.loc[st]
    dif = max(abs(v - rec["W_V"]), abs(l_ - rec["W_L"]), abs(d_ - rec["W_D"]), abs(idl - rec["閒置_V"]))
    mx = max(mx, dif)
    rows5.append({"市場": "台股", "起點": st, "各層買進日": [tw_d[b] if b is not None else "窗內沒觸發" for b in bk],
                  "各層投入（萬，0 利率）": [wk * 100 if b is not None else None for b, wk in zip(bk, W)],
                  "V−L（萬）手算": round((v - l_) * 100, 4), "V−L（萬）主檔": round((rec["W_V"] - rec["W_L"]) * 100, 4), "最大絕對差": dif})
R["K5_抽樣起點手算"] = {"起點": rows5, "全部最大絕對差（財富單位 1.0＝100 萬）": mx, "對": bool(mx < 1e-9)}

# K7 判語重算
J = json.load(open(os.path.join(OUT, "C13.json"), encoding="utf-8"))
z = NormalDist().inv_cdf(1 - 0.05 / 4)
D10r = D10.reset_index()
x = (D10r["W_V"] - D10r["W_L"]).to_numpy() * 100
p = float((x > 0).mean()); se = float(np.sqrt((((x > 0) - p) ** 2).sum()) / len(x))
lab = "方向一致（贏）" if (np.median(x) > 0 and p - z * se > 0.5) else ("方向一致（輸）" if (np.median(x) < 0 and p + z * se < 0.5) else "分不出")
jm = J["主臂_美股10年"]["對L（主比較，判定）"]
R["K7_判語重算"] = {"中位差（萬）": float(np.median(x)), "贏的比例": p, "CI": [p - z * se, p + z * se], "判語": lab,
                  "對": bool(abs(np.median(x) - jm["中位差（萬）"]) < 1e-9 and abs(p - jm["V贏的起點比例"]) < 1e-12 and lab == jm["判語（月分群）"]),
                  "層3從沒觸發比例": float(1 - D10r["層3觸發"].mean())}

# K9 策略鎖
r = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], cwd=os.path.expanduser("~/tw-p17"),
                   capture_output=True, text=True)
R["K9_策略鎖"] = {"exit": r.returncode, "輸出末行": (r.stdout.strip().splitlines() or [""])[-1][:200]}

R["總結"] = {k: v.get("對", v.get("與 C13_trigger_used.csv 相同", v.get("逐列相同"))) for k, v in R.items() if isinstance(v, dict)}
R["總結"]["K4_違反0"] = R["K4_時差不前視"]["違反"] == 0
R["總結"]["K9_策略鎖exit0"] = R["K9_策略鎖"]["exit"] == 0


def cv(o):
    if isinstance(o, dict):
        return {str(k): cv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [cv(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    return o


json.dump(cv(R), open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(cv(R), ensure_ascii=False, indent=1))
