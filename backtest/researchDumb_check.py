# -*- coding: utf-8 -*-
"""researchDumb 獨立查核（PREREG最笨交易法 seq1）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDumb_check [--procs 4]

獨立寫法（⛔ 不用主程式的函式、rluwork 快取、patterns.Frame、research11.load_bars／limit_flags／fixed_exit／simulate_mtm）：
  價格 ＝ 逐檔 D.load_stock（還原）＋ 自讀原始 CSV（原始收盤、開高低）；漲停 ＝ 自寫升降單位與漲停價（同規格：2015-06-01 前 7%、之後 10%，往下取；
  還原事件日、2015-01-12 後上市前 5 根不判）；營量閘 ＝ 自寫（含 t 的 20 個交易日都有成交 ∧ t−20～t−1 均量 ≥ 500,000 股）；
  開盤漲停／跌停鎖死 ＝ tradability.one 的 up_o／dn_o ∧ 原始最低（最高）＝ 原始開盤（同 researchTopPrevTW_check）；pv ＝ UG.pit_valid；
  壞根 ＝ 同一份輸入（~/crashwork/bad_*.pkl）∪ 自算缺口 ≥ 5；早年另加 R8 事件（addonwork 早年世界 EV）＋ reduce_v2 三份 CSV 自讀；
  MA20、MACD（pandas ewm adjust=False，逐段）、ATR、量門檻、出場與分批 ＝ 自寫迴圈；組合 ＝ 自寫逐日迴圈（同一套名額、抽籤、成本規則）
比對：① 抽樣股（每世界：隨機 100 檔母體股 ＋ 隨機 100 檔「主程式有 F1 列」的股）的 F1／F2／F4／F5 候選集合（逐列）；
      ② 這些列的出場（xpos 相同、g／g_slip 差 ≤ 1e−12、a、分批日）；
      ②′ 出場不同但判斷路徑上有「收盤＝MA20」浮點平手（差 ≤ 1e−12 相對）的列另計、不算錯；③ 6 格 × 2 世界 × （無滑價、滑價）組合逐日權益（主程式 eq npz：相對差 ≤ 1e−9；滑價版另由主表比 6 位有效數字）與各段年化、回落（差 ≤ 1e−9）
輸出 backtest/resultsDumb/check.json、check.log
"""
from __future__ import annotations

import argparse
import json
import math
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
from backtest import universe_gate as UG                    # noqa: E402
from backtest import tradability as TR                      # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsDumb"
H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
V2EXT = os.path.expanduser("~/earlydata/950ad26e12/reduce_ext_b45c9e94dc")
WD = {"主": (H2D, "main"), "早年": (EOTC, "early")}
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CELLS = ("F1", "F2", "F3", "F4", "F5", "F6")
COSTX = 0.001425 * 2 + 0.003
SL = 0.005
_G: dict = {}


def okc(s):
    return isinstance(s, str) and len(s) == 4 and s.isdigit() and s[0] != "0" and not s.startswith("91")


def tick(p):
    if p < 10:
        return 0.01
    if p < 50:
        return 0.05
    if p < 100:
        return 0.1
    if p < 500:
        return 0.5
    if p < 1000:
        return 1.0
    return 5.0


def upper_limit(ref, lim):
    x = ref * (1 + lim); t = tick(x)
    return math.floor(x / t + 1e-9) * t


def early_extra(cal):
    W = pickle.load(open(os.path.expanduser("~/addonwork/world_早年.pkl"), "rb"))
    out = {}

    def add(s, d):
        s = str(s).strip(); d = str(d).strip()
        if not d:
            return
        k = int(cal.searchsorted(pd.Timestamp(d)))
        if k < len(cal):
            out.setdefault(s, set()).add(k)
    for s, e in zip(W["EV"]["stock_id"], W["EV"]["e"]):
        add(s, e)
    t = pd.read_csv(os.path.join(V2EXT, "twse_reduce_detected_2004_2010.csv"), dtype=str, keep_default_na=False)
    for s, d in zip(t["stock_id"], t["date"]):
        add(s, d)
    o = pd.read_csv(os.path.join(V2EXT, "otc_reduce_detected_2007_2012.csv"), dtype=str, keep_default_na=False)
    o = o[(o["shares_down"].str.strip() == "1") & (o["exright_in_gap"].str.strip() == "0")]
    for s, d in zip(o["stock_id"], o["resume_day"]):
        add(s, d)
    u = pd.read_csv(os.path.join(V2EXT, "twse_jump_unexplained_2004_2010.csv"), dtype=str, keep_default_na=False)
    for s, d in zip(u["stock_id"], u["date"]):
        add(s, d)
    return out


