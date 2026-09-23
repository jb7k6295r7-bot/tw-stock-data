"""把【P5 以外】的型態訊號在 ~/tw-p17 這棵樹上掃一次 —— T3 重算用。

⭐⭐ 為什麼一定要重掃、⛔ 不能直接用已交件的 signals.csv.gz：
   已交件那份是在 ~/tw-stock-data 產生的，而 P5 的新尺是在 ~/tw-p17 上跑的
   ⇒ ⛔ 兩棵樹的 data/ 是【不同快照】（日曆 2,852 vs 2,855、個股檔 sha 不同）
   ⇒ 把兩邊拼起來算 T3 ＝ 分子分母來自不同快照 ⇒ ⛔ 那個比例沒有意義。
   ⇒ ⭐ 所以本支在【同一棵樹】上重掃其餘八個型態，與 p5_rescan 的 k=0／k=3 拼成
     兩個【各自內部一致】的候選池。

⛔ 本支不動任何偵測器的門檻：P5 以外的八個一個字都沒改（型態線 2053 §五 逐字確認）。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D          # noqa: E402
from backtest import patterns as P      # noqa: E402
from backtest import run as RUN         # noqa: E402

OUT = os.path.expanduser("~/tw-p17/backtest/resultsp5win")


def _initw(cal, bench, disp, attn, lo, hi, split):
    P.DETECTORS["P5"] = lambda f, *_a, **_kw: []      # ⭐ 只關掉 P5，其餘照跑
    RUN.P.DETECTORS = P.DETECTORS
    RUN._init(cal, bench, disp, attn, lo, hi, split)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    cal = D.load_calendar()
    uni = D.load_universe()
    bench_df = D.load_benchmark(cal)
    bench = {"o": bench_df["open"].to_numpy(float), "c": bench_df["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    attn = D.load_attention_dates()
    lo = int(cal.searchsorted(pd.Timestamp(RUN.SIG_START)))
    hi = int(cal.searchsorted(pd.Timestamp(RUN.SIG_END), side="right") - 1)
    split = int(cal.searchsorted(pd.Timestamp(RUN.SPLIT)))
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    print("母體 {} 檔，訊號區間 {} ~ {}".format(len(jobs), cal[lo].date(), cal[hi].date()), flush=True)

    t0 = time.time()
    with Pool(a.procs, initializer=_initw,
              initargs=(cal, bench, disp, attn, lo, hi, split)) as pool:
        res = []
        for i, r in enumerate(pool.imap_unordered(RUN.process_stock, jobs, chunksize=8)):
            if r is not None:
                res.append(r)
            if (i + 1) % 300 == 0:
                print("  {}/{}  {:.0f}s".format(i + 1, len(jobs), time.time() - t0), flush=True)
    rows = [s for r in res for s in r["signals"]]
    d = pd.DataFrame(rows)
    assert (d["pattern"] != "P5_ma_cross_up").all(), "⛔ P5 沒關乾淨"
    keep = ["pattern", "stock_id", "signal_pos", "entry_pos", "signal_date"]
    d = d[keep].sort_values(["stock_id", "signal_pos"]).reset_index(drop=True)
    d.to_csv(os.path.join(OUT, "other8.csv.gz"), index=False)
    print()
    print("[完成] 其餘八型 {:,} 筆／{:,} 檔（{:.0f}s）"
          .format(len(d), d["stock_id"].nunique(), time.time() - t0))
    print(d["pattern"].value_counts().to_string())


if __name__ == "__main__":
    main()
