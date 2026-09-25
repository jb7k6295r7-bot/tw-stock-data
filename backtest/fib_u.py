# -*- coding: utf-8 -*-
"""PREREGU（費波那契回撤：38.2／61.8 的止跌反彈，有沒有比旁邊的位置多）——【波段與觸及事件偵測器】＋【止跌反彈判定】。
判準＝台股策略線 PREREGU seq1（sha 4ff4c1731fdded12）§一～§三。研究腳本層；⛔ 不是共用引擎。
本支只產生「波段」「觸及日 T」與「位置價 p(x)」，以及給定收盤序列的反彈／沒止住／不分勝負判定（§三）；⛔ 不算報酬。

擺動點（§一）：backtest/stop_fractal.swing_lows —— 高點用 swing_lows(−還原 high, k)，低點用 swing_lows(還原 low, k)（嚴格、平手不算）。
   ⛔ 本支不另寫擺動點；swing_lows 對第 s 根會用到 s+k ⇒ 本支只在第 s+k 根【收盤後】才把 s 當成已確認。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何頻率或結果之前寫在這裡；交件逐條列出）：
 U1 幾何一律在【該股有效 K 棒序列】上數（有效 K 棒 ＝ close 非缺值）：擺動點左右 k 根、L0 回看 120（登錄已寫「有效 K 棒計」）、
    「t_H − t_L ≥ 10 個交易日」、「確認日後 60 個交易日」（⚠ 兩種讀法處：登錄寫「交易日」；本支同 PREREGM M1 讀成有效 K 棒）。
    T+20、20 日合併、20 日區段用【交易日曆】（登錄 §二 末行「T+20 用交易日曆」；那些在 researchU*.py）。
 U2 H0 在 t_H、確認日 conf ＝ t_H＋k（右邊 k 根走完的那一根收盤）。L0 ＝ [t_H−120, t_H) 內、在 conf 以前已確認（s＋k ≤ conf）
    的擺動低點中還原 low 最低者（同值取較晚）⇒ 再判三條件；三條件不過 ⇒ 不成波段（⛔ 不改挑次低的擺動低點）。
    「H0 是這段的頂」＝ 還原 high(t_H) ≥ [t_L, t_H] 內每一根還原 high（缺值略過；等於算頂）。
    20% 用 ≥（相對容差 1e-12，恰好 20% 算過）。
 U3 同一根 K 棒 b 的處理順序（同 PREREGM M3 的精神）：
    ① 現行波段若 b − conf > 60 ⇒ 先失效（b 不再計）；否則 b 的盤中觸及【先計入】現行波段（觸及是盤中、失效看收盤）；
    ② 再看 b 的收盤：收盤 > H0 或 收盤 < L0 ⇒ 波段在 b 收盤後失效（b 當天的觸及仍算）；
    ③ 最後處理「b 收盤後剛確認」的擺動高點：合格 ⇒ 舊波段結束（b 當天的觸及仍歸舊波段）、新波段從 b＋1 起算觸及。
 U4 「確認前已觸及」的範圍 ＝ [t_H, conf]（含 H0 那一根與確認那一根）：該範圍內任一根還原 low ≤ p(x) ⇒ 該波段該位置不計。
    觸及只從 conf＋1 起、到波段結束那一根（含）為止；第一根還原 low ≤ p(x) 的有效 K 棒 ＝ T（low 缺值的那一根不算觸及）。
 U5 位置價 p(x) ＝ H0 − x·(H0 − L0)，x 以比率帶入（38.2 ⇒ 0.382）；觸及用 ≤（恰好等於算觸及）。
 U6 §三 止跌反彈：看 [T, T+20]（交易日曆）內【有收盤】的日子，依序第一個落在閉區間 [0.95·p, 1.05·p] 之外的收盤：
    > 1.05·p ⇒ 反彈（1）／< 0.95·p ⇒ 沒止住（0）；都在帶內（含窗內停牌缺收盤、或窗內下市）⇒ 不分勝負（−1）。
    ⚠ 兩種讀法處：登錄一句寫「[…] 之外」（閉區間 ⇒ 恰好等於 1.05·p 仍在帶內）、下一句寫「≥ p×1.05」；本支取閉區間（等號留在帶內），
    研究腳本另報「恰好落在帶緣」的件數（兩種讀法只差這些件）。
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import stop_fractal as SF          # ⭐ 擺動點用共用那一支（同一件事只准一份實作）

K_MAIN = 5            # 設計參數：k
LOOKBACK = 120        # 設計參數：L0 回看
MIN_SPAN = 10         # 設計參數：t_H − t_L ≥ 10
MIN_RISE = 0.20       # 05趨勢分析：自低點漲超過 20%
LIFE = 60             # 設計參數：確認日後 60 個交易日
BAND = 0.05           # 設計參數：±5% 判定帶
HOLD = 20             # 設計參數：20 日
POS = {"30": 0.30, "38.2": 0.382, "45": 0.45, "50": 0.50, "55": 0.55, "61.8": 0.618, "70": 0.70}
FIB = ("38.2", "61.8")
NB = {"38.2": ("30", "45"), "61.8": ("55", "70"), "50": ("45", "55")}
SIX = ("30", "38.2", "45", "55", "61.8", "70")


def swing_high(h, k):
    return SF.swing_lows(-np.asarray(h, float), k=k)


def swing_low(l, k):
    return SF.swing_lows(np.asarray(l, float), k=k)


def _qualify(h, l, tH, sl, b, lag):
    """U2：以第 b 根收盤時的資訊判 H0＝tH 是否成波段；回 (dict 或 None, 理由)。"""
    lo = tH - LOOKBACK
    cand = sl[(sl >= lo) & (sl < tH) & (sl + lag <= b)]
    if len(cand) == 0:
        return None, "無擺動低點"
    v = l[cand]
    L0 = float(np.min(v))
    tL = int(cand[np.flatnonzero(v == L0)[-1]])           # 同值取較晚
    H0 = float(h[tH])
    seg = h[tL:tH + 1]
    if np.any(np.isfinite(seg) & (seg > H0)):
        return None, "H0非頂"
    if not (H0 - L0) / L0 >= MIN_RISE - 1e-12:
        return None, "漲幅<20%"
    if tH - tL < MIN_SPAN:
        return None, "跨度<10"
    return {"tL": tL, "tH": int(tH), "conf": int(b), "L0": L0, "H0": H0}, "成立"


def detect_waves(h, l, c, k: int = K_MAIN, lag: int | None = None):
    """有效 K 棒序列 ⇒ 波段列表。每個波段：tL, tH, conf, end（觸及可計的最後一根，含）, why_end, L0, H0, pre_min（[tH, conf] 最低 low）。
    lag：⛔ 正式一律＝k；lag≠k 只給 fixture 的「前視破壞」測試用（證明測試分得出來）。"""
    h = np.asarray(h, float); l = np.asarray(l, float); c = np.asarray(c, float)
    m = len(c)
    lag = k if lag is None else lag
    sh = np.flatnonzero(swing_high(h, k)); sl = np.flatnonzero(swing_low(l, k))
    conf_at = {int(s + lag): int(s) for s in sh if s + lag < m}
    waves, why_n = [], {}
    W = None

    def close_w(end, why):
        W["end"] = int(end); W["why_end"] = why
        waves.append(W)

    for b in range(m):
        if W is not None and b - W["conf"] > LIFE:                     # U3 ①
            close_w(b - 1, "逾60日"); W = None
        if W is not None:                                              # U3 ②
            if c[b] > W["H0"]:
                close_w(b, "收盤>H0"); W = None
            elif c[b] < W["L0"]:
                close_w(b, "收盤<L0"); W = None
        s = conf_at.get(b)                                             # U3 ③
        if s is not None:
            nw, why = _qualify(h, l, s, sl, b, lag)
            why_n[why] = why_n.get(why, 0) + 1
            if nw is not None:
                if W is not None:
                    close_w(b, "被新波段取代")
                seg = l[nw["tH"]:b + 1]
                nw["pre_min"] = float(np.nanmin(seg)) if np.isfinite(seg).any() else np.inf
                W = nw
    if W is not None:
        close_w(m - 1, "資料尾")
    return {"waves": waves, "stats": {"擺動高點": int(len(sh)), "擺動低點": int(len(sl)), "確認時判定": why_n}}


def touches(waves, l, fracs):
    """U4／U5：每個波段 × 每個位置 ⇒ 第一次觸及。fracs：{名: 比率}。
    回 list of dict：wave（序號）, pos, p, state（'觸及'／'確認前已觸及'／'未觸及'）, T（有效 K 棒序號或 None）。"""
    l = np.asarray(l, float)
    out = []
    for wi, W in enumerate(waves):
        a, e = W["conf"] + 1, W["end"]
        seg = l[a:e + 1] if e >= a else np.zeros(0)
        seg = np.where(np.isfinite(seg), seg, np.inf)
        run = np.minimum.accumulate(seg) if len(seg) else seg
        for nm, x in fracs.items():
            p = W["H0"] - x * (W["H0"] - W["L0"])
            if W["pre_min"] <= p:
                out.append({"wave": wi, "pos": nm, "p": p, "state": "確認前已觸及", "T": None}); continue
            if len(run) == 0 or run[-1] > p:
                out.append({"wave": wi, "pos": nm, "p": p, "state": "未觸及", "T": None}); continue
            j = int(np.argmax(run <= p))
            out.append({"wave": wi, "pos": nm, "p": p, "state": "觸及", "T": a + j})
    return out


def touches_many(waves, l, fracs_arr):
    """touches 的向量版（假訊號臂用）：fracs_arr 形狀 (P,) ⇒ 回 (P, nW) 的 T（有效 K 棒序號；−1 ＝ 不計）與 p。
    ⭐ fixture 驗與 touches 逐筆相同。"""
    l = np.asarray(l, float); fr = np.asarray(fracs_arr, float)
    P = len(fr); nW = len(waves)
    T = np.full((P, nW), -1, np.int64); PP = np.zeros((P, nW))
    for wi, W in enumerate(waves):
        a, e = W["conf"] + 1, W["end"]
        p = W["H0"] - fr * (W["H0"] - W["L0"])
        PP[:, wi] = p
        if e < a:
            continue
        seg = l[a:e + 1]
        seg = np.where(np.isfinite(seg), seg, np.inf)
        run = np.minimum.accumulate(seg)
        ok = (W["pre_min"] > p) & (run[-1] <= p)
        # run 非增 ⇒ 第一個 run ≤ p 的位置 ＝ searchsorted(−run, −p, 'left')
        j = np.searchsorted(-run, -p, side="left")
        T[ok, wi] = a + j[ok]
    return T, PP


def detect_calendar(h_cal, l_cal, c_cal, k: int = K_MAIN, fracs=None, **kw):
    """對齊交易日曆的序列（洞＝NaN）⇒ 波段與觸及，全部換成日曆位置（另留 *_bar）。有效 K 棒 ＝ close 非缺值。"""
    c_cal = np.asarray(c_cal, float)
    bars = np.flatnonzero(np.isfinite(c_cal))
    hb = np.asarray(h_cal, float)[bars]; lb = np.asarray(l_cal, float)[bars]; cb = c_cal[bars]
    r = detect_waves(hb, lb, cb, k, **kw)
    tc = touches(r["waves"], lb, POS if fracs is None else fracs)
    for W in r["waves"]:
        for f in ("tL", "tH", "conf", "end"):
            W[f + "_bar"] = W[f]; W[f] = int(bars[W[f]])
    for t in tc:
        t["T_bar"] = t["T"]
        t["T"] = None if t["T"] is None else int(bars[t["T"]])
    r["touches"] = tc; r["bars"] = bars
    return r


def outcome(c_cal, T, p, hold: int = HOLD, band: float = BAND):
    """U6：[T, T+hold] 有收盤的日子依序看；回 (1 反彈／0 沒止住／−1 不分勝負, 決定日位置或 None)。"""
    hi, lo = p * (1 + band), p * (1 - band)
    for j in range(T, min(T + hold, len(c_cal) - 1) + 1):
        v = c_cal[j]
        if not np.isfinite(v):
            continue
        if v > hi:
            return 1, j
        if v < lo:
            return 0, j
    return -1, None


def outcome_vec(c_cal, T, p, hold: int = HOLD, band: float = BAND):
    """outcome 的向量版（T、p 為陣列；T+hold 必須 < len(c_cal)）。⭐ fixture 驗與 outcome 逐筆相同。"""
    T = np.asarray(T, np.int64); p = np.asarray(p, float)
    if len(T) == 0:
        return np.zeros(0, np.int8)
    idx = T[:, None] + np.arange(hold + 1)[None, :]
    C = np.asarray(c_cal, float)[idx]
    up = C > (p * (1 + band))[:, None]; dn = C < (p * (1 - band))[:, None]      # NaN ⇒ 兩者皆假
    anyo = up | dn
    first = np.argmax(anyo, axis=1)
    has = anyo.any(axis=1)
    y = np.full(len(T), -1, np.int8)
    rows = np.arange(len(T))
    y[has] = np.where(up[rows, first][has], 1, 0)
    return y
