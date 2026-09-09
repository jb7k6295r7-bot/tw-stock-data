"""研究二：型態全市場回測 執行器。

    python3 -m backtest.run                 # 全市場
    python3 -m backtest.run --stocks 2330 2454 --print   # 幾檔，印訊號
    python3 -m backtest.run --limit 200     # 前 200 檔（測速）

輸出到 backtest/results/：signals.csv（逐筆）、baseline.json、summary.md、variants.csv。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import evaluate as E
from . import patterns as P

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

SIG_START, SIG_END = "2016-01-04", "2026-07-31"
SPLIT = "2021-01-04"

# 斷點視窗（PREREG 更正三）：H ＝ 本研究最長前瞻天數、L ＝ 最長回看天數，從參數算、不寫死。
#   H：進場在訊號次日（+1）、ATR 追蹤與目標價最長 120 日、跌停順延最多 10 日。
#   L：杯柄 325＋120＋30＋5 ＝ 480（見 patterns.max_lookback）。
H_FORWARD = 1 + max(E.HOLD, E.ATR_CAP, E.TARGET_WINDOW) + E.DEFER_MAX
L_LOOKBACK = P.max_lookback()

# ［本研究補］參數的敏感度：(參數, 替代值, 受影響的偵測器)
VARIANTS = [
    ("box_range_max", 0.15, ["P1", "P2", "P3"]), ("box_range_max", 0.25, ["P1", "P2", "P3"]),
    ("gap_min", 0.005, ["P2", "P3"]), ("gap_min", 0.02, ["P2", "P3"]),
    ("body_min_frac", 0.05, ["P4"]), ("body_min_frac", 0.20, ["P4"]),
    ("trend_pct", 0.03, ["P4"]), ("trend_pct", 0.08, ["P4"]),
    ("ma_conv_max", 0.02, ["P5"]), ("ma_conv_max", 0.05, ["P5"]),
    ("ma_vol_x", 1.0, ["P5"]), ("ma_vol_x", 2.0, ["P5"]),
    ("u_frac", 0.30, ["P6"]), ("u_frac", 0.45, ["P6"]),
    ("half_min", 10, ["P6"]), ("half_min", 20, ["P6"]),
    ("liq_min_shares", 200_000, ["P1", "P2", "P3", "P4", "P5", "P6"]),
]

_G: dict = {}


def _init(cal, bench_arr, disp, attn, lo, hi, split_pos):
    _G.update(cal=cal, bench=bench_arr, disp=disp, attn=attn, lo=lo, hi=hi, split=split_pos)


def _arrays(df: pd.DataFrame, f: P.Frame) -> dict:
    return {"o": f.o, "h": f.h, "l": f.l, "c": f.c, "prev_c": f.prev_c, "atr14": f.atr14}


def weekly_frame(df: pd.DataFrame, cal: pd.DatetimeIndex):
    w = df.resample("W-FRI").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                 close=("close", "last"), volume=("volume", "sum"), traded=("traded", "any"))
    w.loc[~w["traded"], ["open", "high", "low", "close"]] = np.nan
    w.loc[~w["traded"], "volume"] = np.nan
    # 每週最後一個交易日在日曆上的位置
    last_day = df["close"].notna().groupby(pd.Grouper(freq="W-FRI")).apply(lambda s: s[s].index.max() if s.any() else pd.NaT)
    last_pos = np.array([cal.searchsorted(d) if pd.notna(d) else -1 for d in last_day.reindex(w.index)])
    return w, last_pos


def process_stock(args):
    sid, market, first_seen, last_seen = args
    cal, bench, disp, attn = _G["cal"], _G["bench"], _G["disp"], _G["attn"]
    lo, hi = _G["lo"], _G["hi"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    # 母體區間：first_seen ~ last_seen 之外一律不進
    in_life = (cal >= first_seen) & (cal <= last_seen)
    f = P.Frame(df, st.event_dates)
    dmask = D.disposal_mask(sid, cal, disp)
    f.gate = f.gate & in_life & ~dmask
    arr = _arrays(df, f)
    attn_set = attn.get(sid, set())
    # 斷點（面額變更等還原因子接不起來的地方）：訊號日 s ∈ [T−H, T+L−1] 的訊號整筆剔除（PREREG 更正二、更正三）
    bps = D.breakpoints(df, st.event_dates)
    jump_rows = [{"stock_id": sid, "market": market, "date": cal[b["pos"]].strftime("%Y-%m-%d"),
                  "prev_date": cal[b["prev_pos"]].strftime("%Y-%m-%d"), "ratio": b["ratio"], "missing_trading_days": b["gap"], "rule": b["rule"]}
                 for b in bps if D.applies(b)]   # 清單只留判讀層有套窗的（資料層全表見 breakpoint_scan 的 holes_scan.csv）
    ncal = len(cal)
    jump_window = D.breakpoint_window(bps, ncal, H_FORWARD, L_LOOKBACK)   # True ＝ 以該日為訊號日的訊號要剔除
    excluded = {"jump": 0}

    def run_detectors(frame, keys, tag=None):
        sigs = []
        for k in keys:
            if k == "P6":
                sigs += P.cup_handle(frame, buy="handle")
                sigs += P.cup_handle(frame, buy="cap")
            else:
                sigs += P.DETECTORS[k](frame)
        out = []
        for s in sigs:
            if not (lo <= s["signal_pos"] <= hi):
                continue
            if jump_window[s["signal_pos"]]:
                excluded["jump"] += 1
                continue
            r = E.evaluate_signal(arr, bench, s)
            if r is None:
                continue
            s.update(r)
            s["stock_id"] = sid; s["market"] = market
            s["signal_date"] = cal[s["signal_pos"]].strftime("%Y-%m-%d")
            s["entry_date"] = cal[s["entry_pos"]].strftime("%Y-%m-%d")
            s["attention"] = cal[s["signal_pos"]] in attn_set
            if tag:
                s["variant"] = tag
            out.append(s)
        return out

    signals = run_detectors(f, ["P1", "P2", "P3", "P4", "P5", "P6"])

    # 週線杯柄（對照）
    try:
        w, last_pos = weekly_frame(df, cal)
        fw = P.Frame(w, set())
        fw.gate = fw.gate & (fw.vol_ma20 >= P.PARAMS["liq_min_shares"] * 5)
        for s in P.cup_handle(fw, buy="handle", unit=5):
            wp = s["signal_pos"]
            sp = last_pos[wp]
            if sp < 0 or not (lo <= sp <= hi):
                continue
            ep = sp + 1
            if ep >= len(cal) or dmask[sp] or not in_life[sp] or jump_window[sp]:
                continue
            s["pattern"] = "P6w_cup_handle_weekly"
            s["signal_pos"], s["entry_pos"] = int(sp), int(ep)
            r = E.evaluate_signal(arr, bench, s)
            if r is None:
                continue
            s.update(r)
            s["stock_id"] = sid; s["market"] = market
            s["signal_date"] = cal[sp].strftime("%Y-%m-%d"); s["entry_date"] = cal[ep].strftime("%Y-%m-%d")
            s["attention"] = cal[sp] in attn_set
            signals.append(s)
    except Exception as ex:  # 週線失敗不影響主表，但要留痕
        signals.append({"pattern": "ERR_weekly", "stock_id": sid, "err": repr(ex)})

    # 敏感度
    variants = []
    for name, val, keys in VARIANTS:
        p2 = dict(P.PARAMS); p2[name] = val
        f2 = P.Frame(df, st.event_dates, p2)
        f2.gate = f2.gate & in_life & ~dmask
        for s in run_detectors(f2, keys, tag=f"{name}={val}"):
            variants.append({k: s.get(k) for k in ("variant", "pattern", "stock_id", "signal_pos", "entry_pos", "signal_date", "ret_hold_signed")})

    # 母體基準（毛報酬，未扣成本），分子期間；跳價視窗內的股票日也排除
    split = _G["split"]
    bgate = f.gate & ~jump_window
    c = pd.Series(f.c)
    trend = (c.shift(1) / c.shift(1 + P.PARAMS["trend_days"]) - 1).to_numpy(float)
    with np.errstate(invalid="ignore"):
        down5 = trend <= -P.PARAMS["trend_pct"]
        up5 = trend >= P.PARAMS["trend_pct"]
    base = {}
    for key, cond in (("", None), ("down5_", down5), ("up5_", up5)):
        b1 = E.baseline_returns(arr, bgate, lo, split - 1, cond) + E.COST
        b2 = E.baseline_returns(arr, bgate, split, hi, cond) + E.COST
        base.update({f"{key}pre_sum": float(b1.sum()), f"{key}pre_n": int(len(b1)), f"{key}pre_sq": float((b1 ** 2).sum()),
                     f"{key}post_sum": float(b2.sum()), f"{key}post_n": int(len(b2)), f"{key}post_sq": float((b2 ** 2).sum())})
    # 240 日報酬（給杯柄 RS 替代值用）
    r240 = (c / c.shift(240) - 1).to_numpy(np.float32)
    return {"sid": sid, "signals": signals, "variants": variants, "base": base, "r240": r240,
            "jumps": jump_rows, "excluded": excluded}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stocks", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--out", default=RESULTS)
    a = ap.parse_args()

    t0 = time.time()
    cal = D.load_calendar()
    uni = D.load_universe()
    if a.stocks:
        uni = uni[uni["stock_id"].isin(a.stocks)]
    if a.limit:
        uni = uni.head(a.limit)
    bench_df = D.load_benchmark(cal)
    bench = {"o": bench_df["open"].to_numpy(float), "c": bench_df["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    attn = D.load_attention_dates()
    lo = int(cal.searchsorted(pd.Timestamp(SIG_START)))
    hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)
    split = int(cal.searchsorted(pd.Timestamp(SPLIT)))
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    print(f"母體 {len(jobs)} 檔，訊號區間 {cal[lo].date()} ~ {cal[hi].date()}，分割 {cal[split].date()}", file=sys.stderr)

    results = []
    if a.procs <= 1 or len(jobs) <= 4:
        _init(cal, bench, disp, attn, lo, hi, split)
        for j in jobs:
            results.append(process_stock(j))
    else:
        with Pool(a.procs, initializer=_init, initargs=(cal, bench, disp, attn, lo, hi, split)) as pool:
            for i, r in enumerate(pool.imap_unordered(process_stock, jobs, chunksize=8)):
                results.append(r)
                if (i + 1) % 200 == 0:
                    print(f"  {i + 1}/{len(jobs)}  {time.time() - t0:.0f}s", file=sys.stderr)
    results = [r for r in results if r is not None]

    sigs = pd.DataFrame([s for r in results for s in r["signals"]])
    var = pd.DataFrame([s for r in results for s in r["variants"]])
    base = {}
    for key in ("", "down5_", "up5_"):
        for per in ("pre", "post"):
            n = sum(r["base"][f"{key}{per}_n"] for r in results); sm = sum(r["base"][f"{key}{per}_sum"] for r in results)
            sq = sum(r["base"][f"{key}{per}_sq"] for r in results)
            mg = sm / n if n else float("nan")
            base[f"{key}{per}"] = {"n": n, "sum": sm, "sq": sq, "mean_gross": mg,
                                   "sd": float(np.sqrt(max(0.0, sq / n - mg ** 2))) if n else float("nan")}
        ntot = base[f"{key}pre"]["n"] + base[f"{key}post"]["n"]
        base[f"{key}all"] = {"n": ntot, "mean_gross": (base[f"{key}pre"]["sum"] + base[f"{key}post"]["sum"]) / ntot if ntot else float("nan")}
    base["excluded_jump_signals"] = int(sum(r["excluded"]["jump"] for r in results))
    jumps = pd.DataFrame([j for r in results for j in r["jumps"]])

    # 杯柄 RS 替代值：訊號日前 240 日報酬在母體的百分位
    if len(sigs) and "signal_pos" in sigs:
        R = np.vstack([r["r240"] for r in results])  # stocks × days
        sid_idx = {r["sid"]: i for i, r in enumerate(results)}
        pct = np.full(len(sigs), np.nan)
        m = sigs["pattern"].astype(str).str.startswith("P6")
        for i in np.flatnonzero(m.to_numpy()):
            row = sigs.iloc[i]
            col = R[:, int(row["signal_pos"])]
            col = col[~np.isnan(col)]
            x = R[sid_idx[row["stock_id"]], int(row["signal_pos"])]
            if len(col) and not np.isnan(x):
                pct[i] = (col < x).mean() * 100
        sigs["rs_pct_240"] = pct

    os.makedirs(a.out, exist_ok=True)
    sigs.to_csv(os.path.join(a.out, "signals.csv"), index=False)
    var.to_csv(os.path.join(a.out, "variants.csv"), index=False)
    jumps.to_csv(os.path.join(a.out, "breakpoints.csv"), index=False)
    base["breakpoints"] = {"n": int(len(jumps)), "stocks": int(jumps["stock_id"].nunique()) if len(jumps) else 0,
                           "by_rule": {k: int(v) for k, v in jumps["rule"].value_counts().items()} if len(jumps) else {},
                           "H": H_FORWARD, "L": L_LOOKBACK}
    with open(os.path.join(a.out, "baseline.json"), "w") as fh:
        json.dump(base, fh, indent=1, ensure_ascii=False)
    print(f"訊號 {len(sigs)} 筆，敏感度 {len(var)} 筆，{time.time() - t0:.0f}s", file=sys.stderr)
    if a.print and len(sigs):
        cols = [c for c in ("pattern", "stock_id", "signal_date", "entry_date", "entry_price", "ret_hold_net", "ret_atr_net", "vol_x", "box_top", "cup_len", "handle_len", "depth") if c in sigs]
        with pd.option_context("display.width", 200, "display.max_rows", 500):
            print(sigs[cols].sort_values(["pattern", "signal_date"]).to_string())
    from .report import write_report
    write_report(a.out, sigs, var, base, cal, split)


if __name__ == "__main__":
    main()
