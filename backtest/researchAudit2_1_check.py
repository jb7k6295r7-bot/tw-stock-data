# -*- coding: utf-8 -*-
"""稽核 ② 5 三態輪動 K7 重挑 獨立查核（⛔ 不 import backtest 任何模組、不 import researchAudit2_1）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_1_check.py

上半段 ＝ researchTri_check.py（bf4192c348）第 3～280 行原樣（自接 0050、自讀外資融資、自寫 25 訊號、狀態機、金額制引擎；T1 訊號日數對原件 pre_signals）；
下半段 A1～A6：退化格排除計數、X1 依構造、主版重挑與確認段、三態觸發次數、假訊號 1,000 次、壓力段

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchTri_check.py

獨立的地方：0050 自己接（早年 git grep ＋ 主快照 CSV／adj 自還原）；外資／融資直接讀 ~/ydata/3edc0e2206 的檔（自己併外資兩列）；
  指標自寫（MA 用 pandas rolling、EMA／KD／RSI 逐根迴圈、布林用 rolling std(ddof=0)）；狀態機自寫；引擎用金額制
T1 訊號：25 個訊號逐日相同｜T2 全部 1,120 格 × 兩段 年化／回落／轉換次數｜T3 兩種挑法、確認段標籤｜T4 2022 谷底｜
T5 假訊號（讀主程式存的隨機轉換日重算，p 相同）｜T6 壓力段 6 列
"""
import glob
import io
import json
import os
import subprocess
import sys
from itertools import product

import numpy as np
import pandas as pd

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
YD = os.path.expanduser("~/ydata/3edc0e2206")
DB = os.path.expanduser("~/tw-stock-data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsTri")
ANN, COST, FEE = 245, 0.00385, 0.01 / 245
TOL = 1e-9
bad = []


def chk(n, ok, det=""):
    print(("✅" if ok else "⛔"), n, det, flush=True)
    if not ok:
        bad.append(n)


def git(*a):
    return subprocess.run(["git", "-C", DB, *a], capture_output=True, text=True, check=True).stdout


# ── 日曆與價格
st = pd.read_csv(os.path.join(YD, "data/early/_structure.csv"), dtype=str)
early_cal = sorted(st.loc[(st["market"] == "twse") & (pd.to_numeric(st["rows"]) > 0), "date"])
main_cal = pd.read_csv(os.path.join(SNAP, "meta/calendar_twse.csv"), dtype=str)["date"].tolist()
cal = early_cal + main_cal; N = len(cal); pos = {d: i for i, d in enumerate(cal)}


def main_px(sid):
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype=str).set_index("date")
    a = pd.read_csv(os.path.join(SNAP, "adj", f"{sid}.csv"), dtype=str)
    ed = a["date"].to_numpy(); cf = a["cum_factor"].astype(float).to_numpy()
    out = {k: np.full(N, np.nan) for k in ("open", "high", "low", "close")}
    raw_c = {}
    for d in r.index:
        j = np.flatnonzero(ed > d); f = cf[j[0]] if len(j) else 1.0
        vals = {k: pd.to_numeric(r.at[d, k], errors="coerce") for k in out}
        if any(v <= 0 for v in vals.values() if pd.notna(v)):
            continue
        for k in out:
            out[k][pos[d]] = vals[k] * f
        raw_c[d] = vals["close"]
    return out, raw_c


P50, raw50 = main_px("0050"); P31, _ = main_px("00631L")
s_ = P50["close"][pos[main_cal[0]]] / raw50[main_cal[0]]
txt = subprocess.run("grep -h '^[0-9-]*_0050,' " + os.path.join(YD, "data/early/daily") + "/*.csv", shell=True, capture_output=True, text=True).stdout
ed_rows = pd.read_csv(io.StringIO(txt), header=None, dtype=str)            # 讀 researchY 抽出的 tar（非 git grep）
assert len(ed_rows) == len(early_cal), (len(ed_rows), len(early_cal))
ex = []
for f in sorted(glob.glob(os.path.join(YD, "data/early/exright/*.csv"))):
    x = pd.read_csv(f, dtype=str)
    x = x[x["stock_id"] == "0050"]
    for _, r in x.iterrows():
        ex.append((r["date"], float(r["ref_price"]) / float(r["pre_close"])))
for _, r in ed_rows.iterrows():
    d = r[1]
    if d >= main_cal[0]:
        continue
    f = s_
    for e_, fac in ex:
        if e_ > d:
            f *= fac
    for k, col in (("open", 5), ("high", 6), ("low", 7), ("close", 8)):
        v = float(r[col])
        P50[k][pos[d]] = v * f if v > 0 else np.nan

