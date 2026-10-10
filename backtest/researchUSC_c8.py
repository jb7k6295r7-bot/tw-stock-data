# -*- coding: utf-8 -*-
"""USREG-C8（← 草稿 B8，sha a3bbe592df10f4ed）波動目標穩健性：A1-2 乙「依波動調整正2 比例」是一大片還是一格？＋前瞻紀錄。
裁定 seq321 §三：⚠ 事後追加 ⇒ ⛔ 不計 N、⛔ 不判合格；只描述（參數高原、分段）＋前瞻；早年合成照 seq309（扣 DTB3＋0.25% 融資與費用率）；QQQ 1999-03 前不可判定。

═══ C8 補讀法（C8- 標；⭐ 寫死於 2026-10-10 23:24（台北），寫死前 ⛔ 沒看任何 C8 數字；本執行者也沒看過 A1-2 乙早年段與其他格的數字，
    只在本檔閘 C8-9 讀 A1 結果檔做重現比對）═══
 C8-1 資料、引擎 ＝ USREG-A1 同一套（researchUSA1_data：~/usdata/60d2f99、load_market、engine（t 開盤成交、現金 DTB3 逐日）、perf、dd_info）；
      σ̂ ＝ researchLowFreq.lev_sigma（正2 過去 L 個日報酬 sd（ddof＝1）× √252，t−1 以前），權重 w ＝ min(1, σ*÷σ̂)（A1 P9 同式）；
      判斷所用的正2：2007-04-02 以前用合成、之後用真實（A1 件二 lev_of 同式）。
 C8-2 網格（登錄 §二）：σ* {15,20,25,30,35,40,50%} × L {10,20,60,120} × 其餘 {SPY（a）, 國庫券（b）} × 正2 {SSO, QLD} ＝ 112 格；原格 ＝ A1-2 乙 s40_L20_b_QLD。
      調整頻率：每月第一個交易日（主）；每週第一個交易日、每季第一個交易日（描述，同式，只換調整日）。成本：換手金額 × 0.05%（A1 引擎同式）。
 C8-3 分段（各段以 1.0 起算，段首開盤建倉付一次成本）：早年合成 SSO ＝ 合成 SSO 的 σ̂（L＝120）可算後第一個月初 ～ 2007-03-30；
      早年合成 QLD ＝ 合成 QLD（QQQ 含息價 ×2，seq313）σ̂（L＝120）可算後第一個月初 ～ 2007-03-30（QQQ 1999-03-10 前不可判定）；
      真實一 2007-04-02 ～ 2021-12-31；真實二 2022-01-03 ～ 2026-09-30。⭐ 同一段同一正2 的 56 格共用起點（L＝120 決定），⛔ 不逐格挑起點。
 C8-4 早年合成（seq309）：r ＝ 2 r_idx − (DTB3_{t−1}＋0.25%)/252 − f/252（researchUSA1_data.synth 同式）；f ＝ 資料庫 etf_expense_ratios.csv 的
      SEC 497K（2026-09-28）淨費用率（SSO、QLD）；毛費用率版、A1 原費用率版（0.89%／0.95%）只描述。
 C8-5 每格每段：年化、最大回落、比值、平均 w、每年換手、成本／年、對 ^SP500TR 判語（描述）、對「一直抱同一支正2」（同段、段首開盤買、付一次成本；早年用合成）。
      「好格」＝ 年化 ≥ 一直抱正2 且 最大回落較淺（回落 ＞ 一直抱正2 的回落）。
 C8-6 高原判讀（登錄 §四，看數字前寫死）：某段「站得住」＝ 該段 112 格中好格 ≥ 70%；
      某段「只是那一格」＝ 好格 ＜ 30%，或好格在 σ*×L 網格上（同其餘、同正2，上下左右相鄰）最大相連塊只有 1 格；其餘 ＝「中間」。
      總讀法：三段都站得住 ⇒「站得住」；一兩段站得住 ⇒「看段：只在〔段〕有用」；沒有一段站得住 ⇒ 三段都是「只是那一格」⇒「只是那一格」，否則「中間（不是一大片、也不只一格）」。
      站得住 ⇒ 進前瞻紀錄（照原格），結果句標「暫定、事後追加、需前瞻再驗」。
 C8-7 假訊號（登錄 §四）：原格每段，把段內各調整日的 w 值（含段首當時的 w）隨機重排 1,000 次（同調整次數、同一組 w ⇒ 同平均槓桿），
      p ＝ 隨機年化 ≥ 原格年化 的比例；另報隨機也是「好格」的比例。rng ＝ default_rng([20261010, 8, 段序])。
 C8-8 必報：每段最大回落、回本交易日數（A1 dd_info）；三次大跌期間平均 w：2008 ＝ 2007-10-09～2009-03-09、2020 ＝ 2020-02-19～2020-03-23、
      2022 ＝ 2022-01-03～2022-10-12（S&P 500 高點到低點；原格與各段格中位）；同平均槓桿固定比例：固定 w̄ 正2 ＋（1−w̄）其餘（同其餘），每月調回；
      「看波動贏固定」＝ 年化較高 且 比值不低（逐格、逐段報比例；原格逐段報）。換手、成本。窗尾（2026-09-30）w。
 C8-9 閘：① 每月版權重 ＝ researchLowFreq.W_yi 逐日相同；② A1 原格真實一（＝ A1 探索）、真實二（＝ A1 確認）年化與 resultsUSA1/A2_summary.json 相同（≤1e−9）；
      ③ A1 費用率＋A1 早年起點（1999-07-01）重跑原格早年 ＝ A1 早年年化。任一不過 ⇒ 不出結果。
 C8-10 前瞻（登錄 §一 3）：給原格 2026-10 的建議 w（σ̂ 用 2026-09-30 以前 20 根 QLD 日報酬）；之後逐月記錄由美股線做、⛔ 不改規則。
 C8-11 先驗對錯照登錄 §六 四條逐條報。
"""
from __future__ import annotations

