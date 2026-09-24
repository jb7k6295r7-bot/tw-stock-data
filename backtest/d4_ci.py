# -*- coding: utf-8 -*-
"""D4 必報欄① 的 CI（⇐ seq19 §5-2-3；裁定線 1950 §二 指名要補）。

量　逐月超額 ＝ S1′ 的月報酬 − 基準臂同月的月報酬（⭐ 同窗同月 ⇒ 配對）
n　 判定窗內月數（⭐ 程式算出來，⛔ 不寫死 114）
SE　【並列兩個】① 月分群配對 SE　② Newey-West lag=5（⛔ 固定）⇒ **CI 取較寬的那一個**
⛔ 回落腳沒有 CI（單一極值）⇒ 只報點值與兩臂差
⚠ 必報 lag1~lag5 自相關（⛔ 只報值、不做判斷）
⭐ 逐月報酬取自 researchp12.win_read 的 mret（＝ researchp11.monthly_returns，⛔ 沒有第二份實作）
"""
from __future__ import annotations
import os, sys, math
from multiprocessing import Pool
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F, research11 as R
from backtest import researchp1 as P1, researchp7 as P7, researchp12 as P12, tradability as T
import backtest.researchd4 as D4

OUT = "backtest/results_d4"
_S: dict = {}


def _init(sigs, closes, opens, ncal, marks, trad):
    _S.update(sigs=sigs, closes=closes, opens=opens, ncal=ncal, marks=marks, trad=trad)


def _mret(args):
    arm, seed, use_tr = args
    R.COST = D4.COST_STD
    out = R.simulate_mtm(_S["sigs"][arm], D4.RULE, D4.N_C1, np.random.default_rng(seed),
                         _S["closes"], _S["opens"], _S["ncal"], return_equity=True,
                         tradable=_S["trad"] if use_tr else None)
    return (arm, seed, use_tr, P12.win_read(out, D4.W0, D4.W1, _S["marks"])["mret"])


def nw_se(x: np.ndarray, lag: int = 5) -> float:
    """Newey-West（對平均數），lag 固定 5。"""
    x = np.asarray(x, float); n = len(x); e = x - x.mean()
    g0 = float((e * e).sum()) / n
    s = g0
    for k in range(1, lag + 1):
        gk = float((e[k:] * e[:-k]).sum()) / n
        s += 2.0 * (1.0 - k / (lag + 1.0)) * gk
    return math.sqrt(max(s, 0.0) / n)


def main():
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
    panel["measure_date"] = pd.to_datetime(panel["measure_date"])
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    marks = P12.month_marks(cal, D4.W0, D4.W1)
    n_month = len(marks) - 1
    print("[窗] [{},{}]｜**{} 個月**（⭐ 算出來的；seq19 §5-2-3 寫 114）".format(D4.W0, D4.W1, n_month))

    ed = pd.read_csv(os.path.join(OUT, "elig_d4.csv.gz"), dtype={"stock_id": str})
    ed["measure_date"] = pd.to_datetime(ed["measure_date"])
    key = ed.set_index(["stock_id", "measure_date"])["elig_d4"]
    p2 = panel.copy()
    p2["eligible"] = list(zip(p2["stock_id"].astype(str), p2["measure_date"]))
    p2["eligible"] = p2["eligible"].map(key).fillna(False).astype(bool)
    sigs = {
        "S1p": P7.build_sig_gate_b(p2, cal, closes, opens, start=D4.START, signal="B"),
        "S0_mkt": P7.build_sig_gate_b(panel, cal, closes, opens, start=D4.START, signal="ALL"),
        "S0_pool": P7.build_sig_gate_b(p2, cal, closes, opens, start=D4.START, signal="ALL"),
    }
    trad = T.build(set().union(*[set(v["sid"]) for v in sigs.values()]), cal)
    REPS = 200
    jobs = [(a, D4.SEED0 + r, u) for a in sigs for r in range(REPS) for u in (False, True)]
    with Pool(6, initializer=_init, initargs=(sigs, closes, opens, ncal, marks, trad)) as pool:
        res = pool.map(_mret, jobs, chunksize=8)
    M = {}
    for arm, seed, u, mr in res:
        M.setdefault((arm, u), {})[seed] = np.asarray(mr, float)

    rows, ac_rows = [], []
    for u in (False, True):
        col = "附欄(三臂全開)" if u else "主欄(tradable 關)"
        for lab, base in (("Δ_mkt(甲)", "S0_mkt"), ("Δ_pool", "S0_pool")):
            # ⭐ 逐種子配對差的【逐月序列】，再對種子取平均 ⇒ 一條 n 個月的序列
            seeds = sorted(M[("S1p", u)])
            dif = np.mean([M[("S1p", u)][s] - M[(base, u)][s] for s in seeds], axis=0)
            x = dif[np.isfinite(dif)]
            n = len(x); mean = float(x.mean())
            se_cl = float(x.std(ddof=1) / math.sqrt(n))
            se_nw = nw_se(x, 5)
            wide = "NW(lag5)" if se_nw >= se_cl else "月分群"
            se = max(se_cl, se_nw)
            rows.append({"欄": col, "量": lab, "n_月": n, "月超額中位_pp": float(np.median(x)) * 100,
                         "點估計_pp": mean * 100, "月分群SE_pp": se_cl * 100, "NW5_SE_pp": se_nw * 100,
                         "採用": wide, "lo_pp": (mean - 1.96 * se) * 100, "hi_pp": (mean + 1.96 * se) * 100,
                         "CI含0": bool((mean - 1.96 * se) * (mean + 1.96 * se) <= 0)})
            s_ = pd.Series(x)
            ac_rows.append({"欄": col, "量": lab, **{f"lag{k}": float(s_.autocorr(lag=k)) for k in range(1, 6)}})
    ci = pd.DataFrame(rows); ac = pd.DataFrame(ac_rows)
    ci.to_csv(os.path.join(OUT, "ci_monthly.csv"), index=False)
    ac.to_csv(os.path.join(OUT, "acf_monthly.csv"), index=False)
    print("\n=== ⭐ 年化腳的月分群配對 CI（⛔ 回落腳依登錄沒有 CI）===")
    print(ci.to_string(index=False))
    print("\n=== ⚠ 必報：逐月超額的 lag1~lag5 自相關（⛔ 只報值，不做判斷）===")
    print(ac.to_string(index=False))
    print("\n⇒ 落檔 {}/ci_monthly.csv、{}/acf_monthly.csv".format(OUT, OUT))


if __name__ == "__main__":
    main()
