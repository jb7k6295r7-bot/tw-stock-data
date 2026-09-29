# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：中段底「會再拉一段」的判斷（描述與參考，⛔ 不計 N；看過 mid_desc／exitsig／topjudge 結果之後才加）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_bottomjudge [--check]

⚠ 中段底、頂後底都是事後才知道的；第一、二部分用「事後已知這天是低點」的點，只有第三部分（回落第一次達到 x% 那天）是當下真的能用的版本。

═══ 讀法（寫死於 2026-09-29 21:53（台北），在算任何數字之前）═══
 ⛔ mid_desc 已整理過的 Lk 特徵（Q 表級距的涵蓋率）不重列，網頁連結帶過；新的只有「拉回狀態類特徵」與「判斷」
 B1 事件、格、彙總：seq6 events、事件 ≥ 30 的 182 格；逐格算、取格中位附 p10～p90；x ∈ {10, 20, 30}% 各一套（切段同 mid_desc M2／M2b）
    段 ＝ 依該點日期月份：探索 2021-01～2023-12、確認 2024-01～2026-08；某格某段要兩類各 ≥ 30 點才進該格
 B2 兩類低點：
    會再拉（＝ 1）＝ 中段底 Lk（k ≥ 2），之前的高點 H ＝ H(k−1)，前段起點 ＝ L(k−1)（L1 ＝ t）
    沒再拉（＝ 0）＝ 頂後底：P 之後第一天收盤 ≤ c[P] ×（1 − x）起，追蹤最低收盤，直到第一天收盤 ≥ 當時最低 ×（1 ＋ x）或 2026-08-31；
       那段期間最低收盤那天（同價取最早）；之前的高點 H ＝ P，前段起點 ＝ 最後一個 Lk（沒有 ＝ t）；P 之後到 2026-08-31 都沒回落 x% ⇒ 沒有頂後底
    頂後底之後到 2026-08-31 收盤又越過 c[P] 的 ⇒ 另分「頂後底（之後又越過 P）」，照報，⛔ 不進 0／1 判斷
    另依「第幾段的底」分：L2、L3、L4 以後（照報可用格）
 B3 拉回狀態類特徵（低點 L 當天收盤含以前可得；區間 (H, L]）：
    回落深度 c[L]÷c[H]−1｜拉回天數 L−H｜回落速度 ＝ 深度÷天數｜量縮 ＝ (H, L] 日均額 ÷ (前段起點, H] 日均額｜
    融資變化 ＝ (L 融資餘額 − H 融資餘額)×1000 ÷ 股本｜外資淨買 ＝ (H, L] 外資買賣超合計 ÷ 股本｜投信淨賣 ＝ (H, L] 投信合計 ＜ 0（是／否）｜
    大戶變化 ＝ L 當天 F 表 tdcc_20（集保 400 張以上 4 週變化；⚠ 沒有逐區間算）｜
    守住 MA20／MA60 ＝ c[L] ≥ 當天 MA20／MA60（還原收盤、K 棒序列）；(H, L] 收盤在 MA20／MA60 之下的天數｜守住前段起漲價 ＝ c[L] ≥ c[前段起點]｜
    拉回時處置中 ＝ L 當天處置中｜剛出關 ＝ (H, L] 內有處置迄日｜前段漲幅 ＝ c[H]÷c[前段起點]−1｜前面已完成段數（Lk ＝ k−1；頂後底 ＝ 總段數）｜
    從 t 起累積漲幅 ＝ c[H]÷c[t]−1｜從 t 起累計進入處置次數（到 L）
    連續值 ⇒ 五等分（分界 ＝ 該 x 探索段兩類低點合併的 20／40／60／80 分位，同值落同一格）；是否類 ⇒ 是／否；段數、處置次數 ⇒ 0、1、2、3 以上
 B4 第一部分（兩段合併）：拉回狀態類各級距在 會再拉、沒再拉 的涵蓋率（一般股-日沒有對應 ⇒ 不報）；差 ≥ 10 個百分點列「多了什麼／少了什麼」；分類呈現
 B5 第二部分 1：低點中「有此級距時是會再拉」的比例 ÷ 基準；月分群 95% 下緣；探索、確認各報（Q 表級距（非原門檻）＋拉回狀態類一起）
    第二部分 2：探索段選「會再拉 − 沒再拉 涵蓋差（格中位）最大、且倍數下緣（格中位）＞ 1」的前 K 個（K ∈ {3, 5, 8, 全部}；一概念一個）；分數 ＝ 同時有幾個；
       確認段校準：分數 ≥ m 的會再拉比例、抓到會再拉的幾成、誤抓頂後底的幾成、占低點比例
 B6 第三部分（當下可用版）：觸發日 d ＝ 每個新高日 a（a ＞ t，含 P）之後、下一個新高之前（P 則到 2026-08-31），收盤第一次 ≤ c[a] ×（1 − x）那天；
    特徵照 B3 以 H ＝ a、L ＝ d 算（前段起點 ＝ a 之前最後一個已完成的拉回低點，沒有 ＝ t）＋ d 當天 Q 表級距；
    結果：之後 20／60／120 日內收盤 ＞ c[a]（再創新高）；之後 60 日內再跌 10／20%（最低收盤 ≤ c[d] ×（1 − y））；d＋h ≤ 2026-08-31 才算
    分數用 B5 選出的特徵組；m* ＝ 探索段「抓到 120 日再創新高 − 誤抓沒再創新高」格中位最大的 m；確認段報各 m
 B7 查核（--check）：抽 2 格，逐日狀態機重算 x＝20% 的中段底、頂後底個數與回落深度中位、一個 Q 級距在兩類的涵蓋率 ⇒ 對長表
