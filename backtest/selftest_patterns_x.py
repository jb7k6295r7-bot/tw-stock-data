# -*- coding: utf-8 -*-
"""PREREGX T1（登錄 §一之二 末行、§四「前置」）：合成教科書型態 fixture —— 每一條都要過，researchX.py 才准開跑該型。

 甲 三個新偵測器（W 底、頭肩底、旗形）：
   A1 標準型抓得到、而且抓在手算的那一根（T、目標、型態低點逐值比）
   A2 門檻差一點的抓不到（每條門檻各一組：差一點過 vs 差一點不過；等號邊界算過）
 乙 六個形成中狀態（箱型、杯柄、W 底、頭肩底、旗形、趨勢線）：
   B1 標準型的 S 落在手算的那一根；B2 門檻差一點 ⇒ 沒有 S
 C  ⭐ 前視突變：隨機改動 T0 以後的價格（另一條路徑／截成前綴兩種）⇒ T0 以前（含）的事件、S、逐根狀態完全不變
 D  ⭐ 測試分得出來（不假綠）：故意把確認提早一根（lag＝k−1；趨勢線 lag＝R−1；箱型／杯柄用「偷看次日」版）
    ⇒ C 的比法【必須】抓到差異；同一組突變用正式版 ⇒ 零差異

    ~/tw-p16/.venv/bin/python -m backtest.selftest_patterns_x
"""
from __future__ import annotations
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import patterns_x as PX                  # noqa: E402
from backtest import patterns as P                     # noqa: E402
from backtest import selftest_patterns as SP           # noqa: E402  研究二的合成杯柄（只 import）
from backtest import selftest_trendline_m as STM       # noqa: E402  PREREGM 的合成趨勢線（只 import）

RES = {}


def rec(key, ok, msg):
    RES[key] = (bool(ok), msg)
    print(("✅ " if ok else "⛔ ") + key + "｜" + msg, flush=True)
    return ok


def pw(pts, n=None):
    """分段線性收盤（整數 K 棒）。"""
    xs, ys = zip(*pts)
    n = (xs[-1] + 1) if n is None else n
    return np.interp(np.arange(n), xs, ys).astype(float)


def ev(r):
    return [e["T"] for e in r["events"]]


def S_of(r):
    return [g["S"] for g in r["groups"] if g["S"] is not None]


# ═════════════ 甲＋乙：W 底 ═════════════
def t_w():
    ok = True
    c = pw([(0, 130), (30, 100), (40, 115), (50, 101), (70, 131)])
    r = PX.detect_turn("w", c)
    e = r["events"]
    ok &= rec("W.A1 標準型", ev(r) == [60] and e[0]["pts"] == {"L1": 30, "L2": 50, "A": 40}
              and abs(e[0]["target"] - 130.0) < 1e-9 and e[0]["low"] == 100.0,
              "L1＝30、L2＝50、A＝40（115）⇒ T＝60（第一個收盤 116 ＞ 115）、目標 130、低點 100；得 {}".format(ev(r)))
    ok &= rec("W.B1 形成中", S_of(r) == [53], "L2 確認日 53 收盤 105.5 ＜ 115 ⇒ S＝53；得 {}".format(S_of(r)))
    got = {}
    for tag, L2 in (("eq 5.00%（等號）", 105.0), ("eq 5.10%", 105.1)):
        rr = PX.detect_turn("w", pw([(0, 130), (30, 100), (40, 115), (50, L2), (70, 131)]))
        got[tag] = (ev(rr), S_of(rr))
    ok &= rec("W.A2/B2 兩底差", got["eq 5.00%（等號）"][0] != [] and got["eq 5.10%"] == ([], []),
              "等號 5% 抓得到、5.1% 抓不到（S 也沒有）；得 {}".format(got))
    got = {}
    for tag, A in (("bounce 10.0%（等號）", 110.0), ("bounce 9.9%", 109.9)):
        rr = PX.detect_turn("w", pw([(0, 130), (30, 100), (40, A), (50, 101), (70, 131)]))
        got[tag] = (ev(rr), S_of(rr))
    ok &= rec("W.A2/B2 反彈", got["bounce 10.0%（等號）"][0] != [] and got["bounce 9.9%"] == ([], []),
              "等號 10% 抓得到、9.9% 抓不到；得 {}".format(got))
    got = {}
    for tag, L2, end in (("L1→T 60 根", 79, (120, 162.5)), ("L1→T 61 根", 80, (121, 162.5))):
        rr = PX.detect_turn("w", pw([(0, 130), (30, 100), (55, 115), (L2, 101), end]))
        got[tag] = ev(rr)
    ok &= rec("W.A2 60 日視窗", got["L1→T 60 根"] == [89] and got["L1→T 61 根"] == [],
              "T−L1＋1＝60 抓（T＝89）、61 不抓；得 {}".format(got))
    return ok


