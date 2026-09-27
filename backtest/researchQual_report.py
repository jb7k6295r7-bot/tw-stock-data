# -*- coding: utf-8 -*-
"""PREREG品質 報告（只讀 resultsQual/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchQual_report.py"""
from __future__ import annotations
import json, os
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsQual")
QN = {"Q1": "ROE", "Q2": "營業利益÷資產（非毛利）", "Q3": "ROA", "Q4": "研發強度", "量": "成交量相對放大（營量 v1 挑法）"}


def p(x):
    return "—" if x is None or x != x else f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    Z = S["0050"]; PK = S["挑格"]
    L = ["# PREREG品質 seq1：ROE、營業利益÷資產（非毛利）、ROA、研發強度（裁定 seq256；N_組合 ＋2）【A2 暫定】", ""]
    ja, yi = PK["甲"], PK["乙"]
    L.append(f"**結論（⚠ 財報可用日 A2 暫定）：甲族（單用品質）挑中「{QN[ja['量測']]}、每{ja['頻率']}前 {ja['N']} 檔」，確認段 {p(ja['確認']['年化'])}／{p(ja['確認']['回落'])}【{ja['確認']['標籤']}】、"
             f"早年段【{ja['早年']['標籤']}】；乙族（月營收創 24 月新高池內用品質挑）挑中「{QN[yi['量測']]}、每{yi['頻率']}前 {yi['N']} 檔」，確認段 {p(yi['確認']['年化'])}／{p(yi['確認']['回落'])}【{yi['確認']['標籤']}】、"
             f"早年段【{yi['早年']['標籤']}】⇒ 件標籤 甲「{ja['件標籤']}」、乙「{yi['件標籤']}」；同池用量挑（營量 v1 挑法）確認段 {p(yi['同池用量挑（營量 v1 挑法）']['確認']['年化'])}。"
             "（出處：回測 PREREG品質 researchQual；登錄 sha 24e7fb594193b9c0）**")
    L.append("")
    L.append("| 族（挑中格） | 探索 2017-03～2021 | 確認 2022～2026-08 | 早年 2014-06～2016（只上市） | 件標籤 | 假訊號 p（確認／早年） |")
    L.append("|---|---|---|---|---|---|")
    for fam, k in (("甲 單用", ja), ("乙 營收創高池內", yi)):
        L.append(f"| {fam}：{QN[k['量測']]}、{k['頻率']}換、{k['N']} 檔 | {p(k['探索']['年化'])}／{p(k['探索']['回落'])} | {p(k['確認']['年化'])}／{p(k['確認']['回落'])} {k['確認']['標籤']} | "
                 f"{p(k['早年']['年化'])}／{p(k['早年']['回落'])} {k['早年']['標籤']} | **{k['件標籤']}** | "
                 f"{k['假訊號_確認']['p（隨機年化 ≥ 本格）']:.3f}／{k['假訊號_早年']['p（隨機年化 ≥ 本格）']:.3f} |")
    v = yi["同池用量挑（營量 v1 挑法）"]
    L.append(f"| 乙 同池用量挑（並列、⛔ 不判） | — | {p(v['確認']['年化'])}／{p(v['確認']['回落'])} {v['確認']['標籤']} | {p(v['早年']['年化'])}／{p(v['早年']['回落'])} {v['早年']['標籤']} | — | — |")
    L.append(f"| 0050 | {p(Z['探索']['年化'])}／{p(Z['探索']['回落'])} | {p(Z['確認']['年化'])}／{p(Z['確認']['回落'])} | {p(Z['早年']['年化'])}／{p(Z['早年']['回落'])} | — | — |")
    L.append(f"| 營量 v1 | — | {p(S['營量v1']['確認']['年化'])}／{p(S['營量v1']['確認']['回落'])} | — | — | — |")
    L.append("")
    L.append("## 結果句（登錄 §三）")
    L.append("")
    for fam, k in (("甲", ja), ("乙", yi)):
        pre = "隨機挑也做得到：" if k["假訊號_確認"]["p（隨機年化 ≥ 本格）"] >= 0.05 else ""
        L.append(f"- {pre}〔{fam}族〕{QN[k['量測']]}每{k['頻率']}挑前 {k['N']} 檔：確認段 {p(k['確認']['年化'])}／{p(k['確認']['回落'])}（0050 {p(Z['確認']['年化'])}）、"
                 f"早年段 {p(k['早年']['年化'])}／{p(k['早年']['回落'])}（0050 {p(Z['早年']['年化'])}）⇒ {k['件標籤']}"
                 + ("；⚠ 營業利益÷資產（非毛利）" if k["量測"] == "Q2" else "") + "。【A2 暫定】")
    L.append(f"- 乙族：品質挑 − 同池用量挑（確認段）＝ {v['確認 品質 − 量（點）'] if '確認 品質 − 量（點）' in v else yi['同池用量挑（營量 v1 挑法）']['確認 品質 − 量（點）']:+.2f} 點")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append(f"  ・{S['可用日']}（逐字）")
    L.append(f"  ・財報 ＝ {S['財報']}；Q2 ＝ 營業利益÷資產（非毛利）；毛利版照裁定 seq259 §四 另起")
    L.append("  ・停止交易強制出場：開；換股簿按月／季／半年換股、窗尾照市值 ⇒ 依構造不因資料尾截斷（t1_censor 不適用，照實寫）")
    L.append(f"  ・早年段 ＝ 早年版面 2014-06～12（W1 eligible）＋ 主快照 2015-08～2016-12（只上市；主快照 eligible 2015-08 起）串接、各自期初全現金、空窗 2015-01～07 不計："
             f"{S['早年段實際窗']}；乙族早年乙的月營收接早年版面（主快照 2015-01 起、24 月新高算不出）")
    L.append("  ・金融保險業不參與排名（快照 industry.csv 名稱）；含金融版見描述")
    L.append("```")
    L.append("")
    L.append("## 一、挑格細節與必報")
    L.append("")
    for fam, k in (("甲", ja), ("乙", yi)):
        c = k["確認"]
        L.append(f"- {fam}族：挑中 {k['格']}；探索過判準 {k['探索過判準格數']} 格、退化排除 {k['退化排除格數']} 格；確認段 換手 {c['換手']:.2f}、成本／年 {p(c['成本／年'])}、平均持股 {c['平均持股']:.1f}")
    L.append(f"- 乙族池：主窗換股日中位 {yi['池']['乙族池中位（主窗換股日）']:.0f} 檔；湊不滿 N 的換股比例 {yi['池']['湊不滿 N 的換股比例（主窗）']:.2%}")
    L.append(f"- 與營量 v1 持股重疊（確認段，挑中頻率與檔數下各量測）：" + "；".join(f"{k_} {v_:.2f}" for k_, v_ in S["與營量v1持股重疊（確認段，挑中頻率與檔數下各量測）"].items() if v_ is not None))
    L.append(f"- Q1～Q4 兩兩 Spearman（主窗換股日平均）：" + "、".join(f"{k_} {v_:.2f}" for k_, v_ in S["Q 兩兩 Spearman（主窗換股日平均）"].items()))
    L.append(f"- Q4 研發可排名占甲族母體：{S['Q4 研發可排名占甲族母體（主窗換股日平均）']:.1%}")
    L.append("")
    L.append("## 二、描述（全賣全買、含金融、出場敏感度）")
    L.append("")
    for fam, k in (("甲", ja), ("乙", yi)):
        for vn, d in k["描述"].items():
            L.append(f"- {fam}族 {vn}：確認 {p(d['確認'][0])}／{p(d['確認'][1])} {d['確認'][2]}；早年 {p(d['早年'][0])}／{p(d['早年'][1])} {d['早年'][2]}")
    L.append("")
    L.append("## 三、全部判定格（確認段）")
    L.append("")
    cf = T[T["段"] == "確認"]
    L.append("| 族 | 量測 | " + " | ".join(f"{fq} N{N}" for fq in ("月", "季", "半年") for N in (10, 20)) + " |")
    L.append("|---|---|" + "---|" * 6)
    for fam in ("甲", "乙"):
        for k in ("Q1", "Q2", "Q3", "Q4") + (("量",) if fam == "乙" else ()):
            row = []
            for fq in ("月", "季", "半年"):
                for N in (10, 20):
                    x = cf[cf["格"] == f"{fam}_{k}_{fq}_N{N}"].iloc[0]
                    row.append(f"{p(x['年化'])}／{p(x['回落'])} {x['標籤']}")
            L.append(f"| {fam} | {QN[k]} | " + " | ".join(row) + " |")
    L.append("")
    L.append("## 四、先驗（登錄 §五；⛔ 寫下就不改）")
    L.append("")
    L.append(f"- ① 甲族確認段不是合格：{ja['確認']['標籤']}；回落比 0050 淺：{p(ja['確認']['回落'])} vs {p(Z['確認']['回落'])}")
    L.append(f"- ② 乙族挑中格確認段年化高於同池用量挑：{p(yi['確認']['年化'])} vs {p(v['確認']['年化'])}")
    L.append(f"- ③ Q4 研發在甲族最好：甲族挑中 {QN[ja['量測']]}")
    L.append(f"- ④ 早年段甲族挑中格合格：{ja['早年']['標籤']}")
    L.append("")
    L.append("## 五、閘與查核")
    L.append("")
    L.append(f"- 閘：{S['閘']}")
    if CK:
        L.append(f"- 獨立查核 `researchQual_check.py`（⛔ 不 import 主程式、researchMomX、research13、research34、p4_features、researchH2）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k_, v_ in CK.items():
            if isinstance(v_, dict):
                L.append(f"  - {k_}：{'✅' if v_['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v_.items() if a not in ("過", "逐項")))
    L.append("")
    L.append("## 六、檔案")
    L.append("")
    L.append("`backtest/researchQual.py`、`researchQual_check.py`、`researchQual_report.py`；resultsQual/：summary.json、cells.csv、picks.csv.gz、fake.csv.gz、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:16]))


if __name__ == "__main__":
    main()
