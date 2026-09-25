# -*- coding: utf-8 -*-
"""PREREG型態全量 T1 fixture（backtest/patterns_all.py）——每個變體逐條；不過的變體標「T1 不過」、照報（⛔ 不中止別的變體）。

每個變體（96 個）：
  F1 標準型：合成教科書型態 ⇒ 抓在手算的那一根 T（K 棒：T ＝ 最後一根型態 K 棒；結構：見各 builder 註解）；d 與登錄相同
  F2 門檻差一點：同一組數字只改一個門檻差一點 ⇒ T 那一根抓不到（結構另附「差一點過」⇒ 仍抓得到）
  F3 ⭐ 前視突變：把 T 以後（不含 T）的價格與量換成 5 條隨機路徑 ⇒ T 以前（含 T）全部 96 變體的事件（T、first、d、r10、r20、r60、
     型態期間報酬）逐位元不變
  F4 ⭐ 鑑別力（不假綠）：「偷看一根」版（整條序列提前一根餵給偵測器 ⇒ 第 j 根的判定用到 j＋1）＋ 同一種突變（從 T 起換）
     ⇒ 5 條路徑裡至少一條讓 T 以前的事件變了（⇒ F3 的比法抓得到偷看一根）
全族（隨機序列 6 條 × 8 個切點，兩種突變：換路徑／截成前綴）：
  G1 正式版：所有變體零差異
  G2 偷看一根版（整條提前）：K 棒族必須抓到差異（其他族、轉折確認提早的隨機命中數只列報）
  G3 轉折確認提早（手造＋指定突變，見 lag_tests）：甲 lag＝2（提早一根）、乙 lag＝3（提早兩根）⇒ 偷看版必須被抓到、正式版不變
     ⚠ 乙 的突破只在 conf＋1 以後判 ⇒ 確認只提早「一根」時事件本身沒有用到未來（只有逐根狀態有）⇒ 事件層要提早兩根才是「事件偷看一根」
     ⚠ 隨機切點很少剛好落在「確認當根／確認後一根就觸發」的事件上 ⇒ 用手造序列保證會命中

    ~/tw-p16/.venv/bin/python -m backtest.selftest_patterns_all
"""
from __future__ import annotations
import os
import sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import patterns_all as PA          # noqa: E402

KEYS = ("T", "first", "d", "r10", "r20", "r60", "prd")
NBG = 70


# ═════════════ 共用 ═════════════
def mk(o, h, l, c, v=None):
    o, h, l, c = (np.asarray(x, float) for x in (o, h, l, c))
    v = np.full(len(c), 1000.0) if v is None else np.asarray(v, float)
    return {"o": o, "h": h, "l": l, "c": c, "v": v, "ro": o.copy(), "rh": h.copy(), "rl": l.copy(), "rc": c.copy()}


def run(A, **kw):
    return PA.detect_all(A["o"], A["h"], A["l"], A["c"], A["v"], A["ro"], A["rh"], A["rl"], A["rc"], **kw)


def adv(A):
    """偷看一根：x'[j] ＝ x[j＋1]（最後一根補缺值）。"""
    return {k: np.append(x[1:], np.nan) for k, x in A.items()}


def upto(r, T0):
    """T < T0 的事件（逐欄，浮點以 repr 比 ⇒ 逐位元）。"""
    out = {}
    for vid, e in r.items():
        m = e["T"] < T0
        out[vid] = [tuple(repr(float(e[k][i])) if k not in ("T", "first", "d") else int(e[k][i]) for k in KEYS) for i in np.flatnonzero(m)]
    return out


def diff_vids(a, b):
    return [v for v in a if a[v] != b.get(v)]


def rand_path(rng, c0, n, tick=0.05):
    """隨機 OHLCV（含一字線、光頭光腳、缺口、爆量）。"""
    o = np.empty(n); h = np.empty(n); l = np.empty(n); c = np.empty(n); v = np.empty(n)
    prev = c0
    for i in range(n):
        g = rng.normal(0, 0.03) + (rng.choice([-1, 1]) * 0.06 if rng.random() < 0.04 else 0.0)
        op = prev * np.exp(rng.normal(0, 0.012) + (g * 0.5 if rng.random() < 0.1 else 0.0))
        cl = prev * np.exp(g)
        hi = max(op, cl) * (1 + abs(rng.normal(0, 0.01))); lo = min(op, cl) * (1 - abs(rng.normal(0, 0.01)))
        if rng.random() < 0.15:
            hi = max(op, cl)
        if rng.random() < 0.15:
            lo = min(op, cl)
        if rng.random() < 0.03:
            op = cl = hi = lo = prev
        q = lambda x: max(tick, round(x / tick) * tick)
        o[i], h[i], l[i], c[i] = q(op), q(hi), q(lo), q(cl)
        h[i] = max(h[i], o[i], c[i]); l[i] = min(l[i], o[i], c[i])
        v[i] = float(np.exp(rng.normal(7, 0.5)) * (3 if rng.random() < 0.05 else 1))
        prev = c[i]
    return o, h, l, c, v


def mutate(A, T0, seed):
    """第 T0 根（含）以後換成一條隨機路徑（起價 ＝ c[T0−1]）。"""
    rng = np.random.default_rng(seed)
    n = len(A["c"]); B = {k: x.copy() for k, x in A.items()}
    if T0 >= n:
        return B
    o, h, l, c, v = rand_path(rng, float(A["c"][T0 - 1]), n - T0)
    for k, x in (("o", o), ("h", h), ("l", l), ("c", c), ("v", v), ("ro", o), ("rh", h), ("rl", l), ("rc", c)):
        B[k][T0:] = x
    return B


