# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 配合飆股流程出場（使用者問：「營量、營飆配合飆股流程可以提高期望值嗎？」；參考，⛔ 不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_flowexit [--check | --page]

═══ 讀法（寫死於 2026-09-30 21:10（台北），在算任何數字之前）═══
 F1 本體與閘（正式口徑 ＝ T1 版、停止交易強制出場開，commit 1e7229c101 起）：ctx ＝ researchT1fix.build_ctx(True)
    營量 v1 ＝ simulate_mtm(sig13, "H60", 20, default_rng(7000＋r), pick relvol, queue_days 0, log=[], stop_force)；relvol 挑選、不抽籤 ⇒ r0（另核 r1 同）
    營飆 v1 ＝ simulate_mtm(sig, "H120", 10, default_rng(1000＋r), stop_force)，r ＝ 0～199
    閘 ①：A 的年化、回落（主窗 2017-03-02～2026-08-24，RR.win_metrics）與 resultsT1fix/seeds.csv.gz（營量 c13｜t1｜r0、r1；營飆 c1｜t1｜r0～199）repr 逐位元相同
    閘 ②：A 改走 held_map 合成序列（每列訊號自己的價格鍵、xpos／g 照正式、合成收盤 ＝ 原收盤）權益須與 A 逐位元相同（營量 r0、營飆 r0～4）⇒ 驗 B／C／D 用的管線本身不改結果
    閘 ③：營量 r0 的 A 買進列 ＝ resultsYLlist/audit_seed0.csv.gz 買進列
 F2 飆股流程（surge_flow_daily.replay，commit 18f363f654 的版本，⛔ 去掉「中段底買回」與之後的第二段）；每一列候選訊號都算：
    進場日 e ＝ entry_pos；進場價 bp ＝ 引擎進場價（e 開盤，無效改 e 收盤）；價格 ＝ 引擎同一份（ctx closes 還原 ffill、opens）；
    K 棒 ＝ research11.load_bars 的有效 K 棒（traded）；次一開盤 ＝ 之後第一根有效 K 棒且開盤有限 ＞ 0（資料內）
    起漲點 t ＝ anchor_of（250 日內最高收盤之前的最低收盤），⭐ 資料只到 e−1、進場時就固定、之後不隨資料日重算
      （每日名單是每天用當天資料重播、錨可能隨日移動；回測固定錨 ⇒ 不用事後資訊）；從 t 起回落 30% 在 e−1 以前已發生 ⇒ 改錨到結束日～e−1 最低收盤，重複（同 researchYL_entrystage Y3）
    結束 stop ＝ [t, 資料尾] 第一次收盤 ≤ t 起最高收盤 × 0.7（任何時候回落 30% ⇒ 本筆結束，還有部位 ⇒ 次一開盤賣）
    本段起點 ＝ cuts_rec(c[t..e])（x＝20%）回升日 ≤ e 的最後一個拉回低點；沒有 ⇒ t
    W1：買進前本段已有 W1（[本段起點, e)，且 stop ＞ e）⇒ 當作 e 當天出現；否則 [e, stop) 第一個 W1
    40 天沒新高 n40：新高 ＝ 收盤 ＞ t 以來最高（t 本身算）；最後新高日之後的 K 棒數第一次 ≥ 40、且那天 ≥ e；n40 ≤ W1 那天（或沒有 W1）⇒ 次一開盤賣全部
    沒有 W1、沒有 n40 ⇒ stop 次一開盤賣全部；都沒有 ⇒ 未完
    有 W1 ⇒ 次一開盤 ex1 賣 3 成；剩 7 成：買進前、本段 W1 之後已有 W2 ⇒ 與 3 成同一天賣；否則 [ex1, stop) 第一個 W2 ⇒ 次一開盤賣；否則 stop 次一開盤賣；都沒有 ⇒ 未完
    W1 ＝ 收盤創 20 日新高 ∧ 10 日注意次數 Q5 ∧（5 日漲停天數 Q5 ∨ 5 日報酬 Q5）∧ 60 日無處置 ∧ 有效 K 棒；
    W2 ＝（再次進入處置：處置起日且前 60 個交易日內另有起日｜處置出關：迄日下一交易日）∧ 收盤在含當天 20 根最高收盤 10% 內 ∧ 有效 K 棒
      —— 照 researchSurge6_restexit.build（飆股資料 s5work Q／F、stitch 價格、MAIN 注意／處置表），依日期對到引擎日曆；不在飆股母體的檔 ⇒ 沒有 W1／W2（筆數照報）
    未完 ⇒ 照 T1：xpos ＝ 資料尾後墊的那一天、以資料尾收盤計值；停止交易 ⇒ 引擎 stop_force 同一條（L＋1 以 L 收盤出）
    壞根（load_bars next_bad；同正式 fixed_exit 的界線 ＝ 訊號根前 20 根起第一個壞根）：出場晚於壞根前一根收盤 ⇒ 改在壞根前一根收盤出（筆數照報）
 F3 四種出場（同一批候選訊號；每筆拆 3 成／7 成兩個子部位；正式出場 ＝ 第 H 根收盤（H ＝ 60／120），照正式 sig 的 xpos／g，含 T1 補）：
    A ＝ 正式；B ＝ 流程（不設天數上限）；C ＝ 每個子部位取「正式、流程」較早者（流程、最長不超過正式天數）；
    D ＝ 每個子部位取較晚者（⇒ 正式到期時流程還抱著的部分續抱到流程出場；流程已賣掉的部分在正式到期日照正式賣）
    時間先後：X 日開盤早於同一天收盤；未完最晚；同時 ⇒ 取正式
 F4 逐筆（參考；每筆當獨立一筆）：同一批進場 ＝ A 的實際交易（營量 r0 717 筆；營飆 200 顆合併、同一筆出現幾次算幾次，另報去重）
    每筆報酬 ＝ 0.3 ×（3 成出場價 ÷ bp − 1）＋ 0.7 ×（7 成出場價 ÷ bp − 1）− 0.585%（來回成本，照引擎）
    持有天數 ＝ 兩個子部位的有效 K 棒數依 3／7 加權（開盤賣 ⇒ 算到前一根；收盤賣 ⇒ 含當根）；每持有一天報酬 ＝ 平均報酬 ÷ 平均持有天數
    報：筆數、平均、中位、勝率（報酬 ＞ 0）、賺的平均、賠的平均、平均持有天數、每天報酬、3 成與 7 成子部位各自的平均（未扣成本）；分期依進場日
 F5 組合（照實模擬，⛔ 不沿用 A 的進場清單）：B／C／D 用引擎 held_map：每列候選訊號改用自己的價格鍵「代號#進場位置」，
    合成收盤 ＝ Σ 子部位權重 ×（還在抱 ⇒ 當日收盤；已賣 ⇒ 賣價）；xpos ＝ 最後一個子部位出場那天（開盤賣 ⇒ 那天；收盤賣 ⇒ 那天，同正式慣例）；
    g ＝ Σ 權重 × 出場價 ÷ bp − 1；名額、排序、抽籤、成本、停止交易強制出場全照正式引擎
    ⭐ 分批的近似：先賣的 3 成的錢留在部位裡（價值凍結在賣價、報酬 0），名額到最後一個子部位出場才釋出；成本在最後出場時一次扣整筆來回（金額相同、只差時點）
    營量 ⇒ 1 顆（r0；另核 r1 ＝ r0）；營飆 200 顆 ⇒ 報中位、p10～p90，對 A 同顆差的中位與「贏 A 的顆數比例」
    分期：同一條權益曲線切窗（全部 ＝ 主窗 2017-03-02～2026-08-24；2021-01～2023-12；2024-01～2026-08-24），RR.win_metrics
 F6 查核（--check）：從 A 的交易（營量＋營飆去重）抽 50 筆（random_state 20260930），逐日迴圈從頭重算 W1（飆股資料逐根）、W2（處置區間）、錨、stop、
    本段起點、n40、兩個子部位出場日與價、壞根、停止交易，與 B／C／D 的 xpos、g、子部位比 ⇒ 0 不同才算過；並附 F1 的閘
 F7 必報：流程出場原因分佈（買進前本段已有 W1、W1 賣 3 成、40 天沒新高、回落 30%、W2、未完）、B 的持有天數分佈、組合層買進筆數與平均持股
