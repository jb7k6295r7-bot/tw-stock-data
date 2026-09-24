# -*- coding: utf-8 -*-
"""D4 池子對帳三件（⇐ 裁定線 1950 §一）：
 ① |A∪B| 是多少、與 2,039 清單差哪幾檔
 ② 1,586 與 1,587 差的那一檔是誰、為什麼
 ③ S0_pool 用 2,037、清單 2,039 ⇒ 少的 2 檔是誰
⛔ 純對帳，不改任何池子定義（裁定線：清單為準）。"""
import os, sys, re
import pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F, researchp12 as P12

cal = D.load_calendar(); pos = {d: i for i, d in enumerate(cal)}
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
panel["measure_date"] = pd.to_datetime(panel["measure_date"])
panel["pos"] = panel["measure_date"].map(pos)
uni = D.load_universe()
nm = dict(zip(uni["stock_id"].astype(str), uni["name"].astype(str)))

W0, W1 = 523, 2835
w = panel[panel["pos"].notna() & (panel["pos"] >= W0) & (panel["pos"] <= W1)]
A = set(w.loc[w["eligible"].astype(bool), "stock_id"].astype(str))     # 判定窗內曾 eligible
g = pd.read_csv("backtest/resultsd4_gate.csv", dtype=str)
B = set(g.loc[(g["direction"] == "新進來") & (g["fam2"].str.contains("沒過閘門", na=False)), "stock_id"])
print("=== ① |A ∪ B|（台股策略線 1944 §三 的構造）===")
print("  A ＝ 判定窗 [{},{}] 內曾 eligible ＝ **{:,} 檔**".format(W0, W1, len(A)))
print("  B ＝ 本線 1511 量的新增普通股 ＝ **{:,} 檔**".format(len(B)))
print("  A ∩ B ＝ {} 檔（⭐ 應為 0：B 的定義就是「沒過閘門」）".format(len(A & B)))
print("  ⇒ **|A ∪ B| ＝ {:,}**  ⇒ {}".format(len(A | B), "✅ 等於 2,039，閘門過" if len(A | B) == 2039 else "⛔ 不等於 2,039"))

print()
print("=== ② 1,586 vs 1,587 差的那一檔 ===")
p17 = panel[panel["measure_date"] >= pd.Timestamp(P12.START)]
S0 = set(p17.loc[p17["eligible"].astype(bool), "stock_id"].astype(str))   # 本線 1931 §二 的 1,587
print("  本線 1511（A）：判定窗 [523,2835] 內曾 eligible          ＝ {:,} 檔".format(len(A)))
print("  本線 1931（S0）：measure_date ≥ {} 且 eligible          ＝ {:,} 檔".format(P12.START, len(S0)))
d1, d2 = S0 - A, A - S0
for lab, s in (("S0 有而 A 沒有", d1), ("A 有而 S0 沒有", d2)):
    print("  {} ＝ {} 檔：{}".format(lab, len(s), "、".join("{}({})".format(x, nm.get(x, "?")) for x in sorted(s))))
for sid in sorted(d1 | d2):
    r = panel[panel["stock_id"].astype(str) == sid]
    e = r[r["eligible"].astype(bool)]
    print("    ⇒ {} {}：eligible 的月份 {} 個｜位置 {}～{}｜日期 {}～{}".format(
        sid, nm.get(sid, "?"), len(e),
        int(e["pos"].min()) if len(e) else "-", int(e["pos"].max()) if len(e) else "-",
        str(e["measure_date"].min())[:10] if len(e) else "-", str(e["measure_date"].max())[:10] if len(e) else "-"))
    print("       ⭐ 判定窗是 [{},{}] ⇒ 它的 eligible 月{}落在窗內".format(
        W0, W1, "沒有一個" if len(e) and (e["pos"].max() < W0 or e["pos"].min() > W1) else "有"))

print()
print("=== ③ S0_pool 2,037 vs 清單 2,039 ⇒ 少的 2 檔 ===")
pool = A | B
tdr_in = sorted(s for s in pool if s.startswith("91") or re.fullmatch(r"\d{4}[A-Z]\d?", s)
                or re.fullmatch(r"00\d{2,3}[A-Z]?", s) or re.fullmatch(r"\d{6}", s))
print("  2,039 清單中命中「非普通股」結構判準的 ＝ {} 檔：{}".format(
    len(tdr_in), "、".join("{}({})".format(x, nm.get(x, "?")) for x in tdr_in)))
print("  ⇒ 2,039 − {} ＝ **{:,}** ⇒ 那就是 S1′／S0_pool 實際用的池（seq17 §4-3：S1′ 與 S0_pool 剔 TDR）".format(
    len(tdr_in), len(pool) - len(tdr_in)))
print("  ⇒ {}".format("✅ 與跑出來的 2,037 相符" if len(pool) - len(tdr_in) == 2037 else "⛔ 不符"))
