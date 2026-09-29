# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：「第一頂警示 W1 能不能更靠近頂部」改良候選（參考，⛔ 不計 N；看過 topwarn 結果之後才加）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_w1better [--check | --page]

═══ 讀法（寫死於 2026-09-30 00:02（台北），在算任何數字之前；規則由協調者轉達，⛔ 不在確認段挑）═══
 G1 進場母體 B'（同 researchSurge6_topwarn R5，⛔ 不改）：14 個起漲特徵（researchSurge6_overlap.FEATS）同時 ≥ m 個，m ∈ {5, 7, 10}；
    訊號日 d（2021-01～2026-08，d＋1 ≤ 2026-08-31）收盤可判、d＋1 開盤進（seq5 buy_ok；買價 bp ＝ 還原開盤）；同一檔到本筆結束前不重複進場
    一筆結束 stop ＝ 從進場日起第一次收盤 ≤ 當時最高收盤 × 0.7；真頂 P* ＝ [e, stop] 最高收盤；到 2026-08-31 沒回落 30% ⇒「未完」（stop ＝ 2026-08-31）
    切段：[e, P*] 收盤用 mid_desc.pullbacks，拉回 ≥ 20%（lo ≤ hi × 0.8 ×(1＋1e−9)）的新高日 ＝ 段頂 H1, H2, …，最後一個段頂 ＝ P*；只有 1 段 ⇒ 第一頂 ＝ 真頂
    段底：Hk 與 Hk＋1 之間 ＝ 那次拉回的最低收盤日（pullbacks 的 trough）；P* 之後 ＝ stop（未完 ⇒ 沒有最後段底）
 G2 W1 基本版（對照基準，同 topwarn）＝ 創 20 日新高 ∧ 10 日注意 Q5 ∧（5 日漲停 Q5 或 5 日報酬 Q5）∧ 過去 60 日無處置；[e, stop] 內第一次出現日 d1
 G3 所有規則：訊號日 ds 收盤可判 ⇒ 賣在 ds 之後第一個有效開盤 ex（還原開盤 sp）；ds 必須在 [e, stop] 內，否則 ＝ 本規則沒觸發（該筆不賣，照 30% 結束走）
    元件（還原 OHLC，K 棒序列 ＝ 有收盤且 bar 的日子）：
      MA5／MA10 ＝ 含當根的 5／10 根收盤平均；「跌破 MAk」＝ 當根收盤 ＜ MAk 且前一根收盤 ≥ 前一根 MAk（向下穿越）
      收黑破前低 ＝ 收盤 ＜ 開盤 且 收盤 ＜ 前一根最低
      爆量長黑 ＝ 收盤 ＜ 開盤 ∧ ar_20（當日額 ÷ 前 20 日均額，Q 表）≥ q ∧ 黑 K 實體 ≥ q；
          黑 K 實體 ＝ (開 − 收) ÷ 前一根收盤，當日有 K 棒的全部股票橫斷面五等分（同 S10 qtie，同值同組；白 K 為負值一併排序）；q ∈ {Q5, Q4 以上}
      回落 y% ＝ 收盤 ≤ 參考最高收盤 × (1 − y)，y ∈ {5, 8, 10, 12, 15}%（無容差，同結束規則）
    C1 W1 後等轉弱：ds ＝ (d1, stop] 內第一個轉弱日；轉弱日 ∈ {收黑破前低, 跌破 MA5, 跌破 MA10, 從 [d1, d] 最高收盤回落 y%, 爆量長黑（q＝Q5／Q4 以上）} 共 10 版
    C2 W1 後移動停利：ds ＝ (d1, stop] 內第一個「收盤 ≤ [e, d] 最高收盤 × (1 − y)」的日子；5 版
    C3 W1 疊加：ds ＝ [e, stop] 內第一個「W1 ∧ 疊加」的日子；疊加 ∈ {K＞80 連續天數（kdrun，Q 表）Q5／Q4 以上、布林上軌（bbup）Q5／Q4 以上、5 日漲停天數（F 表 lu_5 原值）≥2／≥3}；6 版
    C4 只看轉弱、不看 W1（對照）：ds ＝ [e, stop] 內第一個「收盤 ≤ [e, d] 最高收盤 × (1 − y)」；或第一個「跌破 MA10」；6 版
    ⛔ 不用固定持有天數當對照；未觸發的筆不補賣（只報觸發比例）
 G4 每筆、每規則（觸發者）：
    位置 ＝ 賣出日 ex 歸到最近的段頂（|ex − 段頂| 最小；同距取後面的），±5 日內 ⇒ 第一頂附近（k＝0 且不是最後一段）／第二頂以後附近（0＜k＜最後）／真頂附近（k＝最後），否則「都不在」
      ⚠ 與 topwarn 的差別：topwarn 用訊號日歸類；本檔依任務用賣出日。W1 基本版另報「訊號日歸類」一列供對帳 topwarn
    吃到第一頂 ＝ (sp − bp) ÷ (c[H1] − bp)｜吃到真頂 ＝ (sp − bp) ÷ (c[P*] − bp)｜賣價 ÷ 第一頂收盤 − 1
    中位 ＝ 全部觸發筆；平均 ＝ 只算分母 ≥ 5% × bp 的筆（分母近 0 會把平均拉爆），剔除比例照報
    賣出日 − H1、賣出日 − P*（交易日；負 ＝ 在頂之前）中位與平均
    賣後又創新高 ＝ (ds, stop] 內有收盤 ＞ [e, ds] 最高收盤
    賣後到下一個段底 ＝ c[第一個 index ≥ ex 的段底] ÷ sp − 1（負 ＝ 賣後又跌這麼多 ＝ 躲過；正 ＝ 賣在段底之下）；沒有下一個段底（未完且已過 P* 之後）⇒ 不計
    同筆配對（對 W1 基本版，兩者都觸發的筆）：吃到第一頂差（規則 − 基本版）的中位與平均、規則賣價較高的比例、賣出日差中位
 G5 分段：依進場日月份，探索 2021-01～2023-12、確認 2024-01～2026-08；全部逐筆合併計
    排名：探索段、每個 m 各排兩次 ——（a）吃到第一頂中位、（b）賣在任一段頂 ±5 的比例（＝ 1 − 都不在）；兩個排名的前 5 名（聯集）＋ W1 基本版到確認段照報，⛔ 不依確認段重排或挑
    ⚠ 觸發比例不同 ⇒ 各規則的觸發筆是不同子集；「是否更靠近」以同筆配對為主讀
    同筆配對的吃到第一頂平均差，另附確認段依進場月分群的 bootstrap 95% 區間（2000 次，種子 20260930；只當描述）
 G6 查核（--check）：m＝7 抽 200 筆，逐日迴圈重算 stop、P*、H1、W1 基本版 d1、以及 4 個規則（C1 收黑破前低、C1 跌破 MA10、C2 y＝10%、C4 y＝10%）的訊號日與吃到第一頂；0 不同才算過；
    另對帳 topwarn：m＝5、7 的筆數與 W1 基本版（訊號日歸類）的確認段數字應與 topwarn/Bp_signals.csv 相同
 G7 網頁先講結論：有沒有比 W1 基本版更靠近第一頂的版本、靠近多少、代價（觸發少、吃到真頂少、又創新高多等）
 G8（2026-09-30 00:13（台北）補；⚠ 已跑過第一次、看過查核與筆數對帳，⛔ 還沒看任何規則的彙總數字）：查核抓到 1 筆「收盤剛好等於 MA10」
    （6510，還原價小數相同），兩種加總法的浮點誤差讓「收盤 ＜ MA」一邊成立、一邊不成立 ⇒ 「跌破 MAk」改為 收盤 ＜ MAk ×(1 − 1e−9) 且前一根沒有如此（相等不算跌破）；
    主程式與查核同一寫法，其他不變，整份重跑
 G9（2026-09-30 00:18（台北）補；⚠ 已看過彙總數字）：只用「觸發筆」與「兩者都觸發的配對」會漏掉代價 ——
    C3 疊加要等 W1 再出現一次，沒等到（股價先掉下去）的筆就從比較中消失，對 C3 有利。
    ⇒ 另報「固定分母」描述（⛔ 不參與 G5 排名、不改任何既有欄）：分母 ＝ W1 基本版有出現的筆；規則沒觸發 ⇒ 照 30% 結束走，賣在 stop 次一有效開盤（未完 ⇒ 2026-08-31 收盤）；
    報吃到第一頂、吃到真頂（中位＋平均，平均同 G4 剔除規則）、與 W1 基本版的同筆差（中位＋平均）、沒觸發占 W1 筆比例；確認段同筆平均差另附 G5 的月分群 bootstrap 區間
