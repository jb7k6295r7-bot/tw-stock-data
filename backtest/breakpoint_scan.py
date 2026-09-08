"""全母體掃斷點，並與資料庫線的 `data/meta/par_change.csv`（24 筆／22 檔）對帳。

    python3 -m backtest.breakpoint_scan            # 印統計，寫 results/breakpoints_scan.csv

規則在 `data.breakpoints`（K線線 2026-09-09 三訂：①比值 ≤ 0.55／≥ 1.8、②連續缺 ≥ 5 個交易日，
且區間 (前一次有成交, 這一次有成交] 內無 data/adj/ 事件）。這支只讀不改。
對帳的期待：par_change.csv 的 24 筆**全部**要被規則抓到（漏掉任何一筆就是規則寫錯）；
規則多抓的是「不論成因都算斷點」的其他長停牌，另列出來看。
"""
from __future__ import annotations

import os
import sys

import pandas as pd

from . import data as D

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def main():
    cal = D.load_calendar()
    uni = D.load_universe()
    rows = []
    for sid, market in zip(uni["stock_id"], uni["market"]):
        st = D.load_stock(sid, market, cal)
        if st is None:
            continue
        for b in D.breakpoints(st.df, st.event_dates):
            rows.append({"stock_id": sid, "market": market, "date": cal[b["pos"]].strftime("%Y-%m-%d"),
                         "prev_date": cal[b["prev_pos"]].strftime("%Y-%m-%d"), "ratio": round(b["ratio"], 4),
                         "gap": b["gap"], "rule": b["rule"]})
    bp = pd.DataFrame(rows)
    os.makedirs(RESULTS, exist_ok=True)
    bp.to_csv(os.path.join(RESULTS, "breakpoints_scan.csv"), index=False)
    print(f"母體 {len(uni)} 檔，斷點 {len(bp)} 個、{bp['stock_id'].nunique()} 檔")
    print(bp["rule"].value_counts().to_string())
    print("gap 分布：", bp["gap"].describe()[["min", "50%", "max"]].to_dict())

    pc_path = os.path.join(D.DATA, "meta", "par_change.csv")
    if not os.path.exists(pc_path):
        print("（沒有 data/meta/par_change.csv，略過對帳）")
        return
    pc = pd.read_csv(pc_path, dtype={"stock_id": str})
    key = set(zip(bp["stock_id"], bp["date"]))
    hit = pc[[(s, d) in key for s, d in zip(pc["stock_id"], pc["event_date"])]]
    miss = pc[[(s, d) not in key for s, d in zip(pc["stock_id"], pc["event_date"])]]
    print(f"\n對帳 par_change.csv：{len(pc)} 筆／{pc['stock_id'].nunique()} 檔，規則抓到 {len(hit)}，漏 {len(miss)}")
    if len(miss):
        print("⛔ 漏掉：\n" + miss[["stock_id", "event_date", "ratio"]].to_string(index=False))
    pcs = set(zip(pc["stock_id"], pc["event_date"]))
    extra = bp[[(s, d) not in pcs for s, d in zip(bp["stock_id"], bp["date"])]]
    print(f"規則另外抓到（不在 par_change.csv）：{len(extra)} 個、{extra['stock_id'].nunique()} 檔；其中 price 規則 {int((extra['rule'] != 'gap').sum())} 個")
    with pd.option_context("display.width", 160, "display.max_rows", 200):
        print(extra[extra["rule"] != "gap"].to_string(index=False))
    return 1 if len(miss) else 0


if __name__ == "__main__":
    sys.exit(main())
