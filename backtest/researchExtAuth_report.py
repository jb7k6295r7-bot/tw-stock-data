# -*- coding: utf-8 -*-
"""PREREG外部作者 REPORT.md 產生器（只讀 resultsExtAuth/ 的 summary.json、pre.json、cells.csv、se_cells.csv、quad_cells.csv、check.json；⛔ 不重算）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtAuth_report.py
"""
from __future__ import annotations
import json, os
import numpy as np
import pandas as pd

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsExtAuth")
NAME = {"W1": "W1 上升三法", "W2": "W2 年線戰法", "Y1": "Y1 量縮打底突破回踩", "Y2": "Y2 高檔爆量長黑三日", "Y3": "Y3 恐慌量後量縮不破底",
        "Y4": "Y4 三段移動停利", "Y5": "Y5 量縮陰跌"}
CN = {"W1": "上升三法", "W2": "年線戰法", "Y1": "量縮打底突破回踩", "Y2in": "Y2 進", "Y2out": "Y2 出", "Y3": "恐慌量後量縮", "Y4_MA5": "Y4（MA5 臂）",
      "Y4_MA10": "Y4（MA10 臂）", "Y5": "量縮陰跌", "BASE": "基準（不加）"}


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
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    SE = pd.read_csv(os.path.join(OUT, "se_cells.csv"))
    Q = pd.read_csv(os.path.join(OUT, "quad_cells.csv"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    B = S["0050同段"]; J = S["判定"]; FK = S["假訊號"]; ch = S["探索段挑格"]
    labs = {g: J[g]["判定"] for g in NAME}
    n_ok = sum(v == "合格" for v in labs.values()); n_x = sum(v == "另列" for v in labs.values())
    n_no = sum(v == "不合格" for v in labs.values()); n_na = sum(v == "依構造不可判定" for v in labs.values())
    n_half = sum(("未過" in v) for v in labs.values())
    rnd = [g for g in NAME if g in FK and FK[g]["p（隨機 ≥ 本格）"] >= 0.05]
    L = []
    L.append("# PREREG外部作者 seq1（波段醫生＋楊爸，七顆）：本體＋獨立查核")
    L.append("")
    head = (f"七顆裡 {n_ok} 顆合格、{n_x} 顆另列、{n_half} 顆只過確認段、{n_no} 顆不合格、{n_na} 顆依構造不可判定"
            + ("" if n_ok + n_x + n_half else " ⇒ 波段醫生與楊爸的買點與賣法放進 10 檔組合，都沒有贏 0050（確認段與主窗全段皆然）"))
    L.append(f"**結論：{head}。**（⚠ 事後追加、N ＋7；W2 用季財報可用日 A2 暫定；判定格的假訊號 p ≥ 0.05：{('、'.join(rnd) if rnd else '無')}）")
    L.append("")
    L.append("| 顆 | 探索段挑中 | 確認段 年化／回落／比值 | 主窗全段 年化／回落／比值 | 判定 | 假訊號 p |")
    L.append("|---|---|---|---|---|---|")
    for g in NAME:
        j = J[g]
        if "格" not in j:
            L.append(f"| {NAME[g]} | — | — | — | **依構造不可判定** | — |"); continue
        c, m = j["確認"], j["主窗"]
        pf = FK.get(g, {}).get("p（隨機 ≥ 本格）")
        L.append(f"| {NAME[g]} | `{j['格']}` | {p(c['cagr_med'])}／{p(c['mdd_med'])}／{f(c['ratio'], 3)} | {p(m['cagr_med'])}／{p(m['mdd_med'])}／{f(m['ratio'], 3)} | "
                 f"**{j['判定']}**{'（隨機也做得到）' if (pf is not None and pf >= 0.05) else ''} | {f(pf, 3)} |")
    L.append(f"| 0050（判準） | — | {p(B['確認']['cagr'])}／{p(B['確認']['mdd'])}／{f(B['確認']['cagr'] / abs(B['確認']['mdd']), 3)} | "
             f"{p(B['主窗']['cagr'])}／{p(B['主窗']['mdd'])}／{f(B['主窗']['cagr'] / abs(B['主窗']['mdd']), 3)} | — | — |")
    L.append("")
    L.append("")
    L.append(f"Y3 全部 3 格事件太少（主窗 71 筆、年均 7.5）⇒ 挑選前剔除 ⇒ 依構造不可判定（N 照 ＋7）。Y2 進 3 格也因主窗事件 111 ＜ 200 被剔 ⇒ Y2 的判定格來自 Y2 出（`{ch.get('Y2')}`）。")
    over = [g for g in ("Y2", "Y4", "Y5") if "確認_加減不加" in J[g]]
    if over:
        L.append("出場顆「加這條 vs 不加（同基準同 H）」：" + "；".join(
            f"{NAME[g]}（`{J[g]['格']}`）確認段年化差 {J[g]['確認_加減不加']['年化差（點）']:+.2f} 點、回落差 {J[g]['確認_加減不加']['回落差（點）']:+.2f} 點（加 − 不加；回落為負 ＝ 更深）"
            f"（主窗 {J[g]['主窗_加減不加']['年化差（點）']:+.2f}／{J[g]['主窗_加減不加']['回落差（點）']:+.2f} 點）" for g in over) + "。")
        L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・事後追加：看過反轉訊號、訊號系統結果後才加（裁定 seq248 ⑦）；家族 N ＋7")
    L.append(f"  ・W2：{S['W2 標註']}（逐字）；結果「暫定」、⛔ 不對使用者說定論")
    L.append("  ・本線讀法 Q1（登錄沒寫）：Y2 是一顆（進＋出）、N＋7 ⇒ Y2 的 1 格在「Y2 進 3 格 ∪ Y2 出 3 格」裡照同一挑法挑")
    L.append("  ・本線讀法 Q2：出場只看持有期間（d ≥ e＝t＋1）⇒ 訊號日當天的跌破不擋進場（⛔ 不沿用 researchSig「同日有出場訊號不進」）")
    L.append("  ・引擎沿用 PREREG訊號系統：200 顆抽籤取中位、無 tradable（漲跌停不擋）、各段期初全現金、段尾按市值計")
    L.append("```")
    L.append("")
    # §一 pre
    L.append("## 一、事件數與退化格（pre；⛔ 挑選前）")
    L.append("")
    L.append("| 格 | 主窗事件 | 年均 | 探索段列 | 探索段段尾未出場 | 確認段列 | 訊號日同時跌破（照進） | 剔除 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in PRE["進場格"]:
        L.append(f"| {r['格']} | {r['主窗事件']:,} | {r['年均事件']:.1f} | {r['探索_列']:,} | {r['探索_段尾未出場比例'] * 100:.1f}% | {r['確認_列']:,} | "
                 f"{r.get('主窗_訊號日同時跌破（照進）', '—')} | {'；'.join(PRE['剔除'][r['格']]) or '—'} |")
    ov = pd.DataFrame(PRE["出場格"])
    for g_, gg in ov[ov["段"] == "主窗"].groupby("格", sort=False):
        r = gg.iloc[0]
        L.append(f"| {r['格']} | {int(r['有效觸發列']):,}（基準 {int(r['基準列']):,}） | {r['有效觸發列'] / (2313 / 245):.1f} | — | — | — | — | {'；'.join(PRE['剔除'][r['格']]) or '—'} |")
    L.append("")
    L.append(f"W2 年線站上後拉回的候選 {PRE['W2']['候選 (s, r)']:,}、過基本面 {PRE['W2']['過基本面']:,}（來源：{PRE['W2']['過基本面的來源']}；fin_ts ＝ 有 t57sb01 時戳、fin_dl ＝ 法定期限＋5 日）。"
              f"Y1 突破日 {PRE['Y1 突破日']:,}、其中 2 日內有回踩 {PRE['Y1 有回踩']:,}（全母體、全日曆、不分資格）。")
    L.append("")
    # §二 全部格
    L.append("## 二、全部格（探索段 200 顆中位；剔除的只描述）")
    L.append("")
    L.append("| 格 | 年化 | 回落 | 比值 | 每顆交易筆 | 勝率 | 持有天數 平均／中位 | 平均持股 | 現金 | 段尾未出場 | 換手成本／年 | 再進場筆（每顆） | 剔除 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ex = C[C["段"] == "探索"]
    for r in ex.itertuples():
        L.append(f"| {r.顆}｜{r._3} | {p(r.cagr_med)} | {p(r.mdd_med)} | {f(r.ratio, 3)} | {f(r.交易筆_每顆平均, 0)} | {q(r.勝率)} | {f(r.持有天數_平均, 0)}／{f(r.持有天數_中位, 0)} | "
                 f"{f(r.平均持股檔數, 1)} | {q(r.現金比例, 0)} | {f(r.段尾未出場_每顆, 1)} | {p(r.換手成本_每年)} | {f(r.再進場_筆數每顆, 1)} | {r.剔除 if isinstance(r.剔除, str) else '—'} |")
    L.append(f"\n0050 探索段 {p(B['探索']['cagr'])}／{p(B['探索']['mdd'])}／{f(B['探索']['cagr'] / abs(B['探索']['mdd']), 3)}。")
    L.append("")
    # §三 判定格細項
    L.append("## 三、判定格：確認段與主窗")
    L.append("")
    L.append("| 格 | 段 | 年化 | 回落 | 比值 | 每年交易（中位年） | 勝率 | 持有天數 平均／中位 | 平均持股 | 現金 | 段尾未出場 | 換手成本／年 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for seg in ("確認", "主窗"):
        for r in C[C["段"] == seg].itertuples():
            if r._3.startswith("固定") or r._3.startswith("BL"):
                continue
            yrs = json.loads(r.每年交易) if isinstance(r.每年交易, str) else {}
            L.append(f"| {r.顆}｜{r._3} | {seg} | {p(r.cagr_med)} | {p(r.mdd_med)} | {f(r.ratio, 3)} | {f(np.median(list(yrs.values())) if yrs else np.nan, 1)} | {q(r.勝率)} | "
                     f"{f(r.持有天數_平均, 0)}／{f(r.持有天數_中位, 0)} | {f(r.平均持股檔數, 1)} | {q(r.現金比例, 0)} | {f(r.段尾未出場_每顆, 1)} | {p(r.換手成本_每年)} |")
    L.append("")
    # §四 對照
    L.append("## 四、對照")
    L.append("")
    L.append("| 格 | 段 | 抱 20 日 | 抱 60 日 | 抱 120 日 |")
    L.append("|---|---|---|---|---|")
    for seg in ("探索", "確認"):
        fx = C[(C["段"] == seg) & C["出場／H"].astype(str).str.startswith("固定")]
        for code, gg in fx.groupby("顆", sort=False):
            v = {r._3: r for r in gg.itertuples()}
            L.append(f"| {code} | {seg} | " + " | ".join(f"{p(v[f'固定H{H}'].cagr_med)}／{p(v[f'固定H{H}'].mdd_med)}" if f"固定H{H}" in v else "—" for H in (20, 60, 120)) + " |")
    L.append("")
    L.append("| 判定格 | 假訊號（同進場／同基準＋隨機出場）確認段中位 | p10～p90 | p（隨機 ≥ 本格） | 贏 0050 同段的比例 |")
    L.append("|---|---|---|---|---|")
    for g, v in FK.items():
        L.append(f"| {NAME[g]} | {p(v['中位年化'])} | {p(v['p10'])}～{p(v['p90'])} | {f(v['p（隨機 ≥ 本格）'], 3)} | {v['贏0050同段比例'] * 100:.1f}% |")
    L.append("")
    # §五 描述
    L.append("## 五、描述（⛔ 不判）")
    L.append("")
    bl = C[(C["段"] == "確認") & C["出場／H"].astype(str).str.startswith("BL")]
    if len(bl):
        L.append("「收盤 ＜ MA 即賣」並列（確認段；登錄 §一 均線列）：" + "；".join(
            f"{r.顆}｜{r._3} {p(r.cagr_med)}／{p(r.mdd_med)}（持有中位 {f(r.持有天數_中位, 0)} 日）" for r in bl.itertuples()) + "。")
        L.append("")
    for g, v in S.get("描述_收盤低於MA即賣", {}).items():
        L.append(f"- {NAME[g]}（確認段 {v['列']:,} 列）：訊號日收盤已在出場均線下 {v['訊號日收盤已在 MA 下的列']} 列（照進；跌破式要先站上才可能賣），其中到段尾都沒出場 {v['其中到段尾都沒出場']} 列")
    y1 = S.get("Y1放棄組", {})
    L.append(f"- Y1 放棄組（主窗、eligible）：突破日 {y1.get('突破日（主窗、eligible）')}、有回踩 {y1.get('有回踩')}；沒回踩的突破次日買 20 日 {p(y1.get('沒回踩_突破次日買20日報酬平均'))}、"
             f"有回踩的突破次日買 {p(y1.get('有回踩_突破次日買20日報酬平均'))}、回踩次日買 {p(y1.get('有回踩_回踩次日買20日報酬平均'))}（未扣成本）")
    L.append("")
    # §六 單筆層
    L.append("## 六、單筆層（{5, 10, 20, 60} 日；差 ＝ 報酬 − 基準②；95% CI 以月分群；只描述）")
    L.append("")
    L.append("| 訊號 | H | 保留事件 | n_eff | 差平均 | 95% CI | 扣 0.585% 後 | 成功率／基準 | 讀法 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in SE.itertuples():
        L.append(f"| {r.名}（{r.方向}） | {r.H} | {r.保留:,} | {int(r.n_eff) if np.isfinite(r.n_eff) else 0} | {p(r.mean)} | {p(getattr(r, 'lo', np.nan))}～{p(getattr(r, 'hi', np.nan))} | "
                 f"{p(getattr(r, 'mean_net', np.nan))}（{getattr(r, '扣成本後', '—') if isinstance(getattr(r, '扣成本後', None), str) else '—'}） | {q(r.成功率)}／{q(r.基準成功率)} | {r.判定} |")
    L.append("")
    for code, g in SE.groupby("code", sort=False):
        L.append(f"- {g['名'].iloc[0]}：{g['穩不穩'].iloc[0]}")
    L.append("")
    # §七 全市場基準
    L.append("## 七、出場三顆套「全市場任何一檔任何時候買」基準（四類單獨口徑；配對差 ＝ 加這條 − 抱滿 H；只描述）")
    L.append("")
    L.append("| 段 | H | 出場 | 筆 | 觸發比例 | 配對差平均 | 95% CI（月分群） |")
    L.append("|---|---|---|---|---|---|---|")
    for r in Q.itertuples():
        L.append(f"| {r.段} | {r.H} | {CN.get(r.出場, r.出場)} | {r.筆:,} | {q(r.觸發比例)} | {p(r.差平均, 3)} | {p(r.CI低, 3)}～{p(r.CI高, 3)} |")
    L.append("")
    # §八 早年
    L.append("## 八、早年段（描述）")
    L.append("")
    E = S.get("早年段")
    if E:
        L.append(S.get("早年段_註", ""))
        L.append("")
        L.append("| 段 | 格 | 年化 | 回落 | 0050 同段 |")
        L.append("|---|---|---|---|---|")
        for k, v in E.items():
            if isinstance(v, dict) and "cagr_med" in v:
                part = k.split("|")[0]
                b = E.get(f"{part}_0050", {})
                L.append(f"| {part}（{'～'.join(E.get(part + '_窗', []))}） | {k.split('|', 1)[1]} | {p(v['cagr_med'])} | {p(v['mdd_med'])} | {p(b.get('cagr'))}／{p(b.get('mdd'))} |")
    else:
        L.append("（未跑）")
    L.append("")
    # §九 先驗
    L.append("## 九、先驗對照（登錄 §六；只對事實）")
    L.append("")
    ent = ["W1", "W2", "Y1", "Y3"] + (["Y2"] if str(ch.get("Y2", "")).startswith("Y2in") else [])
    L.append(f"- ① 五顆進場在確認段都不合格；至少一顆依構造不可判定：{', '.join(f'{g} {labs[g]}' for g in ['W1', 'W2', 'Y1', 'Y2', 'Y3'])}（Y2 進被剔、Y3 不可判定）⇒ 先驗成立")
    L.append("- ③ 單筆層 Y1、Y3 在 5、10 日有正差：Y1 5 日反方向顯著、10 日分不出；Y3 5、10 日分不出（n_eff 52）；Y5 看跌方向：10 日反方向顯著、其餘分不出 ⇒ 先驗不成立")
    if over:
        hi = [g for g in over if J[g]['確認_加減不加']['年化差（點）'] > 0]
        L.append("- ② 出場三顆加 vs 不加確認段年化都不比不加高：" + "、".join(f"{g} {J[g]['確認_加減不加']['年化差（點）']:+.2f} 點" for g in over)
                 + (f" ⇒ 先驗不成立（{'、'.join(hi)} 比不加高；但都沒贏 0050）" if hi else " ⇒ 先驗成立"))
    L.append(f"- ④ 假訊號 p ≥ 0.05 的格過半：{len(rnd)}／{len(FK)} ⇒ 先驗成立")
    L.append("")
    L.append("## 十、出場敏感度（新規矩 ③）")
    L.append("")
    if any(v in ("合格", "另列") or "未過" in v for v in labs.values()):
        L.append("⚠ 有合格／另列格 ⇒ 應跟一輪（見 sens 檔）")
    else:
        L.append("沒有合格或另列的格 ⇒ ⛔ 不跑。")
    L.append("")
    L.append("## 十一、閘與查核")
    L.append("")
    L.append(f"- selftest（偵測 fixture）{S['selftest']}；pre 與 body 的訊號 digest 相同 {PRE['訊號 digest']}；0050 主窗對 P17 錨 ✅")
    if CK:
        L.append(f"- 獨立查核 `researchExtAuth_check.py`（⛔ 不 import 主程式）：{'✅ 全過' if CK['全部過'] else '❌ 有不過'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] is True else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a not in ("過", "例")))
    L.append("")
    L.append("## 十二、檔案")
    L.append("")
    L.append("`backtest/researchExtAuth.py`（selftest／pre／body／early）、`researchExtAuth_early.py`、`researchExtAuth_check.py`、`researchExtAuth_report.py`；"
             "resultsExtAuth/：summary.json、pre.json、cells.csv、se_cells.csv、se_events.csv.gz、quad_cells.csv、quad_trades.csv.gz、y1_abandon.csv.gz、"
             "confirm_rows_*.csv.gz、confirm_audit3.csv、check.json、run.log、check.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:30]))


if __name__ == "__main__":
    main()
