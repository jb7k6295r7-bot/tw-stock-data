# -*- coding: utf-8 -*-
"""Mass Index 反轉凸起 seq1【頻率表・乾跑】（台股策略線 單筆層登錄 sha 356f3ccfda10a90f，2026-10-18 13:28；裁定 seq374、375 發號；
N_前段 ＋1）——回測線計算子代理。
⛔ 只數凸起、事件日期與個數、剔除計數、n_eff、曝險股日；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、出場日（裁定 seq366：乾跑）。
   用到的價格只有 ≤ T 的日高低收；T＋1 只判「有沒有成交、開盤是否鎖漲停」（快取 trd／o／upl）。
⛔ 不 commit、不改既有程式與結果夾；researchWR_freq（共用 base／st_next_open／run_freq）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMI_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMI_freq_check
輸出 backtest/resultsMI/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格：
  A         判定格（登錄 §一、§二）：MI 升破 27.0 後第一次跌回 26.5 以下那根 T（凸起完成）∧ T 當日 EMA9(收盤) ＜ 前一日 ⇒ T＋1 開盤買
  D1_26     描述 D1：凸起完成門檻改 26.0（同方向條件）
  D2_無方向 描述 D2：不加方向條件（凸起完成就做多；＝ 凸起完成全體）
  （D3 固定抱 20／60 日、假訊號臂、對照、持有天數都要進場後價格 ⇒ ⛔ 不在頻率表）

═══ 讀法（G 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 G1 世界、母體、壞根、T 的母體閘、段、n_eff、每年／每檔每年 ＝ researchWR_freq R1、R2、R10 原樣（同一支 base／run_freq；UO／DMI 頻率表同）：
    主 ＝ rerun17 快照（2015-01-05～資料尾）；早年 ＝ ~/earlydata（2004-02-11～2014-12-31）；四碼普通股、含已下市、GATE_V2；
    壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、價格斷點、幽靈還原）∪ crashwork ∪ 早年 reduce_v2（seq341 §六）；
    T 的母體 ＝ patterns.Frame.gate[T]（T−20～T−1 日均量 ≥ 500 張 ＝「T 前一日 20 日均量」）∧ UG.pit_valid[T]。
    所有「N 日」一律在【該股有效 K 棒序列】上數（停牌日不算）；H、L、C 為同一累積還原因子的還原價（登錄 §一）。
 G2 ★ EMA 起始方式（登錄只寫 EMA9）：每個無壞 K 棒段（段首 ＝ 第 0 根或壞 K 棒）各自起算；第 9 根（段內位置 8）的值 ＝ 前 9 根簡單平均
    （StockCharts／TA-Lib 慣例），之後 EMA[k] ＝ EMA[k−1] ＋ α（x[k] − EMA[k−1])、α ＝ 2 ÷（9 ＋ 1）＝ 0.2〔另一讀法：以第一根值起始——不採〕。
    E1 ＝ EMA9(H − L)：段內位置 8 起有值；E2 ＝ EMA9(E1)：E1 有值的前 9 根平均起始 ⇒ 段內位置 16 起有值；
    比值 E1 ÷ E2（E2 ≤ 0 ⇒ 缺值）；MI ＝ 段內最近 25 根比值總和（25 根都有值 ⇒ 段內位置 40 起）。
    ★ 暖機：MI 只在段內位置 ≥ MI_WARM ＝ 60 時有效（起始值誤差到第 60 根對 MI 的影響約 0.03 點以內，遠小於 27／26.5 的 0.5 點間距）。
    EMA9(收盤)（方向條件與正式跑出場用）同 G2 起始法、同段、段內位置 8 起有值。不跨壞根：段一斷，所有指標重算。
 G3 凸起（登錄 §一 逐字）：MI[k−1]、MI[k] 都有效 ∧ MI[k−1] ≤ 27.0 ∧ MI[k] ＞ 27.0 ⇒ 凸起開始（k）；之後第一個 MI[t] ＜ 26.5（D1：＜ 26.0）
    ⇒ 凸起完成日 T ＝ t。一次凸起只算一次：完成前 MI 又在 27 上下來回不算新凸起；完成後要再由 ≤ 27.0 升破 27.0 才算下一次。
    ★ 凸起進行中碰到 MI 缺值（壞 K 棒、段首暖機）⇒ 該凸起作廢、不產生事件（不跨壞根）。★ 段內第一個有效 MI 已 ＞ 27 ⇒ 不算凸起開始（沒看到「升破」）。
    D1（26.0）用同一組 27.0 開始規則、各自一條狀態機（26.5 已完成而 26.0 未完成的凸起，在 D1 繼續等 ＜ 26.0）。
 G4 方向條件（登錄 §二；二手轉述）：EMA9c[T] ＜ EMA9c[T−1]（嚴格；兩者同段有值）⇒ 做多事件；否則不算（D2_無方向不看此條）。
 G5 剔除（每筆只記第一個原因；UO Q8／WR R7 同一套 ＝ WF.st_next_open）：閘外(500張/pit) → 壞根(T) → 壞根(T+1) → T+1無成交
    （下一根有效 K 棒不是日曆 T＋1、或無成交、或開盤缺值）→ T+1開盤鎖漲停（快取 upl；登錄「開盤鎖漲停買不到不算」）。保留 ＝ 事件數。
 G6 「同一檔持有中不重複進場」要出場日（收盤 ＜ EMA9 且 EMA9 下彎 ⇒ 進場後價格）⇒ 頻率表 ⛔ 不套；本表事件數 ＝ 上限（每次凸起至多一筆）。
 G7 必報「凸起數、加方向條件後保留比例」：凸起數 ＝ 段內凸起完成（偵測、剔除前、不看母體閘）＝ D2_無方向偵測數；
    方向保留比例 ＝ A 偵測 ÷ D2 偵測（剔除前）；另報 A 保留 ÷ D2 保留；D1 同報。另報凸起開始數（開始日在段內）與作廢數。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WF                  # noqa: E402  共用 base／st_next_open／run_freq（⛔ 只 import）

REG_SHA = "356f3ccfda10a90f"
OUT = "backtest/resultsMI/freq"
EMA_N = 9
MI_N = 25
MI_WARM = 60
UP = 27.0
DN = 26.5
DN_D1 = 26.0
CELLS = {"A": "判定格：MI 升破 27 後跌回 26.5 以下（凸起完成）且 EMA9(收盤) 當日下彎，T+1 開盤買",
         "D1_26": "描述 D1：凸起完成門檻改 26.0（同方向條件）",
         "D2_無方向": "描述 D2：不加方向條件（凸起完成就做多）"}


# ═════════════ G2 EMA、MI ═════════════
def seg_starts(bad):
    n = len(bad)
    st = [0] + [k for k in range(1, n) if bad[k]]
    return st, st[1:] + [n]


def ema_sma_seed(x, n=EMA_N):
    """單段：第 n 根（位置 n−1）＝ 前 n 個有值的簡單平均（x 前段可為缺值：從第一個有值位置起算），之後 α ＝ 2/(n+1) 遞迴。"""
    x = np.asarray(x, float); m = len(x); out = np.full(m, np.nan)
    fin = np.flatnonzero(np.isfinite(x))
    if len(fin) == 0:
        return out
    f0 = int(fin[0])
    if m - f0 < n:
        return out
    if not np.isfinite(x[f0:]).all():
        raise RuntimeError("⛔ EMA 輸入在起點後有缺值（不應發生）")
    seed = float(np.mean(x[f0:f0 + n]))
    s = pd.Series(np.r_[seed, x[f0 + n:]])
    out[f0 + n - 1:] = s.ewm(alpha=2.0 / (n + 1), adjust=False).mean().to_numpy(float)
    return out


def indicators(h, l, c, bad):
    """回 MI（已套暖機）、EMA9c、段內位置、E1、E2、比值。逐無壞 K 棒段各自起算。"""
    N = len(c)
    MI = np.full(N, np.nan); EC = np.full(N, np.nan); POS = np.zeros(N, np.int64)
    E1a = np.full(N, np.nan); E2a = np.full(N, np.nan); RA = np.full(N, np.nan)
    st, en = seg_starts(bad)
    for s, e in zip(st, en):
        POS[s:e] = np.arange(e - s)
        e1 = ema_sma_seed(h[s:e] - l[s:e]); e2 = ema_sma_seed(e1)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.where(e2 > 0, e1 / e2, np.nan)
        mi = pd.Series(r).rolling(MI_N, min_periods=MI_N).sum().to_numpy(float)
        E1a[s:e] = e1; E2a[s:e] = e2; RA[s:e] = r; MI[s:e] = mi
        EC[s:e] = ema_sma_seed(c[s:e])
    MI[POS < MI_WARM] = np.nan
    return MI, EC, POS, E1a, E2a, RA


# ═════════════ G3 凸起狀態機 ═════════════
def bulges(MI, dn=DN, up=UP):
    """回 (完成清單 [(T, 開始, 峰值)], 開始清單 [k], 作廢清單 [(開始, 作廢根)])。⛔ 判 t 只用 ≤ t 的 MI。"""
    done = []; starts = []; void = []
    armed = False; k0 = -1; pk = -np.inf
    for k in range(1, len(MI)):
        v = MI[k]
        if not np.isfinite(v):
            if armed:
                void.append((k0, k))
            armed = False
            continue
        if armed:
            pk = max(pk, v)
            if v < dn:
                done.append((k, k0, pk)); armed = False
            continue
        p = MI[k - 1]
        if np.isfinite(p) and p <= up and v > up:
            armed = True; k0 = k; pk = v; starts.append(k)
    return done, starts, void


def down(EC, k):
    return bool(k >= 1 and np.isfinite(EC[k]) and np.isfinite(EC[k - 1]) and EC[k] < EC[k - 1])


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    X = WF.base(wn, sid)
    if X is None:
        return sid, None
    h, l, c, bad, idx, cal = X["h"], X["l"], X["c"], X["bad"], X["idx"], X["cal"]
    MI, EC, POS, _, _, _ = indicators(h, l, c, bad)
    EV = {"A": [], "D1_26": [], "D2_無方向": [], "_開始": [], "_作廢": []}
    for dn, cells in ((DN, ("A", "D2_無方向")), (DN_D1, ("D1_26",))):
        done, starts, void = bulges(MI, dn)
        for (t, k0, pk) in done:
            dw = down(EC, t)
            rec = {"sid": sid, "T": int(idx[t]), "k": int(t), "凸起開始日": str(cal[idx[k0]].date()), "凸起根數": int(t - k0),
                   "MI峰值": float(pk), "MI[T-1]": float(MI[t - 1]), "MI[T]": float(MI[t]),
                   "EMA9c[T-1]": float(EC[t - 1]), "EMA9c[T]": float(EC[t]), "EMA9下彎": dw, "段內位置": int(POS[t]),
                   "st": WF.st_next_open(X, t)}
            for cell in cells:
                if cell == "D2_無方向" or dw:
                    EV[cell].append(dict(rec))
        if dn == DN:
            EV["_開始"] = [{"sid": sid, "T": int(idx[k]), "k": int(k), "st": "開始"} for k in starts]
            EV["_作廢"] = [{"sid": sid, "T": int(idx[k1]), "k": int(k1), "開始": int(idx[k0]), "st": "作廢"} for (k0, k1) in void]
    return sid, {"ev": EV, "expo": X["expo"], "nb": X["nb"], "nmi": int(np.isfinite(MI).sum()), "nst": len(EV["_開始"])}


def seg_extra(ok, p0, p1, cal):
    def cnt(cell, kept=False):
        return sum(1 for r in ok.values() for e in r["ev"][cell] if p0 <= e["T"] <= p1 and (not kept or e["st"] == "保留"))
    nD2, nA, nD1 = cnt("D2_無方向"), cnt("A"), cnt("D1_26")
    kD2, kA, kD1 = cnt("D2_無方向", True), cnt("A", True), cnt("D1_26", True)
    return {"凸起開始數(開始日在段內)": cnt("_開始"), "凸起作廢數(缺值中斷)": cnt("_作廢"),
            "凸起數(26.5完成,偵測)": nD2, "A偵測(加方向)": nA, "方向保留比例(偵測)": round(nA / nD2, 4) if nD2 else None,
            "凸起保留數": kD2, "A保留": kA, "方向保留比例(保留)": round(kA / kD2, 4) if kD2 else None,
            "D1偵測": nD1, "D1保留": kD1}


def main():
    WF.run_freq({"sha": REG_SHA, "out": OUT, "cells": CELLS, "job": stock_job, "ev_cells": ("A", "D1_26", "D2_無方向"),
                 "title": "Mass Index 反轉凸起 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
                 "ruling": "seq374 起草、seq375 發號；N_前段 ＋1；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N；乾跑",
                 "doc": __doc__, "seg_extra": seg_extra,
                 "diag": lambda ok: {"有效K棒": int(sum(r["nb"] for r in ok.values())), "MI有效K棒": int(sum(r["nmi"] for r in ok.values())),
                                     "凸起開始總數": int(sum(r["nst"] for r in ok.values()))}})


if __name__ == "__main__":
    main()
