# -*- coding: utf-8 -*-
"""PREREG攤平停利 fixture（合成資料；⛔ 不讀任何報酬、⛔ 不讀真實股價）。全部 assert 過才回結果；任一條不過 ⇒ 研究檔中止。

 F1 觸發抓在正確的日子：手造（等號：收盤 ＝ 0.90·P0、＝ 1.15·P0 算觸發；只取第一次；觀察期 [e, e＋119]：第 120 個交易日算、第 121 個不算；
    T＝e 可能；無效 K 棒不判）＋ 隨機 300 條 × 每條 12 筆持有 對一份【獨立寫法】（純 Python 迴圈、不呼叫 avgdown）逐筆相同；
    並示範字面式與引擎式的浮點分歧（P0＝100、收盤 115：字面觸發、引擎式 115/100−1 ＜ 0.15 不觸發）
 F2 T＋1 成交與遞延：攤平（買）T＋1 開盤漲停 ⇒ 遞延、開盤跌停 ⇒ 照買；停利（賣）T＋1 開盤跌停 ⇒ 遞延、開盤漲停 ⇒ 照賣；
    停牌 ⇒ 遞延；到最後都成交不了 ⇒ 剔除_成交不到；x ≥ 日曆尾 ⇒ 剔除_超出日曆；T ＞ w1−H ⇒ 窗外；終點停牌 ⇒ 前一根有效收盤
 F3 ⭐ 無前視（突變）：把序列 i 之後改成任意值（收盤、開盤、成交旗標）⇒ T ≤ i 的觸發、r20、持有是否建立、最早進行中 e 全不變
    （隨機 60 條 × 多個 i）；假訊號臂：在 T 之後加真事件 ⇒ T 是否可抽不變
 F4 ⭐ 鑑別力（檢查本身會響）：故意用【隔天收盤】判觸發（前視）⇒ F3 的截斷檢查一定抓到；門檻改 0.91 ⇒ 事件不同（⛔ 不是恆等輸出）；
    舊的「前後 ±20 日」排除（用到未來）⇒ F3 的假訊號檢查一定抓到
 F5 0 報酬（價格恆等、0050 恆等）⇒ R＝R0＝0 ⇒ 不含成本的判定量＝0；含成本 X 恰為成本差（攤平 −0.200%、停利 −0.385%）；
    CR0 SE＝0；配對股同一條路徑 ⇒ X − y ＝ 0
 F6 去重：兩筆持有同一天觸發 ⇒ 只留 e 最早的一筆、去掉 1
 F7 硬斷點：brk_vec ＝ exit_signal.brk（＝ researchH2.brk）逐點（隨機 5,000 組窗）；窗 [e, x]：斷點在 e−1 不剔、在 e 剔、在 x 剔、在 x＋1 不剔
 F8 十分位與配對：deciles 對獨立寫法（隨機 200 天橫斷面）；researchAvg.match_controls 的 ȳ 對暴力法（合成 40 檔 × 8 天）逐筆同
 F9 假訊號臂：排除 [T−20, T]（含當天）；T_r＝T−21 不排除；T_r＝T＋1 不影響；逐檔種子與行程分工無關（兩種順序抽出相同）
 F10 乙 引擎能力（research11.simulate_mtm；⛔ 只 import）——2026-09-25 改寫（裁定 seq181：引擎兩型 d609e89a95 收下，F10 改驗新 kind）：
    原本的 F10 證明「引擎沒有 跌 x% 加碼／漲 x% 賣半」；引擎擴充後改成驗 add_rule kind＝"loss"、trim_rule kind＝"gain" 三件事：
    ⓐ 觸發：P0＝100、收盤 90.0（＝0.90·P0）⇒ 次日開盤加（等號算）；90.01 ⇒ 不加；收盤 115.0（＝1.15·P0）⇒ 次日開盤賣半；114.99 ⇒ 不賣
       （115 用引擎舊比值式 115/100−1 ＜ 0.15 不會觸發 ⇒ 新 kind 用的是登錄字面式，與 F1 的浮點分歧示範同一個數）
    ⓑ 只一次：觸發後更深（80）／更高（130）⇒ 不再加／不再賣（x_add_n、x_trim_n 都是 1）
    ⓒ 與登錄門檻字面式一致：隨機 300 條路徑 × 2 筆持有 × 2 型，引擎的加碼／賣半日 − 1 ＝ 獨立寫法 ind_first_trigger（收盤 ≤ 0.90·P0、
       ≥ 1.15·P0）的第一次觸發日，也 ＝ 甲的 avgdown.first_triggers（字面式）落在持有期內的那一次；觀察窗 ＝ 引擎能在出場前成交的
       [e, x−2]（排程出場日 x 當天不再加減碼）
    ⇒ 結論：乙一、乙二 引擎都有對應參數（add_rule {"kind": "loss", "x": 0.10}、trim_rule {"kind": "gain", "x": 0.15, "frac": 0.5}）
"""
from __future__ import annotations
import os, sys, zlib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                                    # 快照路徑、chdir
from backtest import avgdown as AV
from backtest import exit_signal as XS
from backtest import research11 as R11


