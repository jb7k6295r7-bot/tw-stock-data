# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 持有中只看「真頂訊號」賣出，真頂從【起漲點】起算（使用者 2026-10-06：「在持有過程中出現真頂訊號賣出（只有限定真頂喔），
真頂計算要從起漲點算起，不是持股買入時間喔，沒有真頂訊號就按照正式指標規劃賣出！」；參考，⛔ 不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_truetopT [--check | --page]

═══ 讀法（寫死於 2026-10-06 04:35（台北），在算任何數字之前）═══
 U1 本體、閘、組合層：整套沿用 backtest/researchYL_truetop.py（⇒ researchYL_flowexit F1／F5；ctx ＝ researchT1fix.build_ctx(True)）
    營量 v1 ＝ H60、20 槽、relvol 挑（r0；另核 r1 ＝ r0）；營飆 v1 ＝ H120、10 槽、抽籤 r ＝ 0～199；成本、名額、抽籤、停止交易強制出場、壞根全照正式引擎與 truetop
    閘 ① A 年化、回落（主窗）與 resultsT1fix/seeds.csv.gz repr 逐位元相同；閘 ② A 走 held_map ＝ A（營量 r0、營飆 r0～4）；閘 ③ 營量 r0 A 買進列 ＝ resultsYLlist/audit_seed0
    母體 ＝ 正式本體母體（照 truetop 原口徑，⛔ 不開 universe_gate.set_gate_v2；開了本體 A 會和正式不一致）
 U2 起漲點 t（point-in-time）：持有中每個訊號日 d，只用 d 收盤含以前的資料，逐字照 surge_flow_daily.replay 的錨點（資料日 T ＝ d、買進日 ＝ 進場日 e）：
      t ＝ anchor_of(c, d)（d 往前 250 個交易日內最高收盤之前的最低收盤日）；e ＜ t ⇒ t ＝ anchor_of(c, e)；
      t 起的漲勢在買進日 e 之前已從最高回落 30% 結束（第一個 c ≤ 0.7 × t 起最高收盤的日子 ＜ e）⇒ t 改用「結束日～e 最低收盤日」，重複（最多 50 次）
    價格 ＝ 引擎還原收盤（ctx closes，ffill）；--check 對幾檔逐日直接呼叫 surge_flow_daily.replay 比起漲點
 U3 T1 真頂訊號（主版）＝ W2，從 t 起算（d 收盤可判）：
      W2a 再次進入處置 ＝ d 是處置起日，且 [t, d−1] 內已有 ≥ 1 次處置起日（＝ researchSurge6_topwarn「W2a 再次進入處置（從t起版）」：START ∧ prv ≥ 1 ∧ NEAR ∧ bar）
      W2b 處置出關 ＝ d 是處置迄日的下一個交易日（同既有定義，不另加 t 條件）
      兩者都要 NEAR（收盤 ≥ 含當天 20 根有效 K 棒最高收盤 × 0.9）∧ 有效 K 棒；處置表、K 棒、NEAR 同 flowexit.surge_signals（飆股資料 MAIN 處置表、stitch 價格），依日期對到引擎日曆
      進場前的處置也算進「[t, d−1] 已有幾次起日」；訊號本身只看持有期間 e ≤ d ＜ xf（xf ＝ 正式出場日：營量第 60、營飆第 120 個交易日收盤）
      ⇒ 第一個訊號日 d 之後第一個有效開盤賣全部；與正式收盤比取較早者（同一天 ⇒ 開盤早於收盤）；沒訊號 ⇒ 照正式
      ⛔ 沒有 W1、⛔ 不分 3 成／7 成、⛔ 沒有 40 天規則、⛔ 不延長
 U4 T2 真頂分數版：researchSurge6_topjudge T5 當下可用版 —— features_used.csv 的 30 個特徵（飆股 Q 表「欄 ＝ 碼」，沒值 ＝ 沒有）同時有幾個 ＝ 分數，
      m* ＝ topjudge meta「m*／創新高日」（不重挑）；訊號日 ＝ 創新高日（c[d] ＞ [t, d−1] 最高收盤，t ＝ U2 的 t(d)；d ＝ t 不算）且分數 ≥ m*
      空值收盤（未上市的日子）在 [t, d−1] 最高收盤裡略過；其他同 T1（只看持有期間、隔天開盤全賣、與正式比取早）
 U5 T3 ＝ T1 ∪ T2（同日任一即訊號）
 U6 F 假訊號臂（描述「提早賣」本身的效果，⛔ 不挑版本用）：每個策略各自以候選列算 T1 實際提早賣的比例 p 與「訊號日 − 進場日」（引擎日曆位置差）的分布 K；
      每次抽：每列候選依序 u ～ U(0,1)，u ＜ p ⇒ 從 K 中「＜ xf − e」的值等機率抽一個 k，假訊號日 ＝ e ＋ k ⇒ 同 T1 的賣法（隔天第一個有效開盤、與正式比取早）
      種子 ＝ default_rng(20261006 ＋ 1000 × 策略序 ＋ 抽次)；營量 200 抽（都配組合種子 r0）；營飆 200 抽、第 r 抽配組合種子 r
 U7 組合層：同 truetop T4；分期 ＝ 同一條權益曲線切窗：全部（主窗 2017-03-02～2026-08-24）、2021-01～2023-12（主判）、2024-01～2026-08-24（只當對照）
      營量 1 顆（F 為 200 抽）；營飆 200 顆 ⇒ 中位、p10～p90、同顆對 A 差的中位、「年化贏 A 的顆數比例」
 U8 逐筆（同一批進場 ＝ A 的實際交易：營量 r0；營飆 200 顆合併、出現幾次算幾次；F 為各抽次合併）：筆數、平均、中位、勝率、平均持有天數、觸發比例；分期依進場日
    觸發時距真頂（事後已知，⛔ 僅描述）：真頂 P* ＝ 從 t(e) 起最高收盤，結束 ＝ e 以後第一個 c ≤ 0.7 × [t(e), d] 最高收盤（沒有 ⇒ 資料尾、未完）；
      報賣出日 − P*（有效 K 棒數）、賣在 P* 以前（含當天開盤）比例、離 P* 5 根以內比例、賣價 ÷ c[P*] − 1、吃到真頂幾成 ＝（賣價 − 買價）÷（c[P*] − 買價）（c[P*] ＞ 買價者）
 U9 查核（--check）：(a) 抽 8 筆 A 交易，持有期間逐日直接呼叫 surge_flow_daily.replay（price_dir ＝ 引擎快照）取起漲點 ⇒ 與本檔 anchor_pit 0 不同；replay 價格 ＝ 引擎價格；
    (b) A 交易（營量＋營飆去重）抽 50 筆（random_state 20261006），逐日迴圈從頭重算起漲點、W2a／W2b（處置表逐筆）、創新高與分數（Q 表逐特徵）、
        T1／T2／T3／F（第 0 抽）出場日與報酬、壞根、停止交易 ⇒ 0 不同才算過；並附 U1 的閘
輸出 backtest/resultsYL_truetopT/（逐筆大檔不進 repo：~/ttwork/truetopT/）
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR
from backtest import researchYL_flowexit as FX0
from backtest import researchYL_truetop as TT

