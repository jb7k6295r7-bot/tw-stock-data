# -*- coding: utf-8 -*-
"""researchMACDBoll 自測（合成 fixture；⛔ 不讀任何報酬）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMACDBoll_check
涵蓋：① MACD 柱翻正（EMA 對手算、≤0 邊界）、② 布林上下軌同時往外開（嚴格、ddof=0）、②另一讀法 1.10 含等號、③ 站上上揚 MA20（相等不算）、
      KD（手算 RSV／K／D、無區間 RSV＝50、K<50 嚴格、黃金交叉）、壞根切段（暖機 60 根）、出場（跌破 MA20／MA20 下彎／停損 3% 先到、同日多因、
      停損含等號、壞根強制出、賣出根跨壞根、同根兩價取較低 seq373、下市、資料尾）、加碼（一次、出場日不加、被擋等下一個、拿掉加碼）、
      空手一天（持有中／空手日／被 entry_flag 擋的不佔位）、組合層（5 份、每份 1、加碼佔份、沒份不加、名額不足日、抽籤可重現、空手一天）、
      等價自查（條件比例、Jaccard）、PIT（改未來不影響過去）、閘門（正式跑拒跑）、登錄 sha、已產出檔無報酬欄、突變（翻正 <0、開口 ≥、停損 <、空手 0、K≤50）。
fixture 數值：價格用整數或 2 的冪分數（〈一百二十一〉）；EMA、0.97 這類換數字也做不到的，與同式手算比（〈一百三十三〉②）。
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchMACDBoll as M   # noqa: E402

RES = []


def ok(name, cond, info=""):
    RES.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"｜{info}" if info and not cond else ""), flush=True)


# ── ① MACD ───────────────────────────────────────────
def t_macd():
    rng = np.random.default_rng(7)
    c = 64.0 + np.cumsum(rng.integers(-4, 5, 200)) / 4.0
    def ema_hand(x, n):
        a = 2.0 / (n + 1); y = np.empty(len(x)); y[0] = x[0]
        for k in range(1, len(x)):
            y[k] = a * x[k] + (1 - a) * y[k - 1]
        return y
    dif = ema_hand(c, 12) - ema_hand(c, 26); hist = dif - ema_hand(dif, 9)
    ok("MACD 柱 ＝ 手算 EMA12−EMA26−EMA9（遞迴，容差 1e−12）", np.max(np.abs(M.macd_hist(c) - hist)) < 1e-12)
    h = np.array([-1.0, 0.0, 1.0, 2.0, -1.0, 1.0, 0.0, 0.5])
    tp = M.turn_pos(h)
    ok("翻正：柱(t−1)＝0 也算（≤0）、柱(t)＝0 不算", tp.tolist() == [False, False, True, False, False, True, False, True])
    mut = np.r_[False, (h[1:] > 0) & (h[:-1] < 0)]                    # 突變：前一根嚴格 <0
    ok("突變（前一根 <0）會被 fixture 抓到", mut.tolist() != tp.tolist())


# ── ② 布林 ───────────────────────────────────────────
def t_boll():
    c = np.array([float(x) for x in range(1, 41)])
    ma, ub, lb = M.boll(c)
    k = 25
    w = c[k - 19:k + 1]
    ok("布林中軌 MA20、ddof=0（np.std）", abs(ma[k] - w.mean()) < 1e-12 and abs(ub[k] - (w.mean() + 2 * w.std())) < 1e-12 and np.isnan(ma[18]) and np.isfinite(ma[19]))
    ub = np.array([1.0, 2.0, 3.0, 3.0, 4.0]); lb = np.array([0.0, -1.0, -1.0, -2.0, -3.0])
    wd = M.widen(ub, lb)
    ok("開口：上下軌都外開才算；上軌持平或下軌持平都不算", wd.tolist() == [False, True, False, False, True])
    mut = np.r_[False, (ub[1:] >= ub[:-1]) & (lb[1:] <= lb[:-1])]
    ok("突變（≥／≤）會被 fixture 抓到", mut.tolist() != wd.tolist())
    ub = np.array([2.0] * 5 + [2.0, 2.2, 2.25]); lb = np.zeros(8); ma = np.ones(8)
    bw_ok = (ub[5:] - lb[5:]) / ma[5:] >= 1.10 * (ub[:3] - lb[:3]) / ma[:3]
    ok("另一讀法開口：帶寬 ≥ 1.10 × 5 根前（含等號依同式手算）", M.widen_alt(ub, lb, ma).tolist() == [False] * 5 + bw_ok.tolist() and bool(M.widen_alt(ub, lb, ma)[7]) and not M.widen_alt(ub, lb, ma)[5])


# ── ③ 站上上揚 MA20 ───────────────────────────────────
def t_above():
    ma = np.array([10.0, 10.0, 11.0, 12.0, 12.0])
    c = np.array([11.0, 11.0, 11.0, 13.0, 13.0])
    ok("③：收盤＝MA 不算、MA 持平不算", M.above_rising(c, ma).tolist() == [False, False, False, True, False])


# ── KD ──────────────────────────────────────────────
def t_kd():
    c = np.array([8.0, 9, 10, 9, 8, 7, 8, 9, 10, 12, 11, 12, 12, 12, 12, 12, 12, 12, 12, 12])
    h = c + 1; l = c - 1
    K, D = M.kd(c, h, l)
    kp = dp = 50.0; Kh = np.full(len(c), np.nan); Dh = np.full(len(c), np.nan)
    for t in range(8, len(c)):
        hh = h[t - 8:t + 1].max(); ll = l[t - 8:t + 1].min()
        rsv = 50.0 if hh == ll else (c[t] - ll) / (hh - ll) * 100
        kp = kp * 2 / 3 + rsv / 3; dp = dp * 2 / 3 + kp / 3; Kh[t] = kp; Dh[t] = dp
    ok("KD 手算（9 日 RSV、1/3 平滑、前值 50）", np.nanmax(np.abs(K - Kh)) < 1e-12 and np.isnan(K[7]) and np.isfinite(K[8]) and np.allclose(D[8:], Dh[8:], atol=1e-12))
    c2 = np.full(12, 5.0); K2, _ = M.kd(c2, c2, c2)
    ok("KD 無區間 ⇒ RSV＝50 ⇒ K 恆 50", np.allclose(K2[8:], 50.0))
    Ka = np.array([10.0, 30, 60, 10, 50, 20, 49]); Da = np.array([20.0, 25, 40, 20, 40, 30, 40])
    g = M.kd_gc(Ka, Da)
    ok("KD 黃金交叉且 K<50（K＝50 不算、K＞D 已在上方不算）", g.tolist() == [False, True, False, False, False, False, True])
    mut = np.r_[False, (Ka[1:] > Da[1:]) & (Ka[:-1] <= Da[:-1]) & (Ka[1:] <= 50)]
    ok("突變（K≤50）會被 fixture 抓到", mut.tolist() != g.tolist())


# ── 特徵、壞根切段、PIT ──────────────────────────────
def path(n=300, seed=3):
    rng = np.random.default_rng(seed)
    return 64.0 + np.cumsum(rng.integers(-3, 4, n)) / 4.0


def t_features():
    for sd in range(3, 200):                                            # 決定式：第一個有三條件同日訊號的種子
        c = path(seed=sd); h = c + 0.5; l = c - 0.5
        F = M.seg_features(c, h, l)
        if (F["C1"] & F["C2"] & F["C3"]).any():
            break
    ok("暖機：索引 < 60 不可判、不出訊號", (not F["J"][59]) and F["J"][60] and not (F["C1"][:60] | F["C2"][:60] | F["C3"][:60]).any())
    bad = np.zeros(len(c), bool); bad[150] = True
    S = M.stock_features(c, h, l, None, bad)
    ok("壞根切段：壞根當根起 60 根內不可判", (not S["J"][150:210].any()) and S["J"][210] and S["J"][149])
    sig = F["C1"] & F["C2"] & F["C3"]
    ok("fixture 有三條件同日訊號（否則下面 PIT 測不到）", sig.sum() >= 1, f"{sig.sum()}")
    k = int(np.flatnonzero(sig)[0]) if sig.any() else 200
    c2 = c.copy(); c2[k + 1:] = c2[k + 1:] * 2 + 7; h2 = c2 + 0.5; l2 = c2 - 0.5
    F2 = M.seg_features(c2, h2, l2)
    same = all(np.array_equal(F[x][:k + 1], F2[x][:k + 1]) for x in ("C1", "C2", "C3", "XB", "XD", "GC"))
    ok("PIT：改 t 之後的價格，t 以前的條件與出場狀態不變", same)


# ── 出場與加碼 ───────────────────────────────────────
def mk(n=40):
    c = np.full(n, 100.0); o = np.full(n, 100.0); xb = np.zeros(n, bool); xd = np.zeros(n, bool); gc = np.zeros(n, bool); bad = np.zeros(n, bool)
    return c, o, xb, xd, gc, bad


def yes(k, a):
    return True


def t_exit():
    c, o, xb, xd, gc, bad = mk(); n = len(c); e = 5
    xb[9] = True; xd[11] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("先到者：跌破 MA20 在 9 ⇒ 10 開盤賣", X["x"] == 10 and X["kind"] == "open" and X["reason"] == "跌破MA20" and X["done"])
    c, o, xb, xd, gc, bad = mk(); xb[9] = True; xd[9] = True; c[9] = o[e] * M.STOP
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("同日多因 ⇒ 原因記組合", X["reason"] == "跌破MA20+MA20下彎+停損3%" and X["x"] == 10)
    c, o, xb, xd, gc, bad = mk(); c[8] = o[e] * M.STOP
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("停損含等號（收盤 ＝ 0.97×首次進場價）", X["d"] == 8 and X["reason"] == "停損3%")
    c, o, xb, xd, gc, bad = mk(); c[8] = np.nextafter(o[e] * M.STOP, 1e9)
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("停損：差一個 ulp 以上不觸發（突變 < 會被抓到：等號那一格）", X["d"] is None and X["reason"] == "資料尾未出" and not X["done"])
    c, o, xb, xd, gc, bad = mk(); c[e] = o[e] * M.STOP
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("進場當天收盤即觸發 ⇒ 次日開盤賣", X["d"] == e and X["x"] == e + 1)
    c, o, xb, xd, gc, bad = mk(); bad[12] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("未觸發遇壞根 ⇒ 壞根前一根收盤強制出", X["x"] == 11 and X["kind"] == "close" and X["reason"] == "壞根前強制出")
    c, o, xb, xd, gc, bad = mk(); xb[11] = True; bad[12] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("觸發後下一根是壞根 ⇒ 觸發日收盤強制出", X["x"] == 11 and X["kind"] == "close" and X["reason"].endswith("壞根前強制出"))
    c, o, xb, xd, gc, bad = mk(); xb[10] = True; bad[12] = True; o[11] = 104.0; c[11] = 96.0
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("seq373：賣出根同時是壞根前強制收盤根 ⇒ minoc（取較低）", X["x"] == 11 and X["kind"] == "minoc" and "同根取較低" in X["flags"]
       and M.exit_price(c, o, 11, X["kind"]) == 96.0)
    c, o, xb, xd, gc, bad = mk(); c[21:] = np.nan; o[21:] = np.nan
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, 20, yes)
    ok("下市（末根距資料尾 ≥5）⇒ 末根收盤", X["x"] == 20 and X["reason"] == "下市末根" and X["done"])
    c, o, xb, xd, gc, bad = mk(); c[21:] = np.nan; o[21:] = np.nan; xb[19] = True; o[20] = 99.0; c[20] = 101.0
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, 20, yes)
    ok("觸發後賣出根是下市末根 ⇒ minoc", X["x"] == 20 and X["kind"] == "minoc" and M.exit_price(c, o, 20, "minoc") == 99.0)
    c, o, xb, xd, gc, bad = mk(); c[14] = np.nan; o[14] = np.nan; xb[13] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("觸發後下一根停牌 ⇒ 下一個有效根開盤賣", X["x"] == 15 and X["kind"] == "open")
    # 加碼
    c, o, xb, xd, gc, bad = mk(); gc[7] = True; gc[9] = True; xb[12] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("加碼：第一個 KD 條件 7 ⇒ 8 開盤加、只加一次", X["A"] == 8 and X["Alist"] == [8, 10] and X["kd_seen"])
    c, o, xb, xd, gc, bad = mk(); gc[9] = True; xb[9] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("觸發日當天的 KD 條件不加（出場優先）", X["A"] is None and not X["kd_seen"])
    c, o, xb, xd, gc, bad = mk(); gc[7] = True; gc[9] = True; xb[12] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, lambda k, a: a != 8)
    ok("加碼根過不了 entry_flag ⇒ 等下一個 KD 條件", X["A"] == 10 and X["kd_blocked"] == 1)
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes, addon=False)
    ok("拿掉加碼 ⇒ 不加、出場同主格", X["A"] is None and X["x"] == 13)
    c, o, xb, xd, gc, bad = mk(); gc[e] = True; xb[12] = True
    X = M.exit_sim(c, o, xb, xd, gc, bad, e, n - 1, n - 1, yes)
    ok("進場當天收盤的 KD 條件算（★9）⇒ e＋1 加", X["A"] == e + 1)
    o2 = o.copy(); o2[e] = 128.0; c2 = c.copy(); c2[:] = 128.0; c2[10] = 124.0; c2[11] = 124.0
    X = M.exit_sim(c2, o2, np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), bad, e, n - 1, n - 1, yes)
    ok("停損用首次進場價（128×0.97＝124.16 ⇒ 124 觸發）", X["d"] == 10)
    c3 = c2.copy(); c3[25:] = 1.0
    X3 = M.exit_sim(c3, o2, np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool), bad, e, n - 1, n - 1, yes)
    ok("PIT：改觸發之後的價格，出場位置不變", X3["x"] == X["x"] and X3["d"] == X["d"])


def t_sim_stock():
    exits = {6: 10, 13: 15, 20: 30}
    def ex(e):
        return {"x": exits.get(e, e + 3), "kind": "open", "reason": "", "trig": (), "A": None, "Alist": [], "kd_seen": False, "kd_blocked": 0,
                "flags": [], "done": True, "d": None}
    tr, sk = M.sim_stock([5, 7, 9, 10, 11], lambda t: "保留", ex, 100)
    ok("空手一天：出場 10 ⇒ 訊號 7、9 持有中、10 空手日、11 才進（e＝12）", [z["t"] for z in tr] == [5, 11] and sk["持有中"] == 2 and sk["空手一天"] == 1)
    old = M.FLAT; M.FLAT = 0
    tr0, _ = M.sim_stock([5, 7, 9, 10, 11], lambda t: "保留", ex, 100)
    M.FLAT = old
    ok("突變（FLAT＝0）會被 fixture 抓到", [z["t"] for z in tr0] != [z["t"] for z in tr])
    tr, sk = M.sim_stock([5, 12, 13], lambda t: "e開盤鎖漲停" if t == 12 else "保留", ex, 100)
    ok("被 entry_flag 擋的訊號不佔位、次數照報", [z["t"] for z in tr] == [5, 13] and sk["e開盤鎖漲停"] == 1)
    tr, sk = M.sim_stock([50, 100], lambda t: "保留", ex, 100)
    ok("訊號在資料尾 ⇒ e 超出資料尾", [z["t"] for z in tr] == [50] and sk["e超出資料尾"] == 1)


# ── 組合層 ───────────────────────────────────────────
def fx(x, A=None, kind="open"):
    return {"x": x, "kind": kind, "A": A, "Alist": ([] if A is None else [A])}


def t_portfolio():
    sids = [f"{1000 + k}" for k in range(10)]
    trades = {(k, 0): fx(20) for k in range(6)}
    trades[(0, 0)] = fx(5, A=3)                                         # 0 號 3 開盤加碼、5 開盤賣
    trades[(6, 4)] = fx(30)
    trades[(7, 4)] = fx(30)
    trades[(0, 5)] = fx(9)                                              # 0 號 5 賣、5 訊號 ⇒ 空手一天擋
    trades[(0, 6)] = fx(9)
    sig = {0: [0, 1, 2, 3, 4, 5], 4: [6, 7], 5: [0], 6: [0]}
    st = M.portfolio(0, 10, sig, lambda i, t: trades.get((i, t)), M.lottery_order(sids, 0))
    ok("5 份：同日 6 候選只進 5、1 筆因名額未進、該日算名額不足", st["進場筆數"] >= 5 and st["因名額未進筆數"] >= 1 and st["名額不足日比例(分母有候選日)"] is not None)
    st2 = M.portfolio(0, 10, sig, lambda i, t: trades.get((i, t)), M.lottery_order(sids, 0))
    st3 = M.portfolio(0, 10, sig, lambda i, t: trades.get((i, t)), M.lottery_order(sids, 1))
    ok("抽籤可重現（同 r 同結果）", st == st2)
    # 決定式排序：依代號 ⇒ 0～4 進、5 未進
    order = lambda cands, p: sorted(cands, key=lambda z: sids[z[0]])
    st = M.portfolio(0, 10, sig, lambda i, t: trades.get((i, t)), order)
    ok("沒空份 ⇒ 加碼不加（0 號在 3 開盤要加、份數全滿）", st["加碼成功"] == 0 and st["加碼因無份數未加(次)"] == 1)
    ok("0 號 5 開盤賣 ⇒ 釋出 1 份 ⇒ 5 開盤進 6（4 日訊號）、7 名額未進；6 日訊號（7 開盤）份數全滿未進", st["進場筆數"] == 6 and st["因名額未進筆數"] == 3)
    ok("空手一天：0 號 5 開盤賣 ⇒ 5 日訊號擋（6 開盤不可進）、6 日訊號不擋", st["空手一天擋"] == 1)
    # 有空份 ⇒ 加碼成功且佔份
    sig2 = {0: [0, 1]}
    tr2 = {(0, 0): fx(8, A=3), (1, 0): fx(8)}
    st = M.portfolio(0, 10, sig2, lambda i, t: tr2.get((i, t)), order)
    ok("有空份 ⇒ 加碼成功、佔 1 份（2～7 日閒置 2/5、其餘 3/5…）", st["加碼成功"] == 1 and st["5份全滿日比例"] == 0.0
       and abs(st["閒置份數比例(日平均)"] - (1 * 1.0 + 2 * 0.6 + 5 * 0.4 + 3 * 1.0) / 11) < 1e-12, f"{st}")
    # 收盤強制出 ⇒ 當天收盤釋出、次一日可用
    sig3 = {0: [0, 1, 2, 3, 4], 2: [5]}
    tr3 = {(k, 0): fx(20) for k in range(5)}; tr3[(0, 0)] = fx(2, kind="close"); tr3[(5, 2)] = fx(20)
    st = M.portfolio(0, 10, sig3, lambda i, t: tr3.get((i, t)), order)
    ok("收盤強制出（2 收盤）⇒ 3 開盤可用（2 日訊號進場）", st["進場筆數"] == 6 and st["因名額未進筆數"] == 0)


# ── 等價自查 ─────────────────────────────────────────
def t_equiv():
    C1 = np.array([1, 1, 0, 0, 1, 0, 0, 0], bool); C2 = np.array([1, 1, 1, 1, 0, 0, 0, 0], bool); C3 = np.array([1, 0, 1, 1, 1, 1, 0, 0], bool)
    T = {r["讀法"]: r for r in M.equiv_table(C1, C2, C3)}
    ok("P(③|②) ＝ 3/4", T["P(③|②)【主讀法】"]["比例"] == 0.75 and T["P(③|②)【主讀法】"]["分母"] == 4)
    ok("P(②|③) ＝ 3/5、Jaccard(②,③) ＝ 3/6", T["P(②|③)"]["比例"] == 0.6 and T["Jaccard(②,③)"]["比例"] == 0.5)
    ok("P(①|②∧③) ＝ 1/3", abs(T["P(①|②∧③)"]["比例"] - 1 / 3) < 1e-15)
    ok("分母 0 ⇒ 比例 None（不是 0）", M.cond_share(np.zeros(3, bool), np.ones(3, bool))[2] is None)


# ── 閘門與登錄 ───────────────────────────────────────
def t_gate():
    g = M.gate
    ok("--dry ⇒ 乾跑", g(["--dry"])[0] == "dry")
    ok("--formal 無裁定 ⇒ 拒跑", g(["--formal"])[0] == "refuse")
    ok("--formal --ruling seq486 ⇒ 拒跑", g(["--formal", "--ruling", "seq486"])[0] == "refuse")
    ok("--formal --dry ⇒ 拒跑", g(["--formal", "--dry", "--ruling", "seq487"])[0] == "refuse")
    ok("無參數 ⇒ 拒跑", g([])[0] == "refuse")
    ok("--formal --ruling seq487 ⇒ 通過閘（main 仍拒跑：正式輸出未實作）", g(["--formal", "--ruling", "seq487"])[0] == "formal")
    try:
        r = M.reg_verify(); good = r["bytes"] == 5124 and r["pw1去戳記相符"] and "seq487" in r["裁定"]
    except SystemExit as e:
        good = False; r = str(e)
    ok("登錄 5124 B、pw1 去戳記 sha d2eadb7cad586731、裁定 seq487 在信箱", good, str(r))


# ── 已產出檔：無報酬欄 ────────────────────────────────
def t_outputs():
    od = os.path.join(M.OUT, "freq")
    fs = sorted(glob.glob(os.path.join(od, "*.csv*")))
    if not fs:
        ok("產出檔（尚未產出，略）", True); return
    badcols = []
    for f in fs:
        cols = pd.read_csv(f, nrows=0).columns
        if os.path.basename(f) == "desc_dryrun_status.csv":
            if list(cols) != ["section", "cell", "stat", "n", "status"]:
                badcols.append((f, list(cols)))
            continue
        for c_ in cols:
            if any(k in c_ for k in ("報酬", "超額", "勝率", "權益", "回落", "年化")):
                badcols.append((f, c_))
    ok("產出檔沒有報酬／超額／勝率／權益／回落欄（描述欄狀態檔只有 filled／EMPTY）", not badcols, str(badcols[:5]))
    ds = pd.read_csv(os.path.join(od, "desc_dryrun_status.csv"))
    ok("描述欄乾跑：status 只有 filled／EMPTY", set(ds["status"]) <= {"filled", "EMPTY"})


def main():
    for f in (t_macd, t_boll, t_above, t_kd, t_features, t_exit, t_sim_stock, t_portfolio, t_equiv, t_gate, t_outputs):
        f()
    n = len(RES); p = sum(1 for _, x in RES if x)
    print(f"\n自測 {p}/{n} 通過")
    sys.exit(0 if p == n else 1)


if __name__ == "__main__":
    main()