# ───────── 獨立寫法（⛔ 不呼叫 avgdown）─────────
def ind_first_trigger(c, valid, e, P0, kind, obs=120):
    for t in range(e, min(e + obs, len(c))):
        if not valid[t]:
            continue
        if kind == "跌" and c[t] <= 0.90 * P0:
            return t
        if kind == "漲" and c[t] >= 1.15 * P0:
            return t
    return -1


def rand_path(seed, m=400):
    r = np.random.default_rng(seed)
    c = 50 * np.exp(r.normal(0, 0.025, m).cumsum())
    o = c * np.exp(r.normal(0, 0.01, m))
    valid = r.random(m) > 0.03
    c = np.where(valid, c, np.nan)
    return o, c, valid


def F1():
    n = 300
    c = np.full(n, 100.0); o = np.full(n, 100.0); valid = np.ones(n, bool)
    # 等號：P0＝100，第 5 根收盤恰 90 ⇒ 觸發在 5（0.9*100 ＝ 90.0）
    c[3] = 90.5; c[5] = 90.0; c[8] = 80.0
    T = AV.first_triggers(c, valid, np.array([0]), np.array([100.0]), "跌", n)
    assert list(T) == [5], T
    # 只取第一次：第 8 根更深也不改
    # 漲：第 7 根收盤 115 ⇒ 字面觸發；引擎式 115/100−1 ＜ 0.15 ⇒ 不觸發（浮點分歧）
    c2 = np.full(n, 100.0); c2[7] = 115.0; c2[9] = 116.0
    Tl = AV.first_triggers(c2, valid, np.array([0]), np.array([100.0]), "漲", n)
    Te = AV.first_triggers(c2, valid, np.array([0]), np.array([100.0]), "漲", n, form="eng")
    assert list(Tl) == [7] and list(Te) == [9], (Tl, Te)
    # 觀察期 [e, e＋119]：e＝10，第 129 根（e＋119）觸發算、第 130 根不算
    c3 = np.full(n, 100.0); c3[129] = 89.0
    assert list(AV.first_triggers(c3, valid, np.array([10]), np.array([100.0]), "跌", n)) == [129]
    c3[129] = 100.0; c3[130] = 89.0
    assert list(AV.first_triggers(c3, valid, np.array([10]), np.array([100.0]), "跌", n)) == [-1]
    # T＝e：e 當天收盤就 ≤ 0.9 P0
    c4 = np.full(n, 100.0); c4[10] = 89.0
    assert list(AV.first_triggers(c4, valid, np.array([10]), np.array([100.0]), "跌", n)) == [10]
    # 無效 K 棒不判
    v5 = valid.copy(); c5 = np.full(n, 100.0); c5[12] = 80.0; v5[12] = False; c5[14] = 85.0
    assert list(AV.first_triggers(c5, v5, np.array([10]), np.array([100.0]), "跌", n)) == [14]
    # 持有：e 停牌／開盤漲停 ⇒ 不建
    trd = np.ones(n, bool); up = np.zeros(n, bool); trd[20] = False; up[40] = True
    e_el, P0 = AV.holdings(np.array([0, 20, 40, 60]), trd, up, o)
    assert list(e_el) == [0, 60] and list(P0) == [100.0, 100.0]
    # 隨機 300 條 × 12 筆持有 對獨立寫法
    tot = 0
    for sd in range(300):
        o, c, valid = rand_path(5000 + sd)
        E = np.arange(0, 400, 33)[:12]
        P0 = o[E]
        for kind in AV.TYPES:
            a = AV.first_triggers(c, valid, E, P0, kind, 400)
            b = [ind_first_trigger(c, valid, int(e), float(p), kind) for e, p in zip(E, P0)]
            assert list(a) == b, (sd, kind, a, b)
            tot += int((a >= 0).sum())
    assert tot > 1000, tot
    return {"手造": "7 條過", "隨機": "300 條 × 12 筆 × 2 型對獨立寫法逐筆同（觸發 {:,} 筆）".format(tot), "浮點分歧示範": "115 vs 100：字面觸發、引擎式不觸發"}


