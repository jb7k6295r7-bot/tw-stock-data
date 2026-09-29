# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：網路流傳的「飆股結束訊號」驗證（⛔ 只描述：不判定、不計 N、不挑格）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_exitsig_desc [--check]

⚠ 真頂 P、中段頂 Hk 都是事後才知道的；B 的對象是「事後挑出的真飆股」，照做結果不能直接外推到一般持股。

═══ 讀法（寫死於 2026-09-29 21:29（台北），在算任何數字之前；門檻一律用五等分或網格、每個版本都報）═══
 ⭐ 協調者兩次更正（使用者：「忘記抱固定天數」「假頂是我要的中間段的頂」）都在開算前收到，已直接寫進 E3～E6；⛔ 本件沒有「抱到 t＋h」的對照，也不引用以前任何固定持有天數的結論
 E1 資料：seq6 events（2021-01～2026-08、右截斷 2026-08-31）；價量用還原 OHLC（D.load_stock）；訊號日在 d 收盤可判；2026-08-31 之後的訊號日一律不看
    五等分同 seq5 S10（當日有 K 棒的橫斷面、同值同組）；Q 表（s5work）有的直接用
 E2 訊號版本（25 個）：
    S1 高檔爆量長黑（4 版）＝ 量 {當日額÷前 20 日均額 Q5（Q 表 ar_20）｜當日額 ＞ 前 20 根 K 棒最大額} × 黑 K {實體 (開−收)÷前收 當日橫斷面 Q5｜收 − 低 ≤ 0.2×(高 − 低)}，且收 ＜ 開
    S2 爆量黑 K 後 3 根內收盤跌破該黑 K 最低（對應 S1 四版＋「任一 S1」聯集版；訊號日 ＝ 跌破那天，同一根黑 K 只取第一次）
    S3 收盤跌破 MA5／MA10／MA20（還原收盤、K 棒序列均線；前一根收盤 ≥ 前一根均線）
    S4 跳空跌破：開 ＜ 前一根最低 且 收 ＜ 前一根最低（缺口未回補）
    S5 資增價跌：融資 5 日變化÷股本 Q5（Q 表 mchg_5）且 5 日報酬 ＜ 0（F 表 r_5）
    S6 法人轉賣：外資 5、10 日、投信 5、10 日 淨買÷股本 Q1（4 版）
    S7 處置（main disposal 起訖）：進入 ＝ 起日；第二次 ＝ 起日前 60 個交易日內另有一次起日；出關 ＝ 迄日的下一個交易日
    S8 利多不漲：營收年增 Q5（Q 表 yoy）的可得日當天收黑且 收 ≤ 開 ×（1 − x），x ∈ {2%, 5%}；
       可得日 ＝ 月營收：次月 10 日之後第一個交易日（同 seq5；⚠ 資料沒有逐家實際公布日）｜季報：A2 可得日（共 4 版）
 E3 段頂：照 mid_desc M2／M2b 切段，x ∈ {10, 20, 30, 50}%；中段頂 ＝ H1…H(段數−1)，真頂 ＝ P；L1 ＝ t、L(k＋1) ＝ 第 k 次拉回低點；組 ＝ x × 總段數 × 第幾段（5 段以上的 H5 以後合併）
    另加「x 的所有中段頂」合併組
 E4 A 視窗出現率（逐格算、取格中位；某組在某格 ＜ 30 點不進該格，照報可用格）：各訊號在 [點−5, 點＋5]、[點, 點＋10] 至少出現一次的比例；
    點 ＝ 中段頂 Hk（各組）、真頂 P、6 成點 D60（progress_desc）；一般股-日 ＝ V5 定義域每個股-日當中心的 [d−5, d＋5]；視窗超過 2026-08-31 的部分截掉
    「比較常出現」＝ 出現率 ÷ 一般 ≥ 1.5；兩邊（真頂、x＝20% 所有中段頂）都 ＜ 1.5 ⇒「兩邊都不準」（只是描述用的分類）
 E5 A 之二：每個事件 (t, min(P＋5, 2026-08-31)] 內的每個訊號日 d：就在真頂 ±5 日、就在某個中段頂 ±5 日（x ＝ 10／20／30 各一欄）；
    之後 20／60 日再創新高（(d, d＋h] 最高收盤 ＞ [t, d] 最高收盤；d＋h ≤ 2026-08-31 才算）；之後 60 日內回落 20／30%（相對 d 收盤）；逐格比例取格中位（訊號日 ≥ 30 的格）
 E6 B 照做、評「離頂多近」（每個事件列；t＋1 開盤買，買價 ＝ 還原開盤 o[t＋1]，須有效）：
    規則 ＝ 訊號在 [t＋1, 2026-08-31] 第一次出現於 d ⇒ d 之後第一個有效開盤賣（須 ≤ 2026-08-31）；三層 ＝ 跌破 MA5、S2 任一 S1 版、跌破 MA20 各賣 1/3（各自隔日開盤），
    賣價 ＝ 三個賣價平均；某一層到資料尾都沒觸發 ⇒ 該層以最後一個有效收盤計（標「未觸發」）；三層的賣出日 ＝ 三個賣出日平均
    對真頂 P：賣價 ÷ c[P]；吃到幾成 ＝ (賣價 − 買價) ÷ (c[P] − 買價)；賣出日 − P（負 ＝ 提早）；
      賣早了（d ＜ P）：比例、賣後到 P 還漲 c[P] ÷ 賣價 − 1｜賣晚了（d ≥ P）：比例、賣價 ÷ c[P] − 1｜都沒出現：比例、最後有效收盤（資料尾或下市）÷ c[P] − 1
    對最近的段頂（同一 x 的切段；依訊號日 d 找 |d − 段頂| 最小的 Hk 或 P）：賣價 ÷ c[段頂]；吃到該段幾成 ＝ (賣價 − c[L_k]) ÷ (c[H_k] − c[L_k])；賣出日 − 段頂；
      最近的是中段頂且賣出日 ≤ L(k＋1) ⇒ 躲過的拉回 ＝ c[L(k＋1)] ÷ 賣價 − 1
    彙總：每格事件中位（比例用平均）→ 格中位附 p10～p90；對段頂那套依 x × 總段數（1、2、3、4、5 段以上）分開，格內事件 ＜ 30 不進
    依「吃到真頂漲幅的幾成」排序
 E7 一般股-日對照：V5 列中訊號出現的股-日，出現後 20／60 日（c[d＋h] ÷ c[d] − 1，須 hdef6 ≥ h）的漲跌分佈（中位、p25、p75、跌的比例），並列全部股-日
 E8 查核（--check）：抽 2 格，pandas 逐根重算 S3 MA20 與 S4 訊號日、真頂 [P−5, P＋5] 出現比例；抽 50 個事件列重算 MA20 規則的賣價與吃到幾成