# ── 外資、融資
ia = []
for tree in ("early", "universe"):
    for f in sorted(glob.glob(os.path.join(YD, f"data/{tree}/instamt/*.csv"))):
        ia.append(pd.read_csv(f, dtype=str))
ia = pd.concat(ia)
ia["net"] = pd.to_numeric(ia["net"].str.replace(",", ""), errors="coerce")
FOREIGN = {"外資", "外資及陸資", "外資及陸資(不含外資自營商)", "外資自營商"}
fnet = ia[ia["investor"].isin(FOREIGN)].groupby("date")["net"].sum()
mg = []
for tree in ("early", "universe"):
    for f in sorted(glob.glob(os.path.join(YD, f"data/{tree}/marginmkt/*.csv"))):
        x = pd.read_csv(f, dtype=str); mg.append(x[x["item"] == "融資金額(仟元)"][["date", "prev"]])
mg = pd.concat(mg); mg["prev"] = pd.to_numeric(mg["prev"].str.replace(",", ""))
mg = mg.sort_values("date").reset_index(drop=True)

# ── 指標（有效 K 棒）
bars = np.flatnonzero(np.isfinite(P50["close"]))
c = pd.Series(P50["close"][bars]); h = P50["high"][bars]; l = P50["low"][bars]
ma = {n: c.rolling(n).mean().to_numpy() for n in (20, 60, 200)}
cc = c.to_numpy()


def ema(x, span, start):
    a = 2 / (span + 1); out = np.full(len(x), np.nan); v = x[start]
    out[start] = v
    for i in range(start + 1, len(x)):
        v = a * x[i] + (1 - a) * v; out[i] = v
    return out


dif = ema(cc, 12, 0) - ema(cc, 26, 0); dif[:25] = np.nan
dea = np.full(len(cc), np.nan); dea[25:] = ema(dif[25:], 9, 0)
K = np.full(len(cc), np.nan); Dd = np.full(len(cc), np.nan); k_ = d_ = 50.0
for t in range(8, len(cc)):
    hh, ll = max(h[t - 8:t + 1]), min(l[t - 8:t + 1])
    rsv = 50.0 if hh == ll else (cc[t] - ll) / (hh - ll) * 100
    k_ = k_ * 2 / 3 + rsv / 3; d_ = d_ * 2 / 3 + k_ / 3; K[t] = k_; Dd[t] = d_
R = np.full(len(cc), np.nan); g = np.maximum(np.diff(cc), 0); lo = np.maximum(-np.diff(cc), 0)
ag, al = g[:14].mean(), lo[:14].mean(); R[14] = 100 - 100 / (1 + ag / al) if al else 100
for t in range(15, len(cc)):
    ag = (ag * 13 + g[t - 1]) / 14; al = (al * 13 + lo[t - 1]) / 14; R[t] = 100 - 100 / (1 + ag / al) if al else 100
sd = c.rolling(20).std(ddof=0).to_numpy(); lower = ma[20] - 2 * sd
bias = cc / ma[60] - 1; dd = cc / c.rolling(250).max().to_numpy() - 1


def dn(a, b):
    o = np.zeros(len(a), bool)
    for i in range(1, len(a)):
        o[i] = a[i] < b[i] and a[i - 1] >= b[i - 1]
    return o


def up(a, b):
    o = np.zeros(len(a), bool)
    for i in range(1, len(a)):
        o[i] = a[i] > b[i] and a[i - 1] <= b[i - 1]
    return o


Kp = np.r_[np.nan, K[:-1]]
Rp = np.r_[np.nan, R[:-1]]; Bp = np.r_[np.nan, bias[:-1]]
bsig = {"W1": dn(cc, ma[20]), "W2": dn(cc, ma[60]), "W3": dn(cc, ma[200]), "W4": dn(ma[20], ma[60]), "W5": dn(dif, dea),
        "W6": dn(K, Dd) & (Kp > 80), "W7": (Rp > 50) & (R < 50), "W8": (Bp > 0.1) & (bias <= 0.1),
        "P1": dd <= -0.15, "P2": dd <= -0.2, "P3": dd <= -0.3, "P4": R < 30, "P5": K < 20, "P6": dn(cc, lower), "P7": bias < -0.1,
        "U1": up(cc, ma[20]), "U2": up(cc, ma[60]), "U3": up(ma[20], ma[60]), "U4": up(dif, dea), "U5": up(K, Dd) & (Kp < 20),
        "U6": (Rp < 50) & (R > 50), "U7": up(cc, ma[20])}