輸出 backtest/resultsYL_flowexit/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR

TIME = "2026-09-30 21:10（台北）"
OUT = "backtest/resultsYL_flowexit"
X = 0.20
COST = R.COST
W30 = 0.3
VARS = ("A", "B", "C", "D")
VNAME = {"A": "A 正式", "B": "B 流程", "C": "C 流程＋正式天數上限", "D": "D 正式＋流程延長"}
STR = {"營量 v1": {"rule": "H60", "H": 60, "N": 20, "sig": "sig13"}, "營飆 v1": {"rule": "H120", "H": 120, "N": 10, "sig": "sig"}}
SEGS = {"全部": ("2017-01-01", "2026-12-31"), "2021-2023": ("2021-01-01", "2023-12-31"), "2024-2026.08": ("2024-01-01", "2026-08-31")}
NYF = 200


# ── surge_flow_daily（commit 18f363f654）逐字抄入 ──
def anchor_of(c, T):
    """資料日（或買進日）T 往前 250 個交易日內，最高收盤之前的最低收盤日。"""
    lo = max(T - 249, 0); P0 = lo + int(np.argmax(c[lo:T + 1]))
    return lo + int(np.argmin(c[lo:P0 + 1]))


def cuts_rec(cs, x=X):
    """[t..] 收盤 ⇒ [(a, trough, recover)]（相對位置；a ＞ 0 且回落 ≥ x；recover ＝ a 之後下一個新高日）；同 mid_desc M2／M2b。"""
    rm = np.maximum.accumulate(cs)
    nh = np.flatnonzero(cs[1:] > rm[:-1]) + 1
    pk = np.r_[0, nh]; out = []
    for j in np.flatnonzero(np.diff(pk) >= 2):
        a, b = int(pk[j]), int(pk[j + 1]); seg = cs[a + 1:b]; k = int(np.argmin(seg))
        if a > 0 and seg[k] <= cs[a] * (1 - x) * (1 + 1e-9):
            out.append((a, a + 1 + k, b))
    return out


def anchor_before(c, e):
    """F2：資料到 e−1（同 researchYL_entrystage.anchor_before）。"""
    T = e - 1; t = anchor_of(c, T); nre = 0
    for _ in range(50):
        rm_ = np.maximum.accumulate(c[t:T + 1]); w_ = np.flatnonzero(c[t:T + 1] <= rm_ * 0.7)
        st_ = t + int(w_[0]) if len(w_) else None
        if st_ is None:
            break
        t = st_ + int(np.argmin(c[st_:T + 1])); nre += 1
    return t, nre


# ═════════════ 飆股訊號（照 researchSurge6_restexit.build）═════════════
def surge_signals(sids, cal_e, log):
    """⇒ {sid: (W1, W2)}（引擎日曆長布林）、資訊。⚠ 會切 D.DATA，結束時切回快照。"""
    from backtest import researchSurge5 as S5
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str)
    D.DATA = S5.ST; cal_s = D.load_calendar()
    bar = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r")
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(S5.WORK, "F.npy"), mmap_mode="r"); FX = S5.FIX
    _, DISP = S5.SF.att_disp(S5.MAIN, cal_s)
    s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    gi = cal_s.get_indexer(cal_e); ok = gi >= 0
    out = {}; miss = []
    for sid in sorted(sids):
        if sid not in s2i:
            miss.append(sid); continue
        s = s2i[sid]; st = D.load_stock(sid, uni.loc[s, "market"], cal_s)
        if st is None:
            miss.append(sid); continue
        n = len(cal_s); bs = np.asarray(bar[s], bool)
        c0 = st.df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(c0) & bs)
        HI20 = np.zeros(n, bool); NEAR = np.zeros(n, bool)
        if len(idx) >= 25:
            cb = c0[idx]
            mx20 = pd.Series(cb).rolling(20, min_periods=20).max().to_numpy(); pmx = np.r_[np.nan, mx20[:-1]]
            HI20[idx] = cb > pmx; NEAR[idx] = cb >= 0.9 * mx20
        att = np.asarray(Qm[FX["att_10"], s]) == 5
        surge = (np.asarray(Qm[FX["lu_5"], s]) == 5) | (np.asarray(Qm[FX["r_5"], s]) == 5)
        nod60 = np.asarray(Fm[FX["disp_60"], s]) == 0
        w1 = HI20 & att & surge & nod60 & bs
        EXIT = np.zeros(n, bool); RE60 = np.zeros(n, bool); iv = DISP.get(sid, []); st_ = sorted(a for a, b in iv)
        for a, b in iv:
            if 0 <= a < n and any(0 < a - x <= 60 for x in st_ if x != a):
                RE60[a] = True
            if 0 <= b + 1 < n:
                EXIT[b + 1] = True
        w2 = ((RE60 & NEAR) | (EXIT & NEAR)) & bs
        W1e = np.zeros(len(cal_e), bool); W2e = np.zeros(len(cal_e), bool)
        W1e[ok] = w1[gi[ok]]; W2e[ok] = w2[gi[ok]]
        out[sid] = (W1e, W2e)
    att_raw = pd.read_csv(os.path.join(S5.MAIN, "meta", "attention.csv"), dtype=str, usecols=["date"])["date"]
    dsp_raw = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype=str, usecols=["start_date"])["start_date"]
    info = {"飆股日曆": [str(cal_s[0].date()), str(cal_s[-1].date())], "引擎日曆對不到的天數": int((~ok).sum()), "不在飆股母體的檔": miss,
            "注意表最早": str(att_raw.min()), "處置表最早": str(dsp_raw.min())}
    RR.use_snapshot()
    log(f"[飆股訊號] {len(out)} 檔｜缺 {len(miss)}｜{info}")
    return out, info


# ═════════════ 逐筆流程 ═════════════
def stock_arrays(ctx, sid, n0):
    B = R.load_bars(sid, ctx["mk"].get(sid, "twse"), ctx["cal"])
    c = np.asarray(ctx["closes"][sid], float)[:n0]; o = np.asarray(ctx["opens"][sid], float)[:n0]
    bar = np.zeros(n0, bool)
    if B is not None:
        bar[B["idx"][B["idx"] < n0]] = True
    okop = bar & np.isfinite(o) & (o > 0)
    nxt = np.full(n0 + 1, -1, np.int64)
    for p in range(n0 - 1, -1, -1):
        nxt[p] = p if okop[p] else nxt[p + 1]
    return {"c": c, "o": o, "bar": bar, "cb": np.cumsum(bar), "nxt": nxt, "B": B}


