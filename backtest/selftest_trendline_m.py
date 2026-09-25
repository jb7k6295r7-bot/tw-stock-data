# -*- coding: utf-8 -*-
"""PREREGM 偵測器 fixture（backtest/trendline_m.py）——全部要過，researchM_freq.py 才准跑盤點。

 F1 教科書下降線＋收盤突破：(甲)(乙)(丙) 都抓得到、都抓在 T＝70；R＝3、10 同；日曆有洞時 T 對回正確日曆位置
 F2 實體穿線：P2–P3 之間實體穿 ⇒ (甲)(乙) 不成立；P1–P2 之間實體穿 ⇒ (乙) 不成立、(甲) 改用後一條線照抓；只有影線穿 ⇒ 照抓
 F3 平手高點不算樞紐（swing_lows 嚴格）⇒ 取點改變、(乙) 取點不足
 F4 (乙) 第三點：偏 2.00% 採、2.01%／3% 不採
 F5 期限：確認日＋60 那天突破 ⇒ 抓；＋61 ⇒ 不抓｜最早取點距確認日 120 ⇒ 成立；121 ⇒ 不成立
 F6 樞紐右 R 根未走完時不可被使用：現行線在確認日前一根仍是舊線、確認日當根收盤才換
 F7 ⭐ 前視突變：隨機改動 T 以後的價格（與截斷成前綴兩種）⇒ T 以前（含 T）的事件與逐根現行線完全不變；三畫法 × R∈{3,5,10}
 F8 ⭐ 測試分得出來（不假綠）：故意把確認提早一根（lag＝R−1）⇒ F7 的比法必須抓到差異；正確 lag 同一組突變 ⇒ 零差異
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import trendline_m as TM


def build(P=(10, 30, 50), Tb=70, n_after=10, a=125.0, slope=-0.5, kappa=1.0, gap=12.0, q=0.002):
    """手造一檔：線 line(t)＝a＋slope·t；t ≤ 最後樞紐：high＝line − κ·距最近樞紐（樞紐恰在線上、嚴格局部最高）；
    收盤＝ a − gap ＋ slope·t − q·t²（凹 ⇒ 回歸線外推永遠高於收盤 ⇒ (丙) 在 Tb 以前不會觸發）；開＝收＋0.5（實體頂＝開，遠在線下）；
    最後樞紐之後 high＝收＋1（嚴格遞減、無新樞紐）；Tb 收盤＝ line(Tb)＋2；之後逐根上漲。"""
    m = Tb + 1 + n_after
    t = np.arange(m, dtype=float)
    line = a + slope * t
    c = a - gap + slope * t - q * t * t
    o = c + 0.5
    P = np.array(P)
    dist = np.min(np.abs(t[:, None] - P[None, :]), axis=1)
    h = np.where(t <= P[-1], line - kappa * dist, c + 1.0)
    c[Tb] = line[Tb] + 2.0; o[Tb] = c[Tb - 1] + 0.5; h[Tb] = c[Tb] + 1.0
    for j in range(Tb + 1, m):
        c[j] = c[j - 1] + 1.0; o[j] = c[j] - 1.0; h[j] = c[j] + 1.0
    l = np.fmin(o, c) - 1.0
    assert np.all(h >= np.fmax(o, c) - 1e-12), "⛔ fixture 本身不合法：high < 實體頂"
    return o, h, l, c


def Ts(r):
    return [e["T"] for e in r["events"]]


def f1():
    o, h, l, c = build()
    assert list(np.flatnonzero(TM.pivot_highs(h, 5))) == [10, 30, 50], np.flatnonzero(TM.pivot_highs(h, 5))
    A = TM.detect_bars(o, h, c, "甲"); B = TM.detect_bars(o, h, c, "乙"); C = TM.detect_bars(o, h, c, "丙")
    assert Ts(A) == [70] and A["events"][0]["anchors"] == (30, 50), A["events"]
    assert Ts(B) == [70] and B["events"][0]["anchors"] == (10, 30, 50), B["events"]
    assert Ts(C)[:1] == [70] and min(Ts(C)) == 70, Ts(C)
    for R in (3, 10):
        assert Ts(TM.detect_bars(o, h, c, "甲", R)) == [70] and Ts(TM.detect_bars(o, h, c, "乙", R)) == [70], R
    # 日曆有洞：在第 40 根之前插 3 個 NaN 日 ⇒ T 的日曆位置 ＝ 73、取點 30→30、50→53
    ins = lambda x: np.concatenate([x[:40], np.full(3, np.nan), x[40:]])
    rc = TM.detect_calendar(ins(o), ins(h), ins(c), "甲")
    assert Ts(rc) == [73] and rc["events"][0]["anchors"] == (30, 53) and rc["events"][0]["T_bar"] == 70, rc["events"]
    rc = TM.detect_calendar(ins(o), ins(h), ins(c), "丙")
    assert min(Ts(rc)) == 73, Ts(rc)
    return "F1 教科書：甲 T＝70 取點(30,50)｜乙 T＝70 取點(10,30,50)｜丙 首筆 T＝70｜R＝3、10 同｜日曆插洞 ⇒ T 對到 73"


def f2():
    o, h, l, c = build()
    # A：第 31 根（P2–P3 之間）實體頂 109.7 > 線值 109.5，high 109.8 < 110（30 仍是樞紐）
    oa, ha, ca = o.copy(), h.copy(), c.copy(); oa[31], ca[31], ha[31] = 109.0, 109.7, 109.8
    assert list(np.flatnonzero(TM.pivot_highs(ha, 5))) == [10, 30, 50]
    assert Ts(TM.detect_bars(oa, ha, ca, "甲")) == [], "⛔ 甲：P1–P2 間實體穿線應不成立"
    assert Ts(TM.detect_bars(oa, ha, ca, "乙")) == [], "⛔ 乙：取點範圍內實體穿線應不成立"
    # B：第 11 根（乙 的 P1–P2 之間）實體穿 ⇒ 乙 不成立；甲 的 (10,30) 不成立、但 55 換成 (30,50) 照抓 70
    ob, hb, cb = o.copy(), h.copy(), c.copy(); ob[11], cb[11], hb[11] = 119.0, 119.7, 119.8
    assert list(np.flatnonzero(TM.pivot_highs(hb, 5))) == [10, 30, 50]
    rA = TM.detect_pivot(ob, hb, cb, "甲", trace=True)
    assert Ts(rA) == [70] and rA["trace"][35] is None and rA["trace"][55] == (30, 50), (Ts(rA), rA["trace"][35], rA["trace"][55])
    assert Ts(TM.detect_bars(ob, hb, cb, "乙")) == []
    # C：只有影線穿（第 31 根 high 109.9 > 線 109.5，實體在線下）⇒ 照抓
    hc = h.copy(); hc[31] = 109.9
    assert Ts(TM.detect_bars(o, hc, c, "甲")) == [70] and Ts(TM.detect_bars(o, hc, c, "乙")) == [70]
    # D：實體頂恰好等於線值 ⇒ 不算穿（「不可高於」）
    od, cd, hd = o.copy(), c.copy(), h.copy(); od[31], cd[31], hd[31] = 109.0, 109.5, 109.8
    assert Ts(TM.detect_bars(od, hd, cd, "甲")) == [70]
    return "F2 實體穿線：P2–P3 間穿 ⇒ 甲乙皆不成立｜P1–P2 間穿 ⇒ 乙不成立、甲換線照抓 70｜只穿影線 ⇒ 照抓｜實體頂＝線值 ⇒ 不算穿"


def f3():
    assert not TM.pivot_highs(np.array([1, 2, 3, 3, 2, 1, 0.]), 2).any(), "⛔ 平手高點不該是樞紐"
    assert list(np.flatnonzero(TM.pivot_highs(np.array([1, 2, 4, 3, 2, 1.]), 2))) == [2]
    o, h, l, c = build(); h = h.copy(); h[25] = 110.0          # 與 P＝30 平手
    assert list(np.flatnonzero(TM.pivot_highs(h, 5))) == [10, 50], np.flatnonzero(TM.pivot_highs(h, 5))
    A = TM.detect_bars(o, h, c, "甲")
    assert Ts(A) == [70] and A["events"][0]["anchors"] == (10, 50), A["events"]
    assert Ts(TM.detect_bars(o, h, c, "乙")) == [], "⛔ 只剩兩個樞紐，乙 應取點不足"
    return "F3 平手：[1,2,3,3,2,1] 無樞紐｜第 25 根與 30 平手 ⇒ 兩者都不是樞紐 ⇒ 甲取點變 (10,50)、乙取點不足"


def f4():
    o, h, l, c = build()
    got = {}
    for v in (101.0, 102.0, 102.01, 103.0):
        hh = h.copy(); hh[50] = v
        assert list(np.flatnonzero(TM.pivot_highs(hh, 5))) == [10, 30, 50]
        got[v] = Ts(TM.detect_bars(o, hh, c, "乙"))
    assert got == {101.0: [70], 102.0: [70], 102.01: [], 103.0: []}, got
    return "F4 乙 第三點：ℓ(P3)＝100；high(P3)＝101、102（恰 2%）採 ⇒ 抓 70｜102.01、103 不採 ⇒ 無事件"


def f5():
    # 期限 60：確認日 55 ⇒ 115 突破抓、116 不抓
    for Tb, want in ((115, [115]), (116, [])):
        o, h, l, c = build(Tb=Tb)
        assert Ts(TM.detect_bars(o, h, c, "甲")) == want, (Tb, Ts(TM.detect_bars(o, h, c, "甲")))
        assert Ts(TM.detect_bars(o, h, c, "乙")) == want, Tb
    # 跨度 120：P1＝10、P2＝125 ⇒ 確認 130、距 120 成立；P2＝126 ⇒ 121 不成立
    kw = dict(slope=-0.1, kappa=0.2, gap=15.0, q=0.0005)
    o, h, l, c = build(P=(10, 125), Tb=140, **kw)
    assert list(np.flatnonzero(TM.pivot_highs(h, 5))) == [10, 125]
    assert Ts(TM.detect_bars(o, h, c, "甲")) == [140]
    o, h, l, c = build(P=(10, 126), Tb=141, **kw)
    assert list(np.flatnonzero(TM.pivot_highs(h, 5))) == [10, 126]
    r = TM.detect_pivot(o, h, c, "甲")
    assert Ts(r) == [] and r["stats"]["選取結果"].get("跨度") == 1, r["stats"]
    return "F5 期限：確認＋60 抓、＋61 不抓（甲乙）｜最早取點距確認 120 成立、121 不成立（理由＝跨度）"


def f6():
    o, h, l, c = build()
    r = TM.detect_pivot(o, h, c, "甲", trace=True)
    tr = r["trace"]
    assert tr[34] is None and tr[35] == (10, 30), (tr[34], tr[35])        # 30 在 35 收盤才確認
    assert tr[54] == (10, 30) and tr[55] == (30, 50), (tr[54], tr[55])    # 50 在 55 收盤才確認
    r2 = TM.detect_pivot(o, h, c, "乙", trace=True)
    assert r2["trace"][54] is None and r2["trace"][55] == (10, 30, 50)
    # 截成只到第 54 根（50 右邊只走了 4 根）⇒ 50 不可能是樞紐、也不可被用
    assert not TM.pivot_highs(h[:55], 5)[50] and TM.detect_pivot(o[:55], h[:55], c[:55], "甲", trace=True)["trace"][54] == (10, 30)
    return "F6 右 R 根：樞紐 30 在第 35 根收盤才生效（34 仍無線）、50 在第 55 根才換線（54 仍是舊線）；截到 54 ⇒ 50 不是樞紐"


def rand_series(rng, m):
    r = rng.normal(0, 0.022, m)
    c = 100 * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]] * np.exp(rng.normal(0, 0.008, m))
    h = np.fmax(o, c) * np.exp(np.abs(rng.normal(0, 0.012, m)))
    return o, h, c


def _cmp(full, part, T, method):
    ef = [e for e in full["events"] if e["T"] <= T]; ep = [e for e in part["events"] if e["T"] <= T]
    if [(e["T"], e.get("anchors"), e.get("win0")) for e in ef] != [(e["T"], e.get("anchors"), e.get("win0")) for e in ep]:
        return False
    return list(full["trace"][:T + 1]) == list(part["trace"][:T + 1])


def _run(o, h, c, method, R, lag=None):
    if method == "丙":
        return TM.detect_reg(c, trace=True)
    return TM.detect_pivot(o, h, c, method, R, lag=lag, trace=True)


def f7(n_series=6, m=900, trials=40):
    rng = np.random.default_rng(20260925)
    n_ev = {}; n_cmp = 0
    for k in range(n_series):
        o, h, c = rand_series(rng, m)
        for method in TM.METHODS:
            for R in ((3, 5, 10) if method != "丙" else (5,)):
                full = _run(o, h, c, method, R)
                n_ev[(method, R)] = n_ev.get((method, R), 0) + len(full["events"])
                Tlist = list(rng.integers(0, m - 1, trials)) + [e["T"] for e in full["events"][:10]]
                for T in Tlist:
                    T = int(T)
                    o2, h2, c2 = rand_series(rng, m)
                    s = c[T] / c2[T]
                    om, hm, cm = o.copy(), h.copy(), c.copy()
                    om[T + 1:], hm[T + 1:], cm[T + 1:] = o2[T + 1:] * s, h2[T + 1:] * s, c2[T + 1:] * s
                    assert _cmp(full, _run(om, hm, cm, method, R), T, method), ("⛔ 前視：突變 T 以後改變了 T 以前", method, R, T)
                    assert _cmp(full, _run(o[:T + 1], h[:T + 1], c[:T + 1], method, R), T, method), ("⛔ 前視：前綴不同", method, R, T)
                    n_cmp += 2
    assert all(v > 0 for v in n_ev.values()), ("⛔ 隨機序列上沒有事件 ⇒ 測試沒有鑑別力", n_ev)
    return "F7 前視突變：{} 次比對（突變＋前綴）全相同；隨機序列上事件數 {}".format(
        n_cmp, "、".join("{}R{}={}".format(k[0], k[1], v) for k, v in sorted(n_ev.items())))


def f8(m=900):
    rng = np.random.default_rng(7)
    bad = good = n = 0
    for k in range(4):
        o, h, c = rand_series(rng, m)
        for R in (3, 5):
            piv = np.flatnonzero(TM.pivot_highs(h, R))
            for s in piv[:40]:
                T = int(s + R - 1)                       # 破壞版在這一根收盤就用了 s
                if T + 1 >= m:
                    continue
                hm = h.copy(); hm[T + 1] = h[s] * 1.5    # 改的是 T＋1（＝s＋R）⇒ s 不再是樞紐
                n += 1
                if not _cmp(_run(o, h, c, "甲", R, lag=R - 1), _run(o, hm, c, "甲", R, lag=R - 1), T, "甲"):
                    bad += 1
                if not _cmp(_run(o, h, c, "甲", R), _run(o, hm, c, "甲", R), T, "甲"):
                    good += 1
    assert bad > 0, "⛔ 破壞版（提早一根確認）沒被抓到 ⇒ F7 的比法沒有鑑別力"
    assert good == 0, "⛔ 正式版在同一組突變下出現差異"
    return "F8 鑑別力：同一組 {} 次突變，破壞版（lag＝R−1）被抓到 {} 次差異；正式版 0 次".format(n, bad)


def run_all():
    out = []
    for f in (f1, f2, f3, f4, f5, f6, f7, f8):
        out.append(f()); print("✅", out[-1], flush=True)
    return out


if __name__ == "__main__":
    run_all()
    print("✅ trendline_m fixture 全過")