TIME = "2026-10-06 04:35（台北）"
OUT = os.environ.get("TTT_OUT", "backtest/resultsYL_truetopT")
WORKX = os.path.expanduser(os.environ.get("TTT_WORK", "~/ttwork/truetopT"))
COST = R.COST
VARS = ("A", "T1", "T2", "T3", "F")
VT = ("T1", "T2", "T3")
VNAME = {"A": "正式（不提早賣）", "T1": "T1 真頂訊號（處置 W2，從起漲點算）", "T2": "T2 真頂分數（創新高日分數≥門檻）", "T3": "T3 T1＋T2 任一", "F": "假訊號（隨機挑一天提早賣）"}
STR = FX0.STR
SEGS = FX0.SEGS
NYF = int(os.environ.get("TTT_NYF", 200))
NF = int(os.environ.get("TTT_NF", 200))
TJ = "backtest/resultsSurge6/topjudge"


# ═════════════ 起漲點（逐字照 surge_flow_daily.replay）═════════════
def anchor_of(c, T):
    """資料日（或買進日）T 往前 250 個交易日內，最高收盤之前的最低收盤日。（surge_flow_daily.anchor_of 逐字）"""
    lo = max(T - 249, 0); P0 = lo + int(np.argmax(c[lo:T + 1]))
    return lo + int(np.argmin(c[lo:P0 + 1]))


def anchor_pit(c, T, eb_):
    """資料日 T、買進日 eb_ ⇒ replay 的起漲點 t（anchor 未指定那段逐字）。"""
    t = anchor_of(c, T)
    if eb_ < t:
        t = anchor_of(c, eb_)
    for _ in range(50):
        rm_ = np.maximum.accumulate(c[t:T + 1]); w_ = np.flatnonzero(c[t:T + 1] <= rm_ * 0.7)
        st_ = t + int(w_[0]) if len(w_) else None
        if st_ is None or st_ >= eb_:
            break
        t = st_ + int(np.argmin(c[st_:eb_ + 1]))
    return t


def true_top(c, t, e, n0):
    """U8：⇒ (P*, 結束日, 是否結束)。"""
    seg = c[t:n0]; rm = np.fmax.accumulate(seg)
    with np.errstate(invalid="ignore"):
        w = np.flatnonzero(seg <= rm * 0.7)
    w = w[t + w >= e]
    end = t + int(w[0]) if len(w) else n0 - 1
    return t + int(np.nanargmax(c[t:end + 1])), end, int(len(w) > 0)


# ═════════════ 飆股資料：W2 元件與 T2 分數 ═════════════
def surge_world(sids, cal_e, log):
    """⇒ {sid: dict(NEAR, BAR, EXIT, START（引擎日曆長布林）, SCORE（int）, st（處置起日，飆股日曆位置）)}、gi、資訊。⚠ 會切 D.DATA，結束切回快照。"""
    from backtest import researchSurge5 as S5
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str)
    D.DATA = S5.ST; cal_s = D.load_calendar()
    bar = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r"); Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); FXQ = S5.FIX
    FS = pd.read_csv(os.path.join(TJ, "features_used.csv")); mstar = int(json.load(open(os.path.join(TJ, "meta.json"), encoding="utf-8"))["m*"]["創新高日"])
    _, DISP = S5.SF.att_disp(S5.MAIN, cal_s)
    s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    gi = cal_s.get_indexer(cal_e); ok = gi >= 0; n = len(cal_s); ne = len(cal_e)
    ine = np.zeros(n, bool); ine[gi[ok]] = True
    out = {}; miss = []; lost = 0
    for sid in sorted(sids):
        if sid not in s2i:
            miss.append(sid); continue
        s = s2i[sid]; st = D.load_stock(sid, uni.loc[s, "market"], cal_s)
        if st is None:
            miss.append(sid); continue
        bs = np.asarray(bar[s], bool); c0 = st.df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(c0) & bs)
        NEAR = np.zeros(n, bool)
        if len(idx) >= 25:
            cb = c0[idx]; mx20 = pd.Series(cb).rolling(20, min_periods=20).max().to_numpy(); NEAR[idx] = cb >= 0.9 * mx20
        iv = DISP.get(sid, []); START = np.zeros(n, bool); EXIT = np.zeros(n, bool)
        for a, b in iv:
            if 0 <= a < n:
                START[a] = True
            if 0 <= b + 1 < n:
                EXIT[b + 1] = True
        rg_ = np.zeros(n, bool); rg_[gi[ok].min():gi[ok].max() + 1] = True
        lost += int((START & ~ine & rg_).sum() + (EXIT & ~ine & rg_).sum())
        sc = np.zeros(n, np.int16)
        for col, code in zip(FS["欄"], FS["碼"]):
            sc += (np.asarray(Qm[FXQ[col], s]) == int(code))
        E = {}
        for k, v in (("NEAR", NEAR), ("BAR", bs), ("EXIT", EXIT), ("START", START), ("SCORE", sc)):
            a_ = np.zeros(ne, v.dtype); a_[ok] = v[gi[ok]]; E[k] = a_
        E["st"] = np.array(sorted(a for a, b in iv if 0 <= a < n), np.int64)
        out[sid] = E
    info = {"飆股日曆": [str(cal_s[0].date()), str(cal_s[-1].date())], "引擎日曆對不到的天數": int((~ok).sum()), "不在飆股母體的檔": miss,
            "處置起日／出關日落在引擎日曆範圍內、但不在引擎日曆的天數（這批檔）": lost, "T2 特徵數": int(len(FS)), "T2 m*": mstar}
    RR.use_snapshot()
    log(f"[飆股資料] {len(out)} 檔｜{info}")
    return out, gi, mstar, info


def signals_row(S, SW, gi, mstar, e, hi):
    """持有期間 [e, hi) 每天 ⇒ t(d)、T1（W2a、W2b）、T2 旗標。"""
    c = S["c"]; L = hi - e
    tt = np.array([anchor_pit(c, d, e) for d in range(e, hi)], np.int64) if L > 0 else np.zeros(0, np.int64)
    w2a = np.zeros(L, bool); w2b = np.zeros(L, bool); t2 = np.zeros(L, bool); nh = np.zeros(L, bool)
    if SW is not None and L > 0:
        ds = np.arange(e, hi); near = SW["NEAR"][ds] & SW["BAR"][ds]; st = SW["st"]
        prv = np.searchsorted(st, gi[ds], "left") - np.searchsorted(st, gi[tt], "left")
        w2a = SW["START"][ds] & (prv >= 1) & near; w2b = SW["EXIT"][ds] & near
        sc = SW["SCORE"][ds]
    for j in range(L):
        d = e + j; t = int(tt[j])
        if d > t:
            m = np.nanmax(c[t:d]) if np.isfinite(c[t:d]).any() else np.nan
            nh[j] = bool(np.isfinite(m) and c[d] > m)
    if SW is not None and L > 0:
        t2 = nh & (sc >= mstar)
    return tt, w2a, w2b, nh, t2


def early_exit(S, sigday, xf, n0):
    """第一個訊號日 ⇒ 次一有效開盤；與正式比取早。⇒ (出場元組, 是否提早)。"""
    nxo = TT.nxo_of(S, n0); pf = ("close", xf) if xf < n0 else ("end", None)
    tk = lambda p: 2 * p[1] + (1 if p[0] == "close" else 0) if p[0] != "end" else 2 * n0
    if sigday is None:
        return pf, 0
    x = nxo(sigday); p = ("open", x) if x is not None else ("end", None)
    return (p, 1) if tk(p) < tk(pf) else (pf, 0)


def bad_root(S, e):
    B = S["B"]; dbad = None
    if B is not None:
        idx = B["idx"]; kb = int(np.searchsorted(idx, e)) - 1; nbk = int(B["next_bad"][max(0, kb - 20)])
        if nbk < len(idx):
            dbad = int(idx[nbk - 1])
    return dbad


