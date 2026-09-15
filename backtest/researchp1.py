"""PREREGP1：組合層——存量槽數 N 下探（2／3／8）與每日新增上限 d 的成本。判準 backtest/PREREGP1.md（策略線登錄、K線分析 0715 過目、回測線落地）。

    python3 -m backtest.researchp1 --regress            # 只跑回歸（R0～R3），任一格不過就 exit 1
    python3 -m backtest.researchp1 [--sets AND S] [--reps 200] [--procs 4] [--out DIR]

引擎 ＝ research11.simulate_mtm（PREREGP1 加了 d_max／pick／log／queue_days，預設值下與原版逐位元相同）；
視窗統計 ＝ research13.window_stats；月分群 CI ＝ research11.cl_stats。同一件事只有一份實作。
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
from . import research13 as R13

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp1")
REG = os.path.join(RESULTS, "regress")
COST = R.COST
HOLDS = (20, 60, 120)
NS_A = [2, 3, 5, 8, 10, 20, 30, 40]
DS_B = [1, 2, 3]                       # d＝∞ 那兩格已在 4-A（N＝8）
RULES = ["null", "relvol"]
SEED0 = 7000
QUEUE = 5                              # 回測線定的：被 b 擋掉的訊號最多再等 5 個交易日
_G: dict = {}
_SIM: dict = {}


# ── 逐檔特徵：relvol（兩集合）＋ AND 的 H20 ──
def _init(cal):
    R._init(cal); _G["cal"] = cal


def feat_worker(args):
    sid, market, ks_all, ks_and = args
    B = R.load_bars(sid, market, _G["cal"])
    if B is None:
        return {"sid": sid, "missing": True}
    idx, o, c, amt, next_bad = B["idx"], B["o"], B["c"], B["amt"], B["next_bad"]
    n = len(idx); out = {"sid": sid, "missing": False, "relvol": {}, "h20": {}, "mismatch": 0}
    for k, pos in ks_all:
        if k >= n or int(idx[k]) != int(pos):
            out["mismatch"] += 1; continue
        if k >= 60:
            med = float(np.nanmedian(amt[k - 60:k]))
            out["relvol"][k] = float(amt[k]) / med if med > 0 and np.isfinite(amt[k]) else np.nan
        else:
            out["relvol"][k] = np.nan
    for k in ks_and:
        if k >= n:
            continue
        nb = next_bad[max(0, k - 20)]                    # 與 research13.g_exits 相同的壞根口徑
        r = R.fixed_exit(o, c, k, 20, nb) if nb > k else None
        out["h20"][k] = (r[1], int(idx[r[0]])) if r else (np.nan, -1)
    return out


def attach_features(AND, S, cal, uni, procs):
    ks = {}
    for df, is_and in ((AND, True), (S, False)):
        for sid, g in df.groupby("sid"):
            e = ks.setdefault(sid, {"all": set(), "and": set()})
            e["all"].update(zip(g["k"].astype(int), g["pos"].astype(int)))
            if is_and:
                e["and"].update(g["k"].astype(int))
    tasks = [(sid, uni.get(sid, "twse"), sorted(v["all"]), sorted(v["and"])) for sid, v in ks.items()]
    rel = {}; h20 = {}; missing = []; mism = 0
    with Pool(procs, initializer=_init, initargs=(cal,)) as pool:
        for r in pool.imap_unordered(feat_worker, tasks, chunksize=16):
            if r["missing"]:
                missing.append(r["sid"]); continue
            mism += r["mismatch"]
            for k, v in r["relvol"].items():
                rel[(r["sid"], k)] = v
            for k, v in r["h20"].items():
                h20[(r["sid"], k)] = v
    for df in (AND, S):
        df["relvol"] = [rel.get((s, int(k)), np.nan) for s, k in zip(df["sid"], df["k"])]
    AND["g_H20"] = [h20.get((s, int(k)), (np.nan, -1))[0] for s, k in zip(AND["sid"], AND["k"])]
    AND["xpos_H20"] = [h20.get((s, int(k)), (np.nan, -1))[1] for s, k in zip(AND["sid"], AND["k"])]
    return missing, mism


def load_prices(sids, cal, uni):
    cp, op = os.path.join(REG, "closes.npz"), os.path.join(REG, "opens.npz")
    if os.path.exists(cp) and os.path.exists(op):
        cz, oz = np.load(cp), np.load(op)
        closes = {k: cz[k] for k in cz.keys()}; opens = {k: oz[k] for k in oz.keys()}
        if set(sids) <= set(closes):
            return closes, opens
    closes, opens = {}, {}
    for sid in sorted(set(sids)):
        st = D.load_stock(sid, uni.get(sid, "twse"), cal)
        if st is None:
            continue
        closes[sid] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(np.float32); opens[sid] = st.df["open"].to_numpy(np.float32)
    os.makedirs(REG, exist_ok=True)
    np.savez_compressed(cp, **closes); np.savez_compressed(op, **opens)
    return closes, opens


# ── 回歸 ──
def regress(AND, S, closes, opens, cal, uni, ncal):
    ok = True
    def chk(cond, msg):
        nonlocal ok
        print(("  ✓ " if cond else "  ✗ ") + msg, flush=True); ok = ok and bool(cond)
    # R1 逐種子逐格重現改引擎前的基線
    for name, sig, base_f, Ns, rules, seed0 in (("S", S, "baseline_S.npz", (5, 10, 20), ("H20", "H60", "H120", "LD"), 3000),
                                                  ("AND", AND, "baseline_AND.npz", (10, 20, 30, 40), ("H60", "H120", "LD"), 1000)):
        p = os.path.join(REG, base_f)
        if not os.path.exists(p):
            chk(False, f"R1 {name}：基線 {base_f} 不存在（先用改動前的引擎跑 p1_baseline）"); continue
        z = np.load(p)
        for N in Ns:
            for rule in rules:
                st = [R.simulate_mtm(sig, rule, N, np.random.default_rng(seed0 + r), closes, opens, ncal) for r in range(200)]
                same = all(np.array_equal(np.array([x[key] for x in st], float), z[f"{name}_{N}_{rule}_{key}"]) for key in ("cagr", "mdd", "slot_use", "trades"))
                chk(same, f"R1 {name} N={N} {rule}：200 種子 cagr/mdd/slot/trades 與基線逐位元相同")
    # R2 對 results13_adj0914（同日、同 adj、同種子）完全相等；對 13b／研究十一 ±1 pp
    p13 = os.path.join(HERE, "results13_adj0914", "portfolio.csv")
    if os.path.exists(p13):
        ref = pd.read_csv(p13); ref = ref[(ref.set == "AND") & (~ref.regime)]
        for N in (10, 20):
            for rule in ("H60", "H120", "LD"):
                st = pd.DataFrame([R.simulate_mtm(AND, rule, N, np.random.default_rng(1000 + r), closes, opens, ncal) for r in range(200)])
                row = ref[(ref.N == N) & (ref.rule == rule)].iloc[0]
                chk(abs(st["cagr"].median() - row["cagr"]) < 1e-9 and abs(st["mdd"].median() - row["mdd"]) < 1e-9, f"R2 AND N={N} {rule}：中位 cagr/mdd 與 results13_adj0914 相等（{st['cagr'].median() * 100:+.1f}% / {row['cagr'] * 100:+.1f}%）")
    p13b = os.path.join(HERE, "results13b", "portfolio.csv")
    if os.path.exists(p13b):
        ref = pd.read_csv(p13b); ref = ref[(ref.set == "AND") & (~ref.regime)]
        for N in (30, 40):
            st = pd.DataFrame([R.simulate_mtm(AND, "H60", N, np.random.default_rng(1000 + r), closes, opens, ncal) for r in range(200)])
            row = ref[(ref.N == N) & (ref.rule == "H60")].iloc[0]
            chk(abs(st["cagr"].median() - row["cagr"]) < 0.01, f"R2 AND N={N} H60：對 results13b ±1 pp（{st['cagr'].median() * 100:+.1f}% / {row['cagr'] * 100:+.1f}%，價格改版容忍）")
    # R3 合成：每天 10 個訊號、N＝8
    n_days = 60; sids = [f"X{i}" for i in range(10)]
    cz = {s: np.full(80, 1.0, np.float32) for s in sids}; oz = {s: np.full(80, 1.0, np.float32) for s in sids}
    rows = [{"sid": s, "entry_pos": t, "xpos_H60": t + 5, "g_H60": 0.01, "month": f"2020-{1 + t // 30:02d}"} for t in range(1, n_days + 1) for s in sids]
    syn = pd.DataFrame(rows)
    lg = []; o1 = R.simulate_mtm(syn, "H60", 8, np.random.default_rng(1), cz, oz, 80, log=lg)
    L1 = pd.DataFrame(lg); day1 = L1[(L1.t == 1) & (L1.reason == "in")]
    chk(len(day1) == 8 and (L1[L1.t == 1].reason == "a").sum() == 2, f"R3 d=∞：第一天進 8、槽滿擋 2（進 {len(day1)}、a {(L1[L1.t == 1].reason == 'a').sum()}）")
    lg = []; o2 = R.simulate_mtm(syn, "H60", 8, np.random.default_rng(1), cz, oz, 80, log=lg, d_max=1)
    L2 = pd.DataFrame(lg); per_day = L2[L2.reason == "in"].groupby("t").size()
    chk(per_day.max() == 1 and (L2.reason == "b").sum() > 0, f"R3 d=1：每天新增 ≤ 1（最大 {per_day.max()}）、b 擋掉 {(L2.reason == 'b').sum()} 筆")
    lg = []; o3 = R.simulate_mtm(syn, "H60", 8, np.random.default_rng(1), cz, oz, 80, log=lg, d_max=1, queue_days=QUEUE)
    L3 = pd.DataFrame(lg); dl = L3[(L3.reason == "in") & (L3.delay > 0)]["delay"]
    chk(o3["deferred"] > 0 and dl.min() >= 1 and dl.max() <= QUEUE and o3["expired"] > 0, f"R3 隊列：推遲進場 {o3['deferred']} 筆、delay ∈ [{dl.min() if len(dl) else '-'},{dl.max() if len(dl) else '-'}]、b_expired {o3['expired']}")
    chk(o1["trades"] == o1["m"] and 0 <= o1["pos_frac"] <= 1, "R3 輸出鍵 m／pos_frac")
    # R0 股息口徑：還原 close 的變動率 ＝ 原始變動率 ÷ 因子
    rng = np.random.default_rng(0); n_ok = 0; tried = 0
    cands = [s for s in sorted(AND["sid"].unique()) if os.path.exists(os.path.join(D.DATA, "adj", f"{s}.csv"))]
    for sid in rng.permutation(cands)[:40]:
        adj = D.load_adj(sid)
        ev = adj[adj["kind"].astype(str).isin(["息", "除息"])]
        if ev.empty:
            continue
        st = D.load_stock(sid, uni.get(sid, "twse"), cal)
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"])
        raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")["close"].astype(float)
        e = pd.Timestamp(ev.iloc[len(ev) // 2]["date"]); f = float(ev.iloc[len(ev) // 2]["factor"])
        pos = int(cal.searchsorted(e))
        if pos >= len(cal) or cal[pos] != e or pos == 0 or e not in raw.index or cal[pos - 1] not in raw.index:
            continue
        a1, a0 = float(st.df["close"].iloc[pos]), float(st.df["close"].iloc[pos - 1]); r1, r0 = float(raw[e]), float(raw[cal[pos - 1]])
        if not (a0 > 0 and r0 > 0 and np.isfinite(a1) and np.isfinite(r1)):
            continue
        tried += 1; n_ok += int(abs((a1 / a0) - r1 / (r0 * f)) < 1e-4)
        if tried >= 5:
            break
    chk(tried == 5 and n_ok == 5, f"R0 股息口徑：5 檔「息」事件日 還原變動率 ＝ 原始變動率 ÷ 因子（{n_ok}/{tried}）")
    return ok


# ── 模擬 ──
def _sim_init(sig, closes, opens, ncal, first_all, split_pos, end_all):
    _SIM.update(sig=sig, closes=closes, opens=opens, ncal=ncal, first_all=first_all, split_pos=split_pos, end_all=end_all)


def _diffs(L):
    """log → 進場組 − 擋掉組（排除 c）的三個持有期平均差（給 200 種子的分佈用）。"""
    if L is None or not len(L):
        return {f"diff_H{H}": np.nan for H in HOLDS}
    df = pd.DataFrame(L); ent = df[df.reason == "in"]; blk = df[df.reason.isin(["a", "b", "b_expired"])]
    return {f"diff_H{H}": (ent[f"g_H{H}"].mean() - blk[f"g_H{H}"].mean()) if (f"g_H{H}" in df and len(blk) and len(ent)) else np.nan for H in HOLDS}


def _sim_one(args):
    N, d, rule, seed, want_log = args
    lg = []
    s = R.simulate_mtm(_SIM["sig"], "H60", N, np.random.default_rng(seed), _SIM["closes"], _SIM["opens"], _SIM["ncal"], return_equity=True,
                       d_max=d, pick=None if rule == "null" else "relvol", log=lg, queue_days=QUEUE if d is not None else 0)
    ca, ma = R13.window_stats(s["equity"], s["first"], s["end"], _SIM["first_all"], _SIM["split_pos"])
    cb, mb = R13.window_stats(s["equity"], s["first"], s["end"], _SIM["split_pos"], _SIM["end_all"])
    out = {"seed": seed, "cagr": s["cagr"], "mdd": s["mdd"], "slot": s["slot_use"], "m": s["m"], "pos_frac": s["pos_frac"],
           "deferred": s["deferred"], "delay_med": s["delay_med"], "expired": s["expired"], "ca": ca, "ma": ma, "cb": cb, "mb": mb, **_diffs(lg)}
    if want_log:
        out["log"] = lg
    return out


def group_stats(L, H):
    """4-C：各去向的 g_H 平均／中位／月分群 CI／n／有效月數；差值 ＝ in − 擋掉（排除 c），SE 取兩組平方和。"""
    df = pd.DataFrame(L); col = f"g_H{H}"
    if col not in df:
        return None
    groups = {"in": df[df.reason == "in"], "a": df[df.reason == "a"], "b": df[df.reason == "b"], "b_expired": df[df.reason == "b_expired"],
              "c": df[df.reason == "c"], "blocked_ex_c": df[df.reason.isin(["a", "b", "b_expired"])], "blocked_all": df[df.reason != "in"]}
    res = {}
    for nm, g in groups.items():
        g = g.dropna(subset=[col])
        if len(g) == 0:
            res[nm] = {"n": 0}; continue
        s = R.cl_stats(g[col].to_numpy(float), g["month"].to_numpy())
        res[nm] = {"n": s["n"], "mean": s["mean"], "median": s["median"], "lo": s["lo"], "hi": s["hi"], "se": (s["hi"] - s["lo"]) / 3.92, "months": int(g["month"].nunique())}
    a, b = res["in"], res["blocked_ex_c"]
    if a.get("n", 0) and b.get("n", 0):
        dm = a["mean"] - b["mean"]; se = float(np.sqrt(a["se"] ** 2 + b["se"] ** 2))
        res["diff"] = {"mean": dm, "lo": dm - 1.96 * se, "hi": dm + 1.96 * se, "months": min(a["months"], b["months"])}
    return res


def fmt_pct(x, d=1):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def run_set(name, sig, closes, opens, cal, bench, reps, procs, out_dir):
    ncal = len(cal); split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    first_all = int(sig["entry_pos"].min()); end_all = ncal
    b_c, b_m = R13.window_stats(bench, first_all, end_all, first_all, end_all)
    b_ca, b_ma = R13.window_stats(bench, first_all, end_all, first_all, split_pos)
    b_cb, b_mb = R13.window_stats(bench, first_all, end_all, split_pos, end_all)
    configs = [(N, None, rule) for N in NS_A for rule in RULES] + [(8, d, rule) for d in DS_B for rule in RULES]
    rows = []; cstats = {}
    pool = Pool(procs, initializer=_sim_init, initargs=(sig, closes, opens, ncal, first_all, split_pos, end_all))
    t0 = time.time()
    for N, d, rule in configs:
        st = pool.map(_sim_one, [(N, d, rule, SEED0 + r, False) for r in range(reps)], chunksize=4)
        df = pd.DataFrame(st); md_ = df.median(numeric_only=True)
        win = bool(md_["cagr"] >= b_c and md_["mdd"] > b_m and md_["ca"] >= b_ca and md_["ma"] > b_ma and md_["cb"] >= b_cb and md_["mb"] > b_mb)
        med_seed = int(df.iloc[int(np.argsort(df["cagr"].to_numpy())[len(df) // 2])]["seed"])
        rep = _sim_one((N, d, rule, med_seed, True)) if not procs else pool.map(_sim_one, [(N, d, rule, med_seed, True)])[0]
        L = rep["log"]
        pd.DataFrame(L).to_csv(os.path.join(out_dir, f"blocked_{name}_N{N}_d{d if d else 'inf'}_{rule}.csv.gz"), index=False)
        cstats[(N, d, rule)] = {H: group_stats(L, H) for H in HOLDS}
        rows.append({"set": name, "N": N, "d": d if d else np.inf, "rule": rule, "cagr": md_["cagr"], "cagr_p10": df["cagr"].quantile(0.1), "cagr_p90": df["cagr"].quantile(0.9),
                     "mdd": md_["mdd"], "mdd_p10": df["mdd"].quantile(0.1), "mdd_p90": df["mdd"].quantile(0.9), "slot": md_["slot"], "m": md_["m"], "m_p10": df["m"].quantile(0.1), "m_p90": df["m"].quantile(0.9),
                     "pos_frac": md_["pos_frac"], "pos_p10": df["pos_frac"].quantile(0.1), "pos_p90": df["pos_frac"].quantile(0.9),
                     "deferred": md_["deferred"], "delay_med": md_["delay_med"], "expired": md_["expired"], "ca": md_["ca"], "ma": md_["ma"], "cb": md_["cb"], "mb": md_["mb"], "win": win,
                     "unstable": bool(df["cagr"].quantile(0.1) < 0), "med_seed": med_seed,
                     **{f"diff_H{H}_p{q}": df[f"diff_H{H}"].quantile(q / 100) for H in HOLDS for q in (10, 50, 90)}})
        r_ = rows[-1]
        print(f"  {name} N={N} d={d or '∞'} {rule}: 年化 {r_['cagr'] * 100:+.1f}% ({r_['cagr_p10'] * 100:+.1f}~{r_['cagr_p90'] * 100:+.1f}) 回落 {r_['mdd'] * 100:.1f}% 槽 {r_['slot'] * 100:.0f}% m {r_['m']:.0f} {'贏' if win else '沒贏'}  {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    pool.close(); pool.join()
    bench_stats = {"c": b_c, "m": b_m, "ca": b_ca, "ma": b_ma, "cb": b_cb, "mb": b_mb, "first": cal[first_all].date(), "end": cal[end_all - 1].date()}
    return pd.DataFrame(rows), cstats, bench_stats


def write_summary(out_dir, results, meta):
    L = ["# PREREGP1：組合層 存量 N 下探 × 每日新增上限 d——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREGP1.md`。種子 {SEED0}+r、r∈[0,{meta['reps']})；隊列 Q＝{QUEUE}；成本 {COST}；H60 為主格出場。", ""]
    L.append(f"資料：AND {meta['n_and']:,} 筆（{meta['and_h20']:,} 筆補得出 H20）、S {meta['n_s']:,} 筆；relvol 缺值 AND {meta['rel_na_and']:,}／S {meta['rel_na_s']:,}（前 60 根不足）；價格檔 {meta['n_px']:,} 檔（今天的 data/adj）。"); L.append("")
    for name, (P, C, B) in results.items():
        L.append(f"## {name} 集合"); L.append("")
        L.append(f"0050 買進持有（{B['first']} ～ {B['end']}）：年化 {B['c'] * 100:+.1f}%、最大回落 {B['m'] * 100:.1f}%；A 窗 {B['ca'] * 100:+.1f}%／{B['ma'] * 100:.1f}%；B 窗 {B['cb'] * 100:+.1f}%／{B['mb'] * 100:.1f}%。"); L.append("")
        L.append("### 4-A 存量曲線（d＝∞；描述）"); L.append("")
        L.append("| N | rule | 年化 中位 | p10～p90 | p90−p10 (pp) | ×√N | 最大回落 中位 | p10～p90 | 槽位 | m 中位 | A 窗 | B 窗 | 對 0050 |"); L.append("|---:|---|---:|---|---:|---:|---:|---|---:|---:|---|---|---|")
        for _, r in P[P.d == np.inf].iterrows():
            sp = (r.cagr_p90 - r.cagr_p10) * 100
            L.append(f"| {r.N} | {r.rule} | **{r.cagr * 100:+.1f}%** | {r.cagr_p10 * 100:+.1f} ~ {r.cagr_p90 * 100:+.1f}% | {sp:.1f} | {sp * np.sqrt(r.N):.0f} | {r.mdd * 100:.1f}% | {r.mdd_p10 * 100:.1f} ~ {r.mdd_p90 * 100:.1f}% | {r.slot * 100:.0f}% | {r.m:.0f} | {r.ca * 100:+.1f}%／{r.ma * 100:.1f}% | {r.cb * 100:+.1f}%／{r.mb * 100:.1f}% | {'**贏**' if r.win else '沒贏'}{'（不穩）' if r.unstable else ''} |")
        wins = int(P[P.d == np.inf].win.sum()); L.append(""); L.append(f"三條判準同時成立：{wins}／{int((P.d == np.inf).sum())} 格。"); L.append("")
        L.append("### 4-B 流量成本（N＝8；描述）"); L.append("")
        L.append("| d | rule | 年化 中位 | p10～p90 | 最大回落 中位 | 槽位 | m 中位 | 推遲進場 中位 | 推遲天數 中位 | b_expired 中位 | 對 0050 |"); L.append("|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|")
        for _, r in P[P.N == 8].sort_values(["d", "rule"]).iterrows():
            L.append(f"| {'∞' if r.d == np.inf else int(r.d)} | {r.rule} | **{r.cagr * 100:+.1f}%** | {r.cagr_p10 * 100:+.1f} ~ {r.cagr_p90 * 100:+.1f}% | {r.mdd * 100:.1f}% | {r.slot * 100:.0f}% | {r.m:.0f} | {r.deferred:.0f} | {r.delay_med if np.isfinite(r.delay_med) else '—'} | {r.expired:.0f} | {'**贏**' if r.win else '沒贏'} |")
        L.append("")
        for H in HOLDS:
            L.append(f"### 4-C 進場組 vs 擋掉組（H{H}；代表種子＝年化中位那個；月分群 95% CI{'，⚠ 一筆跨多月、CI 偏窄' if H > 20 else ''}）"); L.append("")
            L.append("| N | d | rule | in n／月 | in 平均／中位 | 擋掉(ex c) n／月 | 擋掉 平均／中位 | a n／平均 | b n／平均 | b_exp n／平均 | c n／平均 | 差 in−擋掉 | 95% CI | 統計層 | 差 200 種子 p10／p50／p90 |")
            L.append("|---:|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|")
            for _, r in P.sort_values(["N", "d", "rule"]).iterrows():
                cs = C[(int(r.N), None if r.d == np.inf else int(r.d), r.rule)][H]
                if cs is None:
                    continue
                def cell(nm, both=True):
                    g = cs.get(nm, {"n": 0})
                    if not g.get("n"):
                        return "0"
                    return f"{g['n']:,}／{g['months']} | {fmt_pct(g['mean'], 2)}／{fmt_pct(g['median'], 2)}" if both else f"{g['n']:,}／{fmt_pct(g['mean'], 2)}"
                dd = cs.get("diff")
                v = "—" if dd is None else ("測不出" if dd["lo"] <= 0 <= dd["hi"] else ("測得出（＋）" if dd["mean"] > 0 else "測得出（−）"))
                L.append(f"| {r.N} | {'∞' if r.d == np.inf else int(r.d)} | {r.rule} | {cell('in')} | {cell('blocked_ex_c')} | {cell('a', False)} | {cell('b', False)} | {cell('b_expired', False)} | {cell('c', False)} | "
                         f"{fmt_pct(dd['mean'], 2) if dd else '—'} | {fmt_pct(dd['lo'], 2) + ' ~ ' + fmt_pct(dd['hi'], 2) if dd else '—'} | {v} | "
                         f"{fmt_pct(r[f'diff_H{H}_p10'], 2)}／{fmt_pct(r[f'diff_H{H}_p50'], 2)}／{fmt_pct(r[f'diff_H{H}_p90'], 2)} |")
            L.append("")
        L.append("### 4-D 做 m 筆的真實機率（逐種子：完成交易筆數與其中淨報酬為正的比例）"); L.append("")
        L.append("| N | d | rule | m 中位（p10～p90） | 為正比例 中位（p10～p90） |"); L.append("|---:|---|---|---|---|")
        for _, r in P.sort_values(["N", "d", "rule"]).iterrows():
            L.append(f"| {r.N} | {'∞' if r.d == np.inf else int(r.d)} | {r.rule} | {r.m:.0f}（{r.m_p10:.0f}～{r.m_p90:.0f}） | {r.pos_frac * 100:.1f}%（{r.pos_p10 * 100:.1f}～{r.pos_p90 * 100:.1f}） |")
        L.append("")
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--sets", nargs="*", default=["AND", "S"]); ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--regress", action="store_true", help="只跑回歸 R0～R3")
    ap.add_argument("--skip-regress", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); t0 = time.time()
    cal = D.load_calendar(); ncal = len(cal); uni = D.load_universe().set_index("stock_id")["market"]
    AND = pd.read_csv(os.path.join(HERE, "results13b", "and_signals.csv.gz"), dtype={"sid": str})
    S = pd.read_csv(os.path.join(HERE, "results11", "signals.csv.gz"), dtype={"sid": str})
    closes, opens = load_prices(set(AND["sid"]) | set(S["sid"]), cal, uni)
    missing, mism = attach_features(AND, S, cal, uni, a.procs)
    print(f"特徵：AND {len(AND):,}（H20 補得出 {int(AND['g_H20'].notna().sum()):,}）、S {len(S):,}；relvol 缺 AND {int(AND['relvol'].isna().sum())}／S {int(S['relvol'].isna().sum())}；k↔pos 不符 {mism}；讀不到 {len(missing)} 檔  {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    if mism:
        print("⛔ 訊號的 k 與 pos 對不上（資料改版？），停。", file=sys.stderr); sys.exit(1)
    AND.to_csv(os.path.join(a.out, "and_signals_p1.csv.gz"), index=False)
    if not a.skip_regress:
        print("回歸：", file=sys.stderr, flush=True)
        if not regress(AND, S, closes, opens, cal, uni, ncal):
            print("⛔ 回歸沒過，停。", file=sys.stderr); sys.exit(1)
        print(f"回歸全過 {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    if a.regress:
        return
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    results = {}; allrows = []
    for name in a.sets:
        sig = {"AND": AND, "S": S}[name]
        P, C, B = run_set(name, sig, closes, opens, cal, bench, a.reps, a.procs, a.out)
        results[name] = (P, C, B); allrows.append(P)
    pd.concat(allrows).to_csv(os.path.join(a.out, "portfolio.csv"), index=False)
    meta = {"reps": a.reps, "n_and": len(AND), "and_h20": int(AND["g_H20"].notna().sum()), "n_s": len(S), "rel_na_and": int(AND["relvol"].isna().sum()), "rel_na_s": int(S["relvol"].isna().sum()), "n_px": len(closes)}
    write_summary(a.out, results, meta)
    print(f"完成 {time.time() - t0:.0f}s → {a.out}/summary.md", file=sys.stderr)


if __name__ == "__main__":
    main()
