# -*- coding: utf-8 -*-
"""稽核 ② 3（seq3 §二 第 4 列、§七之六；裁定 seq257 §三 5）：上升趨勢線跌破 補 5／10／60 日視窗＋基準②。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit2_3 [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_3_check.py

原件：researchUT.py（0feb35c37c）主格 甲×R5×1% 穿越：20 日 X −0.37%〔−0.52%～−0.22%〕結果③；60 日（描述）−0.18%。
K3 已由裁定 seq257 §三 5 核准「扣成本後不可執行」（|X| 小於賣出再買回的 0.585%）⇒ 本件只補 K2 視窗與 K4 基準②，K3 照各視窗同法並報。
═══ 照原件、⛔ 不改 ═══
  事件 ＝ 原件 events_X.csv.gz 主格保留事件（sid、T、first；⛔ 不重偵測）；R_H ＝ px(T＋1＋H)／還原 open(T＋1) − 1（px ＝ 有效開盤、否則 ffill 收盤 ⇒ 停止交易強制出場：開）；
  X_H ＝ R_H − EW_H(T＋1)（researchM.ew_open，gate3 等權、同一式）；CI ＝ 月分群 CR0（researchM.summ）；出口 ＝ researchM.verdict（n_eff ＝ min(n, H 日區段數)）
═══ 本件新增（⭐ 開跑前寫死；本線讀法）═══
  視窗 H ∈ {5, 10, 20, 60}：區段 ＝ H 日（上限 2,313÷H）；H ＞ 20 的事件須 T＋1＋H ≤ 窗尾、硬斷點延伸到 [first, T＋1＋H]（原件 V9 同）；H ≤ 20 用原件同一批事件
  基準②：同一個 T，gate3 全體中「T 有效 K 棒、T＋1 可買（有成交、開盤有效、非開盤漲停）、[T, T＋1＋H] 無硬斷點（原件控制組 HB 同式延伸）、
     前 20 日報酬（avgdown.r20_cal）可算、R_H 可算」的股票，依前 20 日報酬分十分位（avgdown.deciles，股票代號序）；
     ȳ ＝ 與事件股同十分位的其他股 R_H 等權平均；X2_H ＝ R_H − ȳ（成本兩邊相同互抵）；事件股 r20 不可算或無配對 ⇒ 不進此項、件數必報
  K3（照裁定 seq257 已核的讀法）：賣出訊號要可執行，須跌破後少賺的幅度大於賣出再買回的成本 ⇒ 「可執行」＝ CI 上緣 ＜ −0.585%；
     否則「扣成本後不可執行」；另報點估計是否 ＜ −0.585%
  閘：H20 的 X 逐筆 ＝ 原件 events_X.csv.gz 的 X（逐位元）；H60 的 n／平均 ＝ 原件 summary 60 日
  「穩」：四個視窗的基準② 結果都同一出口同一方向才寫
輸出 backtest/resultsAudit2/3/
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                             # ⭐ 快照、chdir ⇒ repo（原件同）
D, TR, UG = H2.D, H2.TR, H2.UG
import researchM_freq as RF
import researchM as TWM
from backtest import avgdown as AV

OUT = "backtest/resultsAudit2/3"
HS = (5, 10, 20, 60)
COST = H2.COST_RT
MAIN = "甲_R5_1%穿越"
_G: dict = {}


def _init(cal, off):
    _G.update(cal=cal, off=off)


def load(args):
    sid, market = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    cff = pd.Series(c).ffill().to_numpy()
    okO = valid & np.isfinite(o) & (o > 0)
    px = np.where(okO, o, cff)
    return {"sid": sid, "market": market, "o": o, "valid": valid, "px": px, "okO": okO,
            "trd1": tb["trd"] & np.isfinite(o) & ~tb["up_o"], "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32),
            "r20": AV.r20_cal(c, bars)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchAudit2_3（上升趨勢線跌破 5／10／20／60 日＋基準②）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(H2.W0))); w1 = int(cal.searchsorted(pd.Timestamp(H2.W1)))
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if a.limit:
        U = U.head(a.limit)
    off = TR.load_official()
    with Pool(a.procs, initializer=_init, initargs=(cal, off)) as pool:
        ST = {r["sid"]: r for r in pool.map(load, list(zip(U["stock_id"], U["market"])), chunksize=16) if r is not None}
    sids = sorted(ST); sidx = {s: i for i, s in enumerate(sids)}
    log(f"[讀檔] gate3 {len(U):,}｜可用 {len(ST):,}")
    O = np.column_stack([ST[s]["o"] for s in sids]); okO = np.column_stack([ST[s]["okO"] for s in sids]); PX = np.column_stack([ST[s]["px"] for s in sids])
    VAL = np.column_stack([ST[s]["valid"] for s in sids]); TRD1 = np.column_stack([ST[s]["trd1"] for s in sids])
    R20 = np.column_stack([ST[s]["r20"] for s in sids])
    CP = np.column_stack([ST[s]["cs_pb"] for s in sids]); CG = np.column_stack([ST[s]["cs_g5"] for s in sids])
    Od = np.where(okO, O, np.nan)
    ev = pd.read_csv("backtest/resultsUT/events_X.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    ev = ev[(ev["格"] == MAIN) & ev["sid"].isin(sidx)].reset_index(drop=True)
    pos = {str(d.date()): i for i, d in enumerate(cal)}
    ev["first_pos"] = ev["first"].map(lambda s_: pos[s_]) if ev["first"].dtype == object else ev["first"].astype(int)
    S = {"原件": "researchUT.py 0feb35c37c（events_X.csv.gz 主格）", "事件": int(len(ev)), "閘": {}}
    res = {}; rows_all = []
    for H in HS:
        EW = TWM.ew_open(O, okO, PX, H)
        G = np.full((n, len(sids)), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            G[:n - H - 1] = PX[H + 1:] / Od[1:n - H] - 1.0
        Tr = np.arange(1, n - H - 1)
        HB = np.zeros((n, len(sids)), bool)
        HB[Tr] = ((CP[Tr + H + 1] - CP[Tr - 1]) > 0) | ((CG[Tr + H + 1] - CG[np.minimum(Tr + 3, n - 1)]) > 0)
        xs, x2s, Ts, keep = [], [], [], []
        why = {"超窗尾": 0, "延伸段斷點": 0, "r20不可算": 0, "無配對": 0}
        dec_cache = {}
        for i, e in ev.iterrows():
            T = int(e["T"]); s = sidx[e["sid"]]; fp = int(e["first_pos"])
            if T + 1 + H > w1 and H > 20:
                why["超窗尾"] += 1; continue
            if H > 20 and H2.brk({"cs_pb": ST[e["sid"]]["cs_pb"], "cs_g5": ST[e["sid"]]["cs_g5"]}, fp, T + 1 + H):
                why["延伸段斷點"] += 1; continue
            g = PX[T + 1 + H, s] / O[T + 1, s] - 1.0
            x = g - EW[T + 1]
            x2 = np.nan
            if np.isfinite(R20[T, s]):
                if T not in dec_cache:
                    el = VAL[T] & TRD1[T + 1] & ~HB[T] & np.isfinite(R20[T]) & np.isfinite(G[T])
                    r_ = np.where(el, R20[T], np.nan)
                    dec_cache[T] = (el, AV.deciles(r_))
                el, dec = dec_cache[T]
                if dec[s] < 0:
                    why["事件股不在配對母體"] = why.get("事件股不在配對母體", 0) + 1
                else:
                    peer = el & (dec == dec[s]); peer[s] = False
                    if peer.any():
                        x2 = g - float(G[T, peer].mean())
                    else:
                        why["無配對"] += 1
            else:
                why["r20不可算"] += 1
            xs.append(x); x2s.append(x2); Ts.append(T); keep.append(i)
            rows_all.append({"H": H, "sid": e["sid"], "T": T, "R": g, "X": x, "X2": x2})
        xs, x2s, Ts = np.array(xs), np.array(x2s), np.array(Ts)
        blk, cap = H, H2.WIN_DAYS // H
        sX = TWM.summ(xs, Ts, cal, w0, blk=blk, cap=cap); ok2 = np.isfinite(x2s)
        s2 = TWM.summ(x2s[ok2], Ts[ok2], cal, w0, blk=blk, cap=cap)
        cell = {"X（對 gate3 等權，原件量）": {**{k: sX[k] for k in ("n", "平均", "lo", "hi", "n_eff", "中位")}, "出口結果": TWM.verdict(sX)},
                "X2（基準②：前 20 日同十分位）": {**{k: s2[k] for k in ("n", "平均", "lo", "hi", "n_eff", "中位")}, "出口結果": TWM.verdict(s2)},
                "沒進的件數": why}
        for k in ("X（對 gate3 等權，原件量）", "X2（基準②：前 20 日同十分位）"):
            c_ = cell[k]
            c_["K3"] = "可執行（CI 上緣 ＜ −0.585%）" if c_["hi"] < -COST else "扣成本後不可執行"
            c_["點估計 ＜ −0.585%"] = bool(c_["平均"] < -COST)
        yr = np.array([cal[t].year for t in Ts])
        cell["X2 逐年"] = {int(y): float(np.nanmean(x2s[yr == y])) for y in sorted(set(yr))}
        res[f"H{H}"] = cell
        log(f"[H{H}] X {sX['平均']:+.3%} [{sX['lo']:+.3%}, {sX['hi']:+.3%}] {cell['X（對 gate3 等權，原件量）']['出口結果']}｜"
            f"X2 {s2['平均']:+.3%} [{s2['lo']:+.3%}, {s2['hi']:+.3%}] {cell['X2（基準②：前 20 日同十分位）']['出口結果']}｜沒進 {why}")
        if H == 20:
            mine = np.array(xs); ref = ev["X"].to_numpy(float)
            S["閘"]["H20 X 逐筆 ＝ 原件 events_X（逐位元）"] = {"筆數": [len(mine), len(ref)],
                                                           "不逐位元": int(sum(repr(float(p)) != repr(float(q)) for p, q in zip(mine, ref))) if len(mine) == len(ref) else None}
        if H == 60:
            o60 = json.load(open("backtest/resultsUT/summary.json", encoding="utf-8"))["60日（描述）"][MAIN]
            S["閘"]["H60 n／平均 ＝ 原件 summary"] = {"本件": [sX["n"], sX["平均"]], "原件": [o60["n"], o60["平均"]],
                                                   "相同": bool(sX["n"] == o60["n"] and abs(sX["平均"] - o60["平均"]) <= 1e-15)}
    S["結果"] = res
    S["穩（四個視窗基準② 同出口同方向）"] = len({tuple(res[f"H{H}"]["X2（基準②：前 20 日同十分位）"]["出口結果"]) for H in HS}) == 1
    pd.DataFrame(rows_all).to_csv(os.path.join(OUT, "events.csv.gz"), index=False, float_format="%.17g")
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[閘] {S['閘']}")
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
