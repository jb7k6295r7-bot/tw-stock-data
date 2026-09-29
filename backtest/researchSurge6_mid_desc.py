# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：飆股漲勢「分段」的中途高點 Hk、拉回低點 Lk 整理（⛔ 只描述：不判定、不計 N、不挑格）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_mid_desc [--check]

⚠ Hk、Lk 跟最高點 P 一樣，都是事後才知道的：當下無法確定那天是中途高點或拉回低點。

═══ 讀法（寫死於 2026-09-29 20:23（台北），在算任何數字之前；已含協調者更正「三、四段的也要分開」）═══
 M1 對象、格、彙總、一般股-日對照、特徵可得日：同 end_desc（W1～W4、W10）：seq6 events、事件 ≥ 30 的 182 格、逐格算取格中位附 p10～p90、
    一般 ＝ 兩段內有 K 棒且 hdef6 ≥ H 的股-日；特徵看該點當天收盤（含）以前可得，用 s5work Q／F
 M2 分段（x ∈ {10, 20, 30, 50}% 各做一次）：在 [t, P] 的還原收盤（ffill）上，「新高日」＝ 收盤嚴格高於之前 [t, 當日) 最高收盤的日子；
    相鄰兩個新高日 a ＜ b 之間（不含兩端）的最低收盤 ≤ a 收盤 ×（1 − x）⇒ 這次回落算一次「中段拉回」，切出一段：
    Hk ＝ a（該段高點）、L(k+1) ＝ a、b 之間最低收盤那天（同價取最早）；a ＝ t 本身（起漲日就先跌）不算（那是起漲前，不是中途高點）
    段數 ＝ 拉回次數 ＋ 1；最後一段的高點 ＝ P；L1 ＝ t。1 段 ＝ 一路沒有回落 ≥ x% 就漲到頂
 M2b（2026-09-29 20:35（台北）補；查核抓到：原本用「最低 ÷ 高點 − 1 ≤ −x」比，剛好回落 x% 的（例 100→80）會被浮點誤差判成沒到；還沒看任何結果數字）
    ⇒ 改成「最低收盤 ≤ 高點 ×（1 − x）×（1 ＋ 1e−9）」，同 seq5 S5 的浮點處理
 M3 組：依「總段數 × 點」分開：2 段 {H1, L2}；3 段 {H1, L2, H2, L3}；4 段 {H1…L4}；5 段以上 {H1…H4, L2…L5, 「H5以後」, 「L6以後」}（5 段以後的點合併成一組）
    另加對照點：同一批事件的 P（頂）與 t（起漲）
    格門檻：某組在某格的點數 ＜ 30 ⇒ 該格不進該組的格中位；照報每組可用格數；可用格 0 的組不報
 M4 六塊（每組）同 end_desc：① 涵蓋率（全部級距；前 20 排非「原：」、原門檻另表）；② 納入 ＝ 涵蓋率 ≥ 10% 且 倍數 ＞ 1、一個概念只留一個（概念對照同 end_desc W6），
    ⛔ 不限數量；兩兩 P(B|A)、Jaccard、同時有幾個（0～K 逐個＋至少幾個）、前 10 組合（組合一般股-日比例只算前 10 名）；
    ③ 階段 2×2（同 end_desc W7）；④ 前 1／3／5／10 天（同批 ② 特徵）；⑤ 隔天（同 end_desc W9）；⑥ 資料可得時點（同 W10）
 M5 對照：每個 Hk 對同一批事件的 P、每個 Lk 對同一批事件的 t：同一批特徵（該 Hk／Lk 組的 ② 納入）兩邊涵蓋率並列；
    另報全部非「原：」級距涵蓋率的相關係數與平均絕對差（「像不像」的一個數）
 M6 各段描述（每個 x × 總段數）：第 k 段漲幅 ＝ c[Hk] ÷ c[Lk] − 1（L1 ＝ t、最後 H ＝ P）、上漲天數 Hk − Lk；第 k 次拉回深度 ＝ c[L(k+1)] ÷ c[Hk] − 1、天數 L(k+1) − Hk；
    H1 在整段漲幅的位置 ＝ (c[H1] − c[t]) ÷ (c[P] − c[t])；天數一律日曆交易日索引差；各段數的事件比例（1、2、3、4、5 段以上）
    5 段以上的第 5 段以後合併成「第 5 段以後」
 M7 查核（--check）：抽 2 格，用逐日狀態機（另寫）重算 x＝20% 的段數分佈與 H1／L2 位置、一組一個級距的涵蓋率、該組 2×2 ⇒ 對長表
輸出 backtest/resultsSurge6/mid_desc/
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5
from backtest import researchSurge5_feat as FT
from backtest import researchSurge6_end_desc as ED

D = S5.D
TIME = "2026-09-29 20:23（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/mid_desc"
XS = (0.10, 0.20, 0.30, 0.50)
PTS = {"2": ["H1", "L2"], "3": ["H1", "L2", "H2", "L3"], "4": ["H1", "L2", "H2", "L3", "H3", "L4"],
       "5+": ["H1", "L2", "H2", "L3", "H3", "L4", "H4", "L5", "H5以後", "L6以後"]}