def build_variants(ctx, sig, rule, SWD, gi, mstar, SA, SF, n0, NP):
    rows = []; SCS = {v: {} for v in ("A",) + VT}
    for r in sig.itertuples(index=False):
        sid = r.sid; e = int(r.entry_pos); xf = int(getattr(r, f"xpos_{rule}")); gf = float(getattr(r, f"g_{rule}"))
        if xf < 0:
            continue
        S = SA[sid]; bp = FX0.engine_ep(ctx, sid, e); hi = min(xf, n0)
        tt, w2a, w2b, nh, t2 = signals_row(S, SWD.get(sid), gi, mstar, e, hi)
        t1 = w2a | w2b; t3 = t1 | t2
        first = {k: (e + int(np.flatnonzero(m)[0]) if m.any() else None) for k, m in (("T1", t1), ("T2", t2), ("T3", t3))}
        dbad = bad_root(S, e); L = SF.get(sid)
        te = anchor_pit(S["c"], e, e); Ps, endP, done = true_top(S["c"], te, e, n0)
        key = f"{sid}#{e}"
        base = {"sid": sid, "e": e, "key": key, "bp": bp, "xf": xf, "gf": gf, "dbad": -1 if dbad is None else dbad, "L": -1 if L is None else L,
                "t進場": te, "t變過": int(len(tt) > 0 and (tt != tt[0]).any()), "t最早": int(tt.min()) if len(tt) else te, "持有窗": hi - e,
                "P*": Ps, "P*結束": endP, "P*已結束": done, "cP*": float(S["c"][Ps]),
                "W2a天": int(w2a.sum()), "W2b天": int(w2b.sum()), "創新高天": int(nh.sum()), "T2天": int(t2.sum()),
                "T1由": "" if first["T1"] is None else ("W2a" if w2a[first["T1"] - e] else "W2b"),
                **{f"{k}訊號日": -1 if v is None else v for k, v in first.items()}, "無飆股資料": int(sid not in SWD)}
        pf = ("close", xf) if xf < n0 else ("end", None)
        for v in ("A",) + VT:
            if v == "A":
                Sc = np.asarray(ctx["closes"][sid], float)[:NP].copy()
                xa, ga, sf = xf, gf, 0
                if L is not None and xf > L + 1:
                    xa, ga, sf = L + 1, float(ctx["closes"][sid][L]) / bp - 1.0, 1
                d_ = int(S["cb"][L if sf else min(xf, n0 - 1)] - (S["cb"][e - 1] if e > 0 else 0))
                f = {"xpos": xa, "g": ga, "天": d_, "壞根截": 0, "停止交易": sf, "Sc": Sc}; ear = 0
            else:
                p, ear = early_exit(S, first[v], xf, n0)
                f = TT.finalize1(p, pf, bp, gf, e, S, n0, dbad, L, NP)
            SCS[v][key] = f.pop("Sc")
            base.update({f"{v}_{k}": val for k, val in f.items()}); base[f"{v}_早賣"] = ear
        rows.append(base)
    return pd.DataFrame(rows), SCS


def fake_draw(TR, SA, n0, NP, kpool, p, seed, bpk, need_sc=True):
    """U6 一抽 ⇒ DataFrame(xpos, g, 天, 早賣, 假訊號日, 壞根截, 停止交易)、SC。"""
    rng = np.random.default_rng(seed); out = []; SC = {}
    for r in TR.itertuples(index=False):
        e, xf = int(r.e), int(r.xf); u = rng.random(); d = None
        if u < p:
            ks = kpool[kpool < xf - e]
            if len(ks):
                d = e + int(ks[rng.integers(len(ks))])
        S = SA[r.sid]; pf = ("close", xf) if xf < n0 else ("end", None)
        pp, ear = early_exit(S, d, xf, n0)
        f = TT.finalize1(pp, pf, r.bp, r.gf, e, S, n0, None if r.dbad < 0 else int(r.dbad), None if r.L < 0 else int(r.L), NP)
        sc = f.pop("Sc")
        if need_sc:
            SC[r.key] = sc
        out.append({"xpos": f["xpos"], "g": f["g"], "天": f["天"], "早賣": ear, "假訊號日": -1 if d is None else d, "壞根截": f["壞根截"], "停止交易": f["停止交易"]})
    return pd.DataFrame(out), SC


