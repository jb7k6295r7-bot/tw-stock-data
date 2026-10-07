# -*- coding: utf-8 -*-
"""飆股 seq6 描述追加：14 個起漲特徵的「同時符合幾個」表，加上 F4（連續虧損）重跑（使用者直接問；描述、參考、⛔ 不計 N、⛔ 不判定）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_featF4            # 本體＋網頁
    ...                                                              -m backtest.researchSurge6_featF4 page       # 只重做網頁
    ...                                                              -m backtest.researchSurge6_featF4 --check    # 獨立寫法抽樣重算

使用者原話：「當初的起漲特徵資料還在吧？加上F4後條件我看一下，再重跑一次」

═══ 讀法（寫死於 2026-10-07 07:58（台北），在算任何 F4 版數字之前；⛔ 寫死前只看過 2026-09-29 當時的舊數字）═══
 F0 舊數字出處：2026-09-29 協調者 session 的臨時程式（/tmp/perday.py、/tmp/unify.py＋unify2.py、/tmp/t15.py；沒存檔、沒 commit；
    程式與輸出從該 session 紀錄逐字找回）。本檔把三支的算法原樣搬進來（R 標），先重現舊數字（閘門），再加 F4。⛔ 不改原程式與原結果夾。
 R1 起漲特徵 ＝ researchSurge6_overlap.FEATS（14 個；s5work Q 表碼相等 ＝ 有；沒有值算沒有）；k ＝ 當天收盤同時符合的個數（0～14）
    資料、母體、日曆 ＝ researchSurge6_overlap.load()（s5 名單 2,203 檔＝全部上市櫃普通股含下市；stitch 日曆；bar ＝ 有 K 棒）
 R2 每天幾檔（＝ perday.py）：某段每個交易日（該日至少一檔有 K 棒），有 K 棒且符合條件的檔數；報平均、中位、p10、p90（不去重）
 R3 變飆股比例（＝ unify.py／unify2.py）：股-日 (s, d)：有 K 棒、d 在 2021-01～2026-08、seq6 右截斷定義域 hdef6 ≥ H、還原收盤（ffill）有值；
    標籤 ＝ (d, d＋H] 內最高收盤 ≥ c[d] ×（1＋g）×（1 − 1e−9）；H ∈ 10～250（每 10）、g ∈ {50%,100%,150%,200%,250%,300%,400%,500%,700%,1000%}
    格 ＝ 舊程式同一批：兩段合併、全部上市櫃、全部 k 的標籤數 ≥ 1,500 的格（舊 167 格；閘門要相同）；⛔ 不挑格、各組都用同一批格
    每格：比例 ＝ 該組標籤數 ÷ 該組股-日數；彙總 ＝ 格中位（附 p10～p90；該組在某格 0 股-日 ⇒ 該格不算）
    倍數 ＝ 各格（該組比例 ÷ 同段同版本「全部股票」比例）的格中位；「全部股票」＝ 不看特徵、不看 F4 的同一定義域
    ⛔ 不寫「N 天漲一倍」：飆股固定 ＝ seq6 網格、取格中位
 R4 多久漲 15%、先跌 15%（＝ t15.py）：股-日 d：有 K 棒、d 在 2021-01～2026-08、收盤有值；看 c[d＋1 … d＋250]（還原收盤 ffill，到資料尾為止）
    同一檔連續出現只取第一天：在該股有效 K 棒序列上，與上一個符合日相隔 ＞ 20 根才算新的（每個條件各自去重）
    20／60／120／250 日內漲 15% ＝ 觀察窗 ≥ h 的筆數中，h 日內收盤 ≥ c[d] × 1.15 的比例；中位天數 ＝ 觀察窗滿 250 且有漲到者，第一次 ≥ 1.15 的天數中位（p25、p75）
    先漲 15%／先跌 15% ＝ 觀察窗滿 250 的筆數中，先碰到 ≥ 1.15 ／先碰到 ≤ 0.85 的比例（都沒碰到 ⇒ 兩者都不算）
    「全部股票（不看特徵）」：舊程式是每檔隨機抽 2%（rng 0）、不去重 ⇒ 重現時照舊；新表的對照列改用全部股-日、不去重（同樣不去重，只是不抽樣）
 F1 F4（連續虧損）＝ researchMine X5：最近 4 季 EPS 合計 ＜ 0 且最近一季 ＜ 0（F4a）｜或最近 8 季 ≥ 6 季虧損（F4b）；季報可用日 A2 式；
    直接讀 ~/minework/flags_main.npz 逐月底判定（F4、F4_ok、EL）
 F2 判定時點（擇一，寫明）：股-日 d 的 F4 ＝ 嚴格早於 d 的最後一個月底判定日 m 的 F4（＝ researchMine Z2「m ＝ 嚴格 ＜ t 的最後一個月底」同式；point-in-time）
    ⛔ 不用逐日最新季報版。flags 名冊沒有這檔、或 m 時 F4 不可判 ⇒ 當「不帶 F4」（researchMine X7：不可判當沒旗），比例另報
 F3 分組：特徵數 k × {全部、帶 F4、不帶 F4}；另 k′ ＝ k ＋（帶 F4 ? 1 : 0）（F4 當第 15 個特徵，0～15）× 全部
    條件列：k（或 k′）逐個，加上分界 ≥5、5～9、5～10、≥9、≥10、≥11（k′ 的 5～10 不列）；另「不看特徵」× {全部、帶 F4、不帶 F4}
 F4 段（依 d 的月份）：探索 2021-01～2023-12、確認 2024-01～2026-08、合併（兩段加總）；版本：全部上市櫃（主）、W1 母體內（＝ m 時 EL；營量／營飆能買的）
    W1 版：每天幾檔、比例、去重都只在 W1 母體內的股-日上算；倍數的「全部股票」也換成 W1 母體內全部股-日
 F5 只描述：⛔ 不判定、⛔ 不計 N、⛔ 不轉成「能不能事先預測」、⛔ 不給買賣建議；用語一律「假訊號」
 F6 --check（獨立寫法，⛔ 不呼叫本檔本體函式）：從 Q 表逐特徵自算 k、從 flags_main.npz 用 pandas merge_asof 自找判定月；
    ① 抽 2 格（固定格集內、seed 20261007）逐股以 sliding_window_view 重算 N、L（兩版本、兩段、每個 (F4, k)）⇒ 比 cells.csv.gz，0 不同
    ② 抽 25 個交易日以 pandas groupby 重算每天各 (版本, F4, k) 檔數 ⇒ 比 perday.csv.gz，0 不同
    ③ 三個條件（k≥10∧帶F4、k≥10∧不帶F4、k′≥10）× 兩版本，逐股純 Python 迴圈找訊號、去重、往後逐日掃 ±15% ⇒ 比 t15.csv 的筆數、各比例、中位天數，0 不同
輸出 backtest/resultsSurge6/featF4/：repro.json、table_k.csv、table_kp.csv、cells.csv.gz、perday.csv.gz、t15.csv、meta.json、check.json、run.log、起漲特徵加連續虧損.html
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

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import researchSurge6_overlap as O

TIME = "2026-10-07 07:58（台北）"
OUT = "backtest/resultsSurge6/featF4"
FLAGS = os.path.expanduser("~/minework/flags_main.npz")
HS, GS = O.HS, O.GS
K = len(O.FEATS)
SEGN = ["探索", "確認"]; SEG3 = ["探索", "確認", "合併"]
SEGLAB = {"探索": "探索 2021-01～2023-12", "確認": "確認 2024-01～2026-08", "合併": "合併 2021-01～2026-08"}
VERN = ["全部上市櫃", "W1 母體內"]
F4N = ["全部", "帶 F4", "不帶 F4"]
F4SEL = {"全部": (0, 1), "帶 F4": (1,), "不帶 F4": (0,)}
HZ = [20, 60, 120, 250]
MINL = 1500
OLD = {  # 2026-09-29 舊數字（協調者 session 紀錄逐字）
    "每天（確認段）": {"≥5 中位": 268, "≥5 p10": 197, "≥5 p90": 368, "≥9 平均": 14.8, "≥10 平均": 5.1, "≥10 中位": 4, "≥10 p90": 11, "≥11 平均": 1.2, "5～10 平均": 274.4},
    "變飆股（合併、格中位）": {"格數": 167, "全部股票": 0.0129, "≥5": 0.023, "≥9": 0.040, "≥10": 0.047, "≥11": 0.043},
    "漲15%（合併）": {"≥10 筆數": 1844, "≥10 20日內": 0.36, "≥10 60日內": 0.56, "≥10 中位天數": 22, "≥10 先跌": 0.54,
                   "≥9 筆數": 3447, "≥5 筆數": 22794, "≥5 先跌": 0.36, "≥11 筆數": 655, "≥11 中位天數": 20, "≥11 先跌": 0.55,
                   "全部(抽2%) 筆數": 49317, "全部(抽2%) 20日內": 0.15, "全部(抽2%) 中位天數": 57, "全部(抽2%) 先跌": 0.38},
}


def ksets(fam):
    top = K + (1 if fam == "kp" else 0)
    L = [(f"{i} 個", (i,)) for i in range(top + 1)]
    L += [("5 個以上", tuple(range(5, top + 1))), ("5～9 個", tuple(range(5, 10)))]
    if fam == "k":
        L += [("5～10 個", tuple(range(5, 11)))]
    L += [("9 個以上", tuple(range(9, top + 1))), ("10 個以上", tuple(range(10, top + 1))), ("11 個以上", tuple(range(11, top + 1)))]
    return L


def groups():
    """t15 用的條件清單：(fam, k 名, kset, F4 名, 去重)。"""
    G = [("base", "不看特徵", tuple(range(K + 1)), f, False) for f in F4N]
    G += [("k", nm, ks, f, True) for nm, ks in ksets("k") for f in F4N]
    G += [("kp", nm, ks, "全部", True) for nm, ks in ksets("kp")]
    return G


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


# ═════════════ 載入 ═════════════
def f4_days(uni, cal, n):
    z = np.load(FLAGS)
    me = pd.to_datetime(z["me"]); mpos = cal.get_indexer(me)
    keep = mpos >= 0
    assert (me[~keep] > cal[-1]).all(), "⛔ 月底判定日對不到 stitch 日曆"
    mpos = mpos[keep]; F4 = z["F4"][keep]; OK = z["F4_ok"][keep]; EL = z["EL"][keep]
    six = {s: i for i, s in enumerate(z["sids"].tolist())}
    col = np.array([six.get(s, -1) for s in uni["stock_id"]])
    S = len(uni)
    jm = np.searchsorted(mpos, np.arange(n), side="left") - 1       # 嚴格 ＜ d 的最後一個月底
    F4d = np.zeros((S, n), bool); OKd = np.zeros((S, n), bool); ELd = np.zeros((S, n), bool)
    has = col >= 0
    for j in np.unique(jm[jm >= 0]):
        tt = np.flatnonzero(jm == j)
        for A, src in ((F4d, F4), (OKd, OK), (ELd, EL)):
            v = np.zeros(S, bool); v[has] = src[j, col[has]]
            A[:, tt] = v[:, None]
    return F4d, OKd, ELd, int((~has).sum())


def load_all():
    uni, cal, Qs, inseg, bar, h6, E = O.load()
    code = np.array([c for _, _, c in O.FEATS], np.int8)
    S, n = bar.shape
    sc = np.zeros((S, n), np.int8)
    for i in range(K):
        sc += (Qs[i] == code[i])
    del Qs
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    segd = np.full(n, -1, np.int8)
    segd[(mon >= 2021 * 12) & (mon <= 2023 * 12 + 11)] = 0
    segd[(mon >= 2024 * 12) & (mon <= 2026 * 12 + 7)] = 1
    assert ((segd >= 0) == inseg).all()
    F4d, OKd, ELd, nomiss = f4_days(uni, cal, n)
    return uni, cal, sc, inseg, bar, h6, segd, F4d, OKd, ELd, nomiss


# ═════════════ 本體 ═════════════
def body():
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchSurge6_featF4 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TIME} =====")
    uni, cal, sc, inseg, bar, h6, segd, F4d, OKd, ELd, nomiss = load_all()
    S, n = bar.shape
    log(f"[載入] 股 {S}、日 {n}；flags 名冊沒有的檔 {nomiss}")
    base_rows = bar & inseg[None, :]
    cov = {"段內有K棒股-日": int(base_rows.sum()), "F4 可判比例": float(OKd[base_rows].mean()), "帶 F4 比例": float(F4d[base_rows].mean()),
           "W1 母體內比例": float(ELd[base_rows].mean()), "W1 內帶 F4 比例": float(F4d[base_rows & ELd].mean())}
    log(f"[F4] {cov}")
    kc = (F4d.astype(np.int8) * (K + 1) + sc)                   # 0～29：F4*15 ＋ k
    # ── 每天幾檔 ──
    days = np.flatnonzero(inseg & bar.any(0))
    CNT = np.zeros((2, len(days), 2 * (K + 1)), np.int32)
    for v, msk in enumerate((bar, bar & ELd)):
        sub = np.where(msk[:, days], kc[:, days], -1)
        for c in range(2 * (K + 1)):
            CNT[v, :, c] = (sub == c).sum(0)
    PD = []
    for v in range(2):
        df = pd.DataFrame(CNT[v], columns=[f"F{c // (K + 1)}_k{c % (K + 1)}" for c in range(2 * (K + 1))])
        df.insert(0, "版本", VERN[v]); df.insert(0, "日期", [str(cal[t].date()) for t in days]); PD.append(df)
    pd.concat(PD).to_csv(os.path.join(OUT, "perday.csv.gz"), index=False)
    log("[每天] 完成")
    # ── 逐股：標籤（R3）與 t15（R4）──
    G = groups(); NG = len(G)
    MK = np.zeros((NG, K + 2), bool); MF = np.zeros((NG, 2), bool); FAM = np.array([g[0] == "kp" for g in G]); DED = np.array([g[4] for g in G])
    for gi, (fam, nm, ks, f, dd) in enumerate(G):
        MK[gi, list(ks)] = True; MF[gi, list(F4SEL[f])] = True
    N = np.zeros((2, len(HS), 60), np.int64); L = np.zeros((2, len(HS), len(GS), 60), np.int64)
    T_N = np.zeros((NG, 2, 2), np.int64); T_C = np.zeros((NG, 2, 2, len(HZ)), np.int64); T_U = np.zeros((NG, 2, 2, len(HZ)), np.int64)
    T_OK = np.zeros((NG, 2, 2), np.int64); T_FU = np.zeros((NG, 2, 2), np.int64); T_FD = np.zeros((NG, 2, 2), np.int64)
    T_H = np.zeros((NG, 2, 2, 251), np.int64)
    OLDS = {k: [] for k in ("≥10", "≥9", "≥5", "全部", "≥11", "≥12")}
    rng = np.random.default_rng(0)
    D.DATA = O.ST
    for s in range(S):
        if not (bar[s] & inseg).any():
            continue
        st = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal)
        if st is None:
            continue
        c = pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy()
        k = sc[s].astype(np.int64); f = F4d[s].astype(np.int64); el = ELd[s]
        sg = segd.astype(np.int64)
        cd = (sg * 2 + f) * (K + 1) + k
        rv = pd.Series(c[::-1])
        for hi, H in enumerate(HS):
            dm = bar[s] & inseg & (h6[s] >= H) & np.isfinite(c)
            if not dm.any():
                continue
            fmx = np.r_[rv.rolling(H, min_periods=H).max().to_numpy()[::-1][1:], np.nan]
            for v, m2 in enumerate((dm, dm & el)):
                if not m2.any():
                    continue
                r = fmx[m2] / c[m2]; cc = cd[m2]
                N[v, hi] += np.bincount(cc, minlength=60)
                for gi, g in enumerate(GS):
                    L[v, hi, gi] += np.bincount(cc[r >= (1 + g) * (1 - 1e-9)], minlength=60)
        # t15
        idx = np.flatnonzero(bar[s] & inseg & np.isfinite(c))
        if len(idx) < 2:
            continue
        cpad = np.r_[c, np.full(250, np.nan)]
        W = np.lib.stride_tricks.sliding_window_view(cpad[1:], 250)[idx]        # c[d+1 … d+250]
        base = c[idx][:, None]
        hu = W >= base * 1.15; hd = W <= base * 0.85
        up = np.where(hu.any(1), hu.argmax(1) + 1, 999); dn = np.where(hd.any(1), hd.argmax(1) + 1, 999)
        av = np.minimum(250, n - 1 - idx)
        # 舊 t15 重現（照舊：sc≥m 去重；全部 ＝ 抽 2%）
        smp = rng.random(len(idx)) < 0.02
        ki = k[idx]
        for key, mask, ded in (("≥10", ki >= 10, True), ("≥9", ki >= 9, True), ("≥5", ki >= 5, True), ("全部", smp, False), ("≥11", ki >= 11, True), ("≥12", ki >= 12, True)):
            p = np.flatnonzero(mask)
            if ded and len(p):
                p = p[np.r_[True, np.diff(p) > 20]]
            OLDS[key].append(np.c_[up[p], dn[p], av[p]])
        kv = np.where(FAM[:, None], (k + f)[idx][None, :], ki[None, :])          # (NG, m)
        A = MK[np.arange(NG)[:, None], kv] & MF[:, f[idx]]
        sgi = segd[idx].astype(np.int64)
        for v in range(2):
            Av = A if v == 0 else A & el[idx][None, :]
            for gi in np.flatnonzero(Av.any(1)):
                p = np.flatnonzero(Av[gi])
                if DED[gi]:
                    p = p[np.r_[True, np.diff(p) > 20]]
                u, d_, a_, q = up[p], dn[p], av[p], sgi[p]
                np.add.at(T_N[gi, v], q, 1)
                for hj, h in enumerate(HZ):
                    ok = a_ >= h
                    np.add.at(T_C[gi, v, :, hj], q[ok], 1); np.add.at(T_U[gi, v, :, hj], q[ok & (u <= h)], 1)
                ok = a_ >= 250
                np.add.at(T_OK[gi, v], q[ok], 1)
                np.add.at(T_FU[gi, v], q[ok & (u < d_)], 1); np.add.at(T_FD[gi, v], q[ok & (d_ < u)], 1)
                hit = ok & (u <= 250)
                np.add.at(T_H[gi, v], (q[hit], u[hit]), 1)
        if s % 300 == 0:
            log(f"[逐股] {s}/{S}")
    np.savez_compressed(os.path.join(OUT, "_raw.npz"), N=N, L=L, T_N=T_N, T_C=T_C, T_U=T_U, T_OK=T_OK, T_FU=T_FU, T_FD=T_FD, T_H=T_H, CNT=CNT, days=days)
    log("[逐股] 完成")
    # ── 格（舊規則）──
    Lall = L[0].reshape(len(HS), len(GS), 2, 2, K + 1).sum((2, 3, 4))
    cells = [(hi, gi) for hi in range(len(HS)) for gi in range(len(GS)) if Lall[hi, gi] >= MINL]
    log(f"[格] 標籤數 ≥ {MINL} 的格 {len(cells)}")
    # cells.csv.gz
    rows = []
    N5 = N.reshape(2, len(HS), 2, 2, K + 1); L5 = L.reshape(2, len(HS), len(GS), 2, 2, K + 1)
    for v in range(2):
        for hi, gi in cells:
            for sgx in range(2):
                for ff in range(2):
                    for kk in range(K + 1):
                        rows.append((VERN[v], SEGN[sgx], ff, kk, HS[hi], GS[gi], int(N5[v, hi, sgx, ff, kk]), int(L5[v, hi, gi, sgx, ff, kk])))
    pd.DataFrame(rows, columns=["版本", "段", "帶F4", "k", "H", "g", "股日數", "標籤數"]).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False)
    # ── 重現 ──
    rep = repro(CNT, days, segd, N5, L5, cells, OLDS)
    log(f"[重現] {json.dumps(rep, ensure_ascii=False)}")
    json.dump(rep, open(os.path.join(OUT, "repro.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # ── 主表 ──
    TK, T15 = tables(CNT, days, segd, N5, L5, cells, G, T_N, T_C, T_U, T_OK, T_FU, T_FD, T_H)
    TK.to_csv(os.path.join(OUT, "table_all.csv"), index=False, float_format="%.6g")
    TK[TK["家族"] != "k′"].to_csv(os.path.join(OUT, "table_k.csv"), index=False, float_format="%.6g")
    TK[TK["家族"] == "k′"].to_csv(os.path.join(OUT, "table_kp.csv"), index=False, float_format="%.6g")
    T15.to_csv(os.path.join(OUT, "t15.csv"), index=False)
    META = {"讀法寫死": TIME, "格數": len(cells), "格": [f"H{HS[h]}_g{int(round(GS[g] * 100))}%" for h, g in cells], "F4 覆蓋": cov,
            "flags 名冊沒有的檔": nomiss, "各段交易日數": {SEGN[i]: int((segd[days] == i).sum()) for i in range(2)}}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page()
    log("[完]")


def hist_med(h):
    """整數直方圖（索引 ＝ 天數）的中位、p25、p75（np.median／np.percentile 同義）。"""
    tot = int(h.sum())
    if tot == 0:
        return np.nan, np.nan, np.nan
    vals = np.repeat(np.arange(len(h)), h)
    return float(np.median(vals)), float(np.percentile(vals, 25)), float(np.percentile(vals, 75))


def repro(CNT, days, segd, N5, L5, cells, OLDS):
    con = segd[days] == 1
    kk = np.arange(K + 1)
    tot = CNT[0][con].reshape(-1, 2, K + 1).sum(1)            # (天, k)
    def pdq(m):
        x = tot[:, m].sum(1); return {"平均": float(x.mean()), "中位": float(np.median(x)), "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90))}
    A = {"≥5": pdq(kk >= 5), "≥9": pdq(kk >= 9), "≥10": pdq(kk >= 10), "≥11": pdq(kk >= 11), "5～10": pdq((kk >= 5) & (kk <= 10))}
    Nh = N5[0].sum((1, 2)); Lh = L5[0].sum((2, 3))               # (H, k)、(H, g, k)
    P = {m: [] for m in (5, 9, 10, 11)}; base = []
    for hi, gi in cells:
        cN = Nh[hi][::-1].cumsum()[::-1]; cL = Lh[hi, gi][::-1].cumsum()[::-1]
        for m in P:
            P[m].append(cL[m] / max(cN[m], 1))
        base.append(Lh[hi, gi].sum() / Nh[hi].sum())
    B = {"格數": len(cells), "全部股票": float(np.median(base)), **{f"≥{m}": float(np.median(v)) for m, v in P.items()}}
    C = {}
    for key, v in OLDS.items():
        a = np.concatenate(v).astype(float); up, dn, av = a[:, 0], a[:, 1], a[:, 2]
        up[up == 999] = np.nan; dn[dn == 999] = np.nan
        ok = av >= 250; hit = np.isfinite(up) & ok
        C[key] = {"筆數": len(a), **{f"{h}日內": float(np.mean(up[av >= h] <= h)) for h in HZ},
                  "中位天數": float(np.median(up[hit])), "p25": float(np.percentile(up[hit], 25)), "p75": float(np.percentile(up[hit], 75)),
                  "先漲": float((ok & (np.nan_to_num(up, nan=1e9) < np.nan_to_num(dn, nan=1e9)))[ok].mean()),
                  "先跌": float((ok & (np.nan_to_num(dn, nan=1e9) < np.nan_to_num(up, nan=1e9)))[ok].mean())}
    return {"舊": OLD, "重算": {"每天（確認段）": A, "變飆股（合併、格中位）": B, "漲15%（合併）": C}}


def tables(CNT, days, segd, N5, L5, cells, G, T_N, T_C, T_U, T_OK, T_FU, T_FD, T_H):
    out = []; t15 = []
    gidx = {(g[0], g[1], g[3]): i for i, g in enumerate(G)}
    for v in range(2):
        for s3 in SEG3:
            sm = [0, 1] if s3 == "合併" else [SEGN.index(s3)]
            dsel = np.isin(segd[days], sm)
            cnt = CNT[v][dsel].reshape(-1, 2, K + 1)                 # (天, F4, k)
            Nv = N5[v][:, sm].sum(1); Lv = L5[v][:, :, sm].sum(2)     # (H, F4, k)、(H, g, F4, k)
            baseP = np.array([Lv[hi, gi].sum() / Nv[hi].sum() for hi, gi in cells])
            for fam, nm, ks, f, dd in G:
                fs = list(F4SEL[f])
                if fam == "kp":
                    sel = np.zeros((2, K + 1), bool)
                    for ff in (0, 1):
                        for kk in range(K + 1):
                            sel[ff, kk] = (kk + ff) in ks
                else:
                    sel = np.zeros((2, K + 1), bool); sel[np.ix_(fs, list(ks))] = True
                x = cnt[:, sel].sum(1)
                Pc = []; R = []
                for j, (hi, gi) in enumerate(cells):
                    nn = Nv[hi][sel].sum()
                    if nn > 0:
                        p = Lv[hi, gi][sel].sum() / nn; Pc.append(p); R.append(p / baseP[j])
                Pc = np.array(Pc); R = np.array(R)
                gi_ = gidx[(fam, nm, f)]
                tn = T_N[gi_, v, sm].sum(); tc = T_C[gi_, v, sm].sum(0); tu = T_U[gi_, v, sm].sum(0); tok = T_OK[gi_, v, sm].sum()
                med, p25, p75 = hist_med(T_H[gi_, v, sm].sum(0))
                fam_lab = {"base": "不看特徵", "k": "k", "kp": "k′"}[fam]
                cond = cond_text(fam, nm, f)
                row = {"版本": VERN[v], "段": s3, "家族": fam_lab, "特徵數": nm, "F4": f, "條件": cond,
                       "每天平均幾檔": float(x.mean()), "每天中位": float(np.median(x)), "每天 p10": float(np.percentile(x, 10)), "每天 p90": float(np.percentile(x, 90)),
                       "股-日數（合計）": int(Nv[0][sel].sum()),
                       "變飆股比例（格中位）": float(np.median(Pc)) if len(Pc) else np.nan, "p10": float(np.percentile(Pc, 10)) if len(Pc) else np.nan,
                       "p90": float(np.percentile(Pc, 90)) if len(Pc) else np.nan, "算到的格數": len(Pc),
                       "相對全部股票倍數（格中位）": float(np.median(R)) if len(R) else np.nan,
                       "訊號筆數（去重）" if dd else "股-日筆數（不去重）": int(tn), "筆數": int(tn), "去重": dd,
                       **{f"{h}日內漲15%": (tu[j] / tc[j] if tc[j] else np.nan) for j, h in enumerate(HZ)},
                       "漲到15%中位天數": med, "天數 p25": p25, "天數 p75": p75,
                       "一年內先漲15%": T_FU[gi_, v, sm].sum() / tok if tok else np.nan, "一年內先跌15%": T_FD[gi_, v, sm].sum() / tok if tok else np.nan,
                       "觀察窗滿250筆數": int(tok)}
                out.append(row)
    TK = pd.DataFrame(out)
    TK = TK.drop(columns=[c for c in ("訊號筆數（去重）", "股-日筆數（不去重）") if c in TK.columns])
    T15 = TK[["版本", "段", "家族", "特徵數", "F4", "條件", "去重", "筆數"] + [f"{h}日內漲15%" for h in HZ] + ["漲到15%中位天數", "天數 p25", "天數 p75", "一年內先漲15%", "一年內先跌15%", "觀察窗滿250筆數"]]
    return TK, T15


def cond_text(fam, nm, f):
    ftxt = {"全部": "", "帶 F4": "，且帶 F4（連續虧損）", "不帶 F4": "，且不帶 F4"}[f]
    if fam == "base":
        return {"全部": "全部股票（不看特徵）", "帶 F4": "帶 F4（連續虧損）的全部股票", "不帶 F4": "不帶 F4 的全部股票"}[f]
    if fam == "kp":
        return f"14 個起漲特徵＋F4（共 15 個）同時符合 {nm}"
    return f"14 個起漲特徵同時符合 {nm}{ftxt}"


# ═════════════ 網頁 ═════════════
P_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.1f}%"
P2 = lambda x: "—" if x is None or not np.isfinite(x) else (f"{x * 100:.2f}%" if x < 0.1 else f"{x * 100:.1f}%")
F1_ = lambda x: "—" if x is None or not np.isfinite(x) else (f"{x:.1f}" if x < 100 else f"{x:,.0f}")
X_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:.1f} 倍"
D_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:.0f} 天"


def page():
    TK = pd.read_csv(os.path.join(OUT, "table_all.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    REP = json.load(open(os.path.join(OUT, "repro.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal;min-width:11em}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            "\ntr.sep td{border-top:2px solid #bbb}tr.hl td{background:#fff8e1}ul.k li{margin:.2em 0}")

    def get(v, s3, fam, nm, f):
        r = TK[(TK["版本"] == v) & (TK["段"] == s3) & (TK["家族"] == {"base": "不看特徵", "k": "k", "kp": "k′"}[fam]) & (TK["特徵數"] == nm) & (TK["F4"] == f)]
        assert len(r) == 1, (v, s3, fam, nm, f)
        return r.iloc[0]

    def row(r, hl=False, sep=False):
        cls = " class='" + " ".join(x for x, b in (("hl", hl), ("sep", sep)) if b) + "'" if (hl or sep) else ""
        return (f"<tr{cls}><td class='l'>{html.escape(r['條件'])}</td><td>{F1_(r['每天平均幾檔'])}</td>"
                f"<td>{P2(r['變飆股比例（格中位）'])}<br><small>{P2(r['p10'])}～{P2(r['p90'])}</small></td><td>{X_(r['相對全部股票倍數（格中位）'])}</td>"
                f"<td>{D_(r['漲到15%中位天數'])}</td><td>{P_(r['20日內漲15%'])}</td><td>{P_(r['一年內先跌15%'])}</td><td>{int(r['筆數']):,}</td></tr>")
    HEAD = ("<tr><th class='l'>條件</th><th>每天平均幾檔</th><th>之後變飆股<br><small>格中位（p10～p90）</small></th><th>相對全部股票</th>"
            "<th>漲到 15%<br>中位天數</th><th>20 天內<br>漲 15%</th><th>一年內<br>先跌 15%</th><th>筆數</th></tr>")
    v0 = VERN[0]
    a10 = get(v0, "合併", "k", "10 個以上", "全部"); a10f = get(v0, "合併", "k", "10 個以上", "帶 F4"); a10n = get(v0, "合併", "k", "10 個以上", "不帶 F4")
    a5 = get(v0, "合併", "k", "5 個以上", "全部"); a5f = get(v0, "合併", "k", "5 個以上", "帶 F4"); a5n = get(v0, "合併", "k", "5 個以上", "不帶 F4")
    b0 = get(v0, "合併", "base", "不看特徵", "全部"); bf = get(v0, "合併", "base", "不看特徵", "帶 F4")
    p10 = get(v0, "合併", "kp", "10 個以上", "全部")
    e10f = get(v0, "探索", "k", "10 個以上", "帶 F4"); e10n = get(v0, "探索", "k", "10 個以上", "不帶 F4")
    c10f = get(v0, "確認", "k", "10 個以上", "帶 F4"); c10n = get(v0, "確認", "k", "10 個以上", "不帶 F4")
    w10f = get(VERN[1], "合併", "k", "10 個以上", "帶 F4"); w10n = get(VERN[1], "合併", "k", "10 個以上", "不帶 F4")
    cov = META["F4 覆蓋"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>起漲特徵加連續虧損</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>起漲特徵加上 F4（連續虧損）重跑（2021-01～2026-08）</h1>",
         "<p class='warn'>只描述，⛔ 不判定、不計檢定數；不是買賣建議。飆股定義和當初一樣：seq6 網格（10～250 天 × 漲 50%～10 倍以上），每格各算一次再取中位數。</p>",
         "<h2>先講結論</h2><ul class='k'>",
         f"<li><b>當初的資料都還在，定義沒變</b>：用原本的資料與算法重算，舊數字全部對上（見第六節）。</li>",
         f"<li><b>連續虧損股本來就比較常變飆股</b>：不看特徵時，帶 F4 的股票之後變飆股的比例 {P2(bf['變飆股比例（格中位）'])}，全部股票 {P2(b0['變飆股比例（格中位）'])}"
         f"（{X_(bf['相對全部股票倍數（格中位）'])}）；但帶 F4 的只占全部股-日的 {cov['帶 F4 比例'] * 100:.1f}%。</li>",
         f"<li><b>14 個特徵符合 10 個以上</b>：全部 {P2(a10['變飆股比例（格中位）'])}（每天 {F1_(a10['每天平均幾檔'])} 檔）；"
         f"其中帶 F4 的 {P2(a10f['變飆股比例（格中位）'])}（每天 {F1_(a10f['每天平均幾檔'])} 檔），不帶 F4 的 {P2(a10n['變飆股比例（格中位）'])}。</li>",
         f"<li><b>符合 5 個以上</b>：全部 {P2(a5['變飆股比例（格中位）'])}；帶 F4 {P2(a5f['變飆股比例（格中位）'])}（每天 {F1_(a5f['每天平均幾檔'])} 檔）；不帶 F4 {P2(a5n['變飆股比例（格中位）'])}。</li>",
         f"<li><b>先跌 15% 的比例</b>：10 個以上全部 {P_(a10['一年內先跌15%'])}、帶 F4 {P_(a10f['一年內先跌15%'])}、不帶 F4 {P_(a10n['一年內先跌15%'])}；全部股票 {P_(b0['一年內先跌15%'])}。</li>",
         f"<li><b>把 F4 當第 15 個特徵</b>：15 個裡符合 10 個以上 {P2(p10['變飆股比例（格中位）'])}，每天 {F1_(p10['每天平均幾檔'])} 檔。</li>",
         f"<li><b>兩段方向一樣</b>：10 個以上帶 F4 vs 不帶 F4，探索段 {P2(e10f['變飆股比例（格中位）'])} vs {P2(e10n['變飆股比例（格中位）'])}、"
         f"確認段 {P2(c10f['變飆股比例（格中位）'])} vs {P2(c10n['變飆股比例（格中位）'])}；只看 W1 母體內 {P2(w10f['變飆股比例（格中位）'])} vs {P2(w10n['變飆股比例（格中位）'])}。</li>",
         f"<li>樣本小：10 個以上又帶 F4，兩段合計去重後只有 {int(a10f['筆數'])} 筆（每天約 1 檔），11 個以上更少，誤差大、只能看方向。</li></ul>",
         "<h2>怎麼讀</h2><ul class='k'>",
         "<li><b>每天平均幾檔</b>：當天收盤符合條件的檔數，各交易日平均（同一檔連續好幾天都算）。</li>",
         "<li><b>之後變飆股</b>：符合那天之後，會漲到飆股標準的比例（不限定當天就是起漲第一天）。</li>",
         "<li><b>相對全部股票</b>：同一格裡，條件的比例 ÷ 全部股票的比例，再取格中位。</li>",
         "<li><b>漲到 15% 中位天數、20 天內漲 15%、一年內先跌 15%</b>：同一檔連續出現只算第一天（前 20 天沒出現過才算新的）；中位天數只算一年內有漲到的。「不看特徵」那幾列不去重。</li>",
         "<li><b>筆數</b>：去重後的訊號筆數；「不看特徵」那幾列是全部股-日。「5～9 個」和「5 個以上」的筆數幾乎一樣，因為去重只取一段的第一天，而一段通常從 5～9 個開始。</li>",
         f"<li><b>F4（連續虧損）</b>：最近 4 季 EPS 合計虧且最近一季虧，或最近 8 季有 6 季以上虧；用符合當天之前最後一個月底、當時已公布的季報判定。"
         f"F4 判不出來（例如季報不足）當作不帶 F4（占段內股-日 {(1 - cov['F4 可判比例']) * 100:.1f}%）。</li></ul>"]
    # 一、主表（合併、全部上市櫃）
    H.append(f"<h2>一、分界表（{SEGLAB['合併']}、全部上市櫃）</h2><div class='wrap'><table>{HEAD}")
    for nm in ("不看特徵", "5 個以上", "5～9 個", "9 個以上", "10 個以上", "11 個以上"):
        for i, f in enumerate(F4N):
            r = get(v0, "合併", "base" if nm == "不看特徵" else "k", nm, f)
            H.append(row(r, hl=(nm == "10 個以上"), sep=(i == 0)))
    H.append("</table></div>")
    # 二、0～14 逐個
    H.append(f"<h2>二、14 個特徵逐個（0～14 個；{SEGLAB['合併']}、全部上市櫃）</h2>"
             "<p class='note'>每格大字 ＝ 每天平均幾檔；第二行 ＝ 之後變飆股（格中位）。</p><div class='wrap'><table>"
             "<tr><th class='l'>同時符合</th><th>全部</th><th>帶 F4</th><th>不帶 F4</th></tr>")
    for kk in range(K + 1):
        cells_ = []
        for f in F4N:
            r = get(v0, "合併", "k", f"{kk} 個", f)
            cells_.append(f"<td>{F1_(r['每天平均幾檔'])} 檔<br><small>{P2(r['變飆股比例（格中位）'])}</small></td>")
        H.append(f"<tr><td class='l'>剛好 {kk} 個</td>{''.join(cells_)}</tr>")
    H.append("</table></div>")
    # 三、k′
    H.append(f"<h2>三、把 F4 當第 15 個特徵（{SEGLAB['合併']}、全部上市櫃）</h2><div class='wrap'><table>{HEAD}")
    H.append(row(b0))
    for nm in ("5 個以上", "5～9 個", "9 個以上", "10 個以上", "11 個以上"):
        H.append(row(get(v0, "合併", "kp", nm, "全部"), hl=(nm == "10 個以上")))
    H.append("</table></div><details><summary>15 個逐個（0～15）</summary><div class='wrap'><table>"
             "<tr><th class='l'>同時符合</th><th>每天平均幾檔</th><th>之後變飆股</th><th>相對全部股票</th></tr>")
    for kk in range(K + 2):
        r = get(v0, "合併", "kp", f"{kk} 個", "全部")
        H.append(f"<tr><td class='l'>剛好 {kk} 個</td><td>{F1_(r['每天平均幾檔'])}</td><td>{P2(r['變飆股比例（格中位）'])}</td><td>{X_(r['相對全部股票倍數（格中位）'])}</td></tr>")
    H.append("</table></div></details>")
    # 四、分段
    H.append("<h2>四、分段看（探索、確認）</h2><p class='note'>同一套表分成兩段；兩段方向一樣才比較可信。</p>")
    for s3 in ("探索", "確認"):
        H.append(f"<h3>{SEGLAB[s3]}</h3><div class='wrap'><table>{HEAD}")
        for nm in ("不看特徵", "5 個以上", "10 個以上", "11 個以上"):
            for i, f in enumerate(F4N):
                H.append(row(get(v0, s3, "base" if nm == "不看特徵" else "k", nm, f), hl=(nm == "10 個以上"), sep=(i == 0)))
        H.append(row(get(v0, s3, "kp", "10 個以上", "全部"), sep=True))
        H.append("</table></div>")
    # 五、W1
    v1 = VERN[1]
    H.append(f"<h2>五、只看 W1 母體內（營量／營飆能買的；{SEGLAB['合併']}）</h2>"
             f"<p class='note'>W1 母體內占段內股-日 {cov['W1 母體內比例'] * 100:.1f}%；其中帶 F4 {cov['W1 內帶 F4 比例'] * 100:.1f}%。倍數的分母換成 W1 母體內全部股票。</p>"
             f"<div class='wrap'><table>{HEAD}")
    for nm in ("不看特徵", "5 個以上", "9 個以上", "10 個以上", "11 個以上"):
        for i, f in enumerate(F4N):
            H.append(row(get(v1, "合併", "base" if nm == "不看特徵" else "k", nm, f), hl=(nm == "10 個以上"), sep=(i == 0)))
    H.append(row(get(v1, "合併", "kp", "10 個以上", "全部"), sep=True))
    H.append("</table></div>")
    # 六、重現
    o, nw = REP["舊"], REP["重算"]
    a, b, c = nw["每天（確認段）"], nw["變飆股（合併、格中位）"], nw["漲15%（合併）"]
    RR = [("確認段每天：5 個以上（中位，p10～p90）", f"{o['每天（確認段）']['≥5 中位']}（{o['每天（確認段）']['≥5 p10']}～{o['每天（確認段）']['≥5 p90']}）", f"{a['≥5']['中位']:.0f}（{a['≥5']['p10']:.0f}～{a['≥5']['p90']:.0f}）"),
          ("確認段每天：5～10 個（平均）", f"{o['每天（確認段）']['5～10 平均']}", f"{a['5～10']['平均']:.1f}"),
          ("確認段每天：9 個以上（平均）", f"{o['每天（確認段）']['≥9 平均']}", f"{a['≥9']['平均']:.1f}"),
          ("確認段每天：10 個以上（平均；中位；p90）", f"{o['每天（確認段）']['≥10 平均']}；{o['每天（確認段）']['≥10 中位']}；{o['每天（確認段）']['≥10 p90']}", f"{a['≥10']['平均']:.1f}；{a['≥10']['中位']:.0f}；{a['≥10']['p90']:.0f}"),
          ("確認段每天：11 個以上（平均）", f"{o['每天（確認段）']['≥11 平均']}", f"{a['≥11']['平均']:.1f}"),
          ("格數（標籤 ≥ 1,500）", f"{o['變飆股（合併、格中位）']['格數']}", f"{b['格數']}"),
          ("變飆股：全部股票", "1.29%", f"{b['全部股票'] * 100:.2f}%")]
    RR += [(f"變飆股：{m} 個以上", f"{o['變飆股（合併、格中位）'][f'≥{m}'] * 100:.1f}%", f"{b[f'≥{m}'] * 100:.1f}%") for m in (5, 9, 10, 11)]
    RR += [("10 個以上：筆數；20 天內漲 15%；中位天數；先跌", f"{o['漲15%（合併）']['≥10 筆數']:,}；36%；22 天；54%",
            f"{c['≥10']['筆數']:,}；{c['≥10']['20日內'] * 100:.0f}%；{c['≥10']['中位天數']:.0f} 天；{c['≥10']['先跌'] * 100:.0f}%"),
           ("5 個以上：筆數；先跌", "22,794；36%", f"{c['≥5']['筆數']:,}；{c['≥5']['先跌'] * 100:.0f}%"),
           ("11 個以上：筆數；中位天數；先跌", "655；20 天；55%", f"{c['≥11']['筆數']:,}；{c['≥11']['中位天數']:.0f} 天；{c['≥11']['先跌'] * 100:.0f}%"),
           ("全部（抽 2%）：筆數；20 天內；中位天數；先跌", "49,317；15%；57 天；38%",
            f"{c['全部']['筆數']:,}；{c['全部']['20日內'] * 100:.0f}%；{c['全部']['中位天數']:.0f} 天；{c['全部']['先跌'] * 100:.0f}%")]
    H.append("<h2>六、重現當初的數字（證明資料還在、定義沒變）</h2><div class='wrap'><table><tr><th class='l'>項目</th><th>2026-09-29 當時</th><th>這次重算</th></tr>")
    H += [f"<tr><td class='l'>{html.escape(x)}</td><td>{html.escape(y)}</td><td>{html.escape(z)}</td></tr>" for x, y, z in RR]
    H.append("</table></div>")
    ck = "（查核未跑）" if CK is None else f"獨立寫法抽樣重算：不同 {CK.get('錯誤數', '?')} 處（{html.escape('；'.join(CK.get('項目', [])))}）。"
    H.append(f"<p class='note'>讀法寫死 {html.escape(TIME)}。{ck} 全部數字見 table_all.csv（兩版本 × 三段 × 全部條件）。</p></main></body></html>")
    open(os.path.join(OUT, "起漲特徵加連續虧損.html"), "w", encoding="utf-8").write("\n".join(H))


# ═════════════ 查核（獨立寫法）═════════════
def check():
    log = log_to(os.path.join(OUT, "run_check.log"))
    log(f"===== check {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    uni = pd.read_csv(os.path.join(O.WORK5, "uni.csv"), dtype=str)
    D.DATA = O.ST; cal = D.load_calendar(); n = len(cal)
    fcol = json.load(open(os.path.join(O.WORK5, "build.json"), encoding="utf-8"))["特徵欄"]
    Qm = np.load(os.path.join(O.WORK5, "Q.npy"), mmap_mode="r")
    bar = np.load(os.path.join(O.WORK5, "bar.npy")); h6 = np.load(os.path.join(O.WORK6, "hdef6.npy"))
    dates = pd.Series(cal)
    seg = np.where((dates >= "2021-01-01") & (dates <= "2023-12-31"), 0, np.where((dates >= "2024-01-01") & (dates <= "2026-08-31"), 1, -1))
    # k：逐特徵自算
    kmat = np.zeros(bar.shape, np.int16)
    for nm, col, code in O.FEATS:
        kmat += (np.asarray(Qm[fcol.index(col)]) == code).astype(np.int16)
    # F4：merge_asof（嚴格早於 d）
    z = np.load(FLAGS); me = pd.to_datetime(z["me"]); sids = list(z["sids"])
    F4 = pd.DataFrame(z["F4"], index=me, columns=sids); EL = pd.DataFrame(z["EL"], index=me, columns=sids)
    left = pd.DataFrame({"d": cal})
    ref = pd.DataFrame({"m": me, "j": np.arange(len(me))})
    mj = pd.merge_asof(left, ref, left_on="d", right_on="m", allow_exact_matches=False)["j"].to_numpy()
    def flag_row(df, sid):
        if sid not in df.columns:
            return np.zeros(n, bool)
        v = df[sid].to_numpy(); out = np.zeros(n, bool); ok = np.isfinite(mj)
        out[ok] = v[mj[ok].astype(int)]; return out
    cl = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); PDc = pd.read_csv(os.path.join(OUT, "perday.csv.gz")); T15 = pd.read_csv(os.path.join(OUT, "t15.csv"))
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    rng = np.random.default_rng(20261007)
    pick = rng.choice(meta["格"], 2, replace=False).tolist()
    pc = [(int(p.split("_")[0][1:]), float(p.split("_g")[1][:-1]) / 100) for p in pick]
    errs = []; items = []
    # ① 格  ③ t15
    accN = {}; accL = {}
    COND = {"k≥10∧帶F4": lambda k, f: (k >= 10) & f, "k≥10∧不帶F4": lambda k, f: (k >= 10) & ~f, "k′≥10": lambda k, f: (k + f.astype(int)) >= 10}
    ev = {(cn, v): [] for cn in COND for v in range(2)}
    for s in range(len(uni)):
        sid = uni.loc[s, "stock_id"]
        rows_ok = bar[s] & (seg >= 0)
        if not rows_ok.any():
            continue
        st = D.load_stock(sid, uni.loc[s, "market"], cal)
        if st is None:
            continue
        c = st.df["close"].ffill().to_numpy(float)
        f = flag_row(F4, sid); el = flag_row(EL, sid); k = kmat[s]
        for H, g in pc:
            cpad = np.r_[c, np.full(H, np.nan)]
            fm = np.lib.stride_tricks.sliding_window_view(cpad[1:], H).max(1)[:n]
            dm = rows_ok & (h6[s] >= H) & np.isfinite(c)
            for v, mm in enumerate((dm, dm & el)):
                for t in np.flatnonzero(mm):
                    key = (v, H, g, int(seg[t]), int(f[t]), int(k[t]))
                    accN[key] = accN.get(key, 0) + 1
                    if np.isfinite(fm[t]) and fm[t] >= c[t] * (1 + g) * (1 - 1e-9):
                        accL[key] = accL.get(key, 0) + 1
        vb = np.flatnonzero(rows_ok & np.isfinite(c))
        for cn, fn in COND.items():
            sig = fn(k, f)
            for v in range(2):
                m_ = sig & (el if v == 1 else True)
                last = -10 ** 9
                for j, t in enumerate(vb):
                    if not m_[t]:
                        continue
                    newsig = (j - last) > 20; last = j
                    if not newsig:
                        continue
                    up = dn = None; av = 0
                    for h in range(1, 251):
                        if t + h >= n:
                            break
                        av = h
                        if up is None and c[t + h] >= c[t] * 1.15:
                            up = h
                        if dn is None and c[t + h] <= c[t] * 0.85:
                            dn = h
                    ev[(cn, v)].append((int(seg[t]), up, dn, av))
    for v in range(2):
        for H, g in pc:
            sub = cl[(cl["版本"] == VERN[v]) & (cl["H"] == H) & np.isclose(cl["g"], g)]
            for r in sub.itertuples():
                key = (v, H, g, SEGN.index(r.段), int(r.帶F4), int(r.k))
                if accN.get(key, 0) != r.股日數 or accL.get(key, 0) != r.標籤數:
                    errs.append(f"格 {VERN[v]} H{H} g{g} {r.段} F{r.帶F4} k{r.k}：自算 {accN.get(key, 0)}/{accL.get(key, 0)} 檔 {r.股日數}/{r.標籤數}")
            n_rows = len(sub)
            items.append(f"格 {VERN[v]} H{H}_g{int(round(g * 100))}% {n_rows} 列")
    MAPC = {"k≥10∧帶F4": ("k", "10 個以上", "帶 F4"), "k≥10∧不帶F4": ("k", "10 個以上", "不帶 F4"), "k′≥10": ("k′", "10 個以上", "全部")}
    for (cn, v), lst in ev.items():
        for s3 in SEG3:
            L_ = [e for e in lst if s3 == "合併" or e[0] == SEGN.index(s3)]
            fam, nm, ff = MAPC[cn]
            r = T15[(T15["版本"] == VERN[v]) & (T15["段"] == s3) & (T15["家族"] == fam) & (T15["特徵數"] == nm) & (T15["F4"] == ff)].iloc[0]
            mine = {"筆數": len(L_)}
            for h in HZ:
                ok = [e for e in L_ if e[3] >= h]
                mine[f"{h}日內漲15%"] = (sum(1 for e in ok if e[1] is not None and e[1] <= h) / len(ok)) if ok else np.nan
            ok = [e for e in L_ if e[3] >= 250]
            hits = sorted(e[1] for e in ok if e[1] is not None)
            mine["漲到15%中位天數"] = float(np.median(hits)) if hits else np.nan
            mine["一年內先跌15%"] = (sum(1 for e in ok if e[2] is not None and (e[1] is None or e[2] < e[1])) / len(ok)) if ok else np.nan
            mine["一年內先漲15%"] = (sum(1 for e in ok if e[1] is not None and (e[2] is None or e[1] < e[2])) / len(ok)) if ok else np.nan
            for kx, vx in mine.items():
                if not np.isclose(vx, r[kx], rtol=1e-9, atol=1e-12, equal_nan=True):
                    errs.append(f"t15 {cn} {VERN[v]} {s3} {kx}：自算 {vx} 檔 {r[kx]}")
            items.append(f"t15 {cn} {VERN[v]} {s3} {len(L_)} 筆")
    # ② 每天
    days = sorted(PDc["日期"].unique()); dp = rng.choice(days, 25, replace=False)
    pos = {str(d.date()): i for i, d in enumerate(cal)}
    for dstr in dp:
        t = pos[dstr]
        fcol_t = np.zeros(len(uni), bool); ecol_t = np.zeros(len(uni), bool)
        jj = mj[t]
        if np.isfinite(jj):
            for i, sid in enumerate(uni["stock_id"]):
                if sid in F4.columns:
                    fcol_t[i] = F4[sid].iloc[int(jj)]; ecol_t[i] = EL[sid].iloc[int(jj)]
        df = pd.DataFrame({"k": kmat[:, t], "f": fcol_t.astype(int), "el": ecol_t, "bar": bar[:, t]})
        for v in range(2):
            sub = df[df["bar"] & (df["el"] if v == 1 else True)]
            gcount = sub.groupby(["f", "k"]).size()
            r = PDc[(PDc["日期"] == dstr) & (PDc["版本"] == VERN[v])].iloc[0]
            for ff in range(2):
                for kk in range(K + 1):
                    mine = int(gcount.get((ff, kk), 0))
                    if mine != int(r[f"F{ff}_k{kk}"]):
                        errs.append(f"每天 {dstr} {VERN[v]} F{ff} k{kk}：自算 {mine} 檔 {r[f'F{ff}_k{kk}']}")
    items.append(f"每天 抽 25 天 × 2 版本 × 30 格")
    out = {"抽格": pick, "抽日": [str(x) for x in dp], "項目": items, "錯誤數": len(errs), "錯誤": errs[:50]}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[查核] 錯誤 {len(errs)}｜{items}")
    page()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="body"); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check:
        check()
    elif a.cmd == "page":
        page()
    else:
        body()


if __name__ == "__main__":
    main()
