# -*- coding: utf-8 -*-
"""PREREG KDJ三週期共振 seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 94378c24e2a8af54，2026-10-20 18:47；裁定 seq394 第 3 題、
seq398 發號、seq399 核准開跑（可判、不退化：只佔日線 KD 事件 3～5%）；N_前段 ＋1；標籤照常）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsKDJ3/freq/ ⛔ 不碰）；researchKDJ3_freq（事件偵測、剔除）、researchWR_freq（世界、base、段）、
   researchWR（ctrl_tables、ctrl_lookup、stock_arrays〔fixture 對照用〕）、researchPatC（decile_int、dec_matrix、excl_past、verdict、agg_eval、
   diff_stats）、researchAscTri_freq（load_world）、research11（cl_stats）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchKDJ3 [--procs 2] [--dry [--limit N]]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchKDJ3_check
    --dry ＝ 不含報酬的乾跑（所有 R 一律寫成 0、只留「可不可算」；輸出到 scratch 夾）；--limit 只准與 --dry 同用（⛔ 含報酬的小樣本試跑）
輸出 backtest/resultsKDJ3/（⛔ 不碰 freq/）：KDJ3.json、KDJ3_main.csv（判定表＋分報＋描述格）、KDJ3_diff.csv（J − D 差）、
    KDJ3_overlap.csv（重疊）、by_year.csv、fake_reps.csv、fake_acc.npz、events/trades_<世界>_<段>_<格>_H<H>.csv.gz、run.log

格（頻率表同名）：J ＝ 判定格（H20 判；H60、H120 描述）；描述（⛔ 不判、不計 N）：D（只有日線 K[T−1]＜20 金叉 ＝ 退化分母、日線 KD 對照）、
    較嚴 J_週月KD皆<20、J_週已金叉、J_月已金叉、J_J<0、單條 D+週、D+月；另一讀法（只報）J_週月暖機9根。

═══ 讀法（G 標；頻率表 K1～K8 原樣沿用（世界、母體、壞根、KD、週月 K「已收完」、暖機、合併、剔除、段）；方法 ＝ researchWR V1～V13
     （PREREG型態全量 seq3 事件層 C1～C8 的 AT 世界落地版），以下只寫與 WR 不同或新增者；⛔ 在讀任何本件報酬之前寫死；
     ★＝執行者定，〔 〕內為另一讀法、⛔ 不另跑）═══
 G1 事件 ＝ 逐股呼叫 researchKDJ3_freq.stock_job 原樣；⭐ 依 run_freq 寫法排成 events_<世界>.csv.gz 全文，與已提交檔【逐字】比，任一不同 ⇒
    中止、⛔ 不算報酬。判定母體 ＝ 狀態「保留」者（同檔 20 日內只算第一筆 ⇒ H20 持有不重疊）。
 G2 R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1（WR V2 同；H ∈ {20, 60, 120}）；X ＝ R − 對照平均；成本兩邊相同 ⇒ X ⛔ 不扣，
    另報 X̄ − 0.585% 與每筆淨報酬（R − 0.585%）。
 G3 對照（登錄 §三「同一天 T、r60 同十分位、當天沒觸發本件的股票等權」）＝ WR V3 原樣，只把 r20 換成 r60：
    ★ r60 ＝ c[b] ÷ c[b−60] − 1（b ＝ 該股 T 那根有效 K 棒；含 T 收盤，WR V3 同理）〔另一讀法：c[b−1] ÷ c[b−61] − 1〕；(b−60, b] 內有壞 K 棒 ⇒ 缺值
    （事件剔除並計數「r60不可算」）。十分位橫斷面 ＝ T 當天母體（Frame.gate ∧ pit_valid）∧ 有效 K 棒 ∧ r60 可算（＜10 檔 ⇒ 無十分位）。
    對照股 ＝ 同十分位 ∧ T 當天母體 ∧ T＋1 可買（頻率表 K1 同旗標；⛔ 不另剔開盤跌停）∧ (T, T＋H] 無硬斷點 ∧ R 可算
    ∧ ★ T 當天【原始】偵測沒有「該格」（J 的對照扣 J 的原始偵測，任何狀態；描述格各扣各的）∧ 不是自己 ⇒ 等權平均。
 G4 硬斷點 ＝ WR V4（(T, T＋H] 有壞 K 棒，或 T＋H 落在 ≥ 5 日缺口）；T＋H 超出資料尾 ⇒ 剔除並計數。
 G5 判定量 X̄；CI：H20 ＝ T 所在曆月分群（登錄 §三）；★ H60 ＝ (T − 段起點)//60、H120 ＝ (T − 段起點)//120 分群（PatAll C6 推廣；只描述）；
    CR0、1.96；n_eff ＝ min(配對後事件數, 分群數)；＜30 樣本不足以分辨、30～99 出口②（「樣本中等」）、≥100 出口③；
    結果② ＝ CI 不含 0 且 ＞0、③ ＝ 不含 0 且 ＜0、① ＝ 含 0。Bonferroni 族 ＝ 本登錄判定格 N ＝ 1 ⇒ z ＝ 1.96。
 G6 段（登錄 §三）：判定 ＝【探索】【確認】各自照 G5 判（各一個結果）；主全窗並報【參考】；早年只描述（附 reduce_v2 註）。
 G7 假訊號臂（WR V8 原樣；只跑判定格 J、H20）：r ＝ 0…29；可抽日 ＝ 該檔有效 K 棒 ∧ r60 可算 ∧ T 當天母體、T ∈ [段起點, min(段尾, 資料尾 − 20)]；
    新預設排除「存在 J 保留真事件 T_r ∈ [T−20, T]」的日子，不排除版並列；種子 default_rng([20261020＋r, crc32(sid), 0, 段序號, 版本])。
    x／30 ＝ 落結果② 的次數；結果② 且 x ≥ 2 ⇒ 句首「⚠ 隨機挑日子也有 x／30 次同樣過關。」
 G8 seq322 門檻（WR V9 同式）＝ 該段結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；
    五條全過才另起組合層（登錄 §三）。探索、確認各報（主全窗參考）。
 G9 J − D 差（描述、⛔ 不判）：PatC P8／WR V10 曆月分群線性化 SE（重疊事件互相抵銷）；H60／H120 用 G5 的分群。
 G10 重疊（登錄 §四；J 保留事件，件數 ÷ 保留數）：日線 KD 低檔金叉（%R 件 K 格）、Williams %R（W 格）＝ 頻率表旗標；
    ★ 急跌錯殺 ＝ resultsCrashOversold/events.csv.gz 全部候選列（最低 2% ∧ r10＜0、20 日去重後；不看 F1／公司事件；版面 main↔主、早年↔早年）
      同檔同日（T ＝ 日期t）與同檔 ±20 交易日；★ 大盤大跌後買什麼 ＝ resultsMktDrop/events.csv 定義 q2（擴張視窗 2% 分位）全部日子
      （另報「波段第一天」）：T ＝ 事件日（同日）與 T ∈ [事件日, 事件日＋20 交易日]（之後 20 日內）。
 G11 描述：逐年（J 保留數）與空頭年 2008、2011、2022 占比（裁定 seq399 結果句附）；上市／上櫃；未配對 X_u（WR V5）。
 G12 結果句必附：「多週期共振為實務說法、無學術原作，與 Elder 三重濾網（長週期看趨勢、短週期等超賣）不同」「參數 9／3／3 為台灣通用」
    「月線只用已收完的月 K」「事件集中空頭年 2008、2011、2022」「單筆層通過 ≠ 組合會贏 0050」；早年另附「早年含減資假飆股約 0.3%
    （剩 22 筆未解釋）」＋ 上櫃版面註。本件無賣出訊號（固定 H 天）；措辭照 seq343，⛔ 不稱最高點、頂部。先驗 ①②③ 照登錄逐字對照（⛔ 不改）。
"""
from __future__ import annotations

