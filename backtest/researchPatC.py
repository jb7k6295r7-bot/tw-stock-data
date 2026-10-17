# -*- coding: utf-8 -*-
"""型態補條件 C 組 seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 8827942d8c296851，2026-10-17 09:38；裁定 seq360 §二 N_前段 ＋2、
seq361 發號、seq363 撤回 seq362：K1 判定格＝原登錄文獻版四條、⛔ 不改；研究二原版杯柄改當對照格並報）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchPatC_freq（事件偵測、剔除）、researchAscTri_freq（世界）、research11 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatC [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatC_check
輸出 backtest/resultsPatC/：PatC.json、PatC_main.csv（主表）、PatC_desc.csv（描述格）、PatC_compare.csv（K1 對 K1b、K2 對 K2b）、
    by_year.csv、fake_reps.csv、fake_acc.npz、events/events_<世界>_<段>_<格>_H<H>.csv.gz（逐筆 R、對照、X）、run.log

格：判定 K1 ＝ 杯柄＋柄四條（文獻版，H20）、K2 ＝ W 底＋左谷量＞右谷量（H20）；對照格（seq363 並報、⛔ 不計 N）K1b ＝ 研究二原版杯柄、
    K2b ＝ W 底底版；描述（⛔ 不判）：嚴版（研究二原版 ∩ 四條）、K1 多出來的（K1 ∖ K1b）、Adam／Eve 四分類（含 Eve&Eve）、量遞減、全部 H60。

═══ 讀法（P 標；方法全沿用 PREREG型態全量 seq3 ＝ researchPatAll.py 的 C1～C8 價格結構版；⛔ 在讀任何本件報酬之前寫死；
     ★＝兩種讀法擇一，〔 〕內為另一讀法、⛔ 不另跑，除非註明「並報」）═══
 P1 事件 ＝ 頻率表同一批：逐股呼叫 researchPatC_freq.stock_job 原樣（世界 ＝ researchAscTri_freq.load_world），
    ⭐ 每個 (世界, 段, 格) 依頻率表寫法排成表、與已提交的 resultsPatC/freq/events_*.csv.gz 逐列逐欄比，任一不同 ⇒ 中止、⛔ 不算報酬。
    判定母體 ＝ 狀態_H20（H60 用 狀態_H60）＝「保留」者。
 P2 R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1（load_bars 的 df；PatAll C1）。成本兩邊相同、相減抵銷 ⇒ 本體 ⛔ 不扣；
    seq322 門檻「扣成本後仍 ＞ 0」另欄 ＝ d×X̄ − 0.585%（evaluate.COST；PatAll_cost 同口徑）。
 P3 對照（登錄 §二 ⇒ PatAll §五 價格結構、C3 ★ 讀法原樣）：配對量 ＝ r60 ＝ c[first−1] ÷ c[first−61] − 1（有效 K 棒 ＝ 還原收盤非缺值；
    first：杯柄 ＝ 左杯口 L、W 底 ＝ 左谷 L1，同頻率表 Q3）⇒ 橫斷面 ＝ first 那一天；十分位 ＝ rank(method="first") 等分 10（PatAll decile_int 同式）。
    ★ 本件母體是 point-in-time（UG.pit_valid、GATE_V2 開；頻率表 Q3 第一道剔除）⇒ 十分位橫斷面 ＝ first 當天 pit_valid ∧ 有效 K 棒 ∧ r60 可算；
      對照池另要求 pit_valid[T]〔另一讀法：PatAll 的靜態 gate3，不看 pit_valid〕。
    對照股 ＝ 錨點日同十分位、T 有有效 K 棒、T 當天【原始】偵測沒有該格（不論合併／剔除；原始 ＝ 頻率表事件檔任何狀態）、
    T＋1 可成交（有成交、開盤非缺且 ＞ 0、非開盤漲停、非開盤跌停 ＝ 頻率表 Q3 同旗標）、[事件 first, T＋H] 該對照股無硬斷點
    （頻率表 brk 同式：區間內有壞 K 棒，或 T＋H 前最後一根 K 棒到 T＋H 已缺 ≥ 5 日且之後還有成交）、R 可算 ⇒ 等權平均；自己不算。
    ⛔ 不加事前門檻（PatAll C3）。
 P4 錨點 r60 不可算（first 前不足 61 根）或配對格當天沒有對照股 ⇒ 該事件剔除並計數（PatAll C4）。
 P5 未配對描述：EW_H(T) ＝ T 當天 pit_valid ∧ R 可算的全部股票之 R 等權平均；X_u ＝ R − EW。
 P6 判定量 ＝ d × X̄（d ＝ ＋1）。CI：H20 ＝ T 所在曆月分群、H60 ＝ (T − 段起點)//60 分群；CR0（research11.cl_stats）、1.96；
    非重疊 SE ＝ 20／60 日區段平均的標準差 ÷ √區段數（第二欄）。n_eff ＝ min(配對後事件數, 有事件的分群數)；
    ＜30 ⇒ 樣本不足以分辨、30～99 ⇒ 出口②（句首「樣本中等」）、≥100 ⇒ 出口③；結果② ＝ CI 不含 0 且 ＞0、③ ＝ 不含 0 且 ＜0、① ＝ 含 0。
    ★ Bonferroni 族 ＝ 本登錄判定格 N ＝ 2（seq360 N_前段 ＋2）⇒ z ＝ Φ⁻¹(1 − 0.05／4)〔另一讀法：PatAll 的 0.05／180 ⇒ 並報一欄「參考」、⛔ 不用來判〕。
    判定只用【主全窗 H20】（PatAll 單一判定窗、頻率表 Q2）；探索／確認／早年 同法分報（標籤照印、⛔ 不改判定）；H60 只描述。
 P7 假訊號臂（PatAll C8 價格結構版）：r ＝ 0…29；每檔、每格、每段（H20）：n ＝ 該檔保留真事件數；可抽日 ＝ 該檔有效 K 棒、T ∈ [段起點, min(段尾, 資料尾 − H)]；
    新預設 ＝ 排除「存在該格保留真事件 T_r ∈ [T − 20, T]」的日子；不排除版並列描述；不放回抽 n 天（不足 ⇒ 全取、另報）；⛔ 不合併。
    假事件 first ＝ 把該檔真事件（依 T 排序）的「first 到 T 的有效 K 棒根數」依序配給抽到的日子（依 T 排序）。
    之後同一套剔除 ★ 加 pit_valid[T]（頻率表 Q3 第一道；PatAll 母體靜態所以沒有）→ [first, T＋H] 硬斷點 → T＋1 不可成交（⛔ 不補抽）、
    同一套對照（P3；自己從自己的對照裡扣掉）、同分群、同判定式。種子 default_rng([20260927＋r, crc32(sid), 格序號, H, 版本])。
    格序號：K1＝0、K1b＝1、K2＝2、K2b＝3。x／30 ＝ 落結果② 的次數。結果② 且 x ≥ 2 ⇒ 句首「⚠ 隨機挑日子也有 x／30 次同樣過關。」（PatAll 同）。
 P8 K1 對 K1b（seq363「照文獻做會不會比本專案原本的杯柄好」）、K2 對 K2b：同窗、同 H，差 ＝ d×X̄(新) − d×X̄(原)；
    SE ＝ 曆月分群線性化（每月 Σ(x−x̄₁)/n₁ − Σ(y−ȳ₂)/n₂ 的平方和開根號；兩組重疊事件自動抵銷）、1.96；⛔ 不計 N、⛔ 不判（描述）。
 P9 描述格（⛔ 不判、不計 N）：嚴版 ＝ K1 保留事件中「同檔同 T 也是 K1b 保留事件」者（用 K1 的對照）〔另一讀法：重做對照、排除兩者交集的原始偵測〕；
    K1∖K1b ＝ 其餘；Adam／Eve 四組合與 Eve&Eve、量遞減（L1 量 ＞ A 量 ＞ L2 量）＝ K2、K2b 保留事件的子集（用母格的對照）；H60 全部描述。
 P10 seq322 門檻（登錄 §三）＝ 主全窗 H20 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ d×X̄ − 0.585% ＞ 0（四條全過才另起組合層登錄）。
 P11 結果句必附：「單筆層通過 ≠ 組合會贏 0050」；K1 另附「文獻版四條比本專案原版寬（筆數約 1.8 倍）」「柄 ≥5 日是型態線換算、非原文數字」；
    早年另附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPatC_freq as PCF             # noqa: E402  事件偵測＋剔除原樣（⛔ 只 import）
from backtest import researchAscTri_freq as AT            # noqa: E402  load_world 原樣
from backtest import research11 as R                      # noqa: E402  load_bars、cl_stats
from backtest import evaluate as E                        # noqa: E402  COST
from backtest import universe_gate as UG                  # noqa: E402

UG.set_gate_v2(True)

REG_SHA = PCF.REG_SHA
OUT = "backtest/resultsPatC"
FREQ = "backtest/resultsPatC/freq"
HS = (20, 60)
REPS, EXCL, SEED_FAKE = 30, 20, 20260927
NCL = 256
Z95 = 1.96
N_FAM = 2
Z_BONF = NormalDist().inv_cdf(1 - 0.05 / N_FAM / 2)
Z_BONF180 = NormalDist().inv_cdf(1 - 0.05 / 180 / 2)
COST = E.COST
RUN = ["K1", "K1b", "K2", "K2b"]
VNUM = {"K1": 0, "K1b": 1, "K2": 2, "K2b": 3}
NAME = {"K1": "杯柄＋柄四條（文獻版）", "K1b": "研究二原版杯柄（對照格）", "K2": "W 底＋左谷量＞右谷量", "K2b": "W 底底版（對照格）"}
ROLE = {"K1": "判定格", "K2": "判定格", "K1b": "對照格（seq363 並報、不計 N）", "K2b": "對照格（並報、不計 N）"}
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
SENT_K1 = ["文獻版四條比本專案原版寬（筆數約 1.8 倍）", "柄 ≥5 日是型態線換算、非原文數字"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
_X: dict = {}       # 子行程共用（fork）
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 小工具（PatAll 同式；fixture 也測）═════════════
def decile_int(v):
    m = len(v)
    order = np.argsort(v, kind="stable")
    rank = np.empty(m, np.int64); rank[order] = np.arange(1, m + 1)
    lab = np.zeros(m, np.int8)
    for j in range(1, 10):
        lab += (10 * (rank - 1) > j * (m - 1)).astype(np.int8)
    return lab


def dec_matrix(M, base):
    out = np.full(M.shape, -1, np.int8)
    for t in range(M.shape[0]):
        idx = np.flatnonzero(base[t])
        if len(idx) < 10:
            continue
        out[t, idx] = decile_int(M[t, idx])
    return out


def excl_past(cand, Tk, excl=EXCL):
    if len(Tk) == 0 or len(cand) == 0:
        return cand
    k = np.searchsorted(Tk, cand, side="right") - 1
    prev = np.where(k >= 0, Tk[np.clip(k, 0, len(Tk) - 1)], -10 ** 9)
    return cand[~((k >= 0) & (cand - prev <= excl))]


def verdict(m, se, n_eff):
    if n_eff < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if n_eff < 100 else "出口③"
    lo, hi = m - Z95 * se, m + Z95 * se
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果②" if m > 0 else "結果③")


def agg_eval(acc):
    nn = acc[:, 0]; S = acc[:, 1]; N = nn.sum()
    if N == 0:
        return None
    m = S.sum() / N
    se = float(np.sqrt(((S - nn * m) ** 2).sum()) / N)
    ne = int(min(N, (nn > 0).sum()))
    ex, rs = verdict(m, se, ne)
    return {"n": int(N), "平均": float(m), "lo": m - Z95 * se, "hi": m + Z95 * se, "n_eff": ne, "出口": ex, "結果": rs}


def clkey(T, H, p0, moni):
    T = np.asarray(T, np.int64)
    return moni[T] if H != 60 else (T - p0) // 60


def cell_stats(dx, T, H, p0, moni):
    dx = np.asarray(dx, float); T = np.asarray(T, np.int64); n = len(dx)
    if n == 0:
        return {"n": 0, "出口": "出口①", "結果": "樣本不足以分辨", "n_eff": 0}
    o = {"n": int(n), "dX̄": float(dx.mean()), "中位": float(np.median(dx)), "勝率": float((dx > 0).mean()),
         "最差": float(dx.min()), "p10": float(np.percentile(dx, 10)), "p90": float(np.percentile(dx, 90))}
    key = clkey(T, H, p0, moni)
    cs = R.cl_stats(dx, key)
    assert abs(cs["mean"] - o["dX̄"]) < 1e-15
    se = cs["se"]; ng = cs["months"]
    blk = (T - p0) // (20 if H == 20 else 60)
    bm = pd.Series(dx).groupby(blk).mean()
    se2 = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    ne = int(min(n, ng))
    ex, rs = verdict(o["dX̄"], se, ne)
    m = o["dX̄"]
    o.update(se=se, lo=m - Z95 * se, hi=m + Z95 * se, 群數=int(ng), 分群單位=("曆月" if H == 20 else "60日區段"),
             bonf_lo=m - Z_BONF * se, bonf_hi=m + Z_BONF * se, bonf不含0=bool(m - Z_BONF * se > 0 or m + Z_BONF * se < 0),
             bonf180_lo=m - Z_BONF180 * se, bonf180_hi=m + Z_BONF180 * se,
             se_非重疊=se2, lo_非重疊=m - Z95 * se2, hi_非重疊=m + Z95 * se2, 非重疊區段數=int(len(bm)),
             n_eff=ne, 出口=ex, 結果=rs, 扣成本=m - COST, CI下界扣成本=m - Z95 * se - COST)
    return o


def diff_stats(x1, k1, x2, k2):
    """兩組（可重疊）平均差、曆月分群線性化 SE（P8）。"""
    x1 = np.asarray(x1, float); x2 = np.asarray(x2, float)
    n1, n2 = len(x1), len(x2)
    if n1 == 0 or n2 == 0:
        return {"n新": n1, "n原": n2}
    m1, m2 = x1.mean(), x2.mean()
    a = pd.Series(x1 - m1).groupby(np.asarray(k1)).sum() / n1
    b = pd.Series(x2 - m2).groupby(np.asarray(k2)).sum() / n2
    d = a.sub(b, fill_value=0.0)
    se = float(np.sqrt((d ** 2).sum()))
    return {"n新": n1, "n原": n2, "新": float(m1), "原": float(m2), "差": float(m1 - m2), "se": se,
            "lo": float(m1 - m2 - Z95 * se), "hi": float(m1 - m2 + Z95 * se), "群數": int(len(d)),
            "標籤（描述）": "差的 CI 含 0" if (m1 - m2 - Z95 * se) <= 0 <= (m1 - m2 + Z95 * se) else ("新＞原" if m1 > m2 else "新＜原")}


def desc_ci(x, T, H, p0, moni):
    x = np.asarray(x, float); T = np.asarray(T, np.int64); ok = np.isfinite(x); x, T = x[ok], T[ok]
    if len(x) == 0:
        return {"n": 0}
    o = {"n": int(len(x)), "平均": float(x.mean()), "中位": float(np.median(x)), "勝率": float((x > 0).mean())}
    if len(x) < 2:
        return o
    cs = R.cl_stats(x, clkey(T, H, p0, moni))
    ne = int(min(len(x), cs["months"]))
    ex, rs = verdict(cs["mean"], cs["se"], ne)
    o.update(lo=cs["lo"], hi=cs["hi"], n_eff=ne, 標籤=rs + "（描述、⛔ 不判）")
    return o


# ═════════════ 對照（單一事件；真／假共用）═════════════
def s_one(X, base_row, A, H, i, T, f):
    """⇒ (對照平均, 對照數)；對照數 −1 ＝ 錨點量不可算。base_row ＝ BASE[cell,H][T]（pit∧有效∧T+1 可成交∧R 可算∧當天無原始偵測）。"""
    di = A[f, i]
    if di < 0:
        return np.nan, -1
    b = T + H
    pb = X["CSB"][b] - (X["CSB"][f - 1] if f > 0 else 0)
    m = base_row & (A[f] == di) & (pb == 0) & ~X["GAP"][b]
    m[i] = False
    cnt = int(m.sum())
    return (float(X["G"][H][T][m].mean()) if cnt else np.nan), cnt


def own_brk(X, i, f, b):
    pb = X["CSB"][b, i] - (X["CSB"][f - 1, i] if f > 0 else 0)
    return bool(pb > 0 or X["GAP"][b, i])


# ═════════════ 逐股（fork 子行程）═════════════
def stock_job(a):
    wn, sid = a
    sid_, res = PCF.stock_job(a)                          # ⭐ 頻率表同一支：事件、剔除狀態
    if res is None:
        return sid, None
    W = PCF._G[wn]; cal = W["cal"]; n0 = W["n0"]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    cf = df["close"].to_numpy(float); of = df["open"].to_numpy(float)
    valid = np.isfinite(cf); bars = np.flatnonzero(valid); cb = cf[bars]
    cff = pd.Series(cf).ffill().to_numpy()
    okO1 = np.zeros(n0, bool); okO1[:-1] = valid[1:] & np.isfinite(of[1:]) & (np.nan_to_num(of[1:]) > 0)
    G = {}
    for H in HS:
        g = np.full(n0, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            g[:n0 - H] = np.where(okO1[:n0 - H], cff[H:] / of[1:n0 - H + 1] - 1.0, np.nan)
        G[H] = g
    A60 = np.full(n0, np.nan)
    j = np.arange(len(bars)); jj = j[j >= 61]
    with np.errstate(invalid="ignore", divide="ignore"):
        A60[bars[jj]] = cb[jj - 1] / cb[jj - 61] - 1.0
    # 壞根（頻率表 stock_job 同式）⇒ 日曆位置
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    badcal = np.zeros(n0, bool); badcal[idx[bad]] = True
    csb = np.cumsum(badcal).astype(np.int32)
    # GAP[p]：p 前最後一根 K 棒（load_bars idx）到 p 已缺 ≥5 日且之後還有成交（頻率表 brk 第二條）
    kH = np.searchsorted(idx, np.arange(n0), "right") - 1
    gap = np.zeros(n0, bool)
    okk = (kH >= 0) & (kH < nb - 1)
    p = np.arange(n0)[okk]; kk = kH[okk]
    gap[p] = (idx[kk + 1] - idx[kk] - 1 >= 5) & (p - idx[kk] >= 5)
    return sid, {"rows": res["rows"], "valid": valid, "G": G, "A60": A60, "csb": csb, "gap": gap, "bars": bars.astype(np.int32)}


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(7)
    n, S = 300, 40
    X = {"G": {H: rng.normal(0, 0.1, (n, S)) for H in HS}, "CSB": np.cumsum(rng.random((n, S)) < 0.01, axis=0).astype(np.int32),
         "GAP": rng.random((n, S)) < 0.02}
    for H in HS:
        X["G"][H][n - H:] = np.nan
    A = rng.integers(-1, 3, (n, S)).astype(np.int8)
    BASE = rng.random((n, S)) < 0.8
    worst = 0.0; nchk = 0
    for H in HS:
        BH = BASE & np.isfinite(X["G"][H])
        for _ in range(300):
            t = int(rng.integers(70, n - H)); i = int(rng.integers(0, S)); f = int(t - rng.integers(0, 60))
            c1, n1 = s_one(X, BH[t].copy(), A, H, i, t, f)
            # 逐檔迴圈
            if A[f, i] < 0:
                assert n1 == -1; continue
            vals = []
            for q in range(S):
                if q == i or not BH[t, q] or A[f, q] != A[f, i]:
                    continue
                if own_brk(X, q, f, t + H):
                    continue
                vals.append(X["G"][H][t, q])
            assert n1 == len(vals), (n1, len(vals))
            if vals:
                worst = max(worst, abs(c1 - float(np.mean(vals))))
            nchk += 1
    assert worst < 1e-12
    msgs.append(f"F1 價格結構對照向量版 ＝ 逐檔迴圈（{nchk} 筆）最大差 {worst:.1e}")
    Xz = {"G": {H: np.zeros((n, S)) for H in HS}, "CSB": X["CSB"], "GAP": X["GAP"]}
    mx = 0.0
    for H in HS:
        for _ in range(200):
            t = int(rng.integers(70, n - H)); i = int(rng.integers(0, S)); f = int(t - rng.integers(0, 60))
            c1, n1 = s_one(Xz, BASE[t].copy(), A, H, i, t, f)
            if n1 > 0:
                mx = max(mx, abs(0.0 - c1))
    assert mx == 0.0
    msgs.append("F2 報酬全 0 的世界 ⇒ X ＝ 0")
    got = excl_past(np.array([79, 80, 99, 100, 101, 120, 121, 140]), np.array([100])).tolist()
    assert got == [79, 80, 99, 121, 140], got
    msgs.append("F3 假訊號排除只看過去 [T−20, T]")
    x = rng.normal(0, 1, 500); key = rng.integers(0, 40, 500)
    acc = np.zeros((NCL, 2)); np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a_ = agg_eval(acc); b_ = R.cl_stats(x, key)
    assert abs(a_["平均"] - b_["mean"]) < 1e-12 and abs(a_["lo"] - b_["lo"]) < 1e-12
    msgs.append("F4 假訊號分群彙總式 ＝ research11.cl_stats")
    d = diff_stats(x, key, x, key)
    assert abs(d["差"]) < 1e-15 and d["se"] < 1e-15
    msgs.append("F5 兩組相同 ⇒ 差 0、SE 0（重疊抵銷）")
    v = rng.normal(size=137)
    assert (decile_int(v) == pd.qcut(pd.Series(v).rank(method="first"), 10, labels=False).to_numpy()).all()
    msgs.append("F6 十分位整數式 ＝ pd.qcut(rank(first), 10)")
    for m in msgs:
        log("✅ " + m)
    return msgs


# ═════════════ 主程式 ═════════════
def freq_frame(rows, cal):
    rows = sorted(rows, key=lambda x: (x["T"], x["sid"]))
    return pd.DataFrame([{"sid": x["sid"], "T": str(cal[x["T"]].date()), "first": str(cal[x["first"]].date()),
                          "狀態_H20": x["st20"], "狀態_H60": x["st60"], **({"Adam/Eve": x["shape"], "量遞減": x["dec"]} if "shape" in x else {})}
                         for x in rows])


def fake_arm(X, A, cell, H, ev, p0, pend, moni, BASE):
    """ev：該格該段保留真事件（含配對失敗者，與 PatAll 同：n 取保留數）。"""
    idx = ev["i"]; T = ev["T"]; lag = ev["lag"]
    order = np.lexsort((T, idx))
    idx_s, T_s, lag_s = idx[order], T[order], lag[order]
    stocks, starts = np.unique(idx_s, return_index=True)
    ends = np.r_[starts[1:], len(idx_s)]
    acc = np.zeros((REPS, 2, NCL, 2)); cnt = np.zeros((REPS, 2, 6), np.int64)  # 抽出、剔除pit、剔除斷點／成交、配對格無對照股、可抽日不足、錨點不可算
    cands = {}
    for i in stocks:
        bars = X["BARS"][int(i)]
        cands[int(i)] = bars[(bars >= p0) & (bars <= pend)].astype(np.int64)
    G = X["G"][H]
    for r in range(REPS):
        for ver in (0, 1):
            dX = []; TT = []
            for i, a, b in zip(stocks, starts, ends):
                Tk = T_s[a:b]
                cand = cands[int(i)]
                if ver == 0:
                    cand = excl_past(cand, Tk)
                m = min(len(Tk), len(cand)); cnt[r, ver, 4] += len(Tk) - m
                if m == 0:
                    continue
                rng = np.random.default_rng([SEED_FAKE + r, X["CRC"][int(i)], VNUM[cell], H, ver])
                pick = np.sort(rng.choice(cand, size=m, replace=False))
                bars = X["BARS"][int(i)]
                for t, lg in zip(pick, lag_s[a:a + m]):
                    t = int(t); cnt[r, ver, 0] += 1
                    bi = int(np.searchsorted(bars, t))
                    if bi - lg < 0:
                        cnt[r, ver, 5] += 1; continue
                    f = int(bars[bi - lg])
                    if not X["PV"][t, i]:
                        cnt[r, ver, 1] += 1; continue
                    if own_brk(X, int(i), f, t + H) or not (X["TRD1"][t, i] and np.isfinite(G[t, i])):
                        cnt[r, ver, 2] += 1; continue
                    cm, c_ = s_one(X, BASE[t].copy(), A, H, int(i), t, f)
                    if c_ < 0:
                        cnt[r, ver, 5] += 1; continue
                    if c_ == 0:
                        cnt[r, ver, 3] += 1; continue
                    dX.append(float(G[t, i] - cm)); TT.append(t)
            if dX:
                cl = clkey(np.asarray(TT), H, p0, moni)
                assert cl.max() < NCL
                np.add.at(acc[r, ver, :, 0], cl, 1.0)
                np.add.at(acc[r, ver, :, 1], cl, np.asarray(dX))
    return acc, cnt


def sentence(cell, row, early=False):
    nm = NAME[cell].replace("（對照格）", ""); H = int(row["H"])
    tail = [SENT_ALL] + (SENT_K1 if cell == "K1" else []) + (NOTE_EARLY if early else [])
    rs = row["結果"]
    if rs == "樣本不足以分辨":
        s = f"{nm}之後 {H} 天：樣本不足以分辨（配對後 n_eff＝{int(row.get('n_eff', 0) or 0)}）"
        return s + "｜" + "；".join(tail)
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(int(row["n_eff"])) if row.get("出口") == "出口②" else ""
    if rs == "結果①":
        s = "{}{}之後 {} 天，比同樣事前走勢、沒出現型態的股票：測不出（d×X̄ {}，95% CI {} ～ {}）".format(pre, nm, H, pct(row["dX̄"]), pct(row["lo"]), pct(row["hi"]))
    else:
        x2 = row.get("假訊號_新預設_x2", 0) or 0
        warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
        if rs == "結果②":
            s = "{}{}{}之後 {} 天，比同樣事前走勢、沒出現型態的股票，照文獻實測方向多走 {}".format(warn, pre, nm, H, pct(abs(row["dX̄"]))[1:])
        else:
            s = "{}{}之後 {} 天，跟文獻實測方向相反：比對照組多跌 {}".format(pre, nm, H, pct(abs(row["dX̄"]))[1:])
        s += "（95% CI {} ～ {}）".format(pct(row["lo"]), pct(row["hi"]))
        s += ("；Bonferroni（0.05／{}）也不含 0 ⇒ 可單獨引用".format(N_FAM) if row.get("bonf不含0")
              else "；單格過關、但 Bonferroni（0.05／{}）下界含 0（⛔ 不單獨引用）".format(N_FAM))
    return s + "｜" + "；".join(tail)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out = OUT if a.limit is None else "/tmp/patc_try"
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = PCF.reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜本體開跑 {now_tpe()}")
    fx = selftest()
    J = {"性質": "型態補條件 C 組 seq1 事件層正式跑（單筆層；判定 K1、K2 各 H20）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq360 §二（N_前段 ＋2）、seq361 發號、seq363（K1 照文獻版、研究二原版改對照格並報）",
         "方法": "PREREG型態全量 seq3（sha b7b4a05af0341797）價格結構版 C1～C8", "Bonferroni": {"族N": N_FAM, "z": Z_BONF, "參考_N180_z": Z_BONF180},
         "成本": COST, "fixture": fx, "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DESC = []; CMP = []; BY = []; FK = []; FACC = {}
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in PCF.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 1 if y_ is None else int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1
            win[sg] = (p0, p1)
        W["win"] = win; PCF._G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        S = len(W["sids"]); ix = W["ix"]
        VALID = np.zeros((n0, S), bool); A60 = np.full((n0, S), np.nan)
        G = {H: np.full((n0, S), np.nan) for H in HS}
        CSB = np.zeros((n0, S), np.int32); GAP = np.zeros((n0, S), bool)
        BARS = [np.zeros(0, np.int32)] * S
        ROWS = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]
                    VALID[:, j] = r["valid"]; A60[:, j] = r["A60"]; CSB[:, j] = r["csb"]; GAP[:, j] = r["gap"]; BARS[j] = r["bars"]
                    for H in HS:
                        G[H][:, j] = r["G"][H]
                    ROWS[sid] = r["rows"]
                if (k_ + 1) % 300 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(ROWS)} 檔｜{time.time() - t0:.0f}s")
        PV = np.asarray(W["PV"], bool)[:, :n0].T.copy()
        TRD = W["TRD"]; O = W["O"][:, :n0]; UPL = W["UPL"]; DNL = W["DNL"]
        TRD1 = np.zeros((n0, S), bool)
        with np.errstate(invalid="ignore"):
            TRD1[:-1] = (TRD[:, 1:] & np.isfinite(O[:, 1:]) & (np.nan_to_num(O[:, 1:]) > 0) & ~UPL[:, 1:] & ~DNL[:, 1:]).T
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐列逐欄）
        nchk = 0
        for sg in win:
            for cell in PCF.CELLS:
                rows = [x for s_ in ROWS for x in ROWS[s_][(sg, cell)]]
                mine = freq_frame(rows, cal) if rows else pd.DataFrame()
                p_ = os.path.join(FREQ, f"events_{wn}_{sg}_{cell}.csv.gz")
                if not os.path.exists(p_):
                    assert len(mine) == 0, p_; continue
                ref = pd.read_csv(p_, dtype=str, keep_default_na=False)
                if a.limit:
                    ref = ref[ref["sid"].isin(set(sids))].reset_index(drop=True)
                same = list(ref.columns) == list(mine.columns) and ref.shape == mine.shape and (ref.values == mine.astype(str).values).all()
                if not same:
                    raise SystemExit(f"⛔ {wn}/{sg}/{cell} 重新偵測 ≠ 已提交事件檔（{len(mine)} vs {len(ref)}）⇒ 中止（未算任何報酬）")
                nchk += len(ref)
        log(f"[查核1] {wn}：重新偵測與已提交頻率表事件檔逐列逐欄相同（{nchk:,} 列）")
        # ── 原始偵測（各格；任何狀態）、狀態查核（斷點、T+1）
        RAW = {}
        for cell in RUN:
            M = np.zeros((n0, S), bool)
            for s_ in ROWS:
                j = ix[s_]
                for sg in win:
                    for x in ROWS[s_][(sg, cell)]:
                        M[x["T"], j] = True
            RAW[cell] = M
        X = {"G": G, "CSB": CSB, "GAP": GAP, "PV": PV, "TRD1": TRD1, "BARS": BARS,
             "CRC": [zlib.crc32(s.encode("utf-8")) for s in W["sids"]]}
        bad_st = Counter()
        for s_ in ROWS:
            j = ix[s_]
            for sg in win:
                for cell in RUN:
                    for x in ROWS[s_][(sg, cell)]:
                        for H in HS:
                            st = x[f"st{H}"]
                            if st == "保留":
                                if own_brk(X, j, x["first"], x["T"] + H) or not TRD1[x["T"], j] or not PV[x["T"], j] or not np.isfinite(G[H][x["T"], j]):
                                    bad_st["保留但本支判不可用"] += 1
                            elif st == "剔除_硬斷點":
                                if not own_brk(X, j, x["first"], x["T"] + H):
                                    bad_st["硬斷點但本支判無斷點"] += 1
        assert not bad_st, bad_st
        log("[查核2] 保留事件：本支斷點矩陣無斷點、T＋1 可成交、pit_valid、R 可算；頻率表「剔除_硬斷點」本支全部判有斷點")
        BASEP = PV & VALID & np.isfinite(A60)
        DECA = dec_matrix(A60, BASEP)
        del A60
        EW = {}
        for H in HS:
            gm = np.where(PV, G[H], np.nan)
            with np.errstate(invalid="ignore"):
                c_ = np.isfinite(gm).sum(axis=1); s2 = np.nansum(gm, axis=1)
            EW[H] = np.where(c_ > 0, s2 / np.maximum(c_, 1), np.nan)
            del gm
        moni = np.asarray(cal.year * 12 + cal.month)
        years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        log(f"[十分位、EW] 完成｜第一次讀報酬 {J['時點']['第一次讀報酬']}｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(ROWS),
              "閘": W["gate"], "壞根": W["bad_info"], "段": {}}
        for sg, (p0, p1) in win.items():
            moni_s = moni - moni[p0]
            segj = {}; EVF = {}
            for cell in RUN:
                for H in HS:
                    BASE = PV & VALID & TRD1 & np.isfinite(G[H]) & ~RAW[cell]
                    ev = [(ix[s_], x) for s_ in ROWS for x in ROWS[s_][(sg, cell)] if x[f"st{H}"] == "保留"]
                    ev.sort(key=lambda z: (z[1]["T"], z[1]["sid"]))
                    ii = np.array([e[0] for e in ev], np.int64); TT = np.array([e[1]["T"] for e in ev], np.int64)
                    FF = np.array([e[1]["first"] for e in ev], np.int64)
                    lag = np.array([int(np.searchsorted(BARS[i], t)) - int(np.searchsorted(BARS[i], f)) for i, t, f in zip(ii, TT, FF)], np.int64)
                    g = G[H][TT, ii] if len(ev) else np.zeros(0)
                    assert np.isfinite(g).all()
                    ctrl = np.full(len(ev), np.nan); cc = np.zeros(len(ev), np.int64)
                    for q in range(len(ev)):
                        ctrl[q], cc[q] = s_one(X, BASE[TT[q]].copy(), DECA, H, int(ii[q]), int(TT[q]), int(FF[q]))
                    why = np.where(cc > 0, "有", np.where(cc < 0, "錨點量不可算", "配對格無對照股"))
                    Xv = g - ctrl; dX = 1.0 * Xv; ok = np.isfinite(Xv)
                    ew = EW[H][TT] if len(ev) else np.zeros(0); Xu = g - ew
                    st = cell_stats(dX[ok], TT[ok], H, p0, moni_s)
                    st.update({"保留": int(len(ev)), "配對剔除": dict(Counter(why[~ok].tolist())), "配對剔除數": int((~ok).sum()),
                               "對照數_中位": float(np.median(cc[ok])) if ok.any() else None, "對照數_最小": int(cc[ok].min()) if ok.any() else None,
                               "R̄": float(g[ok].mean()) if ok.any() else None, "對照R̄": float(ctrl[ok].mean()) if ok.any() else None,
                               "未配對_dXu": desc_ci(Xu[ok], TT[ok], H, p0, moni_s), "相異檔數": int(len(set(ii[ok].tolist())))})
                    mk = np.array([W["mk"].get(W["sids"][i], "twse") for i in ii]) if len(ev) else np.zeros(0, str)
                    st["上市"] = desc_ci(dX[ok & (mk == "twse")], TT[ok & (mk == "twse")], H, p0, moni_s)
                    st["上櫃"] = desc_ci(dX[ok & (mk == "tpex")], TT[ok & (mk == "tpex")], H, p0, moni_s)
                    yr = years[TT] if len(ev) else np.zeros(0, int)
                    st["逐年"] = {str(y): {"n": int((ok & (yr == y)).sum()), "dX̄": float(dX[ok & (yr == y)].mean()) if (ok & (yr == y)).any() else None}
                                for y in sorted(set(yr.tolist()))}
                    for y, q in st["逐年"].items():
                        BY.append({"世界": wn, "段": sg, "格": cell, "H": H, "年": y, **q})
                    shape = np.array([e[1].get("shape", "") for e in ev]); dec = np.array([bool(e[1].get("dec", False)) for e in ev])
                    fr = pd.DataFrame({"sid": [W["sids"][i] for i in ii], "market": mk, "T": dates[TT] if len(ev) else [], "first": dates[FF] if len(ev) else [],
                                       "lag": lag, "R": g, "對照平均": ctrl, "對照數": cc, "X": Xv, "dX": dX, "EW": ew, "X_未配對": Xu,
                                       "分群": clkey(TT, H, p0, moni_s) if len(ev) else [], "配對": why, "Adam/Eve": shape, "量遞減": dec})
                    EVF[(cell, H)] = {"fr": fr, "i": ii, "T": TT, "lag": lag, "ok": ok, "dX": dX}
                    # 假訊號臂（H20）
                    if H == 20:
                        pend = min(p1, n0 - 1 - H)
                        acc, cntf = fake_arm(X, DECA, cell, H, {"i": ii, "T": TT, "lag": lag}, p0, pend, moni_s, BASE)
                        FACC[f"{wn}|{sg}|{cell}|H{H}"] = (acc, cntf)
                        for ver, vn in ((0, "新預設"), (1, "不排除")):
                            res_ = [agg_eval(acc[r_, ver]) for r_ in range(REPS)]
                            st[f"假訊號_{vn}_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                            st[f"假訊號_{vn}_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                            st[f"假訊號_{vn}_平均dX"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                            c2 = cntf[:, ver].sum(axis=0)
                            st[f"假訊號_{vn}_帳"] = {"抽出": int(c2[0]), "剔除_pit無效": int(c2[1]), "剔除_斷點或T+1": int(c2[2]),
                                                  "配對格無對照股": int(c2[3]), "可抽日不足": int(c2[4]), "錨點不可算": int(c2[5])}
                            for r_, q in enumerate(res_):
                                FK.append({"世界": wn, "段": sg, "格": cell, "H": H, "版本": vn, "r": r_,
                                           **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                    st["H"] = H
                    if H == 60:
                        st["身分"] = "H60 描述（⛔ 不判）"
                    else:
                        st["身分"] = (ROLE[cell] + ("｜判定窗" if (wn == "主" and sg == "主全窗" and cell in ("K1", "K2")) else "｜分報（⛔ 不改判定）"))
                    st["句子"] = sentence(cell, st, early=(wn == "早年"))
                    segj[f"{cell}_H{H}"] = st
                    fr.to_csv(os.path.join(out, "events", f"events_{wn}_{sg}_{cell}_H{H}.csv.gz"), index=False,
                              compression={"method": "gzip", "compresslevel": 6})
                    MAIN.append({"世界": wn, "段": sg, "格": cell, "說明": NAME[cell], "H": H, "身分": st["身分"], "期間": f"{cal[p0].date()}～{cal[min(p1, n0 - 1 - H)].date()}",
                                 **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("H", "身分", "句子")}, "句子": st["句子"]})
                    log(f"  [{wn}/{sg}] {cell} H{H}：n={st['n']} n_eff={st.get('n_eff')} d×X̄={pct(st.get('dX̄'))} "
                        f"CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}" + (f" 假 x={st.get('假訊號_新預設_x2')}" if H == 20 else "") + f"｜{time.time() - t0:.0f}s")
            # ── 比較（P8）
            for new, old in (("K1", "K1b"), ("K2", "K2b")):
                for H in HS:
                    A1 = EVF[(new, H)]; A2 = EVF[(old, H)]
                    k1 = clkey(A1["T"][A1["ok"]], H, p0, moni_s); k2 = clkey(A2["T"][A2["ok"]], H, p0, moni_s)
                    d = diff_stats(A1["dX"][A1["ok"]], k1, A2["dX"][A2["ok"]], k2)
                    CMP.append({"世界": wn, "段": sg, "比較": f"{new} − {old}", "H": H, **d})
            # ── 描述格（P9）
            for H in HS:
                A1 = EVF[("K1", H)]; A2 = EVF[("K1b", H)]
                kb = set(zip(A2["fr"]["sid"], A2["fr"]["T"]))
                inb = np.array([(s_, t_) in kb for s_, t_ in zip(A1["fr"]["sid"], A1["fr"]["T"])], bool)
                okk = A1["ok"]
                subs = {"嚴版（研究二原版∩四條）": okk & inb, "K1 多出來的（K1∖K1b）": okk & ~inb}
                for nm, m in subs.items():
                    DESC.append({"世界": wn, "段": sg, "母格": "K1", "子集": nm, "H": H, **desc_ci(A1["dX"][m], A1["T"][m], H, p0, moni_s)})
                for cell in ("K2", "K2b"):
                    A_ = EVF[(cell, H)]; fr = A_["fr"]; okk = A_["ok"]
                    for shp in ("Adam&Adam", "Adam&Eve", "Eve&Adam", "Eve&Eve"):
                        m = okk & (fr["Adam/Eve"].to_numpy() == shp)
                        DESC.append({"世界": wn, "段": sg, "母格": cell, "子集": shp, "H": H, **desc_ci(A_["dX"][m], A_["T"][m], H, p0, moni_s)})
                    m = okk & fr["量遞減"].to_numpy(bool)
                    DESC.append({"世界": wn, "段": sg, "母格": cell, "子集": "量遞減 L1＞A＞L2", "H": H, **desc_ci(A_["dX"][m], A_["T"][m], H, p0, moni_s)})
            Wj["段"][sg] = segj
        J["世界"][wn] = Wj
        del VALID, G, CSB, GAP, PV, TRD1, DECA, RAW, X, BASE
    # ── 判定（主全窗 H20）
    jd = {}
    for cell in ("K1", "K2"):
        st = J["世界"]["主"]["段"]["主全窗"][f"{cell}_H20"]
        g322 = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and (st.get("假訊號_新預設_x2", 99) <= 1) and st.get("扣成本", -1) > 0)
        jd[cell] = {"格": NAME[cell], "結果": st["結果"], "出口": st.get("出口"), "n": st["n"], "n_eff": st.get("n_eff"), "d×X̄": st.get("dX̄"),
                    "95%CI": [st.get("lo"), st.get("hi")], "BonfCI(0.05/2)": [st.get("bonf_lo"), st.get("bonf_hi")],
                    "假訊號x/30(新預設)": st.get("假訊號_新預設_x2"), "d×X̄−成本": st.get("扣成本"),
                    "過seq322門檻": g322, "句子": st["句子"]}
    J["判定"] = jd
    J["N"] = {"本件判定格": 2, "對照格與描述格": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "PatC_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DESC).to_csv(os.path.join(out, "PatC_desc.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(CMP).to_csv(os.path.join(out, "PatC_compare.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    keys = list(FACC)
    np.savez_compressed(os.path.join(out, "fake_acc.npz"), keys=np.array(keys), acc=np.stack([FACC[k][0] for k in keys]),
                        cnt=np.stack([FACC[k][1] for k in keys]))
    J["比較"] = CMP; J["描述"] = DESC
    json.dump(J, open(os.path.join(out, "PatC.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'd×X̄', '假訊號x/30(新預設)', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
