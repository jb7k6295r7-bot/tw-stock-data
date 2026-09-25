# -*- coding: utf-8 -*-
"""PREREG營飆停損（seq200）六族停損線 ＋ PREREG營飆時停（seq201）九格時停線 ＋ ⓓ 補股池放寬逐日池：建構器 fixture 與真資料計數。
回測線，2026-09-26。⛔ 不跑任何判定格、⛔ 不讀年化／回落；引擎只跑手造小例（引擎取 git HEAD 的 research11.py，⛔ 不動工作樹那一份）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 python backtest/selftest_yfstop.py fixtures  # 手算小例＋引擎小例＋無前視＋突變體（不讀資料）
    ... real    # setup_t1 的訊號列：六族（M 三種 arm）＋時停九格全部建線；與獨立迴圈版逐點比對；略過數、停損距離、進場隔天觸發占比、
                #   價格層第一次觸發距進場幾根（⛔ 不跑引擎）；寫 resultsYfStop/lines_*.json
    ... pool    # ⓓ：不去重池逐列重建 signals_S／and_signals／setup_t1 的 1,688 列；逐日池大小分佈、對當日訊號池的比例；池列建線略過數
    ... all
"""
from __future__ import annotations

import bisect
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest", "resultsYfStop")
RESULTS: list = []
EXTRA: dict = {}

from backtest import selftest_p9engine as SP9        # noqa: E402  ⭐ 只借小工具
from backtest import yfstop_lines as Y               # noqa: E402
from backtest import stop_fractal as SF              # noqa: E402
from backtest import listexit_lines as L             # noqa: E402
run, NC = SP9.run, SP9.NC

LIT_LE = {"P15": True, "T20": True, "A3": False, "M20": False, "M50": False, "F": False}     # 登錄 §二 字面
LIT_TIME_LE = {"R0": True, "R10": False, "NH": False}                                       # 時停登錄 §二 字面


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag, extra=None):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"lines_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
         "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if extra:
        d["extra"] = extra
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


def engine_head():
    blob = subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD:backtest/research11.py"]).decode().strip()
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", blob]).decode("utf-8")
    EXTRA["engine_blob"] = blob
    return SP9._load_src(src, "backtest._r11_yfstop_head", os.path.join(REPO, "backtest", "research11.py"))


# ─────────────────────────── 突變體（原始碼字串替換；每個都必須讓手算組至少一條失敗）
Y_MUT = {
    "MU_P15_lt":   ('"P15": {"le": True,', '"P15": {"le": False,'),
    "MU_T20_lt":   ('"T20": {"le": True,', '"T20": {"le": False,'),
    "MU_A3_le":    ('"A3":  {"le": False,', '"A3":  {"le": True,'),
    "MU_M20_le":   ('"M20": {"le": False,', '"M20": {"le": True,'),
    "MU_M50_le":   ('"M50": {"le": False,', '"M50": {"le": True,'),
    "MU_F_le":     ('"F":   {"le": False,', '"F":   {"le": True,'),
    "MU_T20_down": ("hi = np.maximum.accumulate(run)", "hi = run"),
    "MU_MA_fut":   ("cur = ma[j]", "cur = ma[min(j + 1, len(ma) - 1)]"),
    "MU_MA_excl":  ("ma[n - 1:] = (cs[n:] - cs[:-n]) / n", "ma[n:] = (cs[n:-1] - cs[:-n - 1]) / n"),
    "MU_MA_cal":   ("cv = np.asarray(c_cal, float)[idx]", "cv = np.asarray(c_cal, float)[np.arange(idx[0], idx[0] + len(idx))]"),
    "MU_d_off":    ("jd = k + 1 + d - 1", "jd = k + 1 + d"),
    "MU_NH_bar1":  ("ev = np.zeros(d, bool); hi = float(cb[0])", "ev = np.zeros(d, bool); ev[0] = True; hi = float(cb[0])"),
    "MU_NH_ge":    ("if float(cb[m]) > hi:", "if float(cb[m]) >= hi:"),
    "MU_R0_lt":    ('TIME_LE = {"R0": True,', 'TIME_LE = {"R0": False,'),
    "MU_R10_naive": ("return pct_of(ep, 110)", "return ep * 1.10"),
    "MU_inf":      ("BIG = float(np.finfo(np.float64).max)", "BIG = float('inf')"),
}
SF_MUT = {
    "MF_down": ("if s_new >= 0 and sw[s_new] and np.isfinite(stop) and l[s_new] > stop and", "if s_new >= 0 and sw[s_new] and np.isfinite(stop) and"),
    "MF_lag":  ("lag = k if lag is None else lag", "lag = k - 1 if lag is None else lag"),
}


def y_mut(tag):
    ys = open(Y.__file__, encoding="utf-8").read()
    if tag in Y_MUT:
        a, b = Y_MUT[tag]
        if ys.count(a) != 1:
            raise SystemExit(f"⛔ 突變點 {tag} 找不到或不唯一：{a!r}")
        return SP9._load_src(ys.replace(a, b), f"backtest._yf_{tag}", Y.__file__)
    a, b = SF_MUT[tag]
    ss = open(SF.__file__, encoding="utf-8").read()
    if ss.count(a) != 1:
        raise SystemExit(f"⛔ 突變點 {tag} 找不到或不唯一：{a!r}")
    sfm = SP9._load_src(ss.replace(a, b), f"backtest._sf_{tag}", SF.__file__)
    ym = SP9._load_src(ys, f"backtest._yf_{tag}", Y.__file__)
    ym.SF = sfm
    return ym


# ─────────────────────────── 手算小例（每條 (名, ok, 細節)；同一組拿去跑突變體）
def find_tick_mismatch(pct, step):
    """找一個 float32 可表示的整數價 x（x 為 step 的倍數），使 x×pct/100 是整數、而 (pct/100)×x 算出來不是它（示範浮點寫法差一個 ulp）。"""
    for m in range(1, 20001):
        x = float(step * m); want = x * pct // 100
        if (pct / 100) * x != want and x * pct / 100 == want:
            return x
    return None


