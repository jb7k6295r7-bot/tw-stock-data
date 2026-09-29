# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：真頂與中段頂的判斷（描述與參考，⛔ 不計 N；看過 mid_desc／exitsig 結果之後才加）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_topjudge [--check]

⚠ 真頂、中段頂都是事後才知道的；第一部分（段頂分數）用「事後已知這天是段頂」的點，只有第二部分（每個創新高日算分數）是當下真的能用的版本。

═══ 讀法（寫死於 2026-09-29 21:46（台北），在算任何數字之前；協調者三次更正都在開算前收到，以最後一則為準）═══
 ⛔ 不重列真頂的特徵（已在 end_desc／mid_desc）、不新增漲勢位置類特徵、不從全部級距重挑
 T1 特徵集（寫死規則，執行時從既有檔讀出、照實列出）：mid_desc/compare_vs_P_t.csv 中 x＝20%、對照 ＝ P（頂）的各組，
    P − Hk ≥ 10 個百分點（「對照點 − 這個點」）的級距，排除價格位置類概念（r、dhi、dlo、ma、rng、maalign、v3box，同 progress_desc R5）；
    一個概念只留一個：出現在最多組者優先，同數取差距中位較大者（概念對照同 end_desc W6）
 T2 段頂：mid_desc 切法（M2／M2b），x ∈ {10, 20, 30}% 各一套；真頂 P ＝ 1、中段頂 Hk ＝ 0；seq6 事件、事件 ≥ 30 的 182 格；逐格算、取格中位附 p10～p90；
    某格某段要真頂、中段頂各 ≥ 30 點才進該格；段 ＝ 依該點日期月份：探索 2021-01～2023-12、確認 2024-01～2026-08
 T3 單一特徵：段頂中「有此級距時是真頂」的比例 ÷ 基準（該特徵有值的段頂中真頂比例）；月分群 CR0 95% 下緣；探索、確認各報
 T4 分數 ＝ T1 特徵同時有幾個（該點當天收盤含以前可得；沒有值 ＝ 沒有）
    探索段只用來定讀法：m* ＝ 探索段「抓到真頂的比例 − 誤抓中段頂的比例」格中位最大的 m（同值取較小 m）
    確認段校準：分數 ≥ m 時是真頂的比例、抓到真頂的幾成（漏掉 ＝ 1 − 這個）、占段頂比例；分數 ＝ j 的逐格表另存
 T5 當下可用版：每個事件 (t, P] 內每個「收盤 ＞ [t, 前一日] 最高收盤」的日子 d（段頂都在其中）算同一分數；
    結果：之後 20／60 日「不再創新高」＝ (d, d＋h] 最高收盤 ≤ c[d]；之後 60 日內回落 20／30% ＝ (d, d＋60] 最低收盤 ≤ c[d] ×（1 − x）；
    d＋h ≤ 2026-08-31 才算（資料用到 2026-08-31，含 P 之後）；m* ＝ 探索段對「60 日不再創新高」同 T4 規則；確認段報各 m 的四個比例與占創新高日比例；基準 ＝ 全部創新高日
 T6 查核（--check）：抽 2 格，逐日狀態機重算 x＝20% 真頂數、中段頂數、創新高日數、60 日不再創新高比例、第一個特徵在真頂／中段頂的涵蓋率 ⇒ 對長表
輸出 backtest/resultsSurge6/topjudge/
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
TIME = "2026-09-29 21:46（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/topjudge"
XS = (0.10, 0.20, 0.30)
HS = list(S5.HS); GS = list(S5.GS)
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_
Z = 1.959963984540054
EXP = (2021 * 12, 2023 * 12 + 11); CON = (2024 * 12, 2026 * 12 + 7)
PRICEPOS = {"r", "dhi", "dlo", "ma", "rng", "maalign", "v3box"}


