# -*- coding: utf-8 -*-
"""PREREG滑價 REPORT.md 產生器（只讀 resultsSlip/；⛔ 不重算）。"""
from __future__ import annotations
import json, os
import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsSlip")


def p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def q(x, d=1):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary_main.json"), encoding="utf-8"))
    SE = json.load(open(os.path.join(OUT, "summary_early.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "summary_early.json")) else None
    T = pd.read_csv(os.path.join(OUT, "table_main.csv"))
    TE = pd.read_csv(os.path.join(OUT, "table_early.csv")) if os.path.exists(os.path.join(OUT, "table_early.csv")) else None
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    Z = S["0050"]; BE = S["損益兩平"]
    REAL = "現實版（C1 0.3%＋C2 50 萬＋C3＋C4）"; REAL5 = "現實版＋C5 低消 20 元"; ORIG = "原件（stop_force 關）"; BASE = "基準（stop_force 開）"

    def row(strat, arm, tab=T):
        return tab[(tab["策略"] == strat) & (tab["臂"] == arm)].iloc[0]
    sent = []
    for st in ("營量 v1", "營飆 v1"):
        o, r = row(st, ORIG), row(st, REAL)
        chg = "不變" if o["主窗_標籤"] == r["主窗_標籤"] else f"{o['主窗_標籤']}→{r['主窗_標籤']}"
        sent.append(f"{st} 現實版主窗 {p(r['主窗_年化'])}（原 {p(o['主窗_年化'])}，少 {r['比原回測少（點，主窗）']:.2f} 點；標籤{chg}）")
    L = ["# PREREG滑價 seq1：營量 v1／營飆 v1 的滑價與流動性敏感度（敏感度、N 不加）", ""]
    L.append(f"**結論：{'；'.join(sent)}；損益兩平額外單邊成本 營量 {q(BE['營量 v1']['損益兩平額外單邊成本_比值跌到0050以下'], 2)}（比值）／{q(BE['營量 v1']['損益兩平額外單邊成本_年化跌到0050以下'], 2)}（年化）、"
             f"營飆 {q(BE['營飆 v1']['損益兩平額外單邊成本_比值跌到0050以下'], 2)}／{q(BE['營飆 v1']['損益兩平額外單邊成本_年化跌到0050以下'], 2)}。**")
    L.append("")
    L.append("| 策略 | 版 | 主窗 年化／回落（比值） | 標籤 | 探索段 | 確認段 | 比原回測少 |")
    L.append("|---|---|---|---|---|---|---|")
    for st in ("營量 v1", "營飆 v1"):
        for arm in (ORIG, BASE, REAL, REAL5):
            x = row(st, arm)
            L.append(f"| {st} | {arm} | {p(x['主窗_年化'])}／{p(x['主窗_回落'])}（{x['主窗_比值']:.3f}） | {x['主窗_標籤']} | {p(x['探索_年化'])}／{p(x['探索_回落'])}（{x['探索_標籤']}） | "
                     f"{p(x['確認_年化'])}／{p(x['確認_回落'])}（{x['確認_標籤']}） | {x['比原回測少（點，主窗）']:+.2f} 點 |")
    L.append(f"| 0050 | — | {p(Z['主窗'][0])}／{p(Z['主窗'][1])}（{Z['主窗'][0] / abs(Z['主窗'][1]):.3f}） | — | {p(Z['探索'][0])}／{p(Z['探索'][1])} | {p(Z['確認'][0])}／{p(Z['確認'][1])} | — |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    for t in S["標註"]:
        L.append(f"  ・{t}")
    L.append("  ・敏感度：策略本體一字不改、N 不加；「原件」＝ stop_force 關、無任何臂（閘：逐位元重現原件逐種子檔）")
    L.append("  ・營量只跑 r＝0（relvol 排序不抽籤 ⇒ 200 顆完全相同）；營飆 200 顆中位")
    L.append("  ・C1 成本在出場時以進場金額一次扣（引擎既有口徑）；C2 衝擊在出場時一次反映於該筆報酬（持有期間市值照原價）")
    L.append("```")
    L.append("")
    L.append("## 一、全部臂（主窗與兩段）")
    L.append("")
    L.append("| 策略 | 臂 | 主窗 年化／回落／比值 | 主窗標籤 | 探索 年化／回落 | 確認 年化／回落 | 比原回測少 | 一字漲停擋買 | 跌停延後賣 | 強制出場 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, x in T.iterrows():
        L.append(f"| {x['策略']} | {x['臂']} | {p(x['主窗_年化'])}／{p(x['主窗_回落'])}／{x['主窗_比值']:.3f} | {x['主窗_標籤']} | {p(x['探索_年化'])}／{p(x['探索_回落'])}（{x['探索_標籤']}） | "
                 f"{p(x['確認_年化'])}／{p(x['確認_回落'])}（{x['確認_標籤']}） | {x['比原回測少（點，主窗）']:+.2f} 點 | {x['一字漲停擋買（中位）']:.0f} | {x['跌停延後賣（中位）']:.0f} | {x['強制出場（中位）']:.0f} |")
    L.append("")
    L.append("## 二、損益兩平成本（主窗、停止交易強制出場開；額外單邊成本 s ⇒ 引擎來回成本 0.585%＋2s）")
    L.append("")
    for st, v in BE.items():
        L.append(f"- {st}：比值掉到 0050 以下 ⇐ 額外單邊 {q(v['損益兩平額外單邊成本_比值跌到0050以下'], 3)}；年化掉到 0050 以下 ⇐ {q(v['損益兩平額外單邊成本_年化跌到0050以下'], 3)}；"
                 f"{'⚠ 對成本很敏感（＜ 0.3% 單邊）' if v['對成本很敏感（＜ 0.3% 單邊）'] else '不算對成本很敏感（≥ 0.3% 單邊）'}")
    L.append("")
    L.append("## 三、流動性、參與率、一字漲停")
    L.append("")
    for st, v in S["流動性與漲停"].items():
        L.append(f"### {st}")
        L.append("")
        L.append("| 資金 | 每筆下單 | 參與率中位 | 參與率 ＞1% | ＞5% |")
        L.append("|---|---|---|---|---|")
        for cap, x in v["參與率"].items():
            L.append(f"| {cap} | {x['每筆下單']:,.0f} 元 | {q(x['參與率中位'], 2)} | {q(x['＞1%'])} | {q(x['＞5%'])} |")
        a = v["持股 ADV20（元）10／50／90 分位"]
        L.append("")
        L.append(f"持股 20 日平均成交金額 10／50／90 分位：{a[0] / 1e6:,.1f}／{a[1] / 1e6:,.1f}／{a[2] / 1e6:,.1f} 百萬元。"
                 f"訊號進場日一字漲停 {v['訊號進場日一字漲停']['筆']} 筆（{q(v['訊號進場日一字漲停']['占訊號'], 2)}）；放棄組（那批原本的報酬）平均 {p(v['訊號進場日一字漲停']['放棄組報酬平均（原 g、未扣成本）'])}、"
                 f"其餘訊號 {p(v['訊號進場日一字漲停']['其餘訊號報酬平均'])}。")
        L.append("")
    L.append("## 四、C5 零股低消換算（裁定 seq258）")
    L.append("")
    for st, v in S["C5 低消換算"].items():
        L.append(f"- {st}：" + "；".join(f"{k}：每筆 {x['每筆']:,} 元 ⇒ 低消換算單邊 {q(x['低消換算單邊'], 3)}，比 0.1425% 多出 {q(x['比 0.1425% 多出的單邊'], 4)}" for k, x in v.items())
                 + f"；對年化：C4 均價 {p(row(st, 'C4 均價成交')['主窗_年化'])} → 低消 1 元 {p(row(st, 'C5 低消 1 元（＋C4）')['主窗_年化'])}、低消 20 元 {p(row(st, 'C5 低消 20 元（＋C4）')['主窗_年化'])}")
    L.append(f"- ⚠ {S['標註'][1]}")
    L.append("")
    L.append("## 五、早年段 2012-06～2014-12（只上市）")
    L.append("")
    if TE is not None:
        ZE = SE["0050"]["主窗"]
        L.append(f"0050 同窗 {p(ZE[0])}／{p(ZE[1])}（{ZE[0] / abs(ZE[1]):.3f}）。")
        L.append("")
        L.append("| 策略 | 臂 | 年化／回落／比值 | 標籤 | 比原回測少 |")
        L.append("|---|---|---|---|---|")
        for _, x in TE.iterrows():
            L.append(f"| {x['策略']} | {x['臂']} | {p(x['主窗_年化'])}／{p(x['主窗_回落'])}／{x['主窗_比值']:.3f} | {x['主窗_標籤']} | {x['比原回測少（點，主窗）']:+.2f} 點 |")
    else:
        L.append("（未跑）")
    L.append("")
    L.append("## 六、先驗（登錄 §五；只對事實）")
    L.append("")
    ry, rf = row("營量 v1", REAL), row("營飆 v1", REAL)
    L.append(f"- ① 現實版營量少 2～5 點、營飆少 1～3 點：營量 {ry['比原回測少（點，主窗）']:.2f} 點、營飆 {rf['比原回測少（點，主窗）']:.2f} 點")
    L.append(f"- ② 營量主窗現實版從合格掉到另列：原件 {row('營量 v1', ORIG)['主窗_標籤']} → 現實版 {ry['主窗_標籤']}")
    L.append(f"- ③ 1,000 萬時營量參與率 ＞ 5% 的交易 ＞ 5%：{q(S['流動性與漲停']['營量 v1']['參與率']['1000 萬']['＞5%'])}")
    L.append(f"- ④ 一字漲停比例 營飆 ＞ 營量：營飆 {q(S['流動性與漲停']['營飆 v1']['訊號進場日一字漲停']['占訊號'], 2)}、營量 {q(S['流動性與漲停']['營量 v1']['訊號進場日一字漲停']['占訊號'], 2)}")
    L.append("")
    L.append("## 七、讀法（登錄 §四，機械套用）")
    L.append("")
    for st in ("營量 v1", "營飆 v1"):
        o, r = row(st, ORIG), row(st, REAL)
        same = o["主窗_標籤"] == r["主窗_標籤"]
        L.append(f"- {st}：" + ("加上現實成本後結論不變" if same else "真實下單可能沒有回測那麼好（標籤降一級）" + ("；營量「暫定」理由加一條" if st == "營量 v1" else ""))
                 + ("；對成本很敏感" if BE[st]["對成本很敏感（＜ 0.3% 單邊）"] else ""))
    L.append("")
    L.append("## 八、閘與查核")
    L.append("")
    L.append(f"- 主窗：{S['閘']}")
    if SE:
        L.append(f"- 早年：{SE['閘']}")
    L.append("- 註：run_main.log 第 12 行那次閘顯示 177／200、3／3 不逐位元，是重啟續跑時讀回 seeds_main.csv.gz 未用 float_precision=\"round_trip\"（pandas 預設解析器末位不精確）的假警報；引擎輸出本身未變，改用 round_trip 讀回後 203／203 逐位元（第 49 行），查核 ② 同。")
    if CK:
        L.append(f"- 獨立查核 `researchSlip_check.py`（⛔ 不 import 主程式）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] is True else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 九、檔案")
    L.append("")
    L.append("`backtest/researchSlip.py`、`researchSlip_check.py`、`researchSlip_report.py`；resultsSlip/：table_main.csv、table_early.csv、seeds_main.csv.gz、seeds_early.csv.gz、"
             "summary_main.json、summary_early.json、check.json、run_main.log、run_early.log、check.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:16]))


if __name__ == "__main__":
    main()
