# -*- coding: utf-8 -*-
"""PREREG反轉訊號（台股策略線登錄 seq2 sha 6309d93ebdf2652f；裁定 seq226 發號、N_前段 最多 ＋96、Bonferroni 按層內可判定數）。
大盤（0050）＋個股兩層 × 原版／加確認兩版 × 21 訊號的事件研究。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchRev.py pre|body|report [--procs 2] [--limit N]

═══ 訊號（登錄 §一；裁定：頭肩頂、2B 頂、2B 底 無機器定義 ⇒ 不收 ⇒ 高點 10＋低點 11 ＝ 21；登錄 §七 寫「22 種」，照「無定義不收」落地後是 21 種）═══
  高點：M 頭（型態全量 S01）｜TD 9 賣｜KD 頂背離｜MACD 頂背離｜RSI 70 跌回｜高檔爆量長上影｜黃昏之星（K02）｜空頭吞噬（K61）｜
        上升趨勢線跌破（PREREG上升趨勢線主格 ＝ PREREGM 甲 鏡像、R＝5、收盤 ＜ 線 × 0.99）｜跌破 60 日線
  低點：頭肩底（PREREGX hs）｜W 底（PREREGX w）｜TD 9 買｜KD 底背離｜MACD 底背離｜RSI 30 站回｜低檔爆量長下影｜晨星（K07）｜多頭吞噬（K56）｜
        下降趨勢線突破（trendline_m 甲、R＝5 原樣）｜站回 60 日線
  落地讀法（回報、裁定無異議）：
   KD(9,3,3) 台灣式：RSV＝(C−L9)÷(H9−L9)×100（H9＝L9 ⇒ 50）、K＝K×2/3＋RSV/3、D＝D×2/3＋K/3、初值 50；背離用 K 值
   MACD(12,26,9)：還原收盤 EMA（pandas ewm adjust=False）、DIF＝EMA12−EMA26（第 26 根起有值）；背離用 DIF
   背離：5 根碎形（stop_fractal.swing_lows，左右各 2 根嚴格；頂用 −high、底用 low），第 s＋2 根收盤確認；取最近兩個已確認轉折 P1、P2；
         頂：H(P2)＞H(P1) 且 指標(P2)＜指標(P1)；底：L(P2)＜L(P1) 且 指標(P2)＞指標(P1)；兩點距離不設上限；訊號日＝P2＋2；first＝P1
   RSI(14) Wilder（第 14 根起）：高點 RSI[t−1]＞70 且 RSI[t]＜70；低點 RSI[t−1]＜30 且 RSI[t]＞30
   TD 9：連續 9 根 c[t]＞c[t−4]（賣）／＜（買），計數剛好到 9 那根＝訊號（第 10 根以後不再出）
   爆量長上影：v[t]＞2×mean(v[t−20..t−1])；U＝H−max(O,C)＞0 且 U ≥ 2|C−O|；H[t]＝max H[t−19..t]；長下影鏡像（D、L 新低）；還原 OHLC
   60 日線：有效 K 棒 MA60（math.fsum÷60、含當根）；跌破＝c[t]＜MA[t] 且 c[t−1] ≥ MA[t−1]；站回鏡像
   幾何一律在有效 K 棒序列上；first（硬斷點範圍起點）：型態／趨勢線／背離＝第一個取點，其餘＝T
═══ 量與判定 ═══
  報酬 R_H ＝ c[T＋H] ÷ o[T＋1] − 1（交易日曆；T＋H 無成交 ⇒ 之前最後一根有效收盤）；H＝20（判定）、60（描述）；⛔ 不扣成本（基準同）
  同一訊號 20 個交易日內只取第一筆（先合併、再剔除；PatAll Q2）；事件須 T＋H ≤ 窗尾
  確認版：T＋1～T＋5（交易日曆、有效 K 棒）收盤 ＞ 訊號 K 還原高點（低點訊號）／＜ 還原低點（高點訊號）⇒ 確認日 C；從 C＋1 開盤起算；
          沒確認 ⇒ 不算一筆，照報比例與那批的原版報酬（放棄組）
  大盤層：0050 還原價；主窗 2017-03-02～2026-08-24（判定）；早年 2004-02-11～2016-12-30（描述；data/early 釘 3edc0e2206 接主快照）
    X ＝ R20 − 同窗所有交易日 R20 的平均；CI 以 20 日區段分群（(基準日 − w0)//20）；n_eff ＝ min(n, 區段數)
    成功率：高點 R20 ＜ 0、低點 ＞ 0 的比例；基準比例 ＝ 同窗所有交易日
    假訊號臂：同事件數隨機日 1,000 次 ⇒ 隨機也過的比例（描述、不計 N）
  個股層：W1 eligible（resultsp4/panel.csv.gz，當月面板）∩ gate3；剔除 T＋1 停牌／開盤漲停／開盤跌停、[first, T＋H] 硬斷點（delist on）
    基準①＝同月全母體股日；基準②＝同月、同一天橫斷面前 20 日報酬十分位（avgdown.r20_cal、avgdown.deciles）同一格；X ＝ R20 − 基準②
    CI 以基準日曆月分群；n_eff ＝ min(n, 月數)；假訊號臂：登錄 §七 未列 ⇒ 不跑
  兩層：n_eff ＜ 10 ⇒ 依構造不可判定、不計 N；Bonferroni α ＝ 0.05／k（k ＝ 該層兩版合計 n_eff ≥ 10 的格數）；出口照 PREREGH1 §五
  通過 ＝ 高點 結果③（CI 全 ＜ 0）、低點 結果②（CI 全 ＞ 0）
輸出 backtest/resultsRev/
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                                   # ⭐ D.DATA ⇒ 快照 edc6f、chdir ⇒ repo
import researchM_freq as MF
from backtest import avgdown as AV
from backtest import patterns_all as PA
from backtest import patterns_x as PX
from backtest import stop_fractal as SF
from backtest import trendline_m as TM

D, TR, UG = H2.D, H2.TR, H2.UG
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsRev")
DB = os.path.expanduser("~/tw-stock-data")
EARLY_SHA = "3edc0e2206"
W0, W1 = "2017-03-02", "2026-08-24"
E0, E1 = "2004-02-11", "2016-12-30"
HS = (20, 60)
MERGE, CONF_N = 20, 5
NEFF_MIN = 10
FAKE_N = 1000
SIG = [("H_M", "高", "M 頭"), ("H_TD", "高", "TD 9 賣"), ("H_KD", "高", "KD 頂背離"), ("H_MACD", "高", "MACD 頂背離"),
       ("H_RSI", "高", "RSI 70 跌回"), ("H_VS", "高", "高檔爆量長上影"), ("H_EVE", "高", "黃昏之星"), ("H_ENG", "高", "空頭吞噬"),
       ("H_TL", "高", "上升趨勢線跌破"), ("H_MA", "高", "跌破 60 日線"),
       ("L_HS", "低", "頭肩底"), ("L_W", "低", "W 底"), ("L_TD", "低", "TD 9 買"), ("L_KD", "低", "KD 底背離"), ("L_MACD", "低", "MACD 底背離"),
       ("L_RSI", "低", "RSI 30 站回"), ("L_VS", "低", "低檔爆量長下影"), ("L_MOR", "低", "晨星"), ("L_ENG", "低", "多頭吞噬"),
       ("L_TL", "低", "下降趨勢線突破"), ("L_MA", "低", "站回 60 日線")]
CODES = [s[0] for s in SIG]
SIDE = {s[0]: s[1] for s in SIG}
NAME = {s[0]: s[2] for s in SIG}
_G: dict = {}


# ═════════════════════════════ 指標與訊號（有效 K 棒序列；索引＝序號）
def kd(h, l, c):
    n = len(c); K = np.full(n, np.nan); Dd = np.full(n, np.nan)
    k_ = 50.0; d_ = 50.0
    for t in range(8, n):
        hh = float(np.max(h[t - 8:t + 1])); ll = float(np.min(l[t - 8:t + 1]))
        rsv = 50.0 if hh == ll else (c[t] - ll) / (hh - ll) * 100.0
        k_ = k_ * 2.0 / 3.0 + rsv / 3.0
        d_ = d_ * 2.0 / 3.0 + k_ / 3.0
        K[t] = k_; Dd[t] = d_
    return K, Dd


def macd_dif(c):
    s = pd.Series(c)
    dif = (s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean()).to_numpy(float).copy()
    dif[:25] = np.nan
    return dif


def rsi(c, n=14):
    m = len(c); out = np.full(m, np.nan)
    if m <= n:
        return out
    dlt = np.diff(c); g = np.maximum(dlt, 0.0); lo = np.maximum(-dlt, 0.0)
    ag = float(np.mean(g[:n])); al = float(np.mean(lo[:n]))
    out[n] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for t in range(n + 1, m):
        ag = (ag * (n - 1) + g[t - 1]) / n; al = (al * (n - 1) + lo[t - 1]) / n
        out[t] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def ma_fsum(c, n):
    out = np.full(len(c), np.nan)
    if len(c) >= n:
        W = np.lib.stride_tricks.sliding_window_view(c, n)
        out[n - 1:] = np.fromiter((math.fsum(r) for r in W), float, count=len(W)) / n
    return out


def divergence(h, l, ind, top):
    n = len(h)
    piv = np.flatnonzero(SF.swing_lows(-h, 2) if top else SF.swing_lows(l, 2))
    ev = []; prev = None
    for s in piv:
        s = int(s)
        if prev is not None and s + 2 < n and np.isfinite(ind[s]) and np.isfinite(ind[prev]):
            ok = (h[s] > h[prev] and ind[s] < ind[prev]) if top else (l[s] < l[prev] and ind[s] > ind[prev])
            if ok:
                ev.append((s + 2, prev))
        prev = s
    return ev


def td9(c, up):
    n = len(c); ev = []; run = 0
    for t in range(n):
        ok = t >= 4 and ((c[t] > c[t - 4]) if up else (c[t] < c[t - 4]))
        run = run + 1 if ok else 0
        if run == 9:
            ev.append((t, t))
    return ev


def vol_shadow(o, h, l, c, v, top):
    n = len(c); ev = []
    if n <= 20:
        return ev
    vm = np.full(n, np.nan)
    W = np.lib.stride_tricks.sliding_window_view(v, 20)[:n - 20]
    vm[20:] = W.mean(axis=1)
    body = np.abs(c - o)
    with np.errstate(invalid="ignore"):
        if top:
            sh = h - np.fmax(o, c)
            ext = np.full(n, False); ext[19:] = h[19:] >= np.lib.stride_tricks.sliding_window_view(h, 20).max(axis=1)
        else:
            sh = np.fmin(o, c) - l
            ext = np.full(n, False); ext[19:] = l[19:] <= np.lib.stride_tricks.sliding_window_view(l, 20).min(axis=1)
        m = np.isfinite(vm) & (vm > 0) & (v > 2.0 * vm) & (sh > 0) & (sh >= 2.0 * body) & ext
    return [(int(t), int(t)) for t in np.flatnonzero(m)]


def ma_cross(c, up):
    ma = ma_fsum(c, 60); ev = []
    with np.errstate(invalid="ignore"):
        if up:
            m = (c[1:] > ma[1:]) & (c[:-1] <= ma[:-1])
        else:
            m = (c[1:] < ma[1:]) & (c[:-1] >= ma[:-1])
    m &= np.isfinite(ma[1:]) & np.isfinite(ma[:-1])
    return [(int(t) + 1, int(t) + 1) for t in np.flatnonzero(m)]


def rsi_cross(c, top):
    r = rsi(c); ev = []
    with np.errstate(invalid="ignore"):
        m = (r[:-1] > 70) & (r[1:] < 70) if top else (r[:-1] < 30) & (r[1:] > 30)
    return [(int(t) + 1, int(t) + 1) for t in np.flatnonzero(m)]


def up_line_events(o, l, c, R=5, num=99, lag=None):
    """PREREG上升趨勢線主格：PREREGM 甲 的鏡像（連低點）。收盤 ＜ 線 × num/100 且 前一根收盤 ≥ 線(前一根) × num/100 ⇒ 跌破。
    num＝100 時與 trendline_m.detect_pivot(−o, −l, −c, 甲) 應逐筆相同（閘門）。"""
    o = np.asarray(o, float); l = np.asarray(l, float); c = np.asarray(c, float); m = len(c)
    bot = np.fmin(o, c)
    lag = R if lag is None else lag
    piv = np.flatnonzero(SF.swing_lows(l, R))
    conf_at = {int(s + lag): int(s) for s in piv}
    conf, ev = [], []
    L = None

    def lv(L, b):
        return L["l1"] + L["slope"] * (b - L["p1"])

    def thr(x):
        return x if num == 100 else x * num / 100.0
    for b in range(m):
        if L is not None:
            if b - L["conf"] > TM.LIFE:
                L = None
            elif b >= 1 and c[b] < thr(lv(L, b)) and c[b - 1] >= thr(lv(L, b - 1)):
                ev.append((b, L["p1"])); L = None
        s = conf_at.get(b)
        if s is not None:
            conf.append(s); L = None
            if len(conf) >= 2:
                p1, p2 = conf[-2], conf[-1]
                if l[p2] > l[p1]:
                    slope = (l[p2] - l[p1]) / (p2 - p1)
                    if slope > 0 and b - p1 <= TM.MAX_SPAN:
                        seg = np.arange(p1, p2 + 1); keep = (seg != p1) & (seg != p2)
                        line = l[p1] + slope * (seg - p1)
                        if not np.any(bot[seg][keep] < line[keep]):
                            L = {"p1": int(p1), "l1": float(l[p1]), "slope": float(slope), "conf": int(b)}
    return ev


def detect(o, h, l, c, v, ro, rh, rl, rc):
    """有效 K 棒序列 ⇒ {code: [(T, first)]}（依 T 排序、同 T 只留一筆）。"""
    out = {}
    K = PA.detect_kbars(o, h, l, c, ro, rh, rl, rc)
    for code, vid in (("H_EVE", "K02"), ("H_ENG", "K61"), ("L_MOR", "K07"), ("L_ENG", "K56")):
        out[code] = list(zip(K[vid]["T"].tolist(), K[vid]["first"].tolist()))
    r60 = PA._rN(c, PA.R60)
    ev, seen = [], set()
    for e in sorted(set(PA.detect_turns(c, r60)["S01"])):
        if e[0] not in seen:
            seen.add(e[0]); ev.append((int(e[0]), int(e[1])))
    out["H_M"] = ev
    out["L_W"] = [(int(e["T"]), int(e["first"])) for e in PX.detect_turn("w", c)["events"]]
    out["L_HS"] = [(int(e["T"]), int(e["first"])) for e in PX.detect_turn("hs", c)["events"]]
    out["L_TL"] = [(int(e["T"]), int(e["first"])) for e in TM.detect_bars(o, h, c, "甲", TM.R_MAIN)["events"]]
    out["H_TL"] = up_line_events(o, l, c)
    out["H_TD"] = td9(c, True); out["L_TD"] = td9(c, False)
    K_, _ = kd(h, l, c); dif = macd_dif(c)
    out["H_KD"] = divergence(h, l, K_, True); out["L_KD"] = divergence(h, l, K_, False)
    out["H_MACD"] = divergence(h, l, dif, True); out["L_MACD"] = divergence(h, l, dif, False)
    out["H_RSI"] = rsi_cross(c, True); out["L_RSI"] = rsi_cross(c, False)
    out["H_VS"] = vol_shadow(o, h, l, c, v, True); out["L_VS"] = vol_shadow(o, h, l, c, v, False)
    out["H_MA"] = ma_cross(c, False); out["L_MA"] = ma_cross(c, True)
    for k_ in out:
        d = {}
        for T, f in out[k_]:
            if T not in d:
                d[T] = f
        out[k_] = sorted(d.items())
    return out


def gate_upline(o, l, c):
    """閘：num＝100 的鏡像 ＝ trendline_m.detect_pivot(−o, −l, −c, 甲) 逐筆（T 與 P1）。"""
    a = up_line_events(o, l, c, num=100)
    b = [(int(e["T"]), int(e["anchors"][0])) for e in TM.detect_pivot(-np.asarray(o, float), -np.asarray(l, float), -np.asarray(c, float), "甲", TM.R_MAIN)["events"]]
    return a == b, len(a)


def merge20(T):
    keep = np.zeros(len(T), bool); t0 = -10 ** 9
    for i, t in enumerate(T):
        if not (t0 < t <= t0 + MERGE):
            keep[i] = True; t0 = t
    return keep


def confirm_day(c_cal, valid, h_T, l_T, T, top, last):
    for k in range(1, CONF_N + 1):
        d = T + k
        if d > last:
            return -1
        if valid[d] and ((c_cal[d] < l_T) if top else (c_cal[d] > h_T)):
            return d
    return -1


# ═════════════════════════════ 大盤層（0050）
def git(*a):
    return subprocess.run(["git", "-C", DB, *a], capture_output=True, text=True, check=True).stdout


def load_raw(sid, cal):
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close", "volume"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close", "volume"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    bad = (raw[["open", "high", "low", "close"]] <= 0).any(axis=1)
    raw.loc[bad, ["open", "high", "low", "close"]] = np.nan
    raw = raw.reindex(cal)
    return [raw[c].to_numpy(float) for c in ("open", "high", "low", "close", "volume")]


def market_series():
    """回 (main, spliced)：各為 dict(dates, o,h,l,c,v 還原, ro,rh,rl,rc 原始)，只含有效 K 棒（收盤有限）。"""
    cal = D.load_calendar()
    st = D.load_stock("0050", "twse", cal); df = st.df
    ro, rh, rl, rc, rv = load_raw("0050", cal)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy(float)
    b = np.flatnonzero(np.isfinite(c))
    main = {"dates": np.array([str(x.date()) for x in cal]), "o": o, "h": h, "l": l, "c": c, "v": v,
            "ro": ro, "rh": rh, "rl": rl, "rc": rc}
    sha = git("rev-parse", EARLY_SHA).strip()
    rows = git("grep", "-h", "_0050,", sha, "--", "data/early/daily/")
    cols = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
            "shares", "transactions", "price_basis", "last_price"]
    d = pd.read_csv(io.StringIO(rows), header=None, names=cols, dtype=str)
    d = d[d["stock_id"] == "0050"].copy()
    for k in ("open", "high", "low", "close", "volume"):
        d[k] = pd.to_numeric(d[k], errors="coerce")
    bad = (d[["open", "high", "low", "close"]] <= 0).any(axis=1)
    d.loc[bad, ["open", "high", "low", "close"]] = np.nan
    d = d.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    d = d[(d["date"] < main["dates"][0]) & d["close"].notna()].reset_index(drop=True)
    ex = git("grep", "-h", ",0050,", sha, "--", "data/early/exright/")
    e = pd.read_csv(io.StringIO(ex), header=None, names=["date", "stock_id", "pre_close", "ref_price", "value", "kind", "open_base",
                                                         "limit_up", "limit_down", "ex_div_ref"], dtype={"date": str, "stock_id": str})
    e = e[e["stock_id"] == "0050"].sort_values("date").reset_index(drop=True)
    f = e["ref_price"].astype(float).to_numpy() / e["pre_close"].astype(float).to_numpy()
    evd = e["date"].to_numpy()
    F = np.array([np.prod(f[evd > x]) for x in d["date"].to_numpy()])
    s = main["c"][b[0]] / main["rc"][b[0]]
    early = {"dates": d["date"].to_numpy()}
    for k, rk in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close")):
        early["r" + k] = d[rk].to_numpy(float)
        early[k] = d[rk].to_numpy(float) * F * s
    early["v"] = d["volume"].to_numpy(float)
    spl = {k: np.concatenate([early[k], main[k]]) for k in main}
    for X in (main, spl):
        X["valid"] = np.isfinite(X["c"]); X["bars"] = np.flatnonzero(X["valid"]); X["lv"] = AV.last_valid(X["valid"])
    info = {"主快照日曆上 0050 沒有 K 棒的日子": [str(x) for x in main["dates"][~main["valid"]]], "早年 sha": sha, "早年列數": int(len(d)), "早年首日": str(d["date"].iloc[0]), "除息筆數": int(len(e)),
            "接點比例 s（主快照首日 還原÷原始）": float(s), "主快照首日": str(main["dates"][0]),
            "接點前後原始量": [float(early["v"][-1]), float(main["v"][b[0]])], "主快照 0050 有效根數": int(len(b)),
            "早年還原開盤缺值": int((~np.isfinite(early["o"])).sum())}
    return main, spl, info


def mk_events(S, T, first, top, lo, hi):
    """一條序列（日曆對齊、洞＝NaN）上的事件：窗 [lo, hi − 20]、合併 20、剔除 T＋1 停牌（開盤無效）、確認版。回 DataFrame。"""
    rows = []
    T = np.asarray(T, int); first = np.asarray(first, int)
    m = (T >= lo) & (T <= hi - HS[0])
    T, first = T[m], first[m]
    keep = merge20(T)
    for t, f, k in zip(T, first, keep):
        if not k:
            continue
        st = "保留" if np.isfinite(S["o"][t + 1]) else "剔除_停牌"
        C = confirm_day(S["c"], S["valid"], S["h"][t], S["l"][t], t, top, hi)
        stc = "沒確認" if C < 0 else ("窗外" if C + HS[0] > hi else ("保留" if np.isfinite(S["o"][C + 1]) else "剔除_停牌"))
        rows.append({"T": int(t), "first": int(f), "C": int(C), "st": st, "st_c": stc})
    return pd.DataFrame(rows, columns=["T", "first", "C", "st", "st_c"]), int(m.sum()), int((~keep).sum())


def fwd(S, b, H, hi):
    """b 收盤後 ⇒ b＋1 開盤進、b＋H 收盤出（無成交 ⇒ 之前最後一根有效收盤）；超出 hi 或 b＋1 開盤無效 ⇒ NaN。"""
    if b < 0 or b + H > hi or not np.isfinite(S["o"][b + 1]):
        return np.nan
    return float(S["c"][S["lv"][b + H]] / S["o"][b + 1] - 1.0)


def base_days(S, lo, hi, H):
    return np.array([d for d in range(lo, hi - H + 1) if S["valid"][d] and np.isfinite(S["o"][d + 1])], int)


def detect_series(X):
    b = X["bars"]
    ev = detect(*(np.asarray(X[k], float)[b] for k in ("o", "h", "l", "c", "v", "ro", "rh", "rl", "rc")))
    return {k: [(int(b[t]), int(b[f])) for t, f in v] for k, v in ev.items()}


# ═════════════════════════════ 個股層
def stock_one(args):
    sid, market, mode = args
    cal, w0, w1, off, elig = _G["cal"], _G["w0"], _G["w1"], _G["off"], _G["elig"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df; n = len(cal)
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 30:
        return None
    ro, rh, rl, rc, _ = load_raw(sid, cal)
    sel = lambda x: np.asarray(x, float)[bars]
    ev = detect(sel(o), sel(h), sel(l), c[bars], sel(v), sel(ro), sel(rh), sel(rl), sel(rc))
    g_ok, g_n = gate_upline(sel(o), sel(l), c[bars])
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = MF._g5(valid, upto=ds["last"]) if delisted else MF._g5(valid)
    S = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    lv = AV.last_valid(valid)
    mon = _G["mon"]
    em = elig.get(sid, set())
    halt = ~tb["trd"] | ~np.isfinite(o)

    def entry_bad(t):
        return "剔除_停牌" if halt[t + 1] else ("剔除_開盤漲停" if tb["up_o"][t + 1] else ("剔除_開盤跌停" if tb["dn_o"][t + 1] else None))
    rows = []
    for code in CODES:
        top = SIDE[code] == "高"
        if not ev[code]:
            continue
        T = bars[np.array([t for t, _ in ev[code]], int)]; F = bars[np.array([f for _, f in ev[code]], int)]
        m = (T >= w0) & (T <= w1 - HS[0])
        T, F = T[m], F[m]
        m2 = np.array([mon[t] in em for t in T], bool) if len(T) else np.zeros(0, bool)
        n_win, n_inelig = int(len(T)), int((~m2).sum())
        T, F = T[m2], F[m2]
        keep = merge20(T)
        for t, f, k in zip(T, F, keep):
            r = {"sid": sid, "market": market, "code": code, "T": int(t), "first": int(f)}
            if not k:
                r["st"] = "合併掉"; rows.append(r); continue
            why = "剔除_硬斷點" if H2.brk(S, int(f), int(t) + HS[0]) else entry_bad(t)
            r["st"] = why or "保留"
            C = confirm_day(c, valid, h[t], l[t], int(t), top, w1)
            r["C"] = int(C)
            if C >= 0:
                cw = "窗外" if C + HS[0] > w1 else ("剔除_硬斷點" if H2.brk(S, int(f), int(C) + HS[0]) else entry_bad(C))
                r["st_c"] = cw or "保留"
            else:
                r["st_c"] = "沒確認"
            if mode == "body":
                if r["st"] == "保留":
                    r["R20"] = float(c[lv[t + 20]] / o[t + 1] - 1.0)
                    r["R60"] = float(c[lv[t + 60]] / o[t + 1] - 1.0) if (t + 60 <= w1 and not H2.brk(S, int(f), int(t) + 60)) else np.nan
                if r["st_c"] == "保留":
                    r["R20c"] = float(c[lv[C + 20]] / o[C + 1] - 1.0)
                    r["R60c"] = float(c[lv[C + 60]] / o[C + 1] - 1.0) if (C + 60 <= w1 and not H2.brk(S, int(f), int(C) + 60)) else np.nan
            rows.append(r)
        rows.append({"sid": sid, "market": market, "code": code, "T": -1, "st": "_計數", "n_win": n_win, "n_inelig": n_inelig})
    days = None
    if mode == "body":                                      # 基準股日：母體內、[w0, w1−20]
        dd = np.arange(w0, w1 - HS[0] + 1)
        dd = dd[np.array([mon[t] in em for t in dd], bool)] if em else np.zeros(0, int)
        r20p = AV.r20_cal(c, bars)
        R = np.full(len(dd), np.nan)
        if len(dd):
            ok = valid[dd] & ~halt[dd + 1] & ~tb["up_o"][dd + 1] & ~tb["dn_o"][dd + 1] & ~AV.brk_vec(S["cs_pb"], S["cs_g5"], dd, dd + HS[0])
            with np.errstate(invalid="ignore", divide="ignore"):
                Rall = c[lv[dd + HS[0]]] / o[dd + 1] - 1.0
            R = np.where(ok, Rall, np.nan)
        days = {"d": dd.astype(np.int32), "r20p": r20p[dd], "R20": R}
    return {"sid": sid, "market": market, "rows": rows, "days": days, "gate": (bool(g_ok), int(g_n))}


def _init(d):
    _G.update(d)


def stock_universe(cal):
    from backtest import p4_features as P4F
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    p = P4F.read_panel(os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))]
    elig = {}
    for sid, g in p.groupby("stock_id"):
        elig[sid] = set(str(x)[:7] for x in g["measure_date"])
    mk = U.set_index("stock_id")["market"]
    return sorted(elig), elig, mk


def run_stocks(cal, w0, w1, mode, procs, limit, log):
    sids, elig, mk = stock_universe(cal)
    if limit:
        sids = sids[:limit]
    mon = np.array([str(d)[:7] for d in cal])
    init = {"cal": cal, "w0": w0, "w1": w1, "off": TR.load_official(), "elig": elig, "mon": mon}
    res = []
    t0 = time.time()
    with Pool(procs, initializer=_init, initargs=(init,)) as pool:
        for i, r in enumerate(pool.imap_unordered(stock_one, [(s, mk.get(s, "twse"), mode) for s in sids], chunksize=4)):
            if r is not None:
                res.append(r)
            if (i + 1) % 400 == 0:
                log(f"  [個股 {mode}] {i + 1}/{len(sids)}｜{time.time() - t0:.0f}s")
    return res, len(sids)


# ═════════════════════════════ 統計
def zb(k):
    return NormalDist().inv_cdf(1 - (0.05 / max(k, 1)) / 2)


def ci(x, g, z):
    m, se, ng = AV.cr0(np.asarray(x, float), np.asarray(g))
    n = len(x); ne = int(min(n, ng))
    lo, hi = m - z * se, m + z * se
    ex, rs = AV.exit_result(m, lo, hi, n, ne)
    return {"mean": m, "se": se, "lo": lo, "hi": hi, "n": n, "群數": int(ng), "n_eff": ne, "出口": ex, "結果": rs}


def verdict(code, c):
    if c["n_eff"] < NEFF_MIN:
        return "不可判定"
    ok = (c["結果"] == "結果③") if SIDE[code] == "高" else (c["結果"] == "結果②")
    return "通過" if ok else "不通過"


def succ(code, R):
    R = np.asarray(R, float)
    return float((R < 0).mean()) if SIDE[code] == "高" else float((R > 0).mean())


# ═════════════════════════════ 主程式
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pre", "body", "report"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.mode == "report":
        report(a.out); return
    logf = open(os.path.join(a.out, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    log(f"===== researchRev {a.mode} procs={a.procs} limit={a.limit} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("researchRev.py", "patterns_all.py", "patterns_x.py", "trendline_m.py", "stop_fractal.py", "avgdown.py")}
    log(f"[程式 sha256] {src}")
    cal = D.load_calendar()
    w0, w1 = int(cal.searchsorted(pd.Timestamp(W0))), int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1
    SP = os.path.join(a.out, "summary.json")
    S = json.load(open(SP, encoding="utf-8")) if os.path.exists(SP) else {}
    S.update({"登錄": "PREREG反轉訊號 seq2 sha 6309d93ebdf2652f；裁定 seq226；讀法裁定（頭肩頂、2B 不收；21 種）", "程式": src,
              "訊號": {c: {"名": NAME[c], "邊": SIDE[c]} for c in CODES}})
    # ── 大盤層
    Mm, Ms, info = market_series()
    S["大盤資料"] = info
    ev_main = detect_series(Mm)
    ev_spl = detect_series(Ms)
    dM, dS = Mm["dates"], Ms["dates"]
    mw0, mw1 = int(np.searchsorted(dM, W0)), int(np.searchsorted(dM, W1))
    assert dM[mw0] == W0 and dM[mw1] == W1
    cal_w = [str(x.date()) for x in cal[w0:w1 + 1]]
    g_cal = list(dM[mw0:mw1 + 1]) == cal_w
    g_spl = {}
    for code in CODES:
        a_ = [dM[t] for t, _ in ev_main[code] if W0 <= dM[t] <= W1]
        b_ = [dS[t] for t, _ in ev_spl[code] if W0 <= dS[t] <= W1]
        g_spl[code] = a_ == b_
    bM = Mm["bars"]
    g_up, n_up = gate_upline(Mm["o"][bM], Mm["l"][bM], Mm["c"][bM])
    S["閘_大盤"] = {"主快照日曆 ＝ 大盤層日曆（主窗）": g_cal, "接起來的序列在主窗的事件 ＝ 只用主快照": all(g_spl.values()),
                  "不一致的訊號": [c for c, v in g_spl.items() if not v], "上升線鏡像(num=100) ＝ trendline_m 取負": g_up, "上升線事件數(num=100)": n_up}
    log(f"[閘 大盤] {S['閘_大盤']}")
    if not (g_cal and all(g_spl.values()) and g_up):
        json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        raise SystemExit("⛔ 閘不過（大盤）")
    ew0 = int(np.searchsorted(dS, E0)); ew1 = int(np.searchsorted(dS, E1, side="right")) - 1
    assert dS[ew0] == E0 and dS[ew1] == E1, (dS[ew0], dS[ew1])
    MK = {}
    for seg, (ser, evs, lo, hi) in {"主窗": (Mm, ev_main, mw0, mw1), "早年": (Ms, ev_spl, ew0, ew1)}.items():
        for code in CODES:
            E = evs[code]
            E_df, n_win, n_merged = mk_events(ser, [t for t, _ in E], [f for _, f in E], SIDE[code] == "高", lo, hi)
            MK[(seg, code)] = (E_df, n_win, n_merged)
    # ── pre
    if a.mode == "pre":
        pre = {"大盤": [], "個股": []}
        for (seg, code), (E_df, n_win, n_merged) in MK.items():
            lo = mw0 if seg == "主窗" else ew0
            for ver in ("原版", "確認版"):
                bd = E_df.loc[E_df["st"] == "保留", "T"].to_numpy(int) if ver == "原版" else E_df.loc[E_df["st_c"] == "保留", "C"].to_numpy(int)
                segs = np.unique((bd - lo) // 20)
                pre["大盤"].append({"段": seg, "code": code, "名": NAME[code], "邊": SIDE[code], "版": ver, "窗內原始": n_win, "合併掉": n_merged,
                                  "剔除_停牌": int((E_df["st"] if ver == "原版" else E_df["st_c"]).eq("剔除_停牌").sum()),
                                  "事件": int(len(bd)), "20日區段": int(len(segs)), "n_eff": int(min(len(bd), len(segs))),
                                  "沒確認": int(((E_df["st"] == "保留") & (E_df["C"] < 0)).sum()) if ver == "確認版" else None})
        res, nU = run_stocks(cal, w0, w1, "pre", a.procs, a.limit, log)
        rows = pd.DataFrame([r for x in res for r in x["rows"]])
        cnt = rows[rows["st"] == "_計數"]; ev = rows[rows["st"] != "_計數"]
        mon = np.array([str(d)[:7] for d in cal])
        g_bad = [x["sid"] for x in res if not x["gate"][0]]
        S["閘_個股"] = {"上升線鏡像(num=100) ＝ trendline_m 取負：不一致檔數": len(g_bad), "例": g_bad[:5], "檢查檔數": len(res),
                      "事件數(num=100)": int(sum(x["gate"][1] for x in res))}
        log(f"[閘 個股] {S['閘_個股']}")
        for code in CODES:
            e = ev[ev["code"] == code]; cc = cnt[cnt["code"] == code]
            for ver in ("原版", "確認版"):
                if ver == "原版":
                    k = e[e["st"] == "保留"]; bd = k["T"].to_numpy(int)
                else:
                    k = e[e["st_c"] == "保留"] if "st_c" in e.columns else e.iloc[0:0]; bd = k["C"].to_numpy(int)
                ms = np.unique(mon[bd]) if len(bd) else []
                stc = e["st"].value_counts().to_dict()
                pre["個股"].append({"code": code, "名": NAME[code], "邊": SIDE[code], "版": ver,
                                  "窗內原始": int(cc["n_win"].sum()), "非母體": int(cc["n_inelig"].sum()),
                                  "合併掉": int(stc.get("合併掉", 0)), "剔除_硬斷點": int(stc.get("剔除_硬斷點", 0)),
                                  "剔除_停牌": int(stc.get("剔除_停牌", 0)), "剔除_開盤漲停": int(stc.get("剔除_開盤漲停", 0)),
                                  "剔除_開盤跌停": int(stc.get("剔除_開盤跌停", 0)),
                                  "事件": int(len(bd)), "月數": int(len(ms)), "n_eff": int(min(len(bd), len(ms))),
                                  "沒確認（原版保留者）": int(((e["st"] == "保留") & (e["C"] < 0)).sum()) if ver == "確認版" else None})
        S["個股母體檔數"] = nU
        json.dump(pre, open(os.path.join(a.out, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        S["pre"] = {lay: {"可判定格數（主窗、n_eff ≥ 10）": int(sum(1 for r in pre[lay] if r.get("段", "主窗") == "主窗" and r["n_eff"] >= NEFF_MIN)),
                          "格數": int(sum(1 for r in pre[lay] if r.get("段", "主窗") == "主窗"))} for lay in pre}
        S["pre完成"] = time.strftime("%F %T")
        log(f"[pre] {S['pre']}｜{time.time() - t00:.0f}s")
        json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        return
    # ── body：大盤
    cells = []; evrows = []; fake = []
    for seg, ser, lo, hi in (("主窗", Mm, mw0, mw1), ("早年", Ms, ew0, ew1)):
        base = {H: np.array([fwd(ser, d, H, hi) for d in base_days(ser, lo, hi, H)]) for H in HS}
        for code in CODES:
            E_df = MK[(seg, code)][0]
            for ver in ("原版", "確認版"):
                bd = E_df.loc[E_df["st"] == "保留", "T"].to_numpy(int) if ver == "原版" else E_df.loc[E_df["st_c"] == "保留", "C"].to_numpy(int)
                R = {H: np.array([fwd(ser, d, H, hi) for d in bd]) for H in HS}
                for d, r20, r60 in zip(bd, R[20], R[60]):
                    evrows.append({"層": "大盤", "段": seg, "code": code, "版": ver, "基準日": ser["dates"][d], "R20": r20, "R60": r60})
                row = {"層": "大盤", "段": seg, "code": code, "名": NAME[code], "邊": SIDE[code], "版": ver, "事件": int(len(bd)),
                       "成功率": succ(code, R[20]) if len(bd) else np.nan, "基準成功率": succ(code, base[20]),
                       "R20平均": float(np.mean(R[20])) if len(bd) else np.nan, "R20中位": float(np.median(R[20])) if len(bd) else np.nan,
                       "基準R20平均": float(np.mean(base[20])),
                       "R60平均": float(np.nanmean(R[60])) if np.isfinite(R[60]).any() else np.nan,
                       "R60中位": float(np.nanmedian(R[60])) if np.isfinite(R[60]).any() else np.nan,
                       "基準R60平均": float(np.nanmean(base[60])), "R60事件": int(np.isfinite(R[60]).sum())}
                X = R[20] - float(np.mean(base[20]))
                g = (bd - lo) // 20
                row["_X"] = X; row["_g"] = g
                if ver == "確認版":
                    unc = E_df.loc[(E_df["C"] < 0) & (E_df["st"] == "保留"), "T"].to_numpy(int)
                    Ru = np.array([fwd(ser, d, 20, hi) for d in unc])
                    row.update({"沒確認": int(len(unc)), "沒確認比例": float(len(unc) / max(1, int((E_df["st"] == "保留").sum()))),
                                "放棄組R20平均": float(Ru.mean()) if len(Ru) else np.nan, "放棄組成功率": succ(code, Ru) if len(Ru) else np.nan})
                yrs = np.array([int(ser["dates"][d][:4]) for d in bd])
                for y in sorted(set(yrs)):
                    row[f"y{y}"] = float(np.mean(X[yrs == y]))
                cells.append(row)
        S[f"大盤基準_{seg}"] = {"R20平均": float(np.mean(base[20])), "R20＜0比例": float((base[20] < 0).mean()), "R20＞0比例": float((base[20] > 0).mean()),
                              "日數": int(len(base[20]))}
        if seg == "主窗":
            S["_bdays"] = [int(lo), int(hi)]
    # ── body：個股
    res, nU = run_stocks(cal, w0, w1, "body", a.procs, a.limit, log)
    rows = pd.DataFrame([r for x in res for r in x["rows"] if r["st"] != "_計數"])
    rows.to_csv(os.path.join(a.out, "stock_rows.csv.gz"), index=False, float_format="%.17g")
    mon = np.array([str(d)[:7] for d in cal])
    DD = []
    for x in res:
        dd = x["days"]
        if dd is not None and len(dd["d"]):
            DD.append(pd.DataFrame({"sid": x["sid"], "d": dd["d"], "r20p": dd["r20p"], "R20": dd["R20"]}))
    DD = pd.concat(DD, ignore_index=True).sort_values(["d", "sid"]).reset_index(drop=True)
    dec = np.full(len(DD), -1, int)
    for d, idx in DD.groupby("d").indices.items():
        dec[idx] = AV.deciles(DD["r20p"].to_numpy()[idx])
    DD["dec"] = dec; DD["m"] = mon[DD["d"].to_numpy()]
    fin = DD[np.isfinite(DD["R20"])]
    B1 = fin.groupby("m")["R20"].agg(["mean", "count"]); B1["neg"] = fin.assign(x=fin["R20"] < 0).groupby("m")["x"].mean()
    B1["pos"] = fin.assign(x=fin["R20"] > 0).groupby("m")["x"].mean()
    f2 = fin[fin["dec"] >= 0]
    B2 = f2.groupby(["m", "dec"])["R20"].agg(["mean", "count"])
    B2["neg"] = f2.assign(x=f2["R20"] < 0).groupby(["m", "dec"])["x"].mean(); B2["pos"] = f2.assign(x=f2["R20"] > 0).groupby(["m", "dec"])["x"].mean()
    B1.to_csv(os.path.join(a.out, "stock_base1.csv")); B2.to_csv(os.path.join(a.out, "stock_base2.csv"))
    DD[["sid", "d", "r20p", "R20", "dec"]].to_csv(os.path.join(a.out, "stock_days.csv.gz"), index=False, float_format="%.17g")
    key = {(s, int(d)): int(q) for s, d, q in zip(DD["sid"], DD["d"], DD["dec"])}
    S["個股基準"] = {"股日": int(len(DD)), "有報酬股日": int(len(fin)), "R20平均（全部股日）": float(fin["R20"].mean())}
    stock_ev = []
    for code in CODES:
        e = rows[rows["code"] == code]
        for ver in ("原版", "確認版"):
            if ver == "原版":
                k = e[e["st"] == "保留"].copy(); k["bd"] = k["T"]; k["R"] = k["R20"]; k["R6"] = k["R60"]
            else:
                k = e[e["st_c"] == "保留"].copy() if "st_c" in e else e.iloc[0:0].copy(); k["bd"] = k["C"]; k["R"] = k["R20c"]; k["R6"] = k["R60c"]
            k["m"] = mon[k["bd"].to_numpy(int)] if len(k) else []
            k["dec"] = [key.get((s, int(d)), -1) for s, d in zip(k["sid"], k["bd"])]
            k["b1"] = [B1["mean"].get(m_, np.nan) for m_ in k["m"]]
            k["b2"] = [B2["mean"].get((m_, q), np.nan) if q >= 0 else np.nan for m_, q in zip(k["m"], k["dec"])]
            side = "neg" if SIDE[code] == "高" else "pos"
            k["s1"] = [B1[side].get(m_, np.nan) for m_ in k["m"]]
            k["s2"] = [B2[side].get((m_, q), np.nan) if q >= 0 else np.nan for m_, q in zip(k["m"], k["dec"])]
            nb = int(np.isnan(k["b2"].to_numpy(float)).sum()) if len(k) else 0
            kk = k[np.isfinite(k["b2"].to_numpy(float))] if len(k) else k
            X = (kk["R"] - kk["b2"]).to_numpy(float)
            row = {"層": "個股", "段": "主窗", "code": code, "名": NAME[code], "邊": SIDE[code], "版": ver, "事件": int(len(kk)), "基準2缺": nb,
                   "成功率": succ(code, kk["R"]) if len(kk) else np.nan, "基準1成功率": float(kk["s1"].mean()) if len(kk) else np.nan,
                   "基準2成功率": float(kk["s2"].mean()) if len(kk) else np.nan, "R20平均": float(kk["R"].mean()) if len(kk) else np.nan,
                   "R20中位": float(kk["R"].median()) if len(kk) else np.nan, "基準1R20平均": float(kk["b1"].mean()) if len(kk) else np.nan,
                   "基準2R20平均": float(kk["b2"].mean()) if len(kk) else np.nan,
                   "R60平均": float(np.nanmean(kk["R6"])) if len(kk) and np.isfinite(kk["R6"].to_numpy(float)).any() else np.nan,
                   "_X": X, "_g": kk["m"].to_numpy() if len(kk) else np.zeros(0)}
            for m_ in ("twse", "tpex"):
                q = kk["market"].to_numpy() == m_ if len(kk) else np.zeros(0, bool)
                row[f"X_{m_}"] = float(X[q].mean()) if q.any() else np.nan; row[f"n_{m_}"] = int(q.sum())
            if ver == "確認版":
                orig = e[e["st"] == "保留"]
                unc = orig[orig["C"] < 0]
                row.update({"沒確認": int(len(unc)), "沒確認比例": float(len(unc) / max(1, len(orig))),
                            "放棄組R20平均": float(unc["R20"].mean()) if len(unc) else np.nan,
                            "放棄組成功率": succ(code, unc["R20"]) if len(unc) else np.nan})
            yrs = np.array([int(m_[:4]) for m_ in kk["m"]]) if len(kk) else np.zeros(0, int)
            for y in sorted(set(yrs)):
                row[f"y{y}"] = float(X[yrs == y].mean())
            cells.append(row)
            kk2 = kk[["sid", "market", "T", "C", "bd", "R", "R6", "b1", "b2", "dec"]].copy() if len(kk) else pd.DataFrame()
            if len(kk2):
                kk2["code"] = code; kk2["版"] = ver; stock_ev.append(kk2)
    # ── 判定（主窗；Bonferroni 按層、兩版合計 n_eff ≥ 10）
    for lay in ("大盤", "個股"):
        L_ = [c for c in cells if c["層"] == lay and c["段"] == "主窗"]
        for c in L_:
            ng = len(np.unique(c["_g"])) if len(c["_X"]) else 0
            c["n_eff"] = int(min(len(c["_X"]), ng))
        k = sum(1 for c in L_ if c["n_eff"] >= NEFF_MIN)
        z = zb(k)
        S[f"Bonferroni_{lay}"] = {"k": k, "α": 0.05 / max(k, 1), "z": z}
        for c in L_:
            if c["n_eff"] >= NEFF_MIN:
                c.update(ci(c["_X"], c["_g"], z))
            else:
                c.update({"mean": float(np.mean(c["_X"])) if len(c["_X"]) else np.nan, "出口": "依構造不可判定", "結果": "—"})
            c["判定"] = verdict(c["code"], c)
    # 早年（描述）
    for c in cells:
        if c["段"] == "早年":
            c["mean"] = float(np.mean(c["_X"])) if len(c["_X"]) else np.nan
            c["n_eff"] = int(min(len(c["_X"]), len(np.unique(c["_g"])))) if len(c["_X"]) else 0
            c["判定"] = "描述"
    # 假訊號臂（大盤主窗）
    rng = np.random.default_rng(20260927)
    lo, hi = mw0, mw1
    bdM = base_days(Mm, lo, hi, 20)
    base20 = np.array([fwd(Mm, d, 20, hi) for d in bdM]); bm = float(base20.mean())
    zM = S["Bonferroni_大盤"]["z"]
    for c in cells:
        if c["層"] != "大盤" or c["段"] != "主窗" or c["n_eff"] < NEFF_MIN:
            continue
        n = c["事件"]; passed = 0
        for _ in range(FAKE_N):
            ii = np.sort(rng.choice(len(bdM), size=n, replace=False))
            X = base20[ii] - bm; g = (bdM[ii] - lo) // 20
            r = ci(X, g, zM)
            if r["n_eff"] >= NEFF_MIN and ((r["結果"] == "結果③") if SIDE[c["code"]] == "高" else (r["結果"] == "結果②")):
                passed += 1
        c["假訊號過的比例"] = passed / FAKE_N
        fake.append({"code": c["code"], "版": c["版"], "事件": n, "隨機也過": passed, "次數": FAKE_N})
    # ── 輸出
    C = pd.DataFrame([{k: v for k, v in c.items() if not k.startswith("_")} for c in cells])
    C.to_csv(os.path.join(a.out, "cells.csv"), index=False)
    pd.DataFrame(evrows).to_csv(os.path.join(a.out, "events_market.csv"), index=False, float_format="%.17g")
    X_all = []
    for c in cells:
        X_all.append(pd.DataFrame({"層": c["層"], "段": c["段"], "code": c["code"], "版": c["版"], "X": c["_X"], "g": c["_g"]}))
    pd.concat(X_all, ignore_index=True).to_csv(os.path.join(a.out, "cell_x.csv.gz"), index=False, float_format="%.17g")
    if stock_ev:
        pd.concat(stock_ev, ignore_index=True).to_csv(os.path.join(a.out, "events_stock.csv.gz"), index=False, float_format="%.17g")
    pd.DataFrame(fake).to_csv(os.path.join(a.out, "fake_market.csv"), index=False)
    S.pop("_bdays", None)
    S["body完成"] = time.strftime("%F %T"); S["秒_body"] = round(time.time() - t00)
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[body 完成] {time.time() - t00:.0f}s")
    report(a.out)


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.{d}f}%"


def _r(x):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:.1f}%"


def report(OUT_):
    S = json.load(open(os.path.join(OUT_, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT_, "cells.csv"))
    M = C[C["段"] == "主窗"]
    npass = {lay: int(((M["層"] == lay) & (M["判定"] == "通過")).sum()) for lay in ("大盤", "個股")}
    L = ["# PREREG反轉訊號：0050 與個股的高點／低點反轉訊號，原版 vs 加確認", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq2（sha 6309d93ebdf2652f）；裁定 seq226；回測線。", ""]
    passed = M[M["判定"] == "通過"]
    if len(passed):
        s = "、".join(f"{r.層}{r.版}〔{r.名}〕" for r in passed.itertuples())
        L.append(f"**結論：21 個訊號 × 兩層 × 兩版裡，通過的是 {s}；其餘都看不出比隨便一天（大盤）或同月同走勢的股票（個股）準。**")
    else:
        L.append("**結論：21 個訊號 × 兩層 × 兩版，沒有一個通過：高點訊號之後沒有比平常容易跌、低點訊號之後沒有比平常容易漲（大盤對隨便一天、個股對同月同走勢的股票）。**")
    L += ["", f"Bonferroni：大盤 k＝{S['Bonferroni_大盤']['k']}、個股 k＝{S['Bonferroni_個股']['k']}（各層兩版合計 n_eff ≥ 10 的格數）。成功率：高點＝20 日後下跌的比例、低點＝上漲的比例。", "",
          "| 訊號 | 邊 | 大盤 原版 | 大盤 確認版 | 個股 原版 | 個股 確認版 |", "|---|---|---|---|---|---|"]

    def cell(lay, code, ver):
        q = M[(M["層"] == lay) & (M["code"] == code) & (M["版"] == ver)]
        if not len(q):
            return "—"
        q = q.iloc[0]
        b = q["基準成功率"] if lay == "大盤" else q["基準2成功率"]
        if q["判定"] == "不可判定":
            return f"不可判定（n_eff {int(q['n_eff'])}）"
        return f"**{q['判定']}**｜成功率 {_r(q['成功率'])} vs {_r(b)}｜差 {_p(q['mean'])}"
    for code in CODES:
        L.append(f"| {NAME[code]} | {SIDE[code]}點 | {cell('大盤', code, '原版')} | {cell('大盤', code, '確認版')} | {cell('個股', code, '原版')} | {cell('個股', code, '確認版')} |")
    L += ["", "「差」＝ 訊號後 20 日報酬 − 基準（大盤：同窗所有交易日平均；個股：同月、同一天前 20 日報酬同十分位的股票）；成功率 vs 後面那個是基準的同一比例（個股是基準②）。", "",
          "- 進場從訊號日（確認版：確認日）次一交易日開盤起算；⛔ 沒扣成本（基準同）",
          "- 登錄寫「22 種」，但照「無定義不收」落地後是 21 種：頭肩頂、2B 頂、2B 底 本專案沒有機器定義 ⇒ 不收（裁定）",
          "- 個股層假訊號臂：登錄 §七未列 ⇒ 不跑", "- 這是全市場（個股層）／0050 的平均，不是對某一檔、某一天的預測", ""]
    # 接法
    mp = M[(M["層"] == "大盤") & (M["判定"] == "通過")]; sp = M[(M["層"] == "個股") & (M["判定"] == "通過")]
    L += ["## 接法（登錄 §四：通過的高點 ⇒ 三態輪動「轉弱」、低點 ⇒「反彈」，第三層）", ""]
    L.append(f"- 大盤層通過 {len(mp)} 格" + ("：" + "、".join(f"{r.名}（{r.版}）" for r in mp.itertuples()) if len(mp) else " ⇒ 三態輪動第三層沒有可加的大盤訊號"))
    L.append(f"- 個股層通過 {len(sp)} 格" + ("：" + "、".join(f"{r.名}（{r.版}，{r.邊}點）" for r in sp.itertuples()) if len(sp) else "")
             + "；⚠ 三態輪動是 0050 層的輪動，個股層的通過要不要接、怎麼接 ⇒ 留給登錄方／裁定（本件不自己接）")
    pre = S.get("pre", {})
    L += ["", f"- 可判定格數（pre，⛔ 看報酬前）：{pre}；大盤層依構造不可判定的格都是事件太少（0050 主窗 9.5 年）", ""]
    # 結果句
    L += ["## 結果句（大盤層照登錄 §三查表）", ""]
    for code in CODES:
        for ver in ("原版", "確認版"):
            q = M[(M["層"] == "大盤") & (M["code"] == code) & (M["版"] == ver)]
            if not len(q):
                continue
            q = q.iloc[0]
            nm = NAME[code] + ("（加確認）" if ver == "確認版" else "")
            if q["判定"] == "通過":
                s = (f"0050 出現〔{nm}〕後 20 天比平常容易跌；成功率 {_r(q['成功率'])}（平常 {_r(q['基準成功率'])}）" if SIDE[code] == "高"
                     else f"0050 出現〔{nm}〕後 20 天比平常容易漲；成功率 {_r(q['成功率'])}（平常 {_r(q['基準成功率'])}）")
            elif q["判定"] == "不可判定":
                s = f"〔{nm}〕在大盤上事件太少（n_eff {int(q['n_eff'])} ＜ 10）⇒ 依構造不可判定"
            else:
                s = f"〔{nm}〕在大盤上看不出比隨便一天準（成功率 {_r(q['成功率'])}，平常 {_r(q['基準成功率'])}）"
            L.append(f"- {s}")
    L += [""]
    # 明細表
    for lay in ("大盤", "個股"):
        L += [f"## {lay}層 明細（主窗 2017-03-02～2026-08-24）", ""]
        if lay == "大盤":
            L += ["| 訊號 | 版 | 事件 | n_eff | 成功率／基準 | R20 平均／中位（基準） | R60 平均（基準） | 差 X | CI（Bonferroni） | 出口／結果 | 判定 | 假訊號過 | 沒確認比例／放棄組 R20 |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        else:
            L += ["| 訊號 | 版 | 事件 | n_eff | 成功率／基準①／基準② | R20 平均／中位 | 基準① ／② R20 | 差 X（對②） | CI（Bonferroni） | 出口／結果 | 判定 | 上市／上櫃 X | 沒確認比例／放棄組 R20 |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in M[M["層"] == lay].itertuples():
            ci_ = f"[{_p(r.lo)}, {_p(r.hi)}]" if hasattr(r, "lo") and np.isfinite(getattr(r, "lo", np.nan)) else "—"
            ab = f"{_r(getattr(r, '沒確認比例', np.nan))}／{_p(getattr(r, '放棄組R20平均', np.nan))}" if r.版 == "確認版" else "—"
            if lay == "大盤":
                L.append(f"| {r.名} | {r.版} | {r.事件} | {r.n_eff} | {_r(r.成功率)}／{_r(r.基準成功率)} | {_p(r.R20平均)}／{_p(r.R20中位)}（{_p(r.基準R20平均)}） | "
                         f"{_p(r.R60平均)}（{_p(r.基準R60平均)}） | {_p(r.mean)} | {ci_} | {r.出口}／{r.結果} | {r.判定} | "
                         f"{'—' if not np.isfinite(getattr(r, '假訊號過的比例', np.nan)) else f'{r.假訊號過的比例:.3f}'} | {ab} |")
            else:
                L.append(f"| {r.名} | {r.版} | {r.事件} | {r.n_eff} | {_r(r.成功率)}／{_r(r.基準1成功率)}／{_r(r.基準2成功率)} | {_p(r.R20平均)}／{_p(r.R20中位)} | "
                         f"{_p(r.基準1R20平均)}／{_p(r.基準2R20平均)} | {_p(r.mean)} | {ci_} | {r.出口}／{r.結果} | {r.判定} | {_p(r.X_twse)}／{_p(r.X_tpex)} | {ab} |")
        L += [""]
    E = C[C["段"] == "早年"]
    L += ["## 大盤早年段 2004-02-11～2016-12-30（描述、⛔ 不判）", "", "| 訊號 | 版 | 事件 | 成功率／基準 | R20 平均 | 差 X | R60 平均（基準） |", "|---|---|---|---|---|---|---|"]
    for r in E.itertuples():
        L.append(f"| {r.名} | {r.版} | {r.事件} | {_r(r.成功率)}／{_r(r.基準成功率)} | {_p(r.R20平均)} | {_p(r.mean)} | {_p(r.R60平均)}（{_p(r.基準R60平均)}） |")
    L += ["", f"大盤基準：主窗 {S.get('大盤基準_主窗')}；早年 {S.get('大盤基準_早年')}", "",
          "分年（依基準日年份的差 X）見 cells.csv 的 yYYYY 欄。", "",
          "## 閘門與資料", "", f"- 大盤：{S.get('閘_大盤')}", f"- 個股：{S.get('閘_個股')}", f"- 0050 早年資料：{S.get('大盤資料')}",
          f"- 個股基準股日：{S.get('個股基準')}", ""]
    open(os.path.join(OUT_, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