輸出 backtest/resultsSurge6/w1better/
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

warnings.filterwarnings("ignore", category=RuntimeWarning)
D = S5.D
TIME = "2026-09-30 00:02（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/w1better"
EXP = (2021 * 12, 2023 * 12 + 11); CON = (2024 * 12, 2026 * 12 + 7)
MS = (5, 7, 10)
YS = (0.05, 0.08, 0.10, 0.12, 0.15)
BASE = "W1 基本版"
BASE_SIG = "W1 基本版（訊號日歸類，對帳 topwarn）"
CLS = ["第一頂附近", "第二頂以後附近", "真頂附近", "都不在"]


def rules():
    """(名稱, 族, 型, 參數)；型：w1｜after_mask（(d1, stop] 內第一個 mask）｜after_dd_d1｜after_dd_e｜mask（[e, stop] 內第一個 mask）｜dd_e"""
    R = [(BASE, "基準", "w1", None)]
    R += [("C1 W1後 收黑破前低", "C1", "after_mask", "BLK"), ("C1 W1後 跌破MA5", "C1", "after_mask", "X5"), ("C1 W1後 跌破MA10", "C1", "after_mask", "X10")]
    R += [(f"C1 W1後 從W1後高回落{int(round(y * 100))}%", "C1", "after_dd_d1", y) for y in YS]
    R += [("C1 W1後 爆量長黑（Q5）", "C1", "after_mask", "BIG5"), ("C1 W1後 爆量長黑（Q4以上）", "C1", "after_mask", "BIG4")]
    R += [(f"C2 W1後 從持有期高回落{int(round(y * 100))}%", "C2", "after_dd_e", y) for y in YS]
    R += [("C3 W1＋K>80連續天數Q5", "C3", "mask", "W1KD5"), ("C3 W1＋K>80連續天數Q4以上", "C3", "mask", "W1KD4"),
          ("C3 W1＋布林上軌Q5", "C3", "mask", "W1BB5"), ("C3 W1＋布林上軌Q4以上", "C3", "mask", "W1BB4"),
          ("C3 W1＋5日漲停≥2", "C3", "mask", "W1LU2"), ("C3 W1＋5日漲停≥3", "C3", "mask", "W1LU3")]
    R += [(f"C4 不看W1 從持有期高回落{int(round(y * 100))}%", "C4", "dd_e", y) for y in YS]
    R += [("C4 不看W1 跌破MA10", "C4", "mask", "X10")]
    return R


RULES = rules()


def build_masks(uni, cal, n, bar, t1, log):
    """⇒ C（ffill 還原收盤）、O（還原開盤）、M（各 mask，S×n bool）"""
    S = len(uni); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    C = np.full((S, n), np.nan); O = np.full((S, n), np.nan)
    HI20 = np.zeros((S, n), bool); BLK = np.zeros((S, n), bool); X5 = np.zeros((S, n), bool); X10 = np.zeros((S, n), bool); BLACK = np.zeros((S, n), bool)
    BODY = np.full((S, n), np.nan, np.float64)
    D.DATA = S5.ST
    for s in range(S):
        st = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal)
        if st is None:
            continue
        df = st.df; c0 = df["close"].to_numpy(float); o0 = df["open"].to_numpy(float); l0 = df["low"].to_numpy(float)
        C[s] = pd.Series(c0).ffill().to_numpy(); O[s] = o0
        idx = np.flatnonzero(np.isfinite(c0) & bar[s])
        if len(idx) < 25:
            continue
        cb = c0[idx]; ob = o0[idx]; lb = l0[idx]
        mx20 = pd.Series(cb).rolling(20, min_periods=20).max().to_numpy(); pmx = np.r_[np.nan, mx20[:-1]]
        HI20[s, idx] = cb > pmx
        BLK[s, idx] = (cb < ob) & np.r_[False, cb[1:] < lb[:-1]]; BLACK[s, idx] = cb < ob
        for k, A in ((5, X5), (10, X10)):
            ma = pd.Series(cb).rolling(k, min_periods=k).mean().to_numpy()
            below = cb < ma * (1 - 1e-9)                                           # G8：相等不算跌破
            A[s, idx] = np.r_[False, below[1:] & ~below[:-1] & np.isfinite(ma[:-1])]
        BODY[s, idx] = np.r_[np.nan, (ob[1:] - cb[1:]) / cb[:-1]]
    log("[元件] 價量完成")
    BQ = np.zeros((S, n), np.int8)
    for t in range(n):
        b_ = bar[:, t]
        if b_.any():
            BQ[b_, t] = S5.qtie(BODY[b_, t])
    del BODY
    att = np.asarray(Qm[FX["att_10"]]) == 5
    surge = (np.asarray(Qm[FX["lu_5"]]) == 5) | (np.asarray(Qm[FX["r_5"]]) == 5)
    nod60 = np.asarray(Fm[FX["disp_60"]]) == 0
    W1 = HI20 & att & surge & nod60 & bar
    ar = np.asarray(Qm[FX["ar_20"]]); kd = np.asarray(Qm[FX["kdrun"]]); bb = np.asarray(Qm[FX["bbup"]]); lu5 = np.nan_to_num(np.asarray(Fm[FX["lu_5"]]), nan=0)
    M = {"W1": W1, "BLK": BLK & bar, "X5": X5 & bar, "X10": X10 & bar,
         "BIG5": BLACK & (ar == 5) & (BQ == 5) & bar, "BIG4": BLACK & (ar >= 4) & (BQ >= 4) & bar,
         "W1KD5": W1 & (kd == 5), "W1KD4": W1 & (kd >= 4), "W1BB5": W1 & (bb == 5), "W1BB4": W1 & (bb >= 4), "W1LU2": W1 & (lu5 >= 2), "W1LU3": W1 & (lu5 >= 3)}
    for k in M:
        M[k][:, t1 + 1:] = False
    log("[元件] 訊號完成｜" + "｜".join(f"{k} {int(v.sum()):,}" for k, v in M.items()))
    return C, O, M


