# -*- coding: utf-8 -*-
"""PREREG合成分數 描述臂：「同分時舊持股優先」（裁定 seq262 §三：描述臂、不改判定格、N 不加）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchScore_desc [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchScore_desc_check.py

⭐ 只 import researchScore（786147154e），⛔ 不改它；特徵快取 resultsScore/feat_main.pkl、feat_A.pkl
讀法：挑中格（L20｜月換｜N10；resultsScore/summary.json）同一套票、同一個抽籤數（default_rng([20260928, e])）；
      唯一改動：換股日排名鍵由 (−分數, 抽籤數) 改成 (−分數, 舊持股先, 抽籤數) —— 「舊持股」＝ 換股日開盤前仍在簿上的持股（含待賣）
      ⇒ 名單要在模擬過程中決定（舊持股是前一次換股的結果），模擬器 ＝ researchScore.sim_book 同一套規則，只把名單改成當場算
⭐ 停止交易強制出場：開（同原件）；資料尾：換股簿、無固定持有 ⇒ t1_censor 不適用
閘：「舊持股先」關掉時（排名鍵退回原件）⇒ 權益 ＝ researchScore.sim_book 逐位元
輸出 backtest/resultsScore/desc/：cells.csv、summary.json、REPORT.md
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

from . import researchScore as SC

OUT = os.path.join(SC.HERE, "resultsScore", "desc")


def sim_pref(VT, reb, vs, N, P, dl, SF, t0, t1, prefer=True):
    """researchScore.sim_book 同一套；差別只在換股日當場排名（prefer ⇒ 同分時舊持股先）。"""
    ncal = len(next(iter(P.values()))["c"])
    eq = np.ones(ncal); cash = 1.0
    pos = {}; pend = set()
    npos = np.zeros(ncal, np.int16); cashf = np.zeros(ncal); costd = np.zeros(ncal)
    buys = {}; sels = {}; scs = {}
    cnt = {"buy": 0, "sell": 0, "stop_force": 0, "keep_by_tie": 0}
    rebs = set(reb)
    for t in range(t0, t1 + 1):
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt = pos.pop(s)
            cash += u * P[s]["c"][t] - amt * SC.COST; costd[t] += amt * SC.COST; cnt["stop_force"] += 1
            pend.discard(s)
        sel = None
        if t in rebs:
            T = VT[t]
            if len(T):
                sc = SC.score_of(T, vs); sids = sorted(T.index); u_ = SC.tie_u(t, sids)
                held = set(pos)
                key = (lambda s: (-sc[s], 0 if s in held else 1, u_[s])) if prefer else (lambda s: (-sc[s], u_[s]))
                order = sorted(sids, key=key)
                sel = order[:N]; scs[t] = [int(sc[s]) for s in sel]
                if prefer:
                    base = sorted(sids, key=lambda s: (-sc[s], u_[s]))[:N]
                    cnt["keep_by_tie"] += len((set(sel) - set(base)) & held)
            else:
                sel = []
            sels[t] = sel
            pend = (pend | (set(pos) - set(sel))) - set(sel)
        for s in sorted(pend):
            x = P[s]; o_t = x["o"][t]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]
            else:
                continue
            u, amt = pos.pop(s)
            cash += u * px - amt * SC.COST; costd[t] += amt * SC.COST; cnt["sell"] += 1
            pend.discard(s)
        if sel is not None:
            free = N - len(pos)
            new = [s for s in sel if s not in pos][:max(free, 0)]
            nb = 0
            for s in new:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0) or x["up_o"][t]:
                    continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[s] = [amt / o_t, amt]; nb += 1; cnt["buy"] += 1
            buys[t] = nb
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
    eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buys": buys, "cnt": cnt, "sels": sels, "scs": scs}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t00 = time.time()
    SS = json.load(open(os.path.join(SC.OUT, "summary.json"), encoding="utf-8"))
    ck = SS["探索挑格"]["挑中"]; Ls, rb, Ns = ck.split("_"); L = int(Ls[1:]); N = int(Ns[1:])
    rows = []; gate = {}
    for part, win, segs in (("main", SC.MAIN_W, SC.SEG), ("A", SC.EARLY_A, {"早年A": SC.EARLY_A})):
        FT = SC.prep_part(part, a)
        cal = FT["cal"]; t0, t1 = SC.pos_of(cal, win[0]), SC.pos_of(cal, win[1])
        VT = SC.vote_table(FT, L)
        reb = SC.reb_days(cal, t0, t1, rb == "季換")
        SF = SC.R.stop_force_days({s: v["valid"] for s, v in FT["P"].items()}, t1)
        sel, _ = SC.select(VT, reb, SC.SETS["主版"], N)
        ref = SC.sim_book(sel, FT["P"], FT["dl"], SF, t0, t1, "hold", N)
        off = sim_pref(VT, reb, SC.SETS["主版"], N, FT["P"], FT["dl"], SF, t0, t1, prefer=False)
        on = sim_pref(VT, reb, SC.SETS["主版"], N, FT["P"], FT["dl"], SF, t0, t1, prefer=True)
        gate[f"{part}：舊持股先關掉 ＝ researchScore.sim_book（權益逐位元）"] = bool(np.array_equal(ref["eq"], off["eq"]))
        bench = FT["bench"]
        for nm, (x_, y_) in segs.items():
            x, y = SC.pos_of(cal, x_), SC.pos_of(cal, y_)
            b = SC.seg_metrics(bench, x, y)
            rs = [e for e in reb if x <= e <= y]
            for tag, res in (("原件（同分抽籤）", off), ("描述臂（同分舊持股先）", on)):
                c, m, ratio = SC.seg_metrics(res["eq"], x, y)
                yrs = (y + 1 - x) / 245
                rows.append({"段": nm, "版本": tag, "年化": c, "回落": m, "比值": ratio, "標籤": SC.label(c, m, b[0], b[1]),
                             "每年換手": sum(res["buys"].get(e, 0) for e in rs) / N / yrs,
                             "成本／年": float(res["costd"][x:y + 1].sum()) / float(res["eq"][x:y + 1].mean()) / yrs,
                             "平均持股": float(res["npos"][x:y + 1].mean()), "現金比例": float(np.nanmean(res["cashf"][x:y + 1])),
                             "0050年化": b[0], "0050回落": b[1], "同分保住舊股次數": res["cnt"].get("keep_by_tie", 0) if tag.startswith("描述") else 0})
        if part == "main":
            pd.DataFrame([{"e": e, "rank": i + 1, "sid": s} for e, v in on["sels"].items() for i, s in enumerate(v)]).to_csv(os.path.join(OUT, "picks_pref.csv.gz"), index=False)
            np.savez_compressed(os.path.join(OUT, "eq.npz"), on=on["eq"], off=off["eq"], t0=t0, t1=t1)
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    S = {"件": "PREREG合成分數 描述臂：同分舊持股優先（裁定 seq262 §三；不改判定格、N 不加）", "挑中格": ck, "閘": gate, "閘過": all(gate.values()),
         "停止交易強制出場": "開", "秒": round(time.time() - t00)}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cf = T[(T["段"] == "確認")].set_index("版本")
    o_, d_ = cf.loc["原件（同分抽籤）"], cf.loc["描述臂（同分舊持股先）"]
    L_ = ["# PREREG合成分數 描述臂：同分時舊持股優先", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq262 §三（描述臂、⛔ 不改判定格、N 不加）。回測線。⭐ 停止交易強制出場：開。", "",
          f"**結論（描述）：挑中格 {ck} 確認段，同分舊持股先 {d_['年化'] * 100:+.2f}%／{d_['回落'] * 100:+.2f}%（每年換手 {d_['每年換手']:.2f}、成本／年 {d_['成本／年'] * 100:.2f}%）；"
          f"原件同分抽籤 {o_['年化'] * 100:+.2f}%／{o_['回落'] * 100:+.2f}%（換手 {o_['每年換手']:.2f}、成本 {o_['成本／年'] * 100:.2f}%）；0050 {o_['0050年化'] * 100:+.2f}%。判定仍以原件為準（不合格）。**", "",
          "| 段 | 版本 | 年化 | 回落 | 比值 | 對 0050（描述） | 每年換手 | 成本／年 | 平均持股 | 同分保住舊股次數 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in T.to_dict("records"):
        L_.append(f"| {r['段']} | {r['版本']} | {r['年化'] * 100:+.2f}% | {r['回落'] * 100:+.2f}% | {r['比值']:.3f} | {r['標籤']} | {r['每年換手']:.2f} | {r['成本／年'] * 100:.2f}% | {r['平均持股']:.1f} | {r['同分保住舊股次數']} |")
    L_ += ["", f"- 閘：{json.dumps(gate, ensure_ascii=False)}", "- 描述臂 ⛔ 不判、⛔ 不取代判定格；早年 A 段同一套（只上市、early 版面）", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L_) + "\n")
    print(L_[4])
    if not all(gate.values()):
        raise SystemExit("⛔ 閘不過")


if __name__ == "__main__":
    main()
