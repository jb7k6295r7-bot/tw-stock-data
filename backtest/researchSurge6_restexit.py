# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：W1 賣 3 成後「剩下 7 成」與「沒漲起來的筆」怎麼出場（參考，⛔ 不計 N；看過 topwarn、w1better 結果之後才加）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_restexit [--check | --page]

═══ 讀法（寫死於 2026-09-30 00:41（台北），在算任何數字之前；題目由協調者轉達（使用者已決定：W1 第一次出現 ⇒ 次一開盤賣 3 成、留 7 成），⛔ 不在確認段挑）═══
 E1 母體 B'（同 researchSurge6_topwarn R5／w1better G1，⛔ 不改）：14 個起漲特徵同時 ≥ m 個，m ∈ {5, 7, 10}；d＋1 開盤買（bp）；同一檔到本筆結束前不重複進場
    本筆結束 stop ＝ 第一次收盤 ≤ 進場以來最高收盤 × 0.7；真頂 P* ＝ [e, stop] 最高收盤；到 2026-08-31 沒回落 30% ⇒「未完」（stop ＝ 2026-08-31）
    W1 基本版（同 w1better G2）第一次出現日 d1 ∈ [e, stop]；W1 賣價 sp1 ＝ d1 之後第一個有效開盤 ex1 的還原開盤
    分群（事後）：甲 ＝ 有 d1；乙 ＝ 沒有 d1。探索 2021-01～2023-12、確認 2024-01～2026-08，依進場月份
 E2 所有規則：d 收盤可判 ⇒ 賣在 d 之後第一個有效開盤；觸發日 ds 必須 ≤ stop；沒觸發 ⇒ 照現行 30% 結束：stop 次一有效開盤（未完 ⇒ 2026-08-31 收盤）
    甲群規則窗 ＝ (d1, stop]（R3 為 [ex1, stop]）；乙群規則窗 ＝ [e, stop]
    元件（還原收盤、K 棒序列）：
      R1 移動停利：收盤 ≤ 參考最高收盤 ×(1 − y)，y ∈ {5, 8, 10, 15, 20, 30}%；參考 ＝ 甲：[d1, d] 最高收盤｜乙：[e, d] 最高收盤（無容差）
      R2 跌破均線 MAk（k ∈ {10, 20, 60}，含當根的 k 根收盤平均）：收盤 ＜ MAk ×(1 − 1e−9) 且前一根沒有如此（向下穿越；同 w1better G8）
      R3 保本線：甲 ＝ 收盤 ＜ sp1 ×(1 ＋ z)，z ∈ {0, −5, −10}%，d ∈ [ex1, stop]｜乙 ＝ 收盤 ＜ bp ×(1 ＋ z)，z ∈ {−5, −8, −10, −15}%
      R4 沒創新高 N 天：新高 ＝ 收盤 ＞ 參考起點以來最高收盤（甲 起點 d1、乙 起點 e；起點本身算新高日）；最後一個新高日 h 之後的 K 棒數（(h, d] 內有 K 棒的日子）第一次 ≥ N 的那天，N ∈ {5, 10, 20, 40}
          ⚠ 這是規則候選，不是固定持有對照
      R5 現行流程：甲 ＝ (d1, stop] 內第一個 W2（W2a 再次進入處置 或 W2b 處置出關，60 日版，同 topwarn R3），沒有 ⇒ 30% 結束；另報「只等回落 30%」一版｜乙 ＝ 30% 結束
      R6 組合：R1(y) 與 R4(N) 取先到的；y × N 全網格 24 組都報
 E3 甲群（剩 7 成；W1 那 3 成固定）：
    有再漲 ＝ (d1, stop] 內最高收盤 ＞ [e, d1] 最高收盤（又創新高）且 ＞ sp1 × 1.10；其餘 ＝ 沒再漲
    報（全部、有再漲、沒再漲 各一份）：觸發比例；出場價 ÷ sp1 − 1；出場價 ÷ c[P*]；
      對現行（R5 W2 或 30%）：(出場價 − R5 出場價) ÷ bp —— 沒再漲者的平均 ＝「少虧」（正 ＝ 少虧）、有再漲者取負號 ＝「少賺」（正 ＝ 少賺）
      整筆合計：報酬 ＝ 0.3 × sp1 ÷ bp ＋ 0.7 × 出場價 ÷ bp − 1；吃到真頂 ＝ [0.3 (sp1 − bp) ＋ 0.7 (出場價 − bp)] ÷ (c[P*] − bp)，中位與平均（平均只算 c[P*] − bp ≥ 5% × bp 的筆，同 w1better）
 E4 乙群（整筆）：出場報酬 ＝ 出場價 ÷ bp − 1 的 p10／p25／中位／p75／p90／平均；虧損比例、虧損筆的虧損中位；
    賣錯 ＝ (ds, stop] 內有收盤 ＞ bp（照現行流程抱著的話，賣後又漲回進場價以上）；對現行（30% 結束）差 ＝ (出場價 − 30% 結束價) ÷ bp，中位與平均
    ⭐ 當下的代價（開算前就加；乙是事後才知道的分群）：同一條乙群規則從進場日起套在「甲群」的筆上 ⇒ 在 W1 出現前（ds ＜ d1）就被賣掉的比例（誤殺）；
      以及套在全部筆上的整筆報酬（規則先到 ⇒ 規則價整筆出；否則 ⇒ 3 成 W1 ＋ 7 成現行 R5）對「全部照現行」的差，中位與平均
 E5 排名（探索段、每個 m）：甲 依「整筆合計吃到真頂 中位」由高到低取前 5；乙 依「出場報酬中位 名次 ＋ 賣錯率 名次（低者好）」名次和由小到大取前 5（同分依報酬中位）；
    前 5 名 ＋ 現行 R5 到確認段照報，⛔ 不依確認段重排
    確認段前 5 名另附對現行的同筆差（甲：整筆吃到真頂；乙：出場報酬；再加乙規則套全部筆的整筆報酬差）平均的進場月分群 bootstrap 95% 區間（2000 次，種子 20260930；只當描述）
 E6 查核（--check）：m＝7 抽 200 筆逐日迴圈重算 stop、P*、d1、sp1，與規則 R1 y＝10%、R2 MA20、R3（甲 z＝0／乙 z＝−8%）、R4 N＝10 的觸發日與出場價、甲群整筆吃到真頂；0 不同才算過；
    另對帳 w1better：同一 m 的筆（股, 進場日）與 W1 d1 應完全相同
 E7 網頁先講結論，一句話建議：剩 7 成用什麼出場、沒漲起來的用什麼出場、代價是什麼；⛔ 不用固定持有天數當對照
 E8（2026-09-30 00:53（台北）補；⚠ 已看過彙總數字）：甲群「吃到真頂」是逐筆比例，會把大漲筆與小漲筆等權 ——
    看到收緊出場讓吃到真頂中位上升、但整筆報酬平均下降 ⇒ 確認段前 5 名另附「整筆報酬 對現行差」平均的同一套月分群 bootstrap 區間（只當描述，⛔ 不改 E5 排名）