def load_one(a):
    """一檔的日曆陣列（價格、閘、可買賣）；full ⇒ 再算訊號旗標。"""
    wn, sid, full = a
    data = WD[wn][0]; D.DATA = data; cal = _G[("cal", wn)]; n = len(cal)
    mk = _G[("mk", wn)].get(sid, "twse")
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    vol = df["volume"].to_numpy(float)
    traded = np.isfinite(c)
    raw = pd.read_csv(os.path.join(data, "stocks", f"{sid}.csv"), dtype={"date": str}).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float)
    ro = pd.to_numeric(raw["open"], errors="coerce").to_numpy(float)
    rh = pd.to_numeric(raw["high"], errors="coerce").to_numpy(float); rl = pd.to_numeric(raw["low"], errors="coerce").to_numpy(float)
    tb = TR.one(sid, cal)
    with np.errstate(invalid="ignore"):
        upl = tb["up_o"] & (rl == ro); dnl = tb["dn_o"] & (rh == ro)
    trd = np.asarray(tb["trd"], bool)
    cf = pd.Series(c).ffill().to_numpy(float)
    out = {"cf": cf, "o": np.where(np.isfinite(o) & (o > 0), o, np.nan)}
    if not full:
        return sid, out
    idx = np.flatnonzero(traded); nb = len(idx)
    if nb < 260:
        out["flags"] = None
        return sid, out
    # 壞 K 棒
    badc = set(_G[("bad", wn)].get(sid, set()))
    gp = np.diff(idx) - 1
    for j in np.flatnonzero(gp >= 5):
        badc.add(int(idx[j + 1]))
    badb = np.zeros(nb, bool)
    for p in badc:
        k = int(np.searchsorted(idx, p))
        if k < nb:
            badb[k] = True
    # 漲停
    adj = D.load_adj(sid)
    skip = np.zeros(nb, bool)
    if adj is not None and len(adj):
        for d in adj["date"]:
            k = int(np.searchsorted(cal[idx], pd.Timestamp(d)))
            if k < nb:
                skip[k] = True
    if cal[idx[0]] > pd.Timestamp("2015-01-12"):
        skip[:5] = True
    rcb = rc[idx]; up = np.zeros(nb, bool)
    for k in range(1, nb):
        if skip[k] or not np.isfinite(rcb[k]) or not np.isfinite(rcb[k - 1]) or rcb[k - 1] <= 0:
            continue
        lim = 0.07 if cal[idx[k]] < pd.Timestamp("2015-06-01") else 0.10
        up[k] = abs(rcb[k] - upper_limit(rcb[k - 1], lim)) < 1e-6
    cb = c[idx]; ob = o[idx]; hb = h[idx]; lb = l[idx]; vb = vol[idx]
    ma = np.full(nb, np.nan)
    for k in range(19, nb):
        if not badb[k - 18:k + 1].any():
            ma[k] = cb[k - 19:k + 1].mean()
    # 閘
    gate = np.zeros(n, bool)
    for t in range(20, n):
        if traded[t - 19:t + 1].all():
            w = vol[t - 20:t]
            if np.isfinite(w).all() and w.mean() >= 500_000:
                gate[t] = True
    pv = np.asarray(UG.pit_valid(sid, cal, data), bool)
    # MACD（月）
    MID = cal.year * 12 + cal.month
    segno = np.cumsum(badb)
    mrec = {}
    bm = MID[idx]
    for k in range(nb):
        if k == nb - 1 or bm[k + 1] != bm[k]:
            mrec[int(bm[k])] = k
    months = sorted(mrec)
    mser = pd.DataFrame({"m": months, "k": [mrec[m] for m in months]})
    mser["c"] = cb[mser["k"].to_numpy()]; mser["seg"] = segno[mser["k"].to_numpy()]
    brk = (mser["seg"].diff() != 0) | (mser["m"].diff() != 1)
    mser["run"] = brk.cumsum()
    mser["dif"] = np.nan; mser["dea"] = np.nan; mser["pos"] = 0
    for _, g in mser.groupby("run"):
        e12 = g["c"].ewm(span=12, adjust=False).mean(); e26 = g["c"].ewm(span=26, adjust=False).mean()
        dif = e12 - e26; dea = dif.ewm(span=9, adjust=False).mean()
        mser.loc[g.index, "dif"] = dif; mser.loc[g.index, "dea"] = dea; mser.loc[g.index, "pos"] = np.arange(len(g))
    mi = mser.set_index("m")
    lastday = np.zeros(n, bool); lastday[:-1] = np.asarray(MID[1:]) != np.asarray(MID[:-1])
    F = {"F1": [], "F2": [], "F4": [], "F5": []}
    for k in range(nb):
        t = int(idx[k]); e = t + 1
        if k < 20 or k + 1 >= nb or e >= n or int(idx[k + 1]) != e:
            continue
        if badb[k - 20:k + 2].any() or not np.isfinite(ma[k]) or not gate[t] or not pv[t]:
            continue
        if not (trd[e] and np.isfinite(o[e]) and o[e] > 0 and not upl[e]):
            continue
        # ①
        win = [j for j in range(max(0, k - 12), k + 1) if idx[j] >= t - 9]
        a1 = any(up[j] for j in win) and not any(up[j] and up[j - 1] and up[j - 2] for j in win if j - 2 >= win[0])
        # ②
        ms = int(MID[t]) if lastday[t] else int(MID[t]) - 1
        a2 = False
        if ms in mi.index:
            r = mi.loc[ms]
            if int(r["k"]) <= k and int(r["seg"]) == int(segno[k]) and int(r["pos"]) >= 34:
                a2 = bool(r["dif"] > r["dea"])
        # ③
        red = cb[k] > ob[k]
        v20 = vb[k - 20:k].mean()
        a3 = (lb[k] <= ma[k] * 1.02) and (cb[k] >= ma[k]) and red and np.isfinite(vb[k]) and np.isfinite(v20) and vb[k] > 1.5 * v20
        tr = [max(hb[j], cb[j - 1]) - min(lb[j], cb[j - 1]) for j in range(k - 19, k + 1)]
        atr = float(np.mean(tr))
        a3r = False
        if k >= 60 and not badb[k - 60:k + 1].any():
            p80 = np.percentile(vb[k - 60:k], 80)
            a3r = (lb[k] <= ma[k] + 0.5 * atr) and (cb[k] >= ma[k]) and red and np.isfinite(vb[k]) and np.isfinite(p80) and vb[k] >= p80
        if a1 and a2 and a3:
            F["F1"].append(k)
        if a1 and a2 and a3r:
            F["F2"].append(k)
        if a1 and a3:
            F["F4"].append(k)
        if a2 and a3:
            F["F5"].append(k)
    sellable = np.array([bool(trd[int(t)] and np.isfinite(o[int(t)]) and o[int(t)] > 0 and not dnl[int(t)]) for t in idx])
    out["flags"] = F
    out["bars"] = {"idx": idx, "c": cb, "o": ob, "ma": ma, "bad": badb, "sell": sellable, "atrp": None, "end": bool(idx[-1] == n - 1)}
    atrp = np.full(nb, np.nan)
    for k in range(20, nb):
        atrp[k] = np.mean([max(hb[j], cb[j - 1]) - min(lb[j], cb[j - 1]) for j in range(k - 19, k + 1)]) / cb[k]
    out["bars"]["atrp"] = atrp
    return sid, out


