"""研究十三 追加四：S∖AND 與安慰劑限 AND 同窗（month ≥ 2017-02）。判準 backtest/PREREG10.md 追加四。

    python3 -m backtest.r13_win [--panel results3_f3_0914/panel.csv.gz] [--out results13_win0914]

逐筆表與集合建構全部 import 研究十三（同一件事只有一份實作）；不碰 AND 主格、G1、組合層。
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from . import data as D
from . import research13 as R13

HERE = os.path.dirname(os.path.abspath(__file__))
WIN_FROM = "2017-02"     # AND 第一筆訊號 2017-02-13 所在月


def placebo(S_pool, AND, base, seed=13, reps=200):
    bm = base[120]["sum"] / base[120]["count"]
    exS = (S_pool["g_H120"] - S_pool["month"].map(bm)).to_numpy(float); okS = ~np.isnan(exS)
    real = float(np.nanmean((AND["g_H120"] - AND["month"].map(bm)).to_numpy(float)))
    rng = np.random.default_rng(seed); draws = []
    size = int(AND["g_H120"].notna().sum())
    for _ in range(reps):
        pick = rng.choice(np.flatnonzero(okS), size=size, replace=False)
        draws.append(exS[pick].mean())
    draws = np.array(draws)
    return real, draws, float((draws < real).mean() * 100), int(okS.sum()), size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=os.path.join(HERE, "results3_f3_0914", "panel.csv.gz"))
    ap.add_argument("--out", default=os.path.join(HERE, "results13_win0914"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cal = D.load_calendar()
    panel = pd.read_csv(a.panel, dtype={"stock_id": str})
    panel["rev_hi24"] = panel["rev_hi24"].fillna(False).astype(bool)
    S, AND, _ = R13.build_sets(cal, panel)
    bm = pd.read_csv(os.path.join(HERE, "results11", "baseline_months.csv"), dtype={"month": str}).set_index(["hold", "month"])
    base = {H: bm.loc[H] for H in (60, 120)}
    comp = S[~S.index.isin(AND.index)]
    win = comp["month"] >= WIN_FROM
    comp_win, comp_2016 = comp[win], comp[~win]
    S_win = S[S["month"] >= WIN_FROM]
    L = ["# 研究十三 追加四：S∖AND 與安慰劑限 AND 同窗（month ≥ 2017-02）——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG10.md` 追加四。面板 `{os.path.relpath(a.panel, HERE)}`。", "",
         f"S {len(S):,} 筆（{S['month'].min()} ～ {S['month'].max()}）；AND {len(AND):,} 筆（{AND['month'].min()} ～ {AND['month'].max()}）；"
         f"S∖AND 全部 {len(comp):,} ＝ 限窗 {len(comp_win):,} ＋ 2016 段（≤ 2017-01）{len(comp_2016):,}。", ""]
    L.append("## 一、逐筆層"); L.append("")
    R13.set_table("AND（不變，對照用）", AND, base, L)
    R13.set_table("S∖AND 含 2016（原版口徑；⚠ 2016 段結構性全 False）", comp, base, L)
    R13.set_table("S∖AND 限窗 month ≥ 2017-02（追加四主格）", comp_win, base, L)
    R13.set_table("S 2016 段 month ≤ 2017-01（單獨對照；這段 AND 結構性 0 筆）", comp_2016, base, L)
    L.append("## 二、安慰劑：從 S 隨機抽 |AND 有 H120| 筆 × 200 次，H120 超額分佈（種子 13）"); L.append("")
    for nm, pool in (("原版口徑：母體 ＝ 全部 S（含 2016）", S), ("追加四：母體 ＝ S month ≥ 2017-02", S_win)):
        real, draws, pct, npool, size = placebo(pool, AND, base)
        L.append(f"- {nm}（母體 {npool:,} 筆、每次抽 {size:,}）：真 AND H120 超額 {real * 100:+.2f} pp；p5／p50／p95 ＝ "
                 f"{np.percentile(draws, 5) * 100:+.2f}／{np.percentile(draws, 50) * 100:+.2f}／{np.percentile(draws, 95) * 100:+.2f} pp；真值落在第 **{pct:.0f}** 百分位 ⇒ "
                 + ("超出 p95，疊加效果測得出" if pct >= 95 else "在安慰劑範圍內，疊加效果測不出"))
    L.append("")
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
