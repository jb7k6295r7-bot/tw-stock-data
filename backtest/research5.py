"""研究五：出場規則比較。判準在 backtest/PREREG4.md。

    python3 -m backtest.research5 [--procs 4] [--report-only]

進場集合固定取自既有結果（E1 G1 月營收創高、E2 P1 箱型突破、E3 P4 錘子），
每一筆進場套 11 種出場規則，輸出 results5/exits.csv.gz 與 summary.md。
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

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results5")
CAP = 60
SPLIT = "2021-01-04"
GAP_NONOVERLAP = 60

# (代號, 類型, 參數)；PREREG4 第二節，事前列好，不掃格
RULES = [("H20", "hold", 20), ("H60", "hold", 60),
         ("S5", "stop", 0.05), ("S8", "stop", 0.08), ("S10", "stop", 0.10), ("S15", "stop", 0.15),
         ("T10", "trail", 0.10), ("T20", "trail", 0.20),
         ("A1.5", "atr", 1.5), ("A2", "atr", 2.0), ("A3", "atr", 3.0)]
SETS = {"E1": "G1 月營收創 24 月新高", "E2": "P1 箱型突破", "E3": "P4 錘子"}

_G: dict = {}


def _init(cal):
    _G["cal"] = cal


def _hold(arr, entry, n_days):
    """固定持有 n_days 日；出場日鎖跌停或缺收盤則順延（最多 DEFER_MAX），與 evaluate.hold_exit 同邏輯。"""
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
    return j, c[j], False


def _stop(arr, entry, kind, p, cap=CAP):
    """停損類：收盤跌破停損線 → 次日開盤出場；到期走 _hold(cap)。
    stop：線 ＝ 進場價 × (1−p)，不動。trail：線 ＝ 進場後最高收盤 × (1−p)，只升不降。atr：線 ＝ 最高收盤 − p×ATR14，只升不降。"""
    o, c, atr = arr["o"], arr["c"], arr["atr14"]
    n = len(c)
    ep = o[entry]
    if kind == "atr" and np.isnan(atr[entry]):
        return None                      # 算不出 ATR：這條規則不適用（PREREG4 第四節另報）
    hi = -np.inf
    stop = ep * (1 - p) if kind == "stop" else -np.inf
    last = min(n - 1, entry + cap - 1)
    for i in range(entry, last + 1):
        ci = c[i]
        if np.isnan(ci):
            continue
        if ci > hi:
            hi = ci
        if kind == "trail":
            stop = max(stop, hi * (1 - p))
        elif kind == "atr":
            a = atr[i]
            if not np.isnan(a):
                stop = max(stop, hi - p * a)
        if ci < stop:
            j = E._next_tradable_open(o, i + 1, n)
            if j is None:
                return i, ci, True
            return j, o[j], True
    return _hold(arr, entry, cap)


def process_stock(job):
    sid, market, sigs = job
    cal = _G["cal"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return []
    f = P.Frame(st.df, st.event_dates)
    arr = {"o": f.o, "h": f.h, "l": f.l, "c": f.c, "prev_c": f.prev_c, "atr14": f.atr14}
    n = len(f.c)
    out = []
    for set_code, sp, ep in sigs:
        if ep >= n or np.isnan(arr["o"][ep]):
            continue
        price = arr["o"][ep]
        row = {"set": set_code, "stock_id": sid, "market": market, "signal_pos": int(sp), "entry_pos": int(ep),
               "entry_date": cal[ep].strftime("%Y-%m-%d"), "atr_nan": bool(np.isnan(arr["atr14"][ep])),
               # 給研究六（等風險版）用：進場日 ATR 占進場價比例、20／60 日內最大不利偏移（收盤基準）
               "atr_pct": float(arr["atr14"][ep] / price) if not np.isnan(arr["atr14"][ep]) else np.nan}
        for hh in (20, 60):
            seg = arr["c"][ep:ep + hh]
            row[f"mae{hh}"] = float(np.nanmin(seg) / price - 1) if len(seg) and not np.isnan(seg).all() else np.nan
        for code, kind, p in RULES:
            r = _hold(arr, ep, p) if kind == "hold" else _stop(arr, ep, kind, p)
            if r is None:
                row[f"ret_{code}"] = np.nan; row[f"days_{code}"] = np.nan; row[f"trig_{code}"] = np.nan
            else:
                row[f"ret_{code}"] = r[1] / price - 1 - E.COST
                row[f"days_{code}"] = r[0] - ep + 1
                row[f"trig_{code}"] = float(r[2])
        out.append(row)
    return out


def load_entries() -> pd.DataFrame:
    panel = pd.read_csv(os.path.join(HERE, "results3", "panel.csv.gz"), dtype={"stock_id": str})
    e1 = panel[panel["rev_hi24"] == True][["stock_id", "market", "signal_pos", "entry_pos"]].copy()  # noqa: E712
    e1["set"] = "E1"
    sig = pd.read_csv(os.path.join(HERE, "results", "signals.csv.gz"), dtype={"stock_id": str},
                      usecols=["pattern", "stock_id", "market", "signal_pos", "entry_pos"])
    e2 = sig[sig["pattern"] == "P1_box_breakout"].drop(columns="pattern").copy(); e2["set"] = "E2"
    e3 = sig[sig["pattern"] == "P4_hammer"].drop(columns="pattern").copy(); e3["set"] = "E3"
    ent = pd.concat([e1, e2, e3], ignore_index=True)
    ent["signal_pos"] = ent["signal_pos"].astype(int); ent["entry_pos"] = ent["entry_pos"].astype(int)
    return ent


# ── 統計 ──
def _nonoverlap(df: pd.DataFrame, gap: int = GAP_NONOVERLAP) -> int:
    cnt = 0
    for _, g in df.groupby("stock_id"):
        last = -10 ** 9
        for e in np.sort(g["entry_pos"].to_numpy()):
            if e - last >= gap:
                cnt += 1; last = e
    return cnt


def _stats(df: pd.DataFrame, code: str) -> dict | None:
    m = df[f"ret_{code}"].notna()
    if m.sum() == 0:
        return None
    d = df[m]
    x = d[f"ret_{code}"].to_numpy(float)
    n = len(x); n_no = _nonoverlap(d)
    mean = x.mean(); se = x.std(ddof=1) / math.sqrt(max(1, n_no)) if n > 1 else float("nan")
    days = d[f"days_{code}"].to_numpy(float)
    trig = d[f"trig_{code}"].to_numpy(float)
    return {"n": n, "n_no": n_no, "mean": mean, "lo": mean - 1.96 * se, "hi": mean + 1.96 * se,
            "median": float(np.median(x)), "win": float((x > 0).mean()), "p5": float(np.percentile(x, 5)),
            "worst": float(x.min()), "days": float(np.nanmean(days)), "trig": float(np.nanmean(trig)),
            "per_day": mean / float(np.nanmean(days))}


def _paired(df: pd.DataFrame, code: str, base: str = "H60") -> dict | None:
    m = df[f"ret_{code}"].notna() & df[f"ret_{base}"].notna()
    if m.sum() < 2:
        return None
    d = df[m]
    x = (d[f"ret_{code}"] - d[f"ret_{base}"]).to_numpy(float)
    n_no = _nonoverlap(d)
    mean = x.mean(); se = x.std(ddof=1) / math.sqrt(max(1, n_no))
    return {"n": len(x), "mean": mean, "lo": mean - 1.96 * se, "hi": mean + 1.96 * se}


def _verdict(pair_all, pair_pre, pair_post, st_rule, st_base) -> str:
    if pair_all is None:
        return "—"
    same_sign = (pair_pre is not None and pair_post is not None and np.sign(pair_pre["mean"]) == np.sign(pair_post["mean"]))
    if pair_all["lo"] > 0 and same_sign:
        return "期望值較好"
    if pair_all["hi"] < 0:
        return "較差"
    if st_rule is not None and st_base is not None and (st_rule["p5"] - st_base["p5"]) >= 0.03:
        return "只是保險"
    return "分不出來"


def _pct(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.2f}%"


def write_report(ex: pd.DataFrame, cal: pd.DatetimeIndex, split_pos: int):
    L = ["# 研究五：出場規則比較——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準見 `backtest/PREREG4.md`，逐筆見 `exits.csv.gz`。",
         f"時間上限 {CAP} 個交易日；成本 {E.COST * 100:.3f}%；非重疊 n 以同檔進場相隔 ≥ {GAP_NONOVERLAP} 日計；配對差 ＝ 同一筆進場「該規則 − H60」。", ""]
    for set_code, set_name in SETS.items():
        d = ex[ex["set"] == set_code]
        if not len(d):
            continue
        pre, post = d[d["entry_pos"] < split_pos], d[d["entry_pos"] >= split_pos]
        L.append(f"## {set_code} {set_name}（n {len(d):,}，ATR 算不出 {int(d['atr_nan'].sum()):,} 筆）"); L.append("")
        L.append("| 規則 | n | 非重疊 | 平均淨報酬 | 95% CI | 中位數 | 勝率 | 第 5 百分位 | 最差 | 平均持有日 | 觸發率 | 每持有日 | 配對差 vs H60 | 配對差 CI | 前段差 | 後段差 | 判定 |")
        L.append("|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|")
        base = _stats(d, "H60")
        for code, kind, p in RULES:
            s = _stats(d, code)
            if s is None:
                continue
            pa, pp, po = _paired(d, code), _paired(pre, code), _paired(post, code)
            v = "基準" if code == "H60" else _verdict(pa, pp, po, s, base)
            if s["n_no"] < 30:            # PREREG4 更正一：非重疊 n < 30 只報筆數
                v = "樣本不足（不報）"
            elif s["n_no"] < 100:
                v += "（樣本不足）"
            L.append(f"| {code} | {s['n']:,} | {s['n_no']:,} | **{_pct(s['mean'])}** | {_pct(s['lo'])} ~ {_pct(s['hi'])} | {_pct(s['median'])} | {s['win'] * 100:.1f}% | {_pct(s['p5'])} | {_pct(s['worst'])} | {s['days']:.1f} | {s['trig'] * 100:.0f}% | {s['per_day'] * 10000:+.1f} bp | "
                     f"{_pct(pa['mean']) if pa else '—'} | {(_pct(pa['lo']) + ' ~ ' + _pct(pa['hi'])) if pa else '—'} | {_pct(pp['mean']) if pp else '—'} | {_pct(po['mean']) if po else '—'} | {v} |")
        L.append("")
    # 第四節：算不出 ATR 那一群
    d = ex[(ex["set"] == "E1") & ex["atr_nan"]]
    L.append(f"## 第四節：E1 裡進場日 ATR14 算不出來的訊號（n {len(d):,}）"); L.append("")
    if len(d):
        L.append("| 規則 | n | 平均淨報酬 | 95% CI | 中位數 | 勝率 | 第 5 百分位 | 最差 |"); L.append("|---|---:|---:|---|---:|---:|---:|---:|")
        for code in ("H20", "H60", "S8", "S10"):
            s = _stats(d, code)
            if s:
                L.append(f"| {code} | {s['n']:,} | **{_pct(s['mean'])}** | {_pct(s['lo'])} ~ {_pct(s['hi'])} | {_pct(s['median'])} | {s['win'] * 100:.1f}% | {_pct(s['p5'])} | {_pct(s['worst'])} |")
        L.append("")
        L.append("n < 100 時只報數字、不做判定（PREREG4 第四節）。" if len(d) < 100 else "")
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    cal = D.load_calendar()
    split_pos = int(cal.searchsorted(pd.Timestamp(SPLIT)))
    path = os.path.join(RESULTS, "exits.csv.gz")
    if a.report_only:
        ex = pd.read_csv(path, dtype={"stock_id": str})
    else:
        ent = load_entries()
        print(f"進場：{ent.groupby('set').size().to_dict()}", file=sys.stderr)
        jobs = [(sid, g["market"].iloc[0], list(zip(g["set"], g["signal_pos"], g["entry_pos"])))
                for sid, g in ent.groupby("stock_id")]
        rows = []
        with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
            for i, r in enumerate(pool.imap_unordered(process_stock, jobs, chunksize=8)):
                rows += r
                if (i + 1) % 300 == 0:
                    print(f"  {i + 1}/{len(jobs)}  {time.time() - t0:.0f}s", file=sys.stderr)
        ex = pd.DataFrame(rows)
        os.makedirs(RESULTS, exist_ok=True)
        ex.to_csv(path, index=False)
    print(f"逐筆 {len(ex):,} 列，{time.time() - t0:.0f}s", file=sys.stderr)
    write_report(ex, cal, split_pos)


if __name__ == "__main__":
    main()
