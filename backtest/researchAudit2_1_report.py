# -*- coding: utf-8 -*-
"""稽核 ② 5 三態輪動 K7 重挑 報告（只讀 resultsAudit2/1/）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python -m backtest.researchAudit2_1_report"""
from __future__ import annotations
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsAudit2", "1")


def p(x):
    return f"{x * 100:+.2f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    nb, ob = S["主版挑法乙（判定）"], S["原件挑法乙（K7 前）"]
    z = S["0050同窗"]["確認"]; h = S["純抱00631L"]["確認"]; fk = S["假訊號（主版乙，確認段）"]
    st = {r["對象"] + r["期間"]: r for r in S["壓力（合成、非實際 ETF）"]}
    L = ["# 稽核 ② 5：正2 三態輪動 K7 重挑（稽核 seq3 §二 第 5 列；裁定 seq257 順 5）", ""]
    L.append(f"**結論：排除探索段觸發太少／依構造只剩兩態的組合後重挑，挑中的換成「{nb['白話']}」（跌深由「距 250 日高 −30%」換成「RSI＜30」，轉弱與反彈不變）；"
             f"確認段 {p(nb['確認']['年化'])}／{p(nb['確認']['回落'])}，贏 0050（{p(z['年化'])}），使用者判準仍【{nb['確認']['使用者判準']}】（比值 {nb['確認']['比值']:.3f} ＜ 0050 {z['比值']:.3f}），"
             f"與原件（{p(ob['確認']['年化'])}／{p(ob['確認']['回落'])}、另列）同一結論；⚠ 隨便換也有 {fk['p_年化贏0050'] * 100:.1f}% 贏 0050。"
             f"（出處：回測 PREREG三態輪動 researchTri bf4192c348；本件 researchAudit2_1）**")
    L.append("")
    L.append("| 確認段 2022-01-03～2026-08-24 | 年化 | 回落 | 比值 | 標籤 | 跌深態進入次數（探索／確認／早年） |")
    L.append("|---|---:|---:|---:|---|---|")
    for nm, x in (("**主版重挑** " + "×".join(nb["格"]), nb), ("原件 " + "×".join(ob["格"]), ob)):
        L.append(f"| {nm} | {p(x['確認']['年化'])} | {p(x['確認']['回落'])} | {x['確認']['比值']:.3f} | {x['確認']['使用者判準']} | "
                 f"{x['探索計數']['nC（B→C）']}／{x['確認計數']['nC（B→C）']}／{x['早年計數']['nC（B→C）']} |")
    L.append(f"| 純抱 00631L | {p(h['年化'])} | {p(h['回落'])} | {h['年化'] / abs(h['回落']):.3f} | — | — |")
    L.append(f"| 0050 | {p(z['年化'])} | {p(z['回落'])} | {z['比值']:.3f} | — | — |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・退化格規則只用探索段狀態路徑的次數、⛔ 不用報酬；但原件的報酬本線事前已看過（照實寫）")
    L.append("  ・stop_force、T1 補尾：兩檔 ETF 輪動、無固定持有天數出場、無停止交易 ⇒ 不適用")
    L.append("  ・N：重挑取代原挑法，⛔ 不另加 N（登錄 N_組合 ＋1 不變）")
    L.append("  ・「穩」只用在：門檻改 1／5、保留 B 抱 0050 三種描述版的確認段標籤都相同（見 §三）；⛔ 不代表樣本外成立")
    L.append("```")
    L.append("")
    L.append("## 一、退化格排除（researchAudit2_1 開頭寫死）")
    L.append("")
    L.append("```")
    L.append("計數在探索段 2015-11-02～2021-12-30 的狀態路徑上：nB ＝ A→B、nC ＝ B→C（跌深態真的被用到）、nA ＝ 回 A")
    L.append("X1 B 態抱 0050 的格：B 與 C 都抱 0050 ⇒ 持股路徑與跌深訊號無關（7 種跌深逐位元相同，已驗）⇒ 依構造兩態")
    L.append("X2 nC ＜ 3｜X3 nB ＜ 3｜X4 nC ÷ nB ＞ 0.9（B 態幾乎不存在）")
    e = S["排除統計"]
    L.append(f"⇒ 1,120 格保留 {e['保留']}（X1 {e['X1']}、X2 {e['X2']}、X3 {e['X3']}、X4 {e['X4']}；可重複）")
    L.append("B 現金格裡 7 種跌深的探索段 nC 中位：" + "、".join(f"{k} {v:g}" for k, v in e["跌深 7 種各自在 B現金格的 nC 中位"].items())
             + "（P3＝距 250 日高 −30%：0）")
    L.append("```")
    L.append("")
    L.append("## 二、三態各觸發幾次（主版乙；原件並列）")
    L.append("")
    L.append("| 格 | 段 | A→B | B→C | 回 A | A 日 | B 日 | C 日 |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for nm, x in (("主版 " + "×".join(nb["格"]), nb), ("原件 " + "×".join(ob["格"]), ob)):
        for sg, k in (("早年 2005-02～2014", "早年計數"), ("探索 2015-11～2021", "探索計數"), ("確認 2022～2026-08", "確認計數")):
            c = x[k]
            L.append(f"| {nm} | {sg} | {c['nB（A→B）']} | {c['nC（B→C）']} | {c['nA（回 A）']} | {c['A日']} | {c['B日']} | {c['C日']} |")
    L.append("")
    L.append("## 三、描述（⛔ 不判）：規則換一種寫法，挑中格與確認段")
    L.append("")
    L.append("| 版 | 保留格數 | 挑法 | 挑中 | 探索 nC | 確認段年化／回落 | 標籤 |")
    L.append("|---|---:|---|---|---:|---|---|")
    main_pa = S["主版挑法甲（並列）"]
    L.append(f"| 主版（門檻 3、X1～X4） | {e['保留']} | 乙（判定） | {'×'.join(nb['格'])} | {nb['探索計數']['nC（B→C）']} | {p(nb['確認']['年化'])}／{p(nb['確認']['回落'])} | {nb['確認']['使用者判準']} |")
    L.append(f"| 主版 | {e['保留']} | 甲（並列） | {'×'.join(main_pa['格'])} | {main_pa['探索計數']['nC（B→C）']} | {p(main_pa['確認']['年化'])}／{p(main_pa['確認']['回落'])} | {main_pa['確認']['使用者判準']} |")
    for k, v in S["描述_門檻敏感"].items():
        for w in ("乙", "甲"):
            x = v[w]
            L.append(f"| {k} | {v['保留格數']} | {w} | {'×'.join(x['格'])} | {x['探索計數']['nC（B→C）']} | {p(x['確認']['年化'])}／{p(x['確認']['回落'])} | {x['確認']['使用者判準']} |")
    L.append("")
    L.append("## 四、假訊號、2022、壓力（主版乙；原件同法）")
    L.append("")
    y = S["2022（100 萬：谷底、12-30）"]
    L.append("```")
    L.append(f"假訊號（確認段狀態序列保留 {fk['轉換次數']} 次轉換與順序、轉換日隨機 1,000 次，rng 20260929）：年化贏 0050 {fk['p_年化贏0050'] * 100:.1f}%（原件 19.6%）、"
             f"贏純抱 00631L {fk['年化贏純抱00631L比例'] * 100:.1f}%、使用者判準合格 {fk['使用者判準合格比例'] * 100:.1f}%")
    L.append(f"2022（100 萬）：主版 谷底 {y['主版乙'][0] / 1e4:.1f} 萬、12-30 {y['主版乙'][1] / 1e4:.1f} 萬｜純抱 00631L {y['純抱00631L'][0] / 1e4:.1f}、{y['純抱00631L'][1] / 1e4:.1f}｜0050 {y['0050'][0] / 1e4:.1f}、{y['0050'][1] / 1e4:.1f}")
    for per in ("2008-01～2009-03", "早年全段（起跑～2014-12-31）"):
        L.append(f"壓力 {per}（合成、非實際 ETF）：主版 最大跌幅 {p(st['主版乙（A 抱合成正2）' + per]['最大跌幅'])}、最慘剩 {st['主版乙（A 抱合成正2）' + per]['100萬谷底剩'] / 1e4:.1f} 萬、年化 {p(st['主版乙（A 抱合成正2）' + per]['年化'])}｜"
                 f"原件 {p(st['原件乙（A 抱合成正2）' + per]['最大跌幅'])}、{st['原件乙（A 抱合成正2）' + per]['100萬谷底剩'] / 1e4:.1f} 萬｜"
                 f"純抱 {p(st['純抱合成正2' + per]['最大跌幅'])}、{st['純抱合成正2' + per]['100萬谷底剩'] / 1e4:.1f} 萬｜0050 {p(st['0050' + per]['最大跌幅'])}、{st['0050' + per]['100萬谷底剩'] / 1e4:.1f} 萬")
    L.append("```")
    L.append("")
    L.append("## 五、閘與查核")
    L.append("")
    L.append(f"- 1,120 格 × 兩段重跑 ＝ resultsTri/body_cells.csv 逐位元：{all(v == 0 for v in S['閘']['1,120 格×兩段 ＝ body_cells.csv（逐位元，各欄不同列數）'].values())}；"
             f"原挑法重挑 ＝ W4×P3×U4×現金：{S['閘']['原挑法重挑 ＝ W4×P3×U4×現金']}；X1 依構造同：{S['閘']['X1 B 抱 0050 的格：7 種跌深年化／回落／成交次數全同']}")
    if CK is not None:
        L.append(f"- 獨立查核 `researchAudit2_1_check.py`（⛔ 不 import backtest；上半段＝ researchTri_check 的自接資料、自寫訊號／狀態機／引擎）："
                 + ("✅ 全過（T1 訊號、A1 排除計數、A2 X1、A3 重挑與確認段、A4 三態次數、A5 假訊號、A6 壓力）" if not CK["不過"] else f"❌ 不過 {CK['不過']}"))
    L.append("")
    L.append("## 六、檔案")
    L.append("")
    L.append("`backtest/researchAudit2_1.py`、`researchAudit2_1_check.py`、`researchAudit2_1_report.py`；resultsAudit2/1/：summary.json、cells.csv（1,120 格 × 兩段＋計數＋排除理由）、"
             "null.csv、null_days.npz、stress.csv、check.json、check.log、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
