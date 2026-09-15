"""PREREGP3：閒置資金放 0050 vs 空手（策略線 09-15 13:35 丙節；落地版定義見 backtest/PREREGP3.md 追加）。

    python3 -m backtest.researchp3 --out backtest/resultsp3 [--procs 4] [--reps 200] [--shuffles 200] [--pre]

對照（登錄 §三＋K線分析 09-15 17:00 §一 裁定）：
  甲 cash_mode="zero"  閒置槽位空手（＝P1 現況；同種子 7000+r ⇒ 與 resultsp1/portfolio.csv 逐格對帳）
  乙 cash_mode="bench" 閒置槽位放 0050 還原收盤，進出各付單邊 COST/2（research11.simulate_mtm 既有）
  丙 同平均曝險、時點隨機：取甲每個種子的逐日曝險 e_t＝hold_val/equity 與持股部分逐日報酬 r_inv_t＝(equity_t/equity_{t−1}−1)/e_{t−1}
     （e_{t−1}＝0 的日子 r_inv＝0、另計筆數），套回同一條 r_inv：equity'_t＝equity'_{t−1}×(1＋e'_{t−1}×r_inv_t)；閒置現金報酬與甲同（0）。
     丙1【主格】環形平移：e'_t＝e_{(t+k) mod T}，k 均勻抽自 [1, T−1]（＝假訊號組①套在曝險序列上；保住 e 的自相關與連續空手段長度）
     丙2【第二格】整段重排：e 逐日 permutation（連自相關也拿掉，更強的虛無）
     每種子各 K 次，種子 9000+k（丙1）／10000+k（丙2），⛔ 與 P1 不同段。甲−丙1＝時點對齊的貢獻；丙1−丙2＝曝險持續性的貢獻。
格子（登錄 §四＋K線分析 1-1）：主格＝P1 贏過 0050 的三格 AND N30 null／N40 null／N40 relvol（d=∞、H60 出場）
     ＋【輸給 0050 的對照格】N30 relvol、N20 null（同網格，沒被看過 ⇒ 讓丙可否證）＋ N ≤ 8 的全部格（P1 網格 14 格）。
前置（K線分析 1-3，⛔ 結果之前先報）：--pre 印甲各主格的空手天數佔比、最長連續空手段、平均閒置比例。
量測：最大回落中位＋年化中位（全期與 A／B 窗，P1 同法）；槽位使用率（甲乙各自；丙＝甲）；乙−甲 分解；甲在丙分佈的百分位；逐年（代表種子）。
判定（登錄 §一／二）：H1 三格在乙下「不再贏」＝ 乙的最大回落中位 ≤ 0050 買進持有（劣於或等於）；同時報 P1 六條件 win；
     H2 N ≤ 8 各格在乙下沒有一格 win；出口 ⓐ 有效月 < 24 ⇒ 還沒測；ⓑ 乙−甲 差異的 p10～p90 含 0（年化與回落皆） ⇒ 分不出。
⛔ 判定字只用 測得出／測不出／還沒測／分不出；成本 COST、bench_cost＝COST/2（P1 〇節）。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp3")
COST = R.COST
SEED0 = P1.SEED0                 # 7000+r，沿用 P1（登錄 §四：要能逐格對帳）
SHUFFLE_SEED0 = 9000             # 丙的重排種子（⛔ 與 P1 不同段）
N_MIN_MONTHS = 24
MAIN_CELLS = [(30, None, "null"), (40, None, "null"), (40, None, "relvol")]     # P1 贏過 0050 的三格（CONCLUSIONS 十一 11-1）
LOSING_CELLS = [(30, None, "relvol"), (20, None, "null")]                          # P1 輸給 0050、同網格、沒被看過（K線分析 1700 §1-1）
SHUFFLE_SEED_PERM = 10000
_S: dict = {}


def cells() -> list[tuple]:
    grid = [(N, None, rule) for N in P1.NS_A for rule in P1.RULES] + [(8, d, rule) for d in P1.DS_B for rule in P1.RULES]
    small = [c for c in grid if c[0] <= 8]
    return MAIN_CELLS + LOSING_CELLS + small


def exposure_series(equity: np.ndarray, hold_val: np.ndarray, first: int, end: int):
    """甲 → (e, r_inv, n_zero)：e_t＝持股市值/權益；r_inv_t＝總報酬/e_{t−1}（e_{t−1}＝0 ⇒ 0）。索引對齊 [first, end)。"""
    eq = equity[first:end]; hv = hold_val[first:end]
    e = np.where(eq > 0, hv / eq, 0.0)
    r_tot = np.empty_like(eq); r_tot[0] = 0.0; r_tot[1:] = eq[1:] / eq[:-1] - 1
    e_prev = np.r_[0.0, e[:-1]]
    r_inv = np.where(e_prev > 1e-12, r_tot / np.where(e_prev > 1e-12, e_prev, 1.0), 0.0)
    return e, r_inv, int((e_prev[1:] <= 1e-12).sum())


def rebuild(e: np.ndarray, r_inv: np.ndarray) -> np.ndarray:
    """equity'_t ＝ Π (1 + e_{t−1} r_inv_t)，equity'_0＝1。e＝甲原序列時逐位元重現甲（自測驗）。"""
    e_prev = np.r_[0.0, e[:-1]]
    return np.cumprod(1.0 + e_prev * r_inv)


def idle_stats(e: np.ndarray) -> dict:
    """空手天數佔比（e＝0 的日子）、最長連續空手段（交易日）、平均閒置比例 1−mean(e)。"""
    z = e <= 1e-12
    longest = 0; cur = 0
    for v in z:
        cur = cur + 1 if v else 0
        longest = max(longest, cur)
    return {"idle_day_share": float(z.mean()), "longest_idle_run": int(longest), "avg_idle_frac": float(1 - e.mean())}


def shuffle_exposure(e: np.ndarray, rng, mode: str, month_ids: np.ndarray | None = None) -> np.ndarray:
    if mode == "shift":
        k = int(rng.integers(1, len(e)))          # k ∈ [1, T−1]
        return np.roll(e, -k)                      # e'_t ＝ e_{(t+k) mod T}
    if mode == "day":
        return e[rng.permutation(len(e))]
    assert month_ids is not None
    blocks = [np.flatnonzero(month_ids == m) for m in pd.unique(month_ids)]
    order = rng.permutation(len(blocks))
    out = np.empty_like(e); pos = 0
    # 以月為塊重排：塊長不同 ⇒ 依原塊順序的位置填入重排後的塊內容（截斷／循環到原塊長）
    for b, src in zip(blocks, [blocks[i] for i in order]):
        vals = e[src]
        out[b] = np.resize(vals, len(b))
    return out


def _stats(eq: np.ndarray, first: int, end: int, first_all: int, split_pos: int, end_all: int) -> dict:
    c, m = R13.window_stats(eq, first, end, first_all, end_all)
    ca, ma = R13.window_stats(eq, first, end, first_all, split_pos)
    cb, mb = R13.window_stats(eq, first, end, split_pos, end_all)
    return {"cagr": c, "mdd": m, "ca": ca, "ma": ma, "cb": cb, "mb": mb}


def _init(sig, closes, opens, ncal, first_all, split_pos, end_all, bench, month_ids, shuffles):
    _S.update(sig=sig, closes=closes, opens=opens, ncal=ncal, first_all=first_all, split_pos=split_pos, end_all=end_all, bench=bench,
              month_ids=month_ids, shuffles=shuffles)


def sim_cell_seed(args):
    """一格一種子：甲、乙各跑一次；丙1（環形平移）與丙2（整段重排）各 K 次。回傳逐種子列。"""
    N, d, rule, seed = args
    kw = dict(d_max=d, pick=None if rule == "null" else "relvol", queue_days=P1.QUEUE if d is not None else 0, return_equity=True)
    A = R.simulate_mtm(_S["sig"], "H60", N, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"], **kw)
    B = R.simulate_mtm(_S["sig"], "H60", N, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"], cash_mode="bench", bench=_S["bench"], bench_cost=COST / 2, **kw)
    fa, ea = A["first"], A["end"]
    sa = _stats(A["equity"], fa, ea, _S["first_all"], _S["split_pos"], _S["end_all"]); sb = _stats(B["equity"], B["first"], B["end"], _S["first_all"], _S["split_pos"], _S["end_all"])
    e, r_inv, n_zero = exposure_series(A["equity"], A["hold_val"], fa, ea)
    out = {"N": N, "d": d if d else np.inf, "rule": rule, "seed": seed,
           **{f"A_{k}": v for k, v in sa.items()}, "A_slot": A["slot_use"], "A_trades": A["trades"],
           **{f"B_{k}": v for k, v in sb.items()}, "B_slot": B["slot_use"], "B_trades": B["trades"],
           "avg_exposure": float(e.mean()), "zero_exp_days": n_zero, "days": int(ea - fa), **idle_stats(e)}
    for tag, mode, seed0 in (("C1", "shift", SHUFFLE_SEED0), ("C2", "day", SHUFFLE_SEED_PERM)):
        mdds, cagrs = [], []
        for k in range(_S["shuffles"]):
            eq2 = rebuild(shuffle_exposure(e, np.random.default_rng(seed0 + k), mode), r_inv)
            c2, m2 = R13.window_stats(eq2, 0, len(eq2), 0, len(eq2))
            mdds.append(m2); cagrs.append(c2)
        mdds = np.array(mdds); cagrs = np.array(cagrs)
        out.update({f"{tag}_mdd_p10": float(np.quantile(mdds, 0.1)), f"{tag}_mdd_p50": float(np.median(mdds)), f"{tag}_mdd_p90": float(np.quantile(mdds, 0.9)),
                    f"{tag}_cagr_p10": float(np.quantile(cagrs, 0.1)), f"{tag}_cagr_p50": float(np.median(cagrs)), f"{tag}_cagr_p90": float(np.quantile(cagrs, 0.9)),
                    f"A_mdd_pct_in_{tag}": float((mdds < sa["mdd"]).mean() * 100),     # 甲的回落比幾 % 的丙深（回落是負數）
                    f"A_cagr_pct_in_{tag}": float((cagrs < sa["cagr"]).mean() * 100)})
    return out


def p1_win(md: pd.Series, prefix: str, b: dict) -> bool:
    """P1 六條件（run_set 原式）：年化 ≥ 0050 且回落淺於 0050，全期／A／B 皆成立。"""
    return bool(md[f"{prefix}_cagr"] >= b["c"] and md[f"{prefix}_mdd"] > b["m"] and md[f"{prefix}_ca"] >= b["ca"] and md[f"{prefix}_ma"] > b["ma"]
                and md[f"{prefix}_cb"] >= b["cb"] and md[f"{prefix}_mb"] > b["mb"])


def judge_cell(cell: tuple, df: pd.DataFrame, b: dict, months: int) -> dict:
    md = df.median(numeric_only=True)
    winA, winB = p1_win(md, "A", b), p1_win(md, "B", b)
    diff_m = df["B_mdd"] - df["A_mdd"]; diff_c = df["B_cagr"] - df["A_cagr"]
    undist = bool(diff_m.quantile(0.1) <= 0 <= diff_m.quantile(0.9) and diff_c.quantile(0.1) <= 0 <= diff_c.quantile(0.9))
    is_main = cell in MAIN_CELLS
    if months < N_MIN_MONTHS:
        j = "還沒測（有效月 < 24）"
    elif cell in LOSING_CELLS:
        j = "對照格（P1 輸給 0050）：只報甲−丙1、丙1−丙2，不判定"
    elif is_main:
        h1 = md["B_mdd"] <= b["m"]        # 乙的回落中位 劣於或等於 0050（回落是負數，越小越深）
        j = ("H1 成立：乙不再贏（乙回落中位 ≤ 0050）" if h1 else "H1 否證：乙仍贏（回落仍淺於 0050）") + ("｜⚠ ⓑ 乙−甲 p10～p90 含 0 ⇒ 分不出" if undist else "")
    else:
        j = ("H2 否證：N ≤ 8 在乙下出現贏格 ⇒ 本件作廢重查" if winB else "H2 成立：乙下仍沒贏")
    return {"win_A": winA, "win_B": winB, "undistinguishable": undist, "judge": j}


def yearly_table(cell_rows: dict, cal: pd.DatetimeIndex, bench: np.ndarray) -> pd.DataFrame:
    rows = []
    yrs = cal.year
    for (N, d, rule), (eqA, eqB, first, end) in cell_rows.items():
        for y in sorted(set(yrs[first:end])):
            m = np.flatnonzero((yrs == y) & (np.arange(len(cal)) >= first) & (np.arange(len(cal)) < end))
            if len(m) < 2:
                continue
            a0, a1 = m[0] - 1 if m[0] > first else m[0], m[-1]
            rows.append({"N": N, "d": d if d else np.inf, "rule": rule, "year": y,
                         "A_ret": eqA[a1] / eqA[a0] - 1, "B_ret": eqB[a1] / eqB[a0] - 1, "bench_ret": bench[a1] / bench[a0] - 1})
    return pd.DataFrame(rows)


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=HERE, text=True).strip()
    except Exception:
        return "unknown"


def write_csv(df: pd.DataFrame, path: str, stamp: str, commit: str):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# commit={commit} run={stamp} (Asia/Taipei) prereg=backtest/PREREGP3.md seeds={SEED0}+r C1(shift)_seeds={SHUFFLE_SEED0}+k C2(perm)_seeds={SHUFFLE_SEED_PERM}+k\n")
        df.to_csv(fh, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--shuffles", type=int, default=200)
    ap.add_argument("--cells", type=int, default=None, help="只跑前 n 格（自測／冒煙用）")
    ap.add_argument("--pre", action="store_true", help="前置：只印主格與對照格（甲，3 種子）的空手佔比／最長連續空手段，不跑丙乙")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); t0 = time.time()
    stamp = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"); commit = _commit()
    cal = D.load_calendar(); ncal = len(cal); uni = D.load_universe().set_index("stock_id")["market"]
    AND = pd.read_csv(os.path.join(HERE, "resultsp1", "and_signals_p1.csv.gz"), dtype={"sid": str})     # ⭐ P1 落地時存的訊號（含 relvol），逐格對帳用
    closes, opens = P1.load_prices(set(AND["sid"]), cal, uni)
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01"))); first_all = int(AND["entry_pos"].min()); end_all = ncal
    b = dict(zip(("c", "m"), R13.window_stats(bench, first_all, end_all, first_all, end_all)))
    b.update(dict(zip(("ca", "ma"), R13.window_stats(bench, first_all, end_all, first_all, split_pos))))
    b.update(dict(zip(("cb", "mb"), R13.window_stats(bench, first_all, end_all, split_pos, end_all))))
    months = int(pd.Series(cal[first_all:end_all]).dt.to_period("M").nunique())
    month_ids = cal.to_period("M").astype(str).to_numpy()
    cl = cells()[: a.cells] if a.cells else cells()
    if a.pre:
        for N, d, rule in MAIN_CELLS + LOSING_CELLS:
            kw = dict(d_max=d, pick=None if rule == "null" else "relvol", queue_days=P1.QUEUE if d is not None else 0, return_equity=True)
            st = []
            for r in range(3):
                A = R.simulate_mtm(AND, "H60", N, np.random.default_rng(SEED0 + r), closes, opens, ncal, **kw)
                e, _, _ = exposure_series(A["equity"], A["hold_val"], A["first"], A["end"]); st.append(idle_stats(e))
            m = pd.DataFrame(st).median()
            print(f"前置 N{N} {rule}：空手天數佔比 {m['idle_day_share'] * 100:.1f}%、最長連續空手段 {m['longest_idle_run']:.0f} 交易日、平均閒置比例 {m['avg_idle_frac'] * 100:.1f}%（3 種子中位）")
        return
    rows, cell_rows, summ = [], {}, []
    with Pool(a.procs, initializer=_init, initargs=(AND, closes, opens, ncal, first_all, split_pos, end_all, bench, month_ids, a.shuffles)) as pool:
        for cell in cl:
            N, d, rule = cell
            st = pool.map(sim_cell_seed, [(N, d, rule, SEED0 + r) for r in range(a.reps)], chunksize=4)
            df = pd.DataFrame(st); rows.append(df)
            md = df.median(numeric_only=True); jd = judge_cell(cell, df, b, months)
            med_seed = int(df.iloc[int(np.argsort(df["A_cagr"].to_numpy())[len(df) // 2])]["seed"])
            kw = dict(d_max=d, pick=None if rule == "null" else "relvol", queue_days=P1.QUEUE if d is not None else 0, return_equity=True)
            A = R.simulate_mtm(AND, "H60", N, np.random.default_rng(med_seed), closes, opens, ncal, **kw)
            B = R.simulate_mtm(AND, "H60", N, np.random.default_rng(med_seed), closes, opens, ncal, cash_mode="bench", bench=bench, bench_cost=COST / 2, **kw)
            cell_rows[cell] = (A["equity"], B["equity"], A["first"], A["end"])
            r = {"cell": "主格" if cell in MAIN_CELLS else ("對照格（輸）" if cell in LOSING_CELLS else "N≤8"), "N": N, "d": d if d else np.inf, "rule": rule, "months": months, "reps": len(df), "med_seed": med_seed,
                 **{f"{p}_{k}_med": md[f"{p}_{k}"] for p in ("A", "B") for k in ("cagr", "mdd", "ca", "ma", "cb", "mb", "slot")},
                 **{f"{p}_{k}_p{q}": df[f"{p}_{k}"].quantile(q / 100) for p in ("A", "B") for k in ("cagr", "mdd") for q in (10, 90)},
                 "BminusA_cagr_med": (df["B_cagr"] - df["A_cagr"]).median(), "BminusA_mdd_med": (df["B_mdd"] - df["A_mdd"]).median(),
                 "BminusA_cagr_p10": (df["B_cagr"] - df["A_cagr"]).quantile(0.1), "BminusA_cagr_p90": (df["B_cagr"] - df["A_cagr"]).quantile(0.9),
                 "BminusA_mdd_p10": (df["B_mdd"] - df["A_mdd"]).quantile(0.1), "BminusA_mdd_p90": (df["B_mdd"] - df["A_mdd"]).quantile(0.9),
                 "avg_exposure_med": md["avg_exposure"], "zero_exp_days_med": md["zero_exp_days"], "idle_day_share_med": md["idle_day_share"], "longest_idle_run_med": md["longest_idle_run"],
                 **{f"{t}_{k}_med": md[f"{t}_{k}"] for t in ("C1", "C2") for k in ("mdd_p10", "mdd_p50", "mdd_p90", "cagr_p50")},
                 **{f"A_{k}_pct_in_{t}_med": md[f"A_{k}_pct_in_{t}"] for t in ("C1", "C2") for k in ("mdd", "cagr")},
                 "AminusC1_mdd_med": (df["A_mdd"] - df["C1_mdd_p50"]).median(), "C1minusC2_mdd_med": (df["C1_mdd_p50"] - df["C2_mdd_p50"]).median(),
                 "AminusC1_cagr_med": (df["A_cagr"] - df["C1_cagr_p50"]).median(), "C1minusC2_cagr_med": (df["C1_cagr_p50"] - df["C2_cagr_p50"]).median(),
                 "bench_cagr": b["c"], "bench_mdd": b["m"], **jd}
            summ.append(r)
            print(f"  N={N} d={d or '∞'} {rule}: 甲 {md['A_cagr'] * 100:+.1f}%／{md['A_mdd'] * 100:.1f}% 乙 {md['B_cagr'] * 100:+.1f}%／{md['B_mdd'] * 100:.1f}% 0050 {b['c'] * 100:+.1f}%／{b['m'] * 100:.1f}% 甲回落在丙1／丙2百分位 {md['A_mdd_pct_in_C1']:.0f}／{md['A_mdd_pct_in_C2']:.0f}  {jd['judge']}  {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    S = pd.DataFrame(summ); write_csv(S, os.path.join(a.out, "summary.csv"), stamp, commit)
    write_csv(pd.concat(rows, ignore_index=True), os.path.join(a.out, "seeds.csv"), stamp, commit)
    write_csv(yearly_table(cell_rows, cal, bench), os.path.join(a.out, "yearly.csv"), stamp, commit)
    main_ = S[S["cell"] != "N≤8"]; small = S[S["cell"] == "N≤8"]
    L = [f"# PREREGP3 閒置資金放 0050 vs 空手——細表", "",
         f"產出：{stamp}（台北）、commit {commit}。判準 `backtest/PREREGP3.md`。種子 {SEED0}+r（沿用 P1，r<{a.reps}）；丙1 環形平移種子 {SHUFFLE_SEED0}+k、丙2 整段重排種子 {SHUFFLE_SEED_PERM}+k（k<{a.shuffles}）；成本 {COST}、bench 單邊 {COST / 2}；期間 {cal[first_all].date()}～{cal[end_all - 1].date()}（{months} 個月）。0050 買進持有：年化 {b['c'] * 100:+.1f}%、最大回落 {b['m'] * 100:.1f}%。", ""]
    L.append("## 〇、前置（K線分析 1-3）：甲的空手天數佔比／最長連續空手段／平均閒置比例（200 種子中位）"); L.append("")
    for r in main_.itertuples():
        L.append(f"- {r.cell} N{r.N} {r.rule}：空手天數 {r.idle_day_share_med * 100:.1f}%、最長連續 {r.longest_idle_run_med:.0f} 交易日、平均閒置 {(1 - r.avg_exposure_med) * 100:.1f}%")
    L.append(""); L.append("## 一、主格三格（P1 贏過 0050 的那三格）＋ 對照格（輸給 0050，沒被看過）"); L.append("")
    L.append("| 格 | 甲 年化／回落（中位） | 乙 年化／回落（中位） | 乙−甲 回落 中位（p10～p90） | 槽位 甲／乙 | 丙1 回落 p10／p50／p90 | 甲回落在丙1／丙2 百分位 | 甲−丙1 回落 | 丙1−丙2 回落 | P1 win 甲／乙 | 判定 |"); L.append("|---|---|---|---|---|---|---|---:|---:|---|---|")
    for r in main_.itertuples():
        L.append(f"| {r.cell} N{r.N} {r.rule} | {r.A_cagr_med * 100:+.1f}%／{r.A_mdd_med * 100:.1f}% | {r.B_cagr_med * 100:+.1f}%／{r.B_mdd_med * 100:.1f}% | {r.BminusA_mdd_med * 100:+.1f}pp（{r.BminusA_mdd_p10 * 100:+.1f}～{r.BminusA_mdd_p90 * 100:+.1f}） | {r.A_slot_med * 100:.0f}%／{r.B_slot_med * 100:.0f}% | {r.C1_mdd_p10_med * 100:.1f}／{r.C1_mdd_p50_med * 100:.1f}／{r.C1_mdd_p90_med * 100:.1f}% | {r.A_mdd_pct_in_C1_med:.0f}／{r.A_mdd_pct_in_C2_med:.0f} | {r.AminusC1_mdd_med * 100:+.1f}pp | {r.C1minusC2_mdd_med * 100:+.1f}pp | {r.win_A}／{r.win_B} | {r.judge} |")
    L.append(""); L.append("## 二、N ≤ 8 各格（H2：乙下不得出現贏格）"); L.append("")
    L.append("| N | d | rule | 甲 年化／回落 | 乙 年化／回落 | P1 win 甲／乙 | 判定 |"); L.append("|---:|---|---|---|---|---|---|")
    for r in small.itertuples():
        L.append(f"| {r.N} | {'∞' if r.d == np.inf else int(r.d)} | {r.rule} | {r.A_cagr_med * 100:+.1f}%／{r.A_mdd_med * 100:.1f}% | {r.B_cagr_med * 100:+.1f}%／{r.B_mdd_med * 100:.1f}% | {r.win_A}／{r.win_B} | {r.judge} |")
    L.append(""); L.append("⚠ 甲在丙的百分位：回落是負數，「甲比 X% 的丙深」＝丙中比甲淺的占 100−X%。丙1（環形平移）保住曝險的自相關與連續空手段，只打散相位 ⇒ 登錄 §五④「空手集中在連續幾個月會低估甲」在丙1 下不成立；丙2（整段重排）連自相關也拿掉 ⇒ 那條限制只對丙2 成立（K線分析 1700 §1-2）。甲−丙1＝時點對齊的貢獻；丙1−丙2＝曝險持續性的貢獻。")
    L.append("⚠ 主格三格是 P1 裡已知贏的格 ⇒ 本件對它們是【歸因】不是【驗證】：只能寫「這三格的表現裡有多少來自曝險時點」，⛔ 不可寫「通過 P3 ⇒ 確認有效」（K線分析 1700 §1-1）。對照格（輸給 0050）若丙給出同樣大的時點貢獻 ⇒ 丙量到的是引擎共同性質。")
    L.append("⚠ 甲乙同種子 ⇒ 進場序列相同（乙只多了閒置資金持 0050 的記帳）；relvol 格 pick 決定 ⇒ 200 種子相同。逐年見 `yearly.csv`（代表種子＝甲年化中位那個），逐種子見 `seeds.csv`。⛔ 本件只分辨「贏是不是現金買的」，不回答該不該持有現金。")
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
