# -*- coding: utf-8 -*-
"""稽核 ② 4 報告（只讀 resultsAudit2/4/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_4_report.py"""
from __future__ import annotations
import json, os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/4")
HS = (5, 10, 20, 60)


def p(x):
    return f"{x * 100:+.2f}%"


def cellstr(c):
    if not c or "lo" not in c:
        return f"n {c.get('n', 0)}（{c.get('結果', '—')}）"
    return f"{p(c['dX̄'])}〔{p(c['lo'])}～{p(c['hi'])}〕{c['結果']}"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    M, EA = S["主窗"], S["早年段合併（甲＋乙）"]
    L = ["# 稽核 ② 4：型態全量「上升三角往上突破（S06）」樣本外＋補 5／10 日＋CI 下緣對成本（稽核 seq3 §二 第 3 列；裁定 seq257 順 5）", ""]
    L.append(f"**結論：主窗（原件）四個天數都是結果②，但 CI 下緣只有 20、60 日勉強高於 0.585%（{p(M['H20']['lo'])}、{p(M['H60']['lo'])}），5、10 日沒有；"
             f"早年段（2004-02～2017-02，樣本外）20 日 {p(EA['H20']['dX̄'])}〔{p(EA['H20']['lo'])}～{p(EA['H20']['hi'])}〕仍是結果②、但只剩主窗的一半，"
             f"點估計就低於一次來回成本 0.585%，5／10／60 日都測不出 ⇒ 方向在樣本外仍在、量級縮水到付不起成本 ⇒ 「上升三角往上突破」只能寫「有一點、扣成本後不可執行」，"
             "⛔ 不當買進理由。（出處：回測 PREREG型態全量 researchPatAll b0e44526b8；本件 researchAudit2_4）**")
    L.append("")
    L.append("| d×X̄〔95% CI〕 | 5 日 | 10 日 | 20 日（原件判定格） | 60 日 |")
    L.append("|---|---|---|---|---|")
    for nm, key in (("主窗 2017-03～2026-08（原件）", "主窗"), ("早年甲 2004-02～2014-12（只上市）", "早年甲"), ("早年乙 2015-01～2017-02", "早年乙")):
        L.append(f"| {nm} | " + " | ".join(cellstr(S[key].get(f"H{H}", {})) for H in HS) + " |")
    L.append("| **早年段合併（樣本外）** | " + " | ".join(f"{p(EA[f'H{H}']['dX̄'])}〔{p(EA[f'H{H}']['lo'])}～{p(EA[f'H{H}']['hi'])}〕{EA[f'H{H}']['結果']}" for H in HS) + " |")
    L.append("| 95% CI 下緣 ＞ 0.585%？（主窗／早年合併） | " + " | ".join(
        f"{'是' if M[f'H{H}'].get('95%CI下緣 ＞ 0.585%') else '否'}／{'是' if EA[f'H{H}']['95%CI下緣 ＞ 0.585%'] else '否'}" for H in HS) + " |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・樣本外只有一格判定（早年段合併 20 日，⛔ 不增 N）；5／10／60 日與各段分列為描述")
    L.append("  ・早年甲只上市（早年版面沒有上櫃）；早年乙起點前資料不足 60 根 ⇒ 最早一批事件配不到對照（見件數）")
    L.append("  ・d×X̄ 是【型態組 − 同 first 當天 r60 十分位、沒有型態的股票】的差，成本兩邊相減抵銷；「CI 下緣 ＞ 0.585%」是稽核加的可執行門檻")
    L.append("  ・停止交易強制出場：開（出場日沒成交 ⇒ 之前最後一根收盤，原件 C1 同式）；單筆層固定天數、段內 ⇒ 沒有資料尾截斷")
    L.append("  ・「穩」：主窗四個天數都結果② 但樣本外只剩 20 日、且量級減半 ⇒ 不寫穩")
    L.append("```")
    L.append("")
    L.append("## 一、各段件數與剔除")
    L.append("")
    for key in ("主窗", "早年甲", "早年乙"):
        x = S[key]
        L.append(f"- {key}：窗 {x['窗'][0]}～{x['窗'][1]}、gate3 {x['gate3 檔數']:,} 檔；" + "；".join(
            f"{H} 日 保留 {x[f'H{H}'].get('保留', 0)}、配對剔除 {x[f'H{H}'].get('配對剔除', {})}" for H in HS))
    L.append("")
    L.append("## 二、閘與查核")
    L.append("")
    L.append(f"- 閘：{S['閘']}")
    if CK:
        L.append(f"- 獨立查核 `researchAudit2_4_check.py`（⛔ 不 import 主程式、researchPatAll、researchPatAll_freq、patterns_all、research11）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 三、檔案")
    L.append("")
    L.append("`backtest/researchAudit2_4.py`、`researchAudit2_4_check.py`、`researchAudit2_4_report.py`；resultsAudit2/4/：summary.json、events.csv.gz（三段 × 四 H 逐筆）、raw_events.csv.gz、check.json、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