def hand(Ym, R):
    out = []

    def add(nm, ok, det=""):
        out.append((nm, bool(ok), det))

    def safe(fn):
        try:
            fn()
        except Exception as ex:                  # 突變體可能直接炸 ⇒ 算抓到
            add(f"{fn.__name__} 例外", False, repr(ex)[:200])

    def t_table():
        add("T0 比較方向對登錄字面：P15、T20「≤」、A3、M20、M50、F「＜」；時停 R0「≤」、R10「＜」、NH 必觸發",
            {k: v["le"] for k, v in Ym.FAMILIES.items()} == LIT_LE and Ym.TIME_LE == LIT_TIME_LE,
            f"{ {k: v['le'] for k, v in Ym.FAMILIES.items()} }｜{Ym.TIME_LE}")

    def t_p15():
        x = 20.0
        sig = pd.DataFrame({"sid": ["A", "B"], "k": [9, 9], "entry_pos": [10, 10], "xpos_H120": [60, 60]})
        oA = np.full(NC, x); cA = np.full(NC, x); oB = np.full(NC, 10.0); oB[10] = np.nan; cB = np.full(NC, 12.0)
        ln = Ym.p15_lines(sig, {"A": oA, "B": oB}, {"A": cA, "B": cB})
        want = x * 85 // 100
        add(f"P1 P15 線 ＝ ep×85／100 ＝ {want}（ep＝{x}）；開盤 NaN ⇒ ep 用收盤 12 ⇒ 10.2",
            ln[("A", 10)][1][0] == want and len(ln[("A", 10)][1]) == 51 and ln[("B", 10)][1][0] == 12.0 * 85 / 100,
            f"{ln[('A', 10)][1][0]!r}／{ln[('B', 10)][1][0]!r}")
        # 引擎：收盤恰好 ＝ 線 ⇒ 次日開盤出（le）
        o_ = np.full(NC, x); c_ = np.full(NC, x); c_[20] = want; o_[21] = want - 1.0; c_[21:] = x
        o = run(R, [("A", 10, 60)], {"A": (o_, c_)}, 2, stop_line={("A", 10): ln[("A", 10)]}, stop_line_le=Ym.FAMILIES["P15"]["le"])
        sells = [(r["t"], r["px"]) for r in o["_audit"] if r["side"] == "sell"]
        add("P2 引擎：收盤恰 ＝ 線 ⇒ t＝21 開盤出（「≤」）", sells[:1] == [(21, want - 1.0)], f"{sells}")

    def t_t20():
        valid = np.ones(30, bool); valid[[12, 13]] = False
        c = np.full(30, 10.0); c[5] = 10.0; c[6] = 12.0; c[7] = 11.0; c[8] = 9.6; c[12] = 50.0; c[13] = 50.0; c[14] = 13.0
        lv = Ym.t20_levels(c, valid, 5, 20)
        want = [8.0, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 10.4, 10.4, 10.4, 10.4, 10.4, 10.4, 10.4]
        add("T1 T20 手算：進場日收盤 10 起算 ⇒ 8.0；12 ⇒ 9.6；停牌日（12、13）的 50 不算；14 收 13 ⇒ 10.4；只升不降",
            np.array_equal(lv, np.array(want)), f"{lv.tolist()}")
        o_ = np.full(NC, 10.0); o_[5] = 11.0; c_ = np.full(NC, 10.0); c_[6] = 12.0; c_[7] = 11.0; c_[8] = 9.6; o_[9] = 9.3
        ln = (5, Ym.t20_levels(c_, np.ones(NC, bool), 5, 60))
        o = run(R, [("A", 5, 60)], {"A": (o_, c_)}, 2, stop_line={("A", 5): ln}, stop_line_le=Ym.FAMILIES["T20"]["le"])
        sells = [(r["t"], r["px"]) for r in o["_audit"] if r["side"] == "sell"]
        add("T2 引擎：高點 12 ⇒ 線 9.6；收盤恰 9.6 ⇒ t＝9 開盤 9.3 出（「≤」）；進場開盤 11 ＞ 收盤 10 不影響起點（起點 ＝ 進場日收盤）",
            sells[:1] == [(9, 9.3)] and ln[1][0] == 8.0, f"{sells}")

    def t_a3():
        idx = np.arange(20); atr = np.full(20, 0.5); atr[5] = 0.1
        c = np.full(20, 10.0); c[5] = 9.9; c[6] = 9.6; c[7] = 10.4; c[9] = 11.0; c[10] = 12.0
        s, lv = L.trail_levels(idx, atr, c, 4, 10.0, 15, 3.0, "entry_close")
        want = [9.6, 9.6, 9.6, 9.6, 9.6, 10.5, 10.5, 10.5, 10.5, 10.5, 10.5]
        add("A1 A3＝S2 的 3 倍：起始 10−1.5＝8.5；d5 收 9.9 第一個高點 ⇒ 9.9−0.3＝9.6；d7 10.4 ⇒ 8.9 不降；d9 11 ⇒ 9.5 不降；d10 12 ⇒ 10.5",
            s == 5 and np.allclose(lv, want, atol=1e-12), f"{np.round(lv, 6).tolist()}")

    def ma_case(c_cal, valid, k_cal, e, xp, n, arm):
        idx = np.flatnonzero(valid); k = int(np.searchsorted(idx, k_cal))
        return Ym.ma_levels(c_cal, idx, Ym.ma_valid(c_cal, idx, n), k, e, xp, arm)

    def t_ma():
        valid = np.ones(30, bool); valid[[12, 13]] = False
        c = np.full(30, 10.0); c[10] = 9.0; c[11] = 11.0; c[12] = 11.0; c[13] = 11.0; c[14] = 12.0; c[15] = 10.0
        n3 = lambda *v: sum(v) / 3
        want = [n3(10, 10, 9), n3(10, 9, 11), n3(10, 9, 11), n3(10, 9, 11), n3(9, 11, 12), n3(11, 12, 10), n3(12, 10, 10), 10.0, 10.0, 10.0, 10.0]
        lv = ma_case(c, valid, 9, 10, 20, 3, "state")
        add("M1 均線（n＝3 手算）state：含該根收盤；停牌日（12、13）沿用 11 的均線；14 復牌 ＝ (9＋11＋12)/3（只數有效 K 棒）",
            np.allclose(lv, want, rtol=0, atol=1e-12), f"{np.round(lv, 6).tolist()}")
        tr = Y.first_trigger(lv, 10, c, 20, False)
        add("M2 state：進場日收盤 9 ＜ 9.667 ⇒ 觸發日 ＝ 進場日（次日開盤出）", tr == 10, f"{tr}")
        lv2 = ma_case(c, valid, 9, 10, 20, 3, "cross_sig")
        add("M3 cross_sig：訊號日 c＝10 ≥ MA＝10 ⇒ 從進場日起同 state", np.allclose(lv2, want, rtol=0, atol=1e-12, equal_nan=True))
        lv3 = ma_case(c, valid, 9, 10, 20, 3, "cross_entry")
        add("M4 cross_entry：進場日 9 ＜ 均線 ⇒ 沒線；11 收 11 ≥ 10 ⇒ 從 11 起有線",
            np.isnan(lv3[0]) and np.allclose(lv3[1:], want[1:], rtol=0, atol=1e-12), f"{np.round(lv3, 6).tolist()}")
        c2 = c.copy(); c2[9] = 9.5
        lv4 = ma_case(c2, valid, 9, 10, 20, 3, "cross_sig")
        add("M5 cross_sig：訊號日 9.5 ＜ MA 9.833 ⇒ 未武裝；進場日 9 仍下；11 收 11 ≥ (9.5＋9＋11)/3 ⇒ 從 11 起",
            np.isnan(lv4[0]) and abs(lv4[1] - (9.5 + 9 + 11) / 3) < 1e-12, f"{np.round(lv4[:3], 6).tolist()}")
        try:
            Ym.ma_levels(c, np.flatnonzero(valid), Ym.ma_valid(c, np.flatnonzero(valid), 3), 9, 10, 20, None); bad = False
        except ValueError:
            bad = True
        add("M6 arm 沒給 ⇒ ValueError（登錄沒寫、⛔ 建構器不自己選）", bad)
        # 引擎：平盤 收盤 ＝ 20 日均線 ⇒「＜」不出
        o_ = np.full(NC, 10.0); c_ = np.full(NC, 10.0)
        ln = (30, ma_case(c_, np.ones(NC, bool), 29, 30, 60, 20, "state"))
        o = run(R, [("A", 30, 60)], {"A": (o_, c_)}, 2, stop_line={("A", 30): ln}, stop_line_le=Ym.FAMILIES["M20"]["le"])
        sells = [r["t"] for r in o["_audit"] if r["side"] == "sell"]
        add("M7 引擎：平盤 收盤 ＝ 20 日均線 10 ⇒「＜」不觸發、抱到排程 60", sells == [60] and ln[1][0] == 10.0, f"{sells}")
        for fam in ("M50", "A3", "F"):
            o = run(R, [("A", 30, 60)], {"A": (o_, c_)}, 2, stop_line={("A", 30): (30, np.full(31, 10.0))}, stop_line_le=Ym.FAMILIES[fam]["le"])
            add(f"M8 引擎：{fam} 收盤 ＝ 線 ⇒「＜」不觸發", [r["t"] for r in o["_audit"] if r["side"] == "sell"] == [60])

    def t_f():
        l = np.array([10, 9, 8, 9, 10, 11, 10, 9.5, 10, 12, 11, 9.0, 10, 11, 12, 13], float)
        h = l + 1; c = l + 0.5; o = l + 0.3
        bars = list(range(12)) + list(range(14, 18))              # 日曆 12、13 停牌
        arr, kind, init = Ym.f_one(bars, (o, h, l, c), 5, 17)
        # K 棒 b＝5..15 ⇒ 8,8,8,8,9.5,9.5,9.5,9.5,9.5,9.5,9.5（s＝11 的 9.0 較低 ⇒ 不退）；日曆 12、13 沿用 11；K 棒 12..15 ＝ 日曆 14..17
        want = [8, 8, 8, 8, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5, 9.5]
        add("F1 前低棘輪（PREREGD5）：低點 8（s＝2，確認於 4）；9.5（s＝7）在 s＋2＝9 才生效；較低的 9.0（s＝11）⛔ 不退；停牌日沿用",
            kind == "碎形" and init == 8.0 and np.array_equal(arr, np.array(want, float)), f"{arr.tolist()}")
        try:
            Ym.SF.fixtures(); ok = True
        except AssertionError as ex:
            ok = False
        add("F2 stop_fractal.fixtures()（PREREGD5 ①③）", ok)

    def t_time():
        valid = np.ones(NC, bool); valid[[10, 11]] = False        # 第 1～5 根 ＝ 日曆 5..9；第 m 根（m ≥ 6）＝ 日曆 m＋6 ⇒ 第 20 根 ＝ 26
        idx = np.flatnonzero(valid); k = int(np.searchsorted(idx, 4))
        c = np.full(NC, 9.5); c[5] = 10.0
        lv, st = Ym.time_levels(c, idx, k, 5, 90, 10.0, "R0", 20)
        pos = np.flatnonzero(np.isfinite(lv))
        add("H1 時停：第 20 根 ＝ 日曆 26（停牌 10、11 不數）；只在那一天有線（其餘 NaN）", st == "ok" and pos.tolist() == [26 - 5] and lv[21] == 10.0,
            f"{pos.tolist()}")
        # R0：第 20 根收盤恰 ＝ ep ⇒ 引擎 t＝27 開盤出；27 停牌 ⇒ 28 開盤出
        for halt27 in (False, True):
            o_ = np.full(NC, 10.0); c_ = c.copy(); c_[26] = 10.0; c_[27:] = 12.0; o_[27] = 10.2; o_[28] = 10.4
            o_[[10, 11]] = np.nan; c_[10] = c_[11] = c_[9]
            v = valid.copy()
            if halt27:
                o_[27] = np.nan; c_[27] = c_[26]; v[27] = False
            ix = np.flatnonzero(v)
            ln = (5, Ym.time_levels(c_, ix, int(np.searchsorted(ix, 4)), 5, 90, 10.0, "R0", 20)[0])
            o = run(R, [("A", 5, 90)], {"A": (o_, c_)}, 2, stop_line={("A", 5): ln}, stop_line_le=Ym.TIME_LE["R0"])
            sells = [(r["t"], r["px"]) for r in o["_audit"] if r["side"] == "sell"]
            exp = (28, 10.4) if halt27 else (27, 10.2)
            add(f"H2 引擎 R0-20：第 20 根（日曆 26）收盤恰 ＝ ep ⇒ {'27 停牌 ⇒ 28' if halt27 else '第 21 根 27'} 開盤出（「≤」）",
                sells[:1] == [exp], f"{sells}")
        # R10：找一個整數價 x 使 x×1.10 的浮點結果 ≠ 真值 1.1x（真值可表示）⇒ 線必須恰好 ＝ 1.1x；收盤恰 1.1x ⇒ 不觸發
        x = find_tick_mismatch(110, 10)
        w11 = x * 110 // 100
        lv, _ = Ym.time_levels(c, idx, k, 5, 90, x, "R10", 20)
        add(f"H3 R10 線 ＝ ep×110／100 恰好 {w11}（ep＝{x}；{x}×1.10 ＝ {x * 1.10!r} 會把「剛好漲 10%」判成沒反應）；「＜」",
            lv[21] == w11 and not (w11 < lv[21]) and ((w11 - 0.01) < lv[21]), f"{lv[21]!r}")
        # NH
        def nh(cb_vals, d):
            cc = np.full(NC, 9.0); ix = np.arange(NC); cc[5:5 + len(cb_vals)] = cb_vals
            return Ym.time_levels(cc, ix, 4, 5, 90, 10.0, "NH", d)[0][d - 1]
        a = [10.0] + [9.5, 10.0] + [9.8] * 17                   # 第 3 根平第 1 根（⛔ 不算創新高）
        b = list(a); b[14] = 10.5                                # 第 15 根創新高
        cse = [10.0] + [8.0 + 0.1 * i for i in range(19)]        # 第 2..20 根一路走高但沒超過第 1 根
        add("H4 NH-20：第 2..20 根沒有收盤 ＞ 第 1 根以來最高（平的不算）⇒ 必觸發（BIG）", nh(a, 20) == Ym.BIG, f"{nh(a, 20)!r}")
        add("H5 NH-20：第 15 根 10.5 創新高 ⇒ 無線（NaN）", np.isnan(nh(b, 20)))
        add("H6 NH-20：一路走高但沒超過第 1 根 ⇒ 仍是必觸發（新高是對第 1 根以來，⛔ 不是對前一根）", nh(cse, 20) == Ym.BIG)
        d40a = [10.0] * 19 + [11.0] + [10.5] * 20                # 事件在第 20 根（窗 21..40 之外）
        d40b = [10.0] * 20 + [11.0] + [10.5] * 19                # 事件在第 21 根
        add("H7 NH-40：事件在第 20 根 ⇒ 窗 21..40 內沒有 ⇒ 必觸發；事件在第 21 根 ⇒ 無線", nh(d40a, 40) == Ym.BIG and np.isnan(nh(d40b, 40)))
        cc = np.full(NC, 9.0); cc[5] = 10.0
        ln = (5, Ym.time_levels(cc, np.arange(NC), 4, 5, 90, 10.0, "NH", 20)[0])
        o_ = np.full(NC, 10.0); o_[25] = 8.8
        o = run(R, [("A", 5, 90)], {"A": (o_, cc)}, 2, stop_line={("A", 5): ln}, stop_line_le=Ym.TIME_LE["NH"])
        sells = [(r["t"], r["px"]) for r in o["_audit"] if r["side"] == "sell"]
        add("H8 引擎 NH-20：線 BIG ⇒ 第 21 根（日曆 25）開盤 8.8 出；（+∞ 會被引擎的 isfinite 擋掉 ⇒ 永不觸發）", sells[:1] == [(25, 8.8)], f"{sells}")
        o = run(R, [("A", 5, 90)], {"A": (o_, cc)}, 2, stop_line={("A", 5): (5, np.where(np.isfinite(ln[1]), np.inf, np.nan))})
        add("H9 引擎查證：線 ＝ +∞ 時引擎【不】觸發（所以 BIG 不是多此一舉）", [r["t"] for r in o["_audit"] if r["side"] == "sell"] == [90])

    def t_lookahead():
        rng = np.random.default_rng(20260926)
        bad = []
        for w in range(60):
            n = 160
            c = 10 * np.exp(np.cumsum(rng.normal(0, 0.03, n))); valid = rng.random(n) > 0.05; valid[:70] = True
            c = pd.Series(np.where(valid, c, np.nan)).ffill().to_numpy()
            idx = np.flatnonzero(valid); k = 60; e = int(idx[k + 1]); xp = min(n - 1, e + 80)
            m = int(rng.integers(e + 1, xp + 1))                 # 改第 m 天以後的收盤 ⇒ m 以前的線不可變
            c2 = c.copy(); c2[m:] *= np.exp(rng.normal(0, 0.2, n - m))
            idx2 = idx
            ma = {nn: (Ym.ma_valid(c, idx, nn), Ym.ma_valid(c2, idx2, nn)) for nn in (5, 20)}
            outs = []
            outs.append(("T20", Ym.t20_levels(c, valid, e, xp), Ym.t20_levels(c2, valid, e, xp)))
            for nn in (5, 20):
                for arm in Ym.ARMS:
                    outs.append((f"M{nn}{arm}", Ym.ma_levels(c, idx, ma[nn][0], k, e, xp, arm), Ym.ma_levels(c2, idx2, ma[nn][1], k, e, xp, arm)))
            for kind in Ym.TIME_DEFS:
                for d in (5, 20, 40):
                    outs.append((f"{kind}{d}", Ym.time_levels(c, idx, k, e, xp, 10.0, kind, d)[0], Ym.time_levels(c2, idx2, k, e, xp, 10.0, kind, d)[0]))
            lo_ = c * np.exp(-np.abs(rng.normal(0, 0.01, n))); lo2 = lo_.copy(); lo2[m:] = c2[m:] * 0.97
            bars = idx.tolist()
            f1 = Ym.f_one(bars, (c[idx], c[idx] * 1.01, lo_[idx], c[idx]), e, xp)[0]
            f2 = Ym.f_one(bars, (c2[idx], c2[idx] * 1.01, lo2[idx], c2[idx]), e, xp)[0]
            outs.append(("F", f1, f2))
            for nm, a1, a2 in outs:
                if not np.array_equal(a1[:m - e], a2[:m - e], equal_nan=True):
                    bad.append((w, nm))
        add("L1 無前視（60 個隨機世界 × T20／M5・M20 三種 arm／時停 R0・R10・NH × d5・20・40／F）：改第 m 天以後的價，m 以前的線逐位不變",
            not bad, f"變了 {bad[:6]}")

    for fn in (t_table, t_p15, t_t20, t_a3, t_ma, t_f, t_time, t_lookahead):
        safe(fn)
    return out