def flow_one(S, W1, W2, e, n0):
    """⇒ dict：錨、stop、各子部位 (kind, day)、原因。kind：'open'（該日開盤賣）｜'end'（未完）。"""
    c, cb, nxt = S["c"], S["cb"], S["nxt"]; last = n0 - 1
    nxo = lambda d: (int(nxt[d + 1]) if d + 1 <= last and nxt[d + 1] >= 0 else None)
    t, nre = anchor_before(c, e)
    seg = c[t:last + 1]; rmx = np.maximum.accumulate(seg); sw = np.flatnonzero(seg <= rmx * 0.7)
    stop = t + int(sw[0]) if len(sw) else None
    lastday = stop if stop is not None else last
    CU = [(t + a, t + b, t + r) for a, b, r in cuts_rec(c[t:e + 1])]
    segst = max([b for a, b, r in CU if r <= e], default=t)
    pre1 = [int(d) for d in segst + np.flatnonzero(W1[segst:e])] if (stop is None or stop > e) else []
    if pre1:
        d1_, d1date = e, pre1[0]
    else:
        cand = e + np.flatnonzero(W1[e:lastday + 1]); cand = cand[cand < stop] if stop is not None else cand
        d1_ = int(cand[0]) if len(cand) else None; d1date = d1_
    sg_ = c[t:lastday + 1]; r_ = np.maximum.accumulate(sg_)
    isnh = np.r_[True, sg_[1:] > r_[:-1]]; lastnh = t + np.maximum.accumulate(np.where(isnh, np.arange(len(sg_)), 0))
    nbar = cb[t:lastday + 1] - cb[lastnh]; hh = t + np.flatnonzero(nbar >= 40); hh = hh[hh >= e]
    n40 = int(hh[0]) if len(hh) else None
    rec = {"t": t, "重錨": nre, "stop": -1 if stop is None else stop, "本段起點": segst, "買進前W1": int(bool(pre1)), "d1": -1 if d1date is None else d1date,
           "n40": -1 if n40 is None else n40, "W2日": -1}
    op = lambda x: ("open", x) if x is not None else ("end", None)
    if n40 is not None and (d1_ is None or n40 <= d1_):
        p = op(nxo(n40)); rec.update(p30=p, p70=p, 原因30="40天沒新高", 原因70="40天沒新高"); rec["d1"] = -1
        return rec
    if d1_ is None:
        if stop is not None:
            p = op(nxo(stop)); rec.update(p30=p, p70=p, 原因30="回落30%", 原因70="回落30%")
        else:
            rec.update(p30=("end", None), p70=("end", None), 原因30="未完", 原因70="未完")
        return rec
    ex1 = nxo(d1_)
    if ex1 is None:
        rec.update(p30=("end", None), p70=("end", None), 原因30="未完", 原因70="未完")
        return rec
    rec.update(p30=("open", ex1), 原因30="W1")
    pre2 = [int(d) for d in np.flatnonzero(W2[max(segst, d1date + 1):e]) + max(segst, d1date + 1)] if d1date < e else []
    if pre2:
        rec.update(p70=("open", ex1), 原因70="W2（買進前）", W2日=pre2[0])
        return rec
    w2c = ex1 + np.flatnonzero(W2[ex1:lastday + 1]) if ex1 <= lastday else np.array([], int)
    w2d = int(w2c[0]) if len(w2c) else None
    if w2d is None or (stop is not None and w2d >= stop):
        if stop is not None:
            rec.update(p70=op(nxo(stop)), 原因70="回落30%")
        else:
            rec.update(p70=("end", None), 原因70="未完")
    else:
        rec.update(p70=op(nxo(w2d)), 原因70="W2", W2日=w2d)
    return rec


def portion(kind, day, S, n0, px_formal=None):
    """⇒ (tk, xpos, px, dlast)。tk 越大越晚；'open' X ⇒ 2X；'close' d ⇒ 2d＋1；'end' ⇒ 2n0。"""
    if kind == "open":
        return (2 * day, day, float(S["o"][day]), day - 1)
    if kind == "close":
        return (2 * day + 1, day, float(px_formal), day)
    return (2 * n0, n0, float(S["c"][n0 - 1]) if px_formal is None else float(px_formal), n0 - 1)


def finalize(parts, bp, e, S, n0, dbad, L, NP):
    """parts ＝ [p30, p70]（portion 元組）⇒ 壞根截、停止交易（引擎同一條）⇒ dict（xpos、g、子部位、合成收盤）。"""
    c = S["c"]; nbad = 0
    if dbad is not None:
        pp = []
        for p in parts:
            if p[0] > 2 * dbad + 1:
                p = (2 * dbad + 1, dbad, float(c[dbad]), dbad); nbad = 1
            pp.append(p)
        parts = pp
    w = (W30, 1 - W30)
    fin = max(parts, key=lambda p: p[0])
    xpos = fin[1]
    Sc = np.empty(NP); cc = np.r_[c, c[-1]] if NP > n0 else c
    tt = np.arange(NP)
    Sc[:] = 0.0
    for wi, p in zip(w, parts):
        Sc += wi * np.where(tt <= p[3], cc[:NP], p[2])
    sf = 0
    if L is not None and xpos > L + 1:
        parts = [p if p[3] <= L else (2 * L + 1, L + 1, float(c[L]), L) for p in parts]; sf = 1
        xpos = L + 1
    px = [p[2] for p in parts]
    g = (w[0] * px[0] + w[1] * px[1]) / bp - 1.0
    if sf:
        g = float(Sc[L]) / bp - 1.0
    days = [int(S["cb"][min(p[3], n0 - 1)] - (S["cb"][e - 1] if e > 0 else 0)) for p in parts]
    return {"xpos": int(xpos), "g": float(g), "x30": int(parts[0][1]), "x70": int(parts[1][1]), "px30": px[0], "px70": px[1],
            "天30": days[0], "天70": days[1], "壞根截": nbad, "停止交易": sf, "Sc": Sc}


def engine_ep(ctx, sid, e):
    ep = float(ctx["opens"][sid][e])
    if not np.isfinite(ep) or ep <= 0:
        ep = float(ctx["closes"][sid][e])
    return ep


def build_variants(ctx, sig, rule, H, SIGW, SA, SF, n0, NP):
    """每列候選訊號 ⇒ 流程細節與 A～D 的 (xpos, g, 子部位, Sc)。"""
    rows = []; SCS = {v: {} for v in VARS}
    for r in sig.itertuples(index=False):
        sid = r.sid; e = int(r.entry_pos); xf = int(getattr(r, f"xpos_{rule}")); gf = float(getattr(r, f"g_{rule}"))
        if xf < 0:
            continue
        S = SA[sid]; bp = engine_ep(ctx, sid, e)
        W1, W2 = SIGW.get(sid, (np.zeros(n0, bool), np.zeros(n0, bool)))
        fr = flow_one(S, W1, W2, e, n0)
        B = S["B"]; dbad = None
        if B is not None:
            idx = B["idx"]; kb = int(np.searchsorted(idx, e)) - 1; nbk = int(B["next_bad"][max(0, kb - 20)])
            if nbk < len(idx):
                dbad = int(idx[nbk - 1])
        L = SF.get(sid)
        pf = portion("close", xf, S, n0, bp * (1 + gf)) if xf < n0 else portion("end", None, S, n0, bp * (1 + gf))
        pB = [portion(k, d, S, n0) for k, d in (fr["p30"], fr["p70"])]
        V = {"A": [pf, pf], "B": pB,
             "C": [pf if pf[0] <= p[0] else p for p in pB],
             "D": [pf if pf[0] >= p[0] else p for p in pB]}
        key = f"{sid}#{e}"
        base = {"sid": sid, "e": e, "key": key, "bp": bp, "xf": xf, "gf": gf, "dbad": -1 if dbad is None else dbad, "L": -1 if L is None else L,
                **{k: v for k, v in fr.items() if k not in ("p30", "p70")},
                "流程30": f"{fr['p30'][0]}{'' if fr['p30'][1] is None else fr['p30'][1]}", "流程70": f"{fr['p70'][0]}{'' if fr['p70'][1] is None else fr['p70'][1]}"}
        for v in VARS:
            if v == "A":
                # A 直接用正式 xpos／g（引擎本來怎麼跑就怎麼記）；停止交易照引擎規則
                Sc = np.asarray(ctx["closes"][sid], float)[:NP].copy()
                xa, ga, sf = xf, gf, 0
                if L is not None and xf > L + 1:
                    xa, ga, sf = L + 1, float(ctx["closes"][sid][L]) / bp - 1.0, 1
                d_ = int(S["cb"][L if sf else min(xf, n0 - 1)] - (S["cb"][e - 1] if e > 0 else 0))
                f = {"xpos": xa, "g": ga, "x30": xa, "x70": xa, "px30": bp * (1 + ga), "px70": bp * (1 + ga), "天30": d_, "天70": d_, "壞根截": 0, "停止交易": sf, "Sc": Sc}
            else:
                f = finalize(V[v], bp, e, S, n0, dbad, L, NP)
            SCS[v][key] = f.pop("Sc")
            base.update({f"{v}_{k}": val for k, val in f.items()})
        rows.append(base)
    return pd.DataFrame(rows), SCS