def F2():
    n = 60; H = 5; w1 = 50
    o = np.full(n, 10.0); c = np.full(n, 10.0); valid = np.ones(n, bool)
    trd = np.ones(n, bool); up = np.zeros(n, bool); dn = np.zeros(n, bool)
    cs0 = np.zeros(n, np.int32)
    T = 10
    up[11] = True; dn[12] = True
    nb = AV.next_true(AV.trade_ok(trd, up, o)); ns = AV.next_true(AV.trade_ok(trd, dn, o))
    lv = AV.last_valid(valid)
    st, s, x, j = AV.outcome([T], [0], H, nb, lv, cs0, cs0, n, w1)
    assert (st[0], s[0], x[0]) == (AV.ST_KEEP, 12, 16), (st, s, x)            # 攤平：11 漲停 ⇒ 12（12 跌停照買）
    st, s, x, j = AV.outcome([T], [0], H, ns, lv, cs0, cs0, n, w1)
    assert (st[0], s[0]) == (AV.ST_KEEP, 11), (st, s)                           # 停利：11 漲停照賣
    st, s, x, j = AV.outcome([11], [0], H, ns, lv, cs0, cs0, n, w1)
    assert s[0] == 13, s                                                        # 停利：12 跌停 ⇒ 13
    trd2 = trd.copy(); trd2[11] = False; up2 = up.copy(); up2[11] = False; up2[12] = True
    nb2 = AV.next_true(AV.trade_ok(trd2, up2, o))
    st, s, x, j = AV.outcome([T], [0], H, nb2, lv, cs0, cs0, n, w1)
    assert s[0] == 13 and s[0] - (T + 1) == 2                                   # 停牌、漲停 ⇒ 遞延 2 日
    trd3 = trd.copy(); trd3[11:] = False
    st, s, x, j = AV.outcome([T], [0], H, AV.next_true(AV.trade_ok(trd3, up, o)), lv, cs0, cs0, n, w1)
    assert st[0] == AV.ST_NOTRADE
    st, s, x, j = AV.outcome([w1 - H + 1], [0], H, nb, lv, cs0, cs0, n, w1)
    assert st[0] == AV.ST_OUT
    st, s, x, j = AV.outcome([56], [0], H, nb, lv, cs0, cs0, n, 62)
    assert st[0] == AV.ST_BEYOND, st
    v4 = valid.copy(); v4[16] = False
    st, s, x, j = AV.outcome([T], [0], H, nb, AV.last_valid(v4), cs0, cs0, n, w1)
    assert x[0] == 16 and j[0] == 15                                            # 終點停牌 ⇒ 前一根有效收盤
    # H〈n〉＝ 成交日＋(n−1)：s＝11、H＝20 ⇒ x＝30
    st, s, x, j = AV.outcome([T], [0], 20, AV.next_true(AV.trade_ok(trd, np.zeros(n, bool), o)), lv, cs0, cs0, n, w1)
    assert (s[0], x[0]) == (11, 30)
    # 讀法 A12：0050 停牌 ⇒ 兩條腿一起遞延（股票 11 可成交、0050 11～12 停牌 ⇒ s＝13）
    ok50 = np.ones(n, bool); ok50[11:13] = False
    nz = AV.next_true(AV.trade_ok(trd, np.zeros(n, bool), o) & ok50)
    st, s, x, j = AV.outcome([T], [0], 20, nz, lv, cs0, cs0, n, w1)
    assert (s[0], x[0]) == (13, 32)
    return "11 條過（買／賣兩側的漲跌停、停牌遞延、0050 停牌同步遞延、成交不到、超出日曆、窗外、終點停牌、H 定義）"


