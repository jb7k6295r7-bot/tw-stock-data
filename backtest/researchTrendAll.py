# -*- coding: utf-8 -*-
"""PREREG個股趨勢全多 seq3（台股策略線登錄 sha ad7617478ca8b71b，2026-10-10 23:18；裁定 seq323 發號 N_組合 ＋1、seq324 母體更正；
事後重切 ⇒ 最多暫定、只進前瞻紀錄）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTrendAll run [--procs 2] [--reps 200] [--fake 200]
    ...                                                      -m backtest.researchTrendAll page
    抽樣查核（獨立寫法）：... -m backtest.researchTrendAll_check

⭐ 讀法寫死時間：2026-10-10 23:41（台北）；寫死前 ⛔ 沒算任何本件數字。共同讀法 ＝ backtest/researchPRE5core.py 檔頭（C1～C15）。

═══ 本件讀法（T 標）═══
 T1 檢查日 t ＝ 每月第一個交易日（本版面日曆）；決策 ＝ t 收盤；進場 e ＝ t＋1 開盤（登錄「t+1 開盤買」）；母體 ＝ C3 在 d＝t（5,000 萬＋四碼，⭐ seq324：不排金融、生技）
 T2「多」（MA20、MA60、MA240，還原收盤）：在該股有效 K 棒序列上 收盤 ＞ MA_L 且 MA_L ＞ 5 根前的 MA_L；MA 要滿 L 根（不足 ⇒ 不多）；t 當天沒 K 棒 ⇒ 不是候選
    全多 ＝ 三條都多；全空 ＝ 三條都不多
 T3 候選 ＝ 母體 ∧ 全多；選法抽籤（單一選法）；空位才買（引擎）；同一檔已持有不重買
 T4 出場：之後每個檢查日 t′（＞ 進場那次的 t）：D1 ＝ 不再全多 ⇒ t′＋1 開盤賣；D2 ＝ 全空 ⇒ t′＋1 開盤賣（中間狀態續抱）；⛔ 不設最長天數
    t′ 當天該股沒 K 棒（停牌）⇒ 該月判不出、續抱（次數照報）
 T5 早年段：只用價量 ⇒ 用日線判（裁定 seq323）：early 版面 2005-02-01～2014-12-30（MA240 暖機；上櫃 2007-07 起才有日 K，照報）
 T6 件專屬描述：每月全多檔數（母體內）、出場時的狀態
輸出 backtest/resultsTrendAll/；網頁 backtest/個股趨勢全多_回測.html
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchPRE5core as C   # noqa: E402


class TrendAll:
    NAME = "PREREG個股趨勢全多 seq3"
    KEY = "TrendAll"
    REG_SHA = "ad7617478ca8b71b"
    TIME = "2026-10-10 23:41（台北）"
    OUT = os.path.expanduser("~/tw-p17/backtest/resultsTrendAll")
    PAGE = os.path.expanduser("~/tw-p17/backtest/個股趨勢全多_回測.html")
    cells = ["D1", "D2"]
    PICK = {"D1": False, "D2": False}
    excl_fb = False
    early_ok = True
    early_note = ""
    meta_extra = {"件說明": "每月初買收盤在 20／60／240 日線上、三條線都上彎（全多）的股票；D1 不再全多才賣、D2 全空才賣"}
    LONG = "全多組 +0.60%"

    def result_sentence(self):
        return "做多那一腿對母體只有 全多組 +0.60%，扣一趟成本 0.585% 後只剩約 0～0.2%；基準是 5,000 萬等權母體、不是 0050。"

    def notes(self):
        return ["每月第一個交易日收盤判「全多」（MA20／60／240 都：收盤在線上、線比 5 根前高；有效 K 棒序列、還原價），次一交易日開盤買；母體 5,000 萬＋四碼、不排金融生技（seq324）。",
                "D1 不再全多才賣、D2 全空才賣（次月初判、再隔一日開盤賣）；⛔ 不設最長天數；判斷日停牌 ⇒ 該月續抱。",
                "早年段用日線判（seq323）：early 版面 2005-02～2014-12（上櫃 2007-07 起才有日 K）。",
                "事後重切（情報 #14 已看過）⇒ 就算兩段都合格也最多「暫定」、只進前瞻紀錄。",
                "現實版 ＝ 每邊 ＋0.3%、50 萬平方根衝擊、一字漲跌停、均價成交。"]

    def dec_days(self, W):
        d = W.month_first_days()
        return d[d < W.n - 1]

    def rebal_days(self, W):
        return self.dec_days(W) + 1

    def universe(self, W, log):
        return W.UNI.copy()

    def _state(self, W):
        k = ("trend",)
        if k not in W.ind_cache:
            u = [W.ma_up(L) for L in (20, 60, 240)]
            W.ind_cache[k] = (u[0] & u[1] & u[2], ~u[0] & ~u[1] & ~u[2] & W.BAR)
        return W.ind_cache[k]

    def build(self, W, U, log):
        ALL, NONE = self._state(W)
        td = self.dec_days(W)
        out = {"D1": [], "D2": []}
        skip = 0
        for s in range(W.S):
            bar_t = W.BAR[s, td]; all_t = ALL[s, td]; none_t = NONE[s, td]
            cand = np.flatnonzero(U[s, td] & all_t)
            if not len(cand):
                continue
            ex1 = np.flatnonzero(bar_t & ~all_t); ex2 = np.flatnonzero(bar_t & none_t)
            for j in cand:
                for cell, ex in (("D1", ex1), ("D2", ex2)):
                    k = int(np.searchsorted(ex, j + 1))
                    x = int(td[ex[k]]) + 1 if k < len(ex) else -1
                    why = ("不再全多" if cell == "D1" else "全空") if x > 0 else "未完"
                    out[cell].append((s, int(td[j]) + 1, "open", x, why, np.nan))
        R = {c: pd.DataFrame(v, columns=["s", "e", "xk", "x", "why", "key"]) for c, v in out.items()}
        return R

    def early_window(self, W, log):
        return C.EARLY

    def extra_desc(self, W, U, chosen, log):
        return {}

    def extra_stats(self, W, U, FB, RES, chosen, seg, log):
        ALL, NONE = self._state(W)
        td = self.dec_days(W)
        a, b = seg["主窗"]
        tt = td[(td + 1 >= a) & (td + 1 <= b)]
        n_all = [int((U[:, t] & ALL[:, t]).sum()) for t in tt]
        n_uni = [int(U[:, t].sum()) for t in tt]
        n_none = [int((U[:, t] & NONE[:, t]).sum()) for t in tt]
        return {"每月全多檔數（母體內）": C.q_(n_all), "每月全空檔數（母體內）": C.q_(n_none), "每月母體檔數": C.q_(n_uni),
                "全多占母體（月平均）": float(np.mean(np.array(n_all) / np.maximum(np.array(n_uni), 1)))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="run")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.cmd == "run":
        C.run_study(TrendAll(), a)
    elif a.cmd == "page":
        from backtest import researchPRE5page as PG
        PG.page(TrendAll())


if __name__ == "__main__":
    main()
