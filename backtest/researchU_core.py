# -*- coding: utf-8 -*-
"""PREREGU 共用的【讀檔＋偵測＋事件狀態】（⛔ 本支不讀 T 以後的任何收盤、不算任何報酬或反彈判定）。
判準＝台股策略線 PREREGU seq1（sha 4ff4c1731fdded12）。頻率（researchU_freq.py）與本體（researchU.py）都 import 本支，
⇒ 兩邊的事件集合是同一套函式算出來的；本體開算前另與頻率交出的事件檔逐列比。

資料、母體、讀檔、硬斷點：與 PREREGH1／H2／M 同一份快照與同一套函式（import researchH2：main edc6f8002f、gate3、H2.brk；
   delist on 的缺日處理同 researchM_freq Q5：下市者最後成交之後的缺日不算「連續缺 5 日」）。
偵測器：backtest/fib_u.py（fixture：backtest/selftest_fib_u.py，⭐ 開跑前先全跑、任一條不過即中止）。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何頻率之前寫在這裡；交件逐條列出；偵測器本身的讀法 U1～U6 見 fib_u.py）：
 V1 判定窗：沿用 PREREGH1／H2／M 同一窗 [2017-03-02, 2026-08-24]（2,313 個交易日；登錄沒寫窗 ⇒ 同骨架件同一窗）；
    事件須 T ∈ [窗起點, 窗尾 − H]（H＝20 ⇒ T+20 ≤ 窗尾）。波段偵測用全期歷史（只用到 T 以前）。
 V2 事件處理順序（同 PREREGM Q2）：同檔、同位置、依 T 走 ⇒ T 落在「上一個被保留事件 t0」的 (t0, t0+20]（交易日曆）⇒ 合併掉；
    否則 [T, T+H] 有硬斷點 ⇒ 剔除；否則保留。被剔除者 ⛔ 不開合併窗。合併是【跨波段】的（同檔同位置，不論屬哪個波段）。
    ⛔ 判定量只看收盤、不成交 ⇒ 本件主格【不】剔除 T+1 停牌／開盤漲停（那只在描述臂 d 交易版剔除、另報）。
 V3 硬斷點（同 H2 R3＋M Q5）：① 相鄰有效 K 棒 close 比 ≤ 0.55 或 ≥ 1.8 且其間無 data/adj 事件，斷點日落在 [T, T+H]；
    ② [T, T+H] 內連續 ≥ 5 個交易日無有效 K 棒（5 個缺日全在範圍內）；delist on：下市者最後成交之後的缺日不算。
    另報（不剔除）：波段內部 [t_L, T) 有硬斷點的保留事件數（登錄只要求觀察窗不跨斷點）。
 V4 描述臂 b 的 10 日／40 日窗：觀察窗與「T+H ≤ 窗尾」「[T, T+H] 無斷點」跟著改；合併仍是 20 日（登錄的合併規則是獨立一條）。
 V5 20 日區段：從窗起點以交易日曆每 20 日切一段，區段號 ＝ min((T − 窗起點)//20, 114)（同 PREREGM：上限 115）。
"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                            # ⭐ 同一份快照、同一套讀檔／斷點（D.DATA 已被指到快照）
D, TR, UG = H2.D, H2.TR, H2.UG
import researchM_freq as RF                        # 只 import _g5（delist on 的連續缺日）
from backtest import fib_u as FU

W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
MERGE, BLOCK, CAP = 20, 20, 115
# (k, H)：主格 (5, 20)；描述臂 c：k＝3、10；描述臂 b：10 日、40 日窗
CFGS = [(5, 20), (3, 20), (10, 20), (5, 10), (5, 40)]


def cfg_name(k, H):
    return "k{}_H{}".format(k, H)


def load(sid, market, cal, off):
    """讀一檔（還原 OHLC、日曆對齊）＋斷點累計＋可成交旗標；回 S dict 或 None。"""
    n = len(cal)
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
    ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5_lit = RF._g5(valid)
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else g5_lit
    return {"sid": sid, "market": market, "o": o, "h": h, "l": l, "c": c, "valid": valid, "bars": bars,
            "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32),
            "cs_g5_lit": np.cumsum(g5_lit).astype(np.int32),
            "trd": tb["trd"], "up_o": tb["up_o"], "delisted": bool(delisted), "last": (ds["last"] if ds else None),
            "status": (ds["status"] if ds else None),
            "nan_low": int(np.sum(valid & ~np.isfinite(l))), "nan_high": int(np.sum(valid & ~np.isfinite(h)))}


def brk(S, a, b, lit=False):
    SS = {"cs_pb": S["cs_pb"], "cs_g5": S["cs_g5_lit"] if lit else S["cs_g5"]}
    return H2.brk(SS, a, b)


def assign(S, r, w0, w1, H):
    """V1～V3：偵測結果 r（fib_u.detect_calendar）⇒ 每個窗內觸及的狀態列。只用 [t_L, T+H] 的斷點旗標，⛔ 不讀 T 以後的價格。"""
    W = r["waves"]; wLast = w1 - H
    tc = [t for t in r["touches"] if t["state"] == "觸及" and w0 <= t["T"] <= wLast]
    rows = []
    for pos in FU.POS:
        ev = sorted((t for t in tc if t["pos"] == pos), key=lambda t: t["T"])
        t_keep = -10 ** 9
        for t in ev:
            T = t["T"]; w = W[t["wave"]]
            f_brk = brk(S, T, T + H)
            if t_keep < T <= t_keep + MERGE:
                stt = "合併掉"
            elif f_brk:
                stt = "剔除_硬斷點"
            else:
                stt = "保留"; t_keep = T
            rows.append({"pos": pos, "T": int(T), "p": float(t["p"]), "wave": int(t["wave"]), "tL": int(w["tL"]), "tH": int(w["tH"]),
                         "conf": int(w["conf"]), "L0": float(w["L0"]), "H0": float(w["H0"]), "狀態": stt,
                         "f_brk_lit": bool(brk(S, T, T + H, lit=True)),
                         "f_dl_in": bool(S["delisted"] and S["last"] < T + H),
                         "f_brk_wave": bool(brk(S, int(w["tL"]), T - 1))})
    rows.sort(key=lambda x: (x["T"], x["pos"]))
    return rows


def detect_all(S, cal, w0, w1, cfgs=CFGS):
    """每個 (k, H) ⇒ 偵測＋狀態；k 相同的只偵測一次。"""
    det, out = {}, {}
    for k, H in cfgs:
        if k not in det:
            det[k] = FU.detect_calendar(S["h"], S["l"], S["c"], k)
        out[(k, H)] = {"rows": assign(S, det[k], w0, w1, H)}
    return det, out


def win_index(cal):
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS, (cal[w0], cal[w1])
    return w0, w1
