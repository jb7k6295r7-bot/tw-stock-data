# -*- coding: utf-8 -*-
"""rerun17 前置：在 main edc6f8002f 快照上重建 PREREG10／P1／P3 的 AND 訊號（⛔ 策略邏輯一律呼叫原程式的函式）。

    python3 -m backtest.rerun17_build [--procs 4]

四步，全部照原件的那一支：
  ① 營收面板（rev_hi24）＝ research34.process_stock（results3/panel.csv.gz 的產生器；liq_mode=shares、pub_day=10、SIG_START／SIG_END 原常數）
  ② S（3/5 主格 30|3|20）＝ research11.stock_features 的 "main" 列（results11/signals.csv.gz 的產生器）
  ③ AND ＝ research13.and_flags(S, 面板)（STALE_MAX=45，research13.build_sets 同欄位）
  ④ relvol ＝ researchp1.attach_features（resultsp1/and_signals_p1.csv.gz 的產生器）

落地讀法（⛔ 看結果前寫定）：
  ・資料 ＝ ~/h2data/<sha>/data（唯讀）；D.DATA 指過去（同 researchH2）
  ・母體 ＝ data.load_universe() ∩ universe_gate.gate3(快照 stocks.csv)（同 researchAFC_panel；新跑件一律 gate3）
    ⚠ 原件是 load_universe() 全體（分支 09-11 快照）⇒ 這一步同時換了資料與母體閘，於 README 寫明
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import rerun17 as RR

RR.use_snapshot()

from . import data as D                 # noqa: E402
from . import patterns as PT            # noqa: E402
from . import research11 as R           # noqa: E402
from . import research13 as R13         # noqa: E402
from . import research34 as R34         # noqa: E402
from . import researchp1 as P1          # noqa: E402
from . import universe_gate as UG       # noqa: E402

OUT = os.path.join(RR.OUT, "sig_edc6f")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "build.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    t0 = time.time()
    assert D.DATA == RR.H2D, D.DATA
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    uni_all = D.load_universe()
    uni = uni_all.merge(U[["stock_id"]], on="stock_id")
    log(f"===== rerun17_build {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜快照 {RR.SHA[:10]}｜日曆 {len(cal)} 根 {cal[0].date()}～{cal[-1].date()}")
    log(f"[母體] load_universe {len(uni_all):,} 檔 ∩ gate3 {len(U):,} ⇒ {len(uni):,} 檔（剔 {sorted(set(uni_all['stock_id']) - set(uni['stock_id']))}）")

    # ① 營收面板（research34.main 的非 report-only 路徑，逐步照抄呼叫順序）
    PT.PARAMS["liq_mode"] = "shares"
    bdf = D.load_benchmark(cal)
    bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    rev, rev_ly, ind = R34.load_revenue()
    rdates = R34.rebalance_dates(list(rev.index), cal, 10)
    lo = int(cal.searchsorted(pd.Timestamp(R34.SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(R34.SIG_END), side="right") - 1)
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    log(f"[①面板] 營收 {rev.shape[0]} 期 × {rev.shape[1]} 檔（{rev.index.min()}～{rev.index.max()}）；換股日 {len(rdates)}；訊號窗 {cal[lo].date()}～{cal[hi].date()}")
    rows = []
    with Pool(a.procs, initializer=R34._init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi)) as pool:
        for i, r in enumerate(pool.imap_unordered(R34.process_stock, jobs, chunksize=8)):
            if r:
                rows += r
            if (i + 1) % 500 == 0:
                log(f"  ① {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    panel = pd.DataFrame(rows)
    for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c in panel:
            panel[c] = panel[c].astype("boolean")
    panel["signal_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["signal_pos"]]
    panel["entry_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["entry_pos"]]
    panel.to_csv(os.path.join(OUT, "panel_rev.csv.gz"), index=False, compression="gzip")
    log(f"[①面板] {len(panel):,} 列、rev_hi24=True {int((panel['rev_hi24'] == True).sum()):,}｜{time.time() - t0:.0f}s")

    # ② S：research11.stock_features 的 main 列
    tasks = [(r.stock_id, r.market, r.first_seen) for r in uni.itertuples()]
    main_rows = []
    with Pool(a.procs, initializer=R._init, initargs=(cal,)) as pool:
        for i, r in enumerate(pool.imap_unordered(R.stock_features, tasks, chunksize=8)):
            if r is not None:
                main_rows.extend(r["main"])
            if (i + 1) % 500 == 0:
                log(f"  ② {i + 1}/{len(tasks)} {time.time() - t0:.0f}s")
    S_full = pd.DataFrame(main_rows)
    S_full.to_csv(os.path.join(OUT, "signals_S.csv.gz"), index=False)
    log(f"[②S] 3/5 主格 {len(S_full):,} 筆／{S_full['sid'].nunique():,} 檔｜{time.time() - t0:.0f}s")

    # ③ AND：research13.build_sets 的欄位與 and_flags
    pnl = pd.read_csv(os.path.join(OUT, "panel_rev.csv.gz"), dtype={"stock_id": str})      # ⭐ 與 research13.main 同一條讀法（讀回 csv）
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    S = pd.read_csv(os.path.join(OUT, "signals_S.csv.gz"), dtype={"sid": str})
    S = S[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    flags, and60 = R13.and_flags(S, pnl)
    AND = S[flags].copy()
    log(f"[③AND] {len(AND):,} 筆／{AND['sid'].nunique():,} 檔（占 S {len(AND) / len(S) * 100:.1f}%）")

    # ④ relvol：researchp1.attach_features
    missing, mism = P1.attach_features(AND, S, cal, uni.set_index("stock_id")["market"], a.procs)
    log(f"[④relvol] 缺 {int(AND['relvol'].isna().sum())}；k↔pos 不符 {mism}；讀不到 {len(missing)} 檔")
    if mism:
        raise SystemExit("⛔ k 與 pos 對不上 ⇒ 停")
    AND.to_csv(os.path.join(OUT, "and_signals.csv.gz"), index=False)
    log(f"[完成] {OUT}/and_signals.csv.gz｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
