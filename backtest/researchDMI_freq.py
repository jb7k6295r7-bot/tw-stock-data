# -*- coding: utf-8 -*-
"""DMI 交叉＋極點進場（＋SAR 出場）seq1【頻率表・乾跑】（台股策略線 單筆層登錄 sha 7329d0b51c85b40c，2026-10-18 11:08；裁定 seq371 §二、
seq372 發號；N_前段 ＋1）——回測線計算子代理。
⛔ 只數交叉、事件日期與個數、剔除計數、n_eff、曝險股日；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、出場日（裁定 seq366、372：乾跑）。
   用到的價格只有 ≤ T 的日高低收（T 日最高只用來判觸價）；T 開盤只用來判「開盤鎖漲停全日鎖死」。SAR（含起點）只在出場用 ⇒ ⛔ 本表不算。
⛔ 不 commit、不改既有程式與結果夾；researchTurtle_freq（Wilder 實作）／researchWR_freq（共用驅動）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDMI_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDMI_freq_check
輸出 backtest/resultsDMI/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格：
  E        判定格：交叉日 c（+DI 上穿 −DI）之後 20 根內、開盤前 +DI 仍 ＞ −DI，當日最高 ＞ c 日最高 ⇒ 當日觸價買（T ＝ 進場日）
  D1_ADXR  描述 D1：E ∧ ADXR(14)[T−1] ＞ 25
  D2_收盤  描述 D2（收盤判版）：同一交叉、收盤 ＞ c 日最高 ⇒ T＋1 開盤買
  （對照隨機 20 檔、SAR 出場、勝率、賺賠比、平均持有天數要進場後價格 ⇒ ⛔ 不在頻率表）

═══ 讀法（M 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 M1 世界、母體、壞根、T 的母體閘、段、n_eff、每年／每檔每年 ＝ researchWR_freq R1、R2、R10 原樣（同一支 base／run_freq）。
    E 的 T ＝ 突破（進場）當天，母體閘用「T 前一日 20 日均量」（海龜 T1 同）；D2 的 T ＝ 收盤判定日（進場 T＋1）。
 M2 +DI(14)、−DI(14)、ADX ＝ researchTurtle_freq.adx_wilder 那一份 Wilder 原式（⛔ 不另寫）：以 inspect 取其原始碼、只插入「把當根 pdi／mdi
    存進陣列」兩處與回傳值（DMI_SRC_PATCH，逐字列在下方），exec 成 dmi_wilder ⇒ ADX、段齡與原函式逐位相同（check 逐檔驗）。
    不跨壞根：同海龜 T6（每個無壞 K 棒段從頭起算；DI 在段內第 14 根起有值）。TR14 ＝ 0 ⇒ DI 缺值。
 M3 ★ ADXR(14)[k] ＝（ADX[k] ＋ ADX[k−14]）÷ 2，兩者有值且同段（段齡[k] ≥ 14）〔另一讀法 k−13——不採〕；D1 濾網時點 ★ ＝ T−1（T 開盤前已知；海龜 T6 同）；
    濾網 ＝ ADXR ＞ 25（嚴格）；缺值 ⇒ 不過。
 M4 交叉日 c：DI[c−1]、DI[c] 都有值（⇒ 同段）∧ +DI[c−1] ≤ −DI[c−1] ∧ +DI[c] ＞ −DI[c]；c 當天 ⛔ 不進場。
 M5 E：依序看 t ＝ c＋1 … c＋20（有效 K 棒）：★ t 是壞 K 棒 ⇒ 交叉作廢（不跨壞根）；+DI[t−1] ≤ −DI[t−1] 或缺值 ⇒ 交叉作廢（登錄「期間 +DI 先跌回」、
    「開盤前 +DI 仍 ＞ −DI」）；h[t] ＞ h[c]（嚴格）⇒ 事件 T ＝ t（成交價 max(開, h[c]) 屬報酬段、本表不用）；同一交叉只進一次。
    同一時間只會有一個未作廢的交叉（新交叉必先有 +DI ≤ −DI ⇒ 舊交叉已作廢）。
 M6 E 剔除（海龜 T4 同）：閘外(500張/pit) → 壞根(T)（M5 已排除）→ T開盤缺值 → T開盤鎖漲停（快取 upl）。★ 開盤漲停但盤中打開 ⇒ 買得到、算事件。
 M7 D2：同 M4、M5 的交叉與作廢規則（★ 有效性一樣看 DI[t−1]，與 E 同口徑以便並報），觸發改 c[t] ＞ h[c] ⇒ T ＝ t，T＋1 開盤買；
    剔除 ＝ researchWR_freq R7（閘外 → 壞根(T) → 壞根(T+1) → T+1無成交 → T+1開盤鎖漲停）。
 M8 「同一檔持有中不重複進場」要出場日（SAR 翻轉 ⇒ 進場後價格）⇒ 頻率表 ⛔ 不套；本表事件數 ＝ 上限（每個交叉至多一筆）。
 M9 必報「交叉數、進場率」：交叉數 ＝ c 落在段內的交叉（不看母體閘）；另報 c 日在母體內的交叉數；
    進場率 ＝ 段內交叉中 20 根內有觸發（偵測，剔除前）的比例；另報「保留事件 ÷ 段內交叉數」。D2 同報。
"""
from __future__ import annotations

