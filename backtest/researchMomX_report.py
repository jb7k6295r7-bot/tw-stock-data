# -*- coding: utf-8 -*-
"""PREREG動能改良 報告（只讀 resultsMomX/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchMomX_report.py"""
from __future__ import annotations
import json, os
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsMomX")
MN = {"M1": "剔除極端 3%", "M2": "持續型", "M3": "殘差動能", "M4": "波動縮放"}
SAME = {"M1": "與 F（W1 池剔除極端強勢）同一想法、換參數再測", "M3": "與 C（W1 池殘差動能）同一想法、換參數再測"}


def p(x):
    return "—" if x is None or x != x else f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    Z = S["0050"]; PK = S["挑格"]
    labs = {M: PK[M]["件標籤（兩段較嚴）"] for M in PK}
    L = ["# PREREG動能改良 seq1：剔除極端、持續型、殘差動能、波動縮放（裁定 seq256；N_組合 ＋4）", ""]
    ok = [M for M in PK if labs[M] == "合格"]; al = [M for M in PK if labs[M] == "另列"]
    L.append("**結論：四件兩段（確認 2022～2026、早年 2006～2014）較嚴的標籤：" + "、".join(f"{MN[M]}【{labs[M]}】" for M in PK) +
             ("；⇒ 沒有一件兩段都合格" if not ok else f"；兩段都合格：{'、'.join(MN[M] for M in ok)}") +
             "。M1、M3 與 F／C 同一想法、換參數再測，結果不覆蓋 F、C 的「另列」。（出處：回測 PREREG動能改良 researchMomX；登錄 sha f9b6932850aa4ea7）**")
    L.append("")
    L.append("| 件（挑中格） | 確認 2022～2026 年化／回落（比值） | 標籤 | 早年 2006～2014 年化／回落 | 標籤 | 件標籤 | 比同格單純動能多（確認／早年，點） | 假訊號 p（確認／早年） |")
    L.append("|---|---|---|---|---|---|---|---|")
    for M in PK:
        k = PK[M]; c, e = k["確認"], k["早年"]
        L.append(f"| {MN[M]}（F{k['F']}、{k['頻率']}換、{k['N']} 檔） | {p(c['年化'])}／{p(c['回落'])}（{c['比值']:.3f}） | {c['標籤']} | {p(e['年化'])}／{p(e['回落'])} | {e['標籤']} | **{labs[M]}** | "
                 f"{k['同格 M0']['確認 比 M0 多（點）']:+.2f}／{k['同格 M0']['早年 比 M0 多（點）']:+.2f} | "
                 f"{k['假訊號_確認']['p（隨機年化 ≥ 本格）']:.3f}／{k['假訊號_早年']['p（隨機年化 ≥ 本格）']:.3f} |")
    L.append(f"| 0050 | {p(Z['確認']['年化'])}／{p(Z['確認']['回落'])}（{Z['確認']['比值']:.3f}） | — | {p(Z['早年']['年化'])}／{p(Z['早年']['回落'])}（{Z['早年']['比值']:.3f}） | — | — | — | — |")
    L.append(f"| 營量 v1（並列） | {p(S['營量v1']['確認']['年化'])}／{p(S['營量v1']['確認']['回落'])} | — | — | — | — | — | — |")
    L.append("")
    L.append("## 結果句（登錄 §三）")
    L.append("")
    for M in PK:
        k = PK[M]; c, e = k["確認"], k["早年"]
        L.append(f"- 〔{MN[M]}〕每{k['頻率']}挑前 {k['N']} 檔（形成期 {k['F']} 個月），2022～2026 年化 {p(c['年化'])}／回落 {p(c['回落'])}（0050 {p(Z['確認']['年化'])}）；"
                 f"早年段 {p(e['年化'])}；比單純動能多 {k['同格 M0']['確認 比 M0 多（點）']:+.2f} 點。" + (f"⚠ {SAME[M]}。" if M in SAME else ""))
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・停止交易強制出場：開；換股簿按月（季）換股、窗尾照市值，沒有固定持有天數的出場 ⇒ 依構造不會因資料尾截斷丟訊號（t1_censor 不適用）；最後換股日 2026-08-04")
    L.append("  ・早年：早年版面（只上市、2004-02 起的價格）；早年沒有個股法人 ⇒ eligible ＝ liq_ok ∧ bars_ok（非 W1 三道閘）；登錄寫 2006～2016，2015～2016 做不到（兩版面還原尺度未接）")
    L.append("  ・形成期讀法：跳過換股日前一整月（登錄 §一）；不跳過的讀法只在下表描述")
    L.append("  ・PREREGF（W1 池剔除極端強勢）主窗 +26.14%／−40.27% 另列、PREREGC（W1 池殘差動能）+24.62%／−41.51% 另列 ⇒ 本件方向已見，M1、M3 結果並列、不覆蓋")
    L.append("  ・M4 實作 ＝ 覆蓋層（M0 同格換股簿 × 股票部位 w，換股日調整、調整金額扣 0.585%）")
    L.append("```")
    L.append("")
    L.append("## 一、挑格細節（探索段 2017-03～2021-12；退化格事前排除）")
    L.append("")
    L.append("| 件 | 挑中 | 探索 年化／回落（比值） | 探索過判準格數 | 退化排除 | 確認 換手／成本／年／平均持股 | 其他必報 | 確認 與營量 v1 重疊 | 不跳過讀法（確認／早年） |")
    L.append("|---|---|---|---:|---:|---|---|---|---|")
    for M in PK:
        k = PK[M]; c = k["確認"]; oth = []
        if "持續判定後留下比例" in c:
            oth.append(f"留下比例 {c['持續判定後留下比例']:.2f}")
        if "平均股票比例" in c:
            oth.append(f"平均股票比例 確認 {c['平均股票比例']:.2f}／早年 {k['早年'].get('平均股票比例') or float('nan'):.2f}")
        d = k["描述_不跳過最近一月（另一讀法）"]
        L.append(f"| {MN[M]} | {k['格']} | {p(k['探索']['年化'])}／{p(k['探索']['回落'])}（{k['探索']['比值']:.3f}） | {k['探索過判準格數']} | {k['退化排除格數']} | "
                 f"{c.get('換手（每次換股買進檔數÷N）', float('nan')):.2f}／{p(c.get('成本／年'))}／{c['平均持股']:.1f} | {'；'.join(oth) or '—'} | "
                 f"{k.get('確認 與營量 v1 重疊率（本格持股中也在營量 v1 的比例，逐日均）') or float('nan'):.2f} | {p(d['確認']['年化'])}／{p(d['早年']['年化'])} |")
    L.append("")
    L.append("## 二、出場敏感度（新規矩 ③；確認段合格／另列的件才跟；描述）")
    L.append("")
    any_s = False
    for M in PK:
        s = PK[M].get("出場敏感度（新規矩 ③，描述）")
        if s:
            any_s = True
            L.append(f"- {MN[M]}：" + "；".join(f"{k} {p(v['年化'])}／{p(v['回落'])} {v['標籤']}" for k, v in s.items()))
    if not any_s:
        L.append("- 沒有件的確認段是合格或另列 ⇒ 不跟")
    L.append("")
    L.append("## 三、全部格（確認段；M0 為單純動能對照、⛔ 不判）")
    L.append("")
    cf = T[(T["世界"] == "主") & (T["段"] == "確認")]
    L.append("| 格 | " + " | ".join(MN.get(M, "M0 單純動能") for M in ("M0", "M1", "M2", "M3", "M4")) + " |")
    L.append("|---|" + "---|" * 5)
    for F in (3, 6, 12):
        for fq in ("月", "季"):
            for N in (10, 20):
                row = []
                for M in ("M0", "M1", "M2", "M3", "M4"):
                    x = cf[cf["格"] == f"{M}_F{F}_{fq}_N{N}"].iloc[0]
                    row.append(f"{p(x['年化'])}／{p(x['回落'])} {x['標籤']}")
                L.append(f"| F{F} {fq} N{N} | " + " | ".join(row) + " |")
    L.append("")
    L.append("## 四、先驗（登錄 §五；⛔ 寫下就不改）")
    L.append("")
    m0c = cf[cf["件"] == "M0"]
    L.append(f"- ① M0 確認段不合格（約七成）：M0 12 格確認段 合格 {int((m0c['標籤'] == '合格').sum())}／另列 {int((m0c['標籤'] == '另列').sum())}／不合格 {int((m0c['標籤'] == '不合格').sum())}")
    L.append("- ②～④ 見上表（四件挑中格的確認段年化 vs 同格 M0、合格件數、M4 回落與年化、早年段標籤）")
    L.append("")
    L.append("## 五、閘與查核")
    L.append("")
    L.append(f"- 閘：{S['閘']}")
    if CK:
        L.append(f"- 獨立查核 `researchMomX_check.py`（⛔ 不 import 主程式、researchSector、research13、researchH2）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a not in ("過", "逐項")))
    L.append("")
    L.append("## 六、沿革（裁定 seq256 §二 1）")
    L.append("")
    for k, v in S["沿革（裁定 seq256 §二 1）"].items():
        L.append(f"- {k}：{v}")
    L.append("")
    L.append("## 七、檔案")
    L.append("")
    L.append("`backtest/researchMomX.py`、`researchMomX_check.py`、`researchMomX_report.py`；resultsMomX/：summary.json、cells.csv（5 件 × 12 格 × 三段）、picks.csv.gz、fake.csv.gz、eq_picks.npz、check.json、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
