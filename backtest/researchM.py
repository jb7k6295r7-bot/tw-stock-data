# -*- coding: utf-8 -*-
"""PREREGM 本體（下降趨勢線被收盤向上突破：三種畫法並測）——判定量、CI、出口、§六 必報、§七 描述臂 a～f、§八 假訊號臂。
判準＝台股策略線 PREREGM seq1（sha 9316840579a8d33a）§四～§九；五處讀法＝裁定線 seq156（照 trendline_m.py M1～M8、researchM_freq.py Q1～Q8）。

資料、母體、讀檔、硬斷點：與 PREREGH1／H2 同一份快照（import researchH2：main edc6f8002f、gate3、H2.brk）。
事件：backtest/trendline_m.py 重新偵測，再照 researchM_freq Q2 同一順序判狀態 ⇒ ⭐ 開算前先與已提交的
   resultsM/events_*.csv 七檔逐列比（sid、market、T、取點／回歸窗起點、確認日、狀態），任一列不同 ⇒ 中止。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何報酬之前寫在這裡；交件逐條列出）：
 B1 出場價 px(j)：還原 open(j)（j 為有效 K 棒且開盤 > 0）；否則＝該股 ≤ j 最後一根有效 K 棒的還原收盤
    （下市者＝最後成交價，delist on；短停牌＝停牌前收盤；同 H1 Q4／H2 R10 的 cff）。用到退路的件數另報。
 B2 基準 EW_H(d)：d 日為有效 K 棒且還原開盤 > 0 的全部 gate3 股票（含日後下市者），px(d+H)／open(d) − 1 的等權平均；
    主格 d＝T+1、H＝20（⇒ [open(T+1), open(T+21)]）。⛔ 不排除 d 日開盤漲停者（同 H1 Q4）。
 B3 R_e ＝ px(T+21)／open(T+1) − 1 − 0.585%；X_e ＝ R_e −（EW_20(T+1) − 0.585%）。
 B4 主 CI：research11.cl_stats（平均的 CR0 月分群 SE、T 所在曆月、1.96）；非重疊 SE：H2 R8（20 日區段平均的標準差／√區段數，
    區段號 ＝ min((T − 窗起點)//20, 114)）。
 B5 n_eff ＝ min(保留事件數, 有事件的區段數)；< 30 出口①、30～99 出口②、≥ 100 出口③；事件 < 30 ⇒ 結果④ 併入出口①。
 B6 勝率 ＝ X > 0 的比例（另報 R_e > 0）；最差單筆 ＝ min X（另報 min R_e）；比率一律附分母與上市／上櫃組成。
 B7 兩兩重疊 ＝ 同檔同 T（保留事件對保留事件）；另報「同檔、T 相差 ≤ 5 個交易日」（描述）。
 B8 「收盤創 20 日新高」＝ close(T) ≥ 該股最近 20 根有效 K 棒（含 T）收盤最大值（research11 的 hiN 同式）。
 B9 假訊號臂：每個（檔, 曆月）有 k 筆保留真事件 ⇒ 在該檔該月、T ∈ [窗起點, 窗尾−21] 的有效 K 棒中不放回抽 k 天；
    之後照 Q2 同一順序（合併 20 日 → 硬斷點 [T, T+21]（無取點 ⇒ 從 T 起）→ T+1 停牌 → T+1 開盤漲停），再照 §四§五。
    判過 ＝ CI 不含 0（兩側，同 H1／H2）；另分列 (+)／(−)。種子 20260925＋r，r＝0…29。
 B10 描述臂 a 突破判準：「收盤穿越 1%」＝ close(T) > 1.01·ℓ(T) ∧ close(T−1) ≤ 1.01·ℓ(T−1)；
    「3 日 3% 站穩」＝ t 為收盤穿越（close(t) > ℓ(t) ∧ close(t−1) ≤ ℓ(t−1)）且 t+1、t+2（有效 K 棒）收盤皆 > ℓ、
    close(t+2) ≥ 1.03·ℓ(t+2) ⇒ T＝t+2（第三日收盤確認）。(甲)(乙)：線的生命週期規則不變，只有符合該判準的事件才結束線，
    且 t ≥ 確認日＋1；(丙)：用 t 日那條 ŷ_t 延伸到 t+1、t+2。(丙) N×R² 報 {30,60,120}×{0.3,0.5,0.7} 除主格外 8 格（全報）。
 B11 描述臂 b：持有期內有效 K 棒 j（T < j ≤ T+20）收盤 < 延伸原線 ℓ(j) ⇒ px(j 的次一交易日) 出；否則 T+21 出。
    (甲)(乙) 原線 ＝ P1–P2 在有效 K 棒軸上延伸；(丙) ＝ ŷ_T 延伸。X 用同長度 EW_H。
 B12 描述臂 c：T+61 開盤出、需 T+61 ≤ 窗尾、硬斷點範圍延伸到 T+61（不符者另計）；非重疊區段 60 日（上限 38）。
 B13 描述臂 d：近 20 日報酬 ＝ close(T)／close(該股往前第 20 根有效 K 棒) − 1；十分位 ＝ T 日全部 gate3 可算此值者 rank(first) 後等分 10；
    控制組 ＝ 同十分位、該畫法 T 日無【原始】突破（含被合併／剔除者）、T+1 可成交（有成交、開盤非缺、非開盤漲停）、
    [T, T+21] 無硬斷點、非事件股本身 的【全部】股票之毛報酬等權平均；d_e ＝ 事件毛報酬 − 控制平均（成本相消）。
 B14 描述臂 e：(甲) 保留事件，依「該線確認那一根收盤時 (乙) 的選取結果」分組；放棄組 ＝ (乙) 為「第三點偏離」
    （三個遞降樞紐、第三點離 P1–P2 線 > 2%）。其餘選取結果並報。
 B15 描述臂 f：E＝還原 open(T+1)、S＝還原 low(T)、1R＝E−S；持有期內有效 K 棒 j（T < j ≤ T+20）收盤判；
    f2 每根先用當時停損判出場、再判 close(j) ≥ E+1R ⇒ 停損上移到 E（同一根兩者不會同時成立）。放棄組 60 日只取 T+61 ≤ 窗尾者。
"""
from __future__ import annotations
import os, sys, time, json
from collections import Counter
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                            # ⭐ 同一份快照、同一套讀檔／斷點（D.DATA 已被指到快照）
D, TR, UG, R11 = H2.D, H2.TR, H2.UG, H2.R
from backtest import trendline_m as TM
import researchM_freq as RF                        # 只 import（_g5、cfg_name、常數）