import os
import time
from itertools import product
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backtest import researchUSC as K
from backtest import researchUSA1_data as A
from backtest import researchUSA1 as A1
from backtest import researchLowFreq as LF

READ_TS = "2026-10-10 23:24（台北）"
SIG = (15, 20, 25, 30, 35, 40, 50)
LS = (10, 20, 60, 120)
RESTS = ("a", "b")
LEVS = ("SSO", "QLD")
ORIG = (40, 20, "b", "QLD")
SEGN = ("早年合成", "真實一", "真實二")
CRASH = {"2008": ("2007-10-09", "2009-03-09"), "2020": ("2020-02-19", "2020-03-23"), "2022": ("2022-01-03", "2022-10-12")}
_M: dict = {}


def cname(s, L, v, lev):
    return f"s{s}_L{L}_{v}_{lev}"


def masks(cal, kind):
    """調整日：M ＝ 每月第一個交易日、W ＝ 每週第一個交易日、Q ＝ 每季第一個交易日（第 0 天不算）。"""
    d = pd.to_datetime(pd.Series(cal))
    if kind == "M":
        k = d.dt.year * 100 + d.dt.month
    elif kind == "Q":
        k = d.dt.year * 10 + (d.dt.month - 1) // 3
    else:
        iso = d.dt.isocalendar(); k = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    k = k.to_numpy()
    out = np.zeros(len(cal), bool); out[1:] = k[1:] != k[:-1]
    return out


def W_vt(ms, sg, s, v):
    N = len(ms); W = np.full((N, 2), np.nan); wv = np.full(N, np.nan); cur = None
    for t in range(N):
        if ms[t]:
            x = sg[t]
            if np.isfinite(x) and x > 0:
                w = min(1.0, (s / 100.0) / x)
                cur = (np.array([1.0 - w, w]) if v == "a" else np.array([0.0, w]), w)
        if cur is not None:
            W[t] = cur[0]; wv[t] = cur[1]
    return W, wv


def setup():
    A.assert_pinned()
    M = A.load_market()
    er = pd.read_csv(K.p_new("macro", "etf_expense_ratios.csv"))
    sec = er[er["source_type"].str.startswith("SEC")].drop_duplicates("ticker", keep="first").set_index("ticker")
    fees = {"": {k: float(sec.loc[k, "net_er"]) / 100 for k in LEVS}, "_g": {k: float(sec.loc[k, "gross_er"]) / 100 for k in LEVS},
            "_A1": dict(A.FEE)}
    old = dict(A.FEE)
    for tag, fee in fees.items():
        A.FEE = fee
        for k in LEVS:
            M["O"][f"SYN{tag}_{k}"], M["C"][f"SYN{tag}_{k}"] = A.synth(M, k, A.SPREAD)
    A.FEE = old
    M["fees"] = fees; M["fee_asof"] = {k: str(sec.loc[k, "asof"]) for k in LEVS}
    return M


