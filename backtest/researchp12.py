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
# ⭐ K線分析線 1700 裁定① ＝ 錨點①【拆成兩個】：①-引擎 對 ⓒ（逐種子自己最深的回落）／①-判定口徑【不設】
ANCHOR_OWN_DD = -0.409           # 錨點①-引擎：(S1,C1,T1) 含成本的【自己最深回落】中位（§十-1）
ANCHORS = {("主格窗", "S0", "C0a", "T0", "成本0"): -0.1521}       # §四④ 錨點②（⭐ 成本設 0 對帳）
ANCHOR_TOL = 0.01                # ±1pp（⛔ 策略線定的，⛔ 回測線不得放寬）
COSTS = (("成本0.585%", COST_STD), ("成本0", 0.0))
# ⭐ 裁定④（§十-4）：C0 兩版。C0a ＝ 曝險對齊（⭐ 判定用）／C0f ＝ 字面最小 n_slots（⛔ 只作描述）
C_LEVELS = ("C1", "C0a", "C0f")
FACTOR_LEVELS = {"S": ("S1", "S0"), "C": ("C1", "C0a"), "T": ("T1", "T0")}   # ⛔ C0f 不進因子
CORNERS = [(s, c, t) for s in ("S1", "S0") for c in C_LEVELS for t in ("T1", "T0")]
GAP_REF_PP = -13.25              # 裁定②：被拆的量 ＝ 同窗差（⛔ 不是 25.6pp；⚠ 它是【中位】口徑，加法表是【平均】）
# 裁定③（§十-3）：先驗由 25.7pp 版【按比例機械換算】，⛔ 未重新判斷方向或量級
PRIOR_PP = {"S": (-10.3, -5.2), "T": (-5.2, -1.5), "殘差": (-4.0, -1.3)}
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


def caps_buy_all(sig: pd.DataFrame, ncal: int) -> np.ndarray:
    """C0a 的逐日容量 ＝【若全部買光，當天會持有的相異部位數】（下限 1；§十-4）。

    ⭐ 用引擎**同一條**規則推：逐日先出場（`exit_pos <= t`）、再把當天 entry_pos 的候選裡
       【尚未持有】的收進來（⛔ 已持有的不重入 ＝ `~cand["sid"].isin(held)`）。
    ⇒ 容量 ≥ 當天該有的部位數 ⇒ 沒有候選被【槽位】擋掉；slot ＝ equity ÷ 當日部位數 ⇒ 曝險 ~100%。
    ⚠ ⛔ 現金仍可能擋（`amt = min(slot, cash)`，§八⑥(b)）⇒ 買光到不到位要**量**，⛔ 不是假設。
    """
    by: dict = {}
    for r in sig.itertuples():
        by.setdefault(int(r.entry_pos), []).append((r.sid, int(getattr(r, f"xpos_{RULE}"))))
    caps = np.ones(ncal, int); held: dict = {}
    for t in range(ncal):
        for sid in [k for k, x in held.items() if x <= t]:
            held.pop(sid)
        for sid, x in by.get(t, []):
            if sid not in held and x > t:
                held[sid] = x
        caps[t] = max(1, len(held))
    return caps


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


def _init(sigs, nslots, closes, opens, ncal, wins, marks, cal=None):
    _S.update(sigs=sigs, nslots=nslots, closes=closes, opens=opens, ncal=ncal, wins=wins, marks=marks, cal=cal)


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
    own = deepest_episode(out["equity"], out["first"], out["end"], _S["cal"])[2] if wk == "*" else np.nan
    rows = []
    for w in (_S["wins"] if wk == "*" else [wk]):
        w0, w1 = _S["wins"][w]
        rows.append({"S": s, "C": c, "T": t, "win": w, "cost": ctag, "seed": seed, "own_dd": own,
                     **win_read(out, w0, w1, _S["marks"][w])})
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
    tab["tmax"] = tmax
    log(f"  [C0] {s}/{t}/{wk} ⇒ n_slots {hi}（trades 上限 {tmax:,}，梯度 {len(tab)} 點）")
    return hi, tab


# ── 判定 ──
def main_effect(df: pd.DataFrame, mr: dict, factor: str, win: str, ctag: str, arms: dict | None = None) -> dict:
    """一個主效果：點估計（種子平均的 win_ret 差）＋ 判定（逐月配對差的月分群 CI）。

    ⛔ 配對＝同種子、同其餘兩個開關；先對【種子與 4 種組合】取平均 ⇒ 一條逐月序列 ⇒ P8.month_ci。
    """
    hi, lo = FACTOR_LEVELS[factor]
    others = [f for f in ("S", "C", "T") if f != factor]
    d = df[(df["win"] == win) & (df["cost"] == ctag)]
    for k, v in FACTOR_LEVELS.items():
        d = d[d[k].isin(v)]                      # ⛔ C0f（描述版）不進因子（§十-4）
    for k, v in (arms or {}).items():
        d = d[d[k] == v]                         # 裁定⑤：T 的主效果要報【不含 S1 臂】那一版
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
    return {"factor": factor, "win": win, "cost": ctag, "arm": "全部" if not arms else "／".join(arms.values()),
            "point_pp": pt * 100, "n_pairs": len(diffs), **ci,
            "verdict": "測得出" if ci["detectable"] else "測不出"}


