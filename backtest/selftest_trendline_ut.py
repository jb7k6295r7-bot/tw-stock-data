# -*- coding: utf-8 -*-
"""trendline_ut（上升趨勢線跌破）fixture ——全部要過，researchUT.py 才准跑。

 G1 ⭐ 鏡像對稱：價格以常數 K 反射（p′ ＝ K − p；high′ ＝ K − low）後，
    本支 close 版的 (甲)(乙)(丙) 事件（T、取點、確認日）＝ trendline_m 的下降線突破事件，逐筆相同（隨機序列 × R∈{3,5,10}；乙 的 2% 以超大容差同時關掉兩邊）
 G2 教科書上升線（PREREGM F1 的反射）：close／1% 穿越 抓在第 70 根、3 日 3% 抓在第 72 根；R＝3、10 同；日曆插洞 ⇒ T 對回日曆位置
 G3 門檻邊界：收盤恰 ＝ 0.99·ℓ 不算、低一點算；第三日恰 ＝ 0.97·ℓ 不算、低一點算；第二日站回線上 ⇒ 3 日 3% 不成立
 G4 實體穿線鏡像：取點之間（第 35 根，線 (30,50)）實體底低於線 ⇒ 甲不成立；只有影線穿 ⇒ 照抓；實體底恰 ＝ 線值不算穿
 G5 期限：確認＋60 抓、＋61 不抓；乙 第三點 2% 邊界（反射後分母 150：偏 3.00（恰 2%）採、3.01 不採）
 G6 ⭐ 前視突變：改 T 以後的價格（突變與截斷兩種）⇒ T 以前（含）事件與逐根現行線不變；甲乙 × R∈{3,5,10} × 兩判準、丙 × 兩判準
 G7 ⭐ 鑑別力：確認提早一根（lag＝R−1）⇒ 同一比法必須抓到差異；正式版 0
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import trendline_ut as UT
from backtest import trendline_m as TM
from backtest import selftest_trendline_m as STM

K = 250.0


def refl(o, h, l, c):
    """反射：p′ ＝ K − p ⇒ 上升線 ↔ 下降線；high′ ＝ K − low、low′ ＝ K − high。"""
    return K - o, K - l, K - h, K - c


def Ts(r):
    return [e["T"] for e in r["events"]]


def rand_ohlc(rng, m):
    r = rng.normal(0, 0.022, m)
    c = 100 * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.008, m))
    h = np.fmax(o, c) * np.exp(np.abs(rng.normal(0, 0.012, m)))
    l = np.fmin(o, c) * np.exp(-np.abs(rng.normal(0, 0.012, m)))
    return o, h, l, c


def g1():
    rng = np.random.default_rng(20260927)
    n_cmp = n_ev = 0
    old = TM.TOL3
    try:
        for k in range(8):
            o, h, l, c = rand_ohlc(rng, 900)
            o2, h2, l2, c2 = refl(o, h, l, c)
            for meth in ("甲", "乙"):
                for R in (3, 5, 10):
                    tol = 10.0 if meth == "乙" else None
                    if meth == "乙":
                        TM.TOL3 = 10.0
                    a = UT.detect_pivot(o, l, c, meth, R, "close", tol=tol)["events"]
                    b = TM.detect_pivot(o2, h2, c2, meth, R)["events"]
                    TM.TOL3 = old
                    assert [(e["T"], e["anchors"], e["conf"]) for e in a] == [(e["T"], e["anchors"], e["conf"]) for e in b], (k, meth, R)
                    n_cmp += 1; n_ev += len(a)
            a = UT.detect_reg(c, "close")["events"]; b = TM.detect_reg(c2)["events"]
            assert [e["T"] for e in a] == [e["T"] for e in b], (k, "丙")
            n_cmp += 1; n_ev += len(a)
    finally:
        TM.TOL3 = old
    assert n_ev > 100
    return "G1 鏡像對稱：反射價格後 close 版 甲乙丙 與 trendline_m 下降線突破逐筆相同（{} 組比對、{} 筆事件）".format(n_cmp, n_ev)


def textbook():
    o, h, l, c = STM.build(n_after=10)
    return refl(o, h, l, c)           # 上升線 ℓ′(t) ＝ K − line(t)；T＝70 收盤 ＝ ℓ′ − 2


def g2():
    o, h, l, c = textbook()
    assert list(np.flatnonzero(UT.pivot_lows(l, 5))) == [10, 30, 50]
    for rule, want in (("close", 70), ("pct1", 70), ("d3p3", 72)):
        A = UT.detect_pivot(o, l, c, "甲", 5, rule)["events"]
        assert A and A[0]["T"] == want and A[0]["anchors"] == (30, 50), (rule, A[:1])
        B = UT.detect_pivot(o, l, c, "乙", 5, rule)["events"]
        assert B and B[0]["T"] == want and B[0]["anchors"] == (10, 30, 50), (rule, B[:1])
        C = UT.detect_reg(c, rule)["events"]
        assert C and min(e["T"] for e in C) == want, (rule, C[:2])
        for R in (3, 10):
            assert Ts(UT.detect_pivot(o, l, c, "甲", R, rule))[:1] == [want], (rule, R)
    ins = lambda x: np.concatenate([x[:40], np.full(3, np.nan), x[40:]])
    rc = UT.detect_calendar(ins(o), ins(l), ins(c), "甲", 5, "pct1")
    assert Ts(rc)[:1] == [73] and rc["events"][0]["anchors"] == (30, 53), rc["events"][:1]
    return "G2 教科書（PREREGM F1 反射）：close／1% 抓在 70、3 日 3% 抓在 72（甲乙丙、R＝3、5、10）；日曆插洞 ⇒ 73、取點 (30,53)"


def g3():
    o, h, l, c = textbook()
    ell = lambda t: K - (125.0 - 0.5 * t)          # 上升線值
    for v, want in ((0.99 * ell(70), []), (0.99 * ell(70) - 0.01, [70])):
        cc = c.copy(); cc[70] = v; cc[71:] = ell(np.arange(71, len(c))) + 5      # 之後回到線上，避免後續觸發
        A = UT.detect_pivot(o, l, cc, "甲", 5, "pct1")["events"]
        assert [e["T"] for e in A][:1] == want, (v, A[:1])
    for v, want in ((0.97 * ell(72), []), (0.97 * ell(72) - 0.01, [72])):
        cc = c.copy(); cc[70] = ell(70) - 1; cc[71] = ell(71) - 1; cc[72] = v; cc[73:] = ell(np.arange(73, len(c))) + 5
        A = UT.detect_pivot(o, l, cc, "甲", 5, "d3p3")["events"]
        assert [e["T"] for e in A][:1] == want, (v, A[:1])
    cc = c.copy(); cc[70] = ell(70) - 1; cc[71] = ell(71) + 0.5; cc[72] = 0.9 * ell(72); cc[73:] = ell(np.arange(73, len(c))) + 5
    A = UT.detect_pivot(o, l, cc, "甲", 5, "d3p3")["events"]
    assert all(e["T"] != 72 for e in A), A
    return "G3 門檻：1% 恰 0.99·ℓ 不抓、再低 0.01 抓；3 日 3% 恰 0.97·ℓ 不抓、再低 0.01 抓；第二日站回線上 ⇒ 不成立"


def g4():
    o, h, l, c = textbook()
    ell = lambda t: K - (125.0 - 0.5 * t)
    ob, cb, lb = o.copy(), c.copy(), l.copy(); ob[35], cb[35] = ell(35) + 0.5, ell(35) - 0.2; lb[35] = cb[35] - 0.3
    assert list(np.flatnonzero(UT.pivot_lows(lb, 5))) == [10, 30, 50]
    r = UT.detect_pivot(ob, lb, cb, "甲", 5, "pct1", trace=True)
    assert r["why_at"][55] == "實體穿線", r["why_at"]
    ls = l.copy(); ls[35] = ell(35) - 0.2                        # 只有下影線穿
    assert list(np.flatnonzero(UT.pivot_lows(ls, 5))) == [10, 30, 50]
    assert Ts(UT.detect_pivot(o, ls, c, "甲", 5, "pct1"))[:1] == [70]
    oe, ce = o.copy(), c.copy(); oe[35], ce[35] = ell(35) + 0.5, ell(35)   # 實體底恰 ＝ 線值
    assert Ts(UT.detect_pivot(oe, l, ce, "甲", 5, "pct1"))[:1] == [70]
    return "G4 實體穿線（鏡像）：P2–P3 間實體底低於線 ⇒ 選取結果「實體穿線」；只有下影線穿 ⇒ 照抓；實體底恰 ＝ 線值 ⇒ 不算穿"


def g5():
    for Tb, want in ((115, [115]), (116, [])):
        o, h, l, c = refl(*STM.build(Tb=Tb))
        assert Ts(UT.detect_pivot(o, l, c, "甲", 5, "close")) == want, Tb
    o, h, l, c = textbook()
    got = {}
    for v in (101.0, 102.0, 102.01, 103.0):
        oo, hh0, ll0, cc0 = STM.build(); hh0 = hh0.copy(); hh0[50] = v
        o2, h2, l2, c2 = refl(oo, hh0, ll0, cc0)
        got[v] = Ts(UT.detect_pivot(o2, l2, c2, "乙", 5, "close"))
    # 反射後 2% 的分母是 ℓ′ ＝ K − 100 ＝ 150 ⇒ 門檻換算：|Δ| ≤ 3.0 ⇔ 原 high ∈ [97, 103]
    assert got == {101.0: [70], 102.0: [70], 102.01: [70], 103.0: [70]}, got
    oo, hh0, ll0, cc0 = STM.build(); hh0 = hh0.copy(); hh0[50] = 103.01
    o2, h2, l2, c2 = refl(oo, hh0, ll0, cc0)
    assert Ts(UT.detect_pivot(o2, l2, c2, "乙", 5, "close")) == []
    return "G5 期限：確認＋60 抓、＋61 不抓｜乙 2%（分母 ℓ(P3)＝150 ⇒ 偏 3.00 採、3.01 不採）"


def _cmp(full, part, T):
    ef = [(e["T"], e.get("anchors")) for e in full["events"] if e["T"] <= T]
    ep = [(e["T"], e.get("anchors")) for e in part["events"] if e["T"] <= T]
    if ef != ep:
        return False
    return full["trace"] is None or list(full["trace"][:T + 1]) == list(part["trace"][:T + 1])


def g6():
    rng = np.random.default_rng(11)
    n = 0; nev = 0
    for k in range(5):
        o, h, l, c = rand_ohlc(rng, 800)
        for meth in ("甲", "乙", "丙"):
            for R in ((3, 5, 10) if meth != "丙" else (5,)):
                for rule in UT.RULES:
                    run = (lambda oo, ll, cc: UT.detect_reg(cc, rule, trace=True)) if meth == "丙" else \
                          (lambda oo, ll, cc: UT.detect_pivot(oo, ll, cc, meth, R, rule, trace=True))
                    full = run(o, l, c); nev += len(full["events"])
                    for T in list(rng.integers(50, 790, 20)) + [e["T"] for e in full["events"][:5]]:
                        T = int(T)
                        o2, h2, l2, c2 = rand_ohlc(rng, 800); s = c[T] / c2[T]
                        om, lm, cm = o.copy(), l.copy(), c.copy()
                        om[T + 1:], lm[T + 1:], cm[T + 1:] = o2[T + 1:] * s, l2[T + 1:] * s, c2[T + 1:] * s
                        assert _cmp(full, run(om, lm, cm), T), ("突變", meth, R, rule, T)
                        assert _cmp(full, run(o[:T + 1], l[:T + 1], c[:T + 1]), T), ("前綴", meth, R, rule, T)
                        n += 2
    assert nev > 0
    return "G6 前視突變：{} 次比對（突變＋前綴）全相同；隨機序列事件 {} 筆".format(n, nev)


def g7():
    rng = np.random.default_rng(7)
    bad = good = n = 0
    for k in range(4):
        o, h, l, c = rand_ohlc(rng, 800)
        for R in (3, 5):
            piv = np.flatnonzero(UT.pivot_lows(l, R))
            for s in piv[:40]:
                T = int(s + R - 1)
                if T + 1 >= len(c):
                    continue
                lm = l.copy(); lm[T + 1] = l[s] * 0.5
                n += 1
                if not _cmp(UT.detect_pivot(o, l, c, "甲", R, "pct1", lag=R - 1, trace=True), UT.detect_pivot(o, lm, c, "甲", R, "pct1", lag=R - 1, trace=True), T):
                    bad += 1
                if not _cmp(UT.detect_pivot(o, l, c, "甲", R, "pct1", trace=True), UT.detect_pivot(o, lm, c, "甲", R, "pct1", trace=True), T):
                    good += 1
    assert bad > 0 and good == 0, (bad, good)
    return "G7 鑑別力：{} 次突變，破壞版（lag＝R−1）抓到 {} 次差異；正式版 0".format(n, bad)


def run_all():
    out = []
    for f in (g1, g2, g3, g4, g5, g6, g7):
        out.append(f()); print("✅", out[-1], flush=True)
    return out


if __name__ == "__main__":
    run_all()
    print("✅ trendline_ut fixture 全過")
