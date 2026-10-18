# -*- coding: utf-8 -*-
"""營飆「不抽籤、同天出現都買」三種讀法（使用者問「營飆如果不抽籤，同天出現都買，明天開始不買會怎樣？」）——回測線計算子代理。
⭐ 描述、⛔ 不計 N、⛔ 看過結果才提的變體、⛔ 不改營飆 v1 規則。⛔ 不改任何既有 .py／結果夾（research11.py、rerun17.py 一字不動）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYFallin [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYFallin_check

═══ 讀法（寫於 2026-10-18 20:58（台北），在算任何本件數字之前；⚠ 本線看過：營飆 v1／營量 v1 各段年化與回落（resultsYF_N、resultsYL_integrate、
    resultsYLvsYF）、resultsYFskip（C 類「滿了才來」的訊號晚入波段、平均較差）；⛔ 沒看過任何「同日全買」帳的數字）═══
 A1 世界 ＝ researchYL_integrate.main_world（主）與 early_world（早年）；訊號母體 ＝ 該世界 SIG[閘]（營飆 v1 的 t−1 大盤閘）；H120；成本 research11.COST
    出場 ＝ 營飆 v1 同一條：排程出場（xpos_H120、g_H120）、停止交易強制出場（stop_force ＝ W["SF"]）；逐日收盤市值權益；閒置現金報酬 0
 A2 引擎不能表達「超過空槽」與「現金平分」⇒ 本檔寫獨立的逐日迴圈 sim()（照 research11.simulate_mtm 的 stop_force／pick／抽籤 路徑逐行同序）：
    mode "v1"   ＝ 營飆 v1（抽籤：rng ＝ default_rng(rerun17.P10_SEED0＋r)，候選多於空槽時 rng.permutation 取前 空槽 檔；每檔 min(前一日權益÷10, 現金)）
                  ＝ 營量 v1（pick＝relvol：SIG[無閘]、H60、N20、依 relvol 遞減、NaN 最後）
                  ⇒ 引擎模式閘 E1：v1 200 顆 × 兩世界的逐日權益 eq_sha ＝ resultsYF_N（N10）同 r；營量 v1 eq_sha ＝ resultsYL_integrate 格 H60·S20·無·relvol r0；
                     另直接呼叫 research11.simulate_mtm（營飆 r0、營量）逐日權益最大差 ＝ 0（不過即停）
    mode "W1" 同日全買、可超過 10 檔：當天開盤（排程出場與強制出場之後）持股 ＜ 10 且有候選（當天訊號、未持有）⇒ 候選【全部】買進；
                  每檔目標 ＝ 前一日權益 ÷ 10；現金 ＜ 目標 × 候選數 ⇒ 各檔等比例縮小 ＝ 現金 ÷ 候選數；持股 ≥ 10 ⇒ 不買
    mode "W2" 同日全買、資金平分：同 W1 的時機與候選；每檔 ＝ min(現金 ÷ 候選數, 前一日權益 ÷ 10)
    mode "W3" 一波只買第一天：當天開盤持股 ＝ 0 且有候選 ⇒ 現金 ÷ 候選數 全部買進（⛔ 不設每檔上限，照使用者原話）；
                  之後不買任何新股，直到這批全部出場（各自 120 天或強制出場）後持股回到 0，才等下一個訊號日
    共同：每檔金額 ≤ 1e−9 ⇒ 當天不買（＝ 沒現金）；已持有的同一檔不再買（同引擎）；買進價 ＝ 進場日開盤（無效改收盤）
 A3 段（＝ 營飆 v1 原報告段界）：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（主世界一條權益切段讀）；早年 2005-02-01～2014-12-31（早年世界）
 A4 每帳每段：年化、最大回落 ＝ rerun17.win_metrics；比值 ＝ 年化 ÷ |回落|；對 0050 ＝ researchYL_integrate.label（營飆判準：合格／另列／不合格）＋ 0050 同段
    平均持股 ＝ 段內逐日收盤持股檔數平均；最大同時持股 ＝ 段內最大；單檔最大占比 ＝ 段內逐日（單一部位市值 ÷ 權益）的最大值，另報其逐日平均
    現金比例 ＝ 1 − 段內平均(持股市值 ÷ 權益)；換手（每年）＝ 段內買進金額和 ÷ 段內平均權益 ÷ 段年數（＝ researchYL_integrate.stats 同式）；
    成本（每年）＝ 段內賣出筆的 金額 × COST 和 ÷ 段內平均權益 ÷ 段年數；買進筆數（每年）、買進日數（每年）＝ 段內有買進的交易日數 ÷ 段年數；段年數 ＝ 段交易日數 ÷ 245
    W1／W2 另報：段內「當天買進檔數 ＞ 開盤空槽」的日數、最多一天買幾檔；W3 另報 批次數、每批檔數中位與最大
    另報每個日曆年的買進日數（years.csv）
 A5 營飆 v1 ＝ 200 顆中位（年化、回落另報 p10／p90；比值 ＝ 年化中位 ÷ |回落中位|）；營量 v1 ＝ r0 一條；W1～W3 無抽籤 ⇒ 單值；0050 ＝ W["b50"]
 A6 閘（不過即停）：E1（見 A2）；E2 營飆 v1 各段 年化／回落／持股／現金 ＝ resultsYF_N seeds 同 r（repr）；營量 v1 各段 ＝ resultsYL_integrate seeds（repr）；
    E3 0050 各段 ＝ 整合件 summary.json；E4 每帳 現金 ≥ −1e−12、權益 ＞ 0；W1／W2／W3 規則自檢（買進日開盤持股條件、候選全買、金額式）
 ═══ 事後追加（寫於 2026-10-18 21:10（台北）；⚠ 已看過 W1～W3 與營飆 v1 3 顆的煙霧測試結果；上面 A1～A6 一字不動）═══
 B0 煙霧測試後才發現：W1 與 W2 的金額式在數學上恆等（現金 ≥ 目標×候選數 ⇔ 現金÷候選數 ≥ 目標 ⇒ min(現金÷k, 目標) ＝ W1 的式）⇒ 兩帳逐位元相同，只報一次並註明
 B1 W1b「同日全買、超出部分用外部備用金」（使用者澄清後追加的描述格）：本帳 E 從 1 起；開盤（出場後）總持股（本帳格＋超額檔）＜ 10 且有候選 ⇒ 候選全部買；
    依訊號表原序，前「空槽 ＝ 10 − 總持股」檔由本帳出資 min(本帳前一日淨值÷10, 本帳現金)（本帳現金 ≤ 1e−9 ⇒ 該檔改由備用金）；其餘每檔 ＝ 本帳前一日淨值÷10、
    不縮小、由備用金出資（＝ 超額檔）；超額檔出場的淨入帳回備用金；總持股 ≥ 10 ⇒ 不買。⇒ 本帳 ≈「抽籤改為依訊號表原序」的營飆 v1
    備用金規模 Q（⚠ 看結果後才知、事後定）＝ max( 該世界全窗同時最多動用的超額成本 Σ金額, 備用金現金路徑的最大透支 )；以本帳起始 1 為單位
    比較 (a) 合併帳 ＝ (本帳 ＋ Q ＋ 備用金現金 ＋ 超額檔市值) ÷ (1＋Q)，閒置備用金放現金（報酬 0）；對照 ＝ 營飆 v1 每顆 (權益＋Q) ÷ (1＋Q)（200 顆中位、p10／p90）
         (c) 實際投入資金報酬 ＝ 段內買進的每筆交易 Σ金額×(賣價÷買價−1−COST) ÷ Σ金額（不含閒置現金；與營飆 v1 每顆同式取中位）；W1～W3、營量也附
    ⛔ 使用者更正：(b) 閒置備用金放 0050 不算
    另報：超額檔數逐日分布（0／1／2／3／≥4 檔的日數占比）、同時最多超額檔數、超額動用成本 ÷ 本帳淨值 的段內最大、超額交易自己的筆數與平均淨報酬、資金加權報酬
    必附：「備用金規模是看結果後才定，只描述」
 必附：「看過結果的參數變體，只描述，不當改規則的依據；要採用須另行登錄、以前瞻驗證」；早年附「早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）」與 NOTE3
輸出 backtest/resultsYFallin/：seeds.csv.gz（v1 每顆）、cells.csv、years.csv、daily_W.csv.gz、trades_W.csv.gz、summary.json、run.log
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
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402

TIME = "2026-10-18 20:58（台北）"
OUT = "backtest/resultsYFallin"
NSEED = 200
N = 10
COST = R.COST
if os.environ.get("YFA_QUICK"):                              # 煙霧測試（不是交件）
    NSEED, OUT = 3, "/tmp/yfa_quick"
WORD = "看過結果的參數變體，只描述，不當改規則的依據；要採用須另行登錄、以前瞻驗證"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；早年照營飆 v1 早年既有版面（上市＋上櫃 eotc_f65bb03e11、R8 截斷）", IG.NOTE3]
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}
MODES = ("W1", "W2", "W3")
MNAME = {"v1": "營飆 v1（抽籤）", "YL": "營量 v1", "W1": "W1 同日全買·可超過10檔", "W2": "W2 同日全買·資金平分", "W3": "W3 一波只買第一天"}
_W: dict = {}


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


# ═════════════ 訊號表 ═════════════
def build_days(sig, H, pick=None):
    """＝ simulate_mtm 的 d／by_entry：dropna(四欄)、xpos ≥ 0、依 entry_pos 分組（組內保原序）。"""
    cols = ["sid", "entry_pos", f"xpos_H{H}", f"g_H{H}"]
    d = sig[cols + ([pick] if pick else [])].dropna(subset=cols)
    d = d[d[f"xpos_H{H}"] >= 0]
    days = {}
    for k, g in d.groupby("entry_pos"):
        days[int(k)] = (list(g["sid"]), [int(v) for v in g[f"xpos_H{H}"]], [float(v) for v in g[f"g_H{H}"]],
                        g[pick].to_numpy(float) if pick else None)
    return days, int(d["entry_pos"].min()), int(d[f"xpos_H{H}"].max())


# ═════════════ 逐日迴圈（A2）═════════════
def sim(W, DAYS, mode, n_slots=N, rng=None, pick=False):
    days, first, last = DAYS
    NP = W["NP"]; cl, op, SF = W["closes"], W["opens"], W["SF"]
    equity = np.ones(NP); hold_val = np.zeros(NP); cash = 1.0; open_pos = []; held = set()
    npos = np.zeros(NP, int); maxw = np.zeros(NP); mincash = 1.0
    buys, sells, dinfo = [], [], []
    eq_prev = 1.0
    t_end = min(NP, last + 2)
    for t in range(first, t_end):
        if open_pos:                                   # 停止交易強制出場（＝ 引擎 stop_force 段）
            for k, (ex, sid, amt, gross, ep) in enumerate(open_pos):
                L = SF.get(sid)
                if L is not None and t == L + 1 and ex > t:
                    open_pos[k] = (t, sid, amt, float(cl[sid][L]) / ep - 1.0, ep)
        still = []
        for p in open_pos:
            ex, sid, amt, gross, ep = p
            if ex <= t:
                cash += amt * (1 + gross - COST)
                held.discard(sid)
                sells.append((t, sid, amt, amt * (1 + gross), amt * COST, eq_prev))
            else:
                still.append(p)
        open_pos = still
        day = days.get(t)
        if day is not None:
            sids, xs, gs, keys = day
            n0 = len(open_pos)
            ok = (n0 == 0) if mode == "W3" else (n0 < n_slots)
            if ok:
                ci = [i for i in range(len(sids)) if sids[i] not in held]
                if ci:
                    take = []; amts = []
                    if mode == "v1":
                        free = n_slots - n0
                        if pick:
                            key = keys[ci]; key = np.where(np.isnan(key), -np.inf, key)
                            order = np.argsort(-key, kind="stable")
                        else:
                            order = rng.permutation(len(ci))
                        slot = equity[t - 1] / n_slots
                        for i in order[:free]:
                            amt = min(slot, cash)
                            if amt <= 1e-9:
                                break
                            take.append(ci[i]); amts.append(None)
                            cash -= amt
                            buys.append(_buy(open_pos, held, op, cl, sids[ci[i]], xs[ci[i]], gs[ci[i]], amt, t, eq_prev))
                    else:
                        kk = len(ci); slot = equity[t - 1] / n_slots; c0 = cash
                        if mode == "W1":
                            a = slot if c0 >= slot * kk else c0 / kk
                        elif mode == "W2":
                            a = min(c0 / kk, slot)
                        else:
                            a = c0 / kk
                        if a > 1e-9:
                            for i in ci:
                                amt = min(a, cash)
                                cash -= amt
                                take.append(i)
                                buys.append(_buy(open_pos, held, op, cl, sids[i], xs[i], gs[i], amt, t, eq_prev))
                    dinfo.append((t, n0, n_slots - n0, len(ci), len(take)))
        hv = sum(amt * float(cl[sid][t]) / ep for _, sid, amt, _, ep in open_pos)
        equity[t] = cash + hv
        hold_val[t] = hv; npos[t] = len(open_pos); mincash = min(mincash, cash)
        if open_pos and equity[t] > 0:
            maxw[t] = max((amt * float(cl[sid][t]) / ep) / equity[t] for _, sid, amt, _, ep in open_pos)
        eq_prev = equity[t]
    end = min(NP, last + 2)
    equity[:first] = 1.0; equity[end:] = equity[end - 1]
    return {"equity": equity, "hold_val": hold_val, "npos": npos, "maxw": maxw, "first": first, "end": end, "buys": buys, "sells": sells,
            "dinfo": dinfo, "mincash": mincash, "open_end": [(sid, ex) for ex, sid, *_ in open_pos]}


def _buy(open_pos, held, op, cl, sid, x, g, amt, t, eq_prev):
    ep = float(op[sid][t])
    if not np.isfinite(ep) or ep <= 0:
        ep = float(cl[sid][t])
    open_pos.append((int(x), sid, amt, float(g), ep)); held.add(sid)
    return (t, sid, amt, eq_prev, ep, int(x))


# ═════════════ W1b（B1，事後追加）═════════════
def sim_w1b(W, DAYS):
    days, first, last = DAYS
    NP = W["NP"]; cl, op, SF = W["closes"], W["opens"], W["SF"]
    E = np.ones(NP); RC = np.zeros(NP); X = np.zeros(NP); U = np.zeros(NP); NX = np.zeros(NP, int); npos = np.zeros(NP, int); HV = np.zeros(NP)
    cash = 1.0; rc = 0.0; rc_min = 0.0; open_pos = []; held = set(); buys, sells, dinfo = [], [], []
    eq_prev = 1.0
    t_end = min(NP, last + 2)
    for t in range(first, t_end):
        if open_pos:
            for k, (ex, sid, amt, gross, ep, isx) in enumerate(open_pos):
                L = SF.get(sid)
                if L is not None and t == L + 1 and ex > t:
                    open_pos[k] = (t, sid, amt, float(cl[sid][L]) / ep - 1.0, ep, isx)
        still = []
        for p in open_pos:
            ex, sid, amt, gross, ep, isx = p
            if ex <= t:
                if isx:
                    rc += amt * (1 + gross - COST)
                else:
                    cash += amt * (1 + gross - COST)
                held.discard(sid)
                sells.append((t, sid, amt, amt * (1 + gross), amt * COST, eq_prev, isx))
            else:
                still.append(p)
        open_pos = still
        day = days.get(t)
        if day is not None:
            sids, xs, gs, _ = day
            n0 = len(open_pos)
            if n0 < N:
                ci = [i for i in range(len(sids)) if sids[i] not in held]
                if ci:
                    free = N - n0; slot = E[t - 1] / N; nx_ = 0
                    for j, i in enumerate(ci):
                        isx = True
                        if j < free:
                            amt = min(slot, cash)
                            if amt > 1e-9:
                                cash -= amt; isx = False
                        if isx:
                            amt = slot; rc -= amt; nx_ += 1
                        s = sids[i]; ep = float(op[s][t])
                        if not np.isfinite(ep) or ep <= 0:
                            ep = float(cl[s][t])
                        open_pos.append((int(xs[i]), s, amt, float(gs[i]), ep, isx)); held.add(s)
                        buys.append((t, s, amt, eq_prev, ep, int(xs[i]), isx))
                    rc_min = min(rc_min, rc)
                    dinfo.append((t, n0, free, len(ci), len(ci), nx_))
        hvm = sum(amt * float(cl[sid][t]) / ep for _, sid, amt, _, ep, isx in open_pos if not isx)
        hvx = sum(amt * float(cl[sid][t]) / ep for _, sid, amt, _, ep, isx in open_pos if isx)
        E[t] = cash + hvm; HV[t] = hvm; RC[t] = rc; X[t] = hvx
        U[t] = sum(amt for _, _, amt, _, _, isx in open_pos if isx); NX[t] = sum(1 for p in open_pos if p[5]); npos[t] = len(open_pos)
        eq_prev = E[t]
    end = min(NP, last + 2)
    E[:first] = 1.0
    for A in (E, RC, X, U):
        A[end:] = A[end - 1]
    NX[end:] = NX[end - 1]; npos[end:] = npos[end - 1]
    return {"E": E, "HV": HV, "RC": RC, "X": X, "U": U, "NX": NX, "npos": npos, "first": first, "end": end, "buys": buys, "sells": sells,
            "dinfo": dinfo, "rc_min": rc_min, "open_end": len(open_pos)}


def trade_list(o):
    """買賣配對（同一檔同時只會持有一筆）⇒ [(買進日, 金額, 淨報酬, 是否超額)]。"""
    op_, T = {}, []
    ev = [(b[0], 1, b) for b in o["buys"]] + [(s[0], 0, s) for s in o["sells"]]
    for t, side, z in sorted(ev, key=lambda q: (q[0], q[1])):        # 同日先賣後買（＝ 迴圈順序）
        if side == 1:
            op_[z[1]] = z
        else:
            b = op_.pop(z[1])
            T.append((b[0], b[2], z[3] / b[2] - 1.0 - COST, bool(b[6]) if len(b) > 6 else False))
    if op_:
        raise SystemExit(f"⛔ 模擬尾仍有 {len(op_)} 筆未賣")
    return T


def cw_ret(T, x, y, which=None):
    z = [(a, r) for tb, a, r, isx in T if x <= tb <= y and (which is None or isx == which)]
    if not z:
        return np.nan, np.nan, 0
    a = np.array([q[0] for q in z]); r = np.array([q[1] for q in z])
    return float((a * r).sum() / a.sum()), float(r.mean()), len(z)


# ═════════════ 段統計（A4）═════════════
def seg_metrics(W, o, sg):
    x, y = W["segp"][sg]
    eq, hv = o["equity"], o["hold_val"]
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
    yrs = (y - x + 1) / 245.0; meq = float(np.mean(eq[x:y + 1]))
    bs = [b for b in o["buys"] if x <= b[0] <= y]; ss = [s for s in o["sells"] if x <= s[0] <= y]
    di = [d for d in o["dinfo"] if x <= d[0] <= y and d[4] > 0]
    bdays = sorted({b[0] for b in bs})
    row = {"年化": float(c_), "回落": float(m_), "比值": float(c_) / abs(float(m_)) if m_ else np.nan,
           "持股": float(np.mean(o["npos"][x:y + 1])), "最大持股": int(np.max(o["npos"][x:y + 1])),
           "單檔最大占比": float(np.max(o["maxw"][x:y + 1])), "單檔占比日均最大": float(np.mean(o["maxw"][x:y + 1])),
           "現金": float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1])),
           "換手每年": float(sum(b[2] for b in bs) / meq / yrs), "成本每年": float(sum(s[4] for s in ss) / meq / yrs),
           "買進筆每年": len(bs) / yrs, "買進日每年": len(bdays) / yrs,
           "超空槽日數": int(sum(1 for d in di if d[4] > d[2])), "單日最多買": int(max((d[4] for d in di), default=0)),
           "批次數": len(di), "每批檔數中位": float(np.median([d[4] for d in di])) if di else np.nan}
    row["投入報酬"], row["每筆淨報酬平均"], _ = cw_ret(trade_list(o), x, y)          # B1 (c)
    Q = W.get("Q")
    if Q is not None:                                                                # B1 (a) 對照：本帳＋同額現金
        cq, mq, _ = RR.win_metrics((eq + Q) / (1 + Q), o["first"], o["end"], x, y)
        row["加備用金年化"] = float(cq); row["加備用金回落"] = float(mq)
    return row


def seg_w1b(W, o, sg, Q):
    x, y = W["segp"][sg]
    C = (o["E"] + Q + o["RC"] + o["X"]) / (1 + Q)
    c_, m_, _ = RR.win_metrics(C, o["first"], o["end"], x, y)
    cb, mb, _ = RR.win_metrics(o["E"], o["first"], o["end"], x, y)
    T = trade_list(o)
    nx = o["NX"][x:y + 1]
    di = [d for d in o["dinfo"] if x <= d[0] <= y]
    yrs = (y - x + 1) / 245.0
    row = {"合併年化": float(c_), "合併回落": float(m_), "合併比值": float(c_) / abs(float(m_)), "本帳年化": float(cb), "本帳回落": float(mb),
           "持股": float(np.mean(o["npos"][x:y + 1])), "最大持股": int(np.max(o["npos"][x:y + 1])),
           "同時最多超額檔": int(nx.max()), "超額動用占本帳最大": float(np.max(o["U"][x:y + 1] / o["E"][x:y + 1])),
           "超額動用最大（本帳起始＝1）": float(np.max(o["U"][x:y + 1])),
           "超空槽日數": int(sum(1 for d in di if d[5] > 0)), "單日最多買": int(max((d[4] for d in di), default=0)),
           "單日最多超額": int(max((d[5] for d in di), default=0)), "買進日每年": len(di) / yrs,
           "合併現金占比": float(np.mean((Q + o["RC"][x:y + 1] + o["E"][x:y + 1] - o["HV"][x:y + 1]) / (o["E"][x:y + 1] + Q + o["RC"][x:y + 1] + o["X"][x:y + 1])))}
    for j, lab in enumerate(("0", "1", "2", "3")):
        row[f"超額{lab}檔日占比"] = float(np.mean(nx == j))
    row["超額≥4檔日占比"] = float(np.mean(nx >= 4))
    row["投入報酬"], row["每筆淨報酬平均"], row["交易筆數"] = cw_ret(T, x, y)
    row["本帳交易_投入報酬"], row["本帳交易_平均"], row["本帳交易_筆數"] = cw_ret(T, x, y, False)
    row["超額交易_投入報酬"], row["超額交易_平均"], row["超額交易_筆數"] = cw_ret(T, x, y, True)
    return row


def year_counts(W, o):
    cal = W["cal"]; yy = {}
    for t in sorted({b[0] for b in o["buys"]}):
        if W["w0"] <= t <= W["w1"]:
            yy[int(cal[t].year)] = yy.get(int(cal[t].year), 0) + 1
    return yy


def rule_check(W, DAYS, o, mode):
    """E4：W 帳每個買進日都符合規則（開盤持股條件、候選全買、金額式）；回不符筆數。"""
    days = DAYS[0]; bad = 0
    byt = {}
    for b in o["buys"]:
        byt.setdefault(b[0], []).append(b)
    for t, n0, free, nc, nb in o["dinfo"]:
        if mode == "W3" and n0 != 0:
            bad += 1
        if mode in ("W1", "W2") and n0 >= N:
            bad += 1
        if nb not in (0, nc):
            bad += 1
        bb = byt.get(t, [])
        if len(bb) != nb or (bb and max(b[2] for b in bb) > min(b[2] for b in bb) * (1 + 1e-12)):
            bad += 1
        if nb and len(bb):
            slot = bb[0][3] / N
            if mode in ("W1", "W2") and bb[0][2] > slot * (1 + 1e-12):
                bad += 1
    return bad


# ═════════════ 工作 ═════════════
def job(args):
    wn, mode, r = args
    W = _W[wn]
    if mode == "v1":
        o = sim(W, W["DAYS_F"], "v1", N, rng=np.random.default_rng(RR.P10_SEED0 + r))
    elif mode == "YL":
        o = sim(W, W["DAYS_Y"], "v1", 20, pick=True)
    else:
        o = sim(W, W["DAYS_F"], mode, N)
    row = {"世界": wn, "帳": mode, "r": r, "eq_sha": sha(o["equity"]), "first": o["first"], "end": o["end"], "trades": len(o["buys"]),
           "最低現金": o["mincash"], "最低權益": float(np.min(o["equity"]))}
    for sg in SEGS[wn]:
        for k, v in seg_metrics(W, o, sg).items():
            row[f"{sg}_{k}"] = v
    extra = None
    if mode != "v1" or r == 0:
        extra = {"years": year_counts(W, o), "rule_bad": rule_check(W, W["DAYS_F"], o, mode) if mode in MODES else 0,
                 "eq": o["equity"], "npos": o["npos"], "hv": o["hold_val"], "buys": o["buys"], "sells": o["sells"], "dinfo": o["dinfo"]}
    return row, extra


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}｜種子 {NSEED}")
    Wm, gm = IG.main_world(log)
    We, ge = IG.early_world(log, a.procs)
    for W in (Wm, We):
        W["DAYS_F"] = build_days(W["SIG"][True], 120)
        W["DAYS_Y"] = build_days(W["SIG"][False], 60, pick="relvol")
    _W["主"], _W["早年"] = Wm, We
    gate = {}
    # B1 W1b：先跑（決定 Q，⚠ 事後），再讓 v1 各顆在 job 裡算「本帳＋Q 現金」對照
    OB = {}
    for wn, W in _W.items():
        ob = sim_w1b(W, W["DAYS_F"]); OB[wn] = ob
        q_lit = float(np.max(ob["U"])); need = float(max(0.0, -ob["rc_min"]))
        W["Q"] = max(q_lit, need)
        ob["Q_lit"], ob["need"] = q_lit, need
        bad = 0; byt = {}
        for b in ob["buys"]:
            byt.setdefault(b[0], []).append(b)
        for t, n0, free, nc, nb, nx_ in ob["dinfo"]:
            bb = byt.get(t, [])
            bad += int(n0 >= N) + int(len(bb) != nc) + int(nx_ < max(0, nc - free)) + int(sum(1 for b in bb if b[6]) != nx_)
            bad += int(any(b[6] and abs(b[2] - b[3] / N) > 1e-15 for b in bb))
        gate[f"E5 {wn} W1b 規則不符（筆）"] = bad
        gate[f"E5 {wn} W1b 合併帳備用金透支（Q＋現金 ＜ −1e−12 天數）"] = int((W["Q"] + ob["RC"] < -1e-12).sum())
        log(f"[W1b {wn}] Q ＝ {W['Q']:.6f}（同時最多超額成本 {q_lit:.6f}、現金路徑最大透支 {need:.6f}）｜買進 {len(ob['buys'])}｜超額買進 {sum(1 for b in ob['buys'] if b[6])}")
    # E1b：直接對 simulate_mtm（營飆 r0、營量）
    for wn, W in _W.items():
        oF = R.simulate_mtm(W["SIG"][True], "H120", N, np.random.default_rng(RR.P10_SEED0), W["closes"], W["opens"], W["NP"], return_equity=True, stop_force=W["SF"])
        mF = sim(W, W["DAYS_F"], "v1", N, rng=np.random.default_rng(RR.P10_SEED0))
        oY = R.simulate_mtm(W["SIG"][False], "H60", 20, np.random.default_rng(RR.P1_SEED0), W["closes"], W["opens"], W["NP"], return_equity=True,
                            log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"])
        mY = sim(W, W["DAYS_Y"], "v1", 20, pick=True)
        gate[f"E1b {wn} 營飆 r0 權益最大差 vs simulate_mtm"] = float(np.max(np.abs(oF["equity"] - mF["equity"])))
        gate[f"E1b {wn} 營飆 r0 持股市值最大差"] = float(np.max(np.abs(oF["hold_val"] - mF["hold_val"])))
        gate[f"E1b {wn} 營飆 r0 trades 差"] = int(oF["trades"] - len(mF["buys"]))
        gate[f"E1b {wn} 營量 權益最大差 vs simulate_mtm"] = float(np.max(np.abs(oY["equity"] - mY["equity"])))
        gate[f"E1b {wn} 營量 trades 差"] = int(oY["trades"] - len(mY["buys"]))
    log(f"[E1b] {gate}")
    jobs = [(wn, "v1", r) for wn in ("主", "早年") for r in range(NSEED)] + [(wn, m, 0) for wn in ("主", "早年") for m in ("YL",) + MODES]
    T0 = time.time()
    with Pool(a.procs) as pool:
        RES = pool.map(job, jobs, chunksize=4)
    log(f"[迴圈] {len(RES)} 次｜{time.time() - T0:.0f}s")
    SE = pd.DataFrame([z[0] for z in RES])
    EX = {(z[0]["世界"], z[0]["帳"]): z[1] for z in RES if z[1] is not None}
    # ── 閘 ──
    rf = pd.read_csv("backtest/resultsYF_N/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    ri = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    for wn in ("主", "早年"):
        a_ = SE[(SE["世界"] == wn) & (SE["帳"] == "v1")].set_index("r")
        b_ = rf[(rf["世界"] == wn) & (rf["N"] == N)].set_index("r")
        gate[f"E1 {wn} 營飆 v1 eq_sha ≠ YF_N（顆／{len(a_)}）"] = int(sum(a_.loc[r, "eq_sha"] != b_.loc[r, "eq_sha"] for r in a_.index))
        gate[f"E2 {wn} 營飆 v1 段值 ≠ YF_N（顆）"] = int(sum(any(repr(float(a_.loc[r, f"{sg}_{k}"])) != repr(float(b_.loc[r, f"{sg}_{k}"]))
                                                          for sg in SEGS[wn] for k in ("年化", "回落", "持股", "現金")) for r in a_.index))
        gate[f"E2 {wn} 營飆 v1 trades ≠ YF_N（顆）"] = int(sum(int(a_.loc[r, "trades"]) != int(b_.loc[r, "trades"]) for r in a_.index))
        y_ = SE[(SE["世界"] == wn) & (SE["帳"] == "YL")].iloc[0]
        yi = ri[(ri["世界"] == wn) & (ri["格"] == IG.YL) & (ri["r"] == 0)].iloc[0]
        gate[f"E1 {wn} 營量 v1 eq_sha ≠ 整合件"] = int(y_["eq_sha"] != yi["eq_sha"])
        gate[f"E2 {wn} 營量 v1 段值 ≠ 整合件（項）"] = int(sum(repr(float(y_[f"{sg}_{k}"])) != repr(float(yi[f"{sg}_{k}"]))
                                                         for sg in SEGS[wn] for k in ("年化", "回落", "持股", "現金")))
    sm = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
    gate["E3 0050 各段 ≠ 整合件（項）"] = int(sum(repr(float(_W[wn]["b50"][sg][k])) != repr(float(sm[wn][sg][k]))
                                            for wn in ("主", "早年") for sg in SEGS[wn] for k in ("cagr", "mdd")))
    gate["E4 現金 ＜ −1e−12 或權益 ≤ 0（帳）"] = int(((SE["最低現金"] < -1e-12) | (SE["最低權益"] <= 0)).sum())
    gate["E4 W 規則不符（筆）"] = int(sum(EX[(wn, m)]["rule_bad"] for wn in ("主", "早年") for m in MODES))
    log(f"[閘] {gate}")
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    S = {"讀法寫死": TIME, "性質": "描述、不計 N、看過結果才提的變體、不改規則", "必附": WORD, "早年註": NOTE_EARLY, "世界閘": {**gm, **ge}, "閘": gate}
    hard = [k for k, v in gate.items() if (v > 0 if "最大差" in k else v != 0)]
    if hard:
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit(f"⛔ 閘不過 {hard}")
    # ── 逐日／逐筆（W 帳、v1 r0、營量；給查核）──
    DL, TL = [], []
    for (wn, m), ex in EX.items():
        cal = _W[wn]["cal"]
        DL.append(pd.DataFrame({"世界": wn, "帳": m, "t": np.arange(len(ex["eq"])),
                                "日期": [cal[t].strftime("%Y-%m-%d") if t < len(cal) else "" for t in range(len(ex["eq"]))],
                                "權益": ex["eq"], "持股市值": ex["hv"], "持股": ex["npos"]}))
        for b in ex["buys"]:
            TL.append({"世界": wn, "帳": m, "side": "buy", "t": b[0], "sid": b[1], "amt": b[2], "eq_prev": b[3], "px": b[4], "xpos": b[5]})
        for s_ in ex["sells"]:
            TL.append({"世界": wn, "帳": m, "side": "sell", "t": s_[0], "sid": s_[1], "amt": s_[2], "amt_out": s_[3], "cost": s_[4], "eq_prev": s_[5]})
    pd.concat(DL, ignore_index=True).to_csv(os.path.join(OUT, "daily_W.csv.gz"), index=False, float_format="%.17g")
    pd.DataFrame(TL).to_csv(os.path.join(OUT, "trades_W.csv.gz"), index=False, float_format="%.17g")
    # ── 彙總 ──
    MET = ["年化", "回落", "持股", "最大持股", "單檔最大占比", "單檔占比日均最大", "現金", "換手每年", "成本每年", "買進筆每年", "買進日每年",
           "超空槽日數", "單日最多買", "批次數", "每批檔數中位", "投入報酬", "每筆淨報酬平均"]
    C = []
    for wn in ("主", "早年"):
        W = _W[wn]
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]; b = W["b50"][sg]
            for m in ("v1", "YL") + MODES:
                g = SE[(SE["世界"] == wn) & (SE["帳"] == m)]
                row = {"世界": wn, "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}", "帳": MNAME[m], "顆數": len(g)}
                for k in MET:
                    v = g[f"{sg}_{k}"].astype(float)
                    row[k] = float(v.median())
                    if m == "v1" and k in ("年化", "回落", "持股", "換手每年", "買進日每年"):
                        row[f"{k}_p10"] = float(v.quantile(.1)); row[f"{k}_p90"] = float(v.quantile(.9))
                row["比值"] = row["年化"] / abs(row["回落"])
                row["對0050"] = IG.label(row["年化"], row["回落"], b)
                row.update({"0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])})
                C.append(row)
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    # ── W1b（B1）──
    CB = []
    for wn in ("主", "早年"):
        W = _W[wn]; Q = W["Q"]; ob = OB[wn]
        for sg in SEGS[wn]:
            b = W["b50"][sg]
            row = {"世界": wn, "段": sg, "Q（本帳起始＝1）": Q, "Q_同時最多超額成本": ob["Q_lit"], "Q_現金最大透支": ob["need"], **seg_w1b(W, ob, sg, Q)}
            row["合併對0050"] = IG.label(row["合併年化"], row["合併回落"], b)
            g = SE[(SE["世界"] == wn) & (SE["帳"] == "v1")]
            for k in ("加備用金年化", "加備用金回落", "投入報酬", "每筆淨報酬平均"):
                v = g[f"{sg}_{k}"].astype(float)
                row[f"v1_{k}_中位"] = float(v.median()); row[f"v1_{k}_p10"] = float(v.quantile(.1)); row[f"v1_{k}_p90"] = float(v.quantile(.9))
            row["v1_加備用金比值"] = row["v1_加備用金年化_中位"] / abs(row["v1_加備用金回落_中位"])
            row["v1_加備用金對0050"] = IG.label(row["v1_加備用金年化_中位"], row["v1_加備用金回落_中位"], b)
            row["v1_年化_中位"] = float(g[f"{sg}_年化"].median()); row["v1_回落_中位"] = float(g[f"{sg}_回落"].median())
            row.update({"0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])})
            CB.append(row)
        cal = W["cal"]
        DL_b = pd.DataFrame({"世界": wn, "t": np.arange(W["NP"]), "本帳": ob["E"], "本帳持股市值": ob["HV"], "備用金現金": ob["RC"], "超額市值": ob["X"],
                             "超額成本": ob["U"], "超額檔": ob["NX"], "總持股": ob["npos"]})
        DL_b.to_csv(os.path.join(OUT, f"daily_W1b_{wn}.csv.gz"), index=False, float_format="%.17g")
        pd.DataFrame([{"side": "buy", "t": z[0], "sid": z[1], "amt": z[2], "eq_prev": z[3], "px": z[4], "xpos": z[5], "超額": int(z[6])} for z in ob["buys"]] +
                     [{"side": "sell", "t": z[0], "sid": z[1], "amt": z[2], "amt_out": z[3], "cost": z[4], "eq_prev": z[5], "超額": int(z[6])} for z in ob["sells"]]
                     ).to_csv(os.path.join(OUT, f"trades_W1b_{wn}.csv.gz"), index=False, float_format="%.17g")
    CB = pd.DataFrame(CB)
    CB.to_csv(os.path.join(OUT, "cells_W1b.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S["W1b"] = {"註": ["備用金規模是看結果後才定，只描述", "使用者澄清後追加；(b) 閒置放 0050 依使用者更正不算", "W1 與 W2 金額式數學恆等 ⇒ 兩帳相同"],
                "表": CB.to_dict("records")}
    YR = []
    for (wn, m), ex in EX.items():
        for yv, n_ in sorted(ex["years"].items()):
            YR.append({"世界": wn, "帳": MNAME[m] + ("（r0）" if m == "v1" else ""), "年": yv, "買進日數": n_})
    YR = pd.DataFrame(YR)
    YR.to_csv(os.path.join(OUT, "years.csv"), index=False, encoding="utf-8-sig")
    S["表"] = C.to_dict("records"); S["每年買進日數"] = YR.to_dict("records"); S["完成（台北）"] = now_tpe()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
    show = ["世界", "段", "帳", "年化", "年化_p10", "年化_p90", "回落", "比值", "對0050", "持股", "最大持股", "單檔最大占比", "現金", "換手每年", "成本每年",
            "買進日每年", "超空槽日數", "單日最多買", "批次數", "投入報酬", "每筆淨報酬平均", "0050年化", "0050回落"]
    log("\n" + C[show].to_string(index=False))
    log("\n" + YR.pivot_table(index="年", columns=["世界", "帳"], values="買進日數").to_string())
    log("\n[W1b]\n" + CB.T.to_string())
    log(f"[完] {now_tpe()}（台北）")


if __name__ == "__main__":
    main()
