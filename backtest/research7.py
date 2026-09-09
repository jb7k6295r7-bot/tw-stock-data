"""研究七：六種型態 × 持有 20／60 日並列。判準在 backtest/PREREG6.md。

    python3 -m backtest.research7 [--procs 4]

進場集合取自 results/signals.csv.gz（研究二第三版），每檔重算 H20／H60 淨報酬與母體 20／60 日基準（同一組閘門）。
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import evaluate as E
from . import patterns as P
from . import run as R

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results7")
HOLDS = (20, 60)
SPLIT = R.SPLIT
SETS = ["P1_box_breakout", "P2_breakaway_gap", "P3_false_breakout", "P4_hammer", "P4_shooting_star",
        "P5_ma_cross_up", "P6_cup_handle", "P6_cup_handle_cap", "P6w_cup_handle_weekly"]
NAMES = {"P1_box_breakout": "P1 箱型突破", "P2_breakaway_gap": "P2 突破缺口", "P3_false_breakout": "P3 假突破（空）",
         "P4_hammer": "P4 錘子", "P4_shooting_star": "P4 射擊之星（空）", "P5_ma_cross_up": "P5 底穿上",
         "P6_cup_handle": "P6 杯柄（柄高）", "P6_cup_handle_cap": "P6 杯柄（杯蓋）", "P6w_cup_handle_weekly": "P6 杯柄（週線）"}

_G: dict = {}


def _init(cal, disp, lo, hi, split):
    _G.update(cal=cal, disp=disp, lo=lo, hi=hi, split=split)


def _hold(arr, entry, n_days):
    o, h, l, c, pc = arr["o"], arr["h"], arr["l"], arr["c"], arr["prev_c"]
    n = len(c)
    e = entry + n_days - 1
    if e >= n:
        return None
    j, k = e, 0
    while j < n and (np.isnan(c[j]) or E._limit_down_locked(o, h, l, c, pc, j)) and k < E.DEFER_MAX:
        j += 1; k += 1
    if j >= n or np.isnan(c[j]):
        seg = c[entry:e + 1]
        if np.isnan(seg).all():
            return None
        j = entry + int(np.flatnonzero(~np.isnan(seg))[-1])
    return j, c[j]


def _baseline(arr, gate, lo, hi, hold):
    o, c = arr["o"], arr["c"]
    n = len(c)
    idx = np.arange(max(lo, 0), min(hi, n - hold - 1) + 1)
    idx = idx[gate[idx]]
    if len(idx) == 0:
        return np.empty(0)
    r = c[idx + hold] / o[idx + 1] - 1
    return r[~np.isnan(r)]


def process_stock(job):
    sid, market, first_seen, last_seen, sigs = job
    cal, disp, lo, hi, split = _G["cal"], _G["disp"], _G["lo"], _G["hi"], _G["split"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    in_life = (cal >= first_seen) & (cal <= last_seen)
    f = P.Frame(df, st.event_dates)
    dmask = D.disposal_mask(sid, cal, disp)
    f.gate = f.gate & in_life & ~dmask
    jw = D.breakpoint_window(D.breakpoints(df, st.event_dates), len(cal), R.H_FORWARD, R.L_LOOKBACK)
    gate = f.gate & ~jw
    arr = {"o": f.o, "h": f.h, "l": f.l, "c": f.c, "prev_c": f.prev_c}
    base = {}
    for hd in HOLDS:
        b1 = _baseline(arr, gate, lo, split - 1, hd); b2 = _baseline(arr, gate, split, hi, hd)
        base[hd] = {"pre_sum": float(b1.sum()), "pre_n": int(len(b1)), "post_sum": float(b2.sum()), "post_n": int(len(b2))}
    rows = []
    for pat, sp, ep, direction in sigs:
        ep = int(ep)
        if ep >= len(f.c) or np.isnan(f.o[ep]):
            continue
        price = f.o[ep]
        row = {"pattern": pat, "stock_id": sid, "signal_pos": int(sp), "entry_pos": ep, "entry_date": cal[ep].strftime("%Y-%m-%d"),
               "direction": int(direction)}
        for hd in HOLDS:
            r = _hold(arr, ep, hd)
            row[f"ret_{hd}"] = np.nan if r is None else direction * (r[1] / price - 1) - E.COST
        rows.append(row)
    return {"base": base, "rows": rows}


def _nonoverlap(df, gap):
    cnt = 0
    for _, g in df.groupby("stock_id"):
        last = -10 ** 9
        for e in np.sort(g["entry_pos"].to_numpy()):
            if e - last >= gap:
                cnt += 1; last = e
    return cnt


def _segments(df, gap):
    cnt, last = 0, -10 ** 9
    for e in np.sort(df["entry_pos"].unique()):
        if e - last >= gap:
            cnt += 1; last = e
    return cnt


def _cluster_se(df, col):
    """按進場月分群的 cluster-robust SE（平均數）。"""
    x = df[col].to_numpy(float); m = x.mean()
    grp = df["entry_date"].str[:7]
    s = pd.Series(x - m).groupby(grp.to_numpy()).sum().to_numpy(float)
    return float(np.sqrt((s ** 2).sum()) / len(x))


def _pct(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.2f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe(); disp = D.load_disposal_intervals()
    lo = int(cal.searchsorted(pd.Timestamp(R.SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(R.SIG_END), side="right") - 1)
    split = int(cal.searchsorted(pd.Timestamp(SPLIT)))
    sig = pd.read_csv(os.path.join(HERE, "results", "signals.csv.gz"), dtype={"stock_id": str},
                      usecols=["pattern", "stock_id", "signal_pos", "entry_pos", "direction"])
    sig = sig[sig["pattern"].isin(SETS)]
    by = {s: list(zip(g["pattern"], g["signal_pos"], g["entry_pos"], g["direction"])) for s, g in sig.groupby("stock_id")}
    jobs = [(r.stock_id, r.market, r.first_seen, r.last_seen, by.get(r.stock_id, [])) for r in uni.itertuples()]
    print(f"母體 {len(jobs)} 檔，訊號 {len(sig):,} 筆", file=sys.stderr)
    res = []
    with Pool(a.procs, initializer=_init, initargs=(cal, disp, lo, hi, split)) as pool:
        for i, r in enumerate(pool.imap_unordered(process_stock, jobs, chunksize=8)):
            if r is not None:
                res.append(r)
            if (i + 1) % 400 == 0:
                print(f"  {i + 1}/{len(jobs)}  {time.time() - t0:.0f}s", file=sys.stderr)
    rows = pd.DataFrame([x for r in res for x in r["rows"]])
    base = {}
    for hd in HOLDS:
        pre_n = sum(r["base"][hd]["pre_n"] for r in res); post_n = sum(r["base"][hd]["post_n"] for r in res)
        pre_s = sum(r["base"][hd]["pre_sum"] for r in res); post_s = sum(r["base"][hd]["post_sum"] for r in res)
        base[hd] = {"pre": pre_s / pre_n - E.COST, "post": post_s / post_n - E.COST, "all": (pre_s + post_s) / (pre_n + post_n) - E.COST,
                    "pre_n": pre_n, "post_n": post_n}
    os.makedirs(RESULTS, exist_ok=True)
    rows.to_csv(os.path.join(RESULTS, "holds.csv.gz"), index=False)
    print(f"逐筆 {len(rows):,}，{time.time() - t0:.0f}s", file=sys.stderr)

    L = ["# 研究七：六種型態 × 持有 20／60 日並列——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG6.md`。逐筆 `holds.csv.gz`。",
         "**不設主表**：兩個持有期並列、各判各的。空方型態報酬已方向修正（放空賺錢為正）。",
         "**本表為等權；等風險版見研究六——判定一致，但差距約為本表的十分之一。**（K線線 12:00）",
         "60 日欄的固定持有是**基準／可執行性見研究六第五節**（沒有停損距離就算不出部位），不列為建議做法。", "",
         "## 母體基準（通過閘門的股票日，次日開盤進、第 N 日收盤出，扣成本）", "",
         "| 持有 | 前段 2016～2020 | 後段 2021～2026-07 | 全期 | 股票日數 |", "|---|---:|---:|---:|---:|"]
    for hd in HOLDS:
        b = base[hd]
        L.append(f"| {hd} 日 | {_pct(b['pre'])} | {_pct(b['post'])} | {_pct(b['all'])} | {b['pre_n'] + b['post_n']:,} |")
    L.append("")
    L.append("## 各型態")
    L.append("")
    L.append("| 型態 | 持有 | n | 非重疊 | 獨立區段 | 淨報酬 | 超額 | 超額 CI（非重疊 SE） | 超額 CI（月分群 SE） | 中位數 | 勝率 | 前段超額 | 後段超額 | 判定 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|")
    verdicts = {}
    for pat in SETS:
        d = rows[rows["pattern"] == pat]
        for hd in HOLDS:
            col = f"ret_{hd}"
            g = d[d[col].notna()]
            if not len(g):
                continue
            x = g[col].to_numpy(float); n = len(x)
            n_no = _nonoverlap(g, hd); seg = _segments(g, hd)
            sgn = 1 if g["direction"].iloc[0] > 0 else -1
            b = base[hd]
            bl = {k: (b[k] if sgn > 0 else -(b[k] + E.COST) - E.COST) for k in ("pre", "post", "all")}   # 空方基準 ＝ −毛 − 成本
            mean = x.mean(); ex_ = mean - bl["all"]
            se = x.std(ddof=1) / math.sqrt(max(1, n_no)) if n > 1 else float("nan")
            cse = _cluster_se(g, col) if n > 1 else float("nan")
            pre = g[g["entry_pos"] < split][col]; post = g[g["entry_pos"] >= split][col]
            ex_pre = pre.mean() - bl["pre"] if len(pre) else float("nan"); ex_post = post.mean() - bl["post"] if len(post) else float("nan")
            lo_, hi_ = ex_ - 1.96 * se, ex_ + 1.96 * se
            if lo_ > 0 and ex_pre > 0 and ex_post > 0:
                v = "通過"
            elif hi_ < 0:
                v = "反向顯著"
            else:
                v = "測不出效果"
            if n_no < 30:
                v = "樣本不足（不報）"
            elif n_no < 100:
                v += "（樣本不足）"
            verdicts[(pat, hd)] = (v, lo_, hi_)
            L.append(f"| {NAMES[pat]} | {hd} | {n:,} | {n_no:,} | {seg} | {_pct(mean)} | **{_pct(ex_)}** | {_pct(lo_)} ~ {_pct(hi_)} | {_pct(ex_ - 1.96 * cse)} ~ {_pct(ex_ + 1.96 * cse)} | {_pct(float(np.median(x)))} | {(x > 0).mean() * 100:.1f}% | {_pct(ex_pre)} | {_pct(ex_post)} | {v} |")
    L.append("")
    L.append("## 跨持有期揭露（PREREG6 第五節）")
    L.append("")
    for pat in SETS:
        v20, v60 = verdicts.get((pat, 20)), verdicts.get((pat, 60))
        if not v20 or not v60:
            continue
        opp = (v20[1] > 0 and v60[2] < 0) or (v20[2] < 0 and v60[1] > 0)
        note = "⚠ 方向相反且都顯著——此型態效果對持有期極度敏感（視為樣本不足的訊號）" if opp else ("兩個持有期判定相同" if v20[0].split("（")[0] == v60[0].split("（")[0] else "兩個持有期判定不同，兩個都寫、不挑")
        L.append(f"- {NAMES[pat]}：20 日「{v20[0]}」、60 日「{v60[0]}」→ {note}")
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"寫入 {RESULTS}/summary.md", file=sys.stderr)


if __name__ == "__main__":
    main()
