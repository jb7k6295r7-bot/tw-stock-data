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
 F10 乙 引擎能力（research11.simulate_mtm；⛔ 只 import）：
    ⓐ 2-B ⓐ add_rule gain x＝0.15 在 +15% 那天之後的開盤加（鏡像的「漲」方向存在）；2-C ⓐ trim_rule x＝0.10 在 −10% 之後開盤賣半
    ⓑ add_rule 沒有「跌 x% 加碼」：kind 只接受 gain／flag／hold（"loss" ⇒ ValueError）；gain 取 x＝−0.10 ⇒ 價格不動的第一天就加（方向錯）
    ⓒ trim_rule 沒有「漲 x% 賣半」：x 必須在 (0,1)（x＝−0.15 ⇒ ValueError）
    ⓓ flag 旗標以股票代號給、條件卻依【部位】進場價 ⇒ 同一檔兩列重疊訊號（A、B 進場價不同）時，同一份旗標無法同時對兩種持有情境都對
    ⇒ 結論：乙一、乙二 引擎都沒有對應參數 ⇒ 停、回報（⛔ 不改引擎）
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
    # ⓐ 鏡像存在的那兩條：2-B ⓐ（漲 15% 加）、2-C ⓐ（跌 10% 賣半）
    c = np.full(ncal, 100.0, np.float32); c[6] = 116.0; o = np.full(ncal, 100.0, np.float32)
    g = float(c[30] / o[2] - 1)
    r1 = _sim([("A", 2, 30, g)], {"A": c}, {"A": o}, ncal, add_rule={"kind": "gain", "x": 0.15}, audit=(au := []))
    add_days = [a["t"] for a in au if a.get("kind") == "add"]
    assert add_days == [7] and r1["x_add_n"] == 1, (add_days, r1.get("x_add_n"))
    c2 = np.full(ncal, 100.0, np.float32); c2[6] = 89.0
    r2 = _sim([("A", 2, 30, float(c2[30] / o[2] - 1))], {"A": c2}, {"A": o}, ncal, trim_rule={"x": 0.10, "frac": 0.5}, audit=(au2 := []))
    trim_days = [a["t"] for a in au2 if a.get("kind") == "trim"]
    assert trim_days == [7] and r2["x_trim_n"] == 1, trim_days
    out["ⓐ 鏡像的兩條在引擎裡"] = "2-B ⓐ gain +15% ⇒ 次日開盤加（t＝7）；2-C ⓐ trim −10% ⇒ 次日開盤賣半（t＝7）"
    # ⓑ 沒有「跌 x% 加碼」
    try:
        _sim([("A", 2, 30, 0.0)], {"A": c2}, {"A": o}, ncal, add_rule={"kind": "loss", "x": 0.10})
        raise AssertionError("⛔ add_rule kind＝loss 居然能跑")
    except ValueError:
        pass
    flat = np.full(ncal, 100.0, np.float32)
    r3 = _sim([("A", 2, 30, 0.0)], {"A": flat}, {"A": o}, ncal, add_rule={"kind": "gain", "x": -0.10}, audit=(au3 := []))
    d3 = [a["t"] for a in au3 if a.get("kind") == "add"]
    assert d3 == [3], d3                                   # 價格不動，進場後第一天就加 ⇒ 方向錯
    r4 = _sim([("A", 2, 30, float(c2[30] / o[2] - 1))], {"A": c2}, {"A": o}, ncal, add_rule={"kind": "gain", "x": 0.15})
    assert r4["x_add_n"] == 0                              # 跌 10% 時 gain 不會加
    out["ⓑ 乙一（跌 10% 加 0.5 slot）"] = "引擎沒有：kind 只接受 gain／flag／hold（loss ⇒ ValueError）；gain x＝−0.10 在價格不動的第一天就加（方向錯）"
    # ⓒ 沒有「漲 x% 賣半」
    try:
        _sim([("A", 2, 30, 0.0)], {"A": c}, {"A": o}, ncal, trim_rule={"x": -0.15, "frac": 0.5})
        raise AssertionError("⛔ trim_rule x＝−0.15 居然能跑")
    except ValueError:
        pass
    r5 = _sim([("A", 2, 30, float(c[30] / o[2] - 1))], {"A": c}, {"A": o}, ncal, trim_rule={"x": 0.10, "frac": 0.5})
    assert r5["x_trim_n"] == 0                             # 漲 15% 時 trim 不會賣
    out["ⓒ 乙二（漲 15% 賣半）"] = "引擎沒有：trim_rule 只有「≤ −x」方向、x 必須在 (0,1)（−0.15 ⇒ ValueError）；regime_trim 看的是 0050 不是個股"
    # ⓓ flag 以股票代號給、條件依部位進場價 ⇒ 重疊兩列無法用同一份旗標
    oo = np.full(ncal, 100.0, np.float32); oo[4] = 110.0     # A 在 2 進場（ep 100）、B 在 4 進場（ep 110）
    cc = np.full(ncal, 100.0, np.float32); cc[8] = 95.0      # 95 ≤ 0.9×110＝99 ⇒ B 該加；95 > 90 ⇒ A 不該加
    fA = np.zeros(ncal, bool); fB = np.zeros(ncal, bool)
    fB[8] = True                                              # B 的正確旗標（A 的正確旗標全假）
    rowA = ("S", 2, 30, float(cc[30] / oo[2] - 1)); rowB = ("S", 4, 32, float(cc[32] / oo[4] - 1))
    res = {}
    for nm, fl in (("A的旗標", fA), ("B的旗標", fB)):
        a1 = _sim([rowA], {"S": cc}, {"S": oo}, ncal, add_rule={"kind": "flag", "flags": {"S": fl}})["x_add_n"]
        b1 = _sim([rowB], {"S": cc}, {"S": oo}, ncal, add_rule={"kind": "flag", "flags": {"S": fl}})["x_add_n"]
        res[nm] = (a1, b1)
    assert res["A的旗標"] == (0, 0) and res["B的旗標"] == (1, 1), res       # 正確答案是 (A 不加, B 加) ＝ (0, 1)：兩份旗標都做不到
    out["ⓓ flag 旗標代替不了"] = "同一檔兩列（ep 100／110）：A 的旗標 ⇒ (A 加 0, B 加 0)；B 的旗標 ⇒ (1, 1)；正確 ＝ (0, 1) ⇒ 靜態旗標無解"
    out["結論"] = {"乙一_引擎有對應參數": False, "乙二_引擎有對應參數": False, "處置": "停、回報（⛔ 不改引擎）"}
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
