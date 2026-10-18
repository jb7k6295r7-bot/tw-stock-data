# -*- coding: utf-8 -*-
"""營量 v1 遇營飆 v1 同檔「跳過不買」（使用者問：「如果兩個同時都有出現訊號，營飆有買營量就跳過不買會怎樣？」）——回測線計算子代理。
⭐ 描述、⛔ 不計 N、看過結果才提的變體、⛔ 不改營量 v1／營飆 v1 規則。⛔ 不改任何既有 .py／結果夾（research11.py、rerun17.py、researchYFallin.py 一字不動）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLnoDup [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLnoDup_check

═══ 讀法（寫死於 2026-10-18 21:52（台北），在算任何本件數字之前；⚠ 本線看過：營量 v1／營飆 v1 各段年化與回落、resultsYLvsYF（持股重疊、
    日報酬相關）、resultsYLmerge（各半·年調）、resultsYFallin；⛔ 沒看過任何「營量跳過營飆同檔」帳的數字）═══
 N1 世界、訊號、引擎 ＝ researchYFallin（主世界 IG.main_world、早年世界 IG.early_world；DAYS_F ＝ SIG[閘]·H120、DAYS_Y ＝ SIG[無閘]·H60·relvol）
    營飆 v1 ＝ FA.sim(DAYS_F, "v1", 10, rng ＝ default_rng(rerun17.P10_SEED0＋r))；營量 v1 ＝ FA.sim(DAYS_Y, "v1", 20, pick＝relvol)
    ⭐ 本檔不寫新的逐日迴圈：只把營量「第 t 天的候選名單」先剔掉排除檔（filt），再交給同一個 FA.sim（import、不複製）
    ⇒ 引擎模式：排除集合空 ⇒ filt 回原表 ⇒ 逐日權益須 ＝ research11.simulate_mtm 定版（營飆 200 顆 eq_sha ＝ resultsYF_N N10；營量 ＝ resultsYL_integrate）
 N2 變體（寫死；⛔ 不再加）
    原版：兩本帳各自獨立（排除集合空）
    X1 同日跳過：營量第 t 天的候選剔除「營飆第 t 天買進的股票」；剔除後照 relvol 遞減遞補（空位給下一名候選，若有）
    X2 持有中也跳過：營量第 t 天的候選剔除「營飆第 t 天持有中或當天買進的股票」＝ 營飆交易 tb ≤ t ＜ ts
       （ts ＝ 引擎出場日；出場日當天引擎先結算再買進，視為已不持有，＝ researchYLvsYF.book 口徑）
    共同：只影響營量的【買進】；營量已持有的股不強迫賣；營飆不受營量影響（營飆帳 ＝ 原版逐位元相同）
 N3 每顆種子 r ＝ 0～199：營飆 v1 r 一條；X1／X2 的營量隨營飆抽籤變 ⇒ 報 200 顆中位與 p10／p90；原版營量與 r 無關（單值）
 N4 段 ＝ 營飆 v1 原報告：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（主世界一條權益切段讀）；早年 2005-02-01～2014-12-31（早年世界）
 N5 每段報：
    營量本帳：年化、回落（rerun17.win_metrics）、比值 ＝ 年化 ÷ |回落|、對 0050 ＝ researchYL_integrate.label；平均持股
    合併帳「各半·年調」＝ researchp17.compose(營飆, 營量, w＝0.5, 每年第一個交易日調回（窗首不算）, 換手×0.585%)（＝ researchYLmerge／researchYfSlots2 同路徑）：年化、回落、比值
    兩本帳逐日持股重疊：ⓐ 營飆持股中也在營量、ⓑ 營量持股中也在營飆（researchYLvsYF.seg_overlap）；
      合併帳相異檔數平均 ＝ 營飆持股＋營量持股−同檔（逐日平均，＝ researchYLmerge 各半「持股」聯集）；兩本帳日報酬相關（段內 corrcoef）
    替補：每個「排除檔出現在營量當天候選」的日子，用營量變體當天的實際狀態（出場後持股、現金）重算「若不排除會買的名單」B0；實買 B（＝ 剔除後依 relvol 前 K 名）
      被跳過 ＝ B0 − B；替補 ＝ B − B0；報 筆數、替補實際淨報酬平均、被跳過那檔在營量規則下的假想淨報酬平均
      （同日開盤進、xpos_H60／g_H60、停止交易強制出場同引擎、扣 COST）；交易歸段 ＝ 買進日所在段
    中位與 p10／p90（200 顆）；比值、對 0050 用中位；另報成對差（X − 原版，同顆）中位與 p10／p90
 N6 閘（不過即停）：E1 引擎模式（營飆 200 顆 eq_sha ＝ resultsYF_N；營量原版 eq_sha ＝ 整合件；營飆 r0／營量 直接呼叫 research11.simulate_mtm 逐日權益最大差 ＝ 0；
      空排除集合走 filt 後 ＝ 原表 ＝ simulate_mtm）；E2 營飆各段年化／回落 ＝ resultsYF_N、營量原版各段 ＝ 整合件（repr）；
    E3 原版 ⓐⓑ／日報酬相關 ＝ resultsYLvsYF seeds（repr）；E4 原版 各半·年調 年化／回落／持股 ＝ resultsYLmerge seeds（repr）；E5 0050 ＝ 整合件；
    E6 X1／X2 規則不符筆數 ＝ 0（營量每筆買進都不在當天排除集合）、遞補規則不符 ＝ 0（B ＝ 剔除後 relvol 前 K 名；被跳過全屬排除檔）；E7 現金 ≥ −1e−12、權益 ＞ 0
 必附：「看過結果的參數變體，只描述，不當改規則的依據；要採用須另行登錄、以前瞻驗證」；早年附「早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）」與 NOTE3
輸出 backtest/resultsYLnoDup/：seeds.csv.gz、cells.csv、sample_trades.csv.gz、sample_daily.csv.gz（r＝0～2 給查核）、summary.json、REPORT.md、run.log
"""
from __future__ import annotations