# ═════════════ 甲＋乙：頭肩底 ═════════════
def t_hs():
    ok = True
    base = [(0, 130), (20, 100), (27, 115), (35, 85), (43, 114), (50, 101), (80, 146)]
    r = PX.detect_turn("hs", pw(base))
    e = r["events"]
    ok &= rec("HS.A1 標準型", ev(r) == [60] and e[0]["pts"]["L"] == 20 and e[0]["pts"]["H"] == 35 and e[0]["pts"]["R"] == 50
              and abs(e[0]["level"] - 114.5) < 1e-9 and abs(e[0]["target"] - 144.0) < 1e-9 and e[0]["low"] == 85.0,
              "L/H/R＝20/35/50、頸線 (115＋114)/2＝114.5 ⇒ T＝60、目標 144、低點 85；得 {}".format(ev(r)))
    ok &= rec("HS.B1 形成中", S_of(r) == [53], "右肩確認日 53 收盤 105.5 ＜ 114.5 ⇒ S＝53；得 {}".format(S_of(r)))
    w_ = PX.detect_turn("w", pw(base))
    ok &= rec("HS.A1' 不誤判成 W", ev(w_) == [], "同一條序列 W 底 0 筆（兩底差 15%、19%）；得 {}".format(ev(w_)))
    got = {}
    for tag, R in (("兩肩差 4.94%", 104.2), ("兩肩差 5.18%", 104.4)):
        rr = PX.detect_turn("hs", pw([(0, 130), (20, 100), (27, 115), (35, 85), (43, 114), (50, R), (80, 146)]))
        got[tag] = (ev(rr), S_of(rr))
    ok &= rec("HS.A2/B2 兩肩", got["兩肩差 4.94%"][0] != [] and got["兩肩差 5.18%"] == ([], []), "得 {}".format(got))
    got = {}
    for tag, H in (("頭深 10.0%（等號）", 90.0), ("頭深 9.9%", 90.1)):
        rr = PX.detect_turn("hs", pw([(0, 120), (20, 95), (27, 100), (35, H), (43, 100), (50, 95.5), (80, 130)]))
        got[tag] = (ev(rr), S_of(rr))
    ok &= rec("HS.A2/B2 頭深", got["頭深 10.0%（等號）"][0] != [] and got["頭深 9.9%"] == ([], []), "得 {}".format(got))
    rr = PX.detect_turn("hs", pw([(0, 120), (20, 95), (27, 110), (35, 96), (43, 110), (50, 95.5), (80, 130)]))
    ok &= rec("HS.A2/B2 頭不是最低", (ev(rr), S_of(rr)) == ([], []), "頭 96 ＞ 左肩 95 ⇒ 0 筆；得 {}".format((ev(rr), S_of(rr))))
    return ok


# ═════════════ 甲＋乙：旗形 ═════════════
def flag_series(P_top=135.0, face=None, brk=134.0, n_after=10):
    """0..30：95→100；30..45：100→P_top（E＝45）；旗面 46..；突破 brk；之後每根＋1。"""
    c = list(pw([(0, 95), (30, 100), (45, P_top)]))
    if face is None:
        j = np.arange(1, 13)
        face = P_top - (0.0815 * P_top) * (1 - np.exp(-j / 4.0)) / (1 - np.exp(-3.0))
    c += list(face) + [brk]
    for _ in range(n_after):
        c.append(c[-1] + 1.0)
    return np.array(c, float)


