# -*- coding: utf-8 -*-
"""本批 A／F／C 共同前置：在 main edc6f8002f 快照上重建 P4 面板（researchp4.build_panel，同一支實作）。
與舊面板（resultsp4/panel.csv.gz，分支舊快照）差在兩處（⛔ 看任何結果前寫定）：
  ① 資料 ＝ 釘住的 main 快照（~/h2data/<sha>/data，唯讀）
  ② 母體 ＝ gate3（排除 -DR、-創）⇒ 面板的橫斷面百分位在 gate3 內算（新跑件一律 gate3）
量測日照原設計：每月第一個交易日，2015-01-01～2026-03-31。min_periods 常設斷言照原樣：不一致 > 0 ⇒ 停。"""
import os, sys, time
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                       # 把 D.DATA 指到快照
import pandas as pd
from backtest import researchp4 as RP4
from backtest import p4_features as P

OUT = "backtest/resultsAFC"

if __name__ == "__main__":
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    cal = H2.D.load_calendar()
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = H2.UG.gate3(stocks)
    U = H2.D.load_universe().merge(U[["stock_id"]], on="stock_id")     # 取 load_universe 的欄（first_seen／last_seen）
    positions = P.measurement_days(cal, "2015-01-01", "2026-03-31")
    print("[面板] 快照 {}｜gate3 {} 檔｜量測日 {} 個（{}～{}）".format(H2.SHA[:10], len(U), len(positions), cal[positions[0]].date(), cal[positions[-1]].date()), flush=True)
    panel, M = RP4.build_panel(cal, U, positions, procs=4, log=lambda s: print(s, flush=True))
    print("[面板] {:,} 列、eligible {:,}｜min_periods 不一致 {}｜{:.0f}s".format(len(panel), int(panel["eligible"].sum()), len(M), time.time() - t0), flush=True)
    if len(M):
        M.to_csv(os.path.join(OUT, "min_periods_mismatch.csv"), index=False)
        raise SystemExit("⛔ min_periods 常設斷言不成立 ⇒ 停")
    p = os.path.join(OUT, "panel.csv.gz")
    panel.to_csv(p, index=False)
    back = P.read_panel(p)
    assert len(back) == len(panel)
    print("✅ 面板寫出並重讀：", p)
