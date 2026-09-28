# -*- coding: utf-8 -*-
"""PREREG季節性 seq1：由 resultsSeason/ 產 REPORT.md（只讀檔，不重算）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchSeason_report.py
"""
from __future__ import annotations
import json, os
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsSeason")
ONE = ("**營量 v1**：挑中「丙：1～2 月整組換 0050」。確認段 +37.92%／−32.93%，比原策略（+31.67%／−30.84%）多 +6.26 點、回落深 2.09 點；"
       "但以年為單位（5 個年初）的差 CI〔−2.08%, +11.60%〕含 0 ⇒ **測不出**，⛔ 不寫「多賺」；假訊號 p 0.102 ⇒ 隨便挑一段月份也做得到。"
       "早年段只有 2 個年初 ⇒ 依構造不可判定（點值少賺 4.25 點）⇒ 件句 **「不必避開」**。"
       "**營飆 v1**：原策略在探索段 1～3 月實際新進場最多 13 筆（＜ 20），9 格全部退化 ⇒ **依構造不可判定**、不計 N。")


def P(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.{d}f}%"


def pp(x):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.2f} 點"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    J = S["判定"]; Z = S["0050"]
    L = []; w = L.append
    w("# PREREG季節性 seq1 REPORT（回測 研究季節性）\n")
    w("> 回測線，2026-09-28。登錄：台股策略線 季節性 seq1（sha 8b763863d5b15258）；裁定 seq256 §一 發號、§二 2（年為單位 CI）、seq262 §四 4（照原登錄開跑）；N ＋2（營量、營飆各 1 格）。\n")
    w("## 一句話\n")
    w(ONE + "\n")
    w("| 策略 | 挑中格 | 確認 2022–2026-08：比原策略（年化差／回落差） | 年為單位 CI | 早年 2012-06～2014 | 件句 |")
    w("|---|---|---|---|---|---|")
    for s, v in J.items():
        if "確認" not in v:
            w(f"| {s} | {v['格']} | — | — | — | {v['件句']} |"); continue
        c, e = v["確認"], v["早年"]
        w(f"| {s} | {v['格']} | {pp(c['年化差中位'])}／{pp(c['回落差中位'])}（{P(c['年化中位'])}／{P(c['回落中位'])} {c['標籤']}；原策略 {P(c['原策略']['年化中位'])}／{P(c['原策略']['回落中位'])}） | "
          f"年初 {int(c['年初個數'])} 個：〔{P(c['年CI下'])}, {P(c['年CI上'])}〕 {c['年判定']} | {pp(e['年化差中位'])}；{e['年判定']} | {v['件句']} |")
    w(f"\n0050：" + "；".join(f"{k} {P(v['年化'])}／{P(v['回落'])}" for k, v in Z.items()) + "\n")
    w("## 一、設定\n")
    w("- 本體一字不改：營飆 v1 ＝ researchT1fix #1（T1、t−1 大盤閘、H120 N10、種子 1000＋r）；營量 v1 ＝ #13（T1、H60 N20 relvol、種子 7000＋r）；兩者停止交易強制出場：開；200 顆")
    w("- 早年段 ＝ researchV 早年版面 2012-06-04～2014-12-31（登錄寫 2012-05～2016；早年訊號只到 2014，照 PREREGV 實際窗）＋ 強制出場")
    w("- 做法：甲 停買（M 內不進新股）｜乙 甲＋M 內閒置現金全抱 0050（M 後首日開盤賣、0050 來回 0.385%）｜丙 乙＋M 第一個交易日開盤把持股全賣（付 0.585%）、M 後照原規則重建")
    w("- 挑法：探索段（2017-03～2021-12）同顆配對「格年化 − 原策略年化」中位最高；K7：探索段 M 內原策略實際新進場 ＜ 20 筆（200 顆中位）的格不進挑選")
    w("- 判定（seq256 §二 2）：每個 1 月在段內的曆年，差 ＝ 200 顆平均（格當年報酬 − 原策略當年報酬）；bootstrap by year（B＝20,000）95% CI 下緣 ＞ 0 才寫「多賺」；年初 ＜ 3 個 ⇒ 依構造不可判定")
    w("- 資料尾：主窗 T1（截斷訊號補回、窗內以收盤計值）；早年 AND_mtm 同讀法\n")
    w("## 二、挑格候選（探索段）\n")
    for s, v in S["挑格"].items():
        w(f"**{s}** ⇒ {v['格']}\n")
        w("| 格 | 探索段配對年化差 | 比值 | M 內原策略進場（中位） | 退化 |")
        w("|---|---|---|---|---|")
        for c in v["候選"]:
            w(f"| {c['格']} | {pp(c['探索差'])} | {c['比值']:.2f} | {c['月份內原策略進場']:.0f} | {'是' if c['退化'] else ''} |")
        w("")
    w("## 三、全格（描述）\n")
    w("| 世界 | 策略 | 格 | 段 | 年化中位 | 回落中位 | 標籤 | 配對年化差 | 配對回落差 | 年初 | 年差平均 | 年 CI | 年判定 |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in T.to_dict("records"):
        ci = "" if pd.isna(r.get("年CI下")) else "〔" + P(r["年CI下"]) + ", " + P(r["年CI上"]) + "〕"
        w(f"| {r['世界']} | {r['策略']} | {r['格']} | {r['段']} | {P(r['年化中位'])} | {P(r['回落中位'])} | {r['標籤']} | {pp(r.get('年化差中位'))} | {pp(r.get('回落差中位'))} | "
          f"{'' if pd.isna(r.get('年初個數')) else int(r['年初個數'])} | {P(r.get('年差平均'))} | {ci} | {r.get('年判定') if isinstance(r.get('年判定'), str) else ''} |")
    w("\n## 四、挑中格：逐年差與假訊號\n")
    for s, v in J.items():
        if "確認" not in v:
            continue
        for sg in ("探索", "確認", "早年"):
            x = v[sg]
            w(f"- {s} {v['格']} {sg}：逐年差 {x['逐年差']}；假訊號 p（每年隨機一段同長度月份，1,000 次）{x['假訊號 p（隨機 ≥ 配對差中位）']:.3f}"
              + ("　⇒ 句前「隨便挑一段月份也做得到」" if x['假訊號 p（隨機 ≥ 配對差中位）'] >= 0.05 else ""))
    w("\n## 五、原策略各曆月平均報酬（描述；200 顆平均）\n")
    w("| 策略_段 | " + " | ".join(f"{m}月" for m in range(1, 13)) + " |")
    w("|---|" + "---|" * 12)
    for k, v in S["原策略各曆月平均報酬（200 顆平均）"].items():
        w(f"| {k} | " + " | ".join(P(v[str(m)]) for m in range(1, 13)) + " |")
    w("\n## 六、新規矩 ③ 出場敏感度（描述、不判）\n")
    sens = S.get("新規矩③ 出場敏感度（描述；各段 [年化中位, 回落中位]）")
    w(f"觸發：{S['新規矩③']}；{S.get('新規矩③ 註', '')}；提前出場筆數 {S.get('新規矩③ 提前出場筆數', {})}\n")
    if sens:
        w("| 變體 | 探索 | 確認 | 早年 |")
        w("|---|---|---|---|")
        for k, v in sens.items():
            w(f"| {k} | " + " | ".join((f"{P(v[sg][0])}／{P(v[sg][1])}" if sg in v else "—") for sg in ("探索", "確認", "早年")) + " |")
    w("\n## 七、閘與查核\n")
    w(f"- 閘：{S['閘']}")
    w(f"- 丙 1～3 月被切部位數：{S.get('丙 1～3月 被切部位數')}")
    if CK:
        for k, v in CK.items():
            if isinstance(v, dict):
                w(f"- 獨立查核 {k}：{'過' if v['過'] else '⛔ 不過'}（" + "；".join(f"{a}={b}" for a, b in v.items() if a != "過") + "）")
        w(f"- 獨立查核 researchSeason_check.py（⛔ 不 import 主程式）：{'全部過' if CK.get('全部過') else '⛔ 有不過'}")
    w("")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
