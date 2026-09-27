# -*- coding: utf-8 -*-
"""稽核 ② 5 報告（只讀 resultsAudit2/5/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchAudit2_5_report.py"""
from __future__ import annotations
import json, os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/5")
HS = (5, 10, 20, 60)
SEGS = ("探索 2016～2020", "確認 2021～2026", "早年 2012～2014")


def p(x):
    return f"{x * 100:+.2f}%"


def c(d):
    return f"{p(d['mean'])} {d['判定']}" if "mean" in d else "—"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    R = S["結果"]
    cf = {H: R[f"確認 2021～2026｜H{H}"] for H in HS}; ea = {H: R[f"早年 2012～2014｜H{H}"] for H in HS}
    L = ["# 稽核 ② 5：選股條件 G1 營收創 24 月新高、G3 創高＋多頭排列 重測（稽核 seq3 §二 第 1 列、§八；裁定 seq257 順 5、seq258 §二）", ""]
    L.append("**結論：改對「同一天前 20 日漲跌同十分位」（基準②）後，G1、G3 在探索（2016～2020）與確認（2021～2026）四個天數都還是好；"
             f"扣一次來回成本（乙口徑）後，G3 確認段四個天數都好（20 日 {p(cf[20]['G3']['X2 甲互抵']['mean'])}），G1 只有 20、60 日好（5、10 日分不出）；"
             f"G3 對「只看多頭排列」同月配對確認段四個天數都好；早年 2012～2014（樣本外、只上市）明顯變弱：G1 20 日 {p(ea[20]['G1']['X2 甲互抵']['mean'])} 好但扣成本分不出、"
             f"G3 20 日分不出、只有 60 日扣成本後仍好。⚠ 下市公司月營收補不到：照 P4 最壞情境（−100％）全部翻成差、0％ 版確認段仍好 ⇒ 量級取決於下市股處理。"
             "（出處：回測 研究三／四 PREREG3 research34；本件 researchAudit2_5）**")
    L.append("")
    L.append("| 確認段 2021～2026（基準②） | 5 日 | 10 日 | 20 日 | 60 日 |")
    L.append("|---|---|---|---|---|")
    for tag in ("G1", "G3"):
        L.append(f"| {tag} 甲 互抵 | " + " | ".join(c(cf[H][tag]["X2 甲互抵"]) for H in HS) + " |")
        L.append(f"| {tag} 乙 扣 0.585% | " + " | ".join(c(cf[H][tag]["X2 乙對成本"]) for H in HS) + " |")
    L.append("| G3 − 只看多頭排列（同月配對） | " + " | ".join(c(cf[H]["G3 − C1 同月配對"]) for H in HS) + " |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append(f"  ・原件數字不逐位元重現（原件是 09-18 分支快照、無 gate3）：本快照原件式 20 日全期 G1 {p(S['量級對照（原件式、本快照、訊號 2016-01～2026-07）']['G1']['超額'])}（原件 +1.87%）、"
             f"G3 {p(S['量級對照（原件式、本快照、訊號 2016-01～2026-07）']['G3']['超額'])}（原件 +2.57%）")
    L.append("  ・早年只上市（早年版面沒有上櫃）；早年月營收來自 data/early/revenue")
    L.append("  ・停止交易強制出場：開（原件 hold_exit：到期日沒收盤或跌停鎖死順延 ≤ 10 日、仍不行用窗內最後收盤）；段內整筆 ⇒ 沒有資料尾截斷")
    L.append(f"  ・「穩」：G1 {'是' if S['穩_G1（確認段四個 H × 兩口徑 × 基準② 同結果）'] else '否'}（5、10 日扣成本分不出）；G3 {'是' if S['穩_G3（確認段四個 H × 兩口徑 × 基準② 同結果）'] else '否'}（確認段四個 H × 兩口徑 × 基準② 全好）"
             "，⛔ 但早年樣本外 G3 20 日分不出 ⇒ G3 的「穩」只限 2016～2026")
    L.append("```")
    L.append("")
    for sn in SEGS:
        L.append(f"## {sn}")
        L.append("")
        L.append("| 量 | " + " | ".join(f"{H} 日" for H in HS) + " |")
        L.append("|---|" + "---|" * 4)
        for tag in ("G1", "G3", "C1（描述）"):
            for k in ("X1 甲互抵", "X1 乙對成本", "X2 甲互抵", "X2 乙對成本"):
                L.append(f"| {tag} {k}（n） | " + " | ".join(f"{c(R[f'{sn}｜H{H}'][tag][k])}（{R[f'{sn}｜H{H}'][tag]['n']:,}）" for H in HS) + " |")
        L.append("| G3 − C1 同月配對 | " + " | ".join(c(R[f"{sn}｜H{H}"].get("G3 − C1 同月配對", {})) for H in HS) + " |")
        L.append("| 同月隨機 p（G1／G3；隨機 ≥ 真） | " + " | ".join(
            f"{R[f'{sn}｜H{H}']['G1']['同月隨機']['p（隨機 ≥ 真）']:.3f}／{R[f'{sn}｜H{H}']['G3']['同月隨機']['p（隨機 ≥ 真）']:.3f}" for H in HS) + " |")
        b = R[f"{sn}｜H20"]["下市月營收下界"]
        L.append("")
        L.append(f"下市月營收下界（20 日；缺營收的閘門列 {b['缺營收列']:,}，其中已下市 {b['其中已下市']:,}；照 P4 全部當成訊號、代入邊界值）："
                 f"G1 −100％ {c(b['G1 下界 −100％（X1 甲）'])}、0％ {c(b['G1 下界 0％（X1 甲）'])}｜G3 −100％ {c(b['G3 下界 −100％（X1 甲）'])}、0％ {c(b['G3 下界 0％（X1 甲）'])}"
                 "（⛔ 最壞情境、非估計值）")
        L.append("")
    L.append("## 閘與查核")
    L.append("")
    if CK:
        L.append(f"- 獨立查核 `researchAudit2_5_check.py`（⛔ 不 import 主程式、research34、evaluate、patterns、avgdown）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a not in ("過", "不符")))
    L.append("")
    L.append("## 檔案")
    L.append("")
    L.append("`backtest/researchAudit2_5.py`、`researchAudit2_5_check.py`、`researchAudit2_5_report.py`；resultsAudit2/5/：summary.json、panel_main.csv.gz、panel_early.csv.gz、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:16]))


if __name__ == "__main__":
    main()