import inspect
import os
import sys

import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WF                  # noqa: E402  共用 base／st_*／run_freq（⛔ 只 import）
from backtest import researchTurtle_freq as RT              # noqa: E402  adx_wilder（⛔ 只 import，不另寫）

REG_SHA = "7329d0b51c85b40c"
OUT = "backtest/resultsDMI/freq"
WIN = 20
ADXR_LAG = 14
ADXR_TH = 25.0
WARM = 150
CELLS = {"E": "判定格：+DI 上穿 −DI 後 20 根內、開盤前 +DI 仍＞−DI，盤中最高＞交叉日最高（觸價當日買）",
         "D1_ADXR": "描述 D1：E 且 ADXR(14)[T−1]＞25",
         "D2_收盤": "描述 D2：同交叉，收盤＞交叉日最高，T+1 開盤買"}

# ═════════════ M2 DI：由 researchTurtle_freq.adx_wilder 原始碼插入紀錄點 ═════════════
DMI_SRC_PATCH = [
    ("def adx_wilder(", "def dmi_wilder("),
    ("A = np.full(N, np.nan); age = np.zeros(N, np.int64)",
     "A = np.full(N, np.nan); age = np.zeros(N, np.int64); PDI = np.full(N, np.nan); MDI = np.full(N, np.nan)"),
    ("pdi = 100.0 * pdm / trs; mdi = 100.0 * mdm / trs",
     "pdi = 100.0 * pdm / trs; mdi = 100.0 * mdm / trs; PDI[k] = pdi; MDI[k] = mdi"),
    ("return A, age", "return A, age, PDI, MDI"),
]


def _build_dmi():
    src = inspect.getsource(RT.adx_wilder)
    for a, b in DMI_SRC_PATCH:
        if src.count(a) != 1:
            raise SystemExit(f"⛔ researchTurtle_freq.adx_wilder 原始碼找不到唯一一處「{a}」⇒ 不 patch")
        src = src.replace(a, b)
    ns = dict(RT.__dict__)
    exec(compile(src, "<dmi_wilder from researchTurtle_freq.adx_wilder>", "exec"), ns)
    return ns["dmi_wilder"], src


dmi_wilder, DMI_SRC = _build_dmi()


def adxr(ADX, AGE, lag=ADXR_LAG):
    N = len(ADX); out = np.full(N, np.nan)
    k = np.arange(lag, N)
    ok = (AGE[k] >= lag) & np.isfinite(ADX[k]) & np.isfinite(ADX[k - lag])
    out[k[ok]] = (ADX[k[ok]] + ADX[k[ok] - lag]) / 2.0
    return out


def crosses(PDI, MDI):
    k = np.arange(1, len(PDI))
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(PDI[k - 1]) & np.isfinite(MDI[k - 1]) & np.isfinite(PDI[k]) & np.isfinite(MDI[k]) & \
             (PDI[k - 1] <= MDI[k - 1]) & (PDI[k] > MDI[k])
    return [int(x) for x in k[ok]]


def entry(cx, h, c, PDI, MDI, bad, close_confirm=False):
    """M5／M7：回 t 或 None。⛔ 判 t 只用 ≤ t 的資料（DI 用到 t−1；觸發用 h[t] 或 c[t]）。"""
    n = len(h)
    for t in range(cx + 1, min(cx + WIN, n - 1) + 1):
        if bad[t]:
            return None
        if not (np.isfinite(PDI[t - 1]) and np.isfinite(MDI[t - 1]) and PDI[t - 1] > MDI[t - 1]):
            return None
        x = c[t] if close_confirm else h[t]
        if x > h[cx]:
            return t
    return None


