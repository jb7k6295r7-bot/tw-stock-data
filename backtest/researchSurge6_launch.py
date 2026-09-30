# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：低檔發動當下有什麼訊號、從低點到第一頂分段多出什麼訊號，以及發動當下能不能分出來（描述＋參考，⛔ 不計 N）——回測線計算子代理。
使用者原話：「找找看股票從低檔發動當下有什麼訊號，然後從低點到第一頂分段，看中間會多出什麼訊號」

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_launch [--check | --page]

═══ 讀法（寫死於 2026-09-30 19:42（台北），在算任何數字之前）═══
 L1 對象：seq6 飆股事件（~/s6work/events.npz），事件 ≥ 30 的全部格（同 end_desc／progress_desc）；逐格算、取格中位（附 p10～p90）
 L2 低檔位置：pos(d) ＝ (c[d] − 最低) ÷ (最高 − 最低)，最高／最低 ＝ 含 d 的最近 250 根有效 K 棒還原收盤（不足 250 根 ⇒ 沒值、不算低檔）；最高 ＝ 最低 ⇒ 沒值
    版本：V1 pos ≤ 0.2、V2 pos ≤ 0.4、V3 pos ≤ 0.6、V4「之前沒大漲」＝ pos ≤ 0.4 ∧ 120 日報酬 Q 碼 ≠ 5 ∧ 20 日漲停天數（F 原值）＜ 3（四版都報）
    事件只取起漲日 t 符合該版者；該版事件 ≥ 30 的格才進格中位（各版格數照報）
 L3 第一頂 H1：c[t..P]（P ＝ 事件 (t, t＋H] 最高收盤日）用 mid_desc.pullbacks，第一個「新高日 a ＞ 0 且之後回落 ≥ 20%（lo ≤ hi × 0.8 ×(1＋1e−9)）」的 a；沒有 ⇒ H1 ＝ P
    進度點 p ∈ {0, 10, …, 100}%：p＝0 ⇒ t；其餘 ＝ (t, H1] 內第一個 c ≥ (c[t] ＋ p ×(c[H1] − c[t])) ×(1 − 1e−9) 的日子（p＝100 ⇒ 第一次到 H1 的收盤價）；各點距 t 天數（交易日索引差）
 L4 訊號 ① 特徵表（seq5 levels() 全部級距，Q／F 表，照可得時點）：該點當天的級距
    ② 當下發生（14＋2 個；一般通用參數；以該點或前 2 根有效 K 棒內「發生」算 ＝ 近 3 日）：
      MACD 金叉（EMA12、EMA26、DEA＝EMA9，DIF 由 ≤DEA 轉 ＞DEA）｜KD 金叉（9 日 RSV、K＝⅔K＋⅓RSV、D＝⅔D＋⅓K，K 由 ≤D 轉 ＞D）｜RSI14（Wilder）由 ≤50 轉 ＞50｜
      MA20 由 ≤MA60 轉 ＞MA60｜收盤 ＞ 前 20 根最高收盤｜收盤 ＞ 前 55 根最高收盤｜成交量 ≥ 前 20 根均量 × 2｜收盤由 ≤MA20 轉 ＞MA20（布林中軌）｜
      收盤由 ≤上軌 轉 ＞上軌（20 日、2 倍標準差、母體 std）｜OBV 由 ≤OBV 的 20 日均 轉 ＞｜三大法人合計（stocks_inst total）連 3 根淨買 ＞0｜
      營收近 3 月年增平均 ＞ 20%（同 seq5 yoy 的 3 期平均、照公布可得期）且 近 20 根漲幅 ＜ 10%｜收盤 ＞ 前 250 根最高收盤（一年新高）｜
      月營收創 24 月新高（F 表 d_revhi ＝ 1，狀態）｜被列注意（注意公告日）｜進入處置（處置起日）
      價量用還原價（high／low 也還原）、成交量用原始股數；指標在有效 K 棒序列上算
 L5 描述：每個點、每個訊號的涵蓋率（格中位）；一般股-日對照 ＝ 兩段內有 K 棒且 hdef6 ≥ H 的全部股-日（同 progress_desc），倍數 ＝ 涵蓋率 ÷ 一般
    「這一段新出現」＝ 比上一點增加 ≥ 10 個百分點；「發動訊號」＝ t 點涵蓋率 ≥ 30% 且 倍數 ＞ 1.5
    描述用全部事件（2021～2026-08）；另報探索段事件版供判斷挑特徵
 L6 判斷（當下可用）：母體 ＝ 該版低檔位置的全部股-日（有 K 棒、hdef6 ≥ H、探索 2021-01～2023-12／確認 2024-01～2026-08 依日期）
    候選 ＝ ② 的 16 個（近 3 日）＋ ① 裡「探索段事件（任一版）t 點為發動訊號」的級距（聯集）；組合 ＝ 候選同時 ≥ k 個，k ＝ 1～10
    標籤 ＝ seq5 S1 grid 標籤：(d, d＋H] 內最高收盤 ≥ c[d] ×(1＋g) ×(1 − 1e−9)（任一天）；每格比例 ÷ 同格母體基準 ＝ 倍數，取格中位（該格母體與訊號日各 ≥ 30 才算）
    探索段依「倍數格中位」排名，前 10 名（單一訊號與組合合併排）到確認段照報，⛔ 不依確認段重排
    另報：每天平均幾檔（段內每個交易日符合的股數平均）；一年內先跌 15% ＝ (d, d＋250] 內第一次收盤 ≤ c[d] × 0.85 早於第一次收盤 ≥ c[d] × 1.15（或從未 +15%）的比例，只算 d＋250 ≤ 2026-08-31 的日子
 L8（2026-09-30 19:44（台北）補，仍在算任何數字之前；協調者轉使用者：「特徵也可以不一定要是訊號！」）：
    狀態／特徵與當下訊號同等重要 ⇒ 描述、時間軸、「新出現」「發動當下就有」、判斷，兩類都做、分兩區呈現；特徵表全部級距依類別完整呈現
    另加「低檔打底」狀態量（當天收盤可判；每天有 K 棒的母體橫斷面五等分，同 S10 qtie）：
      低檔盤整天數 ＝ 連續（到當根為止）pos ≤ 0.5 的有效 K 棒數｜距一年最低點幾根 ＝ 當根 − 最近 250 根最低收盤那根（同價取最近）｜
      量縮程度 ＝ 近 20 根均額 ÷ 再之前 250 根均額｜波動收斂 ＝ 近 20 根日報酬標準差 ÷ 近 250 根日報酬標準差
      其餘指定的狀態量已在特徵表：打底區間振幅（rng_60 ＝ 60 日最高÷最低 − 1）、融資 60 日變化（mchg_60）、集保大戶 12 週變化（tdcc_60）、營收年增趨勢（y3chg）、產業 20 日報酬排名（indrk_20）
    判斷候選 ＝ 當下訊號 16 個 ＋ 特徵類（特徵表與打底五等分）裡「探索段事件（任一版）t 點為發動訊號」的級距；組合分三組：只數當下訊號 ≥k（k＝1～6）、只數特徵 ≥k（k＝1～10）、全部 ≥k（k＝1～10）
 L7 查核（--check）：抽 2 格逐事件迴圈重找 H1 與 50% 點、用迴圈重算 MACD 金叉（近 3 日）在 50% 點的涵蓋率；判斷部分抽 2 格 × 150 檔，逐日迴圈重算 V2 探索段基準與 MACD 的母體數、標籤數 ⇒ 0 不同才算過
