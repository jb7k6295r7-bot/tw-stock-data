# -*- coding: utf-8 -*-
"""落地裁定線 seq94 §二：「反向顯著」為停用用語 ⇒ 交件【不改字】，在表下加一行腳註重讀（冪等）。

⭐ 每一格的「現行判定」⛔ 不憑印象寫 —— 逐格去找【同一（組態, 窗）】的月分群 CI：
   有 ⇒ 依月分群 CI 讀（含 0 ⇒ 測不出；不含 0 且點估計為負 ⇒ 測得出（−））
   沒有 ⇒ 寫「現行判定未重算」（裁定線逐字要求：⛔ 不自己換字）
"""
from __future__ import annotations
import os
import io
import re
import sys

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
CHECK = "--check" in sys.argv
MARK = "「反向顯著」為停用用語（裁定線 20260924-2244 §二"


def rows_of(path, head_prefix):
    L = io.open(path, encoding="utf-8").read().split("\n")
    i = next(k for k, l in enumerate(L) if l.startswith(head_prefix))
    head = [c.strip() for c in L[i].strip().strip("|").split("|")]
    out, j = [], i + 2
    while j < len(L) and L[j].startswith("|"):
        out.append([c.strip() for c in L[j].strip().strip("|").split("|")])
        j += 1
    return L, head, out, j  # j ＝ 表後第一行的索引


def ci(s):
    m = re.findall(r"[-−+]?\d+\.\d+", s.replace("−", "-"))
    return float(m[0]), float(m[1])


#  ── ① results7：自己的表就有「月分群 SE」欄 ⇒ 逐格讀
L7, H7, R7, _ = rows_of("results7/summary.md", "| 型態 | 持有 | n |")
i_mc = H7.index("超額 CI（月分群 SE）")
i_v = H7.index("判定")
i_ex = H7.index("超額")
cur7 = {}
print("=== ① results7 的『反向顯著』逐格：同列月分群 CI ===")
for r in R7:
    if "反向顯著" in r[i_v]:
        lo, hi = ci(r[i_mc])
        pt = float(re.findall(r"[-−+]?\d+\.\d+", r[i_ex].replace("−", "-"))[0])
        now = "測不出" if lo <= 0 <= hi else ("測得出（−）" if pt < 0 else "測得出（＋）")
        cur7[(r[0], r[1])] = (now, r[2], r[i_mc])
        print("  {} {} 日 n {}｜月分群 CI {} ⇒ 現行讀法【{}】".format(r[0], r[1], r[2], r[i_mc], now))
assert len(cur7) == 4, "⛔ results7 反向顯著不是 4 格：{}".format(len(cur7))

#  ── ② results/CONCLUSIONS 並列表：同一（組態, 窗）去哪找月分群 CI
LP, HP, RP, _ = rows_of("results/CONCLUSIONS.md", "| 型態 | 500 張：n／超額／判定")
amt_mc = io.open("results_amt/summary.md", encoding="utf-8").read().count("月分群")
print()
print("=== ② results/CONCLUSIONS 並列表的『反向顯著』逐格 ===")
curP = []
for r in RP:
    for col, lab in ((1, "500 張"), (2, "5,000 萬")):
        if "反向顯著" not in r[col]:
            continue
        n = r[col].split("／")[0].replace(",", "")
        hit = [v for (nm, h), v in cur7.items() if h == "20" and v[1].replace(",", "") == n]
        if lab == "500 張" and hit:
            now, _, mc = hit[0]
            curP.append((r[0], lab, "results7/summary.md 同列（n {} 相同）月分群 CI {} ⇒ **{}**".format(n, mc, now)))
        else:
            curP.append((r[0], lab, "本件與 results_amt 都只有非重疊 SE（results_amt 裡「月分群」出現 {} 次）⇒ **現行判定未重算**".format(amt_mc)))
for x in curP:
    print("  {} {} ⇒ {}".format(*x))
assert len(curP) == 3, "⛔ 並列表反向顯著不是 3 格"

HEAD = ("> ⚠ 本表的" + MARK + "；tw-backtest-inference〈十二〉）。現行讀法：以月分群 CI 判——"
        "含 0 ⇒ 測不出；不含 0 且點估計為負 ⇒ 測得出（−）。")
line7 = HEAD + "本表 4 格的現行判定：" + "；".join(
    "{} {} 日 ⇒ 同列「超額 CI（月分群 SE）」{} ⇒ **{}**".format(k[0], k[1], v[2], v[0]) for k, v in cur7.items()) \
    + "。⛔ 表內原字不改（定版交件）。"
lineP = HEAD + "本表這幾格的現行判定：" + "；".join("{} {} ⇒ {}".format(a, b, c) for a, b, c in curP) \
    + "。⛔ 表內原字不改（定版交件）。"

#  ── ③ results7/CONCLUSIONS 也有同一張判定表（被問一張，同一族的另一張照同規則走）
L7c = io.open("results7/CONCLUSIONS.md", encoding="utf-8").read().split("\n")
has7c = any("反向顯著" in l and l.startswith("|") for l in L7c)


def insert_after_table(path, head_prefix, line):
    L = io.open(path, encoding="utf-8").read().split("\n")
    if any(MARK in l for l in L):
        return "跳過（已有）"
    i = next(k for k, l in enumerate(L) if l.startswith(head_prefix))
    j = i + 2
    while j < len(L) and L[j].startswith("|"):
        j += 1
    new = L[:j] + ["", line] + L[j:]
    assert [l for l in new if MARK not in l and l != ""] == [l for l in L if l != ""], "⛔ 動到別行"
    if not CHECK:
        io.open(path, "w", encoding="utf-8").write("\n".join(new))
    return "插在第 {} 行後".format(j)


print()
print("=== ③ 插腳註（{}）===".format("--check 不寫檔" if CHECK else "寫檔"))
print("  results/CONCLUSIONS.md 並列表下：", insert_after_table("results/CONCLUSIONS.md", "| 型態 | 500 張：n／超額／判定", lineP))
print("  results7/summary.md 各型態表下：", insert_after_table("results7/summary.md", "| 型態 | 持有 | n |", line7))
if has7c:
    hp = next(l for l in L7c if l.startswith("|") and "型態" in l)
    line7c = line7.replace("同列「超額 CI（月分群 SE）」", "results7/summary.md 同列月分群 CI ")
    print("  results7/CONCLUSIONS.md 判定表下：", insert_after_table("results7/CONCLUSIONS.md", "| 型態 | 20 日超額 |", line7c))
print()
print("results7 那一行：\n  " + line7[:300] + "…")
