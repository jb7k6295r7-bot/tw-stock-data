# -*- coding: utf-8 -*-
"""稽核 ② 8 報告（只讀 resultsAudit2/8/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_8_report.py"""
from __future__ import annotations
import json, os
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/8")


def p(x):
    return "—" if x != x else f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    C = pd.read_csv(os.path.join(OUT, "bf_cells.csv"))
    J = S["乙 限價"]
    cnt = S["甲 突破過濾 結果類計數"]
    L = ["# 稽核 ② 8：突破後過濾（直接買）、限價（直接買）⇒ 20／60／120 日都列判定格（稽核 seq3 §二 第 8 列；裁定 seq257 順 7）", ""]
    L.append(f"**結論：兩件的「直接買」都維持。突破過濾 14 格：20 日 {cnt['H20'].get('加過濾較差', 0)} 格加過濾較差、{cnt['H20'].get('分不出來', 0)} 格分不出，"
             f"60 日（原件）{cnt['H60'].get('加過濾較差', 0)} 格較差、{cnt['H60'].get('分不出來', 0)} 格分不出，沒有任何一格加過濾比較好；"
             f"限價 3 格：20 日（原件）都分不出、60 日都是結果③（掛低 1／2／3% 比開盤市價差 {p(J['H60_L1']['D'])}／{p(J['H60_L2']['D'])}／{p(J['H60_L3']['D'])}）；"
             "兩件的 120 日都只有約 19 個 120 日區段 ⇒ 依構造不可判定（只描述點估計，都偏向直接買）。"
             "（出處：回測 PREREG突破過濾 researchBF 1344491855、回測 PREREG限價 researchLimit 074d29f6c1；本件 researchAudit2_8）**")
    L.append("")
    L.append("## 一、突破過濾（Δ ＝ r(過濾) − r(A 直接買)；20 日曆月分群、60 日 60 日區段）")
    L.append("")
    L.append("| 型態 | 買法 | 20 日 Δ〔CI〕 | 20 日結果 | 60 日 Δ〔CI〕（原件） | 60 日結果 | 120 日 Δ（描述） |")
    L.append("|---|---|---|---|---|---|---|")
    for (typ, arm), g in C.groupby(["型態", "買法"], sort=False):
        r = {int(h): row for h, row in zip(g["H"], g.to_dict("records"))}
        L.append(f"| {typ} | {r[20]['買法名']} | {p(r[20]['Δ'])}〔{p(r[20]['CI95_lo'])}～{p(r[20]['CI95_hi'])}〕 | {r[20]['結果類']} | "
                 f"{p(r[60]['Δ'])}〔{p(r[60]['CI95_lo'])}～{p(r[60]['CI95_hi'])}〕 | {r[60]['結果類']} | {p(r[120]['Δ'])} |")
    L.append("")
    L.append("## 二、限價（D ＝ r(掛低 k%) − r(開盤市價)）")
    L.append("")
    L.append("| 格 | 20 日（原件）D〔CI〕 | 結果 | 60 日 D〔CI〕 | 結果 | 120 日 D（描述） |")
    L.append("|---|---|---|---|---|---|")
    for k in (1, 2, 3):
        a, b, c = J[f"H20_L{k}"], J[f"H60_L{k}"], J[f"H120_L{k}"]
        L.append(f"| 掛低 {k}% | {p(a['D'])}〔{p(a['lo'])}～{p(a['hi'])}〕 | {a['出口']} {a['結果']} | {p(b['D'])}〔{p(b['lo'])}～{p(b['hi'])}〕 | {b['出口']} {b['結果']} | {p(c['D'])} |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・突破過濾 20 日：用原件既有逐筆 r20（原件 P3：終點 T＋20、進場晚於 T＋20 的臂記 0），⛔ 沒重跑；60 日照抄原件（重算逐位元同）")
    L.append("  ・限價 60 日：import 原件同一套 entries／exits／returns 補算；20、120 日逐筆 ＝ 原件 trades.csv.gz（逐位元）")
    L.append("  ・120 日：120 日區段上限 19 ⇒ n_eff ＜ 30 ⇒ 依構造不可判定（〈一百一十一〉附則：⛔ 不把區段切小）")
    L.append("  ・Bonferroni：突破過濾 20 日照原件 α ＝ 0.05／14；三個天數合計 28 格的下界另列在 bf_cells.csv（Bonf28_lo，描述；N 由裁定線定）")
    L.append("  ・停止交易強制出場：開（兩件原件都 delist on）；單筆層 ⇒ 資料尾補回不適用")
    L.append("  ・⚠ 限價母體是門檻B 訊號（resultsAFC 面板，量測日到 2026-03）⇒ K5 面板截斷沒補（本件只補 K2）")
    L.append(f"  ・「穩」（兩件 20／60 日都沒有任何一格「過濾／限價較好」）：{S['直接買 穩（兩件、H20／H60 皆無「過濾／限價較好」）']}")
    L.append("```")
    L.append("")
    L.append("## 三、閘與查核")
    L.append("")
    L.append(f"- 閘：{S['閘']}")
    if CK:
        L.append(f"- 獨立查核 `researchAudit2_8_check.py`（⛔ 不 import 主程式、researchBF、researchLimit、limit_entry、research11）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 四、檔案")
    L.append("")
    L.append("`backtest/researchAudit2_8.py`、`researchAudit2_8_check.py`、`researchAudit2_8_report.py`；resultsAudit2/8/：summary.json、bf_cells.csv、limit_h60.csv.gz、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:3]))


if __name__ == "__main__":
    main()
