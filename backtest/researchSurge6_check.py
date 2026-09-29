# -*- coding: utf-8 -*-
"""researchSurge6 的獨立查核（⛔ 不 import researchSurge6、researchSurge5 的計算函式；常數在此另寫一次）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSurge6_check.py

⓪ 期間：events.npz 的起漲日全部在 2021-01-01～2026-08-31
① 抽 8 檔（固定種子）：自己算壞根、定義域、250 格事件（逐日掃、鏈從 2021 第一個交易日起、跳過 H 日）、P、花幾天、H 內最大漲幅、P 後回落 30／50% 天數 ⇒ 對 s6work/events.npz
② 網格：抽 12 格 × 2 段，自己從事件與定義域算 ⇒ 對 grid.csv
③ 提升倍數：抽 4 個級距 × 5 格 × 探索段（pandas 逐列 groupby 月份，95%）＋ 第一個進確認段級距 × 3 格 × 確認段（Bonferroni）⇒ 對 feat_cells.csv.gz
④ 挑選重數：由 feat_cells.csv.gz 自己數「探索 下緣＞1 且 涵蓋≥5%」≥125 格 ⇒ 對 feat_summary 的進確認段；確認B 下緣＞1 ≥125 ⇒ 對站得住；k、N 對 summary_feat.json
⑤ ③：2 個級距 h＝60 探索段對基準② 超額（十分位自己分）＋ 全體淨報酬 h＝60 確認段 ⇒ 對 curves.csv.gz
⑥ 妖股：r_20 Q5、回落 50%、探索段 250 格提升倍數中位 ⇒ 對 yao_summary.csv
⑦ 結束可交易（若有站得住）：確認段第一個級距 h＝60 A−B 平均與 n ⇒ 對 end_trade.csv
⑧ 右截斷：自算 hdef6 ＝ min(seq5 hdef, 2026-08-31 索引 − t) ⇒ 對 s6work/hdef6.npy（全表）；所有事件 t＋H ≤ 2026-08-31
⑨ 量縮 D1：全期 F1 事件與全體股-日「前 60 日曾量縮」自算（pandas rolling）⇒ 對 shrink_D1.csv
（全部照 2026-08-31 右截斷：定義域、R_h、P 後觀察期）
⇒ backtest/resultsSurge6/check.json
"""
import json
import os
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D

ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
WORK5 = os.path.expanduser("~/s5work"); WORK6 = os.path.expanduser("~/s6work")
OUT = "backtest/resultsSurge6"
HS = list(range(10, 251, 10)); GS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0]
SEG = {"探索": ((2021, 1), (2023, 12)), "確認": ((2024, 1), (2026, 8))}
Z = 1.959963984540054
D.DATA = ST; cal = D.load_calendar(); n = len(cal)
t0 = int(cal.searchsorted(pd.Timestamp("2021-01-01"))); t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
mon = np.array([d.year * 12 + d.month - 1 for d in cal])
DM = {k: (mon >= a[0] * 12 + a[1] - 1) & (mon <= b[0] * 12 + b[1] - 1) for k, (a, b) in SEG.items()}
uni = pd.read_csv(os.path.join(WORK5, "uni.csv"), dtype=str); sidx = {s: i for i, s in enumerate(uni["stock_id"])}
FC = json.load(open(os.path.join(WORK5, "build.json"), encoding="utf-8"))["特徵欄"]; FX = {c: i for i, c in enumerate(FC)}
Q = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Rm = np.load(os.path.join(WORK5, "R.npy"), mmap_mode="r")
bar = np.load(os.path.join(WORK5, "bar.npy")); hdef5 = np.load(os.path.join(WORK5, "hdef.npy"))
hdef = np.load(os.path.join(WORK6, "hdef6.npy"))
E = dict(np.load(os.path.join(WORK6, "events.npz")))
errs = []; info = {}
rng = np.random.default_rng(20260930)

# ⓪ ⑧
mine_h = np.clip(np.minimum(hdef5.astype(np.int64), t1 - np.arange(n)[None, :]), 0, 250)
info["⑧ hdef6 不同股日"] = int((mine_h != hdef).sum())
if info["⑧ hdef6 不同股日"]:
    errs.append("⑧ hdef6 不同")
