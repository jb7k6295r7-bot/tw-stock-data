# -*- coding: utf-8 -*-
"""PREREGU 偵測器 fixture（backtest/fib_u.py）——全部要過，researchU_freq.py／researchU.py 才准跑。

 F1 教科書回撤：L0＝99.5（第 10 根）、H0＝150.5（第 40 根）、確認於第 45 根；之後每根跌 1 ⇒ 七個位置抓在手算的那一根
    （30→55、38.2→59、45→62、50→65、55→68、61.8→71、70→75），p(x) 與手算差 < 1e-12；k＝3、10 同樣抓到（確認日隨 k 變）
 F2 門檻差一點：最低 low ＝ p(38.2)＋0.01 ⇒ 38.2 未觸及；＝ p(38.2) 恰好 ⇒ 觸及｜漲幅 19.9% ⇒ 不成波段、20.0% ⇒ 成｜
    t_H − t_L ＝ 9 ⇒ 不成、10 ⇒ 成｜[t_L, t_H] 內有更高的 high ⇒ 不成（H0 非頂）｜回看 121 根外的低點不用
 F3 確認前已觸及：[t_H, conf] 內 low 穿 p(30) ⇒ 30 不計、38.2 照抓｜確認日當根穿 ⇒ 也不計｜conf＋1 穿 ⇒ 計
 F4 同日穿多位置：一根跳空跌穿 30／38.2／45 ⇒ 三個位置同一個 T
 F5 失效：收盤 < L0 那一根的盤中觸及仍計、之後不計｜收盤 > H0 ⇒ 之後不計｜conf＋60 觸及 ⇒ 計、conf＋61 ⇒ 不計（逾60日）｜
    新合格波段確認 ⇒ 舊波段結束（被新波段取代），確認那一根的觸及歸舊波段
 F6 止跌反彈判定：反彈／沒止住／不分勝負、T 當日收盤就出帶、閉區間帶緣（恰好 1.05p 留在帶內）、缺收盤略過、T+21 不看；
    outcome_vec ＝ outcome（隨機 20,000 筆逐筆相同）；touches_many ＝ touches（隨機 300 檔 × 20 個位置逐筆相同）
 F7 日曆有洞：T／t_H／t_L／conf 對回正確日曆位置，且與無洞序列的有效 K 棒結果相同
 F8 ⭐ 前視突變：隨機改動 cut 以後的價格（與截斷成前綴兩種）⇒ conf ≤ cut 的波段（t_L、t_H、L0、H0、pre_min）與 T ≤ cut 的觸及
    完全不變；k ∈ {3,5,10} × 隨機 120 檔 × 每檔 4 個隨機 cut＋前 3 個波段的確認日
 F9 ⭐ 測試分得出來（不假綠）：故意把確認提早一根（lag＝k−1）⇒ F8 的比法必須抓到差異；正確 lag 同一組突變 ⇒ 零差異
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import fib_u as FU

L0_, H0_ = 99.5, 150.5


def build(L0=L0_, H0=H0_, tL=10, tH=40, after=None, n=110, bottom=113.5, rise_after=0.5, cf=0.5):
    """手造一檔（有效 K 棒序列）：low 在 tL 前每根 +1 遞減到 L0；tL→tH 線性升到 H0−1（high＝low＋1 ⇒ high(tH)＝H0）；
    tH 之後 low 每根 −1，直到 ≤ bottom 的那一根設成 bottom，之後每根 +rise_after。after：直接給 tH＋1 起的 low（覆蓋預設）。
    high＝low＋1、close＝low＋cf。"""
    l = np.zeros(max(n, tH + 1 + (0 if after is None else len(after))))
    for t in range(tL + 1):
        l[t] = L0 + (tL - t)
    for t in range(tL, tH + 1):
        l[t] = L0 + (t - tL) * (H0 - 1 - L0) / (tH - tL)
    if after is None:
        v = H0 - 1; hitb = False
        for t in range(tH + 1, n):
            if not hitb:
                v = v - 1.0
                if v <= bottom:
                    v = bottom; hitb = True
            else:
                v = v + rise_after
            l[t] = v
    else:
        after = np.asarray(after, float)
        l[tH + 1:tH + 1 + len(after)] = after
        l = l[:tH + 1 + len(after)]
    h = l + 1.0; c = l + cf
    return h, l, c


def P(x, L0=L0_, H0=H0_):
    return H0 - x * (H0 - L0)


def tmap(r):
    """detect_waves＋touches ⇒ {(wave, pos): (state, T)}。"""
    return {(t["wave"], t["pos"]): (t["state"], t["T"]) for t in r}


def run(h, l, c, k=5, **kw):
    r = FU.detect_waves(h, l, c, k, **kw)
    return r, FU.touches(r["waves"], l, FU.POS)


def f1():
    h, l, c = build()
    r, tc = run(h, l, c)
    W = r["waves"]
    assert len(W) == 1 and (W[0]["tL"], W[0]["tH"], W[0]["conf"]) == (10, 40, 45) and W[0]["L0"] == L0_ and W[0]["H0"] == H0_, W
    want = {"30": 55, "38.2": 59, "45": 62, "50": 65, "55": 68, "61.8": 71, "70": 75}
    got = {t["pos"]: t["T"] for t in tc}
    assert got == want, (got, want)
    for t in tc:
        assert abs(t["p"] - P(FU.POS[t["pos"]])) < 1e-12 and t["state"] == "觸及"
        assert l[t["T"]] <= t["p"] < l[t["T"] - 1], "⛔ 不是第一次觸及"
    for k in (3, 10):
        r2, tc2 = run(h, l, c, k)
        assert len(r2["waves"]) == 1 and r2["waves"][0]["conf"] == 40 + k, r2["waves"]
        assert {t["pos"]: t["T"] for t in tc2} == want
    return "F1 教科書七位置抓在 {}；k＝3／10 同（確認日 43／50）".format(want)


def f2():
    p38 = P(0.382)
    h, l, c = build(bottom=p38 + 0.01)
    _, tc = run(h, l, c); g = {t["pos"]: t["state"] for t in tc}
    assert g["30"] == "觸及" and g["38.2"] == "未觸及" and g["45"] == "未觸及", g
    h, l, c = build(bottom=p38)
    _, tc = run(h, l, c); g = {t["pos"]: t["state"] for t in tc}
    assert g["38.2"] == "觸及" and g["45"] == "未觸及", g
    # 漲幅 19.9% ／ 20.0%
    for H0, ok in ((L0_ * 1.199, False), (L0_ * 1.2, True)):
        h, l, c = build(H0=H0, bottom=L0_ + 2)
        r, _ = run(h, l, c)
        assert (len(r["waves"]) == 1) == ok, (H0, r["stats"])
        if not ok:
            assert r["stats"]["確認時判定"].get("漲幅<20%") == 1
    # 跨度 9 ／ 10
    for tH, ok in ((19, False), (20, True)):
        h, l, c = build(tH=tH, bottom=110)
        r, _ = run(h, l, c)
        assert (len(r["waves"]) == 1) == ok, (tH, r["stats"])
        if not ok:
            assert r["stats"]["確認時判定"].get("跨度<10") == 1
    # H0 非頂：在 [tL, tH] 中段放一根更高的 high（不成擺動高點以免多一個波段：只提高 high、左右都不動 ⇒ 它自己會是擺動高點，
    #   但它在 tH 之前確認，也會被判；本條只看 tH 那一個的判定理由）
    h, l, c = build()
    h[20] = H0_ + 5
    r, _ = run(h, l, c)
    assert all(w["tH"] != 40 for w in r["waves"]) and r["stats"]["確認時判定"].get("H0非頂", 0) >= 1, r
    # 回看 120：低點在 tH−121 ⇒ 不在範圍內 ⇒ 改用範圍內最低的擺動低點（或無）
    h, l, c = build(tL=10, tH=131, n=200, bottom=120)
    r, _ = run(h, l, c)
    assert len(r["waves"]) == 0 and r["stats"]["確認時判定"].get("無擺動低點") == 1, r["stats"]
    h, l, c = build(tL=10, tH=130, n=200, bottom=120)
    r, _ = run(h, l, c)
    assert len(r["waves"]) == 1 and r["waves"][0]["tL"] == 10, r
    return "F2 門檻：p(38.2)+0.01 抓不到／恰好抓到；漲幅 19.9% 不成／20% 成；跨度 9 不成／10 成；H0 非頂不成；回看 121 不用／120 用"


def f3():
    p30, p38 = P(0.30), P(0.382)
    for j, st in ((2, "確認前已觸及"), (5, "確認前已觸及"), (6, "觸及")):     # tH＋j；conf ＝ tH＋5
        h, l, c = build()
        l[40 + j] = p30 - 0.1; h[40 + j] = max(h[40 + j], l[40 + j] + 1); c[40 + j] = l[40 + j] + 0.5
        # 讓那一根只是影線：收盤拉回（避免收盤 < L0 等其他規則）
        c[40 + j] = l[40 + j] + 5
        r, tc = run(h, l, c)
        g = {t["pos"]: (t["state"], t["T"]) for t in tc}
        assert g["30"][0] == st, (j, g["30"])
        if st == "觸及":
            assert g["30"][1] == 46
        assert g["38.2"] == ("觸及", 59), g["38.2"]
    return "F3 確認前已觸及：tH＋2、tH＋5（確認當根）⇒ 30 不計；tH＋6 ⇒ 計；38.2 照抓在 59"


def f4():
    after = [149.5 - j for j in range(1, 15)] + [127.0 - j for j in range(0, 20)] + [108 + 0.5 * j for j in range(30)]
    h, l, c = build(after=after)
    _, tc = run(h, l, c)
    g = {t["pos"]: t["T"] for t in tc}
    assert g["30"] == g["38.2"] == g["45"] == 55 and g["50"] == 55 + 2, g
    return "F4 跳空一根跌穿 30／38.2／45 ⇒ 同一個 T＝55"


def f5():
    msgs = []
    # (a) 收盤 < L0 那一根：盤中觸及 70 仍計；之後不計
    after = [149.5 - j for j in range(1, 30)] + [L0_ - 10] + [L0_ - 12 + 0.2 * j for j in range(30)]
    h, l, c = build(after=after)
    c[40 + 30] = L0_ - 5                             # 那一根收盤 < L0
    r, tc = run(h, l, c)
    W = r["waves"][0]
    assert W["why_end"] == "收盤<L0" and W["end"] == 70, W
    g = {t["pos"]: (t["state"], t["T"]) for t in tc}
    assert g["70"] == ("觸及", 70) and g["61.8"] == ("觸及", 70), g
    msgs.append("收盤<L0 當根觸及仍計")
    # (b) 收盤 > H0 ⇒ 之後不計
    after = [149.5 - j for j in range(1, 12)] + [139 + 2 * j for j in range(1, 10)] + [150 - j for j in range(40)]
    h, l, c = build(after=after)
    r, tc = run(h, l, c)
    W = [w for w in r["waves"] if w["tH"] == 40][0]
    assert W["why_end"] == "收盤>H0", W
    g = {t["pos"]: t for t in tc if t["wave"] == r["waves"].index(W)}
    assert g["30"]["state"] == "未觸及" and all(v["state"] != "觸及" for v in g.values()), g
    msgs.append("收盤>H0 後不計")
    # (c) conf＋60 觸及 ⇒ 計；conf＋61 ⇒ 不計
    for j, ok in ((65, True), (66, False)):
        after = [149.5 - 0.1 * i for i in range(1, 80)]
        after[j - 1] = P(0.30) - 0.01
        h, l, c = build(after=after)
        c[40 + j] = P(0.30) + 3; h[40 + j] = c[40 + j] + 1   # 影線
        r, tc = run(h, l, c)
        g = {t["pos"]: t for t in tc}
        assert (g["30"]["state"] == "觸及") == ok and (not ok or g["30"]["T"] == 105), (j, g["30"], r["waves"])
        assert r["waves"][0]["why_end"] == "逾60日" and r["waves"][0]["end"] == 105
    msgs.append("conf＋60 計／＋61 不計")
    # (d) 被新波段取代：回檔到 ~128 後再漲、high 過 H0 但收盤不過 H0 ⇒ 新擺動高點確認且合格 ⇒ 舊波段結束
    dn = [149.5 - j for j in range(1, 23)]                   # 到 127.5（觸及 30、38.2、45）
    up = [127.5 + 1.2 * j for j in range(1, 20)]             # 升到 150.3
    top = [150.5]                                            # high＝151.5 > H0；收盤另設 < H0
    dn2 = [149.0 - j for j in range(1, 30)]
    after = dn + up + top + dn2
    h, l, c = build(after=after)
    c = np.minimum(c, H0_ - 0.2)                             # 收盤一律 ≤ H0（不觸發收盤 > H0）
    r, tc = run(h, l, c)
    tH2 = 40 + len(dn) + len(up) + 1
    assert len(r["waves"]) == 2 and r["waves"][0]["why_end"] == "被新波段取代" and r["waves"][0]["end"] == tH2 + 5 \
        and r["waves"][1]["tH"] == tH2 and r["waves"][1]["conf"] == tH2 + 5, r["waves"]
    g1 = {t["pos"]: t["T"] for t in tc if t["wave"] == 1}
    assert all(T is None or T > tH2 + 5 for T in g1.values()), g1
    msgs.append("新合格波段取代舊波段（舊波段 end＝新確認根）")
    return "F5 失效：" + "、".join(msgs)


def f6():
    p = 100.0
    O = FU.outcome
    assert O(np.array([100, 102, 105.01, 90] + [100] * 30), 0, p) == (1, 2)
    assert O(np.array([100, 96, 94.99, 120] + [100] * 30), 0, p) == (0, 2)
    assert O(np.array([100] * 21 + [200] * 5), 0, p) == (-1, None), "⛔ T+21 不看"
    assert O(np.array([106.0] + [100] * 30), 0, p) == (1, 0), "T 當日收盤就出帶"
    assert O(np.array([p * 1.05, p * 0.95] + [100] * 30), 0, p) == (-1, None), "閉區間帶緣留在帶內"
    assert O(np.array([100, np.nan, np.nan, 94] + [100] * 30), 0, p) == (0, 3), "缺收盤略過"
    rng = np.random.default_rng(3)
    n = 400; worst = 0
    for _ in range(50):
        c = 100 * np.exp(rng.normal(0, 0.03, n).cumsum()); c[rng.random(n) < 0.05] = np.nan
        T = rng.integers(0, n - 21, 400); pp = c[T] * np.exp(rng.normal(0, 0.05, 400)); pp[~np.isfinite(pp)] = 100
        v = FU.outcome_vec(c, T, pp)
        s = np.array([O(c, int(t), float(q))[0] for t, q in zip(T, pp)])
        worst += int((v != s).sum())
        for band, hold in ((0.03, 10), (0.08, 40)):
            T2 = T[T < n - 41]; p2 = pp[T < n - 41]
            v = FU.outcome_vec(c, T2, p2, hold, band); s = np.array([O(c, int(t), float(q), hold, band)[0] for t, q in zip(T2, p2)])
            worst += int((v != s).sum())
    assert worst == 0, worst
    # touches_many ＝ touches
    bad = 0; nwv = 0
    fr = np.r_[np.array(list(FU.POS.values())), rng.uniform(0.15, 0.85, 13)]
    names = {str(i): float(x) for i, x in enumerate(fr)}
    for s in range(300):
        h, l, c = rand_series(np.random.default_rng(500 + s))
        r = FU.detect_waves(h, l, c, 5)
        T, PP = FU.touches_many(r["waves"], l, fr)
        tc = FU.touches(r["waves"], l, names)
        nwv += len(r["waves"])
        for t in tc:
            i = int(t["pos"]); want = t["T"] if t["state"] == "觸及" else -1
            bad += int(T[i, t["wave"]] != want) + int(abs(PP[i, t["wave"]] - t["p"]) > 0)
    assert bad == 0 and nwv > 100, (bad, nwv)
    return "F6 判定：反彈／沒止住／不分勝負／T 當日／閉區間帶緣／缺收盤／T+21 不看；outcome_vec＝outcome 20,000＋筆差 0；touches_many＝touches（300 檔 {} 波段 × 20 位置）差 0".format(nwv)


def rand_series(rng, n=600):
    c = 50 * np.exp(rng.normal(0, 0.03, n).cumsum())
    h = c * (1 + np.abs(rng.normal(0, 0.012, n))); l = c * (1 - np.abs(rng.normal(0, 0.012, n)))
    return h, l, c


def f7():
    h, l, c = build()
    n = len(c) + 12
    holes = np.array([3, 15, 16, 41, 60, 61, 62, 63, 80, 90, 100, 101])
    keep = np.setdiff1d(np.arange(n), holes)
    H = np.full(n, np.nan); L = np.full(n, np.nan); C = np.full(n, np.nan)
    H[keep] = h; L[keep] = l; C[keep] = c
    r = FU.detect_calendar(H, L, C)
    W = r["waves"][0]
    assert (W["tL"], W["tH"], W["conf"]) == (keep[10], keep[40], keep[45])
    want = {"30": 55, "38.2": 59, "45": 62, "50": 65, "55": 68, "61.8": 71, "70": 75}
    got = {t["pos"]: t["T"] for t in r["touches"]}
    assert got == {k: int(keep[v]) for k, v in want.items()}, (got,)
    return "F7 日曆 12 個洞：t_L／t_H／conf／七個 T 都對回正確日曆位置"


def snap(r, tc, cut):
    """cut 以前（含）可知的部分：conf ≤ cut 的波段（不含 end）與 T ≤ cut 的觸及；end < cut 的波段連 end 一起比。"""
    ws = []
    for i, W in enumerate(r["waves"]):
        if W["conf"] <= cut:
            ws.append((W["tL"], W["tH"], W["conf"], W["L0"], W["H0"], W["pre_min"], (W["end"], W["why_end"]) if W["end"] < cut else None))
    key = {i: (W["tH"], W["conf"]) for i, W in enumerate(r["waves"])}
    ts = sorted((key[t["wave"]], t["pos"], t["T"]) for t in tc if t["T"] is not None and t["T"] <= cut)
    pre = sorted((key[t["wave"]], t["pos"]) for t in tc if t["state"] == "確認前已觸及" and r["waves"][t["wave"]]["conf"] <= cut)
    return ws, ts, pre


def mutation(lag_off=0, n_series=120):
    diff = 0; checks = 0; n_touch = 0
    for k in (3, 5, 10):
        for s in range(n_series):
            rng = np.random.default_rng(10_000 * k + s)
            h, l, c = rand_series(rng)
            lag = k - lag_off
            r0 = FU.detect_waves(h, l, c, k, lag=lag); t0 = FU.touches(r0["waves"], l, FU.POS)
            n_touch += sum(t["T"] is not None for t in t0)
            cuts = list(rng.integers(100, len(c) - 20, 4)) + [W["conf"] for W in r0["waves"][:3] if 100 <= W["conf"] < len(c) - 20]
            for cut in cuts:
                a = snap(r0, t0, cut)
                h2, l2, c2 = h.copy(), l.copy(), c.copy()
                f = np.exp(rng.normal(0, 0.08, len(c) - cut - 1))
                c2[cut + 1:] *= f; h2[cut + 1:] = c2[cut + 1:] * (1 + np.abs(rng.normal(0, 0.03, len(f))))
                l2[cut + 1:] = c2[cut + 1:] * (1 - np.abs(rng.normal(0, 0.03, len(f))))
                r1 = FU.detect_waves(h2, l2, c2, k, lag=lag); t1 = FU.touches(r1["waves"], l2, FU.POS)
                r2 = FU.detect_waves(h[:cut + 1], l[:cut + 1], c[:cut + 1], k, lag=lag); t2 = FU.touches(r2["waves"], l[:cut + 1], FU.POS)
                b = snap(r1, t1, cut); d = snap(r2, t2, cut)
                # 截斷成前綴：end < cut 的波段在前綴裡的 end 可能被「資料尾」截 ⇒ 前綴只比 end 以外的欄
                strip = lambda z: ([w[:6] for w in z[0]], z[1], z[2])
                diff += int(a != b) + int(strip(a) != strip(d))
                checks += 2
    return diff, checks, n_touch


def f8_f9():
    d0, n0, nt = mutation(0)
    assert d0 == 0, "⛔ 前視突變：正確 lag 下 cut 以前的波段／觸及變了 {}／{}".format(d0, n0)
    d1, n1, _ = mutation(1)
    assert d1 > 0, "⛔ 測試沒有鑑別力：lag＝k−1 也全過"
    return ("F8 前視突變：k∈{{3,5,10}} × 120 檔 × （4 個隨機 cut＋前 3 個波段的確認日）（突變＋截斷兩種，共 {} 次比對、觸及 {} 筆）差 0｜"
            "F9 鑑別力：確認提早一根（lag＝k−1）同一組比對抓到 {} 次差異").format(n0, nt, d1)


def run_all():
    out = []
    for f in (f1, f2, f3, f4, f5, f6, f7, f8_f9):
        m = f(); print("✅ " + m, flush=True); out.append(m)
    return out


if __name__ == "__main__":
    run_all()
    print("✅ selftest_fib_u：全部通過")
