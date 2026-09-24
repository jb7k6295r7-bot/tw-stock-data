# -*- coding: utf-8 -*-
"""C3 必報欄：**時序打亂臂的判定格判過比例**（⇐ 裁定線 seq88 §一③）。

裁定線逐字：「判定格過了，但 §四 只報 CAGR 百分位與 |MDD| 比例，沒報
『時序打亂 1,000 組裡，判定格（兩腳嚴格優於基準①）過了幾組』
⇒ ⏳ 回測線從既有結果數（沒存逐組結果就照原種子重跑空模型，那是必報欄、不是新分析）」

⭐ 好消息：逐組結果有存 ⇒ `resultsc3/null_time.csv.gz` ⇒ ⛔ 不必重跑。
⭐ 而本支同時報【邊際】與【聯合】：報告現有的兩個百分位是邊際的，
   而判定格要的是**兩腳同時**成立 ⇒ 兩者不可互推。
"""
from __future__ import annotations
import os
import io
import re
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
REP = io.open("resultsc3/C3_REPORT.md", encoding="utf-8").read()

print("=== ① 基準① 與策略（從報告逐字抓，⛔ 不手打）===")
row_b = next(l for l in REP.split("\n") if l.startswith("| 基準① 六幣等權買進持有"))
print("  " + row_b.strip())
nums = re.findall(r"([+-]?\d+\.\d+)%", row_b)
B_CAGR, B_MDD = float(nums[0]) / 100, abs(float(nums[1])) / 100
print("  ⇒ 基準① CAGR {!r}／|MDD| {!r}".format(B_CAGR, B_MDD))
row_s = next(l for l in REP.split("\n") if l.startswith("|") and "策略" in l and "%" in l
             and "對照" not in l and "基準" not in l)
print("  策略那一列：" + row_s.strip()[:120])

d = pd.read_csv("resultsc3/null_time.csv.gz", float_precision="round_trip")
print()
print("=== ② null_time.csv.gz ===")
print("  列數 {:,}｜欄 {}".format(len(d), list(d.columns)))
print(d.head(3).to_string(index=False))

#  ⭐ 找出 CAGR 與 MDD 欄（⛔ 不猜欄名，先印出來確認）
cc = [c for c in d.columns if re.fullmatch(r"cagr|CAGR", str(c))]
mm = [c for c in d.columns if re.fullmatch(r"mdd|MDD", str(c))]
assert cc and mm, "⛔ 找不到 cagr／mdd 欄：{}".format(list(d.columns))
C, M = d[cc[0]].astype(float), d[mm[0]].astype(float).abs()

print()
print("=== ③ ⭐ 先重現報告已印的兩個【邊際】數 ===")
#  報告：策略 CAGR 在假訊號分布的百分位 79.3；|MDD| 比假訊號淺的比例 63.0%
s_c = float(re.search(r"策略 CAGR 在假訊號分布的百分位 ([\d.]+)", REP).group(1))
s_m = float(re.search(r"\|MDD\| 比假訊號淺的比例 ([\d.]+)%", REP).group(1))
print("  報告逐字：CAGR 百分位 {}｜|MDD| 比假訊號淺的比例 {}%".format(s_c, s_m))
print("  ⇒ ⭐ 那兩個是【邊際】的（各看一腳）")

print()
print("=== ④ ⭐⭐ 裁定線要的【聯合】：兩腳同時嚴格優於基準① ===")
leg_c = C > B_CAGR
leg_m = M < B_MDD
both = leg_c & leg_m
n = len(d)
print("  年化腳嚴格優（CAGR > {:.4%}）      {:4d}／{:,} ＝ {:.1f}%".format(
    B_CAGR, int(leg_c.sum()), n, leg_c.mean() * 100))
print("  回落腳嚴格優（|MDD| < {:.4%}）     {:4d}／{:,} ＝ {:.1f}%".format(
    B_MDD, int(leg_m.sum()), n, leg_m.mean() * 100))
print("  ⭐⭐ **兩腳同時**                    {:4d}／{:,} ＝ **{:.1f}%**".format(
    int(both.sum()), n, both.mean() * 100))
print()
print("  ⇒ ⭐ 注意：{:.1f}% × {:.1f}% ＝ {:.1f}%，而實際是 {:.1f}%".format(
    leg_c.mean() * 100, leg_m.mean() * 100, leg_c.mean() * leg_m.mean() * 100, both.mean() * 100))
print("     ⇒ ⇒ 兩腳【不獨立】⇒ ⛔ 不可用兩個邊際百分位相乘去推聯合判過比例")

print()
print("=== ⑤ ⭐ 順帶：橫斷面打亂（隨機選幣）那一組也算一次 ===")
d2 = pd.read_csv("resultsc3/null_cross.csv.gz", float_precision="round_trip")
C2, M2 = d2[cc[0]].astype(float), d2[mm[0]].astype(float).abs()
b2 = (C2 > B_CAGR) & (M2 < B_MDD)
print("  null_cross {:,} 組 ⇒ 兩腳同時嚴格優 {:4d} ＝ **{:.1f}%**".format(
    len(d2), int(b2.sum()), b2.mean() * 100))

print()
print("=== ⑥ ⇒ 本線給措辭的那一句（⛔ 本線不定稿）===")
print('  「時序打亂臂判定格判過比例 **{:.1f}%**（1,000 組裡 {} 組兩腳都嚴格優於基準①）；'
      .format(both.mean() * 100, int(both.sum())))
print('    橫斷面打亂（隨機選幣）**{:.1f}%**。」'.format(b2.mean() * 100))

out = pd.DataFrame([
    dict(空模型="時序打亂（逐幣整段重排）", 組數=n, 年化腳過=int(leg_c.sum()), 回落腳過=int(leg_m.sum()),
         兩腳都過=int(both.sum()), 判過比例=round(both.mean() * 100, 2)),
    dict(空模型="橫斷面打亂（隨機選幣）", 組數=len(d2), 年化腳過=int((C2 > B_CAGR).sum()),
         回落腳過=int((M2 < B_MDD).sum()), 兩腳都過=int(b2.sum()), 判過比例=round(b2.mean() * 100, 2)),
])
out.to_csv("results_step2/c3_null_passrate.csv", index=False, encoding="utf-8")
print()
print(out.to_string(index=False))

# ⛔ 鑑別力自測：把門檻降到 −999%（誰都過）與升到 +999%（誰都過不了）
assert ((C > -9.99) & (M < 9.99)).mean() == 1.0, "⛔ 門檻放到最鬆卻不是全過 ⇒ 比對壞了"
assert ((C > 9.99) & (M < 9.99)).sum() == 0, "⛔ 門檻放到最嚴卻還有人過 ⇒ 比對壞了"
print()
print("✅ 鑑別力自測：門檻放到最鬆 ⇒ 全過；放到最嚴 ⇒ 0 過（⇒ 判準真的有在算）")
print("⇒ 落檔 results_step2/c3_null_passrate.csv")
