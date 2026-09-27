# -*- coding: utf-8 -*-
"""PREREG強勢類股 REPORT.md 產生器（只讀 resultsSector/ 的 body.json、cells.csv、coverage.csv、check.json；⛔ 不重算）。

    python -m backtest.researchSector_report
"""
from __future__ import annotations
import os, json
import pandas as pd

OUT = "backtest/resultsSector"
PKN = {"a": "(a) 同回看期漲最多", "b": "(b) 營收創 24 月新高"}


def p(x, d=2):
    return "—" if x is None or x != x else f"{x * 100:+.{d}f}%"


def main():
    J = json.load(open(os.path.join(OUT, "body.json"), encoding="utf-8"))
    C = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    PRE = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    ck, L, k, pk = J["探索挑格"]["挑中"], J["探索挑格"]["L"], J["探索挑格"]["k"], J["探索挑格"]["挑法"]
    Z = J["0050"]; cf = J["確認"]; lab = cf["判定"]; pf = J["假訊號p_確認"]
    S = J["對照"]; OV = J["營量v1"]
    if lab == "合格":
        sent = f"先挑最強的 {k} 個類股、再挑{PKN[pk]}，2022～2026 年化 {p(cf['年化'])}／回落 {p(cf['回落'])}，贏 0050 且風險調整後不輸"
    elif lab == "另列":
        sent = "報酬贏 0050，但回落比例上不划算"
    else:
        sent = "用類股強度找股票，沒有贏 0050"
    if pf >= 0.05:
        sent = "隨機挑類股也做得到；" + sent
    nocls = J["類股覆蓋"]["無類股占eligible股月"]
    L_ = []
    L_.append("# PREREG強勢類股（先找最強類股、再在裡面挑股票）：本體＋獨立查核")
    L_.append("")
    L_.append(f"**結論：{sent}。**（探索段 18 格挑中 `{ck}`＝回看 {L} 日、前 {k} 強類股、{PKN[pk]}；確認段判定【{lab}】；"
              f"假訊號臂 p ＝ {pf:.3f}（隨機挑 {k} 個類股、同挑法的 1,000 次裡，確認段年化不輸本格的占 {pf * 100:.1f}% ⇒ 照登錄前加「隨機挑類股也做得到」）；早年段依構造做不了、未跑。）")
    L_.append("")
    if k == 1:
        mm = T[(T["格"] == ck) & (T["版本"] == "月換續抱") & (T["段"] == "確認")].iloc[0]
        L_.append(f"⚠ 挑中的正是 k＝1 硬傷格之一：探索段 18 格【沒有一格過判準】（過判準 {J['探索挑格']['過判準格數']}／18）⇒ 照登錄取年化÷|MDD| 最高者，"
                  f"而它是平均只持 {mm['平均持股']:.1f} 檔、現金 {mm['現金比例'] * 100:.0f}% 的格（比值高來自現金壓低回落，⛔ 不是類股強度選得準）。")
        L_.append("")
    L_.append("| | 年化 | 最大回落 | 年化÷\\|MDD\\| |")
    L_.append("|---|---|---|---|")
    ex = J["探索挑格"]["探索"]
    L_.append(f"| 挑中格 `{ck}`・探索段 2017-03-02～2021-12-30 | {p(ex['年化'])} | {p(ex['回落'])} | {ex['比值']:.3f} |")
    L_.append(f"| 0050・探索段 | {p(Z['探索']['年化'])} | {p(Z['探索']['回落'])} | {Z['探索']['比值']:.3f} |")
    L_.append(f"| **挑中格・確認段 2022-01-03～2026-08-24（判定）** | **{p(cf['年化'])}** | **{p(cf['回落'])}** | **{cf['比值']:.3f}** |")
    L_.append(f"| 0050・確認段（判準） | {p(Z['確認']['年化'])} | {p(Z['確認']['回落'])} | {Z['確認']['比值']:.3f} |")
    L_.append(f"| 營量 v1（#13）・確認段 | {p(OV['確認']['營量v1_年化'])} | {p(OV['確認']['營量v1_回落'])} | {OV['確認']['營量v1_比值']:.3f} |")
    L_.append(f"| 假訊號臂（隨機 {k} 個類股、同挑法）確認段中位（1,000 次） | {p(S['fake_確認']['中位'])} | {p(S['fake_確認']['回落中位'])} | — |")
    L_.append(f"| (c) 同 {k} 強類股內隨機 10 檔・確認段中位（1,000 次） | {p(S['c_確認']['中位'])} | {p(S['c_確認']['回落中位'])} | — |")
    L_.append("")
    L_.append("```")
    L_.append("⚠ 逐字標註（協調 2026-09-27 指示）：")
    L_.append("  ・產業別用今日快照（2022 新增類別往回套）")
    L_.append(f"  ・已下市股沒有類股、無法入選，占 eligible 股-月 2.5%（pre 量的全期；本體窗 2017-03～2026-08 重量 {nocls * 100:.1f}%，"
              f"{J['類股覆蓋']['無類股股月']:,}／{J['類股覆蓋']['eligible股月']:,}，其中已下市 {J['類股覆蓋']['無類股且已下市股月']:,} 股-月）")
    L_.append("  ⇒ 登錄 §二「含已下市股」這一部分做不到（已下市股大多不在 industry.csv ⇒ 無類股 ⇒ 不能被排名也不能入選），照實寫")
    L_.append("⚠ k＝1 那 6 格的依構造硬傷：類股集中度依構造 100%（10 檔全在同一個類股）；(b) 挑法在單一類股裡符合營收新高的常不足 10 檔")
    L_.append("  ⇒ 平均只持 2～3 檔、現金 7 成上下、有整月空手 ⇒ 依構造幾乎不可能贏 0050。照登錄仍然參加探索段挑選（見 §一）。")
    L_.append("```")
    L_.append("")
    # 12 處
    L_.append("## 〇、12 處未列預設與定案值（協調 2026-09-27：照暫定 (i) 全部定案，另補三點）")
    L_.append("")
    L_.append("| # | 預設 | 定案值 |")
    L_.append("|---|---|---|")
    rows12 = [
        ("U1 ★", "換股日仍入選的舊持股", "(i) 續抱、只賣落選、買新入選、⛔ 不再平衡（主版）；(ii) 全賣全買另報成本敏感度、只描述（§二）"),
        ("U2 ★", "抱 60 日怎麼組", "(i) 每月換股日買一批、各抱 60 個交易日、10 槽滿了就不買（simulate_mtm、tradable＋delist）"),
        ("U3", "季換的月份", "(i) 1、4、7、10 月的換股日"),
        ("U4 ★", "eligible 用哪一天", "(i) 同月第一個交易日量測的 W1 eligible；面板改用 resultsp9_engine/panel_ext.csv.gz（d2c9df7fe2，量測日到 2026-08-03）；"
                                    f"2026-03-02 以前與 resultsAFC 逐列相同：{'✅' if J['U4 對帳']['逐列相同（measure_date、stock_id、market、eligible）'] else '❌'}"
                                    f"（{J['U4 對帳']['panel_ext 列數']:,} 列、eligible 真 {J['U4 對帳']['panel_ext eligible 真']:,}）"),
        ("U5 ★", "產業別", "(i) 產業別用今日快照（2022 新增類別往回套）；金融保險業／金融業 ⇒ 金融保險；存託憑證排除"),
        ("U6 ★", "已下市股沒有類股", "(i) 無類股 ⇒ 不能被排名也不能入選（⇒ 登錄「含已下市」做不到，照實寫）"),
        ("U7", "類股強度的算法", "(i) 成分股各自 L 日報酬（ffill 還原收盤、截至換股日前一交易日）等權平均；成分 ＝ 當月 eligible 且有類股；成分 ＜ 5 不排名"),
        ("U8", "(a)(b) 前 10 檔的範圍", "(i) 前 k 強類股的聯集裡一起排；同值依代號"),
        ("U9", "現金報酬", "(i) 0"),
        ("U10", "(c) 與假訊號臂的種子", "(i) default_rng(20260925＋r)，r＝0…999"),
        ("U11", "探索段挑格的平手", "(i) 年化高者、再 L 小、k 小、(a) 先"),
        ("U12", "早年段", "(i) 依構造做不了（data/early 沒有全體個股還原事件 TWT49U 與個股法人 inst_ok）⇒ 寫明、不跑"),
    ]
    for a, b, c in rows12:
        L_.append(f"| {a} | {b} | {c} |")
    L_.append("")
    L_.append(f"其餘：營收 24 月新高 ＝ p4_features.rev_hi24_flags 在換股日 ＝ 100（營飆／營量同條件、同可得日）；換手 ＝ 每次換股新買進檔數 ÷ 10；"
              f"快照 {J['快照'][:10]}；成本來回 0.585%（賣出時扣進場金額 × 0.585%，與 simulate_mtm 同口徑）；段落指標在同一條連續權益（2017-03-02 起）上切段、245 日／年。")
    L_.append("")
    # §一 18 格
    def tbl(var, seg):
        d = T[(T["版本"] == var) & (T["段"] == seg)]
        out = ["| 格 | 年化 | 回落 | 比值 | 每月換手 | 平均持股 | 現金 | 集中度 平均／最大 |", "|---|---|---|---|---|---|---|---|"]
        for r in d.itertuples():
            mark = " ⭐" if r.格 == ck else ""
            out.append(f"| {r.格}{mark} | {p(r.年化)} | {p(r.回落)} | {r.比值:.3f} | {r.每月換手 * 100:.0f}% | {r.平均持股:.1f} | {r.現金比例 * 100:.0f}% | "
                       f"{r.集中度_平均 * 100:.0f}%／{r.集中度_最大 * 100:.0f}% |")
        return out
    L_.append(f"## 一、18 格（月換、續抱＝主版）")
    L_.append("")
    L_.append(f"### 探索段（挑格；0050 同段 {p(Z['探索']['年化'])}／{p(Z['探索']['回落'])}／{Z['探索']['比值']:.3f}；過判準 {J['探索挑格']['過判準格數']}／18）")
    L_.append("")
    L_ += tbl("月換續抱", "探索")
    L_.append("")
    L_.append(f"### 確認段（⛔ 只有 ⭐ 那一格是判定；其餘 17 格只描述；0050 同段 {p(Z['確認']['年化'])}／{p(Z['確認']['回落'])}／{Z['確認']['比值']:.3f}）")
    L_.append("")
    L_ += tbl("月換續抱", "確認")
    L_.append("")
    # §二 變體
    L_.append("## 二、天數軸與成本敏感度（只描述）")
    L_.append("")
    L_.append("| 格 | 段 | 月換續抱（主） | 月換全賣全買 (ii) | 季換續抱 | 抱 60 日 |")
    L_.append("|---|---|---|---|---|---|")
    for g in T["格"].unique():
        for seg in ("探索", "確認"):
            v = {var: T[(T["格"] == g) & (T["段"] == seg) & (T["版本"] == var)].iloc[0] for var in ("月換續抱", "月換全賣全買", "季換續抱", "抱60日")}
            mark = " ⭐" if g == ck else ""
            L_.append(f"| {g}{mark} | {seg} | " + " | ".join(f"{p(x['年化'])}／{p(x['回落'])}" for x in v.values()) + " |")
    L_.append("")
    m1 = T[(T["格"] == ck) & (T["版本"] == "月換續抱") & (T["段"] == "確認")].iloc[0]
    m2 = T[(T["格"] == ck) & (T["版本"] == "月換全賣全買") & (T["段"] == "確認")].iloc[0]
    L_.append(f"挑中格確認段：全賣全買比續抱年化差 {(m2['年化'] - m1['年化']) * 100:+.2f} 個百分點（成本 ＋ 回到等權兩者合計，⛔ 不拆）。")
    L_.append("")
    # §三 挑中格必報
    L_.append(f"## 三、挑中格 `{ck}` 必報")
    L_.append("")
    L_.append("| 年 | 挑中格 | 0050 |")
    L_.append("|---|---|---|")
    for y, v in J["挑中格各年"].items():
        L_.append(f"| {y} | {p(v)} | {p(J['0050各年'][y])} |")
    L_.append("")
    for seg in ("探索", "確認"):
        L_.append(f"最常入選的類股前 5（{seg}段，換股後持股的股-月）：" + "、".join(f"{c}（{n_}，{s * 100:.0f}%）" for c, n_, s in J["挑中格類股前5"][seg]))
        L_.append("")
    L_.append("與營量 v1（#13：P1 AND｜N20｜d=inf｜relvol｜H60；resultsYfMix13 的 eq_main.npz 與 positions.csv.gz）同段：")
    L_.append("")
    L_.append("| 段 | 營量 v1 年化／回落／比值 | 重疊 ÷ 本格持股（逐日均值） | 重疊 ÷ 營量 v1 持股 | 同時持有檔數 | 營量 v1 持股數 |")
    L_.append("|---|---|---|---|---|---|")
    for seg, v in OV.items():
        L_.append(f"| {seg} | {p(v['營量v1_年化'])}／{p(v['營量v1_回落'])}／{v['營量v1_比值']:.3f} | {v['重疊÷本格持股_逐日均值'] * 100:.1f}% | "
                  f"{v['重疊÷營量v1持股_逐日均值'] * 100:.1f}% | {v['同時持有檔數_逐日均值']:.2f} | {v['營量v1持股數_逐日均值']:.1f} |")
    L_.append("")
    cn = J["挑中格計數"]
    L_.append(f"成交計數（全窗）：買 {cn['buy']:,}、賣 {cn['sell']:,}；開盤漲停擋買 {cn['buy_blocked_limit_up']}、停牌擋買 {cn['buy_blocked_halt']}（名額持現金、⛔ 不遞補）；"
              f"延後賣的日數 {cn['sell_delayed_days']}；下市以最後收盤了結 {cn['delist_settled']}；ambig 照停牌的日數 {cn['delist_ambig_days']}。")
    L_.append("")
    # §四 對照
    L_.append("## 四、對照（登錄 §四）")
    L_.append("")
    L_.append("| 臂（1,000 次，種子 20260925＋r） | 段 | 中位 | p10～p90 | 本格年化 | 年化 ≥ 本格的比例 | 贏 0050 同段的比例 |")
    L_.append("|---|---|---|---|---|---|---|")
    for arm, nm in (("fake", f"③ 假訊號：隨機 {k} 個可排名類股、同挑法"), ("c", f"④ (c) 前 {k} 強類股聯集內隨機 10 檔")):
        for seg in ("探索", "確認"):
            v = S[f"{arm}_{seg}"]
            L_.append(f"| {nm} | {seg} | {p(v['中位'])} | {p(v['p10'])}～{p(v['p90'])} | {p(v['本格年化'])} | {v['p（年化 ≥ 本格的比例）']:.3f} | {v['贏0050同段的比例'] * 100:.1f}% |")
    L_.append("")
    fc, cc = S["fake_確認"], S["c_確認"]
    L_.append(f"拆解（確認段、描述）：挑中格 {p(fc['本格年化'])}；(c) 同類股隨機中位 {p(cc['中位'])} ⇒「挑對個股」≈ {(fc['本格年化'] - cc['中位']) * 100:+.2f} 個百分點；"
              f"假訊號（隨機類股、同挑法）中位 {p(fc['中位'])} ⇒「挑對類股」≈ {(fc['本格年化'] - fc['中位']) * 100:+.2f} 個百分點（兩者都是對各自中位、⛔ 不可相加）。")
    L_.append(f"假訊號 p（確認段年化 ≥ 本格的比例）＝ {pf:.3f} ⇒ {'≥ 0.05 ⇒ 結果句前加「隨機挑類股也做得到」' if pf >= 0.05 else '< 0.05'}。")
    L_.append("")
    # §五 敏感度
    L_.append("## 五、出場與檔數敏感度（seq242 ②）")
    L_.append("")
    if lab in ("合格", "另列"):
        L_.append("⚠ 判定為合格／另列 ⇒ 應跟進（見 sens 檔）。")
    else:
        L_.append(f"判定【{lab}】⇒ 登錄 §一：停損停利、檔數 {{5, 10, 20}} 只在合格／另列時跟進 ⇒ ⛔ 不跑。")
    L_.append("")
    L_.append("## 六、早年段")
    L_.append("")
    L_.append("U12 定案：data/early 沒有全體個股的還原事件（TWT49U）與個股法人（W1 eligible 的 inst_ok 要用）⇒ W1 母體與還原價依構造做不出來 ⇒ ⛔ 不跑，寫明。")
    L_.append("")
    L_.append("## 七、先驗對照（登錄 §六，寫下不改；這裡只對事實）")
    L_.append("")
    cmax = T[(T["格"] == ck) & (T["版本"] == "月換續抱") & (T["段"] == "確認")]["集中度_最大"].iloc[0]
    L_.append(f"- ① 確認段不合格或只另列：實際【{lab}】")
    L_.append(f"- ② 若有贏、貢獻主要來自 (b) 而不是類股強度：前提「有贏」{'不成立' if lab == '不合格' else '成立'}；挑中格挑法 {pk}；(c) 類股內隨機確認段中位 {p(cc['中位'])}、假訊號中位 {p(fc['中位'])}（0050 {p(Z['確認']['年化'])}）")
    L_.append(f"- ③ 挑中格同類股占比最大值 ≥ 50%：確認段最大 {cmax * 100:.0f}%")
    L_.append("")
    L_.append("## 八、閘與查核")
    L_.append("")
    L_.append(f"- 模擬器 fixture {J['selftest']}（常數價只剩成本、已知報酬、續抱 vs 全賣全買成本差手算、漲停擋買不遞補、跌停延後賣、下市以最後收盤了結、ambig 照停牌、金額 ＝ 前一日 equity ÷ 10）")
    L_.append(f"- 0050 主窗 2017-03-02～2026-08-24 對 P17 W0 錨（+24.02%／-33.96%）逐位元：{'✅' if J['0050主窗對錨'] else '❌'}")
    L_.append(f"- U4 對帳：量測日 ≤ 2026-03-02 的 {J['U4 對帳']['resultsAFC 列數']:,} 列逐列相同 ✅；panel_ext 另有 {', '.join(J['U4 對帳']['panel_ext 2026-03-02 之後的量測日'])}")
    L_.append(f"- ⚠ 查核抓到並已修：industry.csv 有 40 列 industry_name 空白、只有代碼（32 文化創意業 {J['產業別']['名稱空白依代碼補']['32']} 檔、"
              f"33 農業科技 {J['產業別']['名稱空白依代碼補']['33']} 檔、91 存託憑證 {J['產業別']['名稱空白依代碼補']['91']} 檔）。第一次本體（未 commit）與 pre 段把這 40 檔併成同一個 NaN「類股」"
              "（⛔ 不是 U5 定案的「照原名」），查核③名單在 10 個格×換股日對不上而抓到。本體改為依代碼補名稱（類股 34 個）後重跑，查核全過。"
              "修正前的第一次本體：挑中格同為 L60_k1_b，探索 +18.11%／-28.15%／0.644、確認 +10.14%／-23.85%／0.425、判定同為不合格、假訊號 p＝0.258 ⇒ 結論不變。"
              "pre 段的檔案（PRE_REPORT.md、pre.json 的「33 個類股」含這個 NaN 組）保持原樣、⛔ 不重跑。")
    if C:
        L_.append(f"- 獨立查核 `researchSector_check.py`（⛔ 不 import 主程式）：{'✅ 全過' if C['全部過'] else '❌ 有不過'}")
        for k_, v in C.items():
            if isinstance(v, dict):
                L_.append(f"  - {k_}：{'✅' if v['過'] else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a not in ('過', '例')))
    L_.append("")
    L_.append("## 九、檔案")
    L_.append("")
    L_.append("`backtest/researchSector.py`（pre／selftest／body）、`backtest/researchSector_check.py`、`backtest/researchSector_report.py`；"
              "resultsSector/：body.json、cells.csv（18 格 × 4 版本 × 2 段）、picks.csv.gz（每格每換股日的名單）、eq_cells.npz（逐日權益）、"
              "controls.csv.gz（對照 2,000 次）、coverage.csv、recon.json、check.json、body.log、check.log；pre 段檔案不動。")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L_) + "\n")
    print("\n".join(L_[:20]))


if __name__ == "__main__":
    main()
