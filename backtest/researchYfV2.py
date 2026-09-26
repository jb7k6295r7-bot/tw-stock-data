# -*- coding: utf-8 -*-
"""PREREG營飆v2候選（台股策略線登錄 seq2 sha c4e9ab933b4bfb15；裁定線 seq207 發號、N_驗收 ＋2）：主窗描述＋控制臂（⛔ 主窗不判）。
回測線，2026-09-26。早年段判定與 PREREGV 同批（⛔ 本檔不跑）。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfV2 main [--reps 200] [--out 目錄]

底：listexit_lines.setup_t1()（營飆 v1：rerun17 快照、AND、t−1 大盤閘、10 槽、H120、主窗、種子 1000＋r）
臂（主窗；⛔ 全部只描述、不判、不計 N）：
  cand1 候選一「M20 整份」＝ yfstop_lines.ma_lines(20, arm="state")、stop_line_le=False、⛔ 不給 stop_proceeds（＝ PREREG營飆停損 M20 ⓐ）
        閘：200 顆逐位元 ＝ resultsYfStop/body_seeds_arms.csv 的 a_M20（cagr／mdd／vol repr、first／end／trades、eq_sha）
  cand2 候選二「K4 排名」＝ pick="K4"、pick_tie="rng"（鍵 ＝ resultsYfRank/pre_keys.csv）
        閘：200 顆逐位元 ＝ resultsYfRank/seeds.csv 的 K4（cagr／mdd／vol repr、eq_sha）
  C1 隨機賣出＋整份（控制臂，必跑）：
        ① 經驗分佈 ＝ cand1 同窗 200 顆實際買到的部位：p ＝ 被 M20 賣掉的部位數 ÷ 全部部位數（200 顆合併）；
           觸發根分佈 ＝ 被賣部位的「觸發日是進場後第幾根有效 K 棒」（進場日 ＝ 1；200 顆合併）
        ② 每顆種子另開一支 rng：np.random.default_rng([1000＋r, 1])（⭐ 同顆種子、另一條流；⛔ 不動引擎用的 default_rng(1000＋r)）
           ⇒ 依訊號表列序，逐列抽「會不會被賣」（機率 p）；會 ⇒ 從觸發根分佈等機率抽一根 b
        ③ 建成事先算好的 stop_line：只在該列第 b 根有效 K 棒的日曆位置放必觸發的線（float64 最大有限值 BIG；stop_line_le=False ⇒ 任何有限收盤 ＜ BIG）
           ⇒ 次一有效開盤整檔賣出；⛔ 不給 stop_proceeds（＝ 整份併池，同候選一）
           第 b 根落在該列排程出場前一根之後（停牌讓有效根數不夠）⇒ 那列不賣（計數報）
        ⚠ 讀法（登錄與裁定 seq207 定「同窗」；其餘本件定、列出）：p 與觸發根兩個分佈分開抽（不保留兩者的相關）；逐「訊號列」抽（部位是列的子集，
           沒買到的列抽了也不起作用）；觸發根用有效 K 棒計
  C2 M20 不整份 ＝ PREREG營飆停損 M20 主版（引用 resultsYfStop/body_cells.csv、⛔ 不重跑）
  K0 代號尾數排名 ＝ PREREG營飆排名 K0（引用 resultsYfRank/cells.csv、⛔ 不重跑）
  base 營飆 v1 原樣（閘：＝ regime_t1 t1 #1）
「C1 ≈ 候選一」的讀法（登錄沒寫數字、本件定、看數字前寫死）：C1 對候選一同顆種子配對，兩項（年化差、回落差）皆正 ＜ 190 且皆負 ＜ 190（＝ 登錄對營飆 v1 的同一把尺判「分不出」）
  ⇒ 句中寫「好處來自錢不閒置（少了閒置現金），不是 20 日線」
輸出 backtest/resultsYfV2/：main_seeds_arms.csv、main_cells.csv、main_c1_dist.json、main_summary.json、main_run.log、REPORT.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd

from . import listexit_lines as L
from . import researchYfStop as YS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYfV2")
BIG = float(np.finfo(np.float64).max)
FOOT = "這是全部選到的股票平均起來的結果，不是對某一檔的預測"
TAG = "事後挑出、30 餘臂中最好"
_S: dict = {}


def positions(au, xmap, V):
    """audit ⇒ 每個部位 (sid, 進場 t, 是否被停損賣出, 觸發根)。"""
    pos = {}; out = []
    for a in au:
        t = int(a["t"])
        if a["side"] == "buy":
            pos[a["sid"]] = t
        elif "kind" not in a:
            s = a["sid"]; e = pos.pop(s); x = xmap[(s, e)]
            out.append((s, e, t < x, int(V[s][e:t].sum()) if t < x else 0))
    return out


def c1_lines(r, sig, V, p, bars):
    """C1：同顆種子另開一支 rng，逐列抽「賣不賣」與「第幾根」，建成必觸發的線。"""
    g = np.random.default_rng([1000 + r, 1])
    out = {}; n_sell = n_short = 0
    for s, e, x in zip(sig["sid"], sig["entry_pos"].astype(int), sig["xpos_H120"].astype(int)):
        if x < 0:
            continue
        sell = g.random() < p
        b = int(g.choice(bars)) if sell else 0
        lv = np.full(x - e + 1, np.nan)
        if sell:
            vb = np.flatnonzero(V[s][e:x - 1]) + e                   # 可觸發的日曆位置（有效 K 棒，≤ 排程出場前一根）
            if b <= len(vb):
                lv[vb[b - 1] - e] = BIG; n_sell += 1
            else:
                n_short += 1
        out[(s, e)] = (e, lv)
    return out, n_sell, n_short


def main(a):
    os.makedirs(a.out, exist_ok=True)
    logf = open(os.path.join(a.out, "main_run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    t00 = time.time()
    log(f"===== researchYfV2 main reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）⛔ 主窗只描述 =====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("research11.py", "listexit_lines.py", "yfstop_lines.py", "researchYfStop.py", "researchYfV2.py")}
    log(f"[程式 sha256] {src}")
    from . import yfstop_lines as Y
    ctx = L.setup_t1(log)
    RR, cal, w0, w1 = ctx["RR"], ctx["cal"], ctx["w0"], ctx["w1"]
    bw = RR.bench_row(cal, RR.load_bench(cal), w0, w1 + 1)
    g1 = repr(bw["cagr"]) == repr(YS.ANCHOR[0]) and repr(bw["mdd"]) == repr(YS.ANCHOR[1])
    log(f"[閘一 0050 錨] 逐位元 {g1}")
    if not g1:
        raise SystemExit("⛔ 閘一不過")
    K = pd.read_csv(os.path.join(HERE, "resultsYfRank", "pre_keys.csv"), dtype={"sid": str}, usecols=["sid", "entry_pos", "K4"], float_precision="round_trip")
    sig = ctx["sig"].merge(K, on=["sid", "entry_pos"], how="left", validate="1:1")
    assert len(sig) == len(ctx["sig"]) and not sig["K4"].isna().any()
    ctx["sig"] = sig
    YS._G.update(ctx=ctx, years=YS.years_of(cal, w0, w1), xmap={(s, int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"])})
    YS._G["valid"] = {s: YS.valid_of(s) for s in set(sig["sid"])}
    M20 = Y.ma_lines(sig, ctx["closes"], YS.bars_of, 20, arm="state")
    YS._G["ARMS"] = {"base": ({}, "base"), "cand1": ({"stop_line": M20, "stop_line_le": False}, "候選一"),
                     "cand2": ({"pick": "K4", "pick_tie": "rng"}, "候選二")}
    rows = {}
    t0 = time.time()
    for key in ("base", "cand1", "cand2"):
        rows[key] = pd.DataFrame([YS._one((key, r)) for r in range(a.reps)]).set_index("r").sort_index()
        log(f"  [{key}] {time.time() - t0:.0f}s")
    # 閘
    ref = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r").sort_index()
    rs = pd.read_csv(os.path.join(HERE, "resultsYfStop", "body_seeds_arms.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    rs = rs[rs["arm"] == "a_M20"].set_index("r").sort_index()
    rk = pd.read_csv(os.path.join(HERE, "resultsYfRank", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    rk = rk[rk["arm"] == "K4"].set_index("r").sort_index()

    def same(D, R_, cols, ints=()):
        return all(all(repr(float(D.loc[r, c])) == repr(float(R_.loc[r, c])) for c in cols) and all(int(D.loc[r, c]) == int(R_.loc[r, c]) for c in ints)
                   and str(D.loc[r, "eq_sha"]) == str(R_.loc[r, "eq_sha"]) for r in D.index)
    gates = {"一_0050錨": g1, "二_營飆v1原樣＝regime_t1": same(rows["base"], ref, ("cagr", "mdd", "vol"), ("first", "end", "trades")),
             "三_候選一＝營飆停損 M20ⓐ": same(rows["cand1"], rs, ("cagr", "mdd", "vol"), ("first", "end", "trades")),
             "四_候選二＝營飆排名 K4": same(rows["cand2"], rk, ("cagr", "mdd", "vol"), ("first", "end", "trades"))}
    log(f"[閘] {gates}")
    if not all(gates.values()):
        raise SystemExit("⛔ 閘不過")
    # C1 經驗分佈（候選一同窗 200 顆實際部位）
    ctxs = ctx; V = YS._G["valid"]; xmap = YS._G["xmap"]
    n_pos = 0; bars = []
    for r in range(a.reps):
        au = []
        L.sim(ctxs, {"stop_line": M20, "stop_line_le": False}, r, audit=au)
        P = positions(au, xmap, V)
        n_pos += len(P); bars += [b for _, _, st, b in P if st]
    p = len(bars) / n_pos
    bars = np.asarray(bars, int)
    dist = {"部位數（200 顆合併）": n_pos, "被 M20 賣掉的部位數": int(len(bars)), "p（被賣機率）": p,
            "觸發根 p10／p25／中位／p75／p90": [float(np.quantile(bars, q)) for q in (.1, .25, .5, .75, .9)], "觸發根 最小／最大": [int(bars.min()), int(bars.max())]}
    log(f"[C1 經驗分佈] {dist}")
    c1rows = []; c1_real = {"部位": 0, "被賣": 0, "根": []}; c1_cnt = {"抽中賣": 0, "有效根數不夠而不賣": 0}
    for r in range(a.reps):
        lines, ns, nsh = c1_lines(r, sig, V, p, bars)
        c1_cnt["抽中賣"] += ns; c1_cnt["有效根數不夠而不賣"] += nsh
        YS._G["ARMS"]["C1"] = ({"stop_line": lines, "stop_line_le": False}, "C1")
        c1rows.append(YS._one(("C1", r)))
        au = []
        L.sim(ctxs, {"stop_line": lines, "stop_line_le": False}, r, audit=au)
        P = positions(au, xmap, V)
        c1_real["部位"] += len(P); c1_real["被賣"] += sum(st for _, _, st, _ in P); c1_real["根"] += [b for _, _, st, b in P if st]
    rows["C1"] = pd.DataFrame(c1rows).set_index("r").sort_index()
    cb = np.asarray(c1_real["根"], int)
    dist["C1 實際：被賣比例"] = c1_real["被賣"] / c1_real["部位"]
    dist["C1 實際：觸發根 p10／p25／中位／p75／p90"] = [float(np.quantile(cb, q)) for q in (.1, .25, .5, .75, .9)]
    dist["C1 抽樣計數（200 顆 × 訊號列）"] = c1_cnt
    json.dump(dist, open(os.path.join(a.out, "main_c1_dist.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[C1] {dist}｜{time.time() - t00:.0f}s")
    A = pd.concat([d.reset_index().assign(arm=k) for k, d in rows.items()], ignore_index=True)
    A.to_csv(os.path.join(a.out, "main_seeds_arms.csv"), index=False)
    # 彙總（⛔ 不判；標籤與配對只當描述）
    base = ref.loc[range(a.reps)]
    cells = []
    for k in ("base", "cand1", "cand2", "C1"):
        g = rows[k]
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio = YS.label(c, m)
        dc = g["cagr"] - base["cagr"]; dm = g["mdd"] - base["mdd"]
        row = {"arm": k, "cagr_med": c, "mdd_med": m, "ratio": ratio, "label_desc": lab, "ratio_seed_med": float((g["cagr"] / g["mdd"].abs()).median()),
               "vs_v1_both_pos": int(((dc > 0) & (dm > 0)).sum()), "vs_v1_both_neg": int(((dc < 0) & (dm < 0)).sum()),
               "d_cagr_med": float(dc.median()), "d_mdd_med": float(dm.median())}
        if k == "C1":
            c1 = rows["cand1"]; ec = g["cagr"] - c1["cagr"]; em = g["mdd"] - c1["mdd"]
            row.update({"vs_cand1_both_pos": int(((ec > 0) & (em > 0)).sum()), "vs_cand1_both_neg": int(((ec < 0) & (em < 0)).sum()),
                        "vs_cand1_d_cagr_med": float(ec.median()), "vs_cand1_d_mdd_med": float(em.median())})
            row["C1≈候選一"] = row["vs_cand1_both_pos"] < 190 and row["vs_cand1_both_neg"] < 190
        for q in ("turnover_yr", "cost_drag_yr", "cash_mean", "cash_med", "rebuy20_n", "rebuy20_ret_mean", "rebuy20_ret_med", "n_stop", "stop_frac_pos",
                  "trig_bar_med", "trig_bar_p10", "trig_bar_p90", "stop_h120_mean", "stop_h120_med", "stop_h120_better_frac", "held_mean", "trades",
                  "ddlog_單日暴跌型", "ddlog_延續下跌型", "ddlog_混合型"):
            row[q] = float(g[q].astype(float).median())
        for q in [c_ for c_ in g.columns if c_.startswith("y") and c_[1:].isdigit()]:
            row[q] = float(g[q].median())
        cells.append(row)
    TB = pd.DataFrame(cells)
    TB.to_csv(os.path.join(a.out, "main_cells.csv"), index=False)
    S = {"登錄": "PREREG營飆v2候選 seq2 sha c4e9ab933b4bfb15（主窗描述＋控制臂；⛔ 不判）", "閘": gates, "C1經驗分佈": dist, "程式": src, "秒": round(time.time() - t00)}
    json.dump(S, open(os.path.join(a.out, "main_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(TB, S, a.out)
    log(f"[完成] {time.time() - t00:.0f}s")


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def report(TB, S, OUT_):
    T = TB.set_index("arm")
    st = pd.read_csv(os.path.join(HERE, "resultsYfStop", "body_cells.csv")).set_index("arm")
    rk = pd.read_csv(os.path.join(HERE, "resultsYfRank", "cells.csv")).set_index("key")
    c2 = st.loc["M20"]; k0 = rk.loc["K0"]; k4 = rk.loc["K4"]
    q1, q2, c1 = T.loc["cand1"], T.loc["cand2"], T.loc["C1"]
    Ls = ["# PREREG營飆v2候選：主窗描述＋控制臂（⛔ 主窗不判；早年段與 PREREGV 同批）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq2（sha c4e9ab933b4bfb15）；裁定 seq207。回測線。", "",
          f"閘：{S['閘']}", "", "## 描述句（⛔ 不下結論）", "",
          f"- 候選一「M20 整份」（{TAG}）：主窗年化中位 {_p(q1['cagr_med'])}、回落中位 {_p(q1['mdd_med'])}（對 0050 描述「{q1['label_desc']}」；"
          f"對營飆 v1 同顆兩項皆好 {q1['vs_v1_both_pos']}／皆差 {q1['vs_v1_both_neg']}）。（{FOOT}）",
          f"- 候選二「K4 排名」（{TAG}）：主窗年化中位 {_p(q2['cagr_med'])}、回落中位 {_p(q2['mdd_med'])}（對 0050 描述「{q2['label_desc']}」；"
          f"對營飆 v1 同顆兩項皆好 {q2['vs_v1_both_pos']}／皆差 {q2['vs_v1_both_neg']}；營飆排名判定時落抽籤年化第 {k4['pctl_cagr']:.1f}、比值第 {k4['pctl_ratio']:.1f} 百分位）。（{FOOT}）"]
    if bool(c1["C1≈候選一"]):
        Ls.append(f"- C1（隨機賣出＋整份）與候選一差不多（同顆配對兩項皆好 {c1['vs_cand1_both_pos']:.0f}／皆差 {c1['vs_cand1_both_neg']:.0f}，皆 ＜ 190）"
                  "⇒ 好處來自併池（少了閒置現金），不是 20 日線。")
    else:
        Ls.append(f"- C1（隨機賣出＋整份）與候選一不同（同顆配對兩項皆好 {c1['vs_cand1_both_pos']:.0f}／皆差 {c1['vs_cand1_both_neg']:.0f}）。")
    Ls.append(f"- ⚠ 拆開看（描述、不判）：回落中位 C1 {_p(c1['mdd_med'])} vs 候選一 {_p(q1['mdd_med'])}（幾乎相同 ⇒ 回落變淺主要來自併池）；"
              f"年化中位 C1 {_p(c1['cagr_med'])} vs 候選一 {_p(q1['cagr_med'])}（同顆年化差中位 {_p(c1['vs_cand1_d_cagr_med'])}；C1 兩項皆差 {c1['vs_cand1_both_neg']:.0f} 顆）"
              "⇒ 年化保住較多的那部分不能歸給併池。")
    Ls.append(f"- ⚠ M20（state）在主窗每一個部位最後都會觸發（p ＝ {S['C1經驗分佈']['p（被賣機率）']:.3f}）⇒ C1 ＝ 每個部位都在隨機的一根賣出，只保留觸發根分佈。")
    Ls += ["- 早年段（2012～2014、只上市）判定：與 PREREGV 同批，⛔ 本件未跑。", "",
           "## 主窗各臂（200 顆中位；⛔ 描述）", "",
           "| 臂 | 年化中位 | 回落中位 | 比值 | 對 0050（描述） | 對營飆 v1 皆好／皆差 | 周轉/年 | 成本/年 | 現金比例 均值／中位 | 停損後 20 日內又買回（次／報酬中位） | 觸發根 中位〔p10～p90〕 | 放棄組 抱到 120 根 平均／中位 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, nm in (("base", "營飆 v1 原樣"), ("cand1", "候選一 M20 整份"), ("C1", "C1 隨機賣出＋整份"), ("cand2", "候選二 K4 排名")):
        q = T.loc[k]
        Ls.append(f"| {nm} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.4f} | {q['label_desc']} | {q['vs_v1_both_pos']}／{q['vs_v1_both_neg']} | "
                  f"{q['turnover_yr']:.2f} | {_p(q['cost_drag_yr'])} | {q['cash_mean']:.3f}／{q['cash_med']:.3f} | {q['rebuy20_n']:.0f}／{_p(q['rebuy20_ret_med'])} | "
                  f"{q['trig_bar_med']:.0f}〔{q['trig_bar_p10']:.0f}～{q['trig_bar_p90']:.0f}〕 | {_p(q['stop_h120_mean'])}／{_p(q['stop_h120_med'])} |")
    Ls.append(f"| C2 M20 不整份（引用 resultsYfStop） | {_p(c2['cagr_med'])} | {_p(c2['mdd_med'])} | {c2['ratio']:.4f} | {c2['label']} | {c2['vs_v1_both_pos']}／{c2['vs_v1_both_neg']} | "
              f"{c2['turnover_yr']:.2f} | {_p(c2['cost_drag_yr'])} | {c2['cash_mean']:.3f}／{c2['cash_med']:.3f} | {c2['rebuy20_n']:.0f}／{_p(c2['rebuy20_ret_med'])} | "
              f"{c2['trig_bar_med']:.0f}〔{c2['trig_bar_p10']:.0f}～{c2['trig_bar_p90']:.0f}〕 | {_p(c2['stop_h120_mean'])}／{_p(c2['stop_h120_med'])} |")
    Ls.append(f"| K0 代號尾數（引用 resultsYfRank） | {_p(k0['cagr_med'])} | {_p(k0['mdd_med'])} | — | {k0['label_0050']} | {k0['pair_both_better']}／{k0['pair_both_worse']} | — | — | — | — | — | — |")
    Ls += ["", f"C1 經驗分佈與實現（main_c1_dist.json）：{S['C1經驗分佈']}", "",
           f"C1 對候選一（同顆配對）：年化差中位 {_p(c1['vs_cand1_d_cagr_med'])}、回落差中位 {_p(c1['vs_cand1_d_mdd_med'])}；兩項皆好 {c1['vs_cand1_both_pos']:.0f}、皆差 {c1['vs_cand1_both_neg']:.0f}", "",
           f"候選二買到的 K4 值（營飆排名 cells.csv）：排名版平均 {k4['buy_K4_mean_ranked']:.4f} vs 抽籤 {k4['buy_K4_mean_lottery']:.4f}", "",
           "分年報酬（主窗逐年，yYYYY 欄）見 main_cells.csv；早年段 2012～2014 分年待 PREREGV 同批。", "",
           "讀法（登錄沒寫、本件定）：C1 的 p 與觸發根分開抽；逐訊號列抽；觸發根用有效 K 棒計；另一條 rng ＝ default_rng([1000＋r, 1])；"
           "「C1 ≈ 候選一」＝ 同顆配對兩項皆好 ＜ 190 且皆差 ＜ 190。", ""]
    open(os.path.join(OUT_, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Ls) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["main"])
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=OUT)
    main(ap.parse_args())