import argparse
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
from backtest import researchp17 as P17                     # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchYLvsYF as YV                   # noqa: E402
from backtest import researchYFallin as FA                  # noqa: E402

TIME = "2026-10-18 21:52（台北）"
OUT = "backtest/resultsYLnoDup"
NSEED = 200
SAVE_R = (0, 1, 2)
if os.environ.get("YND_QUICK"):                              # 煙霧測試（不是交件）
    NSEED, OUT = 3, "/tmp/ynd_quick"
COST = R.COST
MCOST = 0.00585                                             # compose 換手成本（＝ researchYLmerge.MCOST）
VARS = ("原版", "X1", "X2")
DESC = {"原版": "兩本帳各自獨立", "X1": "同日跳過：營飆當天買的，營量當天不買、空位給 relvol 下一名",
        "X2": "持有中也跳過：營飆持有中或當天買的，營量都不買、空位給下一名"}
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}
REPSEG = (("主", "探索"), ("主", "確認"), ("早年", "早年"))
WORD = "看過結果的參數變體，只描述，不當改規則的依據；要採用須另行登錄、以前瞻驗證"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；早年照營飆 v1 早年既有版面（上市＋上櫃 eotc_f65bb03e11、R8 截斷）", IG.NOTE3]
_W: dict = {}


# ═════════════ 排除與名單 ═════════════
def filt(DAYS, excl):
    """營量訊號表剔除排除檔：excl ＝ {t: set(sid)}；其餘逐字保留（first／last 不動）。"""
    days, first, last = DAYS
    nd = {}
    for t, day in days.items():
        ex = excl.get(t)
        if ex and any(s in ex for s in day[0]):
            sids, xs, gs, keys = day
            keep = [i for i, s in enumerate(sids) if s not in ex]
            nd[t] = ([sids[i] for i in keep], [xs[i] for i in keep], [gs[i] for i in keep], keys[np.asarray(keep, dtype=np.int64)])
        else:
            nd[t] = day
    return nd, first, last


def trades(o):
    """FA.sim 結果 ⇒ [(sid, tb, ts, amt, px_in, 淨報酬)]、audit（給 researchYLvsYF.book）。同日先賣後買（＝ 迴圈順序）。"""
    ev = [(b[0], 1, b) for b in o["buys"]] + [(s[0], 0, s) for s in o["sells"]]
    op_, T, au = {}, [], []
    for t, side, z in sorted(ev, key=lambda q: (q[0], q[1])):
        if side == 1:
            if z[1] in op_:
                raise SystemExit(f"⛔ {z[1]} 重複買進")
            op_[z[1]] = z
            au.append({"side": "buy", "t": t, "sid": z[1], "amt": z[2], "px": z[4], "equity_prev": z[3]})
        else:
            b = op_.pop(z[1])
            T.append((z[1], b[0], t, b[2], b[4], z[3] / b[2] - 1.0 - COST))
            au.append({"side": "sell", "t": t, "sid": z[1], "amt": z[2], "px": b[4] * z[3] / b[2], "equity_prev": z[5]})
    if op_:
        raise SystemExit(f"⛔ 模擬尾仍有 {len(op_)} 筆未賣")
    return T, au


