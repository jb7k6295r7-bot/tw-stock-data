# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 改用賣 5 出場 seq1（裁定 seq492）——自測（fixture＋重現＋PIT＋閘＋策略鎖）。回測線計算子代理。
⛔ 不算、不印任何報酬；原版權益只比 eq_sha。⛔ 不 commit、不改既有檔。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLSell5_check [--procs 3] [--fast]

 C1 合成序列 fixture：賣 5 觸發（逐根迴圈獨立算 MA200／斜率 vs 向量化 X5）、隔天開盤賣；上限 250（不觸發 ⇒ e＋250 收盤，xpos ＝ cap）；
    買進日已符合賣 5（d ＝ e ⇒ e 之後第一根開盤、H ＝ 2）；同根取較低（X ＝ cap ⇒ min(開, 收)）；停牌跨上限；觸發後下一根跨壞根 ⇒ 觸發日收盤、xpos ＝ d＋1；
    沒觸發遇壞根 ⇒ 壞根前最後一根收盤、xpos ＝ 賣出根＋1；壞根切段（MA200 不跨壞根）；資料尾仍持有；停止交易經濟口徑（econ）；port_stats 合成路徑。
 C2 真實股票：X5 逐根迴圈獨立重算（壞根切段）抽 60 檔全序列；PIT ＝ 截到第 t 根重算 X5[t] 與全序列相同（抽 60 檔 × 每檔 10 天）。
 C3 出場模擬器重現正式出場：x5 全假、cap ＝ xf − e ⇒ 每列 sale ＝ xpos ＝ xf、kind ＝ close（兩世界、兩策略全部 xf ＜ 資料尾的列）。
 C4 重現：sig_with(原出場) 乾跑引擎（價格 1、成本 0）成交清單 ＝ 正式 IG.eng（真實價格）成交清單（兩世界 × 營量 r0、營飆 r0～199）；
    sig_with(原出場, 真實價格) 走引擎 eq_sha ＝ resultsYL_integrate（只比 sha）；賣 5 版 sig 只動 xpos／g 兩欄、其餘欄與列逐位元相同。
 C5 閘（營飆）：SIG[閘] ＝ 窗內訊號 ∧ 0050 regime[e−1]（重算）；SIG[無閘] ＝ 窗內訊號；營飆正式買進全部 regime[e−1] 為真。
 C6 策略鎖：strategy_lock.check() ＝ []，且鎖內 25 支 git diff HEAD 無改動。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchYLSell5 as Y                   # noqa: E402
from backtest import researchAddOn as AO                    # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import strategy_lock as SLK                   # noqa: E402

RES = {}


def ok(name, cond, detail=""):
    RES[name] = {"通過": bool(cond), "說明": detail}
    print(f"[{'✓' if cond else '✗'}] {name} {detail}", flush=True)


# ═════════════ 獨立參考：逐根迴圈 X5 ═════════════
def x5_loop(c, badv, maw=200, sl=20):
    n = len(c); out = np.zeros(n, bool); s0 = 0
    for k in range(n):
        if k > 0 and badv[k]:
            s0 = k
        if k - (maw - 1) - sl >= s0:
            ma = sum(c[k - maw + 1:k + 1]) / maw
            ma2 = sum(c[k - sl - maw + 1:k - sl + 1]) / maw
            out[k] = (c[k] < ma) and (ma < ma2)
    return out


def near_tie(c, badv, maw=200, sl=20):
    """浮點近乎相等的根（滾動平均 vs 直接平均可能翻）⇒ 不比。"""
    n = len(c); out = np.zeros(n, bool); s0 = 0
    for k in range(n):
        if k > 0 and badv[k]:
            s0 = k
        if k - (maw - 1) - sl >= s0:
            ma = sum(c[k - maw + 1:k + 1]) / maw; ma2 = sum(c[k - sl - maw + 1:k - sl + 1]) / maw
            out[k] = abs(c[k] - ma) <= 1e-9 * abs(ma) or abs(ma - ma2) <= 1e-9 * abs(ma)
    return out