# ═════════════ 主程式 ═════════════
def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORKX, exist_ok=True)
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); NP = ctx["ncal"]; w0, w1 = ctx["w0"], ctx["w1"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    SEGP = FX0.seg_pos(cal, w0, w1)
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
    gates = {}
    sids = sorted(set(ctx["sig13"]["sid"]) | set(ctx["sig"]["sid"]))
    SA = {s: FX0.stock_arrays(ctx, s, n0) for s in sids}
    log(f"[價格] {len(SA)} 檔")
    SWD, gi, mstar, sinfo = surge_world(sids, cal, log)
    TRS = {}; PR = []; ATR = {}; FDS = {}; FINFO = {}
    for si, (strat, cf) in enumerate(STR.items()):
        sig = ctx[cf["sig"]]; rule = cf["rule"]
        TR, SCS = build_variants(ctx, sig, rule, SWD, gi, mstar, SA, SF, n0, NP)
        TR.insert(0, "策略", strat); TRS[strat] = TR
        gates[f"{strat} 候選列（代號, 進場位置）不重複"] = bool(not TR.duplicated(["sid", "e"]).any())
        nosig = (TR["T1訊號日"] < 0) & (TR["A_停止交易"] == 0)
        gates[f"{strat} T1 沒訊號且沒壞根截的列 ＝ A（不同列數）"] = int(((TR.loc[nosig & (TR["T1_壞根截"] == 0), "T1_xpos"] != TR.loc[nosig & (TR["T1_壞根截"] == 0), "A_xpos"])).sum())
        # 假訊號：p、K
        trig = TR["T1_早賣"] == 1; p = float(trig.mean()); kpool = np.sort((TR.loc[trig, "T1訊號日"] - TR.loc[trig, "e"]).to_numpy(np.int64))
        FINFO[strat] = {"p（候選列 T1 提早賣比例）": p, "K 筆數": int(len(kpool)), "K 中位": float(np.median(kpool)) if len(kpool) else None,
                        "K p10～p90": [float(np.quantile(kpool, .1)), float(np.quantile(kpool, .9))] if len(kpool) else None}
        log(f"[{strat}] 候選 {len(TR)} 列｜T1 提早賣 {p:.3f}｜{time.time() - T0:.0f}s")
        seeds = [0, 1] if strat == "營量 v1" else list(range(NYF))
        keyed = {v: FX0.keyed_inputs(ctx, sig, rule, TR, v, SCS, SF) for v in ("A",) + VT}
        buys = []; FD = []
        for r in seeds:
            o, au = FX0.run_engine(ctx, strat, sig, rule, cf["N"], r, SF)
            row, eq = FX0.port_row(o, au, SEGP, w0, w1)
            key = "c13" if strat == "營量 v1" else "c1"
            rr = ref[(ref["key"] == key) & (ref["var"] == "t1") & (ref["r"] == r)].iloc[0]
            c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
            ok = repr(float(c_)) == repr(float(rr["cagr"])) and repr(float(m_)) == repr(float(rr["mdd"]))
            gates.setdefault(f"① {strat} A ＝ resultsT1fix（不同顆數）", 0); gates[f"① {strat} A ＝ resultsT1fix（不同顆數）"] += int(not ok)
            PR.append({"策略": strat, "出場": "A", "r": r, **row})
            b = pd.DataFrame([a for a in au if a["side"] == "buy"])[["t", "sid", "px"]]; b["r"] = r; buys.append(b)
            if r < (1 if strat == "營量 v1" else 5):
                s2, cl, op, SFk, hm = keyed["A"]
                o2, _ = FX0.run_engine(ctx, strat, s2, rule, cf["N"], r, SFk, cl, op, hm, audit=False)
                gates.setdefault(f"② {strat} A 走 held_map ＝ A（不同顆數）", 0)
                gates[f"② {strat} A 走 held_map ＝ A（不同顆數）"] += int(not np.array_equal(np.asarray(o2["equity"], float), eq))
            for v in VT:
                s2, cl, op, SFk, hm = keyed[v]
                o2, au2 = FX0.run_engine(ctx, strat, s2, rule, cf["N"], r, SFk, cl, op, hm)
                row2, _ = FX0.port_row(o2, au2, SEGP, w0, w1)
                PR.append({"策略": strat, "出場": v, "r": r, **row2})
            # 假訊號：營飆第 r 抽配種子 r；營量在 r0 跑 200 抽
            draws = range(NF) if strat == "營量 v1" and r == 0 else ([] if strat == "營量 v1" else [r])
            for k in draws:
                FDk, SCk = fake_draw(TR, SA, n0, NP, kpool, p, 20261006 + 1000 * si + k, None)
                TRF = TR[["sid", "e"]].copy(); TRF["F_xpos"] = FDk["xpos"].to_numpy(); TRF["F_g"] = FDk["g"].to_numpy()
                s2, cl, op, SFk, hm = FX0.keyed_inputs(ctx, sig, rule, TRF, "F", {"F": SCk}, SF)
                o2, au2 = FX0.run_engine(ctx, strat, s2, rule, cf["N"], r, SFk, cl, op, hm)
                row2, _ = FX0.port_row(o2, au2, SEGP, w0, w1)
                PR.append({"策略": strat, "出場": "F", "r": r, "抽": k, **row2})
                FDk.insert(0, "抽", k); FDk.insert(0, "e", TR["e"].to_numpy()); FDk.insert(0, "sid", TR["sid"].to_numpy()); FD.append(FDk)
                del SCk, cl
                if strat == "營量 v1" and k % 50 == 0:
                    log(f"[{strat}] 假訊號第 {k} 抽｜{time.time() - T0:.0f}s")
            if r % 50 == 0:
                log(f"[{strat}] r{r}｜{time.time() - T0:.0f}s")
        FDS[strat] = pd.concat(FD, ignore_index=True)
        BY = pd.concat(buys, ignore_index=True); BY["sid"] = BY["sid"].astype(str)
        if strat == "營量 v1":
            f0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str}); f0 = f0[f0["side"] == "buy"][["t", "sid"]].reset_index(drop=True)
            y0 = BY[BY["r"] == 0].reset_index(drop=True); y1 = BY[BY["r"] == 1].reset_index(drop=True)
            gates["③ 營量 r0 A 買進列 ＝ audit_seed0"] = bool(len(f0) == len(y0) and (f0["t"].to_numpy() == y0["t"].to_numpy()).all() and (f0["sid"].to_numpy() == y0["sid"].to_numpy()).all())
            gates["營量 r1 A 買進列 ＝ r0（不抽籤）"] = bool(len(y1) == len(y0) and (y1["t"].to_numpy() == y0["t"].to_numpy()).all() and (y1["sid"].to_numpy() == y0["sid"].to_numpy()).all())
            BY = y0.assign(r=0)
        ATR[strat] = BY
        del keyed, SCS
    PR = pd.DataFrame(PR); PR.to_csv(os.path.join(OUT, "portfolio_seeds.csv.gz"), index=False, float_format="%.10g")
    for v in ("A",) + VT:
        x = PR[(PR["策略"] == "營量 v1") & (PR["出場"] == v)]
        gates[f"營量 {v} r1 ＝ r0（年化回落）"] = bool(len(x) == 2 and all(x[f"{sg}_{k}"].nunique() == 1 for sg in SEGS for k in ("年化", "回落")))
    TRA = pd.concat(TRS.values(), ignore_index=True)
    TRA.to_csv(os.path.join(OUT, "signals_truetopT.csv.gz"), index=False, float_format="%.10g")
    FDA = pd.concat([d.assign(策略=s) for s, d in FDS.items()], ignore_index=True)
    FDA.to_csv(os.path.join(WORKX, "fake_draws.csv.gz"), index=False, float_format="%.10g")
    FDA[FDA["抽"] == 0].to_csv(os.path.join(OUT, "fake_draw0.csv.gz"), index=False, float_format="%.10g")
    # 逐筆：A 的實際交易
    P = []
    for strat, BY in ATR.items():
        T = TRS[strat].set_index(["sid", "e"])
        m = T.loc[list(zip(BY["sid"], BY["t"].astype(int)))].reset_index()
        m["r"] = BY["r"].to_numpy(); m["進場日"] = [str(cal[int(x)].date()) for x in m["e"]]
        gates[f"{strat} A 交易進場價 ＝ 引擎（不同筆數）"] = int((~np.isclose(m["bp"].to_numpy(float), BY["px"].to_numpy(float), rtol=1e-9)).sum())
        P.append(m)
    PT = pd.concat(P, ignore_index=True)
    for v in ("A",) + VT:
        PT[f"{v}_報酬"] = PT[f"{v}_g"] - COST
    gates["A 逐筆 g ＝ 正式 g（停止交易外，不同筆數）"] = int((PT.loc[PT["A_停止交易"] == 0, "A_g"] != PT.loc[PT["A_停止交易"] == 0, "gf"]).sum())
    PT.to_csv(os.path.join(WORKX, "trades_A_entries.csv.gz"), index=False, float_format="%.10g")
    # F 逐筆：營量 ＝ r0 交易 × 200 抽；營飆 ＝ 種子 r 的交易配第 r 抽
    PF = []
    for strat in STR:
        m = PT[PT["策略"] == strat][["策略", "sid", "e", "r", "進場日", "bp", "A_報酬", "A_天", "P*", "cP*", "dbad"]]
        fd = FDS[strat]
        if strat == "營量 v1":
            x = m.drop(columns="r").merge(fd, on=["sid", "e"], how="left")
        else:
            x = m.merge(fd.rename(columns={"抽": "r"}), on=["sid", "e", "r"], how="left"); x["抽"] = x["r"]
        gates[f"{strat} F 逐筆對得上（缺列數）"] = int(x["g"].isna().sum())
        x = x.rename(columns={"xpos": "F_xpos", "g": "F_g", "天": "F_天", "早賣": "F_早賣"}); x["F_報酬"] = x["F_g"] - COST
        PF.append(x)
    PF = pd.concat(PF, ignore_index=True)
    PF.to_csv(os.path.join(WORKX, "trades_F.csv.gz"), index=False, float_format="%.10g")
    ST = per_trade_summary(PT, PF, n0, ctx, SA); ST.to_csv(os.path.join(OUT, "summary_per_trade.csv"), index=False, float_format="%.6g")
    TG = trigger_summary(PT, PF, SA); TG.to_csv(os.path.join(OUT, "summary_trigger.csv"), index=False, float_format="%.6g")
    SP = port_summary(PR); SP.to_csv(os.path.join(OUT, "summary_portfolio.csv"), index=False, float_format="%.6g")
    PT.drop_duplicates(["策略", "sid", "e"]).to_csv(os.path.join(OUT, "trades_A_dedup.csv.gz"), index=False, float_format="%.10g")
    META = {"讀法寫死": TIME, "閘": gates, "飆股資料": sinfo, "假訊號": FINFO,
            "SEGP": {k: [str(cal[a].date()), str(cal[b].date())] for k, (a, b) in SEGP.items()},
            "候選列": {s: int(len(TRS[s])) for s in TRS}, "A 交易筆": {s: int(len(ATR[s])) for s in ATR},
            "營飆 A 去重筆": int(ATR["營飆 v1"][["sid", "t"]].drop_duplicates().shape[0]),
            "起漲點在持有中變過（候選列比例）": {s: float(TRS[s]["t變過"].mean()) for s in TRS},
            "起漲點落在空值收盤（候選列，進場時）": {s: int(sum(not np.isfinite(SA[a]["c"][b]) for a, b in zip(TRS[s]["sid"], TRS[s]["t進場"]))) for s in TRS},
            "壞根截（候選列）": {s: {v: int(TRS[s][f"{v}_壞根截"].sum()) for v in VT} for s in TRS}, "日曆尾": str(cal[-1].date()), "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {json.dumps(META, ensure_ascii=False, default=str)}")
    if not all(v is True or v == 0 for v in gates.values()):
        raise SystemExit(f"⛔ 閘不過 {gates}")


