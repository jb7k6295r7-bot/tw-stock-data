"""把 signals.csv 整理成 summary.md。判定門檻照 backtest/PREREG.md 第五節。"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import evaluate as E

MIN_N = 50


def _pct(x, d=2):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def _n(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.0f}"


def _period_stats(df, col, base_signed):
    return E.stats(df, col, base_signed)


def pattern_block(name: str, g: pd.DataFrame, base: dict, split_pos: int) -> str:
    d = int(g["direction"].iloc[0])
    bs = {k: d * base[k]["mean_gross"] - E.COST for k in ("pre", "post", "all")}
    pre = g[g["signal_pos"] < split_pos]
    post = g[g["signal_pos"] >= split_pos]
    s_all = _period_stats(g, "ret_hold_signed", bs["all"])
    s_pre = _period_stats(pre, "ret_hold_signed", bs["pre"])
    s_post = _period_stats(post, "ret_hold_signed", bs["post"])
    s_atr = _period_stats(g, "ret_atr_signed", bs["all"]) if "ret_atr_signed" in g else {"n": 0}

    L = [f"### {name}（{'多' if d > 0 else '空'}方）", ""]
    L.append(f"- 筆數 {s_all.get('n', 0):,}；非重疊 {s_all.get('n_nonoverlap', 0):,}（重疊比例 {s_all.get('overlap_pct', 0) * 100:.0f}%）；前段 {s_pre.get('n', 0):,}、後段 {s_post.get('n', 0):,}")
    if s_all.get("n", 0) == 0:
        L.append("- **沒有訊號。**")
        return "\n".join(L) + "\n"
    L.append("")
    L.append("| 出場 | 期間 | n | 平均淨報酬 | 中位數 | 95% CI | 母體基準 | 超額 | 超額 CI | 勝率 | 平均賺 | 平均賠 | 最差 | 最好 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    def row(label, per, s, b):
        if s.get("n", 0) == 0:
            return f"| {label} | {per} | 0 | | | | | | | | | | | |"
        return (f"| {label} | {per} | {s['n']:,} | {_pct(s['mean'])} | {_pct(s['median'])} | {_pct(s['ci_lo'])} ~ {_pct(s['ci_hi'])} | {_pct(b)} | "
                f"**{_pct(s['excess'])}** | {_pct(s['excess_ci_lo'])} ~ {_pct(s['excess_ci_hi'])} | {s['win_rate'] * 100:.1f}% | "
                f"{_pct(s['avg_win'])} | {_pct(s['avg_loss'])} | {_pct(s['worst'])} | {_pct(s['best'])} |")

    L.append(row("固定 20 日", "全期", s_all, bs["all"]))
    L.append(row("固定 20 日", "前段", s_pre, bs["pre"]))
    L.append(row("固定 20 日", "後段", s_post, bs["post"]))
    L.append(row("2×ATR 追蹤", "全期", s_atr, bs["all"]))
    if "atr_stopped" in g and g["atr_stopped"].notna().any():
        L.append("")
        L.append(f"- 2×ATR 追蹤：停損觸發率 {g['atr_stopped'].mean() * 100:.1f}%，平均持有 {g['atr_days'].mean():.1f} 日；最差單筆 固定 {_pct(s_all['worst'])} → 追蹤 {_pct(s_atr.get('worst', np.nan))}")
    if "bench_hold" in g and g["bench_hold"].notna().any():
        L.append(f"- 0050 同窗平均 {_pct(float(g['bench_hold'].mean()))}（型態多方毛報酬 {_pct(float(g['ret_hold_gross'].mean()))}）")
    x = g["ret_hold_gross"].dropna()
    L.append(f"- |毛報酬| > 50% 的筆數：{int((x.abs() > 0.5).sum())}（{(x.abs() > 0.5).mean() * 100:.2f}%）")
    # 追加分析（事後）：影線型態對「同樣前段趨勢、不限 K 棒形狀」的控制組
    ckey = {"P4_hammer": ("down5_", "前 10 日跌 ≥ 5% 的所有股票日"), "P4_shooting_star": ("up5_", "前 10 日漲 ≥ 5% 的所有股票日")}.get(name)
    if ckey and f"{ckey[0]}all" in base:
        L.append("")
        L.append(f"**追加分析（事後，不影響上面的判定）**：控制組 ＝ {ckey[1]}。")
        L.append("")
        L.append("| 期間 | 控制組 n | 控制組平均淨報酬（方向修正後） | 型態 − 控制組 | 型態 − 控制組 CI |")
        L.append("|---|---|---|---|---|")
        for per, sp_, lab in (("all", s_all, "全期"), ("pre", s_pre, "前段"), ("post", s_post, "後段")):
            cb = base[f"{ckey[0]}{per}"]
            cbs = d * cb["mean_gross"] - E.COST
            if sp_.get("n", 0):
                L.append(f"| {lab} | {cb['n']:,} | {_pct(cbs)} | **{_pct(sp_['mean'] - cbs)}** | {_pct(sp_['mean'] - cbs - 1.96 * sp_['se'])} ~ {_pct(sp_['mean'] - cbs + 1.96 * sp_['se'])} |")

    # 判定
    verdict = []
    ok_n = s_all["n_nonoverlap"] >= MIN_N
    c1 = s_all["excess_ci_lo"] > 0
    c2 = s_pre.get("n", 0) > 0 and s_post.get("n", 0) > 0 and s_pre["excess"] > 0 and s_post["excess"] > 0
    if not ok_n:
        verdict.append(f"**樣本不足**（非重疊 {s_all['n_nonoverlap']} < {MIN_N}），不下結論。")
    elif c1 and c2:
        verdict.append("**通過事前門檻**：全期超額 CI 不含 0，且前後段超額皆 > 0。")
    else:
        why = []
        if not c1:
            why.append("全期超額 CI 含 0" if s_all["excess"] > 0 else "全期超額 ≤ 0")
        if not c2:
            why.append(f"子期間不一致（前 {_pct(s_pre.get('excess', np.nan))}、後 {_pct(s_post.get('excess', np.nan))}）")
        verdict.append("**測不出效果**：" + "；".join(why) + "。")
    L.append("")
    L.append("- 判定：" + " ".join(verdict))
    return "\n".join(L) + "\n"


def extras_block(sigs: pd.DataFrame, base: dict, split_pos: int) -> str:
    L = []
    # P2 事後分類
    g = sigs[sigs["pattern"] == "P2_breakaway_gap"]
    if len(g) and "filled_5d" in g:
        L.append("### P2 事後分類：5 日內回補與否（不是進場條件，只是描述）")
        L.append("")
        L.append("| 5 日內回補 | n | 平均淨報酬 | 勝率 |")
        L.append("|---|---|---|---|")
        for k, gg in g.groupby(g["filled_5d"].astype(str)):
            s = E.stats(gg, "ret_hold_net")
            L.append(f"| {k} | {s['n']:,} | {_pct(s['mean'])} | {s['win_rate'] * 100:.1f}% |")
        L.append("")
    # P6 細節
    for pat in ("P6_cup_handle", "P6_cup_handle_cap", "P6w_cup_handle_weekly"):
        g = sigs[sigs["pattern"] == pat]
        if not len(g):
            continue
        L.append(f"### {pat}：目標價達成率與停損對照")
        L.append("")
        L.append("| 項目 | 數值 | Bulkowski（美股，多頭 412 例） |")
        L.append("|---|---|---|")
        for col, lab, ref in (("tgt_half", "半杯深達成率（120 日內）", "76%"), ("tgt_full", "全杯深達成率", "50%"), ("tgt_pct", "百分比算法達成率", "無實測")):
            if col in g:
                L.append(f"| {lab} | {g[col].mean() * 100:.1f}%（n={g[col].notna().sum()}） | {ref} |")
        for col, hit, lab in (("ret_stop_handle_net", "stop_handle_hit", "柄低點停損"), ("ret_stop_8pct_net", "stop_8pct_hit", "8% 停損")):
            if col in g and g[col].notna().any():
                s = E.stats(g, col)
                L.append(f"| {lab}：平均淨報酬／觸發率／最差 | {_pct(s['mean'])} ／ {g[hit].mean() * 100:.1f}% ／ {_pct(s['worst'])} | — |")
        if "pretty" in g:
            for k, gg in g.groupby(g["pretty"].astype(str)):
                s = E.stats(gg, "ret_hold_net")
                L.append(f"| 「漂亮」標記＝{k} | n={s['n']}，平均淨報酬 {_pct(s['mean'])}，勝率 {s['win_rate'] * 100:.1f}% | — |")
        if "rs_pct_240" in g and g["rs_pct_240"].notna().any():
            hi = g[g["rs_pct_240"] >= 90]; lo = g[g["rs_pct_240"] < 90]
            for lab, gg in (("RS 替代值 ≥ 90", hi), ("RS 替代值 < 90", lo)):
                if len(gg):
                    s = E.stats(gg, "ret_hold_net")
                    L.append(f"| {lab} | n={s['n']}，平均淨報酬 {_pct(s['mean'])}，勝率 {s['win_rate'] * 100:.1f}% | — |")
        L.append(f"| 杯身長度中位數／柄長度中位數 | {g['cup_len'].median():.0f} ／ {g['handle_len'].median():.0f}（{'週' if 'weekly' in pat else '交易日'}） | — |")
        L.append("")
    return "\n".join(L) + "\n"


def variants_block(var: pd.DataFrame, sigs: pd.DataFrame, base: dict) -> str:
    if not len(var):
        return ""
    L = ["## 敏感度（［本研究補］參數各換一個鄰近值）", "", "主表值見 PREREG。只看「平均淨報酬（方向修正後）」與筆數有沒有翻轉。", ""]
    L.append("| 型態 | 設定 | n | 平均淨報酬 |")
    L.append("|---|---|---|---|")
    for pat, g0 in sigs.groupby("pattern"):
        if pat.startswith("ERR"):
            continue
        s0 = E.stats(g0, "ret_hold_signed")
        L.append(f"| {pat} | **主表** | {s0['n']:,} | {_pct(s0['mean'])} |")
        vv = var[var["pattern"] == pat]
        for tag, g in vv.groupby("variant"):
            s = E.stats(g, "ret_hold_signed")
            flip = " ⚠翻轉" if (s["n"] and (s["mean"] > 0) != (s0["mean"] > 0)) else ""
            L.append(f"| {pat} | {tag} | {s['n']:,} | {_pct(s['mean'])}{flip} |")
    return "\n".join(L) + "\n"


def write_report(out_dir: str, sigs: pd.DataFrame, var: pd.DataFrame, base: dict, cal, split_pos: int):
    L = ["# 研究二：型態全市場回測——結果", ""]
    L.append(f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準見 `backtest/PREREG.md`，逐筆見 `signals.csv`。")
    L.append("")
    L.append("## 母體基準（隨便挑一天進場、20 日固定持有）")
    L.append("")
    L.append("| 期間 | 股票日 n | 毛報酬平均 | 淨報酬平均（扣 0.585%） |")
    L.append("|---|---|---|---|")
    for k, lab in (("pre", "前段 2016～2020"), ("post", "後段 2021～2026-07"), ("all", "全期")):
        b = base[k]
        L.append(f"| {lab} | {b['n']:,} | {_pct(b['mean_gross'])} | {_pct(b['mean_gross'] - E.COST)} |")
    L.append("")
    L.append("空方型態的基準是「−毛報酬 − 成本」，表裡已換算。")
    L.append("")
    L.append(f"因面額變更等未還原跳價而整筆剔除的訊號：{base.get('excluded_jump_signals', 0):,} 筆（跳價清單見 `par_change_candidates.csv`）。")
    L.append("")
    L.append("## 各型態")
    L.append("")
    if len(sigs):
        errs = sigs[sigs["pattern"].astype(str).str.startswith("ERR")]
        for pat in sorted(sigs["pattern"].unique()):
            if pat.startswith("ERR"):
                continue
            L.append(pattern_block(pat, sigs[sigs["pattern"] == pat], base, split_pos))
        L.append(extras_block(sigs, base, split_pos))
        if len(errs):
            L.append(f"週線杯柄有 {len(errs)} 檔出錯（見 signals.csv 的 ERR_weekly 列）。")
            L.append("")
    L.append(variants_block(var, sigs, base))
    L.append("## 必須揭露")
    L.append("")
    L.append("- 上櫃還原因子來自 FinMind（非官方）；上市因子已對官方全量核對。")
    L.append("- 逐日進場的筆數不是獨立觀察；標準誤一律用非重疊筆數算，CI 因此偏寬。")
    L.append("- 固定持有與 2×ATR 追蹤的差值含「在市場裡的時間變短」的成分。")
    L.append("- Bulkowski 的杯柄對照數字是美股 1990 年代樣本，不是台股。")
    L.append("- 2303 聯電 2008～2009 的杯柄在資料區間外，辨識器未在該案例驗證。")
    L.append("- 成交量未還原：除權（股票股利）當日前後的量比會略有失真。")
    L.append("- 籌碼資料（法人、融資）未用於任何條件，只在 signals.csv 留位置供事後分析。")
    with open(os.path.join(out_dir, "summary.md"), "w") as fh:
        fh.write("\n".join(L))