輸出 backtest/resultsSurge6/launch/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5
from backtest import researchSurge5_feat as FT
from backtest import researchSurge6_end_desc as ED
from backtest import researchSurge6_mid_desc as MD

D = S5.D
TIME = "2026-09-30 19:42（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/launch"
HS = list(S5.HS); GS = list(S5.GS)
PCTS = list(range(0, 101, 10))
PTN = [f"{p}%" for p in PCTS]
VERS = ["V1 位置≤0.2", "V2 位置≤0.4", "V3 位置≤0.6", "V4 位置≤0.4且之前沒大漲"]
SIGN = ["MACD金叉", "KD金叉", "RSI上穿50", "MA20上穿MA60", "創20日新高", "創55日新高", "量≥20日均量2倍", "站上布林中軌", "站上布林上軌",
        "OBV上穿20日均", "三大法人連買≥3日", "營收成長股價未漲", "創一年新高", "營收創24月新高", "被列注意", "進入處置"]
NS = len(SIGN)
NEWN = ["低檔盤整天數", "距一年最低點幾根", "量縮程度（近20均額÷前250均額）", "波動收斂（近20波動÷近250波動）"]
CATG = {"價": "價位與均線、波動", "量": "量能", "技術": "價位與均線、波動", "法人": "籌碼（法人）", "融資": "籌碼（融資）", "借券": "籌碼（借券）", "集保": "籌碼（集保大戶）",
        "注意處置": "注意處置", "營收": "營收", "財報A2": "財報", "產業": "產業", "大盤": "大盤", "規模": "規模", "打底": "低檔打底（新增）"}
EXP = (2021 * 12, 2023 * 12 + 11); CON = (2024 * 12, 2026 * 12 + 7)
KS = list(range(1, 11)); KSS = list(range(1, 7))
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_


def ema(x, n_):
    return pd.Series(x).ewm(span=n_, adjust=False).mean().to_numpy()


def cross_up(a, b):
    out = np.zeros(len(a), bool)
    ok = np.isfinite(a) & np.isfinite(b)
    out[1:] = ok[1:] & ok[:-1] & (a[1:] > b[1:]) & (a[:-1] <= b[:-1])
    return out


def stock_signals(sid, mk, cal, n, bar_s, W, F_revhi, INSTD):
    """⇒ c（ffill 還原收盤，n）、pos（n）、base（NS × n bool：當根發生）、near3（NS × n）"""
    st = D.load_stock(sid, mk, cal)
    base = np.zeros((NS, n), bool); pos = np.full(n, np.nan)
    if st is None:
        return None
    df = st.df; c0 = df["close"].to_numpy(float); h0 = df["high"].to_numpy(float); l0 = df["low"].to_numpy(float); v0 = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
    c = pd.Series(c0).ffill().to_numpy()
    idx = np.flatnonzero(np.isfinite(c0) & bar_s)
    if len(idx) < 30:
        return c, pos, base, base.copy(), np.full((len(NEWN), n), np.nan, np.float32)
    cb = c0[idx]; hb = np.where(np.isfinite(h0[idx]), h0[idx], cb); lb = np.where(np.isfinite(l0[idx]), l0[idx], cb); vb = np.nan_to_num(v0[idx])
    m = len(idx); S = pd.Series(cb)
    mx250 = S.rolling(250, min_periods=250).max().to_numpy(); mn250 = S.rolling(250, min_periods=250).min().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        p_ = (cb - mn250) / (mx250 - mn250)
    p_[~(mx250 > mn250)] = np.nan; pos[idx] = p_
    B = np.zeros((NS, m), bool)
    dif = ema(cb, 12) - ema(cb, 26); dea = ema(dif, 9); B[0] = cross_up(dif, dea); B[0][:34] = False
    K = np.full(m, np.nan); Dd = np.full(m, np.nan); k0 = d0 = 50.0
    for i in range(8, m):
        lo, hi = lb[i - 8:i + 1].min(), hb[i - 8:i + 1].max()
        rsv = 50.0 if hi - lo <= 0 else (cb[i] - lo) / (hi - lo) * 100
        k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3; K[i] = k0; Dd[i] = d0
    B[1] = cross_up(K, Dd)
    from backtest import surge_features as SFe
    r14 = SFe.rsi(cb, 14); B[2] = cross_up(r14, np.full(m, 50.0))
    ma20 = S.rolling(20, min_periods=20).mean().to_numpy(); ma60 = S.rolling(60, min_periods=60).mean().to_numpy()
    B[3] = cross_up(ma20, ma60)
    p20 = np.r_[np.nan, S.rolling(20, min_periods=20).max().to_numpy()[:-1]]; p55 = np.r_[np.nan, S.rolling(55, min_periods=55).max().to_numpy()[:-1]]
    p250 = np.r_[np.nan, S.rolling(250, min_periods=250).max().to_numpy()[:-1]]
    with np.errstate(invalid="ignore"):
        B[4] = cb > p20; B[5] = cb > p55; B[12] = cb > p250
        vm = np.r_[np.nan, pd.Series(vb).rolling(20, min_periods=20).mean().to_numpy()[:-1]]
        B[6] = (vb >= 2 * vm) & (vm > 0)
    sd = S.rolling(20, min_periods=20).std(ddof=0).to_numpy()
    B[7] = cross_up(cb, ma20); B[8] = cross_up(cb, ma20 + 2 * sd)
    obv = np.cumsum(np.r_[0.0, np.sign(np.diff(cb)) * vb[1:]]); obm = pd.Series(obv).rolling(20, min_periods=20).mean().to_numpy()
    B[9] = cross_up(obv, obm)
    if INSTD is not None:
        tot = INSTD.reindex(cal[idx]).to_numpy(float)
        pos3 = pd.Series(np.nan_to_num(tot) > 0).astype(float).rolling(3, min_periods=3).sum().to_numpy()
        B[10] = pos3 >= 3
    # 營收成長股價未漲
    y3a = np.full(n, np.nan)
    if sid in W["REV"].columns:
        V = W["REV"][sid].to_numpy(float); eff = W["REV_EFF"]
        yoy = np.full(len(V), np.nan); yoy[12:] = np.where((V[:-12] > 0) & np.isfinite(V[:-12]), V[12:] / V[:-12] - 1, np.nan)
        y3 = pd.Series(yoy).rolling(3, min_periods=3).mean().to_numpy()
        order = np.argsort(eff, kind="stable"); effs = eff[order]
        for i, d in enumerate(idx):
            j = int(np.searchsorted(effs, d, side="right")) - 1
            if j < 0:
                continue
            kx = order[j]
            while kx >= 0 and not np.isfinite(V[kx]):
                kx -= 1
            if kx >= 0:
                y3a[d] = y3[kx]
    r20 = np.r_[np.full(20, np.nan), cb[20:] / cb[:-20] - 1] if m > 20 else np.full(m, np.nan)
    with np.errstate(invalid="ignore"):
        B[11] = (y3a[idx] > 0.20) & (r20 < 0.10)
        B[13] = F_revhi[idx] == 1
    att = W["ATT"].get(sid, np.zeros(0, int)); ats = np.zeros(n, bool); ats[att[(att >= 0) & (att < n)]] = True; B[14] = ats[idx]
    dst = np.zeros(n, bool)
    for a_, b_ in W["DISP"].get(sid, []):
        if 0 <= a_ < n:
            dst[a_] = True
    B[15] = dst[idx]
    N3 = B.copy(); N3[:, 1:] |= B[:, :-1]; N3[:, 2:] |= B[:, :-2]
    base[:, idx] = B; near = np.zeros((NS, n), bool); near[:, idx] = N3
    # 低檔打底狀態量（L8）
    raw = np.full((len(NEWN), n), np.nan, np.float32)
    lowh = np.nan_to_num(p_, nan=9) <= 0.5; run_ = np.zeros(m)
    for i in range(m):
        run_[i] = run_[i - 1] + 1 if (i > 0 and lowh[i]) else float(lowh[i])
    run_[~np.isfinite(p_)] = np.nan
    since = np.full(m, np.nan)
    for i in range(249, m):
        w = cb[i - 249:i + 1]; j = 249 - int(np.argmin(w[::-1]))
        since[i] = 249 - j
    amt = np.nan_to_num(pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)[idx])
    a20 = pd.Series(amt).rolling(20, min_periods=20).mean().to_numpy(); a250p = np.r_[np.full(20, np.nan), pd.Series(amt).rolling(250, min_periods=250).mean().to_numpy()[:-20]]
    rr = np.r_[np.nan, cb[1:] / cb[:-1] - 1]
    s20 = pd.Series(rr).rolling(20, min_periods=20).std(ddof=0).to_numpy(); s250 = pd.Series(rr).rolling(250, min_periods=250).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        raw[0, idx] = run_; raw[1, idx] = since; raw[2, idx] = np.where(a250p > 0, a20 / a250p, np.nan); raw[3, idx] = np.where(s250 > 0, s20 / s250, np.nan)
    return c, pos, base, near, raw


