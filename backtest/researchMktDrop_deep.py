# -*- coding: utf-8 -*-
"""大盤大跌日「當天跌最多的一成」（v1 候選 C）逐筆拆解——描述性統計（⛔ 不計 N、⛔ 不判定、⛔ 不找預測規則）——回測線計算子代理，2026-10-16。
使用者：「所以跌深反彈的最好，那跌深的細部分析一下！」＝ 各種情況各占幾成、各自報酬。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（v1／初測程式只 import 重用，逐股快取只讀）；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_deep [--procs 4]

═══ 讀法（執行者補的都在這裡；寫死於第一次跑之前）═══
 D0 全部重用 researchMktDrop_v1（PREREG大盤大跌後買什麼 seq1）：q2 事件＋「同時只處理一個事件」鎖 ⇒ 同 28 個接受事件（早年 10、2015～2021 7、2022～ 11）；
    世界、母體 R1、C ＝ 母體當天報酬最低 ceil(10%) 檔（同 v1.basket 的穩定排序；程式內核對 sel[BUY] ＝ v1.basket(M, t, "C")）、
    主出場（加權收盤 ≥ 事件前一日收盤 ⇒ 隔天開盤賣；⛔ 不設天數；壞根前收盤強制、下市最後收盤）、成本 0.585%——逐股出場直接讀 v1 快取 packs 的 SP／SX／SK
    每筆（事件×股）淨報酬 ＝ (賣價 ÷ 買價)(1 − 0.585%) − 1 ⇒ 同事件等權平均 ≡ v1 event_rows 的 C 主出場報酬（程式內對帳，差 ＞ 1e-8 ⇒ 停）
    持有天數 ＝ 賣出日曆位置 − 進場日曆位置（交易日）
 D1 分析單位 ＝ 買得到的 C 檔次（事件×股）；買不到的（隔天沒成交、開盤漲停鎖死、隔天壞根）另表照報。
    每組報 檔次、占比（該段買得到 C 檔次中）、母體占比（同段 R1 母體全部股日中同組的比例，看 C 偏向哪裡）、平均、中位、勝率（淨報酬 ＞ 0）、
    貢獻事件數、事件群集 bootstrap 95% CI（段內事件有放回重抽 2000 次，組平均 ＝ 重抽事件的組報酬和 ÷ 組檔次和）、
    事件內相對 ＝ 每個有該組的事件「組平均 − 同事件 C 全體平均」再對事件等權平均（去掉事件本身好壞），及事件內相對 ＞ 0 的事件比例
    段 ＝ 2006～2014、2015～2021、2022～、全部（全部的 CI 重抽 28 個事件）
 D2 特徵（⛔ 只描述；t ＝ 事件日；k ＝ 該股 t 的有效 K 棒；還原價 ＝ research11.load_bars；窗內有壞根（seq335）⇒ 該特徵缺）：
    ① 跌停 ＝ load_bars dn（未還原收盤 ＝ 跌停價；2015-06-01 前 7%、之後 10%；還原事件根不判）；跌 ≥7% 未跌停；其餘
       全市場名次 ＝ 當天報酬在 R1 母體由低到高的名次 ÷ 母體檔數：≤1%、1～5%、5～10%；當天跌幅 ≤−9%、−9～−6%、−6～−4%、＞−4%
    ② 前 20／60 日漲幅 ＝ c[k−1] ÷ c[k−21]／c[k−61] − 1（大跌前一天為止）；距 52 週高 ＝ c[k−1] ÷ max(c[k−250..k−1]) − 1；MA60 ＝ c[k−1] ≥ 平均(c[k−60..k−1])
    ③ 市值 ＝ 未還原收盤[t] × 股數（stocks csv shares 欄，往前延用最近值、⛔ 不往回補；早年 2006 全缺、2007～2011 只部分有）；
       前 20 日均成交額 ＝ 平均 amount[k−20..k−1]；五分位切點 ＝ 該事件日 R1 母體（Q1 最小）；股價 ＝ 未還原收盤[t]：＜20、20～50、50～150、≥150
    ④ 月營收 ＝ researchExit5.load_revenue（早年＋主世界 revenue_hist 合併、主世界優先）／avail_pos（≤2025-12 期次月 10 日後、≥2026-01 期 15 日後第一個交易日）／
       rev_events：可得日 ≤ t 的最後一期 ⇒ 年增（＞+20%、0～20%、≤0、缺）、是否創 24 月新高（不含當期的前 24 期都要有）
       營量 ＝ v1 f_flags 的 ACH（營量 v1 正式訊號已達成）：事件日當天是訊號；近 60 根（含 t）有訊號（＝營量持有中）；
       營飆 ＝ 近 120 根（含 t）有 ACH 訊號 ∧ 該訊號日 0050 還原收盤 ＞ 自身 200 日均（營飆 v1 大盤閘；執行者讀法）
    ⑤ 三大法人 ＝ stocks_inst total（股）t 當天：買超／賣超（另標賣超 ≥ 當天成交股數 10%）；早年 2012-05 前沒有 ⇒ 早年段全缺
       融資使用率 ＝ stocks_margin m_balance ÷ m_limit（t 當天）：m_limit ≤ 0 ⇒ 不能融資；＜5%、5～15%、≥15%；早年沒有 ⇒ 全缺
       處置 ＝ meta/disposal.csv 普通股區間含 t（2010-12 起有資料）；注意 ＝ meta/attention.csv t 當天或前 9 根內有（2011-01-03 起有資料）⇒ 早年段幾乎全缺
    ⑥ 產業 ＝ v1 packs 的 ind（industry_pit pit 版＋營收彙總表後備，PRE.PIT，t 當天；不排除「其他」）；每段 ≥10 檔次才列
    ⑦ 隔天開盤跳空 ＝ 還原開盤[k+1] ÷ 還原收盤[k] − 1（＝ 買價 ÷ t 收盤 − 1）：≤−3%（開低多）、−3～−1%、−1～+1%（開平）、＞+1%（開高）；
       開盤跌停 ＝ 未還原開盤[k+1] ＝ 跌停價（k+1 是還原事件根不判）——開盤跌停買得到（賣方多）；買不到原因另表
    ⑧ 結果分布：淨報酬分位、賺錢比例、持有天數分位、出場種類；報酬前 10% ＝ (a) 全部檔次合併的第 90 百分位以上 (b) 事件內第 90 百分位以上；
       各特徵組在前 10% 的占比 vs 全體占比
 D3 必附：事件只有 28 次、同事件內檔次高度相關 ⇒ 看 CI 與貢獻事件數；差異多半不顯著；描述性、不計 N、不判定、⛔ 不是買賣建議
輸出 backtest/resultsMktDrop/deep/：MktDrop_deep.json、groups.csv、c_rows.csv、events_c.csv、dist.csv、top10.csv、unbuyable.csv、run.log；大檔 ~/mktdropwork/deep/
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/deep")
WORK = os.path.expanduser("~/mktdropwork/deep")
V1WORK = os.path.expanduser("~/mktdropwork/v1")
V1ER = os.path.join(REPO, "backtest/resultsMktDrop/v1/event_rows.csv")
TIME = "2026-10-16（台北；讀法寫死、第一次跑之前）"
NBOOT = 2000
SEED = 2026101601
SEGS = ["2006～2014", "2015～2021", "2022～", "全部"]
NOTES = ["描述性：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議；看過 v1 結果才拆 ⇒ 任何「看起來有差」都只是待驗的線索",
         "事件只有 28 次（早年 10、2015～2021 7、2022～ 11），同一事件內的檔次高度相關（一起漲一起跌）⇒ 看 CI（事件群集重抽）與貢獻事件數；差異多半不顯著",
         "收復才賣的勝率有一部分來自規則本身（等多久都等）",
         "早年（2006～2014）沒有法人、融資資料；處置／注意 2011 起才有；市值股數 2006 全缺、2007～2011 部分有",
         "早年含減資假飆股約 0.3%（剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；2005-01～2007-06 只有上市",
         "2015-06-01 前漲跌幅 7% ⇒ 早年「跌 ≥7% 未跌停」幾乎不存在",
         "成本：個股 0.585% 來回；未含滑價"]
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 逐股特徵（Pool；fork 繼承 _G）═════════════
def feat_job(a):
    wn, sid, poss = a
    from backtest import data as D
    from backtest import research11 as R
    from backtest import researchExit5 as EX5
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    idx = B["idx"].astype(np.int64); nb = len(idx)
    c = np.asarray(B["c"], float); o = np.asarray(B["o"], float); amt = np.asarray(B["amt"], float); rc = np.asarray(B["rc"], float)
    dn = np.asarray(B["dn"], bool); skip = np.asarray(B["skip"], bool); nxb = np.asarray(B["next_bad"])
    vol = B["df"]["volume"].to_numpy(float)[idx]
    bad = np.asarray(nxb[:nb] == np.arange(nb), bool)
    for p in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p, "left"))
        if k < nb:
            bad[k] = True
    CB = np.r_[0, np.cumsum(bad)]

    def clean(a_, b_):          # c[a_]..c[b_] 可比：a_ ≥ 0 且 (a_, b_] 無壞根
        return a_ >= 0 and b_ < nb and CB[b_ + 1] - CB[a_ + 1] == 0
    raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "open", "shares"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    ro = pd.to_numeric(raw["open"], errors="coerce").reindex(cal).to_numpy(float)
    sh = pd.to_numeric(raw["shares"], errors="coerce").ffill().reindex(cal, method="ffill").to_numpy(float)
    inst = {}; marg = {}
    fp = os.path.join(W["data"], "stocks_inst", f"{sid}.csv")
    if os.path.exists(fp):
        d_ = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "foreign", "total"])
        inst = {dd: (float(t_), float(f_)) for dd, t_, f_ in zip(d_["date"], pd.to_numeric(d_["total"], errors="coerce"), pd.to_numeric(d_["foreign"], errors="coerce"))}
    fp = os.path.join(W["data"], "stocks_margin", f"{sid}.csv")
    if os.path.exists(fp):
        d_ = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "m_balance", "m_limit"])
        marg = {dd: (float(b_), float(l_)) for dd, b_, l_ in zip(d_["date"], pd.to_numeric(d_["m_balance"], errors="coerce"), pd.to_numeric(d_["m_limit"], errors="coerce"))}
    rev, rly, AV = _G["REV"]
    rev_ev = EX5.rev_events(sid, rev, rly, AV, n0)
    rA = np.array([e[0] for e in rev_ev], np.int64)
    att = _G["ATT"].get(sid, set()); disp = W["disp"].get(sid, [])
    att_pos = np.array(sorted(int(x) for x in (cal.searchsorted(d) for d in att) if x < n0), np.int64) if att else np.array([], np.int64)
    out = []
    cut = pd.Timestamp("2015-06-01")
    for p in poss:
        k = int(np.searchsorted(idx, p))
        if k >= nb or idx[k] != p:
            out.append({"p": p, "sid": sid, "err": "no bar"}); continue
        dt = cal[p]; ds = str(dt.date())
        f = {"p": p, "sid": sid, "ret1_chk": c[k] / c[k - 1] - 1 if k > 0 else np.nan, "dn": bool(dn[k]), "rc": rc[k]}
        f["ret20p"] = c[k - 1] / c[k - 21] - 1 if clean(k - 21, k - 1) else np.nan
        f["ret60p"] = c[k - 1] / c[k - 61] - 1 if clean(k - 61, k - 1) else np.nan
        f["d52"] = c[k - 1] / np.max(c[k - 250:k]) - 1 if clean(k - 250, k - 1) else np.nan
        f["ma60"] = (float(c[k - 1] >= np.mean(c[k - 60:k])) if clean(k - 60, k - 1) else np.nan)
        f["amt20"] = float(np.mean(amt[k - 20:k])) if k >= 20 else np.nan
        f["mcap"] = rc[k] * sh[p] if np.isfinite(sh[p]) and sh[p] > 0 else np.nan
        # 營收
        j = int(np.searchsorted(rA, p, "right")) - 1
        if j >= 0:
            f["yoy"] = rev_ev[j][1]; f["hi24"] = (np.nan if rev_ev[j][2] is None else float(rev_ev[j][2])); f["rev_age"] = int(p - rev_ev[j][0])
        else:
            f["yoy"] = np.nan; f["hi24"] = np.nan; f["rev_age"] = np.nan
        # 法人、融資
        if ds in inst and np.isfinite(inst[ds][0]):
            f["inst"] = inst[ds][0]; f["inst_r"] = inst[ds][0] / vol[k] if vol[k] > 0 else np.nan; f["foreign"] = inst[ds][1]
        else:
            f["inst"] = np.nan; f["inst_r"] = np.nan; f["foreign"] = np.nan
        f["has_inst_file"] = bool(inst)
        if ds in marg:
            b_, l_ = marg[ds]
            f["mutil"] = (b_ / l_) if (np.isfinite(l_) and l_ > 0 and np.isfinite(b_)) else -1.0     # −1 ＝ 不能融資
        else:
            f["mutil"] = np.nan
        f["has_marg_file"] = bool(marg)
        # 處置、注意
        f["disp"] = (float(any(s_ <= dt <= e_ for s_, e_ in disp)) if dt >= pd.Timestamp("2010-12-14") else np.nan)
        if dt >= pd.Timestamp("2011-01-03"):
            lo = idx[max(0, k - 9)]
            f["att_t"] = float(p in set(att_pos.tolist())) if len(att_pos) else 0.0
            f["att10"] = float(np.sum((att_pos >= lo) & (att_pos <= p)))
        else:
            f["att_t"] = np.nan; f["att10"] = np.nan
        # 隔天開盤
        if k + 1 < nb and idx[k + 1] == p + 1:
            f["gap"] = o[k + 1] / c[k] - 1
            if not skip[k + 1] and np.isfinite(rc[k]) and rc[k] > 0 and np.isfinite(ro[p + 1]):
                lim = 0.07 if cal[p + 1] < cut else 0.10
                f["open_dn"] = float(abs(ro[p + 1] - R.limit_price(rc[k], False, lim)) < 1e-6)
                f["open_up"] = float(abs(ro[p + 1] - R.limit_price(rc[k], True, lim)) < 1e-6)
            else:
                f["open_dn"] = np.nan; f["open_up"] = np.nan
            f["bad_k1"] = bool(bad[k + 1])
        else:
            f["gap"] = np.nan; f["open_dn"] = np.nan; f["open_up"] = np.nan; f["bad_k1"] = False
        f["next_is_t1"] = bool(k + 1 < nb and idx[k + 1] == p + 1)
        out.append(f)
    return sid, out


# ═════════════ 分組 ═════════════
def cut_lab(x, edges, labs):
    if not np.isfinite(x):
        return "缺"
    for e, l_ in zip(edges, labs):
        if x <= e:
            return l_
    return labs[-1]


def add_groups(df):
    """⇒ 每列加上各特徵的組名（df 可以是 C 或母體）。回傳 [(類別, 特徵, 欄, 組順序)]。"""
    G = []

    def put(cat, name, col, vals, order):
        df[col] = vals; G.append((cat, name, col, order))
    r1 = df["ret1"].to_numpy(float)
    put("1 跌幅深淺", "當天跌停", "g_lim",
        np.where(df["dn"].to_numpy(bool), "跌停", np.where(r1 <= -0.07, "跌≥7%未跌停", "其餘")), ["跌停", "跌≥7%未跌停", "其餘"])
    pr = df["prank"].to_numpy(float)
    put("1 跌幅深淺", "全市場名次（母體由低到高）", "g_pr", np.where(pr <= 0.01, "最差1%", np.where(pr <= 0.05, "1～5%", np.where(pr <= 0.10, "5～10%", "＞10%"))),
        ["最差1%", "1～5%", "5～10%", "＞10%"])
    put("1 跌幅深淺", "當天跌幅", "g_r1", [cut_lab(x, [-0.09, -0.06, -0.04], ["≤−9%", "−9～−6%", "−6～−4%", "＞−4%"]) for x in r1],
        ["≤−9%", "−9～−6%", "−6～−4%", "＞−4%"])
    put("2 大跌前走勢", "前20日漲幅", "g_r20", [cut_lab(x, [-0.10, 0.0, 0.10], ["≤−10%", "−10～0%", "0～+10%", "＞+10%"]) for x in df["ret20p"]],
        ["≤−10%", "−10～0%", "0～+10%", "＞+10%", "缺"])
    put("2 大跌前走勢", "前60日漲幅", "g_r60", [cut_lab(x, [-0.15, 0.0, 0.20], ["≤−15%（原本就弱）", "−15～0%", "0～+20%", "＞+20%（原本強勢）"]) for x in df["ret60p"]],
        ["≤−15%（原本就弱）", "−15～0%", "0～+20%", "＞+20%（原本強勢）", "缺"])
    put("2 大跌前走勢", "距52週高（大跌前一天）", "g_d52", [cut_lab(x, [-0.30, -0.10], ["≤−30%（離高點遠）", "−30～−10%", "＞−10%（近高點）"]) for x in df["d52"]],
        ["≤−30%（離高點遠）", "−30～−10%", "＞−10%（近高點）", "缺"])
    put("2 大跌前走勢", "大跌前一天在MA60之上", "g_ma60", [("缺" if not np.isfinite(x) else ("是" if x > 0.5 else "否")) for x in df["ma60"]], ["是", "否", "缺"])
    put("3 規模流動性", "市值五分位（母體切點）", "g_mcap", df["q_mcap"].fillna("缺").to_numpy(), ["Q1最小", "Q2", "Q3", "Q4", "Q5最大", "缺"])
    put("3 規模流動性", "前20日均成交額五分位（母體切點）", "g_amt", df["q_amt"].fillna("缺").to_numpy(), ["Q1最小", "Q2", "Q3", "Q4", "Q5最大", "缺"])
    put("3 規模流動性", "股價（未還原）", "g_px", [cut_lab(x, [20, 50, 150], ["＜20", "20～50", "50～150", "≥150"]) for x in df["rc"]], ["＜20", "20～50", "50～150", "≥150", "缺"])
    put("4 基本面", "最近一期月營收年增", "g_yoy", [cut_lab(x, [0.0, 0.20], ["≤0", "0～+20%", "＞+20%"]) for x in df["yoy"]], ["＞+20%", "0～+20%", "≤0", "缺"])
    put("4 基本面", "最近一期月營收創24月新高", "g_hi24", [("缺" if not np.isfinite(x) else ("是" if x > 0.5 else "否")) for x in df["hi24"]], ["是", "否", "缺"])
    put("4 基本面", "營量／營飆", "g_yl", np.where(df["yl_t"].to_numpy(bool), "事件日當天營量訊號",
                                             np.where(df["yl60"].to_numpy(bool) & df["yf120"].to_numpy(bool), "營量＋營飆持有中",
                                                      np.where(df["yl60"].to_numpy(bool), "只營量持有中（近60根）",
                                                               np.where(df["yf120"].to_numpy(bool), "只營飆持有中（近120根、閘開）", "都不是")))),
        ["事件日當天營量訊號", "營量＋營飆持有中", "只營量持有中（近60根）", "只營飆持有中（近120根、閘開）", "都不是"])
    ir = df["inst_r"].to_numpy(float); it = df["inst"].to_numpy(float)
    put("5 籌碼", "三大法人（事件日）", "g_inst",
        np.where(~np.isfinite(it), "缺", np.where(it > 0, "買超", np.where(it == 0, "零", np.where(np.isfinite(ir) & (ir <= -0.10), "賣超≥成交量10%", "賣超＜10%")))),
        ["買超", "零", "賣超＜10%", "賣超≥成交量10%", "缺"])
    mu = df["mutil"].to_numpy(float)
    put("5 籌碼", "融資使用率（事件日）", "g_mu", np.where(~np.isfinite(mu), "缺", np.where(mu < 0, "不能融資", np.where(mu < 0.05, "＜5%", np.where(mu < 0.15, "5～15%", "≥15%")))),
        ["＜5%", "5～15%", "≥15%", "不能融資", "缺"])
    dp = df["disp"].to_numpy(float); a10 = df["att10"].to_numpy(float)
    put("5 籌碼", "處置／注意", "g_da", np.where(~np.isfinite(dp) | ~np.isfinite(a10), "缺", np.where(dp > 0.5, "處置中", np.where(a10 > 0, "近10根有注意", "都沒有"))),
        ["處置中", "近10根有注意", "都沒有", "缺"])
    put("6 產業", "產業（industry_pit）", "g_ind", df["ind"].fillna("無產業").to_numpy(), None)
    gp = df["gap"].to_numpy(float)
    put("7 隔天開盤", "隔天開盤跳空（買價÷t收盤−1）", "g_gap", [cut_lab(x, [-0.03, -0.01, 0.01], ["≤−3%（開低多）", "−3～−1%", "−1～+1%（開平）", "＞+1%（開高）"]) for x in gp],
        ["≤−3%（開低多）", "−3～−1%", "−1～+1%（開平）", "＞+1%（開高）", "缺"])
    od = df["open_dn"].to_numpy(float)
    put("7 隔天開盤", "隔天開盤跌停", "g_odn", np.where(~np.isfinite(od), "缺（隔天是還原事件根等）", np.where(od > 0.5, "開盤跌停", "沒有")), ["開盤跌停", "沒有", "缺（隔天是還原事件根等）"])
    return G


def boot_ci(sums, cnts, B, rng):
    E = len(sums)
    if E == 0 or cnts.sum() == 0:
        return np.nan, np.nan
    ix = rng.integers(0, E, (B, E))
    S = sums[ix].sum(1); N = cnts[ix].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(N > 0, S / N, np.nan)
    return float(np.nanpercentile(m, 2.5)), float(np.nanpercentile(m, 97.5))


def group_table(C, P, G, log):
    rows = []; ctr = 0
    for sg in SEGS:
        Cs = C if sg == "全部" else C[C["段"] == sg]
        Ps = P if sg == "全部" else P[P["段"] == sg]
        evs = sorted(Cs["ev"].unique()); E = len(evs); evi = {e: i for i, e in enumerate(evs)}
        ei = Cs["ev"].map(evi).to_numpy(); net = Cs["net"].to_numpy(float)
        ev_mean = np.bincount(ei, net, E) / np.bincount(ei, None, E)
        nC = len(Cs); nP = len(Ps)
        for cat, name, col, order in G:
            vc = Cs[col].astype(str).to_numpy()
            labs = order if order is not None else [l_ for l_, n_ in pd.Series(vc).value_counts().items() if n_ >= 10]
            pv = Ps[col].astype(str).value_counts()
            for g in labs:
                m = vc == g; n = int(m.sum())
                ctr += 1
                if n == 0:
                    rows.append({"段": sg, "類別": cat, "特徵": name, "組": g, "檔次": 0, "占比": 0.0, "母體占比": float(pv.get(g, 0) / nP) if nP else np.nan})
                    continue
                x = net[m]
                sums = np.bincount(ei[m], x, E); cnts = np.bincount(ei[m], None, E)
                lo, hi = boot_ci(sums, cnts, NBOOT, np.random.default_rng([SEED, ctr]))
                has = cnts > 0
                rel = sums[has] / cnts[has] - ev_mean[has]
                rows.append({"段": sg, "類別": cat, "特徵": name, "組": g, "檔次": n, "占比": n / nC, "母體占比": float(pv.get(g, 0) / nP) if nP else np.nan,
                             "平均": float(x.mean()), "中位": float(np.median(x)), "勝率": float(np.mean(x > 0)),
                             "貢獻事件數": int(has.sum()), "段事件數": E, "CI95_低（事件群集）": lo, "CI95_高": hi,
                             "事件內相對（組−同事件C，事件等權）": float(rel.mean()), "事件內相對＞0事件比例": float(np.mean(rel > 0)),
                             "平均持有天數": float(Cs["hold"].to_numpy(float)[m].mean())})
    T = pd.DataFrame(rows)
    log(f"[分組] {len(T)} 列")
    return T


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    from multiprocessing import Pool
    from backtest import data as D
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop as MD
    from backtest import researchExit5 as EX5
    MD.SEGS = V1.SEGS_V1
    S = {"件": "大盤大跌日 C（當天跌最多一成）逐筆拆解（描述性、不計 N、不判定）", "讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法": "見程式檔頭 D0～D3",
         "必附": NOTES, "重用": "researchMktDrop_v1（PREREG大盤大跌後買什麼 seq1）＋ v1 逐股快取 ~/mktdropwork/v1/packs_*.pkl（只讀）", "閘": {}}
    IXmd = MD.load_index(log)
    df = IXmd["df"]
    EV = V1.index_events(df)
    ft = np.flatnonzero(EV["FIRST"]["q2"])
    if not np.array_equal(EV["rec"][ft], IXmd["rec"][ft]):
        raise SystemExit("⛔ q2 收復列與初測 rec 不同")
    S["指數"] = {"origin/main sha": IXmd["sha"], "q2 接受事件（全部）": int(EV["ACC"]["q2"].sum())}
    # 營收（早年＋主合併、主優先）
    rev_e, rly_e, info_e = EX5.load_revenue(MD.DB.WORLDS["早年"]["data"])
    rev_m, rly_m, info_m = EX5.load_revenue(MD.DB.WORLDS["主"]["data"])
    rev = rev_m.combine_first(rev_e).sort_index(); rly = rly_m.combine_first(rly_e).sort_index()
    S["營收"] = {"早年": info_e, "主": info_m, "合併期別": [str(rev.index[0]), str(rev.index[-1])]}
    PRE_rev = MD.PRE.load_rev(MD.IND_DATA)
    MD._G["PIT"] = MD.PRE.PIT(MD.IND_DATA, PRE_rev[2])
    ER1 = pd.read_csv(V1ER)
    ER1 = ER1[(ER1["定義"] == "q2") & (ER1["候選"] == "C") & (ER1["出場"] == "主")].set_index("日期")
    CROWS = []; PROWS = []; UNB = []; EVROWS = []
    for wn in ("早年", "主"):
        W = MD.load_world(wn, IXmd, log); MD._G[wn] = W; _G[wn] = W
        PK = pickle.load(open(os.path.join(V1WORK, f"packs_{wn}.pkl"), "rb")); log(f"[逐股 {wn}] 讀 v1 快取")
        EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
        M = MD.assemble(W, PK, EP, log)
        S["閘"][wn] = {"營量": MD.f_flags(W, PK, M, log)}
        cal = W["cal"]; n0 = W["n0"]
        D.DATA = W["data"]; _G["ATT"] = D.load_attention_dates()
        _G["REV"] = (rev, rly, EX5.avail_pos(list(rev.index), cal))
        datepos = {d: j for j, d in enumerate(cal)}
        segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
        evs = []
        for i in np.flatnonzero(EV["ACC"]["q2"]):
            p = datepos.get(df["date"].iloc[i])
            if p is not None and p + 1 < n0 and segof(p) is not None:
                evs.append((p, i))
        # 營飆閘：0050 還原收盤 ＞ 200 日均
        bch = pd.Series(np.asarray(W["bench"], float)).ffill()
        gate = (bch > bch.rolling(200, min_periods=200).mean()).to_numpy(bool)
        ACH = M["ACH"]; ACHG = ACH & gate[None, :]
        # 母體與 C
        need = {}; EVINFO = {}
        for p, i in evs:
            m = M["MEM"][:, p] & np.isfinite(M["RET"][:, p]); rows = np.flatnonzero(m)
            if len(rows) < 20:
                raise SystemExit(f"⛔ {cal[p].date()} 母體 ＜ 20")
            v = M["RET"][rows, p]; ns = int(np.ceil(0.10 * len(rows)))
            o_ = np.argsort(v, kind="stable"); rank = np.empty(len(rows), np.int64); rank[o_] = np.arange(len(rows))
            sel = rows[o_[:ns]]
            Iv1, nsel_v1, _ = V1.basket(M, p, "C")
            if nsel_v1 != ns or not np.array_equal(np.sort(sel[M["BUY"][sel, p]]), np.sort(Iv1)):
                raise SystemExit(f"⛔ {cal[p].date()} C 名單與 v1.basket 不同")
            EVINFO[p] = (i, rows, rank, sel)
            for r in rows:
                need.setdefault(M["sids"][r], []).append(p)
        fp = os.path.join(WORK, f"feat_{wn}.pkl")
        if os.path.exists(fp):
            FT = pickle.load(open(fp, "rb")); log(f"[特徵 {wn}] 讀快取 {fp}")
        else:
            t0 = time.time(); FT = {}
            with Pool(a.procs) as pool:
                for j, (s, out) in enumerate(pool.imap_unordered(feat_job, [(wn, s, sorted(ps)) for s, ps in need.items()], chunksize=4)):
                    FT[s] = out
                    if j % 300 == 0:
                        log(f"[特徵 {wn}] {j}/{len(need)}｜{time.time() - t0:.0f}s")
            pickle.dump(FT, open(fp, "wb"), protocol=5)
        FD = {}
        nerr = 0
        for s, out in FT.items():
            if out is None:
                nerr += 1; continue
            for f in out:
                if "err" in f:
                    nerr += 1; continue
                FD[(s, f["p"])] = f
        S["閘"][wn]["特徵缺（無 K 棒／load_bars 無）"] = nerr
        rix = {s: r for r, s in enumerate(M["sids"])}
        maxchk = 0.0
        for p, (i, rows, rank, sel) in EVINFO.items():
            sg = segof(p); ev = str(cal[p].date()); nm = len(rows)
            selset = set(int(x) for x in sel)
            # 五分位（母體切點）
            mc = np.array([FD.get((M["sids"][r], p), {}).get("mcap", np.nan) for r in rows], float)
            am = np.array([FD.get((M["sids"][r], p), {}).get("amt20", np.nan) for r in rows], float)
            labs5 = ["Q1最小", "Q2", "Q3", "Q4", "Q5最大"]

            def q5(x):
                out_ = np.full(len(x), None, object); ok = np.isfinite(x)
                if ok.sum() >= 10:
                    out_[ok] = pd.qcut(pd.Series(x[ok]).rank(method="first"), 5, labels=labs5).astype(str).to_numpy()
                return out_
            qm = q5(mc); qa = q5(am)
            pk_ind = {}
            for jj, r in enumerate(rows):
                s = M["sids"][r]; f = FD.get((s, p))
                if f is None:
                    continue
                pk = PK[s]; kk = int(np.searchsorted(pk["idx"], p))
                ind = pk["ind"][kk] if kk < len(pk["idx"]) and pk["idx"][kk] == p else None
                ret1 = float(M["RET"][r, p])
                maxchk = max(maxchk, abs(ret1 - f["ret1_chk"]) if np.isfinite(f["ret1_chk"]) else 0.0)
                base = {"段": sg, "ev": ev, "sid": s, "ret1": ret1, "prank": (rank[jj] + 1) / nm, "q_mcap": qm[jj], "q_amt": qa[jj], "ind": ind,
                        "yl_t": bool(ACH[r, p]), "yl60": bool(ACH[r, max(0, p - 59):p + 1].any()), "yf120": bool(ACHG[r, max(0, p - 119):p + 1].any()),
                        **{k_: f[k_] for k_ in ("dn", "rc", "ret20p", "ret60p", "d52", "ma60", "amt20", "mcap", "yoy", "hi24", "rev_age", "inst", "inst_r", "foreign",
                                                "mutil", "disp", "att_t", "att10", "gap", "open_dn", "open_up")}}
                PROWS.append(base)
                if r in selset:
                    buy = bool(M["BUY"][r, p])
                    row = {**base, "世界": wn, "買得到": buy}
                    if buy:
                        sp = int(M["SP"]["主"][r, p]); sx = float(M["SX"]["主"][r, p]); kd = int(M["SK"]["主"][r, p]); bp = float(M["BP"][r, p])
                        g_ = sx / bp - 1.0
                        row.update({"買價": bp, "賣價": sx, "毛報酬": g_, "net": (1 + g_) * (1 - V1.COST_STK) - 1, "hold": sp - (p + 1),
                                    "出場種類": MD.KIND.get(kd, str(kd)), "賣出日": str(cal[min(sp, n0 - 1)].date())})
                    else:
                        e = p + 1
                        trd = bool(W["TRD"][W["ix"][s], e]); upl = bool(W["UPL"][W["ix"][s], e]); ov = W["O"][W["ix"][s], e]
                        why = ("隔天沒成交" if not trd else "隔天開盤漲停鎖死" if upl else "隔天開盤價無效" if not (np.isfinite(ov) and ov > 0) else "隔天是壞根（缺口≥5日等）")
                        row.update({"買不到原因": why})
                        UNB.append({"段": sg, "ev": ev, "sid": s, "原因": why, "ret1": ret1})
                    CROWS.append(row)
            # 對帳 v1
            cr = [x for x in CROWS if x["ev"] == ev and x["買得到"]]
            mine = float(np.mean([x["net"] for x in cr])) if cr else np.nan
            ref = float(ER1.loc[ev, "報酬"]) if ev in ER1.index else np.nan
            if not (abs(mine - ref) < 1e-8):
                raise SystemExit(f"⛔ {ev} C 平均 {mine} ≠ v1 {ref}")
            nets = np.array([x["net"] for x in cr]); hs = np.array([x["hold"] for x in cr])
            EVROWS.append({"段": sg, "事件日": ev, "指數報酬": float(EV["r"][i]), "母體檔數": nm, "C 選出檔數": len(sel), "買到檔數": len(cr),
                           "C 當天報酬最高（第10%邊界）": float(np.max(M["RET"][sel, p])), "C 當天跌停比例": float(np.mean([FD[(M["sids"][r], p)]["dn"] for r in sel if (M["sids"][r], p) in FD])),
                           "平均淨報酬（＝v1）": mine, "中位": float(np.median(nets)), "勝率": float(np.mean(nets > 0)), "最好": float(nets.max()), "最差": float(nets.min()),
                           "持有天數中位": float(np.median(hs)), "持有天數最長": int(hs.max()), "v1 報酬": ref})
        S["閘"][wn]["當天報酬 RET vs load_bars 最大差"] = maxchk
        if maxchk > 1e-9:
            raise SystemExit(f"⛔ {wn} 當天報酬對不上 {maxchk}")
        log(f"[{wn}] 完｜C 檔次累計 {len(CROWS)}｜{time.time() - T0:.0f}s")
        del M, PK, FT, FD
    C_all = pd.DataFrame(CROWS); P = pd.DataFrame(PROWS); U = pd.DataFrame(UNB); EVT = pd.DataFrame(EVROWS)
    C = C_all[C_all["買得到"]].copy()
    G = add_groups(C); add_groups(P)
    T = group_table(C, P, G, log)
    # 全體列
    base_rows = []
    for sg in SEGS:
        Cs = C if sg == "全部" else C[C["段"] == sg]; Ca = C_all if sg == "全部" else C_all[C_all["段"] == sg]
        x = Cs["net"].to_numpy(float); h = Cs["hold"].to_numpy(float)
        evm = Cs.groupby("ev")["net"].mean()
        evs = sorted(Cs["ev"].unique()); evi = {e: i_ for i_, e in enumerate(evs)}; ei = Cs["ev"].map(evi).to_numpy()
        lo, hi = boot_ci(np.bincount(ei, x, len(evs)), np.bincount(ei, None, len(evs)).astype(float), NBOOT, np.random.default_rng([SEED, 0, SEGS.index(sg)]))
        q = np.percentile(x, [5, 10, 25, 50, 75, 90, 95]); qh = np.percentile(h, [10, 25, 50, 75, 90])
        base_rows.append({"段": sg, "事件數": len(evs), "C 選出檔次": len(Ca), "買到檔次": len(Cs), "買不到比例": float(1 - len(Cs) / len(Ca)),
                          "每事件買到檔數_最少": int(Cs.groupby("ev").size().min()), "每事件買到檔數_最多": int(Cs.groupby("ev").size().max()),
                          "每筆平均": float(x.mean()), "CI95_低（事件群集）": lo, "CI95_高": hi, "事件等權平均（＝v1 平均報酬）": float(evm.mean()),
                          "中位": float(np.median(x)), "勝率": float(np.mean(x > 0)),
                          **{f"P{int(pp)}": float(v) for pp, v in zip([5, 10, 25, 50, 75, 90, 95], q)},
                          "≤−20%比例": float(np.mean(x <= -0.20)), "≥+20%比例": float(np.mean(x >= 0.20)), "≥+50%比例": float(np.mean(x >= 0.50)),
                          "持有天數P10": float(qh[0]), "持有天數P25": float(qh[1]), "持有天數中位": float(qh[2]), "持有天數P75": float(qh[3]), "持有天數P90": float(qh[4]),
                          "持有天數最長": int(h.max()), "平均持有天數": float(h.mean()),
                          **{f"出場_{k_}": float(v) for k_, v in Cs["出場種類"].value_counts(normalize=True).items()}})
    DIST = pd.DataFrame(base_rows)
    # 前 10%
    thr = np.percentile(C["net"], 90)
    C["top_all"] = C["net"] >= thr
    C["top_ev"] = C.groupby("ev")["net"].transform(lambda s: s >= np.percentile(s, 90))
    trow = []
    for cat, name, col, order in G:
        vc = C[col].astype(str)
        labs = order if order is not None else [l_ for l_, n_ in vc.value_counts().items() if n_ >= 10]
        for g in labs:
            m = (vc == g).to_numpy()
            if not m.any():
                continue
            trow.append({"類別": cat, "特徵": name, "組": g, "全體占比": float(m.mean()),
                         "前10%占比（全部合併門檻）": float(m[C["top_all"].to_numpy()].mean()), "前10%占比（事件內）": float(m[C["top_ev"].to_numpy()].mean()),
                         "差（全部合併−全體）": float(m[C["top_all"].to_numpy()].mean() - m.mean()), "差（事件內−全體）": float(m[C["top_ev"].to_numpy()].mean() - m.mean()),
                         "前10%（全部合併）各段檔次": "／".join(f"{sg} {int((C['top_all'] & (C['段'] == sg)).sum())}" for sg in SEGS[:3])})
    TOP = pd.DataFrame(trow)
    UT = (U.groupby(["段", "原因"]).size().rename("檔次").reset_index() if len(U) else pd.DataFrame(columns=["段", "原因", "檔次"]))
    # 存檔
    T.to_csv(os.path.join(OUT, "groups.csv"), index=False, float_format="%.6g", encoding="utf-8")
    keepc = ["段", "ev", "sid", "ind", "ret1", "prank", "dn", "rc", "ret20p", "ret60p", "d52", "ma60", "amt20", "mcap", "q_mcap", "q_amt", "yoy", "hi24", "rev_age",
             "yl_t", "yl60", "yf120", "inst", "inst_r", "foreign", "mutil", "disp", "att_t", "att10", "gap", "open_dn", "買得到", "買不到原因", "買價", "賣價", "毛報酬", "net", "hold",
             "出場種類", "賣出日"]
    C_all.merge(C[["ev", "sid", "top_all", "top_ev"]], on=["ev", "sid"], how="left")[[c_ for c_ in keepc if c_ in C_all.columns] + ["top_all", "top_ev"]] \
        .rename(columns={"ev": "事件日", "net": "淨報酬", "hold": "持有天數"}).to_csv(os.path.join(OUT, "c_rows.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EVT.to_csv(os.path.join(OUT, "events_c.csv"), index=False, float_format="%.6g", encoding="utf-8")
    DIST.to_csv(os.path.join(OUT, "dist.csv"), index=False, float_format="%.6g", encoding="utf-8")
    TOP.to_csv(os.path.join(OUT, "top10.csv"), index=False, float_format="%.6g", encoding="utf-8")
    UT.to_csv(os.path.join(OUT, "unbuyable.csv"), index=False, encoding="utf-8")
    S["全體（C 買到檔次）"] = DIST.to_dict("records"); S["逐事件"] = EVT.to_dict("records"); S["買不到"] = UT.to_dict("records")
    S["前10%門檻（全部合併，淨報酬）"] = float(thr)
    S["分組（全部段）"] = T[T["段"] == "全部"].to_dict("records")
    S["前10%"] = TOP.to_dict("records")
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_deep.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500); pd.set_option("display.max_columns", 30)
    log("[全體]\n" + DIST[["段", "事件數", "C 選出檔次", "買到檔次", "買不到比例", "每筆平均", "CI95_低（事件群集）", "CI95_高", "事件等權平均（＝v1 平均報酬）", "中位", "勝率",
                           "P10", "P90", "持有天數中位", "持有天數P90"]].to_string())
    log("[逐事件]\n" + EVT.to_string())
    log("[買不到]\n" + UT.to_string())
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    sys.path.insert(0, REPO)
    os.makedirs(OUT, exist_ok=True)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()
