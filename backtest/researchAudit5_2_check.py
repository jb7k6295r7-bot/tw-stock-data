# -*- coding: utf-8 -*-
"""researchAudit5_2 的獨立查核（⛔ 不 import researchAudit5_2、⛔ 不呼叫 research5 的出場函式）：
① 自己照 PREREG4 §二 文字寫固定持有與三類停損（收盤跌破 ⇒ 次日第一個有開盤的日子開盤出；時間上限到期走固定持有；
   固定持有出場日缺收盤或鎖跌停 ⇒ 順延 ≤ 10 日，仍不行 ⇒ 期間最後有收盤那天），抽 --n 筆進場、全部 30 條腿 ⇒ 對 legs.csv.gz
② 從 legs.csv.gz 自己算每個配對（非重疊 60 日、SE、前後段、判定）⇒ 對 pairs.csv（研究五與研究六的主版全部列）
⇒ check.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import patterns as P

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit5/2")
COST = 0.00585
STOPS = [("S5", "stop", 0.05), ("S8", "stop", 0.08), ("S10", "stop", 0.10), ("S15", "stop", 0.15), ("T10", "trail", 0.10), ("T20", "trail", 0.20),
         ("A1.5", "atr", 1.5), ("A2", "atr", 2.0), ("A3", "atr", 3.0)]


def hold(o, h, l, c, pc, ent, nd):
    n = len(c); e = ent + nd - 1
    if e >= n:
        return None
    j = e; k = 0
    while j < n and k < 10 and (np.isnan(c[j]) or ((not np.isnan(h[j])) and h[j] == l[j] and (not np.isnan(pc[j])) and c[j] <= pc[j] * 0.905)):
        j += 1; k += 1
    if j >= n or np.isnan(c[j]):
        idx = [i for i in range(ent, e + 1) if not np.isnan(c[i])]
        if not idx:
            return None
        j = idx[-1]
    return j, c[j]


def stop(o, h, l, c, pc, atr, ent, kind, p, cap):
    n = len(c); ep = o[ent]
    if kind == "atr" and np.isnan(atr[ent]):
        return None
    hi = -np.inf; line = ep * (1 - p) if kind == "stop" else -np.inf
    for i in range(ent, min(n - 1, ent + cap - 1) + 1):
        if np.isnan(c[i]):
            continue
        hi = max(hi, c[i])
        if kind == "trail":
            line = max(line, hi * (1 - p))
        elif kind == "atr" and not np.isnan(atr[i]):
            line = max(line, hi - p * atr[i])
        if c[i] < line:
            j = i + 1
            while j < n and np.isnan(o[j]):
                j += 1
            return (i, c[i]) if j >= n else (j, o[j])
    return hold(o, h, l, c, pc, ent, cap)


def nonoverlap(g):
    cnt = 0
    for _, x in g.groupby("stock_id"):
        last = -10 ** 9
        for e in np.sort(x["entry_pos"].to_numpy()):
            if e - last >= 60:
                cnt += 1; last = e
    return cnt


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=300); a = ap.parse_args()
    errs = []; info = {}
    cal = D.load_calendar()
    LG = pd.read_csv(os.path.join(OUT, "legs.csv.gz"), dtype={"stock_id": str})
    ex = pd.read_csv("backtest/results5/exits.csv.gz", dtype={"stock_id": str}, usecols=["stock_id", "market"]).drop_duplicates("stock_id").set_index("stock_id")["market"]
    smp = LG[LG["ok"] == True].sample(a.n, random_state=20260928)                     # noqa: E712
    nb = 0; nt = 0
    for sid, g in smp.groupby("stock_id"):
        st = D.load_stock(sid, ex[sid], cal); f = P.Frame(st.df, st.event_dates)
        o, h, l, c, pc, atr = f.o, f.h, f.l, f.c, f.prev_c, f.atr14
        for _, r in g.iterrows():
            ep = int(r["entry_pos"]); px = o[ep]
            for H in (20, 60, 120):
                legs = [(f"ret_H{H}", hold(o, h, l, c, pc, ep, H))] + [(f"ret_{cd}_c{H}", stop(o, h, l, c, pc, atr, ep, k, p, H)) for cd, k, p in STOPS]
                for col, x in legs:
                    mine = np.nan if x is None else x[1] / px - 1 - COST
                    nt += 1
                    if not ((np.isnan(mine) and np.isnan(r[col])) or abs(mine - r[col]) < 1e-12):
                        nb += 1
                        if nb <= 5:
                            errs.append(f"① {sid} {ep} {col}：自算 {mine} vs 檔 {r[col]}")
    info["① 腿（抽樣筆×30）"] = [nt, nb]
    T = pd.read_csv(os.path.join(OUT, "pairs.csv"))
    split = int(cal.searchsorted(pd.Timestamp("2021-01-04")))
    nbad = 0; ntot = 0
    for _, r in T[T["版本"] == "主版（上限＝H）"].iterrows():
        d = LG[LG["set"] == r["集合"]]
        H = int(r["基準"][1:])
        col, base = f"ret_{r['規則']}_c{H}", f"ret_H{H}"
        m = d[col].notna() & d[base].notna(); g = d[m]
        x = (g[col] - g[base]).to_numpy(float); nno = nonoverlap(g)
        mean = x.mean(); se = x.std(ddof=1) / math.sqrt(max(1, nno))
        ntot += 1
        if abs(mean - r["五_mean"]) > 1e-12 or abs((mean - 1.96 * se) - r["五_lo"]) > 1e-12 or int(nno) != int(r["五_n_no"]):
            nbad += 1
        pre = g[g["entry_pos"] < split]; post = g[g["entry_pos"] >= split]
        dp, dq = (pre[col] - pre[base]).mean(), (post[col] - post[base]).mean()
        same = np.sign(dp) == np.sign(dq)
        p5d = np.percentile(g[col], 5) - np.percentile(g[base], 5)
        v = "期望值較好" if (mean - 1.96 * se > 0 and same) else ("較差" if mean + 1.96 * se < 0 else ("只是保險" if p5d >= 0.03 else "分不出來"))
        if nno < 30:
            v = "樣本不足（不報）"
        elif nno < 100:
            v += "（樣本不足）"
        if v != r["五_判定"]:
            nbad += 1; errs.append(f"② {r['集合']} {r['規則']} H{H} 判定 {v} vs {r['五_判定']}")
    info["② 研究五主版配對（列／不同）"] = [ntot, nbad]
    info["錯誤數"] = len(errs) + (1 if nb else 0) + (1 if nbad else 0)
    json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(info, ensure_ascii=False)); [print("  ⛔", e) for e in errs[:10]]
    print("查核：" + ("全過" if info["錯誤數"] == 0 else "⛔ 不過"))


if __name__ == "__main__":
    main()