def feature_set():
    C = pd.read_csv("backtest/resultsSurge6/mid_desc/compare_vs_P_t.csv"); S = pd.read_csv("backtest/resultsSurge6/mid_desc/selected.csv")[["組", "特徵", "欄", "碼", "概念"]]
    C = C[C["組"].str.startswith("20%") & (C["對照"] == "P（頂）")].merge(S, on=["組", "特徵"], how="left")
    C["差"] = C["對照點"] - C["這個點"]; C = C[(C["差"] >= 0.10) & ~C["概念"].isin(PRICEPOS)]
    g = C.groupby(["概念", "特徵", "欄", "碼"]).agg(組數=("差", "size"), 差中位=("差", "median")).reset_index()
    g = g.sort_values(["組數", "差中位"], ascending=False).drop_duplicates("概念", keep="first").reset_index(drop=True)
    return g


def cuts_full(cs):
    rm = np.maximum.accumulate(cs)
    nh = np.flatnonzero(cs[1:] > rm[:-1]) + 1
    pk = np.r_[0, nh]; out = []
    for j in np.flatnonzero(np.diff(pk) >= 2):
        a, b = int(pk[j]), int(pk[j + 1]); seg = cs[a + 1:b]; k = int(np.argmin(seg))
        out.append((a, float(seg[k]), float(cs[a])))
    return nh, out