def excl_sets(oF, days_keys, mode):
    """X1：營飆第 t 天買進；X2：營飆 tb ≤ t ＜ ts。只建營量有訊號的日子。"""
    ex = {}
    if mode == "X1":
        for b in oF["buys"]:
            if b[0] in days_keys:
                ex.setdefault(b[0], set()).add(b[1])
    elif mode == "X2":
        TF, _ = trades(oF)
        for s, tb, ts, *_ in TF:
            for t in range(tb, ts):
                if t in days_keys:
                    ex.setdefault(t, set()).add(s)
    return ex


def rank(sids, keys, held):
    """＝ FA.sim 的 relvol 排序：未持有者、relvol 遞減、NaN 最後、同值保原序。"""
    ci = [i for i in range(len(sids)) if sids[i] not in held]
    if not ci:
        return []
    k = keys[np.asarray(ci, dtype=np.int64)]; k = np.where(np.isnan(k), -np.inf, k)
    return [sids[ci[i]] for i in np.argsort(-k, kind="stable")]


def hypo_net(W, s, t, x, g):
    """被跳過那檔在營量規則下的假想淨報酬（＝ FA.sim 的 _buy／強制出場／結算式）。"""
    cl, op = W["closes"], W["opens"]
    ep = float(op[s][t])
    if not np.isfinite(ep) or ep <= 0:
        ep = float(cl[s][t])
    gross = float(g)
    L = W["SF"].get(s)
    if L is not None and L >= t and L + 1 < x:
        gross = float(cl[s][L]) / ep - 1.0
    return gross - COST


def subst(W, DAYS0, DAYSX, oY, TY, excl):
    """替補分析（N5）。回 ([(t, sid, 假想淨報酬)] 被跳過, [(t, sid, 實際淨報酬)] 替補, 遞補規則不符數)。"""
    days0, daysX = DAYS0[0], DAYSX[0]
    eq, hv = oY["equity"], oY["hold_val"]
    bt = {}
    for b in oY["buys"]:
        bt.setdefault(b[0], []).append(b)
    net_of = {(s, tb): r for s, tb, ts, amt, px, r in TY}
    q = sorted(t for t in excl if t in days0 and any(s in excl[t] for s in days0[t][0]))
    # 持股掃描：held(t) ＝ {tb ＜ t ＜ ts}
    adds = sorted((tb + 1, s) for s, tb, ts, *_ in TY); rems = sorted((ts, s) for s, tb, ts, *_ in TY)
    ia = ir = 0; cnt = {}
    SK, RP, bad = [], [], 0
    for t in q:
        while ia < len(adds) and adds[ia][0] <= t:
            cnt[adds[ia][1]] = cnt.get(adds[ia][1], 0) + 1; ia += 1
        while ir < len(rems) and rems[ir][0] <= t:
            cnt[rems[ir][1]] -= 1; ir += 1
        held = {s for s, c in cnt.items() if c > 0}
        sids, xs, gs, keys = days0[t]
        ex = excl[t]
        free = 20 - len(held)
        B = [b[1] for b in bt.get(t, [])]
        Lu = rank(sids, keys, held)
        Lf = rank(daysX[t][0], daysX[t][3], held)
        if free <= 0:
            K = 0
        elif len(B) < min(free, len(Lf)):
            K = len(B)                                       # 現金不足（金額與挑哪檔無關）
        elif len(B) == free:
            K = free
        else:                                                # len(B) ＝ len(Lf) ＜ free：以當天現金重算可買檔數
            c = float(eq[t] - hv[t] + sum(b[2] for b in bt.get(t, []))); slot = eq[t - 1] / 20; K = 0
            while K < free:
                a = min(slot, c)
                if a <= 1e-9:
                    break
                c -= a; K += 1
            K = max(K, len(B))
        B0 = Lu[:K]
        bad += int(B != Lf[:len(B)]) + int(len(B) != min(K, len(Lf)))
        sk = [s for s in B0 if s not in B]; rp = [s for s in B if s not in B0]
        bad += int(any(s not in ex for s in sk)) + int(len(rp) > len(sk))
        pos = {s: i for i, s in enumerate(sids)}
        for s in sk:
            i = pos[s]
            SK.append((t, s, hypo_net(W, s, t, xs[i], gs[i])))
        for s in rp:
            RP.append((t, s, net_of[(s, t)]))
    return SK, RP, bad