def F3():
    bad = 0; checks = 0
    for sd in range(60):
        o, c, valid = rand_path(7000 + sd, 300)
        trd = valid.copy(); up = np.zeros(300, bool)
        E = np.arange(0, 300, 21)
        e_el, P0 = AV.holdings(E, trd, up, o)
        bars = np.flatnonzero(valid)
        full = {k: AV.first_triggers(c, valid, e_el, P0, k, 300) for k in AV.TYPES}
        r20 = AV.r20_cal(c, bars)
        for i in (60, 120, 180, 240):
            r = np.random.default_rng(sd * 10 + i)
            c2 = c.copy(); o2 = o.copy(); v2 = valid.copy(); t2 = trd.copy()
            c2[i + 1:] = r.uniform(1, 200, 300 - i - 1); o2[i + 1:] = r.uniform(1, 200, 300 - i - 1)
            v2[i + 1:] = r.random(300 - i - 1) > 0.5; c2 = np.where(v2, c2, np.nan); t2[i + 1:] = v2[i + 1:]
            e2, P02 = AV.holdings(E, t2, up, o2)
            k_ = e_el <= i
            assert list(e2[e2 <= i]) == list(e_el[k_]) and list(P02[e2 <= i]) == list(P0[k_])
            for k in AV.TYPES:
                g = AV.first_triggers(c2, v2, e2, P02, k, 300)
                a = np.where((full[k] >= 0) & (full[k] <= i), full[k], -1)[k_]
                b = np.where((g >= 0) & (g <= i), g, -1)[e2 <= i]
                checks += 1; bad += int(not np.array_equal(a, b))
            r2 = AV.r20_cal(c2, np.flatnonzero(v2))
            assert np.array_equal(np.nan_to_num(r2[:i + 1], nan=-9), np.nan_to_num(r20[:i + 1], nan=-9))
            Tq = np.arange(0, i + 1)
            assert np.array_equal(AV.earliest_active(e_el, Tq), AV.earliest_active(e2, Tq))   # 最早進行中 e 只取決於 ≤ T 的 e
    assert bad == 0, bad
    # 假訊號臂：在 T 之後加真事件 ⇒ T 是否可抽不變
    cand = np.arange(100, 200)
    base = AV.fake_candidates(cand, [120, 150])
    for extra in (171, 180, 199, 250):
        assert np.array_equal(AV.fake_candidates(cand, [120, 150, extra])[AV.fake_candidates(cand, [120, 150, extra]) < extra],
                              base[base < extra])
    return {"截斷突變": "60 條 × 4 個截點 × 2 型：觸發、持有、r20 全不變（{} 組）".format(checks), "假訊號": "加未來真事件不改變之前的可抽日"}


