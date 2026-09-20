"""PREREGP12（策略線 2026-09-20 1500 seq=2；K線分析線 1510【准予開跑】）：**把 25.7pp 拆成 S／C／T**。

    python3 -m backtest.researchp12 [--procs 8] [--reps 200] [--out backtest/resultsp12]
                                    [--part c0|cells|all]

⭐ 引擎是 `research11.simulate_mtm`（⛔ 沒有另建、⛔ 沒有加參數）；sig 是 `researchp7.build_sig_gate_b`
   （signal="B" ＝ S1／signal="ALL" ＝ S0，⛔ 沒有抄第二份）；逐月報酬是 `researchp11.monthly_returns`；
   月分群 CI 是 `researchp8.month_ci`；曝險是 `researchp3.exposure_series`；窗內年化／回落是 `research13.window_stats`。

⛔ 登錄全文＋回測線落地登錄（§九，機器定義）：`backtest/PREREGP12.md`。以下只複述**跑起來會用到**的那幾條：

  窗　　主格窗 [2071, 2498]（2023-07-03~2025-04-09，428 日，⚠ 含選擇效應）／全窗 [523, 2835]
  總報酬 win_ret ＝ equity[w1] / equity[w0] − 1（⛔ 不是 w0−1；對帳另報 w0−1 那一版）
  S　　 S1 ＝ 門檻B／S0 ＝ 全市場（過閘門就算訊號）
  C　　 C1 ＝ n_slots 8／C0 ＝【買光】＝ 使 trades 達上限的**最小** n_slots（§九-5，0.999 寫死）
  T　　 T1 ＝ H120 輪動（⭐ 跑完整條日曆、讀窗段 ⇒ 窗頭帶著倉位）／T0 ＝ 窗內第一個訊號月建倉、xpos ＝ 窗尾
  成本　每一格都跑【0.585%】與【0】兩份：⛔ 判定用含成本那一份，成本 0 是描述（§四④⑥）
  種子　default_rng(102000 + r)，R=200
  判定　只有三個主效果進判定，⇒ 逐種子＋逐「其餘兩開關」配對的**逐月報酬差** ⇒ month_ci ⇒ CI 含不含 0

⛔⛔ 否證①：兩個錨點（主格窗 (S1,C1,T1) ＝ −40.9% 含成本／(S0,C0,T0) ＝ −15.21% **成本 0**，各 ±1pp）
   任一個對不上 ⇒ **停止、本件不出結論**（程式會寫出對帳段落然後 `SystemExit`，⛔ 不會印出任何主效果）。
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
from . import p4_features as P4F
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1
from . import researchp3 as P3
from . import researchp7 as P7
from . import researchp8 as P8
from . import researchp11 as P11

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp12")
SEED0 = 102000                   # ⛔ 登錄 §九-8 寫死；⛔ 與 P1(1000/3000/7000)／P2(12000)／P3(9000)／P6(96000)／P7(97000)／P8(98000)／P9(99000)／P11(101000) 都不重疊
RULE = P7.RULE                   # "H120"（⭐ 唯一定義在 P7，⛔ 本檔沒有第二份）
COST_STD = R.COST                # 0.585%（⛔ 在任何成本切換之前抓下來 ⇒ 還原用）
N_C1 = 8                         # C1 ＝ n_slots 8（登錄 §一）
C0_FRAC = 0.999                  # C0 的「買光」判準：trades ≥ 0.999 × 上限（⛔ 寫死，⛔ 不事後調）
WINDOWS = {"主格窗": ("2023-07-03", "2025-04-09"), "全窗": ("2017-03-02", "2026-08-24")}
WIN_DAYS = {"主格窗": 428}       # ⭐ 登錄 §二 寫死的天數（程式自驗；全窗沒給數字 ⇒ 不驗）
ANCHORS = {("主格窗", "S1", "C1", "T1", "成本0.585%"): -0.409,     # §四④ 錨點①（含成本）
           ("主格窗", "S0", "C0", "T0", "成本0"): -0.1521}         # §四④ 錨點②（⭐ 成本設 0 對帳）
ANCHOR_TOL = 0.01                # ±1pp（⛔ 策略線定的，⛔ 回測線不得放寬）
COSTS = (("成本0.585%", COST_STD), ("成本0", 0.0))
CORNERS = [(s, c, t) for s in ("S1", "S0") for c in ("C1", "C0") for t in ("T1", "T0")]
SIG_OF = {"S1": "B", "S0": "ALL"}
START = "2017-01-01"


# ── 窗與月界 ──
def win_bounds(cal, key: str) -> tuple[int, int]:
    """窗的日曆位置 [w0, w1]（⭐ 兩端都含）。⛔ 對不上登錄寫死的天數就停。"""
    a, b = WINDOWS[key]
    w0, w1 = int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b)))
    if not (0 <= w0 < len(cal) and 0 <= w1 < len(cal)):
        raise SystemExit(f"⛔ {key} 的端點落在日曆之外（ncal={len(cal)}）：{a}→{w0}／{b}→{w1}")
    if str(cal[w0].date()) != a or str(cal[w1].date()) != b:
        raise SystemExit(f"⛔ {key} 的端點不是交易日：{a}→{cal[w0].date()}／{b}→{cal[w1].date()}")
    if key in WIN_DAYS and w1 - w0 + 1 != WIN_DAYS[key]:
        raise SystemExit(f"⛔ {key} 天數對不上登錄：要 {WIN_DAYS[key]}、實得 {w1 - w0 + 1}")
    return w0, w1


def month_marks(cal, w0: int, w1: int) -> np.ndarray:
    """月界 ＝ [w0, 窗內各日曆月的最後一個交易日…, w1]（⭐ 第一段是 w0 → 當月月底的部分月）。"""
    ym = pd.DatetimeIndex(cal[w0:w1 + 1]).strftime("%Y-%m")
    last = {k: w0 + i for i, k in enumerate(ym)}         # 後面的覆蓋前面的 ⇒ 每個月留最後一天
    out = [w0]
    for v in last.values():
        if v > out[-1]:
            out.append(v)
    return np.array(out, int)          # ⭐ 最後一個月的最後一天就是 w1 ⇒ ⛔ 不必（也不可以）再補一個


def sig_hold_to(sig: pd.DataFrame, w0: int, w1: int, closes: dict, opens: dict) -> pd.DataFrame:
    """T0 的 sig：窗內**第一個**訊號月整批進場、xpos ＝ 窗尾 w1（登錄 §一／§九-4）。

    ⭐ 從 T1 的 sig 派生 ⇒ 訊號集（S 這個開關）在 T1／T0 兩側**完全相同**，⛔ 不另開母體。
    ⛔ 剔除規則與 T1 同一條：進場開盤非有限或 ≤ 0、窗尾收盤非有限 ⇒ 丟掉。
    """
    d = sig[(sig["entry_pos"] >= w0) & (sig["entry_pos"] <= w1)]
    if d.empty:
        raise SystemExit(f"⛔ 窗 [{w0},{w1}] 內沒有任何訊號 ⇒ T0 建不出來")
    e0 = int(d["entry_pos"].min())
    d = d[d["entry_pos"] == e0].copy()
    if e0 >= w1:
        raise SystemExit(f"⛔ T0 建倉日 {e0} 不早於窗尾 {w1}")
    ok, g = [], []
    for r in d.itertuples():
        o = float(opens[r.sid][e0]); c = float(closes[r.sid][w1])
        good = np.isfinite(o) and o > 0 and np.isfinite(c)
        ok.append(good); g.append(c / o - 1.0 if good else np.nan)
    d[f"xpos_{RULE}"] = w1
    d[f"g_{RULE}"] = g
    return d[np.array(ok)].reset_index(drop=True)


# ── 逐格量 ──
def win_read(out: dict, w0: int, w1: int, marks: np.ndarray) -> dict:
    """一條權益曲線在 [w0, w1] 的：窗期總報酬（§九-2 主口徑）＋年化＋回落＋曝險＋逐月報酬。"""
    eq, hv, first, end = out["equity"], out["hold_val"], out["first"], out["end"]
    lo = min(first, w0)                              # ⭐ 繞開 window_stats 的 a=max(a,first)：T0 的 first 在 w0 之後，
    cagr, mdd = R13.window_stats(eq, lo, max(end, w1 + 1), w0, w1 + 1)   # ⛔ 讓它 clamp 會把建倉日那天的漲跌吃掉
    e, _r, _z = P3.exposure_series(eq, hv, w0, w1 + 1)
    return {"tr": float(eq[w1] / eq[w0] - 1.0), "tr_prev": float(eq[w1] / eq[w0 - 1] - 1.0) if w0 > 0 else np.nan,
            "cagr": float(cagr), "mdd": float(mdd), "expo": float(e.mean()), "slot": float(out["slot_use"]),
            "trades": int(out["trades"]), "mret": P11.monthly_returns(eq, marks)}


_S: dict = {}


def _init(sigs, nslots, closes, opens, ncal, wins, marks):
    _S.update(sigs=sigs, nslots=nslots, closes=closes, opens=opens, ncal=ncal, wins=wins, marks=marks)


def _sim(sig, n, seed, cost):
    """⭐ 唯一一個呼叫引擎的地方。成本用模組常數切換 ⇒ ⛔ 不改引擎、⛔ 跑完立刻還原（自測驗過不外洩）。"""
    R.COST = cost
    try:
        return R.simulate_mtm(sig, RULE, n, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                              return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero")
    finally:
        R.COST = COST_STD


def _one(args):
    s, c, t, wk, ctag, cost, seed = args
    out = _sim(_S["sigs"][(s, t, wk)], _S["nslots"][(s, c, t, wk)], seed, cost)
    rows = []
    for w in (_S["wins"] if wk == "*" else [wk]):
        w0, w1 = _S["wins"][w]
        rows.append({"S": s, "C": c, "T": t, "win": w, "cost": ctag, "seed": seed, **win_read(out, w0, w1, _S["marks"][w])})
    return rows


def _trades_at(args):
    """C0 搜尋用：給定 n_slots 跑一顆種子 ⇒ (n, trades, 槽位使用率, 曝險)。⛔ 一律含成本（§九-5）。"""
    s, t, wk, n, w = args
    out = _sim(_S["sigs"][(s, t, wk)], n, SEED0, COST_STD)
    w0, w1 = _S["wins"][w]
    r = win_read(out, w0, w1, _S["marks"][w])
    return {"n_slots": n, "trades": r["trades"], "slot_use": r["slot"], "expo": r["expo"]}


def choose_c0(pool, s: str, t: str, wk: str, w: str, n_max: int, log=print) -> tuple[int, pd.DataFrame]:
    """C0 ＝ 使 trades 達上限的**最小** n_slots（登錄 §九-5）。梯度先包夾、再二分。

    ⛔ 上限 tmax ＝ n_slots 取 n_max（＝ sig 筆數）那一跑的 trades（⇒ 槽位不可能不夠）。
    ⛔ 判準 trades ≥ C0_FRAC × tmax（0.999 寫死）。⭐ 回傳的梯度表就是 §四⑤ 要的證據。
    """
    ladder = sorted({min(n_max, 2 ** k) for k in range(3, int(np.log2(max(n_max, 8))) + 1)} | {n_max})
    tab = pd.DataFrame(pool.map(_trades_at, [(s, t, wk, n, w) for n in ladder])).sort_values("n_slots")
    tmax = int(tab["trades"].max()); need = C0_FRAC * tmax
    hi = int(tab.loc[tab["trades"] >= need, "n_slots"].min())
    below = tab.loc[tab["trades"] < need, "n_slots"]
    lo = int(below.max()) if len(below) else 1
    while hi - lo > 1:                                   # ⭐ 二分到最小值（⛔ 假設 trades 對 n_slots 單調，梯度表可自己查）
        mid = (lo + hi) // 2
        r = _trades_at((s, t, wk, mid, w))
        tab = pd.concat([tab, pd.DataFrame([r])], ignore_index=True)
        lo, hi = (lo, mid) if r["trades"] >= need else (mid, hi)
    tab = tab.sort_values("n_slots").reset_index(drop=True)
    log(f"  [C0] {s}/{t}/{wk} ⇒ n_slots {hi}（trades 上限 {tmax:,}，梯度 {len(tab)} 點）")
    return hi, tab


# ── 判定 ──
def main_effect(df: pd.DataFrame, mr: dict, factor: str, win: str, ctag: str) -> dict:
    """一個主效果：點估計（種子平均的 win_ret 差）＋ 判定（逐月配對差的月分群 CI）。

    ⛔ 配對＝同種子、同其餘兩個開關；先對【種子與 4 種組合】取平均 ⇒ 一條逐月序列 ⇒ P8.month_ci。
    """
    hi, lo = {"S": ("S1", "S0"), "C": ("C1", "C0"), "T": ("T1", "T0")}[factor]
    others = [f for f in ("S", "C", "T") if f != factor]
    d = df[(df["win"] == win) & (df["cost"] == ctag)]
    pt = float(d[d[factor] == hi]["tr"].mean() - d[d[factor] == lo]["tr"].mean())
    keys = sorted({tuple(r) for r in d[others].to_numpy()})
    seeds = sorted(d["seed"].unique())
    diffs = []
    for k in keys:
        cell_hi = {**dict(zip(others, k)), factor: hi}
        cell_lo = {**dict(zip(others, k)), factor: lo}
        for sd in seeds:
            a = mr[(cell_hi["S"], cell_hi["C"], cell_hi["T"], win, ctag, sd)]
            b = mr[(cell_lo["S"], cell_lo["C"], cell_lo["T"], win, ctag, sd)]
            diffs.append(a - b)
    dm = np.vstack(diffs).mean(axis=0)                   # ⭐ 先配對再平均 ⇒ 剩下的抽樣單位是【月】
    ci = P8.month_ci(dm)
    return {"factor": factor, "win": win, "cost": ctag, "point_pp": pt * 100, "n_pairs": len(diffs), **ci,
            "verdict": "測得出" if ci["detectable"] else "測不出"}


def attribution(df: pd.DataFrame, eff: pd.DataFrame, win: str, ctag: str) -> dict:
    """加法表：gap ＝ (S1,C1,T1) − (S0,C0,T0) ＝ S ＋ C ＋ T ＋ 殘差（⭐ 用種子平均，⛔ 中位數不可加）。"""
    d = df[(df["win"] == win) & (df["cost"] == ctag)]
    m = lambda s, c, t: float(d[(d["S"] == s) & (d["C"] == c) & (d["T"] == t)]["tr"].mean())
    gap = m("S1", "C1", "T1") - m("S0", "C0", "T0")
    e = eff[(eff["win"] == win) & (eff["cost"] == ctag)].set_index("factor")["point_pp"]
    resid = gap * 100 - float(e.sum())
    biggest = float(e.abs().max())
    return {"win": win, "cost": ctag, "gap_pp": gap * 100, "S_pp": float(e["S"]), "C_pp": float(e["C"]),
            "T_pp": float(e["T"]), "resid_pp": resid, "resid_share": abs(resid) / abs(gap * 100) if gap else np.nan,
            "resid_gt_max": bool(abs(resid) > biggest)}


def direct_equal_weight(sids, closes, opens, w0: int, w1: int, e0: int) -> dict:
    """⭐ 不經引擎的直算（§九-4）：等權買進持有的窗期報酬，兩個口徑各一份。

    直算A ＝ mean(close[w1] / close[w0] − 1)　　（策略線 cap5.py 的口徑：窗頭那一天的收盤起算）
    直算B ＝ mean(close[w1] / open[e0]  − 1)　　（本引擎的口徑：窗內第一個訊號月的建倉日開盤）
    ⇒ 兩者的差 ＝ 【一天 ＋ 開收差】這個已知口徑差本身，⛔ 它在看到錨點結果之前就算得出來。
    """
    a, b = [], []
    for s in sids:
        c1 = float(closes[s][w1]); c0 = float(closes[s][w0]); o0 = float(opens[s][e0])
        if np.isfinite(c1) and np.isfinite(c0) and c0 > 0:
            a.append(c1 / c0 - 1.0)
        if np.isfinite(c1) and np.isfinite(o0) and o0 > 0:
            b.append(c1 / o0 - 1.0)
    return {"n_A": len(a), "A": float(np.mean(a)), "n_B": len(b), "B": float(np.mean(b)), "gap_pp": (np.mean(b) - np.mean(a)) * 100}


def cell_table(df: pd.DataFrame) -> pd.DataFrame:
    """逐格彙總：⭐ 平均與中位並列（§九-7：加法表用平均、錨點用中位，⛔ 不是跑完才挑）。"""
    g = df.groupby(["win", "cost", "S", "C", "T"])
    out = g.agg(tr_mean=("tr", "mean"), tr_med=("tr", "median"), tr_p10=("tr", lambda x: x.quantile(0.1)),
                tr_p90=("tr", lambda x: x.quantile(0.9)), tr_prev_med=("tr_prev", "median"),
                cagr_med=("cagr", "median"), cagr_p10=("cagr", lambda x: x.quantile(0.1)), cagr_p90=("cagr", lambda x: x.quantile(0.9)),
                mdd_med=("mdd", "median"), mdd_p10=("mdd", lambda x: x.quantile(0.1)), mdd_p90=("mdd", lambda x: x.quantile(0.9)),
                expo_med=("expo", "median"), slot_med=("slot", "median"), trades_med=("trades", "median"), seeds=("seed", "size"))
    return out.reset_index()


def check_anchors(tab: pd.DataFrame) -> pd.DataFrame:
    """§四④：兩個錨點的對帳（⛔ 用【中位種子】，⛔ 容差 ±1pp 是策略線定的）。"""
    rows = []
    for (win, s, c, t, ctag), want in ANCHORS.items():
        r = tab[(tab["win"] == win) & (tab["S"] == s) & (tab["C"] == c) & (tab["T"] == t) & (tab["cost"] == ctag)]
        got = float(r["tr_med"].iloc[0]) if len(r) else np.nan
        rows.append({"錨點": f"{win} ({s},{c},{t}) {ctag}", "前測": want, "本線中位": got, "差pp": (got - want) * 100,
                     "過": bool(np.isfinite(got) and abs(got - want) <= ANCHOR_TOL)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    ap.add_argument("--part", choices=("all", "c0", "cells"), default="all",
                    help="c0＝只做 C0 的 n_slots 搜尋（寫 c0_ladder.csv）；cells＝讀已存的 n_slots 跑八格")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda s: print(s, flush=True)
    t_start = time.time()
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    wins = {k: win_bounds(cal, k) for k in WINDOWS}
    marks = {k: month_marks(cal, *wins[k]) for k in WINDOWS}
    _init({}, {}, closes, opens, ncal, wins, marks)      # ⭐ 主行程自己也要有 _S（C0 二分那幾步在主行程跑）
    log(f"[窗] " + "；".join(f"{k} [{v[0]},{v[1]}] {v[1] - v[0] + 1} 日／{len(marks[k]) - 1} 個月" for k, v in wins.items()))

    # ① sig：S1 ＝ 門檻B（⛔ 七個驗收數對不上就停）、S0 ＝ 全市場
    sigs = {}
    t0 = time.time()
    sig_b = P7.build_sig_gate_b(panel, cal, closes, opens, start=START, signal=SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig_b), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上策略線 1115 §1-2 ⇒ 停跑\n  want {want}\n  got  {got}")
    log(f"[sig] S1 門檻B ✅ 七個驗收數逐項相同：{len(sig_b):,} 筆／{sig_b['sid'].nunique():,} 檔／{sig_b['month'].nunique()} 月")
    sig_all = P7.build_sig_gate_b(panel, cal, closes, opens, start=START, signal=SIG_OF["S0"])
    log(f"[sig] S0 全市場 {len(sig_all):,} 筆／{sig_all['sid'].nunique():,} 檔／{sig_all['month'].nunique()} 月"
        f"（建 sig 共 {time.time() - t0:.0f}s）⇒ ⭐ §四⑦ 的訊號量")
    sigs[("S1", "T1", "*")] = sig_b; sigs[("S0", "T1", "*")] = sig_all
    # ⭐ §九-3 的對帳版（⛔ 只給錨點①看、⛔ 不進因子）：T1 的【窗內限定】——sig 只留 entry_pos ∈ 主格窗
    w0m, w1m = wins["主格窗"]
    sigs[("S1", "T1w", "主格窗")] = sig_b[(sig_b["entry_pos"] >= w0m) & (sig_b["entry_pos"] <= w1m)].reset_index(drop=True)
    for s, sg in (("S1", sig_b), ("S0", sig_all)):
        for w, (w0, w1) in wins.items():
            sigs[(s, "T0", w)] = sig_hold_to(sg, w0, w1, closes, opens)
            d = sigs[(s, "T0", w)]
            log(f"[sig] {s}/T0/{w}：建倉日 {int(d['entry_pos'].iloc[0])}（{cal[int(d['entry_pos'].iloc[0])].date()}）"
                f"、{len(d):,} 檔、持有到 {cal[w1].date()}")
    # ⭐ §九-9①：我方 2023-07 過閘門檔數 vs 策略線的 671
    n_670 = len(sigs[("S0", "T0", "主格窗")])
    log(f"[母體] 主格窗 S0 建倉日可買 {n_670:,} 檔（⚠ 策略線 §八② 寫 671 檔 ⇒ 差 {n_670 - 671:+d}，⛔ 明寫、⛔ 不當成同一個母體）")

    pool = Pool(a.procs, initializer=_init, initargs=(sigs, {}, closes, opens, ncal, wins, marks))
    try:
        # ② C0 的 n_slots（§九-5）
        c0_path = os.path.join(a.out, "c0_ladder.csv")
        if a.part in ("all", "c0") or not os.path.exists(c0_path):
            lad = []
            n_slots = {}
            for s in ("S1", "S0"):
                for t, wk, w in (("T1", "*", "全窗"), ("T0", "主格窗", "主格窗"), ("T0", "全窗", "全窗")):
                    key = (s, t, wk)
                    n, tab = choose_c0(pool, s, t, wk, w, len(sigs[key]), log)
                    n_slots[key] = n
                    lad.append(tab.assign(S=s, T=t, wk=wk, chosen=n))
            pd.concat(lad).to_csv(c0_path, index=False)
            pd.DataFrame([{"S": k[0], "T": k[1], "wk": k[2], "n_slots": v} for k, v in n_slots.items()]).to_csv(
                os.path.join(a.out, "c0_nslots.csv"), index=False)
            log(f"[C0] 寫入 {c0_path}（{time.time() - t_start:.0f}s）")
        else:
            n_slots = {(r["S"], r["T"], r["wk"]): int(r["n_slots"])
                       for _, r in pd.read_csv(os.path.join(a.out, "c0_nslots.csv")).iterrows()}
        if a.part == "c0":
            return
        NS = {}
        for s, c, t in CORNERS:
            for wk in (["*"] if t == "T1" else list(WINDOWS)):
                NS[(s, c, t, wk)] = N_C1 if c == "C1" else n_slots[(s, t, wk)]
        NS[("S1", "C1", "T1w", "主格窗")] = N_C1
        _S.update(sigs=sigs, nslots=NS)
        pool.close(); pool.join()
        pool = Pool(a.procs, initializer=_init, initargs=(sigs, NS, closes, opens, ncal, wins, marks))

        # ③ 八個角落 × 兩個窗 × 兩種成本 × R 顆種子
        jobs = [(s, c, t, wk, ctag, cost, SEED0 + r)
                for s, c, t in CORNERS for wk in (["*"] if t == "T1" else list(WINDOWS))
                for ctag, cost in COSTS for r in range(a.reps)]
        log(f"[跑] {len(jobs):,} 個工作（8 角落 × 2 窗 × 2 成本 × {a.reps} 種子）")
        jobs += [("S1", "C1", "T1w", "主格窗", ctag, cost, SEED0 + r) for ctag, cost in COSTS for r in range(a.reps)]
        rows = []
        t0 = time.time()
        for i, rs in enumerate(pool.imap_unordered(_one, jobs, chunksize=2), 1):
            rows.extend(rs)
            if i % max(1, len(jobs) // 20) == 0:
                log(f"  {i:,}/{len(jobs):,}（{time.time() - t0:.0f}s）")
    finally:
        pool.close(); pool.join()
    df = pd.DataFrame(rows)
    mr = {(r["S"], r["C"], r["T"], r["win"], r["cost"], r["seed"]): r["mret"] for r in rows}
    df = df.drop(columns=["mret"])
    xdf = df[df["T"] == "T1w"].copy(); df = df[df["T"] != "T1w"].copy()   # ⛔ 對帳版不進因子
    df.to_csv(os.path.join(a.out, "cells_by_seed.csv.gz"), index=False)
    tab = cell_table(df); tab.to_csv(os.path.join(a.out, "cells.csv"), index=False)
    xtab = cell_table(xdf); xtab.to_csv(os.path.join(a.out, "cells_T1w.csv"), index=False)

    # ④ 錨點（⛔ 否證①：對不上就停，⛔ 不算主效果）
    e0_main = int(sigs[("S0", "T0", "主格窗")]["entry_pos"].iloc[0])
    dirc = direct_equal_weight(list(sigs[("S0", "T0", "主格窗")]["sid"]), closes, opens, *wins["主格窗"], e0_main)
    anc = check_anchors(tab); anc.to_csv(os.path.join(a.out, "anchors.csv"), index=False)
    log("\n[錨點]\n" + anc.to_string(index=False))
    log(f"[口徑差] 直算A（close[{wins['主格窗'][0]}]起，{dirc['n_A']} 檔）{dirc['A'] * 100:+.2f}%／"
        f"直算B（open[{e0_main}]起，{dirc['n_B']} 檔）{dirc['B'] * 100:+.2f}% ⇒ 差 {dirc['gap_pp']:+.2f}pp")
    if not bool(anc["過"].all()):
        L = anchor_report(anc, dirc, tab, xtab, cal, wins, e0_main, a.reps)
        open(os.path.join(a.out, "P12_ANCHOR_FAIL.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
        raise SystemExit("⛔ 否證①：錨點對不上 ⇒ 停止、本件不出結論（已寫 P12_ANCHOR_FAIL.md）")

    # ⑤ 主效果＋加法表（⛔ 只有三個主效果進判定）
    eff = pd.DataFrame([main_effect(df, mr, f, w, ct) for w in WINDOWS for ct, _ in COSTS for f in ("S", "C", "T")])
    eff.to_csv(os.path.join(a.out, "effects.csv"), index=False)
    att = pd.DataFrame([attribution(df, eff, w, ct) for w in WINDOWS for ct, _ in COSTS])
    att.to_csv(os.path.join(a.out, "attribution.csv"), index=False)
    lad_tab = pd.read_csv(os.path.join(a.out, "c0_ladder.csv"))
    L = report(tab, xtab, eff, att, anc, dirc, lad_tab, sigs, closes, opens, cal, wins, marks, a.reps, e0_main, n_670,
               time.time() - t_start)
    open(os.path.join(a.out, "P12_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"寫入 {os.path.join(a.out, 'P12_REPORT.md')}（總計 {time.time() - t_start:.0f}s）")


# ── 報告 ──
def _hdr(reps: int) -> list:
    return [f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。"
            f"判準＝`backtest/PREREGP12.md`（策略線 1500 seq=2 全文 §〇~§八 ＋ 回測線落地登錄 §九）。",
            f"引擎 `research11.simulate_mtm`（⛔ 未改）；種子 `default_rng({SEED0} + r)`，R={reps}；"
            f"`pick=None／cap_fn=None／d_max=None／queue_days=0／cash_mode=\"zero\"／stop=None`（§八⑦）。", ""]


def _anchor_block(anc: pd.DataFrame, dirc: dict, xtab: pd.DataFrame, cal, wins: dict, e0: int) -> list:
    w0, w1 = wins["主格窗"]
    L = ["| 錨點 | 前測（策略線） | 本線【中位種子】 | 差 | 容差 | 判 |", "|---|---:|---:|---:|---:|:--:|"]
    for r in anc.itertuples():
        L.append(f"| {getattr(r, '錨點')} | {getattr(r, '前測') * 100:+.2f}% | {getattr(r, '本線中位') * 100:+.2f}% | "
                 f"{getattr(r, '差pp'):+.2f}pp | ±{ANCHOR_TOL * 100:.0f}pp | {'✅' if getattr(r, '過') else '⛔'} |")
    L += ["", f"⭐ **口徑差（§九-4，⛔ 在看到錨點結果之前就算得出來）**：同一批 {dirc['n_A']:,} 檔等權買進持有、不經引擎直算——",
          f"- 直算A（策略線口徑：{cal[w0].date()} **收盤**起算）＝ **{dirc['A'] * 100:+.2f}%**（{dirc['n_A']:,} 檔）",
          f"- 直算B（本引擎口徑：{cal[e0].date()} **開盤**起算，⚠ 比窗頭晚一個交易日）＝ **{dirc['B'] * 100:+.2f}%**（{dirc['n_B']:,} 檔）",
          f"- ⇒ 兩個口徑本身差 **{dirc['gap_pp']:+.2f}pp**。", ""]
    if len(xtab):
        L += [f"⭐ **T1 的口徑對帳（§九-3，⛔ 只給錨點①看、⛔ 不進因子）**：主格窗 (S1,C1,T1)", "",
              "| T1 口徑 | 窗期總報酬 中位 | 平均 | p10～p90 | 分母 equity[w0−1] 版 |", "|---|---:|---:|---|---:|"]
        for r in xtab[xtab["cost"] == "成本0.585%"].itertuples():
            L.append(f"| 窗內限定（sig 只留 entry ∈ 窗；窗頭空手） | {r.tr_med * 100:+.2f}% | {r.tr_mean * 100:+.2f}% | "
                     f"{r.tr_p10 * 100:+.1f}～{r.tr_p90 * 100:+.1f} | {r.tr_prev_med * 100:+.2f}% |")
        L.append("")
    return L


def anchor_report(anc, dirc, tab, xtab, cal, wins, e0, reps) -> list:
    """⛔ 否證①觸發時寫這一份：**只有對帳，⛔ 沒有任何主效果、沒有結論**。"""
    L = ["# PREREGP12：⛔ 錨點對不上 ⇒ **本件不出結論**（否證①）", ""] + _hdr(reps)
    L += ["⛔ 依登錄 §六① 逐字：「任一錨點對不上 ⇒ 停止，本件不出結論」。",
          "⇒ ⭐ 本檔**只**列對帳所需的數字；主效果、加法表**沒有算**（⛔ 不是算了不寫）。", ""]
    L += ["## 一、錨點對帳（§四④）", ""] + _anchor_block(anc, dirc, xtab, cal, wins, e0)
    L += ["## 二、主格窗八格的窗期總報酬（⛔ 只作對帳線索，⛔ 不是結論）", "",
          "| 成本 | S | C | T | 中位 | 平均 | p10～p90 |", "|---|---|---|---|---:|---:|---|"]
    for r in tab[tab["win"] == "主格窗"].itertuples():
        L.append(f"| {r.cost} | {r.S} | {r.C} | {r.T} | {r.tr_med * 100:+.2f}% | {r.tr_mean * 100:+.2f}% | "
                 f"{r.tr_p10 * 100:+.1f}～{r.tr_p90 * 100:+.1f} |")
    L += ["", "⇒ ⛔ 回測線**不自行放寬容差、不自行改錨點**（§九-4）⇒ 這一份交策略線裁定。", ""]
    return L


def _cells_block(tab: pd.DataFrame, win: str) -> list:
    L = [f"### {win}", "",
         "| 成本 | S | C | T | 窗期總報酬 中位 | 平均 | p10～p90 | 年化 中位 | 最大回落 中位（p10～p90） | 平均曝險 | 槽位使用率 | 進場筆數 中位 |",
         "|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    for r in tab[tab["win"] == win].itertuples():
        L.append(f"| {r.cost} | {r.S} | {r.C} | {r.T} | {r.tr_med * 100:+.2f}% | {r.tr_mean * 100:+.2f}% | "
                 f"{r.tr_p10 * 100:+.1f}～{r.tr_p90 * 100:+.1f} | {r.cagr_med * 100:+.2f}% | "
                 f"{r.mdd_med * 100:.1f}%（{r.mdd_p10 * 100:.1f}～{r.mdd_p90 * 100:.1f}） | {r.expo_med * 100:.1f}% | "
                 f"{r.slot_med:.3f} | {r.trades_med:,.0f} |")
    return L + [""]


def report(tab, xtab, eff, att, anc, dirc, lad, sigs, closes, opens, cal, wins, marks, reps, e0, n_670, secs) -> list:
    L = ["# PREREGP12：25.7pp 拆成【選股 S／集中度 C／時點 T】——回測線落地執行結果", ""] + _hdr(reps)
    L += ["⛔ **本件是【歸屬】，⛔ 不是尋找更好的設定**（§七①）⇒ 任何一格好看都**不構成**建議。",
          "⛔ **本件對最大回落天生沉默**（§七③〈九十五〉：逐種子配對消掉時點效應）⇒ 判定只談【窗期總報酬】；",
          "　 表裡的回落欄只是描述（⭐ 它只有種子帶，⛔ 不是抽樣分佈）。",
          f"⛔ **主格窗含選擇效應**（§二：它是用組合自己的高點選出來的）⇒ ⛔ 不可當無偏估計；有效樣本數＝**1 個窗**（§七②〈九十八〉）。", "",
          "---", "", "## 一、⛔⛔ 錨點對帳（§四④；⛔ 任一個沒過就不會有下面幾節）", ""]
    L += _anchor_block(anc, dirc, xtab, cal, wins, e0)
    L += ["---", "", "## 二、八個角落逐格（§四①②③）", "",
          "⚠ 「進場筆數」：T1 是**整條日曆那一跑的總筆數**（⛔ 不是窗內的，§九-9②；本引擎沒有回傳窗內筆數）；",
          "　 T0 就是建倉那一批。⭐ 成本那一塊改由【成本 0 對照】直接量（§四⑥，見第五節）——那是更直接的儀器。",
          "⚠ 「平均持有天數」是**算出來的**（§九-9③）：T1 ＝ 119 個交易日（持有 120 根、⛔ 沒開停損）；"
          f"T0 ＝ 窗尾 − 建倉日（主格窗 {wins['主格窗'][1] - e0} 天／全窗 {wins['全窗'][1] - int(sigs[('S1', 'T0', '全窗')]['entry_pos'].iloc[0])} 天）。",
          "⭐ 「平均曝險」＝ 持股市值 ÷ 權益 的窗內日均（§七⑧ 逐字：⛔ 不可用槽位使用率代替）。", ""]
    for w in WINDOWS:
        L += _cells_block(tab, w)
    L += ["---", "", "## 三、C0【買光】的 n_slots 與證據（§四⑤）", "",
          "⭐ 機器定義（§九-5）：C0 ＝ 使進場筆數達上限的**最小** n_slots（判準 trades ≥ 0.999×上限，⛔ 0.999 寫死）。",
          "⛔ 為什麼不照字面「設到槽位使用率不再上升」：本引擎裡 n_slots 越大、槽位使用率只會**下降**；",
          "　 而 slot ＝ equity/n_slots ⇒ n_slots 開太大 ⇒ 買得光但**曝險被稀釋**（下表的曝險欄直接看得到）。", "",
          "| S | T | 窗 | n_slots | 進場筆數 | 槽位使用率 | 平均曝險 | 選中 |", "|---|---|---|---:|---:|---:|---:|:--:|"]
    for r in lad.sort_values(["S", "T", "wk", "n_slots"]).itertuples():
        L.append(f"| {r.S} | {r.T} | {r.wk} | {r.n_slots:,} | {r.trades:,} | {r.slot_use:.3f} | {r.expo * 100:.1f}% | "
                 f"{'⭐' if r.n_slots == r.chosen else ''} |")
    L += ["", "---", "", "## 四、⭐⭐ 判定：三個主效果（§三）", "",
          "⛔ 判定用 **CI 含不含 0**（⛔ 不看點估計大小，〈九十七〉）。配對＝同種子、同其餘兩個開關 ⇒ "
          "先對【種子 × 4 種組合】取平均 ⇒ 得到一條**逐月**序列 ⇒ 月分群 SE 的 95% CI（抽樣單位是月）。",
          "⛔ 多重檢定：判定格 3 個（× 2 窗），虛無期望 0.15 格／窗。",
          "⚠ 逐月 CI 與下一節的加法表**不是同一個量**（前者是月均差、會複利到不等於總報酬差）⇒ ⛔ 不可互相代替。", "",
          "| 窗 | 成本 | 因子 | 逐月配對差（月均） | 95% CI | 月數 | 正的月數 | 判 | 點估計（窗期總報酬差） |",
          "|---|---|---|---:|---|---:|---:|:--:|---:|"]
    for r in eff.sort_values(["win", "cost", "factor"]).itertuples():
        L.append(f"| {r.win} | {r.cost} | {r.factor} | {r.diff_pp:+.3f}pp | {r.lo_pp:+.3f}～{r.hi_pp:+.3f}pp | "
                 f"{r.n_months} | {r.pos_months} | {'✅ 測得出' if r.detectable else '⛔ 測不出'} | {r.point_pp:+.2f}pp |")
    L += ["", "## 五、歸屬加法表（§三末）", "",
          "gap ＝ (S1,C1,T1) − (S0,C0,T0) ＝ S ＋ C ＋ T ＋ 殘差（⭐ 用**種子平均**，⛔ 中位數不可加）。", "",
          "| 窗 | 成本 | gap | S | C | T | 殘差 | 殘差佔 | 殘差 > 最大主效果？ |", "|---|---|---:|---:|---:|---:|---:|---:|:--:|"]
    for r in att.sort_values(["win", "cost"]).itertuples():
        L.append(f"| {r.win} | {r.cost} | {r.gap_pp:+.2f}pp | {r.S_pp:+.2f}pp | {r.C_pp:+.2f}pp | {r.T_pp:+.2f}pp | "
                 f"{r.resid_pp:+.2f}pp | {r.resid_share * 100:.0f}% | {'⛔ 是 ⇒ 判【拆不開】' if r.resid_gt_max else '否'} |")
    L += ["", "⚠ 前測的 25.7pp 是【錨點①含成本 − 錨點②成本 0】⇒ **兩邊成本口徑不同**（§四④）。",
          "⇒ ⭐ 上表的 gap 是**同一個成本口徑**內的差 ⇒ ⛔ 它不會剛好等於 25.7pp，兩種成本各報一列。", ""]
    # 成本（§四⑥）
    L += ["---", "", "## 六、成本那一塊有多大（§四⑥；⛔ 只作描述）", "",
          "| 窗 | S | C | T | 含成本 | 成本0 | 成本吃掉 |", "|---|---|---|---|---:|---:|---:|"]
    p = tab.pivot_table(index=["win", "S", "C", "T"], columns="cost", values="tr_med")
    for idx, r in p.iterrows():
        L.append(f"| {idx[0]} | {idx[1]} | {idx[2]} | {idx[3]} | {r['成本0.585%'] * 100:+.2f}% | {r['成本0'] * 100:+.2f}% | "
                 f"{(r['成本0.585%'] - r['成本0']) * 100:+.2f}pp |")
    # §四⑦⑧
    w0m, w1m = wins["主格窗"]
    no_trade = sum(1 for s in sigs[("S0", "T0", "主格窗")]["sid"] if not np.isfinite(float(opens[s][w1m])))
    L += ["", "---", "", "## 七、訊號量與執行（§四⑦）", "",
          f"- S1 門檻B：**{len(sigs[('S1', 'T1', '*')]):,}** 筆訊號（{sigs[('S1', 'T1', '*')]['sid'].nunique():,} 檔）",
          f"- S0 全市場：**{len(sigs[('S0', 'T1', '*')]):,}** 筆訊號（{sigs[('S0', 'T1', '*')]['sid'].nunique():,} 檔）"
          f" ⇒ 約 S1 的 {len(sigs[('S0', 'T1', '*')]) / len(sigs[('S1', 'T1', '*')]):.0f} 倍",
          f"- 本趟總執行時間 **{secs / 60:.0f} 分鐘**（含 C0 搜尋）⇒ ⭐ 沒有觸發否證⑤（不必改成分層抽樣）。", "",
          "## 八、倖存者與母體（§四⑧、§九-9①④）", "",
          f"- ⚠ 主格窗建倉日我方可買 **{n_670:,}** 檔，策略線 §八② 寫 **671** 檔 ⇒ **差 {n_670 - 671:+d} 檔**，來源未查 ⇒ "
          "⛔ 明寫在這裡，⛔ 不當成同一個母體。",
          f"- 這 {n_670:,} 檔裡，窗尾那一天（{cal[w1m].date()}）**沒有開盤價（＝當天沒有成交）** 的有 **{no_trade}** 檔 ⇒ "
          "處置＝`closes` 已 ffill 到最後成交價（⛔ 不是 −100%、⛔ 也不是丟掉），與策略線 §八② 同一種處置。",
          "- ⛔ 而**策略那一側**（門檻B 候選池）的倖存者處理【本件未查】⇒ 仍是已知偏差（§七⑤ 逐字）。", "",
          "## 九、⛔ 範圍限制（照抄登錄，⛔ 不刪）", "",
          "- ⛔ 本件是歸屬、不是找設定；任何一格好看都不是建議（§七①）。",
          "- ⛔ 有效樣本數：主格窗只有 1 個窗；全窗是第二個資料點，⛔ 不是 111 個（§七②）。",
          "- ⛔ 對最大回落天生沉默（§七③）。⛔ 33.5pp（等權 vs 市值加權）不在本件範圍（§七④）。",
          "- ⛔ 成本 0.585%、滑價未計（§七⑤）。⛔ 前測對照組沒有成本也沒有換股 ⇒ 25.7pp 是【上界】（§七⑥）。",
          "- ⛔ T0 只取窗內第一個訊號月 ⇒ 它是【一次性建倉】，不是完美的買進持有（§七⑦）。",
          "- ⛔ C0 有現金拖累 ⇒ 不等於 100% 曝險的買進持有（§七⑧）⇒ 曝險欄已列。",
          "- ⛔ T 這個開關**必然**含有「窗頭有沒有倉位」這一項（§九-3）⇒ 第一節的【窗內限定版】就是它的量。", ""]
    return L


if __name__ == "__main__":
    main()
