# -*- coding: utf-8 -*-
"""PREREG外部作者 seq1（台股策略線登錄 seq1 sha 62e4026f16879fed「外部作者批七顆：波段醫生與楊爸」；裁定 seq248、249、252 發號，N ＋7，⚠ 事後追加）。
回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtAuth.py selftest|pre|body|early|report [--procs 2] [--reps 200] [--fake 1000]

═══ 沿用（登錄 §一；逐條）═══
  引擎 ＝ research11.simulate_mtm（＝ PREREG訊號系統 researchSig 同一套：N＝10、買進投入當時淨值 1/10、同日多於空格 ⇒ 抽籤 rng 1000＋r、
         200 顆取中位；成本 0.585%；無 tradable（進場開盤無效 ⇒ 收盤＝引擎原式；出場開盤無效 ⇒ 延到第一個有效開盤））
  價   ＝ rerun17.load_prices（快照 edc6f、還原、收盤 ffill）；訊號偵測 ＝ D.load_stock 還原 OHLC（float64）＋原始成交量（股數）
  母體 ＝ W1 eligible（resultsp9_engine/panel_ext.csv.gz 當月面板）∩ gate3；訊號日 t 看它那個月的面板
  段   ＝ 探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24｜主窗 2017-03-02～2026-08-24；各段獨立起跑（期初全現金）；進場 e＝t＋1 ∈ 段內；
         進場訊號 ⛔ 無時間出口（排程出場設在段尾次一交易日 ⇒ 段尾收盤按市值計、段尾未出場照報）
  出場 ＝ 出場條件 d 收盤成立 ⇒ d＋1 開盤賣（引擎 stop_line 在 d 放必觸發線）；d ≥ e（只看持有期間：訊號日 t 當天的跌破不算、也不擋進場，
         只計數報「訊號日同時跌破」列數；⚠ 與 researchSig 的「同日有出場訊號不進」不同，因本件登錄明寫只看持有期間）；
         持有中再出訊號不加碼（引擎 held）；賣出後再出訊號可再買
═══ 指標（有效 K 棒上算；⭐ 看數字前寫死）═══
  實體 ＝ (收 − 開) ÷ 開；長紅 ≥ +4%、長黑 ≤ −4%、小 K ｜實體｜＜ 2%
  均線 MA_n ＝ 還原收盤 n 根簡單平均、含當根（researchRev.ma_fsum：math.fsum ÷ n，避免恰好相等被 cumsum 誤差判成跌破）
  20 日均量 vm(t) ＝ t 之前 20 根（不含當根）成交量平均；「跌破 MA_n」＝ c(t−1) ≥ MA_n(t−1) 且 c(t) ＜ MA_n(t)（由上往下穿越，★ 補定）
═══ 七顆（登錄 §二；★ 補定全部照裁定 seq252 接受）═══
  W1：d0 長紅 ⇒ 1～3 根小 K（每根收 ≥ d0 低）⇒ 緊接長紅且收 ＞ d0 高 ＝ 訊號日；中間出現非小 K、或第 4 根還是小 K ⇒ 作廢
  W2：s 收盤上穿 MA250（c(s−1) ≤ MA250(s−1)、c(s) ＞ MA250(s)）且 s−60～s−1 中 ≥ 40 根收 ＜ MA250；基本面（s 當日可用）；
      r ∈ s＋1～s＋10 第一個「收 ＜ 前收、量 ＜ vm×0.5、收 ≥ MA250」＝ 訊號日；s＋1～r 間任一根收 ＜ MA250 ⇒ 作廢；自帶出場 ＝ 跌破 MA60
      基本面 ＝ 最近一期月營收 YoY ＞ 0（當月營收 ＞ 去年當月營收 ＞ 0；可用日 ＝ 次月 10 日後第一個交易日；最近一期 ＝ s 當日已可用、且該檔有申報的最近一期）
             或 最近一季稅後淨利由負轉正（單季本期淨利 ni：本季 ＞ 0 且上一季 ＜ 0；Q4 單季 ＝ 全年累計 − Q3 累計）
      ⚠ 季財報可用日用 A2 暫定：有 t57sb01 時戳（fin_hist b6cce05ba3 的 meta/filing_dates.csv）⇒ 上傳日期之後第一個交易日；
        其餘 ⇒ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 次年 3/31）之後第一個交易日再往後 5 個交易日；A0 落地後重跑 W2
      財報 ＝ fin_hist（main b6cce05ba3，git archive 到 ~/msdata/<sha>，唯讀）；只用本件母體（上市櫃名冊 gate3）內的公司
  Y1：準備日 p：vm(p) ≤ vm 在 p−250～p−1 的第 20 百分位（numpy 線性內插）、且 min(低 p−9～p) ≥ min(低 p−29～p−10）；
      突破日 b：p ∈ b−10～b−1 有準備日、量 ≥ vm×2、實體 ≥ +4%、收 ＞ N ＝ max(高 b−20～b−1)；
      回踩日 r ∈ {b＋1, b＋2} 第一個「低 ≤ max(N×1.01, MA5) 且 收 ≥ N」＝ 訊號日（★）；沒回踩 ⇒ 不進（放棄組：突破日次日開盤買的 20 日報酬）
  Y2：長黑日 d：收 ≥ max(高 d−60～d−1)×0.95、量 ≥ vm×2、實體 ≤ −4%；
      出 ＝ d＋1～d＋3 第一個收 ＜ d 低的那天；進 ＝ d＋1～d＋3 收都 ≥ d 低、且 d＋4 量 ≤ d 量×0.5、紅 K、收 ≥ (d 開＋d 收)/2 ⇒ d＋4（★）
  Y3：d：量 ≥ vm×3、實體 ≤ −4%；d＋1、d＋2（、d＋3）量逐根遞減（v(d＋1) ＜ v(d)…）且低 ≥ d 低；緊接一根 e：量 ≥ vm（★）、收上穿 MA5
      （c(e−1) ≤ MA5(e−1)、c(e) ＞ MA5(e)）；先試 e＝d＋3，不成且 d＋3 仍遞減不破 ⇒ 試 e＝d＋4；d＋5 前沒有 ⇒ 作廢
  Y4（出、疊加）：持有報酬 ＝ 收 ÷ 買價 − 1（買價 ＝ 引擎進場價）；以【之前各根】收盤的最高報酬判段：≥ +25% ⇒ 當根跌破 MA_k（k＝5／10 兩臂）即出；
      ≥ +10%（未到 25%）⇒ 當根收 ＜ 買價即出
  Y5（出）：收 ＜ MA20、量 v(t) ＜ v(t−1) ＜ … ＜ v(t−4)、MA20(t) ＜ MA20(t−5)
═══ 格、挑法、判定（登錄 §三）═══
  進場五顆 × 出場 {跌破 MA10, MA20, MA60} ＝ 15 格（W2 自帶 ＝ MA60）
  出場三顆：基準 ＝ 五顆進場任一（同檔同日只一列）抱 H ∈ {20, 60, 120}（第 H 根收盤出 ＝ 引擎 xpos ＝ e＋H−1，超過段尾 ⇒ 段尾次一日）
           ＋這條（誰先到先出；觸發 d ≤ xpos−2 才有效）⇒ Y2 出 3 格、Y4 6 格、Y5 3 格；另跑同 H 的「不加」基準
  ⚠ 本線讀法 Q1（登錄沒寫、報告標明）：Y2 是一顆（進＋出），N＋7 ⇒ Y2 的 1 格在「Y2 進 3 格 ∪ Y2 出 3 格」共 6 格裡照同一挑法挑；兩角色各自最好的另列描述
  退化格：主窗事件數 ＜ 200 或年均 ＜ 10（主窗 2,313 日 ÷ 245）⇒ 挑選前剔除、只描述；進場格事件 ＝ 主窗進場列；出場格事件 ＝ 主窗基準列裡有效觸發的列；
          探索段「段尾未出場」列 ＞ 50% 的格同樣剔除；一顆全部被剔 ⇒ 依構造不可判定（N 照 ＋7）
  探索段挑：過判準（年化 ＞ 0050 同段 且 年化÷|MDD| ≥ 0050）的裡取比值最高；都沒過取比值最高（同分取年化高）
  判定：確認段 ＋ 主窗全段各跑一次；兩段都合格 ⇒ 合格；只確認段 ⇒「確認段合格、全段未過」；另列同理
  對照：0050 同段｜同進場固定抱 20／60／120｜假訊號 1,000 次（同進場／同基準＋隨機出場：持有天數抽自本格 200 顆已結清交易，
        rng default_rng([20260927, i])、引擎 1000＋(i mod 200)）⇒ p（隨機年化 ≥ 本格）≥ 0.05 ⇒ 句前「隨機也做得到」
  描述：出場三顆另套「全市場任何一檔任何時候買」基準（四類單獨口徑：每月 eligible 全部、量測日次日開盤、抱 H、整筆在段內；配對差）
═══ 單筆層（登錄 §四；只描述）═══
  researchRev_win 同口徑：T ∈ [W0, W1−H]、同檔同訊號 20 日內只取第一筆、T＋1 停牌／開盤漲停／開盤跌停與 [起點, T＋H] 硬斷點剔除、
  R_H ＝ c[T＋H]（無成交取之前最後一根）÷ o[T＋1] − 1；差 ＝ R_H − 基準②（同月、前 20 日報酬同十分位；讀 resultsRev/win_stock_days.csv.gz）；
  CI 以月分群（95%）；扣 0.585% ＝ 往不利方向移；n_eff ＜ 10 ⇒ 依構造不可判定；穩不穩照 seq249
輸出 backtest/resultsExtAuth/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchSig as SG                                  # ⭐ 引擎殼（make_cell、summarize、agg、pick）與 researchRev（D.DATA ⇒ 快照）
from backtest import avgdown as AV
from backtest import research34 as R34

RV, D, RR, R11, L = SG.RV, SG.D, SG.RR, SG.R11, SG.L
H2, TR, MF = RV.H2, RV.TR, RV.MF
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsExtAuth")
COST = R11.COST
BIG = SG.BIG
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "主窗": ("2017-03-02", "2026-08-24")}
MAIN_DAYS = 2313
YEARS_MAIN = MAIN_DAYS / 245.0
PANEL = SG.PANEL
FIN_SHA = "b6cce05ba3b0fe4809d0c5e5c84abab8a1630f21"
FD = os.path.expanduser(f"~/msdata/{FIN_SHA}/data")
WIN_DAYS_FILE = os.path.join(HERE, "resultsRev", "win_stock_days.csv.gz")
ENTRIES = ["W1", "W2", "Y1", "Y2in", "Y3"]
EXOPT = ["MA10", "MA20", "MA60"]
OVERS = ["Y2out", "Y4_MA5", "Y4_MA10", "Y5"]
HB = (20, 60, 120)
HS = (5, 10, 20, 60)
KE = {"W1": "W1", "W2": "W2", "Y1": "Y1", "Y2": "Y2", "Y3": "Y3", "Y4": "Y4", "Y5": "Y5"}
NAME = {"W1": "上升三法", "W2": "年線戰法", "Y1": "量縮打底突破回踩", "Y2in": "高檔爆量長黑三日（進）", "Y2out": "高檔爆量長黑三日（出）",
        "Y3": "恐慌量後量縮不破底", "Y4_MA5": "三段移動停利（MA5 臂）", "Y4_MA10": "三段移動停利（MA10 臂）", "Y5": "量縮陰跌",
        "Y2": "高檔爆量長黑三日", "Y4": "三段移動停利"}
SE_CODES = ["W1", "W2", "Y1", "Y2in", "Y3", "Y2out", "Y5"]
SE_BEAR = {"Y2out", "Y5"}
TAG = "⚠ 事後追加（看過反轉訊號、訊號系統結果後才加；裁定 seq248 ⑦）"
A2TAG = "季財報可用日 A2 暫定（有 t57sb01 時戳用時戳；其餘法定期限＋5 個交易日緩衝）；A0 落地後重跑 W2"
_G: dict = {}


# ═════════════════════════════ 指標與偵測（有效 K 棒空間）
def vma(v, n=20):
    """vm[i] ＝ v[i−n..i−1] 平均（不含當根）；前 n 根或窗內有缺 ⇒ NaN。成交量是整數 ⇒ cumsum 精確。"""
    v = np.asarray(v, float); nb = len(v)
    fin = np.isfinite(v); vv = np.where(fin, v, 0.0)
    cs = np.r_[0.0, np.cumsum(vv)]; cf = np.r_[0, np.cumsum(fin)]
    out = np.full(nb, np.nan)
    if nb > n:
        i = np.arange(n, nb)
        s = cs[i] - cs[i - n]; k = cf[i] - cf[i - n]
        out[n:] = np.where(k == n, s / n, np.nan)
    return out


def rmax(x, n):
    """rm[i] ＝ max(x[i−n..i−1])；不足 n 根 ⇒ NaN。"""
    x = np.asarray(x, float); nb = len(x); out = np.full(nb, np.nan)
    if nb > n:
        W = np.lib.stride_tricks.sliding_window_view(x, n)[:nb - n]
        out[n:] = W.max(axis=1)
    return out


def rmin_incl(x, a, b):
    """out[i] ＝ min(x[i−a..i−b])（a ≥ b ≥ 0、含兩端）；不足 ⇒ NaN。"""
    x = np.asarray(x, float); nb = len(x); w = a - b + 1; out = np.full(nb, np.nan)
    if nb > a:
        W = np.lib.stride_tricks.sliding_window_view(x, w)          # W[j] ＝ x[j..j+w−1]
        i = np.arange(a, nb)
        out[a:] = W[i - a].min(axis=1)
    return out


def detect(o, h, l, c, v):
    """有效 K 棒陣列 ⇒ {code: 訊號 K 棒位置（排序、唯一）}；另回 W2 候選 (s, r)、Y1 突破 (b, r|−1)、各訊號的形態起點 first。"""
    nb = len(c)
    with np.errstate(invalid="ignore", divide="ignore"):
        bd = (c - o) / o
    LR = bd >= 0.04; LB = bd <= -0.04; SM = np.abs(bd) < 0.02
    vm = vma(v, 20)
    ma = {k: RV.ma_fsum(c, k) for k in (5, 10, 20, 60, 250)}
    out = {}; first = {}
    # W1
    w1 = {}
    for d0 in np.flatnonzero(LR):
        cnt = 0; j = d0 + 1
        while j < nb:
            if cnt >= 1 and LR[j] and c[j] > h[d0]:
                w1.setdefault(j, d0); break
            if SM[j] and c[j] >= l[d0] and cnt < 3:
                cnt += 1; j += 1; continue
            break
    out["W1"] = np.array(sorted(w1), int); first["W1"] = np.array([w1[j] for j in sorted(w1)], int)
    # W2 候選
    m250 = ma[250]
    with np.errstate(invalid="ignore"):
        below = np.isfinite(m250) & (c < m250)
    cb = np.r_[0, np.cumsum(below)]
    w2 = []
    for s in range(61, nb):
        if not (np.isfinite(m250[s - 1]) and np.isfinite(m250[s]) and c[s - 1] <= m250[s - 1] and c[s] > m250[s]):
            continue
        if cb[s] - cb[s - 60] < 40:
            continue
        for j in range(s + 1, min(s + 10, nb - 1) + 1):
            if not c[j] >= m250[j]:
                break
            if c[j] < c[j - 1] and np.isfinite(vm[j]) and v[j] < vm[j] * 0.5:
                w2.append((s, j)); break
    out["W2c"] = np.array(w2, int).reshape(-1, 2)
    # Y1
    pct = np.full(nb, np.nan)
    if nb > 250:
        W = np.lib.stride_tricks.sliding_window_view(vm, 250)[:nb - 250]
        pct[250:] = np.percentile(W, 20, axis=1)
    lo_a = rmin_incl(l, 9, 0); lo_b = rmin_incl(l, 29, 10)
    with np.errstate(invalid="ignore"):
        prep = np.isfinite(vm) & np.isfinite(pct) & (vm <= pct) & np.isfinite(lo_a) & np.isfinite(lo_b) & (lo_a >= lo_b)
    cp = np.r_[0, np.cumsum(prep)]
    hh20 = rmax(h, 20)
    y1 = {}; y1b = []
    for b in range(11, nb):
        if not (cp[b] - cp[b - 10] > 0):
            continue
        if not (np.isfinite(vm[b]) and v[b] >= vm[b] * 2 and LR[b] and np.isfinite(hh20[b]) and c[b] > hh20[b]):
            continue
        N = hh20[b]; rr = -1
        for r in (b + 1, b + 2):
            if r < nb and l[r] <= np.fmax(N * 1.01, ma[5][r]) and c[r] >= N:
                rr = r; break
        y1b.append((b, rr))
        if rr >= 0:
            y1.setdefault(rr, max(b - 30, 0))
    out["Y1"] = np.array(sorted(y1), int); first["Y1"] = np.array([y1[j] for j in sorted(y1)], int)
    out["Y1b"] = np.array(y1b, int).reshape(-1, 2)
    # Y2
    hh60 = rmax(h, 60)
    y2i = {}; y2o = {}
    with np.errstate(invalid="ignore"):
        cand = np.flatnonzero(np.isfinite(hh60) & (c >= hh60 * 0.95) & np.isfinite(vm) & (v >= vm * 2) & LB)
    for d in cand:
        jx = -1
        for j in range(d + 1, min(d + 3, nb - 1) + 1):
            if c[j] < l[d]:
                jx = j; break
        if jx >= 0:
            y2o.setdefault(jx, max(d - 60, 0)); continue
        e = d + 4
        if e < nb and v[e] <= v[d] * 0.5 and c[e] > o[e] and c[e] >= (o[d] + c[d]) / 2:
            y2i.setdefault(e, max(d - 60, 0))
    out["Y2in"] = np.array(sorted(y2i), int); first["Y2in"] = np.array([y2i[j] for j in sorted(y2i)], int)
    out["Y2out"] = np.array(sorted(y2o), int); first["Y2out"] = np.array([y2o[j] for j in sorted(y2o)], int)
    # Y3
    y3 = {}
    with np.errstate(invalid="ignore"):
        cand = np.flatnonzero(np.isfinite(vm) & (v >= vm * 3) & LB)

    def dec(k, d):
        return k < nb and v[k] < v[k - 1] and l[k] >= l[d]

    def ce(e):
        return (e < nb and np.isfinite(vm[e]) and v[e] >= vm[e] and np.isfinite(ma[5][e - 1]) and np.isfinite(ma[5][e])
                and c[e - 1] <= ma[5][e - 1] and c[e] > ma[5][e])
    for d in cand:
        if not (dec(d + 1, d) and dec(d + 2, d)):
            continue
        if ce(d + 3):
            y3.setdefault(d + 3, max(d - 20, 0))
        elif dec(d + 3, d) and ce(d + 4):
            y3.setdefault(d + 4, max(d - 20, 0))
    out["Y3"] = np.array(sorted(y3), int); first["Y3"] = np.array([y3[j] for j in sorted(y3)], int)
    # Y5
    m20 = ma[20]
    y5 = np.zeros(nb, bool)
    if nb > 5:
        t = np.arange(5, nb)
        with np.errstate(invalid="ignore"):
            y5[5:] = (c[t] < m20[t]) & (v[t] < v[t - 1]) & (v[t - 1] < v[t - 2]) & (v[t - 2] < v[t - 3]) & (v[t - 3] < v[t - 4]) & (m20[t] < m20[t - 5])
    out["Y5"] = np.flatnonzero(y5); first["Y5"] = np.maximum(out["Y5"] - 5, 0)
    # 均線跌破（由上往下穿越）與「收 ＜ MA」
    for k in (5, 10, 20, 60):
        m = ma[k]; x = np.zeros(nb, bool)
        with np.errstate(invalid="ignore"):
            x[1:] = (c[:-1] >= m[:-1]) & (c[1:] < m[1:])
            out[f"BL{k}"] = np.flatnonzero(c < m)
        out[f"MA{k}"] = np.flatnonzero(x)
    return out, first


def y4_day(c, bars_in, ep, xdn_bool):
    """Y4 觸發（日曆位置；無 ⇒ −1）。bars_in ＝ [e, lim] 內的有效 K 棒（日曆位置、排序）；xdn_bool ＝ 日曆布林（跌破 MA_k）。"""
    if len(bars_in) == 0:
        return -1
    cc = c[bars_in]
    pm = np.maximum.accumulate(np.r_[-np.inf, cc[:-1]])
    t25 = pm >= ep * 125 / 100; t10 = (pm >= ep * 110 / 100) & ~t25
    trig = (t25 & xdn_bool[bars_in]) | (t10 & (cc < ep))
    w = np.flatnonzero(trig)
    return int(bars_in[w[0]]) if len(w) else -1


# ═════════════════════════════ 基本面（W2）
def load_fund(cal, log, with_fin=True):
    """回 FUND：sid → {rev_av, rev_ok, fin: [(period_idx, av_pos, ni, src)]}、統計。"""
    rev, rev_ly, _ = R34.load_revenue()
    rd = R34.rebalance_dates(list(rev.index), cal, 10)
    per = [p for p in rev.index if p in rd]
    av = np.array([rd[p][1] for p in per], int)
    FUND = {}
    for sid in rev.columns:
        r_ = rev.loc[per, sid].to_numpy(float); ly = rev_ly.loc[per, sid].to_numpy(float) if sid in rev_ly.columns else np.full(len(per), np.nan)
        m = np.isfinite(r_)
        with np.errstate(invalid="ignore"):
            ok = m & np.isfinite(ly) & (ly > 0) & (r_ > ly)
        FUND[sid] = {"rev_av": av[m], "rev_ok": ok[m], "fin": []}
    st = {"月營收期別": [per[0], per[-1]] if per else None}
    if not with_fin:
        return FUND, st
    fs = sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv")))
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "ni_q", "ni_ytd"]) for f in fs], ignore_index=True)
    F = F.drop_duplicates(["stock_id", "period"], keep="last")
    F["y"] = F["period"].str[:4].astype(int); F["q"] = F["period"].str[-1].astype(int)
    ytd = {(s, y, q): v for s, y, q, v in zip(F["stock_id"], F["y"], F["q"], F["ni_ytd"])}
    niq = []
    for s, y, q, a_, b_ in zip(F["stock_id"], F["y"], F["q"], F["ni_q"], F["ni_ytd"]):
        if np.isfinite(a_):
            niq.append(a_)
        elif q == 1:
            niq.append(b_)
        else:
            p_ = ytd.get((s, y, q - 1), np.nan)
            niq.append(b_ - p_ if (np.isfinite(b_) and np.isfinite(p_)) else np.nan)
    F["ni"] = niq
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    fd["d"] = pd.to_datetime(fd["uploaded_at"].str[:10], errors="coerce")
    fd = fd.dropna(subset=["d"]).groupby(["stock_id", "year", "season"])["d"].min()
    dl = {1: (5, 15), 2: (8, 14), 3: (11, 14)}
    n_ts = 0; n_dl = 0
    for s, g in F.groupby("stock_id"):
        rows = []
        for y, q, ni in zip(g["y"], g["q"], g["ni"]):
            ts = fd.get((s, y, q)) if (s, y, q) in fd.index else None
            if ts is not None and not pd.isna(ts):
                pos = int(cal.searchsorted(ts, side="right")); src = "ts"; n_ts += 1
            else:
                ddl = pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, *dl[q])
                pos = int(cal.searchsorted(ddl, side="right")) + 5; src = "dl"; n_dl += 1
            rows.append((y * 4 + q - 1, pos, float(ni), src))
        FUND.setdefault(s, {"rev_av": np.zeros(0, int), "rev_ok": np.zeros(0, bool), "fin": []})["fin"] = sorted(rows)
    st.update({"fin_hist": f"{FIN_SHA[:10]}（{len(fs)} 季檔、{len(F):,} 列）", "季別可用日_時戳": n_ts, "季別可用日_期限＋5": n_dl})
    log(f"[基本面] {st}")
    return FUND, st


def fund_ok(FUND, sid, s):
    """(過不過, 來源)：來源 rev／fin_ts／fin_dl／''。"""
    f = FUND.get(sid)
    if f is None:
        return False, ""
    i = int(np.searchsorted(f["rev_av"], s, side="right")) - 1
    if i >= 0 and f["rev_ok"][i]:
        return True, "rev"
    fin = f["fin"]
    if fin:
        avail = [x for x in fin if x[1] <= s]
        if avail:
            q = max(avail, key=lambda x: x[0])
            prev = [x for x in fin if x[0] == q[0] - 1]
            if prev and np.isfinite(q[2]) and np.isfinite(prev[0][2]) and q[2] > 0 and prev[0][2] < 0:
                return True, "fin_" + q[3]
    return False, ""


# ═════════════════════════════ 每檔（訊號、單筆層、全市場基準）
def stock_work(args):
    sid, market = args
    cal = _G["cal"]; n = len(cal); mode = _G["mode"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 30:
        return None
    sel = lambda x: np.asarray(x, float)[bars]
    B, F = detect(sel(o), sel(h), sel(l), c[bars], sel(v))
    S = {}; FIRST = {}
    for k, x in B.items():
        if k == "W2c":
            S[k] = bars[x] if len(x) else np.zeros((0, 2), int)
        elif k == "Y1b":
            S[k] = (np.stack([bars[x[:, 0]], np.where(x[:, 1] >= 0, bars[np.maximum(x[:, 1], 0)], -1)], axis=1)
                    if len(x) else np.zeros((0, 2), int))
        else:
            S[k] = bars[x].astype(np.int32)
    for k, x in F.items():
        FIRST[k] = bars[x].astype(np.int32) if len(x) else np.zeros(0, np.int32)
    # W2：基本面在 s
    keep = []; srcs = []
    for s_, r_ in S["W2c"]:
        ok, src = fund_ok(_G["FUND"], sid, int(s_))
        if ok:
            keep.append(int(r_)); srcs.append(src)
    S["W2"] = np.array(sorted(set(keep)), np.int32)
    FIRST["W2"] = np.array([int(dict(zip(S["W2c"][:, 1].tolist(), S["W2c"][:, 0].tolist()))[r]) - 60 for r in S["W2"]], np.int32) if len(S["W2"]) else np.zeros(0, np.int32)
    w2src = {}
    for s_ in srcs:
        w2src[s_] = w2src.get(s_, 0) + 1
    res = {"sid": sid, "market": market, "S": S, "c": c, "valid": np.packbits(valid), "w2src": w2src,
           "w2_cand": int(len(S["W2c"])), "w2_pass": int(len(keep))}
    if mode != "body":
        return res
    # ── 單筆層事件（researchRev_win 同口徑）
    w0, w1, mon, elig = _G["w0"], _G["w1"], _G["mon"], _G["elig"]
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = MF._g5(valid, upto=ds["last"]) if delisted else MF._g5(valid)
    SB = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    lv = AV.last_valid(valid); em = elig.get(sid, set())
    halt = ~tb["trd"] | ~np.isfinite(o)
    ev = []
    for code in SE_CODES:
        T0 = S[code]; F0 = FIRST[code]
        for H in HS:
            m = (T0 >= w0) & (T0 <= w1 - H)
            T, Fs = T0[m], F0[m]
            if len(T):
                m2 = np.array([mon[t] in em for t in T], bool); T, Fs = T[m2], Fs[m2]
            kp = RV.merge20(T)
            for t, f, k in zip(T, Fs, kp):
                if not k:
                    continue
                t = int(t)
                why = ("剔除_硬斷點" if H2.brk(SB, int(f), t + H) else
                       ("剔除_停牌" if halt[t + 1] else ("剔除_開盤漲停" if tb["up_o"][t + 1] else ("剔除_開盤跌停" if tb["dn_o"][t + 1] else "保留"))))
                r = {"sid": sid, "code": code, "H": H, "T": t, "st": why}
                if why == "保留":
                    r["R"] = float(c[lv[t + H]] / o[t + 1] - 1.0)
                ev.append(r)
    res["ev"] = ev
    # Y1 放棄組（主窗、eligible 月、突破日次日開盤買的 20 日報酬）
    ab = []
    for b_, r_ in S["Y1b"]:
        b_ = int(b_)
        if w0 <= b_ <= w1 - 21 and mon[b_] in em and not halt[b_ + 1] and not H2.brk(SB, b_ - 30, b_ + 21):
            ab.append({"sid": sid, "b": b_, "r": int(r_), "R20_b": float(c[lv[b_ + 20]] / o[b_ + 1] - 1.0),
                       "R20_r": float(c[lv[int(r_) + 20]] / o[int(r_) + 1] - 1.0) if (r_ >= 0 and r_ + 20 <= w1 and not halt[int(r_) + 1]) else np.nan})
    res["y1ab"] = ab
    # ── 全市場基準（四類單獨口徑）上的出場三顆
    ok_sell = AV.trade_ok(tb["trd"], tb["dn_o"], o); ok_buy = AV.trade_ok(tb["trd"], tb["up_o"], o)
    nxt_sell = AV.next_true(ok_sell)
    xd = {"Y2out": np.zeros(n, bool), "Y5": np.zeros(n, bool), "MA5": np.zeros(n, bool), "MA10": np.zeros(n, bool)}
    for k in xd:
        xd[k][S[k]] = True
    q = []
    for T_ in _G["MEAS"].get(sid, []):
        e = int(T_) + 1
        for H in HB:
            x = e + H - 1
            seg = "探索" if (e >= _G["P"]["探索"][0] and x <= _G["P"]["探索"][1]) else ("確認" if (e >= _G["P"]["確認"][0] and x <= _G["P"]["確認"][1]) else "")
            if not seg or x >= n:
                continue
            if not ok_buy[e]:
                q.append({"sid": sid, "e": e, "H": H, "seg": seg, "st": "進場日漲停或停牌"}); continue
            if bool(AV.brk_vec(SB["cs_pb"], SB["cs_g5"], e, x)[0]):
                q.append({"sid": sid, "e": e, "H": H, "seg": seg, "st": "硬斷點"}); continue
            P0 = float(o[e]); j = int(lv[x]); base = float(c[j] / P0 - 1.0 - COST)
            r = {"sid": sid, "e": e, "H": H, "seg": seg, "st": "保留", "base": base}
            bi = bars[(bars >= e) & (bars <= x - 1)]
            for code in OVERS:
                if code.startswith("Y4"):
                    d = y4_day(c, bi, P0, xd["MA5" if code == "Y4_MA5" else "MA10"])
                else:
                    w = bi[xd[code][bi]]
                    d = int(w[0]) if len(w) else -1
                s_ = int(nxt_sell[d + 1]) if (d >= 0 and d + 1 < n) else -1
                if d >= 0 and 0 <= s_ < x:
                    r[f"d_{code}"] = float((o[s_] / P0 - 1.0 - COST) - base); r[f"t_{code}"] = 1
                else:
                    r[f"d_{code}"] = 0.0; r[f"t_{code}"] = 0
            q.append(r)
    res["quad"] = q
    return res


def _init(d):
    _G.update(d)


# ═════════════════════════════ 列
def entry_rows(SIG, elig, mon, code, xopt, s0, s1):
    rows = []; drop_same = 0
    for sid, X in SIG.items():
        em = elig.get(sid)
        if not em:
            continue
        ent = np.asarray(X["S"][code], int)
        ent = ent[(ent + 1 >= s0) & (ent + 1 <= s1)]
        if not len(ent):
            continue
        ent = ent[np.array([mon[t] in em for t in ent], bool)]
        Xd = np.asarray(X["S"][xopt], int)
        drop_same += int(np.isin(ent, Xd).sum())          # ⭐ 只計數、⛔ 不剔除：出場只看持有期間（d ≥ e＝t＋1），訊號日當天的跌破不算（登錄 §一）
        for t in ent:
            e = int(t) + 1
            i = int(np.searchsorted(Xd, e))
            dX = int(Xd[i]) if i < len(Xd) and Xd[i] <= s1 else -1
            rows.append((sid, int(t), e, dX))
    return pd.DataFrame(rows, columns=["sid", "t", "entry_pos", "dX"]), drop_same


def base_rows(SIG, elig, mon, s0, s1):
    """五顆進場任一（同檔同日一列）；src ＝ 哪幾顆。"""
    rows = []
    for sid, X in SIG.items():
        em = elig.get(sid)
        if not em:
            continue
        parts = [(k, np.asarray(X["S"][k], int)) for k in ENTRIES]
        ent = np.unique(np.concatenate([p for _, p in parts]))
        ent = ent[(ent + 1 >= s0) & (ent + 1 <= s1)]
        if not len(ent):
            continue
        ent = ent[np.array([mon[t] in em for t in ent], bool)]
        ps = [(k, set(p.tolist())) for k, p in parts]
        for t in ent:
            rows.append((sid, int(t), int(t) + 1, "+".join(k for k, p in ps if int(t) in p)))
    return pd.DataFrame(rows, columns=["sid", "t", "entry_pos", "src"])


def overlay_days(R, SIG, code, H, s1, ep, ncal):
    """每列：xpos 與觸發日 d（d ≤ min(s1, xpos−2)；無 ⇒ −1）。"""
    xp = np.minimum(R["entry_pos"].to_numpy(int) + H - 1, s1 + 1)
    d = np.full(len(R), -1, int)
    if code is None:
        return xp, d
    for i, (sid, e, x) in enumerate(zip(R["sid"], R["entry_pos"].to_numpy(int), xp)):
        X = SIG[sid]; lim = min(s1, int(x) - 2)
        if lim < e:
            continue
        if code.startswith("Y4"):
            k = "MA5" if code == "Y4_MA5" else "MA10"
            xb = X.get("_xb_" + k)
            if xb is None:
                xb = np.zeros(ncal, bool); xb[X["S"][k]] = True; X["_xb_" + k] = xb
            vb = X.get("_bars")
            if vb is None:
                vb = np.flatnonzero(np.unpackbits(X["valid"])[:ncal].astype(bool)); X["_bars"] = vb
            bi = vb[(vb >= e) & (vb <= lim)]
            d[i] = y4_day(X["c"], bi, ep[i], xb)
        else:
            Xd = np.asarray(X["S"][code], int)
            j = int(np.searchsorted(Xd, e))
            d[i] = int(Xd[j]) if j < len(Xd) and Xd[j] <= lim else -1
    return xp, d


def make_fixed(R, xp, d, ep, cz, why_name):
    sig = pd.DataFrame({"sid": R["sid"].to_numpy(), "entry_pos": R["entry_pos"].to_numpy(int), "xpos_X": xp})
    sig["g_X"] = [float(cz[s][x]) / e_ - 1.0 for s, x, e_ in zip(sig["sid"], xp, ep)]
    sl = {(s, int(e)): (int(dd), np.array([BIG])) for s, e, dd in zip(sig["sid"], sig["entry_pos"], d) if dd >= 0}
    reason = {(s, int(e)): (why_name if dd >= 0 else "H", int(dd)) for s, e, dd in zip(sig["sid"], sig["entry_pos"], d)}
    return sig, ({"stop_line": sl} if sl else {}), reason


# ═════════════════════════════ 引擎
def run_one(args):
    key, r, s0, s1 = args
    G = SG._G
    sig, kw, reason, cf = G["CELLS"][key]
    au = []
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), G["cz"], G["oz"], G["ncal"], return_equity=True, audit=au, **kw)
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, s1)
    res = SG.summarize(key, r, au, eq, hv, c_, m_, reason, cf, s0, s1)
    cst = sum(float(a["cost"]) / float(a["equity_prev"]) for a in au if a["side"] == "sell" and int(a["t"]) <= s1 and a.get("equity_prev", 0) > 0)
    res["costyr"] = cst / ((s1 - s0 + 1) / 245.0)
    return res


def run_cells(keys, s0, s1, reps, procs, tag, log):
    t0 = time.time(); res = {k: [] for k in keys}
    with Pool(procs) as pool:
        for x in pool.imap_unordered(run_one, [(k, r, s0, s1) for k in keys for r in range(reps)], chunksize=2):
            res[x["key"]].append(x)
    log(f"  [{tag}] {len(keys)} 格 × {reps} 顆｜{time.time() - t0:.0f}s")
    return res


def agg2(rows, bench):
    out = SG.agg(rows, bench)
    out["換手成本_每年"] = float(np.mean([x["costyr"] for x in rows]))
    return out


def fake_one(i):
    J = SG._G["FAKEJOB"]
    R, xp, s1, s0, hold = J["R"], J["xp"], J["s1"], J["s0"], J["hold"]
    rng = np.random.default_rng([20260927, i]); r = i % 200
    e = R["entry_pos"].to_numpy(int)
    h = rng.choice(hold, size=len(R), replace=True) if len(hold) else np.full(len(R), 10 ** 6)
    dA = e + h - 1
    dA = np.where(dA <= np.minimum(s1, xp - 2), dA, -1)
    sig, kw, _ = make_fixed(R, xp, dA, J["ep"], SG._G["cz"], "rand")
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), SG._G["cz"], SG._G["oz"], SG._G["ncal"], return_equity=True, **kw)
    c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)
    return float(c_), float(m_)


# ═════════════════════════════ 統計（單筆層）
def se_stats(X, g, bear, z=1.959963984540054):
    X = np.asarray(X, float); n = len(X)
    if n == 0:
        return {"n": 0, "n_eff": 0, "判定": "依構造不可判定"}
    m, se, ng = AV.cr0(X, np.asarray(g)); ne = int(min(n, ng))
    out = {"n": n, "n_eff": ne, "mean": m, "se": se}
    if ne < RV.NEFF_MIN:
        out["判定"] = "依構造不可判定"; return out
    lo, hi = m - z * se, m + z * se
    fav = (hi < 0) if bear else (lo > 0)
    sh = COST if bear else -COST
    out.update(lo=lo, hi=hi, mean_net=m + sh, lo_net=lo + sh, hi_net=hi + sh,
               判定=("有利方向（95% CI 不含 0）" if fav else ("反方向（95% CI 不含 0）" if ((lo > 0) if bear else (hi < 0)) else "分不出（CI 含 0）")),
               扣成本後=("仍在有利方向" if ((hi + sh < 0) if bear else (lo + sh > 0)) else "不在有利方向"))
    return out


def stability(C):
    out = {}
    for code, g in C.groupby("code"):
        g = g.set_index("H").reindex(list(HS)); bear = code in SE_BEAR
        fav = lambda x: (x < 0) if bear else (x > 0)
        passed = [H for H in HS if str(g.at[H, "判定"]).startswith("有利")]
        if not passed:
            out[code] = "四個視窗都沒有有利方向的顯著差" if (g["判定"] != "依構造不可判定").any() else "四個視窗都依構造不可判定"
            continue
        parts = []
        for H in passed:
            i = HS.index(H); nb = [HS[j] for j in (i - 1, i + 1) if 0 <= j < len(HS)]
            ok = [x for x in nb if np.isfinite(g.at[x, "mean"]) and fav(g.at[x, "mean"])]
            parts.append(f"{H} 天有利、相鄰（{'／'.join(map(str, nb))} 天）同向 ⇒ 穩" if len(ok) == len(nb)
                         else f"只在 {H} 天看得到、不穩（相鄰 {'／'.join(str(x) for x in nb if x not in ok)} 天方向相反）")
        out[code] = "；".join(parts)
    return out


# ═════════════════════════════ selftest（偵測 fixture：手造 K 棒，逐顆「該觸發／不該觸發」）
def selftest():
    ok = []

    def chk(name, got, exp):
        good = list(map(int, got)) == list(exp); ok.append(good)
        print(f"  {'✅' if good else '❌'} {name}：得 {list(map(int, got))}／應 {list(exp)}")
    base = 100.0
    # 平盤 260 根（量 1000），之後放形態
    def flat(nb=320, px=base, vol=1000.0):
        o = np.full(nb, px); c = np.full(nb, px); h = np.full(nb, px * 1.005); l = np.full(nb, px * 0.995); v = np.full(nb, vol)
        return o, h, l, c, v
    # W1：長紅 d0＝270（100→105），2 根小 K 收 ≥ d0 低，第 273 根長紅收 110 ＞ d0 高 105.5
    o, h, l, c, v = flat()
    o[270], c[270], h[270], l[270] = 100, 105, 105.5, 99.8
    for j in (271, 272):
        o[j], c[j], h[j], l[j] = 104.5, 105, 105.3, 104
    o[273], c[273], h[273], l[273] = 105, 110, 110.2, 104.9
    B, _ = detect(o, h, l, c, v); chk("W1 兩根小 K 後長紅過高 ⇒ 273", B["W1"], [273])
    o2, h2, l2, c2, v2 = [x.copy() for x in (o, h, l, c, v)]
    o2[272], c2[272] = 104.5, 101.0                                 # 第二根變成實體 −3.35%（非小 K）⇒ 作廢
    B, _ = detect(o2, h2, l2, c2, v2); chk("W1 中間出現非小 K ⇒ 無", B["W1"], [])
    o3, h3, l3, c3, v3 = [x.copy() for x in (o, h, l, c, v)]
    for j in (271, 272, 273, 274):
        o3[j], c3[j], h3[j], l3[j] = 104.5, 105, 105.3, 104
    o3[275], c3[275], h3[275], l3[275] = 105, 110, 110.2, 104.9     # 4 根小 K ⇒ 作廢
    B, _ = detect(o3, h3, l3, c3, v3); chk("W1 4 根小 K ⇒ 無", B["W1"], [])
    # Y2：d＝280 高檔爆量長黑；d＋1～d＋3 守住；d＋4 量縮紅 K 收復一半 ⇒ 284
    o, h, l, c, v = flat()
    o[280], c[280], h[280], l[280], v[280] = 101, 96, 101.2, 95.5, 3000
    for j in (281, 282, 283):
        o[j], c[j], h[j], l[j], v[j] = 96, 96.5, 97, 95.6, 1500
    o[284], c[284], h[284], l[284], v[284] = 97, 99, 99.2, 96.8, 1400
    B, _ = detect(o, h, l, c, v); chk("Y2 進 ⇒ 284", B["Y2in"], [284]); chk("Y2 出 ⇒ 無", B["Y2out"], [])
    c[282] = 95.0; l[282] = 94.8                                     # d＋2 收破 d 低 ⇒ 出場訊號 282、進場作廢
    B, _ = detect(o, h, l, c, v); chk("Y2 出 ⇒ 282", B["Y2out"], [282]); chk("Y2 進 ⇒ 無", B["Y2in"], [])
    # Y3：d＝280 爆量 3 倍長黑；281、282 量遞減不破低；283 帶量站回 MA5
    o, h, l, c, v = flat()
    o[280], c[280], h[280], l[280], v[280] = 100, 95, 100.2, 94.5, 3500
    o[281], c[281], h[281], l[281], v[281] = 95, 95.2, 95.5, 94.8, 2000
    o[282], c[282], h[282], l[282], v[282] = 95.2, 95.3, 95.6, 94.9, 1500
    o[283], c[283], h[283], l[283], v[283] = 95.5, 100, 100.2, 95.4, 1200
    B, _ = detect(o, h, l, c, v); chk("Y3 ⇒ 283", B["Y3"], [283])
    v[283] = 1000 * 0.9 * 0 + 900                                    # 量 ＜ 20 日均量 ⇒ 不是「帶量」；且 283 量 ＜ 282 ⇒ 延一根試 284（284 沒站回）
    B, _ = detect(o, h, l, c, v); chk("Y3 帶量不足 ⇒ 無", B["Y3"], [])
    # 均線跌破：由上往下穿越才算
    c = np.r_[np.full(30, 100.0), np.full(5, 90.0), np.full(5, 95.0)]; o = c.copy(); h = c * 1.001; l = c * 0.999; v = np.full(len(c), 1000.0)
    B, _ = detect(o, h, l, c, v); chk("MA10 跌破只在第一根 ⇒ 30", B["MA10"], [30])
    # Y4：買價 100；收盤 105、112（曾 ≥10%）、99 ⇒ 99 那天出（收 ＜ 買價）
    cc = np.array([np.nan, 105, 112, 108, 99, 98.0]); bi = np.arange(1, 6); xb = np.zeros(6, bool)
    chk("Y4 過 +10% 後跌破買價 ⇒ 4", [y4_day(cc, bi, 100.0, xb)], [4])
    cc = np.array([np.nan, 105, 126, 120, 118, 99.0]); xb = np.zeros(6, bool); xb[3] = True
    chk("Y4 過 +25% 後改看跌破 MA ⇒ 3（不看買價）", [y4_day(cc, bi, 100.0, xb)], [3])
    cc = np.array([np.nan, 105, 109.9, 99, 98, 97.0]); xb = np.zeros(6, bool)
    chk("Y4 沒到 +10% ⇒ 不出", [y4_day(cc, bi, 100.0, xb)], [-1])
    # vma 不含當根
    vv = np.arange(1, 31, dtype=float); vm_ = vma(vv, 20)
    chk("vma(20) 在第 20 根 ＝ 1～20 的平均 10.5 ⇒ ×2＝21", [vm_[20] * 2], [21])
    allok = all(ok)
    print(f"selftest {'全過' if allok else '⛔ 有不過'}（{sum(ok)}／{len(ok)}）")
    return allok, sum(ok), len(ok)


# ═════════════════════════════ 主程式
def setup(a, log, mode):
    cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
    P = {k: (int(cal.searchsorted(pd.Timestamp(v[0]))), int(cal.searchsorted(pd.Timestamp(v[1])))) for k, v in SEG.items()}
    for k, (x0, x1) in P.items():
        assert str(cal[x0].date()) == SEG[k][0] and str(cal[x1].date()) == SEG[k][1]
    assert P["主窗"][1] - P["主窗"][0] + 1 == MAIN_DAYS and P["主窗"][1] + 1 < ncal
    sids, elig, mk = SG.stock_universe(cal, PANEL, os.path.join(H2.H2D, "meta", "stocks.csv"))
    FUND, fst = load_fund(cal, log)
    init = {"cal": cal, "mode": mode, "FUND": FUND}
    if mode == "body":
        from backtest import p4_features as P4F
        p = P4F.read_panel(PANEL); U = set(sids)
        p = p[p["eligible"].astype(bool) & p["stock_id"].isin(U)]
        pos = {d: i for i, d in enumerate(cal)}
        MEAS = {}
        for s, g in p.groupby("stock_id"):
            MEAS[s] = sorted(int(pos[pd.Timestamp(d)]) for d in g["measure_date"] if pd.Timestamp(d) in pos)
        init.update(w0=P["主窗"][0], w1=P["主窗"][1], mon=mon, elig=elig, off=TR.load_official(), MEAS=MEAS, P=P)
    t0 = time.time(); SIG = {}
    with Pool(a.procs, initializer=_init, initargs=(init,)) as pool:
        for i, r in enumerate(pool.imap_unordered(stock_work, [(s, mk.get(s, "twse")) for s in sids], chunksize=4)):
            if r is not None:
                SIG[r["sid"]] = r
            if (i + 1) % 500 == 0:
                log(f"  [每檔 {mode}] {i + 1}/{len(sids)}｜{time.time() - t0:.0f}s")
    log(f"[每檔 {mode}] {len(SIG)} 檔｜{time.time() - t0:.0f}s")
    return cal, ncal, mon, P, sids, elig, mk, FUND, fst, SIG


def sig_digest(SIG):
    h = hashlib.sha256()
    for sid in sorted(SIG):
        for k in sorted(SIG[sid]["S"]):
            h.update(f"{sid}|{k}|".encode()); h.update(np.asarray(SIG[sid]["S"][k], np.int64).tobytes())
    return h.hexdigest()[:16]


def pre_counts(SIG, elig, mon, P, ncal, cz=None):
    """每格事件數（主窗）、探索段段尾未出場比例、同日不進；出場格的主窗有效觸發（Y4 需要進場價 ⇒ 用 cz／oz 的引擎進場價）。"""
    rows = []
    for code in ENTRIES:
        for xo in EXOPT:
            rec = {"格": f"{code}|{xo}", "顆": code[:2], "角色": "進"}
            for seg in ("探索", "確認", "主窗"):
                R, drop = entry_rows(SIG, elig, mon, code, xo, *P[seg])
                rec[f"{seg}_列"] = int(len(R)); rec[f"{seg}_訊號日同時跌破（照進）"] = drop
                rec[f"{seg}_段尾未出場列"] = int((R["dX"] < 0).sum()) if len(R) else 0
                rec[f"{seg}_出場觸發列"] = int((R["dX"] >= 0).sum()) if len(R) else 0
            rec["主窗事件"] = rec["主窗_列"]; rec["年均事件"] = rec["主窗_列"] / YEARS_MAIN
            rec["探索_段尾未出場比例"] = rec["探索_段尾未出場列"] / max(1, rec["探索_列"])
            rows.append(rec)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["selftest", "pre", "body", "early", "report"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--fake", type=int, default=1000)
    a = ap.parse_args()
    if a.mode == "selftest":
        ok, _, _ = selftest(); sys.exit(0 if ok else 1)
    os.makedirs(OUT, exist_ok=True)
    if a.mode == "report":
        import researchExtAuth_report as REP
        REP.main(); return
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("researchExtAuth.py", "researchSig.py", "researchRev.py", "research11.py", "avgdown.py", "research34.py")}
    log(f"===== researchExtAuth {a.mode} procs={a.procs} reps={a.reps} fake={a.fake} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    log(f"[程式 sha256] {src}")
    ok, n_ok, n_all = selftest()
    if not ok:
        raise SystemExit("⛔ selftest 不過")
    if a.mode == "early":
        import researchExtAuth_early as EA
        EA.run(a, log); return
    SP = os.path.join(OUT, "summary.json")
    S = json.load(open(SP, encoding="utf-8")) if os.path.exists(SP) else {}
    S.update({"登錄": "PREREG外部作者 seq1 sha 62e4026f16879fed；裁定 seq248／249／252；N ＋7", "性質": TAG, "程式": src,
              "selftest": f"{n_ok}/{n_all}", "W2 標註": A2TAG,
              "面板": {"路徑": PANEL, "sha256": SG.sha16(PANEL)}, "財報": f"fin_hist {FIN_SHA}（~/msdata，唯讀）"})
    cal, ncal, mon, P, sids, elig, mk, FUND, fst, SIG = setup(a, log, "pre" if a.mode == "pre" else "body")
    S["基本面"] = fst
    dg = sig_digest(SIG)
    w2 = {"候選 (s, r)": sum(x["w2_cand"] for x in SIG.values()), "過基本面": sum(x["w2_pass"] for x in SIG.values())}
    srcs = {}
    for x in SIG.values():
        for k, v in x["w2src"].items():
            srcs[k] = srcs.get(k, 0) + v
    w2["過基本面的來源"] = srcs
    if a.mode == "pre":
        C = pre_counts(SIG, elig, mon, P, ncal)
        # 出場格事件：基準列 × H × 出場（Y4 需要引擎進場價 ⇒ 讀價）
        RR.use_snapshot()
        allsid = sorted(SIG)
        cz, oz = RR.load_prices(allsid, cal, mk, "branch")
        OV = []
        for seg in ("探索", "確認", "主窗"):
            s0, s1 = P[seg]
            R = base_rows(SIG, elig, mon, s0, s1).reset_index(drop=True)
            ep = np.array([L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])])
            for H in HB:
                for code in OVERS:
                    xp, d = overlay_days(R, SIG, code, H, s1, ep, ncal)
                    OV.append({"段": seg, "格": f"{code}|H{H}", "基準列": int(len(R)), "有效觸發列": int((d >= 0).sum()),
                               "段尾未出場列": int(((xp == s1 + 1) & (d < 0)).sum())})
        OVd = pd.DataFrame(OV)
        exc = {}
        for r in C:
            bad = []
            if r["主窗事件"] < 200:
                bad.append("主窗事件 ＜ 200")
            if r["年均事件"] < 10:
                bad.append("年均 ＜ 10")
            if r["探索_段尾未出場比例"] > 0.5:
                bad.append("探索段段尾未出場 ＞ 50%")
            exc[r["格"]] = bad
        for r in OVd[OVd["段"] == "主窗"].itertuples():
            bad = []
            if r.有效觸發列 < 200:
                bad.append("主窗有效觸發 ＜ 200")
            if r.有效觸發列 / YEARS_MAIN < 10:
                bad.append("年均 ＜ 10")
            ex_ = OVd[(OVd["段"] == "探索") & (OVd["格"] == r.格)].iloc[0]
            if ex_["段尾未出場列"] / max(1, ex_["基準列"]) > 0.5:
                bad.append("探索段段尾未出場 ＞ 50%")
            exc[r.格] = bad
        pre = {"訊號 digest": dg, "W2": w2, "進場格": C, "出場格": OV, "剔除": exc,
               "訊號總數（全母體、不分資格、全日曆）": {k: int(sum(len(x["S"][k]) for x in SIG.values())) for k in ENTRIES + ["Y2out", "Y5", "MA10", "MA20", "MA60"]},
               "Y1 突破日": int(sum(len(x["S"]["Y1b"]) for x in SIG.values())), "Y1 有回踩": int(sum(int((x["S"]["Y1b"][:, 1] >= 0).sum()) for x in SIG.values() if len(x["S"]["Y1b"])))}
        json.dump(pre, open(os.path.join(OUT, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=int)
        S["pre"] = {"完成": time.strftime("%F %T"), "訊號 digest": dg, "剔除": {k: v for k, v in exc.items() if v}}
        json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        for r in C:
            log(f"  [進] {r['格']}：主窗 {r['主窗事件']:,}（年均 {r['年均事件']:.1f}）｜探索 {r['探索_列']:,}、段尾未出場 {r['探索_段尾未出場比例']:.1%}｜確認 {r['確認_列']:,}｜{exc[r['格']] or '—'}")
        for r in OVd[OVd["段"] == "主窗"].itertuples():
            log(f"  [出] {r.格}：主窗基準 {r.基準列:,}、有效觸發 {r.有效觸發列:,}（年均 {r.有效觸發列 / YEARS_MAIN:.1f}）｜{exc[r.格] or '—'}")
        log(f"[W2] {w2}｜[pre 完成] digest {dg}｜{time.time() - t00:.0f}s")
        return
    # ═══════════════ body
    pre = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    if pre["訊號 digest"] != dg:
        raise SystemExit(f"⛔ 閘：body 重算的訊號 digest {dg} ≠ pre {pre['訊號 digest']}")
    log(f"[閘] 訊號 digest 與 pre 相同 {dg}")
    exc = pre["剔除"]
    RR.use_snapshot()
    allsid = sorted(SIG)
    cz, oz = RR.load_prices(allsid, cal, mk, "branch")
    bench = RR.load_bench(cal)
    B50 = {seg: RR.bench_row(cal, bench, s0, s1 + 1) for seg, (s0, s1) in P.items()}
    assert abs(B50["主窗"]["cagr"] - 0.24020209886370614) < 1e-12 and abs(B50["主窗"]["mdd"] + 0.3395700527611012) < 1e-12, B50["主窗"]
    S["0050同段"] = B50
    CELLS = {}
    SG._G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS)
    OUTC = {}; ROWS = {}

    def mk_entry(seg, code, xo):
        s0, s1 = P[seg]
        R, drop = entry_rows(SIG, elig, mon, code, xo, s0, s1); R = R.reset_index(drop=True)
        SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
        sig, kw, reason = SG.make_cell(R, SD, s1, "無", "無", cz, oz)
        k = (seg, code, xo); CELLS[k] = (sig, kw, reason, None); ROWS[k] = (R, SD["ep"].to_numpy(float), np.full(len(R), s1 + 1))
        return k

    BASE = {}

    def mk_over(seg, code, H):
        s0, s1 = P[seg]
        if seg not in BASE:
            R = base_rows(SIG, elig, mon, s0, s1).reset_index(drop=True)
            ep = np.array([L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])])
            BASE[seg] = (R, ep)
        R, ep = BASE[seg]
        xp, d = overlay_days(R, SIG, None if code == "BASE" else code, H, s1, ep, ncal)
        sig, kw, reason = make_fixed(R, xp, d, ep, cz, code)
        k = (seg, code, f"H{H}"); CELLS[k] = (sig, kw, reason, None); ROWS[k] = (R, ep, xp)
        return k

    # ── 探索段：全部格（剔除的也跑、只描述）
    keys = [mk_entry("探索", c_, x_) for c_ in ENTRIES for x_ in EXOPT]
    keys += [mk_over("探索", c_, H) for c_ in OVERS + ["BASE"] for H in HB]
    res = run_cells(keys, *P["探索"], a.reps, a.procs, "探索段 全部格", log)
    for k in keys:
        OUTC[k] = agg2(res[k], B50["探索"])
    # ── 挑格（每顆 1 格）
    def cell_name(k):
        return f"{k[1]}|{k[2]}"
    groups = {"W1": [("W1", x) for x in EXOPT], "W2": [("W2", x) for x in EXOPT], "Y1": [("Y1", x) for x in EXOPT],
              "Y2": [("Y2in", x) for x in EXOPT] + [("Y2out", f"H{H}") for H in HB], "Y3": [("Y3", x) for x in EXOPT],
              "Y4": [(c_, f"H{H}") for c_ in ("Y4_MA5", "Y4_MA10") for H in HB], "Y5": [("Y5", f"H{H}") for H in HB]}
    chosen = {}; cand_info = {}
    for g, lst in groups.items():
        cands = [(("探索",) + x, OUTC[("探索",) + x]) for x in lst if not exc.get(f"{x[0]}|{x[1]}")]
        cand_info[g] = {"候選": [f"{x[0]}|{x[1]}" for x in lst], "剔除": {f"{x[0]}|{x[1]}": exc.get(f"{x[0]}|{x[1]}") for x in lst if exc.get(f"{x[0]}|{x[1]}")}}
        chosen[g] = SG.pick(cands) if cands else None
    S["探索段挑格"] = {g: (cell_name(k) if k else "依構造不可判定（全部格被剔除）") for g, k in chosen.items()}; S["挑格候選"] = cand_info
    log(f"[挑格] {S['探索段挑格']}")
    S["探索段完成"] = time.strftime("%F %T")
    # ── 確認段、主窗（⛔ 上面挑完才算）
    JUD = {}
    for seg in ("確認", "主窗"):
        keys = []
        for g, k in chosen.items():
            if k is None:
                continue
            _, c_, x_ = k
            if c_ in ENTRIES:
                keys.append(mk_entry(seg, c_, x_))
            else:
                H = int(x_[1:]); keys.append(mk_over(seg, c_, H)); keys.append(mk_over(seg, "BASE", H))
        keys = list(dict.fromkeys(keys))
        res = run_cells(keys, *P[seg], a.reps, a.procs, f"{seg} 判定格", log)
        for k in keys:
            OUTC[k] = agg2(res[k], B50[seg])
    for g, k in chosen.items():
        if k is None:
            JUD[g] = {"判定": "依構造不可判定"}; continue
        _, c_, x_ = k
        cf, mw = OUTC[("確認", c_, x_)], OUTC[("主窗", c_, x_)]
        lc, lm = cf["label"], mw["label"]
        if lc == "合格" and lm == "合格":
            fin_ = "合格"
        elif lc == "合格":
            fin_ = "確認段合格、全段未過"
        elif lc == "另列" and lm in ("合格", "另列"):
            fin_ = "另列"
        elif lc == "另列":
            fin_ = "確認段另列、全段未過"
        else:
            fin_ = "不合格"
        J = {"格": f"{c_}|{x_}", "確認": {kk: cf[kk] for kk in ("cagr_med", "mdd_med", "ratio", "label")},
             "主窗": {kk: mw[kk] for kk in ("cagr_med", "mdd_med", "ratio", "label")}, "判定": fin_}
        if c_ in OVERS:
            for seg in ("確認", "主窗"):
                b = OUTC[(seg, "BASE", x_)]; o_ = OUTC[(seg, c_, x_)]
                J[f"{seg}_加減不加"] = {"年化差（點）": (o_["cagr_med"] - b["cagr_med"]) * 100, "回落差（點）": (o_["mdd_med"] - b["mdd_med"]) * 100,
                                     "不加_年化": b["cagr_med"], "不加_回落": b["mdd_med"]}
        JUD[g] = J
    log(f"[判定] {json.dumps({g: j['判定'] for g, j in JUD.items()}, ensure_ascii=False)}")
    # ── 對照：固定持有（進場顆）、假訊號（全部判定格）
    FIX = {}
    for seg in ("探索", "確認"):
        keys = []
        s0, s1 = P[seg]
        for g, k in chosen.items():
            if k is None or k[1] not in ENTRIES:
                continue
            R, ep, _ = ROWS[(seg, k[1], k[2])] if (seg, k[1], k[2]) in ROWS else ROWS[mk_entry(seg, k[1], k[2])]
            for H in HB:
                xp = np.minimum(R["entry_pos"].to_numpy(int) + H - 1, s1 + 1)
                sig, kw, reason = make_fixed(R, xp, np.full(len(R), -1), ep, cz, f"H{H}")
                kk = (seg, k[1], f"固定H{H}"); CELLS[kk] = (sig, kw, reason, None); keys.append(kk)
        keys = list(dict.fromkeys(keys))
        res = run_cells(keys, s0, s1, a.reps, a.procs, f"{seg} 固定持有對照", log)
        for kk in keys:
            OUTC[kk] = agg2(res[kk], B50[seg])
    FAKE = {}
    s0, s1 = P["確認"]
    for g, k in chosen.items():
        if k is None:
            continue
        kk = ("確認", k[1], k[2]); R, ep, xp = ROWS[kk]
        SG._G["FAKEJOB"] = {"R": R, "xp": np.asarray(xp, int), "s0": s0, "s1": s1, "hold": OUTC[kk]["_hold_pool"], "ep": ep}
        t0 = time.time()
        with Pool(a.procs) as pool:
            fk = pool.map(fake_one, range(a.fake), chunksize=8)
        fc = np.array([x[0] for x in fk]); m = OUTC[kk]["cagr_med"]
        FAKE[g] = {"中位年化": float(np.median(fc)), "p10": float(np.percentile(fc, 10)), "p90": float(np.percentile(fc, 90)),
                   "p（隨機 ≥ 本格）": float((fc >= m).mean()), "本格贏過的比例": float((m > fc).mean()), "次數": a.fake,
                   "持有天數池": int(len(OUTC[kk]["_hold_pool"])), "贏0050同段比例": float((fc > B50["確認"]["cagr"]).mean())}
        log(f"  [假訊號 {g}] {a.fake} 次｜p＝{FAKE[g]['p（隨機 ≥ 本格）']:.3f}｜{time.time() - t0:.0f}s")
    S["判定"] = JUD; S["假訊號"] = FAKE
    # ── 「收盤 ＜ MA 即賣」描述（進場判定格、確認段）
    DESC = {}
    keys = []
    s0, s1 = P["確認"]
    for g, k in chosen.items():
        if k is None or k[1] not in ENTRIES:
            continue
        xo = "BL" + k[2][2:]
        R, drop = entry_rows(SIG, elig, mon, k[1], xo, s0, s1); R = R.reset_index(drop=True)
        SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
        sig, kw, reason = SG.make_cell(R, SD, s1, "無", "無", cz, oz)
        kk = ("確認", k[1], xo); CELLS[kk] = (sig, kw, reason, None); keys.append(kk)
        DESC[g] = {"訊號日收盤已 ＜ MA（照進）": drop}
    if keys:
        res = run_cells(keys, s0, s1, a.reps, a.procs, "確認段 收盤＜MA 即賣（描述）", log)
        for kk in keys:
            OUTC[kk] = agg2(res[kk], B50["確認"])
    # 進場時已在線下（跌破式要先站上才可能賣）的列數
    for g, k in chosen.items():
        if k is None or k[1] not in ENTRIES:
            continue
        R, ep, _ = ROWS[("確認", k[1], k[2])]
        n_ = int(k[2][2:]); below_at_e = 0; never = 0; BLs = {}
        for sid, t, dX in zip(R["sid"], R["t"].to_numpy(int), R["dX"].to_numpy(int)):
            bl = BLs.get(sid)
            if bl is None:
                bl = BLs[sid] = set(SIG[sid]["S"][f"BL{n_}"].tolist())
            if int(t) in bl:
                below_at_e += 1
                never += int(dX < 0)
        DESC.setdefault(g, {}).update({"訊號日收盤已在 MA 下的列": below_at_e, "其中到段尾都沒出場": never, "列": int(len(R))})
    S["描述_收盤低於MA即賣"] = DESC
    # ── 單筆層
    ev = pd.DataFrame([r for x in SIG.values() for r in x.get("ev", [])])
    ev.to_csv(os.path.join(OUT, "se_events.csv.gz"), index=False, float_format="%.17g")
    DD = pd.read_csv(WIN_DAYS_FILE, dtype={"sid": str})
    DD["m"] = mon[DD["d"].to_numpy()]
    key = {(s, int(d)): int(q) for s, d, q in zip(DD["sid"], DD["d"], DD["dec"])}
    SE = []
    for H in HS:
        f = DD[np.isfinite(DD[f"R{H}"]) & (DD["dec"] >= 0)]
        B2 = f.groupby(["m", "dec"])[f"R{H}"].mean()
        sp = f.assign(x=f[f"R{H}"] > 0).groupby(["m", "dec"])["x"].mean(); sn = f.assign(x=f[f"R{H}"] < 0).groupby(["m", "dec"])["x"].mean()
        e = ev[(ev["H"] == H) & (ev["st"] == "保留")] if len(ev) else ev
        for code in SE_CODES:
            k_ = e[e["code"] == code] if len(e) else e
            bear = code in SE_BEAR
            T = k_["T"].to_numpy(int) if len(k_) else np.zeros(0, int); Rr = k_["R"].to_numpy(float) if len(k_) else np.zeros(0)
            mm = mon[T] if len(T) else np.zeros(0, str)
            q = [key.get((s, int(d)), -1) for s, d in zip(k_["sid"], T)] if len(k_) else []
            b2 = np.array([B2.get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
            bs = np.array([(sn if bear else sp).get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
            okm = np.isfinite(b2)
            st_ = se_stats(Rr[okm] - b2[okm], mm[okm], bear)
            cand = int(((ev["H"] == H) & (ev["code"] == code)).sum()) if len(ev) else 0
            SE.append({"code": code, "名": NAME[code], "方向": "看跌" if bear else "看漲", "H": H, "候選（合併後）": cand, "保留": int(len(k_)),
                       "基準2缺": int((~okm).sum()), "R平均": float(Rr[okm].mean()) if okm.any() else np.nan,
                       "基準R平均": float(b2[okm].mean()) if okm.any() else np.nan,
                       "成功率": float(((Rr[okm] < 0) if bear else (Rr[okm] > 0)).mean()) if okm.any() else np.nan,
                       "基準成功率": float(bs[okm].mean()) if okm.any() else np.nan, **st_})
    SEc = pd.DataFrame(SE)
    stab = stability(SEc); SEc["穩不穩"] = SEc["code"].map(stab)
    SEc.to_csv(os.path.join(OUT, "se_cells.csv"), index=False)
    y1 = pd.DataFrame([r for x in SIG.values() for r in x.get("y1ab", [])])
    y1.to_csv(os.path.join(OUT, "y1_abandon.csv.gz"), index=False, float_format="%.17g")
    S["Y1放棄組"] = {"突破日（主窗、eligible）": int(len(y1)), "有回踩": int((y1["r"] >= 0).sum()) if len(y1) else 0,
                  "沒回踩_突破次日買20日報酬平均": float(y1.loc[y1["r"] < 0, "R20_b"].mean()) if len(y1) else np.nan,
                  "有回踩_突破次日買20日報酬平均": float(y1.loc[y1["r"] >= 0, "R20_b"].mean()) if len(y1) else np.nan,
                  "有回踩_回踩次日買20日報酬平均": float(y1.loc[y1["r"] >= 0, "R20_r"].mean()) if len(y1) else np.nan}
    # ── 全市場基準（四類單獨口徑）描述
    Q = pd.DataFrame([r for x in SIG.values() for r in x.get("quad", [])])
    Q.to_csv(os.path.join(OUT, "quad_trades.csv.gz"), index=False, float_format="%.17g")
    QD = []
    k_ok = Q[Q["st"] == "保留"]
    for seg in ("探索", "確認"):
        for H in HB:
            qq = k_ok[(k_ok["seg"] == seg) & (k_ok["H"] == H)]
            mm = mon[qq["e"].to_numpy(int) - 1]
            for code in OVERS:
                x = qq[f"d_{code}"].to_numpy(float)
                m_, se_, ng = AV.cr0(x, mm) if len(x) else (np.nan, np.nan, 0)
                QD.append({"段": seg, "H": H, "出場": code, "筆": int(len(x)), "觸發比例": float(qq[f"t_{code}"].mean()) if len(qq) else np.nan,
                           "差平均": m_, "CI低": m_ - 1.96 * se_, "CI高": m_ + 1.96 * se_, "月數": int(ng),
                           "觸發筆差平均": float(x[qq[f"t_{code}"].to_numpy(int) == 1].mean()) if (qq[f"t_{code}"] == 1).any() else np.nan})
    pd.DataFrame(QD).to_csv(os.path.join(OUT, "quad_cells.csv"), index=False)
    S["全市場基準_剔除"] = Q["st"].value_counts().to_dict() if len(Q) else {}
    # ── 輸出
    rows = []
    for k, c in OUTC.items():
        rows.append({"段": k[0], "顆": k[1], "出場／H": k[2], "剔除": "；".join(exc.get(f"{k[1]}|{k[2]}", []) or []),
                     **{kk: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for kk, v in c.items() if not kk.startswith("_")}})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "cells.csv"), index=False)
    aud = []
    for g, k in chosen.items():
        if k is None:
            continue
        kk = ("確認", k[1], k[2]); sig_, kw_, _, _ = CELLS[kk]
        for r in range(3):
            au = []
            o = R11.simulate_mtm(sig_, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, audit=au, **kw_)
            c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], *P["確認"])
            aud.append({"cell": "|".join(kk), "r": r, "cagr": c_, "mdd": m_, "n_audit": len(au),
                        "sha": hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest()[:16]})
        R, ep, xp = ROWS[kk]
        R.assign(ep=ep, xpos=xp, trig=[CELLS[kk][2].get((s, int(e)), ("", -1))[1] for s, e in zip(R["sid"], R["entry_pos"])]).to_csv(
            os.path.join(OUT, f"confirm_rows_{g}.csv.gz"), index=False, float_format="%.17g")
    pd.DataFrame(aud).to_csv(os.path.join(OUT, "confirm_audit3.csv"), index=False)
    S["W2"] = w2; S["body完成"] = time.strftime("%F %T"); S["秒_body"] = round(time.time() - t00)
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[body 完成] {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