# ═════════════ 每顆種子 ═════════════
def job(r_args):
    wn, r = r_args
    W = _W[wn]
    oF = FA.sim(W, W["DAYS_F"], "v1", 10, rng=np.random.default_rng(RR.P10_SEED0 + r))
    TF, auF = trades(oF)
    F = YV.book(W, oF, auF)
    eF = F[0]; n = len(eF); w0, w1 = W["w0"], W["w1"]
    row = {"世界": wn, "r": r, "營飆_eq_sha": FA.sha(eF), "營飆_trades": len(oF["buys"])}
    for sg in SEGS[wn]:
        x, y = W["segp"][sg]
        c_, m_, _ = RR.win_metrics(eF, oF["first"], oF["end"], x, y)
        row[f"{sg}_營飆_年化"] = c_; row[f"{sg}_營飆_回落"] = m_
    keys = set(W["DAYS_Y"][0])
    extra = {} if r in SAVE_R else None
    if extra is not None:
        extra["營飆"] = (oF, None)
    for v in VARS:
        excl = {} if v == "原版" else excl_sets(oF, keys, v)
        DX = filt(W["DAYS_Y"], excl)
        oY = FA.sim(W, DX, "v1", 20, pick=True)
        TY, auY = trades(oY)
        Y = YV.book(W, oY, auY)
        eY = Y[0]
        row[f"{v}_eq_sha"] = FA.sha(eY); row[f"{v}_trades"] = len(oY["buys"])
        row[f"{v}_最低現金"] = float(oY["mincash"]); row[f"{v}_最低權益"] = float(np.min(eY))
        row[f"{v}_規則不符"] = int(sum(1 for b in oY["buys"] if b[1] in excl.get(b[0], ())))
        if v == "原版":                                      # 描述：原版營量買進中，落在 X1／X2 排除集合的筆數
            ex1, ex2 = excl_sets(oF, keys, "X1"), excl_sets(oF, keys, "X2")
            for sg in SEGS[wn]:
                x, y = W["segp"][sg]
                row[f"{sg}_原版_同日營飆也買筆"] = int(sum(1 for b in oY["buys"] if x <= b[0] <= y and b[1] in ex1.get(b[0], ())))
                row[f"{sg}_原版_營飆持有中買筆"] = int(sum(1 for b in oY["buys"] if x <= b[0] <= y and b[1] in ex2.get(b[0], ())))
        inter, ovA = YV.overlap_series(F, Y)
        uni = F[2] + Y[2] - inter
        EA, EB = eF[w0:w1 + 1], eY[w0:w1 + 1]
        Vw, turn, cst = P17.compose(EA, EB, np.full(len(EA), 0.5), W["REBAL"], cost=MCOST)
        V = np.full(n, np.nan); V[w0:w1 + 1] = Vw
        if v != "原版":
            SK, RP, bad = subst(W, W["DAYS_Y"], DX, oY, TY, excl)
        else:
            SK, RP, bad = [], [], 0
        row[f"{v}_遞補不符"] = bad
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]
            c_, m_, _ = RR.win_metrics(eY, oY["first"], oY["end"], x, y)
            row[f"{sg}_{v}_年化"] = c_; row[f"{sg}_{v}_回落"] = m_
            row[f"{sg}_{v}_持股"] = float(np.mean(oY["npos"][x:y + 1]))
            row[f"{sg}_{v}_買進筆"] = int(sum(1 for b in oY["buys"] if x <= b[0] <= y))
            cc, mc, _ = RR.win_metrics(V, w0, w1 + 1, x, y)
            row[f"{sg}_{v}_合併年化"] = cc; row[f"{sg}_{v}_合併回落"] = mc
            a, b, am, _, _ = YV.seg_overlap(F, Y, inter, ovA, x, y)
            row[f"{sg}_{v}_F中也在Y"] = a; row[f"{sg}_{v}_Y中也在F"] = b
            row[f"{sg}_{v}_相異檔數"] = float(np.mean(uni[x:y + 1]))
            row[f"{sg}_{v}_日報酬相關"] = float(np.corrcoef(YV.daily_r(eF, x, y), YV.daily_r(eY, x, y))[0, 1])
            sk = [z[2] for z in SK if x <= z[0] <= y]; rp = [z[2] for z in RP if x <= z[0] <= y]
            row[f"{sg}_{v}_被跳過筆"] = len(sk); row[f"{sg}_{v}_替補筆"] = len(rp)
            row[f"{sg}_{v}_被跳過假想平均"] = float(np.mean(sk)) if sk else np.nan
            row[f"{sg}_{v}_替補平均"] = float(np.mean(rp)) if rp else np.nan
            row[f"{sg}_{v}_被跳過假想和"] = float(np.sum(sk)); row[f"{sg}_{v}_替補和"] = float(np.sum(rp))
        if extra is not None:
            extra[v] = (oY, V, SK, RP)
    return row, extra


