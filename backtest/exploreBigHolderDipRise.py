# -*- coding: utf-8 -*-
"""集保大戶比例升幅前 5%（B60）訊號後一年：大戶比例「先降後升」的涵蓋率與時間——探索、只描述；不判、不計 N。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.exploreBigHolderDipRise

逐週路徑（比例 RAT、股價 PRC、累積報酬 RET、窗內 inwin）一律用 exploreBigHolderLong.build(build76())，⛔ 不另寫訊號或比例算法。
母體：52 週窗完整（inwin 第 0～52 週全在資料尾內）且 53 週中比例至少 48 週有值的筆（同 exploreBigHolderLong 最高點分析）。
缺週照原程式：比例缺的週該格不算（NaN 不參與最低點、回升判定與中位數）。

定義（門檻 0.1pp＝FLAT）：
 累積比例變化 CH[k]＝第 k 週比例 − 第 0 週（訊號週）比例。
 比例低點週 L＝第 1～52 週中 CH 最低的週（同值取最早）；低點深度＝CH[L]。
 先降＝低點深度 < −0.1pp。
 回升週 R＝L 之後第一個 CH > +0.1pp 的週。
 組：先降後升（先降且有 R）｜先降沒回來（先降、無 R）｜沒先降（低點 ≥ −0.1pp）。
 先降後升再分：第 52 週 CH > +0.1pp（仍高於訊號週）／第 52 週 CH ≤ +0.1pp（回升後又跌回）／第 52 週比例缺。
 水下週數＝第 1～R−1 週中 CH < 0 的有值週數。
 股價低點週＝第 1～52 週累積報酬最低的週（同值取最早；第 1 週股價日早於進場日者該格不算）。
粗算版（對照，主線先前用 explore_long/per_event.csv 粗算的口徑）：只看第 4/8/12/52 週（四週比例與第 52 週報酬都有值）；
 「先降」＝第 4/8/12 週最低 < −0.1pp；先降後升＝第 52 週 > +0.1pp、先降後持平＝±0.1pp、先降沒回來＝< −0.1pp。
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from backtest import data as D
from backtest import researchBigHolderRise as R
from backtest import exploreBigHolderLong as BL

OUTD = os.path.join(R.HERE, "resultsBigHolderRise", "explore_dip_rise")
LONG_PER = os.path.join(R.HERE, "resultsBigHolderRise", "explore_long", "per_event.csv")
HMAX = BL.HMAX
FLAT = BL.FLAT
MINCOV = BL.PEAK_MINCOV
flag = BL.flag
ret_stats = BL.ret_stats
pc = BL.pc
WBINS = [("1–4", 1, 4), ("5–8", 5, 8), ("9–12", 9, 12), ("13–26", 13, 26), ("27–52", 27, 52)]
DBINS = [("−0.1～−1pp", -0.01, -FLAT), ("−1～−3pp", -0.03, -0.01), ("−3～−5pp", -0.05, -0.03), ("< −5pp", -np.inf, -0.05)]
OFFS = list(range(-8, 9))
MDSC = [("全部訊號", "合計"), ("全部訊號", "探索"), ("全部訊號", "確認"), ("去重", "合計")]
G_DR, G_DN, G_NO = "先降後升", "先降沒回來", "沒先降"
CG_UP, CG_FL, CG_DN, CG_NO = "先降後升(粗)", "先降後持平(粗)", "先降沒回來(粗)", "沒先降(粗)"
CV_ALL, CV_SUB = "粗算（4 時點，原母體）", "粗算（4 時點，限逐週母體）"
S_UP, S_BK, S_NA ="第52週仍高於訊號週", "回升後又跌回（第52週≤+0.1pp）", "第52週比例缺"


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def pos(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float((x > 0).mean()) if len(x) else np.nan


def binshare(x, bins, kind="w"):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    out = {}
    for lab, a, b in bins:
        if kind == "w":
            k = ((x >= a) & (x <= b)).sum()
        else:
            k = ((x >= a) & (x < b)).sum()
        out[lab] = float(k / n) if n else np.nan
    return out


def per_event(S, RAT, PRC, RET, inwin):
    n = len(S)
    CH = RAT - RAT[:, [0]]
    full = inwin.all(axis=1) & (np.isfinite(RAT).sum(axis=1) >= MINCOV)
    L = np.full(n, -1); Rw = np.full(n, -1); PL = np.full(n, -1); UW = np.full(n, np.nan)
    for i in np.where(full)[0]:
        c = CH[i]
        l = int(np.nanargmin(c[1:])) + 1; L[i] = l
        if c[l] < -FLAT:
            hit = np.where(c[l + 1:] > FLAT)[0]           # NaN 比較為 False ⇒ 缺週不算
            if len(hit):
                r = l + 1 + int(hit[0]); Rw[i] = r
                UW[i] = float((c[1:r] < 0).sum())
        rr = RET[i, 1:]
        if np.isfinite(rr).any():
            PL[i] = int(np.nanargmin(rr)) + 1
    ar = np.arange(n)
    dep = np.where(full, CH[ar, np.clip(L, 0, None)], np.nan)
    g = np.where(~full, "", np.where(dep < -FLAT, np.where(Rw > 0, G_DR, G_DN), G_NO))
    ch52 = CH[:, HMAX]
    sub = np.where(g != G_DR, "", np.where(~np.isfinite(ch52), S_NA, np.where(ch52 > FLAT, S_UP, S_BK)))
    has_r = Rw > 0
    chR = np.where(has_r, CH[ar, np.clip(Rw, 0, None)], np.nan)
    retR = np.where(has_r, RET[ar, np.clip(Rw, 0, None)], np.nan)
    prR = np.where(has_r, PRC[ar, np.clip(Rw, 0, None)], np.nan)
    retL = np.where(full, RET[ar, np.clip(L, 0, None)], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        rR52 = PRC[:, HMAX] / prR - 1
    # 粗算版（6 時點）
    c6 = np.isfinite(CH[:, [4, 8, 12, HMAX]]).all(axis=1) & np.isfinite(RET[:, HMAX])
    dip12 = np.nanmin(np.where(np.isfinite(CH[:, [4, 8, 12]]), CH[:, [4, 8, 12]], np.inf), axis=1) < -FLAT
    gc = np.where(~c6, "", np.where(dip12, np.where(ch52 > FLAT, CG_UP, np.where(ch52 < -FLAT, CG_DN, CG_FL)), CG_NO))
    P = pd.DataFrame({"sid": S.sid.to_numpy(), "資料日": S["資料日"].dt.date.astype(str).to_numpy(),
                      "進場日": S["進場日"].dt.date.astype(str).to_numpy(), "進場年": S["進場日"].dt.year.to_numpy(),
                      "段": S["段"].to_numpy(), "去重": S["去重"].to_numpy(), "逐週母體": full,
                      "組": g, "細分": sub, "粗算組": gc,
                      "比例低點週": np.where(full, L, np.nan), "低點深度": dep,
                      "回升週": np.where(has_r, Rw, np.nan), "水下週數": UW,
                      "股價低點週": np.where(full & (PL > 0), PL, np.nan),
                      "比例變化_w52": ch52, "報酬_w52": RET[:, HMAX],
                      "回升週比例變化": chR, "報酬_低點週": retL, "報酬_回升週": retR, "報酬_回升週到w52": rR52})
    P["回升後比例升幅_R到w52"] = P["比例變化_w52"] - P["回升週比例變化"]
    P["低點到w52比例升幅"] = np.where(full, ch52 - dep, np.nan)
    return P, CH, full


def scope_masks(P):
    for lab, m0 in (("全部訊號", np.ones(len(P), bool)), ("去重", P["去重"].to_numpy(bool))):
        for sg in ("探索", "確認", "合計"):
            m = m0 if sg == "合計" else (m0 & (P["段"] == sg).to_numpy())
            yield lab, sg, m


def main():
    os.makedirs(OUTD, exist_ok=True)
    D.DATA = R.DATA
    R.LOGS.clear()
    R.log(f"[資料] tw-stock-data {R.SHA[:10]}｜探索、只描述（不判、不計 N）")
    Bx = R.build76()
    S, RAT, PRC, RET, IW, inwin, e = BL.build(Bx)
    P, CH, full = per_event(S, RAT, PRC, RET, inwin)
    R.log(f"[逐週母體] 52 週窗完整且比例 ≥{MINCOV} 週有值：{int(full.sum())} / {len(P)}")

    t1 = []; t2 = []; t3 = []; t4 = []; t4b = []; t5 = []; t6 = []; t7 = []
    for lab, sg, m in scope_masks(P):
        Q = P[m & full]; nQ = len(Q)
        # ① 各組占比與一年後
        rows = [("全部", np.ones(nQ, bool)), (G_DR, Q["組"] == G_DR), ("├ " + S_UP, Q["細分"] == S_UP),
                ("├ " + S_BK, Q["細分"] == S_BK), ("├ " + S_NA, Q["細分"] == S_NA), (G_DN, Q["組"] == G_DN), (G_NO, Q["組"] == G_NO)]
        for gname, gm in rows:
            gm = np.asarray(gm, bool); x = Q[gm]
            st = ret_stats(x["報酬_w52"].dropna())
            t1.append({"口徑": lab, "範圍": sg, "版本": "逐週", "組": gname, "N": int(gm.sum()), "占比": float(gm.mean()) if nQ else np.nan,
                       "比例w52變化中位_pp": med(x["比例變化_w52"]) * 100} | {f"報酬w52_{k}": v for k, v in st.items()})
        for ver, Qc in ((CV_ALL, P[m & (P["粗算組"] != "")]), (CV_SUB, Q[Q["粗算組"] != ""])):
            nc = len(Qc)
            for gname in (CG_UP, CG_FL, CG_DN, CG_NO):
                gm = (Qc["粗算組"] == gname).to_numpy(); x = Qc[gm]
                st = ret_stats(x["報酬_w52"].dropna())
                t1.append({"口徑": lab, "範圍": sg, "版本": ver, "組": gname, "N": int(gm.sum()), "占比": float(gm.mean()) if nc else np.nan,
                           "比例w52變化中位_pp": med(x["比例變化_w52"]) * 100} | {f"報酬w52_{k}": v for k, v in st.items()})
        # ② 先降後升的時間
        X = Q[Q["組"] == G_DR]; nx = len(X)
        r2 = {"口徑": lab, "範圍": sg, "N": nx, "註": flag(nx),
              "L週中位": med(X["比例低點週"]), "R週中位": med(X["回升週"]), "R−L週數中位": med(X["回升週"] - X["比例低點週"]),
              "水下週數中位": med(X["水下週數"]), "低點深度中位_pp": med(X["低點深度"]) * 100,
              "回升後到w52比例升幅中位_pp": med(X["回升後比例升幅_R到w52"]) * 100,
              "低點到w52比例升幅中位_pp": med(X["低點到w52比例升幅"]) * 100, "w52比例變化中位_pp": med(X["比例變化_w52"]) * 100}
        r2 |= {f"L週_{k}": v for k, v in binshare(X["比例低點週"], WBINS).items()}
        r2 |= {f"R週_{k}": v for k, v in binshare(X["回升週"], WBINS).items()}
        r2 |= {f"深度_{k}": v for k, v in binshare(X["低點深度"], DBINS, "d").items()}
        t2.append(r2)
        # ③ 依深度／L 週分層（先降者）
        Dp = Q[Q["組"].isin([G_DR, G_DN])]
        for kind, bins, col, kk in (("低點深度", DBINS, "低點深度", "d"), ("比例低點週", WBINS, "比例低點週", "w")):
            for blab, a, b in bins:
                x = Dp[col].to_numpy(float)
                bm = (x >= a) & (x <= b) if kk == "w" else (x >= a) & (x < b)
                Y = Dp[bm]; ny = len(Y); rec = Y["組"] == G_DR
                t3.append({"口徑": lab, "範圍": sg, "分層": kind, "層": blab, "先降筆數": ny, "註": flag(ny),
                           "後來回升占比": float(rec.mean()) if ny else np.nan,
                           "回升且w52仍高占比": float((Y["細分"] == S_UP).mean()) if ny else np.nan,
                           "一年報酬中位_全層": med(Y["報酬_w52"]), "一年報酬中位_有回升": med(Y.loc[rec, "報酬_w52"]),
                           "一年報酬中位_沒回來": med(Y.loc[~rec, "報酬_w52"]), "有回升筆數": int(rec.sum()), "沒回來筆數": int((~rec).sum())})
        # ④ 事件時間對齊
        idx_all = np.where(m & full)[0]
        for anc, gname in (("L", G_DR), ("L", G_DN), ("R", G_DR)):
            ii = idx_all[(P["組"].to_numpy()[idx_all] == gname)]
            a0 = (P["比例低點週"] if anc == "L" else P["回升週"]).to_numpy()[ii].astype(int)
            for off in OFFS:
                k = a0 + off; ok = (k >= 0) & (k <= HMAX)
                rr = RET[ii[ok], k[ok]]; cc = CH[ii[ok], k[ok]]
                t4.append({"口徑": lab, "範圍": sg, "錨": f"{anc}（{gname}）", "相對週": off,
                           "報酬中位": med(rr), "報酬N": int(np.isfinite(rr).sum()), "比例變化中位_pp": med(cc) * 100,
                           "比例N": int(np.isfinite(cc).sum())})
        for gname, gm in ((G_DR, Q["組"] == G_DR), (G_DN, Q["組"] == G_DN), ("先降合計", Q["組"].isin([G_DR, G_DN]))):
            x = Q[np.asarray(gm, bool)].dropna(subset=["股價低點週"])
            dif = (x["股價低點週"] - x["比例低點週"]).to_numpy(float); nd = len(dif)
            t4b.append({"口徑": lab, "範圍": sg, "組": gname, "N": nd, "註": flag(nd),
                        "股價低點先": float((dif < 0).mean()) if nd else np.nan, "同週": float((dif == 0).mean()) if nd else np.nan,
                        "比例低點先": float((dif > 0).mean()) if nd else np.nan,
                        "差距中位_股價減比例": med(dif), "差距絕對值中位": med(np.abs(dif)),
                        "股價低點週中位": med(x["股價低點週"]), "比例低點週中位": med(x["比例低點週"]),
                        "相差≤4週": float((np.abs(dif) <= 4).mean()) if nd else np.nan})
        # ⑤ 回升當下
        for gname, gm in ((G_DR, Q["組"] == G_DR), ("├ " + S_UP, Q["細分"] == S_UP), ("├ " + S_BK, Q["細分"] == S_BK)):
            x = Q[np.asarray(gm, bool)]
            st = ret_stats(x["報酬_回升週到w52"].dropna())
            t5.append({"口徑": lab, "範圍": sg, "組": gname, "N": len(x), "R週報酬中位": med(x["報酬_回升週"]), "R週報酬為正": pos(x["報酬_回升週"]),
                       "R週比例變化中位_pp": med(x["回升週比例變化"]) * 100} | {f"R到w52_{k}": v for k, v in st.items()})
        # ⑥ 先降後升 vs 先降沒回來 並排
        for gname in (G_DR, G_DN, G_NO):
            x = Q[Q["組"] == gname]; st = ret_stats(x["報酬_w52"].dropna())
            r6 = {"口徑": lab, "範圍": sg, "組": gname, "N": len(x), "註": flag(len(x)), "L週中位": med(x["比例低點週"]),
                  "低點深度中位_pp": med(x["低點深度"]) * 100, "L週報酬中位": med(x["報酬_低點週"]), "L週報酬為正": pos(x["報酬_低點週"]),
                  "股價低點週中位": med(x["股價低點週"]), "w52比例變化中位_pp": med(x["比例變化_w52"]) * 100}
            r6 |= {f"L週_{k}": v for k, v in binshare(x["比例低點週"], WBINS).items()}
            r6 |= {f"深度_{k}": v for k, v in binshare(x["低點深度"], DBINS, "d").items()}
            t6.append(r6 | {f"報酬w52_{k}": v for k, v in st.items()})
        # ⑦ 依進場年
        if sg == "合計":
            for yr, x in Q.groupby("進場年"):
                ny = len(x); xr = x[x["組"] == G_DR]
                t7.append({"口徑": lab, "進場年": int(yr), "N": ny, "註": flag(ny),
                           "先降後升占比": float((x["組"] == G_DR).mean()), "其中w52仍高占比": float((x["細分"] == S_UP).mean()),
                           "先降沒回來占比": float((x["組"] == G_DN).mean()), "沒先降占比": float((x["組"] == G_NO).mean()),
                           "先降後升筆數": len(xr), "先降後升_一年報酬中位": med(xr["報酬_w52"]), "全部_一年報酬中位": med(x["報酬_w52"])})
    T1 = pd.DataFrame(t1); T2 = pd.DataFrame(t2); T3 = pd.DataFrame(t3); T4 = pd.DataFrame(t4); T4B = pd.DataFrame(t4b)
    T5 = pd.DataFrame(t5); T6 = pd.DataFrame(t6); T7 = pd.DataFrame(t7)

    chk = selfcheck(P, T1, full)
    w = lambda df, f: df.to_csv(os.path.join(OUTD, f), index=False, encoding="utf-8-sig", float_format="%.6g")
    w(P[P["逐週母體"] | (P["粗算組"] != "")], "per_event.csv")
    w(T1, "t1_groups.csv"); w(T2, "t2_dip_rise_timing.csv"); w(T3, "t3_strata.csv"); w(T4, "t4_event_align.csv")
    w(T4B, "t4_low_order.csv"); w(T5, "t5_at_recovery.csv"); w(T6, "t6_side_by_side.csv"); w(T7, "t7_by_year.csv")
    write_md(P, full, T1, T2, T3, T4, T4B, T5, T6, T7, chk, Bx)
    with open(os.path.join(OUTD, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(R.LOGS) + "\n")


def selfcheck(P, T1, full):
    out = []
    for lab, sg, m in scope_masks(P):
        Q = P[m & full]
        s = int(Q["組"].isin([G_DR, G_DN, G_NO]).sum()); ss = int(Q["細分"].isin([S_UP, S_BK, S_NA]).sum())
        ok = (s == len(Q)) and (ss == int((Q["組"] == G_DR).sum()))
        out.append(f"{lab}/{sg}：三組合計 {s} ＝ 母體 {len(Q)}；先降後升細分合計 {ss} ＝ {int((Q['組'] == G_DR).sum())} → {'OK' if ok else '不符'}")
        assert ok
    # 與 explore_long/per_event.csv 交叉驗
    L = pd.read_csv(LONG_PER, dtype={"sid": str}, encoding="utf-8-sig")
    M = P.merge(L[["sid", "資料日", "比例變化_w52", "報酬_w52"]], on=["sid", "資料日"], how="left", suffixes=("", "_long"), indicator=True)
    nmiss = int((M["_merge"] != "both").sum())
    out.append(f"與 explore_long/per_event.csv 逐筆對應：{len(M)} 筆中未對到 {nmiss} 筆；w52 報酬有值 {int(M['報酬_w52_long'].notna().sum())}（本檔 {int(P['報酬_w52'].notna().sum())}）")
    assert nmiss == 0 and len(M) == len(P)
    for col in ("比例變化_w52", "報酬_w52"):
        a = M[col].map(lambda x: "nan" if not np.isfinite(x) else f"{x:.6g}")
        b = M[f"{col}_long"].map(lambda x: "nan" if not np.isfinite(x) else f"{x:.6g}")
        nd = int((a != b).sum())
        out.append(f"{col}：逐筆與 explore_long/per_event.csv 比（%.6g 字串）不一致 {nd} 筆／{len(M)}")
        assert nd == 0
    # 重算表 1 兩三格（用 explore_long 的 w52 數字＋本檔分組）
    Mf = M[M["逐週母體"]]
    for gname in (G_DR, G_DN):
        x = Mf[Mf["組"] == gname]
        t = T1[(T1["口徑"] == "全部訊號") & (T1["範圍"] == "合計") & (T1["版本"] == "逐週") & (T1["組"] == gname)].iloc[0]
        a1 = float(x["報酬_w52_long"].dropna().median()); a2 = float(x["比例變化_w52_long"].dropna().median()) * 100; a3 = len(x) / len(Mf)
        ok = abs(a1 - t["報酬w52_中位"]) < 1e-5 and abs(a2 - t["比例w52變化中位_pp"]) < 1e-3 and abs(a3 - t["占比"]) < 1e-12
        out.append(f"表1 全部訊號/{gname}：占比 {a3:.6f} vs {t['占比']:.6f}｜一年報酬中位 {a1:.6f} vs {t['報酬w52_中位']:.6f}｜比例 w52 中位 {a2:.4f} vs {t['比例w52變化中位_pp']:.4f} pp → {'OK' if ok else '不符'}")
        assert ok
    # 粗算版從 explore_long/per_event.csv 直接重算
    c = L.dropna(subset=["比例變化_w4", "比例變化_w8", "比例變化_w12", "比例變化_w52", "報酬_w52"])
    d12 = c[["比例變化_w4", "比例變化_w8", "比例變化_w12"]].min(axis=1) < -FLAT
    gdr = c[d12 & (c["比例變化_w52"] > FLAT)]; gdn = c[d12 & (c["比例變化_w52"] < -FLAT)]
    t = T1[(T1["口徑"] == "全部訊號") & (T1["範圍"] == "合計") & (T1["版本"] == CV_ALL)].set_index("組")
    out.append(f"粗算版由 explore_long/per_event.csv 直接重算：N {len(c)}｜先降後升 {len(gdr)}（{len(gdr) / len(c):.1%}，中位 {gdr['報酬_w52'].median():+.1%}）"
               f"｜先降沒回來 {len(gdn)}（{len(gdn) / len(c):.1%}，中位 {gdn['報酬_w52'].median():+.1%}）；本程式 {int(t['N'].sum())}／{int(t.loc[CG_UP, 'N'])}／{int(t.loc[CG_DN, 'N'])}")
    assert len(c) == int(t["N"].sum()) and len(gdr) == int(t.loc[CG_UP, "N"]) and len(gdn) == int(t.loc[CG_DN, "N"])
    for s in out:
        R.log("[自檢] " + s)
    return out


def pp(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x:+.{d}f}"


def wk(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:.0f}"


def sel(T, lab, sg):
    return T[(T["口徑"] == lab) & (T["範圍"] == sg)]


def write_md(P, full, T1, T2, T3, T4, T4B, T5, T6, T7, chk, Bx):
    dates = Bx["dates"]; cal = Bx["cal"]
    nall = len(P); nf = int(full.sum())
    Lm = ["# B60 訊號後一年：大戶比例「先降後升」有多少、什麼時候、股價怎麼走", "",
          "**探索、只描述；不判、不計 N。**（不是出場或加碼訊號測試、不是事前預測；不與抱固定天數比較）", "",
          f"回測線計算子代理｜資料 tw-stock-data `{R.SHA[:10]}`（價格到 {cal[-1].date()}、集保到 {dates.iloc[-1].date()}）｜程式 `backtest/exploreBigHolderDipRise.py`"
          "（逐週路徑全用 `exploreBigHolderLong.build(researchBigHolderRise.build76())`，不另寫訊號或比例算法）", "",
          "## 〇、口徑與⚠", "",
          f"- 母體：B60 訊號 {nall} 筆（同 `explore_long`）中，**52 週窗完整**（第 0～52 週都在資料尾內）且 53 週中比例至少 {MINCOV} 週有值者：**{nf} 筆**。"
          "確認段 2025-11 之後的訊號還沒滿一年、探索段 2018-12～2019-06 集保缺 25 週，這兩類多半不在母體內。",
          "- 週、股價、累積報酬（÷ 進場日還原開盤 − 1，**未扣成本**）、比例（集保 12～15 級 ÷ 1～15 級）、去重（每檔第一次、52 週內不重複）全同 `explore_long/探索.md`。比例缺週的格不算。",
          "- 累積比例變化＝第 k 週比例 − 訊號週（第 0 週）比例，單位 pp。門檻 0.1pp。",
          "- **比例低點週 L**＝第 1～52 週累積變化最低的週；**低點深度**＝該週變化。**先降**＝深度 < −0.1pp。",
          "- **回升週 R**＝L 之後第一個累積變化 > +0.1pp（回到訊號週之上）的週。",
          "- 分組：**先降後升**（先降且有 R）／**先降沒回來**（先降、L 之後沒有任何一週 > +0.1pp）／**沒先降**（低點 ≥ −0.1pp）。先降後升再分：第 52 週仍 > +0.1pp／回升後又跌回（第 52 週 ≤ +0.1pp）。",
          "- 水下週數＝第 1～R−1 週中累積變化 < 0 的有值週數。股價低點週＝第 1～52 週累積報酬最低的週。",
          "- 粗算版（對照，主線先前用 `explore_long/per_event.csv` 粗算的口徑）＝只看第 4/8/12/52 週：先降＝第 4/8/12 週最低 < −0.1pp；"
          "先降後升＝第 52 週 > +0.1pp、先降後持平＝±0.1pp、先降沒回來＝< −0.1pp；「原母體」＝這 4 週比例與第 52 週報酬都有值的筆（不要求逐週完整）。",
          "- ⚠ **分組全用事後資訊**：L、R、低點深度、是否回升都要看完整條 52 週才知道；R 週當下也無法知道那是不是低點之後的回升。",
          "- ⚠ 集保資料日是週五、公布約 +2 日；「第 k 週」的比例與股價是同一資料日事後對齊，實際能看到比例時股價已多走 1～2 個交易日。",
          "- ⚠ 同一檔連續多週的訊號路徑高度重疊、不獨立（去重版另列）；百分比與中位數只當描述，不做檢定、不計 N、不判合格。",
          "- 每格附 N；N < 30 標「樣本少」。", ""]

    # 1
    n_cout = int(((P["粗算組"] != "") & ~full).sum())
    Lm += ["## 一、各組占比與一年後（第 52 週）", "",
           "報酬＝第 52 週累積報酬（相對進場價）；比例 w52＝第 52 週累積比例變化中位。"
           + (f"粗算版原母體 {int((P['粗算組'] != '').sum())} 筆全部落在逐週母體內，所以「限逐週母體」與「原母體」相同，只列一份（csv 兩份都有）。" if n_cout == 0
              else f"粗算版原母體有 {n_cout} 筆不在逐週母體內，另列「限逐週母體」版。"), ""]
    for lab, sg in MDSC:
        d = sel(T1, lab, sg)
        Lm += [f"### {lab}｜{sg}", "",
               "| 版本 | 組 | N | 占比 | 一年報酬中位 | 為正 | ≥+30% | ≤−20% | 比例 w52 中位 (pp) | 註 |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for _, r in d.iterrows():
            if (r["組"] == "├ " + S_NA and r["N"] == 0) or (r["版本"] == CV_SUB and n_cout == 0):
                continue
            Lm.append(f"| {r['版本']} | {r['組']} | {r['N']} | {pc(r['占比'])} | {pc(r['報酬w52_中位'])} | {pc(r['報酬w52_為正'])} | "
                      f"{pc(r['報酬w52_大漲≥+30%'])} | {pc(r['報酬w52_大跌≤−20%'])} | {pp(r['比例w52變化中位_pp'])} | {flag(r['N'])} |")
        Lm.append("")
    Lm += ["對照說明：粗算版的「先降後升」要求第 52 週仍高，最接近逐週版的「先降後升 ├ 第52週仍高於訊號週」；粗算版的「先降沒回來」只看第 52 週，"
           "包含逐週版的「先降沒回來」與部分「回升後又跌回」；粗算只在第 4/8/12 週看有沒有降，第 13 週後才降、或在兩個取樣週之間短暫下降的筆，粗算版歸到「沒先降」。"
           "逐週版的「先降後升」只要 L 之後任一週回到 +0.1pp 之上就算，所以占比比粗算版大很多。", ""]

    # 2
    Lm += ["## 二、先降後升組的時間", "",
           "L＝比例低點週、R＝回升週（回到訊號週 +0.1pp 之上）、水下＝R 之前低於訊號週的週數；升幅單位 pp。", "",
           "| 口徑 | 範圍 | N | L 中位 | R 中位 | R−L 中位 | 水下週數中位 | 低點深度中位 | 回升後到 w52 比例升幅中位 | 低點到 w52 升幅中位 | 註 |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for lab, sg in MDSC:
        r = sel(T2, lab, sg).iloc[0]
        Lm.append(f"| {lab} | {sg} | {r['N']} | {wk(r['L週中位'])} | {wk(r['R週中位'])} | {wk(r['R−L週數中位'])} | {wk(r['水下週數中位'])} | "
                  f"{pp(r['低點深度中位_pp'])} | {pp(r['回升後到w52比例升幅中位_pp'])} | {pp(r['低點到w52比例升幅中位_pp'])} | {r['註']} |")
    for nm, pre, bins in (("L 週分布", "L週_", WBINS), ("R 週分布", "R週_", WBINS), ("低點深度分布", "深度_", DBINS)):
        Lm += ["", f"{nm}（先降後升組內占比）：", "", "| 口徑 | 範圍 | " + " | ".join(b[0] for b in bins) + " |", "|---|---|" + "---:|" * len(bins)]
        for lab, sg in MDSC:
            r = sel(T2, lab, sg).iloc[0]
            Lm.append(f"| {lab} | {sg} | " + " | ".join(pc(r[pre + b[0]]) for b in bins) + " |")
    Lm.append("")

    # 3
    Lm += ["## 三、先降的筆：依低點深度、依低點早晚分層", "",
           "母數＝先降（先降後升＋先降沒回來）。⚠ 低點越晚，剩下能回升的週數越少（第 27–52 週的低點本來就難在 52 週內回升），這是窗長造成的。", ""]
    for kind in ("低點深度", "比例低點週"):
        Lm += [f"### 依{kind}", "", "| 口徑 | 範圍 | 層 | 先降筆數 | 後來回升 | 回升且 w52 仍高 | 一年報酬中位：全層 | 有回升（N） | 沒回來（N） | 註 |",
               "|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
        for lab, sg in MDSC:
            for _, r in sel(T3, lab, sg)[lambda x: x["分層"] == kind].iterrows():
                Lm.append(f"| {lab} | {sg} | {r['層']} | {r['先降筆數']} | {pc(r['後來回升占比'])} | {pc(r['回升且w52仍高占比'])} | {pc(r['一年報酬中位_全層'])} | "
                          f"{pc(r['一年報酬中位_有回升'])}（{r['有回升筆數']}） | {pc(r['一年報酬中位_沒回來'])}（{r['沒回來筆數']}） | {r['註']} |")
        Lm.append("")

    # 4
    Lm += ["## 四、股價與比例誰先轉（事後對齊）", "",
           "### 以比例低點週 L、回升週 R 為 0：前後 8 週的累積報酬中位（相對進場價）／累積比例變化中位（pp）", "",
           "相對週超出第 0～52 週的格不算，所以兩端 N 較小（各格 N 見 `t4_event_align.csv`）。第 0 週（訊號週）在進場前，累積報酬不算。", ""]
    ancs = [f"L（{G_DR}）", f"L（{G_DN}）", f"R（{G_DR}）"]
    for lab, sg in MDSC:
        d = sel(T4, lab, sg)
        Lm += [f"#### {lab}｜{sg}", "", "| 相對週 | " + " | ".join(f"{a}：報酬／比例（N）" for a in ancs) + " |", "|---:|" + "---|" * len(ancs)]
        for off in OFFS:
            cells = []
            for a in ancs:
                r = d[(d["錨"] == a) & (d["相對週"] == off)].iloc[0]
                cells.append(f"{pc(r['報酬中位'])}／{pp(r['比例變化中位_pp'])}（{r['報酬N']}）")
            Lm.append(f"| {off:+d} | " + " | ".join(cells) + " |")
        turn = []
        for a in ancs:
            x = d[d["錨"] == a].dropna(subset=["報酬中位"])
            if len(x):
                x = x.sort_values("相對週"); dj = x["報酬中位"].diff()
                turn.append(f"{a} 報酬中位最低在相對第 {int(x.loc[x['報酬中位'].idxmin(), '相對週']):+d} 週、"
                            f"單週升幅最大在第 {int(x.loc[dj.idxmax(), '相對週']):+d} 週（{pc(dj.max())}）")
        Lm += ["", "轉折：" + "；".join(turn) + "（只在 −8～+8 週內找；中位數逐週由不同筆組成，只當形狀）。", ""]
    Lm += ["### 每筆「股價低點週」對「比例低點週」（第 1～52 週）", "",
           "| 口徑 | 範圍 | 組 | N | 股價先 | 同週 | 比例先 | 差距中位（股價−比例，週） | 差距絕對值中位 | 相差 ≤4 週 | 股價低點週中位 | 比例低點週中位 | 註 |",
           "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for lab, sg in MDSC:
        for _, r in sel(T4B, lab, sg).iterrows():
            Lm.append(f"| {lab} | {sg} | {r['組']} | {r['N']} | {pc(r['股價低點先'])} | {pc(r['同週'])} | {pc(r['比例低點先'])} | {pp(r['差距中位_股價減比例'], 0)} | "
                      f"{wk(r['差距絕對值中位'])} | {pc(r['相差≤4週'])} | {wk(r['股價低點週中位'])} | {wk(r['比例低點週中位'])} | {r['註']} |")
    Lm.append("")

    # 5
    Lm += ["## 五、回升當下（R 週）的股價，與回升後到第 52 週", "",
           "R 週報酬＝R 週還原收盤 ÷ 進場價 − 1；R→w52＝第 52 週還原收盤 ÷ R 週還原收盤 − 1（回升後再持有的區段，只描述；R 週當下無法知道這是低點後的回升）。", "",
           "| 口徑 | 範圍 | 組 | N | R 週報酬中位 | R 週為正 | R 週比例變化中位 (pp) | R→w52 中位 | 為正 | ≥+30% | ≤−20% | 註 |", "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for lab, sg in MDSC:
        for _, r in sel(T5, lab, sg).iterrows():
            Lm.append(f"| {lab} | {sg} | {r['組']} | {r['N']} | {pc(r['R週報酬中位'])} | {pc(r['R週報酬為正'])} | {pp(r['R週比例變化中位_pp'])} | {pc(r['R到w52_中位'])} | "
                      f"{pc(r['R到w52_為正'])} | {pc(r['R到w52_大漲≥+30%'])} | {pc(r['R到w52_大跌≤−20%'])} | {flag(r['N'])} |")
    Lm.append("")

    # 6
    Lm += ["## 六、並排：先降後升 vs 先降沒回來（沒先降附列）", "",
           "| 口徑 | 範圍 | 組 | N | L 週中位 | L 週 1–4／5–8／9–12／13–26／27–52 | 低點深度中位 (pp) | 深度 " + "／".join(b[0] for b in DBINS) +
           " | L 週報酬中位 | L 週為正 | 股價低點週中位 | 一年報酬中位 | 為正 | ≥+30% | ≤−20% | 比例 w52 中位 (pp) | 註 |",
           "|---|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for lab, sg in MDSC:
        for _, r in sel(T6, lab, sg).iterrows():
            Lm.append(f"| {lab} | {sg} | {r['組']} | {r['N']} | {wk(r['L週中位'])} | " + "／".join(pc(r['L週_' + b[0]], 0) for b in WBINS) +
                      f" | {pp(r['低點深度中位_pp'])} | " + "／".join(pc(r['深度_' + b[0]], 0) for b in DBINS) +
                      f" | {pc(r['L週報酬中位'])} | {pc(r['L週報酬為正'])} | {wk(r['股價低點週中位'])} | {pc(r['報酬w52_中位'])} | {pc(r['報酬w52_為正'])} | "
                      f"{pc(r['報酬w52_大漲≥+30%'])} | {pc(r['報酬w52_大跌≤−20%'])} | {pp(r['w52比例變化中位_pp'])} | {r['註']} |")
    Lm += ["", "（沒先降組的「L 週」是比例最低的週，但低點未低於訊號週 −0.1pp。）", ""]

    # 7
    Lm += ["## 七、依進場年份", "",
           "| 口徑 | 進場年 | N | 先降後升 | 其中 w52 仍高 | 先降沒回來 | 沒先降 | 先降後升：一年報酬中位（N） | 全部：一年報酬中位 | 註 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in T7.iterrows():
        Lm.append(f"| {r['口徑']} | {r['進場年']} | {r['N']} | {pc(r['先降後升占比'])} | {pc(r['其中w52仍高占比'])} | {pc(r['先降沒回來占比'])} | {pc(r['沒先降占比'])} | "
                  f"{pc(r['先降後升_一年報酬中位'])}（{r['先降後升筆數']}） | {pc(r['全部_一年報酬中位'])} | {r['註']} |")
    Lm += ["", "⚠ 2018-11～12 進場的筆因 52 週窗跨集保 25 週缺口全數不在母體、2019 年上半進場的也多數不在；2025 年只含進場滿一年的筆；年份間行情不同，占比差異只描述。", ""]

    Lm += ["## 八、自檢", ""] + [f"- {s}" for s in chk] + ["",
           "## 九、檔案", "",
           "- `per_event.csv`：逐筆（組、細分、粗算組、L、深度、R、水下週數、股價低點週、w52 比例與報酬、L／R 週報酬、R→w52）",
           "- `t1_groups.csv`、`t2_dip_rise_timing.csv`、`t3_strata.csv`、`t4_event_align.csv`、`t4_low_order.csv`、`t5_at_recovery.csv`、`t6_side_by_side.csv`、`t7_by_year.csv`、`run.log`"
           "（csv 含去重版探索／確認段）", "",
           "描述，不是買賣建議。", ""]
    with open(os.path.join(OUTD, "探索.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(Lm))


if __name__ == "__main__":
    main()
