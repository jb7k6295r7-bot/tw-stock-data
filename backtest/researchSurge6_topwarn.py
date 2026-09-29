# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：第一頂、第二頂「當下可判」警示規則驗證（參考，⛔ 不計 N；看過前面結果之後才加）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_topwarn [--check]

═══ 讀法（寫死於 2026-09-29 22:43（台北），在算任何數字之前；規則由協調者轉達，⛔ 本線不改門檻、不在確認段挑最好的）═══
 R1 元件（d 收盤可判；還原收盤、K 棒序列）：
    創20日新高 ＝ c[d] ＞ 前 20 根 K 棒最高收盤｜近20日高10%內 ＝ c[d] ≥ 0.9 × 含 d 的 20 根最高收盤
    過去60日無處置 ＝ F 表 disp_60 ＝ 0（[d−59, d] 處置天數）｜注意 Q5 ＝ Q 表 att_5／att_10／att_20 ＝ 5｜
    急拉 ＝ Q 表 lu_5 ＝ 5 或 r_5 ＝ 5｜急拉變體 ＝ F 表 lu_20 ≥ 3
    處置起日、出關日（迄日下一個交易日）同 exitsig S7（main disposal）
 R2 W1 第一頂警示 ＝ 創20日新高 ∧ 無處置 ∧ 注意 Q5 ∧ 急拉；變體 ＝ 注意 {5, 10, 20} 日 × 急拉 {lu_5 或 r_5 Q5, lu_20 ≥ 3}（6 版，全部照報）
    無處置：一般版 ＝ 過去60日無處置；飆股版（只在 A）＝ 從 t 起累計進入處置 0 次（起日在 [t, d]）
 R3 W2 第二頂警示 ＝ 近20日高10%內 ∧（W2a 再次進入處置：d 是處置起日，且 [d−60, d−1] 另有起日｜W2b 處置出關：d 是出關日）；
    飆股版（只在 A）：W2a 另一起日在 [t, d−1]；W2b 那次處置起日 ≥ t
 R4 A 飆股事件（seq6、事件 ≥ 30 的 182 格；x＝20% 切段同 mid_desc）：窗 ＝ [t＋1, min(P＋5, 2026-08-31)] 內的訊號日；
    每個訊號日歸到最近的段頂（|d − 段頂| 最小；同距取 P、再取後面的 Hk）：±5 日內 ⇒ 「H1 附近」「H2 以後附近」「P 附近」，否則「都不在」；各格比例取格中位（該格訊號日 ≥ 30）
    第一次出現（窗內第一個訊號日）：有出現的事件比例、漲到全程幾成 (c[d]−c[t])÷(c[P]−c[t])、離最近段頂天數（d − 段頂，負 ＝ 在頂之前）；格中位（該格有出現事件 ≥ 30）
 ⭐ 協調者三次更正都在開算前收到（使用者：「2 不用算，你已經有起漲點訊號了」「起漲點訊號是我們剛剛整理的那個，不是做好的策略！」「中間底你剛剛也給我了吧？」）：
    ⛔ 原 B（全部股票訊號後表現）拿掉；⛔ 不用營量／營飆；改成 B' ＋ 完整一輪
 R5 B' 起漲點訊號進場（母體 ＝ 上市櫃普通股全部，⛔ 不限飆股事件）：訊號日 d（2021-01～2026-08，d＋1 ≤ 2026-08-31）收盤可判、d＋1 開盤進（seq5 buy_ok；買價 ＝ 還原開盤）
    進場版本：overlap 的 14 個起漲特徵（researchSurge6_overlap.FEATS）同時有 ≥ m 個，m ∈ {5, 6, 7, 8, 9}（每個都報，⛔ 不挑）；
    另加「第二段起漲型」＝（120日報酬 Q5 或 20日漲停 ≥ 3）∧（距5日低 Q1 或 距10日低 Q1）
    同一檔進場後到本筆結束之前不重複進場；探索／確認依進場日月份分段；全部逐筆合併計（非逐格）
    本筆結束與真頂 P*：從進場日起跟著創新高，第一次收盤 ≤ 當時最高 × 0.7 那天結束；P* ＝ [進場日, 結束日] 最高收盤（同 S7 P*）；到 2026-08-31 沒回落 30% ⇒「未完」
    分段：[進場日, P*] 收盤用 mid_desc M2／M2b（x＝20%，a ＞ 0）切出第一頂 H1、第二頂…；只有 1 段 ⇒ 第一頂 ＝ 真頂
    W1、W2（一般 60 日版）第一次出現於 [進場日, 結束日]：歸到最近的段頂（同 A，±5 日）；賣在次一有效開盤：吃到「進場→第一頂」「進場→真頂」的幾成、賣出日 − 第一頂、賣出日 − 真頂；
    之後到結束前又有收盤 ＞ [進場日, 訊號日] 最高收盤 ⇒「之後又創新高」；⛔ 不用固定持有天數對照；另描述第 60 日收盤 ÷ 真頂 − 1、真頂在第 60 日之後的比例
 R5b 完整一輪（B' 同一批進場；W1 用基本版「注意10日Q5×急拉lu5或r5」）：
    ① 第一次賣 ＝ W1 第一次出現、次一開盤；沒出現 ⇒ 沒有這一輪（照報比例）
    ② 買回：第一次賣之後、結束日之前，收盤「從進場以來最高收盤回落第一次達到 x%」的日子（跨過 x% 的那天，可能多次），x ∈ {10, 20, 30}；
       當天算 bottomjudge 當下版分數（K＝5 已選特徵、探索段 m*、五等分分界，⛔ 不重挑；拉回狀態以 H ＝ 進場以來最高收盤那天、L ＝ 當天、前段起點 ＝ 進場後最後一個已完成拉回低點（沒有 ＝ 進場日）、t ＝ 進場日）；
       第一個分數 ≥ m* 的日子 ⇒ 次一開盤買回；結束日先到 ⇒ 不買回（照報）。⚠ x＝30% 的回落門檻與結束規則幾乎相同，跨過那天通常就是結束日 ⇒ 幾乎不會買回（買回門檻含 1e−9 容差、結束規則沒有 ⇒ 約 0.2% 邊界個案）
    ③ 第二次賣 ＝ 買回後 W2（a 再次進入處置、b 處置出關 分開）第一次出現、次一開盤；結束日先到 ⇒ 結束日次一開盤（未完 ⇒ 2026-08-31 收盤計）
    報：各步觸發比例；第一段吃到第一頂 ＝ (賣1 − 買價) ÷ (c[H1] − 買價)；買回價比中段底高 ＝ 買回價 ÷ 中段底 − 1（中段底 ＝ 第一次賣到「買回後第一次收盤 ＞ 買回前最高」或結束日之間的最低收盤）；
       第二段吃到 ＝ (賣2 − 買回價) ÷ (c[P*] − 中段底)；全輪報酬 ＝ 賣1÷買價 × 賣2÷買回價 − 1（沒買回 ＝ 賣1÷買價 − 1）；全輪吃到真頂 ＝ 全輪報酬 ÷ (c[P*]÷買價 − 1)；
       買錯 ＝ 買回後到結束日都沒有收盤 ＞ 買回前最高；買錯虧損 ＝ 賣2 ÷ 買回價 − 1（買錯者）
 R6 C：各訊號在 A（事件窗內，(股, d) 去重）的訊號日數；B' 各版本的筆數
 R7 查核（--check）：抽 2 格，逐根重算 W1 基本版在事件窗內的訊號日數與四類比例；B' 抽「≥7 個」200 筆逐日重算結束日、P*、段數、W1 基本版第一次出現日與吃到真頂幾成（完整一輪不另查）
 R8（2026-09-29 22:52（台北）補；⚠ 已看過第一次結果）：查核抓到價格矩陣存成 float32，20% 切段與 30% 結束門檻有浮點誤差（1～2 筆不同）⇒ 改 float64 整份重跑，其他不變
