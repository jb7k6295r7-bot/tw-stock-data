# -*- coding: utf-8 -*-
"""舊 219 格【事後描述表】（裁定線 seq141 §三；⛔ 不是判過、⛔ 不改任何舊判定、⛔ 不計 N）

表頭逐字（seq141 §三）：「判準在看過這 219 格結果之後才改；本表只供挑候選，⛔ 不是判過」

新判準（seq141 §二）：條件一 年化 ＞ 0050（嚴格）；條件二 年化 ÷ |回落| ≥ 0050 同窗同一比值
  兩條都成立 ⇒ 合格｜只條件一 ⇒ 另列｜條件一不成立 ⇒ 不合格
本表讀法（本線寫死，看新判準下的標籤之前定）：
  ① 格值 ＝ 該格原交件印的那個數（多種子件 ＝ 年化中位、回落中位；比值 ＝ 中位 ÷ |中位|，⛔ 不是逐種子比值的中位）
  ② 0050 ＝ 該格原交件的【同窗】0050（seq141「同窗」）；各族窗不同 ⇒ 錨不同，逐列印出
  ③ 原交件只印到 0.1% 的錨或格值 ⇒ 以區間 [x−0.05pp, x+0.05pp] 判；標籤在區間內會變 ⇒ 標「捨入內不定」
  ④ 219 格的組成照 台股策略線 N 盤點 seq21（N_組合 ≥ 219）；PREREG11 只列 N30／N40（N10／20 與 PREREG10 同組態，seq17）
  ⑤ 年化波動：舊交件只存年化與回落 ⇒ 本表不回頭重跑；候選重驗時照 seq141 必報欄補
"""
import os, json
import numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
rows = []
EX = (0.24020209886370614, -0.3395700527611012)            # 釘死窗 0050（P17 W0 200/200 逐位元；AFC 同一條）


def add(fam, cell, c, m, ac, am, asrc, rc=0.0, ra=0.0, note=""):
    rows.append(dict(族=fam, 格=cell, 年化=c, 回落=m, 錨年化=ac, 錨回落=am, 錨出處=asrc, 格捨入=rc, 錨捨入=ra, 註=note))


def lab(c, m, ac, am):
    if not (c > ac):
        return "不合格"
    return "合格" if c / abs(m) >= ac / abs(am) else "另列"


def rl(x):
    return x if isinstance(x, str) else "null"


# PREREG10／PREREG11（results13／13b portfolio.csv 全窗；0050 +24.8%／−34.0%，2016-01-12～2026-09-11）
for f, fam, n0 in (("results13/portfolio.csv", "PREREG10／研究十三", 0), ("results13b/portfolio.csv", "PREREG11／研究十三b", 30)):
    d = pd.read_csv(f)
    for r in d[d.N >= n0].itertuples():
        add(fam, f"{r.set}｜regime={r.regime}｜N{r.N}｜{r.rule}", r.cagr, r.mdd, 0.248, -0.340, f"{f.split('/')[0]}/summary.md 89 行", ra=0.0005)
# PREREG9／研究十一（results11/CONCLUSIONS.md 組合層表，只印到 0.1%；0050 事後補 +24.9%／−34.0%）
for N, rule, c, m in [(5, "H20", 11.0, -58.2), (5, "H60", 21.4, -48.9), (5, "H120", 14.0, -52.9), (5, "LD", 16.8, -44.1),
                      (10, "H20", 14.3, -46.2), (10, "H60", 25.1, -42.3), (10, "H120", 15.4, -45.8), (10, "LD", 16.2, -36.7),
                      (20, "H20", 15.9, -38.5), (20, "H60", 22.6, -40.0), (20, "H120", 16.8, -40.5), (20, "LD", 15.4, -32.7)]:
    add("PREREG9／研究十一（事後補）", f"N{N}｜{rule}", c / 100, m / 100, 0.249, -0.340, "results11/CONCLUSIONS.md 133 行", rc=0.0005, ra=0.0005)
