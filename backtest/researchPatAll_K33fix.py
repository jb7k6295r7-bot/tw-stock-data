# -*- coding: utf-8 -*-
"""PREREG型態全量 #33 多頭母子十字 第一根顏色更正（裁定 seq298 §三；型態線 2026-10-04 20:40 訂正）——回測線。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatAll_K33fix [--procs 2]

⭐ 查到的事實（讀法寫死前先查，2026-10-04 21:1x 台北）：
   patterns_all._kcond 第 33 號 ＝ wh(1) & lng(1) & dj(2) & (H(2) ≤ H(1)) & (L(2) ≥ L(1)) ⇒ 第一根用的是【白K】（照型態線舊筆記）
   型態線訂正（Bulkowski 原文 "a tall black candle followed by a doji"）⇒ 多頭母子十字第一根應為【黑K】
   ⇒ 照裁定 seq298 §三「屬定義錯誤更正：該格照正確定義重跑一次，新結果取代、舊結果入沿革；批 N（180）不變」
   第 52 號空頭母子十字 ＝ wh(1)…（第一根白K）＝ 訂正後仍正確 ⇒ 不動
⭐ 做法（⛔ 不改 patterns_all.py／researchPatAll*.py；只在本行程把第 33 號換成黑K）：
   ① 頻率階段 researchPatAll_freq.main 原樣重跑、輸出到 resultsPatAll_K33fix/freq（96 變體全跑；其餘 95 個事件檔應與已提交逐檔相同 ⇒ 驗）
   ② 本體 researchPatAll.main 原樣重跑、FREQ 指到 ①、OUT ＝ resultsPatAll_K33fix/body（查核1、fixture、十分位、假訊號臂 30 次照原樣；
      其餘 95 變體各格應與已提交 cells.csv 逐欄相同 ⇒ 驗；族結論 a／b、假訊號臂 30 次全族計數隨 K33 兩格更新）
   ③ 讀法、種子、判定式一字不改；d（−1，登錄方向表）不改（裁定只更正顏色）
輸出 backtest/resultsPatAll_K33fix/（freq/、body/、K33_CHANGE.md、compare.json）
"""
from __future__ import annotations
import gzip, hashlib, json, os, sys, glob
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchPatAll_freq as RPF
import researchPatAll as RPA
PA = RPF.PA

BASE = "backtest/resultsPatAll_K33fix"
_orig = PA._kcond


def _kcond_fix(num, g, Bm, Rm):
    if num != 33:
        return _orig(num, g, Bm, Rm)
    lng = g("B", 1) >= PA.LONG * Bm
    return g("bk", 1) & lng & g("doji", 2) & (g("H", 2) <= g("H", 1)) & (g("L", 2) >= g("L", 1))      # ⭐ 第一根黑K（訂正）


def md5gz(p):
    with gzip.open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    PA._kcond = _kcond_fix
    os.makedirs(BASE, exist_ok=True)
    fq = os.path.join(BASE, "freq")
    RPF.OUT = fq
    if not os.path.exists(os.path.join(fq, "freq.csv")):
        RPF.main()
    # ① 其餘 95 個事件檔逐檔相同
    cmp = {}
    for p in sorted(glob.glob("backtest/resultsPatAll/events_*.csv.gz")):
        q = os.path.join(fq, os.path.basename(p))
        cmp[os.path.basename(p)] = md5gz(p) == md5gz(q)
    diff = [k for k, v in cmp.items() if not v]
    print("[① 事件檔] 不同：", diff, flush=True)
    assert diff == ["events_K33_多頭母子十字.csv.gz"], diff
    F0 = pd.read_csv("backtest/resultsPatAll/freq.csv", encoding="utf-8-sig", dtype={"vid": str}).set_index("vid")
    F1 = pd.read_csv(os.path.join(fq, "freq.csv"), encoding="utf-8-sig", dtype={"vid": str}).set_index("vid")
    print("[① freq K33] 舊", F0.loc["K33"].to_dict(), "\n           新", F1.loc["K33"].to_dict(), flush=True)
    # ② 本體
    RPA.FREQ = fq
    RPA.OUT = os.path.join(BASE, "body")
    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:]]
    RPA.main()


if __name__ == "__main__":
    main()