def build_rows(uni, cal, n, E, t1, log):
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    R = {k: [] for k in ("s", "d", "cell", "no20", "no60", "dd20", "dd30", "lab_0", "lab_1", "lab_2")}
    D.DATA = S5.ST
    for s in np.unique(es):
        c = pd.Series(D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].to_numpy(float)).ffill().to_numpy()
        rv = pd.Series(c[::-1]); FUT = {}
        for h in (20, 60):
            mx = np.r_[rv.rolling(h, min_periods=h).max().to_numpy()[::-1][1:], np.nan]; mn = np.r_[rv.rolling(h, min_periods=h).min().to_numpy()[::-1][1:], np.nan]
            lim = np.arange(n) + h > t1; mx[lim] = np.nan; mn[lim] = np.nan; FUT[h] = (mx, mn)
        memo = {}
        for i in np.flatnonzero(es == s):
            t, P = ed[i], Pv[i]
            if (t, P) not in memo:
                cs = c[t:P + 1]; nh, cu = cuts_full(cs); d = t + nh
                b = {"s": np.full(len(nh), s), "d": d}
                f20, _ = FUT[20]; f60, m60 = FUT[60]
                b["no20"] = np.where(np.isfinite(f20[d]), f20[d] <= c[d], np.nan); b["no60"] = np.where(np.isfinite(f60[d]), f60[d] <= c[d], np.nan)
                b["dd20"] = np.where(np.isfinite(m60[d]), m60[d] <= c[d] * 0.8, np.nan); b["dd30"] = np.where(np.isfinite(m60[d]), m60[d] <= c[d] * 0.7, np.nan)
                for xi, x in enumerate(XS):
                    A = [a for a, lo, hi in cu if a > 0 and lo <= hi * (1 - x) * (1 + 1e-9)]
                    lab = np.full(len(nh), -1, np.int8); lab[np.isin(nh, A)] = 0; lab[nh == len(cs) - 1] = 1
                    b[f"lab_{xi}"] = lab
                memo[(t, P)] = b
            b = memo[(t, P)]
            R["cell"].append(np.full(len(b["d"]), ec[i]))
            for k in b:
                R[k].append(b[k])
    R = {k: np.concatenate(v) for k, v in R.items()}
    log(f"[列] 創新高日 {len(R['d']):,}")
    return R


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    FS = feature_set(); FS.to_csv(os.path.join(OUT, "features_used.csv"), index=False, float_format="%.5g"); K = len(FS)
    log(f"[特徵] {K} 個：{'、'.join(FS['特徵'])}")
    R = build_rows(uni, cal, n, E, t1, log)
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); rm = mon[R["d"]]
    seg = np.where((rm >= EXP[0]) & (rm <= EXP[1]), 0, np.where((rm >= CON[0]) & (rm <= CON[1]), 1, -1))
    mi = (rm - EXP[0]).astype(np.int64); NM = int(CON[1] - EXP[0] + 1)
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    PR = np.zeros((len(R["d"]), K), bool); DF = np.zeros_like(PR)
    for j, r in enumerate(FS.to_dict("records")):
        q = np.asarray(Qm[S5.FIX[r["欄"]]])[R["s"], R["d"]]; PR[:, j] = q == r["碼"]; DF[:, j] = q > 0
    score = PR.sum(1)
    cl = np.array(cells)
    order = np.argsort(R["cell"], kind="stable"); cb = np.searchsorted(R["cell"][order], np.arange(251))
    ROWS = {c: order[cb[c]:cb[c + 1]] for c in cells}
    # ── 單一特徵
    ST = []
    for xi, x in enumerate(XS):
        lab = R[f"lab_{xi}"]
        for j, r in enumerate(FS.to_dict("records")):
            row = {"x": f"{int(x * 100)}%", "特徵": r["特徵"]}
            for sk, sn in ((0, "探索"), (1, "確認")):
                m = (lab >= 0) & (seg == sk) & DF[:, j]
                key = ((R["cell"][m] * 2 + lab[m]) * NM + mi[m]) * 2 + PR[m, j]
                cc = np.bincount(key, minlength=250 * 2 * NM * 2).reshape(250, 2, NM, 2)[cl]
                n1, n0 = cc[:, 1].sum((1, 2)), cc[:, 0].sum((1, 2)); ok = (n1 >= 30) & (n0 >= 30)
                e = cc[:, 1, :, 1].astype(float); nn = (cc[:, 0, :, 1] + cc[:, 1, :, 1]).astype(float); N = nn.sum(1)
                p = e.sum(1) / N; base = n1 / (n1 + n0); se = np.sqrt(((e - p[:, None] * nn) ** 2).sum(1)) / N
                row[f"{sn} 可用格"] = int(ok.sum())
                for nm_, arr in (("真頂涵蓋", cc[:, 1, :, 1].sum(1) / n1), ("中段頂涵蓋", cc[:, 0, :, 1].sum(1) / n0), ("倍數", p / base), ("倍數下緣", (p - Z * se) / base), ("基準真頂比例", base)):
                    row[f"{sn} {nm_}"] = q3(arr[ok])[0] if ok.any() else np.nan
            ST.append(row)
    ST = pd.DataFrame(ST); ST.to_csv(os.path.join(OUT, "single.csv"), index=False, float_format="%.5g")

    def curves(mask, y, uc):
        """每格：分數 ≥ m 的 正比例、抓到正的幾成、抓到負的幾成、占比 ⇒ dict m → 各格陣列。"""
        out = {m: [] for m in range(K + 1)}
        for c in uc:
            rr = ROWS[c]; w = rr[mask[rr]]; sc = score[w]; yy = y[w]
            n1, n0 = (yy == 1).sum(), (yy == 0).sum()
            for m in range(K + 1):
                g = sc >= m
                out[m].append((yy[g].mean() if g.any() else np.nan, (g & (yy == 1)).sum() / n1, (g & (yy == 0)).sum() / n0, g.mean()))
        return {m: np.array(v) for m, v in out.items()}
    CAL = []; RT = []; MSTAR = {}
    for xi, x in enumerate(XS):
        lab = R[f"lab_{xi}"].astype(float); lab[lab < 0] = np.nan
        for sk in (0, 1):
            m_ = np.isfinite(lab) & (seg == sk)
            uc = [c for c in cells if (m_[ROWS[c]] & (lab[ROWS[c]] == 1)).sum() >= 30 and (m_[ROWS[c]] & (lab[ROWS[c]] == 0)).sum() >= 30]
            cv = curves(m_, lab, uc)
            if sk == 0:
                J = {m: np.nanmedian(cv[m][:, 1] - cv[m][:, 2]) if len(uc) else np.nan for m in cv}
                MSTAR[("段頂", xi)] = int(max(J, key=lambda m: (J[m], -m))) if len(uc) else 0
            for m, a in cv.items():
                CAL.append({"x": f"{int(x * 100)}%", "段": "探索" if sk == 0 else "確認", "分數≥": m, "可用格": len(uc), "是真頂的比例": q3(a[:, 0])[0] if len(uc) else np.nan,
                            "p10": q3(a[:, 0])[1] if len(uc) else np.nan, "p90": q3(a[:, 0])[2] if len(uc) else np.nan,
                            "抓到真頂的幾成": q3(a[:, 1])[0] if len(uc) else np.nan, "誤抓中段頂的幾成": q3(a[:, 2])[0] if len(uc) else np.nan,
                            "占段頂比例": q3(a[:, 3])[0] if len(uc) else np.nan, "m*": m == MSTAR[("段頂", xi)]})
        log(f"[段頂分數] x＝{int(x * 100)}% m*＝{MSTAR[('段頂', 0 if False else xi)]}")
    CAL = pd.DataFrame(CAL); CAL.to_csv(os.path.join(OUT, "score_calib_tops.csv"), index=False, float_format="%.5g")
    # ── 當下可用版（創新高日；不分 x）
    y = R["no60"]
    for sk in (0, 1):
        m_ = np.isfinite(y) & (seg == sk)
        uc = [c for c in cells if (m_[ROWS[c]] & (y[ROWS[c]] == 1)).sum() >= 30 and (m_[ROWS[c]] & (y[ROWS[c]] == 0)).sum() >= 30]
        cv = curves(m_, y, uc)
        if sk == 0:
            J = {m: np.nanmedian(cv[m][:, 1] - cv[m][:, 2]) for m in cv}; MSTAR["創新高日"] = int(max(J, key=lambda m: (J[m], -m)))
        for m in range(K + 1):
            row = {"段": "探索" if sk == 0 else "確認", "分數≥": m, "可用格": len(uc), "m*": m == MSTAR["創新高日"]}
            for yk, nm_ in (("no60", "60日不再創新高"), ("no20", "20日不再創新高"), ("dd20", "60日內回落20%"), ("dd30", "60日內回落30%")):
                yv = R[yk]; vals = []; covs = []
                for c in uc:
                    rr = ROWS[c]; w = rr[(seg[rr] == sk) & np.isfinite(yv[rr])]; g = score[w] >= m
                    vals.append(yv[w][g].mean() if g.any() else np.nan); covs.append(g.mean())
                row[nm_] = q3(vals)[0]
                if yk == "no60":
                    row["占創新高日"] = q3(covs)[0]
            row["抓到『60日不再創新高』的幾成"] = q3(cv[m][:, 1])[0]
            RT.append(row)
    RT = pd.DataFrame(RT); RT.to_csv(os.path.join(OUT, "realtime.csv"), index=False, float_format="%.5g")
    # 查核長表
    CL = []
    for c in cells:
        w = np.zeros(len(R["d"]), bool); w[ROWS[c]] = True; l1 = R["lab_1"]
        for lab_, nm_ in ((1, "x20 真頂"), (0, "x20 中段頂")):
            mm = w & (l1 == lab_); CL.append({"格": S5.cell_name(c), "項": f"{nm_}數", "值": float(mm.sum())})
            CL.append({"格": S5.cell_name(c), "項": f"{nm_}涵蓋｜{FS['特徵'][0]}", "值": PR[mm & DF[:, 0], 0].mean() if (mm & DF[:, 0]).any() else np.nan})
        CL.append({"格": S5.cell_name(c), "項": "創新高日數", "值": float(w.sum())}); CL.append({"格": S5.cell_name(c), "項": "60日不再創新高", "值": float(np.nanmean(R["no60"][w]))})
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "特徵數": K, "特徵": FS["特徵"].tolist(), "創新高日列": int(len(R["d"])),
            "m*": {f"段頂 x{int(XS[k[1]] * 100)}" if isinstance(k, tuple) else k: v for k, v in MSTAR.items()},
            "警語": "真頂、中段頂都是事後才知道；只有創新高日版當下能用", "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, FS, ST, CAL, RT)
    log(f"[完] {time.time() - T0:.0f}s")