def fixtures():
    print("── fixtures：手算小例（引擎 ＝ git HEAD 的 research11.py）", flush=True)
    R = engine_head()
    base = hand(Y, R)
    for nm, ok, det in base:
        chk(nm, ok, det)
    print("── 突變體（每個都必須讓手算組至少一條失敗）", flush=True)
    caught = {}
    for tag in list(Y_MUT) + list(SF_MUT):
        res = hand(y_mut(tag), R)
        fails = [nm for nm, ok, _ in res if not ok]
        caught[tag] = fails
        chk(f"突變體 {tag} 被抓到", len(fails) > 0, f"失敗 {len(fails)} 條：{[f.split(' ')[0] for f in fails][:6]}")
    EXTRA["mutants"] = {k: [f.split(" ")[0] for f in v] for k, v in caught.items()}
    dump("fixtures", EXTRA)


# ─────────────────────────── 獨立寫法（純迴圈，照登錄文字）⇒ 真資料逐點比對
def wilder_ind(h, l, c, n=14, min_bars=114):
    m = len(c); tr = [0.0] * m; out = [float("nan")] * m
    for i in range(m):
        tr[i] = h[i] - l[i] if i == 0 else max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    if m < n:
        return np.array(out)
    a = sum(tr[:n]) / n; out[n - 1] = a
    for i in range(n, m):
        a = (a * (n - 1) + tr[i]) / n; out[i] = a
    for i in range(min(min_bars - 1, m)):
        out[i] = float("nan")
    return np.array(out)


