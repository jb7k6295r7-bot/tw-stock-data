"""PREREGP6（策略線 0810／1115 §三）：**④型當門檻B 之後的第二道篩**。

    python3 -m backtest.researchp6 [--procs 8] [--reps 200] [--out backtest/resultsp6]

⭐ 引擎與 sig 都不另建：sig ＝ `researchp7.build_sig_gate_b`（同一份門檻B），引擎 ＝ `research11.simulate_mtm`。

⛔ **本規則【不曾】被登錄為獨立排除規則**——④型佔全母體 40.2%（> 30% 的紅線，策略線 0810 §陷阱③），
  那個用法已經出局；本件只登錄【門檻B 池內的第二道篩】（池內佔比另報）。
  ⇒ ⭐〈九十二〉：觸發率判準必須連同【它作用在哪一個母體】一起報，同一條規則在兩個母體上可以得到相反的裁定。

⛔ **寫法限制**（K線分析線 0400 §二，逐字）：
  ① 結論、登錄、報告裡都**不得**把④型描述成「輸家」「地雷」「避雷」「排雷」。
  ② **不得**宣稱排除④能改善回落——④的 p10 最淺 ⇒ 排掉它理論上讓回落**變差一點**。
  ③ 要寫「排除④是為了把資金讓給①③」⇒ 它的驗收只能在**組合層**（有槽數限制的地方）。
⛔ 本件**不宣稱**④型的獨立性（只證明過它不是流動性代理，⛔ 沒排掉其他已知因子）。

⭐ 判準三行（策略線 1115 §三，⛔ 重跑前寫死、這次跑完就結案、⛔ 不再換第三組種子）：
  ① 判定量 ＝ 組合層【年化差】（排除④ − 不排除）在 N=8 上，200 顆種子 `default_rng(96000+r)`
     **逐種子配對**後取中位 ＋ 95% CI。⛔ CI 含 0 ⇒ 寫「排除④在組合層測不出」，
     ⛔ 不可回頭引用策略線前測那個單筆層 +0.38pp 當成「有效」。
  ② 通過門檻 ＝ 對 0050 的三條判準要【全窗＋A 窗＋B 窗三個都成立】；只有全窗成立 ⇒ 寫「僅全窗成立」，⛔ 不可寫「通過」。
  ③ 多重檢定 ＝ 本件 8 格（N ∈ {5,8,10,20} × 有／無排除④），虛無期望 0.05×8 ＝ 0.4 格
     ⇒ ⛔ 測得出的格數 ≤ 1 一律判「不超過雜訊期望」；判定只看 N=8 那 2 格。
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1
from . import researchp7 as P7

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp6")
SEED0 = 96000                # ⛔ 判準三行 ①：寫死，⛔ 不再換第三組種子
NS = (5, 8, 10, 20)          # 8 格 ＝ 4 個 N × 有／無排除④
N_JUDGE = 8                  # ⛔ 判定只看 N=8 那 2 格
DROP_TYPE = "④死水"
NULL_EXPECT = 0.05 * 8       # 虛無期望 0.4 格


def drop_type4(sig: pd.DataFrame, cl: pd.DataFrame, typ: str = DROP_TYPE) -> tuple[pd.DataFrame, dict]:
    """把 sig 裡歸型為 `typ` 的（股, 月）拿掉。回 (篩後 sig, 佔比三數)。

    ⭐〈九十二〉：佔比要連同母體一起報 ⇒ 這裡報的是【門檻B 池內】的佔比，
    ⛔ 不是全母體那個 40.2%（那個用法已經出局，見檔頭）。
    """
    key = cl.assign(month=cl["measure_date"].dt.strftime("%Y-%m"))[["stock_id", "month", "type"]]
    m = sig.merge(key, left_on=["sid", "month"], right_on=["stock_id", "month"], how="left")
    hit = (m["type"] == typ).to_numpy()
    kept = sig[~hit].reset_index(drop=True)
    info = {"pool_rows": int(len(sig)), "dropped_rows": int(hit.sum()),
            "dropped_share_pct": float(hit.mean() * 100) if len(sig) else np.nan,
            "unmatched_rows": int(m["type"].isna().sum())}
    return kept, info


def _pair_stats(a: pd.DataFrame, b: pd.DataFrame, col: str = "cagr") -> dict:
    """逐種子配對差（a − b）的中位與 95% CI（⛔ 配對，不是兩組各取中位再相減）。"""
    j = a[["seed", col]].merge(b[["seed", col]], on="seed", suffixes=("_x", "_y"))
    d = (j[f"{col}_x"] - j[f"{col}_y"]).to_numpy(float)
    n = len(d)
    med = float(np.median(d)) if n else np.nan
    se = float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
    mean = float(d.mean()) if n else np.nan
    return {"n_seeds": n, "diff_median": med, "diff_mean": mean,
            "ci_lo": mean - 1.96 * se if np.isfinite(se) else np.nan,
            "ci_hi": mean + 1.96 * se if np.isfinite(se) else np.nan,
            "detectable": bool(np.isfinite(se) and (mean - 1.96 * se) * (mean + 1.96 * se) > 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    ap.add_argument("--classified", default=os.path.join(HERE, "resultsp4", "classified.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = print
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens)
    cl = pd.read_csv(a.classified, parse_dates=["measure_date"], dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "type"])
    kept, info = drop_type4(sig, cl)
    log(f"[池] 門檻B {info['pool_rows']:,} 筆 ⇒ 排除{DROP_TYPE} {info['dropped_rows']:,} 筆"
        f"（池內 {info['dropped_share_pct']:.1f}%，⛔ 全母體那個 40.2% 是另一個用法）⇒ 剩 {len(kept):,} 筆"
        f"；歸型對不上的 {info['unmatched_rows']:,} 筆")
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    first_all = int(sig["entry_pos"].min())
    b_c, b_m = R13.window_stats(bench, first_all, ncal, first_all, ncal)
    b_ca, b_ma = R13.window_stats(bench, first_all, ncal, first_all, split_pos)
    b_cb, b_mb = R13.window_stats(bench, first_all, ncal, split_pos, ncal)
    log(f"[0050] 全窗 {b_c * 100:+.2f}%／{b_m * 100:.1f}%；A 窗 {b_ca * 100:+.2f}%／{b_ma * 100:.1f}%；B 窗 {b_cb * 100:+.2f}%／{b_mb * 100:.1f}%")
    rows = []; raw = {}
    for name, s_ in (("不排除④", sig), ("排除④", kept)):
        P7._S.clear()
        P7._init(s_, closes, opens, ncal, first_all, split_pos, ncal)
        for N in NS:
            res = pd.DataFrame([P7._one((N, None, SEED0 + r)) for r in range(a.reps)])
            raw[(name, N)] = res
            md = res.median(numeric_only=True)
            win_all = bool(md["cagr"] >= b_c and md["mdd"] > b_m)
            win_a = bool(md["ca"] >= b_ca and md["ma"] > b_ma)
            win_b = bool(md["cb"] >= b_cb and md["mb"] > b_mb)
            rows.append({"set": name, "N": N, "cagr": md["cagr"], "cagr_p10": res["cagr"].quantile(0.1), "cagr_p90": res["cagr"].quantile(0.9),
                         "mdd": md["mdd"], "slot": md["slot"], "m": md["m"], "ca": md["ca"], "ma": md["ma"], "cb": md["cb"], "mb": md["mb"],
                         "win_all": win_all, "win_a": win_a, "win_b": win_b, "win": bool(win_all and win_a and win_b)})
            log(f"  {name:<7} N={N:<3} 年化 {md['cagr'] * 100:+6.2f}% 回落 {md['mdd'] * 100:6.1f}% 筆數 {md['m']:.0f} "
                f"⇒ 全窗 {'✅' if win_all else '✗'}／A {'✅' if win_a else '✗'}／B {'✅' if win_b else '✗'}")
    T = pd.DataFrame(rows)
    pairs = []
    for N in NS:
        p_ = _pair_stats(raw[("排除④", N)], raw[("不排除④", N)], "cagr")
        p_m = _pair_stats(raw[("排除④", N)], raw[("不排除④", N)], "mdd")
        pairs.append({"N": N, **{f"cagr_{k}": v for k, v in p_.items()}, **{f"mdd_{k}": v for k, v in p_m.items()}})
        log(f"  [配對] N={N:<3} 年化差 中位 {p_['diff_median'] * 100:+.2f}pp、CI [{p_['ci_lo'] * 100:+.2f}, {p_['ci_hi'] * 100:+.2f}] "
            f"⇒ {'測得出' if p_['detectable'] else '⛔ CI 含 0 ⇒ 測不出'}")
    P = pd.DataFrame(pairs)
    T.to_csv(os.path.join(a.out, "cells.csv"), index=False); P.to_csv(os.path.join(a.out, "paired.csv"), index=False)
    n_det = int(P["cagr_detectable"].sum())
    judge = P[P["N"] == N_JUDGE].iloc[0]
    L = ["# PREREGP6：④型當門檻B 之後的第二道篩（回測線落地）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準＝策略線 PREREGP6（0810）＋1115 §三 的三行。",
         f"種子 `default_rng({SEED0} + r)` × {a.reps}；⛔ 這次跑完就結案，不再換第三組種子。", "",
         "⛔ 本規則**不曾**被登錄為獨立排除規則：④型佔**全母體** 40.2%（> 30% 紅線）已使該用法出局。",
         f"⇒ 本件只登錄【門檻B 池內的第二道篩】：池內 {info['dropped_rows']:,}／{info['pool_rows']:,} ＝ **{info['dropped_share_pct']:.1f}%**"
         f"（⭐〈九十二〉：佔比要連同母體一起報）。", "",
         "⛔ **寫法限制**（K線分析線 0400 §二）：④型**不是**「輸家／地雷」——它勝率 50.1% 高於②型、p10 最淺；"
         "⇒ ⛔ 不得宣稱排除它能改善回落（理論上會**變差一點**），⭐ 它是**機會成本規則**：排除④是為了把資金讓給①③。", "",
         f"**0050 買進持有**：全窗 {b_c * 100:+.2f}%／{b_m * 100:.1f}%；A 窗 {b_ca * 100:+.2f}%／{b_ma * 100:.1f}%；B 窗 {b_cb * 100:+.2f}%／{b_mb * 100:.1f}%。", "",
         "| 組 | N | 年化 中位 | p10～p90 | 最大回落 | 槽位 | 筆數 | 全窗 | A 窗 | B 窗 | 三窗全過 |",
         "|---|---:|---:|---|---:|---:|---:|:--:|:--:|:--:|:--:|"]
    for r in T.itertuples():
        L.append(f"| {r.set} | {r.N} | {r.cagr * 100:+.2f}% | {r.cagr_p10 * 100:+.1f}～{r.cagr_p90 * 100:+.1f} | {r.mdd * 100:.1f}% | "
                 f"{r.slot:.2f} | {r.m:.0f} | {'✅' if r.win_all else '✗'} | {'✅' if r.win_a else '✗'} | {'✅' if r.win_b else '✗'} | {'✅' if r.win else '⛔'} |")
    L += ["", "## ⭐ 判定量：逐種子配對的年化差（排除④ − 不排除）", "",
          "| N | 配對種子 | 年化差 中位 | 年化差 平均 | 95% CI | 測得出？ | 回落差 中位 |", "|---:|---:|---:|---:|---|:--:|---:|"]
    for r in P.itertuples():
        L.append(f"| {r.N} | {r.cagr_n_seeds} | {r.cagr_diff_median * 100:+.2f}pp | {r.cagr_diff_mean * 100:+.2f}pp | "
                 f"[{r.cagr_ci_lo * 100:+.2f}, {r.cagr_ci_hi * 100:+.2f}] | {'✅' if r.cagr_detectable else '⛔'} | {r.mdd_diff_median * 100:+.2f}pp |")
    L += ["", f"⭐ **判定（只看 N={N_JUDGE} 那 2 格）**：年化差中位 **{judge['cagr_diff_median'] * 100:+.2f}pp**、"
          f"95% CI [{judge['cagr_ci_lo'] * 100:+.2f}, {judge['cagr_ci_hi'] * 100:+.2f}] ⇒ "
          + ("**測得出**。" if judge["cagr_detectable"] else "**CI 含 0 ⇒ 排除④在組合層測不出**。"
             "⛔ 不可回頭引用策略線前測那個單筆層 +0.38pp 當成「有效」。"), "",
          f"⚠ 多重檢定：8 格裡測得出 **{n_det}** 格，虛無期望 {NULL_EXPECT:.1f} 格 ⇒ "
          + ("⛔ **不超過雜訊期望**（≤ 1）。" if n_det <= 1 else f"超過雜訊期望，⛔ 而判定仍只看 N={N_JUDGE}。"), ""]
    open(os.path.join(a.out, "P6_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"寫入 {os.path.join(a.out, 'P6_REPORT.md')}｜8 格裡測得出 {n_det} 格（虛無期望 {NULL_EXPECT:.1f}）")


if __name__ == "__main__":
    sys.exit(main())