輸出 backtest/resultsSurge6/bottomjudge/
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
from backtest import researchSurge5_feat as FT
from backtest import researchSurge6_end_desc as ED

warnings.filterwarnings("ignore", category=RuntimeWarning)
D = S5.D
TIME = "2026-09-29 21:53（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/bottomjudge"
XS = (0.10, 0.20, 0.30)
HS = list(S5.HS); GS = list(S5.GS)
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_
Z = 1.959963984540054
EXP = (2021 * 12, 2023 * 12 + 11); CON = (2024 * 12, 2026 * 12 + 7)
KS = (3, 5, 8, "全部")
CONT = ["回落深度", "拉回天數", "回落速度", "量縮(拉回均額÷前段均額)", "融資變化÷股本", "外資淨買÷股本", "大戶4週變化", "MA20下天數", "MA60下天數", "前段漲幅", "從t起累積漲幅"]
BOOL = ["投信淨賣", "守住MA20", "守住MA60", "守住前段起漲價", "拉回時處置中", "剛出關"]
CNTF = ["前面已完成段數", "累計處置次數"]
PCAT = {"回落深度": "拉回幅度與時間", "拉回天數": "拉回幅度與時間", "回落速度": "拉回幅度與時間", "量縮(拉回均額÷前段均額)": "量", "融資變化÷股本": "籌碼", "外資淨買÷股本": "籌碼",
        "投信淨賣": "籌碼", "大戶4週變化": "籌碼", "守住MA20": "均線與支撐", "守住MA60": "均線與支撐", "守住前段起漲價": "均線與支撐", "MA20下天數": "均線與支撐", "MA60下天數": "均線與支撐",
        "拉回時處置中": "處置", "剛出關": "處置", "累計處置次數": "處置", "前段漲幅": "漲勢位置", "前面已完成段數": "漲勢位置", "從t起累積漲幅": "漲勢位置"}