輸出 backtest/resultsSurge6/restexit/
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
from backtest import researchSurge6_overlap as OV

warnings.filterwarnings("ignore", category=RuntimeWarning)
D = S5.D
TIME = "2026-09-30 00:41（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/restexit"
EXP = (2021 * 12, 2023 * 12 + 11); CON = (2024 * 12, 2026 * 12 + 7)
MS = (5, 7, 10)
YS = (0.05, 0.08, 0.10, 0.15, 0.20, 0.30)
KS = (10, 20, 60)
ZA = (0.0, -0.05, -0.10)
ZB = (-0.05, -0.08, -0.10, -0.15)
NS = (5, 10, 20, 40)
R5A = "R5 現行：等W2或回落30%"
R5A0 = "R5 只等回落30%"
R5B = "R5 現行：等回落30%"
pc = lambda v: f"{int(round(v * 100))}%"


def rule_list(grp):
    R = [(f"R1 從{'W1後' if grp == 'A' else '進場後'}高回落{pc(y)}", "R1", ("dd", y)) for y in YS]
    R += [(f"R2 跌破MA{k}", "R2", ("ma", k)) for k in KS]
    if grp == "A":
        R += [(f"R3 跌破W1賣價{'' if z == 0 else pc(z)}".replace("賣價-", "賣價−"), "R3", ("be", z)) for z in ZA]
    else:
        R += [(f"R3 跌破進場價{pc(z)}".replace("價-", "價−"), "R3", ("be", z)) for z in ZB]
    R += [(f"R4 連{N}天沒創新高", "R4", ("nh", N)) for N in NS]
    R += [(R5A, "R5", ("w2",)), (R5A0, "R5", ("end",))] if grp == "A" else [(R5B, "R5", ("end",))]
    R += [(f"R6 回落{pc(y)}或連{N}天沒新高", "R6", ("combo", y, N)) for y in YS for N in NS]
    return R


RA = rule_list("A"); RB = rule_list("B")


def build(uni, cal, n, bar, t1, log):
    S = len(uni); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    C = np.full((S, n), np.nan); O = np.full((S, n), np.nan)
    HI20 = np.zeros((S, n), bool); NEAR = np.zeros((S, n), bool); XM = {k: np.zeros((S, n), bool) for k in KS}
    D.DATA = S5.ST
    for s in range(S):
        st = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal)
        if st is None:
            continue
        c0 = st.df["close"].to_numpy(float); C[s] = pd.Series(c0).ffill().to_numpy(); O[s] = st.df["open"].to_numpy(float)
        idx = np.flatnonzero(np.isfinite(c0) & bar[s])
        if len(idx) < 25:
            continue
        cb = c0[idx]
        mx20 = pd.Series(cb).rolling(20, min_periods=20).max().to_numpy(); pmx = np.r_[np.nan, mx20[:-1]]
        HI20[s, idx] = cb > pmx; NEAR[s, idx] = cb >= 0.9 * mx20
        for k in KS:
            ma = pd.Series(cb).rolling(k, min_periods=k).mean().to_numpy(); below = cb < ma * (1 - 1e-9)
            XM[k][s, idx] = np.r_[False, below[1:] & ~below[:-1] & np.isfinite(ma[:-1])]
    log("[元件] 價量完成")
    att = np.asarray(Qm[FX["att_10"]]) == 5
    surge = (np.asarray(Qm[FX["lu_5"]]) == 5) | (np.asarray(Qm[FX["r_5"]]) == 5)
    nod60 = np.asarray(Fm[FX["disp_60"]]) == 0
    W1 = HI20 & att & surge & nod60 & bar
    _, DISP = S5.SF.att_disp(S5.MAIN, cal)
    EXIT = np.zeros((S, n), bool); RE60 = np.zeros((S, n), bool); sid2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    for sd, iv in DISP.items():
        if sd not in sid2i:
            continue
        s = sid2i[sd]; st_ = sorted(a for a, b in iv)
        for a, b in iv:
            if 0 <= a < n and any(0 < a - x <= 60 for x in st_ if x != a):
                RE60[s, a] = True
            if 0 <= b + 1 < n:
                EXIT[s, b + 1] = True
    W2 = ((RE60 & NEAR) | (EXIT & NEAR)) & bar
    M = {"W1": W1, "W2": W2, **{f"X{k}": XM[k] & bar for k in KS}}
    for k in M:
        M[k][:, t1 + 1:] = False
    log("[元件] 訊號完成｜" + "｜".join(f"{k} {int(v.sum()):,}" for k, v in M.items()))
    return C, O, M


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
            c = C[s]; o = O[s]; bs = bar[s]; cbar = np.cumsum(bs)
            okop = np.isfinite(o) & (o > 0) & bs
            nxo = np.full(n + 2, n + 10, np.int64)
            for p in range(n - 1, -1, -1):
                nxo[p] = p if okop[p] else nxo[p + 1]
            POS = {k: np.flatnonzero(v[s]) for k, v in M.items()}
            px_of = lambda dd: (o[nxo[dd + 1]] if nxo[dd + 1] <= t1 else c[t1])
            nxt_free = -1
            for d in ds_:
                if d <= nxt_free or not buy_ok[s, d + 1]:
                    continue
                e = d + 1; bp = o[e]
                seg = c[e:t1 + 1]; rm = np.maximum.accumulate(seg); w = np.flatnonzero(seg <= rm * 0.7)
                stop = e + int(w[0]) if len(w) else t1; opn = int(len(w) == 0)
                Ps = e + int(np.argmax(c[e:stop + 1])); pend = px_of(stop)

                def first(pos, lo_):
                    j = np.searchsorted(pos, lo_)
                    return int(pos[j]) if j < len(pos) and pos[j] <= stop else None

                def run_rules(RL, st0, lo_be, thr_be):
                    """st0：參考起點（甲 d1／乙 e）；規則觸發日 ⇒ {名: ds or None}"""
                    sg = c[st0:stop + 1]; r_ = np.maximum.accumulate(sg)
                    lo_ = st0 + 1 if RL is RA else st0                                     # 甲：(d1, stop]；乙：[e, stop]
                    k0 = lo_ - st0
                    isnh = np.r_[True, sg[1:] > r_[:-1]]; lastnh = st0 + np.maximum.accumulate(np.where(isnh, np.arange(len(sg)), 0))
                    nbar = cbar[st0:stop + 1] - cbar[lastnh]
                    out = {}
                    dd = {}
                    for y in YS:
                        hh = np.flatnonzero(sg[k0:] <= r_[k0:] * (1 - y)); dd[y] = lo_ + int(hh[0]) if len(hh) else None
                    nh = {}
                    for N in NS:
                        hh = np.flatnonzero(nbar[k0:] >= N); nh[N] = lo_ + int(hh[0]) if len(hh) else None
                    for name, fam, par in RL:
                        t_ = par[0]
                        if t_ == "dd":
                            v = dd[par[1]]
                        elif t_ == "ma":
                            v = first(POS[f"X{par[1]}"], lo_)
                        elif t_ == "be":
                            hh = np.flatnonzero((c[lo_be:stop + 1] < thr_be * (1 + par[1])) & bs[lo_be:stop + 1]); v = lo_be + int(hh[0]) if len(hh) else None
                        elif t_ == "nh":
                            v = nh[par[1]]
                        elif t_ == "w2":
                            v = first(POS["W2"], lo_)
                        elif t_ == "end":
                            v = None
                        else:
                            a_, b_ = dd[par[1]], nh[par[2]]; v = min(x for x in (a_, b_, n + 99) if x is not None); v = None if v == n + 99 else v
                        out[name] = v
                    return out
                d1 = first(POS["W1"], e)
                tid = len(TRS)
                rec = {"tid": tid, "m": m, "s": s, "d": d, "e": e, "bp": bp, "stop": stop, "P*": Ps, "c_P": c[Ps], "未完": opn, "進場月": mon[e], "px_end": pend,
                       "d1": -1 if d1 is None else d1, "群": "乙" if d1 is None else "甲"}
                if d1 is not None:
                    ex1 = nxo[d1 + 1]; sp1 = o[ex1] if ex1 <= t1 else c[t1]
                    later = c[d1 + 1:stop + 1].max() if d1 < stop else -np.inf
                    rec.update({"sp1": sp1, "再漲": int(later > c[e:d1 + 1].max() and later > sp1 * 1.10)})
                    for name, v in run_rules(RA, d1, int(min(ex1, stop + 1)), sp1).items():
                        RR.append((tid, "甲", name, int(v is not None), -1 if v is None else v, pend if v is None else px_of(v), np.nan))
                for name, v in run_rules(RB, e, e, bp).items():
                    wrong = float((c[v + 1:stop + 1] > bp).any()) if v is not None and v < stop else 0.0
                    RR.append((tid, "乙", name, int(v is not None), -1 if v is None else v, pend if v is None else px_of(v), wrong))
                TRS.append(rec); nxt_free = stop; nt += 1
        log(f"[B'] ≥{m} 個：{nt:,} 筆")
    T = pd.DataFrame(TRS)
    R = pd.DataFrame(RR, columns=["tid", "規則組", "規則", "觸發", "ds", "px", "賣錯"])
    return T, R


