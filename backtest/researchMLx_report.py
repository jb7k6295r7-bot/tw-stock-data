# -*- coding: utf-8 -*-
"""PREREG機器學習改目標：由 resultsMLx/ 產 REPORT.md（只讀檔，不重算）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchMLx_report.py
"""
from __future__ import annotations
import json, os
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsMLx")


def P(x):
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    pk = S["挑格"]; Z = S["0050"]; V = S["持股 vol60 百分位（全窗平均；0.5 ＝ 當期中位）"]; fk = S["假訊號（同池隨機，挑中格頻率與 N）"]
    v1 = S["營量 v1（T1 版、stop_force 開、種子 0）"]
    yrs = S["挑中格各年（本格／0050）"]
    L = []; w = L.append
    w("# PREREG機器學習改目標 seq1 REPORT（回測 研究MLx）\n")
    w("> 回測線，2026-09-28。登錄：台股策略線 機器學習選股改目標 seq1（sha 168560f97763a287）；裁定 seq265 §二 發號、N ＋1。"
      "⚠ 登錄照實標「看過簡化版結果之後才設計」；⭐ 判定上限 ＝「確認段合格（無早年段）」⇒ 合格也只進前瞻紀錄、不進有效清單。\n")
    w("## 一句話\n")
    w(f"探索段挑中 **{pk['格']}**（目 A 超額數值、提升樹樁、季換、20 檔）：探索段 {P(pk['探索']['年化'])}／{P(pk['探索']['回落'])}，"
      f"其中 2021 一年 {P(yrs['2021'][0])}；確認段 {P(pk['確認']['年化'])}／{P(pk['確認']['回落'])}，對 0050（{P(Z['確認']['年化'])}／{P(Z['確認']['回落'])}）"
      f"年化差 {100 * (pk['確認']['年化'] - Z['確認']['年化']):+.2f} 點 ⇒ **確認段不合格**。"
      f"低波動傾向已改掉：持股 60 日波動百分位 {V['挑中格']:.2f}（簡化版挑中格 {V['簡化版挑中格 RIDGE_月_N20']:.2f}）。"
      f"同池隨機 p：確認段 {fk['確認']['p（隨機年化 ≥ 本格）']:.3f}，所以排序本身有用，只是扣成本後沒贏 0050。\n")
    w("| 格 | 探索 2019–2021 | 確認 2022–2026-08 | 確認標籤 |")
    w("|---|---|---|---|")
    w(f"| 挑中 {pk['格']} | {P(pk['探索']['年化'])}／{P(pk['探索']['回落'])} | {P(pk['確認']['年化'])}／{P(pk['確認']['回落'])} | {pk['確認']['標籤']} |")
    w(f"| 0050 | {P(Z['探索']['年化'])}／{P(Z['探索']['回落'])} | {P(Z['確認']['年化'])}／{P(Z['確認']['回落'])} | — |")
    lite = S["簡化版同頻率同 N（resultsMLlite）"]
    if isinstance(lite, dict):
        for m in ("RIDGE", "STUMP"):
            k = [x for x in lite if x.startswith(m)]
            if k:
                e_ = lite[f"{k[0].rsplit('_', 1)[0]}_探索"]; c_ = lite[f"{k[0].rsplit('_', 1)[0]}_確認"]
                w(f"| 簡化版 {k[0].rsplit('_', 1)[0]} | {P(e_[0])}／{P(e_[1])} | {P(c_[0])}／{P(c_[1])} | {c_[2]} |")
    if isinstance(v1, dict):
        w(f"| 營量 v1（T1、種子 0） | {P(v1['探索']['年化'])}／{P(v1['探索']['回落'])} | {P(v1['確認']['年化'])}／{P(v1['確認']['回落'])} | — |")
    w(f"| 同池隨機 1,000 次（中位） | {P(fk['探索']['隨機年化中位'])} | {P(fk['確認']['隨機年化中位'])} | p 探索 {fk['探索']['p（隨機年化 ≥ 本格）']:.3f}／確認 {fk['確認']['p（隨機年化 ≥ 本格）']:.3f} |")
    w("")
    w("## 一、設定（照登錄寫死）\n")
    w(f"- 特徵：researchMLlite（1ed9de081e）同一版；閘 ①：月、季資料集與簡化版 dataset 逐位元相同（{S['閘']['① 月季資料集 ＝ resultsMLlite dataset（x_ 欄、ret、sid、e 逐位元）']}）；資料集 {S['資料集']['列']}，訓練起點 {S['資料集']['訓練起點']}")
    w("- 目標：A ＝ 下期報酬 − 0050 同期，1%／99% 截尾、不排名｜B ＝ 下期前 20% ＝ 1｜C ＝ 下期報酬排名，選股時依 60 日波動分五組、各取 N÷5")
    w("- 模型：嶺迴歸 α {1, 10, 100}｜提升樹樁 輪數 {50, 100, 200}、學習率 0.1、每葉 ≥ 200、切點 0.1…0.9；目 B 對數損失；驗證段 2018 以 IC（對實際下期報酬）選 1 組；2019 起每年重訓")
    w("- 組合：前 N 等權換股簿（續抱、強制出場：開、下市了結）；窗尾照市值 ⇒ 依構造不截斷；目標期跨資料尾的列不進訓練")
    w("- 退化（探索段平均持股 ＜ N÷2 或現金 ＞ 30%）：" + ("、".join(pk["退化排除"]) if pk["退化排除"] else "0 格") + f"；探索段過判準 {pk['探索過判準格數']} 格 ⇒ 取比值最高\n")
    w("## 二、驗證段選參\n")
    w("| 目標_頻率 | α（驗證 IC） | 輪數（驗證 IC） |")
    w("|---|---|---|")
    for k, v in S["模型"].items():
        w(f"| {k} | {v['α']:g}（" + "、".join(f"{a}: {b:+.3f}" for a, b in v["α 驗證 IC"].items()) + f"） | {v['輪數']}（" + "、".join(f"{a}: {b:+.3f}" for a, b in v["輪數 驗證 IC"].items()) + "） |")
    w("\n⚠ 目 B（大贏家）驗證段與確認段 IC 多為負：模型學到的「會變大贏家」偏高波動股，對平均報酬排序反而負相關（描述）。\n")
    w("## 三、36 格（描述；只有挑中格判定）\n")
    w("| 格 | 探索 年化／回落 | 確認 年化／回落 | 確認標籤 | 持股 vol60 百分位 | 確認 換手／成本每年 |")
    w("|---|---|---|---|---|---|")
    ex = T[T["段"] == "探索"].set_index("格"); cf = T[T["段"] == "確認"].set_index("格")
    for k in ex.index:
        w(f"| {k} | {P(ex.loc[k, '年化'])}／{P(ex.loc[k, '回落'])} | {P(cf.loc[k, '年化'])}／{P(cf.loc[k, '回落'])} | {cf.loc[k, '標籤']} | {ex.loc[k, 'vol60 百分位（全窗）']:.2f} | "
          f"{cf.loc[k, '換手']:.0%}／{cf.loc[k, '成本／年']:.2%} |")
    nq = int((cf["標籤"] == "合格").sum())
    w(f"\n⚠ 36 格中確認段事後看有 {nq} 格合格；那是看過確認段才挑得出來的，⛔ 不能拿來當結論（本件只判探索段挑中的那一格）。\n")
    w("## 四、必報\n")
    w(f"- 持股 60 日波動百分位（0.5 ＝ 當期中位）：挑中格 {V['挑中格']:.3f}；簡化版挑中格 RIDGE_月_N20 {V['簡化版挑中格 RIDGE_月_N20']:.3f} ⇒ {V['判讀']}")
    w("- 挑中格各年（本格／0050）：" + "；".join(f"{y} {P(a)}／{P(b)}" for y, (a, b) in yrs.items()))
    m = S["模型"][f"{pk['格'].split('_')[0]}_{pk['格'].split('_')[2]}"]
    w("- 特徵重要度前 10（樹樁增益）：" + "、".join(c for c, _ in m["樹樁 增益合計前 10"]) + "｜嶺迴歸 |係數|：" + "、".join(c for c, _ in m["嶺迴歸 |係數| 平均前 10"]))
    ic = S["樣本外 IC（對實際下期報酬）"]
    w("- 樣本外 IC（確認段平均）：" + "；".join(f"{k.replace('_確認', '')} {v['平均 IC']:+.3f}" for k, v in ic.items() if k.endswith("確認")))
    w(f"- 挑中格確認段：換手 {pk['確認']['換手']:.0%}、成本每年 {pk['確認']['成本／年']:.2%}、平均持股 {pk['確認']['平均持股']:.1f}")
    w(f"- 合成分數同格（確認段）：{S['合成分數同格（resultsScore 確認段）']}")
    w(f"- 新規矩 ③：{S['新規矩③ 出場敏感度（描述）']}\n")
    w("## 五、閘與查核\n")
    w(f"- 閘：{S['閘']}")
    if CK:
        for k, v in CK.items():
            if isinstance(v, dict):
                w(f"- 獨立查核 {k}：{'過' if v['過'] else '⛔ 不過'}（" + "；".join(f"{a}={b}" for a, b in v.items() if a != "過") + "）")
        w(f"- 獨立查核 researchMLx_check.py（⛔ 不 import 主程式、researchMLlite、researchMomX、research13）：{'全部過' if CK.get('全部過') else '⛔ 有不過'}")
    w("")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
