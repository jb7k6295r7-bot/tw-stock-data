# -*- coding: utf-8 -*-
"""USREG-T1 獨立重算（回測線計算子代理，2026-10-17）：⛔ 不 import researchUST1、data、research11；只讀原始 CSV 自己算。
重算：P 序列（含排除旗標）、Z60、去重事件、甲 主格（H20／H5 每窗每方向的平均、月分群 SE、CI）、乙 主格（每窗年化、回落、比值、進場次數、平均持有天數）
⇒ 與 backtest/resultsUST1/ 與 ~/us_work/t1/premium_daily.csv 逐項比，最大差 ≤ 1e−9 才過。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUST1_check
"""
from __future__ import annotations

import os
import sys
from collections import deque

import numpy as np
import pandas as pd

TOL = 1e-9
USM = os.path.expanduser("~/us-stock-data/data/macro")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUST1")
DAILY = os.path.expanduser("~/us_work/t1/premium_daily.csv")
DIRS = {"早年": os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data"),
        "主": os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")}
WINS = {"早年": ("2005-02-01", "2014-12-31", "早年"), "主窗": ("2017-03-02", "2026-08-24", "主"),
        "探索": ("2017-03-02", "2021-12-30", "主"), "確認": ("2022-01-03", "2026-08-24", "主")}
BUYC, S_STK, S_ETF = 0.001425, 0.004425, 0.002425


def raw_px(d, sid):
    x = pd.read_csv(os.path.join(d, "stocks", f"{sid}.csv"), dtype={"date": str})
    x["date"] = pd.to_datetime(x["date"])
    x = x.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "close"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
        x.loc[x[c] <= 0, c] = np.nan
    return x


def factor(d, sid, dates):
    a = pd.read_csv(os.path.join(d, "adj", f"{sid}.csv"), dtype={"date": str})
    a["date"] = pd.to_datetime(a["date"]); a = a.sort_values("date")
    out = np.ones(len(dates))
    for i, t in enumerate(dates):
        later = a[a["date"] > t]
        if len(later):
            out[i] = float(later["cum_factor"].iloc[0])
    return out, a


def world(wn):
    d = DIRS[wn]
    cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(d, "meta", "calendar_twse.csv"))["date"])).sort_values()
    s = raw_px(d, "2330").reindex(cal); e = raw_px(d, "0050").reindex(cal)
    f2, a2 = factor(d, "2330", cal); f5, _ = factor(d, "0050", cal)
    traded = s["close"].notna().to_numpy()
    # 缺口 ≥ 5 交易日（seq335）、相鄰有效收盤比 ≤0.55／≥1.8 且無 adj 事件 ⇒ 壞根；本件 2330 應為 0
    idx = np.flatnonzero(traded)
    gaps = np.diff(idx) - 1
    if (gaps >= 5).any():
        raise SystemExit(f"⛔ {wn} 2330 有缺口 ≥5：{cal[idx[1:][gaps >= 5]]}")
    rc = s["close"].to_numpy(float)
    C2 = pd.Series(rc * f2).ffill().to_numpy(); O2 = s["open"].to_numpy(float) * f2
    BC = pd.Series(e["close"].to_numpy(float) * f5).ffill().to_numpy()
    BO = e["open"].to_numpy(float) * f5
    bad = ~np.isfinite(BO)
    BO[bad] = np.r_[np.nan, BC[:-1]][bad]
    evd = [t for t in a2["date"] if cal[0] < t <= cal[-1]]
    return {"cal": cal, "rc": rc, "C2": C2, "O2": O2, "BC": BC, "BO": BO, "ev": evd}