S = {}
for k, v in bsig.items():
    full = np.zeros(N, bool)
    if k in ("P1", "P2", "P3", "P4", "P5", "P7"):
        last = False
        vb = dict(zip(bars, v))
        for i in range(N):
            if i in vb:
                last = bool(vb[i])
            full[i] = last
    else:
        full[bars] = v
    S[k] = full


def streak(flag, n):
    o = np.zeros(N, bool); r = 0
    for i in range(N):
        r = r + 1 if flag[i] else 0
        o[i] = r == n
    return o


fs = np.array([fnet.get(d, np.nan) for d in cal])
S["W9"] = streak(np.nan_to_num(fs, nan=0) < 0, 5); S["U8"] = streak(np.nan_to_num(fs, nan=0) > 0, 3)
pv = mg["prev"].to_numpy(); ch = np.full(len(pv), np.nan); ch[20:] = pv[20:] / pv[:-20] - 1
S["W10"] = np.zeros(N, bool)
for i in range(1, len(pv)):
    if ch[i] > 0.1 and ch[i - 1] <= 0.1:
        S["W10"][pos[mg["date"].iloc[i]]] = True

pre = pd.read_csv(os.path.join(OUT, "pre_signals.csv"))
s0 = pos[json.load(open(os.path.join(OUT, "pre_summary.json"), encoding="utf-8"))["狀態機起跑日（全部訊號可算）"]]
segs = {"早年（起跑～2014-12-31）": (s0, pos["2014-12-31"]), "探索": (pos["2015-11-02"], pos["2021-12-30"]), "確認": (pos["2022-01-03"], pos["2026-08-24"])}
# 精確平手日：收盤與 MA20 在浮點下差 < 1e-9 的日子，用有理數精確重算（早年價 ＝ 原始收盤 × Π(參考價÷前收) × s，s 為正、不影響正負號）
from fractions import Fraction as Fr
raw_e = {r[1]: r[8] for _, r in ed_rows.iterrows()}
exq = []
for f in sorted(glob.glob(os.path.join(YD, "data/early/exright/*.csv"))):
    x = pd.read_csv(f, dtype=str); x = x[x["stock_id"] == "0050"]
    exq += [(r["date"], Fr(r["ref_price"]) / Fr(r["pre_close"])) for _, r in x.iterrows()]


def exact_c(k):
    d = cal[bars[k]]; f = Fr(1)
    for e_, q in exq:
        if e_ > d:
            f *= q
    return Fr(raw_e[d]) * f


ties = []
for k in np.flatnonzero(np.abs(cc - ma[20]) < 1e-9 * cc):
    if cal[bars[k]] < main_cal[0] and k >= 19 and exact_c(k) == sum(exact_c(j) for j in range(k - 19, k + 1)) / 20:
        ties.append(cal[bars[k]])
print("  早年 收盤＝MA20 精確平手日：", ties)
mism = 0; tie_ok = 0
for _, r in pre.iterrows():
    for sg, (a, b) in segs.items():
        dv = int(S[r["代號"]][a:b + 1].sum()) - int(r[f"{sg}_成立日數"])
        if dv:
            if sg.startswith("早年") and r["代號"] in ("W1", "U1", "U7") and abs(dv) <= len(ties):
                tie_ok += 1; print("  平手造成（精確算術＝查核版）", r["代號"], sg, dv)
            else:
                mism += 1; print("  不符", r["代號"], sg, dv)
chk("T1 25 訊號 × 3 段成立日數", mism == 0, f"不符 {mism}；早年精確平手日 {ties} 造成的差 {tie_ok} 項（主程式浮點判為跌破；只影響早年段 W1／U1／U7）")


# ── 狀態機、引擎
def machine(w, p, u):
    stt = np.full(N, -1); stt[s0] = 0
    for t in range(s0 + 1, N):
        j = t - 1; a = stt[j]
        if a == 0:
            stt[t] = 1 if S[w][j] else 0
        elif a == 1:
            stt[t] = 0 if S[u][j] else (2 if S[p][j] else 1)
        else:
            stt[t] = 0 if S[u][j] else 2
    return stt


C50 = pd.Series(P50["close"]).ffill().to_numpy()
LEV = {"00631L": (P31["open"], pd.Series(P31["close"]).ffill().to_numpy())}


def tgt(s, b):
    return (0.0, 1.0) if s == 0 else ((1.0, 0.0) if (s == 2 or b == "B0050") else (0.0, 0.0))