import argparse
import gzip
import io
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
from backtest import researchKDJ3_freq as KF                # noqa: E402  事件偵測＋剔除（⛔ 只 import）
from backtest import researchWR_freq as WF                  # noqa: E402  base、SEGS、reg_check、_G（⛔ 只 import）
from backtest import researchWR as WRF                      # noqa: E402  ctrl_tables、ctrl_lookup、stock_arrays（⛔ 只 import）
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import researchWeekly as RW                   # noqa: E402  weeks_of
from backtest import researchPatC as PC                     # noqa: E402  PatAll 同式小工具（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  cl_stats
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = KF.REG_SHA
OUT = "backtest/resultsKDJ3"
FREQ = KF.OUT
DRY_OUT = "/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/f4c14e25-a422-4a37-ab64-e11f2ead97b5/scratchpad/kdj3_dry"
HS = (20, 60, 120)
RN = 60
REPS, EXCL, SEED_FAKE = 30, 20, 20261020
NCL = 512
Z95 = 1.96
N_FAM = 1
Z_BONF = 1.96
COST = E.COST
CELLS = list(KF.CELLS)
CELLNUM = {c: i for i, c in enumerate(CELLS)}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
JUDGE_SEGS = ("探索", "確認")
BEAR_YEARS = (2008, 2011, 2022)
NAME = {"J": "日、週、月 KD 都在 20 以下、日線 K 上穿 D", "D": "只有日線 KD 低檔金叉（K[T−1]＜20、K 上穿 D）",
        "J_週月KD皆<20": "較嚴：週、月 K 與 D 都 ＜20", "J_週已金叉": "較嚴：週線也已金叉", "J_月已金叉": "較嚴：月線也已金叉",
        "J_J<0": "較嚴：日線 J[T−1] ＜ 0", "J_週月暖機9根": "另一讀法：週月 KD 第 9 根起就判", "D+週": "單條：日線 ＋ 週 K＜20",
        "D+月": "單條：日線 ＋ 月 K＜20"}
SENT_SELF = ["多週期共振為實務說法、無學術原作，與 Elder 三重濾網（長週期看趨勢、短週期等超賣）不同", "參數 9／3／3 為台灣通用",
             "月線只用已收完的月 K", "事件集中空頭年 2008、2011、2022"]
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
EXC = ["T+H超出資料尾", "r60不可算", "持有期壞根", "R不可算", "無十分位(橫斷面<10)", "配對格無對照股"]
LOG: list = []
DRY = False


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 共用小工具（三重底件 import）═════════════
def clkey(T, H, p0, moni_s):
    """G5：H20 曆月；H60／H120 ＝ (T − 段起點)//H。"""
    T = np.asarray(T, np.int64)
    return moni_s[T] if H == 20 else (T - p0) // H


def cell_stats(dx, T, H, p0, moni_s):
    """WR.cell_stats 同式，分群改 G5。"""
    dx = np.asarray(dx, float); T = np.asarray(T, np.int64); n = len(dx)
    if n == 0:
        return {"n": 0, "出口": "出口①", "結果": "樣本不足以分辨", "n_eff": 0}
    o = {"n": int(n), "X̄": float(dx.mean()), "中位": float(np.median(dx)), "X勝率": float((dx > 0).mean()),
         "最差": float(dx.min()), "p10": float(np.percentile(dx, 10)), "p90": float(np.percentile(dx, 90))}
    key = clkey(T, H, p0, moni_s)
    cs = R.cl_stats(dx, key)
    assert abs(cs["mean"] - o["X̄"]) < 1e-12
    se = cs["se"]; ng = cs["months"]
    blk = (T - p0) // H
    bm = pd.Series(dx).groupby(blk).mean()
    se2 = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    ne = int(min(n, ng))
    ex, rs = PC.verdict(o["X̄"], se, ne)
    m = o["X̄"]
    mm = pd.Series(dx).groupby(key).mean()
    o.update(se=se, lo=m - Z95 * se, hi=m + Z95 * se, 群數=int(ng), 分群單位=("曆月" if H == 20 else f"{H}日區段"),
             bonf_lo=m - Z_BONF * se, bonf_hi=m + Z_BONF * se,
             se_非重疊=se2, lo_非重疊=m - Z95 * se2, hi_非重疊=m + Z95 * se2, 非重疊區段數=int(len(bm)),
             n_eff=ne, 出口=ex, 結果=rs, X̄扣成本=m - COST, CI下界扣成本=m - Z95 * se - COST,
             逐群平均之中位=float(mm.median()), 逐群中位與平均同號=bool(np.sign(mm.median()) == np.sign(m)))
    return o