# PREREG15（results15/summary.md §六；0050 +24.6%／−34.0%，2016-01-07～2026-09-11）
for N, rule, c, m in [(5, "H20", 14.3, -45.4), (5, "H60", 21.6, -47.6), (10, "H20", 16.3, -34.6), (10, "H60", 19.1, -40.2), (20, "H20", 16.1, -27.4), (20, "H60", 16.7, -34.9)]:
    add("PREREG15", f"N{N}｜{rule}", c / 100, m / 100, 0.246, -0.340, "results15/summary.md 151 行", rc=0.0005, ra=0.0005)
# P 系列舊窗（0050 全窗 +24.54%／−34.0%）
A7 = (0.2454, -0.340)
for r in pd.read_csv("resultsp7/cells.csv").itertuples():
    add("P7 停損四族", f"N{r.N}｜{r.stop}" + ("（＝門檻B 本體 N=8）" if r.stop == "none" else ""), r.cagr, r.mdd, *A7, "resultsp7/P7_REPORT.md 56 行", ra=(0.00005, 0.0005))
for r in pd.read_csv("resultsp7/sensitivity.csv").itertuples():
    add("P7 敏感度", f"N{r.N}｜{r.stop}", r.cagr, r.mdd, *A7, "resultsp7/P7_REPORT.md 56 行", ra=(0.00005, 0.0005))
for r in pd.read_csv("resultsp7/baseline_gateB.csv").itertuples():
    if r.N != 8:                                            # N=8 none 與 P7 主表同組態 ⇒ 全專案算 1
        add("BASELINE 門檻B", f"N{r.N}｜{r.stop}", r.cagr, r.mdd, *A7, "resultsp7/BASELINE_REPORT.md 50 行", ra=(0.00005, 0.0005))
for r in pd.read_csv("resultsp9/cells.csv").itertuples():
    add("P9ⓑ", r.arm, r.cagr, r.mdd, *A7, "resultsp9/P9B_REPORT.md 66 行", ra=(0.00005, 0.0005))
for r in pd.read_csv("resultsp11/cells.csv").itertuples():
    add("P11", f"{r.sigset}｜{r.mode}｜{r.rate}", r.cagr, r.mdd, *A7, "resultsp11/P11_REPORT.md 66 行", ra=(0.00005, 0.0005))
for r in pd.read_csv("resultsp6/cells.csv").itertuples():
    add("P6", f"{r.set}｜N{r.N}", r.cagr, r.mdd, *A7, "resultsp6/P6_REPORT.md 11 行", ra=(0.00005, 0.0005))
# 釘死窗件（0050 ＝ +24.020210%／−33.957005%）
d = pd.read_csv("resultsp13/arms.csv")
for r in d[(d.win == "全窗") & d.arm.isin(["W0", "W1"])].itertuples():
    add("P13", f"{r.arm}｜全窗", r.cagr_med, r.mdd_med, *EX, "P13_REPORT.md 35 行（+24.02%）；回落取釘死值")
for r in pd.read_csv("resultsp14/w_summary.csv").itertuples():
    add("P14", f"w={r.w:.2f}" + ("（＝0050 本身）" if r.w == 0 else "（＝各半混 0050）" if r.w == 0.5 else ""), r.cagr_med, r.mdd_med, *EX, "resultsp14/w_summary.csv w=0 列")
d = pd.read_csv("resultsp15/summary.csv")
for r in d[d["臂"].isin(["G0", "G1"])].itertuples():
    add("P15", r[1], r.cagr_med, r.mdd_med, *EX, "P15_REPORT.md 52 行")
d = pd.read_csv("resultsp16/summary.csv")
for r in d[d["臂"] != "R1"].itertuples():
    add("P16", r[1], r.cagr_med, r.mdd_med, *EX, "P16_REPORT.md 268 行")
