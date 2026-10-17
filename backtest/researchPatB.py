# -*- coding: utf-8 -*-
"""型態補條件 B 組 seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 15b61be1b85b426d，2026-10-17 09:38；裁定 seq360 §二：
只做做多兩格 B1 三內向上、B2 三外向上，N_前段 ＋2；向下兩格 ⛔ 不做）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchPatB_freq（事件偵測、剔除）、researchAscTri_freq（世界）、research11 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatB [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatB_check
輸出 backtest/resultsPatB/（⛔ 不碰 freq/）：PatB.json、PatB_main.csv（主表）、PatB_compare.csv（確認版 − 原版）、PatB_alt.csv（先驗③）、
    PatB_desc.csv（只配 r10、上市／上櫃等描述）、by_year.csv、fake_reps.csv、fake_acc.npz、
    events/events_<世界>_<段>_<格>_H<H>.csv.gz（逐筆 R、對照、X）、events/alt_<世界>_<段>_<格>_H<H>.csv.gz、run.log

格：判定 B1 三內向上、B2 三外向上（各 H20；H60 只描述）；描述對照（⛔ 不判、不計 N）K25 原版多頭母子線、K56 原版多頭吞噬（T ＝ 第 2 根）。

═══ 讀法（P 標；方法全沿用 PREREG型態全量 seq3 ＝ researchPatAll.py 的 C1～C8 K 棒版；母體、GATE_V2、壞根、剔除同 C 組 researchPatC；
     ⛔ 在讀任何本件報酬之前寫死；★＝兩種讀法擇一，〔 〕內為另一讀法、⛔ 不另跑）═══
 P1 事件 ＝ 頻率表同一批：逐股呼叫 researchPatB_freq.stock_job 原樣（世界 ＝ researchAscTri_freq.load_world），
    ⭐ 每個 (世界, 段, 格) 依頻率表寫法排成表、與已提交的 resultsPatB/freq/events_*.csv.gz 逐列逐欄比，任一不同 ⇒ 中止、⛔ 不算報酬。
    判定母體 ＝ 狀態_H20（H60 用 狀態_H60）＝「保留」者。
 P2 R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1（load_bars 的 df；PatAll C1）。成本兩邊相同、相減抵銷 ⇒ 本體 ⛔ 不扣；
    seq322 門檻「扣成本後仍 ＞ 0」另欄 ＝ d×X̄ − 0.585%（evaluate.COST）。
 P3 K 棒主對照（登錄 §二 ⇒ PatAll §五／C2）：k ＝ 型態根數（B1、B2 ＝ 3；K25、K56 ＝ 2）；b ＝ 該股 T 那根有效 K 棒序號；
    r10_k ＝ c[b−k] ÷ c[b−k−10] − 1（＝ 第 1 根前一日的 r10，與偵測器 A2 同值）、型態期間報酬_k ＝ c[b] ÷ c[b−k] − 1
    （B 組 ＝ 第 1 根前一日收盤到 T 收盤，三根；登錄 §二 ⚠）。兩量各自在 T 當天的橫斷面切十分位
    （rank(method="first") 等分 10，PatAll decile_int 同式；m＜10 ⇒ 無十分位）。
    ★ 母體是 point-in-time（C 組 P3 同）⇒ 十分位橫斷面 ＝ T 當天 pit_valid ∧ 有效 K 棒 ∧ r10_k、期間報酬_k 可算（含 T＋1 不能成交、有斷點、
      當天有型態者；PatAll C2 ★ 同）〔另一讀法：PatAll 的靜態 gate3，不看 pit_valid〕。
    對照股 ＝ 同 r10 十分位 × 同期間報酬十分位、同事前門檻（四格都是「降」⇒ r10_k ＜ 0）、T 當天【原始】偵測沒有該格
    （不論合併／剔除；原始 ＝ 頻率表事件檔任何狀態）、T＋1 可成交（有成交、開盤非缺且 ＞ 0、非開盤漲停、非開盤跌停 ＝ 頻率表同旗標）、
    ★ [該股自己的 first_k（第 b−k＋1 根）, T＋H] 無硬斷點（PatAll C2 ★；斷點式 ＝ 頻率表 brk：區間內有壞 K 棒，或 T＋H 前最後一根 K 棒
    到 T＋H 已缺 ≥ 5 日且之後還有成交）、R 可算 ⇒ 等權平均；自己不算。只配 r10 的描述版 ＝ 同一套、只去掉期間報酬十分位。
 P4 配對格當天沒有對照股 ⇒ 該事件剔除並計數（PatAll C4）；事件不在十分位母體（理論上不會）⇒ 同樣剔除並計數。
 P5 未配對描述：EW_H(T) ＝ T 當天 pit_valid ∧ R 可算的全部股票之 R 等權平均；X_u ＝ R − EW（C 組 P5 同）。
 P6 判定量 ＝ d × X̄（d ＝ ＋1）。CI：H20 ＝ T 所在曆月分群、H60 ＝ (T − 段起點)//60 分群；CR0（research11.cl_stats）、1.96；
    非重疊 SE ＝ 20／60 日區段平均的標準差 ÷ √區段數（第二欄）。n_eff ＝ min(配對後事件數, 有事件的分群數)；
    ＜30 ⇒ 樣本不足以分辨、30～99 ⇒ 出口②（句首「樣本中等」）、≥100 ⇒ 出口③；結果② ＝ CI 不含 0 且 ＞0、③ ＝ 不含 0 且 ＜0、① ＝ 含 0。
    ★ Bonferroni 族 ＝ 本登錄判定格 N ＝ 2（seq360 N_前段 ＋2；C 組同讀法）⇒ z ＝ Φ⁻¹(1 − 0.05／4)〔另一讀法：PatAll 的 0.05／180
    ⇒ 並報一欄「參考」、⛔ 不用來判〕。判定只用【主全窗 H20】；探索／確認／早年 同法分報（標籤照印、⛔ 不改判定）；H60 只描述。
 P7 假訊號臂（PatAll C8 K 棒版）：r ＝ 0…29；每檔、每格、每段（H20）：n ＝ 該檔保留真事件數；可抽日 ＝ 該檔 T ∈ [段起點, min(段尾, 資料尾 − H)]
    且 ★ 在十分位母體（pit_valid ∧ 有效 K 棒 ∧ r10_k、期間報酬_k 可算 ∧ 十分位有定義）且 r10_k ＜ 0（PatAll C8 ★ K 棒同；pit_valid 是 C 組加的）；
    新預設 ＝ 排除「存在該格保留真事件 T_r ∈ [T − 20, T]」的日子；不排除版並列描述；不放回抽 n 天（不足 ⇒ 全取、另報）；⛔ 不合併。
    假事件 first ＝ 第 b−k＋1 根；之後同一套剔除（[first, T＋H] 硬斷點、T＋1 不可成交 ⇒ 計數、⛔ 不補抽）、同一套對照（自己若在對照池
    ⇒ 從自己的對照裡扣掉）、同分群、同判定式。種子 default_rng([20260927＋r, crc32(sid), 格序號, H, 版本])；格序號 B1＝0、B2＝1、K25＝2、K56＝3。
    x／30 ＝ 落結果② 的次數。結果② 且 x ≥ 2 ⇒ 句首「⚠ 隨機挑日子也有 x／30 次同樣過關。」（PatAll 同）。
 P8 確認版 vs 原版（登錄 §三；描述、⛔ 不判、不計 N）：B1 − K25、B2 − K56，同段、同 H；差 ＝ d×X̄(確認) − d×X̄(原版)；
    SE ＝ 曆月分群線性化（C 組 P8 同式；兩組各自的對照）、1.96。原版事件中第 3 根確認的比例 ＝ 頻率表 confirm.csv（引用）。
 P9 先驗③「從原版 T＋1 開盤起算」（描述、⛔ 不判）：事件 ＝ B1（B2）該 H 保留事件；T2 ＝ 第 2 根（原版 T）；
    進場 ＝ 原版 T＋1 開盤（＝ 第 3 根開盤）；★ 出場 ＝ 確認版同一個出場日 T3＋H 的收盤〔另一讀法：原版 T2＋H〕
    ⇒ R_alt ＝ ffill 還原收盤(T2＋H＋1) ÷ 還原開盤(T2＋1) − 1；確認日 R_day ＝ 還原收盤(T2＋1) ÷ 還原開盤(T2＋1) − 1。
    ★ 對照 ＝ 原版 K25（K56）的 K 棒主對照：同一天 T2、k ＝ 2 的 r10 × 期間報酬十分位、r10 ＜ 0、T2 當天沒有原版原始偵測、T2＋1 可成交、
    [自己 first_2, T2＋H＋1] 無硬斷點、R_alt 可算；同一組對照股同時算 R_alt 與 R_day 的平均（⇒ 確認日的超額與全段超額用同一組人）。
    X_alt ＝ R_alt − 對照、X_day ＝ R_day − 對照、X_rest ＝ X_alt − X_day；比例 ＝ mean(X_day) ÷ mean(X_alt)，
    CI ＝ 分群線性化（z_i ＝ (X_day,i − 比例·X_alt,i) ÷ mean(X_alt)，CR0）；mean(X_alt) 的 CI 含 0 ⇒ 註「分母含 0、比例不穩」。
    不可算 ⇒ 計數剔除：第 3 根不是 T2 的次一日曆交易日（中間停牌）、T2 pit 無效、T2＋1 不可成交（含開盤漲跌停）、斷點、配對格無對照股。
    同一批事件另報確認版自己的 X（對照：P3）。
 P10 seq322 門檻 ＝ 主全窗 H20 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ d×X̄ − 0.585% ＞ 0（四條全過才另起組合層登錄）。
 P11 結果句照 PatAll §七 原句；必附「單筆層通過 ≠ 組合會贏 0050」；早年另附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註。
 P12 確認段 B1 的 T＋1 開盤跌停剔除（頻率表狀態「剔除_T+1開盤跌停」）照 C 組剔除規則處理、⛔ 不補、不改；逐日筆數報在 PatB.json。
"""
from __future__ import annotations

