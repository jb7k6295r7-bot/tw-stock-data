# -*- coding: utf-8 -*-
"""researchTri_0052 的簡單獨立查核（⛔ 不 import backtest 任何模組）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchTri_0052_check.py

Q1 0052 早年：列數、首日、除息 4 筆對官方 TWT49U（~/tri0052_official）｜Q2 6 版 × 兩段 年化／回落（自接價、自算 W4／P3／U4、金額制引擎）｜
Q3 事後挑（乙、甲）用 desc0052_cells.csv 以不同寫法重挑｜Q4 壓力段 0052 上市後窗、2008 窗 各列
"""
import glob
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
YD = os.path.expanduser("~/ydata/3edc0e2206")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsTri")
ANN, COST, FEE, TOL = 245, 0.00385, 0.01 / 245, 1e-9
bad = []


def chk(n, ok, det=""):
    print(("✅" if ok else "⛔"), n, det, flush=True)
    if not ok:
        bad.append(n)


st = pd.read_csv(os.path.join(YD, "data/early/_structure.csv"), dtype=str)
early_cal = sorted(st.loc[(st["market"] == "twse") & (pd.to_numeric(st["rows"]) > 0), "date"])
main_cal = pd.read_csv(os.path.join(SNAP, "meta/calendar_twse.csv"), dtype=str)["date"].tolist()
cal = early_cal + main_cal; N = len(cal); pos = {d: i for i, d in enumerate(cal)}


def px(sid):
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype=str).set_index("date")
    a = pd.read_csv(os.path.join(SNAP, "adj", f"{sid}.csv"), dtype=str)
    O = np.full(N, np.nan); C = np.full(N, np.nan); rawc = None
    for d in r.index:
        j = [float(x) for e, x in zip(a["date"], a["cum_factor"]) if e > d]; f = j[0] if j else 1.0
        o, c = pd.to_numeric(r.at[d, "open"], errors="coerce"), pd.to_numeric(r.at[d, "close"], errors="coerce")
        if pd.notna(c) and c > 0:
            O[pos[d]] = o * f if o > 0 else np.nan; C[pos[d]] = c * f
            if rawc is None:
                rawc = c
    s = C[pos[main_cal[0]]] / rawc
    txt = subprocess.run(f"grep -h '^[0-9-]*_{sid},' " + os.path.join(YD, "data/early/daily") + "/*.csv", shell=True, capture_output=True, text=True).stdout
    er = pd.read_csv(io.StringIO(txt), header=None, dtype=str)
    ex = []
    for fn in sorted(glob.glob(os.path.join(YD, "data/early/exright/*.csv"))):
        x = pd.read_csv(fn, dtype=str); x = x[x["stock_id"] == sid]
        ex += [(q["date"], float(q["ref_price"]) / float(q["pre_close"]), q) for _, q in x.iterrows()]
    n_ok = 0
    for _, q in er.iterrows():
        d = q[1]
        c = pd.to_numeric(q[8], errors="coerce")
        if d >= main_cal[0] or not (pd.notna(c) and c > 0):
            continue
        f = s
        for e, fac, _ in ex:
            if e > d:
                f *= fac
        o = pd.to_numeric(q[5], errors="coerce")
        O[pos[d]] = o * f if o > 0 else np.nan; C[pos[d]] = c * f; n_ok += 1
    return O, pd.Series(C).ffill().to_numpy(), er, ex, n_ok


O50, C50, _, _, _ = px("0050"); O52, C52, er52, ex52, n52 = px("0052")
r31 = pd.read_csv(os.path.join(SNAP, "stocks/00631L.csv"), dtype=str).set_index("date")
a31 = pd.read_csv(os.path.join(SNAP, "adj/00631L.csv"), dtype=str)
O31 = np.full(N, np.nan); C31 = np.full(N, np.nan)
for d in r31.index:
    f = float(a31["cum_factor"].iloc[0]) if d < a31["date"].iloc[0] else 1.0
    O31[pos[d]] = float(r31.at[d, "open"]) * f; C31[pos[d]] = float(r31.at[d, "close"]) * f
C31 = pd.Series(C31).ffill().to_numpy()

# Q1
off = {}
for fn in sorted(glob.glob(os.path.expanduser("~/tri0052_official/twt49u_*.json"))):
    j = json.load(open(fn, encoding="utf-8"))
    for r in j["data"]:
        if r[1].strip() == "0052":
            y, m, dd = r[0].replace("年", "/").replace("月", "/").replace("日", "").split("/")
            off[f"{int(y) + 1911}-{m}-{dd}"] = (float(r[3]), float(r[4]))