def inst_total(sid):
    p_ = os.path.join(S5.MAIN, "stocks_inst", sid + ".csv")
    if not os.path.exists(p_):
        return None
    it = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "total"]).drop_duplicates("date", keep="last")
    it.index = pd.to_datetime(it["date"]); return pd.to_numeric(it["total"], errors="coerce")


def build(uni, cal, n, bar, log):
    W, _ = S5.world(log)
    Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    revhi = np.asarray(Fm[FX["d_revhi"]])
    S = len(uni); C = np.full((S, n), np.nan); POS = np.full((S, n), np.nan); NEAR = np.zeros((S, n), np.uint32)
    RAW = np.full((len(NEWN), S, n), np.nan, np.float32)
    D.DATA = S5.ST
    for s in range(S):
        sid = uni.loc[s, "stock_id"]
        o = stock_signals(sid, uni.loc[s, "market"], cal, n, bar[s], W, revhi[s], inst_total(sid))
        if o is None:
            continue
        c, pos, base, near, raw = o
        C[s] = c; POS[s] = pos; RAW[:, s] = raw
        NEAR[s] = (near.astype(np.uint32) << np.arange(NS, dtype=np.uint32)[:, None]).sum(0).astype(np.uint32)
        if s % 400 == 0:
            log(f"[訊號] {s}/{S}")
    NEWQ = np.zeros((len(NEWN), S, n), np.int8)
    for t in range(n):
        b_ = bar[:, t]
        if b_.any():
            for k in range(len(NEWN)):
                NEWQ[k, b_, t] = S5.qtie(RAW[k, b_, t])
    log("[打底] 五等分完成")
    return W, C, POS, NEAR, NEWQ


def version_masks(POS, Qr120, Flu20):
    with np.errstate(invalid="ignore"):
        v1 = POS <= 0.2; v2 = POS <= 0.4; v3 = POS <= 0.6
        v4 = v2 & (Qr120 != 5) & (np.nan_to_num(Flu20, nan=0) < 3)
    return [v1, v2, v3, v4]


def first_top(c, t, P):
    cs = c[t:P + 1]
    if len(cs) > 2:
        for a, b, lo, hi in MD.pullbacks(cs):
            if a > 0 and lo <= hi * 0.8 * (1 + 1e-9):
                return t + a
    return P


def points(uni, cal, E, C):
    es, ed, Pv = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int)
    H1 = np.zeros(len(es), np.int64); PT = np.zeros((len(PCTS), len(es)), np.int64)
    for i in range(len(es)):
        c = C[es[i]]; t, P = ed[i], Pv[i]; h1 = first_top(c, t, P); H1[i] = h1
        lo, hi = c[t], c[h1]; w = c[t + 1:h1 + 1]
        PT[0, i] = t
        for k, p in enumerate(PCTS[1:], 1):
            PT[k, i] = t + 1 + int(np.argmax(w >= (lo + p / 100 * (hi - lo)) * (1 - 1e-9))) if len(w) else t
    return H1, PT


def feat_sources(NEWQ):
    """⇒ [(key, 取陣列函式, [(碼, 級距名, 欄, 類別)])]；Q 表全部級距 ＋ 打底五等分"""
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); LV = FT.levels(); out = []
    for fi in sorted({x[0] for x in LV}):
        lv = [(x[2], f"{x[4]}｜{x[3]}", x[1], ED.CAT.get(x[1], "")) for x in LV if x[0] == fi]
        out.append((("Q", fi), (lambda fi=fi: np.asarray(Qm[fi])), lv))
    for k, nm in enumerate(NEWN):
        out.append((("N", k), (lambda k=k: NEWQ[k]), [(q, f"{nm}｜Q{q}", f"N{k}", "打底") for q in range(1, 6)]))
    return out