def rand_series(seed, n=1200):
    """全族用：折線（6～15 根一段、振幅隨機）＋ 雜訊 ⇒ 產生轉折、三角、缺口、爆量。"""
    rng = np.random.default_rng(seed)
    xs = [0]; ys = [100.0]
    while xs[-1] < n:
        xs.append(xs[-1] + int(rng.integers(6, 16))); ys.append(ys[-1] * float(np.exp(rng.normal(0, 0.07))))
    base = np.interp(np.arange(n), xs, ys)
    o, h, l, c, v = rand_path(rng, 100.0, n)
    c2 = np.round(base * np.exp(rng.normal(0, 0.006, n)) / 0.05) * 0.05
    sc = c2 / c
    o, h, l, c = o * sc, h * sc, l * sc, c2
    q = lambda x: np.round(x / 0.05) * 0.05
    o, h, l = q(o), q(h), q(l)
    h = np.maximum.reduce([h, o, c]); l = np.minimum.reduce([l, o, c])
    return mk(o, h, l, c, v)


# ═════════════ K 棒 68 型的合成資料 ═════════════
def kb_series(trend, bars, n_after=30):
    """背景 NBG 根：B＝1、R＝2（⇒ B̄＝1、R̄＝2）、收盤每根 ±0.5、最後一根收盤 100（升：白 K；降：黑 K）；接型態 K 棒；再接 n_after 根。"""
    o, h, l, c = [], [], [], []
    for i in range(NBG):
        if trend > 0:
            cc = 100.0 - 0.5 * (NBG - 1 - i); oo = cc - 1.0; hh = cc + 0.5; ll = oo - 0.5
        else:
            cc = 100.0 + 0.5 * (NBG - 1 - i); oo = cc + 1.0; hh = oo + 0.5; ll = cc - 0.5
        o.append(oo); h.append(hh); l.append(ll); c.append(cc)
    for (oo, hh, ll, cc) in bars:
        o.append(oo); h.append(hh); l.append(ll); c.append(cc)
    last = c[-1]
    for j in range(n_after):
        cc = last + (0.3 if j % 2 == 0 else -0.3); oo = last
        o.append(oo); h.append(max(oo, cc) + 0.4); l.append(min(oo, cc) - 0.4); c.append(cc); last = cc
    return mk(o, h, l, c)