def desc_ci(x, T, H, p0, moni_s):
    x = np.asarray(x, float); T = np.asarray(T, np.int64); ok = np.isfinite(x); x, T = x[ok], T[ok]
    if len(x) == 0:
        return {"n": 0}
    o = {"n": int(len(x)), "平均": float(x.mean()), "中位": float(np.median(x)), "勝率": float((x > 0).mean())}
    if len(x) < 2:
        return o
    cs = R.cl_stats(x, clkey(T, H, p0, moni_s))
    ne = int(min(len(x), cs["months"]))
    ex, rs = PC.verdict(cs["mean"], cs["se"], ne)
    o.update(lo=cs["lo"], hi=cs["hi"], n_eff=ne, 標籤=rs + "（描述、⛔ 不判）")
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


def stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, hs=HS, rn=RN, anchor="T", dry=False):
    """WR.stock_arrays 的日線部分（H 可多個）＋ rN 配對量。anchor ＝ "T"：rN[idx[b]] ＝ c[b]÷c[b−N]−1、(b−N, b] 無壞根；
    "pre"：rN[idx[b]] ＝ c[b−1]÷c[b−1−N]−1（PA._rN 同式，型態第一點用）、(b−1−N, b−1] 無壞根。另回 CSB（日曆壞根累加）、GAP。"""
    nb = len(idx)
    valid = np.zeros(n0, bool); valid[idx] = True
    cf = np.full(n0, np.nan); cf[idx] = c_b
    of = np.full(n0, np.nan); of[idx] = o_b
    cff = pd.Series(cf).ffill().to_numpy()
    badcal = np.zeros(n0, bool); badcal[idx[np.asarray(badb, bool)]] = True
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
    for H in hs:
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
    RNa = np.full(n0, np.nan)
    CB = np.cumsum(np.asarray(badb, np.int64))
    if anchor == "T":
        bb = np.arange(rn, nb)
        bb = bb[(CB[bb] - CB[bb - rn]) == 0]
        RNa[idx[bb]] = c_b[bb] / c_b[bb - rn] - 1.0
    else:
        bb = np.arange(rn + 1, nb)
        bb = bb[(CB[bb - 1] - CB[bb - 1 - rn]) == 0]
        RNa[idx[bb]] = c_b[bb - 1] / c_b[bb - 1 - rn] - 1.0
    TR1 = np.zeros(n0, bool)
    with np.errstate(invalid="ignore"):
        TR1[:-1] = valid[:-1] & valid[1:] & ~badcal[1:] & TRDi[1:n0] & np.isfinite(Oi[1:n0]) & (np.nan_to_num(Oi[1:n0]) > 0) & ~UPLi[1:n0]
    PV = np.asarray(PVi, bool)[:n0]
    POPT = np.asarray(gate, bool)[:n0] & PV
    return {"valid": valid, "G": G, "BRK": BRK, "RN": RNa, "TR1": TR1, "POPT": POPT, "PV": PV, "CSB": csb, "GAP": gap}


def stock_arrays_loop(idx, o_b, c_b, badb, n0, hs=HS, rn=RN, anchor="T"):
    """逐根迴圈版（fixture）：G、BRK、RN。"""
    nb = len(idx); pos = {int(p): k for k, p in enumerate(idx)}
    badset = set(int(idx[k]) for k in range(nb) if badb[k])

    def close_le(p):
        ks = [k for k in range(nb) if idx[k] <= p]
        return c_b[ks[-1]] if ks else np.nan

    def in_gap(p):
        ks = [k for k in range(nb) if idx[k] <= p]
        if not ks or ks[-1] == nb - 1:
            return False
        k = ks[-1]
        return (idx[k + 1] - idx[k] - 1 >= 5) and (p - idx[k] >= 5)

    out = {"G": {}, "BRK": {}}
    for H in hs:
        g = np.full(n0, np.nan); b = np.ones(n0, bool)
        for t in range(n0):
            if t + H > n0 - 1:
                continue
            b[t] = any(t < q <= t + H for q in badset) or in_gap(t + H)
            if (t + 1) in pos and o_b[pos[t + 1]] > 0:
                g[t] = close_le(t + H) / o_b[pos[t + 1]] - 1.0
        out["G"][H] = g; out["BRK"][H] = b
    RNa = np.full(n0, np.nan)
    for k in range(nb):
        if anchor == "T":
            if k >= rn and not any(badb[j] for j in range(k - rn + 1, k + 1)):
                RNa[idx[k]] = c_b[k] / c_b[k - rn] - 1.0
        else:
            if k >= rn + 1 and not any(badb[j] for j in range(k - rn, k)):
                RNa[idx[k]] = c_b[k - 1] / c_b[k - 1 - rn] - 1.0
    out["RN"] = RNa
    return out