REF = ["P（頂）", "t（起漲）"]
GROUPS = [(x, cl, pt) for x in XS for cl in PTS for pt in PTS[cl] + REF]
GID = {g: i for i, g in enumerate(GROUPS)}
NG = len(GROUPS); MINPT = 30
HS = list(S5.HS); GS = list(S5.GS)
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_


def gname(g):
    return f"{int(g[0] * 100)}%｜{g[1]}段｜{g[2]}"


def cls_of(nseg):
    return "5+" if nseg >= 5 else str(nseg)


def pullbacks(cs):
    """cs：[t..P] 還原收盤 ⇒ [(a, trough, depth)]，a ＝ 新高日（相對位置），只列 a、下一個新高日之間至少隔一天者。"""
    rm = np.maximum.accumulate(cs)
    nh = np.flatnonzero(cs[1:] > rm[:-1]) + 1
    pk = np.r_[0, nh]
    out = []
    gaps = np.flatnonzero(np.diff(pk) >= 2)
    for j in gaps:
        a, b = int(pk[j]), int(pk[j + 1])
        seg = cs[a + 1:b]; k = int(np.argmin(seg))
        out.append((a, a + 1 + k, float(seg[k]), float(cs[a])))
    return out


def build(uni, cal, E, log):
    """⇒ PT（點表）、SEGD（各段描述）、NSEG（段數）"""
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    PT = {k: [] for k in ("x", "ev", "g", "day")}; SEGR = []; NS = np.zeros((len(XS), len(es)), np.int16)
    D.DATA = S5.ST
    for s in np.unique(es):
        ii = np.flatnonzero(es == s)
        cff = pd.Series(D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].to_numpy(float)).ffill().to_numpy()
        memo = {}
        for i in ii:
            t, P = int(ed[i]), int(Pv[i])
            if (t, P) not in memo:
                memo[(t, P)] = pullbacks(cff[t:P + 1])
            pbs = memo[(t, P)]
            for xi, x in enumerate(XS):
                cuts = [(a, b) for a, b, lo, hi in pbs if a > 0 and lo <= hi * (1 - x) * (1 + 1e-9)]     # M2b
                ns = len(cuts) + 1; NS[xi, i] = ns
                if ns == 1:
                    continue
                cl = cls_of(ns)
                Hs = [t + a for a, _ in cuts] + [P]; Ls = [t] + [t + b for _, b in cuts]
                for k in range(1, ns):                                      # Hk（k＝1…ns−1）
                    pt = f"H{k}" if (cl != "5+" or k <= 4) else "H5以後"
                    PT["x"].append(xi); PT["ev"].append(i); PT["g"].append(GID[(x, cl, pt)]); PT["day"].append(Hs[k - 1])
                for k in range(2, ns + 1):                                  # Lk（k＝2…ns）
                    pt = f"L{k}" if (cl != "5+" or k <= 5) else "L6以後"
                    PT["x"].append(xi); PT["ev"].append(i); PT["g"].append(GID[(x, cl, pt)]); PT["day"].append(Ls[k - 1])
                for rp, day in ((REF[0], P), (REF[1], t)):
                    PT["x"].append(xi); PT["ev"].append(i); PT["g"].append(GID[(x, cl, rp)]); PT["day"].append(day)
                for k in range(1, ns + 1):
                    L_, H_ = Ls[k - 1], Hs[k - 1]
                    r = {"x": xi, "ev": i, "段數": ns, "段": min(k, 5), "漲幅": cff[H_] / cff[L_] - 1, "上漲天數": H_ - L_}
                    if k < ns:
                        r.update({"拉回深度": cff[Ls[k]] / cff[H_] - 1, "拉回天數": Ls[k] - H_})
                    if k == 1:
                        r["H1位置"] = (cff[H_] - cff[t]) / (cff[P] - cff[t]) if cff[P] > cff[t] else np.nan
                    SEGR.append(r)
    PT = {k: np.asarray(v, np.int64) for k, v in PT.items()}
    log(f"[分段] 點 {len(PT['g']):,}｜段列 {len(SEGR):,}")
    return PT, pd.DataFrame(SEGR), NS


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    HC = np.array([HS[c // len(GS)] for c in range(250)]); Hset = sorted({HC[c] for c in cells})
    PT, SEGR, NS = build(uni, cal, E, log)
    ps, pd_, pg, pc = es[PT["ev"]], PT["day"], PT["g"], ec[PT["ev"]]
    npt = np.bincount(pg * 250 + pc, minlength=NG * 250).reshape(NG, 250)
    UC = {g: [c for c in cells if npt[g, c] >= MINPT] for g in range(NG)}
    # 段數分佈
    SD = []
    for xi, x in enumerate(XS):
        for k in range(1, 6):
            v = [np.mean(np.minimum(NS[xi, ec == c], 5) == k) for c in cells]; y = q3(v)
            SD.append({"x": f"{int(x * 100)}%", "段數": "5 段以上" if k == 5 else f"{k} 段", "事件比例 中位": y[0], "p10": y[1], "p90": y[2]})
    SD = pd.DataFrame(SD); SD.to_csv(os.path.join(OUT, "segment_count.csv"), index=False, float_format="%.5g")
    # 各段描述
    SEGR["cell"] = ec[SEGR["ev"].to_numpy()]; SEGR["cls"] = [cls_of(v) for v in SEGR["段數"]]
    SG = []
    for (xi, cl, k), g in SEGR.groupby(["x", "cls", "段"]):
        per = g.groupby("cell").agg(n=("漲幅", "size"), 漲幅=("漲幅", "median"), 上漲天數=("上漲天數", "median"), 拉回深度=("拉回深度", "median"),
                                   拉回天數=("拉回天數", "median"), H1位置=("H1位置", "median"))
        per = per[per["n"] >= MINPT]
        r = {"x": f"{int(XS[xi] * 100)}%", "總段數": cl, "第幾段": "第 5 段以後" if k == 5 else f"第 {k} 段", "可用格": len(per)}
        for col in ("漲幅", "上漲天數", "拉回深度", "拉回天數", "H1位置"):
            y = q3(per[col]) if len(per) else (np.nan,) * 3
            r[f"{col} 中位"], r[f"{col} p10"], r[f"{col} p90"] = y
        SG.append(r)
    SG = pd.DataFrame(SG); SG.to_csv(os.path.join(OUT, "segments.csv"), index=False, float_format="%.5g")
    log(f"[各段] 完成 {time.time() - T0:.0f}s")
    # ① 涵蓋率：全部級距 × 組 × 格
    LV = FT.levels(); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")
    rs, rt = np.nonzero(bar & inseg[None, :]); rh = np.minimum(h6[rs, rt].astype(np.int64), 250)
    covS = {}; covG = {}
    for fi in sorted({x[0] for x in LV}):
        q = np.asarray(Qm[fi]); qv = q[ps, pd_].astype(np.int64)
        m = np.bincount((pg * 250 + pc) * 7 + qv, minlength=NG * 250 * 7).reshape(NG, 250, 7)
        gg = np.bincount(q[rs, rt].astype(np.int64) * 251 + rh, minlength=7 * 251).reshape(7, 251)
        ge = np.cumsum(gg[:, ::-1], axis=1)[:, ::-1]
        with np.errstate(invalid="ignore", divide="ignore"):
            den = m[:, :, 1:].sum(2)
            for lv in [x for x in LV if x[0] == fi]:
                covS[(fi, lv[2])] = m[:, :, lv[2]] / den                                  # (NG, 250)
                covG[(fi, lv[2])] = {H: ge[lv[2], H] / ge[1:, H].sum() for H in Hset}
    log(f"[①] 涵蓋率完成 {time.time() - T0:.0f}s")
    COV = []
    for g in range(NG):
        uc = UC[g]
        if not uc:
            continue
        for lv in LV:
            s_ = q3(covS[(lv[0], lv[2])][g, uc]); gm = q3([covG[(lv[0], lv[2])][HC[c]] for c in uc])[0]
            COV.append({"組": gname(GROUPS[g]), "gi": g, "特徵": f"{lv[4]}｜{lv[3]}", "欄": lv[1], "碼": lv[2], "概念": ED.concept(lv[1]), "原門檻": lv[1].startswith("d_"),
                        "類別": ED.CAT.get(lv[1], ""), "可得時點": ED.AVAIL.get(ED.CAT.get(lv[1], ""), ""), "可用格": len(uc),
                        "涵蓋率 中位": s_[0], "p10": s_[1], "p90": s_[2], "一般 中位": gm, "倍數": s_[0] / gm if gm > 0 else np.nan})
    COV = pd.DataFrame(COV); COV.to_csv(os.path.join(OUT, "coverage_all.csv.gz"), index=False, float_format="%.5g")
    # ② 納入（每組）
    SELS = {}
    for g, cv in COV.groupby("gi"):
        c_ = cv[(cv["涵蓋率 中位"] >= 0.10) & (cv["倍數"] > 1)].sort_values("涵蓋率 中位", ascending=False)
        SELS[g] = c_.drop_duplicates("概念", keep="first").reset_index(drop=True)
    pd.concat(SELS.values()).to_csv(os.path.join(OUT, "selected.csv"), index=False, float_format="%.5g")
    ucols = sorted({(r["欄"], int(r["碼"])) for s in SELS.values() for r in s[["欄", "碼"]].to_dict("records")})
    UX = {k: i for i, k in enumerate(ucols)}
    log(f"[②] 各組納入 {min(len(s) for s in SELS.values())}～{max(len(s) for s in SELS.values())} 個；聯集 {len(ucols)}")
    FXc = {c: i for i, c in enumerate(S5.FCOL)}
    # 一般股-日 聯集特徵的有／有值（依 h 分桶）
    hb = np.minimum(rh // 10, 25)
    order = np.argsort(hb, kind="stable"); hb_s = hb[order]; bstart = np.searchsorted(hb_s, np.arange(27))
    QC = {col: np.asarray(Qm[FXc[col]]) for col in sorted({c for c, _ in ucols} | {"r_5", "r_120"})}
    GP = np.zeros((len(order), len(ucols)), bool); GD = np.zeros_like(GP)
    for j, (col, code) in enumerate(ucols):
        q = QC[col][rs[order], rt[order]]; GP[:, j] = q == code; GD[:, j] = q > 0
    # 各組重疊
    PR = []; DI = []; CBo = []; CL = []
    for g, sel in SELS.items():
        uc = UC[g]; K = len(sel); idx = [UX[(c, int(k))] for c, k in zip(sel["欄"], sel["碼"])]; names = sel["特徵"].tolist()
        codes = sel["碼"].to_numpy(np.int8); Qsel = [QC[c] for c in sel["欄"]]
        mk = pg == g; sS, sD, sC = ps[mk], pd_[mk], pc[mk]
        qq = np.stack([Q_[sS, sD] for Q_ in Qsel], 1) if K else np.zeros((len(sS), 0), np.int8)
        Pm, Dm = qq == codes[None, :], qq > 0
        SUR = {}
        for c in uc:
            r_ = sC == c; pba, jac = ED.pair_stats(Pm[r_], Dm[r_]); dist, combo = ED.cnt_combo(Pm[r_])
            SUR[c] = (pba, jac, dist, combo)
        # 一般：分桶累加
        GENc = {}
        bb, ba, bd = [], [], []
        for b in range(26):
            sl = slice(bstart[b], bstart[b + 1]); Pf = GP[sl][:, idx].astype(np.float32); Df = GD[sl][:, idx].astype(np.float32)
            bb.append(Pf.T @ Pf); ba.append(Pf.T @ Df); bd.append(np.bincount(GP[sl][:, idx].sum(1), minlength=K + 1))
        cb, ca, cdi = np.cumsum(bb[::-1], 0)[::-1], np.cumsum(ba[::-1], 0)[::-1], np.cumsum(bd[::-1], 0)[::-1]
        for H in Hset:
            i_ = H // 10
            with np.errstate(invalid="ignore", divide="ignore"):
                GENc[H] = (cb[i_] / ca[i_], cb[i_] / (ca[i_] + ca[i_].T - cb[i_]), cdi[i_] / cdi[i_].sum())
        for a in range(K):
            for b in range(K):
                if a != b:
                    x1 = q3([SUR[c][0][a, b] for c in uc]); x2 = q3([SUR[c][1][a, b] for c in uc]); x3 = q3([GENc[HC[c]][0][a, b] for c in uc])
                    PR.append({"組": gname(GROUPS[g]), "A": names[a], "B": names[b], "P(B|A) 中位": x1[0], "p10": x1[1], "p90": x1[2], "Jaccard 中位": x2[0],
                               "一般 P(B|A) 中位": x3[0], "倍數": x1[0] / x3[0] if x3[0] > 0 else np.nan})
        for i in range(K + 1):
            x = q3([SUR[c][2][i] for c in uc]); y = q3([GENc[HC[c]][2][i] for c in uc])
            xa = q3([SUR[c][2][i:].sum() for c in uc]); ya = q3([GENc[HC[c]][2][i:].sum() for c in uc])
            DI.append({"組": gname(GROUPS[g]), "K": K, "同時有幾個": i, "中位": x[0], "p10": x[1], "p90": x[2], "一般 中位": y[0], "至少 中位": xa[0], "至少 一般 中位": ya[0]})
        allm = set()
        for c in uc:
            allm |= {m for m in SUR[c][3] if any(m)}
        cbs = sorted(((float(np.median([SUR[c][3].get(m, 0.0) for c in uc])), m) for m in allm), reverse=True)[:10]
        gpk = np.packbits(GP[:, idx], axis=1) if cbs else None
        for v, m in cbs:
            bits = np.unpackbits(np.frombuffer(m, np.uint8))[:K].astype(bool)
            eq = (gpk == np.frombuffer(m, np.uint8)[None, :]).all(1)
            hb_ = np.bincount(hb_s[eq], minlength=26); nb_ = np.bincount(hb_s, minlength=26); ch = np.cumsum(hb_[::-1])[::-1]; cn = np.cumsum(nb_[::-1])[::-1]
            yd = {H: ch[H // 10] / cn[H // 10] for H in {HC[c] for c in uc}}; ym = float(np.median([yd[HC[c]] for c in uc]))
            CBo.append({"組": gname(GROUPS[g]), "組合": "＋".join(names[i] for i in range(K) if bits[i]), "特徵數": int(bits.sum()), "中位": v, "一般 中位": ym,
                        "倍數": v / ym if ym > 0 else np.nan})
        if K >= 2:
            for c in uc:
                CL.append({"組": gname(GROUPS[g]), "格": S5.cell_name(c), "項": "P(B|A)", "特徵": f"{names[0]}→{names[1]}", "值": SUR[c][0][0, 1]})
    pd.DataFrame(PR).to_csv(os.path.join(OUT, "pairs.csv.gz"), index=False, float_format="%.5g")
    pd.DataFrame(DI).to_csv(os.path.join(OUT, "count_dist.csv"), index=False, float_format="%.5g")
    pd.DataFrame(CBo).to_csv(os.path.join(OUT, "combos_top10.csv"), index=False, float_format="%.5g")
    del GP, GD
    log(f"[②] 重疊完成 {time.time() - T0:.0f}s")
    # ③ 階段 2×2
    q5r = np.asarray(Qm[FXc["r_5"]]); q120 = np.asarray(Qm[FXc["r_120"]]); lu5 = np.asarray(Fm[FXc["lu_5"]]); lu20 = np.asarray(Fm[FXc["lu_20"]])
    A_ = (q5r[ps, pd_] == 5) | (np.nan_to_num(lu5[ps, pd_], nan=0) >= 1); B_ = (q120[ps, pd_] == 5) | (np.nan_to_num(lu20[ps, pd_], nan=0) >= 3)
    quad = np.select([A_ & B_, A_ & ~B_, ~A_ & B_], [0, 1, 2], 3)
    qm = np.bincount((pg * 250 + pc) * 4 + quad, minlength=NG * 250 * 4).reshape(NG, 250, 4)
    QG = {H: ED_quad_general(q5r, q120, lu5, lu20, rs[rh >= H], rt[rh >= H]) for H in Hset}
    QN = ["短線急拉＋之前已大漲", "只有短線急拉", "只有之前已大漲", "兩者皆非"]; STG = []
    for g in range(NG):
        uc = UC[g]
        if not uc:
            continue
        sh = qm[g, uc] / qm[g, uc].sum(1, keepdims=True)
        for i, nm in enumerate(QN):
            x = q3(sh[:, i]); y = q3([QG[HC[c]][i] for c in uc])
            STG.append({"組": gname(GROUPS[g]), "狀態": nm, "中位": x[0], "p10": x[1], "p90": x[2], "一般 中位": y[0], "倍數": x[0] / y[0] if y[0] > 0 else np.nan})
            for j, c in enumerate(uc):
                CL.append({"組": gname(GROUPS[g]), "格": S5.cell_name(c), "項": "階段", "特徵": nm, "值": sh[j, i]})
    pd.DataFrame(STG).to_csv(os.path.join(OUT, "stage_2x2.csv"), index=False, float_format="%.5g")
    # ④ 前 k 天（該組納入特徵）
    SH = []
    for g, sel in SELS.items():
        uc = UC[g]; mk = pg == g; sS, sD, sC = ps[mk], pd_[mk], pc[mk]
        for r in sel.to_dict("records"):
            q = QC[r["欄"]]; row = {"組": gname(GROUPS[g]), "特徵": r["特徵"], "當天": r["涵蓋率 中位"], "一般": r["一般 中位"]}
            for k in ED.SHIFTS:
                v = q[sS, np.maximum(sD - k, 0)].astype(np.int64)
                mm = np.bincount(sC * 7 + v, minlength=250 * 7).reshape(250, 7)
                with np.errstate(invalid="ignore", divide="ignore"):
                    row[f"前{k}天"] = q3((mm[:, r["碼"]] / mm[:, 1:].sum(1))[uc])[0]
            SH.append(row)
    pd.DataFrame(SH).to_csv(os.path.join(OUT, "shift_coverage.csv"), index=False, float_format="%.5g")
    # 覆蓋率長表（查核用：每組第一個納入級距）
    for g, sel in SELS.items():
        if len(sel):
            r = sel.iloc[0]
            for c in UC[g]:
                CL.append({"組": gname(GROUPS[g]), "格": S5.cell_name(c), "項": "涵蓋率", "特徵": r["特徵"], "值": covS[(S5.FIX[r["欄"]], int(r["碼"]))][g, c]})
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    log(f"[③④] 完成 {time.time() - T0:.0f}s")
    # ⑤ 隔天
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    ND = np.full((len(ps), 7), np.nan)
    for s in np.unique(ps):
        ii = np.flatnonzero(ps == s)
        cA, oA, rr, evd = ED._stock_arrays(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal, n)
        bars = np.flatnonzero(bar[s]); memo = {}
        for i in ii:
            p = int(pd_[i])
            if p not in memo:
                memo[p] = ED._nd(p, bars, cA, oA, rr, evd, cal, t1)
            ND[i] = memo[p]
    GND = ED.general_nextday(uni, cal, n, bar, inseg, h6, Hset, log)
    NX = ["收跌停", "盤中碰跌停", "開盤跳空跌≥3%", "收跌≥5%", "收黑"]; NDR = []
    for g in range(NG):
        uc = UC[g]
        if not uc:
            continue
        mk = pg == g; v = ND[mk]; cc = pc[mk]
        per = {nm: [] for nm in NX + ["漲跌中位"]}
        for c in uc:
            w = v[cc == c]; ok = np.isfinite(w[:, 5]); okl = ok & np.isfinite(w[:, 0])
            for i, nm in enumerate(NX):
                mm = okl if i < 2 else ok
                per[nm].append(np.nanmean(w[mm, i]) if mm.any() else np.nan)
            per["漲跌中位"].append(np.nanmedian(w[ok, 5]) if ok.any() else np.nan)
        for nm, vals in per.items():
            x = q3(vals); y = q3([GND[HC[c]][nm] for c in uc])
            NDR.append({"組": gname(GROUPS[g]), "項目": nm, "中位": x[0], "p10": x[1], "p90": x[2], "一般 中位": y[0]})
    NDR = pd.DataFrame(NDR); NDR.to_csv(os.path.join(OUT, "nextday.csv"), index=False, float_format="%.5g")
    log(f"[⑤] 完成 {time.time() - T0:.0f}s")
    # M5 對照
    CMP = []; SIM = []
    for (x, cl, pt), g in GID.items():
        if pt in REF or g not in SELS:
            continue
        ref = GID[(x, cl, REF[0] if pt.startswith("H") else REF[1])]
        if ref not in SELS and not UC[ref]:
            continue
        uc = sorted(set(UC[g]) & set(UC[ref]))
        if not uc:
            continue
        for r in SELS[g].to_dict("records"):
            fi = S5.FIX[r["欄"]]
            CMP.append({"組": gname((x, cl, pt)), "對照": REF[0] if pt.startswith("H") else REF[1], "特徵": r["特徵"], "這個點": q3(covS[(fi, int(r["碼"]))][g, uc])[0],
                        "對照點": q3(covS[(fi, int(r["碼"]))][ref, uc])[0], "一般": r["一般 中位"]})
        a_ = COV[(COV["gi"] == g) & ~COV["原門檻"]].set_index("特徵")["涵蓋率 中位"]; b_ = COV[(COV["gi"] == ref) & ~COV["原門檻"]].set_index("特徵")["涵蓋率 中位"]
        j = a_.index.intersection(b_.index); aa, bb = a_[j].to_numpy(float), b_[j].to_numpy(float); ok = np.isfinite(aa) & np.isfinite(bb)
        SIM.append({"x": f"{int(x * 100)}%", "總段數": cl, "點": pt, "對照": REF[0] if pt.startswith("H") else REF[1], "可用格": len(uc),
                    "相關係數": float(np.corrcoef(aa[ok], bb[ok])[0, 1]) if ok.sum() > 2 else np.nan, "平均絕對差": float(np.mean(np.abs(aa[ok] - bb[ok]))) if ok.any() else np.nan})
    CMP = pd.DataFrame(CMP); CMP.to_csv(os.path.join(OUT, "compare_vs_P_t.csv"), index=False, float_format="%.5g")
    SIM = pd.DataFrame(SIM); SIM.to_csv(os.path.join(OUT, "similarity.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "組數（含對照點）": NG, "各組可用格": {gname(GROUPS[g]): len(UC[g]) for g in range(NG)},
            "各組納入特徵數": {gname(GROUPS[g]): len(s) for g, s in SELS.items()}, "警語": "Hk、Lk、P 都是事後才知道的", "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, SD, SG, COV, SELS, pd.DataFrame(PR), pd.DataFrame(DI), pd.DataFrame(CBo), pd.DataFrame(STG), pd.DataFrame(SH), NDR, CMP, SIM)
    log(f"[完] {time.time() - T0:.0f}s")


def ED_quad_general(q5r, q120, lu5, lu20, s_, t_):
    a = (q5r[s_, t_] == 5) | (np.nan_to_num(lu5[s_, t_], nan=0) >= 1)
    b = (q120[s_, t_] == 5) | (np.nan_to_num(lu20[s_, t_], nan=0) >= 3)
    return np.array([(a & b).mean(), (a & ~b).mean(), (~a & b).mean(), (~a & ~b).mean()])


def page(META, SD, SG, COV, SELS, PR, DI, CB, STG, SH, NDR, CMP, SIM):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".sel{position:sticky;top:0;background:#fff;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}")
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>飆股中段高低點</title>", f"<style>{CSS}</style></head><body><main>", "<h1>飆股漲勢分段：中途高點與拉回低點（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 中途高點（H）、拉回低點（L）跟最高點一樣，都是事後才知道的：當下沒有辦法確定那天是不是中途高點或拉回低點。只描述、沒有檢定。</p>",
         f"<p class='lead'>{META['合格格數']} 種飆股定義各算一次取中位數；某組在某格少於 30 個點就不算那格。拉回 ＝ 從當時最高收盤回落至少 x% 之後又創新高。讀法寫死 {html.escape(META['讀法寫死'])}。</p>"]
    # 結論
    H.append("<h2>先講結論</h2><ul>")
    for x in XS:
        s = SD[SD["x"] == f"{int(x * 100)}%"]; top = s.sort_values("事件比例 中位", ascending=False).iloc[0]
        H.append(f"<li>拉回門檻 {int(x * 100)}%：" + "、".join(f"{r['段數']} {P_(r['事件比例 中位'])}" for r in s.to_dict("records")) + f"；最常見 {top['段數']}。</li>")
    for tgt in REF:
        s = SIM[SIM["對照"] == tgt]
        if len(s):
            H.append(f"<li>{'中途高點 H 對最高點 P' if tgt == REF[0] else '拉回低點 L 對起漲點 t'}：全部級距涵蓋率相關係數中位 {s['相關係數'].median():.2f}（範圍 {s['相關係數'].min():.2f}～{s['相關係數'].max():.2f}），平均絕對差中位 {P_(s['平均絕對差'].median())}。</li>")
    H.append("</ul>")
    H.append("<h2>一、每個拉回門檻下，事件分成幾段</h2><div class='wrap'><table><tr><th>x</th><th>1 段</th><th>2 段</th><th>3 段</th><th>4 段</th><th>5 段以上</th></tr>")
    for x in XS:
        s = SD[SD["x"] == f"{int(x * 100)}%"]["事件比例 中位"].to_list()
        H.append(f"<tr><td>{int(x * 100)}%</td>" + "".join(f"<td>{P_(v)}</td>" for v in s) + "</tr>")
    H.append("</table></div><p class='note'>1 段 ＝ 一路沒有回落 x% 以上就漲到頂。</p>")
    H.append("<h2>二、像不像</h2><p class='note'>把幾百個特徵級距在兩個點的出現比例拿來比：相關係數越接近 1、平均差越小 ＝ 越像。</p><div class='wrap'><table><tr><th>x</th><th>段數</th><th>點</th><th>對照</th><th>相關</th><th>平均差</th><th>可用格</th></tr>")
    for r in SIM.to_dict("records"):
        H.append(f"<tr><td>{r['x']}</td><td>{r['總段數']}</td><td>{r['點']}</td><td>{r['對照']}</td><td>{X_(r['相關係數'])}</td><td>{P_(r['平均絕對差'])}</td><td>{r['可用格']}</td></tr>")
    H.append("</table></div>")
    # 選單
    H.append("<h2>三、分組細看</h2><div class='sel'>拉回門檻<select id='sx' onchange='sw()'>" + "".join(f"<option value='{int(x * 100)}'>{int(x * 100)}%</option>" for x in XS) +
             "</select>總段數<select id='sc' onchange='sw()'>" + "".join(f"<option value='{c}'>{c}</option>" for c in PTS) + "</select></div>")
    for x in XS:
        for cl in PTS:
            pid = f"p{int(x * 100)}_{cl.replace('+', 'p')}"
            H.append(f"<div class='pane' id='{pid}'><h3>{int(x * 100)}% 拉回、{cl} 段：各段漲多少、拉回多深</h3>")
            sg = SG[(SG["x"] == f"{int(x * 100)}%") & (SG["總段數"] == cl)]
            H.append("<div class='wrap'><table><tr><th class='l'>段</th><th>漲幅</th><th>上漲天數</th><th>之後拉回</th><th>拉回天數</th><th>可用格</th></tr>")
            for r in sg.to_dict("records"):
                H.append(f"<tr><td class='l'>{r['第幾段']}</td><td>{P_(r['漲幅 中位'])}</td><td>{ED_n(r['上漲天數 中位'])}</td><td>{P_(r['拉回深度 中位'])}</td><td>{ED_n(r['拉回天數 中位'])}</td><td>{r['可用格']}</td></tr>")
            h1 = sg[sg["第幾段"] == "第 1 段"]
            H.append("</table></div>" + (f"<p class='note'>H1 在整段漲幅的位置（0 ＝ 起漲、1 ＝ 頂）：中位 {X_(h1.iloc[0]['H1位置 中位'])}。</p>" if len(h1) else ""))
            for pt in PTS[cl]:
                g = GID[(x, cl, pt)]; gn = gname((x, cl, pt))
                if g not in SELS:
                    H.append(f"<h4>{pt}：可用格 0，不報</h4>"); continue
                sel = SELS[g]; cv = COV[(COV["gi"] == g) & ~COV["原門檻"]].sort_values("涵蓋率 中位", ascending=False).head(10)
                H.append(f"<h4>{pt}（可用 {META['各組可用格'][gn]} 格；納入 {len(sel)} 個）</h4><div class='wrap'><table><tr><th class='l'>最常見的情況（前 10）</th><th>這個點</th><th>一般</th><th>倍數</th></tr>")
                for r in cv.to_dict("records"):
                    H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}<br><small>{html.escape(r['可得時點'])}</small></td><td>{P_(r['涵蓋率 中位'])}</td><td>{P_(r['一般 中位'])}</td><td>{X_(r['倍數'])}</td></tr>")
                H.append("</table></div>")
                cm = CMP[CMP["組"] == gn].head(10)
                if len(cm):
                    H.append(f"<div class='wrap'><table><tr><th class='l'>同一批特徵對照（前 10）</th><th>{pt}</th><th>{html.escape(cm.iloc[0]['對照'])}</th><th>一般</th></tr>")
                    for r in cm.to_dict("records"):
                        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{P_(r['這個點'])}</td><td>{P_(r['對照點'])}</td><td>{P_(r['一般'])}</td></tr>")
                    H.append("</table></div>")
                st = STG[STG["組"] == gn]; nd = NDR[NDR["組"] == gn].set_index("項目")
                H.append("<p class='note'>階段：" + "；".join(f"{r['狀態']} {P_(r['中位'])}（一般 {P_(r['一般 中位'])}）" for r in st.to_dict("records")) + "</p>")
                if len(nd):
                    H.append(f"<p class='note'>隔天：收跌停 {P_(nd.loc['收跌停', '中位'])}、收跌≥5% {P_(nd.loc['收跌≥5%', '中位'])}、收黑 {P_(nd.loc['收黑', '中位'])}、漲跌中位 {P_(nd.loc['漲跌中位', '中位'])}（一般 {P_(nd.loc['漲跌中位', '一般 中位'])}）。</p>")
                di = DI[DI["組"] == gn]
                if len(di):
                    ktot = int(di["K"].iloc[0]); md = di.iloc[(di["至少 中位"] >= 0.5).to_numpy().nonzero()[0].max()] if (di["至少 中位"] >= 0.5).any() else None
                    H.append(f"<p class='note'>同時有幾個（共 {ktot} 個）：一半的點至少有 {int(md['同時有幾個']) if md is not None else 0} 個（一般股票同數量以上 {P_(md['至少 一般 中位']) if md is not None else '—'}）。完整分佈見 count_dist.csv。</p>")
                pr = PR[PR["組"] == gn].sort_values("倍數", ascending=False).head(5) if len(PR) else PR
                if len(pr):
                    H.append("<p class='note'>最特別的一起出現（倍數前 5）：" + "；".join(f"{html.escape(r['A'])}→{html.escape(r['B'])} {P_(r['P(B|A) 中位'])}（一般 {P_(r['一般 P(B|A) 中位'])}）" for r in pr.to_dict("records")) + "</p>")
            H.append("</div>")
    H.append("<p class='note'>全部數字（兩兩、組合、前 1／3／5／10 天、原門檻版）見 csv。</p>")
    H.append("<script>function sw(){var x=document.getElementById('sx').value,c=document.getElementById('sc').value.replace('+','p');document.querySelectorAll('.pane').forEach(e=>e.classList.toggle('on',e.id=='p'+x+'_'+c))}sw()</script></main></body></html>")
    open(os.path.join(OUT, "飆股中段高低點整理.html"), "w", encoding="utf-8").write("\n".join(H))


def ED_n(v):
    return "—" if v is None or not np.isfinite(v) else f"{v:.0f} 天"


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); SEL = pd.read_csv(os.path.join(OUT, "selected.csv"))
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")
    FX = {c: i for i, c in enumerate(json.load(open(os.path.join(WORK5, "build.json"), encoding="utf-8"))["特徵欄"])}
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False); errs = []; info = {}
    x = 0.20
    for c in pick:
        nm = S5.cell_name(c); k = np.flatnonzero(E["cell"] == c)
        pts = {}
        for i in k:
            s, t, P = int(E["s"][i]), int(E["d"][i]), int(E["P"][i])
            cff = pd.Series(D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].to_numpy(float)).ffill().to_numpy()
            # 逐日狀態機：peak、谷、是否回落過 x
            pk, pkd, tv, tvd = cff[t], t, np.inf, -1; Hs, Ls = [], []
            for d in range(t + 1, P + 1):
                v = cff[d]
                if v > pk:
                    if pkd > t and tv <= pk * (1 - x) * (1 + 1e-9):
                        Hs.append(pkd); Ls.append(tvd)
                    pk, pkd, tv, tvd = v, d, np.inf, -1
                elif v < tv:
                    tv, tvd = v, d
            ns = len(Hs) + 1
            if ns >= 2:
                cl = "5+" if ns >= 5 else str(ns)
                pts.setdefault((cl, "H1"), []).append((s, Hs[0])); pts.setdefault((cl, "L2"), []).append((s, Ls[0]))
        for (cl, pt), lst in pts.items():
            gn = f"20%｜{cl}段｜{pt}"
            if len(lst) < 30:
                continue
            sel = SEL[SEL["組"] == gn]
            ref = CL[(CL["組"] == gn) & (CL["格"] == nm)]
            if not len(sel) or not len(ref):
                continue
            r0 = sel.iloc[0]; q = np.asarray(Qm[FX[r0["欄"]]]); v = np.array([q[s, d] for s, d in lst])
            mine = (v == r0["碼"]).sum() / (v > 0).sum()
            rr = ref[(ref["項"] == "涵蓋率")]
            if len(rr) and not np.isclose(mine, rr.iloc[0]["值"], rtol=1e-6):
                errs.append(f"{nm} {gn} 涵蓋率：{mine} 檔 {rr.iloc[0]['值']}")
            q5 = np.asarray(Qm[FX["r_5"]]); q120 = np.asarray(Qm[FX["r_120"]]); l5 = np.asarray(Fm[FX["lu_5"]]); l20 = np.asarray(Fm[FX["lu_20"]])
            a = np.array([(q5[s, d] == 5) or (np.nan_to_num(l5[s, d]) >= 1) for s, d in lst]); b = np.array([(q120[s, d] == 5) or (np.nan_to_num(l20[s, d]) >= 3) for s, d in lst])
            mine2 = (a & b).mean(); rs_ = ref[(ref["項"] == "階段") & (ref["特徵"] == "短線急拉＋之前已大漲")]
            if len(rs_) and not np.isclose(mine2, rs_.iloc[0]["值"], rtol=1e-6):
                errs.append(f"{nm} {gn} 2×2：{mine2} 檔 {rs_.iloc[0]['值']}")
            info[f"{nm} {gn}"] = [len(lst), float(mine), float(mine2)]
    out = {"抽格": [S5.cell_name(c) for c in pick], "比對（點數／涵蓋率／2×2 第一格）": info, "錯誤數": len(errs), "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[查核] 錯誤 {len(errs)}｜比對 {len(info)} 組")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