OUT = "backtest/resultsM_body"
W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
COST = H2.COST_RT                                  # 0.585%
H_OUT, MERGE, BLOCK, CAP = 21, 20, 20, 115
SEED = 20260925
REPS = 30
PIV_CFG = [("甲", 5), ("乙", 5), ("甲", 3), ("乙", 3), ("甲", 10), ("乙", 10)]
REG_GRID = [(N, r2) for N in (30, 60, 120) for r2 in (0.3, 0.5, 0.7)]
MAIN = ("甲", "乙", "丙")
_G = {}


# ═════════════ 偵測：描述臂 a 的突破判準變體（主格一律 trendline_m；變體的 "close" 版要與它逐筆相同）═════════════
def _hit(rule, L, c, b):
    lv = lambda j: TM._lv(L, j)
    if rule == "close":
        return b >= 1 and c[b] > lv(b) and c[b - 1] <= lv(b - 1)
    if rule == "pct1":
        return b >= 1 and c[b] > 1.01 * lv(b) and c[b - 1] <= 1.01 * lv(b - 1)
    if rule == "d3p3":
        return (b - 2 >= L["conf"] + 1 and b >= 3 and c[b - 3] <= lv(b - 3) and c[b - 2] > lv(b - 2)
                and c[b - 1] > lv(b - 1) and c[b] >= 1.03 * lv(b))
    raise ValueError(rule)


def detect_pivot_var(o, h, c, method, R, rule):
    """(甲)(乙) 同 TM.detect_pivot 的線生命週期（M2～M4，選取直接用 TM._select），只換突破判準；另回每個確認根的選取理由。"""
    o = np.asarray(o, float); h = np.asarray(h, float); c = np.asarray(c, float)
    m = len(c); top = np.fmax(o, c)
    piv = np.flatnonzero(TM.pivot_highs(h, R))
    conf_at = {int(s + R): int(s) for s in piv}
    conf, ev, why_at = [], [], {}
    L = None
    for b in range(m):
        if L is not None:
            if b - L["conf"] > TM.LIFE:
                L = None
            elif _hit(rule, L, c, b):
                ev.append({"T": b, "anchors": L["anchors"], "conf": L["conf"], "first": L["anchors"][0]})
                L = None
        s = conf_at.get(b)
        if s is not None:
            conf.append(s)
            L, why = TM._select(method, conf, h, top, b)
            why_at[b] = why
    return ev, why_at


def reg_arrays(c, N):
    """與 TM.detect_reg 同一組算式（逐位元相同）。回 (T, ybar, slope, r2)，第 i 列 ＝ T＝i+N 的窗 [T−N, T−1]。"""
    c = np.asarray(c, float); m = len(c)
    if m < N + 1:
        return np.zeros(0, int), np.zeros(0), np.zeros(0), np.zeros(0)
    W = np.lib.stride_tricks.sliding_window_view(c, N)[: m - N]
    x = np.arange(N, dtype=float) - (N - 1) / 2.0
    sxx = float((x * x).sum())
    ybar = W.mean(axis=1)
    slope = (W * x).sum(axis=1) / sxx
    syy = ((W - ybar[:, None]) ** 2).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        r2 = np.where(syy > 0, slope * slope * sxx / syy, 0.0)
    return np.arange(N, m), ybar, slope, r2


def reg_line(ybar, slope, N, k):
    """ŷ_T 在 T−N+k 根的值（k＝N ⇒ T 當根；與 TM 的 yT 同式）。"""
    return ybar + slope * (k - (N - 1) / 2.0)


def detect_reg_var(c, N, r2min, rule):
    c = np.asarray(c, float); m = len(c)
    T, yb, sl, r2 = reg_arrays(c, N)
    if len(T) == 0:
        return []
    down = (sl < 0) & (r2 >= r2min)
    yT = reg_line(yb, sl, N, N); yT1 = reg_line(yb, sl, N, N - 1)
    if rule == "close":
        hit = down & (c[T] > yT) & (c[T - 1] <= yT1)
        return [{"T": int(t), "first": int(t - N), "i": int(i)} for i, t in zip(np.flatnonzero(hit), T[hit])]
    if rule == "pct1":
        hit = down & (c[T] > 1.01 * yT) & (c[T - 1] <= 1.01 * yT1)
        return [{"T": int(t), "first": int(t - N), "i": int(i)} for i, t in zip(np.flatnonzero(hit), T[hit])]
    if rule == "d3p3":
        base = down & (c[T] > yT) & (c[T - 1] <= yT1)
        out = []
        for i in np.flatnonzero(base):
            t = int(T[i])
            if t + 2 >= m:
                continue
            if c[t + 1] > reg_line(yb[i], sl[i], N, N + 1) and c[t + 2] >= 1.03 * reg_line(yb[i], sl[i], N, N + 2):
                out.append({"T": t + 2, "first": t - N, "i": int(i)})
        return out
    raise ValueError(rule)


# ═════════════ 狀態（researchM_freq Q2 同一順序）═════════════
def status(evs, S, w0, wE, hold=H_OUT):
    """evs：[(T, first, payload)]（日曆位置、依 T 排序）⇒ [(T, first, payload, 狀態)]；只收 T ∈ [w0, wE]。"""
    out = []; t_keep = -10 ** 9
    for T, first, pay in evs:
        if not (w0 <= T <= wE):
            continue
        f_brk = H2.brk(S, first, T + hold)
        f_halt = (not bool(S["trd"][T + 1])) or (not np.isfinite(S["o"][T + 1]))
        f_lim = bool(S["up_o"][T + 1])
        if t_keep < T <= t_keep + MERGE:
            st = "合併掉"
        elif f_brk:
            st = "剔除_硬斷點"
        elif f_halt:
            st = "剔除_T+1停牌"
        elif f_lim:
            st = "剔除_T+1開盤漲停"
        else:
            st = "保留"; t_keep = T
        out.append((T, first, pay, st))
    return out


# ═════════════ 讀檔＋偵測（worker）═════════════
def _init(cal, w0, w1, off):
    _G.update(cal=cal, w0=w0, w1=w1, off=off)


