# -*- coding: utf-8 -*-
"""PREREG上升趨勢線（上升趨勢線被跌破：三畫法 × R × 兩種跌破判準）——【跌破事件偵測器】（研究腳本層；⛔ 不是共用引擎）。
判準＝台股策略線 上升趨勢線跌破 登錄 seq1（sha ffac12dee65c6bf1）§一；裁定 seq225、seq226。
⭐ 本支是 backtest/trendline_m.py（PREREGM 下降線突破）的【鏡像】：高 ↔ 低、實體頂 ↔ 實體底、向上突破 ↔ 向下跌破；
   ⛔ trendline_m.py 一行未改；設計參數（120／60 日、2%、N＝60、R² ≥ 0.5）直接 import 它的常數（同一個數只准一份）。
   ⛔ 本支不碰任何報酬。

樞紐低點：backtest/stop_fractal.swing_lows(還原 low, k＝R) ⇒ 還原 low【嚴格低於】左右各 R 根（平手不算；PREREGM §二 的鏡像）。

讀法（trendline_m M1～M8 逐條鏡像；⛔ 在看任何頻率或結果之前寫在這裡）：
 N1 幾何在【該股有效 K 棒序列】上（同 M1）；T+1、T+21、合併 20 日、區段用交易日曆（在 researchUT.py）。
 N2 線只從最後取點的確認日 conf ＝ 最後取點＋R 之後才存在；判定在 b ≥ conf＋1；b − conf ≤ 60；conf − P1 ≤ 120（同 M2）。
 N3 同一根 b：先用 b 開盤前就存在的線判跌破／逾期；再處理 b 收盤後剛確認的樞紐 ⇒ 重選取點、舊線結束（同 M3）。
 N4 重選：從全部已確認樞紐低點取最近兩個（甲）／三個（乙）；不合格 ⇒ 此時沒有線（同 M4）。一條線只在【該格的跌破判準】成立時結束
    （researchM B10 同：線的生命週期不變，只有符合該判準的事件才結束線）。
 N5 「實體不可穿」鏡像：實體底 min(還原開, 還原收) 不可【低於】當日線值；(甲) 範圍 [P1, P2]、(乙) [P1, P3]；取點 P1、P2 本身不判（同 M5）。
    開盤缺值 ⇒ 用收盤。等於不算穿。
 N6 (乙) 依序遞升 low(P1) ＜ low(P2) ＜ low(P3)（嚴格）；ℓ(P3) ≤ 0 ⇒ 不採；|low(P3) − ℓ(P3)|／ℓ(P3) ≤ 2%（同 M6）。
 N7 (丙)：[T−60, T−1] 還原收盤 OLS；上升線 ⇔ 斜率 ＞ 0 ∧ R² ≥ 0.5；窗內收盤全等 ⇒ 不算（同 M7）；每個 T 自成一條線。
 N8 跌破判準（登錄 §一；researchM B10 的鏡像）：
    close（只給鏡像對稱 fixture，⛔ 不是登錄的格）：c(T) ＜ ℓ(T) ∧ c(T−1) ≥ ℓ(T−1)
    pct1「1% 穿越」：c(T) ＜ 0.99·ℓ(T) ∧ c(T−1) ≥ 0.99·ℓ(T−1)（登錄「收盤 ＜ 趨勢線 × 0.99」，嚴格 ＜；「穿越」⇒ 前一根在門檻之上或等於）
    d3p3「3 日 3%」：t 為向下穿越（c(t) ＜ ℓ(t) ∧ c(t−1) ≥ ℓ(t−1)），t+1、t+2 收盤皆 ＜ ℓ，且 c(t+2) ＜ 0.97·ℓ(t+2)（嚴格）⇒ T ＝ t+2；
         (甲)(乙) 另需 t ≥ conf＋1；(丙) 用 t 日那條 ŷ_t 延伸到 t+1、t+2。
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import stop_fractal as SF
from backtest import trendline_m as TM

MAX_SPAN, LIFE, TOL3, REG_N, REG_R2 = TM.MAX_SPAN, TM.LIFE, TM.TOL3, TM.REG_N, TM.REG_R2
RULES = ("pct1", "d3p3")
PCT1, D3 = 0.99, 0.97


def pivot_lows(l, R: int) -> np.ndarray:
    """樞紐低點布林（第 s 根 ⇔ 還原 low 嚴格低於左右各 R 根）；⚠ 用到 s+R ⇒ 只能在 s+R 收盤後使用。"""
    return SF.swing_lows(np.asarray(l, float), k=R)


def _select(method, conf, l, bot, b, tol=None):
    tol = TOL3 if tol is None else tol
    need = 2 if method == "甲" else 3
    if len(conf) < need:
        return None, "取點不足"
    if method == "甲":
        p1, p2 = conf[-2], conf[-1]; last = p2; anchors = (p1, p2)
        if not l[p2] > l[p1]:
            return None, "非遞升"
    else:
        p1, p2, p3 = conf[-3], conf[-2], conf[-1]; last = p3; anchors = (p1, p2, p3)
        if not (l[p1] < l[p2] < l[p3]):
            return None, "非遞升"
    slope = (l[p2] - l[p1]) / (p2 - p1)
    if not slope > 0:
        return None, "斜率"
    if method == "乙":
        l3 = l[p1] + slope * (p3 - p1)
        if not (l3 > 0 and abs(l[p3] - l3) / l3 <= tol):
            return None, "第三點偏離"
    if b - p1 > MAX_SPAN:
        return None, "跨度"
    seg = np.arange(p1, last + 1)
    keep = (seg != p1) & (seg != p2)
    lv = l[p1] + slope * (seg - p1)
    if np.any(bot[seg][keep] < lv[keep]):
        return None, "實體穿線"
    return {"anchors": anchors, "p1": int(p1), "l1": float(l[p1]), "slope": float(slope), "conf": int(b)}, "成立"


def _lv(L, b):
    return L["l1"] + L["slope"] * (b - L["p1"])


def _hit(rule, L, c, b):
    lv = lambda j: _lv(L, j)
    if rule == "close":
        return b >= 1 and c[b] < lv(b) and c[b - 1] >= lv(b - 1)
    if rule == "pct1":
        return b >= 1 and c[b] < PCT1 * lv(b) and c[b - 1] >= PCT1 * lv(b - 1)
    if rule == "d3p3":
        return (b - 2 >= L["conf"] + 1 and b >= 3 and c[b - 3] >= lv(b - 3) and c[b - 2] < lv(b - 2)
                and c[b - 1] < lv(b - 1) and c[b] < D3 * lv(b))
    raise ValueError(rule)


def detect_pivot(o, l, c, method: str, R: int, rule: str, lag: int | None = None, trace: bool = False, tol=None):
    """(甲)(乙)：有效 K 棒序列上的跌破事件。回 {events[{T, anchors, conf, first}], why_at{b: 選取理由}, stats, trace}。
    lag：⛔ 正式＝R；≠R 只給 fixture 的前視破壞測試。"""
    assert method in ("甲", "乙")
    o = np.asarray(o, float); l = np.asarray(l, float); c = np.asarray(c, float)
    m = len(c); bot = np.fmin(o, c)
    lag = R if lag is None else lag
    piv = np.flatnonzero(pivot_lows(l, R))
    conf_at = {int(s + lag): int(s) for s in piv}
    conf, events, why_at = [], [], {}
    tr = [None] * m if trace else None
    st = {"樞紐": int(len(piv)), "線成立": 0, "跌破結束": 0, "逾60日結束": 0, "被新樞紐取代": 0}
    L = None
    for b in range(m):
        if L is not None:
            if b - L["conf"] > LIFE:
                L = None; st["逾60日結束"] += 1
            elif _hit(rule, L, c, b):
                events.append({"T": b, "anchors": L["anchors"], "conf": L["conf"], "first": L["anchors"][0]})
                L = None; st["跌破結束"] += 1
        s = conf_at.get(b)
        if s is not None:
            conf.append(s)
            if L is not None:
                st["被新樞紐取代"] += 1
            L, why = _select(method, conf, l, bot, b, tol)
            why_at[b] = why
            if L is not None:
                st["線成立"] += 1
        if trace:
            tr[b] = None if L is None else L["anchors"]
    return {"events": events, "why_at": why_at, "stats": st, "trace": tr}


def reg_arrays(c, N):
    """與 trendline_m.detect_reg 同一組算式。回 (T, ybar, slope, r2)，第 i 列 ＝ T＝i+N 的窗 [T−N, T−1]。"""
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
    return ybar + slope * (k - (N - 1) / 2.0)


def detect_reg(c, rule: str, N: int = REG_N, r2min: float = REG_R2, trace: bool = False):
    """(丙)：上升回歸線被跌破。回 {events[{T, first, i}], trace（每根是否為上升線日）}。"""
    c = np.asarray(c, float); m = len(c)
    T, yb, sl, r2 = reg_arrays(c, N)
    out = {"events": [], "trace": ([False] * m if trace else None)}
    if len(T) == 0:
        return out
    up = (sl > 0) & (r2 >= r2min)
    yT = reg_line(yb, sl, N, N); yT1 = reg_line(yb, sl, N, N - 1)
    if rule == "close":
        hit = up & (c[T] < yT) & (c[T - 1] >= yT1)
    elif rule == "pct1":
        hit = up & (c[T] < PCT1 * yT) & (c[T - 1] >= PCT1 * yT1)
    elif rule == "d3p3":
        base = up & (c[T] < yT) & (c[T - 1] >= yT1)
        ev = []
        for i in np.flatnonzero(base):
            t = int(T[i])
            if t + 2 >= m:
                continue
            if c[t + 1] < reg_line(yb[i], sl[i], N, N + 1) and c[t + 2] < D3 * reg_line(yb[i], sl[i], N, N + 2):
                ev.append({"T": t + 2, "first": t - N, "i": int(i)})
        out["events"] = ev
        hit = None
    else:
        raise ValueError(rule)
    if hit is not None:
        out["events"] = [{"T": int(t), "first": int(t - N), "i": int(i)} for i, t in zip(np.flatnonzero(hit), T[hit])]
    if trace:
        tr = [False] * m
        for t, d in zip(T, up):
            tr[int(t)] = bool(d)
        out["trace"] = tr
    return out


def detect_calendar(o_cal, l_cal, c_cal, method: str, R: int, rule: str, **kw):
    """對齊交易日曆的序列（洞＝NaN）⇒ 事件，T／first／anchors／conf 換成日曆位置；有效 K 棒 ＝ close 非缺值。"""
    c_cal = np.asarray(c_cal, float)
    bars = np.flatnonzero(np.isfinite(c_cal))
    ob, lb, cb = np.asarray(o_cal, float)[bars], np.asarray(l_cal, float)[bars], c_cal[bars]
    if method == "丙":
        r = detect_reg(cb, rule, **kw)
    else:
        r = detect_pivot(ob, lb, cb, method, R, rule, **kw)
        r["why_at"] = {int(bars[b]): w for b, w in r["why_at"].items()}
    for e in r["events"]:
        e["T_bar"] = e["T"]; e["T"] = int(bars[e["T"]]); e["first"] = int(bars[e["first"]])
        if "anchors" in e:
            e["anchors"] = tuple(int(bars[a]) for a in e["anchors"])
        if "conf" in e:
            e["conf"] = int(bars[e["conf"]])
    r["bars"] = bars
    return r
