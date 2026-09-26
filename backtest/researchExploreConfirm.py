# -*- coding: utf-8 -*-
"""PREREG探索批【確認段 A】——回測線落地（登錄 seq3 sha 22ee7941c61f8757 §一、§二、§五；N_組合 ＋5，5 條一次跑完）。

    python3 backtest/researchExploreConfirm.py --part gate_explore|gate_w1|gate_elig|A|report [--procs 3]

⛔ 確認窗 B（2012-06～2014-12，等早年資料）不跑；前瞻 C 不在本程式。
對象（登錄 §四 寫死、探索段 clues.csv）：F09+F17、F11+F13、F09+F13、F06+F11、F04+F18；前 10%、兩兩等權、200 顆種子 102000＋r。

═══ 確認窗 A（登錄 §一，逐字）═══
  判讀窗 2023-01-03 ～ 2026-08-24；「確認窗 A 從 2023-01 重新起跑」⇒ 訊號只取量測日 ≥ 2023-01-01（首個 2023-01-03 ⇒ 2023-01-04 進場），
  ⛔ 不帶 2022 以前進場的部位；特徵回看用到 2022 以前的價格（登錄：「那不是 A 的報酬」）
  量測日 ＝ W1 同一組（每月第一個交易日，至 2026-03-31 ⇒ 末個 2026-03-02）；引擎跑完整條日曆（快照最後一日 2026-09-24）、讀窗 [w0, w1]
     ＝ W1 讀全窗的同一條路（P12.win_read；窗尾未到期部位按 2026-08-24 收盤計值）
  資料 ＝ edc6f8002f 快照、檔內還原因子（同 W1；⛔ 探索段的 as-of 2022-12-30 只為切點，A 不用）；官方下市日全收（同 W1）
  日曆：calendar_twse.csv（快照最後一日 2026-09-24；程式斷言沒有 2026-09-25）
═══ 判定（登錄 §五；使用者判準 seq141）═══
  Q 合格：A ＞ A50 ∧ A÷|D| ≥ A50÷|D50|；R 另列：A ＞ A50 ∧ 比值 ＜ 0050；F 不合格：A ≤ A50（0050 同窗自算、未捨入）
  S0（signal ALL＋pick=None，1,000 顆，同樣從 2023-01 重新起跑）⇒ p ＝ 逐顆種子落入 Q 的比例；結論句後附「純運氣預期約 5p 條合格」；p ≥ 5% ⇒ 句前 ⚠
  對照（⛔ 不計 N）：W1ref ＝ 門檻B 同樣從 2023-01 重新起跑 200 顆；另附描述 W1full ＝ W1 原跑法（2017 起跑）讀窗 A 的 200 顆
讀法：探索段 X1～X8 全部沿用（同一支 researchExplore 的函式）；X3、X4 在 A 用不到
閘門：gate_explore ＝ 同程式在探索窗重跑 5 條線索 ⇒ 與 resultsExplore/seeds.csv 逐欄相同；gate_w1 ＝ W1 前 20 顆全期逐位元重現 resultsAFC/w1_1000.csv；
      gate_elig ＝ A 的 eligible ＝ AFC 面板同量測日 eligible；0050 錨在窗 A 自算（查核程式獨立重算）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchExplore as RE                          # ⭐ 特徵、挑選、訊號、引擎呼叫全用探索段同一支函式

D, H2, P4F, P7, P12, RP4, R13, T = RE.D, RE.H2, RE.P4F, RE.P7, RE.P12, RE.RP4, RE.R13, RE.T
CLUES = ["F09+F17", "F11+F13", "F09+F13", "F06+F11", "F04+F18"]
WIN = {"explore": {"cut": RE.CUT, "start": "2017-01-01", "w0": "2017-03-02", "w1": "2022-12-30", "asof": True, "pos_end": None},
       "A": {"cut": None, "start": "2023-01-01", "w0": "2023-01-03", "w1": "2026-08-24", "asof": False, "pos_end": "2026-03-31"}}
OUT = "backtest/resultsExplore/confirmA"
N_S0 = 1000


def prep(win: str, procs: int, log=print, signals=("cells", "S0", "W1ref")):
    W = WIN[win]
    D.load_adj = RE.load_adj_asof if W["asof"] else RE._ORIG_LOAD_ADJ
    RE.START = W["start"]                              # sig_explore 讀模組常數 START
    cal_full = D.load_calendar()
    assert pd.Timestamp("2026-09-25") not in cal_full, "⛔ 日曆含 2026-09-25（興櫃假日檔）"
    assert cal_full[-1] == pd.Timestamp("2026-09-24"), f"⛔ 快照日曆尾 {cal_full[-1]}"
    cal = cal_full[cal_full <= W["cut"]] if W["cut"] is not None else cal_full
    ncal = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W["w0"]))); w1 = int(cal.searchsorted(pd.Timestamp(W["w1"])))
    assert str(cal[w0].date()) == W["w0"] and str(cal[w1].date()) == W["w1"]
    marks = P12.month_marks(cal, w0, w1)
    RE._G["cal"] = cal; RE._G["leak"] = False
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = H2.UG.gate3(stocks)
    U = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    positions = P4F.measurement_days(cal, W["start"], W["pos_end"])
    panel, _ = RP4.build_panel(cal, U, positions, procs=procs, mp_check=False, log=lambda s: None)
    el = panel[panel["eligible"].astype(bool)]
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens = {}, {}
    for s in sorted(set(panel["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        closes[s] = st.df["close"].ffill().to_numpy(float); opens[s] = st.df["open"].to_numpy(float)
    c50 = closes["0050"]
    a50, d50 = R13.window_stats(c50 / c50[w0], w0, w1 + 1, w0, w1 + 1)
    log(f"[{win}] 日曆 {cal[0].date()}～{cal[-1].date()}（{ncal}）｜窗 {cal[w0].date()}～{cal[w1].date()}｜量測日 {len(positions)}（{cal[positions[0]].date()}～{cal[positions[-1]].date()}）｜eligible {len(el):,}｜0050 {a50:+.4%}／{d50:+.4%}／{a50 / abs(d50):.4f}")
    pos_of = {d: i for i, d in enumerate(cal)}
    el = el.assign(pos=el["measure_date"].map(pos_of).astype(int))
    jobs = [(s, uni.get(s, "twse"), g["pos"].to_numpy(int)) for s, g in el.groupby("stock_id", sort=True)]
    if procs > 1:
        with Pool(procs) as pool:
            fr = [r for rs in pool.map(RE.feat_worker, jobs, chunksize=8) for r in rs]
    else:
        fr = [r for j in jobs for r in RE.feat_worker(j)]
    F = pd.DataFrame(fr)
    feat = F.merge(RE.revenue_feats(cal, F[["pos", "sid"]]), on=["pos", "sid"], how="left", validate="1:1")
    feat["measure_date"] = [str(cal[p].date()) for p in feat["pos"]]
    feat = feat[["measure_date", "pos", "sid", "rev_period"] + RE.CONDS].sort_values(["pos", "sid"]).reset_index(drop=True)
    sigA, n_base, n_tail = RE.sig_explore(panel, cal, closes, opens, "ALL")
    sel, cstat = RE.select_cells(feat)
    key = sigA.assign(pos=sigA["entry_pos"] - 1).set_index(["pos", "sid"])
    sigs, cst = {}, []
    for c in RE.CELLS:
        nm = RE.cell_name(c)
        if nm not in CLUES:
            continue
        s = sel[c]
        m = key.index.isin(pd.MultiIndex.from_arrays([s["pos"].astype(int), s["sid"]]))
        sigs[nm] = sigA[m].reset_index(drop=True)
        st_ = np.array(cstat[c], float)
        cst.append({"cell": nm, "sig_rows": len(sigs[nm]), "selected": len(s), "dropped_entry_open": int(len(s) - m.sum()),
                    "avg_eligible": float(st_[:, 1].mean()), "avg_valid": float(st_[:, 2].mean()), "avg_k": float(st_[:, 3].mean())})
    sigs["S0"] = sigA
    sigB, _, _ = RE.sig_explore(panel, cal, closes, opens, "B")
    sigs["W1ref"] = sigB
    log(f"[{win}] 候選母體 ALL {len(sigA):,}（尾段 {n_tail}）｜門檻B {len(sigB):,}｜" + "；".join(f"{r['cell']} 訊號 {r['sig_rows']:,}" for r in cst))
    trad = T.build(set(sigA["sid"]), cal)
    off = T.load_official()
    if W["cut"] is not None:
        off = {k: v for k, v in off.items() if v <= W["cut"]}
    dl = T.delist_status(trad, cal, official=off)
    RE._S.update(sigs=sigs, closes=closes, opens=opens, ncal=ncal, trad=trad, dl=dl, w0=w0, w1=w1, marks=marks)
    return {"a50": a50, "d50": d50, "feat": feat, "cst": pd.DataFrame(cst), "cal": cal, "panel": panel, "w0": w0, "w1": w1}


def run(keys_n, procs):
    tasks = [(k, RE.SEED0 + r) for k, n in keys_n for r in range(n)]
    if procs > 1:
        with Pool(procs) as pool:
            return pd.DataFrame(pool.map(RE.run_one, tasks, chunksize=5))
    return pd.DataFrame([RE.run_one(t) for t in tasks])


def gate_explore(procs, log):
    prep("explore", procs, log)
    got = run([(c, RE.REPS) for c in CLUES], procs)
    p = os.path.join(OUT, "_gate_explore.csv"); got.to_csv(p, index=False)
    a = pd.read_csv(p, dtype=str); os.remove(p)
    ref = pd.read_csv("backtest/resultsExplore/seeds.csv", dtype=str)
    ref = ref[ref["cell"].isin(CLUES)]
    m = a.merge(ref, on=["cell", "seed"], suffixes=("", "_r"))
    cols = [c for c in a.columns if c not in ("cell", "seed")]
    same = np.all([(m[c] == m[c + "_r"]).to_numpy() for c in cols], axis=0)
    ok = len(m) == 1000 and bool(same.all())
    log(f"[閘 explore] 5 條線索 × 200 顆在探索窗重跑 ⇒ 與 resultsExplore/seeds.csv 逐欄相同 {int(same.sum())}／{len(m)}（含權益曲線 sha1）{'✅' if ok else '⛔'}")
    return ok


def gate_w1(log):
    D.load_adj = RE._ORIG_LOAD_ADJ
    cal = D.load_calendar(); ncal = len(cal)
    panel = P4F.read_panel("backtest/resultsAFC/panel.csv.gz")
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens = {}, {}
    for s in sorted(set(panel["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        closes[s] = st.df["close"].ffill().to_numpy(float); opens[s] = st.df["open"].to_numpy(float)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
    sig = sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    w0, w1 = P12.win_bounds(cal, "全窗")
    RE._S.update(sigs={"W1": sig}, closes=closes, opens=opens, ncal=ncal, trad=trad, dl=dl, w0=w0, w1=w1, marks=P12.month_marks(cal, w0, w1))
    ref = pd.read_csv("backtest/resultsAFC/w1_1000.csv", float_precision="round_trip").set_index("seed")
    n_ok = sum(int((o := RE.run_one(("W1", 102000 + r)))["cagr"] == ref.loc[o["seed"], "cagr"] and o["mdd"] == ref.loc[o["seed"], "mdd"]) for r in range(20))
    # 描述臂 W1full：同一條 W1 原跑法（2017 起跑、全期）讀窗 A
    a0 = int(cal.searchsorted(pd.Timestamp(WIN["A"]["w0"]))); a1 = int(cal.searchsorted(pd.Timestamp(WIN["A"]["w1"])))
    RE._S.update(w0=a0, w1=a1, marks=P12.month_marks(cal, a0, a1))
    wf = run([("W1", RE.REPS)], 1).assign(cell="W1full")
    wf.to_csv(os.path.join(OUT, "_w1full_seeds.csv"), index=False)
    log(f"[閘 w1] W1 前 20 顆全期重現 resultsAFC/w1_1000.csv ⇒ 逐位元相同 {n_ok}／20 {'✅' if n_ok == 20 else '⛔'}｜描述 W1full 讀窗 A 200 顆已存")
    return n_ok == 20


def gate_elig(procs, log):
    P = prep("A", procs, log)
    F = P["feat"]
    Q = pd.read_csv("backtest/resultsAFC/panel.csv.gz", dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "eligible"])
    Q = Q[(Q["measure_date"] >= "2023-01-01") & Q["eligible"].astype(bool)]
    a = set(zip(F["measure_date"], F["sid"])); b = set(zip(Q["measure_date"].str[:10], Q["stock_id"]))
    log(f"[閘 elig] 窗 A 重建 eligible {len(a):,}｜AFC 面板同量測日 {len(b):,}｜只在前者 {len(a - b)}｜只在後者 {len(b - a)} ⇒ {'✅' if a == b else '⛔'}")
    return a == b


def part_A(procs, log):
    P = prep("A", procs, log)
    Q = pd.read_csv("backtest/resultsAFC/panel.csv.gz", dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "eligible"])
    Q = Q[(Q["measure_date"] >= "2023-01-01") & Q["eligible"].astype(bool)]
    ea = set(zip(P["feat"]["measure_date"], P["feat"]["sid"])); eb = set(zip(Q["measure_date"].str[:10], Q["stock_id"]))
    P["elig"] = {"重建": len(ea), "AFC面板": len(eb), "只在重建": len(ea - eb), "只在AFC": len(eb - ea), "相同": ea == eb}
    log(f"[閘 elig] 窗 A 重建 eligible {len(ea):,}｜AFC 面板同量測日 {len(eb):,}｜差 {len(ea - eb)}／{len(eb - ea)} ⇒ {'✅' if ea == eb else '⛔'}")
    if ea != eb:
        raise SystemExit("⛔ 窗 A 母體與 W1 面板不同 ⇒ 停")
    P["feat"].to_csv(os.path.join(OUT, "features.csv"), index=False)
    P["cst"].to_csv(os.path.join(OUT, "cand_stats.csv"), index=False)
    S = run([(c, RE.REPS) for c in CLUES] + [("S0", N_S0), ("W1ref", RE.REPS)], procs)
    wf = os.path.join(OUT, "_w1full_seeds.csv")
    if os.path.exists(wf):
        S = pd.concat([S, pd.read_csv(wf, dtype={"cell": str}, float_precision="round_trip")[S.columns]], ignore_index=True)
    S.to_csv(os.path.join(OUT, "seeds.csv"), index=False)
    S = pd.read_csv(os.path.join(OUT, "seeds.csv"), dtype={"cell": str}, float_precision="round_trip")
    a50, d50 = P["a50"], P["d50"]; r50 = a50 / abs(d50)
    s0 = S[S["cell"] == "S0"]
    q0 = (s0["cagr"] > a50) & (s0["cagr"] / s0["mdd"].abs() >= r50)
    p = float(q0.mean())
    EX = pd.read_csv("backtest/resultsExplore/ranking_171.csv", dtype={"cell": str}, float_precision="round_trip").set_index("cell")
    rows = []
    for k in CLUES + ["S0", "W1ref", "W1full"]:
        g = S[S["cell"] == k]
        if not len(g):
            continue
        A, Dd = float(g["cagr"].median()), float(g["mdd"].median()); ratio = A / abs(Dd)
        lab = ("Q" if ratio >= r50 else "R") if A > a50 else "F"
        rows.append({"cell": k, "role": "線索" if k in CLUES else "參照（不計 N）", "n": len(g), "A": A, "D": Dd, "ratio": ratio,
                     "A_p10": float(g["cagr"].quantile(0.1)), "A_p90": float(g["cagr"].quantile(0.9)),
                     "vol_med": float(g["vol"].median()), "ratio_over_vol": A / float(g["vol"].median()),
                     "A_minus_0050": A - a50, "ratio_minus_0050": ratio - r50, "label": lab if k in CLUES else f"（{lab}，參照）",
                     "seeds_Q_frac": float(((g["cagr"] > a50) & (g["cagr"] / g["mdd"].abs() >= r50)).mean()),
                     "explore_A": float(EX.loc[k, "A"]) if k in EX.index else np.nan,
                     "explore_ratio": float(EX.loc[k, "ratio"]) if k in EX.index else np.nan,
                     "explore_label": EX.loc[k, "label"] if k in EX.index else ""})
    C = pd.DataFrame(rows)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    nQ = int((C.loc[C["role"] == "線索", "label"] == "Q").sum())
    summ = {"登錄": "PREREG探索批 seq3 sha 22ee7941c61f8757 確認段 A（N_組合 ＋5）；確認窗 B 未跑（等早年資料）",
            "窗A": [WIN["A"]["w0"], WIN["A"]["w1"]], "起跑": "量測日 ≥ 2023-01-01（重新起跑、不帶倉）", "快照日曆尾": "2026-09-24（無 2026-09-25）",
            "0050同窗": {"年化": a50, "回落": d50, "比值": r50},
            "閘_elig": P["elig"],
            "S0": {"n": int(len(s0)), "年化中位": float(s0["cagr"].median()), "回落中位": float(s0["mdd"].median()),
                   "合格比例p（逐顆）": p, "純運氣預期合格條數5p": 5 * p, "p≥5%⇒⚠": bool(p >= 0.05)},
            "線索合格數Q": nQ, "標籤": C.loc[C["role"] == "線索"].set_index("cell")["label"].to_dict()}
    json.dump(summ, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[A] 0050 {a50:+.4%}／{d50:+.4%}／{r50:.4f}｜S0 p {p:.4f}（5p {5 * p:.2f}）｜" + "；".join(f"{r.cell} {r.A:+.2%}／{r.D:+.2%}／{r.ratio:.3f} {r.label}" for r in C.itertuples()))


def part_report(log):
    """REPORT.md：數字一律由 cells.csv／summary.json／run.log 帶出（⛔ 手抄）；結果句照登錄 §五查表。"""
    C = pd.read_csv(os.path.join(OUT, "cells.csv"), dtype={"cell": str}, float_precision="round_trip")
    J = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RL = open(os.path.join(OUT, "run.log"), encoding="utf-8").read()
    z = J["0050同窗"]; p = J["S0"]["合格比例p（逐顆）"]
    pct = lambda x: f"{x * 100:+.2f}%"
    L = ["# PREREG探索批 確認段 A（回測線）", "",
         f"登錄 seq3 sha 22ee7941c61f8757 §五；N_組合 ＋5（5 條一次跑完）。窗 A {J['窗A'][0]}～{J['窗A'][1]}，{J['起跑']}；快照 edc6f8002f，日曆尾 {J['快照日曆尾']}。",
         "⛔ 確認窗 B（2012-06～2014-12）未跑（等早年資料）；前瞻 C 2026-10 起另記。", "",
         "## 閘門", "",
         "| 閘 | 結果 |", "|---|---|"]
    for key in ("[閘 w1]", "[閘 explore]", "[閘 elig]"):
        line = [x for x in RL.splitlines() if x.startswith(key)][-1]
        L.append(f"| {key[1:-1]} | {line[len(key):].strip()} |")
    L += [f"| 0050 錨（窗 A 自算） | 年化 {pct(z['年化'])}、回落 {pct(z['回落'])}、比值 {z['比值']:.4f}（查核程式獨立重算，見 check.log） |", "",
          "## 判定（使用者判準：年化 ＞ 0050 且 比值 ≥ 0050 ⇒ Q；只前者 ⇒ R；年化 ≤ 0050 ⇒ F）", "",
          "| 線索 | 窗 A 年化中位 | 回落中位 | 比值 | 對 0050 年化差 | 窗 A 判定 | 探索窗年化 | 探索窗比值 | 探索窗標籤 | 200 顆中逐顆達 Q 比例 |",
          "|---|---:|---:|---:|---:|:--:|---:|---:|:--:|---:|"]
    cl = C[C["role"] == "線索"]
    for r in cl.itertuples():
        L.append(f"| {r.cell} | {pct(r.A)} | {pct(r.D)} | {r.ratio:.4f} | {r.A_minus_0050 * 100:+.2f}pp | {r.label} | {pct(r.explore_A)} | {r.explore_ratio:.4f} | {r.explore_label} | {r.seeds_Q_frac:.3f} |")
    L += ["", f"0050 同窗：年化 {pct(z['年化'])}、回落 {pct(z['回落'])}、比值 {z['比值']:.4f}。", "", "## 結果句（登錄 §五查表）", ""]
    warn = "⚠ " if J["S0"]["p≥5%⇒⚠"] else ""
    for r in cl.itertuples():
        if r.label == "Q":
            s = f"{r.cell}：確認窗 A 合格（Q）；確認窗 B 未跑 ⇒ 「找到、可以用」待 B。"
        elif r.label == "R":
            s = f"{r.cell}：確認窗 A 另列（R）：賺得比 0050 多，但風險增加得比報酬多（年化 {pct(r.A)}、回落 {pct(r.D)}、比值 {r.ratio:.4f}）。"
        else:
            s = f"{r.cell}：確認窗 A 不合格（F，年化 {pct(r.A)} ≤ 0050 {pct(z['年化'])}）⇒ 探索窗的好成績在沒看過的年份沒有撐住。"
        L.append(f"- {warn}{s}")
    L += ["", f"{warn}5 條線索確認窗 A 合格 {J['線索合格數Q']} 條；純運氣預期約 {5 * p:.2f} 條合格（S0 逐顆合格比例 p ＝ {p:.4f}，1,000 顆）。",
          "⇒ 5 條都不合格（A 窗為 F）⇒ 不論確認窗 B 結果如何，本批 5 條都不能對使用者說「找到、可以用」。", "",
          "## 對照（⛔ 不計 N、只當參照）", "", "| 臂 | 年化中位 | 回落中位 | 比值 | 說明 |", "|---|---:|---:|---:|---|"]
    desc = {"S0": "同母體每月隨機抽 8 檔（signal ALL），1,000 顆，2023-01 重新起跑", "W1ref": "門檻B，2023-01 重新起跑，200 顆",
            "W1full": "門檻B W1 原跑法（2017 起跑、窗頭帶倉）讀窗 A，200 顆（描述）"}
    for r in C[C["role"] != "線索"].itertuples():
        L.append(f"| {r.cell} | {pct(r.A)} | {pct(r.D)} | {r.ratio:.4f} | {desc.get(r.cell, '')} |")
    L += ["", "## 讀法", "",
          "- 探索段 X1～X8 全沿用（同一支 researchExplore 函式；X3、X4 在 A 用不到）。",
          "- 「確認窗 A 從 2023-01 重新起跑」＝ 只取量測日 ≥ 2023-01-01 的訊號、不帶 2022 以前進場的部位；量測日照 W1 同一組（末個 2026-03-02）；窗尾未到期部位按 2026-08-24 收盤計值（同 W1 讀全窗）。",
          "- 窗 A 用快照檔內還原因子（同 W1）；探索段的 as-of 2022-12-30 只為切點。",
          "- 同窗 W1 對照：登錄只寫「同窗 W1」⇒ 重新起跑（W1ref）與原跑法讀窗（W1full）兩臂並列，都是參照、不影響判定。",
          "- S0 合格比例 p ＝ 1,000 顆中逐顆落入 Q 的比例。", "",
          "## 檔案", "", "cells.csv（線索＋參照逐列）｜seeds.csv（逐種子，含權益曲線 sha1）｜summary.json｜features.csv｜cand_stats.csv｜check.log｜run.log"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(chr(10).join(L) + chr(10))
    log("[report] REPORT.md 寫出")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=("gate_explore", "gate_w1", "gate_elig", "A", "report"))
    ap.add_argument("--procs", type=int, default=1)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(s):
        print(s, flush=True); logf.write(s + "\n"); logf.flush()
    t0 = time.time()
    log(f"=== researchExploreConfirm --part {a.part} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）procs={a.procs}")
    ok = {"gate_explore": lambda: gate_explore(a.procs, log), "gate_w1": lambda: gate_w1(log),
          "gate_elig": lambda: gate_elig(a.procs, log), "A": lambda: part_A(a.procs, log) or True, "report": lambda: part_report(log)}[a.part]()
    log(f"結束 {time.time() - t0:.0f}s")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