# 編號 ⇒ (標準型 K 棒, 門檻差一點的 K 棒, 說明)；事前趨勢照登錄（升／降；無 ⇒ 用升，d 應 ＝ 續 +1、反 −1）
KFIX = {
    1: ([(101, 101.2, 99, 99), (100, 100.1, 98, 98), (99, 99.1, 97, 97)],
        [(101, 101.2, 99, 99), (100, 100.1, 98, 98), (99, 99.1, 97.6, 97.6)], "第 3 根 B 2→1.4（長 1.5B̄）"),
    2: ([(100, 102.2, 99.8, 102), (102.5, 102.8, 102.3, 102.6), (102.3, 102.4, 100, 100.5)],
        [(100, 102.2, 99.8, 102), (102.5, 102.8, 102.3, 102.6), (102.3, 102.4, 100, 101.1)], "C3 101.1 ＞ mid1 101"),
    3: ([(100, 100.1, 97.9, 98), (97.5, 99, 97.45, 97.8)],
        [(100, 100.1, 97.9, 98), (97.5, 98.35, 97.45, 97.8)], "U2 0.55 ＜ 2B2 0.6"),
    4: ([(101, 101.2, 98.8, 99), (99.5, 99.8, 98.9, 99.1)],
        [(101, 101.2, 98.8, 99), (99.5, 99.8, 98.9, 99.2)], "|C2−C1| 0.2 ＞ 0.2%×99"),
    5: ([(99, 99.2, 97.8, 98), (98.5, 99.1, 97, 97.2)],
        [(99, 99.2, 97.8, 98), (98.5, 99.2, 97, 97.2)], "H2 ＝ H1（要 ＜）"),
    6: ([(100, 102.2, 99.8, 102), (102.5, 103.3, 102.4, 103), (103, 103.8, 102.8, 103.5), (103.5, 104.3, 103.3, 104), (104.2, 104.3, 102.1, 102.2)],
        [(100, 102.2, 99.8, 102), (102.5, 103.3, 102.4, 103), (103, 103.8, 102.8, 103.5), (103.5, 104.3, 103.3, 104), (104.2, 104.3, 102.5, 102.6)], "C5 102.6 ≥ bot2 102.5"),
    7: ([(100, 100.2, 97.8, 98), (97.4, 97.7, 97.2, 97.5), (97.6, 99.6, 97.5, 99.4)],
        [(100, 100.2, 97.8, 98), (97.4, 97.7, 97.2, 97.5), (97.6, 99.6, 97.5, 98.9)], "C3 98.9 ＜ mid1 99"),
    8: ([(100, 100.2, 97.8, 98), (97.5, 99.6, 97.4, 99.5)],
        [(100, 100.2, 97.8, 98), (97.5, 99.6, 97.4, 98.9)], "C2 98.9 ≤ mid1 99"),
    9: ([(100.5, 100.7, 98.8, 99), (99.2, 100.8, 99.1, 100.5), (100.4, 100.6, 98.9, 99.1)],
        [(100.5, 100.7, 98.8, 99), (99.2, 100.8, 99.1, 100.5), (100.4, 100.6, 98.9, 99.2)], "|C3−C1| 0.2 ＞ 0.198"),
    10: ([(100, 100.2, 97.8, 98), (97.5, 98.8, 97.4, 98.6)],
         [(100, 100.2, 97.8, 98), (97.5, 98.8, 97.4, 98.15)], "C2 98.15 ≤ C1＋0.1B1 98.2"),
    11: ([(100, 102.2, 99.8, 102), (104, 104.2, 101.9, 102.1)],
         [(100, 102.2, 99.8, 102), (104, 104.2, 101.9, 102.25)], "|C2−C1| 0.25 ＞ 0.204"),
    12: ([(100, 100.2, 97.8, 98), (97.5, 98.2, 97.4, 98.1)],
         [(100, 100.2, 97.8, 98), (97.5, 98.3, 97.4, 98.25)], "C2 98.25 ＞ C1＋0.1B1 98.2"),
    13: ([(100, 100.2, 97.8, 98), (96, 98.2, 95.9, 98.1)],
         [(100, 100.2, 97.8, 98), (96, 98.3, 95.9, 98.25)], "|C2−C1| 0.25 ＞ 0.196"),
    14: ([(103.5, 104, 99.5, 100)], [(102.9, 103.4, 99.5, 100)], "B 2.9 ＜ 3B̄"),
    15: ([(100, 100.2, 97.8, 98), (99.5, 99.7, 98.3, 98.5)],
         [(100, 100.2, 97.8, 98), (100.1, 100.2, 98.9, 99.1)], "top2 100.1 ＞ top1 100"),
    16: ([(100, 102.2, 99.8, 102), (102.5, 102.6, 100.4, 100.5)],
         [(100, 102.2, 99.8, 102), (102.5, 102.6, 101, 101.1)], "C2 101.1 ≥ mid1 101"),
    17: ([(100, 100.2, 97.8, 98), (97.5, 97.8, 97.2, 97.52), (97.6, 99.8, 97.5, 99.7)],
         [(100, 100.2, 97.8, 98), (97.5, 97.8, 97.2, 97.57), (97.6, 99.8, 97.5, 99.7)], "第 2 根 B 0.07 ＞ 0.1R 0.06（非十字）"),
    18: ([(100, 102.2, 99.8, 102), (102.5, 102.8, 102.2, 102.52), (102.4, 102.45, 100.3, 100.4)],
         [(100, 102.2, 99.8, 102), (102.4, 102.7, 102.1, 102.42), (102.4, 102.45, 100.3, 100.4)], "bot2 102.4 ＝ top3（要 ＞）"),
    19: ([(100, 100.2, 97.8, 98), (99, 100.2, 98.9, 100)],
         [(100, 100.2, 97.8, 98), (98.9, 100.2, 98.8, 100)], "O2 98.9 ＜ mid1 99"),
    20: ([(98, 100, 97.8, 100), (99, 101.05, 98.8, 101), (100, 102, 99.9, 102)],
         [(98, 100, 97.8, 100), (99, 101.05, 98.8, 101), (100, 102.3, 99.9, 102)], "U3 0.3 ＞ 0.1R3 0.24"),
    21: ([(100, 100.2, 97.8, 98), (97.2, 97.9, 97.1, 97.85)],
         [(100, 100.2, 97.8, 98), (97.2, 98.1, 97.1, 98.0)], "|C2−L1| 0.2 ＞ 0.1956"),
    22: ([(100, 101.6, 98.4, 100.02)], [(100.5, 101.6, 98.4, 100.52)], "|mid−(H＋L)/2| 0.51 ＞ 0.1R 0.32"),
    23: ([(102, 102.2, 99.8, 100), (102.1, 104.3, 102, 104.2)],
          [(102, 102.2, 99.8, 100), (102.3, 104.3, 102.2, 104.2)], "|O2−O1| 0.3 ＞ 0.204"),
    24: ([(100, 101.6, 98.4, 100.02)], [(100, 101.45, 98.55, 100.02)], "R 2.9 ＜ 1.5R̄ 3"),
    25: ([(100, 100.2, 97.8, 98), (98.5, 99.7, 98.4, 99.5)],
         [(100, 100.2, 97.8, 98), (98.5, 100.2, 98.4, 100.1)], "top2 100.1 ＞ top1 100"),
    26: ([(98, 100.2, 97.9, 100), (98.1, 98.2, 95.9, 96)],
         [(98, 100.2, 97.9, 100), (98.3, 98.4, 95.9, 96)], "|O2−O1| 0.3 ＞ 0.196"),
    27: ([(102, 102.3, 100, 100)], [(102, 102.3, 99.9, 100)], "C ≠ L（有下影）"),
    28: ([(100.5, 100.7, 98.8, 99), (99.2, 99.9, 98.85, 99.6)],
         [(100.5, 100.7, 98.8, 99), (99.2, 99.9, 99.0, 99.6)], "|L2−L1| 0.2 ＞ 0.1976"),
    29: ([(100, 100.2, 97.8, 98), (97.5, 97.6, 96.8, 97), (97, 97.1, 96.3, 96.5), (96.5, 96.6, 95.8, 96), (95.8, 97.9, 95.7, 97.7)],
         [(100, 100.2, 97.8, 98), (97.5, 97.6, 96.8, 97), (97, 97.1, 96.3, 96.5), (96.5, 96.6, 95.8, 96), (95.8, 98.2, 95.7, 98.1)], "C5 98.1 ≥ bot1 98"),
    30: ([(99.2, 99.65, 97.8, 99.6)], [(99.2, 99.65, 98.05, 99.6)], "D 1.15 ＜ 3B 1.2"),
    31: ([(99, 99.6, 98.9, 99.5), (99.7, 99.8, 98.7, 98.8)],
         [(99, 99.6, 98.9, 99.5), (99.4, 99.5, 98.7, 98.8)], "top2 99.4 ＜ top1 99.5"),
    32: ([(100, 100.2, 97.8, 98), (97.5, 97.8, 97.2, 97.52)],
         [(100, 100.2, 97.8, 98), (97.98, 98.3, 97.7, 98.0)], "top2 98 ＝ bot1（要 ＜）"),
    33: ([(98, 100.2, 97.9, 100), (99, 99.5, 98.5, 99.02)],
         [(98, 100.2, 97.9, 100), (99, 100.3, 98.5, 99.02)], "H2 100.3 ＞ H1 100.2"),
    34: ([(100, 102.2, 99.8, 102), (102.5, 102.8, 102.2, 102.52)],
         [(100, 102.2, 99.8, 102), (102.0, 102.3, 101.7, 102.02)], "bot2 102 ＝ top1（要 ＞）"),
    35: ([(100, 103.8, 99.5, 103.5)], [(100, 103.2, 99.5, 102.9)], "B 2.9 ＜ 3B̄"),
    36: ([(100, 101.1, 99.9, 101), (100.5, 101.9, 100.4, 101.6), (101, 102.6, 100.9, 102)],
         [(100, 101.1, 99.9, 101), (100.5, 101.9, 100.4, 101.6), (101, 102.3, 100.9, 102)], "U3 0.3 ＝ U2（要 ＞）"),
    37: ([(102, 102, 100, 100)], [(102, 102.01, 100, 100)], "O ≠ H"),
    38: ([(102, 102, 99.9, 100)], [(102, 102.1, 99.9, 100)], "O ≠ H"),
    39: ([(100, 102.2, 99.8, 102), (101, 101.1, 99.9, 100)],
         [(100, 102.2, 99.8, 102), (101.1, 101.2, 99.9, 100)], "O2 101.1 ＞ mid1 101"),
    40: ([(100.4, 100.5, 99.9, 100)], [(100.4, 100.9, 99.9, 100)], "U 0.5 ＞ B 0.4（要 ＜）"),
    41: ([(100, 101.7, 98.7, 100.4)], [(100, 101.7, 98.9, 100.4)], "D 1.1 ＜ 3B 1.2"),
    42: ([(100, 101.2, 99.8, 101)], [(100, 101.7, 99.8, 101.5)], "B 1.5 ＝ 1.5B̄（要 ＜）"),
    43: ([(100, 100.8, 99.5, 100.3)], [(100, 100.6, 99.5, 100.3)], "U 0.3 ＝ B（要 ＞）"),
    44: ([(100, 102, 99.9, 102)], [(100, 102.01, 99.9, 102)], "C ≠ H"),
    45: ([(100, 102, 100, 102)], [(100, 102, 99.99, 102)], "O ≠ L"),
    46: ([(100, 102.2, 99.8, 102), (101.5, 101.6, 100.4, 100.5)],
         [(100, 102.2, 99.8, 102), (101.5, 101.6, 99.8, 99.9)], "bot2 99.9 ＜ bot1 100"),
    47: ([(100.3, 100.8, 99.5, 100)], [(100.3, 100.8, 99.7, 100)], "D 0.3 ＝ B（要 ＞）"),
    48: ([(100, 102.3, 100, 102)], [(100, 102.3, 99.99, 102)], "O ≠ L"),
    49: ([(100, 101.5, 100, 100.05)], [(100, 101.5, 99.8, 100.05)], "D 0.2 ＞ 0.1R 0.17"),
    50: ([(100, 100.5, 99.5, 100.05)], [(100, 100.5, 99.5, 100.11)], "B 0.11 ＞ 0.1R 0.1"),
    51: ([(100.5, 100.6, 99.9, 100), (99.9, 100.8, 99.8, 100.7)],
         [(100.5, 100.6, 99.9, 100), (99.9, 100.5, 99.8, 100.4)], "top2 100.4 ＜ top1 100.5"),
    52: ([(100, 102.2, 99.8, 102), (101, 101.5, 100.5, 101.02)],
         [(100, 102.2, 99.8, 102), (101, 101.5, 99.7, 101.02)], "L2 99.7 ＜ L1 99.8"),
    53: ([(100, 101.2, 99.8, 101), (101, 101.25, 100.3, 100.5)],
         [(100, 101.2, 99.8, 101), (101, 101.41, 100.3, 100.5)], "|H2−H1| 0.21 ＞ 0.2024"),
    54: ([(101, 101.2, 99.8, 100)], [(100.5, 100.6, 99.9, 100)], "B 0.5 ＝ 0.5B̄（要 ＞）"),
    55: ([(100, 100.5, 99.5, 100.05)], [(100, 100.5, 99.5, 100.11)], "B 0.11 ＞ 0.1R 0.1"),
    56: ([(99.5, 99.6, 98.9, 99), (98.9, 99.8, 98.8, 99.7)],
         [(99.5, 99.6, 98.9, 99), (98.9, 99.5, 98.8, 99.4)], "top2 99.4 ＜ top1 99.5"),
    57: ([(100, 100.5, 99.9, 100.4)], [(100, 100.5, 99.6, 100.4)], "D 0.4 ＝ B（要 ＜）"),
    58: ([(100.5, 101.05, 99.5, 101)], [(100.5, 101.05, 99.51, 101)], "D 0.99 ＜ 2B 1.0"),
    59: ([(99, 99.3, 98.7, 99.02)], [(99.2, 99.5, 98.9, 99.22)], "H 99.5 ＝ 前一日 L（要 ＜）"),
    60: ([(100, 100.2, 97.8, 98), (98.2, 98.5, 98.0, 98.4), (98.5, 98.9, 98.4, 98.8), (98.9, 99.3, 98.8, 99.2), (99.3, 99.4, 97.2, 97.3)],
         [(100, 100.2, 97.8, 98), (98.2, 98.5, 98.0, 98.4), (98.5, 98.9, 98.4, 98.8), (98.9, 99.3, 98.8, 99.2), (99.8, 99.9, 97.9, 98.0)], "C5 98 ＝ C1（要 ＜）"),
    61: ([(100, 100.6, 99.9, 100.5), (100.6, 100.7, 99.8, 99.9)],
         [(100, 100.6, 99.9, 100.5), (100.6, 100.7, 100.0, 100.05)], "bot2 100.05 ＞ bot1 100"),
    62: ([(101, 101.3, 100.7, 101.02)], [(100.8, 101.1, 100.5, 100.82)], "L 100.5 ＝ 前一日 H（要 ＞）"),
    63: ([(100, 102.2, 99.8, 102), (102, 104.2, 101.9, 104), (104.1, 104.5, 104, 104.4)],
         [(100, 102.2, 99.8, 102), (102, 104.2, 101.9, 104), (104.25, 104.6, 104.2, 104.5)], "|O3−C2| 0.25 ＞ 0.208"),
    64: ([(100, 102.2, 99.8, 102), (101.8, 102, 101.5, 101.6), (101.4, 101.6, 101.1, 101.2), (101.0, 101.2, 100.7, 100.8), (100.9, 102.7, 100.8, 102.6)],
         [(100, 102.2, 99.8, 102), (101.8, 102, 101.5, 101.6), (101.4, 101.6, 101.1, 101.2), (101.0, 101.2, 100.7, 100.8), (100.4, 102.1, 100.3, 102.0)], "C5 102 ＝ C1（要 ＞）"),
    65: ([(100, 100, 98, 98), (100.5, 102.5, 100.5, 102.5)], [(100, 100, 98, 98), (100, 102, 100, 102)], "L2 100 ＝ H1（要 ＞）"),
    66: ([(100, 101.2, 99.8, 101), (99.5, 99.7, 99.2, 99.52), (99, 99.1, 98, 98.2)],
         [(100, 101.2, 99.8, 101), (99.5, 99.7, 99.2, 99.52), (99, 99.2, 98, 98.2)], "H3 99.2 ＝ L2（要 ＜）"),
    67: ([(100, 100.02, 98.5, 100.01)], [(100, 100.21, 98.5, 100.01)], "U 0.2 ＞ 0.1R 0.171"),
    68: ([(100, 102, 100, 102), (99.5, 99.5, 97.5, 97.5)], [(100, 102, 100, 102), (100, 100, 98, 98)], "H2 100 ＝ L1（要 ＜）"),
}


