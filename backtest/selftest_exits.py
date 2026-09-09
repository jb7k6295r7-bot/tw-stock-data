"""出場規則的合成資料自我測試（研究五／六／七用的 _hold／_stop 與 evaluate 的 hold_exit／atr_trail_exit）。

    python3 -m backtest.selftest_exits

每條規則一段手工序列，斷言「哪一天出、用哪個價」。回 CODE 09:50 全體 Q1：在此之前這些函式只靠
「H20 與研究二主表數字一致」這種總量交叉核對驗過，沒有逐路徑斷言；本檔補上。
"""
from __future__ import annotations

import sys

import numpy as np

from . import evaluate as E
from . import research5 as R5


def _arr(closes, opens=None, highs=None, lows=None, atr=None):
    c = np.array(closes, float)
    o = np.array(opens if opens is not None else closes, float)
    h = np.array(highs if highs is not None else np.maximum(o, c) * 1.01, float)
    l = np.array(lows if lows is not None else np.minimum(o, c) * 0.99, float)
    pc = np.concatenate([[np.nan], c[:-1]])
    a = np.array(atr if atr is not None else np.full(len(c), 1.0), float)
    return {"o": o, "h": h, "l": l, "c": c, "prev_c": pc, "atr14": a}


def check(name, cond, detail=""):
    print(f"{'✓' if cond else '✗'} {name} {detail}")
    return bool(cond)


def main():
    ok = True
    # 1. 固定持有：第 n 日收盤出（進場日算第 1 天）
    arr = _arr([100] * 30)
    arr["c"][4] = 123.0
    r = R5._hold(arr, 0, 5)
    ok &= check("hold n=5 → 第 5 日（索引 4）收盤", r == (4, 123.0, False), str(r))
    # 2. 固定持有遇缺收盤：順延到下一個有收盤的日子
    arr = _arr([100] * 30); arr["c"][4] = np.nan; arr["c"][5] = 111.0
    r = R5._hold(arr, 0, 5)
    ok &= check("hold 出場日缺收盤 → 順延一日", r == (5, 111.0, False), str(r))
    # 3. 固定持有遇跌停鎖死：順延（h==l 且收盤 ≤ 前收 × 0.905）
    c = [100.0] * 30; c[4] = 90.0; c[5] = 95.0
    arr = _arr(c); arr["h"][4] = 90.0; arr["l"][4] = 90.0
    r = R5._hold(arr, 0, 5)
    ok &= check("hold 出場日鎖跌停 → 順延到次日", r == (5, 95.0, False), str(r))
    # 4. 固定停損 8%：收盤跌破 92 → 次日開盤出
    c = [100, 99, 97, 91, 95, 100, 100, 100, 100, 100]
    o = [100, 99, 97, 91, 93, 100, 100, 100, 100, 100]
    arr = _arr(c, o)
    r = R5._stop(arr, 0, "stop", 0.08, cap=10)
    ok &= check("stop 8%：第 4 日收 91 < 92 → 第 5 日開盤 93 出", r == (4, 93.0, True), str(r))
    # 5. 固定停損：沒跌破 → 到期走 hold(cap)
    arr = _arr([100] * 12); arr["c"][9] = 105.0
    r = R5._stop(arr, 0, "stop", 0.08, cap=10)
    ok &= check("stop 未觸發 → 第 10 日收盤 105 出", r == (9, 105.0, False), str(r))
    # 6. 追蹤停損 10%：最高收盤 120 → 線 108；收 107 觸發
    c = [100, 110, 120, 115, 107, 100, 100, 100, 100, 100]
    arr = _arr(c)
    r = R5._stop(arr, 0, "trail", 0.10, cap=10)
    ok &= check("trail 10%：最高 120、收 107 < 108 → 次日開盤 100 出", r == (5, 100.0, True), str(r))
    # 7. 追蹤停損不觸發：回檔 9% 不出
    c = [100, 110, 120, 110, 110, 110, 110, 110, 110, 110]
    arr = _arr(c)
    r = R5._stop(arr, 0, "trail", 0.10, cap=10)
    ok &= check("trail 10%：回檔到 110（8.3%）不出 → 到期", r == (9, 110.0, False), str(r))
    # 8. ATR 追蹤 2×：ATR 2 → 線 ＝ 最高 − 4
    c = [100, 104, 108, 105, 103.9, 100, 100, 100, 100, 100]
    arr = _arr(c, atr=[2.0] * 10)
    r = R5._stop(arr, 0, "atr", 2.0, cap=10)
    ok &= check("atr 2×：最高 108、線 104、收 103.9 → 次日開盤出", r == (5, 100.0, True), str(r))
    # 9. ATR 進場日算不出 → None
    arr = _arr([100] * 10, atr=[np.nan] + [2.0] * 9)
    ok &= check("atr 進場日 NaN → None", R5._stop(arr, 0, "atr", 2.0, cap=10) is None)
    # 10. 停損觸發後沒有可成交的開盤 → 當日收盤出
    c = [100, 90, np.nan, np.nan]; o = [100, 90, np.nan, np.nan]
    arr = _arr(c, o)
    r = R5._stop(arr, 0, "stop", 0.05, cap=4)
    ok &= check("stop 觸發後無開盤 → 當日收盤 90 出", r == (1, 90.0, True), str(r))
    # 11. evaluate.atr_trail_exit 與 research5 A2（cap 相同時）出場日一致
    c = [100, 104, 108, 105, 103.9, 100, 100, 100, 100, 100]
    arr = _arr(c, atr=[2.0] * 10)
    old_cap = E.ATR_CAP; E.ATR_CAP = 10
    try:
        e = E.atr_trail_exit(arr, 0, 1)
    finally:
        E.ATR_CAP = old_cap
    ok &= check("evaluate.atr_trail_exit 與 research5 atr 同一天出", e[0] == 5 and e[1] == 100.0, str(e))
    print("\n全部通過" if ok else "\n有失敗")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
