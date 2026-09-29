# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：從起漲到頂，約 6 成、8 成、真的頂點時分別出現的特徵（⛔ 只描述：不判定、不計 N、不挑格）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_progress_desc [--check]

⚠ 頂點 P 是事後才知道的；6 成點、8 成點也是事後依頂回推，當下不知道自己在第幾成。

═══ 讀法（寫死於 2026-09-29 21:07（台北），在算任何數字之前）═══
 R1 對象、格、彙總、一般股-日、特徵可得日：同 end_desc（W1～W4、W10）：seq6 events、事件 ≥ 30 的全部格（182）、逐格算取格中位附 p10～p90；
    一般 ＝ 兩段內有 K 棒且 hdef6 ≥ H 的股-日；特徵看該點當天收盤（含）以前可得（s5work Q／F）
 R2 進度點（每個事件；還原收盤 ffill）：低 ＝ c[t]、頂 ＝ c[P]；進度 ＝ (c − 低) ÷ (頂 − 低)；
    D60 ＝ (t, P] 內第一個 c ≥ (低 ＋ 0.6 ×（頂 − 低））×（1 − 1e−9）的日子；D80 同理用 0.8；頂 ＝ P；另附 t 當基準
 R3 ① 四點（t、D60、D80、P）涵蓋率並列、對一般股-日附倍數（級距 ＝ seq5 levels()）；
    納入 ＝ 任一點「涵蓋率 ≥ 10% 且 倍數 ＞ 1」的級距，每個概念（概念對照同 end_desc W6）只留一個：取該概念在任一點涵蓋率最高的那個級距；⛔ 不限數量（K）
    「原：」使用者原門檻版另表全列
 R4 ② 新出現：在納入的 K 個裡，(a) D60 就已 ≥ 50%；(b) D80 − D60 ≥ +15 個百分點；(c) P − D80 ≥ +15 個百分點；各依增幅（(a) 依 D60 涵蓋率）排序
 R5 ③ 價格位置類（構造使然：P 必然偏高）＝ 概念 r（N 日報酬）、dhi／dlo（距 N 日高／低）、ma（收盤÷MA 乖離，含原「站上 MA100」）、rng（N 日區間寬度）、
    maalign（均線排列段數，含原「多頭排列」）、v3box（收盤÷修正箱上箱價）；其餘（籌碼、注意處置、漲停次數、周轉、量、融資、借券、營收、財報、K 值、RSI、布林、大盤、產業、規模…）＝ 非價格位置類
    網頁先放非價格位置類，價格位置類另一區
 R6 ④ 各點同時有幾個（K 個；0～K 逐個＋至少幾個累計；沒有值 ＝ 沒有）
 R7 ⑤ 天數（日曆交易日索引差）：t→D60、D60→D80、D80→P，各格事件中位再取格中位
 R8 ⑥ 各點隔天：同 end_desc W9（收跌停、收跌 ≥ 5%、收黑、漲跌中位；另附盤中碰跌停、跳空跌 ≥ 3%）
 R9 查核（--check）：抽 2 格，逐列迴圈重找 D60／D80、重算一個級距在 D60 的涵蓋率與 t→D60 天數格中位 ⇒ 對 cells 長表
輸出 backtest/resultsSurge6/progress_desc/
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
from backtest import researchSurge5_feat as FT
from backtest import researchSurge6_end_desc as ED

D = S5.D
TIME = "2026-09-29 21:07（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/progress_desc"
PTS = ["t（起漲）", "D60（6 成）", "D80（8 成）", "P（頂）"]
PRICEPOS = {"r", "dhi", "dlo", "ma", "rng", "maalign", "v3box"}
HS = list(S5.HS); GS = list(S5.GS)
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_


def progress_days(uni, cal, E):
    es, ed, Pv = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int)
    d60 = np.zeros(len(es), np.int64); d80 = np.zeros(len(es), np.int64)
    D.DATA = S5.ST
    for s in np.unique(es):
        ii = np.flatnonzero(es == s)
        cff = pd.Series(D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].to_numpy(float)).ffill().to_numpy()
        for i in ii:
            t, P = ed[i], Pv[i]; lo, hi = cff[t], cff[P]; w = cff[t + 1:P + 1]
            d60[i] = t + 1 + int(np.argmax(w >= (lo + 0.6 * (hi - lo)) * (1 - 1e-9)))
            d80[i] = t + 1 + int(np.argmax(w >= (lo + 0.8 * (hi - lo)) * (1 - 1e-9)))
    return d60, d80


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    HC = np.array([HS[c // len(GS)] for c in range(250)]); Hset = sorted({HC[c] for c in cells})
    d60, d80 = progress_days(uni, cal, E)
    DAYS = [ed, d60, d80, Pv]
    assert ((d60 > ed) & (d60 <= d80) & (d80 <= Pv)).all()
    log(f"[進度點] 完成 {time.time() - T0:.0f}s")
    # ⑤ 天數
    TM = []
    for nm, a, b in (("t→D60", ed, d60), ("D60→D80", d60, d80), ("D80→P", d80, Pv), ("t→P", ed, Pv)):
        y = q3([np.median((b - a)[ec == c]) for c in cells]); TM.append({"區間": nm, "天數 格中位": y[0], "p10": y[1], "p90": y[2]})
    TM = pd.DataFrame(TM); TM.to_csv(os.path.join(OUT, "days.csv"), index=False, float_format="%.5g")
    # ① 涵蓋率
    LV = FT.levels(); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")
    rs, rt = np.nonzero(bar & inseg[None, :]); rh = np.minimum(h6[rs, rt].astype(np.int64), 250)
    covS = {}; covG = {}
    for fi in sorted({x[0] for x in LV}):
        q = np.asarray(Qm[fi])
        ms = [np.bincount(ec * 7 + q[es, dd].astype(np.int64), minlength=250 * 7).reshape(250, 7) for dd in DAYS]
        gg = np.bincount(q[rs, rt].astype(np.int64) * 251 + rh, minlength=7 * 251).reshape(7, 251); ge = np.cumsum(gg[:, ::-1], axis=1)[:, ::-1]
        with np.errstate(invalid="ignore", divide="ignore"):
            for lv in [x for x in LV if x[0] == fi]:
                covS[(fi, lv[2])] = np.stack([m[:, lv[2]] / m[:, 1:].sum(1) for m in ms])          # (4, 250)
                covG[(fi, lv[2])] = {H: ge[lv[2], H] / ge[1:, H].sum() for H in Hset}
    log(f"[①] 涵蓋率完成 {time.time() - T0:.0f}s")
    C1 = []
    for lv in LV:
        fi, col, code = lv[0], lv[1], lv[2]; g = q3([covG[(fi, code)][HC[c]] for c in cells])[0]; cp = ED.concept(col)
        r = {"特徵": f"{lv[4]}｜{lv[3]}", "欄": col, "碼": code, "概念": cp, "原門檻": col.startswith("d_"), "價格位置類": cp in PRICEPOS,
             "類別": ED.CAT.get(col, ""), "可得時點": ED.AVAIL.get(ED.CAT.get(col, ""), ""), "一般": g}
        for i, pt in enumerate(PTS):
            s = q3(covS[(fi, code)][i, cells])
            r[pt] = s[0]; r[f"{pt} p10"] = s[1]; r[f"{pt} p90"] = s[2]; r[f"{pt} 倍數"] = s[0] / g if g > 0 else np.nan
        C1.append(r)
    C1 = pd.DataFrame(C1); C1.to_csv(os.path.join(OUT, "coverage_all.csv"), index=False, float_format="%.5g")
    C1[C1["原門檻"]].to_csv(os.path.join(OUT, "coverage_original.csv"), index=False, float_format="%.5g")
    ok = np.zeros(len(C1), bool); best = np.full(len(C1), -1.0)
    for pt in PTS:
        m_ = (C1[pt] >= 0.10) & (C1[f"{pt} 倍數"] > 1); ok |= m_.to_numpy(); best = np.maximum(best, np.where(m_, C1[pt], -1.0))
    cand = C1[ok].assign(_best=best[ok]).sort_values("_best", ascending=False)
    SEL = cand.drop_duplicates("概念", keep="first").drop(columns="_best").reset_index(drop=True); K = len(SEL)
    SEL.to_csv(os.path.join(OUT, "selected.csv"), index=False, float_format="%.5g")
    log(f"[①] 納入 {K} 個（候選 {len(cand)}）")
    # ② 新出現
    NEW = []
    for r in SEL.to_dict("records"):
        if r[PTS[1]] >= 0.5:
            NEW.append({"清單": "(a) D60 就已出現（≥50%）", "特徵": r["特徵"], "價格位置類": r["價格位置類"], "t": r[PTS[0]], "D60": r[PTS[1]], "D80": r[PTS[2]], "P": r[PTS[3]], "一般": r["一般"], "排序值": r[PTS[1]]})
        if r[PTS[2]] - r[PTS[1]] >= 0.15:
            NEW.append({"清單": "(b) D60→D80 增加 ≥15 點", "特徵": r["特徵"], "價格位置類": r["價格位置類"], "t": r[PTS[0]], "D60": r[PTS[1]], "D80": r[PTS[2]], "P": r[PTS[3]], "一般": r["一般"], "排序值": r[PTS[2]] - r[PTS[1]]})
        if r[PTS[3]] - r[PTS[2]] >= 0.15:
            NEW.append({"清單": "(c) D80→P 增加 ≥15 點", "特徵": r["特徵"], "價格位置類": r["價格位置類"], "t": r[PTS[0]], "D60": r[PTS[1]], "D80": r[PTS[2]], "P": r[PTS[3]], "一般": r["一般"], "排序值": r[PTS[3]] - r[PTS[2]]})
    NEW = pd.DataFrame(NEW).sort_values(["清單", "排序值"], ascending=[True, False]); NEW.to_csv(os.path.join(OUT, "new_appear.csv"), index=False, float_format="%.5g")
    # ④ 同時有幾個
    FXc = {c: i for i, c in enumerate(S5.FCOL)}
    QC = {c: np.asarray(Qm[FXc[c]]) for c in set(SEL["欄"])}
    codes = SEL["碼"].to_numpy(np.int8)
    DI = []; CL = []
    rows_by_H = {H: rh >= H for H in Hset}
    gcnt = np.zeros(len(rs), np.int64)
    for c_, k_ in zip(SEL["欄"], codes):
        gcnt += QC[c_][rs, rt] == k_
    GD = {H: np.bincount(gcnt[m], minlength=K + 1) / m.sum() for H, m in rows_by_H.items()}
    for i, pt in enumerate(PTS):
        cntp = np.zeros(len(es), np.int64)
        for c_, k_ in zip(SEL["欄"], codes):
            cntp += QC[c_][es, DAYS[i]] == k_
        per = {c: np.bincount(cntp[ec == c], minlength=K + 1) / (ec == c).sum() for c in cells}
        for j in range(K + 1):
            x = q3([per[c][j] for c in cells]); xa = q3([per[c][j:].sum() for c in cells]); y = q3([GD[HC[c]][j] for c in cells]); ya = q3([GD[HC[c]][j:].sum() for c in cells])
            DI.append({"點": pt, "同時有幾個": j, "中位": x[0], "p10": x[1], "p90": x[2], "至少 中位": xa[0], "至少 p10": xa[1], "至少 p90": xa[2], "一般 中位": y[0], "至少 一般 中位": ya[0]})
    DI = pd.DataFrame(DI); DI.to_csv(os.path.join(OUT, "count_dist.csv"), index=False, float_format="%.5g")
    # ⑥ 隔天
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    NDs = [np.full((len(es), 7), np.nan) for _ in PTS]
    for s in np.unique(es):
        ii = np.flatnonzero(es == s)
        cA, oA, rr, evd = ED._stock_arrays(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal, n)
        bars = np.flatnonzero(bar[s]); memo = {}
        for i in ii:
            for k, dd in enumerate(DAYS):
                p = int(dd[i])
                if p not in memo:
                    memo[p] = ED._nd(p, bars, cA, oA, rr, evd, cal, t1)
                NDs[k][i] = memo[p]
    GND = ED.general_nextday(uni, cal, n, bar, inseg, h6, Hset, log)
    NX = ["收跌停", "盤中碰跌停", "開盤跳空跌≥3%", "收跌≥5%", "收黑"]; NDR = []
    for k, pt in enumerate(PTS):
        per = {nm: [] for nm in NX + ["漲跌中位"]}
        for c in cells:
            w = NDs[k][ec == c]; okr = np.isfinite(w[:, 5]); okl = okr & np.isfinite(w[:, 0])
            for i, nm in enumerate(NX):
                mm = okl if i < 2 else okr
                per[nm].append(np.nanmean(w[mm, i]) if mm.any() else np.nan)
            per["漲跌中位"].append(np.nanmedian(w[okr, 5]) if okr.any() else np.nan)
            if k == 1:
                CL.append({"格": S5.cell_name(c), "項": "D60 收跌停", "值": per["收跌停"][-1]})
        for nm, vals in per.items():
            x = q3(vals); y = q3([GND[HC[c]][nm] for c in cells])
            NDR.append({"點": pt, "項目": nm, "中位": x[0], "p10": x[1], "p90": x[2], "一般 中位": y[0]})
    NDR = pd.DataFrame(NDR); NDR.to_csv(os.path.join(OUT, "nextday.csv"), index=False, float_format="%.5g")
    # 查核長表
    r0 = SEL[~SEL["價格位置類"]].iloc[0] if (~SEL["價格位置類"]).any() else SEL.iloc[0]
    for c in cells:
        CL.append({"格": S5.cell_name(c), "項": f"D60 涵蓋率｜{r0['特徵']}", "值": covS[(S5.FIX[r0["欄"]], int(r0["碼"]))][1, c]})
        CL.append({"格": S5.cell_name(c), "項": "t→D60 天數中位", "值": float(np.median((d60 - ed)[ec == c]))})
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "納入特徵數 K": K, "候選級距數": int(len(cand)), "其中價格位置類": int(SEL["價格位置類"].sum()),
            "警語": "頂點是事後才知道的；6 成、8 成也是事後依頂回推，當下不知道自己在第幾成", "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, TM, SEL, C1[C1["原門檻"]], NEW, DI, NDR)
    log(f"[完] {time.time() - T0:.0f}s")


def page(META, TM, SEL, ORIG, NEW, DI, NDR):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}.up{background:#fdecea}"
    tm = TM.set_index("區間"); nd = NDR.set_index(["點", "項目"])
    np_ = SEL[~SEL["價格位置類"]]; pp_ = SEL[SEL["價格位置類"]]
    na = NEW[(NEW["清單"].str.startswith("(a)")) & ~NEW["價格位置類"]]; nb = NEW[(NEW["清單"].str.startswith("(b)")) & ~NEW["價格位置類"]]; nc = NEW[(NEW["清單"].str.startswith("(c)")) & ~NEW["價格位置類"]]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>飆股六八成與頂點</title>", f"<style>{CSS}</style></head><body><main>", "<h1>飆股漲到 6 成、8 成、頂點時，各出現什麼特徵？（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 頂點是事後才知道的；6 成、8 成也是事後依頂點回推的，當下不知道自己在第幾成。只描述、沒有檢定。</p>",
         f"<p class='lead'>6 成點 ＝ 從起漲收盤到頂點收盤，第一天收盤漲到 60% 的位置；8 成點同理。{META['合格格數']} 種飆股定義各算一次取中位數；讀法寫死 {html.escape(META['讀法寫死'])}。</p>",
         "<h2>先講結論</h2><ul>",
         f"<li>時間：起漲到 6 成中位 {tm.loc['t→D60', '天數 格中位']:.0f} 天、6 成到 8 成 {tm.loc['D60→D80', '天數 格中位']:.0f} 天、8 成到頂 {tm.loc['D80→P', '天數 格中位']:.0f} 天（全程 {tm.loc['t→P', '天數 格中位']:.0f} 天）。</li>",
         f"<li>納入 {META['納入特徵數 K']} 個特徵（其中 {META['其中價格位置類']} 個是價格位置類，頂點必然偏高、構造使然）。</li>",
         f"<li>非價格位置類：6 成時就已過半的 {len(na)} 個；6 成→8 成明顯增加的 {len(nb)} 個；8 成→頂明顯增加的 {len(nc)} 個。</li>",
         "<li>隔天：" + "；".join(f"{pt} 收跌停 {P_(nd.loc[(pt, '收跌停'), '中位'])}、收跌≥5% {P_(nd.loc[(pt, '收跌≥5%'), '中位'])}" for pt in PTS) + "。</li></ul>"]

    def newtab(df, title, col):
        H.append(f"<h3>{title}（{len(df)} 個）</h3><div class='wrap'><table><tr><th class='l'>特徵</th><th>起漲</th><th>6 成</th><th>8 成</th><th>頂</th><th>一般</th></tr>")
        for r in df.to_dict("records"):
            H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td>" + "".join(f"<td class='{'up' if k == col else ''}'>{P_(r[k])}</td>" for k in ("t", "D60", "D80", "P")) + f"<td>{P_(r['一般'])}</td></tr>")
        H.append("</table></div>")
    H.append("<h2>一、非價格位置類（籌碼、注意處置、漲停、周轉、融資、營收、財報、技術…）</h2>")
    newtab(na, "6 成時就已出現（≥ 50%）", "D60"); newtab(nb, "6 成 → 8 成明顯增加（+15 點以上）", "D80"); newtab(nc, "8 成 → 頂明顯增加（+15 點以上）", "P")
    H.append(f"<h3>全部非價格位置類（{len(np_)} 個）</h3><div class='wrap'><table><tr><th class='l'>特徵</th><th>起漲</th><th>6 成</th><th>8 成</th><th>頂</th><th>一般</th><th>頂的倍數</th></tr>")
    for r in np_.sort_values(PTS[3], ascending=False).to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}<br><small>{html.escape(r['可得時點'])}</small></td>" + "".join(f"<td>{P_(r[pt])}</td>" for pt in PTS) + f"<td>{P_(r['一般'])}</td><td>{X_(r[PTS[3] + ' 倍數'])}</td></tr>")
    H.append("</table></div>")
    H.append(f"<h2>二、價格位置類（{len(pp_)} 個；構造使然，頂點必然偏高）</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>起漲</th><th>6 成</th><th>8 成</th><th>頂</th><th>一般</th></tr>")
    for r in pp_.sort_values(PTS[1], ascending=False).to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td>" + "".join(f"<td>{P_(r[pt])}</td>" for pt in PTS) + f"<td>{P_(r['一般'])}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>三、你給的原門檻版</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>起漲</th><th>6 成</th><th>8 成</th><th>頂</th><th>一般</th></tr>")
    for r in ORIG.sort_values(PTS[3], ascending=False).to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td>" + "".join(f"<td>{P_(r[pt])}</td>" for pt in PTS) + f"<td>{P_(r['一般'])}</td></tr>")
    H.append("</table></div>")
    H.append(f"<h2>四、同時有幾個（共 {META['納入特徵數 K']} 個）</h2><div class='wrap'><table><tr><th>至少</th>" + "".join(f"<th>{pt}</th>" for pt in PTS) + "<th>一般</th></tr>")
    K = META["納入特徵數 K"]
    for j in range(0, K + 1, max(1, K // 12)):
        row = [DI[(DI["點"] == pt) & (DI["同時有幾個"] == j)]["至少 中位"].iloc[0] for pt in PTS]
        H.append(f"<tr><td>{j} 個</td>" + "".join(f"<td>{P_(v)}</td>" for v in row) + f"<td>{P_(DI[(DI['點'] == PTS[0]) & (DI['同時有幾個'] == j)]['至少 一般 中位'].iloc[0])}</td></tr>")
    H.append("</table></div><p class='note'>逐個分佈見 count_dist.csv。</p>")
    H.append("<h2>五、時間</h2><div class='wrap'><table><tr><th class='l'>區間</th><th>天數（格中位）</th><th>各格 p10～p90</th></tr>")
    for r in TM.to_dict("records"):
        H.append(f"<tr><td class='l'>{r['區間']}</td><td>{r['天數 格中位']:.0f}</td><td>{r['p10']:.0f}～{r['p90']:.0f}</td></tr>")
    H.append("</table></div><h2>六、隔天表現</h2><div class='wrap'><table><tr><th class='l'>項目</th>" + "".join(f"<th>{pt}</th>" for pt in PTS) + "<th>一般</th></tr>")
    for it in ["收跌停", "盤中碰跌停", "開盤跳空跌≥3%", "收跌≥5%", "收黑", "漲跌中位"]:
        H.append(f"<tr><td class='l'>{it}</td>" + "".join(f"<td>{P_(nd.loc[(pt, it), '中位'])}</td>" for pt in PTS) + f"<td>{P_(nd.loc[(PTS[0], it), '一般 中位'])}</td></tr>")
    H.append("</table></div></main></body></html>")
    open(os.path.join(OUT, "飆股六八成與頂點特徵.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); SEL = pd.read_csv(os.path.join(OUT, "selected.csv"))
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    FX = {c: i for i, c in enumerate(json.load(open(os.path.join(WORK5, "build.json"), encoding="utf-8"))["特徵欄"])}
    it = [x for x in CL["項"].unique() if x.startswith("D60 涵蓋率｜")][0]; fname = it.split("｜", 1)[1]
    r0 = SEL[SEL["特徵"] == fname].iloc[0]; q = np.asarray(Qm[FX[r0["欄"]]])
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False); errs = []; info = {}; CF = {}; D.DATA = S5.ST
    for c in pick:
        nm = S5.cell_name(c); k = np.flatnonzero(E["cell"] == c); d60s = []; gaps = []
        for i in k:
            s, t, P = int(E["s"][i]), int(E["d"][i]), int(E["P"][i])
            if s not in CF:
                CF[s] = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal).df["close"].ffill().to_numpy(float)
            cff = CF[s]
            lvl = cff[t] + 0.6 * (cff[P] - cff[t]); d = t + 1
            while cff[d] < lvl * (1 - 1e-9):
                d += 1
            d60s.append((s, d)); gaps.append(d - t)
        v = np.array([q[s, d] for s, d in d60s]); mine = (v == r0["碼"]).sum() / (v > 0).sum()
        ref = CL[(CL["格"] == nm) & (CL["項"] == it)]["值"].iloc[0]
        if not np.isclose(mine, ref, rtol=1e-6):
            errs.append(f"{nm} D60 涵蓋率：{mine} 檔 {ref}")
        g2 = float(np.median(gaps)); ref2 = CL[(CL["格"] == nm) & (CL["項"] == "t→D60 天數中位")]["值"].iloc[0]
        if not np.isclose(g2, ref2):
            errs.append(f"{nm} t→D60：{g2} 檔 {ref2}")
        info[nm] = {"事件": len(k), "D60 涵蓋率": float(mine), "t→D60 中位": g2}
    out = {"抽格": list(info), "級距": fname, "比對": info, "錯誤數": len(errs), "錯誤": errs}
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
