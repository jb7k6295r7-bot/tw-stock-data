# -*- coding: utf-8 -*-
"""PREREG正2現金 本體的獨立查核（⛔ 不 import researchLev2、⛔ 不 import backtest 任何模組）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchLev2_check.py

獨立的地方：
  ・自己讀快照 CSV（stocks／adj／calendar），自己還原（adj.cum_factor 的「事件日嚴格大於 d」）
  ・引擎用【金額制】（持有金額逐日乘價格比；成交日拆成 前收→開盤、開盤→收盤），主程式是【單位制】
  ・均線用 cumsum 自算（主程式用 pandas rolling）
  ・年化／回落、判定、挑選、假訊號 p 全部自算，再和 resultsLev2/body_*.csv、body_summary.json 對
查核項：K1 0050 主窗錨逐位元｜K2 全部格（問一 264×2、問二全部列）年化／回落相對差｜K3 挑選與確認段標籤｜
        K4 假訊號一（同一 rng 抽樣）｜K5 假訊號二（讀主程式存的 1,000 條打亂狀態，逐條保段長、重算標籤）｜K6 2022 必報｜K7 描述臂
"""
import json
import os
import sys
from itertools import product

import numpy as np
import pandas as pd

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsLev2")
ANC = (0.24020209886370614, -0.3395700527611012)
ANN = 245
COST = 0.00385
TOL = 1e-10
SIDS = ("0050", "0052", "00631L", "00685L")
WTS = [(e, l, 10 - e - l) for e in range(11) for l in range(11 - e)]

cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(SNAP, "meta", "calendar_twse.csv"))["date"])).sort_values()
pos = {d: i for i, d in enumerate(cal)}


def px(sid):
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype=str)
    d = pd.to_datetime(r["date"])
    o = pd.to_numeric(r["open"], errors="coerce").to_numpy(float).copy(); c = pd.to_numeric(r["close"], errors="coerce").to_numpy(float).copy()
    hh = pd.to_numeric(r["high"], errors="coerce").to_numpy(); ll = pd.to_numeric(r["low"], errors="coerce").to_numpy()
    bad = (o <= 0) | (c <= 0) | (hh <= 0) | (ll <= 0)                 # 零價視為缺（NaN 比較為 False，同 data.py）
    o[bad] = np.nan; c[bad] = np.nan
    a = pd.read_csv(os.path.join(SNAP, "adj", f"{sid}.csv"), dtype={"date": str})
    ed = pd.to_datetime(a["date"]).to_numpy(); cf = a["cum_factor"].to_numpy(float)
    F = np.ones(len(d))
    for i, x in enumerate(d.to_numpy()):
        later = np.flatnonzero(ed > x)
        if len(later):
            F[i] = cf[later[0]]
    O = np.full(len(cal), np.nan); Cc = np.full(len(cal), np.nan)
    for i, x in enumerate(d):
        if x in pos:
            O[pos[x]] = o[i] * F[i]; Cc[pos[x]] = c[i] * F[i]
    return O, pd.Series(Cc).ffill().to_numpy()


P = {s: px(s) for s in SIDS}
B = P["0050"][1]


def ix(d):
    return pos[pd.Timestamp(d)]


def ma(x, n):
    cs = np.concatenate([[0.0], np.cumsum(x)])
    out = np.full(len(x), np.nan)
    out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


M = {n: ma(B, n) for n in (20, 50, 60, 200)}
raw = {"C1": B > M[200], "C2": B > M[60], "C3": B > M[20], "C4": M[50] > M[200]}
COND = {k: np.concatenate([[False], v[:-1]]) for k, v in raw.items()}