def k_fixture(num):
    v = PA.VMAP[PA.vid_k(num)]
    tr = -1 if v["pre"] == "降" else 1
    std, near, why = KFIX[num]
    T = NBG + v["k"] - 1
    dexp = v["d"] if v["d"] in (1, -1) else (1 if v["d"] == "續" else -1)     # 無 ⇒ 背景升 ⇒ 續＝＋1、反＝−1
    return kb_series(tr, std), kb_series(tr, near), T, dexp, why


# ═════════════ 價格結構 28 變體的合成資料 ═════════════
def from_close(c, v=None, hw=0.5):
    c = np.asarray(c, float)
    return mk(c - 0.2, c + hw, c - hw, c, v)


def pw(pts, n):
    xs, ys = zip(*pts)
    return np.interp(np.arange(n), xs, ys).astype(float)


def s_turn(num, near):
    if num == 1:      # M 頭：P1＝70(100)、V＝80(88→差一點 91)、P2＝90(99)；T ＝ 第一個 c＜C_V：c(x)＝99−1.4(x−90) ⇒ x＝98
        V = 91.0 if near else 88.0
        return from_close(pw([(0, 80), (70, 100), (80, V), (90, 99), (100, 85), (130, 85)], 131)), 98, "V 91（跌幅 9% ＜ 10%）"
    if num == 2:      # 三重底：L 70/90/110＝100/101/102、A＝113（差一點 109.9）；T：c＝102＋(23/15)(x−110) ＞ 113 ⇒ x＝118
        A1, A2 = (109.9, 109.9) if near else (112.0, 113.0)
        return from_close(pw([(0, 130), (70, 100), (80, A1), (90, 101), (100, A2), (110, 102), (125, 125), (150, 125)], 151)), 118, "反彈 9.9% ＜ 10%"
    if num == 3:      # 三重頂：P 70/90/110＝100/99/98、V＝88（差一點 90.5）；T：c＝98−1.2(x−110) ＜ 88 ⇒ x＝119
        V1, V2 = (91.0, 90.5) if near else (89.0, 88.0)
        return from_close(pw([(0, 70), (70, 100), (80, V1), (90, 99), (100, V2), (110, 98), (125, 80), (150, 80)], 151)), 119, "回檔 9.5% ＜ 10%"