def my_exit(B, k, mode, bp, n0, th):
    idx, c, o, ma, bad, sell = B["idx"], B["c"], B["o"], B["ma"], B["bad"], B["sell"]; nb = len(idx); ke = k + 1
    kb = None
    for j in range(ke + 1, nb):
        if bad[j]:
            kb = j; break
    lim = kb if kb is not None else nb

    def sale(d):
        j = d + 1
        while j < lim and not sell[j]:
            j += 1
        return j if j < lim else None

    def below(j):
        return np.isfinite(ma[j]) and c[j] < ma[j]

    def forced():
        if kb is not None:
            return ("close", int(idx[kb - 1]), float(c[kb - 1]), int(idx[kb - 1]), int(idx[kb - 1]) + 1)
        if B["end"]:
            return ("end", n0 - 1, float(c[nb - 1]), n0 - 1, n0)
        return ("close", int(idx[nb - 1]), float(c[nb - 1]), int(idx[nb - 1]), int(idx[nb - 1]) + 1)
    a = 0
    if mode == "H60":
        q = k + 60
        fin = ("close", int(idx[q]), float(c[q]), int(idx[q]), int(idx[q])) if q < lim else forced()
    else:
        d = None
        if below(ke):
            d, a = ke, 1
        elif ke + 1 < lim and below(ke + 1):
            d, a = ke + 1, 2
        else:
            j = ke + 2
            while j + 3 < lim:
                if below(j) and below(j + 1) and below(j + 2) and below(j + 3):
                    d = j + 3; break
                j += 1
        S = sale(d) if d is not None else None
        fin = ("open", int(idx[S]), float(o[S]), int(idx[S]) - 1, int(idx[S])) if S is not None else forced()
    tf = 2 * n0 if fin[0] == "end" else (2 * fin[1] if fin[0] == "open" else 2 * fin[1] + 1)
    parts = []; ps = []
    if th is not None and mode != "H60":
        for x in th:
            P = None
            for j in range(ke, lim):
                if c[j] / bp - 1.0 >= x:
                    P = sale(j); break
            if P is not None and 2 * int(idx[P]) < tf:
                ps.append(int(idx[P])); parts.append((1 / 3, float(o[P]), int(idx[P]) - 1))
            else:
                ps.append(-1)
    else:
        ps = [-1, -1]
    parts.append((1.0 - len(parts) / 3, fin[2], fin[3]))
    g = sum(w * p for w, p, _ in parts) / bp - 1.0
    gs = sum(w * p * (1 - SL) for w, p, _ in parts) / (bp * (1 + SL)) - 1.0
    return {"xpos": fin[4], "g": g, "g_slip": gs, "a": a, "p1": ps[0], "p2": ps[1], "parts": parts}