Hs = np.array(HS)[E["cell"].astype(int) // 10]
if (E["d"].astype(int) + Hs > t1).any():
    errs.append("⑧ 有事件 t＋H 超過 2026-08-31")
del mine_h
info["⓪ 起漲日範圍"] = [str(cal[int(E["d"].min())].date()), str(cal[int(E["d"].max())].date())]
if E["d"].min() < t0 or E["d"].max() > t1:
    errs.append("⓪ 起漲日超出 2021-01～2026-08")

# ①
act = bar[:, t0:t1 + 1].sum(1)
cand = [s for s in uni["stock_id"] if act[sidx[s]] > 300]
smp = list(rng.choice(cand, size=8, replace=False)); info["抽樣"] = smp
nev = [0, 0]
for s in smp:
    si = sidx[s]; st = D.load_stock(s, uni.loc[si, "market"], cal); df = st.df
    c = df["close"]; idx = np.flatnonzero(c.notna().to_numpy()); dts = cal[idx]
    raw = pd.read_csv(os.path.join(ST, "stocks", s + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rc = pd.to_numeric(raw["close"], errors="coerce").iloc[idx].to_numpy(float)
    bad = np.zeros(len(idx), bool); adj = D.load_adj(s)
    if adj is not None:
        for d_, f_ in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dts, d_))
            if 0 < k < len(idx) and np.isfinite(rc[k]) and np.isfinite(rc[k - 1]) and f_ > 0 and not (0.895 <= rc[k] / (rc[k - 1] * f_) <= 1.105):
                bad[k] = True
    for b in D.breakpoints(df, st.event_dates):
        if "price" in b["rule"]:
            bad[int(np.searchsorted(idx, b["pos"]))] = True
    cff = c.ffill().to_numpy(float); last = int(idx[-1])
    badday = np.zeros(n + 1, bool); badday[idx[bad]] = True
    nb_after = np.full(n + 2, 10 ** 9)
    for p in range(n - 1, -1, -1):
        nb_after[p] = p if badday[p] else nb_after[p + 1]
    myh = {int(p): max(0, min(250, n - 1 - p, nb_after[p + 1] - 1 - p, t1 - p)) for p in idx}
    if not np.array_equal(np.array([myh[int(p)] for p in idx]), hdef[si, idx]):
        errs.append(f"① {s} 定義域不同")
    myev = []
    for hi, H in enumerate(HS):
        for gi, g in enumerate(GS):
            lastE = -10 ** 9
            for p in idx:
                p = int(p)
                if p < t0 or p > t1 or myh[p] < H or p - lastE <= H:
                    continue
                w = cff[p + 1:p + H + 1]
                if w.max() >= cff[p] * (1 + g) * (1 - 1e-9):
                    P = p + 1 + int(np.argmax(w)); dg = int(np.argmax(w >= cff[p] * (1 + g) * (1 - 1e-9))) + 1
                    endobs = min(last, nb_after[P + 1] - 1, n - 1, t1); aft = cff[P + 1:endobs + 1]
                    d30 = np.flatnonzero(aft <= cff[P] * 0.7); d50 = np.flatnonzero(aft <= cff[P] * 0.5)
                    myev.append((hi * 10 + gi, p, P, dg, int(d30[0]) + 1 if len(d30) else -1, int(d50[0]) + 1 if len(d50) else -1, round(float(w.max() / cff[p] - 1), 4)))
                    lastE = p
    k = np.flatnonzero(E["s"] == si)
    ref = sorted(zip(E["cell"][k].astype(int), E["d"][k].astype(int), E["P"][k].astype(int), E["dg"][k].astype(int), E["dd30"][k].astype(int), E["dd50"][k].astype(int),
                     np.round(E["M"][k].astype(float), 4)))
    mine = sorted(myev); nev[0] += len(mine)
    if len(mine) != len(ref) or any(x[:6] != y[:6] or abs(x[6] - y[6]) > 2e-4 for x, y in zip(mine, ref)):
        nev[1] += 1; errs.append(f"① {s} 事件 自算 {len(mine)} 檔 {len(ref)}")
info["① 事件（自算事件數／不同檔數）"] = nev

# ②
G = pd.read_csv(os.path.join(OUT, "grid.csv")); ng = 0
for sg, dm in DM.items():
    rows = bar & dm[None, :]
    for cc in rng.choice(250, 12, replace=False):
        H = HS[cc // 10]; g = GS[cc % 10]
        den = int((hdef[rows] >= H).sum()); ev = int(((E["cell"] == cc) & dm[E["d"].astype(int)]).sum())
        r = G[(G["段"] == sg) & (G["H"] == H) & np.isclose(G["g"], g)].iloc[0]
        if ev != int(r["事件"]) or den != int(r["定義域股日"]):
            ng += 1; errs.append(f"② {sg} H{H} g{g}：自算 {ev}/{den} 檔 {r['事件']}/{r['定義域股日']}")
info["② 網格 不同（24 個）"] = ng

# ③④
A = pd.read_csv(os.path.join(OUT, "feat_cells.csv.gz"))
SMR = pd.read_csv(os.path.join(OUT, "feat_summary.csv")); SJ = json.load(open(os.path.join(OUT, "summary_feat.json"), encoding="utf-8"))
ev = pd.DataFrame({"cell": E["cell"].astype(int), "s": E["s"].astype(int), "d": E["d"].astype(int)})
ekey = {c_: set(zip(g["s"], g["d"])) for c_, g in ev.groupby("cell")}
cname = lambda c_: f"H{HS[c_ // 10]}_g{int(round(GS[c_ % 10] * 100))}%"


def lift_self(col, code, sg, cells, z):
    q = np.asarray(Q[FX[col]]); dm = DM[sg]
    rows = np.argwhere(bar & dm[None, :] & (q > 0))
    dfr = pd.DataFrame({"s": rows[:, 0], "d": rows[:, 1]}); dfr["code"] = q[dfr["s"], dfr["d"]]; dfr["h"] = hdef[dfr["s"], dfr["d"]]; dfr["m"] = mon[dfr["d"]]
    out = []
    for c_ in cells:
        sub = dfr[dfr["h"] >= HS[c_ // 10]].copy(); key = ekey.get(c_, set())
        sub["y"] = [(a_, b_) in key for a_, b_ in zip(sub["s"], sub["d"])]
        base = sub["y"].mean(); g = sub[sub["code"] == code]; p = g["y"].mean()
        mm = g.groupby("m")["y"].agg(["sum", "size"]); se = np.sqrt(((mm["sum"] - p * mm["size"]) ** 2).sum()) / len(g)
        out.append((c_, (p / base, (p - z * se) / base, g["y"].sum() / sub["y"].sum())))
    return out


nl = 0; nt = 0
for col, code in (("r_20", 5), ("amt_60", 1), ("yoy", 5), ("turn_20", 5)):
    for c_, mine in lift_self(col, code, "探索", (51, 0, 113, 240, 25), Z):
        r = A[(A["欄"] == col) & (A["碼"] == code) & (A["段"] == "探索") & (A["格"] == cname(c_))].iloc[0]; nt += 1
        if not np.allclose(mine, (r["提升"], r["下緣"], r["涵蓋率"]), rtol=1e-3, equal_nan=True):
            nl += 1; errs.append(f"③ {col} Q{code} {cname(c_)}：自算 {mine} 檔 {(r['提升'], r['下緣'], r['涵蓋率'])}")
kB = SJ["Bonferroni k（飆股）"]
PKs = SMR[SMR["進確認段"] == True]
if len(PKs):
    r0 = PKs.iloc[0]; zB = NormalDist().inv_cdf(1 - 0.025 / kB)
    for c_, mine in lift_self(r0["欄"], int(r0["碼"]), "確認", (51, 130, 245), zB):
        r = A[(A["欄"] == r0["欄"]) & (A["碼"] == int(r0["碼"])) & (A["段"] == "確認B") & (A["格"] == cname(c_))].iloc[0]; nt += 1
        if not np.allclose(mine, (r["提升"], r["下緣"], r["涵蓋率"]), rtol=1e-3, equal_nan=True):
            nl += 1; errs.append(f"③ 確認B {r0['欄']} Q{r0['碼']} {cname(c_)}：自算 {mine} 檔 {(r['提升'], r['下緣'], r['涵蓋率'])}")
info[f"③ 提升倍數 不同（{nt} 個）"] = nl
X = A[A["段"] == "探索"]; X = X[~X["欄"].str.startswith("d_")]
cnt = X.assign(ok=(X["下緣"] > 1) & (X["涵蓋率"] >= 0.05)).groupby(["欄", "碼"])["ok"].sum()
myPK = {kk for kk, v in cnt.items() if v >= 125}
refPK = {(c_, int(q_)) for c_, q_ in zip(PKs["欄"], PKs["碼"])}
Y = A[A["段"] == "確認B"]; cb = Y.assign(ok=Y["下緣"] > 1).groupby(["欄", "碼"])["ok"].sum()
mySt = {kk for kk, v in cb.items() if v >= 125}
refSt = {(c_, int(q_)) for c_, q_, f_ in zip(SMR["欄"], SMR["碼"], SMR.get("站得住（確認，Bonferroni）", pd.Series(False, index=SMR.index)).fillna(False)) if f_}
info["④ 進確認段（自數／檔／k）"] = [len(myPK), len(refPK), kB]; info["④ 站得住（自數／檔）"] = [len(mySt), len(refSt)]
if myPK != refPK or len(refPK) != kB:
    errs.append("④ 進確認段集合不同")
if mySt != refSt:
    errs.append("④ 站得住集合不同")
NS = SJ["N_單筆"]; comp = SJ["N 組成"]
if NS != comp["飆股"] + sum(comp["妖股"].values()) + sum(comp["結束"].values()):
    errs.append("④ N 加總不符")

# ⑤
C = pd.read_csv(os.path.join(OUT, "curves.csv.gz"))
r60 = np.where(hdef >= 60, np.asarray(Rm[11]), np.nan); r5 = np.where(hdef >= 5, np.asarray(Rm[0]), np.nan); r20 = np.load(os.path.join(WORK5, "r20c.npy")); nc = 0
dm = DM["探索"]
for col, code in (("r_20", 5), ("amt_60", 1)):
    q = np.asarray(Q[FX[col]]); xs = []; ms = []
    for t in np.flatnonzero(dm):
        b = bar[:, t]; ok10 = b & np.isfinite(r5[:, t]) & np.isfinite(r20[:, t])
        v = pd.Series(np.where(ok10, r20[:, t], np.nan)); k = v.notna().sum()
        if k == 0:
            continue
        ordr = np.lexsort((np.arange(len(v)), v.fillna(np.inf).to_numpy()))[:k]
        dec = np.full(len(v), -1); dec[ordr] = (np.arange(k) * 10) // k
        y = r60[:, t]; fin = b & np.isfinite(y) & (dec >= 0)
        for d_ in range(10):
            g = fin & (dec == d_)
            if g.sum() < 2:
                continue
            tot = y[g].sum(); cn = g.sum()
            for i in np.flatnonzero(g & (q[:, t] == code)):
                xs.append(y[i] - (tot - y[i]) / (cn - 1)); ms.append(mon[t])
    xs = np.array(xs); ms = np.array(ms); mu = xs.mean(); se = np.sqrt((pd.Series(xs - mu).groupby(ms).sum() ** 2).sum()) / len(xs)
    r = C[(C["欄"] == col) & (C["碼"] == code) & (C["段"] == "探索") & (C["h"] == 60)].iloc[0]
    if not np.allclose((mu, mu - Z * se), (r["對基準②"], r["對基準②_下"]), rtol=1e-3):
        nc += 1; errs.append(f"⑤ {col} Q{code}：自算 {mu:.6f}/{mu - Z * se:.6f} 檔 {r['對基準②']:.6f}/{r['對基準②_下']:.6f}")
dm = DM["確認"]; rows = bar & dm[None, :] & np.isfinite(r60)
v = r60[rows] - 0.00585; mm = mon[np.nonzero(rows)[1]]; mu = v.mean()
se = np.sqrt((pd.Series(v - mu).groupby(mm).sum() ** 2).sum()) / len(v)
r = C[(C["欄"] == "全體") & (C["段"] == "確認") & (C["h"] == 60)].iloc[0]
if not np.allclose((mu, mu - Z * se), (r["淨報酬"], r["淨報酬_下"]), rtol=1e-3):
    nc += 1; errs.append(f"⑤ 全體 確認 h60：自算 {mu:.6f} 檔 {r['淨報酬']:.6f}")
info["⑤ ③ 曲線 不同（3 個）"] = nc

# ⑥
YR = pd.read_csv(os.path.join(OUT, "yao_summary.csv"))
q = np.asarray(Q[FX["r_20"]]); dmx = DM["探索"]; ed = E["d"].astype(int); es = E["s"].astype(int)
code_e = q[es, ed]; hit = E["dd50"] > 0; inx = dmx[ed]; lifts = []
for c_ in range(250):
    m_ = (E["cell"] == c_) & inx & (code_e > 0)
    if m_.sum() == 0 or hit[m_].sum() == 0:
        lifts.append(np.nan); continue
    mc = m_ & (code_e == 5)
    lifts.append((hit[mc].sum() / mc.sum()) / (hit[m_].sum() / m_.sum()) if mc.sum() else np.nan)
mine = float(np.nanmedian(lifts))
r = YR[(YR["回落"] == "50%") & (YR["欄"] == "r_20") & (YR["碼"] == 5)].iloc[0]
info["⑥ 妖股 r_20 Q5 回落50% 探索 提升中位（自算／檔）"] = [mine, float(r["探索_提升中位"])]
if not np.isclose(mine, r["探索_提升中位"], rtol=1e-3):
    errs.append("⑥ 妖股提升中位不同")

# ⑦
p_ = os.path.join(OUT, "end_trade_summary.csv")
if os.path.exists(p_) and os.path.getsize(p_) > 2:
    SMY = pd.read_csv(p_); DT = pd.read_csv(os.path.join(OUT, "end_trade.csv"))
    r0 = SMY[SMY["段"] == "確認"].iloc[0]; col, code = r0["欄"], int(r0["碼"])
    dm = DM["確認"]
    st_ = pd.DataFrame({"s": es, "d": ed})[dm[ed]].drop_duplicates()
    q = np.asarray(Q[FX[col]]); vals = []; mons = []
    for s, g in st_.groupby("s"):
        df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
        o = df["open"].to_numpy(float); sig = np.flatnonzero(q[s] == code)
        for t in g["d"]:
            B = float(Rm[11, s, t])
            if not np.isfinite(B) or hdef[s, t] < 60:
                continue
            nx = sig[sig > t]; A_ = B
            if len(nx) and nx[0] <= t + 59:
                e = nx[0] + 1
                while e < n and not (np.isfinite(o[e]) and o[e] > 0):
                    e += 1
                if e <= t + 60:
                    A_ = o[e] / o[t + 1] - 1
            vals.append(A_ - B); mons.append(mon[t])
    v = np.array(vals); mu = v.mean()
    ref = DT[(DT["欄"] == col) & (DT["碼"] == code) & (DT["段"] == "確認") & (DT["h"] == 60)].iloc[0]
    info["⑦ 結束可交易（級距、h60 確認：自算平均／檔／自算 n／檔 n）"] = [f"{col} {code}", float(mu), float(ref["A−B"]), int(len(v)), int(ref["n"])]
    if not (np.isclose(mu, ref["A−B"], rtol=1e-4, atol=1e-7) and len(v) == int(ref["n"])):
        errs.append("⑦ 結束可交易 不同")
else:
    info["⑦ 結束可交易"] = "沒有站得住的結束特徵 ⇒ 不查"
# ⑨
S1 = pd.read_csv(os.path.join(OUT, "shrink_D1.csv"))
x = np.asarray(np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")[FX["d_shrink"]])
dmA = DM["探索"] | DM["確認"]
k = np.flatnonzero((E["cell"] == 51) & dmA[ed]); k = k[np.isfinite(x[es[k], ed[k]]) & bar[es[k], ed[k]]]
a60 = np.array([bool((x[s_, max(0, t_ - 59):t_ + 1] == 1).any()) for s_, t_ in zip(es[k], ed[k])])
r = S1[(S1["段"] == "全期") & (S1["對象"].str.startswith("F1（"))].iloc[0]
info["⑨ 量縮 F1 全期 前60日曾量縮（自算／檔）"] = [float(a60.mean()), float(r["前60日曾量縮"]), int(len(k)), int(r["n"])]
if not (np.isclose(a60.mean(), r["前60日曾量縮"], rtol=1e-4) and len(k) == int(r["n"])):
    errs.append("⑨ 量縮 D1 F1 不同")
rows = np.isfinite(x) & bar & dmA[None, :]
sh = pd.DataFrame(x == 1).T.rolling(60, min_periods=1).max().T.to_numpy() > 0
r = S1[(S1["段"] == "全期") & (S1["對象"] == "全體股-日")].iloc[0]
info["⑨ 量縮 全體 全期（自算／檔）"] = [float(sh[rows].mean()), float(r["前60日曾量縮"])]
if not np.isclose(sh[rows].mean(), r["前60日曾量縮"], rtol=1e-4):
    errs.append("⑨ 量縮 D1 全體 不同")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:60]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:20]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