def _line_series(kinds, xs, ys, up, margin=3.0, lead=20.0):
    """乙 型：頂點 (xs, ys)（kinds：H／L 交錯）；還原 high＝c＋0.5、low＝c−0.5；
    最後頂點之後 5 根往內走 0.3／根（保住嚴格轉折），第 6 根（＝conf＋1）跳到上線＋margin（向上）或下線−margin（向下）⇒ T ＝ x_last＋6。"""
    lead_y = ys[0] - lead if kinds[0] == "H" else ys[0] + lead
    pts = [(0, lead_y)] + list(zip(xs, ys))
    xl, yl, kl = xs[-1], ys[-1], kinds[-1]
    n = xl + 6 + 31
    c = pw(pts, xl + 1)
    tail = [yl + (-0.3 if kl == "H" else 0.3) * j for j in range(1, 6)]
    Hx = [x for x, k in zip(xs, kinds) if k == "H"]; Hy = [y + 0.5 for y, k in zip(ys, kinds) if k == "H"]
    Lx = [x for x, k in zip(xs, kinds) if k == "L"]; Ly = [y - 0.5 for y, k in zip(ys, kinds) if k == "L"]
    return c, tail, (Hx, Hy), (Lx, Ly), xl, n


def _finish(c, tail, lineU, lineL, xl, n, up, margin=3.0, ulines=None):
    """ulines：(上線, 下線) 用哪幾個點配（鑽石＝後段）；fixture 自己用 np.polyfit 算（與偵測器獨立）。"""
    (Hx, Hy), (Lx, Ly) = ulines if ulines else (lineU, lineL)
    bu = np.polyfit(Hx, Hy, 1); bl = np.polyfit(Lx, Ly, 1)
    T = xl + 6
    cT = np.polyval(bu, T) + margin if up else np.polyval(bl, T) - margin
    cc = np.concatenate([c, tail, [cT], np.full(n - T - 1, cT)])
    return from_close(cc), T


