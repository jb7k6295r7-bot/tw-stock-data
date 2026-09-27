# -*- coding: utf-8 -*-
"""researchMix70 的簡單獨立查核（⛔ 不 import backtest 任何模組）：自接價格、自合成、金額制重算每一列的年化／回落／動手次數，
並重做「最大 x」「前 5 名」「12 個月差距」。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchMix70_check.py
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
YD = os.path.expanduser("~/ydata/3edc0e2206")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsMix70")
COST, ANN, TOL = 0.00385, 245, 1e-9
bad = []


def chk(n, ok, det=""):
    print(("✅" if ok else "⛔"), n, det, flush=True)
    if not ok:
        bad.append(n)


st = pd.read_csv(os.path.join(YD, "data/early/_structure.csv"), dtype=str)
early = sorted(st.loc[(st["market"] == "twse") & (pd.to_numeric(st["rows"]) > 0), "date"])
mainc = pd.read_csv(os.path.join(SNAP, "meta/calendar_twse.csv"), dtype=str)["date"].tolist()
cal = early + mainc; N = len(cal); pos = {d: i for i, d in enumerate(cal)}


def load(sid, with_early):
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype=str)
    a = pd.read_csv(os.path.join(SNAP, "adj", f"{sid}.csv"), dtype=str)
    O = np.full(N, np.nan); C = np.full(N, np.nan); fr = None
    for d, o, h, l, c in zip(r["date"], *(pd.to_numeric(r[k], errors="coerce") for k in ("open", "high", "low", "close"))):
        if not all(pd.notna(x) and x > 0 for x in (o, h, l, c)):
            continue
        f = next((float(x) for e, x in zip(a["date"], a["cum_factor"]) if e > d), 1.0)
        O[pos[d]] = o * f; C[pos[d]] = c * f; fr = fr or (d, c)
    if with_early:
        s = C[pos[fr[0]]] / fr[1]
        ex = []
        for fn in sorted(glob.glob(f"{YD}/data/early/exright/*.csv")):
            x = pd.read_csv(fn, dtype=str); x = x[x["stock_id"] == sid]
            ex += [(q["date"], float(q["ref_price"]) / float(q["pre_close"])) for _, q in x.iterrows()]
        txt = subprocess.run(f"grep -h '^[0-9-]*_{sid},' {YD}/data/early/daily/*.csv", shell=True, capture_output=True, text=True).stdout
        for line in txt.splitlines():
            p = line.split(",")
            v = [pd.to_numeric(z, errors="coerce") for z in p[5:9]]
            if p[1] >= mainc[0] or not all(pd.notna(z) and z > 0 for z in v):
                continue
            f = s
            for e, q in ex:
                if e > p[1]:
                    f *= q
            O[pos[p[1]]] = v[0] * f; C[pos[p[1]]] = v[3] * f
    return O, pd.Series(C).ffill().to_numpy()


P = {"0050": load("0050", True), "0052": load("0052", True), "00631L": load("00631L", False), "00685L": load("00685L", False)}
o50, c50 = P["0050"]; s0 = pos["2006-09-12"]


def syn(fee):
    Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 2] = 1.0
    for t in range(s0 - 1, N):
        Lo[t] = Lc[t - 1] * (1 + 2 * (o50[t] / c50[t - 1] - 1)) if np.isfinite(o50[t]) else np.nan
        Lc[t] = Lc[t - 1] * (1 + 2 * (c50[t] / c50[t - 1] - 1) - fee / 245)
    return Lo, Lc


PS = dict(P); PS["00631L"] = syn(0.01); PS["00685L"] = syn(0.003)


def sim(P, assets, w, a, b, months=(1,), band=None):
    hv = np.zeros(len(assets)); cash = 1.0; eq = []; nact = 0; pend = True
    for t in range(a, b + 1):
        O = np.array([P[x][0][t] for x in assets]); C = np.array([P[x][1][t] for x in assets]); Cp = np.array([P[x][1][t - 1] for x in assets])
        if t > a:
            if band is None and cal[t][:7] != cal[t - 1][:7] and int(cal[t][5:7]) in months:
                pend = True
            if band is not None and (hv.sum() + cash) > 0 and np.max(np.abs(hv / (hv.sum() + cash) - np.array(w))) > band + 1e-12:
                pend = True
        traded = False
        if pend and all(np.isfinite(O[j]) for j in range(len(assets)) if hv[j] > 0 or w[j] > 0):
            cur = np.array([hv[j] * O[j] / Cp[j] if hv[j] > 0 else 0.0 for j in range(len(assets))]); V = cur.sum() + cash
            tr = 0.5 * (np.abs(np.array(w) * V - cur).sum() + abs((1 - sum(w)) * V - cash)); V -= tr * COST
            hv = np.array([w[j] * V * C[j] / O[j] if w[j] > 0 else 0.0 for j in range(len(assets))]); cash = (1 - sum(w)) * V
            pend = False; traded = True; nact += (t > a and tr > 0)
        if not traded:
            hv = np.array([hv[j] * C[j] / Cp[j] if hv[j] > 0 else 0.0 for j in range(len(assets))])
        eq.append(hv.sum() + cash)
    eq = np.array(eq); p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p)
    return eq[-1] ** (ANN / len(eq)) - 1, ((p - pk) / pk).min(), nact / (len(eq) / ANN)


F = (pos["2015-11-02"], pos["2026-08-24"]); W = (pos["2018-01-15"], pos["2026-08-24"]); STR = (s0, pos["2014-12-31"])
g2 = pd.read_csv(os.path.join(OUT, "mix2_grid.csv"), dtype={"ETF": str}); mx = 0.0; ok = []
for _, r in g2.iterrows():
    w = (r["正2%"] / 100, 1 - r["正2%"] / 100); a = ("00631L", r["ETF"])
    c, m, na = sim(P, a, w, *F); _, ms, _ = sim(PS, a, w, *STR)
    mx = max(mx, abs(c - r["年化"]), abs(m - r["最大回落"]), abs(ms - r["2008合成最大回落（2006-09～2014）"]), abs(na - r["每年動手"]))
    ok.append((r["ETF"], r["正2%"], m >= -0.7 and ms >= -0.7))
best = {e: max(x for ee, x, o in ok if ee == e and o) for e in ("0050", "0052")}
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
chk("C1 兩檔 22 列＋最大 x", mx < TOL and best == {k: int(v) for k, v in S["①最大正2比例"].items()}, f"最大差 {mx:.1e}、最大 x {best}")

g3 = pd.read_csv(os.path.join(OUT, "mix3_grid.csv")); mx = 0.0; rows = []
A3 = ("0050", "00631L", "00685L")
for _, r in g3.iterrows():
    w = (r["0050%"] / 100, r["00631L%"] / 100, r["00685L%"] / 100)
    c, m, na = sim(P, A3, w, *W); _, ms, _ = sim(PS, A3, w, *STR)
    mx = max(mx, abs(c - r["年化"]), abs(m - r["最大回落"]), abs(ms - r["2008合成最大回落（2006-09～2014）"]))
    rows.append((w, c, m >= -0.7 and ms >= -0.7))
t5 = pd.read_csv(os.path.join(OUT, "mix3_top5.csv"))
mine = sorted([x for x in rows if x[2]], key=lambda x: -x[1])[:5]
same = all(abs(a[0][0] - b["0050%"] / 100) < 1e-9 and abs(a[0][2] - b["00685L%"] / 100) < 1e-9 for a, (_, b) in zip(mine, t5.iterrows()))
chk("C2 三檔 66 列＋前 5 名", mx < TOL and same, f"最大差 {mx:.1e}、合格 {sum(x[2] for x in rows)}")

wb = mine[0][0]; fr = pd.read_csv(os.path.join(OUT, "rebalance_freq.csv")); mx = 0.0
for (_, r), kw in zip(fr.iterrows(), (dict(months=(1,)), dict(months=(1, 7)), dict(months=(1, 4, 7, 10)), dict(band=0.10))):
    c, m, na = sim(P, A3, wb, *W, **kw); mx = max(mx, abs(c - r["年化"]), abs(m - r["最大回落"]), abs(na - r["每年動手"]))
chk("C3 調整方式 4 列", mx < TOL, f"最大差 {mx:.1e}")
mo = pd.read_csv(os.path.join(OUT, "rebalance_month.csv")); mx = 0.0; cs = []
for _, r in mo.iterrows():
    c, m, _ = sim(P, A3, wb, *W, months=(int(r["調整月"]),)); cs.append(c); mx = max(mx, abs(c - r["年化"]), abs(m - r["最大回落"]))
chk("C4 12 個月＋最好最差差距", mx < TOL and abs((max(cs) - min(cs)) * 100 - S["③12個月"]["年化最好－最差（點）"]) < 1e-9, f"差距 {(max(cs) - min(cs)) * 100:.2f} 點")
print("⛔ 不過：" + "、".join(bad) if bad else "✅ 全過")
sys.exit(1 if bad else 0)
