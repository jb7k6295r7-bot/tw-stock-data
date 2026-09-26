# -*- coding: utf-8 -*-
"""USREG-W1b 本體報告：body_summary.json＋body_check.json＋pre_summary.json ⇒ resultsUSW1b/BODY_REPORT.md（⛔ 只有彙總）。"""
import os, json

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSW1b")
S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
C = json.load(open(os.path.join(OUT, "body_check.json"), encoding="utf-8"))
P = json.load(open(os.path.join(OUT, "pre_summary.json"), encoding="utf-8"))
pc = lambda x: "{:+.2f}%".format(x * 100)
B = S["基準"]; M = S["臂"]["main"]
L = []; A = L.append
A("# USREG-W1b 本體交件：季營收創近 8 季新高 ∧ ¬ma_stack ∧ ma60_up（美股，組合層）\n")
A("| 欄 | 值 |\n|---|---|")
A("| 判準 | 美股登錄 seq2 §五＋seq3 §四＋seq4 §二§三＋seq5 §一～§三；裁定 seq168 §三、seq176 §二、seq182、seq214 §三；判準 ＝ 台股 seq141 同形，對 ^SP500TR 同窗 |")
A("| 讀法定案 | ① 營收新高用對稱容差 1e-4（台股 rev_hi24 先例）② 特徵回看窗或持有期跨轉接層斷點 ⇒ 剔除；兩處另跑敏感度（精確 ≥、保留跨斷點） |")
A("| 引擎 | research11.simulate_mtm（未改）：H120、8 槽、pick＝None、d_max＝None、queue 0、cash_mode zero、tradable＋delist on（美股無漲跌停）；成本 0.05% 來回；種子 default_rng(102000＋r)×{} |".format(S["種子數"]))
A("| 資料 | us-stock-data `{}`；判定窗 {}～{}；ANN {}；訊號表 {} |".format(S["資料commit"], S["判定窗"][0], S["判定窗"][1], S["ANN"],
  "、".join("{} {:,}".format(k, v) for k, v in S["訊號表筆數"].items())))
A("| 程式 | `backtest/researchUSW1b.py`、`researchUSW1b_check.py`（獨立路，不 import 主程式）、`researchUSW1b_report.py`；pre 見 PRE_REPORT.md |")
A("| 授權 | 權益曲線、逐月面板、訊號表、逐顆彙總、成交紀錄都在 `~/us_work/usw1b/`（repo 外），sha 見 `work_sha.csv`；本資料夾只有彙總 |\n")
A("## 〇、結論\n\n```")
A("判定（主臂，200 顆中位 對 ^SP500TR 同窗）：【{}】".format(M["標籤"]))
A("  年化中位 {}（基準 {}）｜回落中位 {}（基準 {}）｜比值 {:.3f}（基準 {:.3f}）".format(pc(M["年化中位"]), pc(B["SP500TR"]["年化"]), pc(M["回落中位"]), pc(B["SP500TR"]["回落"]), M["比值"], M["基準比值"]))
A("  條件一（年化中位 ＞ 基準）：{}；條件二（比值 ≥ 基準比值）：{}".format("成立" if M["年化中位"] > B["SP500TR"]["年化"] else "不成立", "成立" if M["比值"] >= M["基準比值"] else "不成立"))
A("⚠ 窗首 2016-01-04～{} 依構造空手（面板最早 2015-12-01，湊滿 120 根 K 棒前沒有候選）".format(S["第一個進場日"]))
A("⚠ 缺價的 35 檔（含倒閉銀行）不在母體 ⇒ 偏向存活股；不適用 19 檔不進候選")
A("⚠ 限制（seq2 §五）：窗 2016 起、無更早驗收段 ⇒ 即使合格也只算候選，須以 2026-09 後資料前瞻再驗")
A("```\n")
A("## 一、各臂（⛔ 只有 main 進判定；其餘描述）\n")
A("| 臂 | 年化中位（p10～p90） | 回落中位（p10～p90） | 比值 | 基準 年化／回落／比值 | 標籤 | 逐種子 合格／另列／不合格 | 交易數中位 | 槽位使用率 |")
A("|---|---|---|---:|---|---|---|---:|---:|")
for k, v in S["臂"].items():
    b = B["SP500TR_扣30%股息（描述）"] if k == "div_net30" else B["SP500TR"]
    s = v["逐種子標籤比例"]
    A("| {} | {}（{}～{}） | {}（{}～{}） | {:.3f} | {}／{}／{:.3f} | {} | {:.0%}／{:.0%}／{:.0%} | {:.0f} | {:.1%} |".format(
        k, pc(v["年化中位"]), pc(v["年化p10"]), pc(v["年化p90"]), pc(v["回落中位"]), pc(v["回落p10"]), pc(v["回落p90"]), v["比值"],
        pc(b["年化"]), pc(b["回落"]), b["比值"], v["標籤"], s["合格"], s["另列"], s["不合格"], v["交易數中位"], v["槽位使用率中位"]))
