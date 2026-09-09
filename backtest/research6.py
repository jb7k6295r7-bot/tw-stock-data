"""研究六：出場規則比較——等風險版。判準在 backtest/PREREG5.md（定案前不跑）。

    python3 -m backtest.research6 --wmax 0.25

只做後處理：讀 results5/exits.csv.gz（研究五逐筆，含 atr_pct、mae20、mae60），
依每條規則的「進場時停損距離 d」算部位 w ＝ min(2% ÷ d, wmax)，主指標 ＝ w × 淨報酬（占資金比例）對 H60 的逐筆配對差。
H20／H60 的 d 是代用值：該集合內同持有期 MAE 的第 95 百分位（PREREG5 第二節）。
"""
from __future__ import annotations

import argparse
import math
import os

import numpy as np
import pandas as pd

from . import research5 as R5

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results6")
RISK = 0.02


def stop_distance(ex: pd.DataFrame, code: str, kind: str, p) -> pd.Series:
    if kind == "stop" or kind == "trail":
        return pd.Series(p, index=ex.index, dtype=float)
    if kind == "atr":
        return p * ex["atr_pct"]
    # hold：代用值 ＝ 同集合、同持有期 MAE 第 95 百分位（取絕對值），逐集合算
    hh = p
    d = pd.Series(np.nan, index=ex.index, dtype=float)
    for s, g in ex.groupby("set"):
        mae = -g[f"mae{hh}"].dropna()
        d.loc[g.index] = float(np.percentile(mae, 95)) if len(mae) else np.nan
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wmax", type=float, required=True, help="單筆部位上限（占資金比例），PREREG5 第五節問題 1 的答案")
    a = ap.parse_args()
    ex = pd.read_csv(os.path.join(HERE, "results5", "exits.csv.gz"), dtype={"stock_id": str})
    cal_split = pd.Timestamp(R5.SPLIT)
    ex["pre"] = pd.to_datetime(ex["entry_date"]) < cal_split
    for code, kind, p in R5.RULES:
        d = stop_distance(ex, code, kind, p)
        w = np.minimum(RISK / d, a.wmax)
        ex[f"d_{code}"] = d; ex[f"w_{code}"] = w
        ex[f"pnl_{code}"] = w * ex[f"ret_{code}"]          # 對帳戶的損益（占資金比例）
        ex[f"R_{code}"] = ex[f"ret_{code}"] / d            # R 倍數
    os.makedirs(RESULTS, exist_ok=True)
    ex.to_csv(os.path.join(RESULTS, "exits_risk.csv.gz"), index=False)

    L = ["# 研究六：出場規則比較——等風險版（細表）", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG5.md`。每筆風險 {RISK * 100:.0f}%，單筆部位上限 w_max ＝ {a.wmax * 100:.0f}%。",
         "主指標 ＝ 每筆對帳戶的損益（w × 淨報酬，占資金比例）；配對差 ＝ 同一筆進場「該規則 − H60」。H20／H60 的停損距離是代用值（同集合 MAE 第 95 百分位）。", ""]
    for set_code, set_name in R5.SETS.items():
        d = ex[ex["set"] == set_code]
        if not len(d):
            continue
        L.append(f"## {set_code} {set_name}（n {len(d):,}）"); L.append("")
        L.append("| 規則 | n | 非重疊 | 停損距離 d | 平均部位 w | 平均損益（占資金） | 95% CI | 第 5 百分位 | 最差 | 平均 R | 配對差 vs H60 | 配對差 CI | 前段差 | 後段差 | 判定 |")
        L.append("|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---:|---:|---|")
        base_col = "pnl_H60"
        for code, kind, p in R5.RULES:
            col = f"pnl_{code}"
            m = d[col].notna()
            if m.sum() == 0:
                continue
            g = d[m]
            x = g[col].to_numpy(float); n_no = R5._nonoverlap(g)
            mean = x.mean(); se = x.std(ddof=1) / math.sqrt(max(1, n_no))
            mm = g[col].notna() & g[base_col].notna()
            diff = (g.loc[mm, col] - g.loc[mm, base_col]).to_numpy(float)
            dn = R5._nonoverlap(g[mm]); dmean = diff.mean(); dse = diff.std(ddof=1) / math.sqrt(max(1, dn))
            pre = g[mm & g["pre"]]; post = g[mm & ~g["pre"]]
            dpre = (pre[col] - pre[base_col]).mean() if len(pre) else np.nan
            dpost = (post[col] - post[base_col]).mean() if len(post) else np.nan
            lo, hi = dmean - 1.96 * dse, dmean + 1.96 * dse
            if code == "H60":
                v = "基準"
            elif lo > 0 and np.sign(dpre) == np.sign(dpost):
                v = "期望值較好"
            elif hi < 0:
                v = "較差"
            else:
                v = "分不出來"
            if n_no < 30:
                v = "樣本不足（不報）"
            elif n_no < 100:
                v += "（樣本不足）"
            L.append(f"| {code} | {len(x):,} | {n_no:,} | {g[f'd_{code}'].mean() * 100:.1f}% | {g[f'w_{code}'].mean() * 100:.1f}% | **{mean * 100:+.3f}%** | {(mean - 1.96 * se) * 100:+.3f}% ~ {(mean + 1.96 * se) * 100:+.3f}% | "
                     f"{np.percentile(x, 5) * 100:+.2f}% | {x.min() * 100:+.2f}% | {g[f'R_{code}'].mean():+.2f} | {dmean * 100:+.3f}% | {lo * 100:+.3f}% ~ {hi * 100:+.3f}% | {dpre * 100:+.3f}% | {dpost * 100:+.3f}% | {v} |")
        L.append("")
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"寫入 {RESULTS}/summary.md")


if __name__ == "__main__":
    main()