# ═════════════ 引擎 ═════════════
def run_engine(ctx, strat, sig, rule, N, r, SF, closes=None, opens=None, held_map=None, audit=True):
    au = [] if audit else None
    kw = dict(log=[], d_max=None, pick="relvol", queue_days=0) if strat == "營量 v1" else {}
    seed = (RR.P1_SEED0 if strat == "營量 v1" else 1000) + r
    o = R.simulate_mtm(sig, rule, N, np.random.default_rng(seed), closes or ctx["closes"], opens or ctx["opens"], ctx["ncal"], return_equity=True,
                       stop_force=SF, audit=au, held_map=held_map, **kw)
    return o, au


def keyed_inputs(ctx, sig, rule, TR, v, SCS, SF):
    """⇒ (sig_k, closes, opens, SF_k, held_map)：變體 v 的 held_map 輸入。"""
    T = TR.set_index(["sid", "e"])
    s2 = sig[sig[f"xpos_{rule}"] >= 0].copy()
    k = [f"{s}#{e}" for s, e in zip(s2["sid"], s2["entry_pos"].astype(int))]
    tv = T.loc[list(zip(s2["sid"], s2["entry_pos"].astype(int)))]
    hm = dict(zip(k, s2["sid"]))
    if v != "A":
        s2[f"xpos_{rule}"] = tv[f"{v}_xpos"].to_numpy(np.int64); s2[f"g_{rule}"] = tv[f"{v}_g"].to_numpy(float)
    s2["sid"] = k
    cl = {**ctx["closes"], **{kk: SCS[v][kk] for kk in k}}
    op = {**ctx["opens"], **{kk: ctx["opens"][hm[kk]] for kk in k}}
    SFk = {**SF, **{kk: SF[hm[kk]] for kk in k if hm[kk] in SF}}
    return s2, cl, op, SFk, hm


def seg_pos(cal, w0, w1):
    out = {}
    for sg, (a, b) in SEGS.items():
        x = max(int(cal.searchsorted(pd.Timestamp(a))), w0); y = min(int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1, w1)
        out[sg] = (x, y)
    return out


def port_row(o, au, SEGP, w0, w1):
    eq = np.asarray(o["equity"], float); row = {}
    for sg, (x, y) in SEGP.items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
    cnt = np.zeros(len(eq) + 1); opn = {}; hold = []
    for a in sorted(au, key=lambda z: (z["t"], z["side"] != "sell")):
        cnt[a["t"]] += 1 if a["side"] == "buy" else -1
        if a["side"] == "buy":
            opn[a["sid"]] = a["t"]
        else:
            t0 = opn.pop(a["sid"], None)
            if t0 is not None and w0 <= t0 <= w1:
                hold.append(a["t"] - t0)
    hc = np.cumsum(cnt)[:len(eq)]
    row["買進筆"] = int(sum(1 for a in au if a["side"] == "buy" and w0 <= a["t"] <= w1))
    row["平均持股"] = float(np.mean(hc[w0:w1 + 1])); row["平均持有日"] = float(np.mean(hold)) if hold else np.nan
    return row, eq


# ═════════════ 主程式 ═════════════
def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); NP = ctx["ncal"]; w0, w1 = ctx["w0"], ctx["w1"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    SEGP = seg_pos(cal, w0, w1)
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
    gates = {}
    sids = sorted(set(ctx["sig13"]["sid"]) | set(ctx["sig"]["sid"]))
    SA = {s: stock_arrays(ctx, s, n0) for s in sids}
    log(f"[價格] {len(SA)} 檔｜{time.time() - T0:.0f}s")
    SIGW, sinfo = surge_signals(sids, cal, log)
    TRS = {}; PR = []; ATR = {}
    for strat, cf in STR.items():
        sig = ctx[cf["sig"]]; rule = cf["rule"]
        TR, SCS = build_variants(ctx, sig, rule, cf["H"], SIGW, SA, SF, n0, NP)
        TR.insert(0, "策略", strat); TRS[strat] = TR
        gates[f"{strat} 候選列（代號, 進場位置）不重複"] = bool(not TR.duplicated(["sid", "e"]).any())
        gates[f"{strat} 候選列都在流程母體內（缺 K 棒檔數）"] = int(sum(SA[s]["B"] is None for s in set(TR["sid"])))
        log(f"[{strat}] 候選 {len(TR)} 列｜{time.time() - T0:.0f}s")
        seeds = [0, 1] if strat == "營量 v1" else list(range(NYF))
        keyed = {v: keyed_inputs(ctx, sig, rule, TR, v, SCS, SF) for v in ("A", "B", "C", "D")}
        buys = []; EQ0 = {}
        for r in seeds:
            o, au = run_engine(ctx, strat, sig, rule, cf["N"], r, SF)
            row, eq = port_row(o, au, SEGP, w0, w1)
            key = "c13" if strat == "營量 v1" else "c1"
            rr = ref[(ref["key"] == key) & (ref["var"] == "t1") & (ref["r"] == r)].iloc[0]
            c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
            ok = repr(float(c_)) == repr(float(rr["cagr"])) and repr(float(m_)) == repr(float(rr["mdd"]))
            gates.setdefault(f"① {strat} A ＝ resultsT1fix（不同顆數）", 0); gates[f"① {strat} A ＝ resultsT1fix（不同顆數）"] += int(not ok)
            PR.append({"策略": strat, "出場": "A", "r": r, **row})
            b = pd.DataFrame([a for a in au if a["side"] == "buy"])[["t", "sid", "px"]]; b["r"] = r; buys.append(b)
            if r < (1 if strat == "營量 v1" else 5):
                s2, cl, op, SFk, hm = keyed["A"]
                o2, _ = run_engine(ctx, strat, s2, rule, cf["N"], r, SFk, cl, op, hm, audit=False)
                gates.setdefault(f"② {strat} A 走 held_map ＝ A（不同顆數）", 0)
                gates[f"② {strat} A 走 held_map ＝ A（不同顆數）"] += int(not np.array_equal(np.asarray(o2["equity"], float), eq))
            EQ0[r] = eq
            for v in ("B", "C", "D"):
                s2, cl, op, SFk, hm = keyed[v]
                o2, au2 = run_engine(ctx, strat, s2, rule, cf["N"], r, SFk, cl, op, hm)
                row2, _ = port_row(o2, au2, SEGP, w0, w1)
                PR.append({"策略": strat, "出場": v, "r": r, **row2})
            if r % 50 == 0:
                log(f"[{strat}] r{r}｜{time.time() - T0:.0f}s")
        BY = pd.concat(buys, ignore_index=True); BY["sid"] = BY["sid"].astype(str)
        if strat == "營量 v1":
            f0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str}); f0 = f0[f0["side"] == "buy"][["t", "sid"]].reset_index(drop=True)
            y0 = BY[BY["r"] == 0].reset_index(drop=True); y1 = BY[BY["r"] == 1].reset_index(drop=True)
            gates["③ 營量 r0 A 買進列 ＝ audit_seed0"] = bool(len(f0) == len(y0) and (f0["t"].to_numpy() == y0["t"].to_numpy()).all() and (f0["sid"].to_numpy() == y0["sid"].to_numpy()).all())
            gates["營量 r1 A 買進列 ＝ r0（不抽籤）"] = bool(len(y1) == len(y0) and (y1["t"].to_numpy() == y0["t"].to_numpy()).all() and (y1["sid"].to_numpy() == y0["sid"].to_numpy()).all())
            BY = y0.assign(r=0)
        ATR[strat] = BY
        del keyed, SCS
    PR = pd.DataFrame(PR); PR.to_csv(os.path.join(OUT, "portfolio_seeds.csv.gz"), index=False, float_format="%.10g")
    # 營量 r1 ＝ r0（B／C／D）
    for v in VARS:
        x = PR[(PR["策略"] == "營量 v1") & (PR["出場"] == v)]
        gates[f"營量 {v} r1 ＝ r0（年化回落）"] = bool(len(x) == 2 and all(x[f"{sg}_{k}"].nunique() == 1 for sg in SEGS for k in ("年化", "回落")))
    TRA = pd.concat(TRS.values(), ignore_index=True)
    TRA.to_csv(os.path.join(OUT, "signals_flow.csv.gz"), index=False, float_format="%.10g")
    # 逐筆：A 的實際交易
    P = []
    for strat, BY in ATR.items():
        T = TRS[strat].set_index(["sid", "e"])
        m = T.loc[list(zip(BY["sid"], BY["t"].astype(int)))].reset_index()
        m["r"] = BY["r"].to_numpy(); m["進場日"] = [str(cal[int(x)].date()) for x in m["e"]]
        pxbad = int((~np.isclose(m["bp"].to_numpy(float), BY["px"].to_numpy(float), rtol=1e-9)).sum())
        gates[f"{strat} A 交易進場價 ＝ 引擎（不同筆數）"] = pxbad
        P.append(m)
    PT = pd.concat(P, ignore_index=True)
    for v in VARS:
        PT[f"{v}_r30"] = PT[f"{v}_px30"] / PT["bp"] - 1; PT[f"{v}_r70"] = PT[f"{v}_px70"] / PT["bp"] - 1
        PT[f"{v}_報酬"] = W30 * PT[f"{v}_r30"] + (1 - W30) * PT[f"{v}_r70"] - COST
        PT[f"{v}_天"] = W30 * PT[f"{v}_天30"] + (1 - W30) * PT[f"{v}_天70"]
    PT.to_csv(os.path.join(OUT, "trades_A_entries.csv.gz"), index=False, float_format="%.10g")
    gates["A 逐筆 g ＝ 正式 g（停止交易外，不同筆數）"] = int((~np.isclose(PT.loc[PT["A_停止交易"] == 0, "A_g"], PT.loc[PT["A_停止交易"] == 0, "gf"], rtol=1e-12)).sum())
    ST = per_trade_summary(PT, n0); ST.to_csv(os.path.join(OUT, "summary_per_trade.csv"), index=False, float_format="%.6g")
    RS = reason_summary(PT); RS.to_csv(os.path.join(OUT, "summary_flow_reasons.csv"), index=False, float_format="%.6g")
    SP = port_summary(PR); SP.to_csv(os.path.join(OUT, "summary_portfolio.csv"), index=False, float_format="%.6g")
    META = {"讀法寫死": TIME, "閘": gates, "飆股訊號": sinfo, "SEGP": {k: [str(cal[a].date()), str(cal[b].date())] for k, (a, b) in SEGP.items()},
            "候選列": {s: int(len(TRS[s])) for s in TRS}, "A 交易筆": {s: int(len(ATR[s])) for s in ATR}, "營飆 A 去重筆": int(ATR["營飆 v1"][["sid", "t"]].drop_duplicates().shape[0]),
            "壞根截（候選列，B）": {s: int(TRS[s]["B_壞根截"].sum()) for s in TRS}, "日曆尾": str(cal[-1].date()), "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {json.dumps(META, ensure_ascii=False, default=str)}")
    if not all(v is True or v == 0 for v in gates.values()):
        raise SystemExit(f"⛔ 閘不過 {gates}")