def sigmas(M, tag=""):
    cal = M["cal"]; N = len(cal); e0 = M["pos"]["2007-04-02"]
    LF.ANN = A.ANN
    G = {"cal": cal, "C": {"0050": M["C"]["J"], "SSO": M["C"]["SSO"], "QLD": M["C"]["QLD"],
                           "SYN_SSO": M["C"][f"SYN{tag}_SSO"], "SYN_QLD": M["C"][f"SYN{tag}_QLD"]}}
    I = LF.indicators(G)
    SGM = {}
    for lev in LEVS:
        for L in LS:
            syn = LF.lev_sigma(G, "SYN_" + lev, L); real = LF.lev_sigma(G, lev, L)
            SGM[(lev, L)] = np.where(np.arange(N) < e0, syn, real)
    lev_of = {k: np.array(["SYN_" + k] * e0 + [k] * (N - e0), object) for k in LEVS}
    return G, I, SGM, lev_of


def first_ms_after(ms, i):
    j = np.flatnonzero(ms & (np.arange(len(ms)) > i))
    return int(j[0])


def run_cell(M, assets, W, i0, i1, early, cost=A.COST, R=None):
    r = A1.run_assets(M, assets, W, i0, i1, early=early, cost=cost, R=R)
    c, m = A.perf(r["eq"])
    return r, c, m


def _fake_one(args):
    seg, lev, v, i0, i1, early, seqd, seqw, reps, seed = args
    M = _M["M"]; rng = np.random.default_rng(seed); out = []
    n = i1 - i0 + 1
    for _ in range(reps):
        ww = rng.permutation(seqw)
        W2 = np.zeros((n, 2))
        for q, d0 in enumerate(seqd):
            w = ww[q]; W2[d0:] = np.array([1.0 - w, w]) if v == "a" else np.array([0.0, w])
        r = A1.run_assets(M, ("SPY", lev), W2, i0, i1, early=early)
        out.append(A.perf(r["eq"]))
    return out


def comps(good):
    """good：dict (s, L) → bool ⇒ 最大相連塊（上下左右）。"""
    seen = set(); best = 0
    for k, g in good.items():
        if not g or k in seen:
            continue
        stack = [k]; seen.add(k); sz = 0
        while stack:
            s, L = stack.pop(); sz += 1
            si, li = SIG.index(s), LS.index(L)
            for ds, dl in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = si + ds, li + dl
                if 0 <= a < len(SIG) and 0 <= b < len(LS):
                    nb = (SIG[a], LS[b])
                    if good.get(nb) and nb not in seen:
                        seen.add(nb); stack.append(nb)
        best = max(best, sz)
    return best