def _top_pos(m, v, SA, xcol, gcol):
    """觸發時距真頂（只對提早賣的筆）⇒ dict。"""
    if not len(m):
        return {}
    xp = m[xcol].to_numpy(np.int64); Ps = m["P*"].to_numpy(np.int64); sid = m["sid"].to_numpy()
    kb = np.array([int(SA[s]["cb"][min(x, len(SA[s]["cb"]) - 1)] - SA[s]["cb"][p]) for s, x, p in zip(sid, xp, Ps)])
    px = m["bp"].to_numpy(float) * (1 + m[gcol].to_numpy(float)); cp = m["cP*"].to_numpy(float); bp = m["bp"].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        cap = np.where(cp > bp, (px - bp) / (cp - bp), np.nan)
    return {f"{v} 賣出−真頂 中位（K棒）": float(np.median(kb)), f"{v} 賣在真頂以前": float(np.mean(xp <= Ps)), f"{v} 離真頂5根內": float(np.mean(np.abs(kb) <= 5)),
            f"{v} 賣價÷真頂−1 中位": float(np.median(px / cp - 1)), f"{v} 吃到真頂幾成 中位": float(np.nanmedian(cap)) if np.isfinite(cap).any() else np.nan}


def per_trade_summary(PT, PF, n0, ctx, SA):
    out = []
    for strat in STR:
        for dd in ((False, True) if strat == "營飆 v1" else (False,)):
            m0 = PT[PT["策略"] == strat]; f0 = PF[PF["策略"] == strat]
            if dd:
                m0 = m0.drop_duplicates(["sid", "e"]); f0 = f0.drop_duplicates(["sid", "e"])
            for sg, (a, b) in SEGS.items():
                m = m0[(m0["進場日"] >= a) & (m0["進場日"] <= b)]; f = f0[(f0["進場日"] >= a) & (f0["進場日"] <= b)]
                if not len(m):
                    continue
                for v in VARS:
                    src = f if v == "F" else m
                    x = src[f"{v}_報酬"]; d = src[f"{v}_天"]; ax = src["A_報酬"]
                    out.append({"策略": strat, "口徑": "去重" if dd else ("200 顆合併" if strat == "營飆 v1" else "r0"), "段": sg, "出場": v, "筆數": len(src),
                                "平均": x.mean(), "中位": x.median(), "勝率": (x > 0).mean(), "p10": x.quantile(.1), "p90": x.quantile(.9),
                                "平均持有天數": d.mean(), "觸發比例": src[f"{v}_早賣"].mean() if v != "A" else 0.0, "對A差平均": (x - ax).mean(),
                                "比A好比例": (x > ax + 1e-12).mean(), "比A差比例": (x < ax - 1e-12).mean()})
    return pd.DataFrame(out)


def trigger_summary(PT, PF, SA):
    out = []
    for strat in STR:
        m0 = PT[PT["策略"] == strat]; f0 = PF[PF["策略"] == strat]
        for sg, (a, b) in SEGS.items():
            m = m0[(m0["進場日"] >= a) & (m0["進場日"] <= b)]; f = f0[(f0["進場日"] >= a) & (f0["進場日"] <= b)]
            if not len(m):
                continue
            r = {"策略": strat, "段": sg, "筆數": len(m)}
            for v in VT:
                r[f"{v} 提早賣"] = m[f"{v}_早賣"].mean()
            r["F 提早賣"] = f["F_早賣"].mean()
            t1 = m[m["T1_早賣"] == 1]
            r["T1 由再次處置觸發"] = (t1["T1由"] == "W2a").mean() if len(t1) else np.nan
            r["T1 由出關觸發"] = (t1["T1由"] == "W2b").mean() if len(t1) else np.nan
            r["持有期間起漲點變過"] = m["t變過"].mean()
            r.update(_top_pos(m, "A", SA, "A_xpos", "A_g"))
            for v in VT:
                r.update(_top_pos(m[m[f"{v}_早賣"] == 1], v, SA, f"{v}_xpos", f"{v}_g"))
            r.update(_top_pos(f[f["F_早賣"] == 1], "F", SA, "F_xpos", "F_g"))
            out.append(r)
    return pd.DataFrame(out)


def port_summary(PR):
    out = []
    for strat in STR:
        a = PR[(PR["策略"] == strat) & (PR["出場"] == "A")].sort_values("r")
        if strat == "營量 v1":
            a = a[a["r"] == 0]
        for v in VARS:
            x = PR[(PR["策略"] == strat) & (PR["出場"] == v)].sort_values(["r", "抽"] if "抽" in PR else "r")
            if strat == "營量 v1" and v != "F":
                x = x[x["r"] == 0]
            for sg in SEGS:
                cg = x[f"{sg}_年化"].to_numpy(); md = x[f"{sg}_回落"].to_numpy()
                if strat == "營量 v1":
                    ac, am = float(a[f"{sg}_年化"].iloc[0]), float(a[f"{sg}_回落"].iloc[0])
                else:
                    ac = a.set_index("r").loc[x["r"].to_numpy(), f"{sg}_年化"].to_numpy(); am = a.set_index("r").loc[x["r"].to_numpy(), f"{sg}_回落"].to_numpy()
                dc = cg - ac; dm = md - am
                out.append({"策略": strat, "出場": v, "段": sg, "顆數": len(x), "年化 中位": np.median(cg), "年化 p10": np.quantile(cg, .1), "年化 p90": np.quantile(cg, .9),
                            "回落 中位": np.median(md), "回落 p10": np.quantile(md, .1), "回落 p90": np.quantile(md, .9),
                            "對A年化差 中位": np.median(dc), "對A回落差 中位": np.median(dm), "年化贏A比例": float(np.mean(dc > 1e-12)) if v != "A" else np.nan,
                            "回落比A淺比例": float(np.mean(dm > 1e-12)) if v != "A" else np.nan,
                            "買進筆 中位": float(x["買進筆"].median()), "平均持股 中位": float(x["平均持股"].median()), "平均持有日 中位": float(x["平均持有日"].median())})
    return pd.DataFrame(out)


# ═════════════ 查核 ═════════════
class _Got(Exception):
    pass