def stock_ctx(sid, mk, cal, n, W, disp_row):
    st = D.load_stock(sid, mk, cal); df = st.df
    c = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
    amt = np.nan_to_num(pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)); bar = np.isfinite(df["close"].to_numpy(float))
    raw = pd.read_csv(os.path.join(S5.ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "shares"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); sh = pd.to_numeric(raw["shares"].reindex(cal), errors="coerce").ffill().to_numpy(float).copy(); sh[~(sh > 0)] = np.nan
    fo = np.zeros(n); tr = np.zeros(n); mb = np.full(n, np.nan)
    p_ = os.path.join(S5.MAIN, "stocks_inst", sid + ".csv")
    if os.path.exists(p_):
        it = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last"); it.index = pd.to_datetime(it["date"])
        fo = pd.to_numeric(it["foreign"], errors="coerce").reindex(cal).fillna(0.0).to_numpy(); tr = pd.to_numeric(it["trust"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
    p_ = os.path.join(S5.MAIN, "stocks_margin", sid + ".csv")
    if os.path.exists(p_):
        mg = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "m_balance"]).drop_duplicates("date", keep="last"); mg.index = pd.to_datetime(mg["date"])
        mb = pd.to_numeric(mg["m_balance"], errors="coerce").reindex(cal).ffill().to_numpy()
    idx = np.flatnonzero(bar); cb = c[idx]
    ma = {}
    for w in (20, 60):
        m_ = np.full(n, np.nan); m_[idx] = pd.Series(cb).rolling(w, min_periods=w).mean().to_numpy(); ma[w] = pd.Series(m_).ffill().to_numpy()
    below = {w: np.r_[0, np.cumsum(bar & (c < ma[w]))] for w in (20, 60)}
    ends = np.array(sorted(b for a, b in W["DISP"].get(sid, []))); starts = np.array(sorted(a for a, b in W["DISP"].get(sid, [])))
    return {"c": c, "ca": np.r_[0, np.cumsum(amt)], "cn": np.r_[0, np.cumsum(bar)], "cf": np.r_[0, np.cumsum(fo)], "ct": np.r_[0, np.cumsum(tr)], "mb": mb, "sh": sh,
            "ma": ma, "below": below, "ends": ends, "starts": starts, "disp": disp_row}


def pull_feats(X, H, L, Lp, t, k_done, tdcc):
    """X：stock_ctx；H、L、Lp、t：陣列（日曆索引）⇒ dict 原值。"""
    c = X["c"]; f = {}
    f["回落深度"] = c[L] / c[H] - 1; f["拉回天數"] = (L - H).astype(float); f["回落速度"] = f["回落深度"] / np.maximum(L - H, 1)
    avg = lambda a, b: (X["ca"][b + 1] - X["ca"][a + 1]) / np.maximum(X["cn"][b + 1] - X["cn"][a + 1], 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["量縮(拉回均額÷前段均額)"] = avg(H, L) / avg(Lp, H)
        f["融資變化÷股本"] = (X["mb"][L] - X["mb"][H]) * 1000 / X["sh"][L]
        f["外資淨買÷股本"] = (X["cf"][L + 1] - X["cf"][H + 1]) / X["sh"][L]
        tn = X["ct"][L + 1] - X["ct"][H + 1]
    f["投信淨賣"] = (tn < 0).astype(float); f["大戶4週變化"] = tdcc
    for w in (20, 60):
        f[f"守住MA{w}"] = np.where(np.isfinite(X["ma"][w][L]), c[L] >= X["ma"][w][L], np.nan); f[f"MA{w}下天數"] = (X["below"][w][L + 1] - X["below"][w][H + 1]).astype(float)
    f["守住前段起漲價"] = (c[L] >= c[Lp]).astype(float); f["拉回時處置中"] = X["disp"][L].astype(float)
    e = X["ends"]; f["剛出關"] = ((np.searchsorted(e, L, "right") - np.searchsorted(e, H, "right")) > 0).astype(float)
    f["前段漲幅"] = c[H] / c[Lp] - 1; f["前面已完成段數"] = np.minimum(k_done, 3).astype(float); f["從t起累積漲幅"] = c[H] / c[t] - 1
    st = X["starts"]; f["累計處置次數"] = np.minimum(np.searchsorted(st, L, "right") - np.searchsorted(st, t, "left"), 3).astype(float)
    return f


def build(uni, cal, n, E, W, t1, log):
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    disp = np.load(os.path.join(WORK5, "disp.npy")); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); tdcc = np.asarray(Fm[S5.FIX["tdcc_20"]])
    LOW = {xi: {k: [] for k in ("s", "d", "cell", "lab", "k", "over")} for xi in range(len(XS))}
    TRG = {xi: {k: [] for k in ("s", "d", "cell", "nh20", "nh60", "nh120", "dd10", "dd20")} for xi in range(len(XS))}
    LF = {xi: [] for xi in range(len(XS))}; TF = {xi: [] for xi in range(len(XS))}
    D.DATA = S5.ST
    for s in np.unique(es):
        sid = uni.loc[s, "stock_id"]; X = stock_ctx(sid, uni.loc[s, "market"], cal, n, W, disp[s]); c = X["c"]
        rv = pd.Series(c[::-1]); FUT = {}
        for h in (20, 60, 120):
            mx = np.r_[rv.rolling(h, min_periods=h).max().to_numpy()[::-1][1:], np.nan]; mn = np.r_[rv.rolling(h, min_periods=h).min().to_numpy()[::-1][1:], np.nan]
            lim = np.arange(n) + h > t1; mx[lim] = np.nan; mn[lim] = np.nan; FUT[h] = (mx, mn)
        memo = {}
        for i in np.flatnonzero(es == s):
            t, P = ed[i], Pv[i]
            if (t, P) not in memo:
                cs = c[t:P + 1]; rm = np.maximum.accumulate(cs); nh = np.flatnonzero(cs[1:] > rm[:-1]) + 1; pk = np.r_[0, nh]
                res = {}
                for xi, x in enumerate(XS):
                    thr = (1 - x) * (1 + 1e-9)
                    cuts = []
                    for j in np.flatnonzero(np.diff(pk) >= 2):
                        a, b = int(pk[j]), int(pk[j + 1]); seg = cs[a + 1:b]; kk = int(np.argmin(seg))
                        if a > 0 and seg[kk] <= cs[a] * thr:
                            cuts.append((a, a + 1 + kk))
                    Hs = [t + a for a, _ in cuts]; Ls = [t + b for _, b in cuts]
                    rows = []                                                      # (H, L, Lp, k_done, lab, k, over)
                    for kk, (h_, l_) in enumerate(zip(Hs, Ls), 1):
                        rows.append((h_, l_, t if kk == 1 else Ls[kk - 2], kk - 1, 1, kk + 1, 0))
                    # 頂後底
                    cP = c[P]; aft = np.flatnonzero(c[P + 1:t1 + 1] <= cP * thr)
                    if len(aft):
                        f0 = P + 1 + int(aft[0]); m_, md = c[f0], f0; d = f0 + 1
                        while d <= t1:
                            if c[d] < m_:
                                m_, md = c[d], d
                            elif c[d] >= m_ * (1 + x):
                                break
                            d += 1
                        over = int((c[md + 1:t1 + 1] > cP).any())
                        rows.append((P, md, Ls[-1] if Ls else t, len(Hs) + 1, 0 if not over else 2, 0, over))
                    # 觸發日
                    trg = []
                    peaks = list(pk[pk > 0]); nxt = {int(pk[j]): int(pk[j + 1]) for j in range(len(pk) - 1)}
                    done_lows = sorted(zip(Hs, Ls))
                    for a in peaks:
                        A = t + int(a); end = t + nxt[int(a)] - 1 if int(a) in nxt else t1
                        w = np.flatnonzero(c[A + 1:end + 1] <= c[A] * thr)
                        if not len(w):
                            continue
                        d = A + 1 + int(w[0]); prev = [l_ for h_, l_ in done_lows if l_ < A]
                        trg.append((A, d, prev[-1] if prev else t, len(prev)))
                    res[xi] = (rows, trg)
                memo[(t, P)] = res
            for xi in range(len(XS)):
                rows, trg = memo[(t, P)][xi]
                if rows:
                    Hh, Ll, Lp, kd, lab, kk, ov = (np.array(v) for v in zip(*rows))
                    for k_, v in (("s", np.full(len(Ll), s)), ("d", Ll), ("cell", np.full(len(Ll), ec[i])), ("lab", lab), ("k", kk), ("over", ov)):
                        LOW[xi][k_].append(v)
                    LF[xi].append(pull_feats(X, Hh, Ll, Lp, np.full(len(Ll), t), kd, tdcc[s, Ll]))
                if trg:
                    Aa, dd, Lp, kd = (np.array(v) for v in zip(*trg))
                    f20, _ = FUT[20]; f60, m60 = FUT[60]; f120, _ = FUT[120]
                    for k_, v in (("s", np.full(len(dd), s)), ("d", dd), ("cell", np.full(len(dd), ec[i])),
                                  ("nh20", np.where(np.isfinite(f20[dd]), f20[dd] > c[Aa], np.nan)), ("nh60", np.where(np.isfinite(f60[dd]), f60[dd] > c[Aa], np.nan)),
                                  ("nh120", np.where(np.isfinite(f120[dd]), f120[dd] > c[Aa], np.nan)),
                                  ("dd10", np.where(np.isfinite(m60[dd]), m60[dd] <= c[dd] * 0.9, np.nan)), ("dd20", np.where(np.isfinite(m60[dd]), m60[dd] <= c[dd] * 0.8, np.nan))):
                        TRG[xi][k_].append(v)
                    TF[xi].append(pull_feats(X, Aa, dd, Lp, np.full(len(dd), t), kd, tdcc[s, dd]))
    out = {}
    for xi in range(len(XS)):
        lw = {k: np.concatenate(v) for k, v in LOW[xi].items()}; tg = {k: np.concatenate(v) for k, v in TRG[xi].items()}
        for k_ in LF[xi][0]:
            lw[k_] = np.concatenate([f[k_] for f in LF[xi]]); tg[k_] = np.concatenate([f[k_] for f in TF[xi]])
        out[xi] = (lw, tg)
        log(f"[列] x＝{int(XS[xi] * 100)}%：低點 {len(lw['d']):,}（會再拉 {(lw['lab'] == 1).sum():,}／沒再拉 {(lw['lab'] == 0).sum():,}／頂後又越過 P {(lw['lab'] == 2).sum():,}）｜觸發日 {len(tg['d']):,}")
    return out


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    W, _ = S5.world(log)
    DATA = build(uni, cal, n, E, W, t1, log)
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); NM = int(CON[1] - EXP[0] + 1)
    LV = [lv for lv in FT.levels() if not lv[1].startswith("d_")]; Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    cl = np.array(cells)
    P1 = []; P2 = []; CAL = []; RT = []; SEL = []; CL = []; BND = {}; GRPN = []
    for xi, x in enumerate(XS):
        lw, tg = DATA[xi]; xs_ = f"{int(x * 100)}%"
        lm = mon[lw["d"]]; lseg = np.where((lm >= EXP[0]) & (lm <= EXP[1]), 0, np.where((lm >= CON[0]) & (lm <= CON[1]), 1, -1)); lmi = np.clip(lm - EXP[0], 0, NM - 1)
        tm = mon[tg["d"]]; tseg = np.where((tm >= EXP[0]) & (tm <= EXP[1]), 0, np.where((tm >= CON[0]) & (tm <= CON[1]), 1, -1))
        lab = lw["lab"]
        # 級距碼：拉回狀態類
        LEV = []                                          # (名稱, 概念, 分類, 低點碼, 觸發碼, 碼)
        explow = (lseg == 0) & (lab <= 1)
        for f in CONT:
            v = lw[f]; bd = np.nanpercentile(v[explow & np.isfinite(v)], [20, 40, 60, 80]); BND[f"{f}_x{int(x * 100)}"] = [float(b) for b in bd]
            cd_l = np.where(np.isfinite(v), np.searchsorted(bd, v, "right") + 1, 0); vt = tg[f]; cd_t = np.where(np.isfinite(vt), np.searchsorted(bd, vt, "right") + 1, 0)
            for q in range(1, 6):
                lo = "−∞" if q == 1 else f"{bd[q - 2]:.3g}"; hi = "∞" if q == 5 else f"{bd[q - 1]:.3g}"
                LEV.append((f"{f}｜Q{q}（{lo}～{hi}）", f"位置:{f}", PCAT[f], cd_l, cd_t, q))
        for f in BOOL:
            cd_l = np.where(np.isfinite(lw[f]), lw[f] + 1, 0); cd_t = np.where(np.isfinite(tg[f]), tg[f] + 1, 0)
            for q, nm in ((2, "是"), (1, "否")):
                LEV.append((f"{f}｜{nm}", f"位置:{f}", PCAT[f], cd_l, cd_t, q))
        for f in CNTF:
            cd_l = lw[f] + 1; cd_t = tg[f] + 1
            for q, nm in ((1, "0"), (2, "1"), (3, "2"), (4, "3 以上")):
                LEV.append((f"{f}｜{nm}", f"位置:{f}", PCAT[f], cd_l, cd_t, q))
        NEWN = len(LEV)
        QC = {}
        for lv in LV:
            if lv[0] not in QC:
                q = np.asarray(Qm[lv[0]]); QC[lv[0]] = (q[lw["s"], lw["d"]], q[tg["s"], tg["d"]])
            LEV.append((f"{lv[4]}｜{lv[3]}", ED.concept(lv[1]), "Q表", QC[lv[0]][0], QC[lv[0]][1], lv[2]))
        # 計數：低點 (cell, lab01, month, has)
        m01 = lab <= 1

        def stat(cd, code, segk, minn=30):
            defd = (cd > 0) & m01 & ((lseg == segk) if segk != "all" else (lseg >= 0))
            key = ((lw["cell"][defd] * 2 + lab[defd]) * NM + lmi[defd]) * 2 + (cd[defd] == code)
            cc = np.bincount(key, minlength=250 * 2 * NM * 2).reshape(250, 2, NM, 2)[cl]
            n1, n0 = cc[:, 1].sum((1, 2)), cc[:, 0].sum((1, 2)); ok = (n1 >= minn) & (n0 >= minn)
            e = cc[:, 1, :, 1].astype(float); nn = (cc[:, 0, :, 1] + cc[:, 1, :, 1]).astype(float); N = nn.sum(1)
            p = e.sum(1) / N; base = n1 / (n1 + n0); se = np.sqrt(((e - p[:, None] * nn) ** 2).sum(1)) / N
            return ok, cc[:, 1, :, 1].sum(1) / n1, cc[:, 0, :, 1].sum(1) / n0, p / base, (p - Z * se) / base
        for j, (nm, cp, cat, cdl, cdt, code) in enumerate(LEV):
            if j < NEWN:
                ok, c1, c0, lf, lo = stat(cdl, code, "all")
                if ok.any():
                    P1.append({"x": xs_, "特徵": nm, "分類": cat, "可用格": int(ok.sum()), "會再拉": q3(c1[ok])[0], "會再拉 p10": q3(c1[ok])[1], "會再拉 p90": q3(c1[ok])[2],
                               "沒再拉": q3(c0[ok])[0], "差(會再拉−沒再拉)": q3(c1[ok])[0] - q3(c0[ok])[0]})
            r = {"x": xs_, "特徵": nm, "概念": cp, "分類": cat, "新特徵": j < NEWN}
            for sk, sn in ((0, "探索"), (1, "確認")):
                ok, c1, c0, lf, lo = stat(cdl, code, sk)
                r[f"{sn} 可用格"] = int(ok.sum())
                for k_, arr in (("會再拉涵蓋", c1), ("沒再拉涵蓋", c0), ("倍數", lf), ("倍數下緣", lo)):
                    r[f"{sn} {k_}"] = q3(arr[ok])[0] if ok.any() else np.nan
                r[f"{sn} 差"] = r[f"{sn} 會再拉涵蓋"] - r[f"{sn} 沒再拉涵蓋"]
            P2.append(r)
        p2 = pd.DataFrame([r for r in P2 if r["x"] == xs_])
        pk_ = p2[(p2["探索 倍數下緣"] > 1) & (p2["探索 差"] > 0)].sort_values("探索 差", ascending=False).drop_duplicates("概念", keep="first")
        LX = {r[0]: r for r in LEV}
        order = np.argsort(lw["cell"], kind="stable"); cbd = np.searchsorted(lw["cell"][order], np.arange(251)); ROWS = {c: order[cbd[c]:cbd[c + 1]] for c in cells}
        ordt = np.argsort(tg["cell"], kind="stable"); cbt = np.searchsorted(tg["cell"][ordt], np.arange(251)); ROWT = {c: ordt[cbt[c]:cbt[c + 1]] for c in cells}
        for K in KS:
            sel = pk_ if K == "全部" else pk_.head(K); names = sel["特徵"].tolist(); k_ = len(names)
            SEL += [{"x": xs_, "K": K, "順位": j + 1, "特徵": nm} for j, nm in enumerate(names)]
            scL = np.sum([LX[nm][3] == LX[nm][5] for nm in names], 0) if k_ else np.zeros(len(lab), int)
            scT = np.sum([LX[nm][4] == LX[nm][5] for nm in names], 0) if k_ else np.zeros(len(tg["d"]), int)
            for sk, sn in ((0, "探索"), (1, "確認")):
                uc = [c for c in cells if ((lseg[ROWS[c]] == sk) & (lab[ROWS[c]] == 1)).sum() >= 30 and ((lseg[ROWS[c]] == sk) & (lab[ROWS[c]] == 0)).sum() >= 30]
                for m in range(k_ + 1):
                    pr, rc, fp, cv = [], [], [], []
                    for c in uc:
                        w = ROWS[c][(lseg[ROWS[c]] == sk) & (lab[ROWS[c]] <= 1)]; g = scL[w] >= m; y = lab[w] == 1
                        pr.append(y[g].mean() if g.any() else np.nan); rc.append((g & y).sum() / y.sum()); fp.append((g & ~y).sum() / (~y).sum()); cv.append(g.mean())
                    CAL.append({"x": xs_, "K": K, "實際特徵數": k_, "段": sn, "分數≥": m, "可用格": len(uc), "會再拉的比例": q3(pr)[0], "p10": q3(pr)[1], "p90": q3(pr)[2],
                                "抓到會再拉的幾成": q3(rc)[0], "誤抓頂後底的幾成": q3(fp)[0], "占低點比例": q3(cv)[0]})
                # 當下可用版
                y120 = tg["nh120"]; uct = [c for c in cells if ((tseg[ROWT[c]] == sk) & (y120[ROWT[c]] == 1)).sum() >= 30 and ((tseg[ROWT[c]] == sk) & (y120[ROWT[c]] == 0)).sum() >= 30]
                for m in range(k_ + 1):
                    row = {"x": xs_, "K": K, "實際特徵數": k_, "段": sn, "分數≥": m, "可用格": len(uct)}
                    jj = []
                    for yk, ynm in (("nh20", "20日內再創新高"), ("nh60", "60日內再創新高"), ("nh120", "120日內再創新高"), ("dd10", "60日內再跌10%"), ("dd20", "60日內再跌20%")):
                        yv = tg[yk]; vals = []; covs = []
                        for c in uct:
                            w = ROWT[c][(tseg[ROWT[c]] == sk) & np.isfinite(yv[ROWT[c]])]; g = scT[w] >= m
                            vals.append(yv[w][g].mean() if g.any() else np.nan); covs.append(g.mean())
                            if yk == "nh120":
                                y1 = yv[w] == 1; jj.append((g & y1).sum() / max(y1.sum(), 1) - (g & ~y1).sum() / max((~y1).sum(), 1))
                        row[ynm] = q3(vals)[0]
                        if yk == "nh20":
                            row["占觸發日"] = q3(covs)[0]
                    row["J(120日)"] = q3(jj)[0]
                    RT.append(row)
        # 查核長表
        if xi == 1:
            q0 = LEV[NEWN]
            for c in cells:
                w = ROWS[c]
                for lb, nm in ((1, "會再拉"), (0, "沒再拉")):
                    ww = w[lab[w] == lb]; CL.append({"格": S5.cell_name(c), "項": f"x20 {nm}數", "值": float(len(ww))})
                    CL.append({"格": S5.cell_name(c), "項": f"x20 {nm}深度中位", "值": float(np.median(lw["回落深度"][ww])) if len(ww) else np.nan})
                    dd = q0[3][ww]; CL.append({"格": S5.cell_name(c), "項": f"x20 {nm}涵蓋｜{q0[0]}", "值": float((dd[dd > 0] == q0[5]).mean()) if (dd > 0).any() else np.nan})
                CL.append({"格": S5.cell_name(c), "項": "x20 頂後又越過P數", "值": float((lab[w] == 2).sum())})
        for nm_, m_ in (("會再拉（中段底 Lk）", lab == 1), ("沒再拉（頂後底）", lab == 0), ("頂後底之後又越過 P", lab == 2), ("中段底 L2", (lab == 1) & (lw["k"] == 2)),
                        ("中段底 L3", (lab == 1) & (lw["k"] == 3)), ("中段底 L4 以後", (lab == 1) & (lw["k"] >= 4))):
            per = np.bincount(lw["cell"][m_], minlength=250)[cl]
            GRPN.append({"x": xs_, "組": nm_, "點數": int(m_.sum()), "事件≥30 的格": int((per >= 30).sum()), "深度中位（格中位）": q3([np.median(lw["回落深度"][m_ & (lw["cell"] == c)]) for c in cl[per >= 30]])[0] if (per >= 30).any() else np.nan})
        log(f"[x＝{xs_}] 完成 {time.time() - T0:.0f}s（選入 {len(pk_)}）")
    P1 = pd.DataFrame(P1); P1.to_csv(os.path.join(OUT, "part1_pull_features.csv"), index=False, float_format="%.5g")
    P2 = pd.DataFrame(P2); P2.to_csv(os.path.join(OUT, "part2_single.csv.gz"), index=False, float_format="%.5g")
    CAL = pd.DataFrame(CAL); CAL.to_csv(os.path.join(OUT, "part2_score_calib.csv"), index=False, float_format="%.5g")
    RT = pd.DataFrame(RT); RT.to_csv(os.path.join(OUT, "part3_realtime.csv"), index=False, float_format="%.5g")
    SEL = pd.DataFrame(SEL); SEL.to_csv(os.path.join(OUT, "part2_selected.csv"), index=False)
    GRPN = pd.DataFrame(GRPN); GRPN.to_csv(os.path.join(OUT, "groups.csv"), index=False, float_format="%.5g")
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    MST = {}
    for (xv, K), g in RT[RT["段"] == "探索"].groupby(["x", "K"]):
        g = g.sort_values(["J(120日)", "分數≥"], ascending=[False, True]); MST[f"{xv}_K{K}"] = int(g["分數≥"].iloc[0]) if g["J(120日)"].notna().any() else 0
    RT["m*"] = [r["分數≥"] == MST.get(f"{r['x']}_K{r['K']}", -1) for r in RT.to_dict("records")]; RT.to_csv(os.path.join(OUT, "part3_realtime.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "五等分分界（探索段低點）": BND, "當下可用版 m*": MST, "警語": "中段底、頂後底都是事後才知道；只有觸發日版當下能用", "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, P1, P2, CAL, RT, SEL, GRPN)
    log(f"[完] {time.time() - T0:.0f}s")


STRUCT = ("前面已完成段數", "從t起累積漲幅", "前段漲幅")
WARN_S = "<br><small>⚠ 構造使然，不可當訊號</small>"


def is_struct(nm):
    return nm.startswith(STRUCT)


def page(META, P1, P2, CAL, RT, SEL, GRPN):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}.ok{border-left:4px solid #2b6cb0;padding:6px 10px;background:#eef4fb}"
            "tr.m td{background:#fdecea;font-weight:bold}.sel{position:sticky;top:0;background:#fff;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}")
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>中段底再拉一段判斷</title>", f"<style>{CSS}</style></head><body><main>", "<h1>拉回的低點：會再拉一段，還是就此結束？（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 中段底（拉回後還會再創新高的低點）、頂後底（真頂之後第一次回落的低點）都是事後才知道的。第一、二部分用「事後已知這天是低點」的點；"
         "<b>只有第三部分「回落第一次達到 x% 那天」當下真的能用</b>。本件是看過前幾份結果之後才加的，只當描述與參考，沒有計入檢定數。</p>",
         "<p class='note'>中段底當天的一般特徵（Q 表各級距）已在「飆股中段高低點整理」那頁，這裡只放新的「拉回狀態」特徵與判斷。</p>",
         f"<p class='lead'>{META['合格格數']} 種飆股定義各算一次取中位數；探索 2021–2023 選、確認 2024–2026-08 驗。讀法寫死 {html.escape(META['讀法寫死'])}。</p>"]
    x0 = "20%"; p1 = P1[P1["x"] == x0]
    p1 = p1[~p1["特徵"].map(is_struct)]
    more = p1[p1["差(會再拉−沒再拉)"] >= 0.10].sort_values("差(會再拉−沒再拉)", ascending=False); less = p1[p1["差(會再拉−沒再拉)"] <= -0.10].sort_values("差(會再拉−沒再拉)")
    H.append("<h2>先講結論（以拉回 20% 為例；其他用下方選單）</h2><p class='note'>⚠ 「前面已完成段數」「從起漲累積漲幅」「前段漲幅」三項：頂後底在定義上一定跟在整段漲完之後，差距是構造使然、不可當訊號，下面結論已排除。</p><ul>")
    H.append("<li><b>會再拉的底比較常見</b>：" + ("、".join(f"{html.escape(r['特徵'])}（{P_(r['會再拉'])} 對 {P_(r['沒再拉'])}）" for r in more.head(5).to_dict("records")) or "沒有差 10 個百分點以上的") + "。</li>")
    H.append("<li><b>就此結束的底比較常見</b>：" + ("、".join(f"{html.escape(r['特徵'])}（{P_(r['沒再拉'])} 對 {P_(r['會再拉'])}）" for r in less.head(5).to_dict("records")) or "沒有差 10 個百分點以上的") + "。</li>")
    c = CAL[(CAL["x"] == x0) & (CAL["K"].astype(str) == "5") & (CAL["段"] == "確認")]
    if len(c):
        b0 = c[c["分數≥"] == 0].iloc[0]; k_ = int(c["實際特徵數"].iloc[0]); r = c[c["分數≥"] == max(1, (k_ + 1) // 2)].iloc[0]
        H.append(f"<li><b>低點分數（K＝5）確認段</b>（⚠ 用事後已知的低點、含構造使然的特徵，數字偏樂觀）：全部低點裡會再拉占 {P_(b0['會再拉的比例'])}；分數 ≥ {int(r['分數≥'])} 時 {P_(r['會再拉的比例'])}，抓到 {P_(r['抓到會再拉的幾成'])} 的會再拉、誤抓 {P_(r['誤抓頂後底的幾成'])} 的頂後底。</li>")
    rt = RT[(RT["x"] == x0) & (RT["K"].astype(str) == "5") & (RT["段"] == "確認")]
    if len(rt):
        b0 = rt[rt["分數≥"] == 0].iloc[0]; ms = rt[rt["m*"]].iloc[0] if rt["m*"].any() else b0
        H.append(f"<li class='ok'><b>當下可用版（回落第一次達到 20% 那天，K＝5）確認段</b>：全部之後 120 日內再創新高 {P_(b0['120日內再創新高'])}；分數 ≥ {int(ms['分數≥'])}（探索段定的讀法）時 {P_(ms['120日內再創新高'])}，"
                 f"占觸發日 {P_(ms['占觸發日'])}；60 日內再跌 20% {P_(ms['60日內再跌20%'])}（全部 {P_(b0['60日內再跌20%'])}）。</li>")
    H.append("</ul>")
    H.append("<div class='sel'>拉回門檻<select id='sx' onchange='sw()'>" + "".join(f"<option value='{v}'>{v}%</option>" for v in (10, 20, 30)) + "</select></div>")
    for xv in ("10%", "20%", "30%"):
        H.append(f"<div class='pane' id='p{xv[:-1]}'>")
        g = GRPN[GRPN["x"] == xv]
        H.append("<h2>零、兩類低點各有多少</h2><div class='wrap'><table><tr><th class='l'>組</th><th>點數</th><th>可用格</th><th>回落深度（中位）</th></tr>")
        for r in g.to_dict("records"):
            H.append(f"<tr><td class='l'>{html.escape(r['組'])}</td><td>{r['點數']:,}</td><td>{r['事件≥30 的格']}</td><td>{P_(r['深度中位（格中位）'])}</td></tr>")
        H.append("</table></div>")
        p1 = P1[P1["x"] == xv].copy(); p1["_a"] = p1["差(會再拉−沒再拉)"].abs()
        H.append("<h2>一、拉回狀態：會再拉 vs 就此結束（兩段合併）</h2>")
        for cat in ["拉回幅度與時間", "量", "籌碼", "均線與支撐", "處置", "漲勢位置"]:
            sub = p1[p1["分類"] == cat].sort_values("差(會再拉−沒再拉)", ascending=False)
            if not len(sub):
                continue
            H.append(f"<h3>{cat}</h3><div class='wrap'><table><tr><th class='l'>特徵</th><th>會再拉</th><th>沒再拉</th><th>差</th></tr>")
            for r in sub.to_dict("records"):
                H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}{WARN_S if is_struct(r['特徵']) else ''}</td><td>{P_(r['會再拉'])}</td><td>{P_(r['沒再拉'])}</td><td>{P_(r['差(會再拉−沒再拉)'])}</td></tr>")
            H.append("</table></div>")
        p2 = P2[(P2["x"] == xv)].sort_values("探索 倍數", ascending=False).head(15)
        H.append("<h2>二、單一特徵：有它時會再拉的機率是平常的幾倍（探索前 15、確認照報）</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>探索 倍數（下緣）</th><th>確認 倍數（下緣）</th></tr>")
        for r in p2.to_dict("records"):
            H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}{WARN_S if is_struct(r['特徵']) else ''}</td><td>{X_(r['探索 倍數'])}（{X_(r['探索 倍數下緣'])}）</td><td>{X_(r['確認 倍數'])}（{X_(r['確認 倍數下緣'])}）</td></tr>")
        H.append("</table></div>")
        H.append("<p class='warn'>⚠ 下面的低點分數用的是事後才知道的低點，而且選入的特徵含構造使然的項目（標 ⚠ 者），數字偏樂觀；當下真的能用的請看第三部分。</p>")
        for K in KS:
            c = CAL[(CAL["x"] == xv) & (CAL["K"].astype(str) == str(K)) & (CAL["段"] == "確認")]
            if not len(c):
                continue
            names = SEL[(SEL["x"] == xv) & (SEL["K"].astype(str) == str(K))]["特徵"].tolist()
            nms = "、".join(html.escape(x_) + ("（⚠ 構造使然）" if is_struct(x_) else "") for x_ in names[:8])
            H.append(f"<h3>低點分數 K＝{K}（{nms}{'…' if len(names) > 8 else ''}）確認段</h3><div class='wrap'><table><tr><th>分數 ≥</th><th>會再拉</th><th>抓到會再拉</th><th>誤抓頂後底</th><th>占低點</th></tr>")
            for r in c.to_dict("records"):
                H.append(f"<tr><td>{int(r['分數≥'])}</td><td>{P_(r['會再拉的比例'])}</td><td>{P_(r['抓到會再拉的幾成'])}</td><td>{P_(r['誤抓頂後底的幾成'])}</td><td>{P_(r['占低點比例'])}</td></tr>")
            H.append("</table></div>")
        H.append("<h2>三、當下可用版：回落第一次達到 x% 那天算分數（確認段）</h2><p class='note'>⭐ 只有這一版當下真的能用：從當時最高收盤跌到 x% 的那天就知道自己在拉回，看之後會不會再創新高。紅列 ＝ 探索段定的讀法。</p>")
        for K in (5, "全部"):
            s = RT[(RT["x"] == xv) & (RT["K"].astype(str) == str(K)) & (RT["段"] == "確認")]
            if not len(s):
                continue
            H.append(f"<h3>K＝{K}</h3><div class='wrap'><table><tr><th>分數 ≥</th><th>20日內創高</th><th>60日內</th><th>120日內</th><th>60日內再跌10%</th><th>再跌20%</th><th>占觸發日</th></tr>")
            for r in s.to_dict("records"):
                H.append(f"<tr class='{'m' if r['m*'] else ''}'><td>{int(r['分數≥'])}</td><td>{P_(r['20日內再創新高'])}</td><td>{P_(r['60日內再創新高'])}</td><td>{P_(r['120日內再創新高'])}</td><td>{P_(r['60日內再跌10%'])}</td><td>{P_(r['60日內再跌20%'])}</td><td>{P_(r['占觸發日'])}</td></tr>")
            H.append("</table></div>")
        H.append("</div>")
    H.append("<script>function sw(){var x=document.getElementById('sx').value;document.querySelectorAll('.pane').forEach(e=>e.classList.toggle('on',e.id=='p'+x))}document.getElementById('sx').value='20';sw()</script></main></body></html>")
    open(os.path.join(OUT, "中段底再拉一段判斷.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    it = [v for v in CL["項"].unique() if v.startswith("x20 會再拉涵蓋｜")][0]; fname = it.split("｜", 1)[1]
    lv = next(l for l in FT.levels() if f"{l[4]}｜{l[3]}" == fname); q = np.asarray(Qm[lv[0]])
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False); errs = []; info = {}; D.DATA = S5.ST; CF = {}
    for c in pick:
        nm = S5.cell_name(c); k = np.flatnonzero(E["cell"] == c); pts = {1: [], 0: [], 2: []}
        for i in k:
            s, t, P = int(E["s"][i]), int(E["d"][i]), int(E["P"][i])
            if s not in CF:
                CF[s] = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].ffill().to_numpy(float)
            cf = CF[s]; pk, pkd, tv, tvd = cf[t], t, np.inf, -1
            for d in range(t + 1, P + 1):
                v = cf[d]
                if v > pk:
                    if pkd > t and tv <= pk * 0.8 * (1 + 1e-9):
                        pts[1].append((s, tvd, tv / pk - 1))
                    pk, pkd, tv, tvd = v, d, np.inf, -1
                elif v < tv:
                    tv, tvd = v, d
            cP = cf[P]; d = P + 1
            while d <= t1 and cf[d] > cP * 0.8 * (1 + 1e-9):
                d += 1
            if d <= t1:
                lo, ld = cf[d], d; d += 1
                while d <= t1 and cf[d] < lo * 1.2:
                    if cf[d] < lo:
                        lo, ld = cf[d], d
                    d += 1
                over = (cf[ld + 1:t1 + 1] > cP).any()
                pts[2 if over else 0].append((s, ld, lo / cP - 1))
        got = {"x20 會再拉數": len(pts[1]), "x20 沒再拉數": len(pts[0]), "x20 頂後又越過P數": len(pts[2]),
               "x20 會再拉深度中位": float(np.median([p[2] for p in pts[1]])) if pts[1] else np.nan, "x20 沒再拉深度中位": float(np.median([p[2] for p in pts[0]])) if pts[0] else np.nan}
        for lb, nmk in ((1, "會再拉"), (0, "沒再拉")):
            v = np.array([q[s, d] for s, d, _ in pts[lb]]); got[f"x20 {nmk}涵蓋｜{fname}"] = (v[v > 0] == lv[2]).mean() if (v > 0).any() else np.nan
        for kk, mine in got.items():
            ref = CL[(CL["格"] == nm) & (CL["項"] == kk)]["值"].iloc[0]
            if not np.isclose(mine, ref, rtol=1e-5, equal_nan=True):
                errs.append(f"{nm} {kk}：{mine} 檔 {ref}")
        info[nm] = got
    out = {"抽格": list(info), "比對": info, "錯誤數": len(errs), "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 錯誤 {len(errs)}｜{errs[:4]}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    if a.page:                                                                     # 只重產網頁（讀既有 csv，不重算）
        rd = lambda f: pd.read_csv(os.path.join(OUT, f))
        page(json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8")), rd("part1_pull_features.csv"), rd("part2_single.csv.gz"), rd("part2_score_calib.csv"),
             rd("part3_realtime.csv"), rd("part2_selected.csv"), rd("groups.csv"))
        print("網頁已重產"); return
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
