# -*- coding: utf-8 -*-
"""PREREG一般出場法 第二輪 seq6（台股策略線登錄 sha 484b78603a696fbd，2026-10-20 01:38；裁定 seq382 發號、N_前段 ＋28；seq1～5 作廢）——回測線計算子代理。
隨便買 × 常見七類出場 × 三刀情況（強／弱、波動大／小、0050 在 200 日線上／下），純單筆、基準抱 120 天（60、250 只描述）。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExitGen.py fixture|dry|body|report [--procs 4]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExitGen_check.py

═══ 重用（⛔ 不另寫一份）═══
  researchQuad（PREREG四類單獨 9/27）：stock_data（RA.prep 還原價、可成交、硬斷點 cs_pb／cs_g5、Wilder 14 ATR、fsum 均線）、first_trig（SL10／AT3／TP50／MA50）、
  exec_day、COST 0.585%、ci 用 exit_signal.cr0（進場月分群 CR0）與 exit_result（n_eff ＜ 30 ⇒ 出口①）；research11.regime_below（0050 MA200）；
  research34.load_revenue／rebalance_dates（月營收、可用日）
═══ 讀法（★ ＝ 本線定；登錄沒寫死的都在這裡；寫死前 ⛔ 沒算任何本件報酬）═══
 ★R1 底：同 9/27——母體 W1 eligible（resultsp4/panel.csv.gz）∩ gate3；量測日 T ＝ 每月第一個交易日收盤判、e ＝ T＋1 開盤進場；P0 ＝ 還原 open(e)；
     e 開盤漲停／停牌不建；x ＝ e＋H−1（抱 H 根交易日曆）、x 沒成交 ⇒ x 以前最後一根有效收盤；[e, x] 有硬斷點（D.breakpoints 價格規則 ∪ 缺口 ≥5 日，seq335）⇒ 剔除
 ★R2 段：探索 e ≥ 2017-03-02 且 x ≤ 2021-12-30；確認 e ≥ 2022-01-03 且 x ≤ 資料尾（快照 edc6f8002f 日曆尾 2026-09-24；9/27 用 2026-08-24 窗尾，本件照登錄字面「資料尾」）；
     量測日 ≤ 2026-03-02 用 resultsp4 面板，之後用 resultsp9_engine/panel_ext（稽核 ②2 前例）；只收整筆落在段內（每個 H 各自判）
     早年 2005～2014 只描述：~/earlydata/950ad26e12/reduce_v2（seq341 v2：還原鏈含減資，只上市）＋ 早年面板 3edc0e2206/sig_main（只上市）；
     早年沒有個股法人 ⇒ W1 eligible 做不到 ⇒ 早年母體 ＝ liq_ok ∧ bars_ok（researchMomX R10 前例）∩ gate3；e ≥ 2005 第一個交易日、x ≤ 2014-12-31
 R3 出場（收盤判 d、d 之後第一個可賣開盤 s 全賣；判定日 d ∈ [e, x−1]；s ≥ x ⇒ 不做）：
     X1 ＝ 9/27 SL10（收盤 ≤ P0×90/100）｜X2 ＝ 9/27 AT3（★ 照「沿用 9/27 定義」：線 ＝ 起點 P0−3×ATR(e 前一根)、之後嚴格新高收盤才上調、收盤 ＜ 線；登錄寫 ≤，差在恰好相等）
     X3 ＝ 9/27 TP50（收盤 ≥ P0×150/100）
     X4 ＝ 0050 還原收盤（ffill）由 MA200 上（含等於）跌到線下的那一天 d（below200[d] ∧ ¬below200[d−1] ∧ 前一天 MA 有值）；站回不買回
     X5 ＝ 進場日算第 1 根有效 K 棒，第 20 根有效 K 棒 d 收盤 ≤ P0（★ 報酬 ≤ 0 ＝ 還原收盤 ÷ 進場價 − 1 ≤ 0，⛔ 不含成本）；只判這一次
     X6 ＝ 有效 K 棒 d：收盤 ＜ MA50 且前一根有效 K 棒收盤 ≥ 其 MA50（★ d ＝ e 時前一根是 e 之前的 K 棒：買進當天收盤就跌穿也算持有中穿越）
     X7 ＝ 依可用日排序的月營收公布序列：本期年增 ＜ 0 且前一次公布（有營收的前一期）年增 ≥ 0（兩者都可算才判；年增 ＝ 當月 ÷ 去年當月 − 1，去年當月 ＞ 0）；
         可用日 A ＝ 期別次月 10 日（≤ 2025-12）／15 日（≥ 2026-01）之後第一個交易日（seq304，research34.rebalance_dates side=right）；
         持有中新公布 ＝ A ∈ [e, x−1]；d ＝ A（可用日收盤知道）⇒ s ＝ A 之後第一個可賣開盤
 ★R4 三刀（T ＝ e−1 量測日收盤可知；中位 ＝ 當月全部候選（eligible∩gate3，不看進場日能否成交、不看持有期斷點）有值者的中位）：
     S1 ＝ c[lv(T−21)] ÷ c[lv(T−252)] − 1（日曆位置、最後有效收盤）；T−252 ＜ 0、取不到、或 [lv(T−252), T] 有硬斷點 ⇒ 無值（不進這一刀）
     S2 ＝ 相鄰有效 K 棒日報酬、後一根落在 [T−59, T] 者的標準差（ddof＝1）；＜ 40 個或窗內有硬斷點 ⇒ 無值
     S3 ＝ 0050 還原收盤 ≥ MA200（T 當天；MA 無值 ⇒ 無值）
     ≥ 中位 ⇒ 強／大；其餘 ⇒ 弱／小
 R5 報酬：基準 ＝ c[j]/P0 − 1 − 0.585%；出場 ＝ o[s]/P0 − 1 − 0.585%；賣掉後到原出場日記 0；d ＝ 出場 − 基準（沒觸發 ⇒ 0）
     滑價另報：買 ×1.005、賣 ×0.995（兩邊同式）；★ 同根兩出場價：每臂只有一種出場、一律收盤判隔日開盤賣 ⇒ 不會有同根兩價（seq373 不適用，照寫）
 R6 判定（H＝120、探索與確認）：整體 7 格 ＝ d 平均；交互 21 格 ＝ 同一出場刀兩邊 d 平均之差（強−弱、大−小、多頭−空頭），
     SE ＝ 二組指標迴歸係數的進場月分群 CR0（＝ Σ_g（Σ_A (d−m_A)/n_A − Σ_B (d−m_B)/n_B）²，與 exit_signal.cr0 同為無小樣本修正）；
     CI ＝ ±z，z ＝ Φ⁻¹(1 − 0.05/28/2)（雙尾 99.82%）；★ n_eff ＝ min(n, 月數)（交互取兩邊較小）＜ 30 ⇒ 該段分不出（exit_result 出口①）
     每段 ＞0 且不含 0 ⇒ 正｜＜0 且不含 0 ⇒ 負｜其餘分不出；兩段同號且都不含 0 ⇒ 成立
 ★R7 描述：成本／年 ＝ 0.585% × 245 ÷ 平均持有天數（若每次賣掉就換一筆的年化成本；本件單筆、每筆固定一次 0.585%）；持有天數 ＝ s − e（觸發）或 H
     每筆回落 ＝ 持股價值路徑（P0 起、有效 K 棒收盤、賣出那天以開盤價結束）的最大回落；先驗④ 用確認段 X4 對基準的平均每筆回落
輸出 backtest/resultsExitGen/：dry/（階段一，⛔ 不含報酬）、fixture.json、rows_{main,early}.csv.gz、cells.csv、verdict.json、summary.json、REPORT.md、run.log
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

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchQuad as Q                                   # ⭐ 9/27 框架（import 時 researchH2 把 D.DATA 指到快照 edc6f）
from backtest import avgdown as AV
from backtest import research11 as R11
from backtest import research34 as R34
from backtest import universe_gate as UG
from backtest import exit_signal as XS

D, RA = Q.D, Q.RA
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsExitGen")
DRY = os.path.join(OUT, "dry")
COST = Q.COST
SLIP = 0.005
HS = (60, 120, 250)
HJ = 120
EXITS = ["X1", "X2", "X3", "X4", "X5", "X6", "X7"]
ENAME = {"X1": "固定 −10% 停損", "X2": "3×ATR 追蹤停損", "X3": "漲 +50% 全賣", "X4": "0050 跌穿 200 日線全賣", "X5": "第 20 日報酬 ≤0 全賣（時間停損）",
         "X6": "個股跌穿 50 日線全賣", "X7": "月營收年增轉負全賣"}
CUTS = {"S1": ("強", "弱"), "S2": ("大", "小"), "S3": ("多頭", "空頭")}
CNAME = {"S1": "過去一年強／弱", "S2": "60 日波動大／小", "S3": "0050 在 200 日線上／下"}
PANEL_EXT = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
EARLY_DATA = os.path.expanduser("~/earlydata/950ad26e12/reduce_v2/data")
EARLY_PANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
SEGW = {"main": {"explore": ("2017-03-02", "2021-12-30"), "confirm": ("2022-01-03", None)},
        "early": {"early": ("2005-01-01", "2014-12-31")}}
ZB = NormalDist().inv_cdf(1 - 0.05 / 28 / 2)
MUST = ["隨便買的平均，不是對某一檔的預測", "情況在買進當下判，持有中不換邊", "單筆比較、沒算賣掉的錢再拿去做什麼"]
EARLY_NOTE = "早年含減資假飆股約 0.3%（剩 22 筆未解釋）；早年只上市、母體 liq_ok∧bars_ok（無個股法人）"
_W: dict = {}


# ═════════════════════════════ 出場觸發（單筆；fixture 與正式共用）
def cross_ma(S):
    """X6：有效 K 棒 d 收盤 ＜ MA50 且前一根有效 K 棒收盤 ≥ 其 MA50 ⇒ True（日曆位置）。"""
    c, v, ma, pb = S["c"], S["valid"], S["ma50"], S["prevbar"]
    n = len(c)
    with np.errstate(invalid="ignore"):
        below = v & np.isfinite(ma) & (c < ma)
        above = v & np.isfinite(ma) & (c >= ma)
    out = np.zeros(n, bool)
    idx = np.flatnonzero(below & (pb >= 0))
    out[idx] = above[pb[idx]]
    return out


def cross_mkt(c50ff, n=200):
    """X4：0050 收盤由 MA200 上（含等於）跌到線下那一天；前一天 MA 要有值。另回 ma 與 below。"""
    b = np.asarray(c50ff, float)
    ma = pd.Series(b).rolling(n).mean().to_numpy()
    below = R11.regime_below(b, n)
    out = np.zeros(len(b), bool)
    out[1:] = below[1:] & ~below[:-1] & np.isfinite(ma[:-1])
    return out, ma, below


def rev_turns(sid, rev, rly, A):
    """X7：依可用日排序 ⇒ (轉負的可用日陣列, 有營收列數)。A：period → 可用日日曆位置。"""
    if rev is None or sid not in rev.columns:
        return np.zeros(0, int), 0
    rv = rev[sid].to_numpy(float); rl = rly[sid].to_numpy(float); per = list(rev.index)
    ev = []
    for k, p in enumerate(per):
        if not np.isfinite(rv[k]) or p not in A:
            continue
        yoy = rv[k] / rl[k] - 1.0 if (np.isfinite(rl[k]) and rl[k] > 0) else np.nan
        ev.append((A[p], yoy))
    ev.sort(key=lambda z: z[0])
    turns = [ev[i][0] for i in range(1, len(ev)) if np.isfinite(ev[i][1]) and np.isfinite(ev[i - 1][1]) and ev[i][1] < 0 <= ev[i - 1][1]]
    return np.asarray(turns, int), len(ev)


def trig_all(S, e, x, P0, x4, x6, turns):
    """⇒ {code: (d, s)}；d ＝ 第一個成立判定日（−1 沒有）、s ＝ 成交日（−1 不做）。"""
    out = {}
    for code, q in (("X1", "SL10"), ("X2", "AT3"), ("X3", "TP50")):
        out[code] = Q.first_trig(q, S, e, x, P0)
    w = np.flatnonzero(x4[e:x]); out["X4"] = int(e + w[0]) if len(w) else -1
    b = S["bars"]; i0 = int(np.searchsorted(b, e))
    d5 = int(b[i0 + 19]) if i0 + 19 < len(b) else -1
    out["X5"] = d5 if (0 <= d5 < x and S["valid"][d5] and S["c"][d5] <= P0) else -1
    w = np.flatnonzero(x6[e:x]); out["X6"] = int(e + w[0]) if len(w) else -1
    w = turns[(turns >= e) & (turns < x)]; out["X7"] = int(w.min()) if len(w) else -1
    return {k: (d, Q.exec_day(S, d, "sell", x) if d >= 0 else -1) for k, d in out.items()}


def trade_mdd(S, e, end_close, P0, s_open=None):
    """持股價值路徑最大回落：P0 起、[e, end_close] 有效 K 棒收盤；s_open ⇒ 最後以 o[s] 結束。"""
    c, v = S["c"], S["valid"]
    seg = c[e:end_close + 1][v[e:end_close + 1]] / P0 if end_close >= e else np.zeros(0)
    path = np.r_[1.0, seg, [S["o"][s_open] / P0] if s_open is not None else []]
    return float((path / np.maximum.accumulate(path) - 1.0).min())


# ═════════════════════════════ 每檔
def cut_vals(S, T):
    c, lv = S["c"], S["lv"]
    mom = vol = np.nan
    if T - 252 >= 0:
        ia, ib = int(lv[T - 252]), int(lv[T - 21])
        if ia >= 0 and ib >= 0 and not bool(AV.brk_vec(S["cs_pb"], S["cs_g5"], ia, T)[0]):
            mom = float(c[ib] / c[ia] - 1.0)
    b = S["bars"]
    k1 = int(np.searchsorted(b, T, side="right"))            # b[:k1] ≤ T
    k0 = int(np.searchsorted(b, T - 59))                      # b[k0:] ≥ T−59
    if k0 >= 1 and k1 - k0 >= 40:
        bb = b[k0 - 1:k1]
        if not bool(AV.brk_vec(S["cs_pb"], S["cs_g5"], int(bb[0]), T)[0]):
            r = c[bb[1:]] / c[bb[:-1]] - 1.0
            vol = float(np.std(r, ddof=1))
    return mom, vol


def work(args):
    sid, market, es, mode = args
    cal = Q._G["cal"]; n = len(cal)
    S = Q.stock_data(sid, market)
    if S is None:
        return [{"sid": sid, "market": market, "e": int(e), "status": "無資料"} for e in es]
    x4, rev, rly, A = _W["x4"], _W["rev"], _W["rly"], _W["A"]
    x6 = cross_ma(S)
    turns, nrev = rev_turns(sid, rev, rly, A)
    out = []
    for e in es:
        e = int(e)
        r = {"sid": sid, "market": market, "e": e, "status": "ok", "nrev": nrev}
        r["mom"], r["vol"] = cut_vals(S, e - 1)
        P0 = float(S["o"][e]) if e < n else np.nan
        r["na_atr"] = int(not np.isfinite(S["atr_cal"][max(S["prevbar"][e], 0)])) if e < n else 1
        for H in HS:
            x = e + H - 1
            if x >= n:
                r[f"st{H}"] = "超出日曆"; continue
            if not S["ok_buy"][e]:
                r[f"st{H}"] = "進場日漲停或停牌"; continue
            if bool(AV.brk_vec(S["cs_pb"], S["cs_g5"], e, x)[0]):
                r[f"st{H}"] = "硬斷點"; continue
            r[f"st{H}"] = "保留"
            tg = trig_all(S, e, x, P0, x4, x6, turns)
            for k, (d, s) in tg.items():
                r[f"d{k}_{H}"] = d; r[f"s{k}_{H}"] = s
            w = turns[(turns >= e) & (turns < x)]; r[f"nturn{H}"] = int(len(w))
            if H == HJ:                                         # 9/27「跌破 50 日線」（狀態）對照：只看觸發
                dm = Q.first_trig("MA50", S, e, x, P0)
                r["sMA50state"] = Q.exec_day(S, dm, "sell", x) if dm >= 0 else -1
                r["dMA50state"] = dm
            if mode == "body":                                  # ⛔ dry 不算任何報酬
                j = int(S["lv"][x]); cj = float(S["c"][j]); o = S["o"]
                base = cj / P0 - 1.0 - COST
                bsl = cj * (1 - SLIP) / (P0 * (1 + SLIP)) - 1.0 - COST
                r[f"base{H}"] = base; r[f"bsl{H}"] = bsl
                if H == HJ:
                    r["mdd_base"] = trade_mdd(S, e, x, P0)
                for k, (d, s) in tg.items():
                    if s >= 0:
                        ret = float(o[s] / P0 - 1.0 - COST)
                        r[f"r{k}_{H}"] = ret; r[f"D{k}_{H}"] = ret - base
                        r[f"Dsl{k}_{H}"] = float(o[s] * (1 - SLIP) / (P0 * (1 + SLIP)) - 1.0 - COST) - bsl
                        if H == HJ:
                            r[f"mdd{k}"] = trade_mdd(S, e, s - 1, P0, s)
                    else:
                        r[f"D{k}_{H}"] = 0.0; r[f"Dsl{k}_{H}"] = 0.0
                        if H == HJ:
                            r[f"mdd{k}"] = r["mdd_base"]
        out.append(r)
    return out


def _init(cal, off, b60, b200, x4, rev, rly, A):
    Q._init(cal, off, b60, b200)
    _W.update(x4=x4, rev=rev, rly=rly, A=A)


# ═════════════════════════════ 世界
def avail_map(periods, cal):
    a10 = R34.rebalance_dates([p for p in periods if p <= "2025-12"], cal, pub_day=10)
    a15 = R34.rebalance_dates([p for p in periods if p >= "2026-01"], cal, pub_day=15)
    return {p: v[1] for p, v in {**a10, **a15}.items()}


def setup(world, log):
    if world == "main":
        D.DATA = Q.RA.H2.H2D
        cal = D.load_calendar()
        from backtest import p4_features as P4F
        p = P4F.read_panel(os.path.join(HERE, "resultsp4", "panel.csv.gz"))
        cut = p["measure_date"].max()
        pe = pd.read_csv(PANEL_EXT, dtype={"stock_id": str}, parse_dates=["measure_date"], usecols=["measure_date", "stock_id", "eligible"])
        pe = pe[pe["measure_date"] > cut]
        p = pd.concat([p[["measure_date", "stock_id", "eligible"]], pe], ignore_index=True)
        p = p[p["eligible"].astype(str).isin(["True", "1", "1.0"])]
        U = RA.load_universe(None)
        mk = U.set_index("stock_id")["market"]
        p = p[p["stock_id"].isin(set(U["stock_id"]))].copy()
        info_src = {"面板": "resultsp4/panel.csv.gz（≤ " + str(cut.date()) + "）＋ panel_ext（之後）", "量測日上限": str(p["measure_date"].max().date())}
    else:
        D.DATA = EARLY_DATA
        cal = D.load_calendar()
        p = pd.read_csv(EARLY_PANEL, dtype={"stock_id": str}, parse_dates=["measure_date"], usecols=["measure_date", "stock_id", "liq_ok", "bars_ok"])
        p = p[p["liq_ok"].astype(str).isin(["True", "1"]) & p["bars_ok"].astype(str).isin(["True", "1"])]
        stocks = pd.read_csv(os.path.join(EARLY_DATA, "meta", "stocks.csv"), dtype=str)
        U = UG.gate3(stocks)
        p = p[p["stock_id"].isin(set(U["stock_id"]))].copy()
        mk = pd.Series("twse", index=sorted(set(p["stock_id"])))
        info_src = {"面板": EARLY_PANEL + "（liq_ok∧bars_ok）", "版面": EARLY_DATA}
    pos = {d: i for i, d in enumerate(cal)}
    p["T"] = p["measure_date"].map(pos)
    off_cal = int(p["T"].isna().sum())
    p = p[p["T"].notna()].copy(); p["T"] = p["T"].astype(int); p["e"] = p["T"] + 1
    lo = int(cal.searchsorted(pd.Timestamp(min(v[0] for v in SEGW[world].values()))))
    p = p[(p["e"] >= lo) & (p["e"] < len(cal))]
    p = p.drop_duplicates(["stock_id", "e"])
    s50 = D.load_stock("0050", "twse", cal).df
    c50ff = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy()
    x4, ma200, below200 = cross_mkt(c50ff)
    rev, rly, _ind = R34.load_revenue()
    A = avail_map(list(rev.index), cal)
    tail = str(cal[-1].date())
    segs = {}
    for sg, (a, b) in SEGW[world].items():
        segs[sg] = (int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b or tail), side="right") - 1))
    info = {**info_src, "DATA": D.DATA, "日曆": [str(cal[0].date()), tail], "候選列（e 在範圍內）": int(len(p)), "量測日不在日曆": off_cal,
            "段（日曆位置）": {k: [int(v[0]), int(v[1]), str(cal[v[0]].date()), str(cal[v[1]].date())] for k, v in segs.items()},
            "月營收期別": [str(rev.index[0]), str(rev.index[-1])], "股數": int(p["stock_id"].nunique())}
    log(f"[世界 {world}] {json.dumps(info, ensure_ascii=False)}")
    return dict(world=world, cal=cal, p=p, mk=mk, c50ff=c50ff, x4=x4, ma200=ma200, below200=below200, rev=rev, rly=rly, A=A, segs=segs, info=info)


def run_pool(Wd, mode, procs, limit=None):
    cal = Wd["cal"]; p = Wd["p"]
    if limit:
        p = p[p["stock_id"].isin(sorted(p["stock_id"].unique())[:limit])]
    off = RA.TR.load_official()
    b60 = R11.regime_below(Wd["c50ff"], 60)
    tasks = [(sid, Wd["mk"].get(sid, "twse"), sorted(g["e"].astype(int)), mode) for sid, g in p.groupby("stock_id")]
    rows = []
    with Pool(procs, initializer=_init, initargs=(cal, off, b60, Wd["below200"], Wd["x4"], Wd["rev"], Wd["rly"], Wd["A"])) as pool:
        for r in pool.imap_unordered(work, tasks, chunksize=8):
            rows += r
    K = pd.DataFrame(rows).sort_values(["sid", "e"]).reset_index(drop=True)
    # 三刀（當月中位；全部候選有值者）
    K["T"] = K["e"] - 1
    K["mon"] = K["e"].map(lambda t: str(cal[t])[:7])
    for col, cut in (("mom", "S1"), ("vol", "S2")):
        med = K.groupby("T")[col].transform("median")
        K[cut] = np.where(K[col].notna() & med.notna(), np.where(K[col] >= med, 1, 0), -1)
    ma = Wd["ma200"]; cf = Wd["c50ff"]; T = K["T"].to_numpy()
    K["S3"] = np.where(np.isfinite(ma[T]), np.where(cf[T] >= ma[T], 1, 0), -1)
    # 段（每個 H 各自）
    for H in HS:
        K[f"seg{H}"] = ""
        for sg, (a, b) in Wd["segs"].items():
            sel = (K["e"] >= a) & (K["e"] + H - 1 <= b)
            K.loc[sel, f"seg{H}"] = sg
    return K


# ═════════════════════════════ 統計
def ci_mean(d, mon, z=1.96):
    d = np.asarray(d, float); n = len(d)
    if n == 0:
        return {"mean": np.nan, "se": np.nan, "lo": np.nan, "hi": np.nan, "n": 0, "月數": 0, "n_eff": 0}
    m, se, ng = XS.cr0(d, mon)
    return {"mean": m, "se": se, "lo": m - z * se, "hi": m + z * se, "n": n, "月數": int(ng), "n_eff": int(min(n, ng))}


def ci_diff(d, side, mon, z=1.96):
    """兩組平均之差（side＝1 − side＝0）的進場月分群 CR0（＝ 指標迴歸係數）。"""
    d = np.asarray(d, float); side = np.asarray(side, int); mon = np.asarray(mon)
    A, B = side == 1, side == 0
    nA, nB = int(A.sum()), int(B.sum())
    if nA == 0 or nB == 0:
        return {"diff": np.nan, "se": np.nan, "lo": np.nan, "hi": np.nan, "nA": nA, "nB": nB, "月A": 0, "月B": 0, "n_eff": 0, "mA": np.nan, "mB": np.nan}
    mA, mB = float(d[A].mean()), float(d[B].mean())
    psi = np.where(A, (d - mA) / nA, 0.0) - np.where(B, (d - mB) / nB, 0.0)
    keys, inv = np.unique(mon, return_inverse=True)
    s = np.zeros(len(keys)); np.add.at(s, inv, psi)
    se = float(np.sqrt((s ** 2).sum()))
    gA, gB = len(np.unique(mon[A])), len(np.unique(mon[B]))
    return {"diff": mA - mB, "se": se, "lo": mA - mB - z * se, "hi": mA - mB + z * se, "nA": nA, "nB": nB, "月A": gA, "月B": gB,
            "n_eff": int(min(nA, nB, gA, gB)), "mA": mA, "mB": mB}


def sign_of(est, lo, hi, n_eff):
    if not np.isfinite(est):
        return "分不出"
    if n_eff < 30:
        return "分不出（n_eff＜30）"
    if lo > 0:
        return "正"
    if hi < 0:
        return "負"
    return "分不出"


# ═════════════════════════════ fixture（合成序列；⛔ 不讀任何真實資料）
def synth_S(c, o=None, h=None, l=None):
    c = np.asarray(c, float); n = len(c)
    o = c.copy() if o is None else np.asarray(o, float)
    h = np.maximum(o, c) * 1.01 if h is None else np.asarray(h, float)
    l = np.minimum(o, c) * 0.99 if l is None else np.asarray(l, float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    S = {"o": o, "c": c, "valid": valid, "bars": bars, "lv": np.asarray(AV.last_valid(valid), int)}
    prevbar = np.full(n, -1, int)
    for i in range(1, len(bars)):
        prevbar[bars[i]] = bars[i - 1]
    S["prevbar"] = prevbar
    atr = np.full(n, np.nan); atr[bars] = R11.wilder_atr(h[bars], l[bars], c[bars]); S["atr_cal"] = atr
    ma50 = np.full(n, np.nan); ma50[bars] = Q.ma_exact(c, bars, 50); S["ma50"] = ma50
    ma20 = np.full(n, np.nan); ma20[bars] = Q.ma_exact(c, bars, 20); S["ma20"] = ma20
    trd = valid.copy(); z = np.zeros(n, bool)
    S["ok_sell"] = AV.trade_ok(trd, z, o); S["ok_buy"] = AV.trade_ok(trd, z, o)
    S["nxt_sell"] = AV.next_true(S["ok_sell"]); S["nxt_buy"] = AV.next_true(S["ok_buy"])
    S["cs_pb"] = np.zeros(n, np.int32); S["cs_g5"] = np.zeros(n, np.int32)
    return S


def fixture(log):
    res = {"單元": [], "兩兩不蘊含": {}}
    ok_all = True

    def chk(name, got, want):
        nonlocal ok_all
        ok = got == want; ok_all &= ok
        res["單元"].append({"名": name, "得": got, "應": want, "過": ok}); log(f"  [fixture] {'✔' if ok else '✘'} {name}：得 {got}、應 {want}")

    n = 400; e = 300; H = 60; x = e + H - 1
    base = np.r_[np.linspace(50, 100, e), np.full(n - e, 100.0)]     # 進場前一路漲 ⇒ 在 MA50 上
    c50 = np.r_[np.linspace(50, 100, n)]                             # 0050 一路漲 ⇒ 不跌穿
    x4_none, _, _ = cross_mkt(c50)
    no_turn = np.zeros(0, int)
    # X1：第 e+5 根收盤 90 ⇒ d＝e+5、s＝e+6
    c = base.copy(); c[e + 5:] = 90.0; S = synth_S(c)
    chk("X1 收盤恰 = P0×0.9 觸發（≤）", trig_all(S, e, x, 100.0, x4_none, cross_ma(S), no_turn)["X1"], (e + 5, e + 6))
    # X3：收盤 150 ⇒ 觸發
    c = base.copy(); c[e + 7:] = 150.0; S = synth_S(c)
    chk("X3 收盤恰 = P0×1.5 觸發（≥）", trig_all(S, e, x, 100.0, x4_none, cross_ma(S), no_turn)["X3"], (e + 7, e + 8))
    # X5：第 20 根收盤 ≤ P0 才觸發、只判一次（第 21 根以後再低也不賣）
    c = base.copy(); c[e + 19] = 100.0; S = synth_S(c)
    chk("X5 第 20 根收盤 = P0 觸發", trig_all(S, e, x, 100.0, x4_none, cross_ma(S), no_turn)["X5"], (e + 19, e + 20))
    c = base.copy(); c[e + 19] = 100.5; c[e + 20:] = 70.0; S = synth_S(c)
    chk("X5 第 20 根 ＞ P0、之後大跌也不賣（只判一次）", trig_all(S, e, x, 100.0, x4_none, cross_ma(S), no_turn)["X5"][0], -1)
    c = base.copy(); c[e + 3] = np.nan; c[e + 20] = 99.0; S = synth_S(c)
    chk("X5 數有效 K 棒（中間停一天 ⇒ 第 20 根在 e+20）", trig_all(S, e, x, 100.0, x4_none, cross_ma(S), no_turn)["X5"][0], e + 20)
    # X6：穿越 vs 狀態
    c = base.copy(); c[e - 1] = 70.0; c[e:] = 70.0; S = synth_S(c)        # 進場前一天已在線下 ⇒ 狀態式 d＝e、穿越式不觸發（要先站上）
    chk("X6 進場時已在 MA50 下 ⇒ 穿越式不觸發", trig_all(S, e, x, 70.0, x4_none, cross_ma(S), no_turn)["X6"][0], -1)
    chk("9/27 MA50 狀態式 ⇒ 第一根就觸發（對照）", Q.first_trig("MA50", S, e, x, 70.0), e)
    c2 = c.copy(); c2[e + 10:e + 15] = 200.0; c2[e + 15:] = 60.0; S = synth_S(c2)
    chk("X6 先站上（e+10）再跌穿（e+15）⇒ d＝e+15", trig_all(S, e, x, 70.0, x4_none, cross_ma(S), no_turn)["X6"][0], e + 15)
    # X4：0050 先在線上、e+8 跌穿；空頭進場要先站回再跌穿
    c50b = c50.copy(); c50b[e + 8:] = 10.0
    x4b, _, _ = cross_mkt(c50b); S = synth_S(base)
    chk("X4 0050 在 e+8 跌穿 200 日線 ⇒ d＝e+8", trig_all(S, e, x, 100.0, x4b, cross_ma(S), no_turn)["X4"], (e + 8, e + 9))
    c50c = c50.copy(); c50c[e - 5:] = 10.0                            # 進場前已跌穿、之後一直在線下 ⇒ 不觸發
    x4c, _, _ = cross_mkt(c50c)
    chk("X4 進場前已在線下、持有中沒站回 ⇒ 不觸發", trig_all(S, e, x, 100.0, x4c, cross_ma(S), no_turn)["X4"][0], -1)
    # X7：轉負序列
    rv = pd.DataFrame({"9999": [100, 100, 100, 100]}, index=["2020-01", "2020-02", "2020-03", "2020-04"], dtype=float)
    ly = pd.DataFrame({"9999": [110, 90, 110, 90]}, index=rv.index, dtype=float)      # 年增：−, +, −, +
    A = {"2020-01": e - 20, "2020-02": e + 3, "2020-03": e + 25, "2020-04": e + 45}
    tr, nr = rev_turns("9999", rv, ly, A)
    chk("X7 轉負只在前一次 ≥0、本次 ＜0（−,+,−,+ ⇒ 只有第 3 次）", tr.tolist(), [e + 25])
    chk("X7 持有中第一個轉負 ⇒ d＝A、s＝A＋1", trig_all(S, e, x, 100.0, x4_none, cross_ma(S), tr)["X7"], (e + 25, e + 26))
    ly2 = ly.copy(); ly2.iloc[1] = np.nan
    tr2, _ = rev_turns("9999", rv, ly2, A)
    chk("X7 前一次年增不可算 ⇒ 不判", tr2.tolist(), [])
    # 賣不到（s ≥ x）⇒ 不做
    c = base.copy(); c[x - 1] = 80.0; S = synth_S(c)
    chk("最後一個判定日 x−1 觸發、成交日 x ⇒ 不做", trig_all(S, e, x, 100.0, x4_none, cross_ma(S), no_turn)["X1"], (x - 1, -1))
    # X2 對 X6 恰好同日（舉例存在即可，不是蘊含）
    # ── 兩兩不蘊含：隨機合成世界中逐一找「A 觸發、B 不觸發」的例子（42 個有序對）
    rng = np.random.default_rng(20261020)
    need = {(a, b) for a in EXITS for b in EXITS if a != b}
    found = {}
    same_day_any = {}
    N = 0
    while need and N < 20000:
        N += 1
        nn = 700; ee = 450; HH = 120; xx = ee + HH - 1
        sig = rng.uniform(0.005, 0.04); mu = rng.normal(0, 0.002)
        c = 100 * np.exp(np.cumsum(rng.normal(mu, sig, nn)))
        o = c * np.exp(rng.normal(0, sig / 3, nn))
        h = np.maximum(o, c) * (1 + rng.uniform(0, sig, nn)); l = np.minimum(o, c) * (1 - rng.uniform(0, sig, nn))
        S = synth_S(c, o, h, l)
        cm = 100 * np.exp(np.cumsum(rng.normal(rng.normal(0, 0.001), 0.012, nn)))
        x4r, _, _ = cross_mkt(cm)
        months = [f"{2000 + k // 12}-{k % 12 + 1:02d}" for k in range(nn // 21)]
        rv = pd.DataFrame({"9999": rng.uniform(80, 120, len(months))}, index=months)
        ly = pd.DataFrame({"9999": rng.uniform(80, 120, len(months))}, index=months)
        Am = {p: 10 + 21 * k for k, p in enumerate(months)}
        tr, _ = rev_turns("9999", rv, ly, Am)
        P0 = float(o[ee])
        tg = trig_all(S, ee, xx, P0, x4r, cross_ma(S), tr)
        on = {k for k, (d, s) in tg.items() if s >= 0}
        for a in on:
            for b in EXITS:
                if b != a and b not in on and (a, b) in need:
                    need.discard((a, b)); found[f"{a}→{b}"] = {"世界": N, "A 的 d": tg[a][0], "B": "不觸發"}
        for a in on:
            for b in on:
                if a < b and tg[a][0] == tg[b][0]:
                    same_day_any[f"{a}={b}"] = same_day_any.get(f"{a}={b}", 0) + 1
    res["兩兩不蘊含"] = {"找到的有序對": len(found), "應有": 42, "沒找到": sorted(f"{a}→{b}" for a, b in need), "合成世界數": N, "例": found,
                     "同日觸發次數（合成，描述）": same_day_any}
    ok_all &= len(need) == 0
    log(f"  [fixture] 兩兩不蘊含：{len(found)}／42（{N} 個合成世界）；沒找到 {sorted(need)}")
    res["全過"] = bool(ok_all)
    return res


CONDS = {
    "X1": "∃d∈[e,x−1]: v_d ∧ C_d ≤ 0.9·P0",
    "X2": "L_e = P0 − 3·ATR(k_e−1)；L_d = max(L_{d−1}, C_d − 3·ATR_d 若 C_d ＞ max_{e≤u<d} C_u)；∃d: v_d ∧ C_d ＜ L_d",
    "X3": "∃d: v_d ∧ C_d ≥ 1.5·P0",
    "X4": "∃d: M_d ＜ MA200(M)_d ∧ M_{d−1} ≥ MA200(M)_{d−1}（M ＝ 0050）",
    "X5": "d ＝ 第 20 根有效 K 棒（e＝第 1 根）∧ d ≤ x−1 ∧ C_d ≤ P0（只此一次）",
    "X6": "∃d: v_d ∧ C_d ＜ MA50_d ∧ C_{k(d)} ≥ MA50_{k(d)}（k(d) ＝ 前一根有效 K 棒）",
    "X7": "∃ 公布 i: A_i∈[e,x−1] ∧ yoy_i ＜ 0 ∧ yoy_{i−1} ≥ 0",
}
PAIRNOTE = {
    ("X1", "X2"): "X1 線固定於 P0、X2 線隨最高收盤上移且隨 ATR 變；漲後回落 3ATR 不必跌破 −10%，ATR 大時跌 10% 不必碰 X2 線",
    ("X1", "X5"): "X5 只看第 20 根是否 ≤P0（不必跌 10%）；X1 任何一天 ≤−10%（不必在第 20 根）",
    ("X2", "X6"): "MA50 穿越 vs 最高收盤回落 3ATR：條件變數不同（均線 vs 高點與 ATR），可能常同日 ⇒ 重疊比例照報",
    ("X4", "*"): "X4 只看 0050，與個股價格無關 ⇒ 與 X1～X3、X5、X6 互不蘊含；與 X7（營收）無關",
    ("X7", "*"): "X7 只看月營收公布 ⇒ 與價格類互不蘊含",
    ("X3", "*"): "X3 是上漲才賣；其餘六類是下跌或外部條件 ⇒ X3 與 X1、X5 同一筆可同時觸發但不同日",
}


# ═════════════════════════════ 階段一：乾跑（⛔ 不讀任何報酬）
def dry_summary(K, world, cal):
    out = {}
    for H in HS:
        for sg in sorted(set(K[f"seg{H}"]) - {""}):
            G = K[(K[f"seg{H}"] == sg)]
            st = G[f"st{H}"].value_counts().to_dict()
            k = G[G[f"st{H}"] == "保留"]
            if len(k) == 0:
                continue
            mon = k["mon"].to_numpy()
            ent = {"狀態": {str(a): int(b) for a, b in st.items()}, "保留": int(len(k)), "月數": int(len(set(mon))), "n_eff": int(min(len(k), len(set(mon))))}
            tr = {}
            for X in EXITS:
                s = k[f"s{X}_{H}"].to_numpy(); d = k[f"d{X}_{H}"].to_numpy(); t = s >= 0
                tr[X] = {"觸發比例": float(t.mean()), "觸發筆數": int(t.sum()),
                         "條件成立但賣不到（s≥x）": int(((d >= 0) & ~t).sum()),
                         "平均觸發日（d−e＋1，第幾根交易日）": float((d[t] - k["e"].to_numpy()[t] + 1).mean()) if t.any() else None,
                         "中位觸發日": float(np.median(d[t] - k["e"].to_numpy()[t] + 1)) if t.any() else None,
                         "平均持有天數（賣出 s−e；沒觸發記 H）": float(np.where(t, s - k["e"].to_numpy(), H).mean()),
                         "第一根就觸發（d＝e）占全部": float(((d == k["e"].to_numpy()) & t).mean()),
                         "前 5 根內觸發占全部": float(((d - k["e"].to_numpy() < 5) & t).mean()),
                         "第一根就觸發占已觸發": float(((d == k["e"].to_numpy()) & t).sum() / max(t.sum(), 1))}
            ent["七類"] = tr
            if H == HJ:
                # 兩兩觸發關係（⛔ 不含報酬）
                pw = {}
                for i, a in enumerate(EXITS):
                    for b in EXITS[i + 1:]:
                        ta = k[f"s{a}_{H}"].to_numpy() >= 0; tb = k[f"s{b}_{H}"].to_numpy() >= 0
                        da = k[f"d{a}_{H}"].to_numpy(); db = k[f"d{b}_{H}"].to_numpy()
                        both = ta & tb
                        pw[f"{a}×{b}"] = {"P(B|A)": float(tb[ta].mean()) if ta.any() else None, "P(A|B)": float(ta[tb].mean()) if tb.any() else None,
                                          "Jaccard": float(both.sum() / max((ta | tb).sum(), 1)), "兩者都觸發": int(both.sum()),
                                          "都觸發中同一天": float((da[both] == db[both]).mean()) if both.any() else None,
                                          "都觸發中相差 ≤5 天": float((np.abs(da[both] - db[both]) <= 5).mean()) if both.any() else None,
                                          "觸發集合與日全同（等價）": bool((ta == tb).all() and (da[both] == db[both]).all())}
                ent["兩兩"] = pw
                # X4 依 S3 兩邊
                ent["X4 依 S3"] = {CUTS["S3"][1 - v] if v in (0, 1) else "無值": float((k.loc[k["S3"] == v, f"sX4_{H}"] >= 0).mean())
                                  for v in (1, 0, -1) if (k["S3"] == v).any()}
                # X6 與 9/27 狀態式
                ent["X6 穿越 vs 9/27 狀態式"] = {"穿越式觸發比例": float((k[f"sX6_{H}"] >= 0).mean()), "狀態式觸發比例": float((k["sMA50state"] >= 0).mean()),
                                            "狀態式第一根就觸發": float(((k["dMA50state"] == k["e"]) & (k["sMA50state"] >= 0)).mean()),
                                            "兩式同日": float(((k[f"dX6_{H}"] == k["dMA50state"]) & (k["sMA50state"] >= 0)).mean())}
                ent["X7 營收"] = {"該股完全沒有月營收列": float((k["nrev"] == 0).mean()), "持有期內沒有任何轉負公布": float((k[f"nturn{H}"] == 0).mean())}
                ent["X2 ATR 無法起算"] = int(k["na_atr"].sum())
                # 三刀
                cuts = {}
                for cu, (pos, neg) in CUTS.items():
                    v = k[cu].to_numpy()
                    cuts[cu] = {"無值": int((v == -1).sum())}
                    for val, nm in ((1, pos), (0, neg)):
                        sel = v == val
                        cuts[cu][nm] = {"n": int(sel.sum()), "月數": int(len(set(mon[sel]))), "n_eff": int(min(sel.sum(), len(set(mon[sel]))))}
                    for X in EXITS:
                        t = k[f"s{X}_{H}"].to_numpy() >= 0
                        cuts[cu].setdefault("觸發比例", {})[X] = {pos: float(t[v == 1].mean()) if (v == 1).any() else None,
                                                             neg: float(t[v == 0].mean()) if (v == 0).any() else None}
                ok = k["mom"].notna() & k["vol"].notna()
                cuts["S1×S2"] = {"值相關（Pearson）": float(np.corrcoef(k.loc[ok, "mom"], k.loc[ok, "vol"])[0, 1]),
                                 "值相關（Spearman）": float(k.loc[ok, ["mom", "vol"]].rank().corr().iloc[0, 1]),
                                 "強且大占強": float(((k["S1"] == 1) & (k["S2"] == 1)).sum() / max((k["S1"] == 1).sum(), 1)),
                                 "phi（指標）": float(np.corrcoef((k.loc[(k.S1 >= 0) & (k.S2 >= 0), "S1"]), k.loc[(k.S1 >= 0) & (k.S2 >= 0), "S2"])[0, 1])}
                ent["三刀"] = cuts
            out[f"{sg}_H{H}"] = ent
    return out


def degeneracy(DS):
    flags = []
    for key, ent in DS.items():
        if not key.endswith(f"H{HJ}"):
            continue
        for X, t in ent["七類"].items():
            if t["第一根就觸發占已觸發"] > 0.5:
                flags.append(f"{key} {X} 第一根就觸發占已觸發 {t['第一根就觸發占已觸發']:.3f} ＞ 0.5 ⇒ 一買就賣退化")
        for pr, q in ent.get("兩兩", {}).items():
            if q["觸發集合與日全同（等價）"]:
                flags.append(f"{key} {pr} 觸發集合與日全同 ⇒ 等價")
            for kk in ("P(B|A)", "P(A|B)"):
                if q[kk] is not None and q[kk] >= 0.99 and q["都觸發中同一天"] is not None and q["都觸發中同一天"] >= 0.99:
                    flags.append(f"{key} {pr} {kk}={q[kk]:.3f} 且同日 {q['都觸發中同一天']:.3f} ⇒ 疑似蘊含")
    return flags


# ═════════════════════════════ 階段二：格
def cells(K, world):
    rows = []
    for H in HS:
        for sg in sorted(set(K[f"seg{H}"]) - {""}):
            k = K[(K[f"seg{H}"] == sg) & (K[f"st{H}"] == "保留")]
            if len(k) == 0:
                continue
            mon = k["mon"].to_numpy(); yr = k["e"].map(lambda t: int(str(_W["cal"][t])[:4])).to_numpy()
            base = k[f"base{H}"].to_numpy(float)
            for X in EXITS:
                d = k[f"D{X}_{H}"].to_numpy(float); dsl = k[f"Dsl{X}_{H}"].to_numpy(float); s = k[f"s{X}_{H}"].to_numpy(); t = s >= 0
                c95 = ci_mean(d, mon); cB = ci_mean(d, mon, ZB)
                hold = np.where(t, s - k["e"].to_numpy(), H)
                r = {"world": world, "seg": sg, "H": H, "exit": X, "cut": "整體", "side": "全部", "mean": c95["mean"], "se": c95["se"],
                     "lo95": c95["lo"], "hi95": c95["hi"], "loB": cB["lo"], "hiB": cB["hi"], "n": c95["n"], "月數": c95["月數"], "n_eff": c95["n_eff"],
                     "trig_frac": float(t.mean()), "ret_trig_mean": float(k.loc[t, f"r{X}_{H}"].mean()) if t.any() else np.nan,
                     "abandon_base_mean": float(base[t].mean()) if t.any() else np.nan, "hold_better_frac": float((d[t] < 0).mean()) if t.any() else np.nan,
                     "hold_days_mean": float(hold.mean()), "cost_per_year": COST * 245 / float(hold.mean()), "slip_mean": float(dsl.mean()),
                     "base_mean": float(base.mean()), "median": float(np.median(d))}
                if H == HJ:
                    r["mdd_mean"] = float(k[f"mdd{X}"].mean()); r["mdd_base_mean"] = float(k["mdd_base"].mean())
                for m_ in ("twse", "tpex"):
                    sel = k["market"].to_numpy() == m_
                    r[f"mean_{m_}"] = float(d[sel].mean()) if sel.any() else np.nan; r[f"n_{m_}"] = int(sel.sum())
                for y in sorted(set(yr)):
                    r[f"y{y}"] = float(d[yr == y].mean())
                rows.append(r)
                for cu, (pos, neg) in CUTS.items():
                    v = k[cu].to_numpy(); ok = v >= 0
                    q95 = ci_diff(d[ok], v[ok], mon[ok]); qB = ci_diff(d[ok], v[ok], mon[ok], ZB)
                    rows.append({"world": world, "seg": sg, "H": H, "exit": X, "cut": cu, "side": f"{pos}−{neg}", "mean": q95["diff"], "se": q95["se"],
                                 "lo95": q95["lo"], "hi95": q95["hi"], "loB": qB["lo"], "hiB": qB["hi"], "n": q95["nA"] + q95["nB"], "n_eff": q95["n_eff"],
                                 "nA": q95["nA"], "nB": q95["nB"], "月A": q95["月A"], "月B": q95["月B"], "mA": q95["mA"], "mB": q95["mB"]})
                    for val, nm in ((1, pos), (0, neg)):
                        sel = v == val
                        c1 = ci_mean(d[sel], mon[sel]); c2 = ci_mean(d[sel], mon[sel], ZB)
                        rows.append({"world": world, "seg": sg, "H": H, "exit": X, "cut": cu, "side": nm, "mean": c1["mean"], "se": c1["se"],
                                     "lo95": c1["lo"], "hi95": c1["hi"], "loB": c2["lo"], "hiB": c2["hi"], "n": c1["n"], "月數": c1["月數"], "n_eff": c1["n_eff"],
                                     "trig_frac": float(t[sel].mean()) if sel.any() else np.nan, "base_mean": float(base[sel].mean()) if sel.any() else np.nan})
    return pd.DataFrame(rows)


def verdicts(C):
    out = []
    m = C[(C["world"] == "main") & (C["H"] == HJ)]
    for X in EXITS:
        for cu in ["整體"] + list(CUTS):
            sideq = "全部" if cu == "整體" else f"{CUTS[cu][0]}−{CUTS[cu][1]}"
            seg = {}
            for sg in ("explore", "confirm"):
                r = m[(m["seg"] == sg) & (m["exit"] == X) & (m["cut"] == cu) & (m["side"] == sideq)].iloc[0]
                seg[sg] = {"est": float(r["mean"]), "loB": float(r["loB"]), "hiB": float(r["hiB"]), "n_eff": int(r["n_eff"]),
                           "號": sign_of(r["mean"], r["loB"], r["hiB"], int(r["n_eff"]))}
            a, b = seg["explore"]["號"], seg["confirm"]["號"]
            v = f"成立（{a}）" if (a == b and a in ("正", "負")) else "分不出"
            raw = [("正" if s["loB"] > 0 else ("負" if s["hiB"] < 0 else "含0")) for s in seg.values()]
            out.append({"exit": X, "cut": cu, "side": sideq, "explore": seg["explore"], "confirm": seg["confirm"], "判定": v,
                        "不看 n_eff 時（描述）": "兩段同號不含 0" if raw[0] == raw[1] and raw[0] != "含0" else "否"})
    return out


def mkt_events(Wd):
    """X4 的事件清單：0050 跌穿 200 日線的日子（每段）。〈九十八〉事件數才是有效樣本。"""
    cal = Wd["cal"]; out = {}
    for sg, (a, b) in Wd["segs"].items():
        out[sg] = [str(cal[i].date()) for i in np.flatnonzero(Wd["x4"][a:b + 1]) + a]
    return out


# ═════════════════════════════ 主程式
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fixture", "dry", "body", "report"])
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(DRY, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchExitGen {a.mode} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）procs {a.procs} =====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("researchExitGen.py", "researchQuad.py", "research11.py", "avgdown.py", "researchAvg.py", "research34.py", "exit_signal.py")}
    log(f"[程式 sha256] {src}")
    if a.mode == "fixture":
        F = fixture(log)
        json.dump(F, open(os.path.join(OUT, "fixture.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        log(f"[fixture] 全過＝{F['全過']}")
        return
    if a.mode == "report":
        report(json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8")))
        return
    if a.mode == "dry":
        res = {"登錄": "一般出場法第二輪 seq6 sha 484b78603a696fbd；裁定 seq382", "程式": src, "⛔": "乾跑：不讀任何進場後報酬，只看觸發、觸發日、三刀事件數",
               "條件式": CONDS, "條件比較": {f"{k[0]}×{k[1]}": v for k, v in PAIRNOTE.items()}}
        for world in ("main", "early"):
            Wd = setup(world, log); _W["cal"] = Wd["cal"]
            t0 = time.time()
            K = run_pool(Wd, "dry", a.procs, a.limit)
            leak = [c for c in K.columns if c.startswith(("base", "bsl", "mdd")) or (c[:1] in ("r", "D") and c[1:3] in [X[:2] for X in EXITS])]
            if leak:
                raise SystemExit(f"⛔ 乾跑出現報酬欄：{leak}")
            K.to_csv(os.path.join(DRY, f"dry_rows_{world}.csv.gz"), index=False)
            res[world] = {"世界": Wd["info"], "格": dry_summary(K, world, Wd["cal"]), "秒": round(time.time() - t0)}
            log(f"[dry {world}] {len(K):,} 列｜{time.time() - t0:.0f}s")
        res["退化與等價旗標"] = degeneracy(res["main"]["格"]) + degeneracy(res["early"]["格"])
        res["寫檔時間（台北）"] = f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M:%S}"
        json.dump(res, open(os.path.join(DRY, "dry.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        log(f"[dry] 旗標 {res['退化與等價旗標']}")
        return
    # ── body
    dryj = json.load(open(os.path.join(DRY, "dry.json"), encoding="utf-8"))
    if dryj["退化與等價旗標"]:
        raise SystemExit(f"⛔ 階段一有退化／等價旗標，不跑報酬：{dryj['退化與等價旗標']}")
    S = {"登錄": "一般出場法第二輪 seq6 sha 484b78603a696fbd；裁定 seq382；N_前段 ＋28", "程式": src, "z_Bonferroni": ZB}
    Cs = []
    for world in ("main", "early"):
        Wd = setup(world, log); _W["cal"] = Wd["cal"]
        t0 = time.time()
        K = run_pool(Wd, "body", a.procs, a.limit)
        Kd = pd.read_csv(os.path.join(DRY, f"dry_rows_{world}.csv.gz"), dtype={"sid": str})
        trig_cols = [f"{p_}{X}_{H}" for p_ in ("s", "d") for X in EXITS for H in HS if f"{p_}{X}_{H}" in Kd.columns] + ["S1", "S2", "S3"] + [f"st{H}" for H in HS]
        M = K.merge(Kd[["sid", "e"] + trig_cols], on=["sid", "e"], suffixes=("", "_dry"), how="outer", indicator=True)
        diff = {c: int(((M[c].fillna(-9) != M[c + "_dry"].fillna(-9))).sum()) for c in trig_cols}
        S.setdefault("閘_body觸發＝dry觸發", {})[world] = {"不同": {k: v for k, v in diff.items() if v}, "列不齊": int((M["_merge"] != "both").sum())}
        if any(diff.values()) or (M["_merge"] != "both").any():
            raise SystemExit(f"⛔ body 觸發 ≠ dry：{S['閘_body觸發＝dry觸發']}")
        K.to_csv(os.path.join(OUT, f"rows_{world}.csv.gz"), index=False, float_format="%.17g")
        Cs.append(cells(K, world))
        S[f"世界_{world}"] = Wd["info"]
        S[f"X4事件_{world}"] = mkt_events(Wd)
        log(f"[body {world}] {len(K):,} 列｜{time.time() - t0:.0f}s")
    C = pd.concat(Cs, ignore_index=True)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.10g")
    V = verdicts(C)
    json.dump(V, open(os.path.join(OUT, "verdict.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    S["判定"] = V
    S["寫檔時間（台北）"] = f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M:%S}"
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(S)
    log(f"[完成] {time.time() - T0:.0f}s")


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.{d}f}%"


def _row(C, world, seg, H, X, cut="整體", side="全部"):
    q = C[(C["world"] == world) & (C["seg"] == seg) & (C["H"] == H) & (C["exit"] == X) & (C["cut"] == cut) & (C["side"] == side)]
    return q.iloc[0] if len(q) else None


def priors(C, V):
    vm = {(v["exit"], v["cut"]): v for v in V}
    P = {}
    n_pos = sum(1 for X in EXITS if vm[(X, "整體")]["判定"] == "成立（正）")
    P["①"] = {"先驗": "整體 7 格 0 格成立為正（約六成五）", "結果": f"成立為正 {n_pos} 格", "中": n_pos == 0}
    nI = sum(1 for v in V if v["cut"] != "整體" and v["判定"].startswith("成立"))
    P["②"] = {"先驗": "交互 21 格成立 ≤ 3 格（約七成五）", "結果": f"成立 {nI} 格", "中": nI <= 3}
    s3 = {}
    for X in ("X1", "X2"):
        s3[X] = {sg: float(_row(C, "main", sg, HJ, X, "S2", "大−小")["mean"]) for sg in ("explore", "confirm")}
    P["③"] = {"先驗": "X1、X2 在波動大那邊的 d 比波動小高（約六成，方向即可）", "結果": s3,
              "中": all(v > 0 for d_ in s3.values() for v in d_.values()), "讀法": "★ 兩段的點估計（大−小）都 ＞ 0 才算中"}
    r4 = _row(C, "main", "confirm", HJ, "X4")
    P["④"] = {"先驗": "X4 在確認段回落較淺但 d 平均 ＜ 0（約六成）",
              "結果": {"X4 每筆平均回落": float(r4["mdd_mean"]), "基準每筆平均回落": float(r4["mdd_base_mean"]), "d 平均": float(r4["mean"])},
              "中": bool(r4["mdd_mean"] > r4["mdd_base_mean"] and r4["mean"] < 0), "讀法": "★ 回落 ＝ 每筆持股價值路徑最大回落的平均（單筆層）"}
    best = {sg: max(EXITS, key=lambda X: float(_row(C, "main", sg, HJ, X)["mean"])) for sg in ("explore", "confirm")}
    P["⑥"] = {"先驗": "七格中 X7 整體 d 最高（約四成）；X7 整體成立為正（約二成）",
              "結果": {"各段 d 最高": best, "X7 判定": vm[("X7", "整體")]["判定"]},
              "中": {"X7 最高": all(b == "X7" for b in best.values()), "X7 成立為正": vm[("X7", "整體")]["判定"] == "成立（正）"},
              "讀法": "★ 兩段都最高才算中"}
    r7 = {X: {sg: float(_row(C, "main", sg, HJ, X)["mean"]) for sg in ("explore", "confirm")} for X in ("X5", "X6")}
    P["⑦"] = {"先驗": "X5、X6 整體 d ＜ 0（各約六成五）", "結果": r7, "中": {X: all(v < 0 for v in r7[X].values()) for X in r7},
              "讀法": "★ 兩段點估計都 ＜ 0 才算中"}
    P["⑤"] = {"先驗": "seq6 作廢", "結果": "—", "中": None}
    return P


def report(S):
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    V = S["判定"]
    dryj = json.load(open(os.path.join(DRY, "dry.json"), encoding="utf-8"))
    PR = priors(C, V)
    json.dump(PR, open(os.path.join(OUT, "priors.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# 一般出場法第二輪 seq6：隨便買 × 常見七類出場 × 三刀情況（單筆層）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq6（sha 484b78603a696fbd）；裁定 seq382 發號、N_前段 ＋28。回測線計算子代理。", "",
         "必附：" + "；".join(MUST) + "；X5～X7 為實務常見作法、參數本線定。", ""]
    # ── 判定
    L += [f"## 一、判定（H120；28 格 Bonferroni 雙尾 99.82%，z＝{ZB:.4f}；兩段同號且都不含 0 才成立）", "",
          "d ＝ 加出場的報酬（賣掉後記 0）− 抱 120 天報酬；CI 進場月分群。n_eff ＜ 30 ⇒ 該段分不出（exit_result 出口①）。", "",
          "| 出場 | 格 | 探索 估計 [CI] n_eff | 號 | 確認 估計 [CI] n_eff | 號 | 判定 |", "|---|---|---|---|---|---|---|"]
    for v in V:
        ex, cf = v["explore"], v["confirm"]
        nm = "整體" if v["cut"] == "整體" else CNAME[v["cut"]] + "（" + v["side"] + "）"
        L.append(f"| {v['exit']} {ENAME[v['exit']]} | {nm} | {_p(ex['est'], 3)} [{_p(ex['loB'], 3)}, {_p(ex['hiB'], 3)}] {ex['n_eff']} | {ex['號']} | "
                 f"{_p(cf['est'], 3)} [{_p(cf['loB'], 3)}, {_p(cf['hiB'], 3)}] {cf['n_eff']} | {cf['號']} | **{v['判定']}** |")
    nI = sum(1 for v in V if v["cut"] != "整體" and v["判定"].startswith("成立"))
    nO = [v["exit"] for v in V if v["cut"] == "整體" and v["判定"].startswith("成立")]
    s3raw = [f"{v['exit']}" for v in V if v["cut"] == "S3" and v["不看 n_eff 時（描述）"] != "否"]
    L += ["", f"整體成立 {len(nO)} 格（{'、'.join(nO) or '無'}）；交互 21 格成立 {nI} 格。"
          f"S3（0050 多空）空頭邊只有 11／13 個進場月 ⇒ S3 七格依構造 n_eff ＜ 30 判不了（〈四十九〉：還沒測，不是測不出）；"
          f"若不看 n_eff，S3 兩段同號不含 0 的有：{'、'.join(s3raw) or '無'}（描述）。", ""]
    # ── 結果句
    L += ["## 二、結果句（照登錄 §九查表）", ""]
    for v in V:
        if not v["判定"].startswith("成立"):
            continue
        X = v["exit"]; est = (v["explore"]["est"] + v["confirm"]["est"]) / 2
        if v["cut"] == "整體":
            L.append(f"- 隨便買的股票加〔{ENAME[X]}〕，單筆看兩段都比抱 120 天{'好' if '正' in v['判定'] else '差'}，"
                     f"平均{'多' if '正' in v['判定'] else '少'} {abs(v['explore']['est']) * 100:.2f}%（探索）／{abs(v['confirm']['est']) * 100:.2f}%（確認）。")
        else:
            pos, neg = CUTS[v["cut"]]
            a_, b_ = (pos, neg) if "正" in v["判定"] else (neg, pos)
            side_rows = {sg: _row(C, "main", sg, HJ, X, v["cut"], a_) for sg in ("explore", "confirm")}
            stand = []
            for sg, r in side_rows.items():
                stand.append(f"{'探索' if sg == 'explore' else '確認'} {_p(r['mean'], 2)} [{_p(r['loB'], 2)}, {_p(r['hiB'], 2)}]⇒"
                             + ("贏" if r["loB"] > 0 else ("輸" if r["hiB"] < 0 else "分不出")))
            L.append(f"- 〔{ENAME[X]}〕在〔{a_}〕比在〔{b_}〕好 {abs(v['explore']['est']) * 100:.2f}%／{abs(v['confirm']['est']) * 100:.2f}%（兩段一致）；"
                     f"在〔{a_}〕本身對抱著：{'；'.join(stand)}（Bonferroni CI，描述）。")
    if not any(v["判定"].startswith("成立") for v in V):
        L.append("- 隨便買的股票，這七種常見出場不管哪種情況都沒有比抱著好。")
    L += ["- 結果句必附：" + "；".join(MUST) + "。⛔ 本件不是「抱 120 天最好」的證據：只比了這七種出場對抱 120 天，60／250 天只描述。", ""]
    # ── 描述：整體各 H
    L += ["## 三、描述（⛔ 不判）", "", "### 3.1 整體 d（95% CI；各 H、各段）", "",
          "| 段 | H | 出場 | d 平均 [95% CI] | 中位 | 觸發比例 | 觸發時平均報酬 | 放棄組：被賣的抱滿平均／抱著較好比例 | 平均持有天數 | 成本／年 | 滑價版 d | 上市／上櫃 d |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for world, segs in (("main", ("explore", "confirm")), ("early", ("early",))):
        for sg in segs:
            for H in HS:
                for X in EXITS:
                    r = _row(C, world, sg, H, X)
                    if r is None:
                        continue
                    L.append(f"| {sg} | {H} | {X} | {_p(r['mean'], 2)} [{_p(r['lo95'], 2)}, {_p(r['hi95'], 2)}] | {_p(r['median'], 2)} | {r['trig_frac']:.3f} | "
                             f"{_p(r['ret_trig_mean'], 2)} | {_p(r['abandon_base_mean'], 2)}／{r['hold_better_frac']:.3f} | {r['hold_days_mean']:.1f} | "
                             f"{r['cost_per_year'] * 100:.2f}% | {_p(r['slip_mean'], 2)} | {_p(r['mean_twse'], 2)}／{_p(r['mean_tpex'], 2)} |")
                rb = _row(C, world, sg, H, "X1")
                if rb is not None:
                    L.append(f"| {sg} | {H} | 基準（抱 H 天）報酬平均 | {_p(rb['base_mean'], 2)} | | | | | {H} | | | |")
    L += ["", "早年（2005～2014）只描述：" + EARLY_NOTE + "。", ""]
    # ── 切片
    L += ["### 3.2 各情況每種出場的 d（H120；95% CI／Bonferroni CI；描述）", "",
          "| 段 | 刀 | 邊 | 出場 | d 平均 [95%] | [Bonf] | n | 月數 | 觸發比例 |", "|---|---|---|---|---|---|---|---|---|"]
    for world, segs in (("main", ("explore", "confirm")), ("early", ("early",))):
        for sg in segs:
            for cu, (pos, neg) in CUTS.items():
                for side in (pos, neg):
                    for X in EXITS:
                        r = _row(C, world, sg, HJ, X, cu, side)
                        L.append(f"| {sg} | {cu} | {side} | {X} | {_p(r['mean'], 2)} [{_p(r['lo95'], 2)}, {_p(r['hi95'], 2)}] | "
                                 f"[{_p(r['loB'], 2)}, {_p(r['hiB'], 2)}] | {int(r['n'])} | {int(r['月數'])} | {r['trig_frac']:.3f} |")
    L += ["", "H60、H250 的切片在 cells.csv（同欄位）。", ""]
    # ── 分年
    ycols = sorted([c for c in C.columns if c.startswith("y")])
    L += ["### 3.3 分年（H120；依進場年；d 平均）", "", "| 段 | 出場 | " + " | ".join(c[1:] for c in ycols) + " |", "|---|---|" + "---|" * len(ycols)]
    for world, segs in (("main", ("explore", "confirm")), ("early", ("early",))):
        for sg in segs:
            for X in EXITS:
                r = _row(C, world, sg, HJ, X)
                L.append(f"| {sg} | {X} | " + " | ".join(_p(r[c], 1) if np.isfinite(r[c]) else "" for c in ycols) + " |")
    # ── 回落
    L += ["", "### 3.4 每筆最大回落（H120；持股價值路徑；描述）", "", "| 段 | 基準 | " + " | ".join(EXITS) + " |", "|---|---|" + "---|" * 7]
    for world, segs in (("main", ("explore", "confirm")), ("early", ("early",))):
        for sg in segs:
            r0 = _row(C, world, sg, HJ, "X1")
            L.append(f"| {sg} | {_p(r0['mdd_base_mean'], 1)} | " + " | ".join(_p(_row(C, world, sg, HJ, X)["mdd_mean"], 1) for X in EXITS) + " |")
    # ── 階段一
    L += ["", "## 四、階段一（乾跑、⛔ 不含報酬）摘要", ""]
    for world, key in (("main", "explore_H120"), ("main", "confirm_H120"), ("early", "early_H120")):
        ent = dryj[world]["格"][key]
        L.append(f"- {world} {key}：保留 {ent['保留']:,}、月 {ent['月數']}、狀態 {ent['狀態']}")
        L.append("  - 觸發比例／平均觸發日／第一根就觸發占已觸發：" + "；".join(
            f"{X} {t['觸發比例']:.3f}／{t['平均觸發日（d−e＋1，第幾根交易日）'] or 0:.1f}／{t['第一根就觸發占已觸發']:.4f}" for X, t in ent["七類"].items()))
        q = ent["兩兩"]["X2×X6"]
        L.append(f"  - X2×X6：P(X6|X2) {q['P(B|A)']:.3f}、P(X2|X6) {q['P(A|B)']:.3f}、Jaccard {q['Jaccard']:.3f}；兩者都觸發中同一天 {q['都觸發中同一天']:.3f}、相差 ≤5 天 {q['都觸發中相差 ≤5 天']:.3f}")
        L.append(f"  - X6 穿越 vs 9/27 狀態式：{ent['X6 穿越 vs 9/27 狀態式']}；X7：{ent['X7 營收']}；X4 依 S3：{ent['X4 依 S3']}")
        L.append(f"  - S1×S2：{ent['三刀']['S1×S2']}")
    L += [f"- 退化／等價旗標：{dryj['退化與等價旗標'] or '無'}（一買就賣：第一根就觸發占已觸發全部 ≤ 4.5%；兩兩無觸發集合與日全同）", ""]
    L += ["X4 事件（0050 跌穿 200 日線的日子；〈九十八〉有效樣本是事件數）：" + json.dumps({k: v for k, v in S.items() if k.startswith("X4事件")}, ensure_ascii=False), ""]
    # ── 先驗
    L += ["## 五、先驗對照（登錄 §十，⛔ 寫下就不改）", ""]
    for k in ("①", "②", "③", "④", "⑤", "⑥", "⑦"):
        p = PR[k]
        L.append(f"- {k} {p['先驗']}：{json.dumps(p['結果'], ensure_ascii=False, default=str)} ⇒ 中：{p['中']}{('（' + p['讀法'] + '）') if '讀法' in p else ''}")
    L += ["", "## 六、措辭與註", "",
          "- 同根兩出場價（seq373）：每臂只有一種出場、一律收盤判、隔日開盤賣 ⇒ 不會同根碰兩價，不適用。",
          "- 賣出點（seq343）：本件七種出場都是條件到了就賣，⛔ 不稱賣在最高點或頂部。",
          "- 早年：" + EARLY_NOTE + "。", ""]
    L += ["## 七、★ 本線定的地方（登錄沒寫死）", "",
          "1. 確認段尾 ＝ 快照 edc6f 日曆尾 2026-09-24（登錄「資料尾」；9/27 用 2026-08-24）；量測日 2026-03-02 之後用 panel_ext（稽核 ②2 前例）",
          "2. 早年世界 ＝ reduce_v2 版面（只上市）＋ 早年面板 liq_ok∧bars_ok（W1 要個股法人、早年做不到；researchMomX 前例）",
          "3. X2 照「沿用 9/27 定義」用收盤 ＜ 線（登錄字面 ≤，差在恰好相等）",
          "4. X5 報酬 ≤0 ＝ 還原收盤 ≤ 進場價（不含成本）；第 20 日 ＝ 第 20 根有效 K 棒（進場日算第 1 根）",
          "5. X6 進場當天收盤就由線上跌到線下也算「持有中穿越」（前一根是進場前的 K 棒）",
          "6. X7「轉負」比的是前一次公布（有營收的前一期）；前一次年增不可算 ⇒ 不判；可用日 side=right（10／15 日之後第一個交易日）",
          "7. 三刀中位 ＝ 當月全部候選（不看進場日能否成交、不看持有期斷點）有值者；S1 用日曆位置最後有效收盤，回看窗 [lv(T−252), T] 有硬斷點 ⇒ 無值；"
          "S2 ＝ 後一根落在 [T−59, T] 的相鄰有效 K 棒日報酬 ≥40 個、窗內無硬斷點",
          "8. 交互 SE ＝ 指標迴歸係數的月分群 CR0（無小樣本修正，同 exit_signal.cr0）；n_eff（交互取兩邊樣本與月數最小）＜ 30 ⇒ 該段分不出",
          "9. 成本／年 ＝ 0.585% × 245 ÷ 平均持有天數；每筆回落 ＝ 單筆持股價值路徑最大回落（先驗④ 用這個）",
          "10. 先驗判中讀法：③⑦ 兩段點估計方向都對才算中；⑥「最高」要兩段都最高",
          "11. 整體成立為負的結果句：登錄 §九只列正向句 ⇒ 本線用對稱句「比抱 120 天差、平均少 x%」",
          "12. 退化旗標規則：第一根就觸發占已觸發 ＞ 50% ⇒ 一買就賣；觸發集合與日全同 ⇒ 等價；P(B|A) ≥ 0.99 且同日 ≥ 0.99 ⇒ 疑似蘊含", ""]
    ck = os.path.join(OUT, "check.json")
    if os.path.exists(ck):
        cj = json.load(open(ck, encoding="utf-8"))
        L += ["## 八、對帳（researchExitGen_check.py）", "",
              f"- ① 逐根手算 20 筆（七種出場各 ≥2 筆有觸發）：不同 {cj['① 逐根手算 20 筆']['不同筆數']}／20（d、s、基準、D 逐筆，容差 1e−12）",
              f"- ② 不前視：正式程式吃「d 之後截掉」的資料，觸發日不變；三刀值吃「T 之後截掉」不變：不通過 {cj['② 不前視']['不通過筆數']}／20"
              "（反向對照：截到 d−1 ⇒ 91／91 個觸發日都改變，測試不是空轉）",
              f"- ③ 彙總重算 {cj['③ 彙總重算']['格數']} 格（H120 主＋早年，整體＋交互）：最大差 平均 {cj['③ 彙總重算']['最大差（平均）']:.1e}、SE {cj['③ 彙總重算']['最大差（SE）']:.1e}；"
              f"判定重算不同 {cj['③ 判定重算']['不同']}／{cj['③ 判定重算']['格']}",
              "- 9/27 重現：探索段 H120 保留 21,588 筆、X1 d −4.483% ＝ resultsQuad SL10 同值", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
