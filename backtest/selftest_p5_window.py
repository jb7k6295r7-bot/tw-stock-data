"""P5 對齊窗（型態線 20260923-2053 裁）的自測。

⛔⛔ 為什麼要另寫一支：既有的 `selftest_patterns.py` 那一格
   「P5 底穿上：上漲起點附近一次訊號 [301]」在 k=0 與 k=3 底下【給出同一個答案】
   ⇒ ⭐ 它分不出這次的訂正有沒有生效 ⇒ 依方法論〈突變測試前 fixture 要先證明它分得出來〉，
     ⛔ 不可以拿它當「改對了」的證據。

本支的四格，每一格都【必須】在 k=0 與 k=3 給出不同答案（第 ④ 格除外，它是護欄）。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import patterns as P  # noqa: E402

N = 120
FAIL = []


def frame(vol_day: int | None, cross_at: int = 60) -> P.Frame:
    """造一條在 cross_at 發生 5MA 上穿 10/20MA 的序列；放量只發生在 vol_day 那一天。

    ⭐ 手法：前段用極窄的區間讓三條均線收斂，cross_at 起小幅走高把 ma5 推過去。
    """
    c = np.full(N, 100.0)
    c[cross_at:] = 100.0 + np.arange(N - cross_at) * 0.9
    idx = pd.bdate_range("2020-01-01", periods=N)
    v = np.full(N, 1_000_000.0)
    if vol_day is not None:
        v[vol_day] = 1_000_000.0 * 3.0          # ⭐ 遠高於 ma_vol_x=1.5 倍
    df = pd.DataFrame({"open": c, "high": c * 1.001, "low": c * 0.999, "close": c,
                       "volume": v, "traded": True}, index=idx)
    f = P.Frame(df, set())
    return f


def sigs(f, k):
    return [s["signal_pos"] for s in P.ma_cross_up(f, confirm_window=k)]


def check(name, got, want):
    ok = got == want
    print("{} {}  得 {}　期望 {}".format("PASS" if ok else "⛔FAIL", name, got, want))
    if not ok:
        FAIL.append(name)


# ⭐ 先確認這個 fixture 真的造得出一個上穿（否則四格都是空對空 ⇒ 全部假綠）
f_same = frame(vol_day=None)
base_cross = [int(t) for t in np.flatnonzero(
    f_same.gate & (f_same.ma5 > np.maximum(f_same.ma10, f_same.ma20))
    & (np.roll(f_same.ma5, 1) <= np.roll(np.maximum(f_same.ma10, f_same.ma20), 1)))]
print("① fixture 自身有效性：上穿日 ＝ {}（⛔ 空的話下面四格全部沒有鑑別力）".format(base_cross))
if not base_cross:
    raise SystemExit("⛔⛔ fixture 造不出上穿 ⇒ 停止，⛔ 不可以拿下面的 PASS 當證據")
TC = base_cross[0]

# ② 放量【就在】上穿日 ⇒ 兩種尺都要抓到，且事件日相同
f = frame(vol_day=TC)
check("② 放量與上穿同日：k=0", sigs(f, 0), [TC])
check("② 放量與上穿同日：k=3", sigs(f, 3), [TC])

# ③ ⭐⭐ 放量在上穿【之後】2 日 ⇒ k=0 漏掉、k=3 抓到，且事件日 ＝ 放量日（較晚）
f = frame(vol_day=TC + 2)
check("③ 放量晚 2 日：k=0【應漏掉】", sigs(f, 0), [])
check("③ 放量晚 2 日：k=3 事件日＝放量日", sigs(f, 3), [TC + 2])

# ④ 放量在上穿【之前】2 日 ⇒ k=0 漏掉、k=3 抓到，事件日 ＝ 上穿日（較晚的那一天）
#    ⭐ 這一格正是型態線「⛔ 不是較早」那句話的斷言
f = frame(vol_day=TC - 2)
check("④ 放量早 2 日：k=0【應漏掉】", sigs(f, 0), [])
check("④ 放量早 2 日：k=3 事件日＝上穿日（⛔ 不是放量日）", sigs(f, 3), [TC])

# ⑤ 護欄：放量差 4 日（＞窗）⇒ 兩種尺都要漏掉（⛔ 窗不可以無限放寬）
f = frame(vol_day=TC + 4)
check("⑤ 放量晚 4 日 ＞ 窗：k=0", sigs(f, 0), [])
check("⑤ 放量晚 4 日 ＞ 窗：k=3【仍應漏掉】", sigs(f, 3), [])

# ⑥ 護欄：完全沒有放量 ⇒ 兩種尺都要 0 筆
f = frame(vol_day=None)
check("⑥ 全無放量：k=0", sigs(f, 0), [])
check("⑥ 全無放量：k=3", sigs(f, 3), [])

print()
if FAIL:
    raise SystemExit("⛔⛔ {} 格不過：{}".format(len(FAIL), "／".join(FAIL)))
print("✅ 全部通過。⭐ 而且第 ③ ④ 格【在 k=0 與 k=3 給出不同答案】")
print("   ⇒ 本 fixture 對這次的尺訂正【有鑑別力】，⛔ 不是空對空的綠燈。")
