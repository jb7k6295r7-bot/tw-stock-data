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
HOLD_PROXY_ATR_X = 3.0     # H20／H60 代用停損距離的 ATR 倍數（PREREG5 定案）
CAP_WARN = 0.30            # 被 w_max 綁住的筆數比例超過三成 → 該組「等風險」標籤打折


def stop_distance(ex: pd.DataFrame, code: str, kind: str, p) -> pd.Series:
    if kind == "stop" or kind == "trail":
        return pd.Series(p, index=ex.index, dtype=float)
    if kind == "atr":
        return p * ex["atr_pct"]
    # hold：代用值 ＝ 3 × ATR14(進場日) ÷ 進場價（PREREG5 定案：零前視，與 A3 同部位）
    return HOLD_PROXY_ATR_X * ex["atr_pct"]


def main():
    global RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--wmax", type=float, required=True, help="單筆部位上限（占資金比例），PREREG5 第五節問題 1 的答案")
    ap.add_argument("--out", default=RESULTS, help="輸出目錄（敏感度用，主表固定 results6/）")
    a = ap.parse_args()
    RESULTS = a.out
    ex = pd.read_csv(os.path.join(HERE, "results5", "exits.csv.gz"), dtype={"stock_id": str})
    cal_split = pd.Timestamp(R5.SPLIT)
    ex["pre"] = pd.to_datetime(ex["entry_date"]) < cal_split
    for code, kind, p in R5.RULES:
        d = stop_distance(ex, code, kind, p)
        w_raw = RISK / d
        w = np.minimum(w_raw, a.wmax)
        ex[f"d_{code}"] = d; ex[f"w_{code}"] = w
        ex[f"capped_{code}"] = (w_raw > a.wmax).astype(float).where(d.notna())
        ex[f"risk_{code}"] = w * d                            # 實際每筆風險（占資金）
        ex[f"pnl_{code}"] = w * ex[f"ret_{code}"]          # 對帳戶的損益（占資金比例）
        ex[f"R_{code}"] = ex[f"ret_{code}"] / d            # R 倍數
    os.makedirs(RESULTS, exist_ok=True)
    ex.to_csv(os.path.join(RESULTS, "exits_risk.csv.gz"), index=False)

    def paired(g, col, base_col):
        mm = g[col].notna() & g[base_col].notna()
        if mm.sum() < 2:
            return None
        diff = (g.loc[mm, col] - g.loc[mm, base_col]).to_numpy(float)
        dn = R5._nonoverlap(g[mm]); dmean = diff.mean(); dse = diff.std(ddof=1) / math.sqrt(max(1, dn))
        pre = g[mm & g["pre"]]; post = g[mm & ~g["pre"]]
        dpre = (pre[col] - pre[base_col]).mean() if len(pre) else np.nan
        dpost = (post[col] - post[base_col]).mean() if len(post) else np.nan
        return {"n": int(mm.sum()), "n_no": dn, "mean": dmean, "lo": dmean - 1.96 * dse, "hi": dmean + 1.96 * dse, "pre": dpre, "post": dpost}

    def verdict(pa, n_no, is_base=False):
        if is_base:
            return "基準"
        if pa is None:
            return "—"
        if pa["lo"] > 0 and np.sign(pa["pre"]) == np.sign(pa["post"]):
            v = "期望值較好"
        elif pa["hi"] < 0:
            v = "較差"
        else:
            v = "分不出來"
        if n_no < 30:
            v = "樣本不足（不報）"
        elif n_no < 100:
            v += "（樣本不足）"
        return v

    L = ["# 研究六：出場規則比較——等風險版（細表）", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG5.md`（定案段）。每筆風險 {RISK * 100:.0f}%，單筆部位上限 w_max ＝ {a.wmax * 100:.0f}%。",
         f"主指標 ＝ 每筆對帳戶的損益（w × 淨報酬，占資金比例）；配對差 ＝ 同一筆進場「該規則 − H60」。H20／H60 的停損距離是代用值（{HOLD_PROXY_ATR_X:.0f}×ATR14 初始距離，零前視，與 A3 同部位）。",
         f"「綁住比例」＝ 2%÷d 超過 w_max 而被砍到 w_max 的筆數比例；超過 {CAP_WARN * 100:.0f}% 的組，「等風險」標籤要打折（K線線 10:40）。「實際風險」＝ w × d 的平均。", ""]
    for set_code, set_name in R5.SETS.items():
        d = ex[ex["set"] == set_code]
        if not len(d):
            continue
        L.append(f"## {set_code} {set_name}（n {len(d):,}）"); L.append("")
        L.append("| 規則 | n | 非重疊 | 停損距離 d | 平均部位 w | 綁住比例 | 實際風險 | 平均損益（占資金） | 95% CI | 第 5 百分位 | 最差 | 平均 R | 配對差 vs H60 | 配對差 CI | 前段差 | 後段差 | 判定 |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---:|---:|---|")
        base_col = "pnl_H60"
        for code, kind, p in R5.RULES:
            col = f"pnl_{code}"
            m = d[col].notna()
            if m.sum() == 0:
                continue
            g = d[m]
            x = g[col].to_numpy(float); n_no = R5._nonoverlap(g)
            mean = x.mean(); se = x.std(ddof=1) / math.sqrt(max(1, n_no))
            pa = paired(g, col, base_col)
            v = verdict(pa, n_no, is_base=(code == "H60"))
            capped = float(g[f"capped_{code}"].mean())
            if capped > CAP_WARN and code != "H60":
                v += f"；⚠ 綁住 {capped * 100:.0f}%，等風險標籤打折"
            L.append(f"| {code} | {len(x):,} | {n_no:,} | {g[f'd_{code}'].mean() * 100:.1f}% | {g[f'w_{code}'].mean() * 100:.1f}% | {capped * 100:.0f}% | {g[f'risk_{code}'].mean() * 100:.2f}% | **{mean * 100:+.3f}%** | {(mean - 1.96 * se) * 100:+.3f}% ~ {(mean + 1.96 * se) * 100:+.3f}% | "
                     f"{np.percentile(x, 5) * 100:+.2f}% | {x.min() * 100:+.2f}% | {g[f'R_{code}'].mean():+.2f} | "
                     + (f"{pa['mean'] * 100:+.3f}% | {pa['lo'] * 100:+.3f}% ~ {pa['hi'] * 100:+.3f}% | {pa['pre'] * 100:+.3f}% | {pa['post'] * 100:+.3f}% | {v} |" if pa else "— | — | — | — | — |"))
        # K線線 10:40：唯一控制住部位、只變動停損機制的一對——H60（3×ATR 部位）vs A3
        g = d[d["pnl_A3"].notna() & d["pnl_H60"].notna()]
        if len(g):
            pa = paired(g, "pnl_A3", "pnl_H60"); n_no = R5._nonoverlap(g)
            same = bool(np.allclose(g["w_A3"], g["w_H60"]))
            L.append("")
            L.append(f"**同部位對照：A3 − H60（兩者部位{'完全相同' if same else '不同（檢查！）'}，唯一差別是 3×ATR 停損有沒有觸發）**：n {pa['n']:,}、非重疊 {n_no:,}，"
                     f"配對差 **{pa['mean'] * 100:+.3f}%**（CI {pa['lo'] * 100:+.3f}% ~ {pa['hi'] * 100:+.3f}%），前段 {pa['pre'] * 100:+.3f}%、後段 {pa['post'] * 100:+.3f}% → {verdict(pa, n_no)}。"
                     f"以 R 倍數看：A3 平均 {g['R_A3'].mean():+.2f} R、H60 {g['R_H60'].mean():+.2f} R。")
        L.append("")
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"寫入 {RESULTS}/summary.md")


if __name__ == "__main__":
    main()
