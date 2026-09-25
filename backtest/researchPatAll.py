# -*- coding: utf-8 -*-
"""PREREG型態全量 本體（台股，單筆層，可判定 180 格：H20 92＋H60 88）——回測線落地。
判準＝台股策略線「型態全量_單筆層登錄」seq3（sha b7b4a05af0341797，24408B，2026-09-25 20:43）；
裁定線 seq173 §二（四處：K 棒主對照＝r10 × 型態期間報酬 雙十分位、族運氣基準用假訊號臂、單格引用要過 Bonferroni、方向對照表）、
seq175 §一（假訊號臂只排除過去 20 日；不排除版並列描述）、§三（N_前段 ＋180；依構造不可判定 12 格照寫、不計 N；包含關係照算、不扣 N；
平頭頂底頻繁描述寫一句）、seq177 §一③（seq3 核准、可跑報酬）。

用法（repo 根目錄；PYTHONPATH＝~/tw-p17；Python ＝ ~/tw-p16/.venv/bin/python）：
  python backtest/researchPatAll.py [--procs 2] [--limit N]      （--limit 只給除錯；正式交件不用）
輸出：backtest/resultsPatAll/body/（summary.json、cells.csv、by_year.csv、fake_reps.csv、fake_acc.npz、events/events_<vid>.csv.gz、PATALL_REPORT.md）

資料、母體、讀檔、事件：與頻率階段【同一套函式】——import researchPatAll_freq（one_stock、classify、事件檔的寫法）⇒ main edc6f8002f 快照、
   gate3、delist on、還原 OHLC、tradability（原始價漲跌停）、硬斷點 H2.brk；偵測器 patterns_all.py（⛔ 只 import、不改）。
⭐ 開算前先把重新偵測的事件，照頻率階段的寫法逐列排成文字，與已提交的 resultsPatAll/events_<vid>_<型態>.csv.gz 逐檔逐股比（列數＋md5），
   任一不同 ⇒ 中止、⛔ 不算任何報酬。另逐筆驗：事件檔的 r10／型態期間報酬（K）與錨點 r60／r20（S）＝ 本支矩陣上的值（逐位元）。
判定母體 ＝ 事件檔 狀態_H20／狀態_H60 ＝「保留」者；H120 ＝ 狀態_H120 ＝「保留」者（只描述）。
fixture：本支開頭先跑 selftest()（F1～F8），任一條不過就停。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何報酬之前寫在這裡；交件逐條列出；★＝兩種讀法擇一，〔 〕內是另一讀法、⛔ 不另跑）：
 C1 R_e ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1（登錄 §二「H〈n〉＝ 進場日＋(n−1) 的收盤」⇒ T＋1＋(H−1)＝T＋H，交易日曆；
    T＋H 無成交 ⇒ ≤ T＋H 最後一根有效 K 棒的收盤；下市者＝最後成交價，delist on）。成本兩邊相同、相減抵銷 ⇒ ⛔ 不扣。
 C2 K 棒主對照（登錄 §五、seq173 ②①）：同一天 T、gate3 中「T 有有效 K 棒、且 r10_k、型態期間報酬_k 可算」的股票（k＝該型態根數；
    r10_k ＝ c[b−k] ÷ c[b−k−10] − 1、期間報酬_k ＝ c[b] ÷ c[b−k] − 1，b ＝ 該股 T 那根有效 K 棒序號 ⇒ 等於「假如這檔 T 也出現這個型態」
    時偵測器會算出的兩個值；事件本身的值逐位元相同）⇒ 兩量各自在這個橫斷面上切十分位；
    ★ 十分位的母體 ＝ 上述全部股票（含 T＋1 不能成交、有斷點、當天有型態者）〔另一讀法：只用可當對照者＋事件本身切〕；
    十分位 ＝ rank(method="first") 後等分 10（＝ pd.qcut(rank, 10)，本支用整數式 #{j∈1..9 : 10(rank−1) ＞ j(m−1)} 免浮點邊界；F1 證同）；m＜10 ⇒ 無十分位。
    對照股 ＝ 同 r10 十分位 × 同期間報酬十分位、同事前門檻（升 r10_k＞0／降 r10_k＜0／★ 無 ⇒ r10_k ≠ 0，同偵測器 A4）、
    T 當天【原始】偵測沒有該變體（不論合併／剔除）、T＋1 可成交（有成交、開盤非缺、非開盤漲停／跌停）、
    ★ [該股自己的 first_k（＝ 第 b−k＋1 根）, T＋H] 無硬斷點（事件用 [first, T＋H]，對照用「假如它有型態時」的同一段）、R 可算 ⇒ 等權平均。
    只配 r10 的描述版 ＝ 同一套、只去掉期間報酬十分位。
 C3 價格結構對照（登錄 §五）★：配對量 ＝ 事件的「事前量」原值（r60；S25 島型頂、S26 島型底、S27 V 型改 r20），
    它是在型態第一個轉折 first 量的（c[first−1] ÷ c[first−61] − 1，事件檔 r60 欄）⇒ 橫斷面 ＝ first 那一天、全部 gate3 中當天有有效 K 棒
    且同式可算者（各股自己的有效 K 棒序列）；對照股 ＝ 該錨點日同十分位、T 有有效 K 棒、T 當天原始偵測沒有該變體、T＋1 可成交、
    [first, T＋H]（事件的同一段）無硬斷點、R 可算〔另一讀法：r60 一律在 T 量（c[T−1] ÷ c[T−61] − 1）、橫斷面在 T〕。
    ★ 價格結構的對照 ⛔ 不加事前門檻（登錄 §五 價格結構只寫十分位；K 棒才寫「同事前門檻」）。
 C4 配對格（K：十分位 × 十分位；S：十分位）當天沒有對照股 ⇒ 該事件剔除並計數（登錄 §五）；S 事件的錨點量不可算（first 前不足 61 根）⇒ 同樣剔除並計數。
 C5 未配對描述（登錄 §五 描述）：EW_H(T) ＝ T＋1 有有效 K 棒且還原開盤 ＞ 0 的全部 gate3 股票之同式 R 的等權平均（researchExit B5 同）；X_u ＝ R_e − EW_H(T)。
 C6 判定量 ＝ d × X̄（每筆 dX ＝ d_e × X_e；續／反 型的 d_e ＝ ±sign(r10)）。主 CI：H20 ＝ T 所在曆月分群、H60 ＝ (T − 窗起點)//60 分群；
    CR0（research11.cl_stats）、1.96；非重疊 SE（第二欄）＝ 20／60 日區段平均的標準差 ÷ √區段數。
    Bonferroni（seq173 ③）：雙側 α＝0.05／180 ⇒ z ＝ Φ⁻¹(1 − 0.05／360)；下界 ＝ d×X̄ ∓ z·SE（同一個 SE）。
    n_eff ＝ min(配對後事件數, 有事件的分群數)；＜30 ⇒ 出口①「樣本不足以分辨」；30～99 ⇒ 出口②（句首加「樣本中等」）；≥100 ⇒ 出口③。
    結果② ＝ CI 不含 0 且 d×X̄＞0；結果③ ＝ CI 不含 0 且 d×X̄＜0；結果① ＝ CI 含 0。勝率 ＝ dX＞0 的比例；最差單筆 ＝ min dX。
 C7 依構造不可判定 12 格（freq.csv 可判定_H20／_H60 ＝ False）：⛔ 不讀報酬、結果逐字「依構造不可判定」、附 n_eff 上限。
    H120 ＝ 描述（d×X̄、中位、p10／p90、最差），⛔ 不印 CI；★ 四個兩個 H 都不可判定的變體（K29、K60、K64、K66）H120 也 ⛔ 不讀
    〔另一讀法：H120 全 96 變體都描述〕。
 C8 假訊號臂（登錄 §八、seq175 §一）：r＝0…29；每檔、每個判定格 (變體, H)：n ＝ 該檔該格【保留】真事件數；
    可抽日 ＝ 該檔有效 K 棒、T ∈ [窗起點, 窗尾 − H]；★ K 棒另要求 r10_k、期間報酬_k 可算且滿足該變體的事前門檻（同 C2）
    〔另一讀法：不要求 ⇒ 不滿足門檻的假日子找不到同門檻對照股、被 C4 剔掉，假訊號臂的有效筆數約少一半、運氣基準偏低〕；
    新預設 ＝ 排除「存在該格保留真事件 T_r ∈ [T − 20, T]」的日子（含當天：當天收盤就知道；researchAvg A11 同）
    〔另一讀法：原始事件／[T−20, T−1]〕；不排除版 ＝ 不排除、並列描述。不放回抽 n 天（不足 ⇒ 全取、另報）；⛔ 不合併（researchAvg 同）。
    假事件的 first：K ＝ 第 b−k＋1 根；★ S ＝ 把該檔真事件（依 T 排序）的「T 到 first 的根數」依序配給抽到的日子（依 T 排序）
    〔另一讀法：S 的錨點一律取 T〕。之後同一套剔除（[first, T＋H] 硬斷點、T＋1 停牌／開盤漲停／跌停 ⇒ 計數、⛔ 不補抽）、
    同一套對照（C2／C3；假事件自己若也在對照池 ⇒ 從它自己的對照平均裡扣掉）、同分群、同判定式。
    d：固定 d 的變體照 d；續／反 型 ＝ ±sign(該假日子的 r10_k)。種子 default_rng([20260927＋r, crc32(sid), 變體序號, H, 版本])（逐檔獨立 ⇒ 與行程分工無關）。
    每格 x／30 ＝ 落結果② 的次數；每一次 r 數「180 格裡落結果② 的格數」⇒ 30 個數與最大值 ⇒ 族結論（登錄 §七）。
 C9 族結論 a ＝ 180 格中結果② 的格數、b ＝ 結果③ 的格數；a ＞ 假訊號臂（新預設）30 次的最大值 ⇒ 不加「與運氣分不開」，否則加。
 C10 包含關係 6 組（K50⊃K67、K50⊃K59、K55⊃K49、K55⊃K62、K24⊃K22、K19⊃K65）：兩格各自照算、並列；另描述「外層扣掉與內層同檔同日者」
    （外層保留事件中，該檔當天【沒有】內層原始偵測的那些）⇒ ⛔ 不判、不計 N。
 C11 照名稱方向（登錄 §三）：名稱方向 ＝ 健檢總表「名稱隱含方向」含「看漲」⇒ ＋1、含「看跌」⇒ −1（上漲受阻、停頓型態原欄「常被講成看跌反轉」⇒ −1）、
    「無明確方向」⇒ 無此讀法；價格結構 ＝ d。讀法 ＝ 名稱方向 × X̄（同一個數字、正負可能相反）。
 C12 上市／上櫃依快照 stocks.csv market 欄；逐年依 T 的曆年（描述）。
"""
from __future__ import annotations
import os, sys, time, json, gzip, hashlib, zlib
from collections import Counter, defaultdict
import multiprocessing as mp
from statistics import NormalDist
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchPatAll_freq as RPF                  # ⭐ 頻率階段原樣（one_stock、classify、f6）；⛔ 只 import
H2, D, TR, UG, PA = RPF.H2, RPF.D, RPF.TR, RPF.UG, RPF.PA
R11 = H2.R                                         # research11：⛔ 只用 cl_stats