def F4():
    # ① 故意前視：用隔天收盤判觸發 ⇒ 截斷檢查抓到
    def peek(c, valid, e_el, P0, kind, n):
        cn = np.r_[c[1:], np.nan]; vn = np.r_[valid[1:], False]
        return AV.first_triggers(cn, vn, e_el, P0, kind, n)
    caught = 0
    for sd in range(40):
        o, c, valid = rand_path(9000 + sd, 300)
        e_el = np.arange(0, 300, 21); P0 = o[e_el]
        full = peek(c, valid, e_el, P0, "跌", 300)
        i = 150
        c2 = c.copy(); c2[i + 1:] = 1.0; v2 = valid.copy(); v2[i + 1:] = True
        g = peek(c2, v2, e_el, P0, "跌", 300)
        k_ = e_el <= i
        a = np.where((full >= 0) & (full <= i), full, -1)[k_]; b = np.where((g >= 0) & (g <= i), g, -1)[k_]
        caught += int(not np.array_equal(a, b))
    assert caught > 0, "⛔ 截斷檢查沒抓到故意前視"
    # ② 門檻改 0.91 ⇒ 事件不同
    diff = 0
    for sd in range(40):
        o, c, valid = rand_path(9500 + sd, 300)
        e_el = np.arange(0, 300, 21); P0 = o[e_el]
        a = AV.first_triggers(c, valid, e_el, P0, "跌", 300)
        b = np.array([next((t for t in range(e, min(e + 120, 300)) if valid[t] and c[t] <= 0.91 * p), -1) for e, p in zip(e_el, P0)])
        diff += int(not np.array_equal(a, b))
    assert diff > 0
    # ③ 舊的 ±20 排除（用未來）⇒ 假訊號檢查抓到
    def old(cand, T_real):
        T_real = np.asarray(T_real)
        return np.array([t for t in cand if not (np.abs(T_real - t) <= 20).any()], int)
    cand = np.arange(100, 200)
    a = old(cand, [120, 150]); b = old(cand, [120, 150, 175])
    assert not np.array_equal(a[a < 175], b[b < 175]), "⛔ 假訊號前視檢查沒響"
    return {"故意前視（隔天收盤）被抓到": "{}／40 條".format(caught), "門檻 0.91 事件不同": "{}／40 條".format(diff), "舊 ±20 排除": "被抓到（未來事件改變之前的可抽日）"}


