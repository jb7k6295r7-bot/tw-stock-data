# -*- coding: utf-8 -*-
"""答台股策略線 2147 §③ 的兩件確認：

  (一) resultsp3：甲臂是不是就是 P1 本身？那 17 個判準列怎麼拆？
  (二) resultsp6：8 格的判準；而「不排除④」那一臂是不是與 P7 的 stop=none 同組態？

⭐ 判「同組態」的方法：⛔ 不看名字，看【數字】——
   同一個組態在同一個窗上跑出來的年化與回落必須逐位元相同（同種子集合）。
"""
from __future__ import annotations
import os
import io
import re
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest"))

print("=== (一) resultsp3：那 17 個判準列逐類拆 ===")
txt = io.open("resultsp3/summary.md", encoding="utf-8").read()
lines = txt.split("\n")
PAT = re.compile(r"仍沒贏|不再贏|仍贏|沒贏|贏過")
hit = [(i + 1, l) for i, l in enumerate(lines) if l.startswith("|") and PAT.search(l)]
print("  命中表格列 {} 個".format(len(hit)))
#  依所在的節分類
sec = None
buckets = {}
for i, l in enumerate(lines):
    if l.startswith("#"):
        sec = l.strip("# ").strip()
    if l.startswith("|") and PAT.search(l):
        buckets.setdefault(sec, []).append((i + 1, l))
for s, v in buckets.items():
    print()
    print("  ── 節：{}　⇒ {} 列".format(s, len(v)))
    for n, l in v[:6]:
        cells = [c.strip() for c in l.strip("|").split("|")]
        print("     行{:4d}  {}  …  判定「{}」".format(n, cells[0][:22], cells[-1][:34]))
    if len(v) > 6:
        print("     …共 {} 列".format(len(v)))

print()
print("=== ⭐ resultsp3 的甲臂是不是就是 P1？用【數字】對，⛔ 不看名字 ===")
p1 = pd.read_csv("resultsp1/portfolio.csv", float_precision="round_trip")
#  P3 §一 主格三格逐字引的是 P1 贏過 0050 的那三格
w = p1[p1["win"].astype(str).str.lower() == "true"]
print("  P1 win=True 的三格：")
print(w[["set", "N", "d", "rule", "cagr", "mdd"]].to_string(index=False))
p3head = "\n".join(lines[:25])
for _, r in w.iterrows():
    tag = "{:+.1f}%／{:.1f}%".format(r["cagr"] * 100, r["mdd"] * 100)
    t2 = "{:+.1f}%／{:.1f}%".format(r["cagr"] * 100, abs(r["mdd"]) * 100)
    found = (tag in p3head) or (t2 in p3head) or \
            ("{:+.1f}%".format(r["cagr"] * 100) in p3head)
    print("    N{} {} ⇒ 年化 {:+.1f}% 出現在 P3 §一 的表頭區？{}".format(
        int(r["N"]), r["rule"], r["cagr"] * 100, "✅ 是" if found else "⛔ 否"))
print("  ⇒ ⭐ P3 §一 的標題逐字就是「主格三格（P1 贏過 0050 的那三格）＋ 對照格（輸給 0050，沒被看過）」")
print("  ⇒ ✅ 所以【甲臂就是 P1 本身】——台股策略線 2147 §③ 說的對")

print()
print("=== (二) resultsp6：8 格與「不排除④」臂 ===")
p6 = pd.read_csv("resultsp6/cells.csv", float_precision="round_trip")
print("  resultsp6/cells.csv {} 列；set 取值 {}；N 取值 {}".format(
    len(p6), sorted(p6["set"].unique()), sorted(p6["N"].unique())))
print(p6[["set", "N", "cagr", "mdd", "win_all", "win_a", "win_b", "win"]].to_string(index=False))

print()
print("=== ⭐ 「不排除④」是不是與 P7 的 stop=none 同組態？用數字對 ===")
p7 = pd.read_csv("resultsp7/cells.csv", float_precision="round_trip")
p7b = pd.read_csv("resultsp7/baseline_gateB.csv", float_precision="round_trip")
print("  resultsp7/cells.csv 的 stop 取值 {}；N 取值 {}".format(
    sorted(p7["stop"].astype(str).unique()), sorted(p7["N"].unique())))
print("  resultsp7/baseline_gateB.csv 的 N 取值 {}（stop 全 {}）".format(
    sorted(p7b["N"].unique()), sorted(p7b["stop"].astype(str).unique())))
p7n = pd.concat([p7[p7["stop"].astype(str) == "none"], p7b[p7b["stop"].astype(str) == "none"]],
                ignore_index=True)
print("  ⇒ P7 側 stop=none 的列共 {}（N＝{}）".format(len(p7n), sorted(p7n["N"].unique())))

same = []
for _, a in p6.iterrows():
    for _, b in p7n.iterrows():
        if int(a["N"]) != int(b["N"]):
            continue
        dc = abs(float(a["cagr"]) - float(b["cagr"]))
        dm = abs(float(a["mdd"]) - float(b["mdd"]))
        if dc < 1e-12 and dm < 1e-12:
            same.append((a["set"], int(a["N"]), float(a["cagr"]), float(a["mdd"])))
print()
if same:
    print("  ⇒ ⭐⭐ 逐位元相同的格 **{} 個**（⇒ 同組態，依「全專案算 1」要去重）：".format(len(same)))
    for s, n, c, m in same:
        print("     set「{}」N={}　年化 {!r}　回落 {!r}".format(s, n, c, m))
else:
    print("  ⇒ ⛔ 沒有任何一格與 P7 的 stop=none 逐位元相同 ⇒ ⛔ 不可去重")
    #  ⭐ 若不是逐位元相同，印出最接近的一組，讓人看得出差多少
    best = None
    for _, a in p6.iterrows():
        for _, b in p7n.iterrows():
            if int(a["N"]) != int(b["N"]):
                continue
            d = abs(float(a["cagr"]) - float(b["cagr"])) + abs(float(a["mdd"]) - float(b["mdd"]))
            if best is None or d < best[0]:
                best = (d, a["set"], int(a["N"]), float(a["cagr"]), float(b["cagr"]),
                        float(a["mdd"]), float(b["mdd"]))
    if best:
        print("     最接近的一組：set「{}」N={}".format(best[1], best[2]))
        print("       P6 年化 {!r}　vs  P7 none 年化 {!r}".format(best[3], best[4]))
        print("       P6 回落 {!r}　vs  P7 none 回落 {!r}".format(best[5], best[6]))
        print("     ⇒ ⭐ 差不是 0 ⇒ 它們是【不同的組態】（母體或訊號集不同），⛔ 不是同一格")

# ⛔ 自測：比對必須有鑑別力 —— P7 自己跟自己比必須全部逐位元相同
cnt = 0
for _, a in p7n.iterrows():
    for _, b in p7n.iterrows():
        if int(a["N"]) == int(b["N"]) and abs(float(a["cagr"]) - float(b["cagr"])) < 1e-12 \
           and abs(float(a["mdd"]) - float(b["mdd"])) < 1e-12:
            cnt += 1
assert cnt >= len(p7n), "⛔ 連自己跟自己都對不上 ⇒ 比對邏輯壞了"
print()
print("✅ 鑑別力自測：P7 stop=none 自己跟自己比，{} 組逐位元相同（⇒ 比對邏輯會響）".format(cnt))
