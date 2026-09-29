# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：起漲特徵 ≥10 個的訊號日，「快漲」與「先跌」比較（參考，⛔ 不計 N；看過前面結果之後才加）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_sig10_split [--check]

═══ 讀法（寫死於 2026-09-29 23:38（台北），在算任何數字之前）═══
 G1 訊號日：全部上市櫃普通股（s5work 母體），d 在 2021-01～2026-08 且有 K 棒；d 收盤時 overlap 的 14 個起漲特徵（researchSurge6_overlap.FEATS，Q 表碼相等）同時 ≥ 10 個；
    同一檔連續出現只取第一天：該股前 20 根 K 棒都沒有 ≥ 10 個才算新訊號
 G2 分組（還原收盤 ffill；看 d＋1～min(d＋250, 2026-08-31)）：上 ＝ 第一天收盤 ≥ c[d] × 1.15；下 ＝ 第一天收盤 ≤ c[d] × 0.85
    快漲 ＝ 上 存在且 上 − d ≤ 8，且 下 不存在或 下 ＞ 上｜先跌 ＝ 下 存在且（上 不存在或 下 ＜ 上）｜其他 ＝ 其餘（慢漲，或都沒碰到）；觀察窗被 2026-08-31 截短的照算、另報比例
 G3 特徵（d 收盤含以前可得）：① Q 表全部級距（seq5 levels()，含原門檻）；② 14 個起漲特徵各自有沒有；
    ③ 附加：當日 K 棒 —— 收漲停（未還原價、research11.limit_price）、紅K／黑K、當日漲跌、實體 (c−o)÷前收、上影 (高−max(開,收))÷前收、下影 (min(開,收)−低)÷前收
       （連續值五等分，分界 ＝ 探索段訊號日合併的 20／40／60／80 分位）；處置中；剛出關（出關日 ＝ 迄日下一交易日，落在 [d−4, d]）；
       近 5／10 日注意次數（F 表 att_5／att_10：0、1、2、3 次以上）；0050 在 200 日線上（F 表 d_mkt200）；股價級距、成交額級距已在 ①（原：股價級距、amt_20 五等分）
 G4 第一部分（兩段合併）：各級距在 快漲／先跌／其他 的涵蓋率（該級距有值者）；差距 ＝ 快漲 − 先跌；列差距最大的各 20 個（兩個方向）
 G5 第二部分：依訊號日月份分段（探索 2021-01～2023-12、確認 2024-01～2026-08）
    單一特徵剔除：探索段每個級距「剔除有此級距的訊號」後，分數 ＝（剔除後快漲比例 − 全部快漲比例）−（剔除後先跌比例 − 全部先跌比例），剩餘 ≥ 100 筆才排；取前 10，確認段照報
    簡單規則：探索段依「先跌涵蓋率 − 快漲涵蓋率」由大到小，一概念一個（概念同 end_desc W6），有此級距的先跌 ≥ 30 筆，取前 K 個（K ∈ {1, 2, 3}），有任一就剔除；確認段照報
    報：剩幾筆、每天平均幾檔（剩餘筆數 ÷ 該段交易日數）、快漲、先跌比例、漲到 15% 的中位天數（有漲到者）、20／60 日內漲到 15% 的比例（不論先跌與否）
    ⛔ 不在確認段挑；⚠ 樣本小
 G6 查核（--check）：逐檔迴圈重算訊號日（≥10、前 20 根不重複）總數與抽 300 筆的分組；重算一個級距在快漲組的涵蓋率 ⇒ 對檔
輸出 backtest/resultsSurge6/sig10_split/
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
from backtest import researchSurge6_overlap as OV
from backtest import research11 as R11

warnings.filterwarnings("ignore", category=RuntimeWarning)
D = S5.D
TIME = "2026-09-29 23:38（台北）"
WORK5 = S5.WORK
OUT = "backtest/resultsSurge6/sig10_split"
P_ = ED.P_; X_ = ED.X_
EXP = (2021 * 12, 2023 * 12 + 11); CON = (2024 * 12, 2026 * 12 + 7)
GRP = ["快漲", "先跌", "其他"]