def per_trade_summary(PT, n0):
    out = []
    for strat in STR:
        for dd in ((False, True) if strat == "營飆 v1" else (False,)):
            m0 = PT[PT["策略"] == strat]
            if dd:
                m0 = m0.drop_duplicates(["sid", "e"])
            for sg, (a, b) in SEGS.items():
                m = m0[(m0["進場日"] >= a) & (m0["進場日"] <= b)]
                if not len(m):
                    continue
                for v in VARS:
                    x = m[f"{v}_報酬"]; d = m[f"{v}_天"]
                    out.append({"策略": strat, "口徑": "去重" if dd else ("200 顆合併" if strat == "營飆 v1" else "r0"), "段": sg, "出場": v, "筆數": len(m),
                                "平均": x.mean(), "中位": x.median(), "勝率": (x > 0).mean(), "賺的平均": x[x > 0].mean(), "賠的平均": x[x <= 0].mean(),
                                "p10": x.quantile(.1), "p90": x.quantile(.9), "平均持有天數": d.mean(), "每天報酬": x.mean() / d.mean(),
                                "3成平均": m[f"{v}_r30"].mean(), "7成平均": m[f"{v}_r70"].mean(), "對A差平均": (x - m["A_報酬"]).mean(),
                                "對A差中位": (x - m["A_報酬"]).median(), "比A好比例": (x > m["A_報酬"] + 1e-12).mean(), "未完": (m[f"{v}_xpos"] >= n0).mean()})
    return pd.DataFrame(out)


def reason_summary(PT):
    out = []
    for strat in STR:
        m0 = PT[PT["策略"] == strat]
        for sg, (a, b) in SEGS.items():
            m = m0[(m0["進場日"] >= a) & (m0["進場日"] <= b)]
            if not len(m):
                continue
            r = {"策略": strat, "段": sg, "筆數": len(m), "買進前本段已有W1": m["買進前W1"].mean(), "重錨過": (m["重錨"] > 0).mean()}
            for k in ("原因30", "原因70"):
                for nm, cn in m[k].value_counts(normalize=True).items():
                    r[f"{k}｜{nm}"] = cn
            d = m["B_天"]
            r.update({"B 持有天數 中位": d.median(), "B 持有天數 p10": d.quantile(.1), "B 持有天數 p90": d.quantile(.9),
                      "B 比正式短": (m["B_天"] < m["A_天"]).mean(), "D 比正式長": (m["D_天"] > m["A_天"] + 1e-9).mean(),
                      "C 比正式短": (m["C_天"] < m["A_天"] - 1e-9).mean(), "B 壞根截": m["B_壞根截"].mean(), "B 停止交易": m["B_停止交易"].mean()})
            out.append(r)
    return pd.DataFrame(out)


def port_summary(PR):
    out = []
    for strat in STR:
        for v in VARS:
            x = PR[(PR["策略"] == strat) & (PR["出場"] == v)].sort_values("r")
            a = PR[(PR["策略"] == strat) & (PR["出場"] == "A")].sort_values("r")
            if strat == "營量 v1":
                x = x[x["r"] == 0]; a = a[a["r"] == 0]
            for sg in SEGS:
                cg = x[f"{sg}_年化"].to_numpy(); md = x[f"{sg}_回落"].to_numpy()
                dc = cg - a[f"{sg}_年化"].to_numpy(); dm = md - a[f"{sg}_回落"].to_numpy()
                out.append({"策略": strat, "出場": v, "段": sg, "顆數": len(x), "年化 中位": np.median(cg), "年化 p10": np.quantile(cg, .1), "年化 p90": np.quantile(cg, .9),
                            "回落 中位": np.median(md), "回落 p10": np.quantile(md, .1), "回落 p90": np.quantile(md, .9),
                            "對A年化差 中位": np.median(dc), "對A回落差 中位": np.median(dm), "年化贏A比例": float(np.mean(dc > 1e-12)) if v != "A" else np.nan,
                            "回落比A淺比例": float(np.mean(dm > 1e-12)) if v != "A" else np.nan,
                            "買進筆 中位": float(x["買進筆"].median()), "平均持股 中位": float(x["平均持股"].median()), "平均持有日 中位": float(x["平均持有日"].median())})
    return pd.DataFrame(out)


