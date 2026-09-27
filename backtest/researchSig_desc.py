# -*- coding: utf-8 -*-
"""PREREG訊號系統 裁定 seq246 ①：「X 任一」出場版在 E1、E2 確認段的描述補報。
⛔ 看過結果後補報，⛔ 不當判定（E1、E2 判定格已改判「依構造不可判定」、不另挑判定格）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSig_desc.py [--procs 2] [--reps 200]

程式一字不動：import researchSig（2fe5809e9b）的建列、引擎一顆、彙總函式；同一份訊號快取（resultsSig/sig_cache.pkl）、同一份面板（panel_ext）、
同一套引擎設定（營飆 v1 骨架、200 顆、種子 1000＋r）。輸出 resultsSig/desc_anyexit.csv、desc_anyexit.json、desc_anyexit.md
"""
from __future__ import annotations
import argparse, json, os, pickle, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchSig as RS

TAG = "看過結果後補報，⛔ 不當判定"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    OUT = RS.OUT
    log = lambda x: print(x, flush=True)
    RS.RR.use_snapshot()
    cal = RS.D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
    s0, s1 = (int(cal.searchsorted(pd.Timestamp(v))) for v in RS.SEG["確認"])
    sids, elig, mk = RS.stock_universe(cal, RS.PANEL, os.path.join(RS.RV.H2.H2D, "meta", "stocks.csv"))
    SIG, VAL = pickle.load(open(os.path.join(OUT, "sig_cache.pkl"), "rb"))
    cz, oz = RS.RR.load_prices(sorted(SIG), cal, mk, "branch")
    bench = RS.RR.load_bench(cal); b50 = RS.RR.bench_row(cal, bench, s0, s1 + 1)
    CELLS = {}
    RS._G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS, VAL=VAL)
    keys = []; nrow = {}
    for E in ("E1", "E2"):
        R, drop, byc = RS.build_rows(SIG, elig, mon, E, "ANY", s0, s1); R = R.reset_index(drop=True)
        SD = pd.DataFrame({"ep": [RS.L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
        sig, kw, reason = RS.make_cell(R, SD, s1, "無", "無", cz, oz)
        k = ("確認", E, "ANY", "無", "無"); CELLS[k] = (sig, kw, reason, None); keys.append(k); nrow[E] = int(len(R))
    t0 = time.time()
    res = RS.run_cells_g(keys, s0, s1, a.reps, a.procs, "確認段 X 任一（描述補報）", log)
    rows = []; out = {"性質": TAG, "依據": "裁定 seq246 ①", "0050同段": b50, "格": {}}
    for k in keys:
        c = RS.agg(res[k], b50)
        yrs = c["每年交易"]
        d = {"E": k[1], "出場": "X 任一", "年化中位": c["cagr_med"], "回落中位": c["mdd_med"], "比值": c["ratio"],
             "每顆交易筆": c["交易筆_每顆平均"], "每年交易": yrs, "段尾未出場_每顆": c["段尾未出場_每顆"], "勝率": c["勝率"],
             "持有天數_中位": c["持有天數_中位"], "持有天數_平均": c["持有天數_平均"], "出場原因占比": c["出場原因占比"],
             "再進場_筆數每顆": c["再進場_筆數每顆"], "進場列": nrow[k[1]], "對0050（僅描述）": c["label"]}
        out["格"][k[1]] = d
        rows.append({kk: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for kk, v in d.items()})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "desc_anyexit.csv"), index=False)
    json.dump(out, open(os.path.join(OUT, "desc_anyexit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    p_ = lambda x: f"{x * 100:+.2f}%"
    L = [f"# 訊號系統：「X 任一」出場版 確認段描述補報（⚠ {TAG}）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。依據裁定 seq246 ①。回測線。", "",
         f"確認段 2022-01-03～2026-08-24；0050 同段 年化 {p_(b50['cagr'])}、回落 {p_(b50['mdd'])}。200 顆取中位；同一份訊號、面板、引擎設定。", "",
         "| E | 年化中位 | 回落中位 | 比值 | 每顆交易筆 | 段尾未出場（每顆） | 勝率 | 持有天數 中位 |", "|---|---|---|---|---|---|---|---|"]
    for E, d in out["格"].items():
        L.append(f"| {E} | {p_(d['年化中位'])} | {p_(d['回落中位'])} | {d['比值']:.3f} | {d['每顆交易筆']:.1f} | {d['段尾未出場_每顆']:.1f} | {d['勝率']:.3f} | {d['持有天數_中位']:.0f} |")
    L += ["", "每年交易次數（每顆平均）："] + [f"- {E}：{d['每年交易']}" for E, d in out["格"].items()]
    L += ["", f"⚠ {TAG}：E1、E2 判定格已依裁定 seq246 改判「依構造不可判定」，本表不改判定、不另挑判定格、不計 N。", ""]
    open(os.path.join(OUT, "desc_anyexit.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"[完成] {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
