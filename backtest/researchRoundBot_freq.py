# -*- coding: utf-8 -*-
"""PREREG圓弧底 seq1【頻率表・乾跑】（台股策略線 單筆層登錄 sha f2488c52d9e96535，2026-10-20 18:47；裁定 seq394 第 2 題、seq398 發號；
N_前段 ＋1；標籤上限「最多暫定」（主形狀已在型態全量 S22 測過））——回測線計算子代理。
⛔ 只數事件日期與個數、剔除計數、n_eff、曝險股日、條件成立比例、與已測項重疊；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、出場日
   （seq366 乾跑）。用到的價格只有 ≤ T 的日線開高低收量；T＋1 只判「有沒有成交、開盤是否鎖漲停」。
⛔ 不 commit、不改既有程式與結果夾；patterns_all（S22 偵測 detect_round、S28 平台 detect_platform）、patterns_x（W 底 detect_turn）、
   researchWR_freq、researchTripleBot_freq（本件姊妹檔：放量、長期下跌、剔除、重疊工具）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRoundBot_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRoundBot_freq_check
輸出 backtest/resultsRoundBot/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格（⭐ 判定只有 J；其餘只報、⛔ 不疊加）：
  M   主錨（描述）＝ 主要條件 ＝ PREREG型態全量 S22 圓形底（patterns_all.detect_round 原樣、參數唯一一組、⛔ 不調不掃）
  J   判定格 ＝ M ∧ 均線金叉（b 到 T 之間 MA5 由下往上穿 MA20）∧ 放量上攻（vr20 ≥ 1.5 ∧ T 收紅）∧ 長期下跌（b 收盤距 250 日最高 ≤ −20%）
  較嚴（各換掉 J 的一條、只報）：J_走平後金叉、J_金叉T前10日內、J_放量2倍、J_放量3倍、J_前5日均量1.5倍、J_跌30%、J_跌40%、J_120日線下>3月
  單條（只報）：M+金叉、M+放量、M+長期下跌
  量縮兩組（只報）：J_有量縮／J_沒量縮、M_有量縮／M_沒量縮（碗底 20 日均量 ＜ 左緣 20 日均量）

═══ 讀法（R 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 R1 世界、母體、壞根、500 張閘、剔除、20 日合併、段、n_eff ＝ 三重底件 researchTripleBot_freq T1、T3、T4、T9 原樣（import 同一批函式）；
    型態期間 ＝ [first, T]，first ＝ 左緣 a（登錄 §四「a～T 不跨壞根」）。
 R2 偵測輸入 ＝ 三重底件 T2 同一條；S22 ＝ PA.detect_round(c, r60)["S22"]（PatAll B8：a ＝ [T−250, T−60] 最高收盤、首次 c[T] ＞ c[a]、
    二次最小平方 γ＞0、R² ≥ 0.6、頂點在中間三分之一、b−a ≥ 20、T−b ≥ 20、r60[a] ＜ 0）；去重 ＝ detect_all 同式。
    碗底 b ＝ a + argmin(c[a..T−1])（detect_round 同式，平手取最早）。
 R3 均線（有效 K 棒、還原收盤）：MA_n[t] ＝ 含 t 的 n 根收盤平均，n 根需彼此相連（不跨壞根），否則缺值。
    金叉日 t ＝ MA5[t−1] ≤ MA20[t−1] ∧ MA5[t] ＞ MA20[t]（四值皆有；★ 兩者相差在 1e−9 × MA20 內視為相等＝浮點平手不算在上方
    〔對帳時發現：低波動股 MA5 與 MA20 數學上相等、浮點差 1e−15 會被算成穿越〕）；★「b 到 T 之間任一天」＝ t ∈ [b＋1, T]（b 當天穿越要用 b−1，不算）。
    ★ 走平後（台股策略線定 ±2%）＝ 該金叉日 |MA20[t−1] ÷ MA20[t−21] − 1| ≤ 2%（穿越前 20 根的 MA20 變動；兩值需有）；
    ★ 穿越在 T 前 10 日內 ＝ 有金叉日 t ∈ [T−9, T]（含 T、10 根有效 K 棒）。
    ⭐ seq377 等價自查：M 保留中「已有金叉」比例；≥ 95% ⇒ 金叉條件標【退化】、判定格等於不加（照報，⛔ 不改判定格定義）。
 R4 放量 ＝ 三重底件 T5 原樣（vr20、vr5、收紅）。
 R5 長期下跌 ＝ 三重底件 T6 原樣，基準點由 L1 換成 b：dd ＝ c[b] ÷ max(c[s..b]) − 1，s ＝ max(b − 249, b 所在無壞根段第一根)（段內 ＜ 60 根 ⇒ 不成立）；
    「b 前 120 日線下 ＞ 3 個月」＝ 截至 b（含）連續收盤 ＜ MA120 ＞ 63 根。
    ⭐ seq377 自查：M 保留中長期下跌成立比例（a 是 [T−250, T−60] 最高 ⇒ 碗深 ≥ 20% 時多半自動成立）；另報碗深 c[b] ÷ c[a] − 1 ≤ −20% 的比例。
 R6 量縮（只描述）★：碗底 20 日均量 ＝ mean(v[b−10..b＋9])、左緣 20 日均量 ＝ mean(v[a−10..a＋9])（以 b、a 為中心的 20 根有效 K 棒；
    皆 ≤ T−1 ⇒ 不前視）；任一窗有缺值或不足 ⇒ 歸「沒量縮」並另計缺值筆數。
 R7 重疊（件數 ÷ 本格保留數）：W 底（PX.detect_turn("w")）、C 組 K2（W 底 ∧ 左谷量 ＞ 右谷量）同日與 ±20 根；平台整理 ＝ PA.detect_platform
    （型態全量 S28 原樣）同日與 ±20 根；杯柄 ＝ 已提交 resultsPatC/freq K1 事件檔同日（任何狀態）；型態 B 組 B1／B2 同日（同三重底件 T8）。
 R8 S22 型態全量原標籤 ＝ 三重底件 T10 同式（resultsPatAll/body/cells.csv S22 列，⛔ 不搬報酬欄）。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WR                  # noqa: E402  （⛔ 只 import）
from backtest import researchTripleBot_freq as TB           # noqa: E402  姊妹檔工具（⛔ 只 import）
from backtest import patterns_all as PA                     # noqa: E402  S22、S28 偵測（⛔ 只 import）

REG_SHA = "f2488c52d9e96535"
OUT = "backtest/resultsRoundBot/freq"
VID = "S22"
FLAT = 0.02
EPS = 1e-9
CELLS = {
    "M": "主錨（描述）：主要條件＝型態全量 S22 圓形底",
    "J": "判定格：S22 ∧ b~T 間 MA5 上穿 MA20 ∧ 放量上攻(vr20≥1.5∧收紅) ∧ 長期下跌(b 距250日高≤−20%)",
    "J_走平後金叉": "較嚴（只報）：金叉改 穿越前20根 MA20 變動≤±2%",
    "J_金叉T前10日內": "較嚴（只報）：金叉改 穿越在 T 前 10 根內",
    "J_放量2倍": "較嚴（只報）：放量改 vr20≥2",
    "J_放量3倍": "較嚴（只報）：放量改 vr20≥3",
    "J_前5日均量": "較嚴（只報）：放量改 前5日均量版 vr5≥1.5",
    "J_跌30%": "較嚴（只報）：長期下跌改 ≤−30%",
    "J_跌40%": "較嚴（只報）：長期下跌改 ≤−40%",
    "J_120日線下>3月": "較嚴（只報）：長期下跌改 b 前連續收盤<MA120 >63根",
    "M+金叉": "單條（只報）：S22 ∧ 金叉",
    "M+放量": "單條（只報）：S22 ∧ 放量上攻",
    "M+長期下跌": "單條（只報）：S22 ∧ 長期下跌−20%",
    "J_有量縮": "量縮組（只報）：J ∧ 碗底20日均量<左緣20日均量",
    "J_沒量縮": "量縮組（只報）：J ∧ 非量縮",
    "M_有量縮": "量縮組（只報）：S22 ∧ 量縮",
    "M_沒量縮": "量縮組（只報）：S22 ∧ 非量縮",
}
_J = lambda f, x=None, vv=None, d=None: (f[x or "gx"] and f[vv or "vol15"] and f[d or "dd20"])
PRED = {
    "M": lambda f: True,
    "J": lambda f: _J(f),
    "J_走平後金叉": lambda f: _J(f, x="gx_flat"),
    "J_金叉T前10日內": lambda f: _J(f, x="gx_10"),
    "J_放量2倍": lambda f: _J(f, vv="vol2"),
    "J_放量3倍": lambda f: _J(f, vv="vol3"),
    "J_前5日均量": lambda f: _J(f, vv="vol5"),
    "J_跌30%": lambda f: _J(f, d="dd30"),
    "J_跌40%": lambda f: _J(f, d="dd40"),
    "J_120日線下>3月": lambda f: _J(f, d="below120"),
    "M+金叉": lambda f: f["gx"],
    "M+放量": lambda f: f["vol15"],
    "M+長期下跌": lambda f: f["dd20"],
    "J_有量縮": lambda f: _J(f) and f["shrink"],
    "J_沒量縮": lambda f: _J(f) and not f["shrink"],
    "M_有量縮": lambda f: f["shrink"],
    "M_沒量縮": lambda f: not f["shrink"],
}


def ma(c, bad, n):
    m = np.array(pd.Series(c).rolling(n, min_periods=n).mean().to_numpy(float), copy=True)
    m[~WR.clean_window(bad, n)] = np.nan
    return m


def cmean(v, bad, a, b):
    """v[a..b] 平均；需 a ≥ 0、b 在範圍內、相連、非缺值。"""
    if a < 0 or b >= len(v) or not TB._clean(bad, a, b):
        return np.nan
    w = v[a:b + 1]
    return float(w.mean()) if np.isfinite(w).all() else np.nan


def stock_job(a):
    wn, sid = a
    X = WR.base(wn, sid)
    if X is None:
        return sid, None
    df = X["df"]; idx = X["idx"]; nb = X["nb"]; bad = X["bad"]; o = X["o"]; c = X["c"]; h = X["h"]; l_ = X["l"]; cal = X["cal"]
    v = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
    cf = df["close"].to_numpy(float); bars = np.flatnonzero(np.isfinite(cf))
    bars_eq = bool(len(bars) == nb and (bars == idx).all())
    if not bars_eq:
        return sid, {"ev": {cell: [] for cell in CELLS}, "expo": X["expo"], "nb": nb, "bars_eq": False, "nS22": 0, "n_trunc": 0}
    cd = cf[bars]
    r60 = PA._rN(cd, PA.R60)
    ev, seen = [], set()
    for e in sorted(set(PA.detect_round(cd, r60)[VID])):
        if e[0] not in seen:
            seen.add(e[0]); ev.append(e)
    ss = TB.seg_start(bad)
    m5, m20 = ma(c, bad, 5), ma(c, bad, 20)
    gxd = np.zeros(nb, bool)
    with np.errstate(invalid="ignore"):
        tol = EPS * np.abs(m20)                                # R3：浮點平手（MA5 ＝ MA20 到 1e−9 相對）算「沒有在上方」
        gxd[1:] = np.isfinite(m5[:-1]) & np.isfinite(m20[:-1]) & np.isfinite(m5[1:]) & np.isfinite(m20[1:]) &             (m5[:-1] <= m20[:-1] + tol[:-1]) & (m5[1:] > m20[1:] + tol[1:])
    flat = np.zeros(nb, bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        flat[21:] = np.isfinite(m20[20:-1]) & np.isfinite(m20[:-21]) & (np.abs(m20[20:-1] / m20[:-21] - 1.0) <= FLAT)
    sets = TB.turn_sets(c, v)
    pf = np.array(sorted({e[0] for e in PA.detect_platform(h, l_, c)["S28"]}), np.int64)
    sets = {"W底": sets["W底"], "C組K2": sets["C組K2"], "平台整理S28": pf}
    feats = {}; n_trunc = 0
    for (Tb, ab) in ev:
        k = int(Tb); ka = int(ab)
        kb = ka + int(np.argmin(cd[ka:k]))
        gx_days = np.flatnonzero(gxd[kb + 1:k + 1]) + kb + 1
        vr20 = TB.vol_ratio(v, bad, k, 20); vr5 = TB.vol_ratio(v, bad, k, 5); red = bool(c[k] > o[k])
        dd, trunc = TB.longdown(c, ss, kb); n_trunc += int(trunc and np.isfinite(dd))
        b120 = TB.below_run(c, bad, kb)
        vb = cmean(v, bad, kb - 10, kb + 9); va = cmean(v, bad, ka - 10, ka + 9)
        sh_ok = np.isfinite(vb) and np.isfinite(va)
        f = {"kf": ka, "why0": None, "a": str(cal[idx[ka]].date()), "b": str(cal[idx[kb]].date()),
             "碗深": round(float(cd[kb] / cd[ka] - 1.0), 4), "金叉日數": int(len(gx_days)),
             "最後金叉": str(cal[idx[gx_days[-1]]].date()) if len(gx_days) else "",
             "gx": bool(len(gx_days)), "gx_flat": bool(flat[gx_days].any()) if len(gx_days) else False,
             "gx_10": bool((gx_days >= k - 9).any()) if len(gx_days) else False,
             "vr20": round(vr20, 4) if np.isfinite(vr20) else None, "vr5": round(vr5, 4) if np.isfinite(vr5) else None, "收紅": red,
             "dd250": round(dd, 4) if np.isfinite(dd) else None, "線下根數": int(b120),
             "vol15": bool(np.isfinite(vr20) and vr20 >= 1.5 and red), "vol2": bool(np.isfinite(vr20) and vr20 >= 2 and red),
             "vol3": bool(np.isfinite(vr20) and vr20 >= 3 and red), "vol5": bool(np.isfinite(vr5) and vr5 >= 1.5 and red),
             "dd20": bool(np.isfinite(dd) and dd <= -0.20), "dd30": bool(np.isfinite(dd) and dd <= -0.30),
             "dd40": bool(np.isfinite(dd) and dd <= -0.40), "below120": bool(b120 > 63),
             "shrink": bool(sh_ok and vb < va), "shrink缺值": bool(not sh_ok), **TB.ov_flags(k, sets)}
        feats[k] = f
    keys = ["a", "b", "碗深", "金叉日數", "最後金叉", "gx", "gx_flat", "gx_10", "vr20", "vr5", "收紅", "dd250", "線下根數", "vol15", "dd20",
            "shrink", "shrink缺值", *[z for z in next(iter(feats.values())).keys() if z.startswith(("同日_", "±"))]] if feats else []
    EV = TB.cells_from_feats(X, feats, CELLS, PRED, keys)
    return sid, {"ev": EV, "expo": X["expo"], "nb": nb, "bars_eq": True, "nS22": len(ev), "n_trunc": n_trunc}


def seg_extra(ok, p0, p1, cal):
    wn, sg = TB.wn_sg(cal, p0, p1)
    kp = {cell: [e for r in ok.values() for e in r["ev"][cell] if p0 <= e["T"] <= p1 and e["st"] == "保留"] for cell in ("M", "J")}
    M, J = kp["M"], kp["J"]
    nM = len(M)
    r = lambda x: round(x / nM, 4) if nM else None
    gx = sum(1 for e in M if e["gx"])
    out = {"seq377自查": {"M保留": nM, "已有金叉": gx, "已有金叉比例": r(gx),
                       "金叉退化(≥95%)": bool(nM and gx / nM >= 0.95),
                       "走平後金叉": sum(1 for e in M if e["gx_flat"]), "金叉T前10日內": sum(1 for e in M if e["gx_10"]),
                       "長期下跌−20%成立": sum(1 for e in M if e["dd20"]), "長期下跌比例": r(sum(1 for e in M if e["dd20"])),
                       "碗深≤−20%": sum(1 for e in M if e["碗深"] <= -0.20), "碗深≤−20%比例": r(sum(1 for e in M if e["碗深"] <= -0.20)),
                       "放量1.5倍收紅成立": sum(1 for e in M if e["vol15"]), "放量比例": r(sum(1 for e in M if e["vol15"])),
                       "J÷M": r(len(J))},
           "量縮缺值筆數(M保留)": sum(1 for e in M if e["shrink缺值"]),
           "重疊_J": TB.overlap_block(J, cal, wn, sg, ("W底", "C組K2", "平台整理S28")),
           "重疊_M": TB.overlap_block(M, cal, wn, sg, ("W底", "C組K2", "平台整理S28"))}
    return out


def diag(ok):
    return {"有效K棒": int(sum(r["nb"] for r in ok.values())), "偵測K棒≠load_bars K棒檔數": int(sum(1 for r in ok.values() if not r["bars_eq"])),
            "S22偵測總數(全期)": int(sum(r["nS22"] for r in ok.values())),
            "長期下跌250日窗被壞根或上市截短(全期偵測)": int(sum(r["n_trunc"] for r in ok.values()))}


def main():
    WR.run_freq({"sha": REG_SHA, "out": OUT, "cells": CELLS, "job": stock_job, "ev_cells": tuple(CELLS),
                 "title": "PREREG圓弧底 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
                 "ruling": "seq394 第 2 題、seq398 發號；N_前段 ＋1；標籤最多暫定；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N；乾跑",
                 "doc": __doc__, "seg_extra": seg_extra, "diag": diag, "st_all": TB.ST_PAT})
    lim = "--limit" in sys.argv
    TB.finalize(OUT if not lim else os.path.join(OUT, "_try"), VID, "J", "M")


if __name__ == "__main__":
    main()