mine_ex = {e: (float(q["pre_close"]), float(q["ref_price"])) for e, _, q in ex52}
S = json.load(open(os.path.join(OUT, "desc0052_summary.json"), encoding="utf-8"))
chk("Q1 0052 早年（首日、有效列、除息對官方）", sorted(er52[1])[0] == S["0052早年"]["0052 早年首日"] and n52 == S["0052早年"]["早年有效收盤列"] and mine_ex == off,
    f"首日 {sorted(er52[1])[0]}、有效列 {n52}、除息 {len(mine_ex)} 筆＝官方 {len(off)} 筆")

# 訊號 W4 P3 U4（0050）
# 有效 K 棒：主快照有收盤、早年有收盤（重讀一次避免 ffill 汙染）
def valid_close(sid):
    out = np.full(N, np.nan)
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype=str)
    for d, c in zip(r["date"], pd.to_numeric(r["close"], errors="coerce")):
        if pd.notna(c) and c > 0:
            out[pos[d]] = 1
    txt = subprocess.run(f"grep -h '^[0-9-]*_{sid},' " + os.path.join(YD, "data/early/daily") + "/*.csv", shell=True, capture_output=True, text=True).stdout
    for line in txt.splitlines():
        p = line.split(",")
        if p[1] < main_cal[0] and p[8] not in ("", "0", "0.00") and float(p[8]) > 0:
            out[pos[p[1]]] = 1
    return np.flatnonzero(out == 1)


b = valid_close("0050"); c = pd.Series(C50[b])
m20, m60 = c.rolling(20).mean().to_numpy(), c.rolling(60).mean().to_numpy()
cc = c.to_numpy()


def ema(x, span):
    a = 2 / (span + 1); o = np.empty(len(x)); v = x[0]
    for i, xi in enumerate(x):
        v = xi if i == 0 else a * xi + (1 - a) * v; o[i] = v
    return o


dif = ema(cc, 12) - ema(cc, 26); dif[:25] = np.nan; dea = np.full(len(cc), np.nan); dea[25:] = ema(dif[25:], 9)
dd = cc / c.rolling(250).max().to_numpy() - 1
W4 = np.zeros(N, bool); U4 = np.zeros(N, bool); P3 = np.zeros(N, bool)
for k in range(1, len(b)):
    W4[b[k]] = m20[k] < m60[k] and m20[k - 1] >= m60[k - 1]
    U4[b[k]] = dif[k] > dea[k] and dif[k - 1] <= dea[k - 1]
last = False; bp = {bb: k for k, bb in enumerate(b)}
for i in range(N):
    if i in bp:
        last = bool(dd[bp[i]] <= -0.3)
    P3[i] = last
s0 = pos[json.load(open(os.path.join(OUT, "pre_summary.json"), encoding="utf-8"))["狀態機起跑日（全部訊號可算）"]]
stt = np.full(N, -1); stt[s0] = 0
for t in range(s0 + 1, N):
    a = stt[t - 1]
    stt[t] = (1 if W4[t - 1] else 0) if a == 0 else ((0 if U4[t - 1] else (2 if P3[t - 1] else 1)) if a == 1 else (0 if U4[t - 1] else 2))


def tgt(s_, bst, cst):
    w = [0.0, 0.0, 0.0]
    if s_ == 0:
        w[2] = 1.0
    elif s_ == 1 and bst != "現金":
        w[0 if bst == "0050" else 1] = 1.0
    elif s_ == 2:
        w[0 if cst == "0050" else 1] = 1.0
    return tuple(w)


def sim(stt, bst, cst, i0, i1, O, C):
    hv = [0.0] * 3; cash = 1.0; last = None; eq = []
    for t in range(i0, i1 + 1):
        w = tgt(stt[t], bst, cst); traded = False
        if last is None or w != last:
            need = [j for j in range(3) if hv[j] > 0 or w[j] > 0]
            if all(np.isfinite(O[j][t]) for j in need):
                cur = [hv[j] * O[j][t] / C[j][t - 1] if hv[j] > 0 else 0.0 for j in range(3)]
                V = sum(cur) + cash
                V -= COST * 0.5 * (sum(abs(w[j] * V - cur[j]) for j in range(3)) + abs((1 - sum(w)) * V - cash))
                hv = [w[j] * V * C[j][t] / O[j][t] if w[j] > 0 else 0.0 for j in range(3)]
                cash = (1 - sum(w)) * V; last = w; traded = True
        if not traded:
            hv = [hv[j] * C[j][t] / C[j][t - 1] if hv[j] > 0 else 0.0 for j in range(3)]
        eq.append(sum(hv) + cash)
    return np.array(eq)


