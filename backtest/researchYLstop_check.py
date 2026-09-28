# -*- coding: utf-8 -*-
"""營量 跌破停損換股（描述臂）簡短查核（⛔ 不 import researchYLstop、researchYLexit*）。
自寫停損改寫 ⇒ 主世界 b10_H60 一日、b7_H40 兩日確認 ⇒ 引擎種子 0 eq_sha ＝ resultsYLstop/seeds.csv；觸發率 ＝ cells.csv。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLstop_check.py
"""
from __future__ import annotations
import hashlib, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R

OUT = "backtest/resultsYLstop"


def main():
    RES = {}
    SD = pd.read_csv(os.path.join(OUT, "seeds.csv"), dtype={"eq_sha": str}); TB = pd.read_csv(os.path.join(OUT, "cells.csv"))
    RR.use_snapshot()
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True); cal = ctx["cal"]; cl, op, NP = ctx["closes"], ctx["opens"], ctx["ncal"]; mk = ctx["mk"]; w0, w1 = ctx["w0"], ctx["w1"]; n0 = len(cal)
    base = ctx["sig13"]
    B = {}
    for s in sorted(set(base["sid"])):
        b = R.load_bars(s, mk.get(s, "twse"), cal)
        B[s] = None if b is None else (b["idx"], b["o"], b["c"], b["l"], b["next_bad"])
    SF = {}
    for s in sorted(cl):
        st_ = D.load_stock(s, mk.get(s, "twse"), cal)
        if st_ is None:
            continue
        v_ = np.flatnonzero(np.isfinite(st_.df["close"].to_numpy(float)))
        if len(v_) and v_[-1] < w1:
            SF[s] = int(v_[-1])
    bad = []; badr = []
    for bb, H, two in ((0.10, 60, False), (0.07, 40, True)):
        X = []; G = []; trig = []
        for s, k, e, x0, g0 in zip(base["sid"], base["k"].astype(int), base["entry_pos"].astype(int), base["xpos_H60"].astype(int), base["g_H60"].astype(float)):
            b = B[s]
            if H != 60:                                            # H 根固定出場＋T1
                if b is None:
                    X.append(-1); G.append(np.nan); trig.append(None); continue
                idx, o, c, lo, nb = b; n = len(idx); nbk = nb[max(0, k - 20)]; ex = k + H
                if ex < n and ex < nbk:
                    x0, g0 = int(idx[ex]), c[ex] / o[k + 1] - 1
                elif ex >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1:
                    x0, g0 = n0, float(c[n - 1] / o[k + 1] - 1)
                else:
                    X.append(-1); G.append(np.nan); trig.append(None); continue
            if b is None or x0 < 0:
                X.append(x0); G.append(g0); trig.append(None); continue
            idx, o, c, lo, nb = b; ke = k + 1; kx = int(np.searchsorted(idx, min(x0, n0 - 1), side="right") - 1); P0 = o[ke]
            hit = None; cand = None
            for j in range(ke, kx):
                if two:
                    if cand is not None and c[j] < lo[cand]:
                        hit = j; break
                    cand = j if c[j] < P0 * (1 - bb) else None
                elif c[j] < P0 * (1 - bb):
                    hit = j; break
            if hit is not None and hit + 1 <= kx:
                X.append(int(idx[hit + 1])); G.append(o[hit + 1] / P0 - 1)
            else:
                X.append(x0); G.append(g0)
            trig.append(hit is not None and hit + 1 <= kx if w0 <= e <= w1 else None)
        sig = base.copy(); sig[f"xpos_H{H}"] = np.array(X, np.int64); sig[f"g_H{H}"] = np.array(G)
        eq = np.asarray(R.simulate_mtm(sig, f"H{H}", 20, np.random.default_rng(7000), cl, op, NP, return_equity=True, log=[], d_max=None, pick="relvol",
                                       queue_days=0, stop_force=SF)["equity"], float)
        nm = f"停損_b{int(round(bb * 100))}_H{H}" + ("_兩日確認" if two else "")
        if hashlib.sha256(eq.tobytes()).hexdigest()[:16] != SD[(SD["世界"] == "主") & (SD["格"] == nm)]["eq_sha"].iloc[0]:
            bad.append(nm)
        tr = [t for t in trig if t is not None]
        if abs(np.mean(tr) - TB[TB["格"] == nm]["主_觸發率"].iloc[0]) > 1e-12:
            badr.append((nm, float(np.mean(tr))))
        print(nm, "done", bad, badr, flush=True)
    RES["① 自寫停損改寫 ⇒ eq_sha ＝ seeds.csv（b10_H60 一日、b7_H40 兩日確認）"] = {"不符": bad, "過": not bad}
    RES["② 觸發率 ＝ cells.csv"] = {"不符": badr, "過": not badr}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES["③ 閘（主程式）"] = {**S["閘"], "過": all(S["閘"].values())}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