d = pd.read_csv("resultsp17/per_seed_arm.csv").groupby("arm")[["cagr", "mdd"]].median()
add("P17", "R_eq（判定格）", d.loc["R_eq", "cagr"], d.loc["R_eq", "mdd"], *EX, "P17_REPORT.md 15 行（W0 逐位元）")
add("P17", "W_fix（w＝0.5 各半混 0050；事後比判準）", d.loc["W_fix", "cagr"], d.loc["W_fix", "mdd"], *EX, "P17_REPORT.md 15 行（W0 逐位元）")
d = pd.read_csv("results_d4/cells.csv")
for t, nm in ((False, "S1′｜tradable off"), (True, "S1′｜tradable on")):
    g = d[(d.arm == "S1p") & (d.tradable == t)]
    add("D4", nm, g.cagr.median(), g.mdd.median(), *EX, "D4 交件未印 0050 值 ⇒ 取釘死窗", note="年化約 20%，對 24.0～24.9 任一錨標籤都不變")
d = pd.read_csv("resultsp1/portfolio.csv")
for r in d.itertuples():
    ac = (0.241, "resultsp1/summary.md AND 0050 行（2017-02-13 起）") if r.set == "AND" else (0.248, "resultsp1/summary.md S 0050 行（2016-01-12 起）")
    add("P1", f"{r.set}｜N{r.N}｜d={r.d}｜{rl(r.rule)}", r.cagr, r.mdd, ac[0], -0.340, ac[1], ra=0.0005)
d = pd.read_csv("resultsp3/summary.csv", comment="#")
for r in d[d.cell != "對照格（輸）"].itertuples():
    add("P3 乙臂（閒置放 0050）", f"{r.cell}｜N{r.N}｜d={r.d}｜{rl(r.rule)}", r.B_cagr_med, r.B_mdd_med, 0.241, -0.340, "PREREGP3.md 103 行（2017-02-13～2026-09-11）", ra=0.0005)
for k in ("Δ_β", "Δ_ind", "Δ_stk", "Δ_vol"):
    add("PREREGI", k, np.nan, np.nan, *EX, "—", note="反事實回落拆解量，不是一條權益曲線 ⇒ 新判準無從套用")
add("PREREGA", "A 單一路徑", 0.1764, -0.3323, *EX, "AFC_REPORT.md 14 行", rc=0.00005)
f = pd.read_csv("resultsAFC/f_and_fake.csv"); f = f[f.arm == -1]
add("PREREGF", "F 200 顆中位", f.cagr.median(), f.mdd.median(), *EX, "AFC_REPORT.md 14 行")
add("PREREGC", "C 單一路徑", 0.2462, -0.4151, *EX, "AFC_REPORT.md 14 行", rc=0.00005)
d = pd.read_csv("resultsD5/d5_200.csv")
add("PREREGD5", "D5 200 顆中位", d.cagr.median(), d.mdd.median(), *EX, "D5_REPORT.md 15 行")

T = pd.DataFrame(rows)
assert len(T) == 219, len(T)
out = []
for r in T.itertuples():
    if not np.isfinite(r.年化):
        out.append(("—（無從套用）", False, np.nan, np.nan)); continue
    ea, eb = r.錨捨入 if isinstance(r.錨捨入, tuple) else (r.錨捨入, r.錨捨入)
    L = {lab(r.年化 + a, r.回落 + b, r.錨年化 + e, r.錨回落 + g) for a in (-r.格捨入, r.格捨入) for b in (-r.格捨入, r.格捨入) for e in (-ea, ea) for g in (-eb, eb)}
    out.append((lab(r.年化, r.回落, r.錨年化, r.錨回落), len(L) > 1, r.年化 / abs(r.回落), r.錨年化 / abs(r.錨回落)))
T["新判準標籤"], T["捨入內不定"], T["比值"], T["錨比值"] = zip(*out)
T["年化差pp"] = (T.年化 - T.錨年化) * 100
T["回落差pp（負＝比0050深）"] = (T.回落 - T.錨回落) * 100
T["年化波動"] = "未存"
os.makedirs("resultsN219", exist_ok=True)
T.to_csv("resultsN219/table219.csv", index=False, encoding="utf-8")
print(T["新判準標籤"].value_counts().to_string()); print("捨入內不定", int(T["捨入內不定"].sum()))
print(T.groupby("族")["新判準標籤"].value_counts().unstack(fill_value=0).to_string())
q = T[T["新判準標籤"].isin(["合格", "另列"])].sort_values(["新判準標籤", "比值"], ascending=[True, False])
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
print(q[["族", "格", "年化", "回落", "比值", "錨年化", "錨比值", "新判準標籤", "捨入內不定"]].to_string())