def sim(stt, b, i0, i1, lev="00631L"):
    Lo, Lc = LEV[lev]
    O = [P50["open"], Lo]; C = [C50, Lc]
    hv = [0.0, 0.0]; cash = 1.0; last = None; eq = []
    for t in range(i0, i1 + 1):
        w = tgt(stt[t], b); traded = False
        if last is None or w != last:
            need = [j for j in range(2) if hv[j] > 0 or w[j] > 0]
            if all(np.isfinite(O[j][t]) for j in need):
                cur = [hv[j] * O[j][t] / C[j][t - 1] if hv[j] > 0 else 0.0 for j in range(2)]
                V = sum(cur) + cash
                tr = 0.5 * (sum(abs(w[j] * V - cur[j]) for j in range(2)) + abs((1 - sum(w)) * V - cash))
                V -= tr * COST
                hv = [w[j] * V * C[j][t] / O[j][t] if w[j] > 0 else 0.0 for j in range(2)]
                cash = (1 - sum(w)) * V; last = w; traded = True
        if not traded:
            hv = [hv[j] * C[j][t] / C[j][t - 1] if hv[j] > 0 else 0.0 for j in range(2)]
        eq.append(sum(hv) + cash)
    return np.array(eq)


def pf(eq):
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p)
    return eq[-1] ** (ANN / len(eq)) - 1, ((p - pk) / pk).min()


def bench(i0, i1):
    s = C50[i0:i1 + 1] / C50[i0]; pk = np.maximum.accumulate(s)
    return (s[-1] / s[0]) ** (1 / (len(s) / ANN)) - 1, ((s - pk) / pk).min()


def lab(c_, m_, c50, m50):
    r, r50 = c_ / abs(m_), c50 / abs(m50)
    return "合格" if (c_ > c50 and r >= r50) else ("另列" if c_ > c50 else "不合格")




# ═════════════ 以下為 researchAudit2_1 獨立查核（上半段＝ researchTri_check.py 1～280 行原樣：自接 0050、自讀外資融資、自寫指標、狀態機、金額制引擎；⛔ 不 import backtest）═════════════
A2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsAudit2", "1")
Sm = json.load(open(os.path.join(A2, "summary.json"), encoding="utf-8"))
E = (pos["2015-11-02"], pos["2021-12-30"]); Cf = (pos["2022-01-03"], pos["2026-08-24"])
BB = {"探索": bench(*E), "確認": bench(*Cf)}
W_ = [f"W{i}" for i in range(1, 11)]; P_ = [f"P{i}" for i in range(1, 8)]; U_ = [f"U{i}" for i in range(1, 9)]


def cnt(stt, i0, i1):
    nb = nc = na = 0
    for t in range(i0, i1 + 1):
        a, b = stt[t - 1], stt[t]
        if a != b:
            nb += (a == 0 and b == 1); nc += (a == 1 and b == 2); na += (b == 0)
    return nb, nc, na


ST = {}; CN = {}
for w, p, u in product(W_, P_, U_):
    ST[(w, p, u)] = machine(w, p, u); CN[(w, p, u)] = cnt(ST[(w, p, u)], *E)
keep = []; nx = {"X1": 0, "X2": 0, "X3": 0, "X4": 0}
o = 0
for w, p, u, b in product(W_, P_, U_, ("B0050", "Bcash")):
    nb, nc, _ = CN[(w, p, u)]
    x = []
    if b == "B0050":
        x.append("X1")
    if nc < 3:
        x.append("X2")
    if nb < 3:
        x.append("X3")
    if nb >= 3 and nc / nb > 0.9:
        x.append("X4")
    for k in x:
        nx[k] += 1
    if not x:
        keep.append((w, p, u, b, o))
    o += 1
ref = Sm["排除統計"]
chk("A1 排除計數（X1～X4、保留格數）", len(keep) == ref["保留"] and all(nx[k] == ref[k] for k in nx), f"保留 {len(keep)}；{nx}")
# X1 依構造：B 抱 0050 ⇒ 目標權重 B、C 相同 ⇒ 抽一組 (W4, U4) 驗 7 種跌深確認段相同
e7 = [pf(sim(ST[("W4", p, "U4")], "B0050", *Cf)) for p in P_]
chk("A2 X1 依構造（W4×U4 B 抱 0050，7 種跌深確認段相同）", max(abs(a[0] - e7[0][0]) for a in e7) == 0.0)
res = []
for w, p, u, b, o_ in keep:
    stt = ST[(w, p, u)]
    cg, md = pf(sim(stt, b, *E))
    res.append((w, p, u, b, o_, cg, md, int(np.sum(stt[E[0] + 1:E[1] + 1] != stt[E[0]:E[1]]))))