def prep(W, log):
    W["DAYS_F"] = FA.build_days(W["SIG"][True], 120)
    W["DAYS_Y"] = FA.build_days(W["SIG"][False], 60, pick="relvol")
    cal = W["cal"]; w0, w1 = W["w0"], W["w1"]
    W["REBAL"] = np.r_[False, pd.DatetimeIndex(cal[w0 + 1:w1 + 1]).year != pd.DatetimeIndex(cal[w0:w1]).year]
    log(f"[{W['name']}] 窗 {cal[w0].date()}～{cal[w1].date()}｜年調日 {int(W['REBAL'].sum())}｜營量訊號日 {len(W['DAYS_Y'][0])}｜營飆訊號日 {len(W['DAYS_F'][0])}")


def engine_gate(W):
    """E1 引擎模式：直接呼叫 research11.simulate_mtm（營飆 r0、營量），與 FA.sim（營量走 filt 空排除）逐日權益最大差。"""
    g = {}
    wn = W["name"]
    oF = R.simulate_mtm(W["SIG"][True], "H120", 10, np.random.default_rng(RR.P10_SEED0), W["closes"], W["opens"], W["NP"], return_equity=True, stop_force=W["SF"])
    mF = FA.sim(W, W["DAYS_F"], "v1", 10, rng=np.random.default_rng(RR.P10_SEED0))
    oY = R.simulate_mtm(W["SIG"][False], "H60", 20, np.random.default_rng(RR.P1_SEED0), W["closes"], W["opens"], W["NP"], return_equity=True,
                        log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"])
    D0 = filt(W["DAYS_Y"], {})
    D1 = filt(W["DAYS_Y"], {t: {"__無此股__"} for t in W["DAYS_Y"][0]})
    mY0 = FA.sim(W, D0, "v1", 20, pick=True); mY1 = FA.sim(W, D1, "v1", 20, pick=True)
    g[f"E1 {wn} 營飆 r0 權益最大差 vs simulate_mtm"] = float(np.max(np.abs(oF["equity"] - mF["equity"])))
    g[f"E1 {wn} 營飆 r0 trades 差"] = int(oF["trades"] - len(mF["buys"]))
    g[f"E1 {wn} 營量 空排除 filt 權益最大差 vs simulate_mtm"] = float(max(np.max(np.abs(oY["equity"] - mY0["equity"])), np.max(np.abs(oY["equity"] - mY1["equity"]))))
    g[f"E1 {wn} 營量 trades 差"] = int(abs(oY["trades"] - len(mY0["buys"])) + abs(oY["trades"] - len(mY1["buys"])))
    return g


# ═════════════ 主程式 ═════════════
def q3(v):
    v = pd.Series(v, dtype=float).dropna()
    if not len(v):
        return np.nan, np.nan, np.nan
    return float(v.median()), float(v.quantile(.1)), float(v.quantile(.9))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = YV.log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {YV.now_tpe()}（台北）｜讀法寫死 {TIME}｜種子 {NSEED}")
    Wm, gm = IG.main_world(log)
    We, ge = IG.early_world(log, a.procs)
    for W in (Wm, We):
        prep(W, log)
    _W["主"], _W["早年"] = Wm, We
    gate = {}
    for W in (Wm, We):
        gate.update(engine_gate(W))
    log(f"[E1 直呼] {gate}")
    T0 = time.time()
    with Pool(a.procs) as pool:
        RES = pool.map(job, [(wn, r) for wn in ("主", "早年") for r in range(NSEED)], chunksize=4)
    log(f"[迴圈] {len(RES)} 顆｜{time.time() - T0:.0f}s")
    SE = pd.DataFrame([z[0] for z in RES])
    EX = {(z[0]["世界"], z[0]["r"]): z[1] for z in RES if z[1] is not None}
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # ═══ 閘 ═══
    rf = pd.read_csv("backtest/resultsYF_N/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    ri = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    vs = pd.read_csv("backtest/resultsYLvsYF/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    mg = pd.read_csv("backtest/resultsYLmerge/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    rp = lambda v: repr(float(v))                            # noqa: E731
    for wn in ("主", "早年"):
        A = SE[SE["世界"] == wn].set_index("r")
        B = rf[(rf["世界"] == wn) & (rf["N"] == 10)].set_index("r")
        gate[f"E1 {wn} 營飆 eq_sha ≠ YF_N（顆／{len(A)}）"] = int(sum(A.loc[r, "營飆_eq_sha"] != B.loc[r, "eq_sha"] for r in A.index))
        gate[f"E2 {wn} 營飆 各段年化／回落 ≠ YF_N（顆）"] = int(sum(any(rp(A.loc[r, f"{sg}_營飆_{k}"]) != rp(B.loc[r, f"{sg}_{k}"]) for sg in SEGS[wn] for k in ("年化", "回落"))
                                                       for r in A.index))
        yi = ri[(ri["世界"] == wn) & (ri["格"] == IG.YL) & (ri["r"] == 0)].iloc[0]
        gate[f"E1 {wn} 營量原版 eq_sha ≠ 整合件（顆）"] = int((A["原版_eq_sha"] != yi["eq_sha"]).sum())
        gate[f"E2 {wn} 營量原版 各段 ≠ 整合件（項）"] = int(sum(rp(A[f"{sg}_原版_{k}"].iloc[0]) != rp(yi[f"{sg}_{k}"]) for sg in SEGS[wn] for k in ("年化", "回落", "持股")))
        V_ = vs[vs["世界"] == wn].set_index("r")
        gate[f"E3 {wn} 原版 ⓐⓑ／日報酬相關 ≠ resultsYLvsYF（項）"] = int(sum(
            rp(A.loc[r, f"{sg}_原版_{k}"]) != rp(V_.loc[r, f"{sg}_{k}"]) for r in A.index for sg in SEGS[wn] for k in ("F中也在Y", "Y中也在F", "日報酬相關")))
        M_ = mg[(mg["世界"] == wn) & (mg["變體"] == "各半·年調")].set_index("r")
        gate[f"E4 {wn} 原版 各半·年調 年化／回落／相異檔數 ≠ resultsYLmerge（項）"] = int(sum(
            rp(A.loc[r, f"{sg}_原版_{k}"]) != rp(M_.loc[r, f"{sg}_{kk}"]) for r in A.index for sg in SEGS[wn]
            for k, kk in (("合併年化", "年化"), ("合併回落", "回落"), ("相異檔數", "持股"))))
        for v in ("X1", "X2"):
            gate[f"E6 {wn} {v} 規則不符（筆）"] = int(A[f"{v}_規則不符"].sum())
            gate[f"E6 {wn} {v} 遞補規則不符（日）"] = int(A[f"{v}_遞補不符"].sum())
        gate[f"E7 {wn} 現金 ＜ −1e−12 或權益 ≤ 0（帳）"] = int(sum(((A[f"{v}_最低現金"] < -1e-12) | (A[f"{v}_最低權益"] <= 0)).sum() for v in VARS))
    sm = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
    gate["E5 0050 各段 ≠ 整合件（項）"] = int(sum(rp(_W[wn]["b50"][sg][k]) != rp(sm[wn][sg][k]) for wn in ("主", "早年") for sg in SEGS[wn] for k in ("cagr", "mdd")))
    log(f"[閘] {gate}")
    S = {"讀法寫死": TIME, "性質": "描述、不計 N、看過結果才提的變體、不改規則", "必附": WORD, "早年註": NOTE_EARLY, "變體": DESC, "世界閘": {**gm, **ge}, "閘": gate}
    hard = [k for k, v in gate.items() if (v > 0 if "最大差" in k else v != 0)]
    if hard and NSEED == 200:
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit(f"⛔ 閘不過 {hard}")
    # ═══ 抽樣（查核用）═══
    DL, TL = [], []
    for (wn, r), ex in EX.items():
        cal = _W[wn]["cal"]
        for v, z in ex.items():
            o = z[0]
            d = {"世界": wn, "r": r, "帳": v, "t": np.arange(len(o["equity"])), "權益": o["equity"], "持股市值": o["hold_val"], "持股": o["npos"]}
            if v != "營飆":
                d["合併"] = z[1]
            DL.append(pd.DataFrame(d))
            for b in o["buys"]:
                TL.append({"世界": wn, "r": r, "帳": v, "side": "buy", "t": b[0], "日期": cal[b[0]].strftime("%Y-%m-%d"), "sid": b[1], "amt": b[2], "eq_prev": b[3], "px": b[4], "xpos": b[5]})
            for s_ in o["sells"]:
                TL.append({"世界": wn, "r": r, "帳": v, "side": "sell", "t": s_[0], "日期": (cal[s_[0]].strftime("%Y-%m-%d") if s_[0] < len(cal) else ""), "sid": s_[1], "amt": s_[2], "amt_out": s_[3], "cost": s_[4]})
            if v in ("X1", "X2"):
                for t, s, nr in z[2]:
                    TL.append({"世界": wn, "r": r, "帳": v, "side": "skip", "t": t, "日期": cal[t].strftime("%Y-%m-%d"), "sid": s, "net": nr})
                for t, s, nr in z[3]:
                    TL.append({"世界": wn, "r": r, "帳": v, "side": "repl", "t": t, "日期": cal[t].strftime("%Y-%m-%d"), "sid": s, "net": nr})
    pd.concat(DL, ignore_index=True).to_csv(os.path.join(OUT, "sample_daily.csv.gz"), index=False, float_format="%.17g")
    pd.DataFrame(TL).to_csv(os.path.join(OUT, "sample_trades.csv.gz"), index=False, float_format="%.17g")
    # ═══ 彙總 ═══
    KS = ("年化", "回落", "持股", "買進筆", "合併年化", "合併回落", "F中也在Y", "Y中也在F", "相異檔數", "日報酬相關",
          "被跳過筆", "替補筆", "被跳過假想平均", "替補平均", "被跳過假想和", "替補和")
    C = []
    for wn, sg in REPSEG:
        W = _W[wn]; x, y = W["segp"][sg]; b = W["b50"][sg]
        A = SE[SE["世界"] == wn]
        for v in VARS:
            row = {"世界": wn, "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}", "變體": v, "說明": DESC[v], "顆數": len(A)}
            for k in KS:
                m_, p10, p90 = q3(A[f"{sg}_{v}_{k}"])
                row[k] = m_; row[f"{k}_p10"] = p10; row[f"{k}_p90"] = p90
            row["比值"] = row["年化"] / abs(row["回落"]); row["對0050"] = IG.label(row["年化"], row["回落"], b)
            row["合併比值"] = row["合併年化"] / abs(row["合併回落"]); row["合併對0050"] = IG.label(row["合併年化"], row["合併回落"], b)
            for k in ("年化", "回落", "合併年化", "合併回落"):
                m_, p10, p90 = q3(A[f"{sg}_{v}_{k}"] - A[f"{sg}_原版_{k}"])
                row[f"差_{k}"] = m_; row[f"差_{k}_p10"] = p10; row[f"差_{k}_p90"] = p90
            m_, p10, p90 = q3(A[f"{sg}_{v}_替補平均"] - A[f"{sg}_{v}_被跳過假想平均"])
            row["替補減被跳過"] = m_; row["替補減被跳過_p10"] = p10; row["替補減被跳過_p90"] = p90
            if v == "原版":
                for k in ("同日營飆也買筆", "營飆持有中買筆"):
                    row[k], row[f"{k}_p10"], row[f"{k}_p90"] = q3(A[f"{sg}_原版_{k}"])
            row["營飆年化"] = q3(A[f"{sg}_營飆_年化"])[0]; row["營飆回落"] = q3(A[f"{sg}_營飆_回落"])[0]
            row.update({"0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])})
            C.append(row)
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S["表"] = C.to_dict("records"); S["完成（台北）"] = YV.now_tpe()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(S, C)
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
    log("\n" + C[["段", "變體", "年化", "年化_p10", "年化_p90", "回落", "比值", "對0050", "差_年化", "合併年化", "合併回落", "合併比值", "差_合併年化",
                  "F中也在Y", "Y中也在F", "相異檔數", "日報酬相關", "被跳過筆", "替補筆", "被跳過假想平均", "替補平均", "替補減被跳過"]].to_string(index=False))
    log(f"[完] {YV.now_tpe()}（台北）")


def pc(v, d=1, sign=True):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v * 100:+.{d}f}%" if sign else f"{v * 100:.{d}f}%"


def rg(r, k, d=1, sign=True):
    if r["變體"] == "原版" or not np.isfinite(r.get(f"{k}_p10", np.nan)) or r[f"{k}_p10"] == r[f"{k}_p90"]:
        return pc(r[k], d, sign)
    return f"{pc(r[k], d, sign)}〔{pc(r[f'{k}_p10'], d, sign)}～{pc(r[f'{k}_p90'], d, sign)}〕"


def report(S, C):
    L = ["# 營量遇營飆同檔就跳過：描述性測試", "", f"產出 {S['完成（台北）']}（台北）。回測線計算子代理。⭐ 描述、不計 N、看過結果才提的變體、不改規則。", "",
         f"> ⚠ {WORD}。", "", "## 變體（看報酬前寫死）", "", "| 代號 | 內容 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in DESC.items()]
    L += ["", "營飆帳在三個變體都相同（＝ 營飆 v1 原版，逐位元）；只有營量帳變。X1／X2 的營量隨營飆抽籤種子變 ⇒ 200 顆中位〔p10～p90〕。", ""]
    for wn, sg in REPSEG:
        g = C[(C["世界"] == wn) & (C["段"] == sg)]
        r0 = g.iloc[0]
        L += [f"## {sg}（{r0['窗']}）", "", f"0050：{pc(r0['0050年化'])}／{pc(r0['0050回落'])}／{r0['0050比值']:.2f}；營飆本帳（三變體相同）中位 {pc(r0['營飆年化'])}／{pc(r0['營飆回落'])}", "",
              "| 變體 | 營量 年化 | 回落 | 比值 | 對 0050 | 年化差（對原版） | 合併 年化 | 合併 回落 | 合併 比值 | 合併年化差 |", "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            L.append(f"| {r['變體']} | {rg(r, '年化')} | {rg(r, '回落')} | {r['比值']:.2f} | {r['對0050']} | {'—' if r['變體'] == '原版' else rg(r, '差_年化')} | "
                     f"{rg(r, '合併年化')} | {rg(r, '合併回落')} | {r['合併比值']:.2f} | {'—' if r['變體'] == '原版' else rg(r, '差_合併年化')} |")
        L += ["", "| 變體 | 營飆持股中在營量 | 營量持股中在營飆 | 合併相異檔數 | 日報酬相關 | 營量持股 | 被跳過筆 | 替補筆 | 替補實際淨報酬平均 | 被跳過假想淨報酬平均 | 替補−被跳過 |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            if r["變體"] == "原版":
                L.append(f"| 原版 | {rg(r, 'F中也在Y', 1, False)} | {rg(r, 'Y中也在F', 1, False)} | {r['相異檔數']:.1f} | {r['日報酬相關']:.2f} | {r['持股']:.1f} | — | — | — | — | — |")
            else:
                L.append(f"| {r['變體']} | {rg(r, 'F中也在Y', 1, False)} | {rg(r, 'Y中也在F', 1, False)} | {r['相異檔數']:.1f}〔{r['相異檔數_p10']:.1f}～{r['相異檔數_p90']:.1f}〕 | "
                         f"{r['日報酬相關']:.2f}〔{r['日報酬相關_p10']:.2f}～{r['日報酬相關_p90']:.2f}〕 | {r['持股']:.1f} | {r['被跳過筆']:.0f}〔{r['被跳過筆_p10']:.0f}～{r['被跳過筆_p90']:.0f}〕 | "
                         f"{r['替補筆']:.0f}〔{r['替補筆_p10']:.0f}～{r['替補筆_p90']:.0f}〕 | {rg(r, '替補平均')} | {rg(r, '被跳過假想平均')} | {rg(r, '替補減被跳過')} |")
        L.append("")
    L += ["註：", "- 年化、回落 ＝ rerun17.win_metrics；比值 ＝ 年化 ÷ |回落|；對 0050：合格 ＝ 年化 ＞ 0050 且比值 ≥ 0050；另列 ＝ 只贏年化；不合格 ＝ 年化沒贏。比值、對 0050 用中位。",
          "- 合併 ＝ 兩本帳各半、每年第一個交易日調回、換手×0.585%（researchp17.compose，＝ resultsYLmerge 各半·年調）。使用者實際是兩本帳各自資金，營量本帳那欄即是。",
          "- 年化差 ＝ 同一顆種子 X − 原版 的成對差中位〔p10～p90〕。",
          "- 被跳過 ＝ 若不排除、營量當天依同一狀態會買的排除檔；替補 ＝ 因此改買的下一名。被跳過多於替補 ＝ 當天沒有下一名候選，空位留現金。",
          "  淨報酬 ＝ 每筆（扣 0.585%）；被跳過的是假想（同日開盤進、營量 60 天出場或停止交易強制出場）。每顆先平均再取 200 顆中位。", "",
          "## 對帳", "", "```", json.dumps(S["閘"], ensure_ascii=False, indent=1), "```", "",
          f"早年註：{'；'.join(S['早年註'])}", "", f"> ⚠ {WORD}。", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
