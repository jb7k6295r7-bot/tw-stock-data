# -*- coding: utf-8 -*-
"""Williams %R 當「KD 的未平滑版」seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 92d0b5b84554d22e，2026-10-18 11:08；
裁定 seq369 §二、seq372 發號；N_前段 ＋1）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsWR/freq/ ⛔ 不碰）；researchWR_freq（事件偵測、剔除、%R、KD、週線）、researchAscTri_freq（世界）、
   researchPatC（PatAll 同式小工具：decile_int、dec_matrix、excl_past、verdict、agg_eval、clkey、diff_stats、desc_ci）、research11 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWR [--procs 2] [--dry]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWR_check
    --dry ＝ 不含報酬的乾跑（所有 R 一律寫成 0、只留「可不可算」；輸出到 scratch 夾；只驗流程與件數）
輸出 backtest/resultsWR/（⛔ 不碰 freq/）：WR.json、WR_main.csv（判定表＋分報）、WR_diff.csv（W − K）、WR_desc.csv（描述格）、
    WR_week.csv（週線版描述）、by_year.csv、fake_reps.csv、fake_acc.npz、events/trades_<世界>_<段>_<格>_H<H>.csv.gz、run.log

格：W ＝ 判定格（日線 %R(14) 由 ＜−80 回到 ≥−80，H20 判、H60 描述）；K ＝ 對照格（日線 KD(9,3,3) 低檔金叉，同法報結果、⛔ 不判、不計 N）；
    W − K 差（描述、報 CI）；描述：W∩K 同日、W 獨有、K 獨有、上市／上櫃、逐年、未配對；週線版 週_W／週_K（4／8／12／26 週，只描述）。

═══ 讀法（V 標；頻率表 R1～R11 原樣沿用（世界、母體、壞根、%R、KD、偵測、合併、剔除、段）；方法 ＝ PREREG型態全量 seq3 事件層
     （researchPatAll C1～C8；落地沿用 AT 世界版 researchPatC P1～P10）；⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法、⛔ 不另跑）═══
 V1 事件 ＝ 逐股呼叫 researchWR_freq.stock_job 原樣；⭐ 依 run_freq 的寫法排成 events_<世界>.csv.gz 的全文，與已提交檔【逐字】比，
    任一不同 ⇒ 中止、⛔ 不算報酬。判定母體 ＝ 狀態「保留」者（W、K 各自；20 日內只算第一次 ⇒ H20 持有不重疊，頻率表 R8）。
 V2 R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1（PatAll C1；T＋H 無成交 ⇒ ≤ T＋H 最後一根有效 K 棒收盤；下市者 ＝ 最後成交價）。
    還原開高低收 ＝ load_bars 的 B["o"/"c"]（頻率表 %R 用的同一組）放回日曆。成本兩邊相同、相減抵銷 ⇒ X ⛔ 不扣；
    「扣成本 0.585% 另報」＝ X̄ − 0.585%（evaluate.COST；PatC P2 同口徑）與 R̄ − 0.585%（每筆淨報酬）兩欄。
 V3 對照（登錄 §三）：同一天 T、r20 同一十分位、當天沒出現該訊號的股票等權。
    ★ r20 ＝ c[b] ÷ c[b−20] − 1（b ＝ 該股 T 那根有效 K 棒；含 T 當天收盤 ⇒ 決策時點已知的前 20 根走勢；PatAll K 棒對照同時配
      「型態前 r10 ＋ 型態期間報酬」⇒ 單根訊號含當根）〔另一讀法：c[b−1] ÷ c[b−21] − 1、不含 T〕；
      不跨壞根：(b−20, b] 內有壞 K 棒 ⇒ r20 缺值（事件 ⇒ 剔除並計數「r20 不可算」）。
    ★ 十分位橫斷面 ＝ T 當天 母體（Frame.gate ∧ pit_valid，頻率表 R1）∧ T 有有效 K 棒 ∧ r20 可算；rank(method="first") 等分 10
      （PatAll decile_int；橫斷面 ＜ 10 檔 ⇒ 無十分位 ⇒ 剔除並計數）〔另一讀法：只用可當對照者＋事件本身切〕。
    對照股 ＝ 同十分位 ∧ T 當天母體 ∧ ★ T＋1 可買（頻率表 R7 同旗標：下一根有效 K 棒 ＝ 日曆 T＋1、非壞 K 棒、有成交、開盤非缺且 ＞ 0、
      非開盤鎖漲停；⛔ 不另剔開盤跌停，與事件同〔另一讀法：PatC 另剔跌停〕）∧ 持有期無硬斷點（同 V4）∧ R 可算 ∧ ★ T 當天【原始】偵測
      沒有該格（W 對照扣 W 的原始偵測、K 對照扣 K 的；原始 ＝ 頻率表事件檔任何狀態，含「合併掉」；PatC P3 同）∧ 不是自己 ⇒ 等權平均。
      配對格當天沒有對照股 ⇒ 剔除並計數（PatAll C4）。
 V4 硬斷點（事件、對照同式；PatC P3 brk）：(T, T＋H] 內有壞 K 棒（頻率表 R1 壞根：缺口 ≥ 5 日 seq335、價格斷點、幽靈還原、crashwork、
    早年 reduce_v2），或 T＋H 落在 ≥ 5 日缺口中（之前最後一根到 T＋H 已缺 ≥ 5 日且之後還有成交）⇒ 不可用（事件剔除並計數「持有期壞根」）。
    r20 的窗 (b−20, b] 已在 V3 要求無壞 K 棒 ⇒ 合起來 ＝ [b−20, T＋H] 無斷點。T＋H 超出資料尾 ⇒ 剔除並計數「T＋H 超出資料尾」。
 V5 未配對描述：EW_H(T) ＝ T 當天母體 ∧ T＋1 可買 ∧ R 可算的全部股票 R 等權；X_u ＝ R − EW。
 V6 判定量 ＝ X̄（d ＝ ＋1）。CI：H20 ＝ T 所在曆月分群（登錄 §三）、★ H60（描述）＝ (T − 段起點)//60 分群（PatAll C6）〔另一讀法：H60 也曆月〕；
    CR0（research11.cl_stats）、1.96；非重疊 SE（第二欄）＝ 20／60 日區段平均的標準差 ÷ √區段數。n_eff ＝ min(配對後事件數, 有事件的分群數)；
    ＜30 ⇒ 樣本不足以分辨、30～99 ⇒ 出口②（句首「樣本中等」）、≥100 ⇒ 出口③；結果② ＝ CI 不含 0 且 ＞0、③ ＝ 不含 0 且 ＜0、① ＝ 含 0
    （PatAll §七）。Bonferroni 族 ＝ 本登錄判定格 N ＝ 1 ⇒ z ＝ 1.96（與 95% 同；另欄照印）。
 V7 段（登錄 §三「各自報」）：判定 ＝ 【探索】、【確認】各自照 V6 判（兩段各一個結果；⛔ 不合併成一個）；主全窗 同法並報【參考】；
    早年 只描述（附 reduce_v2「早年含減資假飆股約 0.3%」註）。段界 ＝ 頻率表 R10（T 的日曆位置；主的段尾 ＝ 資料尾前一日）。
 V8 假訊號臂（登錄 §八 ＝ PatAll C8、PatC P7 同式）：r ＝ 0…29；每檔、每格（W、K）、每段（H20）：n ＝ 該檔該段【保留】事件數；
    可抽日 ＝ 該檔有效 K 棒、T ∈ [段起點, min(段尾, 資料尾 − H)]、★ r20 可算 ∧ T 當天母體（Frame.gate ∧ pit_valid）（PatAll C8 ★ 同理：
    假日子要求配對量可算；乾跑見 500 張閘在抽後剔會少掉約 32% 假事件、運氣基準偏低 ⇒ 改當可抽條件；看報酬前定）
    〔另一讀法：PatC P7 抽後再剔 pit〕；
    新預設 ＝ 排除「存在該格保留真事件 T_r ∈ [T − 20, T]」的日子；不排除版並列描述；不放回抽 n 天（不足 ⇒ 全取、另報）；⛔ 不合併。
    之後同一套剔除（持有期斷點／T＋1 不可買／R 不可算 → 無十分位 → 配對格無對照股；計數、⛔ 不補抽）、同一套對照
    （V3；假事件自己若在對照池 ⇒ 從它自己的對照裡扣掉）、同分群、同判定式。種子 default_rng([20261018＋r, crc32(sid), 格序號, 段序號, 版本])；
    格序號 W＝0、K＝1；段序號 探索＝0、確認＝1、主全窗＝2、早年＝3。x／30 ＝ 落結果② 的次數；結果② 且 x ≥ 2 ⇒ 句首「⚠ 隨機挑日子也有 x／30 次同樣過關。」
 V9 seq322 門檻（UO E9 同式）＝ 該段結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；
    五條全過才另起組合層登錄（登錄「性質」）。探索、確認各報（主全窗參考）；只有 W 判，K 照印、⛔ 不判。
 V10 W − K 差（登錄 §三「差：W − K（同段、同法；描述，報 CI）」）：差 ＝ X̄(W) − X̄(K)，兩組各自用自己的配對後事件與對照。
    ⭐ 重疊處理：W 與 K 同檔同日約 15%（÷W）～23%（÷K）（頻率表），兩組不獨立 ⇒ SE ＝ 曆月分群線性化（PatC P8 diff_stats 同式）：
    每個曆月 g 算 d_g ＝ Σ_{i∈W,g}(x_i − x̄_W)/n_W − Σ_{j∈K,g}(y_j − ȳ_K)/n_K，SE ＝ √Σ_g d_g²。這是兩個平均之差的分群穩健（CR0）變異數，
    允許同一個月內任意相關——同檔同日的重疊事件必在同月、X 幾乎相同（同 T、同 r20 十分位，對照池只差扣掉的原始偵測）⇒ 在 d_g 裡互相抵銷，
    不會被當成兩筆獨立樣本；跨月相關不處理（與主 CI 同限制）。〔另一讀法：把兩組當獨立樣本、SE ＝ √(se_W² ＋ se_K²)——重疊時高估 SE，只並印一欄參考〕
    另描述拆解：W∩K 同日、W 獨有（W ∖ K）、K 獨有（K ∖ W）三組各自 X̄（各用自己格的對照）。差 ⛔ 不判、不計 N；先驗③ ＝ 差的 CI 含 0。
 V11 週線版（只描述；登錄 §一「%R(14 週) 對週 KD S1、同 4～26 週持有」＝ researchWeekly 甲 A3／A5 的框架原樣）：事件 ＝ 頻率表 週_W／週_K 保留者
    （T ＝ 該股該週最後一根有效 K 棒、進場 ＝ 下一個日曆週第一個交易日開盤）；k ∈ {4, 8, 12, 26}：R_k ＝ c_ff[第 w＋k 週最後一個交易日]
    ÷ 還原開盤[第 w＋1 週第一個交易日] − 1（A3）；★ 第 w＋k 週須完整在資料內（第 w＋k＋1 週存在）；斷點：(第 w−4 週最後一日, 第 w＋k 週最後一日]
    有壞 K 棒或終點落在 ≥ 5 日缺口 ⇒ 不可算。對照（A5 基準②）＝ 同週、母體（該股該週最後一根有效 K 棒那天 Frame.gate ∧ pit_valid）、
    前 4 週報酬（c_ff[wl[w]] ÷ c_ff[wl[w−4]] − 1）同十分位、進場日可買、R_k 可算、無斷點、★ 當週事件檔沒有該格事件（任何狀態；8 週內併掉者、
    壞根週者不在事件檔、未扣）的股票等權；CI ＝ T 曆月分群；⛔ 不判、不計 N、不跑假訊號。
 V12 每年事件數 ＝ 保留數（另報配對後）÷ 段長（年 ＝ 日曆天 ÷ 365.25）；逐年 ＝ T 的曆年；W 與 K 同日重疊比例 ＝ 頻率表 R11 同式（保留層）＋ 配對後層。
    勝率 ＝ 淨報酬（R − 0.585%）＞ 0 的比例；X 勝率 ＝ X ＞ 0 的比例。
 V13 結果句必附（登錄 §四）：「口徑由本線定：日線 14 日、回升過 −80；KD 對照是同法日線重算」「單筆層通過 ≠ 組合會贏 0050」；
    早年另附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註（PatB NOTE_EARLY 同）。先驗 ①②③ 照登錄逐字對照（⛔ 不改）。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WF                  # noqa: E402  事件偵測＋剔除＋%R＋KD＋週線（⛔ 只 import）
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import researchWeekly as RW                   # noqa: E402  weeks_of
from backtest import researchPatC as PC                     # noqa: E402  PatAll 同式小工具（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  cl_stats
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = WF.REG_SHA
OUT = "backtest/resultsWR"
FREQ = WF.OUT
DRY_OUT = "/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/f4c14e25-a422-4a37-ab64-e11f2ead97b5/scratchpad/wr_dry"
HS = (20, 60)
HW = (4, 8, 12, 26)
R20N = 20
REPS, EXCL, SEED_FAKE = 30, 20, 20261018
NCL = 256
Z95 = 1.96
N_FAM = 1
Z_BONF = 1.96
COST = E.COST
DCELLS = ("W", "K")
WCELLS = ("週_W", "週_K")
CELLNUM = {"W": 0, "K": 1}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
JUDGE_SEGS = ("探索", "確認")
NAME = {"W": "Williams %R(14) 從 −80 以下回升", "K": "日線 KD(9,3,3) 低檔金叉（K 上穿 D 且 K ≤ 30）",
        "週_W": "週 %R(14) 從 −80 以下回升", "週_K": "週 KD S1（K 上穿 D 且 K ≤ 30）"}
SENT_SELF = "口徑由本線定：日線 14 日、回升過 −80；KD 對照是同法日線重算"
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
EXC = ["T+H超出資料尾", "r20不可算", "持有期壞根", "R不可算", "無十分位(橫斷面<10)", "配對格無對照股"]
LOG: list = []
DRY = False


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 逐股陣列（純函式；fixture 對逐根迴圈）═════════════
def stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl, dry=False):
    """idx：有效 K 棒的日曆位置；o_b／c_b：有效 K 棒還原開／收；badb[k]：第 k 根與前一根斷開。回日曆（與週）陣列。"""
    nb = len(idx)
    valid = np.zeros(n0, bool); valid[idx] = True
    cf = np.full(n0, np.nan); cf[idx] = c_b
    of = np.full(n0, np.nan); of[idx] = o_b
    cff = pd.Series(cf).ffill().to_numpy()
    badcal = np.zeros(n0, bool); badcal[idx[badb]] = True
    csb = np.cumsum(badcal).astype(np.int64)
    kH = np.searchsorted(idx, np.arange(n0), "right") - 1
    gap = np.zeros(n0, bool)
    okk = (kH >= 0) & (kH < nb - 1)
    p = np.arange(n0)[okk]; kk = kH[okk]
    gap[p] = (idx[kk + 1] - idx[kk] - 1 >= 5) & (p - idx[kk] >= 5)
    okO1 = np.zeros(n0, bool)
    with np.errstate(invalid="ignore"):
        okO1[:-1] = valid[1:] & np.isfinite(of[1:]) & (np.nan_to_num(of[1:]) > 0)
    G = {}; BRK = {}
    t = np.arange(n0)
    for H in HS:
        g = np.full(n0, np.nan)
        m = (t + H <= n0 - 1) & okO1
        tt = t[m]
        with np.errstate(invalid="ignore", divide="ignore"):
            v = cff[tt + H] / of[tt + 1] - 1.0
        g[tt] = 0.0 * v if dry else v
        G[H] = g
        b = np.ones(n0, bool)
        q = t[t + H <= n0 - 1]
        b[q] = ((csb[q + H] - csb[q]) > 0) | gap[q + H]
        BRK[H] = b
    R20 = np.full(n0, np.nan)
    CB = np.cumsum(np.asarray(badb, np.int64))
    bb = np.arange(R20N, nb)
    clean = (CB[bb] - CB[bb - R20N]) == 0
    bb = bb[clean]
    R20[idx[bb]] = c_b[bb] / c_b[bb - R20N] - 1.0
    TR1 = np.zeros(n0, bool)
    with np.errstate(invalid="ignore"):
        TR1[:-1] = valid[:-1] & valid[1:] & ~badcal[1:] & TRDi[1:n0] & np.isfinite(Oi[1:n0]) & (np.nan_to_num(Oi[1:n0]) > 0) & ~UPLi[1:n0]
    POPT = np.asarray(gate, bool)[:n0] & np.asarray(PVi, bool)[:n0]
    # ── 週
    nw = len(wf)
    hasbar = np.bincount(wk[idx], minlength=nw) > 0
    lastpos = np.full(nw, -1, np.int64)
    np.maximum.at(lastpos, wk[idx], idx)
    WGATE = np.zeros(nw, bool)
    WGATE[hasbar] = POPT[lastpos[hasbar]]
    WPRE = np.full(nw, np.nan)
    w = np.arange(4, nw)
    m = hasbar[w]
    w = w[m]
    with np.errstate(invalid="ignore", divide="ignore"):
        WPRE[w] = cff[wl[w]] / cff[wl[w - 4]] - 1.0
    ENT = np.zeros(nw, bool)
    ww = np.arange(nw - 1); e = wf[ww + 1]
    with np.errstate(invalid="ignore"):
        ENT[ww] = valid[e] & TRDi[e] & np.isfinite(Oi[e]) & (np.nan_to_num(Oi[e]) > 0) & ~UPLi[e] & np.isfinite(of[e]) & (np.nan_to_num(of[e]) > 0)
    WR_ = {}; WB = {}
    for k in HW:
        r = np.full(nw, np.nan)
        w2 = np.arange(nw); m2 = ENT & (w2 + k + 1 <= nw - 1)
        w2 = w2[m2]
        with np.errstate(invalid="ignore", divide="ignore"):
            v = cff[wl[w2 + k]] / of[wf[w2 + 1]] - 1.0
        r[w2] = 0.0 * v if dry else v
        WR_[k] = r
        bk = np.ones(nw, bool)
        w3 = np.arange(4, nw - k)
        bk[w3] = ((csb[wl[w3 + k]] - csb[wl[w3 - 4]]) > 0) | gap[wl[w3 + k]]
        WB[k] = bk
    return {"valid": valid, "G": G, "BRK": BRK, "R20": R20, "TR1": TR1, "POPT": POPT,
            "WBASE": WGATE & hasbar & np.isfinite(WPRE), "WPRE": WPRE, "ENT": ENT, "WR": WR_, "WB": WB}


def stock_arrays_loop(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl):
    """逐根迴圈版（fixture 用）。"""
    nb = len(idx); pos = {int(p): k for k, p in enumerate(idx)}
    badset = set(int(idx[k]) for k in range(nb) if badb[k])

    def close_le(p):
        ks = [k for k in range(nb) if idx[k] <= p]
        return c_b[ks[-1]] if ks else np.nan

    def has_bad(a, b):
        return any(a < q <= b for q in badset)

    def in_gap(p):
        ks = [k for k in range(nb) if idx[k] <= p]
        if not ks or ks[-1] == nb - 1:
            return False
        k = ks[-1]
        return (idx[k + 1] - idx[k] - 1 >= 5) and (p - idx[k] >= 5)

    out = {"G": {}, "BRK": {}}
    for H in HS:
        g = np.full(n0, np.nan); b = np.ones(n0, bool)
        for t in range(n0):
            if t + H > n0 - 1:
                continue
            b[t] = has_bad(t, t + H) or in_gap(t + H)
            if (t + 1) in pos and o_b[pos[t + 1]] > 0:
                g[t] = close_le(t + H) / o_b[pos[t + 1]] - 1.0
        out["G"][H] = g; out["BRK"][H] = b
    R20 = np.full(n0, np.nan)
    for k in range(R20N, nb):
        if not any(badb[j] for j in range(k - R20N + 1, k + 1)):
            R20[idx[k]] = c_b[k] / c_b[k - R20N] - 1.0
    out["R20"] = R20
    TR1 = np.zeros(n0, bool)
    for t in range(n0 - 1):
        if t in pos and (t + 1) in pos and not badb[pos[t + 1]] and TRDi[t + 1] and np.isfinite(Oi[t + 1]) and Oi[t + 1] > 0 and not UPLi[t + 1]:
            TR1[t] = True
    out["TR1"] = TR1
    nw = len(wf)
    WBASE = np.zeros(nw, bool); WPRE = np.full(nw, np.nan); ENT = np.zeros(nw, bool)
    out["WR"] = {k: np.full(nw, np.nan) for k in HW}; out["WB"] = {k: np.ones(nw, bool) for k in HW}
    for w in range(nw):
        inw = [int(p) for p in idx if wk[p] == w]
        if inw and w >= 4:
            WPRE[w] = close_le(wl[w]) / close_le(wl[w - 4]) - 1.0
        if inw:
            lp = max(inw)
            WBASE[w] = bool(gate[lp] and PVi[lp] and np.isfinite(WPRE[w]))
        if w + 1 < nw:
            e = wf[w + 1]
            ENT[w] = bool(e in pos and TRDi[e] and np.isfinite(Oi[e]) and Oi[e] > 0 and not UPLi[e] and o_b[pos[e]] > 0)
        for k in HW:
            if ENT[w] and w + k + 1 <= nw - 1:
                out["WR"][k][w] = close_le(wl[w + k]) / o_b[pos[wf[w + 1]]] - 1.0
            if 4 <= w and w + k <= nw - 1:
                out["WB"][k][w] = has_bad(wl[w - 4], wl[w + k]) or in_gap(wl[w + k])
    out.update(WBASE=WBASE, WPRE=WPRE, ENT=ENT)
    return out


def stock_job(a):
    wn, sid = a
    sid_, res = WF.stock_job(a)                           # ⭐ 頻率表同一支：事件、狀態
    if res is None:
        return sid, None
    X = WF.base(wn, sid)                                  # 頻率表同一支：還原 OHLC、壞根、閘、旗標
    W = X["W"]; n0 = X["n0"]; idx = X["idx"]
    B = X["B"]
    o_b = np.asarray(B["o"], float); c_b = np.asarray(B["c"], float)
    assert len(o_b) == len(idx) == len(c_b)
    df = X["df"]
    dfc = df["close"].to_numpy(float)
    assert np.allclose(dfc[idx], c_b, rtol=0, atol=0, equal_nan=False), f"{sid} B['c'] ≠ df close"
    A = stock_arrays(idx, o_b, c_b, X["bad"], n0, X["TRD"], X["O"], X["UPL"], X["gate"], X["PV"], W["wk"], W["wf"], W["wl"], dry=DRY)
    return sid, {"ev": res["ev"], "A": A}


# ═════════════ 統計 ═════════════
def cell_stats(dx, T, H, p0, moni_s):
    dx = np.asarray(dx, float); T = np.asarray(T, np.int64); n = len(dx)
    if n == 0:
        return {"n": 0, "出口": "出口①", "結果": "樣本不足以分辨", "n_eff": 0}
    o = {"n": int(n), "X̄": float(dx.mean()), "中位": float(np.median(dx)), "X勝率": float((dx > 0).mean()),
         "最差": float(dx.min()), "p10": float(np.percentile(dx, 10)), "p90": float(np.percentile(dx, 90))}
    key = PC.clkey(T, H, p0, moni_s)
    cs = R.cl_stats(dx, key)
    assert abs(cs["mean"] - o["X̄"]) < 1e-12
    se = cs["se"]; ng = cs["months"]
    blk = (T - p0) // (20 if H == 20 else 60)
    bm = pd.Series(dx).groupby(blk).mean()
    se2 = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    ne = int(min(n, ng))
    ex, rs = PC.verdict(o["X̄"], se, ne)
    m = o["X̄"]
    mm = pd.Series(dx).groupby(key).mean()
    o.update(se=se, lo=m - Z95 * se, hi=m + Z95 * se, 群數=int(ng), 分群單位=("曆月" if H == 20 else "60日區段"),
             bonf_lo=m - Z_BONF * se, bonf_hi=m + Z_BONF * se,
             se_非重疊=se2, lo_非重疊=m - Z95 * se2, hi_非重疊=m + Z95 * se2, 非重疊區段數=int(len(bm)),
             n_eff=ne, 出口=ex, 結果=rs, X̄扣成本=m - COST, CI下界扣成本=m - Z95 * se - COST,
             逐群平均之中位=float(mm.median()), 逐群中位與平均同號=bool(np.sign(mm.median()) == np.sign(m)))
    return o


def trade_stats(Rv, C):
    Rv = np.asarray(Rv, float); C = np.asarray(C, float)
    if len(Rv) == 0:
        return {}
    net = Rv - COST
    w = net[net > 0]; l_ = net[net <= 0]
    return {"R̄": float(Rv.mean()), "對照R̄": float(C.mean()), "淨報酬平均(R−0.585%)": float(net.mean()), "淨報酬中位": float(np.median(net)),
            "勝率(淨>0)": float((net > 0).mean()), "平均賺": float(w.mean()) if len(w) else None, "平均賠": float(l_.mean()) if len(l_) else None,
            "平均賺賠比": float(w.mean() / abs(l_.mean())) if len(w) and len(l_) and l_.mean() != 0 else None,
            "對照淨報酬平均": float((C - COST).mean())}


def diff_indep(sd1, sd2):
    """另一讀法（只並印）：兩組當獨立樣本。"""
    if not sd1.get("n") or not sd2.get("n"):
        return {}
    d = sd1["X̄"] - sd2["X̄"]; se = float(np.sqrt(sd1["se"] ** 2 + sd2["se"] ** 2))
    return {"se_當獨立": se, "lo_當獨立": d - Z95 * se, "hi_當獨立": d + Z95 * se}


# ═════════════ 對照表（向量化；fixture 對逐檔迴圈）═════════════
def ctrl_tables(POOL, DEC, G):
    n0 = POOL.shape[0]
    rr = np.broadcast_to(np.arange(n0, dtype=np.int64)[:, None], POOL.shape)
    key = (rr * 10 + DEC.astype(np.int64))[POOL]
    gv = G[POOL]
    CS = np.bincount(key, weights=gv, minlength=n0 * 10).reshape(n0, 10)
    CC = np.bincount(key, minlength=n0 * 10).reshape(n0, 10)
    return CS, CC


def ctrl_lookup(CS, CC, POOL, DEC, G, T, i):
    """⇒ (對照平均, 對照數)；對照數 −1 ＝ 無十分位。自己在池內 ⇒ 扣掉。"""
    T = np.asarray(T, np.int64); i = np.asarray(i, np.int64)
    d = DEC[T, i].astype(np.int64)
    ok = d >= 0
    dd = np.where(ok, d, 0)
    selfin = POOL[T, i]
    cc = CC[T, dd] - selfin.astype(np.int64)
    cs = CS[T, dd] - np.where(selfin, np.nan_to_num(G[T, i]), 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        cm = np.where(ok & (cc > 0), cs / np.maximum(cc, 1), np.nan)
    cc = np.where(ok, cc, -1)
    return cm, cc


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(11)
    # F1 對照表 ＝ 逐檔迴圈
    n, S = 200, 50
    G = rng.normal(0, 0.1, (n, S)); G[rng.random((n, S)) < 0.05] = np.nan
    DEC = rng.integers(-1, 10, (n, S)).astype(np.int8)
    POOL = (rng.random((n, S)) < 0.7) & np.isfinite(G) & (DEC >= 0)
    CS, CC = ctrl_tables(POOL, DEC, np.nan_to_num(G))
    worst = 0.0; nchk = 0
    for _ in range(2000):
        t = int(rng.integers(0, n)); i = int(rng.integers(0, S))
        cm, cc = ctrl_lookup(CS, CC, POOL, DEC, G, [t], [i])
        if DEC[t, i] < 0:
            assert cc[0] == -1; continue
        vals = [G[t, q] for q in range(S) if q != i and POOL[t, q] and DEC[t, q] == DEC[t, i]]
        assert cc[0] == len(vals), (cc[0], len(vals))
        if vals:
            worst = max(worst, abs(cm[0] - float(np.mean(vals))))
        nchk += 1
    assert worst < 1e-12
    msgs.append(f"F1 對照表向量版（含自己在池內扣掉）＝ 逐檔迴圈（{nchk} 筆）最大差 {worst:.1e}")
    CS0, CC0 = ctrl_tables(POOL, DEC, np.zeros((n, S)))
    cm0, _ = ctrl_lookup(CS0, CC0, POOL, DEC, np.zeros((n, S)), rng.integers(0, n, 500), rng.integers(0, S, 500))
    assert np.nanmax(np.abs(cm0)) == 0.0
    msgs.append("F2 報酬全 0 的世界 ⇒ 對照 0、X ＝ 0")
    got = PC.excl_past(np.array([79, 80, 99, 100, 101, 120, 121, 140]), np.array([100])).tolist()
    assert got == [79, 80, 99, 121, 140], got
    msgs.append("F3 假訊號排除只看過去 [T−20, T]")
    x = rng.normal(0, 1, 500); key = rng.integers(0, 40, 500)
    acc = np.zeros((NCL, 2)); np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a_ = PC.agg_eval(acc); b_ = R.cl_stats(x, key)
    assert abs(a_["平均"] - b_["mean"]) < 1e-12 and abs(a_["lo"] - b_["lo"]) < 1e-12
    msgs.append("F4 假訊號分群彙總式 ＝ research11.cl_stats")
    d = PC.diff_stats(x, key, x, key)
    assert abs(d["差"]) < 1e-15 and d["se"] < 1e-15
    # 重疊：兩組共用一半事件 ⇒ 線性化 SE ＜ 當獨立
    y = np.r_[x[:250], rng.normal(0, 1, 250)]; ky = np.r_[key[:250], rng.integers(0, 40, 250)]
    d2 = PC.diff_stats(x, key, y, ky)
    s1 = R.cl_stats(x, key)["se"]; s2 = R.cl_stats(y, ky)["se"]
    assert d2["se"] < np.sqrt(s1 ** 2 + s2 ** 2)
    msgs.append(f"F5 兩組相同 ⇒ 差 0、SE 0；共用一半事件 ⇒ 線性化 SE {d2['se']:.4f} ＜ 當獨立 {np.sqrt(s1 ** 2 + s2 ** 2):.4f}（重疊抵銷）")
    v = rng.normal(size=137)
    assert (PC.decile_int(v) == pd.qcut(pd.Series(v).rank(method="first"), 10, labels=False).to_numpy()).all()
    msgs.append("F6 十分位整數式 ＝ pd.qcut(rank(first), 10)")
    # F7 逐股陣列 ＝ 逐根迴圈（合成 K 棒：停牌、≥5 日缺口、壞根、資料尾）
    cal = pd.bdate_range("2020-01-01", periods=260)
    wk, wf, wl = RW.weeks_of(cal)
    n0 = len(cal); worst = 0.0
    for trial in range(6):
        r2 = np.random.default_rng(100 + trial)
        keep = r2.random(n0) > 0.08
        keep[120:128] = False                      # ≥5 日缺口
        if trial % 2:
            keep[-12:] = False                     # 下市（之後無成交）
        idx = np.flatnonzero(keep).astype(np.int64)
        c_b = 50 * np.exp(np.cumsum(r2.normal(0, 0.02, len(idx))))
        o_b = c_b * np.exp(r2.normal(0, 0.01, len(idx)))
        badb = r2.random(len(idx)) < 0.02
        badb[np.flatnonzero(np.diff(idx) - 1 >= 5) + 1] = True
        TRDi = r2.random(n0) > 0.03; Oi = np.where(r2.random(n0) > 0.02, 10.0, np.nan); UPLi = r2.random(n0) < 0.03
        gate = r2.random(n0) > 0.2; PVi = r2.random(n0) > 0.05
        A = stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl)
        L = stock_arrays_loop(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl)
        for H in HS:
            assert (np.isfinite(A["G"][H]) == np.isfinite(L["G"][H])).all(), ("G 有值位置", H, trial)
            worst = max(worst, float(np.nanmax(np.abs(A["G"][H] - L["G"][H]))))
            assert (A["BRK"][H] == L["BRK"][H]).all(), ("BRK", H, trial)
        assert (np.isfinite(A["R20"]) == np.isfinite(L["R20"])).all()
        worst = max(worst, float(np.nanmax(np.abs(A["R20"] - L["R20"]))))
        assert (A["TR1"] == L["TR1"]).all(), ("TR1", trial)
        assert (A["WBASE"] == L["WBASE"]).all() and (A["ENT"] == L["ENT"]).all(), ("週", trial)
        assert (np.isfinite(A["WPRE"]) == np.isfinite(L["WPRE"])).all()
        worst = max(worst, float(np.nanmax(np.abs(A["WPRE"] - L["WPRE"]))))
        for k in HW:
            assert (np.isfinite(A["WR"][k]) == np.isfinite(L["WR"][k])).all(), ("WR", k, trial)
            if np.isfinite(A["WR"][k]).any():
                worst = max(worst, float(np.nanmax(np.abs(A["WR"][k] - L["WR"][k]))))
            assert (A["WB"][k] == L["WB"][k]).all(), ("WB", k, trial)
        D0 = stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl, dry=True)
        assert all((np.isfinite(D0["G"][H]) == np.isfinite(A["G"][H])).all() and np.nanmax(np.abs(D0["G"][H])) == 0 for H in HS)
    assert worst < 1e-12
    msgs.append(f"F7 逐股陣列（R、斷點、r20、T＋1 可買、週 前4週／進場／R_k／斷點）向量版 ＝ 逐根迴圈（6 組合成 K 棒，最大差 {worst:.1e}）；乾跑只留可算位置")
    # F8 不前視：截斷資料尾不改變 ≤ T 的 r20、T＋1 可買以外欄位
    r2 = np.random.default_rng(5)
    idx = np.flatnonzero(r2.random(n0) > 0.05).astype(np.int64)
    c_b = 50 * np.exp(np.cumsum(r2.normal(0, 0.02, len(idx)))); o_b = c_b.copy(); badb = r2.random(len(idx)) < 0.02
    TRDi = np.ones(n0, bool); Oi = np.full(n0, 10.0); UPLi = np.zeros(n0, bool); gate = np.ones(n0, bool); PVi = np.ones(n0, bool)
    A = stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl)
    cut = 180; kc = int(np.searchsorted(idx, cut, "right"))
    Ac = stock_arrays(idx[:kc], o_b[:kc], c_b[:kc], badb[:kc], n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl)
    assert np.array_equal(np.isfinite(A["R20"][:cut + 1]), np.isfinite(Ac["R20"][:cut + 1]))
    assert np.nanmax(np.abs(A["R20"][:cut + 1] - Ac["R20"][:cut + 1])) == 0
    msgs.append("F8 r20（配對量）截掉 T 之後的 K 棒不變（不前視）")
    for m in msgs:
        log("✅ " + m)
    return msgs


# ═════════════ 主程式 ═════════════
def freq_text(ok, cal, n0):
    """照 researchWR_freq.run_freq 的寫法重排 events_<世界>.csv.gz 全文。"""
    allrows = []
    for cell in ("W", "K", "週_W", "週_K"):
        rows = sorted([e for r in ok.values() for e in r["ev"].get(cell, [])], key=lambda x: (x["T"], x["sid"]))
        if not rows:
            continue
        dfo = pd.DataFrame(rows)
        for col in ("T", "c日", "進場日位置"):
            if col in dfo:
                dfo[col] = [str(cal[x].date()) if 0 <= x < n0 else "" for x in dfo[col]]
        dfo.insert(0, "格", cell)
        allrows.append(dfo)
    return pd.concat(allrows, ignore_index=True).to_csv(index=False)


def fake_arm(M, cell, H, ii, TT, p0, pend, moni_s, segnum):
    POOL, DEC, G = M["POOL"][(cell, H)], M["DEC"], M["G"][H]
    CS, CC = M["TAB"][(cell, H)]
    order = np.lexsort((TT, ii)); ii_s, TT_s = ii[order], TT[order]
    stocks, starts = np.unique(ii_s, return_index=True)
    ends = np.r_[starts[1:], len(ii_s)]
    acc = np.zeros((REPS, 2, NCL, 2)); cnt = np.zeros((REPS, 2, 6), np.int64)   # 抽出、閘外、斷點/T+1/R、無十分位、無對照股、可抽日不足
    cands = {}
    for i in stocks:
        cmask = M["VALID"][p0:pend + 1, i] & np.isfinite(M["R20"][p0:pend + 1, i]) & M["POPT"][p0:pend + 1, i]
        cands[int(i)] = (np.flatnonzero(cmask) + p0).astype(np.int64)
    okH = M["TR1"] & ~M["BRK"][H] & np.isfinite(G)
    for r in range(REPS):
        for ver in (0, 1):
            dX = []; TTs = []
            for i, a, b in zip(stocks, starts, ends):
                i = int(i); Tk = TT_s[a:b]
                cand = cands[i]
                if ver == 0:
                    cand = PC.excl_past(cand, Tk)
                m = min(len(Tk), len(cand)); cnt[r, ver, 5] += len(Tk) - m
                if m == 0:
                    continue
                rng = np.random.default_rng([SEED_FAKE + r, M["CRC"][i], CELLNUM[cell], segnum, ver])
                pick = np.sort(rng.choice(cand, size=m, replace=False))
                cnt[r, ver, 0] += m
                g1 = M["POPT"][pick, i]
                cnt[r, ver, 1] += int((~g1).sum()); pick = pick[g1]
                g2 = okH[pick, i]
                cnt[r, ver, 2] += int((~g2).sum()); pick = pick[g2]
                if len(pick) == 0:
                    continue
                cm, cc = ctrl_lookup(CS, CC, POOL, DEC, G, pick, np.full(len(pick), i))
                cnt[r, ver, 3] += int((cc < 0).sum()); cnt[r, ver, 4] += int((cc == 0).sum())
                g3 = cc > 0
                dX.append(G[pick[g3], i] - cm[g3]); TTs.append(pick[g3])
            if dX:
                dXa = np.concatenate(dX); Ta = np.concatenate(TTs)
                if len(dXa):
                    cl = PC.clkey(Ta, H, p0, moni_s)
                    assert cl.max() < NCL
                    np.add.at(acc[r, ver, :, 0], cl, 1.0)
                    np.add.at(acc[r, ver, :, 1], cl, dXa)
    return acc, cnt


def sentence(cell, st, sg, early=False):
    nm = NAME[cell]; H = int(st["H"])
    tail = [SENT_SELF, SENT_ALL] + (NOTE_EARLY if early else [])
    rs = st["結果"]
    head = f"{nm}那天收盤判、隔天開盤買，{H} 天後比同一天、前 20 日走勢同一級距、當天沒出現該訊號的股票"
    if rs == "樣本不足以分辨":
        return f"{head}：樣本不足以分辨（n_eff＝{int(st.get('n_eff', 0) or 0)}）｜" + "；".join(tail)
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(int(st["n_eff"])) if st.get("出口") == "出口②" else ""
    if rs == "結果①":
        s = "{}{}：測不出（每筆平均 X̄ {}，95% CI {} ～ {}）".format(pre, head, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
    else:
        x2 = st.get("假訊號_新預設_x2", 0) or 0
        warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
        verb = "每筆平均多賺" if rs == "結果②" else "每筆平均少賺"
        s = "{}{}{}：{} {}（95% CI {} ～ {}；扣成本 0.585% 後 X̄ {}）".format(warn, pre, head, verb, pct(abs(st["X̄"]))[1:], pct(st["lo"]), pct(st["hi"]), pct(st["X̄扣成本"]))
    role = {"W": "", "K": "〔對照格、描述、⛔ 不判〕"}.get(cell, "")
    seg = {"探索": "〔探索段・判定〕", "確認": "〔確認段・判定〕", "主全窗": "〔主全窗・參考〕", "早年": "〔早年・描述〕"}[sg]
    if cell == "K":
        seg = seg.replace("・判定", "・描述")
    if H == 60:
        seg = seg.replace("・判定", "・描述").replace("・參考", "・描述")
    return seg + role + s + "｜" + "；".join(tail)


def main():
    global DRY
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    DRY = bool(a.dry)
    t0 = time.time()
    out = DRY_OUT if DRY else OUT
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = WF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑（R 全寫 0）' if DRY else '本體'}開跑 {now_tpe()}")
    fx = selftest()
    J = {"性質": "Williams %R 對日線 KD seq1 事件層正式跑（單筆層；判定 W 一格 H20，探索、確認各自報）" + ("〔乾跑：R 全 0〕" if DRY else ""),
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq369 §二、seq372 發號；N_前段 ＋1",
         "方法": "PREREG型態全量 seq3 事件層（researchPatAll C1～C8；AT 世界落地 researchPatC P1～P10）", "Bonferroni": {"族N": N_FAM, "z": Z_BONF},
         "成本": COST, "fixture": fx, "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DIFF = []; DESC = []; WEEK = []; BY = []; FK = []; FACC = {}
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in WF.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 2 if y_ is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["wk"], W["wf"], W["wl"] = RW.weeks_of(cal)
        WF._G[wn] = W
        wk, wf, wl = W["wk"], W["wf"], W["wl"]; nw = len(wf)
        log(f"[{wn}] 段 " + "｜".join(f"{k} {cal[p].date()}～{cal[q].date()}" for k, (p, q) in win.items()))
        sids = W["sids"]; S = len(sids); ix = W["ix"]
        VALID = np.zeros((n0, S), bool); R20 = np.full((n0, S), np.nan); TR1 = np.zeros((n0, S), bool); POPT = np.zeros((n0, S), bool)
        G = {H: np.full((n0, S), np.nan) for H in HS}; BRK = {H: np.ones((n0, S), bool) for H in HS}
        WBASE = np.zeros((nw, S), bool); WPRE = np.full((nw, S), np.nan); ENT = np.zeros((nw, S), bool)
        WRk = {k: np.full((nw, S), np.nan) for k in HW}; WBk = {k: np.ones((nw, S), bool) for k in HW}
        ok = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]; A = r["A"]
                    VALID[:, j] = A["valid"]; R20[:, j] = A["R20"]; TR1[:, j] = A["TR1"]; POPT[:, j] = A["POPT"]
                    for H in HS:
                        G[H][:, j] = A["G"][H]; BRK[H][:, j] = A["BRK"][H]
                    WBASE[:, j] = A["WBASE"]; WPRE[:, j] = A["WPRE"]; ENT[:, j] = A["ENT"]
                    for k in HW:
                        WRk[k][:, j] = A["WR"][k]; WBk[k][:, j] = A["WB"][k]
                    ok[sid] = {"ev": r["ev"]}
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(ok)} 檔｜{time.time() - t0:.0f}s")
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐字）
        mine = freq_text(ok, cal, n0)
        ref = gzip.open(os.path.join(FREQ, f"events_{wn}.csv.gz"), "rt", encoding="utf-8").read()
        if mine != ref:
            raise SystemExit(f"⛔ {wn} 重新偵測 ≠ 已提交 events_{wn}.csv.gz（{len(mine)} vs {len(ref)} 字元）⇒ 中止（未算任何報酬）")
        nlines = ref.count("\n") - 1
        log(f"[查核1] {wn}：重新偵測與已提交頻率表 events_{wn}.csv.gz 逐字相同（{nlines:,} 列）")
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        # ── 原始偵測矩陣、保留事件
        RAW = {c: np.zeros((n0, S), bool) for c in DCELLS}
        RAWW = {c: np.zeros((nw, S), bool) for c in WCELLS}
        KEPT = {c: [] for c in DCELLS + WCELLS}
        WKEPT = {(ix[s_], e["T"]) for s_, r in ok.items() for e in r["ev"]["W"] if e["st"] == "保留"}
        for s_, r in ok.items():
            j = ix[s_]
            for c in DCELLS:
                for e in r["ev"][c]:
                    RAW[c][e["T"], j] = True
                    if e["st"] == "保留":
                        KEPT[c].append((j, e["T"], bool(e["同日K"]) if c == "W" else ((j, e["T"]) in WKEPT)))
            for c in WCELLS:
                for e in r["ev"][c]:
                    RAWW[c][wk[e["T"]], j] = True
                    if e["st"] == "保留":
                        KEPT[c].append((j, e["T"], False))
        # 查核 2：保留事件 ⇒ T＋1 可買、母體（本支矩陣）
        bad2 = Counter()
        for c in DCELLS:
            for j, T, _ in KEPT[c]:
                if not POPT[T, j]:
                    bad2[f"{c} 保留但本支判閘外"] += 1
                if not TR1[T, j]:
                    bad2[f"{c} 保留但本支判 T+1 不可買"] += 1
        assert not bad2, bad2
        log("[查核2] 日線保留事件：本支矩陣判 T 當天母體、T＋1 可買（與頻率表 R7 一致）")
        # ── 十分位、池、對照表、EW
        BASED = POPT & VALID & np.isfinite(R20)
        DEC = PC.dec_matrix(R20, BASED)
        POOLS = {}; TABS = {}; EW = {}
        for H in HS:
            Gz = np.nan_to_num(G[H])
            for c in DCELLS:
                P_ = BASED & TR1 & ~BRK[H] & np.isfinite(G[H]) & ~RAW[c]
                POOLS[(c, H)] = P_; TABS[(c, H)] = ctrl_tables(P_, DEC, Gz)
            em = POPT & TR1 & np.isfinite(G[H])
            cnt_ = em.sum(axis=1); sm = np.where(em, Gz, 0.0).sum(axis=1)
            EW[H] = np.where(cnt_ > 0, sm / np.maximum(cnt_, 1), np.nan)
        M = {"POOL": POOLS, "TAB": TABS, "DEC": DEC, "G": G, "BRK": BRK, "TR1": TR1, "POPT": POPT, "VALID": VALID, "R20": R20,
             "CRC": [zlib.crc32(s.encode("utf-8")) for s in sids]}
        WDEC = PC.dec_matrix(WPRE, WBASE)
        moni = np.asarray(cal.year * 12 + cal.month)
        years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        log(f"[十分位、對照表、EW] 完成｜第一次讀報酬 {J['時點']['第一次讀報酬']}｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(ok),
              "閘": W["gate"], "壞根": W["bad_info"], "段": {}}
        mk_all = np.array([W["mk"].get(s, "twse") for s in sids])
        for sg, (p0, p1) in win.items():
            moni_s = moni - moni[p0]
            yrs = (cal[p1] - cal[p0]).days / 365.25
            segj = {"期間": f"{cal[p0].date()}～{cal[p1].date()}", "年": round(yrs, 3)}
            EVF = {}
            for c in DCELLS:
                kept = [x for x in KEPT[c] if p0 <= x[1] <= p1]
                kept.sort(key=lambda z: (z[1], sids[z[0]]))
                ii = np.array([x[0] for x in kept], np.int64); TT = np.array([x[1] for x in kept], np.int64)
                ovl = np.array([x[2] for x in kept], bool)
                for H in HS:
                    why = np.full(len(kept), "有", dtype=object)
                    beyond = TT + H > n0 - 1
                    Tc = np.minimum(TT, n0 - 1 - H)
                    r20v = np.where(beyond, np.nan, R20[Tc, ii]) if len(kept) else np.zeros(0)
                    g = np.where(beyond, np.nan, G[H][Tc, ii]) if len(kept) else np.zeros(0)
                    brk = np.where(beyond, True, BRK[H][Tc, ii]) if len(kept) else np.zeros(0, bool)
                    cm, cc = ctrl_lookup(*TABS[(c, H)], POOLS[(c, H)], DEC, G[H], Tc, ii) if len(kept) else (np.zeros(0), np.zeros(0, np.int64))
                    dec_e = DEC[Tc, ii] if len(kept) else np.zeros(0, np.int8)
                    for q in range(len(kept)):
                        if beyond[q]:
                            why[q] = EXC[0]
                        elif not np.isfinite(r20v[q]):
                            why[q] = EXC[1]
                        elif brk[q]:
                            why[q] = EXC[2]
                        elif not np.isfinite(g[q]):
                            why[q] = EXC[3]
                        elif cc[q] < 0:
                            why[q] = EXC[4]
                        elif cc[q] == 0:
                            why[q] = EXC[5]
                    okm = why == "有"
                    Xv = np.where(okm, g - cm, np.nan)
                    ew = np.where(beyond, np.nan, EW[H][Tc]) if len(kept) else np.zeros(0)
                    Xu = g - ew
                    st = cell_stats(Xv[okm], TT[okm], H, p0, moni_s)
                    st.update(trade_stats(g[okm], cm[okm]))
                    st.update({"保留": int(len(kept)), "配對剔除": {k: int(v) for k, v in Counter(why[~okm].tolist()).items()},
                               "配對剔除數": int((~okm).sum()), "對照數_中位": float(np.median(cc[okm])) if okm.any() else None,
                               "對照數_最小": int(cc[okm].min()) if okm.any() else None,
                               "每年事件數(保留)": round(len(kept) / yrs, 1), "每年事件數(配對後)": round(int(okm.sum()) / yrs, 1),
                               "相異檔數": int(len(set(ii[okm].tolist()))),
                               "未配對_Xu": PC.desc_ci(Xu[okm], TT[okm], H, p0, moni_s)})
                    mk = mk_all[ii] if len(kept) else np.zeros(0, str)
                    st["上市"] = PC.desc_ci(Xv[okm & (mk == "twse")], TT[okm & (mk == "twse")], H, p0, moni_s)
                    st["上櫃"] = PC.desc_ci(Xv[okm & (mk == "tpex")], TT[okm & (mk == "tpex")], H, p0, moni_s)
                    yr = years[TT] if len(kept) else np.zeros(0, int)
                    st["逐年"] = {str(y): {"保留": int((yr == y).sum()), "n": int((okm & (yr == y)).sum()),
                                         "X̄": float(Xv[okm & (yr == y)].mean()) if (okm & (yr == y)).any() else None}
                                for y in sorted(set(yr.tolist()))}
                    for y, qd in st["逐年"].items():
                        BY.append({"世界": wn, "段": sg, "格": c, "H": H, "年": y, **qd})
                    fr = pd.DataFrame({"sid": [sids[i] for i in ii], "market": mk, "T": dates[TT] if len(kept) else [],
                                       "進場日": [dates[t + 1] for t in TT], "出場日": [dates[t + H] if t + H <= n0 - 1 else "" for t in TT],
                                       "r20": r20v, "十分位": dec_e, "R": g, "對照平均": cm, "對照數": cc, "X": Xv, "EW": ew, "X_未配對": Xu,
                                       "分群": PC.clkey(TT, H, p0, moni_s) if len(kept) else [], "配對": why,
                                       ("同日K" if c == "W" else "同日W"): ovl})
                    EVF[(c, H)] = {"fr": fr, "i": ii, "T": TT, "ok": okm, "X": Xv, "ovl": ovl}
                    if H == 20:
                        pend = min(p1, n0 - 1 - H)
                        acc, cntf = fake_arm(M, c, H, ii, TT, p0, pend, moni_s, SEGNUM[sg])
                        FACC[f"{wn}|{sg}|{c}|H{H}"] = (acc, cntf)
                        for ver, vn in ((0, "新預設"), (1, "不排除")):
                            res_ = [PC.agg_eval(acc[r_, ver]) for r_ in range(REPS)]
                            st[f"假訊號_{vn}_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                            st[f"假訊號_{vn}_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                            st[f"假訊號_{vn}_平均X"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                            c2 = cntf[:, ver].sum(axis=0)
                            st[f"假訊號_{vn}_帳"] = {"抽出": int(c2[0]), "剔除_閘外": int(c2[1]), "剔除_斷點或T+1或R": int(c2[2]),
                                                  "無十分位": int(c2[3]), "配對格無對照股": int(c2[4]), "可抽日不足": int(c2[5])}
                            for r_, q in enumerate(res_):
                                FK.append({"世界": wn, "段": sg, "格": c, "H": H, "版本": vn, "r": r_,
                                           **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                    st["H"] = H
                    if c == "K":
                        st["身分"] = "對照格（同法報、⛔ 不判、不計 N）"
                    elif H == 60:
                        st["身分"] = "H60 描述（⛔ 不判）"
                    else:
                        st["身分"] = {"探索": "判定格｜探索段判定", "確認": "判定格｜確認段判定", "主全窗": "判定格｜主全窗參考", "早年": "判定格｜早年描述"}[sg]
                    if H == 20:
                        st["過seq322門檻"] = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st.get("假訊號_新預設_x2", 99) <= 1
                                               and st.get("X̄扣成本", -1) > 0 and st.get("逐群中位與平均同號", False))
                    st["句子"] = sentence(c, st, sg, early=(wn == "早年"))
                    segj[f"{c}_H{H}"] = st
                    fr.to_csv(os.path.join(out, "events", f"trades_{wn}_{sg}_{c}_H{H}.csv.gz"), index=False,
                              compression={"method": "gzip", "compresslevel": 6})
                    MAIN.append({"世界": wn, "段": sg, "格": c, "說明": NAME[c], "H": H, "身分": st["身分"], "期間": segj["期間"],
                                 **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("H", "身分", "句子")}, "句子": st["句子"]})
                    log(f"  [{wn}/{sg}] {c} H{H}：保留 {len(kept)} 配對 {st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} "
                        f"CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}" + (f" 假 x={st.get('假訊號_新預設_x2')}" if H == 20 else "") + f"｜{time.time() - t0:.0f}s")
            # ── W − K 差（V10）與重疊拆解
            for H in HS:
                A1 = EVF[("W", H)]; A2 = EVF[("K", H)]
                k1 = PC.clkey(A1["T"][A1["ok"]], H, p0, moni_s); k2 = PC.clkey(A2["T"][A2["ok"]], H, p0, moni_s)
                d = PC.diff_stats(A1["X"][A1["ok"]], k1, A2["X"][A2["ok"]], k2)
                d = {("差(W−K)" if k == "差" else ("X̄_W" if k == "新" else ("X̄_K" if k == "原" else ("n_W" if k == "n新" else ("n_K" if k == "n原" else k))))): v
                     for k, v in d.items()}
                d["標籤（描述）"] = "差的 CI 含 0" if d["lo"] <= 0 <= d["hi"] else ("W＞K" if d["差(W−K)"] > 0 else "W＜K")
                d.update(diff_indep(segj[f"W_H{H}"], segj[f"K_H{H}"]))
                kw = set(zip(A1["fr"]["sid"][A1["ok"]], A1["fr"]["T"][A1["ok"]])); kk_ = set(zip(A2["fr"]["sid"][A2["ok"]], A2["fr"]["T"][A2["ok"]]))
                both = len(kw & kk_)
                d.update({"配對後同檔同日重疊": both, "重疊÷W": both / len(kw) if kw else None, "重疊÷K": both / len(kk_) if kk_ else None})
                DIFF.append({"世界": wn, "段": sg, "H": H, **d})
                inK = A1["ovl"]; inW = A2["ovl"]                    # 保留層同檔同日（頻率表 R11 同式）
                for nm, src, m_ in (("W∩K 同日・保留層（W 的對照）", A1, A1["ok"] & inK), ("W 獨有（W∖K）", A1, A1["ok"] & ~inK),
                                    ("W∩K 同日・保留層（K 的對照）", A2, A2["ok"] & inW), ("K 獨有（K∖W）", A2, A2["ok"] & ~inW)):
                    DESC.append({"世界": wn, "段": sg, "子集": nm, "H": H, **PC.desc_ci(src["X"][m_], src["T"][m_], H, p0, moni_s)})
            kpw = [x for x in KEPT["W"] if p0 <= x[1] <= p1]; kpk = [x for x in KEPT["K"] if p0 <= x[1] <= p1]
            bw = sum(1 for x in kpw if x[2])
            segj["重疊(保留層)"] = {"W保留": len(kpw), "K保留": len(kpk), "同檔同日": bw, "÷W": bw / len(kpw) if kpw else None,
                                 "÷K": bw / len(kpk) if kpk else None}
            # ── 週線版（V11）
            for c in WCELLS:
                kept = [x for x in KEPT[c] if p0 <= x[1] <= p1]
                kept.sort(key=lambda z: (z[1], sids[z[0]]))
                ii = np.array([x[0] for x in kept], np.int64); TT = np.array([x[1] for x in kept], np.int64)
                ww = wk[TT] if len(kept) else np.zeros(0, np.int64)
                for k in HW:
                    if not len(kept):
                        WEEK.append({"世界": wn, "段": sg, "格": c, "持有週": k, "保留": 0}); continue
                    POOLW = WBASE & ENT & np.isfinite(WRk[k]) & ~WBk[k] & ~RAWW[c]
                    CSw, CCw = ctrl_tables(POOLW, WDEC, np.nan_to_num(WRk[k]))
                    cm, cc = ctrl_lookup(CSw, CCw, POOLW, WDEC, WRk[k], ww, ii)
                    rk = WRk[k][ww, ii]; bk = WBk[k][ww, ii]; base_ = WBASE[ww, ii]; ent = ENT[ww, ii]
                    why = np.where(~ent, "進場不可買", np.where(~np.isfinite(rk), "R不可算(出場週超出資料尾)", np.where(bk, "斷點", np.where(~base_, "前4週報酬不可算或閘外",
                                   np.where(cc < 0, "無十分位", np.where(cc == 0, "配對格無對照股", "有")))))).astype(object)
                    okm = why == "有"
                    Xv = np.where(okm, rk - cm, np.nan)
                    dsc = PC.desc_ci(Xv[okm], TT[okm], 20, p0, moni_s)
                    WEEK.append({"世界": wn, "段": sg, "格": c, "持有週": k, "保留": int(len(kept)), "配對剔除": dict(Counter(why[~okm].tolist())),
                                 **dsc, "R̄": float(rk[okm].mean()) if okm.any() else None, "對照R̄": float(cm[okm].mean()) if okm.any() else None,
                                 "_X": Xv, "_T": TT, "_ok": okm})
                    pd.DataFrame({"sid": [sids[i] for i in ii], "T": dates[TT], "週": ww, "R": rk, "對照平均": cm, "對照數": cc, "X": Xv, "配對": why}).to_csv(
                        os.path.join(out, "events", f"trades_{wn}_{sg}_{c}_K{k}w.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
            for k in HW:
                a1 = [w_ for w_ in WEEK if w_["世界"] == wn and w_["段"] == sg and w_["格"] == "週_W" and w_["持有週"] == k and "_X" in w_]
                a2 = [w_ for w_ in WEEK if w_["世界"] == wn and w_["段"] == sg and w_["格"] == "週_K" and w_["持有週"] == k and "_X" in w_]
                if a1 and a2:
                    a1, a2 = a1[0], a2[0]
                    d = PC.diff_stats(a1["_X"][a1["_ok"]], moni_s[a1["_T"][a1["_ok"]]], a2["_X"][a2["_ok"]], moni_s[a2["_T"][a2["_ok"]]])
                    WEEK.append({"世界": wn, "段": sg, "格": "週_W − 週_K", "持有週": k, "n": d.get("n新"), "平均": d.get("差"), "lo": d.get("lo"), "hi": d.get("hi"),
                                 "標籤": (d.get("標籤（描述）", "") or "").replace("新", "週_W").replace("原", "週_K") + "（描述、⛔ 不判）"})
            Wj["段"][sg] = segj
        J["世界"][wn] = Wj
        del VALID, R20, TR1, POPT, G, BRK, WBASE, WPRE, ENT, WRk, WBk, RAW, RAWW, M, POOLS, TABS, DEC, WDEC
    # ── 判定（W H20；探索、確認各自）
    jd = {}
    for sg in JUDGE_SEGS + ("主全窗",):
        st = J["世界"]["主"]["段"][sg]["W_H20"]
        jd[sg] = {"身分": "判定" if sg in JUDGE_SEGS else "參考", "結果": st["結果"], "出口": st.get("出口"), "n": st["n"], "n_eff": st.get("n_eff"),
                  "X̄": st.get("X̄"), "95%CI": [st.get("lo"), st.get("hi")], "假訊號x/30(新預設)": st.get("假訊號_新預設_x2"),
                  "X̄−成本": st.get("X̄扣成本"), "逐月中位同號": st.get("逐群中位與平均同號"), "過seq322門檻": st.get("過seq322門檻"), "句子": st["句子"]}
    J["判定"] = jd
    # ── 先驗（登錄 §四，⛔ 不改）
    dW = {r["段"]: r for r in DIFF if r["世界"] == "主" and r["H"] == 20}
    ov = {sg: J["世界"]["主"]["段"][sg]["重疊(保留層)"]["÷W"] for sg in ("探索", "確認", "主全窗")}
    J["先驗"] = {
        "① W 落結果①（約六成五）": {sg: {"結果": jd[sg]["結果"], "中": jd[sg]["結果"] == "結果①"} for sg in JUDGE_SEGS},
        "② W 與 K 同日重疊 ＜ 30%（約五成五）": {sg: {"重疊÷W": ov[sg], "中": bool(ov[sg] < 0.30)} for sg in ov},
        "③ W − K 差 CI 含 0（約七成）": {sg: {"差": dW[sg]["差(W−K)"], "CI": [dW[sg]["lo"], dW[sg]["hi"]], "中": bool(dW[sg]["lo"] <= 0 <= dW[sg]["hi"])}
                                    for sg in JUDGE_SEGS}}
    J["N"] = {"本件判定格": 1, "對照格 K、W−K 差、描述格、週線版": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    for w_ in WEEK:
        for k in ("_X", "_T", "_ok"):
            w_.pop(k, None)
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "WR_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DIFF).to_csv(os.path.join(out, "WR_diff.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DESC).to_csv(os.path.join(out, "WR_desc.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(WEEK).to_csv(os.path.join(out, "WR_week.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    keys = list(FACC)
    np.savez_compressed(os.path.join(out, "fake_acc.npz"), keys=np.array(keys), acc=np.stack([FACC[k][0] for k in keys]),
                        cnt=np.stack([FACC[k][1] for k in keys]))
    J["W−K"] = DIFF; J["描述"] = DESC; J["週線"] = WEEK
    json.dump(J, open(os.path.join(out, "WR.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'X̄', '假訊號x/30(新預設)', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
