# -*- coding: utf-8 -*-
"""PREREGP9 seq8 2-B ⓑ「進場後貼近 120 日高點三分位」旗標建構器（回測線，2026-09-25）。

⭐ 用途：產生 `research11.simulate_mtm(add_rule={"kind": "flag", "flags": {sid: 布林序列}})` 要的旗標。
   引擎只讀 flags[sid][t−1]、在 t 開盤加碼，⛔ 引擎不認識三分位（ENGINE_REPORT §六 讀法 ⑥）。
⛔ 本檔不跑 P9 的任何一格；⛔ 旗標不計 N。

── 定義出處（逐字，⛔ 不另訂）───────────────────────────────────────────
  PREREGP9 seq8 §二 2-B ⓑ：「進場後貼近 120 日高點三分位（定義照 PREREGP8，⛔ 不另訂）」
  PREREGP8 seq2（sha 55d8c99ee7b587f8）：
    §五②  dist_hi120 ＝ 收盤 ÷ 近 120 個交易日最高【收盤】− 1（⛔ 不是最高價、⛔ 不是 250 日）
    §2-A   母體＝全市場過閘門（近20日均額 ≥5,000萬、有效K棒 ≥120）；dist_hi120【逐月橫斷面】切分位
    §2-C   「dist_hi120 前三分位」＝ 三分位裡最貼近高點的那一格
  PREREGP8 的落地程式 researchp8.py（resultsp8/P8_REPORT.md 由它產生）：
    ・母體 ＝ panel 的 eligible 列（liq_ok ∧ bars_ok ∧ inst_ok）
    ・切法 ＝ researchp8.xs_bucket(el, "dist_hi120", 3)：逐 measure_date 以 rank(method="first") 排名，
      桶 ＝ ceil(名次 ÷ n × 3) − 1；「貼近高點三分位」＝ 桶 2（researchp8 main 的 `el["ter"] == N_TER − 1`）
  ⇒ 本檔【直接呼叫 researchp8.xs_bucket】（⛔ 不抄第二份），母體與排序口徑與 P8 相同。

── 本檔寫定的讀法（⭐ 看任何 P9 結果之前寫死；回報給裁定線）────────────────────
  ① 只在【每月量測日】判（＝ panel 的 measure_date，每月第一個交易日）。
     出處：PREREGP8 §2-A「逐月橫斷面」＋ researchp8 以 measure_date 分組；PREREGP9 seq8 §一「只在每月量測日判」。
     ⛔ 不每天重切橫斷面（那是另訂一個 P8 沒有的定義）。
     ⇒ flags[sid][d] ＝ True 只可能出現在量測日 d；其餘日一律 False。
     ⇒ 引擎在 t ＝ d＋1 開盤讀 flags[d] ⇒ 加碼在量測日次一交易日開盤（與門檻B 進場同一個時點慣例）。
  ② 時序：flags[d] 只用 d 當天（含）以前的收盤（dist_hi120 是尾端 120 根的滾動最大值），引擎再平移一天讀
     ⇒ 加碼決定只用 t−1 以前的資料。
  ③ 母體：該量測日 eligible 的全市場股票（⛔ 不是只在門檻B 或持股裡排）。
     ⇒ 持有中的股票若在某個量測日【不是 eligible】⇒ 它不在 P8 的橫斷面裡 ⇒ 那一月旗標 False（⛔ 不拿切點外插）。
  ④ 等號：沿用 P8 的 rank(method="first") ⇒ 同值依 panel 列順序（measure_date、stock_id 遞增）給名次，
     落在切點上的同值可能一個進、一個不進。⛔ 不改成「同值同進退」（那是另訂）。
  ⑤ 資料不足：dist_hi120 非有限 ⇒ 不排名、不進分母；某月有限值 < 3 檔 ⇒ 該月全部 False（P8 xs_bucket 的行為）；
     sid 不在 panel ⇒ 全 False；panel 沒有的月份（本庫兩份 panel 的量測日都只到 2026-03-02）⇒ 那些月沒有旗標。
  ⑥ 值的來源：預設讀 panel 的 dist_hi120 欄（＝ P8 排名用的那一欄，逐字）。
     另提供 source="closes"：由呼叫端給的還原收盤（ffill）自算同一條算式（p4_features.stock_raw、min_periods＝120）
     ⇒ 只給 fixture 用：證明兩者在真資料上逐位元相同、並做無前視突變測試。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import researchp8 as P8

FEATURE = P8.FEATURE            # "dist_hi120"（PREREGP8 §五②）
N_TER = P8.N_TER                # 3（PREREGP8 §2-B／2-C 三分位）
TOP = N_TER - 1                 # 桶 2 ＝ 最貼近 120 日高點（researchp8：el["ter"] == N_TER − 1）
WIN_HI = 120                    # 近 120 個交易日最高收盤（p4_features.stock_raw：rolling(120, min_periods=120)）


def dist_hi120(close) -> np.ndarray:
    """收盤 ÷ 近 120 個交易日（含當日）最高收盤 − 1；與 p4_features.stock_raw 同一條算式（ffill、min_periods＝120）。

    ⭐ 第 i 個值只用 close[i−119 … i] ⇒ 無前視。暖身不足 ⇒ NaN。
    """
    c = pd.Series(np.asarray(close, float)).ffill()
    return (c / c.rolling(WIN_HI, min_periods=WIN_HI).max() - 1).to_numpy()


def _elig(panel: pd.DataFrame) -> pd.DataFrame:
    """eligible 列，⭐ 保留 panel 原列順序（P8 的 rank(method="first") 依它決定同值名次）。"""
    return panel[panel["eligible"].astype(bool)].copy()


def _dist_from_closes(el: pd.DataFrame, cal: pd.DatetimeIndex, closes: dict) -> np.ndarray:
    """source="closes"：量測日 d 的 dist_hi120 由 closes[sid][: d+1] 自算。沒有價 ⇒ NaN。"""
    pos = {d: i for i, d in enumerate(cal)}
    ix_all = el["measure_date"].map(pos).to_numpy(dtype=float)
    out = np.full(len(el), np.nan)
    sids = el["stock_id"].to_numpy()
    for sid in pd.unique(sids):
        m = (sids == sid) & np.isfinite(ix_all)                  # 量測日不在日曆上 ⇒ NaN（不排名）
        c = closes.get(sid)
        if c is None or not m.any():
            continue
        ds = dist_hi120(c)
        ix = ix_all[m].astype(int)
        v = ds[ix]  # _FLAG_LAG
        out[m] = v
    return out


def top_tercile(panel: pd.DataFrame, cal: pd.DatetimeIndex | None = None, closes: dict | None = None,
                source: str = "panel") -> pd.DataFrame:
    """回 eligible 列 ＋ 欄 `dist`（用來排名的值）、`ter`（0／1／2，NaN＝不排名）、`top`（布林）。

    ⭐ 排名一律呼叫 researchp8.xs_bucket（⛔ 不抄第二份）。
    """
    if source not in ("panel", "closes"):
        raise ValueError(f"source 只能是 'panel'（P8 逐字）或 'closes'（fixture 用），收到 {source!r}")
    el = _elig(panel)
    if source == "panel":
        el["dist"] = pd.to_numeric(el[FEATURE], errors="coerce").astype(float)
    else:
        if cal is None or closes is None:
            raise ValueError("source='closes' 需要 cal 與 closes")
        el["dist"] = _dist_from_closes(el, cal, closes)
    el.loc[~np.isfinite(el["dist"].to_numpy()), "dist"] = np.nan    # 非有限 ⇒ 不排名、不進分母
    el["ter"] = P8.xs_bucket(el, "dist", N_TER)
    el["top"] = (el["ter"] == TOP).to_numpy()
    return el


def build_flags(panel: pd.DataFrame, cal: pd.DatetimeIndex, sids=None, closes: dict | None = None,
                source: str = "panel") -> dict:
    """{sid: 長度 len(cal) 的布林序列}；flags[sid][d] ＝ 量測日 d 該股在 eligible 橫斷面的 dist_hi120 前三分位。

    sids：要回的股票（預設 ＝ panel 裡出現過的全部）；不在 panel 的 sid 回全 False。
    ⭐ 引擎讀 flags[sid][t−1] ⇒ 在量測日次一交易日開盤加碼。
    """
    ncal = len(cal)
    pos = {d: i for i, d in enumerate(cal)}
    el = top_tercile(panel, cal, closes, source)
    hit = el[el["top"]]
    want = sorted(set(panel["stock_id"])) if sids is None else sorted(set(sids))
    flags = {s: np.zeros(ncal, bool) for s in want}
    for sid, g in hit.groupby("stock_id", sort=False):
        if sid not in flags:
            continue
        ix = g["measure_date"].map(pos).dropna().astype(int).to_numpy()
        flags[sid][ix] = True  # _FLAG_POS
    return flags


def flag_summary(flags: dict, lo: int = 0, hi: int | None = None) -> dict:
    """觸發次數（只報次數，⛔ 不涉報酬）：旗標為真的 (sid, 日) 數、涉及檔數、涉及日數。"""
    n = 0; s_ = 0; days = set()
    for s, f in flags.items():
        seg = np.asarray(f[lo:hi], bool)
        k = int(seg.sum())
        if k:
            n += k; s_ += 1; days.update((np.flatnonzero(seg) + lo).tolist())
    return {"flag_true": n, "stocks": s_, "days": len(days)}