def fixture_common():
    """F1～F6：共用小工具（兩件共用）。"""
    msgs = []
    rng = np.random.default_rng(11)
    n, S = 200, 50
    G = rng.normal(0, 0.1, (n, S)); G[rng.random((n, S)) < 0.05] = np.nan
    DEC = rng.integers(-1, 10, (n, S)).astype(np.int8)
    POOL = (rng.random((n, S)) < 0.7) & np.isfinite(G) & (DEC >= 0)
    CS, CC = WRF.ctrl_tables(POOL, DEC, np.nan_to_num(G))
    worst = 0.0; nchk = 0
    for _ in range(1500):
        t = int(rng.integers(0, n)); i = int(rng.integers(0, S))
        cm, cc = WRF.ctrl_lookup(CS, CC, POOL, DEC, G, [t], [i])
        if DEC[t, i] < 0:
            assert cc[0] == -1; continue
        vals = [G[t, q] for q in range(S) if q != i and POOL[t, q] and DEC[t, q] == DEC[t, i]]
        assert cc[0] == len(vals)
        if vals:
            worst = max(worst, abs(cm[0] - float(np.mean(vals))))
        nchk += 1
    assert worst < 1e-12
    msgs.append(f"F1 對照表向量版（含自己在池內扣掉）＝ 逐檔迴圈（{nchk} 筆）最大差 {worst:.1e}")
    got = PC.excl_past(np.array([79, 80, 99, 100, 101, 120, 121, 140]), np.array([100])).tolist()
    assert got == [79, 80, 99, 121, 140], got
    msgs.append("F2 假訊號排除只看過去 [T−20, T]")
    x = rng.normal(0, 1, 500); key = rng.integers(0, 40, 500)
    acc = np.zeros((NCL, 2)); np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a_ = PC.agg_eval(acc); b_ = R.cl_stats(x, key)
    assert abs(a_["平均"] - b_["mean"]) < 1e-12 and abs(a_["lo"] - b_["lo"]) < 1e-12
    msgs.append("F3 假訊號分群彙總式 ＝ research11.cl_stats")
    d = PC.diff_stats(x, key, x, key)
    assert abs(d["差"]) < 1e-15 and d["se"] < 1e-15
    msgs.append("F4 兩組相同 ⇒ 差 0、SE 0")
    v = rng.normal(size=137)
    assert (PC.decile_int(v) == pd.qcut(pd.Series(v).rank(method="first"), 10, labels=False).to_numpy()).all()
    msgs.append("F5 十分位整數式 ＝ pd.qcut(rank(first), 10)")
    # F6 逐股陣列 ＝ 逐根迴圈；H20／H60 與 researchWR.stock_arrays 逐位元同；rN(T, 20) ＝ WR 的 r20
    cal = pd.bdate_range("2020-01-01", periods=300)
    wk, wf, wl = RW.weeks_of(cal)
    n0 = len(cal); worst = 0.0
    for trial in range(6):
        r2 = np.random.default_rng(100 + trial)
        keep = r2.random(n0) > 0.08
        keep[120:128] = False
        if trial % 2:
            keep[-12:] = False
        idx = np.flatnonzero(keep).astype(np.int64)
        c_b = 50 * np.exp(np.cumsum(r2.normal(0, 0.02, len(idx))))
        o_b = c_b * np.exp(r2.normal(0, 0.01, len(idx)))
        badb = r2.random(len(idx)) < 0.02
        badb[np.flatnonzero(np.diff(idx) - 1 >= 5) + 1] = True
        TRDi = r2.random(n0) > 0.03; Oi = np.where(r2.random(n0) > 0.02, 10.0, np.nan); UPLi = r2.random(n0) < 0.03
        gate = r2.random(n0) > 0.2; PVi = r2.random(n0) > 0.05
        for anc in ("T", "pre"):
            A = stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, anchor=anc)
            L = stock_arrays_loop(idx, o_b, c_b, badb, n0, anchor=anc)
            for H in HS:
                assert (np.isfinite(A["G"][H]) == np.isfinite(L["G"][H])).all(), ("G", H, trial)
                worst = max(worst, float(np.nanmax(np.abs(A["G"][H] - L["G"][H]))))
                assert (A["BRK"][H] == L["BRK"][H]).all(), ("BRK", H, trial)
            assert (np.isfinite(A["RN"]) == np.isfinite(L["RN"])).all(), ("RN", anc, trial)
            worst = max(worst, float(np.nanmax(np.abs(A["RN"] - L["RN"]))))
        Wd = WRF.stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, wk, wf, wl)
        A20 = stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, hs=(20, 60), rn=20, anchor="T")
        for H in (20, 60):
            assert np.array_equal(np.isfinite(Wd["G"][H]), np.isfinite(A20["G"][H])) and np.nanmax(np.abs(Wd["G"][H] - A20["G"][H])) == 0
            assert (Wd["BRK"][H] == A20["BRK"][H]).all()
        assert (Wd["TR1"] == A20["TR1"]).all() and (Wd["POPT"] == A20["POPT"]).all()
        assert np.array_equal(np.isfinite(Wd["R20"]), np.isfinite(A20["RN"])) and np.nanmax(np.abs(Wd["R20"] - A20["RN"])) == 0
        D0 = stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, dry=True)
        assert all((np.isfinite(D0["G"][H]) == np.isfinite(A["G"][H])).all() and np.nanmax(np.abs(D0["G"][H])) == 0 for H in HS)
    assert worst < 1e-12
    msgs.append(f"F6 逐股陣列（R H20/60/120、斷點、rN 兩種錨點）＝ 逐根迴圈（最大差 {worst:.1e}）；H20/60、T＋1 可買、母體、r20 與 researchWR.stock_arrays 逐位元同；乾跑只留可算位置")
    # F7 不前視：截掉 T 之後的 K 棒不改 ≤ T 的 rN（兩種錨點）
    r2 = np.random.default_rng(5)
    idx = np.flatnonzero(r2.random(n0) > 0.05).astype(np.int64)
    c_b = 50 * np.exp(np.cumsum(r2.normal(0, 0.02, len(idx)))); o_b = c_b.copy(); badb = r2.random(len(idx)) < 0.02
    TRDi = np.ones(n0, bool); Oi = np.full(n0, 10.0); UPLi = np.zeros(n0, bool); gate = np.ones(n0, bool); PVi = np.ones(n0, bool)
    for anc in ("T", "pre"):
        A = stock_arrays(idx, o_b, c_b, badb, n0, TRDi, Oi, UPLi, gate, PVi, anchor=anc)
        cut = 200; kc = int(np.searchsorted(idx, cut, "right"))
        Ac = stock_arrays(idx[:kc], o_b[:kc], c_b[:kc], badb[:kc], n0, TRDi, Oi, UPLi, gate, PVi, anchor=anc)
        assert np.array_equal(np.isfinite(A["RN"][:cut + 1]), np.isfinite(Ac["RN"][:cut + 1]))
        assert np.nanmax(np.abs(A["RN"][:cut + 1] - Ac["RN"][:cut + 1])) == 0
    msgs.append("F7 配對量 rN（T 錨點、型態第一點錨點）截掉 T 之後的 K 棒不變（不前視）")
    return msgs


def freq_text(ok, cal, n0, cells):
    """照 researchWR_freq.run_freq 的寫法重排 events_<世界>.csv.gz 全文。"""
    allrows = []
    for cell in cells:
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