輸出 backtest/resultsSurge6/topwarn/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5
from backtest import researchSurge6_end_desc as ED
from backtest import researchSurge6_mid_desc as MD
from backtest import researchSurge6_overlap as OV
from backtest import researchSurge6_bottomjudge as BJ
from backtest import researchSurge5_feat as FT

warnings.filterwarnings("ignore", category=RuntimeWarning)
D = S5.D
TIME = "2026-09-29 22:43（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/topwarn"
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_
EXP = (2021 * 12, 2023 * 12 + 11); CON = (2024 * 12, 2026 * 12 + 7)
W1V = [(a, s) for a in (10, 5, 20) for s in ("急拉lu5或r5", "20日漲停≥3")]
W1N = [f"W1 注意{a}日Q5×{s}" for a, s in W1V]
W2N = ["W2a 再次進入處置", "W2b 處置出關"]
GEN_SIG = W1N + W2N
MS = (5, 6, 7, 8, 9)
XB = (0.10, 0.20, 0.30)


def components(uni, cal, n, bar, t1, W, log):
    S = len(uni); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    C = np.full((S, n), np.nan, np.float64); O = np.full((S, n), np.nan, np.float64); HI20 = np.zeros((S, n), bool); NEAR = np.zeros((S, n), bool)
    OUTC = {k: np.full((S, n), np.nan, np.float32) for k in ("near_top", "dd20_20", "nh_20", "r_20", "dd20_60", "nh_60", "r_60")}
    D.DATA = S5.ST
    for s in range(S):
        st = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal)
        if st is None:
            continue
        c0 = st.df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(c0) & bar[s])
        c = pd.Series(c0).ffill().to_numpy(); C[s] = c; O[s] = st.df["open"].to_numpy(float)
        if len(idx) < 25:
            continue
        cb = c0[idx]; mx20 = pd.Series(cb).rolling(20, min_periods=20).max().to_numpy(); pmx = np.r_[np.nan, mx20[:-1]]
        HI20[s, idx] = cb > pmx; NEAR[s, idx] = cb >= 0.9 * mx20
        hi20c = np.full(n, np.nan); hi20c[idx] = mx20
        rv = pd.Series(c[::-1])
        fut = {h: (np.r_[rv.rolling(h, min_periods=h).max().to_numpy()[::-1][1:], np.nan], np.r_[rv.rolling(h, min_periods=h).min().to_numpy()[::-1][1:], np.nan]) for h in (20, 60)}
        ctr = pd.Series(c).rolling(11, min_periods=11, center=True).max().to_numpy()              # [d−5, d＋5]
        f15 = np.r_[pd.Series(c[::-1]).rolling(15, min_periods=15).max().to_numpy()[::-1][6:], np.full(6, np.nan)]   # (d＋5, d＋20]
        d_ = np.arange(n)
        nt = np.where(d_ + 20 <= t1, (f15 <= ctr).astype(float), np.nan)
        for h in (20, 60):
            mx, mn = fut[h]; ok = (d_ + h <= t1) & np.isfinite(mx)
            OUTC[f"dd20_{h}"][s] = np.where(ok, mn <= 0.8 * c, np.nan); OUTC[f"nh_{h}"][s] = np.where(ok & np.isfinite(hi20c), mx > hi20c, np.nan)
            OUTC[f"r_{h}"][s] = np.where(ok, np.r_[c[h:], np.full(h, np.nan)] / c - 1, np.nan)
        OUTC["near_top"][s] = nt
    log("[元件] 價量完成")
    nod60 = np.asarray(Fm[FX["disp_60"]]) == 0
    att = {a: np.asarray(Qm[FX[f"att_{a}"]]) == 5 for a in (5, 10, 20)}
    surge = (np.asarray(Qm[FX["lu_5"]]) == 5) | (np.asarray(Qm[FX["r_5"]]) == 5); lu20 = np.nan_to_num(np.asarray(Fm[FX["lu_20"]]), nan=0) >= 3
    START = np.zeros((S, n), bool); EXIT = np.zeros((S, n), bool); RE60 = np.zeros((S, n), bool)
    sid2i = {sd: i for i, sd in enumerate(uni["stock_id"])}; STARTS = {}
    for sd, iv in W["DISP"].items():
        if sd not in sid2i:
            continue
        s = sid2i[sd]; st_ = sorted(a for a, b in iv); STARTS[s] = np.array(st_)
        for a, b in iv:
            if 0 <= a < n:
                START[s, a] = True
                if any(0 < a - x <= 60 for x in st_ if x != a):
                    RE60[s, a] = True
            if 0 <= b + 1 < n:
                EXIT[s, b + 1] = True
    base1 = {v: HI20 & att[a] & (surge if sv == "急拉lu5或r5" else lu20) for v, (a, sv) in zip(W1N, W1V)}
    SIG = {v: base1[v] & nod60 & bar for v in W1N}
    SIG["W2a 再次進入處置"] = RE60 & NEAR & bar; SIG["W2b 處置出關"] = EXIT & NEAR & bar
    for v in SIG:
        SIG[v][:, t1 + 1:] = False
    return C, O, SIG, base1, START, EXIT, NEAR, STARTS, HI20, OUTC