import argparse
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
from backtest import researchPatB_freq as PBF             # noqa: E402  事件偵測＋剔除原樣（⛔ 只 import）
from backtest import researchAscTri_freq as AT            # noqa: E402  load_world 原樣
from backtest import research11 as R                      # noqa: E402  load_bars、cl_stats
from backtest import evaluate as E                        # noqa: E402  COST
from backtest import universe_gate as UG                  # noqa: E402

UG.set_gate_v2(True)

REG_SHA = PBF.REG_SHA
OUT = "backtest/resultsPatB"
FREQ = PBF.OUT
HS = (20, 60)
HG = (1, 20, 21, 60, 61)
HB = (20, 21, 60, 61)
KS = (2, 3)
REPS, EXCL, SEED_FAKE = 30, 20, 20260927
NCL = 256
Z95 = 1.96
N_FAM = 2
Z_BONF = NormalDist().inv_cdf(1 - 0.05 / N_FAM / 2)
Z_BONF180 = NormalDist().inv_cdf(1 - 0.05 / 180 / 2)
COST = E.COST
RUN = ["B1", "B2", "K25", "K56"]
KOF = {"B1": 3, "B2": 3, "K25": 2, "K56": 2}
BASEOF = {"B1": "K25", "B2": "K56"}
VNUM = {"B1": 0, "B2": 1, "K25": 2, "K56": 3}
NAME = {"B1": "三內向上", "B2": "三外向上", "K25": "多頭母子線（原版）", "K56": "多頭吞噬（原版）"}
ROLE = {"B1": "判定格", "B2": "判定格", "K25": "描述對照（原版、⛔ 不判、不計 N）", "K56": "描述對照（原版、⛔ 不判、不計 N）"}
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 小工具（PatAll／C 組同式；fixture 也測）═════════════
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
    """兩組（可重疊）平均差、分群線性化 SE（C 組 P8 同式）。"""
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
            "標籤（描述）": "差的 CI 含 0" if (m1 - m2 - Z95 * se) <= 0 <= (m1 - m2 + Z95 * se) else ("確認版＞原版" if m1 > m2 else "確認版＜原版")}


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
    o.update(lo=cs["lo"], hi=cs["hi"], se=cs["se"], n_eff=ne, 標籤=rs + "（描述、⛔ 不判）")
    return o