輸出 backtest/resultsSurge6/exitsig_desc/
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

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5
from backtest import researchSurge6_end_desc as ED
from backtest import researchSurge6_mid_desc as MD
from backtest import researchSurge6_progress_desc as PG

D = S5.D
TIME = "2026-09-29 21:29（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/exitsig_desc"
HS = list(S5.HS); GS = list(S5.GS)
XS = (0.10, 0.20, 0.30, 0.50)
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_
SIGS = ["S1 量Q5×實體Q5", "S1 量Q5×收近低", "S1 量創20日高×實體Q5", "S1 量創20日高×收近低",
        "S2 破黑K低(量Q5×實體Q5)", "S2 破黑K低(量Q5×收近低)", "S2 破黑K低(量創高×實體Q5)", "S2 破黑K低(量創高×收近低)", "S2 破黑K低(任一S1)",
        "S3 跌破MA5", "S3 跌破MA10", "S3 跌破MA20", "S4 跳空跌破未回補", "S5 資增價跌",
        "S6 外資5日賣超Q1", "S6 外資10日賣超Q1", "S6 投信5日賣超Q1", "S6 投信10日賣超Q1",
        "S7 進入處置", "S7 第二次處置", "S7 處置出關", "S8 營收利多收黑≥2%", "S8 營收利多收黑≥5%", "S8 季報利多收黑≥2%", "S8 季報利多收黑≥5%"]
SX = {s: i for i, s in enumerate(SIGS)}; NV = len(SIGS)
THREE = "三層出場（MA5／破黑K低／MA20 各 1/3）"
RULES = SIGS + [THREE]; NR = len(RULES)
TEXT = {"S1": "高檔爆量長黑", "S2": "爆量黑 K 後 3 日內跌破黑 K 低點", "S3": "跌破 5／10／20 日線", "S4": "跳空跌破不回補",
        "S5": "融資增、股價跌", "S6": "外資／投信轉賣", "S7": "處置（進入、第二次、出關）", "S8": "利多（營收／財報好）卻收長黑"}
CLS = ["1", "2", "3", "4", "5+"]


