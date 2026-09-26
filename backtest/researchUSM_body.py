# -*- coding: utf-8 -*-
"""USREG-M 本體（美股移植 PREREGM：下降趨勢線被收盤向上突破，三種畫法並測）——判定三格、CI、出口、§六 必報、§七 描述臂 a～f、§八 假訊號臂。

判準：美股登錄 seq2（a3c98a07e882a574，正文）＋seq3（81bfc48eff6258f5）＋seq4（cbfc7610923b9e53）＋seq5（ffb22ecb1bd749ff）；
     移植來源 台股 PREREGM seq1（9316840579a8d33a）§四～§九；pre 段 commit dd474c0e7b（backtest/researchUSM.py）。
讀法：裁定 seq214 §三（照回測 pre 段建議；協調者轉達定案 R1～R4、B1～B7）＝
 R1 T 當天不在指數的偵測事件 ⇒ 不是事件、⛔ 不開合併窗（pre U4 主讀法）
 R2 還原跳躍 ⇒ P0：只認轉接層 hard_break（seam／split_div）；⛔ 不加 0.55／1.8 收盤比門檻
 R3 停牌 ⇒ S1：[最早取點（丙：回歸窗起點）, T+21] 內任一交易日沒有有效 K 棒 ⇒ 硬斷點
    （只數該股第一根～最後一根有效 K 棒之間；最後一根之後＝下市，同台股 Q5；UA 那根無效 K 棒也算「沒有 K 棒」）
 R4 持有期內移出指數 ⇒ E0：照抱到 T+21（scope＝panel 有移出後的價格）；出場價照 B2
 B1 基準 ＝ d＝T+1 當天【在指數（面板 in_index＝1）】且有效 K 棒、還原開盤 > 0 的全部股票，px(d+20)／open(d) − 1 的等權平均
    （台股 B2 同形，gate3 → in_index）；⭐ (d, d+H] 內有轉接層 hard_break 的股票不進該日基準
    （轉接層：⛔ 不跨 seam／split_div 算跨日報酬；0043f97 只有 IR、DHR、XRX 三根）
 B2 出場價 px(j) ＝ 還原 open(j)（j 為有效 K 棒且開盤 > 0）；否則 ＝ ≤ j 最後一根有效 K 棒的還原收盤（下市、移出後停止報價皆同）
 B3 §六「上市／上櫃」⇒ 改「期初已在指數／期中加入」：T 所在那段指數區間的起點 ≤ 窗首 ⇒ 期初已在；否則期中加入
 B4 假訊號臂（seq4；照台股 researchAvg A11／researchPatAll C8）：真事件 ＝ 該格【保留】事件；排除「存在真事件 T_r ∈ [T−20, T]」的日子；
    每檔抽數 ＝ 該檔保留真事件數（全窗）；可抽日 ＝ T ∈ [窗首, 窗尾−21]、當天在指數且有有效 K 棒；不放回；可抽日不足 ⇒ 全取、另報；
    ⛔ 不合併；之後照同一套剔除（[T, T+21] 硬斷點（S1）→ T+1 停牌）、⛔ 不補抽；「不排除」版並列描述。
    種子 default_rng([20260925＋r, crc32(代號), 畫法序號, 版本序號])（逐檔獨立、與行程分工無關）；r＝0…29。
    判過 ＝ 95% CI（月分群）不含 0（兩側）；x ≥ 2 且該格結果② ⇒ 句前加警語、⛔ 不改判定。
 B5 描述臂 d 控制組十分位母體 ＝ T 當天在指數且有效 K 棒、近 20 日報酬可算的股票
 B6 ⛔ 不列預扣稅版
 B7 台股本體 B1～B15、trendline_m M1～M8、researchM_freq Q1～Q8 整套照搬（成本改 0.05% 來回；「T+1 開盤漲停」拿掉）
其餘：成本 0.05% 來回（seq2 §一）；R_e ＝ px(T+21)／open(T+1) − 1 − 0.05%；X_e ＝ R_e −（EW_20(T+1) − 0.05%）；
     主 CI ＝ research11.cl_stats（T 所在曆月 CR0）；非重疊 SE ＝ 20 日區段平均的標準差／√區段數（區段上限 133）；
     n_eff ＝ min(保留事件數, 有事件的區段數)；< 30 出口①、30～99 出口②、≥ 100 出口③。
     Bonferroni：登錄沒有這一條 ⇒ 只描述（三格 α＝0.05／3 的 CI 並列），⛔ 不改判定。
     成本敏感度 0.02%／0.10%：X 裡成本相消 ⇒ 只報 R_e 平均（描述）。

⛔⛔ 授權：resultsUSM/ 只寫彙總（格的平均／中位／CI／判語／筆數／區段／sha）；逐筆事件、逐檔數字寫 ~/us_work/usm/body/（repo 外）並列 sha。
偵測器：backtest/trendline_m.py；描述臂變體偵測：backtest/researchM.py 的 detect_pivot_var／detect_reg_var（只 import、⛔ 未改）。
"""
from __future__ import annotations
import os, sys, time, json, io, csv, zlib
from collections import Counter
from statistics import NormalDist
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import us_data as U
from backtest import trendline_m as TM
from backtest import selftest_trendline_m as STM
from backtest import researchUSM as RU            # pre 段：prep、member_array、span_start_array、assign、usm_fixtures
import researchM as TWM                           # 台股本體：summ、verdict、selftest、描述臂變體偵測器（只 import）

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSM")
WORK = os.path.expanduser("~/us_work/usm/body")
PRE_WORK = os.path.expanduser("~/us_work/usm")
COST = U.COST_ROUNDTRIP                           # 0.05%
COST_SENS = U.COST_SENSITIVITY
H_OUT, MERGE, BLOCK = 21, 20, 20
SEED, REPS = 20260925, 30
PIV_CFG = [("甲", 5), ("乙", 5), ("甲", 3), ("乙", 3), ("甲", 10), ("乙", 10)]
REG_GRID = [(N, r2) for N in (30, 60, 120) for r2 in (0.3, 0.5, 0.7)]
MAIN = ("甲", "乙", "丙")
NAME = {"甲": "(甲) 兩點法", "乙": "(乙) 三點驗證法", "丙": "(丙) 回歸法"}
TW = {"甲": -0.0011, "乙": 0.0001, "丙": -0.0068}      # 台股同格平均 X（M_REPORT，只給 seq2 §二③ 先驗比對用）
Z_BONF = NormalDist().inv_cdf(1 - 0.05 / 3 / 2)
CAL0 = pd.Timestamp("2015-11-02")                    # 日曆從這天起即可（面板最早 2015-12-01）
_G = {}


