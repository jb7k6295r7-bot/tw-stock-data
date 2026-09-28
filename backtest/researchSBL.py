# -*- coding: utf-8 -*-
"""PREREG借券法人 seq1（台股策略線 登錄 sha 9d8ebf5b85c263f9；裁定 seq257 §五 發號、N ＋1；seq262 §四 4 核准照原登錄；seq259 §四 資料窗）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSBL [--procs 2] [--seeds 200] [--reps 1000] [--report]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchSBL_check.py

問：借券賣出多的股票之後會不會比較弱？投信／外資買的會不會比較強？當營量 v1 的過濾，有沒有比原本好？

═══ 資料（⭐ 看任何數字前寫死）═══
  借券：tw-stock-data main aa964804e7（git archive、repo 外、唯讀）data/universe/sbl（上市）＋ otcsbl（上櫃），2015-01-05 起逐日
        ⇒ ~/h2data/univ_aa964804e7/data/universe/；main 快照 edc6f8002f 裡【沒有】universe/ 這一層（已查）
        欄：sbl_sell ＝ 借券當日賣出（股）、sbl_balance ＝ 借券賣出當日餘額（股）；s_* 是融券（本件不用）
        某日某檔不在當日檔 ⇒ 該日借券賣出 ＝ 0（不在借券名單 ＝ 不能借券賣出；計數必報）
  價量、股數：接合版面 ~/evtdata/stitch_950ad26e12_edc6f8002f（早年 950ad26e12 ≤ 2014-12-31 ＋ main edc6f ≥ 2015-01-05；PREREG事件 seq2 所建、唯讀沿用；STITCH.json 記 sha）
        股數 ＝ stocks/<代號>.csv 的 shares（逐日；只 ffill、⛔ 不 bfill；≤ 0 ⇒ NaN；同 p4_features.load_shares）
  法人：stocks_inst（股）；早年 950ad26e12（2012-05-02 起）≤ 2014-12-31 ＋ main edc6f ≥ 2015-01-05；某日無列 ⇒ 0；窗碰到的那一段沒有該股法人檔 ⇒ NaN
═══ 量測（登錄 §一；T ＝ 資料日、動作 ＝ T＋1 開盤）═══
  S_L ＝ Σ(T−L+1..T) 借券賣出股數 ÷ Σ 同期成交股數（stocks volume；無成交日 0；分母 0 ⇒ NaN）；窗首 ＜ 2015-01-05 ⇒ NaN
  I_L ＝ Σ 投信淨買股數 ÷ 股數[T]｜F_L 外資（stocks_inst foreign）同法；窗首 ＜ 法人起點 ⇒ NaN
  B ＝ 借券賣出餘額[T] ÷ 股數[T]（登錄「另報」⇒ 只描述）；L ∈ {5, 20, 60}；窗 ＝ 交易日曆位置（不是有效 K 棒）
═══ 單筆層（登錄 §二）═══
  M1 月：每月第一個交易日 t；T ＝ t−1；母體 ＝ t 當時的 W1 eligible（PREREG事件 seq2 E6 同規則：2012-06～2014-12 早年面板、2015-01～07 接合版面補定、2015-08 起 panel_ext）
  M2 分組池 ＝ 母體 ∧ T 有效 K 棒 ∧ T＋1 可買（有成交、開盤有效、非開盤漲停）∧ 量測值有限；avgdown.deciles（同值依代號序）⇒ 最高十分位（9）、最低（0）
  M3 報酬 R_H ＝ c_ff[min(T＋H, 末日)] ÷ o[T＋1] − 1（還原價；c_ff ＝ 收盤 ffill ⇒ 停止交易以最後收盤計；資料尾以末日收盤計 ＝ t1_censor 同讀法、計數必報）；
     硬斷點 ⇒ 該股該月該 H 剔除（research11.load_bars 的 next_bad：有效 K 棒 [k_T−19, k_x] 有壞根；load_bars 為 None ⇒ 剔除）；H ∈ {5, 20, 60, 120}
  M4 基準② ＝ 同 T、同 H：母體 ∧ 可買 ∧ R_H 有限 ∧ 前 20 日報酬（avgdown.r20_cal）有限 ⇒ 十分位；ȳ ＝ 同十分位【其他】股 R_H 平均；X ＝ R_H − ȳ
  M5 判定量 D ＝ 最高組 X 平均 − 最低組 X 平均（兩組迴歸、T 曆月分群 CR0）；⭐ 扣成本 ＝ 成本帶 ±0.585%：Bonferroni CI 下緣 ＞ +0.585% ⇒ 測得出（＋）、
     上緣 ＜ −0.585% ⇒ 測得出（−）、否則測不出（＝ 往不利方向移 0.585% 後 CI 不含 0；價差兩腿成本相消，改用成本帶）；另報毛結果與「看好端 X − 0.585%」
     （看好端 ＝ 先驗方向：S、B 取最低組；I、F 取最高組）
     ⚠ 試跑（種子 2 顆）時第一版寫成「D − sign(D)×0.585%、CI 同移」，|D| ＜ 成本的格會被翻成反向顯著 ⇒ 是讀法錯，改成成本帶；正式跑之前改、改完才看正式數字
  M6 n_eff ＝ min(各組筆數, 各組 H 日區段數)；＜ 30 出口①（不可判定、不計 k）、30～99 ②、≥ 100 ③；
     Bonferroni：α ＝ 0.05／k，k ＝ 該段可判定格數（S、I、F × L × H；早年 S 只描述、不計）⇒ 扣成本 CI 不含 0 ⇒ 測得出；另列 95% 未校正
  M7 「穩」（seq253 收緊）：相鄰視窗（5–20–60–120）本身也過 Bonferroni 門檻、同方向才寫；否則「方向一致，但只有 X 天過門檻」
  M8 段（以 t 所在月）：探索 2017-03～2021-12（判）｜確認 2022-01～2026-08（判）｜早年 2012-08～2016-12（I、F 判；⭐ 2012-08 起 ＝ L＝60 的法人窗完整）；
     S、B 的早年只描述（2015-05～2016-12；借券 2015-01-05 起、L＝60 窗完整）——裁定 seq259 §四
  M9 假訊號：每格每段 1,000 次；每個月在「同一個 X 池」（該 H 的 X 有限 ∧ 量測值有限）隨機抽同樣大小的最高組、最低組（不重疊）⇒ 同式 D；
     p ＝ 假 D 在真 D 方向上 ≥ 真 D 的比例；rng default_rng([20260928, 變數, L, H, 段])
═══ 組合層（登錄 §三；營量 v1 本體一字不改）═══
  C1 營量 v1 T1 版 ＝ listexit_lines.setup_t1(t1=True)（＝ rerun17.setup_and(..., t1=True)）的 AND 窗內（2017-03-02～2026-08-24）＝ researchT1fix #13：
     simulate_mtm(sig, "H60", 20, default_rng(7000＋r), log=[], d_max=None, pick="relvol", queue_days=0, stop_force ＝ stop_force_days(valid_from_data(AND 全部股票), 主窗尾))
     閘：原版 200 顆（多帶 audit、只記錄）＝ resultsT1fix/seeds.csv.gz c13 t1（年化、回落 repr、eq_sha 逐位元）
  C2 過濾（每筆 AND 列、資料日 ＝ 進場日 − 1）：甲 剔除 S_L 在「進場日當月 W1 eligible 母體」的最高十分位（該股在母體內 ⇒ 用其十分位；不在 ⇒ S ≥ 最高十分位最小值即算）；
     乙 只留 I_L ＞ 0｜丙 只留 I_L＋F_L ＞ 0｜丁 甲＋乙；× L 3 ＝ 12 格；NaN ⇒ 甲不剔（非最高）、乙丙「不留」；計數必報
  C3 段：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（同一條權益，rerun17.win_metrics 段內讀）；200 顆取年化中位、回落中位 ⇒ 使用者判準對 0050 同段
  C4 早年：營量 v1 早年版面（researchV.body_setup("main")、只上市、researchYear1M.sig_of(13, "mtm")、and_censor ＝ T1、stop_force 開；同 researchYLretest b2e）；
     ⭐ 只有乙、丙（法人）可跑；甲、丁要借券 ⇒ 早年不可判定（seq259 §四）；
     過濾要 L＝60 法人窗完整 ⇒ 早年段 ＝ 進場 2012-08-01～2014-12-31（訊號只留進場 ≥ 2012-08-01；原版同窗並列）；
     閘：原版全早年窗（2012-06-04 起）200 顆 ＝ resultsYLretest/b2_early_seeds.csv「main|開|N20|H60」逐位元
  C5 退化（挑前排除；登錄 K7）：探索段平均持股 ＜ 10（audit 逐日重建）或現金 ＞ 30%（1 − 平均持股市值÷權益）⇒ 不進挑選
  C6 挑法：探索段 年化÷|回落| 最高（同分取年化高）⇒ 確認段、早年段判；件標籤 ＝ 兩段較嚴者（早年不可判定 ⇒ 只看確認，註明）
  C7 同過濾率隨機剔除 1,000 次（登錄）：挑中格每個進場月保留與真過濾同樣筆數、從該月 AND 列均勻抽；引擎種子 7000＋i、抽樣 default_rng([20260928, 7, i])；
     p ＝ 隨機年化 ≥ 挑中格年化中位 的比例（各段）；早年同（挑中格是乙、丙才有）
  C8 新規矩 ③：挑中格確認或早年「合格／另列」⇒ 另跑出場敏感度（描述、不判；同 PREREG事件 seq2 E11 的定義）：SL10、SL20、TP30h、TP50h、AT2、R0-40、檔數 10／30
輸出 backtest/resultsSBL/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import research11 as R11
from backtest import rerun17 as RR
from backtest import avgdown as AV

ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_edc6f8002f/data")
EINST = os.path.expanduser("~/earlydata/950ad26e12/main/data/stocks_inst")
MAIN = RR.H2D
UNIV_SHA = "aa964804e72c6a09ea3a166a65826adcb45654b7"
UD = os.path.expanduser(f"~/h2data/univ_{UNIV_SHA[:10]}/data/universe")
EPANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
MPANEL = "backtest/resultsp9_engine/panel_ext.csv.gz"
OUT = "backtest/resultsSBL"
LS = (5, 20, 60)
HS = (5, 20, 60, 120)
VARS = ("S", "I", "F")
COST = 0.00585
LIQ_MIN, MIN_BARS = 50_000_000, 120
SEGM = {"早年": ("2012-08", "2016-12"), "探索": ("2017-03", "2021-12"), "確認": ("2022-01", "2026-08")}
S_EARLY = ("2015-05", "2016-12")
FAV = {"S": 0, "B": 0, "I": 9, "F": 9}                     # 看好端（先驗方向）
SEG_C = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
EARLY_FROM = "2012-08-01"
SEED0 = 7000
C50, R50 = 0.24020209886370614, 0.7073712681980713
_G: dict = {}
_W: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


# ═════════════ 借券日檔 ═════════════
def load_sbl(cal):
    n = len(cal); pos = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(cal)}
    sell, bal = {}, {}
    cnt = {"日數": 0, "日檔缺": 0, "列": 0}
    days = sorted(set(f[:-4] for f in os.listdir(os.path.join(UD, "sbl"))) | set(f[:-4] for f in os.listdir(os.path.join(UD, "otcsbl"))))
    for d in days:
        if d not in pos:
            continue
        i = pos[d]; cnt["日數"] += 1
        for sub in ("sbl", "otcsbl"):
            p = os.path.join(UD, sub, d + ".csv")
            if not os.path.exists(p):
                cnt["日檔缺"] += 1; continue
            x = pd.read_csv(p, dtype={"stock_id": str}, usecols=["stock_id", "sbl_sell", "sbl_balance"])
            cnt["列"] += len(x)
            for s, a, b in zip(x["stock_id"], pd.to_numeric(x["sbl_sell"], errors="coerce"), pd.to_numeric(x["sbl_balance"], errors="coerce")):
                if s not in sell:
                    sell[s] = np.zeros(n, np.float64); bal[s] = np.zeros(n, np.float64)
                sell[s][i] += 0.0 if not np.isfinite(a) else a
                bal[s][i] += 0.0 if not np.isfinite(b) else b
    s0 = pos["2015-01-05"]
    cal_days = sum(1 for d in cal if d >= pd.Timestamp("2015-01-05"))
    cnt["交易日（2015-01-05 起）"] = cal_days
    return sell, bal, s0, cnt


# ═════════════ 每檔 ═════════════
def load_one(args):
    sid, mk = args
    cal = _G["cal"]; n = len(cal); NEED = _G["NEED"]; MT = _G["MT"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float); valid = np.isfinite(c)
    cff = pd.Series(c).ffill().to_numpy(float)
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "amount", "volume", "shares"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)
    vol = np.nan_to_num(pd.to_numeric(raw["volume"], errors="coerce").to_numpy(float), nan=0.0)
    sh = pd.to_numeric(raw["shares"], errors="coerce")
    sh = sh.where(sh > 0).ffill().to_numpy(float)
    tb = TR.one(sid, cal)
    trd, up = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    idx = np.flatnonzero(valid)
    r20 = AV.r20_cal(c, idx)
    buy = np.zeros(n, bool)
    buy[:-1] = valid[:-1] & trd[1:] & np.isfinite(o[1:]) & (o[1:] > 0) & ~up[1:]
    B = R11.load_bars(sid, mk, cal)
    R = {H: np.full(len(MT), np.nan) for H in HS}
    cens = {H: np.zeros(len(MT), bool) for H in HS}
    if B is not None:
        assert np.array_equal(B["idx"], idx), sid
        nb = B["next_bad"]; k_of = np.full(n, -1); k_of[idx] = np.arange(len(idx))
        ok = buy[MT]
        for H in HS:
            x = np.minimum(MT + H, n - 1)
            kx = np.searchsorted(idx, x, side="right") - 1
            kT = k_of[MT]
            clean = ok & (kT >= 0) & (nb[np.maximum(kT - 19, 0)] > kx)
            t = MT[clean]
            R[H][clean] = cff[np.minimum(t + H, n - 1)] / o[t + 1] - 1.0
            cens[H] = clean & (MT + H > n - 1)
    # 法人
    tr_ = np.zeros(n); fo_ = np.zeros(n); has = []
    for p, lo, hi in ((os.path.join(EINST, sid + ".csv"), None, "2014-12-31"), (os.path.join(MAIN, "stocks_inst", sid + ".csv"), "2015-01-05", None)):
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date")
            if lo:
                x = x[x["date"] >= lo]
            if hi:
                x = x[x["date"] <= hi]
            ii = cal.get_indexer(pd.to_datetime(x["date"]))
            m = ii >= 0
            tr_[ii[m]] += np.nan_to_num(pd.to_numeric(x["trust"], errors="coerce").to_numpy(float)[m])
            fo_[ii[m]] += np.nan_to_num(pd.to_numeric(x["foreign"], errors="coerce").to_numpy(float)[m])
            has.append(bool(m.any()))
        else:
            has.append(False)
    has_e, has_m = has
    i0 = _G["INST0"]; OFF = _G["OFF"]
    ctr, cfo, cvol = np.r_[0, np.cumsum(tr_)], np.r_[0, np.cumsum(fo_)], np.r_[0, np.cumsum(vol)]
    sb = _G["SBL_SELL"].get(sid); bb = _G["SBL_BAL"].get(sid)
    sb = np.zeros(n) if sb is None else sb; bb = np.zeros(n) if bb is None else bb
    csb = np.r_[0, np.cumsum(sb)]
    s0 = _G["SBL0"]
    V = {}
    T = NEED
    shT = sh[T]
    for L in LS:
        a = T - L + 1
        okI = (a >= i0) & np.isfinite(shT) & ((a >= OFF) | has_e) & ((T < OFF) | has_m)   # 窗內各段都要有該段的法人檔
        V[f"I{L}"] = np.where(okI, (ctr[T + 1] - ctr[a.clip(0)]) / shT, np.nan)
        V[f"F{L}"] = np.where(okI, (cfo[T + 1] - cfo[a.clip(0)]) / shT, np.nan)
        den = cvol[T + 1] - cvol[a.clip(0)]
        okS = (a >= s0) & (den > 0)
        V[f"S{L}"] = np.where(okS, (csb[T + 1] - csb[a.clip(0)]) / np.where(den > 0, den, 1.0), np.nan)
    V["B"] = np.where((T >= s0) & np.isfinite(shT), bb[T] / shT, np.nan)
    out = {"V": V, "valid": valid, "amt": amt.astype(np.float32), "buyMT": buy[MT], "validMT": valid[MT], "r20MT": r20[MT], "R": R, "cens": cens}
    return sid, out


# ═════════════ 母體（照 PREREG事件 seq2 E6 的規則；程式另寫）═════════════
def eligibility(cal, P, sids):
    n = len(cal); ix = {s: i for i, s in enumerate(sids)}
    ep = pd.read_csv(EPANEL, dtype={"stock_id": str}, parse_dates=["measure_date"])
    mp = pd.read_csv(MPANEL, dtype={"stock_id": str}, parse_dates=["measure_date"])
    tf = lambda s: s.astype(str).isin(["True", "1", "1.0"])
    M = []
    for md, g in ep.groupby("measure_date"):
        if md < pd.Timestamp("2012-06-01"):
            continue
        M.append((md, set(g.loc[tf(g["eligible"]).to_numpy(), "stock_id"]), "早年 W1"))
    for md, g in mp.groupby("measure_date"):
        if md >= pd.Timestamp("2015-08-01"):
            M.append((md, set(g.loc[tf(g["eligible"]).to_numpy(), "stock_id"]), "panel_ext W1")); continue
        pos = int(cal.searchsorted(md))
        ok = set(s for s in g["stock_id"] if s in P and P[s] is not None and int(P[s]["valid"][:pos + 1].sum()) >= MIN_BARS)
        if md >= pd.Timestamp("2015-02-01"):
            el = tf(g["liq_ok"]) & tf(g["inst_ok"])
            M.append((md, set(g.loc[el.to_numpy(), "stock_id"]) & ok, "2015 liq∧inst∧接合 bars"))
        else:
            ok2 = set()
            for s in ok:
                vv = np.flatnonzero(P[s]["valid"][:pos + 1])[-20:]
                if len(vv) == 20 and np.nanmean(P[s]["amt"][vv].astype(float)) >= LIQ_MIN:
                    ok2.add(s)
            M.append((md, ok2, "2015-01 接合 amt20∧bars"))
    M.sort(key=lambda t: t[0])
    E = np.zeros((len(sids), n), bool)
    mpos = [int(cal.searchsorted(md)) for md, _, _ in M]
    rules = {}
    for j, (md, S_, rule) in enumerate(M):
        a = mpos[j]; b = mpos[j + 1] if j + 1 < len(M) else n
        for s in S_:
            if s in ix:
                E[ix[s], a:b] = True
        rules[str(md.date())] = [rule, len(S_), int(sum(1 for s in S_ if s in ix))]
    return E, rules, [str(md.date()) for md, _, _ in M]


# ═════════════ 單筆層統計 ═════════════
def reg2(y, grp, cl):
    X = np.column_stack([np.ones(len(y)), grp.astype(float)])
    Xi = np.linalg.inv(X.T @ X); b = Xi @ X.T @ y; u = y - X @ b
    meat = np.zeros((2, 2))
    for c_ in np.unique(cl):
        m_ = cl == c_; s_ = X[m_].T @ u[m_]; meat += np.outer(s_, s_)
    V = Xi @ meat @ Xi
    return float(b[1]), float(np.sqrt(V[1, 1]))


def exit_of(neff):
    return "出口①" if neff < 30 else ("出口②" if neff < 100 else "出口③")


def verdict(lo, hi):
    return "測不出" if lo <= 0 <= hi else ("測得出（＋）" if lo > 0 else "測得出（−）")


def x_month(Ri, r20i, pool):
    """同 T 同 H：基準② X（avgdown.deciles 於 pool；同十分位其他股平均）。"""
    X = np.full(len(Ri), np.nan)
    v = np.where(pool, r20i, np.nan)
    d = AV.deciles(v)
    for q in range(10):
        m = d == q
        k = int(m.sum())
        if k < 2:
            continue
        s = Ri[m].sum()
        X[m] = Ri[m] - (s - Ri[m]) / (k - 1)
    return X


def fake_p(month_blocks, D_true, seed):
    """month_blocks：[(Xpool, n_top, n_bot)]；每月隨機抽不重疊兩組 ⇒ 合併 D；1,000 次。"""
    rng = np.random.default_rng(seed); R_ = _G["REPS"]
    st = np.zeros(R_); sb = np.zeros(R_); nt = 0; nb = 0
    for Xp, a, b in month_blocks:
        if a == 0 or b == 0 or a + b > len(Xp):
            continue
        o = np.argsort(rng.random((R_, len(Xp))), axis=1)[:, :a + b]
        st += Xp[o[:, :a]].sum(1); sb += Xp[o[:, a:]].sum(1); nt += a; nb += b
    if nt == 0 or nb == 0:
        return np.nan, np.nan
    Df = st / nt - sb / nb
    sg = 1.0 if D_true >= 0 else -1.0
    return float(np.mean(sg * Df >= sg * D_true)), float(np.median(Df))


# ═════════════ 組合層引擎 ═════════════
def _seg_stats(W, o, aud, N):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    cnt = np.zeros(len(eq) + 1)
    for a in aud:
        cnt[a["t"]] += 1 if a["side"] == "buy" else -1
    hold = np.cumsum(cnt)[:len(eq)]
    row = {}
    for sg, (x, y) in W["SEGP"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_持股"] = float(np.mean(hold[x:y + 1]))
        row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
    row["持股最大"] = float(hold.max()); row["持股最小"] = float(hold.min()); row["持股尾"] = float(hold[-1])
    return row, eq


def _eng(W, sig, seed, N=20, **kw):
    aud = []
    o = R11.simulate_mtm(sig, "H60", N, np.random.default_rng(seed), W["closes"], W["opens"], W["ncal"], return_equity=True,
                         log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=aud, **kw)
    return o, aud


def run_cell(job):
    world, key, r = job
    W = _W[world]
    o, aud = _eng(W, W["SIG"][key], SEED0 + r)
    row, eq = _seg_stats(W, o, aud, 20)
    c, m, _ = RR.win_metrics(eq, o["first"], o["end"], W["w0"], W["w1"])
    row.update({"世界": world, "格": key, "r": r, "全窗_年化": float(c), "全窗_回落": float(m), "eq_sha": sha(eq), "強制出場": int(o.get("x_stop_force_n", -1)),
                "trades": int(o["trades"])})
    return row


def run_rand(job):
    world, key, i = job
    W = _W[world]
    sig = W["SIG"][key + "_base"]
    kept = W["KEEP"][key]                                  # {月: 保留筆數}
    rng = np.random.default_rng([20260928, 7, i])
    parts = []
    for mth, g in sig.groupby("_m", sort=True):
        k = kept.get(mth, 0)
        if k > 0:
            parts.append(g.iloc[np.sort(rng.choice(len(g), size=k, replace=False))])
    s2 = pd.concat(parts).sort_index() if parts else sig.iloc[:0]
    o, aud = _eng(W, s2.drop(columns=["_m"]), SEED0 + i)
    row, _ = _seg_stats(W, o, aud, 20)
    row.update({"世界": world, "i": i, "筆數": int(len(s2))})
    return row


def run_sens(job):
    world, name, r = job
    W = _W[world]
    v = dict(W["VAR"][name]); N = v.pop("nslot", 20)
    sig = W["SIGV"].get(name, W["SIG"][W["PICK"]])
    o, aud = _eng(W, sig, SEED0 + r, N=N, **v)
    row, _ = _seg_stats(W, o, aud, N)
    row.update({"世界": world, "變體": name, "r": r})
    return row


def exit_variants(W, base, cal, mk):
    """AT2、R0-40（PREREG事件 seq2 E11 同定義；程式另寫）⇒ 改 xpos_H60／g_H60。"""
    n = len(cal); cache = {}
    A2 = base.copy(); R4 = base.copy(); cA = cR = 0
    xs, gs = "xpos_H60", "g_H60"
    cx, cg = A2.columns.get_loc(xs), A2.columns.get_loc(gs)
    for i, (s, e, x) in enumerate(zip(base["sid"], base["entry_pos"], base[xs])):
        if s not in cache:
            st = D.load_stock(s, mk.get(s, "twse"), cal); df = st.df
            c = df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(c))
            h = df["high"].to_numpy(float)[idx]; l_ = df["low"].to_numpy(float)[idx]; cc = c[idx]
            tr = np.r_[h[0] - l_[0], np.maximum.reduce([h[1:] - l_[1:], np.abs(h[1:] - cc[:-1]), np.abs(l_[1:] - cc[:-1])])]
            atr = np.full(len(idx), np.nan)
            if len(idx) >= 14:
                atr[13] = tr[:14].mean()
                for k in range(14, len(idx)):
                    atr[k] = (atr[k - 1] * 13 + tr[k]) / 14
            cache[s] = (idx, cc, atr, df["open"].to_numpy(float))
        idx, cc, atr, o = cache[s]
        ke = int(np.searchsorted(idx, e)); kx = int(np.searchsorted(idx, min(int(x), n - 1), side="right") - 1)
        if ke >= len(idx) or idx[ke] != e or not np.isfinite(o[e]):
            continue
        oe = o[e]; mx = cc[ke]
        for k in range(ke + 1, kx + 1):
            if np.isfinite(atr[k - 1]) and cc[k] <= mx - 2 * atr[k - 1]:
                A2.iat[i, cx] = int(idx[k]); A2.iat[i, cg] = cc[k] / oe - 1.0; cA += 1
                break
            mx = max(mx, cc[k])
        k40 = ke + 39
        if k40 <= kx and k40 < len(idx) and idx[k40] < min(int(x), n):
            if cc[k40] <= oe:
                R4.iat[i, cx] = int(idx[k40]); R4.iat[i, cg] = cc[k40] / oe - 1.0; cR += 1
    return {"AT2": A2, "R0-40": R4}, {"AT2 提前": cA, "R0-40 提前": cR, "列": int(len(base))}


def label(c, m, b):
    bc, bm = b
    return "合格" if (c > bc and c / abs(m) >= bc / abs(bm)) else ("另列" if c > bc else "不合格")


def _p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def _f3(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x:.3f}"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells_single.csv"))
    PT = pd.read_csv(os.path.join(OUT, "cells_combo.csv")); EPT = pd.read_csv(os.path.join(OUT, "cells_combo_early.csv"))
    J = S["組合層判定"]; pk = S["挑中格"]; B50 = S["0050 同段"]; eb = S["0050 早年"]["2012-08-01～2014-12-31"]
    NM = {"甲": "剔借券高（S 最高十分位）", "乙": "只留投信買（I＞0）", "丙": "只留投信＋外資買（I＋F＞0）", "丁": "剔借券高＋只留投信買"}
    pname = (NM[pk.split("_L")[0]] + f"，L＝{pk.split('_L')[1]}") if pk else "—"
    sig = C[C["結果"].astype(str).str.startswith("測得出")]
    L = ["# PREREG借券法人 seq1（借券賣出與法人過濾）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 sha 9d8ebf5b85c263f9；裁定 seq257 §五（N ＋1）、seq262 §四 4、seq259 §四。回測線。"
         "⭐ 停止交易強制出場：開；T1（資料尾）：開。引用請寫「回測 PREREG借券法人」。", ""]
    if pk:
        c = J["確認"]; e = J["早年"]
        etxt = f"早年段 {_p(e['年化'])}（{e['標籤']}；原版 {_p(e['原版年化'])}）" if "年化" in e else f"早年段{e['標籤']}"
        L.append(f"**結論：營量 v1 加〔{pname}〕：2022～2026 年化 {_p(c['年化'])}（原版 {_p(c['原版年化'])}、0050 {_p(c['0050'])}；{c['標籤']}）；{etxt}；"
                 f"隨機剔同比例 p ＝ {_f3(c['隨機剔除p（年化）'])}。件標籤：{J['件標籤']}。單筆層在 Bonferroni＋成本帶下測得出 {len(sig)} 格"
                 f"（可判定 {int(sum(S['單筆層 Bonferroni k'].values()))} 格）。**")
    else:
        L.append("**結論：組合層 12 格全部退化，沒有挑中格。**")
    L += ["", "| | 探索 2017-03～2021-12 | 確認 2022-01～2026-08 | 早年 2012-08～2014-12 |", "|---|---|---|---|"]
    po = PT.set_index("格").loc["原版"]; eo = EPT.set_index("格").loc["原版"]
    L.append(f"| 營量 v1 原版 | {_p(po['探索_年化'])}／{_p(po['探索_回落'])} | {_p(po['確認_年化'])}／{_p(po['確認_回落'])}（{po['確認_標籤']}） | "
             f"{_p(eo['早年_年化'])}／{_p(eo['早年_回落'])}（{eo['早年_標籤']}） |")
    if pk:
        pr = PT.set_index("格").loc[pk]
        es = EPT.set_index("格").loc[pk] if pk in set(EPT["格"]) else None
        L.append(f"| 挑中 {pk} | {_p(pr['探索_年化'])}／{_p(pr['探索_回落'])} | {_p(pr['確認_年化'])}／{_p(pr['確認_回落'])}（{pr['確認_標籤']}） | "
                 + (f"{_p(es['早年_年化'])}／{_p(es['早年_回落'])}（{es['早年_標籤']}）" if es is not None else "不可判定（要借券）") + " |")
        L.append(f"| 隨機剔同比例 p（年化） | {_f3(J['探索']['隨機剔除p（年化）'])} | {_f3(J['確認']['隨機剔除p（年化）'])} | {_f3(J['早年'].get('隨機剔除p（年化）'))} |")
    L.append(f"| 0050 | {_p(B50['探索']['cagr'])}／{_p(B50['探索']['mdd'])} | {_p(B50['確認']['cagr'])}／{_p(B50['確認']['mdd'])} | {_p(eb['cagr'])}／{_p(eb['mdd'])} |")
    L += ["", "（年化中位／回落中位，200 顆；標籤 ＝ 使用者判準對 0050 同段）", "", "## 一、單筆層（最高十分位 − 最低十分位，對基準②）", "",
          f"- Bonferroni k：{S['單筆層 Bonferroni k']}（出口②③ 才可判定；H60、H120 的 H 日區段數 ＜ 30 ⇒ 出口①）；成本帶 ±0.585%",
          "- 早年段：I、F 判（2012-08～2016-12）；S 與 B 只描述（2015-05～2016-12，裁定 seq259 §四）", "",
          "| 變數 | L | H | 段 | n 高／低 | n_eff | D（毛） | Bonferroni CI | 結果 | 看好端 X − 0.585% | 假訊號 p | 穩 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in C.iterrows():
        Ls = "—" if pd.isna(r["L"]) else int(r["L"])
        stv = r["穩不穩"] if isinstance(r.get("穩不穩"), str) else ""
        L.append(f"| {r['變數']} | {Ls} | {r['H']} | {r['段']} | {r['n高']}／{r['n低']} | {r.get('n_eff', '—')} | {_p(r.get('D'))} | "
                 f"〔{_p(r.get('loB'))}, {_p(r.get('hiB'))}〕 | {r.get('結果', '—')} | {_p(r.get('看好端X扣'))} | {_f3(r.get('假訊號p'))} | {stv} |")
    L += ["", "## 二、組合層 12 格（套在營量 v1 T1 版；本體不改）", "",
          "| 格 | 保留筆數 | 探索 年化／回落（比值） | 探索 持股／現金 | 確認 年化／回落 | 確認標籤 | 退化 |", "|---|---|---|---|---|---|---|"]
    for _, r in PT.iterrows():
        L.append(f"| {r['格']} | {r['保留筆數']} | {_p(r['探索_年化'])}／{_p(r['探索_回落'])}（{r['探索_比值']:.3f}） | {r['探索_持股']:.1f}／{r['探索_現金'] * 100:.0f}% | "
                 f"{_p(r['確認_年化'])}／{_p(r['確認_回落'])} | {r['確認_標籤']} | {'是' if r['退化'] else ''} |")
    L += ["", "早年（2012-08-01～2014-12-31；只上市；只有乙、丙可跑）：", "", "| 格 | 保留筆數 | 年化／回落 | 持股／現金 | 標籤 |", "|---|---|---|---|---|"]
    for _, r in EPT.iterrows():
        L.append(f"| {r['格']} | {r['保留筆數']} | {_p(r['早年_年化'])}／{_p(r['早年_回落'])} | {r['早年_持股']:.1f}／{r['早年_現金'] * 100:.0f}% | {r['早年_標籤']} |")
    L += ["", f"- 退化（挑前排除；探索段平均持股 ＜ 10 或現金 ＞ 30%）：{S['退化（挑前排除）']}", f"- 挑中：{pk}（探索段比值最高）", ""]
    L += ["## 三、新規矩 ③", "", str(S["新規矩③"]), ""]
    sens = S.get("新規矩③ 出場敏感度（描述、不判；各段 [年化中位, 回落中位]）")
    if sens:
        L.append(sens["定義"]); L.append("")
        for wn in ("主", "早年"):
            if wn in sens:
                w = sens[wn]; segs = list(w["原格"])
                L += [f"{wn}（提前出場筆數 {w['提前出場筆數']}）：", "", "| 變體 | " + " | ".join(segs) + " |", "|---" * (len(segs) + 1) + "|"]
                for k, v in w.items():
                    if k == "提前出場筆數":
                        continue
                    L.append(f"| {k} | " + " | ".join(f"{_p(v[sg][0])}／{_p(v[sg][1])}" for sg in segs) + " |")
                L.append("")
    L += ["## 四、閘與計數", "", f"- 閘：{json.dumps(S['閘'], ensure_ascii=False)}", f"- 資料：{json.dumps(S['資料'], ensure_ascii=False)}",
          f"- 單位閘（S5 ＞ 1 的比例）：{S['單位閘（S5 ＞ 1 的比例）']}", f"- 過濾計數（主）：{json.dumps(S['過濾計數（主）'], ensure_ascii=False)}",
          f"- 過濾計數（早年）：{json.dumps(S['過濾計數（早年）'], ensure_ascii=False)}", f"- 資料尾以末日收盤計（股-月）：{S['資料尾以末日收盤計（股-月）']}",
          "- 「穩」照 seq253 收緊讀法；假訊號 1,000 次（單筆層：同月同池隨機兩組；組合層：同過濾率隨機剔除）",
          "- ⚠ 單筆層扣成本讀法在試跑（種子 2 顆）後由「D 往 0 移」改為成本帶（原讀法會把 |D| ＜ 成本的格翻成反向顯著）；正式數字是改完後才跑", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4] if len(L) > 4 else "")


# ═════════════ 主程式 ═════════════
def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200); ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--report", action="store_true", help="只重寫 REPORT.md")
    a = ap.parse_args()
    if a.report:
        report(); return
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    T0 = time.time()
    log(f"===== researchSBL {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜procs {a.procs} seeds {a.seeds} reps {a.reps}｜停止交易強制出場：開｜T1：開 =====")
    S = {"件": "PREREG借券法人 seq1（登錄 sha 9d8ebf5b85c263f9）", "資料": {"借券": f"tw-stock-data main {UNIV_SHA}（git archive、唯讀）data/universe/sbl＋otcsbl",
                                                                 "main 快照 edc6f 有無 universe/": os.path.isdir(os.path.join(MAIN, "universe")),
                                                                 "接合版面": json.load(open(os.path.join(ST, "STITCH.json"), encoding="utf-8"))}}
    _G["REPS"] = a.reps
    # ── 單筆層：接合版面 ──
    D.DATA = ST
    cal = D.load_calendar(); n = len(cal)
    per = pd.DatetimeIndex(cal).strftime("%Y-%m")
    firsts = np.r_[0, np.flatnonzero(per[1:] != per[:-1]) + 1]
    mon = {per[t]: int(t) for t in firsts}
    months = [m for m in sorted(mon) if "2012-08" <= m <= "2026-08"]
    MT = np.array([mon[m] - 1 for m in months])
    SELL, BAL, s0, cs = load_sbl(cal)
    S["資料"]["借券日檔"] = cs
    OFF = int(cal.searchsorted(pd.Timestamp("2015-01-05")))
    mcal = pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"]
    assert list(pd.to_datetime(mcal)) == list(cal[OFF:OFF + len(mcal)]), "⛔ main 日曆與接合版面不一致"
    A = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), dtype={"sid": str})
    need_and = set((A["entry_pos"].to_numpy() - 1 + OFF).tolist())
    e0, e1 = int(cal.searchsorted(pd.Timestamp("2012-07-01"))), int(cal.searchsorted(pd.Timestamp("2014-12-31")))
    NEED = np.array(sorted(set(MT.tolist()) | need_and | set(range(e0, e1 + 1))))
    inst0 = int(cal.searchsorted(pd.Timestamp("2012-05-02")))
    _G.update(cal=cal, NEED=NEED, MT=MT, SBL_SELL=SELL, SBL_BAL=BAL, SBL0=s0, INST0=inst0, OFF=OFF)
    roster = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    roster = roster[roster["kind"] == "stock"]
    mk = roster.set_index("stock_id")["market"].to_dict()
    sids_all = sorted(set(roster["stock_id"]))
    t0 = time.time()
    with Pool(a.procs) as pool:
        P = dict(pool.map(load_one, [(s, mk[s]) for s in sids_all], chunksize=8))
    sids = [s for s in sids_all if P[s] is not None]
    log(f"[讀檔] {len(sids)} 檔｜NEED {len(NEED)} 日｜月 {len(months)}（{months[0]}～{months[-1]}）｜{time.time() - t0:.0f}s")
    E, rules, mds = eligibility(cal, P, sids)
    S["母體量測日"] = rules
    ni = {int(t): i for i, t in enumerate(NEED)}
    VN = [f"{v}{L}" for v in VARS for L in LS] + ["B"]
    VAL = {k: np.column_stack([P[s]["V"][k] for s in sids]) for k in VN}           # [len(NEED), 檔]
    for s in sids:
        P[s]["V"] = None
    S["借券名單內（任一日）檔數"] = int(sum(1 for s in sids if s in SELL))
    # 單位檢查：借券賣出 ≤ 成交股數（S5 ≤ 1）
    s5 = VAL["S5"][np.isfinite(VAL["S5"])]
    S["單位閘（S5 ＞ 1 的比例）"] = float(np.mean(s5 > 1.0)) if len(s5) else None
    # 月面板
    rows = []
    cens_cnt = {H: 0 for H in HS}
    for j, m in enumerate(months):
        t = mon[m]; T = t - 1; k = ni[T]
        uni = E[:, t]
        validT = np.array([P[s]["validMT"][j] for s in sids]); buyT = np.array([P[s]["buyMT"][j] for s in sids])
        r20T = np.array([P[s]["r20MT"][j] for s in sids])
        base = uni & validT & buyT
        rec = {"月": m, "T": int(T), "sid": np.array(sids)[base]}
        for vn in VN:
            rec[vn] = VAL[vn][k][base]
        for H in HS:
            Ri = np.array([P[s]["R"][H][j] for s in sids])
            ce = np.array([P[s]["cens"][H][j] for s in sids])
            pool2 = uni & buyT & np.isfinite(Ri) & np.isfinite(r20T)
            X = x_month(np.where(pool2, Ri, 0.0), r20T, pool2)
            X[~pool2] = np.nan
            rec[f"R{H}"] = np.where(pool2, Ri, np.nan)[base]; rec[f"X{H}"] = X[base]
            cens_cnt[H] += int((ce & pool2 & base).sum())
        rows.append(pd.DataFrame(rec))
    PM = pd.concat(rows, ignore_index=True)
    PM.to_csv(os.path.join(OUT, "panel_month.csv.gz"), index=False, float_format="%.17g")
    S["資料尾以末日收盤計（股-月）"] = cens_cnt
    S["母體股-月（分組池基底）"] = int(len(PM))
    log(f"[月面板] {len(PM):,} 股-月｜單位閘 S5＞1 比例 {S['單位閘（S5 ＞ 1 的比例）']}｜{time.time() - T0:.0f}s")
    # 各格
    segm_of = {m: sg for sg, (x, y) in SEGM.items() for m in months if x <= m <= y}
    PM["段"] = PM["月"].map(segm_of)
    cells = []
    FK = {}
    for vn in VN:
        var = vn[0]
        L = int(vn[1:]) if vn != "B" else None
        for sg in SEGM:
            g = PM[PM["段"] == sg]
            if var in ("S", "B") and sg == "早年":
                g = g[(g["月"] >= S_EARLY[0]) & (g["月"] <= S_EARLY[1])]
            if not len(g):
                continue
            dec = np.full(len(g), -1)
            gi = g.index.to_numpy()
            for m_, gg in g.groupby("月", sort=True):
                pos_ = np.searchsorted(gi, gg.index.to_numpy())
                dec[pos_] = AV.deciles(gg[vn].to_numpy(float))
            seg_start = int(g["T"].min())
            for H in HS:
                x = g[f"X{H}"].to_numpy(float); ok = np.isfinite(x) & (dec >= 0)
                top = ok & (dec == 9); bot = ok & (dec == 0)
                sel = top | bot
                row = {"變數": var, "L": L, "H": H, "段": sg, "n高": int(top.sum()), "n低": int(bot.sum()), "月數": int(g.loc[sel, "月"].nunique())}
                if top.sum() < 2 or bot.sum() < 2:
                    cells.append(row); continue
                Tt = g["T"].to_numpy()
                b, se = reg2(x[sel], top[sel], g["月"].to_numpy()[sel])
                blk = lambda msk: len(set(((Tt[msk] - seg_start) // H).tolist()))
                neff = int(min(min(int(top.sum()), blk(top)), min(int(bot.sum()), blk(bot))))
                fe = FAV[var]
                xf = x[ok & (dec == fe)]
                row.update({"D": b, "SE": se, "n_eff": neff, "出口": exit_of(neff), "高組X": float(x[top].mean()), "低組X": float(x[bot].mean()),
                            "看好端": "低" if fe == 0 else "高", "看好端X扣": float(xf.mean() - COST)})
                mb = []
                for m_, gg in g[ok].groupby("月", sort=True):
                    pos_ = np.searchsorted(gi, gg.index.to_numpy())
                    mb.append((x[pos_], int((dec[pos_] == 9).sum()), int((dec[pos_] == 0).sum())))
                p, fmed = fake_p(mb, b, [20260928, "SIFB".index(var), L or 0, H, list(SEGM).index(sg)])
                row["假訊號p"] = p; row["假D中位"] = fmed
                cells.append(row)
        log(f"  [{vn}] {time.time() - T0:.0f}s")
    C = pd.DataFrame(cells)
    # 可判定、Bonferroni
    C["描述"] = (C["變數"] == "B") | ((C["變數"] == "S") & (C["段"] == "早年"))
    C["可判定"] = (~C["描述"]) & C["出口"].isin(["出口②", "出口③"])
    kseg = C[C["可判定"]].groupby("段").size().to_dict()
    S["單筆層 Bonferroni k"] = {sg: int(kseg.get(sg, 0)) for sg in SEGM}
    for i, r in C.iterrows():
        if not np.isfinite(r.get("D", np.nan)):
            C.at[i, "結果"] = "—"; continue
        z = NormalDist().inv_cdf(1 - 0.025 / max(kseg.get(r["段"], 1), 1))
        C.at[i, "lo95"] = r["D"] - 1.96 * r["SE"]; C.at[i, "hi95"] = r["D"] + 1.96 * r["SE"]
        C.at[i, "loB"] = r["D"] - z * r["SE"]; C.at[i, "hiB"] = r["D"] + z * r["SE"]
        C.at[i, "z"] = z
        C.at[i, "毛結果"] = verdict(C.at[i, "loB"], C.at[i, "hiB"])
        C.at[i, "結果"] = ("描述：" if r["描述"] else "") + (verdict(C.at[i, "loB"] - COST, C.at[i, "hiB"] + COST) if r["可判定"] or r["描述"] else "出口①（不可判定）")
    # 穩
    for (var, L, sg), g in C[C["可判定"]].groupby(["變數", "L", "段"]):
        g = g.set_index("H")
        for H in g.index:
            res = g.loc[H, "結果"]
            if not res.startswith("測得出"):
                continue
            k_ = HS.index(H); nb_ = [HS[k_ + d] for d in (-1, 1) if 0 <= k_ + d < len(HS) and HS[k_ + d] in g.index]
            if nb_ and all(g.loc[h, "結果"] == res for h in nb_):
                st = "穩"
            else:
                passed = [h for h in g.index if g.loc[h, "結果"] == res]
                st = f"方向一致，但只有 {'、'.join(map(str, passed))} 天過門檻" if all(np.sign(g.loc[h, "D"]) == np.sign(g.loc[H, "D"]) for h in g.index) \
                    else f"方向不一致；只有 {'、'.join(map(str, passed))} 天過門檻"
            C.loc[(C["變數"] == var) & (C["L"] == L) & (C["段"] == sg) & (C["H"] == H), "穩不穩"] = st
    C.to_csv(os.path.join(OUT, "cells_single.csv"), index=False, float_format="%.17g")
    log(f"[單筆層] {len(C)} 格｜k {S['單筆層 Bonferroni k']}｜{time.time() - T0:.0f}s")
    # ── 組合層：主窗 ──
    from backtest import listexit_lines as LL
    ctx = LL.setup_t1(log, t1=True)
    G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    sig13 = AND[(e >= G["w0"]) & (e <= G["w1"])].copy()
    mcal_ = ctx["cal"]; mkm = ctx["mk"]
    SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), mkm, mcal_), G["w1"])
    SEGP = {sg: (int(mcal_.searchsorted(pd.Timestamp(x))), int(mcal_.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in SEG_C.items()}
    for sg, (x, y) in SEGP.items():
        assert str(mcal_[x].date()) == SEG_C[sg][0] and str(mcal_[y].date()) == SEG_C[sg][1], sg
    bench = RR.load_bench(mcal_)
    B50 = {sg: RR.bench_row(mcal_, bench, x, y + 1) for sg, (x, y) in SEGP.items()}
    S["0050 同段"] = B50
    ix_s = {s: i for i, s in enumerate(sids)}

    def flags_for(sig, world_pos_to_st):
        """每列：資料日 ＝ 進場日 − 1（接合版面位置）；母體 ＝ 進場日當時 E。"""
        out = {}
        dst = np.array([world_pos_to_st(int(p) - 1) for p in sig["entry_pos"]])
        est = dst + 1
        col = np.array([ix_s.get(s, -1) for s in sig["sid"]])
        out["資料日"] = [str(cal[d].date()) for d in dst]
        out["sid不在接合版面"] = int((col < 0).sum())
        for L in LS:
            vS = np.full(len(sig), np.nan); vI = vS.copy(); vF = vS.copy(); top = np.zeros(len(sig), bool)
            for j, (d, ee, c_) in enumerate(zip(dst, est, col)):
                k = ni.get(int(d))
                if k is None:
                    raise SystemExit(f"⛔ NEED 沒有 {cal[d].date()}")
                if c_ >= 0:
                    vS[j] = VAL[f"S{L}"][k, c_]; vI[j] = VAL[f"I{L}"][k, c_]; vF[j] = VAL[f"F{L}"][k, c_]
                row = VAL[f"S{L}"][k]
                u = E[:, ee] & np.isfinite(row)
                if not u.any() or not np.isfinite(vS[j]):
                    continue
                dq = AV.deciles(np.where(u, row, np.nan))
                if c_ >= 0 and u[c_]:
                    top[j] = dq[c_] == 9
                else:
                    top[j] = vS[j] >= row[dq == 9].min()
            out[f"S{L}"] = vS; out[f"I{L}"] = vI; out[f"F{L}"] = vF; out[f"S{L}_最高十分位"] = top
        return out

    FL = flags_for(sig13, lambda p: p + OFF)
    FLT = pd.DataFrame({k: v for k, v in FL.items() if k != "sid不在接合版面"})
    FLT.insert(0, "sid", sig13["sid"].to_numpy()); FLT.insert(1, "entry_pos", sig13["entry_pos"].to_numpy()); FLT.insert(0, "世界", "主")
    SIG = {"原版": sig13}
    fcnt = {}
    for L in LS:
        top = FL[f"S{L}_最高十分位"]; iv = FL[f"I{L}"]; fv = FL[f"F{L}"]
        mA = ~top
        mB = np.nan_to_num(iv, nan=-1.0) > 0
        mC = np.nan_to_num(iv + fv, nan=-1.0) > 0
        for vn, mm in (("甲", mA), ("乙", mB), ("丙", mC), ("丁", mA & mB)):
            SIG[f"{vn}_L{L}"] = sig13[mm]
            fcnt[f"{vn}_L{L}"] = {"保留": int(mm.sum()), "列": int(len(mm)), "S NaN": int(np.isnan(FL[f'S{L}']).sum()), "I NaN": int(np.isnan(iv).sum())}
    S["過濾計數（主）"] = fcnt; S["過濾 sid 不在接合版面（主）"] = FL["sid不在接合版面"]
    _W["主"] = {"SIG": SIG, "closes": ctx["closes"], "opens": ctx["opens"], "ncal": ctx["ncal"], "SF": SF, "SEGP": SEGP, "w0": G["w0"], "w1": G["w1"]}
    keys = list(SIG)
    t0 = time.time()
    with Pool(a.procs) as pool:
        SEED = pd.DataFrame(pool.map(run_cell, [("主", k, r) for k in keys for r in range(a.seeds)], chunksize=4))
    log(f"[組合層 主] {len(keys)} 格 × {a.seeds}｜{time.time() - t0:.0f}s")
    # 閘：原版 ＝ resultsT1fix c13 t1
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
    ref = ref[(ref["key"] == "c13") & (ref["var"] == "t1")].sort_values("r").reset_index(drop=True)
    mine = SEED[SEED["格"] == "原版"].sort_values("r").reset_index(drop=True)
    nn = min(len(ref), len(mine))
    gate = {"原版＝T1fix c13 t1（年化／回落 repr、eq_sha 不同顆數）": int(sum(repr(float(ref.loc[i, "cagr"])) != repr(float(mine.loc[i, "全窗_年化"]))
                                                                       or repr(float(ref.loc[i, "mdd"])) != repr(float(mine.loc[i, "全窗_回落"]))
                                                                       or ref.loc[i, "eq_sha"] != mine.loc[i, "eq_sha"] for i in range(nn))), "比對顆數": nn}
    gate["audit 重建持股 超出 [0, 20]"] = int(((SEED["持股最大"] > 20) | (SEED["持股最小"] < 0)).sum())
    S["閘"] = gate
    log(f"[閘 主] {gate}")
    # 各格中位
    PT = []
    for k, g in SEED.groupby("格", sort=False):
        row = {"世界": "主", "格": k, "顆數": len(g)}
        for sg in SEGP:
            c, m = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
            row.update({f"{sg}_年化": c, f"{sg}_回落": m, f"{sg}_比值": c / abs(m), f"{sg}_標籤": label(c, m, (B50[sg]["cagr"], B50[sg]["mdd"])),
                        f"{sg}_持股": float(g[f"{sg}_持股"].median()), f"{sg}_現金": float(g[f"{sg}_現金"].median())})
        row["保留筆數"] = int(len(SIG[k])); row["強制出場中位"] = float(g["強制出場"].median())
        PT.append(row)
    PT = pd.DataFrame(PT)
    PT["退化"] = (PT["格"] != "原版") & ((PT["探索_持股"] < 10) | (PT["探索_現金"] > 0.30))
    cand = PT[(PT["格"] != "原版") & ~PT["退化"]]
    if len(cand):
        pick = cand.sort_values(["探索_比值", "探索_年化"], ascending=[False, False]).iloc[0]["格"]
    else:
        pick = None
    S["退化（挑前排除）"] = PT.loc[PT["退化"], "格"].tolist()
    S["挑中格"] = pick
    log(f"[挑格] 退化 {S['退化（挑前排除）']}｜挑中 {pick}")
    # 同過濾率隨機剔除（主）
    mth = np.array([str(mcal_[p].date())[:7] for p in sig13["entry_pos"]])
    base = sig13.copy(); base["_m"] = mth
    RD = pd.DataFrame()
    if pick:
        kept = pd.Series(mth[sig13.index.isin(SIG[pick].index)]).value_counts().to_dict()
        _W["主"]["SIG"][pick + "_base"] = base; _W["主"]["KEEP"] = {pick: kept}
        t0 = time.time()
        with Pool(a.procs) as pool:
            RD = pd.DataFrame(pool.map(run_rand, [("主", pick, i) for i in range(a.reps)], chunksize=8))
        log(f"[隨機剔除 主] {a.reps} 次｜{time.time() - t0:.0f}s")
    # ── 組合層：早年 ──
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    V.body_setup("main", log)
    ecal = V._B["cal"]; ew0, ew1 = V._B["w0"], V._B["w1"]
    euni = D.load_universe().set_index("stock_id")["market"]
    ET = Y.sig_of(13, "mtm", ew0, ew1).reset_index(drop=True)
    eSF = R11.stop_force_days(R11.valid_from_data(sorted(Y._G["closes"]), euni, ecal), ew1)
    ef = int(ecal.searchsorted(pd.Timestamp(EARLY_FROM)))
    ESEGP = {"早年": (ef, ew1)}
    eb50 = RR.bench_row(ecal, RR.load_bench(ecal), ef, ew1 + 1)
    eb50_full = RR.bench_row(ecal, RR.load_bench(ecal), ew0, ew1 + 1)
    S["0050 早年"] = {"2012-08-01～2014-12-31": eb50, "2012-06-04～2014-12-31": eb50_full}
    st_pos = {d: i for i, d in enumerate(cal)}
    e2st = lambda p: st_pos[ecal[p]]
    ETf = ET[ET["entry_pos"].to_numpy() >= ef].copy()
    EFL = flags_for(ETf, e2st)
    ESIG = {"原版全窗": ET, "原版": ETf}
    efcnt = {}
    for L in LS:
        iv = EFL[f"I{L}"]; fv = EFL[f"F{L}"]
        for vn, mm in (("乙", np.nan_to_num(iv, nan=-1.0) > 0), ("丙", np.nan_to_num(iv + fv, nan=-1.0) > 0)):
            ESIG[f"{vn}_L{L}"] = ETf[mm]
            efcnt[f"{vn}_L{L}"] = {"保留": int(mm.sum()), "列": int(len(mm)), "I NaN": int(np.isnan(iv).sum())}
    S["過濾計數（早年）"] = efcnt; S["過濾 sid 不在接合版面（早年）"] = EFL["sid不在接合版面"]
    et = pd.DataFrame({k: v for k, v in EFL.items() if k != "sid不在接合版面" and not k.startswith("S")})
    et.insert(0, "sid", ETf["sid"].to_numpy()); et.insert(1, "entry_pos", ETf["entry_pos"].to_numpy()); et.insert(0, "世界", "早年")
    pd.concat([FLT, et], ignore_index=True).to_csv(os.path.join(OUT, "and_filter.csv.gz"), index=False, float_format="%.17g")
    _W["早年"] = {"SIG": ESIG, "closes": Y._G["closes"], "opens": Y._G["opens"], "ncal": Y._G["NP"], "SF": eSF, "SEGP": ESEGP, "w0": ef, "w1": ew1}
    _W["早年全"] = dict(_W["早年"], SEGP={"早年全窗": (ew0, ew1)}, w0=ew0)
    t0 = time.time()
    jobs = [("早年全", "原版全窗", r) for r in range(a.seeds)] + [("早年", k, r) for k in ESIG if k != "原版全窗" for r in range(a.seeds)]
    with Pool(a.procs) as pool:
        ESEED = pd.DataFrame(pool.map(run_cell, jobs, chunksize=4))
    log(f"[組合層 早年] {len(ESIG)} 格 × {a.seeds}｜{time.time() - t0:.0f}s")
    eref = pd.read_csv("backtest/resultsYLretest/b2_early_seeds.csv", float_precision="round_trip")
    eref = eref[eref["key"] == "main|開|N20|H60"].sort_values("r").reset_index(drop=True)
    em = ESEED[ESEED["格"] == "原版全窗"].sort_values("r").reset_index(drop=True)
    nn = min(len(eref), len(em))
    gate["早年原版全窗＝YLretest b2e main|開|N20|H60（年化／回落 repr 不同顆數）"] = int(sum(repr(float(eref.loc[i, "cagr"])) != repr(float(em.loc[i, "早年全窗_年化"]))
                                                                                  or repr(float(eref.loc[i, "mdd"])) != repr(float(em.loc[i, "早年全窗_回落"])) for i in range(nn)))
    gate["早年比對顆數"] = nn
    log(f"[閘 早年] {gate}")
    EPT = []
    for k, g in ESEED[ESEED["格"] != "原版全窗"].groupby("格", sort=False):
        c, m = float(g["早年_年化"].median()), float(g["早年_回落"].median())
        EPT.append({"世界": "早年", "格": k, "顆數": len(g), "早年_年化": c, "早年_回落": m, "早年_比值": c / abs(m),
                    "早年_標籤": label(c, m, (eb50["cagr"], eb50["mdd"])), "早年_持股": float(g["早年_持股"].median()),
                    "早年_現金": float(g["早年_現金"].median()), "保留筆數": int(len(ESIG[k]))})
    EPT = pd.DataFrame(EPT)
    ERD = pd.DataFrame()
    if pick and pick[0] in "乙丙" and pick in ESIG:
        emth = np.array([str(ecal[p].date())[:7] for p in ETf["entry_pos"]])
        ebase = ETf.copy(); ebase["_m"] = emth
        ekept = pd.Series(emth[ETf.index.isin(ESIG[pick].index)]).value_counts().to_dict()
        _W["早年"]["SIG"][pick + "_base"] = ebase; _W["早年"]["KEEP"] = {pick: ekept}
        with Pool(a.procs) as pool:
            ERD = pd.DataFrame(pool.map(run_rand, [("早年", pick, i) for i in range(a.reps)], chunksize=8))
    # ── 判定 ──
    SEED.to_csv(os.path.join(OUT, "seeds_main.csv.gz"), index=False, float_format="%.17g")
    ESEED.to_csv(os.path.join(OUT, "seeds_early.csv.gz"), index=False, float_format="%.17g")
    if len(RD):
        RD.to_csv(os.path.join(OUT, "rand_main.csv.gz"), index=False, float_format="%.17g")
    if len(ERD):
        ERD.to_csv(os.path.join(OUT, "rand_early.csv.gz"), index=False, float_format="%.17g")
    PT.to_csv(os.path.join(OUT, "cells_combo.csv"), index=False, float_format="%.17g")
    EPT.to_csv(os.path.join(OUT, "cells_combo_early.csv"), index=False, float_format="%.17g")
    J = {}
    if pick:
        pr = PT.set_index("格").loc[pick]; po = PT.set_index("格").loc["原版"]
        J["確認"] = {"年化": pr["確認_年化"], "回落": pr["確認_回落"], "標籤": pr["確認_標籤"], "原版年化": po["確認_年化"], "原版標籤": po["確認_標籤"],
                   "0050": B50["確認"]["cagr"], "隨機剔除p（年化）": float(np.mean(RD["確認_年化"] >= pr["確認_年化"])) if len(RD) else None,
                   "隨機剔除年化中位": float(RD["確認_年化"].median()) if len(RD) else None}
        J["探索"] = {"年化": pr["探索_年化"], "回落": pr["探索_回落"], "標籤": pr["探索_標籤"], "原版年化": po["探索_年化"],
                   "隨機剔除p（年化）": float(np.mean(RD["探索_年化"] >= pr["探索_年化"])) if len(RD) else None}
        if pick in ESIG:
            er = EPT.set_index("格").loc[pick]; eo = EPT.set_index("格").loc["原版"]
            J["早年"] = {"年化": er["早年_年化"], "回落": er["早年_回落"], "標籤": er["早年_標籤"], "原版年化": eo["早年_年化"], "0050": eb50["cagr"],
                       "隨機剔除p（年化）": float(np.mean(ERD["早年_年化"] >= er["早年_年化"])) if len(ERD) else None}
        else:
            J["早年"] = {"標籤": "不可判定（挑中格要借券；借券 2015 起）"}
        labs = [J["確認"]["標籤"]] + ([J["早年"]["標籤"]] if pick in ESIG else [])
        order = {"不合格": 0, "另列": 1, "合格": 2}
        J["件標籤"] = min(labs, key=lambda x: order[x])
    S["組合層判定"] = J
    # ── 新規矩 ③ ──
    trig = bool(pick) and (J["確認"]["標籤"] in ("合格", "另列") or (pick in ESIG and J["早年"]["標籤"] in ("合格", "另列")))
    S["新規矩③"] = "要跑" if trig else "不適用（挑中格確認、早年皆非合格／另列）"
    if trig:
        VAR = {"SL10": {"stop": ("fix", 0.10)}, "SL20": {"stop": ("fix", 0.20)}, "TP30h": {"trim_rule": {"kind": "gain", "x": 0.30, "frac": 0.5}},
               "TP50h": {"trim_rule": {"kind": "gain", "x": 0.50, "frac": 0.5}}, "AT2": {}, "R0-40": {}, "N10": {"nslot": 10}, "N30": {"nslot": 30}}
        SENS = {}
        worlds = [("主", MAIN)] + ([("早年", None)] if pick in ESIG else [])
        for wn, data_dir in worlds:
            if wn == "主":
                D.DATA = MAIN; SV, cv = exit_variants(_W["主"], _W["主"]["SIG"][pick], mcal_, mkm)
            else:
                V.use_layout("main"); SV, cv = exit_variants(_W["早年"], _W["早年"]["SIG"][pick], ecal, euni)
            _W[wn].update(VAR=VAR, SIGV=SV, PICK=pick)
            with Pool(a.procs) as pool:
                SR = pd.DataFrame(pool.map(run_sens, [(wn, v, r) for v in VAR for r in range(a.seeds)], chunksize=4))
            SR.to_csv(os.path.join(OUT, f"sens_{'main' if wn == '主' else 'early'}.csv.gz"), index=False, float_format="%.17g")
            segs = list(_W[wn]["SEGP"])
            ref_ = (PT if wn == "主" else EPT).set_index("格").loc[pick]
            out = {"提前出場筆數": cv, "原格": {sg: [float(ref_[f"{sg}_年化"]), float(ref_[f"{sg}_回落"])] for sg in segs}}
            for v, g in SR.groupby("變體", sort=False):
                out[v] = {sg: [float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())] for sg in segs}
            SENS[wn] = out
            log(f"[新規矩③ {wn}] {out}")
        S["新規矩③ 出場敏感度（描述、不判；各段 [年化中位, 回落中位]）"] = {"定義": "SL10／SL20 收盤 ≤ 進場價×0.9／×0.8 當日收盤出場（simulate_mtm stop fix）；TP30h／TP50h 收盤[t−1] ≥ 進場價×1.3／×1.5 ⇒ t 開盤賣半一次（trim_rule gain）；"
                                                                  "AT2 進場以來最高收盤 − 2×ATR14（Wilder、前一日值）⇒ 收盤 ≤ 線當日收盤出場；R0-40 第 40 根有效 K 棒收盤 ≤ 進場價 ⇒ 當日收盤出場；N10／N30 檔數", **SENS}
    S["秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    bad = gate["原版＝T1fix c13 t1（年化／回落 repr、eq_sha 不同顆數）"] or gate["早年原版全窗＝YLretest b2e main|開|N20|H60（年化／回落 repr 不同顆數）"] \
        or gate["audit 重建持股 超出 [0, 20]"]
    report()
    log(f"[完] {S['秒']}s｜閘 {'不過' if bad else '過'}")
    if bad:
        raise SystemExit("⛔ 閘不過")


if __name__ == "__main__":
    main()