def stock_job(a):
    wn, sid = a
    X = WF.base(wn, sid)
    if X is None:
        return sid, None
    h, l, c, bad, idx, gate, PV = X["h"], X["l"], X["c"], X["bad"], X["idx"], X["gate"], X["PV"]
    ADX, AGE, PDI, MDI = dmi_wilder(h, l, c, bad)
    AR = adxr(ADX, AGE)
    cx = crosses(PDI, MDI)
    EV = {"E": [], "D2_收盤": [], "_交叉": []}
    for x in cx:
        tE = entry(x, h, c, PDI, MDI, bad, False)
        tD = entry(x, h, c, PDI, MDI, bad, True)
        EV["_交叉"].append({"sid": sid, "T": int(idx[x]), "k": x, "閘內": bool(gate[idx[x]] and PV[idx[x]]),
                           "E觸發": tE is not None, "D2觸發": tD is not None, "st": "交叉"})
        for cell, t, fn in (("E", tE, WF.st_same_day), ("D2_收盤", tD, WF.st_next_open)):
            if t is None:
                continue
            ka = t - 1
            EV[cell].append({"sid": sid, "T": int(idx[t]), "k": t, "c日": int(idx[x]), "距交叉": int(t - x), "c日最高": float(h[x]),
                             ("最高" if cell == "E" else "收盤"): float(h[t] if cell == "E" else c[t]),
                             "+DI[T-1]": float(PDI[ka]), "-DI[T-1]": float(MDI[ka]), "ADXR[T-1]": float(AR[ka]),
                             "DI段齡[T-1]": int(AGE[ka]), "ADXR>25": bool(np.isfinite(AR[ka]) and AR[ka] > ADXR_TH), "st": fn(X, t)})
    EV["D1_ADXR"] = [e for e in EV["E"] if e["ADXR>25"]]
    return sid, {"ev": EV, "expo": X["expo"], "nb": X["nb"], "ndi": int(np.isfinite(PDI).sum()), "nx": len(cx)}


def seg_extra(ok, p0, p1, cal):
    X = [e for r in ok.values() for e in r["ev"]["_交叉"] if p0 <= e["T"] <= p1]
    nE = sum(1 for e in X if e["E觸發"]); nD = sum(1 for e in X if e["D2觸發"])
    keptE = sum(1 for r in ok.values() for e in r["ev"]["E"] if p0 <= e["T"] <= p1 and e["st"] == "保留")
    keptD = sum(1 for r in ok.values() for e in r["ev"]["D2_收盤"] if p0 <= e["T"] <= p1 and e["st"] == "保留")
    young = sum(1 for r in ok.values() for e in r["ev"]["E"] if p0 <= e["T"] <= p1 and e["st"] == "保留" and e["DI段齡[T-1]"] < WARM)
    return {"交叉數(c在段內)": len(X), "交叉數(c日在母體內)": int(sum(1 for e in X if e["閘內"])),
            "E有觸發交叉": nE, "E進場率(偵測÷交叉)": round(nE / len(X), 4) if X else None,
            "E保留÷交叉": round(keptE / len(X), 4) if X else None,
            "D2有觸發交叉": nD, "D2進場率(偵測÷交叉)": round(nD / len(X), 4) if X else None,
            "D2保留÷交叉": round(keptD / len(X), 4) if X else None,
            "E保留中DI段齡<150": young}


def main():
    WF.run_freq({"sha": REG_SHA, "out": OUT, "cells": CELLS, "job": stock_job, "ev_cells": ("E", "D2_收盤"),
                 "title": "DMI 交叉＋極點進場 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
                 "ruling": "seq371 §二、seq372 發號；N_前段 ＋1；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N；乾跑",
                 "doc": __doc__ + "\n DMI_SRC（exec 後的原始碼）：\n" + DMI_SRC, "seg_extra": seg_extra,
                 "diag": lambda ok: {"有效K棒": int(sum(r["nb"] for r in ok.values())), "DI有值K棒": int(sum(r["ndi"] for r in ok.values())),
                                     "交叉總數": int(sum(r["nx"] for r in ok.values()))}})


if __name__ == "__main__":
    main()
