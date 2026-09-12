"""研究十三：G1（月營收創 24 月新高）× 3/5（相似度計分）疊加 ＋ 大盤濾網 ＋ 組合層對 0050。判準 backtest/PREREG10.md。

    python3 -m backtest.research13 [--procs 4] [--reps 200] [--out DIR] [--report-only]

出場引擎、月分群 CI、逐日市值組合層全部 import 研究十一（同一件事只有一份實作）。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results13")
COST = R.COST
RULES = ["H60", "H120", "LD"]
NS = [10, 20]
SETS = ["S", "G", "AND", "OR"]
SPLIT = "2021-01"
MA_REGIME = 200
STALE_MAX = 45     # AND：最新一期面板列距訊號日 ≤ 45 個交易日
_G: dict = {}


def _init(cal, gpos):
    _G["cal"] = cal; _G["gpos"] = gpos


def g_exits(args):
    """一檔：G1 訊號的 H60／H120／LD 出場（研究十一引擎），並回傳 closes／opens 給組合層。"""
    sid, market = args
    B = R.load_bars(sid, market, _G["cal"])
    if B is None:
        return None
    idx, o, c, dn, next_bad, df = B["idx"], B["o"], B["c"], B["dn"], B["next_bad"], B["df"]
    n = len(idx); month = B["dates"].strftime("%Y-%m")
    rows = []
    for sp in _G["gpos"].get(sid, ()):
        k = int(np.searchsorted(idx, sp))          # 訊號日或之後第一根有效 K 棒
        if k >= n or k + 1 >= n or k < 20:
            continue
        if idx[k] - sp > 5:
            continue                                # 訊號日後 5 個交易日內沒有有效 K 棒 ⇒ 不算
        nb = next_bad[max(0, k - 20)]
        if nb <= k:
            continue
        row = {"sid": sid, "k": k, "pos": int(idx[k]), "entry_pos": int(idx[k + 1]), "month": month[k], "g1_pos": int(sp)}
        for H in (60, 120):
            r = R.fixed_exit(o, c, k, H, nb); row[f"g_H{H}"] = r[1] if r else np.nan; row[f"xpos_H{H}"] = int(idx[r[0]]) if r else -1
        r = R.cond_exit(o, c, k, nb, lambda j: bool(dn[j]))
        row["g_LD"], row["xpos_LD"], row["t_LD"] = (r[1], int(idx[r[0]]), r[2]) if r else (np.nan, -1, False)
        rows.append(row)
    return {"sid": sid, "rows": rows,
            "close": pd.Series(df["close"].to_numpy()).ffill().to_numpy(np.float32), "open": df["open"].to_numpy(np.float32)}


def _p(x, d=2):
    return R._p(x, d)


def set_table(name, d, base, L):
    L.append(f"#### {name}（n＝{len(d):,}）"); L.append("")
    L.append("| 規則 | 期間 | n | 平均 | 中位 | 勝率 | 最壞 | p10 | 基準 | 超額 | 超額 月配對 95% CI | 統計層 |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for nm in RULES:
        for per in ("ALL", "A", "B"):
            m = R.period_mask(d["month"], per); dd = d[m]
            x = dd[f"g_{nm}"].to_numpy(float) - COST
            s = R.cl_stats(x, dd["month"].to_numpy())
            if s["n"] == 0:
                L.append(f"| {nm} | {per} | 0 | | | | | | | | | |"); continue
            if nm[0] == "H":
                H = int(nm[1:]); bm = base[H]["sum"] / base[H]["count"]
                ex = dd[f"g_{nm}"].to_numpy(float) - dd["month"].map(bm).to_numpy(float)
                se = R.cl_stats(ex, dd["month"].to_numpy())
                b = R.base_mean(base, H, set(dd["month"]))
                exs = f"{se['mean'] * 100:+.2f} pp"; ci = f"{se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f}"
                v = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
            else:
                b = np.nan; exs = "—"; ci = "—"; v = "—"
            L.append(f"| {nm} | {per} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['worst'])} | {_p(s['p10'])} | {_p(b)} | {exs} | {ci} | {v} |")
    L.append("")


def window_stats(eq, first, end, a, b):
    """權益曲線在 [a, b) 窗的年化與最大回落（窗與模擬區間取交集）。"""
    a = max(a, first); b = min(b, end)
    if b - a < 245:
        return np.nan, np.nan
    seg = eq[a:b]; years = (b - a) / 245
    cagr = (seg[-1] / seg[0]) ** (1 / years) - 1
    peak = np.maximum.accumulate(seg); mdd = float(((seg - peak) / peak).min())
    return cagr, mdd


_SIM: dict = {}


def _sim_one(args):
    """一個種子（fork 之後從 _SIM 讀共用資料，不逐工作 pickle 1,900 檔股價）。"""
    key, rule, N, seed, first_all, split_pos, end_all = args
    s = R.simulate_mtm(_SIM["pools"][key], rule, N, np.random.default_rng(seed), _SIM["closes"], _SIM["opens"], _SIM["ncal"], return_equity=True)
    eq = s["equity"]
    ca, ma_ = window_stats(eq, s["first"], s["end"], first_all, split_pos)
    cb, mb_ = window_stats(eq, s["first"], s["end"], split_pos, end_all)
    return {"cagr": s["cagr"], "mdd": s["mdd"], "calmar": s["cagr"] / abs(s["mdd"]) if s["mdd"] < 0 else np.nan,
            "slot": s["slot_use"], "trades": s["trades"], "ca": ca, "ma": ma_, "cb": cb, "mb": mb_,
            "equity": eq, "first": s["first"], "end": s["end"]}


def dd_episodes(eq, first, end, cal, top=3):
    """權益曲線的回落段：峰→谷→回到峰。回傳 [(峰日, 谷日, 深度, 回復日或 None)]，按深度排。"""
    seg = eq[first:end]; peak = np.maximum.accumulate(seg); dd = seg / peak - 1
    eps = []; i = 0; n = len(seg)
    while i < n:
        if dd[i] < 0:
            j = i
            while j < n and dd[j] < 0:
                j += 1
            k = i + int(np.argmin(dd[i:j]))
            eps.append((cal[first + i - 1].date(), cal[first + k].date(), float(dd[k]), cal[first + j].date() if j < n else None))
            i = j
        else:
            i += 1
    return sorted(eps, key=lambda e: e[2])[:top]


def report(S, G, AND, base, closes, opens, cal, bench, reps, and60, out, procs=4):
    ncal = len(cal); split_pos = int(cal.searchsorted(pd.Timestamp(SPLIT + "-01")))
    L = ["# 研究十三：G1 × 3/5 疊加 ＋ 大盤濾網 ＋ 組合層對 0050——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG10.md`。", ""]
    L.append(f"S 3/5 {len(S):,} 筆／{S['sid'].nunique():,} 檔；G G1 {len(G):,} 筆／{G['sid'].nunique():,} 檔（面板 rev_hi24 8,827 筆，研究十一引擎可算出場的）；"
             f"AND {len(AND):,} 筆／{AND['sid'].nunique():,} 檔（占 S {len(AND) / len(S) * 100:.1f}%）；AND-60 {len(and60):,} 筆；S∖AND {len(S) - len(AND):,} 筆。")
    # 訊號頻率
    L.append(f"訊號頻率（每月中位／最大）：S {S.groupby('month').size().median():.0f}／{S.groupby('month').size().max()}、G {G.groupby('month').size().median():.0f}／{G.groupby('month').size().max()}、AND {AND.groupby('month').size().median():.0f}／{AND.groupby('month').size().max()}"); L.append("")
    L.append("## 一、逐筆層"); L.append("")
    comp = S[~S.index.isin(AND.index)]
    for nm, d in (("S ＝ 3/5", S), ("G ＝ G1", G), ("AND ＝ 3/5 且最新一期營收創 24 月新高", AND), ("S∖AND", comp), ("AND-60（變數：前 60 根內有 G1 訊號日）", and60)):
        set_table(nm, d, base, L)
    # 安慰劑
    L.append("### 安慰劑：S 內隨機抽 |AND| 筆 200 次，H120 超額分佈"); L.append("")
    bm = base[120]["sum"] / base[120]["count"]
    exS = (S["g_H120"] - S["month"].map(bm)).to_numpy(float); okS = ~np.isnan(exS)
    real = float(np.nanmean((AND["g_H120"] - AND["month"].map(bm)).to_numpy(float)))
    rng = np.random.default_rng(13); draws = []
    for _ in range(200):
        pick = rng.choice(np.flatnonzero(okS), size=int(AND["g_H120"].notna().sum()), replace=False)
        draws.append(exS[pick].mean())
    draws = np.array(draws); pct = float((draws < real).mean() * 100)
    L.append(f"- 真 AND H120 超額 {real * 100:+.2f} pp；安慰劑 p5／p50／p95 ＝ {np.percentile(draws, 5) * 100:+.2f}／{np.percentile(draws, 50) * 100:+.2f}／{np.percentile(draws, 95) * 100:+.2f} pp；真值落在第 **{pct:.0f}** 百分位 ⇒ "
             + ("**超出 p95，疊加效果測得出**" if pct >= 95 else "**在安慰劑範圍內，疊加效果測不出**")); L.append("")
    # ── 組合層 ──
    L.append("## 二、組合層（200 種子、逐日收盤市值；判準 PREREG10 四）"); L.append("")
    # 濾網
    ma = pd.Series(bench).rolling(MA_REGIME, min_periods=MA_REGIME).mean().to_numpy()
    regime_ok = bench > ma
    L.append(f"大盤濾網：0050 還原收盤 > {MA_REGIME} 根 MA 的日子占 {np.nanmean(regime_ok[MA_REGIME:]) * 100:.0f}%。"); L.append("")
    pools = {"S": S, "G": G, "AND": AND, "OR": pd.concat([S, G], ignore_index=True)}
    # 0050 對照
    first_all = int(min(S["entry_pos"].min(), G["entry_pos"].min())); end_all = ncal
    b_c, b_m = window_stats(bench, first_all, end_all, first_all, end_all)
    b_ca, b_ma = window_stats(bench, first_all, end_all, first_all, split_pos)
    b_cb, b_mb = window_stats(bench, first_all, end_all, split_pos, end_all)
    L.append(f"**0050 買進持有**（{cal[first_all].date()} ～ {cal[end_all - 1].date()}）：年化 {b_c * 100:+.1f}%、最大回落 {b_m * 100:.1f}%；A 窗 {b_ca * 100:+.1f}%／{b_ma * 100:.1f}%；B 窗 {b_cb * 100:+.1f}%／{b_mb * 100:.1f}%。"); L.append("")
    L.append("| 集合 | 濾網 | N | 規則 | 年化 中位 | p10 ~ p90 | 最大回落 中位 | p10 ~ p90 | Calmar 中位 | A 窗 年化／回落 | B 窗 年化／回落 | 槽位 | 筆數 | 判定 |")
    L.append("|---|---|---:|---|---:|---|---:|---|---:|---|---|---:|---:|---|")
    wins = 0; total = 0; rows_out = []; dd_store = {}
    _SIM["closes"] = closes; _SIM["opens"] = opens; _SIM["ncal"] = ncal
    _SIM["pools"] = {(sname, reg): (pools[sname][regime_ok[pools[sname]["entry_pos"].to_numpy()]] if reg else pools[sname]) for sname in SETS for reg in (False, True)}
    pool = Pool(procs)   # fork：_SIM 已填好
    for sname in SETS:
        for reg in (False, True):
            for N in NS:
                for rule in RULES:
                    st = pool.map(_sim_one, [((sname, reg), rule, N, 1000 + r, first_all, split_pos, end_all) for r in range(reps)], chunksize=4)
                    cs = np.array([x["cagr"] for x in st]); med = st[int(np.argsort(cs)[len(cs) // 2])]
                    dd_store[(sname, reg, N, rule)] = (med["cagr"], dd_episodes(med["equity"], med["first"], med["end"], cal))
                    df = pd.DataFrame([{k: v for k, v in x.items() if k not in ("equity", "first", "end")} for x in st]); md_ = df.median(numeric_only=True)
                    win = (md_["cagr"] >= b_c and md_["mdd"] > b_m and md_["ca"] >= b_ca and md_["ma"] > b_ma and md_["cb"] >= b_cb and md_["mb"] > b_mb)
                    unstable = df["cagr"].quantile(0.10) < 0
                    total += 1; wins += int(win)
                    v = ("**贏過 0050**" if win else "沒贏") + ("（不穩：p10 年化 < 0）" if unstable else "")
                    L.append(f"| {sname} | {'有' if reg else '無'} | {N} | {rule} | **{md_['cagr'] * 100:+.1f}%** | {df['cagr'].quantile(0.1) * 100:+.1f} ~ {df['cagr'].quantile(0.9) * 100:+.1f}% | "
                             f"{md_['mdd'] * 100:.1f}% | {df['mdd'].quantile(0.1) * 100:.1f} ~ {df['mdd'].quantile(0.9) * 100:.1f}% | {md_['calmar']:.2f} | "
                             f"{md_['ca'] * 100:+.1f}%／{md_['ma'] * 100:.1f}% | {md_['cb'] * 100:+.1f}%／{md_['mb'] * 100:.1f}% | {md_['slot'] * 100:.0f}% | {md_['trades']:.0f} | {v} |")
                    rows_out.append({"set": sname, "regime": reg, "N": N, "rule": rule, **{k: float(md_[k]) for k in ("cagr", "mdd", "calmar", "ca", "ma", "cb", "mb", "slot", "trades")},
                                     "cagr_p10": float(df["cagr"].quantile(0.1)), "cagr_p90": float(df["cagr"].quantile(0.9)), "win": bool(win)})
                    print(f"  {sname} reg={reg} N={N} {rule}: {md_['cagr'] * 100:+.1f}% / {md_['mdd'] * 100:.1f}%", file=sys.stderr)
    L.append(""); L.append(f"**三條同時成立（全窗＋A 窗＋B 窗，年化不低於且回落較淺）的格數：{wins}／{total}。**"); L.append("")
    # 回落歸因（年化中位那個種子）
    L.append("## 三、最大回落歸因（每格取年化為中位數的那個種子；最深三段：峰日 → 谷日，深度，回到峰的日子）"); L.append("")
    b_eps = dd_episodes(bench, first_all, end_all, cal)
    L.append("- 0050：" + "；".join(f"{p_} → {t_} {d_ * 100:.1f}%（回復 {r_ or '未回復'}）" for p_, t_, d_, r_ in b_eps)); L.append("")
    L.append("| 集合 | 濾網 | N | 規則 | 種子年化 | 第 1 深 | 第 2 深 | 第 3 深 |"); L.append("|---|---|---:|---|---:|---|---|---|")
    for sname in SETS:
        for reg in (False, True):
            for N in NS:
                for rule in RULES:
                    mc, eps = dd_store[(sname, reg, N, rule)]
                    cells = [f"{p_} → {t_} **{d_ * 100:.1f}%**（{r_ or '未回復'}）" for p_, t_, d_, r_ in eps] + ["", "", ""]
                    L.append(f"| {sname} | {'有' if reg else '無'} | {N} | {rule} | {mc * 100:+.1f}% | {cells[0]} | {cells[1]} | {cells[2]} |")
    pool.close(); pool.join()
    pd.DataFrame(rows_out).to_csv(os.path.join(out, "portfolio.csv"), index=False)
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def and_flags(S, panel):
    """AND：訊號日當下最新一期面板列（signal_pos ≤ pos、距離 ≤ STALE_MAX）rev_hi24；AND-60：前 60 個交易日內有 G1 訊號日。回傳兩個 bool 陣列。"""
    p = panel.sort_values(["stock_id", "signal_pos"])
    flags = np.zeros(len(S), bool); and60 = np.zeros(len(S), bool)
    by = {sid: (g["signal_pos"].to_numpy(), g["rev_hi24"].to_numpy(bool)) for sid, g in p.groupby("stock_id")}
    for i, (sid, pos) in enumerate(zip(S["sid"], S["pos"])):
        if sid not in by:
            continue
        sp, hi = by[sid]
        j = int(np.searchsorted(sp, pos, side="right")) - 1
        if j >= 0 and pos - sp[j] <= STALE_MAX and hi[j]:
            flags[i] = True
        # 前 60 個交易日（日曆位置）內有 G1 訊號日
        lo = int(np.searchsorted(sp, pos - 60)); hi_j = int(np.searchsorted(sp, pos, side="right"))
        if hi[lo:hi_j].any():
            and60[i] = True
    return flags, and60


def build_sets(cal, panel):
    S = pd.read_csv(os.path.join(HERE, "results11", "signals.csv.gz"), dtype={"sid": str})
    S = S[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    flags, and60 = and_flags(S, panel)
    return S, S[flags].copy(), S[and60].copy()


def main():
    global RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=None); ap.add_argument("--report-only", action="store_true"); ap.add_argument("--limit", type=int)
    ap.add_argument("--sets", nargs="*", default=None, help="只跑這些集合（預設 S G AND OR）")
    ap.add_argument("--ns", nargs="*", type=int, default=None, help="槽數（預設 10 20）")
    ap.add_argument("--g1-from", default=None, help="--report-only 時 g1_signals.csv.gz 所在目錄（預設 --out）")
    a = ap.parse_args()
    if a.out:
        RESULTS = a.out
    os.makedirs(RESULTS, exist_ok=True)
    t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe(); ncal = len(cal)
    panel = pd.read_csv(os.path.join(HERE, "results3", "panel.csv.gz"), dtype={"stock_id": str})
    panel["rev_hi24"] = panel["rev_hi24"].fillna(False).astype(bool)   # 面板裡沒有 24 期歷史的列是 NaN ＝ 不算創高
    S, AND, and60 = build_sets(cal, panel)
    bm = pd.read_csv(os.path.join(HERE, "results11", "baseline_months.csv"), dtype={"month": str}).set_index(["hold", "month"])
    base = {H: bm.loc[H] for H in (60, 120)}
    bench_st = D.load_stock("0050", "twse", cal)
    bench = pd.Series(bench_st.df["close"].to_numpy()).ffill().to_numpy(float)
    gpos = {sid: g["signal_pos"].to_numpy() for sid, g in panel[panel["rev_hi24"]].groupby("stock_id")}
    if a.report_only:
        G = pd.read_csv(os.path.join(a.g1_from or RESULTS, "g1_signals.csv.gz"), dtype={"sid": str})
        closes, opens = {}, {}
        mk = uni.set_index("stock_id")["market"]
        for sid in set(S["sid"]) | set(G["sid"]):
            st = D.load_stock(sid, mk.get(sid, "twse"), cal)
            closes[sid] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(np.float32); opens[sid] = st.df["open"].to_numpy(np.float32)
    else:
        tasks = [(r.stock_id, r.market) for r in uni.itertuples()]
        if a.limit:
            tasks = tasks[: a.limit]
        rows = []; closes = {}; opens = {}
        with Pool(a.procs, initializer=_init, initargs=(cal, gpos)) as pool:
            for i, r in enumerate(pool.imap_unordered(g_exits, tasks, chunksize=8)):
                if r is None:
                    continue
                rows.extend(r["rows"]); closes[r["sid"]] = r["close"]; opens[r["sid"]] = r["open"]
                if (i + 1) % 400 == 0:
                    print(f"  {i + 1}/{len(tasks)} {time.time() - t0:.0f}s", file=sys.stderr)
        G = pd.DataFrame(rows)
        G.to_csv(os.path.join(RESULTS, "g1_signals.csv.gz"), index=False)
        print(f"G1 出場算完 {len(G):,} 筆，{time.time() - t0:.0f}s", file=sys.stderr)
    if a.limit:
        keep = set(closes)
        S = S[S["sid"].isin(keep)]; AND = AND[AND["sid"].isin(keep)]; and60 = and60[and60["sid"].isin(keep)]
    AND.to_csv(os.path.join(RESULTS, "and_signals.csv.gz"), index=False)
    global SETS, NS
    if a.sets:
        SETS = a.sets
    if a.ns:
        NS = a.ns
    report(S, G, AND, base, closes, opens, cal, bench, a.reps, and60, RESULTS, a.procs)
    print(f"完成 {time.time() - t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