# ---- 交件 md ----
T["同值組"] = T.groupby([T.年化.round(12), T.回落.round(12)]).ngroup()
dup = T[T.年化.notna()].groupby("同值組").filter(lambda g: len(g) > 1)
dupmap = {k: "、".join(f"{a}〔{b}〕" for a, b in zip(g.族, g.格)) for k, g in dup.groupby("同值組")}
pp = lambda x: f"{x * 100:+.2f}%"
L = ["# 舊 219 格【事後描述表】——照 seq141 新判準逐格標", "",
     "> **判準在看過這 219 格結果之後才改；本表只供挑候選，⛔ 不是判過**", "",
     "依據：裁定線 seq141 §三。程式 `backtest/table219.py`，逐格表 `backtest/resultsN219/table219.csv`（219 列）。⛔ 不改任何舊判定、⛔ 不計 N。", "",
     "## 一、讀法（本線寫死，⛔ 未改判準本身）", "",
     "- 新判準（seq141 §二）：條件一 年化 ＞ 0050（嚴格）；條件二 年化 ÷ |回落| ≥ 0050 同窗同一比值。兩條都成立 ⇒ **合格**；只條件一 ⇒ **另列**；條件一不成立 ⇒ **不合格**",
     "- 格值 ＝ 該格原交件印的數。多種子件 ＝ 年化中位、回落中位；比值 ＝ 中位 ÷ |中位|，⛔ 不是逐種子比值的中位",
     "- 0050 ＝ 該格原交件的**同窗** 0050；各族窗不同 ⇒ 錨不同（24.02～24.9%），逐列印在 csv 的「錨年化／錨回落／錨出處」",
     "- 原交件只印到 0.1% 的錨或格值 ⇒ 以 ±0.05pp 區間判（印到 0.01% 的 ⇒ ±0.005pp）；區間內標籤會變 ⇒ 標「捨入內不定」",
     "- 219 格組成照 台股策略線 N 盤點 seq21；PREREG11 只列 N30／N40（N10／20 與 PREREG10 同組態，盤點 seq17）；BASELINE 不列 N=8（與 P7 主表 N8 none 同組態）",
     "- 年化波動：舊交件只存年化與回落 ⇒ 本表 **未報**（⛔ 不回頭重跑 219 格）；候選重驗時照 seq141 必報欄補", "",
     "## 二、總數", "", "| 標籤 | 格數 |", "|---|---:|"]
for k in ("合格", "另列", "不合格", "—（無從套用）"):
    L.append(f"| {k} | {int((T['新判準標籤'] == k).sum())} |")
L += ["", f"捨入內不定：{int(T['捨入內不定'].sum())} 格（見 §五）。無從套用 4 ＝ PREREGI 四個 Δ（反事實回落拆解量，不是一條權益曲線）。", "",
      "### 逐族", "", "| 族 | 合格 | 另列 | 不合格 | 無從套用 |", "|---|---:|---:|---:|---:|"]
for fam, g in T.groupby("族", sort=False):
    v = g["新判準標籤"].value_counts()
    L.append(f"| {fam} | {v.get('合格', 0)} | {v.get('另列', 0)} | {v.get('不合格', 0)} | {v.get('—（無從套用）', 0)} |")
L += ["", "## 三、合格（按比值由高到低）", "",
      "⚠ 合格 ＝ 事後在同一段歷史上落入新判準 ⇒ 只是**候選**；要在沒看過的資料上重驗才可對使用者說可用（seq141 §三）。", "",
      "| # | 族 | 格 | 年化 | 回落 | 比值 | 0050 同窗 | 0050 比值 | 對 0050 | 同值組 |", "|---:|---|---|---:|---:|---:|---|---:|---|---|"]