def ind_t20(c, vset, e, xp):
    hi = -np.inf; out = []
    for d in range(e, xp + 1):
        if d in vset and c[d] > hi:
            hi = c[d]
        out.append(0.8 * hi)
    return np.array(out)


def ind_ma(c, vlist, k_cal, e, xp, n, arm):
    def ma_at(d):                                  # 最後一根 ≤ d 的有效 K 棒往回 n 根
        j = bisect.bisect_right(vlist, d) - 1
        if j - n + 1 < 0:
            return np.nan
        return sum(float(c[vlist[i]]) for i in range(j - n + 1, j + 1)) / n
    armed = arm == "state" or (arm == "cross_sig" and np.isfinite(ma_at(k_cal)) and c[k_cal] >= ma_at(k_cal))
    out = []; vs = set(vlist)
    for d in range(e, xp + 1):
        v = ma_at(d)
        if not armed and d in vs and np.isfinite(v) and c[d] >= v:
            armed = True
        out.append(v if armed else np.nan)
    return np.array(out)


def ind_a3(B, c_cal, k, e, xp, ep):
    atr = wilder_ind(B["h"], B["l"], B["c"]); idx = B["idx"]; pos = {int(p): j for j, p in enumerate(idx)}
    if not np.isfinite(atr[k]):
        return None
    cur = ep - 3.0 * atr[k]; hi = -np.inf; out = []
    for d in range(e, xp + 1):
        if d in pos:
            j = pos[d]; cj = float(c_cal[d])
            if cj > hi:
                hi = cj
                if np.isfinite(atr[j]):
                    cur = max(cur, cj - 3.0 * atr[j])
        out.append(cur)
    return np.array(out)


