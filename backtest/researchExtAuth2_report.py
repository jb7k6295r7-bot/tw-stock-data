# -*- coding: utf-8 -*-
"""PREREG外部作者追加 REPORT.md 產生器（只讀 resultsExtAuth2/；⛔ 不重算）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtAuth2_report.py
"""
from __future__ import annotations
import json, os
import numpy as np
import pandas as pd

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsExtAuth2")
NAME = {"F1": "F1 三線反紅", "O1": "O1 均線假跌破 3 日站回", "S1": "S1 高檔量縮過久補量下跌（出）"}


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


def f(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    PRE = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells.csv")); SE = pd.read_csv(os.path.join(OUT, "se_cells.csv")); Q = pd.read_csv(os.path.join(OUT, "quad_cells.csv"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    B = S["0050同段"]; J = S["判定"]; FK = S["假訊號"]; ch = S["探索段挑格"]
    labs = {g: J[g]["判定"] for g in NAME}
    cnt = {k: sum(v == k for v in labs.values()) for k in ("合格", "另列", "不合格", "依構造不可判定")}
    half = sum("未過" in v for v in labs.values())
    rnd = [g for g in NAME if g in FK and FK[g]["p（隨機 ≥ 本格）"] >= 0.05]
    head = (f"三顆裡 {cnt['合格']} 顆合格、{cnt['另列']} 顆另列、{half} 顆只過確認段、{cnt['不合格']} 顆不合格、{cnt['依構造不可判定']} 顆依構造不可判定"
            + ("" if cnt["合格"] + cnt["另列"] + half else " ⇒ 薛俊原、方天龍、OANDA 這三個做法放進 10 檔組合都沒有贏 0050"))
    L = ["# PREREG外部作者追加 seq1（S1 薛俊原、F1 方天龍、O1 OANDA）：本體＋獨立查核", ""]
    L.append(f"**結論：{head}。**（⚠ 事後追加、N ＋3（外部作者合計 ＋10）；停止交易強制出場：開；判定格假訊號 p ≥ 0.05：{'、'.join(rnd) if rnd else '無'}）")
    L.append("")
    L.append("| 顆 | 探索段挑中 | 確認段 年化／回落／比值 | 主窗全段 年化／回落／比值 | 判定 | 假訊號 p |")
    L.append("|---|---|---|---|---|---|")
    for g in NAME:
        j = J[g]
        if "格" not in j:
            L.append(f"| {NAME[g]} | — | — | — | **依構造不可判定** | — |"); continue
        c, m = j["確認"], j["主窗"]; pf = FK.get(g, {}).get("p（隨機 ≥ 本格）")
        L.append(f"| {NAME[g]} | `{j['格']}` | {p(c['cagr_med'])}／{p(c['mdd_med'])}／{f(c['ratio'], 3)} | {p(m['cagr_med'])}／{p(m['mdd_med'])}／{f(m['ratio'], 3)} | "
                 f"**{j['判定']}**{'（隨機也做得到）' if (pf is not None and pf >= 0.05) else ''} | {f(pf, 3)} |")
    L.append(f"| 0050（判準） | — | {p(B['確認']['cagr'])}／{p(B['確認']['mdd'])}／{f(B['確認']['cagr'] / abs(B['確認']['mdd']), 3)} | "
             f"{p(B['主窗']['cagr'])}／{p(B['主窗']['mdd'])}／{f(B['主窗']['cagr'] / abs(B['主窗']['mdd']), 3)} | — | — |")
    L.append("")
    if "確認_加減不加" in J.get("S1", {}):
        j = J["S1"]
        L.append(f"S1 另一句：加 S1 vs 不加（同基準同出場 `{j['格'].split('|')[1]}`）：確認段年化差 {j['確認_加減不加']['年化差（點）']:+.2f} 點、回落差 {j['確認_加減不加']['回落差（點）']:+.2f} 點"
                 f"（主窗 {j['主窗_加減不加']['年化差（點）']:+.2f}／{j['主窗_加減不加']['回落差（點）']:+.2f} 點；回落差為負 ＝ 更深）。")
        L.append("")
    cmpx = S.get("seq1出場顆_同一次重跑（停止交易強制出場開）", {})
    if cmpx:
        L.append("同一次、同引擎開關重跑 seq1 出場三顆的判定格（描述對照，⛔ 不改 seq1 判定）：" + "；".join(
            f"{g} `{v['確認']['格']}` 確認段 {p(v['確認']['年化'])}（不加 {p(v['確認']['不加_年化'])}，差 {v['確認']['年化差（點）']:+.2f} 點）" for g, v in cmpx.items()) + "。")
        L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・停止交易強制出場：開（裁定 seq255 §一 4；research11.simulate_mtm stop_force，commit 51a3dc35f3）")
    L.append("  ・事後追加；家族 N ＋3（外部作者合計 ＋10）")
    L.append("  ・★ 補定照裁定 seq253 §二：S1 觸發窗「段中或結束後 5 日」、F1 下降趨勢定義、O1 斜率 5 日差")
    L.append("  ・「穩」照裁定 seq253 §一 3 收緊：相鄰視窗本身也過門檻才寫「穩」")
    L.append("  ・做法全照 PREREG外部作者 seq1（researchExtAuth.py import、不改）；出場只看持有期間、訊號日當天跌破不擋進場（seq255 已核准）")
    L.append("```")
    L.append("")
    L.append("## 一、事件數與退化格（pre；⛔ 挑選前）")
    L.append("")
    L.append("| 格 | 主窗事件 | 年均 | 探索段列 | 探索段段尾未出場 | 確認段列 | 剔除 |")
    L.append("|---|---|---|---|---|---|---|")
    for r in PRE["進場格"]:
        L.append(f"| {r['格']} | {r['主窗事件']:,} | {r['年均事件']:.1f} | {r['探索_列']:,} | {r['探索_段尾未出場比例'] * 100:.1f}% | {r['確認_列']:,} | {'；'.join(PRE['剔除'][r['格']]) or '—'} |")
    for r in [x for x in PRE["出場格"] if x["段"] == "主窗"]:
        L.append(f"| {r['格']} | {r['有效觸發列']:,}（基準 {r['基準列']:,}） | {r['有效觸發列'] / (2313 / 245):.1f} | — | — | — | {'；'.join(PRE['剔除'][r['格']]) or '—'} |")
    L.append("")
    fi, oi, si = PRE["F1（主窗 eligible）"], PRE["O1（主窗 eligible）"], PRE["S1（主窗、全母體）"]
    L.append(f"F1：主窗 eligible 原版事件 {fi['原版事件']}、確認率 {q(fi['確認率'])}；與多頭吞噬（反轉訊號 L_ENG）同檔 ±2 日重疊 {fi['與多頭吞噬 ±2 日重疊']} 筆 ＝ {q(fi['重疊率'])}。"
              f"O1：跌破事件 {oi['跌破事件']:,}、3 日內站回 {oi['3 日內站回']:,}（站回率 {q(oi['站回率'])}）。S1：主窗觸發 {si['觸發']:,} 次、{si['有觸發的檔數']:,} 檔、每檔每年 {si['每檔每年']:.2f} 次。")
    L.append("")
    for g, v in S.get("放棄組", {}).items():
        L.append(f"- 放棄組 {g}：事件 {v['事件']:,}、確認／站回率 {q(v['確認／站回率'])}；有確認的 20 日報酬 {p(v['有確認的_20日報酬平均'])}、沒確認的（照原版／k 次日買）{p(v['沒確認的_20日報酬平均（照原版／k 次日買）'])}（未扣成本）")
    L.append("")
    L.append("## 二、全部格（探索段 200 顆中位；剔除的只描述）")
    L.append("")
    L.append("| 格 | 年化 | 回落 | 比值 | 每顆交易筆 | 勝率 | 持有天數 平均／中位 | 平均持股 | 現金 | 段尾未出場 | 換手成本／年 | 強制出場（每顆） | 剔除 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in C[C["段"] == "探索"].itertuples():
        L.append(f"| {r.顆}｜{r._3} | {p(r.cagr_med)} | {p(r.mdd_med)} | {f(r.ratio, 3)} | {f(r.交易筆_每顆平均, 0)} | {q(r.勝率)} | {f(r.持有天數_平均, 0)}／{f(r.持有天數_中位, 0)} | "
                 f"{f(r.平均持股檔數, 1)} | {q(r.現金比例, 0)} | {f(r.段尾未出場_每顆, 1)} | {p(r.換手成本_每年)} | {f(r.停止交易強制出場_每顆, 1)} | {r.剔除 if isinstance(r.剔除, str) else '—'} |")
    L.append(f"\n0050 探索段 {p(B['探索']['cagr'])}／{p(B['探索']['mdd'])}。")
    L.append("")
    L.append("## 三、確認段與主窗（判定格＋ seq1 出場顆對照）")
    L.append("")
    L.append("| 格 | 段 | 年化 | 回落 | 比值 | 勝率 | 持有天數 平均／中位 | 平均持股 | 現金 | 段尾未出場 | 換手成本／年 | 強制出場 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for seg in ("確認", "主窗"):
        for r in C[C["段"] == seg].itertuples():
            if str(r._3).startswith("固定"):
                continue
            L.append(f"| {r.顆}｜{r._3} | {seg} | {p(r.cagr_med)} | {p(r.mdd_med)} | {f(r.ratio, 3)} | {q(r.勝率)} | {f(r.持有天數_平均, 0)}／{f(r.持有天數_中位, 0)} | "
                     f"{f(r.平均持股檔數, 1)} | {q(r.現金比例, 0)} | {f(r.段尾未出場_每顆, 1)} | {p(r.換手成本_每年)} | {f(r.停止交易強制出場_每顆, 1)} |")
    L.append("")
    L.append("## 四、對照")
    L.append("")
    fx = C[C["出場／H"].astype(str).str.startswith("固定")]
    if len(fx):
        L.append("| 格 | 段 | 抱 20 日 | 抱 60 日 | 抱 120 日 |")
        L.append("|---|---|---|---|---|")
        for (seg, code), gg in fx.groupby(["段", "顆"], sort=False):
            v = {r._3: r for r in gg.itertuples()}
            L.append(f"| {code} | {seg} | " + " | ".join(f"{p(v[f'固定H{H}'].cagr_med)}／{p(v[f'固定H{H}'].mdd_med)}" if f"固定H{H}" in v else "—" for H in (20, 60, 120)) + " |")
        L.append("")
    L.append("| 判定格 | 假訊號確認段中位 | p10～p90 | p（隨機 ≥ 本格） | 贏 0050 同段比例 |")
    L.append("|---|---|---|---|---|")
    for g, v in FK.items():
        L.append(f"| {NAME[g]} | {p(v['中位年化'])} | {p(v['p10'])}～{p(v['p90'])} | {f(v['p（隨機 ≥ 本格）'], 3)} | {v['贏0050同段比例'] * 100:.1f}% |")
    L.append("")
    L.append("## 五、均線出場主版加報（裁定 seq252 §一）：確認段一直沒出場的那批")
    L.append("")
    for g, v in S.get("一直沒出場的那批（確認段判定格）", {}).items():
        L.append(f"- {NAME[g]}：" + (v["不適用"] if "不適用" in v else "0 筆" if not v.get("筆數") else
                 f"{v['筆數']} 筆（占 {q(v['占列'])}）、段尾未實現報酬中位 {p(v['段尾未實現報酬_中位'])}（p10 {p(v['p10'])}、p90 {p(v['p90'])}）、最長持有 {v['最長持有（交易日）']} 個交易日"))
    L.append("")
    L.append("## 六、單筆層（{5, 10, 20, 60} 日；差 ＝ 報酬 − 基準②；95% CI 月分群；只描述）")
    L.append("")
    L.append("| 訊號 | H | 保留 | n_eff | 差平均 | 95% CI | 扣 0.585% 後 | 成功率／基準 | 讀法 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in SE.itertuples():
        L.append(f"| {r.名}（{r.方向}） | {r.H} | {r.保留:,} | {int(r.n_eff) if np.isfinite(r.n_eff) else 0} | {p(r.mean)} | {p(getattr(r, 'lo', np.nan))}～{p(getattr(r, 'hi', np.nan))} | "
                 f"{p(getattr(r, 'mean_net', np.nan))}（{getattr(r, '扣成本後') if isinstance(getattr(r, '扣成本後', None), str) else '—'}） | {q(r.成功率)}／{q(r.基準成功率)} | {r.判定} |")
    L.append("")
    for code, g in SE.groupby("code", sort=False):
        L.append(f"- {g['名'].iloc[0]}：{g['穩不穩'].iloc[0]}")
    L.append("")
    L.append("## 七、S1 套「全市場任何一檔任何時候買」基準（四類單獨口徑；配對差 ＝ 加 S1 − 抱滿 H）")
    L.append("")
    L.append("| 段 | H | 筆 | 觸發比例 | 配對差平均 | 95% CI |")
    L.append("|---|---|---|---|---|---|")
    for r in Q.itertuples():
        L.append(f"| {r.段} | {r.H} | {r.筆:,} | {q(r.觸發比例)} | {p(r.差平均, 3)} | {p(r.CI低, 3)}～{p(r.CI高, 3)} |")
    L.append("")
    L.append("## 八、早年段（描述）")
    L.append("")
    E = S.get("早年段")
    if E:
        L.append(S.get("早年段_註", "")); L.append("")
        L.append("| 段 | 格 | 年化 | 回落 | 0050 同段 |")
        L.append("|---|---|---|---|---|")
        for k, v in E.items():
            if isinstance(v, dict) and "cagr_med" in v:
                part = k.split("|")[0]; b = E.get(f"{part}_0050", {})
                L.append(f"| {part}（{'～'.join(E.get(part + '_窗', []))}） | {k.split('|', 1)[1]} | {p(v['cagr_med'])} | {p(v['mdd_med'])} | {p(b.get('cagr'))}／{p(b.get('mdd'))} |")
    else:
        L.append("（未跑）")
    L.append("")
    L.append("## 九、先驗（登錄 §六；只對事實）")
    L.append("")
    L.append(f"- ① F1、O1 確認段都不合格；F1 事件少依構造不可判定：F1 {labs['F1']}、O1 {labs['O1']}")
    L.append(f"- ② F1 與多頭吞噬重疊率 ≥ 五成：{q(fi['重疊率'])}")
    if "確認_加減不加" in J.get("S1", {}):
        L.append(f"- ③ S1 加 vs 不加確認段年化不比不加高：{J['S1']['確認_加減不加']['年化差（點）']:+.2f} 點")
    o1 = SE[SE["code"] == "O1"].set_index("H")
    L.append(f"- ④ O1 單筆層 5、10 日正差：5 日 {p(o1.at[5, 'mean'])}（{o1.at[5, '判定']}）、10 日 {p(o1.at[10, 'mean'])}（{o1.at[10, '判定']}）")
    L.append("")
    L.append("## 十、出場敏感度（新規矩 ③）")
    L.append("")
    lab = [g for g in NAME if labs[g] in ("合格", "另列") or "未過" in labs[g]]
    L.append(("⚠ 有合格／另列：" + "、".join(lab) + " ⇒ 見 sens") if lab else "沒有合格或另列的格 ⇒ ⛔ 不跑。")
    L.append("")
    L.append("## 十一、閘與查核")
    L.append("")
    L.append(f"- selftest {S['selftest']}；seq1 訊號 digest ＝ seq1 pre（29f9a22c6fbcbed5）；新訊號 digest pre ＝ body（{PRE['新訊號 digest']}）；0050 主窗錨")
    if CK:
        L.append(f"- 獨立查核 `researchExtAuth2_check.py`（⛔ 不 import 主程式）：{'✅ 全過' if CK['全部過'] else '❌ 有不過'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] is True else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 十二、檔案")
    L.append("")
    L.append("`backtest/researchExtAuth2.py`（selftest／pre／body／early）、`researchExtAuth2_early.py`、`researchExtAuth2_check.py`、`researchExtAuth2_report.py`；"
             "resultsExtAuth2/：summary.json、pre.json、cells.csv、se_cells.csv、se_events.csv.gz、quad_cells.csv、quad_trades.csv.gz、abandon.csv.gz、"
             "confirm_rows_*.csv.gz、confirm_audit3.csv、check.json、run.log、check.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:22]))


if __name__ == "__main__":
    main()