def firsts(i0, i1, q=False):
    s = cal[i0:i1 + 1]
    k = (s.year * 10 + (s.month - 1) // 3) if q else s.year
    k = np.asarray(k)
    m = np.zeros(len(s), bool); m[1:] = k[1:] != k[:-1]
    return m


def sim(assets, W, R, i0, cash_g=0.0):
    """金額制。h：各檔持有金額（上一日收盤市值），cash。"""
    n, k = W.shape
    O = np.stack([P[a][0][i0:i0 + n] for a in assets], 1); C = np.stack([P[a][1][i0:i0 + n] for a in assets], 1)
    Cprev = np.stack([P[a][1][i0 - 1:i0 + n - 1] for a in assets], 1)
    h = np.zeros(k); cash = 1.0; last = None; pend = True; eq = np.zeros(n); held = np.full((n, k), np.nan); ex = np.zeros(n, bool)
    for t in range(n):
        if t > 0 and (R[t] or not np.array_equal(W[t], last)):
            pend = True
        traded = False
        if pend:
            need = (h > 0) | (W[t] > 0)
            if all(np.isfinite(O[t, j]) for j in range(k) if need[j]):
                hv = np.array([h[j] * O[t, j] / Cprev[t, j] if h[j] > 0 else 0.0 for j in range(k)])
                V = hv.sum() + cash
                tg = W[t] * V; tc = V - tg.sum()
                cost = COST * 0.5 * (np.abs(tg - hv).sum() + abs(tc - cash))
                V -= cost
                h = W[t] * V; cash = V - h.sum()
                h = np.array([h[j] * C[t, j] / O[t, j] if h[j] > 0 else 0.0 for j in range(k)])
                last = W[t].copy(); pend = False; traded = True; ex[t] = True
        if not traded:
            h = np.array([h[j] * C[t, j] / Cprev[t, j] if h[j] > 0 else 0.0 for j in range(k)])
        if t > 0:
            cash *= 1.0 + cash_g
        eq[t] = h.sum() + cash
        held[t] = last if last is not None else np.nan
    return eq, held, ex


def pf(eq):
    n = len(eq)
    path = np.concatenate([[1.0], eq]); pk = np.maximum.accumulate(path)
    return (eq[-1]) ** (ANN / n) - 1, ((path - pk) / pk).min()


def bpf(i0, i1):
    seg = B[i0:i1 + 1] / B[i0]
    n = len(seg); c = (seg[-1] / seg[0]) ** (1 / (n / ANN)) - 1
    pk = np.maximum.accumulate(seg)
    return c, ((seg - pk) / pk).min()


def rt(c, m):
    return c / abs(m) if m < 0 else np.nan


def lab(c, m, c50, m50):
    return "合格" if (c > c50 and rt(c, m) >= rt(c50, m50)) else ("另列" if c > c50 else "不合格")


res = {}; bad = []


def chk(name, ok, detail=""):
    res[name] = {"過": bool(ok), "明細": detail}
    print(("✅" if ok else "⛔"), name, detail, flush=True)
    if not ok:
        bad.append(name)


# K1
w0, w1 = ix("2017-03-02"), ix("2026-08-24")
k1 = bpf(w0, w1)
chk("K1 0050 主窗錨逐位元", repr(float(k1[0])) == repr(ANC[0]) and repr(float(k1[1])) == repr(ANC[1]), f"{k1}")

SEG = {("A", "探索"): (ix("2015-11-02"), ix("2021-12-30")), ("L", "探索"): (ix("2018-01-15"), ix("2021-12-30")),
       ("A", "確認"): (ix("2022-01-03"), ix("2026-08-24")), ("L", "確認"): (ix("2022-01-03"), ix("2026-08-24"))}
BB = {k: bpf(*v) for k, v in SEG.items()}
S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
d0 = max(abs(BB[("A", "探索")][0] - S["0050同窗"]["A_探索"]["年化"]), abs(BB[("A", "確認")][0] - S["0050同窗"]["A_確認"]["年化"]))
chk("K1b 0050 同窗（探索／確認）", d0 < 1e-14, f"差 {d0:.1e}")

# K2 問一
q1 = pd.read_csv(os.path.join(OUT, "body_q1.csv"), dtype={"ETF": str, "正2": str})
mx = 0.0; labs_bad = 0; mine = []
for etf, lev, (e, l, c) in product(("0050", "0052"), ("00631L", "00685L"), WTS):
    g = "A" if lev == "00631L" else "L"
    for sg in ("探索", "確認"):
        i0, i1 = SEG[(g, sg)]; n = i1 - i0 + 1
        eq, _, _ = sim((etf, lev), np.tile([e / 10, l / 10], (n, 1)), firsts(i0, i1), i0)
        cc, mm = pf(eq); lb = lab(cc, mm, *BB[(g, sg)])
        row = q1[(q1["段"] == sg) & (q1["ETF"] == etf) & (q1["正2"] == lev) & (q1["ETF%"] == e * 10) & (q1["正2%"] == l * 10)].iloc[0]
        mx = max(mx, abs(cc - row["年化"]), abs(mm - row["回落"])); labs_bad += lb != row["標籤"]
        mine.append({"段": sg, "g": g, "ETF": etf, "正2": lev, "e": e, "l": l, "c": cc, "m": mm, "r": rt(cc, mm), "lab": lb})
mine = pd.DataFrame(mine)
chk("K2a 問一 528 列 年化／回落", mx < TOL and labs_bad == 0, f"最大絕對差 {mx:.1e}、標籤不符 {labs_bad}")

# K3 問一挑選
pool = mine[(mine["段"] == "探索") & (mine["g"] == "A")].reset_index(drop=True)
ok = pool[pool["c"] > BB[("A", "探索")][0]].copy(); ok["o"] = range(len(ok))
pk1 = ok.sort_values(["r", "l", "o"], ascending=[False, True, True]).iloc[0]
s1 = S["問一_探索"]["挑中"]
chk("K3a 問一挑中", (pk1["ETF"], pk1["e"] * 10, pk1["l"] * 10) == (s1["ETF"], s1["ETF%"], s1["正2%"]) and len(ok) == S["問一_探索"]["年化>0050格數"],
    f"{pk1['ETF']} {pk1['e']*10}/{pk1['l']*10}/{100-pk1['e']*10-pk1['l']*10}、年化＞0050 {len(ok)} 格")
c1 = mine[(mine["段"] == "確認") & (mine["ETF"] == pk1["ETF"]) & (mine["正2"] == pk1["正2"]) & (mine["e"] == pk1["e"]) & (mine["l"] == pk1["l"])].iloc[0]
chk("K3b 問一確認段標籤", c1["lab"] == S["確認段"]["問一"]["標籤"], f"{c1['lab']}（{c1['c']:.6f}／{c1['m']:.6f}）")

# K2b 問二
q2 = pd.read_csv(os.path.join(OUT, "body_q2.csv"), dtype={"ETF": str, "正2": str})
mx = 0.0; lb_bad = 0; rows2 = []
for _, r in q2.iterrows():
    g = "A" if r["正2"] == "00631L" else "L"
    i0, i1 = SEG[(g, r["段"])]; n = i1 - i0 + 1; on = COND[r["條件"]][i0:i1 + 1]
    if r["換法"] == "X1":
        a_, W = (r["正2"],), on.astype(float)[:, None]
    elif r["換法"] == "X2":
        a_, W = (r["ETF"], r["正2"]), np.stack([(~on).astype(float), on.astype(float)], 1)
    else:
        raise SystemExit("⛔ 主池出現 X3（問一正2%＝0 時不該有）")
    eq, held, _ = sim(a_, W, firsts(i0, i1), i0)
    cc, mm = pf(eq); lb = lab(cc, mm, *BB[(g, r["段"])])
    mx = max(mx, abs(cc - r["年化"]), abs(mm - r["回落"])); lb_bad += lb != r["標籤"]
    rows2.append({"段": r["段"], "g": g, "條件": r["條件"], "換法": r["換法"], "ETF": r["ETF"], "正2": r["正2"], "c": cc, "m": mm, "r": rt(cc, mm),
                  "lw": float(np.nanmean(held[:, len(a_) - 1])), "lab": lb})
chk("K2b 問二全部列 年化／回落", mx < TOL and lb_bad == 0, f"{len(q2)} 列、最大絕對差 {mx:.1e}、標籤不符 {lb_bad}")
m2 = pd.DataFrame(rows2)
p2 = m2[(m2["段"] == "探索") & (m2["g"] == "A")].reset_index(drop=True)
ok2 = p2[p2["c"] > BB[("A", "探索")][0]].copy(); ok2["o"] = range(len(ok2))
pk2 = ok2.sort_values(["r", "lw", "o"], ascending=[False, True, True]).iloc[0]
s2 = S["問二_探索"]["挑中"]
chk("K3c 問二挑中", (pk2["條件"], pk2["換法"], pk2["ETF"]) == (s2["條件"], s2["換法"], s2["ETF"]), f"{pk2['條件']} {pk2['換法']} {pk2['ETF']}、池 {len(p2)}、年化＞0050 {len(ok2)}")
c2 = m2[(m2["段"] == "確認") & (m2["條件"] == pk2["條件"]) & (m2["換法"] == pk2["換法"]) & (m2["ETF"] == pk2["ETF"]) & (m2["正2"] == pk2["正2"])].iloc[0]
chk("K3d 問二確認段標籤", c2["lab"] == S["確認段"]["問二"]["標籤"], f"{c2['lab']}（{c2['c']:.6f}／{c2['m']:.6f}）")

# K4 假訊號一
cm = mine[mine["段"] == "確認"].copy()
cm["key"] = [tuple(sorted((a, w) for a, w in ((x.ETF, x.e), (x.正2, x.l)) if w > 0)) for x in cm.itertuples()]
u = cm.drop_duplicates("key").reset_index(drop=True)
dr = np.random.default_rng(20260927).integers(0, len(u), 1000)
pp = float(np.mean(u["lab"].to_numpy()[dr] == "合格"))
chk("K4 假訊號一 p", len(u) == 221 and abs(pp - S["假訊號_問一"]["p_合格"]) < 1e-15 and abs(np.mean(u["lab"] == "合格") - S["假訊號_問一"]["母體精確合格比例"]) < 1e-15,
    f"組合 {len(u)}、p {pp}、母體 {np.mean(u['lab'] == '合格'):.4f}")

# K5 假訊號二
z = np.load(os.path.join(OUT, "body_null_q2_states.npz"))
n = int(z["n"]); st = np.unpackbits(z["states"], axis=1)[:, :n].astype(bool)
i0, i1 = SEG[("A", "確認")]
on0 = COND[pk2["條件"]][i0:i1 + 1]


def runs(x):
    out = []; t = 0
    while t < len(x):
        if x[t]:
            s_ = t
            while t < len(x) and x[t]:
                t += 1
            out.append(t - s_)
        else:
            t += 1
    return sorted(out)


r0 = runs(on0); keep = all(runs(s_) == r0 for s_ in st)
nl = pd.read_csv(os.path.join(OUT, "body_null_q2.csv"))
lb2 = []
for s_ in st:
    if pk2["換法"] == "X1":
        a_, W = (pk2["正2"],), s_.astype(float)[:, None]
    else:
        a_, W = (pk2["ETF"], pk2["正2"]), np.stack([(~s_).astype(float), s_.astype(float)], 1)
    eq, _, _ = sim(a_, W, firsts(i0, i1), i0)
    lb2.append(lab(*pf(eq), *BB[("A", "確認")]))
lb2 = np.array(lb2)
chk("K5 假訊號二（1,000 條保段長、逐條標籤、p）", keep and (lb2 == nl["標籤"].to_numpy()).all() and abs(np.mean(lb2 == "合格") - S["假訊號_問二"]["p_合格"]) < 1e-15,
    f"段長保持 {keep}、段數 {len(r0)}、標籤全同 {(lb2 == nl['標籤'].to_numpy()).all()}、p {np.mean(lb2 == '合格')}")

# K6 2022
y0, y1 = ix("2022-01-03"), ix("2022-12-30"); ny = y1 - y0 + 1
rep = {r["對象"]: r for r in S["必報_2022"]}


def y22(eq):
    path = np.concatenate([[1.0], eq[:ny]]); pk = np.maximum.accumulate(path)
    return ((path - pk) / pk).min(), eq[ny - 1] * 1e6


mx = 0.0
for lev in ("00631L", "00685L"):
    eq, _, _ = sim((lev,), np.ones((ny, 1)), np.zeros(ny, bool), y0)
    a_, b_ = y22(eq); r = rep[f"{lev} 單獨（2022-01-03 開盤買進、付成本）"]
    mx = max(mx, abs(a_ - r["2022年內最大回落"]), abs(b_ - r["100萬到2022-12-30"]) / 1e6)
ci0, ci1 = SEG[("A", "確認")]; nn = ci1 - ci0 + 1
eq, _, _ = sim((pk1["ETF"], pk1["正2"]), np.tile([pk1["e"] / 10, pk1["l"] / 10], (nn, 1)), firsts(ci0, ci1), ci0)
a_, b_ = y22(eq); r = rep["確認段 問一格"]; mx = max(mx, abs(a_ - r["2022年內最大回落"]), abs(b_ - r["100萬到2022-12-30"]) / 1e6)
on = COND[pk2["條件"]][ci0:ci1 + 1]
a2 = (pk2["正2"],) if pk2["換法"] == "X1" else (pk2["ETF"], pk2["正2"])
W2 = on.astype(float)[:, None] if pk2["換法"] == "X1" else np.stack([(~on).astype(float), on.astype(float)], 1)
eq, _, _ = sim(a2, W2, firsts(ci0, ci1), ci0)
a_, b_ = y22(eq); r = rep["確認段 問二格"]; mx = max(mx, abs(a_ - r["2022年內最大回落"]), abs(b_ - r["100萬到2022-12-30"]) / 1e6)
chk("K6 2022 必報（00631L、00685L、確認 2 格）", mx < TOL, f"最大差 {mx:.1e}")

# K7 描述臂（問一格：現金 1%、季度）
de = pd.read_csv(os.path.join(OUT, "body_desc.csv"))
mx = 0.0
for sg in ("探索", "確認"):
    i0, i1 = SEG[("A", sg)]; n = i1 - i0 + 1; W = np.tile([pk1["e"] / 10, pk1["l"] / 10], (n, 1))
    for nm, R_, g in (("問一格｜現金年1%", firsts(i0, i1), 1.01 ** (1 / ANN) - 1), ("問一格｜季度再平衡", firsts(i0, i1, q=True), 0.0)):
        cc, mm = pf(sim((pk1["ETF"], pk1["正2"]), W, R_, i0, cash_g=g)[0])
        r = de[(de["段"] == sg) & (de["臂"] == nm)].iloc[0]; mx = max(mx, abs(cc - r["年化"]), abs(mm - r["回落"]))
chk("K7 描述臂（問一格 現金1%／季度）", mx < TOL, f"最大差 {mx:.1e}")

json.dump({"結果": res, "不過": bad}, open(os.path.join(OUT, "check_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("⛔ 有不過：" + "、".join(bad) if bad else "✅ 全過")
sys.exit(1 if bad else 0)
