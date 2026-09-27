# -*- coding: utf-8 -*-
"""稽核 ② 9 報告（只讀 resultsAudit2/9/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_9_report.py"""
from __future__ import annotations
import json, os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/9")


def p(x):
    return f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    R = S["結果"]
    a5, a10 = R["攤平_H5"], R["攤平_H10"]
    L = ["# 稽核 ② 9：攤平停利（單筆層，甲）補 5、10 日（稽核 seq3 §二 第 9 列；裁定 seq257 順 7）", ""]
    L.append(f"**結論：攤平（跌 10% 加碼）在 5、10 日變成結果③（加的那一份比同一筆錢買 0050 差 {-a5['X̄'] * 100:.2f}%、{-a10['X̄'] * 100:.2f}%），20、60 日（原件）分不出；"
             f"但同一天前 20 日同十分位、沒觸發的持股換 0050 也差不多（y {p(a5['必附句_配對組']['y'])}、{p(a10['必附句_配對組']['y'])}，X − y CI 都含 0）⇒ "
             "「輸 0050」是同類股普遍的事，⛔ 不是攤平特有；結論方向不變：不支持因為跌了而加碼。停利（漲 15% 賣半）四個天數都分不出。"
             "（出處：回測 PREREG攤平停利 甲 researchAvg 69cdc62bd8；本件 researchAudit2_9）**")
    L.append("")
    L.append("| 格 | n | X̄〔95% CI〕 | 出口／結果 | y（同分位沒觸發換 0050） | X − y〔CI〕 |")
    L.append("|---|---:|---|---|---|---|")
    for cell in ("攤平", "停利"):
        for H in (5, 10, 20, 60):
            J = R[f"{cell}_H{H}"]; d = J["必附句_配對組"]["X−y"]
            L.append(f"| {cell} {H} 日{'（原件）' if H in (20, 60) else ''} | {J['n']:,} | {p(J['X̄'])}〔{p(J['lo'])}～{p(J['hi'])}〕 | {J['出口']} {J['結果']} | "
                     f"{p(J['必附句_配對組']['y'])} | {p(d['X̄'])}〔{p(d['lo'])}～{p(d['hi'])}〕 |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・5、10 日 ⛔ 沒有假訊號臂（原件假訊號陣列的天數維寫死 2 格；原件 20／60 日假訊號 x2 ＝ 0）")
    L.append("  ・5、10 日分群 ＝ 曆月（同 20 日）；原件 20／60 日照原件重算（逐筆逐位元同）")
    L.append("  ・停止交易強制出場：開（原件 delist on）；單筆層 ⇒ 資料尾補回不適用")
    L.append(f"  ・「穩」（同型 4 個天數同結果）：攤平 {S['穩_攤平（四個天數同結果）']}（5／10 日結果③、20／60 日結果①）；停利 {S['穩_停利（四個天數同結果）']}")
    L.append("```")
    L.append("")
    L.append("## 給使用者的句子（照原件 sentence 同一張表；5、10 日）")
    L.append("")
    for cell in ("攤平", "停利"):
        for H in (5, 10):
            L.append(f"- {R[f'{cell}_H{H}']['給使用者的句子']}")
    L.append("")
    L.append("## 閘與查核")
    L.append("")
    L.append(f"- 閘：{S['閘']}")
    if CK:
        L.append(f"- 獨立查核 `researchAudit2_9_check.py`（⛔ 不 import 主程式、researchAvg、avgdown、research11、researchH2）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 檔案")
    L.append("")
    L.append("`backtest/researchAudit2_9.py`、`researchAudit2_9_check.py`、`researchAudit2_9_report.py`；resultsAudit2/9/：summary.json、events_h5_h10.csv.gz、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