def signals(uni, cal, n, bar, inseg, t1):
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); FX = S5.FIX
    cnt = np.zeros(bar.shape, np.int8)
    for nm, col, code in OV.FEATS:
        cnt += (np.asarray(Qm[FX[col]]) == code)
    hit = (cnt >= 10) & bar
    out = []
    for s in range(len(uni)):
        idx = np.flatnonzero(bar[s]); h = hit[s, idx]
        if not h.any():
            continue
        ch = np.r_[0, np.cumsum(h)]; k = np.arange(len(idx))
        prev20 = ch[k] - ch[np.maximum(k - 20, 0)]
        new = h & (prev20 == 0)
        for kk in np.flatnonzero(new):
            d = idx[kk]
            if inseg[d] and d <= t1:
                out.append((s, d))
    return np.array(out, int), cnt


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt_ = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    SD, cntm = signals(uni, cal, n, bar, inseg, t1); N = len(SD)
    log(f"[訊號] {N:,} 筆")
    W, _ = S5.world(log); disp = np.load(os.path.join(WORK5, "disp.npy"))
    Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); FX = S5.FIX
    rows = []; D.DATA = S5.ST
    for s in np.unique(SD[:, 0]):
        sid = uni.loc[s, "stock_id"]; df = D.load_stock(sid, uni.loc[s, "market"], cal).df
        c = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy(); o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
        raw = pd.read_csv(os.path.join(S5.ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date"); raw.index = pd.to_datetime(raw["date"])
        rc = pd.to_numeric(raw["close"].reindex(cal), errors="coerce").to_numpy(float)
        bars = np.flatnonzero(bar[s]); ex = np.array(sorted(b + 1 for a, b in W["DISP"].get(sid, [])))
        for d in SD[SD[:, 0] == s, 1]:
            e = min(d + 250, t1); w = c[d + 1:e + 1]
            up = np.flatnonzero(w >= c[d] * 1.15); dn = np.flatnonzero(w <= c[d] * 0.85)
            u = int(up[0]) + 1 if len(up) else None; dd = int(dn[0]) + 1 if len(dn) else None
            g = 0 if (u is not None and u <= 8 and (dd is None or dd > u)) else (1 if (dd is not None and (u is None or dd < u)) else 2)
            j = np.searchsorted(bars, d); pb = bars[j - 1] if j > 0 else d
            pc = c[pb]; prc = rc[pb]
            lu = float(abs(rc[d] - R11.limit_price(prc, True, 0.10)) < 1e-6) if np.isfinite(prc) and np.isfinite(rc[d]) else np.nan
            rows.append({"s": s, "d": d, "組": GRP[g], "上": u, "下": dd, "窗截短": int(d + 250 > t1), "月": mon[d],
                         "收漲停": lu, "紅K": float(c[d] > o[d]), "當日漲跌": c[d] / pc - 1, "實體": (c[d] - o[d]) / pc, "上影": (h[d] - max(o[d], c[d])) / pc, "下影": (min(o[d], c[d]) - l[d]) / pc,
                         "處置中": float(disp[s, d]), "剛出關": float(((ex >= d - 4) & (ex <= d)).any()),
                         "近5日注意次數": float(min(np.asarray(Fm[FX["att_5"], s, d]), 3)), "近10日注意次數": float(min(np.asarray(Fm[FX["att_10"], s, d]), 3)),
                         "0050在200日線上": float(np.asarray(Fm[FX["d_mkt200"], s, d]))})
    T = pd.DataFrame(rows).sort_values(["d", "s"]).reset_index(drop=True)
    T["段"] = np.where((T["月"] >= EXP[0]) & (T["月"] <= EXP[1]), "探索", "確認")
    log(f"[分組] {T['組'].value_counts().to_dict()}｜{time.time() - T0:.0f}s")
    # 級距
    LEVS = []                                                   # (名稱, 概念, 來源, 碼陣列（0 ＝ 沒值）, 碼)
    for lv in FT.levels():
        q = np.asarray(Qm[lv[0]])[T["s"], T["d"]]; LEVS.append((f"{lv[4]}｜{lv[3]}", ED.concept(lv[1]), "Q表", q, lv[2]))
    for j, (nm, col, code) in enumerate(OV.FEATS):
        q = (np.asarray(Qm[FX[col]])[T["s"], T["d"]] == code).astype(int) + 1; LEVS.append((f"起漲特徵：{nm}｜有", f"起漲:{col}", "起漲14", q, 2))
    expm = T["段"] == "探索"
    for f in ("當日漲跌", "實體", "上影", "下影"):
        v = T[f].to_numpy(float); bd = np.nanpercentile(v[expm & np.isfinite(v)], [20, 40, 60, 80]); cd = np.where(np.isfinite(v), np.searchsorted(bd, v, "right") + 1, 0)
        for q in range(1, 6):
            lo = "−∞" if q == 1 else f"{bd[q - 2] * 100:.1f}%"; hi = "∞" if q == 5 else f"{bd[q - 1] * 100:.1f}%"
            LEVS.append((f"K棒 {f}｜Q{q}（{lo}～{hi}）", f"K:{f}", "附加", cd, q))
    for f in ("收漲停", "紅K", "處置中", "剛出關", "0050在200日線上"):
        v = T[f].to_numpy(float); cd = np.where(np.isfinite(v), v + 1, 0).astype(int)
        LEVS.append((f"{f}｜是", f"A:{f}", "附加", cd, 2)); LEVS.append((f"{f}｜否", f"A:{f}", "附加", cd, 1))
    for f in ("近5日注意次數", "近10日注意次數"):
        v = T[f].to_numpy(float); cd = np.where(np.isfinite(v), v + 1, 0).astype(int)
        for q, nm in ((1, "0 次"), (2, "1 次"), (3, "2 次"), (4, "3 次以上")):
            LEVS.append((f"{f}｜{nm}", f"A:{f}", "附加", cd, q))
    g = T["組"].to_numpy()
    # 第一部分
    P1 = []
    for nm, cp, src, cd, code in LEVS:
        r = {"特徵": nm, "概念": cp, "來源": src}
        for gg in GRP:
            m_ = (g == gg) & (cd > 0); r[f"{gg} 涵蓋"] = float((cd[m_] == code).mean()) if m_.any() else np.nan; r[f"{gg} 有值筆數"] = int(m_.sum())
        r["差距(快漲−先跌)"] = r["快漲 涵蓋"] - r["先跌 涵蓋"]; P1.append(r)
    P1 = pd.DataFrame(P1); P1.to_csv(os.path.join(OUT, "part1_all.csv.gz"), index=False, float_format="%.5g")
    ok1 = (P1["快漲 有值筆數"] >= 20) & (P1["先跌 有值筆數"] >= 20)
    UP20 = P1[ok1].sort_values("差距(快漲−先跌)", ascending=False).head(20); DN20 = P1[ok1].sort_values("差距(快漲−先跌)").head(20)
    UP20.to_csv(os.path.join(OUT, "part1_fast_more_top20.csv"), index=False, float_format="%.5g"); DN20.to_csv(os.path.join(OUT, "part1_drop_more_top20.csv"), index=False, float_format="%.5g")
    # 第二部分
    ndays = {sg: int(((mon >= a) & (mon <= b)).sum()) for sg, (a, b) in (("探索", EXP), ("確認", CON))}

    def stats(mask, sg):
        t = T[mask & (T["段"] == sg).to_numpy()]
        up = t["上"].to_numpy(float)
        return {"剩幾筆": len(t), "每天平均幾檔": len(t) / ndays[sg], "快漲": (t["組"] == "快漲").mean() if len(t) else np.nan, "先跌": (t["組"] == "先跌").mean() if len(t) else np.nan,
                "漲到15%中位天數": float(np.nanmedian(up)) if np.isfinite(up).any() else np.nan, "20日內漲15%": float(np.mean(np.nan_to_num(up, nan=999) <= 20)) if len(t) else np.nan,
                "60日內漲15%": float(np.mean(np.nan_to_num(up, nan=999) <= 60)) if len(t) else np.nan}
    allm = np.ones(N, bool)
    B = {sg: stats(allm, sg) for sg in ("探索", "確認")}
    SC = []
    for j, (nm, cp, src, cd, code) in enumerate(LEVS):
        keep = ~(cd == code)
        st = stats(keep, "探索")
        if st["剩幾筆"] < 100 or st["剩幾筆"] == B["探索"]["剩幾筆"]:
            continue
        SC.append((j, (st["快漲"] - B["探索"]["快漲"]) - (st["先跌"] - B["探索"]["先跌"]), st))
    SC.sort(key=lambda x: -x[1])
    S1 = [{"規則": "（全部，不剔除）", **{f"探索 {k}": v for k, v in B["探索"].items()}, **{f"確認 {k}": v for k, v in B["確認"].items()}}]
    for j, sc, st in SC[:10]:
        nm, cp, src, cd, code = LEVS[j]; keep = ~(cd == code)
        S1.append({"規則": f"剔除「{nm}」", "探索分數": sc, **{f"探索 {k}": v for k, v in st.items()}, **{f"確認 {k}": v for k, v in stats(keep, "確認").items()}})
    S1 = pd.DataFrame(S1); S1.to_csv(os.path.join(OUT, "part2_single.csv"), index=False, float_format="%.5g")
    ex_t = T["段"] == "探索"
    RK = []
    for j, (nm, cp, src, cd, code) in enumerate(LEVS):
        m1 = ex_t & (g == "先跌") & (cd > 0); m0 = ex_t & (g == "快漲") & (cd > 0)
        if ((cd == code) & m1).sum() < 30 or not m0.any():
            continue
        RK.append((j, cp, float((cd[m1] == code).mean() - (cd[m0] == code).mean())))
    RK.sort(key=lambda x: -x[2]); pick = []; seen = set()
    for j, cp, dv in RK:
        if cp not in seen:
            pick.append((j, dv)); seen.add(cp)
        if len(pick) == 3:
            break
    S2 = [S1.iloc[0].to_dict()]
    for K in (1, 2, 3):
        rem = np.zeros(N, bool)
        for j, dv in pick[:K]:
            rem |= LEVS[j][3] == LEVS[j][4]
        keep = ~rem
        S2.append({"規則": f"K＝{K}：剔除任一「" + "」「".join(LEVS[j][0] for j, _ in pick[:K]) + "」", **{f"探索 {k}": v for k, v in stats(keep, "探索").items()}, **{f"確認 {k}": v for k, v in stats(keep, "確認").items()}})
    S2 = pd.DataFrame(S2); S2.to_csv(os.path.join(OUT, "part2_rule.csv"), index=False, float_format="%.5g")
    T.to_csv(os.path.join(OUT, "signals.csv.gz"), index=False, float_format="%.6g")
    META = {"讀法寫死": TIME, "訊號筆數": N, "分組": T["組"].value_counts().to_dict(), "各段": T.groupby("段")["組"].value_counts().unstack().to_dict("index"),
            "觀察窗被截短比例": float(T["窗截短"].mean()), "各段交易日數": ndays, "簡單規則選入": [(LEVS[j][0], dv) for j, dv in pick], "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, UP20, DN20, S1, S2)
    log(f"[完] {time.time() - T0:.0f}s")


def page(META, UP20, DN20, S1, S2):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\ntd.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
    N0 = lambda v: "—" if not np.isfinite(v) else f"{v:.0f}"
    b = S1.iloc[0]; gg = META["分組"]; nn = META["訊號筆數"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>10個以上快漲與先跌</title>", f"<style>{CSS}</style></head><body><main>", "<h1>起漲特徵 ≥10 個那天：快漲的和先跌的，差在哪？能先剔除嗎？（2021–2026-08）</h1>",
         f"<p class='warn'>⚠ 只當參考，沒有計入檢定數；樣本小（確認段 {int(b['確認 剩幾筆'])} 筆），比例的誤差可能有好幾個百分點。挑選只在探索段（2021–2023）做，確認段（2024–2026-08）照報。</p>",
         f"<p class='lead'>訊號 ＝ 當天收盤 14 個起漲特徵同時有 10 個以上（同一檔前 20 天沒出現過才算新的），共 {nn:,} 筆：快漲（8 天內漲 15% 且沒先跌 15%）{gg.get('快漲', 0):,}、先跌（先跌 15%）{gg.get('先跌', 0):,}、其他 {gg.get('其他', 0):,}。讀法寫死 {html.escape(META['讀法寫死'])}。</p>"]
    r3 = S2.iloc[-1]
    H.append("<h2>先講結論</h2><ul>")
    H.append(f"<li>全部訊號（確認段）：快漲 {P_(b['確認 快漲'])}、先跌 {P_(b['確認 先跌'])}；60 日內漲到 15% {P_(b['確認 60日內漲15%'])}；每天平均 {b['確認 每天平均幾檔']:.2f} 檔。</li>")
    H.append("<li>快漲的比較常有：" + "、".join(f"{html.escape(r['特徵'])}（{P_(r['快漲 涵蓋'])} 對 {P_(r['先跌 涵蓋'])}）" for r in UP20.head(4).to_dict("records")) + "。</li>")
    H.append("<li>先跌的比較常有：" + "、".join(f"{html.escape(r['特徵'])}（{P_(r['先跌 涵蓋'])} 對 {P_(r['快漲 涵蓋'])}）" for r in DN20.head(4).to_dict("records")) + "。</li>")
    H.append(f"<li>簡單剔除規則（探索段選的 {html.escape(r3['規則'])}）在確認段：剩 {int(r3['確認 剩幾筆'])} 筆，快漲 {P_(r3['確認 快漲'])}、先跌 {P_(r3['確認 先跌'])}（全部 {P_(b['確認 快漲'])}／{P_(b['確認 先跌'])}）。</li></ul>")
    for title, df, a, bcol in (("一、快漲比較多的 20 個", UP20, "快漲", "先跌"), ("二、先跌比較多的 20 個", DN20, "先跌", "快漲")):
        H.append(f"<h2>{title}（兩段合併）</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>快漲</th><th>先跌</th><th>其他</th><th>差</th></tr>")
        for r in df.to_dict("records"):
            H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{P_(r['快漲 涵蓋'])}</td><td>{P_(r['先跌 涵蓋'])}</td><td>{P_(r['其他 涵蓋'])}</td><td>{P_(r['差距(快漲−先跌)'])}</td></tr>")
        H.append("</table></div>")
    for title, df in (("三、單一特徵剔除（探索選前 10，確認照報）", S1), ("四、簡單規則：有任一個就剔除（K＝1、2、3）", S2)):
        H.append(f"<h2>{title}</h2><div class='wrap'><table><tr><th class='l'>規則</th><th>確認 剩幾筆（每天）</th><th>快漲</th><th>先跌</th><th>漲到15%天數</th><th>20／60日內漲15%</th><th>探索 快漲／先跌</th></tr>")
        for r in df.to_dict("records"):
            H.append(f"<tr><td class='l'><small>{html.escape(r['規則'])}</small></td><td>{int(r['確認 剩幾筆'])}（{r['確認 每天平均幾檔']:.2f}）</td><td>{P_(r['確認 快漲'])}</td><td>{P_(r['確認 先跌'])}</td>"
                     f"<td>{N0(r['確認 漲到15%中位天數'])}</td><td>{P_(r['確認 20日內漲15%'])}／{P_(r['確認 60日內漲15%'])}</td><td>{P_(r['探索 快漲'])}／{P_(r['探索 先跌'])}</td></tr>")
        H.append("</table></div>")
    H.append(f"<p class='note'>觀察窗（之後 250 天）被 2026-08-31 截短的訊號占 {P_(META['觀察窗被截短比例'])}，照算。</p></main></body></html>")
    open(os.path.join(OUT, "10個以上快漲與先跌比較.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt_ = ED.load()
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    T = pd.read_csv(os.path.join(OUT, "signals.csv.gz")); P1 = pd.read_csv(os.path.join(OUT, "part1_all.csv.gz"))
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); FX = S5.FIX; errs = []; info = {}
    Qs = [np.asarray(Qm[FX[col]]) for _, col, _ in OV.FEATS]; codes = [c for _, _, c in OV.FEATS]
    mine = []
    for s_ in range(len(uni)):
        bs = np.flatnonzero(bar[s_]); cntv = sum((Qs[j][s_, bs] == codes[j]).astype(int) for j in range(14))
        last = -10 ** 9
        for k in np.flatnonzero(cntv >= 10):
            d = bs[k]
            if k - last > 20 and inseg[d] and d <= t1:
                mine.append((s_, d))
            last = k
    info["逐檔重算筆數"] = len(mine); info["檔內筆數"] = len(T)
    if len(mine) != len(T):
        errs.append(f"筆數不同：{len(mine)} 檔 {len(T)}")
    D.DATA = S5.ST; nb = 0
    for r in T.sample(min(300, len(T)), random_state=1).itertuples():
        c = D.load_stock(uni.loc[r.s, "stock_id"], uni.loc[r.s, "market"], cal).df["close"].ffill().to_numpy(float)
        g = "其他"
        for d in range(r.d + 1, min(r.d + 250, t1) + 1):
            if c[d] <= c[r.d] * 0.85:
                g = "先跌"; break
            if c[d] >= c[r.d] * 1.15:
                g = "快漲" if d - r.d <= 8 else "其他"; break
        nb += int(g != r.組)
    info["抽 300 筆分組不同"] = nb
    if nb:
        errs.append(f"分組不同 {nb}")
    q = np.asarray(Qm[FX["r_5"]]); f = T[T["組"] == "快漲"]; v = q[f["s"], f["d"]]; mv = float((v[v > 0] == 1).mean())
    ref = P1[P1["特徵"] == "5日報酬｜Q1"]["快漲 涵蓋"].iloc[0]; info["5日報酬Q1 快漲涵蓋（自算／檔）"] = [mv, float(ref)]
    if not np.isclose(mv, ref, rtol=1e-4):
        errs.append("涵蓋率不同")
    out = {"比對": info, "錯誤數": len(errs), "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 錯誤 {len(errs)}｜{errs[:3]}｜{info}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