def cls_of(x, tops):
    dist = np.abs(x - tops) - np.arange(len(tops)) * 1e-6; k = int(dist.argmin()); mn = abs(x - tops[k])
    return 3 if mn > 5 else (2 if k == len(tops) - 1 else (0 if k == 0 else 1))


def trades(uni, n, bar, inseg, t1, C, O, M, mon, log):
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); FX = S5.FIX
    buy_ok = np.load(os.path.join(WORK5, "buy_ok.npy"))
    cntm = np.zeros(bar.shape, np.int8)
    for nm, col, code in OV.FEATS:
        cntm += (np.asarray(Qm[FX[col]]) == code)
    okday = inseg.copy(); okday[t1:] = False
    TRS = []; RR = []
    for m in MS:
        cand = (cntm >= m) & bar & okday[None, :]; nt = 0
        for s in range(len(uni)):
            ds_ = np.flatnonzero(cand[s])
            if not len(ds_):
                continue
            c = C[s]; o = O[s]
            okop = np.isfinite(o) & (o > 0) & bar[s]
            nxo = np.full(n + 2, n + 10, np.int64)
            for p in range(n - 1, -1, -1):
                nxo[p] = p if okop[p] else nxo[p + 1]
            POS = {k: np.flatnonzero(v[s]) for k, v in M.items()}
            nxt_free = -1
            for d in ds_:
                if d <= nxt_free or not buy_ok[s, d + 1]:
                    continue
                e = d + 1; bp = o[e]
                seg = c[e:t1 + 1]; rm = np.maximum.accumulate(seg); w = np.flatnonzero(seg <= rm * 0.7)
                stop = e + int(w[0]) if len(w) else t1; opn = int(len(w) == 0)
                Ps = e + int(np.argmax(c[e:stop + 1]))
                cs = c[e:Ps + 1]
                pbs = [(e + a, e + b) for a, b, lo, hi in MD.pullbacks(cs) if a > 0 and lo <= hi * 0.8 * (1 + 1e-9)] if len(cs) > 2 else []
                tops = np.array([a for a, b in pbs] + [Ps]); bots = np.array([b for a, b in pbs] + ([] if opn else [stop]), np.int64)
                tid = len(TRS)
                TRS.append({"tid": tid, "m": m, "s": s, "d": d, "e": e, "bp": bp, "stop": stop, "P*": Ps, "H1": int(tops[0]), "段數": len(tops), "未完": opn, "進場月": mon[e],
                            "c_H1": c[tops[0]], "c_P": c[Ps], "sp_end": o[nxo[stop + 1]] if nxo[stop + 1] <= t1 else c[t1]})
                rmE = rm[:stop - e + 1]; segE = seg[:stop - e + 1]

                def first(pos, lo_):
                    j = np.searchsorted(pos, lo_)
                    return int(pos[j]) if j < len(pos) and pos[j] <= stop else None
                d1 = first(POS["W1"], e)
                for name, fam, kind, par in RULES:
                    if kind == "w1":
                        dsg = d1
                    elif kind == "mask":
                        dsg = first(POS[par], e)
                    elif kind == "dd_e":
                        hh = np.flatnonzero(segE <= rmE * (1 - par)); dsg = e + int(hh[0]) if len(hh) else None
                    elif d1 is None:
                        dsg = None
                    elif kind == "after_mask":
                        dsg = first(POS[par], d1 + 1)
                    elif kind == "after_dd_e":
                        k0 = d1 - e + 1; hh = np.flatnonzero(segE[k0:] <= rmE[k0:] * (1 - par)); dsg = d1 + 1 + int(hh[0]) if len(hh) else None
                    elif kind == "after_dd_d1":
                        s2 = c[d1:stop + 1]; r2 = np.maximum.accumulate(s2); hh = np.flatnonzero(s2[1:] <= r2[1:] * (1 - par)); dsg = d1 + 1 + int(hh[0]) if len(hh) else None
                    if dsg is None:
                        RR.append((tid, name, 0, -1, -1, np.nan, -1, -1, np.nan, np.nan)); continue
                    ex = int(nxo[min(dsg + 1, n + 1)]); sp = o[ex] if ex <= t1 else np.nan
                    later = float((c[dsg + 1:stop + 1] > c[e:dsg + 1].max()).any()) if dsg < stop else 0.0
                    j = np.searchsorted(bots, ex); nb = c[bots[j]] / sp - 1 if (j < len(bots) and np.isfinite(sp)) else np.nan
                    RR.append((tid, name, 1, dsg, ex, sp, cls_of(ex, tops), cls_of(dsg, tops) if kind == "w1" else -1, later, nb))
                nxt_free = stop; nt += 1
        log(f"[B'] ≥{m} 個：{nt:,} 筆")
    T = pd.DataFrame(TRS)
    R = pd.DataFrame(RR, columns=["tid", "規則", "觸發", "ds", "ex", "sp", "類", "類_訊號日", "又創新高", "下一段底÷賣價−1"])
    R = R.merge(T[["tid", "bp", "H1", "P*", "c_H1", "c_P"]], on="tid", how="left")
    R["吃到第一頂"] = (R["sp"] - R["bp"]) / (R["c_H1"] - R["bp"]); R["吃到真頂"] = (R["sp"] - R["bp"]) / (R["c_P"] - R["bp"])
    R["den1ok"] = (R["c_H1"] - R["bp"]) >= 0.05 * R["bp"]; R["denPok"] = (R["c_P"] - R["bp"]) >= 0.05 * R["bp"]
    R["賣價÷第一頂−1"] = R["sp"] / R["c_H1"] - 1
    R["賣出−第一頂"] = np.where(R["觸發"] == 1, R["ex"] - R["H1"], np.nan); R["賣出−真頂"] = np.where(R["觸發"] == 1, R["ex"] - R["P*"], np.nan)
    R = R.drop(columns=["bp", "H1", "P*", "c_H1", "c_P"])
    return T, R


