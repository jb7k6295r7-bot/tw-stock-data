# -*- coding: utf-8 -*-
"""researchTopPrevTW 獨立查核（PREREG每年買去年漲最多 seq1）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTopPrevTW_check [--procs 3]

獨立寫法（⛔ 不用主程式的 rluwork 快取、patterns.Frame、research11.simulate_mtm、主程式的 book／ranked）：
  價格 ＝ 逐檔 D.load_stock（還原、ffill）；營量閘 ＝ 自寫（含 d 的 20 根有成交 ∧ d−20～d−1 日量平均 ≥ 500,000 股）；
  開盤漲停／跌停鎖死 ＝ tradability.one 的 up_o／dn_o ∧ 原始最低（最高）＝ 原始開盤；營收 ＝ 自讀 revenue_hist、自算可得日；
  壞根 ＝ 同一份輸入（主、早年：~/crashwork/bad_*.pkl；早年另加 R8 事件＋reduce_v2 三份 CSV 自讀；早年v2：research11.load_bars）；
  換股簿與逐日權益 ＝ 自寫迴圈（同一套出場規則、同一個權重函數）
比對：6 格 × 3 世界主臂的逐年名單（逐字）、逐日權益（相對差 ≤ 1e−9）、逐年組合報酬與各段年化／回落（差 ≤ 1e−9）
輸出 backtest/resultsTopPrevTW/check.json、check.log
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import tradability as TR                      # noqa: E402

OUT = "backtest/resultsTopPrevTW"
WORK = os.path.expanduser("~/topprevwork")
H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
V2 = os.path.expanduser("~/earlydata/950ad26e12/reduce_v2/data")
V2EXT = os.path.expanduser("~/earlydata/950ad26e12/reduce_ext_b45c9e94dc")
COST = 0.00585
CELLS = {"T1": ("整年", 1, False), "T2": ("整年", 10, False), "T3": ("扣一月", 1, False), "T4": ("扣一月", 10, False),
         "T5": ("整年", 1, True), "T6": ("整年", 10, True)}
WORLDS = {"主": (H2D, 2017, 9999, "main"), "早年": (EOTC, 2006, 2014, "early"), "早年v2": (V2, 2006, 2014, None)}
SEGS = {"主": {"探索": (2017, 2021), "確認": (2022, None)}, "早年": {"早年": (2006, 2014)}, "早年v2": {"早年": (2006, 2014)}}
_G: dict = {}


def okc(s):
    return len(s) == 4 and s.isdigit() and s[0] != "0" and not s.startswith("91")


def load_one(a):
    data, sid, v2 = a
    D.DATA = data
    cal = _G[data]; n = len(cal)
    st = D.load_stock(sid, "twse", cal)
    if st is None:
        return sid, None
    df = st.df
    cl = df["close"].to_numpy(float); op = df["open"].to_numpy(float); vol = df["volume"].to_numpy(float)
    traded = np.isfinite(cl)
    raw = pd.read_csv(os.path.join(data, "stocks", f"{sid}.csv"), dtype={"date": str}).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    ro = pd.to_numeric(raw["open"], errors="coerce").to_numpy(float); rh = pd.to_numeric(raw["high"], errors="coerce").to_numpy(float)
    rl = pd.to_numeric(raw["low"], errors="coerce").to_numpy(float)
    tb = TR.one(sid, cal)
    with np.errstate(invalid="ignore"):
        upl = tb["up_o"] & (rl == ro); dnl = tb["dn_o"] & (rh == ro)
    # 營量閘（自寫）
    g = np.zeros(n, bool)
    for d in range(20, n):
        if traded[d - 19:d + 1].all():
            w = vol[d - 20:d]
            if np.isfinite(w).all() and w.mean() >= 500_000:
                g[d] = True
    out = {"c": pd.Series(cl).ffill().to_numpy(float), "o": np.where(np.isfinite(op) & (op > 0), op, np.nan), "bar": traded,
           "trd": np.asarray(tb["trd"], bool), "upl": upl, "dnl": dnl, "g": g, "pv": np.asarray(UG.pit_valid(sid, cal, data), bool)}
    if v2:
        mk = raw["market"].ffill().fillna("").to_numpy()
        out["tw"] = mk == "twse"
        B = R.load_bars(sid, "twse", cal)
        if B is not None:
            out["bad"] = np.asarray([B["idx"][k] for k in range(len(B["idx"])) if B["next_bad"][k] == k], np.int64)
        else:
            idx = np.flatnonzero(traded); gp = np.diff(idx) - 1
            out["bad"] = idx[1:][gp >= 5]
    return sid, out


def rev_table(data):
    fs = sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv")))
    rows = {}
    for f in fs:
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
        for s, p, a, b in zip(x["stock_id"], x["period"], x["當月營收"], x["去年當月營收"]):
            rows[(s, p)] = (pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce"))   # 同鍵後蓋前 ＝ 取最後一列
    return rows


def avail(p, cal):
    y, m = int(p[:4]), int(p[5:])
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    cut = pd.Timestamp(year=y2, month=m2, day=10 if p <= "2025-12" else 15)
    k = np.flatnonzero(cal > cut)
    return int(k[0]) if len(k) else len(cal)


def world(wn, procs, log):
    data, y0, y1, part = WORLDS[wn]
    D.DATA = data
    cal = D.load_calendar(); n = len(cal); _G[data] = cal
    st = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(st); sids = sorted(s for s in U["stock_id"] if okc(s))
    with Pool(procs) as pool:
        res = dict(pool.map(load_one, [(data, s, part is None) for s in sids], chunksize=8))
    sids = [s for s in sids if res.get(s) is not None]
    S = len(sids); ix = {s: i for i, s in enumerate(sids)}
    A = {k: np.vstack([res[s][k] for s in sids]) for k in ("c", "o", "bar", "trd", "upl", "dnl", "g", "pv")}
    A["tw"] = np.vstack([res[s]["tw"] for s in sids]) if part is None else np.ones((S, n), bool)
    BAD = np.zeros((S, n), bool)
    if part is not None:
        B = pickle.load(open(os.path.expanduser(f"~/crashwork/bad_{part}.pkl"), "rb"))
        miss = [s for s in sids if s not in B]
        assert not miss, f"crashwork 缺 {miss[:5]}"
        for s in sids:
            a, b = B[s]; BAD[ix[s], a] = True; BAD[ix[s], b] = True
        if wn == "早年":
            def addd(s, d):
                s = str(s).strip(); d = str(d).strip()
                if s in ix and d:
                    k = int(cal.searchsorted(pd.Timestamp(d)))
                    if k < n:
                        BAD[ix[s], k] = True
            EV = pickle.load(open(os.path.expanduser("~/addonwork/world_早年.pkl"), "rb"))["EV"]
            for s, e in zip(EV["stock_id"], EV["e"]):
                addd(s, e)
            t = pd.read_csv(os.path.join(V2EXT, "twse_reduce_detected_2004_2010.csv"), dtype=str, keep_default_na=False)
            for s, d in zip(t["stock_id"], t["date"]):
                addd(s, d)
            o = pd.read_csv(os.path.join(V2EXT, "otc_reduce_detected_2007_2012.csv"), dtype=str, keep_default_na=False)
            o = o[(o["shares_down"].str.strip() == "1") & (o["exright_in_gap"].str.strip() == "0")]
            for s, d in zip(o["stock_id"], o["resume_day"]):
                addd(s, d)
            u = pd.read_csv(os.path.join(V2EXT, "twse_jump_unexplained_2004_2010.csv"), dtype=str, keep_default_na=False)
            for s, d in zip(u["stock_id"], u["date"]):
                addd(s, d)
    else:
        for s in sids:
            BAD[ix[s], res[s]["bad"]] = True
    D.DATA = data
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    RV = rev_table(data)
    periods = sorted({p for (_, p) in RV})
    AV = {p: avail(p, cal) for p in periods}
    yrs = np.asarray(cal.year)
    fi = {int(y): int(np.flatnonzero(yrs == y)[0]) for y in np.unique(yrs)}
    YT = {}
    for Y in range(y0, min(y1, int(yrs[-1])) + 1):
        if Y not in fi or (Y - 1) not in fi or fi[Y - 1] - 1 < 0 or cal[fi[Y - 1] - 1].year != Y - 2:
            continue
        novs = np.flatnonzero((yrs == Y - 1) & (np.asarray(cal.month) == 11))
        YT[Y] = {"e": fi[Y], "d": fi[Y] - 1, "d0": fi[Y - 1] - 1, "nov": int(novs[-1]), "x": fi.get(Y + 1, n)}
    SF = {}
    for s in sids:
        b = np.flatnonzero(A["bar"][ix[s]])
        if len(b) and b[-1] < n - 1:
            SF[ix[s]] = int(b[-1])
    log(f"[查核世界 {wn}] 股 {S}｜{cal[0].date()}～{cal[-1].date()}｜年 {min(YT)}～{max(YT)}")
    return {"wn": wn, "cal": cal, "n": n, "sids": sids, "ix": ix, "A": A, "BAD": BAD, "bench": bench, "RV": RV, "periods": periods, "AV": AV, "YT": YT, "SF": SF}


def rank(Wd, Y, form, rev):
    A = Wd["A"]; yt = Wd["YT"][Y]; d, d0 = yt["d"], yt["d0"]; fe = d if form == "整年" else yt["nov"]
    e = yt["e"]; out = []
    av = [p for p in Wd["periods"] if Wd["AV"][p] <= e]
    for s, i in Wd["ix"].items():
        if not (A["g"][i, d] and A["pv"][i, d] and A["pv"][i, d0]):
            continue
        if Wd["wn"] == "早年v2" and not A["tw"][i, d]:
            continue
        ca, cb = A["c"][i, d0], A["c"][i, fe]
        if not (np.isfinite(ca) and np.isfinite(cb) and ca > 0 and cb > 0):
            continue
        if Wd["BAD"][i, d0 + 1:fe + 1].any():
            continue
        if rev:
            yo = None
            for p in reversed(av):
                v = Wd["RV"].get((s, p))
                if v is not None and np.isfinite(v[0]):
                    yo = (v[0] / v[1] - 1.0) if (np.isfinite(v[1]) and v[1] > 0) else np.nan
                    break
            if yo is None or not np.isfinite(yo) or yo <= 0:
                continue
        out.append((-(cb / ca - 1.0), s, i, cb / ca - 1.0))
    out.sort()
    return [(i, r) for _, s, i, r in out]


def sim(Wd, form, N, rev):
    A = Wd["A"]; n = Wd["n"]; C = A["c"]; O = A["o"]; BAD = Wd["BAD"]; YT = Wd["YT"]
    sellok = A["trd"] & np.isfinite(O) & (O > 0) & ~A["dnl"]

    def can_buy(i, e):
        return bool(A["trd"][i, e] and np.isfinite(O[i, e]) and O[i, e] > 0 and not A["upl"][i, e])

    def sale_from(i, ep, t0):
        for t in range(t0, n):
            if sellok[i, t]:
                return t, O[i, t] / ep - 1.0
        L = Wd["SF"].get(i)
        if L is not None and L >= t0:
            return L + 1, C[i, L] / ep - 1.0
        return n, C[i, n - 1] / ep - 1.0

    def forced(i, ep, e, x, ent):
        cand = []
        bars = np.flatnonzero(A["bar"][i])
        if x < n:
            nb = bars[bars >= x]; hi = int(nb[0]) if len(nb) else n - 1
            hi = min(max(hi, x), n - 1)
        else:
            hi = n - 1
        for k in range(e + 1, hi + 1):
            if BAD[i, k]:
                pb = bars[bars < k]
                if len(pb) and pb[-1] + 1 <= x:
                    cand.append((int(pb[-1]) + 1, C[i, pb[-1]] / ep - 1.0))
                break
        L = Wd["SF"].get(i)
        if L is not None and e <= L and L + 1 <= min(x, n - 1):
            cand.append((L + 1, C[i, L] / ep - 1.0))
        return min(cand) if cand else None
    held = {}; trades = []; busy_until = []; sel_log = {}
    for Y in sorted(YT):
        e, x = YT[Y]["e"], YT[Y]["x"]
        Lr = rank(Wd, Y, form, rev)
        sel = [i for i, _ in Lr[:N]]; sel_log[Y] = [Wd["sids"][i] for i in sel]
        score = dict(Lr)
        for i in list(held):
            if i not in sel:
                ent, ep, sc = held.pop(i)
                xp, g = sale_from(i, ep, e)
                trades.append((i, ent, ep, xp, g, sc))
                if xp > e:
                    busy_until.append(xp)
        busy = sum(1 for xp in busy_until if xp > e); busy_until = [xp for xp in busy_until if xp > e]
        free = N - sum(1 for i in sel if i in held) - busy
        for i in sel:
            if i in held:
                continue
            if can_buy(i, e) and free > 0:
                held[i] = (e, O[i, e], score[i]); free -= 1
        for i in list(held):
            ent, ep, sc = held[i]
            f = forced(i, ep, e, x, ent)
            if f is not None:
                held.pop(i); trades.append((i, ent, ep, f[0], f[1], sc))
                if f[0] > x:
                    busy_until.append(f[0])
    for i in list(held):
        ent, ep, sc = held.pop(i)
        trades.append((i, ent, ep, n, C[i, n - 1] / ep - 1.0, sc))
    # 逐日權益（自寫）
    byin = {}; byout = {}
    for k, (i, ent, ep, xp, g, sc) in enumerate(trades):
        byin.setdefault(ent, []).append(k); byout.setdefault(xp, []).append(k)
    first = min(byin) if byin else n
    eq = np.ones(n + 1); cash = 1.0; pos = {}
    Cp = np.hstack([C, C[:, -1:]])
    for t in range(first, n + 1):
        for k in byout.get(t, []):
            if k in pos:
                amt = pos.pop(k); g = trades[k][4]
                cash += amt * (1 + g) - amt * COST
        ins = sorted(byin.get(t, []), key=lambda k: -trades[k][5])
        if ins:
            tgt = min(eq[t - 1] / N, cash / len(ins))
            for k in ins:
                a = min(tgt, cash); cash -= a; pos[k] = a
        eq[t] = cash + sum(a * Cp[trades[k][0], t] / trades[k][2] for k, a in pos.items())
    return eq, sel_log, first


def wstats(eq, a, b):
    seg = eq[a:b + 1]; yrs = (b + 1 - a) / 245
    return (seg[-1] / seg[0]) ** (1 / yrs) - 1, float((seg / np.maximum.accumulate(seg) - 1).min())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    lf = open(os.path.join(OUT, "check.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); lf.write(m + "\n"); lf.flush()
    UG.set_gate_v2(True)
    REF = pickle.load(open(os.path.join(WORK, "main_arms.pkl"), "rb"))
    CT = pd.read_csv(os.path.join(OUT, "cells.csv"))
    CT = CT[CT["臂"] == "主臂"]
    out = {"說明": "獨立寫法：價格逐檔 D.load_stock、營量閘自寫、營收自讀、換股簿與逐日權益自寫；壞根集合同一份輸入", "格": {}}
    worst = 0.0; nsel_bad = 0
    for wn in WORLDS:
        Wd = world(wn, a.procs, log)
        for k, (form, N, rev) in CELLS.items():
            eq, sel, first = sim(Wd, form, N, rev)
            ref = REF[f"{wn}·{k}"]
            sb = sum(int(sel[Y] != ref["sel"][Y]) for Y in sel)
            nsel_bad += sb
            rf = np.asarray(ref["eq"], float)
            lo = min(first, ref["first"])
            d_eq = float(np.max(np.abs(eq[lo:Wd["n"]] / rf[lo:Wd["n"]] - 1.0)))
            segd = {}
            for sg, (y0, y1) in SEGS[wn].items():
                w0 = Wd["YT"][y0]["d"]; w1 = Wd["YT"][y1 + 1]["d"] if (y1 is not None and (y1 + 1) in Wd["YT"]) else Wd["n"] - 1
                c, m = wstats(eq, w0, w1)
                r_ = CT[(CT["世界"] == wn) & (CT["格"] == k) & (CT["段"] == sg)].iloc[0]
                segd[sg] = {"年化差": float(abs(c - r_["年化"])), "回落差": float(abs(m - r_["回落"]))}
                worst = max(worst, segd[sg]["年化差"], segd[sg]["回落差"])
            yrd = 0.0
            for Y in Wd["YT"]:
                aa = Wd["YT"][Y]["d"]; bb = Wd["YT"][Y + 1]["d"] if (Y + 1) in Wd["YT"] else Wd["n"] - 1
                yrd = max(yrd, abs(eq[bb] / eq[aa] - rf[bb] / rf[aa]))
            worst = max(worst, d_eq, yrd)
            out["格"][f"{wn}·{k}"] = {"名單不同年數": sb, "逐日權益最大相對差": d_eq, "逐年報酬最大差": yrd, "段": segd}
            log(f"[{wn}·{k}] 名單不同 {sb} 年｜權益 {d_eq:.2e}｜逐年 {yrd:.2e}｜段 {segd}")
    out["結論"] = {"名單不同（年×格×世界）": nsel_bad, "最大差": worst, "過（名單全同 ∧ 差 ≤ 1e−9）": bool(nsel_bad == 0 and worst <= 1e-9)}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[結論] {out['結論']}｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
