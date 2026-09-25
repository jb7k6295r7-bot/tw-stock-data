# -*- coding: utf-8 -*-
"""PREREGM（下降趨勢線被收盤向上突破：三種畫法並測）——【突破事件偵測器】（研究腳本層；⛔ 不是共用引擎）。
判準＝台股策略線 PREREGM seq1（sha 9316840579a8d33a）§一～§三。本支只產生「突破日 T」與取點；⛔ 不碰任何報酬。

輸入：一檔股票的還原 open／high／close（⭐ 還原價；原始價只用在漲跌停，那不在本支）。
   detect_bars()     ⇒ 輸入是【有效 K 棒序列】（close 非缺值的那些日子依序排好），索引＝有效 K 棒序號
   detect_calendar() ⇒ 輸入是對齊交易日曆的序列（洞＝NaN），內部抽出有效 K 棒、跑 detect_bars、再把 T／取點對回日曆位置

樞紐高點（§二）：backtest/stop_fractal.swing_lows(−還原 high, k＝R) ⇒ 還原 high【嚴格高於】左右各 R 根（平手不算）。
   ⛔ 本支不另寫擺動點；swing_lows 對第 s 根會用到 s+R ⇒ 本支只在第 s+R 根【收盤後】才把 s 當成已確認。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何頻率或結果之前寫在這裡；交件逐條列出）：
 M1 幾何一律在【該股有效 K 棒序列】上：線的橫軸（日序）、樞紐左右 R 根、「最早取點距確認日 ≤ 120」、「確認日起有效 ≤ 60」、
    (丙) 的 [T−60, T−1] 60 根、以及「T−1」＝前一根有效 K 棒（§一⑤：樞紐左右 R 根在有效 K 棒上數；其餘幾何同一把尺）。
    T+1、T+21、判定窗、合併 20 日、20 日區段用【交易日曆】（那些在 researchM_freq.py，不在本支）。
 M2 「線只從最後一個取點的確認日之後才存在」＝ 確認日 conf ＝ 最後取點 s＋R；突破只在 b ≥ conf＋1 判；
    「有效 ≤ 60 個交易日」讀成 b − conf ≤ 60（⇒ 可判的 T ∈ [conf＋1, conf＋60]，共 60 根）。
    「最早取點距確認日 ≤ 120」讀成 conf − P1 ≤ 120。
 M3 同一根 K 棒 b 的處理順序：① 先用【b 開盤前就已存在】的那條線判 b 是否突破（或 b − conf > 60 而失效）；
    ② 再處理「b 收盤後剛確認」的樞紐 ⇒ 重選取點、舊線結束。（樞紐在 b 收盤後才確認 ⇒ 它不能影響 b 當日的判定。）
 M4 重選取點：每確認一個新樞紐，就從【全部已確認樞紐】取最近的兩個（甲）／三個（乙）重來；不合格 ⇒ 此時沒有線
    （直到下一個樞紐確認）。舊線不論有沒有被突破都結束（⛔ 同時只追一條）。
 M5 (甲)(乙)「實體不可穿」的範圍：(甲) ＝ [P1, P2] 之間每一根；(乙) ＝ [P1, P3] 之間每一根（⭐ 讀法：P3 也是取點，
    「兩個取點之間」取成全部取點所跨的範圍）；線值一律是 P1–P2 那條線。取點 P1、P2 本身在線上（線值＝其 high），
    不另判（數學上實體頂 ≤ high ＝ 線值；免去浮點誤差造成的假穿線）。實體頂 ＝ max(還原開, 還原收)，開盤缺值 ⇒ 用收盤。
    「不可高於」＝ 實體頂 > 線值 才算穿（等於不算穿）。
 M6 (乙) 的「依序遞降」＝ high(P1) > high(P2) > high(P3)（嚴格）；ℓ(P3) ≤ 0 ⇒ 不採；2% 用 ≤（邊界算過）。
 M7 (丙) 橫軸取窗內有效 K 棒序號；R² ＝ 1 − SSE／SST（單變數 OLS 下 ＝ slope²·Sxx／Syy）；窗內收盤全等（Syy＝0）⇒ 不算下降線。
    (丙) 每個 T 自成一條線 ⇒「一條線被突破一次就結束」對 (丙) 沒有作用；同檔連續觸發交給合併規則（researchM_freq）。
 M8 突破：close(T) > ℓ(T) 且 close(T−1) ≤ ℓ(T−1)，嚴格照寫、⛔ 不加容差。
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import stop_fractal as SF          # ⭐ 擺動點用共用那一支（同一件事只准一份實作）

R_MAIN = 5            # 設計參數（§三）
MAX_SPAN = 120        # 設計參數：最早取點距確認日 ≤ 120
LIFE = 60             # 設計參數：線從確認日起有效 ≤ 60
TOL3 = 0.02           # 設計參數：(乙) 第三點 2%
REG_N = 60            # 設計參數：(丙) N＝60
REG_R2 = 0.5          # 設計參數：(丙) R² ≥ 0.5
METHODS = ("甲", "乙", "丙")


def pivot_highs(h, R: int) -> np.ndarray:
    """樞紐高點布林（第 s 根 ⇔ 還原 high 嚴格高於左右各 R 根）；⚠ 用到 s+R ⇒ 呼叫端只能在 s+R 收盤後使用。"""
    return SF.swing_lows(-np.asarray(h, float), k=R)


def _select(method, conf, h, top, b):
    """第 b 根收盤剛確認新樞紐 ⇒ 依規則從已確認樞紐 conf 重選取點；回 (線 dict 或 None, 理由)。"""
    need = 2 if method == "甲" else 3
    if len(conf) < need:
        return None, "取點不足"
    if method == "甲":
        p1, p2 = conf[-2], conf[-1]; last = p2; anchors = (p1, p2)
        if not h[p2] < h[p1]:
            return None, "非遞降"
    else:
        p1, p2, p3 = conf[-3], conf[-2], conf[-1]; last = p3; anchors = (p1, p2, p3)
        if not (h[p1] > h[p2] > h[p3]):
            return None, "非遞降"
    slope = (h[p2] - h[p1]) / (p2 - p1)
    if not slope < 0:
        return None, "斜率"
    if method == "乙":
        l3 = h[p1] + slope * (p3 - p1)
        if not (l3 > 0 and abs(h[p3] - l3) / l3 <= TOL3):
            return None, "第三點偏離"
    if b - p1 > MAX_SPAN:
        return None, "跨度"
    seg = np.arange(p1, last + 1)
    keep = (seg != p1) & (seg != p2)                        # M5：取點 P1、P2 在線上，不另判
    lv = h[p1] + slope * (seg - p1)
    if np.any(top[seg][keep] > lv[keep]):
        return None, "實體穿線"
    return {"anchors": anchors, "p1": int(p1), "h1": float(h[p1]), "slope": float(slope), "conf": int(b)}, "成立"


def _lv(L, b):
    return L["h1"] + L["slope"] * (b - L["p1"])


def detect_pivot(o, h, c, method: str, R: int = R_MAIN, lag: int | None = None, trace: bool = False):
    """(甲)(乙)：有效 K 棒序列上的突破事件。回 dict：events［{T, anchors, conf}］、stats、trace（每根收盤後的現行線取點或 None）。
    lag：⛔ 正式一律＝R（右邊 R 根走完才確認）；lag≠R 只給 fixture 的「前視破壞」測試用（證明測試分得出來）。"""
    assert method in ("甲", "乙")
    o = np.asarray(o, float); h = np.asarray(h, float); c = np.asarray(c, float)
    m = len(c)
    top = np.fmax(o, c)                                      # M5：開盤缺值 ⇒ 用收盤
    lag = R if lag is None else lag
    piv = np.flatnonzero(pivot_highs(h, R))
    conf_at = {int(s + lag): int(s) for s in piv}
    conf, events, tr = [], [], ([None] * m if trace else None)
    st = {"樞紐": int(len(piv)), "線成立": 0, "突破結束": 0, "逾60日結束": 0, "被新樞紐取代": 0}
    why_n = {}
    L = None
    for b in range(m):
        if L is not None:                                    # M3 ①
            if b - L["conf"] > LIFE:
                L = None; st["逾60日結束"] += 1
            elif b >= 1 and c[b] > _lv(L, b) and c[b - 1] <= _lv(L, b - 1):
                events.append({"T": b, "anchors": L["anchors"], "conf": L["conf"]})
                L = None; st["突破結束"] += 1
        s = conf_at.get(b)                                   # M3 ②
        if s is not None:
            conf.append(s)
            if L is not None:
                st["被新樞紐取代"] += 1
            L, why = _select(method, conf, h, top, b)
            why_n[why] = why_n.get(why, 0) + 1
            if L is not None:
                st["線成立"] += 1
        if trace:
            tr[b] = None if L is None else L["anchors"]
    st["選取結果"] = why_n
    return {"events": events, "stats": st, "trace": tr}


def detect_reg(c, N: int = REG_N, r2min: float = REG_R2, trace: bool = False):
    """(丙)：每個 T 用 [T−N, T−1] 的 N 根有效 K 棒還原收盤對日序 OLS；斜率 < 0 ∧ R² ≥ r2min ∧
    close(T) > ŷ_T(T) ∧ close(T−1) ≤ ŷ_T(T−1)。⭐ 逐列獨立計算（⛔ 不用累加和）⇒ 前綴不變、前視突變測試可逐位元比。"""
    c = np.asarray(c, float); m = len(c)
    out = {"events": [], "stats": {"可判日": 0, "下降線日": 0}, "trace": ([False] * m if trace else None)}
    if m < N + 1:
        return out
    W = np.lib.stride_tricks.sliding_window_view(c, N)[: m - N]   # 第 i 列 ＝ c[i : i+N] ＝ T＝i+N 的窗
    x = np.arange(N, dtype=float) - (N - 1) / 2.0
    sxx = float((x * x).sum())
    ybar = W.mean(axis=1)
    slope = (W * x).sum(axis=1) / sxx
    syy = ((W - ybar[:, None]) ** 2).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        r2 = np.where(syy > 0, slope * slope * sxx / syy, 0.0)
    T = np.arange(N, m)
    yT = ybar + slope * (N - (N - 1) / 2.0)
    yT1 = ybar + slope * ((N - 1) - (N - 1) / 2.0)
    down = (slope < 0) & (r2 >= r2min)
    hit = down & (c[T] > yT) & (c[T - 1] <= yT1)
    out["stats"] = {"可判日": int(len(T)), "下降線日": int(down.sum())}
    out["events"] = [{"T": int(t), "win0": int(t - N)} for t in T[hit]]
    if trace:
        tr = [False] * m
        for t, d in zip(T, down):
            tr[int(t)] = bool(d)
        out["trace"] = tr
    return out


def detect_bars(o, h, c, method: str, R: int = R_MAIN, **kw):
    """有效 K 棒序列 ⇒ 事件（索引＝有效 K 棒序號）。每筆事件帶 first：最早取點（丙：回歸窗起點）的序號。"""
    if method == "丙":
        r = detect_reg(c, **kw)
        for e in r["events"]:
            e["first"] = e["win0"]
    else:
        r = detect_pivot(o, h, c, method, R, **kw)
        for e in r["events"]:
            e["first"] = e["anchors"][0]
    return r


def detect_calendar(o_cal, h_cal, c_cal, method: str, R: int = R_MAIN, **kw):
    """對齊交易日曆的序列（洞＝NaN）⇒ 事件，T／first／anchors 換成日曆位置；有效 K 棒 ＝ close 非缺值。"""
    c_cal = np.asarray(c_cal, float)
    bars = np.flatnonzero(np.isfinite(c_cal))
    r = detect_bars(np.asarray(o_cal, float)[bars], np.asarray(h_cal, float)[bars], c_cal[bars], method, R, **kw)
    for e in r["events"]:
        e["T_bar"] = e["T"]; e["T"] = int(bars[e["T"]]); e["first"] = int(bars[e["first"]])
        if "anchors" in e:
            e["anchors"] = tuple(int(bars[a]) for a in e["anchors"])
        if "win0" in e:
            e["win0"] = int(bars[e["win0"]])
        if "conf" in e:
            e["conf"] = int(bars[e["conf"]])
    r["bars"] = bars
    return r