def bj_scorer(x):
    """bottomjudge 當下版（K＝5）已選特徵與門檻 ⇒ (特徵名清單, m*, 分界)。"""
    sel = pd.read_csv("backtest/resultsSurge6/bottomjudge/part2_selected.csv"); meta = json.load(open("backtest/resultsSurge6/bottomjudge/meta.json", encoding="utf-8"))
    xs = f"{int(x * 100)}%"; names = sel[(sel["x"] == xs) & (sel["K"].astype(str) == "5")].sort_values("順位")["特徵"].tolist()
    return names, int(meta["當下可用版 m*"][f"{xs}_K5"]), {k: v for k, v in meta["五等分分界（探索段低點）"].items() if k.endswith(f"_x{int(x * 100)}")}


def bj_has(name, f, bounds, x, qv):
    """name：bottomjudge 級距名；f：pull_feats 原值 dict（單點）；qv：Q 表碼查詢函式 ⇒ 是否有。"""
    feat, lev = name.split("｜", 1)
    if feat in BJ.CONT:
        v = f[feat]
        if not np.isfinite(v):
            return False
        bd = bounds[f"{feat}_x{int(x * 100)}"]; code = int(lev.split("（")[0][1:])
        return int(np.searchsorted(bd, v, "right") + 1) == code
    if feat in BJ.BOOL:
        v = f[feat]
        return np.isfinite(v) and (v == 1) == (lev == "是")
    if feat in BJ.CNTF:
        return f[feat] == (3 if lev.startswith("3") else int(lev))
    return qv(name)