def seg_mask(T, sg):
    if sg == "探索":
        return (T["進場月"] >= EXP[0]) & (T["進場月"] <= EXP[1])
    if sg == "確認":
        return T["進場月"] >= CON[0]
    return pd.Series(True, index=T.index)


def summarize(T, R):
    Rw = R.merge(T[["tid", "m", "進場月"]], on="tid")
    base = Rw[Rw["規則"] == BASE].set_index("tid"); TI = T.set_index("tid")
    out = []
    names = [r[0] for r in RULES] + [BASE_SIG]
    for m in MS:
        for sg in ("探索", "確認", "全部"):
            tt = T[(T["m"] == m) & seg_mask(T, sg)]; ids = set(tt["tid"]); N = len(tt)
            if not N:
                continue
            rr = Rw[Rw["tid"].isin(ids)]
            for name in names:
                x = rr[rr["規則"] == (BASE if name == BASE_SIG else name)]; h = x[x["觸發"] == 1]
                cl = h["類_訊號日"] if name == BASE_SIG else h["類"]
                fam = "基準" if name == BASE_SIG else next(r[1] for r in RULES if r[0] == name)
                r = {"m": m, "段": sg, "族": fam, "規則": name, "筆數": N, "觸發筆": len(h), "觸發比例": len(h) / N}
                for j, cn in enumerate(CLS):
                    r[cn] = (cl == j).mean() if len(h) else np.nan
                r["任一段頂±5"] = 1 - r["都不在"] if len(h) else np.nan
                for k_, ok in (("吃到第一頂", "den1ok"), ("吃到真頂", "denPok")):
                    r[f"{k_} 中位"] = h[k_].median(); r[f"{k_} 平均"] = h.loc[h[ok], k_].mean(); r[f"{k_} 平均剔除比例"] = 1 - h[ok].mean() if len(h) else np.nan
                r["賣價÷第一頂−1 中位"] = h["賣價÷第一頂−1"].median()
                for k_ in ("賣出−第一頂", "賣出−真頂"):
                    r[f"{k_} 中位"] = h[k_].median(); r[f"{k_} 平均"] = h[k_].mean()
                r["又創新高"] = h["又創新高"].mean() if len(h) else np.nan
                nb = h["下一段底÷賣價−1"]
                r["下一段底÷賣價−1 中位"] = nb.median(); r["下一段底÷賣價−1 平均"] = nb.mean(); r["有下一段底"] = nb.notna().mean() if len(h) else np.nan
                r["下一段底低於賣價"] = (nb < 0).sum() / nb.notna().sum() if nb.notna().any() else np.nan
                if name not in (BASE, BASE_SIG):
                    pr = h.set_index("tid").join(base[["觸發", "吃到第一頂", "sp", "ex"]], rsuffix="_b", how="inner")
                    pr = pr[pr["觸發_b"] == 1]; both = pr[["sp", "sp_b"]].notna().all(axis=1)
                    dd = pr["吃到第一頂"] - pr["吃到第一頂_b"]
                    r.update({"配對筆": len(pr), "配對 吃到第一頂差 中位": dd.median(), "配對 吃到第一頂差 平均": dd[pr["den1ok"]].mean(),
                              "配對 賣價較高": (pr["sp"] > pr["sp_b"])[both].mean() if both.any() else np.nan,
                              "配對 賣價相同": (pr["sp"] == pr["sp_b"])[both].mean() if both.any() else np.nan,
                              "配對 賣出日差 中位": (pr["ex"] - pr["ex_b"]).median()})
                if name != BASE_SIG:
                    r.update(fixed_den(Rw, TI, name, ids))
                out.append(r)
    return pd.DataFrame(out)


def fixed_eat(Rw, TI, name, tids):
    """G9：tids（W1 基本版有出現的筆）上，規則的賣價；沒觸發 ⇒ sp_end ⇒ (吃到第一頂, 吃到真頂, 觸發, den1ok, denPok)"""
    x = Rw[(Rw["規則"] == name) & Rw["tid"].isin(tids)].set_index("tid").reindex(sorted(tids))
    t = TI.loc[x.index]
    sp = np.where(x["觸發"] == 1, x["sp"], t["sp_end"])
    e1 = (sp - t["bp"]) / (t["c_H1"] - t["bp"]); eP = (sp - t["bp"]) / (t["c_P"] - t["bp"])
    return pd.DataFrame({"e1": e1, "eP": eP, "trig": x["觸發"].to_numpy(), "ok1": (t["c_H1"] - t["bp"]) >= 0.05 * t["bp"], "okP": (t["c_P"] - t["bp"]) >= 0.05 * t["bp"],
                         "月": t["進場月"]}, index=x.index)


def fixed_den(Rw, TI, name, ids):
    w1t = set(Rw.loc[(Rw["規則"] == BASE) & (Rw["觸發"] == 1) & Rw["tid"].isin(ids), "tid"])
    if not w1t:
        return {}
    a = fixed_eat(Rw, TI, name, w1t); b = fixed_eat(Rw, TI, BASE, w1t); d = a["e1"] - b["e1"]
    return {"固定分母 W1筆": len(a), "固定分母 沒觸發占W1筆": 1 - a["trig"].mean(),
            "固定分母 吃到第一頂 中位": a["e1"].median(), "固定分母 吃到第一頂 平均": a.loc[a["ok1"], "e1"].mean(),
            "固定分母 吃到真頂 中位": a["eP"].median(), "固定分母 吃到真頂 平均": a.loc[a["okP"], "eP"].mean(),
            "固定分母 同筆差 中位": d.median(), "固定分母 同筆差 平均": d[a["ok1"]].mean()}