A("\n```")
m, e, kp = S["臂"]["main"], S["臂"]["exact"], S["臂"]["keep_pb"]
A("敏感度①（營收新高精確 ≥）：標籤 {}→{}；年化中位差 {:+.4f}pp、回落中位差 {:+.4f}pp".format(m["標籤"], e["標籤"], (e["年化中位"] - m["年化中位"]) * 100, (e["回落中位"] - m["回落中位"]) * 100))
A("敏感度②（保留跨斷點的訊號）：標籤 {}→{}；年化中位差 {:+.4f}pp、回落中位差 {:+.4f}pp".format(m["標籤"], kp["標籤"], (kp["年化中位"] - m["年化中位"]) * 100, (kp["回落中位"] - m["回落中位"]) * 100))
ae = [k for k in m if k.startswith("標籤_ANN實際")][0]
A("年化分母：ANN 245 ⇒ {}；{} ⇒ {}（主臂標籤不隨 ANN 變：{}）".format(m["標籤_ANN245"], ae.replace("標籤_", ""), m[ae], "是" if m["標籤_ANN245"] == m["標籤"] == m[ae] else "否"))
A("從第一個進場日（{}）起算（描述）：年化中位 {}、回落中位 {}（基準 {}／{}）⇒ {}".format(S["第一個進場日"], pc(m["自第一個進場日_年化中位"]), pc(m["自第一個進場日_回落中位"]),
  pc(B["SP500TR"]["自第一個進場日_年化"]), pc(B["SP500TR"]["自第一個進場日_回落"]), m["自第一個進場日_標籤（描述）"]))
A("SPY 還原價備援（描述）：年化 {}、回落 {}".format(pc(B["SPY備援（描述）"]["年化"]), pc(B["SPY備援（描述）"]["回落"])))
A("下市了結中位 {:.0f}、下市不明中位 {:.0f}、進場日無 K 棒（名額持現金）中位 {:.0f}、出場延後中位 {:.0f}".format(m["下市了結中位"], m["下市不明中位"], m["進場日無K棒（名額持現金）中位"], m["出場延後中位"]))
A("```\n")
A("## 二、pre 要點（PRE_REPORT.md）\n\n```")
A("候選股-月 {:,}｜訊號 {:,}｜每月訊號中位 {:.0f}、≥ 8 檔月份 {:.0%}".format(P["候選（在指數∧bars∧營收）股月"], P["訊號（再∧¬ma_stack∧ma60_up）股月"],
  P["每月訊號數（窗內）"]["中位"], P["每月訊號數（窗內）"]["≥8的月比例"]))
k = P["Z5_描述臂_曆季逐字會被踢出"]
A("描述臂 曆季逐字會被踢出：營收新高股-月 {:,}（{} 檔），其中訊號 {:,}".format(k["在指數且bars_ok且營收新高的股月"], k["檔數"], k["其中也過技術條件（訊號）"]))
A("value ≤ 0：{} 列／{} 檔；不適用 {} 檔；倒閉銀行依構造不可能被選到".format(P["Z5_value≤0"]["列數"], P["Z5_value≤0"]["檔數"], len(P["Z5_不適用19檔"])))
A("```\n")
A("## 三、硬性查核\n\n```")
A("fixture FW1～FW3 全過（pre）")
A("獨立路（researchUSW1b_check.py，不 import 主程式；直接讀快照 CSV 與 repo 外逐顆彙總）：")
A("  ① 基準（^SP500TR、扣 30% 版）自算最大差 {:.1e}".format(C["①基準"]["最大差"]))
A("  ② 各臂中位與標籤：最大差 {:.1e}、標籤全同 {}".format(C["②各臂中位與標籤"]["最大差"], C["②各臂中位與標籤"]["標籤全同且種子數對"]))
c3 = C["③種子102000"]
A("  ③ 種子 102000：窗內年化／回落差 {:.1e}｜成交紀錄重建現金與權益末值差 {:.1e}（買 {}、賣 {}）｜抽 {} 筆成交價最大相對差 {:.1e}".format(
    c3["窗內年化回落差"], c3["成交紀錄重建現金與權益末值差"], c3["買筆數"], c3["賣筆數"], c3["抽查成交價筆數"], c3["成交價最大相對差"]))
A("  ④ 訊號面板抽 {} 列（營收新高、ma_stack、ma60_up、bars、在指數）不符：{}".format(C["④訊號面板"]["抽查列"], C["④訊號面板"]["不符"]))
A("  ⇒ " + ("全部通過" if C["全部通過"] else "⛔ 有不符"))
A("⛔ 未 commit、未 push、未派 workflow")
A("```")
open(os.path.join(OUT, "BODY_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("寫出 BODY_REPORT.md（{} 行）".format(len(L)))