def entries_and_trades(uni, cal, n, bar, inseg, t1, C, O, SIG, mon, W, log):
    """B'：起漲點訊號進場 ⇒ 每個版本一張逐筆表（含完整一輪）。"""
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    buy_ok = np.load(os.path.join(WORK5, "buy_ok.npy")); disp = np.load(os.path.join(WORK5, "disp.npy")); tdcc = np.asarray(Fm[FX["tdcc_20"]])
    cntm = np.zeros(bar.shape, np.int8)
    for nm, col, code in OV.FEATS:
        cntm += (np.asarray(Qm[FX[col]]) == code)
    v2 = ((np.asarray(Qm[FX["r_120"]]) == 5) | (np.nan_to_num(np.asarray(Fm[FX["lu_20"]]), nan=0) >= 3)) & ((np.asarray(Qm[FX["dlo_5"]]) == 1) | (np.asarray(Qm[FX["dlo_10"]]) == 1))
    ENT = {f"起漲特徵 ≥{m} 個": cntm >= m for m in MS}
    ENT["第二段起漲型（之前已大漲＋短線拉回）"] = v2
    okday = inseg.copy(); okday[t1:] = False
    SPOS = {v: {s: np.flatnonzero(SIG[v][s]) for s in range(len(uni))} for v in GEN_SIG}
    BJS = {x: bj_scorer(x) for x in XB}
    LVN = {f"{l[4]}｜{l[3]}": l for l in FT.levels()}
    QC = {}
    def qv_of(s, d):
        def f(name):
            lv = LVN[name]
            if lv[0] not in QC:
                QC[lv[0]] = np.asarray(Qm[lv[0]])
            return QC[lv[0]][s, d] == lv[2]
        return f
    W1B = W1N[0]
    TR = {}
    for ename, EM in ENT.items():
        rows = []
        cand = EM & bar & okday[None, :]
        for s in range(len(uni)):
            ds = np.flatnonzero(cand[s])
            if not len(ds):
                continue
            c = C[s].astype(float); o = O[s].astype(float)
            okop = np.isfinite(o) & (o > 0) & bar[s]
            nxo = np.full(n + 2, n + 10, np.int64)
            for p in range(n - 1, -1, -1):
                nxo[p] = p if okop[p] else nxo[p + 1]
            X = None
            nxt_free = -1
            for d in ds:
                if d <= nxt_free or not buy_ok[s, d + 1]:
                    continue
                e = d + 1; bp = o[e]
                seg = c[e:t1 + 1]; rm = np.maximum.accumulate(seg); w = np.flatnonzero(seg <= rm * 0.7)
                stop = e + int(w[0]) if len(w) else t1; opn = int(len(w) == 0)
                Ps = e + int(np.argmax(c[e:stop + 1]))
                cs = c[e:Ps + 1]
                tops = [e + a for a, b, lo, hi in MD.pullbacks(cs) if a > 0 and lo <= hi * 0.8 * (1 + 1e-9)] if len(cs) > 2 else []
                tops = np.array(tops + [Ps])
                r = {"s": s, "d": d, "e": e, "bp": bp, "stop": stop, "P*": Ps, "未完": opn, "真頂漲幅": c[Ps] / bp - 1, "段數": len(tops), "H1": tops[0],
                     "第60日÷真頂": c[e + 60] / c[Ps] - 1 if e + 60 <= t1 else np.nan, "真頂在第60日之後": float(Ps > e + 60), "進場月": mon[e]}
                for v in GEN_SIG:
                    pos = SPOS[v][s]; j = np.searchsorted(pos, e)
                    if j < len(pos) and pos[j] <= stop:
                        d1 = int(pos[j]); ex = nxo[min(d1 + 1, n + 1)]
                        dist = np.abs(d1 - tops) - np.arange(len(tops)) * 1e-6; k = int(dist.argmin()); mn = abs(d1 - tops[k])
                        cls = 3 if mn > 5 else (2 if k == len(tops) - 1 else (0 if k == 0 else 1))
                        sp = o[ex] if ex <= t1 else np.nan
                        later = float((c[d1 + 1:stop + 1] > c[e:d1 + 1].max()).any()) if d1 < stop else 0.0
                        r.update({f"{v}|出現": 1, f"{v}|日": d1, f"{v}|類": cls, f"{v}|吃到第一頂": (sp - bp) / (c[tops[0]] - bp), f"{v}|吃到真頂": (sp - bp) / (c[Ps] - bp),
                                  f"{v}|賣出日−第一頂": ex - tops[0], f"{v}|賣出日−真頂": ex - Ps, f"{v}|之後又創新高": later})
                    else:
                        r[f"{v}|出現"] = 0
                # ── 完整一輪（W1 基本版賣 → 中段底買回 → W2 賣）
                if r[f"{W1B}|出現"] == 1:
                    d1 = r[f"{W1B}|日"]; ex1 = nxo[min(d1 + 1, n + 1)]; sp1 = o[ex1] if ex1 <= t1 else np.nan
                    for x in XB:
                        names, mstar, bnds = BJS[x]; key = f"輪x{int(x * 100)}"
                        r[f"{key}|第一段吃到第一頂"] = (sp1 - bp) / (c[tops[0]] - bp)
                        bought = False
                        if np.isfinite(sp1) and ex1 < stop:
                            rmx = np.maximum.accumulate(c[e:stop + 1]); thr = rmx * (1 - x) * (1 + 1e-9); below = c[e:stop + 1] <= thr
                            cross = np.flatnonzero(below[1:] & ~below[:-1]) + 1 + e
                            cross = cross[(cross > ex1) & (cross < stop)]
                            for d2 in cross:
                                if X is None:
                                    X = BJ.stock_ctx(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal, n, W, disp[s])
                                A = e + int(np.argmax(c[e:d2 + 1]))
                                cuts = [(e + a, e + b) for a, b, lo, hi in MD.pullbacks(c[e:A + 1]) if a > 0 and lo <= hi * (1 - x) * (1 + 1e-9)] if A - e > 2 else []
                                Lp = cuts[-1][1] if cuts else e
                                f = {k_: float(v_[0]) for k_, v_ in BJ.pull_feats(X, np.array([A]), np.array([d2]), np.array([Lp]), np.array([e]), np.array([len(cuts)]), np.array([tdcc[s, d2]])).items()}
                                sc = sum(bj_has(nm_, f, bnds, x, qv_of(s, d2)) for nm_ in names)
                                if sc >= mstar:
                                    eb = nxo[min(d2 + 1, n + 1)]
                                    if eb > stop or eb > t1:
                                        break
                                    pb = o[eb]; runhi = c[e:d2 + 1].max()
                                    nh = np.flatnonzero(c[eb:stop + 1] > runhi); endl = eb + int(nh[0]) if len(nh) else stop
                                    low = c[ex1:endl + 1].min()
                                    bought = True; break
                        r[f"{key}|買回"] = float(bought)
                        if not bought:
                            r[f"{key}|全輪報酬"] = sp1 / bp - 1
                            r[f"{key}|全輪吃到真頂"] = (sp1 / bp - 1) / (c[Ps] / bp - 1)
                            continue
                        r[f"{key}|買回價÷中段底"] = pb / low - 1
                        r[f"{key}|買錯"] = float(not len(nh))
                        for w2 in W2N:
                            pos = SPOS[w2][s]; j = np.searchsorted(pos, eb)
                            hit = j < len(pos) and pos[j] <= stop
                            ex2 = nxo[min((int(pos[j]) if hit else stop) + 1, n + 1)]
                            sp2 = o[ex2] if ex2 <= t1 else c[t1]
                            tag = f"{key}|{w2[:3]}"
                            r[f"{tag}|W2出現"] = float(hit)
                            r[f"{tag}|第二段吃到"] = (sp2 - pb) / (c[Ps] - low) if c[Ps] > low else np.nan
                            tot = (sp1 / bp) * (sp2 / pb) - 1
                            r[f"{tag}|全輪報酬"] = tot; r[f"{tag}|全輪吃到真頂"] = tot / (c[Ps] / bp - 1)
                            r[f"{tag}|買錯虧損"] = sp2 / pb - 1 if not len(nh) else np.nan
                rows.append(r); nxt_free = stop
        TR[ename] = pd.DataFrame(rows)
        log(f"[B'] {ename}：{len(rows):,} 筆")
    return TR


