# -*- coding: utf-8 -*-
"""PREREG動能改良 seq1（台股策略線 登錄 sha f9b6932850aa4ea7；裁定 seq256 發號、N_組合 ＋4；§二 1：M1≈F、M3≈C 同構）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMomX [--procs 2] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchMomX_check.py

═══ 登錄定義（§二，逐字照做）═══
  M0 單純動能（對照、⛔ 不判）：R(F) 最高前 N｜M1 剔除極端：刪 R(F) 最高 3% 與最低 3% 後取最高前 N
  M2 持續型：上個換股日 R(F) 前 30% ∧ 這個換股日仍前 30% 的股票裡取 R(F) 最高前 N（兩次判定都只用各自換股日前一日以前的資料）
  M3 殘差動能：過去 36 個月月報酬對 0050 月報酬迴歸（≥ 24 個月），殘差在形成期的累積 ÷ 殘差標準差，最高前 N
  M4 波動縮放：持股同 M0；股票部位比例 ＝ min(1, 20% ÷ 持股組合過去 60 日年化波動)，其餘現金（0 息）
  格：F ∈ {3, 6, 12} 月 × 月／季換 × N ∈ {10, 20} ＝ 12 格／件；等權、成本 0.585%、仍入選續抱
═══ 本線落地讀法（⭐ 看任何報酬前寫死；登錄沒寫死之處）═══
  R1 換股日 e ＝ 當月 W1 量測日（該月第一個交易日，面板 measure_date）的次一交易日；eligible ＝ 同月量測日的面板 eligible（量測日收盤可知）
     季換 ＝ 1、4、7、10 月的換股日（強勢類股 U3 同）
  R2 形成期：⭐ R(F) ＝ 月底收盤(m−2) ÷ 月底收盤(m−2−F) − 1（m ＝ 換股日所在月；月底 ＝ 該月最後交易日、ffill 還原收盤）
     ⇒ 照 §一「跳過最近 1 個月」：跳過 m−1 整月；§二 字面「前 F＋1 個月底到前 1 個月底」若以換股日當月為第 0 個月即同此式。
     另一讀法（不跳過：月底(m−1)÷月底(m−1−F)）⛔ 不判，只在挑中格報描述
     R(F) 需兩端收盤有限 ＞ 0；排名母體 ＝ 當月 eligible ∩ R(F) 可算；同值依代號
  R3 M1：n ＝ 排名母體數，k ＝ floor(0.03n)，刪最高 k 與最低 k
  R4 M2：「上個換股日」＝ 同頻率（月／季）的前一個換股日；前 30% ＝ 名次 ≤ ceil(0.3n)；留下比例 ＝ |交集| ÷ |本期前 30%|
  R5 M3：月報酬 ＝ 月底收盤比；迴歸窗 ＝ m−37～m−2 的 36 個月報酬（有 intercept 的 OLS），股票與 0050 當月報酬都有限的月 ≥ 24；
     殘差標準差 ＝ 迴歸窗殘差 ddof＝1；分數 ＝ 最近 F 個月（m−F−1～m−2）殘差和 ÷ 殘差標準差
  R6 M4：持股組合 ＝ 本期 M0 名單；波動 ＝ 名單 N 檔 [e−60, e−1] 等權日報酬（ffill 收盤）的標準差 × √245；不可算 ⇒ 比例 1（件數報）
     ⭐ 實作 ＝ 覆蓋層：M0 同格換股簿的逐日報酬 × 股票部位；換股日把股票部位調到 w × equity，調整金額 × 0.585%（保守：整筆來回）；兩次換股間部位隨行情漂移
  R7 換股簿（researchSector sim_book 同一套）：落選者換股日開盤賣（跌停／停牌延後）、新入選依名次開盤買（漲停／停牌 ⇒ 該名額持現金、⛔ 不遞補）、
     金額 ＝ min(前一日 equity ÷ N, 現金)、賣出扣進場金額 × 0.585%；⭐ 停止交易強制出場：開（該股最後一根有效收盤 L ＜ 窗尾 ⇒ t ＞ L 起以 L 收盤了結、扣成本）；
     下市（delist_status delisted_*）同樣了結；窗尾照收盤計值
     ⇒ 資料尾：換股簿按月換股、窗尾照市值，⛔ 沒有固定持有天數的出場 ⇒ 依構造不會因資料尾截斷丟訊號（t1_censor 不適用，照實寫）；最後一個換股日 ＝ 2026-08-04（量測 08-03）
  R8 退化格（K7，事前排除）：探索段 平均持股 ＜ N÷2、或換股簿現金比例 ＞ 30% ⇒ 不參與挑格（M4 用其底層 M0 換股簿判；波動縮放的現金是設計，不算退化）
  R9 挑格：每件探索段 12 格（去退化）⇒ 過使用者判準（年化 ＞ 0050 同段 ∧ 比值 ≥ 0050）者取比值最高；都沒過取比值最高；平手 ⇒ 年化高、F 小、月先、N 小
     判定：確認段、早年段各照使用者判準；件標籤 ＝ 兩段較嚴的一個（合格 ＞ 另列 ＞ 不合格；裁定 seq256 §二 1）
  R10 窗：主 ＝ main edc6f8002f 快照、panel_ext（量測日 2015-01～2026-08-03）、換股簿 2017-03-02～2026-08-24 一條權益；探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24
      ⭐ 早年 ＝ 早年版面 ~/earlydata/3edc0e2206/main（只上市；2004-02-11～2014-12-31）＋ 面板 sig_main/panel.csv.gz；
      早年沒有個股法人（T86 2012-05 起）⇒ W1 eligible 在 2012-06 以前做不到 ⇒ 早年 eligible ＝ liq_ok ∧ bars_ok（eligible_v，researchV desc 同）；
      換股簿 2006 年第一個換股日～2014-12-31；⚠ 登錄寫「2006～2016」：2015～2016 在主快照、形成期要 2014 以前的價格（兩版面還原尺度未接）⇒ 做不到、照寫
  R11 假訊號（同池隨機）：挑中格的頻率與 N；每個換股日從排名母體（eligible ∩ R(F) 可算）不放回隨機抽 N 檔（M4 照同一套縮放）；rng default_rng([20260928, 件序, r])；
      p ＝ 隨機年化 ≥ 本格的比例（確認段、早年段各報）
  R12 出場敏感度（新規矩 ③；描述、⛔ 不判）：挑中格若確認段 合格／另列 ⇒ 另跑 (a) 全賣全買、(b) 持有期間收盤跌破 MA60（ffill 收盤 60 日均）⇒ 次一交易日開盤賣、現金等下次換股
  R13 營量 v1 並列：resultsYfMix13（eq_main.npz、positions.csv.gz 格 13）同段年化／回落與逐日持股重疊（主窗）
  R14 PREREGF（W1 池剔除極端強勢 主窗 +26.14%／−40.27% 另列）、PREREGC（W1 池殘差動能 +24.62%／−41.51% 另列）⇒ 結果句必附；本件結果不覆蓋 F、C
輸出 backtest/resultsMomX/
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                               # ⭐ D.DATA ⇒ main 快照、chdir ⇒ repo
D, TR, UG = H2.D, H2.TR, H2.UG
from backtest import research13 as R13

OUT = "backtest/resultsMomX"
COST = 0.00585
FS, FREQS, NS = (3, 6, 12), ("月", "季"), (10, 20)
MS = ("M0", "M1", "M2", "M3", "M4")
MNAME = {"M0": "單純動能（對照）", "M1": "剔除極端 3%", "M2": "持續型", "M3": "殘差動能（對 0050、36 月）", "M4": "波動縮放（目標 20%）"}
MAIN = {"data": H2.H2D, "panel": "backtest/resultsp9_engine/panel_ext.csv.gz", "elig": "eligible", "w": ("2017-03-02", "2026-08-24"),
        "segs": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}}
EARLY = {"data": os.path.expanduser("~/earlydata/3edc0e2206/main/data"), "panel": os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz"),
         "elig": "eligible_v", "w": ("2006-01-01", "2014-12-31"), "segs": {"早年": ("2006-01-01", "2014-12-31")}}
ANCHOR = (0.24020209886370614, -0.3395700527611012)
_G: dict = {}


# ═════════════ 資料 ═════════════
def _init(cal, data):
    D.DATA = data
    _G.update(cal=cal)


def load_full(args):
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    raw = st.df["close"].to_numpy(float)
    tb = TR.one(sid, cal)
    return sid, {"c": pd.Series(raw).ffill().to_numpy(float), "o": st.df["open"].to_numpy(float), "valid": np.isfinite(raw),
                 "trd": np.asarray(tb["trd"], bool), "up_o": np.asarray(tb["up_o"], bool), "dn_o": np.asarray(tb["dn_o"], bool)}


def load_world(W, procs, log):
    D.DATA = W["data"]
    cal = D.load_calendar(); n = len(cal)
    pan = pd.read_csv(W["panel"], dtype={"stock_id": str}, parse_dates=["measure_date"],
                      usecols=lambda c: c in ("measure_date", "stock_id", "eligible", "liq_ok", "bars_ok"))
    if W["elig"] == "eligible_v":
        pan["el"] = pan["liq_ok"].astype(str).isin(["True", "1"]) & pan["bars_ok"].astype(str).isin(["True", "1"])
    else:
        pan["el"] = pan["eligible"].astype(str).isin(["True", "1"])
    stocks = pd.read_csv(os.path.join(W["data"], "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    G = G[G["stock_id"].isin(set(pan["stock_id"]))]
    with Pool(procs, initializer=_init, initargs=(cal, W["data"])) as pool:
        P = dict(pool.map(load_full, list(zip(G["stock_id"], G["market"])), chunksize=16))
    P = {s: v for s, v in P.items() if v is not None}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=TR.load_official())
    w0 = int(cal.searchsorted(pd.Timestamp(W["w"][0]))); w1 = int(cal.searchsorted(pd.Timestamp(W["w"][1]), side="right") - 1)
    ym = np.asarray(cal.year * 12 + cal.month)
    months = np.unique(ym)
    me = {int(m): int(np.flatnonzero(ym == m)[-1]) for m in months}          # 月底位置
    reb = {}
    for d, g in pan.groupby("measure_date"):
        mpos = int(cal.searchsorted(d))
        if mpos >= n - 1 or cal[mpos] != d:
            continue
        e = mpos + 1
        if e > w1:
            continue
        reb[e] = sorted(s for s in g.loc[g["el"], "stock_id"] if s in P)
    allr = sorted(reb)
    rebs = [e for e in allr if e >= w0]
    pre = [e for e in allr if e < w0][-3:]                                  # 窗前 3 個：只給 M2 當「上個換股日」（季換要回看一季）
    reb = {e: reb[e] for e in pre + rebs}
    w0 = rebs[0]                                                            # 換股簿從第一個換股日起算
    sids = sorted(P); ix = {s: i for i, s in enumerate(sids)}
    C = np.column_stack([P[s]["c"] for s in sids])
    V = np.column_stack([P[s]["valid"] for s in sids])
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    SF = {}
    for s in sids:
        b = np.flatnonzero(P[s]["valid"])
        if len(b) and b[-1] < w1:
            SF[s] = int(b[-1])
    log(f"[資料] {W['data']}｜日曆 {cal[0].date()}～{cal[-1].date()}｜母體 {len(P):,}｜換股日 {len(rebs)}（{cal[rebs[0]].date()}～{cal[rebs[-1]].date()}）｜"
        f"eligible 中位 {np.median([len(v) for v in reb.values()]):.0f}｜停止交易（窗尾前）{len(SF)}")
    return {"cal": cal, "n": n, "P": P, "dl": dl, "w0": w0, "w1": w1, "ym": ym, "me": me, "reb": reb, "rebs": rebs, "pre": pre, "sids": sids, "ix": ix,
            "C": C, "V": V, "bench": bench, "SF": SF}


# ═════════════ 排名 ═════════════
def rank_tables(Wd, F, skip=True):
    """每個換股日：R(F)（dict）、M3 分數（dict）。"""
    cal, me, C, ix = Wd["cal"], Wd["me"], Wd["C"], Wd["ix"]
    out = {}
    bench = Wd["bench"]
    for e in Wd["pre"] + Wd["rebs"]:
        m = int(Wd["ym"][e]); lag = 2 if skip else 1
        a_m, b_m = m - lag - F, m - lag
        if a_m not in me or b_m not in me:
            out[e] = ({}, {}); continue
        ca, cb = C[me[a_m]], C[me[b_m]]
        R = {}
        for s in Wd["reb"][e]:
            i = ix[s]
            if np.isfinite(ca[i]) and np.isfinite(cb[i]) and ca[i] > 0 and cb[i] > 0:
                R[s] = float(cb[i] / ca[i] - 1.0)
        M3 = {}
        ks = [k for k in range(b_m - 36, b_m + 1) if k in me]              # 至多 37 個月底 ⇒ 至多 36 個月報酬（m−37…m−2；日曆起點前的月不存在）
        if len(ks) >= 25 and R:
            pos = [me[k] for k in ks]
            bm = bench[pos]; rb = bm[1:] / bm[:-1] - 1.0
            cols = [ix[s] for s in R]
            CM = C[np.ix_(pos, cols)]
            with np.errstate(invalid="ignore", divide="ignore"):
                RS = CM[1:] / CM[:-1] - 1.0
            for j, s in enumerate(R):
                y = RS[:, j]; ok = np.isfinite(y) & np.isfinite(rb)
                if ok.sum() < 24:
                    continue
                x_ = rb[ok]; y_ = y[ok]
                X = np.column_stack([np.ones(len(x_)), x_])
                beta, *_ = np.linalg.lstsq(X, y_, rcond=None)
                res = np.full(len(y), np.nan); res[ok] = y_ - X @ beta
                sd = float(np.nanstd(res[ok], ddof=1))
                if not (sd > 0):
                    continue
                last = res[-F:]
                if not np.isfinite(last).all():
                    continue
                M3[s] = float(last.sum() / sd)
        out[e] = (R, M3)
    return out


def top(d, N, excl=None):
    items = sorted(((v, s) for s, v in d.items() if excl is None or s not in excl), key=lambda t: (-t[0], t[1]))
    return [s for _, s in items[:N]]


def select(Wd, TB, M, F, freq, N):
    """回 {e: 名單}（換股日依頻率）與 M2 留下比例。"""
    allr = [e for e in Wd["pre"] + Wd["rebs"] if freq == "月" or Wd["cal"][e].month in (1, 4, 7, 10)]
    sel = {}; keep = []
    prev = None
    for e in allr:
        R, M3 = TB[e]
        if e < Wd["w0"]:                                                    # 窗前：只給 M2 記「上個換股日」的前 30%
            order = sorted(R, key=lambda s: (-R[s], s)); prev = set(order[:int(math.ceil(0.3 * len(order)))])
            continue
        if M in ("M0", "M4"):
            sel[e] = top(R, N)
        elif M == "M1":
            n = len(R); k = int(math.floor(0.03 * n))
            order = sorted(R, key=lambda s: (-R[s], s))
            drop = set(order[:k]) | set(order[n - k:]) if k > 0 else set()
            sel[e] = top(R, N, excl=drop)
        elif M == "M2":
            order = sorted(R, key=lambda s: (-R[s], s)); cut = int(math.ceil(0.3 * len(order)))
            cur = set(order[:cut])
            if prev is None:
                sel[e] = []
            else:
                both = {s: R[s] for s in cur & prev}
                sel[e] = top(both, N)
                keep.append(len(cur & prev) / len(cur) if cur else np.nan)
            prev = cur
        elif M == "M3":
            sel[e] = top(M3, N)
    return sel, (float(np.nanmean(keep)) if keep else None)


# ═════════════ 換股簿 ═════════════
def sim_book(sel, Wd, N, mode="hold", ma_stop=None, scale=None, t0=None, t1=None):
    """researchSector.sim_book 同一套＋停止交易強制出場（Wd['SF']）＋ ma_stop（跌破 MA 次日開盤賣）＋ scale（M4 覆蓋層另算）。"""
    P, dl, SF = Wd["P"], Wd["dl"], Wd["SF"]
    t0 = Wd["w0"] if t0 is None else t0; t1 = Wd["w1"] if t1 is None else t1
    n = Wd["n"]
    eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    npos = np.zeros(n, np.int16); cashf = np.zeros(n); costd = np.zeros(n)
    buys = {}; hold = {}
    cnt = {"buy": 0, "sell": 0, "limit_up": 0, "halt": 0, "sell_delayed": 0, "delist_settled": 0, "stop_force": 0, "ma_stop": 0}
    for t in range(t0, t1 + 1):
        s_ = sel.get(t)
        if s_ is not None:
            pend = set(pos) if mode == "all" else ((pend | (set(pos) - set(s_))) - set(s_))
        if ma_stop is not None and t > t0:
            for s in list(pos):
                if s in pend:
                    continue
                mv = ma_stop[s][t - 1]
                if np.isfinite(mv) and P[s]["valid"][t - 1] and P[s]["c"][t - 1] < mv:
                    pend.add(s); cnt["ma_stop"] += 1
        for s in sorted(set(pend) | {s for s in pos if s in SF and t > SF[s]}):
            if s not in pos:
                pend.discard(s); continue
            x = P[s]; o_t = x["o"][t]
            if s in SF and t > SF[s]:
                px = x["c"][t]; cnt["stop_force"] += 1
            elif x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; cnt["delist_settled"] += 1
            else:
                cnt["sell_delayed"] += 1; continue
            u, amt = pos.pop(s)
            cash += u * px - amt * COST; costd[t] += amt * COST; cnt["sell"] += 1
            pend.discard(s)
        if s_ is not None:
            free = N - len(pos)
            new = [s for s in s_ if s not in pos][:max(free, 0)]
            nb = 0
            for s in new:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0) or (s in SF and t > SF[s]):
                    cnt["halt"] += 1; continue
                if x["up_o"][t]:
                    cnt["limit_up"] += 1; continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[s] = [amt / o_t, amt]; nb += 1; cnt["buy"] += 1
            buys[t] = nb; hold[t] = sorted(pos)
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buys": buys, "hold": hold, "cnt": cnt}


def vol_scale(Wd, sel, N):
    """R6：每個換股日的股票部位比例 w。"""
    C, ix = Wd["C"], Wd["ix"]; w = {}; nan = 0
    for e, s_ in sel.items():
        cols = [ix[s] for s in s_]
        if len(cols) == 0 or e - 61 < 0:
            w[e] = 1.0; nan += 1; continue
        seg = C[e - 61:e, :][:, cols]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = seg[1:] / seg[:-1] - 1.0
        ew = np.nanmean(r, axis=1)
        ew = ew[np.isfinite(ew)]
        if len(ew) < 30:
            w[e] = 1.0; nan += 1; continue
        v = float(np.std(ew, ddof=1) * math.sqrt(245))
        w[e] = min(1.0, 0.20 / v) if v > 0 else 1.0
    return w, nan


def overlay(book_eq, w, t0, t1, n):
    """R6：覆蓋層權益。"""
    eq = np.ones(n); sl = 0.0; cash = 1.0; wd = np.full(n, np.nan); costd = np.zeros(n)
    for t in range(t0, t1 + 1):
        if t > t0:
            r = book_eq[t] / book_eq[t - 1] - 1.0
            sl *= (1.0 + r)
        tot = sl + cash
        if t in w:
            tgt = w[t] * tot
            c_ = abs(tgt - sl) * COST
            sl, cash = tgt, tot - tgt - c_; costd[t] = c_
        eq[t] = sl + cash; wd[t] = sl / eq[t] if eq[t] > 0 else np.nan
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    return eq, wd, costd


def seg_stats(Wd, res, a, b, N, reb_seg, eq=None, costd=None):
    eq = res["eq"] if eq is None else eq
    costd = res["costd"] if costd is None else costd
    c, m = R13.window_stats(eq, 0, len(eq), a, b + 1)
    yrs = (b - a + 1) / 245
    tv = [res["buys"][e] / N for e in reb_seg[1:] if e in res["buys"]]
    cy = float(sum(costd[t] / eq[t - 1] for t in range(a, b + 1) if costd[t] > 0) / yrs)
    return {"年化": float(c), "回落": float(m), "比值": float(c) / abs(float(m)) if m < 0 else float("nan"),
            "換手（每次換股買進檔數÷N）": float(np.mean(tv)) if tv else float("nan"), "成本／年": cy,
            "平均持股": float(np.mean(res["npos"][a:b + 1])), "換股簿現金比例": float(np.nanmean(res["cashf"][a:b + 1]))}


def label(c, m, c0, m0):
    r, r0 = c / abs(m), c0 / abs(m0)
    return "合格" if (c > c0 and r >= r0) else ("另列" if c > c0 else "不合格")


LORD = {"合格": 0, "另列": 1, "不合格": 2}


# ═════════════ 一個世界的全部格 ═════════════
def run_world(Wd, segs, log, tag):
    cal = Wd["cal"]
    SEGP = {nm: (max(int(cal.searchsorted(pd.Timestamp(a))), Wd["w0"]), min(int(cal.searchsorted(pd.Timestamp(b), side="right") - 1), Wd["w1"])) for nm, (a, b) in segs.items()}
    Z = {nm: R13.window_stats(Wd["bench"], 0, Wd["n"], a, b + 1) for nm, (a, b) in SEGP.items()}
    TBs = {F: rank_tables(Wd, F) for F in FS}
    rows = []; EQ = {}; RES = {}; SELS = {}
    for M in MS:
        for F in FS:
            for fq in FREQS:
                for N in NS:
                    key = f"{M}_F{F}_{fq}_N{N}"
                    base_M = "M0" if M == "M4" else M
                    sel, keep = select(Wd, TBs[F], base_M, F, fq, N)
                    res = sim_book(sel, Wd, N)
                    extra = {}
                    if M == "M4":
                        w, nw = vol_scale(Wd, sel, N)
                        eq4, wd, cd4 = overlay(res["eq"], w, Wd["w0"], Wd["w1"], Wd["n"])
                        costd = res["costd"] * 0.0
                        # 成本：底層換股簿成本按股票部位比例計入 ＋ 覆蓋層調整成本
                        for t in range(Wd["w0"], Wd["w1"] + 1):
                            if res["costd"][t] > 0 and not np.isnan(wd[t - 1] if t > 0 else np.nan):
                                costd[t] = res["costd"][t] / res["eq"][t - 1] * wd[t - 1] * eq4[t - 1]
                        costd = costd + cd4
                        eq = eq4; extra = {"w": w, "wd": wd, "w不可算": nw}
                    else:
                        eq, costd = res["eq"], res["costd"]
                    EQ[key] = eq; RES[key] = res; SELS[key] = sel
                    for nm, (a, b) in SEGP.items():
                        rs = [e for e in sorted(sel) if a <= e <= b]
                        st = seg_stats(Wd, res, a, b, N, rs, eq=eq, costd=costd)
                        if M == "M4":
                            st["平均股票比例"] = float(np.nanmean(extra["wd"][a:b + 1]))
                        if M == "M2":
                            st["持續判定後留下比例"] = keep
                        st["標籤"] = label(st["年化"], st["回落"], Z[nm][0], Z[nm][1])
                        rows.append({"世界": tag, "件": M, "格": key, "F": F, "頻率": fq, "N": N, "段": nm, **st, **{f"cnt_{k}": v for k, v in res["cnt"].items()}})
        log(f"  [{tag}] {M} 12 格完成")
    return pd.DataFrame(rows), EQ, RES, SELS, SEGP, Z, TBs


# ═════════════ 假訊號、出場敏感度 ═════════════
def _fake(args):
    mi, M, F, fq, N, r = args
    Wd, TB = _G["Wd"], _G["TBs"][F]
    rebs = [e for e in Wd["rebs"] if fq == "月" or Wd["cal"][e].month in (1, 4, 7, 10)]
    rng = np.random.default_rng([20260928, mi, r])
    sel = {}
    for e in rebs:
        pool = sorted(TB[e][0])
        sel[e] = list(rng.choice(pool, size=min(N, len(pool)), replace=False)) if pool else []
    res = sim_book(sel, Wd, N)
    eq = res["eq"]
    if M == "M4":
        w, _ = vol_scale(Wd, sel, N)
        eq, _, _ = overlay(res["eq"], w, Wd["w0"], Wd["w1"], Wd["n"])
    out = {"件": M, "r": r}
    for nm, (a, b) in _G["SEGP"].items():
        c, m = R13.window_stats(eq, 0, len(eq), a, b + 1)
        out[f"{nm}_年化"] = float(c); out[f"{nm}_回落"] = float(m)
    return out


def ma_table(Wd, sids, n_=60):
    return {s: pd.Series(Wd["P"][s]["c"]).rolling(n_, min_periods=n_).mean().to_numpy() for s in sids}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchMomX（PREREG動能改良 seq1）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）procs {a.procs} reps {a.reps} =====")
    S = {"登錄": "PREREG動能改良 seq1 sha f9b6932850aa4ea7；裁定 seq256", "閘": {}}
    # ── 主世界
    Wm = load_world(MAIN, a.procs, log)
    c_, m_ = R13.window_stats(Wm["bench"], 0, Wm["n"], Wm["w0"], Wm["w1"] + 1)
    S["閘"]["0050 主窗錨逐位元"] = repr(float(c_)) == repr(ANCHOR[0]) and repr(float(m_)) == repr(ANCHOR[1])
    S["閘"]["主窗起點 ＝ 2017-03-02"] = str(Wm["cal"][Wm["w0"]].date()) == "2017-03-02"
    log(f"[閘] {S['閘']}")
    if not all(S["閘"].values()):
        raise SystemExit("⛔ 閘不過")
    Tm, EQm, RESm, SELm, SEGm, Zm, TBm = run_world(Wm, MAIN["segs"], log, "主")
    # ── 早年世界
    We = load_world(EARLY, a.procs, log)
    Te, EQe, RESe, SELe, SEGe, Ze, TBe = run_world(We, EARLY["segs"], log, "早年")
    D.DATA = H2.H2D
    T = pd.concat([Tm, Te], ignore_index=True)
    T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    S["0050"] = {**{nm: {"年化": float(v[0]), "回落": float(v[1]), "比值": float(v[0]) / abs(float(v[1]))} for nm, v in Zm.items()},
                 **{nm: {"年化": float(v[0]), "回落": float(v[1]), "比值": float(v[0]) / abs(float(v[1]))} for nm, v in Ze.items()}}
    S["窗"] = {**{nm: [str(Wm["cal"][a_].date()), str(Wm["cal"][b_].date())] for nm, (a_, b_) in SEGm.items()},
               **{nm: [str(We["cal"][a_].date()), str(We["cal"][b_].date())] for nm, (a_, b_) in SEGe.items()}}
    # ── 挑格（每件）
    picks = {}
    ex = T[(T["世界"] == "主") & (T["段"] == "探索")].copy()
    c0, m0 = Zm["探索"]; r0 = c0 / abs(m0)
    for M in ("M1", "M2", "M3", "M4"):
        x = ex[ex["件"] == M].copy()
        base = ex[ex["件"] == ("M0" if M == "M4" else M)].set_index("格")
        bk = [k.replace("M4_", "M0_") if M == "M4" else k for k in x["格"]]
        x["退化"] = [(base.loc[k, "平均持股"] < int(k.split("_N")[1]) / 2) or (base.loc[k, "換股簿現金比例"] > 0.30) for k in bk]
        pool = x[~x["退化"]]
        pas = pool[(pool["年化"] > c0) & (pool["比值"] >= r0)]
        pp = pas if len(pas) else pool
        pp = pp.assign(_f=pp["頻率"].map({"月": 0, "季": 1}))
        best = pp.sort_values(["比值", "年化", "F", "_f", "N"], ascending=[False, False, True, True, True]).iloc[0]
        key = best["格"]
        cf = T[(T["世界"] == "主") & (T["段"] == "確認") & (T["格"] == key)].iloc[0]
        ea = T[(T["世界"] == "早年") & (T["段"] == "早年") & (T["格"] == key)].iloc[0]
        m0k = key.replace(M, "M0")
        cm0 = T[(T["世界"] == "主") & (T["段"] == "確認") & (T["格"] == m0k)].iloc[0]
        em0 = T[(T["世界"] == "早年") & (T["段"] == "早年") & (T["格"] == m0k)].iloc[0]
        final = max((cf["標籤"], ea["標籤"]), key=lambda l: LORD[l])
        picks[M] = {"格": key, "F": int(best["F"]), "頻率": best["頻率"], "N": int(best["N"]), "探索過判準格數": int(len(pas)), "退化排除格數": int(x["退化"].sum()),
                    "探索": {k: float(best[k]) for k in ("年化", "回落", "比值")},
                    "確認": {k: (float(cf[k]) if k != "標籤" else cf[k]) for k in ("年化", "回落", "比值", "換手（每次換股買進檔數÷N）", "成本／年", "平均持股", "標籤")},
                    "早年": {k: (float(ea[k]) if k != "標籤" else ea[k]) for k in ("年化", "回落", "比值", "平均持股", "標籤")},
                    "件標籤（兩段較嚴）": final,
                    "同格 M0": {"確認": {"年化": float(cm0["年化"]), "回落": float(cm0["回落"]), "標籤": cm0["標籤"]},
                              "早年": {"年化": float(em0["年化"]), "回落": float(em0["回落"]), "標籤": em0["標籤"]},
                              "確認 比 M0 多（點）": float((cf["年化"] - cm0["年化"]) * 100), "早年 比 M0 多（點）": float((ea["年化"] - em0["年化"]) * 100)}}
        for k in ("平均股票比例", "持續判定後留下比例"):
            if k in cf and pd.notna(cf.get(k)):
                picks[M]["確認"][k] = float(cf[k]); picks[M]["早年"][k] = float(ea[k]) if pd.notna(ea.get(k)) else None
        log(f"[挑格 {M}] {key}｜探索 {best['年化']:+.2%}／{best['回落']:+.2%}（{best['比值']:.3f}）｜確認 {cf['年化']:+.2%}／{cf['回落']:+.2%} {cf['標籤']}｜"
            f"早年 {ea['年化']:+.2%}／{ea['回落']:+.2%} {ea['標籤']} ⇒ {final}｜同格 M0 確認 {cm0['年化']:+.2%}")
    S["挑格"] = picks
    # ── 假訊號（同池隨機）
    FK = []
    for Wd, TBs, SEGP, nmw in ((Wm, TBm, SEGm, "主"), (We, TBe, SEGe, "早年")):
        _G.update(Wd=Wd, TBs=TBs, SEGP=SEGP)
        jobs = [(mi, M, picks[M]["F"], picks[M]["頻率"], picks[M]["N"], r) for mi, M in enumerate(("M1", "M2", "M3", "M4")) for r in range(a.reps)]
        tt = time.time()
        with Pool(a.procs) as pool:
            res = pool.map(_fake, jobs, chunksize=20)
        for x in res:
            x["世界"] = nmw
        FK += res
        log(f"[假訊號 {nmw}] {len(jobs):,} 次｜{time.time() - tt:.0f}s")
    FKd = pd.DataFrame(FK); FKd.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
    for M in ("M1", "M2", "M3", "M4"):
        f = FKd[FKd["件"] == M]
        for nm, seg in (("確認", "確認"), ("早年", "早年")):
            x = f[f[f"{seg}_年化"].notna()][f"{seg}_年化"].to_numpy(float) if f"{seg}_年化" in f else np.array([])
            real = picks[M][nm]["年化"]
            picks[M][f"假訊號_{nm}"] = {"p（隨機年化 ≥ 本格）": float(np.mean(x >= real)) if len(x) else None, "隨機年化中位": float(np.median(x)) if len(x) else None,
                                      "次數": int(len(x))}
    # ── 營量 v1 並列（主窗）
    z13 = np.load("backtest/resultsYfMix13/eq_main.npz")
    t0, t1 = Wm["w0"], Wm["w1"]
    assert int(z13["w0"]) == t0 and int(z13["w1"]) == t1
    b13 = np.ones(Wm["n"]); b13[t0:t1 + 1] = z13["b13"]; b13[t1 + 1:] = z13["b13"][-1]
    pos13 = pd.read_csv("backtest/resultsYfMix13/positions.csv.gz", dtype={"sid": str}); pos13 = pos13[pos13["cell"] == 13]
    H13 = [set() for _ in range(Wm["n"])]
    for s, tb, ts in zip(pos13["sid"], pos13["t_buy"], pos13["t_sell"]):
        ts = Wm["n"] if ts < 0 else ts
        for t in range(max(tb, t0), min(ts, t1 + 1)):
            H13[t].add(s)
    S["營量v1"] = {nm: dict(zip(("年化", "回落"), map(float, R13.window_stats(b13, 0, Wm["n"], a_, b_ + 1)))) for nm, (a_, b_) in SEGm.items()}
    for M in ("M1", "M2", "M3", "M4"):
        key = picks[M]["格"]; res = RESm[key if M != "M4" else key.replace("M4", "M0")]
        hd = {}; cur = set()
        for t in range(t0, t1 + 1):
            if t in res["hold"]:
                cur = set(res["hold"][t])
            hd[t] = cur
        a_, b_ = SEGm["確認"]
        ov = [len(hd[t] & H13[t]) / len(hd[t]) for t in range(a_, b_ + 1) if hd[t]]
        picks[M]["確認 與營量 v1 重疊率（本格持股中也在營量 v1 的比例，逐日均）"] = float(np.mean(ov)) if ov else None
    # ── 不跳過讀法（描述）與出場敏感度（新規矩 ③）
    for M in ("M1", "M2", "M3", "M4"):
        pk = picks[M]; F, fq, N = pk["F"], pk["頻率"], pk["N"]
        desc = {}
        for Wd, SEGP, nmw in ((Wm, SEGm, "主"), (We, SEGe, "早年")):
            TBn = rank_tables(Wd, F, skip=False)
            sel, _ = select(Wd, TBn, "M0" if M == "M4" else M, F, fq, N)
            res = sim_book(sel, Wd, N); eq = res["eq"]
            if M == "M4":
                w, _ = vol_scale(Wd, sel, N); eq, _, _ = overlay(res["eq"], w, Wd["w0"], Wd["w1"], Wd["n"])
            for nm, (a_, b_) in SEGP.items():
                c, m = R13.window_stats(eq, 0, len(eq), a_, b_ + 1)
                desc[nm] = {"年化": float(c), "回落": float(m)}
        pk["描述_不跳過最近一月（另一讀法）"] = desc
        if pk["確認"]["標籤"] in ("合格", "另列"):
            sens = {}
            TBs = {"主": rank_tables(Wm, F), "早年": rank_tables(We, F)}
            for Wd, SEGP, nmw in ((Wm, SEGm, "主"), (We, SEGe, "早年")):
                sel, _ = select(Wd, TBs[nmw], "M0" if M == "M4" else M, F, fq, N)
                us = sorted({s for v in sel.values() for s in v})
                MA = ma_table(Wd, us)
                for vn, kw in (("(a) 全賣全買", {"mode": "all"}), ("(b) 跌破 MA60 次日開盤賣", {"ma_stop": MA})):
                    res = sim_book(sel, Wd, N, **kw); eq = res["eq"]
                    if M == "M4":
                        w, _ = vol_scale(Wd, sel, N); eq, _, _ = overlay(res["eq"], w, Wd["w0"], Wd["w1"], Wd["n"])
                    for nm, (a_, b_) in SEGP.items():
                        c, m = R13.window_stats(eq, 0, len(eq), a_, b_ + 1)
                        sens[f"{vn}｜{nm}"] = {"年化": float(c), "回落": float(m), "標籤": label(float(c), float(m), *(Zm[nm] if nm in Zm else Ze[nm]))}
            pk["出場敏感度（新規矩 ③，描述）"] = sens
        log(f"[描述 {M}] 不跳過 {desc}｜敏感度 {'有' if '出場敏感度（新規矩 ③，描述）' in pk else '（確認段不合格 ⇒ 不跟）'}")
    np.savez_compressed(os.path.join(OUT, "eq_picks.npz"), **{f"主__{picks[M]['格']}": EQm[picks[M]['格']] for M in picks},
                        **{f"早年__{picks[M]['格']}": EQe[picks[M]['格']] for M in picks})
    rows = []
    for tag, SL, Wd in (("主", SELm, Wm), ("早年", SELe, We)):
        for M in picks:
            k = picks[M]["格"] if M != "M4" else picks[M]["格"].replace("M4", "M0")
            for e, s_ in SL[k].items():
                for i, s in enumerate(s_):
                    rows.append({"世界": tag, "件": M, "格": picks[M]["格"], "換股日": str(Wd["cal"][e].date()), "名次": i + 1, "sid": s})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "picks.csv.gz"), index=False)
    S["沿革（裁定 seq256 §二 1）"] = {"M1 ≈ PREREGF（W1 池剔除極端強勢）": "主窗 +26.14%／−40.27% 另列（K6 重判）", "M3 ≈ PREREGC（W1 池殘差動能）": "主窗 +24.62%／−41.51% 另列（K6 重判）",
                                "讀法": "本件結果不覆蓋 F、C 的標籤，兩者並列；以兩段都判、判準較嚴的一方為準"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
