# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：處置與注意「從起漲點 t 起累計」（⛔ 只描述；看過前面結果之後才補，照實記）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_dispcum [--check]

⚠ 真頂、中段頂、中段底、6 成、8 成點都是事後才知道的；只有「每個創新高日」那一塊是當下真的能用的版本。

═══ 讀法（寫死於 2026-09-29 22:05（台北），在算任何數字之前；使用者：「處置跟注意應該用從起漲點日期算到頂才對吧？」）═══
 C1 事件、格：seq6 events、事件 ≥ 30 的 182 格；逐格算、取格中位附 p10～p90；分段 ＝ mid_desc x＝20%（M2／M2b）
 C2 量（每個事件、每一天 d，t ≤ d ≤ P；資料 ＝ main attention／disposal，同 exitsig）：
    累計注意次數 ＝ 注意日落在 [t, d] 的次數（注意日 ＝ attention 檔的日期，d 當天含，同 seq5 att_L）
    累計處置次數 ＝ 處置起日落在 [t, d] 的次數；「第二次處置」＝ 累計 ≥ 2
    累計處置天數 ＝ [t, d] 內處置中的交易日數（s5work disp，起訖含）
    目前處置中 ＝ d 在某次處置起訖內｜距上次出關天數 ＝ d − 出關日（出關日 ＝ 迄日的下一個交易日，同 exitsig S7；出關日 ≤ d 的最近一次；不限 t 之後；從未處置 ＝ 沒有值）
 C3 點：t、D60、D80（progress_desc R2）、中段頂 H1、H2、H3 以後、中段底 L2、L3、L4 以後、真頂 P；各點各量：格內中位、p25、p75（再取格中位）、累計處置 0／1／2／3 次以上比例、處置中比例
    某點在某格少於 30 個 ⇒ 該格不進該點
 C4 真頂 vs 中段頂（全部 Hk 合併）：累計處置次數 0／1／2／3+ 分佈並列
 C5 當下可用版：每個事件 (t, P] 內每個「收盤 ＞ [t, 前一日] 最高收盤」的日子（同 topjudge T5）；依 累計處置次數 0／1／2／3+、累計注意次數五等分
    （分界 ＝ 探索段 2021-01～2023-12 全部創新高日的 20／40／60／80 分位，同值落同一格）分組，報之後 60 日不再創新高、60 日內回落 20／30%（同 topjudge 定義）
    各組在某格 ＜ 30 列不進該格
 C6 第一次達到累計處置 1／2／3 次（d ≤ P）：達到的事件比例；那天漲到全程幾成 ＝ (c[d] − c[t]) ÷ (c[P] − c[t])；離頂天數 ＝ P − d
 C7 查核（--check）：抽 2 格，逐區間迴圈重算 P 點累計處置次數分佈、第一次達到 1 次的比例與幾成中位 ⇒ 對長表
輸出 backtest/resultsSurge6/dispcum/
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
from backtest import researchSurge6_progress_desc as PG

