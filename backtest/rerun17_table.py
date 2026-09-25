# -*- coding: utf-8 -*-
"""rerun17 彙總：seeds_*.csv ⇒ resultsN17/rerun17.csv（17 列）＋ rerun17_seeds.csv（逐種子）。

新判準標籤（寫死、只描述；⛔ 不是判過／判不過）：
  條件一 年化中位 ＞ 0050 同窗年化（嚴格）
  條件二 比值（年化中位 ÷ |回落中位|）≥ 0050 同窗比值（未捨入）
  兩條都成立＝合格；只條件一＝另列；條件一不成立＝不合格
  合格而回落比 0050 深 ⇒ 另給「回落比 0050 深 x 點、報酬多 y 點」
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

from . import rerun17 as RR

RT = dict(float_precision="round_trip")


def label(c, m, bc, bm):
    ratio = c / abs(m); bratio = bc / abs(bm)
    k1 = c > bc; k2 = ratio >= bratio
    lab = "合格" if (k1 and k2) else ("另列" if k1 else "不合格")
    extra = ""
    if lab == "合格" and m < bm:
        extra = f"回落比 0050 深 {(bm - m) * 100:.2f} 點、報酬多 {(c - bc) * 100:.2f} 點"
    return lab, ratio, extra


def src_value(sp, t):
    """原件出處檔的未捨入值（round_trip 讀）。⚠ table219.csv 只存 16 位有效數字 ⇒ 與原件可差 1 ulp，逐位元要對出處檔。"""
    H = RR.HERE
    if sp["fam"] == "P10":
        p = pd.read_csv(os.path.join(H, "results13", "portfolio.csv"), **RT)
        q = p[(p["set"] == "AND") & (p["regime"] == sp["reg"]) & (p["N"] == sp["N"]) & (p["rule"] == sp["rule"])].iloc[0]
        return q["cagr"], q["mdd"], "results13/portfolio.csv"
    if sp["fam"] == "P1":
        p = pd.read_csv(os.path.join(H, "resultsp1", "portfolio.csv"), **RT)
        d = np.inf if sp["d"] is None else float(sp["d"])
        m = (p["set"] == "AND") & (p["N"] == sp["N"]) & (p["d"] == d) & ((p["rule"] == sp["pick"]) if sp["pick"] else p["rule"].isna())
        q = p[m].iloc[0]
        return q["cagr"], q["mdd"], "resultsp1/portfolio.csv"
    if sp["fam"] == "P3B":
        p = pd.read_csv(os.path.join(H, "resultsp3", "summary.csv"), comment="#", **RT)
        q = p[(p["N"] == sp["N"]) & (p["d"] == float(sp["d"])) & (p["rule"] == sp["pick"])].iloc[0]
        return q["B_cagr_med"], q["B_mdd_med"], "resultsp3/summary.csv（B_*_med）"
    if sp["fam"] == "P14":
        p = pd.read_csv(os.path.join(H, "resultsp14", "w_summary.csv"), **RT)
        q = p[p["w"] == 0.5].iloc[0]
        return q["cagr_med"], q["mdd_med"], "resultsp14/w_summary.csv"
    return t["年化"], t["回落"], "resultsN219/table219.csv（P17 交件值）"


def med(df, cid, stage):
    g = df[(df["cell"] == cid) & (df["stage"] == stage)]
    if g.empty:
        return None
    return {"cagr": float(g["cagr"].median()), "mdd": float(g["mdd"].median()), "vol": float(g["vol"].median()), "n": len(g),
            "first_min": int(g["first"].min()), "first_max": int(g["first"].max())}


def build(out, log):
    fs = sorted(glob.glob(os.path.join(out, "seeds_*.csv")))
    df = pd.concat([pd.read_csv(f, dtype={"eq_sha": str}, **RT) for f in fs], ignore_index=True)
    df.to_csv(os.path.join(out, "rerun17_seeds.csv"), index=False)
    t219 = pd.read_csv(os.path.join(RR.HERE, "resultsN219", "table219.csv"), **RT)
    mt = json.load(open(os.path.join(out, "meta_main.json"), encoding="utf-8"))
    bw = mt["bench_win"]
    anchor_ok = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    wo = {}
    for f in glob.glob(os.path.join(out, "meta_winonly*.json")) + glob.glob(os.path.join(out, "meta_repro*.json")):
        m = json.load(open(f, encoding="utf-8")); wo[os.path.basename(f)] = m["bench_win"]
    b_c, b_m, b_v = bw["cagr"], bw["mdd"], bw["vol"]
    rows = []
    for cid, tier, fam, cell, sp in RR.CELLS:
        key_f = RR.T219_FAM[fam]; key_c = RR.T219_CELL.get(cid, cell)
        t = t219[(t219["族"] == key_f) & (t219["格"] == key_c)]
        if len(t) != 1:
            raise SystemExit(f"⛔ table219 找不到唯一列：{key_f}｜{key_c}（{len(t)} 列）")
        t = t.iloc[0]
        p12 = sp["fam"] in ("P14", "P17")
        rep = med(df, cid, "repro")
        win = rep if p12 else med(df, cid, "winonly")
        mn = med(df, cid, "main")
        do = None if p12 else med(df, cid, "dataonly")
        row = {"編號": cid, "層": tier, "族": fam, "格": cell,
               "原交件_年化": t["年化"], "原交件_回落": t["回落"], "原交件_錨年化": t["錨年化"], "原交件_錨回落": t["錨回落"],
               "原交件_標籤219": t["新判準標籤"]}
        sc, sm, srcn = src_value(sp, t)
        if rep:
            row.update({"重現_年化": rep["cagr"], "重現_回落": rep["mdd"], "重現_年化波動": rep["vol"],
                        "重現_逐位元_對出處檔": repr(float(rep["cagr"])) == repr(float(sc)) and repr(float(rep["mdd"])) == repr(float(sm)), "重現_出處檔": srcn,
                        "重現_差_對219_年化": rep["cagr"] - t["年化"], "重現_差_對219_回落": rep["mdd"] - t["回落"]})
        if win:
            lab, ratio, _ = label(win["cagr"], win["mdd"], b_c, b_m)
            row.update({"只換窗_年化": win["cagr"], "只換窗_回落": win["mdd"], "只換窗_比值": ratio, "只換窗_年化波動": win["vol"],
                        "只換窗_標籤": lab})
        if do:
            row.update({"只換資料_年化": do["cagr"], "只換資料_回落": do["mdd"], "只換資料_年化波動": do["vol"]})
        if mn:
            lab, ratio, extra = label(mn["cagr"], mn["mdd"], b_c, b_m)
            row.update({"主窗_年化": mn["cagr"], "主窗_回落": mn["mdd"], "主窗_比值": ratio, "主窗_年化波動": mn["vol"],
                        "主窗_年化÷波動": mn["cagr"] / mn["vol"], "主窗_標籤": lab, "主窗_深淺註": extra,
                        "主窗_條件一": mn["cagr"] > b_c, "主窗_條件二": ratio >= b_c / abs(b_m),
                        "主窗_年化差pp": (mn["cagr"] - b_c) * 100, "主窗_回落差pp（負＝比0050深）": (mn["mdd"] - b_m) * 100,
                        "主窗_first": f"{mn['first_min']}～{mn['first_max']}", "種子數": mn["n"]})
        l219, lw, lm = row.get("原交件_標籤219"), row.get("只換窗_標籤"), row.get("主窗_標籤")
        if lm is not None:
            src = []
            if l219 != lw:
                src.append("換窗（含改用主窗 0050 錨）" if not p12 else "—")
            if lw != lm:
                src.append("換資料")
            row["標籤變動"] = "無" if l219 == lm else f"{l219} → {lm}"
            row["變動來源"] = "、".join(src) if src else ("—" if l219 == lm else "來回抵銷")
        row.update({"錨_年化": b_c, "錨_回落": b_m, "錨_比值": b_c / abs(b_m), "錨_年化波動": b_v, "錨_年化÷波動": b_c / b_v, "錨_逐位元": anchor_ok})
        rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(out, "rerun17.csv"), index=False)
    log(f"[table] rerun17.csv {len(T)} 列；0050 錨逐位元 {anchor_ok}；中間版 0050：{wo}")
    cols = ["編號", "族", "格", "原交件_年化", "原交件_回落", "重現_逐位元_對出處檔", "主窗_年化", "主窗_回落", "主窗_比值", "主窗_年化波動", "主窗_年化÷波動", "原交件_標籤219", "只換窗_標籤", "主窗_標籤", "變動來源"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        log(T[[c for c in cols if c in T]].to_string(index=False))
    return T