def check_events(mine, wn, freq_dir, sids_lim):
    ref = gzip.open(os.path.join(freq_dir, f"events_{wn}.csv.gz"), "rt", encoding="utf-8").read()
    if sids_lim is None:
        if mine != ref:
            raise SystemExit(f"⛔ {wn} 重新偵測 ≠ 已提交 events_{wn}.csv.gz（{len(mine)} vs {len(ref)} 字元）⇒ 中止（未算任何報酬）")
        return ref.count("\n") - 1, "逐字"
    a = pd.read_csv(io.StringIO(mine), dtype=str, keep_default_na=False)
    b = pd.read_csv(io.StringIO(ref), dtype=str, keep_default_na=False)
    b = b[b["sid"].isin(set(sids_lim))].reset_index(drop=True)
    if not (list(a.columns) == list(b.columns) and a.shape == b.shape and (a.values == b.values).all()):
        raise SystemExit(f"⛔ {wn} 重新偵測（--limit）≠ 已提交事件檔子集")
    return len(b), "逐列逐欄（--limit 子集）"


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    sid_, res = KF.stock_job(a)                            # ⭐ 頻率表同一支：事件、狀態
    if res is None:
        return sid, None
    X = WF.base(wn, sid)
    B = X["B"]; idx = X["idx"]; n0 = X["n0"]
    o_b = np.asarray(B["o"], float); c_b = np.asarray(B["c"], float)
    assert np.array_equal(X["df"]["close"].to_numpy(float)[idx], c_b), f"{sid} B['c'] ≠ df close"
    A = stock_arrays(idx, o_b, c_b, X["bad"], n0, X["TRD"], X["O"], X["UPL"], X["gate"], X["PV"], anchor="T", dry=DRY)
    A.pop("CSB"); A.pop("GAP"); A.pop("PV")
    return sid, {"ev": res["ev"], "A": A}


def fake_arm(M, H, ii, TT, p0, pend, moni_s, segnum, cellnum=0):
    """WR.fake_arm 原樣，r20 換 r60。"""
    POOL, DEC, G = M["POOL"], M["DEC"], M["G"][H]
    CS, CC = M["TAB"]
    order = np.lexsort((TT, ii)); ii_s, TT_s = ii[order], TT[order]
    stocks, starts = np.unique(ii_s, return_index=True)
    ends = np.r_[starts[1:], len(ii_s)]
    acc = np.zeros((REPS, 2, NCL, 2)); cnt = np.zeros((REPS, 2, 6), np.int64)
    cands = {}
    for i in stocks:
        cmask = M["VALID"][p0:pend + 1, i] & np.isfinite(M["RN"][p0:pend + 1, i]) & M["POPT"][p0:pend + 1, i]
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
                rng = np.random.default_rng([SEED_FAKE + r, M["CRC"][i], cellnum, segnum, ver])
                pick = np.sort(rng.choice(cand, size=m, replace=False))
                cnt[r, ver, 0] += m
                g1 = M["POPT"][pick, i]
                cnt[r, ver, 1] += int((~g1).sum()); pick = pick[g1]
                g2 = okH[pick, i]
                cnt[r, ver, 2] += int((~g2).sum()); pick = pick[g2]
                if len(pick) == 0:
                    continue
                cm, cc = WRF.ctrl_lookup(CS, CC, POOL, DEC, G, pick, np.full(len(pick), i))
                cnt[r, ver, 3] += int((cc < 0).sum()); cnt[r, ver, 4] += int((cc == 0).sum())
                g3 = cc > 0
                dX.append(G[pick[g3], i] - cm[g3]); TTs.append(pick[g3])
            if dX:
                dXa = np.concatenate(dX); Ta = np.concatenate(TTs)
                if len(dXa):
                    cl = clkey(Ta, H, p0, moni_s)
                    assert cl.max() < NCL
                    np.add.at(acc[r, ver, :, 0], cl, 1.0)
                    np.add.at(acc[r, ver, :, 1], cl, dXa)
    return acc, cnt