warnings.filterwarnings("ignore", category=RuntimeWarning)
D = S5.D
TIME = "2026-09-29 22:05（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/dispcum"
q3 = ED.q3; P_ = ED.P_; X_ = ED.X_
EXP = (2021 * 12, 2023 * 12 + 11)
QTY = ["累計注意次數", "累計處置次數", "累計處置天數", "目前處置中", "距上次出關天數"]
PTN = ["t（起漲）", "D60（6 成）", "D80（8 成）", "中段頂 H1", "中段頂 H2", "中段頂 H3 以後", "中段底 L2", "中段底 L3", "中段底 L4 以後", "真頂 P"]


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    es, ed, Pv, ec = E["s"].astype(int), E["d"].astype(int), E["P"].astype(int), E["cell"].astype(int)
    W, _ = S5.world(log); disp = np.load(os.path.join(WORK5, "disp.npy"))
    d60, d80 = PG.progress_days(uni, cal, E)
    PT = {k: [] for k in ("ev", "pt", "d", *QTY)}; NH = {k: [] for k in ("cell", "d", "disp", "att", "no60", "dd20", "dd30")}; FR = []
    D.DATA = S5.ST
    for s in np.unique(es):
        sid = uni.loc[s, "stock_id"]
        c = pd.Series(D.load_stock(sid, uni.loc[s, "market"], cal).df["close"].to_numpy(float)).ffill().to_numpy()
        att = np.zeros(n + 1, np.int64); a_ = W["ATT"].get(sid, np.zeros(0, int)); a_ = a_[(a_ >= 0) & (a_ < n)]
        np.add.at(att, a_ + 1, 1); ca = np.cumsum(att)                                           # ca[d＋1] ＝ ≤ d 的注意數
        iv = W["DISP"].get(sid, []); st_ = np.array(sorted(a for a, b in iv)); ex_ = np.array(sorted(b + 1 for a, b in iv))
        cd_ = np.r_[0, np.cumsum(disp[s])]
        rv = pd.Series(c[::-1]); f60 = np.r_[rv.rolling(60, min_periods=60).max().to_numpy()[::-1][1:], np.nan]; m60 = np.r_[rv.rolling(60, min_periods=60).min().to_numpy()[::-1][1:], np.nan]
        lim = np.arange(n) + 60 > t1; f60[lim] = np.nan; m60[lim] = np.nan

        def qty(t, d):
            d = np.asarray(d)
            j = np.searchsorted(ex_, d, "right") - 1
            return {"累計注意次數": (ca[d + 1] - ca[t]).astype(float), "累計處置次數": (np.searchsorted(st_, d, "right") - np.searchsorted(st_, t, "left")).astype(float),
                    "累計處置天數": (cd_[d + 1] - cd_[t]).astype(float), "目前處置中": disp[s, d].astype(float),
                    "距上次出關天數": (np.where(j >= 0, d - ex_[np.maximum(j, 0)], np.nan) if len(ex_) else np.full(d.shape, np.nan)).astype(float)}
        for i in np.flatnonzero(es == s):
            t, P = ed[i], Pv[i]
            pbs = MD.pullbacks(c[t:P + 1]); cuts = [(t + a, t + b) for a, b, lo, hi in pbs if a > 0 and lo <= hi * 0.8 * (1 + 1e-9)]
            pts = [(PTN[0], t), (PTN[1], d60[i]), (PTN[2], d80[i]), (PTN[9], P)]
            for k, (h_, l_) in enumerate(cuts, 1):
                pts.append((PTN[3 + min(k, 3) - 1], h_)); pts.append((PTN[6 + min(k + 1, 4) - 2], l_))
            nm, dd = zip(*pts); q = qty(t, np.array(dd))
            PT["ev"].append(np.full(len(dd), i)); PT["pt"].append(np.array([PTN.index(x) for x in nm])); PT["d"].append(np.array(dd))
            for k in QTY:
                PT[k].append(q[k])
            cs = c[t:P + 1]; rm = np.maximum.accumulate(cs); nh = t + np.flatnonzero(cs[1:] > rm[:-1]) + 1
            q2 = qty(t, nh)
            NH["cell"].append(np.full(len(nh), ec[i])); NH["d"].append(nh); NH["disp"].append(q2["累計處置次數"]); NH["att"].append(q2["累計注意次數"])
            NH["no60"].append(np.where(np.isfinite(f60[nh]), f60[nh] <= c[nh], np.nan)); NH["dd20"].append(np.where(np.isfinite(m60[nh]), m60[nh] <= c[nh] * 0.8, np.nan))
            NH["dd30"].append(np.where(np.isfinite(m60[nh]), m60[nh] <= c[nh] * 0.7, np.nan))
            inw = st_[(st_ >= t) & (st_ <= P)]
            for kk in (1, 2, 3):
                if len(inw) >= kk:
                    d = int(inw[kk - 1]); FR.append((i, kk, 1, (c[d] - c[t]) / (c[P] - c[t]), P - d))
                else:
                    FR.append((i, kk, 0, np.nan, np.nan))
    PT = {k: np.concatenate(v) for k, v in PT.items()}; NH = {k: np.concatenate(v) for k, v in NH.items()}; FR = np.array(FR, float)
    log(f"[點] {len(PT['d']):,}｜創新高日 {len(NH['d']):,}｜{time.time() - T0:.0f}s")
    pc = ec[PT["ev"]]; cl = np.array(cells)
    # C3 各點分佈
    DS = []; CL = []
    for pi, pn in enumerate(PTN):
        m_ = PT["pt"] == pi; per = {}
        for c in cells:
            w = m_ & (pc == c)
            if w.sum() >= 30:
                per[c] = w
        r = {"點": pn, "可用格": len(per), "點數": int(m_.sum())}
        for k in QTY:
            for st, fn in (("中位", np.nanmedian), ("p25", lambda v: np.nanpercentile(v, 25)), ("p75", lambda v: np.nanpercentile(v, 75))):
                r[f"{k} {st}"] = q3([fn(PT[k][w]) for w in per.values()])[0] if per else np.nan
        for v, lab in ((0, "0 次"), (1, "1 次"), (2, "2 次"), (3, "3 次以上")):
            r[f"累計處置 {lab}"] = q3([np.mean(np.minimum(PT["累計處置次數"][w], 3) == v) for w in per.values()])[0] if per else np.nan
        r["處置中比例"] = q3([np.mean(PT["目前處置中"][w]) for w in per.values()])[0] if per else np.nan
        r["從未處置比例（距出關無值）"] = q3([np.mean(~np.isfinite(PT["距上次出關天數"][w])) for w in per.values()])[0] if per else np.nan
        DS.append(r)
        if pn == "真頂 P":
            for c, w in per.items():
                for v in (0, 1, 2, 3):
                    CL.append({"格": S5.cell_name(c), "項": f"P 累計處置 {v}", "值": float(np.mean(np.minimum(PT['累計處置次數'][w], 3) == v))})
    DS = pd.DataFrame(DS); DS.to_csv(os.path.join(OUT, "points.csv"), index=False, float_format="%.5g")
    # C4 真頂 vs 中段頂
    TV = []
    for nm, m_ in (("真頂 P", PT["pt"] == 9), ("中段頂（全部 Hk）", np.isin(PT["pt"], [3, 4, 5]))):
        per = [m_ & (pc == c) for c in cells if (m_ & (pc == c)).sum() >= 30]
        r = {"點": nm, "可用格": len(per)}
        for v, lab in ((0, "0 次"), (1, "1 次"), (2, "2 次"), (3, "3 次以上")):
            y = q3([np.mean(np.minimum(PT["累計處置次數"][w], 3) == v) for w in per]); r[lab] = y[0]; r[f"{lab} p10"] = y[1]; r[f"{lab} p90"] = y[2]
        TV.append(r)
    TV = pd.DataFrame(TV); TV.to_csv(os.path.join(OUT, "true_vs_mid.csv"), index=False, float_format="%.5g")
    # C5 當下可用版
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); nm_ = mon[NH["d"]]; expm = (nm_ >= EXP[0]) & (nm_ <= EXP[1])
    bd = np.nanpercentile(NH["att"][expm], [20, 40, 60, 80]); aq = np.searchsorted(bd, NH["att"], "right") + 1
    order = np.argsort(NH["cell"], kind="stable"); cb = np.searchsorted(NH["cell"][order], np.arange(251)); ROWS = {c: order[cb[c]:cb[c + 1]] for c in cells}
    RT = []
    for var, codes, labs in (("累計處置次數", np.minimum(NH["disp"], 3).astype(int), ["0 次", "1 次", "2 次", "3 次以上"]), ("累計注意次數", aq - 1, [f"Q{q}" for q in range(1, 6)])):
        for v, lab in enumerate(labs):
            r = {"分組": var, "級": lab if var == "累計處置次數" else f"{lab}（{'−∞' if v == 0 else f'{bd[v - 1]:.0f}'}～{'∞' if v == 4 else f'{bd[v]:.0f}'}）"}
            covs = []
            for yk, ynm in (("no60", "60日不再創新高"), ("dd20", "60日內回落20%"), ("dd30", "60日內回落30%")):
                vals = []
                for c in cells:
                    w = ROWS[c]; ww = w[(codes[w] == v) & np.isfinite(NH[yk][w])]
                    if len(ww) >= 30:
                        vals.append(NH[yk][ww].mean())
                        if yk == "no60":
                            covs.append(len(w[codes[w] == v]) / len(w))
                y = q3(vals); r[ynm] = y[0]; r[f"{ynm} p10"] = y[1]; r[f"{ynm} p90"] = y[2]
                if yk == "no60":
                    r["可用格"] = len(vals); r["占創新高日"] = q3(covs)[0]
            RT.append(r)
    base = {yk: q3([np.nanmean(NH[yk][ROWS[c]]) for c in cells])[0] for yk in ("no60", "dd20", "dd30")}
    RT.append({"分組": "全部", "級": "全部創新高日", "60日不再創新高": base["no60"], "60日內回落20%": base["dd20"], "60日內回落30%": base["dd30"], "占創新高日": 1.0, "可用格": len(cells)})
    RT = pd.DataFrame(RT); RT.to_csv(os.path.join(OUT, "realtime.csv"), index=False, float_format="%.5g")
    # C6 第一次達到
    FRD = []
    fev = FR[:, 0].astype(int); fcell = ec[fev]
    for kk in (1, 2, 3):
        m_ = FR[:, 1] == kk; r = {"第幾次": kk}
        ach = [FR[m_ & (fcell == c), 2].mean() for c in cells]; y = q3(ach); r["達到的事件比例"] = y[0]; r["p10"] = y[1]; r["p90"] = y[2]
        g = [(FR[m_ & (fcell == c) & (FR[:, 2] == 1), 3], FR[m_ & (fcell == c) & (FR[:, 2] == 1), 4]) for c in cells]
        g = [x for x in g if len(x[0]) >= 30]
        r["可用格"] = len(g); r["漲到全程幾成 中位"] = q3([np.median(a) for a, b in g])[0] if g else np.nan; r["離頂天數 中位"] = q3([np.median(b) for a, b in g])[0] if g else np.nan
        r["漲到全程幾成 p25"] = q3([np.percentile(a, 25) for a, b in g])[0] if g else np.nan; r["漲到全程幾成 p75"] = q3([np.percentile(a, 75) for a, b in g])[0] if g else np.nan
        FRD.append(r)
        if kk == 1:
            for c in cells:
                w = m_ & (fcell == c); CL.append({"格": S5.cell_name(c), "項": "第一次處置 達到比例", "值": float(FR[w, 2].mean())})
                ww = w & (FR[:, 2] == 1); CL.append({"格": S5.cell_name(c), "項": "第一次處置 幾成中位", "值": float(np.median(FR[ww, 3])) if ww.any() else np.nan})
    FRD = pd.DataFrame(FRD); FRD.to_csv(os.path.join(OUT, "first_reach.csv"), index=False, float_format="%.5g")
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "注意次數五等分分界（探索段創新高日）": [float(b) for b in bd], "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, DS, TV, RT, FRD)
    log(f"[完] {time.time() - T0:.0f}s")


