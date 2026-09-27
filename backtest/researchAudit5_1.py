# -*- coding: utf-8 -*-
"""稽核 §五（稽核 seq3 §五、§七之六；裁定 seq255、seq257 順 7 後半）第 1 件：M1、門檻B 單筆層 +6.95 點 ⇒ K3 用既有數字扣成本重判（⛔ 不跑新的）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit5_1
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit5_1_check.py

讀法（⭐ 寫在看數字之前）：
  K3 扣成本 ＝ 把「要進出一次才拿得到」的那一側扣一次來回成本；判得出 ⇔ 扣後 CI 下緣 ＞ 0（稽核 §八 G2 的慣例：「CI 下緣 − 成本 ＞ 0」）
  ① PREREGM1 層一（大盤層；resultsm1/layer1.csv，commit 6d3ea9905）：判定格 7 格 ＝ v2 §3-4（c、d 的 H＝120 全期＋a 的 H＝120 主判定 2001 起）
     差 ＝ 狀態 S 的段平均未來 120 日報酬 − 其餘段；照狀態進出一次 ⇒ 扣 0.385%（大盤層／ETF，裁定口徑）；另並列 0.585%（個股口徑）
     ⛔ 層一沒有比價基準（原件 summary.md 自註）⇒ 本重判只改「扣成本後判不判得出」，⛔ 不做「贏大盤」比較
  ② 門檻B 單筆層（策略線〈門檻B全期回測與五問登錄地圖〉§二，2026-09-20；專案搬出_20260925）：
     全期 98 月 H＝120 逐訊號等權平均超額 +6.95pp、月分群 CI [+4.33, +9.57]（原件 §三 ③ 自註「成本未扣」）⇒ 扣 0.585%（個股）
     另三段（除四月、2021-01～2026-03、2017-2020）同式並列
  ⚠ 既有數字的其他問題（K5：資料到 2026-03、月營收倖存者；K4：無基準②）不在 K3 範圍，照原件的限制欄；⛔ 本件不處理
輸出 backtest/resultsAudit5/1/：rejudge.csv、summary.json、REPORT.md
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsAudit5", "1")
M1_CSV = os.path.join(HERE, "resultsm1", "layer1.csv")
GB_DOC = "/mnt/c/SynologyDrive/投資/台股策略用/專案搬出_20260925/門檻B全期回測與五問登錄地圖_策略線_20260920.md"
COST_IDX, COST_STK = 0.00385, 0.00585
# 門檻B：原件 §二 表（pp；⭐ 逐字抄錄，查核從原件文字重新解析）
GB = [("全期", 98, 6.95, 4.33, 9.57), ("除四月", 97, 6.71, 4.10, 9.31), ("2021-01~2026-03", 57, 7.03, 3.79, 10.26), ("2017-2020（中心擬合段）", 41, 6.84, 2.43, 11.25)]


def judge(lo, hi):
    return "扣成本後判得出（CI 下緣 ＞ 0）" if lo > 0 else ("扣成本後判得出（為負）" if hi < 0 else "扣成本後判不出（CI 含 0）")


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    d = pd.read_csv(M1_CSV, comment="#", float_precision="round_trip")
    j = d[(d["H"] == 120) & (((d["signal"] == "a") & (d["window"] == "主判定 2001 起")) | (d["signal"].isin(["c", "d"]) & (d["window"] == "全期")))]
    assert len(j) == 7, len(j)
    for _, r in j.iterrows():
        row = {"件": "PREREGM1 層一", "格": f"{r['label']}｜{r['state']}｜{r['window']}｜H120", "段數": int(r["n_seg"]),
               "原_差pp": r["diff"] * 100, "原_CI": f"{r['ci_lo'] * 100:+.2f}～{r['ci_hi'] * 100:+.2f}", "原_判定": r["judge"]}
        for nm, cst in (("0.385%", COST_IDX), ("0.585%", COST_STK)):
            lo, hi = r["ci_lo"] - cst, r["ci_hi"] - cst
            row[f"扣{nm}_差pp"] = (r["diff"] - cst) * 100; row[f"扣{nm}_CI"] = f"{lo * 100:+.2f}～{hi * 100:+.2f}"; row[f"扣{nm}_判定"] = judge(lo, hi)
        rows.append(row)
    doc = open(GB_DOC, "rb").read()
    for nm, m, pp, lo, hi in GB:
        row = {"件": "門檻B 單筆層（H120 逐訊號超額）", "格": nm, "段數": m, "原_差pp": pp, "原_CI": f"{lo:+.2f}～{hi:+.2f}", "原_判定": "成本未扣（原件 §三 ③）"}
        for cn, cst in (("0.385%", COST_IDX), ("0.585%", COST_STK)):
            row[f"扣{cn}_差pp"] = pp - cst * 100; row[f"扣{cn}_CI"] = f"{lo - cst * 100:+.2f}～{hi - cst * 100:+.2f}"
            row[f"扣{cn}_判定"] = judge(lo - cst * 100, hi - cst * 100)
        rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "rejudge.csv"), index=False)
    m1 = T[T["件"] == "PREREGM1 層一"]; gb = T[T["件"] != "PREREGM1 層一"]
    S = {"出處": {"M1": {"檔": "backtest/resultsm1/layer1.csv", "sha256": hashlib.sha256(open(M1_CSV, "rb").read()).hexdigest()[:16], "commit": "6d3ea9905"},
                "門檻B": {"檔": GB_DOC, "sha256": hashlib.sha256(doc).hexdigest()[:16]}},
         "M1_扣0.385%_判得出格數": int(m1["扣0.385%_判定"].str.startswith("扣成本後判得出").sum()),
         "M1_扣0.585%_判得出格數": int(m1["扣0.585%_判定"].str.startswith("扣成本後判得出").sum()),
         "門檻B_扣0.585%": gb[["格", "扣0.585%_差pp", "扣0.585%_CI", "扣0.585%_判定"]].to_dict("records")}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    g0 = gb.iloc[0]
    L = ["# 稽核 §五 第 1 件：M1、門檻B 單筆層 K3 扣成本重判（既有數字，⛔ 未跑新的）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。稽核 seq3 §五、§七之六；裁定 seq255、seq257 順 7。回測線。", "",
         f"**結論：PREREGM1 層一 7 個判定格扣成本（0.385%／0.585%）後判得出的仍是 {S['M1_扣0.385%_判得出格數']}／{S['M1_扣0.585%_判得出格數']} 格 ⇒ 原判定不變（正式）；"
         f"門檻B 單筆層全期扣 0.585% 後 {g0['扣0.585%_差pp']:+.2f} 點、CI {g0['扣0.585%_CI']} ⇒ {g0['扣0.585%_判定']}（四段皆同）。**", "",
         "| 件 | 格 | 段／月 | 原 差 | 原 CI | 扣 0.385% CI | 扣 0.585% CI | 扣成本後 |", "|---|---|---|---|---|---|---|---|"]
    for _, r in T.iterrows():
        k = "扣0.385%_判定" if r["件"] == "PREREGM1 層一" else "扣0.585%_判定"
        L.append(f"| {r['件']} | {r['格']} | {r['段數']} | {r['原_差pp']:+.2f} | {r['原_CI']} | {r['扣0.385%_CI']} | {r['扣0.585%_CI']} | {r[k]} |")
    L += ["", "## 讀法與限制", "",
          "- K3 慣例：扣一次來回成本後 CI 下緣 ＞ 0 才算判得出（稽核 §八 G2 同式）；大盤層用 0.385%（ETF），並列 0.585%",
          "- M1：原件判定字（還沒測／未判定：缺假訊號組半寬）是 K3 以外的原因，扣成本只會讓 CI 更往下 ⇒ 判定字不變；⛔ 層一沒有比價基準、不做贏大盤比較",
          "- 門檻B：數字出自策略線文件（非本 repo 產出；sha 見 summary.json）；逐訊號等權、無槽位、無資金約束（原件 §三 ①②）；"
          "K5（資料到 2026-03、月營收倖存者）、K4（無基準②）不在本件範圍，⛔ 本重判只回答 K3",
          "- ⭐ 門檻B 的組合層版本（P7／P9 系、219 表 N8 +28.18%／−41.80%）才是可實現的結果；單筆層 +6.95 點 ⛔ 不可讀成組合層年化", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])


if __name__ == "__main__":
    main()