def sentence(cell, st, sg, early=False):
    nm = NAME[cell]; H = int(st["H"])
    tail = SENT_SELF + [SENT_ALL] + (NOTE_EARLY if early else [])
    rs = st["結果"]
    head = f"{nm}那天收盤判、隔天開盤買，之後 {H} 天比同一天、前 60 日走勢同一級距、當天沒觸發的其他股票"
    if rs == "樣本不足以分辨":
        s = f"{head}：樣本不足以分辨（n_eff＝{int(st.get('n_eff', 0) or 0)}）"
    else:
        pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(int(st["n_eff"])) if st.get("出口") == "出口②" else ""
        if rs == "結果①":
            s = "{}{}：分不出（每筆平均 X̄ {}，95% CI {} ～ {}）".format(pre, head, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
        else:
            x2 = st.get("假訊號_新預設_x2", 0) or 0
            warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
            verb = "多" if rs == "結果②" else "少"
            s = "{}{}{}：{} {}（95% CI {} ～ {}；扣成本 0.585% 後 X̄ {}）".format(warn, pre, head, verb, pct(abs(st["X̄"]))[1:], pct(st["lo"]),
                                                                       pct(st["hi"]), pct(st["X̄扣成本"]))
    seg = {"探索": "〔探索段・判定〕", "確認": "〔確認段・判定〕", "主全窗": "〔主全窗・參考〕", "早年": "〔早年・描述〕"}[sg]
    if cell != "J" or H != 20:
        seg = seg.replace("・判定", "・描述").replace("・參考", "・描述")
    role = "" if cell == "J" else "〔描述格、⛔ 不判、不計 N〕"
    return seg + role + s + "｜" + "；".join(tail)


def overlap_ext(wn, cal, kept_seg, sids):
    """G10：急跌錯殺、大盤大跌（J 保留事件）。kept_seg：[(j, T)]。"""
    n = len(kept_seg); out = {"保留": n}
    if not n:
        return out
    dates = np.array([str(d.date()) for d in cal])
    co = pd.read_csv("backtest/resultsCrashOversold/events.csv.gz", dtype=str, usecols=["sid", "日期t", "版面"])
    co = co[co["版面"] == ("main" if wn == "主" else "早年")]
    pos = cal.searchsorted(pd.to_datetime(co["日期t"]))
    inc = (pos < len(cal)) & (dates[np.minimum(pos, len(cal) - 1)] == co["日期t"].to_numpy())
    cop = {}
    for s_, p_ in zip(co["sid"].to_numpy()[inc], pos[inc]):
        cop.setdefault(s_, []).append(int(p_))
    cop = {k: np.array(sorted(v)) for k, v in cop.items()}
    same = sum(1 for j, T in kept_seg if sids[j] in cop and np.isin(T, cop[sids[j]]))
    near = sum(1 for j, T in kept_seg if sids[j] in cop and bool((np.abs(cop[sids[j]] - T) <= 20).any()))
    out.update({"急跌錯殺_同檔同日": same, "急跌錯殺_同檔同日_比例": same / n, "急跌錯殺_同檔±20": near, "急跌錯殺_同檔±20_比例": near / n,
                "急跌錯殺_來源": "resultsCrashOversold/events.csv.gz 全部候選列（F1／公司事件前）"})
    md = pd.read_csv("backtest/resultsMktDrop/events.csv", dtype=str)
    md = md[md["定義"] == "q2"]
    for nm, sub in (("大盤大跌q2", md), ("大盤大跌q2波段第一天", md[md["波段第一天"] == "True"])):
        p_ = cal.searchsorted(pd.to_datetime(sub["日期"]))
        okm = (p_ < len(cal)) & (dates[np.minimum(p_, len(cal) - 1)] == sub["日期"].to_numpy())
        P_ = np.array(sorted(set(p_[okm].tolist())), np.int64)
        Ts = np.array([T for _, T in kept_seg], np.int64)
        s1 = int(np.isin(Ts, P_).sum())
        k_ = np.searchsorted(P_, Ts, "right") - 1
        s2 = int(((k_ >= 0) & (Ts - P_[np.clip(k_, 0, max(len(P_) - 1, 0))] <= 20)).sum()) if len(P_) else 0
        out.update({f"{nm}_同日": s1, f"{nm}_同日_比例": s1 / n, f"{nm}_之後20日內": s2, f"{nm}_之後20日內_比例": s2 / n,
                    f"{nm}_世界內事件日數": int(len(P_))})
    return out


# ═════════════ 主程式 ═════════════
def main():
    global DRY
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    DRY = bool(a.dry)
    if a.limit and not DRY:
        raise SystemExit("⛔ --limit 只准與 --dry 同用（不准做含報酬的小樣本試跑）")
    t0 = time.time()
    out = DRY_OUT if DRY else OUT
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = WF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑（R 全寫 0）' if DRY else '本體'}開跑 {now_tpe()}")
    fx = fixture_common()
    for m_ in fx:
        log("✅ " + m_)
    J = {"性質": "KDJ 三週期共振 seq1 事件層正式跑（單筆層；判定 J 一格 H20，探索、確認各自報；H60／H120 描述）" + ("〔乾跑：R 全 0〕" if DRY else ""),
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq394 第 3 題、seq398 發號、seq399 核准開跑；N_前段 ＋1；標籤照常",
         "方法": "PREREG型態全量 seq3 事件層（AT 世界落地 researchWR V1～V13；配對量 r60）", "Bonferroni": {"族N": N_FAM, "z": Z_BONF},
         "成本": COST, "fixture": fx, "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DIFF = []; OVL = []; BY = []; FK = []; FACC = {}
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
        log(f"[{wn}] 段 " + "｜".join(f"{k} {cal[p].date()}～{cal[q].date()}" for k, (p, q) in win.items()))
        sids = W["sids"]; S = len(sids); ix = W["ix"]
        run_sids = sids[:a.limit] if a.limit else sids
        VALID = np.zeros((n0, S), bool); RNm = np.full((n0, S), np.nan); TR1 = np.zeros((n0, S), bool); POPT = np.zeros((n0, S), bool)
        G = {H: np.full((n0, S), np.nan) for H in HS}; BRK = {H: np.ones((n0, S), bool) for H in HS}
        ok = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in run_sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]; A = r["A"]
                    VALID[:, j] = A["valid"]; RNm[:, j] = A["RN"]; TR1[:, j] = A["TR1"]; POPT[:, j] = A["POPT"]
                    for H in HS:
                        G[H][:, j] = A["G"][H]; BRK[H][:, j] = A["BRK"][H]
                    ok[sid] = {"ev": r["ev"]}
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(run_sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(ok)} 檔｜{time.time() - t0:.0f}s")
        nl, how = check_events(freq_text(ok, cal, n0, CELLS), wn, FREQ, run_sids if a.limit else None)
        log(f"[查核1] {wn}：重新偵測與已提交頻率表 events_{wn}.csv.gz {how}相同（{nl:,} 列）")
        if "第一次讀報酬" not in J["時點"] and not DRY:
            J["時點"]["第一次讀報酬"] = now_tpe()
        RAW = {c: np.zeros((n0, S), bool) for c in CELLS}
        KEPT = {c: [] for c in CELLS}
        for s_, r in ok.items():
            j = ix[s_]
            for c in CELLS:
                for e in r["ev"][c]:
                    RAW[c][e["T"], j] = True
                    if e["st"] == "保留":
                        KEPT[c].append((j, e["T"]))
        bad2 = Counter()
        for c in CELLS:
            for j, T in KEPT[c]:
                if not POPT[T, j]:
                    bad2[f"{c} 保留但本支判閘外"] += 1
                if not TR1[T, j]:
                    bad2[f"{c} 保留但本支判 T+1 不可買"] += 1
        assert not bad2, bad2
        log("[查核2] 保留事件：本支矩陣判 T 當天母體、T＋1 可買（與頻率表 K1 一致）")
        BASED = POPT & VALID & np.isfinite(RNm)
        DEC = PC.dec_matrix(RNm, BASED)
        EW = {}
        for H in HS:
            Gz = np.nan_to_num(G[H])
            em = POPT & TR1 & np.isfinite(G[H])
            cnt_ = em.sum(axis=1); sm = np.where(em, Gz, 0.0).sum(axis=1)
            EW[H] = np.where(cnt_ > 0, sm / np.maximum(cnt_, 1), np.nan)
        moni = np.asarray(cal.year * 12 + cal.month)
        years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        crc = [zlib.crc32(s.encode("utf-8")) for s in sids]
        mk_all = np.array([W["mk"].get(s, "twse") for s in sids])
        log(f"[十分位、EW] 完成｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(ok),
              "閘": W["gate"], "壞根": W["bad_info"], "段": {sg: {"期間": f"{cal[p].date()}～{cal[q].date()}", "年": round((cal[q] - cal[p]).days / 365.25, 3)}
                                                           for sg, (p, q) in win.items()}}
        EVF = {}
        for c in CELLS:
            for H in HS:
                Gz = np.nan_to_num(G[H])
                POOL = BASED & TR1 & ~BRK[H] & np.isfinite(G[H]) & ~RAW[c]
                TAB = WRF.ctrl_tables(POOL, DEC, Gz)
                for sg, (p0, p1) in win.items():
                    moni_s = moni - moni[p0]
                    yrs = (cal[p1] - cal[p0]).days / 365.25
                    kept = sorted([x for x in KEPT[c] if p0 <= x[1] <= p1], key=lambda z: (z[1], sids[z[0]]))
                    ii = np.array([x[0] for x in kept], np.int64); TT = np.array([x[1] for x in kept], np.int64)
                    nk = len(kept)
                    beyond = TT + H > n0 - 1
                    Tc = np.minimum(TT, n0 - 1 - H)
                    rv = np.where(beyond, np.nan, RNm[Tc, ii]) if nk else np.zeros(0)
                    g = np.where(beyond, np.nan, G[H][Tc, ii]) if nk else np.zeros(0)
                    brk = np.where(beyond, True, BRK[H][Tc, ii]) if nk else np.zeros(0, bool)
                    cm, cc = WRF.ctrl_lookup(*TAB, POOL, DEC, G[H], Tc, ii) if nk else (np.zeros(0), np.zeros(0, np.int64))
                    dec_e = DEC[Tc, ii] if nk else np.zeros(0, np.int8)
                    why = np.full(nk, "有", dtype=object)
                    for q in range(nk):
                        if beyond[q]:
                            why[q] = EXC[0]
                        elif not np.isfinite(rv[q]):
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
                    ew = np.where(beyond, np.nan, EW[H][Tc]) if nk else np.zeros(0)
                    Xu = g - ew
                    st = cell_stats(Xv[okm], TT[okm], H, p0, moni_s)
                    st.update(trade_stats(g[okm], cm[okm]))
                    st.update({"保留": int(nk), "配對剔除": {k: int(v) for k, v in Counter(why[~okm].tolist()).items()},
                               "配對剔除數": int((~okm).sum()), "對照數_中位": float(np.median(cc[okm])) if okm.any() else None,
                               "對照數_最小": int(cc[okm].min()) if okm.any() else None,
                               "每年事件數(保留)": round(nk / yrs, 1), "每年事件數(配對後)": round(int(okm.sum()) / yrs, 1),
                               "相異檔數": int(len(set(ii[okm].tolist()))), "未配對_Xu": desc_ci(Xu[okm], TT[okm], H, p0, moni_s)})
                    mk = mk_all[ii] if nk else np.zeros(0, str)
                    st["上市"] = desc_ci(Xv[okm & (mk == "twse")], TT[okm & (mk == "twse")], H, p0, moni_s)
                    st["上櫃"] = desc_ci(Xv[okm & (mk == "tpex")], TT[okm & (mk == "tpex")], H, p0, moni_s)
                    yr = years[TT] if nk else np.zeros(0, int)
                    st["逐年"] = {str(y): {"保留": int((yr == y).sum()), "n": int((okm & (yr == y)).sum()),
                                         "X̄": float(Xv[okm & (yr == y)].mean()) if (okm & (yr == y)).any() else None}
                                for y in sorted(set(yr.tolist()))}
                    for y, qd in st["逐年"].items():
                        BY.append({"世界": wn, "段": sg, "格": c, "H": H, "年": y, **qd})
                    fr = pd.DataFrame({"sid": [sids[i] for i in ii], "market": mk, "T": dates[TT] if nk else [],
                                       "進場日": [dates[t + 1] for t in TT], "出場日": [dates[t + H] if t + H <= n0 - 1 else "" for t in TT],
                                       "r60": rv, "十分位": dec_e, "R": g, "對照平均": cm, "對照數": cc, "X": Xv, "EW": ew, "X_未配對": Xu,
                                       "分群": clkey(TT, H, p0, moni_s) if nk else [], "配對": why})
                    if c in ("J", "D"):
                        EVF[(sg, c, H)] = {"T": TT, "ok": okm, "X": Xv}
                    if c == "J" and H == 20:
                        pend = min(p1, n0 - 1 - H)
                        Mf = {"POOL": POOL, "TAB": TAB, "DEC": DEC, "G": G, "BRK": BRK, "TR1": TR1, "POPT": POPT, "VALID": VALID, "RN": RNm, "CRC": crc}
                        acc, cntf = fake_arm(Mf, H, ii, TT, p0, pend, moni_s, SEGNUM[sg])
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
                        st["過seq322門檻"] = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st.get("假訊號_新預設_x2", 99) <= 1
                                               and st.get("X̄扣成本", -1) > 0 and st.get("逐群中位與平均同號", False))
                    st["H"] = H
                    if c != "J":
                        st["身分"] = "另一讀法（只報）" if c == "J_週月暖機9根" else "描述格（⛔ 不判、不計 N）"
                    elif H != 20:
                        st["身分"] = f"H{H} 描述（⛔ 不判）"
                    else:
                        st["身分"] = {"探索": "判定格｜探索段判定", "確認": "判定格｜確認段判定", "主全窗": "判定格｜主全窗參考", "早年": "判定格｜早年描述"}[sg]
                    st["句子"] = sentence(c, st, sg, early=(wn == "早年"))
                    Wj["段"][sg][f"{c}_H{H}"] = st
                    fr.to_csv(os.path.join(out, "events", f"trades_{wn}_{sg}_{c}_H{H}.csv.gz"), index=False,
                              compression={"method": "gzip", "compresslevel": 6})
                    MAIN.append({"世界": wn, "段": sg, "格": c, "說明": NAME[c], "H": H, "身分": st["身分"], "期間": Wj["段"][sg]["期間"],
                                 **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("H", "身分", "句子")}, "句子": st["句子"]})
                    if c == "J" or H == 20:
                        log(f"  [{wn}/{sg}] {c} H{H}：保留 {nk} 配對 {st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} "
                            f"CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}" + (f" 假 x={st.get('假訊號_新預設_x2')}" if (c == "J" and H == 20) else "")
                            + f"｜{time.time() - t0:.0f}s")
                del POOL, TAB
        # ── J − D 差（G9）、重疊（G10）、逐年（G11）
        for sg, (p0, p1) in win.items():
            moni_s = moni - moni[p0]
            for H in HS:
                A1 = EVF[(sg, "J", H)]; A2 = EVF[(sg, "D", H)]
                k1 = clkey(A1["T"][A1["ok"]], H, p0, moni_s); k2 = clkey(A2["T"][A2["ok"]], H, p0, moni_s)
                d = PC.diff_stats(A1["X"][A1["ok"]], k1, A2["X"][A2["ok"]], k2)
                d = {{"差": "差(J−D)", "新": "X̄_J", "原": "X̄_D", "n新": "n_J", "n原": "n_D"}.get(k, k): v for k, v in d.items()}
                if "lo" in d:
                    d["標籤（描述）"] = "差的 CI 含 0" if d["lo"] <= 0 <= d["hi"] else ("J＞D" if d["差(J−D)"] > 0 else "J＜D")
                DIFF.append({"世界": wn, "段": sg, "H": H, **d})
            kp = [x for x in KEPT["J"] if p0 <= x[1] <= p1]
            ov = overlap_ext(wn, cal, kp, sids)
            fl = {}
            for e_ in [e for s_, r in ok.items() for e in r["ev"]["J"] if e["st"] == "保留" and p0 <= e["T"] <= p1]:
                for k_ in ("同日_日線KD(K≤30,%R件K格)", "±20_日線KD(K≤30,%R件K格)", "同日_%R(W格)", "±20_%R(W格)"):
                    fl[k_] = fl.get(k_, 0) + int(bool(e_[k_]))
            for k_, v in fl.items():
                ov[k_] = v; ov[k_ + "_比例"] = v / len(kp) if kp else None
            Wj["段"][sg]["重疊_J"] = ov
            OVL.append({"世界": wn, "段": sg, **{k: v for k, v in ov.items() if not isinstance(v, dict)}})
        yk = Counter(int(years[T]) for _, T in KEPT["J"])
        Wj["J保留逐年(全期)"] = {str(y): int(v) for y, v in sorted(yk.items())}
        J["世界"][wn] = Wj
        del VALID, RNm, TR1, POPT, G, BRK, RAW, DEC, BASED, EW
    # ── 空頭年占比（G11）
    allyr = Counter()
    for wn in ("主", "早年"):
        for y, v in J["世界"][wn]["J保留逐年(全期)"].items():
            allyr[int(y)] += v
    tot = sum(allyr.values())
    J["空頭年占比"] = {"J保留(兩世界全期)": tot, **{str(y): {"件數": allyr.get(y, 0), "占比": allyr.get(y, 0) / tot if tot else None} for y in BEAR_YEARS},
                    "三年合計占比": sum(allyr.get(y, 0) for y in BEAR_YEARS) / tot if tot else None, "逐年": {str(k): v for k, v in sorted(allyr.items())}}
    # ── 判定（J H20；探索、確認各自）
    jd = {}
    for sg in JUDGE_SEGS + ("主全窗",):
        st = J["世界"]["主"]["段"][sg]["J_H20"]
        jd[sg] = {"身分": "判定" if sg in JUDGE_SEGS else "參考", "結果": st["結果"], "出口": st.get("出口"), "n": st["n"], "n_eff": st.get("n_eff"),
                  "X̄": st.get("X̄"), "95%CI": [st.get("lo"), st.get("hi")], "假訊號x/30(新預設)": st.get("假訊號_新預設_x2"),
                  "X̄−成本": st.get("X̄扣成本"), "逐月中位同號": st.get("逐群中位與平均同號"), "過seq322門檻": st.get("過seq322門檻"), "句子": st["句子"]}
    J["判定"] = jd
    both322 = all(jd[sg]["過seq322門檻"] for sg in JUDGE_SEGS)
    J["整件"] = {"兩段皆過seq322": both322, "結論": ("兩段皆過 seq322 ⇒ 可另起組合層登錄（單筆層通過 ≠ 組合會贏 0050）" if both322
                                                 else "未兩段皆過 seq322 ⇒ ⛔ 不另起組合層"), "標籤上限": "照常"}
    # ── 先驗（登錄 §六，⛔ 不改）
    fq = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    rat = {sg: fq["判斷摘要"][f"主/{sg}"]["J÷D"] for sg in JUDGE_SEGS}
    ne_ok = {sg: bool((jd[sg]["n_eff"] or 0) >= 30) for sg in JUDGE_SEGS}
    J["先驗"] = {
        "① 兩段 n_eff ≥ 30（約五成）": {sg: {"n_eff(配對後)": jd[sg]["n_eff"], "中": ne_ok[sg]} for sg in JUDGE_SEGS} | {"中": all(ne_ok.values())},
        "② 若可判，兩段皆 ① 或 ③（約七成五）": {sg: {"結果": jd[sg]["結果"]} for sg in JUDGE_SEGS}
                                         | {"中": bool(all(ne_ok.values()) and all(jd[sg]["結果"] in ("結果①", "結果③") for sg in JUDGE_SEGS))},
        "③ 不與日線 KD 退化（本件 ÷ 日線 KD ＜ 50%）（約八成）": {sg: {"J÷D(保留，頻率表)": rat[sg]} for sg in JUDGE_SEGS}
                                                     | {"中": bool(all(v < 0.5 for v in rat.values()))}}
    J["N"] = {"本件判定格": 1, "描述格、另一讀法、J−D 差、H60／H120": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "KDJ3_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DIFF).to_csv(os.path.join(out, "KDJ3_diff.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(OVL).to_csv(os.path.join(out, "KDJ3_overlap.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    keys = list(FACC)
    np.savez_compressed(os.path.join(out, "fake_acc.npz"), keys=np.array(keys), acc=np.stack([FACC[k][0] for k in keys]),
                        cnt=np.stack([FACC[k][1] for k in keys]))
    J["J−D"] = DIFF; J["重疊"] = OVL
    json.dump(J, open(os.path.join(out, "KDJ3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'X̄', '假訊號x/30(新預設)', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"[先驗] " + "｜".join(f"{k} 中={v['中']}" for k, v in J["先驗"].items()))
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