def summarize_trades(TR):
    CLS = ["第一頂附近", "第二頂以後附近", "真頂附近", "都不在"]
    POP = []; SUM = []; CYC = []
    for ename, T in TR.items():
        for sg, m in (("全部", np.ones(len(T), bool)), ("探索", (T["進場月"] >= EXP[0]) & (T["進場月"] <= EXP[1])), ("確認", T["進場月"] >= CON[0])):
            t = T[m]
            if not len(t):
                continue
            g = t["真頂漲幅"]
            POP.append({"進場": ename, "段": sg, "筆數": len(t), "未完比例": t["未完"].mean(), "真頂漲幅 中位": g.median(), "p25": g.quantile(.25), "p75": g.quantile(.75), "p90": g.quantile(.9),
                        "漲不到20%": (g < 0.2).mean(), "漲 ≥100%": (g >= 1).mean(), **{f"{k}段": (t["段數"] == k).mean() for k in (1, 2, 3)}, "4段以上": (t["段數"] >= 4).mean(),
                        "第60日÷真頂 中位": t["第60日÷真頂"].median(), "真頂在第60日之後": t["真頂在第60日之後"].mean()})
            for v in GEN_SIG:
                ap = t[f"{v}|出現"] == 1; tt = t[ap]
                r = {"進場": ename, "段": sg, "訊號": v, "筆數": len(t), "有出現": ap.mean()}
                for j, cn in enumerate(CLS):
                    r[cn] = (tt[f"{v}|類"] == j).mean() if len(tt) else np.nan
                for k_ in ("吃到第一頂", "吃到真頂", "賣出日−第一頂", "賣出日−真頂"):
                    r[k_ + " 中位"] = tt[f"{v}|{k_}"].median() if len(tt) else np.nan
                r["之後又創新高"] = tt[f"{v}|之後又創新高"].mean() if len(tt) else np.nan
                SUM.append(r)
            w1 = t[t[f"{W1N[0]}|出現"] == 1]
            for x in XB:
                key = f"輪x{int(x * 100)}"
                if f"{key}|買回" not in t.columns:
                    continue
                bb = w1[w1[f"{key}|買回"] == 1]
                for w2 in W2N:
                    tag = f"{key}|{w2[:3]}"
                    tot = w1[f"{key}|全輪吃到真頂"].copy() if f"{key}|全輪吃到真頂" in w1 else pd.Series(np.nan, index=w1.index)
                    if f"{tag}|全輪吃到真頂" in w1:
                        tot = tot.where(w1[f"{key}|買回"] != 1, w1[f"{tag}|全輪吃到真頂"])
                    CYC.append({"進場": ename, "段": sg, "x": f"{int(x * 100)}%", "第二次賣": w2, "筆數": len(t), "W1 出現（第一次賣）": len(w1) / len(t),
                                "買回（占第一次賣）": w1[f"{key}|買回"].mean() if len(w1) else np.nan,
                                "W2 出現（占買回）": bb[f"{tag}|W2出現"].mean() if len(bb) and f"{tag}|W2出現" in bb else np.nan,
                                "第一段吃到第一頂 中位": w1[f"{key}|第一段吃到第一頂"].median() if len(w1) else np.nan,
                                "買回價比中段底高 中位": bb[f"{key}|買回價÷中段底"].median() if len(bb) else np.nan,
                                "第二段吃到（中段底→真頂）中位": bb[f"{tag}|第二段吃到"].median() if len(bb) and f"{tag}|第二段吃到" in bb else np.nan,
                                "全輪吃到真頂 中位": tot.median() if len(tot) else np.nan,
                                "買錯（買回後沒再創新高）": bb[f"{key}|買錯"].mean() if len(bb) else np.nan,
                                "買錯虧損 中位": bb[f"{tag}|買錯虧損"].median() if len(bb) and f"{tag}|買錯虧損" in bb else np.nan})
    return pd.DataFrame(POP), pd.DataFrame(SUM), pd.DataFrame(CYC)


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    W, _ = S5.world(log)
    C, O, SIG, base1, START, EXIT, NEAR, STARTS, HI20, OUTC = components(uni, cal, n, bar, t1, W, log)
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    ANAMES = [f"{v}（60日無處置）" for v in W1N] + [f"{v}（從t起處置0）" for v in W1N] + [f"{v}（60日版）" for v in W2N] + [f"{v}（從t起版）" for v in W2N]
    CLS = ["H1 附近", "H2 以後附近", "P 附近", "都不在"]
    acc = {a: np.zeros((250, 4)) for a in ANAMES}; first = {a: [] for a in ANAMES}; seen = {a: set() for a in ANAMES}
    for s in np.unique(es):
        c = C[s].astype(float); st_ = STARTS.get(s, np.zeros(0, int)); memo = {}
        for i in np.flatnonzero(es == s):
            t, P = ed[i], Pv[i]; e = min(P + 5, t1)
            if e <= t:
                continue
            if (t, P) not in memo:
                cuts = [t + a for a, b, lo, hi in MD.pullbacks(c[t:P + 1]) if a > 0 and lo <= hi * 0.8 * (1 + 1e-9)]
                memo[(t, P)] = np.array(cuts + [P])
            tops = memo[(t, P)]; ds = np.arange(t + 1, e + 1)
            cum = np.searchsorted(st_, ds, "right") - np.searchsorted(st_, t, "left")                   # [t, d] 起日數
            prv = np.searchsorted(st_, ds, "left") - np.searchsorted(st_, t, "left")                    # [t, d−1]
            sigs = {}
            for v in W1N:
                sigs[f"{v}（60日無處置）"] = SIG[v][s, ds]; sigs[f"{v}（從t起處置0）"] = base1[v][s, ds] & (cum == 0) & bar[s, ds]
            sigs["W2a 再次進入處置（60日版）"] = SIG["W2a 再次進入處置"][s, ds]; sigs["W2b 處置出關（60日版）"] = SIG["W2b 處置出關"][s, ds]
            sigs["W2a 再次進入處置（從t起版）"] = START[s, ds] & (prv >= 1) & NEAR[s, ds] & bar[s, ds]
            sigs["W2b 處置出關（從t起版）"] = EXIT[s, ds] & (prv >= 1) & NEAR[s, ds] & bar[s, ds]
            dist = np.abs(ds[:, None] - tops[None, :]); order = np.lexsort((-np.arange(len(tops))[None, :].repeat(len(ds), 0), dist), axis=1) if False else None
            # 最近段頂：距離最小，同距取 P（最後一個）、再取後面的
            dd = dist.astype(float) - np.arange(len(tops))[None, :] * 1e-6; k = dd.argmin(1); near = dist[np.arange(len(ds)), k] <= 5
            cls = np.where(~near, 3, np.where(k == len(tops) - 1, 2, np.where(k == 0, 0, 1)))
            for a, m in sigs.items():
                if not m.any():
                    continue
                acc[a][ec[i]] += np.bincount(cls[m], minlength=4)
                seen[a].update(zip([s] * int(m.sum()), ds[m].tolist()))
                j = int(np.flatnonzero(m)[0]); d0 = ds[j]
                first[a].append((ec[i], 1, (c[d0] - c[t]) / (c[P] - c[t]), d0 - tops[k[j]]))
            for a in sigs:
                if not sigs[a].any():
                    first[a].append((ec[i], 0, np.nan, np.nan))
    log(f"[A] 逐事件完成 {time.time() - T0:.0f}s")
    AR = []
    for a in ANAMES:
        m = acc[a][cells]; ok = m.sum(1) >= 30; sh = m[ok] / m[ok].sum(1, keepdims=True)
        F = np.array(first[a], float); r = {"訊號": a, "可用格（訊號日≥30）": int(ok.sum()), "A 訊號日數（(股,d) 去重）": len(seen[a])}
        for j, cn in enumerate(CLS):
            r[cn] = q3(sh[:, j])[0] if ok.any() else np.nan
        per = {c: F[F[:, 0] == c] for c in cells}
        r["有出現的事件比例"] = q3([v[:, 1].mean() for v in per.values() if len(v)])[0]
        g = [v[v[:, 1] == 1] for v in per.values()]; g = [v for v in g if len(v) >= 30]
        r["第一次出現可用格"] = len(g)
        r["第一次：漲到全程幾成"] = q3([np.median(v[:, 2]) for v in g])[0] if g else np.nan
        r["第一次：離最近段頂天數"] = q3([np.median(v[:, 3]) for v in g])[0] if g else np.nan
        AR.append(r)
    AR = pd.DataFrame(AR); AR.to_csv(os.path.join(OUT, "A_events.csv"), index=False, float_format="%.5g")
    # B'
    TR = entries_and_trades(uni, cal, n, bar, inseg, t1, C, O, SIG, mon, W, log)
    POP, BS, CYC = summarize_trades(TR)
    POP.to_csv(os.path.join(OUT, "Bp_population.csv"), index=False, float_format="%.5g"); BS.to_csv(os.path.join(OUT, "Bp_signals.csv"), index=False, float_format="%.5g")
    CYC.to_csv(os.path.join(OUT, "Bp_full_cycle.csv"), index=False, float_format="%.5g")
    TR["起漲特徵 ≥7 個"].to_csv(os.path.join(OUT, "check_Bp_m7.csv.gz"), index=False, float_format="%.8g")
    # 查核長表
    CL = []
    a0 = "W1 注意10日Q5×急拉lu5或r5（60日無處置）"
    for c in cells:
        m = acc[a0][c]; CL.append({"格": S5.cell_name(c), "項": "W1基本 訊號日數", "值": float(m.sum())})
        for j, cn in enumerate(CLS):
            CL.append({"格": S5.cell_name(c), "項": f"W1基本 {cn}", "值": float(m[j] / m.sum()) if m.sum() else np.nan})
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    page(META, AR, POP, BS, CYC)
    log(f"[完] {time.time() - T0:.0f}s")


