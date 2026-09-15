"""PREREGM1 層一：市場狀態 → 未來指數報酬（同一條序列各狀態互比）。判準 backtest/PREREGM1.md（⛔ 策略線改版登錄到了才跑）。

    python3 -m backtest.researchm1 --index data/history/market_index.csv --out backtest/resultsm1

規則（K線分析 09-14 1935／09-15 0800 裁定）：
  訊號與去抖 import m1_states（a/b/a∧b/c/d；<K 併入前段再合併同狀態；K=20 交易日）
  每日狀態 ＝ 去抖後所屬段的狀態；有效 n ＝ 去抖後段數（右設限：最後一段未結束不計）；按狀態別各報 n，<24 標「還沒測」
  量測 ＝ 各狀態下未來 H=20/60/120 日報酬的平均與 p10/p50/p90；狀態間差的 95% CI 用【段分群】SE（段均值的 std/sqrt(段數)）
  分段 ＝ 1990s／2000s／2010s／2020s 四段並列 ＋ 主判定格「2001 起」（240MA＝年線只在 2001 後成立）；a 的 1990-2000 段結論欄寫「窗口長度不可比」
  敏感度 ＝ 剔除 1990-92、剔除 7～9 月進場；另報各狀態的進場月份分佈
  判定字只用 測得出／測不出／還沒測；⛔ 不做任何「贏過大盤」的比價（層一沒有比價基準）
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from . import m1_states as M

HERE = os.path.dirname(os.path.abspath(__file__))
HOLDS = (20, 60, 120)
N_MIN = 24
MAIN_FROM = "2001-01-01"
WINDOWS = {"全期": None, "1990s": ("1990-01-01", "1999-12-31"), "2000s": ("2000-01-01", "2009-12-31"), "2010s": ("2010-01-01", "2019-12-31"),
           "2020s": ("2020-01-01", "2099-12-31"), "主判定 2001 起": (MAIN_FROM, "2099-12-31"), "剔除 1990-92": ("1993-01-01", "2099-12-31")}


def day_states(close: pd.Series, k: int = M.K_DEFAULT) -> dict[str, pd.DataFrame]:
    """每個訊號：逐日 DataFrame(state, seg_id, seg_start)——state 是去抖後所屬段的狀態；最後一段 open=True（不計入 n）。"""
    out = {}
    for key in M.SIGNALS:
        s = M.signals(close)[key].dropna()
        db = M.debounce(s, k)
        idx = s.index
        seg_id = np.searchsorted(db["start"].to_numpy(), idx.to_numpy(), side="right") - 1
        st = db["state"].to_numpy(object)[seg_id]
        out[key] = pd.DataFrame({"state": st, "seg_id": seg_id, "open": seg_id == len(db) - 1}, index=idx)
    return out


def fwd_returns(close: pd.Series, holds=HOLDS) -> pd.DataFrame:
    return pd.DataFrame({H: close.shift(-H) / close - 1 for H in holds}, index=close.index)


def _cluster_stats(x: pd.Series, seg: pd.Series):
    """段分群：回傳 (段數, 平均, SE)；平均取逐日平均，SE 用段均值的離散。"""
    g = x.groupby(seg).mean()
    n = int(len(g))
    se = float(g.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
    return n, float(x.mean()), se


def layer1(close: pd.Series, k: int = M.K_DEFAULT, holds=HOLDS, exclude_months=()) -> pd.DataFrame:
    """逐格：訊號 × 視窗 × 狀態 × H。每列含 n（完整段數）、平均、p10/p50/p90、對「其餘狀態」的差與 CI、判定。"""
    ds = day_states(close, k); fr = fwd_returns(close, holds)
    rows = []
    for key, d in ds.items():
        d = d[~d["open"]]                       # 右設限：最後一段不計
        for wname, win in WINDOWS.items():
            dd = d if win is None else d[(d.index >= pd.Timestamp(win[0])) & (d.index <= pd.Timestamp(win[1]))]
            if exclude_months:
                dd = dd[~dd.index.month.isin(exclude_months)]
            for H in holds:
                x = fr[H].reindex(dd.index); ok = x.notna(); dd_ok = dd[ok]; x = x[ok]
                if len(x) == 0:
                    continue
                for st in sorted(dd_ok["state"].unique()):
                    m = dd_ok["state"] == st
                    n, mean, se = _cluster_stats(x[m], dd_ok.loc[m, "seg_id"])
                    n2, mean2, se2 = _cluster_stats(x[~m], dd_ok.loc[~m, "seg_id"]) if (~m).any() else (0, np.nan, np.nan)
                    diff = mean - mean2 if n2 else np.nan
                    sed = np.sqrt(se ** 2 + se2 ** 2) if (n > 1 and n2 > 1) else np.nan
                    lo, hi = (diff - 1.96 * sed, diff + 1.96 * sed) if np.isfinite(sed) else (np.nan, np.nan)
                    if key == "a" and wname == "1990s":
                        judge = "窗口長度不可比（240 交易日在 1990 年代 ≈ 10.1 個月）"
                    elif n < N_MIN or n2 < N_MIN:
                        judge = "還沒測（狀態別 n < 24）"
                    elif not np.isfinite(lo):
                        judge = "還沒測"
                    elif lo <= 0 <= hi:
                        judge = "測不出"
                    else:
                        judge = "測得出（＋）" if diff > 0 else "測得出（−）"
                    rows.append({"signal": key, "label": M.LABELS[key], "window": wname, "state": st, "H": H, "n_seg": n, "n_days": int(m.sum()),
                                 "mean": mean, "p10": float(x[m].quantile(0.1)), "p50": float(x[m].median()), "p90": float(x[m].quantile(0.9)),
                                 "rest_n_seg": n2, "rest_mean": mean2, "diff": diff, "ci_lo": lo, "ci_hi": hi, "judge": judge})
    return pd.DataFrame(rows)


def month_distribution(close: pd.Series, k: int = M.K_DEFAULT) -> pd.DataFrame:
    rows = []
    for key, d in day_states(close, k).items():
        ct = pd.crosstab(d["state"], d.index.month)
        share = ct.div(ct.sum(axis=1), axis=0) * 100
        for st in share.index:
            r = {"signal": key, "state": st, **{f"m{m:02d}": float(share.loc[st].get(m, 0.0)) for m in range(1, 13)}}
            r["q3_share"] = float(share.loc[st].reindex([7, 8, 9]).fillna(0).sum())
            rows.append(r)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, help="指數 CSV（date,close）——本庫:data/history/market_index.csv；⛔ 只讀 close")
    ap.add_argument("--out", default=os.path.join(HERE, "resultsm1")); ap.add_argument("--k", type=int, default=M.K_DEFAULT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    c = M.load_series(a.index)
    t = M.n_table(c, a.k); t.to_csv(os.path.join(a.out, "n_table.csv"), index=False)
    L1 = layer1(c, a.k); L1.to_csv(os.path.join(a.out, "layer1.csv"), index=False)
    S = layer1(c, a.k, exclude_months=(7, 8, 9)); S.to_csv(os.path.join(a.out, "layer1_ex_q3.csv"), index=False)
    md = month_distribution(c, a.k); md.to_csv(os.path.join(a.out, "month_dist.csv"), index=False)
    stamp = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    L = [f"# PREREGM1 層一——細表", "", f"產出：{stamp}（台北）。序列 `{a.index}`（{c.index[0].date()} ～ {c.index[-1].date()}，{len(c):,} 日）；K＝{a.k}。判準 `backtest/PREREGM1.md`。", ""]
    L.append("## 一、有效 n（去抖後段數）"); L.append("")
    for r in t.itertuples():
        L.append(f"- {r.label}: 素切換 {r.raw_switches}、去抖後 n＝{r.n} {r.n_by_state}、最後一段 {r.last_state} {r.last_len} 日未計、{r.judge}")
    L.append(""); L.append("## 二、主判定格（2001 起）H＝120，各狀態 vs 其餘"); L.append("")
    L.append("| 訊號 | 狀態 | 段數 | 平均 | p10 / p50 / p90 | 差 | 95% CI | 判定 |"); L.append("|---|---|---:|---:|---|---:|---|---|")
    for r in L1[(L1["window"] == "主判定 2001 起") & (L1["H"] == 120)].itertuples():
        L.append(f"| {r.label} | {r.state} | {r.n_seg} | {r.mean * 100:+.2f}% | {r.p10 * 100:+.1f} / {r.p50 * 100:+.1f} / {r.p90 * 100:+.1f} | {r.diff * 100:+.2f} pp | {r.ci_lo * 100:+.2f} ~ {r.ci_hi * 100:+.2f} | {r.judge} |")
    L.append(""); L.append("其餘視窗（四段並列、全期、剔除 1990-92）與 H＝20／60 見 `layer1.csv`；剔除 7～9 月進場見 `layer1_ex_q3.csv`；月份分佈見 `month_dist.csv`。")
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