def ratio_ci(a, b, key):
    """比例 mean(a)/mean(b)、分群線性化 CR0 SE（P9）。"""
    a = np.asarray(a, float); b = np.asarray(b, float); n = len(a)
    if n < 2:
        return {}
    ma, mb = a.mean(), b.mean()
    r = ma / mb
    z = (a - r * b) / mb
    g = pd.Series(z - z.mean()).groupby(np.asarray(key)).sum()
    se = float(np.sqrt((g ** 2).sum()) / n)
    return {"比例": float(r), "lo": float(r - Z95 * se), "hi": float(r + Z95 * se), "se": se}


# ═════════════ K 棒對照（格表；真／假共用；PatAll k_tables／k_eval 同式）═════════════
def k_tab(X, cell, k, Hb, Gks):
    pool = X["BASEK"][k] & X["TRD1"] & ~X["BRK"][(k, Hb)] & ~X["RAW"][cell]
    for h in Gks:
        pool &= np.isfinite(X["G"][h])
    n0 = pool.shape[0]
    rr = np.arange(n0, dtype=np.int64)[:, None]
    CELL = X["CELL"][k]
    key = (rr * 100 + CELL)[pool]
    CC = np.bincount(key, minlength=n0 * 100).reshape(n0, 100)
    CS = {h: np.bincount(key, weights=X["G"][h][pool], minlength=n0 * 100).reshape(n0, 100) for h in Gks}
    DR = X["DECR"][k]
    key10 = (rr * 10 + DR.astype(np.int64))[pool]
    CC10 = np.bincount(key10, minlength=n0 * 10).reshape(n0, 10)
    CS10 = np.bincount(key10, weights=X["G"][Gks[0]][pool], minlength=n0 * 10).reshape(n0, 10)
    return {"k": k, "pool": pool, "CC": CC, "CS": CS, "CC10": CC10, "CS10": CS10, "Gks": Gks}


def k_eval(X, tb, idx, T):
    """⇒ g{h}、ctrl{h}、cc、ctrl10、cc10、自己在池、在十分位母體。"""
    idx = np.asarray(idx, np.int64); T = np.asarray(T, np.int64); k = tb["k"]
    inb = X["BASEK"][k][T, idx]
    c = np.where(inb, X["CELL"][k][T, idx], 0).astype(np.int64)
    c10 = np.where(inb, X["DECR"][k][T, idx], 0).astype(np.int64)
    s = tb["pool"][T, idx]
    g = {h: X["G"][h][T, idx] for h in tb["Gks"]}
    cc = np.where(inb, tb["CC"][T, c] - s, 0)
    cc10 = np.where(inb, tb["CC10"][T, c10] - s, 0)
    ctrl = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        for h in tb["Gks"]:
            cs = tb["CS"][h][T, c] - np.where(s, g[h], 0.0)
            ctrl[h] = np.where(cc > 0, cs / np.maximum(cc, 1), np.nan)
        h0 = tb["Gks"][0]
        cs10 = tb["CS10"][T, c10] - np.where(s, g[h0], 0.0)
        ctrl10 = np.where(cc10 > 0, cs10 / np.maximum(cc10, 1), np.nan)
    return g, ctrl, cc, ctrl10, cc10, s, inb