def signals(uni, cal, n, bar, t1, log):
    """⇒ SIG (NV, S, n) bool、C（還原收盤 ffill）、O（還原開盤）"""
    S = len(uni)
    W, _ = S5.world(log)
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); FX = S5.FIX
    qar = np.asarray(Qm[FX["ar_20"]]); qm5 = np.asarray(Qm[FX["mchg_5"]]); r5 = np.asarray(Fm[FX["r_5"]]); qyoy = np.asarray(Qm[FX["yoy"]])
    qf5, qf10, qt5, qt10 = (np.asarray(Qm[FX[c]]) for c in ("fnet_5", "fnet_10", "tnet_5", "tnet_10"))
    C = np.full((S, n), np.nan, np.float32); O = np.full((S, n), np.nan, np.float32); BODY = np.full((S, n), np.nan, np.float32)
    SIG = np.zeros((NV, S, n), bool); AUX = {}
    for s in range(S):
        st = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal)
        if st is None:
            continue
        df = st.df; c = df["close"].to_numpy(float); o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
        amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)
        idx = np.flatnonzero(np.isfinite(c) & bar[s])
        C[s] = pd.Series(c).ffill().to_numpy(); O[s, idx] = o[idx]
        if len(idx) < 3:
            continue
        cb, ob, hb, lb, ab = c[idx], o[idx], h[idx], l[idx], amt[idx]
        pc = np.r_[np.nan, cb[:-1]]; pl = np.r_[np.nan, lb[:-1]]
        BODY[s, idx] = (ob - cb) / pc
        mx20 = np.r_[np.nan, pd.Series(ab).rolling(20, min_periods=20).max().to_numpy()[:-1]]
        blk = cb < ob; nearlow = (cb - lb) <= 0.2 * (hb - lb)
        AUX[s] = (idx, blk, nearlow, ab > mx20, lb, cb)
        for j, w in ((9, 5), (10, 10), (11, 20)):
            ma = pd.Series(cb).rolling(w, min_periods=w).mean().to_numpy(); pma = np.r_[np.nan, ma[:-1]]
            SIG[j, s, idx] = (cb < ma) & (pc >= pma)
        SIG[12, s, idx] = (ob < pl) & (cb < pl)
    log("[訊號] 價量讀完")
    # 實體五等分（當日橫斷面、同值同組）
    BQ = np.zeros((S, n), np.int8)
    for d in range(n):
        b = bar[:, d] & np.isfinite(BODY[:, d])
        if b.sum() >= 5:
            BQ[b, d] = S5.qtie(BODY[b, d])
    for s, (idx, blk, nearlow, vmx, lb, cb) in AUX.items():
        vq = qar[s, idx] == 5; bq = BQ[s, idx] == 5
        s1 = [blk & vq & bq, blk & vq & nearlow, blk & vmx & bq, blk & vmx & nearlow]
        for j, f in enumerate(s1):
            SIG[j, s, idx] = f
        m = len(idx)
        for j, f in enumerate(s1 + [np.any(s1, axis=0)]):
            out = np.zeros(m, bool)
            for k in np.flatnonzero(f):
                for dj in (1, 2, 3):
                    if k + dj < m and cb[k + dj] < lb[k]:
                        out[k + dj] = True; break
            SIG[4 + j, s, idx] = out
    log("[訊號] S1、S2 完成")
    SIG[13] = (qm5 == 5) & (np.nan_to_num(r5, nan=0) < 0) & bar
    for j, q in zip((14, 15, 16, 17), (qf5, qf10, qt5, qt10)):
        SIG[j] = (q == 1) & bar
    sid2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    for sd, iv in W["DISP"].items():
        if sd not in sid2i:
            continue
        s = sid2i[sd]; starts = sorted(a for a, b in iv)
        for a, b in iv:
            if 0 <= a < n:
                SIG[18, s, a] = True
                if any(0 < a - x <= 60 for x in starts if x != a):
                    SIG[19, s, a] = True
            if 0 <= b + 1 < n:
                SIG[20, s, b + 1] = True
    revd = np.unique(W["REV_EFF"][(W["REV_EFF"] >= 0) & (W["REV_EFF"] < n)])
    rev_mask = np.zeros(n, bool); rev_mask[revd] = True
    Cr = np.where(bar, C, np.nan)
    down = {x: (Cr <= O * (1 - x)) for x in (0.02, 0.05)}
    for j, x in ((21, 0.02), (22, 0.05)):
        SIG[j] = rev_mask[None, :] & (qyoy == 5) & down[x] & bar
    a2 = np.zeros((S, n), bool)
    for sd, fr in W["FIN"].items():
        if sd in sid2i:
            for x in fr:
                if 0 <= x[0] < n:
                    a2[sid2i[sd], x[0]] = True
    for j, x in ((23, 0.02), (24, 0.05)):
        SIG[j] = a2 & (qyoy == 5) & down[x] & bar
    SIG[:, :, t1 + 1:] = False
    log(f"[訊號] 全部完成；各版訊號日數：{dict(zip(SIGS, SIG.sum((1, 2)).tolist()))}")
    return SIG, C, O




def segtops(c, t, P):
    """⇒ {xi: (tops[], lows[])}；tops 含 P（最後一個），lows[0] ＝ t。"""
    pbs = MD.pullbacks(c[t:P + 1])
    out = {}
    for xi, x in enumerate(XS):
        cuts = [(a, b) for a, b, lo, hi in pbs if a > 0 and lo <= hi * (1 - x) * (1 + 1e-9)]
        out[xi] = (np.array([t + a for a, _ in cuts] + [P]), np.array([t] + [t + b for _, b in cuts]))
    return out