# ═════════════ C1 合成 fixture ═════════════
def mkpk(c, o=None, bad=None, n0=None, bars=None):
    n0 = len(c) if n0 is None else n0
    o = c.copy() if o is None else o
    bars = np.ones(n0, bool) if bars is None else bars
    idx = np.flatnonzero(bars)
    bad_cal = np.zeros(n0 + 1, bool) if bad is None else np.r_[bad, False]
    LB = (idx, c[idx].copy(), c[idx].copy(), c[idx].copy())
    W = {"closes": {"S": np.r_[c, c[-1]]}, "opens": {"S": np.r_[o, o[-1]]}}
    HB = {"S": (np.r_[bars, False], bad_cal)}
    return Y.stock_pack(W, "S", LB, HB, n0, n0 + 1)


def c1():
    n = 900
    t = np.arange(n, dtype=float)
    up = 100 + 0.2 * t                                   # 一路上漲：不觸發
    pk = mkpk(up)
    ok("C1a 上漲序列 X5 全假", not pk["x5"].any())
    e = 300
    X = Y.sell5_exit(pk, e, n)
    ok("C1b 上限 250：不觸發 ⇒ e＋250 收盤、xpos ＝ cap", X["kind"] == "close" and X["sale"] == e + 250 and X["xpos"] == e + 250 and X["reason"] == "上限250", str(X["reason"]))
    # 先漲後跌：MA200 下彎後收盤在線下
    c = np.r_[100 + 0.5 * t[:500], 350 - 0.8 * (t[500:] - 500)]
    o = c * 1.001
    pk = mkpk(c, o)
    ref = x5_loop(list(c), np.zeros(n, bool))
    ok("C1c 合成 X5 ＝ 逐根迴圈", bool(np.array_equal(pk["x5"], ref)), f"首觸發根 {int(np.flatnonzero(ref)[0]) if ref.any() else -1}")
    d0 = int(np.flatnonzero(ref)[0])
    e = d0 - 30
    X = Y.sell5_exit(pk, e, n)
    ok("C1d 賣 5 觸發 ⇒ 隔天開盤賣", X["kind"] == "open" and X["d"] == d0 and X["sale"] == d0 + 1 and X["xpos"] == d0 + 1 and X["px"] == o[d0 + 1], str(X))
    X = Y.sell5_exit(pk, d0 + 5, n)
    ok("C1e 買進日已符合賣 5 ⇒ d ＝ e、e＋1 開盤賣、H ＝ 2", X["d"] == d0 + 5 and X["sale"] == d0 + 6 and X["sale"] - (d0 + 5) + 1 == 2)
    # 同根取較低：手給 x5，觸發在 cap−1
    pk2 = mkpk(up, up * 1.01)
    x5 = np.zeros(n, bool); e = 100; x5[e + 249] = True
    X = Y.sell5_exit(pk2, e, n, x5=x5)
    ok("C1f X ＝ cap ⇒ 同根取較低 min(開, 收)", X["kind"] == "minoc" and X["sale"] == e + 250 and X["px"] == min(up[e + 250] * 1.01, up[e + 250]) and "同根取較低" in X["flags"])
    # 停牌跨上限：cap 附近停牌
    bars = np.ones(n, bool); bars[e + 249:e + 253] = False
    pk3 = mkpk(up, up, bars=bars)
    x5 = np.zeros(n, bool); x5[e + 248] = True
    X = Y.sell5_exit(pk3, e, n, x5=x5)
    ok("C1g 停牌跨上限 ⇒ 復牌第一根開盤賣、旗標", X["kind"] == "open" and X["sale"] == e + 253 and "停牌跨上限" in X["flags"], str(X))
    # 沒觸發、上限根停牌 ⇒ cap 以前最後一根有效收盤
    X = Y.sell5_exit(pk3, e, n, x5=np.zeros(n, bool))
    ok("C1h 上限根無成交 ⇒ 之前最後一根收盤、xpos ＝ cap", X["kind"] == "close" and X["sale"] == e + 248 and X["xpos"] == e + 250 and "上限根無成交" in X["flags"])
    # 壞根：沒觸發 ⇒ 壞根前最後一根收盤、xpos ＝ 賣出根＋1
    bad = np.zeros(n, bool); bad[e + 100] = True
    pk4 = mkpk(up, up, bad=bad)
    X = Y.sell5_exit(pk4, e, n)
    ok("C1i 持有中遇壞根 ⇒ 壞根前收盤、xpos ＋1", X["kind"] == "cclose" and X["sale"] == e + 99 and X["xpos"] == e + 100 and X["reason"] == "壞根前強制")
    # 觸發後下一根跨壞根
    bad = np.zeros(n, bool); bad[e + 51] = True
    pk5 = mkpk(up, up, bad=bad)
    x5 = np.zeros(n, bool); x5[e + 50] = True
    X = Y.sell5_exit(pk5, e, n, x5=x5)
    ok("C1j 觸發後下一根是壞根 ⇒ 觸發日收盤、xpos ＝ d＋1", X["kind"] == "cclose" and X["sale"] == e + 50 and X["xpos"] == e + 51)
    # 壞根切段：壞根後 MA200 重新累積
    bad = np.zeros(n, bool); bad[600] = True
    pk6 = mkpk(c, o, bad=bad)
    badv = Y.bad_on_bars(pk6["idx"], bad)
    ref6 = x5_loop(list(c), badv)
    ok("C1k 壞根切段 X5 ＝ 逐根迴圈（壞根後 219 根內不成立）", bool(np.array_equal(pk6["x5"], ref6)) and not pk6["x5"][600:600 + 219].any())
    # 壞根落在非 K 棒日 ⇒ 下一根有效 K 棒當新段起點
    bars7 = np.ones(n, bool); bars7[600:606] = False
    bad7 = np.zeros(n, bool); bad7[603] = True
    pk7 = mkpk(c, o, bad=bad7, bars=bars7)
    bv = Y.bad_on_bars(pk7["idx"], bad7)
    ok("C1l 非 K 棒日壞根 ⇒ 下一根有效 K 棒標壞根", bool(bv[int(np.searchsorted(pk7["idx"], 606))]) and int(bv.sum()) == 1)
    # 資料尾仍持有
    X = Y.sell5_exit(pk, n - 100, n, x5=np.zeros(n, bool))
    ok("C1m cap 超過資料尾 ⇒ 資料尾仍持有、xpos ＝ n0", X["kind"] == "end" and X["xpos"] == n and X["sale"] == n - 1)
    x5 = np.zeros(n, bool); x5[n - 1] = True
    X = Y.sell5_exit(pk, n - 100, n, x5=x5)
    ok("C1n 資料尾當天才觸發 ⇒ 仍持有", X["kind"] == "end")
    # 觸發後再也沒有成交（下市）⇒ 觸發日收盤
    bars8 = np.ones(n, bool); bars8[e + 61:] = False
    pk8 = mkpk(up, up, bars=bars8)
    x5 = np.zeros(n, bool); x5[e + 60] = True
    X = Y.sell5_exit(pk8, e, n, x5=x5)
    ok("C1o 觸發後無成交 ⇒ 觸發日收盤、xpos ＝ d＋1", X["kind"] == "cclose" and X["sale"] == e + 60 and X["xpos"] == e + 61)
    # econ
    cc = np.arange(10.0)
    ok("C1p 停止交易經濟口徑 ＝ L＋1、L 收盤", Y.econ(9, 8, 1.0, 5, cc) == (6, 5, 5.0, 1) and Y.econ(6, 5, 1.0, 5, cc) == (6, 5, 1.0, 0))
    # port_stats 合成路徑（N＝2；第 0 段 5 天）
    W = {"NP": 12, "segp": {"段": (1, 5)}}
    Y.STR["_T"] = {"N": 2}
    buys = [(1, "A"), (1, "B"), (4, "C")]; sells = [(4, "A"), (9, "B"), (10, "C")]
    cand = pd.DataFrame({"sid": ["A", "B", "C", "D", "B", "E"], "entry_pos": [1, 1, 4, 2, 3, 4]})
    st = Y.port_stats(W, "_T", buys, sells, cand, {("A", 1): 3, ("B", 1): 8, ("C", 4): 6})["段"]
    del Y.STR["_T"]
    ok("C1q port_stats：滿倉日、名額不足、已持有、補位鍵", st["滿倉日比例"] == 1.0 and st["名額不足沒進"] == 2 and st["已持有沒進"] == 1 and st["買進筆"] == 3,
       json.dumps({k: v for k, v in st.items() if k != "買進鍵"}, ensure_ascii=False))