def check(log):
    from backtest import researchT1fix as T1
    from backtest import researchSurge5 as S5
    from backtest import surge_flow_daily as SFL
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); last = n0 - 1; NP = ctx["ncal"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), ctx["w1"])
    PT = pd.read_csv(os.path.join(OUT, "trades_A_dedup.csv.gz"), dtype={"sid": str})
    F0 = pd.read_csv(os.path.join(OUT, "fake_draw0.csv.gz"), dtype={"sid": str})
    out = {"讀法寫死": TIME}
    # ── (a) replay 起漲點（price_dir ＝ 引擎快照）
    H2D = D.DATA; SMA = PT.sample(8, random_state=20261006); cache = {}; real_ctx = SFL.stock_ctx; real_sig = SFL.signals_for
    def ctx_cached(code, mk, cal_, n_, price_dir, aux_dir, DISP, disp_row):
        if code not in cache:
            cache[code] = real_ctx(code, mk, cal_, n_, price_dir, aux_dir, DISP, disp_row)
        return cache[code]
    def grab(*a, **k):
        f = sys._getframe(1); raise _Got(int(f.f_locals["t"]))
    SFL.stock_ctx = ctx_cached; SFL.signals_for = grab
    na = 0; nd_a = 0; px_bad = 0; px_rel = 0.0; ex_a = []
    try:
        for r in SMA.itertuples():
            sid, e, xf = r.sid, int(r.e), int(r.xf); c = np.asarray(ctx["closes"][sid], float)[:n0]
            uni = pd.DataFrame({"stock_id": [sid], "market": [ctx["mk"].get(sid, "twse")]})
            for d in range(e, min(xf, n0)):
                Rr = {"cal": cal, "W": {"DISP": {}}, "uni": uni, "d0": 0, "d1": d}
                try:
                    SFL.replay(Rr, sid, str(cal[e].date()), 1.0, H2D, "/nonexistent_aux", names_bj=([], 0, {}))
                    raise RuntimeError("replay 沒走到 signals_for")
                except _Got as g:
                    tr = int(g.args[0])
                tm = anchor_pit(c, d, e); na += 1
                if tr != tm:
                    nd_a += 1; ex_a.append(f"{sid} e{e} d{d}: replay {tr} 本檔 {tm}")
            cc = cache[sid]["c"][:n0]
            ok_ = np.isfinite(cc) & np.isfinite(c); px_rel = max(px_rel, float(np.max(np.abs(c[ok_] / cc[ok_] - 1))) if ok_.any() else 0.0)
            px_bad += int((np.isfinite(cc) != np.isfinite(c)).any() or (ok_.any() and np.max(np.abs(c[ok_] / cc[ok_] - 1)) > 1e-6))
    finally:
        SFL.stock_ctx = real_ctx; SFL.signals_for = real_sig; RR.use_snapshot()
    out["(a) replay 起漲點"] = {"筆": len(SMA), "比對日數": na, "不同": nd_a, "例": ex_a[:5], "replay 價格與引擎價格相對差 ＞ 1e-6 的檔數": px_bad, "最大相對差（引擎價格存 float32）": px_rel}
    log(f"[查核 a] {out['(a) replay 起漲點']}")
    # ── (b) 逐日迴圈
    SMP = PT.sample(50, random_state=20261006)
    W, _ = S5.world(log)
    cal_s = W["cal"]; pos_s = {d: j for j, d in enumerate(cal_s)}
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    bar_s = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r"); Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); FXQ = S5.FIX
    FS = pd.read_csv(os.path.join(TJ, "features_used.csv")); mstar = int(json.load(open(os.path.join(TJ, "meta.json"), encoding="utf-8"))["m*"]["創新高日"])
    dsp = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    D.DATA = S5.ST; SURGE = {}
    for sid in sorted(set(SMP["sid"])):
        if sid not in s2i:
            SURGE[sid] = None; continue
        s = s2i[sid]; c0 = D.load_stock(sid, uni.loc[s, "market"], cal_s).df["close"].to_numpy(float)
        bars = [d for d in range(len(cal_s)) if np.isfinite(c0[d]) and bar_s[s, d]]; bpos = {d: j for j, d in enumerate(bars)}
        g = dsp[dsp["stock_id"] == sid]
        starts = sorted(int(cal_s.searchsorted(pd.Timestamp(x))) for x in g["start_date"])
        ends = [int(cal_s.searchsorted(pd.Timestamp(y), side="right")) - 1 for y in g["end_date"]]
        Q = {col: np.asarray(Qm[FXQ[col], s]) for col in FS["欄"]}
        SURGE[sid] = (c0, bars, bpos, starts, ends, Q)
    RR.use_snapshot()
    errs = []; nd = 0; cnt = {"T1早賣": 0, "T2早賣": 0, "T3早賣": 0, "F早賣": 0, "起漲點變過": 0}
    for r in SMP.itertuples():
        sid, e, xf, gf = r.sid, int(r.e), int(r.xf), float(r.gf); why = []
        B = R.load_bars(sid, ctx["mk"].get(sid, "twse"), cal)
        c = np.asarray(ctx["closes"][sid], float)[:n0]; o = np.asarray(ctx["opens"][sid], float)[:n0]
        isb = np.zeros(n0, bool); isb[B["idx"][B["idx"] < n0]] = True
        bp = float(o[e]) if np.isfinite(o[e]) and o[e] > 0 else float(c[e])

        def nxo(d):
            x = d + 1
            while x <= last and not (isb[x] and np.isfinite(o[x]) and o[x] > 0):
                x += 1
            return x if x <= last else None

        def anchor_loop(T, eb):
            def a_of(TT_):
                lo = max(TT_ - 249, 0); P0 = lo
                for d in range(lo, TT_ + 1):
                    if c[d] > c[P0] or (np.isnan(c[d]) and not np.isnan(c[P0])):
                        P0 = d
                    if np.isnan(c[P0]):
                        break
                t_ = lo
                for d in range(lo, P0 + 1):
                    if np.isnan(c[t_]):
                        break
                    if c[d] < c[t_] or np.isnan(c[d]):
                        t_ = d
                return t_
            t = a_of(T)
            if eb < t:
                t = a_of(eb)
            for _ in range(50):
                rm = -np.inf; st_ = None
                for d in range(t, T + 1):
                    rm = max(rm, c[d]) if not np.isnan(c[d]) and not np.isnan(rm) else np.nan
                    if not np.isnan(rm) and c[d] <= rm * 0.7:
                        st_ = d; break
                if st_ is None or st_ >= eb:
                    break
                m_ = st_
                for d in range(st_, eb + 1):
                    if c[d] < c[m_]:
                        m_ = d
                t = m_
            return t
        sg = SURGE[sid]; T1d = T2d = None; tset = set()
        for d in range(e, min(xf, n0)):
            t = anchor_loop(d, e); tset.add(t)
            hit1 = hit2 = False
            if sg is not None:
                c0, bars, bpos, starts, ends, Q = sg
                ds = pos_s.get(cal[d]); ts = pos_s.get(cal[t])
                if ds is not None and ds in bpos:
                    j = bpos[ds]
                    near = j >= 19 and c0[ds] >= 0.9 * max(c0[bars[j - 19:j + 1]])
                    w2a = ds in starts and any(ts <= x <= ds - 1 for x in starts)
                    w2b = any(ds == b + 1 for b in ends)
                    hit1 = near and (w2a or w2b)
                mx = -np.inf
                for k in range(t, d):
                    if np.isfinite(c[k]) and c[k] > mx:
                        mx = c[k]
                if d > t and mx > -np.inf and c[d] > mx and ds is not None:
                    sc = sum(int(Q[col][ds] == int(code)) for col, code in zip(FS["欄"], FS["碼"]))
                    hit2 = sc >= mstar
            if hit1 and T1d is None:
                T1d = d
            if hit2 and T2d is None:
                T2d = d
        cnt["起漲點變過"] += int(len(tset) > 1)
        T3d = min([x for x in (T1d, T2d) if x is not None], default=None)
        fk = F0[(F0["策略"] == r.策略) & (F0["sid"] == sid) & (F0["e"] == e)]
        Fd = int(fk["假訊號日"].iloc[0]) if len(fk) else -1
        idx = B["idx"]; kb = int(np.searchsorted(idx, e)) - 1; nbk = int(B["next_bad"][max(0, kb - 20)]); dbad = int(idx[nbk - 1]) if nbk < len(idx) else None
        L = SF.get(sid)
        for v, sd in (("T1", T1d), ("T2", T2d), ("T3", T3d), ("F", None if Fd < 0 else Fd)):
            p = None
            if sd is not None:
                x = nxo(sd)
                if x is None:
                    p = None if xf >= n0 else None
                elif xf >= n0 or x <= xf:
                    p = ("open", x)
            cnt[f"{v}早賣"] += int(p is not None)
            if p is None:
                xp, g = xf, gf
                if dbad is not None and xf > dbad:
                    xp, g = dbad, c[dbad] / bp - 1
            else:
                xp, g = p[1], o[p[1]] / bp - 1
                if dbad is not None and 2 * p[1] > 2 * dbad + 1:
                    xp, g = dbad, c[dbad] / bp - 1
            if L is not None and xp > L + 1:
                xp, g = L + 1, c[L] / bp - 1
            if v == "F":
                if not len(fk):
                    why.append("F 找不到第 0 抽"); continue
                rx, rg = int(fk["xpos"].iloc[0]), float(fk["g"].iloc[0])
            else:
                rx, rg = int(getattr(r, f"{v}_xpos")), float(getattr(r, f"{v}_g"))
            if xp != rx or not np.isclose(g, rg, rtol=1e-9, atol=1e-12):
                why.append(f"{v}: xpos {xp}/{rx} g {g:.6f}/{rg:.6f}")
        for v, sd in (("T1", T1d), ("T2", T2d), ("T3", T3d)):
            if (-1 if sd is None else sd) != int(getattr(r, f"{v}訊號日")):
                why.append(f"{v} 訊號日 {sd}/{getattr(r, f'{v}訊號日')}")
        if why:
            nd += 1; errs.append(f"{r.策略} {sid} {e}：{'；'.join(why)}")
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    out.update({"(b) 抽樣": "A 交易（營量＋營飆去重）抽 50 筆（random_state 20261006）", "(b) 不同": nd, "(b) 事件（抽樣）": cnt, "(b) 不同的筆": errs[:20],
                "主程式閘": meta["閘"], "通過": nd == 0 and nd_a == 0 and px_bad == 0 and all(v is True or v == 0 for v in meta["閘"].values())})
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核 b] 不同 {nd}｜{cnt}｜{errs[:3]}｜通過 {out['通過']}")