# ═════════════ 查核 ═════════════
def check(log):
    from backtest import researchT1fix as T1
    from backtest import researchSurge5 as S5
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); last = n0 - 1
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), ctx["w1"])
    PT = pd.read_csv(os.path.join(OUT, "trades_A_entries.csv.gz"), dtype={"sid": str})
    SMP = PT.drop_duplicates(["策略", "sid", "e"]).sample(50, random_state=20260930)
    # 飆股資料（逐根）
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    D.DATA = S5.ST; cal_s = D.load_calendar(); pos_s = {d: j for j, d in enumerate(cal_s)}
    bar_s = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r")
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(S5.WORK, "F.npy"), mmap_mode="r"); FX = S5.FIX
    dsp = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    SIGC = {}
    for sid in sorted(set(SMP["sid"])):
        W1 = np.zeros(n0, bool); W2 = np.zeros(n0, bool)
        if sid in s2i:
            s = s2i[sid]; c0 = D.load_stock(sid, uni.loc[s, "market"], cal_s).df["close"].to_numpy(float)
            bars = [d for d in range(len(cal_s)) if np.isfinite(c0[d]) and bar_s[s, d]]; bpos = {d: j for j, d in enumerate(bars)}
            att = np.asarray(Qm[FX["att_10"], s]); lu5 = np.asarray(Qm[FX["lu_5"], s]); r5 = np.asarray(Qm[FX["r_5"], s]); d60 = np.asarray(Fm[FX["disp_60"], s])
            g = dsp[dsp["stock_id"] == sid]
            starts = [int(cal_s.searchsorted(pd.Timestamp(x))) for x in g["start_date"]]
            ends = [int(cal_s.searchsorted(pd.Timestamp(y), side="right")) - 1 for y in g["end_date"]]
            for te in range(n0):
                d = pos_s.get(cal[te])
                if d is None or d not in bpos:
                    continue
                j = bpos[d]
                if j >= 20 and c0[d] > max(c0[bars[j - 20:j]]) and att[d] == 5 and (lu5[d] == 5 or r5[d] == 5) and d60[d] == 0:
                    W1[te] = True
                near = j >= 19 and c0[d] >= 0.9 * max(c0[bars[j - 19:j + 1]])
                re60 = d in starts and any(0 < d - x <= 60 for x in starts if x != d)
                ex_ = any(d == b + 1 for b in ends)
                W2[te] = near and (re60 or ex_)
        SIGC[sid] = (W1, W2)
    RR.use_snapshot()
    errs = []; nd = 0; cnt = {"W1": 0, "n40": 0, "stop": 0, "W2": 0, "未完": 0, "買進前W1": 0}
    for r in SMP.itertuples():
        sid, e = r.sid, int(r.e); why = []
        B = R.load_bars(sid, ctx["mk"].get(sid, "twse"), cal)
        c = np.asarray(ctx["closes"][sid], float)[:n0]; o = np.asarray(ctx["opens"][sid], float)[:n0]
        isb = np.zeros(n0, bool); isb[B["idx"][B["idx"] < n0]] = True
        W1, W2 = SIGC[sid]
        bp = float(o[e]) if np.isfinite(o[e]) and o[e] > 0 else float(c[e])

        def nxo(d):
            x = d + 1
            while x <= last and not (isb[x] and np.isfinite(o[x]) and o[x] > 0):
                x += 1
            return x if x <= last else None
        # 錨（逐日）
        T = e - 1; lo = max(T - 249, 0); P0 = lo
        for d in range(lo, T + 1):
            if c[d] > c[P0]:
                P0 = d
        t = lo
        for d in range(lo, P0 + 1):
            if c[d] < c[t]:
                t = d
        for _ in range(50):
            rm = -np.inf; st_ = None
            for d in range(t, T + 1):
                rm = max(rm, c[d])
                if c[d] <= rm * 0.7:
                    st_ = d; break
            if st_ is None:
                break
            m_ = st_
            for d in range(st_, T + 1):
                if c[d] < c[m_]:
                    m_ = d
            t = m_
        rm = -np.inf; stop = None
        for d in range(t, last + 1):
            rm = max(rm, c[d])
            if c[d] <= rm * 0.7:
                stop = d; break
        # 本段起點（逐日找回升日 ≤ e 的 20% 拉回）
        pk, pkd, tv, tvd, segst = c[t], t, np.inf, -1, t
        for d in range(t + 1, e + 1):
            if c[d] > pk:
                if pkd > t and tv <= pk * (1 - X) * (1 + 1e-9):
                    segst = tvd
                pk, pkd, tv, tvd = c[d], d, np.inf, -1
            elif c[d] < tv:
                tv, tvd = c[d], d
        pre1 = next((d for d in range(segst, e) if W1[d]), None) if (stop is None or stop > e) else None
        # 逐日狀態機（全部持有）
        lastday = stop if stop is not None else last
        rmx = -np.inf; nbars = 0; ev = None
        for d in range(t, lastday + 1):
            if c[d] > rmx:
                rmx = c[d]; nbars = 0
            elif isb[d]:
                nbars += 1
            if d < e:
                continue
            if nbars >= 40:
                ev = ("n40", d); break
            if (d == e and pre1 is not None) or (W1[d] and (stop is None or d < stop)):
                ev = ("W1", d); break
        if ev is None and stop is not None:
            ev = ("stop", stop)
        if ev is None:
            p30 = p70 = ("end", None); cnt["未完"] += 1
        elif ev[0] in ("n40", "stop"):
            x = nxo(ev[1]); p30 = p70 = ("open", x) if x is not None else ("end", None); cnt[ev[0]] += 1
        else:
            cnt["W1"] += 1; cnt["買進前W1"] += int(pre1 is not None and ev[1] == e)
            x1 = nxo(ev[1])
            if x1 is None:
                p30 = p70 = ("end", None)
            else:
                p30 = ("open", x1)
                d1date = pre1 if (pre1 is not None and ev[1] == e) else ev[1]
                pre2 = next((d for d in range(max(segst, d1date + 1), e) if W2[d]), None) if d1date < e else None
                if pre2 is not None:
                    p70 = ("open", x1); cnt["W2"] += 1
                else:
                    w2d = next((d for d in range(x1, lastday + 1) if W2[d] and (stop is None or d < stop)), None)
                    if w2d is not None:
                        x2 = nxo(w2d); cnt["W2"] += 1
                    elif stop is not None:
                        x2 = nxo(stop)
                    else:
                        x2 = None
                    p70 = ("open", x2) if x2 is not None else ("end", None)
        # 組合 A～D（逐筆重寫）
        xf = int(r.xf); gf = float(r.gf); L = SF.get(sid)
        idx = B["idx"]; kb = int(np.searchsorted(idx, e)) - 1; nbk = int(B["next_bad"][max(0, kb - 20)]); dbad = int(idx[nbk - 1]) if nbk < len(idx) else None

        def tk(p):
            return 2 * p[1] if p[0] == "open" else (2 * p[1] + 1 if p[0] == "close" else 2 * n0)
        fp = ("close", xf, "正式") if xf < n0 else ("end", None, "正式")
        p30 = (*p30, "流程"); p70 = (*p70, "流程")

        def px_of(p):
            return bp * (1 + gf) if p[2] == "正式" else (float(o[p[1]]) if p[0] == "open" else float(c[last]))

        def dl(p):
            return p[1] - 1 if p[0] == "open" else (p[1] if p[0] == "close" else last)
        for v, parts in (("B", [p30, p70]), ("C", [fp if tk(fp) <= tk(p) else p for p in (p30, p70)]), ("D", [fp if tk(fp) >= tk(p) else p for p in (p30, p70)])):
            q = []
            for p in parts:
                pv = (tk(p), p[1] if p[0] != "end" else n0, px_of(p), dl(p))
                if dbad is not None and pv[0] > 2 * dbad + 1:
                    pv = (2 * dbad + 1, dbad, float(c[dbad]), dbad)
                q.append(pv)
            fin = q[0] if q[0][0] >= q[1][0] else q[1]
            xp = fin[1]; g = (0.3 * q[0][2] + 0.7 * q[1][2]) / bp - 1
            if L is not None and xp > L + 1:
                val = sum(w * (c[L] if p[3] >= L else p[2]) for w, p in zip((0.3, 0.7), q))
                xp = L + 1; g = val / bp - 1
            if xp != int(getattr(r, f"{v}_xpos")) or not np.isclose(g, float(getattr(r, f"{v}_g")), rtol=1e-9, atol=1e-12):
                why.append(f"{v}: xpos {xp}/{getattr(r, f'{v}_xpos')} g {g:.6f}/{float(getattr(r, f'{v}_g')):.6f}")
        if t != int(r.t) or (stop if stop is not None else -1) != int(r.stop) or segst != int(r.本段起點):
            why.append(f"錨 {t}/{r.t} stop {stop}/{r.stop} 段 {segst}/{r.本段起點}")
        if why:
            nd += 1; errs.append(f"{r.策略} {sid} {e}：{'；'.join(why)}")
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    out = {"讀法寫死": TIME, "抽樣": "A 交易（營量＋營飆去重）抽 50 筆（random_state 20260930）", "不同": nd, "流程事件（抽樣）": cnt, "不同的筆": errs[:20],
           "F1 閘（主程式）": meta["閘"], "通過": nd == 0 and all(v is True or v == 0 for v in meta["閘"].values())}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 不同 {nd}｜{cnt}｜{errs[:3]}")