def s_line(num, near):
    """S4～S17：5 個頂點（x＝70,80,90,100,110），3 點那一邊的中間點位移 δ：差一點過 0.97δ*、差一點不過 1.03δ*（δ* ＝ 剛好 2%）；
    標準型 δ＝0。near ∈ {None, 'pass', 'fail'}。"""
    geo = {  # (kinds, ys)
        "sym": ("HLHLH", [120, 100, 116, 104, 112]),
        "asc": ("HLHLH", [120, 100, 120, 106, 120]),
        "desc": ("HLHLH", [120, 100, 116, 100, 112]),
        "rw": ("HLHLH", [110, 100, 114, 106, 118]),
        "fw": ("HLHLH", [130, 110, 124, 106, 118]),
        "brT": ("HLHLH", [110, 100, 114, 96, 118]),
        "brB": ("LHLHL", [100, 110, 96, 114, 92]),
    }
    typ, up = {4: ("sym", 1), 5: ("sym", 0), 6: ("asc", 1), 7: ("asc", 0), 8: ("desc", 1), 9: ("desc", 0),
               10: ("rw", 1), 11: ("rw", 0), 12: ("fw", 1), 13: ("fw", 0), 14: ("brT", 1), 15: ("brT", 0),
               16: ("brB", 1), 17: ("brB", 0)}[num]
    kinds, ys = geo[typ]; ys = [float(y) for y in ys]; xs = [70, 80, 90, 100, 110]
    why = ""
    if near:
        k = kinds[2]; Y = ys[2] + (0.5 if k == "H" else -0.5)
        dstar = 0.06 * Y / (2 - 0.02) if k == "H" else 0.06 * Y / (2 + 0.02)
        dl = dstar * (0.97 if near == "pass" else 1.03)
        ys[2] += dl if k == "H" else -dl
        why = "中間{}點離線 {:.2f}%（差一點{}）".format("高" if k == "H" else "低", 100 * (2 * dl / 3) / (Y + (dl / 3 if k == "H" else -dl / 3)),
                                               "過" if near == "pass" else "不過")
    c, tail, U, L, xl, n = _line_series(list(kinds), xs, ys, up)
    A, T = _finish(c, tail, U, L, xl, n, up)
    return A, T, why


def s_diamond(num, near):
    """S18～S21：8 個頂點間距 17（首到尾含頭尾 ＝ 120 日 ⇒ 剛好過）；差一點不過 ＝ 最後一段 18（121 日）。T ＝ x_last＋6。"""
    top = num in (18, 19); up = num in (18, 20)
    if top:
        kinds = "HLHLHLHL"; ys = [110, 100, 115, 95, 114, 97, 110, 101]
    else:
        kinds = "LHLHLHLH"; ys = [100, 110, 95, 115, 96, 114, 100, 110]
    gaps = [17] * 7
    if near:
        gaps[-1] = 18
    xs = [70]
    for g_ in gaps:
        xs.append(xs[-1] + g_)
    c, tail, U, L, xl, n = _line_series(list(kinds), xs, [float(y) for y in ys], up)
    back = [(x, y, k) for x, y, k in zip(xs, ys, kinds)][4:]
    bU = ([x for x, y, k in back if k == "H"], [y + 0.5 for x, y, k in back if k == "H"])
    bL = ([x for x, y, k in back if k == "L"], [y - 0.5 for x, y, k in back if k == "L"])
    A, T = _finish(c, tail, U, L, xl, n, up, ulines=(bU, bL))
    return A, T, "首到尾 121 日 ＞ 120"


def s_round(num, near):
    """S22：a＝300（120）、弧 90＋30((x−xv)/(xv−300))²、xv＝432（中間三分之一上界 432.67 ⇒ 過；差一點 433 ⇒ 不過）、T＝500 收 121。
    S23／S24：鏡像 150−30(·)²；向上 T 收 151、向下 T 收 119。"""
    xv = 433.0 if near else 432.0
    x = np.arange(301, 500, dtype=float)
    if num == 22:
        lead = np.concatenate([np.linspace(150, 125, 240), np.linspace(124, 119.6, 10), np.linspace(119.5, 119.0, 50)])
        arc = 90 + 30 * ((x - xv) / (xv - 300)) ** 2
        c = np.concatenate([lead, [120.0], arc, [121.0], np.full(30, 121.0)])
    else:
        lead = np.concatenate([np.linspace(80, 115, 240), np.linspace(116, 120.4, 10), np.linspace(120.5, 121.0, 50)])
        arc = 150 - 30 * ((x - xv) / (xv - 300)) ** 2
        cT = 151.0 if num == 23 else 119.0
        c = np.concatenate([lead, [120.0], arc, [cT], np.full(30, cT)])
    return from_close(c), 500, "頂點 433 ＞ 中間三分之一上界 432.67"