# ═════════════ 網頁 ═════════════
def page(log):
    ST = pd.read_csv(os.path.join(OUT, "summary_per_trade.csv")); SP = pd.read_csv(os.path.join(OUT, "summary_portfolio.csv"))
    TG = pd.read_csv(os.path.join(OUT, "summary_trigger.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    OLDp = "backtest/resultsYL_truetop/summary_portfolio.csv"; OLD = pd.read_csv(OLDp) if os.path.exists(OLDp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            ".sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}"
            ".pane{display:none}.pane.on{display:block}td.up{color:#b0261e;font-weight:600}td.dn{color:#1f6f3d;font-weight:600}tr.f td{background:#f4f4f4;color:#555}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    P_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    D_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.0f}"
    B2 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.2f}%"
    st = lambda s, sg, v: ST[(ST["策略"] == s) & (ST["段"] == sg) & (ST["出場"] == v) & (ST["口徑"] != "去重")].iloc[0]
    sp = lambda s, sg, v: SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["出場"] == v)].iloc[0]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>真頂出場起漲點版</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>營量、營飆：持有中出現「真頂訊號」就賣（真頂從起漲點算）</h1>",
         "<p class='warn'>⚠ 只當參考，沒有計入檢定數。看結果以 2021～2023 為主；2024～2026.08 只當對照。灰色列「假訊號」是隨機挑一天提早賣，只用來看「提早賣」本身的效果，不是候選做法。</p>"]
    H.append("<div class='ok big'>__CONCL__</div>")
    fi = META["假訊號"]
    H.append(f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。<b>起漲點</b>：持有中每一天，用當天以前的資料、照每日名單同一套規則找起漲點（往前 250 天最高收盤之前的最低點；"
             "買進前那段漲勢已從最高跌 30% 結束就改用之後的低點）。"
             "<b>T1 真頂訊號</b>：處置出關、或「起漲以來已經處置過、又再一次進處置」，而且收盤還在 20 日最高收盤 9 成以上。"
             f"<b>T2 真頂分數</b>：收盤創起漲以來新高那天，30 個真頂特徵同時有 {META['飆股資料']['T2 m*']} 個以上。<b>T3</b>：T1 或 T2 任一。"
             "訊號只看買進以後、正式賣出日以前；當天收盤看到、隔天開盤全部賣；沒訊號就照正式（營量第 60 天、營飆第 120 天收盤賣）。"
             "組合層照正式引擎重新模擬（同槽數、排序／抽籤、成本、停止交易強制出場）。"
             + (f"查核：逐日直接呼叫每日名單的程式比起漲點 {CK['(a) replay 起漲點']['比對日數']:,} 天、{CK['(a) replay 起漲點']['不同']} 天不同；抽 50 筆從頭逐日重算，{CK['(b) 不同']} 筆不同；正式版逐位元相同。" if CK else "") + "</p>")
    H.append("<h2>一、組合層（年化、最大回落）</h2><div class='sel'>策略 <select id='s1' onchange='sw()'>" + "".join(f"<option>{s}</option>" for s in STR) + "</select></div>")
    for s in STR:
        yf = s == "營飆 v1"
        H.append(f"<div class='pane' id='p1{s[:2]}'><div class='wrap'><table><tr><th class='l'>期間</th><th class='l'>出場</th><th>年化<br><small>{'中位（p10～p90）' if yf else '假訊號：200 抽中位'}</small></th>"
                 f"<th>最大回落</th><th>對正式<br><small>年化差</small></th><th>年化贏正式<br><small>{'種子比例' if yf else '抽次比例'}</small></th><th>買進筆</th><th>平均持有<br><small>交易日</small></th></tr>")
        for sg in SEGS:
            for v in VARS:
                x = sp(s, sg, v); many = yf or v == "F"
                cls = "" if v == "A" else (" class='up'" if x["對A年化差 中位"] > 0 else " class='dn'")
                rc = " class='f'" if v == "F" else ""
                H.append(f"<tr{rc}><td class='l'>{sg if v == 'A' else ''}</td><td class='l'>{VNAME[v]}</td>"
                         f"<td>{P1(x['年化 中位'])}" + (f"<br><small>{P1(x['年化 p10'])}～{P1(x['年化 p90'])}</small>" if many else "") + "</td>"
                         f"<td>{P1(x['回落 中位'])}" + (f"<br><small>{P1(x['回落 p10'])}～{P1(x['回落 p90'])}</small>" if many else "") + "</td>"
                         f"<td{cls}>{'—' if v == 'A' else PT(x['對A年化差 中位'])}</td><td>{'—' if v == 'A' or not many else P_(x['年化贏A比例'])}</td>"
                         f"<td>{D_(x['買進筆 中位'])}</td><td>{D_(x['平均持有日 中位'])}</td></tr>")
        H.append("</table></div><p class='note'>買進筆、平均持有只算主窗。" + ("營飆抽籤 200 顆種子；對正式差是同一顆種子相減取中位；假訊號第 r 抽配第 r 顆。" if yf else "營量依 relvol 排序、不抽籤（1 顆）；假訊號抽 200 次。") + "</p></div>")
    H.append("<h2>二、逐筆（同一批進場：正式實際買進的交易）</h2><div class='sel'>策略 <select id='s2' onchange='sw()'>"
             + "".join(f"<option>{s}</option>" for s in STR) + "</select>期間 <select id='s3' onchange='sw()'>" + "".join(f"<option>{k}</option>" for k in SEGS) + "</select></div>")
    for s in STR:
        for sg in SEGS:
            H.append(f"<div class='pane' id='p2{s[:2]}_{sg}'><div class='wrap'><table><tr><th class='l'>出場</th><th>筆數</th><th>平均<br><small>扣成本</small></th><th>中位</th><th>勝率</th>"
                     "<th>平均持有<br><small>交易日</small></th><th>提早賣<br><small>比例</small></th><th>對正式差<br><small>平均</small></th><th>比正式好／差</th></tr>")
            for v in VARS:
                x = st(s, sg, v)
                rc = " class='f'" if v == "F" else ""
                H.append(f"<tr{rc}><td class='l'>{VNAME[v]}</td><td>{int(x['筆數']):,}</td><td>{B2(x['平均'])}</td><td>{B2(x['中位'])}</td><td>{P_(x['勝率'])}</td>"
                         f"<td>{D_(x['平均持有天數'])}</td><td>{'—' if v == 'A' else P_(x['觸發比例'])}</td><td>{'—' if v == 'A' else PT(x['對A差平均'])}</td>"
                         f"<td>{'—' if v == 'A' else P_(x['比A好比例']) + '／' + P_(x['比A差比例'])}</td></tr>")
            H.append("</table></div>")
            t = TG[(TG["策略"] == s) & (TG["段"] == sg)]
            if len(t):
                t = t.iloc[0]
                H.append("<p class='note'>賣出位置和「真頂」（事後才知道的最高收盤；只描述）比：")
                for v in ("A",) + VT + ("F",):
                    k = f"{v} 賣在真頂以前"
                    if k in t and np.isfinite(t[k]):
                        H.append(f"{VNAME[v].split('（')[0]}：賣在真頂以前 {P_(t[k])}、離真頂 5 天內 {P_(t[f'{v} 離真頂5根內'])}、賣價比真頂 {P1(t[f'{v} 賣價÷真頂−1 中位'])}、吃到真頂 {P_(t[f'{v} 吃到真頂幾成 中位'])}（中位）；")
                H.append(f"T1 提早賣裡由「再次處置」觸發 {P_(t['T1 由再次處置觸發'])}、由「出關」{P_(t['T1 由出關觸發'])}。（提早賣的筆才算；正式那列是全部筆）</p>")
            H.append("</div>")
    H.append("<h2>名詞與做法</h2><ul class='note'>"
             "<li>正式：營量第 60 個交易日收盤賣（20 槽、依 relvol 挑）；營飆第 120 個交易日收盤賣（10 槽、抽籤）。每筆扣來回成本 0.585%。</li>"
             "<li>和上一份（真頂訊號從買進日算、處置要 60 天內）不同：這次「已處置過」是從起漲點算起，進場前的處置也算；只有真頂訊號、沒有分批、沒有 40 天規則、沒有延長。</li>"
             f"<li>假訊號：每個策略照 T1 實際提早賣的比例（營量 {P_(fi['營量 v1']['p（候選列 T1 提早賣比例）'])}、營飆 {P_(fi['營飆 v1']['p（候選列 T1 提早賣比例）'])}）"
             "和「訊號在買進後第幾天」的分布，隨機挑一天提早賣；種子寫死。它比正式好或差多少，就是「提早賣」本身的效果。</li>"
             "<li>資料最後一天（2026-09-24）還沒賣的，以那天收盤計值。母體 ＝ 正式本體母體（和正式版逐位元相同）。</li></ul>")
    H.append("<script>function sw(){var a=document.getElementById('s1').value.slice(0,2),b=document.getElementById('s2').value.slice(0,2),c=document.getElementById('s3').value;"
             "document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p1'+a||x.id=='p2'+b+'_'+c))}sw()</script></main></body></html>")
    txt = "\n".join(H).replace("__CONCL__", conclusion(SP, ST, OLD))
    open(os.path.join(OUT, "營量營飆真頂出場_起漲點版.html"), "w", encoding="utf-8").write(txt)
    log("[網頁] 完成")


