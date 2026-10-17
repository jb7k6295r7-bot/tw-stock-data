# -*- coding: utf-8 -*-
"""researchAscTri 獨立查核（PREREG上升三角組合層 seq3）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAscTri_check [--procs 2]

獨立寫法（⛔ 不用主程式的函式、rluwork 快取、research11.load_bars／simulate_mtm、rerun17.win_metrics／bench_row、patterns.Frame）：
  價格 ＝ 逐檔 D.load_stock（還原開高低收）；可賣開盤 ＝ tradability.one 的 trd ∧ 開盤有效 ∧ ⛔ 非（dn_o ∧ 原始最高 ＝ 原始開盤）（同 researchDumb_check）；
  0050 ＝ D.load_stock("0050") 收盤 ffill；ATR20、出場 a／b、固定 20／60 根、毛報酬、滑價 ＝ 自寫迴圈；
  組合 ＝ 自寫逐日迴圈（10 槽、新部位 min(前一日權益÷10, 可提現金)、default_rng(1000) 抽籤、同檔一筆、同日先出後進、
  空格放 0050：單位數記帳、進出 0050 各付 0.385%÷2；空格留現金：現金記帳）；年化、回落、標籤 ＝ 自寫。
⚠ 沿用主程式輸入（同一份）：訊號列（rows_{世界}.csv.gz 的 T、可買、下線 la／lb、壞根 kb、營收旗標）——型態偵測與營收不重做（偵測已與 PatAll 逐筆對帳）。
比對：① 每一筆可買列：ATR20（相對差 ≤ 1e−9）、主出場觸發根、xpos、毛報酬（差 ≤ 1e−12）、固定 20／60 根 xpos 與毛報酬、滑價毛報酬；
      ② 6 臂 × 2 世界 逐日權益（主程式 eq_{世界}.npz：相對差 ≤ 1e−9）；③ 各段年化、回落、0050 年化、回落（主程式 AscTri.json 主表：差 ≤ 1e−9）、標籤、平均持股
輸出 backtest/resultsAscTri/check.json、check.log
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import tradability as TRB                     # noqa: E402

OUT = "backtest/resultsAscTri"
H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
WD = {"主": H2D, "早年": EOTC}
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CST = 0.001425 * 2 + 0.003
ECST = (0.001425 * 2 + 0.001) / 2
SLP = 0.005
ARMX = {"M0050": ("M", True, False, False), "Mcash": ("M", False, False, False), "H20": ("H20", True, False, False),
        "H60": ("H60", True, False, False), "REV": ("M", True, False, True), "M0050slip": ("M", True, True, False)}
_G: dict = {}
LOG = []


def log(m):
    m = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {m}"; print(m, flush=True); LOG.append(m)


def one(a):
    wn, sid, rws = a
    D.DATA = WD[wn]; cal = _G[("cal", wn)]; n = len(cal)
    st = D.load_stock(sid, _G[("mk", wn)].get(sid, "twse"), cal)
    df = st.df
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    raw = pd.read_csv(os.path.join(WD[wn], "stocks", f"{sid}.csv"), dtype={"date": str}).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    ro = pd.to_numeric(raw["open"], errors="coerce").to_numpy(float); rh = pd.to_numeric(raw["high"], errors="coerce").to_numpy(float)
    tb = TRB.one(sid, cal)
    with np.errstate(invalid="ignore"):
        dnl = np.asarray(tb["dn_o"], bool) & (rh == ro)
    trd = np.asarray(tb["trd"], bool)
    bars = np.flatnonzero(np.isfinite(c)); nb = len(bars)
    cb, ob, hb, lb_ = c[bars], o[bars], h[bars], l[bars]
    sellable = trd[bars] & np.isfinite(ob) & (ob > 0) & ~dnl[bars]
    endok = bool(bars[-1] == n - 1)
    res = []
    for r in rws:
        k = int(np.searchsorted(bars, r["T"])); assert bars[k] == r["T"]
        ke = k + 1; assert bars[ke] == r["entry_pos"]
        bp = ob[ke]
        trs = [max(hb[j], cb[j - 1]) - min(lb_[j], cb[j - 1]) for j in range(k - 19, k + 1)]
        A = sum(trs) / 20.0
        kb = int(r["kb"]); lim = kb if kb >= 0 else nb

        def forced():
            if kb >= 0:
                return int(bars[kb - 1]) + 1, cb[kb - 1]
            if endok:
                return n, cb[nb - 1]
            return int(bars[nb - 1]) + 1, cb[nb - 1]
        # 主出場
        hm = -1e300; d = -1
        for j in range(ke, lim):
            if cb[j] > hm:
                hm = cb[j]
            if cb[j] < r["la"] + r["lb"] * j or cb[j] <= hm - 3.0 * A:
                d = j; break
        xs = None
        if d >= 0:
            for j in range(d + 1, lim):
                if sellable[j]:
                    xs = j; break
        if xs is not None:
            xm, pm = int(bars[xs]), ob[xs]
        else:
            xm, pm = forced()
        out = {"sid": sid, "entry_pos": r["entry_pos"], "atr": A, "trig": d, "xpos_M": xm, "g_M": pm / bp - 1.0,
               "gs_M": pm * (1 - SLP) / (bp * (1 + SLP)) - 1.0}
        for H in (20, 60):
            q = ke + H - 1
            if q < lim:
                out[f"xpos_H{H}"], out[f"g_H{H}"] = int(bars[q]), cb[q] / bp - 1.0
            else:
                x_, p_ = forced(); out[f"xpos_H{H}"], out[f"g_H{H}"] = x_, p_ / bp - 1.0
        res.append(out)
    cf = pd.Series(c).ffill().to_numpy(float)
    return sid, res, np.r_[cf, cf[-1]], np.r_[np.where(np.isfinite(o) & (o > 0), o, np.nan), np.nan]


def sim(rows, CL, OP, bench, NP, use_bench, slip):
    rows = sorted(rows, key=lambda r: (r["entry_pos"], r["sid"]))
    by = {}
    for r in rows:
        by.setdefault(r["entry_pos"], []).append(r)
    first = rows[0]["entry_pos"]; last = max(r["xpos"] for r in rows); tend = min(NP, last + 2)
    eq = np.ones(NP); rng = np.random.default_rng(1000)
    units = 1.0 / bench[first - 1] if use_bench else 0.0; cash = 1.0
    pos = []; held = set(); hold = np.zeros(NP)
    for t in range(first, tend):
        keep = []
        for p in pos:
            if p["x"] <= t:
                pr = p["amt"] * (1.0 + p["g"] - CST)
                if use_bench:
                    units += pr * (1 - ECST) / bench[t]
                else:
                    cash += pr
                held.discard(p["sid"])
            else:
                keep.append(p)
        pos = keep
        g = by.get(t)
        if g is not None and len(pos) < 10:
            cand = [r for r in g if r["sid"] not in held]
            if cand:
                order = rng.permutation(len(cand))
                slot = eq[t - 1] / 10.0
                for q in order[:10 - len(pos)]:
                    r = cand[q]
                    av = units * bench[t] * (1 - ECST) if use_bench else cash
                    amt = min(slot, av)
                    if amt <= 1e-9:
                        break
                    if use_bench:
                        units -= amt / ((1 - ECST) * bench[t])
                    else:
                        cash -= amt
                    ep = OP[r["sid"]][t] * ((1 + SLP) if slip else 1.0)
                    if not (np.isfinite(ep) and ep > 0):
                        ep = CL[r["sid"]][t]
                    pos.append({"sid": r["sid"], "amt": amt, "ep": ep, "x": r["xpos"], "g": r["g"]}); held.add(r["sid"])
        hv = 0.0
        for p in pos:
            hv += p["amt"] * CL[p["sid"]][t] / p["ep"]
        eq[t] = (units * bench[t] if use_bench else cash) + hv
        hold[t] = len(pos)
    if use_bench:
        eq[tend:] = eq[tend - 1] * bench[tend:] / bench[tend - 1]
        if first > 1:
            eq[:first - 1] = bench[:first - 1] / bench[first - 1]
    else:
        eq[tend:] = eq[tend - 1]
    return eq, hold


def stats(seg):
    yrs = len(seg) / 245.0
    pk = np.maximum.accumulate(seg)
    return (seg[-1] / seg[0]) ** (1 / yrs) - 1, float(((seg - pk) / pk).min())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    T0 = time.time()
    J = json.load(open(os.path.join(OUT, "AscTri.json"), encoding="utf-8"))
    MT = pd.DataFrame(J["主表"])
    CK = {"說明": __doc__.split("比對：")[1].split("輸出")[0].strip(), "世界": {}}
    allok = True
    for wn in ("主", "早年"):
        D.DATA = WD[wn]; cal = D.load_calendar(); n = len(cal); NP = n + 1
        st = pd.read_csv(os.path.join(WD[wn], "meta", "stocks.csv"), dtype=str)
        _G[("cal", wn)] = cal; _G[("mk", wn)] = dict(zip(st["stock_id"], st["market"]))
        RW = pd.read_csv(os.path.join(OUT, f"rows_{wn}.csv.gz"), dtype={"sid": str, "why": str}, keep_default_na=False, low_memory=False)
        RW = RW[RW["why"] == ""].copy()
        for cc in ("T", "entry_pos", "kb", "xpos_M", "xpos_H20", "xpos_H60", "trig_M"):
            RW[cc] = RW[cc].astype(float).astype(int)
        for cc in ("la", "lb", "atr", "g_M", "gs_M", "g_H20", "g_H60"):
            RW[cc] = RW[cc].astype(float)
        RW["rev_ok"] = RW["rev_ok"].astype(str) == "True"
        recs = RW.to_dict("records")
        bys = {}
        for r in recs:
            bys.setdefault(r["sid"], []).append(r)
        CL, OP, MY = {}, {}, {}
        with Pool(a.procs) as pool:
            for sid, res, cl, op in pool.imap_unordered(one, [(wn, s, v) for s, v in sorted(bys.items())], chunksize=4):
                CL[sid], OP[sid] = cl, op
                for x in res:
                    MY[(sid, x["entry_pos"])] = x
        # ① 逐列
        bad = {"ATR": 0, "觸發根": 0, "xpos_M": 0, "g_M": 0, "gs_M": 0, "xpos_H": 0, "g_H": 0}; ex = []
        dmax = {"ATR相對": 0.0, "g_M": 0.0, "gs_M": 0.0, "g_H": 0.0}
        for r in recs:
            m = MY[(r["sid"], r["entry_pos"])]
            da = abs(m["atr"] / r["atr"] - 1); dmax["ATR相對"] = max(dmax["ATR相對"], da); bad["ATR"] += da > 1e-9
            bad["觸發根"] += m["trig"] != r["trig_M"]; bad["xpos_M"] += m["xpos_M"] != r["xpos_M"]
            for k_ in ("g_M", "gs_M"):
                dd = abs(m[k_] - r[k_]); dmax[k_] = max(dmax[k_], dd); bad[k_] += dd > 1e-12
            for H in (20, 60):
                bad["xpos_H"] += m[f"xpos_H{H}"] != r[f"xpos_H{H}"]
                dd = abs(m[f"g_H{H}"] - r[f"g_H{H}"]); dmax["g_H"] = max(dmax["g_H"], dd); bad["g_H"] += dd > 1e-12
            if (m["trig"] != r["trig_M"] or m["xpos_M"] != r["xpos_M"]) and len(ex) < 5:
                ex.append((r["sid"], r["entry_pos"], m["trig"], r["trig_M"], m["xpos_M"], r["xpos_M"]))
        W_ = {"可買列": len(recs), "不同筆數": bad, "最大差": dmax, "例": ex}
        rows_ok = all(v == 0 for v in bad.values())
        log(f"[① 逐列 {wn}] {W_}")
        # ② 組合
        b0 = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float); bench = np.r_[b0, b0[-1]]
        EQ = np.load(os.path.join(OUT, f"eq_{wn}.npz"))
        segp = {}
        for sg, (x0, y0) in SEGS[wn].items():
            x = int(cal.searchsorted(pd.Timestamp(x0))); y = n - 1 if y0 is None else int(cal.searchsorted(pd.Timestamp(y0), side="right")) - 1
            segp[sg] = (x, y)
        eqd = {}; segd = []; eq_ok = True; seg_ok = True
        for arm, (xk, ub, slip, rv) in ARMX.items():
            rr = [{"sid": r["sid"], "entry_pos": r["entry_pos"], "xpos": r[f"xpos_{xk}"],
                   "g": MY[(r["sid"], r["entry_pos"])]["gs_M" if slip else f"g_{xk}"]} for r in recs if (r["rev_ok"] or not rv)]
            eq, hold = sim(rr, CL, OP, bench, NP, ub, slip)
            rel = float(np.max(np.abs(eq / EQ[arm] - 1.0)))
            eqd[arm] = rel; eq_ok &= rel <= 1e-9
            for sg, (x, y) in segp.items():
                c_, m_ = stats(eq[x:y + 1]); bc, bm = stats(bench[x:y + 1])
                lab = "合格" if (c_ > bc and c_ / abs(m_) >= bc / abs(bm)) else ("另列" if c_ > bc else "不合格")
                z = MT[(MT["世界"] == wn) & (MT["臂"] == arm) & (MT["段"] == sg)].iloc[0]
                dd = {"世界": wn, "臂": arm, "段": sg, "年化": c_, "回落": m_, "Δ年化": abs(c_ - z["年化"]), "Δ回落": abs(m_ - z["回落"]),
                      "Δ0050年化": abs(bc - z["0050年化"]), "Δ0050回落": abs(bm - z["0050回落"]), "標籤同": lab == z["標籤"],
                      "Δ平均持股": abs(float(np.mean(hold[x:y + 1])) - z["平均持股"])}
                seg_ok &= max(dd["Δ年化"], dd["Δ回落"], dd["Δ0050年化"], dd["Δ0050回落"], dd["Δ平均持股"]) <= 1e-9 and dd["標籤同"]
                segd.append(dd)
        W_.update({"逐日權益最大相對差": eqd, "各段": segd, "逐列通過": rows_ok, "權益通過": eq_ok, "各段通過": seg_ok})
        log(f"[② 權益 {wn}] {eqd}")
        log(f"[③ 各段 {wn}] " + "｜".join(f"{d['臂']}/{d['段']} Δ年化 {d['Δ年化']:.1e} Δ回落 {d['Δ回落']:.1e} 標籤同 {d['標籤同']}" for d in segd))
        allok &= rows_ok and eq_ok and seg_ok
        CK["世界"][wn] = W_
    CK["全部通過"] = bool(allok); CK["耗時秒"] = round(time.time() - T0); CK["時間（台北）"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 全部通過 {allok}｜{CK['耗時秒']}s")
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    if not allok:
        raise SystemExit("⛔ 查核不通過")


if __name__ == "__main__":
    main()