def sim(rows, NP, CF, OP, slip):
    rows = sorted(rows, key=lambda r: (r["entry_pos"], r["key"]))
    by = {}
    for r in rows:
        by.setdefault(r["entry_pos"], []).append(r)
    first = min(r["entry_pos"] for r in rows); last = max(r["xpos"] for r in rows); end = min(NP, last + 2)
    tt = np.arange(NP)
    SC = {}
    for r in rows:
        cf = CF[r["sid"]]
        if len(r["parts"]) > 1:
            SC[r["key"]] = sum(w * np.where(tt <= dl, cf, p * (1 - SL) if slip else p) for w, p, dl in r["parts"])
        else:
            SC[r["key"]] = cf
    eq = np.ones(NP); cash = 1.0; pos = []; held = set(); rng = np.random.default_rng(1000)
    for t in range(first, end):
        keep = []
        for p in pos:
            if p["x"] <= t:
                cash += p["amt"] * (1 + p["g"] - COSTX); held.discard(p["sid"])
            else:
                keep.append(p)
        pos = keep
        g = by.get(t)
        if g is not None and len(pos) < 10:
            cand = [r for r in g if r["sid"] not in held]
            if cand:
                order = rng.permutation(len(cand)); avail = 10 - len(pos)
                slot = eq[t - 1] / 10
                for i in order[:avail]:
                    r = cand[i]
                    amt = min(slot, cash)
                    if amt <= 1e-9:
                        break
                    cash -= amt
                    ep = OP[r["sid"]][t] * ((1 + SL) if slip else 1.0)
                    if not (np.isfinite(ep) and ep > 0):
                        ep = SC[r["key"]][t]
                    pos.append({"x": r["xpos"], "sid": r["sid"], "key": r["key"], "amt": amt, "g": r["g_slip"] if slip else r["g"], "ep": ep})
                    held.add(r["sid"])
        eq[t] = cash + sum(p["amt"] * SC[p["key"]][t] / p["ep"] for p in pos)
    eq[:first] = 1.0; eq[end:] = eq[end - 1]
    return eq


