# -*- coding: utf-8 -*-
"""researchYF_N 獨立查核（回測線計算子代理；⛔ 不改既有檔）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYF_N_check [--procs 3]

 C1 抽樣種子 r ∈ {0, 57, 199} × N ∈ {10, 15, 20} × 兩世界：另寫一支逐日迴圈小引擎（等權 N 槽、排程出場→停止交易強制出場→進場抽籤 rng.permutation、
    slot ＝ 前一日權益 ÷ N、成本出場扣），⛔ 不呼叫 research11.simulate_mtm
    ⇒ ① 逐日權益 vs simulate_mtm（最大相對差）② 逐日收盤持倉集合 vs simulate_mtm audit 區間（不同天數）
    ③ 由小引擎直接數的 持股、現金、抽籤落選、槽滿未進、等效獨立（researchDumb.eff_n 原迴圈式 np.corrcoef）、右尾（前 10% 占比、貢獻和、淨報酬中位）
       vs backtest/resultsYF_N/seeds.csv.gz 同顆（計數 ＝ 0 差、浮點相對差 ≤ 1e−9）
 C2 cells.csv 各格中位、比值、對 0050 標籤由 seeds.csv.gz 重算（0 不同）
輸出 backtest/resultsYF_N/check.json、run_check.log
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchYF_N as M                      # noqa: E402

OUT = M.OUT
RS = (0, 57, 199)
COST = R.COST
_W: dict = {}


def mini(W, N, r):
    sig = W["SIG"][True]
    d = sig[["sid", "entry_pos", "xpos_H120", "g_H120"]].dropna()
    d = d[d["xpos_H120"] >= 0]
    by = {}
    for sid, e, x, g in zip(d["sid"], d["entry_pos"].astype(int), d["xpos_H120"].astype(int), d["g_H120"].astype(float)):
        by.setdefault(e, []).append((sid, x, g))
    first, last = int(d["entry_pos"].min()), int(d["xpos_H120"].max())
    NP = W["NP"]; cl, op, SF = W["closes"], W["opens"], W["SF"]
    rng = np.random.default_rng(RR.P10_SEED0 + r)
    eq = np.ones(NP); hv_ = np.zeros(NP); cash = 1.0; pos = []
    HOLD = {}; lose = []; full = []; TR = []
    t_end = min(NP, last + 2)
    for t in range(first, t_end):
        for p in pos:
            L = SF.get(p[1])
            if L is not None and t == L + 1 and p[0] > t:
                p[0] = t; p[3] = float(cl[p[1]][L]) / p[4] - 1.0
        keep = []
        for p in pos:
            if p[0] <= t:
                cash += p[2] * (1 + p[3] - COST)
                TR.append((p[1], p[5], t, p[2], p[3], p[6]))
            else:
                keep.append(p)
        pos = keep
        rows = by.get(t)
        if rows:
            held = {p[1] for p in pos}
            cand = [z for z in rows if z[0] not in held]
            if len(pos) < N:
                if cand:
                    free = N - len(pos)
                    order = rng.permutation(len(cand)); take = list(order[:free]); rest = list(order[free:])
                    slot = eq[t - 1] / N
                    for j, i in enumerate(take):
                        amt = min(slot, cash)
                        if amt <= 1e-9:
                            rest = take[j:] + rest; break
                        cash -= amt
                        sid, x, g = cand[i]
                        ep = float(op[sid][t])
                        if not np.isfinite(ep) or ep <= 0:
                            ep = float(cl[sid][t])
                        pos.append([x, sid, amt, g, ep, t, eq[t - 1]])
                    lose += [t] * len(rest)
            else:
                full += [t] * len(cand)
        hv = sum(p[2] * float(cl[p[1]][t]) / p[4] for p in pos)
        eq[t] = cash + hv; hv_[t] = hv
        HOLD[t] = frozenset(p[1] for p in pos)
    end = min(NP, last + 2)
    eq[:first] = 1.0; eq[end:] = eq[end - 1]
    for p in pos:
        TR.append((p[1], p[5], NP, p[2], float(cl[p[1]][end - 1]) / p[4] - 1.0, p[6]))
    return eq, hv_, HOLD, np.array(lose, int), np.array(full, int), TR, first, end


def eff_loop(closes, iv, days):
    """researchDumb.eff_n 原迴圈式。"""
    res = []
    for t in days:
        held = [s for s, t0, t1 in iv if t0 <= t < t1]
        N = len(held)
        if N == 0:
            continue
        if N == 1:
            res.append((t, 1, np.nan, 1.0)); continue
        Rm = []
        for s in held:
            cc = np.asarray(closes[s][max(t - 60, 0):t + 1], float)
            Rm.append(cc[1:] / cc[:-1] - 1.0 if len(cc) == 61 else np.full(60, np.nan))
        Rm = np.array(Rm); cs = []
        for a in range(N):
            for b in range(a + 1, N):
                mk = np.isfinite(Rm[a]) & np.isfinite(Rm[b])
                if mk.sum() < 40:
                    continue
                u, v = Rm[a][mk], Rm[b][mk]
                if u.std() == 0 or v.std() == 0:
                    continue
                cs.append(float(np.corrcoef(u, v)[0, 1]))
        rho = float(np.mean(cs)) if cs else np.nan
        res.append((t, N, rho, N / (1 + (N - 1) * rho) if np.isfinite(rho) else np.nan))
    return res


def job(args):
    wn, N, r = args
    W = _W[wn]
    eq, hv, HOLD, lose, full, TR, first, end = mini(W, N, r)
    au = []
    o = R.simulate_mtm(W["SIG"][True], "H120", N, np.random.default_rng(RR.P10_SEED0 + r), W["closes"], W["opens"], W["NP"],
                       return_equity=True, stop_force=W["SF"], audit=au)
    e2 = np.asarray(o["equity"], float)
    out = {"世界": wn, "N": N, "r": r, "權益最大相對差": float(np.max(np.abs(eq / e2 - 1)))}
    iv_e = [(s, tb, ts) for s, tb, ts, *_ in M.trades_of(au, W["NP"])]
    w0, w1 = W["w0"], W["w1"]
    bad = 0
    for t in range(max(first, w0), min(end, w1 + 1)):
        if HOLD.get(t, frozenset()) != frozenset(s for s, tb, ts in iv_e if tb <= t < ts):
            bad += 1
    out["持倉不同天數"] = bad; out["比對天數"] = int(min(end, w1 + 1) - max(first, w0))
    iv = [(s, tb, ts) for s, tb, ts, *_ in TR]
    nh = np.zeros(W["NP"])
    for t, h in HOLD.items():
        nh[t] = len(h)
    row = {}
    for sg, (x, y) in W["segp"].items():
        row[f"{sg}_持股"] = float(np.mean(nh[x:y + 1])); row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
        row[f"{sg}_抽籤落選"] = int(((lose >= x) & (lose <= y)).sum()); row[f"{sg}_槽滿未進"] = int(((full >= x) & (full <= y)).sum())
        days = sorted({tb for s, tb, ts in iv if x <= tb <= y})
        en = eff_loop(W["closes"], iv, days)
        row[f"{sg}_等效獨立"] = float(np.nanmean([z[3] for z in en])) if en else np.nan
        cs = np.array([amt * (g - COST) / ep_ for s, tb, ts, amt, g, ep_ in TR if x <= tb <= y])
        nets = np.array([g - COST for s, tb, ts, amt, g, ep_ in TR if x <= tb <= y])
        k = int(math.ceil(0.1 * len(cs)))
        od = np.argsort(-cs, kind="stable")[:k]
        row[f"{sg}_交易數"] = len(cs)
        row[f"{sg}_前10%占比"] = float(cs[od].sum() / cs.sum()) if cs.sum() > 0 else np.nan
        row[f"{sg}_前10%占正貢獻"] = float(cs[od].sum() / cs[cs > 0].sum()) if cs[cs > 0].sum() > 0 else np.nan
        row[f"{sg}_前10%貢獻和"] = float(cs[od].sum()); row[f"{sg}_前10%淨報酬中位"] = float(np.median(nets[od]))
    out["row"] = row
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    log = M.log_to(os.path.join(OUT, "run_check.log"))
    log(f"[查核開始] {M.now_tpe()}（台北）")
    Wm, _ = IG.main_world(log)
    We, _ = IG.early_world(log, a.procs)
    _W["主"], _W["早年"] = Wm, We
    with Pool(a.procs) as pool:
        RES = pool.map(job, [(wn, N, r) for wn in ("主", "早年") for N in M.NS for r in RS], chunksize=1)
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip").set_index(["世界", "N", "r"])
    CK = {"C1": [], "C1_不同": 0}
    for x in RES:
        ref = SE.loc[(x["世界"], x["N"], x["r"])]
        diff = {}
        for k, v in x["row"].items():
            rv = ref[k]
            if isinstance(v, int):
                if int(rv) != v:
                    diff[k] = (v, int(rv))
            elif not (np.isnan(v) and np.isnan(rv)) and not (abs(v - rv) <= 1e-9 * max(1.0, abs(rv))):
                diff[k] = (v, float(rv))
        okk = x["權益最大相對差"] <= 1e-10 and x["持倉不同天數"] == 0 and not diff
        CK["C1_不同"] += int(not okk)
        CK["C1"].append({"世界": x["世界"], "N": x["N"], "r": x["r"], "權益最大相對差": x["權益最大相對差"], "持倉不同天數": x["持倉不同天數"],
                         "比對天數": x["比對天數"], "指標不同": diff})
        log(f"[C1] {x['世界']} N{x['N']} r{x['r']}｜權益差 {x['權益最大相對差']:.2e}｜持倉不同 {x['持倉不同天數']}/{x['比對天數']}｜指標不同 {diff}")
    # C2
    SE2 = SE.reset_index(); C = pd.read_csv(os.path.join(OUT, "cells.csv"), encoding="utf-8-sig")
    bad = 0
    for row in C.itertuples():
        g = SE2[(SE2["世界"] == row.世界) & (SE2["N"] == row.N)]
        c_, m_ = float(g[f"{row.段}_年化"].median()), float(g[f"{row.段}_回落"].median())
        W = _W[row.世界]; lab = IG.label(c_, m_, W["b50"][row.段])
        if abs(c_ - row.年化_中位) > 1e-9 or abs(m_ - row.回落_中位) > 1e-9 or abs(c_ / abs(m_) - row.比值) > 1e-8 or lab != row.對0050:
            bad += 1
        for k in ("持股", "現金", "抽籤落選", "槽滿未進", "等效獨立", "前10%占比", "前10%占正貢獻"):
            v = float(g[f"{row.段}_{k}"].median())
            cv = float(C.loc[row.Index, f"{k}_中位"])
            if not (np.isnan(v) and np.isnan(cv)) and not (abs(v - cv) <= 1e-8 * max(1, abs(v))):
                bad += 1
    CK["C2_不同"] = bad
    CK["結論"] = "過" if CK["C1_不同"] == 0 and bad == 0 else "⛔ 不過"
    CK["完成（台北）"] = M.now_tpe()
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] C1 不同 {CK['C1_不同']}／{len(RES)}｜C2 不同 {bad}｜{CK['結論']}")


if __name__ == "__main__":
    main()
