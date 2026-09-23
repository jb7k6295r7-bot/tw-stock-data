"""T1 第①步：算【母體】—— 觸發率的分母（〈九十二〉：觸發率一定要連同母體一起報）。

⛔ 閘門、母體區間、訊號視窗【全部沿用 backtest/run.py 那一份】，不另寫第二套（四點五）：
     gate = Frame.gate & in_life & ~disposal_mask，視窗 [SIG_START, SIG_END]
⭐ 市值口徑【逐字照 K線分析線 20260920-1915 §六】：
     市值 ＝ 量測日【原始收盤】× 當日 shares      ⛔ 不可用別的定義
     級距 ＝ 當月【全市場】市值前 50
   量測日取【該月最後一個有成交日】。

輸出（寫到 scratchpad，⛔ 不碰 repo）：exposure.csv
"""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-stock-data"))
from backtest import data as D          # noqa: E402
from backtest import patterns as P      # noqa: E402
from backtest.run import SIG_START, SIG_END  # noqa: E402

OUT = "/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/57a7a54c-a515-48e2-87ab-d32197791f42/scratchpad/t1"
RAW = os.path.expanduser("~/tw-stock-data/data/stocks")

_G: dict = {}


def _init(cal, disp, lo, hi):
    _G.update(cal=cal, disp=disp, lo=lo, hi=hi)


def one(args):
    sid, market, first_seen, last_seen = args
    cal, disp, lo, hi = _G["cal"], _G["disp"], _G["lo"], _G["hi"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    f = P.Frame(st.df, st.event_dates)
    in_life = (cal >= first_seen) & (cal <= last_seen)
    gate = f.gate & in_life & ~D.disposal_mask(sid, cal, disp)
    win = np.zeros(len(cal), bool)
    win[lo:hi + 1] = True
    gate = gate & win
    if not gate.any():
        return None

    ym_all = pd.Series(cal).dt.strftime("%Y-%m").to_numpy()
    g = pd.DataFrame({"ym": ym_all[gate]}).groupby("ym").size().rename("gate_days")

    # ⭐ 市值：原始收盤 × 當日 shares，取該月最後一個有成交日
    p = os.path.join(RAW, f"{sid}.csv")
    if not os.path.exists(p):
        cap = pd.Series(dtype=float, name="mktcap")
    else:
        r = pd.read_csv(p, usecols=lambda c: c in ("date", "close", "shares", "volume"),
                        dtype={"close": float, "shares": float, "volume": float})
        r = r.dropna(subset=["close", "shares"])
        r = r[(r["volume"].fillna(0) > 0)]
        if len(r):
            r["ym"] = r["date"].str.slice(0, 7)
            r = r.sort_values("date").groupby("ym").tail(1)
            r["mktcap"] = r["close"] * r["shares"]
            cap = r.set_index("ym")["mktcap"]
        else:
            cap = pd.Series(dtype=float, name="mktcap")

    out = pd.DataFrame(g).join(cap.rename("mktcap"), how="left").reset_index()
    out.insert(0, "stock_id", sid)
    out.insert(1, "market", market)
    return out


def main():
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    t0 = time.time()
    cal = D.load_calendar()
    uni = D.load_universe()
    disp = D.load_disposal_intervals()
    lo = int(cal.searchsorted(pd.Timestamp(SIG_START)))
    hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    print(f"母體 {len(jobs)} 檔，訊號區間 {cal[lo].date()} ~ {cal[hi].date()}，procs={procs}", file=sys.stderr)

    res = []
    with Pool(procs, initializer=_init, initargs=(cal, disp, lo, hi)) as pool:
        for i, r in enumerate(pool.imap_unordered(one, jobs, chunksize=8)):
            if r is not None:
                res.append(r)
            if (i + 1) % 400 == 0:
                print(f"  {i + 1}/{len(jobs)}  {time.time() - t0:.0f}s", file=sys.stderr)

    d = pd.concat(res, ignore_index=True)
    os.makedirs(OUT, exist_ok=True)
    d.to_csv(f"{OUT}/exposure.csv", index=False)
    print(f"\n✅ exposure.csv：{len(d):,} 列（檔-月）　{d['stock_id'].nunique():,} 檔　"
          f"{d['ym'].nunique()} 個月　{time.time() - t0:.0f}s")
    print(f"   gate 日合計 {int(d['gate_days'].sum()):,} 檔-交易日")
    print(f"   ⚠ 市值缺值：{int(d['mktcap'].isna().sum()):,} 檔-月"
          f"（{d['mktcap'].isna().mean():.1%}）")


if __name__ == "__main__":
    main()
