"""研究八：組合層模擬——同一筆資金、固定 N 個等權槽、訊號到了就補位、補不到就空手。判準 backtest/PREREG7.md。

    python3 -m backtest.research8 [--n 5] [--reps 200]

逐筆的進場日／出場日／出場價取自研究五第二版 results5/exits.csv.gz（含 days_<rule>、ret_<rule>），不重算。
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

from . import data as D
from . import research5 as R5

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results8")
RULES = ["H20", "H60", "S10", "S15", "T20", "A2", "A3"]
SETS = {"E1": "G1 月營收創 24 月新高", "E3": "P4 錘子", "E2": "P1 箱型突破"}
SPLIT = R5.SPLIT
END = "2026-08-31"


def simulate(sig: pd.DataFrame, rule: str, n_slots: int, rng: np.random.Generator, ncal: int, split_pos: int):
    """sig：該集合逐筆，含 entry_pos、days_<rule>、ret_<rule>（淨報酬）。回傳 (每日權益, 統計)。
    進場在 entry_pos 當日開盤（訊號日 ＝ entry_pos − 1），出場在 entry_pos + days − 1 收盤（或次日開盤，已含在 ret 內）。"""
    d = sig[["stock_id", "entry_pos", f"days_{rule}", f"ret_{rule}"]].dropna()
    d = d.rename(columns={f"days_{rule}": "days", f"ret_{rule}": "ret"})
    d["exit_pos"] = d["entry_pos"] + d["days"].astype(int) - 1
    by_entry = {k: g for k, g in d.groupby("entry_pos")}
    equity = np.ones(ncal)
    cash = 1.0
    open_pos = []   # (exit_pos, stock_id, amount_in, ret)
    held = set()
    slot_used_days = 0; trades = 0; hold_days = 0
    pnl_pre = 0.0; pnl_post = 0.0
    first, last = int(d["entry_pos"].min()), int(d["exit_pos"].max())
    for t in range(first, min(ncal, last + 2)):
        # 出場（t 為出場日：ret 已含次日開盤或當日收盤價，這裡把資金在 t 日回收）
        still = []
        for ex_pos, sid, amt, ret in open_pos:
            if ex_pos <= t:
                cash += amt * (1 + ret)
                held.discard(sid)
                if ex_pos < split_pos:
                    pnl_pre += amt * ret
                else:
                    pnl_post += amt * ret
            else:
                still.append((ex_pos, sid, amt, ret))
        open_pos = still
        # 進場（t 為進場日開盤）
        g = by_entry.get(t)
        if g is not None and len(open_pos) < n_slots:
            cand = g[~g["stock_id"].isin(held)]
            if len(cand):
                take = rng.permutation(len(cand))[: n_slots - len(open_pos)]
                slot_value = equity[t - 1] / n_slots if t > 0 else 1.0 / n_slots
                for i in take:
                    row = cand.iloc[i]
                    amt = min(slot_value, cash)
                    if amt <= 1e-9:
                        break
                    cash -= amt
                    open_pos.append((int(row["exit_pos"]), row["stock_id"], amt, float(row["ret"])))
                    held.add(row["stock_id"]); trades += 1; hold_days += int(row["days"])
        slot_used_days += len(open_pos)
        # 權益：現金 ＋ 持倉以成本計（逐日市值需要價格序列；本研究只用出場時結算，權益曲線為階梯狀）
        equity[t] = cash + sum(a for _, _, a, _ in open_pos)
    equity[:first] = 1.0
    equity[min(ncal, last + 2):] = equity[min(ncal, last + 2) - 1]
    days_total = min(ncal, last + 2) - first
    years = days_total / 245
    final = equity[min(ncal, last + 2) - 1]
    # 最大回撤（階梯權益）
    peak = np.maximum.accumulate(equity); mdd = float(((equity - peak) / peak).min())
    return equity, {"final": final, "cagr": final ** (1 / years) - 1, "mdd": mdd, "trades": trades,
                    "slot_use": slot_used_days / (days_total * n_slots), "avg_hold": hold_days / max(1, trades),
                    "pnl_pre": pnl_pre, "pnl_post": pnl_post}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--sens", nargs="*", type=int, default=[3, 10])
    a = ap.parse_args()
    t0 = time.time()
    cal = D.load_calendar(); ncal = len(cal); split_pos = int(cal.searchsorted(pd.Timestamp(SPLIT)))
    ex = pd.read_csv(os.path.join(HERE, "results5", "exits.csv.gz"), dtype={"stock_id": str})
    os.makedirs(RESULTS, exist_ok=True)
    L = ["# 研究八：組合層模擬——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG7.md`。",
         f"資金 1、N＝{a.n} 個等權槽、訊號多於空槽時隨機挑（{a.reps} 個種子）、補不到就空手、現金報酬 0、成本 0.585%／筆。年化以 245 個交易日／年計。權益以成本計、出場時結算（階梯曲線），最大回撤因此偏小、只供相對比較。", ""]
    allstats = {}
    for set_code, set_name in SETS.items():
        sig = ex[ex["set"] == set_code]
        L.append(f"## {set_code} {set_name}（訊號 {len(sig):,} 筆，N＝{a.n}）"); L.append("")
        L.append("| 規則 | 年化報酬 中位數 | p10 ~ p90 | 對 H60 年化差 中位數 | p10 ~ p90 | 同號比例 | 判定 | 最大回撤 | 槽位使用率 | 交易筆數 | 平均持有日 | 前段損益／後段損益（占資金） |")
        L.append("|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|---:|")
        res = {}
        for rule in RULES:
            stats = []
            for r in range(a.reps):
                rng = np.random.default_rng(1000 + r)
                _, s = simulate(sig, rule, a.n, rng, ncal, split_pos)
                stats.append(s)
            res[rule] = pd.DataFrame(stats)
        base = res["H60"]["cagr"].to_numpy()
        for rule in RULES:
            s = res[rule]; c = s["cagr"].to_numpy(); diff = c - base
            same = float(np.mean(np.sign(diff) == np.sign(np.median(diff)))) if rule != "H60" else 1.0
            if rule == "H60":
                v = "基準"
            elif same >= 0.9 and abs(np.median(diff)) >= 0.01:
                v = "較好" if np.median(diff) > 0 else "較差"
            else:
                v = "分不出來"
            L.append(f"| {rule} | **{np.median(c) * 100:+.2f}%** | {np.percentile(c, 10) * 100:+.2f}% ~ {np.percentile(c, 90) * 100:+.2f}% | "
                     f"{np.median(diff) * 100:+.2f} pp | {np.percentile(diff, 10) * 100:+.2f} ~ {np.percentile(diff, 90) * 100:+.2f} | {same * 100:.0f}% | {v} | "
                     f"{s['mdd'].median() * 100:.1f}% | {s['slot_use'].median() * 100:.0f}% | {s['trades'].median():.0f} | {s['avg_hold'].median():.1f} | "
                     f"{s['pnl_pre'].median() * 100:+.0f}%／{s['pnl_post'].median() * 100:+.0f}% |")
        allstats[set_code] = res
        L.append("")
        # 敏感度：N
        for n2 in a.sens:
            row = []
            for rule in RULES:
                cs = [simulate(sig, rule, n2, np.random.default_rng(5000 + r), ncal, split_pos)[1]["cagr"] for r in range(min(a.reps, 50))]
                row.append(f"{rule} {np.median(cs) * 100:+.2f}%")
            L.append(f"- 敏感度 N＝{n2}（50 個種子，年化中位數）：" + "、".join(row))
        L.append("")
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"寫入 {RESULTS}/summary.md，{time.time() - t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