def page(META, FS, ST, CAL, RT):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}.ok{border-left:4px solid #2b6cb0;padding:6px 10px;background:#eef4fb}tr.m td{background:#fdecea;font-weight:bold}"
    K = META["特徵數"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>真頂與中段頂判斷</title>", f"<style>{CSS}</style></head><body><main>", "<h1>真頂還是中段頂？用「同時有幾個特徵」來分（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 真頂（整段最高點）、中段頂（漲勢中途、拉回後又再創新高前的高點）都是事後才知道的。第一部分用「事後已知這天是段頂」的點；"
         "<b>只有第二部分「每個創新高日算分數」當下真的能用</b>。本件是看過前幾份結果之後才加的，只當描述與參考，沒有計入檢定數。</p>",
         "<p class='note'>真頂、中段頂各自有哪些特徵，已在「飆股結束整理」與「飆股中段高低點整理」兩頁，這裡不重列。</p>",
         f"<p class='lead'>用的 {K} 個特徵 ＝ 中段高低點整理裡「真頂比中段頂多 10 個百分點以上」的非價格位置類，一個概念一個：{html.escape('、'.join(FS['特徵']))}。"
         f"分數 ＝ 那天同時有幾個。探索 2021–2023 只用來定「幾分以上」，確認 2024–2026-08 驗。讀法寫死 {html.escape(META['讀法寫死'])}。</p>"]
    H.append("<h2>先講結論</h2><ul>")
    for xv in ("20%",):
        c = CAL[(CAL["x"] == xv) & (CAL["段"] == "確認")]
        if len(c):
            b0 = c[c["分數≥"] == 0].iloc[0]; ms = c[c["m*"]].iloc[0] if c["m*"].any() else b0
            H.append(f"<li><b>段頂分數（拉回 20%）</b>：確認段全部段頂裡真頂占 {P_(b0['是真頂的比例'])}。探索段定的讀法是「≥ {int(ms['分數≥'])} 分」："
                     f"確認段 ≥ {int(ms['分數≥'])} 分的段頂有 {P_(ms['是真頂的比例'])} 是真頂，抓到 {P_(ms['抓到真頂的幾成'])} 的真頂（漏掉 {P_(1 - ms['抓到真頂的幾成'])}），"
                     f"也誤抓 {P_(ms['誤抓中段頂的幾成'])} 的中段頂。</li>")
    r = RT[RT["段"] == "確認"]
    if len(r):
        b0 = r[r["分數≥"] == 0].iloc[0]; ms = r[r["m*"]].iloc[0] if r["m*"].any() else b0
        H.append(f"<li class='ok'><b>當下可用版（每個創新高日）</b>：確認段全部創新高日之後 60 日不再創新高 {P_(b0['60日不再創新高'])}；"
                 f"分數 ≥ {int(ms['分數≥'])}（探索段定的讀法）時 {P_(ms['60日不再創新高'])}，占創新高日 {P_(ms['占創新高日'])}；60 日內回落 20% {P_(ms['60日內回落20%'])}（全部 {P_(b0['60日內回落20%'])}）。</li>")
    H.append("</ul>")
    H.append("<h2>一、段頂分數：分數越高越像真頂嗎？（確認段）</h2>")
    for xv in ("10%", "20%", "30%"):
        c = CAL[(CAL["x"] == xv) & (CAL["段"] == "確認")]
        if not len(c) or c["可用格"].max() == 0:
            continue
        H.append(f"<h3>拉回 {xv}（可用 {int(c['可用格'].max())} 格；紅列 ＝ 探索段定的讀法）</h3><div class='wrap'><table><tr><th>分數 ≥</th><th>是真頂</th><th>抓到真頂</th><th>誤抓中段頂</th><th>占段頂</th></tr>")
        for rr in c.to_dict("records"):
            H.append(f"<tr class='{'m' if rr['m*'] else ''}'><td>{int(rr['分數≥'])}</td><td>{P_(rr['是真頂的比例'])}</td><td>{P_(rr['抓到真頂的幾成'])}</td><td>{P_(rr['誤抓中段頂的幾成'])}</td><td>{P_(rr['占段頂比例'])}</td></tr>")
        H.append("</table></div>")
    H.append("<h2>二、當下可用版：每個創新高日算分數（確認段）</h2><p class='note'>⭐ 只有這一版當下真的能用：每天收盤創起漲以來新高時算分數，看之後會不會就是頂了。</p>"
             "<div class='wrap'><table><tr><th>分數 ≥</th><th>60日不再創高</th><th>20日不再創高</th><th>60日內跌20%</th><th>跌30%</th><th>占創新高日</th></tr>")
    for rr in RT[RT["段"] == "確認"].to_dict("records"):
        H.append(f"<tr class='{'m' if rr['m*'] else ''}'><td>{int(rr['分數≥'])}</td><td>{P_(rr['60日不再創新高'])}</td><td>{P_(rr['20日不再創新高'])}</td><td>{P_(rr['60日內回落20%'])}</td><td>{P_(rr['60日內回落30%'])}</td><td>{P_(rr['占創新高日'])}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>三、單一特徵：有它時是真頂的機率是平常的幾倍（拉回 20%）</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>探索 倍數（下緣）</th><th>確認 倍數（下緣）</th><th>確認 真頂／中段頂有它</th></tr>")
    for rr in ST[ST["x"] == "20%"].sort_values("探索 倍數", ascending=False).to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(rr['特徵'])}</td><td>{X_(rr['探索 倍數'])}（{X_(rr['探索 倍數下緣'])}）</td><td>{X_(rr['確認 倍數'])}（{X_(rr['確認 倍數下緣'])}）</td><td>{P_(rr['確認 真頂涵蓋'])}／{P_(rr['確認 中段頂涵蓋'])}</td></tr>")
    H.append("</table></div></main></body></html>")
    open(os.path.join(OUT, "真頂與中段頂判斷.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); FS = pd.read_csv(os.path.join(OUT, "features_used.csv")); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    q = np.asarray(Qm[S5.FIX[FS["欄"][0]]]); code = int(FS["碼"][0]); fname = FS["特徵"][0]
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False); errs = []; info = {}; D.DATA = S5.ST; CF = {}
    for c in pick:
        nm = S5.cell_name(c); k = np.flatnonzero(E["cell"] == c); tops = {0: [], 1: []}; nnh = 0; no60 = []
        for i in k:
            s, t, P = int(E["s"][i]), int(E["d"][i]), int(E["P"][i])
            if s not in CF:
                CF[s] = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].ffill().to_numpy(float)
            cf = CF[s]; pk, pkd, tv = cf[t], t, np.inf
            for d in range(t + 1, P + 1):
                v = cf[d]
                if v > pk:
                    if pkd > t and tv <= pk * 0.8 * (1 + 1e-9):
                        tops[0].append((s, pkd))
                    pk, pkd, tv = v, d, np.inf; nnh += 1
                    if d + 60 <= t1:
                        no60.append(cf[d + 1:d + 61].max() <= v)
                elif v < tv:
                    tv = v
            tops[1].append((s, P))
        got = {"x20 真頂數": len(tops[1]), "x20 中段頂數": len(tops[0]), "創新高日數": nnh, "60日不再創新高": float(np.mean(no60))}
        for lab, nmk in ((1, "x20 真頂"), (0, "x20 中段頂")):
            v = np.array([q[s, d] for s, d in tops[lab]]); got[f"{nmk}涵蓋｜{fname}"] = (v == code).sum() / max((v > 0).sum(), 1)
        for kk, mine in got.items():
            ref = CL[(CL["格"] == nm) & (CL["項"] == kk)]["值"].iloc[0]
            if not np.isclose(mine, ref, rtol=1e-6):
                errs.append(f"{nm} {kk}：{mine} 檔 {ref}")
        info[nm] = got
    out = {"抽格": list(info), "比對": info, "錯誤數": len(errs), "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 錯誤 {len(errs)}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
