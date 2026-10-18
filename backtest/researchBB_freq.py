# -*- coding: utf-8 -*-
"""布林通道 Method I（擠壓後突破）、Method II（%b 配 MFI 順勢）seq1【頻率表・乾跑】（台股策略線 單筆層登錄 sha d5ac888e15ab1418，
2026-10-18 11:08；裁定 seq371 §一、seq372 發號；N_前段 ＋2）——回測線計算子代理。
⛔ 只數事件日期與個數、剔除計數、n_eff、曝險股日；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、出場日（裁定 seq366、372：乾跑）。
   用到的價格只有 ≤ T 的日高低收與成交量；T＋1 只判「有沒有成交、開盤是否鎖漲停」。SAR、碰下軌、跌破中軌都是出場 ⇒ ⛔ 本表不算。
⛔ 不 commit、不改既有程式與結果夾；researchWR_freq（共用驅動）／researchUO_freq（轉折低點）／research11／patterns ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBB_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBB_freq_check
輸出 backtest/resultsBB/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格：
  M1  判定格（Method I）：擠壓日（BandWidth ＝ 含當日最近 125 根最低）之後 20 根內，收盤 ＞ 上軌 ⇒ T；T＋1 開盤買
  M2  判定格（Method II）：%b ＞ 0.8 ∧ MFI(10) ＞ 80 兩條同日成立的第一天 ⇒ T；T＋1 開盤買
  M3  描述（Method III，只描述）：W 底＋%b 由下軌外轉軌內＋MFI 方向確認（★ 操作化見 B8）
  （M1、M2「收盤判隔天開盤出場版」與「固定 20／60 日」只換出場 ⇒ 進場事件與 M1、M2 相同，不另列；對照隨機 20 檔要報酬 ⇒ ⛔ 不在頻率表）

═══ 讀法（B 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 B1 世界、母體、壞根、T 的母體閘、剔除、段、n_eff、每年／每檔每年 ＝ researchWR_freq R1、R2、R7、R10 原樣（同一支 base／st_next_open／run_freq）。
    所有「N 日」在【該股有效 K 棒序列】上數。
 B2 布林（登錄 §一）：中軌 ＝ 20 根收盤均值；★ 標準差用【母體標準差 ddof＝0】（Bollinger 原作明示 population）〔另一讀法 ddof＝1——不採〕；
    上／下軌 ＝ 中軌 ± 2σ；BandWidth ＝（上 − 下）÷ 中；%b ＝（收 − 下）÷（上 − 下）；σ ＝ 0 ⇒ %b 缺值。
    不跨壞根：[k−19, k] 內除第一根外有壞 K 棒 ⇒ 缺值。
 B3 MFI(10)（登錄 §一）：典型價 TP ＝（高＋低＋收）÷ 3（還原價）；★ 方向 ＝ TP[k] 與 TP[k−1] 比（＞ 正向、＜ 負向、＝ 兩邊都不計，通行定義）；
    ★ 資金流金額 ＝ 原始典型價 × 原始成交股數 ＝ TP[k] ÷ F[k] × V[k]（F ＝ 還原收 ÷ 原始收：成交量未還原，用原始價配原始量才是真實金額；
    10 根窗內只有除權息會讓 F 變動，影響極小）〔另一讀法：還原 TP × 原始量〕；
    MFI ＝ 100 − 100 ÷（1 ＋ 正÷負）＝ 100 × 正 ÷（正＋負）；負 ＝ 0 且正 ＞ 0 ⇒ 100；★ 正＋負 ＝ 0 ⇒ 缺值。
    不跨壞根：第 k 根是壞 K 棒（或第 0 根）⇒ 該根方向不可判 ⇒ 缺值傳染 10 根（rolling min_periods＝10）；成交量缺值同。
 B4 M1 擠壓日 s：BW[s−124..s] 125 根全有值 ∧ BW[s] ＝ 其最小值（★ 平手算擠壓）。
    ★「最近一次擠壓日之後 20 個交易日內」＝ 存在擠壓日 s ∈ [k−20, k−1]（擠壓當天不算「之後」；取最近的 s）∧ [s＋1, k] 無壞 K 棒；
    觸發 ＝ c[k] ＞ 上軌[k]（嚴格）。
    ★ 登錄沒寫「第一天」⇒ 窗內每一根收盤在上軌之上都算偵測（不套持有限制的【上限】；海龜 T7 同口徑），另報「前一根非事件（連續段第一根）」筆數。
 B5 M2：cond[k] ＝ %b[k] ＞ 0.8 ∧ MFI[k] ＞ 80（嚴格、兩者有值）；T ＝ cond[k] ∧ ¬cond[k−1]，★ 且 k−1 兩值都有值（前一天可判才算「第一天」，不跨壞根）。
 B6 「同一檔持有中不重複進場」要出場日（SAR、碰下軌、跌破中軌 ⇒ 進場後價格）⇒ 頻率表 ⛔ 不套；本表事件數 ＝ 上限，正式跑套持有限制後會減少。
    參考（⛔ 不用出場日）：同檔相鄰兩個保留事件間隔 ＝1、≤10、≤20 根的筆數。
 B7 開盤鎖漲停買不到 ⇒ 剔除「T+1開盤鎖漲停」（快取 upl：開盤＝漲停且全日鎖死）。
 B9 數值（對帳後補，2026-10-18，⛔ 未看任何報酬）：初版用 pandas 滾動 mean／std／sum，對帳 C3 發現其累加殘差（MFI 會略超 100、
    BW 在數學上相等的兩天之間有 1e−13 級差 ⇒ 擠壓日平手判定翻轉）⇒ 改逐窗精確計算（sliding_window_view）；擠壓判定 ★ 加相對容差
    BW[s] ≤ 125 根最小 ×（1＋1e−9）（數學上平手者一律算擠壓、不受浮點雜訊影響）。MFI 的缺值傳染改由「窗內有缺值 ⇒ 缺值」達成（同義）；
    MFI 改寫成 100 ×（正 ÷（正＋負））避免 100×正 先捨入而得 100.00000000000001。
 B8 M3（只描述；原作條件無硬數字 ⇒ ★ 全部由本件操作化，⛔ 不判）：轉折低點 ＝ researchUO_freq.pivots（還原收盤、左右各 5 根嚴格、第 s＋5 根確認、
    [s−4, s＋5] 無壞 K 棒）；相鄰兩個轉折低點 P1、P2：P2 − P1 ≤ 60 根；%b[P1] ＜ 0（第一低收在下軌外）∧ %b[P2] ＞ 0（第二低收在軌內）
    ∧ MFI[P2] ＞ MFI[P1]（方向確認）；確認 conf ＝ P2＋5，T ＝ conf＋1 … conf＋20 內第一根 c[t] ＞ max(c[P1..P2])（W 頸線）；
    [P1, T] 無壞 K 棒、指標有值；同一 T 由多組產生只算一筆；剔除同 B1。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WF                  # noqa: E402  共用 base／st_next_open／clean_window／run_freq（⛔ 只 import）
from backtest import researchUO_freq as RU                  # noqa: E402  pivots 原樣（⛔ 只 import）

REG_SHA = "d5ac888e15ab1418"
OUT = "backtest/resultsBB/freq"
BB_N = 20
BB_K = 2.0
SQ_N = 125
SQ_TOL = 1e-9
M1_WIN = 20
PB_TH = 0.8
MFI_N = 10
MFI_TH = 80.0
M3_GAP = 60
M3_WIN = 20
PIV_R = 5
CELLS = {"M1": "判定格 Method I：BW 125 日新低擠壓後 20 根內收盤＞上軌（每根都算，上限）",
         "M2": "判定格 Method II：%b＞0.8 且 MFI(10)＞80 同日成立的第一天",
         "M3": "描述 Method III（★操作化）：W 底＋%b 下軌外轉軌內＋MFI 方向確認＋頸線突破"}


def _win(x, n, fn):
    """out[k] ＝ fn(x[k−n+1..k])（k ＜ n−1 ⇒ 缺值；窗內有缺值 ⇒ 缺值）。"""
    x = np.asarray(x, float); out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = fn(np.lib.stride_tricks.sliding_window_view(x, n), axis=1)
    return out


def boll(c, bad, n=BB_N, k=BB_K):
    m = _win(c, n, np.mean)                     # B9：逐窗精確計算（不用 pandas 滾動累加，避免殘差）
    sd = _win(c, n, np.std)                     # np.std 預設 ddof＝0（母體）
    ok = WF.clean_window(bad, n)
    m[~ok] = np.nan; sd[~ok] = np.nan
    up = m + k * sd; lo = m - k * sd
    with np.errstate(invalid="ignore", divide="ignore"):
        bw = (up - lo) / m
        pb = np.where(sd > 0, (c - lo) / (up - lo), np.nan)
    return m, up, lo, bw, pb


def mfi(h, l, c, v, F, bad, n=MFI_N):
    tp = (h + l + c) / 3.0
    mf = tp / F * v
    N = len(c)
    dtp = np.full(N, np.nan); dtp[1:] = tp[1:] - tp[:-1]
    brk = np.asarray(bad, bool).copy(); brk[0] = True
    dtp[brk] = np.nan
    pos = np.where(dtp > 0, mf, 0.0); neg = np.where(dtp < 0, mf, 0.0)
    nanm = ~np.isfinite(dtp) | ~np.isfinite(mf)
    pos[nanm] = np.nan; neg[nanm] = np.nan
    P_ = _win(pos, n, np.sum)                   # B9：逐窗精確加總（pandas 滾動累加會留下殘差）
    N_ = _win(neg, n, np.sum)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(P_ + N_ > 0, 100.0 * (P_ / (P_ + N_)), np.nan)
    return out


def squeeze(bw, n=SQ_N):
    rmin = pd.Series(bw).rolling(n, min_periods=n).min().to_numpy(float)
    with np.errstate(invalid="ignore"):
        return np.isfinite(rmin) & np.isfinite(bw) & (bw <= rmin * (1 + SQ_TOL))


def detect_m1(c, up, sq, bad):
    """回 [(k, s)]：s ＝ [k−20, k−1] 內最近的擠壓日、[s＋1, k] 無壞 K 棒、c[k] ＞ up[k]。⛔ 判 k 只用 ≤ k 的資料。"""
    n = len(c); CB = np.r_[0, np.cumsum(np.asarray(bad, bool))]
    last = -10 ** 9; out = []
    for k in range(n):
        if k >= 1 and sq[k - 1]:
            last = k - 1
        if k - last <= M1_WIN and np.isfinite(up[k]) and c[k] > up[k] and CB[k + 1] - CB[last + 1] == 0:
            out.append((k, last))
    return out


def detect_m2(pb, MF):
    with np.errstate(invalid="ignore"):
        fin = np.isfinite(pb) & np.isfinite(MF)
        cond = fin & (pb > PB_TH) & (MF > MFI_TH)
    k = np.arange(1, len(pb))
    return [int(x) for x in k[cond[k] & fin[k - 1] & ~cond[k - 1]]]


def detect_m3(c, pb, MF, bad, piv):
    n = len(c); CB = np.r_[0, np.cumsum(np.asarray(bad, bool))]; d = {}
    for q in range(1, len(piv)):
        p1, p2 = piv[q - 1], piv[q]
        if p2 - p1 > M3_GAP:
            continue
        if not (np.isfinite(pb[p1]) and np.isfinite(pb[p2]) and np.isfinite(MF[p1]) and np.isfinite(MF[p2])):
            continue
        if not (pb[p1] < 0 and pb[p2] > 0 and MF[p2] > MF[p1]):
            continue
        neck = float(np.max(c[p1:p2 + 1])); conf = p2 + PIV_R
        for t in range(conf + 1, min(conf + M3_WIN, n - 1) + 1):
            if CB[t + 1] - CB[p1 + 1] != 0:
                break
            if c[t] > neck:
                if t not in d or p2 < d[t][1]:
                    d[t] = (p1, p2, neck)
                break
    return d


def stock_job(a):
    wn, sid = a
    X = WF.base(wn, sid)
    if X is None:
        return sid, None
    h, l, c, bad, idx, B, cal = X["h"], X["l"], X["c"], X["bad"], X["idx"], X["B"], X["cal"]
    v = pd.to_numeric(X["df"]["volume"], errors="coerce").to_numpy(float)[idx]
    rc = np.asarray(B["rc"], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        F = np.where(rc > 0, c / rc, np.nan)
    m, up, lo, bw, pb = boll(c, bad)
    MF = mfi(h, l, c, v, F, bad)
    sq = squeeze(bw)
    EV = {}
    m1 = detect_m1(c, up, sq, bad); ks1 = {k for k, _ in m1}
    EV["M1"] = [{"sid": sid, "T": int(idx[k]), "k": k, "擠壓日": str(cal[idx[s]].date()), "擠壓距T": int(k - s), "BW[s]": float(bw[s]),
                 "收": float(c[k]), "上軌": float(up[k]), "前一根也是事件": bool((k - 1) in ks1), "st": WF.st_next_open(X, k)} for k, s in m1]
    EV["M2"] = [{"sid": sid, "T": int(idx[k]), "k": k, "%b": float(pb[k]), "MFI": float(MF[k]), "%b[T-1]": float(pb[k - 1]),
                 "MFI[T-1]": float(MF[k - 1]), "st": WF.st_next_open(X, k)} for k in detect_m2(pb, MF)]
    piv = RU.pivots(c, bad, PIV_R)
    d3 = detect_m3(c, pb, MF, bad, piv)
    EV["M3"] = [{"sid": sid, "T": int(idx[t]), "k": t, "P1": str(cal[idx[p1]].date()), "P2": str(cal[idx[p2]].date()), "頸線": neck,
                 "%b[P1]": float(pb[p1]), "%b[P2]": float(pb[p2]), "MFI[P1]": float(MF[p1]), "MFI[P2]": float(MF[p2]),
                 "st": WF.st_next_open(X, t)} for t, (p1, p2, neck) in sorted(d3.items())]
    return sid, {"ev": EV, "expo": X["expo"], "nb": X["nb"], "nsq": int(sq.sum()), "nbb": int(np.isfinite(bw).sum()),
                 "nmfi": int(np.isfinite(MF).sum()), "npiv": len(piv)}


def main():
    WF.run_freq({"sha": REG_SHA, "out": OUT, "cells": CELLS, "job": stock_job, "ev_cells": ("M1", "M2", "M3"),
                 "title": "布林 Method I／II seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
                 "ruling": "seq371 §一、seq372 發號；N_前段 ＋2（Bonferroni 族 N＝2）；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N；乾跑",
                 "doc": __doc__,
                 "diag": lambda ok: {"有效K棒": int(sum(r["nb"] for r in ok.values())), "BW有值K棒": int(sum(r["nbb"] for r in ok.values())),
                                     "MFI有值K棒": int(sum(r["nmfi"] for r in ok.values())), "擠壓日總數": int(sum(r["nsq"] for r in ok.values())),
                                     "轉折低點總數": int(sum(r["npiv"] for r in ok.values()))}})


if __name__ == "__main__":
    main()
