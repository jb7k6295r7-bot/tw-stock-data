# -*- coding: utf-8 -*-
"""PREREG探索批【探索段】運氣基準 讀法丙「假訊號條件」——⛔ 只作描述臂：不改線索標記、不動 ranking_171／clues／summary。

    python3 backtest/researchExplore_fakecond.py [--procs 1] [--only I] [--out backtest/resultsExplore/fakecond]

定義（協調者指示，逐字落地）：
  171 次假訊號條件，第 i 次（i ＝ 0..170）種子 SEED_F ＝ 103000 ＋ i；rng ＝ np.random.default_rng(SEED_F)
  每個量測日（依日期順序各抽一次）從該日探索母體（eligible，n 檔，依代號排序）均勻隨機不放回挑 k ＝ ceil(0.1 × n) 檔
     ⇒ rng.choice(n, size=k, replace=False)；之後與格子同一條路：與 signal ALL 候選母體取交集（進場開盤剔除）
  其餘照格子：切點 2022-12-30、N＝8、種子 102000＋r（200 顆）、同一支 researchExplore.run_one
  每次的統計量：
     甲式（主，與格子同形）ratio_cell ＝ 年化中位 ÷ |回落中位|  ⇐ 線索的比值就是這個形
     乙式（字面「200 顆比值的中位」）ratio_seedmed ＝ median(cagr_s ÷ |mdd_s|)
  ⭐ 讀法：協調者寫「每次取 200 顆比值的中位」、又寫「其餘照格子」⇒ 兩式都報；拿線索比位置時以甲式為主（同形才可比），乙式並列
前置：與 researchExplore.main 同一串（as-of 還原、截斷日曆、RP4.build_panel、sig_explore、tradable／delist）；
      開跑前兩道對帳：①母體 ＝ features.csv 的 (量測日, 代號) ②F09+F17 種子 102000 重跑 ＝ seeds.csv 那一列（逐欄）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchExplore as RE                          # ⭐ 只 import 主程式的函式與常數，⛔ 不改它

D, H2, P4F, P12, RP4, T = RE.D, RE.H2, RE.P4F, RE.P12, RE.RP4, RE.T
SEED_F0, N_FAKE = 103000, 171
MAIN = "backtest/resultsExplore"
OUT = os.path.join(MAIN, "fakecond")
QS = (0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)


def prep(procs: int, log=print):
    """與 researchExplore.main 同一串前置 ⇒ 回 (sigA, 母體 by pos, 引擎輸入)。"""
    D.load_adj = RE.load_adj_asof
    cal_full = D.load_calendar()
    cal = cal_full[cal_full <= RE.CUT]; ncal = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(RE.W0_DATE))); w1 = ncal - 1
    marks = P12.month_marks(cal, w0, w1)
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = H2.UG.gate3(stocks)
    U = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    positions = P4F.measurement_days(cal, RE.START, None)
    panel, _ = RP4.build_panel(cal, U, positions, procs=procs, mp_check=False, log=lambda s: None)
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens = {}, {}
    for s in sorted(set(panel["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        closes[s] = st.df["close"].ffill().to_numpy(float); opens[s] = st.df["open"].to_numpy(float)
    el = panel[panel["eligible"].astype(bool)]
    pos_of = {d: i for i, d in enumerate(cal)}
    el = el.assign(pos=el["measure_date"].map(pos_of).astype(int))
    pop = {int(t): np.array(sorted(g["stock_id"])) for t, g in el.groupby("pos", sort=True)}
    sigA, _, _ = RE.sig_explore(panel, cal, closes, opens, "ALL")
    trad = T.build(set(sigA["sid"]), cal)
    off = {k: v for k, v in T.load_official().items() if v <= RE.CUT}
    dl = T.delist_status(trad, cal, official=off)
    RE._S.update(closes=closes, opens=opens, ncal=ncal, trad=trad, dl=dl, w0=w0, w1=w1, marks=marks)
    log(f"[前置] 量測日 {len(pop)}｜母體 {sum(len(v) for v in pop.values()):,} 股-月｜S0 候選母體 {len(sigA):,} 列")
    return sigA, pop


def fake_sig(i: int, sigA: pd.DataFrame, pop: dict) -> tuple[pd.DataFrame, int]:
    rng = np.random.default_rng(SEED_F0 + i)
    pos, sid = [], []
    for t in sorted(pop):                              # ⭐ 依日期順序各抽一次
        s = pop[t]; n = len(s); k = int(math.ceil(RE.TOP * n))
        take = rng.choice(n, size=k, replace=False)
        pos += [t] * k; sid += list(s[take])
    key = sigA.assign(pos=sigA["entry_pos"] - 1).set_index(["pos", "sid"])
    m = key.index.isin(pd.MultiIndex.from_arrays([np.array(pos, int), np.array(sid)]))
    return sigA[m].reset_index(drop=True), len(pos)


def summarize(df: pd.DataFrame) -> dict:
    A, Dd = float(df["cagr"].median()), float(df["mdd"].median())
    return {"A": A, "D": Dd, "ratio_cell": A / abs(Dd), "ratio_seedmed": float((df["cagr"] / df["mdd"].abs()).median())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=1); ap.add_argument("--out", default=OUT)
    ap.add_argument("--only", type=int, default=None, help="只跑第 i 次（查核用），結果寫到 --out")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    logf = open(os.path.join(a.out, "run.log"), "a", encoding="utf-8")

    def log(s):
        print(s, flush=True); logf.write(s + "\n"); logf.flush()
    log(f"=== researchExplore_fakecond {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）out={a.out} only={a.only} procs={a.procs}")
    sigA, pop = prep(a.procs, log)
    # 對帳 ①：母體 ＝ features.csv
    F = pd.read_csv(os.path.join(MAIN, "features.csv"), dtype={"sid": str}, usecols=["pos", "sid"])
    mine = {(t, s) for t, v in pop.items() for s in v}
    assert mine == set(zip(F["pos"].astype(int), F["sid"])), "⛔ 母體與 features.csv 不同"
    # 對帳 ②：一格一顆重跑 ＝ seeds.csv
    C = pd.read_csv(os.path.join(MAIN, "cands.csv"), dtype={"sid": str, "cell": str})
    c = C[C["cell"] == "F09+F17"]
    k2 = sigA.set_index(["entry_pos", "sid"]).index.isin(pd.MultiIndex.from_arrays([c["entry_pos"].astype(int), c["sid"]]))
    RE._S["sigs"] = {"F09+F17": sigA[k2].reset_index(drop=True)}
    got = RE.run_one(("F09+F17", RE.SEED0))
    S = pd.read_csv(os.path.join(MAIN, "seeds.csv"), dtype=str)
    ref = S[(S["cell"] == "F09+F17") & (S["seed"] == str(RE.SEED0))].iloc[0]
    tmp = pd.DataFrame([got]); tmp.to_csv(os.path.join(a.out, "_anchor.csv"), index=False)
    back = pd.read_csv(os.path.join(a.out, "_anchor.csv"), dtype=str).iloc[0]; os.remove(os.path.join(a.out, "_anchor.csv"))
    assert all(back[k] == ref[k] for k in ref.index), f"⛔ F09+F17 種子 102000 重跑對不上 seeds.csv：{dict(back)} vs {dict(ref)}"
    log(f"[對帳] ①母體 ＝ features.csv {len(mine):,}｜②F09+F17 種子 102000 重跑逐欄 ＝ seeds.csv（eq_sha {ref['eq_sha']}）｜{time.time() - t0:.0f}s")
    # 假訊號條件
    idx = [a.only] if a.only is not None else list(range(N_FAKE))
    sp = os.path.join(a.out, "fakecond_seeds.csv")
    done = set()
    if os.path.exists(sp):
        old = pd.read_csv(sp, dtype={"cell": str})
        cnt = old.groupby("fake_i")["seed"].nunique()
        if (cnt != RE.REPS).any():
            raise SystemExit("⛔ fakecond_seeds.csv 有不完整的次 ⇒ 先刪掉再續跑")
        done = set(cnt.index.astype(int))
    for i in idx:
        if i in done:
            continue
        sg, nsel = fake_sig(i, sigA, pop)
        RE._S["sigs"] = {f"FAKE{i:03d}": sg}
        tasks = [(f"FAKE{i:03d}", RE.SEED0 + r) for r in range(RE.REPS)]
        if a.procs > 1:                                # ⭐ fork 之後才看得到這一次的 sigs ⇒ 每次開一個 pool
            with Pool(a.procs) as pool:
                res = pool.map(RE.run_one, tasks, chunksize=5)
        else:
            res = [RE.run_one(x) for x in tasks]
        df = pd.DataFrame(res); df.insert(0, "fake_i", i); df.insert(1, "seed_f", SEED_F0 + i)
        df["n_selected"] = nsel; df["sig_rows"] = len(sg)
        df.to_csv(sp, mode="a", header=not os.path.exists(sp), index=False)
        s = summarize(df)
        log(f"  FAKE{i:03d} 抽 {nsel:,}／訊號 {len(sg):,}｜年化中位 {s['A']:+.4%} 回落中位 {s['D']:+.4%} 比值(甲) {s['ratio_cell']:.4f}｜{time.time() - t0:.0f}s")
    if a.only is None:
        aggregate(a.out, log)
    log(f"完成｜{time.time() - t0:.0f}s")


def aggregate(out, log=print):
    S = pd.read_csv(os.path.join(out, "fakecond_seeds.csv"), dtype={"cell": str}, float_precision="round_trip")
    rows = []
    for i, g in S.groupby("fake_i", sort=True):
        s = summarize(g)
        rows.append({"fake_i": int(i), "seed_f": SEED_F0 + int(i), "n_selected": int(g["n_selected"].iloc[0]),
                     "sig_rows": int(g["sig_rows"].iloc[0]), **s,
                     "eq_sha_200": hashlib.sha1("".join(g.sort_values("seed")["eq_sha"]).encode()).hexdigest()[:16]})
    X = pd.DataFrame(rows)
    X.to_csv(os.path.join(out, "fakecond_171.csv"), index=False)
    CL = pd.read_csv(os.path.join(MAIN, "clues.csv"), dtype={"cell": str}, float_precision="round_trip")
    RK = pd.read_csv(os.path.join(MAIN, "ranking_171.csv"), dtype={"cell": str}, float_precision="round_trip")
    out_j = {"說明": "PREREG探索批 探索段 運氣基準 讀法丙（假訊號條件）｜⛔ 描述臂：不改線索標記、不改 ranking／clues／summary",
             "次數": int(len(X)), "種子": "SEED_F＝103000＋i；每次 200 顆 102000＋r"}
    for col, tag in (("ratio_cell", "甲式 年化中位÷|回落中位|（與格同形，主）"), ("ratio_seedmed", "乙式 逐種子比值的中位（字面）")):
        v = X[col].to_numpy(float)
        mx = float(v.max())
        out_j[tag] = {"171次取最大": mx, "取最大的是第幾次": int(X.loc[X[col].idxmax(), "fake_i"]),
                      **{f"p{int(q * 100)}": float(np.quantile(v, q)) for q in QS}, "max": mx,
                      "線索": [{"clue": int(r.clue), "cell": r.cell, "比值": float(r.ratio),
                               "在171個中的分位（≤它的比例）": float((v <= r.ratio).mean()),
                               "大於171次取最大": bool(r.ratio > mx)} for r in CL.itertuples()],
                      "171格中大於此最大值的格數": int((RK["ratio"] > mx).sum())}
    out_j["假訊號條件 年化中位分佈"] = {f"p{int(q * 100)}": float(X["A"].quantile(q)) for q in QS} | {"max": float(X["A"].max())}
    out_j["每次挑選數（平均）"] = float(X["n_selected"].mean()); out_j["每次訊號列（平均）"] = float(X["sig_rows"].mean())
    json.dump(out_j, open(os.path.join(out, "fakecond_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    m = out_j["甲式 年化中位÷|回落中位|（與格同形，主）"]
    log(f"[讀法丙 甲式] 171 次最大 {m['max']:.4f}｜p50 {m['p50']:.4f} p95 {m['p95']:.4f} p99 {m['p99']:.4f}｜"
        + "；".join(f"{c['cell']} {c['比值']:.3f} 分位 {c['在171個中的分位（≤它的比例）']:.3f}{' ＞最大' if c['大於171次取最大'] else ''}" for c in m["線索"]))


if __name__ == "__main__":
    main()
