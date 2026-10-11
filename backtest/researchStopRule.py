# -*- coding: utf-8 -*-
"""營量營飆停用條件 seq1（台股策略線登錄 sha 2c7943d7a204c1a8；裁定 seq339 交辦；監控規則、⛔ 不計 N）§四 ①② ——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchStopRule [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchStopRule_check [--procs 3]

═══ 讀法（寫死於 2026-10-11 20:34（台北），在算任何本件數字之前；⚠ 本線看過的：營量 v1／營飆 v1 兩段的年化與最大回落
    （營量 早年 +21.8%／−34.4%、主窗 +35.02%／−32.13%；營飆 早年 +15.2%／−56.1%、主窗 +37.79%／−40.48%）；⛔ 沒看過任何月底 R12 分布）═══
 S1 淨值來源（⛔ 不改引擎；照各策略已判正式版）：
    主窗 2017-03-02～2026-08-24 ＝ researchYL_integrate.main_world（＝ researchT1fix.build_ctx(True)：AND T1、停止交易強制出場開）
    早年 2005-02-01～2014-12-31 ＝ researchYL_integrate.early_world（上市＋上櫃版面 eotc_f65bb03e11、AND T1＋R8 減資截斷）
      ⚠ 引用必附（裁定 seq283）：上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市
      ⚠ IFRS（裁定 seq284）：2013-01～2014-12 的訊號回看 24 個月跨 IFRS 換軌；早年對外口徑照「不剔除版」，本件同（剔除版不另算）
    營量 v1 ＝ IG.eng(W, "H60·S20·無·relvol", r＝0)（relvol 挑選、1 條）；營飆 v1 ＝ IG.eng(W, "H120·S10·閘·抽籤", r)，r ＝ 0～199
    開盤價成交、0.585% 成本（引擎 COST，出場一次扣）；閘：每條權益 eq_sha ＝ resultsYL_integrate/seeds.csv.gz（同世界、同格、同 r）
    0050 ＝ 各世界版面的 0050 還原收盤（RR.load_bench，含息還原）；閘：主窗 bench_row ＝ researchT1fix ANCHOR；早年 ＝ early_world 的 b50 repr
    「資料尾」＝ 正式主窗尾 2026-08-24（rerun17 win 讀法；⛔ 不自行延長到正式回測以外的日子）
 S2 月底：段內每個日曆月的最後一個交易日（cal 下一個交易日換月者；早年版面日曆止於 2014-12-31 ⇒ 段尾是月底就算）；段首 w0 當基準點 M0（⛔ 不當月底）；
    段尾若不是月底（主窗 2026-08-24 之後 cal 還有 8 月的日子）⇒ 該殘月不算月底
    第 j 個月底（j ＝ 1, 2, …）：j ≥ 12 ⇒ R12 ＝ (E[Mj]/E[Mj−12] − 1) − (B[Mj]/B[Mj−12] − 1)（M0 ＝ w0）
    D ＝ E[Mj] ÷ 段首起逐日最高淨值 − 1（逐日權益、月底判）
 S3 ① x ＝ 兩段合併所有 j ≥ 12 月底 R12 的第 5 百分位（np.percentile 線性內插）；兩段各自的第 5 百分位另報
    Dmax ＝ min(早年段逐日最深回落, 主窗段逐日最深回落)（段內逐日、= RR.win_metrics 的 mdd）；兩段各報、附高點日與低點日
    營飆 200 顆：每顆各算 x_r、Dmax_r ⇒ ⭐ 寫死數字取 200 顆中位（同本線「報 200 顆中位」慣例；登錄引的早年 −56% 即中位）；
      另報 p10～p90 與「200 顆 R12 合併後的第 5 百分位」（參考）
 S4 ② 歷史滾動驗算：每段各自當成一次前瞻（段首級 0、從段首起算月數、高點從段首起算）；x、Dmax 用 S3 寫死的原始值（不四捨五入）
    判斷值 R：j ＜ 6 不判（T1 不觸發；「改善」「恢復」只看 D）；6 ≤ j ＜ 12 ⇒ 累計差 (E[Mj]/E[M0] − 1) − (B[Mj]/B[M0] − 1)；j ≥ 12 ⇒ R12
    T1 ＝ R ＜ x；T2 警戒 ＝ D ≤ 0.8×Dmax；T2 停用 ＝ D ≤ Dmax；改善 ＝ R ≥ x 且 D ＞ 0.8×Dmax；恢復條件 ＝ R ≥ 0 且 D ＞ 0.8×Dmax
    狀態機（月底收盤判，動作自次一交易日生效）：
      級 0：T2 停用 ⇒ 級 2；否則 T1 或 T2 警戒 ⇒ 級 1（3 個月時鐘歸零）
      級 1（由級 0 進）：時鐘 +1；T2 停用 ⇒ 級 2；否則 改善 ⇒ 級 0；否則 時鐘 ＝ 3 ⇒ 級 2（「滿 3 個月仍未改善」＝ 進級後第 3 個月底判）
      級 2：T2 停用 ⇒ 恢復計數歸零；恢復條件成立 ⇒ 計數 +1，連續 6 個 ⇒ 級 1（恢復級 1）；不成立 ⇒ 歸零
      恢復級 1：T2 停用 ⇒ 級 2；恢復條件連續 6 個（自進恢復級 1 的下一個月底起數）⇒ 級 0；
        ⚠ 登錄沒寫、本件選的讀法（請台股／裁定過目）：恢復級 1 中再出現 T1 或 T2 警戒 ⇒ 起 3 個月時鐘，3 個月內改善 ⇒ 時鐘解除（仍在恢復級 1、恢復計數照算）；
          滿 3 個月未改善 ⇒ 級 2。（不讓恢復級 1 套「級 1 改善 ⇒ 回級 0」，否則「再連續 6 個月 ⇒ 回級 0」形同虛設）
      T3 無法回測（T3a 是實際帳戶與規則的偏離、T3b 資料源改版、T3c 制度變 ⇒ 回測期沒有對應的紙上量）⇒ 不套
 S5 ② 報：每年進級 1（級 0→1）／進級 2 的次數、各級停留月數（第 j 個月的生效級 ＝ 第 j−1 個月底判後的級）、每段級 1／級 2 的段數與長度；
    觸發後 12 個月 策略 − 0050（觸發月底 Mj 起到 Mj+12；段尾不足 12 個月 ⇒ 另列「未滿」）；
    「太敏感」＝ 兩段合計 進級 2 次數 ÷ 年數 ＞ 0.5；「太鈍」＝ 2008 與 2022 兩個日曆年都沒有任何月底判後級別 ≥ 1
    ⚠ 循環：x、Dmax 取自同一回測期 ⇒ T1 在回測期內依構造約 5% 的月底觸發；T2 停用線＝回測期最深那一次，月底判最多碰到一次（低點剛好在月底才碰得到）⇒ 照數
 S6 減碼／停用的帳戶模擬（⭐ 近似，⛔ 不改引擎）：級別由【紙上淨值】判（登錄 §一：量的是規則版紙上淨值；停用期間照記）⇒ 級別序列與模擬帳戶無關
    逐筆重播引擎的 audit（同日先賣後買）：原筆 i 的買進比例 f_i ＝ 金額 ÷ 原權益[t−1]；模擬帳戶買 m × f_i × 模擬權益[t−1]（m：級 0 ＝ 1、級 1 ＝ 0.5、級 2 ＝ 0）；
      部位之後的市值、出場淨入帳照原筆等比例（同一檔、同一天、同價、同成本）
    0050 子帳（單位數 × 0050 還原收盤；每次買賣付單邊 COST/2，同引擎 cash_mode="bench" 慣例）：
      級 1 新買 ⇒ 省下的半份 0.5 × f_i × 模擬權益[t−1] 從現金買 0050；買股現金不足 ⇒ 先賣 0050 補
      進級 2 的生效日 ⇒ 現金全轉 0050；級 2 期間出場淨入帳 ⇒ 買 0050；回級 0 的生效日 ⇒ 0050 全賣回現金；級 2→恢復級 1 ⇒ 0050 留著、買股時賣
      0050 進出一律用當日收盤（股票是當日開盤）⇒ 日內時點近似
    ⚠ 近似之處：① 停用期間沒買的那些名額，真實引擎在恢復後會用空槽買別檔，這裡只照原名單（⇒ 恢復後頭幾個月持股偏少）；
      ② 原引擎的「金額 ＝ min(槽, 現金)」改成等比例縮放；③ 0050 用收盤價進出
    閘：級別全 0 時，模擬帳戶逐日 ＝ 原權益（相對差 ≤ 1e−9）
 輸出 backtest/resultsStopRule/：stop_rule.json、levels_monthly.csv（⛔ 不出 HTML）
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
from backtest import research11 as R
from backtest import rerun17 as RR
from backtest import researchYL_integrate as IG

TIME = "2026-10-11 20:34（台北）"
OUT = "backtest/resultsStopRule"
NSEED = 200
if os.environ.get("SR_QUICK"):                                   # 煙霧測試（不是交件）
    NSEED, OUT = 3, "/tmp/sr_quick"
STRATS = {"營量 v1": IG.YL, "營飆 v1": IG.YF}
SEGN = {"早年": "早年 2005-02～2014-12", "主": "主窗 2017-03～2026-08-24"}
BC = R.COST / 2
ANCHOR = (0.24020209886370614, -0.3395700527611012)
MULT = {0: 1.0, 1: 0.5, 2: 0.0}
_W: dict = {}


def seeds_of(sn):
    return [0] if sn == "營量 v1" else list(range(NSEED))


# ═════════════ 月底與 R、D ═════════════
def month_ends(cal, w0, w1):
    per = cal.to_period("M")
    out = [p for p in range(w0, w1 + 1) if p + 1 < len(cal) and per[p + 1] != per[p]]
    if w1 == len(cal) - 1 and cal[w1] == cal[w1] + pd.offsets.BMonthEnd(0):     # 版面日曆止於段尾且段尾是月底（早年 2014-12-31）
        out.append(w1)
    return out


def path_stats(eq, bench, w0, w1, MEs):
    P = np.array([w0] + list(MEs))
    E = eq[P]; B = bench[P]; K = len(MEs)
    seg = eq[w0:w1 + 1]; rm = np.maximum.accumulate(seg); dd = seg / rm - 1.0
    D = dd[np.asarray(MEs) - w0]
    R12 = np.full(K, np.nan); RJ = np.full(K, np.nan); kind = np.array(["不判"] * K, dtype=object)
    for j in range(1, K + 1):
        if j >= 12:
            R12[j - 1] = (E[j] / E[j - 12] - 1.0) - (B[j] / B[j - 12] - 1.0)
            RJ[j - 1] = R12[j - 1]; kind[j - 1] = "R12"
        elif j >= 6:
            RJ[j - 1] = (E[j] / E[0] - 1.0) - (B[j] / B[0] - 1.0); kind[j - 1] = "累計"
    tr = int(np.argmin(dd)); pk = int(np.argmax(seg[:tr + 1]))
    return {"P": P, "E": E, "B": B, "D": D, "R12": R12, "RJ": RJ, "kind": kind, "mdd": float(dd.min()), "trough": w0 + tr, "peak": w0 + pk}


def pct5(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return float(np.percentile(v, 5))


# ═════════════ 狀態機 ═════════════
def levels(RJ, D, x, Dmax):
    L, rec, clock, rc = 0, False, None, 0
    out = []
    for j in range(len(D)):
        Rv = RJ[j]; av = bool(np.isfinite(Rv))
        t1 = av and Rv < x; warn = bool(D[j] <= 0.8 * Dmax); stop = bool(D[j] <= Dmax)
        imp = (not av or Rv >= x) and D[j] > 0.8 * Dmax
        rok = (not av or Rv >= 0) and D[j] > 0.8 * Dmax
        prev, prec, why = L, rec, ""
        if L == 0:
            if stop:
                L, rc, why = 2, 0, "T2停用"
            elif t1 or warn:
                L, rec, clock = 1, False, 0
                why = "+".join(k for k, v in (("T1", t1), ("T2警戒", warn)) if v)
        elif L == 1 and not rec:
            clock += 1
            if stop:
                L, rc, clock, why = 2, 0, None, "T2停用"
            elif imp:
                L, clock, why = 0, None, "改善"
            elif clock >= 3:
                L, rc, clock, why = 2, 0, None, "滿3月未改善"
        elif L == 1 and rec:
            if stop:
                L, rec, rc, clock, why = 2, False, 0, None, "T2停用"
            else:
                if clock is not None:
                    clock += 1
                    if imp:
                        clock = None
                    elif clock >= 3:
                        L, rec, rc, clock, why = 2, False, 0, None, "恢復級1中再觸發滿3月未改善"
                elif t1 or warn:
                    clock = 0; why = "恢復級1中再觸發（起3月時鐘）"
                if L == 1:
                    rc = rc + 1 if rok else 0
                    if rc >= 6:
                        L, rec, rc, why = 0, False, 0, "恢復連6月→級0"
        else:
            if stop:
                rc = 0
            elif rok:
                rc += 1
                if rc >= 6:
                    L, rec, clock, rc, why = 1, True, None, 0, "恢復連6月→級1"
            else:
                rc = 0
        out.append({"prev": prev, "prev_rec": prec, "L": L, "rec": rec, "why": why, "t1": t1, "warn": warn, "stop": stop, "imp": bool(imp), "rok": bool(rok)})
    return out


def lev_days(n, MEs, lv, w1):
    a = np.zeros(n, np.int8)
    for j, m in enumerate(MEs):
        a[m + 1:(MEs[j + 1] + 1) if j + 1 < len(MEs) else w1 + 1] = lv[j]["L"]
    return a


# ═════════════ 帳戶重播（近似）═════════════
def replay(eq, au, closes, bench, lev, first, w1):
    n = len(eq)
    V = np.ones(n); C = 1.0; Z = 0.0
    pos = {}; q = {}
    byt = {}
    for i, a in enumerate(au):
        byt.setdefault(a[0], []).append((i, a))
    for t in range(first, w1 + 1):
        b = float(bench[t]); lt = int(lev[t]); lp = int(lev[t - 1]) if t > 0 else 0
        if lt != lp:
            if lt == 0 and Z > 0:
                C += Z * b * (1 - BC); Z = 0.0
            if lt == 2 and C > 0:
                Z += C * (1 - BC) / b; C = 0.0
        evs = byt.get(t, [])
        for i, (tt, side, sid, amt, cost, px) in evs:
            if side != "sell":
                continue
            j_, k = q[sid].pop(0)
            if k > 0:
                pos.pop(j_)
                net = (amt - cost) * k
                if lt == 2:
                    Z += net * (1 - BC) / b
                else:
                    C += net
        for i, (tt, side, sid, amt, cost, px) in evs:
            if side != "buy":
                continue
            f = amt / eq[t - 1]; Vp = V[t - 1]; want = MULT[lt] * f * Vp; k = 0.0
            if want > 0:
                if C < want and Z > 0:
                    units = min((want - C) / (b * (1 - BC)), Z)
                    C += units * b * (1 - BC); Z -= units
                a_ = min(want, C); C -= a_; k = a_ / amt
                if lt == 1:
                    h = min(0.5 * f * Vp, C)
                    if h > 0:
                        Z += h * (1 - BC) / b; C -= h
            q.setdefault(sid, []).append((i, k))
            if k > 0:
                pos[i] = (sid, amt * k, px)
        hv = sum(ak * float(closes[s][t]) / ep for s, ak, ep in pos.values())
        V[t] = C + Z * b + hv
    V[w1 + 1:] = V[w1]
    return V


# ═════════════ 引擎 ═════════════
def job(args):
    wn, sn, r = args
    o, au = IG.eng(_W[wn], STRATS[sn], r)
    eq = np.asarray(o["equity"], float)
    auc = [(int(a["t"]), a["side"], a["sid"], float(a["amt"]), float(a.get("cost", 0.0)), float(a["px"])) for a in au]
    return wn, sn, r, eq, int(o["first"]), int(o["end"]), auc


def build(log, procs):
    Wm, gm = IG.main_world(log)
    bm = np.asarray(RR._G["bench"], float).copy()
    We, ge = IG.early_world(log, procs)
    be = np.asarray(RR.load_bench(We["cal"]), float)
    gates = {**gm, **ge}
    b0 = RR.bench_row(Wm["cal"], bm, Wm["w0"], Wm["w1"] + 1)
    gates["0050 主窗 ＝ T1fix ANCHOR（repr）"] = bool(repr(b0["cagr"]) == repr(ANCHOR[0]) and repr(b0["mdd"]) == repr(ANCHOR[1]))
    b1 = RR.bench_row(We["cal"], be, We["w0"], We["w1"] + 1)
    gates["0050 早年 ＝ early_world b50（repr）"] = bool(repr(b1["cagr"]) == repr(We["b50"]["早年"]["cagr"]) and repr(b1["mdd"]) == repr(We["b50"]["早年"]["mdd"]))
    Wm["bench"], We["bench"] = bm, be
    return {"主": Wm, "早年": We}, gates


def run_engines(WS, procs, log):
    _W.update(WS)
    jobs = [(wn, sn, r) for wn in ("早年", "主") for sn in STRATS for r in seeds_of(sn)]
    with Pool(procs) as pool:
        res = pool.map(job, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    bad = sum(int(IG.sha(eq) != REF[(wn, STRATS[sn], r)]) for wn, sn, r, eq, *_ in res)
    RES = {(wn, sn, r): {"eq": eq, "first": f, "end": e, "au": au} for wn, sn, r, eq, f, e, au in res}
    log(f"[引擎] {len(res)} 條｜eq_sha ≠ integrate：{bad}")
    return RES, bad


# ═════════════ 彙總工具 ═════════════
def q3(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v):
        return {"中位": None, "p10": None, "p90": None, "n": 0}
    return {"中位": float(np.median(v)), "p10": float(np.quantile(v, .1)), "p90": float(np.quantile(v, .9)), "n": int(len(v))}


def pc(v):
    return None if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"


def dstr(cal, p):
    return str(cal[int(p)].date())


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    WS, gates = build(log, a.procs)
    RES, bad = run_engines(WS, a.procs, log)
    gates["eq_sha ＝ resultsYL_integrate/seeds.csv.gz（不同條數）"] = bad
    ME = {wn: month_ends(W["cal"], W["w0"], W["w1"]) for wn, W in WS.items()}
    for wn, W in WS.items():
        cal = W["cal"]
        log(f"[{wn}] 窗 {dstr(cal, W['w0'])}～{dstr(cal, W['w1'])}｜月底 {len(ME[wn])} 個 {dstr(cal, ME[wn][0])}～{dstr(cal, ME[wn][-1])}｜cal 尾 {dstr(cal, len(cal) - 1)}")
    # ── 每條路徑的月底統計 ──
    ST = {}
    mdd_gate = 0.0
    for (wn, sn, r), v in RES.items():
        W = WS[wn]
        s = path_stats(v["eq"], W["bench"], W["w0"], W["w1"], ME[wn])
        c_, m_, _ = RR.win_metrics(v["eq"], v["first"], v["end"], W["w0"], W["w1"])
        mdd_gate = max(mdd_gate, abs(s["mdd"] - m_)); s["cagr"] = c_; s["mdd_wm"] = m_
        ST[(wn, sn, r)] = s
    gates["段內逐日回落 vs RR.win_metrics 最大差"] = mdd_gate
    # ── ① x、Dmax ──
    TH = {}
    for sn in STRATS:
        per = []
        for r in seeds_of(sn):
            se, sm = ST[("早年", sn, r)], ST[("主", sn, r)]
            per.append({"r": r, "x": pct5(np.r_[se["R12"], sm["R12"]]), "x早年": pct5(se["R12"]), "x主": pct5(sm["R12"]),
                        "D早年": se["mdd"], "D主": sm["mdd"], "Dmax": min(se["mdd"], sm["mdd"])})
        P_ = pd.DataFrame(per)
        x = float(np.median(P_["x"])); Dm = float(np.median(P_["Dmax"]))
        pool_all = np.concatenate([np.r_[ST[("早年", sn, r)]["R12"], ST[("主", sn, r)]["R12"]] for r in seeds_of(sn)])
        where = {}
        for wn in ("早年", "主"):
            cal = WS[wn]["cal"]
            pk = pd.Series([dstr(cal, ST[(wn, sn, r)]["peak"]) for r in seeds_of(sn)]).value_counts()
            tr = pd.Series([dstr(cal, ST[(wn, sn, r)]["trough"]) for r in seeds_of(sn)]).value_counts()
            s0 = ST[(wn, sn, 0)]
            where[wn] = {"r0 高點日": dstr(cal, s0["peak"]), "r0 低點日": dstr(cal, s0["trough"]), "r0 回落": s0["mdd"],
                         "低點日最常見": tr.index[0], "低點日最常見占比": float(tr.iloc[0] / len(seeds_of(sn))),
                         "高點日最常見": pk.index[0], "高點日最常見占比": float(pk.iloc[0] / len(seeds_of(sn))),
                         "R12 個數（每條）": int(np.isfinite(s0["R12"]).sum())}
        deep_seg = "早年" if float(np.median(P_["D早年"])) <= float(np.median(P_["D主"])) else "主"
        TH[sn] = {
            "x": x, "x_百分比": pc(x), "Dmax": Dm, "Dmax_百分比": pc(Dm), "警戒線 0.8×Dmax": 0.8 * Dm, "警戒線_百分比": pc(0.8 * Dm),
            "x_早年段": float(np.median(P_["x早年"])), "x_早年段_百分比": pc(float(np.median(P_["x早年"]))),
            "x_主窗段": float(np.median(P_["x主"])), "x_主窗段_百分比": pc(float(np.median(P_["x主"]))),
            "Dmax_早年段": float(np.median(P_["D早年"])), "Dmax_早年段_百分比": pc(float(np.median(P_["D早年"]))),
            "Dmax_主窗段": float(np.median(P_["D主"])), "Dmax_主窗段_百分比": pc(float(np.median(P_["D主"]))),
            "最深出在": SEGN[deep_seg], "高低點": where,
            "原始年化／回落（核對）": {wn: {"年化": q3([ST[(wn, sn, r)]["cagr"] for r in seeds_of(sn)])["中位"],
                                 "回落": q3([ST[(wn, sn, r)]["mdd"] for r in seeds_of(sn)])["中位"]} for wn in ("早年", "主")},
        }
        if sn == "營飆 v1":
            TH[sn]["寫死口徑"] = "200 顆各自算 x_r、Dmax_r ⇒ 取中位"
            TH[sn]["x 200 顆分布"] = q3(P_["x"]); TH[sn]["Dmax 200 顆分布"] = q3(P_["Dmax"])
            TH[sn]["x（參考：200 顆 R12 合併後第 5 百分位）"] = pct5(pool_all)
            TH[sn]["Dmax 出在早年段的顆數比例"] = float((P_["D早年"] <= P_["D主"]).mean())
        else:
            TH[sn]["寫死口徑"] = "relvol 挑選、不抽籤 ⇒ 1 條"
        log(f"[①] {sn}：x {x:.6f}（{pc(x)}）｜Dmax {Dm:.6f}（{pc(Dm)}）")
    for wn in ("早年", "主"):
        W = WS[wn]
        TH.setdefault("0050", {})[wn] = RR.bench_row(W["cal"], W["bench"], W["w0"], W["w1"] + 1)
    # ── ② 狀態機＋帳戶重播 ──
    rows = []; SUM = {}
    gate_rep = 0.0
    for sn in STRATS:
        x, Dm = TH[sn]["x"], TH[sn]["Dmax"]
        per = []
        for r in seeds_of(sn):
            ps = {"r": r, "年": {}, "觸發後12月": [], "段": {}}
            n_l2 = 0; n_years = 0.0; bear = {2008: False, 2022: False}
            for wn in ("早年", "主"):
                W = WS[wn]; cal = W["cal"]; s = ST[(wn, sn, r)]; v = RES[(wn, sn, r)]
                lv = levels(s["RJ"], s["D"], x, Dm)
                K = len(lv); n_years += K / 12.0
                eff = [0] + [lv[j]["L"] for j in range(K - 1)]
                ep1, ep2 = [], []; cur = None
                for j in range(K):
                    d = cal[s["P"][j + 1]]; y = int(d.year)
                    Y = ps["年"].setdefault(y, {"進級1": 0, "進級2": 0, "月_級0": 0, "月_級1": 0, "月_級2": 0})
                    Y[f"月_級{eff[j]}"] += 1
                    L, prev = lv[j]["L"], lv[j]["prev"]
                    if L == 1 and prev == 0:
                        Y["進級1"] += 1
                    if L == 2 and prev != 2:
                        Y["進級2"] += 1; n_l2 += 1
                    if y in bear and L >= 1:
                        bear[y] = True
                    if (L == 1 and prev == 0) or (L == 2 and prev != 2):
                        jj = j + 1; je = min(jj + 12, K)
                        dd_ = (s["E"][je] / s["E"][jj] - 1.0) - (s["B"][je] / s["B"][jj] - 1.0)
                        ps["觸發後12月"].append({"段": wn, "月": str(d.to_period("M")), "進": f"級{L}", "原因": lv[j]["why"],
                                              "策略−0050": float(dd_), "滿12月": bool(jj + 12 <= K), "策略": float(s["E"][je] / s["E"][jj] - 1.0),
                                              "0050": float(s["B"][je] / s["B"][jj] - 1.0)})
                    rows.append({"策略": sn, "r": r, "段": wn, "月": str(d.to_period("M")), "月底日": str(d.date()), "月序": j + 1,
                                 "R_類": s["kind"][j], "R": s["RJ"][j], "R12": s["R12"][j], "D": s["D"][j],
                                 "T1": int(lv[j]["t1"]), "T2警戒": int(lv[j]["warn"]), "T2停用": int(lv[j]["stop"]), "改善": int(lv[j]["imp"]), "恢復條件": int(lv[j]["rok"]),
                                 "判前級": lv[j]["prev"], "判後級": L, "恢復級1": int(lv[j]["rec"]), "生效級（本月）": eff[j], "變動原因": lv[j]["why"]})
                # 段落（以生效級連續段計長度）
                effs = eff[1:] + [lv[-1]["L"]]                       # 第 j 個月底判後 ⇒ 第 j+1 個月生效
                runs = []
                for k_, g in pd.Series(effs).groupby((pd.Series(effs) != pd.Series(effs).shift()).cumsum()):
                    runs.append((int(g.iloc[0]), len(g)))
                # 帳戶重播
                lev = lev_days(len(v["eq"]), ME[wn], lv, W["w1"])
                V = replay(v["eq"], v["au"], W["closes"], W["bench"], lev, v["first"], W["w1"])
                if r < 2 or sn == "營量 v1":
                    V0 = replay(v["eq"], v["au"], W["closes"], W["bench"], np.zeros_like(lev), v["first"], W["w1"])
                    gate_rep = max(gate_rep, float(np.max(np.abs(V0[:W["w1"] + 1] / v["eq"][:W["w1"] + 1] - 1.0))))
                cm, mm, _ = RR.win_metrics(V, v["first"], v["end"], W["w0"], W["w1"])
                ps["段"][wn] = {"原 年化": s["cagr"], "原 回落": s["mdd"], "規則後 年化": cm, "規則後 回落": mm,
                               "原 成長倍數": float(v["eq"][W["w1"]] / v["eq"][W["w0"]]), "規則後 成長倍數": float(V[W["w1"]] / V[W["w0"]]),
                               "天數": int(W["w1"] - W["w0"] + 1), "級1段長": [ln for lvv, ln in runs if lvv == 1], "級2段長": [ln for lvv, ln in runs if lvv == 2],
                               "月底碰 T2停用 次數": int(sum(z["stop"] for z in lv)), "月底 T1 觸發數": int(sum(z["t1"] for z in lv)),
                               "可判 R 月數": int(np.isfinite(s["RJ"]).sum()), "R12 月數": int(np.isfinite(s["R12"]).sum()),
                               "R12＜x 月數": int(np.nansum(s["R12"] < x)), "月數": K,
                               "生效級月數": {f"級{k_}": int(sum(1 for e_ in eff if e_ == k_)) for k_ in (0, 1, 2)}}
            days = sum(ps["段"][wn]["天數"] for wn in ps["段"])
            g0 = np.prod([ps["段"][wn]["原 成長倍數"] for wn in ps["段"]]); g1 = np.prod([ps["段"][wn]["規則後 成長倍數"] for wn in ps["段"]])
            ps["兩段合併"] = {"原 年化": float(g0 ** (245 / days) - 1), "規則後 年化": float(g1 ** (245 / days) - 1),
                          "原 回落": min(ps["段"][w]["原 回落"] for w in ps["段"]), "規則後 回落": min(ps["段"][w]["規則後 回落"] for w in ps["段"])}
            ps["進級2 每年"] = n_l2 / n_years; ps["年數"] = n_years
            ps["太敏感"] = bool(n_l2 / n_years > 0.5); ps["太鈍"] = bool(not bear[2008] and not bear[2022]); ps["空頭年有級≥1"] = {str(k): v_ for k, v_ in bear.items()}
            per.append(ps)
        SUM[sn] = summarize(sn, per, TH)
        log(f"[②] {sn}：{json.dumps(SUM[sn]['判斷'], ensure_ascii=False)}")
    gates["帳戶重播（級別全 0）vs 原權益 最大相對差"] = gate_rep
    gates["帳戶重播閘 ≤ 1e−9"] = bool(gate_rep <= 1e-9)
    LV = pd.DataFrame(rows)
    LV.to_csv(os.path.join(OUT, "levels_monthly.csv"), index=False, float_format="%.15g")
    OUTJ = {"讀法寫死": TIME, "登錄": "營量營飆停用條件 seq1（台股策略線 sha 2c7943d7a204c1a8；裁定 seq339 交辦；監控規則、不計 N）§四 ①②",
            "來源": {"主窗": "researchYL_integrate.main_world（＝researchT1fix.build_ctx(True)）2017-03-02～2026-08-24",
                   "早年": "researchYL_integrate.early_world（上市＋上櫃 eotc_f65bb03e11）2005-02-01～2014-12-31",
                   "營量 v1": "H60·S20·無·relvol r0（＝T1fix c13 t1）", "營飆 v1": "H120·S10·閘·抽籤 r0～199（＝T1fix c1 t1；早年＝researchYL_feiearly）",
                   "閘參照": "backtest/resultsYL_integrate/seeds.csv.gz（commit 2d41ca796f）",
                   "早年標註": IG.NOTE3, "IFRS": "2013-01～2014-12 訊號回看跨 IFRS 換軌；照早年對外口徑用不剔除版（裁定 seq284）",
                   "月底": {wn: [dstr(WS[wn]["cal"], ME[wn][0]), dstr(WS[wn]["cal"], ME[wn][-1]), len(ME[wn])] for wn in WS},
                   "主窗殘月": "主窗尾 2026-08-24 不是月底 ⇒ 2026-08 不算（最後月底 2026-07-31）" if ME["主"][-1] < WS["主"]["w1"] else "—"},
            "閘": gates, "①": TH, "②": SUM,
            "近似法": APPROX, "T3": "無法回測：T3a 需使用者實際持股、T3b 是資料源改版事件、T3c 是制度變 ⇒ 回測期沒有可套的紙上量；②只套 T1、T2",
            "循環": None, "耗時秒": None}
    OUTJ["循環"] = circ_note(SUM, TH)
    OUTJ["耗時秒"] = round(time.time() - T0)
    with open(os.path.join(OUT, "stop_rule.json"), "w", encoding="utf-8") as f:
        json.dump(OUTJ, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(f"[完] 閘 {json.dumps(gates, ensure_ascii=False, default=str)}｜{time.time() - T0:.0f}s")


APPROX = ["級別一律由紙上淨值（原規則、不減碼）判；模擬帳戶只用來量『照規則減碼／停用後』的年化與回落",
          "逐筆重播引擎 audit：每筆買進金額 ＝ m ×（原金額 ÷ 原權益[t−1]）× 模擬權益[t−1]，m：級0＝1、級1＝0.5、級2＝0；之後市值與出場淨入帳等比例",
          "級1 省下的半份買 0050；進級2 生效日現金全轉 0050、期間出場入帳買 0050；回級0 生效日 0050 全賣回現金；0050 每次進出付單邊 COST/2（0.2925%）、用當日收盤價",
          "停用期間沒買的名額，真實引擎恢復後會用空槽買別檔；這裡只照原名單 ⇒ 恢復後頭幾個月持股偏少（偏保守）",
          "原引擎『金額 ＝ min(槽, 現金)』改為等比例縮放；級別全 0 時重播 ＝ 原權益（閘 ≤ 1e−9）"]


def summarize(sn, per, TH):
    yrs = sorted({y for p in per for y in p["年"]})
    ytab = {}
    for y in yrs:
        g = [p["年"].get(y) for p in per if y in p["年"]]
        ytab[str(y)] = {k: (float(np.mean([z[k] for z in g])) if len(per) > 1 else g[0][k]) for k in ("進級1", "進級2", "月_級0", "月_級1", "月_級2")}
        if len(per) > 1:
            ytab[str(y)]["有進級1的顆數比例"] = float(np.mean([z["進級1"] > 0 for z in g]))
            ytab[str(y)]["有進級2的顆數比例"] = float(np.mean([z["進級2"] > 0 for z in g]))
    out = {"x 用值": TH[sn]["x"], "Dmax 用值": TH[sn]["Dmax"], "顆數": len(per), "每年（營飆＝200 顆平均）": ytab}
    seg = {}
    for wn in ("早年", "主", "兩段合併"):
        get = (lambda p, k: p["段"][wn][k]) if wn != "兩段合併" else (lambda p, k: p["兩段合併"][k])
        seg[wn] = {k: q3([get(p, k) for p in per]) for k in ("原 年化", "規則後 年化", "原 回落", "規則後 回落")}
        seg[wn]["年化差（規則後−原）"] = q3([get(p, "規則後 年化") - get(p, "原 年化") for p in per])
        seg[wn]["回落差（規則後−原）"] = q3([get(p, "規則後 回落") - get(p, "原 回落") for p in per])
        if wn != "兩段合併":
            seg[wn]["級1段數"] = q3([len(p["段"][wn]["級1段長"]) for p in per]); seg[wn]["級2段數"] = q3([len(p["段"][wn]["級2段長"]) for p in per])
            seg[wn]["級1段長（月，全部段合併）"] = q3([ln for p in per for ln in p["段"][wn]["級1段長"]])
            seg[wn]["級2段長（月，全部段合併）"] = q3([ln for p in per for ln in p["段"][wn]["級2段長"]])
            for k in ("級0", "級1", "級2"):
                seg[wn][f"生效{k}月數"] = q3([p["段"][wn]["生效級月數"][k] for p in per])
            seg[wn]["月底碰 T2停用 次數"] = q3([p["段"][wn]["月底碰 T2停用 次數"] for p in per])
            seg[wn]["R12＜x 月數 ÷ R12 月數"] = q3([p["段"][wn]["R12＜x 月數"] / p["段"][wn]["R12 月數"] for p in per])
            seg[wn]["月數"] = per[0]["段"][wn]["月數"]
    out["段"] = seg
    trig = [dict(z, r=p["r"]) for p in per for z in p["觸發後12月"]]
    T = pd.DataFrame(trig)
    tsum = {}
    if len(T):
        for (nm, full), g in T.groupby(["進", "滿12月"]):
            tsum[f"{nm}｜{'滿12月' if full else '未滿12月'}"] = {"筆數": int(len(g)), "每顆平均筆數": float(len(g) / len(per)), "策略−0050": q3(g["策略−0050"]),
                                                          "策略−0050 平均": float(g["策略−0050"].mean()), "策略−0050＞0 比例": float((g["策略−0050"] > 0).mean())}
    out["觸發後12月彙總"] = tsum
    if sn == "營量 v1":
        out["觸發後12月逐筆"] = trig
    else:
        r0 = [z for z in trig if z["r"] == 0]
        out["觸發後12月逐筆（r0）"] = r0
        out["觸發月份分布（全部顆數，前 20）"] = T.groupby(["進", "月"]).size().sort_values(ascending=False).head(20).rename("顆數").reset_index().to_dict("records") if len(T) else []
    l2y = [p["進級2 每年"] for p in per]
    out["判斷"] = {"進級2 每年（中位）": float(np.median(l2y)), "年數": per[0]["年數"],
                 "太敏感（每 2 年進級2 ＞ 1 次 ⇔ 每年 ＞ 0.5）": bool(np.median(l2y) > 0.5),
                 "太敏感 顆數比例": float(np.mean([p["太敏感"] for p in per])),
                 "2008 有級≥1 顆數比例": float(np.mean([p["空頭年有級≥1"]["2008"] for p in per])),
                 "2022 有級≥1 顆數比例": float(np.mean([p["空頭年有級≥1"]["2022"] for p in per])),
                 "太鈍（2008、2022 都沒進級1）顆數比例": float(np.mean([p["太鈍"] for p in per]))}
    out["判斷"]["太鈍"] = bool(out["判斷"]["太鈍（2008、2022 都沒進級1）顆數比例"] > 0.5)
    return out


def circ_note(SUM, TH):
    o = {}
    for sn in STRATS:
        s = SUM[sn]["段"]
        o[sn] = {"T1：回測期 R12＜x 的月比例（依構造約 5%）": {wn: s[wn]["R12＜x 月數 ÷ R12 月數"] for wn in ("早年", "主")},
                 "T2 停用線＝回測期最深那一次；月底判碰到的次數": {wn: s[wn]["月底碰 T2停用 次數"] for wn in ("早年", "主")},
                 "說明": "x、Dmax 取自同一回測期 ⇒ 驗算是樣本內：T1 觸發率被 x 的定義釘在 5% 附近；T2 停用線就是最深那次的逐日低點，"
                       "回測期內逐日只有那一天剛好等於 Dmax，月底判要低點恰在月底才碰得到 ⇒ ② 裡的級2 幾乎都來自「級1 滿 3 個月未改善」，"
                       "⛔ 不能拿來說明 T2 停用線在前瞻會多常觸發"}
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    lf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(m):
        s = f"[{time.strftime('%H:%M:%S')}] {m}"; print(s, flush=True); lf.write(s + "\n"); lf.flush()
    run(a, log)


if __name__ == "__main__":
    main()
