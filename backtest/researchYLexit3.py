# -*- coding: utf-8 -*-
"""PREREG營量出場 seq3（台股策略線 登錄 sha ee4bab026f160ddf；裁定 seq269：取代 seq1、seq2，沿用 PREREG營量出場 編號、N ＋2 不變）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit3 [--procs 2] [--seeds 5] [--yf-seeds 200] [--reps 200]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchYLexit3_check.py

⚠ 交件必寫（裁定 seq269 §1）：改寫（seq2 14:33、seq3 14:34）當下，seq1 已產出並回報（resultsYLexit，13:5x 回報協調者）、
   seq1 的例子網頁已交使用者看過（14:1x）⇒ 「seq1 數字早於改寫」；seq1 兩件（researchYLexit）只當描述臂、⛔ 不作判定。
⭐ 先驗提醒（裁定 seq266 §二）：本專案停損類（營飆停損、回測 研究五／六、四類單獨）全部不如抱著。⛔ 合格也不取代營量 v1，只進前瞻紀錄並列。

═══ 本體（同 seq1，⛔ 不改）═══
  營量 v1 ＝ researchT1fix #13（T1、H60 N20 relvol、stop_force）；早年 ＝ researchV 早年版面 2012-06-04～2014-12-31；營飆 v1（甲件描述）＝ #1（H120 N10 抽籤）
  共用引擎 research11.simulate_mtm＋held_map 開關（f179b17e04 已 commit、閘見 resultsYLexit/ENGINE_GATE.md）；出場根 H40／H80、合成序列同 researchYLexit
═══ 甲件 seq3（§六之一＋§七；⭐ 本線讀法 Z1～Z8 看任何本件數字前寫死）═══
 Z1 出：持有中收盤 ＜ P0×(1−b) ⇒ 下一根有效 K 棒開盤賣（同 seq1）；「觸發出場那天」＝ 收盤跌破那一根（警訊期間從這根起算，含）
 Z2 暫出中每根收盤依序判：① 任一啟用警訊成立 ⇒ 放棄（⛔ 不再買回；「名額次一交易日釋出」＝ 該股下一根有效 K 棒那天，引擎在那天以凍結值出場、同日可進新訊號）
       ⚠ 跌破當根就有警訊 ⇒ 下一根開盤賣出即放棄（賣出日 ＝ 釋出日）
    ② 收盤 ≥ P0 ⇒ 下一根開盤買回　③ 該根是該股一筆新的營量 v1 訊號根（AND 表任一列的 k；營飆描述用營飆表）⇒ 下一根開盤買回
       ⚠ 讀法：②③ 是「在同一個名額內買回」，P0 與第 H 根結束日都照原筆（⛔ 不重算）；同根 ① 與 ②③ 同時成立 ⇒ ① 優先（登錄「有警訊 ⇒ 放棄；沒警訊 ⇒ 再進」）
    ④ §七 等待上限 L＝10：自賣出那根算第 1 根，第 L 根收盤仍 ＜ P0 且沒有 ②③ ⇒ 放棄（同 ① 釋出）；L＝5、20 只描述
    第 H 根（進場根算第 1 根）收盤不論在場與否結束；第 H 根收盤觸發的動作不執行
 Z2b ⭐ 使用者 09-28 追加（逐字）：「買回次數最多一次，超過換下檔」（使用者 09-28 追加，台股將改寫登錄）⇒ 判定格：同一筆最多買回 1 次；
     買回後再觸發暫出（收盤 ＜ P0×(1−b)）⇒ 不再等站回：下一根開盤賣出並放棄（同警訊／等滿 L 的釋出）；原因記「買回上限」
     不設上限（seq3 原文）⇒ 只當描述臂（挑中 b、H）；必報：挑中格每筆買回次數分佈（有上限 vs 沒上限）
 Z3 警訊（有效 K 棒空間、還原價、原始成交股數；vm ＝ 前 20 根均量、不含當根，researchExtAuth.vma 同式）：
    W1 下跌放量：c/c[−1] − 1 ≤ −3% 且 v ≥ vm×2
    W2 高檔爆量長黑（外部作者 Y2 長黑日定義，只當警訊）：c ≥ max(h 前 60 根)×0.95、v ≥ vm×2、(c−o)/o ≤ −4%
    W3 帶量跌破 MA50：c[−1] ≥ MA50[−1]、c ＜ MA50（含當根 50 根均）、v ≥ vm×1.5
    W4 基本面背離：該根是一筆新月營收的可用根（營量面板 panel_rev 的 signal_pos 之後第一根有效 K 棒）且 yoy ＜ 0
 Z4 「放棄後同一檔」：新的營量訊號照一般新進場（引擎本來就會：釋出後 held 清掉）
 Z5 成本：每趟「賣出＋買回」扣一趟來回 0.585%（以買回金額計，併入合成序列）；最後一趟由引擎出場時扣（同 seq1）
 Z6 格：b {0, 3, 5%} × H {40, 60, 80} ＝ 9；描述臂（挑中格、不判、不計 N）：W1～W4 各自單獨、L＝5、L＝20；seq1 原版 ＝ resultsYLexit 同 b、H
 Z7 假訊號（200 次）：警訊改成「每段暫出以相同機率 q 隨機放棄」（q ＝ 挑中格該世界實際被警訊放棄的暫出段比例；放棄根 ＝ 跌破根起 [0, L] 根內均勻），其餘（站回、新訊號、L＝10）照舊；
    rng default_rng([20260928, 31, i])；p ＝ 假年化 ≥ 本格年化 的比例
 Z8 必報：暫出後觸發警訊比例（各 W，含同根多個）、放棄原因拆分（警訊／等滿 L）、最後站回比例、閒置比例（同 seq1）、
    放棄後同一天換進的新部位淨報酬（引擎 audit、種子 0）vs 被放棄那檔從釋出日開盤抱到第 H 根收盤（扣一趟成本）、等滿 L 被放棄那批同法
═══ 乙件 seq3（§六之二）═══
 Y1 第 k 根收盤 ＝ 初始基準 B；確認根 ＝ k、k＋c、k＋2c…；第 k＋1 根起任一根收盤 ＜ B ⇒ 下一根開盤賣；確認根收盤 ≥ B ⇒ B ＝ 該收盤（只上不下）
    第 C 根收盤上限；第 k 根前有壞根或資料尾 ⇒ 照原 H60；持有中遇壞根 ⇒ 壞根前一根收盤出；第 C 根超過資料末日 ⇒ T1 讀法（窗內照市值），筆數必報（同 seq1 X3）
 Y2 格：k {50, 55, 60} × c {5, 10, 20} × C {120, 250} ＝ 18；描述臂：seq1 原版（基準固定）＝ resultsYLexit
 Y3 假訊號（200 次）：每筆 k 改為 [40, 60] 均勻整數（rng [20260928, 32, i]），c、C 同挑中格
 Y4 必報：平均持有根數、＞60 根比例、觸頂 C 比例、平均上調次數、出場價相對持有期最高收盤的回吐
═══ 兩件共同 ═══
 段：探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24｜早年 2012-06-04～2014-12-31；退化 ＝ 探索段平均持股 ＜ 10（乙另加現金 ＞ 30%；甲現金門檻不適用）
 挑格 ＝ 探索段先合格、再比值；件標籤 ＝ 確認、早年較嚴；對營量 v1 同段同顆配對（日報酬差、曆月 CR0、95% CI ×245）；
 「比營量好」＝ 確認段 CI 下緣 ＞ 0 且早年同向；只一段 ⇒「不穩」；含 0 ⇒「分不出」
 種子：營量依 relvol 排序、不抽籤 ⇒ 各格跑 --seeds 顆（預設 5）並驗「各顆逐位元相同」（seq1 已驗 200 顆 eq_sha 只有 1 種）；營飆描述 --yf-seeds 顆（抽籤）
 挪起點（K4 ④）：挑中格與營量 v1 在確認、早年段 +{0, 5, 10, 15, 20} 交易日重新起算（1 顆）
 新規矩 ③：挑中格確認或早年合格／另列 ⇒ SL10／SL20／檔數 5、10（乙另加 TP30h／TP50h）描述
輸出 backtest/resultsYLexit3/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from backtest import researchYLexit as YX

OUT = "backtest/resultsYLexit3"
COST = R11.COST
B_S = (0.0, 0.03, 0.05); H_S = (40, 60, 80)
K_S = (50, 55, 60); CC_S = (5, 10, 20); C_S = (120, 250)
SHIFTS = (0, 5, 10, 15, 20)
WS = ("W1", "W2", "W3", "W4")
ORDER = {"不合格": 0, "另列": 1, "合格": 2}
_W: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def vma(v, n=20):
    v = np.asarray(v, float); nb = len(v)
    fin = np.isfinite(v); vv = np.where(fin, v, 0.0)
    cs = np.r_[0.0, np.cumsum(vv)]; cf = np.r_[0, np.cumsum(fin)]
    out = np.full(nb, np.nan)
    if nb > n:
        i = np.arange(n, nb); s = cs[i] - cs[i - n]; k = cf[i] - cf[i - n]
        out[n:] = np.where(k == n, s / n, np.nan)
    return out


def rmax(x, n):
    x = np.asarray(x, float); nb = len(x); out = np.full(nb, np.nan)
    if nb > n:
        out[n:] = np.lib.stride_tricks.sliding_window_view(x, n)[:nb - n].max(axis=1)
    return out


def warns(W, s):
    """該股有效 K 棒上的 W1～W4 布林陣列（快取）。"""
    C_ = W.setdefault("WARN", {})
    if s in C_:
        return C_[s]
    B = YX.bars_of(W, s)
    if B is None:
        C_[s] = None; return None
    idx = B[0]; b = R11.load_bars(s, W["mk"].get(s, "twse"), W["cal"])
    o, h, l, c = b["o"], b["h"], b["l"], b["c"]; v = b["df"]["volume"].to_numpy(float)[idx]
    vm = vma(v, 20); hh60 = rmax(h, 60)
    ma50 = pd.Series(c).rolling(50, min_periods=50).mean().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        r1 = np.r_[np.nan, c[1:] / c[:-1] - 1.0]
        w1 = (r1 <= -0.03) & np.isfinite(vm) & (v >= vm * 2)
        w2 = np.isfinite(hh60) & (c >= hh60 * 0.95) & np.isfinite(vm) & (v >= vm * 2) & ((c - o) / o <= -0.04)
        prev_ok = np.r_[False, np.isfinite(ma50[:-1]) & (c[:-1] >= ma50[:-1])]
        w3 = prev_ok & np.isfinite(ma50) & (c < ma50) & np.isfinite(vm) & (v >= vm * 1.5)
    w4 = np.zeros(len(idx), bool)
    ev = W["REV"].get(s)
    if ev is not None:
        for sp_, y_ in zip(*ev):
            j = int(np.searchsorted(idx, sp_, side="right"))       # signal_pos 之後第一根有效 K 棒
            if j < len(idx) and np.isfinite(y_) and y_ < 0:
                w4[j] = True
    C_[s] = {"W1": w1, "W2": w2, "W3": w3, "W4": w4}
    return C_[s]


# ═════════════ 甲 seq3：逐筆路徑 ═════════════
def path3(W, s, k, e, x, b, act=WS, L=10, newk=None, rnd=None, M=1):
    """回 (Sc 或 None, xpos, g, st)。rnd ＝ (rng, q) ⇒ 警訊改成隨機放棄（假訊號）。"""
    B = YX.bars_of(W, s)
    st = {"出": 0, "進站回": 0, "進新訊號": 0, "暫出中出現新訊號根": 0, "放棄": None, "警訊": [], "段": [], "終於暫出": False, "釋出t": None}
    if B is None or x < 0:
        return None, x, None, st
    idx = B[0]; NP = W["NP"]; n0 = len(W["cal"])
    cl, op = W["closes"][s], W["opens"][s]
    ke = k + 1
    kx = int(np.searchsorted(idx, (NP - 2) if x >= n0 else x, side="right") - 1)
    P0 = float(op[e]); WA = warns(W, s) if rnd is None else None
    nk = newk.get(s, set()) if newk is not None else set()
    inm = True; ve = 1.0; pe = P0; vf = None; touched = False; vals = {}
    pend = None; s_bar = None; s_open = None; j0 = None; rab = None; xrel = None
    for j in range(ke, kx + 1):
        t = int(idx[j]); o_t = float(op[t]); c_t = float(cl[t])
        if pend == "sell" and inm and np.isfinite(o_t) and o_t > 0:
            vf = ve * o_t / pe; inm = False; touched = True; st["出"] += 1; s_bar = j; s_open = o_t
        elif pend in ("buy_up", "buy_new") and (not inm) and np.isfinite(o_t) and o_t > 0:
            ve = vf * (1.0 - COST); pe = o_t; inm = True; st["進站回" if pend == "buy_up" else "進新訊號"] += 1
            st["段"].append((s_bar, j, o_t / s_open - 1.0))
        elif pend == "abandon":
            if inm and np.isfinite(o_t) and o_t > 0:                      # 跌破當根就有警訊：賣出即放棄
                vf = ve * o_t / pe; inm = False; touched = True; st["出"] += 1; s_bar = j; s_open = o_t
            vals[t] = vf; xrel = t; st["釋出t"] = t
            st["段"].append((s_bar, j, float(op[t]) / s_open - 1.0 if np.isfinite(op[t]) and op[t] > 0 else np.nan))
            break
        pend = None
        vals[t] = (ve * c_t / pe) if inm else vf
        if j >= kx:
            break
        if inm:
            if c_t < P0 * (1.0 - b):
                pend = "sell"; j0 = j
                if M is not None and st["進站回"] + st["進新訊號"] >= M:
                    pend = "abandon"; st["放棄"] = "買回上限"; continue
                if rnd is not None:
                    rng, q = rnd
                    rab = j + int(rng.integers(0, L + 1)) if rng.random() < q else None
                hit = [w for w in act if WA is not None and WA[w][j]] if rnd is None else ([] if rab != j else ["隨機"])
                if hit:
                    pend = "abandon"; st["放棄"] = "警訊"; st["警訊"] = hit
        else:
            st["暫出中出現新訊號根"] += int(j in nk)
            hit = [w for w in act if WA[w][j]] if rnd is None else (["隨機"] if rab == j else [])
            if hit:
                pend = "abandon"; st["放棄"] = "警訊"; st["警訊"] = hit
            elif c_t >= P0:
                pend = "buy_up"
            elif j in nk:
                pend = "buy_new"
            elif j - s_bar + 1 >= L:
                pend = "abandon"; st["放棄"] = f"等滿{L}"
    if not touched:
        return None, x, None, st
    if xrel is None and not inm:
        st["終於暫出"] = True
        st["段"].append((s_bar, kx + 1, float(cl[int(idx[kx])]) / s_open - 1.0))
    Sc = np.array(cl, dtype=float, copy=True); lastv = None
    for t in range(e, NP):
        if t in vals:
            lastv = vals[t]
        if lastv is not None:
            Sc[t] = P0 * lastv
    xp = xrel if xrel is not None else x
    g = Sc[xp if xp < NP else NP - 1] / P0 - 1.0
    return Sc, xp, g, st


def build3(W, strat, H, b, act=WS, L=10, rnd_i=None, q=0.0, M=1):
    base = W["SIGH"][(strat, H)]
    rows = []; ac = {}; ao = {}; hm = {}; stats = []
    rng = np.random.default_rng([20260928, 31, rnd_i]) if rnd_i is not None else None
    for r in base.itertuples(index=False):
        s, k, e, x, g0 = r.sid, int(r.k), int(r.entry_pos), int(getattr(r, f"xpos_H{H}")), float(getattr(r, f"g_H{H}"))
        Sc, xp, g, st = path3(W, s, k, e, x, b, act=act, L=L, newk=W["NEWK"][strat], rnd=(rng, q) if rng is not None else None, M=M)
        st.update({"sid": s, "e": e, "x": x}); stats.append(st)
        if Sc is None:
            rows.append((s, s, k, e, x, g0, r.relvol))
        else:
            key = f"{s}#{e}"; ac[key] = Sc; ao[key] = W["opens"][s]; hm[key] = s
            rows.append((key, s, k, e, xp, g, r.relvol))
    sig = pd.DataFrame(rows, columns=["sid", "usid", "k", "entry_pos", f"xpos_H{H}", f"g_H{H}", "relvol"])
    for s in set(sig["usid"]):
        hm.setdefault(s, s)
    SF = {**W["SF"], **{k_: W["SF"][u] for k_, u in hm.items() if u in W["SF"] and k_ != u}}
    return sig, {**W["closes"], **ac}, {**W["opens"], **ao}, SF, hm, stats


# ═════════════ 乙 seq3 ═════════════
def rule_yi3(W, sig, K, cstep, C, kfn=None):
    n0 = len(W["cal"]); S2 = sig.copy()
    X = S2["xpos_H60"].to_numpy(np.int64).copy(); G = S2["g_H60"].to_numpy(float).copy()
    held = np.full(len(S2), np.nan); ups = np.full(len(S2), np.nan); gb = np.full(len(S2), np.nan)
    cnt = {"跌破出": 0, "觸頂C": 0, "資料尾補": 0, "壞根截": 0, "k前原樣": 0}
    for i, (s, k, x0) in enumerate(zip(S2["sid"], S2["k"].astype(int), X)):
        if x0 < 0:
            continue
        B = YX.bars_of(W, s)
        if B is None:
            continue
        idx, o, c, nb, _, _ = B; n = len(idx); nbk = nb[max(0, k - 20)]
        Ki = K if kfn is None else kfn(i)
        ke = k + 1; kk = ke + Ki - 1; kc = ke + C - 1; ep = o[ke]
        if kk > n - 1 or kk >= nbk:
            cnt["k前原樣"] += 1
            xb = int(np.searchsorted(idx, min(x0, n0 - 1), side="right") - 1)
            held[i] = xb - ke + 1; ups[i] = 0; gb[i] = c[xb] / np.max(c[ke:xb + 1]) - 1.0; continue
        Bv = c[kk]; nu = 0; last = min(kc, n - 1, nbk - 1); xb = None; px = None
        for j in range(kk + 1, last + 1):
            if c[j] < Bv:
                if j + 1 <= last:
                    xb, px = j + 1, o[j + 1]
                else:
                    xb, px = j, c[j]
                cnt["跌破出"] += 1; break
            if (j - kk) % cstep == 0 and c[j] >= Bv:
                if c[j] > Bv:
                    nu += 1
                Bv = c[j]
        if xb is None:
            if last == kc:
                xb, px = kc, c[kc]; cnt["觸頂C"] += 1
            elif last == nbk - 1 and nbk <= min(kc, n - 1):
                xb, px = last, c[last]; cnt["壞根截"] += 1
            else:
                xb, px = n - 1, c[n - 1]; cnt["資料尾補"] += 1
                X[i] = n0 if int(idx[n - 1]) == n0 - 1 else int(idx[n - 1]); G[i] = px / ep - 1.0
                held[i] = xb - ke + 1; ups[i] = nu; gb[i] = px / np.max(c[ke:xb + 1]) - 1.0; continue
        X[i] = int(idx[xb]); G[i] = px / ep - 1.0
        held[i] = xb - ke + 1; ups[i] = nu; gb[i] = px / np.max(c[ke:xb + 1]) - 1.0
    S2["xpos_H60"] = X; S2["g_H60"] = G
    return S2, {"held": held, "ups": ups, "giveback": gb}, cnt


# ═════════════ 格 ═════════════
def cname(cell):
    strat, fam, par = cell
    if fam == "base":
        return f"{strat}v1"
    if fam == "甲":
        b, H, act, L, M = par
        tail = ("_只" + "".join(act) if tuple(act) != WS else "") + (f"_L{L}" if L != 10 else "") + ("_不限買回" if M is None else "")
        return f"{strat}_甲3_b{int(round(b * 100))}_H{H}{tail}"
    k, cs, C = par
    return f"{strat}_乙3_k{k}_c{cs}_C{C}"


def inputs(W, cell):
    Cc = W.setdefault("CACHE", {})
    if cell in Cc:
        return Cc[cell]
    strat, fam, par = cell
    if fam == "base":
        rule = YX.STRAT[strat][0]; v = (W["SIGH"][(strat, int(rule[1:]))], rule, None, None, None, None)
    elif fam == "甲":
        b, H, act, L, M = par
        sig, cl, op, SF, hm, st = build3(W, strat, H, b, act=act, L=L, M=M)
        v = (sig, f"H{H}", cl, op, SF, hm); W.setdefault("JST", {})[cell] = st
    else:
        k, cs, C = par
        sig, info, cnt = rule_yi3(W, W["SIGH"][(strat, 60)], k, cs, C)
        v = (sig, "H60", None, None, None, None); W.setdefault("YST", {})[cell] = (info, cnt)
    Cc[cell] = v
    return v


def run_cell(job):
    world, cell, r = job
    W = _W[world]
    sig, rule, cl, op, SF, hm = inputs(W, cell)
    strat = cell[0]
    o, aud = YX._eng(W, strat, sig, rule, YX.STRAT[strat][2] + r, closes=cl, opens=op, SF=SF, held_map=hm)
    row, eq, _ = YX._stats(W, o, aud, W["SEGP"], YX.STRAT[strat][1])
    row.update({"世界": world, "格": cname(cell), "r": r, "eq_sha": YX.sha(eq)})
    cal = W["cal"]; yr = pd.DatetimeIndex(cal).year.to_numpy()
    for y_ in sorted(set(yr[W["w0"]:W["w1"] + 1])):
        ii = np.flatnonzero(yr == y_); a_, b_ = max(ii[0], W["w0"]), min(ii[-1], W["w1"]); prev = a_ - 1 if a_ > W["w0"] else a_
        row[f"年{y_}"] = float(eq[b_] / eq[prev] - 1.0)
    if cell[1] == "甲":
        hv = np.asarray(o["hold_val"], float); outv = np.zeros(len(eq))
        outd = W.setdefault("OUTD", {}).get(cell)
        if outd is None:
            outd = {}
            for st in W["JST"][cell]:
                if st["出"]:
                    idx = YX.bars_of(W, st["sid"])[0]; ks = set()
                    for sb, rb, _ in st["段"]:
                        a0 = int(idx[sb]); b0 = int(idx[rb]) if rb < len(idx) else W["NP"]
                        ks.update(range(a0, b0))
                    outd[f"{st['sid']}#{st['e']}"] = ks
            W["OUTD"][cell] = outd
        openp = {}
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
                if t0_ <= t < len(eq):
                    outv[t] += amt_ * float(cl[sid_][t]) / ep_
        for sg, (x, y) in W["SEGP"].items():
            row[f"{sg}_閒置"] = float(np.mean((eq[x:y + 1] - hv[x:y + 1] + outv[x:y + 1]) / eq[x:y + 1]))
    diffs = {}
    V1 = W.get("V1EQ")
    if V1 is not None and cell[1] != "base" and strat == "營量":
        for sg, (x, y) in W["SEGP"].items():
            diffs[sg] = (eq[x + 1:y + 1] / eq[x:y] - 1.0) - (V1[x + 1:y + 1] / V1[x:y] - 1.0)
    keep = (eq, aud) if W.get("KEEP") == cell else None
    return row, diffs, keep


def run_fake(job):
    world, cell, i = job
    W = _W[world]; strat, fam, par = cell
    if fam == "甲":
        b, H, act, L, M = par
        sig, cl, op, SF, hm, _ = build3(W, strat, H, b, act=act, L=L, rnd_i=i, q=W["Q"], M=M)
        o, aud = YX._eng(W, strat, sig, f"H{H}", YX.STRAT[strat][2] + i, closes=cl, opens=op, SF=SF, held_map=hm)
    else:
        k, cs, C = par
        rng = np.random.default_rng([20260928, 32, i]); ks = rng.integers(40, 61, size=len(W["SIGH"][(strat, 60)]))
        sig, _, _ = rule_yi3(W, W["SIGH"][(strat, 60)], k, cs, C, kfn=lambda j: int(ks[j]))
        o, aud = YX._eng(W, strat, sig, "H60", YX.STRAT[strat][2] + i)
    row, _, _ = YX._stats(W, o, aud, W["SEGP"], YX.STRAT[strat][1])
    row.update({"世界": world, "格": cname(cell), "i": i})
    return row


def run_shift(job):
    world, cell, sg, sh = job
    W = _W[world]
    sig, rule, cl, op, SF, hm = inputs(W, cell)
    x, y = W["SEGP"][sg]; s0 = x + sh
    o, _ = YX._eng(W, cell[0], sig[sig["entry_pos"].to_numpy() >= s0], rule, YX.STRAT[cell[0]][2], closes=cl, opens=op, SF=SF, held_map=hm, audit=False)
    eq = np.asarray(o["equity"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, y)
    return {"世界": world, "格": cname(cell), "段": sg, "挪": sh, "年化": float(c_), "回落": float(m_)}


def run_sens(job):
    world, cell, name, kw = job
    W = _W[world]
    sig, rule, cl, op, SF, hm = inputs(W, cell)
    kw = dict(kw); N = kw.pop("N", None)
    o, aud = YX._eng(W, cell[0], sig, rule, YX.STRAT[cell[0]][2], closes=cl, opens=op, SF=SF, held_map=hm, N=N, **kw)
    row, _, _ = YX._stats(W, o, aud, W["SEGP"], N or YX.STRAT[cell[0]][1])
    row.update({"世界": world, "格": cname(cell), "變體": name})
    return row


def rev_events(path):
    rv = pd.read_csv(path, dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "yoy"])
    return {s: (g["signal_pos"].to_numpy(int), g["yoy"].to_numpy(float)) for s, g in rv.groupby("stock_id")}


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=5); ap.add_argument("--yf-seeds", type=int, default=200)
    ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log"); open(LOGF, "w").close()
    T0 = time.time()
    log(f"===== researchYLexit3 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜seeds {a.seeds} yf {a.yf_seeds} reps {a.reps}｜強制出場：開｜T1：開 =====")
    S = {"件": "PREREG營量出場 seq3（登錄 sha ee4bab026f160ddf；裁定 seq269：沿用編號、N ＋2）", "閘": {},
         "seq1 聲明": "seq1 數字早於改寫：改寫（seq2 14:33、seq3 14:34）當下 seq1 已產出並回報（resultsYLexit），且 seq1 例子網頁已給使用者看過 ⇒ seq1 兩件只當描述臂、⛔ 不作判定",
         "先驗提醒": "本專案停損類（營飆停損、回測 研究五／六、四類單獨）全部不如抱著"}
    JIA = [("營量", "甲", (b, H, WS, 10, 1)) for b in B_S for H in H_S]
    YI = [("營量", "乙", (k, cs, C)) for k in K_S for cs in CC_S for C in C_S]
    YF = [("營飆", "甲", (b, 120, WS, 10, 1)) for b in B_S]
    BASEc = ("營量", "base", None); YFB = ("營飆", "base", None)
    # ── 世界
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; mk = ctx["mk"]; AND = RR._G["AND"]
    SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), mk, cal), ctx["w1"])
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in YX.SEG_C.items()}
    Wm = {"cal": cal, "NP": ctx["ncal"], "closes": ctx["closes"], "opens": ctx["opens"], "SF": SF, "mk": mk, "w0": ctx["w0"], "w1": ctx["w1"], "SEGP": SEGP,
          "BARS": {}, "EVD": {}, "REV": rev_events(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"))}
    Wm["SIGH"] = {("營量", 60): ctx["sig13"], ("營飆", 120): ctx["sig"]}
    for H in (40, 80):
        t_, _ = YX.exits_H(Wm, ctx["sig13"], H); Wm["SIGH"][("營量", H)] = t_[t_[f"xpos_H{H}"] >= 0]
    Wm["NEWK"] = {"營量": {s: set(g["k"].astype(int)) for s, g in AND.groupby("sid")}, "營飆": {s: set(g["k"].astype(int)) for s, g in ctx["sig"].groupby("sid")}}
    bench = RR.load_bench(cal)
    B50 = {sg: RR.bench_row(cal, bench, x, y + 1) for sg, (x, y) in SEGP.items()}
    _W["主"] = Wm
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    from backtest import early_data as E
    # 早年世界（先建、fork 前）
    V.body_setup("main", log)
    ecal = V._B["cal"]; ew0, ew1 = V._B["w0"], V._B["w1"]; euni = Y._G["uni"]
    EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(ecal)}; EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    ecl, eop = Y._G["closes"], Y._G["opens"]
    eSF = R11.stop_force_days(R11.valid_from_data(sorted(ecl), euni, ecal), ew1)
    We = {"cal": ecal, "NP": Y._G["NP"], "closes": ecl, "opens": eop, "SF": eSF, "mk": euni, "w0": ew0, "w1": ew1, "SEGP": {"早年": (ew0, ew1)}, "BARS": {}, "EVD": EVD,
          "REV": rev_events(os.path.join(V.body_paths("main")[1], "panel_rev.csv.gz"))}
    EALL = Y.sig_of(13, "mtm", 0, len(ecal) + 5); YALL = Y.sig_of(1, "mtm", 0, len(ecal) + 5)
    es13 = Y.sig_of(13, "mtm", ew0, ew1); es1 = Y.sig_of(1, "mtm", ew0, ew1)
    We["SIGH"] = {("營量", 60): es13, ("營飆", 120): es1}
    for H in (40, 80):
        t_, _ = YX.exits_H(We, es13, H); We["SIGH"][("營量", H)] = t_[t_[f"xpos_H{H}"] >= 0]
    We["NEWK"] = {"營量": {s: set(g["k"].astype(int)) for s, g in EALL.groupby("sid")}, "營飆": {s: set(g["k"].astype(int)) for s, g in YALL.groupby("sid")}}
    B50["早年"] = RR.bench_row(ecal, RR.load_bench(ecal), ew0, ew1 + 1)
    _W["早年"] = We
    # 注意：bars_of 依 D.DATA 讀檔 ⇒ 每個世界的 bars 在切換版面時先預載
    RR.use_snapshot()
    for s in sorted(set(ctx["sig13"]["sid"]) | set(ctx["sig"]["sid"])):
        YX.bars_of(Wm, s); warns(Wm, s)
    D.DATA = V.body_paths("main")[0]
    for s in sorted(set(es13["sid"]) | set(es1["sid"])):
        YX.bars_of(We, s); warns(We, s)
    RR.use_snapshot()
    log(f"[世界] 主 營量 {len(ctx['sig13'])}、營飆 {len(ctx['sig'])}｜早年 營量 {len(es13)}、營飆 {len(es1)}｜{time.time() - T0:.0f}s")
    # 早年閘（researchV 設定下的 D.DATA）：bars 已預載，引擎只用記憶體陣列
    ALLROWS = []; DIFF = {}; KEEP = {}
    for wk, W in (("主", Wm), ("早年", We)):
        W["KEEP"] = BASEc
        with Pool(a.procs) as pool:
            res = pool.map(run_cell, [(wk, BASEc, r) for r in range(a.seeds)])
        W["V1EQ"] = res[0][2][0]; W["KEEP"] = None
        ALLROWS += [x[0] for x in res]
        cells = JIA + YI
        W["KEEP"] = None
        with Pool(a.procs) as pool:
            for row, diffs, _ in pool.imap_unordered(run_cell, [(wk, c, r) for c in cells for r in range(a.seeds)] + [(wk, c, r) for c in YF + [YFB] for r in range(a.yf_seeds)], chunksize=2):
                ALLROWS.append(row)
                if diffs and row["r"] == 0:
                    for sg, d in diffs.items():
                        DIFF[(wk, row["格"], sg)] = d
        log(f"[{wk}] 格完成｜{time.time() - T0:.0f}s")
    SEED = pd.DataFrame(ALLROWS); SEED.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # 閘：營量格各顆相同；營量 v1 ＝ seq1 resultsYLexit
    yl = SEED[SEED["格"].str.startswith("營量")]
    S["閘"]["營量各格各顆 eq_sha 相同（不同的格數）"] = int((yl.groupby(["世界", "格"])["eq_sha"].nunique() > 1).sum())
    ref = pd.read_csv("backtest/resultsYLexit/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    g1 = {}
    for wk in ("主", "早年"):
        rr = ref[(ref["世界"] == wk) & (ref["格"] == "營量v1") & (ref["r"] == 0)]["eq_sha"].iloc[0]
        g1[wk] = bool((SEED[(SEED["世界"] == wk) & (SEED["格"] == "營量v1")]["eq_sha"] == rr).all())
    S["閘"]["營量 v1 ＝ resultsYLexit（seq1）種子 0 eq_sha"] = g1
    log(f"[閘] {S['閘']}")
    # ── 彙總
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in SEGP.items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[ew0 + 1:ew1 + 1]])
    PT = []
    for c in [BASEc] + JIA + YI + [YFB] + YF:
        k = cname(c); g = SEED[(SEED["世界"] == "主") & (SEED["格"] == k)]; ge = SEED[(SEED["世界"] == "早年") & (SEED["格"] == k)]
        row = {"格": k, "件": ("營飆描述" if c[0] == "營飆" else c[1])}
        for sg, gg in (("探索", g), ("確認", g), ("早年", ge)):
            cc, mm = float(gg[f"{sg}_年化"].median()), float(gg[f"{sg}_回落"].median())
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": YX.label(cc, mm, B50[sg]),
                        f"{sg}_持股": float(gg[f"{sg}_持股"].median()), f"{sg}_現金": float(gg[f"{sg}_現金"].median()),
                        f"{sg}_換手每年": float(gg[f"{sg}_換手每年"].median()), f"{sg}_成本每年": float(gg[f"{sg}_成本每年"].median())})
            if f"{sg}_閒置" in gg and gg[f"{sg}_閒置"].notna().any():
                row[f"{sg}_閒置"] = float(gg[f"{sg}_閒置"].median())
            key = ("主" if sg != "早年" else "早年", k, sg)
            if key in DIFF:
                m_, se_ = YX.cr0(DIFF[key], months[sg])
                row.update({f"{sg}_配對差年化": m_ * 245, f"{sg}_配對差lo": (m_ - 1.96 * se_) * 245, f"{sg}_配對差hi": (m_ + 1.96 * se_) * 245})
        PT.append(row)
    PT = pd.DataFrame(PT)
    for bk in ("營量v1", "營飆v1"):
        v1 = PT.set_index("格").loc[bk]; msk = PT["格"].str.startswith(bk[:2])
        for sg in ("探索", "確認", "早年"):
            PT.loc[msk, f"{sg}_年化差"] = PT.loc[msk, f"{sg}_年化"] - v1[f"{sg}_年化"]; PT.loc[msk, f"{sg}_回落差"] = PT.loc[msk, f"{sg}_回落"] - v1[f"{sg}_回落"]
    PT["退化"] = PT["件"].isin(["甲", "乙"]) & ((PT["探索_持股"] < 10) | ((PT["件"] == "乙") & (PT["探索_現金"] > 0.30)))
    J = {}
    for fam, cells in (("甲", JIA), ("乙", YI)):
        cand = PT[(PT["件"] == fam) & ~PT["退化"]]
        q_ = cand[cand["探索_標籤"] == "合格"] if (cand["探索_標籤"] == "合格").any() else cand
        pr = q_.sort_values(["探索_比值", "探索_年化"], ascending=[False, False]).iloc[0]
        lo, hi, ed = pr["確認_配對差lo"], pr["確認_配對差hi"], pr["早年_配對差年化"]
        vs = ("比營量 v1 好" if ed > 0 else "不穩（確認段好、早年反向）") if lo > 0 else (("比營量 v1 差" if ed < 0 else "不穩（確認段差、早年反向）") if hi < 0 else "分不出（確認段配對差 CI 含 0）")
        J[fam] = {"挑中": pr["格"], "cell": next(c for c in cells if cname(c) == pr["格"]), "件標籤": min([pr["確認_標籤"], pr["早年_標籤"]], key=lambda z: ORDER[z]), "對營量v1": vs,
                  **{k_: (pr[k_] if isinstance(pr[k_], str) else float(pr[k_])) for k_ in pr.index if k_ not in ("格", "件")}}
    S["0050"] = B50; S["退化（挑前排除）"] = PT.loc[PT["退化"], "格"].tolist()
    log(f"[判定] " + json.dumps({f: {k_: J[f][k_] for k_ in ('挑中', '件標籤', '對營量v1', '確認_年化', '確認_回落', '早年_年化', '確認_配對差年化', '確認_配對差lo', '確認_配對差hi', '早年_配對差年化')} for f in J}, ensure_ascii=False, default=str))
    # ── 甲 描述臂、必報
    cj = J["甲"]["cell"]; b_, H_, _, _, _ = cj[2]
    CUNL = ("營量", "甲", (b_, H_, WS, 10, None))
    DESC = [("營量", "甲", (b_, H_, (w,), 10, 1)) for w in WS] + [("營量", "甲", (b_, H_, WS, L, 1)) for L in (5, 20)] + [CUNL]
    for wk in ("主", "早年"):
        with Pool(a.procs) as pool:
            rows = [z[0] for z in pool.map(run_cell, [(wk, c, 0) for c in DESC])]
        for x in rows:
            x.pop("r", None)
        PT = pd.concat([PT, pd.DataFrame([{"格": x["格"], "件": "甲描述臂", "世界": wk, **{k_: v_ for k_, v_ in x.items() if k_.endswith(("_年化", "_回落", "_閒置", "_持股"))}} for x in rows])], ignore_index=True)
    PS = {}
    for wk, W in (("主", Wm), ("早年", We)):
        inputs(W, cj); inputs(W, J["乙"]["cell"])
        st = [x for x in W["JST"][cj] if W["w0"] <= x["e"] <= W["w1"]]
        ot = [x for x in st if x["出"] > 0]
        seg_n = sum(len(x["段"]) for x in ot)
        PS[f"{wk}|甲"] = {"筆": len(st), "有暫出的筆比例": len(ot) / max(len(st), 1),
                         "有暫出者：被放棄比例": float(np.mean([x["放棄"] is not None for x in ot])) if ot else np.nan,
                         "放棄原因：警訊": sum(x["放棄"] == "警訊" for x in ot), "放棄原因：等滿10": sum(x["放棄"] == "等滿10" for x in ot),
                         "放棄原因：買回上限": sum(x["放棄"] == "買回上限" for x in ot),
                         **{f"警訊含 {w}（筆）": sum(w in x["警訊"] for x in ot) for w in WS},
                         "有暫出者：最後站回（結束時在場）比例": float(np.mean([(x["放棄"] is None) and (not x["終於暫出"]) for x in ot])) if ot else np.nan,
                         "每筆平均出": float(np.mean([x["出"] for x in st])), "買回：站回（次）": sum(x["進站回"] for x in st), "買回：新訊號（次）": sum(x["進新訊號"] for x in st), "暫出中出現新訊號的根數（不論先後）": sum(x["暫出中出現新訊號根"] for x in st),
                         "暫出段數": seg_n}
        # 放棄後：同日換進的新部位 vs 被放棄那檔抱到 H
        W["KEEP"] = cj
        _, _, kept = run_cell((wk, cj, 0)); W["KEEP"] = None
        eqk, aud = kept
        buys = {}
        opn = {}
        rt = []
        for a_ in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
            if a_["side"] == "buy":
                opn[a_["sid"]] = a_
            else:
                b0 = opn.pop(a_["sid"]); rt.append((b0["t"], a_["sid"], a_["amt"] / b0["amt"] - 1 - a_["cost"] / b0["amt"]))
        by_day = {}
        for t_, s_, r_ in rt:
            by_day.setdefault(t_, []).append(r_)
        cmp = {"警訊": [], "等滿10": [], "買回上限": []}
        stmap = {(x["sid"], x["e"]): x for x in W["JST"][cj]}
        sold = {a_["sid"]: a_["t"] for a_ in aud if a_["side"] == "sell"}
        for (s_, e_), x in stmap.items():
            if x["放棄"] and x["釋出t"] is not None and not (W["w0"] <= e_ <= W["w1"]):
                continue
            if x["放棄"] and x["釋出t"] is not None and sold.get(f"{s_}#{e_}") == x["釋出t"]:
                t_ = x["釋出t"]; xH = min(x["x"], len(W["cal"]) - 1)
                hold = float(W["closes"][s_][xH]) / float(W["opens"][s_][t_]) - 1 - COST if np.isfinite(W["opens"][s_][t_]) and W["opens"][s_][t_] > 0 else np.nan
                new = [r_ for r_ in by_day.get(t_, [])]
                cmp[x["放棄"]].append((hold, float(np.mean(new)) if new else np.nan, len(new)))
        for kx_, v_ in cmp.items():
            if v_:
                arr = np.array(v_, float)
                PS[f"{wk}|甲"][f"放棄（{kx_}）後：被放棄那檔抱到 H 平均（扣成本）"] = float(np.nanmean(arr[:, 0]))
                PS[f"{wk}|甲"][f"放棄（{kx_}）後：同日換進新部位平均淨報酬"] = float(np.nanmean(arr[:, 1])) if np.isfinite(arr[:, 1]).any() else np.nan
                PS[f"{wk}|甲"][f"放棄（{kx_}）：組合實際放棄筆／同日有換進的筆"] = [len(v_), int(np.sum(arr[:, 2] > 0))]
        info, cnt = W["YST"][J["乙"]["cell"]]
        sig = W["SIGH"][("營量", 60)]; m_ = (sig["entry_pos"].to_numpy() >= W["w0"]) & (sig["entry_pos"].to_numpy() <= W["w1"]) & np.isfinite(info["held"])
        h = info["held"][m_]; C_ = J["乙"]["cell"][2][2]
        PS[f"{wk}|乙"] = {"筆": int(m_.sum()), "平均持有根數": float(np.mean(h)), "＞60 根比例": float(np.mean(h > 60)), "觸頂 C 比例": float(np.mean(h >= C_)),
                         "60 根前出比例": float(np.mean(h < 60)), "平均上調次數": float(np.mean(info["ups"][m_])), "出場相對持有期最高收盤回吐（平均）": float(np.mean(info["giveback"][m_])),
                         "計數（全表）": cnt}
        # q（假訊號用）
        W["Q"] = (sum(1 for x in ot if x["放棄"] == "警訊") / seg_n) if seg_n else 0.0
        inputs(W, CUNL)
        stu = [x for x in W["JST"][CUNL] if W["w0"] <= x["e"] <= W["w1"]]
        PS[f"{wk}|甲"]["每筆買回次數分佈（有上限 1）"] = pd.Series([x["進站回"] + x["進新訊號"] for x in st]).value_counts().sort_index().to_dict()
        PS[f"{wk}|甲"]["每筆買回次數分佈（沒上限，seq3 原文）"] = pd.Series([x["進站回"] + x["進新訊號"] for x in stu]).value_counts().sort_index().to_dict()
    S["路徑必報"] = PS
    # ── 假訊號、挪起點
    FK = []; SH = []
    for fam in ("甲", "乙"):
        cell = J[fam]["cell"]
        for wk in ("主", "早年"):
            with Pool(a.procs) as pool:
                FK += pool.map(run_fake, [(wk, cell, i) for i in range(a.reps)], chunksize=4)
            with Pool(a.procs) as pool:
                SH += pool.map(run_shift, [(wk, c_, sg, sh) for c_ in (cell, BASEc) for sg in (["確認"] if wk == "主" else ["早年"]) for sh in SHIFTS])
        log(f"[假訊號／挪起點 {fam}] {time.time() - T0:.0f}s")
    FK = pd.DataFrame(FK); SH = pd.DataFrame(SH)
    FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g"); SH.to_csv(os.path.join(OUT, "shift.csv.gz"), index=False, float_format="%.17g")
    for fam in ("甲", "乙"):
        f_ = FK[FK["格"] == J[fam]["挑中"]]
        J[fam]["假訊號"] = {sg: {"p（假年化 ≥ 本格年化）": float(np.mean(f_[f"{sg}_年化"].dropna() >= J[fam][f"{sg}_年化"])), "假年化中位": float(f_[f"{sg}_年化"].median())}
                          for sg in ("探索", "確認", "早年") if f"{sg}_年化" in f_ and f_[f"{sg}_年化"].notna().any()}
        J[fam]["挪起點（本格、營量 v1 年化）"] = {f"{r_.段}+{r_.挪}": [float(SH[(SH['格'] == J[fam]['挑中']) & (SH['段'] == r_.段) & (SH['挪'] == r_.挪)]['年化'].iloc[0]), float(r_.年化)]
                                            for r_ in SH[SH["格"] == "營量v1"].drop_duplicates(["段", "挪"]).itertuples()}
    S["假訊號 q（甲：每段暫出被警訊放棄的比例）"] = {"主": Wm["Q"], "早年": We["Q"]}
    # ── 新規矩 ③
    SENS = []
    for fam in ("甲", "乙"):
        if not any(J[fam][f"{sg}_標籤"] in ("合格", "另列") for sg in ("確認", "早年")):
            J[fam]["新規矩③"] = "不適用"; continue
        var = {"SL10": {"stop": ("fix", 0.10)}, "SL20": {"stop": ("fix", 0.20)}, "N5": {"N": 5}, "N10": {"N": 10}}
        if fam == "乙":
            var.update({"TP30h": {"trim_rule": {"kind": "gain", "x": 0.30, "frac": 0.5}}, "TP50h": {"trim_rule": {"kind": "gain", "x": 0.50, "frac": 0.5}}})
        for wk in ("主", "早年"):
            with Pool(a.procs) as pool:
                SENS += pool.map(run_sens, [(wk, J[fam]["cell"], vn, kw) for vn, kw in var.items()])
        J[fam]["新規矩③"] = "要跑（見 sens）"
    if SENS:
        SD = pd.DataFrame(SENS); SD.to_csv(os.path.join(OUT, "sens.csv"), index=False, float_format="%.17g")
        S["新規矩③ 出場敏感度（描述）"] = {f"{r_['格']}|{r_['變體']}|{r_['世界']}": {sg: [r_[f"{sg}_年化"], r_[f"{sg}_回落"]] for sg in ("探索", "確認", "早年") if f"{sg}_年化" in r_ and pd.notna(r_.get(f"{sg}_年化"))}
                                   for r_ in SD.to_dict("records")}
    for fam in J:
        J[fam].pop("cell")
    S["判定"] = J
    # seq1 描述臂（同 b／H、同 k／C）
    s1 = pd.read_csv("backtest/resultsYLexit/cells.csv")
    S["seq1 描述臂（resultsYLexit）"] = s1[s1["格"].str.startswith("營量")][["格", "確認_年化", "確認_回落", "早年_年化", "早年_回落", "確認_配對差年化"]].to_dict("records")
    PT.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    np.savez_compressed(os.path.join(OUT, "pairdiff.npz"), **{f"{w}|{k}|{sg}": d for (w, k, sg), d in DIFF.items()})
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