def _cnt(cs, a, b):
    b = min(b, len(cs) - 1)
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


# ═════════════ 讀檔＋偵測（worker）═════════════
def _init(cal, w0, w1):
    _G.update(cal=cal, w0=w0, w1=w1)


def low_aligned(df, cal):
    """與 RU.prep 同一個「有效 K 棒」遮罩的還原 low（f 臂的 S＝low(T) 要用；RU.prep 沒存 low）。"""
    df = df[df.index.isin(cal)]
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    ok = (l <= np.fmin(o, c)) & (np.fmax(o, c) <= h)
    L = np.full(len(cal), np.nan)
    L[cal.get_indexer(df.index)[ok]] = l[ok]
    return L


class Stk:
    """一檔的陣列與規則（S1 硬斷點、Q2 狀態）。"""

    def __init__(self, t, A, L, member, spanst, w0, wE):
        self.t = t; self.o, self.h, self.c, self.l = A["O"], A["H"], A["C"], L
        self.valid, self.bars, self.pb = A["valid"], A["bars"], A["pb"]
        self.n = len(self.c); self.member = member; self.spanst = spanst
        b = self.bars; self.last = int(b[-1])
        miss = ~self.valid; miss[:b[0]] = False; miss[self.last + 1:] = False
        self.cs_pb = np.cumsum(self.pb); self.cs_ms = np.cumsum(miss)
        self.okO = self.valid & (np.nan_to_num(self.o) > 0)
        cff = pd.Series(self.c).ffill().to_numpy()
        self.px = np.where(self.okO, self.o, cff)
        self.fb = ~self.okO
        self.w0, self.wE = w0, wE

    def brk(self, a, b):
        """R2＝P0、R3＝S1：[a, b] 內有轉接層 hard_break 或任一天沒有有效 K 棒。"""
        return _cnt(self.cs_pb, a, b) > 0 or _cnt(self.cs_ms, a, b) > 0

    def status(self, evs, hold=H_OUT):
        """evs：[(T, first, payload)] 依 T 排序 ⇒ [(T, first, payload, 狀態)]；只收 T ∈ [w0, wE] 且 member[T]∧valid[T]（R1）。"""
        out = []; t_keep = -10 ** 9
        for T, first, pay in evs:
            if not (self.w0 <= T <= self.wE) or not (self.member[T] and self.valid[T]):
                continue
            f_brk = self.brk(first, T + hold)
            f_halt = (T + 1 >= self.n) or (not bool(self.valid[T + 1]))
            if t_keep < T <= t_keep + MERGE:
                st = "合併掉"
            elif f_brk:
                st = "剔除_硬斷點"
            elif f_halt:
                st = "剔除_T+1停牌"
            else:
                st = "保留"; t_keep = T
            out.append((T, first, pay, st))
        return out


def load_one(t):
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]; n = len(cal); wE = w1 - H_OUT
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A = RU.prep(df, cal)
    if len(A["bars"]) == 0:
        return None
    S = Stk(t, A, low_aligned(df, cal), RU.member_array(t, cal), RU.span_start_array(t, cal), w0, wE)
    o, h, c, bars = S.o, S.h, S.c, S.bars
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
    for meth, R in PIV_CFG:
        r = TM.detect_calendar(o, h, c, meth, R)
        evs = [(e["T"], e["first"], {"anchors": e["anchors"], "conf": e["conf"], "T_bar": e["T_bar"]}) for e in r["events"]]
        cfgs[(meth, R, "close")] = S.status(evs)
        if R == 5:
            raw_main[meth] = np.array([e["T"] for e in r["events"]], int)
        v, why = TWM.detect_pivot_var(ob, hb, cb, meth, R, "close")
        a1 = [(e["T"], e["anchors"], e["conf"]) for e in r["events"]]
        a2 = [(toc(e["T"]), tuple(toc(x) for x in e["anchors"]), toc(e["conf"])) for e in v]
        mism[(meth, R)] = int(a1 != a2)
        if (meth, R) == ("乙", 5):
            why_yi = {toc(b): w for b, w in why.items()}
        if R == 5:
            for rule in ("pct1", "d3p3"):
                v2, _ = TWM.detect_pivot_var(ob, hb, cb, meth, R, rule)
                evs2 = [(toc(e["T"]), toc(e["first"]), {"anchors": tuple(toc(x) for x in e["anchors"]), "conf": toc(e["conf"]), "T_bar": e["T"]}) for e in v2]
                cfgs[(meth, R, rule)] = S.status(evs2)
    Tn, yb, sl, _ = TWM.reg_arrays(cb, TM.REG_N)
    for N, r2 in REG_GRID:
        r = TM.detect_calendar(o, h, c, "丙", N=N, r2min=r2)
        if (N, r2) == (TM.REG_N, TM.REG_R2):
            evs = [(e["T"], e["first"], {"T_bar": e["T_bar"], "ybar": float(yb[e["T_bar"] - TM.REG_N]),
                                         "slope": float(sl[e["T_bar"] - TM.REG_N])}) for e in r["events"]]
            raw_main["丙"] = np.array([e["T"] for e in r["events"]], int)
            v = TWM.detect_reg_var(cb, N, r2, "close")
            mism[("丙", 5)] = int([e["T"] for e in r["events"]] != [toc(e["T"]) for e in v])
            for rule in ("pct1", "d3p3"):
                v2 = TWM.detect_reg_var(cb, N, r2, rule)
                cfgs[("丙", 5, rule)] = S.status([(toc(e["T"]), toc(e["first"]), {"T_bar": e["T"]}) for e in v2])
            cfgs[("丙", 5, "close")] = S.status(evs)
        else:
            cfgs[("丙", (N, r2), "close")] = S.status([(e["T"], e["first"], {"T_bar": e["T_bar"]}) for e in r["events"]])
    return {"S": S, "r20": r20, "nh20": nh20, "cfgs": cfgs, "mism": mism, "raw": raw_main, "why_yi": why_yi}


