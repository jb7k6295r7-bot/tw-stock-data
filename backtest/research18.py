"""研究十八：快速噴出後該不該提早停利（X0～X3 × 快慢組）＋ 收盤位置 p 在突破根上。判準 backtest/PREREG18.md。

    python3 -m backtest.research18 [--procs 4] [--limit N] [--reps 2000]

訊號集 ＝ results11/signals.csv.gz 主格 cell 30|3|20（研究十一 3/5）；K 棒／CI：research11；bootstrap：research16。
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
from . import research16 as R16

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results18")
R11DIR = os.path.join(HERE, "results11")
COST = R.COST
LIQ = 5e7
FAST_BARS = 15; TARGET = 0.20; HOLD_AFTER = 40; MA_TRAIL = 50; CAP3 = 120
HOLDS = (60, 120)
G_THR = {"G1": 0.618, "G2": 0.5, "G3": 0.75, "G4": 0.80}
_G: dict = {}


def _init(cal):
    R._init(cal); _G["cal"] = cal


def worker(args):
    sid, market, ks = args
    B = R.load_bars(sid, market, _G["cal"])
    if B is None:
        return [{"rid": rid, "err": "no_bars"} for _, rid in ks]
    o, c, h, l, next_bad = (B[x] for x in ("o", "c", "h", "l", "next_bad"))
    n = len(c); ma50 = pd.Series(c).rolling(MA_TRAIL).mean().to_numpy(float); a20 = R16.atr20_simple(h, l, c)
    out = []
    for k, rid in ks:
        if k + 1 >= n or not (o[k + 1] > 0):
            out.append({"rid": rid, "err": "no_entry"}); continue
        ep = o[k + 1]; nb = next_bad[k + 1]
        row = {"rid": rid, "entry": float(ep)}
        # 觸及 +20%（收盤）與盤中版
        tc = next((t for t in range(k + 1, n) if c[t] >= ep * (1 + TARGET)), -1)
        th = next((t for t in range(k + 1, n) if h[t] >= ep * (1 + TARGET)), -1)
        row["t_close"] = tc; row["t_high"] = th
        row["fast"] = bool(tc >= 0 and tc <= k + FAST_BARS); row["fast_i"] = bool(th >= 0 and th <= k + FAST_BARS)
        def g(x):
            return c[x] / ep - 1 if (x < n and x < nb) else np.nan
        for H in HOLDS:
            row[f"X0_H{H}"] = g(k + H)
        if tc >= 0:
            row["X1"] = g(tc); row["X2"] = g(tc + HOLD_AFTER)
            u = next((u for u in range(tc + 1, min(tc + CAP3, n - 1) + 1) if np.isfinite(ma50[u]) and c[u] < ma50[u]), min(tc + CAP3, n - 1))
            row["X3"] = g(u); row["X3_bars"] = u - k
        else:
            for H in HOLDS:
                pass
            row["X1"] = np.nan; row["X2"] = np.nan; row["X3"] = np.nan; row["X3_bars"] = np.nan
        hl = h[k] - l[k]
        row["lock"] = bool(hl <= 0); row["p"] = ((c[k] - l[k]) / hl) if hl > 0 else (1.0 if (k > 0 and c[k] >= c[k - 1]) else 0.0)
        row["amp_ok"] = bool(np.isfinite(a20[k]) and hl >= 0.5 * a20[k])
        out.append(row)
    return out


def _p(x, d=2):
    return R._p(x, d)


def _ci(s):
    return f"{s['mean'] * 100:+.2f} pp（{s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}）⇒ {'測不出' if s['lo'] <= 0 <= s['hi'] else '測得出'}"


def stats_line(name, x, m, base_m=None):
    x = np.asarray(x, float); m = np.asarray(m); ok = ~np.isnan(x); x, m = x[ok], m[ok]
    if len(x) == 0:
        return f"| {name} | 0 | | | | | | |"
    s = R.cl_stats(x - COST, m)
    ex = ""
    if base_m is not None:
        e = x - pd.Series(m).map(base_m).to_numpy(float); se = R.cl_stats(e, m)
        ex = f" {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} |"
    return f"| {name} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['p10'])} | {_p(s['worst'])} |{ex}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--limit", type=int); ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True); t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe().set_index("stock_id")["market"]
    S = pd.read_csv(os.path.join(R11DIR, "signals.csv.gz"), dtype={"sid": str}, low_memory=False)
    S = S[(S["cell"] == "30|3|20") & (S["liq"] >= LIQ)].copy(); S["rid"] = np.arange(len(S))
    bl = pd.read_csv(os.path.join(R11DIR, "baseline_months.csv"))
    base_m = {H: (bl[bl.hold == H].set_index("month")["sum"] / bl[bl.hold == H].set_index("month")["count"]) for H in (20, 60, 120) if (bl.hold == H).any()}
    if a.limit:
        S = S[S["sid"].isin(S["sid"].unique()[:a.limit])]
    jobs = [(sid, uni.get(sid), [(int(k), int(rid)) for k, rid in zip(g["k"], g["rid"])]) for sid, g in S.groupby("sid")]
    rows = []
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, jobs, chunksize=8)):
            rows.extend(r)
            if (i + 1) % 300 == 0:
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s", file=sys.stderr)
    P = pd.DataFrame(rows); err = P[P.get("err").notna()] if "err" in P else P.iloc[0:0]
    P = P[P.get("err").isna()] if "err" in P else P
    M = S.merge(P, on="rid", how="inner"); M.to_csv(os.path.join(RESULTS, "rows.csv.gz"), index=False)
    L = ["# 研究十八：快速噴出後的出場＋p 在突破根上——細表", "", f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG18.md`。訊號集 ＝ 研究十一 3/5 主格、liq ≥ 5,000 萬。", ""]
    # 對帳
    both = M["X0_H60"].notna() & M["g_H60"].notna(); mism = int((np.abs(M.loc[both, "X0_H60"] - M.loc[both, "g_H60"]) > 1e-9).sum())
    L.append(f"## 〇、對帳：研究十一 3/5 主格 {len(S):,} 筆（liq ≥ 5,000 萬），可算 {len(M):,}；X0_H60 重算 vs 研究十一 g_H60 可比 {int(both.sum()):,}、不等 {mism}（{'✓' if mism == 0 else '⛔'}）"); L.append("")
    if mism > 0:
        open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L)); print("⛔ 對帳不過"); sys.exit(1)
    fast = M[M.fast]; slow = M[~M.fast]
    L.append(f"## 一、快組／慢組：15 根內收盤 ≥ +20%：快組 {len(fast):,}（{len(fast) / len(M) * 100:.1f}%）、慢組 {len(slow):,}；盤中版快組 {int(M.fast_i.sum()):,}。慢組裡日後（任何時候）觸及 +20% 的 {int(slow.t_close.ge(0).sum()):,} 筆"); L.append("")
    k_sig = 0
    for lab, d in (("快組", fast), ("慢組", slow)):
        L.append(f"### {lab}（n＝{len(d):,}）"); L.append("")
        L.append("| 規則 | n | 平均 | 中位 | 勝率 | p10 | 最壞 | 超額(H60 基準) | CI |"); L.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
        L.append(stats_line("X0 主格 H60", d["X0_H60"], d["month"], base_m.get(60)))
        L.append(stats_line("X0 H120", d["X0_H120"], d["month"], base_m.get(120)))
        for nm, col in (("X1 觸及 +20% 當天出", "X1"), ("X2 觸及後再持有 40 根", "X2"), ("X3 觸及後 MA50 追蹤（上限 120）", "X3")):
            L.append(stats_line(nm, d[col], d["month"]))
        L.append("")
        L.append("配對（同筆差、月分群 CI；X1～X3 沒觸及者退化成 X0，慢組要看這一行的 n）：")
        for nm, col in (("X2 − X1", "X2"), ("X3 − X1", "X3"), ("X0(H60) − X1", "X0_H60")):
            pr = d[d["X1"].notna() & d[col].notna()]
            s = R.cl_stats((pr[col] - pr["X1"]).to_numpy(float), pr["month"].to_numpy())
            k_sig += int(s.get("n", 0) > 0 and not (s["lo"] <= 0 <= s["hi"]))
            L.append(f"- {nm}：{_ci(s) if s.get('n') else 'n 0'}（n {s.get('n', 0):,}）")
        if len(d) and d["X3_bars"].notna().any():
            L.append(f"- X3 平均持有 {d['X3_bars'].mean():.0f} 根（含觸及前）；X1 觸及日距進場中位 {(d['t_close'] - d['k']).median():.0f} 根")
        L.append("")
    # p 在突破根上
    L.append("## 二、p 在突破根上（3/5 訊號根；H20 主判定，另報 H60；格 − 補集 ＝ 月分群 bootstrap）"); L.append("")
    nlock = int(M["lock"].sum())
    L.append(f"high == low 鎖死 {nlock:,} 筆（{nlock / len(M) * 100:.1f}%）；A 案 p ∈ {{0,1}}、B 案另列。"); L.append("")
    for H in (20, 60):
        col = f"g_H{H}"; bm = base_m.get(H)
        L.append(f"#### H{H}"); L.append("")
        L.append("| 格 | 版 | n | 砍掉 | 平均 | 中位 | 超額 | CI | 格 − 補集 | CI | 判 |"); L.append("|---|---|---:|---:|---:|---:|---:|---|---:|---|---|")
        for case, dd in (("A", M), ("B", M[~M["lock"]])):
            for gname, thr in [("G0", None)] + list(G_THR.items()):
                for ver in ("a", "b"):
                    if gname == "G0" and ver == "b":
                        continue
                    m = pd.Series(True, index=dd.index) if thr is None else (dd["p"] >= thr)
                    if ver == "b":
                        m = m & dd["amp_ok"]
                    sub, comp = dd[m], dd[~m]
                    x = sub[col].to_numpy(float); ok = ~np.isnan(x)
                    if ok.sum() == 0:
                        continue
                    se = R.cl_stats(x[ok] - sub["month"].map(bm).to_numpy(float)[ok], sub["month"].to_numpy()[ok]) if bm is not None else {"mean": np.nan, "lo": np.nan, "hi": np.nan, "n": int(ok.sum())}
                    bd = R16.boot_diff(x, sub["month"].to_numpy(), comp[col].to_numpy(float), comp["month"].to_numpy(), reps=a.reps) if len(comp) else {}
                    bds = f"{bd['mean'] * 100:+.2f} pp | {bd['lo'] * 100:+.2f} ~ {bd['hi'] * 100:+.2f} | {'測不出' if bd['lo'] <= 0 <= bd['hi'] else '測得出'}" if "mean" in bd else "— | — | —"
                    if H == 20 and case == "A" and gname != "G0" and "mean" in bd:
                        k_sig += int(not (bd["lo"] <= 0 <= bd["hi"]))
                    L.append(f"| {gname} | {case}{ver} | {int(ok.sum()):,} | {(1 - len(sub) / len(dd)) * 100:.0f}% | {_p(np.nanmean(x) - COST)} | {_p(np.nanmedian(x) - COST)} | {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | {bds} |")
            if case == "B":
                lk = M[M["lock"]]; x = lk[col].to_numpy(float); ok = ~np.isnan(x)
                if ok.sum():
                    se = R.cl_stats(x[ok] - lk["month"].map(bm).to_numpy(float)[ok], lk["month"].to_numpy()[ok])
                    L.append(f"| 鎖死 | B | {int(ok.sum()):,} | — | {_p(np.nanmean(x) - COST)} | {_p(np.nanmedian(x) - COST)} | {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | | | |")
        L.append("")
    L.append(f"## 三、格數：14 格（快慢組配對 6 ＋ p H20 A 案 8）、測得出 {k_sig} 格、雜訊期望 0.7")
    open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L))
    print(f"完成 {time.time() - t0:.0f}s → {RESULTS}/summary.md；測得出 {k_sig}/14", file=sys.stderr)


if __name__ == "__main__":
    main()