# ═════════════ 世界、逐股 ═════════════
def build(procs):
    WS = AO.worlds(print, procs)
    out = {}; X1 = None
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; n0 = len(cal)
        sids = sorted(set(W["SIG"][False]["sid"]) | set(W["SIG"][True]["sid"]))
        M, HB, X1, info = AO.market(wn, W, X1, print, sids)
        del M
        Y._G["data"] = W["data"]; Y._G["cal"] = cal
        with Pool(procs) as pool:
            LBS = dict(pool.map(Y.bars_job, [(s, W["uni"].get(s, "twse")) for s in sids], chunksize=8))
        PK = {s: Y.stock_pack(W, s, LBS[s], HB, n0, W["NP"]) for s in sids}
        out[wn] = {"PK": PK, "LBS": LBS, "HB": HB, "n0": n0}
    return WS, out


def c2(WS, B, nsamp=60):
    rng = np.random.default_rng(20261030)
    bad_ct = 0; pit_bad = 0; tot = 0; tie = 0; pit_n = 0
    for wn in ("主", "早年"):
        PK, LBS, HB, n0 = B[wn]["PK"], B[wn]["LBS"], B[wn]["HB"], B[wn]["n0"]
        sids = sorted(PK)
        for s in rng.choice(sids, size=min(nsamp // 2, len(sids)), replace=False):
            idx, h, l, cb = LBS[s]; m = idx < n0; idx, h, l, cb = idx[m], h[m], l[m], cb[m]
            badv = Y.bad_on_bars(idx, np.asarray(HB[s][1], bool)[:n0])
            ref = x5_loop(list(cb), badv); nt = near_tie(list(cb), badv)
            got = PK[s]["x5"][idx]
            bad_ct += int(((got != ref) & ~nt).sum()); tie += int(nt.sum()); tot += len(idx)
            for k in rng.choice(np.arange(250, len(idx)), size=10, replace=False):
                X5k, _ = Y.x5_features(cb[:k + 1], h[:k + 1], l[:k + 1], badv[:k + 1])
                pit_bad += int(X5k[k] != got[k]); pit_n += 1
    ok("C2a 真實股票 X5 ＝ 逐根迴圈（壞根切段；近乎相等根不比）", bad_ct == 0, f"不同 {bad_ct}／{tot} 根；近乎相等 {tie} 根")
    ok("C2b PIT：截到第 t 根重算 X5[t] ＝ 全序列", pit_bad == 0, f"不同 {pit_bad}／{pit_n}")


def c3(WS, B):
    tot = 0; bad = 0; skip = 0; xb = 0
    for wn in ("主", "早年"):
        W = WS[wn]; PK, n0 = B[wn]["PK"], B[wn]["n0"]
        for sn, S in Y.STR.items():
            sig = W["SIG"][S["G"]]; sig = sig[sig[f"xpos_H{S['H']}"] >= 0]
            for s, e, xf in zip(sig["sid"], sig["entry_pos"].astype(int), sig[f"xpos_H{S['H']}"].astype(int)):
                if xf >= n0:
                    skip += 1; continue
                nb_ = int(PK[s]["nbad"][e + 1])
                if 0 <= nb_ <= xf:
                    xb += 1; continue                         # 正式窗內有壞根（減資等）：正式不截、本件壞根前強制 ⇒ 另計
                X = Y.sell5_exit(PK[s], e, n0, cap=xf - e, x5=np.zeros(n0, bool))
                tot += 1
                bad += int(not (X["kind"] == "close" and X["sale"] == xf and X["xpos"] == xf))
    ok("C3 出場模擬器（x5 全假、cap ＝ xf − e）重現正式出場根", bad == 0, f"不同 {bad}／{tot}；T1 補回略過 {skip}；正式窗內有壞根另計 {xb}")


def job_off(a):
    wn, sn, r = a
    o, au = IG.eng(Y._G["WS"][wn], Y.STR[sn]["key"], r, audit=True)
    return wn, sn, r, IG.sha(np.asarray(o["equity"], float)), Y.trade_list(au)


def job_orig_real(a):
    wn, sn, r = a
    W = Y._G["WS"][wn]; S = Y.STR[sn]; sig = Y._G["SIGO"][(wn, sn)]
    if sn == "營量":
        o = R.simulate_mtm(sig, f"H{S['H']}", S["N"], np.random.default_rng(RR.P1_SEED0 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"])
    else:
        o = R.simulate_mtm(sig, f"H{S['H']}", S["N"], np.random.default_rng(RR.P10_SEED0 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                           stop_force=W["SF"])
    return wn, sn, r, IG.sha(np.asarray(o["equity"], float))


def c4(WS, B, procs, fast):
    Y._G["WS"] = WS; Y._G["COST0"] = R.COST
    seeds = (lambda sn: [0] if sn == "營量" else (list(range(5)) if fast else list(range(Y.NSEED))))
    jobs = [(wn, sn, r) for wn in ("主", "早年") for sn in Y.STR for r in seeds(sn)]
    with Pool(procs) as pool:
        off = pool.map(job_off, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    OFF = {(wn, sn, r): tl for wn, sn, r, _, tl in off}
    ok("C4a 正式 IG.eng eq_sha ＝ resultsYL_integrate", all(sh == REF[(wn, Y.STR[sn]["key"], r)] for wn, sn, r, sh, _ in off), f"{len(off)} 條")
    # 逐列（賣 5）只為建 sig；不用任何價格算報酬
    ROWS = {(wn, sn): Y.build_rows(wn, sn, WS[wn], B[wn]["PK"], B[wn]["n0"]) for wn in ("主", "早年") for sn in Y.STR}
    DRY = {}; SIGO = {}; same = True
    for (wn, sn), T in ROWS.items():
        W = WS[wn]; S = Y.STR[sn]
        so = Y.sig_with(W, sn, T, "o", dry=True); sn_ = Y.sig_with(W, sn, T, "n", dry=True)
        base = W["SIG"][S["G"]]
        cols = [c for c in base.columns if c not in (f"xpos_H{S['H']}", f"g_H{S['H']}")]
        same &= bool(sn_[cols].equals(base[cols]) and so[cols].equals(base[cols]) and so[f"xpos_H{S['H']}"].equals(base[f"xpos_H{S['H']}"]))
        cl = Y.ones_prices(W, set(so["sid"]) | set(W["SF"]))
        DRY[(wn, sn, "o")] = {"sig": so, "cl": cl, "op": cl}
        SIGO[(wn, sn)] = Y.sig_with(W, sn, T, "o", dry=False)
        same &= bool(SIGO[(wn, sn)].equals(base))
    ok("C4b sig_with：只動 xpos／g 兩欄，其餘欄、列序逐位元相同；原出場真實價版 ＝ 正式訊號表", same)
    Y._G["DRY"] = DRY; Y._G["SIGO"] = SIGO; Y._G["KEEP_EQ"] = False
    jd = [(wn, sn, "o", r) for wn in ("主", "早年") for sn in Y.STR for r in seeds(sn)]
    with Pool(procs) as pool:
        dres = pool.map(Y.job_dry, jd, chunksize=4)
    nd = 0; nb = 0; nsd = 0; expl = 0; why = []
    for wn, sn, arm, r, tl, *_ in dres:
        off_ = OFF[(wn, sn, r)]; nb += len(off_[0])
        if tl == off_:
            continue
        nd += 1; nsd += len(set(tl[0]) ^ set(off_[0]))
        e_, w_ = explain(WS[wn], sn, r, off_, tl, REF)
        expl += int(e_); why.append(w_)
    ok("C4c 原出場乾跑（價格 1、成本 0）成交清單 ＝ 正式（真實價格）；不同者第一個分歧日 ＝ 正式「有空槽、現金不夠」擋掉（log 'a'）",
       expl == nd and (nb == 0 or nsd / nb <= 0.01), f"不同 {nd}／{len(dres)} 條（已解釋 {expl}）；買進對稱差 {nsd}／{nb} 筆；{why[:4]}")
    with Pool(procs) as pool:
        rr = pool.map(job_orig_real, jobs, chunksize=4)
    ok("C4d 原出場 sig_with 真實價格走引擎 eq_sha ＝ resultsYL_integrate", all(sh == REF[(wn, Y.STR[sn]["key"], r)] for wn, sn, r, sh in rr), f"{len(rr)} 條")
    ok("C4e 引擎成本已還原 0.585%", abs(R.COST - Y.COST) < 1e-15)
    return OFF, ROWS


def explain(W, sn, r, off_, tl, REF):
    """真實價格、log 開（不改抽籤：log 只記去向）重跑正式；eq_sha 要 ＝ 正式；找第一個買進分歧日 t*：
    正式在 t* 有候選被標 'a'，且 t* 收盤後持股數 ＜ N（有空槽卻沒買 ⇒ 現金不夠）⇒ 已解釋。"""
    S = Y.STR[sn]; lg = []; au = []
    seed0 = RR.P1_SEED0 if sn == "營量" else RR.P10_SEED0
    kw = dict(log=lg, d_max=None, pick="relvol", queue_days=0) if sn == "營量" else dict(log=lg)
    o = R.simulate_mtm(W["SIG"][S["G"]], f"H{S['H']}", S["N"], np.random.default_rng(seed0 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                       stop_force=W["SF"], audit=au, **kw)
    sh_ok = IG.sha(np.asarray(o["equity"], float)) == REF[(W["name"], S["key"], r)]
    bo, bd = off_[0], tl[0]
    t_star = next((min(a[0], b[0]) for a, b in zip(bo, bd) if a != b), None)
    if t_star is None:
        return False, "找不到分歧日"
    nb_ = sum(1 for t, _ in bo if t <= t_star); ns_ = sum(1 for t, _ in off_[1] if t <= t_star)
    a_ = [x["sid"] for x in lg if x["t"] == t_star and x["reason"] == "a"]
    return bool(sh_ok and a_ and (nb_ - ns_) < S["N"]), {"世界": W["name"], "策略": sn, "r": r, "t*": int(t_star), "收盤持股": nb_ - ns_, "被擋a": a_[:3], "log版sha同": bool(sh_ok)}


def c5(WS, OFF):
    okk = True; nb = 0
    det = {}
    for wn, W in WS.items():
        base = W["SIG"][False]; reg = np.asarray(RR.regime_mask(np.asarray(W["bench"], float)), bool)
        e = base["entry_pos"].to_numpy(int)
        exp = base[reg[e - 1]]
        cal = W["cal"]; w0, w1 = W["w0"], W["w1"]
        inwin = bool(((e >= w0) & (e <= w1)).all())
        det[wn] = {"有閘列": len(W["SIG"][True]), "重算列": len(exp), "窗內": inwin}
        okk &= bool(W["SIG"][True].equals(exp)) and inwin
        for (wn2, sn, r), (buys, _) in OFF.items():
            if wn2 == wn and sn == "營飆":
                nb += sum(int(not reg[t - 1]) for t, _ in buys)
    ok("C5 營飆閘：SIG[閘] ＝ 窗內訊號 ∧ 0050 regime[e−1]（rerun17.regime_mask 重算）；營飆正式買進全在閘內", okk and nb == 0, f"閘外買進 {nb}｜{det}")


def c6():
    diff = SLK.check()
    files = [f"backtest/{m}.py" for m in SLK.closure()]
    gd = subprocess.run(["git", "diff", "--name-only", "HEAD", "--"] + files, capture_output=True, text=True).stdout.split()
    st = subprocess.run(["git", "status", "--porcelain", "--"] + files, capture_output=True, text=True).stdout.strip()
    ok("C6 策略鎖相符、鎖內檔與 HEAD 無差異", not diff and not gd and not st, f"鎖內 {len(files)} 支；check {diff}；git diff {gd}；status {st!r}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    T0 = time.time()
    c6()
    c1()
    WS, B = build(a.procs)
    c2(WS, B)
    c3(WS, B)
    OFF, ROWS = c4(WS, B, a.procs, a.fast)
    c5(WS, OFF)
    c6()
    allok = all(v["通過"] for v in RES.values())
    print(f"[總結] {'全部通過' if allok else '有不通過'}｜{sum(v['通過'] for v in RES.values())}／{len(RES)}｜{time.time() - T0:.0f}s", flush=True)
    od = os.path.join(Y.OUT, "freq"); os.makedirs(od, exist_ok=True)
    json.dump({"時間": Y.now_tpe() + "（台北）", "fast": a.fast, "結果": RES, "全部通過": allok}, open(os.path.join(od, "check.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
