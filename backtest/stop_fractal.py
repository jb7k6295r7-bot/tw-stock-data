# -*- coding: utf-8 -*-
"""PREREGD5 的停損線（研究腳本層；⛔ 不是共用引擎）——在裁定線裁引擎兩處之前先備好、先驗 fixture ①③。

定義（台股策略線 PREREGD5 seq1 §一，逐字要點）：
  擺動低點：第 s 根還原低點嚴格低於左右各 k 根（k＝2，5 根碎形）；右邊 k 根走完才確認 ⇒ 第 s 根的低點在 s+k 收盤才可用
  初始停損：進場根 e 以前（含 e）最近一個【已確認】擺動低點（確認根 ≤ e，且 s ≥ e−LOOKBACK）的還原低點
     找不到 ⇒ 進場價 − 3 × ATR（research11.wilder_atr，n＝14，只用 e 以前 ⇒ 取 e−1 的 ATR）；e 以前有效 K 棒 < 114 根 ⇒ 無停損
  棘輪：持有期間每出現一個新確認的擺動低點且高於現行停損 ⇒ 上移；⛔ 只進不退
  觸發：還原收盤 < 停損 ⇒ T+1 開盤出場（出場由引擎做；本支只給每一根的停損線）
一律在【該股有效 K 棒序列】上數（左右 k 根、回看 120 根、ATR 都是 K 棒數）。

⭐ 本線提給裁定線的引擎改法（最小）：引擎只加一個通用參數「每個部位一條事先算好的停損線 ＋ 收盤跌破 ⇒ 次一可交易日開盤出」，
   碎形／棘輪／ATR 全在本支；⇒ 共用引擎不認識「碎形」，日後換停損定義不必再動引擎。
"""
from __future__ import annotations
import os, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import research11 as R          # ⭐ ATR 用共用那一份（同一件事只准一份實作）

K_SIDE, LOOKBACK, ATR_N, ATR_MULT, MIN_BARS = 2, 120, 14, 3.0, 114


def swing_lows(low: np.ndarray, k: int = K_SIDE) -> np.ndarray:
    """回傳布林：第 s 根是否為擺動低點（嚴格低於左右各 k 根）。⚠ 用到 s+k ⇒ 呼叫端只能在 s+k 以後使用。"""
    n = len(low); out = np.zeros(n, bool)
    for s in range(k, n - k):
        v = low[s]
        if np.all(v < low[s - k:s]) and np.all(v < low[s + 1:s + k + 1]):
            out[s] = True
    return out


def stop_line(o, h, l, c, e, x, k=K_SIDE, lookback=LOOKBACK, lag=None):
    """部位從第 e 根開盤進、排程第 x 根收盤出（皆為有效 K 棒索引）⇒ 回 (levels[e..x], 初始類型)。
    levels[j] ＝ 第 e+j 根收盤時生效的停損價（NaN ＝ 無停損）。"""
    sw = swing_lows(l, k)
    lag = k if lag is None else lag                              # ⭐ 正式＝k（右邊 k 根走完才確認）；lag≠k 只給 fixture ⑤ 的突變用
    conf = lambda s: s + lag                                      # 第 s 根的低點在 s+k 收盤才可用
    cand = [s for s in range(max(0, e - lookback), e + 1) if sw[s] and conf(s) <= e]
    if cand:
        stop = l[cand[-1]]; kind = "碎形"
    elif e >= MIN_BARS:
        atr = R.wilder_atr(h, l, c, ATR_N)
        stop = o[e] - ATR_MULT * atr[e - 1] if np.isfinite(atr[e - 1]) else np.nan
        kind = "3×ATR" if np.isfinite(stop) else "無停損"
    else:
        stop = np.nan; kind = "無停損"
    levels = np.full(x - e + 1, np.nan)
    for j, b in enumerate(range(e, x + 1)):
        s_new = b - lag                                          # 這一根收盤剛確認的擺動低點
        if s_new >= 0 and sw[s_new] and np.isfinite(stop) and l[s_new] > stop and s_new > (cand[-1] if cand else -1):
            stop = l[s_new]
        elif s_new >= 0 and sw[s_new] and not np.isfinite(stop) and kind != "無停損":
            stop = l[s_new]
        levels[j] = stop
    return levels, kind


def fixtures():
    """① 手造 15 根：兩個擺動低點 ⇒ 停損逐根與手算相同，第二個低點在 s+2 才生效；③ 3×ATR 代用與手算差 < 1e-10、K 棒不足 ⇒ 無停損。"""
    l = np.array([10, 9, 8, 9, 10, 11, 10, 9.5, 10, 12, 12, 11.5, 12, 13, 14], float)
    #             0  1  2  3   4   5   6   7    8   9   10  11    12  13  14
    # 擺動低點：s＝2（8，確認於 4）、s＝7（9.5，確認於 9）；s＝11（11.5）右邊只到 13 ⇒ 確認於 13
    h = l + 1; c = l + 0.5; o = l + 0.3
    sw = swing_lows(l)
    assert list(np.flatnonzero(sw)) == [2, 7, 11], np.flatnonzero(sw)
    lv, kind = stop_line(o, h, l, c, e=5, x=14)
    want = [8, 8, 8, 8, 9.5, 9.5, 9.5, 9.5, 11.5, 11.5]      # e＝5..14：9.5 在第 9 根生效、11.5 在第 13 根生效
    assert kind == "碎形" and np.allclose(lv, want), (lv, want)
    assert lv[8 - 5] == 8 and lv[9 - 5] == 9.5, "⛔ 第二個低點應在 s+2＝9 才生效，8 那天不生效"
    # ③ 無擺動低點（單調上升）、K 棒足 ⇒ 3×ATR 代用
    n = 130; c3 = np.linspace(100, 160, n); h3 = c3 + 1.0; l3 = c3 - 1.0; o3 = c3 - 0.2
    e = 125
    lv3, k3 = stop_line(o3, h3, l3, c3, e=e, x=n - 1)
    # 手算（⛔ 不呼叫任何 ATR 函式）：Wilder 遞迴從前 14 根 TR 平均起算
    tr = [h3[0] - l3[0]] + [max(h3[i] - l3[i], abs(h3[i] - c3[i - 1]), abs(l3[i] - c3[i - 1])) for i in range(1, n)]
    a_ = sum(tr[:14]) / 14
    for i in range(14, e):
        a_ = (a_ * 13 + tr[i]) / 14
    hand = o3[e] - 3 * a_
    assert k3 == "3×ATR" and abs(lv3[0] - hand) < 1e-10, (k3, lv3[0], hand)
    lv4, k4 = stop_line(o3[:100], h3[:100], l3[:100], c3[:100], e=90, x=99)
    assert k4 == "無停損" and np.all(np.isnan(lv4)), k4
    print("✅ 停損線 fixture：①擺動低點 [2,7,11]、停損逐根與手算相同、第二個低點在 s+2 才生效｜③3×ATR 代用差 {:.1e}、K 棒不足 ⇒ 無停損".format(abs(lv3[0] - hand)))


if __name__ == "__main__":
    fixtures()
