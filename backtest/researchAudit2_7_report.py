# -*- coding: utf-8 -*-
"""稽核 ② 7 報告（只讀 resultsAudit2/7/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_7_report.py"""
from __future__ import annotations
import json, os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/7")
KE, KY, KYC, KX = ("原件 E（續抱原始報酬）", "① Y 續抱 − 換 0050（原件口徑，0050 多付 0.1425%）",
                   "① Y_c 續抱 − 換 0050（0050 付一次來回 0.385%）", "② X2 續抱 − 基準②")
NM = {"甲": "收盤跌破破壞價", "乙": "收盤跌破 MA20", "丙": "收盤跌破 MA60"}


def p(x):
    return f"{x * 100:+.2f}%"


def c(d):
    return f"{p(d['mean'])}〔{p(d['lo'])}～{p(d['hi'])}〕{d['結果']}"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    R = S["結果"]
    L = ["# 稽核 ② 7：既有部位出場（跌破破壞價／MA20／MA60）判定量改「續抱 − 賣掉改買 0050」＋基準②（稽核 seq3 §二 第 7 列；裁定 seq257 順 7）", ""]
    L.append("**結論：① 改成「續抱 − 賣掉換 0050」後，三訊號 × 20／60 日 6 格全部結果③（續抱比換 0050 差 0.9～2.7 點；扣 ETF 一次來回 0.385% 後仍全部結果③）；"
             "② 但對「同一天前 20 日漲跌同十分位的其他股票」（基準②），6 格全部測不出（−0.06%～+0.27%）"
             "⇒ 續抱輸 0050 是「一般個股同期輸 0050」，不是跌破均線帶來的；跌破本身仍「不構成賣出理由」（原件結論的理由改成：訊號對同類股沒有預測力）。"
             "（出處：回測 PREREG出場訊號 researchExit bd3fa4d69f；本件 researchAudit2_7）**")
    L.append("")
    L.append("| 格 | 原件 E（續抱原始報酬） | ① 續抱 − 換 0050 | ① 扣 ETF 來回後 | ② 續抱 − 基準② |")
    L.append("|---|---|---|---|---|")
    for g in "甲乙丙":
        for H in (20, 60):
            x = R[f"{g}_H{H}"]
            L.append(f"| {NM[g]} {H} 日 | {c(x[KE])} | {c(x[KY])} | {c(x[KYC])} | {c(x[KX])} |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・① 是用原件既有逐筆數字重判（events_kept.csv.gz 的「換0050減續抱」），⛔ 沒重跑事件；② 是本件新算")
    L.append("  ・Y ＝ X2 ＋（同分位股 − 0050）：Y 顯著為負而 X2 測不出 ⇒ 差距來自「同類股整體輸 0050」這一項")
    L.append("  ・賣掉換 0050 在數字上【可執行】（Y_c CI 上緣 ＜ 0）⇒ 但對任何同類股同樣成立，⛔ 不是「跌破就賣」的理由；「個股 vs 0050」是組合層問題（見 PREREGP14／P17）")
    L.append("  ・停止交易強制出場：開（原件 delist on：下市了結）；單筆層、T＋H ≤ 窗尾 ⇒ 沒有資料尾截斷")
    r1 = {R[f"{g}_H{H}"][KYC]["結果"] for g in "甲乙丙" for H in (20, 60)}; r2 = {R[f"{g}_H{H}"][KX]["結果"] for g in "甲乙丙" for H in (20, 60)}
    L.append(f"  ・「穩」（收緊：6 判定格結果全同、且 5／10 日描述不反向）：① 扣來回後 6 格 {'／'.join(sorted(r1))}；② 6 格 {'／'.join(sorted(r2))}；"
             "⚠ ① 在 5、10 日多數分不出、② 在 甲 10 日 結果③、乙 5 日 結果② ⇒ 只寫「20／60 日一致」，⛔ 不寫全天數穩")
    L.append("```")
    L.append("")
    L.append("## 一、5、10 日（描述；原件描述臂 b）")
    L.append("")
    L.append("| 格 | 原件 E | ① 續抱 − 換 0050 | ① 扣 ETF 來回 | ② 續抱 − 基準② |")
    L.append("|---|---|---|---|---|")
    for g in "甲乙丙":
        for H in (5, 10):
            x = R[f"{g}_H{H}"]
            L.append(f"| {NM[g]} {H} 日 | {c(x[KE])} | {c(x[KY])} | {c(x[KYC])} | {c(x[KX])} |")
    L.append("")
    L.append("120 日（依構造不可判定，描述）：" + "；".join(f"{NM[g]} Y {p(R[f'{g}_H120']['Y 平均'])}、X2 {p(R[f'{g}_H120']['X2 平均'])}" for g in "甲乙丙"))
    L.append("")
    L.append("## 二、基準② 的做法與件數")
    L.append("")
    L.append("同一個 T：十分位母體 ＝ gate3 中 T 有效、前 20 日報酬可算（含事件股）；配對股 ＝ 同十分位、非同格事件股、T＋1 可賣（有成交、開盤有效、非開盤跌停）、"
             "[T−60, T＋H] 無硬斷點、R 可算；R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1；X2 ＝ 事件 R − 配對股平均。")
    L.append("")
    L.append(f"沒進的件數：{S['基準②沒進']}")
    L.append("")
    L.append("## 三、閘與查核")
    L.append("")
    L.append(f"- 閘：由原件 events_kept 重算 6 格 n／E／結果 ＝ 原件交件表：{S['閘']['原件 6 格 n／E／結果（由 events_kept 重算）']}")
    if CK:
        L.append(f"- 獨立查核 `researchAudit2_7_check.py`（⛔ 不 import 主程式、researchExit、exit_signal、researchH2、avgdown、research11）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 四、檔案")
    L.append("")
    L.append("`backtest/researchAudit2_7.py`、`researchAudit2_7_check.py`、`researchAudit2_7_report.py`；resultsAudit2/7/：summary.json、events.csv.gz、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
