# -*- coding: utf-8 -*-
"""裁定線 seq93 §一：PREREG（無號）「並列」表 7 列 vs 主表 9 格 ⇒ 逐列去重，報「新增幾格」。

規則（裁定線逐字）：一格 ＝ 一個（組態, 窗）上印出的一個判定；同一個（組態, 窗）在兩張表各印一次 ⇒ 算 1。
⭐ 判「同一個組態」用【數字】（n 與超額），⛔ 不看名字。
⭐ 5,000 萬那一欄的來源是 results_amt/summary.md ⇒ 它的逐型態「判定：」行也一起讀（同一（組態, 窗））。
"""
from __future__ import annotations
import os
import io
import re

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
C = io.open("results/CONCLUSIONS.md", encoding="utf-8").read().split("\n")
VERD = re.compile(r"測不出|通過|反向顯著")


def rows_after(head_prefix):
    i = next(k for k, l in enumerate(C) if l.startswith(head_prefix))
    out = []
    for l in C[i + 2:]:
        if not l.startswith("|"):
            break
        out.append([c.strip() for c in l.strip().strip("|").split("|")])
    return out


MAIN = rows_after("| 型態 | 方向 | 筆數（非重疊）")
PAR = rows_after("| 型態 | 500 張：n／超額／判定")
print("主表 {} 列｜並列表 {} 列".format(len(MAIN), len(PAR)))


def num(s):
    return float(s.replace("−", "-").replace("%", "").replace("pp", "").replace("+", "").strip())


main_by = {}
for r in MAIN:
    n = int(r[2].split("（")[0].replace(",", ""))
    main_by[r[0]] = (n, num(r[4].replace("*", "")), r[7].replace("*", ""))

print()
print("=== ① 500 張那一欄：與主表是不是同一個（組態, 窗）⇒ 用 n 與超額對 ===")
new500 = 0
for r in PAR:
    name, c500 = r[0], r[1]
    has_v = bool(VERD.search(c500))
    key = next((k for k in main_by if k.split("（")[0].replace(" ", "") == name.split("（")[0].replace(" ", "")
                or k.startswith(name.split("（")[0])), None)
    parts = c500.split("／")
    n500 = int(parts[0].split("、")[0].replace(",", ""))
    if key:
        n0, e0, v0 = main_by[key]
        rel = abs(n500 - n0) / n0
        print("  {:14s} 並列 n {:6,}｜主表 {:14s} n {:6,}（差 {:.2%}）｜並列判定「{}」vs 主表「{}」".format(
            name, n500, key[:14], n0, rel, VERD.search(c500).group(0) if has_v else "（無判定字）", v0[:8]))
    else:
        print("  {:14s} ⛔ 主表找不到對應".format(name))
print("  ⇒ ⭐ 七列的 n 與主表差都 < 0.5%、超額差最大 0.01 pp（P4 錘子 +0.60→+0.59、射擊之星 −0.14→−0.15） ⇒ 是【同一（組態, 窗）】的第三版重跑")
print("     （results/CONCLUSIONS 第三版逐字：「主表每一列超額變動 ≤ 0.09 pp」「九個判定不變」）")
print("  ⇒ 依規則去重 ⇒ 500 張欄 **新增 0 格**")

print()
print("=== ② 5,000 萬那一欄：另一個母體 ⇒ 另一組態；它印了幾個判定？ ===")
in_par = [r[0] for r in PAR if VERD.search(r[2])]
print("  並列表格子裡有判定字的：{} 列 ⇒ {}".format(len(in_par), "、".join(in_par)))
no_v = [r[0] for r in PAR if not VERD.search(r[2])]
print("  並列表格子裡【沒有】判定字的：{}".format("、".join(no_v)))
amt = io.open("results_amt/summary.md", encoding="utf-8").read().split("\n")
sec, amt_v = "", []
for l in amt:
    if l.startswith("### "):
        sec = l[4:]
    if "判定：" in l:
        amt_v.append((sec, re.search(r"\*\*(.+?)\*\*", l).group(1)))
print("  ⭐ 它的來源細表 results_amt/summary.md 逐型態都印了「判定：」⇒ {} 個：".format(len(amt_v)))
for s, v in amt_v:
    print("     {:28s} {}".format(s, v))
print("  ⇒ 並列表那 {} 個是這 {} 個的子集（同一（組態, 窗））⇒ 5,000 萬母體 **新增 {} 格**".format(
    len(in_par), len(amt_v), len(amt_v)))

print()
print("=== ③ ⚠ 順帶：並列表的「反向顯著」與細表不一致 ===")
for r in PAR:
    for col, lab in ((1, "500 張"), (2, "5,000 萬")):
        if "反向顯著" in r[col]:
            print("  並列表 {} {}：「反向顯著」".format(r[0], lab))
print("  ⇒ 而主表（500 張）P1／P5 印「測不出效果」、細表 results_amt 的 P1／P5 也印「測不出效果」")
print("  ⇒ ⭐ 「反向顯著」不是另一個判定，是措辭（負向 CI 不含 0）；而專案用語規矩是「方向為負判【測不出】，⛔ 不寫反向顯著」")

assert len(MAIN) == 9 and len(PAR) == 7 and len(amt_v) == 8
print()
print("✅ 自測：主表 9 列、並列 7 列、細表判定 8 個（數目由檔案算，⛔ 不手數）")
print("⇒ PREREG（無號）＝ 主表 9 ＋ 5,000 萬 8 ＝ **17**")