def attribution(df: pd.DataFrame, eff: pd.DataFrame, win: str, ctag: str) -> dict:
    """加法表：gap ＝ (S1,C1,T1) − (S0,C0,T0) ＝ S ＋ C ＋ T ＋ 殘差（⭐ 用種子平均，⛔ 中位數不可加）。"""
    d = df[(df["win"] == win) & (df["cost"] == ctag)]
    m = lambda s, c, t: float(d[(d["S"] == s) & (d["C"] == c) & (d["T"] == t)]["tr"].mean())
    gap = m("S1", "C1", "T1") - m("S0", "C0a", "T0")
    e = eff[(eff["win"] == win) & (eff["cost"] == ctag) & (eff["arm"] == "全部")].set_index("factor")["point_pp"]
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


def check_anchors(tab: pd.DataFrame, own_med: float) -> pd.DataFrame:
    """§四④ ＋ K線分析線 1700 裁定①：兩個錨點（⛔ 用【中位種子】，⛔ 容差 ±1pp 是策略線定的）。

    ①-引擎　(S1,C1,T1) 含成本的【逐種子自己最深回落】對 −40.9%（⭐ 不是固定窗的窗期報酬）
    ②　　　 (S0,C0a,T0) 成本 0 的窗期總報酬對 −15.21%
    ⛔ ①-判定口徑【不設錨點】（裁定 §1-2：沒有人事先算過那個量 ⇒ 拿本趟的值回頭當目標＝自己對自己）
    """
    rows = [{"錨點": "①-引擎 主格窗 (S1,C1,T1) 含成本【自己最深回落 ⓒ】", "前測": ANCHOR_OWN_DD, "本線中位": own_med,
             "差pp": (own_med - ANCHOR_OWN_DD) * 100,
             "過": bool(np.isfinite(own_med) and abs(own_med - ANCHOR_OWN_DD) <= ANCHOR_TOL)}]
    for (win, s, c, t, ctag), want in ANCHORS.items():
        r = tab[(tab["win"] == win) & (tab["S"] == s) & (tab["C"] == c) & (tab["T"] == t) & (tab["cost"] == ctag)]
        got = float(r["tr_med"].iloc[0]) if len(r) else np.nan
        rows.append({"錨點": f"② {win} ({s},{c},{t}) {ctag}【窗期總報酬 ⓐ】", "前測": want, "本線中位": got,
                     "差pp": (got - want) * 100, "過": bool(np.isfinite(got) and abs(got - want) <= ANCHOR_TOL)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    ap.add_argument("--part", choices=("all", "c0", "cells", "anchor-diag"), default="all",
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
    _init({}, {}, closes, opens, ncal, wins, marks, cal)      # ⭐ 主行程自己也要有 _S（C0 二分那幾步在主行程跑）
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

    _S.update(sigs=sigs)                 # ⭐ 主行程的 _S 也要拿到 sigs（C0 二分那幾步在主行程跑）
    pool = Pool(a.procs, initializer=_init, initargs=(sigs, {}, closes, opens, ncal, wins, marks, cal))
    try:
        # ② C0 的 n_slots（§九-5）
        c0_path = os.path.join(a.out, "c0_ladder.csv")
        if a.part in ("all", "c0") or not os.path.exists(c0_path):
            lad = []
            n_slots = {}; tmax_of = {}
            for s in ("S1", "S0"):
                for t, wk, w in (("T1", "*", "全窗"), ("T0", "主格窗", "主格窗"), ("T0", "全窗", "全窗")):
                    key = (s, t, wk)
                    n, tab = choose_c0(pool, s, t, wk, w, len(sigs[key]), log)
                    n_slots[key] = n; tmax_of[key] = int(tab["tmax"].iloc[0])
                    lad.append(tab.assign(S=s, T=t, wk=wk, chosen=n))
            pd.concat(lad).to_csv(c0_path, index=False)
            pd.DataFrame([{"S": k[0], "T": k[1], "wk": k[2], "n_slots": v, "tmax": tmax_of[k]}
                          for k, v in n_slots.items()]).to_csv(os.path.join(a.out, "c0_nslots.csv"), index=False)
            log(f"[C0] 寫入 {c0_path}（{time.time() - t_start:.0f}s）")
        else:
            _c0 = pd.read_csv(os.path.join(a.out, "c0_nslots.csv"))
            n_slots = {(r["S"], r["T"], r["wk"]): int(r["n_slots"]) for _, r in _c0.iterrows()}
            tmax_of = {(r["S"], r["T"], r["wk"]): int(r["tmax"]) for _, r in _c0.iterrows()}
        if a.part == "c0":
            return
        if a.part == "anchor-diag":       # ⛔ 只在錨點沒過之後跑：查，⛔ 不出結論
            dg = pd.DataFrame(pool.map(_diag_one, [(SEED0 + r, COST_STD) for r in range(a.reps)]))
            dg["peak_date"] = [str(cal[i].date()) for i in dg["peak_pos"]]
            dg["trough_date"] = [str(cal[i].date()) for i in dg["trough_pos"]]
            dg.to_csv(os.path.join(a.out, "anchor_diag.csv"), index=False)
            cp = os.path.join(a.out, "cells.csv")                 # ⭐ (S0,C0,T0) 含成本那一格從結果檔讀，⛔ 不寫死
            ct = pd.read_csv(cp)
            bh = float(ct[(ct["win"] == "主格窗") & (ct["cost"] == "成本0.585%") & (ct["S"] == "S0")
                          & (ct["C"] == "C0") & (ct["T"] == "T0")]["tr_med"].iloc[0])
            L = diag_report(dg, cal, wins, ANCHORS[("主格窗", "S1", "C1", "T1", "成本0.585%")], a.reps, bh)
            open(os.path.join(a.out, "P12_ANCHOR_DIAG.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
            log("\n".join(L))
            return
        NS = {}
        ev = []
        for s, c, t in CORNERS:
            for wk in (["*"] if t == "T1" else list(WINDOWS)):
                if c == "C1":
                    NS[(s, c, t, wk)] = N_C1
                elif c == "C0f":
                    NS[(s, c, t, wk)] = n_slots[(s, t, wk)]
                else:                                   # C0a：逐日容量（§十-4）
                    NS[(s, c, t, wk)] = caps_buy_all(sigs[(s, t, wk)], ncal)
        # ⭐ 必報⑤＋裁定④的證據：三種容量各跑一顆種子，看【買光到不到位】與【曝險】
        for s in ("S1", "S0"):
            for t, wk, w in (("T1", "*", "全窗"), ("T0", "主格窗", "主格窗"), ("T0", "全窗", "全窗")):
                sg = sigs[(s, t, wk)]
                narrow = P11.caps_series(sg, 1.0, ncal)[0]      # ⛔ 字面【窄讀】：當天新出現的訊號數（⭐ 沒有第二份實作）
                for lab, n in (("C0f 字面最小 n_slots", n_slots[(s, t, wk)]),
                               ("C0a 對齊（在場候選數）", NS[(s, "C0a", t, wk)]),
                               ("窄讀（當日新訊號數）", narrow)):
                    o = _sim(sg, n, SEED0, COST_STD)
                    w0, w1 = wins[w]; r = win_read(o, w0, w1, marks[w])
                    ev.append({"S": s, "T": t, "wk": wk, "版本": lab, "trades": r["trades"], "trades上限": int(tmax_of[(s, t, wk)]),
                               "買光率": r["trades"] / max(1, tmax_of[(s, t, wk)]), "曝險": r["expo"], "槽位使用率": r["slot"],
                               "容量": (f"逐日 {int(np.min(n))}~{int(np.max(n))}" if not isinstance(n, (int, np.integer)) else int(n))})
                    log(f"  [容量] {s}/{t}/{wk} {lab}：trades {r['trades']:,}／上限 {tmax_of[(s, t, wk)]:,}"
                        f"、曝險 {r['expo'] * 100:.1f}%")
        pd.DataFrame(ev).to_csv(os.path.join(a.out, "capacity_evidence.csv"), index=False)
        NS[("S1", "C1", "T1w", "主格窗")] = N_C1
        _S.update(sigs=sigs, nslots=NS)
        pool.close(); pool.join()
        pool = Pool(a.procs, initializer=_init, initargs=(sigs, NS, closes, opens, ncal, wins, marks, cal))

        # ③ 八個角落 × 兩個窗 × 兩種成本 × R 顆種子
        jobs = [(s, c, t, wk, ctag, cost, SEED0 + r)
                for s, c, t in CORNERS for wk in (["*"] if t == "T1" else list(WINDOWS))
                for ctag, cost in COSTS for r in range(a.reps)]
        jobs += [("S1", "C1", "T1w", "主格窗", ctag, cost, SEED0 + r) for ctag, cost in COSTS for r in range(a.reps)]
        log(f"[跑] {len(jobs):,} 個工作（{len(CORNERS)} 格 × 窗 × 2 成本 × {a.reps} 種子，含 T1w 對帳版）")
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
    own = df[(df["win"] == "主格窗") & (df["cost"] == "成本0.585%") & (df["S"] == "S1") & (df["C"] == "C1") & (df["T"] == "T1")]["own_dd"]
    own_med = float(own.median())
    anc = check_anchors(tab, own_med); anc.to_csv(os.path.join(a.out, "anchors.csv"), index=False)
    log("\n[錨點]\n" + anc.to_string(index=False))
    log(f"[口徑差] 直算A（close[{wins['主格窗'][0]}]起，{dirc['n_A']} 檔）{dirc['A'] * 100:+.2f}%／"
        f"直算B（open[{e0_main}]起，{dirc['n_B']} 檔）{dirc['B'] * 100:+.2f}% ⇒ 差 {dirc['gap_pp']:+.2f}pp")
    if not bool(anc["過"].all()):
        L = anchor_report(anc, dirc, tab, xtab, cal, wins, e0_main, a.reps)
        open(os.path.join(a.out, "P12_ANCHOR_FAIL.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
        raise SystemExit("⛔ 否證①：錨點對不上 ⇒ 停止、本件不出結論（已寫 P12_ANCHOR_FAIL.md）")

    # ⑤ 主效果＋加法表（⛔ 只有三個主效果進判定；⭐ T 依裁定⑤ 多報一版【不含 S1 臂】）
    jobs_e = [(f, w, ct, None) for w in WINDOWS for ct, _ in COSTS for f in ("S", "C", "T")]
    jobs_e += [("T", w, ct, {"S": "S0"}) for w in WINDOWS for ct, _ in COSTS]
    eff = pd.DataFrame([main_effect(df, mr, f, w, ct, arms) for f, w, ct, arms in jobs_e])
    eff.to_csv(os.path.join(a.out, "effects.csv"), index=False)
    att = pd.DataFrame([attribution(df, eff, w, ct) for w in WINDOWS for ct, _ in COSTS])
    att.to_csv(os.path.join(a.out, "attribution.csv"), index=False)
    lad_tab = pd.read_csv(os.path.join(a.out, "c0_ladder.csv"))
    ev_tab = pd.read_csv(os.path.join(a.out, "capacity_evidence.csv"))
    L = report(tab, xtab, eff, att, anc, dirc, lad_tab, ev_tab, sigs, closes, opens, cal, wins, marks, a.reps, e0_main,
               n_670, own_med, time.time() - t_start)
    open(os.path.join(a.out, "P12_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"寫入 {os.path.join(a.out, 'P12_REPORT.md')}（總計 {time.time() - t_start:.0f}s）")


# ── ⛔ 錨點沒過之後的【查】（§六①「停下來查」；⭐ 只查、⛔ 不出結論、⛔ 不改任何登錄） ──
def deepest_episode(eq: np.ndarray, first: int, end: int, cal) -> tuple[int, int, float]:
    """整條權益曲線【最深】的那一段回落 ⇒ (峰的日曆位置, 谷的日曆位置, 深度)。

    ⭐ 分段走 `research13.dd_episodes`（唯一實作），本函式只把它的日期換回日曆位置並取最深那一段。
    """
    eps = R13.dd_episodes(eq, first, end, cal, top=1)
    if not eps:
        return -1, -1, 0.0
    pk, tr, depth = eps[0][0], eps[0][1], eps[0][2]
    return int(cal.searchsorted(pd.Timestamp(pk))), int(cal.searchsorted(pd.Timestamp(tr))), float(depth)


def _diag_one(args):
    """錨點①的查：一顆種子 ⇒ 主格窗報酬／窗內回落／**這顆種子自己**最深的那一段回落在哪裡。"""
    seed, cost = args
    out = _sim(_S["sigs"][("S1", "T1", "*")], N_C1, seed, cost)
    w0, w1 = _S["wins"]["主格窗"]
    r = win_read(out, w0, w1, _S["marks"]["主格窗"])
    pk, tr, depth = deepest_episode(out["equity"], out["first"], out["end"], _S["cal"])
    return {"seed": seed, "tr": r["tr"], "win_mdd": r["mdd"], "peak_pos": pk, "trough_pos": tr, "深度": depth}


def diag_report(dg: pd.DataFrame, cal, wins: dict, want: float, reps: int, bh: float) -> list:
    """⛔ 錨點①沒過之後的【查】：只把事實列出來，⛔ 不下結論、⛔ 不改口徑、⛔ 不放寬容差。"""
    w0, w1 = wins["主格窗"]
    hit = dg[(dg["peak_pos"] == w0) & (dg["trough_pos"] == w1)]
    q = float((dg["tr"] <= want).mean())
    L = ["# PREREGP12 錨點①【查】：−40.9% 是哪一個量？", ""] + _hdr(reps)
    L += ["⛔ 依登錄 §六①，本件已停止、**不出結論**。這一份**只有事實**，交策略線裁定（⛔ 回測線不自行改錨點或容差）。", "",
          "## 一、兩個量差了 11pp，而它們**不是同一個量**", "",
          "| 量 | 中位（200 顆種子） | p10～p90 |", "|---|---:|---|",
          f"| ⓐ 固定窗 [{cal[w0].date()}, {cal[w1].date()}] 的**窗期總報酬**（＝本件登錄的主口徑） | "
          f"{dg['tr'].median() * 100:+.2f}% | {dg['tr'].quantile(0.1) * 100:+.1f}～{dg['tr'].quantile(0.9) * 100:+.1f} |",
          f"| ⓑ 同一個固定窗內的**最大回落** | {dg['win_mdd'].median() * 100:+.2f}% | "
          f"{dg['win_mdd'].quantile(0.1) * 100:+.1f}～{dg['win_mdd'].quantile(0.9) * 100:+.1f} |",
          f"| ⓒ ⭐**每顆種子自己最深的那一段回落**（峰、谷各自不同） | {dg['深度'].median() * 100:+.2f}% | "
          f"{dg['深度'].quantile(0.1) * 100:+.1f}～{dg['深度'].quantile(0.9) * 100:+.1f} |", "",
          f"⇒ ⭐ 前測的 **{want * 100:+.2f}%** 與 **ⓒ** 只差 {abs(dg['深度'].median() - want) * 100:.2f}pp（在 ±1pp 內），"
          f"與 ⓐ 差 {abs(dg['tr'].median() - want) * 100:.2f}pp。", "",
          "## 二、⛔ 為什麼 ⓐ 比 ⓒ 淺 11pp：**峰不是同一天**", "",
          f"- 每顆種子**自己**最深回落的【峰】落在哪一天（前五名，共 {reps} 顆）：", "",
          "| 峰日 | 顆數 |", "|---|---:|"]
    for d_, n_ in dg["peak_date"].value_counts().head().items():
        L.append(f"| {d_} | {n_} |")
    L += ["", f"- 【谷】：", "", "| 谷日 | 顆數 |", "|---|---:|"]
    for d_, n_ in dg["trough_date"].value_counts().head().items():
        L.append(f"| {d_} | {n_} |")
    L += ["", f"- ⭐ 谷落在 {cal[w1].date()} 的有 **{int((dg['trough_pos'] == w1).sum())}/{reps}** 顆（約一半），"
          f"但峰落在 {cal[w0].date()} 的只有 **{int((dg['peak_pos'] == w0).sum())}/{reps}** 顆。",
          f"- ⭐ 峰與谷**兩個都**剛好是 [{cal[w0].date()}, {cal[w1].date()}] 的有 **{len(hit)}/{reps}** 顆"
          + (f"，它們的窗期報酬中位 **{hit['tr'].median() * 100:+.2f}%**。" if len(hit) else "。"), "",
          "⇒ ⚠ 這正是登錄 §二 自己寫的那一句：「這個窗是用**組合自己的高點**選出來的」。",
          "　 每顆種子的峰各自不同 ⇒ 把窗**固定**成某一顆種子的峰谷之後，其餘種子在同一個窗上的跌幅自然較淺。",
          f"　 而前測的 {want * 100:+.2f}% 落在本線【固定窗報酬】分佈的第 **{q * 100:.1f} 百分位**"
          f"（{int((dg['tr'] <= want).sum())}/{reps} 顆比它更慘）⇒ ⛔ 它不是那個分佈的中位。", "",
          "## 三、⛔ 這件事會往前影響【25.7pp 這個被拆的量本身】", "",
          "```",
          f"25.7pp ＝ (−40.9%) − (−15.21%)",
          f"          ↑ ⓒ 逐種子自己的最深回落（含『挑最壞區段』）",
          f"                      ↑ 固定窗 [{cal[w0].date()}, {cal[w1].date()}] 的等權買進持有報酬",
          "⇒ ⛔ 兩邊不是同一種量：一邊是每條路徑自己的最壞區段，一邊是固定區段的報酬。",
          "```", "",
          "⭐ 把兩邊都放到**同一個固定窗**上（本趟實測、含成本 0.585%）：",
          f"　 策略 (S1,C1,T1) {dg['tr'].median() * 100:+.2f}%　vs　全市場等權買光 (S0,C0,T0) {bh * 100:+.2f}%　⇒ 差 "
          f"**{(dg['tr'].median() - bh) * 100:+.2f}pp**（⛔ 這是事實陳述，⛔ 不是本件的結論）。", "",
          "## 四、⛔ 回測線**沒有**做的事（⭐ 逐條寫明）", "",
          "- ⛔ 沒有改錨點、沒有放寬容差、沒有改窗、沒有改口徑（§九-4 事前就寫死不自行改）。",
          "- ⛔ 沒有算三個主效果、沒有算加法表（程式在錨點那一步 `SystemExit`）。",
          "- ⛔ 沒有挑一個「對得上」的口徑回頭宣告錨點過（〈六十四〉）。", "",
          "## 五、⭐ 需要策略線裁定的兩條（⛔ 回測線不代決）", "",
          "1. **錨點①要對的是哪一個量**：ⓐ 固定窗的窗期總報酬（本件登錄寫的）、還是 ⓒ 逐種子自己的最深回落（前測算的）？",
          "2. 若是 ⓒ ⇒ **25.7pp 的分子與分母口徑不同**（§七⑥ 已說它是上界，⚠ 但這一項不在那個上界的說明裡）",
          "　 ⇒ 要拆的那個量要不要改成**同一個固定窗**上的差？改了之後被拆的數就不是 25.7pp。", ""]
    return L


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


def report(tab, xtab, eff, att, anc, dirc, lad, ev, sigs, closes, opens, cal, wins, marks, reps, e0, n_670, own_med, secs) -> list:
    L = ["# PREREGP12：把固定窗上的 13.25pp 拆成【選股 S／集中度 C／時點 T】——回測線落地執行結果", ""] + _hdr(reps)
    L += ["⛔ 判準＝策略線 1500 seq=2 全文 ＋ 回測線落地登錄 §九 ＋ **K線分析線 1700 裁定的落地 §十**"
          "（錨點拆兩個／被拆的量改 13.25pp／先驗按比例換算／C0 兩版判定用對齊版／T 主效果兩版）。", "",
          "## ⛔⛔ 開宗明義一行（K線分析線 1700 §2-2 指定逐字）", "",
          "> **本件拆的是固定窗上的 13.25pp。⛔ 它不是 25.6pp —— 後者的分子含【挑最壞區段】這個選擇，"
          "而那不對應任何一個開關。**", "",
          "⛔ **本件是【歸屬】，⛔ 不是尋找更好的設定**（§七①）⇒ 任何一格好看都**不構成**建議。",
          "⛔ **本件對最大回落天生沉默**（§七③〈九十五〉）⇒ 判定只談【窗期總報酬】；表裡的回落欄只是描述。",
          "⛔ **主格窗含選擇效應**（§二）⇒ ⛔ 不可當無偏估計；有效樣本數＝**1 個窗**（§七②〈九十八〉）。", "",
          "---", "", "## 一、⭐ 錨點對帳（§四④ ＋ 裁定①）", ""]
    L += _anchor_block(anc, dirc, xtab, cal, wins, e0)
    L += [f"⭐ **錨點①-引擎**用的是【逐種子自己最深的那一段回落】（ⓒ）＝ 中位 **{own_med * 100:+.2f}%**。",
          "⛔ **錨點①-判定口徑不設**（裁定 §1-2 逐字）：沒有人在 P12 之前算過【固定窗的窗期總報酬】⇒ "
          "拿本趟算出來的值回頭當目標 ＝ 自己對自己。", "",
          "---", "", "## 二、十二個格子逐格（§四①②③；⭐ C0f 只作描述）", "",
          "⚠ 「進場筆數」：T1 是**整條日曆那一跑的總筆數**（⛔ 不是窗內的，§九-9②）；T0 就是建倉那一批。",
          "⚠ 「平均持有天數」是**算出來的**（§九-9③）：T1 ＝ 119 個交易日；"
          f"T0 ＝ 窗尾 − 建倉日（主格窗 {wins['主格窗'][1] - e0} 天／全窗 "
          f"{wins['全窗'][1] - int(sigs[('S1', 'T0', '全窗')]['entry_pos'].iloc[0])} 天）。",
          "⭐ 「平均曝險」＝ 持股市值 ÷ 權益 的窗內日均 ⇒ **它就是 C 這個開關的【安慰劑欄】**（〈一百〇五〉）。", ""]
    for w in WINDOWS:
        L += _cells_block(tab, w)
    L += ["---", "", "## 三、⭐⭐ C0 的兩版與【買光到不到位】的證據（§四②⑤ ＋ 裁定④）", "",
          "⭐ 判定版 ＝ **C0a（曝險對齊）**：逐日容量 ＝【當日在場的候選數】＝ 若全部買光、當天會持有的相異部位數。",
          "⛔ 描述版 ＝ C0f（字面最小 n_slots）。⚠ 而【字面窄讀】（當天**新出現**的訊號數）本線也跑了一顆種子當證據：", "",
          "| S | T | 窗 | 版本 | 容量 | 進場筆數 | 上限 | 買光率 | **平均曝險** | 槽位使用率 |",
          "|---|---|---|---|---|---:|---:|---:|---:|---:|"]
    for r in ev.itertuples():
        L.append(f"| {r.S} | {r.T} | {r.wk} | {getattr(r, '版本')} | {getattr(r, '容量')} | {r.trades:,} | "
                 f"{getattr(r, 'trades上限'):,} | {getattr(r, '買光率') * 100:.1f}% | {getattr(r, '曝險') * 100:.1f}% | "
                 f"{getattr(r, '槽位使用率'):.3f} |")
    L += ["", "⇒ ⭐ 這張表直接回答裁定④ 要的兩件：**買光到不到位**（買光率）與 **曝險對不對齊**（曝險欄）。",
          "⚠ 而 T0 那一側兩版**完全相同**（只有一個進場日 ⇒ 兩種定義都等於當日候選數）"
          "⇒ ⭐ 所以【現金效應】那一格只在 T1 那一側有值。", "",
          "### C0f 的梯度表（§四⑤ 原本要的證據）", "",
          "| S | T | 窗 | n_slots | 進場筆數 | 槽位使用率 | 平均曝險 | 選中 |", "|---|---|---|---:|---:|---:|---:|:--:|"]
    for r in lad.sort_values(["S", "T", "wk", "n_slots"]).itertuples():
        L.append(f"| {r.S} | {r.T} | {r.wk} | {r.n_slots:,} | {r.trades:,} | {r.slot_use:.3f} | {r.expo * 100:.1f}% | "
                 f"{'⭐' if r.n_slots == r.chosen else ''} |")
    L += ["", "---", "", "## 四、⭐⭐ 判定：三個主效果（§三 ＋ 裁定⑤）", "",
          "⛔ 判定用 **CI 含不含 0**（⛔ 不看點估計大小，〈九十七〉）。配對＝同種子、同其餘兩個開關 ⇒ "
          "先對【種子 × 組合】取平均 ⇒ 一條**逐月**序列 ⇒ 月分群 SE 的 95% CI（抽樣單位是月）。",
          "⛔ 多重檢定：判定格 3 個（× 2 窗），虛無期望 0.15 格／窗。",
          "⛔ **T 的「全部」那一版含 (S1,·,T0) 兩格，而那兩格的有效樣本是【4 檔】**（裁定⑤）"
          "⇒ ⭐ 以【只 S0 臂】那一版為準；兩版方向相反 ⇒ 寫【T 在本設計下測不出】。", "",
          "| 窗 | 成本 | 因子 | 臂 | 逐月配對差 | 95% CI | 月數 | 正的月數 | 判 | 點估計（窗期總報酬差） |",
          "|---|---|---|---|---:|---|---:|---:|:--:|---:|"]
    for r in eff.sort_values(["win", "cost", "factor", "arm"]).itertuples():
        L.append(f"| {r.win} | {r.cost} | {r.factor} | {r.arm} | {r.diff_pp:+.3f}pp | {r.lo_pp:+.3f}～{r.hi_pp:+.3f}pp | "
                 f"{r.n_months} | {r.pos_months} | {'✅ 測得出' if r.detectable else '⛔ 測不出'} | {r.point_pp:+.2f}pp |")
    e_main = eff[(eff["win"] == "主格窗") & (eff["cost"] == "成本0.585%") & (eff["arm"] == "全部")].set_index("factor")
    t_all = float(e_main.loc["T", "point_pp"]); t_s0 = float(eff[(eff["win"] == "主格窗") & (eff["cost"] == "成本0.585%")
                                                                & (eff["factor"] == "T") & (eff["arm"] == "S0")]["point_pp"].iloc[0])
    L += ["", f"⇒ ⭐ **T 兩版**（主格窗、含成本）：全部 {t_all:+.2f}pp／只 S0 臂 {t_s0:+.2f}pp ⇒ "
          + ("⛔ **方向相反 ⇒ 依裁定⑤ 寫【T 在本設計下測不出】**" if t_all * t_s0 < 0 else "✅ 方向相同（⛔ 而兩版的判都是 CI 說了算）"), "",
          "### ⛔⛔ 兩件會讓人讀錯這張表的事（⭐ 兩件都是本趟才看得到的）", "",
          "**① S 的『全部』版含著同樣那兩格 4 檔的格子** —— 裁定⑤ 只要求 T 報兩版，⛔ 而 S 的主效果是",
          "　 在 (C,T) 四種組合上平均，其中兩個組合是 T0 ⇒ 它同樣吃進 (S1,·,T0) 那兩格。",
          f"　 實際數字：主格窗 (S1,C1,T0) {tab[(tab['win'] == '主格窗') & (tab['cost'] == '成本0.585%') & (tab['S'] == 'S1') & (tab['C'] == 'C1') & (tab['T'] == 'T0')]['tr_med'].iloc[0] * 100:+.1f}%"
          f" vs (S0,C1,T0) {tab[(tab['win'] == '主格窗') & (tab['cost'] == '成本0.585%') & (tab['S'] == 'S0') & (tab['C'] == 'C1') & (tab['T'] == 'T0')]['tr_med'].iloc[0] * 100:+.1f}%"
          "　⇒ ⭐ 那一格【4 檔】贏了 44pp，而它就是 S 點估計為正的主要來源。",
          "　 ⇒ ⛔ **本線不自行加一版**（那是看過結果之後加切法，〈六十四〉）⇒ ⏳ 要不要比照 T 報兩版，是 K線分析線的格子。",
          "**② 全窗那幾個 pp 是【9.5 年的總報酬差】** ⇒ ⛔ 不可以跟主格窗（1.7 年）的 pp 並排讀。",
          "　 ⭐ 判定本來就不是看它（判定看逐月配對差的 CI）⇒ 那一欄只是描述。", "",
          "## 五、歸屬加法表（§三末 ＋ 裁定②）", "",
          "gap ＝ (S1,C1,T1) − (S0,**C0a**,T0) ＝ S ＋ C ＋ T ＋ 殘差（⭐ 用**種子平均**，⛔ 中位數不可加）。", "",
          "| 窗 | 成本 | gap | S | C | T | 殘差 | 殘差佔 | 殘差 > 最大主效果？ |", "|---|---|---:|---:|---:|---:|---:|---:|:--:|"]
    for r in att.sort_values(["win", "cost"]).itertuples():
        L.append(f"| {r.win} | {r.cost} | {r.gap_pp:+.2f}pp | {r.S_pp:+.2f}pp | {r.C_pp:+.2f}pp | {r.T_pp:+.2f}pp | "
                 f"{r.resid_pp:+.2f}pp | {r.resid_share * 100:.0f}% | {'⛔ 是 ⇒ 判【拆不開】' if r.resid_gt_max else '否'} |")
    g_main = float(att[(att["win"] == "主格窗") & (att["cost"] == "成本0.585%")]["gap_pp"].iloc[0])
    L += ["", f"⚠ 對帳：裁定② 指定的被拆量是 **{GAP_REF_PP:+.2f}pp**，本趟加法表的 gap ＝ **{g_main:+.2f}pp**"
          f"（差 {g_main - GAP_REF_PP:+.2f}pp）。",
          "⭐ 差的來源**不是** C0a 取代 C0f（T0 那一側兩版完全相同 ⇒ gap 的兩端都沒被換掉），",
          "　 而是【中位 vs 平均】：13.25pp 是**中位**口徑（錨點那一欄），加法表依 §九-7 必須用**平均**（⛔ 中位數不可加）。", "",
          "### ⭐ 先驗對照（裁定③：由 25.7pp 版【按比例機械換算】而得）", "",
          "> ⛔ 逐字揭露：**本節先驗由 25.7pp 版按比例機械換算而得，⛔ 未重新判斷方向或量級；"
          "換算時本線已看過四個角落的窗期報酬。**", "",
          "| 項 | 換算後的先驗 | 實測（主格窗・含成本） | |", "|---|---|---:|:--:|"]
    for k, (lo_, hi_) in PRIOR_PP.items():
        got = float(e_main.loc[k, "point_pp"]) if k in e_main.index else float(
            att[(att["win"] == "主格窗") & (att["cost"] == "成本0.585%")]["resid_pp"].iloc[0])
        L.append(f"| {k} | {lo_:+.1f} ~ {hi_:+.1f}pp | {got:+.2f}pp | {'✅ 落在區間' if lo_ <= got <= hi_ else '⛔ 沒落在區間'} |")
    c_row = eff[(eff["win"] == "主格窗") & (eff["cost"] == "成本0.585%") & (eff["factor"] == "C")].iloc[0]
    L += [f"| C（⛔ 不換算，原樣保留） | 押【CI 含 0 ＝ 測不出】 | CI {c_row['lo_pp']:+.2f}～{c_row['hi_pp']:+.2f}pp | "
          f"{'⛔ 否證（CI 不含 0）' if c_row['detectable'] else '✅ 成立'} |", "",
          "---", "", "## 六、成本那一塊有多大（§四⑥；⛔ 只作描述）", "",
          "| 窗 | S | C | T | 含成本 | 成本0 | 成本吃掉 |", "|---|---|---|---|---:|---:|---:|"]
    p = tab.pivot_table(index=["win", "S", "C", "T"], columns="cost", values="tr_med")
    for idx, r in p.iterrows():
        L.append(f"| {idx[0]} | {idx[1]} | {idx[2]} | {idx[3]} | {r['成本0.585%'] * 100:+.2f}% | {r['成本0'] * 100:+.2f}% | "
                 f"{(r['成本0.585%'] - r['成本0']) * 100:+.2f}pp |")
    w0m, w1m = wins["主格窗"]
    no_trade = sum(1 for sid in sigs[("S0", "T0", "主格窗")]["sid"] if not np.isfinite(float(opens[sid][w1m])))
    n_b0 = len(sigs[("S1", "T0", "主格窗")])
    L += ["", "---", "", "## 七、訊號量與執行（§四⑦）", "",
          f"- S1 門檻B：**{len(sigs[('S1', 'T1', '*')]):,}** 筆訊號（{sigs[('S1', 'T1', '*')]['sid'].nunique():,} 檔）",
          f"- S0 全市場：**{len(sigs[('S0', 'T1', '*')]):,}** 筆訊號（{sigs[('S0', 'T1', '*')]['sid'].nunique():,} 檔）"
          f" ⇒ 約 S1 的 {len(sigs[('S0', 'T1', '*')]) / len(sigs[('S1', 'T1', '*')]):.0f} 倍",
          f"- 本趟總執行時間 **{secs / 60:.0f} 分鐘** ⇒ ⭐ 沒有觸發否證⑤（不必改成分層抽樣）。", "",
          "## 八、⭐ 母體、倖存者、與那個 4 檔（§四⑧、裁定①末、裁定⑤）", "",
          f"- ⚠ 主格窗建倉日我方可買 **{n_670:,}** 檔，策略線 §八② 寫 **671** 檔 ⇒ **兩線母體差 {n_670 - 671:+d} 檔**。",
          "  ⛔ 依裁定①末：在查出那 1 檔是什麼之前，**只能寫「兩線母體差 1 檔、直算差 0.03pp」**，"
          "⛔ 不可寫「兩線母體相同」（〈七十〉）。",
          f"- 這 {n_670:,} 檔裡，窗尾那一天（{cal[w1m].date()}）**沒有開盤價（＝當天沒有成交）** 的有 **{no_trade}** 檔 ⇒ "
          "處置＝`closes` 已 ffill 到最後成交價，與策略線 §八② 同一種處置。",
          "- ⛔ **策略那一側**（門檻B 候選池）的倖存者處理【本件未查】⇒ 仍是已知偏差（§七⑤）。",
          f"- ⭐⭐ **門檻B 在主格窗的第一個訊號月（2023-07）只有 {n_b0} 筆訊號**（裁定⑤ 指定寫進本文）：",
          "  ⇒ 所以 (S1,C1,T0) 是「4 檔 × 12.5% ＋ 50% 現金」、(S1,C0a,T0) 是「4 檔各 25%」，"
          "  而 p10 ＝ p90（8 個槽選 4 個候選 ＝ 全選 ⇒ 沒有隨機性可言）。",
          "  ⇒ ⛔ 依〈八十八〉：**訊號在某些時點結構性不觸發，那是規則的性質，⛔ 不是樣本不足** —— 與四月洞同一族。", "",
          "## 九、⛔ 範圍限制（照抄登錄，⛔ 不刪）", "",
          "- ⛔ 本件是歸屬、不是找設定（§七①）。⛔ 有效樣本數：主格窗只有 1 個窗（§七②）。",
          "- ⛔ 對最大回落天生沉默（§七③）。⛔ 33.5pp（等權 vs 市值加權）不在本件範圍（§七④）。",
          "- ⛔ 成本 0.585%、滑價未計（§七⑤）。⛔ T0 只取窗內第一個訊號月 ⇒ 它是【一次性建倉】（§七⑦）。",
          "- ⛔ C0 有現金拖累（§七⑧）⇒ ⭐ 本趟已把它量出來：C0f 與 C0a 的差就是它。",
          "- ⛔ T 這個開關**必然**含「窗頭有沒有倉位」（§九-3）⇒ 第一節的【窗內限定版】就是它的量。", ""]
    return L


if __name__ == "__main__":
    main()