OUT = "backtest/resultsPatAll/body"
FREQ = "backtest/resultsPatAll"
W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
HJ = (20, 60)
HA = (20, 60, 120)
KS = (1, 2, 3, 5)
SEED_FAKE, REPS, EXCL = 20260927, 30, 20
N_FAM = 180
Z95 = 1.96
Z_BONF = NormalDist().inv_cdf(1 - 0.05 / N_FAM / 2)
ANCHOR20 = ("S25", "S26", "S27")
PAIRS6 = [("K50", "K67"), ("K50", "K59"), ("K55", "K49"), ("K55", "K62"), ("K24", "K22"), ("K19", "K65")]
NCL = 128
HEADER = "sid,market,T,first,方向,r10,r20,r60,型態期間報酬,狀態_H20,狀態_H60,狀態_H120\n"
_G = {}
W = {}          # 全域矩陣（fork 後子行程共用、唯讀）
EVT = {}        # (vid, H) ⇒ 保留事件陣列
RAWL = {}       # vid ⇒ (欄號, T) 原始偵測


# ═════════════ 小工具（fixture 也測這些）═════════════
def decile_int(v):
    """v：一列值（已去缺值）⇒ 十分位 0..9（rank(method="first") 後等分 10，整數式）。"""
    m = len(v)
    order = np.argsort(v, kind="stable")
    rank = np.empty(m, np.int64); rank[order] = np.arange(1, m + 1)
    lab = np.zeros(m, np.int8)
    for j in range(1, 10):
        lab += (10 * (rank - 1) > j * (m - 1)).astype(np.int8)
    return lab


def dec_matrix(M, base, rows):
    out = np.full(M.shape, -1, np.int8)
    for t in rows:
        idx = np.flatnonzero(base[t])
        if len(idx) < 10:
            continue
        out[t, idx] = decile_int(M[t, idx])
    return out


def brk_vec(cs_pb, cs_g5, a, H):
    """t ⇒ [a[t], t＋H] 內有無硬斷點（H2.brk 向量版）；a[t] ＜ 0 或 t＋H 超出 ⇒ True（不可用）。"""
    n = len(cs_pb); out = np.ones(n, bool)
    t = np.arange(n - H); b = t + H; aa = a[:n - H]
    ok = aa >= 0
    t, b, aa = t[ok], b[ok], aa[ok]
    pb = cs_pb[b] - np.where(aa > 0, cs_pb[np.maximum(aa - 1, 0)], 0)
    a4 = aa + 4
    g5 = np.where(b >= a4, cs_g5[b] - np.where(a4 > 0, cs_g5[np.maximum(a4 - 1, 0)], 0), 0)
    out[t] = (pb > 0) | (g5 > 0)
    return out


def excl_past(cand, Tk, excl=EXCL):
    """候選日去掉「存在真事件 T_r ∈ [T − excl, T]」者（⛔ 不看未來）。"""
    if len(Tk) == 0 or len(cand) == 0:
        return cand
    k = np.searchsorted(Tk, cand, side="right") - 1
    prev = np.where(k >= 0, Tk[np.clip(k, 0, len(Tk) - 1)], -10 ** 9)
    return cand[~((k >= 0) & (cand - prev <= excl))]


def agg_eval(acc):
    """acc (NCL, 2)：逐群 (n, Σx) ⇒ 平均、CR0 SE、n_eff、出口、結果（cl_stats 的彙總同式）。"""
    nn = acc[:, 0]; S = acc[:, 1]; N = nn.sum()
    if N == 0:
        return None
    m = S.sum() / N
    se = float(np.sqrt(((S - nn * m) ** 2).sum()) / N)
    ne = int(min(N, (nn > 0).sum()))
    ex, rs = verdict(m, se, ne)
    return {"n": int(N), "平均": float(m), "lo": m - Z95 * se, "hi": m + Z95 * se, "n_eff": ne, "出口": ex, "結果": rs}


def verdict(m, se, n_eff):
    if n_eff < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if n_eff < 100 else "出口③"
    lo, hi = m - Z95 * se, m + Z95 * se
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果②" if m > 0 else "結果③")


def clkey(T, H, w0, moni):
    T = np.asarray(T, np.int64)
    return moni[T] if H != 60 else (T - w0) // 60


# ═════════════ 對照（K／S）═════════════
def raw_dense(Wd, vid):
    M = np.zeros(Wd["VALID"].shape, bool)
    j, t = RAWL_get(Wd, vid)
    M[t, j] = True
    return M


def RAWL_get(Wd, vid):
    return Wd["RAWL"][vid]


def pre_mask(sg, pre):
    return (sg == 1) if pre == "升" else ((sg == -1) if pre == "降" else (sg != 0))


def k_tables(Wd, vid, H, RAWD):
    v = PA.VMAP[vid]; k = v["k"]
    r0, r1 = Wd["w0"], Wd["w1"] - H
    sl = slice(r0, r1 + 1); nr = r1 - r0 + 1
    DR = Wd["DECR"][k][sl]; DP = Wd["DECP"][k][sl]
    base = (DR >= 0) & (DP >= 0) & pre_mask(Wd["SGN"][k][sl], v["pre"])
    G = Wd["G"][H][sl]
    pool = base & Wd["TRD1"][sl] & ~Wd["BRK"][(k, H)][sl] & np.isfinite(G) & ~RAWD[sl]
    cell = DR.astype(np.int64) * 10 + DP.astype(np.int64)
    rr = np.arange(nr, dtype=np.int64)[:, None]
    key = (rr * 100 + cell)[pool]; gv = G[pool]
    CS = np.bincount(key, weights=gv, minlength=nr * 100).reshape(nr, 100)
    CC = np.bincount(key, minlength=nr * 100).reshape(nr, 100)
    key10 = (rr * 10 + DR.astype(np.int64))[pool]
    CS10 = np.bincount(key10, weights=gv, minlength=nr * 10).reshape(nr, 10)
    CC10 = np.bincount(key10, minlength=nr * 10).reshape(nr, 10)
    return {"r0": r0, "nr": nr, "k": k, "base": base, "pool": pool, "cell": cell, "DR": DR, "G": G,
            "CS": CS, "CC": CC, "CS10": CS10, "CC10": CC10}


def k_eval(tb, idx, T):
    """⇒ R、主對照平均、對照數、r10 版對照平均、對照數、自己是否在池（假事件要從自己的對照裡扣掉）。"""
    r = np.asarray(T, np.int64) - tb["r0"]; idx = np.asarray(idx, np.int64)
    g = tb["G"][r, idx]; c = tb["cell"][r, idx]; c10 = tb["DR"][r, idx].astype(np.int64)
    s = tb["pool"][r, idx]
    gs = np.where(s, g, 0.0)
    cc = tb["CC"][r, c] - s; cs = tb["CS"][r, c] - gs
    cc10 = tb["CC10"][r, c10] - s; cs10 = tb["CS10"][r, c10] - gs
    with np.errstate(invalid="ignore", divide="ignore"):
        ctrl = np.where(cc > 0, cs / np.maximum(cc, 1), np.nan)
        ctrl10 = np.where(cc10 > 0, cs10 / np.maximum(cc10, 1), np.nan)
    return g, ctrl, cc, ctrl10, cc10, s


def s_pool(Wd, H, RAWD):
    r0, r1 = Wd["w0"], Wd["w1"] - H
    sl = slice(r0, r1 + 1)
    G = Wd["G"][H][sl]
    return {"r0": r0, "pool": Wd["VALID"][sl] & Wd["TRD1"][sl] & np.isfinite(G) & ~RAWD[sl], "G": G}


def s_one(Wd, sp, A, H, i, T, f):
    """單一事件（真或假）⇒ (對照平均, 對照數)；自己一律不算。"""
    di = A[f, i]
    if di < 0:
        return np.nan, -1
    b = T + H
    pb = Wd["CSPB"][b] - (Wd["CSPB"][f - 1] if f > 0 else 0)
    a4 = f + 4
    if b >= a4:
        g5 = Wd["CSG5"][b] - (Wd["CSG5"][a4 - 1] if a4 > 0 else 0)
        nb = (pb == 0) & (g5 == 0)
    else:
        nb = pb == 0
    r = T - sp["r0"]
    m = sp["pool"][r] & (A[f] == di) & nb
    m[i] = False
    cnt = int(m.sum())
    return (float(sp["G"][r][m].mean()) if cnt else np.nan), cnt


def own_brk(Wd, i, f, b):
    pb = Wd["CSPB"][b, i] - (Wd["CSPB"][f - 1, i] if f > 0 else 0)
    a4 = f + 4
    g5 = (Wd["CSG5"][b, i] - (Wd["CSG5"][a4 - 1, i] if a4 > 0 else 0)) if b >= a4 else 0
    return bool(pb > 0 or g5 > 0)