def page(META, AR, POP, BS, CYC):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}.ok{border-left:4px solid #2b6cb0;padding:6px 10px;background:#eef4fb}"
            ".sel{position:sticky;top:0;background:#fff;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}")
    N0 = lambda v: "—" if not np.isfinite(v) else f"{v:+.0f}"
    w1 = W1N[0]; a = AR.set_index("訊號"); r = a.loc[f"{w1}（60日無處置）"]
    ENTS = list(POP["進場"].unique())
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>第一頂第二頂警示驗證</title>", f"<style>{CSS}</style></head><body><main>", "<h1>用起漲訊號買進後，當下能不能說出「第一頂」「第二頂」在哪？（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 只當參考，沒有計入檢定數；規則照原樣驗，不挑最好的版本。段頂、真頂都是事後才知道的，只用來對答案；進場、警示、買回的每一步都是當天收盤就能判斷的。沒有用任何「抱固定天數」當對照。</p>",
         f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。進場 ＝ 起漲特徵（14 個）同時有 ≥ m 個，隔天開盤買；全部上市櫃股票都算（當下不知道會不會變飆股）。一筆的結束 ＝ 從最高點回落 30%；第一頂、第二頂用拉回 20% 切。</p>"]
    pc = POP[POP["段"] == "確認"].set_index("進場"); bc = BS[BS["段"] == "確認"]; cc = CYC[CYC["段"] == "確認"]
    e7 = "起漲特徵 ≥7 個"
    H.append("<h2>先講結論（確認段 2024–2026-08，以 ≥7 個為例；其他用下方選單）</h2><ul>")
    if e7 in pc.index:
        p = pc.loc[e7]
        H.append(f"<li><b>買進之後</b>：共 {int(p['筆數']):,} 筆；真頂漲幅中位 {P_(p['真頂漲幅 中位'])}，{P_(p['漲不到20%'])} 的筆漲不到 20%，{P_(p['漲 ≥100%'])} 漲到一倍以上；只有 1 段 {P_(p['1段'])}、2 段 {P_(p['2段'])}、3 段以上 {P_(p['3段'] + p['4段以上'])}。</li>")
        x = bc[(bc["進場"] == e7) & (bc["訊號"] == w1)]
        if len(x):
            x = x.iloc[0]
            H.append(f"<li><b>第一頂警示 W1</b>：{P_(x['有出現'])} 的筆會出現；出現時落在第一頂附近 {P_(x['第一頂附近'])}、第二頂以後附近 {P_(x['第二頂以後附近'])}、真頂附近 {P_(x['真頂附近'])}、都不在 {P_(x['都不在'])}（誤報）。"
                     f"賣在第一次出現，吃到進場→第一頂的 {P_(x['吃到第一頂 中位'])}、進場→真頂的 {P_(x['吃到真頂 中位'])}；之後又創新高 {P_(x['之後又創新高'])}。</li>")
        for w2 in W2N:
            x = bc[(bc["進場"] == e7) & (bc["訊號"] == w2)]
            if len(x):
                x = x.iloc[0]
                H.append(f"<li><b>{html.escape(w2)}</b>：出現 {P_(x['有出現'])}；落在真頂附近 {P_(x['真頂附近'])}、第二頂以後 {P_(x['第二頂以後附近'])}、都不在 {P_(x['都不在'])}；吃到真頂 {P_(x['吃到真頂 中位'])}。</li>")
        y = cc[(cc["進場"] == e7) & (cc["x"] == "20%") & (cc["第二次賣"] == W2N[1])]
        if len(y):
            y = y.iloc[0]
            H.append(f"<li class='ok'><b>完整一輪（拉回 20% 買回、出關賣）</b>：W1 賣出後有 {P_(y['買回（占第一次賣）'])} 買回，買回價比實際中段底高 {P_(y['買回價比中段底高 中位'])}，買錯（買回後沒再創新高）{P_(y['買錯（買回後沒再創新高）'])}；"
                     f"全輪吃到進場→真頂漲幅的 {P_(y['全輪吃到真頂 中位'])}（中位）。</li>")
    r2 = a.loc[f"{w1}（60日無處置）"]
    H.append(f"<li><b>飆股事件上（事後已知是飆股）</b>：W1 落在 H1 附近 {P_(r2['H1 附近'])}、H2 以後 {P_(r2['H2 以後附近'])}、真頂 {P_(r2['P 附近'])}、都不在 {P_(r2['都不在'])}。</li>")
    H.append("<li><b>誠實的回答</b>：看下面各表的「都不在」與「之後又創新高」——這兩個數字就是誤報率；它們若很高，就代表警示只能說「可能接近某個頂」，不能說「這就是第一頂／第二頂」。</li></ul>")
    H.append("<div class='sel'>進場版本<select id='se' onchange='sw()'>" + "".join(f"<option value='{i}'>{html.escape(e)}</option>" for i, e in enumerate(ENTS)) + "</select>段<select id='ss' onchange='sw()'><option>確認</option><option>探索</option><option>全部</option></select></div>")
    for i, en in enumerate(ENTS):
        for sg in ("確認", "探索", "全部"):
            H.append(f"<div class='pane' id='p{i}_{sg}'>")
            p = POP[(POP["進場"] == en) & (POP["段"] == sg)]
            if len(p):
                p = p.iloc[0]
                H.append(f"<h2>一、買進之後（{p['筆數']:,.0f} 筆；未完 {P_(p['未完比例'])}）</h2><p>真頂漲幅中位 {P_(p['真頂漲幅 中位'])}（p25～p75 {P_(p['p25'])}～{P_(p['p75'])}、p90 {P_(p['p90'])}）；"
                         f"漲不到 20% {P_(p['漲不到20%'])}；段數 1／2／3／4+：{P_(p['1段'])}／{P_(p['2段'])}／{P_(p['3段'])}／{P_(p['4段以上'])}；"
                         f"描述：第 60 日收盤比真頂 {P_(p['第60日÷真頂 中位'])}、真頂在第 60 日之後 {P_(p['真頂在第60日之後'])}。</p>")
            b = BS[(BS["進場"] == en) & (BS["段"] == sg)]
            H.append("<h2>二、警示第一次出現在哪、賣在那天吃到幾成</h2><div class='wrap'><table><tr><th class='l'>警示</th><th>有出現</th><th>第一頂附近</th><th>第二頂以後</th><th>真頂附近</th><th>都不在</th><th>吃到第一頂</th><th>吃到真頂</th><th>賣出−真頂</th><th>之後又創新高</th></tr>")
            for x in b.to_dict("records"):
                H.append(f"<tr><td class='l'>{html.escape(x['訊號'])}</td><td>{P_(x['有出現'])}</td><td>{P_(x['第一頂附近'])}</td><td>{P_(x['第二頂以後附近'])}</td><td>{P_(x['真頂附近'])}</td><td>{P_(x['都不在'])}</td>"
                         f"<td>{P_(x['吃到第一頂 中位'])}</td><td>{P_(x['吃到真頂 中位'])}</td><td>{N0(x['賣出日−真頂 中位'])} 天</td><td>{P_(x['之後又創新高'])}</td></tr>")
            H.append("</table></div>")
            y = CYC[(CYC["進場"] == en) & (CYC["段"] == sg)]
            H.append("<h2>三、完整一輪：起漲買 → 第一頂賣（W1）→ 中段底買回 → 第二頂賣（W2）</h2><div class='wrap'><table><tr><th>買回 x</th><th class='l'>第二次賣</th><th>W1 賣</th><th>買回</th><th>W2 出現</th><th>第一段吃到第一頂</th><th>買回比中段底高</th><th>第二段吃到</th><th>全輪吃到真頂</th><th>買錯（虧損）</th></tr>")
            for x in y.to_dict("records"):
                H.append(f"<tr><td>{x['x']}</td><td class='l'>{html.escape(x['第二次賣'])}</td><td>{P_(x['W1 出現（第一次賣）'])}</td><td>{P_(x['買回（占第一次賣）'])}</td><td>{P_(x['W2 出現（占買回）'])}</td>"
                         f"<td>{P_(x['第一段吃到第一頂 中位'])}</td><td>{P_(x['買回價比中段底高 中位'])}</td><td>{P_(x['第二段吃到（中段底→真頂）中位'])}</td><td>{P_(x['全輪吃到真頂 中位'])}</td>"
                         f"<td>{P_(x['買錯（買回後沒再創新高）'])}<br><small>{P_(x['買錯虧損 中位'])}</small></td></tr>")
            H.append("</table></div><p class='note'>x＝30% 的買回門檻和「一筆結束（回落 30%）」幾乎相同，跨過那天通常就結束，所以幾乎不會買回（約 0.2% 是買回門檻含 1e−9 容差造成的邊界個案）。</p></div>")
    H.append("<h2>附：飆股事件上（事後已知是飆股；拉回 20% 切段）訊號日落在哪</h2><div class='wrap'><table><tr><th class='l'>訊號</th><th>H1 附近</th><th>H2 以後</th><th>真頂附近</th><th>都不在</th><th>第一次：漲到幾成</th><th>離最近段頂</th></tr>")
    for x in AR.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(x['訊號'])}<br><small>{x['A 訊號日數（(股,d) 去重）']:,} 天</small></td><td>{P_(x['H1 附近'])}</td><td>{P_(x['H2 以後附近'])}</td><td>{P_(x['P 附近'])}</td><td>{P_(x['都不在'])}</td>"
                 f"<td>{P_(x['第一次：漲到全程幾成'])}</td><td>{N0(x['第一次：離最近段頂天數'])} 天</td></tr>")
    H.append("</table></div>")
    H.append("<script>function sw(){var e=document.getElementById('se').value,s=document.getElementById('ss').value;document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p'+e+'_'+s))}"
             f"document.getElementById('se').value='{ENTS.index('起漲特徵 ≥7 個') if '起漲特徵 ≥7 個' in ENTS else 0}';sw()</script></main></body></html>")
    open(os.path.join(OUT, "第一頂第二頂警示驗證.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz"))
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    att = np.asarray(Qm[FX["att_10"]]); lu5 = np.asarray(Qm[FX["lu_5"]]); r5 = np.asarray(Qm[FX["r_5"]]); d60 = np.asarray(Fm[FX["disp_60"]])
    D.DATA = S5.ST; CF = {}; errs = []; info = {}
    def cf(s):
        if s not in CF:
            df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
            c0 = df["close"].to_numpy(float); b = np.flatnonzero(np.isfinite(c0) & bar[s]); hi = np.zeros(n, bool)
            for j in range(20, len(b)):
                hi[b[j]] = c0[b[j]] > c0[b[j - 20:j]].max()
            CF[s] = (df["close"].ffill().to_numpy(float), hi)
        return CF[s]
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False)
    for c in pick:
        nm = S5.cell_name(c); k = np.flatnonzero(E["cell"] == c); cnt4 = np.zeros(4)
        for i in k:
            s, t, P = int(E["s"][i]), int(E["d"][i]), int(E["P"][i]); cc, hi = cf(s); e = min(P + 5, t1)
            pk, pkd, tv = cc[t], t, np.inf; tops = []
            for d in range(t + 1, P + 1):
                if cc[d] > pk:
                    if pkd > t and tv <= pk * 0.8 * (1 + 1e-9):
                        tops.append(pkd)
                    pk, pkd, tv = cc[d], d, np.inf
                elif cc[d] < tv:
                    tv = cc[d]
            tops.append(P)
            for d in range(t + 1, e + 1):
                if hi[d] and att[s, d] == 5 and (lu5[s, d] == 5 or r5[s, d] == 5) and d60[s, d] == 0 and bar[s, d]:
                    dist = [abs(d - x) for x in tops]; mn = min(dist); kk = max(j for j, x in enumerate(dist) if x == mn)
                    cnt4[3 if mn > 5 else (2 if kk == len(tops) - 1 else (0 if kk == 0 else 1))] += 1
        ref = CL[CL["格"] == nm].set_index("項")["值"]
        got = {"W1基本 訊號日數": cnt4.sum(), **{f"W1基本 {cn}": cnt4[j] / cnt4.sum() if cnt4.sum() else np.nan for j, cn in enumerate(["H1 附近", "H2 以後附近", "P 附近", "都不在"])}}
        for kk, v in got.items():
            if not np.isclose(v, ref[kk], rtol=1e-6, equal_nan=True):
                errs.append(f"{nm} {kk}：{v} 檔 {ref[kk]}")
        info[nm] = got
    OP = {}
    TB = pd.read_csv(os.path.join(OUT, "check_Bp_m7.csv.gz")).sample(200, random_state=1); nb = 0
    w1d = {}
    for r in TB.itertuples():
        s, e = int(r.s), int(r.e); cc, hi = cf(s); rm = -np.inf; stop = t1
        for d in range(e, t1 + 1):
            rm = max(rm, cc[d])
            if cc[d] <= rm * 0.7:
                stop = d; break
        Ps = e + int(np.argmax(cc[e:stop + 1]))
        pk, pkd, tv, nseg = cc[e], e, np.inf, 1
        for d in range(e + 1, Ps + 1):
            if cc[d] > pk:
                if pkd > e and tv <= pk * 0.8 * (1 + 1e-9):
                    nseg += 1
                pk, pkd, tv = cc[d], d, np.inf
            elif cc[d] < tv:
                tv = cc[d]
        d1 = next((d for d in range(e, stop + 1) if hi[d] and att[s, d] == 5 and (lu5[s, d] == 5 or r5[s, d] == 5) and d60[s, d] == 0 and bar[s, d]), None)
        ok = stop == int(r.stop) and Ps == int(TB.loc[r.Index, "P*"]) and nseg == int(r.段數)
        col = f"{W1N[0]}|日"
        ref_d1 = TB.loc[r.Index, col] if col in TB.columns else np.nan
        ok &= (d1 is None and not np.isfinite(ref_d1)) or (d1 is not None and np.isfinite(ref_d1) and d1 == int(ref_d1))
        if ok and d1 is not None:
            if s not in OP:
                OP[s] = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["open"].to_numpy(float)
            o = OP[s]; ex = d1 + 1
            while ex <= t1 and not (np.isfinite(o[ex]) and o[ex] > 0 and bar[s, ex]):
                ex += 1
            if ex <= t1:
                cap = (o[ex] - r.bp) / (cc[Ps] - r.bp); ok &= bool(np.isclose(cap, TB.loc[r.Index, f"{W1N[0]}|吃到真頂"], rtol=1e-5, atol=1e-7))
        nb += int(not ok)
    info["B' 抽 200 筆不同"] = nb
    if nb:
        errs.append(f"B' 不同 {nb}")
    out = {"抽格": list(info), "比對": info, "錯誤數": len(errs), "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 錯誤 {len(errs)}｜{errs[:4]}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