def s_island(num, near):
    """S25 頂：a＝70 全跳空向上、b＝75 全跳空向下、b 量 2000（差一點 1000 ＝ 均量，要 ＞）；S26 底鏡像。T＝75。"""
    vol = np.full(106, 1000.0); vol[75] = 1000.0 if near else 2000.0
    if num == 25:
        c = np.concatenate([np.linspace(80, 100, 70), [103, 103.5, 104, 103.8, 103.4, 99], np.full(30, 99.0)])
    else:
        c = np.concatenate([np.linspace(120, 100, 70), [97, 96.5, 96, 96.2, 96.6, 101], np.full(30, 101.0)])
    return from_close(c, vol), 75, "第二缺口量 ＝ 前 20 日均量（要 ＞）"


def s_v(near):
    """S27：60 根 100 ⇒ 10 根跌到 70（b＝70，量 2500，差一點 1999）⇒ 75、80、86（≥ 85）⇒ T＝73。"""
    vol = np.full(104, 1000.0); vol[70] = 1999.0 if near else 2500.0
    c = np.concatenate([np.full(60, 100.0), np.linspace(100, 70, 11), [75, 80, 86], np.full(30, 86.0)])
    return from_close(c, vol), 73, "底部量 1.999 倍 ＜ 2 倍"


def s_platform(near):
    """S28：110 根 100 ⇒ 第 110 根 131（差一點 129.9 ⇒ 漲 29.9%）⇒ 111～149 在 131～137 來回 ⇒ T＝150 收 140。"""
    cyc = [131, 133, 135, 137, 135, 133]
    osc = [cyc[j % 6] for j in range(39)]
    c = np.concatenate([np.full(110, 100.0), [129.9 if near else 131.0], osc, [140.0], np.full(30, 140.0)])
    return from_close(c), 150, "起點漲幅 29.9% ＜ 30%"


def s_fixture(num, near):
    if num <= 3:
        return s_turn(num, near)
    if num <= 17:
        return s_line(num, near)
    if num <= 21:
        return s_diamond(num, near)
    if num <= 24:
        return s_round(num, near)
    if num <= 26:
        return s_island(num, near)
    if num == 27:
        return s_v(near)
    return s_platform(near)


# ═════════════ 逐變體 ═════════════
def has(r, vid, T):
    return bool(np.any(r[vid]["T"] == T))


def one_variant(vid, n_mut=5):
    v = PA.VMAP[vid]
    res = {"vid": vid, "name": v["name"]}
    if v["fam"] == "K":
        num = int(vid[1:])
        A, An, T, dexp, why = k_fixture(num)
        extra = {}
    else:
        num = int(vid[1:])
        A, T, _ = s_fixture(num, None)
        An, _, why = s_fixture(num, "fail" if 4 <= num <= 17 else True)
        dexp = v["d"]
        extra = {}
        if 4 <= num <= 17:
            Ap = s_fixture(num, "pass")[0]
            extra["差一點過"] = has(run(Ap), vid, T)
    r = run(A)
    got = r[vid]["T"].tolist()
    i = np.flatnonzero(r[vid]["T"] == T)
    f1 = len(i) == 1 and int(r[vid]["d"][i[0]]) == dexp
    rn = run(An)
    f2 = (not has(rn, vid, T)) and extra.get("差一點過", True)
    base = upto(r, T + 1)
    f3 = True
    for s in range(n_mut):
        rm = run(mutate(A, T + 1, 1000 + s))
        if diff_vids(base, upto(rm, T + 1)):
            f3 = False
    pk = run(adv(A))
    pk_has = has(pk, vid, T - 1)
    pbase = upto(pk, T)
    f4 = False
    for s in range(n_mut):
        pm = run(adv(mutate(A, T, 2000 + s)))
        if diff_vids(pbase, upto(pm, T)):
            f4 = True
    res.update(T=T, 抓到=got[:6], F1=f1, F2=f2, F3=f3, F4=f4 and pk_has, 差一點=why, **extra)
    res["T1"] = bool(f1 and f2 and f3 and res["F4"])
    return res


# ═════════════ 全族：隨機序列 ═════════════
def fam_of(vid):
    return PA.VMAP[vid]["fam"]


def family_tests(seeds=range(6), cuts=8):
    rng = np.random.default_rng(7)
    real_bad = {}; peek_hit = {}; laga_hit = 0; lagb_hit = 0; nev = {}
    for sd in seeds:
        A = rand_series(100 + sd)
        n = len(A["c"])
        r = run(A); pa = run(adv(A)); ra = run(A, lag_a=2); rb = run(A, lag_b=3)
        for vid in PA.VID:
            nev[vid] = nev.get(vid, 0) + len(r[vid]["T"])
        for T0 in sorted(rng.integers(320, n - 40, cuts)):
            T0 = int(T0)
            b0 = upto(r, T0)
            for how in ("mut", "cut"):
                B = mutate(A, T0, 31 * sd + T0) if how == "mut" else {k: x[:T0] for k, x in A.items()}
                for vid in diff_vids(b0, upto(run(B), T0)):
                    real_bad[vid] = real_bad.get(vid, 0) + 1
                if how == "mut":
                    for vid in diff_vids(upto(pa, T0), upto(run(adv(B)), T0)):
                        peek_hit[fam_of(vid)] = peek_hit.get(fam_of(vid), 0) + 1
                    dA = diff_vids(upto(ra, T0), upto(run(B, lag_a=2), T0))
                    laga_hit += sum(1 for vid in dA if vid in ("S01", "S02", "S03"))
                    dB = diff_vids(upto(rb, T0), upto(run(B, lag_b=3), T0))
                    lagb_hit += sum(1 for vid in dB if PA.VMAP[vid]["fam"] == "乙")
    return {"G1_正式版有差異的變體": real_bad, "G2_整條提前一根_抓到差異_依族": peek_hit,
            "G2_甲確認提早一根_抓到差異次數": laga_hit, "G2_乙確認提早兩根_抓到差異次數": lagb_hit,
            "隨機序列事件數": {k: v for k, v in nev.items() if v}}