def main():
    bad = []
    def chk(name, a, b):
        a = np.asarray(a, float); b = np.asarray(b, float)
        if a.shape != b.shape:
            bad.append(f"{name} 形狀 {a.shape} vs {b.shape}"); print(f"✘ {name} 形狀不同"); return
        both_nan = np.isnan(a) & np.isnan(b)
        if ((np.isnan(a) | np.isnan(b)) & ~both_nan).any():
            bad.append(f"{name} 缺值位置不同"); print(f"✘ {name} 缺值位置不同"); return
        m = float(np.nanmax(np.abs(a - b))) if (~both_nan).any() else 0.0
        print(f"{'✔' if m <= TOL else '✘'} {name}：最大差 {m:.3e}（{int((~both_nan).sum())} 個）")
        if m > TOL:
            bad.append(f"{name} {m}")
    W = {k: world(k) for k in ("早年", "主")}
    cal = W["早年"]["cal"].append(W["主"]["cal"]); N = len(cal)
    rc = np.r_[W["早年"]["rc"], W["主"]["rc"]]
    # TSM 未調整：反向累乘
    t = pd.read_csv(os.path.join(USM, "yahoo_TSM.csv")); t["date"] = pd.to_datetime(t["date"]); t = t.sort_values("date").reset_index(drop=True)
    ev = pd.read_csv(os.path.join(USM, "yahoo_events_TSM.csv")); ev["date"] = pd.to_datetime(ev["date"])
    spl = ev[ev["type"] == "split"].sort_values("date", ascending=False)
    f = pd.Series(1.0, index=t.index)
    acc = 1.0; cut = []
    for d, v in zip(spl["date"], spl["value"]):
        nu, de = v.split("/"); cut.append((d, float(nu) / float(de)))
    unadj = t["close"].to_numpy(float).copy()
    for i, dt in enumerate(t["date"]):
        m = 1.0
        for d, r in cut:
            if d > dt:
                m *= r
        unadj[i] *= m
    us = pd.DataFrame({"usd": t["date"], "px": unadj})
    tw = pd.DataFrame({"tw": cal, "twm": cal - pd.Timedelta(seconds=1)})
    mg = pd.merge_asof(tw, us, left_on="twm", right_on="usd", direction="backward")     # 美東日期 ＜ t
    fx = pd.read_csv(os.path.join(USM, "cbc_BP01D01_NTD.csv")); fx["date"] = pd.to_datetime(fx["date"]); fx = fx.dropna().sort_values("date")
    mg = pd.merge_asof(mg, fx.rename(columns={"date": "fxd"}), left_on="tw", right_on="fxd", direction="backward")
    P = mg["px"].to_numpy() / 5.0 * mg["ntd_per_usd"].to_numpy() / rc - 1.0
    # 排除
    ex = np.zeros(N, bool); usdates = mg["usd"].to_numpy()
    pos_list = []
    for wn in ("早年", "主"):
        for d in W[wn]["ev"]:
            pos_list.append(int(np.argmax(cal.to_numpy() >= np.datetime64(d))))
    for d in ev["date"]:
        if d <= mg["usd"].iloc[0]:
            continue
        hit = np.flatnonzero(usdates >= np.datetime64(d))
        if len(hit):
            pos_list.append(int(hit[0]))
    for p in pos_list:
        ex[max(0, p - 3):p + 4] = True
    Pv = np.where(ex, np.nan, P)
    # Z60（deque）
    Z = np.full(N, np.nan); q = deque()
    for i in range(N):
        if not np.isfinite(Pv[i]):
            continue
        if len(q) == 60:
            arr = np.array(q); Z[i] = (Pv[i] - arr.mean()) / arr.std(ddof=1)
        q.append(Pv[i])
        if len(q) > 60:
            q.popleft()
    D0 = pd.read_csv(DAILY)
    if list(D0["date"]) != [str(x.date()) for x in cal]:
        bad.append("逐日日期不同"); print("✘ 逐日日期不同")
    chk("P", P, D0["P"]); chk("排除旗標", ex.astype(float), D0["excluded"]); chk("Z60", Z, D0["Z60"])
    # 事件
    EVm = pd.read_csv(os.path.join(OUT, "events.csv"))
    EVm = EVm[EVm["設定"] == "主 Z60±2"]
    evs = {}
    for dn, sg in (("高", 1), ("低", -1)):
        last = -999; L = []
        for i in range(N):
            if np.isfinite(Z[i]) and ((Z[i] >= 2) if sg > 0 else (Z[i] <= -2)) and i - last >= 20:
                L.append(i); last = i
        evs[dn] = L
        mine = [str(cal[i].date()) for i in L]; theirs = list(EVm[EVm["方向"] == dn]["日期"])
        ok = mine == theirs
        print(f"{'✔' if ok else '✘'} 事件 {dn}：{len(mine)} vs {len(theirs)}")
        if not ok:
            bad.append(f"事件 {dn} 不同")
    # 甲
    nE = len(W["早年"]["cal"])
    def out1(i, H):
        wn = "早年" if i < nE else "主"; w = W[wn]; k = i if wn == "早年" else i - nE
        e = k + 1; x = k + H
        if x >= len(w["cal"]) or not np.isfinite(w["O2"][e]):
            return None
        return wn, x, (w["C2"][x] / w["O2"][e] - 1) - (w["BC"][x] / w["BO"][e] - 1)
    Cm = pd.read_csv(os.path.join(OUT, "cells.csv")); Cm = Cm[Cm["設定"] == "主 Z60±2"]
    for wname, (a, b, wn0) in WINS.items():
        for dn in ("高", "低"):
            for H in (20, 5):
                xs, gs = [], []
                for i in evs[dn]:
                    if not (a <= str(cal[i].date()) <= b):
                        continue
                    o = out1(i, H)
                    if o is None:
                        continue
                    wn, x, v = o
                    if str(W[wn]["cal"][x].date()) > b:
                        continue
                    xs.append(v); gs.append(str(cal[i].date())[:7])
                xs = np.array(xs); n = len(xs); mu = xs.mean()
                sums = pd.Series(xs - mu).groupby(np.array(gs)).sum().to_numpy(); G = len(sums)
                se = np.sqrt(G / (G - 1) * (sums ** 2).sum()) / n
                r = Cm[(Cm["窗"] == wname) & (Cm["方向"] == dn) & (Cm["H"] == H)].iloc[0]
                if int(r["n"]) != n or int(r["G"]) != G:
                    bad.append(f"甲 {wname}{dn}H{H} n/G"); print(f"✘ 甲 {wname} {dn} H{H} n {n}/{r['n']} G {G}/{r['G']}")
                chk(f"甲 {wname} {dn} H{H} 平均／se／97.5%CI", [mu, se, mu - 2.241403 * se, mu + 2.241403 * se], [r["平均"], r["se"], r["lo975"], r["hi975"]])
    # 乙（逐日持股數模擬）
    Pm = pd.read_csv(os.path.join(OUT, "portfolio.csv"))
    for wname, (a, b, wn) in WINS.items():
        w = W[wn]; off = 0 if wn == "早年" else nE; c = w["cal"]
        x0 = int(np.flatnonzero(c >= pd.Timestamp(a))[0]); y0 = int(np.flatnonzero(c <= pd.Timestamp(b))[-1])
        u50 = 1.0 / w["BC"][x0]; u23 = 0.0; hold = False; pend = None; eq = []; nent = 0; lens = []; e0 = None
        for k in range(x0, y0 + 1):
            if pend == "in":
                v = u50 * w["BO"][k] * (1 - S_ETF) * (1 - BUYC); u23 = v / w["O2"][k]; u50 = 0.0; hold = True; nent += 1; e0 = k
            elif pend == "out":
                v = u23 * w["O2"][k] * (1 - S_STK) * (1 - BUYC); u50 = v / w["BO"][k]; u23 = 0.0; hold = False; lens.append(k - e0)
            pend = None
            val = u50 * w["BC"][k] + u23 * w["C2"][k]
            if k == y0 and hold:
                val *= (1 - S_STK) * (1 - BUYC); lens.append(k + 1 - e0)
            eq.append(val)
            if k < y0:
                z = Z[off + k]
                if np.isfinite(z):
                    if not hold and z >= 2:
                        pend = "in"
                    elif hold and z <= 0:
                        pend = "out"
        eq = np.array(eq) / eq[0]
        cagr = (eq[-1] / eq[0]) ** (245 / len(eq)) - 1
        mdd = float(((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min())
        r = Pm[(Pm["窗"] == wname) & Pm["設定"].str.startswith("主 乙")].iloc[0]
        if int(r["進場次數"]) != nent:
            bad.append(f"乙 {wname} 進場次數"); print(f"✘ 乙 {wname} 進場次數 {nent} vs {r['進場次數']}")
        chk(f"乙 {wname} 年化／回落／比值／平均持有", [cagr, mdd, cagr / abs(mdd), np.mean(lens)], [r["年化"], r["最大回落"], r["比值"], r["平均持有天數"]])
        bc = w["BC"][x0:y0 + 1] / w["BC"][x0]
        bcg = (bc[-1]) ** (245 / len(bc)) - 1; bmd = float(((bc - np.maximum.accumulate(bc)) / np.maximum.accumulate(bc)).min())
        chk(f"乙 {wname} 0050 年化／回落", [bcg, bmd], [r["0050年化"], r["0050最大回落"]])
    print("══ 全部通過 ══" if not bad else f"══ ✘ {len(bad)} 項不過：{bad} ══")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
