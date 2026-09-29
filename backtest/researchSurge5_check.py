# -*- coding: utf-8 -*-
"""researchSurge5 的獨立查核（⛔ 不 import researchSurge5 的計算函式；常數在此另寫一次）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSurge5_check.py [--part desc|feat|all]

① 抽 8 檔（固定種子）：自己用 pandas 從接合版面算 12 個特徵 ⇒ 對 F 面板（兩邊都有值處 rtol 1e-4）
② 同 8 檔：自己算壞根、定義域、250 格事件（逐日掃、跳過 H 日）、H 內最大漲幅、P、花幾天、P 後回落 30／50% 天數 ⇒ 對 events.npz
③ 同 8 檔：R_h（h＝5、60、250）⇒ 對 R 面板
④ 五等分：抽 6 個特徵 × 5 天，pandas rank(method="min") 自算 ⇒ 對 Q
⑤ 網格：抽 12 格 × 3 段，自己從事件與定義域算比例 ⇒ 對 grid.csv；最大漲幅分段計數 ⇒ 對 maxgain.csv
⑥（feat）提升倍數：抽 4 個級距 × 5 格 × 探索段，pandas 逐列 groupby 月份自算 ①（含 95% 下緣）與 ② ⇒ 對 feat_cells.csv.gz
⑦（feat）③：抽 2 個級距，h＝60，探索段，自算對基準② 超額（十分位自己分）⇒ 對 curves.csv.gz
⇒ backtest/resultsSurge5/check_<part>.json
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R11

ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
MAIN = os.path.expanduser("~/h2data/surge_b53f5540a8ad/data")
WORK = os.environ.get("S5WORK", os.path.expanduser("~/s5work"))
OUT = "backtest/resultsSurge5"
HS = list(range(10, 251, 10)); GS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0]
SEG = {"探索": ("2017-01", "2021-12"), "確認": ("2022-01", "2026-08"), "早年": ("2005-01", "2014-12")}
ap = argparse.ArgumentParser(); ap.add_argument("--part", default="desc"); a = ap.parse_args()
D.DATA = ST; cal = D.load_calendar(); n = len(cal)
uni = pd.read_csv(os.path.join(WORK, "uni.csv"), dtype=str); sidx = {s: i for i, s in enumerate(uni["stock_id"])}
bj = json.load(open(os.path.join(WORK, "build.json"), encoding="utf-8")); FC = bj["特徵欄"]; FX = {c: i for i, c in enumerate(FC)}
F = np.load(os.path.join(WORK, "F.npy"), mmap_mode="r"); Q = np.load(os.path.join(WORK, "Q.npy"), mmap_mode="r"); Rm = np.load(os.path.join(WORK, "R.npy"), mmap_mode="r")
bar = np.load(os.path.join(WORK, "bar.npy")); hdef = np.load(os.path.join(WORK, "hdef.npy"))
E = dict(np.load(os.path.join(WORK, "events.npz")))
errs = []; info = {}
rng = np.random.default_rng(20260929)
cand = [s for s in uni["stock_id"] if bar[sidx[s]].sum() > 1500]
smp = list(rng.choice(cand, size=8, replace=False))
info["抽樣"] = smp
m50 = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy()


def cmp(name, mine, ref, tol=1e-4):
    both = np.isfinite(mine) & np.isfinite(ref)
    bad = both & ~np.isclose(mine, ref, rtol=tol, atol=1e-9)
    return int(both.sum()), int(bad.sum())


if a.part in ("desc", "all"):
    nf = {}; nev = [0, 0]; nret = 0
    for s in smp:
        si = sidx[s]; mk = uni.loc[si, "market"]
        st = D.load_stock(s, mk, cal); df = st.df
        c = df["close"]; idx = np.flatnonzero(c.notna().to_numpy())
        cb = c.iloc[idx].reset_index(drop=True); h = df["high"].iloc[idx].reset_index(drop=True); l = df["low"].iloc[idx].reset_index(drop=True)
        amt = pd.to_numeric(df["amount"], errors="coerce").iloc[idx].reset_index(drop=True)
        vol = pd.to_numeric(df["volume"], errors="coerce").iloc[idx].reset_index(drop=True)
        raw = pd.read_csv(os.path.join(ST, "stocks", s + ".csv"), dtype={"date": str}, usecols=["date", "close", "shares", "open", "high", "low"]).drop_duplicates("date")
        raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
        sh = pd.to_numeric(raw["shares"], errors="coerce").ffill(); sh = sh.where(sh > 0).iloc[idx].reset_index(drop=True)
        # 自算壞根：幽靈還原 ＋ 價格斷點
        rc = pd.to_numeric(raw["close"], errors="coerce").iloc[idx].to_numpy(float)
        dts = cal[idx]; bad = np.zeros(len(idx), bool)
        adj = D.load_adj(s)
        if adj is not None:
            for d_, f_ in zip(adj["date"], adj["factor"].astype(float)):
                k = int(np.searchsorted(dts, d_))
                if 0 < k < len(idx) and np.isfinite(rc[k]) and np.isfinite(rc[k - 1]) and f_ > 0 and not (0.895 <= rc[k] / (rc[k - 1] * f_) <= 1.105):
                    bad[k] = True
        for b in D.breakpoints(df, st.event_dates):
            if "price" in b["rule"]:
                bad[int(np.searchsorted(idx, b["pos"]))] = True
        mine = {}
        mine["r_20"] = cb / cb.shift(20) - 1
        mine["dhi_60"] = cb / cb.rolling(60).max() - 1
        mine["ma_120"] = cb / cb.rolling(120).mean() - 1
        mine["ar_5"] = amt / amt.shift(1).rolling(5).mean()
        mine["achg_20"] = amt.rolling(20).mean() / amt.rolling(20).mean().shift(20)
        mine["amt_60"] = amt.rolling(60).mean()
        mine["turn_20"] = (vol / sh).rolling(20).mean()
        mine["rng_10"] = cb.rolling(10).max() / cb.rolling(10).min() - 1
        rm = pd.Series(m50[idx]).pct_change(); rs = cb.pct_change(); dn = rm < 0
        mine["anti_60"] = (rs - rm).where(dn, 0).rolling(60).sum() / dn.astype(float).rolling(60).sum()
        mine["price"] = pd.Series(rc)
        spans = {"r_20": 21, "dhi_60": 61, "ma_120": 121, "ar_5": 6, "achg_20": 41, "amt_60": 61, "turn_20": 21, "rng_10": 11, "anti_60": 61, "price": 1}
        cbad = np.r_[0, np.cumsum(bad)]
        for k_, v in mine.items():
            vv = v.to_numpy(float).copy(); kk = np.arange(len(idx)); sp = spans[k_]
            vv[(cbad[kk + 1] - cbad[np.maximum(kk + 1 - sp, 0)]) > 0] = np.nan
            vv[~np.isfinite(vv)] = np.nan
            nb, nbad = cmp(k_, vv, np.asarray(F[FX[k_], si, idx], float))
            x = nf.setdefault(k_, [0, 0]); x[0] += nb; x[1] += nbad
        # ② 事件
        cff = c.ffill().to_numpy(float); last = int(idx[-1])
        badday = np.zeros(n + 1, bool); badday[idx[bad]] = True
        nb_after = np.full(n + 2, 10 ** 9)
        for p in range(n - 1, -1, -1):
            nb_after[p] = p if badday[p] else nb_after[p + 1]
        myh = {int(p): max(0, min(250, n - 1 - p, nb_after[p + 1] - 1 - p)) for p in idx}
        ref_h = hdef[si, idx]
        if not np.array_equal(np.array([myh[int(p)] for p in idx]), ref_h):
            errs.append(f"② {s} 定義域不同")
        myev = []
        for hi, H in enumerate(HS):
            for gi, g in enumerate(GS):
                lastE = -10 ** 9
                for p in idx:
                    p = int(p)
                    if myh[p] < H or p - lastE <= H:
                        continue
                    w = cff[p + 1:p + H + 1]
                    if w.max() >= cff[p] * (1 + g) * (1 - 1e-9):
                        P = p + 1 + int(np.argmax(w)); dg = int(np.argmax(w >= cff[p] * (1 + g) * (1 - 1e-9))) + 1
                        endobs = min(last, nb_after[P + 1] - 1, n - 1); aft = cff[P + 1:endobs + 1]
                        d30 = np.flatnonzero(aft <= cff[P] * 0.7); d50 = np.flatnonzero(aft <= cff[P] * 0.5)
                        myev.append((hi * 10 + gi, p, P, dg, int(d30[0]) + 1 if len(d30) else -1, int(d50[0]) + 1 if len(d50) else -1, round(float(w.max() / cff[p] - 1), 4)))
                        lastE = p
        k = np.flatnonzero(E["s"] == si)
        ref = sorted(zip(E["cell"][k].astype(int), E["d"][k].astype(int), E["P"][k].astype(int), E["dg"][k].astype(int), E["dd30"][k].astype(int), E["dd50"][k].astype(int),
                         np.round(E["M"][k].astype(float), 4)))
        mine_ = sorted(myev)
        nev[0] += len(mine_)
        if len(mine_) != len(ref) or any(x[:6] != y[:6] or abs(x[6] - y[6]) > 2e-4 for x, y in zip(mine_, ref)):
            nev[1] += 1; errs.append(f"② {s} 事件 自算 {len(mine_)} 檔 {len(ref)}")
        # ③ 報酬
        o = df["open"].to_numpy(float); lockd = np.zeros(n, bool)
        ro, rh, rl = (pd.to_numeric(raw[x], errors="coerce").to_numpy(float) for x in ("open", "high", "low"))
        rcl = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float)
        for kk in range(1, len(idx)):
            p = idx[kk]; pv = idx[kk - 1]
            if np.isfinite(rcl[pv]) and np.isfinite(ro[p]) and np.isfinite(rh[p]) and np.isfinite(rl[p]):
                lp = R11.limit_price(rcl[pv], True, 0.07 if cal[p] < pd.Timestamp("2015-06-01") else 0.10)
                lockd[p] = abs(ro[p] - lp) < 1e-6 and abs(rh[p] - lp) < 1e-6 and abs(rl[p] - lp) < 1e-6
        skipd = set()
        if adj is not None:
            for d_ in adj["date"]:
                kx = int(np.searchsorted(dts, d_))
                if kx < len(idx):
                    skipd.add(int(idx[kx]))
        if dts[0] > pd.Timestamp("2015-01-12"):
            skipd |= set(int(x) for x in idx[:5])
        for j, hh in ((0, 5), (11, 60), (49, 250)):
            mine_r = np.full(n, np.nan)
            for p in idx:
                p = int(p)
                if p + 1 < n and myh[p] >= hh and np.isfinite(o[p + 1]) and o[p + 1] > 0 and not (lockd[p + 1] and (p + 1) not in skipd):
                    mine_r[p] = cff[p + hh] / o[p + 1] - 1
            nb, nbad = cmp("R", mine_r[idx], np.asarray(Rm[j, si, idx], float))
            nm_ = np.isfinite(mine_r[idx]) != np.isfinite(np.asarray(Rm[j, si, idx], float))
            if nbad or nm_.sum():
                errs.append(f"③ {s} h{hh} 值不同 {nbad}、有無不同 {int(nm_.sum())}"); nret += 1
    info["① 特徵（比對列／不同）"] = nf; info["② 事件（自算事件數／不同檔數）"] = nev; info["③ 報酬 不同檔×h"] = nret
    for k_, (nb, nbad) in nf.items():
        if nbad > 0.001 * max(nb, 1):
            errs.append(f"① {k_} 不同 {nbad}/{nb}")
    # ④ 五等分
    nq = 0
    for col in ("r_20", "amt_60", "lu_20", "yoy", "dhi_250", "kdrun"):
        for t in rng.choice(np.flatnonzero(bar.sum(0) > 500), 5, replace=False):
            b = bar[:, t]; x = pd.Series(np.asarray(F[FX[col], :, t], float))[b]
            k = x.notna().sum(); rk = x.rank(method="min") - 1
            mine = np.where(x.notna(), (rk * 5 // k + 1), 0).astype(int)
            if not np.array_equal(mine, np.asarray(Q[FX[col], :, t])[b].astype(int)):
                nq += 1; errs.append(f"④ {col} {cal[t].date()}")
    info["④ 五等分 不同（30 個）"] = nq
    # ⑤ 網格
    G = pd.read_csv(os.path.join(OUT, "grid.csv"))
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); ng = 0
    for sg, (x0, x1) in SEG.items():
        p0, p1 = pd.Period(x0), pd.Period(x1)
        dm = (mon >= p0.year * 12 + p0.month - 1) & (mon <= p1.year * 12 + p1.month - 1)
        rows = bar & dm[None, :]
        for c in rng.choice(250, 12, replace=False):
            H = HS[c // 10]; g = GS[c % 10]
            den = int((hdef[rows] >= H).sum()); ev = int(((E["cell"] == c) & dm[E["d"].astype(int)]).sum())
            r = G[(G["段"] == sg) & (G["H"] == H) & np.isclose(G["g"], g)].iloc[0]
            if ev != int(r["事件"]) or den != int(r["定義域股日"]):
                ng += 1; errs.append(f"⑤ {sg} H{H} g{g}：自算 {ev}/{den} 檔 {r['事件']}/{r['定義域股日']}")
        k = np.flatnonzero(dm[E["d"].astype(int)])
        u = pd.DataFrame({"key": E["s"][k].astype(np.int64) * 100000 + E["d"][k].astype(int), "M250": E["M250"][k]}).groupby("key")["M250"].first().to_numpy(float)
        u = u[np.isfinite(u)]
        MG = pd.read_csv(os.path.join(OUT, "maxgain.csv")); r = MG[(MG["段"] == sg) & (MG["口徑"] == "250日內最大漲幅")].iloc[0]
        mine = np.histogram(u, bins=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, np.inf])[0]
        refc = r[["50～100%", "100～150%", "150～200%", "200～250%", "250～300%", "300～400%", "400～500%", "500～700%", "700～1000%", "≥1000%"]].to_numpy(int)
        if not np.array_equal(mine, refc):
            ng += 1; errs.append(f"⑤ 最大漲幅 {sg}")
    info["⑤ 網格＋最大漲幅 不同"] = ng

if a.part in ("feat", "all"):
    A = pd.read_csv(os.path.join(OUT, "feat_cells.csv.gz"))
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); dm = (mon >= 2017 * 12) & (mon <= 2021 * 12 + 11)
    ev = pd.DataFrame({"cell": E["cell"].astype(int), "s": E["s"].astype(int), "d": E["d"].astype(int)})
    nl = 0
    for col, code in (("r_20", 5), ("amt_60", 1), ("yoy", 5), ("lu_60", 5)):
        q = np.asarray(Q[FX[col]])
        rows = np.argwhere(bar & dm[None, :] & (q > 0))
        dfr = pd.DataFrame({"s": rows[:, 0], "d": rows[:, 1]}); dfr["code"] = q[dfr["s"], dfr["d"]]; dfr["h"] = hdef[dfr["s"], dfr["d"]]; dfr["m"] = mon[dfr["d"]]
        for c in (5 * 10 + 1, 0, 11 * 10 + 3, 24 * 10 + 0, 2 * 10 + 5):
            H = HS[c // 10]
            sub = dfr[dfr["h"] >= H].copy()
            e = ev[ev["cell"] == c]; key = set(zip(e["s"], e["d"]))
            sub["y"] = [(s_, d_) in key for s_, d_ in zip(sub["s"], sub["d"])]
            base = sub["y"].mean(); g = sub[sub["code"] == code]
            p = g["y"].mean(); mm = g.groupby("m")["y"].agg(["sum", "size"])
            se = np.sqrt(((mm["sum"] - p * mm["size"]) ** 2).sum()) / len(g)
            mine = (p / base, (p - 1.959963984540054 * se) / base, g["y"].sum() / sub["y"].sum())
            r = A[(A["欄"] == col) & (A["碼"] == code) & (A["段"] == "探索") & (A["格"] == f"H{H}_g{int(round(GS[c % 10] * 100))}%")].iloc[0]
            if not np.allclose(mine, (r["提升"], r["下緣"], r["涵蓋率"]), rtol=1e-3, equal_nan=True):
                nl += 1; errs.append(f"⑥ {col} Q{code} 格{c}：自算 {mine} 檔 {(r['提升'], r['下緣'], r['涵蓋率'])}")
    info["⑥ 提升倍數 不同（20 個）"] = nl
    C = pd.read_csv(os.path.join(OUT, "curves.csv.gz"))
    r60 = np.asarray(Rm[11]); r5 = np.asarray(Rm[0]); r20 = np.load(os.path.join(WORK, "r20c.npy"))
    nc = 0
    for col, code in (("r_20", 5), ("amt_60", 1)):
        q = np.asarray(Q[FX[col]]); xs = []; ms = []
        for t in np.flatnonzero(dm):
            b = bar[:, t]
            ok10 = b & np.isfinite(r5[:, t]) & np.isfinite(r20[:, t])
            v = pd.Series(np.where(ok10, r20[:, t], np.nan))
            k = v.notna().sum()
            if k == 0:
                continue
            ordr = np.lexsort((np.arange(len(v)), v.fillna(np.inf).to_numpy()))[:k]
            dec = np.full(len(v), -1); dec[ordr] = (np.arange(k) * 10) // k
            y = r60[:, t]; fin = b & np.isfinite(y) & (dec >= 0)
            for d_ in range(10):
                g = fin & (dec == d_)
                if g.sum() < 2:
                    continue
                tot = y[g].sum(); cnt = g.sum()
                sel = g & (q[:, t] == code)
                for i in np.flatnonzero(sel):
                    xs.append(y[i] - (tot - y[i]) / (cnt - 1)); ms.append(mon[t])
        xs = np.array(xs); ms = np.array(ms); mu = xs.mean()
        se = np.sqrt((pd.Series(xs - mu).groupby(ms).sum() ** 2).sum()) / len(xs)
        r = C[(C["欄"] == col) & (C["碼"] == code) & (C["段"] == "探索") & (C["h"] == 60)].iloc[0]
        if not np.allclose((mu, mu - 1.959963984540054 * se), (r["對基準②"], r["對基準②_下"]), rtol=1e-3):
            nc += 1; errs.append(f"⑦ {col} Q{code}：自算 {mu:.6f}/{mu - 1.96 * se:.6f} 檔 {r['對基準②']:.6f}/{r['對基準②_下']:.6f}")
    info["⑦ ③ 曲線 不同（2 個）"] = nc
if a.part in ("endtrade", "all"):
    # ⑧ 結束特徵可交易：取確認段第一個級距、h＝60，全部 (股, t) 自算 A−B 平均與 95%／Bonf 下緣
    SMY = pd.read_csv(os.path.join(OUT, "end_trade_summary.csv")); DT = pd.read_csv(os.path.join(OUT, "end_trade.csv"))
    r0 = SMY[SMY["段"] == "確認"].iloc[0]; col, code = r0["欄"], int(r0["碼"])
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); dm = (mon >= 2022 * 12) & (mon <= 2026 * 12 + 7)
    ed_, es_ = E["d"].astype(int), E["s"].astype(int)
    st_ = pd.DataFrame({"s": es_, "d": ed_})[dm[ed_]].drop_duplicates()
    q = np.asarray(Q[FX[col]]); vals = []; mons = []
    for s, g in st_.groupby("s"):
        df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
        o = df["open"].to_numpy(float); cff = df["close"].ffill().to_numpy(float)
        sig = np.flatnonzero(q[s] == code)
        for t in g["d"]:
            B = float(Rm[11, s, t])
            if not np.isfinite(B):
                continue
            nxt = sig[sig > t]; A = B
            if len(nxt) and nxt[0] <= t + 59:
                e = nxt[0] + 1
                while e < n and not (np.isfinite(o[e]) and o[e] > 0):
                    e += 1
                if e <= t + 60:
                    A = o[e] / o[t + 1] - 1
            vals.append(A - B); mons.append(mon[t])
    v = np.array(vals); mu = v.mean(); se = np.sqrt((pd.Series(v - mu).groupby(np.array(mons)).sum() ** 2).sum()) / len(v)
    ref = DT[(DT["欄"] == col) & (DT["碼"] == code) & (DT["段"] == "確認") & (DT["h"] == 60)].iloc[0]
    info["⑧ 結束可交易（級距、h60 確認：自算平均／檔）"] = [f"{col} Q{code}", float(mu), float(ref["A−B"]), int(len(v)), int(ref["n"])]
    if not (np.isclose(mu, ref["A−B"], rtol=1e-4, atol=1e-7) and len(v) == int(ref["n"])):
        errs.append("⑧ 結束可交易 不同")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:60]}, open(os.path.join(OUT, f"check_{a.part}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:20]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