def lag_tests():
    """G3 轉折確認提早的鑑別力（手造、指定突變）：
    甲：M 頭 P2＝90、第 92、93 根就跌破 C_V ⇒ 正式（確認 93）T＝93；偷看版（lag＝2，確認 92）T＝92 ⇒ 把第 93 根起拉到 105（P2 不再是轉折）
        ⇒ 偷看版 93 以前的事件必須變；正式版 93 以前的事件必須不變。
    乙：對稱三角 HLHLH、最後高點 110；第 114 根就跌破下線 ⇒ 正式（確認 115、判 116 起）無事件；偷看版（lag＝3，確認 113、判 114 起）T＝114
        ⇒ 把第 115 根起拉到 125（高點 110 不再是轉折）⇒ 偷看版 115 以前的事件必須變；正式版不變。"""
    out = {}
    c = pw([(0, 80), (70, 100), (80, 88), (90, 99), (92, 87.5), (93, 87)], 94)
    c = np.concatenate([c, np.full(30, 87.0)])
    A = from_close(c)
    B = {k: x.copy() for k, x in A.items()}
    for k, add in (("c", 0.0), ("o", -0.2), ("h", 0.5), ("l", -0.5)):
        B[k][93:] = 105.0 + add; B["r" + k][93:] = 105.0 + add
    real0, real1 = upto(run(A), 93), upto(run(B), 93)
    pk0, pk1 = upto(run(A, lag_a=2), 93), upto(run(B, lag_a=2), 93)
    out["甲"] = {"正式T": run(A)["S01"]["T"].tolist(), "偷看版T": run(A, lag_a=2)["S01"]["T"].tolist(),
                "正式不變": not diff_vids(real0, real1), "偷看版被抓到": "S01" in diff_vids(pk0, pk1)}
    kinds, ys, xs = "HLHLH", [120.0, 100.0, 116.0, 104.0, 112.0], [70, 80, 90, 100, 110]
    cc, tail, U, L, xl, n = _line_series(list(kinds), xs, ys, 0)
    bl = np.polyfit(*L, 1)
    tail = [ys[-1] - 0.3 * j for j in range(1, 4)] + [np.polyval(bl, 114) - 3.0, np.polyval(bl, 114) - 3.0]
    c2 = np.concatenate([cc, tail, np.full(n - xl - 6, np.polyval(bl, 114) - 3.0)])
    A2 = from_close(c2)
    B2 = {k: x.copy() for k, x in A2.items()}
    for k, add in (("c", 0.0), ("o", -0.2), ("h", 0.5), ("l", -0.5)):
        B2[k][115:] = 125.0 + add; B2["r" + k][115:] = 125.0 + add
    r0, r1 = upto(run(A2), 115), upto(run(B2), 115)
    p0, p1 = upto(run(A2, lag_b=3), 115), upto(run(B2, lag_b=3), 115)
    out["乙"] = {"正式T": run(A2)["S05"]["T"].tolist(), "偷看版T": run(A2, lag_b=3)["S05"]["T"].tolist(),
                "正式不變": not diff_vids(r0, r1), "偷看版被抓到": "S05" in diff_vids(p0, p1)}
    out["過"] = all(v["正式不變"] and v["偷看版被抓到"] for k, v in out.items() if k in ("甲", "乙"))
    return out


def run_all(verbose=True):
    rows = []
    for vid in PA.VID:
        try:
            res = one_variant(vid)
        except Exception as e:                      # ⛔ 單一變體出錯 ⇒ 標 T1 不過、照報，不中止
            res = {"vid": vid, "name": PA.VMAP[vid]["name"], "T1": False, "錯誤": repr(e)}
        rows.append(res)
        if verbose:
            print(("✅ " if res["T1"] else "⛔ ") + "{} {}｜{}".format(vid, res["name"],
                  {k: res.get(k) for k in ("T", "抓到", "F1", "F2", "F3", "F4", "差一點過", "錯誤") if k in res}), flush=True)
    fam = family_tests()
    fam["G3_轉折確認提早_手造"] = lag_tests()
    g_ok = (not fam["G1_正式版有差異的變體"]) and fam["G3_轉折確認提早_手造"]["過"] \
        and fam["G2_整條提前一根_抓到差異_依族"].get("K", 0) > 0
    if verbose:
        print(("✅ " if g_ok else "⛔ ") + "全族 {}".format(fam), flush=True)
    # 全族正式版若在某變體出現前視差異 ⇒ 該變體 T1 不過
    for r in rows:
        if r["vid"] in fam["G1_正式版有差異的變體"]:
            r["T1"] = False; r["G1前視"] = fam["G1_正式版有差異的變體"][r["vid"]]
    n_ok = sum(r["T1"] for r in rows)
    if verbose:
        print("T1 過 {}／{}；不過：{}".format(n_ok, len(rows), [r["vid"] for r in rows if not r["T1"]]))
    return {"逐變體": rows, "全族": fam, "全族過": bool(g_ok), "T1過": n_ok}


if __name__ == "__main__":
    run_all()
