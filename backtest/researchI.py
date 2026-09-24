# -*- coding: utf-8 -*-
"""PREREGI（W1 回落來源拆解，台股策略線 seq3 sha a9d46345ed867cd1）——回測線落地。

第一步（§二③，本檔 --part repro）：重現 P12 交件 W1 ＝ (S1, C1, T1)、成本 0.585%、200 顆種子 default_rng(102000+r)
   每顆種子【自己最深的那一段回落】的 深度／峰日／谷日，與交件逐位比對：
     ・resultsp12/anchor_diag.csv（peak_pos／trough_pos／深度）
     ・resultsp12/cells_by_seed.csv.gz 的 own_dd（S1,C1,T1,主格窗,成本0.585%）
   ⛔ 任一顆對不上 ⇒ SystemExit，不往下算（登錄 §二③）
資料：本分支快照（data/ 樹 27d2e42a…，與 P12 交件 f7bdfb62d3 逐位相同）；⛔ 不讀 main、⛔ 不走 gate3。
引擎與 P12 同一個呼叫點：researchp12._sim（⛔ 不抄第二份）。
"""
from __future__ import annotations
import argparse
import os
import sys
import time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import p4_features as P4F
from backtest import researchp1 as P1
from backtest import researchp7 as P7
from backtest import researchp12 as P12

OUT = "backtest/resultsI"


def _repro_one(seed):
    out = P12._sim(P12._S["sigs"][("S1", "T1", "*")], P12.N_C1, seed, P12.COST_STD)
    pk, tr, depth = P12.deepest_episode(out["equity"], out["first"], out["end"], P12._S["cal"])
    return {"seed": seed, "peak_pos": pk, "trough_pos": tr, "深度": depth}


def setup():
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    sig_b = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig_b), P7.WANT_SIG_B
    if got != want:
        raise SystemExit("⛔ 門檻B sig 驗收數對不上 ⇒ 停\n  want {}\n  got  {}".format(want, got))
    sigs = {("S1", "T1", "*"): sig_b}
    return cal, ncal, closes, opens, sigs


def repro(procs, reps):
    t0 = time.time()
    cal, ncal, closes, opens, sigs = setup()
    print("[資料] 日曆 {} 根／尾 {}｜S1 門檻B sig {:,} 筆 ✅ 七個驗收數相同｜{:.0f}s".format(ncal, cal[-1].date(), len(sigs[("S1", "T1", "*")]), time.time() - t0), flush=True)
    P12._init(sigs, {}, closes, opens, ncal, {}, {}, cal)
    with Pool(procs, initializer=P12._init, initargs=(sigs, {}, closes, opens, ncal, {}, {}, cal)) as pool:
        got = pd.DataFrame(pool.map(_repro_one, [P12.SEED0 + r for r in range(reps)]))
    ad = pd.read_csv("backtest/resultsp12/anchor_diag.csv", float_precision="round_trip")
    cb = pd.read_csv("backtest/resultsp12/cells_by_seed.csv.gz", float_precision="round_trip")
    cb = cb[(cb.S == "S1") & (cb.C == "C1") & (cb["T"] == "T1") & (cb.win == "主格窗") & (cb.cost == "成本0.585%")][["seed", "own_dd"]]
    m = got.merge(ad[["seed", "peak_pos", "trough_pos", "深度"]], on="seed", suffixes=("", "_交件")).merge(cb, on="seed")
    assert len(m) == reps == len(got), (len(m), reps)
    bad = {
        "峰日": int((m["peak_pos"] != m["peak_pos_交件"]).sum()),
        "谷日": int((m["trough_pos"] != m["trough_pos_交件"]).sum()),
        "深度 vs anchor_diag": int((m["深度"] != m["深度_交件"]).sum()),
        "深度 vs cells_by_seed.own_dd": int((m["深度"] != m["own_dd"]).sum()),
    }
    os.makedirs(OUT, exist_ok=True)
    m["peak_date"] = [str(cal[i].date()) for i in m["peak_pos"]]
    m["trough_date"] = [str(cal[i].date()) for i in m["trough_pos"]]
    m.to_csv(os.path.join(OUT, "repro_p12_w1.csv"), index=False)
    print("[重現] {} 顆｜不同：{}｜中位深度 {:.4%}（交件 −41.43%）｜{:.0f}s".format(reps, bad, m["深度"].median(), time.time() - t0))
    if any(bad.values()):
        raise SystemExit("⛔ 重現 P12 W1 對不上 ⇒ 依登錄 §二③ 停、回報，⛔ 不往下算")
    print("✅ 200 顆逐位相同（峰日／谷日／深度，兩份交件檔）⇒ 可進第二步")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("repro",), default="repro")
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    if a.part == "repro":
        repro(a.procs, a.reps)