def describe(uni, cal, n, inseg, bar, h6, E, cells, C, POS, NEAR, VM, H1, PT, mon, log, NEWQ):
    es, ed, ec = E["s"].astype(int), E["d"].astype(int), E["cell"].astype(int)
    HC = np.array([HS[c // len(GS)] for c in range(250)]); Hset = sorted({HC[c] for c in cells})
    FS = feat_sources(NEWQ)
    rs, rt = np.nonzero(bar & inseg[None, :]); rh = np.minimum(h6[rs, rt].astype(np.int64), 250)
    VE = [vm[es, ed] for vm in VM]
    segm = {"全部": np.ones(len(es), bool), "探索": (mon[ed] >= EXP[0]) & (mon[ed] <= EXP[1])}
    CV = {}; CELLS = {}
    for vi, vn in enumerate(VERS):
        for sg, sm in segm.items():
            m = VE[vi] & sm; cntc = np.bincount(ec[m], minlength=250); CELLS[(vn, sg)] = [c for c in cells if cntc[c] >= 30]
    # 一般股-日
    GEN = {}
    for key, get, lvs in FS:
        q = get(); gg = np.bincount(q[rs, rt].astype(np.int64) * 251 + rh, minlength=7 * 251).reshape(7, 251); ge = np.cumsum(gg[:, ::-1], axis=1)[:, ::-1]
        with np.errstate(invalid="ignore", divide="ignore"):
            for code, nm, col, cat in lvs:
                GEN[("F", key, code)] = {H: ge[code, H] / ge[1:, H].sum() for H in Hset}
    nr = NEAR[rs, rt]; tot = np.bincount(rh, minlength=251); totc = np.cumsum(tot[::-1])[::-1]
    for j in range(NS):
        b = ((nr >> j) & 1).astype(bool); gg = np.bincount(rh[b], minlength=251); gc = np.cumsum(gg[::-1])[::-1]
        GEN[("S", j, 1)] = {H: gc[H] / totc[H] for H in Hset}
    log("[描述] 一般股-日完成")
    ROWS = []; DAYSR = []
    for vi, vn in enumerate(VERS):
        for sg, sm in segm.items():
            m = VE[vi] & sm; cl = CELLS[(vn, sg)]
            if not cl:
                continue
            for k in range(len(PCTS)):
                dd = PT[k]
                y = q3([np.median((dd - ed)[m & (ec == c)]) for c in cl]); DAYSR.append({"版本": vn, "段": sg, "點": PTN[k], "距t天數 格中位": y[0], "p10": y[1], "p90": y[2]})
            # 自訂訊號
            for j in range(NS):
                cov = np.zeros((len(PCTS), 250))
                for k in range(len(PCTS)):
                    b = ((NEAR[es, PT[k]] >> j) & 1).astype(float)
                    num = np.bincount(ec[m], weights=b[m], minlength=250); den = np.bincount(ec[m], minlength=250)
                    with np.errstate(invalid="ignore", divide="ignore"):
                        cov[k] = num / den
                g = q3([GEN[("S", j, 1)][HC[c]] for c in cl])[0]
                r = {"版本": vn, "段": sg, "類": "當下訊號", "類別": "當下訊號", "訊號": SIGN[j], "src": "S", "key": j, "欄": f"S{j}", "碼": 1, "一般": g}
                for k in range(len(PCTS)):
                    r[PTN[k]] = q3(cov[k, cl])[0]; r[PTN[k] + " 倍數"] = r[PTN[k]] / g if g > 0 else np.nan
                ROWS.append(r)
            log(f"[描述] {vn}｜{sg}｜格 {len(cl)}（當下訊號）")
    # 狀態／特徵：每個特徵只載一次
    for key, get, lvs in FS:
        q = get(); qe = [q[es, PT[k]].astype(np.int64) for k in range(len(PCTS))]
        for vi, vn in enumerate(VERS):
            for sg, sm in segm.items():
                m = VE[vi] & sm; cl = CELLS[(vn, sg)]
                if not cl:
                    continue
                ms = [np.bincount(ec[m] * 7 + qe[k][m], minlength=250 * 7).reshape(250, 7) for k in range(len(PCTS))]
                for code, nm, col, cat in lvs:
                    g = q3([GEN[("F", key, code)][HC[c]] for c in cl])[0]
                    r = {"版本": vn, "段": sg, "類": "狀態／特徵", "類別": CATG.get(cat, cat), "訊號": nm, "src": key[0], "key": key[1], "欄": col, "碼": code, "一般": g}
                    with np.errstate(invalid="ignore", divide="ignore"):
                        for k in range(len(PCTS)):
                            cv = ms[k][:, code] / ms[k][:, 1:].sum(1)
                            r[PTN[k]] = q3(cv[cl])[0]; r[PTN[k] + " 倍數"] = r[PTN[k]] / g if g > 0 else np.nan
                    ROWS.append(r)
    log("[描述] 狀態／特徵完成")
    CV = pd.DataFrame(ROWS)
    # 新出現、發動訊號
    for k in range(1, len(PCTS)):
        CV[f"新增 {PTN[k]}"] = CV[PTN[k]] - CV[PTN[k - 1]]
    CV["發動訊號"] = (CV[PTN[0]] >= 0.30) & (CV[PTN[0] + " 倍數"] > 1.5)
    CV["新出現於"] = [",".join(PTN[k] for k in range(1, len(PCTS)) if r[f"新增 {PTN[k]}"] >= 0.10) for r in CV.to_dict("records")]
    return CV, pd.DataFrame(DAYSR), {f"{k[0]}｜{k[1]}": len(v) for k, v in CELLS.items()}


def judge(uni, cal, n, inseg, bar, h6, cells, C, POS, NEAR, VM, FSEL, mon, t1, log, NEWQ, chk=None):
    """⇒ N[v,seg,H,J]、Y[v,seg,cell,J]、CNT[v,seg,J]、DR（先跌 15%）"""
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    QS = [(np.asarray(Qm[key]) if src == "Q" else NEWQ[key]) for src, key, code, nm in FSEL]
    J0 = NS + len(FSEL); J = 1 + J0 + len(KSS) + len(KS) + len(KS)
    HI = {H: i for i, H in enumerate(HS)}
    cellsHG = {c: (c // len(GS), c % len(GS)) for c in cells}
    N = np.zeros((4, 2, len(HS), J)); Y = np.zeros((4, 2, 250, J)); CNT = np.zeros((4, 2, J)); DRn = np.zeros((4, 2, J)); DRd = np.zeros((4, 2, J))
    segm = [(mon >= EXP[0]) & (mon <= EXP[1]) & inseg, (mon >= CON[0]) & (mon <= CON[1]) & inseg]
    CHK = []
    for s in range(len(uni)):
        c = C[s]
        if not np.isfinite(c).any():
            continue
        d_ok = bar[s] & inseg
        if not d_ok.any():
            continue
        dd = np.flatnonzero(d_ok); lo_, hi_ = dd[0], dd[-1]
        rng = np.arange(lo_, hi_ + 1)
        X = np.zeros((len(rng), J), np.float32); X[:, 0] = 1
        bits = NEAR[s, rng]
        for j in range(NS):
            X[:, 1 + j] = (bits >> j) & 1
        for f, (src, key, code, nm) in enumerate(FSEL):
            X[:, 1 + NS + f] = QS[f][s, rng] == code
        ks_ = X[:, 1:1 + NS].sum(1); kf_ = X[:, 1 + NS:1 + J0].sum(1); ka_ = ks_ + kf_; o_ = 1 + J0
        for i, k in enumerate(KSS):
            X[:, o_ + i] = ks_ >= k
        o_ += len(KSS)
        for i, k in enumerate(KS):
            X[:, o_ + i] = kf_ >= k
        o_ += len(KS)
        for i, k in enumerate(KS):
            X[:, o_ + i] = ka_ >= k
        grp = np.stack([VM[v][s, rng] & bar[s, rng] & segm[g][rng] for v in range(4) for g in range(2)]).astype(np.float32)   # 8 × m
        CNT += (grp @ X).reshape(4, 2, J)
        # 未來最高（ffill 收盤）
        cr = c[rng]; h6s = h6[s, rng]
        rv = pd.Series(c[::-1])
        for H in HS:
            fmx = np.r_[rv.rolling(H, min_periods=H).max().to_numpy()[::-1][1:], np.nan][rng]
            dom = (h6s >= H).astype(np.float32)
            G = grp * dom[None, :]
            N[:, :, HI[H], :] += (G @ X).reshape(4, 2, J)
            gl = [gi for gi in range(len(GS)) if (HI[H] * len(GS) + gi) in cellsHG]
            if not gl:
                continue
            with np.errstate(invalid="ignore"):
                L = np.stack([fmx >= cr * (1 + GS[gi]) * (1 - 1e-9) for gi in gl]).astype(np.float32)          # len(gl) × m
            GL = (G[:, None, :] * L[None, :, :]).reshape(-1, len(rng))
            YY = (GL @ X).reshape(4, 2, len(gl), J)
            for a_, gi in enumerate(gl):
                Y[:, :, HI[H] * len(GS) + gi, :] += YY[:, :, a_, :]
            if chk is not None and s in chk["stocks"]:
                for cc in chk["cells"]:
                    if cc // len(GS) == HI[H]:
                        gi = cc % len(GS); a_ = gl.index(gi)
                        for jn, jj in (("基準", 0), ("MACD", 1)):
                            CHK.append({"s": s, "cell": cc, "j": jn, "N": float((G[2] @ X[:, jj])), "Y": float(YY[1, 0, a_, jj])})
        # 一年內先跌 15%
        dr_ok = (rng + 250 <= t1).astype(np.float32)
        if dr_ok.any():
            first = np.zeros(len(rng), np.float32)
            for i_, d in enumerate(rng):
                if not dr_ok[i_] or not grp[:, i_].any():
                    continue
                w = c[d + 1:d + 251]; dn = np.flatnonzero(w <= c[d] * 0.85); up = np.flatnonzero(w >= c[d] * 1.15)
                first[i_] = float(len(dn) > 0 and (len(up) == 0 or dn[0] < up[0]))
            Gd = grp * dr_ok[None, :]
            DRd += (Gd @ X).reshape(4, 2, J); DRn += ((Gd * first[None, :]) @ X).reshape(4, 2, J)
        if s % 400 == 0:
            log(f"[判斷] {s}/{len(uni)}")
    names = ["基準（不看訊號）"] + SIGN + [r[3] for r in FSEL] + [f"當下訊號同時 ≥{k} 個" for k in KSS] + [f"狀態特徵同時 ≥{k} 個" for k in KS] + [f"全部候選同時 ≥{k} 個" for k in KS]
    return N, Y, CNT, DRn, DRd, names, pd.DataFrame(CHK)


def summarize_judge(N, Y, CNT, DRn, DRd, names, cells, mon, inseg, bar):
    ndays = [int(((mon >= a) & (mon <= b) & inseg).sum()) for a, b in (EXP, CON)]
    HI = {H: i for i, H in enumerate(HS)}
    out = []
    for v, vn in enumerate(VERS):
        for g, sg in enumerate(("探索", "確認")):
            for j, nm in enumerate(names):
                rat = []; rate = []; base = []
                for c in cells:
                    h = c // len(GS)
                    n0, y0 = N[v, g, h, 0], Y[v, g, c, 0]; n1, y1 = N[v, g, h, j], Y[v, g, c, j]
                    if n0 >= 30 and n1 >= 30 and y0 > 0:
                        rate.append(y1 / n1); base.append(y0 / n0); rat.append((y1 / n1) / (y0 / n0))
                r = {"版本": vn, "段": sg, "訊號": nm, "可用格": len(rat), "倍數 格中位": q3(rat)[0], "倍數 p10": q3(rat)[1], "倍數 p90": q3(rat)[2],
                     "變飆股比例 格中位": q3(rate)[0], "基準 格中位": q3(base)[0], "每天平均幾檔": CNT[v, g, j] / ndays[g],
                     "一年內先跌15%": DRn[v, g, j] / DRd[v, g, j] if DRd[v, g, j] > 0 else np.nan, "先跌15% 可算日數": DRd[v, g, j]}
                out.append(r)
    return pd.DataFrame(out)


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    W, C, POS, NEAR, NEWQ = build(uni, cal, n, bar, log)
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")
    VM = version_masks(POS, np.asarray(Qm[S5.FIX["r_120"]]), np.asarray(Fm[S5.FIX["lu_20"]]))
    H1, PT = points(uni, cal, E, C)
    log(f"[點] 完成 {time.time() - T0:.0f}s")
    CV, DY, NC = describe(uni, cal, n, inseg, bar, h6, E, cells, C, POS, NEAR, VM, H1, PT, mon, log, NEWQ)
    CV.to_csv(os.path.join(OUT, "coverage.csv.gz"), index=False, float_format="%.5g"); DY.to_csv(os.path.join(OUT, "days.csv"), index=False, float_format="%.5g")
    # 判斷候選：探索段事件、任一版 t 點發動訊號（特徵表）
    ex = CV[(CV["段"] == "探索") & (CV["類"] == "狀態／特徵") & CV["發動訊號"]]
    FSEL = sorted({(r["src"], int(r["key"]), int(r["碼"]), r["訊號"]) for r in ex.to_dict("records")}, key=lambda x: x[3])
    log(f"[判斷] 特徵候選 {len(FSEL)} 個：{[x[3] for x in FSEL]}")
    rng_ = np.random.default_rng(20260930); ck_cells = [int(x) for x in rng_.choice(cells, 2, replace=False)]; ck_st = set(int(x) for x in rng_.choice(len(uni), 150, replace=False))
    N, Y, CNT, DRn, DRd, names, CHK = judge(uni, cal, n, inseg, bar, h6, cells, C, POS, NEAR, VM, FSEL, mon, t1, log, NEWQ,
                                           chk={"cells": ck_cells, "stocks": ck_st})
    CHK.to_csv(os.path.join(OUT, "check_stock.csv.gz"), index=False)
    JS = summarize_judge(N, Y, CNT, DRn, DRd, names, cells, mon, inseg, bar); JS.to_csv(os.path.join(OUT, "judge.csv"), index=False, float_format="%.5g")
    TOP = []
    for vn in VERS:
        x = JS[(JS["版本"] == vn) & (JS["段"] == "探索") & (JS["訊號"] != "基準（不看訊號）") & (JS["可用格"] > 0)].sort_values("倍數 格中位", ascending=False, kind="mergesort").head(10)
        for rk, nm in enumerate(x["訊號"], 1):
            TOP.append({"版本": vn, "名次": rk, "訊號": nm})
    pd.DataFrame(TOP).to_csv(os.path.join(OUT, "top10_explore.csv"), index=False)
    np.savez_compressed(os.path.join(OUT, "judge_raw.npz"), N=N, Y=Y, CNT=CNT, DRn=DRn, DRd=DRd)
    META = {"讀法寫死": TIME, "合格格數": len(cells), "各版格數": NC, "特徵候選": [x[3] for x in FSEL], "判斷欄": names,
            "事件數": int(len(E["s"])), "各版事件數（全部）": {vn: int(VM[i][E["s"].astype(int), E["d"].astype(int)].sum()) for i, vn in enumerate(VERS)},
            "查核格": ck_cells, "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    np.savez_compressed(os.path.join(OUT, "points.npz"), H1=H1, PT=PT)
    log(f"[完] {time.time() - T0:.0f}s")


def _macd_near3_loop(cb):
    m = len(cb); out = np.zeros(m, bool)

    def ema_l(x, n_):
        a = 2.0 / (n_ + 1); e = [x[0]]
        for v in x[1:]:
            e.append(a * v + (1 - a) * e[-1])
        return np.array(e)
    dif = ema_l(list(cb), 12) - ema_l(list(cb), 26); dea = ema_l(list(dif), 9)
    ev = [False] * m
    for i in range(1, m):
        ev[i] = i >= 34 and dif[i] > dea[i] and dif[i - 1] <= dea[i - 1]
    for i in range(m):
        out[i] = any(ev[max(0, i - 2):i + 1])
    return out


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8")); ck = meta["查核格"]
    PZ = np.load(os.path.join(OUT, "points.npz")); H1, PT = PZ["H1"], PZ["PT"]
    CHK = pd.read_csv(os.path.join(OUT, "check_stock.csv.gz"))
    D.DATA = S5.ST; errs = []; info = {}; memo = {}

    def stock(s):
        if s not in memo:
            df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
            c0 = df["close"].to_numpy(float); cff = pd.Series(c0).ffill().to_numpy(); idx = [d for d in range(n) if np.isfinite(c0[d]) and bar[s, d]]
            cb = np.array([c0[d] for d in idx]); mac = _macd_near3_loop(cb) if len(cb) >= 30 else np.zeros(len(cb), bool)
            pos = {}
            for j, d in enumerate(idx):
                if j >= 249:
                    w = list(cb[j - 249:j + 1]); lo, hi = min(w), max(w)
                    if hi > lo:
                        pos[d] = (cb[j] - lo) / (hi - lo)
            memo[s] = (cff, dict(zip(idx, mac)), pos)
        return memo[s]
    # ① 描述：H1、50% 點（兩格全部事件）
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    for c in ck:
        k = np.flatnonzero(ec == c); nd = 0; hits = []; nv = 0
        for i in k:
            s, t, P = int(es[i]), int(ed[i]), int(Pv[i]); cff, mac, pos = stock(s)
            pk, pkd, tv, h1 = cff[t], t, np.inf, None
            for d in range(t + 1, P + 1):
                if cff[d] > pk:
                    if pkd > t and tv <= pk * 0.8 * (1 + 1e-9):
                        h1 = pkd; break
                    pk, pkd, tv = cff[d], d, np.inf
                elif cff[d] < tv:
                    tv = cff[d]
            h1 = P if h1 is None else h1
            lvl = cff[t] + 0.5 * (cff[h1] - cff[t]); d5 = t + 1
            while d5 < h1 and cff[d5] < lvl * (1 - 1e-9):
                d5 += 1
            nd += int(h1 != H1[i] or d5 != PT[5, i])
            p = pos.get(t)
            if p is not None and p <= 0.4:
                nv += 1; hits.append(bool(mac.get(d5, False)))
        info[f"格 {S5.cell_name(c)}"] = {"事件": int(len(k)), "H1／50%點不同": nd, "V2 事件": nv, "MACD 在 50% 點（近 3 日）涵蓋率（迴圈）": float(np.mean(hits)) if hits else None}
        if nd:
            errs.append(f"{S5.cell_name(c)} 點不同 {nd}")
    # ② 判斷：抽樣股逐日迴圈（V2、探索段；基準與 MACD）
    nb = 0
    for (s, cc), g in CHK.groupby(["s", "cell"]):
        s = int(s); cc = int(cc); cff, mac, pos = stock(s); H = HS[cc // len(GS)]; gg = GS[cc % len(GS)]
        res = {"基準": [0, 0], "MACD": [0, 0]}
        for d in range(n):
            if not (bar[s, d] and inseg[d] and EXP[0] <= mon[d] <= EXP[1] and h6[s, d] >= H):
                continue
            p = pos.get(d)
            if p is None or p > 0.4:
                continue
            lab = max(cff[d + 1:d + H + 1]) >= cff[d] * (1 + gg) * (1 - 1e-9)
            res["基準"][0] += 1; res["基準"][1] += int(lab)
            if mac.get(d, False):
                res["MACD"][0] += 1; res["MACD"][1] += int(lab)
        for r in g.to_dict("records"):
            a = res[r["j"]]
            if not (a[0] == int(r["N"]) and a[1] == int(r["Y"])):
                nb += 1; errs.append(f"股 {s} 格 {S5.cell_name(cc)} {r['j']}：迴圈 {a} 檔 {r['N']:.0f}/{r['Y']:.0f}")
    info["判斷抽樣 股×格×欄"] = int(len(CHK)); info["判斷不同"] = nb
    out = {"讀法寫死": TIME, "比對": info, "錯誤數": len(errs), "錯誤": errs[:20], "通過": len(errs) == 0}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 錯誤 {len(errs)}｜{errs[:3]}")


def page(log):
    CV = pd.read_csv(os.path.join(OUT, "coverage.csv.gz")); DY = pd.read_csv(os.path.join(OUT, "days.csv")); JS = pd.read_csv(os.path.join(OUT, "judge.csv"))
    TOPX = pd.read_csv(os.path.join(OUT, "top10_explore.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal;min-width:9em}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}.up{background:#fdecea;font-weight:600}.t0{background:#e8f5e9;font-weight:600}"
            ".sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}"
            "details{margin:6px 0}summary{cursor:pointer;font-weight:600}table.tl td,table.tl th{padding:3px 4px;font-size:.82rem}")
    P0 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.1f}%"
    XX = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.2f}"
    V0 = VERS[1]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>低檔發動到第一頂的訊號</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>股票從低檔發動時有什麼訊號？漲到第一頂的路上又多了什麼？（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 描述＋參考，沒有計入檢定數。「第一頂」「進度幾成」都是事後才知道的，只用來對答案；判斷那一節才是當下可用的。判斷的訊號在探索段（2021–2023）排名，確認段（2024–2026-08）只照報。</p>",
         f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。低檔 ＝ 起漲日收盤落在前 250 日區間的下方（位置 ＝（收盤 − 最低）÷（最高 − 最低））；第一頂 ＝ 從起漲點起第一個之後拉回 20% 的高點；"
         f"進度 0%～100% ＝ 從起漲收盤漲到第一頂收盤的第幾成。{META['合格格數']} 種飆股定義逐一算、取中位數。兩類並列：<b>狀態／特徵</b>（當天的狀態，例如融資使用率高、營收年增）與<b>當下訊號</b>（近 3 日剛發生，例如 MACD 金叉）。"
         + (f"查核：{'通過' if CK['通過'] else '有錯'}（錯誤 {CK['錯誤數']}）。" if CK else "") + "</p>"]
    c0 = CV[(CV["版本"] == V0) & (CV["段"] == "全部")]
    launch = c0[c0["發動訊號"]].sort_values(PTN[0] + " 倍數", ascending=False)
    newp = c0[c0["新出現於"].fillna("") != ""]
    j0 = JS[(JS["版本"] == V0)]
    tops = TOPX[TOPX["版本"] == V0]["訊號"].tolist()
    jb = j0[j0["訊號"] == "基準（不看訊號）"].set_index("段")
    best = tops[0] if tops else None
    jx = j0[j0["訊號"] == best].set_index("段") if best else None
    dy = DY[(DY["版本"] == V0) & (DY["段"] == "全部")].set_index("點")
    H.append(f"<h2>先講結論（{html.escape(V0)}；其他版本用選單看）</h2><ul class='big'>")
    H.append(f"<li><b>時間</b>：從低點發動到第一頂，中位 {dy.loc['100%', '距t天數 格中位']:.0f} 個交易日；走到一半（50%）約第 {dy.loc['50%', '距t天數 格中位']:.0f} 天。</li>")
    for cls in ("狀態／特徵", "當下訊號"):
        x = launch[launch["類"] == cls].head(6)
        H.append(f"<li><b>發動當下就有（{cls}）</b>：{len(launch[launch['類'] == cls])} 個（起漲日涵蓋率 ≥30% 且是一般股的 1.5 倍以上）"
                 + ("，倍數最高的：" + "、".join(f"{html.escape(r['訊號'])} {P0(r[PTN[0]])}（{XX(r[PTN[0] + ' 倍數'])} 倍）" for r in x.to_dict("records")) if len(x) else "") + "。</li>")
        y = newp[newp["類"] == cls]
        H.append(f"<li><b>路上新出現（{cls}）</b>：{len(y)} 個在某一段比上一點多 10 個百分點以上"
                 + ("，例如 " + "、".join(f"{html.escape(r['訊號'])}（{r['新出現於'].split(',')[0]}）" for r in y.sort_values(PTN[10], ascending=False).head(6).to_dict("records")) if len(y) else "") + "。</li>")
    if best is not None and len(jb) == 2:
        H.append(f"<li><b>發動當下能不能分出來</b>：低檔股票之後變飆股的比例（格中位）探索段 {P1(jb.loc['探索', '變飆股比例 格中位'])}、確認段 {P1(jb.loc['確認', '變飆股比例 格中位'])}。"
                 f"探索段倍數最高的是「{html.escape(best)}」：探索 {XX(jx.loc['探索', '倍數 格中位'])} 倍 → 確認 {XX(jx.loc['確認', '倍數 格中位'])} 倍，"
                 f"確認段變飆股比例 {P1(jx.loc['確認', '變飆股比例 格中位'])}（基準 {P1(jb.loc['確認', '變飆股比例 格中位'])}），每天平均 {jx.loc['確認', '每天平均幾檔']:.1f} 檔，"
                 f"一年內先跌 15% 的 {P0(jx.loc['確認', '一年內先跌15%'])}（基準 {P0(jb.loc['確認', '一年內先跌15%'])}）。</li>")
    H.append("__HONEST__</ul>")
    H.append("<div class='sel'>版本 <select id='sv' onchange='sw()'>" + "".join(f"<option value='{i}'>{html.escape(v)}</option>" for i, v in enumerate(VERS)) + "</select></div>")
    for vi, vn in enumerate(VERS):
        c = CV[(CV["版本"] == vn) & (CV["段"] == "全部")]
        H.append(f"<div class='pane' id='v{vi}'><p class='note'>進格中位的格數：{META['各版格數'].get(vn + '｜全部', '—')}；事件（全部格合計）{META['各版事件數（全部）'].get(vn, 0):,}。</p>")
        dy = DY[(DY["版本"] == vn) & (DY["段"] == "全部")].set_index("點")
        H.append("<h2>一、時間軸（各點距起漲天數，格中位）</h2><div class='wrap'><table class='tl'><tr>" + "".join(f"<th>{p}</th>" for p in PTN) + "</tr><tr>"
                 + "".join(f"<td>{dy.loc[p, '距t天數 格中位']:.0f}</td>" if p in dy.index else "<td>—</td>" for p in PTN) + "</tr></table></div>")
        for cls, title in (("當下訊號", "二、當下訊號（近 3 日發生）的時間軸"), ("狀態／特徵", "三、狀態／特徵的時間軸（發動就有、或路上新出現的）")):
            x = c[c["類"] == cls]
            if cls == "狀態／特徵":
                x = x[x["發動訊號"] | (x["新出現於"].fillna("") != "")]
            H.append(f"<h2>{title}</h2><p class='note'>綠底 ＝ 發動當下就有（≥30% 且 ≥1.5 倍）；紅底 ＝ 這一段新出現（比上一點多 ≥10 點）。最後一欄是一般股-日。</p>"
                     "<div class='wrap'><table class='tl'><tr><th class='l'>訊號</th>" + "".join(f"<th>{p}</th>" for p in PTN) + "<th>一般</th></tr>")
            for r in x.sort_values(["類別", PTN[0]], ascending=[True, False]).to_dict("records"):
                cells_ = []
                for k, p in enumerate(PTN):
                    cl = "t0" if (k == 0 and r["發動訊號"]) else ("up" if k > 0 and r.get(f"新增 {p}", 0) >= 0.10 else "")
                    cells_.append(f"<td class='{cl}'>{P0(r[p])}</td>")
                lab = html.escape(r["訊號"]) + (f"<br><small>{html.escape(str(r['類別']))}</small>" if cls == "狀態／特徵" else "")
                H.append(f"<tr><td class='l'>{lab}</td>" + "".join(cells_) + f"<td>{P0(r['一般'])}</td></tr>")
            H.append("</table></div>")
        H.append("<h2>四、全部狀態／特徵（依類別；起漲、一半、第一頂三點）</h2>")
        x = c[c["類"] == "狀態／特徵"]
        for cat in [v for v in dict.fromkeys(list(CATG.values())) if v in set(x["類別"])]:
            y = x[x["類別"] == cat]
            H.append(f"<details><summary>{html.escape(cat)}（{len(y)} 個級距）</summary><div class='wrap'><table class='tl'><tr><th class='l'>級距</th><th>起漲</th><th>50%</th><th>第一頂</th><th>一般</th><th>起漲倍數</th></tr>")
            for r in y.to_dict("records"):
                H.append(f"<tr><td class='l'>{html.escape(r['訊號'])}</td><td class='{'t0' if r['發動訊號'] else ''}'>{P0(r[PTN[0]])}</td><td>{P0(r[PTN[5]])}</td><td>{P0(r[PTN[10]])}</td>"
                         f"<td>{P0(r['一般'])}</td><td>{XX(r[PTN[0] + ' 倍數'])}</td></tr>")
            H.append("</table></div></details>")
        j = JS[JS["版本"] == vn]; tp = TOPX[TOPX["版本"] == vn]["訊號"].tolist()
        H.append("<h2>五、判斷：低檔股票發動當下有這些，之後變飆股的比例</h2><p class='note'>母體 ＝ 同一版低檔位置的全部股-日；變飆股 ＝ 各格定義（H 日內任一天漲到 g）；倍數 ＝ ÷ 同格基準，取格中位。"
                 "探索段依倍數排前 10，確認段照報。一年內先跌 15% ＝ 250 日內先跌到 −15%（早於漲到 +15%；只算滿一年的日子）。</p>")

        def jrow(nm):
            a = j[(j["訊號"] == nm) & (j["段"] == "探索")]; b = j[(j["訊號"] == nm) & (j["段"] == "確認")]
            if not len(a) or not len(b):
                return ""
            a = a.iloc[0]; b = b.iloc[0]
            return (f"<tr><td class='l'>{html.escape(nm)}</td><td>{XX(a['倍數 格中位'])}</td><td>{XX(b['倍數 格中位'])}</td><td>{P1(b['變飆股比例 格中位'])}</td>"
                    f"<td>{b['每天平均幾檔']:.1f}</td><td>{P0(b['一年內先跌15%'])}</td></tr>")
        hdr = "<div class='wrap'><table class='tl'><tr><th class='l'>訊號</th><th>探索 倍數</th><th>確認 倍數</th><th>確認 變飆股比例</th><th>確認 每天幾檔</th><th>確認 先跌15%</th></tr>"
        H.append("<h3>探索段前 10 名 → 確認段</h3>" + hdr + jrow("基準（不看訊號）") + "".join(jrow(nm) for nm in tp) + "</table></div>")
        H.append("<details><summary>當下訊號（逐個）</summary>" + hdr + "".join(jrow(nm) for nm in SIGN) + "</table></div></details>")
        H.append("<details><summary>狀態／特徵候選（逐個）</summary>" + hdr + "".join(jrow(nm) for nm in META["特徵候選"]) + "</table></div></details>")
        H.append("<details><summary>組合（同時 ≥ k 個）</summary>" + hdr + "".join(jrow(nm) for nm in j["訊號"].unique() if "同時" in nm) + "</table></div></details>")
        H.append("</div>")
    H.append("<h2>定義</h2><ul class='note'><li>當下訊號（近 3 個交易日內發生）：MACD 金叉（12／26／9）、KD 金叉（9 日）、RSI14 上穿 50、MA20 上穿 MA60、收盤創 20 日／55 日新高、量 ≥ 前 20 日均量 2 倍、"
             "收盤站上布林中軌／上軌（20 日、2 倍標準差）、OBV 上穿 20 日均、三大法人連買 3 日、營收近 3 月年增平均 ＞20% 且近 20 日漲幅 ＜10%、創一年新高、月營收創 24 月新高、被列注意、進入處置。</li>"
             "<li>狀態／特徵 ＝ 飆股回推的特徵表全部級距（五等分：Q1 最低、Q5 最高，每天全市場比）＋ 低檔打底四個（低檔盤整天數、距一年最低幾天、量縮程度、波動收斂）。</li>"
             "<li>V4「之前沒大漲」＝ 位置 ≤0.4、120 日報酬不在最高五分之一、20 日漲停 ＜3 次。</li></ul>")
    H.append("<script>function sw(){var v=document.getElementById('sv').value;document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='v'+v))}"
             "document.getElementById('sv').value='1';sw()</script></main></body></html>")
    cs = c0[c0["類"] == "當下訊號"].set_index("訊號")
    g = lambda nm, sg, k: j0[(j0["訊號"] == nm) & (j0["段"] == sg)][k].iloc[0]
    honest = (f"<li><b>起漲日本身就是最低點</b>（事件的定義使然），所以「發動當下就有」的多半是「價格在低檔」這類狀態；真正看得到發動是在漲到第一頂的 1 成時："
              f"量 ≥ 20 日均量 2 倍 {P0(cs.loc['量≥20日均量2倍', PTN[1]])}、創 20 日新高 {P0(cs.loc['創20日新高', PTN[1]])}、站上布林上軌 {P0(cs.loc['站上布林上軌', PTN[1]])}、KD 金叉 {P0(cs.loc['KD金叉', PTN[1]])}"
              f"（一般股-日 {P0(cs.loc['量≥20日均量2倍', '一般'])}、{P0(cs.loc['創20日新高', '一般'])}、{P0(cs.loc['站上布林上軌', '一般'])}、{P0(cs.loc['KD金叉', '一般'])}）；"
              f"之後一路增加的是注意股、漲停次數、周轉率、融資增加、創一年新高。</li>"
              f"<li class='ok'><b>誠實的回答：發動當下分不出來</b>。低檔股票每天約 {g('基準（不看訊號）', '確認', '每天平均幾檔'):.0f} 檔，之後變飆股的只有 {P1(g('基準（不看訊號）', '確認', '變飆股比例 格中位'))}（格中位）；"
              f"探索段倍數最高的前 10 名到確認段大多掉回 1 倍左右。兩段都 ＞1.3 倍的少數幾個（例如被列注意 {XX(g('被列注意', '探索', '倍數 格中位'))}→{XX(g('被列注意', '確認', '倍數 格中位'))} 倍、"
              f"當下訊號同時 ≥5 個 {XX(g('當下訊號同時 ≥5 個', '探索', '倍數 格中位'))}→{XX(g('當下訊號同時 ≥5 個', '確認', '倍數 格中位'))} 倍），變飆股比例也只有 "
              f"{P1(g('被列注意', '確認', '變飆股比例 格中位'))}、{P1(g('當下訊號同時 ≥5 個', '確認', '變飆股比例 格中位'))}，而一年內先跌 15% 的約一半。</li>")
    txt = "\n".join(H).replace("__HONEST__", honest)
    open(os.path.join(OUT, "低檔發動到第一頂的訊號.html"), "w", encoding="utf-8").write(txt)
    log("[網頁] 完成")


HONEST = ""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()
