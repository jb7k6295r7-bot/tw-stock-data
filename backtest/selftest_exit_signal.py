# -*- coding: utf-8 -*-
"""PREREG出場訊號 fixture（合成資料；⛔ 不讀任何報酬）。全部 assert 過才印 ✅；任一條不過 ⇒ 研究檔中止。

 F1 三種訊號抓在正確的日子：手造序列（甲 擺動低點確認後才跌破；乙 MA20；丙 MA60）＋ 隨機 300 條對一份【獨立寫法】
    （純 Python 迴圈、不呼叫 exit_signal／stop_fractal 任何函式）逐根相同
 F2 等號邊界：close ＝ 線 ⇒ 不算跌破；close_{T−1} ＝ 線 ⇒ 算「在線上」（甲、乙各一）；跌破 1%、連 3 日的邊界
 F3 ⭐ 無前視（突變）：把序列截在 i、或把 i 之後改成任意值 ⇒ ≤ i 的 Y、MA、事件旗標、狀態標籤全不變（隨機 40 條 × 全部 i）
    破壞價 Y_i ＝ state_label.core(h[:i+1], l[:i+1], c[:i+1])["break_adj"]（隨機 40 條 × 全部 i，逐位元）
 F4 ⭐ 鑑別力（檢查本身會響）：故意用【未確認】擺動點（lag＝4 < k＝5）、或故意用【當天之後】的收盤（MA 右移一根）
    ⇒ F3 的截斷檢查一定抓到（不相同）；而且兩者在同一批序列上的事件與正式版不同（⛔ 不是恆等輸出）
 F5 0 報酬（價格恆等）⇒ R_H ＝ 0（H＝5、20、60、120），判定量 E ＝ 0、CR0 SE ＝ 0
 F6 賣出遞延與終點：T＋1 停牌、T＋2 開盤跌停、T＋3 可賣 ⇒ s＝T＋3、遞延 2 日、原因「停牌」；終點停牌 ⇒ 用前一根收盤；
    下市 ⇒「下市了結」；T＋1 之後再也無成交 ⇒ 剔除_賣不掉；80 根閘（第 79 根不產生、第 80 根產生）；
    合併（T、T＋20 合併、T＋21 保留）；硬斷點窗 [T−60, 終點]（斷點在 T−60 ⇒ 剔除；T−61 ⇒ 不剔；在終點 ⇒ 剔除；終點＋1 ⇒ 不剔）
 F7 brk ＝ researchH2.brk（隨機 cs 陣列 5,000 組窗）；cr0 ＝ research11.cl_stats（平均、SE 差 < 1e-12）
 F8 狀態標籤向量版 state_vec ＝ state_label.core 的 label_raw（隨機 30 條 × 全部 i ≥ 20）
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import state_label as SL                                   # ⛔ 只 import（它會 import researchH2 ⇒ 快照路徑）
import researchH2 as H2
from backtest import exit_signal as XS
from backtest import research11 as R11


# ───────── 獨立寫法（⛔ 不呼叫 exit_signal／stop_fractal）─────────
def ind_swings(l, k=5):
    return [s for s in range(k, len(l) - k) if l[s] < min(l[s - k:s]) and l[s] < min(l[s + 1:s + k + 1])]


def ind_events(c, l, k=5):
    c = [float(x) for x in c]; l = [float(x) for x in l]; m = len(c)
    sw = ind_swings(l, k)
    ev = {"甲": [], "乙": [], "丙": []}
    for i in range(1, m):
        conf = [s for s in sw if s + k <= i]
        if conf:
            Y = l[conf[-1]]
            if c[i] < Y and c[i - 1] >= Y:
                ev["甲"].append(i)
        for g, n in (("乙", 20), ("丙", 60)):
            if i >= n:
                ma = sum(c[i - n + 1:i + 1]) / n; mp = sum(c[i - n:i]) / n
                # ⚠ 獨立寫法用 sum/n；與 np.mean 可能差 1 ulp ⇒ 隨機序列不會剛好相等，手造邊界另測
                if c[i] < ma and c[i - 1] >= mp:
                    ev[g].append(i)
    return ev


def rand_series(seed, m=400):
    r = np.random.default_rng(seed)
    c = 50 * np.exp(r.normal(0, 0.02, m).cumsum())
    h = c * (1 + np.abs(r.normal(0, 0.01, m))); l = c * (1 - np.abs(r.normal(0, 0.01, m)))
    return h, l, c


def F1():
    # 手造：甲 ——低點序列在 s＝10 有擺動低點 90，第 15 根收盤才確認；第 13 根收盤 90.5（未跌破）；第 22 根收盤 89.5 ⇒ 事件在 22
    m = 30
    l = np.array([95, 94, 93, 94, 95, 96, 95, 94, 93, 92, 90, 91, 92, 93, 94, 95, 96, 97, 96, 95, 94, 92, 89, 88, 87, 88, 89, 90, 91, 92], float)
    c = l + 0.5; c[22] = 89.5; h = c + 1
    assert XS.break_price(l)[1][14] != 10 and XS.break_price(l)[1][15] == 10, "⛔ s＝10 應在第 15 根才確認"
    ev = XS.raw_signals(c, l)
    assert list(np.flatnonzero(ev["甲"])) == [22], np.flatnonzero(ev["甲"])
    # 若第 14 根（確認前一根）就跌破到 89.9 ⇒ 那根低點 ≤ 89.9 < 90 ⇒ s＝10 根本不是擺動點（跌破一定破壞未確認的點）
    # 乙：上升 100 根後第 100 根急跌到 MA20 下
    cc = 100 + 0.5 * np.arange(130); cc[100:] = cc[99] - 6 - 0.1 * np.arange(30); ll = cc - 0.2
    ev2 = XS.raw_signals(cc, ll)
    assert 100 in np.flatnonzero(ev2["乙"]) and list(np.flatnonzero(ev2["乙"])) == [100], np.flatnonzero(ev2["乙"])
    # 丙：同一序列 MA60 被跌破的第一天 ＝ 手算（close < MA60 的第一根）
    ma60 = [np.mean(cc[i - 59:i + 1]) for i in range(59, 130)]
    first = next(i for i in range(60, 130) if cc[i] < ma60[i - 59])
    assert list(np.flatnonzero(ev2["丙"])) == [first], (np.flatnonzero(ev2["丙"]), first)
    # 隨機 300 條對獨立寫法
    bad = 0; tot = {"甲": 0, "乙": 0, "丙": 0}
    for sd in range(300):
        h, l, c = rand_series(1000 + sd)
        e = XS.raw_signals(c, l); ie = ind_events(c, l)
        for g in XS.SIGS:
            tot[g] += len(ie[g])
            bad += int(list(np.flatnonzero(e[g])) != ie[g])
    assert bad == 0 and min(tot.values()) > 300, (bad, tot)
    return "F1 手造三訊號日子正確（甲 22、乙 100、丙 {}）；隨機 300 條對獨立寫法逐根相同（事件數 甲 {:,}／乙 {:,}／丙 {:,}）".format(first, tot["甲"], tot["乙"], tot["丙"])


def F2():
    # 乙：c[0..19]＝100 ⇒ MA20_19 ＝ 100 ＝ c[19]（相等 ⇒ 不是跌破）；c[20]＝99 ⇒ 跌破，而 c[19] ＝ MA20_19 算「在線上」
    c = np.r_[np.full(20, 100.0), 99.0, np.full(10, 98.0)]; l = c - 0.5
    e = XS.raw_signals(c, l)
    assert list(np.flatnonzero(e["乙"])) == [20], np.flatnonzero(e["乙"])
    c2 = c.copy(); c2[20] = 100.0                                     # close ＝ MA ⇒ 不跌破
    assert 20 not in np.flatnonzero(XS.raw_signals(c2, c2 - 0.5)["乙"])
    # 甲：Y＝90（s＝5，第 10 根確認）；第 12 根收盤 ＝ 90 ⇒ 不跌破；第 13 根 89.99 且前一根 ＝ 90 ⇒ 跌破
    l = np.array([95, 94, 93, 92, 91, 90, 91, 92, 93, 94, 95, 94, 89.9, 89.5, 89], float)
    c = np.array([96, 95, 94, 93, 92, 91, 92, 93, 94, 95, 96, 95, 90.0, 89.99, 89.5], float)
    Y, S = XS.break_price(l)
    assert Y[12] == 90 and Y[13] == 90 and S[13] == 5, (Y, S)
    e = XS.raw_signals(c, l)
    assert list(np.flatnonzero(e["甲"])) == [13], np.flatnonzero(e["甲"])
    c3 = c.copy(); c3[13] = 90.0; c3[14] = 90.0
    assert len(np.flatnonzero(XS.raw_signals(c3, l)["甲"])) == 0, "⛔ close ＝ Y 不算跌破"
    # 跌破 1%：線 90 ⇒ 門檻 89.1；89.1 不算、89.09 算
    c4 = c.copy(); c4[12] = 90.0; c4[13] = 89.1; c4[14] = 89.2
    assert len(np.flatnonzero(XS.raw_signals(c4, l, "pct1")["甲"])) == 0
    c4[13] = 89.09
    assert list(np.flatnonzero(XS.raw_signals(c4, l, "pct1")["甲"])) == [13]
    # 連 3 日：跌破日 13、14 收盤 < Y、15 收盤 < Y ⇒ 事件在 15；15 收回 ⇒ 無事件
    l5 = np.r_[l, 88, 87]; c5 = np.r_[c, 89.0, 88.0]
    assert list(np.flatnonzero(XS.raw_signals(c5, l5, "d3")["甲"])) == [15], np.flatnonzero(XS.raw_signals(c5, l5, "d3")["甲"])
    c6 = c5.copy(); c6[15] = 90.5; l6 = l5.copy(); l6[15] = 90.3
    assert len(np.flatnonzero(XS.raw_signals(c6, l6, "d3")["甲"])) == 0
    # 平盤股 ⇒ 0 事件（MA 逐根 np.mean，⛔ 不出 1 ulp 假跌破）
    fl = np.full(200, 10.3)
    assert sum(int(v.sum()) for v in XS.raw_signals(fl, fl).values()) == 0
    return "F2 等號邊界：close＝線 不算跌破、close_{T−1}＝線 算在線上（甲、乙）；跌破 1%（89.1 不算／89.09 算）；連 3 日（第三日收回 ⇒ 無）；平盤 0 事件"


def trunc_check(fn, seeds, m=260):
    """fn(h,l,c) ⇒ dict of arrays（逐根）。截斷在 i、或把 i 之後改成任意值，≤ i 的輸出須不變。回 不同的 (seed, i) 數。"""
    bad = 0
    for sd in seeds:
        h, l, c = rand_series(sd, m)
        full = fn(h, l, c)
        r = np.random.default_rng(sd + 7)
        for i in range(0, m, 7):
            tr = fn(h[:i + 1], l[:i + 1], c[:i + 1])
            h2, l2, c2 = h.copy(), l.copy(), c.copy()
            c2[i + 1:] = r.uniform(1, 200, m - i - 1); l2[i + 1:] = c2[i + 1:] * 0.9; h2[i + 1:] = c2[i + 1:] * 1.1
            mu = fn(h2, l2, c2)
            for k in full:
                a, b, d = np.asarray(full[k][:i + 1]), np.asarray(tr[k][:i + 1]), np.asarray(mu[k][:i + 1])
                same = lambda x, y: (np.array_equal(x, y, equal_nan=True) if x.dtype.kind == "f" else np.array_equal(x, y))
                if not (same(a, b) and same(a, d)):
                    bad += 1; break
    return bad


def fn_ok(h, l, c):
    Y, _ = XS.break_price(l); e = XS.raw_signals(c, l); e1 = XS.raw_signals(c, l, "pct1")
    return {"Y": Y, "m20": XS.sma_exact(c, 20), "m60": XS.sma_exact(c, 60), **{"e" + g: e[g] for g in XS.SIGS},
            **{"p" + g: e1[g] for g in XS.SIGS}, "lab": XS.state_vec(h, l, c).astype(str)}


def fn_leak_swing(h, l, c):                   # ⛔ 故意：未確認的擺動點（右邊只走完 4 根就用）
    Y, _ = XS.break_price(l, lag=4); return {"Y": Y, "e": XS.raw_signals(c, l, lag=4)["甲"]}


def fn_leak_ma(h, l, c):                      # ⛔ 故意：用到當天之後一根的收盤（MA 右移）
    m = XS.sma_exact(c, 20); lead = np.r_[m[1:], np.nan]
    return {"m": lead}


def F3F4():
    seeds = list(range(2000, 2040))
    b0 = trunc_check(fn_ok, seeds)
    assert b0 == 0, "⛔ 正式版有前視：{}".format(b0)
    # Y ＝ state_label.core 的 break_adj（逐位元）
    bad = 0; nn = 0
    for sd in seeds:
        h, l, c = rand_series(sd, 200)
        Y, _ = XS.break_price(l)
        for i in range(0, 200):
            r = SL.core(h[:i + 1], l[:i + 1], c[:i + 1])
            a, b = Y[i], r["break_adj"]
            nn += 1
            if not ((np.isnan(a) and np.isnan(b)) or a == b):
                bad += 1
    assert bad == 0, bad
    # F4 鑑別力
    b1 = trunc_check(fn_leak_swing, seeds); b2 = trunc_check(fn_leak_ma, seeds)
    assert b1 > 0 and b2 > 0, (b1, b2)
    diff = 0
    for sd in seeds:
        h, l, c = rand_series(sd, 260)
        diff += int(not np.array_equal(XS.raw_signals(c, l)["甲"], XS.raw_signals(c, l, lag=4)["甲"]))
    assert diff > 0
    return ("F3 無前視：截斷／i 之後改任意值 ⇒ ≤ i 的 Y、MA20、MA60、三訊號（收盤與 1%）、狀態標籤全不變（40 條 × 每 7 根一個截點，差 0）；"
            "Y ＝ state_label.core break_adj 逐位元（{:,} 點）｜F4 鑑別力：未確認擺動點（lag 4）被抓到 {} 次、MA 用明天收盤被抓到 {} 次；"
            "lag 4 的甲事件與正式版不同 {}／40 條").format(nn, b1, b2, diff)


def mk_ctx(n, valid=None, trd=None, dn_o=None, o=None, pb_at=(), delisted=False):
    valid = np.ones(n, bool) if valid is None else valid
    trd = valid.copy() if trd is None else trd
    dn_o = np.zeros(n, bool) if dn_o is None else dn_o
    o = np.where(valid, 10.0, np.nan) if o is None else o
    pb = np.zeros(n, bool)
    for p in pb_at:
        pb[p] = True
    import researchM_freq as RF
    last = int(np.flatnonzero(valid)[-1])
    g5 = RF._g5(valid, upto=last if delisted else None)
    return {"nb": np.cumsum(valid), "nxt": XS.next_sellable(trd, dn_o, o), "lv": XS.last_valid(valid), "valid": valid, "trd": trd,
            "dn_o": dn_o, "cs_pb": np.cumsum(pb), "cs_g5": np.cumsum(g5), "ncal": n, "delisted": delisted, "last": last}


def F5():
    n = 400; o = np.full(n, 25.0); c = np.full(n, 25.0)
    X = mk_ctx(n)
    Rs = []
    for H in (5, 20, 60, 120):
        st = XS.statuses([100, 150, 200], H, X, 0, n - 1)
        for r in st:
            assert r["狀態"] == "保留"
            Rs.append(XS.ret(o, c, r["s"], r["j_end"]))
    Rs = np.array(Rs)
    m, se, _ = XS.cr0(Rs, np.arange(len(Rs)) % 3)
    assert np.all(Rs == 0) and m == 0 and se == 0, (Rs, m, se)
    return "F5 0 報酬 ⇒ R_H ＝ 0（H＝5／20／60／120 各 3 筆，全為 0）、E ＝ 0、CR0 SE ＝ 0"


def F6():
    n = 300
    valid = np.ones(n, bool); valid[101] = False                     # T＝100 ⇒ T+1 停牌
    dn = np.zeros(n, bool); dn[102] = True                           # T+2 開盤跌停
    X = mk_ctx(n, valid=valid, dn_o=dn)
    r = XS.statuses([100], 20, X, 0, n - 1)[0]
    assert r["狀態"] == "保留" and r["s"] == 103 and r["遞延天數"] == 2 and r["遞延原因"] == "停牌" and r["x"] == 122, r
    # 開盤缺值 ⇒ 遞延、原因「開盤缺值」
    o = np.full(n, 10.0); o[101] = np.nan
    X2 = mk_ctx(n, o=o)
    r = XS.statuses([100], 20, X2, 0, n - 1)[0]
    assert r["s"] == 102 and r["遞延原因"] == "開盤缺值", r
    # 終點停牌 ⇒ 用前一根；下市 ⇒ 下市了結
    v3 = np.ones(n, bool); v3[119] = False                           # T＝100, s＝101, x＝120 … 用 x＝119? 設 H＝19 ⇒ x＝119
    X3 = mk_ctx(n, valid=v3)
    r = XS.statuses([100], 19, X3, 0, n - 1)[0]
    assert r["j_end"] == 118 and r["終點"] == "停牌跨終點", r
    v4 = np.ones(n, bool); v4[110:] = False
    X4 = mk_ctx(n, valid=v4, delisted=True)
    r = XS.statuses([100], 20, X4, 0, n - 1)[0]
    assert r["狀態"] == "保留" and r["j_end"] == 109 and r["終點"] == "下市了結", r
    v5 = np.ones(n, bool); v5[101:] = False
    r = XS.statuses([100], 20, mk_ctx(n, valid=v5, delisted=True), 0, n - 1)[0]
    assert r["狀態"] == "剔除_賣不掉", r
    # 80 根閘
    X6 = mk_ctx(n)
    st = XS.statuses([78, 79], 5, X6, 0, n - 1)
    assert st[0]["狀態"] == "剔除_K棒不足" and st[1]["狀態"] == "保留", st
    # 合併
    st = XS.statuses([100, 120, 121, 141, 142], 5, X6, 0, n - 1)
    assert [r["狀態"] for r in st] == ["保留", "合併掉", "保留", "合併掉", "保留"], [r["狀態"] for r in st]
    # 硬斷點窗 [T−60, x]：T＝100、H＝20 ⇒ x＝120
    for p, want in ((40, "剔除_硬斷點"), (39, "保留"), (120, "剔除_硬斷點"), (121, "保留")):
        r = XS.statuses([100], 20, mk_ctx(n, pb_at=(p,)), 0, n - 1)[0]
        assert r["狀態"] == want, (p, r)
    # 連續缺 5 日（全在窗內才算）
    v7 = np.ones(n, bool); v7[36:41] = False                          # 36..40 ⇒ 40 ＝ T−60 ⇒ 只有 1 天在窗內 ⇒ 不剔
    r = XS.statuses([100], 20, mk_ctx(n, valid=v7), 0, n - 1)[0]; assert r["狀態"] == "保留", r
    v8 = np.ones(n, bool); v8[40:45] = False
    r = XS.statuses([100], 20, mk_ctx(n, valid=v8), 0, n - 1)[0]; assert r["狀態"] == "剔除_硬斷點", r
    # 判定窗：T＋H ≤ 窗尾
    assert len(XS.statuses([100], 20, X6, 0, 119)) == 0 and len(XS.statuses([100], 20, X6, 0, 120)) == 1
    return ("F6 遞延（T＋1 停牌、T＋2 開盤跌停 ⇒ s＝T＋3、遞延 2 日、原因停牌；開盤缺值 ⇒ 遞延）、終點停牌 ⇒ 前一根、下市 ⇒ 下市了結、"
            "之後無成交 ⇒ 剔除_賣不掉、80 根閘（79 根不產生／80 根產生）、合併（T、T＋20 合併、T＋21 保留）、斷點窗 [T−60, 終點] 四個邊界、"
            "連缺 5 日全在窗內才算、判定窗 T＋H ≤ 窗尾")


def F7():
    r = np.random.default_rng(5); bad = 0
    for _ in range(50):
        n = 300
        pb = r.random(n) < 0.01; g5 = r.random(n) < 0.01
        S = {"cs_pb": np.cumsum(pb), "cs_g5": np.cumsum(g5)}
        for _ in range(100):
            a = int(r.integers(0, n)); b = int(r.integers(0, n))
            bad += int(H2.brk(S, a, b) != XS.brk(S["cs_pb"], S["cs_g5"], a, b))
    assert bad == 0, bad
    x = r.normal(0, 0.05, 3000); g = r.integers(0, 110, 3000)
    cs = R11.cl_stats(x, g); m, se, k = XS.cr0(x, g)
    assert abs(cs["mean"] - m) < 1e-12 and abs(cs["se"] - se) < 1e-12 and cs["months"] == k
    return "F7 brk ＝ researchH2.brk（5,000 組窗，差 0）；cr0 ＝ research11.cl_stats（平均、SE 差 < 1e-12、群數同）"


def F8():
    bad = 0; nn = 0
    for sd in range(3000, 3030):
        h, l, c = rand_series(sd, 180)
        v = XS.state_vec(h, l, c)
        for i in range(20, 180):
            r = SL.core(h[:i + 1], l[:i + 1], c[:i + 1]); nn += 1
            bad += int(v[i] != r["label_raw"])
    assert bad == 0, bad
    return "F8 狀態標籤向量版 ＝ state_label.core label_raw（{:,} 點，差 0）".format(nn)


def run_all():
    msgs = [F1(), F2(), F3F4(), F5(), F6(), F7(), F8()]
    for m in msgs:
        print("✅ " + m, flush=True)
    print("✅ selftest_exit_signal 全部通過（{} 組）".format(len(msgs)), flush=True)
    return msgs


if __name__ == "__main__":
    run_all()
