# -*- coding: utf-8 -*-
"""D4（放寬候選池的三個閘門）：Δ_pool 與 Δ_mkt，主欄（tradable 關）＋附欄（三臂全開）。

⇐ D4 seq=17／seq=18 §1-2-2／§4-2／§4-3／§一之六；裁定線 1934（seq70）、台股策略線 1934（seq58）
⛔ 不另建引擎：一律走 research11.simulate_mtm；sig 走 researchp7.build_sig_gate_b；
   窗讀走 researchp12.win_read（它再呼叫 research13.window_stats／researchp3.exposure_series）

四個量（⛔ 各自標名，⛔ 不可混欄）：
  S1'      選股器（門檻B 三條布林）接 elig_d4（2,037 檔；2,039 母體剔 9103／9105 兩檔 TDR）
  S0_mkt   舊面板 eligible 的 naive 等權（⭐ 含那 2 檔 TDR，⛔ 一檔都不動）⇒ 與舊 13.25pp 同錨
  S0_mkt2  同上但剔掉那 2 檔                       ⇒ ⛔ 只當描述，用來算 (甲)−(乙)
  S0_pool  elig_d4 的 naive 等權                    ⇒ D4 必報欄①

  Δ_mkt(甲) ＝ S1' − S0_mkt   ⇒ ⭐ 判定格（裁定線 1934）
  Δ_mkt(乙) ＝ S1' − S0_mkt2  ⇒ ⛔ 描述欄
  Δ_pool    ＝ S1' − S0_pool  ⇒ 必報欄①

共用（⛔ 差一格就不可相減）：窗 [523,2835]／成本 0.585%／C1＝n_slots 8／T1＝H120 輪動／200 顆種子
量 ＝ **固定窗的最大回落**（⛔ 不是逐種子自己最深的回落段）
"""
from __future__ import annotations
import argparse, os, sys, time
from multiprocessing import Pool
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F, research11 as R, research13 as R13
from backtest import researchp1 as P1, researchp3 as P3, researchp7 as P7, researchp11 as P11
from backtest import researchp12 as P12, tradability as T

RULE, N_C1, SEED0, REPS = "H120", 8, 104000, 200      # ⛔ 新種子基底，與 P1/7/9/11/12 都不重疊
COST_STD = R.COST
W0, W1 = 523, 2835
START = P12.START
OUT = "backtest/results_d4"
ARMS = ("S1p", "S0_mkt", "S0_mkt2", "S0_pool")
_S: dict = {}


def _init(sigs, closes, opens, ncal, marks, trad):
    _S.update(sigs=sigs, closes=closes, opens=opens, ncal=ncal, marks=marks, trad=trad)