def page(META, DS, TV, RT, FRD):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}.ok{border-left:4px solid #2b6cb0;padding:6px 10px;background:#eef4fb}"
    ds = DS.set_index("點"); tv = TV.set_index("點"); rt = RT
    N0 = lambda v: "—" if not np.isfinite(v) else f"{v:.0f}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>處置注意從起漲累計</title>", f"<style>{CSS}</style></head><body><main>", "<h1>處置、注意：從起漲那天開始算，漲到哪裡累積了幾次？（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 真頂、中段頂、中段底、6 成、8 成點都是事後才知道的；只有「每個創新高日」那一塊當下真的能用。只描述，看過前面結果之後才補。</p>",
         f"<p class='lead'>{META['合格格數']} 種飆股定義各算一次取中位數；中段頂／底用拉回 20% 切段。讀法寫死 {html.escape(META['讀法寫死'])}。</p><h2>先講結論</h2><ul>"]
    H.append(f"<li>從起漲到真頂，累計進入處置：0 次 {P_(tv.loc['真頂 P', '0 次'])}、1 次 {P_(tv.loc['真頂 P', '1 次'])}、2 次 {P_(tv.loc['真頂 P', '2 次'])}、3 次以上 {P_(tv.loc['真頂 P', '3 次以上'])}；"
             f"中段頂分別 {P_(tv.loc['中段頂（全部 Hk）', '0 次'])}、{P_(tv.loc['中段頂（全部 Hk）', '1 次'])}、{P_(tv.loc['中段頂（全部 Hk）', '2 次'])}、{P_(tv.loc['中段頂（全部 Hk）', '3 次以上'])}。</li>")
    f1 = FRD.set_index("第幾次")
    H.append("<li>第一次進入處置時：" + "；".join(f"第 {k} 次（{P_(f1.loc[k, '達到的事件比例'])} 的飆股到頂前達到）漲到全程 {P_(f1.loc[k, '漲到全程幾成 中位'])}、離頂 {N0(f1.loc[k, '離頂天數 中位'])} 天" for k in (1, 2, 3)) + "。</li>")
    b = rt[rt["分組"] == "全部"].iloc[0]; d3 = rt[(rt["分組"] == "累計處置次數")]
    H.append(f"<li class='ok'>當下可用版（每個創新高日）：全部之後 60 日不再創新高 {P_(b['60日不再創新高'])}、60 日內回落 20% {P_(b['60日內回落20%'])}；"
             + "；".join(f"累計處置 {r['級']}：{P_(r['60日不再創新高'])}、{P_(r['60日內回落20%'])}" for r in d3.to_dict("records")) + "。</li></ul>")
    H.append("<h2>一、各點累計了多少（中位；p25～p75）</h2><div class='wrap'><table><tr><th class='l'>點</th><th>累計注意</th><th>累計處置次數</th><th>累計處置天數</th><th>處置中</th><th>距上次出關</th></tr>")
    for r in DS.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['點'])}<br><small>{r['可用格']} 格</small></td>" + "".join(f"<td>{N0(r[f'{k} 中位'])}<br><small>{N0(r[f'{k} p25'])}～{N0(r[f'{k} p75'])}</small></td>" for k in ("累計注意次數", "累計處置次數", "累計處置天數"))
                 + f"<td>{P_(r['處置中比例'])}</td><td>{N0(r['距上次出關天數 中位'])} 天<br><small>從未處置 {P_(r['從未處置比例（距出關無值）'])}</small></td></tr>")
    H.append("</table></div><h2>二、各點累計處置 0／1／2／3 次以上的比例</h2><div class='wrap'><table><tr><th class='l'>點</th><th>0 次</th><th>1 次</th><th>2 次</th><th>3 次以上</th></tr>")
    for r in DS.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['點'])}</td>" + "".join(f"<td>{P_(r[f'累計處置 {x}'])}</td>" for x in ("0 次", "1 次", "2 次", "3 次以上")) + "</tr>")
    H.append("</table></div><h2>三、當下可用版：每個創新高日，依從起漲累計次數分組（確認＋探索合併）</h2><p class='note'>⭐ 這一塊當下真的能用。</p>"
             "<div class='wrap'><table><tr><th class='l'>分組</th><th>60日不再創新高</th><th>60日內跌20%</th><th>跌30%</th><th>占創新高日</th></tr>")
    for r in RT.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['分組'])}｜{html.escape(str(r['級']))}</td><td>{P_(r['60日不再創新高'])}</td><td>{P_(r['60日內回落20%'])}</td><td>{P_(r['60日內回落30%'])}</td><td>{P_(r['占創新高日'])}</td></tr>")
    H.append("</table></div><h2>四、第一次達到累計處置 1／2／3 次那天</h2><div class='wrap'><table><tr><th>第幾次</th><th>到頂前達到的比例</th><th>漲到全程幾成（p25～p75）</th><th>離頂天數</th></tr>")
    for r in FRD.to_dict("records"):
        H.append(f"<tr><td>{int(r['第幾次'])}</td><td>{P_(r['達到的事件比例'])}</td><td>{P_(r['漲到全程幾成 中位'])}<br><small>{P_(r['漲到全程幾成 p25'])}～{P_(r['漲到全程幾成 p75'])}</small></td><td>{N0(r['離頂天數 中位'])}</td></tr>")
    H.append("</table></div></main></body></html>")
    open(os.path.join(OUT, "處置注意從起漲累計.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); disp_ = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype={"stock_id": str})
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False); errs = []; info = {}; D.DATA = S5.ST; CF = {}
    for c in pick:
        nm = S5.cell_name(c); k = np.flatnonzero(E["cell"] == c); cntP = []; first = []
        for i in k:
            s, t, P = int(E["s"][i]), int(E["d"][i]), int(E["P"][i]); sid = uni.loc[s, "stock_id"]
            g = disp_[disp_["stock_id"] == sid]
            st = sorted(int(cal.searchsorted(pd.Timestamp(x))) for x in g["start_date"])
            inw = [a for a in st if t <= a <= P]; cntP.append(min(len(inw), 3))
            if inw:
                if s not in CF:
                    CF[s] = D.load_stock(sid, uni.loc[s, "market"], cal).df["close"].ffill().to_numpy(float)
                cf = CF[s]; first.append((cf[inw[0]] - cf[t]) / (cf[P] - cf[t]))
        got = {f"P 累計處置 {v}": float(np.mean(np.array(cntP) == v)) for v in (0, 1, 2, 3)}
        got["第一次處置 達到比例"] = float(np.mean(np.array(cntP) >= 1)); got["第一次處置 幾成中位"] = float(np.median(first)) if first else np.nan
        for kk, mine in got.items():
            r = CL[(CL["格"] == nm) & (CL["項"] == kk)]
            if len(r) and not np.isclose(mine, r["值"].iloc[0], rtol=1e-5, equal_nan=True):
                errs.append(f"{nm} {kk}：{mine} 檔 {r['值'].iloc[0]}")
        info[nm] = got
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