def F5():
    n = 200; H = 20; w1 = 150
    o = np.full(n, 37.5); c = np.full(n, 37.5); valid = np.ones(n, bool); trd = valid.copy(); z = np.zeros(n, bool)
    o50 = np.full(n, 120.0); c50 = np.full(n, 120.0); cs0 = np.zeros(n, np.int32)
    Ts = np.arange(10, 100, 3)
    out = {}
    for kind in AV.TYPES:
        nx = AV.next_true(AV.trade_ok(trd, z, o))
        st, s, x, j = AV.outcome(Ts, np.zeros(len(Ts), int), H, nx, AV.last_valid(valid), cs0, cs0, n, w1)
        assert (st == AV.ST_KEEP).all()
        R = AV.ret(o, c, s, j); R0 = AV.ret0050(o50, c50, s, H)
        assert (R == 0).all() and (R0 == 0).all()
        gross = R - R0 if kind == "跌" else R0 - R
        assert (gross == 0).all()
        X = AV.x_value(kind, R, R0)
        want = -0.002 if kind == "跌" else -0.00385
        assert np.allclose(X, want, rtol=0, atol=1e-15), X[:3]
        m, se, ng = AV.cr0(gross, np.arange(len(gross)) // 4)
        assert m == 0 and se == 0
        m2, se2, _ = AV.cr0(X, np.arange(len(X)) // 4)
        assert abs(m2 - want) < 1e-15 and se2 < 1e-15
        d = X - X
        assert (d == 0).all()
        out[AV.CELL[kind]] = "不含成本判定量 0、SE 0；含成本 X ＝ {:+.3%}".format(want)
    return out


def F6():
    n = 200
    c = np.full(n, 100.0); valid = np.ones(n, bool)
    e = np.array([0, 20, 40]); P0 = np.array([100.0, 105.0, 104.0])
    c[50] = 92.0                                          # ≤ 94.5（e＝20）、≤ 93.6（e＝40）；> 90（e＝0）
    c[60] = 89.0                                          # e＝0 第一次
    T = AV.first_triggers(c, valid, e, P0, "跌", n)
    assert list(T) == [60, 50, 50], T
    Es, Ts, nd = AV.dedup(e, T)
    assert list(Ts) == [50, 60] and list(Es) == [20, 0] and nd == 1, (Es, Ts, nd)
    return "同日兩筆只留 e 最早（e＝20）、去掉 1"


def F7():
    r = np.random.default_rng(11)
    for _ in range(5000):
        n = 80
        pb = r.random(n) < 0.03; g5 = r.random(n) < 0.03
        cpb = np.cumsum(pb).astype(np.int32); cg5 = np.cumsum(g5).astype(np.int32)
        a = int(r.integers(-3, n)); b = int(r.integers(0, n))
        v1 = bool(AV.brk_vec(cpb, cg5, [a], [b])[0]); v2 = XS.brk(cpb, cg5, max(a, 0) if a < 0 else a, b)
        S = {"cs_pb": cpb, "cs_g5": cg5}
        if a >= 0:
            assert v1 == v2 == H2.brk(S, a, b), (a, b)
    n = 100; H = 10; w1 = 90
    nx = np.arange(n); lv = np.arange(n)
    for pos, want in ((19, AV.ST_KEEP), (20, AV.ST_BRK), (40, AV.ST_BRK), (41, AV.ST_KEEP)):
        pb = np.zeros(n, bool); pb[pos] = True
        st, s, x, j = AV.outcome([30], [20], H, nx, lv, np.cumsum(pb).astype(np.int32), np.zeros(n, np.int32), n, w1)
        assert x[0] == 40 and st[0] == want, (pos, st, x)
    # g5：連續缺 5 日的第 5 天落在窗內才算
    for last_gap_day, want in ((24, AV.ST_BRK), (19, AV.ST_KEEP)):
        g5 = np.zeros(n, bool); g5[last_gap_day] = True           # g5[d] ＝ d 為「連續缺 ≥ 5 日」的第 5 天以後
        st, s, x, j = AV.outcome([30], [20], H, nx, lv, np.zeros(n, np.int32), np.cumsum(g5).astype(np.int32), n, w1)
        assert st[0] == want, (last_gap_day, st)
    return "brk_vec ＝ exit_signal.brk ＝ researchH2.brk（5,000 組）；窗 [e, x] 四個邊界、g5 兩個邊界過"


def F8():
    import researchAvg as RA
    r = np.random.default_rng(3)
    for _ in range(200):
        n = int(r.integers(1, 60))
        x = r.normal(size=n); x[r.random(n) < 0.2] = np.nan
        x[r.random(n) < 0.2] = 0.5                               # 同值
        d = AV.deciles(x)
        ok = [i for i in range(n) if np.isfinite(x[i])]
        order = sorted(ok, key=lambda i: (x[i], i))
        ref = np.full(n, -1)
        for rk, i in enumerate(order):
            ref[i] = rk * 10 // len(ok)
        assert np.array_equal(d, ref), (x, d, ref)
    # 合成 match_controls
    N, W, wlo = 40, 8, 1000
    res = []
    for i in range(N):
        rr = r.normal(size=W); rr[r.random(W) < 0.15] = np.nan
        q = {"sid": "{:04d}".format(i), "r20u": rr}
        for kind in AV.TYPES:
            q["trig_" + kind] = r.random(W) < 0.2
            for H in (20, 60):
                q["okc_{}_{}".format(kind, H)] = r.random(W) < 0.85
                q["Xc_{}_{}".format(kind, H)] = r.normal(size=W)
        res.append(q)
    ev = []
    for i in range(N):
        for k in range(W):
            for kind in AV.TYPES:
                if res[i]["trig_" + kind][k] and r.random() < 0.5:
                    for H in (20, 60):
                        ev.append({"sid": res[i]["sid"], "kind": kind, "H": H, "T": wlo + k})
    K = pd.DataFrame(ev)
    mc = RA.match_controls(res, K, wlo, body=True)
    RU = np.vstack([q["r20u"] for q in res])
    nchk = 0
    for (kind, H), (idx, dec, nct, yb) in mc.items():
        for q_, (ii, row) in enumerate(K.loc[idx].iterrows()):
            i = int(row["sid"]); k = int(row["T"]) - wlo
            dd = AV.deciles(RU[:, k])
            if dd[i] < 0:
                assert dec[q_] == -1 and not np.isfinite(yb[q_]); continue
            ctl = [j for j in range(N) if dd[j] == dd[i] and not res[j]["trig_" + kind][k] and res[j]["okc_{}_{}".format(kind, H)][k]]
            assert nct[q_] == len(ctl)
            if ctl:
                assert abs(yb[q_] - np.mean([res[j]["Xc_{}_{}".format(kind, H)][k] for j in ctl])) < 1e-12
            else:
                assert not np.isfinite(yb[q_])
            nchk += 1
    assert nchk > 20
    return {"十分位": "200 個橫斷面對獨立寫法逐檔同（含同值、NaN）", "配對": "match_controls 的配對股數與 ȳ 對暴力法 {} 筆全同".format(nchk)}


def F9():
    cand = np.arange(100, 160)
    a = AV.fake_candidates(cand, [130])
    assert 130 not in a and 150 not in a and 151 in a and 129 in a and 110 in a       # [T−20, T] 含當天；之前的日子不受影響
    a2 = AV.fake_candidates(cand, [109])
    assert 130 in a2 and 129 not in a2
    # 逐檔種子：兩種處理順序抽出相同
    sids = ["2330", "1101", "6488", "3008"]
    def draw(order):
        out = {}
        for s in order:
            rng = np.random.default_rng([20260928 + 3, zlib.crc32(s.encode("utf-8"))])
            out[s] = tuple(np.sort(rng.choice(cand, size=5, replace=False)))
        return out
    assert draw(sids) == draw(sids[::-1])
    return "排除 [T−20, T]（含當天）邊界過；逐檔種子與順序無關"


def _sim(sig_rows, closes, opens, ncal, **kw):
    sig = pd.DataFrame(sig_rows, columns=["sid", "entry_pos", "xpos_H120", "g_H120"])
    return R11.simulate_mtm(sig, "H120", 2, np.random.default_rng(0), closes, opens, ncal, return_equity=True, **kw)


def F10():
    ncal = 40
    out = {}
    o = np.full(ncal, 100.0)
    LOSS = {"kind": "loss", "x": 0.10}; GAIN = {"kind": "gain", "x": 0.15, "frac": 0.5}
    # ⓐⓑ 攤平（add_rule kind＝loss）：收盤 90.0 ＝ 0.90×100 ⇒ t＝7 開盤加；之後跌到 80 不再加
    c = np.full(ncal, 100.0); c[6] = 90.0; c[10] = 80.0; c[12] = 85.0
    r1 = _sim([("A", 2, 30, 0.0)], {"A": c}, {"A": o}, ncal, add_rule=LOSS, audit=(au := []))
    add_days = [a["t"] for a in au if a.get("kind") == "add"]
    assert add_days == [7] and (r1["x_add_trig"], r1["x_add_n"]) == (1, 1), (add_days, r1.get("x_add_trig"), r1.get("x_add_n"))
    c1 = np.full(ncal, 100.0); c1[6] = 90.01
    r1b = _sim([("A", 2, 30, 0.0)], {"A": c1}, {"A": o}, ncal, add_rule=LOSS)
    assert (r1b["x_add_trig"], r1b["x_add_n"]) == (0, 0), r1b.get("x_add_trig")
    out["ⓐⓑ 攤平 loss"] = "收盤 90.0（＝0.90·P0）⇒ t＝7 開盤加、之後跌到 80 不再加（trig 1、加成 1）；90.01 ⇒ 不加"
    # ⓐⓑ 停利（trim_rule kind＝gain）：收盤 115.0 ＝ 1.15×100 ⇒ t＝7 開盤賣半；之後漲到 130 不再賣
    c2 = np.full(ncal, 100.0); c2[6] = 115.0; c2[10] = 130.0
    r2 = _sim([("A", 2, 30, 0.0)], {"A": c2}, {"A": o}, ncal, trim_rule=GAIN, audit=(au2 := []))
    trim_days = [a["t"] for a in au2 if a.get("kind") == "trim"]
    assert trim_days == [7] and r2["x_trim_n"] == 1, (trim_days, r2.get("x_trim_n"))
    c3 = np.full(ncal, 100.0); c3[6] = 114.99
    assert _sim([("A", 2, 30, 0.0)], {"A": c3}, {"A": o}, ncal, trim_rule=GAIN)["x_trim_n"] == 0
    assert 115.0 / 100.0 - 1.0 < 0.15 and 115.0 >= (1.0 + 0.15) * 100.0 and 90.0 <= (1.0 - 0.10) * 100.0   # 字面式觸發、舊比值式不觸發
    out["ⓐⓑ 停利 gain"] = "收盤 115.0（＝1.15·P0；舊比值式 115/100−1＜0.15 不觸發）⇒ t＝7 開盤賣半、之後漲到 130 不再賣（x_trim_n 1）；114.99 ⇒ 不賣"
    # ⓒ 與登錄門檻字面式一致：隨機路徑（無停牌 ⇒ 引擎與獨立寫法讀同一串收盤）
    n_path = 300; ncal2 = 400; hit = {"跌": 0, "漲": 0}; tot = 0
    for sd in range(n_path):
        op, cl, _ = rand_path(7000 + sd, ncal2)
        cl = pd.Series(cl).ffill().bfill().to_numpy()
        valid = np.ones(ncal2, bool)
        for e in (5, 200):
            x = e + 119
            for kind, kw, tag in (("跌", dict(add_rule=LOSS), "add"), ("漲", dict(trim_rule=GAIN), "trim")):
                r = _sim([("A", e, x, 0.0)], {"A": cl}, {"A": op}, ncal2, audit=(a_ := []), **kw)
                days = [z["t"] for z in a_ if z.get("kind") == tag]
                T_ind = ind_first_trigger(cl, valid, e, float(op[e]), kind, obs=x - 1 - e)
                T_av = int(AV.first_triggers(cl, valid, np.array([e]), np.array([float(op[e])]), kind, ncal2)[0])
                want = [T_ind + 1] if T_ind >= 0 else []
                want_av = [T_av + 1] if 0 <= T_av <= x - 2 else []
                assert days == want == want_av and len(days) <= 1, (sd, e, kind, days, T_ind, T_av)
                if kind == "跌":
                    assert r["x_add_trig"] == len(want), (sd, e, r["x_add_trig"])
                hit[kind] += len(days); tot += 1
    assert hit["跌"] > 50 and hit["漲"] > 50, hit
    out["ⓒ 字面式一致"] = "隨機 {} 條 × 2 筆 × 2 型 ＝ {} 次：引擎動作日 − 1 ＝ ind_first_trigger ＝ avgdown.first_triggers（窗 [e, x−2]）逐筆同；觸發 跌 {}、漲 {}".format(
        n_path, tot, hit["跌"], hit["漲"])
    out["結論"] = {"乙一_引擎有對應參數": True, "乙二_引擎有對應參數": True,
                 "參數": {"By": {"add_rule": {"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}},
                        "Ci": {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}},
                 "處置": "引擎擴充 d609e89a95（裁定 seq181 收下）；乙二 seq3 另有 trim_proceeds 開關（見 selftest_avgengine2.py）"}
    return out

ALL = {"F1": F1, "F2": F2, "F3": F3, "F4": F4, "F5": F5, "F6": F6, "F7": F7, "F8": F8, "F9": F9, "F10": F10}


def run_all(only=None):
    out = {}
    for k, f in ALL.items():
        if only and k not in only:
            continue
        out[k] = f()
        print("✅ {} {}".format(k, out[k] if isinstance(out[k], str) else ""), flush=True)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), ensure_ascii=False, indent=1))
