# -*- coding: utf-8 -*-
"""營量「有空位且當天候選多於空位時，夠錢就全買（可超過 20 檔）」兩種讀法（使用者問「營量如果超過空位…我指買超過 20 檔」）——回測線計算子代理。
⭐ 描述、⛔ 不計 N、⛔ 看過結果才提的變體、⛔ 不改營量 v1 規則。⛔ 不改任何既有 .py／結果夾（策略鎖 25 支、researchYFallin.py 一字不動）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLallin [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLallin_check

═══ 讀法（寫於 2026-10-18 23:10（台北），在算任何本件數字之前；⚠ 本線看過：營量 v1／營飆 v1 各段年化與回落、resultsYFallin（營飆 W1／W1b 全部數字）；
    ⛔ 沒看過任何「營量同日全買」帳的數字）═══
 L1 世界 ＝ researchYL_integrate.main_world（主）與 early_world（早年）；訊號母體 ＝ SIG[無閘]（營量 v1 無大盤閘）；H60；N20；成本 research11.COST
    出場 ＝ 營量 v1 同一條：排程出場（xpos_H60、g_H60）、停止交易強制出場（stop_force ＝ W["SF"]）；逐日收盤市值權益；閒置現金報酬 0
 L2 逐日迴圈：⭐ 直接 import researchYFallin.sim（已驗證；⛔ 不改）——
    "YL"  ＝ sim(DAYS_Y, "v1", 20, pick=True) ＝ 營量 v1 定版（relvol 遞減、NaN 最後；每檔 min(前一日權益÷20, 現金)）
            ⇒ 引擎模式閘：主世界 eq_sha 與主窗年化／回落 ＝ resultsT1fix c13 t1 r0；兩世界 ＝ resultsYL_integrate 格 H60·S20·無·relvol r0、resultsYFallin YL；
               另直接呼叫 research11.simulate_mtm 逐日權益最大差 ＝ 0（不過即停）
    "V1"  ＝ sim(DAYS_Y, "W1", 20)（＝ 營飆 W1 套營量參數）：當天開盤（排程出場與強制出場之後）持股 ＜ 20 且有候選（當天訊號、未持有）⇒ 候選【全部】買進、可超過 20 檔；
            每檔目標 ＝ 前一日權益 ÷ 20；現金 ＜ 目標 × 候選數 ⇒ 各檔等比例縮小 ＝ 現金 ÷ 候選數；持股 ≥ 20 ⇒ 不買
            ⚠ relvol 在 V1 只在「不買滿」時才有作用 ⇒ V1 一律全買，relvol 不影響買哪幾檔（只用來標記哪幾檔算「超出空槽」，見 L4）
    "V1b" ＝ 本檔 sim_w1b_g(DAYS_Y, n=20, pick=True)（＝ researchYFallin.sim_w1b 參數化：N 10→20、本帳出資順序由「訊號表原序」改 relvol 遞減；其餘逐行同）：
            本帳 E 從 1 起；開盤（出場後）總持股（本帳格＋超額檔）＜ 20 且有候選 ⇒ 候選全部買；依 relvol 遞減，前「空槽 ＝ 20 − 總持股」檔由本帳出資
            min(本帳前一日淨值÷20, 本帳現金)（本帳現金 ≤ 1e−9 ⇒ 該檔改由備用金）；其餘每檔 ＝ 本帳前一日淨值÷20、不縮小、由備用金出資（＝ 超額檔）；
            超額檔出場的淨入帳回備用金；總持股 ≥ 20 ⇒ 不買。⇒ 本帳 ≈ 營量 v1（差在超額檔也占總持股與「已持有不再買」）
            ⇒ 參數化閘：sim_w1b_g(DAYS_F, n=10, pick=False) 的 E／RC／X／U／NX 與買賣紀錄 ＝ researchYFallin.sim_w1b 逐位元、Q ＝ resultsYFallin W1b 表（repr）
            備用金規模 Q（⚠ 看結果後才知、事後定）＝ max( 該世界全窗同時最多動用的超額成本 Σ金額, 備用金現金路徑的最大透支 )；以本帳起始 1 為單位
            比較 (a) 合併帳 ＝ (本帳 ＋ Q ＋ 備用金現金 ＋ 超額檔市值) ÷ (1＋Q)，閒置放現金（報酬 0）；對照 ＝ 營量 v1 (權益＋Q) ÷ (1＋Q)
                 (c) 實際投入資金報酬 ＝ 段內買進的每筆交易 Σ金額×(賣價÷買價−1−COST) ÷ Σ金額（＝ researchYFallin.cw_ret）
            ⛔ 不做「閒置放 0050」（使用者已說不用）
 L3 段（＝ 營飆 v1 原報告段界）：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（主世界一條權益切段讀）；早年 2005-02-01～2014-12-31（早年世界）
 L4 每帳每段：年化、最大回落 ＝ rerun17.win_metrics；比值 ＝ 年化 ÷ |回落|；對 0050 ＝ researchYL_integrate.label；平均／最大持股；現金比例；換手、成本（每年）
    ＝ researchYFallin.seg_metrics 同式（V1b 合併帳另以 合併權益 (E＋Q＋RC＋X) 為分母同式計）
    超額相關：超空槽日數（當天買進檔數 ＞ 開盤空槽）、最多一天買幾檔；同時最多超額檔數（V1 ＝ max(持股 − 20, 0)；V1b ＝ 同時持有的備用金出資檔數）、超過 20 檔的日數占比；
    超額交易：V1 每個買進日依 relvol 遞減，前「空槽」檔算本帳、其餘算超額（只是標記，不影響金額）；V1b ＝ 備用金出資檔；報筆數與平均淨報酬，對照營量 v1 每筆平均
    V1 另報「現金不足等比例縮小」的日數；V1b 另報 Q（＝ 備用金峰值占本帳起始倍數）、段內超額動用成本峰值、超額動用 ÷ 當時本帳淨值 的段內最大
 L5 對照：營量 v1（r0 一條）；營飆 v1 ＝ resultsYFallin/summary.json「表」200 顆中位（讀取）；營飆 W1 ＝ 本檔以 sim(DAYS_F, "W1", 10) 重算、與 resultsYFallin seeds 逐項 repr 對帳；0050 ＝ W["b50"]
 L6 閘（不過即停）：G1～G3 營量 v1（見 L2）；G4 營飆 W1 ＝ resultsYFallin；G5 sim_w1b_g 參數化 ＝ researchYFallin.sim_w1b；G6 0050 ＝ 整合件 summary；
    G7 V1／V1b 規則自檢（開盤持股條件、候選全買、金額式、本帳出資檔 ＝ relvol 前「空槽」檔）、現金 ≥ −1e−12、權益 ＞ 0、合併帳 Q＋備用金現金 ≥ 0
 必附：「看過結果的參數變體，只描述，不當改規則的依據；要採用須另行登錄、以前瞻驗證」「備用金規模看結果後才定」；
       早年附「早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）」與 NOTE3
輸出 backtest/resultsYLallin/：seeds.csv、cells.csv、cells_V1b.csv、daily.csv.gz、trades.csv.gz、daily_V1b_{主,早年}.csv.gz、trades_V1b_{主,早年}.csv.gz、summary.json、run.log
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchYFallin as YA                  # noqa: E402  （只 import 已驗證的迴圈與段統計；⛔ 不改）

TIME = "2026-10-18 23:10（台北）"
OUT = "backtest/resultsYLallin"
if os.environ.get("YLA_QUICK"):
    OUT = "/tmp/yla_quick"
N = 20
COST = R.COST
WORD = YA.WORD
WORD_Q = "備用金規模看結果後才定"
NOTE_EARLY = YA.NOTE_EARLY
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}
MNAME = {"YL": "營量 v1", "V1": "V1 營量同日全買·可超過20檔", "YFW1": "營飆 W1（重算）"}
sha, now_tpe, log_to = YA.sha, YA.now_tpe, YA.log_to


def relvol_order(keys, ci):
    """＝ researchYFallin.sim 的 pick 路徑：key NaN→−inf、依 −key 穩定排序。回 ci 的重排。"""
    key = keys[ci]; key = np.where(np.isnan(key), -np.inf, key)
    return [ci[i] for i in np.argsort(-key, kind="stable")]


# ═════════════ V1b 迴圈（researchYFallin.sim_w1b 參數化：n、pick）═════════════
def sim_w1b_g(W, DAYS, n, pick):
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
            sids, xs, gs, keys = day
            n0 = len(open_pos)
            if n0 < n:
                ci = [i for i in range(len(sids)) if sids[i] not in held]
                if ci:
                    if pick:
                        ci = relvol_order(keys, ci)
                    free = n - n0; slot = E[t - 1] / n; nx_ = 0
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


# ═════════════ V1 超額標記（L4；只標記，不影響金額）═════════════
def mark_excess_v1(o, DAYS):
    days = DAYS[0]; byt = {}
    for k, b in enumerate(o["buys"]):
        byt.setdefault(b[0], []).append(k)
    isx = [False] * len(o["buys"])
    for t, n0, free, nc, nb in o["dinfo"]:
        ks = byt.get(t, [])
        if not ks:
            continue
        sids, _, _, keys = days[t]
        pos = {s: i for i, s in enumerate(sids)}
        ci = [pos[o["buys"][k][1]] for k in ks]
        rank = relvol_order(keys, ci)
        exc = set(sids[i] for i in rank[free:])
        for k in ks:
            isx[k] = o["buys"][k][1] in exc
    o["buys"] = [b + (isx[k],) for k, b in enumerate(o["buys"])]
    return o


def shrink_days(o, x, y):
    by = {}
    for b in o["buys"]:
        if x <= b[0] <= y:
            by.setdefault(b[0], []).append(b)
    return int(sum(1 for t, bb in by.items() if min(b[2] for b in bb) < bb[0][3] / N * (1 - 1e-12)))


def seg_plain(W, o, sg, Q=None):
    """YL／V1／營飆 W1：researchYFallin.seg_metrics ＋ 超額欄。"""
    x, y = W["segp"][sg]
    W["Q"] = None
    row = YA.seg_metrics(W, o, sg)
    T = YA.trade_list(o)
    row["交易筆數"] = YA.cw_ret(T, x, y)[2]
    if len(o["buys"][0]) > 6:
        row["超額交易_投入報酬"], row["超額交易_平均"], row["超額交易_筆數"] = YA.cw_ret(T, x, y, True)
        row["本帳交易_投入報酬"], row["本帳交易_平均"], row["本帳交易_筆數"] = YA.cw_ret(T, x, y, False)
    nn = o["npos"][x:y + 1]
    row["同時最多超出20檔數"] = int(max(0, nn.max() - N)); row["超過20檔日占比"] = float(np.mean(nn > N))
    row["縮小日數"] = shrink_days(o, x, y)
    if Q is not None:
        eq, hv = o["equity"], o["hold_val"]
        cq, mq, _ = RR.win_metrics((eq + Q) / (1 + Q), o["first"], o["end"], x, y)
        yrs = (y - x + 1) / 245.0; mt = float(np.mean(eq[x:y + 1] + Q))
        row["加備用金年化"] = float(cq); row["加備用金回落"] = float(mq); row["加備用金比值"] = float(cq) / abs(float(mq))
        row["加備用金現金"] = float(1.0 - np.mean(hv[x:y + 1] / (eq[x:y + 1] + Q)))
        row["加備用金換手每年"] = float(sum(b[2] for b in o["buys"] if x <= b[0] <= y) / mt / yrs)
        row["加備用金成本每年"] = float(sum(s[4] for s in o["sells"] if x <= s[0] <= y) / mt / yrs)
    return row


def seg_v1b(W, o, sg, Q):
    x, y = W["segp"][sg]
    row = YA.seg_w1b(W, o, sg, Q)
    yrs = (y - x + 1) / 245.0
    tot = o["E"] + Q + o["RC"] + o["X"]; mt = float(np.mean(tot[x:y + 1]))
    row["合併換手每年"] = float(sum(b[2] for b in o["buys"] if x <= b[0] <= y) / mt / yrs)
    row["合併成本每年"] = float(sum(s[4] for s in o["sells"] if x <= s[0] <= y) / mt / yrs)
    row["超過20檔日占比"] = float(np.mean(o["npos"][x:y + 1] > N))
    row["超額動用峰值_段內（本帳起始＝1）"] = row.pop("超額動用最大（本帳起始＝1）")
    return row


def rule_v1(W, DAYS, o):
    days = DAYS[0]; bad = 0; byt = {}
    for b in o["buys"]:
        byt.setdefault(b[0], []).append(b)
    for t, n0, free, nc, nb in o["dinfo"]:
        bb = byt.get(t, [])
        sids = days[t][0]
        bad += int(n0 >= N) + int(nb not in (0, nc)) + int(len(bb) != nb)
        if bb:
            bad += int(max(b[2] for b in bb) > min(b[2] for b in bb) * (1 + 1e-12)) + int(bb[0][2] > bb[0][3] / N * (1 + 1e-12))
            bad += int(len(set(b[1] for b in bb)) != len(bb) or any(b[1] not in sids for b in bb))
    return bad


def rule_v1b(W, DAYS, o):
    days = DAYS[0]; bad = 0; byt = {}
    for b in o["buys"]:
        byt.setdefault(b[0], []).append(b)
    for t, n0, free, nc, nb, nx_ in o["dinfo"]:
        bb = byt.get(t, [])
        sids, _, _, keys = days[t]
        bad += int(n0 >= N) + int(len(bb) != nc) + int(nx_ < max(0, nc - free)) + int(sum(1 for b in bb if b[6]) != nx_)
        bad += int(any(b[6] and abs(b[2] - b[3] / N) > 1e-15 for b in bb))
        pos = {s: i for i, s in enumerate(sids)}
        rank = [sids[i] for i in relvol_order(keys, [pos[b[1]] for b in bb])]
        mine = [b[1] for b in bb if not b[6]]
        bad += int(mine != rank[:len(mine)] or any(not b[6] for b in bb if b[1] in rank[free:]))
    return bad


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}")
    Wm, gm = IG.main_world(log)
    We, ge = IG.early_world(log, a.procs)
    WW = {"主": Wm, "早年": We}
    for W in WW.values():
        W["DAYS_F"] = YA.build_days(W["SIG"][True], 120)
        W["DAYS_Y"] = YA.build_days(W["SIG"][False], 60, pick="relvol")
    gate = {}
    O = {}
    for wn, W in WW.items():
        O[(wn, "YL")] = YA.sim(W, W["DAYS_Y"], "v1", N, pick=True)
        O[(wn, "V1")] = mark_excess_v1(YA.sim(W, W["DAYS_Y"], "W1", N), W["DAYS_Y"])
        O[(wn, "YFW1")] = YA.sim(W, W["DAYS_F"], "W1", 10)
        O[(wn, "V1b")] = sim_w1b_g(W, W["DAYS_Y"], N, True)
        # G3 營量 v1 vs simulate_mtm
        oY = R.simulate_mtm(W["SIG"][False], "H60", N, np.random.default_rng(RR.P1_SEED0), W["closes"], W["opens"], W["NP"], return_equity=True,
                            log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"])
        gate[f"G3 {wn} 營量 v1 權益最大差 vs simulate_mtm"] = float(np.max(np.abs(oY["equity"] - O[(wn, "YL")]["equity"])))
        gate[f"G3 {wn} 營量 v1 持股市值最大差 vs simulate_mtm"] = float(np.max(np.abs(oY["hold_val"] - O[(wn, "YL")]["hold_val"])))
        gate[f"G3 {wn} 營量 v1 trades 差"] = int(oY["trades"] - len(O[(wn, "YL")]["buys"]))
        # G5 sim_w1b_g 參數化 ＝ researchYFallin.sim_w1b
        a_ = sim_w1b_g(W, W["DAYS_F"], 10, False); b_ = YA.sim_w1b(W, W["DAYS_F"])
        gate[f"G5 {wn} sim_w1b_g(n10,原序) ≠ YFallin.sim_w1b（陣列）"] = int(sum(not np.array_equal(a_[k], b_[k]) for k in ("E", "HV", "RC", "X", "U", "NX", "npos")))
        gate[f"G5 {wn} sim_w1b_g 買賣紀錄不同"] = int(a_["buys"] != b_["buys"] or a_["sells"] != b_["sells"] or a_["dinfo"] != b_["dinfo"])
        q_f = max(float(np.max(a_["U"])), float(max(0.0, -a_["rc_min"])))
        yfq = [r["Q（本帳起始＝1）"] for r in json.load(open("backtest/resultsYFallin/summary.json", encoding="utf-8"))["W1b"]["表"] if r["世界"] == wn][0]
        gate[f"G5 {wn} 營飆 W1b Q ≠ YFallin"] = int(repr(q_f) != repr(float(yfq)))
    # Q（⚠ 事後）
    QQ = {}
    for wn in WW:
        ob = O[(wn, "V1b")]
        q_lit = float(np.max(ob["U"])); need = float(max(0.0, -ob["rc_min"]))
        QQ[wn] = {"Q": max(q_lit, need), "Q_同時最多超額成本": q_lit, "Q_現金最大透支": need}
        gate[f"G7 {wn} V1b 合併帳備用金透支（Q＋現金 ＜ −1e−12 天數）"] = int((QQ[wn]["Q"] + ob["RC"] < -1e-12).sum())
        gate[f"G7 {wn} V1 規則不符（筆）"] = rule_v1(WW[wn], WW[wn]["DAYS_Y"], O[(wn, "V1")])
        gate[f"G7 {wn} V1b 規則不符（筆）"] = rule_v1b(WW[wn], WW[wn]["DAYS_Y"], ob)
        for m in ("YL", "V1", "YFW1"):
            o = O[(wn, m)]
            gate[f"G7 {wn} {m} 現金 ＜ −1e−12 或權益 ≤ 0"] = int(o["mincash"] < -1e-12 or float(np.min(o["equity"])) <= 0)
        gate[f"G7 {wn} V1b 本帳權益 ≤ 0"] = int(float(np.min(ob["E"])) <= 0)
        log(f"[V1b {wn}] Q ＝ {QQ[wn]['Q']:.6f}（同時最多超額成本 {q_lit:.6f}、現金路徑最大透支 {need:.6f}）｜買進 {len(ob['buys'])}｜超額買進 {sum(1 for b in ob['buys'] if b[6])}")
    # ── 列 ──
    SE = []
    for wn, W in WW.items():
        for m in ("YL", "V1", "YFW1"):
            o = O[(wn, m)]
            row = {"世界": wn, "帳": m, "eq_sha": sha(o["equity"]), "first": o["first"], "end": o["end"], "trades": len(o["buys"]),
                   "最低現金": o["mincash"], "最低權益": float(np.min(o["equity"]))}
            for sg in SEGS[wn]:
                for k, v in seg_plain(W, o, sg, QQ[wn]["Q"] if m == "YL" else None).items():
                    row[f"{sg}_{k}"] = v
            if wn == "主":
                c_, m_, _ = RR.win_metrics(o["equity"], o["first"], o["end"], *W["segp"]["主窗"])
                row["主窗_年化"], row["主窗_回落"] = c_, m_
            SE.append(row)
    SE = pd.DataFrame(SE)
    # ── 閘 G1／G2／G4／G6 ──
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
    ym = SE[(SE["世界"] == "主") & (SE["帳"] == "YL")].iloc[0]
    gate["G1 營量 v1 主 ≠ T1fix c13 t1 r0（eq_sha／主窗年化／回落）"] = int(ym["eq_sha"] != c13["eq_sha"]) + int(repr(float(ym["主窗_年化"])) != repr(float(c13["cagr"]))) \
        + int(repr(float(ym["主窗_回落"])) != repr(float(c13["mdd"])))
    ri = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    ra = pd.read_csv("backtest/resultsYFallin/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    KF = ("年化", "回落", "比值", "持股", "最大持股", "現金", "換手每年", "成本每年", "買進筆每年", "買進日每年", "超空槽日數", "單日最多買", "投入報酬", "每筆淨報酬平均")
    for wn in WW:
        y_ = SE[(SE["世界"] == wn) & (SE["帳"] == "YL")].iloc[0]
        yi = ri[(ri["世界"] == wn) & (ri["格"] == IG.YL) & (ri["r"] == 0)].iloc[0]
        gate[f"G2 {wn} 營量 v1 eq_sha ≠ 整合件"] = int(y_["eq_sha"] != yi["eq_sha"])
        gate[f"G2 {wn} 營量 v1 段值 ≠ 整合件（項）"] = int(sum(repr(float(y_[f"{sg}_{k}"])) != repr(float(yi[f"{sg}_{k}"])) for sg in SEGS[wn] for k in ("年化", "回落", "持股", "現金")))
        ya = ra[(ra["世界"] == wn) & (ra["帳"] == "YL")].iloc[0]
        gate[f"G2 {wn} 營量 v1 ≠ YFallin YL（eq_sha＋段值項）"] = int(y_["eq_sha"] != ya["eq_sha"]) + int(sum(
            repr(float(y_[f"{sg}_{k}"])) != repr(float(ya[f"{sg}_{k}"])) for sg in SEGS[wn] for k in KF))
        f_ = SE[(SE["世界"] == wn) & (SE["帳"] == "YFW1")].iloc[0]
        fa = ra[(ra["世界"] == wn) & (ra["帳"] == "W1")].iloc[0]
        gate[f"G4 {wn} 營飆 W1 ≠ YFallin W1（eq_sha＋trades＋段值項）"] = int(f_["eq_sha"] != fa["eq_sha"]) + int(int(f_["trades"]) != int(fa["trades"])) + int(sum(
            repr(float(f_[f"{sg}_{k}"])) != repr(float(fa[f"{sg}_{k}"])) for sg in SEGS[wn] for k in KF))
    sm = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
    gate["G6 0050 各段 ≠ 整合件（項）"] = int(sum(repr(float(WW[wn]["b50"][sg][k])) != repr(float(sm[wn][sg][k])) for wn in WW for sg in SEGS[wn] for k in ("cagr", "mdd")))
    log(f"[閘] {json.dumps(gate, ensure_ascii=False)}")
    S = {"讀法寫死": TIME, "性質": "描述、不計 N、看過結果才提的變體、不改規則", "必附": [WORD, WORD_Q], "早年註": NOTE_EARLY, "世界閘": {**gm, **ge}, "閘": gate, "Q": QQ}
    hard = [k for k, v in gate.items() if (v > 0 if "最大差" in k else v != 0)]
    if hard:
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit(f"⛔ 閘不過 {hard}")
    SE.to_csv(os.path.join(OUT, "seeds.csv"), index=False, float_format="%.17g")
    # ── 逐日／逐筆 ──
    DL, TL = [], []
    for (wn, m), o in O.items():
        if m == "V1b":
            continue
        cal = WW[wn]["cal"]
        DL.append(pd.DataFrame({"世界": wn, "帳": m, "t": np.arange(len(o["equity"])),
                                "日期": [cal[t].strftime("%Y-%m-%d") if t < len(cal) else "" for t in range(len(o["equity"]))],
                                "權益": o["equity"], "持股市值": o["hold_val"], "持股": o["npos"]}))
        for b in o["buys"]:
            TL.append({"世界": wn, "帳": m, "side": "buy", "t": b[0], "sid": b[1], "amt": b[2], "eq_prev": b[3], "px": b[4], "xpos": b[5],
                       "超額": int(b[6]) if len(b) > 6 else 0})
        for s_ in o["sells"]:
            TL.append({"世界": wn, "帳": m, "side": "sell", "t": s_[0], "sid": s_[1], "amt": s_[2], "amt_out": s_[3], "cost": s_[4], "eq_prev": s_[5]})
    pd.concat(DL, ignore_index=True).to_csv(os.path.join(OUT, "daily.csv.gz"), index=False, float_format="%.17g")
    pd.DataFrame(TL).to_csv(os.path.join(OUT, "trades.csv.gz"), index=False, float_format="%.17g")
    for wn, W in WW.items():
        ob = O[(wn, "V1b")]
        pd.DataFrame({"世界": wn, "t": np.arange(W["NP"]), "本帳": ob["E"], "本帳持股市值": ob["HV"], "備用金現金": ob["RC"], "超額市值": ob["X"],
                      "超額成本": ob["U"], "超額檔": ob["NX"], "總持股": ob["npos"]}).to_csv(os.path.join(OUT, f"daily_V1b_{wn}.csv.gz"), index=False, float_format="%.17g")
        pd.DataFrame([{"side": "buy", "t": z[0], "sid": z[1], "amt": z[2], "eq_prev": z[3], "px": z[4], "xpos": z[5], "超額": int(z[6])} for z in ob["buys"]] +
                     [{"side": "sell", "t": z[0], "sid": z[1], "amt": z[2], "amt_out": z[3], "cost": z[4], "eq_prev": z[5], "超額": int(z[6])} for z in ob["sells"]]
                     ).to_csv(os.path.join(OUT, f"trades_V1b_{wn}.csv.gz"), index=False, float_format="%.17g")
    # ── 彙總 ──
    YFS = pd.DataFrame(json.load(open("backtest/resultsYFallin/summary.json", encoding="utf-8"))["表"])
    MET = ["年化", "回落", "比值", "持股", "最大持股", "現金", "換手每年", "成本每年", "買進日每年", "超空槽日數", "單日最多買", "同時最多超出20檔數", "超過20檔日占比",
           "縮小日數", "交易筆數", "投入報酬", "每筆淨報酬平均", "超額交易_筆數", "超額交易_平均", "本帳交易_筆數", "本帳交易_平均",
           "加備用金年化", "加備用金回落", "加備用金比值", "加備用金現金", "加備用金換手每年", "加備用金成本每年"]
    C = []
    for wn, W in WW.items():
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]; b = W["b50"][sg]
            for m in ("YL", "V1", "YFW1"):
                g = SE[(SE["世界"] == wn) & (SE["帳"] == m)].iloc[0]
                row = {"世界": wn, "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}", "帳": MNAME[m]}
                for k in MET:
                    row[k] = g.get(f"{sg}_{k}", np.nan)
                row["對0050"] = IG.label(row["年化"], row["回落"], b)
                row.update({"0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])})
                C.append(row)
            f = YFS[(YFS["世界"] == wn) & (YFS["段"] == sg) & (YFS["帳"] == "營飆 v1（抽籤）")].iloc[0]
            row = {"世界": wn, "段": sg, "窗": f["窗"], "帳": "營飆 v1（200 顆中位，讀 resultsYFallin）"}
            for k in ("年化", "回落", "比值", "持股", "最大持股", "現金", "換手每年", "成本每年", "買進日每年", "投入報酬", "每筆淨報酬平均", "年化_p10", "年化_p90"):
                row[k] = f[k]
            row["對0050"] = f["對0050"]; row.update({"0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])})
            gate[f"G8 {wn} {sg} 營飆 v1 讀取 0050 欄 ≠ 本世界（項）"] = int(repr(float(f["0050年化"])) != repr(float(b["cagr"])) or repr(float(f["0050回落"])) != repr(float(b["mdd"])))
            C.append(row)
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    CB = []
    for wn, W in WW.items():
        Q = QQ[wn]["Q"]; ob = O[(wn, "V1b")]
        for sg in SEGS[wn]:
            b = W["b50"][sg]
            y_ = SE[(SE["世界"] == wn) & (SE["帳"] == "YL")].iloc[0]
            row = {"世界": wn, "段": sg, "Q（本帳起始＝1）": Q, "Q_同時最多超額成本": QQ[wn]["Q_同時最多超額成本"], "Q_現金最大透支": QQ[wn]["Q_現金最大透支"],
                   **seg_v1b(W, ob, sg, Q)}
            row["合併對0050"] = IG.label(row["合併年化"], row["合併回落"], b)
            for k in ("加備用金年化", "加備用金回落", "加備用金比值", "加備用金現金", "加備用金換手每年", "加備用金成本每年", "年化", "回落", "投入報酬", "每筆淨報酬平均", "持股"):
                row[f"YL_{k}"] = float(y_[f"{sg}_{k}"])
            row["YL_加備用金對0050"] = IG.label(row["YL_加備用金年化"], row["YL_加備用金回落"], b)
            row.update({"0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])})
            CB.append(row)
    CB = pd.DataFrame(CB)
    CB.to_csv(os.path.join(OUT, "cells_V1b.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S["閘"] = gate
    S["表"] = C.to_dict("records"); S["V1b"] = {"註": [WORD_Q, "使用者已說閒置放 0050 不用 ⇒ 只做 (a)(c)", "V1b 本帳出資順序 ＝ relvol 遞減（營量 v1 挑法）"],
                                             "表": CB.to_dict("records")}
    S["完成（台北）"] = now_tpe()
    hard = [k for k, v in gate.items() if (v > 0 if "最大差" in k else v != 0)]
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    if hard:
        raise SystemExit(f"⛔ 閘不過 {hard}")
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60)
    log("\n" + C.drop(columns=["窗"]).T.to_string())
    log("\n[V1b]\n" + CB.T.to_string())
    log(f"[完] {now_tpe()}（台北）")


if __name__ == "__main__":
    main()
