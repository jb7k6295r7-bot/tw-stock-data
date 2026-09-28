# -*- coding: utf-8 -*-
"""PREREG動能改良 M1 檔數敏感度（裁定 seq262 §三：seq242 ③ 出場敏感度另補檔數 {5, 10, 20}；只描述）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMomX_n [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchMomX_n_check.py

⭐ 只 import researchMomX（5290e58851），⛔ 不改它：load_world、rank_tables、select、sim_book、seg_stats、label 原樣
格：M1 挑中格 M1_F6_季_N20 的 F／頻率不動，N ∈ {5, 10, 20}；主世界（探索、確認）＋早年世界（只上市、2006～2014）
⭐ 停止交易強制出場：開（researchMomX.sim_book 本來就開）；換股簿、無固定持有 ⇒ t1_censor 不適用
閘：N＝20 ＝ resultsMomX/cells.csv 同格（三段年化、回落逐位元）；N＝10 ＝ cells.csv 的 M1_F6_季_N10（原件就有）
輸出 backtest/resultsMomX/nsens/：cells.csv、summary.json、REPORT.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchMomX as MX                                   # ⭐ 原件，只 import

OUT = os.path.expanduser("~/tw-p17/backtest/resultsMomX/nsens")
NS = (5, 10, 20)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); t00 = time.time()
    SJ = json.load(open(os.path.join(os.path.dirname(OUT), "summary.json"), encoding="utf-8"))
    pk = SJ["挑格"]["M1"]; F, fq = pk["F"], pk["頻率"]
    ref = pd.read_csv(os.path.join(os.path.dirname(OUT), "cells.csv"), float_precision="round_trip")
    rows = []; gate = {}
    log = lambda m: print(m, flush=True)
    for tag, W in (("主", MX.MAIN), ("早年", MX.EARLY)):
        Wd = MX.load_world(W, a.procs, log)
        cal = Wd["cal"]
        SEGP = {nm: (max(int(cal.searchsorted(pd.Timestamp(x))), Wd["w0"]), min(int(cal.searchsorted(pd.Timestamp(y), side="right") - 1), Wd["w1"])) for nm, (x, y) in W["segs"].items()}
        Z = {nm: MX.R13.window_stats(Wd["bench"], 0, Wd["n"], x, y + 1) for nm, (x, y) in SEGP.items()}
        TB = MX.rank_tables(Wd, F)
        for N in NS:
            sel, _ = MX.select(Wd, TB, "M1", F, fq, N)
            res = MX.sim_book(sel, Wd, N)
            for nm, (x, y) in SEGP.items():
                rs = [e for e in sorted(sel) if x <= e <= y]
                st = MX.seg_stats(Wd, res, x, y, N, rs)
                st["標籤"] = MX.label(st["年化"], st["回落"], Z[nm][0], Z[nm][1])
                key = f"M1_F{F}_{fq}_N{N}"
                rows.append({"世界": tag, "格": key, "N": N, "段": nm, **st, "0050年化": float(Z[nm][0]), "0050回落": float(Z[nm][1]),
                             "強制出場": int(res["cnt"].get("stop_force", 0)) if "stop_force" in res["cnt"] else None})
                q = ref[(ref["世界"] == tag) & (ref["格"] == key) & (ref["段"] == nm)]
                if len(q):
                    q = q.iloc[0]
                    gate[f"{tag} {key} {nm}"] = repr(float(q["年化"])) == repr(float(st["年化"])) and repr(float(q["回落"])) == repr(float(st["回落"]))
        MX.D.DATA = MX.H2.H2D
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    ok = all(gate.values())
    S = {"件": "PREREG動能改良 M1 檔數敏感度（描述）", "格": f"M1 F{F} {fq}換", "N": list(NS), "閘（N＝10／20 ＝ 原件 cells.csv）": gate, "閘過": ok, "秒": round(time.time() - t00)}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# PREREG動能改良 M1 檔數敏感度 {5, 10, 20}（描述、⛔ 不判）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq262 §三；seq242 ③。回測線。⭐ 停止交易強制出場：開（原件換股簿本來就開）。", ""]
    cf = T[(T["世界"] == "主") & (T["段"] == "確認")].set_index("N"); ea = T[(T["世界"] == "早年")].set_index("N")
    L.append("**結論（描述）：M1（F6 季換）確認段 " + "、".join(f"N{N} {cf.loc[N, '年化'] * 100:+.2f}%／{cf.loc[N, '回落'] * 100:+.2f}%（{cf.loc[N, '標籤']}）" for N in NS)
             + "；早年 " + "、".join(f"N{N} {ea.loc[N, '年化'] * 100:+.2f}%（{ea.loc[N, '標籤']}）" for N in NS) + f"。閘：{'過' if ok else '不過'}。**")
    L += ["", "| 世界 | 段 | N | 年化 | 回落 | 比值 | 對 0050（描述） | 平均持股 | 換手 | 成本／年 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in T.to_dict("records"):
        L.append(f"| {r['世界']} | {r['段']} | {r['N']} | {r['年化'] * 100:+.2f}% | {r['回落'] * 100:+.2f}% | {r['比值']:.3f} | {r['標籤']} | {r['平均持股']:.1f} | "
                 f"{r['換手（每次換股買進檔數÷N）']:.2f} | {r['成本／年'] * 100:.2f}% |")
    L += ["", f"- 閘：{json.dumps(gate, ensure_ascii=False)}", "- 描述、⛔ 不判、⛔ 不改 M1 的件標籤（另列）；「穩」照 seq253 收緊讀法：本表不寫「穩」", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if not ok:
        raise SystemExit("⛔ 閘不過")


if __name__ == "__main__":
    main()