def ind_f(bars, o, h, l, c, e_pos, x_pos):
    """PREREGD5 §一 照字面重寫（⛔ 不呼叫 stop_fractal）。"""
    if e_pos not in bars:
        return None
    n = len(l); e = bars.index(e_pos); x = max(i for i, b in enumerate(bars) if b <= x_pos)
    def sw(s):
        return 2 <= s <= n - 3 and l[s] < l[s - 1] and l[s] < l[s - 2] and l[s] < l[s + 1] and l[s] < l[s + 2]
    stop = np.nan; last = -1
    for s in range(e - 2, max(0, e - 120) - 1, -1):          # 最近一個已確認（s＋2 ≤ e）、回看 120
        if sw(s):
            stop = l[s]; last = s; break
    if last < 0 and e >= 114:
        a = wilder_ind(h, l, c)[e - 1]
        stop = o[e] - 3 * a if np.isfinite(a) else np.nan
    per_bar = []
    for b in range(e, x + 1):
        s = b - 2
        if s > last and sw(s) and np.isfinite(stop) and l[s] > stop:
            stop = l[s]
        per_bar.append(stop)
    out = []; j = 0; cur = np.nan
    for d in range(e_pos, x_pos + 1):
        if j <= x - e and bars[e + j] == d:
            cur = per_bar[j]; j += 1
        out.append(cur)
    return np.array(out)