# ═════════════ 基準（B1）═════════════
def ew_us(O, okM, PX, CSPB, H):
    """EW_H(d) ＝ okM[d]（在指數∧有效∧開盤>0）的股票、(d, d+H] 內無 hard_break：PX(d+H)／O(d) − 1 的等權平均。O…：n×S。"""
    n = O.shape[0]; out = np.full(n, np.nan)
    Od = np.where(okM[:n - H], O[:n - H], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = PX[H:] / Od - 1.0
    r[(CSPB[H:] - CSPB[:n - H]) > 0] = np.nan
    cnt = np.isfinite(r).sum(axis=1); s = np.nansum(r, axis=1)
    out[:n - H] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out


def ew_brute(stocks, d, H):
    """⭐ 獨立寫法（逐檔迴圈、不共用 ew_us 任何一行）：stocks：list of (o, c, mem, pb)。"""
    tot, k = 0.0, 0
    for o, c, mem, pb in stocks:
        if not (mem[d] and np.isfinite(c[d]) and np.isfinite(o[d]) and o[d] > 0):
            continue
        if any(pb[d + 1:d + H + 1]):
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


def body_fixtures():
    """UB1 基準向量法＝獨立迴圈法（在指數與否、停牌、下市、上市前、斷點排除）｜UB2 全體＝事件股 ⇒ X＝0｜UB3 0 報酬 ⇒ R_e＝−0.05%、X＝0｜
    UB4 已知報酬 ⇒ X＝+10%｜UB5 S1 硬斷點與狀態（Stk.status）｜UB6 假訊號可抽日的排除窗 [T−20, T]。"""
    rng = np.random.default_rng(11)
    n, S_ = 90, 7
    O = np.exp(rng.normal(0, 0.03, (n, S_)).cumsum(axis=0)) * 50; C = O * np.exp(rng.normal(0, 0.01, (n, S_)))
    C[10:13, 1] = np.nan; O[10:13, 1] = np.nan                  # 停牌 3 日
    C[50:, 2] = np.nan; O[50:, 2] = np.nan                      # 第 50 日起下市
    C[:30, 3] = np.nan; O[:30, 3] = np.nan                      # 第 30 日才有資料
    MEM = np.ones((n, S_), bool); MEM[:40, 4] = False; MEM[60:, 5] = False   # 第 40 日才入指數／第 60 日移出（價格照有）
    PB = np.zeros((n, S_), bool); PB[45, 6] = True               # 第 45 日 hard_break
    valid = np.isfinite(C); okO = valid & np.isfinite(O) & (O > 0)
    cff = pd.DataFrame(C).ffill().to_numpy(); PX = np.where(okO, O, cff)
    CS = np.cumsum(PB, axis=0)
    stocks = [(O[:, j], C[:, j], MEM[:, j], PB[:, j]) for j in range(S_)]
    worst = 0.0; npts = 0
    for H in (1, 5, 20):
        ew = ew_us(O, okO & MEM, PX, CS, H)
        for d in range(0, n - H):
            b = ew_brute(stocks, d, H); npts += 1
            worst = max(worst, abs(ew[d] - b) if np.isfinite(b) else (0 if np.isnan(ew[d]) else 1))
    assert worst < 1e-12, worst
    # 斷點排除真的有作用：d＝30、H＝20 的第 6 檔被排除
    e_ex = ew_us(O, okO & MEM, PX, CS, 20)[30]; e_in = ew_us(O, okO & MEM, PX, np.zeros_like(CS), 20)[30]
    assert abs(e_ex - e_in) > 1e-6
    T = 30
    o1 = O[:, [0]]; e1 = ew_us(o1, okO[:, [0]], PX[:, [0]], CS[:, [0]], 20)
    X = (PX[T + 21, 0] / o1[T + 1, 0] - 1 - COST) - (e1[T + 1] - COST)
    assert abs(X) < 1e-15, X
    Oc = np.full((n, 4), 20.0); okc = np.ones((n, 4), bool); zc = np.zeros((n, 4), int)
    ec = ew_us(Oc, okc, Oc, zc, 20)
    Re = Oc[T + 21, 2] / Oc[T + 1, 2] - 1 - COST; X = Re - (ec[T + 1] - COST)
    assert abs(Re + COST) < 1e-15 and abs(X) < 1e-15, (Re, X)
    Od = np.full((n, 2), 10.0); Od[T + 21:, 0] = 11.0; Od[T + 21:, 1] = 9.0
    ed = ew_us(Od, np.ones((n, 2), bool), Od, np.zeros((n, 2), int), 20)
    X = (Od[T + 21, 0] / Od[T + 1, 0] - 1 - COST) - (ed[T + 1] - COST)
    assert abs(X - 0.10) < 1e-12, X
    # UB5 Stk.status：S1、R1、合併、T+1 停牌
    m = 120
    c = np.linspace(100, 80, m); o = c + 0.1; h = c + 0.5
    A = {"O": o.copy(), "H": h.copy(), "C": c.copy(), "valid": np.ones(m, bool), "bars": np.arange(m), "pb": np.zeros(m, bool)}
    A["C"][60] = np.nan; A["O"][60] = np.nan; A["valid"][60] = False; A["bars"] = np.flatnonzero(A["valid"])
    mem = np.ones(m, bool); mem[90] = False
    Sx = Stk("fx", A, c - 0.5, mem, np.full(m, np.datetime64("2010-01-01"), dtype="datetime64[ns]"), 0, m - 22)
    ev = [(30, 30, None), (38, 38, None), (40, 35, None), (55, 45, None), (70, 61, None), (75, 75, None), (90, 90, None), (59, 59, None)]
    ev = sorted(ev, key=lambda x: x[0])
    st = [s for *_, s in Sx.status(ev)]
    # 30 保留｜38、40 合併（先判合併）｜55 斷點（[45,76] 含 60）｜59 斷點（T+1＝60 缺，先判斷點）｜70 [61,91] 無缺 ⇒ 保留｜75 合併｜90 不在指數 ⇒ 不是事件
    assert st == ["保留", "合併掉", "合併掉", "剔除_硬斷點", "剔除_硬斷點", "保留", "合併掉"], st
    # UB6 排除窗：真事件 T_r＝50 ⇒ 排除 50～70，71 可抽、49 可抽
    real = np.array([50]); cand = np.arange(40, 80)
    keep = cand[~excl_mask(cand, real)]
    assert 49 in keep and 71 in keep and not any(50 <= x <= 70 for x in keep), keep
    msg = ("UB1 基準向量法＝獨立迴圈法（在指數／移出／停牌／下市／上市前／斷點排除；H＝1、5、20 共 {} 點）最大差 {:.1e}、斷點排除有作用｜"
           "UB2 全體＝事件股 ⇒ X＝0｜UB3 0 報酬 ⇒ R_e＝−0.05%、X＝0｜UB4 已知 X＝+10%｜"
           "UB5 狀態機（S1 缺日斷點、合併、T+1 缺先判斷點、T 不在指數不是事件）｜UB6 假訊號排除窗 [T−20, T]").format(npts, worst)
    print("✅ 本體自測：" + msg, flush=True)
    return msg


def excl_mask(cand, real):
    """cand 中「存在 real 的 T_r ∈ [d−20, d]」的布林遮罩（B4）。"""
    if len(real) == 0:
        return np.zeros(len(cand), bool)
    real = np.sort(real)
    i = np.searchsorted(real, cand, side="right")            # real[i−1] ≤ d 的最後一個
    prev = np.where(i > 0, real[np.maximum(i - 1, 0)], -10 ** 9)
    return (i > 0) & (cand - prev <= 20)


# ═════════════ 統計 ═════════════
def summ(x, T, cal, w0, blk=BLOCK, cap=None):
    return TWM.summ(x, T, cal, w0, blk=blk, cap=cap if cap is not None else _G["cap"])


def grp_split(df, col=None):
    d = df if col is None else df[df[col]]
    return {"分母": int(len(d)), "期初已在": int((d["grp"] == "期初已在").sum()), "期中加入": int((d["grp"] == "期中加入").sum())}


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def pp(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}pp"


def sha256f(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ═════════════ 主程式 ═════════════
def main():
    t0 = time.time()
    U.assert_pinned()
    fx = {"台股F1_F8": STM.run_all(), "台股本體自測（researchM.selftest，驗 import 來的 summ／變體偵測器）": TWM.selftest(),
          "美股UF1_UF8": RU.usm_fixtures(), "本體UB1_UB6": body_fixtures()}
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else REPS
    calF = U.load_calendar(); cal = calF[calF >= CAL0]; n = len(cal)
    w0 = int(cal.searchsorted(U.WINDOW[0])); w1 = int(cal.searchsorted(U.WINDOW[1]))
    assert cal[w0] == U.WINDOW[0] and cal[w1] == U.WINDOW[1]
    wE = w1 - H_OUT
    cap = -(-(wE - w0 + 1) // BLOCK); _G["cap"] = cap
    cap60 = (w1 - w0 + 1) // 60
    tick = [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]
    if lim:
        tick = tick[:lim]
    print("[資料] us-stock-data {}｜日曆 {}～（{} 根）｜判定窗 {}～{}｜T 可落 ～{}｜區段上限 {}｜有 OHLC {} 檔".format(
        U.data_commit()[:10], cal[0].date(), n, cal[w0].date(), cal[w1].date(), cal[wE].date(), cap, len(tick)), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1)) as pool:
        res = pool.map(load_one, tick, chunksize=4)
    ST = {r["S"].t: r for r in res if r is not None}
    sids = sorted(ST); sidx = {s: i for i, s in enumerate(sids)}
    print("[讀檔＋偵測] 可用 {} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    CHK = {"fixture": fx}

    # ── 查核 1：與 pre 段事件檔（~/us_work/usm/events_*.csv）逐列相同；狀態 ＝ 把 pre 的旗標換成 S1 讀法後重排的結果
    rows_equal = {}
    for meth, R in PIV_CFG + [("丙", 5)]:
        nm = RU.cfg_name(meth, R)
        ref = pd.read_csv(os.path.join(PRE_WORK, "events_{}.csv".format(nm)), dtype=str)
        if lim:
            ref = ref[ref["ticker"].isin(sids)]
        ref = ref.sort_values(["ticker", "T"], kind="stable").reset_index(drop=True)
        exp_st = []
        for t, g in ref.groupby("ticker", sort=True):
            evs = [{"T": i, "reason": ("硬斷點" if (fb == "1" or fg == "1") else ("T+1停牌" if fh == "1" else ""))}
                   for i, fb, fg, fh in zip(range(len(g)), g["f_brk"], g["f_gap1"], g["f_halt"])]
            Ts = pd.to_datetime(g["T"]).map(lambda d: int(cal.get_loc(d))).tolist()
            for e, T in zip(evs, Ts):
                e["T"] = T
            st, _ = RU.assign(evs)
            exp_st += st
        rows = []
        for s in sids:
            for T, first, pay, stt in ST[s]["cfgs"][(meth, R, "close")]:
                r_ = {"ticker": s, "T": str(cal[T].date()), "first": str(cal[first].date())}
                if meth != "丙":
                    r_["anchors"] = "|".join(str(cal[a].date()) for a in pay["anchors"]); r_["conf"] = str(cal[pay["conf"]].date())
                r_["狀態"] = stt
                rows.append(r_)
        mine = pd.DataFrame(rows).sort_values(["ticker", "T"], kind="stable").reset_index(drop=True)
        cols = [c_ for c_ in ("ticker", "T", "first", "anchors", "conf") if c_ in mine]
        same_rows = mine.shape[0] == ref.shape[0] and bool((mine[cols].values == ref[cols].fillna("").values).all())
        same_st = same_rows and list(mine["狀態"]) == exp_st
        rows_equal[nm] = {"列數_本體": int(len(mine)), "列數_pre": int(len(ref)), "偵測逐列相同": same_rows, "狀態＝pre旗標改S1重排": same_st,
                          "保留": int((mine["狀態"] == "保留").sum()), "pre狀態欄（S0）保留": int((ref["狀態"] == "保留").sum())}
        print("[查核1] {}：本體 {:,} 列／pre {:,} 列｜偵測 {}｜狀態 {}｜保留 {:,}（pre S0 {:,}）".format(
            nm, len(mine), len(ref), same_rows, same_st, rows_equal[nm]["保留"], rows_equal[nm]["pre狀態欄（S0）保留"]), flush=True)
        if not same_st:
            raise SystemExit("⛔ 本體事件與 pre 段不一致：{} ⇒ 中止（未算任何報酬）".format(nm))
    CHK["事件與pre段逐列相同"] = rows_equal
    mm = Counter()
    for s in sids:
        for k, v in ST[s]["mism"].items():
            mm[RU.cfg_name(*k)] += v
    CHK["變體偵測close版與trendline_m不同的檔數"] = dict(mm)
    assert sum(mm.values()) == 0, mm

    # ── 矩陣與基準
    Sn = len(sids); SS = {s: ST[s]["S"] for s in sids}
    O = np.column_stack([SS[s].o for s in sids]); okO = np.column_stack([SS[s].okO for s in sids])
    PX = np.column_stack([SS[s].px for s in sids]); MEM = np.column_stack([SS[s].member for s in sids])
    CSPB = np.column_stack([SS[s].cs_pb for s in sids])
    okM = okO & MEM
    EW = {H: ew_us(O, okM, PX, CSPB, H) for H in range(1, 61)}
    ew_n = (okM[w0:wE + 2]).sum(axis=1)
    print("[基準] EW_H，H＝1…60｜每日成分數 中位 {:.0f}（{}～{}）｜{:.0f}s".format(np.median(ew_n), ew_n.min(), ew_n.max(), time.time() - t0), flush=True)
    wstart = np.datetime64(cal[w0])

    def kept_df(key):
        rows = []
        for s in sids:
            S = SS[s]
            for T, first, pay, stt in ST[s]["cfgs"][key]:
                if stt != "保留":
                    continue
                P0 = S.o[T + 1]; ex = S.px[T + H_OUT]; g = ex / P0 - 1.0
                rows.append({"sid": s, "T": T, "first": first, "g": g, "R": g - COST, "EW": EW[20][T + 1], "X": g - EW[20][T + 1],
                             "退路": bool(S.fb[T + H_OUT]), "移出": bool((~S.member[T + 1:T + H_OUT + 1]).any()),
                             "grp": "期初已在" if S.spanst[T] <= wstart else "期中加入", **(pay or {})})
        return pd.DataFrame(rows)

    def acct(key):
        a = Counter(stt for s in sids for _, _, _, stt in ST[s]["cfgs"][key])
        return {"母體內原始": int(sum(a.values())), "合併掉": a["合併掉"], "剔除_硬斷點": a["剔除_硬斷點"], "剔除_T+1停牌": a["剔除_T+1停牌"], "保留": a["保留"]}

    RES = {"性質": "USREG-M 本體（單筆層事件研究；判定三格 N_前段 美股 +3）",
           "登錄": {"seq2": "a3c98a07e882a574", "seq3": "81bfc48eff6258f5", "seq4": "cbfc7610923b9e53", "seq5": "ffb22ecb1bd749ff",
                  "台股原件PREREGM_seq1": "9316840579a8d33a", "pre段commit": "dd474c0e7b", "讀法": "裁定 seq214 §三（R1 不開窗／R2 P0／R3 S1／R4 E0＋B2／B1～B7）"},
           "資料commit": U.data_commit(), "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "T可落": [str(cal[w0].date()), str(cal[wE].date())],
           "可用檔數": len(ST), "成本來回": COST, "區段上限": int(cap), "60日區段上限": int(cap60),
           "基準每日成分數": {"中位": float(np.median(ew_n)), "最少": int(ew_n.min()), "最多": int(ew_n.max())},
           "§六_頻率（引 pre_freq.json）": {m: json.load(open(os.path.join(OUT, "pre_freq.json"), encoding="utf-8"))["畫法"][m]["每檔每年_在指數日分母（主）"] for m in MAIN}}
    E = {}; J = {}
    for m in MAIN:
        E[m] = kept_df((m, 5, "close"))
        s_ = summ(E[m]["X"], E[m]["T"], cal, w0); ex_, rs_ = TWM.verdict(s_)
        sR = summ(E[m]["R"], E[m]["T"], cal, w0)
        J[m] = {**s_, "出口": ex_, "結果": rs_, "事件帳": acct((m, 5, "close")),
                "Bonferroni_α0.05／3_CI（描述）": [s_["平均"] - Z_BONF * s_["se_月"], s_["平均"] + Z_BONF * s_["se_月"]],
                "R_e": {"平均": sR["平均"], "中位": sR["中位"], "R>0": sR["勝率"], "R>0數": sR["勝數"], "最差": sR["最差"], "p10": sR["p10"], "p90": sR["p90"],
                        "成本敏感度_平均R_e": {str(k_): float(E[m]["g"].mean() - k_) for k_ in (COST_SENS[0], COST, COST_SENS[1])}},
                "基準平均（EW−0.05%）": float(E[m]["EW"].mean() - COST), "勝率分母組成": grp_split(E[m]),
                "出場用退路（B2）": int(E[m]["退路"].sum()), "持有期內移出指數（R4 E0 照抱）": int(E[m]["移出"].sum())}
        print("[{}] 保留 {:,}｜n_eff {}｜平均X {}（CI {} ～ {}；非重疊 {} ～ {}）｜{} {}".format(
            m, s_["n"], s_["n_eff"], pct(s_["平均"]), pct(s_["lo"]), pct(s_["hi"]), pct(s_["lo_非重疊"]), pct(s_["hi_非重疊"]), ex_, rs_), flush=True)
    RES["判定三格"] = J
    shas = []
    for m in MAIN:
        p = os.path.join(WORK, "events_X_{}.csv".format(m))
        e = E[m].drop(columns=[c_ for c_ in ("anchors",) if c_ in E[m]]).copy()
        e.insert(1, "T_date", [str(cal[t].date()) for t in e["T"]])
        e.insert(2, "T1_date", [str(cal[t + 1].date()) for t in e["T"]])
        e.insert(3, "T21_date", [str(cal[t + H_OUT].date()) for t in e["T"]])
        e.insert(4, "first_date", [str(cal[t].date()) for t in e["first"]])
        if m != "丙":
            e["anchors_dates"] = ["|".join(str(cal[a].date()) for a in an) for an in E[m]["anchors"]]
            e["conf_date"] = [str(cal[int(c_)].date()) for c_ in E[m]["conf"]]
        e.to_csv(p, index=False, encoding="utf-8"); shas.append((os.path.basename(p), len(e), sha256f(p)))

    good = [m for m in MAIN if J[m]["結果"].startswith("結果②")]
    neg = [m for m in MAIN if J[m]["結果"].startswith("結果③")]
    if len(good) == 3:
        comb = "三種畫法都測得出（＋）"
    elif good:
        comb = "只在{}測得出（＋）⇒ 結果隨畫法而變".format("、".join(NAME[g] for g in good))
    else:
        comb = "三種畫法都沒有測得出（＋）"
    if neg:
        comb += "；另：{}測得出（−）".format("、".join(NAME[g] for g in neg))
    RES["三格合句"] = comb

    # ── §六
    six = {}
    for m in MAIN:
        e = E[m]
        six[m] = {g_: summ(e.loc[e["grp"] == g_, "X"], e.loc[e["grp"] == g_, "T"], cal, w0) for g_ in ("期初已在", "期中加入")}
        yr = np.array([cal[t].year for t in e["T"]]); six[m]["逐年"] = {}
        for y in sorted(set(yr)):
            k = yr == y; ss = summ(e["X"][k], e["T"][k], cal, w0)
            six[m]["逐年"][str(y)] = {"n": ss["n"], "平均": ss["平均"], "中位": ss["中位"], "lo": ss["lo"], "hi": ss["hi"], "勝率": ss["勝率"]}
    key = {m: set(zip(E[m]["sid"], E[m]["T"])) for m in MAIN}
    near = {}
    for m in MAIN:
        d = {}
        for s, T in key[m]:
            d.setdefault(s, []).append(T)
        near[m] = {s: np.array(sorted(v)) for s, v in d.items()}

    def within(A_, B_):
        k = 0
        for s, T in key[A_]:
            arr = near[B_].get(s)
            if arr is not None and np.min(np.abs(arr - T)) <= 5:
                k += 1
        return k
    ov = {}
    for i, a in enumerate(MAIN):
        for b in MAIN[i + 1:]:
            both = key[a] & key[b]
            ea = E[a].assign(k=[(s, t) in both for s, t in zip(E[a]["sid"], E[a]["T"])])
            ov["{}×{}".format(a, b)] = {"同檔同T": len(both), "÷" + a: len(both) / len(key[a]), "÷" + b: len(both) / len(key[b]),
                                        "分子組成": grp_split(ea, "k"), "±5日內_÷" + a: within(a, b) / len(key[a]), "±5日內_÷" + b: within(b, a) / len(key[b])}
    six["兩兩重疊"] = ov
    nh = {}
    for m in MAIN:
        e = E[m].copy(); e["nh"] = [bool(ST[s]["nh20"][t]) for s, t in zip(e["sid"], e["T"])]
        a_ = summ(e.loc[e["nh"], "X"], e.loc[e["nh"], "T"], cal, w0); b_ = summ(e.loc[~e["nh"], "X"], e.loc[~e["nh"], "T"], cal, w0)
        nh[m] = {"重疊率": float(e["nh"].mean()), "重疊數": int(e["nh"].sum()), "分母組成": grp_split(e), "重疊組成": grp_split(e, "nh"),
                 "重疊組X": a_, "不重疊組X": b_, "兩組差": float(e["X"][e["nh"]].mean() - e["X"][~e["nh"]].mean())}
    six["與收盤創20日新高"] = nh
    RES["§六"] = six
    print("[§六] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    # ── §八 假訊號臂（B4）
    cand0 = {}
    for s in sids:
        S = SS[s]; idx = np.arange(w0, wE + 1)
        cand0[s] = idx[S.member[w0:wE + 1] & S.valid[w0:wE + 1]]
    FK = []; fchk = {}
    for mi, m in enumerate(MAIN):
        real = {s: np.sort(g["T"].to_numpy()) for s, g in E[m].groupby("sid")}
        for vi, vn in enumerate(("新預設_只排除過去20日", "不排除（描述）")):
            cand = {s: (cand0[s][~excl_mask(cand0[s], real[s])] if vi == 0 else cand0[s]) for s in real}
            short = sum(1 for s in real if len(real[s]) > len(cand[s]))
            for r in range(reps):
                xs, Ts = [], []; acc = Counter()
                for s in sorted(real):
                    S = SS[s]; k = min(len(real[s]), len(cand[s]))
                    rng = np.random.default_rng([SEED + r, zlib.crc32(s.encode()), mi, vi])
                    for T in np.sort(rng.choice(cand[s], size=k, replace=False)):
                        T = int(T)
                        if S.brk(T, T + H_OUT):
                            acc["剔除_硬斷點"] += 1; continue
                        if not S.valid[T + 1]:
                            acc["剔除_T+1停牌"] += 1; continue
                        acc["保留"] += 1
                        xs.append(S.px[T + H_OUT] / S.o[T + 1] - 1.0 - EW[20][T + 1]); Ts.append(T)
                sf = summ(xs, Ts, cal, w0)
                pas = not (sf["lo"] <= 0 <= sf["hi"])
                FK.append({"畫法": m, "版本": vn, "r": r, "抽出": int(sum(acc.values())), "保留": sf["n"], "剔除_硬斷點": acc["剔除_硬斷點"],
                           "剔除_T+1停牌": acc["剔除_T+1停牌"], "平均X": sf["平均"], "中位X": sf["中位"], "lo": sf["lo"], "hi": sf["hi"],
                           "n_eff": sf["n_eff"], "判過": bool(pas), "判過_正": bool(pas and sf["平均"] > 0), "判過_負": bool(pas and sf["平均"] < 0)})
            fchk["{}_{}".format(m, vn)] = {"可抽日不足的檔數（全取）": short, "有真事件的檔數": len(real), "真事件數": int(sum(len(v) for v in real.values()))}
        print("[假訊號臂 {}] 完成｜{:.0f}s".format(m, time.time() - t0), flush=True)
    FK = pd.DataFrame(FK)
    p = os.path.join(OUT, "body_fake_arm.csv"); FK.to_csv(p, index=False, encoding="utf-8")
    fake = {}
    for m in MAIN:
        fake[m] = {}
        for vn in ("新預設_只排除過去20日", "不排除（描述）"):
            f = FK[(FK["畫法"] == m) & (FK["版本"] == vn)]
            fake[m][vn] = {"x／30（CI不含0，兩側）": int(f["判過"].sum()), "其中(+)": int(f["判過_正"].sum()), "其中(−)": int(f["判過_負"].sum()),
                           "次數": int(len(f)), "平均X的平均": float(f["平均X"].mean()), "平均X範圍": [float(f["平均X"].min()), float(f["平均X"].max())],
                           "平均保留數": float(f["保留"].mean())}
        J[m]["假訊號"] = fake[m]["新預設_只排除過去20日"]
    RES["§八假訊號臂"] = fake; CHK["假訊號臂抽樣"] = fchk
    print("[§八] {}｜{:.0f}s".format({m: fake[m]["新預設_只排除過去20日"]["x／30（CI不含0，兩側）"] for m in MAIN}, time.time() - t0), flush=True)

    # ── §七 描述臂（⛔ 不印判定）
    dsc = {}
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
        g = S.px[x] / S.o[T + 1] - 1.0
        return g - COST, g - EW[x - (T + 1)][T + 1], x - (T + 1)

    b_ = {}
    for m in MAIN:
        rows = []
        for ev in E[m].itertuples():
            S = SS[ev.sid]; bars = S.bars; cb = S.c[bars]; tb = int(ev.T_bar); T = int(ev.T)
            if m == "丙":
                line = lambda j, yb=ev.ybar, sl=ev.slope, tb=tb: TWM.reg_line(yb, sl, TM.REG_N, j - (tb - TM.REG_N))
            else:
                p1 = int(np.searchsorted(bars, ev.anchors[0])); p2 = int(np.searchsorted(bars, ev.anchors[1]))
                h_b = S.h[bars]; slope = (h_b[p2] - h_b[p1]) / (p2 - p1); h1 = h_b[p1]
                line = lambda j, h1=h1, slope=slope, p1=p1: h1 + slope * (j - p1)
            x = T + H_OUT; j = tb + 1
            while j < len(bars) and bars[j] <= T + 20:
                if cb[j] < line(j):
                    x = int(bars[j]) + 1; break
                j += 1
            Rb, Xb, Hb = x_at(S, T, x)
            rows.append({"early": x < T + H_OUT, "hold": Hb, "Rb": Rb, "Xb": Xb, "R": ev.R, "X": ev.X, "T": T})
        B = pd.DataFrame(rows); ear = B[B["early"]]
        b_[m] = {"n": len(B), "提早出場比例": float(B["early"].mean()), "提早出場數": int(B["early"].sum()), "平均持有日": float(B["hold"].mean()),
                 "b_平均R": float(B["Rb"].mean()), "b_中位R": float(B["Rb"].median()), "b_最差R": float(B["Rb"].min()), "b_平均X": float(B["Xb"].mean()),
                 "固定20_平均R": float(B["R"].mean()), "固定20_最差R": float(B["R"].min()),
                 "配對差R（b−固定）": summ(B["Rb"] - B["R"], B["T"], cal, w0), "配對差X": summ(B["Xb"] - B["X"], B["T"], cal, w0),
                 "放棄組（被提早出場那批）": {"n": int(len(ear)), "實際_平均R": float(ear["Rb"].mean()), "照抱20日_平均R": float(ear["R"].mean()),
                                    "照抱20日_中位R": float(ear["R"].median()), "照抱20日_平均X": float(ear["X"].mean())}}
    dsc["b_假突破出場"] = b_

    c_ = {}
    for m in MAIN:
        xs, Ts, rs, skip_w, skip_b = [], [], [], 0, 0
        for ev in E[m].itertuples():
            T = int(ev.T); S = SS[ev.sid]
            if T + 61 > w1:
                skip_w += 1; continue
            if S.brk(int(ev.first), T + 61):
                skip_b += 1; continue
            g = S.px[T + 61] / S.o[T + 1] - 1.0
            xs.append(g - EW[60][T + 1]); rs.append(g - COST); Ts.append(T)
        s60 = summ(xs, Ts, cal, w0, blk=60, cap=cap60)
        c_[m] = {**s60, "平均R": float(np.mean(rs)), "排除_T+61超過窗尾": skip_w, "排除_延伸段硬斷點": skip_b}
    dsc["c_持有60日"] = c_
    print("[描述臂 b、c] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    d_ = {}
    VAL = np.column_stack([SS[s].valid for s in sids]); R20 = np.column_stack([ST[s]["r20"] for s in sids])
    HB = np.zeros((n, Sn), bool); Tr = np.arange(1, n - H_OUT)
    for i, s in enumerate(sids):
        S = SS[s]
        HB[Tr, i] = ((S.cs_pb[Tr + H_OUT] - S.cs_pb[Tr - 1]) > 0) | ((S.cs_ms[Tr + H_OUT] - S.cs_ms[Tr - 1]) > 0)
    G20 = np.full((n, Sn), np.nan); Od = np.where(okO, O, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        G20[:n - H_OUT] = PX[H_OUT:] / Od[1:n - H_OUT + 1] - 1.0
    for m in MAIN:
        RAW = np.zeros((n, Sn), bool)
        for s in sids:
            RAW[ST[s]["raw"][m], sidx[s]] = True
        rows = []; noval = 0; nctl = []
        for T, grp in E[m].groupby("T"):
            base = MEM[T] & VAL[T] & np.isfinite(R20[T])
            idx = np.flatnonzero(base); dec = np.full(Sn, -1)
            if len(idx) >= 10:
                dec[idx] = pd.qcut(pd.Series(R20[T, idx]).rank(method="first"), 10, labels=False).to_numpy()
            elig = base & VAL[T + 1] & ~HB[T] & ~RAW[T] & np.isfinite(G20[T])
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

    ea = E["甲"].copy()
    ea["乙選取"] = [ST[s]["why_yi"].get(int(cf), "（該根無乙選取）") for s, cf in zip(ea["sid"], ea["conf"])]
    e_ = {"定義": "(甲) 保留事件，按該線確認根收盤時 (乙) 的選取結果分組"}
    for w, g in ea.groupby("乙選取"):
        e_[w] = {**summ(g["X"], g["T"], cal, w0), "平均R": float(g["R"].mean())}
    e_["放棄組＝第三點偏離"] = e_.get("第三點偏離", {"n": 0})
    dsc["e_乙三點驗證沒過_照甲買"] = e_

    f_ = {}
    for m in MAIN:
        rows = []; na = 0
        for ev in E[m].itertuples():
            T = int(ev.T); S = SS[ev.sid]; bars = S.bars
            Ep = S.o[T + 1]; Sp = S.l[T]
            if not (np.isfinite(Sp) and Ep > Sp):
                na += 1; continue
            oneR = Ep - Sp; js = bars[(bars > T) & (bars <= T + 20)]
            x1 = T + H_OUT
            for j in js:
                if S.c[j] < Sp:
                    x1 = int(j) + 1; break
            x2 = T + H_OUT; stop = Sp; kind2 = "20日"; moved = False
            for j in js:
                if S.c[j] < stop:
                    x2 = int(j) + 1; kind2 = "保本出場" if moved else "初始停損"; break
                if S.c[j] >= Ep + oneR:
                    stop = Ep; moved = True
            r1, X1, h1 = x_at(S, T, x1); r2, X2, h2 = x_at(S, T, x2)
            r60 = (S.px[T + 61] / Ep - 1.0 - COST) if (T + 61 <= w1 and not S.brk(int(ev.first), T + 61)) else np.nan
            rows.append({"T": T, "R": ev.R, "X": ev.X, "r1": r1, "X1": X1, "h1": h1, "e1": x1 < T + H_OUT,
                         "r2": r2, "X2": X2, "h2": h2, "k2": kind2, "r60": r60})
        F = pd.DataFrame(rows)

        def blk(col_r, col_x, col_h, early):
            return {"出場比例": float(early.mean()), "出場數": int(early.sum()), "平均持有日": float(F[col_h].mean()),
                    "平均R": float(F[col_r].mean()), "中位R": float(F[col_r].median()), "最差R": float(F[col_r].min()), "平均X": float(F[col_x].mean()),
                    "配對差R（對固定20日）": summ(F[col_r] - F["R"], F["T"], cal, w0)}
        e2 = F["k2"] != "20日"; ab1 = F[F["e1"]]; ab2 = F[e2]; ab2b = F[F["k2"] == "保本出場"]
        ab = lambda d_, rc: {"n": int(len(d_)), "實際平均R": float(d_[rc].mean()) if rc else None, "照抱20日_平均R": float(d_["R"].mean()),
                             "照抱20日_中位R": float(d_["R"].median()), "照抱60日_平均R": float(d_["r60"].mean()),
                             "照抱60日_中位R": float(d_["r60"].median()), "60日可算數": int(d_["r60"].notna().sum())}
        f_[m] = {"n": int(len(F)), "E≤S不適用": na,
                 "f1": blk("r1", "X1", "h1", F["e1"]),
                 "f2": {**blk("r2", "X2", "h2", e2), "保本出場數": int((F["k2"] == "保本出場").sum()), "初始停損數": int((F["k2"] == "初始停損").sum())},
                 "f2−f1（R）": summ(F["r2"] - F["r1"], F["T"], cal, w0),
                 "固定20日": {"平均R": float(F["R"].mean()), "中位R": float(F["R"].median()), "最差R": float(F["R"].min())},
                 "放棄組_f1被停損": ab(ab1, "r1"), "放棄組_f2被停損或保本": ab(ab2, "r2"), "放棄組_f2保本出場那批": ab(ab2b, None)}
    dsc["f_保本移動停損"] = f_
    RES["§七描述臂"] = dsc
    print("[描述臂 d、e、f] 完成｜{:.0f}s".format(time.time() - t0), flush=True)

    # 先驗（seq2 §二③ 另押、只記錄不改判）：美股效果量不大於台股同格
    RES["先驗比對_美股效果量不大於台股同格（只記錄）"] = {m: {"美股平均X": J[m]["平均"], "台股平均X": TW[m],
                                                  "|美|≤|台|": bool(abs(J[m]["平均"]) <= abs(TW[m]))} for m in MAIN}
    RES["查核"] = CHK
    # 基準日值（給獨立查核用；逐日等權平均，⛔ 無代號）只放 repo 外
    p = os.path.join(WORK, "ew20.csv")
    pd.DataFrame({"date": [str(d.date()) for d in cal], "EW20": EW[20], "n_members": okM.sum(axis=1)}).to_csv(p, index=False)
    shas.append((os.path.basename(p), n, sha256f(p)))
    with io.open(os.path.join(OUT, "body_work_sha.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["file（~/us_work/usm/body/，repo 外）", "rows", "sha256"]); w.writerows(shas)
    RES["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    RES["body_fake_arm.csv_sha256"] = sha256f(os.path.join(OUT, "body_fake_arm.csv"))
    RES["耗時秒"] = round(time.time() - t0, 1)
    json.dump(RES, open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("三格合句：" + comb)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