def load_one(args):
    sid, market = args
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]; n = len(cal); wE = w1 - H_OUT
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    S = {"o": o, "trd": tb["trd"], "up_o": tb["up_o"], "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    cff = pd.Series(c).ffill().to_numpy()
    okO = valid & np.isfinite(o) & (o > 0)
    px = np.where(okO, o, cff)
    cb = c[bars]; ob = o[bars]; hb = h[bars]
    r20 = np.full(n, np.nan)
    if len(bars) > 20:
        r20[bars[20:]] = cb[20:] / cb[:-20] - 1.0
    nh20 = np.zeros(n, bool)
    if len(bars) >= 20:
        mx = pd.Series(cb).rolling(20, min_periods=20).max().to_numpy()
        nh20[bars] = np.isfinite(mx) & (cb >= mx)
    cfgs, mism, raw_main, why_yi = {}, {}, {}, {}
    toc = lambda x: int(bars[x])
    # 主格＋R 描述臂：trendline_m 官方路
    for meth, R in PIV_CFG:
        r = TM.detect_calendar(o, h, c, meth, R)
        evs = [(e["T"], e["first"], {"anchors": e["anchors"], "conf": e["conf"], "T_bar": e["T_bar"]}) for e in r["events"]]
        cfgs[(meth, R, "close")] = status(evs, S, w0, wE)
        if R == 5:
            raw_main[meth] = np.array([e["T"] for e in r["events"]], int)
        # 變體 close 版 ⇒ 必須與 TM 逐筆相同
        v, why = detect_pivot_var(ob, hb, cb, meth, R, "close")
        a1 = [(e["T"], e["anchors"], e["conf"]) for e in r["events"]]
        a2 = [(toc(e["T"]), tuple(toc(x) for x in e["anchors"]), toc(e["conf"])) for e in v]
        mism[(meth, R)] = int(a1 != a2)
        if (meth, R) == ("乙", 5):
            why_yi = {toc(b): w for b, w in why.items()}
        if R == 5:
            for rule in ("pct1", "d3p3"):
                v2, _ = detect_pivot_var(ob, hb, cb, meth, R, rule)
                evs2 = [(toc(e["T"]), toc(e["first"]), {"anchors": tuple(toc(x) for x in e["anchors"]), "conf": toc(e["conf"]), "T_bar": e["T"]}) for e in v2]
                cfgs[(meth, R, rule)] = status(evs2, S, w0, wE)
    # (丙)
    Tn, yb, sl, _ = reg_arrays(cb, TM.REG_N)
    for N, r2 in REG_GRID:
        r = TM.detect_calendar(o, h, c, "丙", N=N, r2min=r2)
        if (N, r2) == (TM.REG_N, TM.REG_R2):
            evs = [(e["T"], e["first"], {"T_bar": e["T_bar"], "ybar": float(yb[e["T_bar"] - TM.REG_N]), "slope": float(sl[e["T_bar"] - TM.REG_N])}) for e in r["events"]]
            raw_main["丙"] = np.array([e["T"] for e in r["events"]], int)
            v = detect_reg_var(cb, N, r2, "close")
            mism[("丙", 5)] = int([e["T"] for e in r["events"]] != [toc(e["T"]) for e in v])
            for rule in ("pct1", "d3p3"):
                v2 = detect_reg_var(cb, N, r2, rule)
                evs2 = [(toc(e["T"]), toc(e["first"]), {"T_bar": e["T"]}) for e in v2]
                cfgs[("丙", 5, rule)] = status(evs2, S, w0, wE)
            cfgs[("丙", 5, "close")] = status(evs, S, w0, wE)
        else:
            evs = [(e["T"], e["first"], {"T_bar": e["T_bar"]}) for e in r["events"]]
            cfgs[("丙", (N, r2), "close")] = status(evs, S, w0, wE)
    return {"sid": sid, "market": market, "o": o, "h": h, "l": l, "c": c, "valid": valid, "bars": bars, "px": px, "okO": okO,
            "fb": ~okO, "trd": tb["trd"], "up_o": tb["up_o"], "cs_pb": S["cs_pb"], "cs_g5": S["cs_g5"],
            "r20": r20, "nh20": nh20, "cfgs": cfgs, "mism": mism, "raw": raw_main, "why_yi": why_yi,
            "delisted": bool(delisted), "last": ds["last"] if ds else None}


# ═════════════ 基準 ═════════════
def ew_open(O, okO, PX, H):
    """EW_H(d) ＝ d 日 okO 的股票：PX(d+H)／O(d) − 1 的等權平均（B2）。O、PX：n×S。"""
    n = O.shape[0]; out = np.full(n, np.nan)
    Od = np.where(okO[:n - H], O[:n - H], np.nan)
    r = PX[H:] / Od - 1.0
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(r).sum(axis=1)
        s = np.nansum(r, axis=1)
    out[:n - H] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out


def ew_brute(stocks, d, H):
    """⭐ 獨立寫法（逐檔逐日迴圈、不共用 ew_open 任何一行）：fixture 用。stocks：list of (o, c) 日曆序列。"""
    tot, k = 0.0, 0
    for o, c in stocks:
        if not (np.isfinite(c[d]) and np.isfinite(o[d]) and o[d] > 0):
            continue
        j = d + H
        if np.isfinite(c[j]) and np.isfinite(o[j]) and o[j] > 0:
            ex = o[j]
        else:
            jj = j
            while jj >= 0 and not np.isfinite(c[jj]):
                jj -= 1
            ex = c[jj]
        tot += ex / o[d] - 1.0; k += 1
    return tot / k if k else np.nan


def selftest():
    """F-a 基準向量法 ＝ 獨立迴圈法（含停牌、下市、上市前、開盤缺值）；F-b 恆等輸入 ⇒ X＝0；F-c 0 報酬 ⇒ X＝0；
    F-d 已知報酬 ⇒ X 手算；F-e 變體判準 close 版 ＝ TM（合成序列）；F-f 3 日 3% 站穩的邊界。"""
    rng = np.random.default_rng(7)
    n, S_ = 80, 6
    O = np.exp(rng.normal(0, 0.03, (n, S_)).cumsum(axis=0)) * 50; C = O * np.exp(rng.normal(0, 0.01, (n, S_)))
    C[10:13, 1] = np.nan; O[10:13, 1] = np.nan                  # 停牌 3 日
    C[50:, 2] = np.nan; O[50:, 2] = np.nan                      # 第 50 日起下市
    C[:30, 3] = np.nan; O[:30, 3] = np.nan                      # 第 30 日才上市
    O[40, 4] = np.nan                                           # 有收盤、開盤缺
    valid = np.isfinite(C); okO = valid & np.isfinite(O) & (O > 0)
    cff = pd.DataFrame(C).ffill().to_numpy(); PX = np.where(okO, O, cff)
    stocks = [(O[:, j], C[:, j]) for j in range(S_)]
    worst = 0.0
    for H in (1, 5, 20):
        ew = ew_open(O, okO, PX, H)
        for d in range(0, n - H):
            b = ew_brute(stocks, d, H)
            worst = max(worst, abs(ew[d] - b) if np.isfinite(b) else (0 if np.isnan(ew[d]) else 1))
    assert worst < 1e-12, worst
    # F-b 恆等：全體只有事件股一檔 ⇒ X＝0
    o1 = O[:, [0]]; ok1 = okO[:, [0]]; px1 = PX[:, [0]]
    e1 = ew_open(o1, ok1, px1, 20)
    T = 30; Re = px1[T + 21, 0] / o1[T + 1, 0] - 1 - COST; X = Re - (e1[T + 1] - COST)
    assert abs(X) < 1e-15, X
    # F-c 0 報酬：全體價格恆等 ⇒ R_e ＝ −0.585%、基準 ＝ −0.585%、X ＝ 0
    Oc = np.full((n, 4), 20.0); okc = np.ones((n, 4), bool)
    ec = ew_open(Oc, okc, Oc, 20)
    Re = Oc[T + 21, 2] / Oc[T + 1, 2] - 1 - COST; X = Re - (ec[T + 1] - COST)
    assert abs(Re + COST) < 1e-15 and abs(X) < 1e-15, (Re, X)
    # F-d 已知：兩檔，事件股 +10%、另一檔 −10% ⇒ EW 0 ⇒ X ＝ +10%
    Od = np.full((n, 2), 10.0); Od[T + 21:, 0] = 11.0; Od[T + 21:, 1] = 9.0
    ed = ew_open(Od, np.ones((n, 2), bool), Od, 20)
    X = (Od[T + 21, 0] / Od[T + 1, 0] - 1 - COST) - (ed[T + 1] - COST)
    assert abs(X - 0.10) < 1e-12, X
    # F-e 變體 close 版 ＝ TM：隨機序列 200 檔
    diffs = 0
    for k in range(200):
        r_ = np.random.default_rng(1000 + k)
        cc = 50 * np.exp(r_.normal(0, 0.02, 400).cumsum()); oo = cc * np.exp(r_.normal(0, 0.005, 400))
        hh = np.fmax(oo, cc) * (1 + np.abs(r_.normal(0, 0.01, 400)))
        for meth in ("甲", "乙"):
            a = TM.detect_bars(oo, hh, cc, meth, 5)["events"]; b, _ = detect_pivot_var(oo, hh, cc, meth, 5, "close")
            diffs += int([(e["T"], e["anchors"]) for e in a] != [(e["T"], e["anchors"]) for e in b])
        a = TM.detect_bars(oo, hh, cc, "丙")["events"]; b = detect_reg_var(cc, 60, 0.5, "close")
        diffs += int([e["T"] for e in a] != [e["T"] for e in b])
    assert diffs == 0, diffs
    # F-f 3 日 3%：手造一條水平下降線 ℓ≡100（斜率 −0 不成立 ⇒ 直接測 _hit）
    L = {"h1": 100.0, "slope": -1e-12, "p1": 0, "conf": 0}
    c = np.array([99, 99, 99, 101, 102, 103.0, 99])
    assert _hit("d3p3", L, c, 5) and not _hit("d3p3", L, c, 4) and not _hit("d3p3", L, c, 3)
    c2 = c.copy(); c2[5] = 102.9; assert not _hit("d3p3", L, c2, 5)            # 第三日未達 3%
    c3 = c.copy(); c3[4] = 99.5; assert not _hit("d3p3", L, c3, 5)             # 中間跌回線下
    assert _hit("pct1", L, np.array([99, 101.5]), 1) and not _hit("pct1", L, np.array([99, 100.9]), 1)
    msg = ("F-a 基準向量法＝獨立迴圈法（停牌／下市／上市前／開盤缺；H＝1、5、20 共 {} 點）最大差 {:.1e}｜F-b 恆等（全體＝事件股）X＝0｜"
           "F-c 0 報酬 R_e＝−0.585%、X＝0｜F-d 已知 X＝+10%｜F-e 變體 close 版＝TM（隨機 200 檔 × 三畫法）差 0｜F-f 3 日 3%、1% 邊界").format(
        sum(n - H for H in (1, 5, 20)), worst)
    print("✅ 自測：" + msg, flush=True)
    return msg


# ═════════════ 統計 ═════════════
def summ(x, T, cal, w0, blk=BLOCK, cap=CAP):
    x = np.asarray(x, float); T = np.asarray(T, int)
    if len(x) == 0:
        return {"n": 0}
    mon = np.array([str(cal[t])[:7] for t in T])
    cs = R11.cl_stats(x, mon)
    b = np.minimum((T - w0) // blk, cap - 1)
    bm = pd.Series(x).groupby(b).mean()
    se2 = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    nb = int(len(bm))
    return {"n": int(len(x)), "平均": cs["mean"], "中位": cs["median"], "勝率": cs["win"], "勝數": int((x > 0).sum()),
            "最差": cs["worst"], "p10": cs["p10"], "p90": float(np.percentile(x, 90)),
            "se_月": cs["se"], "lo": cs["lo"], "hi": cs["hi"], "曆月數": cs["months"],
            "se_非重疊": se2, "lo_非重疊": cs["mean"] - 1.96 * se2, "hi_非重疊": cs["mean"] + 1.96 * se2,
            "區段數": nb, "n_eff": int(min(len(x), nb))}


def verdict(s):
    if s["n"] < 30:
        return "出口①", "結果④（事件 < 30，併入出口①：樣本不足以分辨）"
    if s["n_eff"] < 30:
        return "出口①", "—（出口①：樣本不足以分辨）"
    ex = "出口②" if s["n_eff"] < 100 else "出口③"
    if s["lo"] <= 0 <= s["hi"]:
        return ex, "結果①（測不出）"
    return ex, ("結果②（測得出（＋））" if s["平均"] > 0 else "結果③（測得出（−））")


def mk_split(df, col=None):
    """分母的上市／上櫃組成。"""
    d = df if col is None else df[df[col]]
    return {"分母": int(len(d)), "上市": int((d["market"] == "twse").sum()), "上櫃": int((d["market"] == "tpex").sum())}


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def pp(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}pp"


# ═════════════ 主程式 ═════════════
def main():
    t0 = time.time()
    fx = selftest()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else REPS
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS
    wE = w1 - H_OUT
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official()
    print("[資料] 快照 {}｜日曆 {} 根｜判定窗 [{}, {}]｜T 可落 [{}, {}]｜gate3 {:,} 檔".format(
        SHA[:10], n, W0, W1, cal[w0].date(), cal[wE].date(), len(U)), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, off)) as pool:
        res = pool.map(load_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}
    sids = sorted(ST); sidx = {s: i for i, s in enumerate(sids)}
    print("[讀檔＋偵測] 可用 {:,} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True)
    CHK = {"fixture": fx}

    # ── 查核 1：與已提交事件檔逐列相同
    rows_equal = {}
    for meth, R in PIV_CFG + [("丙", 5)]:
        nm = RF.cfg_name(meth, R)
        rows = []
        for s in sids:
            for T, first, pay, stt in ST[s]["cfgs"][(meth, R, "close")]:
                if meth == "丙":
                    rows.append({"sid": s, "market": ST[s]["market"], "T": str(cal[T].date()), "回歸窗起點": str(cal[first].date()), "狀態": stt})
                else:
                    rows.append({"sid": s, "market": ST[s]["market"], "T": str(cal[T].date()),
                                 "取點": "|".join(str(cal[a].date()) for a in pay["anchors"]), "確認日": str(cal[pay["conf"]].date()), "狀態": stt})
        mine = pd.DataFrame(rows)
        ref = pd.read_csv(os.path.join("backtest/resultsM", "events_{}.csv".format(nm)), dtype=str)
        if lim:
            ref = ref[ref["sid"].isin(sids)].reset_index(drop=True)
        same = mine.shape == ref.shape and bool((mine.fillna("").astype(str).values == ref.fillna("").astype(str).values).all())
        rows_equal[nm] = {"列數_本支": int(len(mine)), "列數_已提交": int(len(ref)), "逐列相同": same,
                          "保留": int((mine["狀態"] == "保留").sum()) if len(mine) else 0}
        print("[查核1 事件檔逐列] {}：本支 {:,} 列／已提交 {:,} 列 ⇒ {}".format(nm, len(mine), len(ref), "相同" if same else "⛔ 不同"), flush=True)
        if not same:
            json.dump(rows_equal, open(os.path.join(OUT, "ABORT_rows.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            raise SystemExit("⛔ 重新偵測與已提交事件檔不同：{} ⇒ 中止（未算任何報酬）".format(nm))
    CHK["事件檔逐列相同"] = rows_equal
    mm = Counter()
    for s in sids:
        for k, v in ST[s]["mism"].items():
            mm[RF.cfg_name(*k)] += v
    CHK["變體偵測close版與trendline_m不同的檔數"] = dict(mm)
    assert sum(mm.values()) == 0, mm
    print("[查核1b] 描述臂變體偵測器的 close 版與 trendline_m 逐檔相同（不同檔數 {}）".format(dict(mm)), flush=True)

    # ── 矩陣與基準
    Sn = len(sids)
    O = np.column_stack([ST[s]["o"] for s in sids]); okO = np.column_stack([ST[s]["okO"] for s in sids])
    PX = np.column_stack([ST[s]["px"] for s in sids])
    EW = {H: ew_open(O, okO, PX, H) for H in range(1, 61)}
    mkt = {s: ST[s]["market"] for s in sids}
    print("[基準] EW_H，H＝1…60｜{:.0f}s".format(time.time() - t0), flush=True)

    def kept_df(key):
        rows = []
        for s in sids:
            S = ST[s]
            for T, first, pay, stt in S["cfgs"][key]:
                if stt != "保留":
                    continue
                P0 = S["o"][T + 1]; ex = S["px"][T + H_OUT]
                g = ex / P0 - 1.0
                rows.append({"sid": s, "market": S["market"], "T": T, "first": first, "P0": P0, "px_out": ex,
                             "退路": bool(S["fb"][T + H_OUT]), "g": g, "R": g - COST, "EW": EW[20][T + 1],
                             "X": g - EW[20][T + 1], **pay})
        return pd.DataFrame(rows)

    def acct(key):
        a = Counter(stt for s in sids for _, _, _, stt in ST[s]["cfgs"][key])
        return {"原始_窗內": int(sum(a.values())), "合併掉": a["合併掉"], "剔除_硬斷點": a["剔除_硬斷點"],
                "剔除_T+1停牌": a["剔除_T+1停牌"], "剔除_T+1開盤漲停": a["剔除_T+1開盤漲停"], "保留": a["保留"]}

    RES = {"快照": SHA, "判定窗": [W0, W1], "gate3母體": int(len(U)), "可用檔數": len(ST), "成本": COST}
    freq = json.load(open("backtest/resultsM/freq.json", encoding="utf-8"))
    RES["§六_頻率（引 resultsM/freq.json）"] = {m: freq["畫法"][m]["每檔每年（合併後、剔除後）"] for m in MAIN}
    E = {}; J = {}
    for m in MAIN:
        E[m] = kept_df((m, 5, "close"))
        s_ = summ(E[m]["X"], E[m]["T"], cal, w0); ex_, rs_ = verdict(s_)
        sR = summ(E[m]["R"], E[m]["T"], cal, w0)
        J[m] = {**s_, "出口": ex_, "結果": rs_, "事件帳": acct((m, 5, "close")),
                "R_e": {"平均": sR["平均"], "中位": sR["中位"], "R>0": sR["勝率"], "R>0數": sR["勝數"], "最差": sR["最差"], "p10": sR["p10"], "p90": sR["p90"]},
                "基準平均": float(E[m]["EW"].mean() - COST), "勝率分母組成": mk_split(E[m]),
                "出場用退路": int(E[m]["退路"].sum())}
        print("[{}] 保留 {:,}｜n_eff {}｜平均X {}（CI {} ～ {}；非重疊 {} ～ {}）｜{} {}".format(
            m, s_["n"], s_["n_eff"], pct(s_["平均"]), pct(s_["lo"]), pct(s_["hi"]), pct(s_["lo_非重疊"]), pct(s_["hi_非重疊"]), ex_, rs_), flush=True)
    RES["判定三格"] = J
    for m in MAIN:
        E[m].drop(columns=[c_ for c_ in ("anchors",) if c_ in E[m]]).assign(T_date=lambda d: [str(cal[t].date()) for t in d["T"]]).to_csv(
            os.path.join(OUT, "events_X_{}.csv".format(m)), index=False, encoding="utf-8")

    # ── 三格合句
    good = [m for m in MAIN if J[m]["結果"].startswith("結果②")]
    neg = [m for m in MAIN if J[m]["結果"].startswith("結果③")]
    if len(good) == 3:
        comb = "三種畫法都測得出（＋）"
    elif good:
        comb = "只在（{}）測得出（＋）⇒ 結果隨畫法而變".format("）（".join(good))
    else:
        comb = "三種畫法都沒有測得出（＋）"
    if neg:
        comb += "；另：（{}）測得出（−）".format("）（".join(neg))
    RES["三格合句"] = comb

    # ── §六
    six = {}
    for m in MAIN:
        e = E[m]
        six[m] = {"上市": summ(e.loc[e["market"] == "twse", "X"], e.loc[e["market"] == "twse", "T"], cal, w0),
                  "上櫃": summ(e.loc[e["market"] == "tpex", "X"], e.loc[e["market"] == "tpex", "T"], cal, w0),
                  "逐年": {}}
        yr = np.array([cal[t].year for t in e["T"]])
        for y in sorted(set(yr)):
            k = yr == y
            ss = summ(e["X"][k], e["T"][k], cal, w0)
            six[m]["逐年"][str(y)] = {"n": ss["n"], "平均": ss["平均"], "中位": ss["中位"], "lo": ss["lo"], "hi": ss["hi"], "勝率": ss["勝率"]}
    # 兩兩重疊
    key = {m: set(zip(E[m]["sid"], E[m]["T"])) for m in MAIN}
    near = {}
    for m in MAIN:
        d = {}
        for s, T in key[m]:
            d.setdefault(s, []).append(T)
        near[m] = {s: np.array(sorted(v)) for s, v in d.items()}
    ov = {}
    for i, a in enumerate(MAIN):
        for b in MAIN[i + 1:]:
            both = key[a] & key[b]
            def within(A, B):
                k = 0
                for s, T in key[A]:
                    arr = near[B].get(s)
                    if arr is not None and np.min(np.abs(arr - T)) <= 5:
                        k += 1
                return k
            ea = E[a].assign(k=[(s, t) in both for s, t in zip(E[a]["sid"], E[a]["T"])])
            eb = E[b].assign(k=[(s, t) in both for s, t in zip(E[b]["sid"], E[b]["T"])])
            ov["{}×{}".format(a, b)] = {"同檔同T": len(both), "÷{}".format(a): len(both) / len(key[a]), "÷{}".format(b): len(both) / len(key[b]),
                                        "分子組成": mk_split(ea, "k"), "{}分母組成".format(a): mk_split(ea), "{}分母組成".format(b): mk_split(eb),
                                        "±5日內_÷{}".format(a): within(a, b) / len(key[a]), "±5日內_÷{}".format(b): within(b, a) / len(key[b])}
    six["兩兩重疊"] = ov
    # 20 日新高
    nh = {}
    for m in MAIN:
        e = E[m].copy()
        e["nh"] = [bool(ST[s]["nh20"][t]) for s, t in zip(e["sid"], e["T"])]
        a_ = summ(e.loc[e["nh"], "X"], e.loc[e["nh"], "T"], cal, w0); b_ = summ(e.loc[~e["nh"], "X"], e.loc[~e["nh"], "T"], cal, w0)
        dd = e["X"][e["nh"]].mean() - e["X"][~e["nh"]].mean()
        nh[m] = {"重疊率": float(e["nh"].mean()), "重疊數": int(e["nh"].sum()), "分母組成": mk_split(e), "重疊組成": mk_split(e, "nh"),
                 "重疊組X": a_, "不重疊組X": b_, "兩組差": float(dd)}
        E[m]["nh"] = e["nh"].to_numpy()
    six["與收盤創20日新高"] = nh
    RES["§六"] = six
    print("[§六] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    # ── §八 假訊號臂
    dayset = {}
    for s in sids:
        b = ST[s]["bars"]; b = b[(b >= w0) & (b <= wE)]
        mon = np.array([str(cal[t])[:7] for t in b])
        for mo in np.unique(mon):
            dayset[(s, mo)] = b[mon == mo]
    FK = []; fchk = {}
    for m in MAIN:
        real = Counter((s, str(cal[t])[:7]) for s, t in zip(E[m]["sid"], E[m]["T"]))
        grp = sorted(real)
        ok_all = True; short = 0; n_fx = []
        for r in range(reps):
            rng = np.random.default_rng(SEED + r)
            drawn = {}
            for g in grp:
                days = dayset[g]; k = real[g]
                if k > len(days):
                    short += 1; k = len(days)
                pick = np.sort(rng.choice(days, size=k, replace=False))
                drawn.setdefault(g[0], []).extend(int(x) for x in pick)
            got = Counter()
            for s, ts in drawn.items():
                for t in ts:
                    got[(s, str(cal[t])[:7])] += 1
            ok_all &= (got == real)
            xs, Ts = [], []; acc = Counter()
            for s in sorted(drawn):
                S = ST[s]
                for T, first, _, stt in status([(t, t, None) for t in sorted(drawn[s])], S, w0, wE):
                    acc[stt] += 1
                    if stt == "保留":
                        xs.append(S["px"][T + H_OUT] / S["o"][T + 1] - 1.0 - EW[20][T + 1]); Ts.append(T)
            sf = summ(xs, Ts, cal, w0)
            pas = not (sf["lo"] <= 0 <= sf["hi"])
            FK.append({"畫法": m, "r": r, "種子": SEED + r, "抽出": int(sum(acc.values())), "保留": sf["n"], "合併掉": acc["合併掉"],
                       "剔除": int(sum(acc.values()) - acc["保留"] - acc["合併掉"]), "平均X": sf["平均"], "lo": sf["lo"], "hi": sf["hi"],
                       "n_eff": sf["n_eff"], "判過": bool(pas), "判過_正": bool(pas and sf["平均"] > 0), "判過_負": bool(pas and sf["平均"] < 0)})
        fchk[m] = {"每(檔,曆月)抽出筆數＝真事件筆數（30 次全部）": bool(ok_all), "可抽天數不足的組數": short,
                   "(檔,曆月)組數": len(grp), "真事件數": int(sum(real.values()))}
        print("[假訊號臂 {}] 同檔同曆月同筆數 {}｜{:.0f}s".format(m, ok_all, time.time() - t0), flush=True)
    FK = pd.DataFrame(FK); FK.to_csv(os.path.join(OUT, "fake_arm.csv"), index=False, encoding="utf-8")
    CHK["假訊號臂分佈"] = fchk
    fake = {}
    for m in MAIN:
        f = FK[FK["畫法"] == m]
        fake[m] = {"x／30（CI不含0，兩側）": int(f["判過"].sum()), "其中(+)": int(f["判過_正"].sum()), "其中(−)": int(f["判過_負"].sum()),
                   "次數": int(len(f)), "平均X的平均": float(f["平均X"].mean()), "平均X範圍": [float(f["平均X"].min()), float(f["平均X"].max())],
                   "平均保留數": float(f["保留"].mean())}
        J[m]["假訊號"] = fake[m]
    RES["§八假訊號臂"] = fake
    print("[§八] {}｜{:.0f}s".format({m: fake[m]["x／30（CI不含0，兩側）"] for m in MAIN}, time.time() - t0), flush=True)

    # ── §七 描述臂（⛔ 不印判定）
    dsc = {}
    # a 鄰格
    a_ = {}
    for meth, R in PIV_CFG[2:]:
        e = kept_df((meth, R, "close")); a_["{}_R{}".format(meth, R)] = {**summ(e["X"], e["T"], cal, w0), "事件帳": acct((meth, R, "close"))}
    for N, r2 in REG_GRID:
        if (N, r2) == (TM.REG_N, TM.REG_R2):
            continue
        e = kept_df(("丙", (N, r2), "close")); a_["丙_N{}_R2{}".format(N, r2)] = {**summ(e["X"], e["T"], cal, w0), "事件帳": acct(("丙", (N, r2), "close"))}
    for m in MAIN:
        for rule, nm_ in (("pct1", "穿越1%"), ("d3p3", "3日3%站穩")):
            e = kept_df((m, 5, rule)); a_["{}_{}".format(m, nm_)] = {**summ(e["X"], e["T"], cal, w0), "事件帳": acct((m, 5, rule))}
    dsc["a_鄰格"] = a_
    print("[描述臂 a] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    def x_at(S, T, x):
        g = S["px"][x] / S["o"][T + 1] - 1.0
        return g - COST, g - EW[x - (T + 1)][T + 1], x - (T + 1)

    # b 假突破出場
    b_ = {}
    for m in MAIN:
        rows = []
        for ev in E[m].itertuples():
            S = ST[ev.sid]; bars = S["bars"]; cb = S["c"][bars]; tb = int(ev.T_bar); T = int(ev.T)
            if m == "丙":
                line = lambda j, yb=ev.ybar, sl=ev.slope, tb=tb: reg_line(yb, sl, TM.REG_N, j - (tb - TM.REG_N))
            else:                                # (甲)(乙)：線值由取點的還原 high 重建（同 TM._select 的式子）
                p1 = int(np.searchsorted(bars, ev.anchors[0])); p2 = int(np.searchsorted(bars, ev.anchors[1]))
                h_b = S["h"][bars]
                slope = (h_b[p2] - h_b[p1]) / (p2 - p1); h1 = h_b[p1]
                line = lambda j, h1=h1, slope=slope, p1=p1: h1 + slope * (j - p1)
            x = T + H_OUT; j = tb + 1
            while j < len(bars) and bars[j] <= T + 20:
                if cb[j] < line(j):
                    x = int(bars[j]) + 1; break
                j += 1
            Rb, Xb, Hb = x_at(S, T, x)
            rows.append({"early": x < T + H_OUT, "hold": Hb, "Rb": Rb, "Xb": Xb, "R": ev.R, "X": ev.X, "T": T})
        B = pd.DataFrame(rows)
        dR = B["Rb"] - B["R"]; dX = B["Xb"] - B["X"]; ear = B[B["early"]]
        b_[m] = {"n": len(B), "提早出場比例": float(B["early"].mean()), "提早出場數": int(B["early"].sum()), "平均持有日": float(B["hold"].mean()),
                 "b_平均R": float(B["Rb"].mean()), "b_中位R": float(B["Rb"].median()), "b_最差R": float(B["Rb"].min()), "b_平均X": float(B["Xb"].mean()),
                 "固定20_平均R": float(B["R"].mean()), "固定20_最差R": float(B["R"].min()),
                 "配對差R（b−固定）": summ(dR, B["T"], cal, w0), "配對差X": summ(dX, B["T"], cal, w0),
                 "放棄組（被提早出場那批）": {"n": int(len(ear)), "實際_平均R": float(ear["Rb"].mean()), "照抱20日_平均R": float(ear["R"].mean()),
                                    "照抱20日_中位R": float(ear["R"].median()), "照抱20日_平均X": float(ear["X"].mean())}}
    dsc["b_假突破出場"] = b_
    print("[描述臂 b] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    # c 持有 60 日
    c_ = {}
    for m in MAIN:
        xs, Ts, rs, skip_w, skip_b = [], [], [], 0, 0
        for ev in E[m].itertuples():
            T = int(ev.T); S = ST[ev.sid]
            if T + 61 > w1:
                skip_w += 1; continue
            if H2.brk(S, int(ev.first), T + 61):
                skip_b += 1; continue
            g = S["px"][T + 61] / S["o"][T + 1] - 1.0
            xs.append(g - EW[60][T + 1]); rs.append(g - COST); Ts.append(T)
        s60 = summ(xs, Ts, cal, w0, blk=60, cap=WIN_DAYS // 60)
        c_[m] = {**s60, "平均R": float(np.mean(rs)), "排除_T+61超過窗尾": skip_w, "排除_延伸段硬斷點": skip_b}
    dsc["c_持有60日"] = c_

    # d 控制組
    d_ = {}
    VAL = np.column_stack([ST[s]["valid"] for s in sids]); R20 = np.column_stack([ST[s]["r20"] for s in sids])
    TRD1 = np.column_stack([ST[s]["trd"] & np.isfinite(ST[s]["o"]) & ~ST[s]["up_o"] for s in sids])
    HB = np.zeros((n, Sn), bool)
    Tr = np.arange(n - H_OUT)
    for i, s in enumerate(sids):
        S = ST[s]; bb = Tr + H_OUT
        pbc = S["cs_pb"][bb] - np.where(Tr > 0, S["cs_pb"][np.maximum(Tr - 1, 0)], 0)
        g5c = S["cs_g5"][bb] - S["cs_g5"][Tr + 3]
        HB[:n - H_OUT, i] = (pbc > 0) | (g5c > 0)
    G20 = np.full((n, Sn), np.nan)
    Od = np.where(okO, O, np.nan)
    G20[:n - H_OUT] = PX[H_OUT:] / Od[1:n - H_OUT + 1] - 1.0     # G20[T] ＝ px(T+21)／open(T+1) − 1
    for m in MAIN:
        RAW = np.zeros((n, Sn), bool)
        for s in sids:
            t_ = ST[s]["raw"][m]
            RAW[t_, sidx[s]] = True
        rows = []; noval = 0; nctl = []
        for T, grp in E[m].groupby("T"):
            base = VAL[T] & np.isfinite(R20[T])
            idx = np.flatnonzero(base)
            dec = np.full(Sn, -1)
            if len(idx) >= 10:
                dec[idx] = pd.qcut(pd.Series(R20[T, idx]).rank(method="first"), 10, labels=False).to_numpy()
            elig = base & TRD1[T + 1] & ~HB[T] & ~RAW[T] & np.isfinite(G20[T])
            for ev in grp.itertuples():
                i = sidx[ev.sid]
                if dec[i] < 0:
                    noval += 1; continue
                cm = elig & (dec == dec[i]); cm[i] = False
                if not cm.any():
                    noval += 1; continue
                rows.append({"T": T, "d": ev.g - float(G20[T, cm].mean()), "ctl": float(G20[T, cm].mean()) - COST, "R": ev.R}); nctl.append(int(cm.sum()))
        Dd = pd.DataFrame(rows)
        d_[m] = {**summ(Dd["d"], Dd["T"], cal, w0), "訊號組平均R": float(Dd["R"].mean()), "控制組平均R": float(Dd["ctl"].mean()),
                 "無十分位或無控制而略過": noval, "每事件控制數_中位": float(np.median(nctl)), "每事件控制數_最小": int(np.min(nctl))}
    dsc["d_控制組_同T同近20日報酬十分位"] = d_
    print("[描述臂 c、d] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    # e 放棄組：(乙) 三點驗證沒過
    ea = E["甲"].copy()
    ea["乙選取"] = [ST[s]["why_yi"].get(int(cf), "（該根無乙選取）") for s, cf in zip(ea["sid"], ea["conf"])]
    e_ = {"定義": "(甲) 保留事件，按該線確認根收盤時 (乙) 的選取結果分組"}
    for w, g in ea.groupby("乙選取"):
        e_[w] = {**summ(g["X"], g["T"], cal, w0), "平均R": float(g["R"].mean())}
    e_["放棄組＝第三點偏離"] = e_.get("第三點偏離", {"n": 0})
    dsc["e_乙三點驗證沒過_照甲買"] = e_

    # f 保本移動停損
    f_ = {}
    for m in MAIN:
        rows = []; na = 0
        for ev in E[m].itertuples():
            T = int(ev.T); S = ST[ev.sid]; bars = S["bars"]
            Ep = S["o"][T + 1]; Sp = S["l"][T]
            if not (np.isfinite(Sp) and Ep > Sp):
                na += 1; continue
            oneR = Ep - Sp
            js = bars[(bars > T) & (bars <= T + 20)]
            x1 = T + H_OUT
            for j in js:
                if S["c"][j] < Sp:
                    x1 = int(j) + 1; break
            x2 = T + H_OUT; stop = Sp; kind2 = "20日"; moved = False
            for j in js:
                if S["c"][j] < stop:
                    x2 = int(j) + 1; kind2 = "保本出場" if moved else "初始停損"; break
                if S["c"][j] >= Ep + oneR:
                    stop = Ep; moved = True
            r1, X1, h1 = x_at(S, T, x1); r2, X2, h2 = x_at(S, T, x2)
            r60 = (S["px"][T + 61] / Ep - 1.0 - COST) if (T + 61 <= w1 and not H2.brk(S, int(ev.first), T + 61)) else np.nan
            rows.append({"T": T, "R": ev.R, "X": ev.X, "r1": r1, "X1": X1, "h1": h1, "e1": x1 < T + H_OUT,
                         "r2": r2, "X2": X2, "h2": h2, "k2": kind2, "r60": r60})
        F = pd.DataFrame(rows)
        def blk(col_r, col_x, col_h, early):
            return {"出場比例": float(early.mean()), "出場數": int(early.sum()), "平均持有日": float(F[col_h].mean()),
                    "平均R": float(F[col_r].mean()), "中位R": float(F[col_r].median()), "最差R": float(F[col_r].min()), "平均X": float(F[col_x].mean()),
                    "配對差R（對固定20日）": summ(F[col_r] - F["R"], F["T"], cal, w0)}
        e2 = F["k2"] != "20日"
        ab1 = F[F["e1"]]; ab2 = F[e2]; ab2b = F[F["k2"] == "保本出場"]
        f_[m] = {"n": int(len(F)), "E≤S不適用": na,
                 "f1": blk("r1", "X1", "h1", F["e1"]), "f2": {**blk("r2", "X2", "h2", e2), "保本出場數": int((F["k2"] == "保本出場").sum()),
                                                             "初始停損數": int((F["k2"] == "初始停損").sum())},
                 "f2−f1（R）": summ(F["r2"] - F["r1"], F["T"], cal, w0),
                 "固定20日": {"平均R": float(F["R"].mean()), "中位R": float(F["R"].median()), "最差R": float(F["R"].min())},
                 "放棄組_f1被停損": {"n": int(len(ab1)), "實際平均R": float(ab1["r1"].mean()), "照抱20日_平均R": float(ab1["R"].mean()), "照抱20日_中位R": float(ab1["R"].median()),
                                "照抱60日_平均R": float(ab1["r60"].mean()), "照抱60日_中位R": float(ab1["r60"].median()), "60日可算數": int(ab1["r60"].notna().sum())},
                 "放棄組_f2被停損或保本": {"n": int(len(ab2)), "實際平均R": float(ab2["r2"].mean()), "照抱20日_平均R": float(ab2["R"].mean()), "照抱20日_中位R": float(ab2["R"].median()),
                                   "照抱60日_平均R": float(ab2["r60"].mean()), "照抱60日_中位R": float(ab2["r60"].median()), "60日可算數": int(ab2["r60"].notna().sum())},
                 "放棄組_f2保本出場那批": {"n": int(len(ab2b)), "照抱20日_平均R": float(ab2b["R"].mean()), "照抱20日_中位R": float(ab2b["R"].median()),
                                   "照抱60日_平均R": float(ab2b["r60"].mean()), "照抱60日_中位R": float(ab2b["r60"].median())}}
    dsc["f_保本移動停損"] = f_
    RES["§七描述臂"] = dsc
    print("[描述臂 e、f] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    # ── 查核：獨立路（直接讀原始價＋還原因子）手算 20 筆 R_e 與 5 天基準
    import researchM_check as MC
    rng = np.random.default_rng(SEED)
    pick = []
    for m in MAIN:
        k = 7 if m != "丙" else 6
        ii = rng.choice(len(E[m]), size=min(k, len(E[m])), replace=False)
        for i in ii:
            r = E[m].iloc[int(i)]
            pick.append({"畫法": m, "sid": r["sid"], "T": str(cal[int(r["T"])].date()), "T1": str(cal[int(r["T"]) + 1].date()),
                         "T21": str(cal[int(r["T"]) + 21].date()), "R": float(r["R"]), "EW20": float(r["EW"])})
    CHK["獨立路"] = MC.run(pick[:20], list(U["stock_id"]) if not lim else sids, n_days=5)
    print("[查核 獨立路] R_e 20 筆最大差 {:.1e}｜基準 {} 天最大差 {:.1e}".format(CHK["獨立路"]["R_e最大差"], CHK["獨立路"]["基準天數"], CHK["獨立路"]["基準最大差"]), flush=True)
    RES["查核"] = CHK
    json.dump(RES, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))



if __name__ == "__main__":
    main()