def cls_of(ns):
    return "5+" if ns >= 5 else str(ns)


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int); nev = len(es)
    HC = np.array([HS[c // len(GS)] for c in range(250)]); Hset = sorted({HC[c] for c in cells})
    SIG, C, O = signals(uni, cal, n, bar, t1, log)
    CS = np.zeros((NV, SIG.shape[1], n + 1), np.int32); np.cumsum(SIG, axis=2, out=CS[:, :, 1:])
    clip = lambda x: np.clip(x, 0, t1)
    # ── 切段
    SEGS = [None] * nev
    for s in np.unique(es):
        c = C[s].astype(float); memo = {}
        for i in np.flatnonzero(es == s):
            k = (ed[i], Pv[i])
            if k not in memo:
                memo[k] = segtops(c, ed[i], Pv[i])
            SEGS[i] = memo[k]
    d60, _ = PG.progress_days(uni, cal, E)
    log(f"[切段] 完成 {time.time() - T0:.0f}s")
    # ── A 點
    GR = ["真頂 P", "6 成點 D60"] + [f"{int(x * 100)}%｜所有中段頂" for x in XS[:]]
    for x in XS:
        for cl in CLS[1:]:
            for k in range(1, 5 if cl != "5+" else 6):
                if cl != "5+" and k > int(cl) - 1:
                    continue
                GR.append(f"{int(x * 100)}%｜{cl}段｜{'H5以後' if k == 5 else f'H{k}'}")
    GI = {g: i for i, g in enumerate(GR)}
    ps, pdd, pc, pg = [es], [Pv], [ec], [np.full(nev, 0)]
    ps.append(es); pdd.append(d60); pc.append(ec); pg.append(np.full(nev, 1))
    xs_, xd_, xc_, xg_ = [], [], [], []
    for i in range(nev):
        for xi, x in enumerate(XS):
            tops, _ = SEGS[i][xi]; ns = len(tops); cl = cls_of(ns)
            for k, hk in enumerate(tops[:-1], 1):
                lab = f"{int(x * 100)}%｜{cl}段｜{'H5以後' if (cl == '5+' and k >= 5) else f'H{k}'}"
                for g in (GI[lab], GI[f"{int(x * 100)}%｜所有中段頂"]):
                    xs_.append(es[i]); xd_.append(hk); xc_.append(ec[i]); xg_.append(g)
    ps.append(np.array(xs_)); pdd.append(np.array(xd_)); pc.append(np.array(xc_)); pg.append(np.array(xg_))
    ps, pdd, pc, pg = (np.concatenate(v).astype(np.int64) for v in (ps, pdd, pc, pg))
    NGR = len(GR); npt = np.bincount(pg * 250 + pc, minlength=NGR * 250).reshape(NGR, 250)
    UC = {g: [c for c in cells if npt[g, c] >= 30] for g in range(NGR)}
    rs, rt = np.nonzero(bar & inseg[None, :]); rh = np.minimum(h6[rs, rt].astype(np.int64), 250)
    AR = []
    for v, sg in enumerate(SIGS):
        hg = (CS[v, rs, clip(rt + 5) + 1] - CS[v, rs, clip(rt - 5)]) > 0
        g_ = np.bincount(rh, weights=hg, minlength=251); nn = np.bincount(rh, minlength=251)
        gcum, ncum = np.cumsum(g_[::-1])[::-1], np.cumsum(nn[::-1])[::-1]
        for wn, (a, b) in (("±5", (-5, 5)), ("0～＋10", (0, 10))):
            hit = (CS[v, ps, clip(pdd + b) + 1] - CS[v, ps, clip(pdd + a)]) > 0
            sh = np.bincount(pg * 250 + pc, weights=hit, minlength=NGR * 250).reshape(NGR, 250) / np.maximum(npt, 1)
            for g, gn in enumerate(GR):
                if not UC[g]:
                    AR.append({"訊號": sg, "點": gn, "視窗": wn, "可用格": 0}); continue
                y = q3(sh[g, UC[g]]); gm = q3([gcum[HC[c]] / ncum[HC[c]] for c in UC[g]])[0]
                AR.append({"訊號": sg, "點": gn, "視窗": wn, "可用格": len(UC[g]), "出現率 中位": y[0], "p10": y[1], "p90": y[2], "一般 11 日": gm,
                           "倍數": y[0] / gm if gm > 0 else np.nan})
    AR = pd.DataFrame(AR); AR.to_csv(os.path.join(OUT, "A_windows.csv"), index=False, float_format="%.5g")
    pd.DataFrame([{"點": g, "可用格": len(UC[i]), "點數": int(npt[i].sum())} for i, g in enumerate(GR)]).to_csv(os.path.join(OUT, "A_groups.csv"), index=False)
    log(f"[A] 完成 {time.time() - T0:.0f}s")
    # ── A 之二
    FUT = {}
    for s in np.unique(es):
        c = C[s].astype(float); rv = pd.Series(c[::-1])
        f = {}
        for h in (20, 60):
            mx = rv.rolling(h, min_periods=h).max().to_numpy()[::-1]; mn = rv.rolling(h, min_periods=h).min().to_numpy()[::-1]
            fm = np.r_[mx[1:], np.nan]; fn = np.r_[mn[1:], np.nan]                              # (d, d＋h]
            lim = np.arange(n) + h > t1; fm[lim] = np.nan; fn[lim] = np.nan
            f[h] = (fm, fn)
        FUT[s] = f
    NF = 11; ACC = np.zeros((250, NV, NF))
    for i in range(nev):
        s, t, P = es[i], ed[i], Pv[i]; e = min(P + 5, t1)
        if e <= t:
            continue
        sg = SIG[:, s, t + 1:e + 1]
        if not sg.any():
            continue
        c = C[s]; ds = np.arange(t + 1, e + 1)
        rmax = np.maximum.accumulate(c[t:e + 1].astype(float))[1:]
        f20, _ = FUT[s][20]; f60, m60 = FUT[s][60]
        a20, a60, b60 = f20[ds], f60[ds], m60[ds]
        nearH = []
        for xi in range(3):
            tops = SEGS[i][xi][0][:-1]
            nearH.append(np.abs(ds[:, None] - tops[None, :]).min(1) <= 5 if len(tops) else np.zeros(len(ds), bool))
        ok20 = np.isfinite(a20); ok60 = np.isfinite(a60)
        cols = np.stack([np.ones(len(ds)), np.abs(ds - P) <= 5, *nearH, ok20, ok20 & (a20 > rmax), ok60, ok60 & (a60 > rmax),
                         ok60 & (b60 <= c[ds] * 0.8), ok60 & (b60 <= c[ds] * 0.7)], 1)
        ACC[ec[i]] += sg.astype(float) @ cols
    AF = []
    for v, sg in enumerate(SIGS):
        a = ACC[cells, v]; ok = a[:, 0] >= 30
        with np.errstate(invalid="ignore", divide="ignore"):
            vals = {"就在真頂±5日": a[:, 1] / a[:, 0], "就在中段頂±5日(10%)": a[:, 2] / a[:, 0], "就在中段頂±5日(20%)": a[:, 3] / a[:, 0], "就在中段頂±5日(30%)": a[:, 4] / a[:, 0],
                    "20日內再創新高": a[:, 6] / a[:, 5], "60日內再創新高": a[:, 8] / a[:, 7], "60日內回落20%": a[:, 9] / a[:, 7], "60日內回落30%": a[:, 10] / a[:, 7]}
        r = {"訊號": sg, "可用格": int(ok.sum()), "訊號日數（格加總）": int(a[:, 0].sum())}
        for k_, x in vals.items():
            y = q3(x[ok]) if ok.any() else (np.nan,) * 3; r[k_] = y[0]; r[f"{k_} p10"] = y[1]; r[f"{k_} p90"] = y[2]
        AF.append(r)
    AF = pd.DataFrame(AF); AF.to_csv(os.path.join(OUT, "A_after_signal.csv"), index=False, float_format="%.5g")
    log(f"[A2] 完成 {time.time() - T0:.0f}s")
    # ── B：離頂多近
    FP = ["賣了", "賣早", "賣晚", "沒出現", "賣價÷P", "吃到幾成", "賣出日−P", "賣後到P還漲", "賣晚已從P回落", "沒出現：尾端÷P"]
    FS = ["賣了", "最近是中段頂", "賣價÷段頂", "吃到該段幾成", "賣出日−段頂", "躲過的拉回"]
    MP = np.full((nev, NR, len(FP)), np.nan, np.float32); MS = np.full((len(XS), nev, NR, len(FS)), np.nan, np.float32); CK = []
    for s in np.unique(es):
        ii = np.flatnonzero(es == s); o = O[s].astype(float); c = C[s].astype(float)
        okop = np.isfinite(o) & (o > 0) & bar[s]
        nxo = np.full(n + 2, n + 10, np.int64)
        for p in range(n - 1, -1, -1):
            nxo[p] = p if okop[p] else nxo[p + 1]
        lastb = np.flatnonzero(bar[s][:t1 + 1]); lb = int(lastb[-1]) if len(lastb) else t1; lastc = c[lb]
        pos = [np.flatnonzero(SIG[v, s]) for v in range(NV)]
        T, P = ed[ii], Pv[ii]; bp = o[np.minimum(T + 1, n - 1)]; okb = okop[np.minimum(T + 1, n - 1)]
        dsig = np.full((NR, len(ii)), n + 10); ex = np.full((NR, len(ii)), n + 10); sp = np.full((NR, len(ii)), np.nan)
        for v in range(NV):
            if len(pos[v]):
                j = np.searchsorted(pos[v], T + 1); dsig[v] = np.where(j < len(pos[v]), pos[v][np.minimum(j, len(pos[v]) - 1)], n + 10)
            ex[v] = nxo[np.minimum(dsig[v] + 1, n + 1)]
            sp[v] = np.where(ex[v] <= t1, o[np.minimum(ex[v], n - 1)], np.nan)
        tr = [SX["S3 跌破MA5"], SX["S2 破黑K低(任一S1)"], SX["S3 跌破MA20"]]
        trig = np.array([np.isfinite(sp[k]) for k in tr])
        sp[-1] = np.mean([np.where(trig[j], sp[k], lastc) for j, k in enumerate(tr)], 0)
        ex[-1] = np.round(np.mean([np.where(trig[j], ex[k], lb) for j, k in enumerate(tr)], 0)).astype(int)
        dsig[-1] = np.where(trig.any(0), ex[-1] - 1, n + 10); sp[-1] = np.where(trig.any(0), sp[-1], np.nan)
        cP = c[P]
        for r_ in range(NR):
            sold = np.isfinite(sp[r_]) & okb; none = ~np.isfinite(sp[r_]) & okb
            early = sold & (dsig[r_] < P); late = sold & (dsig[r_] >= P)
            with np.errstate(invalid="ignore", divide="ignore"):
                MP[ii, r_, 0] = np.where(okb, sold, np.nan); MP[ii, r_, 1] = np.where(okb, early, np.nan); MP[ii, r_, 2] = np.where(okb, late, np.nan); MP[ii, r_, 3] = np.where(okb, none, np.nan)
                MP[ii, r_, 4] = np.where(sold, sp[r_] / cP, np.nan); MP[ii, r_, 5] = np.where(sold, (sp[r_] - bp) / (cP - bp), np.nan)
                MP[ii, r_, 6] = np.where(sold, ex[r_] - P, np.nan); MP[ii, r_, 7] = np.where(early, cP / sp[r_] - 1, np.nan)
                MP[ii, r_, 8] = np.where(late, sp[r_] / cP - 1, np.nan); MP[ii, r_, 9] = np.where(none, lastc / cP - 1, np.nan)
        j20 = SX["S3 跌破MA20"]
        CK.append(np.c_[np.full(len(ii), s), T, P, sp[j20], MP[ii, j20, 5]])
        for a_, i in enumerate(ii):
            if not okb[a_]:
                continue
            for xi in range(len(XS)):
                tops, lows = SEGS[i][xi]; nt = len(tops)
                d = dsig[:, a_]; sold = np.isfinite(sp[:, a_])
                k = np.abs(d[:, None] - tops[None, :]).argmin(1)
                tp = tops[k]; lo = lows[k]; midt = k < nt - 1
                with np.errstate(invalid="ignore", divide="ignore"):
                    MS[xi, i, :, 0] = sold
                    MS[xi, i, :, 1] = np.where(sold, midt, np.nan)
                    MS[xi, i, :, 2] = np.where(sold, sp[:, a_] / c[tp], np.nan)
                    MS[xi, i, :, 3] = np.where(sold, (sp[:, a_] - c[lo]) / (c[tp] - c[lo]), np.nan)
                    MS[xi, i, :, 4] = np.where(sold, ex[:, a_] - tp, np.nan)
                    nxl = lows[np.minimum(k + 1, nt - 1)]
                    MS[xi, i, :, 5] = np.where(sold & midt & (ex[:, a_] <= nxl), c[nxl] / sp[:, a_] - 1, np.nan)
    log(f"[B] 逐事件完成 {time.time() - T0:.0f}s")
    FRAC = {"賣了", "賣早", "賣晚", "沒出現", "最近是中段頂"}

    def agg(M, fields, rows_by_cell, ucells):
        out = {}
        per = {c: M[rows_by_cell[c]] for c in ucells}
        for fi, f in enumerate(fields):
            vals = np.array([(np.nanmean if f in FRAC else np.nanmedian)(per[c][:, :, fi], axis=0) for c in ucells]) if ucells else np.full((1, NR), np.nan)
            out[f] = [q3(vals[:, r_]) for r_ in range(NR)]
        return out
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    rows = {c: np.flatnonzero(ec == c) for c in cells}
    AP = agg(MP, FP, rows, cells)
    BP = pd.DataFrame([{"規則": rl, **{f: AP[f][r_][0] for f in FP}, "吃到幾成 p10": AP["吃到幾成"][r_][1], "吃到幾成 p90": AP["吃到幾成"][r_][2]} for r_, rl in enumerate(RULES)])
    BP = BP.sort_values("吃到幾成", ascending=False); BP.to_csv(os.path.join(OUT, "B_vs_trueP.csv"), index=False, float_format="%.5g")
    BS = []
    nsx = np.array([[len(SEGS[i][xi][0]) for xi in range(len(XS))] for i in range(nev)])
    for xi, x in enumerate(XS):
        for cl in CLS:
            m_ = np.array([cls_of(v) == cl for v in nsx[:, xi]])
            rb = {c: np.flatnonzero((ec == c) & m_) for c in cells}; uc = [c for c in cells if len(rb[c]) >= 30]
            if not uc:
                BS.append({"x": f"{int(x * 100)}%", "總段數": cl, "規則": "—", "可用格": 0}); continue
            A_ = agg(MS[xi], FS, rb, uc)
            for r_, rl in enumerate(RULES):
                BS.append({"x": f"{int(x * 100)}%", "總段數": cl, "規則": rl, "可用格": len(uc), **{f: A_[f][r_][0] for f in FS}})
    BS = pd.DataFrame(BS); BS.to_csv(os.path.join(OUT, "B_vs_segtop.csv"), index=False, float_format="%.5g")
    pd.DataFrame(np.vstack(CK), columns=["s", "t", "P", "sp", "cap"]).to_csv(os.path.join(OUT, "check_B_ma20.csv.gz"), index=False, float_format="%.8g")
    log(f"[B] 彙總完成 {time.time() - T0:.0f}s")
    # ── 一般股-日：訊號後 20／60 日漲跌
    GA = []
    for h in (20, 60):
        okr = h6[rs, rt] >= h; r_all = C[rs[okr], rt[okr] + h] / C[rs[okr], rt[okr]] - 1
        GA.append({"訊號": "全部股-日", "h": h, "n": int(okr.sum()), "中位": float(np.nanmedian(r_all)), "p25": float(np.nanpercentile(r_all, 25)), "p75": float(np.nanpercentile(r_all, 75)), "跌的比例": float(np.nanmean(r_all < 0))})
        for v, sg in enumerate(SIGS):
            m_ = okr & SIG[v, rs, rt]; rr = C[rs[m_], rt[m_] + h] / C[rs[m_], rt[m_]] - 1
            GA.append({"訊號": sg, "h": h, "n": int(m_.sum()), "中位": float(np.nanmedian(rr)) if m_.any() else np.nan, "p25": float(np.nanpercentile(rr, 25)) if m_.any() else np.nan,
                       "p75": float(np.nanpercentile(rr, 75)) if m_.any() else np.nan, "跌的比例": float(np.nanmean(rr < 0)) if m_.any() else np.nan})
    GA = pd.DataFrame(GA); GA.to_csv(os.path.join(OUT, "G_after_signal.csv"), index=False, float_format="%.5g")
    # 查核用：真頂 ±5 各格
    CL = []
    for v, sg in enumerate(SIGS[:NV]):
        hit = (CS[v, es, clip(Pv + 5) + 1] - CS[v, es, clip(Pv - 5)]) > 0
        shc = np.bincount(ec, weights=hit, minlength=250) / np.maximum(cnt, 1)
        CL += [{"格": S5.cell_name(c), "訊號": sg, "真頂±5": shc[c]} for c in cells]
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    # 結論分類
    CON = []
    for sg in SIGS:
        a = AR[(AR["訊號"] == sg) & (AR["視窗"] == "±5")].set_index("點")
        rt_, rm_ = a.loc["真頂 P", "倍數"], a.loc["20%｜所有中段頂", "倍數"]
        lab = ("真頂、中段頂都常見" if rt_ >= 1.5 and rm_ >= 1.5 else "真頂附近常見" if rt_ >= 1.5 else "中段頂附近常見" if rm_ >= 1.5 else "兩邊都不準")
        CON.append({"訊號": sg, "真頂±5 出現率": a.loc["真頂 P", "出現率 中位"], "中段頂(20%)±5 出現率": a.loc["20%｜所有中段頂", "出現率 中位"], "一般 11 日": a.loc["真頂 P", "一般 11 日"],
                    "真頂倍數": rt_, "中段頂倍數": rm_, "分類": lab})
    CON = pd.DataFrame(CON); CON.to_csv(os.path.join(OUT, "conclusion.csv"), index=False, float_format="%.5g")
    SAY = []
    for fam, txt in TEXT.items():
        sub = CON[CON["訊號"].str.startswith(fam)]; f = AF[AF["訊號"].str.startswith(fam)]; b = BP[BP["規則"].str.startswith(fam)]
        SAY.append({"原文": txt, "資料怎麼說": f"真頂前後 5 日出現 {P_(sub['真頂±5 出現率'].min())}～{P_(sub['真頂±5 出現率'].max())}、中段頂 {P_(sub['中段頂(20%)±5 出現率'].min())}～{P_(sub['中段頂(20%)±5 出現率'].max())}，"
                    f"一般股票任 11 日 {P_(sub['一般 11 日'].min())}～{P_(sub['一般 11 日'].max())}（{('、'.join(sorted(set(sub['分類']))))}）；漲勢中出現後 60 日內再創新高 {P_(f['60日內再創新高'].min())}～{P_(f['60日內再創新高'].max())}；"
                    f"第一次出現就賣，吃到起漲到頂漲幅的 {P_(b['吃到幾成'].min())}～{P_(b['吃到幾成'].max())}（中位）。"})
    SAY = pd.DataFrame(SAY); SAY.to_csv(os.path.join(OUT, "say.csv"), index=False)
    META = {"讀法寫死": TIME, "合格格數": len(cells), "各點組可用格": {g: len(UC[i]) for i, g in enumerate(GR)}, "事件列": nev,
            "警語": "真頂、中段頂都是事後才知道；B 的對象是事後挑出的真飆股", "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, AR, AF, BP, BS, GA, CON, SAY, GR)
    log(f"[完] {time.time() - T0:.0f}s")


def page(META, AR, AF, BP, BS, GA, CON, SAY, GR):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".sel{position:sticky;top:0;background:#fff;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}.hi{background:#fdecea}")
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>網路飆股結束訊號驗證</title>", f"<style>{CSS}</style></head><body><main>", "<h1>網路流傳的「飆股結束訊號」，拿 2021–2026 資料對一對</h1>",
         "<p class='warn'>⚠ 真頂（整段最高點）與中段頂（漲勢中途、回落後又創新高前的高點）都是事後才知道的。「照做」的對象是事後挑出的真飆股；只描述、沒有檢定，不是買賣建議。</p>",
         f"<p class='lead'>{META['合格格數']} 種飆股定義各算一次取中位數。讀法寫死 {html.escape(META['讀法寫死'])}。</p>"]
    H.append("<h2>先講結論</h2>")
    for lab in ["真頂、中段頂都常見", "真頂附近常見", "中段頂附近常見", "兩邊都不準"]:
        sub = CON[CON["分類"] == lab]
        H.append(f"<p><b>{lab}</b>（出現率是一般股票的 1.5 倍以上才算常見）：{html.escape('、'.join(sub['訊號'])) or '沒有'}</p>")
    top = BP.head(3)
    H.append("<p><b>第一次出現就賣，吃到起漲→頂漲幅最多的</b>：" + "；".join(f"{html.escape(r['規則'])} {P_(r['吃到幾成'])}" for r in top.to_dict("records")) + "。</p>")
    H.append("<div class='wrap'><table><tr><th class='l'>原文說的訊號</th><th class='l'>資料怎麼說</th></tr>")
    for r in SAY.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['原文'])}</td><td class='l'><small>{html.escape(r['資料怎麼說'])}</small></td></tr>")
    t3 = BP[BP["規則"] == THREE].iloc[0]
    H.append(f"<tr><td class='l'>三層出場法</td><td class='l'><small>平均賣價吃到起漲→頂漲幅的 {P_(t3['吃到幾成'])}，賣價是頂的 {P_(t3['賣價÷P'])}；平均賣出日比頂 {t3['賣出日−P']:+.0f} 天。</small></td></tr></table></div>")
    H.append("<h2>一、真頂、中段頂附近各出現多少（前後 5 日）</h2><div class='wrap'><table><tr><th class='l'>訊號</th><th>真頂</th><th>中段頂(20%)</th><th>6 成點</th><th>一般任 11 日</th><th>分類</th></tr>")
    ar = AR[AR["視窗"] == "±5"]
    for r in CON.to_dict("records"):
        d6 = ar[(ar["訊號"] == r["訊號"]) & (ar["點"] == "6 成點 D60")]["出現率 中位"].iloc[0]
        H.append(f"<tr><td class='l'>{html.escape(r['訊號'])}</td><td>{P_(r['真頂±5 出現率'])}</td><td>{P_(r['中段頂(20%)±5 出現率'])}</td><td>{P_(d6)}</td><td>{P_(r['一般 11 日'])}</td><td class='l'><small>{r['分類']}</small></td></tr>")
    H.append("</table></div>")
    H.append("<h2>二、第一次出現就賣：離真頂多近（依吃到幾成排序）</h2><p class='note'>吃到幾成 ＝ (賣價 − 買價) ÷ (頂 − 買價)；賣早 ＝ 訊號在頂之前；沒出現 ＝ 到資料尾都沒出現。</p>"
             "<div class='wrap'><table><tr><th class='l'>規則</th><th>吃到幾成</th><th>賣價÷頂</th><th>賣出日−頂</th><th>賣早／賣晚／沒出現</th><th>賣早：之後到頂還漲</th><th>賣晚：已從頂跌</th></tr>")
    for r in BP.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['規則'])}</td><td>{P_(r['吃到幾成'])}</td><td>{P_(r['賣價÷P'])}</td><td>{r['賣出日−P']:+.0f}</td>"
                 f"<td>{P_(r['賣早'])}／{P_(r['賣晚'])}／{P_(r['沒出現'])}</td><td>{P_(r['賣後到P還漲'])}</td><td>{P_(r['賣晚已從P回落'])}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>三、依段數細看</h2><div class='sel'>拉回門檻<select id='sx' onchange='sw()'>" + "".join(f"<option value='{int(x * 100)}'>{int(x * 100)}%</option>" for x in XS) +
             "</select>總段數<select id='sc' onchange='sw()'>" + "".join(f"<option value='{c}'>{c}</option>" for c in CLS) + "</select></div>")
    for x in XS:
        for cl in CLS:
            pid = f"p{int(x * 100)}_{cl.replace('+', 'p')}"
            H.append(f"<div class='pane' id='{pid}'>")
            b = BS[(BS["x"] == f"{int(x * 100)}%") & (BS["總段數"] == cl)]
            if not len(b) or b["可用格"].max() == 0:
                H.append("<p>這個組合事件太少（每格 < 30），不報。</p></div>"); continue
            H.append(f"<h3>{int(x * 100)}% 拉回、{cl} 段：照做賣在離最近的段頂多近（可用 {int(b['可用格'].max())} 格）</h3><div class='wrap'><table><tr><th class='l'>規則</th><th>最近是中段頂</th><th>賣價÷段頂</th><th>吃到該段幾成</th><th>賣出日−段頂</th><th>躲過的拉回</th></tr>")
            for r in b.sort_values("吃到該段幾成", ascending=False).to_dict("records"):
                dd_ = r["賣出日−段頂"]; dds = "—" if not np.isfinite(dd_) else f"{dd_:+.0f}"
                H.append(f"<tr><td class='l'>{html.escape(r['規則'])}</td><td>{P_(r['最近是中段頂'])}</td><td>{P_(r['賣價÷段頂'])}</td><td>{P_(r['吃到該段幾成'])}</td><td>{dds}</td><td>{P_(r['躲過的拉回'])}</td></tr>")
            H.append("</table></div>")
            pts = [g for g in GR if g.startswith(f"{int(x * 100)}%｜{cl}段｜")]
            if pts:
                a = AR[(AR["視窗"] == "±5") & (AR["點"].isin(pts + ["真頂 P"]))]
                H.append("<div class='wrap'><table><tr><th class='l'>訊號（前後 5 日出現率）</th>" + "".join(f"<th>{p.split('｜')[-1]}</th>" for p in pts) + "<th>真頂</th><th>一般</th></tr>")
                for sg in CON["訊號"]:
                    row = a[a["訊號"] == sg].set_index("點")
                    H.append(f"<tr><td class='l'>{html.escape(sg)}</td>" + "".join(f"<td>{P_(row.loc[p, '出現率 中位']) if p in row.index and row.loc[p, '可用格'] > 0 else '—'}</td>" for p in pts)
                             + f"<td>{P_(row.loc['真頂 P', '出現率 中位'])}</td><td>{P_(row.loc['真頂 P', '一般 11 日'])}</td></tr>")
                H.append("</table></div>")
            H.append("</div>")
    H.append("<h2>四、一般股票出現這些訊號之後 20／60 日</h2><div class='wrap'><table><tr><th class='l'>訊號</th><th>20 日中位（跌的比例）</th><th>60 日中位（跌的比例）</th></tr>")
    for sg in ["全部股-日"] + SIGS:
        a = GA[(GA["訊號"] == sg) & (GA["h"] == 20)].iloc[0]; b = GA[(GA["訊號"] == sg) & (GA["h"] == 60)].iloc[0]
        H.append(f"<tr><td class='l'>{html.escape(sg)}</td><td>{P_(a['中位'])}（{P_(a['跌的比例'])}）</td><td>{P_(b['中位'])}（{P_(b['跌的比例'])}）</td></tr>")
    H.append("</table></div>")
    H.append("<script>function sw(){var x=document.getElementById('sx').value,c=document.getElementById('sc').value.replace('+','p');document.querySelectorAll('.pane').forEach(e=>e.classList.toggle('on',e.id=='p'+x+'_'+c))}sw()</script></main></body></html>")
    open(os.path.join(OUT, "網路飆股結束訊號驗證.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); BC = pd.read_csv(os.path.join(OUT, "check_B_ma20.csv.gz"))
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False); errs = []; info = {}
    D.DATA = S5.ST; cache = {}

    def sigs(s):
        if s not in cache:
            df = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df
            b = pd.DataFrame({"c": df["close"], "o": df["open"], "l": df["low"]})[bar[s]].dropna(subset=["c"])
            ma = b["c"].rolling(20).mean()
            s3 = (b["c"] < ma) & (b["c"].shift() >= ma.shift()); s4 = (b["o"] < b["l"].shift()) & (b["c"] < b["l"].shift())
            pos = np.array([cal.get_loc(x) for x in b.index])
            cache[s] = (sorted(set(pos[s3.to_numpy()]) - set(range(t1 + 1, n))), sorted(set(pos[s4.to_numpy()]) - set(range(t1 + 1, n))), df)
        return cache[s]
    for c in pick:
        nm = S5.cell_name(c); k = np.flatnonzero(E["cell"] == c); hits = {"S3 跌破MA20": [], "S4 跳空跌破未回補": []}
        for i in k:
            s, P = int(E["s"][i]), int(E["P"][i]); s3, s4, _ = sigs(s)
            hits["S3 跌破MA20"].append(any(P - 5 <= d <= min(P + 5, t1) for d in s3)); hits["S4 跳空跌破未回補"].append(any(P - 5 <= d <= min(P + 5, t1) for d in s4))
        for sg, v in hits.items():
            mine = float(np.mean(v)); ref = CL[(CL["格"] == nm) & (CL["訊號"] == sg)]["真頂±5"].iloc[0]
            info[f"{nm} {sg}"] = [mine, float(ref)]
            if not np.isclose(mine, ref, rtol=1e-6):
                errs.append(f"{nm} {sg}：{mine} 檔 {ref}")
    sub = BC.dropna(subset=["sp"]).sample(50, random_state=1); nb = 0
    for r in sub.itertuples():
        s, t, P = int(r.s), int(r.t), int(r.P); s3, _, df = sigs(s)
        o = df["open"].to_numpy(float); c = df["close"].ffill().to_numpy(float)
        d = next(x for x in s3 if x >= t + 1); e = d + 1
        while e <= t1 and not (np.isfinite(o[e]) and o[e] > 0 and bar[s, e]):
            e += 1
        sp = o[e]; cap = (sp - o[t + 1]) / (c[P] - o[t + 1])
        nb += int(not (np.isclose(sp, r.sp, rtol=1e-5) and np.isclose(cap, r.cap, rtol=1e-4, atol=1e-6)))
    info["B MA20 抽 50 列賣價與吃到幾成不同"] = nb
    if nb:
        errs.append(f"B 不同 {nb}")
    out = {"抽格": [S5.cell_name(c) for c in pick], "比對": info, "錯誤數": len(errs), "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[查核] {out}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
