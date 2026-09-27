# -*- coding: utf-8 -*-
"""稽核 ② 3 報告（只讀 resultsAudit2/3/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_3_report.py"""
from __future__ import annotations
import json, os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/3")
KX, K2 = "X（對 gate3 等權，原件量）", "X2（基準②：前 20 日同十分位）"


def p(x):
    return f"{x * 100:+.2f}%"


def rs(c):
    return c["出口結果"][1].split("（")[0] + ("（" + c["出口結果"][1].split("（", 1)[1] if "（" in c["出口結果"][1] else "")


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    R = S["結果"]; HS = (5, 10, 20, 60)
    x2 = {H: R[f"H{H}"][K2] for H in HS}
    L = ["# 稽核 ② 3：上升趨勢線跌破 補 5／10／60 日＋基準②（稽核 seq3 §二 第 4 列；裁定 seq257 §三 5）", ""]
    L.append("**結論：四個視窗（5／10／20／60 日）跌破後相對同月等權都在 −0.14%～−0.37%，全部小於賣出再買回的 0.585% ⇒ 扣成本後不可執行（K3，四個視窗都成立）；"
             f"改對「同一天前 20 日報酬同十分位的股票」（基準②）後，20 日由 −0.37% 縮成 {p(x2[20]['平均'])}（CI 含 0，測不出），"
             f"只有 10 日還測得出、且只有 {p(x2[10]['平均'])} ⇒ 原件的「跌破後比較會跌」大半是「前 20 日走勢」本身，不是趨勢線；"
             "「不構成賣出理由」維持。（出處：回測 PREREG上升趨勢線 researchUT 0feb35c37c；本件 researchAudit2_3）**")
    L.append("")
    L.append("| 視窗 | n | X（對同月等權，原件量）〔CI〕 | 出口結果 | X2（基準②）〔CI〕 | 出口結果 | K3 |")
    L.append("|---|---:|---|---|---|---|---|")
    for H in HS:
        a, b = R[f"H{H}"][KX], R[f"H{H}"][K2]
        L.append(f"| {H} 日{'（原件主格）' if H == 20 else ''} | {a['n']:,} | {p(a['平均'])}〔{p(a['lo'])}～{p(a['hi'])}〕 | {a['出口結果'][0]} {a['出口結果'][1]} | "
                 f"{p(b['平均'])}〔{p(b['lo'])}～{p(b['hi'])}〕 | {b['出口結果'][0]} {b['出口結果'][1]} | {b['K3']} |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・事件 ＝ 原件主格（甲 兩點法 × R5 × 1% 穿越）保留事件，⛔ 未重偵測；60 日另排除超窗尾與延伸段斷點（原件 V9 同）")
    L.append("  ・停止交易強制出場：開（出場日沒有有效開盤 ⇒ 用之前最後一根收盤，原件 px 同式）；單筆層固定天數、窗內 ⇒ 沒有資料尾截斷")
    L.append("  ・K3：賣出訊號可執行 ＝ CI 上緣 ＜ −0.585%；四個視窗兩種量都沒到 ⇒ 扣成本後不可執行（裁定 seq257 §三 5 已核的結論，本件視窗補齊後不變）")
    L.append("  ・「穩」：四個視窗基準② 不全同（10 日結果③、其餘結果①）⇒ 不寫穩")
    L.append("```")
    L.append("")
    L.append("## 一、基準② 逐年（X2，各視窗）")
    L.append("")
    yrs = sorted({y for H in HS for y in R[f"H{H}"]["X2 逐年"]})
    L.append("| 視窗 | " + " | ".join(str(y) for y in yrs) + " |")
    L.append("|---|" + "---|" * len(yrs))
    for H in HS:
        yy = R[f"H{H}"]["X2 逐年"]
        L.append(f"| {H} 日 | " + " | ".join(p(yy[str(y)] if str(y) in yy else yy.get(y, float('nan'))) for y in yrs) + " |")
    L.append("")
    L.append("## 二、基準② 的做法（researchAudit2_3 開頭寫死）")
    L.append("")
    L.append("```")
    L.append("同一個 T，gate3 全體中：T 有效 K 棒、T＋1 可買（有成交、開盤有效、非開盤漲停）、[T, T＋1＋H] 無硬斷點、前 20 日報酬可算、R_H 可算")
    L.append("⇒ 依前 20 日報酬分十分位（股票代號序定同值）；ȳ ＝ 與事件股同十分位的其他股 R_H 等權平均；X2 ＝ R_H − ȳ（成本兩邊互抵）")
    L.append("沒進的件數：" + "；".join(f"{H} 日 {R[f'H{H}']['沒進的件數']}" for H in HS))
    L.append("```")
    L.append("")
    L.append("## 三、閘與查核")
    L.append("")
    L.append(f"- 閘：{S['閘']}")
    if CK:
        L.append(f"- 獨立查核 `researchAudit2_3_check.py`（⛔ 不 import 主程式、researchUT、researchM、avgdown、researchH2；只共用資料層）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] in (True, 'True') else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 四、檔案")
    L.append("")
    L.append("`backtest/researchAudit2_3.py`、`researchAudit2_3_check.py`、`researchAudit2_3_report.py`；resultsAudit2/3/：summary.json、events.csv.gz（四視窗逐筆 R、X、X2）、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