def pf(eq):
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p)
    return eq[-1] ** (ANN / len(eq)) - 1, ((p - pk) / pk).min()


six = pd.read_csv(os.path.join(OUT, "desc0052_six.csv"), dtype={"B態": str, "C態": str})
Om = [O50, O52, O31]; Cm = [C50, C52, C31]
mx = 0.0
for _, r in six.iterrows():
    i0, i1 = (pos["2015-11-02"], pos["2021-12-30"]) if r["段"] == "探索" else (pos["2022-01-03"], pos["2026-08-24"])
    cg, md = pf(sim(stt, r["B態"], r["C態"], i0, i1, Om, Cm))
    mx = max(mx, abs(cg - r["年化"]), abs(md - r["回落"]))
chk("Q2 W4×P3×U4 × 6 版 × 兩段", mx < TOL, f"最大差 {mx:.1e}")

# Q3
al = pd.read_csv(os.path.join(OUT, "desc0052_cells.csv"), dtype={"B態": str, "C態": str})
pk = pd.read_csv(os.path.join(OUT, "desc0052_picks.csv"))
ex_ = al[al["段"] == "探索"]
top = ex_[ex_["年化"] == ex_["年化"].max()].sort_values("狀態轉換", kind="stable").iloc[0]
print("  乙 同分格：", [f"{t['轉弱']}×{t['跌深']}×{t['反彈']}×B {t['B態']}×C {t['C態']}" for _, t in ex_[ex_["年化"] == ex_["年化"].max()].iterrows()])
b50 = C50[pos["2015-11-02"]:pos["2021-12-30"] + 1] / C50[pos["2015-11-02"]]
c50 = b50[-1] ** (ANN / len(b50)) - 1; m50 = ((b50 - np.maximum.accumulate(b50)) / np.maximum.accumulate(b50)).min()
q = ex_[(ex_["年化"] > c50) & (ex_["年化"] / ex_["回落"].abs() >= c50 / abs(m50))]
topa = q[q["比值"] == q["比值"].max()].sort_values("狀態轉換", kind="stable").iloc[0]
f = lambda t: f"{t['轉弱']}×{t['跌深']}×{t['反彈']}×B {t['B態']}×C {t['C態']}"
chk("Q3 事後挑（乙、甲）", f(top) == pk["格"].iloc[0] and f(topa) == pk["格"].iloc[1], f"乙 {f(top)}；甲 {f(topa)}")

# Q4 壓力
Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 1] = 1.0
for t in range(s0, N):
    Lo[t] = Lc[t - 1] * (1 + 2 * (O50[t] / C50[t - 1] - 1)) if np.isfinite(O50[t]) else np.nan
    Lc[t] = Lc[t - 1] * (1 + 2 * (C50[t] / C50[t - 1] - 1) - FEE)
Os = [O50, O52, Lo]; Cs = [C50, C52, Lc]
stv = pd.read_csv(os.path.join(OUT, "desc0052_stress.csv")); mx = 0.0; n = 0
for _, r in stv.iterrows():
    if pd.isna(r["最大跌幅"]):
        continue
    a, b_ = (s0, pos["2014-12-31"]) if r["期間"].startswith("2005") else ((pos["2006-09-12"], pos["2014-12-31"]) if r["期間"].startswith("2006") else (pos["2008-01-02"], pos["2009-03-31"]))
    o = r["對象"]
    if o.startswith("輪動"):
        bs, cs = o.replace("輪動 B", "").split("／C"); eq = sim(stt, bs, cs, a, b_, Os, Cs)
    elif o == "純抱合成正2":
        eq = sim(np.zeros(N, int), "現金", "0050", a, b_, Os, Cs)
    elif o == "純抱 0052":
        eq = sim(np.full(N, 2), "現金", "0052", a, b_, Os, Cs)
    else:
        eq = C50[a:b_ + 1] / C50[a - 1]
    p = np.r_[1.0, eq]; pkk = np.maximum.accumulate(p)
    mx = max(mx, abs(((p - pkk) / pkk).min() - r["最大跌幅"]), abs(p.min() * 1e6 - r["100萬谷底剩"]) / 1e6, abs(eq[-1] * 1e6 - r["100萬期末"]) / 1e6); n += 1
chk("Q4 壓力段各列", mx < TOL, f"{n} 列、最大差 {mx:.1e}")
print("⛔ 不過：" + "、".join(bad) if bad else "✅ 全過")
sys.exit(1 if bad else 0)
