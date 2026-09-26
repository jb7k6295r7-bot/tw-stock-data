# -*- coding: utf-8 -*-
"""均線精度回查（回測線，2026-09-27；起因：PREREG四類單獨的查核抓到 yfstop_lines.ma_valid 的 cumsum 相減式在「收盤恰等於均線」時誤判）。
⛔ 只數線、不跑引擎、不算報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.ma_precision

對每一批已交件用過的 MA 線（arm＝state）：
  舊 ＝ yfstop_lines.ma_valid（cumsum 相減）→ ma_levels；新 ＝ fsum 版（math.fsum(窗)÷n）→ 同一個 ma_levels
  逐條比「觸發日」＝ yfstop_lines.first_trigger(lv, e, closes, xp, le=False)（引擎同一式：t−1 收盤 ＜ 線、t ∈ (e, xp)）
批：
  main  ＝ listexit_lines.setup_t1() 的營飆 v1 訊號表（researchYfStop M20／M50 主版與 ⓐⓑ 臂；researchYfV2 候選一 ＝ M20 ⓐ、C1 分佈取自它、C2 ＝ M20 主版）
  poolD ＝ yfstop_lines.pool_rows(ctx)（researchYfStop ⓓ 補股池 M20／M50）
另報：每條線上「收盤 ＜ 線」判定翻轉的天數；全序列（每檔全部有效 K 棒）舊新兩式均線值逐位元不同的根數與翻轉數；float64 還原價對照（證明偵測得到）
輸出 backtest/resultsYfStop/ma_precision_lines.csv（只列觸發日會變或有任一天翻轉的線）、ma_precision_summary.json
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np
import pandas as pd

from . import listexit_lines as L
from . import researchYfStop as YS
from . import yfstop_lines as Y

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYfStop")


def ma_fsum(c_cal, idx, n):
    cv = np.asarray(c_cal, float)[idx]
    ma = np.full(len(cv), np.nan)
    if len(cv) >= n:
        w = np.lib.stride_tricks.sliding_window_view(cv, n)
        ma[n - 1:] = np.fromiter((math.fsum(r) for r in w), float, count=len(w)) / n
    return ma


def compare(tag, sig, closes, n, rows_out):
    cache = {}
    nl = nchg = nflip_lines = 0; flip_days = 0; sids = set(); dir_ = {"舊早新晚或不觸發": 0, "新早舊晚或舊不觸發": 0}
    for sid, k, e, xp in Y._rows(sig):
        if xp < 0:
            continue
        if sid not in cache:
            idx = YS.bars_of(sid)["idx"]
            cache[sid] = (idx, Y.ma_valid(closes[sid], idx, n), ma_fsum(closes[sid], idx, n))
        idx, mo, mn = cache[sid]
        lo = Y.ma_levels(closes[sid], idx, mo, k, e, xp, "state")
        ln = Y.ma_levels(closes[sid], idx, mn, k, e, xp, "state")
        to = Y.first_trigger(lo, e, closes[sid], xp, False)
        tn = Y.first_trigger(ln, e, closes[sid], xp, False)
        c = np.asarray(closes[sid][e:xp], float)
        with np.errstate(invalid="ignore"):
            fo = np.isfinite(lo[:xp - e]) & (c < lo[:xp - e]); fn = np.isfinite(ln[:xp - e]) & (c < ln[:xp - e])
        nfl = int((fo != fn).sum())
        nl += 1; flip_days += nfl; nflip_lines += nfl > 0
        if to != tn:
            nchg += 1; sids.add(sid)
            dir_["舊早新晚或不觸發" if (to >= 0 and (tn < 0 or to < tn)) else "新早舊晚或舊不觸發"] += 1
        if to != tn or nfl:
            rows_out.append({"批": tag, "線": f"M{n}", "sid": sid, "entry_pos": e, "xpos": xp, "觸發日_舊": to, "觸發日_新": tn,
                             "觸發日會變": int(to != tn), "翻轉天數": nfl, "最大|舊−新|": float(np.nanmax(np.abs(lo - ln))) if np.isfinite(lo - ln).any() else 0.0})
    return {"線數": nl, "觸發日會變的線": nchg, "涉及檔數": len(sids), "方向": dir_, "有任一天翻轉的線": int(nflip_lines), "翻轉天數合計": int(flip_days)}


def full_series(closes, sids, label):
    """每檔【全部】有效 K 棒（不限持有窗）上，舊新兩式的「收盤 ＜ 均線」判定翻轉幾次。"""
    tot = fl = neq = 0
    for sid in sids:
        idx = YS.bars_of(sid)["idx"]
        c = np.asarray(closes[sid], float); cb = c[idx]
        for n in (20, 50):
            mo = Y.ma_valid(c, idx, n); mn = ma_fsum(c, idx, n)
            with np.errstate(invalid="ignore"):
                fl += int((np.isfinite(mo) & ((cb < mo) != (cb < mn))).sum())
            tot += int(np.isfinite(mo).sum()); neq += int((np.isfinite(mo) & (mo != mn)).sum())
    return {"價格來源": label, "檔數": len(sids), "比較數": tot, "均線值逐位元不同": neq, "翻轉": fl}


def control_f64(sids, ctx):
    """對照：同一批檔改用 float64 還原價（researchAvg.prep ＝ PREREG四類單獨用的那一套）⇒ 證明偵測得到翻轉。"""
    import sys
    sys.path.insert(0, HERE)
    import researchAvg as RA
    off = RA.TR.load_official()
    tot = fl = 0
    for sid in sids:
        P = RA.prep(sid, ctx["mk"].get(sid, "twse"), ctx["cal"], off)
        if P is None:
            continue
        b = P["bars"]; c = P["c"]; cb = c[b]
        for n in (20, 50):
            mo = Y.ma_valid(c, b, n); mn = ma_fsum(c, b, n)
            with np.errstate(invalid="ignore"):
                fl += int((np.isfinite(mo) & ((cb < mo) != (cb < mn))).sum())
            tot += int(np.isfinite(mo).sum())
    return {"價格來源": "researchAvg.prep（float64 還原價）", "檔數": len(sids), "比較數": tot, "翻轉": fl}


def main():
    t0 = time.time()
    logs = []

    def log(x):
        print(x, flush=True); logs.append(x)
    ctx = L.setup_t1(log)
    YS._G["ctx"] = ctx
    rows = []; S = {}
    for n in (20, 50):
        S[f"main_M{n}"] = compare("main", ctx["sig"], ctx["closes"], n, rows)
        log(f"[main M{n}] {S[f'main_M{n}']}")
    # ⓓ 補股池（同 researchYfStop.pool_arms 的建法）
    RR = ctx["RR"]
    P = Y.pool_rows(ctx)
    extra = sorted(set(P["sid"]) - set(ctx["closes"]))
    cz, oz = RR.load_prices(extra, ctx["cal"], ctx["mk"], "branch")
    ctx["closes"].update(cz); ctx["opens"].update(oz)
    for n in (20, 50):
        S[f"poolD_M{n}"] = compare("poolD", P, ctx["closes"], n, rows)
        log(f"[poolD M{n}] {S[f'poolD_M{n}']}")
    sids = sorted(set(ctx["sig"]["sid"]) | set(P["sid"]))
    S["全序列_引擎價"] = full_series(ctx["closes"], sids, "rerun17.load_prices（引擎用的 closes；dtype " + str(ctx["closes"][sids[0]].dtype) + "）")
    log(f"[全序列] {S['全序列_引擎價']}")
    S["對照_float64"] = control_f64(sorted(set(ctx["sig"]["sid"]))[:300], ctx)
    log(f"[對照] {S['對照_float64']}")
    S["訊號列"] = {"main": int(len(ctx["sig"])), "poolD": int(len(P))}
    S["程式 sha256"] = {f: __import__("hashlib").sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
                      for f in ("yfstop_lines.py", "ma_precision.py", "researchYfStop.py", "listexit_lines.py")}
    S["秒"] = round(time.time() - t0)
    pd.DataFrame(rows, columns=["批", "線", "sid", "entry_pos", "xpos", "觸發日_舊", "觸發日_新", "觸發日會變", "翻轉天數", "最大|舊−新|"]).to_csv(os.path.join(OUT, "ma_precision_lines.csv"), index=False)
    json.dump(S, open(os.path.join(OUT, "ma_precision_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(json.dumps(S, ensure_ascii=False))


if __name__ == "__main__":
    main()
