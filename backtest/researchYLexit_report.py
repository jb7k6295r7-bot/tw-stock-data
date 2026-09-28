# -*- coding: utf-8 -*-
"""PREREG營量出場 seq1：由 resultsYLexit/ 產 REPORT.md（只讀檔，不重算）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchYLexit_report.py
"""
from __future__ import annotations
import json, os
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsYLexit")
EXTRA = ("兩件都 **沒有比營量 v1 好**。"
         "甲件：同一筆持有內、把一樣多、一樣長的暫出區間隨機擺 200 次，**每一次都比照規則做的好**（假訊號 p ＝ 1.000）"
         "⇒ 「跌破就賣、站回再買」的時點本身吃虧（賣在低點、買回在較高處，暫出期間該股平均還漲 1.5～3%（挑中格 +2.1%））；"
         "確認段 9 格中 4 格配對差 CI 整段 ＜ 0（描述）。"
         "乙件：確認段年化只比 0050 少 0.14 點、早年段合格，但對營量 v1 的配對差分不出、確認段點值略差、早年略好。")


def P(x):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.2f}%"


def pp(x):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.2f} 點"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    PT = pd.read_csv(os.path.join(OUT, "cells.csv"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    J = S["判定"]; Z = S["0050"]; v1 = PT.set_index("格").loc["營量v1"]
    L = []; w = L.append
    w("# PREREG營量出場 seq1 REPORT（回測 研究營量出場）\n")
    w("> 回測線，2026-09-28。登錄：台股策略線 營量 v1 出場兩件 seq1（sha 1a73bbae1829ca85）；裁定 seq266 §二 發號、N ＋2；使用者主動要的兩件。"
      "⛔ 就算好過營量 v1 也不取代它，只進前瞻紀錄並列。\n")
    w("## 一句話\n")
    s_ = []
    for fam, nm in (("甲", "跌破成本暫出、站回再進"), ("乙", "續抱確認")):
        j = J[fam]
        s_.append(f"**{fam}（{nm}）** 挑中 {j['挑中']}：確認段 {P(j['確認_年化'])}／{P(j['確認_回落'])}、早年 {P(j['早年_年化'])}／{P(j['早年_回落'])} ⇒ 件標籤 **{j['件標籤']}**；"
                  f"對營量 v1：**{j['對營量v1']}**（確認段配對差年化 {P(j['確認_配對差年化'])}〔{P(j['確認_配對差lo'])}, {P(j['確認_配對差hi'])}〕、早年 {P(j['早年_配對差年化'])}）")
    w("。".join(s_) + "。" + EXTRA)
    w(f"\n> ⚠ 先驗提醒（裁定 seq266 §二）：{S['先驗提醒']}。\n")
    w("| | 探索 2017-03～2021 | 確認 2022～2026-08 | 早年 2012-06～2014（只上市） |")
    w("|---|---|---|---|")
    for nm in (J["甲"]["挑中"], J["乙"]["挑中"], "營量v1"):
        r = PT.set_index("格").loc[nm]
        w(f"| {nm} | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} {r['確認_標籤']} | {P(r['早年_年化'])}／{P(r['早年_回落'])} {r['早年_標籤']} |")
    w(f"| 0050 | {P(Z['探索']['cagr'])}／{P(Z['探索']['mdd'])} | {P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])} | {P(Z['早年']['cagr'])}／{P(Z['早年']['mdd'])} |")
    w("")
    w("## 一、設定（照登錄；本線讀法見程式 docstring X1～X10）\n")
    w("- 營量 v1 ＝ T1 版（rerun17.setup_and(t1=True)）、20 檔、relvol、停止交易強制出場：開；200 顆；早年 ＝ 早年版面 2012-06-04～2014-12-31（只上市）")
    w("- 甲：收盤 ＜ 進場價×(1−b) ⇒ 隔日開盤賣；暫出中收盤 ≥ 進場價 ⇒ 隔日開盤買回；名額保留、錢閒置；第 H 天收盤結束｜b {0, 3, 5%} × H {40, 60, 80}")
    w("  - 實作：逐筆合成價格序列＋共用引擎新開關 held_map（預設關、逐位元不變；閘見 ENGINE_GATE.md）；每趟暫出再進扣一趟來回 0.585%")
    w("- 乙：第 k 天收盤當固定基準、之後收盤跌破隔日開盤賣，上限 C 天｜k {50, 55, 60} × C {120, 250}；只改每筆出場日，引擎不動")
    w("  - 資料尾：第 C 天超過資料末日 ⇒ 窗內照市值（T1 讀法），筆數見 §四")
    w("- 挑格：探索段先合格、再比值；退化（平均持股 ＜ 10，乙另加現金 ＞ 30%）：" + ("、".join(S["退化（挑前排除）"]) if S["退化（挑前排除）"] else "0 格"))
    w("- 判定：確認、早年兩段各對 0050 同段，取較嚴；主比較對營量 v1 同段同顆配對（日報酬差 200 顆平均、曆月 CR0、95% CI ×245）\n")
    w("## 二、15 格＋營量 v1（200 顆中位）\n")
    w("| 格 | 探索 年化／回落（比值） | 確認 年化／回落 | 確認標籤 | 確認配對差〔CI〕 | 早年 年化／回落 | 早年標籤 | 早年配對差 | 探索持股／現金 | 甲閒置（確認） |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for r in PT[PT["格"].str.startswith("營量")].to_dict("records"):
        idle = "" if pd.isna(r.get("確認_閒置")) else format(r["確認_閒置"], ".0%")
        cd = "" if r["格"] == "營量v1" else f"{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕"
        w(f"| {r['格']}{'（退化）' if r['退化'] else ''} | {P(r['探索_年化'])}／{P(r['探索_回落'])}（{r['探索_比值']:.2f}） | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | {cd} | "
          f"{P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | {'' if r['格'] == '營量v1' else P(r['早年_配對差年化'])} | {r['探索_持股']:.1f}／{r['探索_現金']:.0%} | "
          f"{idle} |")
    w("\n## 三、甲件另報：營飆 v1（H120，只描述、不判、不計 N）\n")
    w("| 格 | 探索 | 確認 | 早年 |")
    w("|---|---|---|---|")
    for r in PT[PT["格"].str.startswith("營飆")].to_dict("records"):
        w(f"| {r['格']} | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {P(r['早年_年化'])}／{P(r['早年_回落'])} |")
    w("\n## 四、必報（路徑、資料尾）\n")
    for k, v in S["路徑必報"].items():
        w(f"- {k}：" + "；".join(f"{a}={(f'{b:.3f}' if isinstance(b, float) else b)}" for a, b in v.items()))
    w("\n## 五、假訊號與挪起點（挑中格）\n")
    for fam in ("甲", "乙"):
        j = J[fam]
        w(f"- {fam} {j['挑中']} 假訊號（{'同筆內隨機放相同個數與長度的暫出區間' if fam == '甲' else '基準日 k 改為每筆 40～60 隨機'}，200 次）：" +
          "；".join(f"{sg} p {v['p（假年化 ≥ 本格年化中位）']:.3f}（假年化中位 {P(v['假年化中位'])}）" for sg, v in j["假訊號"].items()))
        w(f"- {fam} 挪起點（本格／營量 v1 年化中位）：" + "；".join(f"{k} {P(v[0])}／{P(v[1])}" for k, v in j["挪起點（本格年化、營量年化、本格回落、營量回落 中位）"].items()))
    w("\n## 六、新規矩 ③\n")
    for fam in ("甲", "乙"):
        w(f"- {fam}：{J[fam]['新規矩③']}")
    sens = S.get("新規矩③ 出場敏感度（描述；各段 [年化中位, 回落中位]）")
    if sens:
        w("\n| 格｜變體 | 探索 | 確認 | 早年 |")
        w("|---|---|---|---|")
        for k, v in sens.items():
            w(f"| {k} | " + " | ".join((f"{P(v[sg][0])}／{P(v[sg][1])}" if sg in v else "—") for sg in ("探索", "確認", "早年")) + " |")
    w("\n## 七、閘與查核\n")
    w(f"- 閘：{S['閘']}")
    w("- 現實版（滑價 C1～C5）：甲的合成路徑內暫出再進沒有逐筆滑價模型 ⇒ 本件不做（照寫）")
    if CK:
        for k, v in CK.items():
            if isinstance(v, dict):
                w(f"- 獨立查核 {k}：{'過' if v['過'] else '⛔ 不過'}（" + "；".join(f"{a}={b}" for a, b in v.items() if a != "過") + "）")
        w(f"- 獨立查核 researchYLexit_check.py（⛔ 不 import 主程式）：{'全部過' if CK.get('全部過') else '⛔ 有不過'}")
    w("")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