def t_flag():
    ok = True
    c = flag_series()
    r = PX.detect_turn("flag", c)
    e = r["events"]
    fh = c[46]; s0 = c[25]
    ok &= rec("FLAG.A1 標準型", ev(r) == [58] and e[0]["pts"] == {"S0": 25, "E": 45}
              and abs(e[0]["level"] - fh) < 1e-9 and abs(e[0]["target"] - (fh + 135.0 - s0)) < 1e-9 and e[0]["low"] == c[57],
              "E＝45（135）、S0＝25（旗桿 {:.1%}）、旗面 46..57 回檔 {:.1%} ⇒ T＝58、目標＝旗面高 {:.2f}＋旗桿 {:.2f}；得 {}".format(
                  135 / s0 - 1, (135 - c[57]) / 135, fh, 135 - s0, ev(r)))
    ok &= rec("FLAG.B1 形成中", S_of(r) == [51], "旗面滿 5 日的第一根 51、收盤 ≤ 旗面高 ⇒ S＝51；得 {}".format(S_of(r)))
    got = {}
    for tag, top in (("旗桿 30.0%", c[25] * 1.3001), ("旗桿 29.98%", c[25] * 1.2998)):
        rr = PX.detect_turn("flag", flag_series(P_top=top, brk=top - 1.0))
        got[tag] = (ev(rr), S_of(rr))
    ok &= rec("FLAG.A2/B2 旗桿", got["旗桿 30.0%"][0] == [58] and got["旗桿 29.98%"] == ([], []), "得 {}".format(got))
    j = np.arange(1, 13)
    got = {}
    for tag, d in (("回檔 5.1%", 0.051), ("回檔 4.9%", 0.049)):
        face = 135.0 - (d * 135.0) * (1 - np.exp(-j / 4.0)) / (1 - np.exp(-3.0))
        rr = PX.detect_turn("flag", flag_series(face=face))
        got[tag] = (ev(rr), S_of(rr))
    ok &= rec("FLAG.A2/B2 回檔下限", got["回檔 5.1%"][0] == [58] and got["回檔 4.9%"] == ([], []), "得 {}".format(got))
    got = {}
    for tag, d in (("回檔 19.9%", 0.199), ("回檔 20.1%", 0.201)):
        face = 135.0 - (d * 135.0) * (1 - np.exp(-j / 4.0)) / (1 - np.exp(-3.0))
        rr = PX.detect_turn("flag", flag_series(face=face))
        got[tag] = ev(rr)
    ok &= rec("FLAG.A2 回檔上限", got["回檔 19.9%"] == [58] and got["回檔 20.1%"] == [], "得 {}".format(got))
    got = {}
    for tag, face in (("斜率 ＜ 0", 127 - 2 * np.sqrt(np.linspace(0, 1, 12))), ("斜率 ＞ 0", 125 + 2 * np.sqrt(np.linspace(0, 1, 12)))):
        rr = PX.detect_turn("flag", flag_series(face=face))
        got[tag] = (ev(rr), S_of(rr))
    ok &= rec("FLAG.A2/B2 斜率", got["斜率 ＜ 0"][0] == [58] and got["斜率 ＞ 0"] == ([], []), "得 {}".format(got))
    got = {}
    for tag, m in (("旗面 25 日", 25), ("旗面 26 日", 26)):
        rr = PX.detect_turn("flag", flag_series(face=132 - 7 * np.sqrt(np.linspace(0, 1, m))))
        got[tag] = ev(rr)
    ok &= rec("FLAG.A2 旗面長", got["旗面 25 日"] == [71] and got["旗面 26 日"] == [], "25 日（T＝71）抓、26 日不抓；得 {}".format(got))
    conv_ok = np.r_[np.linspace(131, 126, 6), np.linspace(126, 125, 6)]
    conv_bad = np.r_[np.linspace(128, 127.5, 6), np.linspace(127.4, 124, 6)]
    got = {}
    for tag, face in (("收斂", conv_ok), ("後半變寬", conv_bad)):
        got[tag] = ev(PX.detect_turn("flag", flag_series(face=face)))
    ok &= rec("FLAG.A2 收斂", got["收斂"] == [58] and got["後半變寬"] == [], "得 {}".format(got))
    face = np.array([132, 131, 130, 136, 130, 129, 128, 127, 126, 125, 124.5, 124.0])
    rr = PX.detect_turn("flag", flag_series(face=face))
    g45 = [g for g in rr["groups"] if g["id"] == (45,)]
    ok &= rec("FLAG.A2 旗面收盤高過 E ⇒ 作廢", all(e["id"] != (45,) for e in rr["events"]) and len(g45) == 1 and g45[0]["end"] == 49,
              "第 49 根（旗面第 3 天）收 136 ＞ 135 ⇒ E＝45 這組在 49 作廢、沒有觸發；得 E＝45 組終點 {}、事件 {}".format([g["end"] for g in g45], [(e["T"], e["id"]) for e in rr["events"]]))
    return ok


