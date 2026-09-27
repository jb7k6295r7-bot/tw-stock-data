# -*- coding: utf-8 -*-
"""六四 v1 重測 REPORT.md 產生器（只讀 results64retest/；⛔ 不重算）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/research64retest_report.py
"""
from __future__ import annotations
import json, os
import numpy as np
import pandas as pd

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "results64retest")


def p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def q(x, d=1):
    return f"{float(x) * 100:.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ST = pd.read_csv(os.path.join(OUT, "stress.csv"), encoding="utf-8")
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    R1, R2, R3 = S["① 同窗判定＋⑤ 並列"], S["② 隨機配比臂"], S["③ 2008 合成＋資金成本"]
    A, B, A0 = "A 2018-01-15～2026-08-24", "B 確認段 2022-01-03～2026-08-24", "A0 2017-03-30～2026-08-24（00685L 上市首日起；描述）"
    six = "六四 v1（真 00685L）"; z = "0050（判準，還原、不含成本）"
    la, lb = R1[A][six]["判準"], R1[B][six]["判準"]
    sw = "壓力窗 2006-09-12～2014-12-31"
    worst = min(R3[v][sw]["六四 v1（合成 00685L）"]["最大回落"] for v in R3)
    over = any(R3[v][sw]["六四 v1（合成 00685L）"]["超過 −70%"] for v in R3)
    L = ["# 六四 v1 重測（0050 60%＋00685L 40%、每年 1 月調回；裁定 seq257 §三 順 2、稽核 seq3 §七之三）", ""]
    L.append(f"**結論：六四 v1 在同窗 2018-01～2026-08 與確認段 2022～2026 都對 0050【{la}／{lb}】；但隨機抽配比也有 {q(R2[A]['隨機合格比例'], 0)}／{q(R2[B]['隨機合格比例'], 0)} 合格"
             f"（合格主要來自「有放正2」本身，不是 40% 這個比例特別好）；2008 合成加上資金成本最慘 {p(worst)}，{'⚠ 超過' if over else '仍守住'} −70%（餘裕約 {abs(worst + 0.70) * 100:.1f} 點）；"
             f"1990、2000～2002 壓力【等資料】。**")
    L.append("")
    L.append("| 項目 | 六四 v1 | 0050 | 一直抱正2 | 判定／讀法 |")
    L.append("|---|---|---|---|---|")
    for wn, lab_ in ((A, "同窗 2018-01-15～2026-08-24（真 00685L）"), (B, "確認段 2022-01-03～2026-08-24")):
        r = R1[wn]
        L.append(f"| {lab_} 年化／回落 | {p(r[six]['年化'])}／{p(r[six]['最大回落'])}（比值 {r[six]['比值']:.3f}） | {p(r[z]['年化'])}／{p(r[z]['最大回落'])}（{r[z]['比值']:.3f}） | "
                 f"00685L {p(r['一直抱 00685L']['年化'])}／{p(r['一直抱 00685L']['最大回落'])} | **{r[six]['判準']}** |")
    L.append(f"| 隨機配比臂（1,000 次） | 年化百分位 {q(R2[A]['六四 年化百分位（隨機 ≤ 六四）'], 0)}／{q(R2[B]['六四 年化百分位（隨機 ≤ 六四）'], 0)}；比值百分位 {q(R2[A]['六四 比值百分位'], 0)}／{q(R2[B]['六四 比值百分位'], 0)} | — | — | "
             f"隨機合格 {q(R2[A]['隨機合格比例'])}／{q(R2[B]['隨機合格比例'])}（登錄件 19.5%） |")
    for vn in ("不扣資金成本（researchMix70 原式）", "DTB3（美國 3 個月國庫券，代）", "固定 3%"):
        x = R3[vn][sw]
        L.append(f"| 2008 合成（{vn}）最大回落／100 萬在高點剩 | {p(x['六四 v1（合成 00685L）']['最大回落'])}／{x['六四 v1（合成 00685L）']['100萬在高點_谷底剩（萬）']:.1f} 萬 | "
                 f"{p(x['一直抱 0050']['最大回落'])} | {p(x['一直抱合成正2（00631L 式）']['最大回落'])} | {'⚠ 超過 −70%' if x['六四 v1（合成 00685L）']['超過 −70%'] else '未超過 −70%'} |")
    L.append("| 1990 崩盤、2000～2002 長空頭 | 等資料 | — | — | 資料庫沒有 1990 起加權指數 |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・固定配比 ⇒ 沒有挑選、只判定；判準 ＝ 使用者判準（對 0050 同窗）")
    L.append("  ・窗 A 用真的 00685L（2018-01-15 ＝ researchLev2 R1「上市滿 200 個交易日」起點；上市首日 2017-03-30 起另報 A0，描述）")
    L.append(f"  ・{S['③ 利率']['標註']}")
    L.append("  ・2008 合成：00685L 用 0050×2 合成（每日重設、扣經理費 0.3%／年、另扣資金成本 年利率÷245×(2−1)），非實際 ETF")
    L.append("  ・成本：ETF 0.385%，窗首建倉與每年調回都扣（researchMix70.sim；稽核 K3「看不出」⇒ 已確認有扣）")
    L.append("```")
    L.append("")
    L.append("## 一、同窗判定（①）與並列（⑤）")
    L.append("")
    for wn in (A, B, A0):
        L.append(f"### {wn}")
        L.append("")
        L.append("| 對象 | 年化 | 最大回落 | 比值 | 對 0050 判準 | 高點→谷底 | 每年動手 | 成本／年 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for nm, v in R1[wn].items():
            L.append(f"| {nm} | {p(v['年化'])} | {p(v['最大回落'])} | {v['比值']:.3f} | {v.get('判準', '—')} | {v.get('高點日', '—')}→{v.get('谷底日', '—')} | "
                     f"{v['每年動手']:.2f} | {p(v.get('成本／年（占市值）'), 3)} |" if "每年動手" in v else
                     f"| {nm} | {p(v['年化'])} | {p(v['最大回落'])} | {v['比值']:.3f} | {v.get('判準', '—')} | {v.get('高點日', '—')}→{v.get('谷底日', '—')} | — | — |")
        L.append("")
    L.append("六四 用 00631L 代 00685L 的差（描述）：窗 A 年化 " + f"{(R1[A]['六四（00631L 代，描述）']['年化'] - R1[A][six]['年化']) * 100:+.2f} 點、確認段 "
             f"{(R1[B]['六四（00631L 代，描述）']['年化'] - R1[B][six]['年化']) * 100:+.2f} 點（確認段判準 {R1[B]['六四（00631L 代，描述）']['判準']} ⇒ 低頻擇時件並列的「另列」是代用 ETF 造成的邊緣差）。")
    L.append("")
    L.append("## 二、隨機配比臂（②）")
    L.append("")
    L.append("| 窗 | 六四年化百分位 | 六四比值百分位 | 隨機合格 | 隨機另列 | 隨機年化中位（p10～p90） | 132 組合不抽樣合格 | 六四同配比換調回月份的年化範圍 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for wn in (A, B):
        v = R2[wn]
        L.append(f"| {wn} | {q(v['六四 年化百分位（隨機 ≤ 六四）'])} | {q(v['六四 比值百分位'])} | {q(v['隨機合格比例'])} | {q(v['隨機另列比例'])} | "
                 f"{p(v['隨機年化中位'])}（{p(v['隨機年化 p10～p90'][0])}～{p(v['隨機年化 p10～p90'][1])}） | {q(v['132 組合（不抽樣）合格比例'])} | "
                 f"{p(v['六四同配比 12 個調回月份 年化範圍'][0])}～{p(v['六四同配比 12 個調回月份 年化範圍'][1])} |")
    L.append("")
    L.append("讀法：隨機配比 = 00685L 0～100%（每 10%）× 調回月份 1～12 均勻抽 1,000 次；窗 A 九成以上合格 ⇒「合格」在這段多頭期幾乎是放正2 就有；"
             "六四的年化只在中段（約 40 百分位），但比值在高段（84～89 百分位）⇒ 40% 的好處是回落相對淺，不是賺得多。")
    L.append("")
    L.append("## 三、2008 合成＋資金成本（③）")
    L.append("")
    L.append(f"利率：{S['③ 利率']['DTB3 檔']}（sha {S['③ 利率']['sha256[:16]']}，{S['③ 利率']['期間'][0]}～{S['③ 利率']['期間'][1]}；壓力窗平均 {p(S['③ 利率']['壓力窗平均年利率'])}）")
    L.append("")
    L.append("| 資金成本 | 窗 | 六四 v1 | 一直抱合成正2 | 0050 | 低頻擇時 甲 | 乙 | 丙 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for (vn, win), g in ST.groupby(["資金成本", "窗"], sort=False):
        v = {r["對象"]: r for _, r in g.iterrows()}

        def cell(k):
            r = v[k]; return f"{p(r['最大回落'])}（剩 {r['100萬在高點_谷底剩（萬）']:.1f} 萬{'，⚠' if r['超過−70%'] else ''}）"
        L.append(f"| {vn} | {win} | {cell('六四 v1（合成 00685L）')} | {cell('一直抱合成正2（00631L 式）')} | {cell('一直抱 0050')} | "
                 f"{cell('低頻擇時 甲 D200_a')} | {cell('低頻擇時 乙 s40_L60_a')} | {cell('低頻擇時 丙 B_x20_R2_M')} |")
    L.append("")
    L.append("（格內 ＝ 最大回落（100 萬在高點、谷底剩多少）；⚠ ＝ 超過使用者上限 −70%）")
    L.append("")
    L.append("## 四、1990 起加權指數合成（④）：等資料")
    L.append("")
    for x in S["④ 1990 起加權指數合成"]["查過"]:
        L.append(f"- 查過：{x}")
    L.append(f"- 需要：{S['④ 1990 起加權指數合成']['要什麼']}（請資料庫線提供）")
    L.append("")
    L.append("## 五、閘與查核")
    L.append("")
    g = S["閘"]
    L.append(f"- 0050 主窗錨 {g['0050主窗錨']}；六四窗 A ＝ researchMix70 mix3_grid 60／0／40（逐位元）{g['六四窗A＝Mix70 逐位元']}；不扣資金成本的壓力窗回落 ＝ −67.80% {g['六四壓力窗不扣資金成本＝Mix70 −67.80%']}")
    if CK:
        L.append(f"- 獨立查核 `research64retest_check.py`（⛔ 不 import 主程式；自寫固定配比引擎、合成與利率）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] is True else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 六、六四 v1 重測後建議狀態（本線讀法；⛔ 由裁定線定）")
    L.append("")
    L.append("```")
    L.append(f"K6（從未同窗判過）⇒ 已補：同窗 2018-01～2026-08【{la}】、確認段【{lb}】（真 00685L、扣 0.385%）")
    L.append(f"K4（無隨機配比對照）⇒ 已補：隨機配比合格 {q(R2[A]['隨機合格比例'])}（同窗）／{q(R2[B]['隨機合格比例'])}（確認段）⇒「合格」不是這個配比獨有；六四的特色是比值高（84～89 百分位）")
    L.append(f"K5（2008 合成未含資金成本）⇒ 已補：DTB3 與 1%～3% 下最慘 {p(worst)}，仍在 −70% 內，但餘裕只約 {abs(worst + 0.70) * 100:.1f} 點；1990、2000～2002 等資料")
    L.append("K1（配比是看完全段、以 2008 合成 −70% 回算）⇒ 無法補：固定配比沒有樣本外可挑；2008 壓力測試對 40% 這個比例本身就是樣本內")
    L.append("⇒ 本線讀法：可改標「正式（同窗與確認段合格；合格主要來自持有正2 本身；2008 合成含資金成本守住 −70%、餘裕約 2 點）」，")
    L.append("   但 1990、2000～2002 壓力未測 ⇒ −70% 那一條建議仍標「待 1990 起加權指數資料」；K1 樣本內回算照實並陳")
    L.append("```")
    L.append("")
    L.append("## 七、檔案")
    L.append("")
    L.append("`backtest/research64retest.py`、`research64retest_check.py`、`research64retest_report.py`；results64retest/：summary.json、stress.csv、"
             "random_grid_A.csv、random_grid_B.csv、random_draws.csv、check.json、run.log、check.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