def seg_mask(T, sg):
    if sg == "探索":
        return (T["進場月"] >= EXP[0]) & (T["進場月"] <= EXP[1])
    if sg == "確認":
        return T["進場月"] >= CON[0]
    return pd.Series(True, index=T.index)


def frames(T, R):
    """⇒ A（甲群 × 甲規則，含整筆）、B（全部筆 × 乙規則，含乙群報酬、誤殺、套全部筆報酬）"""
    TI = T.set_index("tid")
    A = R[R["規則組"] == "甲"].merge(T[["tid", "m", "進場月", "bp", "sp1", "c_P", "再漲"]], on="tid")
    r5 = A[A["規則"] == R5A].set_index("tid")["px"]; A["px_R5"] = A["tid"].map(r5)
    A["出場÷W1賣價−1"] = A["px"] / A["sp1"] - 1; A["出場÷真頂"] = A["px"] / A["c_P"]; A["對現行差"] = (A["px"] - A["px_R5"]) / A["bp"]
    A["整筆報酬"] = 0.3 * A["sp1"] / A["bp"] + 0.7 * A["px"] / A["bp"] - 1
    A["整筆吃到真頂"] = (0.3 * (A["sp1"] - A["bp"]) + 0.7 * (A["px"] - A["bp"])) / (A["c_P"] - A["bp"]); A["denok"] = (A["c_P"] - A["bp"]) >= 0.05 * A["bp"]
    cur = A[A["規則"] == R5A].set_index("tid")["整筆報酬"]
    B = R[R["規則組"] == "乙"].merge(T[["tid", "m", "進場月", "bp", "群", "d1", "px_end"]], on="tid")
    B["出場報酬"] = B["px"] / B["bp"] - 1; B["對現行差"] = (B["px"] - B["px_end"]) / B["bp"]
    B["誤殺"] = np.where(B["群"] == "甲", ((B["觸發"] == 1) & (B["ds"] < B["d1"])).astype(float), np.nan)
    curall = np.where(B["群"] == "甲", B["tid"].map(cur), B["px_end"] / B["bp"] - 1)
    B["套全部 報酬"] = np.where((B["群"] == "乙") | (B["誤殺"] == 1), B["出場報酬"], curall); B["套全部 差"] = B["套全部 報酬"] - curall
    return A, B


def summarize(T, A, B):
    SA = []; SB = []
    for m in MS:
        for sg in ("探索", "確認", "全部"):
            ids = set(T.loc[(T["m"] == m) & seg_mask(T, sg), "tid"]); NT = len(ids)
            a = A[A["tid"].isin(ids)]; b = B[B["tid"].isin(ids)]
            for name, fam, par in RA:
                x = a[a["規則"] == name]
                for sub, xx in (("全部", x), ("有再漲", x[x["再漲"] == 1]), ("沒再漲", x[x["再漲"] == 0])):
                    if not len(xx):
                        continue
                    r = {"m": m, "段": sg, "族": fam, "規則": name, "子群": sub, "全部筆": NT, "甲群筆": int((x["tid"].size)), "筆數": len(xx), "占甲群": len(xx) / max(len(x), 1),
                         "觸發比例": xx["觸發"].mean(), "出場÷W1賣價−1 中位": xx["出場÷W1賣價−1"].median(), "出場÷W1賣價−1 平均": xx["出場÷W1賣價−1"].mean(),
                         "出場÷真頂 中位": xx["出場÷真頂"].median(), "對現行差 中位": xx["對現行差"].median(), "對現行差 平均": xx["對現行差"].mean(),
                         "整筆報酬 中位": xx["整筆報酬"].median(), "整筆報酬 平均": xx["整筆報酬"].mean(),
                         "整筆吃到真頂 中位": xx["整筆吃到真頂"].median(), "整筆吃到真頂 平均": xx.loc[xx["denok"], "整筆吃到真頂"].mean()}
                    if sub == "沒再漲":
                        r["少虧（平均）"] = xx["對現行差"].mean()
                    if sub == "有再漲":
                        r["少賺（平均）"] = -xx["對現行差"].mean()
                    SA.append(r)
            for name, fam, par in RB:
                x = b[b["規則"] == name]; yb = x[x["群"] == "乙"]; ya = x[x["群"] == "甲"]; rt = yb["出場報酬"]
                SB.append({"m": m, "段": sg, "族": fam, "規則": name, "全部筆": NT, "乙群筆": len(yb), "觸發比例": yb["觸發"].mean(),
                           **{f"出場報酬 {q}": rt.quantile(v) for q, v in (("p10", .1), ("p25", .25), ("中位", .5), ("p75", .75), ("p90", .9))}, "出場報酬 平均": rt.mean(),
                           "虧損比例": (rt < 0).mean(), "虧損筆虧損中位": rt[rt < 0].median(), "賣錯": yb["賣錯"].mean(),
                           "對現行差 中位": yb["對現行差"].median(), "對現行差 平均": yb["對現行差"].mean(),
                           "誤殺（甲群在W1前被賣）": ya["誤殺"].mean(), "套全部筆 報酬中位": x["套全部 報酬"].median(), "套全部筆 報酬平均": x["套全部 報酬"].mean(),
                           "套全部筆 對現行差 中位": x["套全部 差"].median(), "套全部筆 對現行差 平均": x["套全部 差"].mean()})
    return pd.DataFrame(SA), pd.DataFrame(SB)