# ═════════════ 乙：箱型、杯柄、趨勢線 ═════════════
def t_box():
    ok = True
    got = {}
    for tag, dip in (("高度 19.4%", 81.0), ("高度 20.5%", 79.9)):
        c = np.full(60, 100.0); c[30] = dip
        f = PX.frame_open(SP.base_frame(c))
        got[tag] = [s["S"] for s in PX.box_forming(f)]
    ok &= rec("BOX.B1 形成中", got["高度 19.4%"][0] == 20 and 35 in got["高度 19.4%"] and 30 not in got["高度 19.4%"],
              "平台 100（實體 99.5～100）⇒ 第一個 S＝20；含低點 81 的箱（t＝31～50）仍成立；t＝30 收盤 81 在箱外 ⇒ 不是 S")
    ok &= rec("BOX.B2 高度門檻", all(t not in got["高度 20.5%"] for t in range(31, 51)) and 20 in got["高度 20.5%"],
              "含 79.9 的箱（實體下緣 79.5 ⇒ 20.5%）⇒ t＝31～50 沒有 S；其餘照有")
    c = np.full(60, 100.0); c[34] = 100.5
    f = PX.frame_open(SP.base_frame(c))
    S = [s["S"] for s in PX.box_forming(f)]
    ok &= rec("BOX.B2 3 天法則", 35 not in S and 36 not in S and 37 in S,
              "箱頂在 t−1、t−2 才設（第 34 根）⇒ t＝35、36 不是 S，37 才是；得 35～37：{}".format([t for t in S if 35 <= t <= 37]))
    return ok


def cup_series(depth=0.20, v_shape=False):
    c, v, t = SP.synth_cup()
    x = np.linspace(-1, 1, 121)
    if v_shape:
        c[430:551] = 140 - 140 * depth * (1 - np.abs(x))
    else:
        c[430:551] = 140 - 140 * depth * np.sqrt(np.clip(1 - x ** 2, 0, 1))
    return c, v, t


def t_cup():
    ok = True
    c, v, t = cup_series()
    f = PX.frame_open(SP.base_frame(c, v))
    sig, groups = PX.cup_scan(f)
    ref = P.cup_handle(f)
    gS = [(g["L"], g["R"], g["S"], g["trig"]) for g in groups if g["S"] is not None]
    ok &= rec("CUP.B1 形成中", gS == [(429, 550, 556, t)] and [s["signal_pos"] for s in sig] == [s["signal_pos"] for s in ref] == [t],
              "L＝429、R＝550 ⇒ 柄滿 5 日的第一根 S＝556、同一個 R 的突破 {}；cup_scan 突破清單＝patterns.cup_handle；得 {}".format(t, gS))
    got = {}
    for tag, d in (("杯深 32.5%", 0.325), ("杯深 33.5%", 0.335)):
        c2, v2, _ = cup_series(depth=d)
        f2 = PX.frame_open(SP.base_frame(c2, v2))
        got[tag] = [g["S"] for g in PX.cup_scan(f2)[1] if g["S"] is not None]
    ok &= rec("CUP.B2 杯深", got["杯深 32.5%"] == [556] and got["杯深 33.5%"] == [], "得 {}".format(got))
    c3, v3, _ = cup_series(v_shape=True)
    s3 = [g["S"] for g in PX.cup_scan(PX.frame_open(SP.base_frame(c3, v3)))[1] if g["S"] is not None]
    ok &= rec("CUP.B2 V 型", s3 == [], "直線 V（最低 25% 區停留 25% ＜ 35%）⇒ 沒有 S；得 {}".format(s3))
    v4 = v.copy(); v4[551:566] = 1_200_000
    s4 = [g["S"] for g in PX.cup_scan(PX.frame_open(SP.base_frame(c, v4)))[1] if g["S"] is not None]
    ok &= rec("CUP.B2 柄沒量縮", s4 == [], "柄均量 120 萬 ≥ 右半杯 100 萬 ⇒ 沒有 S；得 {}".format(s4))
    return ok