def ind_time(c, vlist, e, xp, ep, kind, d):
    out = np.full(xp - e + 1, np.nan)
    j0 = vlist.index(e)
    if j0 + d - 1 >= len(vlist):
        return out
    D = vlist[j0 + d - 1]
    if D + 1 >= xp:
        return out
    cb = [float(c[vlist[j0 + i]]) for i in range(d)]
    if kind == "R0":
        v = ep
    elif kind == "R10":
        v = ep * 1.1
    else:
        best = cb[0]; ev = []
        for m in range(1, d):
            ev.append(cb[m] > best); best = max(best, cb[m])
        win = ev[max(0, d - 20) - 1 if d > 20 else 0:]          # 第 max(2, d−19)..d 根
        v = np.nan if any(win) else Y.BIG
    out[D - e] = v
    return out


def q(x, ps=(10, 50, 90)):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if not len(x):
        return {}
    d = {f"p{p}": round(float(np.percentile(x, p)), 6) for p in ps}
    d["mean"] = round(float(x.mean()), 6); d["n"] = int(len(x))
    return d


def real():
    t0 = time.time()
    from backtest import research11 as R11
    ctx = L.setup_t1(lambda x: print("  " + x, flush=True))
    sig, opens, closes, cal, mk = ctx["sig"], ctx["opens"], ctx["closes"], ctx["cal"], ctx["mk"]
    cache = {}

    def bars_of(s):
        if s not in cache:
            cache[s] = R11.load_bars(s, mk.get(s, "twse"), cal)
        return cache[s]
    rows = list(Y._rows(sig))
    chk("訊號列（setup_t1）", True, f"{len(sig):,} 列／{sig['sid'].nunique():,} 檔；xpos_H120＜0 的 {sum(xp < 0 for *_, xp in rows)} 列")
    res = Y.build_all(sig, opens, closes, bars_of)
    print(f"  建線 {time.time() - t0:.0f}s", flush=True)
    stats = {}; per_row = {}
    # 有效 K 棒不一致（load_bars traded vs df 收盤有限；F 用後者）
    nd = 0
    for s in sorted(set(sig["sid"])):
        B = bars_of(s); v2 = np.flatnonzero(np.isfinite(B["df"]["close"].to_numpy(float)))
        nd += int(len(np.setxor1d(B["idx"], v2)))
    EXTRA["有效K棒兩種定義不同的根數（traded vs 收盤有限）"] = nd
    for name, (lines, skipped, ex) in res.items():
        fam = Y.fam_of(name); le = Y.FAMILIES[fam]["le"]
        recs = []; mism = 0; mono_bad = 0
        for sid, k, e, xp in rows:
            if xp < 0:
                continue
            key = (sid, e)
            ep = L.engine_ep(opens, closes, sid, e)
            B = bars_of(sid); idx = B["idx"]; c = np.asarray(closes[sid], float)
            r = {"sid": sid, "entry_pos": e, "xpos": xp, "ep": ep}
            if key not in lines:
                r["skip"] = ex.get("kinds", {}).get(key, "無線"); recs.append(r); continue
            st, lv = lines[key]
            L0 = float(lv[0])
            r.update({"L0": L0, "dist0": (1 - L0 / ep) if np.isfinite(L0) else np.nan,
                      "next_day": bool(np.isfinite(L0) and ((c[e] <= L0) if le else (c[e] < L0)))})
            tp = Y.first_trigger(lv, st, c, xp, le)
            r["trig_pos"] = tp
            r["trig_bar"] = int(np.searchsorted(idx, tp) - np.searchsorted(idx, e)) if tp >= 0 else -1
            # 族別的「進場時已知」距離
            if fam == "A3":
                a = R11.wilder_atr(B["h"], B["l"], B["c"])[k]; r["init_dist"] = 3 * a / ep
            elif fam == "F":
                r["kind"] = ex["kinds"][key]; r["init_dist"] = 1 - L0 / ep
            elif fam in ("M20", "M50"):
                n = int(fam[1:]); ma = Y.ma_valid(c, idx, n); r["init_dist"] = 1 - ma[k] / ep
                r["below_at_sig"] = bool(c[idx[k]] < ma[k]); r["below_at_entry"] = bool(c[e] < ma[k + 1])
            # 獨立版比對
            if fam == "P15":
                ref = np.full(xp - e + 1, ep * 0.85)
            elif fam == "T20":
                ref = ind_t20(c, set(idx.tolist()), e, xp)
            elif fam == "A3":
                ref = ind_a3(B, c, k, e, xp, ep)
            elif fam in ("M20", "M50"):
                ref = ind_ma(c, idx.tolist(), int(idx[k]), e, xp, int(fam[1:]), name.split(":")[1])
            else:
                bars, (o_, h_, l_, c_) = Y.f_ohlc(B)
                ref = ind_f(bars, o_, h_, l_, c_, e, xp)
            if ref is None or not np.allclose(lv, ref, rtol=1e-12, atol=0, equal_nan=True):
                mism += 1
            elif fam in ("T20", "A3", "F"):
                fin = lv[np.isfinite(lv)]
                mono_bad += int(np.any(np.diff(fin) < 0))
            recs.append(r)
        df = pd.DataFrame(recs); per_row[name] = recs
        have = df[df["L0"].notna()] if "L0" in df else df.iloc[0:0]
        s = {"lines": int(len(lines)), "rows": int(len(df)), "skipped": int(df["skip"].notna().sum()) if "skip" in df else 0,
             "skip_kinds": df["skip"].value_counts().to_dict() if "skip" in df else {},
             "no_line_at_entry": int((df["L0"].isna() & (df["skip"].isna() if "skip" in df else True)).sum()) if "L0" in df else 0,
             "dist0": q(have["dist0"]), "line_ge_ep": int((have["dist0"] <= 0).sum()),
             "next_day_share": float(have["next_day"].sum() / len(df)), "next_day_n": int(have["next_day"].sum()),
             "trig_price_share": float((df["trig_pos"] >= 0).sum() / len(df)) if "trig_pos" in df else 0.0,
             "trig_bar": q(df.loc[df["trig_pos"] >= 0, "trig_bar"]) if "trig_pos" in df else {},
             "sha": Y.lines_sha(lines), "indep_mismatch": mism, "ratchet_down_rows": mono_bad}
        if "init_dist" in df:
            s["init_dist"] = q(df["init_dist"])
        if fam == "F":
            s["kinds"] = df["kind"].value_counts().to_dict() if "kind" in df else {}
            for kd in ("碎形", "3×ATR"):
                s[f"init_dist_{kd}"] = q(df.loc[df.get("kind") == kd, "init_dist"])
        if fam in ("M20", "M50"):
            s["below_at_sig"] = int(df["below_at_sig"].sum()); s["below_at_entry"] = int(df["below_at_entry"].sum())
        stats[name] = s
        chk(f"{name}：與獨立迴圈版逐點相同（rtol 1e-12）", mism == 0, f"不同 {mism} 列")
        if fam in ("T20", "A3", "F"):
            chk(f"{name}：只升不降（真資料每條線）", mono_bad == 0, f"下降 {mono_bad} 列")
        print(f"  {name}｜線 {s['lines']}／略過 {s['skipped']}｜距離 {s['dist0']}｜隔天觸發 {s['next_day_share']:.4f}｜{time.time() - t0:.0f}s", flush=True)
    # P15 與 s1_lines(x=0.15) 的浮點寫法差：判法不同的列
    s1 = L.s1_lines(sig, "H120", opens, closes, x=0.15); p15 = res["P15"][0]; diff = []
    for key, (st, lv) in p15.items():
        xp = st + len(lv) - 1; c = np.asarray(closes[key[0]], float)
        if Y.first_trigger(lv, st, c, xp, True) != Y.first_trigger(s1[key][1], st, c, xp, True):
            diff.append(key)
    EXTRA["P15 兩種浮點寫法（ep×85/100 vs (1−0.15)×ep）觸發日不同的列"] = [list(map(str, k)) for k in diff]
    s1b = L.s1_lines(sig, "H120", opens, closes, x=0.10); d90 = 0
    for key, (st, lv) in s1b.items():
        xp = st + len(lv) - 1; c = np.asarray(closes[key[0]], float)
        alt = np.full(len(lv), Y.pct_of(L.engine_ep(opens, closes, key[0], key[1]), 90))
        d90 += Y.first_trigger(lv, st, c, xp, True) != Y.first_trigger(alt, st, c, xp, True)
    EXTRA["（旁查）已判過的 S1：(1−0.10)×ep 與 ep×90/100 觸發日不同的列"] = int(d90)
    chk("P15 浮點寫法：判法不同的列（描述）", True, f"{len(diff)} 列；旁查 S1 {d90} 列")
    # F 與 researchD5.build_lines 逐列相同（PREREGD5 原樣）
    try:
        from backtest import researchD5 as D5
        ohlc, idx_map = {}, {}
        for s in set(sig["sid"]):
            bars, o4 = Y.f_ohlc(bars_of(s)); idx_map[s] = bars; ohlc[s] = o4
        sg = sig[sig["xpos_H120"] >= 0]
        dl, dk = D5.build_lines(sg, ohlc, idx_map)
        fl = res["F"][0]
        same = set(dl) == set(fl) and all(dl[kk][0] == fl[kk][0] and np.array_equal(dl[kk][1], fl[kk][1], equal_nan=True) for kk in dl)
        chk("F：與 researchD5.build_lines（PREREGD5 原程式）逐列逐位相同", same, f"{len(dl)} 條")
    except Exception as ex:
        chk("F：researchD5.build_lines 對照（import 失敗 ⇒ 只有獨立版比對）", True, repr(ex)[:200])
    # 時停九格
    tstats = {}
    for kind in Y.TIME_DEFS:
        for d in Y.TIME_DS:
            lines, st = Y.time_lines(sig, opens, closes, bars_of, kind, d)
            le = Y.TIME_LE[kind]; trig = 0; mism = 0; n = 0; ret_at = []
            for sid, k, e, xp in rows:
                if xp < 0:
                    continue
                n += 1; stt, lv = lines[(sid, e)]; c = np.asarray(closes[sid], float); idx = bars_of(sid)["idx"]
                ep = L.engine_ep(opens, closes, sid, e)
                ref = ind_time(c, idx.tolist(), e, xp, ep, kind, d)
                if not np.allclose(lv, ref, rtol=1e-12, atol=0, equal_nan=True):
                    mism += 1
                tp = Y.first_trigger(lv, stt, c, xp, le)
                if tp >= 0:
                    trig += 1
            tstats[f"{kind}-{d}"] = {"rows": n, "status": st, "trig_share": trig / n, "trig_n": trig, "indep_mismatch": mism, "sha": Y.lines_sha(lines)}
            chk(f"時停 {kind}-{d}：與獨立迴圈版逐點相同", mism == 0, f"不同 {mism}；觸發 {trig}/{n} ＝ {trig / n:.4f}；{st}")
    EXTRA["time"] = tstats
    json.dump({"stats": stats, "time": tstats, "extra": {k: v for k, v in EXTRA.items() if k != "time"}},
              open(os.path.join(OUT, "lines_stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for name, recs in per_row.items():
        json.dump({"name": name, "le": Y.FAMILIES[Y.fam_of(name)]["le"], "sha": stats[name]["sha"], "rows": recs},
                  open(os.path.join(OUT, f"lines_{name.replace(':', '_')}.json"), "w", encoding="utf-8"), ensure_ascii=False, default=str)
    dump("real", {"engine_blob": EXTRA.get("engine_blob")})
    return ctx, bars_of


def pool(ctx=None, bars_of=None):
    from backtest import research11 as R11
    from backtest import research13 as R13
    if ctx is None:
        ctx = L.setup_t1(lambda x: print("  " + x, flush=True))
    RR = ctx["RR"]
    if bars_of is None:
        cache = {}

        def bars_of(s):
            if s not in cache:
                cache[s] = R11.load_bars(s, ctx["mk"].get(s, "twse"), ctx["cal"])
            return cache[s]
    Snd = pd.read_csv(os.path.join(OUT, Y.POOL_S), dtype={"sid": str})
    S0 = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "signals_S.csv.gz"), dtype={"sid": str})
    keep = Y.dedup20(Snd)
    Sd = Snd[keep]
    k1 = set(zip(Sd["sid"], Sd["k"])); k0 = set(zip(S0["sid"], S0["k"]))
    cols = [c for c in S0.columns if c in Sd.columns and c != "cell"]
    m = Sd.merge(S0, on=["sid", "k"], suffixes=("", "_0"))
    same_cols = all(((m[c] == m[c + "_0"]) | (m[c].isna() & m[c + "_0"].isna())).all() for c in cols if c not in ("sid", "k"))
    chk("ⓓ 不去重 S 套回 20 根去重 ⇒ 逐列重建 signals_S.csv.gz（sid、k 集合相同、其餘欄逐值相同）", k1 == k0 and same_cols,
        f"不去重 {len(Snd):,}｜去重後 {len(Sd):,}｜原 {len(S0):,}｜只在一邊 {len(k1 ^ k0)}")
    A = pd.read_csv(os.path.join(OUT, Y.POOL_AND), dtype={"sid": str})
    A0 = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), dtype={"sid": str})
    kA = set(zip(A["sid"], A["k"])) & k1
    chk("ⓓ 不去重 AND ∩ 去重鍵 ⇒ 逐列重建 and_signals.csv.gz", kA == set(zip(A0["sid"], A0["k"])), f"不去重 AND {len(A):,}｜重建 {len(kA):,}｜原 {len(A0):,}")
    P = Y.pool_rows(ctx)
    sig = ctx["sig"]
    kP = set(zip(P["sid"], P["k"])); kS = set(zip(sig["sid"], sig["k"]))
    Pm = P.merge(sig, on=["sid", "k"], suffixes=("", "_0"))
    sc = [c for c in ("pos", "entry_pos", "xpos_H120", "g_H120") if c in sig.columns]
    same = all(((Pm[c] == Pm[c + "_0"]) | (Pm[c].isna() & Pm[c + "_0"].isna())).all() for c in sc)
    chk(f"ⓓ 逐日池 ∩ 去重鍵 ＝ setup_t1 的 {len(sig):,} 列（{sc} 逐值相同）", (kP & k1) == kS and same, f"池 {len(P):,} 列／{P['sid'].nunique():,} 檔")
    w0, w1 = ctx["w0"], ctx["w1"]
    days = np.arange(w0, w1 + 1)
    use = P[P["xpos_H120"] >= 0]
    pn = np.bincount(use["entry_pos"].to_numpy() - w0, minlength=len(days))[:len(days)]
    sn = np.bincount(sig.loc[sig["xpos_H120"] >= 0, "entry_pos"].to_numpy() - w0, minlength=len(days))[:len(days)]
    has = sn > 0
    ratio = pn[has] / sn[has]
    ps = {"全部窗內交易日": q(pn), "有 v1 訊號的日子": q(pn[has]), "v1 訊號池（全部日）": q(sn), "v1 訊號池（有訊號日）": q(sn[has]),
          "逐日比 池／訊號（有訊號日）": q(ratio), "總列數比": float(pn.sum() / sn.sum()),
          "窗內交易日": int(len(days)), "v1 有訊號日": int(has.sum()), "池有候選日": int((pn > 0).sum()),
          "池有候選但 v1 沒訊號的日": int(((pn > 0) & ~has).sum()), "池列 xpos_H120＜0": int((P["xpos_H120"] < 0).sum()),
          "池列數": int(len(P)), "可用池列數": int(len(use))}
    # 池列建線（ⓓ 補進來的部位也要有線）：只報略過數
    # ⚠ setup_t1 的 closes／opens 只載了 v1 訊號的檔 ⇒ 池多出來的檔要補載（rerun17.load_prices 同一條；ⓓ 跑判定時 ctx 也要補）
    miss = sorted(set(use["sid"]) - set(ctx["closes"]))
    c2, o2 = RR.load_prices(miss, ctx["cal"], ctx["mk"], "branch") if miss else ({}, {})
    closes = {**ctx["closes"], **c2}; opens = {**ctx["opens"], **o2}
    ps["池比 v1 多出、setup_t1 沒載價的檔"] = len(miss)
    chk("ⓓ 池多出的檔補載價格（rerun17.load_prices、branch＝快照）", len(c2) == len(miss), f"{len(miss)} 檔")
    t0 = time.time()
    res = Y.build_all(use, opens, closes, bars_of, arms=("state",))
    ps["池列建線"] = {nm: {"lines": len(v[0]), "skipped": int(v[1]), "sha": Y.lines_sha(v[0])} for nm, v in res.items()}
    tl = {}
    for kind in Y.TIME_DEFS:
        for d in Y.TIME_DS:
            lines, st = Y.time_lines(use, opens, closes, bars_of, kind, d)
            tl[f"{kind}-{d}"] = {"lines": len(lines), "status": st}
    ps["池列時停建線"] = tl
    print(f"  池列建線 {time.time() - t0:.0f}s", flush=True)
    chk("ⓓ 逐日池大小（描述）", True, json.dumps({k: ps[k] for k in ("有 v1 訊號的日子", "逐日比 池／訊號（有訊號日）", "總列數比")}, ensure_ascii=False))
    json.dump(ps, open(os.path.join(OUT, "lines_pool_stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    dump("pool")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "fixtures"
    if stage in ("fixtures", "all"):
        fixtures(); RESULTS.clear()
    if stage in ("real", "all"):
        ctx, bo = real(); RESULTS.clear()
        if stage == "all":
            pool(ctx, bo); RESULTS.clear()
    if stage == "pool":
        pool()
