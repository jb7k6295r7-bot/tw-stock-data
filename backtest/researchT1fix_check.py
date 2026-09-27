# -*- coding: utf-8 -*-
"""researchT1fix 的獨立查核（⛔ 不 import researchT1fix）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchT1fix_check.py [--n 2]

① fixture：共用函式 rerun17.t1_censor(AND) ＝ researchYear1M.and_censor(AND) 逐位元（同一份 and_signals、同快照）
② 自己判「資料尾截斷」（用 load_bars 的 idx／next_bad，判法自己寫、向量化）⇒ 補回列集合 ＝ t1_censor 的補回列；
   列出主窗（t−1 閘訊號、#13 訊號）xpos＜0 卻沒補的列與原因（解釋與 audit_trunc 327／74 的差）
③ 自己墊價格、自己組 T1 訊號、自己算停止交易股、自己呼叫引擎跑 #1、#16、#13 的 T1 版前 n 顆 ⇒ 對 seeds.csv.gz 逐位元
④ 從 seeds.csv.gz 自己算各格各版本中位、比值、標籤、差、翻、對營飆 v1 配對數 ⇒ 對 cells.csv；閘門自己再比一次（off 對原件檔、滑價 sf 對 resultsSlip）
⇒ check.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import research11 as R

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsT1fix")
C50, R50 = 0.24020209886370614, 0.7073712681980713
RP = dict(float_precision="round_trip")


def lab(c, m):
    return "合格" if (c > C50 and c / abs(m) >= R50) else ("另列" if c > C50 else "不合格")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=2); a = ap.parse_args()
    errs = []; info = {}
    cal = D.load_calendar(); ncal = len(cal); w0, w1 = RR.win_bounds(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    AND = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), dtype={"sid": str})
    # ①
    from backtest import researchYear1M as Y
    A1, c1 = RR.t1_censor(AND, cal, uni, lambda x: None)
    A2, c2 = Y.and_censor(AND, cal, uni, lambda x: None)
    same = A1.columns.equals(A2.columns) and A1.index.equals(A2.index) and all(
        A1[c].dtype == A2[c].dtype and A1[c].map(repr).tolist() == A2[c].map(repr).tolist() for c in A1.columns) and \
        json.dumps(c1, ensure_ascii=False) == json.dumps(c2, ensure_ascii=False)
    info["① t1_censor ＝ Year1M.and_censor"] = bool(same)
    if not same:
        errs.append("① fixture 不同")
    # ② 自己判
    own = {}
    why_rows = []
    bars = {}
    for H in (60, 120):
        cand = AND[AND[f"xpos_H{H}"] < 0]
        keep = []
        for i, s, k, pos in zip(cand.index, cand["sid"], cand["k"].astype(int), cand["pos"].astype(int)):
            if s not in bars:
                B = R.load_bars(s, uni.get(s, "twse"), cal)
                bars[s] = None if B is None else (np.asarray(B["idx"]), np.asarray(B["next_bad"]), np.asarray(B["o"], float), np.asarray(B["c"], float))
            b = bars[s]
            if b is None:
                why = "沒有 K 棒"
            else:
                idx, nb, o, c = b; n = len(idx)
                exit_bar = k + H                         # 進場 k＋1、持有 H 根 ⇒ 出場根 k＋H
                if idx[k] != pos:
                    why = "訊號根對不上"
                elif exit_bar <= n - 1:
                    why = "不是資料尾（出場根在資料內）"
                elif nb[max(0, k - 20)] < n:
                    why = "k−20 之後有壞根"
                elif idx[-1] != ncal - 1:
                    why = "最後一根不是日曆最後一天（下市／停牌）"
                else:
                    why = "補"
                    keep.append((i, c[-1] / o[k + 1] - 1.0))
            why_rows.append((H, i, s, int(AND.at[i, "entry_pos"]), why))
        own[H] = dict(keep)
        tgt = A1.index[(A1[f"xpos_H{H}"] == ncal) & (AND[f"xpos_H{H}"] < 0)]
        if set(own[H]) != set(tgt) or any(repr(float(A1.at[i, f"g_H{H}"])) != repr(float(g)) for i, g in own[H].items()):
            errs.append(f"② H{H} 補回列不同：自己 {len(own[H])} vs t1_censor {len(tgt)}")
    W = pd.DataFrame(why_rows, columns=["H", "i", "sid", "entry_pos", "why"])
    bench = RR.load_bench(cal); reg = RR.regime_mask(bench)
    e_all = AND["entry_pos"].to_numpy()
    in_t1 = set(AND.index[(e_all >= w0) & (e_all <= w1) & reg[e_all - 1]])
    in_13 = set(AND.index[(e_all >= w0) & (e_all <= w1)])
    for nm, S_, H in (("t−1 閘 H120", in_t1, 120), ("t−1 閘 H60", in_t1, 60), ("#13 H60", in_13, 60)):
        w = W[(W["H"] == H) & W["i"].isin(S_)]
        info[f"② 主窗 {nm}：xpos＜0 原因"] = w["why"].value_counts().to_dict()
        info[f"② 主窗 {nm}：沒補的尾端列（進場日＞2026-03）"] = [(r.sid, str(cal[r.entry_pos].date()), r.why) for r in w.itertuples()
                                                        if r.why != "補" and cal[r.entry_pos] >= pd.Timestamp("2026-03-01")]
    # ③ 自己跑引擎
    closes, opens = RR.load_prices(set(AND["sid"]), cal, uni, "branch")
    cp = {s: np.append(v, v[-1]).astype(v.dtype) for s, v in closes.items()}
    op = {s: np.append(v, np.nan).astype(v.dtype) for s, v in opens.items()}
    AT = AND.copy()
    for H in (60, 120):
        for i, g in own[H].items():
            AT.at[i, f"xpos_H{H}"] = ncal; AT.at[i, f"g_H{H}"] = g
    SF = {}
    for s in sorted(closes):
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        v = np.flatnonzero(np.isfinite(st.df["close"].to_numpy(float)))
        if len(v) and v[-1] < w1:
            SF[s] = int(v[-1])
    info["③ 停止交易股（自算）"] = len(SF)
    e = AT["entry_pos"].to_numpy()
    sig1 = AT[(e >= w0) & (e <= w1) & reg[e - 1]]
    sig13 = AT[(e >= w0) & (e <= w1)]
    SD = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, **RP)
    for key, sig, rule, N, seed0, kw in (("c1", sig1, "H120", 10, 1000, {}), ("c16", sig1, "H60", 20, 1000, {}),
                                        ("c13", sig13, "H60", 20, 7000, dict(log=[], d_max=None, pick="relvol", queue_days=0))):
        for r in range(a.n):
            o = R.simulate_mtm(sig, rule, N, np.random.default_rng(seed0 + r), cp, op, ncal + 1, return_equity=True, stop_force=SF, **kw)
            eq = np.asarray(o["equity"], float)
            c, m, _ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
            ref = SD[(SD["key"] == key) & (SD["var"] == "t1") & (SD["r"] == r)].iloc[0]
            if repr(float(c)) != repr(float(ref["cagr"])) or repr(float(m)) != repr(float(ref["mdd"])) or \
                    hashlib.sha256(eq.tobytes()).hexdigest()[:16] != str(ref["eq_sha"]):
                errs.append(f"③ {key} r{r}：自己 {c}／{m} vs 檔 {ref['cagr']}／{ref['mdd']}")
    info["③ 引擎重跑（每格顆數）"] = a.n
    # ④ 彙總
    TB = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP).set_index("key")
    base = SD[(SD["key"] == "c1") & (SD["var"] == "t1")].set_index("r").sort_index()
    for key, row in TB.iterrows():
        for v in ("off", "sf", "t1"):
            g = SD[(SD["key"] == key) & (SD["var"] == v)]
            if g.empty:
                continue
            c, m = float(g["cagr"].median()), float(g["mdd"].median())
            if abs(c - row[f"{v}_年化"]) > 1e-15 or abs(m - row[f"{v}_回落"]) > 1e-15 or lab(c, m) != row[f"{v}_標籤"]:
                errs.append(f"④ {key} {v}")
        t = SD[(SD["key"] == key) & (SD["var"] == "t1")]
        c, m = float(t["cagr"].median()), float(t["mdd"].median())
        if abs((c - row["原件_年化"]) * 100 - row["差_年化pt"]) > 1e-9 or ((lab(c, m) == row["原件_標籤"]) != (row["翻"] == "無")):
            errs.append(f"④ {key} 差／翻")
        if isinstance(row.get("T1_對營飆v1"), str):
            x = t.set_index("r").sort_index().loc[base.index]
            npos = int(((x["cagr"] > base["cagr"]) & (x["mdd"] > base["mdd"])).sum()); nneg = int(((x["cagr"] < base["cagr"]) & (x["mdd"] < base["mdd"])).sum())
            if npos != row["T1_對營飆v1_兩項皆正"] or nneg != row["T1_對營飆v1_兩項皆負"]:
                errs.append(f"④ {key} 配對")
    # 原件數字對交件檔（off 版）
    orig_off = {"c1": ("regime_t1", 1), "c16": ("regime_t1", 16)}
    r1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "cells.csv"), **RP).set_index("編號")
    for key, (_, cid) in orig_off.items():
        g = SD[(SD["key"] == key) & (SD["var"] == "off")]
        if repr(float(g["cagr"].median())) != repr(float(r1.at[cid, "t1_年化"])) or repr(float(g["mdd"].median())) != repr(float(r1.at[cid, "t1_回落"])):
            errs.append(f"④ {key} off 中位 ≠ regime_t1 cells")
    for key, f, arm in (("time_NH_40", "resultsYfTime/cells.csv", "NH_40"), ("stop_M50", "resultsYfStop/body_cells.csv", "M50"), ("le_S1", "resultsListExit/cells.csv", "S1")):
        t = pd.read_csv(os.path.join(HERE, f), **RP).set_index("arm")
        g = SD[(SD["key"] == key) & (SD["var"] == "off")]
        if repr(float(g["cagr"].median())) != repr(float(t.at[arm, "cagr_med"])) or repr(float(g["mdd"].median())) != repr(float(t.at[arm, "mdd_med"])):
            errs.append(f"④ {key} off 中位 ≠ {f}")
    ref = pd.read_csv(os.path.join(HERE, "resultsSlip", "seeds_main.csv.gz"), dtype={"eq_sha": str}, **RP)
    for key, cell, arm in (("slip1_real", 1, "現實版（C1 0.3%＋C2 50 萬＋C3＋C4）"), ("slip13_real", 13, "現實版（C1 0.3%＋C2 50 萬＋C3＋C4）"),
                           ("slip13_c5", 13, "現實版＋C5 低消 20 元")):
        g = SD[(SD["key"] == key) & (SD["var"] == "sf")].set_index("r")
        rf = ref[(ref["cell"] == cell) & (ref["arm"] == arm)].set_index("r")
        nd = sum(str(g.at[r, "eq_sha"]) != str(rf.at[r, "eq_sha"]) or repr(float(g.at[r, "cagr"])) != repr(float(rf.at[r, "cagr"])) for r in rf.index)
        info[f"④ 滑價 {key} sf ＝ resultsSlip（比對顆數／不同）"] = [len(rf), nd]
        if nd:
            errs.append(f"④ 滑價 {key} ≠ resultsSlip")
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False, default=str))
    for e_ in errs[:20]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()