q = T[T["新判準標籤"] == "合格"].sort_values("比值", ascending=False)
for i, r in enumerate(q.itertuples(), 1):
    dd = r.回落 - r.錨回落
    s = f"報酬多 {(r.年化 - r.錨年化) * 100:.2f} 點、" + (f"回落比 0050 深 {-dd * 100:.2f} 點" if dd < 0 else f"回落淺 {dd * 100:.2f} 點")
    L.append(f"| {i} | {r.族} | {r.格} | {pp(r.年化)} | {pp(r.回落)} | {r.比值:.3f} | {pp(r.錨年化)}／{pp(r.錨回落)} | {r.錨比值:.3f} | {s} | {'見 §六' if r.同值組 in dupmap else ''} |")
L += ["", "## 四、另列（賺得比 0050 多，但風險增加得比報酬多；附年化、回落、比值三數）", "",
      "| # | 族 | 格 | 年化 | 回落 | 比值 | 0050 比值 | 捨入內不定 |", "|---:|---|---|---:|---:|---:|---:|---|"]
q = T[T["新判準標籤"] == "另列"].sort_values("比值", ascending=False)
for i, r in enumerate(q.itertuples(), 1):
    L.append(f"| {i} | {r.族} | {r.格} | {pp(r.年化)} | {pp(r.回落)} | {r.比值:.3f} | {r.錨比值:.3f} | {'⚠' if r.捨入內不定 else ''} |")
L += ["", "## 五、捨入內不定", ""]
for r in T[T["捨入內不定"]].itertuples():
    L.append(f"- {r.族}〔{r.格}〕：年化 {pp(r.年化)}／回落 {pp(r.回落)}，比值 {r.比值:.4f} vs 錨比值 {r.錨比值:.4f}（錨只印到 0.1%）⇒ 標 {r.新判準標籤}，±0.05pp 內會變")
L += ["", "## 六、同值組（不同族印的是同一個數 ⇒ 同一條權益曲線被計成多格；挑候選時只算一條）", ""]
for k, s in dupmap.items():
    L.append(f"- {s}")
L += ["", "## 七、seq141 點名的格（門檻B 本體、各半混 0050、P17）", ""]
for fam, cell in (("P7 停損四族", "N8｜none（＝門檻B 本體 N=8）"), ("P14", "w=0.50（＝各半混 0050）"), ("P17", "W_fix（w＝0.5 各半混 0050；事後比判準）"), ("P17", "R_eq（判定格）")):
    r = T[(T.族 == fam) & (T.格 == cell)].iloc[0]
    L.append(f"- {fam}〔{cell}〕：{pp(r.年化)}／{pp(r.回落)}、比值 {r.比值:.3f} vs 0050 {r.錨比值:.3f} ⇒ **{r.新判準標籤}**")
L.append("- 裁定線 §三 先算的門檻B（策略線公告 +27.79%／−41.8% 對 0050 +24.02%／−33.96%）⇒ 0.665 ＜ 0.707 ⇒ 另列；本線自算那一格（上列第一條，0050 同窗 +24.54%／−34.0%）⇒ 同為另列")
L += ["", "## 八、⛔ 這張表不能拿來說的話", "",
      "- ⛔ 不是判過：判準是看過這 219 格才改的；在同一段歷史上挑出來的格，本來就會偏好看",
      "- ⛔ 多重比較未調整：219 格裡挑最好的，靠運氣也會挑出幾格；Bonferroni 按格、累計 N 的規則不因本表而變",
      "- ⚠ 合格格裡有一批是原登錄寫「只走統計層」的（如 P1 的 N30／N40，登錄說不是使用者可執行的槽數）⇒ 能不能當候選由台股策略線／裁定線定，⛔ 本線不挑"]
open("resultsN219/TABLE219.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("md", len(L), "行；同值組", len(dupmap))