m = pd.DataFrame(res, columns=["w", "p", "u", "b", "o", "c", "m", "sw"])
pb = m.sort_values(["c", "sw", "o"], ascending=[False, True, True]).iloc[0]
m["r"] = m["c"] / m["m"].abs(); q = m[(m["c"] > BB["探索"][0]) & (m["r"] >= BB["探索"][0] / abs(BB["探索"][1]))]
pa = q.sort_values(["r", "sw", "o"], ascending=[False, True, True]).iloc[0]
stb = ST[(pb["w"], pb["p"], pb["u"])]
cc_, cm_ = pf(sim(stb, pb["b"], *Cf))
mb = Sm["主版挑法乙（判定）"]
ok = ([pb["w"], pb["p"], pb["u"], pb["b"]] == mb["格"] and [pa["w"], pa["p"], pa["u"], pa["b"]] == Sm["主版挑法甲（並列）"]["格"]
      and abs(cc_ - mb["確認"]["年化"]) < TOL and abs(cm_ - mb["確認"]["回落"]) < TOL and lab(cc_, cm_, *BB["確認"]) == mb["確認"]["使用者判準"])
chk("A3 主版重挑（乙、甲）與確認段年化／回落／標籤", ok, f"乙 {pb['w']}/{pb['p']}/{pb['u']}/{pb['b']} 確認 {cc_:.6f}／{cm_:.6f} {lab(cc_, cm_, *BB['確認'])}")
cx = {sg: cnt(stb, *rg) for sg, rg in (("探索", E), ("確認", Cf))}
ok4 = (cx["探索"] == (mb["探索計數"]["nB（A→B）"], mb["探索計數"]["nC（B→C）"], mb["探索計數"]["nA（回 A）"])
       and cx["確認"] == (mb["確認計數"]["nB（A→B）"], mb["確認計數"]["nC（B→C）"], mb["確認計數"]["nA（回 A）"]))
chk("A4 主版乙 三態觸發次數（探索、確認）", ok4, f"{cx}")
z = np.load(os.path.join(A2, "null_days.npz")); days, seq = z["days"], z["seq"]
stc = stb[Cf[0]:Cf[1] + 1]
seq_ok = list(seq) == [int(stc[0])] + [int(stc[i]) for i in np.flatnonzero(stc[1:] != stc[:-1]) + 1]
nl = pd.read_csv(os.path.join(A2, "null.csv")); cs = []
for j in range(len(days)):
    s2 = np.full(N, -1); s2[Cf[0]:Cf[1] + 1] = seq[0]
    for q_, dday in enumerate(days[j]):
        s2[Cf[0] + dday:Cf[1] + 1] = seq[q_ + 1]
    cs.append(pf(sim(s2, pb["b"], *Cf))[0])
cs = np.array(cs)
chk("A5 假訊號 1,000 次（p 贏 0050）", seq_ok and np.max(np.abs(cs - nl["年化"].to_numpy())) < TOL
    and float(np.mean(cs > BB["確認"][0])) == Sm["假訊號（主版乙，確認段）"]["p_年化贏0050"], f"p {np.mean(cs > BB['確認'][0])}")
Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 1] = 1.0
for t in range(s0, N):
    Lo[t] = Lc[t - 1] * (1 + 2 * (P50["open"][t] / C50[t - 1] - 1)) if np.isfinite(P50["open"][t]) else np.nan
    Lc[t] = Lc[t - 1] * (1 + 2 * (C50[t] / C50[t - 1] - 1) - FEE)
LEV["SYN"] = (Lo, Lc)
mx = 0.0
for r in Sm["壓力（合成、非實際 ETF）"]:
    if not r["對象"].startswith("主版乙"):
        continue
    eq = sim(stb, pb["b"], pos[r["起"]], pos[r["迄"]], "SYN")
    p_ = np.r_[1.0, eq]; pk = np.maximum.accumulate(p_)
    mx = max(mx, abs(((p_ - pk) / pk).min() - r["最大跌幅"]), abs(p_.min() * 1e6 - r["100萬谷底剩"]) / 1e6)
chk("A6 壓力段（主版乙 2 列）", mx < TOL, f"最大差 {mx:.1e}")
json.dump({"不過": bad}, open(os.path.join(A2, "check.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("⛔ 不過：" + "、".join(bad) if bad else "✅ 全過")
sys.exit(1 if bad else 0)