def wstat(eq, x, y):
    seg = eq[x:y + 1]; yrs = (y + 1 - x) / 245
    return float((seg[-1] / seg[0]) ** (1 / yrs) - 1), float((seg / np.maximum.accumulate(seg) - 1).min())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); a = ap.parse_args()
    lf = open(os.path.join(OUT, "check.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); lf.write(m + "\n"); lf.flush()
    RES = {"寫法": "獨立（見檔頭）", "世界": {}}
    from backtest import rerun17 as RR                         # 只用來把主程式存下的權益算成主程式報的數（＝主程式同一式）
    MT = pd.read_csv(os.path.join(OUT, "Dumb_main.csv"))
    for wn, (data, part) in WD.items():
        D.DATA = data; cal = D.load_calendar(); n0 = len(cal); NP = n0 + 1
        st = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
        U = UG.gate3(st); U = U[U["stock_id"].map(okc)]
        _G[("cal", wn)] = cal; _G[("mk", wn)] = dict(zip(U["stock_id"], U["market"]))
        B = pickle.load(open(os.path.expanduser(f"~/crashwork/bad_{part}.pkl"), "rb"))
        bad = {s: set(int(x) for x in v[0]) | set(int(x) for x in v[1]) for s, v in B.items()}
        if wn == "早年":
            for s, ks in early_extra(cal).items():
                bad.setdefault(s, set()).update(ks)
        _G[("bad", wn)] = bad
        ROWS = {cl: pd.read_csv(os.path.join(OUT, f"rows_{wn}_{cl}.csv.gz"), dtype={"sid": str}) for cl in CELLS}
        rng = np.random.default_rng(20261014 + (0 if wn == "主" else 1))
        allu = sorted(U["stock_id"]); f1s = sorted(set(ROWS["F1"]["sid"]))
        samp = sorted(set(rng.choice(allu, 100, replace=False)) | set(rng.choice(f1s, min(100, len(f1s)), replace=False)))
        need = sorted(set().union(*[set(ROWS[cl]["sid"]) for cl in CELLS]) | set(samp))
        with Pool(a.procs) as pool:
            LD = dict(pool.map(load_one, [(wn, s, s in samp) for s in need], chunksize=8))
        log(f"[{wn}] 抽樣 {len(samp)} 檔｜價格 {len(need)} 檔")
        R = {}
        # ①② 訊號集合與出場
        mism = {cl: 0 for cl in ("F1", "F2", "F4", "F5")}; ex_bad = {cl: 0 for cl in CELLS}; ex_n = {cl: 0 for cl in CELLS}; gmax = 0.0
        ex_tie = {cl: 0 for cl in CELLS}
        sigmap = {"F1": "F1", "F2": "F2", "F3": "F1", "F4": "F4", "F5": "F5", "F6": "F1"}
        modes = {"F1": ("M", (0.30, 0.50)), "F2": ("M2", None), "F3": ("M", None), "F4": ("M", (0.30, 0.50)), "F5": ("M", (0.30, 0.50)), "F6": ("H60", None)}
        examples = []
        for s in samp:
            L = LD.get(s)
            if L is None or L.get("flags") is None:
                for cl in mism:
                    m_ = ROWS[cl][ROWS[cl]["sid"] == s]
                    mism[cl] += len(m_)
                continue
            Bb = L["bars"]
            for cl in ("F1", "F2", "F4", "F5"):
                mine = set(int(Bb["idx"][k]) + 1 for k in L["flags"][cl])
                theirs = set(ROWS[cl][ROWS[cl]["sid"] == s]["entry_pos"].astype(int))
                if mine != theirs:
                    mism[cl] += len(mine ^ theirs)
                    if len(examples) < 10:
                        examples.append({"sid": s, "格": cl, "只在查核": sorted(mine - theirs)[:5], "只在主程式": sorted(theirs - mine)[:5]})
            for cl in CELLS:
                mo, th = modes[cl]
                sub = ROWS[cl][ROWS[cl]["sid"] == s]
                for r in sub.itertuples(index=False):
                    k = int(np.searchsorted(Bb["idx"], int(r.entry_pos) - 1))
                    bp = float(L["o"][int(r.entry_pos)])
                    if mo == "M2":
                        ap_ = Bb["atrp"][k]; th_ = (8 * ap_, 13 * ap_); mo_ = "M"
                    else:
                        th_ = th; mo_ = mo
                    me = my_exit(Bb, k, mo_, bp, n0, th_)
                    ex_n[cl] += 1
                    dg = max(abs(me["g"] - r.g), abs(me["g_slip"] - r.g_slip))
                    if me["xpos"] == int(r.xpos):
                        gmax = max(gmax, dg)
                    if me["xpos"] != int(r.xpos) or dg > 1e-12 or me["a"] != int(r.a) or me["p1"] != int(r.p1) or me["p2"] != int(r.p2):
                        hi_ = int(np.searchsorted(Bb["idx"], max(me["xpos"], int(r.xpos)), side="right"))
                        cc_, mm_ = Bb["c"][k + 1:hi_], Bb["ma"][k + 1:hi_]
                        if np.any(np.isfinite(mm_) & (np.abs(cc_ - mm_) <= 1e-12 * np.abs(mm_))):   # 收盤與 MA20 浮點平手（差 ≤ 1 ulp 級）
                            ex_tie[cl] += 1
                            if len(examples) < 20:
                                examples.append({"sid": s, "格": cl, "e": int(r.entry_pos), "平手": True, "查核": [me["xpos"], me["g"], me["a"]], "主程式": [int(r.xpos), float(r.g), int(r.a)]})
                            continue
                        ex_bad[cl] += 1
                        if len(examples) < 20:
                            examples.append({"sid": s, "格": cl, "e": int(r.entry_pos), "查核": [me["xpos"], me["g"], me["a"], me["p1"], me["p2"]],
                                             "主程式": [int(r.xpos), float(r.g), int(r.a), int(r.p1), int(r.p2)]})
        R["① 訊號集合不同列數（抽樣股）"] = mism; R["② 出場不同列數（非平手）"] = ex_bad; R["② 出場不同、但判斷路徑上有收盤＝MA20 浮點平手"] = ex_tie
        R["② 出場比對列數"] = ex_n; R["② 出場日相同列的 g 最大差"] = gmax; R["例"] = examples
        log(f"[{wn}] ① {mism}｜② 非平手 {ex_bad}｜平手 {ex_tie}／{ex_n}｜g 最大差（出場日相同） {gmax:.3g}")
        # ③ 組合
        CF = {s: np.r_[v["cf"], v["cf"][-1]] for s, v in LD.items() if v is not None}
        OP = {s: np.r_[v["o"], np.nan] for s, v in LD.items() if v is not None}
        EQ = np.load(os.path.join(OUT, f"eq_{wn}.npz"))
        segp = {}
        for sg, (x_, y_) in SEGS[wn].items():
            x = int(cal.searchsorted(pd.Timestamp(x_))); y = n0 - 1 if y_ is None else int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1
            segp[sg] = (x, y)
        port = {}
        for cl in CELLS:
            rows = []
            for r in ROWS[cl].itertuples(index=False):
                rows.append({"sid": r.sid, "entry_pos": int(r.entry_pos), "xpos": int(r.xpos), "g": float(r.g), "g_slip": float(r.g_slip),
                             "key": f"{r.sid}#{int(r.entry_pos)}", "parts": [tuple(p) for p in json.loads(r.parts)]})
            for slip in (False, True):
                eq = sim(rows, NP, CF, OP, slip)
                d = {}
                if not slip:
                    ref = EQ[cl]
                    d["權益最大相對差"] = float(np.max(np.abs(eq / ref - 1.0)))
                    for sg, (x, y) in segp.items():
                        c1, m1 = wstat(eq, x, y)
                        first = int(np.flatnonzero(ref != 1.0)[0]) - 1 if (ref != 1.0).any() else 0
                        c0, m0, _ = RR.win_metrics(ref, 0, NP, x, y)
                        d[sg] = {"年化差": abs(c1 - c0), "回落差": abs(m1 - m0)}
                else:
                    for sg, (x, y) in segp.items():
                        c1, m1 = wstat(eq, x, y)
                        z = MT[(MT["世界"] == wn) & (MT["格"] == cl) & (MT["段"] == sg) & (MT["滑價"])].iloc[0]
                        d[sg] = {"年化 vs 主表（6 位）": abs(c1 - z["年化"]) / max(1e-12, abs(z["年化"])), "回落 vs 主表": abs(m1 - z["回落"]) / max(1e-12, abs(z["回落"]))}
                port[f"{cl}{'·滑價' if slip else ''}"] = d
            log(f"[{wn}] {cl} {port[cl]}")
        R["③ 組合"] = port
        RES["世界"][wn] = R
    ok = True
    for wn, R in RES["世界"].items():
        if any(R["① 訊號集合不同列數（抽樣股）"].values()) or any(R["② 出場不同列數（非平手）"].values()) or R["② 出場日相同列的 g 最大差"] > 1e-12:
            ok = False
        for k, d in R["③ 組合"].items():
            if "權益最大相對差" in d and d["權益最大相對差"] > 1e-9:
                ok = False
            for sg, v in d.items():
                if isinstance(v, dict):
                    if "年化差" in v and (v["年化差"] > 1e-9 or v["回落差"] > 1e-9):
                        ok = False
                    if "年化 vs 主表（6 位）" in v and (v["年化 vs 主表（6 位）"] > 1e-5 or v["回落 vs 主表"] > 1e-5):
                        ok = False
    RES["通過"] = ok
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] 通過 {ok}")


if __name__ == "__main__":
    main()
