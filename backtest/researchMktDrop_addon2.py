# -*- coding: utf-8 -*-
"""大盤大跌「連續大跌時再加碼」描述性測試（⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）——回測線計算子代理，2026-10-17。
使用者：「連續大跌時（第一次大跌後還沒收復又大跌），再加碼會不會比較好？」目前規則：持有中不加碼、收復目標固定為第一次大跌前一日收盤。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（v1／初測／v3／fund／quality／f9／mktdrop_cands 只 import 重用；v1 逐股快取只讀）；用語「假訊號」。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_addon2 [--procs 3]

═══ 讀法（寫死於第一次跑之前，2026-10-17 14:05 台北；⚠ 已看過 v1／v3／yl／fund／quality／f9 的首次進場結果 ⇒ 事後提問、只描述）═══
 A0 事件、世界、母體、首次進場、主出場、成本、配對、②組合層：⭐ 全部照 seq1 v1／seq3 v3——V1.index_events（q2 擴張視窗最差 2%、波段第一天、
    同時只處理一個事件 ⇒ 28 個接受事件：早年 10、2015～2021 7、2022～ 11）、MD.load_world／assemble（v1 逐股快取只讀）、V1.bpath／curve2／wstats、
    v3.sel_pre（C＋ 名單）；首次進場 ＝ 事件日 t 收盤決定、t＋1 開盤買、等權；買不到剔除
 A1 加碼觸發（讀報酬之前寫死；「持有中」＝ 指數列 t0 ＜ ta ＜ 收復日 D0（加權收盤 ≥ t0 前一日收盤的第一天；未收復 ⇒ 到資料尾）；每次持有最多加碼 1 次 ⇒ 取第一次觸及那天）
    T1 ＝ 持有中又有一天 r(ta) ≤ q2(ta)（⭐ 同一門檻判定、用原始大跌日 RAW，不要求「前 20 日內沒有別的大跌日」；另在觸發表描述「只算波段第一天」的次數）
    T2 ＝ 持有中加權收盤 ≤ 第一次事件日收盤 ×（1 − 5%）的第一天
    T3 ＝ 同上 ×（1 − 10%）
    觸發日 ta 要在世界日曆內且 ta＋1 仍在世界內（否則記「世界外」不加碼）
 A2 加碼：觸發日 ta 收盤決定、ta＋1 開盤買，⭐ 與首次相同金額（事件層：首次 1 份 ＋ 加碼 1 份）
    方式甲 ＝ ta 當天重新產的 C＋（v3.sel_pre：R1 母體 ta 當天報酬最低 ceil(10%) 且可得最近一期月營收年增 ＞ 0）：全買／F9 前 4／隨機 4 檔 2,000 次
    方式乙 ＝ 加碼原本首次買到的同一批（C＋ 全買那批／F9 前 4 那 4 檔／隨機那 4 檔〔逐抽配對〕；A 0050、B 00631L 就是再買同一檔）；
             ta＋1 開盤買不到、或首次那份已在 ta＋1 開盤以前出場（壞根強制、下市）⇒ 該檔不加碼
    加碼那份全部買不到 ⇒ 「加碼未進場」、該事件等同不加碼（照報次數）
    F9 前 4（甲）：ta 當天 C＋ 內 F6、F7、Q 逐檔分數 ＝ researchMktDrop_fund／_quality 同一套函式在 ta 以 PIT 重算（大母體 F7、C＋ 內 F6／Q；
             財報 t57sb01 上傳日 ＜ ta），F6／F7／Q 先取 6 位有效數字後 researchMktDrop_f9.add_f9／order；⭐ 程式先用同一段程式重算 18 個原事件，
             與 f9/features.csv 對帳（F9 前 4 名單一致才採用）；原事件的 F9 前 4 一律讀 f9/features.csv
    隨機 4 檔：首次 ＝ default_rng([fund.SEED, 事件序號(28 事件), 4])、同 pick／fund／f9 抽法（N 改 4；N＝1～3 先對帳 f9/summary.csv）；
             甲加碼 ＝ default_rng([fund.SEED, 事件序號, 4, 100 ＋ 觸發號(1～3)])、從 ta 當天 C＋ 抽；乙 ＝ 同一抽的 4 檔
 A3 出場（⛔ 不設天數）：主臂 ＝ 首次＋加碼全部在「加權收盤 ≥ 第一次大跌前一日收盤」的隔日開盤賣（逐股用 MD.exits_core，把 ta 的收復日換成 D0；
             壞根前收盤強制、下市最後收盤、窗尾計值，同 v1）；描述格 ＝ 加碼那份改用「加權收盤 ≥ 加碼觸發前一日收盤」隔日開盤賣（＝ v1 快取 ta 欄出場），首次那份不動
 A4 事件層（每事件）：不加碼 ＝ 首次那份淨報酬（＝ v1／v3／f9 既有，對帳）；加碼後 ＝ 金額加權 ＝（首次淨報酬 ＋ 加碼淨報酬）÷ 2（未觸發／加碼未進場 ⇒ ＝ 不加碼）；
             加碼那份自己的淨報酬；最大帳面虧損 ＝ 持有期間（首次買進到最後一份賣完）每日收盤 (首次市值 ＋ 加碼市值) ÷ 已投入金額 − 1 的最低值（毛、未扣成本、≥0 記 0；
             不加碼 ＝ v3「持有中最低相對買價」）；另報「以首次金額為 1」的最低帳面損益；持有天數 ＝ 首次買進到最後一份賣完（日曆位置差，＝ v3 等待交易日）
             報：平均、中位、最差、虧 ＞10% 次數（只算有觸發的事件；另附全部事件平均）；隨機 ＝ 2,000 抽：平均 ＝ 全部抽的平均、中位 ＝ 逐事件抽平均的中位、
             最差／虧 ＞10% 次數 ＝ 每抽段內值的平均（同 f9 慣例）
             段：A 0050、C＋ 全買 ＝ 2006～2014（早年世界）、2015～2021、2022～、全部；B 00631L ＝ 2015 起（2014-10 上市）；F9 前 4、隨機 4 ＝ 2015～2021、2022～、2015～
 A5 組合層 ②：平時抱 0050；事件 t＋1 開盤撥總資產 20% 到首次部位（＝ V1.curve2 同式：扣 X 來回＋0050 來回）；觸發 ta＋1 開盤再撥「前一日收盤總資產」20% 到加碼部位
             （同扣成本；上限 40%）；各部位賣完那一刻換回 0050；首次部位被略過（重疊）的事件不加碼；年化／最大回落 ＝ V1.wstats（research13.window_stats）
             比：不加碼（＝ curve2，對帳 v3/portfolio.csv）、一直抱 0050；候選 A（⭐ A 的 ② 照 v1 ≡ 一直抱 0050，加碼也是換自己 ⇒ 不動）、B、C＋ 全買、F9 前 4（隨機不做組合層）
 A6 必附：事件少（觸發的只有個位數到十來個）、事後提問、多重比較（3 觸發 × 2 方式 × 2 出場 × 5 候選）、正2 含槓桿、早年 reduce_v2 減資假飆股約 0.3%（剩 22 筆未解釋）、
             成本 個股 0.585%／ETF 0.385% 來回、未含滑價；只描述、不判定
 A7 對帳（不過 ⇒ 停）：首次那份 A／B／C＋ 報酬、等待天數、最低相對買價 ＝ v3/event_rows；C＋ 逐檔淨報酬 ＝ fund/features.csv；F9 N＝1～3 選中與報酬 ＝ f9/event_picks；
             隨機 N＝1～3 段平均 ＝ f9/summary；曲線（無加碼）＝ V1.curve2 ＝ v3/portfolio ②；逐股出場重算（原收復日）＝ v1 快取；乙主臂加碼賣出日 ＝ 首次賣出日
── 事後註（照實記）──
 ① 14:08 第一次全跑：早年全部對帳過；主世界 F9 重算 18 原事件 F7、Q 逐位元同，F6 最大差 0.015、前 4 名單 17/18 同 ⇒ 停（對帳閘照設計擋下）。
    查因：子項全部 6 位有效數字內相同；差在 fund 的 rv_yoy／tc_r60／tc_d52／tc_rs／tc_drop 讀自 c_rows（%.6g），同值同名次 ⇒ 本程式這 5 欄先取 6 位有效數字再排（原事件、觸發日同一套）；
    ⛔ 觸發、加碼、出場、統計規則都沒改；第一次跑停在 F9 對帳、沒有任何加碼報酬輸出（執行者沒看到加碼結果）
輸出 backtest/resultsMktDrop/addon2/：MktDrop_addon2.json、triggers.csv、trigger_counts.csv、event_rows.csv、summary.csv、portfolio.csv、addon_list.csv、
     concentration.csv、f9_trigger_features.csv、recon.csv、run.log；大檔 ~/mktdropwork/addon2/
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest/resultsMktDrop/addon2")
WORK = os.path.expanduser("~/mktdropwork/addon2")
V1WORK = os.path.expanduser("~/mktdropwork/v1")
RD = os.path.join(REPO, "backtest/resultsMktDrop")
TIME = "2026-10-17 14:05（台北；讀法寫死、第一次跑之前）"
# ── 觸發條件（寫死）──
T2_DROP = 0.05
T3_DROP = 0.10
TRIGS = ["T1", "T2", "T3"]
TN = {"T1": "持有中又一天 r ≤ q2（原始大跌日）", "T2": "收盤比第一次事件日收盤再跌 ≥5%", "T3": "收盤比第一次事件日收盤再跌 ≥10%"}
METHODS = ["甲", "乙"]
MN = {"甲": "當天重新產的 C＋（全買／F9 前 4／隨機 4）", "乙": "加碼原本那一批（同股／同 ETF）"}
ARMS = ["主", "描述"]
AN = {"主": "全部在收復第一次大跌前一日收盤時隔日開盤賣", "描述": "加碼那份收復加碼觸發前一日收盤時隔日開盤賣"}
CANDS = ["A", "B", "C+", "F9", "R4"]
CN = {"A": "0050", "B": "00631L（正2）", "C+": "C＋ 全買", "F9": "F9 前 4", "R4": "C＋ 隨機 4 檔（2,000 次）"}
N4 = 4
W_SLEEVE = 0.20
W_ADD = 0.20
COST_STK, COST_ETF = 0.00585, 0.00385
SEGS_ALL = ["2006～2014", "2015～2021", "2022～"]
NOTES = ["描述性測試：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議",
         "⚠ 事件少：28 個接受事件（早年 10、2015～2021 7、2022～ 11），出現觸發的只有個位數到十來個；同一波大跌的觸發高度相關 ⇒ 差異多半是少數幾次決定",
         "⚠ 事後提問：首次進場的 v1／v3／C＋／F9 結果都已看過；加碼規則是看過之後才問的",
         "⚠ 多重比較：3 觸發 × 2 方式 × 2 出場 × 5 候選 × 段 ⇒ 格子很多，碰巧好看的會有",
         "收復才賣的勝率有一部分來自規則本身（等多久都等）；加碼後持有期間不變（主臂）⇒ 加碼的效果主要來自「更低的價格買進」與「多放一倍錢」",
         "正2 的結果含槓桿本身的效果；早年（2006～2014）含減資假飆股約 0.3%（reduce_v2，剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；2005-01～2007-06 只有上市",
         "F9 前 4、隨機 4 只有 2015 起（Q 沒有早年財報）；F9 是使用者採用、未驗證",
         "成本：個股 0.585% 來回、ETF 0.385%；未含滑價；最大帳面虧損為毛值（未扣成本）"]
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def s6(x):
    return float(f"{x:.6g}") if np.isfinite(x) else np.nan


# ═════════════ 觸發 ═════════════
def find_triggers(EV, df):
    """⇒ {接受事件指數列 i0: {"D0": 收復列 or n, "T1": 列 or None, "T1首日": 列 or None, "T2": .., "T3": .., 跌幅...}}"""
    cl = EV["cl"]; n = EV["n"]; raw = EV["RAW"]["q2"]; first = EV["FIRST"]["q2"]
    out = {}
    for i0 in np.flatnonzero(EV["ACC"]["q2"]):
        D0 = int(EV["rec"][i0]) if EV["rec"][i0] >= 0 else n
        win = np.arange(i0 + 1, D0)
        o = {"D0": D0}
        h = win[raw[win]] if len(win) else win
        o["T1"] = int(h[0]) if len(h) else None
        h = win[first[win]] if len(win) else win
        o["T1首日"] = int(h[0]) if len(h) else None
        for k, d in (("T2", T2_DROP), ("T3", T3_DROP)):
            h = win[cl[win] <= cl[i0] * (1 - d)] if len(win) else win
            o[k] = int(h[0]) if len(h) else None
        o["持有中最低收盤相對事件日"] = float(cl[win].min() / cl[i0] - 1) if len(win) else np.nan
        o["持有中原始大跌日數"] = int(raw[win].sum()) if len(win) else 0
        out[int(i0)] = o
    return out


# ═════════════ 逐股出場重算（加碼主臂：把 ta 的收復日換成 D0）═════════════
def exit_job(a):
    from backtest import researchMktDrop as MD
    wn, sid = a
    W = _G[wn]; MD.D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    B = MD.R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    next_bad = np.asarray(B["next_bad"])
    bad = np.asarray(next_bad[:nb] == np.arange(nb), bool)
    for p in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p, "left"))
        if k < nb:
            bad[k] = True
    TRD = W["TRD"][i]; O = W["O"][i]; DNL = W["DNL"][i]
    sell_ok = TRD[idx] & np.isfinite(O[idx]) & (O[idx] > 0) & ~DNL[idx]
    end_ok = bool(idx[-1] == n0 - 1)
    ex0, _, _ = MD.exits_core(idx, o, h, l, c, bad, sell_ok, end_ok, W["Darr"], n0)
    ex1, _, _ = MD.exits_core(idx, o, h, l, c, bad, sell_ok, end_ok, _G["Darr_main_" + wn], n0)
    return sid, (idx, ex0["主"], ex1["主"])


# ═════════════ F9 逐檔分數（fund／quality／f9 同一套函式；任意日期、主世界）═════════════
def f9_features(rows, procs, log):
    """rows：[{事件日, sid, ret1, yoy, hi24}]（C＋ 全名單、含買不到）⇒ DataFrame（F6、F7、Q、r6、r7、rQ、F9…，F6／F7／Q 已取 6 位有效數字）。
    ＝ researchMktDrop_fund.main（U1～U2b，C＋ 部分）＋ researchMktDrop_quality.main（W2～W3）＋ researchMktDrop_f9.add_f9 的逐行搬移，只把事件清單換成參數。"""
    from backtest import data as D
    from backtest import researchExit5 as EX5
    from backtest import rerun17 as RR
    from backtest import researchAddOn as RA
    from backtest import researchMktDrop_fund as FU
    from backtest import researchMktDrop_quality as QL
    from backtest import researchMktDrop_f9 as F9
    WD = {"早年": RA.EOTC, "主": RR.H2D}
    CP = pd.DataFrame(rows).reset_index(drop=True)
    rev_e, rly_e, _ = EX5.load_revenue(WD["早年"]); rev_m, rly_m, _ = EX5.load_revenue(WD["主"])
    rev = rev_m.combine_first(rev_e).sort_index(); rly = rly_m.combine_first(rly_e).sort_index()
    D.DATA = WD["主"]; cal = D.load_calendar()
    FU._G["cal"] = {WD["主"]: cal}
    AVW = EX5.avail_pos(list(rev.index), cal); AVA = np.array([AVW[p] for p in rev.index], np.int64)
    rv3 = []; ychk = []; hchk = []
    for sid, ev in zip(CP["sid"], CP["事件日"]):
        p = int(cal.searchsorted(pd.Timestamp(ev)))
        E = [e for e in EX5.rev_events(sid, rev, rly, AVW, len(cal)) if e[0] <= p]
        last3 = [e[1] for e in E[-3:]]
        rv3.append(float(np.mean(last3)) if len(last3) == 3 and np.isfinite(last3).all() else np.nan)
        ychk.append(E[-1][1] if E else np.nan); hchk.append((np.nan if (not E or E[-1][2] is None) else float(E[-1][2])) if E else np.nan)
    CP["rv_yoy"] = CP["yoy"]; CP["rv_yoy3"] = rv3; CP["rv_hi24"] = CP["hi24"]
    d_ = np.abs(CP["yoy"].to_numpy(float) - np.asarray(ychk, float)); dh = np.asarray(hchk, float); hh = CP["hi24"].to_numpy(float)
    info = {"年增（世界矩陣 vs fund 日曆重算）最大差": float(np.nanmax(d_)) if len(d_) else None,
            "24月新高不同": int(np.sum((np.isfinite(dh) != np.isfinite(hh)) | (np.isfinite(dh) & np.isfinite(hh) & (dh != hh))))}
    FIN, _ = FU.load_fin()
    FF = pd.DataFrame([FU.fin_feats(FIN.get(s), pd.Timestamp(e)) for s, e in zip(CP["sid"], CP["事件日"])])
    for c in FF.columns:
        CP[c] = FF[c].to_numpy()
    dates = sorted(CP["事件日"].unique())
    us = FU.universe_sids(WD["主"], dates[0], dates[-1])
    mk = pd.read_csv(os.path.join(WD["主"], "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last")
    mk = dict(zip(mk["stock_id"], mk["market"]))
    sids = sorted(set(us) | set(CP["sid"]))
    BR = FU.run_jobs([(WD["主"], s, mk.get(s, "twse"), dates) for s in sids], procs, "F9 分數")
    for c in FU.BCOLS[:11]:
        CP[c] = [BR.get((s, e), {}).get(c, np.nan) for s, e in zip(CP["sid"], CP["事件日"])]
    r1c = np.array([BR.get((s, e), {}).get("chk_ret1", np.nan) for s, e in zip(CP["sid"], CP["事件日"])], float)
    info["當日報酬（矩陣 vs load_bars）最大相對差"] = float(np.nanmax(np.abs(r1c - CP["ret1"].to_numpy(float)) / np.maximum(1, np.abs(r1c))))
    TD, _ = FU.load_tdcc()
    CP["ch_big"] = [FU.tdcc_chg(TD, s, pd.Timestamp(e), 4)[0] for s, e in zip(CP["sid"], CP["事件日"])]
    CP["tc_r60"] = CP["chk_r60"]; CP["tc_d52"] = CP["chk_d52"]; CP["tc_ma60"] = CP["chk_ma60"]; CP["tc_rs"] = CP["chk_r20"]; CP["tc_drop"] = -CP["ret1"]
    # 事後註②：fund 這幾欄讀自 deep/c_rows.csv（%.6g 存檔）⇒ 先取 6 位有效數字再排名次（同值才會同名次）
    for c in ("rv_yoy", "tc_r60", "tc_d52", "tc_rs", "tc_drop"):
        CP[c] = [s6(x) for x in CP[c].to_numpy(float)]
    F7R = []
    for ev in dates:
        p = int(cal.searchsorted(pd.Timestamp(ev))); t = pd.Timestamp(ev)
        cps = set(CP.loc[CP["事件日"] == ev, "sid"]); rr = []
        for s in sorted(set(us) | cps):
            b = BR.get((s, ev))
            if b is None:
                continue
            inU = bool(s in us and b.get("valid") == 1.0 and np.isfinite(b.get("amt20", np.nan)) and b["amt20"] >= 5e7)
            if not inU and s not in cps:
                continue
            r = {"事件日": ev, "sid": s, "inU": inU, "inC": s in cps, "e1": b["e1"], "e2": b["e2"], "d1": b["d1"], "d2": b["d2"]}
            r.update(FU.rev7(s, rev, rly, AVA, p)); r.update(FU.fin7(FIN.get(s), t))
            r["d3"], _ = FU.tdcc_chg(TD, s, t, 1)
            rr.append(r)
        T = pd.DataFrame(rr); T = FU.f7_scores(T, T["inU"].to_numpy(bool))
        F7R.append(T[T["inC"]][["事件日", "sid", "inU", "F7A", "F7"]])
    CP = CP.merge(pd.concat(F7R), on=["事件日", "sid"], how="left")
    CP = FU.add_scores(CP, "事件日")
    FINq, _ = QL.load_fin(); DV, mkq, smk = QL.load_div()
    FQ = pd.DataFrame([QL.fin_q(FINq.get(s), pd.Timestamp(e)) for s, e in zip(CP["sid"], CP["事件日"])], index=CP.index)
    for c in FQ.columns:
        CP[c] = FQ[c]
    dv = [QL.div_q(DV, mkq, smk, s, pd.Timestamp(e)) for s, e in zip(CP["sid"], CP["事件日"])]
    CP["q_div"] = [x[0] for x in dv]
    CP = QL.add_q(CP, "事件日")
    for c in ("F6", "F7", "F7A", "Q"):
        CP[c] = [s6(x) for x in CP[c].to_numpy(float)]
    CP = F9.add_f9(CP, "事件日")
    info["F6缺"] = int(CP["F6"].isna().sum()); info["F7缺"] = int(CP["F7"].isna().sum()); info["Q缺"] = int(CP["Q"].isna().sum())
    return CP, info


# ═════════════ 事件層工具 ═════════════
def spath(W, Mx, I, t, end=None):
    """逐股毛值路徑（相對買價、日收盤、已賣固定在賣價）＝ V1.bpath 的逐股版；⇒ (P[len(I), L], e, end, sp, kd, g)。"""
    n0 = W["n0"]; e = t + 1
    sp = Mx["SP"]["主"][I, t].astype(np.int64); sx = Mx["SX"]["主"][I, t]; bp = Mx["BP"][I, t]; kd = Mx["SK"]["主"][I, t]
    if end is None:
        end = int(min(max(sp.max(), e), n0 - 1))
    P_ = Mx["C"][I, e:end + 1] / bp[:, None]
    tt = np.arange(e, end + 1)[None, :]
    P_ = np.where(tt >= sp[:, None], (sx / bp)[:, None], P_)
    return P_, e, end, sp, kd, sx / bp - 1.0


def combine(V1_, e1, end1, V2_, e2, end2):
    """V1_／V2_：(D, L) 毛值路徑（D 抽）；end1／end2：(D,)。V2_ 為 None ⇒ 只有首次。
    ⇒ (最大帳面虧損 相對已投入, 最低帳面損益 以首次為 1, 持有天數)，各 (D,)。"""
    D_ = V1_.shape[0]
    if V2_ is None:
        mn = np.minimum(0.0, np.nanmin(V1_, axis=1) - 1.0)
        return mn, mn, (end1 - e1).astype(float)
    L = max(e1 + V1_.shape[1], e2 + V2_.shape[1]) - e1
    v1 = np.empty((D_, L)); v1[:, :V1_.shape[1]] = V1_; v1[:, V1_.shape[1]:] = V1_[:, -1:]
    v2 = np.zeros((D_, L)); o2 = e2 - e1
    v2[:, o2:o2 + V2_.shape[1]] = V2_; v2[:, o2 + V2_.shape[1]:] = V2_[:, -1:]
    inv = np.ones(L); inv[o2:] = 2.0
    tot = v1 + v2
    rel = np.minimum(0.0, np.nanmin(tot / inv - 1.0, axis=1)); ab = np.minimum(0.0, np.nanmin(tot - inv, axis=1))
    return rel, ab, (np.maximum(end1, end2) - e1).astype(float)


def mstats(X, prefix):
    """X：(事件, 抽)；平均 ＝ 全部；中位 ＝ 逐事件抽平均的中位；最差／虧＞10% ＝ 每抽段內值的平均。"""
    X = np.asarray(X, float)
    if X.size == 0:
        return {f"{prefix}_平均": np.nan, f"{prefix}_中位": np.nan, f"{prefix}_最差": np.nan, f"{prefix}_虧＞10%次數": np.nan}
    return {f"{prefix}_平均": float(np.nanmean(X)), f"{prefix}_中位": float(np.nanmedian(np.nanmean(X, axis=1))),
            f"{prefix}_最差": float(np.nanmean(np.nanmin(X, axis=0))), f"{prefix}_虧＞10%次數": float(np.nanmean((X < -0.10).sum(axis=0)))}


def curve2_add(n0, paths, addp, BO, BC, cost):
    """＝ V1.curve2（平時 0050；事件 t＋1 開盤換 20% 到 X；全籃賣完換回）再加第二個部位：addp ＝ {首次進場位置 e0: (ea, end, V, reopen)}；
    加碼 ta＋1 開盤撥「前一日收盤總資產」20%（扣 X 來回＋0050 來回），賣完換回；首次部位被略過的事件不加碼。addp 空 ⇒ 與 curve2 逐位元同。"""
    by_e = {p[0]: p for p in paths}
    by_a = {}
    for e0, pa in addp.items():
        by_a.setdefault(pa[0], []).append((e0, pa))
    eq = np.ones(n0); core = 1.0; act = None; act2 = None; skipped = 0; skipped2 = 0; added = 0
    for j in range(1, n0):
        o_ = BO[j] if np.isfinite(BO[j]) and BO[j] > 0 else BC[j - 1]
        core *= o_ / BC[j - 1]
        prev2 = act2[4] * act2[2][j - 1 - act2[0]] if (act2 is not None and j - 1 >= act2[0]) else 0.0
        if j in by_e:
            if act is None:
                e0, end, V, reopen = by_e[j]
                tot = core + prev2; core = tot * (1 - W_SLEEVE) - prev2
                act = (e0, end, V, reopen, tot * W_SLEEVE * (1 - cost) * (1 - COST_ETF))
            else:
                skipped += 1
        if j in by_a:
            for e0p, (ea, end, V, reopen) in by_a[j]:
                if act is not None and act[0] == e0p and act2 is None:
                    prev1 = act[4] * act[2][j - 1 - act[0]] if j - 1 >= act[0] else 0.0
                    tot = core + prev1
                    core = core - tot * W_ADD
                    act2 = (ea, end, V, reopen, tot * W_ADD * (1 - cost) * (1 - COST_ETF)); added += 1
                else:
                    skipped2 += 1
        sl = 0.0
        if act is not None:
            e0, end, V, reopen, S0 = act
            if j == end and reopen:
                core += S0 * V[j - e0]
        if act2 is not None:
            ea, end2, V2, reopen2, S2 = act2
            if j == end2 and reopen2:
                core += S2 * V2[j - ea]
        core *= BC[j] / o_
        if act is not None:
            e0, end, V, reopen, S0 = act
            if j == end:
                if not reopen:
                    core += S0 * V[j - e0]
                act = None
            else:
                sl = S0 * V[j - e0]
        if act2 is not None:
            ea, end2, V2, reopen2, S2 = act2
            if j == end2:
                if not reopen2:
                    core += S2 * V2[j - ea]
                act2 = None
            else:
                sl += S2 * V2[j - ea]
        eq[j] = core + sl
    return eq, skipped, skipped2, added


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    from multiprocessing import Pool
    from backtest import researchMktDrop as MD
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop_v3 as V3
    from backtest import researchExit5 as EX5
    from backtest import researchMktDrop_fund as FU
    from backtest import researchMktDrop_f9 as F9
    MD.SEGS = V1.SEGS_V1
    S = {"件": "大盤大跌連續大跌再加碼（描述性測試、不計 N、不判定）", "讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法": "見程式檔頭 A0～A7",
         "必附": NOTES, "觸發": TN, "方式": MN, "出場": AN, "候選": CN, "閘": {}, "對帳": {}}
    REC = []

    def rec(name, val, ok, note=""):
        REC.append({"對帳": name, "值": val, "通過": bool(ok), "註": note}); log(f"[對帳] {name}：{val}｜{'✔' if ok else '✘'} {note}")
        if not ok:
            raise SystemExit(f"⛔ 對帳不過：{name} {val}")

    IXmd = MD.load_index(log)
    df = IXmd["df"]; EV = V1.index_events(df)
    ft = np.flatnonzero(EV["FIRST"]["q2"])
    if not np.array_equal(EV["rec"][ft], IXmd["rec"][ft]):
        raise SystemExit("⛔ q2 收復列與初測 rec 不同")
    TRG = find_triggers(EV, df)
    S["指數"] = {"origin/main sha": IXmd["sha"], "期間": f"{df['date'].iloc[0].date()}～{df['date'].iloc[-1].date()}", "q2 接受事件（全部）": int(EV["ACC"]["q2"].sum())}
    rev_e, rly_e, _ = EX5.load_revenue(MD.DB.WORLDS["早年"]["data"]); rev_m, rly_m, _ = EX5.load_revenue(MD.DB.WORLDS["主"]["data"])
    rev = rev_m.combine_first(rev_e).sort_index(); rly = rly_m.combine_first(rly_e).sort_index()
    V3R = pd.read_csv(os.path.join(RD, "v3/event_rows.csv"))
    V3R = V3R[(V3R["定義"] == "q2") & (V3R["出場"] == "主")]
    FF = pd.read_csv(os.path.join(RD, "fund/features.csv"), dtype={"sid": str}); FF["買得到"] = FF["買得到"].astype(str).str.lower().eq("true")
    F9F = pd.read_csv(os.path.join(RD, "f9/features.csv"), dtype={"sid": str}); F9F["買得到"] = F9F["買得到"].astype(str).str.lower().eq("true")
    evs_all = sorted(FF["事件日"].unique()); assert len(evs_all) == 28
    evidx = {e: k for k, e in enumerate(evs_all)}
    TRROWS = []; EROWS = []; ADDL = []; PORT = []; F9INFO = {}
    R4FIRST = {}                  # 隨機 N＝1～3 對帳用
    for wn in ("早年", "主"):
        W = MD.load_world(wn, IXmd, log); MD._G[wn] = W; _G[wn] = W
        PK = pickle.load(open(os.path.join(V1WORK, f"packs_{wn}.pkl"), "rb")); log(f"[逐股 {wn}] 讀 v1 快取（只讀）")
        EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
        M = MD.assemble(W, PK, EP, log)
        cal = W["cal"]; n0 = W["n0"]; BO, BC = W["BO"], W["BC"]; Sx = M["S"]
        AV = EX5.avail_pos(list(rev.index), cal)
        YOY = np.full((Sx, n0), np.nan); HI = np.full((Sx, n0), np.nan); ar = np.arange(n0)
        for r, s in enumerate(M["sids"]):
            ev = EX5.rev_events(s, rev, rly, AV, n0)
            if not ev:
                continue
            rA = np.array([e[0] for e in ev], np.int64)
            j = np.searchsorted(rA, ar, "right") - 1; ok = j >= 0; jj = np.maximum(j, 0)
            yv = np.array([e[1] for e in ev], float); hv = np.array([np.nan if e[2] is None else float(bool(e[2])) for e in ev])
            YOY[r, ok] = yv[jj[ok]]; HI[r, ok] = hv[jj[ok]]
        M["YOY"] = YOY
        datepos = {d: j for j, d in enumerate(cal)}
        segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
        evs = []
        for i in np.flatnonzero(EV["ACC"]["q2"]):
            p = datepos.get(df["date"].iloc[i])
            if p is not None and p + 1 < n0 and segof(p) is not None:
                evs.append((p, int(i)))
        # ── 觸發 → 世界位置 ──
        TW = {}
        for p, i in evs:
            T = TRG[i]; D0w = int(W["Darr"][p])
            exp = datepos.get(df["date"].iloc[T["D0"]], n0) if T["D0"] < len(df) else n0
            if D0w != exp:
                raise SystemExit(f"⛔ {cal[p].date()} Darr {D0w} ≠ 收復列 {exp}")
            tw = {}
            for k in TRIGS:
                ri = T[k]
                if ri is None:
                    tw[k] = None; continue
                pa = datepos.get(df["date"].iloc[ri])
                tw[k] = pa if (pa is not None and pa + 1 < n0 and pa < D0w) else "世界外"
            TW[p] = tw
            row = {"世界": wn, "段": segof(p), "事件日": str(cal[p].date()), "指數報酬": float(EV["r"][i]),
                   "收復日": (str(cal[D0w].date()) if D0w < n0 else "世界尾仍未收復"), "收復等待（指數交易日）": (T["D0"] - i if T["D0"] < len(df) else None),
                   "持有中最低收盤相對事件日": T["持有中最低收盤相對事件日"], "持有中原始大跌日數": T["持有中原始大跌日數"],
                   "T1首日（只算波段第一天）": (str(df["date"].iloc[T["T1首日"]].date()) if T["T1首日"] is not None else None)}
            for k in TRIGS:
                v = tw[k]
                row[k] = (None if v is None else (v if isinstance(v, str) else str(cal[v].date())))
                if v is not None and not isinstance(v, str):
                    row[f"{k}當天指數報酬"] = float(EV["r"][T[k]]); row[f"{k}收盤相對事件日"] = float(EV["cl"][T[k]] / EV["cl"][i] - 1)
            TRROWS.append(row)
        # ── 主臂逐股出場重算 ──
        Darr_main = W["Darr"].copy()
        need = set()
        for p, i in evs:
            for k in TRIGS:
                pa = TW[p][k]
                if pa is None or isinstance(pa, str):
                    continue
                Darr_main[pa] = W["Darr"][p]
                need |= {M["sids"][r] for r in V3.sel_pre(M, p, "C+")} | {M["sids"][r] for r in V3.sel_pre(M, pa, "C+")}
        _G["Darr_main_" + wn] = Darr_main
        t1 = time.time()
        with Pool(a.procs) as pool:
            RES = dict(pool.imap_unordered(exit_job, [(wn, s) for s in sorted(need)], chunksize=8))
        SPa = M["SP"]["主"].copy(); SXa = M["SX"]["主"].copy(); SKa = M["SK"]["主"].copy()
        rix = {s: r for r, s in enumerate(M["sids"])}
        bad0 = 0
        for s, v in RES.items():
            idx, e0, e1 = v
            sp0, sx0, kd0 = PK[s]["ex"]["主"]
            if not (np.array_equal(e0[0], sp0) and np.allclose(e0[1], sx0, equal_nan=True, rtol=0, atol=0) and np.array_equal(e0[2], kd0)):
                bad0 += 1
            r = rix[s]; SPa[r, idx] = e1[0]; SXa[r, idx] = e1[1]; SKa[r, idx] = e1[2]
        rec(f"{wn} 逐股出場重算（原收復日）＝ v1 快取（{len(RES)} 檔）", bad0, bad0 == 0)
        W2 = dict(W); W2["Darr"] = Darr_main
        for jx, s in enumerate(MD.ETFS):
            epm = MD.etf_pack(W2, s)
            if epm is None:
                continue
            r = Sx + jx; idx = epm["idx"]; sp_, sx_, kd_ = epm["ex"]["主"]
            SPa[r, idx] = sp_; SXa[r, idx] = sx_; SKa[r, idx] = kd_
        Mm = dict(M); Mm["SP"] = {"主": SPa}; Mm["SX"] = {"主": SXa}; Mm["SK"] = {"主": SKa}
        log(f"[主臂出場 {wn}] 重算 {len(RES)} 檔＋ETF｜{time.time() - t1:.0f}s")
        MX = {"主": Mm, "描述": M}
        # ── F9：原事件讀 f9/features；觸發日重算（主世界）──
        F9T = None
        if wn == "主":
            rows = []
            for p, i in evs:
                ds = str(cal[p].date())
                for r in V3.sel_pre(M, p, "C+"):
                    rows.append({"事件日": ds, "sid": M["sids"][r], "ret1": float(M["RET"][r, p]), "yoy": float(YOY[r, p]), "hi24": float(HI[r, p])})
            pas = sorted({TW[p][k] for p, _ in evs for k in TRIGS if TW[p][k] is not None and not isinstance(TW[p][k], str)})
            for pa in pas:
                ds = str(cal[pa].date())
                for r in V3.sel_pre(M, pa, "C+"):
                    rows.append({"事件日": ds, "sid": M["sids"][r], "ret1": float(M["RET"][r, pa]), "yoy": float(YOY[r, pa]), "hi24": float(HI[r, pa])})
            fp = os.path.join(WORK, "f9_features_v2.pkl")
            key = sorted((x["事件日"], x["sid"]) for x in rows)
            if os.path.exists(fp) and pickle.load(open(fp, "rb"))[0] == key:
                _, F9T, F9INFO = pickle.load(open(fp, "rb")); log(f"[F9] 讀快取 {fp}")
            else:
                F9T, F9INFO = f9_features(rows, a.procs, log)
                pickle.dump((key, F9T, F9INFO), open(fp, "wb"), protocol=5)
            log(f"[F9 重算] {F9INFO}")
            # 對帳：18 原事件 重算 vs f9/features
            evd = [str(cal[p].date()) for p, _ in evs]
            X = F9T[F9T["事件日"].isin(evd)].merge(F9F[["事件日", "sid", "F6", "F7", "Q", "F9"]], on=["事件日", "sid"], how="outer", suffixes=("", "_f9"), indicator=True)
            nonboth = int((X["_merge"] != "both").sum())
            dmax = {c: float((X[c] - X[c + "_f9"]).abs().max()) for c in ("F6", "F7", "Q", "F9")}
            same4 = 0
            for e in evd:
                o1 = F9.order(F9T[F9T["事件日"] == e], "F9").head(N4)["sid"].tolist()
                o2 = F9.order(F9F[F9F["事件日"] == e], "F9").head(N4)["sid"].tolist()
                same4 += int(o1 == o2)
            F9INFO["原 18 事件重算 vs f9/features"] = {"名單不同列": nonboth, "最大差": dmax, "F9 前 4 名單相同事件數": f"{same4}/{len(evd)}"}
            rec("F9 重算（18 原事件）前 4 名單 ＝ f9/features", f"{same4}/{len(evd)}；名單不同列 {nonboth}；最大差 {dmax}", same4 == len(evd) and nonboth == 0)
            F9T[F9T["事件日"].isin([str(cal[x].date()) for x in pas])].to_csv(os.path.join(OUT, "f9_trigger_features.csv"), index=False, float_format="%.6g", encoding="utf-8")
        # ── 事件層 ──
        hold0050 = BC / BC[0]
        PATHS = {}                     # (候選, 觸發, 方式, 出場) ⇒ {"first": [...], "add": {e0: path}}
        r4chk_rows = []
        for p, i in evs:
            sg = segof(p); ds = str(cal[p].date())
            CPl = V3.sel_pre(M, p, "C+")                                  # 首次 C＋ 名單（買不到之前）
            for cd in CANDS:
                if cd == "B" and wn == "早年":
                    continue
                if cd in ("F9", "R4") and wn == "早年":
                    continue
                cost = COST_ETF if cd in ("A", "B") else COST_STK
                # 首次那份
                if cd in ("A", "B"):
                    rr = Sx + (0 if cd == "A" else 1)
                    first_sets = [np.array([rr]) if M["BUY"][rr, p] else np.array([], int)]
                elif cd == "C+":
                    first_sets = [CPl[M["BUY"][CPl, p]]]
                elif cd == "F9":
                    d9 = F9F[F9F["事件日"] == ds]
                    top = F9.order(d9, "F9").head(N4)["sid"].tolist()
                    rr_ = np.array([rix[s] for s in top], int)
                    first_sets = [rr_[M["BUY"][rr_, p]]]
                    for N in (1, 2, 3):                                   # 對帳 f9/event_picks
                        R4FIRST.setdefault("F9", []).append((ds, N, F9.order(d9, "F9").head(N)["sid"].tolist()))
                else:
                    dF = FF[FF["事件日"] == ds]                            # 同 fund 列序
                    lst = np.array([rix[s] for s in dF["sid"]], int)
                    if not np.array_equal(np.sort(lst), np.sort(CPl)):
                        raise SystemExit(f"⛔ {ds} fund C＋ 名單 ≠ v3.sel_pre")
                    m = len(lst)
                    for N in (1, 2, 3, N4):
                        rng = np.random.default_rng([FU.SEED, evidx[ds], N])
                        ix = np.argsort(rng.random((FU.NR, m)), axis=1)[:, :N]
                        if N < N4:
                            r4chk_rows.append((ds, N, lst, ix))
                    picks = lst[ix]                                        # (NR, ≤4)
                    first_sets = None
                # ── 確定性候選（A、B、C＋、F9）──
                if cd != "R4":
                    I1 = first_sets[0]
                    base = {"世界": wn, "段": sg, "事件日": ds, "候選": cd, "首次檔數": int(len(I1))}
                    if len(I1):
                        P1, e1, end1, sp1, kd1, g1 = spath(W, M, I1, p)
                        V1_ = np.nanmean(P1, axis=0)[None, :]
                        net1 = (1 + float(np.mean(g1))) * (1 - cost) - 1
                        e_, end_, Vb, ro1 = V1.bpath(W, M, I1, p, "主")
                        if not (e_ == e1 and end_ == end1 and np.allclose(Vb, V1_[0], equal_nan=True)):
                            raise SystemExit(f"⛔ 逐股路徑 ≠ bpath {ds} {cd}")
                        mn0, ab0, hd0 = combine(V1_, e1, np.array([end1]), None, None, None)
                    else:
                        net1 = 0.0; mn0 = ab0 = np.array([0.0]); hd0 = np.array([0.0]); e1 = p + 1; end1 = p + 1; V1_ = None; ro1 = True
                    if cd in ("A", "B", "C+"):
                        q = V3R[(V3R["世界"] == wn) & (V3R["候選"] == cd) & (V3R["日期"] == ds)]
                        if len(q) and str(q["進場"].iloc[0]) == "True":
                            dd = max(abs(float(q["報酬"].iloc[0]) - net1), abs(float(q["持有中最低相對買價"].iloc[0]) - mn0[0]),
                                     abs(float(q["等待交易日（買進到賣完）"].iloc[0]) - hd0[0]))
                            S["對帳"].setdefault("首次 vs v3 最大差", 0.0)
                            S["對帳"]["首次 vs v3 最大差"] = max(S["對帳"]["首次 vs v3 最大差"], dd)
                            S["對帳"]["首次 vs v3 比對筆數"] = S["對帳"].get("首次 vs v3 比對筆數", 0) + 1
                        elif len(I1):
                            raise SystemExit(f"⛔ {ds} {cd} v3 沒進場、本程式有")
                    if len(I1):
                        PATHS.setdefault((cd, "無", "無", "無"), {"first": [], "add": {}})["first"].append((e1, end1, Vb, ro1))
                    for k in TRIGS:
                        pa = TW[p][k]
                        for mt in METHODS:
                            if cd in ("A", "B") and mt == "甲":
                                continue
                            for arm in ARMS:
                                Mx = MX[arm]
                                row = {**base, "觸發": k, "方式": mt, "出場": arm, "觸發日": (None if pa is None else (pa if isinstance(pa, str) else str(cal[pa].date()))),
                                       "不加碼_報酬": net1, "不加碼_最大帳面虧損": float(mn0[0]), "不加碼_持有天數": float(hd0[0])}
                                I2 = np.array([], int)
                                if pa is not None and not isinstance(pa, str) and len(I1) or (pa is not None and not isinstance(pa, str) and mt == "甲"):
                                    if mt == "甲":
                                        if cd == "C+":
                                            c2 = V3.sel_pre(M, pa, "C+"); I2 = c2[M["BUY"][c2, pa]]
                                        else:                                  # F9
                                            dt = F9T[F9T["事件日"] == str(cal[pa].date())]
                                            top2 = F9.order(dt, "F9").head(N4)["sid"].tolist() if len(dt) else []
                                            r2 = np.array([rix[s] for s in top2], int); I2 = r2[M["BUY"][r2, pa]] if len(r2) else r2
                                            row["加碼選中"] = " ".join(top2)
                                    else:
                                        held = (2 * M["SP"]["主"][I1, p].astype(np.int64) + (M["SK"]["主"][I1, p] != 0)) > 2 * (pa + 1)
                                        I2 = I1[held & M["BUY"][I1, pa]]
                                row["觸發"] = k; row["有觸發"] = bool(pa is not None and not isinstance(pa, str))
                                row["加碼檔數"] = int(len(I2))
                                if len(I2):
                                    P2, e2, end2, sp2, kd2, g2 = spath(W, Mx, I2, pa)
                                    V2_ = np.nanmean(P2, axis=0)[None, :]
                                    net2 = (1 + float(np.mean(g2))) * (1 - cost) - 1
                                    if arm == "主" and mt == "乙":
                                        sp1x = M["SP"]["主"][I2, p]; kd1x = M["SK"]["主"][I2, p]
                                        S["對帳"]["乙主臂加碼賣出 ≠ 首次賣出（檔）"] = S["對帳"].get("乙主臂加碼賣出 ≠ 首次賣出（檔）", 0) + int(np.sum((sp2 != sp1x) | (kd2 != kd1x)))
                                        S["對帳"]["乙主臂比對檔次"] = S["對帳"].get("乙主臂比對檔次", 0) + int(len(I2))
                                    if len(I1):
                                        mn, ab, hd = combine(V1_, e1, np.array([end1]), V2_, e2, np.array([end2]))
                                        comb = (net1 + net2) / 2
                                    else:                                       # 首次空手（F9 全買不到）⇒ 只有加碼那份
                                        mn, ab, hd = combine(V2_, e2, np.array([end2]), None, None, None); comb = net2
                                    e_, end_, Vb2, ro2 = V1.bpath(W, Mx, I2, pa, "主")
                                    if not (e_ == e2 and end_ == end2 and np.allclose(Vb2, V2_[0], equal_nan=True)):
                                        raise SystemExit(f"⛔ 加碼逐股路徑 ≠ bpath {ds} {cd} {k} {mt} {arm}")
                                    PATHS.setdefault((cd, k, mt, arm), {"first": [], "add": {}})["add"][e1] = (e2, end2, Vb2, ro2)
                                    row.update({"加碼進場": True, "加碼份_報酬": net2, "加碼份_持有天數": float(end2 - e2), "加碼後_報酬": comb,
                                                "加碼後_最大帳面虧損": float(mn[0]), "加碼後_最低帳面損益（首次＝1）": float(ab[0]), "加碼後_持有天數": float(hd[0]),
                                                "加碼份_賣出日": str(cal[end2].date()), "差（加碼後−不加碼）": comb - net1})
                                else:
                                    row.update({"加碼進場": False, "加碼後_報酬": net1, "加碼後_最大帳面虧損": float(mn0[0]),
                                                "加碼後_最低帳面損益（首次＝1）": float(ab0[0]), "加碼後_持有天數": float(hd0[0]), "差（加碼後−不加碼）": 0.0})
                                EROWS.append(row)
                    continue
                # ── 隨機 4 檔（2,000 抽）──
                NRd = picks.shape[0]
                Pall, e1, endall, spall, kdall, gall = spath(W, M, lst, p)
                buy1 = M["BUY"][lst, p]
                pk_ix = ix                                                 # (NR, 4) ⇒ lst（fund 列序）位置
                bmask = buy1[pk_ix]                                       # 買得到
                cnt1 = bmask.sum(axis=1)
                gm1 = np.where(cnt1 > 0, np.where(bmask, gall[pk_ix], 0.0).sum(axis=1) / np.maximum(cnt1, 1), np.nan)
                net1d = np.where(cnt1 > 0, (1 + gm1) * (1 - cost) - 1, 0.0)
                Pm = np.where(bmask[:, :, None], Pall[pk_ix], np.nan)      # (NR, N, L)
                with np.errstate(invalid="ignore"):
                    V1d = np.nanmean(Pm, axis=1)                          # (NR, L)
                V1d = np.where(cnt1[:, None] > 0, V1d, 1.0)
                end1d = np.where(cnt1 > 0, np.minimum(np.max(np.where(bmask, spall[pk_ix], -1), axis=1), n0 - 1), e1)
                end1d = np.maximum(end1d, e1)
                mn0, ab0, hd0 = combine(V1d, e1, end1d, None, None, None)
                base = {"世界": wn, "段": sg, "事件日": ds, "候選": cd, "首次檔數": float(cnt1.mean())}
                for k in TRIGS:
                    pa = TW[p][k]
                    for mt in METHODS:
                        for arm in ARMS:
                            Mx = MX[arm]
                            row = {**base, "觸發": k, "方式": mt, "出場": arm, "觸發日": (None if pa is None else (pa if isinstance(pa, str) else str(cal[pa].date()))),
                                   "有觸發": bool(pa is not None and not isinstance(pa, str)),
                                   "不加碼_報酬": float(net1d.mean()), "不加碼_最大帳面虧損": float(mn0.mean()), "不加碼_持有天數": float(hd0.mean())}
                            D_ = {"不加碼_報酬": net1d, "不加碼_最大帳面虧損": mn0, "不加碼_持有天數": hd0}
                            if row["有觸發"]:
                                if mt == "甲":
                                    l2 = V3.sel_pre(M, pa, "C+"); m2 = len(l2)
                                    rng = np.random.default_rng([FU.SEED, evidx[ds], N4, 100 + TRIGS.index(k) + 1])
                                    ix2 = np.argsort(rng.random((FU.NR, m2)), axis=1)[:, :N4] if m2 else np.zeros((FU.NR, 0), int)
                                    P2all, e2, end2all, sp2all, kd2all, g2all = spath(W, Mx, l2, pa) if m2 else (None, pa + 1, pa + 1, None, None, None)
                                    b2 = M["BUY"][l2, pa][ix2] if m2 else np.zeros((FU.NR, 0), bool)
                                    P2src, sp2src, g2src = P2all, sp2all, g2all
                                    pk2 = ix2
                                else:
                                    held = (2 * M["SP"]["主"][lst, p].astype(np.int64) + (M["SK"]["主"][lst, p] != 0)) > 2 * (pa + 1)
                                    P2all, e2, end2all, sp2all, kd2all, g2all = spath(W, Mx, lst, pa)
                                    b2 = (bmask & held[pk_ix] & M["BUY"][lst, pa][pk_ix])
                                    P2src, sp2src, g2src = P2all, sp2all, g2all
                                    pk2 = pk_ix
                                cnt2 = b2.sum(axis=1)
                                if b2.shape[1]:
                                    gm2 = np.where(cnt2 > 0, np.where(b2, g2src[pk2], 0.0).sum(axis=1) / np.maximum(cnt2, 1), np.nan)
                                    net2d = np.where(cnt2 > 0, (1 + gm2) * (1 - cost) - 1, np.nan)
                                    Pm2 = np.where(b2[:, :, None], P2src[pk2], np.nan)
                                    with np.errstate(invalid="ignore"):
                                        V2d = np.nanmean(Pm2, axis=1)
                                    end2d = np.where(cnt2 > 0, np.minimum(np.max(np.where(b2, sp2src[pk2], -1), axis=1), n0 - 1), e2)
                                    end2d = np.maximum(end2d, e2)
                                else:
                                    net2d = np.full(NRd, np.nan); V2d = None
                                has2 = cnt2 > 0
                                if has2.any():
                                    V2f = np.where(has2[:, None], V2d, 1.0)
                                    # 首次空手的抽 ⇒ 只有加碼那份（V1＝1 不影響已投入；照實：以已投入計）
                                    mn, ab, hd = combine(V1d, e1, end1d, V2f, e2, end2d)
                                    mnA, abA, hdA = combine(V2f, e2, end2d, None, None, None)
                                    only2 = cnt1 == 0
                                    mn = np.where(only2, mnA, mn); ab = np.where(only2, abA, ab); hd = np.where(only2, hdA, hd)
                                    comb = np.where(only2, net2d, (net1d + np.nan_to_num(net2d)) / 2)
                                    mn = np.where(has2, mn, mn0); ab = np.where(has2, ab, ab0); hd = np.where(has2, hd, hd0); comb = np.where(has2, comb, net1d)
                                    hd2 = np.where(has2, (end2d - e2).astype(float), np.nan)
                                else:
                                    mn, ab, hd, comb, hd2 = mn0, ab0, hd0, net1d, np.full(NRd, np.nan)
                                D_.update({"加碼份_報酬": net2d, "加碼份_持有天數": hd2, "加碼後_報酬": comb, "加碼後_最大帳面虧損": mn,
                                           "加碼後_最低帳面損益（首次＝1）": ab, "加碼後_持有天數": hd, "差（加碼後−不加碼）": comb - net1d})
                                row.update({"加碼檔數": float(cnt2.mean()), "加碼進場": bool(has2.any()), "加碼進場抽比例": float(has2.mean()),
                                            **{kk: float(np.nanmean(vv)) for kk, vv in D_.items()}})
                            else:
                                D_.update({"加碼後_報酬": net1d, "加碼後_最大帳面虧損": mn0, "加碼後_最低帳面損益（首次＝1）": ab0, "加碼後_持有天數": hd0,
                                           "差（加碼後−不加碼）": np.zeros(NRd)})
                                row.update({"加碼進場": False, **{kk: float(np.nanmean(vv)) for kk, vv in D_.items()}})
                            row["_draws"] = D_
                            EROWS.append(row)
        # 隨機 N＝1～3 段平均 對帳 f9/summary（主世界）
        if wn == "主":
            dmx = 0.0
            F9S = pd.read_csv(os.path.join(RD, "f9/summary.csv"))
            segev = {"2015～2021": [str(cal[p].date()) for p, _ in evs if segof(p) == "2015～2021"], "2022～": [str(cal[p].date()) for p, _ in evs if segof(p) == "2022～"]}
            segev["2015～（18事件）"] = segev["2015～2021"] + segev["2022～"]
            RS = {}
            for ds, N, lst_, ix in r4chk_rows:
                d = FF[FF["事件日"] == ds]
                net = np.where(d["買得到"].to_numpy(), d["淨報酬"].to_numpy(float), np.nan)
                v = net[ix]; fin = np.isfinite(v); cnt = fin.sum(axis=1)
                RS[(ds, N)] = np.where(cnt > 0, np.where(fin, v, 0.0).sum(axis=1) / np.maximum(cnt, 1), 0.0)
            for sg_, es in segev.items():
                for N in (1, 2, 3):
                    mine = float(np.stack([RS[(e, N)] for e in es]).mean())
                    ref = float(F9S[(F9S["段"] == sg_) & (F9S["方法"] == "隨機") & (pd.to_numeric(F9S["N"], errors="coerce") == N)]["平均"].iloc[0])
                    dmx = max(dmx, abs(mine - ref))
            rec("隨機 N＝1～3 段平均（同抽法）＝ f9/summary", f"{dmx:.2e}", dmx < 1e-5)
            # F9 N＝1～3 選中 ＝ f9/event_picks
            EPk = pd.read_csv(os.path.join(RD, "f9/event_picks.csv"), dtype={"選中": str}); EPk = EPk[EPk["分數"] == "F9"]
            badp = 0
            for ds, N, ids in R4FIRST.get("F9", []):
                q = EPk[(EPk["事件日"] == ds) & (EPk["N"] == N)]
                badp += int(str(q["選中"].iloc[0]).split() != ids)
            rec("F9 N＝1～3 選中（f9/features 排序）＝ f9/event_picks", f"{badp}/{len(R4FIRST.get('F9', []))}", badp == 0)
        # C＋ 逐檔淨報酬 ＝ fund/features
        mx = 0.0; nb_ = 0; nchk = 0
        for p, i in evs:
            ds = str(cal[p].date()); d = FF[FF["事件日"] == ds]
            for s, b, nr in zip(d["sid"], d["買得到"], d["淨報酬"]):
                r = rix[s]; bb = bool(M["BUY"][r, p]); nchk += 1
                if bb != bool(b):
                    nb_ += 1; continue
                if bb:
                    g = M["SX"]["主"][r, p] / M["BP"][r, p] - 1; my = (1 + g) * (1 - COST_STK) - 1
                    mx = max(mx, abs(my - nr) / max(1.0, abs(nr)))
        rec(f"{wn} C＋ 逐檔淨報酬 ＝ fund/features（{nchk} 檔次）", f"買得到不同 {nb_}；最大相對差 {mx:.2e}", nb_ == 0 and mx < 1e-5)
        # ── 組合層 ② ──
        h = {sg: V1.wstats(hold0050, x0, y0) for sg, (x0, y0) in W["segp"].items()}
        V3P = pd.read_csv(os.path.join(RD, "v3/portfolio.csv"))
        for cd in ("A", "B", "C+", "F9"):
            if (cd == "B" or cd == "F9") and wn == "早年":
                continue
            cost = COST_ETF if cd in ("A", "B") else COST_STK
            base_paths = PATHS.get((cd, "無", "無", "無"), {"first": []})["first"]
            if cd == "A":
                eq0 = hold0050.copy(); skp = 0
            else:
                eq0, skp = V1.curve2(n0, base_paths, BO, BC, cost)
                eqx, s1, s2, ad = curve2_add(n0, base_paths, {}, BO, BC, cost)
                dd = float(np.max(np.abs(eqx - eq0)))
                rec(f"{wn} {cd} 曲線（無加碼）curve2_add ＝ V1.curve2", f"{dd:.1e}", dd == 0.0)
            for sg, (x0, y0) in W["segp"].items():
                s0 = V1.wstats(eq0, x0, y0)
                if cd in ("A", "B", "C+"):
                    q = V3P[(V3P["世界"] == wn) & (V3P["段"] == sg) & (V3P["候選"] == cd)].iloc[0]
                    dd = max(abs(s0["年化"] - q["②平時0050換20%_年化"]), abs(s0["最大回落"] - q["②最大回落"]))
                    rec(f"{wn} {sg} {cd} ②（無加碼）＝ v3/portfolio", f"{dd:.1e}", dd < 5e-6)
                PORT.append({"世界": wn, "段": sg, "候選": cd, "觸發": "不加碼", "方式": "", "出場": "", "②年化": s0["年化"], "②最大回落": s0["最大回落"], "②比值": s0["比值"],
                             "一直抱0050_年化": h[sg]["年化"], "一直抱0050_最大回落": h[sg]["最大回落"], "加碼次數（段內）": 0, "略過": skp})
            for k in TRIGS:
                for mt in METHODS:
                    if cd in ("A", "B") and mt == "甲":
                        continue
                    for arm in ARMS:
                        PP = PATHS.get((cd, k, mt, arm), {"first": base_paths, "add": {}})
                        if cd == "A":
                            eq, s1, s2, ad = hold0050.copy(), 0, 0, len(PP["add"])
                        else:
                            eq, s1, s2, ad = curve2_add(n0, base_paths, PP["add"], BO, BC, cost)
                        for sg, (x0, y0) in W["segp"].items():
                            s_ = V1.wstats(eq, x0, y0); s0 = [r_ for r_ in PORT if r_["世界"] == wn and r_["段"] == sg and r_["候選"] == cd and r_["觸發"] == "不加碼"][0]
                            nad = sum(1 for e0, pa_ in PP["add"].items() if x0 <= e0 - 1 <= y0)
                            PORT.append({"世界": wn, "段": sg, "候選": cd, "觸發": k, "方式": mt, "出場": arm, "②年化": s_["年化"], "②最大回落": s_["最大回落"], "②比值": s_["比值"],
                                         "一直抱0050_年化": h[sg]["年化"], "一直抱0050_最大回落": h[sg]["最大回落"], "加碼次數（段內）": nad, "略過": s1, "加碼略過": s2,
                                         "年化差（加碼−不加碼）": s_["年化"] - s0["②年化"], "回落差（加碼−不加碼）": s_["最大回落"] - s0["②最大回落"],
                                         "年化差（加碼−0050）": s_["年化"] - h[sg]["年化"], "回落差（加碼−0050）": s_["最大回落"] - h[sg]["最大回落"],
                                         "備註": ("A 的 ② 照 v1 ≡ 一直抱 0050（換自己＝不動）" if cd == "A" else "")})
        log(f"[{wn}] 完｜{time.time() - T0:.0f}s")
        del M, Mm, MX, PK
    # ── 對帳彙總 ──
    rec(f"首次那份 A／B／C＋ ＝ v3/event_rows（{S['對帳'].get('首次 vs v3 比對筆數', 0)} 筆：報酬、最低相對買價、等待天數）", f"{S['對帳'].get('首次 vs v3 最大差', 0):.1e}",
        S["對帳"].get("首次 vs v3 最大差", 1) < 1e-9 and S["對帳"].get("首次 vs v3 比對筆數", 0) == 28 * 2 + 18)
    rec("乙主臂：加碼賣出日 ＝ 首次賣出日（檔次）", f"{S['對帳'].get('乙主臂加碼賣出 ≠ 首次賣出（檔）', 0)}/{S['對帳'].get('乙主臂比對檔次', 0)}",
        S["對帳"].get("乙主臂加碼賣出 ≠ 首次賣出（檔）", 0) == 0)
    # ── 輸出 ──
    TR = pd.DataFrame(TRROWS)
    TR.to_csv(os.path.join(OUT, "triggers.csv"), index=False, float_format="%.6g", encoding="utf-8")
    TC = []
    for nm, m_ in (("2005 起（28 事件）", TR["世界"].isin(["早年", "主"])), ("2006～2014", TR["段"] == "2006～2014"), ("2015 起（18 事件）", TR["世界"] == "主"),
                   ("2015～2021", TR["段"] == "2015～2021"), ("2022～", TR["段"] == "2022～")):
        q = TR[m_]
        row = {"範圍": nm, "接受事件數": len(q)}
        for k in TRIGS:
            row[f"{k} 次數"] = int(q[k].notna().sum() - (q[k] == "世界外").sum()); row[f"{k} 世界外"] = int((q[k] == "世界外").sum())
            row[f"{k} 事件"] = " ".join(q.loc[q[k].notna() & (q[k] != "世界外"), "事件日"])
        row["T1（只算波段第一天）次數"] = int(q["T1首日（只算波段第一天）"].notna().sum())
        TC.append(row)
    TC = pd.DataFrame(TC); TC.to_csv(os.path.join(OUT, "trigger_counts.csv"), index=False, encoding="utf-8")
    log("[觸發次數]\n" + TC.to_string(index=False))
    ER = pd.DataFrame([{k: v for k, v in r.items() if k != "_draws"} for r in EROWS])
    ER.to_csv(os.path.join(OUT, "event_rows.csv"), index=False, float_format="%.8g", encoding="utf-8")
    # 彙總
    SUM = []
    SEGSC = {"A": SEGS_ALL + ["全部"], "B": ["2015～2021", "2022～", "2015～"], "C+": SEGS_ALL + ["全部"], "F9": ["2015～2021", "2022～", "2015～"], "R4": ["2015～2021", "2022～", "2015～"]}
    for cd in CANDS:
        for k in TRIGS:
            for mt in METHODS:
                if cd in ("A", "B") and mt == "甲":
                    continue
                for arm in ARMS:
                    rs = [r for r in EROWS if r["候選"] == cd and r["觸發"] == k and r["方式"] == mt and r["出場"] == arm]
                    for sg in SEGSC[cd]:
                        if sg == "全部":
                            rr = rs
                        elif sg == "2015～":
                            rr = [r for r in rs if r["世界"] == "主"]
                        else:
                            rr = [r for r in rs if r["段"] == sg]
                        tr = [r for r in rr if r["有觸發"]]
                        ad = [r for r in tr if r.get("加碼進場")]

                        def mat(lst, key):
                            if not lst:
                                return np.zeros((0, 1))
                            if cd == "R4":
                                return np.stack([np.asarray(r["_draws"][key], float) for r in lst])
                            return np.array([[r[key]] for r in lst], float)
                        row = {"候選": cd, "名稱": CN[cd], "段": sg, "觸發": k, "方式": mt, "出場": arm, "事件數": len(rr), "有觸發事件數": len(tr), "加碼有進場事件數": len(ad),
                               "全部事件_不加碼平均": float(np.nanmean(mat(rr, "不加碼_報酬"))) if rr else np.nan,
                               "全部事件_加碼後平均": float(np.nanmean(mat(rr, "加碼後_報酬"))) if rr else np.nan}
                        row.update(mstats(mat(tr, "不加碼_報酬"), "觸發事件_不加碼報酬"))
                        row.update(mstats(mat(tr, "加碼後_報酬"), "觸發事件_加碼後報酬"))
                        row.update(mstats(mat(ad, "加碼份_報酬"), "加碼份報酬"))
                        dif = mat(tr, "差（加碼後−不加碼）")
                        row["觸發事件_差平均"] = float(np.nanmean(dif)) if dif.size else np.nan
                        row["觸發事件_加碼較好比例"] = float(np.nanmean(np.nanmean(dif, axis=1) > 1e-12)) if dif.size else np.nan
                        for kk, nm in (("不加碼_最大帳面虧損", "不加碼最大帳面虧損"), ("加碼後_最大帳面虧損", "加碼後最大帳面虧損"), ("加碼後_最低帳面損益（首次＝1）", "加碼後最低帳面損益（首次＝1）")):
                            X = mat(tr, kk)
                            row[f"{nm}_平均"] = float(np.nanmean(X)) if X.size else np.nan
                            row[f"{nm}_最差"] = float(np.nanmean(np.nanmin(X, axis=0))) if X.size else np.nan
                        for kk, nm in (("不加碼_持有天數", "不加碼持有天數"), ("加碼後_持有天數", "加碼後持有天數"), ("加碼份_持有天數", "加碼份持有天數")):
                            X = mat(ad if kk == "加碼份_持有天數" else tr, kk)
                            row[f"{nm}_平均"] = float(np.nanmean(X)) if X.size else np.nan
                            row[f"{nm}_最長"] = float(np.nanmean(np.nanmax(X, axis=0))) if X.size else np.nan
                        SUM.append(row)
    SUM = pd.DataFrame(SUM); SUM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    PO = pd.DataFrame(PORT); PO.to_csv(os.path.join(OUT, "portfolio.csv"), index=False, float_format="%.6g", encoding="utf-8")
    # 每次觸發清單（主臂、描述）＋ 集中度
    AL = ER[ER["有觸發"]].copy()
    AL = AL[["候選", "觸發", "方式", "出場", "世界", "段", "事件日", "觸發日", "加碼進場", "加碼檔數", "不加碼_報酬", "加碼份_報酬", "加碼後_報酬", "差（加碼後−不加碼）",
             "不加碼_最大帳面虧損", "加碼後_最大帳面虧損", "加碼後_最低帳面損益（首次＝1）", "不加碼_持有天數", "加碼後_持有天數", "加碼份_持有天數"]]
    AL.to_csv(os.path.join(OUT, "addon_list.csv"), index=False, float_format="%.6g", encoding="utf-8")
    CC = []
    for (cd, k, mt, arm), g in AL.groupby(["候選", "觸發", "方式", "出場"]):
        g = g[g["加碼進場"].astype(bool)]
        if not len(g):
            continue
        dsum = float(g["差（加碼後−不加碼）"].sum()); yr = g["事件日"].str[:4]
        top = g.loc[g["差（加碼後−不加碼）"].abs().idxmax()]
        CC.append({"候選": cd, "觸發": k, "方式": mt, "出場": arm, "加碼事件數": len(g), "差合計": dsum,
                   "2008／2020／2022 事件數": int(yr.isin(["2008", "2020", "2022"]).sum()),
                   "2008／2020／2022 差合計": float(g.loc[yr.isin(["2008", "2020", "2022"]), "差（加碼後−不加碼）"].sum()),
                   "影響最大事件": top["事件日"], "該事件差": float(top["差（加碼後−不加碼）"]),
                   "拿掉影響最大事件後差平均": float(g.drop(index=top.name)["差（加碼後−不加碼）"].mean()) if len(g) > 1 else np.nan,
                   "加碼份報酬 ＜0 次數": int((g["加碼份_報酬"] < 0).sum())})
    CC = pd.DataFrame(CC); CC.to_csv(os.path.join(OUT, "concentration.csv"), index=False, float_format="%.6g", encoding="utf-8")
    RC = pd.DataFrame(REC); RC.to_csv(os.path.join(OUT, "recon.csv"), index=False, encoding="utf-8")
    S["F9 重算"] = F9INFO; S["觸發次數"] = TC.to_dict("records")
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_addon2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
    show = SUM[SUM["出場"] == "主"][["候選", "段", "觸發", "方式", "有觸發事件數", "加碼有進場事件數", "觸發事件_不加碼報酬_平均", "觸發事件_加碼後報酬_平均", "加碼份報酬_平均",
                                    "加碼份報酬_最差", "觸發事件_差平均", "不加碼最大帳面虧損_最差", "加碼後最大帳面虧損_最差", "加碼後最低帳面損益（首次＝1）_最差"]]
    log("[事件層 主臂]\n" + show.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log("[組合層 ②]\n" + PO[["世界", "段", "候選", "觸發", "方式", "出場", "②年化", "②最大回落", "一直抱0050_年化", "一直抱0050_最大回落", "加碼次數（段內）", "年化差（加碼−不加碼）",
                            "回落差（加碼−不加碼）"]].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    log("[集中度]\n" + CC.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()