def _one(args):
    arm, seed, use_tr = args
    R.COST = COST_STD
    out = R.simulate_mtm(_S["sigs"][arm], RULE, N_C1, np.random.default_rng(seed),
                         _S["closes"], _S["opens"], _S["ncal"], return_equity=True,
                         tradable=_S["trad"] if use_tr else None)
    r = P12.win_read(out, W0, W1, _S["marks"])
    rec = {"arm": arm, "seed": seed, "tradable": bool(use_tr), "cagr": r["cagr"], "mdd": r["mdd"],
           "tr": r["tr"], "expo": r["expo"], "trades": r["trades"], "slot": r["slot"]}
    if use_tr:
        for k in ("tr_limit_up", "tr_halt_in", "tr_exit_delayed", "tr_close_locked"):
            rec[k] = int(out.get(k, 0))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--reps", type=int, default=REPS)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
    panel["measure_date"] = pd.to_datetime(panel["measure_date"])
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    marks = P12.month_marks(cal, W0, W1)
    print("[窗] [{},{}] {} ~ {}｜{} 日／{} 個月".format(
        W0, W1, cal[W0].date(), cal[W1].date(), W1 - W0 + 1, len(marks) - 1))

    ed = pd.read_csv(os.path.join(OUT, "elig_d4.csv.gz"), dtype={"stock_id": str})
    ed["measure_date"] = pd.to_datetime(ed["measure_date"])
    key = ed.set_index(["stock_id", "measure_date"])["elig_d4"]
    pan2 = panel.copy()
    pan2["_k"] = list(zip(pan2["stock_id"].astype(str), pan2["measure_date"]))
    pan2["elig_d4"] = pan2["_k"].map(key).fillna(False).astype(bool)
    tdr2 = ["9103", "9105"]

    # ── 四臂的 sig（⭐ 全部走 build_sig_gate_b，⛔ 沒有第二份實作）
    sigs = {}
    sigs["S0_mkt"] = P7.build_sig_gate_b(panel, cal, closes, opens, start=START, signal="ALL")
    got, want = P7.accept_sig_b(P7.build_sig_gate_b(panel, cal, closes, opens, start=START, signal="B")), P7.WANT_SIG_B
    if got != want:
        raise SystemExit("⛔ 門檻B 驗收數對不上 ⇒ 停跑\n  want {}\n  got  {}".format(want, got))
    print("[閘門] 門檻B 七個驗收數逐項相同 ✅（⭐ 錨在既有件上）")
    sigs["S0_mkt2"] = sigs["S0_mkt"][~sigs["S0_mkt"]["sid"].isin(tdr2)].reset_index(drop=True)
    p2 = pan2.copy(); p2["eligible"] = p2["elig_d4"]        # ⭐ 換旗標，⛔ 不改 build_sig_gate_b
    sigs["S1p"] = P7.build_sig_gate_b(p2, cal, closes, opens, start=START, signal="B")
    sigs["S0_pool"] = P7.build_sig_gate_b(p2, cal, closes, opens, start=START, signal="ALL")
    for k in ARMS:
        s = sigs[k]
        print("[sig] {:<8}{:>8,} 筆／{:>5,} 檔／{} 月".format(k, len(s), s["sid"].nunique(), s["month"].nunique()))
    assert not set(sigs["S1p"]["sid"]) & set(tdr2), "⛔ S1′ 不該含 TDR"
    assert set(tdr2) <= set(sigs["S0_mkt"]["sid"]), "⛔ S0_mkt 應含那 2 檔 TDR（與舊值同錨）"
    print("[閘門] S1′ 無 TDR ✅｜S0_mkt 含 9103／9105 ✅（seq17 §4-3）")

    trad = T.build(set().union(*[set(sigs[k]["sid"]) for k in ARMS]), cal)
    print("[tradable] 旗標建好 {:,} 檔（{:.0f}s）".format(len(trad), time.time() - t0))

    jobs = [(arm, SEED0 + r, u) for arm in ARMS for r in range(a.reps) for u in (False, True)]
    with Pool(a.procs, initializer=_init, initargs=(sigs, closes, opens, ncal, marks, trad)) as pool:
        rows = pool.map(_one, jobs, chunksize=8)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    print("[跑完] {:,} 格（{:.0f}s）⇒ {}/cells.csv".format(len(df), time.time() - t0, OUT))

    # ── 逐種子配對差（⭐ 同種子相減，⛔ 不是中位數相減）
    out_rows = []
    for use_tr in (False, True):
        d = df[df["tradable"] == use_tr]
        piv = {k: d[d["arm"] == k].set_index("seed") for k in ARMS}
        for lab, base in (("Δ_mkt(甲)", "S0_mkt"), ("Δ_mkt(乙)", "S0_mkt2"), ("Δ_pool", "S0_pool")):
            for q in ("cagr", "mdd"):
                x = (piv["S1p"][q] - piv[base][q]).dropna()
                out_rows.append({"欄": "附欄(三臂全開)" if use_tr else "主欄(tradable 關)", "量": lab, "腳": q,
                                 "中位_pp": float(x.median()) * 100, "p10_pp": float(x.quantile(.1)) * 100,
                                 "p90_pp": float(x.quantile(.9)) * 100, "為正顆數": int((x > 0).sum()), "n": len(x)})
    res = pd.DataFrame(out_rows)
    res.to_csv(os.path.join(OUT, "deltas.csv"), index=False)
    print("\n=== ⭐ 逐種子配對差（{} 顆種子；量＝固定窗）===".format(a.reps))
    print(res.to_string(index=False))
    print("\n=== 四臂各自的水準（中位）===")
    lv = df.groupby(["tradable", "arm"])[["cagr", "mdd", "expo", "trades"]].median()
    print(lv.to_string())
    tr = df[df["tradable"]]
    print("\n=== ⭐ seq17 §6-4：附欄的擋單數（中位／總和）===")
    for k in ("tr_limit_up", "tr_halt_in", "tr_exit_delayed", "tr_close_locked"):
        if k in tr:
            g = tr.groupby("arm")[k].median()
            print("  {:<18}".format(k) + "｜".join("{} {:.0f}".format(i, v) for i, v in g.items()))
    print("\n⇒ 落檔 {}/cells.csv、{}/deltas.csv".format(OUT, OUT))


if __name__ == "__main__":
    main()
