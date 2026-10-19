# -*- coding: utf-8 -*-
"""researchVIXqld 獨立查核（⛔ 不 import 主檔、researchVIXbuy、researchVIXentry、researchUSC13、researchUSA1_data；美股自讀原始 csv、自寫合成式）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXqld_check

Q1 觸發段：fred_VIXCLS.csv 直讀自算段（段起 ≥ 門檻、段止 ＝ 之後第一個 ≤ 20）；兩個同窗（W1、W2）與各標的全期起點過濾後
   ⇒ 30／50／75 對 resultsUSC13/C13_segments.csv（美股列，段起日 ≥ 起點）逐列相同、40 對 ~/us_work/vixbuy/VIXbuy_events_full.csv 美股列（公開檔已只剩台股）；
   再對主檔 ~/us_work/vixqld/VIXqld_A_events.csv 每個（窗、標的、門檻）的段起日／段止日／買進日逐列相同（買進日自算：市場日期 ＞ VIX 日的第一個有效開盤）。
Q2 合成 QLD 自寫（A1 seq3：2 r_QQQ含息 −（DTB3_{t−1}/100＋0.25%）/252 − 0.95%/252；開 ＝ 前收 ×（1＋2×隔夜跳空））；
   合成 vs 真實 QLD 逐曆年差（2006-06-21 起）自算 ⇒ 對 VIXqld.json「合成vs真實QLD」最大差。
Q3 表 A 手算：A_events 每筆 QLD／合成 QLD／QQQ 的 3 個月～5 年報酬、段內最深、1 年內最深 ⇒ 自寫加月與原始開收重算，最大絕對差（csv 6 位小數）；印 3 筆樣本。
Q4 表 B 手算：B_segments 每筆 QLD／合成 QLD／QQQ 的 E1、E3、E5 期末財富（自寫 DTB3 現金、成本 0.05%）⇒ 最大絕對差；
   另由 B_segments 重算各（窗、標的、持有、方式）期末財富平均 ⇒ 對 VIXqld.json 表B。
Q5 策略鎖 backtest/strategy_lock.py --check。
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
OUT = os.path.expanduser("~/tw-p17/backtest/resultsVIXqld")
WORK = os.path.expanduser("~/us_work/vixqld")
C13 = os.path.expanduser("~/tw-p17/backtest/resultsUSC13/C13_segments.csv")
VBE = os.path.expanduser("~/us_work/vixbuy/VIXbuy_events_full.csv")   # 美股事件已移私有；公開 VIXbuy_events.csv 只剩台股
END = "2026-09-30"; COST = 0.0005
THRS = (30.0, 40.0, 50.0, 75.0)
HM = {3: "3個月", 6: "6個月", 12: "1年", 36: "3年", 60: "5年"}
R = {}


def rd(name):
    return pd.read_csv(os.path.join(MAC, name), dtype=str, keep_default_na=False)


def num(s):
    return pd.to_numeric(pd.Series(s).replace({"": None, ".": None, "null": None}), errors="coerce").to_numpy(float)


def add_months(d, m):
    y, mo, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    k = y * 12 + mo - 1 + m
    y2, mo2 = k // 12, k % 12 + 1
    return f"{y2:04d}-{mo2:02d}-{min(dd, calendar.monthrange(y2, mo2)[1]):02d}"


# ── 原始資料（日曆 ＝ GSPC 日期 ≤ END）──
g = rd("yahoo_GSPC.csv")
cal = sorted(d for d in set(g["date"]) if d <= END)
pos = {d: i for i, d in enumerate(cal)}; n = len(cal)


def adj(name):
    y = rd(name).drop_duplicates("date")
    y = y[y["date"].isin(pos)]
    o = np.full(n, np.nan); c = np.full(n, np.nan)
    k = num(y["adjclose"]) / num(y["close"])
    ix = [pos[d] for d in y["date"]]
    o[ix] = num(y["open"]) * k; c[ix] = num(y["adjclose"])
    bad = ~(np.isfinite(o) & np.isfinite(c) & (o > 0) & (c > 0))
    o[bad] = np.nan; c[bad] = np.nan
    return o, c


QLDo, QLDc = adj("yahoo_QLD.csv")
QQQo, QQQc = adj("yahoo_QQQ.csv")
f = rd("fred_DTB3.csv"); f = f[f["date"] <= END]
fv = dict(zip(f["date"], num(f["value"])))
fd = sorted(d for d, v in fv.items() if np.isfinite(v))
dt = np.array([fv[fd[bisect_right(fd, d) - 1]] if bisect_right(fd, d) else np.nan for d in cal])
gcash = np.zeros(n); gcash[1:] = dt[:-1] / 100 / 252

# Q2 自寫合成 QLD
st = int(np.flatnonzero(np.isfinite(QQQc))[0])
SYc = np.full(n, np.nan); SYo = np.full(n, np.nan); SYc[st] = 1.0
for t in range(st + 1, n):
    r = QQQc[t] / QQQc[t - 1] - 1
    SYc[t] = SYc[t - 1] * (1 + 2 * r - (dt[t - 1] / 100 + 0.0025) / 252 - 0.0095 / 252)
    SYo[t] = SYc[t - 1] * (1 + 2 * (QQQo[t] / QQQc[t - 1] - 1))
SER = {"QLD 真實（那斯達克100 兩倍）": (QLDo, QLDc), "合成 QLD（⚠ 合成、非實際 ETF）": (SYo, SYc), "QQQ（1 倍，含息）": (QQQo, QQQc)}
FIRST = {k: cal[int(np.flatnonzero(np.isfinite(o) & np.isfinite(c))[0])] for k, (o, c) in SER.items()}


def cff(c):
    return pd.Series(c).ffill().to_numpy()


def buy_pos(o, c, d):
    i = bisect_right(cal, d)
    while i < n and not (np.isfinite(o[i]) and np.isfinite(c[i])):
        i += 1
    return i


def last_le(d):
    return bisect_right(cal, d) - 1


# ── Q1 段 ──
vx = rd("fred_VIXCLS.csv"); vx = vx[vx["date"] <= END]
vxv = num(vx["value"]); vxd = vx["date"].to_numpy(str)
vix = [(d, v) for d, v in zip(vxd, vxv) if np.isfinite(v)]


def segs(thr):
    out = []; cur = None
    for d, x in vix:
        if cur is None:
            if x >= thr:
                cur = [d, None]
        elif x <= 20:
            cur[1] = d; out.append(tuple(cur)); cur = None
    if cur:
        out.append((cur[0], "資料末仍 ＞ 20"))
    return out


c13 = pd.read_csv(C13, dtype=str); c13 = c13[c13["市場"] == "美股（^SP500TR）"]
vbe = pd.read_csv(VBE, dtype=str); vbe = vbe[vbe["市場"] == "美股（^SP500TR）"]
AE = pd.read_csv(os.path.join(WORK, "VIXqld_A_events.csv"), dtype=str, keep_default_na=False)
J = json.load(open(os.path.join(OUT, "VIXqld.json"), encoding="utf-8"))
W1 = J["窗"][[k for k in J["窗"] if k.startswith("同窗 W1")][0]]; W2 = J["窗"][[k for k in J["窗"] if k.startswith("同窗 W2")][0]]
mis = []; cnt = {}
for lo in sorted({W1, W2} | set(FIRST.values())):
    for thr in THRS:
        mine = [s for s in segs(thr) if s[0] >= lo]
        cnt[f"{lo}≥{thr:.0f}"] = len(mine)
        ref = c13 if thr != 40.0 else vbe
        ref = ref[(ref["門檻"].astype(float) == thr) & (ref["段起日"] >= lo)]
        if mine != list(zip(ref["段起日"], ref["段止日（VIX≤20）"])):
            mis.append(("C13/VIXbuy", lo, thr))
bad_ae = 0; n_ae = 0
for (w, mk, thr), e in AE.groupby(["窗", "市場", "門檻"]):
    if mk not in SER:
        continue
    lo = W1 if w.startswith("同窗 W1") else (W2 if w.startswith("同窗 W2") else FIRST[mk])
    o, c = SER[mk]
    mine = [(a, b, cal[buy_pos(o, c, a)]) for a, b in segs(float(thr)) if a >= lo]
    n_ae += 1
    if mine != list(zip(e["段起日"], e["段止日（VIX≤20）"], e["買進日"])):
        bad_ae += 1; mis.append(("A_events", w, mk, thr))
R["Q1_觸發段"] = {"段數（起點≥門檻）": cnt, "A_events 組數": n_ae, "不一致": mis, "對": not mis}

# ── Q2 合成 vs 真實 ──
mx_syn = 0.0
i0 = pos[FIRST["QLD 真實（那斯達克100 兩倍）"]]
yd = {}
for y in range(int(cal[i0][:4]), int(END[:4]) + 1):
    a = i0 if y == int(cal[i0][:4]) else last_le(f"{y - 1}-12-31")
    b = last_le(f"{y}-12-31")
    yd[str(y)] = (SYc[b] / SYc[a] - 1) - (QLDc[b] / QLDc[a] - 1)
got = J["合成vs真實QLD"]["逐年差（合成−真實）"]
mx_syn = max(abs(yd[y] - got[y]) for y in yd)
R["Q2_合成vs真實QLD"] = {"逐年差（合成−真實，自算）": {y: round(v, 4) for y, v in yd.items()}, "對主檔最大差": mx_syn,
                       "逐年差絕對值平均": float(np.mean(np.abs(list(yd.values())))), "對": bool(mx_syn < 1e-9)}

# ── Q3 表 A 手算 ──
mx = 0.0; n3 = 0; samp = []
for _, r in AE[AE["市場"].isin(SER)].iterrows():
    if r["買進日"] == "無資料":
        continue
    o, c = SER[r["市場"]]; cf = cff(c); b = pos[r["買進日"]]
    for m, nm in HM.items():
        tg = add_months(r["買進日"], m)
        mine = None if tg > cal[-1] else cf[last_le(tg)] / o[b] - 1
        gv = r[f"報酬_{nm}"]
        if mine is None or gv == "":
            if not (mine is None and gv == ""):
                mx = max(mx, 9.0)
            continue
        n3 += 1; mx = max(mx, abs(mine - float(gv)))
    we = n - 1 if r["段止日（VIX≤20）"].startswith("資料末") else buy_pos(o, c, r["段止日（VIX≤20）"])
    dd = min(0.0, np.nanmin(cf[b:we + 1]) / o[b] - 1)
    tg = add_months(r["買進日"], 12); we1 = n - 1 if tg > cal[-1] else last_le(tg)
    dd1 = min(0.0, np.nanmin(cf[b:we1 + 1]) / o[b] - 1)
    mx = max(mx, abs(dd - float(r["段內最深"])), abs(dd1 - float(r["1年內最深"]))); n3 += 2
    if (r["段起日"], float(r["門檻"])) in {("2008-09-29", 40.0), ("2020-03-12", 75.0), ("2011-08-08", 40.0)} and r["市場"].startswith("QLD") and r["窗"] == "各自全期":
        e = last_le(add_months(r["買進日"], 12))
        samp.append({"門檻": r["門檻"], "段起日": r["段起日"], "買進日": r["買進日"], "買價（還原開）": round(float(o[b]), 4),
                     "1年出場日": cal[e], "出場收（還原）": round(float(cf[e]), 4), "手算1年": round(float(cf[e] / o[b] - 1), 4),
                     "主檔1年": round(float(r["報酬_1年"]), 4), "手算段內最深": round(dd, 4), "主檔段內最深": round(float(r["段內最深"]), 4)})
R["Q3_表A手算"] = {"格數": n3, "最大絕對差（6 位小數存檔）": mx, "對": bool(mx < 6e-6), "樣本（QLD 真實）": samp}

# ── Q4 表 B 手算 ──
BS = pd.read_csv(os.path.join(WORK, "VIXqld_B_segments.csv"), dtype=str, keep_default_na=False)
LB = {"QLD 真實（那斯達克100 兩倍）": "QLD 真實（那斯達克100 兩倍）", "合成 QLD（⚠ 合成、非實際 ETF）": "合成 QLD（⚠ 合成、非實際 ETF）", "QQQ（1 倍，含息）": "QQQ（1 倍，含息）"}
vdate = [d for d, _ in vix]; vval = [v for _, v in vix]
mx4 = 0.0; n4 = 0; bad_day = 0
for _, r in BS[(BS["標的"].isin(LB)) & (BS["狀態"] == "ok") & (BS["方式"].isin(["E1", "E3", "E5"]))].iterrows():
    o, c = SER[r["標的"]]; cf = cff(c)
    d0 = r["段起日d0"]; hm = 12 if r["持有"] == "1年" else 36
    e = last_le(add_months(d0, hm))
    b0 = buy_pos(o, c, d0)
    if r["方式"] == "E1":
        s, bt = b0, b0
    elif r["方式"] == "E5":
        s = bt = buy_pos(o, c, r["E5的≥30段起日"])
    else:
        j = vdate.index(d0)
        j3 = next(k for k in range(j + 1, len(vdate)) if vval[k] < 30)
        s, bt = b0, buy_pos(o, c, vdate[j3])
    if bt <= e:
        cash = float(np.prod(1 + gcash[s:bt]))
        W = cash * (1 - COST) / o[bt] * cf[e]
        bad_day += r["買進日"] != cal[bt]
    else:
        W = float(np.prod(1 + gcash[s:e + 1]))
    n4 += 1; mx4 = max(mx4, abs(W - float(r["期末財富"])))
# 彙總一致
KEY = {"QLD 真實（那斯達克100 兩倍）": "QLD", "合成 QLD（⚠ 合成、非實際 ETF）": "合成QLD", "QQQ（1 倍，含息）": "QQQ",
       "^SP500TR": "SP500TR", "SSO 真實（標普兩倍）": "SSO", "合成 SSO（⚠ 合成、非實際 ETF）": "合成SSO"}
mxs = 0.0; ns = 0
for (w, lbl, h, m), x in BS[BS["狀態"] == "ok"].groupby(["窗", "標的", "持有", "方式"]):
    S = J["表B"][w][KEY[lbl]]["彙總"][h][m]
    mxs = max(mxs, abs(x["期末財富"].astype(float).mean() * 100 - S["期末財富平均（萬）"])); ns += 1
R["Q4_表B手算"] = {"筆數（E1／E3／E5 × QLD／合成QLD／QQQ × 窗 × 持有）": n4, "期末財富最大絕對差": mx4, "買進日不一致": bad_day,
                  "彙總平均對json最大差（萬）": mxs, "彙總格數": ns, "對": bool(mx4 < 2e-6 and bad_day == 0 and mxs < 1e-3)}

# ── Q5 策略鎖 ──
r = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], cwd=os.path.expanduser("~/tw-p17"),
                   capture_output=True, text=True)
R["Q5_策略鎖"] = {"exit": r.returncode, "輸出末行": (r.stdout.strip().splitlines() or [""])[-1][:200], "對": r.returncode == 0}

R["重現（主檔自記）"] = {k: J[k] for k in ("重現_表A_^SP500TR對VIXbuy.json_最大差", "重現_表B_^SP500TR／SSO／合成SSO對VIXentry.json_最大差", "段一致性（lo 起算 ＝ 全歷史過濾）")}
R["總結"] = {k: v["對"] for k, v in R.items() if isinstance(v, dict) and "對" in v}
R["全對"] = all(R["總結"].values())
json.dump(R, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