def conclusion(SP, ST, OLD):
    P1 = lambda v: f"{v * 100:+.1f}%"
    sp = lambda s, v, sg: SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["出場"] == v)].iloc[0]
    L = []
    for s in STR:
        yf = s == "營飆 v1"
        a21, a24, aal = sp(s, "A", "2021-2023"), sp(s, "A", "2024-2026.08"), sp(s, "A", "全部")
        parts = []
        for v in VT + ("F",):
            b21, b24, bal = sp(s, v, "2021-2023"), sp(s, v, "2024-2026.08"), sp(s, v, "全部")
            d = b21["對A年化差 中位"]
            parts.append(f"{'假訊號' if v == 'F' else v} {P1(b21['年化 中位'])}（{'多' if d > 0 else '少'} {abs(d) * 100:.1f} 點"
                         + (f"，贏正式 {b21['年化贏A比例'] * 100:.0f}%" if (yf or v == "F") else "") + f"；對照期 {P1(b24['年化 中位'])}／正式 {P1(a24['年化 中位'])}）")
        L.append(f"<li><b>{s[:2]}</b>（正式 2021～2023 年化 {P1(a21['年化 中位'])}、回落 {P1(a21['回落 中位'])}）：" + "；".join(parts) + "。</li>")
    best = []
    for s in STR:
        w = [v for v in VT if sp(s, v, "2021-2023")["對A年化差 中位"] > 0]
        best.append(f"{s[:2]}：{'、'.join(w) + ' 在主判期贏正式' if w else '沒有一版在主判期贏正式'}")
    if OLD is not None:
        o = []
        for s in STR:
            x = OLD[(OLD["策略"] == s) & (OLD["段"] == "2021-2023") & (OLD["出場"] == "E1")]
            if len(x):
                o.append(f"{s[:2]} {PT_(x['對A年化差 中位'].iloc[0])} → 這次 T1 {PT_(sp(s, 'T1', '2021-2023')['對A年化差 中位'])}")
        if o:
            L.append("<li>和上一份（真頂訊號從買進日算、處置要 60 天內）比，主判期對正式的年化差：" + "；".join(o) + "。</li>")
    L.append("<li>T2（真頂分數）幾乎每筆都很快觸發（平均只抱十幾個交易日），等於很早就下車、錯過後面的大漲，年化大幅輸正式；T3 同理。</li>")
    return "<b>先講結論</b>：" + "；".join(best) + "。<ul class='big'>" + "".join(L) + "</ul>"


def PT_(v):
    return f"{v * 100:+.1f} 點"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()