# ═════════════ 網頁 ═════════════
def page(log):
    ST = pd.read_csv(os.path.join(OUT, "summary_per_trade.csv")); SP = pd.read_csv(os.path.join(OUT, "summary_portfolio.csv"))
    RS = pd.read_csv(os.path.join(OUT, "summary_flow_reasons.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            ".sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}"
            ".pane{display:none}.pane.on{display:block}td.up{color:#b0261e;font-weight:600}td.dn{color:#1f6f3d;font-weight:600}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    P_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    D_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.0f}"
    B2 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.2f}%"
    st = lambda s, sg, v, kou=None: ST[(ST["策略"] == s) & (ST["段"] == sg) & (ST["出場"] == v) & ((ST["口徑"] == kou) if kou else (ST["口徑"] != "去重"))].iloc[0]
    sp = lambda s, sg, v: SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["出場"] == v)].iloc[0]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量營飆配飆股流程</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>營量、營飆改用飆股流程出場，期望值會變高嗎？（2017-03～2026-08）</h1>",
         "<p class='warn'>⚠ 只當參考，沒有計入檢定數。流程規則是使用者定的、不是從這批資料挑的；但四種出場只是描述比較，不作採用判定。</p>"]
    # 結論
    H.append("<h2>先講結論（全部期間）</h2><ul class='big'>")
    for s in STR:
        a, b, c_, d = (sp(s, "全部", v) for v in VARS)
        ta, tb, tc, td = (st(s, "全部", v) for v in VARS)
        best = max(("B", b), ("C", c_), ("D", d), key=lambda z: z[1]["年化 中位"])
        yf = s == "營飆 v1"
        H.append(f"<li><b>{s[:2]}</b>：正式出場（A）年化 {P1(a['年化 中位'])}、最大回落 {P1(a['回落 中位'])}"
                 + ("（200 顆種子中位）" if yf else "") + "。改用流程："
                 f"B 全程照流程 {P1(b['年化 中位'])}／{P1(b['回落 中位'])}，C 流程但不超過正式天數 {P1(c_['年化 中位'])}／{P1(c_['回落 中位'])}，"
                 f"D 正式到期還在續抱就延長 {P1(d['年化 中位'])}／{P1(d['回落 中位'])}"
                 + (f"（年化贏 A 的種子：B {P_(b['年化贏A比例'])}、C {P_(c_['年化贏A比例'])}、D {P_(d['年化贏A比例'])}）" if yf else "") + "。"
                 f"逐筆平均報酬（扣成本）A {B2(ta['平均'])} → B {B2(tb['平均'])}、C {B2(tc['平均'])}、D {B2(td['平均'])}；"
                 f"每持有一天 A {B2(ta['每天報酬'])} → B {B2(tb['每天報酬'])}、C {B2(tc['每天報酬'])}、D {B2(td['每天報酬'])}。</li>")
    H.append("</ul>")
    H.append("<div class='ok big' id='concl'>__CONCL__</div>")
    H.append(f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。四種出場用在<b>同一批候選訊號</b>上，組合層照正式引擎（同樣槽數、排序／抽籤、成本、停止交易強制出場）重新模擬，"
             "出場變了、槽位占用跟著變，買進的筆也跟著變。每筆拆成 3 成、7 成兩部分：流程在 W1 第一頂警示隔天開盤先賣 3 成，剩 7 成等 W2（再次處置或出關）或從最高回落 30%；"
             "還沒 W1 前連 40 個交易日沒創新高 ⇒ 全部賣。起漲點在進場前一天用資料找好、之後固定。"
             + (f"查核：抽 50 筆逐日重算，{CK['不同']} 筆不同；A 與正式 T1 版年化、回落逐位元相同。" if CK else "") + "</p>")
    # 組合層表
    H.append("<h2>一、組合層（正式引擎重新模擬）</h2><div class='sel'>策略 <select id='s1' onchange='sw()'>" + "".join(f"<option>{s}</option>" for s in STR) + "</select></div>")
    for s in STR:
        yf = s == "營飆 v1"
        H.append(f"<div class='pane' id='p1{s[:2]}'><div class='wrap'><table><tr><th class='l'>期間</th><th class='l'>出場</th><th>年化{'<br><small>中位（p10～p90）</small>' if yf else ''}</th>"
                 f"<th>最大回落{'<br><small>中位（p10～p90）</small>' if yf else ''}</th><th>對 A<br><small>年化差{'中位' if yf else ''}</small></th><th>對 A<br><small>回落差</small></th>"
                 + ("<th>年化贏 A<br><small>種子比例</small></th>" if yf else "") + "<th>買進筆</th><th>平均持股</th><th>平均持有<br><small>交易日</small></th></tr>")
        for sg in SEGS:
            for v in VARS:
                x = sp(s, sg, v)
                cls = "" if v == "A" else (" class='up'" if x["對A年化差 中位"] > 0 else " class='dn'")
                H.append(f"<tr><td class='l'>{sg if v == 'A' else ''}</td><td class='l'>{VNAME[v]}</td>"
                         f"<td>{P1(x['年化 中位'])}" + (f"<br><small>{P1(x['年化 p10'])}～{P1(x['年化 p90'])}</small>" if yf else "") + "</td>"
                         f"<td>{P1(x['回落 中位'])}" + (f"<br><small>{P1(x['回落 p10'])}～{P1(x['回落 p90'])}</small>" if yf else "") + "</td>"
                         f"<td{cls}>{'—' if v == 'A' else PT(x['對A年化差 中位'])}</td><td>{'—' if v == 'A' else PT(x['對A回落差 中位'])}</td>"
                         + (f"<td>{'—' if v == 'A' else P_(x['年化贏A比例'])}</td>" if yf else "")
                         + f"<td>{D_(x['買進筆 中位'])}</td><td>{x['平均持股 中位']:.1f}</td><td>{D_(x['平均持有日 中位'])}</td></tr>")
        H.append("</table></div><p class='note'>買進筆、平均持股、平均持有只算主窗（2017-03-02～2026-08-24）。分期是同一條權益曲線切出那段來算。"
                 + ("營飆抽籤，200 顆種子；對 A 差是同一顆種子相減後取中位。" if yf else "營量依 relvol 排序、不抽籤，只有一種結果。") + "</p></div>")
    # 逐筆表
    H.append("<h2>二、逐筆（同一批進場：A 實際買進的交易，每筆當獨立一筆）</h2><div class='sel'>策略 <select id='s2' onchange='sw()'>"
             + "".join(f"<option>{s}</option>" for s in STR) + "</select>期間 <select id='s3' onchange='sw()'>" + "".join(f"<option>{k}</option>" for k in SEGS) + "</select></div>")
    for s in STR:
        for sg in SEGS:
            H.append(f"<div class='pane' id='p2{s[:2]}_{sg}'><div class='wrap'><table><tr><th class='l'>出場</th><th>筆數</th><th>平均<br><small>扣成本</small></th><th>中位</th><th>勝率</th>"
                     "<th>賺的平均</th><th>賠的平均</th><th>平均持有<br><small>交易日</small></th><th>每持有一天</th><th>3 成／7 成<br><small>各自平均</small></th><th>對 A 差<br><small>平均／中位</small></th><th>比 A 好</th></tr>")
            for v in VARS:
                x = st(s, sg, v)
                H.append(f"<tr><td class='l'>{VNAME[v]}</td><td>{int(x['筆數']):,}</td><td>{B2(x['平均'])}</td><td>{B2(x['中位'])}</td><td>{P_(x['勝率'])}</td>"
                         f"<td>{P1(x['賺的平均'])}</td><td>{P1(x['賠的平均'])}</td><td>{D_(x['平均持有天數'])}</td><td>{B2(x['每天報酬'])}</td>"
                         f"<td>{P1(x['3成平均'])}／{P1(x['7成平均'])}</td><td>{'—' if v == 'A' else PT(x['對A差平均']) + '<br><small>' + PT(x['對A差中位']) + '</small>'}</td>"
                         f"<td>{'—' if v == 'A' else P_(x['比A好比例'])}</td></tr>")
            H.append("</table></div>")
            r = RS[(RS["策略"] == s) & (RS["段"] == sg)]
            if len(r):
                r = r.iloc[0]
                g = lambda k: r[k] if k in r and pd.notna(r[k]) else 0.0
                H.append(f"<p class='note'>流程在這批交易上：進場時本段<b>已經出現過 W1 {P_(g('買進前本段已有W1'))}</b>（⇒ 隔天就賣 3 成）；3 成的出場原因：W1 {P_(g('原因30｜W1'))}、"
                         f"連 40 天沒新高 {P_(g('原因30｜40天沒新高'))}、回落 30% {P_(g('原因30｜回落30%'))}、未完 {P_(g('原因30｜未完'))}；"
                         f"7 成：W2 {P_(g('原因70｜W2') + g('原因70｜W2（買進前）'))}、回落 30% {P_(g('原因70｜回落30%'))}、40 天沒新高 {P_(g('原因70｜40天沒新高'))}、未完 {P_(g('原因70｜未完'))}。"
                         f"B 持有天數中位 {D_(r['B 持有天數 中位'])}（p10～p90 {D_(r['B 持有天數 p10'])}～{D_(r['B 持有天數 p90'])}）；B 比正式早出 {P_(r['B 比正式短'])}，D 比正式晚出 {P_(r['D 比正式長'])}。</p>")
            H.append("</div>")
    H.append("<h2>名詞與做法</h2><ul class='note'>"
             "<li>A 正式：營量第 60 個交易日收盤賣（20 槽、依 relvol 挑）；營飆第 120 個交易日收盤賣（10 槽、抽籤）。</li>"
             "<li>B 流程：不設天數上限，照上面的流程賣完為止；資料最後一天（2026-09-24）還沒賣完的，以那天收盤計值。</li>"
             "<li>C：3 成、7 成各自取「流程出場」和「正式到期」比較早的那個。D：各自取比較晚的那個 —— 正式到期時流程還在抱的那部分繼續抱到流程出場，流程已經賣掉的那部分就在正式到期日賣。</li>"
             "<li>分批的做法：先賣的 3 成，錢留在同一個部位裡（價值停在賣價），要等剩下的也賣掉，名額才釋出給新訊號；成本一律每筆扣一次來回 0.585%。</li>"
             "<li>W1、W2、起漲點、40 天沒新高的定義與每日名單的買賣流程相同，只是起漲點在進場前一天就固定；不做中段底買回。</li>"
             "<li>逐筆的營飆是 200 顆種子的交易合併（同一筆出現幾次算幾次）；去重版本見 summary_per_trade.csv。</li></ul>")
    H.append("<script>function sw(){var a=document.getElementById('s1').value.slice(0,2),b=document.getElementById('s2').value.slice(0,2),c=document.getElementById('s3').value;"
             "document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p1'+a||x.id=='p2'+b+'_'+c))}sw()</script></main></body></html>")
    txt = "\n".join(H).replace("__CONCL__", conclusion(ST, SP))
    open(os.path.join(OUT, "營量營飆配飆股流程.html"), "w", encoding="utf-8").write(txt)
    log("[網頁] 完成")


