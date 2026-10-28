# -*- coding: utf-8 -*-
"""researchGranville 自測（合成 fixture；⛔ 不讀任何報酬）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville_check
涵蓋：買1（含走平可、下彎不可）、買2（k 範圍、跌破前 20 日、上揚）、買3（1.02 邊界含等號、前 20 日）、MA200 斜率、停損價、
      出場（停損／賣5／同日／上限 250／同根取較低 seq373／壞根強制出／下市／觸發後跨壞根）、D 百分位只用過去 1,250（numpy 對帳）、
      ≥ 750 門檻、首次進入、壞根切段、60 日去重、配對（產業／十分位／三分位／排除／可進場／抽樣種子）、bootstrap、判定、閘門（正式跑拒跑）、
      PIT（改未來與改當天不影響過去判定）、突變（DMIN、去重 ≤／<、seq373）、已產出檔無報酬欄。
fixture 數值：價格用整數或 2 的冪分數（〈一百二十一〉），MA 相等比較只在整數和上做。
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchGranville as G   # noqa: E402

RES = []


def ok(name, cond, info=""):
    RES.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"｜{info}" if info and not cond else ""), flush=True)


def ma(c, k):
    return float(np.mean(c[k - 199:k + 1]))


# ── 買1 ──────────────────────────────────────────────
def t_buy1():
    pat = np.array([4.0] * 14 + [16.0] * 6)
    c = np.tile(pat, 15)                                   # 300 根，MA 恆 7.6（整數和 ⇒ 相等）
    F = G.seg_features(c, c, c)
    k = 274                                                # 20×13＋14：低 → 高 的轉折、k ≥ 259 才有前 60 根 MA
    ok("買1 走平可：B1[274]", F["B1"][274])
    ok("買1 走平：既非上揚也非下彎", (not F["down"][274]) and abs(F["MA"][274] - F["MA"][254]) == 0.0)
    ok("買1 只在轉折日", set(np.flatnonzero(F["B1"]).tolist()) == {274, 294})
    ok("買1 k<259 不可判（前 60 日 MA 未齊）", (not F["J1"][258]) and F["J1"][259])
    ok("買1 停損價 ＝ 前 60 日最低收盤", F["S1"][274] == 4.0)
    # 下彎 ⇒ 不成立；上揚 ⇒ 成立
    dn = c - np.arange(300) / 64.0
    Fd = G.seg_features(dn, dn, dn)
    ok("買1 下彎不可", (not Fd["B1"][274]) and Fd["down"][274] and ma(dn, 274) < ma(dn, 254))
    upc = c + np.arange(300) / 64.0
    Fu = G.seg_features(upc, upc, upc)
    ok("買1 上揚可", Fu["B1"][274] and ma(upc, 274) > ma(upc, 254))
    # 前 60 日 < MA 只有 39 日 ⇒ 不成立（把 274 前 60 根中三個低點拉到 8（> MA））
    c3 = c.copy()
    for j in (220, 221, 222):                              # 低點（mod 20 ∈ 0..13）42 → 39
        c3[j] = 8.0
    F3 = G.seg_features(c3, c3, c3)
    cnt3 = int(np.sum(c3[214:274] < np.array([ma(c3, j) for j in range(214, 274)])))
    ok("買1 前 60 日 < MA 39 日 ⇒ 不成立", cnt3 == 39 and not F3["B1"][274], f"cnt3={cnt3}")
    c4 = c.copy(); c4[220] = 8.0; c4[221] = 8.0
    F4 = G.seg_features(c4, c4, c4)
    cnt4 = int(np.sum(c4[214:274] < np.array([ma(c4, j) for j in range(214, 274)])))
    ok("買1 前 60 日 < MA 恰 40 日 ⇒ 成立（≥ 邊界）", cnt4 == 40 and F4["B1"][274], f"cnt4={cnt4}")


# ── 買2 ──────────────────────────────────────────────
def mk_up(n, dip_at, dip_len, pre_above=None):
    c = 64.0 + np.arange(n) / 4.0                          # 穩定上揚，收盤恆在 MA 之上
    c[dip_at:dip_at + dip_len] = 32.0
    if pre_above is not None:
        c[pre_above] = 32.0
    return c


def t_buy2():
    c = mk_up(300, 260, 4)
    F = G.seg_features(c, c, c)
    k = 264
    ok("買2 跌破 4 日後站回", F["B2"][k] and ma(c, k) > ma(c, k - 20))
    ok("買2 停損價 ＝ 跌破期間最低", F["S2"][k] == 32.0)
    ok("買2 只取第一次站回", int(F["B2"].sum()) == 1)
    c = mk_up(300, 260, 11)
    ok("買2 跌破 11 日 ⇒ 不成立", not G.seg_features(c, c, c)["B2"][271])
    c = mk_up(300, 260, 10)
    ok("買2 跌破 10 日 ⇒ 成立（k＝10 邊界）", G.seg_features(c, c, c)["B2"][270])
    c = mk_up(300, 260, 4, pre_above=250)                  # 跌破前 20 日內有一天線下
    ok("買2 跌破前 20 日不全在線上 ⇒ 不成立", not G.seg_features(c, c, c)["B2"][264])
    pat = np.array([4.0] * 14 + [16.0] * 6); c = np.tile(pat, 15)
    ok("買2 MA 走平 ⇒ 不成立（須上揚）", not G.seg_features(c, c, c)["B2"].any())


# ── 買3 ──────────────────────────────────────────────
def t_buy3():
    c = 64.0 + np.arange(300) / 4.0
    k = 280
    m = G.seg_features(c, c, c)["MA"][k]
    l = c.copy(); l[k] = m * 1.02
    F = G.seg_features(c, c, l)
    ok("買3 最低 ＝ MA×1.02（含等號）成立", F["B3"][k])
    ok("買3 停損價 ＝ 當天最低", F["S3"][k] == l[k])
    l2 = c.copy(); l2[k] = m * 1.03
    ok("買3 最低 ＞ MA×1.02 ⇒ 不成立", not G.seg_features(c, c, l2)["B3"][k])
    c3 = c.copy(); c3[270] = 32.0
    l3 = c3.copy(); l3[k] = G.seg_features(c3, c3, c3)["MA"][k] * 1.01
    ok("買3 前 20 日有一天線下 ⇒ 不成立", not G.seg_features(c3, c3, l3)["B3"][k])
    pat = np.array([4.0] * 14 + [16.0] * 6); cf = np.tile(pat, 15)
    ok("買3 MA 走平 ⇒ 不成立", not G.seg_features(cf, cf, cf * 0 + 1.0)["B3"].any())


# ── 出場 ──────────────────────────────────────────────
def base_path(n=400, v=100.0):
    c = np.full(n, v); o = np.full(n, v); x5 = np.zeros(n, bool); bad = np.zeros(n, bool)
    return c, o, x5, bad


def t_exit():
    e, S = 10, 90.0; cap = e + 250; cend = 399
    c, o, x5, bad = base_path()
    c[e + 5] = 88.0
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)
    ok("出場 停損先到 ⇒ 次日開盤", X["reason"] == "停損先到" and X["x"] == e + 6 and X["kind"] == "open")
    c, o, x5, bad = base_path(); x5[e + 3] = True
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)
    ok("出場 賣5先到", X["reason"] == "賣5先到" and X["x"] == e + 4)
    c, o, x5, bad = base_path(); x5[e + 3] = True; c[e + 3] = 88.0
    ok("出場 同日兩者", G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)["reason"] == "同日兩者")
    c, o, x5, bad = base_path(); c[e + 3] = 92.0; x5[e + 7] = True; c[e + 2] = 89.5
    ok("出場 停損比賣5早（兩者先到）", G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)["x"] == e + 3)
    c, o, x5, bad = base_path()
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)
    ok("出場 上限 250 日收盤", X["reason"] == "上限250日" and X["x"] == e + 250 and X["kind"] == "close")
    c, o, x5, bad = base_path(); c[cap] = 120.0
    c[cap - 1] = 80.0; o[cap] = 96.0
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)
    ok("出場 觸發在 cap−1 ⇒ 賣出根＝cap ⇒ 取較低（seq373）", X["kind"] == "minoc" and X["x"] == cap and "同根取較低" in X["flags"])
    p, st = G.exit_price(c, o, bad, e, X["x"], X["kind"], cend, 399)
    ok("出場 seq373 價 ＝ min(開, 收)", p == 96.0)
    c, o, x5, bad = base_path(); bad[e + 10] = True
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)
    ok("出場 壞根前強制出", X["reason"] == "壞根前強制出" and X["x"] == e + 9)
    c, o, x5, bad = base_path(); c[e + 20] = 80.0; bad[e + 10] = True
    ok("出場 壞根後的觸發不算", G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)["reason"] == "壞根前強制出")
    c, o, x5, bad = base_path(); c[e + 31:] = np.nan; o[e + 31:] = np.nan
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, e + 30)
    ok("出場 下市末根", X["reason"] == "下市末根" and X["x"] == e + 30)
    c, o, x5, bad = base_path(); c[e + 5] = 88.0; c[e + 6:e + 12] = np.nan; o[e + 6:e + 12] = np.nan; bad[e + 12] = True
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)
    ok("出場 觸發後停牌 ≥5 日復牌（壞根）⇒ 觸發日收盤強制出", X["reason"] == "停損先到→壞根前強制出" and X["x"] == e + 5)
    c, o, x5, bad = base_path(); c[e + 5] = 88.0; c[e + 6] = np.nan; o[e + 6] = np.nan
    X = G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)
    ok("出場 觸發次日無成交 ⇒ 下一根有效開盤", X["x"] == e + 7 and X["kind"] == "open")
    c, o, x5, bad = base_path(); c[e] = 88.0
    ok("出場 進場當天收盤即可觸發（e 收盤）", G.exit_sim(c, o, x5, bad, e, S, cap, cend, 399)["x"] == e + 1)


# ── 乖離 D 分布 ──────────────────────────────────────────────
def t_dev():
    rng = np.random.default_rng(7)
    n = 1700
    c = np.exp(np.cumsum(rng.normal(0, 0.02, n))) * 50
    F = G.seg_features(c, c, c)
    D = F["D"]
    bad_ = 0
    for k in (949, 1000, 1300, 1449, 1450, 1600, 1699):
        w = D[max(0, k - 1250):k]; w = w[np.isfinite(w)]
        p5 = np.percentile(w, 5); p95 = np.percentile(w, 95)
        if not (abs(p5 - F["P5"][k]) <= 1e-12 and abs(p95 - F["P95"][k]) <= 1e-12):
            bad_ += 1
    ok("D 百分位 ＝ numpy percentile（只用 t−1250～t−1）", bad_ == 0)
    ok("D 需 ≥ 750 個值（948 不可、949 可）", (not F["JD"][948]) and F["JD"][949])
    # PIT：改未來、改當天
    c2 = c.copy(); c2[1300:] *= 0.25
    F2 = G.seg_features(c2, c2, c2)
    ok("PIT 改未來不動過去", np.array_equal(F["P5"][:1300], F2["P5"][:1300], equal_nan=True) and np.array_equal(F["OS"][:1300], F2["OS"][:1300]))
    c3 = c.copy(); c3[1200] *= 0.5
    F3 = G.seg_features(c3, c3, c3)
    ok("PIT D(t) 本身不進分布", F3["P5"][1200] == F["P5"][1200] and F3["D"][1200] != F["D"][1200])
    # 首次進入：造一段連續大跌
    c4 = 64.0 + np.zeros(1300); c4 += np.sin(np.arange(1300) / 7.0)
    c4[1200:1210] = 16.0
    F4 = G.seg_features(c4, c4, c4)
    ok("超跌 狀態連續多日、觸發只在第一天", F4["OS"][1200] and F4["OS"][1201] and F4["OSt"][1200] and not F4["OSt"][1201])
    ok("超跌 D < −15% 才成立", F4["D"][1200] < -0.15)
    c5 = c4.copy(); c5[1200:1210] = 64.0 * 0.875 - 0.0                 # D ≈ −12.5% ⇒ 第 5 百分位內但不夠 −15%
    F5 = G.seg_features(c5, c5, c5)
    ok("超跌 D 在百分位內但 > −15% ⇒ 不成立", (not F5["OS"][1200]) and F5["D"][1200] <= F5["P5"][1200])
    c6 = 64.0 + np.zeros(1300) + np.sin(np.arange(1300) / 7.0); c6[1200:1205] = 128.0
    F6 = G.seg_features(c6, c6, c6)
    ok("超漲 D > 30% 且 ≥ 第 95 百分位 ⇒ 觸發第一天", F6["OBt"][1200] and not F6["OBt"][1201])


# ── 壞根切段、去重 ──────────────────────────────────────────────
def t_seg_dedup():
    c = 64.0 + np.arange(600) / 4.0
    bad = np.zeros(600, bool); bad[300] = True
    F = G.stock_features(c, c, c, bad)
    ok("壞根切段：壞根後 199 根內 MA 不可算", np.isnan(F["MA"][300:499]).all() and np.isfinite(F["MA"][499]))
    ok("壞根切段：壞根前不受影響", np.isfinite(F["MA"][299]))
    kept, nd = G.dedup([0, 30, 60, 61, 125])
    ok("60 日去重（≤60 不取）", kept == [0, 61, 125] and nd == 2)


# ── 配對 ──────────────────────────────────────────────
def t_match():
    U = np.arange(10)
    dec = np.array([1, 1, 1, 1, 1, 1, 2, 1, -1, 1]); ter = np.array([2, 2, 2, 2, 2, 3, 2, 2, 2, 2])
    ind = {0: "電子", 1: "電子", 2: "電子", 3: "電子", 4: "電子", 5: "電子", 6: "電子", 7: "塑膠", 8: "電子", 9: ""}
    excl = lambda j: j == 4                                # 當天有訊號
    eok = lambda j: j != 3                                 # 3 不可進場
    out = G.match_day(np.random.default_rng(G.SEED), [0], U, dec, ter, excl, lambda j: ind[j], eok)
    ok("配對 只取同十分位、同三分位、同產業、無訊號、可進場（候選 1、2 ⇒ 全取）", out[0] == ("配到", [1, 2]))
    out = G.match_day(np.random.default_rng(G.SEED), [8], U, dec, ter, excl, lambda j: ind[j], eok)
    ok("配對 分位不可算 ⇒ 配不到", out[8][0] == "分位不可算")
    out = G.match_day(np.random.default_rng(G.SEED), [9], U, dec, ter, excl, lambda j: ind[j], eok)
    ok("配對 無產業 ⇒ 配不到", out[9][0] == "無產業")
    out = G.match_day(np.random.default_rng(G.SEED), [7], U, dec, ter, excl, lambda j: ind[j], eok)
    ok("配對 無候選", out[7][0] == "無候選")
    U = np.arange(8); dec = np.ones(8, int); ter = np.ones(8, int)
    a = G.match_day(np.random.default_rng(G.SEED), [0], U, dec, ter, lambda j: False, lambda j: "x", lambda j: True)
    b = G.match_day(np.random.default_rng(G.SEED), [0], U, dec, ter, lambda j: False, lambda j: "x", lambda j: True)
    ok("配對 ≥3 抽 3、種子可重現、不含本股", a == b and len(a[0][1]) == 3 and 0 not in a[0][1])
    p = G.deciles(np.array([10.0, 20.0, 30.0, np.nan, 20.0]))
    ok("分位 rank pct average（nan 不入母體）", np.allclose(p[[0, 1, 2, 4]], [0.25, 0.625, 1.0, 0.625]) and np.isnan(p[3]))


# ── 統計、判定、閘門 ──────────────────────────────────────────────
def t_stats_gate():
    z = G.cluster_boot(np.zeros(50), np.repeat(np.arange(25), 2))
    ok("bootstrap 0 佔位 ⇒ 0、CI [0,0]、月數 25", z["mean"] == 0 and z["lo"] == 0 and z["hi"] == 0 and z["months"] == 25)
    z = G.cluster_boot(np.ones(30), np.arange(30))
    ok("bootstrap 常數 1 ⇒ CI [1,1]", z["lo"] == 1.0 and z["hi"] == 1.0)
    ok("判定 n_eff < 24 ⇒ 還沒測", G.verdict({"探索": {"mean": 1, "lo": 1, "months": 23}, "確認": {"mean": 1, "lo": 1, "months": 40}}) == "還沒測")
    ok("判定 兩段 > 0 且確認下緣 > 0 ⇒ 通過（暫定）", G.verdict({"探索": {"mean": 1, "lo": -1, "months": 30}, "確認": {"mean": 1, "lo": 0.5, "months": 40}}) == "通過（暫定）")
    ok("判定 方向為負 ⇒ 測不出（不寫反向顯著）", G.verdict({"探索": {"mean": -1, "lo": -2, "months": 30}, "確認": {"mean": -1, "lo": -2, "months": 40}}) == "測不出")
    ok("判定 確認下緣 = 0 ⇒ 測不出（嚴格 >）", G.verdict({"探索": {"mean": 1, "lo": 1, "months": 30}, "確認": {"mean": 1, "lo": 0.0, "months": 40}}) == "測不出")
    g = G.gate
    ok("閘門 無參數 ⇒ 拒跑", g([])[0] == "refuse")
    ok("閘門 --formal 無 ruling ⇒ 拒跑", g(["--formal"])[0] == "refuse")
    ok("閘門 --formal --ruling seq484 ⇒ 拒跑", g(["--formal", "--ruling", "seq484"])[0] == "refuse")
    ok("閘門 --formal --ruling seq485 ⇒ 正式", g(["--formal", "--ruling", "seq485"])[0] == "formal")
    ok("閘門 --formal --dry ⇒ 拒跑", g(["--formal", "--dry", "--ruling", "seq485"])[0] == "refuse")
    ok("閘門 --formal --limit ⇒ 拒跑", g(["--formal", "--ruling", "seq485", "--limit", "5"])[0] == "refuse")
    ok("閘門 --dry ⇒ 乾跑", g(["--dry"])[0] == "dry")
    ok("閘門 未知參數 ⇒ 拒跑", g(["--dry", "--xyz"])[0] == "refuse")


# ── 突變（〈一百一十三〉：fixture 要分得出錯的實作）──────────────────────────────
def t_mutation():
    rng = np.random.default_rng(7)
    c = np.exp(np.cumsum(rng.normal(0, 0.02, 1100))) * 50
    old = G.DMIN
    try:
        G.DMIN = 749
        F = G.seg_features(c, c, c)
        ok("突變 DMIN=749 ⇒ 948 變可判（fixture 抓得到）", F["JD"][948])
    finally:
        G.DMIN = old
    ok("突變 去重若用 < ⇒ 60 會被取（fixture 抓得到）", G.dedup([0, 60])[0] == [0] and G.dedup([0, 60], gap=59)[0] == [0, 60])
    c_, o_, x5, bad = base_path(); cap = 260; c_[cap - 1] = 80.0; o_[cap] = 96.0; c_[cap] = 120.0
    X = G.exit_sim(c_, o_, x5, bad, 10, 90.0, cap, 399, 399)
    p_open = o_[cap]; p_close = c_[cap]
    ok("突變 seq373 若取開盤或取收盤會不同（fixture 抓得到）", p_open != p_close and G.exit_price(c_, o_, bad, 10, X["x"], X["kind"], 399, 399)[0] == min(p_open, p_close))


# ── 已產出檔：無報酬欄 ──────────────────────────────────────────────
def t_outputs():
    od = os.path.join(G.OUT, "freq")
    if not os.path.isdir(od):
        ok("產出檔（尚未產出，略）", True); return
    bad = []
    forbid = ("報酬", "超額", "勝率", "R_", "ret", "price", "價")
    for f in glob.glob(os.path.join(od, "events_*.csv.gz")):
        cols = pd.read_csv(f, nrows=0).columns
        bad += [f"{os.path.basename(f)}:{c}" for c in cols if any(k in c for k in forbid) and c not in ("進場",)]
    ds = pd.read_csv(os.path.join(od, "desc_dryrun_status.csv"))
    ok("產出 events 無報酬／價格欄", not bad, str(bad))
    ok("產出 描述欄乾跑檔只有 filled／EMPTY（不寫值）", set(ds.columns) == {"section", "cell", "stat", "n", "status"} and set(ds["status"]) <= {"filled", "EMPTY"})


def main():
    for f in (t_buy1, t_buy2, t_buy3, t_exit, t_dev, t_seg_dedup, t_match, t_stats_gate, t_mutation, t_outputs):
        f()
    n = len(RES); p = sum(1 for _, x in RES if x)
    print(f"\n自測 {p}/{n} 通過")
    sys.exit(0 if p == n else 1)


if __name__ == "__main__":
    main()