def t_trend():
    ok = True
    o, h, l, c = STM.build(slope=-0.1, kappa=0.15, gap=2.1, q=0.0)
    r = PX.trend_forming(o, h, c)
    gs = [(g["id"], g["S"], g["trig"]) for g in r["groups"]]
    ok &= rec("TREND.B1 形成中", gs == [((10, 30), 36, None), ((30, 50), 56, 70)],
              "線 (10,30) 確認於 35 ⇒ S＝36（收盤低於線 1.7%）；55 換線 (30,50) ⇒ S＝56、同組 70 突破；得 {}".format(gs))
    o, h, l, c = STM.build(slope=-0.1, kappa=0.15, gap=4.0, q=0.0)
    r = PX.trend_forming(o, h, c)
    gs = [(g["id"], g["S"]) for g in r["groups"]]
    ok &= rec("TREND.B2 3% 門檻", all(s is None for _, s in gs) and len(gs) == 2,
              "收盤低於線 3.3%～3.4% ⇒ 兩條線都沒有 S；得 {}".format(gs))
    return ok


# ═════════════ C＋D：前視突變與鑑別力 ═════════════
def rand_close(rng, m, vol=0.03):
    return 100 * np.exp(np.cumsum(rng.normal(0, vol, m)))


def _snap_turn(r, T0):
    return ([(e["T"], e["id"]) for e in r["events"] if e["T"] <= T0],
            sorted((g["id"], g["S"]) for g in r["groups"] if g["S"] is not None and g["S"] <= T0),
            list(r["trace"][:T0 + 1]))


def mutate_turn(kind, lag, trials=300, seed=7):
    rng = np.random.default_rng(seed)
    diff = 0; n_items = 0
    for _ in range(trials):
        m = 400
        c = rand_close(rng, m, vol=0.05 if kind == "flag" else 0.03)
        T0 = int(rng.integers(60, m - 20))
        full = PX.detect_turn(kind, c, lag=lag, trace=True)
        a = _snap_turn(full, T0)
        n_items += len(a[0]) + len(a[1])
        c2 = c.copy(); c2[T0 + 1:] = c[T0] * np.exp(np.cumsum(rng.normal(0, 0.05, m - T0 - 1)))
        b = _snap_turn(PX.detect_turn(kind, c2, lag=lag, trace=True), T0)
        p = _snap_turn(PX.detect_turn(kind, c[:T0 + 1], lag=lag, trace=True), T0)
        diff += int(a != b) + int(a != p)
    return diff, n_items


def _snap_trend(r, T0):
    return (sorted((g["id"], g["S"]) for g in r["groups"] if g["S"] is not None and g["S"] <= T0),
            [e["T"] for e in r["events"] if e["T"] <= T0], list(r["trace"][:T0 + 1]))


def mutate_trend(lag, trials=200, seed=11):
    rng = np.random.default_rng(seed)
    diff = 0; n_items = 0
    for _ in range(trials):
        m = 400
        o, h, c = STM.rand_series(rng, m)
        T0 = int(rng.integers(60, m - 20))
        a = _snap_trend(PX.trend_forming(o, h, c, lag=lag), T0)
        n_items += len(a[0])
        o2, h2, c2 = o.copy(), h.copy(), c.copy()
        k = np.exp(np.cumsum(rng.normal(0, 0.05, m - T0 - 1)))
        c2[T0 + 1:] = c[T0] * k; o2[T0 + 1:] = c2[T0 + 1:] * 1.003; h2[T0 + 1:] = np.fmax(o2, c2)[T0 + 1:] * 1.01
        b = _snap_trend(PX.trend_forming(o2, h2, c2, lag=lag), T0)
        p = _snap_trend(PX.trend_forming(o[:T0 + 1], h[:T0 + 1], c[:T0 + 1], lag=lag), T0)
        diff += int(a != b) + int(a != p)
    return diff, n_items


def _df(c, v, rng):
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.004, len(c)))
    h = np.fmax(o, c) * (1 + np.abs(rng.normal(0, 0.006, len(c))))
    l = np.fmin(o, c) * (1 - np.abs(rng.normal(0, 0.006, len(c))))
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v},
                      index=pd.bdate_range("2015-01-05", periods=len(c)))
    df["traded"] = True
    return df


def _peek(df):
    """⛔ 故意偷看：把第 t 根換成第 t+1 根（給 D 的鑑別力測試）。"""
    d = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        d[col] = d[col].shift(-1).bfill().ffill()
    return d