def run(a):
    T0 = time.time()
    M = setup(); cal = M["cal"]; N = len(cal); P = M["pos"]
    G, I, SGM, lev_of = sigmas(M)
    MS = {k: masks(cal, k) for k in ("M", "W", "Q")}
    ms_lf = np.zeros(N, bool); ms_lf[1:] = I["me"][:-1]
    # ── 閘 ①：每月權重 ＝ LF.W_yi ──
    Wy, wy = LF.W_yi(I, G, N, ORIG[0], ORIG[1], ORIG[2], lev_of[ORIG[3]])
    Wm, wm = W_vt(ms_lf, SGM[(ORIG[3], ORIG[1])], ORIG[0], ORIG[2])
    gate1 = bool(np.allclose(np.nan_to_num(Wy, nan=-9), np.nan_to_num(Wm, nan=-9), atol=1e-12, rtol=0))
    # ── 段 ──
    E1 = P[A.EARLY_END]
    st = {}
    for lev in LEVS:
        need = int(np.flatnonzero(np.isfinite(SGM[(lev, 120)]))[0])
        st[lev] = first_ms_after(ms_lf, need)
    SEG = {lev: {"早年合成": (st[lev], E1), "真實一": (P["2007-04-02"], P["2021-12-31"]), "真實二": (P["2022-01-03"], P["2026-09-30"])} for lev in LEVS}
    # ── 閘 ②③：A1 重現 ──
    import json
    a2 = json.load(open(os.path.join(A.OUT, "A2_summary.json"), encoding="utf-8"))["判定"]["乙"]
    lev0 = ORIG[3]
    _, c_x, _ = run_cell(M, ("SPY", lev0), Wm, P[A.EXP[0]], P[A.EXP[1]], False)
    _, c_c, _ = run_cell(M, ("SPY", lev0), Wm, P[A.CONF[0]], P[A.CONF[1]], False)
    G1, I1, SGM1, _ = sigmas(M, "_A1")
    Wm1, _ = W_vt(ms_lf, SGM1[(lev0, 20)], 40, "b")
    M_save = (M["O"]["SYN_QLD"], M["C"]["SYN_QLD"])
    M["O"]["SYN_QLD"], M["C"]["SYN_QLD"] = M["O"]["SYN_A1_QLD"], M["C"]["SYN_A1_QLD"]
    _, c_e1, _ = run_cell(M, ("SPY", lev0), Wm1, P[a2["早年"]["起"]], E1, True)
    M["O"]["SYN_QLD"], M["C"]["SYN_QLD"] = M_save
    gate = {"①每月權重＝LF.W_yi": gate1, "②真實一年化（本次／A1）": [c_x, a2["探索"]["年化"]], "②真實二年化（本次／A1）": [c_c, a2["確認"]["年化"]],
            "③早年（A1 費用率＋A1 起點）年化（本次／A1）": [c_e1, a2["早年"]["年化"]]}
    ok = gate1 and abs(c_x - a2["探索"]["年化"]) < 1e-9 and abs(c_c - a2["確認"]["年化"]) < 1e-9 and abs(c_e1 - a2["早年"]["年化"]) < 1e-9
    gate["通過"] = ok
    K.log("[C8] 閘 %s" % json.dumps(gate, ensure_ascii=False, default=float), "c8.log")
    if not ok:
        K.jdump({"⛔": "閘不過", "閘": gate}, "C8_gate_fail.json")
        raise SystemExit("C8 閘不過")
    # ── 基準 ──
    BASE = {}
    for lev in LEVS:
        for sg, (i0, i1) in SEG[lev].items():
            h = A1.hold_one(M, lev, i0, i1, early=(sg == "早年合成"))
            BASE[(lev, sg)] = {"一直抱正2": {"年化": h["年化"], "回落": h["回落"], "比值": h["比值"]}, "TR": A1.bench_all(M, i0, i1),
                               "SPY": {k: v for k, v in A1.hold_one(M, "SPY", i0, i1, early=(sg == "早年合成")).items() if k != "_eq"},
                               "起": cal[i0], "迄": cal[i1]}
    # ── 112 格 × 3 段（每月主＋每週、每季描述＋同平均槓桿固定比例）──
    rows = []; WV = {}
    for s, L, v, lev in product(SIG, LS, RESTS, LEVS):
        Wd_ = {}
        for fq in ("M", "W", "Q"):
            ms = ms_lf if fq == "M" else MS[fq]
            Wd_[fq] = W_vt(ms, SGM[(lev, L)], s, v)
        WV[(s, L, v, lev)] = Wd_["M"][1]
        for sg, (i0, i1) in SEG[lev].items():
            early = sg == "早年合成"; n = i1 - i0 + 1; yrs = n / A.ANN
            Bx = BASE[(lev, sg)]
            x = {"格": cname(s, L, v, lev), "σ*": s, "L": L, "其餘": "SPY" if v == "a" else "國庫券", "正2": lev, "段": sg, "起": cal[i0], "迄": cal[i1]}
            for fq in ("M", "W", "Q"):
                W, wv = Wd_[fq]
                r, c, m = run_cell(M, ("SPY", lev), W, i0, i1, early)
                good = bool(c >= Bx["一直抱正2"]["年化"] and m > Bx["一直抱正2"]["回落"])
                if fq == "M":
                    wseg = wv[i0:i1 + 1]
                    x.update({"年化": c, "回落": m, "比值": A.ratio(c, m), "平均w": float(np.nanmean(wseg)), "窗尾w": float(wseg[-1]),
                              "每年換手": float(r["turn"].sum()) / yrs, "成本／年": float(np.sum(r["cst"][1:] / np.r_[1.0, r["eq"][:-2]])) / yrs,
                              "對^SP500TR（描述）": A.label(c, m, Bx["TR"]["年化"], Bx["TR"]["回落"]), "好格": good,
                              "比一直抱正2（點）": (c - Bx["一直抱正2"]["年化"]) * 100, "回本交易日": A.dd_info(r["eq"], cal, i0)["回到高點的交易日數"]})
                    for ck, (d0, d1) in CRASH.items():
                        if P[d0] >= i0 and P[d1] <= i1:
                            x[f"大跌{ck}平均w"] = float(np.nanmean(wv[P[d0]:P[d1] + 1]))
                    wbar = float(np.nanmean(wseg))
                    Wf = np.tile(np.array([1.0 - wbar, wbar]) if v == "a" else np.array([0.0, wbar]), (n, 1))
                    rf, cf, mf = run_cell(M, ("SPY", lev), Wf, i0, i1, early, R=A.reb_mask(cal, i0, i1, "M"))
                    x.update({"固定同槓桿_年化": cf, "固定同槓桿_回落": mf, "看波動贏固定": bool(c > cf and A.ratio(c, m) >= A.ratio(cf, mf))})
                else:
                    x.update({f"{fq}_年化": c, f"{fq}_回落": m, f"{fq}_好格": good})
            rows.append(x)
    df = pd.DataFrame(rows)
    K.log("[C8] 112 格 × 3 段 %.0fs" % (time.time() - T0), "c8.log")
    # ── 高原判讀（C8-6）──
    PL = {}
    for sg in SEGN:
        d = df[df["段"] == sg]
        f = float(d["好格"].mean())
        big = 0
        for v, lev in product(RESTS, LEVS):
            g = {(r["σ*"], r["L"]): bool(r["好格"]) for _, r in d[(d["其餘"] == ("SPY" if v == "a" else "國庫券")) & (d["正2"] == lev)].iterrows()}
            big = max(big, comps(g))
        st_ = "站得住" if f >= 0.70 else ("只是那一格" if (f < 0.30 or big <= 1) else "中間")
        PL[sg] = {"好格比例": f, "好格數": int(d["好格"].sum()), "格數": int(len(d)), "最大相連好格塊": int(big), "讀法": st_,
                  "SSO好格比例": float(d[d["正2"] == "SSO"]["好格"].mean()), "QLD好格比例": float(d[d["正2"] == "QLD"]["好格"].mean()),
                  "每週版好格比例": float(d["W_好格"].mean()), "每季版好格比例": float(d["Q_好格"].mean()),
                  "看波動贏固定同槓桿比例（全部格）": float(d["看波動贏固定"].mean()),
                  "看波動贏固定同槓桿比例（好格中）": float(d[d["好格"]]["看波動贏固定"].mean()) if d["好格"].any() else None,
                  "對^SP500TR合格格數（描述）": int((d["對^SP500TR（描述）"] == "合格").sum()), "平均w中位": float(d["平均w"].median()),
                  **{f"大跌{ck}平均w（格中位）": float(d[f"大跌{ck}平均w"].median()) for ck in CRASH if f"大跌{ck}平均w" in d}}
    ss = [sg for sg in SEGN if PL[sg]["讀法"] == "站得住"]
    if len(ss) == 3:
        verdict = "站得住"
    elif ss:
        verdict = "看段：只在" + "、".join(ss) + "有用"
    elif all(PL[sg]["讀法"] == "只是那一格" for sg in SEGN):
        verdict = "只是那一格"
    else:
        verdict = "中間（不是一大片、也不只一格）"
    # ── 原格 ──
    oc = cname(*ORIG)
    OR = {sg: df[(df["格"] == oc) & (df["段"] == sg)].iloc[0].to_dict() for sg in SEGN}
    # ── 假訊號（C8-7）──
    _M["M"] = M
    jobs = []
    lev = ORIG[3]; wv0 = WV[ORIG]
    for k_, sg in enumerate(SEGN):
        i0, i1 = SEG[lev][sg]
        rd = [0] + [t - i0 for t in range(i0 + 1, i1 + 1) if ms_lf[t] and np.isfinite(wv0[t])]
        seqw = np.array([wv0[i0 + d] for d in rd])
        for part in range(10):
            jobs.append((sg, lev, ORIG[2], i0, i1, sg == "早年合成", rd, seqw, 100, [20261010, 8, k_, part]))
    with Pool(a.procs) as pool:
        res = pool.map(_fake_one, jobs)
    FK = {}
    for sg in SEGN:
        rr = [x for (j, out) in zip(jobs, res) if j[0] == sg for x in out]
        cg = np.array([x[0] for x in rr]); mg = np.array([x[1] for x in rr])
        Bx = BASE[(lev, sg)]["一直抱正2"]
        FK[sg] = {"次數": len(rr), "調整次數": int(len([j for j in jobs if j[0] == sg][0][6])), "隨機年化中位": float(np.median(cg)),
                  "p（隨機年化 ≥ 原格）": float(np.mean(cg >= OR[sg]["年化"])), "隨機也是好格比例": float(np.mean((cg >= Bx["年化"]) & (mg > Bx["回落"])))}
    K.log("[C8] 假訊號 %.0fs" % (time.time() - T0), "c8.log")
    # ── 早年費用率敏感度（描述）──
    FEE_D = {}
    for tag in ("_g", "_A1"):
        Gx, Ix, SGx, _ = sigmas(M, tag)
        sv = {k: (M["O"][f"SYN_{k}"], M["C"][f"SYN_{k}"]) for k in LEVS}
        for k in LEVS:
            M["O"][f"SYN_{k}"], M["C"][f"SYN_{k}"] = M["O"][f"SYN{tag}_{k}"], M["C"][f"SYN{tag}_{k}"]
        good = []
        for s, L, v, lv in product(SIG, LS, RESTS, LEVS):
            i0, i1 = SEG[lv]["早年合成"]
            W, _ = W_vt(ms_lf, SGx[(lv, L)], s, v)
            _, c, m = run_cell(M, ("SPY", lv), W, i0, i1, True)
            h = A1.hold_one(M, lv, i0, i1, early=True)
            good.append(bool(c >= h["年化"] and m > h["回落"]))
            if (s, L, v, lv) == ORIG:
                FEE_D[f"原格早年年化{tag}"] = c; FEE_D[f"一直抱合成QLD早年年化{tag}"] = h["年化"]
        FEE_D[f"早年好格比例{tag}"] = float(np.mean(good))
        for k in LEVS:
            M["O"][f"SYN_{k}"], M["C"][f"SYN_{k}"] = sv[k]
    # ── 合成對帳（重疊期，描述）──
    rec = {}
    for k in LEVS:
        a0 = int(np.flatnonzero(np.isfinite(M["C"][k]))[0]) + 1; b0 = P["2026-09-30"]
        cr, _ = A.bench(M["C"][k], a0, b0); cs, _ = A.bench(M["C"]["SYN_" + k], a0, b0)
        rec[k] = {"重疊期": [cal[a0], cal[b0]], "真實年化": cr, "合成年化": cs, "合成−真實（點）": (cs - cr) * 100}
    # ── 前瞻（C8-10）──
    q = M["C"]["QLD"][:P["2026-09-30"] + 1]; q = q[np.isfinite(q)]
    rq = q[1:] / q[:-1] - 1
    sg20 = float(np.std(rq[-20:], ddof=1) * np.sqrt(A.ANN))
    fw = {"格": oc, "依據": "2026-09-30 以前 20 根 QLD 日報酬", "σ̂": sg20, "2026-10 建議 QLD 比例": min(1.0, 0.40 / sg20), "其餘": "國庫券",
          "說明": "之後逐月記錄由美股策略線做；⛔ 不改規則"}
    # ── 先驗（C8-11）──
    pri = [{"先驗": "真實一段站得住（約六成）", "結果": PL["真實一"]["讀法"], "對": PL["真實一"]["讀法"] == "站得住"},
           {"先驗": "早年合成段站得住（約五成五）", "結果": PL["早年合成"]["讀法"], "對": PL["早年合成"]["讀法"] == "站得住"},
           {"先驗": "對同平均槓桿固定比例也贏（約五成）", "結果": f"原格：" + "、".join(f"{sg} {'贏' if OR[sg]['看波動贏固定'] else '沒贏'}" for sg in SEGN),
            "對": all(OR[sg]["看波動贏固定"] for sg in SEGN)},
           {"先驗": "三段都站得住（約三成五）", "結果": verdict, "對": verdict == "站得住"}]
    def pc(x):
        return f"{x * 100:+.1f}%"
    segtxt = "；".join(f"{sg}（{PL[sg]['好格數']}／{PL[sg]['格數']} 格好、{PL[sg]['讀法']}）" for sg in SEGN)
    sent = (f"波動目標（依正2 波動調整比例）112 格參數高原：{segtxt} ⇒ 總讀法「{verdict}」。"
            f"原格 s40_L20 QLD＋國庫券：早年合成 {pc(OR['早年合成']['年化'])}（一直抱合成 QLD {pc(BASE[('QLD', '早年合成')]['一直抱正2']['年化'])}）、"
            f"真實一 {pc(OR['真實一']['年化'])}（{pc(BASE[('QLD', '真實一')]['一直抱正2']['年化'])}）、真實二 {pc(OR['真實二']['年化'])}（{pc(BASE[('QLD', '真實二')]['一直抱正2']['年化'])}）；"
            f"假訊號 p（隨機排 w ≥ 原格）：" + "、".join(f"{sg} {FK[sg]['p（隨機年化 ≥ 原格）']:.0%}" for sg in SEGN) + "。"
            "⚠ 事後追加、不計 N、不判合格" + ("；站得住 ⇒ 暫定、需前瞻再驗" if verdict == "站得住" else "") + "；早年段是合成、非實際 ETF。")
    card = {"件": "C8", "名稱": "波動目標穩健性（A1-2 乙 參數高原＋分段＋前瞻）", "登錄": f"USREG-B8 seq1 sha {K.REG['C8'][1]}（→ C8）", "裁定": K.RULING,
            "N": "不計（事後追加）", "標籤": f"不判合格；高原讀法：{verdict}", "三欄": "不適用（ETF 層）",
            "條件出場必報": {"說明": "權重型（每月依 σ̂ 調整、w 永遠 ＞ 0）⇒ 無進出場；窗尾 2026-09-30 原格 w", "窗尾w": OR["真實二"]["窗尾w"]},
            "結果句": sent, "偏離": ["早年段起點用 L＝120 可算後第一個月初（同段 56 格共用；A1 原格 L＝20 起點 1999-07-01 只用在閘 ③）",
                                     "早年合成費用率改用資料庫 etf_expense_ratios.csv（SEC 497K 淨費用率），與 A1 的 0.89%／0.95% 不同（兩版都報）",
                                     "每週版的「每週第一個交易日」用 ISO 週"],
            "補讀法": [f"C8-1～C8-11（researchUSC_c8.py docstring，{READ_TS} 寫死）", f"K1～K11（researchUSC.py，{K.READ_TS}）"],
            "相對門檻（seq321 §五）": "σ* 是固定值網格（登錄寫明理由：A1-2 乙 原格與鄰格）；照報"}
    out = {"卡片": card, "閘": gate, "費用率（SEC 497K）": {"淨": M["fees"][""], "毛": M["fees"]["_g"], "A1原": M["fees"]["_A1"], "asof": M["fee_asof"]},
           "段": {lev: {sg: [cal[i0], cal[i1]] for sg, (i0, i1) in SEG[lev].items()} for lev in LEVS},
           "基準": {f"{k[0]}|{k[1]}": v for k, v in BASE.items()}, "高原": PL, "總讀法": verdict, "原格": OR, "假訊號": FK,
           "早年費用率敏感度": FEE_D, "合成對帳": rec, "前瞻": fw, "先驗": pri, "資料": {"A1快照": A.data_commit(), "費用率": K.NEW_COMMIT},
           "算於": K.now_tpe(), "秒": round(time.time() - T0)}
    df.to_csv(os.path.join(K.OUT, "C8_cells.csv"), index=False, encoding="utf-8", float_format="%.6g")
    K.jdump(out, "C8.json")
    K.log("[C8] 讀法 %s｜%s" % (verdict, {sg: PL[sg]["好格比例"] for sg in SEGN}), "c8.log")
    return out