def shortlist(SM):
    """探索段、每個 m：依（a）吃到第一頂中位、（b）任一段頂±5 各排名 ⇒ 前 5 名（不含基準列）"""
    SL = []
    for m in MS:
        x = SM[(SM["m"] == m) & (SM["段"] == "探索") & (SM["族"] != "基準")]
        for key, lab in (("吃到第一頂 中位", "a 吃到第一頂中位"), ("任一段頂±5", "b 賣在段頂±5")):
            y = x.sort_values(key, ascending=False, kind="mergesort").head(5)
            for rk, (nm, v) in enumerate(zip(y["規則"], y[key]), 1):
                SL.append({"m": m, "排名依": lab, "名次": rk, "規則": nm, "探索值": v})
    return pd.DataFrame(SL)


def boot(T, R, SL, B=2000):
    Rw = R.merge(T[["tid", "m", "進場月"]], on="tid"); base = Rw[Rw["規則"] == BASE].set_index("tid"); TI = T.set_index("tid")
    rng = np.random.default_rng(20260930); out = []
    for m in MS:
        ids = set(T.loc[(T["m"] == m) & seg_mask(T, "確認"), "tid"])
        for nm in sorted(set(SL.loc[SL["m"] == m, "規則"])):
            h = Rw[(Rw["tid"].isin(ids)) & (Rw["規則"] == nm) & (Rw["觸發"] == 1)].set_index("tid")
            pr = h.join(base[["觸發", "吃到第一頂"]], rsuffix="_b", how="inner"); pr = pr[(pr["觸發_b"] == 1) & pr["den1ok"]]
            dd = (pr["吃到第一頂"] - pr["吃到第一頂_b"]).dropna()
            r = {"m": m, "規則": nm, "n": len(dd), "月數": 0, "平均差": dd.mean(), "lo": np.nan, "hi": np.nan}
            if len(dd) >= 10:
                mon = pr.loc[dd.index, "進場月"].to_numpy(); v = dd.to_numpy(); um = np.unique(mon)
                sums = np.array([v[mon == u].sum() for u in um]); cnts = np.array([(mon == u).sum() for u in um])
                bs = [sums[k].sum() / cnts[k].sum() for k in (rng.integers(0, len(um), len(um)) for _ in range(B))]
                r.update({"月數": len(um), "lo": np.percentile(bs, 2.5), "hi": np.percentile(bs, 97.5)})
            # G9 固定分母（W1 基本版有出現的筆；沒觸發 ⇒ 30% 結束賣）
            w1t = set(Rw.loc[(Rw["規則"] == BASE) & (Rw["觸發"] == 1) & Rw["tid"].isin(ids), "tid"])
            a = fixed_eat(Rw, TI, nm, w1t); b = fixed_eat(Rw, TI, BASE, w1t); ok = a["ok1"] & np.isfinite(a["e1"] - b["e1"])
            v = (a["e1"] - b["e1"])[ok].to_numpy(); mon = a.loc[ok, "月"].to_numpy(); um = np.unique(mon)
            sums = np.array([v[mon == u].sum() for u in um]); cnts = np.array([(mon == u).sum() for u in um])
            bs = [sums[k].sum() / cnts[k].sum() for k in (rng.integers(0, len(um), len(um)) for _ in range(B))]
            r.update({"固定分母 n": len(v), "固定分母 平均差": v.mean(), "固定分母 lo": np.percentile(bs, 2.5), "固定分母 hi": np.percentile(bs, 97.5)})
            out.append(r)
    return pd.DataFrame(out)


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    C, O, M = build_masks(uni, cal, n, bar, t1, log)
    T, R = trades(uni, n, bar, inseg, t1, C, O, M, mon, log)
    T.to_csv(os.path.join(OUT, "trades.csv.gz"), index=False, float_format="%.10g")
    R.to_csv(os.path.join(OUT, "trade_rules.csv.gz"), index=False, float_format="%.10g")
    SM = summarize(T, R); SM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.5g")
    SL = shortlist(SM); SL.to_csv(os.path.join(OUT, "shortlist.csv"), index=False, float_format="%.5g")
    BT = boot(T, R, SL); BT.to_csv(os.path.join(OUT, "boot_pair_confirm.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "m": list(MS), "y": list(YS), "規則數": len(RULES), "筆數": {str(m): int((T["m"] == m).sum()) for m in MS}, "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[完] {time.time() - T0:.0f}s")


def page(log):
    SM = pd.read_csv(os.path.join(OUT, "summary.csv")); SL = pd.read_csv(os.path.join(OUT, "shortlist.csv")); BT = pd.read_csv(os.path.join(OUT, "boot_pair_confirm.csv"))
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CKJ = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal;min-width:10em}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:6px 10px;background:#eef4fb}.sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}"
            ".sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}.big{font-size:1.05rem}li{margin:.35em 0}")
    P_ = ED.P_
    PT = lambda v: "—" if not np.isfinite(v) else f"{v * 100:+.1f} 點"
    DY = lambda v: "—" if not np.isfinite(v) else (f"晚 {v:.0f} 天" if v > 0 else (f"早 {-v:.0f} 天" if v < 0 else "同一天"))
    g = lambda m, sg, nm: SM[(SM["m"] == m) & (SM["段"] == sg) & (SM["規則"] == nm)].iloc[0]
    bt = lambda m, nm: BT[(BT["m"] == m) & (BT["規則"] == nm)].iloc[0]
    CI = lambda b: f"{PT(b['固定分母 平均差'])}（95% {b['固定分母 lo'] * 100:+.1f}～{b['固定分母 hi'] * 100:+.1f}）"
    m0 = 7; b0 = g(m0, "確認", BASE)
    sla = SL[(SL["m"] == m0) & (SL["排名依"].str.startswith("a"))].sort_values("名次"); slb = SL[(SL["m"] == m0) & (SL["排名依"].str.startswith("b"))].sort_values("名次")
    rb = slb.iloc[0]["規則"]; ra = sla.iloc[0]["規則"]
    xb = g(m0, "確認", rb); xa = g(m0, "確認", ra)
    c3n = [r[0] for r in RULES if r[1] == "C3"]; c12n = [r[0] for r in RULES if r[1] in ("C1", "C2")]; c4n = [r[0] for r in RULES if r[1] == "C4"]
    X7 = SM[(SM["m"] == m0) & (SM["段"] == "確認")].set_index("規則")
    good = BT[BT["固定分母 lo"] > 0]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>第一頂警示改良</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>第一頂警示 W1 能更靠近頂部嗎？（起漲訊號買進，2021–2026-08）</h1>",
         "<p class='warn'>⚠ 只當參考，沒有計入檢定數；是看過 W1 結果之後才加的題。段頂、真頂都是事後才知道，只拿來對答案；每個賣出規則都是當天收盤就能判斷、隔天開盤賣。"
         "版本在探索段（2021–2023）排名選出，確認段（2024–2026-08）只照報，不在確認段挑。沒有用「抱固定天數」當對照。</p>",
         f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}（之後兩次補充見文末）。進場 ＝ 14 個起漲特徵同時 ≥ m 個、隔天開盤買；一筆的結束 ＝ 從最高收盤回落 30%；"
         f"第一頂、第二頂用拉回 20% 切。共 {len(RULES) - 1} 個改良版本 × m ＝ 5、7、10。"
         + (f"查核：抽 200 筆逐日重算 5 個規則 {CKJ['抽 200 筆不同']} 筆不同；W1 基本版與上一份（topwarn）逐項對帳 {CKJ['對帳 topwarn 不同']} 項不同。" if CKJ else "") + "</p>",
         f"<h2>先講結論（確認段，m＝{m0}，{int(b0['筆數']):,} 筆；m＝5、10 方向相同，見下表）</h2><ul class='big'>",
         f"<li><b>沒有一個版本在「賣價」上穩定比 W1 基本版更靠近第一頂。</b>W1 基本版：{P_(b0['觸發比例'])} 的筆會出現，賣在第一次出現吃到進場→第一頂的 {P_(b0['吃到第一頂 中位'])}（中位），"
         f"賣價比第一頂低 {P_(-b0['賣價÷第一頂−1 中位'])}，賣出日比第一頂{DY(b0['賣出−第一頂 中位'])}；之後又創新高 {P_(b0['又創新高'])}。</li>",
         f"<li><b>W1 後等轉弱再賣（C1、C2）：時間更靠近頂，但賣得更便宜。</b>探索段最準的是「{html.escape(rb)}」：賣出日落在段頂 ±5 天 {P_(xb['任一段頂±5'])}（基本版 {P_(b0['任一段頂±5'])}）、"
         f"賣出日比第一頂{DY(xb['賣出−第一頂 中位'])}、賣後又創新高降到 {P_(xb['又創新高'])}；"
         f"代價是同一批筆吃到第一頂 {CI(bt(m0, rb))}。"
         f"等越深（回落 8%→15%）越差：C1、C2 各版同筆平均差 {X7.loc[c12n, '固定分母 同筆差 平均'].max() * 100:+.1f}～{X7.loc[c12n, '固定分母 同筆差 平均'].min() * 100:+.1f} 點。</li>",
         f"<li><b>W1 當天再疊條件（C3）：看起來更近，其實是挑到了後來還在漲的股票。</b>「{html.escape(ra)}」有出現的筆吃到第一頂 {P_(xa['吃到第一頂 中位'])}（基本版 {P_(b0['吃到第一頂 中位'])}），"
         f"但只有 {P_(xa['觸發比例'])} 的筆會出現（基本版 {P_(b0['觸發比例'])}）；W1 出現卻等不到疊加的 {P_(xa['固定分母 沒觸發占W1筆'])} 筆，只能等回落 30% 才出場。"
         f"用同一批 W1 筆公平比（沒出現就照 30% 結束賣），吃到第一頂中位只剩 {P_(xa['固定分母 吃到第一頂 中位'])}（基本版 {P_(b0['吃到第一頂 中位'])}）、同筆平均差 {CI(bt(m0, ra))}，區間很寬；"
         f"C3 六版同筆平均差 {X7.loc[c3n, '固定分母 同筆差 平均'].min() * 100:+.1f}～{X7.loc[c3n, '固定分母 同筆差 平均'].max() * 100:+.1f} 點。</li>",
         f"<li><b>不看 W1、只看轉弱（C4 對照）：幾乎吃不到第一頂</b>（吃到第一頂中位 {P_(X7.loc[c4n, '吃到第一頂 中位'].min())}～{P_(X7.loc[c4n, '吃到第一頂 中位'].max())}）——起漲後的小回檔就把人洗出去。W1 這個「過熱」條件本身是必要的。</li>"]
    if len(good):
        H.append("<li>確認段同筆平均差的 95% 區間整段在 0 以上的只有："
                 + "；".join(f"m＝{int(r['m'])} {html.escape(r['規則'])} {PT(r['固定分母 平均差'])}（{r['固定分母 lo'] * 100:+.1f}～{r['固定分母 hi'] * 100:+.1f}）" for r in good.to_dict("records"))
                 + "。幅度小、只在一個 m 出現，其他 m 的同一類版本差不多是 0，⛔ 不當成改良。</li>")
    H.append(f"<li class='ok'><b>讀法</b>：W1 仍是「第一頂附近」最好的當下提示，但它本質上是「過熱了、可能在頂附近」，不是「這就是頂」——出現後約 {P_(b0['又創新高'])} 還會再創新高。"
             f"想少被洗、晚一點賣，可用「{html.escape(rb)}」，代價約少吃第一頂漲幅 {-bt(m0, rb)['固定分母 平均差'] * 100:.0f} 點。</li></ul>")
    # 表 A
    H.append("<h2>一、探索段選出的版本，到確認段照報</h2><p class='note'>每個 m 在探索段依「吃到第一頂中位」與「賣在段頂 ±5 的比例」各取前 5 名。"
             "「同一批 W1 筆」＝ 分母固定為 W1 基本版有出現的筆，規則沒出現就照回落 30% 結束賣，這樣才不會只挑好的筆比。</p>")
    H.append("<div class='sel'>m <select id='ma' onchange='swa()'>" + "".join(f"<option value='{m}'>{m}</option>" for m in MS) + "</select></div>")
    for m in MS:
        H.append(f"<div class='pane pa' id='a{m}'><div class='wrap'><table><tr><th class='l'>規則</th><th>探索段排名</th><th>有出現</th><th>賣在段頂±5</th><th>吃到第一頂<br><small>有出現的筆</small></th>"
                 "<th>吃到第一頂<br><small>同一批 W1 筆</small></th><th>同筆差（平均）<br><small>95% 月分群</small></th><th>賣出−第一頂</th><th>賣後又創新高</th><th>賣後到下一段底</th></tr>")
        names = [BASE] + list(dict.fromkeys(SL.loc[SL["m"] == m, "規則"]))
        for nm in names:
            x = g(m, "確認", nm)
            rk = "；".join(f"{r['排名依'][0]}#{int(r['名次'])}" for r in SL[(SL["m"] == m) & (SL["規則"] == nm)].to_dict("records")) or "基準"
            if nm == BASE:
                ci = "—"
            else:
                b = bt(m, nm); ci = f"{PT(b['固定分母 平均差'])}<br><small>{b['固定分母 lo'] * 100:+.1f}～{b['固定分母 hi'] * 100:+.1f}</small>"
            H.append(f"<tr><td class='l'>{html.escape(nm)}</td><td>{rk}</td><td>{P_(x['觸發比例'])}</td><td>{P_(x['任一段頂±5'])}</td><td>{P_(x['吃到第一頂 中位'])}</td>"
                     f"<td>{P_(x['固定分母 吃到第一頂 中位'])}</td><td>{ci}</td><td>{DY(x['賣出−第一頂 中位'])}</td><td>{P_(x['又創新高'])}</td><td>{P_(x['下一段底÷賣價−1 中位'])}</td></tr>")
        H.append(f"</table></div><p class='note'>確認段 {int(g(m, '確認', BASE)['筆數']):,} 筆。排名 a ＝ 吃到第一頂中位、b ＝ 賣在段頂 ±5。賣後到下一段底：負 ＝ 賣了之後又跌這麼多（躲過）。</p></div>")
    # 表 B
    H.append("<h2>二、全部版本（每個版本都報）</h2><div class='sel'>m <select id='mb' onchange='swb()'>" + "".join(f"<option value='{m}'>{m}</option>" for m in MS)
             + "</select>段 <select id='sb' onchange='swb()'><option>確認</option><option>探索</option><option>全部</option></select></div>")
    for m in MS:
        for sg in ("確認", "探索", "全部"):
            x = SM[(SM["m"] == m) & (SM["段"] == sg)]
            H.append(f"<div class='pane pb' id='b{m}_{sg}'><p class='note'>{int(x['筆數'].iloc[0]):,} 筆。</p><div class='wrap'><table><tr><th class='l'>規則</th><th>有出現</th><th>第一頂±5</th><th>第二頂以後±5</th><th>真頂±5</th><th>都不在</th>"
                     "<th>吃到第一頂<br><small>中位／平均</small></th><th>吃到真頂<br><small>中位／平均</small></th><th>賣價比第一頂</th><th>賣出−第一頂<br><small>中位／平均</small></th><th>賣出−真頂<br><small>中位／平均</small></th>"
                     "<th>又創新高</th><th>到下一段底<br><small>中位／平均</small></th><th>同一批 W1 筆<br><small>吃到第一頂中位／同筆差平均</small></th><th>W1 出現但沒觸發</th></tr>")
            for r in x.to_dict("records"):
                fd = "—" if r["規則"] == BASE_SIG else f"{P_(r['固定分母 吃到第一頂 中位'])}<br><small>{PT(r['固定分母 同筆差 平均'])}</small>"
                H.append(f"<tr><td class='l'>{html.escape(r['規則'])}</td><td>{P_(r['觸發比例'])}</td><td>{P_(r['第一頂附近'])}</td><td>{P_(r['第二頂以後附近'])}</td><td>{P_(r['真頂附近'])}</td><td>{P_(r['都不在'])}</td>"
                         f"<td>{P_(r['吃到第一頂 中位'])}<br><small>{P_(r['吃到第一頂 平均'])}</small></td><td>{P_(r['吃到真頂 中位'])}<br><small>{P_(r['吃到真頂 平均'])}</small></td><td>{P_(r['賣價÷第一頂−1 中位'])}</td>"
                         f"<td>{DY(r['賣出−第一頂 中位'])}<br><small>{r['賣出−第一頂 平均']:+.1f}</small></td><td>{DY(r['賣出−真頂 中位'])}<br><small>{r['賣出−真頂 平均']:+.1f}</small></td>"
                         f"<td>{P_(r['又創新高'])}</td><td>{P_(r['下一段底÷賣價−1 中位'])}<br><small>{P_(r['下一段底÷賣價−1 平均'])}</small></td><td>{fd}</td>"
                         f"<td>{'—' if r['規則'] == BASE_SIG else P_(r['固定分母 沒觸發占W1筆'])}</td></tr>")
            H.append("</table></div></div>")
    H.append("<h2>名詞</h2><ul class='note'>"
             "<li>W1 基本版 ＝ 創 20 日新高 ＋ 10 日注意次數前 20% ＋（5 日漲停天數或 5 日報酬前 20%）＋ 過去 60 日沒處置。</li>"
             "<li>C1 ＝ W1 出現後，等第一個轉弱日才賣（收黑跌破前一天最低、跌破 MA5／MA10、從 W1 後最高回落 y%、爆量長黑）。C2 ＝ W1 出現後，從進場後最高回落 y% 就賣。"
             "C3 ＝ W1 當天另外要有 K＞80 連續天數、布林上軌、5 日漲停天數。C4 ＝ 不看 W1，只看回落 y% 或跌破 MA10。</li>"
             "<li>段頂 ±5 用「賣出日」歸類（上一份用訊號日；表二的「訊號日歸類」那列就是上一份的數字）。吃到第一頂 ＝（賣價 − 買價）÷（第一頂收盤 − 買價）；超過 100% ＝ 賣在第一頂之後、更高的價位。"
             "平均只算「進場到頂漲幅 ≥ 5%」的筆，免得分母接近 0 把平均拉爆。</li>"
             "<li>95% 區間 ＝ 依進場月份分群重抽 2000 次，只當描述。</li>"
             "<li>補充 1（2026-09-30 00:13）：查核抓到一筆收盤剛好等於 MA10，改成「相等不算跌破」後整份重跑（當時還沒看任何規則的數字）。"
             "補充 2（2026-09-30 00:18，已看過數字）：加上「同一批 W1 筆」的公平比較，只當描述，不影響探索段排名。</li></ul>")
    H.append("<script>function swa(){var m=document.getElementById('ma').value;document.querySelectorAll('.pa').forEach(x=>x.classList.toggle('on',x.id=='a'+m))}"
             "function swb(){var m=document.getElementById('mb').value,s=document.getElementById('sb').value;document.querySelectorAll('.pb').forEach(x=>x.classList.toggle('on',x.id=='b'+m+'_'+s))}"
             f"document.getElementById('ma').value='{m0}';document.getElementById('mb').value='{m0}';swa();swb()</script></main></body></html>")
    open(os.path.join(OUT, "第一頂警示改良.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def check(log):
    """G6：m＝7 抽 200 筆逐日迴圈重算；另對帳 topwarn。"""
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    att = np.asarray(Qm[FX["att_10"]]); lu5 = np.asarray(Qm[FX["lu_5"]]); r5 = np.asarray(Qm[FX["r_5"]]); d60 = np.asarray(Fm[FX["disp_60"]])
    T = pd.read_csv(os.path.join(OUT, "trades.csv.gz")); R = pd.read_csv(os.path.join(OUT, "trade_rules.csv.gz"))
    CK = {"C1 W1後 收黑破前低": "blk", "C1 W1後 跌破MA10": "x10", "C2 W1後 從持有期高回落10%": "c2", "C4 不看W1 從持有期高回落10%": "c4"}
    TB = T[T["m"] == 7].sample(200, random_state=20260930)
    D.DATA = S5.ST; errs = []; nd = 0; ntrig = {k: 0 for k in CK.values()}
    for r in TB.itertuples():
        s, e, bp = int(r.s), int(r.e), float(r.bp)
        df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
        c0 = df["close"].to_numpy(float); o0 = df["open"].to_numpy(float); l0 = df["low"].to_numpy(float); cc = pd.Series(c0).ffill().to_numpy()
        isb = [bool(np.isfinite(c0[d]) and bar[s, d]) for d in range(n)]
        bars = [d for d in range(n) if isb[d]]; bpos = {d: j for j, d in enumerate(bars)}
        rm = -np.inf; stop = t1
        for d in range(e, t1 + 1):
            rm = max(rm, cc[d])
            if cc[d] <= rm * 0.7:
                stop = d; break
        Ps = e + int(np.argmax(cc[e:stop + 1]))
        pk, pkd, tv, tops = cc[e], e, np.inf, []
        for d in range(e + 1, Ps + 1):
            if cc[d] > pk:
                if pkd > e and tv <= pk * 0.8 * (1 + 1e-9):
                    tops.append(pkd)
                pk, pkd, tv = cc[d], d, np.inf
            elif cc[d] < tv:
                tv = cc[d]
        H1 = tops[0] if tops else Ps

        def w1(d):
            if not isb[d] or d > t1:
                return False
            j = bpos[d]
            if j < 20 or not (c0[d] > max(c0[bars[j - 20:j]])):
                return False
            return att[s, d] == 5 and (lu5[s, d] == 5 or r5[s, d] == 5) and d60[s, d] == 0

        def ma10(d):
            j = bpos[d]
            return sum(c0[bars[j - 9:j + 1]]) / 10 if j >= 9 else np.nan
        d1 = next((d for d in range(e, stop + 1) if w1(d)), None)
        got = {}
        if d1 is not None:
            got["blk"] = next((d for d in range(d1 + 1, stop + 1) if isb[d] and bpos[d] >= 1 and c0[d] < o0[d] and c0[d] < l0[bars[bpos[d] - 1]]), None)
            got["x10"] = next((d for d in range(d1 + 1, stop + 1) if isb[d] and bpos[d] >= 10 and c0[d] < ma10(d) * (1 - 1e-9) and not (c0[bars[bpos[d] - 1]] < ma10(bars[bpos[d] - 1]) * (1 - 1e-9))), None)
        else:
            got["blk"] = got["x10"] = None
        rm = -np.inf; got["c2"] = got["c4"] = None
        for d in range(e, stop + 1):
            rm = max(rm, cc[d])
            if cc[d] <= rm * 0.9:
                if got["c4"] is None:
                    got["c4"] = d
                if got["c2"] is None and d1 is not None and d > d1:
                    got["c2"] = d
        why = []
        bp0 = o0[e]                                                               # 買價用原始還原開盤重算（檔內 bp 已四捨五入到 10 位有效數字）
        if not np.isclose(bp0, bp, rtol=1e-8):
            why.append("bp")
        if not (stop == int(r.stop) and Ps == int(r._8) and H1 == int(r.H1)):
            why.append("stop/P*/H1")
        rb = R[(R["tid"] == r.tid) & (R["規則"] == BASE)].iloc[0]
        if not ((d1 is None and rb["觸發"] == 0) or (d1 is not None and rb["觸發"] == 1 and d1 == int(rb["ds"]))):
            why.append("W1 d1")
        for nm, k in CK.items():
            rr = R[(R["tid"] == r.tid) & (R["規則"] == nm)].iloc[0]; g = got[k]
            if g is None:
                if rr["觸發"] != 0:
                    why.append(f"{k} 觸發")
                continue
            ntrig[k] += 1
            ex = g + 1
            while ex <= t1 and not (np.isfinite(o0[ex]) and o0[ex] > 0 and bar[s, ex]):
                ex += 1
            if not (rr["觸發"] == 1 and g == int(rr["ds"]) and ex == int(rr["ex"])):
                why.append(f"{k} 日 {g}/{rr['ds']}")
            elif ex <= t1:
                v = (o0[ex] - bp0) / (cc[H1] - bp0)
                if not np.isclose(v, rr["吃到第一頂"], rtol=1e-6, atol=1e-8, equal_nan=True):
                    why.append(f"{k} 吃到 {v}/{rr['吃到第一頂']}")
        if why:
            nd += 1; errs.append(f"tid {r.tid}：{'；'.join(why)}")
    log(f"[查核] 抽 200 筆不同 {nd}｜各規則觸發筆 {ntrig}")
    # 對帳 topwarn
    SM = pd.read_csv(os.path.join(OUT, "summary.csv")); TWS = pd.read_csv("backtest/resultsSurge6/topwarn/Bp_signals.csv")
    rec = []; nbad = 0
    MAP = {"有出現": "觸發比例", "第一頂附近": "第一頂附近", "第二頂以後附近": "第二頂以後附近", "真頂附近": "真頂附近", "都不在": "都不在",
           "吃到第一頂 中位": "吃到第一頂 中位", "吃到真頂 中位": "吃到真頂 中位", "賣出日−第一頂 中位": "賣出−第一頂 中位", "賣出日−真頂 中位": "賣出−真頂 中位", "之後又創新高": "又創新高", "筆數": "筆數"}
    for m in (5, 7):
        for sg in ("探索", "確認", "全部"):
            a = TWS[(TWS["進場"] == f"起漲特徵 ≥{m} 個") & (TWS["段"] == sg) & (TWS["訊號"] == "W1 注意10日Q5×急拉lu5或r5")].iloc[0]
            b = SM[(SM["m"] == m) & (SM["段"] == sg) & (SM["規則"] == BASE_SIG)].iloc[0]
            for ka, kb in MAP.items():
                same = bool(np.isclose(float(a[ka]), float(b[kb]), rtol=1e-4, atol=1e-6))
                nbad += int(not same); rec.append({"m": m, "段": sg, "項": ka, "topwarn": float(a[ka]), "本檔": float(b[kb]), "同": same})
    log(f"[對帳 topwarn] 不同 {nbad} / {len(rec)}")
    out = {"讀法寫死": TIME, "抽樣": "m＝7 trades 抽 200 筆（random_state 20260930）", "重算規則": ["W1 基本版", *CK], "抽 200 筆不同": nd, "各規則觸發筆": ntrig,
           "不同的筆": errs[:20], "對帳 topwarn 不同": nbad, "對帳 topwarn 明細": rec, "通過": nd == 0 and nbad == 0}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()