def _snap_frame(df, T0, peek, which):
    f = PX.frame_open(_peek(df) if peek else df)
    if which == "box":
        return [s["S"] for s in PX.box_forming(f) if s["S"] <= T0]
    sig, g = PX.cup_scan(f, pivot_shift=3 if peek else 0)
    return ([s["signal_pos"] for s in sig if s["signal_pos"] <= T0],
            sorted((x["L"], x["R"], x["S"]) for x in g if x["S"] is not None and x["S"] <= T0))


def mutate_frame(which, peek, trials=60, seed=13):
    rng = np.random.default_rng(seed)
    diff = 0; n_items = 0
    for _ in range(trials):
        if which == "box":
            m = 300
            c = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, m)))
            v = np.full(m, 1e6) * np.exp(rng.normal(0, 0.3, m))
            T0 = int(rng.integers(40, m - 10))
        else:
            c0, v0, t = SP.synth_cup()
            c = c0 * np.exp(rng.normal(0, 0.002, len(c0))); v = v0.copy(); m = len(c)
            T0 = int(rng.integers(556, 561))
        df = _df(c, v, rng)
        a = _snap_frame(df, T0, peek, which)
        n_items += len(a) if which == "box" else len(a[0]) + len(a[1])
        d2 = df.copy()
        k = 1.08 * np.exp(np.cumsum(rng.normal(0.01, 0.05, m - T0 - 1)))
        base = float(df["close"].iloc[T0])
        for col in ("open", "high", "low", "close"):
            d2.iloc[T0 + 1:, d2.columns.get_loc(col)] = base * k * (1.02 if col == "high" else (0.98 if col == "low" else 1.0))
        d2.iloc[T0 + 1:, d2.columns.get_loc("volume")] = 5e6
        b = _snap_frame(d2, T0, peek, which)
        p = _snap_frame(df.iloc[:T0 + 1].copy(), T0, peek, which)
        diff += int(a != b) + int(a != p)
    return diff, n_items


def t_mutation():
    ok = True
    for kind in ("w", "hs", "flag"):
        d0, n0 = mutate_turn(kind, None)
        d1, _ = mutate_turn(kind, PX.K - 1)
        ok &= rec("{}.C 前視突變".format(kind.upper()), d0 == 0 and n0 > 30,
                  "300 次 × 兩種突變（另一條路徑、截成前綴）⇒ 差異 {} 次；比對到的事件＋S {} 個".format(d0, n0))
        ok &= rec("{}.D 鑑別力".format(kind.upper()), d1 > 0, "確認提早一根（lag＝2）⇒ 同一組突變抓到差異 {} 次（必須 ＞ 0）".format(d1))
    d0, n0 = mutate_trend(None)
    d1, _ = mutate_trend(PX.TL_R - 1)
    ok &= rec("TREND.C 前視突變", d0 == 0 and n0 > 30, "200 次 × 兩種 ⇒ 差異 {}；比對到的 S {} 個".format(d0, n0))
    ok &= rec("TREND.D 鑑別力", d1 > 0, "lag＝R−1 ⇒ 差異 {} 次".format(d1))
    for which in ("box", "cup"):
        d0, n0 = mutate_frame(which, False)
        d1, _ = mutate_frame(which, True)
        ok &= rec("{}.C 前視突變".format(which.upper()), d0 == 0 and n0 > 10, "60 次 × 兩種 ⇒ 差異 {}；比對到 {} 個".format(d0, n0))
        ok &= rec("{}.D 鑑別力".format(which.upper()), d1 > 0,
                  "偷看次日版（箱型：第 t 根換成 t+1；杯柄：樞紐多看 3 根）⇒ 差異 {} 次".format(d1))
    return ok


def run_all():
    out = {}
    for name, fn in (("w", t_w), ("hs", t_hs), ("flag", t_flag), ("box", t_box), ("cup", t_cup), ("trend", t_trend)):
        out[name] = bool(fn())
    t_mutation()
    for key, (okk, _) in RES.items():
        typ = key.split(".")[0].lower()
        out[typ] = out.get(typ, True) and okk
    return out, RES


if __name__ == "__main__":
    res, _ = run_all()
    print("\n=== T1 各型 ===")
    for k_, v_ in res.items():
        print("  {:6s} {}".format(k_, "過" if v_ else "⛔ 不過"))
    sys.exit(0 if all(res.values()) else 1)