# ═════════════ 統計 ═════════════
def cell_stats(dx, T, H, w0, moni):
    dx = np.asarray(dx, float); T = np.asarray(T, np.int64)
    n = len(dx)
    if n == 0:
        return {"n": 0, "出口": "出口①", "結果": "樣本不足以分辨"}
    o = {"n": int(n), "dX̄": float(dx.mean()), "中位": float(np.median(dx)), "勝率": float((dx > 0).mean()),
         "最差": float(dx.min()), "p10": float(np.percentile(dx, 10)), "p90": float(np.percentile(dx, 90))}
    if H == 120:
        o["120日區段數"] = int(len(np.unique((T - w0) // 120)))
        o["註"] = "依構造不可判定（只描述；⛔ 不印 CI）"
        o["結果"] = "H120描述"
        return o
    key = clkey(T, H, w0, moni)
    cs = R11.cl_stats(dx, key)
    assert abs(cs["mean"] - o["dX̄"]) < 1e-15
    se = cs["se"]; ng = cs["months"]
    blk = (T - w0) // (20 if H == 20 else 60)
    bm = pd.Series(dx).groupby(blk).mean()
    se2 = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    ne = int(min(n, ng))
    ex, rs = verdict(o["dX̄"], se, ne)
    m = o["dX̄"]
    o.update(se=se, lo=m - Z95 * se, hi=m + Z95 * se, 群數=int(ng), 分群單位=("曆月" if H == 20 else "60日區段"),
             bonf_lo=m - Z_BONF * se, bonf_hi=m + Z_BONF * se, bonf不含0=bool(m - Z_BONF * se > 0 or m + Z_BONF * se < 0),
             se_非重疊=se2, lo_非重疊=m - Z95 * se2, hi_非重疊=m + Z95 * se2, 非重疊區段數=int(len(bm)),
             n_eff=ne, 出口=ex, 結果=rs)
    return o


def desc_ci(x, T, H, w0, moni):
    """描述用：平均、n、同分群 CI（⛔ 不判）。"""
    x = np.asarray(x, float); T = np.asarray(T, np.int64); ok = np.isfinite(x); x, T = x[ok], T[ok]
    if len(x) == 0:
        return {"n": 0}
    o = {"n": int(len(x)), "平均": float(x.mean()), "中位": float(np.median(x))}
    if H == 120 or len(x) < 2:
        return o
    cs = R11.cl_stats(x, clkey(T, H, w0, moni))
    ne = int(min(len(x), cs["months"]))
    ex, rs = verdict(cs["mean"], cs["se"], ne)
    o.update(lo=cs["lo"], hi=cs["hi"], n_eff=ne, 標籤=rs)
    return o


# ═════════════ 讀檔＋偵測（pass 1 worker）═════════════
def _init(cal, w0, w1, off):
    _G.update(cal=cal, w0=w0, w1=w1, off=off)


def load_one(args):
    sid, market = args
    cal, w0, w1, off = _G["cal"], _G["w0"], _G["w1"], _G["off"]
    n = len(cal)
    X = RPF.one_stock(sid, market, cal, w0, w1, off)
    if X is None:
        return None
    C = RPF.classify(X, w0, w1)
    # ── 事件檔同式文字（逐列比用）
    hsh = {}
    for vid, R in C.items():
        lines = []
        for i in range(len(R["T"])):
            lines.append("{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
                sid, market, cal[R["T"][i]].date(), cal[R["first"][i]].date(), int(R["d"][i]), RPF.f6(R["r10"][i]), RPF.f6(R["r20"][i]),
                RPF.f6(R["r60"][i]), RPF.f6(R["prd"][i]), R["st"][20][i], R["st"][60][i], R["st"][120][i]))
        s = "".join(lines)
        hsh[vid] = (len(lines), hashlib.md5(s.encode("utf-8")).hexdigest())
    st = D.load_stock(sid, market, cal)
    df = st.df
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    assert np.array_equal(o, X["o"], equal_nan=True)
    valid = np.isfinite(c); bars = np.flatnonzero(valid); nb = len(bars)
    cb = c[bars]
    cff = pd.Series(c).ffill().to_numpy()
    tb = X["tb"]
    okO1 = np.zeros(n, bool); okO1[:-1] = valid[1:] & np.isfinite(o[1:]) & (np.nan_to_num(o[1:]) > 0)
    G = {}
    for H in HA:
        g = np.full(n, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            g[:n - H] = np.where(okO1[:n - H], cff[H:] / o[1:n - H + 1] - 1.0, np.nan)
        G[H] = g
    trd1 = np.zeros(n, bool)
    trd1[:-1] = tb["trd"][1:] & np.isfinite(o[1:]) & ~tb["up_o"][1:] & ~tb["dn_o"][1:]
    cs_pb, cs_g5 = X["S"]["cs_pb"], X["S"]["cs_g5"]
    R10, PRD, BRK = {}, {}, {}
    j = np.arange(nb)
    for k in KS:
        r10 = np.full(n, np.nan); prd = np.full(n, np.nan); f = np.full(n, -1, np.int64)
        jj = j[j - k - 10 >= 0]
        with np.errstate(invalid="ignore", divide="ignore"):
            r10[bars[jj]] = cb[jj - k] / cb[jj - k - 10] - 1.0
            prd[bars[jj]] = cb[jj] / cb[jj - k] - 1.0
        jf = j[j - k + 1 >= 0]
        f[bars[jf]] = bars[jf - k + 1]
        R10[k] = r10; PRD[k] = prd
        for H in HA:
            BRK[(k, H)] = brk_vec(cs_pb, cs_g5, f, H)
    A60 = np.full(n, np.nan); A20 = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        jj = j[j >= 61]; A60[bars[jj]] = cb[jj - 1] / cb[jj - 61] - 1.0
        jj = j[j >= 21]; A20[bars[jj]] = cb[jj - 1] / cb[jj - 21] - 1.0
    # ── 事件：原始（窗內）、各 H 保留、帳
    raw, kept, acct = {}, {}, {}
    mism = 0
    for vid in PA.VID:
        e = X["ev"][vid]
        Tr = np.asarray(e["T"], np.int64)
        raw[vid] = Tr[(Tr >= w0) & (Tr <= w1)].astype(np.int32)
    for vid, R in C.items():
        v = PA.VMAP[vid]
        # 逐筆驗：事件檔的事前量 ＝ 本支矩陣
        if v["fam"] == "K":
            k = v["k"]
            mism += int(np.sum(R10[k][R["T"]] != R["r10"])) + int(np.sum(PRD[k][R["T"]] != R["prd"]))
        else:
            A = A20 if vid in ANCHOR20 else A60
            a = A[R["first"]]; e_ = R["r20"] if vid in ANCHOR20 else R["r60"]
            mism += int(np.sum(~((a == e_) | (np.isnan(a) & np.isnan(e_)))))
        bT = np.searchsorted(bars, R["T"]); bF = np.searchsorted(bars, R["first"])
        for H in HA:
            s = np.array(R["st"][H])
            acct[(vid, H)] = Counter(s[s != "窗外"].tolist())
            m = s == "保留"
            if m.any():
                kept[(vid, H)] = {"T": R["T"][m].astype(np.int32), "first": R["first"][m].astype(np.int32),
                                  "d": R["d"][m].astype(np.int8), "lag": (bT[m] - bF[m]).astype(np.int32)}
    return {"sid": sid, "market": market, "valid": valid, "bars": bars.astype(np.int32), "G": G, "trd1": trd1,
            "R10": R10, "PRD": PRD, "BRK": BRK, "A60": A60, "A20": A20, "cs_pb": cs_pb, "cs_g5": cs_g5,
            "raw": raw, "kept": kept, "acct": acct, "hsh": hsh, "mism": mism}


# ═════════════ 每個變體（pass 2 worker；fork 共用 W、EVT）═════════════
def do_variant(vid):
    t0 = time.time()
    Wd = W
    v = PA.VMAP[vid]; isK = v["fam"] == "K"; vnum = PA.VID.index(vid)
    w0, w1, moni = Wd["w0"], Wd["w1"], Wd["MONI"]
    J = Wd["JUDGE"][vid]
    Hs = [H for H in HJ if J[H]] + ([120] if (J[20] or J[60]) else [])
    out = {"vid": vid, "cells": {}, "fake": {}, "pairs": {}, "sec": 0.0}
    if not Hs:
        return out
    RAWD = raw_dense(Wd, vid)
    A = None if isK else (Wd["DECA20"] if vid in ANCHOR20 else Wd["DECA60"])
    frames = []
    for H in Hs:
        E = EVT.get((vid, H))
        if E is None or len(E["i"]) == 0:
            out["cells"][H] = {"n": 0}
            continue
        idx = E["i"].astype(np.int64); T = E["T"].astype(np.int64); fst = E["first"].astype(np.int64); d = E["d"].astype(float)
        if isK:
            tb = k_tables(Wd, vid, H, RAWD)
            inb = tb["base"][T - tb["r0"], idx]
            assert inb.all(), "⛔ 保留事件不在十分位母體（事前量不可算或不滿足門檻）"
            g, ctrl, cc, ctrl10, cc10, s = k_eval(tb, idx, T)
            assert not s.any(), "⛔ 事件自己在對照池（當天應有原始偵測）"
            why = np.where(cc > 0, "", "配對格無對照股")
        else:
            sp = s_pool(Wd, H, RAWD)
            g = sp["G"][T - sp["r0"], idx]
            ctrl = np.full(len(T), np.nan); cc = np.zeros(len(T), np.int64)
            for q in range(len(T)):
                ctrl[q], cc[q] = s_one(Wd, sp, A, H, int(idx[q]), int(T[q]), int(fst[q]))
            ctrl10 = np.full(len(T), np.nan); cc10 = np.full(len(T), -1)
            why = np.where(cc > 0, "", np.where(cc < 0, "錨點量不可算", "配對格無對照股"))
        assert np.isfinite(g).all(), "⛔ 保留事件的 R 不可算"
        X = g - ctrl; dX = d * X
        EW = Wd["EW"][H][T]; Xu = g - EW
        ok = np.isfinite(X)
        # ── 格
        J_ = cell_stats(dX[ok], T[ok], H, w0, moni)
        J_["保留"] = int(len(T)); J_["配對剔除"] = dict(Counter(why[~ok].tolist())); J_["配對剔除數"] = int((~ok).sum())
        J_["對照數_中位"] = float(np.median(cc[ok])) if ok.any() else None
        J_["對照數_最小"] = int(cc[ok].min()) if ok.any() else None
        J_["X̄（未乘d）"] = float(X[ok].mean()) if ok.any() else None
        J_["d組成"] = {"+1": int((d[ok] > 0).sum()), "−1": int((d[ok] < 0).sum())}
        J_["R̄"] = float(g[ok].mean()) if ok.any() else None
        J_["對照R̄"] = float(ctrl[ok].mean()) if ok.any() else None
        J_["未配對_dXu"] = desc_ci(d[ok] * Xu[ok], T[ok], H, w0, moni)
        J_["未配對_dXu_全保留"] = desc_ci(d * Xu, T, H, w0, moni)
        if isK:
            ok10 = np.isfinite(ctrl10)
            J_["只配r10_dX"] = desc_ci(d[ok10] * (g[ok10] - ctrl10[ok10]), T[ok10], H, w0, moni)
            J_["只配r10_對照數_中位"] = float(np.median(cc10[ok10])) if ok10.any() else None
        mk = np.array(Wd["MARKET"])[idx]
        J_["上市"] = desc_ci(dX[ok & (mk == "twse")], T[ok & (mk == "twse")], H, w0, moni)
        J_["上櫃"] = desc_ci(dX[ok & (mk == "tpex")], T[ok & (mk == "tpex")], H, w0, moni)
        yr = Wd["YEAR"][T]
        J_["逐年"] = {str(y): {"n": int((ok & (yr == y)).sum()), "dX̄": float(dX[ok & (yr == y)].mean()) if (ok & (yr == y)).any() else None}
                      for y in sorted(set(yr.tolist()))}
        out["cells"][H] = J_
        # ── 包含關係（外層扣掉與內層同檔同日者；描述）
        for a_, b_ in PAIRS6:
            if a_ != vid:
                continue
            IN = raw_dense(Wd, b_)
            inn = IN[T, idx]
            out["pairs"][(b_, H)] = {"外層與內層同日": desc_ci(dX[ok & inn], T[ok & inn], H, w0, moni),
                                     "外層扣掉內層": desc_ci(dX[ok & ~inn], T[ok & ~inn], H, w0, moni),
                                     "同日件數": int((ok & inn).sum()), "外層件數": int(ok.sum())}
            del IN
        # ── 逐筆
        frames.append(pd.DataFrame({
            "sid": np.array(Wd["SIDS"])[idx], "market": mk, "H": H, "T": Wd["DATES"][T], "first": Wd["DATES"][fst], "d": E["d"],
            "R": g, "對照平均": ctrl, "對照數": cc, "X": X, "dX": dX,
            "對照平均_r10": ctrl10, "對照數_r10": cc10, "X_r10": g - ctrl10, "EW": EW, "X_未配對": Xu,
            "分群": clkey(T, H, w0, moni), "配對": np.where(ok, "有", why)}))
        # ── 假訊號臂（判定格）
        if H in HJ:
            out["fake"][H] = fake_arm(Wd, vid, vnum, H, isK, E, RAWD, tb if isK else None, A)
    if frames:
        os.makedirs(os.path.join(OUT, "events"), exist_ok=True)
        pd.concat(frames, ignore_index=True).to_csv(os.path.join(OUT, "events", "events_{}.csv.gz".format(vid)), index=False,
                                                    compression={"method": "gzip", "compresslevel": 6})
    out["sec"] = time.time() - t0
    return out


def fake_arm(Wd, vid, vnum, H, isK, E, RAWD, tb, A):
    w0, w1, moni = Wd["w0"], Wd["w1"], Wd["MONI"]
    v = PA.VMAP[vid]
    r0, r1 = w0, w1 - H
    idx = E["i"].astype(np.int64); T = E["T"].astype(np.int64)
    order = np.lexsort((T, idx))
    idx_s, T_s, lag_s = idx[order], T[order], E["lag"][order].astype(np.int64)
    stocks, starts = np.unique(idx_s, return_index=True)
    ends = np.r_[starts[1:], len(idx_s)]
    if isK:
        CAND = tb["base"]                      # rows r0..r1
    else:
        CAND = Wd["VALID"][r0:r1 + 1]
        sp = s_pool(Wd, H, RAWD)
    cands = {int(i): np.flatnonzero(CAND[:, i]) + r0 for i in stocks}
    acc = np.zeros((REPS, 2, NCL, 2)); cnt = np.zeros((REPS, 2, 5), np.int64)   # 抽出、剔除（斷點／成交）、配對格無對照股、可抽日不足、錨點不可算
    dfix = v["d"]
    for r in range(REPS):
        for ver in (0, 1):
            fi, fT, fl = [], [], []
            for i, a, b in zip(stocks, starts, ends):
                Tk = T_s[a:b]
                cand = cands[int(i)]
                if ver == 0:
                    cand = excl_past(cand, Tk)
                m = min(len(Tk), len(cand)); cnt[r, ver, 3] += len(Tk) - m
                if m == 0:
                    continue
                rng = np.random.default_rng([SEED_FAKE + r, Wd["CRC"][int(i)], vnum, H, ver])
                pick = np.sort(rng.choice(cand, size=m, replace=False))
                fi.append(np.full(m, i, np.int64)); fT.append(pick.astype(np.int64)); fl.append(lag_s[a:a + m])
            if not fi:
                continue
            fi = np.concatenate(fi); fT = np.concatenate(fT); fl = np.concatenate(fl)
            cnt[r, ver, 0] += len(fi)
            if isK:
                k = tb["k"]
                own = Wd["TRD1"][fT, fi] & ~Wd["BRK"][(k, H)][fT, fi] & np.isfinite(Wd["G"][H][fT, fi])
                cnt[r, ver, 1] += int((~own).sum())
                fi, fT = fi[own], fT[own]
                g, ctrl, cc, _, _, _ = k_eval(tb, fi, fT)
                okc = cc > 0
                cnt[r, ver, 2] += int((~okc).sum())
                sg = Wd["SGN"][k][fT, fi].astype(float)
                dd = np.full(len(fi), float(dfix)) if dfix in (1, -1) else (sg if dfix == "續" else -sg)
                dX = (dd * (g - ctrl))[okc]; TT = fT[okc]
            else:
                dX = []; TT = []
                for i, t, lg in zip(fi, fT, fl):
                    bars = Wd["BARS"][int(i)]
                    bi = int(np.searchsorted(bars, t))
                    if bi - lg < 0:
                        cnt[r, ver, 4] += 1; continue
                    f = int(bars[bi - lg])
                    if not (Wd["TRD1"][t, i] and np.isfinite(Wd["G"][H][t, i])) or own_brk(Wd, int(i), f, int(t) + H):
                        cnt[r, ver, 1] += 1; continue
                    cm, c_ = s_one(Wd, sp, A, H, int(i), int(t), f)
                    if c_ < 0:
                        cnt[r, ver, 4] += 1; continue
                    if c_ == 0:
                        cnt[r, ver, 2] += 1; continue
                    dX.append(float(dfix) * (Wd["G"][H][t, i] - cm)); TT.append(int(t))
                dX = np.asarray(dX, float); TT = np.asarray(TT, np.int64)
            if len(dX):
                cl = clkey(TT, H, w0, moni)
                np.add.at(acc[r, ver, :, 0], cl, 1.0)
                np.add.at(acc[r, ver, :, 1], cl, dX)
    return {"acc": acc, "cnt": cnt}


# ═════════════ fixture ═════════════
def _world(seed, n=260, S=48, zero=False):
    rng = np.random.default_rng(seed)
    w0, w1 = 70, n - 1
    Wd = {"w0": w0, "w1": w1}
    VALID = rng.random((n, S)) < 0.93
    Wd["VALID"] = VALID
    Wd["G"] = {H: np.where(VALID & (rng.random((n, S)) < 0.97), (0.0 if zero else 1.0) * rng.normal(0, 0.08, (n, S)), np.nan) for H in HA}
    for H in HA:
        Wd["G"][H][n - H:] = np.nan
    Wd["TRD1"] = VALID & (rng.random((n, S)) < 0.9)
    Wd["DECR"], Wd["DECP"], Wd["SGN"] = {}, {}, {}
    for k in KS:
        Wd["DECR"][k] = np.where(VALID, rng.integers(0, 3, (n, S)), -1).astype(np.int8)       # 只用 3 個十分位 ⇒ 格子常有人
        Wd["DECP"][k] = np.where(VALID, rng.integers(0, 3, (n, S)), -1).astype(np.int8)
        Wd["SGN"][k] = np.where(VALID, rng.choice([-1, 0, 1], (n, S), p=[0.45, 0.1, 0.45]), 0).astype(np.int8)
    Wd["BRK"] = {(k, H): rng.random((n, S)) < 0.05 for k in KS for H in HA}
    Wd["DECA60"] = np.where(VALID, rng.integers(0, 3, (n, S)), -1).astype(np.int8)
    Wd["DECA20"] = Wd["DECA60"]
    pb = rng.random((n, S)) < 0.01; g5 = rng.random((n, S)) < 0.01
    Wd["CSPB"] = np.cumsum(pb, axis=0).astype(np.int32); Wd["CSG5"] = np.cumsum(g5, axis=0).astype(np.int32)
    RAW = VALID & (rng.random((n, S)) < 0.04)
    Wd["RAWL"] = {vid: (np.nonzero(RAW)[1], np.nonzero(RAW)[0]) for vid in PA.VID}
    return Wd, RAW


def _brute_k(Wd, RAW, vid, H, i, t, only_r10=False):
    v = PA.VMAP[vid]; k = v["k"]
    xs = []
    for j in range(Wd["VALID"].shape[1]):
        if j == i:
            continue
        if not (Wd["DECR"][k][t, j] >= 0 and Wd["DECP"][k][t, j] >= 0):
            continue
        if Wd["DECR"][k][t, j] != Wd["DECR"][k][t, i]:
            continue
        if not only_r10 and Wd["DECP"][k][t, j] != Wd["DECP"][k][t, i]:
            continue
        sg = Wd["SGN"][k][t, j]
        if v["pre"] == "升" and sg != 1 or v["pre"] == "降" and sg != -1 or v["pre"] == "無" and sg == 0:
            continue
        if not Wd["TRD1"][t, j] or Wd["BRK"][(k, H)][t, j] or not np.isfinite(Wd["G"][H][t, j]) or RAW[t, j]:
            continue
        xs.append(Wd["G"][H][t, j])
    return (float(np.mean(xs)) if xs else np.nan), len(xs)


def _brute_s(Wd, RAW, H, i, t, f):
    A = Wd["DECA60"]; xs = []
    if A[f, i] < 0:
        return np.nan, -1
    for j in range(Wd["VALID"].shape[1]):
        if j == i or A[f, j] != A[f, i]:
            continue
        if not Wd["VALID"][t, j] or not Wd["TRD1"][t, j] or not np.isfinite(Wd["G"][H][t, j]) or RAW[t, j]:
            continue
        brk = False
        for q in range(f, t + H + 1):                         # 逐日：價格斷點日在 [f, t+H]、或連續缺 5 日的第 5 天以後落在 [f+4, t+H]
            dpb = Wd["CSPB"][q, j] - (Wd["CSPB"][q - 1, j] if q > 0 else 0)
            dg5 = Wd["CSG5"][q, j] - (Wd["CSG5"][q - 1, j] if q > 0 else 0)
            if dpb > 0 or (q >= f + 4 and dg5 > 0):
                brk = True; break
        if brk:
            continue
        xs.append(Wd["G"][H][t, j])
    return (float(np.mean(xs)) if xs else np.nan), len(xs)


def selftest():
    msgs = []
    # F1 十分位整數式 ＝ pd.qcut(rank(first), 10)
    rng = np.random.default_rng(11); bad = 0
    for q in range(400):
        m = int(rng.integers(10, 3000))
        v = np.round(rng.normal(0, 1, m), int(rng.integers(1, 4)))          # 大量同值
        a = decile_int(v)
        b = pd.qcut(pd.Series(v).rank(method="first"), 10, labels=False).to_numpy()
        bad += int((a != b).sum())
    assert bad == 0, bad
    msgs.append("F1 十分位整數式＝pd.qcut(rank first)（400 組、含大量同值）差 0")
    # F2 brk_vec ＝ H2.brk
    bad = 0
    for q in range(200):
        n = 200
        pb = rng.random(n) < 0.02; g5 = rng.random(n) < 0.03
        S = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
        a = np.where(rng.random(n) < 0.9, np.maximum(np.arange(n) - rng.integers(0, 12, n), 0), -1)
        for H in (3, 20, 60):
            vv = brk_vec(S["cs_pb"], S["cs_g5"], a, H)
            for t in range(n - H):
                if a[t] >= 0:
                    bad += int(vv[t] != H2.brk(S, int(a[t]), t + H))
    assert bad == 0, bad
    msgs.append("F2 硬斷點向量版＝H2.brk（200 條隨機序列 × H 3／20／60）差 0")
    # F3 K 對照（bincount 格表）＝ 逐檔迴圈；含假事件扣自己
    Wd, RAW = _world(5)
    RAWD = raw_dense(Wd, "K01")
    worst = 0.0; nchk = 0
    for vid in ("K01", "K07", "K14", "K40", "K50", "K20"):
        for H in HA:
            tb = k_tables(Wd, vid, H, RAWD)
            for q in range(150):
                t = int(rng.integers(Wd["w0"], Wd["w1"] - H + 1)); i = int(rng.integers(0, Wd["VALID"].shape[1]))
                if not tb["base"][t - tb["r0"], i]:
                    continue
                g, c1, n1, c10, n10, s = k_eval(tb, np.array([i]), np.array([t]))
                b1, m1 = _brute_k(Wd, RAW, vid, H, i, t); b10, m10 = _brute_k(Wd, RAW, vid, H, i, t, only_r10=True)
                assert n1[0] == m1 and n10[0] == m10, (vid, H, t, i, n1, m1, n10, m10)
                if m1:
                    worst = max(worst, abs(c1[0] - b1))
                if m10:
                    worst = max(worst, abs(c10[0] - b10))
                nchk += 1
    assert worst < 1e-12, worst
    msgs.append("F3 K 棒對照（格表＋扣自己）＝逐檔迴圈（{} 筆、主版＋只配 r10 版）最大差 {:.1e}".format(nchk, worst))
    # F4 S 對照 ＝ 逐檔逐日迴圈
    worst = 0.0; nchk = 0
    for H in HA:
        sp = s_pool(Wd, H, RAWD)
        for q in range(150):
            t = int(rng.integers(Wd["w0"], Wd["w1"] - H + 1)); i = int(rng.integers(0, Wd["VALID"].shape[1])); f = int(t - rng.integers(0, 60))
            c1, n1 = s_one(Wd, sp, Wd["DECA60"], H, i, t, f)
            b1, m1 = _brute_s(Wd, RAW, H, i, t, f)
            assert n1 == m1, (H, t, i, f, n1, m1)
            if m1 > 0:
                worst = max(worst, abs(c1 - b1))
            nchk += 1
    assert worst < 1e-12, worst
    msgs.append("F4 價格結構對照＝逐檔逐日迴圈（{} 筆）最大差 {:.1e}".format(nchk, worst))
    # F5 0 報酬 ⇒ X＝0（全部 R ＝ 0 的世界：主版、r10 版、S 版、未配對）
    Wz, RAWz = _world(6, zero=True)
    RAWDz = raw_dense(Wz, "K01")
    mx = 0.0
    for H in HA:
        tb = k_tables(Wz, "K14", H, RAWDz)
        rr, ii = np.nonzero(tb["base"])
        g, c1, n1, c10, n10, _ = k_eval(tb, ii, rr + tb["r0"])
        okk = n1 > 0
        mx = max(mx, float(np.max(np.abs((g - c1)[okk]))), float(np.max(np.abs((g - c10)[n10 > 0]))))
        sp = s_pool(Wz, H, RAWDz)
        for q in range(50):
            t = int(rng.integers(Wz["w0"], Wz["w1"] - H + 1)); i = int(rng.integers(0, 48))
            c1, n1 = s_one(Wz, sp, Wz["DECA60"], H, i, t, t)
            if n1 > 0 and np.isfinite(Wz["G"][H][t, i]):
                mx = max(mx, abs(Wz["G"][H][t, i] - c1))
    assert mx == 0.0, mx
    msgs.append("F5 0 報酬世界 ⇒ X＝0（K 主版／r10 版／S 版）最大 |X| {}".format(mx))
    # F6 已知報酬：事件 +10%，對照兩檔 +4%、−2% ⇒ 對照 +1%、X ＝ +9%；d＝−1 ⇒ dX ＝ −9%
    Wk = {"w0": 0, "w1": 30, "VALID": np.ones((31, 3), bool), "TRD1": np.ones((31, 3), bool),
          "G": {H: np.full((31, 3), np.nan) for H in HA},
          "DECR": {k: np.zeros((31, 3), np.int8) for k in KS}, "DECP": {k: np.zeros((31, 3), np.int8) for k in KS},
          "SGN": {k: np.ones((31, 3), np.int8) for k in KS}, "BRK": {(k, H): np.zeros((31, 3), bool) for k in KS for H in HA}}
    Wk["G"][20][5] = [0.10, 0.04, -0.02]
    RAWk = np.zeros((31, 3), bool); RAWk[5, 0] = True
    tb = k_tables(Wk, "K01", 20, RAWk)
    g, c1, n1, _, _, _ = k_eval(tb, np.array([0]), np.array([5]))
    assert n1[0] == 2 and abs(c1[0] - 0.01) < 1e-15 and abs((g - c1)[0] - 0.09) < 1e-15 and abs(-1 * (g - c1)[0] + 0.09) < 1e-15
    msgs.append("F6 已知：R＝+10%、對照 +4%／−2% ⇒ 對照 +1%、X＝+9%、d＝−1 ⇒ dX＝−9%")
    # F7 假訊號新預設的排除窗：[T−20, T] 含當天、⛔ 不看未來
    Tk = np.array([100])
    c_ = np.array([79, 80, 99, 100, 101, 120, 121, 140])
    got = excl_past(c_, Tk).tolist()
    assert got == [79, 80, 99, 121, 140], got
    msgs.append("F7 假訊號排除只看過去：真事件 100 ⇒ 排掉 100～120、保留 79／80／99（之前）與 121")
    # F8 分群彙總式 ＝ research11.cl_stats
    x = rng.normal(0, 1, 500); key = rng.integers(0, 40, 500)
    acc = np.zeros((NCL, 2)); np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a = agg_eval(acc); b = R11.cl_stats(x, key)
    assert abs(a["平均"] - b["mean"]) < 1e-12 and abs(a["lo"] - b["lo"]) < 1e-12 and a["n_eff"] == min(500, b["months"])
    msgs.append("F8 假訊號臂的分群彙總式＝research11.cl_stats")
    for m in msgs:
        print("✅ " + m, flush=True)
    return msgs


# ═════════════ 主程式 ═════════════
def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


def main():
    global OUT
    if "--out" in sys.argv:                          # 只給除錯（試跑不寫進正式輸出夾）
        OUT = sys.argv[sys.argv.index("--out") + 1]
    t0 = time.time()
    print("[時點] 本體開跑 {}".format(time.strftime("%F %T")), flush=True)
    fx = selftest()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official()
    F = pd.read_csv(os.path.join(FREQ, "freq.csv"), encoding="utf-8-sig", dtype={"vid": str})
    JUDGE = {r.vid: {20: bool(r.可判定_H20), 60: bool(r.可判定_H60)} for r in F.itertuples()}
    nJ = sum(J[20] + J[60] for J in JUDGE.values())
    assert nJ == N_FAM and sum(J[20] for J in JUDGE.values()) == 92, nJ
    DT = pd.read_csv(os.path.join(FREQ, "direction_table.csv"), encoding="utf-8-sig", dtype={"vid": str})
    NAME_DIR = {}
    for r in DT.itertuples():
        nd = str(r.名稱隱含方向)
        if r.vid.startswith("K"):
            NAME_DIR[r.vid] = 1 if "看漲" in nd else (-1 if "看跌" in nd else None)
        else:
            NAME_DIR[r.vid] = int(PA.VMAP[r.vid]["d"])
    sids = list(U["stock_id"]); mkts = list(U["market"]); S = len(sids)
    print("[資料] 快照 {}｜判定窗 [{}, {}]｜gate3 {:,} 檔｜Bonferroni z＝{:.4f}（α＝0.05／{}，雙側）".format(SHA[:10], W0, W1, S, Z_BONF, N_FAM), flush=True)
    # ── pass 1
    VALID = np.zeros((n, S), bool); TRD1 = np.zeros((n, S), bool)
    G = {H: np.full((n, S), np.nan) for H in HA}
    R10 = {k: np.full((n, S), np.nan) for k in KS}; PRD = {k: np.full((n, S), np.nan) for k in KS}
    BRK = {(k, H): np.ones((n, S), bool) for k in KS for H in HA}
    A60 = np.full((n, S), np.nan); A20 = np.full((n, S), np.nan)
    CSPB = np.zeros((n, S), np.int32); CSG5 = np.zeros((n, S), np.int32)
    BARS = [np.zeros(0, np.int32)] * S
    rawL = defaultdict(list); keptL = defaultdict(list); ACCT = defaultdict(Counter); HSH = {}; mism = 0; nok = 0
    ctx = mp.get_context("fork")
    with ctx.Pool(procs, initializer=_init, initargs=(cal, w0, w1, off)) as pool:
        for j, r in enumerate(pool.imap(load_one, list(zip(sids, mkts)), chunksize=8)):
            if r is None:
                continue
            nok += 1
            VALID[:, j] = r["valid"]; TRD1[:, j] = r["trd1"]; BARS[j] = r["bars"]
            for H in HA:
                G[H][:, j] = r["G"][H]
            for k in KS:
                R10[k][:, j] = r["R10"][k]; PRD[k][:, j] = r["PRD"][k]
                for H in HA:
                    BRK[(k, H)][:, j] = r["BRK"][(k, H)]
            A60[:, j] = r["A60"]; A20[:, j] = r["A20"]; CSPB[:, j] = r["cs_pb"]; CSG5[:, j] = r["cs_g5"]
            for vid, Tr in r["raw"].items():
                if len(Tr):
                    rawL[vid].append((np.full(len(Tr), j, np.int32), Tr))
            for key, e in r["kept"].items():
                keptL[key].append({"i": np.full(len(e["T"]), j, np.int32), **e})
            for key, c in r["acct"].items():
                ACCT[key].update(c)
            for vid, h in r["hsh"].items():
                HSH[(r["sid"], vid)] = h
            mism += r["mism"]
            if (j + 1) % 300 == 0:
                print("  … {:,}／{:,} 檔｜{:.0f}s".format(j + 1, S, time.time() - t0), flush=True)
    print("[讀檔＋偵測] 可用 {:,} 檔｜{:.0f}s".format(nok, time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True)
    CHK = {"fixture": fx}
    # ── 查核 1：重新偵測 ＝ 已提交事件檔（逐檔逐股：列數＋md5）
    eq = {}
    for vid in PA.VID:
        nm = PA.VMAP[vid]["name"].replace(" ", "_")
        p = os.path.join(FREQ, "events_{}_{}.csv.gz".format(vid, nm))
        blocks = defaultdict(list)
        with gzip.open(p, "rt", encoding="utf-8") as f:
            head = f.readline()
            assert head == HEADER, head
            for ln in f:
                blocks[ln.split(",", 1)[0]].append(ln)
        if lim:
            blocks = {s: v_ for s, v_ in blocks.items() if s in set(sids)}
        ref = {s: (len(v_), hashlib.md5("".join(v_).encode("utf-8")).hexdigest()) for s, v_ in blocks.items()}
        mine = {s: HSH[(s, vid)] for s in sids if (s, vid) in HSH and HSH[(s, vid)][0] > 0}
        same = ref == mine
        eq[vid] = {"列數_本支": int(sum(v_[0] for v_ in mine.values())), "列數_已提交": int(sum(v_[0] for v_ in ref.values())), "逐列相同": bool(same)}
        if not same:
            json.dump(eq, open(os.path.join(OUT, "ABORT_rows.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            raise SystemExit("⛔ 重新偵測與已提交事件檔不同：{} ⇒ 中止（未算任何報酬）".format(vid))
    CHK["事件檔逐列相同"] = {"變體數": len(eq), "全同": all(v_["逐列相同"] for v_ in eq.values()),
                        "總列數": int(sum(v_["列數_本支"] for v_ in eq.values()))}
    assert mism == 0, "⛔ 事件檔事前量 ≠ 本支矩陣：{} 筆".format(mism)
    CHK["事前量逐位元相同（K：r10、期間報酬；S：錨點 r60／r20）"] = "差 0 筆"
    # 保留數 ＝ freq.csv
    kd = {}
    for r in F.itertuples():
        for H in HA:
            got = ACCT[(r.vid, H)]["保留"]
            kd[(r.vid, H)] = got == getattr(r, "保留_H{}".format(H))
    assert lim or all(kd.values()), [k for k, v_ in kd.items() if not v_][:5]
    CHK["保留數＝freq.csv"] = "{}／{}".format(sum(kd.values()), len(kd))
    print("[查核1] 重新偵測與已提交事件檔 96／96 逐列相同（{:,} 列）；事前量逐位元同；保留數＝freq.csv {}｜{:.0f}s".format(
        CHK["事件檔逐列相同"]["總列數"], CHK["保留數＝freq.csv"], time.time() - t0), flush=True)
    # ── 十分位、EW
    rowsT = range(w0, w1 + 1); rowsA = range(0, w1 + 1)
    DECR, DECP, SGN = {}, {}, {}
    for k in KS:
        base = VALID & np.isfinite(R10[k]) & np.isfinite(PRD[k])
        DECR[k] = dec_matrix(R10[k], base, rowsT); DECP[k] = dec_matrix(PRD[k], base, rowsT)
        SGN[k] = np.sign(np.nan_to_num(R10[k])).astype(np.int8)
    DECA60 = dec_matrix(A60, VALID & np.isfinite(A60), rowsA); DECA20 = dec_matrix(A20, VALID & np.isfinite(A20), rowsA)
    del R10, PRD, A60, A20
    EW = {}
    for H in HA:
        with np.errstate(invalid="ignore"):
            cnt = np.isfinite(G[H]).sum(axis=1); s_ = np.nansum(G[H], axis=1)
        EW[H] = np.where(cnt > 0, s_ / np.maximum(cnt, 1), np.nan)
    moni = np.asarray(cal.year * 12 + cal.month) - (cal[w0].year * 12 + cal[w0].month)
    W.update(w0=w0, w1=w1, VALID=VALID, TRD1=TRD1, G=G, DECR=DECR, DECP=DECP, SGN=SGN, BRK=BRK, DECA60=DECA60, DECA20=DECA20,
             CSPB=CSPB, CSG5=CSG5, EW=EW, MONI=moni, YEAR=np.asarray(cal.year), DATES=np.array([str(d.date()) for d in cal]),
             SIDS=sids, MARKET=mkts, BARS=BARS, CRC=[zlib.crc32(s.encode("utf-8")) for s in sids], JUDGE=JUDGE,
             RAWL={vid: ((np.concatenate([a for a, _ in rawL[vid]]), np.concatenate([b for _, b in rawL[vid]])) if rawL[vid]
                         else (np.zeros(0, np.int32), np.zeros(0, np.int32))) for vid in PA.VID})
    for key, L in keptL.items():
        EVT[key] = {c_: np.concatenate([e[c_] for e in L]) for c_ in ("i", "T", "first", "d", "lag")}
    print("[十分位、基準] 完成｜{:.0f}s".format(time.time() - t0), flush=True)
    print("[時點] 本體第一次讀報酬（變體迴圈開始）{}".format(time.strftime("%F %T")), flush=True)
    t_first = time.strftime("%F %T")
    # ── pass 2：逐變體
    order = sorted(PA.VID, key=lambda v_: -sum(len(EVT.get((v_, H), {"i": []})["i"]) for H in HJ))
    RES = {}
    with ctx.Pool(procs) as pool:
        for r in pool.imap_unordered(do_variant, order, chunksize=1):
            RES[r["vid"]] = r
            print("  [{}] {}｜{:.0f}s（本變體 {:.0f}s）".format(len(RES), r["vid"], time.time() - t0, r["sec"]), flush=True)
    # ── 彙整
    cells = []; FK = []; per_rep = {0: np.zeros(REPS, int), 1: np.zeros(REPS, int)}; per_rep3 = {0: np.zeros(REPS, int), 1: np.zeros(REPS, int)}
    FACC = {}
    for vid in PA.VID:
        v = PA.VMAP[vid]; R = RES[vid]
        for H in HA:
            a = ACCT[(vid, H)]
            row = {"vid": vid, "型態": v["name"], "族": v["fam"], "H": H, "d": v["d"], "名稱方向": NAME_DIR[vid],
                   "原始": int(sum(a.values())), "合併後": int(sum(a.values()) - a["合併掉"]), "合併掉": a["合併掉"],
                   "剔除_硬斷點": a["剔除_硬斷點"], "剔除_T+1停牌": a["剔除_T+1停牌"], "剔除_T+1開盤漲停": a["剔除_T+1開盤漲停"],
                   "剔除_T+1開盤跌停": a["剔除_T+1開盤跌停"], "保留": a["保留"]}
            fr = F[F["vid"] == vid].iloc[0]
            if H in HJ and not JUDGE[vid][H]:
                row.update({"身分": "依構造不可判定", "n_eff上限": int(fr["n_eff上限_H{}".format(H)]), "結果": "依構造不可判定"})
            elif H == 120 and not (JUDGE[vid][20] or JUDGE[vid][60]):
                row.update({"身分": "H120 描述（⛔ 未讀：兩個 H 都依構造不可判定）", "結果": "—"})
            else:
                J_ = R["cells"][H]
                row.update({"身分": "判定格" if H in HJ else "H120 描述", "n_eff上限": int(fr["n_eff上限_H{}".format(H)]) if H in HJ else None})
                row.update({k_: v_ for k_, v_ in J_.items() if not isinstance(v_, dict)})
                row["配對剔除明細"] = json.dumps(J_.get("配對剔除", {}), ensure_ascii=False)
                for nm_ in ("未配對_dXu", "只配r10_dX", "上市", "上櫃"):
                    if nm_ in J_:
                        for kk in ("n", "平均", "lo", "hi", "標籤"):
                            if kk in J_[nm_]:
                                row["{}_{}".format(nm_, kk)] = J_[nm_][kk]
                if H in HJ:
                    fk = R["fake"][H]; FACC[(vid, H)] = fk
                    for ver, vn in ((0, "新預設"), (1, "不排除")):
                        res_ = [agg_eval(fk["acc"][r_, ver]) for r_ in range(REPS)]
                        x2 = sum(1 for q in res_ if q and q["結果"] == "結果②"); x3 = sum(1 for q in res_ if q and q["結果"] == "結果③")
                        row["假訊號_{}_x2".format(vn)] = x2; row["假訊號_{}_x3".format(vn)] = x3
                        row["假訊號_{}_平均dX".format(vn)] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                        c_ = fk["cnt"][:, ver].sum(axis=0)
                        row["假訊號_{}_帳".format(vn)] = json.dumps({"抽出": int(c_[0]), "剔除": int(c_[1]), "配對格無對照股": int(c_[2]),
                                                                  "可抽日不足": int(c_[3]), "錨點不可算": int(c_[4])}, ensure_ascii=False)
                        for r_, q in enumerate(res_):
                            FK.append({"vid": vid, "H": H, "版本": vn, "r": r_, **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                            if q and q["結果"] == "結果②":
                                per_rep[ver][r_] += 1
                            if q and q["結果"] == "結果③":
                                per_rep3[ver][r_] += 1
            cells.append(row)
    C = pd.DataFrame(cells)
    judged = C[C["身分"] == "判定格"]
    a_ = int((judged["結果"] == "結果②").sum()); b_ = int((judged["結果"] == "結果③").sum())
    M0 = int(per_rep[0].max()); M1 = int(per_rep[1].max())
    fam = {"N": N_FAM, "純運氣": N_FAM * 0.025, "a_d方向過關": a_, "b_反方向過關": b_,
           "假訊號_新預設_30次全族d方向過關格數": per_rep[0].tolist(), "假訊號_新預設_最大": M0,
           "假訊號_新預設_分佈": dict(sorted(Counter(per_rep[0].tolist()).items())),
           "假訊號_不排除_30次": per_rep[1].tolist(), "假訊號_不排除_最大": M1,
           "假訊號_新預設_30次全族反方向過關格數": per_rep3[0].tolist(),
           "與運氣分不開": bool(a_ <= M0)}
    fam["族結論句"] = ("本族可判定 N＝{} 格，純運氣約 {}×2.5%＝{:.1f} 格會單邊過關；實際 d 方向過關 {} 格、反方向 {} 格"
                    "（假訊號臂 30 次各自數全族 d 方向過關格數：最大 {} 格{}）{}").format(
        N_FAM, N_FAM, N_FAM * 0.025, a_, b_, M0, "" if a_ > M0 else "，a 沒有超過", "" if a_ > M0 else "，與運氣分不開")
    # 句子
    sent = []
    for i_, row in C.iterrows():
        sent.append(sentence(row, fam))
    C["句子"] = sent
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(OUT, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    np.savez_compressed(os.path.join(OUT, "fake_acc.npz"), keys=np.array(["{}_{}".format(k[0], k[1]) for k in FACC]),
                        acc=np.stack([FACC[k]["acc"] for k in FACC]), cnt=np.stack([FACC[k]["cnt"] for k in FACC]))
    # 逐年
    BY = []
    for vid in PA.VID:
        for H in HA:
            J_ = RES[vid]["cells"].get(H)
            if J_ and "逐年" in J_:
                for y, q in J_["逐年"].items():
                    BY.append({"vid": vid, "型態": PA.VMAP[vid]["name"], "H": H, "年": y, **q})
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    pairs = {}
    for a2, b2 in PAIRS6:
        for H in HA:
            p_ = RES[a2]["pairs"].get((b2, H))
            if p_:
                pairs["{}⊃{}_H{}".format(a2, b2, H)] = p_
    freqj = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    SUM = {"性質": "PREREG型態全量 本體（單筆層；可判定 180 格）", "登錄": "型態全量_單筆層登錄 台股策略線 seq3 sha b7b4a05af0341797",
           "裁定": "seq173 §二、seq175 §一§三、seq177 §一③", "快照": SHA, "判定窗": [W0, W1], "gate3母體": S, "可用檔數": nok,
           "時點": {"本體開跑": time.strftime("%F %T", time.localtime(t0)), "第一次讀報酬": t_first, "完成": time.strftime("%F %T")},
           "Bonferroni_z": Z_BONF, "族": fam, "包含關係6組": pairs, "查核": CHK,
           "重疊_指名配對（引 freq.json）": freqj.get("重疊_指名配對"),
           "格": {"{}_H{}".format(vid, H): RES[vid]["cells"].get(H) for vid in PA.VID for H in HA if RES[vid]["cells"].get(H)}}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    write_report(C, fam, pairs, CHK, SUM, freqj)
    print("[族] a＝{}、b＝{}｜假訊號 新預設 30 次：{}（最大 {}）｜不排除 最大 {}".format(a_, b_, per_rep[0].tolist(), M0, M1), flush=True)
    print(fam["族結論句"], flush=True)
    print("完成 {:.0f}s".format(time.time() - t0), flush=True)


def sentence(row, fam):
    nm = row["型態"]; H = int(row["H"])
    if row["結果"] == "依構造不可判定":
        return "{}（H{}）：依構造不可判定（n_eff 上限 {}）".format(nm, H, row["n_eff上限"])
    if H == 120:
        if row["結果"] == "—":
            return "{}（H120）：⛔ 未讀（兩個 H 都依構造不可判定）".format(nm)
        return "{}（H120）：依構造不可判定（只描述：d×X̄ {}、中位 {}）".format(nm, pct(row.get("dX̄")), pct(row.get("中位")))
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(int(row["n_eff"])) if row.get("出口") == "出口②" else ""
    rs = row["結果"]
    if rs == "樣本不足以分辨":
        return "{}之後 {} 天：樣本不足以分辨（配對後 n_eff＝{}）".format(nm, H, int(row["n_eff"]) if np.isfinite(row.get("n_eff", np.nan)) else 0)
    if rs == "結果①":
        return "{}{}之後 {} 天，比同樣事前走勢、沒出現型態的股票：測不出（d×X̄ {}，95% CI {} ～ {}）".format(pre, nm, H, pct(row["dX̄"]), pct(row["lo"]), pct(row["hi"]))
    x2 = row.get("假訊號_新預設_x2", 0) or 0
    warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
    if rs == "結果②":
        s = "{}{}{}之後 {} 天，比同樣事前走勢、沒出現型態的股票，照文獻實測方向多走 {}".format(warn, pre, nm, H, pct(abs(row["dX̄"]))[1:])
    else:
        d = row["d"]
        if d in (1, -1, "1", "-1"):
            word = "多漲" if row["X̄（未乘d）"] > 0 else "多跌"
            s = "{}{}之後 {} 天，跟文獻實測方向相反：比對照組{} {}".format(pre, nm, H, word, pct(abs(row["X̄（未乘d）"]))[1:])
        else:
            word = "逆著事前趨勢" if d == "續" else "順著事前趨勢"
            s = "{}{}之後 {} 天，跟文獻實測方向相反：比對照組{}多走 {}".format(pre, nm, H, word, pct(abs(row["dX̄"]))[1:])
    s += "（95% CI {} ～ {}）".format(pct(row["lo"]), pct(row["hi"]))
    s += "；Bonferroni（0.05／180）也不含 0 ⇒ 可單獨引用" if row.get("bonf不含0") else "；單格過關、但全族與運氣分不開（Bonferroni 下界含 0，⛔ 不單獨引用）"
    nd = row["名稱方向"]
    if nd in (1, -1) and np.isfinite(row.get("X̄（未乘d）", np.nan)):
        s += "；照名稱方向讀：名稱方向（{}）多走 {}".format("看漲" if nd == 1 else "看跌", pct(nd * row["X̄（未乘d）"]))
    return s


def write_report(C, fam, pairs, CHK, SUM, freqj):
    L = []
    A = L.append
    A("# PREREG型態全量 本體報告（台股，單筆層，可判定 180 格）\n")
    A("> 登錄 seq3（sha b7b4a05af0341797）｜裁定 seq173 §二、seq175 §一§三、seq177 §一③｜快照 main `{}`｜主窗 {}～{}｜gate3 {:,} 檔（可讀 {:,}）".format(
        SHA[:10], W0, W1, SUM["gate3母體"], SUM["可用檔數"]))
    A("> 時點：本體開跑 {}｜第一次讀報酬 {}｜完成 {}".format(SUM["時點"]["本體開跑"], SUM["時點"]["第一次讀報酬"], SUM["時點"]["完成"]))
    A("> ⛔ 單筆層：任何一格過關，也不可說「照這個型態交易贏 0050」；要進組合層須另開一件。⛔ 已測型態（頭肩底、旗形、費波那契、錘子、射擊之星）不因本件改結論。\n")
    A("## 一、族結論（登錄 §七）\n")
    A("**" + fam["族結論句"] + "**\n")
    A("```")
    A("可判定 N＝180（H20 92＋H60 88），純運氣約 180×2.5%＝4.5 格單邊過關")
    A("實際：d 方向過關（結果②）a＝{}｜反方向（結果③）b＝{}".format(fam["a_d方向過關"], fam["b_反方向過關"]))
    A("假訊號臂（新預設：只排除過去 20 日）30 次、每次全族 d 方向過關格數：{}".format(fam["假訊號_新預設_30次全族d方向過關格數"]))
    A("  分佈 {}｜最大 {}".format(fam["假訊號_新預設_分佈"], fam["假訊號_新預設_最大"]))
    A("假訊號臂（不排除版，描述）30 次：{}｜最大 {}".format(fam["假訊號_不排除_30次"], fam["假訊號_不排除_最大"]))
    A("假訊號臂（新預設）每次全族反方向過關格數：{}".format(fam["假訊號_新預設_30次全族反方向過關格數"]))
    A("⇒ a {} 最大值 ⇒ {}".format("＞" if fam["a_d方向過關"] > fam["假訊號_新預設_最大"] else "≤",
                               "不必加「與運氣分不開」" if not fam["與運氣分不開"] else "句尾加「與運氣分不開」"))
    A("```\n")
    J = C[C["身分"] == "判定格"]
    ok1 = J[(J["結果"].isin(["結果②", "結果③"])) & (J["bonf不含0"] == True)]    # noqa: E712
    A("## 二、可以單獨對使用者講的格（seq173 ③：95% CI 與 Bonferroni 0.05／180 下界都不含 0；依變體編號排，⛔ 不依效果排）\n")
    if len(ok1):
        for _, r in ok1.iterrows():
            A("- " + r["句子"])
    else:
        A("- （無）")
    A("")
    ok2 = J[(J["結果"].isin(["結果②", "結果③"])) & (J["bonf不含0"] != True)]    # noqa: E712
    A("只過 95% CI、沒過 Bonferroni 的格（只能寫「單格過關、但全族與運氣分不開」，⛔ 不單獨引用）：{} 格 ⇒ {}\n".format(
        len(ok2), "、".join("{}{}_H{}（{}）".format(r["vid"], r["型態"], r["H"], r["結果"]) for _, r in ok2.iterrows()) or "無"))
    A("## 三、每格全報（判定格 180＋依構造不可判定 12；依編號排）\n")
    A("dX ＝ d × (R_e − 主對照平均)。主對照：K 棒＝同日 × r10 十分位 × 型態期間報酬十分位 × 同事前門檻 × 當天沒出現；價格結構＝錨點 r60（島型、V 型 r20）十分位。")
    A("欄：保留｜配對剔除｜n｜n_eff｜出口｜d×X̄｜95% CI（曆月／60 日區段分群）｜Bonferroni CI｜非重疊 CI｜中位｜勝率｜p10／p90｜最差｜結果｜假訊號 x／30（新預設／不排除）｜只配 r10 d×X̄〔CI〕｜未配對 d×X̄\n")
    for H in HJ:
        A("### H{}\n".format(H))
        A("| vid | 型態 | d | 保留 | 配對剔除 | n | n_eff | 出口 | d×X̄ | 95% CI | Bonf CI | 非重疊 CI | 中位 | 勝率 | p10／p90 | 最差 | 結果 | 假 x／30 | 只配 r10 | 未配對 |")
        A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in C[(C["H"] == H)].iterrows():
            if r["結果"] == "依構造不可判定":
                A("| {} | {} | {} | {} | — | — | 上限 {} | — | — | — | — | — | — | — | — | — | **依構造不可判定** | — | — | — |".format(
                    r["vid"], r["型態"], r["d"], r["保留"], r["n_eff上限"]))
                continue
            if not (isinstance(r.get("n_eff"), (int, float, np.integer, np.floating)) and np.isfinite(r.get("n_eff"))):
                A("| {} | {} | {} | {} | {} | 0 | — | 出口① | — | — | — | — | — | — | — | — | 樣本不足以分辨 | — | — | — |".format(
                    r["vid"], r["型態"], r["d"], r["保留"], r.get("配對剔除數")))
                continue
            A("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {}～{} | {}～{} | {}～{} | {} | {:.1%} | {}／{} | {} | {} | {}／{} | {} | {} |".format(
                r["vid"], r["型態"], r["d"], r["保留"], int(r["配對剔除數"]), int(r["n"]), int(r["n_eff"]), r["出口"], pct(r["dX̄"]),
                pct(r["lo"]), pct(r["hi"]), pct(r["bonf_lo"]), pct(r["bonf_hi"]), pct(r["lo_非重疊"]), pct(r["hi_非重疊"]),
                pct(r["中位"]), r["勝率"], pct(r["p10"]), pct(r["p90"]), pct(r["最差"]), r["結果"],
                int(r["假訊號_新預設_x2"]), int(r["假訊號_不排除_x2"]),
                ("{}〔{}～{}〕".format(pct(r.get("只配r10_dX_平均")), pct(r.get("只配r10_dX_lo")), pct(r.get("只配r10_dX_hi")))
                 if isinstance(r.get("只配r10_dX_平均"), float) and np.isfinite(r.get("只配r10_dX_平均")) else "—"),
                pct(r.get("未配對_dXu_平均"))))
        A("")
    A("### 每格結果句（照登錄 §七 形狀；依編號）\n")
    for H in HJ:
        for _, r in C[C["H"] == H].iterrows():
            A("- " + r["句子"])
    A("")
    A("## 四、H120 全族描述（依構造不可判定；⛔ 不印 CI、⛔ 不判）\n")
    A("| vid | 型態 | 保留 | n | d×X̄ | 中位 | p10／p90 | 最差 | 未配對 d×X̄ |")
    A("|---|---|---|---|---|---|---|---|---|")
    for _, r in C[C["H"] == 120].iterrows():
        if r["結果"] == "—":
            A("| {} | {} | {} | ⛔ 未讀（兩個 H 都依構造不可判定） | | | | | |".format(r["vid"], r["型態"], r["保留"]))
            continue
        A("| {} | {} | {} | {} | {} | {} | {}／{} | {} | {} |".format(r["vid"], r["型態"], r["保留"], int(r["n"]), pct(r["dX̄"]), pct(r["中位"]),
                                                                  pct(r["p10"]), pct(r["p90"]), pct(r["最差"]), pct(r.get("未配對_dXu_平均"))))
    A("")
    A("## 五、包含關係 6 組（seq175 §三：照算、N 照 180、⛔ 不因重疊扣）\n")
    A("| 組 | H | 外層 d×X̄〔結果〕 | 內層 d×X̄〔結果〕 | 外層與內層同檔同日（描述） | 外層扣掉內層（描述） |")
    A("|---|---|---|---|---|---|")
    for a2, b2 in PAIRS6:
        for H in HJ:
            ra = C[(C["vid"] == a2) & (C["H"] == H)].iloc[0]; rb = C[(C["vid"] == b2) & (C["H"] == H)].iloc[0]
            p_ = pairs.get("{}⊃{}_H{}".format(a2, b2, H), {})
            def fx_(q):
                return "n {}：{}〔{}～{}〕".format(q.get("n", 0), pct(q.get("平均")), pct(q.get("lo")), pct(q.get("hi"))) if q and q.get("n") else "—"
            def cell_(r):
                return "依構造不可判定" if r["結果"] == "依構造不可判定" else "{}〔{}〕".format(pct(r["dX̄"]), r["結果"])
            A("| {}{}⊃{}{} | {} | {} | {} | {} | {} |".format(a2, PA.VMAP[a2]["name"], b2, PA.VMAP[b2]["name"], H, cell_(ra), cell_(rb),
                                                             fx_(p_.get("外層與內層同日")), fx_(p_.get("外層扣掉內層"))))
    A("")
    A("## 六、只配 r10 的對照版（seq1 原主對照；描述、並列）與未配對版（前提吃掉多少）\n")
    k = J[J["族"] == "K"].copy()
    k["r10lab"] = k["只配r10_dX_標籤"]
    diff = k[k["r10lab"] != k["結果"]]
    A("```")
    A("K 棒判定格 {} 格：主版（雙十分位）與只配 r10 版的結果標籤不同 {} 格".format(len(k), len(diff)))
    for _, r in diff.iterrows():
        A("  {}{} H{}：主版 {} {}｜只配 r10 {} {}".format(r["vid"], r["型態"], r["H"], r["結果"], pct(r["dX̄"]), r["r10lab"], pct(r["只配r10_dX_平均"])))
    A("只配 r10 版的全族：結果② {} 格、結果③ {} 格（描述、不計 N）".format(int((k["r10lab"] == "結果②").sum()), int((k["r10lab"] == "結果③").sum())))
    A("|主版 d×X̄| 中位 {}｜|只配 r10 d×X̄| 中位 {}｜|未配對 d×X̄| 中位 {}（K 棒判定格）".format(
        pct(float(np.nanmedian(np.abs(k["dX̄"])))), pct(float(np.nanmedian(np.abs(k["只配r10_dX_平均"])))), pct(float(np.nanmedian(np.abs(k["未配對_dXu_平均"]))))))
    s_ = J[J["族"] != "K"]
    A("價格結構判定格 {} 格：|配對 d×X̄| 中位 {}｜|未配對 d×X̄| 中位 {}".format(len(s_), pct(float(np.nanmedian(np.abs(s_["dX̄"])))),
                                                                  pct(float(np.nanmedian(np.abs(s_["未配對_dXu_平均"]))))))
    A("未配對版（R_e − gate3 等權同段；描述）結果標籤：結果② {} 格、結果③ {} 格（180 格中）".format(int((J["未配對_dXu_標籤"] == "結果②").sum()), int((J["未配對_dXu_標籤"] == "結果③").sum())))
    A("```\n")
    A("## 七、上市／上櫃、逐年（描述）\n")
    A("每格上市、上櫃的 d×X̄ 與 CI 在 `cells.csv`（上市_*、上櫃_* 欄）；逐年 n 與 d×X̄ 在 `by_year.csv`。\n")
    A("## 八、重疊（引頻率階段 freq.json；原始事件同檔同日 ÷ 較少者）\n")
    A("```")
    for k_, q in (SUM.get("重疊_指名配對（引 freq.json）") or {}).items():
        A("{}：同日 {}｜重疊率 {}".format(k_, q.get("同日件數"), q.get("重疊率_對較少者", "—")))
    A("```")
    A("⚠ K28 平頭底部、K53 平頭頂部特別頻繁（原始約 32 萬、28 萬筆）：0.2% 的「≈」容差在台股跳動單位下很容易剛好相等；設計參數照登錄、⛔ 不調（seq175 §三）。\n")
    A("## 九、依構造不可判定清單（⛔ 不讀報酬、⛔ 不計 N）\n")
    for _, r in C[C["結果"] == "依構造不可判定"].iterrows():
        A("- {}{} H{}：n_eff 上限 {}".format(r["vid"], r["型態"], r["H"], r["n_eff上限"]))
    A("")
    A("## 十、事件帳與查核\n")
    A("```")
    A("重新偵測 ＝ 已提交事件檔：{}（{:,} 列）｜事前量逐位元同｜保留數＝freq.csv {}".format(
        "96／96 逐列相同" if CHK["事件檔逐列相同"]["全同"] else "⛔", CHK["事件檔逐列相同"]["總列數"], CHK["保留數＝freq.csv"]))
    for m in CHK["fixture"]:
        A("✅ " + m)
    A("```")
    A("每格原始／合併後／合併掉／剔除（硬斷點、T＋1 停牌、開盤漲停、開盤跌停）／保留／配對剔除 ⇒ `cells.csv`；逐筆 ⇒ `events/events_<vid>.csv.gz`；"
      "假訊號臂逐次 ⇒ `fake_reps.csv`、逐群累加 ⇒ `fake_acc.npz`。\n")
    A("## 十一、讀法（全文見 researchPatAll.py docstring C1～C12；★ 兩種讀法處）\n")
    for ln in (__doc__ or "").split("⭐ 登錄沒逐字寫", 1)[1].splitlines()[1:]:
        if ln.strip():
            A("    " + ln.strip())
    A("")
    open(os.path.join(OUT, "PATALL_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
