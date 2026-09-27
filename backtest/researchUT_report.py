# -*- coding: utf-8 -*-
"""PREREG上升趨勢線 報告：summary.json＋pre_freq.json＋check.json ⇒ backtest/resultsUT/REPORT.md（開頭一句結論＋小表）。"""
import os, json, math

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUT")
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
P = json.load(open(os.path.join(OUT, "pre_freq.json"), encoding="utf-8"))
C = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8"))
pc = lambda x, d=2: "—" if x is None or (isinstance(x, float) and not math.isfinite(x)) else "{:+.{}f}%".format(x * 100, d)
MAINK = "甲_R5_1%穿越"
J = S["格"][MAINK]; fk = S["假訊號臂（主格）"]; F0 = fk["新預設_只排除過去20日"]; F1 = fk["不排除（描述）"]
ctl = S["控制組_同T近60日上漲不看趨勢線（描述）"][MAINK]
L = []; A = L.append
A("# PREREG上升趨勢線 交件：上升趨勢線被跌破，之後 20 日真的比較會跌嗎？\n")
A("**結論：{}。**（主格 甲 兩點法 × R＝5 × 1% 穿越：{}、{}；平均 X {}，95% CI {} ～ {}，n＝{:,}）{}\n".format(
    J["判語"], J["出口"], J["結果"], pc(J["平均"]), pc(J["lo"]), pc(J["hi"]), J["n"], "" if J["警語"] == "無" else " " + J["警語"]))
A("| 量 | 主格 | 說明 |\n|---|---|---|")
A("| 平均 X〔95% CI 月分群〕 | {}〔{} ～ {}〕 | 非重疊 SE 欄 {} ～ {}；n_eff {}（{}） |".format(pc(J["平均"]), pc(J["lo"]), pc(J["hi"]), pc(J["lo_非重疊"]), pc(J["hi_非重疊"]), J["n_eff"], J["出口"]))
A("| 控制組差（同 T、近 60 日上漲、不看趨勢線） | {}〔{} ～ {}〕 | 描述；n＝{:,} |".format(pc(ctl["平均"]), pc(ctl["lo"]), pc(ctl["hi"]), ctl["n"]))
A("| 假訊號臂（新預設，30 次） | {}／30 CI 不含 0（＋{}／−{}） | 30 次平均 X {}；不排除版 {}／30（描述） |".format(F0["x／30"], F0["其中(+)"], F0["其中(−)"], pc(F0["30次平均X的平均"]), F1["x／30"]))
A("| 60 日（描述） | {}〔{} ～ {}〕 | n＝{:,}、n_eff {} |".format(pc(S["60日（描述）"][MAINK]["平均"]), pc(S["60日（描述）"][MAINK]["lo"]), pc(S["60日（描述）"][MAINK]["hi"]),
  S["60日（描述）"][MAINK]["n"], S["60日（描述）"][MAINK]["n_eff"]))
c3 = S["格"]["丙_R5_1%穿越"]
A("\n讀的時候要一起看（⛔ 描述，不改判定）：")
A("- 假訊號臂（同檔、只排除過去 20 日）30 次裡 CI 不含 0 的 {} 次**全是（＋）**、平均 X {} ⇒ 同一批股票隨便挑一天並不偏弱；主格的負值⛔ 不是「這些股票本來就弱」（與 PREREGM 丙 那種同月弱勢分不開的情形不同）。警語規則（主格結果③ 且 假訊號（−）≥ 2／30）⇒ {}。".format(
    F0["x／30"], pc(F0["30次平均X的平均"]), "不觸發" if J["警語"] == "無" else "觸發"))
A("- 控制組（同一天、近 60 日也在漲、但沒跌破的股票）差 {}〔{} ～ {}〕⇒ 跌破的比同樣在漲的更差。".format(pc(ctl["平均"]), pc(ctl["lo"]), pc(ctl["hi"])))
A("- 效果量小（−0.37% ／ 20 日）、60 日已不顯著（{}）；描述格裡 甲、乙 多數為負，⚠ 丙（回歸法）反而為正（{}〔{} ～ {}〕）⇒ 「跌破會跌」隨畫法而變，⛔ 只能引主格。".format(
    pc(S["60日（描述）"][MAINK]["平均"]), pc(c3["平均"]), pc(c3["lo"]), pc(c3["hi"])))
A("- 先驗（登錄 §五：主格分不出，或負但與同月弱勢分不開，押約七成）⇒ **沒押中**：主格負、而且同檔隨機日不負。")
A("- ⛔ 單筆層：不可說成組合層的賣出規則有用；要進組合層須另開一件。")
A("\n| 欄 | 值 |\n|---|---|")
A("| 判準 | 台股策略線 上升趨勢線跌破 登錄 seq1（sha ffac12dee65c6bf1）；裁定 seq225、seq226（N_前段 ＋1，只有主格判定） |")
A("| 資料 | main `{}` 快照、gate3 {:,} 檔（可用 {:,}）、主窗 {}～{}；還原 OHLC；成本 0.585% 來回 |".format(S["快照"], P["gate3母體"], S["可用檔數"], S["判定窗"][0], S["判定窗"][1]))
A("| 程式 | `backtest/trendline_ut.py`（trendline_m 的鏡像，trendline_m 未改）、`selftest_trendline_ut.py`、`researchUT.py`（pre＋本體）、`researchUT_check.py`（獨立路）、`researchUT_report.py` |")
A("| 輸出 | `backtest/resultsUT/`：REPORT.md、summary.json、pre_freq.json、check.json、events_X.csv.gz、pre_events.csv.gz、fake_arm.csv、run.log |\n")
A("## 一、18 格（⛔ 只有主格判定；其餘描述、⛔ 不印判定）\n")
A("| 格 | 保留 | 平均 X | 95% CI | n_eff | 每檔每年 |\n|---|---:|---:|---|---:|---:|")
for k, v in S["格"].items():
    A("| {}{} | {:,} | {} | {} ～ {} | {} | {:.2f} |".format("⭐ " if k == MAINK else "", k + ("（丙 不用樞紐，三個 R 相同）" if v.get("丙三個R相同") else ""),
      v["n"], pc(v["平均"]), pc(v["lo"]), pc(v["hi"]), v["n_eff"], P["格"][k]["每檔每年"]["合併比率"]))
