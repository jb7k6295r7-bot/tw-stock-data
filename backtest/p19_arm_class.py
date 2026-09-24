# -*- coding: utf-8 -*-
"""答裁定線 seq87 §一 的 ⏳：PREREG19 對 **A 臂**的定義是「對照臂」還是可採用的停損組態？

⛔ 不憑印象 —— 逐字翻登錄，並把水準表的 12 列逐列分類，算出各種裁法下的格數。
⚠ 而本支同時要報一件裁定線沒問、但用同一條規則會被帶到的事：**C_k 是假訊號臂**。
"""
from __future__ import annotations
import os
import io
import re

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
PRE = io.open("PREREG19.md", encoding="utf-8").read()
SUM = io.open("results19/summary.md", encoding="utf-8").read()

print("=== ① 登錄怎麼定義 A（逐字）===")
for pat in [r"^## 一、.*$", r"^\| 組 \| .*$", r"^\| A \|.*$", r"^\| B_k \|.*$", r"^\| C_k \|.*$"]:
    m = re.search(pat, PRE, re.M)
    print("  " + (m.group(0).strip() if m else "（找不到 {}）".format(pat)))

print()
print("=== ② 登錄標題（⭐ 它就把三組的角色寫在標題裡）===")
print("  " + PRE.split("\n")[0][:150])

print()
print("=== ③ 水準表的 12 列逐列分類（每個持有期一張表、每張 12 列）===")
sec = SUM.split("## 二、主格：收盤跌破")[1].split("## 二′、")[0]
h20 = sec.split("#### H20")[1].split("#### H60")[0]
rows = [l for l in h20.split("\n") if l.startswith("|") and "%" in l]
print("  H20 表的列數 {}".format(len(rows)))
cls = []
for l in rows:
    name = l.strip("|").split("|")[0].strip()
    if name.startswith("無停損"):
        k = "對照臂（無停損＝研究十五 P1）"
    elif name.startswith("A "):
        k = "A：結構低點停損"
    elif name.startswith("B_"):
        k = "B_k：結構低點 − k×ATR"
    elif name.startswith("C_"):
        k = "C_k：固定比例（登錄逐字稱「安慰劑」＝本專案用語的【假訊號】）"
    else:
        k = "⛔ 未分類：" + name
    cls.append((name, k))
for n, k in cls:
    print("    {:28s} ⇒ {}".format(n, k))
n_ctrl = sum(1 for _, k in cls if k.startswith("對照臂"))
n_A = sum(1 for _, k in cls if k.startswith("A："))
n_B = sum(1 for _, k in cls if k.startswith("B_k"))
n_C = sum(1 for _, k in cls if k.startswith("C_k"))
assert n_ctrl + n_A + n_B + n_C == len(rows) == 12, "⛔ 分類加不回 12 列"
print("  ⇒ 對照臂 {}｜A {}｜B_k {}｜C_k {}（合計 {}）".format(n_ctrl, n_A, n_B, n_C, len(rows)))

print()
print("=== ④ ⭐⭐ 答裁定線的問題：A 是不是「對照臂」？ ===")
print("""  ⛔ **不是。** 逐字依據三條：
    ① 登錄 §一 的表頭是「三組停損」，而 A 佔其中一【組】，有自己的停損價規則 `stop = lo_pullback`
    ② 登錄標題就寫「停損位置——**結構低點** vs 結構低點 − k×ATR vs 固定比例安慰劑」
       ⇒ ⭐ A（結構低點）是被比較的三種【停損位置】之一，⛔ 不是基準
    ③ 登錄 §三 的否證條件用 B_k − A 當主要比較 ⇒ A 是被比的對象，⛔ 不是「不判定的對照」
  ⇒ ✅ **所以照裁定線 seq87 §一 的規則，A ⛔ 不扣** ⇒ 研究十九水準列維持 66 ⇒ 全件 126""")

print()
print("=== ⑤ ⚠⚠ 而同一條規則會帶到裁定線沒問的一件：C_k 是【假訊號臂】 ===")
m = re.search(r"^\| C_k \|.*$", PRE, re.M)
print("  登錄 §一 逐字：{}".format(m.group(0).strip() if m else "?"))
print("  登錄標題逐字：「…vs 固定比例**安慰劑**」（⭐ 本專案用語一律寫【假訊號】）")
m2 = re.search(r"^.*安慰劑 C_k.*$", PRE, re.M)
print("  登錄 §校準 逐字：{}".format((m2.group(0).strip()[:120] + "…") if m2 else "?"))
print("""  ⇒ ⚠ 而裁定線 seq84 §一 已裁：「**假訊號臂 ⇒ 永不計**」（當時講的是 P17 的 W_shuf）
  ⇒ ⇒ 若同一條規則套下來，C_k 的水準列也不該計""")

print()
print("=== ⑥ ⭐ 各種裁法下的數字（⛔ 本線不自取，全部擺出來）===")
per = 3  # 三個持有期
for lab, keep in [
    ("裁定線 seq87 現行（只扣無停損對照臂）", n_A + n_B + n_C),
    ("再扣 A（裁定線問的那一案）", n_B + n_C),
    ("⭐ 改扣 C_k（照 seq84 假訊號臂永不計）", n_A + n_B),
    ("兩個都扣（A 與 C_k）", n_B),
]:
    lvl = keep * per * 2
    print("  {:34s} 水準列 {:3d} ⇒ 研究十九 ＝ 30 ＋ 30 ＋ {:3d} ＝ **{}**".format(
        lab, lvl, lvl, 60 + lvl))

print()
print("  ⭐ 本線的讀法（⛔ 只是讀法）：")
print("     ・A ⛔ 不扣（登錄把它當三組之一）")
print("     ・C_k 依 seq84 看起來要扣 ⇒ ⏳ 但那是裁定線的格子")
print("     ⇒ 所以本線報的兩個數是 **126**（現行）與 **96**（若 C_k 照假訊號臂處理）")

# ⛔ 自測：分類必須有鑑別力 —— 四類都要真的出現過
kinds = {k.split("：")[0].split("（")[0] for _, k in cls}
assert len(kinds) == 4, "⛔ 四類沒有都出現 ⇒ 分類是空轉的：{}".format(kinds)
assert n_B == 5 and n_C == 5, "⛔ B_k／C_k 應各 5 列，實得 {}／{}".format(n_B, n_C)
print()
print("✅ 自測：四類都真的出現（⇒ 分類不是空轉）｜B_k 與 C_k 各 5 列")