def shortlist(SA, SB):
    SL = []
    for m in MS:
        x = SA[(SA["m"] == m) & (SA["段"] == "探索") & (SA["子群"] == "全部")].sort_values("整筆吃到真頂 中位", ascending=False, kind="mergesort").head(5)
        SL += [{"m": m, "群": "甲", "名次": i + 1, "規則": nm, "探索值": v} for i, (nm, v) in enumerate(zip(x["規則"], x["整筆吃到真頂 中位"]))]
        y = SB[(SB["m"] == m) & (SB["段"] == "探索")].copy()
        y["rk"] = y["出場報酬 中位"].rank(ascending=False, method="min") + y["賣錯"].rank(ascending=True, method="min")
        y = y.sort_values(["rk", "出場報酬 中位"], ascending=[True, False], kind="mergesort").head(5)
        SL += [{"m": m, "群": "乙", "名次": i + 1, "規則": nm, "探索值": v} for i, (nm, v) in enumerate(zip(y["規則"], y["rk"]))]
    return pd.DataFrame(SL)


def _cb(v, mon, rng, B=2000):
    ok = np.isfinite(v); v = v[ok]; mon = mon[ok]; um = np.unique(mon)
    if len(v) < 10:
        return len(v), (v.mean() if len(v) else np.nan), np.nan, np.nan
    sums = np.array([v[mon == u].sum() for u in um]); cnts = np.array([(mon == u).sum() for u in um])
    bs = [sums[k].sum() / cnts[k].sum() for k in (rng.integers(0, len(um), len(um)) for _ in range(B))]
    return len(v), v.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def boot(T, A, B, SL):
    rng = np.random.default_rng(20260930); out = []
    for m in MS:
        ids = set(T.loc[(T["m"] == m) & seg_mask(T, "確認"), "tid"])
        a = A[A["tid"].isin(ids) & A["denok"]]; cur = a[a["規則"] == R5A].set_index("tid")["整筆吃到真頂"]
        for nm in SL.loc[(SL["m"] == m) & (SL["群"] == "甲"), "規則"]:
            x = a[a["規則"] == nm]; v = (x["整筆吃到真頂"] - x["tid"].map(cur)).to_numpy(float)
            k, mu, lo, hi = _cb(v, x["進場月"].to_numpy(), rng)
            out.append({"m": m, "群": "甲", "規則": nm, "項": "整筆吃到真頂 對現行差", "n": k, "平均差": mu, "lo": lo, "hi": hi})
            a2 = A[A["tid"].isin(ids)]; cr = a2[a2["規則"] == R5A].set_index("tid")["整筆報酬"]; x = a2[a2["規則"] == nm]     # E8
            k, mu, lo, hi = _cb((x["整筆報酬"] - x["tid"].map(cr)).to_numpy(float), x["進場月"].to_numpy(), rng)
            out.append({"m": m, "群": "甲", "規則": nm, "項": "整筆報酬 對現行差（E8）", "n": k, "平均差": mu, "lo": lo, "hi": hi})
        b = B[B["tid"].isin(ids)]
        for nm in SL.loc[(SL["m"] == m) & (SL["群"] == "乙"), "規則"]:
            x = b[(b["規則"] == nm) & (b["群"] == "乙")]
            k, mu, lo, hi = _cb(x["對現行差"].to_numpy(float), x["進場月"].to_numpy(), rng)
            out.append({"m": m, "群": "乙", "規則": nm, "項": "乙群出場報酬 對現行差", "n": k, "平均差": mu, "lo": lo, "hi": hi})
            x = b[b["規則"] == nm]
            k, mu, lo, hi = _cb(x["套全部 差"].to_numpy(float), x["進場月"].to_numpy(), rng)
            out.append({"m": m, "群": "乙", "規則": nm, "項": "套全部筆整筆報酬 對現行差", "n": k, "平均差": mu, "lo": lo, "hi": hi})
    return pd.DataFrame(out)


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    C, O, M = build(uni, cal, n, bar, t1, log)
    T, R = trades(uni, n, bar, inseg, t1, C, O, M, mon, log)
    T.to_csv(os.path.join(OUT, "trades.csv.gz"), index=False, float_format="%.10g"); R.to_csv(os.path.join(OUT, "trade_rules.csv.gz"), index=False, float_format="%.10g")
    A, B = frames(T, R)
    SA, SB = summarize(T, A, B); SA.to_csv(os.path.join(OUT, "summary_甲_剩7成.csv"), index=False, float_format="%.5g"); SB.to_csv(os.path.join(OUT, "summary_乙_沒漲起來.csv"), index=False, float_format="%.5g")
    SL = shortlist(SA, SB); SL.to_csv(os.path.join(OUT, "shortlist.csv"), index=False, float_format="%.5g")
    BT = boot(T, A, B, SL); BT.to_csv(os.path.join(OUT, "boot_confirm.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "m": list(MS), "甲規則數": len(RA), "乙規則數": len(RB),
            "筆數": {str(m): {"全部": int((T["m"] == m).sum()), "甲": int(((T["m"] == m) & (T["群"] == "甲")).sum())} for m in MS}, "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[完] {time.time() - T0:.0f}s")


def page(log):
    SA = pd.read_csv(os.path.join(OUT, "summary_甲_剩7成.csv")); SB = pd.read_csv(os.path.join(OUT, "summary_乙_沒漲起來.csv"))
    SL = pd.read_csv(os.path.join(OUT, "shortlist.csv")); BT = pd.read_csv(os.path.join(OUT, "boot_confirm.csv"))
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CKJ = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal;min-width:9em}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}"
            ".sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}.big{font-size:1.05rem}li{margin:.35em 0}")
    P_ = ED.P_
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    ci = lambda r: "—" if r is None else f"{PT(r['平均差'])}<br><small>{r['lo'] * 100:+.1f}～{r['hi'] * 100:+.1f}</small>"
    cis = lambda r: f"{PT(r['平均差'])}（95% {r['lo'] * 100:+.1f}～{r['hi'] * 100:+.1f}）"

    def bt(m, g, nm, item):
        x = BT[(BT["m"] == m) & (BT["群"] == g) & (BT["規則"] == nm) & (BT["項"] == item)]
        return None if not len(x) else x.iloc[0]
    ga = lambda m, sg, nm, sub="全部": SA[(SA["m"] == m) & (SA["段"] == sg) & (SA["規則"] == nm) & (SA["子群"] == sub)].iloc[0]
    gb = lambda m, sg, nm: SB[(SB["m"] == m) & (SB["段"] == sg) & (SB["規則"] == nm)].iloc[0]
    m0 = 7; sg0 = "確認"
    ta = SL[(SL["m"] == m0) & (SL["群"] == "甲")].sort_values("名次").iloc[0]["規則"]; tb = SL[(SL["m"] == m0) & (SL["群"] == "乙")].sort_values("名次").iloc[0]["規則"]
    a1, a0, a30 = ga(m0, sg0, ta), ga(m0, sg0, R5A), ga(m0, sg0, R5A0)
    au, ad = ga(m0, sg0, ta, "有再漲"), ga(m0, sg0, ta, "沒再漲")
    b1, b0 = gb(m0, sg0, tb), gb(m0, sg0, R5B)
    bra = bt(m0, "甲", ta, "整筆報酬 對現行差（E8）"); brc = bt(m0, "甲", ta, "整筆吃到真頂 對現行差")
    bbb = bt(m0, "乙", tb, "乙群出場報酬 對現行差"); bba = bt(m0, "乙", tb, "套全部筆整筆報酬 對現行差")
    same = {R5B, "R1 從進場後高回落30%"}                                              # 回落 30% ＝ 現行，不算候選
    X = SB[(SB["m"] == m0) & (SB["段"] == sg0) & ~SB["規則"].isin(same)]; XE = SB[(SB["m"] == m0) & (SB["段"] == "探索") & ~SB["規則"].isin(same)]
    lc = XE.sort_values("套全部筆 對現行差 平均", ascending=False).iloc[0]["規則"]; lcc = gb(m0, sg0, lc); lce = gb(m0, "探索", lc)
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>賣3成後剩下怎麼出場</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>W1 賣 3 成之後，剩下 7 成怎麼出場？沒漲起來的怎麼出場？（起漲訊號買進，2021–2026-08）</h1>",
         "<p class='warn'>⚠ 只當參考，沒有計入檢定數；看過前兩份（topwarn、w1better）之後才加的題。每個出場規則都是當天收盤能判斷、隔天開盤賣；"
         "版本在探索段（2021–2023）排名選出，確認段（2024–2026-08）只照報。沒有用「抱固定天數」當對照。</p>",
         f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}（補充一次見文末）。進場 ＝ 14 個起漲特徵同時 ≥ m 個、隔天開盤買；現行流程 ＝ W1 第一次出現隔天賣 3 成，"
         "剩下等 W2 或從最高回落 30%；W1 一直沒出現的筆，等回落 30%。"
         + (f"查核：抽 200 筆逐日重算 {CKJ['抽 200 筆不同']} 筆不同；與前兩份的筆、W1、W2 對帳 {CKJ['對帳不同']} 處不同。" if CKJ else "") + "</p>",
         f"<h2>先講結論（確認段，m＝{m0}；m＝5、10 方向相同）</h2>",
         f"<div class='ok big'><b>一句話</b>：剩 7 成改用「{html.escape(ta)}」出場，一般的一筆吃到真頂從 {P_(a0['整筆吃到真頂 中位'])} 變 {P_(a1['整筆吃到真頂 中位'])}，"
         f"但會放掉大飆股的後段，整筆報酬平均反而少 {-bra['平均差'] * 100:.0f} 點；沒漲起來的筆<b>當下認不出來</b>，任何提早停損都會把之後才漲的好股一起砍掉，"
         f"平均算下來都比現行（回落 30%）差 —— 若一定要設停損，「{html.escape(lc)}」代價最小。</div><ul class='big'>",
         f"<li><b>剩 7 成（W1 有出現，{int(a1['筆數']):,} 筆）</b>：探索段排名第一的是「{html.escape(ta)}」。確認段整筆（3 成 W1 ＋ 7 成規則）吃到真頂中位 {P_(a1['整筆吃到真頂 中位'])}"
         f"（現行 {P_(a0['整筆吃到真頂 中位'])}），剩下那 7 成的出場價比 W1 賣價 {P_(a1['出場÷W1賣價−1 中位'])}（現行 {P_(a0['出場÷W1賣價−1 中位'])}）。</li>",
         f"<li><b>代價</b>：W1 之後還有 {P_(au['占甲群'])} 的筆會再漲（又創新高且超過 W1 賣價 10%）。這些筆那 7 成（每 1 元買價）少賺 {au['少賺（平均）'] * 100:.0f} 點，"
         f"沒再漲的少虧 {ad['少虧（平均）'] * 100:.0f} 點 ⇒ 整筆報酬中位 {P_(a1['整筆報酬 中位'])}（現行 {P_(a0['整筆報酬 中位'])}），"
         f"平均 {P_(a1['整筆報酬 平均'])}（現行 {P_(a0['整筆報酬 平均'])}；差 {cis(bra)}）。"
         f"只等回落 30%（連 W2 都不等）平均 {P_(a30['整筆報酬 平均'])}，平均最高，但吃到真頂中位只有 {P_(a30['整筆吃到真頂 中位'])}。</li>",
         f"<li><b>沒漲起來（W1 一直沒出現，{int(b1['乙群筆']):,} 筆）</b>：現行（回落 30%）出場報酬中位 {P_(b0['出場報酬 中位'])}；探索段排名第一的「{html.escape(tb)}」"
         f"中位 {P_(b1['出場報酬 中位'])}、虧損筆的虧損中位 {P_(b1['虧損筆虧損中位'])}（現行 {P_(b0['虧損筆虧損中位'])}），平均多 {cis(bbb)}；但賣後又漲回進場價以上（賣錯）{P_(b1['賣錯'])}。</li>",
         f"<li><b>但「沒漲起來」是事後才知道的</b>：同一條規則從進場日就套上去，後來會出現 W1 的好股有 {P_(b1['誤殺（甲群在W1前被賣）'])} 在 W1 之前就被賣掉；"
         f"套在全部筆上，整筆報酬平均比現行 {cis(bba)}。所有候選（回落 30% 本身就是現行，不算）套全部筆的平均都比現行差（{PT(X['套全部筆 對現行差 平均'].min())}～{PT(X['套全部筆 對現行差 平均'].max())}）；"
         f"代價最小的是「{html.escape(lc)}」（探索段也是最小；確認段 {PT(lcc['套全部筆 對現行差 平均'])}、誤殺 {P_(lcc['誤殺（甲群在W1前被賣）'])}，"
         f"虧損筆虧損中位 {P_(lcc['虧損筆虧損中位'])}）。這不是探索段排名選出的，只是描述。</li></ul>"]
    # 表一 甲
    H.append("<h2>一、剩 7 成：探索段前 5 名到確認段</h2><p class='note'>探索段依「整筆吃到真頂中位」排。對現行差 ＝ 同一筆和現行（等 W2 或回落 30%）比，平均，下方是依進場月分群的 95% 區間。"
             "少虧／少賺 ＝ 剩下那 7 成每 1 元本金的差（對現行）。</p>")
    H.append("<div class='sel'>m <select id='ma' onchange='sw(\"a\")'>" + "".join(f"<option>{m}</option>" for m in MS) + "</select></div>")
    for m in MS:
        H.append(f"<div class='pane pa' id='a{m}'><div class='wrap'><table><tr><th class='l'>規則</th><th>整筆吃到真頂<br><small>中位</small></th><th>對現行差<br><small>吃到真頂</small></th>"
                 "<th>整筆報酬<br><small>中位／平均</small></th><th>對現行差<br><small>整筆報酬</small></th><th>7 成出場價<br><small>比 W1 賣價</small></th><th>出場價<br><small>÷真頂</small></th>"
                 "<th>沒再漲<br><small>少虧</small></th><th>有再漲<br><small>少賺</small></th></tr>")
        for nm in [R5A, R5A0] + list(SL.loc[(SL["m"] == m) & (SL["群"] == "甲"), "規則"]):
            x = ga(m, sg0, nm); u = ga(m, sg0, nm, "有再漲"); d = ga(m, sg0, nm, "沒再漲")
            H.append(f"<tr><td class='l'>{html.escape(nm)}</td><td>{P_(x['整筆吃到真頂 中位'])}</td><td>{ci(bt(m, '甲', nm, '整筆吃到真頂 對現行差'))}</td>"
                     f"<td>{P_(x['整筆報酬 中位'])}<br><small>{P_(x['整筆報酬 平均'])}</small></td><td>{ci(bt(m, '甲', nm, '整筆報酬 對現行差（E8）'))}</td>"
                     f"<td>{P_(x['出場÷W1賣價−1 中位'])}</td><td>{P_(x['出場÷真頂 中位'])}</td><td>{PT(d['少虧（平均）'])}</td><td>{PT(u['少賺（平均）'])}</td></tr>")
        x0 = ga(m, sg0, R5A)
        H.append(f"</table></div><p class='note'>確認段 W1 有出現 {int(x0['筆數']):,} 筆，其中有再漲 {P_(ga(m, sg0, R5A, '有再漲')['占甲群'])}。</p></div>")
    # 表二 乙
    H.append("<h2>二、沒漲起來：探索段前 5 名到確認段</h2><p class='note'>探索段依「出場報酬中位的名次 ＋ 賣錯率的名次」排。誤殺 ＝ 同一條規則套在後來會出現 W1 的筆上，W1 之前就被賣掉的比例；"
             "套全部筆 ＝ 當下不知道會不會出現 W1，規則先到就整筆賣、否則照現行（3 成 W1 ＋ 7 成等 W2 或回落 30%）。</p>")
    H.append("<div class='sel'>m <select id='mb' onchange='sw(\"b\")'>" + "".join(f"<option>{m}</option>" for m in MS) + "</select></div>")
    for m in MS:
        H.append(f"<div class='pane pb' id='b{m}'><div class='wrap'><table><tr><th class='l'>規則</th><th>出場報酬<br><small>中位</small></th><th>虧損比例</th><th>虧損筆<br><small>虧損中位</small></th><th>賣錯</th>"
                 "<th>對現行差<br><small>沒漲起來的筆</small></th><th>誤殺</th><th>對現行差<br><small>套全部筆</small></th></tr>")
        for nm in [R5B] + list(SL.loc[(SL["m"] == m) & (SL["群"] == "乙"), "規則"]):
            x = gb(m, sg0, nm)
            H.append(f"<tr><td class='l'>{html.escape(nm)}</td><td>{P_(x['出場報酬 中位'])}</td><td>{P_(x['虧損比例'])}</td><td>{P_(x['虧損筆虧損中位'])}</td><td>{P_(x['賣錯'])}</td>"
                     f"<td>{ci(bt(m, '乙', nm, '乙群出場報酬 對現行差'))}</td><td>{P_(x['誤殺（甲群在W1前被賣）'])}</td><td>{ci(bt(m, '乙', nm, '套全部筆整筆報酬 對現行差'))}</td></tr>")
        H.append(f"</table></div><p class='note'>確認段 W1 沒出現 {int(gb(m, sg0, R5B)['乙群筆']):,} 筆。</p></div>")
    # 表三 全部
    H.append("<h2>三、全部版本（每個版本都報）</h2><div class='sel'>m <select id='mc' onchange='sw(\"c\")'>" + "".join(f"<option>{m}</option>" for m in MS)
             + "</select>段 <select id='sc' onchange='sw(\"c\")'><option>確認</option><option>探索</option><option>全部</option></select></div>")
    for m in MS:
        for sg in ("確認", "探索", "全部"):
            H.append(f"<div class='pane pc' id='c{m}_{sg}'><h3>剩 7 成（W1 有出現）</h3><div class='wrap'><table><tr><th class='l'>規則</th><th>規則有觸發</th><th>整筆吃到真頂<br><small>中位／平均</small></th>"
                     "<th>整筆報酬<br><small>中位／平均</small></th><th>7 成出場價<br><small>比 W1 賣價 中位／平均</small></th><th>出場價÷真頂</th><th>對現行差<br><small>中位／平均</small></th><th>沒再漲 少虧</th><th>有再漲 少賺</th></tr>")
            for nm, fam, par in RA:
                x = ga(m, sg, nm); u = ga(m, sg, nm, "有再漲"); d = ga(m, sg, nm, "沒再漲")
                H.append(f"<tr><td class='l'>{html.escape(nm)}</td><td>{P_(x['觸發比例'])}</td><td>{P_(x['整筆吃到真頂 中位'])}<br><small>{P_(x['整筆吃到真頂 平均'])}</small></td>"
                         f"<td>{P_(x['整筆報酬 中位'])}<br><small>{P_(x['整筆報酬 平均'])}</small></td><td>{P_(x['出場÷W1賣價−1 中位'])}<br><small>{P_(x['出場÷W1賣價−1 平均'])}</small></td>"
                         f"<td>{P_(x['出場÷真頂 中位'])}</td><td>{PT(x['對現行差 中位'])}<br><small>{PT(x['對現行差 平均'])}</small></td><td>{PT(d['少虧（平均）'])}</td><td>{PT(u['少賺（平均）'])}</td></tr>")
            H.append("</table></div><h3>沒漲起來（W1 沒出現）</h3><div class='wrap'><table><tr><th class='l'>規則</th><th>規則有觸發</th><th>出場報酬<br><small>p10／p25</small></th><th>中位</th><th>p75／p90</th><th>平均</th>"
                     "<th>虧損比例</th><th>虧損筆虧損中位</th><th>賣錯</th><th>對現行差<br><small>中位／平均</small></th><th>誤殺</th><th>套全部筆<br><small>報酬中位／平均</small></th><th>套全部筆對現行差<br><small>中位／平均</small></th></tr>")
            for nm, fam, par in RB:
                x = gb(m, sg, nm)
                H.append(f"<tr><td class='l'>{html.escape(nm)}</td><td>{P_(x['觸發比例'])}</td><td>{P_(x['出場報酬 p10'])}<br><small>{P_(x['出場報酬 p25'])}</small></td><td>{P_(x['出場報酬 中位'])}</td>"
                         f"<td>{P_(x['出場報酬 p75'])}<br><small>{P_(x['出場報酬 p90'])}</small></td><td>{P_(x['出場報酬 平均'])}</td><td>{P_(x['虧損比例'])}</td><td>{P_(x['虧損筆虧損中位'])}</td><td>{P_(x['賣錯'])}</td>"
                         f"<td>{PT(x['對現行差 中位'])}<br><small>{PT(x['對現行差 平均'])}</small></td><td>{P_(x['誤殺（甲群在W1前被賣）'])}</td>"
                         f"<td>{P_(x['套全部筆 報酬中位'])}<br><small>{P_(x['套全部筆 報酬平均'])}</small></td><td>{PT(x['套全部筆 對現行差 中位'])}<br><small>{PT(x['套全部筆 對現行差 平均'])}</small></td></tr>")
            H.append("</table></div></div>")
    H.append("<h2>名詞</h2><ul class='note'>"
             "<li>R1 ＝ 從最高收盤回落 y%（剩 7 成從 W1 之後算起；沒漲起來的從進場算起）。R2 ＝ 收盤向下跌破 MA10／20／60。R3 ＝ 收盤跌破 W1 賣價（或進場價）的某個百分比。"
             "R4 ＝ 連續 N 個交易日沒創新高。R5 ＝ 現行流程。R6 ＝ R1 和 R4 哪個先到就賣（全部組合都報）。規則一直沒觸發 ⇒ 照現行的回落 30% 出場。</li>"
             "<li>整筆吃到真頂 ＝ [0.3 ×（W1 賣價 − 買價）＋ 0.7 ×（剩下出場價 − 買價）] ÷（真頂 − 買價）；它把每一筆等權，小漲的筆和大飆股算一樣重，所以另報整筆報酬的平均。"
             "平均只算真頂比買價高 5% 以上的筆。</li>"
             "<li>有再漲 ＝ W1 之後又創新高，且超過 W1 賣價 10% 以上。賣錯 ＝ 規則賣掉之後，照現行抱著的話收盤又回到進場價以上。</li>"
             "<li>95% 區間 ＝ 依進場月份分群重抽 2000 次，只當描述。補充（2026-09-30 00:53，已看過數字）：加報「整筆報酬 對現行差」的區間，不改排名。</li></ul>")
    H.append("<script>function sw(k){var m=document.getElementById('m'+k).value,s=k=='c'?'_'+document.getElementById('sc').value:'';"
             "document.querySelectorAll('.p'+k).forEach(x=>x.classList.toggle('on',x.id==k+m+s))}"
             f"['a','b','c'].forEach(k=>{{document.getElementById('m'+k).value='{m0}';sw(k)}})</script></main></body></html>")
    open(os.path.join(OUT, "賣3成後剩下怎麼出場.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def check(log):
    """E6：m＝7 抽 200 筆逐日迴圈重算；另對帳 w1better。"""
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    att = np.asarray(Qm[FX["att_10"]]); lu5 = np.asarray(Qm[FX["lu_5"]]); r5 = np.asarray(Qm[FX["r_5"]]); d60 = np.asarray(Fm[FX["disp_60"]])
    T = pd.read_csv(os.path.join(OUT, "trades.csv.gz")); R = pd.read_csv(os.path.join(OUT, "trade_rules.csv.gz"))
    RI = R.set_index(["tid", "規則組", "規則"])
    CKA = {"R1 從W1後高回落10%": "y10", "R2 跌破MA20": "ma20", "R3 跌破W1賣價": "be", "R4 連10天沒創新高": "n10"}
    CKB = {"R1 從進場後高回落10%": "y10", "R2 跌破MA20": "ma20", "R3 跌破進場價−8%": "be", "R4 連10天沒創新高": "n10"}
    TB = T[T["m"] == 7].sample(200, random_state=20260930)
    D.DATA = S5.ST; errs = []; nd = 0; ntrig = {"甲": dict.fromkeys(CKA.values(), 0), "乙": dict.fromkeys(CKB.values(), 0)}; ngrp = {"甲": 0, "乙": 0}
    for r in TB.itertuples():
        s, e = int(r.s), int(r.e)
        df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
        c0 = df["close"].to_numpy(float); o0 = df["open"].to_numpy(float); cc = pd.Series(c0).ffill().to_numpy()
        isb = [bool(np.isfinite(c0[d]) and bar[s, d]) for d in range(n)]
        bars = [d for d in range(n) if isb[d]]; bpos = {d: j for j, d in enumerate(bars)}
        bp = o0[e]

        def px(d):
            x = d + 1
            while x <= t1 and not (np.isfinite(o0[x]) and o0[x] > 0 and bar[s, x]):
                x += 1
            return (o0[x] if x <= t1 else cc[t1]), x
        rm = -np.inf; stop = t1
        for d in range(e, t1 + 1):
            rm = max(rm, cc[d])
            if cc[d] <= rm * 0.7:
                stop = d; break
        Ps = e + int(np.argmax(cc[e:stop + 1]))

        def w1(d):
            if not isb[d]:
                return False
            j = bpos[d]
            return j >= 20 and c0[d] > max(c0[bars[j - 20:j]]) and att[s, d] == 5 and (lu5[s, d] == 5 or r5[s, d] == 5) and d60[s, d] == 0

        def ma(d, k):
            j = bpos[d]
            return sum(c0[bars[j - k + 1:j + 1]]) / k if j >= k - 1 else np.nan

        def xma(d, k):
            if not isb[d] or bpos[d] < k:
                return False
            p = bars[bpos[d] - 1]
            return c0[d] < ma(d, k) * (1 - 1e-9) and not (c0[p] < ma(p, k) * (1 - 1e-9))

        def rules(st0, lo_, lo_be, thr):
            got = {"y10": None, "ma20": None, "be": None, "n10": None}
            rmx = -np.inf; h = st0; cntb = 0
            for d in range(st0, stop + 1):
                if cc[d] > rmx:
                    rmx = cc[d]; h = d; cntb = 0
                elif isb[d]:
                    cntb += 1
                if d < lo_:
                    continue
                if got["y10"] is None and cc[d] <= rmx * 0.9:
                    got["y10"] = d
                if got["n10"] is None and cntb >= 10:
                    got["n10"] = d
                if got["ma20"] is None and xma(d, 20):
                    got["ma20"] = d
            got["be"] = next((d for d in range(lo_be, stop + 1) if isb[d] and cc[d] < thr), None)
            return got
        why = []
        if not (stop == int(r.stop) and Ps == int(r._8)):
            why.append("stop/P*")
        d1 = next((d for d in range(e, stop + 1) if w1(d)), None)
        grp = "乙" if d1 is None else "甲"; ngrp[grp] += 1
        if grp != r.群 or (d1 is not None and d1 != int(r.d1)):
            why.append("d1")
        pend = px(stop)[0]
        todo = [("乙", CKB, rules(e, e, e, bp * (1 - 0.08)))]
        if d1 is not None:
            sp1, ex1 = px(d1)
            if not np.isclose(sp1, r.sp1, rtol=1e-8):
                why.append("sp1")
            todo.append(("甲", CKA, rules(d1, d1 + 1, ex1, sp1)))
        for g, CK, got in todo:
            for nm, k in CK.items():
                rr = RI.loc[(r.tid, g, nm)]; v = got[k]
                if v is None:
                    if rr["觸發"] != 0 or not np.isclose(rr["px"], pend, rtol=1e-8):
                        why.append(f"{g} {k} 未觸發")
                    continue
                ntrig[g][k] += 1; p_ = px(v)[0]
                if not (rr["觸發"] == 1 and v == int(rr["ds"]) and np.isclose(rr["px"], p_, rtol=1e-8)):
                    why.append(f"{g} {k} {v}/{rr['ds']}")
                if g == "甲" and k == "y10":
                    cap = (0.3 * (sp1 - bp) + 0.7 * (p_ - bp)) / (cc[Ps] - bp)
                    capf = (0.3 * (r.sp1 - r.bp) + 0.7 * (rr["px"] - r.bp)) / (r.c_P - r.bp)
                    if not np.isclose(cap, capf, rtol=1e-6, atol=1e-8):
                        why.append("甲 整筆吃到真頂")
        if why:
            nd += 1; errs.append(f"tid {r.tid}：{'；'.join(why)}")
    log(f"[查核] 抽 200 筆不同 {nd}｜甲 {ngrp['甲']} 乙 {ngrp['乙']}｜觸發 {ntrig}")
    # 對帳 w1better
    WT = pd.read_csv("backtest/resultsSurge6/w1better/trades.csv.gz"); WR = pd.read_csv("backtest/resultsSurge6/w1better/trade_rules.csv.gz")
    wb = WR[WR["規則"] == "W1 基本版"].set_index("tid"); WT["d1"] = np.where(WT["tid"].map(wb["觸發"]) == 1, WT["tid"].map(wb["ds"]), -1)
    rec = {}
    for m in MS:
        a = T[T["m"] == m].set_index(["s", "e"])[["d1"]]; b = WT[WT["m"] == m].set_index(["s", "e"])[["d1"]]
        j = a.join(b, rsuffix="_w", how="outer")
        rec[str(m)] = {"本檔筆": len(a), "w1better 筆": len(b), "筆不同": int(j.isna().any(axis=1).sum()), "d1 不同": int((j["d1"] != j["d1_w"]).sum())}
    nbad = sum(v["筆不同"] + v["d1 不同"] for v in rec.values())
    log(f"[對帳 w1better] {rec}")
    # 對帳 topwarn 的 W2（m＝7）：topwarn 記 [e, stop] 內第一次 W2a、W2b；兩者較早者 ＞ d1 的甲群筆，R5 觸發日應相同；兩者都沒有 ⇒ R5 不觸發
    TW = pd.read_csv("backtest/resultsSurge6/topwarn/check_Bp_m7.csv.gz", usecols=["s", "e", "W2a 再次進入處置|日", "W2b 處置出關|日"])
    TW["w2"] = TW[["W2a 再次進入處置|日", "W2b 處置出關|日"]].min(axis=1)
    a7 = T[(T["m"] == 7) & (T["群"] == "甲")].merge(TW, on=["s", "e"], how="left")
    r5 = R[(R["規則組"] == "甲") & (R["規則"] == R5A)].set_index("tid"); a7["r5ds"] = a7["tid"].map(r5["ds"]); a7["r5trig"] = a7["tid"].map(r5["觸發"])
    none = a7["w2"].isna(); after = a7["w2"] > a7["d1"]
    w2bad = int((none & (a7["r5trig"] != 0)).sum() + (after & ((a7["r5trig"] != 1) | (a7["r5ds"] != a7["w2"]))).sum())
    w2rec = {"甲群筆": len(a7), "可比（topwarn 無 W2）": int(none.sum()), "可比（第一次 W2 在 d1 之後）": int(after.sum()), "不同": w2bad}
    nbad += w2bad
    log(f"[對帳 topwarn W2] {w2rec}")
    rec["topwarn W2（m＝7）"] = w2rec
    out = {"讀法寫死": TIME, "抽樣": "m＝7 抽 200 筆（random_state 20260930）", "重算": {"甲": list(CKA), "乙": list(CKB), "另": ["stop", "P*", "d1", "sp1", "30% 結束價", "甲 R1 10% 整筆吃到真頂"]},
           "抽 200 筆不同": nd, "甲乙筆數": ngrp, "各規則觸發筆": ntrig, "不同的筆": errs[:20], "對帳 w1better": rec, "對帳不同": nbad, "通過": nd == 0 and nbad == 0}
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
