# -*- coding: utf-8 -*-
"""所有策略「大盤大跌時加碼自己」描述（裁定 seq437；seq436 作廢）——回測線計算子代理，2026-10-21。
⭐ 描述、⛔ 不判、⛔ 不計 N、最多暫定、⛔ 不擇優；⛔ 不 commit、不 push、不寫信箱、不動既有檔（只 import 重用）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDropAddSelf <指令> [--part 主|早年] [--procs 3]
      events     事件清單（乾跑：只讀指數，無任何策略報酬）
      build-yf   營量 v1／營飆 v1（200 顆）／營飆全買版 W1：researchYFallin.sim 原樣重跑、存逐筆持股（閘：權益 ＝ resultsBenchRejudge eq_<世界>.npz、daily_W）
      build-pth  高10 200 組同分種子：researchPTH10seed／researchPTHn.run_slot 原樣重跑、存逐筆持股（閘：權益 ＝ resultsBenchRejudge pth10seed_<世界>.npz）
      build-tie  （回測線追加 10/21）高10（F9 同分排序，使用者版）＝ resultsPTH10tie/main T1：權益 raw_<世界>.npz、逐筆 trades_<世界>_T1.csv.gz（⛔ 不重跑引擎）
      dry        乾跑：每事件每策略「可加碼持股檔數」、買不到檔數、出場日對帳（⛔ 不算任何加碼報酬）
      run        全部策略 × 全部臂 × 三段（正式、一次）
      split      兩帳分開報（使用者 10/21 更正）：策略帳 ＝ 100% 策略；加碼帳 ＝ 獨立資金 A／B′／C′／D ＋ 同時機買 0050／大盤／F9 前 4 對照 ⇒ resultsDropAddSelf/split/
    查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDropAddSelf_check [fixture|post]

═══ 讀法（寫死於 2026-10-21 21:30（台北），在算任何本件加碼報酬之前；⚠ 本線看過：排名表 rank.md 全部數字、大跌 4 檔各件、
    「跌 10% 加碼不合格、漲多加碼沒變好、大盤濾網擋加碼反向、大跌後買正2 方向不一致」各件結論；⛔ 沒看過任何「加碼自己」的數字）═══
 Z0 事件 ＝ researchMktDrop_v1.index_events（origin/main data/history/market_index.csv；q2 擴張視窗第 2 百分位、前 20 日無他事件、
    同時只處理一個事件 ACC）；事件日 e 收盤決定、e＋1 開盤加碼；收復 ＝ 加權收盤 ≥ e 前一日收盤的第一天 D0（v1 rec）⇒ D0＋1 開盤賣回；
    −5% 再加碼（臂 D）＝ researchMktDrop_addon2.find_triggers 的 T2（持有中加權收盤 ≤ e 收盤 × 0.95 的第一天 ta ⇒ ta＋1 開盤）。
    閘：接受事件日期 ＝ resultsMktDrop/v1/events.csv（q2、接受）逐筆相同（到 2026-09-24）。
 Z1 期間、口徑 ＝ 排名表（benchmark_rejudge RANK_SEG）：確認 2022-01-03～2026-08-24（主）、探索 2017-03-02～2021-12-30、早年 2005-02-01～2014-12-31；
    統計 ＝ benchmark_rejudge.estat（rerun17.win_metrics：窗首收盤為基、年化 ＝ 窗內交易日 ÷ 245）；六四 ＝ researchLev2.perf（窗首開盤建倉、1.0 起點，
    同 research64retest 窗 B；探索段六四照排名表另表窗 2018-01-15 起）；比值 ＝ 年化 ÷ |回落|；對大盤 ＝ researchAscTri.label 對報酬指數同窗（只描述）。
    每段各自從窗首重新起算（窗首前的事件不帶入）；事件日 e 須 x ≤ e ≤ y−1；收復賣出日 ＞ y ⇒ 窗尾照收盤市值計。
 Z2 帳的組成（不再平衡，「兩帳分記」）：策略帳 ＝ w × 策略權益 E_t ÷ E_x（E 為該策略原樣權益，含它自己的成本與現金）；備用 ＝ 1 − w。
    臂 A  ：w＝0.8、備用 0.2 現金（不計息）；事件 e＋1 開盤把【備用全部】按 e 收盤持股市值等比例買進「策略當下持股」（逐檔）；
            收復 ⇒ D0＋1 開盤把還在手上的加碼部位全部賣回現金，等下次。
    臂 B  ：同 A 加碼；⛔ 不賣回：每一筆加碼部位跟著策略那一檔的出場日、同價出場（逐檔），出場所得「併入策略帳」＝ 之後跟策略權益 E 同比例漲跌（近似，見 Z4）；
            ★「再留 20%」：備用金用完後，下一次事件時從當時淨值撥 20% 出來再加碼進同一批當下持股 ⇒ 撥出的來源（策略帳）與加碼的去處（策略當下持股）
            是同一個策略 ⇒ 本件視為不動（⛔ 不交易、⛔ 不扣成本）；所以 B ＝「窗內第一次有持股的事件加碼一次，之後全帳 ＝ 策略」。
            （差別只在策略帳本身的現金部位：真撥會把那幾 % 的策略閒置現金轉成持股，本件未計；見結果句）
    臂 C  ：同 A，但備用平時放 0050（含息還原，窗首收盤買、不扣成本＝同 0050 列口徑）；事件 e＋1 開盤賣 0050（扣 0050 來回 0.385%）買加碼部位；
            收復賣回後 D0＋1 開盤全數買回 0050；0050 本身的 C ＝ 不動（換自己）。
    臂 D  ：w＝0.6、備用 0.4 現金；事件 e＋1 開盤加碼【備用的一半】；T2（−5%）觸發 ⇒ ta＋1 開盤再把【剩下的備用現金全部】加碼進 ta 收盤當下持股；收復一起賣回。
            （fixture 時補寫、⛔ 尚未看任何報酬：e 收盤 0 檔、第一份沒加到 ⇒ T2 只加備用現金的一半）
    對照  ：100%（＝ 排名表值，對帳必須相同）、80%＋20% 現金永不加碼、另附 60%＋40% 現金永不加碼（D 用）、80%＋20% 0050 永不加碼（C 用）。
 Z3 逐檔加碼（⭐ 不用近似）：個股策略以引擎原樣重跑取逐筆（買進日、金額、基準價、出場價、出場日）：
      營量 v1／營飆 v1（200 顆）／全買版 W1 ＝ researchYFallin.sim（E1 閘已證與 research11.simulate_mtm 逐位元同）；高10 ＝ researchPTHn.run_slot（200 組種子）
    「目前持股」＝ e 收盤仍持有且 e＋1 開盤之後才出場的部位（出場價那天 ≥ e＋1）；權重 ＝ e 收盤市值；e＋1 開盤沒有有效開盤價 ⇒ 該檔買不到、剔除、其餘等比例（照報檔數）
    加碼部位 ＝ 該檔 e＋1 開盤價買進；之後逐日收盤市值；策略那一檔出場 ⇒ 加碼那份同一天、同出場價出場（A／C／D：錢回備用現金、等收復或下次；B：併入策略帳）
    收復賣回 ＝ D0＋1 開盤價（無有效開盤 ⇒ 前一日收盤）；成本 ＝ 引擎同式 金額 ×（1 ＋ 毛報酬 − 成本）出場時一次扣：個股 0.585%、ETF 0.385%
    ETF 類（0050、正2、六四）照配比買：0050 ＝ 0050、正2 ＝ 00631L、六四 ＝ 0050 60%＋00685L 40%（買進後不再平衡、單位制）
    e 收盤時策略 0 檔持股 ⇒ 該次不加碼（A／C／D 備用留著等下次；B 等下一個有持股的事件）
 Z4 近似（只在 B 的「併入」）：加碼部位出場後的錢若真併入策略，策略下一次新進場的每檔金額（前一日權益 ÷ N）會變大；本件以「之後跟 E 同比例」近似，
    ⛔ 不重跑引擎；高10 的閒置錢在引擎內放 0050，也照 E 同比例。
 Z5 多顆策略（營飆 v1、高10）：每顆種子各算一次 ⇒ 年化中位、回落中位、比值 ＝ 中位 ÷ |中位|（排名表慣例）；差 ＝ 臂中位 − 對照中位，另報逐顆配對差中位與「臂年化 ＞ 對照」的顆數比例
 Z6 事件貢獻：A／D 對「同 w 永不加碼」的淨值差 ＝ Σ 各事件加碼部位損益（數學恆等，程式驗）⇒ 每事件損益（以窗首資金 1 為單位）與占比；多顆取中位
 Z7 必附：事件少；「20%」為沿用值未最適化；⛔ 不擇優；已測過相近的（跌 10% 加碼不合格、漲多加碼沒變好、大盤濾網擋加碼反向、大跌後買正2 方向不一致）並列
輸出 backtest/resultsDropAddSelf/：events.csv、table.csv、table.md、event_pnl.csv、recon.json、summary.json、dry.json、run.log；大檔 ~/dasework/
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import benchmark_rejudge as BR                # noqa: E402
from backtest import data as D                              # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import researchMktDrop_v1 as V1               # noqa: E402

TIME = "2026-10-21 21:30（台北）"
OUT = "backtest/resultsDropAddSelf"
WORK = os.path.expanduser("~/dasework")
COST_STK, COST_ETF = 0.00585, 0.00385
BIG = 10 ** 9
SEGS = BR.RANK_SEG      # 確認／探索／早年
SIX4_EXP = ("2018-01-15", "2021-12-30")
ARMS = {"100%": dict(w=1.0, mode="none", pool="cash"),
        "80%＋20%現金": dict(w=0.8, mode="none", pool="cash"),
        "60%＋40%現金": dict(w=0.6, mode="none", pool="cash"),
        "80%＋20%0050": dict(w=0.8, mode="none", pool="0050"),
        "A": dict(w=0.8, mode="A", pool="cash"),
        "B": dict(w=0.8, mode="B", pool="cash"),
        "C": dict(w=0.8, mode="A", pool="0050"),
        "D": dict(w=0.6, mode="D", pool="cash")}
ARM_NAME = {"100%": "100% 策略、不加碼", "80%＋20%現金": "80% 策略＋20% 現金、永不加碼", "60%＋40%現金": "60% 策略＋40% 現金、永不加碼（D 的對照，另附）",
            "80%＋20%0050": "80% 策略＋20% 0050、永不加碼（C 的對照，另附）",
            "A": "A 主臂：大跌加碼 20%、收復賣回", "B": "B 加碼後不賣回（併入策略）", "C": "C 備用平時放 0050", "D": "D 平時留 40%、−5% 再加碼一次"}
CTRL = {"A": "80%＋20%現金", "B": "80%＋20%現金", "C": "80%＋20%0050", "D": "60%＋40%現金"}
LOGF = None
NOTES = ["描述、⛔ 不判、⛔ 不計 N、最多暫定、⛔ 不擇優；⛔ 不是買賣建議",
         "⚠ 事件少：2015 後 18 次（2015～2021 7、2022～ 11）、早年 10 次；同一波大跌高度相關 ⇒ 差異多半由少數幾次決定",
         "「20%」（D 為 20%＋20%）為沿用大跌 4 檔的值、未最適化",
         "已測過相近的：跌 10% 加碼（不合格）、漲多加碼（沒變好）、大盤濾網擋加碼（反向）、大跌後買正2（方向不一致）",
         "逐檔加碼：加碼部位跟策略那一檔同日同價出場；買不到（e＋1 無有效開盤）剔除；未計漲跌停鎖死與滑價",
         "B 的「併入策略」以之後跟策略權益同比例近似（⛔ 未重跑引擎）；B 的「再留 20%」撥出與加回同一策略 ⇒ 視為不動",
         "成本：個股 0.585%、ETF 0.385% 來回（出場時扣）；0050／正2 策略本身同排名表不含成本",
         "早年：上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測；2005-01～2007-06 只有上市；含減資假飆股約 0.3%（reduce_v2）"]


def log(m):
    s = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(s, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(s + "\n")


def git(*a):
    return subprocess.check_output(["git", "-C", os.path.expanduser("~/tw-p17"), *a]).decode("utf-8")


# ═════════════ 事件 ═════════════
def load_events():
    """⇒ (sha, list[dict])：接受事件（日期、跌幅、門檻、收復日、T2 日）。"""
    from backtest import researchMktDrop_addon2 as AD
    sha = git("rev-parse", "origin/main").strip()
    _, df = V1.read_index(sha)
    EV = V1.index_events(df)
    TG = AD.find_triggers(EV, df)
    dts = df["date"].to_numpy()
    out = []
    for i0 in np.flatnonzero(EV["ACC"]["q2"]):
        tg = TG[int(i0)]
        rec = int(EV["rec"][i0])
        out.append({"i0": int(i0), "日期": pd.Timestamp(dts[i0]), "跌幅": float(EV["r"][i0]), "門檻": float(EV["q2"][i0]),
                    "大跌前一日收盤": float(EV["cl"][i0 - 1]), "事件日收盤": float(EV["cl"][i0]),
                    "收復日": (pd.Timestamp(dts[rec]) if rec >= 0 else None), "收復等待（指數列）": (rec - int(i0) if rec >= 0 else None),
                    "T2日": (pd.Timestamp(dts[tg["T2"]]) if tg["T2"] is not None else None)})
    return sha, out


def events_gate(evs):
    R = pd.read_csv("backtest/resultsMktDrop/v1/events.csv", dtype=str)
    R = R[(R["定義"] == "q2") & (R["判定"] == "接受")]
    a = [str(e["日期"].date()) for e in evs if e["日期"] <= pd.Timestamp("2026-09-24")]
    b = list(R["日期"])
    rc = {r["日期"]: r["收復日"] for _, r in R.iterrows()}
    rbad = sum(1 for e in evs if str(e["日期"].date()) in rc and (str(e["收復日"].date()) if e["收復日"] is not None else "") != (rc[str(e["日期"].date())] or ""))
    return {"接受事件 本件": len(a), "接受事件 v1 檔": len(b), "日期不同": int(a != b), "收復日不同": int(rbad)}


def map_events(evs, cal, x, y):
    """事件 ⇒ 日曆位置（e、d＝e＋1、ta、s＝D0＋1）；只取 x ≤ e ≤ y−1。日期不在日曆 ⇒ 記錄。"""
    idx = pd.DatetimeIndex(cal)
    out, miss = [], []

    def pos(ts):
        if ts < idx[0] or ts > idx[-1]:
            return None
        p = int(idx.searchsorted(ts))
        if p >= len(idx) or idx[p] != ts:
            miss.append(str(ts.date()))
            return None
        return p
    for k, ev in enumerate(evs):
        e = pos(ev["日期"])
        if e is None or not (x <= e <= y - 1):
            continue
        s = None
        if ev["收復日"] is not None:
            pD = pos(ev["收復日"])
            if pD is not None and pD + 1 <= y:
                s = pD + 1
        ta = None
        if ev["T2日"] is not None:
            pa = pos(ev["T2日"])
            if pa is not None and pa + 1 <= y and (s is None or pa + 1 < s):
                ta = pa
        out.append({"k": k, "e": e, "d": e + 1, "s": s, "ta": ta})
    return out, miss


# ═════════════ 加碼層（核心；fixture 見 _check）═════════════
def lot_paths(L, d, s, y, CL, OP, cost):
    """一筆加碼（多檔 lot）⇒ 窗內 [d, y] 逐日：val（收盤時仍在手上的市值）、flow_conv（策略出場轉現金，記在出場價那天收盤）、
    flow_sale（收復賣回，記在 s）；以及每檔明細。L ＝ dict(rows, a, p, tpx, exv)。s ＝ None ⇒ 不賣回（B，或窗內未收復）。"""
    T = y - d + 1
    val = np.zeros(T); fconv = np.zeros(T); fsale = np.zeros(T)
    conv_list = []                                                  # (t, proceeds) for B
    for i in range(len(L["rows"])):
        r, a, p, tpx = L["rows"][i], L["a"][i], L["p"][i], int(L["tpx"][i])
        end_live = min(tpx, y) if s is None else min(tpx, s - 1, y)  # 最後一個「收盤仍在手上」的日子（tpx 當天收盤轉現金 ⇒ 不算在手上）
        if tpx <= y and (s is None or tpx <= s - 1):
            # 策略出場：tpx 收盤以出場價轉現金
            last = tpx - 1
            if last >= d:
                val[:last - d + 1] += a * CL[r, d:last + 1] / p
            proc = a * (L["exv"][i] / p - cost)
            fconv[tpx - d] += proc
            conv_list.append((tpx, proc))
        elif s is not None and s <= y:
            last = s - 1
            if last >= d:
                val[:last - d + 1] += a * CL[r, d:last + 1] / p
            px = OP[r, s]
            if not (np.isfinite(px) and px > 0):
                px = CL[r, s - 1]
            fsale[s - d] += a * (px / p - cost)
        else:
            val[:end_live - d + 1] += a * CL[r, d:end_live + 1] / p
    return val, fconv, fsale, conv_list


def overlay(E, x, y, evs, arm, hold_fn, CL, OP, cost, O50=None, C50=None, base="close", out=None):
    """⇒ (NAV 陣列 [x..y], 每事件資訊 list)。E ＝ 策略權益（日曆位置）；base＝"close"：策略帳 ＝ w·E_t/E_x、0050 備用以 C50[x] 買；
    base＝"open"（六四）：E 已是以窗首開盤前 1.0 為基的權益、0050 備用以 O50[x] 買。"""
    w, mode, pool = arm["w"], arm["mode"], arm["pool"]
    T = y - x + 1
    Ew = E[x:y + 1] / (E[x] if base == "close" else 1.0)
    nav = w * Ew
    r0 = 1.0 - w
    if r0 <= 0:
        return nav.copy(), []
    extra = np.zeros(T)                   # 加碼部位市值
    cashflow = np.zeros(T)                # 備用現金的流入（＋）／流出（−），記在當天（開盤或收盤皆計入當天收盤）
    merged = np.zeros(T)                  # B：併入策略帳的部分
    lotsval = np.zeros(T)                 # 加碼部位（個股／ETF 加碼那份）收盤市值（split 的資金使用率用；不含 0050 備用）
    info = []
    # 0050 備用：分段（units 持有期間）
    u50_spans = []                        # (t0, t1, units) 收盤持有 units 的區間 [t0, t1]
    if pool == "0050":
        u0 = r0 / (C50[x] if base == "close" else O50[x])
        cur_units, cur_t0 = u0, x
        cash0 = 0.0
    else:
        cur_units, cur_t0 = 0.0, x
        cash0 = r0
    used_B = False
    if mode != "none":
        for ev in evs:
            if mode == "B" and used_B:
                break
            e, d, s = ev["e"], ev["d"], (None if mode in ("B", "Bp") else ev["s"])   # Bp（split B′）：不在收復賣、跟策略出場
            # 當下可用備用現金（＝ 起始現金 ＋ 至 d−1 收盤為止的流入流出）
            avail_cash = cash0 + cashflow[:d - x].sum()
            withdrawn = 0.0
            L = hold_fn(e, d)
            rec = {"k": ev["k"], "e": e, "d": d, "s": s, "持股檔": 0 if L is None else len(L["rows"]), "買不到": 0 if L is None else L.get("nbad", 0),
                   "投入": 0.0, "回收": 0.0, "窗尾市值": 0.0, "T2加碼": False, "持有至": None}
            rec["併入窗尾市值"] = 0.0
            if L is None and not (mode == "D" and ev["ta"] is not None):
                info.append(rec)
                continue
            tranches = []
            if L is None:
                pass
            elif pool == "0050":
                v = cur_units * (O50[d] if np.isfinite(O50[d]) and O50[d] > 0 else C50[d - 1])
                u50_spans.append((cur_t0, d - 1, cur_units))
                cur_units = 0.0
                withdrawn = v + avail_cash
                dep = v * (1 - COST_ETF) + avail_cash
                cashflow[d - x] -= avail_cash
            else:
                dep = avail_cash * (0.5 if mode == "D" else 1.0)
                withdrawn = dep
                cashflow[d - x] -= dep
            if L is not None:
                tranches.append((d, dep, L))
            if mode == "D" and ev["ta"] is not None:
                tranches.append((ev["ta"] + 1, None, None))
            for (dd, amt, LL) in tranches:
                if amt is None:                                       # T2：ta 收盤持股、剩下備用現金全部
                    LL = hold_fn(ev["ta"], dd)
                    if LL is None:
                        continue
                    amt = (cash0 + cashflow[:dd - x].sum()) * (1.0 if L is not None else 0.5)   # 第一份沒加到（e 收盤 0 檔）⇒ T2 只加一半
                    if amt <= 1e-12:
                        continue
                    cashflow[dd - x] -= amt
                    withdrawn += amt; rec["T2加碼"] = True; rec["T2持股檔"] = len(LL["rows"])
                lots = dict(LL); lots["a"] = amt * np.asarray(LL["w"], float)
                val, fconv, fsale, conv = lot_paths(lots, dd, s, y, CL, OP, cost)
                off = dd - x
                extra[off:] += val; lotsval[off:] += val
                for i_ in range(len(lots["rows"])):
                    tp_ = int(lots["tpx"][i_])
                    end_ = tp_ if (tp_ <= y and (s is None or tp_ <= s - 1)) else (s if (s is not None and s <= y) else y)
                    rec["持有至"] = end_ if rec["持有至"] is None else max(rec["持有至"], end_)
                if mode == "B":
                    for (tc, proc) in conv:
                        merged[tc - x:] += proc * E[tc:y + 1] / E[tc]
                    rec["回收"] += sum(p_ for _, p_ in conv)
                    rec["窗尾市值"] += float(val[-1])
                else:
                    cashflow[off:] += fconv + fsale
                    rec["回收"] += float(fconv.sum() + fsale.sum())
                    rec["窗尾市值"] += float(val[-1])
            rec["投入"] = withdrawn
            if mode == "B":
                used_B = True
                rec["併入窗尾市值"] = float(merged[-1])
            if pool == "0050" and s is not None:
                c_at_s = cash0 + cashflow[:s - x + 1].sum()              # 含 s 當天賣回
                px50 = O50[s] if np.isfinite(O50[s]) and O50[s] > 0 else C50[s - 1]
                cur_units = c_at_s / px50; cur_t0 = s
                cashflow[s - x] -= c_at_s
            info.append(rec)
    if pool == "0050":
        u50_spans.append((cur_t0, y, cur_units))
        for (t0, t1, u) in u50_spans:
            if t1 >= t0 and u > 0:
                extra[t0 - x:t1 - x + 1] += u * C50[t0:t1 + 1]
    cash_path = cash0 + np.cumsum(cashflow)
    nav = nav + extra + cash_path + merged
    if out is not None:
        out["lots"] = lotsval; out["cash"] = cash_path
    return nav, info


# ═════════════ 持股（逐筆）═════════════
def make_hold_fn(P, CL, OP):
    """P ＝ dict(k, tb, ep, amt, exv, tpx) 陣列（單一顆）。⇒ hold_fn(e, d)。"""
    k, tb, ep, amt, exv, tpx = P["k"], P["tb"], P["ep"], P["amt"], P["exv"], P["tpx"]

    def fn(e, d):
        m = (tb <= e) & (tpx >= d)
        if not m.any():
            return None
        rows = k[m]; mv = amt[m] * CL[rows, e] / ep[m]
        p = OP[rows, d]
        ok = np.isfinite(p) & (p > 0) & np.isfinite(mv) & (mv > 0)
        if not ok.any():
            return None
        wv = mv[ok] / mv[ok].sum()
        return {"rows": rows[ok], "w": wv, "p": p[ok], "tpx": tpx[m][ok], "exv": exv[m][ok], "nbad": int((~ok).sum())}
    return fn


def make_etf_fn(rows, wts, CL, OP):
    rows = np.asarray(rows, int); wts = np.asarray(wts, float)

    def fn(e, d):
        p = OP[rows, d].astype(float)
        bad = ~(np.isfinite(p) & (p > 0))
        p[bad] = CL[rows[bad], d - 1]
        return {"rows": rows, "w": wts, "p": p, "tpx": np.full(len(rows), BIG), "exv": np.full(len(rows), np.nan), "nbad": 0}
    return fn


def hold_counts(P, CL, OP, e, d):
    k, tb, tpx = P["k"], P["tb"], P["tpx"]
    m = (tb <= e) & (tpx >= d)
    p = OP[k[m], d]
    ok = np.isfinite(p) & (p > 0)
    return int(m.sum()), int((~ok).sum())


# ═════════════ build：營量／營飆／W1 ═════════════
def build_yf(a):
    from backtest import researchYFallin as YA
    from backtest import researchYL_integrate as IG
    from backtest import rerun17 as RR
    part = a.part
    T0 = time.time()
    W, gate = IG.main_world(log) if part == "主" else IG.early_world(log, a.procs)
    DF = YA.build_days(W["SIG"][True], 120); DY = YA.build_days(W["SIG"][False], 60, pick="relvol")
    runs = [("v1", r) for r in range(200)] + [("YL", 0), ("W1", 0)]
    EQ, POS, SIDS = {}, [], {}
    ref = np.load(os.path.join(BR.OUT, f"eq_{part}.npz"))
    bad = {"v1 權益 ≠ eq_npz YF": 0, "YL 權益 ≠ eq_npz YL": 0, "出場價 ≠ 出場根收盤（筆，容差 2e−6）": 0, "賣買配對錯": 0}
    cl = W["closes"]
    nfix = nforce = 0; relmax = 0.0
    for ri, (m, r) in enumerate(runs):
        if m == "v1":
            o = YA.sim(W, DF, "v1", 10, rng=np.random.default_rng(RR.P10_SEED0 + r))
            if not np.array_equal(o["equity"], ref["YF"][r]):
                bad["v1 權益 ≠ eq_npz YF"] += 1
        elif m == "YL":
            o = YA.sim(W, DY, "v1", 20, pick=True)
            if not np.array_equal(o["equity"], ref["YL"][0]):
                bad["YL 權益 ≠ eq_npz YL"] += 1
        else:
            o = YA.sim(W, DF, "W1", 10)
        EQ[(m, r)] = o["equity"]
        opn = {}
        ev = [(b[0], 1, b) for b in o["buys"]] + [(s_[0], 0, s_) for s_ in o["sells"]]
        rows = []
        for t, side, z in sorted(ev, key=lambda q: (q[0], q[1])):
            if side == 1:
                opn[z[1]] = z
            else:
                b = opn.pop(z[1], None)
                if b is None:
                    bad["賣買配對錯"] += 1; continue
                ratio = z[3] / b[2]
                exv = ratio * b[4]; tc = int(z[0])
                if int(b[5]) > tc:                                       # 停止交易強制出場：L＋1 入帳、價 ＝ L 收盤
                    tpx = tc - 1; nforce += 1
                else:                                                    # 排程出場：出場根 ＝ xpos（＝ 入帳日）當天收盤
                    tpx = tc; nfix += 1
                rel = abs(exv / float(cl[z[1]][tpx]) - 1)               # closes 為 float32 ⇒ 容差 2e−6
                relmax = max(relmax, rel)
                if rel > 2e-6:
                    bad["出場價 ≠ 出場根收盤（筆，容差 2e−6）"] += 1
                rows.append((z[1], int(b[0]), float(b[4]), float(b[2]), float(exv), tpx))
        for sid, b in opn.items():
            rows.append((sid, int(b[0]), float(b[4]), float(b[2]), np.nan, BIG))
        for (sid, tb, ep, amt, exv, tpx) in rows:
            if sid not in SIDS:
                SIDS[sid] = len(SIDS)
            POS.append((ri, SIDS[sid], tb, ep, amt, exv, tpx))
    sids = list(SIDS)
    CLm = np.vstack([np.asarray(W["closes"][s], float) for s in sids]); OPm = np.vstack([np.asarray(W["opens"][s], float) for s in sids])
    # W1 對 daily_W
    d = pd.read_csv(os.path.join(BR.YFA, "daily_W.csv.gz"), encoding="utf-8-sig", float_precision="round_trip")
    d = d[(d["帳"] == "W1") & (d["世界"] == part) & d["日期"].notna()]
    cal = W["cal"]; pos = {str(c.date()): i for i, c in enumerate(cal)}
    e1 = EQ[("W1", 0)]
    bad["W1 權益 ≠ daily_W（日）"] = int(sum(1 for dt, v in zip(d["日期"], d["權益"]) if e1[pos[dt]] != v))
    P = np.array(POS, dtype=[("run", "i4"), ("k", "i4"), ("tb", "i8"), ("ep", "f8"), ("amt", "f8"), ("exv", "f8"), ("tpx", "i8")])
    os.makedirs(WORK, exist_ok=True)
    np.savez_compressed(os.path.join(WORK, f"yf_{part}.npz"), sids=np.array(sids), CL=CLm, OP=OPm, dates=np.array([str(c.date()) for c in cal]),
                        eq_v1=np.array([EQ[("v1", r)] for r in range(200)]), eq_YL=EQ[("YL", 0)], eq_W1=e1, pos=P)
    log(f"[build-yf {part}] 跑 {len(runs)} 條｜持股筆 {len(P)}｜股 {len(sids)}｜排程出場 {nfix}、強制出場 {nforce}、出場價 vs 收盤最大相對差 {relmax:.2e}｜閘 {bad}｜世界閘 {gate}｜{time.time() - T0:.0f}s")
    json.dump({"閘": bad, "世界閘": gate, "排程出場": nfix, "強制出場": nforce, "出場價 vs 收盤最大相對差": relmax, "秒": round(time.time() - T0)}, open(os.path.join(WORK, f"yf_{part}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    if any(v for v in bad.values()):
        raise SystemExit(f"⛔ build-yf 閘不過 {bad}")


# ═════════════ build：高10 ═════════════
def build_pth(a):
    from multiprocessing import Pool
    from backtest import researchPTH10seed as PS
    wn = a.part
    T0 = time.time()
    W = PS.M.build_world(wn, log)
    RES = {}
    with Pool(a.procs) as pool:
        for sid, r in pool.imap_unordered(PS.PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
            if r is not None:
                RES[sid] = r
    ref = np.load(os.path.join(BR.OUT, f"pth10seed_{wn}.npz"))["eq"]
    EQ, POS = [], []
    bad = {"權益 ≠ pth10seed（顆）": 0, "賣出日 ≠ ext（筆）": 0, "出場價 ≠ 賣出日收盤（筆）": 0}
    CM, O = W["CM"], np.asarray(W["O"], float)
    relmax = 0.0
    for k in range(1, PS.NSEED + 1):
        ev, _ = PS.events_with(W, wn, RES, PS.seed_of(k))
        S = PS.PN.run_slot(ev, W, PS.N, False)
        if not np.array_equal(S["eq"], ref[k]):
            bad["權益 ≠ pth10seed（顆）"] += 1
        EQ.append(S["eq"])
        sl = {q: t for t, q, amt, proc in S["sells"]}
        for t, q, amt in S["buys"]:
            j = int(S["j"][q]); ep = float(S["ep"][q]); g = float(S["g"][q])
            if q in sl:
                tc = int(sl[q])
                if tc != int(S["ext"][q]):
                    bad["賣出日 ≠ ext（筆）"] += 1
                exv = (1 + g) * ep
                rel = abs(exv / CM[j, tc] - 1); relmax = max(relmax, rel)
                if not rel <= 2e-6:
                    bad["出場價 ≠ 賣出日收盤（筆）"] += 1
                POS.append((k - 1, j, int(t), ep, float(amt), exv, tc))
            else:
                POS.append((k - 1, j, int(t), ep, float(amt), np.nan, BIG))
    P = np.array(POS, dtype=[("run", "i4"), ("k", "i4"), ("tb", "i8"), ("ep", "f8"), ("amt", "f8"), ("exv", "f8"), ("tpx", "i8")])
    rows = np.unique(P["k"]); rmap = {int(j): i for i, j in enumerate(rows)}
    P["k"] = np.array([rmap[int(j)] for j in P["k"]])
    np.savez_compressed(os.path.join(WORK, f"pth_{wn}.npz"), CL=CM[rows], OP=O[rows], dates=W["dates"], eq=np.array(EQ), pos=P, rows=rows)
    log(f"[build-pth {wn}] 200 顆｜持股筆 {len(P)}｜股 {len(rows)}｜出場價 vs 收盤最大相對差 {relmax:.2e}｜閘 {bad}｜{time.time() - T0:.0f}s")
    json.dump({"閘": bad, "出場價 vs 收盤最大相對差": relmax, "秒": round(time.time() - T0)}, open(os.path.join(WORK, f"pth_{wn}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if any(v for v in bad.values()):
        raise SystemExit(f"⛔ build-pth 閘不過 {bad}")


# ═════════════ build：高10（F9 同分排序，使用者版）═════════════
TIE = "backtest/resultsPTH10tie/main"
TIE_NAME = "高10（F9 同分排序，使用者版）"


def build_tie(a):
    """回測線追加（使用者 10/21「順便測大跌加碼」）：resultsPTH10tie/main（commit 4169202558）T1 單一路徑；權益 ＝ raw_<世界>.npz T1_eq，
    逐筆 ＝ trades_<世界>_T1.csv.gz（researchPTHn.trades_df 原欄）；價格 ＝ researchPTHpf.build_world 的 CM／O（⛔ 不重跑引擎）。"""
    from backtest import researchPTH10seed as PS
    wn = a.part
    T0 = time.time()
    W = PS.M.build_world(wn, log)
    Z = np.load(os.path.join(TIE, f"raw_{wn}.npz"))
    if list(Z["dates"]) != list(W["dates"]):
        raise SystemExit("⛔ raw npz 日曆 ≠ PTH 世界")
    eq = np.asarray(Z["T1_eq"], float)
    T = pd.read_csv(os.path.join(TIE, f"trades_{wn}_T1.csv.gz"), dtype={"sid": str, "賣出日": str}, keep_default_na=False, float_precision="round_trip")
    dpos = {d: i for i, d in enumerate(W["dates"])}
    CM, O = W["CM"], np.asarray(W["O"], float)
    bad = {"出場價 ≠ 賣出日收盤（筆）": 0, "入帳 ≠ 金額×(1＋R−成本)（筆）": 0, "買價 ≠ 買進日開盤（筆）": 0}
    POS = []; relmax = 0.0
    from backtest import research11 as R11
    for _, r in T.iterrows():
        j = int(W["ix"][r["sid"]]); tb = dpos[r["買進日"]]; ep = float(r["市值基準價"]); amt = float(r["金額"])
        if not abs(ep / O[j, tb] - 1) <= 1e-12:
            bad["買價 ≠ 買進日開盤（筆）"] += 1
        if r["賣出日"] != "":
            g = float(r["R用"]); tc = dpos[r["賣出日"]]; exv = (1 + g) * ep
            rel = abs(exv / CM[j, tc] - 1); relmax = max(relmax, rel)
            if rel > 2e-6:
                bad["出場價 ≠ 賣出日收盤（筆）"] += 1
            if abs(float(r["入帳"]) - amt * (1 + g - R11.COST)) > 1e-12:
                bad["入帳 ≠ 金額×(1＋R−成本)（筆）"] += 1
            POS.append((0, j, tb, ep, amt, exv, tc))
        else:
            POS.append((0, j, tb, ep, amt, np.nan, BIG))
    P = np.array(POS, dtype=[("run", "i4"), ("k", "i4"), ("tb", "i8"), ("ep", "f8"), ("amt", "f8"), ("exv", "f8"), ("tpx", "i8")])
    rows = np.unique(P["k"]); rmap = {int(j): i for i, j in enumerate(rows)}
    P["k"] = np.array([rmap[int(j)] for j in P["k"]])
    np.savez_compressed(os.path.join(WORK, f"tie_{wn}.npz"), CL=CM[rows], OP=O[rows], dates=W["dates"], eq=eq[None, :], pos=P, rows=rows)
    log(f"[build-tie {wn}] T1｜持股筆 {len(P)}｜股 {len(rows)}｜出場價 vs 收盤最大相對差 {relmax:.2e}｜閘 {bad}｜{time.time() - T0:.0f}s")
    json.dump({"閘": bad, "出場價 vs 收盤最大相對差": relmax}, open(os.path.join(WORK, f"tie_{wn}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if any(v for v in bad.values()):
        raise SystemExit(f"⛔ build-tie 閘不過 {bad}")


def tie_ref():
    """resultsPTH10tie/main/table.csv 的 T1（無滑價）各段 年化／回落 字串（%.10g）＋窗。"""
    T = pd.read_csv(os.path.join(TIE, "table.csv"), encoding="utf-8-sig", dtype=str)
    T = T[(T["排序"] == "T1") & (T["滑價"] == "False")]
    return {(r["世界"], r["段"]): (r["窗"], r["年化"], r["回落"]) for _, r in T.iterrows()}


# ═════════════ 載入（run／dry 共用）═════════════
def etf_px(data, sids, cal):
    old = D.DATA; D.DATA = data
    try:
        CLm, OPm = [], []
        for s in sids:
            st = D.load_stock(s, "twse", D.load_calendar())
            df = st.df.reindex(cal)
            CLm.append(pd.Series(df["close"].to_numpy(float)).ffill().to_numpy(float)); OPm.append(df["open"].to_numpy(float))
    finally:
        D.DATA = old
    return np.vstack(CLm), np.vstack(OPm)


def split_runs(P, n):
    o = np.argsort(P["run"], kind="stable"); P = P[o]
    b = np.searchsorted(P["run"], np.arange(n + 1))
    return [{f: P[f][b[i]:b[i + 1]] for f in ("k", "tb", "ep", "amt", "exv", "tpx")} for i in range(n)]


def load_world(wn):
    """⇒ dict：cal、各策略 {E: list, P: list or None, CL, OP, cost, etf_fn}、0050 O／C。"""
    cal = BR.world_cal(BR.WORLD_DATA[wn])
    dates = np.array([str(c.date()) for c in cal])
    S = {}
    Z = np.load(os.path.join(WORK, f"yf_{wn}.npz"), allow_pickle=False)
    if list(Z["dates"][:len(cal)]) != list(dates):
        raise SystemExit(f"⛔ yf_{wn} 日曆 ≠ 排名表世界日曆")
    PY = split_runs(Z["pos"], 202)
    CLy, OPy = Z["CL"], Z["OP"]
    S["營量 v1"] = {"E": [Z["eq_YL"]], "P": [PY[200]], "CL": CLy, "OP": OPy, "cost": COST_STK}
    S["營飆 v1"] = {"E": list(Z["eq_v1"]), "P": PY[:200], "CL": CLy, "OP": OPy, "cost": COST_STK}
    S["營飆（使用者全買版）"] = {"E": [Z["eq_W1"]], "P": [PY[201]], "CL": CLy, "OP": OPy, "cost": COST_STK}
    Zp = np.load(os.path.join(WORK, f"pth_{wn}.npz"), allow_pickle=False)
    if list(Zp["dates"][:len(cal)]) != list(dates):
        raise SystemExit(f"⛔ pth_{wn} 日曆 ≠ 排名表世界日曆")
    S["高10"] = {"E": list(Zp["eq"]), "P": split_runs(Zp["pos"], 200), "CL": Zp["CL"], "OP": Zp["OP"], "cost": COST_STK}
    tp = os.path.join(WORK, f"tie_{wn}.npz")
    if os.path.exists(tp):
        Zt = np.load(tp, allow_pickle=False)
        if list(Zt["dates"][:len(cal)]) != list(dates):
            raise SystemExit(f"⛔ tie_{wn} 日曆 ≠ 排名表世界日曆")
        S[TIE_NAME] = {"E": [Zt["eq"][0]], "P": split_runs(Zt["pos"], 1), "CL": Zt["CL"], "OP": Zt["OP"], "cost": COST_STK}
    etfs = ["0050", "00631L"] if wn == "主" else ["0050"]
    CLe, OPe = etf_px(BR.WORLD_DATA[wn], etfs, cal)
    b50 = BR.bench0050(BR.WORLD_DATA[wn]).to_numpy(float)
    if not np.array_equal(CLe[0], b50):
        raise SystemExit("⛔ 0050 收盤 ≠ benchmark_rejudge.bench0050")
    S["0050"] = {"E": [CLe[0]], "P": None, "CL": CLe, "OP": OPe, "cost": COST_ETF, "etf": ([0], [1.0])}
    if wn == "主":
        p2 = BR.stock_close(BR.WORLD_DATA[wn], "00631L").to_numpy(float)
        if not np.array_equal(CLe[1], p2):
            raise SystemExit("⛔ 00631L 收盤 ≠ benchmark_rejudge.stock_close")
        S["正2（00631L）"] = {"E": [CLe[1]], "P": None, "CL": CLe, "OP": OPe, "cost": COST_ETF, "etf": ([1], [1.0])}
    return {"cal": cal, "S": S, "O50": OPe[0], "C50": CLe[0]}


def six4_world():
    X = BR._mx()
    cal = pd.DatetimeIndex(pd.to_datetime(X["cal"]))
    CL = np.vstack([np.asarray(X["C"]["0050"], float), np.asarray(X["C"]["00685L"], float)])
    OP = np.vstack([np.asarray(X["O"]["0050"], float), np.asarray(X["O"]["00685L"], float)])
    return {"cal": cal, "CL": CL, "OP": OP, "X": X}


# ═════════════ 乾跑 ═════════════
def cmd_events(a):
    sha, evs = load_events()
    os.makedirs(OUT, exist_ok=True)
    g = events_gate(evs)
    rows = []
    for e in evs:
        rows.append({"日期": str(e["日期"].date()), "加權跌幅": e["跌幅"], "門檻(q2)": e["門檻"], "收復日": str(e["收復日"].date()) if e["收復日"] is not None else "未收復",
                     "收復等待（指數交易日）": e["收復等待（指數列）"], "−5% 再加碼觸發日(T2)": str(e["T2日"].date()) if e["T2日"] is not None else ""})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "events.csv"), index=False, float_format="%.6g", encoding="utf-8")
    cnt = {"2006～2014": sum(1 for e in evs if e["日期"].year <= 2014), "2015～2021": sum(1 for e in evs if 2015 <= e["日期"].year <= 2021),
           "2022～": sum(1 for e in evs if e["日期"].year >= 2022)}
    W = {}
    for sg, (wn, a_, b_) in SEGS.items():
        cal = BR.world_cal(BR.WORLD_DATA[wn]); x, y = BR.seg_pos(cal, a_, b_)
        m, miss = map_events(evs, cal, x, y)
        W[sg] = {"窗": f"{cal[x].date()}～{cal[y].date()}", "窗內事件": len(m), "T2 觸發": sum(1 for z in m if z["ta"] is not None),
                 "窗內未收復": sum(1 for z in m if z["s"] is None), "日期不在日曆": miss,
                 "事件日": [str(cal[z["e"]].date()) for z in m]}
    log(f"[events] 指數 origin/main {sha[:10]}｜閘 {g}｜期間 {cnt}｜{json.dumps(W, ensure_ascii=False)}")
    return sha, evs, g, cnt, W


def cmd_dry(a):
    """⛔ 不算任何加碼報酬：只數每事件可加碼檔數、買不到檔數。"""
    sha, evs = load_events()
    out = {}
    for sg, (wn, a_, b_) in SEGS.items():
        Wd = load_world(wn); cal = Wd["cal"]; x, y = BR.seg_pos(cal, a_, b_)
        m, _ = map_events(evs, cal, x, y)
        for nm, s in Wd["S"].items():
            if s["P"] is None:
                continue
            for z in m:
                for tag, (e, d) in (("事件", (z["e"], z["d"])),) + ((("T2", (z["ta"], z["ta"] + 1)),) if z["ta"] is not None else ()):
                    c = np.array([hold_counts(P, s["CL"], s["OP"], e, d) for P in s["P"]])
                    out.setdefault(sg, {}).setdefault(nm, []).append({"日": str(cal[e].date()), "類": tag, "持股檔中位": float(np.median(c[:, 0])),
                                                                     "持股檔最少": int(c[:, 0].min()), "0 檔顆數": int((c[:, 0] == 0).sum()),
                                                                     "買不到檔數和": int(c[:, 1].sum()), "顆數": len(c)})
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, "dry.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for sg, v in out.items():
        for nm, L in v.items():
            log(f"[dry {sg} {nm}] " + "｜".join(f"{q['日']}{'(T2)' if q['類'] == 'T2' else ''} 檔{q['持股檔中位']:.0f}/最少{q['持股檔最少']}/0檔{q['0 檔顆數']}/買不到{q['買不到檔數和']}" for q in L))


# ═════════════ 正式 ═════════════
def stat_close(nav, x, y, n):
    full = np.full(n, np.nan); full[x:y + 1] = nav
    return BR.estat(full, x, y)


def cmd_run(a):
    from backtest import researchLev2 as L2
    T0 = time.time()
    sha, evs = load_events()
    g = events_gate(evs)
    if g["日期不同"] or g["收復日不同"]:
        raise SystemExit(f"⛔ 事件閘不過 {g}")
    TR = BR.read_series("git:origin/main:data/history/market_tri.csv")
    RK = pd.read_csv(os.path.join(BR.OUT, "rank.csv"), dtype=str)
    TR1 = tie_ref()
    rows, erows, recon = [], [], []
    SX = six4_world()
    worlds = {}
    for sg, (wn, a_, b_) in SEGS.items():
        if wn not in worlds:
            worlds[wn] = load_world(wn)
        Wd = worlds[wn]; cal = Wd["cal"]; n = len(cal); x, y = BR.seg_pos(cal, a_, b_)
        bt = BR.bstat(cal, BR.on_cal(TR, cal)[0], x, y)
        m, miss = map_events(evs, cal, x, y)
        if miss:
            raise SystemExit(f"⛔ {sg} 事件日不在日曆 {miss}")
        strat = list(Wd["S"].items())
        if sg in ("確認", "探索"):
            strat.append(("六四 v1", None))
        for nm, s in strat:
            if nm == "六四 v1":
                w0, w1 = (a_, b_) if sg == "確認" else SIX4_EXP
                X = SX["X"]; i0, i1 = X["pos"][w0], X["pos"][w1]
                eq, _ = BR.six4_eq(w0, w1)
                E = np.full(len(SX["cal"]), np.nan); E[i0:i1 + 1] = eq
                mm, miss6 = map_events(evs, SX["cal"], i0, i1)
                if miss6:
                    raise SystemExit(f"⛔ 六四 事件日不在日曆 {miss6}")
                runs = [(E, make_etf_fn([0, 1], [0.6, 0.4], SX["CL"], SX["OP"]))]
                ctx = dict(x=i0, y=i1, evs=mm, CL=SX["CL"], OP=SX["OP"], cost=COST_ETF, O50=SX["OP"][0], C50=SX["CL"][0], base="open")
                statf = (lambda nav: L2.perf(nav))
                win = f"{w0}～{w1}"
                btw = bt if sg == "確認" else BR.bstat(cal, BR.on_cal(TR, cal)[0], *BR.seg_pos(cal, *SIX4_EXP))
                cal_ev = SX["cal"]
            else:
                if s["P"] is None:
                    r_, w_ = s["etf"]
                    runs = [(s["E"][0], make_etf_fn(r_, w_, s["CL"], s["OP"]))]
                else:
                    runs = [(E_, make_hold_fn(P, s["CL"], s["OP"])) for E_, P in zip(s["E"], s["P"])]
                ctx = dict(x=x, y=y, evs=m, CL=s["CL"], OP=s["OP"], cost=s["cost"], O50=Wd["O50"], C50=Wd["C50"], base="close")
                statf = (lambda nav, x=x, y=y, n=n: stat_close(nav, x, y, n))
                win = f"{cal[x].date()}～{cal[y].date()}"
                btw = bt
                cal_ev = cal
            V = {}            # arm ⇒ list of (cagr, mdd) per run
            EP = {}           # arm ⇒ list of info per run
            NAVEND = {}
            for arm, cfg in ARMS.items():
                if nm == "0050" and arm == "C":
                    cfg = dict(cfg, mode="none")            # 換自己 ⇒ 不動
                res, inf, ne = [], [], []
                for E_, fn in runs:
                    nav, info = overlay(E_, ctx["x"], ctx["y"], ctx["evs"], cfg, fn, ctx["CL"], ctx["OP"], ctx["cost"], ctx["O50"], ctx["C50"], ctx["base"])
                    res.append(statf(nav)); inf.append(info); ne.append(float(nav[-1]))
                V[arm] = np.array(res); EP[arm] = inf; NAVEND[arm] = np.array(ne)
            # 恆等式閘：A、D 對同 w 對照 淨值差 ＝ Σ 事件損益
            for arm, ct in (("A", "80%＋20%現金"), ("D", "60%＋40%現金")):
                for i in range(len(runs)):
                    sp = sum(r_["回收"] + r_["窗尾市值"] - r_["投入"] for r_ in EP[arm][i])
                    if abs((NAVEND[arm][i] - NAVEND[ct][i]) - sp) > 1e-9:
                        raise SystemExit(f"⛔ 恆等式不過：{sg} {nm} {arm} 顆 {i}：淨值差 {NAVEND[arm][i] - NAVEND[ct][i]} ≠ Σ損益 {sp}")
            med = {arm: (float(np.median(v[:, 0])), float(np.median(v[:, 1]))) for arm, v in V.items()}
            for arm in ARMS:
                c, md = med[arm]
                r = {"段": sg, "策略": nm, "臂": arm, "臂說明": ARM_NAME[arm], "窗": win, "顆數": len(runs), "年化": c, "回落": md, "比值": AS.ratio(c, md),
                     "對大盤": AS.label(c, md, btw), "大盤年化": btw["cagr"], "大盤回落": btw["mdd"], "大盤比值": btw["ratio"]}
                for ct in ("100%", "80%＋20%現金") + ((CTRL[arm],) if arm in CTRL and CTRL[arm] != "80%＋20%現金" else ()):
                    c0, m0 = med[ct]
                    r[f"差年化_對{ct}"] = c - c0; r[f"差回落_對{ct}"] = md - m0; r[f"差比值_對{ct}"] = AS.ratio(c, md) - AS.ratio(c0, m0)
                    if len(runs) > 1:
                        dv = V[arm][:, 0] - V[ct][:, 0]
                        r[f"逐顆差年化中位_對{ct}"] = float(np.median(dv)); r[f"年化贏的顆比例_對{ct}"] = float(np.mean(dv > 0))
                rows.append(r)
            # 對帳：100% ＝ 排名表
            c, md = med["100%"]
            kname = nm
            q = RK[(RK["段"] == sg) & (RK["策略"] == kname)]
            if nm == "六四 v1" and sg == "探索":
                q = RK[(RK["段"] == sg) & (RK["策略"] == kname) & (RK["排名"] == "另表")]
            fmt = "%.8g" if nm in ("營量 v1", "營飆 v1") else "%.10g"
            if nm == TIE_NAME:                                     # 對 resultsPTH10tie/main/table.csv T1（早年該件窗 2005-01-03 起 ⇒ 以該窗另算比對）
                wref, cref, mref = TR1[(wn, sg)]
                cc, mc = (c, md)
                if wref != win:
                    cc, mc = BR.estat(runs[0][0], *BR.seg_pos(cal, *wref.split("～")))
                ok = fmt % cc == fmt % float(cref) and fmt % mc == fmt % float(mref)
                recon.append({"段": sg, "策略": nm, "本件100%年化": c, "本件100%回落": md, "對帳窗": wref, "對帳窗本件年化": cc, "對帳窗本件回落": mc,
                              "resultsPTH10tie T1 年化": cref, "resultsPTH10tie T1 回落": mref, "比較精度": fmt, "相同": bool(ok)})
            else:
                ok = len(q) == 1 and (fmt % c == fmt % float(q.iloc[0]["年化"])) and (fmt % md == fmt % float(q.iloc[0]["回落"]))
                recon.append({"段": sg, "策略": nm, "本件100%年化": c, "本件100%回落": md, "排名表年化": (q.iloc[0]["年化"] if len(q) else None),
                              "排名表回落": (q.iloc[0]["回落"] if len(q) else None), "比較精度": fmt, "相同": bool(ok)})
            # 每事件損益（A、D、C、B），多顆取中位
            for arm in ("A", "B", "C", "D"):
                ne = len(EP[arm][0])
                for j in range(ne):
                    vals = [EP[arm][i][j] for i in range(len(runs))]
                    pn = np.array([(v_["窗尾市值"] + v_["併入窗尾市值"] - v_["投入"]) if arm == "B" else (v_["回收"] + v_["窗尾市值"] - v_["投入"]) for v_ in vals])
                    inv = np.array([v_["投入"] for v_ in vals])
                    with np.errstate(invalid="ignore", divide="ignore"):
                        rr = np.where(inv > 0, pn / inv, np.nan)
                    v0 = vals[0]
                    erows.append({"段": sg, "策略": nm, "臂": arm, "事件": str(cal_ev[v0["e"]].date()), "加碼日": str(cal_ev[v0["d"]].date()),
                                  "賣回日": (str(cal_ev[v0["s"]].date()) if v0["s"] is not None else "窗內未賣回"),
                                  "持股檔中位": float(np.median([v_["持股檔"] for v_ in vals])), "買不到檔中位": float(np.median([v_["買不到"] for v_ in vals])),
                                  "T2 有加碼顆比例": float(np.mean([v_["T2加碼"] for v_ in vals])),
                                  "投入中位（窗首＝1）": float(np.median(inv)), "損益中位（窗首＝1）": float(np.median(pn)), "加碼部位報酬中位": float(np.nanmedian(rr)) if np.isfinite(rr).any() else np.nan,
                                  "損益平均": float(np.mean(pn)), "顆數": len(vals)})
            log(f"[{sg} {nm}] {len(runs)} 顆｜事件 {len(ctx['evs'])}｜對帳 {'同' if ok else '⛔ 不同'}｜{time.time() - T0:.0f}s")
    T = pd.DataFrame(rows); EVR = pd.DataFrame(erows)
    os.makedirs(OUT, exist_ok=True)
    T.to_csv(os.path.join(OUT, "table.csv"), index=False, float_format="%.10g", encoding="utf-8")
    EVR.to_csv(os.path.join(OUT, "event_pnl.csv"), index=False, float_format="%.10g", encoding="utf-8")
    json.dump(recon, open(os.path.join(OUT, "recon.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    bad = [r for r in recon if not r["相同"]]
    S = {"讀法寫死": TIME, "指數": f"origin/main {sha}", "大盤": "git:origin/main:data/history/market_tri.csv", "事件閘": g, "對帳不同": len(bad),
         "必附": NOTES, "秒": round(time.time() - T0)}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(T, EVR, recon, S)
    log(f"[run] {len(T)} 列｜事件列 {len(EVR)}｜對帳不同 {len(bad)}｜{time.time() - T0:.0f}s")
    if bad:
        raise SystemExit(f"⛔ 100% 臂 ≠ 排名表：{bad}")


# ═════════════ split：兩帳分開報（使用者 10/21 更正：「平常策略用策略資金，加碼是加碼資金，不要歸在一起」）═════════════
SPLIT_OUT = os.path.join(OUT, "split")
ARMS_SPLIT = {"A": dict(w=0.0, mode="A", pool="cash"), "B′": dict(w=0.0, mode="Bp", pool="cash"),
              "C′": dict(w=0.0, mode="A", pool="0050"), "D": dict(w=0.0, mode="D", pool="cash")}
SPLIT_NAME = {"A": "A 平時現金；大跌隔天全數加碼策略持股、收復隔天賣回", "B′": "B′ 不在收復賣：每檔跟策略同日同價出場、回現金等下次",
              "C′": "C′ 平時放 0050；大跌賣 0050 買策略持股、收復賣回再買 0050", "D": "D 大跌加一半、−5% 再加另一半；收復一起賣回"}
OLD_OF = {"A": ("A", 0.8), "C′": ("C", 0.8), "D": ("D", 0.6)}     # 加碼帳 ＝ (舊臂淨值 − w·E/E_x) ÷ (1 − w)（金額線性 ⇒ 恆等，閘）
SPLIT_NOTES = NOTES[:4] + NOTES[4:5] + NOTES[6:] + [
    "加碼帳大部分時間是閒置現金（A／B′／D 不計息），窗內年化會被拉低；要看每次事件報酬",
    "策略帳 ＝ 100% 策略本身（＝ 排名表數字，不變）；加碼帳是另一筆獨立資金（窗首 ＝ 1），兩帳 ⛔ 不合併",
    "同時機對照：同一筆加碼帳、同事件日、同收復日賣回，改買 0050（開盤進出、0.385%）／大盤報酬指數（指數無開盤 ⇒ e＋1 收盤進、D0＋1 收盤出、不含成本）／"
    "大跌 4 檔 F9 前 4（＝ researchMktDrop_addon2 丙「平時現金、事件全額」曲線；C′ 對 乙「平時 0050、事件撥 100%」曲線；只有 2015 起）"]


def split_runs_metrics(nav, info, out, statf, base):
    c, m = statf(nav)
    cum = nav[-1] / (nav[0] if base == "close" else 1.0) - 1.0
    ev = []
    for r in info:
        if r["投入"] > 1e-12:
            ev.append({"k": r["k"], "r": (r["回收"] + r["窗尾市值"] - r["投入"]) / r["投入"], "天": (r["持有至"] - r["d"] + 1) if r["持有至"] is not None else np.nan})
    rr = np.array([z["r"] for z in ev]) if ev else np.array([])
    use = float(np.mean(out["lots"] / nav)) if out else np.nan
    return {"年化": c, "回落": m, "累計": cum, "事件數": len(ev), "事件報酬平均": float(rr.mean()) if len(rr) else np.nan,
            "事件報酬中位": float(np.median(rr)) if len(rr) else np.nan, "事件報酬最差": float(rr.min()) if len(rr) else np.nan,
            "事件勝率": float((rr > 0).mean()) if len(rr) else np.nan, "平均投入天數": float(np.nanmean([z["天"] for z in ev])) if ev else np.nan,
            "資金使用率": use}, {z["k"]: z for z in ev}


def split_comps(wn, cal, x, y, evs, Wd, TR):
    """同時機對照（與策略無關）⇒ {名: (年化, 回落, 累計, {k: 報酬}, 說明)}。"""
    n = len(cal); out = {}
    statf = (lambda nav: stat_close(nav, x, y, n))
    m, _ = map_events(evs, cal, x, y)
    S50 = Wd["S"]["0050"]
    dummy = np.ones(n)
    for nm, (CL_, OP_, cost) in (("同時機買 0050", (S50["CL"][:1], S50["OP"][:1], COST_ETF)),
                                ("同時機買大盤報酬指數", (BR.on_cal(TR, cal)[0][None, :], BR.on_cal(TR, cal)[0][None, :], 0.0))):
        nav, info = overlay(dummy, x, y, m, ARMS_SPLIT["A"], make_etf_fn([0], [1.0], CL_, OP_), CL_, OP_, cost, Wd["O50"], Wd["C50"], "close")
        c, md = statf(nav)
        out[nm] = (c, md, nav[-1] / nav[0] - 1, {r["k"]: (r["回收"] + r["窗尾市值"] - r["投入"]) / r["投入"] for r in info if r["投入"] > 0})
    c, md = statf(Wd["C50"][x:y + 1] / Wd["C50"][x])
    out["一直抱 0050"] = (c, md, Wd["C50"][y] / Wd["C50"][x] - 1, {})
    mdp = os.path.join(BR.OUT, "mktdrop_curves.npz")
    if wn == "主":
        Z = np.load(mdp); dts = pd.to_datetime(Z["dates"])
        for key, nm in (("丙_平時現金事件全額", "同時機買大跌 4 檔 F9 前 4（平時現金）"), ("乙_撥100%", "平時 0050、大跌撥 100% 買 F9 前 4（C′ 對照）")):
            e_ = pd.Series(Z[key], index=dts).reindex(cal).to_numpy(float)
            if not np.all(np.isfinite(e_[x:y + 1])):
                continue
            c, md = BR.estat(e_, x, y)
            per = {z["k"]: e_[(z["s"] if z["s"] is not None else y)] / e_[z["e"]] - 1 for z in m}
            out[nm] = (c, md, e_[y] / e_[x] - 1, per)
    return out


def cmd_split(a):
    from backtest import researchLev2 as L2
    T0 = time.time()
    sha, evs = load_events()
    g = events_gate(evs)
    if g["日期不同"] or g["收復日不同"]:
        raise SystemExit(f"⛔ 事件閘不過 {g}")
    TR = BR.read_series("git:origin/main:data/history/market_tri.csv")
    RK = pd.read_csv(os.path.join(BR.OUT, "rank.csv"), dtype=str)
    TR1 = tie_ref()
    SX = six4_world()
    rows, erows, crow, recon = [], [], [], []
    ident_max = 0.0
    worlds = {}
    for sg, (wn, a_, b_) in SEGS.items():
        if wn not in worlds:
            worlds[wn] = load_world(wn)
        Wd = worlds[wn]; cal = Wd["cal"]; n = len(cal); x, y = BR.seg_pos(cal, a_, b_)
        m, miss = map_events(evs, cal, x, y)
        if miss:
            raise SystemExit(f"⛔ {sg} 事件日不在日曆 {miss}")
        COMPS = {f"{cal[x].date()}～{cal[y].date()}": split_comps(wn, cal, x, y, evs, Wd, TR)}
        strat = list(Wd["S"].items()) + ([("六四 v1", None)] if sg in ("確認", "探索") else [])
        for nm, s in strat:
            if nm == "六四 v1":
                w0, w1 = (a_, b_) if sg == "確認" else SIX4_EXP
                X = SX["X"]; i0, i1 = X["pos"][w0], X["pos"][w1]
                eq, _ = BR.six4_eq(w0, w1)
                E = np.full(len(SX["cal"]), np.nan); E[i0:i1 + 1] = eq
                mm, _ = map_events(evs, SX["cal"], i0, i1)
                runs = [(E, make_etf_fn([0, 1], [0.6, 0.4], SX["CL"], SX["OP"]))]
                ctx = dict(x=i0, y=i1, evs=mm, CL=SX["CL"], OP=SX["OP"], cost=COST_ETF, O50=SX["OP"][0], C50=SX["CL"][0], base="open")
                statf = L2.perf
                win = f"{w0}～{w1}"
                if win not in COMPS:
                    xx, yy = BR.seg_pos(cal, w0, w1)
                    COMPS[win] = split_comps(wn, cal, xx, yy, evs, Wd, TR)
                cal_ev = SX["cal"]
            else:
                if s["P"] is None:
                    r_, w_ = s["etf"]
                    runs = [(s["E"][0], make_etf_fn(r_, w_, s["CL"], s["OP"]))]
                else:
                    runs = [(E_, make_hold_fn(P, s["CL"], s["OP"])) for E_, P in zip(s["E"], s["P"])]
                ctx = dict(x=x, y=y, evs=m, CL=s["CL"], OP=s["OP"], cost=s["cost"], O50=Wd["O50"], C50=Wd["C50"], base="close")
                statf = (lambda nav, x=x, y=y, n=n: stat_close(nav, x, y, n))
                win = f"{cal[x].date()}～{cal[y].date()}"
                cal_ev = cal
            CP = COMPS[win]
            # 策略帳（＝ 100%）
            c100 = [statf(E_[ctx["x"]:ctx["y"] + 1] / (E_[ctx["x"]] if ctx["base"] == "close" else 1.0)) for E_, _ in runs]
            c0, m0 = float(np.median([z[0] for z in c100])), float(np.median([z[1] for z in c100]))
            rows.append({"段": sg, "策略": nm, "帳": "策略帳（100% 策略本身）", "臂": "策略帳", "窗": win, "顆數": len(runs), "年化": c0, "回落": m0, "比值": AS.ratio(c0, m0)})
            q = RK[(RK["段"] == sg) & (RK["策略"] == nm)]
            if nm == "六四 v1" and sg == "探索":
                q = q[q["排名"] == "另表"]
            fmt = "%.8g" if nm in ("營量 v1", "營飆 v1") else "%.10g"
            if nm == TIE_NAME:
                wref, cref, mref = TR1[(wn, sg)]
                cc, mc = (c0, m0) if wref == win else BR.estat(runs[0][0], *BR.seg_pos(cal, *wref.split("～")))
                ok = fmt % cc == fmt % float(cref) and fmt % mc == fmt % float(mref); refs = (cref, mref)
            else:
                ok = len(q) == 1 and fmt % c0 == fmt % float(q.iloc[0]["年化"]) and fmt % m0 == fmt % float(q.iloc[0]["回落"])
                refs = (q.iloc[0]["年化"], q.iloc[0]["回落"]) if len(q) else (None, None)
            recon.append({"段": sg, "策略": nm, "策略帳年化": c0, "策略帳回落": m0, "對帳值": refs, "精度": fmt, "相同": bool(ok)})
            for arm, cfg in ARMS_SPLIT.items():
                if nm == "0050" and arm == "C′":
                    cfg = dict(cfg, mode="none")
                MS, EVS = [], []
                for E_, fn in runs:
                    o_ = {}
                    nav, info = overlay(E_, ctx["x"], ctx["y"], ctx["evs"], cfg, fn, ctx["CL"], ctx["OP"], ctx["cost"], ctx["O50"], ctx["C50"], ctx["base"], out=o_)
                    if arm in OLD_OF:                                           # 恆等閘：加碼帳 ＝ (舊臂 − w·E) ÷ (1−w)
                        oa, ow = OLD_OF[arm]
                        ocfg = ARMS[oa] if not (nm == "0050" and oa == "C") else dict(ARMS[oa], mode="none")
                        old, _ = overlay(E_, ctx["x"], ctx["y"], ctx["evs"], ocfg, fn, ctx["CL"], ctx["OP"], ctx["cost"], ctx["O50"], ctx["C50"], ctx["base"])
                        Ew = E_[ctx["x"]:ctx["y"] + 1] / (E_[ctx["x"]] if ctx["base"] == "close" else 1.0)
                        ident_max = max(ident_max, float(np.max(np.abs((old - ow * Ew) / (1 - ow) - nav))))
                    mt, evd = split_runs_metrics(nav, info, o_ if cfg["mode"] != "none" else None, statf, ctx["base"])
                    if cfg["mode"] == "none":
                        mt["資金使用率"] = 0.0
                    MS.append(mt); EVS.append(evd)
                med = {k: float(np.nanmedian([z[k] for z in MS])) if any(np.isfinite(z[k]) for z in MS) else np.nan for k in MS[0]}
                r = {"段": sg, "策略": nm, "帳": "加碼帳", "臂": arm, "臂說明": SPLIT_NAME[arm], "窗": win, "顆數": len(runs), **med, "比值": AS.ratio(med["年化"], med["回落"])}
                comps = (("同時機買 0050", "同時機買大盤報酬指數", "同時機買大跌 4 檔 F9 前 4（平時現金）") if arm != "C′"
                         else ("一直抱 0050", "平時 0050、大跌撥 100% 買 F9 前 4（C′ 對照）"))
                for cn in comps:
                    if cn not in CP:
                        continue
                    cc, cm, ccum, cper = CP[cn]
                    r[f"差年化_對{cn}"] = med["年化"] - cc; r[f"差回落_對{cn}"] = med["回落"] - cm
                    if cper:
                        diffs = []
                        for evd in EVS:
                            dd = [evd[k]["r"] - cper[k] for k in evd if k in cper]
                            diffs.append((np.mean(dd) if dd else np.nan, np.mean(np.array(dd) > 0) if dd else np.nan, len(dd)))
                        r[f"逐事件差平均_對{cn}"] = float(np.nanmedian([z[0] for z in diffs]))
                        r[f"贏的事件比例_對{cn}"] = float(np.nanmedian([z[1] for z in diffs]))
                rows.append(r)
                ks = sorted({k for evd in EVS for k in evd})
                for k in ks:
                    vals = [evd[k] for evd in EVS if k in evd]
                    z0 = next(zz for zz in ctx["evs"] if zz["k"] == k)
                    er = {"段": sg, "策略": nm, "臂": arm, "事件": str(cal_ev[z0["e"]].date()),
                          "收復賣回日": str(cal_ev[z0["s"]].date()) if z0["s"] is not None else "窗內未賣回",
                          "有投入顆數": len(vals), "報酬中位": float(np.median([v["r"] for v in vals])), "報酬平均": float(np.mean([v["r"] for v in vals])),
                          "投入天數中位": float(np.nanmedian([v["天"] for v in vals]))}
                    if arm == "A":
                        for cn in ("同時機買 0050", "同時機買大盤報酬指數", "同時機買大跌 4 檔 F9 前 4（平時現金）"):
                            if cn in CP and k in CP[cn][3]:
                                er[cn] = CP[cn][3][k]
                    erows.append(er)
            log(f"[split {sg} {nm}] {len(runs)} 顆｜策略帳對帳 {'同' if ok else '⛔ 不同'}｜{time.time() - T0:.0f}s")
        for wkey, CP in COMPS.items():
            for cn, (cc, cm, ccum, cper) in CP.items():
                rr = np.array(list(cper.values())) if cper else np.array([])
                crow.append({"段": sg, "窗": wkey, "對照": cn, "年化": cc, "回落": cm, "比值": AS.ratio(cc, cm), "累計": ccum, "事件數": len(rr),
                             "事件報酬平均": float(rr.mean()) if len(rr) else np.nan, "事件報酬中位": float(np.median(rr)) if len(rr) else np.nan,
                             "事件報酬最差": float(rr.min()) if len(rr) else np.nan, "事件勝率": float((rr > 0).mean()) if len(rr) else np.nan})
    os.makedirs(SPLIT_OUT, exist_ok=True)
    T = pd.DataFrame(rows); EVR = pd.DataFrame(erows); C = pd.DataFrame(crow)
    T.to_csv(os.path.join(SPLIT_OUT, "table.csv"), index=False, float_format="%.10g", encoding="utf-8")
    EVR.to_csv(os.path.join(SPLIT_OUT, "event_returns.csv"), index=False, float_format="%.10g", encoding="utf-8")
    C.to_csv(os.path.join(SPLIT_OUT, "comps.csv"), index=False, float_format="%.10g", encoding="utf-8")
    bad = [r for r in recon if not r["相同"]]
    S = {"讀法": "split（兩帳分開報；使用者 10/21 更正）", "指數": f"origin/main {sha}", "事件閘": g, "策略帳對帳不同": len(bad),
         "加碼帳 vs 舊臂恆等式最大差（A／C′／D）": ident_max, "必附": SPLIT_NOTES, "秒": round(time.time() - T0)}
    json.dump(recon, open(os.path.join(SPLIT_OUT, "recon.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(S, open(os.path.join(SPLIT_OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[split] {len(T)} 列｜事件列 {len(EVR)}｜對照 {len(C)}｜策略帳對帳不同 {len(bad)}｜恆等式最大差 {ident_max:.2e}｜{time.time() - T0:.0f}s")
    if bad or ident_max > 1e-9:
        raise SystemExit(f"⛔ split 閘不過：對帳不同 {len(bad)}、恆等式 {ident_max}")


def pct(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.2f}%"


def pp(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.2f} 點"


def write_md(T, EVR, recon, S):
    md = ["## 所有策略「大盤大跌時加碼自己」（描述，裁定 seq437）", "", f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TIME}", ""]
    md += [f"- {x}" for x in NOTES] + [""]
    for sg in SEGS:
        G = T[T["段"] == sg]
        if G.empty:
            continue
        md += [f"### {sg}｜{G.iloc[0]['窗']}", "", "| 策略 | 臂 | 年化 | 回落 | 比值 | 對大盤 | 差年化 對100% | 差比值 對100% | 差年化 對80/20 | 差比值 對80/20 |", "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in G.iterrows():
            md.append(f"| {r['策略']} | {r['臂']} | {pct(r['年化'])} | {pct(r['回落'])} | {r['比值']:.2f} | {r['對大盤']} | {pp(r['差年化_對100%'])} | {r['差比值_對100%']:+.2f} | "
                      f"{pp(r['差年化_對80%＋20%現金'])} | {r['差比值_對80%＋20%現金']:+.2f} |")
        md.append("")
    open(os.path.join(OUT, "table.md"), "w", encoding="utf-8").write("\n".join(md))


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["events", "build-yf", "build-pth", "build-tie", "dry", "run", "split"])
    ap.add_argument("--part", default="主"); ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    od = SPLIT_OUT if a.cmd == "split" else OUT              # split 的紀錄 ⛔ 不寫進已 commit 的 run.log
    os.makedirs(od, exist_ok=True)
    LOGF = os.path.join(od, "run.log")
    log(f"===== researchDropAddSelf {a.cmd} {a.part if a.cmd.startswith('build') else ''}｜{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）")
    {"events": cmd_events, "build-yf": build_yf, "build-pth": build_pth, "build-tie": build_tie, "dry": cmd_dry, "run": cmd_run, "split": cmd_split}[a.cmd](a)


if __name__ == "__main__":
    main()