def conclusion(ST, SP):
    """一句話（依數字自動組；措辭在看過數字後寫（2026-09-30 21:3x），⛔ 不改讀法）。"""
    P1 = lambda v: f"{v * 100:+.1f}%"
    sp = lambda s, v, sg="全部": SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["出場"] == v)].iloc[0]
    st = lambda s, v: ST[(ST["策略"] == s) & (ST["段"] == "全部") & (ST["出場"] == v) & (ST["口徑"] != "去重")].iloc[0]
    worse = all(sp(s, v, sg)["對A年化差 中位"] < 0 for s in STR for v in "BCD" for sg in SEGS)
    ya, yb, yc, yd = (sp("營量 v1", v) for v in VARS); fa, fb, fc, fd = (sp("營飆 v1", v) for v in VARS)
    ta, tb, td = st("營量 v1", "A"), st("營量 v1", "B"), st("營量 v1", "D")
    best_win = sp("營飆 v1", "D", "2024-2026.08")["年化贏A比例"]
    s = (f"<b>一句話：{'不能' if worse else '不一定'}。</b>組合層（真的照槽位下去買）三種流程出場"
         + ("在全部期間、兩個分期都比正式出場的年化低" if worse else "並非每段都比正式出場低") + "："
         f"營量 {P1(ya['年化 中位'])} → B {P1(yb['年化 中位'])}、C {P1(yc['年化 中位'])}、D {P1(yd['年化 中位'])}；"
         f"營飆 {P1(fa['年化 中位'])} → B {P1(fb['年化 中位'])}、C {P1(fc['年化 中位'])}、D {P1(fd['年化 中位'])}"
         f"（全部期間，200 顆種子沒有一顆贏；只有近期 D 有 {best_win * 100:.0f}% 的種子年化贏）。"
         f"<br>換到的是回落變淺（營量 B {P1(yb['回落 中位'])}、營飆 B {P1(fb['回落 中位'])}，正式 {P1(ya['回落 中位'])}／{P1(fa['回落 中位'])}），但年化掉得比回落多，不划算。"
         f"<br>為什麼：營量、營飆通常在漲了八九成才買，進場時四到五成的筆本段已出現過 W1 ⇒ 隔天就先賣 3 成；另外約 3 成在 W1 之前就因「連 40 天沒新高」整筆賣掉。"
         f"逐筆看，營量用流程（B）或延長贏家（D）平均每筆多賺 {(tb['平均'] - ta['平均']) * 100:.1f}／{(td['平均'] - ta['平均']) * 100:.1f} 點，"
         f"但抱得更久（{ta['平均持有天數']:.0f} → {tb['平均持有天數']:.0f}／{td['平均持有天數']:.0f} 天），每持有一天的報酬反而變低，組合層能買的筆數也變少"
         f"（{ya['買進筆 中位']:.0f} → {yb['買進筆 中位']:.0f}／{yd['買進筆 中位']:.0f} 筆）；營飆逐筆就已經變差（B 每筆少 {(st('營飆 v1', 'A')['平均'] - st('營飆 v1', 'B')['平均']) * 100:.0f} 點）。")
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()
