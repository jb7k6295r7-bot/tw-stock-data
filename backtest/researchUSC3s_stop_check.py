# -*- coding: utf-8 -*-
"""USREG-C3s 停用條件 seq1 —— 獨立查核（⛔ 不呼叫 researchStopRule／researchUSC3s_ops／K.book／K.rworld 的月底、R、D、狀態機）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC3s_stop_check

另寫：
 X1 日曆 ＝ world.npz 'cal' 直讀；權益 ＝ ~/us_work/c/c3s/c3s_eq_trades.pkl（researchUSC3s 原跑產出、已過 C3s --check X2）；
    基準 ＝ ~/usdata/881c86a yahoo_SP500TR adjclose 直讀、對日曆 ffill（與主檔 K.rworld()["B"] 另比 ≤ 1e−9）。
 X2 月底 ＝ pandas 依年月取最後一個交易日（(a0, w1] 內、且下一交易日換月）；R12、累計差、D 逐月迴圈另算；第 5 百分位自寫線性內插（sorted）。
 X3 狀態機依登錄 §三＋台股 seq2 讀法 ①② 另寫（dict 狀態）；比 levels_monthly.csv 每月 R、D（≤ 1e−9）、判後級、恢復級1。
 X4 x、Dmax 對 stop.json 與寫死常數（≤ 1e−9）；太敏感／太鈍 判語對 stop.json。
 X5 month_level 在前瞻起點前回「未生效」。
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
TOL = 1e-9
OUTD = os.path.expanduser("~/tw-p17/backtest/resultsUSC/C3s/stop")
SEEN = ("2016-12-30", "2026-09-30")


def pctl(v, q):
    a = sorted(v); x = q / 100 * (len(a) - 1); i = int(np.floor(x)); f = x - i
    return a[i] + (a[min(i + 1, len(a) - 1)] - a[i]) * f


def machine(R, D, x, Dm):
    st = {"L": 0, "rec": False, "clock": None, "rc": 0}; out = []
    for r, d in zip(R, D):
        has = r is not None and np.isfinite(r)
        t1 = has and r < x; warn = d <= 0.8 * Dm; stop = d <= Dm
        imp = ((not has) or r >= x) and d > 0.8 * Dm
        rok = ((not has) or r >= 0) and d > 0.8 * Dm
        L = st["L"]
        if L == 0:
            if stop:
                st.update(L=2, rc=0)
            elif t1 or warn:
                st.update(L=1, rec=False, clock=0)
        elif L == 1 and not st["rec"]:
            st["clock"] += 1
            if stop:
                st.update(L=2, rc=0, clock=None)
            elif imp:
                st.update(L=0, clock=None)
            elif st["clock"] >= 3:
                st.update(L=2, rc=0, clock=None)
        elif L == 1:
            if stop:
                st.update(L=2, rec=False, rc=0, clock=None)
            else:
                if st["clock"] is not None:
                    st["clock"] += 1
                    if imp:
                        st["clock"] = None
                    elif st["clock"] >= 3:
                        st.update(L=2, rec=False, rc=0, clock=None)
                elif t1 or warn:
                    st["clock"] = 0
                if st["L"] == 1:
                    st["rc"] = st["rc"] + 1 if rok else 0
                    if st["rc"] >= 6:
                        st.update(L=0, rec=False, rc=0)
        else:
            if stop:
                st["rc"] = 0
            elif rok:
                st["rc"] += 1
                if st["rc"] >= 6:
                    st.update(L=1, rec=True, clock=None, rc=0)
            else:
                st["rc"] = 0
        out.append((st["L"], st["rec"]))
    return out


def main():
    T0 = time.time()
    z = np.load(os.path.expanduser("~/us_work/a4/world.npz"), allow_pickle=False)
    cal = pd.DatetimeIndex(z["cal"])
    eq = np.asarray(pd.read_pickle(os.path.expanduser("~/us_work/c/c3s/c3s_eq_trades.pkl"))["eq"], float)
    tr = pd.read_csv(os.path.expanduser("~/usdata/881c86a/data/macro/yahoo_SP500TR.csv"), dtype={"date": str}).drop_duplicates("date")
    B = pd.Series(pd.to_numeric(tr["adjclose"], errors="coerce").to_numpy(), index=pd.DatetimeIndex(tr["date"])).reindex(cal).ffill().to_numpy(float)
    a0 = int(np.flatnonzero(cal == pd.Timestamp(SEEN[0]))[0]); w1 = int(np.flatnonzero(cal == pd.Timestamp(SEEN[1]))[0])
    diffs = []; nchk = 0
    # 基準對主檔
    from backtest import researchUSC as K
    Bk = K.rworld()["B"]; nchk += 1
    bd = float(np.max(np.abs(B[a0:w1 + 1] / Bk[a0:w1 + 1] - 1)))
    if bd > TOL:
        diffs.append(("基準 對 K.rworld B 相對差", bd))
    # X2 月底
    s = pd.Series(np.arange(len(cal)), index=cal)
    last = s.groupby([cal.year, cal.month]).max().to_numpy()
    MEs = sorted(int(p) for p in last if a0 < p <= w1 and p + 1 < len(cal))
    P = [a0] + MEs
    peak = -np.inf; Dd = {}
    for t in range(a0, w1 + 1):
        peak = max(peak, eq[t]); Dd[t] = eq[t] / peak - 1
    Rv, R12, Dv = [], [], []
    for j in range(1, len(P)):
        if j >= 12:
            r = (eq[P[j]] / eq[P[j - 12]] - 1) - (B[P[j]] / B[P[j - 12]] - 1); R12.append(r); Rv.append(r)
        elif j >= 6:
            Rv.append((eq[P[j]] / eq[P[0]] - 1) - (B[P[j]] / B[P[0]] - 1))
        else:
            Rv.append(None)
        Dv.append(Dd[P[j]])
    x = pctl(R12, 5); Dm = min(Dd.values())
    js = json.load(open(os.path.join(OUTD, "stop.json"), encoding="utf-8"))
    from backtest import researchUSC3s_stop as ST
    for nm, a, b in (("x 對 stop.json", x, js["①"]["x"]), ("Dmax 對 stop.json", Dm, js["①"]["Dmax"]),
                     ("x 對寫死 X_FIX", x, ST.X_FIX), ("Dmax 對寫死 DMAX_FIX", Dm, ST.DMAX_FIX)):
        nchk += 1
        if b is None or abs(a - b) > TOL:
            diffs.append((nm, a, b))
    # X3 狀態機
    lv = machine(Rv, Dv, x, Dm)
    rows = list(csv.DictReader(open(os.path.join(OUTD, "levels_monthly.csv"), encoding="utf-8-sig")))
    nchk += 1
    if len(rows) != len(lv):
        diffs.append(("月底數", len(lv), len(rows)))
    for j, r in enumerate(rows[:len(lv)]):
        nchk += 4
        if r["月底日"] != str(cal[P[j + 1]].date()):
            diffs.append((j, "月底日", r["月底日"], str(cal[P[j + 1]].date())))
        rr = float(r["R"]) if r["R"] else None
        if (rr is None) != (Rv[j] is None) or (rr is not None and abs(rr - Rv[j]) > TOL):
            diffs.append((r["月"], "R", rr, Rv[j]))
        if abs(float(r["D"]) - Dv[j]) > TOL:
            diffs.append((r["月"], "D", r["D"], Dv[j]))
        if int(r["判後級"]) != lv[j][0] or int(r["恢復級1"]) != int(lv[j][1]):
            diffs.append((r["月"], "級", r["判後級"], lv[j]))
    # X4 判語
    prev = [0] + [l for l, _ in lv[:-1]]
    n2 = sum(1 for p_, (l, _) in zip(prev, lv) if l == 2 and p_ != 2)
    mo = [str(cal[p].to_period("M")) for p in MEs]
    q4 = any(l >= 1 for m, (l, _) in zip(mo, lv) if m in ("2018-10", "2018-11", "2018-12"))
    y22 = any(l >= 1 for m, (l, _) in zip(mo, lv) if m.startswith("2022-"))
    V = js["② 歷史驗算（看過段，描述、⛔ 不改條件）"]["判斷"]
    for nm, a, b in (("太敏感", n2 / (len(lv) / 12) > 0.5, V["太敏感"]), ("2018Q4 有級≥1", q4, V["2018Q4 有級≥1"]),
                     ("2022 有級≥1", y22, V["2022 有級≥1"]), ("太鈍", (not q4) and (not y22), V["太鈍"]), ("進級2 次數", n2, V["進級2 次數"])):
        nchk += 1
        if a != b:
            diffs.append((nm, a, b))
    # X5
    nchk += 1
    v = ST.month_level(SEEN[1])
    if v["級別"] is not None:
        diffs.append(("month_level 前瞻起點前應未生效", v))
    out = {"件": "USREG-C3s 停用條件 --check（獨立：月底、R、D、百分位、狀態機另寫）", "比對項數": nchk, "不同": len(diffs),
           "不同明細": [list(map(str, d)) for d in diffs], "容差": TOL, "x": x, "Dmax": Dm, "月底數": len(MEs), "基準對主檔最大相對差": bd,
           "算於": K.now_tpe() + "（台北）", "秒": round(time.time() - T0)}
    json.dump(out, open(os.path.join(OUTD, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
