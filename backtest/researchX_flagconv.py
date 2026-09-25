# -*- coding: utf-8 -*-
"""PREREGX 旗形「收斂」必報兩數（裁定線 seq159 §五①；⛔ 只改報告措辭、不改計算、⛔ 不算任何報酬）：
   ① 收斂條件擋掉幾組：同一份資料、同一個偵測器，只把收斂條件拿掉（其餘條件、轉折、換組全同）⇒ 會觸發（甲）／會有 S（乙）
      而正式版沒有的組（組＝E）。
   ② 兩半都 0 幅（旗面前半、後半收盤完全不動）幾組：在正式版的觸發組、以及①「被擋掉」那些組的觸發旗面上各數一次。
   範圍：甲 T ∈ [窗起點, 窗尾−120]、乙 S ∈ [窗起點, 窗尾−40]（原始組，合併／剔除之前）。
    ~/tw-p16/.venv/bin/python backtest/researchX_flagconv.py
"""
from __future__ import annotations
import json
import math
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                                 # noqa: E402
D, UG = H2.D, H2.UG
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import patterns_x as PX                   # noqa: E402

_ORIG = PX.face_ok


def face_ok_noconv(F, cE, rmin=PX.FL_RET_MIN, rmax=PX.FL_RET_MAX):
    m = len(F)
    ret = (cE - F.min()) / cE
    if not (rmin <= ret <= rmax):
        return False
    x = np.arange(m, dtype=float); x -= x.mean()
    sxx = float((x * x).sum())
    slope = float((x * (F - F.mean())).sum()) / sxx if sxx > 0 else 0.0
    return slope <= 0


def halves_zero(F):
    h1 = int(math.ceil(len(F) / 2.0))
    a, b = F[:h1], F[h1:]
    return bool(len(b) and a.max() == a.min() and b.max() == b.min())


_G = {}


def _init(cal, lo, hiA, hiB):
    _G.update(cal=cal, lo=lo, hiA=hiA, hiB=hiB)


def one(args):
    sid, market = args
    st = D.load_stock(sid, market, _G["cal"])
    if st is None:
        return None
    c = st.df["close"].to_numpy(float); bars = np.flatnonzero(np.isfinite(c)); cb = c[bars]
    if len(cb) < 30:
        return None
    out = {}
    for tag, fn in (("正式", _ORIG), ("無收斂", face_ok_noconv)):
        PX.face_ok = fn
        r = PX.detect_turn("flag", cb)
        PX.face_ok = _ORIG
        trig = {e["id"]: e["T"] for e in r["events"] if _G["lo"] <= bars[e["T"]] <= _G["hiA"]}
        sS = {g["id"] for g in r["groups"] if g["S"] is not None and _G["lo"] <= bars[g["S"]] <= _G["hiB"]}
        zero = {i: halves_zero(cb[i[0] + 1:T]) for i, T in trig.items()}
        out[tag] = (trig, sS, zero)
    tA, sA, zA = out["正式"]; tB, sB, zB = out["無收斂"]
    blockedT = set(tB) - set(tA); blockedS = sB - sA
    return {"觸發_正式": len(tA), "觸發_無收斂": len(tB), "收斂擋掉_甲組": len(blockedT), "反向_正式有而無收斂沒有_甲": len(set(tA) - set(tB)),
            "S_正式": len(sA), "S_無收斂": len(sB), "收斂擋掉_乙組": len(blockedS),
            "兩半0幅_正式觸發組": int(sum(zA.values())), "兩半0幅_被擋掉的觸發組": int(sum(zB[i] for i in blockedT))}


def main():
    cal = D.load_calendar()
    w0 = int(cal.searchsorted(pd.Timestamp(H2.W0))); w1 = int(cal.searchsorted(pd.Timestamp(H2.W1)))
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    with Pool(2, initializer=_init, initargs=(cal, w0, w1 - 120, w1 - 40)) as pool:
        res = [r for r in pool.map(one, list(zip(U["stock_id"], U["market"])), chunksize=16) if r]
    tot = {k: int(sum(r[k] for r in res)) for k in res[0]}
    print(json.dumps(tot, ensure_ascii=False, indent=1))
    json.dump(tot, open("backtest/resultsX/flag_convergence.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