A("\n## 二、主格必報（描述）\n\n```")
A("事件帳：" + "、".join("{} {:,}".format(k, v) for k, v in J["事件帳"].items()))
A("R_e 平均 {}、中位 {}；X 中位 {}、勝率 {:.1%}、最差 {}".format(pc(J["R_e平均"]), pc(J["R_e中位"]), pc(J["中位"]), J["勝率"], pc(J["最差"])))
A("逐年：" + "、".join("{} {}（{:,}）".format(y, pc(v["平均"]), v["n"]) for y, v in S["主格_逐年"].items()))
A("上市／上櫃：" + "、".join("{} {}〔{} ～ {}〕n＝{:,}".format(k, pc(v["平均"]), pc(v["lo"]), pc(v["hi"]), v["n"]) for k, v in S["主格_上市上櫃"].items()))
A("放棄組（主格事件依 乙 選取結果分組；乙「第三點偏離」＝ 放棄組）：" + "、".join("{} {}（{:,}）".format(k, pc(v["平均"]), v["n"]) for k, v in S["放棄組_乙三點驗證沒過（主格事件依乙選取分組，描述）"].items()))
v2 = S["V2_鏡像讀法_再剔除T+1開盤跌停（主格，描述）"]
A("讀法 V2 另一種（再剔除 T+1 開盤跌停，賣出訊號的鏡像）：n＝{:,}、平均 X {}〔{} ～ {}〕⇒ {}".format(v2["n"], pc(v2["平均"]), pc(v2["lo"]), pc(v2["hi"]), v2["結果（照同一判法，只描述）"]))
A("先驗（登錄 §五：主格分不出或負但與同月弱勢分不開，約七成）⇒ 主格 {}".format(J["結果"]))
A("```\n")
A("## 三、控制組、60 日（各格，描述）\n")
A("| 格 | 控制組差〔CI〕 | 60 日 X〔CI〕 |\n|---|---|---|")
for k, v in S["控制組_同T近60日上漲不看趨勢線（描述）"].items():
    c6 = S["60日（描述）"][k]
    A("| {} | {}〔{} ～ {}〕 | {}〔{} ～ {}〕 |".format(k, pc(v["平均"]), pc(v["lo"]), pc(v["hi"]), pc(c6["平均"]), pc(c6["lo"]), pc(c6["hi"])))
A("\n## 四、硬性查核\n\n```")
A("fixture trendline_ut G1～G7 全過（含 ⭐ 鏡像對稱：反射價格後 close 版 甲乙丙 與 trendline_m 逐筆相同；前視突變；鑑別力）")
A("獨立路（researchUT_check.py，不 import 主程式與偵測器）：① R_e {} 筆最大差 {:.1e}、基準 {} 天最大差 {:.1e}｜② 幾何 {}／{}｜③ {} 格重算最大差 {:.1e}、筆數區段 n_eff 相同 {} ⇒ {}".format(
    C["①R_e與基準"]["R_e筆數"], C["①R_e與基準"]["R_e最大差"], C["①R_e與基準"]["基準天數"], C["①R_e與基準"]["基準最大差"],
    C["②幾何"]["通過"], C["②幾何"]["抽"], C["③格重算"]["格數"], C["③格重算"]["最大差"], C["③格重算"]["筆數區段n_eff相同"], "全部通過" if C["全部通過"] else "⛔ 有不符"))
A("⛔ 未 commit、未 push、未派 workflow")
A("```\n")
A("## 五、讀法（researchUT.py V1～V10、trendline_ut.py N1～N8；⛔ 看報酬前寫死）\n")
A("- V2 T+1 開盤可成交剔除：照登錄「同 PREREGM」字面剔除【開盤漲停】；賣出訊號的鏡像（開盤跌停）只報件數與主格 X（見 §二）。")
A("- V4 丙 不用樞紐 ⇒ R3／R5／R10 三格事件相同，照登錄 18 格全報、逐格註明。")
A("- V6 控制組：同一 T（⊂ 同月）、近 60 日報酬 ＞ 0、該格當日無原始跌破、T+1 可成交、無斷點。")
A("- N8 1% 穿越 ＝ c(T) ＜ 0.99ℓ(T) ∧ c(T−1) ≥ 0.99ℓ(T−1)；3 日 3% ＝ 穿越日 t 起連 3 日收盤 ＜ ℓ、第 3 日 ＜ 0.97ℓ（researchM B10 的鏡像）。")
open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("寫出 REPORT.md（{} 行）".format(len(L)))
