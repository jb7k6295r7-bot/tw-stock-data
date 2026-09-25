# -*- coding: utf-8 -*-
"""PREREGP9 seq8 §四① 兩種對照臂（回測線，2026-09-25）。⛔ 兩者都【不計 N】；⛔ 本檔不跑 P9 的任何一格。

登錄原文（seq8 §四①，逐字）：
  「同平均部位對照（2-B 三格、2-C ⓒ～ⓗ；⛔ 不計 N）：
     m̄ ＝ 該格全期新部位的平均買進倍數（例：ⓓ 若 35% 的新部位買 0.5、其餘 1.0 ⇒ m̄＝0.825）
     對照 ＝ 每個新部位都固定買 m̄ 個 slot、不看大盤
     ⓕⓖⓗ 改用 ē ＝ 該格全期平均持股比例（持股市值 ÷ 總資產，按日平均）；
     對照 ＝ 全期固定持股比例 ē（每月第一個交易日再平衡、成本照算）」
  ⇒ 原文沒有寫「同顆種子」⇒ ē、m̄ 取【該格】一個數（見讀法 ①），對照臂的每顆種子都用同一個 ē／m̄。

════ A. m̄ 對照（2-B ⓐⓑⓒ、2-C ⓒⓓⓔ）════
  mbar_of(out, ...)   從一格的引擎輸出算【該顆種子】的 m̄
  mbar_kwargs(m̄)      對照臂的引擎參數 ＝ size_mult_by_regime={"mult": m̄, "below": 全真}
                      ⇒ 每個新部位都買 m̄ × slot、不看大盤（ENGINE_REPORT §七 已指這條路）
                      ⚠ m̄ ＞ 1 時走引擎 ⓒ 的現金規則（登錄「上限、現金不足照 2-B 規則」＝ short="skip"：
                        現金 ＜ m̄×slot ⇒ 只買 1 個 slot）⇒ 對照臂與 ⓒ／2-B 用同一條現金規則

════ B. ē 對照（2-C ⓕⓖⓗ）════
  ebar_of(equity, hold_val, a, b)   一條權益曲線在 [a, b] 的平均持股比例（hold_val ÷ equity，按日平均）
  ebar_control(...)                 對照臂：以【基準臂（加減碼全關）同顆種子】的持股簿為股票側，
                                    全期固定持股比例 ē、每月第一個交易日再平衡、成本照算
  ⭐ 做法（權益曲線層合成，⛔ 不改引擎；結構同 researchp17.compose 的月度再平衡）：
    股票側日報酬 r_s[t] ＝ (E[t] − E[t−1]) ÷ (H[t−1] ＋ A[t])
      E＝基準臂 equity、H＝基準臂 hold_val（收盤持股市值）、A[t]＝基準臂 t 日開盤新買進的金額（audit 的 buy）
      ⇒ 分母 ＝ 當天承擔價格風險的資本（昨收持股 ＋ 今開新買）；cash_mode="zero" 下現金報酬 0，
        所以 E 的日變動全部來自持股（含出場日扣的來回成本 COST）⇒ r_s ＝ 基準臂持股簿的時間加權日報酬
      分母 ＝ 0（持股簿空的那天）⇒ r_s ＝ 0
    對照臂狀態：S（股票側）、C（現金，報酬 0）
      t ＝ a（窗首）開盤：S ＝ ē × V[a−1]、C ＝ (1−ē) × V[a−1]（期初配置不收成本：引擎慣例買進當下不扣）
      每天：S ← S × (1 ＋ r_s[t])
      再平衡日（窗內 (a, b] 每月第一個交易日，⭐ 同 researchp17.rebal_days；在當日收盤、報酬走完之後）：
        目標 S* ＝ ē × (S ＋ C)；成本見讀法 ②；扣完成本後依 ē 重新配置
    持股比例 h[t] ＝ S ÷ V（基準臂持股簿為空的日子記 0）
  ⚠ 限制：股票側是基準臂持股簿的【同比例縮放】⇒ 「對照＝同一批股票、同一批時點，只把總曝險固定在 ē」。

── 本檔寫定的讀法（⭐ 看任何 P9 結果之前寫死；回報給裁定線）────────────────────
  ① 「該格」的 ē／m̄：先逐種子算，再取 200 顆的【中位】（＝ 本件判定值的取法：種子中位）。
     另備 how="pooled"（m̄：Σ 買進倍數 ÷ Σ 新部位；ē：逐種子 ē 的平均）與「逐種子配對」（呼叫端逐種子傳入各自的 ē／m̄）。
  ② ē 對照的再平衡成本：預設 cost_mode="engine" ＝ 引擎慣例「每一塊買進的錢在賣出時付一次來回 COST」
     ⇒ 再平衡【賣】股票側 x 元付 x×COST，【買】不當下付（那筆錢之後隨持股簿出場時付，已在 r_s 裡）
     ⇒ 與 ⓕⓖⓗ 在引擎裡賣半（付 COST）、補回（當下不付）同一個口徑。
     另備 cost_mode="p17"：兩個方向都付 |移動金額| × COST（researchp17 §1-4 的口徑，較嚴）。
  ③ m̄ 取【實際套用的倍數】（how 之外的另一軸 reading="executed"）：
       2-B：1 ＋ size × (實際加成次數 ÷ 新部位數)（現金不足沒加的 ⇒ 不算）
       ⓒ ：引擎 x_mbar_nominal − (m−1) × x_mult_short ÷ x_new_n（現金不足只買 1 slot 的 ⇒ 算 1）
       ⓓⓔ：＝ x_mbar_nominal（m ≤ 1 一定照倍數買）
     ⛔ 不含「min(slot, 現金)」那一般性的現金截斷（對照臂跑引擎時自然也會被截）。
     另備 reading="nominal"：2-B 用觸發次數（含現金不足沒加的）、ⓒ 用引擎 x_mbar_nominal。
  ④ 「全期」＝ 主窗 [w0, w1]（呼叫端傳 a＝w0、b＝w1）；ē 按日平均的分母是窗內交易日數。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import research11 as R


# ═════════════════════════ A. m̄ 對照 ═════════════════════════
def mbar_of(out: dict, cell: str, *, size: float = 0.5, mult: float | None = None, reading: str = "executed") -> float:
    """一顆種子的 m̄。cell：'add'（2-B ⓐⓑⓒ）／'mult'（2-C ⓒⓓⓔ，需 mult）。見讀法 ③。"""
    if reading not in ("executed", "nominal"):
        raise ValueError(f"reading 只能是 executed／nominal，收到 {reading!r}")
    n = out.get("x_new_n", 0)
    if not n:
        return float("nan")
    if cell == "add":
        k = out["x_add_n"] if reading == "executed" else out["x_add_trig"]
        return 1.0 + size * k / n
    if cell == "mult":
        if mult is None:
            raise ValueError("cell='mult' 需要 mult（該格的線下倍數）")
        nom = float(out["x_mbar_nominal"])
        if reading == "nominal" or mult <= 1:
            return nom
        return nom - (mult - 1.0) * out.get("x_mult_short", 0) / n
    raise ValueError(f"cell 只能是 add／mult，收到 {cell!r}")


def cell_value(per_seed, how: str = "median", weights=None) -> float:
    """「該格」一個數（讀法 ①）。median（預設）／pooled（m̄ 傳 weights＝各種子新部位數；ē 不傳 ⇒ 平均）。"""
    x = np.asarray(per_seed, float)
    if how == "median":
        return float(np.median(x))
    if how == "pooled":
        if weights is None:
            return float(np.mean(x))
        w = np.asarray(weights, float)
        return float((x * w).sum() / w.sum())
    raise ValueError(f"how 只能是 median／pooled，收到 {how!r}")


def mbar_kwargs(mbar: float, ncal: int) -> dict:
    """m̄ 對照臂的引擎參數：每個新部位都買 m̄ × slot、不看大盤（below 全真）。"""
    m = float(mbar)
    if not (np.isfinite(m) and m > 0):
        raise ValueError(f"m̄ 要是正的有限數，收到 {mbar!r}")
    return {"size_mult_by_regime": {"mult": m, "below": np.ones(ncal, bool)}}


# ═════════════════════════ B. ē 對照 ═════════════════════════
def ebar_of(equity, hold_val, a: int, b: int) -> float:
    """[a, b]（含兩端）按日平均的 hold_val ÷ equity。"""
    e = np.asarray(equity, float)[a:b + 1]; h = np.asarray(hold_val, float)[a:b + 1]
    return float(np.mean(h / e))


def rebal_days(cal: pd.DatetimeIndex, a: int, b: int) -> np.ndarray:
    """(a, b] 內每月第一個交易日的日曆位置（窗首當月不算；同 researchp17.rebal_days 的口徑）。"""
    per = pd.DatetimeIndex(cal).to_period("M")
    return np.array([t for t in range(a + 1, b + 1) if per[t] != per[t - 1]], int)


def buys_by_day(audit, ncal: int) -> np.ndarray:
    """基準臂 audit 的 buy 金額按日加總（A[t]）。"""
    A = np.zeros(ncal)
    for r in audit:
        if r["side"] == "buy":
            A[int(r["t"])] += float(r["amt"])
    return A


def book_returns(equity, hold_val, A, a: int, b: int) -> np.ndarray:
    """基準臂持股簿的時間加權日報酬 r_s[t]，t ∈ [a, b]（其他位置 0）。"""
    E = np.asarray(equity, float); H = np.asarray(hold_val, float); A = np.asarray(A, float)
    r = np.zeros(len(E))
    for t in range(max(a, 1), b + 1):
        cap = H[t - 1] + A[t]
        r[t] = (E[t] - E[t - 1]) / cap if cap > 0 else 0.0
    return r


def ebar_control(equity, hold_val, audit, cal: pd.DatetimeIndex, a: int, b: int, ebar: float,
                 cost: float | None = None, cost_mode: str = "engine") -> dict:
    """ē 固定配置、每月第一個交易日再平衡的對照臂（見檔頭 B）。

    equity／hold_val／audit ＝ 基準臂（加減碼全關、cash_mode="zero"）同一顆種子 simulate_mtm(return_equity=True, audit=[]) 的輸出。
    回傳：V（長度 ncal；V[:a] ＝ equity[:a]，V[b+1:] ＝ V[b]）、h（逐日持股比例）、rebal（再平衡日）、
          turn（逐日移動金額）、cost（逐日成本）、n_rebal、ebar_realized（[a, b] 的 h 平均）。
    """
    if cost_mode not in ("engine", "p17"):
        raise ValueError(f"cost_mode 只能是 engine／p17，收到 {cost_mode!r}")
    e_ = float(ebar)
    if not (0.0 <= e_ <= 1.0):
        raise ValueError(f"ē 要在 [0, 1]，收到 {ebar!r}")
    c_ = R.COST if cost is None else float(cost)
    E = np.asarray(equity, float); H = np.asarray(hold_val, float)
    n = len(E)
    A = buys_by_day(audit, n)
    rs = book_returns(E, H, A, a, b)
    rb = rebal_days(cal, a, b); is_rb = np.zeros(n, bool); is_rb[rb] = True
    V = E.copy(); h = np.zeros(n); turn = np.zeros(n); cst = np.zeros(n)
    v0 = float(E[a - 1]) if a >= 1 else 1.0
    S, C = e_ * v0, (1.0 - e_) * v0                     # 窗首開盤配置（⛔ 不收成本）
    for t in range(a, b + 1):
        S *= 1.0 + rs[t]
        v = S + C
        if is_rb[t]:
            d = e_ * v - S
            tr = abs(d)
            c = tr * c_ if cost_mode == "p17" else max(-d, 0.0) * c_
            v -= c
            turn[t] = tr; cst[t] = c
            S, C = e_ * v, (1.0 - e_) * v
        V[t] = v
        h[t] = S / v if (H[t] > 0 and v > 0) else 0.0
    V[b + 1:] = V[b]
    return {"V": V, "h": h, "rebal": rb, "turn": turn, "cost": cst, "n_rebal": int(len(rb)),
            "ebar_realized": float(h[a:b + 1].mean())}
