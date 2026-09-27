# -*- coding: utf-8 -*-
"""稽核 ② 2 報告（只讀 resultsAudit2/2/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_2_report.py"""
from __future__ import annotations
import json, os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/2")
NMS = ("AD10 − 不加（原件判定量）", "AD10 − ①隨機日加碼", "AD10 − ②同日改買 0050", "AD10 − ③基準②（前 20 日同分位）")
SHORT = {NMS[0]: "對不加（原件）", NMS[1]: "對①隨機日加碼", NMS[2]: "對②同日改買 0050", NMS[3]: "對③基準②"}


def p(x):
    return f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    R = S["結果"]
    cf = {H: R[f"H{H}_confirm"] for H in (60, 120, 240)}
    L = ["# 稽核 ② 2：四類單獨「跌 −10% 加半份（攤平）」重測（稽核 seq3 §二 第 2 列；裁定 seq257 順 5）", ""]
    L.append("**結論：確認段三種持有天數（60／120／240 日），攤平都比不加、也比隨便挑一天加好；但跟「同一天前 20 日跌得差不多的其他股」比分不出"
             f"（{'／'.join(p(cf[H][NMS[3]]['mean']) for H in (60, 120, 240))}，CI 都含 0），而且比同一天改買 0050 差"
             f"（{'／'.join(p(cf[H][NMS[2]]['mean']) for H in (60, 120, 240))}，結果③；探索段三個天數都分不出）⇒ 好處跟「同一天買進前 20 日跌得差不多的任何一檔」分不開，"
             "不是「加碼在自己手上這一檔」特有的；原件「好」只成立在對「不加碼、放現金」。（出處：回測 PREREG四類單獨 researchQuad 5b367571db；本件 researchAudit2_2）**")
    L.append("")
    L.append("| 確認段（每筆以 1 單位計的配對差；CI 進場月分群） | 60 日 | 120 日（原件） | 240 日 |")
    L.append("|---|---|---|---|")
    for nm in NMS:
        L.append(f"| {SHORT[nm]} | " + " | ".join(f"{p(cf[H][nm]['mean'])}〔{p(cf[H][nm]['lo'])}～{p(cf[H][nm]['hi'])}〕{cf[H][nm]['判定']}" for H in (60, 120, 240)) + " |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・停止交易強制出場：開（原件的 delist on：x 日沒成交 ⇒ x 以前最後一根有效收盤）；兩段只收整筆落在段內的持有 ⇒ 沒有資料尾截斷")
    L.append("  ・三個對照都在「同一批被觸發的持有」上逐筆配對；「對不加」是原件的判定量（全部持有，沒觸發的差為 0）")
    L.append("  ・「穩」：本件只寫「對不加、對隨機日：三個天數都好」；對基準②與 0050 都不是好 ⇒ 不寫「穩定有效」")
    L.append("  ・組合層描述（原件 port）沒重跑")
    L.append("```")
    L.append("")
    L.append("## 一、六格全表（探索／確認 × 60／120／240 日）")
    L.append("")
    L.append("| 格 | n | 觸發比例 | 被觸發那批抱到底 | 對不加 | 對①隨機日 | 對②0050 | 對③基準② |")
    L.append("|---|---:|---:|---:|---|---|---|---|")
    for H in (60, 120, 240):
        for seg, sn in (("explore", "探索 2017-03～2021"), ("confirm", "確認 2022～2026-08")):
            c = R[f"H{H}_{seg}"]
            L.append(f"| {H} 日 {sn} | {c['n']:,} | {c['觸發比例']:.3f} | {p(c['被觸發那批抱到底平均'])} | "
                     + " | ".join(f"{p(c[nm]['mean'])} {c[nm]['判定']}" for nm in NMS) + " |")
    L.append("")
    L.append("## 二、逐年（確認段，被觸發那批；對①／對②／對③）")
    L.append("")
    L.append("| 天數 | " + " | ".join(str(y) for y in cf[120]["逐年（被觸發；AD10−①／−②／−③）"]) + " |")
    L.append("|---|" + "---|" * len(cf[120]["逐年（被觸發；AD10−①／−②／−③）"]))
    for H in (60, 120, 240):
        yy = cf[H]["逐年（被觸發；AD10−①／−②／−③）"]
        L.append(f"| {H} 日 | " + " | ".join("／".join(p(v) for v in yy[y]) if y in yy else "—" for y in cf[120]["逐年（被觸發；AD10−①／−②／−③）"]) + " |")
    L.append("")
    L.append("## 三、加碼 5 種在各天數的探索段平均（描述；原件在 120 日挑 AD10）")
    L.append("")
    L.append("| 天數 | " + " | ".join(R["H120_explore"]["加碼 5 種平均（描述）"]) + " |")
    L.append("|---|" + "---|" * 5)
    for H in (60, 120, 240):
        a = R[f"H{H}_explore"]["加碼 5 種平均（描述）"]
        L.append(f"| {H} 日 | " + " | ".join(p(v) for v in a.values()) + " |")
    L.append("")
    L.append("## 四、閘與查核")
    L.append("")
    g = S["閘"]
    L.append(f"- 120 日兩段的每筆 d_AD10 ＝ 原件 explore_diffs／confirm_diffs：{g['H120 d_AD10 ＝ 原件']}")
    L.append(f"- 面板：量測日 ≤ {g['resultsp4 最後量測日']} 用原件的 resultsp4、之後接 panel_ext（到 {g['panel_ext 最後量測日']}）；"
             f"⚠ panel_ext 舊段與 resultsp4 不同：{S['面板差（panel_ext 舊段 vs resultsp4）']} ⇒ 舊段照原件")
    L.append(f"- 基準② 沒進的件數：{S['基準②沒進的件數']}；0050 腿遞延件數（確認段 60／120／240）：{'／'.join(str(cf[H]['0050 腿遞延件數']) for H in (60, 120, 240))}")
    if CK:
        L.append(f"- 獨立查核 `researchAudit2_2_check.py`（⛔ 不 import 主程式、researchQuad、researchAvg、avgdown）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a not in ("過", "不符")))
    L.append("")
    L.append("## 五、檔案")
    L.append("")
    L.append("`backtest/researchAudit2_2.py`、`researchAudit2_2_check.py`、`researchAudit2_2_report.py`；resultsAudit2/2/：summary.json、holdings.csv.gz（每筆持有 × 三個天數）、check.json、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
