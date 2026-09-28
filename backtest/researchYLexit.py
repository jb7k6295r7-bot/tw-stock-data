# -*- coding: utf-8 -*-
"""PREREG營量出場 seq1（台股策略線 登錄 sha 1a73bbae1829ca85；裁定 seq266 §二 發號、N ＋2；使用者主動要的兩件）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit [--procs 2] [--seeds 200] [--reps 200] [--shift-seeds 200]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchYLexit_check.py

甲：買進後收盤跌破買進價就先賣，之後收盤站回買進價再買回；到第 H 天照常結束。
乙：抱到第 k 天，用那天收盤當基準；之後收盤跌破就賣，沒跌破就繼續抱（上限 C 天）。
⭐ 先驗提醒（裁定 seq266 §二，結果句旁必附）：本專案停損類（營飆停損、回測 研究五／六、四類單獨）全部不如抱著。
⛔ 就算好過營量 v1 也不取代它；只進前瞻紀錄並列。

═══ 本體（⛔ 不改）═══
  營量 v1 ＝ researchT1fix #13：build_ctx(True)（rerun17.setup_and(t1=True)）sig13、simulate_mtm "H60" N20 default_rng(7000＋r)、log=[]、d_max=None、pick="relvol"、queue_days=0、
          stop_force ＝ stop_force_days(valid_from_data(全部股票), 主窗尾)
  營飆 v1（甲件描述）＝ #1：sig（t−1 大盤閘）、"H120" N10 default_rng(1000＋r)、stop_force 同
  早年 ＝ researchV.body_setup("main")（早年版面、只上市、2012-06-04～2014-12-31）＋ Y.sig_of(13／1, "mtm")、同參數＋stop_force（早年版面自算）
═══ 本線讀法（⭐ 看任何本件數字前寫死；登錄四處補讀照登錄）═══
 X1 「成本」P0 ＝ 該筆進場成交價 ＝ 引擎進場價 opens[sid][進場日]；「跌破／站回」看有效 K 棒收盤（引擎 closes），隔一根有效 K 棒開盤執行
 X2 甲：持有中（含進場當天收盤）收盤 ＜ P0×(1−b) ⇒ 下一根開盤賣；暫出中收盤 ≥ P0 ⇒ 下一根開盤用「這筆的錢」買回同一檔；
       名額保留、錢閒置；第 H 根（進場那根算第 1 根）收盤結束（不論在場與否）；最後一根收盤觸發的動作不執行
    ⭐ 實作 ＝ 逐筆合成價格序列（鍵 "代號#進場日"）：在場時 ＝ P0 × 在場價值 × 收盤 ÷ 最近買進價，暫出時凍結；每次買回乘 (1 − 0.585%)
       （＝ 每一趟「賣出＋買回」一趟來回成本、以買回金額計；第一趟與最後結束的來回照引擎：出場時扣進場金額 × 0.585%）
       ⇒ 共用引擎新開關 held_map（「已持有同一檔」用底層代號判；預設關、逐位元不變；閘 E0～E2）；從沒被觸發的訊號 ⇒ 用原序列、原 xpos／g（逐位元＝營量 v1）
    H ∈ {40, 60, 80}：H60 ＝ AND 表原 xpos／g；H40／H80 ＝ research11.fixed_exit(o, c, k, H, next_bad[max(0,k−20)])＋T1 資料尾（出場根超過資料尾、
       無壞根、該股活到資料末日 ⇒ xpos ＝ ncal、g ＝ 末日收盤 ÷ 進場開盤 − 1）；早年另加 R8 減資截斷（researchYLtrend 同式）；算不出 ⇒ 該列不進（計數）
 X3 乙：第 k 根（進場根算第 1 根）收盤 ＝ 基準 B（固定）；第 k＋1 根起收盤 ＜ B ⇒ 下一根開盤賣；沒跌破抱到第 C 根收盤；
       第 k 根前遇壞根（next_bad）或資料尾 ⇒ 照原 H60 出場；持有中遇壞根 ⇒ 在壞根前一根收盤出（計數）；
       第 C 根超過資料末日 ⇒ xpos ＝ ncal、g ＝ 末日收盤 ÷ P0 − 1（T1 讀法：窗內照市值、不賣、不扣成本；計數必報）
       ⇒ 只改 xpos／g，引擎一字不動
 X4 段：探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24（主窗一條權益）｜早年 2012-06-04～2014-12-31；rerun17.win_metrics
    0050 同段：rerun17.bench_row；使用者判準（seq141）；件標籤 ＝ 確認、早年兩段較嚴
 X5 退化（挑前排除）：探索段平均持股（audit 重建）＜ 10 或現金 ＞ 30%；⚠ 甲件的暫出閒置是規則本身 ⇒ 現金門檻對甲不適用、只報閒置比例
    挑格（各件）：探索段先合格、再比值（年化中位 ÷ |回落中位|；同分年化高）
 X6 主比較（對營量 v1 同段同顆）：日報酬差 200 顆平均 ⇒ 曆月分群 CR0 ⇒ ×245 的 95% CI；
    「比營量好」＝ 確認段 CI 下緣 ＞ 0 且 早年平均差 ＞ 0｜「比營量差」＝ 上緣 ＜ 0 且 早年 ＜ 0｜確認段 CI 不含 0 但早年反向 ⇒「不穩」｜含 0 ⇒「分不出」
 X7 假訊號（K4，挑中格，--reps 次，引擎種子 7000＋i）：甲 ＝ 同一筆持有內，把實際的暫出區間（個數、長度）隨機放到持有窗內（default_rng([20260928, 1, i])）；
    乙 ＝ 基準日 k 改為每筆 [40, 60] 均勻整數（default_rng([20260928, 2, i])）、其餘同；p ＝ 假年化 ≥ 挑中格年化中位 的比例（各段）
 X8 挪起點（K4 ④）：挑中格與營量 v1 在確認段、早年段各自「重新起始」：訊號只收進場 ≥ 段首＋{0, 5, 10, 15, 20} 交易日、權益從該日量到段尾；--shift-seeds 顆
 X9 必報：甲 每筆平均出、進次數、暫出後沒再站回的比例、暫出期間該股漲跌（賣價 → 買回價或結束收盤）、閒置比例（現金＋暫出部位凍結值）÷ 權益；
    乙 平均持有根數、＞ 60 根的比例、觸頂 C 的比例、60 根前就出的比例、資料尾補回筆數；兩件：各年報酬、換手與成本（引擎 audit；甲件暫出再進的成本另計）
    ⚠ 登錄 §四「現實版（滑價 C1～C5）」：甲的合成路徑內暫出再進沒有逐筆滑價模型 ⇒ 本件不做、照寫
 X10 新規矩 ③：挑中格確認或早年「合格／另列」⇒ 出場敏感度（描述）：SL10／SL20（stop fix）、TP30h／TP50h（trim_rule gain，乙件）、檔數 5／10（seq242 ② {5, 10, 20}，20 ＝ 原格）；否則不適用
 閘：E0 held_map fixture｜E1 新引擎（開關關）＝ HEAD 引擎（營量 v1、營飆 v1 各 5 顆：equity 與回傳 dict 逐位元）｜
     E2 開關開＋合成鍵（序列＝原序列）＝ 原引擎（營量 v1 200 顆 eq_sha）｜G1 營量 v1 200 顆 ＝ resultsT1fix c13 t1、營飆 v1 ＝ c1 t1（eq_sha）｜
     G2 早年營量 v1 ＝ resultsYLretest b2_early_seeds「main|開|N20|H60」（年化、回落 repr）｜G3 H60 自算 fixed_exit ＝ AND 表（主、早年）
輸出 backtest/resultsYLexit/（ENGINE_GATE.md ＝ 引擎開關閘）
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11

OUT = "backtest/resultsYLexit"
COST = R11.COST
B_S = (0.0, 0.03, 0.05)
H_S = (40, 60, 80)
K_S = (50, 55, 60)
C_S = (120, 250)
SHIFTS = (0, 5, 10, 15, 20)
SEG_C = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
ORDER = {"不合格": 0, "另列": 1, "合格": 2}
STRAT = {"營量": ("H60", 20, 7000, "relvol"), "營飆": ("H120", 10, 1000, None)}
_W: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def label(c, m, b):
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


# ═════════════ 出場根（H40／H80 與乙） ═════════════
def bars_of(W, s):
    B = W["BARS"].get(s)
    if B is None:
        b = R11.load_bars(s, W["mk"].get(s, "twse"), W["cal"])
        B = None if b is None else (b["idx"], b["o"], b["c"], b["next_bad"], b["df"]["open"].to_numpy(float), b["df"]["close"].to_numpy(float))
        W["BARS"][s] = B
    return B


def exits_H(W, sig, H):
    """H 根固定出場（fixed_exit＋T1＋早年 R8）。回新表（xpos_H{H}, g_H{H}）與計數。"""
    n0 = len(W["cal"]); xs = np.full(len(sig), -1, np.int64); gs = np.full(len(sig), np.nan); cnt = {"fixed": 0, "T1 補": 0, "算不出": 0, "R8 截": 0}
    for i, (s, k) in enumerate(zip(sig["sid"], sig["k"].astype(int))):
        B = bars_of(W, s)
        if B is None:
            cnt["算不出"] += 1; continue
        idx, o, c, nb, of_, cf_ = B; n = len(idx); nbk = nb[max(0, k - 20)]
        r = R11.fixed_exit(o, c, k, H, nbk)
        if r:
            xs[i] = int(idx[r[0]]); gs[i] = r[1]; cnt["fixed"] += 1
        elif D.exit_pos(k + 1, H) >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1:
            xs[i] = n0; gs[i] = float(c[n - 1] / o[k + 1] - 1.0); cnt["T1 補"] += 1
        else:
            cnt["算不出"] += 1; continue
        for pe, pL in W["EVD"].get(s, []):
            ent = int(idx[k + 1])
            if ent <= pL and xs[i] >= pe:
                xs[i] = pL; gs[i] = cf_[pL] / of_[ent] - 1.0; cnt["R8 截"] += 1
    out = sig.copy(); out[f"xpos_H{H}"] = xs; out[f"g_H{H}"] = gs
    return out, cnt


def rule_yi(W, sig, K, C, kfn=None):
    """乙：回（改好 xpos_H60／g_H60 的表, 每筆持有根數, 計數）。kfn(i) ⇒ 該筆 K（假訊號用）。"""
    n0 = len(W["cal"]); S2 = sig.copy()
    X = S2["xpos_H60"].to_numpy(np.int64).copy(); G = S2["g_H60"].to_numpy(float).copy()
    held = np.full(len(S2), np.nan); cnt = {"跌破出": 0, "觸頂C": 0, "資料尾補": 0, "壞根截": 0, "k前原樣": 0, "60根前出": 0, "超過60根": 0}
    for i, (s, k, x0) in enumerate(zip(S2["sid"], S2["k"].astype(int), X)):
        if x0 < 0:
            continue
        B = bars_of(W, s)
        if B is None:
            continue
        idx, o, c, nb, _, _ = B; n = len(idx); nbk = nb[max(0, k - 20)]
        Ki = K if kfn is None else kfn(i)
        ke = k + 1; kk = ke + Ki - 1; kc = ke + C - 1
        ep = o[ke]
        if kk > n - 1 or kk >= nbk:
            cnt["k前原樣"] += 1
            held[i] = (np.searchsorted(idx, min(x0, n0 - 1), side="right") - 1) - ke + 1
            continue
        Bv = c[kk]; last = min(kc, n - 1, nbk - 1); done = False
        for j in range(kk + 1, last + 1):
            if c[j] < Bv:
                if j + 1 <= last:
                    X[i] = int(idx[j + 1]); G[i] = o[j + 1] / ep - 1.0; held[i] = j + 1 - ke + 1
                else:
                    X[i] = int(idx[j]); G[i] = c[j] / ep - 1.0; held[i] = j - ke + 1
                cnt["跌破出"] += 1; done = True; break
        if not done:
            if last == kc:
                X[i] = int(idx[kc]); G[i] = c[kc] / ep - 1.0; held[i] = C; cnt["觸頂C"] += 1
            elif last == nbk - 1 and nbk <= min(kc, n - 1):
                X[i] = int(idx[last]); G[i] = c[last] / ep - 1.0; held[i] = last - ke + 1; cnt["壞根截"] += 1
            elif int(idx[n - 1]) == n0 - 1:
                X[i] = n0; G[i] = c[n - 1] / ep - 1.0; held[i] = n - 1 - ke + 1; cnt["資料尾補"] += 1
            else:
                X[i] = int(idx[n - 1]); G[i] = c[n - 1] / ep - 1.0; held[i] = n - 1 - ke + 1; cnt["資料尾補"] += 1
        cnt["60根前出"] += int(held[i] < 60); cnt["超過60根"] += int(held[i] > 60)
    S2["xpos_H60"] = X; S2["g_H60"] = G
    return S2, held, cnt


# ═════════════ 甲：合成序列 ═════════════
def path_jia(W, s, k, e, x, b, outs=None):
    """一筆的合成收盤序列（引擎 closes 的值）與路徑統計。outs ＝ 指定暫出區間 [(s_bar, r_bar)]（假訊號）；None ⇒ 照規則。
    回 (Sc 或 None（從沒觸發）, g, stats)。"""
    B = bars_of(W, s)
    if B is None:
        return None, None, {"出": 0, "進": 0, "暫出段": [], "終於暫出": False}
    idx, _, _, _, _, _ = B; n = len(idx); NP = W["NP"]
    cl, op = W["closes"][s], W["opens"][s]
    ke = k + 1
    xe = min(x, NP - 2) if x >= len(W["cal"]) else x
    kx = int(np.searchsorted(idx, xe, side="right") - 1)
    P0 = float(op[e])
    plan = {}
    if outs is not None:
        for sb, rb in outs:
            plan[sb] = "sell"
            if rb <= kx:
                plan[rb] = "buy"
    inm = True; ve = 1.0; pe = P0; vf = None; touched = False
    vals = {}; st = {"出": 0, "進": 0, "暫出段": [], "終於暫出": False}
    pend = None; s_open = None
    for j in range(ke, kx + 1):
        t = int(idx[j]); o_t = float(op[t]); c_t = float(cl[t])
        act = plan.get(j) if outs is not None else pend
        if act == "sell" and inm and np.isfinite(o_t) and o_t > 0:
            vf = ve * o_t / pe; inm = False; touched = True; st["出"] += 1; s_open = (o_t, j)
        elif act == "buy" and (not inm) and np.isfinite(o_t) and o_t > 0:
            ve = vf * (1.0 - COST); pe = o_t; inm = True; st["進"] += 1
            st["暫出段"].append((s_open[1], j, o_t / s_open[0] - 1.0)); s_open = None
        pend = None
        vals[t] = (ve * c_t / pe) if inm else vf
        if outs is None and j < kx:
            if inm and c_t < P0 * (1.0 - b):
                pend = "sell"
            elif (not inm) and c_t >= P0:
                pend = "buy"
    if not inm:
        st["終於暫出"] = True
        st["暫出段"].append((s_open[1], kx + 1, float(cl[int(idx[kx])]) / s_open[0] - 1.0))
    if not touched:
        return None, None, st
    Sc = np.array(cl, dtype=float, copy=True)
    lastv = None
    for t in range(e, NP):
        if t in vals:
            lastv = vals[t]
        if lastv is not None:
            Sc[t] = P0 * lastv
    g = Sc[x if x < NP else NP - 1] / P0 - 1.0
    return Sc, g, st


def build_jia(W, strat, H, b, fake_i=None):
    """甲的訊號表（合成鍵）、closes／opens／SF 附加、held_map、路徑統計。"""
    base = W["SIGH"][(strat, H)]
    rows = []; addc = {}; addo = {}; hm = {}; stats = []
    rng = np.random.default_rng([20260928, 1, fake_i]) if fake_i is not None else None
    ref = W.get("JIA_OUTS") if fake_i is not None else None
    for r in base.itertuples(index=False):
        s, k, e, x, g0 = r.sid, int(r.k), int(r.entry_pos), int(getattr(r, f"xpos_H{H}")), float(getattr(r, f"g_H{H}"))
        outs = None
        if fake_i is not None:
            lens = ref.get((s, e), [])
            if lens:
                idx = bars_of(W, s)[0]; ke = k + 1
                xe = min(x, W["NP"] - 2) if x >= len(W["cal"]) else x
                kx = int(np.searchsorted(idx, xe, side="right") - 1)
                span = kx + 1 - (ke + 1); L = list(rng.permutation(lens)); slack = max(span - int(sum(L)), 0)
                cuts = np.sort(rng.choice(slack + len(L), size=len(L), replace=False)) if slack + len(L) > 0 else np.zeros(len(L), int)
                gaps = np.diff(np.r_[-1, cuts]) - 1
                pos = ke + 1; outs = []
                for gp, ln in zip(gaps, L):
                    pos += int(gp); outs.append((pos, pos + int(ln))); pos += int(ln)
            else:
                outs = []
        Sc, g, st = path_jia(W, s, k, e, x, b, outs=outs)
        st.update({"sid": s, "e": e})
        stats.append(st)
        if Sc is None:
            rows.append((s, s, k, e, x, g0, r.relvol))
        else:
            key = f"{s}#{e}"
            addc[key] = Sc; addo[key] = W["opens"][s]; hm[key] = s
            rows.append((key, s, k, e, x, g, r.relvol))
    sig = pd.DataFrame(rows, columns=["sid", "usid", "k", "entry_pos", f"xpos_H{H}", f"g_H{H}", "relvol"])
    for s in set(sig["usid"]):
        hm.setdefault(s, s)
    return sig, addc, addo, hm, stats


# ═════════════ 引擎 ═════════════
def _eng(W, strat, sig, rule, seed, closes=None, opens=None, SF=None, held_map=None, audit=True, N=None, **kw):
    rule_, N0, s0, pick = STRAT[strat]
    aud = [] if audit else None
    extra = dict(log=[], d_max=None, pick="relvol", queue_days=0) if strat == "營量" else {}
    o = R11.simulate_mtm(sig, rule, N or N0, np.random.default_rng(seed), closes or W["closes"], opens or W["opens"], W["NP"], return_equity=True,
                         stop_force=SF or W["SF"], audit=aud, held_map=held_map, **extra, **kw)
    return o, aud


def _stats(W, o, aud, segp, N):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    row = {}
    hold = None
    if aud is not None:
        cnt = np.zeros(len(eq) + 1)
        for a in aud:
            cnt[a["t"]] += 1 if a["side"] == "buy" else -1
        hold = np.cumsum(cnt)[:len(eq)]
    for sg, (x, y) in segp.items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
        if hold is not None:
            row[f"{sg}_持股"] = float(np.mean(hold[x:y + 1]))
            yrs = (y - x + 1) / 245.0; meq = float(np.mean(eq[x:y + 1]))
            row[f"{sg}_買進每年"] = sum(1 for a in aud if a["side"] == "buy" and x <= a["t"] <= y) / yrs
            row[f"{sg}_換手每年"] = sum(a["amt"] for a in aud if a["side"] == "buy" and x <= a["t"] <= y) / meq / yrs
            row[f"{sg}_成本每年"] = sum(a.get("cost", 0.0) for a in aud if a["side"] == "sell" and x <= a["t"] <= y) / meq / yrs
    return row, eq, hold


def cell_inputs(W, cell):
    """cell ＝ ("營量"|"營飆", "base"|"甲"|"乙", 參數 tuple)；每個行程快取。"""
    C_ = W.setdefault("CACHE", {})
    if cell in C_:
        return C_[cell]
    strat, fam, par = cell
    if fam == "base":
        rule = STRAT[strat][0]; v = (W["SIGH"][(strat, int(rule[1:]))], rule, None, None, None, None)
    elif fam == "甲":
        b, H = par
        sig, ac, ao, hm, st = build_jia(W, strat, H, b)
        v = (sig, f"H{H}", {**W["closes"], **ac}, {**W["opens"], **ao}, {**W["SF"], **{k_: W["SF"][s_] for k_, s_ in hm.items() if s_ in W["SF"] and k_ != s_}}, hm)
        W.setdefault("JSTAT", {})[cell] = st
    else:
        K, C = par
        sig, held, cnt = rule_yi(W, W["SIGH"][(strat, 60)], K, C)
        v = (sig, "H60", None, None, None, None)
        W.setdefault("YSTAT", {})[cell] = (held, cnt)
    C_[cell] = v
    return v


def run_cell(job):
    world, cell, r = job
    W = _W[world]
    sig, rule, cl, op, SF, hm = cell_inputs(W, cell)
    strat = cell[0]; N = STRAT[strat][1]
    o, aud = _eng(W, strat, sig, rule, STRAT[strat][2] + r, closes=cl, opens=op, SF=SF, held_map=hm)
    row, eq, hold = _stats(W, o, aud, W["SEGP"], N)
    c, m, _ = RR.win_metrics(eq, o["first"], o["end"], W["w0"], W["w1"])
    row.update({"世界": world, "格": cellname(cell), "r": r, "全窗_年化": float(c), "全窗_回落": float(m), "eq_sha": sha(eq), "強制出場": int(o.get("x_stop_force_n", -1))})
    cal = W["cal"]; yr = pd.DatetimeIndex(cal).year.to_numpy()
    for y_ in sorted(set(yr[W["w0"]:W["w1"] + 1])):
        ii = np.flatnonzero(yr == y_); a_, b_ = max(ii[0], W["w0"]), min(ii[-1], W["w1"]); prev = a_ - 1 if a_ > W["w0"] else a_
        row[f"年{y_}"] = float(eq[b_] / eq[prev] - 1.0)
    if cell[1] == "甲" and hm:                                # 閒置比例 ＝（現金＋暫出部位凍結值）÷ 權益
        outd = W.setdefault("OUTDAYS", {}).get(cell)
        if outd is None:
            outd = {}
            for st in W["JSTAT"][cell]:
                if st["出"] or st["終於暫出"]:
                    idx = bars_of(W, st["sid"])[0]; ks = set()
                    for sb, rb, _ in st["暫出段"]:
                        a0 = int(idx[sb]); b0 = int(idx[rb]) if rb < len(idx) else W["NP"]
                        ks.update(range(a0, b0))
                    outd[f"{st['sid']}#{st['e']}"] = ks
            W["OUTDAYS"][cell] = outd
        hv = np.asarray(o["hold_val"], float); outv = np.zeros(len(eq)); openp = {}
        for a in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
            if a["side"] == "buy":
                openp[a["sid"]] = (a["t"], a["amt"], a["px"])
            else:
                t0_, amt_, ep_ = openp.pop(a["sid"])
                for t in outd.get(a["sid"], ()):
                    if t0_ <= t < a["t"]:
                        outv[t] += amt_ * float(cl[a["sid"]][t]) / ep_
        for sid_, (t0_, amt_, ep_) in openp.items():
            for t in outd.get(sid_, ()):
                if t >= t0_ and t < len(eq):
                    outv[t] += amt_ * float(cl[sid_][t]) / ep_
        for sg, (x, y) in W["SEGP"].items():
            row[f"{sg}_閒置"] = float(np.mean((eq[x:y + 1] - hv[x:y + 1] + outv[x:y + 1]) / eq[x:y + 1]))
    V1 = W.get("V1EQ"); diffs = {}
    if V1 is not None and cell[1] != "base":
        ev = V1[r]
        for sg, (x, y) in W["SEGP"].items():
            diffs[sg] = (eq[x + 1:y + 1] / eq[x:y] - 1.0) - (ev[x + 1:y + 1] / ev[x:y] - 1.0)
    return row, diffs, (eq if W.get("KEEP") == cell else None)


def cellname(cell):
    strat, fam, par = cell
    if fam == "base":
        return f"{strat}v1"
    if fam == "甲":
        return f"{strat}_甲_b{int(round(par[0] * 100))}_H{par[1]}"
    return f"{strat}_乙_k{par[0]}_C{par[1]}"


def run_fake(job):
    world, cell, i = job
    W = _W[world]; strat, fam, par = cell
    if fam == "甲":
        b, H = par
        sig, ac, ao, hm, _ = build_jia(W, strat, H, b, fake_i=i)
        SF = {**W["SF"], **{k_: W["SF"][s_] for k_, s_ in hm.items() if s_ in W["SF"] and k_ != s_}}
        o, aud = _eng(W, strat, sig, f"H{H}", STRAT[strat][2] + i, closes={**W["closes"], **ac}, opens={**W["opens"], **ao}, SF=SF, held_map=hm)
    else:
        K, C = par
        rng = np.random.default_rng([20260928, 2, i]); ks = rng.integers(40, 61, size=len(W["SIGH"][(strat, 60)]))
        sig, _, _ = rule_yi(W, W["SIGH"][(strat, 60)], K, C, kfn=lambda j: int(ks[j]))
        o, aud = _eng(W, strat, sig, "H60", STRAT[strat][2] + i)
    row, _, _ = _stats(W, o, aud, W["SEGP"], STRAT[strat][1])
    row.update({"世界": world, "格": cellname(cell), "i": i})
    return row


def run_shift(job):
    world, cell, sg, sh, r = job
    W = _W[world]
    sig, rule, cl, op, SF, hm = cell_inputs(W, cell)
    x, y = W["SEGP"][sg]; s0 = x + sh
    s2 = sig[sig["entry_pos"].to_numpy() >= s0]
    o, _ = _eng(W, cell[0], s2, rule, STRAT[cell[0]][2] + r, closes=cl, opens=op, SF=SF, held_map=hm, audit=False)
    eq = np.asarray(o["equity"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, y)
    return {"世界": world, "格": cellname(cell), "段": sg, "挪": sh, "r": r, "年化": float(c_), "回落": float(m_)}


def run_sens(job):
    world, cell, name, kw, r = job
    W = _W[world]
    sig, rule, cl, op, SF, hm = cell_inputs(W, cell)
    kw = dict(kw); N = kw.pop("N", None)
    o, aud = _eng(W, cell[0], sig, rule, STRAT[cell[0]][2] + r, closes=cl, opens=op, SF=SF, held_map=hm, N=N, **kw)
    row, _, _ = _stats(W, o, aud, W["SEGP"], N or STRAT[cell[0]][1])
    row.update({"世界": world, "格": cellname(cell), "變體": name, "r": r})
    return row


def cr0(d, months):
    m = float(d.mean()); s = pd.Series(d - m).groupby(months).sum().to_numpy()
    return m, float(np.sqrt((s ** 2).sum()) / len(d))


# ═════════════ 引擎開關閘 ═════════════
def engine_gate(Wm, log):
    res = {}
    # E0 fixture
    n = 40; cal_c = {"A": np.linspace(10, 14, n), "B": np.linspace(20, 18, n)}; cal_o = {k_: v.copy() for k_, v in cal_c.items()}
    sig = pd.DataFrame({"sid": ["A", "B", "A#12"], "entry_pos": [2, 3, 12], "xpos_H5": [20, 25, 30], "g_H5": [cal_c["A"][20] / cal_o["A"][2] - 1, cal_c["B"][25] / cal_o["B"][3] - 1, 0.0]})
    cl2 = dict(cal_c); cl2["A#12"] = cal_c["A"] * 1.0; op2 = dict(cal_o); op2["A#12"] = cal_o["A"]
    sig.loc[2, "g_H5"] = cl2["A#12"][30] / op2["A#12"][12] - 1
    rng = lambda: np.random.default_rng(1)
    o_on = R11.simulate_mtm(sig, "H5", 5, rng(), cl2, op2, n, return_equity=True, held_map={"A": "A", "B": "B", "A#12": "A"})
    o_off = R11.simulate_mtm(sig, "H5", 5, rng(), cl2, op2, n, return_equity=True)
    sig_id = sig.iloc[:2]
    o_id = R11.simulate_mtm(sig_id, "H5", 5, rng(), cal_c, cal_o, n, return_equity=True, held_map={"A": "A", "B": "B"})
    o_df = R11.simulate_mtm(sig_id, "H5", 5, rng(), cal_c, cal_o, n, return_equity=True)
    try:
        R11.simulate_mtm(sig_id, "H5", 5, rng(), cal_c, cal_o, n, return_equity=True, held_map={"A": "A", "B": "B"}, cap_fn=lambda *a_: True); bad_ok = False
    except ValueError:
        bad_ok = True
    res["E0 fixture"] = {"開：A#12 因 A 已持有被擋（trades 2）": int(o_on["trades"]) == 2, "關：A#12 當不同檔進場（trades 3）": int(o_off["trades"]) == 3,
                         "恆等 held_map ＝ 預設（equity 逐位元）": bool(np.array_equal(o_id["equity"], o_df["equity"])),
                         "與 cap_fn 同開 ⇒ ValueError": bad_ok}
    # E1 新引擎（關）＝ HEAD 引擎
    head = subprocess.run(["git", "show", "HEAD:backtest/research11.py"], capture_output=True, text=True).stdout
    hp = os.path.join(OUT, "_research11_head.py"); open(hp, "w", encoding="utf-8").write(head)
    spec = importlib.util.spec_from_file_location("backtest._r11head", hp); Mh = importlib.util.module_from_spec(spec); spec.loader.exec_module(Mh)
    bad = 0; nchk = 0
    for strat in ("營量", "營飆"):
        rule, N, s0, _ = STRAT[strat]; sig = Wm["SIGH"][(strat, int(rule[1:]))]
        extra = dict(log=[], d_max=None, pick="relvol", queue_days=0) if strat == "營量" else {}
        for r in range(5):
            a_ = R11.simulate_mtm(sig, rule, N, np.random.default_rng(s0 + r), Wm["closes"], Wm["opens"], Wm["NP"], return_equity=True, stop_force=Wm["SF"], **extra)
            b_ = Mh.simulate_mtm(sig, rule, N, np.random.default_rng(s0 + r), Wm["closes"], Wm["opens"], Wm["NP"], return_equity=True, stop_force=Wm["SF"], **extra)
            nchk += 1
            same = set(a_) == set(b_) and all((np.array_equal(np.asarray(a_[k_]), np.asarray(b_[k_])) if isinstance(a_[k_], np.ndarray) else repr(a_[k_]) == repr(b_[k_])) for k_ in a_)
            bad += not same
    os.remove(hp)
    import shutil; shutil.rmtree(os.path.join(OUT, "__pycache__"), ignore_errors=True)
    res["E1 開關關 ＝ HEAD 引擎（營量、營飆各 5 顆：equity＋回傳 dict）"] = {"比對": nchk, "不同": bad}
    return res


# ═════════════ 主程式 ═════════════
def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--shift-seeds", type=int, default=200)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log"); open(LOGF, "w").close()
    T0 = time.time()
    log(f"===== researchYLexit {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜seeds {a.seeds} reps {a.reps} shift {a.shift_seeds}｜強制出場：開｜T1：開 =====")
    S = {"件": "PREREG營量出場 seq1（登錄 sha 1a73bbae1829ca85；裁定 seq266 §二；N ＋2）", "閘": {},
         "先驗提醒": "本專案停損類（營飆停損、回測 研究五／六、四類單獨）全部不如抱著"}
    # ── 主世界
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; AND = RR._G["AND"]
    mk = ctx["mk"]
    SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), mk, cal), ctx["w1"])
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in SEG_C.items()}
    Wm = {"cal": cal, "NP": ctx["ncal"], "closes": ctx["closes"], "opens": ctx["opens"], "SF": SF, "mk": mk, "w0": ctx["w0"], "w1": ctx["w1"], "SEGP": SEGP,
          "BARS": {}, "EVD": {}}
    bench = RR.load_bench(cal)
    B50 = {sg: RR.bench_row(cal, bench, x, y + 1) for sg, (x, y) in SEGP.items()}
    Wm["SIGH"] = {("營量", 60): ctx["sig13"], ("營飆", 120): ctx["sig"]}
    for H in (40, 80):
        Wm["SIGH"][("營量", H)], cnt = exits_H(Wm, ctx["sig13"], H); S.setdefault("H40／H80 出場（主）", {})[H] = cnt
        Wm["SIGH"][("營量", H)] = Wm["SIGH"][("營量", H)][Wm["SIGH"][("營量", H)][f"xpos_H{H}"] >= 0]
    chk, _ = exits_H(Wm, ctx["sig13"], 60)
    S["閘"]["G3 主 H60 自算 ＝ AND 表（xpos 不同／g 差＞1e−12）"] = [int((chk["xpos_H60"].to_numpy() != ctx["sig13"]["xpos_H60"].to_numpy()).sum()),
                                                            int(np.nansum(np.abs(chk["g_H60"].to_numpy(float) - ctx["sig13"]["g_H60"].to_numpy(float)) > 1e-12))]
    log(f"[主] 營量 {len(ctx['sig13'])} 列、營飆 {len(ctx['sig'])} 列｜H40／80 {S['H40／H80 出場（主）']}｜G3 {S['閘']['G3 主 H60 自算 ＝ AND 表（xpos 不同／g 差＞1e−12）']}")
    _W["主"] = Wm
    S["閘"]["引擎開關"] = engine_gate(Wm, log)
    log(f"[閘 引擎] {S['閘']['引擎開關']}")
    CELLS = [("營量", "甲", (b, H)) for b in B_S for H in H_S] + [("營量", "乙", (K, C)) for K in K_S for C in C_S]
    YF = [("營飆", "甲", (b, 120)) for b in B_S]
    # 營量 v1 先跑
    Wm["KEEP"] = ("營量", "base", None)
    with Pool(a.procs) as pool:
        res = pool.map(run_cell, [("主", ("營量", "base", None), r) for r in range(a.seeds)], chunksize=4)
    Wm["V1EQ"] = {x[0]["r"]: x[2] for x in res}; Wm["KEEP"] = None
    SEED = [x[0] for x in res]
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str})
    rf = ref[(ref["key"] == "c13") & (ref["var"] == "t1")].set_index("r")["eq_sha"]
    S["閘"]["G1 營量 v1 主 ＝ resultsT1fix c13 t1（eq_sha 不同顆數）"] = int(sum(x["eq_sha"] != rf[x["r"]] for x in SEED))
    # E2：開關開＋合成鍵（原序列）
    base = ctx["sig13"]; keys = [f"{s}#{e}" for s, e in zip(base["sid"], base["entry_pos"])]
    sigE = base.copy(); sigE["sid"] = keys
    hm = dict(zip(keys, base["sid"]))
    clE = {**Wm["closes"], **{k_: Wm["closes"][s] for k_, s in hm.items()}}; opE = {**Wm["opens"], **{k_: Wm["opens"][s] for k_, s in hm.items()}}
    SFE = {**SF, **{k_: SF[s] for k_, s in hm.items() if s in SF}}
    bad = 0
    for r in range(a.seeds):
        o = R11.simulate_mtm(sigE, "H60", 20, np.random.default_rng(7000 + r), clE, opE, Wm["NP"], return_equity=True, log=[], d_max=None, pick="relvol",
                             queue_days=0, stop_force=SFE, held_map=hm)
        bad += sha(o["equity"]) != rf[r]
    S["閘"]["引擎開關"]["E2 開關開＋合成鍵（原序列）＝ 營量 v1（eq_sha 不同顆數）"] = int(bad)
    log(f"[閘] G1 {S['閘']['G1 營量 v1 主 ＝ resultsT1fix c13 t1（eq_sha 不同顆數）']}｜E2 {bad}")
    DIFF = {}
    with Pool(a.procs) as pool:
        for row, diffs, _ in pool.imap_unordered(run_cell, [("主", c, r) for c in CELLS + YF + [("營飆", "base", None)] for r in range(a.seeds)], chunksize=4):
            SEED.append(row)
            if diffs and row["格"].startswith("營量"):
                for sg, d in diffs.items():
                    DIFF.setdefault(row["格"], {})[sg] = d if sg not in DIFF.get(row["格"], {}) else DIFF[row["格"]][sg] + d
    SEEDm = pd.DataFrame(SEED)
    rf1 = ref[(ref["key"] == "c1") & (ref["var"] == "t1")].set_index("r")["eq_sha"]
    y1 = SEEDm[SEEDm["格"] == "營飆v1"]
    S["閘"]["G1 營飆 v1 主 ＝ resultsT1fix c1 t1（eq_sha 不同顆數）"] = int(sum(e_ != rf1[r_] for r_, e_ in zip(y1["r"], y1["eq_sha"])))
    log(f"[主 組合層] {len(SEEDm)} 列｜{time.time() - T0:.0f}s｜閘 {S['閘']}")
    # 路徑統計（主）
    for c in CELLS:
        cell_inputs(Wm, c)
    # ── 早年世界
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    from backtest import early_data as E
    V.body_setup("main", log)
    ecal = V._B["cal"]; ew0, ew1 = V._B["w0"], V._B["w1"]; euni = Y._G["uni"]
    EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(ecal)}
    EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    ecl, eop = Y._G["closes"], Y._G["opens"]
    eSF = R11.stop_force_days(R11.valid_from_data(sorted(ecl), euni, ecal), ew1)
    We = {"cal": ecal, "NP": Y._G["NP"], "closes": ecl, "opens": eop, "SF": eSF, "mk": euni, "w0": ew0, "w1": ew1, "SEGP": {"早年": (ew0, ew1)}, "BARS": {}, "EVD": EVD}
    es13 = Y.sig_of(13, "mtm", ew0, ew1); es1 = Y.sig_of(1, "mtm", ew0, ew1)
    We["SIGH"] = {("營量", 60): es13, ("營飆", 120): es1}
    for H in (40, 80):
        t_, cnt = exits_H(We, es13, H); We["SIGH"][("營量", H)] = t_[t_[f"xpos_H{H}"] >= 0]; S.setdefault("H40／H80 出場（早年）", {})[H] = cnt
    chk, _ = exits_H(We, es13, 60)
    S["閘"]["G3 早年 H60 自算 ＝ AND 表（xpos 不同／g 差＞1e−12）"] = [int((chk["xpos_H60"].to_numpy() != es13["xpos_H60"].to_numpy()).sum()),
                                                              int(np.nansum(np.abs(chk["g_H60"].to_numpy(float) - es13["g_H60"].to_numpy(float)) > 1e-12))]
    eb50 = RR.bench_row(ecal, RR.load_bench(ecal), ew0, ew1 + 1); B50["早年"] = eb50
    _W["早年"] = We
    We["KEEP"] = ("營量", "base", None)
    with Pool(a.procs) as pool:
        res = pool.map(run_cell, [("早年", ("營量", "base", None), r) for r in range(a.seeds)], chunksize=4)
    We["V1EQ"] = {x[0]["r"]: x[2] for x in res}; We["KEEP"] = None
    SEEDE = [x[0] for x in res]
    eref = pd.read_csv("backtest/resultsYLretest/b2_early_seeds.csv", float_precision="round_trip")
    eref = eref[eref["key"] == "main|開|N20|H60"].set_index("r")
    S["閘"]["G2 早年營量 v1 ＝ YLretest main|開|N20|H60（年化／回落 repr 不同顆數）"] = int(sum(repr(float(x["早年_年化"])) != repr(float(eref.at[x["r"], "cagr"]))
                                                                             or repr(float(x["早年_回落"])) != repr(float(eref.at[x["r"], "mdd"])) for x in SEEDE))
    eDIFF = {}
    with Pool(a.procs) as pool:
        for row, diffs, _ in pool.imap_unordered(run_cell, [("早年", c, r) for c in CELLS + YF + [("營飆", "base", None)] for r in range(a.seeds)], chunksize=4):
            SEEDE.append(row)
            if diffs and row["格"].startswith("營量"):
                for sg, d in diffs.items():
                    eDIFF.setdefault(row["格"], {})[sg] = d if sg not in eDIFF.get(row["格"], {}) else eDIFF[row["格"]][sg] + d
    SEEDe = pd.DataFrame(SEEDE)
    for c in CELLS:
        cell_inputs(We, c)
    log(f"[早年 組合層] {len(SEEDe)} 列｜閘 G2 {S['閘']['G2 早年營量 v1 ＝ YLretest main|開|N20|H60（年化／回落 repr 不同顆數）']}｜{time.time() - T0:.0f}s")
    pd.concat([SEEDm, SEEDe]).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # ── 彙總
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in SEGP.items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[ew0 + 1:ew1 + 1]])
    PT = []
    for c in [("營量", "base", None)] + CELLS + [("營飆", "base", None)] + YF:
        k = cellname(c); g = SEEDm[SEEDm["格"] == k]; ge = SEEDe[SEEDe["格"] == k]
        row = {"格": k, "件": c[1] if c[0] == "營量" else "營飆描述"}
        for sg, gg, bb in (("探索", g, B50["探索"]), ("確認", g, B50["確認"]), ("早年", ge, eb50)):
            cc, mm = float(gg[f"{sg}_年化"].median()), float(gg[f"{sg}_回落"].median())
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": label(cc, mm, bb),
                        f"{sg}_持股": float(gg[f"{sg}_持股"].median()), f"{sg}_現金": float(gg[f"{sg}_現金"].median()),
                        f"{sg}_換手每年": float(gg[f"{sg}_換手每年"].median()), f"{sg}_成本每年": float(gg[f"{sg}_成本每年"].median())})
            if f"{sg}_閒置" in gg:
                row[f"{sg}_閒置"] = float(gg[f"{sg}_閒置"].median())
            if c[0] == "營量" and c[1] != "base":
                dd = (DIFF[k][sg] if sg != "早年" else eDIFF[k][sg]) / a.seeds
                m_, se_ = cr0(dd, months[sg])
                row.update({f"{sg}_配對差年化": m_ * 245, f"{sg}_配對差lo": (m_ - 1.96 * se_) * 245, f"{sg}_配對差hi": (m_ + 1.96 * se_) * 245})
        PT.append(row)
    PT = pd.DataFrame(PT)
    for base_k in ("營量v1", "營飆v1"):
        v1 = PT.set_index("格").loc[base_k]
        msk = PT["格"].str.startswith(base_k[:2])
        for sg in ("探索", "確認", "早年"):
            PT.loc[msk, f"{sg}_年化差"] = PT.loc[msk, f"{sg}_年化"] - v1[f"{sg}_年化"]; PT.loc[msk, f"{sg}_回落差"] = PT.loc[msk, f"{sg}_回落"] - v1[f"{sg}_回落"]
    PT["退化"] = PT["件"].isin(["甲", "乙"]) & ((PT["探索_持股"] < 10) | ((PT["件"] == "乙") & (PT["探索_現金"] > 0.30)))
    J = {}
    for fam in ("甲", "乙"):
        cand = PT[(PT["件"] == fam) & ~PT["退化"]]
        if not len(cand):
            J[fam] = {"挑中": None, "件標籤": "依構造不可判定（全部退化）"}; continue
        q = cand[cand["探索_標籤"] == "合格"] if (cand["探索_標籤"] == "合格").any() else cand
        pr = q.sort_values(["探索_比值", "探索_年化"], ascending=[False, False]).iloc[0]
        labs = [pr["確認_標籤"], pr["早年_標籤"]]
        lo, hi, ed = pr["確認_配對差lo"], pr["確認_配對差hi"], pr["早年_配對差年化"]
        if lo > 0:
            vs = "比營量 v1 好" if ed > 0 else "不穩（確認段好、早年反向）"
        elif hi < 0:
            vs = "比營量 v1 差" if ed < 0 else "不穩（確認段差、早年反向）"
        else:
            vs = "分不出（確認段配對差 CI 含 0）"
        J[fam] = {"挑中": pr["格"], "件標籤": min(labs, key=lambda z: ORDER[z]), "對營量v1": vs, **{k_: (float(pr[k_]) if not isinstance(pr[k_], str) else pr[k_]) for k_ in pr.index if k_ not in ("格", "件")}}
    S["判定"] = J; S["0050"] = B50
    S["退化（挑前排除）"] = PT.loc[PT["退化"], "格"].tolist()
    PT.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    np.savez_compressed(os.path.join(OUT, "pairdiff.npz"), **{f"{k}|{sg}": ((DIFF[k][sg] if sg != "早年" else eDIFF[k][sg]) / a.seeds) for k in DIFF for sg in ("探索", "確認", "早年")})
    log(f"[判定] {json.dumps({f: {k_: J[f].get(k_) for k_ in ('挑中', '件標籤', '對營量v1', '確認_年化', '確認_回落', '早年_年化', '確認_配對差年化', '確認_配對差lo', '確認_配對差hi', '早年_配對差年化')} for f in J}, ensure_ascii=False, default=str)}")
    # 路徑必報
    PS = {}
    for wk, W in (("主", Wm), ("早年", We)):
        w0_, w1_ = W["w0"], W["w1"]
        for c in CELLS:
            k = cellname(c)
            if c[1] == "甲":
                st = [x for x in W["JSTAT"][c] if w0_ <= x["e"] <= w1_]
                segs = [d for x in st for d in x["暫出段"]]
                PS[f"{wk}|{k}"] = {"筆": len(st), "每筆平均出": float(np.mean([x["出"] for x in st])), "每筆平均進": float(np.mean([x["進"] for x in st])),
                                   "有暫出的筆比例": float(np.mean([x["出"] > 0 for x in st])),
                                   "暫出後沒再站回（結束時仍在外）比例（有暫出者）": float(np.mean([x["終於暫出"] for x in st if x["出"] > 0])) if any(x["出"] for x in st) else np.nan,
                                   "暫出期間該股平均漲跌": float(np.mean([d[2] for d in segs])) if segs else np.nan, "暫出段數": len(segs)}
            else:
                held, cnt = W["YSTAT"][c]; sig = W["SIGH"][("營量", 60)]
                m_ = (sig["entry_pos"].to_numpy() >= w0_) & (sig["entry_pos"].to_numpy() <= w1_) & np.isfinite(held)
                h = held[m_]
                PS[f"{wk}|{k}"] = {"筆": int(m_.sum()), "平均持有根數": float(np.mean(h)), "＞60 根比例": float(np.mean(h > 60)), "觸頂 C 比例": float(np.mean(h >= c[2][1])),
                                   "60 根前出比例": float(np.mean(h < 60)), "計數（全表）": cnt}
    S["路徑必報"] = PS
    # ── 假訊號、挪起點（挑中格）
    FK = []; SH = []
    for fam in ("甲", "乙"):
        pk = J[fam]["挑中"]
        if pk is None:
            continue
        cell = next(c for c in CELLS if cellname(c) == pk)
        for wk, W in (("主", Wm), ("早年", We)):
            if fam == "甲":
                W["JIA_OUTS"] = {(x["sid"], x["e"]): [d[1] - d[0] for d in x["暫出段"]] for x in W["JSTAT"][cell]}
            with Pool(a.procs) as pool:
                FK += pool.map(run_fake, [(wk, cell, i) for i in range(a.reps)], chunksize=4)
            segs = ["確認"] if wk == "主" else ["早年"]
            with Pool(a.procs) as pool:
                SH += pool.map(run_shift, [(wk, c_, sg, sh, r) for c_ in (cell, ("營量", "base", None)) for sg in segs for sh in SHIFTS for r in range(a.shift_seeds)], chunksize=8)
        log(f"[假訊號／挪起點 {fam}] {time.time() - T0:.0f}s")
    FK = pd.DataFrame(FK); SH = pd.DataFrame(SH)
    FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g"); SH.to_csv(os.path.join(OUT, "shift.csv.gz"), index=False, float_format="%.17g")
    for fam in ("甲", "乙"):
        pk = J[fam]["挑中"]
        if pk is None:
            continue
        f_ = FK[FK["格"] == pk]
        J[fam]["假訊號"] = {sg: {"p（假年化 ≥ 本格年化中位）": float(np.mean(f_[f"{sg}_年化"].dropna() >= J[fam][f"{sg}_年化"])),
                               "假年化中位": float(f_[f"{sg}_年化"].median())} for sg in ("探索", "確認", "早年") if f"{sg}_年化" in f_ and f_[f"{sg}_年化"].notna().any()}
        sh = {}
        for (sg, s_), g in SH[SH["格"].isin([pk, "營量v1"])].groupby(["段", "挪"]):
            a_ = g[g["格"] == pk]; b_ = g[g["格"] == "營量v1"]
            if len(a_) and len(b_):
                sh[f"{sg}+{s_}"] = [float(a_["年化"].median()), float(b_["年化"].median()), float(a_["回落"].median()), float(b_["回落"].median())]
        J[fam]["挪起點（本格年化、營量年化、本格回落、營量回落 中位）"] = sh
    # ── 新規矩 ③
    SENS = []
    for fam in ("甲", "乙"):
        pk = J[fam]["挑中"]
        if pk is None or not any(J[fam][f"{sg}_標籤"] in ("合格", "另列") for sg in ("確認", "早年")):
            J[fam]["新規矩③"] = "不適用"; continue
        cell = next(c for c in CELLS if cellname(c) == pk)
        var = {"SL10": {"stop": ("fix", 0.10)}, "SL20": {"stop": ("fix", 0.20)}, "N5": {"N": 5}, "N10": {"N": 10}}
        if fam == "乙":
            var.update({"TP30h": {"trim_rule": {"kind": "gain", "x": 0.30, "frac": 0.5}}, "TP50h": {"trim_rule": {"kind": "gain", "x": 0.50, "frac": 0.5}}})
        for wk in ("主", "早年"):
            with Pool(a.procs) as pool:
                SENS += pool.map(run_sens, [(wk, cell, vn, kw, r) for vn, kw in var.items() for r in range(a.seeds)], chunksize=8)
        J[fam]["新規矩③"] = "要跑（見 sens）"
    if SENS:
        SD = pd.DataFrame(SENS); SD.to_csv(os.path.join(OUT, "sens_seeds.csv.gz"), index=False, float_format="%.17g")
        S["新規矩③ 出場敏感度（描述；各段 [年化中位, 回落中位]）"] = {f"{k}|{vn}": {sg: [float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())]
                                                                              for sg in ("探索", "確認", "早年") if f"{sg}_年化" in g and g[f"{sg}_年化"].notna().any()}
                                                              for (k, vn), g in SD.groupby(["格", "變體"])}
    S["判定"] = J
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # 引擎閘文件
    eg = S["閘"]["引擎開關"]
    md = ["# 共用引擎：held_map 開關閘門（PREREG營量出場 seq1 甲件）", "", "回測線，2026-09-28（台北）。", "",
          "- `research11.simulate_mtm(..., held_map=None)`：預設關。開時 sig 的 sid 是逐筆合成價格序列的鍵，「已持有同一檔」改用 held_map[sid]（底層代號）判。",
          "- 引擎內改 4 處（`# _HELDMAP`）：出場 held.discard、log 的 c 記錄、候選排除、進場 held.add；另加 1 處互斥檢查（與 nx_pool／trim_proceeds／stop_proceeds／cap_fn／tradable 不同開）。",
          "", "| 閘 | 結果 |", "|---|---|"]
    for k_, v_ in eg.items():
        md.append(f"| {k_} | {v_} |")
    md.append(f"| G1 營量 v1 主 200 顆 ＝ resultsT1fix c13 t1（eq_sha 不同顆數） | {S['閘']['G1 營量 v1 主 ＝ resultsT1fix c13 t1（eq_sha 不同顆數）']} |")
    md.append(f"| G1 營飆 v1 主 200 顆 ＝ resultsT1fix c1 t1（eq_sha 不同顆數） | {S['閘']['G1 營飆 v1 主 ＝ resultsT1fix c1 t1（eq_sha 不同顆數）']} |")
    open(os.path.join(OUT, "ENGINE_GATE.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