# ═════════════ 逐股（fork 子行程）═════════════
def stock_job(a):
    wn, sid = a
    sid_, res = PBF.stock_job(a)                          # ⭐ 頻率表同一支：事件、剔除狀態
    if res is None:
        return sid, None
    W = PBF._G[wn]; cal = W["cal"]; n0 = W["n0"]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    cf = df["close"].to_numpy(float); of = df["open"].to_numpy(float)
    valid = np.isfinite(cf); bars = np.flatnonzero(valid); cb = cf[bars]
    assert len(bars) == nb and (bars == idx).all()
    cff = pd.Series(cf).ffill().to_numpy()
    okO1 = np.zeros(n0, bool); okO1[:-1] = valid[1:] & np.isfinite(of[1:]) & (np.nan_to_num(of[1:]) > 0)
    G = {}
    for H in HG:
        g = np.full(n0, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            g[:n0 - H] = np.where(okO1[:n0 - H], cff[H:] / of[1:n0 - H + 1] - 1.0, np.nan)
        G[H] = g
    j = np.arange(nb)
    R10, PRD, F = {}, {}, {}
    for k in KS:
        r10 = np.full(n0, np.nan); prd = np.full(n0, np.nan); f = np.full(n0, -1, np.int64)
        jj = j[j - k - 10 >= 0]
        with np.errstate(invalid="ignore", divide="ignore"):
            r10[bars[jj]] = cb[jj - k] / cb[jj - k - 10] - 1.0
            prd[bars[jj]] = cb[jj] / cb[jj - k] - 1.0
        jf = j[j - k + 1 >= 0]
        f[bars[jf]] = bars[jf - k + 1]
        R10[k] = r10; PRD[k] = prd; F[k] = f
    # 壞根（頻率表 stock_job 同式）⇒ 日曆位置累加
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        kq = int(np.searchsorted(idx, p_, "left"))
        if kq < nb:
            bad[kq] = True
    badcal = np.zeros(n0, bool); badcal[idx[bad]] = True
    csb = np.cumsum(badcal).astype(np.int64)
    kH = np.searchsorted(idx, np.arange(n0), "right") - 1
    gap = np.zeros(n0, bool)
    okk = (kH >= 0) & (kH < nb - 1)
    p = np.arange(n0)[okk]; kk = kH[okk]
    gap[p] = (idx[kk + 1] - idx[kk] - 1 >= 5) & (p - idx[kk] >= 5)
    BRK = {}
    for k in KS:
        for H in HB:
            out = np.ones(n0, bool)
            t = np.arange(n0 - H); b = t + H; ff = F[k][:n0 - H]
            ok = ff >= 0
            t, b, ff = t[ok], b[ok], ff[ok]
            pb = csb[b] - np.where(ff > 0, csb[np.maximum(ff - 1, 0)], 0)
            out[t] = (pb > 0) | gap[b]
            BRK[(k, H)] = out
    # 事件 first ＝ 第 b−k＋1 根（逐筆驗）
    mism = 0
    for (sg, cell), rows in res["rows"].items():
        k = KOF[cell]
        for x in rows:
            mism += int(F[k][x["T"]] != x["first"])
    return sid, {"rows": res["rows"], "valid": valid, "G": G, "R10": R10, "PRD": PRD, "BRK": BRK, "mism": mism}


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(7)
    n, S = 260, 48
    X = {"G": {h: rng.normal(0, 0.1, (n, S)) for h in HG}, "TRD1": rng.random((n, S)) < 0.9,
         "BRK": {(k, h): rng.random((n, S)) < 0.05 for k in KS for h in HB}, "RAW": {c: rng.random((n, S)) < 0.04 for c in RUN},
         "DECR": {}, "DECP": {}, "BASEK": {}, "CELL": {}}
    for h in HG:
        X["G"][h][n - h:] = np.nan
    for k in KS:
        dr = rng.integers(-1, 3, (n, S)).astype(np.int8); dp = np.where(dr >= 0, rng.integers(0, 3, (n, S)), -1).astype(np.int8)
        sg = rng.choice([-1, 1], (n, S))
        X["DECR"][k] = dr; X["DECP"][k] = dp
        X["BASEK"][k] = (dr >= 0) & (dp >= 0) & (sg == -1)
        X["CELL"][k] = np.where(X["BASEK"][k], dr.astype(np.int16) * 10 + dp, -1).astype(np.int16)
    worst = 0.0; nchk = 0
    for cell in RUN:
        k = KOF[cell]
        for (Hb, Gks) in ((20, (20,)), (60, (60,)), (21, (21, 1)), (61, (61, 1))):
            tb = k_tab(X, cell, k, Hb, Gks)
            for _ in range(150):
                t = int(rng.integers(0, n - Hb)); i = int(rng.integers(0, S))
                if not X["BASEK"][k][t, i]:
                    continue
                g, ctrl, cc, c10, n10, s, inb = k_eval(X, tb, np.array([i]), np.array([t]))
                for only10 in (False, True):
                    xs = {h: [] for h in Gks}
                    for q in range(S):
                        if q == i or not X["BASEK"][k][t, q] or X["DECR"][k][t, q] != X["DECR"][k][t, i]:
                            continue
                        if not only10 and X["DECP"][k][t, q] != X["DECP"][k][t, i]:
                            continue
                        if not X["TRD1"][t, q] or X["BRK"][(k, Hb)][t, q] or X["RAW"][cell][t, q]:
                            continue
                        if not all(np.isfinite(X["G"][h][t, q]) for h in Gks):
                            continue
                        for h in Gks:
                            xs[h].append(X["G"][h][t, q])
                    if only10:
                        assert n10[0] == len(xs[Gks[0]])
                        if xs[Gks[0]]:
                            worst = max(worst, abs(c10[0] - np.mean(xs[Gks[0]])))
                    else:
                        assert cc[0] == len(xs[Gks[0]]), (cc[0], len(xs[Gks[0]]))
                        for h in Gks:
                            if xs[h]:
                                worst = max(worst, abs(ctrl[h][0] - np.mean(xs[h])))
                nchk += 1
    assert worst < 1e-12, worst
    msgs.append(f"F1 K 棒對照格表（扣自己、雙 G 同池、只配 r10）＝ 逐檔迴圈（{nchk} 筆）最大差 {worst:.1e}")
    Xz = dict(X); Xz["G"] = {h: np.where(np.isfinite(X["G"][h]), 0.0, np.nan) for h in HG}
    tb = k_tab(Xz, "B1", 3, 20, (20,))
    rr, ii = np.nonzero(X["BASEK"][3][:n - 20])
    g, ctrl, cc, _, _, _, _ = k_eval(Xz, tb, ii, rr)
    okc = cc > 0
    assert np.nanmax(np.abs((g[20] - ctrl[20])[okc])) == 0.0
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
    msgs.append("F5 兩組相同 ⇒ 差 0、SE 0")
    v = rng.normal(size=137)
    assert (decile_int(v) == pd.qcut(pd.Series(v).rank(method="first"), 10, labels=False).to_numpy()).all()
    msgs.append("F6 十分位整數式 ＝ pd.qcut(rank(first), 10)")
    b = rng.normal(0.02, 0.05, 400); a = 0.3 * b + rng.normal(0, 0.01, 400); kk = rng.integers(0, 30, 400)
    rc = ratio_ci(a, b, kk)
    assert abs(rc["比例"] - a.mean() / b.mean()) < 1e-12 and rc["se"] > 0
    rc2 = ratio_ci(b * 0.5, b, kk)
    assert abs(rc2["比例"] - 0.5) < 1e-12 and rc2["se"] < 1e-12
    msgs.append("F7 比例線性化 CI：a ＝ 0.5b ⇒ 比例 0.5、SE 0")
    for m in msgs:
        log("✅ " + m)
    return msgs


# ═════════════ 主程式 ═════════════
def freq_frame(rows, cal, cell):
    rows = sorted(rows, key=lambda x: (x["T"], x["sid"]))
    return pd.DataFrame([{"sid": x["sid"], "T": str(cal[x["T"]].date()), "first": str(cal[x["first"]].date()),
                          **({"第3根確認": x["conf"]} if cell in ("K25", "K56") else {}),
                          "狀態_H20": x["st20"], "狀態_H60": x["st60"]} for x in rows])


def fake_arm(X, cell, H, ev, p0, pend, moni, tb, crc):
    k = KOF[cell]
    idx = ev["i"]; T = ev["T"]
    order = np.lexsort((T, idx))
    idx_s, T_s = idx[order], T[order]
    stocks, starts = np.unique(idx_s, return_index=True)
    ends = np.r_[starts[1:], len(idx_s)]
    sub = X["BASEK"][k][p0:pend + 1]
    cands = {int(i): np.flatnonzero(sub[:, i]).astype(np.int64) + p0 for i in stocks}
    acc = np.zeros((REPS, 2, NCL, 2)); cnt = np.zeros((REPS, 2, 4), np.int64)   # 抽出、剔除斷點或T+1、配對格無對照股、可抽日不足
    G = X["G"][H]
    for r in range(REPS):
        for ver in (0, 1):
            fi, fT = [], []
            for i, a, b in zip(stocks, starts, ends):
                Tk = T_s[a:b]
                cand = cands[int(i)]
                if ver == 0:
                    cand = excl_past(cand, Tk)
                m = min(len(Tk), len(cand)); cnt[r, ver, 3] += len(Tk) - m
                if m == 0:
                    continue
                rng = np.random.default_rng([SEED_FAKE + r, crc[int(i)], VNUM[cell], H, ver])
                pick = np.sort(rng.choice(cand, size=m, replace=False))
                fi.append(np.full(m, i, np.int64)); fT.append(pick.astype(np.int64))
            if not fi:
                continue
            fi = np.concatenate(fi); fT = np.concatenate(fT)
            cnt[r, ver, 0] += len(fi)
            own = X["TRD1"][fT, fi] & ~X["BRK"][(k, H)][fT, fi] & np.isfinite(G[fT, fi])
            cnt[r, ver, 1] += int((~own).sum())
            fi, fT = fi[own], fT[own]
            g, ctrl, cc, _, _, _, inb = k_eval(X, tb, fi, fT)
            assert inb.all()
            okc = cc > 0
            cnt[r, ver, 2] += int((~okc).sum())
            dX = (g[H] - ctrl[H])[okc]; TT = fT[okc]
            if len(dX):
                cl = clkey(TT, H, p0, moni)
                assert cl.max() < NCL
                np.add.at(acc[r, ver, :, 0], cl, 1.0)
                np.add.at(acc[r, ver, :, 1], cl, dX)
    return acc, cnt


def sentence(cell, row, early=False):
    nm = NAME[cell]; H = int(row["H"])
    tail = [SENT_ALL] + (NOTE_EARLY if early else [])
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
    out = OUT if a.limit is None else "/tmp/patb_try"
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = PBF.reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜本體開跑 {now_tpe()}")
    fx = selftest()
    J = {"性質": "型態補條件 B 組 seq1 事件層正式跑（單筆層；判定 B1、B2 各 H20；H60 只描述）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq360 §二（只做做多兩格、N_前段 ＋2）",
         "方法": "PREREG型態全量 seq3（sha b7b4a05af0341797）K 棒版 C1～C8；母體／剔除同 C 組", "Bonferroni": {"族N": N_FAM, "z": Z_BONF, "參考_N180_z": Z_BONF180},
         "成本": COST, "fixture": fx, "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DESC = []; CMP = []; ALT = []; BY = []; FK = []; FACC = {}
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in PBF.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 1 if y_ is None else int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1
            win[sg] = (p0, p1)
        W["win"] = win; PBF._G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        S = len(W["sids"]); ix = W["ix"]
        VALID = np.zeros((n0, S), bool)
        G = {H: np.full((n0, S), np.nan) for H in HG}
        R10 = {k: np.full((n0, S), np.nan) for k in KS}; PRD = {k: np.full((n0, S), np.nan) for k in KS}
        BRK = {(k, H): np.ones((n0, S), bool) for k in KS for H in HB}
        BARS = [np.zeros(0, np.int64)] * S
        ROWS = {}; mism = 0
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]
                    VALID[:, j] = r["valid"]; BARS[j] = np.flatnonzero(r["valid"])
                    for H in HG:
                        G[H][:, j] = r["G"][H]
                    for k in KS:
                        R10[k][:, j] = r["R10"][k]; PRD[k][:, j] = r["PRD"][k]
                        for H in HB:
                            BRK[(k, H)][:, j] = r["BRK"][(k, H)]
                    ROWS[sid] = r["rows"]; mism += r["mism"]
                if (k_ + 1) % 300 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(ROWS)} 檔｜{time.time() - t0:.0f}s")
        assert mism == 0, f"⛔ 事件 first ≠ 第 b−k＋1 根：{mism}"
        PV = np.asarray(W["PV"], bool)[:, :n0].T.copy()
        TRD = W["TRD"]; O = W["O"][:, :n0]; UPL = W["UPL"]; DNL = W["DNL"]
        TRD1 = np.zeros((n0, S), bool)
        with np.errstate(invalid="ignore"):
            TRD1[:-1] = (TRD[:, 1:] & np.isfinite(O[:, 1:]) & (np.nan_to_num(O[:, 1:]) > 0) & ~UPL[:, 1:] & ~DNL[:, 1:]).T
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐列逐欄）
        nchk = 0
        for sg in win:
            for cell in RUN:
                rows = [x for s_ in ROWS for x in ROWS[s_][(sg, cell)]]
                mine = freq_frame(rows, cal, cell) if rows else pd.DataFrame()
                p_ = os.path.join(FREQ, f"events_{wn}_{sg}_{cell}.csv.gz")
                ref = pd.read_csv(p_, dtype=str, keep_default_na=False)
                if a.limit:
                    ref = ref[ref["sid"].isin(set(sids))].reset_index(drop=True)
                same = list(ref.columns) == list(mine.columns) and ref.shape == mine.shape and (ref.values == mine.astype(str).values).all()
                if not same:
                    raise SystemExit(f"⛔ {wn}/{sg}/{cell} 重新偵測 ≠ 已提交事件檔（{len(mine)} vs {len(ref)}）⇒ 中止（未算任何報酬）")
                nchk += len(ref)
        log(f"[查核1] {wn}：重新偵測與已提交頻率表事件檔逐列逐欄相同（{nchk:,} 列）；事件 first ＝ 第 b−k＋1 根（差 0）")
        RAW = {}
        for cell in RUN:
            M = np.zeros((n0, S), bool)
            for s_ in ROWS:
                j = ix[s_]
                for sg in win:
                    for x in ROWS[s_][(sg, cell)]:
                        M[x["T"], j] = True
            RAW[cell] = M
        bad_st = Counter()
        for s_ in ROWS:
            j = ix[s_]
            for sg in win:
                for cell in RUN:
                    k = KOF[cell]
                    for x in ROWS[s_][(sg, cell)]:
                        for H in HS:
                            st = x[f"st{H}"]
                            if st == "保留":
                                if BRK[(k, H)][x["T"], j] or not TRD1[x["T"], j] or not PV[x["T"], j] or not np.isfinite(G[H][x["T"], j]):
                                    bad_st["保留但本支判不可用"] += 1
                            elif st == "剔除_硬斷點":
                                if not BRK[(k, H)][x["T"], j]:
                                    bad_st["硬斷點但本支判無斷點"] += 1
        assert not bad_st, bad_st
        log("[查核2] 保留事件：本支斷點矩陣無斷點、T＋1 可成交、pit_valid、R 可算；頻率表「剔除_硬斷點」本支全部判有斷點")
        # ── 十分位（K 棒雙十分位；橫斷面 ＝ T 當天 pit_valid ∧ 有效 ∧ 兩量可算）
        DECR, DECP, BASEK, CELL = {}, {}, {}, {}
        for k in KS:
            base = PV & VALID & np.isfinite(R10[k]) & np.isfinite(PRD[k])
            DECR[k] = dec_matrix(R10[k], base); DECP[k] = dec_matrix(PRD[k], base)
            with np.errstate(invalid="ignore"):
                BASEK[k] = (DECR[k] >= 0) & (DECP[k] >= 0) & (np.nan_to_num(R10[k]) < 0)
            CELL[k] = np.where(BASEK[k], DECR[k].astype(np.int16) * 10 + DECP[k], -1).astype(np.int16)
        # 事件的 r10_k ＜ 0、在十分位母體（逐筆）
        nb_ = Counter()
        for s_ in ROWS:
            j = ix[s_]
            for sg in win:
                for cell in RUN:
                    k = KOF[cell]
                    for x in ROWS[s_][(sg, cell)]:
                        if not (R10[k][x["T"], j] < 0):
                            nb_["r10_k 非負"] += 1
        assert not nb_, nb_
        del R10, PRD
        EW = {}
        for H in HS:
            gm = np.where(PV, G[H], np.nan)
            with np.errstate(invalid="ignore"):
                c_ = np.isfinite(gm).sum(axis=1); s2 = np.nansum(gm, axis=1)
            EW[H] = np.where(c_ > 0, s2 / np.maximum(c_, 1), np.nan)
            del gm
        moni = np.asarray(cal.year * 12 + cal.month)
        years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        crc = [zlib.crc32(s.encode("utf-8")) for s in W["sids"]]
        X = {"G": G, "TRD1": TRD1, "BRK": BRK, "RAW": RAW, "DECR": DECR, "DECP": DECP, "BASEK": BASEK, "CELL": CELL}
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        log(f"[十分位、EW] 完成｜第一次讀報酬 {J['時點']['第一次讀報酬']}｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(ROWS),
              "閘": W["gate"], "壞根": W["bad_info"], "段": {}}
        TB = {}
        for cell in RUN:
            for H in HS:
                TB[(cell, H)] = k_tab(X, cell, KOF[cell], H, (H,))
        TBA = {}
        for cell in ("B1", "B2"):
            for H in HS:
                TBA[(cell, H)] = k_tab(X, BASEOF[cell], 2, H + 1, (H + 1, 1))
        for sg, (p0, p1) in win.items():
            moni_s = moni - moni[p0]
            segj = {}; EVF = {}
            for cell in RUN:
                for H in HS:
                    tb = TB[(cell, H)]
                    ev = [(ix[s_], x) for s_ in ROWS for x in ROWS[s_][(sg, cell)] if x[f"st{H}"] == "保留"]
                    ev.sort(key=lambda z: (z[1]["T"], z[1]["sid"]))
                    ii = np.array([e[0] for e in ev], np.int64); TT = np.array([e[1]["T"] for e in ev], np.int64)
                    FF = np.array([e[1]["first"] for e in ev], np.int64)
                    g, ctrl, cc, ctrl10, cc10, s, inb = k_eval(X, tb, ii, TT)
                    g = g[H]; ctrl = ctrl[H]
                    assert np.isfinite(g).all()
                    assert not (s & inb).any(), "⛔ 事件自己在對照池（當天應有原始偵測）"
                    why = np.where(~inb, "不在十分位母體", np.where(cc > 0, "有", "配對格無對照股"))
                    Xv = g - ctrl; dX = 1.0 * Xv; ok = np.isfinite(Xv)
                    ew = EW[H][TT] if len(ev) else np.zeros(0); Xu = g - ew
                    st = cell_stats(dX[ok], TT[ok], H, p0, moni_s)
                    st.update({"保留": int(len(ev)), "配對剔除": dict(Counter(why[~ok].tolist())), "配對剔除數": int((~ok).sum()),
                               "對照數_中位": float(np.median(cc[ok])) if ok.any() else None, "對照數_最小": int(cc[ok].min()) if ok.any() else None,
                               "R̄": float(g[ok].mean()) if ok.any() else None, "對照R̄": float(ctrl[ok].mean()) if ok.any() else None,
                               "相異檔數": int(len(set(ii[ok].tolist())))})
                    ok10 = np.isfinite(ctrl10)
                    sub_desc = {"只配r10": desc_ci(g[ok10] - ctrl10[ok10], TT[ok10], H, p0, moni_s),
                                "未配對_dXu": desc_ci(Xu[ok], TT[ok], H, p0, moni_s)}
                    mk = np.array([W["mk"].get(W["sids"][i], "twse") for i in ii]) if len(ev) else np.zeros(0, str)
                    sub_desc["上市"] = desc_ci(dX[ok & (mk == "twse")], TT[ok & (mk == "twse")], H, p0, moni_s)
                    sub_desc["上櫃"] = desc_ci(dX[ok & (mk == "tpex")], TT[ok & (mk == "tpex")], H, p0, moni_s)
                    for nm_, q in sub_desc.items():
                        DESC.append({"世界": wn, "段": sg, "母格": cell, "子集": nm_, "H": H, **q})
                    st.update(sub_desc)
                    yr = years[TT] if len(ev) else np.zeros(0, int)
                    st["逐年"] = {str(y): {"n": int((ok & (yr == y)).sum()), "dX̄": float(dX[ok & (yr == y)].mean()) if (ok & (yr == y)).any() else None}
                                for y in sorted(set(yr.tolist()))}
                    for y, q in st["逐年"].items():
                        BY.append({"世界": wn, "段": sg, "格": cell, "H": H, "年": y, **q})
                    fr = pd.DataFrame({"sid": [W["sids"][i] for i in ii], "market": mk, "T": dates[TT] if len(ev) else [], "first": dates[FF] if len(ev) else [],
                                       "R": g, "對照平均": ctrl, "對照數": cc, "X": Xv, "dX": dX, "對照平均_r10": ctrl10, "對照數_r10": cc10,
                                       "EW": ew, "X_未配對": Xu, "分群": clkey(TT, H, p0, moni_s) if len(ev) else [], "配對": why})
                    EVF[(cell, H)] = {"fr": fr, "i": ii, "T": TT, "ok": ok, "dX": dX}
                    if H == 20:
                        pend = min(p1, n0 - 1 - H)
                        acc, cntf = fake_arm(X, cell, H, {"i": ii, "T": TT}, p0, pend, moni_s, tb, crc)
                        FACC[f"{wn}|{sg}|{cell}|H{H}"] = (acc, cntf)
                        for ver, vn in ((0, "新預設"), (1, "不排除")):
                            res_ = [agg_eval(acc[r_, ver]) for r_ in range(REPS)]
                            st[f"假訊號_{vn}_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                            st[f"假訊號_{vn}_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                            st[f"假訊號_{vn}_平均dX"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                            c2 = cntf[:, ver].sum(axis=0)
                            st[f"假訊號_{vn}_帳"] = {"抽出": int(c2[0]), "剔除_斷點或T+1": int(c2[1]), "配對格無對照股": int(c2[2]), "可抽日不足": int(c2[3])}
                            for r_, q in enumerate(res_):
                                FK.append({"世界": wn, "段": sg, "格": cell, "H": H, "版本": vn, "r": r_,
                                           **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                    st["H"] = H
                    if H == 60:
                        st["身分"] = "H60 描述（⛔ 不判）"
                    else:
                        st["身分"] = (ROLE[cell] + ("｜判定窗" if (wn == "主" and sg == "主全窗" and cell in ("B1", "B2")) else "｜分報（⛔ 不改判定）"))
                    st["句子"] = sentence(cell, st, early=(wn == "早年"))
                    segj[f"{cell}_H{H}"] = st
                    fr.to_csv(os.path.join(out, "events", f"events_{wn}_{sg}_{cell}_H{H}.csv.gz"), index=False,
                              compression={"method": "gzip", "compresslevel": 6})
                    MAIN.append({"世界": wn, "段": sg, "格": cell, "說明": NAME[cell], "H": H, "身分": st["身分"], "期間": f"{cal[p0].date()}～{cal[min(p1, n0 - 1 - H)].date()}",
                                 **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("H", "身分", "句子")}, "句子": st["句子"]})
                    log(f"  [{wn}/{sg}] {cell} H{H}：n={st['n']} n_eff={st.get('n_eff')} d×X̄={pct(st.get('dX̄'))} "
                        f"CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}" + (f" 假 x={st.get('假訊號_新預設_x2')}" if H == 20 else "") + f"｜{time.time() - t0:.0f}s")
            # ── 確認版 vs 原版（P8）
            for new, old in (("B1", "K25"), ("B2", "K56")):
                for H in HS:
                    A1 = EVF[(new, H)]; A2 = EVF[(old, H)]
                    k1 = clkey(A1["T"][A1["ok"]], H, p0, moni_s); k2 = clkey(A2["T"][A2["ok"]], H, p0, moni_s)
                    d = diff_stats(A1["dX"][A1["ok"]], k1, A2["dX"][A2["ok"]], k2)
                    CMP.append({"世界": wn, "段": sg, "比較": f"{new} − {old}", "H": H, **d})
            # ── 先驗③：從原版 T＋1 開盤起算（P9）
            for cell in ("B1", "B2"):
                for H in HS:
                    A1 = EVF[(cell, H)]; ii = A1["i"]; T3 = A1["T"]
                    T2 = np.array([int(BARS[i][np.searchsorted(BARS[i], t) - 1]) for i, t in zip(ii, T3)], np.int64)
                    why = np.full(len(ii), "", object)
                    c1 = T3 != T2 + 1
                    why[c1] = "第3根不是原版T次一日（中間停牌）"
                    c2 = (why == "") & ~PV[T2, ii]; why[c2] = "原版T pit無效"
                    c3 = (why == "") & ~TRD1[T2, ii]; why[c3] = "原版T+1不可成交（含開盤漲跌停）"
                    c4 = (why == "") & BRK[(2, H + 1)][T2, ii]; why[c4] = "硬斷點"
                    c5 = (why == "") & ~(np.isfinite(G[H + 1][T2, ii]) & np.isfinite(G[1][T2, ii])); why[c5] = "R不可算"
                    tb = TBA[(cell, H)]
                    gA, cA, ccA, _, _, sA, inbA = k_eval(X, tb, ii, T2)
                    c6 = (why == "") & ~inbA; why[c6] = "不在十分位母體"
                    c7 = (why == "") & ~(ccA > 0); why[c7] = "配對格無對照股"
                    use = why == ""
                    Xalt = gA[H + 1] - cA[H + 1]; Xday = gA[1] - cA[1]; Xrest = Xalt - Xday
                    Xconf = A1["dX"]
                    key = clkey(T3[use], H, p0, moni_s)
                    rc = ratio_ci(Xday[use], Xalt[use], key)
                    dA = desc_ci(Xalt[use], T3[use], H, p0, moni_s); dD = desc_ci(Xday[use], T3[use], H, p0, moni_s)
                    dR = desc_ci(Xrest[use], T3[use], H, p0, moni_s); dC = desc_ci(Xconf[use], T3[use], H, p0, moni_s)
                    row = {"世界": wn, "段": sg, "格": cell, "原版": BASEOF[cell], "H": H, "確認版保留": int(len(ii)), "可算": int(use.sum()),
                           "剔除": json.dumps(dict(Counter(why[~use].tolist())), ensure_ascii=False)}
                    for nm_, q in (("X_alt全段", dA), ("X_day確認日", dD), ("X_rest之後", dR), ("X_確認版同批", dC)):
                        for kk in ("n", "平均", "lo", "hi", "中位", "勝率"):
                            row[f"{nm_}_{kk}"] = q.get(kk)
                    row.update({"確認日占比": rc.get("比例"), "占比_lo": rc.get("lo"), "占比_hi": rc.get("hi"),
                                "分母CI含0": bool(dA.get("lo", -1) <= 0 <= dA.get("hi", 1)),
                                "R_alt平均": float(gA[H + 1][use].mean()) if use.any() else None, "R_day平均": float(gA[1][use].mean()) if use.any() else None,
                                "先驗③(占比≥0.5)": (rc.get("比例") is not None and rc["比例"] >= 0.5)})
                    ALT.append(row)
                    pd.DataFrame({"sid": [W["sids"][i] for i in ii], "T": dates[T3], "T2": dates[T2], "R_alt": gA[H + 1], "對照_alt": cA[H + 1],
                                  "R_day": gA[1], "對照_day": cA[1], "對照數": ccA, "X_alt": Xalt, "X_day": Xday, "X_確認版": Xconf,
                                  "可算": use, "剔除": why, "分群": clkey(T3, H, p0, moni_s)}).to_csv(
                        os.path.join(out, "events", f"alt_{wn}_{sg}_{cell}_H{H}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
                    log(f"  [{wn}/{sg}] 先驗③ {cell} H{H}：可算 {int(use.sum())}／{len(ii)}｜X_alt {pct(dA.get('平均'))}｜X_day {pct(dD.get('平均'))}"
                        f"｜占比 {rc.get('比例', float('nan')):.3f}（{rc.get('lo', float('nan')):.3f}～{rc.get('hi', float('nan')):.3f}）")
            Wj["段"][sg] = segj
        J["世界"][wn] = Wj
        del VALID, G, BRK, PV, TRD1, DECR, DECP, BASEK, CELL, RAW, X, TB, TBA
    # ── 確認段 B1 T＋1 開盤跌停剔除（P12）
    lim = {}
    for sg in ("主全窗", "確認", "探索"):
        e = pd.read_csv(os.path.join(FREQ, f"events_主_{sg}_B1.csv.gz"), dtype=str)
        dn = e[e["狀態_H20"] == "剔除_T+1開盤跌停"]
        lim[sg] = {"剔除_T+1開盤跌停_H20": int(len(dn)), "依T日": {str(k): int(v) for k, v in dn["T"].value_counts().sort_index().items()}}
    J["確認段B1開盤跌停剔除"] = lim
    J["原版第3根確認比例(引freq/confirm.csv)"] = pd.read_csv(os.path.join(FREQ, "confirm.csv"), encoding="utf-8-sig").to_dict("records")
    # ── 判定（主全窗 H20）
    jd = {}
    for cell in ("B1", "B2"):
        st = J["世界"]["主"]["段"]["主全窗"][f"{cell}_H20"]
        g322 = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and (st.get("假訊號_新預設_x2", 99) <= 1) and st.get("扣成本", -1) > 0)
        jd[cell] = {"格": NAME[cell], "結果": st["結果"], "出口": st.get("出口"), "n": st["n"], "n_eff": st.get("n_eff"), "d×X̄": st.get("dX̄"),
                    "95%CI": [st.get("lo"), st.get("hi")], "BonfCI(0.05/2)": [st.get("bonf_lo"), st.get("bonf_hi")],
                    "假訊號x/30(新預設)": st.get("假訊號_新預設_x2"), "假訊號x/30(不排除)": st.get("假訊號_不排除_x2"), "d×X̄−成本": st.get("扣成本"),
                    "過seq322門檻": g322, "句子": st["句子"]}
    J["判定"] = jd
    J["N"] = {"本件判定格": 2, "原版描述對照格": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "PatB_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DESC).to_csv(os.path.join(out, "PatB_desc.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(CMP).to_csv(os.path.join(out, "PatB_compare.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(ALT).to_csv(os.path.join(out, "PatB_alt.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    keys = list(FACC)
    np.savez_compressed(os.path.join(out, "fake_acc.npz"), keys=np.array(keys), acc=np.stack([FACC[k][0] for k in keys]),
                        cnt=np.stack([FACC[k][1] for k in keys]))
    J["比較"] = CMP; J["先驗③"] = ALT
    json.dump(J, open(os.path.join(out, "PatB.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'd×X̄', '假訊號x/30(新預設)', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
