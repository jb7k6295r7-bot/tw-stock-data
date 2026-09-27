# -*- coding: utf-8 -*-
"""PREREG外部作者追加 seq1（台股策略線登錄 seq1 sha 48cbe3c0f1fccd3e「外部作者追加三顆：薛俊原 S1、方天龍 F1、OANDA O1」；
裁定 seq250、251、252 §二、253 §二 發號 N ＋3（外部作者合計 ＋10）；⚠ 事後追加）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtAuth2.py selftest|pre|body|early [--procs 2] [--reps 200] [--fake 1000]

⭐ 做法全照 PREREG外部作者 seq1（researchExtAuth.py；⛔ 不改它，只 import）：母體、價量、進出場時點、10 檔 1/10、抽籤 200 顆取中位、無停損、
   不設天數上限、再進場、成本 0.585%、窗（探索／確認／主窗）、均線（fsum、含當根）、跌破 ＝ 由上往下穿越、只看持有期間、20 日均量不含當日、實體定義、
   退化格排除、挑法、判定（確認段＋主窗全段都過才合格）、假訊號臂、單筆層口徑
⭐ 新規（裁定 seq255 §一 4）：停止交易強制出場：開 ⇒ 所有引擎呼叫帶 stop_force＝research11.stop_force_days(valid, 段尾)（commit 51a3dc35f3）
⭐ 新規（裁定 seq253 §一 3）：單筆層「穩」＝ 相鄰視窗本身也過 95% 門檻；只同向 ⇒「方向一致，但只有 X 天過門檻」
⭐ 裁定 seq253 §二：S1 與 Y2 出／Y4／Y5 共用基準的格【同一次跑出】（本檔重跑 Y2 出、Y4 兩臂、Y5 × H 與基準，停止交易強制出場同開）
═══ 三顆（登錄 §二；★ 補定照裁定 seq253 全部接受）═══
  S1（出場疊加）：高檔 ＝ 收 ≥ max(高 t−59～t) × 0.90；量縮 ＝ 5 日均量（含當日）＜ 20 日均量（不含當日）× 0.7；
      量縮過久 ＝ 高檔且量縮連續 ≥ 10 根；觸發日 t ＝（★）在一段量縮過久的連續段之中（至 t 已連續 ≥ 10 根）或該段結束後 5 根內，
      且 量 ≥ 20 日均量 × 1.5、收 ＜ 前收 ⇒ 次日開盤賣（只看持有期間）
  F1（進；原版＋確認版）：b1～b3 連 3 根黑 K（收 ＜ 開）且｜實體｜＜ 2%；下降趨勢（★）＝ c(b1−1) ÷ c(b1−11) − 1 ≤ −5%；
      r ＝ b3＋1：實體 ≥ +3%、開 ≤ b3 收、收 ≥ b1 開、量 ≥ 20 日均量 × 1.5；原版訊號日 ＝ r；確認版 ＝ r＋1～r＋5 第一個收 ＞ max(高 b1～b3)
  O1（進＋自帶出場）：k−1 多頭排列 MA5 ＞ MA10 ＞ MA20 ＞ MA60 且 MA20(k−1) ＞ MA20(k−6)（★ 5 日差）；k 收盤由上往下穿越 MA20；
      站回 ＝ k＋1～k＋3 第一個收 ≥ MA20 ＝ 訊號日；自帶出場 ＝ 持有期間收 ＜ 跌破日 k 最低價 ⇒ 次日開盤賣
═══ 格（登錄 §三）═══
  F1：{原版, 確認版} × {跌破 MA10, MA20, MA60} ＝ 6 格｜O1：{自帶, MA10, MA20, MA60} ＝ 4 格
  S1：基準 ＝ seq1 五顆進場任一（同 Y2 出／Y4／Y5）；基準出場 {抱 20／60／120 日｜跌破 MA10／20／60} ⇒「基準＋S1 誰先到先出」6 格
輸出 backtest/resultsExtAuth2/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExtAuth as EA                              # ⛔ 不改；只用它的偵測、基準、列、指標
SG, RV, D, RR, R11, L = EA.SG, EA.RV, EA.D, EA.RR, EA.R11, EA.L
H2, TR, MF, AV = EA.H2, EA.TR, EA.MF, EA.AV

HERE = EA.HERE
OUT = os.path.join(HERE, "resultsExtAuth2")
COST = EA.COST
BIG = EA.BIG
SEG = EA.SEG
YEARS_MAIN = EA.YEARS_MAIN
HB, HS = EA.HB, EA.HS
EXOPT = EA.EXOPT
NEW_ENT = ["F1", "F1c", "O1"]
NAME = {"F1": "三線反紅（原版）", "F1c": "三線反紅（確認版）", "O1": "均線假跌破 3 日站回", "S1": "高檔量縮過久補量下跌（出）"}
SE_CODES = ["F1", "F1c", "O1", "S1"]
SE_BEAR = {"S1"}
TAG = "⚠ 事後追加（裁定 seq250～253）；家族 N ＋3（外部作者合計 ＋10）"
SF_TAG = "停止交易強制出場：開"
SEQ1_DIGEST = "29f9a22c6fbcbed5"
_G: dict = {}


# ═════════════════════════════ 偵測（有效 K 棒）
def detect_new(o, h, l, c, v):
    nb = len(c)
    with np.errstate(invalid="ignore", divide="ignore"):
        bd = (c - o) / o
    vm = EA.vma(v, 20)
    v5 = np.full(nb, np.nan)
    if nb >= 5:
        v5[4:] = np.lib.stride_tricks.sliding_window_view(v, 5).mean(axis=1)
    ma = {k: RV.ma_fsum(c, k) for k in (5, 10, 20, 60)}
    out = {}
    # S1
    hh = np.full(nb, np.nan)
    if nb >= 60:
        hh[59:] = np.lib.stride_tricks.sliding_window_view(h, 60).max(axis=1)
    with np.errstate(invalid="ignore"):
        both = np.isfinite(hh) & (c >= hh * 0.90) & np.isfinite(v5) & np.isfinite(vm) & (v5 < vm * 0.7)
    run = 0; last_end = -10 ** 9; s1 = []; cur_len = 0
    for t in range(nb):
        if both[t]:
            run += 1
        else:
            if run >= 10:
                last_end = t - 1
            run = 0
        elig = run >= 10 or (1 <= t - last_end <= 5)
        if elig and t >= 1 and np.isfinite(vm[t]) and v[t] >= vm[t] * 1.5 and c[t] < c[t - 1]:
            s1.append(t)
    out["S1"] = np.array(s1, int)
    # F1
    f1 = {}; f1c = {}
    for r in range(15, nb):
        b1, b2, b3 = r - 3, r - 2, r - 1
        if not all(c[b] < o[b] and abs(bd[b]) < 0.02 for b in (b1, b2, b3)):
            continue
        if not (c[b1 - 1] / c[b1 - 11] - 1 <= -0.05):
            continue
        if not (bd[r] >= 0.03 and o[r] <= c[b3] and c[r] >= o[b1] and np.isfinite(vm[r]) and v[r] >= vm[r] * 1.5):
            continue
        f1.setdefault(r, b1)
        top = max(h[b1], h[b2], h[b3])
        for d in range(r + 1, min(r + 5, nb - 1) + 1):
            if c[d] > top:
                f1c.setdefault(d, b1); break
    out["F1"] = np.array(sorted(f1), int); out["F1_first"] = np.array([f1[k] for k in sorted(f1)], int)
    out["F1c"] = np.array(sorted(f1c), int); out["F1c_first"] = np.array([f1c[k] for k in sorted(f1c)], int)
    # O1
    o1 = {}; o1k = []
    for k in range(6, nb):
        a = k - 1
        if not (np.isfinite(ma[60][a]) and ma[5][a] > ma[10][a] > ma[20][a] > ma[60][a] and ma[20][a] > ma[20][k - 6]):
            continue
        if not (c[a] >= ma[20][a] and c[k] < ma[20][k]):
            continue
        j_ = -1
        for j in range(k + 1, min(k + 3, nb - 1) + 1):
            if c[j] >= ma[20][j]:
                j_ = j; break
        o1k.append((k, j_))
        if j_ >= 0 and j_ not in o1:
            o1[j_] = (k, float(l[k]))
    js = sorted(o1)
    out["O1"] = np.array(js, int); out["O1_k"] = np.array([o1[j][0] for j in js], int); out["O1_low"] = np.array([o1[j][1] for j in js], float)
    out["O1_all"] = np.array(o1k, int).reshape(-1, 2)
    return out


def stock_work2(args):
    sid, market = args
    cal = _G["cal"]; n = len(cal); mode = _G["mode"]
    res = EA.stock_work((sid, market))                     # seq1 的訊號（W1…、均線跌破、Y2 出、Y5、MA5…）＋ c、valid
    if res is None:
        return None
    st = D.load_stock(sid, market, cal); df = st.df
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    B = detect_new(o[bars], h[bars], l[bars], c[bars], v[bars])
    S = res["S"]
    for k in ("S1", "F1", "F1c", "O1"):
        S[k] = bars[B[k]].astype(np.int32)
    S["F1_first"] = bars[B["F1_first"]].astype(np.int32) if len(B["F1_first"]) else np.zeros(0, np.int32)
    S["F1c_first"] = bars[B["F1c_first"]].astype(np.int32) if len(B["F1c_first"]) else np.zeros(0, np.int32)
    S["O1_k"] = bars[B["O1_k"]].astype(np.int32) if len(B["O1_k"]) else np.zeros(0, np.int32)
    S["O1_low"] = B["O1_low"]
    oa = B["O1_all"]
    S["O1_all"] = np.stack([bars[oa[:, 0]], np.where(oa[:, 1] >= 0, bars[np.maximum(oa[:, 1], 0)], -1)], 1) if len(oa) else np.zeros((0, 2), int)
    # 多頭吞噬（researchRev 原版 L_ENG）⇒ F1 重疊率
    ro, rh, rl, rc, _ = RV.load_raw(sid, cal)
    sel = lambda x: np.asarray(x, float)[bars]
    ev = RV.detect(sel(o), sel(h), sel(l), c[bars], sel(v), sel(ro), sel(rh), sel(rl), sel(rc))
    S["ENG"] = np.array(sorted({int(bars[t]) for t, _ in ev["L_ENG"]}), np.int32)
    res["S"] = S
    if mode != "body":
        return res
    # ── 單筆層（researchExtAuth 同口徑）
    w0, w1, mon, elig = _G["w0"], _G["w1"], _G["mon"], _G["elig"]
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = MF._g5(valid, upto=ds["last"]) if delisted else MF._g5(valid)
    SB = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    lv = AV.last_valid(valid); em = elig.get(sid, set())
    halt = ~tb["trd"] | ~np.isfinite(o)
    FIRST = {"F1": S["F1_first"], "F1c": S["F1c_first"], "O1": np.maximum(S["O1_k"] - 60, 0) if len(S["O1_k"]) else np.zeros(0, int),
             "S1": np.maximum(S["S1"] - 60, 0)}
    evr = []
    for code in SE_CODES:
        T0 = np.asarray(S[code], int); F0 = np.asarray(FIRST[code], int)
        for H in HS:
            m = (T0 >= w0) & (T0 <= w1 - H)
            T, Fs = T0[m], F0[m]
            if len(T):
                m2 = np.array([mon[t] in em for t in T], bool); T, Fs = T[m2], Fs[m2]
            kp = RV.merge20(T)
            for t, f, k in zip(T, Fs, kp):
                if not k:
                    continue
                t = int(t)
                why = ("剔除_硬斷點" if H2.brk(SB, int(f), t + H) else
                       ("剔除_停牌" if halt[t + 1] else ("剔除_開盤漲停" if tb["up_o"][t + 1] else ("剔除_開盤跌停" if tb["dn_o"][t + 1] else "保留"))))
                r = {"sid": sid, "code": code, "H": H, "T": t, "st": why}
                if why == "保留":
                    r["R"] = float(c[lv[t + H]] / o[t + 1] - 1.0)
                evr.append(r)
    res["ev"] = evr
    # 放棄組：F1 沒確認 ⇒ 照原版（r 次日開盤買 20 日）；O1 沒站回 ⇒ k 次日開盤買 20 日（主窗、eligible、非停牌、無硬斷點）
    ab = []
    conf_r = set()
    for rr, b1 in zip(S["F1"], S["F1_first"]):
        rr = int(rr)
        ok = [d for d in S["F1c"] if rr < d <= rr + 5]
        if w0 <= rr <= w1 - 21 and mon[rr] in em and not halt[rr + 1] and not H2.brk(SB, int(b1), rr + 21):
            ab.append({"sid": sid, "code": "F1", "T": rr, "確認": bool(ok), "R20": float(c[lv[rr + 20]] / o[rr + 1] - 1.0)})
    for k_, j_ in S["O1_all"]:
        k_ = int(k_)
        if w0 <= k_ <= w1 - 21 and mon[k_] in em and not halt[k_ + 1] and not H2.brk(SB, k_ - 60, k_ + 21):
            ab.append({"sid": sid, "code": "O1", "T": k_, "確認": bool(j_ >= 0), "R20": float(c[lv[k_ + 20]] / o[k_ + 1] - 1.0)})
    res["ab"] = ab
    # 全市場基準（四類單獨口徑）上的 S1
    ok_buy = AV.trade_ok(tb["trd"], tb["up_o"], o); ok_sell = AV.trade_ok(tb["trd"], tb["dn_o"], o); nxt_sell = AV.next_true(ok_sell)
    xs = np.zeros(n, bool); xs[S["S1"]] = True
    q = []
    for T_ in _G["MEAS"].get(sid, []):
        e = int(T_) + 1
        for H in HB:
            x = e + H - 1
            seg = "探索" if (e >= _G["P"]["探索"][0] and x <= _G["P"]["探索"][1]) else ("確認" if (e >= _G["P"]["確認"][0] and x <= _G["P"]["確認"][1]) else "")
            if not seg or x >= n:
                continue
            if not ok_buy[e]:
                q.append({"sid": sid, "e": e, "H": H, "seg": seg, "st": "進場日漲停或停牌"}); continue
            if bool(AV.brk_vec(SB["cs_pb"], SB["cs_g5"], e, x)[0]):
                q.append({"sid": sid, "e": e, "H": H, "seg": seg, "st": "硬斷點"}); continue
            P0 = float(o[e]); base = float(c[lv[x]] / P0 - 1.0 - COST)
            bi = bars[(bars >= e) & (bars <= x - 1)]
            w = bi[xs[bi]]; d = int(w[0]) if len(w) else -1
            s_ = int(nxt_sell[d + 1]) if (d >= 0 and d + 1 < n) else -1
            r = {"sid": sid, "e": e, "H": H, "seg": seg, "st": "保留", "base": base}
            if d >= 0 and 0 <= s_ < x:
                r["d_S1"] = float((o[s_] / P0 - 1.0 - COST) - base); r["t_S1"] = 1
            else:
                r["d_S1"] = 0.0; r["t_S1"] = 0
            q.append(r)
    res["quad"] = q
    return res


def _init2(d):
    _G.update(d); EA._init({"cal": d["cal"], "mode": "pre", "FUND": d["FUND"]})


# ═════════════════════════════ 列
def o1_rows(SIG, elig, mon, xopt, s0, s1):
    """O1 進場列；xopt ＝ 'OWN'（收 ＜ 跌破日 k 低）或 MA10／20／60。"""
    rows = []; same = 0
    for sid, X in SIG.items():
        em = elig.get(sid)
        if not em:
            continue
        S = X["S"]; js = np.asarray(S["O1"], int)
        if not len(js):
            continue
        cc = X["c"]; vb = X.get("_bars")
        if vb is None:
            vb = np.flatnonzero(np.unpackbits(X["valid"])[:len(mon)].astype(bool)); X["_bars"] = vb
        for j, lowk in zip(js, S["O1_low"]):
            e = int(j) + 1
            if not (s0 <= e <= s1) or mon[j] not in em:
                continue
            if xopt == "OWN":
                bi = vb[(vb >= e) & (vb <= s1)]
                w = bi[cc[bi] < lowk]
                dX = int(w[0]) if len(w) else -1
            else:
                Xd = np.asarray(S[xopt], int); same += int(j in set(Xd.tolist()))
                i = int(np.searchsorted(Xd, e)); dX = int(Xd[i]) if i < len(Xd) and Xd[i] <= s1 else -1
            rows.append((sid, int(j), e, dX))
    return pd.DataFrame(rows, columns=["sid", "t", "entry_pos", "dX"]), same


def ma_base_with(R, SIG, xo, s1, add_s1):
    """基準列＋出場跌破 MA_n（無天數上限）；add_s1 ⇒ 與 S1 誰先到先出。回 dX 與觸發來源。"""
    dX = np.full(len(R), -1, int); why = np.array([""] * len(R), object)
    for i, (sid, e) in enumerate(zip(R["sid"], R["entry_pos"].to_numpy(int))):
        S = SIG[sid]["S"]
        Xd = np.asarray(S[xo], int); k = int(np.searchsorted(Xd, e)); dm = int(Xd[k]) if k < len(Xd) and Xd[k] <= s1 else -1
        ds = -1
        if add_s1:
            Xs = np.asarray(S["S1"], int); k = int(np.searchsorted(Xs, e)); ds = int(Xs[k]) if k < len(Xs) and Xs[k] <= s1 else -1
        cand = [(d, w) for d, w in ((dm, xo), (ds, "S1")) if d >= 0]
        if cand:
            d, w = min(cand); dX[i] = d; why[i] = w
    return dX, why


# ═════════════════════════════ 引擎（帶 stop_force）
def run_one(args):
    key, r, s0, s1 = args
    G = SG._G
    sig, kw, reason, cf = G["CELLS"][key]
    au = []
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), G["cz"], G["oz"], G["ncal"], return_equity=True, audit=au,
                         stop_force=G["SF"][s1], **kw)
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, s1)
    res = SG.summarize(key, r, au, eq, hv, c_, m_, reason, cf, s0, s1)
    cst = sum(float(a["cost"]) / float(a["equity_prev"]) for a in au if a["side"] == "sell" and int(a["t"]) <= s1 and a.get("equity_prev", 0) > 0)
    res["costyr"] = cst / ((s1 - s0 + 1) / 245.0); res["sf_n"] = int(o.get("x_stop_force_n", 0))
    return res


def run_cells(keys, s0, s1, reps, procs, tag, log):
    t0 = time.time(); res = {k: [] for k in keys}
    with Pool(procs) as pool:
        for x in pool.imap_unordered(run_one, [(k, r, s0, s1) for k in keys for r in range(reps)], chunksize=2):
            res[x["key"]].append(x)
    log(f"  [{tag}] {len(keys)} 格 × {reps} 顆｜{time.time() - t0:.0f}s")
    return res


def agg3(rows, bench):
    out = EA.agg2(rows, bench)
    out["停止交易強制出場_每顆"] = float(np.mean([x["sf_n"] for x in rows]))
    return out


def fake_one(i):
    J = SG._G["FAKEJOB"]
    R, xp, s1, s0, hold = J["R"], J["xp"], J["s1"], J["s0"], J["hold"]
    rng = np.random.default_rng([20260927, i]); r = i % 200
    e = R["entry_pos"].to_numpy(int)
    h = rng.choice(hold, size=len(R), replace=True) if len(hold) else np.full(len(R), 10 ** 6)
    dA = e + h - 1
    dA = np.where(dA <= np.minimum(s1, xp - 2), dA, -1)
    sig, kw, _ = EA.make_fixed(R, xp, dA, J["ep"], SG._G["cz"], "rand")
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), SG._G["cz"], SG._G["oz"], SG._G["ncal"], return_equity=True,
                         stop_force=SG._G["SF"][s1], **kw)
    c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)
    return float(c_), float(m_)


def stability2(C):
    """裁定 seq253 §一 3：相鄰視窗本身也過門檻才寫「穩」。"""
    out = {}
    for code, g in C.groupby("code"):
        g = g.set_index("H").reindex(list(HS))
        passed = [H for H in HS if str(g.at[H, "判定"]).startswith("有利")]
        if not passed:
            out[code] = "四個視窗都沒有有利方向的顯著差" if (g["判定"] != "依構造不可判定").any() else "四個視窗都依構造不可判定"
            continue
        parts = []
        bear = code in SE_BEAR
        for H in passed:
            i = HS.index(H); nb = [HS[j] for j in (i - 1, i + 1) if 0 <= j < len(HS)]
            sig = [x for x in nb if str(g.at[x, "判定"]).startswith("有利")]
            same = [x for x in nb if np.isfinite(g.at[x, "mean"]) and ((g.at[x, "mean"] < 0) if bear else (g.at[x, "mean"] > 0))]
            if len(sig) == len(nb):
                parts.append(f"{H} 天有利、相鄰（{'／'.join(map(str, nb))} 天）也過門檻 ⇒ 穩")
            elif len(same) == len(nb):
                parts.append(f"{H} 天有利；方向一致，但只有 {'／'.join(str(x) for x in [H] + sig)} 天過門檻")
            else:
                parts.append(f"只在 {H} 天看得到、不穩（相鄰 {'／'.join(str(x) for x in nb if x not in same)} 天方向相反）")
        out[code] = "；".join(parts)
    return out


# ═════════════════════════════ selftest
def selftest():
    ok = []

    def chk(name, got, exp):
        good = list(map(int, got)) == list(exp); ok.append(good)
        print(f"  {'✅' if good else '❌'} {name}：得 {list(map(int, got))}／應 {list(exp)}")

    def flat(nb=120, px=100.0, vol=1000.0):
        return np.full(nb, px), np.full(nb, px * 1.005), np.full(nb, px * 0.995), np.full(nb, px), np.full(nb, vol)
    # F1：c 從 110 跌到 100（b1 前一日對 10 日前 ≤ −5%）；b1～b3＝80～82 小黑；r＝83 紅 K 實體 4%、開 ≤ b3 收、收 ≥ b1 開、量 2 倍；確認 84 收 ＞ 三黑最高
    o, h, l, c, v = flat()
    c[60:69] = 110.0; o[60:69] = 110.0; h[60:69] = 110.5; l[60:69] = 109.5
    c[69:80] = np.linspace(109, 100, 11); o[69:80] = c[69:80]; h[69:80] = c[69:80] * 1.003; l[69:80] = c[69:80] * 0.997
    for b, (oo, cc) in zip((80, 81, 82), ((100.0, 99.5), (99.5, 99.0), (99.0, 98.6))):
        o[b], c[b], h[b], l[b] = oo, cc, oo * 1.002, cc * 0.998
    o[83], c[83], h[83], l[83], v[83] = 98.5, 102.5, 102.8, 98.4, 2000.0
    o[84], c[84], h[84], l[84] = 102.5, 103.0, 103.2, 102.3
    o[85:], c[85:], h[85:], l[85:] = 103.0, 103.0, 103.3, 102.7
    B = detect_new(o, h, l, c, v); chk("F1 原版 ⇒ 83", B["F1"], [83]); chk("F1 確認版 ⇒ 84", B["F1c"], [84])
    v2 = v.copy(); v2[83] = 1400.0
    B = detect_new(o, h, l, c, v2); chk("F1 量不足 ⇒ 無", B["F1"], [])
    # O1：上升趨勢多頭排列，k＝100 收盤跌破 MA20，101 站回
    n = 130; c = np.linspace(50, 120, n); o = c.copy(); h = c * 1.002; l = c * 0.998; v = np.full(n, 1000.0)
    ma20_99 = np.mean(c[80:100]); c[100] = ma20_99 * 0.9; o[100] = c[100]; l[100] = c[100] * 0.99; h[100] = c[99]
    c[101] = c[99]; o[101] = c[101]
    B = detect_new(o, h, l, c, v); chk("O1 k＝100 跌破、101 站回 ⇒ 101", B["O1"], [101])
    chk("O1 自帶出場的 k", B["O1_k"], [100])
    c2 = c.copy(); c2[101:104] = c2[100]; o2 = c2.copy(); h2 = c2 * 1.002; l2 = c2 * 0.998
    B = detect_new(o2, h2, l2, c2, v); chk("O1 3 日沒站回 ⇒ 無", B["O1"], [])
    # S1：高檔量縮連 12 根（量 400、20 日均量 1000 ⇒ 5 日均量 ＜ 700）後，第 3 根爆量 1.6 倍收黑
    o, h, l, c, v = flat(140)
    v[80:92] = 400.0
    v[94] = 1500.0 * 1.2; c[94] = 99.0; o[94] = 100.0
    B = detect_new(o, h, l, c, v)
    vm94 = np.mean(v[74:94]); print(f"    （S1 fixture：20 日均量 {vm94:.0f}、觸發量 {v[94]:.0f} ≥ 1.5 倍 {v[94] >= 1.5 * vm94}）")
    chk("S1 段結束後 5 根內補量收黑 ⇒ 94", B["S1"], [94])
    v3 = v.copy(); v3[94] = 400.0; v3[100] = 1800.0; c3 = c.copy(); c3[94] = 100.0; c3[100] = 99.0
    B = detect_new(o, h, l, c3, v3); chk("S1 段結束 5 根後才補量 ⇒ 無", B["S1"], [])
    allok = all(ok)
    print(f"selftest {'全過' if allok else '⛔ 有不過'}（{sum(ok)}／{len(ok)}）")
    return allok, sum(ok), len(ok)


# ═════════════════════════════ 主程式
def setup(a, log, mode):
    cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
    P = {k: (int(cal.searchsorted(pd.Timestamp(v[0]))), int(cal.searchsorted(pd.Timestamp(v[1])))) for k, v in SEG.items()}
    sids, elig, mk = SG.stock_universe(cal, EA.PANEL, os.path.join(H2.H2D, "meta", "stocks.csv"))
    FUND, fst = EA.load_fund(cal, log)
    init = {"cal": cal, "mode": mode, "FUND": FUND}
    if mode == "body":
        from backtest import p4_features as P4F
        p = P4F.read_panel(EA.PANEL); U = set(sids)
        p = p[p["eligible"].astype(bool) & p["stock_id"].isin(U)]
        pos = {d: i for i, d in enumerate(cal)}
        MEAS = {s: sorted(int(pos[pd.Timestamp(d)]) for d in g["measure_date"] if pd.Timestamp(d) in pos) for s, g in p.groupby("stock_id")}
        init.update(w0=P["主窗"][0], w1=P["主窗"][1], mon=mon, elig=elig, off=TR.load_official(), MEAS=MEAS, P=P)
    t0 = time.time(); SIG = {}
    with Pool(a.procs, initializer=_init2, initargs=(init,)) as pool:
        for i, r in enumerate(pool.imap_unordered(stock_work2, [(s, mk.get(s, "twse")) for s in sids], chunksize=4)):
            if r is not None:
                SIG[r["sid"]] = r
            if (i + 1) % 500 == 0:
                log(f"  [每檔 {mode}] {i + 1}/{len(sids)}｜{time.time() - t0:.0f}s")
    log(f"[每檔 {mode}] {len(SIG)} 檔｜{time.time() - t0:.0f}s")
    return cal, ncal, mon, P, sids, elig, mk, FUND, fst, SIG


def digests(SIG):
    base = {sid: {"S": {k: v for k, v in X["S"].items() if k in SEQ1_KEYS}} for sid, X in SIG.items()}
    h = hashlib.sha256()
    for sid in sorted(SIG):
        for k in sorted(SIG[sid]["S"]):
            if k in SEQ1_KEYS:
                continue
            h.update(f"{sid}|{k}|".encode()); h.update(np.asarray(SIG[sid]["S"][k]).astype(np.float64).tobytes())
    return EA.sig_digest(base), h.hexdigest()[:16]


SEQ1_KEYS = None


def pre_counts(SIG, elig, mon, P, cz, oz, ncal):
    ENT = []
    for code in ("F1", "F1c"):
        for xo in EXOPT:
            rec = {"格": f"{code}|{xo}"}
            for seg in ("探索", "確認", "主窗"):
                R, drop = EA.entry_rows(SIG, elig, mon, code, xo, *P[seg])
                rec[f"{seg}_列"] = int(len(R)); rec[f"{seg}_段尾未出場列"] = int((R["dX"] < 0).sum()) if len(R) else 0
                rec[f"{seg}_訊號日同時跌破（照進）"] = drop
            ENT.append(rec)
    for xo in ["OWN"] + EXOPT:
        rec = {"格": f"O1|{xo}"}
        for seg in ("探索", "確認", "主窗"):
            R, drop = o1_rows(SIG, elig, mon, xo, *P[seg])
            rec[f"{seg}_列"] = int(len(R)); rec[f"{seg}_段尾未出場列"] = int((R["dX"] < 0).sum()) if len(R) else 0
            rec[f"{seg}_訊號日同時跌破（照進）"] = drop
        ENT.append(rec)
    for r in ENT:
        r["主窗事件"] = r["主窗_列"]; r["年均事件"] = r["主窗_列"] / YEARS_MAIN; r["探索_段尾未出場比例"] = r["探索_段尾未出場列"] / max(1, r["探索_列"])
    OV = []
    for seg in ("探索", "確認", "主窗"):
        s0, s1 = P[seg]
        R = EA.base_rows(SIG, elig, mon, s0, s1).reset_index(drop=True)
        ep = np.array([L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])])
        for H in HB:
            xp, d = EA.overlay_days(R, SIG, "S1", H, s1, ep, ncal)
            OV.append({"段": seg, "格": f"S1|H{H}", "基準列": int(len(R)), "有效觸發列": int((d >= 0).sum()), "段尾未出場列": int(((xp == s1 + 1) & (d < 0)).sum())})
        for xo in EXOPT:
            dX, why = ma_base_with(R, SIG, xo, s1, True)
            OV.append({"段": seg, "格": f"S1|{xo}", "基準列": int(len(R)), "有效觸發列": int((why == "S1").sum()), "段尾未出場列": int((dX < 0).sum())})
    return ENT, OV


def main():
    global SEQ1_KEYS
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["selftest", "pre", "body", "early"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--fake", type=int, default=1000)
    a = ap.parse_args()
    if a.mode == "selftest":
        ok, _, _ = selftest(); sys.exit(0 if ok else 1)
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("researchExtAuth2.py", "researchExtAuth.py", "researchSig.py", "researchRev.py", "research11.py")}
    log(f"===== researchExtAuth2 {a.mode} procs={a.procs} reps={a.reps} fake={a.fake} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG}｜{SF_TAG} =====")
    log(f"[程式 sha256] {src}")
    ok, n_ok, n_all = selftest(); ok1, n1, a1 = EA.selftest()
    if not (ok and ok1):
        raise SystemExit("⛔ selftest 不過")
    if a.mode == "early":
        import researchExtAuth2_early as E2
        E2.run(a, log); return
    SP = os.path.join(OUT, "summary.json")
    S = json.load(open(SP, encoding="utf-8")) if os.path.exists(SP) else {}
    S.update({"登錄": "PREREG外部作者追加 seq1 sha 48cbe3c0f1fccd3e；裁定 seq250～253；N ＋3", "性質": TAG, "引擎": SF_TAG, "程式": src,
              "selftest": f"{n_ok}/{n_all}（seq1 偵測 {n1}/{a1}）"})
    cal, ncal, mon, P, sids, elig, mk, FUND, fst, SIG = setup(a, log, "pre" if a.mode == "pre" else "body")
    SEQ1_KEYS = set(k for k in next(iter(SIG.values()))["S"] if k not in ("S1", "F1", "F1c", "O1", "F1_first", "F1c_first", "O1_k", "O1_low", "O1_all", "ENG"))
    d1, d2 = digests(SIG)
    log(f"[閘] seq1 訊號 digest {d1}（seq1 pre ＝ {SEQ1_DIGEST}：{'✅' if d1 == SEQ1_DIGEST else '❌'}）｜新訊號 digest {d2}")
    if d1 != SEQ1_DIGEST:
        raise SystemExit("⛔ 閘：seq1 訊號與 seq1 pre 不同")
    RR.use_snapshot()
    cz, oz = RR.load_prices(sorted(SIG), cal, mk, "branch")
    if a.mode == "pre":
        ENT, OV = pre_counts(SIG, elig, mon, P, cz, oz, ncal)
        exc = {}
        for r in ENT:
            bad = []
            if r["主窗事件"] < 200:
                bad.append("主窗事件 ＜ 200")
            if r["年均事件"] < 10:
                bad.append("年均 ＜ 10")
            if r["探索_段尾未出場比例"] > 0.5:
                bad.append("探索段段尾未出場 ＞ 50%")
            exc[r["格"]] = bad
        OVd = pd.DataFrame(OV)
        for r in OVd[OVd["段"] == "主窗"].itertuples():
            bad = []
            if r.有效觸發列 < 200:
                bad.append("主窗有效觸發 ＜ 200")
            if r.有效觸發列 / YEARS_MAIN < 10:
                bad.append("年均 ＜ 10")
            ex_ = OVd[(OVd["段"] == "探索") & (OVd["格"] == r.格)].iloc[0]
            if ex_["段尾未出場列"] / max(1, ex_["基準列"]) > 0.5:
                bad.append("探索段段尾未出場 ＞ 50%")
            exc[r.格] = bad
        # F1 確認率、O1 站回率、F1 與多頭吞噬重疊、S1 每檔每年觸發
        w0, w1 = P["主窗"]
        f1 = [(sid, int(t)) for sid, X in SIG.items() for t in X["S"]["F1"] if w0 <= t <= w1 and mon[t] in elig.get(sid, set())]
        ov_eng = sum(1 for sid, t in f1 if np.any(np.abs(SIG[sid]["S"]["ENG"].astype(int) - t) <= 2))
        f1c_n = sum(1 for sid, t in f1 if np.any((SIG[sid]["S"]["F1c"] > t) & (SIG[sid]["S"]["F1c"] <= t + 5)))
        o1a = [(sid, int(k), int(j)) for sid, X in SIG.items() for k, j in X["S"]["O1_all"] if w0 <= k <= w1 and mon[k] in elig.get(sid, set())]
        s1n = sum(int(((X["S"]["S1"] >= w0) & (X["S"]["S1"] <= w1)).sum()) for X in SIG.values())
        s1_stocks = sum(1 for X in SIG.values() if len(X["S"]["S1"]))
        pre = {"seq1 訊號 digest": d1, "新訊號 digest": d2, "進場格": ENT, "出場格": OV, "剔除": exc,
               "F1（主窗 eligible）": {"原版事件": len(f1), "有確認": f1c_n, "確認率": f1c_n / max(1, len(f1)), "與多頭吞噬 ±2 日重疊": ov_eng,
                                    "重疊率": ov_eng / max(1, len(f1))},
               "O1（主窗 eligible）": {"跌破事件": len(o1a), "3 日內站回": sum(1 for x in o1a if x[2] >= 0), "站回率": sum(1 for x in o1a if x[2] >= 0) / max(1, len(o1a))},
               "S1（主窗、全母體）": {"觸發": s1n, "有觸發的檔數": s1_stocks, "每檔每年": s1n / max(1, len(SIG)) / YEARS_MAIN}}
        json.dump(pre, open(os.path.join(OUT, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=int)
        S["pre"] = {"完成": time.strftime("%F %T"), "剔除": {k: v for k, v in exc.items() if v}}
        json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        for r in ENT:
            log(f"  [進] {r['格']}：主窗 {r['主窗事件']:,}（年均 {r['年均事件']:.1f}）｜探索 {r['探索_列']:,}、段尾未出場 {r['探索_段尾未出場比例']:.1%}｜確認 {r['確認_列']:,}｜{exc[r['格']] or '—'}")
        for r in OVd[OVd["段"] == "主窗"].itertuples():
            log(f"  [出] {r.格}：主窗基準 {r.基準列:,}、有效觸發 {r.有效觸發列:,}（年均 {r.有效觸發列 / YEARS_MAIN:.1f}）｜{exc[r.格] or '—'}")
        log(f"[F1] {pre['F1（主窗 eligible）']}｜[O1] {pre['O1（主窗 eligible）']}｜[S1] {pre['S1（主窗、全母體）']}｜[pre 完成] {time.time() - t00:.0f}s")
        return
    # ═══════════════ body
    pre = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    if pre["新訊號 digest"] != d2:
        raise SystemExit(f"⛔ 閘：body 重算的新訊號 digest {d2} ≠ pre {pre['新訊號 digest']}")
    log(f"[閘] 新訊號 digest 與 pre 相同 {d2}")
    exc = pre["剔除"]
    valid = {sid: np.unpackbits(X["valid"])[:ncal].astype(bool) for sid, X in SIG.items()}
    SF = {s1: R11.stop_force_days(valid, s1) for (s0, s1) in P.values()}
    bench = RR.load_bench(cal)
    B50 = {seg: RR.bench_row(cal, bench, s0, s1 + 1) for seg, (s0, s1) in P.items()}
    S["0050同段"] = B50
    CELLS = {}; ROWS = {}; OUTC = {}
    SG._G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS, SF=SF)

    def mk_entry(seg, code, xo):
        s0, s1 = P[seg]
        if code == "O1":
            R, _ = o1_rows(SIG, elig, mon, xo, s0, s1)
        else:
            R, _ = EA.entry_rows(SIG, elig, mon, code, xo, s0, s1)
        R = R.reset_index(drop=True)
        SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
        sig, kw, reason = SG.make_cell(R, SD, s1, "無", "無", cz, oz)
        k = (seg, code, xo); CELLS[k] = (sig, kw, reason, None); ROWS[k] = (R, SD["ep"].to_numpy(float), np.full(len(R), s1 + 1))
        return k
    BASE = {}

    def base_of(seg):
        s0, s1 = P[seg]
        if seg not in BASE:
            R = EA.base_rows(SIG, elig, mon, s0, s1).reset_index(drop=True)
            BASE[seg] = (R, np.array([L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]))
        return BASE[seg]

    def mk_over(seg, code, ex):
        """code ∈ S1／Y2out／Y4_MA5／Y4_MA10／Y5／BASE；ex ＝ H20／H60／H120 或 MA10／20／60（只給 S1 與 BASE）。"""
        s0, s1 = P[seg]; R, ep = base_of(seg)
        if ex.startswith("H"):
            xp, d = EA.overlay_days(R, SIG, None if code == "BASE" else code, int(ex[1:]), s1, ep, ncal)
            sig, kw, reason = EA.make_fixed(R, xp, d, ep, cz, code)
        else:
            dX, why = ma_base_with(R, SIG, ex, s1, code == "S1")
            R2 = R.assign(dX=dX)
            sig, kw, reason = SG.make_cell(R2, pd.DataFrame({"ep": ep}), s1, "無", "無", cz, oz)
            reason = {k_: ((w if w else "段尾"), dd) for (k_, (_, dd)), w in zip(reason.items(), why)}
            xp = np.full(len(R), s1 + 1)
        k = (seg, code, ex); CELLS[k] = (sig, kw, reason, None); ROWS[k] = (R, ep, xp)
        return k
    # ── 探索段：全部格（含 seq1 出場三顆與基準，同一次跑）
    keys = [mk_entry("探索", c_, x_) for c_ in ("F1", "F1c") for x_ in EXOPT] + [mk_entry("探索", "O1", x_) for x_ in ["OWN"] + EXOPT]
    keys += [mk_over("探索", c_, f"H{H}") for c_ in ("S1", "Y2out", "Y4_MA5", "Y4_MA10", "Y5", "BASE") for H in HB]
    keys += [mk_over("探索", c_, x_) for c_ in ("S1", "BASE") for x_ in EXOPT]
    res = run_cells(keys, *P["探索"], a.reps, a.procs, "探索段 全部格", log)
    for k in keys:
        OUTC[k] = agg3(res[k], B50["探索"])
    groups = {"F1": [(c_, x_) for c_ in ("F1", "F1c") for x_ in EXOPT], "O1": [("O1", x_) for x_ in ["OWN"] + EXOPT],
              "S1": [("S1", f"H{H}") for H in HB] + [("S1", x_) for x_ in EXOPT]}
    chosen = {}
    for g, lst in groups.items():
        cands = [(("探索",) + x, OUTC[("探索",) + x]) for x in lst if not exc.get(f"{x[0]}|{x[1]}")]
        chosen[g] = SG.pick(cands) if cands else None
    S["探索段挑格"] = {g: (f"{k[1]}|{k[2]}" if k else "依構造不可判定（全部格被剔除）") for g, k in chosen.items()}
    log(f"[挑格] {S['探索段挑格']}")
    # ── 確認段、主窗
    SEQ1_PICK = {"Y2": ("Y2out", "H60"), "Y4": ("Y4_MA10", "H120"), "Y5": ("Y5", "H60")}
    for seg in ("確認", "主窗"):
        keys = []
        for g, k in chosen.items():
            if k is None:
                continue
            _, c_, x_ = k
            if c_ in NEW_ENT:
                keys.append(mk_entry(seg, c_, x_))
            else:
                keys += [mk_over(seg, "S1", x_), mk_over(seg, "BASE", x_)]
        for g, (c_, x_) in SEQ1_PICK.items():                 # seq1 判定格（同一次、同引擎開關；描述對照）
            keys += [mk_over(seg, c_, x_), mk_over(seg, "BASE", x_)]
        keys = list(dict.fromkeys(keys))
        res = run_cells(keys, *P[seg], a.reps, a.procs, f"{seg} 判定格＋seq1 對照", log)
        for k in keys:
            OUTC[k] = agg3(res[k], B50[seg])
    JUD = {}
    for g, k in chosen.items():
        if k is None:
            JUD[g] = {"判定": "依構造不可判定"}; continue
        _, c_, x_ = k
        cf, mw = OUTC[("確認", c_, x_)], OUTC[("主窗", c_, x_)]
        lc, lm = cf["label"], mw["label"]
        fin_ = ("合格" if lc == "合格" and lm == "合格" else "確認段合格、全段未過" if lc == "合格"
                else "另列" if lc == "另列" and lm in ("合格", "另列") else "確認段另列、全段未過" if lc == "另列" else "不合格")
        J = {"格": f"{c_}|{x_}", "確認": {kk: cf[kk] for kk in ("cagr_med", "mdd_med", "ratio", "label")},
             "主窗": {kk: mw[kk] for kk in ("cagr_med", "mdd_med", "ratio", "label")}, "判定": fin_}
        if c_ == "S1":
            for seg in ("確認", "主窗"):
                b = OUTC[(seg, "BASE", x_)]; o_ = OUTC[(seg, "S1", x_)]
                J[f"{seg}_加減不加"] = {"年化差（點）": (o_["cagr_med"] - b["cagr_med"]) * 100, "回落差（點）": (o_["mdd_med"] - b["mdd_med"]) * 100,
                                     "不加_年化": b["cagr_med"], "不加_回落": b["mdd_med"]}
        JUD[g] = J
    CMP = {}
    for g, (c_, x_) in SEQ1_PICK.items():
        CMP[g] = {seg: {"格": f"{c_}|{x_}", "年化": OUTC[(seg, c_, x_)]["cagr_med"], "回落": OUTC[(seg, c_, x_)]["mdd_med"],
                        "不加_年化": OUTC[(seg, "BASE", x_)]["cagr_med"], "不加_回落": OUTC[(seg, "BASE", x_)]["mdd_med"],
                        "年化差（點）": (OUTC[(seg, c_, x_)]["cagr_med"] - OUTC[(seg, "BASE", x_)]["cagr_med"]) * 100} for seg in ("確認", "主窗")}
    S["判定"] = JUD; S["seq1出場顆_同一次重跑（停止交易強制出場開）"] = CMP
    log(f"[判定] {json.dumps({g: j['判定'] for g, j in JUD.items()}, ensure_ascii=False)}")
    # ── 對照：固定持有、假訊號
    for seg in ("探索", "確認"):
        keys = []; s0, s1 = P[seg]
        for g, k in chosen.items():
            if k is None or k[1] not in NEW_ENT:
                continue
            R, ep, _ = ROWS[(seg, k[1], k[2])]
            for H in HB:
                xp = np.minimum(R["entry_pos"].to_numpy(int) + H - 1, s1 + 1)
                sig, kw, reason = EA.make_fixed(R, xp, np.full(len(R), -1), ep, cz, f"H{H}")
                kk = (seg, k[1], f"固定H{H}"); CELLS[kk] = (sig, kw, reason, None); keys.append(kk)
        keys = list(dict.fromkeys(keys))
        if keys:
            res = run_cells(keys, s0, s1, a.reps, a.procs, f"{seg} 固定持有對照", log)
            for kk in keys:
                OUTC[kk] = agg3(res[kk], B50[seg])
    FAKE = {}; s0, s1 = P["確認"]
    for g, k in chosen.items():
        if k is None:
            continue
        kk = ("確認", k[1], k[2]); R, ep, xp = ROWS[kk]
        SG._G["FAKEJOB"] = {"R": R, "xp": np.asarray(xp, int), "s0": s0, "s1": s1, "hold": OUTC[kk]["_hold_pool"], "ep": ep}
        t0 = time.time()
        with Pool(a.procs) as pool:
            fk = pool.map(fake_one, range(a.fake), chunksize=8)
        fc = np.array([x[0] for x in fk]); m = OUTC[kk]["cagr_med"]
        FAKE[g] = {"中位年化": float(np.median(fc)), "p10": float(np.percentile(fc, 10)), "p90": float(np.percentile(fc, 90)),
                   "p（隨機 ≥ 本格）": float((fc >= m).mean()), "次數": a.fake, "贏0050同段比例": float((fc > B50["確認"]["cagr"]).mean())}
        log(f"  [假訊號 {g}] p＝{FAKE[g]['p（隨機 ≥ 本格）']:.3f}｜{time.time() - t0:.0f}s")
    S["假訊號"] = FAKE
    # ── 均線出場主版加報（seq252 §一）：一直沒出場的那批（判定格、確認段）
    NEV = {}
    for g, k in chosen.items():
        if k is None:
            continue
        kk = ("確認", k[1], k[2]); R, ep, xp = ROWS[kk]
        trig = np.array([CELLS[kk][2].get((s_, int(e_)), ("", -1))[1] for s_, e_ in zip(R["sid"], R["entry_pos"])])
        m = trig < 0
        if k[2].startswith("H"):
            NEV[g] = {"不適用": "基準出場為抱滿 H 日（沒觸發 S1 的列在第 H 根收盤出場），不是均線出場"}
        elif m.any():
            ur = np.array([float(cz[s_][s1]) / e_ - 1.0 for s_, e_ in zip(R["sid"][m], ep[m])])
            hd = (s1 - R["entry_pos"].to_numpy(int)[m])
            NEV[g] = {"筆數": int(m.sum()), "占列": float(m.mean()), "段尾未實現報酬_中位": float(np.median(ur)), "p10": float(np.percentile(ur, 10)),
                      "p90": float(np.percentile(ur, 90)), "最長持有（交易日）": int(hd.max())}
        else:
            NEV[g] = {"筆數": 0}
        R.assign(ep=ep, xpos=xp, trig=trig).to_csv(os.path.join(OUT, f"confirm_rows_{g}.csv.gz"), index=False, float_format="%.17g")
    S["一直沒出場的那批（確認段判定格）"] = NEV
    # ── 單筆層
    ev = pd.DataFrame([r for x in SIG.values() for r in x.get("ev", [])])
    ev.to_csv(os.path.join(OUT, "se_events.csv.gz"), index=False, float_format="%.17g")
    DD = pd.read_csv(EA.WIN_DAYS_FILE, dtype={"sid": str}); DD["m"] = mon[DD["d"].to_numpy()]
    key = {(s, int(d)): int(q) for s, d, q in zip(DD["sid"], DD["d"], DD["dec"])}
    SE = []
    for H in HS:
        f = DD[np.isfinite(DD[f"R{H}"]) & (DD["dec"] >= 0)]
        B2 = f.groupby(["m", "dec"])[f"R{H}"].mean()
        sp = f.assign(x=f[f"R{H}"] > 0).groupby(["m", "dec"])["x"].mean(); sn = f.assign(x=f[f"R{H}"] < 0).groupby(["m", "dec"])["x"].mean()
        e = ev[(ev["H"] == H) & (ev["st"] == "保留")]
        for code in SE_CODES:
            k_ = e[e["code"] == code]; bear = code in SE_BEAR
            T = k_["T"].to_numpy(int); Rr = k_["R"].to_numpy(float); mm = mon[T] if len(T) else np.zeros(0, str)
            q = [key.get((s, int(d)), -1) for s, d in zip(k_["sid"], T)]
            b2 = np.array([B2.get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
            bs = np.array([(sn if bear else sp).get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
            okm = np.isfinite(b2)
            st_ = EA.se_stats(Rr[okm] - b2[okm], mm[okm], bear)
            SE.append({"code": code, "名": NAME[code], "方向": "看跌" if bear else "看漲", "H": H, "候選（合併後）": int(((ev["H"] == H) & (ev["code"] == code)).sum()),
                       "保留": int(len(k_)), "R平均": float(Rr[okm].mean()) if okm.any() else np.nan, "基準R平均": float(b2[okm].mean()) if okm.any() else np.nan,
                       "成功率": float(((Rr[okm] < 0) if bear else (Rr[okm] > 0)).mean()) if okm.any() else np.nan,
                       "基準成功率": float(bs[okm].mean()) if okm.any() else np.nan, **st_})
    SEc = pd.DataFrame(SE); stab = stability2(SEc); SEc["穩不穩"] = SEc["code"].map(stab)
    SEc.to_csv(os.path.join(OUT, "se_cells.csv"), index=False)
    AB = pd.DataFrame([r for x in SIG.values() for r in x.get("ab", [])]); AB.to_csv(os.path.join(OUT, "abandon.csv.gz"), index=False, float_format="%.17g")
    S["放棄組"] = {c_: {"事件": int((AB["code"] == c_).sum()), "確認／站回率": float(AB.loc[AB["code"] == c_, "確認"].mean()),
                     "有確認的_20日報酬平均": float(AB.loc[(AB["code"] == c_) & AB["確認"], "R20"].mean()),
                     "沒確認的_20日報酬平均（照原版／k 次日買）": float(AB.loc[(AB["code"] == c_) & ~AB["確認"], "R20"].mean())} for c_ in ("F1", "O1")} if len(AB) else {}
    Q = pd.DataFrame([r for x in SIG.values() for r in x.get("quad", [])])
    Q.to_csv(os.path.join(OUT, "quad_trades.csv.gz"), index=False, float_format="%.17g")
    QD = []; kq = Q[Q["st"] == "保留"]
    for seg in ("探索", "確認"):
        for H in HB:
            qq = kq[(kq["seg"] == seg) & (kq["H"] == H)]; mm = mon[qq["e"].to_numpy(int) - 1]
            x = qq["d_S1"].to_numpy(float)
            m_, se_, ng = AV.cr0(x, mm) if len(x) else (np.nan, np.nan, 0)
            QD.append({"段": seg, "H": H, "出場": "S1", "筆": int(len(x)), "觸發比例": float(qq["t_S1"].mean()) if len(qq) else np.nan,
                       "差平均": m_, "CI低": m_ - 1.96 * se_, "CI高": m_ + 1.96 * se_, "月數": int(ng)})
    pd.DataFrame(QD).to_csv(os.path.join(OUT, "quad_cells.csv"), index=False)
    rows = []
    for k, c in OUTC.items():
        rows.append({"段": k[0], "顆": k[1], "出場／H": k[2], "剔除": "；".join(exc.get(f"{k[1]}|{k[2]}", []) or []),
                     **{kk: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for kk, v in c.items() if not kk.startswith("_")}})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "cells.csv"), index=False)
    aud = []
    for g, k in chosen.items():
        if k is None:
            continue
        kk = ("確認", k[1], k[2]); sig_, kw_, _, _ = CELLS[kk]
        for r in range(3):
            o = R11.simulate_mtm(sig_, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, stop_force=SF[P["確認"][1]], **kw_)
            c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], *P["確認"])
            aud.append({"cell": "|".join(kk), "r": r, "cagr": c_, "mdd": m_, "sf_n": int(o.get("x_stop_force_n", 0))})
    pd.DataFrame(aud).to_csv(os.path.join(OUT, "confirm_audit3.csv"), index=False)
    S["body完成"] = time.strftime("%F %T"); S["秒_body"] = round(time.time() - t00)
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[body 完成] {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
