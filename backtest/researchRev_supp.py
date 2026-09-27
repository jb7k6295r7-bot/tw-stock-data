# -*- coding: utf-8 -*-
"""PREREG反轉訊號 個股層補充版（裁定線指示：用 panel_ext 補上 2026-04～07；⛔ 只當補充描述、⛔ 不覆蓋原交件）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchRev_supp.py run|compare [--procs 2]

⭐ 程式一字不動：import researchRev（502cf9761f），只把 stock_universe 的面板換成 resultsp9_engine/panel_ext.csv.gz
   （sha256 d75bf50b…；resultsp9_engine/PANEL_SHA.md；同一支 build_panel 延伸到 2026-08-03；2026-03-02 以前與 resultsp4 面板的 eligible
   在重疊列逐列相同，resultsp4 多出的 1,061 列全不在 gate3 ⇒ 母體不變）
輸出：resultsRev/supp_panelext_run/（researchRev body 全套輸出）、resultsRev/supp_panelext_compare.csv、resultsRev/supp_panelext_REPORT.md
"""
from __future__ import annotations
import hashlib, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchRev as RV

HERE = os.path.expanduser("~/tw-p17/backtest")
PANEL = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
RUN = os.path.join(HERE, "resultsRev", "supp_panelext_run")


def stock_universe_ext(cal):
    from backtest import p4_features as P4F
    stocks = pd.read_csv(os.path.join(RV.H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = RV.UG.gate3(stocks)
    p = P4F.read_panel(PANEL)
    p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))]
    elig = {}
    for sid, g in p.groupby("stock_id"):
        elig[sid] = set(str(x)[:7] for x in g["measure_date"])
    mk = U.set_index("stock_id")["market"]
    return sorted(elig), elig, mk


def compare():
    A = pd.read_csv(os.path.join(HERE, "resultsRev", "cells.csv")); B = pd.read_csv(os.path.join(RUN, "cells.csv"))
    k = ["層", "段", "code", "版"]
    A = A[(A["層"] == "個股")]; B = B[(B["層"] == "個股")]
    m = A[k + ["名", "邊", "事件", "n_eff", "mean", "lo", "hi", "出口", "結果", "判定", "成功率", "基準2成功率"]].merge(
        B[k + ["事件", "n_eff", "mean", "lo", "hi", "出口", "結果", "判定", "成功率", "基準2成功率"]], on=k, suffixes=("_原", "_補"))
    m["判定變了"] = m["判定_原"] != m["判定_補"]
    m.to_csv(os.path.join(HERE, "resultsRev", "supp_panelext_compare.csv"), index=False)
    SA = json.load(open(os.path.join(HERE, "resultsRev", "summary.json"), encoding="utf-8")); SB = json.load(open(os.path.join(RUN, "summary.json"), encoding="utf-8"))

    def p_(x):
        return "—" if not np.isfinite(x) else f"{x * 100:+.2f}%"
    L = ["# PREREG反轉訊號 個股層補充版（panel_ext 補 2026-04～07；⛔ 只當補充描述、不改已判的格）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。會不會改已判的格 ⇒ 由裁定定。", "",
         "- 原交件（502cf9761f）的個股層母體用 resultsp4/panel.csv.gz（量測日只到 2026-03-02）⇒ 2026-04～07 的事件與基準股日實際沒進來（原報告沒寫明）",
         "- 補充版：同一支程式，只把面板換成 resultsp9_engine/panel_ext.csv.gz（sha256 d75bf50b…，量測日到 2026-08-03）；"
         "2026-03-02 以前兩份面板在重疊列的 eligible 逐列相同（resultsp4 多出的 1,061 列都不在 gate3）",
         f"- Bonferroni：原 k＝{SA['Bonferroni_個股']['k']}、補 k＝{SB['Bonferroni_個股']['k']}；基準股日 原 {SA['個股基準']['股日']:,}、補 {SB['個股基準']['股日']:,}", "",
         f"**判定有變的格：{int(m['判定變了'].sum())} 格**" + ("：" + "、".join(f"{r.名}（{r.版}）{r.判定_原}→{r.判定_補}" for r in m[m['判定變了']].itertuples()) if m["判定變了"].any() else ""), "",
         "| 訊號 | 版 | 事件 原／補 | 差 原 | CI 原 | 判定 原 | 差 補 | CI 補 | 判定 補 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in m.itertuples():
        star = "⭐ " if r.判定_原 == "通過" or r.判定_補 == "通過" else ""
        L.append(f"| {star}{r.名} | {r.版} | {r.事件_原}／{r.事件_補} | {p_(r.mean_原)} | [{p_(r.lo_原)}, {p_(r.hi_原)}] | {r.判定_原} | {p_(r.mean_補)} | [{p_(r.lo_補)}, {p_(r.hi_補)}] | {r.判定_補} |")
    L += ["", "大盤層不受面板影響（不重報）。補充版全套輸出在 supp_panelext_run/。", ""]
    open(os.path.join(HERE, "resultsRev", "supp_panelext_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(m[["名", "版", "事件_原", "事件_補", "判定_原", "判定_補"]].to_string())


if __name__ == "__main__":
    if sys.argv[1] == "run":
        RV.stock_universe = stock_universe_ext
        procs = sys.argv[sys.argv.index("--procs") + 1] if "--procs" in sys.argv else "2"
        sys.argv = [sys.argv[0], "body", "--procs", procs, "--out", RUN]
        RV.main()
    else:
        compare()
