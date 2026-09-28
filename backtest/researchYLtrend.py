# -*- coding: utf-8 -*-
"""PREREG營量趨勢 seq1（台股策略線 登錄 sha 5cee2ce099553bb4；裁定 seq265 §二 發號、N ＋1）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLtrend [--procs 2] [--seeds 200] [--reps 200] [--report]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchYLtrend_check.py

問：① 營量 v1 訊號再加一道趨勢確認會不會更好（甲族）？② 把「強勢股 5 取 3」換成單純趨勢定義，會不會一樣好或更好（乙族）？

═══ 本線讀法（⭐ 看任何本件數字前寫死）═══
 Y1 營量 v1 ＝ T1 版（rerun17.setup_and(..., t1=True)）、stop_force 開；引擎 research11.simulate_mtm(sig, "H{H}", 20, default_rng(7000＋r), log=[], d_max=None,
    pick="relvol", queue_days=0, stop_force)；閘：營量 v1（H60、AND 全部）200 顆 ＝ resultsT1fix c13 t1 逐位元；早年 ＝ resultsYLretest b2e「main|開|N20|H60」逐位元
 Y2 趨勢（t−1 ＝ 訊號根 k 收盤；還原價、有效 K 棒；research11.load_bars 的 c）：
    T1 MA5 ＞ MA10 ＞ MA20 ＞ MA60｜T2 收盤 ＞ MA20 ＞ MA60｜T3 收盤 ≥ 近 250 根最高收盤 × 0.90（research11._roll_max(c, 250)）｜
    T4 動能 ＝ 月底[m−2] ÷ 月底[m−8] − 1（m ＝ 訊號根所在曆月；月底 ＝ 該月最後一根有效收盤；缺 ⇒ NaN）在「當月量測日 W1 eligible 全體（動能有限者）」前 30%
       （avgdown.deciles 同式：由小到大、同值依代號序、rank×10//n ≥ 7；該股不在母體 ⇒ 動能 ≥ 前 30% 最小值即算）；MA ＝ research11._roll_mean（有效 K 棒）；NaN ⇒ 不成立
 Y3 甲族 ＝ 營量 v1 的 AND 列（窗內）∧ Tk（訊號根 k）；⛔ 不重新去重
 Y4 乙族 ＝ 候選根 ∧ Tk，同檔 20 根去重（k − 上一個保留 k ＞ 20，同 research11.stock_features 的去重式；在「候選 ∧ Tk」上去重、全歷史連續）：
    候選根 ＝ research11.stock_features 的 eligible 根（≥ 249 根、非 skip、MA100 與 amt_ratio 有值、訊號根與前 20 根無壞根）∧ 營收旗標
    營收旗標 ＝ research13.and_flags 同式：訊號根當下最新一期營收面板列（signal_pos ≤ pos、距離 ≤ STALE_MAX 45）rev_hi24（面板 ＝ 營量 v1 同一份 panel_rev）
    relvol ＝ researchp1.feat_worker 同式（amt[k] ÷ 前 60 根成交額中位數）；母體 ＝ 營量 v1 AND 的同一批股票來源（主：load_universe ∩ gate3；早年：早年版面 load_universe）
 Y5 出場 H ∈ {40, 60, 80}：research11.fixed_exit(o, c, k, H, next_bad[max(0, k−20)]) ＋ T1 資料尾補回（rerun17.t1_censor 同式）；早年另加 R8 減資截斷（researchYLretest.exits_H 同式）
    閘：自算的 H60 出場（xpos、g）＝ 營量 v1 AND 表（T1 後）逐列相同（主、早年各一）
 Y6 段：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（主窗同一條權益、rerun17.win_metrics 段內讀）｜早年 2012-06-04～2014-12-31（營量 v1 早年版面、只上市）
    2005～2012-05 早年延伸段：⛔ 本件不做（營量 v1 早年版面的 W1 母體要法人資料、2012-05 起才有；另起要另建版面）
 Y7 退化（挑前排除）：探索段平均持股 ＜ 10（audit 逐日重建）或現金 ＞ 30%（1 − 平均持股市值 ÷ 權益）；挑格：探索段先合格、再比值（年化中位 ÷ |回落中位|；同分年化高）
    判：確認、早年兩段各自對 0050 同段（使用者判準），件標籤 ＝ 兩段較嚴者
 Y8 主比較（對營量 v1 同段，同顆種子配對）：日報酬差 d_t ＝ r_格,t − r_v1,t，200 顆平均 ⇒ 月分群 CR0 ⇒ 平均 × 245 的 95% CI；另報年化中位差、回落中位差
    「比營量 v1 好」＝ 確認段 CI 下緣 ＞ 0 且 早年段平均差 ＞ 0；「比營量 v1 差」＝ 確認段 CI 上緣 ＜ 0 且 早年平均差 ＜ 0；
    確認段 CI 不含 0 但早年反向 ⇒「不穩」；確認段 CI 含 0 ⇒「分不出」（裁定 seq265 §二）
 Y9 219 對照（裁定 seq265 §二）：挑中格主窗（2017-03-02～2026-08-24）比值 ＝ 年化中位 ÷ |回落中位| ⇒ 在 resultsYLretest/b2_rand219.csv「每顆種子 44 設定取最大比值」分佈的百分位（≤ 的比例）
 Y10 假訊號臂（挑中格；各 --reps 次、引擎種子 7000＋i）：甲族 ＝ 每個訊號日在當日 AND 列中均勻抽「與 Tk 同數量」（同日同通過率）；
     乙族 ＝ 每個訊號日在「當日候選根」（去重前、不看 Tk）中均勻抽「與本格當日同數量」；抽樣 default_rng([20260928, 族, i])；p ＝ 假比值 ≥ 本格比值中位 的比例（各段）
 Y11 挪起點（K4 ④）：挑中格與營量 v1 在確認段、早年段各自「重新起始」：訊號只收進場 ≥ 段首 ＋ {0, 5, 10, 15, 20} 個交易日、權益從該日量到段尾；0050 同窗重算
 Y12 現實版（K3、描述）：researchSlip 的「現實版（C1 0.3%＋C2 50 萬＋C3＋C4）」與「現實版＋C5 低消 20 元」，照 researchT1fix.slip_setup 的 T1 接法；挑中格與營量 v1、主窗
     閘：營量 v1 現實版 T1 200 顆 ＝ resultsT1fix slip13_real t1、slip13_c5 t1（年化、回落 repr）
 Y13 新規矩 ③（登錄 §四）：挑中格確認或早年「合格／另列」⇒ 描述：(b) 持有期間收盤 ＜ MA60（有效 K 棒）⇒ 次一有效根開盤賣（改 xpos／g，research11.cond_exit 同式）；
     (a)「全賣全買」是換股簿的變體，本件是事件型固定持有、沒有換股日 ⇒ 不適用（寫明）
 必報：各 Tk 在營量 v1 訊號中的通過率（甲）、乙族訊號數與平均持股、各年報酬（年化中位的逐年版：每顆逐年報酬取中位）、換手與成本
輸出 backtest/resultsYLtrend/
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

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import research13 as R13
from backtest import avgdown as AV
from backtest import universe_gate as UG

OUT = "backtest/resultsYLtrend"
HS = (40, 60, 80)
TK = ("T1", "T2", "T3", "T4")
SEED0 = 7000
MPANEL = "backtest/resultsp9_engine/panel_ext.csv.gz"
SEG_C = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
SHIFTS = (0, 5, 10, 15, 20)
ORDER = {"不合格": 0, "另列": 1, "合格": 2}
_G: dict = {}
_W: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def label(c, m, b):
    bc, bm = b
    return "合格" if (c > bc and c / abs(m) >= bc / abs(bm)) else ("另列" if c > bc else "不合格")


# ═════════════ 每檔特徵 ═════════════
def feat(args):
    sid, mk = args
    cal = _G["cal"]; ncal0 = len(cal)
    B = R11.load_bars(sid, mk, cal)
    if B is None:
        return sid, None
    idx, o, c, amt, skip, nb = B["idx"], B["o"], B["c"], B["amt"], B["skip"], B["next_bad"]
    n = len(idx); ar = np.arange(n)
    rm = R11._roll_mean
    ma5, ma10, ma20, ma60, ma100 = rm(c, 5), rm(c, 10), rm(c, 20), rm(c, 60), rm(c, 100)
    hi250 = R11._roll_max(c, 250)
    amt_prev20 = np.array(rm(np.roll(amt, 1), 20), dtype=float); amt_prev20[:21] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        amt_ratio = amt / amt_prev20
        T1 = (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60)
        T2 = (c > ma20) & (ma20 > ma60)
        T3 = c >= 0.9 * hi250
    nb_sig = nb[np.maximum(ar - 20, 0)]
    elig = (ar >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(amt_ratio) & (nb_sig > ar)
    # 月底與動能
    dts = cal[idx]
    mi = (dts.year * 12 + dts.month - 1).to_numpy()
    last = np.r_[mi[1:] != mi[:-1], True]
    me = dict(zip(mi[last], c[last]))
    mom = np.array([(me[m - 2] / me[m - 8] - 1.0) if (m - 2 in me and m - 8 in me and me[m - 8] > 0) else np.nan for m in mi])
    mom_month = {int(m): float(v) for m, v in zip(mi[last], mom[last])}   # 該月內動能恆定
    # 營收旗標
    rev = np.zeros(n, bool)
    r_ = _G["REV"].get(sid)
    if r_ is not None:
        sp, hi = r_
        j = np.searchsorted(sp, idx, side="right") - 1
        ok = j >= 0
        rev[ok] = ((idx[ok] - sp[j[ok]]) <= R13.STALE_MAX) & hi[j[ok]]
    pool = elig & rev & (ar + 1 < n)
    ks = set(np.flatnonzero(pool).tolist()) | set(_G["ANDK"].get(sid, []))
    ks = np.array(sorted(k for k in ks if k + 1 < n), dtype=int)
    rel = np.full(len(ks), np.nan)
    for i, k in enumerate(ks):
        if k >= 60:
            med = float(np.nanmedian(amt[k - 60:k]))
            rel[i] = float(amt[k]) / med if med > 0 and np.isfinite(amt[k]) else np.nan
    out = {"k": ks, "pos": idx[ks], "entry_pos": idx[ks + 1], "pool": pool[ks], "T1": T1[ks], "T2": T2[ks], "T3": T3[ks], "mom": mom[ks],
           "mi": mi[ks], "relvol": rel, "mom_month": mom_month}
    EVs = _G.get("EVD", {}).get(sid, [])
    if EVs:
        df = B["df"]; of_, cf_ = df["open"].to_numpy(float), df["close"].to_numpy(float)
    for H in HS:
        xp = np.full(len(ks), -1, np.int64); gg = np.full(len(ks), np.nan)
        for i, k in enumerate(ks):
            nbk = nb[max(0, k - 20)]
            r = R11.fixed_exit(o, c, k, H, nbk)
            if r:
                xp[i] = int(idx[r[0]]); gg[i] = r[1]
            elif D.exit_pos(k + 1, H) >= n and nbk > n - 1 and int(idx[n - 1]) == ncal0 - 1:
                xp[i] = ncal0; gg[i] = float(c[n - 1] / o[k + 1] - 1.0)
        if EVs:                                            # R8（researchYLretest.exits_H 同式）
            ent = idx[ks + 1]
            for pe, pL in EVs:
                for i in range(len(ks)):
                    if xp[i] < 0 or not (ent[i] <= pL and xp[i] >= pe):
                        continue
                    xp[i] = pL; gg[i] = cf_[pL] / of_[ent[i]] - 1.0
        out[f"xpos_H{H}"] = xp; out[f"g_H{H}"] = gg
    return sid, out


# ═════════════ 引擎 ═════════════
def _eng(W, sig, H, seed, N=20, audit=True, **kw):
    aud = [] if audit else None
    o = R11.simulate_mtm(sig, f"H{H}", N, np.random.default_rng(seed), W["closes"], W["opens"], W["ncal"], return_equity=True,
                         log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=aud, **kw)
    return o, aud


def _stats(W, o, aud, segp, N=20):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    hold = None
    if aud is not None:
        cnt = np.zeros(len(eq) + 1)
        for a in aud:
            cnt[a["t"]] += 1 if a["side"] == "buy" else -1
        hold = np.cumsum(cnt)[:len(eq)]
    row = {}
    for sg, (x, y) in segp.items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
        if hold is not None:
            row[f"{sg}_持股"] = float(np.mean(hold[x:y + 1]))
            nb_ = sum(1 for a in aud if a["side"] == "buy" and x <= a["t"] <= y)
            yrs = (y - x + 1) / 245.0
            row[f"{sg}_買進每年"] = nb_ / yrs
    if hold is not None:
        row["持股最大"] = float(hold.max()); row["持股最小"] = float(hold.min())
    return row, eq


def run_cell(job):
    world, key, r = job
    W = _W[world]; sig, H = W["SIG"][key]
    o, aud = _eng(W, sig, H, SEED0 + r)
    row, eq = _stats(W, o, aud, W["SEGP"])
    c, m, _ = RR.win_metrics(eq, o["first"], o["end"], W["w0"], W["w1"])
    row.update({"世界": world, "格": key, "r": r, "全窗_年化": float(c), "全窗_回落": float(m), "eq_sha": sha(eq), "強制出場": int(o.get("x_stop_force_n", -1))})
    # 逐年
    cal = W["cal"]
    yr = pd.DatetimeIndex(cal).year.to_numpy()
    for y_ in sorted(set(yr[W["w0"]:W["w1"] + 1])):
        ii = np.flatnonzero(yr[:len(cal)] == y_)
        a_, b_ = max(ii[0], W["w0"]), min(ii[-1], W["w1"])
        prev = a_ - 1 if a_ > W["w0"] else a_
        row[f"年{y_}"] = float(eq[b_] / eq[prev] - 1.0) if eq[prev] > 0 else np.nan
    # 配對差（對營量 v1 同顆）
    V1 = W.get("V1EQ")
    diffs = {}
    if V1 is not None:
        ev = V1[r]
        for sg, (x, y) in W["SEGP"].items():
            ra = eq[x + 1:y + 1] / eq[x:y] - 1.0; rb = ev[x + 1:y + 1] / ev[x:y] - 1.0
            diffs[sg] = (ra - rb).astype(np.float64)
    return row, diffs, (eq if key == W.get("KEEP_EQ") else None)


def run_fake(job):
    world, i = job
    W = _W[world]; sig, H = W["FAKE"](i)
    o, aud = _eng(W, sig, H, SEED0 + i)
    row, _ = _stats(W, o, aud, W["SEGP"])
    row.update({"世界": world, "i": i, "筆數": int(len(sig))})
    return row


def run_shift(job):
    world, key, sg, sh, r = job
    W = _W[world]; sig, H = W["SIG"][key]
    x, y = W["SEGP0"][sg]
    s0 = x + sh
    s2 = sig[sig["entry_pos"].to_numpy() >= s0]
    o, aud = _eng(W, s2, H, SEED0 + r, audit=False)
    eq = np.asarray(o["equity"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, y)
    return {"世界": world, "格": key, "段": sg, "挪": sh, "r": r, "年化": float(c_), "回落": float(m_)}


def run_slip(job):
    key, arm, r = job
    from backtest import researchSlip as SL
    sig, op, cost, kw = SL._G["INP"][(key, arm)]
    o = SL.run_engine(key, sig, op, cost, kw, r)
    eq = np.asarray(o["equity"], float)
    out = {"格": key, "臂": arm, "r": r}
    for sg, (x, y) in SL._G["subsegs"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        out[f"{sg}_年化"] = float(c_); out[f"{sg}_回落"] = float(m_)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], SL._G["w0"], SL._G["w1"])
    out["全窗_年化"] = float(c_); out["全窗_回落"] = float(m_)
    return out


def run_sens(job):
    world, name, r = job
    W = _W[world]; sig, H = W["SENS"][name]
    o, aud = _eng(W, sig, H, SEED0 + r)
    row, _ = _stats(W, o, aud, W["SEGP"])
    row.update({"世界": world, "變體": name, "r": r})
    return row


def cr0_mean(d, months):
    m = float(d.mean()); u = d - m
    s = pd.Series(u).groupby(months).sum().to_numpy()
    se = float(np.sqrt((s ** 2).sum()) / len(d))
    return m, se


# ═════════════ 一個世界：特徵、訊號 ═════════════
def build_world(tag, cal, w0, w1, sids_mk, AND, rev_panel, elig_by_month, EVD, procs, log):
    rp = rev_panel.sort_values(["stock_id", "signal_pos"])
    _G.update(cal=cal, REV={s: (g["signal_pos"].to_numpy(int), g["rev_hi24"].fillna(False).astype(bool).to_numpy()) for s, g in rp.groupby("stock_id")},
              ANDK={s: g["k"].astype(int).tolist() for s, g in AND.groupby("sid")}, EVD=EVD)
    t0 = time.time()
    with Pool(procs) as pool:
        F = dict(pool.map(feat, sids_mk, chunksize=8))
    F = {s: v for s, v in F.items() if v is not None}
    log(f"[{tag} 特徵] {len(F)} 檔｜{time.time() - t0:.0f}s")
    # T4 門檻（每月）
    T4set = {}
    for mi_, S_ in elig_by_month.items():
        vals = [(s, F[s]["mom_month"].get(mi_, np.nan)) for s in sorted(S_) if s in F]
        vals = [(s, v) for s, v in vals if np.isfinite(v)]
        if not vals:
            continue
        ss = np.array([s for s, _ in vals]); vv = np.array([v for _, v in vals])
        dq = AV.deciles(vv)
        T4set[mi_] = (set(ss[dq >= 7]), float(vv[dq >= 7].min()), set(ss))
    rows = []
    for s, f in F.items():
        t4 = np.zeros(len(f["k"]), bool)
        for i, (m_, v) in enumerate(zip(f["mi"], f["mom"])):
            z = T4set.get(int(m_))
            if z is None or not np.isfinite(v):
                continue
            top, thr, uni = z
            t4[i] = (s in top) if s in uni else (v >= thr)
        d = pd.DataFrame({"sid": s, "k": f["k"], "pos": f["pos"], "entry_pos": f["entry_pos"], "候選": f["pool"], "T1": f["T1"], "T2": f["T2"], "T3": f["T3"],
                          "T4": t4, "mom": f["mom"], "relvol": f["relvol"], **{f"xpos_H{H}": f[f"xpos_H{H}"] for H in HS}, **{f"g_H{H}": f[f"g_H{H}"] for H in HS}})
        rows.append(d)
    ALL = pd.concat(rows, ignore_index=True)
    # 甲：AND 列
    key = ALL.set_index(["sid", "k"])
    A = AND.copy()
    ix = pd.MultiIndex.from_arrays([A["sid"], A["k"].astype(int)])
    miss = int((~ix.isin(key.index)).sum())
    if miss:
        raise SystemExit(f"⛔ {tag}：AND 列 {miss} 筆找不到特徵")
    J = key.loc[ix]
    for c_ in ("T1", "T2", "T3", "T4", "mom"):
        A[c_] = J[c_].to_numpy()
    for H in (40, 80):
        A[f"xpos_H{H}"] = J[f"xpos_H{H}"].to_numpy(); A[f"g_H{H}"] = J[f"g_H{H}"].to_numpy()
    e = A["entry_pos"].to_numpy(); inw = (e >= w0) & (e <= w1)
    Jw = J[inw]; AW = A[inw].copy()
    gate = {"窗內列": int(inw.sum()), "H60 xpos 不同": int((Jw["xpos_H60"].to_numpy() != AW["xpos_H60"].to_numpy(np.int64)).sum()),
            "H60 g 差 ＞ 1e−12": int(np.nansum(np.abs(Jw["g_H60"].to_numpy(float) - AW["g_H60"].to_numpy(float)) > 1e-12)),
            "H60 g 有無不一致": int((np.isfinite(Jw["g_H60"].to_numpy(float)) != np.isfinite(AW["g_H60"].to_numpy(float))).sum()),
            "relvol 差 ＞ 1e−12": int(np.nansum(np.abs(Jw["relvol"].to_numpy(float) - AW["relvol"].to_numpy(float)) > 1e-12))}
    # 乙：候選 ∧ Tk ⇒ 去重
    SIGB = {}
    P = ALL[ALL["候選"]].sort_values(["sid", "k"])
    for tk in TK:
        q = P[P[tk]]
        keep = np.zeros(len(q), bool)
        last_s, last_k = None, -10 ** 9
        for j, (s, k) in enumerate(zip(q["sid"].to_numpy(), q["k"].to_numpy())):
            if s != last_s:
                last_s, last_k = s, -10 ** 9
            if k - last_k > 20:
                keep[j] = True; last_k = k
        qq = q[keep]
        ee = qq["entry_pos"].to_numpy()
        SIGB[tk] = qq[(ee >= w0) & (ee <= w1)].copy()
    PW = P[(P["entry_pos"] >= w0) & (P["entry_pos"] <= w1)].copy()
    nrel = {"候選根 relvol 缺": int(PW["relvol"].isna().sum()), **{f"乙 {tk} relvol 缺": int(SIGB[tk]["relvol"].isna().sum()) for tk in TK}}
    PW["relvol"] = PW["relvol"].fillna(0.0)                    # 讀法：relvol 缺 ⇒ 0（排最後）、計數必報
    for tk in TK:
        SIGB[tk]["relvol"] = SIGB[tk]["relvol"].fillna(0.0)
    return {"F": F, "ALL": ALL, "AND": AW, "SIGB": SIGB, "POOL": PW, "gate_exit": gate, "relvol缺": nrel}


def cells_of(Wd):
    SIG = {"營量v1": (Wd["AND"], 60)}
    for tk in TK:
        for H in HS:
            SIG[f"甲_{tk}_H{H}"] = (Wd["AND"][Wd["AND"][tk].to_numpy(bool)], H)
            SIG[f"乙_{tk}_H{H}"] = (Wd["SIGB"][tk], H)
    return SIG


def fake_maker(world, key):
    W = _W[world]; fam, tk, hh = key.split("_"); H = int(hh[1:])
    if fam == "甲":
        base = W["BASE_AND"]
        by = [(g.index.to_numpy(), int(g[tk].astype(bool).sum())) for _, g in base.groupby("pos")]

        def mk(i):
            rng = np.random.default_rng([20260928, 1, i])
            pick = [np.sort(rng.choice(ix, size=k, replace=False)) for ix, k in by if k > 0]
            return base.loc[np.concatenate(pick) if pick else []].sort_index(), H
    else:
        pool = W["BASE_POOL"]; cnt = W["SIG"][key][0].groupby("pos").size().to_dict()
        by = [(g.index.to_numpy(), cnt.get(p, 0)) for p, g in pool.groupby("pos")]

        def mk(i):
            rng = np.random.default_rng([20260928, 2, i])
            pick = [np.sort(rng.choice(ix, size=min(k, len(ix)), replace=False)) for ix, k in by if k > 0]
            return pool.loc[np.concatenate(pick) if pick else []].sort_index(), H
    return mk


def ma60_variant(sig, H, bars):
    """(b) 持有期間收盤 ＜ MA60 ⇒ 次一有效根開盤賣（research11.cond_exit 同式、上限 ＝ 原 H 出場根）。"""
    S2 = sig.copy(); xs, gs = f"xpos_H{H}", f"g_H{H}"
    cx, cg = S2.columns.get_loc(xs), S2.columns.get_loc(gs)
    n_hit = 0
    for i, (s, k, x) in enumerate(zip(sig["sid"], sig["k"].astype(int), sig[xs].astype(int))):
        idx, o, c, ma60, nb = bars[s]
        n = len(idx)
        kx = int(np.searchsorted(idx, min(x, int(idx[-1])), side="right") - 1)
        ep = o[k + 1]
        for j in range(k + 1, kx + 1):
            if np.isfinite(ma60[j]) and c[j] < ma60[j]:
                if j + 1 <= n - 1 and j + 1 < nb[max(0, k - 20)] and j + 1 <= kx:
                    S2.iat[i, cx] = int(idx[j + 1]); S2.iat[i, cg] = o[j + 1] / ep - 1.0
                else:
                    S2.iat[i, cx] = int(idx[j]); S2.iat[i, cg] = c[j] / ep - 1.0
                n_hit += 1
                break
    return S2, n_hit


# ═════════════ 主程式 ═════════════
def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report(); return
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    T0 = time.time()
    log(f"===== researchYLtrend {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜procs {a.procs} seeds {a.seeds} reps {a.reps}｜停止交易強制出場：開｜T1：開 =====")
    S = {"件": "PREREG營量趨勢 seq1（登錄 sha 5cee2ce099553bb4；裁定 seq265 §二）"}
    # ── 主世界 ──
    RR.use_snapshot()
    cal = D.load_calendar(); w0, w1 = RR.win_bounds(cal)
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", log, t1=True)
    G = RR._G; AND = G["AND"].copy()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks); uni_all = D.load_universe()
    uni = uni_all.merge(U[["stock_id"]], on="stock_id")
    mk = uni.set_index("stock_id")["market"]
    mp = pd.read_csv(MPANEL, dtype={"stock_id": str}, parse_dates=["measure_date"])
    tf = lambda s: s.astype(str).isin(["True", "1", "1.0"])
    elig_m = {}
    for md, g in mp.groupby("measure_date"):
        elig_m[int(md.year * 12 + md.month - 1)] = set(g.loc[tf(g["eligible"]).to_numpy(), "stock_id"])
    rev = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    Wm = build_world("主", cal, w0, w1, list(zip(uni["stock_id"], uni["market"])), AND, rev, elig_m, {}, a.procs, log)
    S["閘"] = {"主 H60 出場／relvol 重算 ＝ AND 表": Wm["gate_exit"]}
    log(f"[閘 主 出場] {Wm['gate_exit']}")
    # 價格：AND 已載 ＋ 乙族其餘股
    closes, opens = dict(G["closes"]), dict(G["opens"])
    extra = sorted((set(Wm["POOL"]["sid"]) | set().union(*[set(v["sid"]) for v in Wm["SIGB"].values()])) - set(closes))
    if extra:
        c2, o2 = RR.load_prices(extra, cal, mk, "branch")
        c2, o2 = RR.pad_px_t1(c2, o2)
        closes.update(c2); opens.update(o2)
    SF = R11.stop_force_days(R11.valid_from_data(sorted(closes), mk, cal), w1)
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in SEG_C.items()}
    bench = RR.load_bench(cal)
    B50 = {sg: RR.bench_row(cal, bench, x, y + 1) for sg, (x, y) in SEGP.items()}
    B50["主窗"] = RR.bench_row(cal, bench, w0, w1 + 1)
    SIGm = cells_of(Wm)
    _W["主"] = {"SIG": SIGm, "closes": closes, "opens": opens, "ncal": G["ncal"], "SF": SF, "SEGP": SEGP, "SEGP0": SEGP, "w0": w0, "w1": w1, "cal": cal,
               "BASE_AND": Wm["AND"], "BASE_POOL": Wm["POOL"]}
    S["0050"] = B50
    # 必報：通過率、訊號數
    S["甲 通過率（主）"] = {tk: float(Wm["AND"][tk].mean()) for tk in TK}
    S["乙 訊號數（主，窗內）"] = {tk: int(len(Wm["SIGB"][tk])) for tk in TK}
    S["候選根（主，窗內、去重前）"] = int(len(Wm["POOL"])); S["營量 AND 列（主，窗內）"] = int(len(Wm["AND"]))
    S["relvol 缺（主）"] = Wm["relvol缺"]
    # 營量 v1 先跑（配對差要用）
    t0 = time.time()
    _W["主"]["KEEP_EQ"] = "營量v1"
    with Pool(a.procs) as pool:
        res = pool.map(run_cell, [("主", "營量v1", r) for r in range(a.seeds)], chunksize=4)
    V1rows = [x[0] for x in res]
    _W["主"]["V1EQ"] = {r: x[2] for r, x in zip(range(a.seeds), res)}; _W["主"]["KEEP_EQ"] = None
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
    ref = ref[(ref["key"] == "c13") & (ref["var"] == "t1")].sort_values("r").reset_index(drop=True)
    mine = pd.DataFrame(V1rows).sort_values("r").reset_index(drop=True)
    nn = min(len(ref), len(mine))
    S["閘"]["營量v1＝T1fix c13 t1（年化／回落 repr、eq_sha 不同顆數）"] = int(sum(repr(float(ref.loc[i, "cagr"])) != repr(float(mine.loc[i, "全窗_年化"]))
                                                                        or repr(float(ref.loc[i, "mdd"])) != repr(float(mine.loc[i, "全窗_回落"]))
                                                                        or ref.loc[i, "eq_sha"] != mine.loc[i, "eq_sha"] for i in range(nn)))
    log(f"[營量 v1 主] {a.seeds} 顆｜閘 {S['閘']}｜{time.time() - t0:.0f}s")
    keys = [k for k in SIGm if k != "營量v1"]
    t0 = time.time()
    SEEDm = list(V1rows); DIFF = {k: {sg: None for sg in SEGP} for k in keys}
    with Pool(a.procs) as pool:
        for row, diffs, _ in pool.imap_unordered(run_cell, [("主", k, r) for k in keys for r in range(a.seeds)], chunksize=4):
            SEEDm.append(row)
            for sg, d in diffs.items():
                DIFF[row["格"]][sg] = d if DIFF[row["格"]][sg] is None else DIFF[row["格"]][sg] + d
    log(f"[組合層 主] {len(keys)} 格 × {a.seeds}｜{time.time() - t0:.0f}s")
    SEEDm = pd.DataFrame(SEEDm)
    # ── 早年世界 ──
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    from backtest import early_data as E
    from backtest import p4_features as P4F
    V.body_setup("main", log)
    ecal = V._B["cal"]; ew0, ew1 = V._B["w0"], V._B["w1"]
    euni = Y._G["uni"]
    EAND = Y.sig_of(13, "mtm", 0, len(ecal) + 5).copy()          # 全表（去重、特徵用）；窗在 build_world 裡切
    sdir = V.body_paths("main")[1]
    erev = pd.read_csv(os.path.join(sdir, "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    ep = P4F.read_panel(os.path.join(sdir, "panel.csv.gz"))
    eelig = {}
    for md, g in ep.groupby("measure_date"):
        if md >= pd.Timestamp("2012-06-01"):
            eelig[int(md.year * 12 + md.month - 1)] = set(g.loc[g["eligible"].astype(bool).to_numpy(), "stock_id"])
    EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(ecal)}
    EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    esids = [(s, euni.get(s, "twse")) for s in sorted(euni.index)]
    We = build_world("早年", ecal, ew0, ew1, esids, EAND, erev, eelig, EVD, a.procs, log)
    S["閘"]["早年 H60 出場／relvol 重算 ＝ AND 表"] = We["gate_exit"]
    log(f"[閘 早年 出場] {We['gate_exit']}")
    ecl, eop = dict(Y._G["closes"]), dict(Y._G["opens"])
    extra = sorted((set(We["POOL"]["sid"]) | set().union(*[set(v["sid"]) for v in We["SIGB"].values()])) - set(ecl))
    if extra:
        c2, o2 = RR.load_prices(extra, ecal, euni, "branch"); c2, o2 = Y.pad_px(c2, o2)
        ecl.update(c2); eop.update(o2)
    eSF = R11.stop_force_days(R11.valid_from_data(sorted(ecl), euni, ecal), ew1)
    ESEGP = {"早年": (ew0, ew1)}
    eb50 = RR.bench_row(ecal, RR.load_bench(ecal), ew0, ew1 + 1)
    S["0050"]["早年"] = eb50
    SIGe = cells_of(We)
    _W["早年"] = {"SIG": SIGe, "closes": ecl, "opens": eop, "ncal": Y._G["NP"], "SF": eSF, "SEGP": ESEGP, "SEGP0": ESEGP, "w0": ew0, "w1": ew1, "cal": ecal,
                 "BASE_AND": We["AND"], "BASE_POOL": We["POOL"], "KEEP_EQ": "營量v1"}
    S["甲 通過率（早年）"] = {tk: float(We["AND"][tk].mean()) for tk in TK}
    S["乙 訊號數（早年，窗內）"] = {tk: int(len(We["SIGB"][tk])) for tk in TK}
    S["relvol 缺（早年）"] = We["relvol缺"]
    with Pool(a.procs) as pool:
        res = pool.map(run_cell, [("早年", "營量v1", r) for r in range(a.seeds)], chunksize=4)
    eV1rows = [x[0] for x in res]; _W["早年"]["V1EQ"] = {r: x[2] for r, x in zip(range(a.seeds), res)}; _W["早年"]["KEEP_EQ"] = None
    eref = pd.read_csv("backtest/resultsYLretest/b2_early_seeds.csv", float_precision="round_trip")
    eref = eref[eref["key"] == "main|開|N20|H60"].sort_values("r").reset_index(drop=True)
    em = pd.DataFrame(eV1rows).sort_values("r").reset_index(drop=True)
    nn = min(len(eref), len(em))
    S["閘"]["早年營量v1＝YLretest b2e main|開|N20|H60（年化／回落 repr 不同顆數）"] = int(sum(repr(float(eref.loc[i, "cagr"])) != repr(float(em.loc[i, "早年_年化"]))
                                                                                  or repr(float(eref.loc[i, "mdd"])) != repr(float(em.loc[i, "早年_回落"])) for i in range(nn)))
    SEEDe = list(eV1rows); eDIFF = {k: {"早年": None} for k in keys}
    with Pool(a.procs) as pool:
        for row, diffs, _ in pool.imap_unordered(run_cell, [("早年", k, r) for k in keys for r in range(a.seeds)], chunksize=4):
            SEEDe.append(row)
            for sg, d in diffs.items():
                eDIFF[row["格"]][sg] = d if eDIFF[row["格"]][sg] is None else eDIFF[row["格"]][sg] + d
    SEEDe = pd.DataFrame(SEEDe)
    log(f"[組合層 早年] {len(keys) + 1} 格｜閘 {S['閘']}｜{time.time() - T0:.0f}s")
    # ── 彙總 ──
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in SEGP.items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[ew0 + 1:ew1 + 1]])
    PT = []
    for k in ["營量v1"] + keys:
        g = SEEDm[SEEDm["格"] == k]; ge = SEEDe[SEEDe["格"] == k]
        row = {"格": k, "族": k.split("_")[0] if k != "營量v1" else "—", "訊號數_主": int(len(SIGm[k][0])), "訊號數_早年": int(len(SIGe[k][0]))}
        for sg, gg, bb in (("探索", g, B50["探索"]), ("確認", g, B50["確認"]), ("早年", ge, eb50)):
            c, m = float(gg[f"{sg}_年化"].median()), float(gg[f"{sg}_回落"].median())
            row.update({f"{sg}_年化": c, f"{sg}_回落": m, f"{sg}_比值": c / abs(m), f"{sg}_標籤": label(c, m, (bb["cagr"], bb["mdd"])),
                        f"{sg}_持股": float(gg[f"{sg}_持股"].median()), f"{sg}_現金": float(gg[f"{sg}_現金"].median()), f"{sg}_買進每年": float(gg[f"{sg}_買進每年"].median())})
            if k != "營量v1":
                dd = (DIFF[k][sg] if sg != "早年" else eDIFF[k][sg]) / a.seeds
                mm_, se_ = cr0_mean(dd, months[sg])
                row.update({f"{sg}_配對差年化": mm_ * 245, f"{sg}_配對差lo": (mm_ - 1.96 * se_) * 245, f"{sg}_配對差hi": (mm_ + 1.96 * se_) * 245})
        c, m = float(g["全窗_年化"].median()), float(g["全窗_回落"].median())
        row.update({"主窗_年化": c, "主窗_回落": m, "主窗_比值": c / abs(m)})
        PT.append(row)
    PT = pd.DataFrame(PT)
    np.savez_compressed(os.path.join(OUT, "pairdiff.npz"), **{f"{k}|{sg}": ((DIFF[k][sg] if sg != "早年" else eDIFF[k][sg]) / a.seeds)
                                                              for k in keys for sg in ("探索", "確認", "早年")})
    v1 = PT.set_index("格").loc["營量v1"]
    for sg in ("探索", "確認", "早年"):
        PT[f"{sg}_年化差"] = PT[f"{sg}_年化"] - v1[f"{sg}_年化"]; PT[f"{sg}_回落差"] = PT[f"{sg}_回落"] - v1[f"{sg}_回落"]
    PT["退化"] = (PT["格"] != "營量v1") & ((PT["探索_持股"] < 10) | (PT["探索_現金"] > 0.30))
    cand = PT[(PT["格"] != "營量v1") & ~PT["退化"]].copy()
    pk = None
    if len(cand):
        q = cand[cand["探索_標籤"] == "合格"] if (cand["探索_標籤"] == "合格").any() else cand
        pk = q.sort_values(["探索_比值", "探索_年化"], ascending=[False, False]).iloc[0]["格"]
    S["退化（挑前排除）"] = PT.loc[PT["退化"], "格"].tolist(); S["挑中格"] = pk
    log(f"[挑格] 退化 {S['退化（挑前排除）']}｜挑中 {pk}")
    J = {}
    if pk:
        pr = PT.set_index("格").loc[pk]
        J["確認標籤"], J["早年標籤"] = pr["確認_標籤"], pr["早年_標籤"]
        J["件標籤"] = min((pr["確認_標籤"], pr["早年_標籤"]), key=lambda x: ORDER[x])
        lo, hi, ed = pr["確認_配對差lo"], pr["確認_配對差hi"], pr["早年_配對差年化"]
        if lo > 0:
            J["對營量v1"] = "比營量 v1 好" if ed > 0 else "不穩（確認段好、早年反向）"
        elif hi < 0:
            J["對營量v1"] = "比營量 v1 差" if ed < 0 else "不穩（確認段差、早年反向）"
        else:
            J["對營量v1"] = "分不出（確認段配對差 CI 含 0）"
        R219 = pd.read_csv("backtest/resultsYLretest/b2_rand219.csv")
        mx = R219.groupby("r")["ratio"].max()
        J["主窗比值"] = float(pr["主窗_比值"])
        J["219 每顆最大比值分佈百分位（≤ 的比例）"] = float((mx <= pr["主窗_比值"]).mean())
        J["219 每顆最大比值 中位／p10／p90"] = [float(mx.median()), float(mx.quantile(0.1)), float(mx.quantile(0.9))]
        J["營量v1 主窗比值（T1）"] = float(v1["主窗_比值"])
        J["營量v1 在同分佈的百分位"] = float((mx <= v1["主窗_比值"]).mean())
    S["判定"] = J
    # ── 假訊號、挪起點、現實版、新規矩 ③ ──
    FK = {}; SH = []; SL_rows = []
    if pk:
        for wn in ("主", "早年"):
            _W[wn]["FAKE"] = fake_maker(wn, pk)
            with Pool(a.procs) as pool:
                FR = pd.DataFrame(pool.map(run_fake, [(wn, i) for i in range(a.reps)], chunksize=4))
            FR.to_csv(os.path.join(OUT, f"fake_{'main' if wn == '主' else 'early'}.csv.gz"), index=False, float_format="%.17g")
            pr = PT.set_index("格").loc[pk]
            for sg in _W[wn]["SEGP"]:
                fr = FR[f"{sg}_年化"] / FR[f"{sg}_回落"].abs()
                FK[sg] = {"p（假比值 ≥ 本格比值）": float(np.mean(fr >= pr[f"{sg}_比值"])), "p（假年化 ≥ 本格年化）": float(np.mean(FR[f"{sg}_年化"] >= pr[f"{sg}_年化"])),
                          "假年化中位": float(FR[f"{sg}_年化"].median()), "假比值中位": float(fr.median()), "假筆數中位": float(FR["筆數"].median())}
            log(f"[假訊號 {wn}] {FK}")
        S["假訊號臂（挑中格）"] = FK
        for wn, segs in (("主", ["確認"]), ("早年", ["早年"])):
            jobs = [(wn, k, sg, sh, r) for k in (pk, "營量v1") for sg in segs for sh in SHIFTS for r in range(a.seeds)]
            with Pool(a.procs) as pool:
                SH += pool.map(run_shift, jobs, chunksize=4)
        SH = pd.DataFrame(SH)
        SH.to_csv(os.path.join(OUT, "shift_seeds.csv.gz"), index=False, float_format="%.17g")
        shs = []
        for (k, sg, sh), g in SH.groupby(["格", "段", "挪"]):
            shs.append({"格": k, "段": sg, "挪": int(sh), "年化": float(g["年化"].median()), "回落": float(g["回落"].median())})
        S["挪起點（重新起始）"] = shs
        log(f"[挪起點] {len(SH)} 次")
    # 0050 挪起點同窗（主、早年各自世界）
    if pk:
        b_m = bench                                              # 主世界 0050（早年版面載入前就讀好）
        for d in S["挪起點（重新起始）"]:
            if d["段"] == "確認":
                x, y = SEGP["確認"]; bb = RR.bench_row(cal, b_m, x + d["挪"], y + 1)
                d["0050"] = [bb["cagr"], bb["mdd"]]; d["標籤"] = label(d["年化"], d["回落"], (bb["cagr"], bb["mdd"]))
    # 早年的 0050 挪起點（目前 D.DATA 是早年版面）
    if pk:
        b_e = RR.load_bench(ecal)
        for d in S["挪起點（重新起始）"]:
            if d["段"] == "早年":
                bb = RR.bench_row(ecal, b_e, ew0 + d["挪"], ew1 + 1)
                d["0050"] = [bb["cagr"], bb["mdd"]]; d["標籤"] = label(d["年化"], d["回落"], (bb["cagr"], bb["mdd"]))
    # 新規矩 ③（早年世界在記憶體內，先做早年再切回主）
    trig = bool(pk) and (J["確認標籤"] in ("合格", "另列") or J["早年標籤"] in ("合格", "另列"))
    S["新規矩③"] = "要跑（(b) 跌破 MA60 次日開盤賣；(a) 全賣全買：事件型固定持有、沒有換股日 ⇒ 不適用）" if trig else "不適用（挑中格確認、早年皆非合格／另列）"
    SENS = {}
    if trig:
        H = int(pk.split("_H")[1])
        for wn in ("早年", "主"):
            if wn == "主":
                RR.use_snapshot()
            else:
                V.use_layout("main")
            W = _W[wn]; sig = W["SIG"][pk][0]
            bars = {}
            for s in sorted(set(sig["sid"])):
                B = R11.load_bars(s, (mk if wn == "主" else euni).get(s, "twse"), W["cal"])
                bars[s] = (B["idx"], B["o"], B["c"], R11._roll_mean(B["c"], 60), B["next_bad"])
            S2, nh = ma60_variant(sig, H, bars)
            W["SENS"] = {"(b) 跌破MA60次日開盤賣": (S2, H)}
            with Pool(a.procs) as pool:
                SR = pd.DataFrame(pool.map(run_sens, [(wn, "(b) 跌破MA60次日開盤賣", r) for r in range(a.seeds)], chunksize=4))
            SENS[wn] = {"提前出場筆數": nh, "列": int(len(sig)), **{sg: [float(SR[f"{sg}_年化"].median()), float(SR[f"{sg}_回落"].median())] for sg in W["SEGP"]}}
        S["新規矩③ 描述"] = SENS
        log(f"[新規矩③] {SENS}")
    # 現實版（主世界）
    RR.use_snapshot()
    if pk:
        from backtest import researchSlip as SL
        H = int(pk.split("_H")[1])
        SL.CELLS["YT"] = dict(SL.CELLS[13], 名=pk, rule=f"H{H}")
        sigp = SIGm[pk][0]; sig13 = SIGm["營量v1"][0]
        ssid = sorted(set(sigp["sid"]) | set(sig13["sid"]))
        _G.update(cal=cal, NPX=len(cal) + 1)
        with Pool(a.procs) as pool:
            X = dict(pool.map(_load_x, [(s, mk.get(s, "twse")) for s in ssid], chunksize=8))
        from backtest import tradability as TR
        trad_full = {s: {"trd": v["trd"][:len(cal)]} for s, v in X.items() if v is not None}
        try:
            off = TR.load_official()
        except Exception:
            off = {}
        dl = TR.delist_status(trad_full, cal, official=off)
        subsegs = dict(SEGP)
        SG = dict(cal=cal, NP=G["ncal"], closes=closes, opens=opens, w0=w0, w1=w1, SF=SF, dl=dl, subsegs=subsegs, X=X, part="main", ncal=len(cal))
        SL._G.clear(); SL._G.update(SG)
        spec = dict(SL.ARMS)
        REAL, C5 = "現實版（C1 0.3%＋C2 50 萬＋C3＋C4）", "現實版＋C5 低消 20 元"
        INP = {}
        for key_, sg_ in (("YT", sigp), (13, sig13)):
            for arm in (REAL, C5):
                INP[(key_, arm)] = SL.arm_inputs(key_, spec[arm], sg_, X, closes, opens)
        SL._G["INP"] = INP
        with Pool(a.procs) as pool:
            SLR = pd.DataFrame(pool.map(run_slip, [(k_, arm, r) for (k_, arm) in INP for r in range(a.seeds)], chunksize=4))
        SLR.to_csv(os.path.join(OUT, "slip_seeds.csv.gz"), index=False, float_format="%.17g")
        rf = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
        gs = {}
        for arm, key_ in ((REAL, "slip13_real"), (C5, "slip13_c5")):
            a_ = SLR[(SLR["格"] == 13) & (SLR["臂"] == arm)].sort_values("r").reset_index(drop=True)
            b_ = rf[(rf["key"] == key_) & (rf["var"] == "t1")].sort_values("r").reset_index(drop=True)
            nn = min(len(a_), len(b_))
            gs[key_] = int(sum(repr(float(a_.loc[i, "全窗_年化"])) != repr(float(b_.loc[i, "cagr"])) or repr(float(a_.loc[i, "全窗_回落"])) != repr(float(b_.loc[i, "mdd"]))
                               for i in range(nn)))
        S["閘"]["營量v1 現實版＝T1fix（不同顆數）"] = gs
        S["現實版（描述）"] = {f"{'挑中格' if k_ == 'YT' else '營量v1'}｜{arm}": {sg: [float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())] for sg in SEGP}
                              for (k_, arm), g in SLR.groupby(["格", "臂"])}
        log(f"[現實版] 閘 {gs}")
    # ── 存檔 ──
    SEEDm.to_csv(os.path.join(OUT, "seeds_main.csv.gz"), index=False, float_format="%.17g")
    SEEDe.to_csv(os.path.join(OUT, "seeds_early.csv.gz"), index=False, float_format="%.17g")
    PT.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    keep_cols = ["sid", "k", "pos", "entry_pos", "relvol", "T1", "T2", "T3", "T4", "mom"] + [f"xpos_H{H}" for H in HS] + [f"g_H{H}" for H in HS]
    for wn, Wd in (("main", Wm), ("early", We)):
        Wd["AND"][keep_cols].assign(族="AND").to_csv(os.path.join(OUT, f"sig_and_{wn}.csv.gz"), index=False, float_format="%.17g")
        pd.concat([Wd["SIGB"][tk][keep_cols].assign(Tk=tk) for tk in TK]).to_csv(os.path.join(OUT, f"sig_b_{wn}.csv.gz"), index=False, float_format="%.17g")
    # 逐年（挑中格與營量 v1）
    yrs = {}
    for k in ["營量v1"] + ([pk] if pk else []):
        for wn, SD in (("主", SEEDm), ("早年", SEEDe)):
            g = SD[SD["格"] == k]
            yrs[f"{k}｜{wn}"] = {c_[1:]: float(g[c_].median()) for c_ in g.columns if c_.startswith("年") and g[c_].notna().any()}
    S["逐年報酬（中位）"] = yrs
    S["秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    g_ = S["閘"]
    bad = any(v for d in (g_["主 H60 出場／relvol 重算 ＝ AND 表"], g_["早年 H60 出場／relvol 重算 ＝ AND 表"]) for kk, v in d.items() if kk != "窗內列") \
        or g_["營量v1＝T1fix c13 t1（年化／回落 repr、eq_sha 不同顆數）"] or g_["早年營量v1＝YLretest b2e main|開|N20|H60（年化／回落 repr 不同顆數）"] \
        or any(g_.get("營量v1 現實版＝T1fix（不同顆數）", {}).values())
    report()
    log(f"[完] {S['秒']}s｜閘 {'不過' if bad else '過'}")
    if bad:
        raise SystemExit("⛔ 閘不過")


def _load_x(args):
    from backtest import researchSlip as SL
    sid, mk = args
    return sid, SL.stock_extra(sid, mk, _G["cal"], _G["NPX"])


def _p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    PT = pd.read_csv(os.path.join(OUT, "cells.csv"))
    pk = S["挑中格"]; J = S["判定"]; B = S["0050"]
    L = ["# PREREG營量趨勢 seq1（營量 v1 換趨勢定義）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 sha 5cee2ce099553bb4；裁定 seq265 §二（N ＋1）。回測線。⭐ 停止交易強制出場：開；T1：開。"
         "引用請寫「回測 PREREG營量趨勢」。⛔ 就算合格也不取代營量 v1（只進前瞻紀錄並列）。", ""]
    if pk:
        pr = PT.set_index("格").loc[pk]; v1 = PT.set_index("格").loc["營量v1"]
        L.append(f"**結論：挑中 {pk}：確認段 {_p(pr['確認_年化'])}／{_p(pr['確認_回落'])}（{pr['確認_標籤']}）、早年段 {_p(pr['早年_年化'])}／{_p(pr['早年_回落'])}（{pr['早年_標籤']}）"
                 f" ⇒ 件標籤 {J['件標籤']}；對營量 v1：{J['對營量v1']}（確認段配對差年化 {_p(pr['確認_配對差年化'])}〔{_p(pr['確認_配對差lo'])}, {_p(pr['確認_配對差hi'])}〕、"
                 f"早年 {_p(pr['早年_配對差年化'])}）；主窗比值 {J['主窗比值']:.3f} 落在「營量第二批 44 設定取最好」分佈第 {J['219 每顆最大比值分佈百分位（≤ 的比例）'] * 100:.1f} 百分位。**")
        L += ["", "| | 探索 | 確認 | 早年 | 主窗比值 |", "|---|---|---|---|---|",
              f"| 營量 v1 | {_p(v1['探索_年化'])}／{_p(v1['探索_回落'])} | {_p(v1['確認_年化'])}／{_p(v1['確認_回落'])}（{v1['確認_標籤']}） | {_p(v1['早年_年化'])}／{_p(v1['早年_回落'])}（{v1['早年_標籤']}） | {v1['主窗_比值']:.3f} |",
              f"| 挑中 {pk} | {_p(pr['探索_年化'])}／{_p(pr['探索_回落'])} | {_p(pr['確認_年化'])}／{_p(pr['確認_回落'])}（{pr['確認_標籤']}） | {_p(pr['早年_年化'])}／{_p(pr['早年_回落'])}（{pr['早年_標籤']}） | {pr['主窗_比值']:.3f} |",
              f"| 0050 | {_p(B['探索']['cagr'])}／{_p(B['探索']['mdd'])} | {_p(B['確認']['cagr'])}／{_p(B['確認']['mdd'])} | {_p(B['早年']['cagr'])}／{_p(B['早年']['mdd'])} | {B['主窗']['cagr'] / abs(B['主窗']['mdd']):.3f} |"]
        fk = S.get("假訊號臂（挑中格）", {})
        if fk:
            f3 = lambda sg: f"{fk[sg]['p（假比值 ≥ 本格比值）']:.3f}" if sg in fk else "—"
            L.append(f"| 假訊號 p（比值） | {f3('探索')} | {f3('確認')} | {f3('早年')} | |")
    L += ["", "## 一、24 格", "", "| 格 | 訊號數 主／早年 | 探索 年化／回落（比值） | 探索 持股／現金 | 確認 年化／回落 | 確認標籤 | 確認配對差年化〔CI〕 | 早年 年化／回落 | 早年標籤 | 早年配對差 | 退化 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in PT.iterrows():
        cd = "" if r["格"] == "營量v1" else f"{_p(r['確認_配對差年化'])}〔{_p(r['確認_配對差lo'])}, {_p(r['確認_配對差hi'])}〕"
        ed = "" if r["格"] == "營量v1" else _p(r["早年_配對差年化"])
        L.append(f"| {r['格']} | {r['訊號數_主']}／{r['訊號數_早年']} | {_p(r['探索_年化'])}／{_p(r['探索_回落'])}（{r['探索_比值']:.3f}） | {r['探索_持股']:.1f}／{r['探索_現金'] * 100:.0f}% | "
                 f"{_p(r['確認_年化'])}／{_p(r['確認_回落'])} | {r['確認_標籤']} | {cd} | {_p(r['早年_年化'])}／{_p(r['早年_回落'])} | {r['早年_標籤']} | {ed} | {'是' if r['退化'] else ''} |")
    L += ["", f"- 退化（挑前排除）：{S['退化（挑前排除）']}；挑中：{pk}（探索段先合格、再比值）",
          f"- 甲族各 Tk 在營量 v1 訊號中的通過率：主 {json.dumps({k: round(v, 3) for k, v in S['甲 通過率（主）'].items()}, ensure_ascii=False)}；早年 {json.dumps({k: round(v, 3) for k, v in S['甲 通過率（早年）'].items()}, ensure_ascii=False)}",
          f"- 乙族訊號數：主 {S['乙 訊號數（主，窗內）']}；早年 {S['乙 訊號數（早年，窗內）']}；營量 AND 主窗 {S['營量 AND 列（主，窗內）']} 筆",
          f"- 219 對照：{json.dumps({k: v for k, v in J.items() if '219' in k or '營量v1' in k or '主窗' in k}, ensure_ascii=False)}", ""]
    if S.get("假訊號臂（挑中格）"):
        L += ["## 二、假訊號臂（挑中格）", "", json.dumps(S["假訊號臂（挑中格）"], ensure_ascii=False), ""]
    if S.get("挪起點（重新起始）"):
        L += ["## 三、挪起點（重新起始；0、5、10、15、20 個交易日）", "", "| 格 | 段 | 挪 | 年化／回落 | 0050 | 標籤 |", "|---|---|---|---|---|---|"]
        for d in S["挪起點（重新起始）"]:
            L.append(f"| {d['格']} | {d['段']} | {d['挪']} | {_p(d['年化'])}／{_p(d['回落'])} | {_p(d.get('0050', [None])[0])} | {d.get('標籤', '')} |")
        L.append("")
    if S.get("現實版（描述）"):
        L += ["## 四、現實版（描述；主窗）", "", "| 格｜臂 | 探索 | 確認 |", "|---|---|---|"]
        for k, v in S["現實版（描述）"].items():
            L.append(f"| {k} | {_p(v['探索'][0])}／{_p(v['探索'][1])} | {_p(v['確認'][0])}／{_p(v['確認'][1])} |")
        L.append("")
    L += ["## 五、新規矩 ③", "", str(S["新規矩③"]), ""]
    if S.get("新規矩③ 描述"):
        L += [json.dumps(S["新規矩③ 描述"], ensure_ascii=False), ""]
    L += ["## 六、逐年報酬（中位）", "", json.dumps(S["逐年報酬（中位）"], ensure_ascii=False), "",
          "## 七、閘", "", json.dumps(S["閘"], ensure_ascii=False), "",
          "- 「穩」照 seq253 收緊讀法（本件組合層不寫「穩」）；「比營量 v1 好」照裁定 seq265 §二（確認段配對差 CI 不含 0 且早年同向）",
          "- 2005～2012-05 早年延伸段：本件不做（見程式說明 Y6）", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4] if len(L) > 4 else "")


if __name__ == "__main__":
    main()
