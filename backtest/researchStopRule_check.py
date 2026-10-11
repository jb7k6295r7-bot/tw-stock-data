# -*- coding: utf-8 -*-
"""researchStopRule 的獨立查核（回測線計算子代理，2026-10-11）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchStopRule_check [--procs 3]

做法（⛔ 不 import researchStopRule 的任何函式；只共用正式引擎與世界建構）：
  ① 重建兩個世界、重跑引擎（營量 r0、營飆 r0～199），eq_sha 對 resultsYL_integrate/seeds.csv.gz
  ② 月底：逐日比 (年, 月)；版面日曆的最後一天 ⇒ 往後找下一個平日，換月才算月底
  ③ R12、累計差、D：逐月／逐日迴圈；第 5 百分位：自寫線性內插（排序、h ＝ (n−1)×0.05）
  ④ 級別：另寫一份狀態機（狀態名 N／C1／S／R1，規則照登錄＋主程式 S4 讀法）
  ⑤ 比對：x、Dmax（含兩段各自）與 stop_rule.json；levels_monthly.csv 逐列 R、R12、D（差 ≤ 1e−9）、T1／T2 旗標、判後級、恢復級1（全等）
輸出 backtest/resultsStopRule/check.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
from backtest import researchYL_integrate as IG

OUT = "backtest/resultsStopRule"
TOL = 1e-9
KEYS = {"營量 v1": "H60·S20·無·relvol", "營飆 v1": "H120·S10·閘·抽籤"}
_X: dict = {}


def seeds(sn, n):
    return [0] if sn == "營量 v1" else list(range(n))


def work(args):
    wn, sn, r = args
    o, _ = IG.eng(_X[wn], KEYS[sn], r, audit=False)
    return wn, sn, r, np.asarray(o["equity"], float)


def my_month_ends(cal, a, b):
    res = []
    for p in range(a, b + 1):
        d = cal[p]
        if p + 1 < len(cal):
            nd = cal[p + 1]
        else:
            nd = d + dt.timedelta(days=1)
            while nd.weekday() >= 5:
                nd = nd + dt.timedelta(days=1)
        if (nd.year, nd.month) != (d.year, d.month):
            res.append(p)
    return res


def my_pct(vals, q):
    v = sorted(x for x in vals if not math.isnan(x))
    h = (len(v) - 1) * q
    lo = int(math.floor(h)); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (h - lo) * (v[hi] - v[lo])


def my_series(eq, bench, a, b, mes):
    base = [a] + mes
    out = []
    peak = -1.0; mdd = 0.0; dd_at = {}
    for p in range(a, b + 1):
        peak = max(peak, eq[p]); d = eq[p] / peak - 1.0
        mdd = min(mdd, d); dd_at[p] = d
    for j in range(1, len(base)):
        p = base[j]
        r12 = float("nan"); rj = float("nan")
        if j >= 12:
            r12 = (eq[p] / eq[base[j - 12]] - 1.0) - (bench[p] / bench[base[j - 12]] - 1.0); rj = r12
        elif j >= 6:
            rj = (eq[p] / eq[base[0]] - 1.0) - (bench[p] / bench[base[0]] - 1.0)
        out.append((r12, rj, dd_at[p]))
    return out, mdd


def my_levels(ser, x, dmax):
    st = "N"; k = 0; rc = 0; clk = -1
    res = []
    for r12, rj, d in ser:
        has = not math.isnan(rj)
        f_t1 = has and rj < x
        f_w = d <= 0.8 * dmax
        f_s = d <= dmax
        good = (rj >= x if has else True) and d > 0.8 * dmax
        rcv = (rj >= 0 if has else True) and d > 0.8 * dmax
        if st == "N":
            if f_s:
                st, rc = "S", 0
            elif f_t1 or f_w:
                st, k = "C1", 0
        elif st == "C1":
            k += 1
            if f_s:
                st, rc = "S", 0
            elif good:
                st = "N"
            elif k == 3:
                st, rc = "S", 0
        elif st == "S":
            if f_s or not rcv:
                rc = 0
            else:
                rc += 1
                if rc == 6:
                    st, rc, clk = "R1", 0, -1
        else:  # R1
            if f_s:
                st, rc, clk = "S", 0, -1
            else:
                dropped = False
                if clk >= 0:
                    clk += 1
                    if good:
                        clk = -1
                    elif clk == 3:
                        st, rc, clk = "S", 0, -1; dropped = True
                elif f_t1 or f_w:
                    clk = 0
                if not dropped:
                    rc = rc + 1 if rcv else 0
                    if rc == 6:
                        st, rc, clk = "N", 0, -1
        lvl = {"N": 0, "C1": 1, "R1": 1, "S": 2}[st]
        res.append((lvl, int(st == "R1"), int(f_t1), int(f_w), int(f_s)))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    T0 = time.time()
    J = json.load(open(os.path.join(OUT, "stop_rule.json"), encoding="utf-8"))
    LV = pd.read_csv(os.path.join(OUT, "levels_monthly.csv"), float_precision="round_trip")
    nseed = int(J["②"]["營飆 v1"]["顆數"])
    log = lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
    Wm, _ = IG.main_world(log)
    bm = np.asarray(RR._G["bench"], float).copy()
    We, _ = IG.early_world(log, a.procs)
    be = np.asarray(RR.load_bench(We["cal"]), float)
    _X.update({"主": Wm, "早年": We})
    BEN = {"主": bm, "早年": be}
    jobs = [(wn, sn, r) for wn in ("早年", "主") for sn in KEYS for r in seeds(sn, nseed)]
    with Pool(a.procs) as pool:
        res = pool.map(work, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    nd = {"eq_sha 不同": sum(int(hashlib.sha256(eq.tobytes()).hexdigest()[:16] != REF[(wn, KEYS[sn], r)]) for wn, sn, r, eq in res)}
    EQ = {(wn, sn, r): eq for wn, sn, r, eq in res}
    MES = {wn: my_month_ends(W["cal"], W["w0"], W["w1"]) for wn, W in _X.items()}
    SER = {}; MDD = {}
    for key, eq in EQ.items():
        W = _X[key[0]]
        SER[key], MDD[key] = my_series(eq, BEN[key[0]], W["w0"], W["w1"], MES[key[0]])
    diffs = {}
    for sn in KEYS:
        xs, xe, xm, de, dm, dx = [], [], [], [], [], []
        for r in seeds(sn, nseed):
            e12 = [s[0] for s in SER[("早年", sn, r)]]; m12 = [s[0] for s in SER[("主", sn, r)]]
            xs.append(my_pct(e12 + m12, 0.05)); xe.append(my_pct(e12, 0.05)); xm.append(my_pct(m12, 0.05))
            de.append(MDD[("早年", sn, r)]); dm.append(MDD[("主", sn, r)]); dx.append(min(MDD[("早年", sn, r)], MDD[("主", sn, r)]))
        med = lambda v: float(np.median(v))
        mine = {"x": med(xs), "x_早年段": med(xe), "x_主窗段": med(xm), "Dmax": med(dx), "Dmax_早年段": med(de), "Dmax_主窗段": med(dm)}
        for k, v in mine.items():
            d = abs(v - J["①"][sn][k]); diffs[f"{sn} {k}"] = d
        nd[f"{sn} x／Dmax 差 ＞ 1e−9（項數）"] = int(sum(abs(v - J["①"][sn][k]) > TOL for k, v in mine.items()))
        # 級別
        x, Dm = J["①"][sn]["x"], J["①"][sn]["Dmax"]
        bad_num = bad_lvl = rows = 0
        for r in seeds(sn, nseed):
            for wn in ("早年", "主"):
                ser = SER[(wn, sn, r)]; lv = my_levels(ser, x, Dm)
                g = LV[(LV["策略"] == sn) & (LV["r"] == r) & (LV["段"] == wn)].sort_values("月序")
                if len(g) != len(ser):
                    bad_lvl += abs(len(g) - len(ser)) + 1; continue
                for (r12, rj, d), (lvl, rec, t1, w, s), (_, row) in zip(ser, lv, g.iterrows()):
                    rows += 1
                    for mv, cv in ((r12, row["R12"]), (rj, row["R"]), (d, row["D"])):
                        if (math.isnan(mv) != (cv != cv)) or (not math.isnan(mv) and abs(mv - cv) > TOL):
                            bad_num += 1
                    if (lvl, rec, t1, w, s) != (int(row["判後級"]), int(row["恢復級1"]), int(row["T1"]), int(row["T2警戒"]), int(row["T2停用"])):
                        bad_lvl += 1
        nd[f"{sn} R／R12／D 差 ＞ 1e−9（列×欄）"] = bad_num
        nd[f"{sn} 級別／旗標不同（列）"] = bad_lvl
        nd[f"{sn} 比對列數"] = rows
    passed = all(v == 0 for k, v in nd.items() if "比對列數" not in k)
    out = {"不同": nd, "x／Dmax 最大差": max(diffs.values()), "差明細": diffs, "月底數": {wn: len(v) for wn, v in MES.items()},
           "全過": passed, "耗時秒": round(time.time() - T0)}
    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"[check] {json.dumps(out, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
