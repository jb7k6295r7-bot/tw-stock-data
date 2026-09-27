# -*- coding: utf-8 -*-
"""X2 早年段 報告（只讀 resultsExtX2early/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchExtX2early_report.py"""
from __future__ import annotations
import json, os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsExtX2early")


def p(x):
    return "—" if x is None or x != x else f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    X = S["X2"]; Z = S["0050同窗（描述窗）"]; m = X["5個月（主格）"]; fk = X["假訊號臂_低波動池隨機50檔（描述，5個月，30次）"]
    L = ["# PREREG外部三件 X2（CGO＋低波動）早年段補跑（只上市；⛔ 描述、不判、不計 N）", ""]
    L.append(f"**結論（描述，⛔ 不判）：早年段 2005～2014（只上市）X2 每 5 個月換 {p(m['年化'])}／{p(m['回落'])}，同窗 0050 {p(Z['年化'])}／{p(Z['回落'])} ⇒ 照使用者判準讀是「{m['標籤（描述，⛔ 不判）']}」；"
             f"與主窗（2017～2026 {S['主窗（原件 9e752a6247，描述）']['5個月']}）方向相反；低波動池隨機 50 檔 30 次年化中位 {p(fk['年化中位'])}、主格在第 {fk['主格年化的百分位']:.0f} 百分位。"
             "⚠ 原文期間內、等於已看過；出處為公開研究、原文數字未必可重現。（出處：回測 PREREG外部三件 researchExt 9e752a6247；本件 researchExtX2early）**")
    L.append("")
    L.append("| 頻率 | 2005-01～2014-12 年化／回落（比值） | 標籤（描述） | 2004 殘段期間報酬（0050 同段） | stop_force 關（對照） |")
    L.append("|---|---|---|---|---|")
    for nm in ("5個月（主格）", "月換", "季換"):
        x = X[nm]
        L.append(f"| {nm} | {p(x['年化'])}／{p(x['回落'])}（{x['比值']:.3f}） | {x['標籤（描述，⛔ 不判）']} | {p(x['2004 殘段期間報酬（原文期間外、不足 1 年）'])}（{p(x['0050 同段'])}） | "
                 f"{p(x['stop_force 關（對照）']['年化'])}／{p(x['stop_force 關（對照）']['回落'])} |")
    L.append(f"| 0050 | {p(Z['年化'])}／{p(Z['回落'])}（{Z['比值']:.3f}） | — | — | — |")
    L.append(f"| 只含存活股（5 個月） | {p(X['只含存活股（描述，5個月）']['年化'])}／{p(X['只含存活股（描述，5個月）']['回落'])} | — | — | — |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・照登錄 §三與裁定 seq245 §二：X2 ⛔ 不計 N、全段描述＋前瞻紀錄 ⇒ 早年段只描述；原文期間 2005-01～2025-06 ⇒ 本段全在原文期間內（2004 殘段不足 1 年）")
    L.append(f"  ・資料：{S['資料']}；與 3edc0e2206 版面除 shares 欄外逐檔相同（查核 ①）")
    L.append("  ・停止交易強制出場：開（原件主窗沒開；本段開與關結果相同）；最後一期出場 ＝ 日曆最後一日收盤 ⇒ 沒有超出資料尾的出場")
    L.append("  ・只上市（早年版面沒有上櫃）；含已下市、上市轉上櫃者以上市末日為止")
    L.append("  ・持續持有的檔每期照付一次來回成本（原件引擎慣例）")
    L.append("```")
    L.append("")
    L.append(f"母體：{S['母體']}；停止交易（窗尾前）{S['停止交易（窗尾前）檔數']} 檔；假訊號臂標籤分佈 {fk['標籤分佈']}")
    L.append("")
    if CK:
        L.append(f"獨立查核 `researchExtX2early_check.py`（⛔ 不 import 主程式、researchExt、p4_features、researchH2、rerun17、research13）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"- {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("檔案：`backtest/researchExtX2early.py`、`researchExtX2early_check.py`、`researchExtX2early_report.py`；resultsExtX2early/：summary.json、picks_monthly.csv.gz、equity.csv.gz、fake_arm.csv、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
