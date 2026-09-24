# -*- coding: utf-8 -*-
"""落地裁定線 20260924-2051（seq85）§一①②：在受影響的交件加【一行】資料快照腳註。

⛔ 依裁定：不重跑（「形狀同停牌 44 筆：很小聲，但要標」）。
⛔ 本支不用「猜哪些件受影響」——範圍由 dr_footnote_scope.csv 量出來的 31 個目錄決定
   （＝輸出檔裡真的出現那 7 檔 -DR 代號的目錄）。

⭐ 安全性先查過：handover_check.sh 的逐位元閘門只比 `$REF/*.csv`（resultsp16 的 15 個 csv）
   ⇒ 本支只動 **.md**，⛔ 不動任何 .csv ⇒ 那道閘門不受影響。

⭐ 冪等：已有標記的檔跳過；除了插入那一行，其餘位元不動（逐檔 assert）。
"""
from __future__ import annotations
import os
import sys
import io
import hashlib
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
MARK = "資料快照腳註（裁定線 20260924-2051 §一②）"
LINE = (
    "> ⚠ **" + MARK + "**：本件的普通股母體來自分支 `data/` 快照 **2026-09-18**，"
    "該快照把 7 檔 `-DR`（9103／9105／9106／9110／9136／9157／9188）誤標成 `kind=='stock'`"
    "（main 自 2026-09-21 起已是 `dr`、0 檔）；實際進到 P4 面板 `eligible` 的只有 **9103／9105、共 50 股-月（0.0837%）**。"
    "⇒ 出處與量測見 `backtest/DR_SNAPSHOT_FOOTNOTE.md`。⛔ 依裁定【不重跑】。\n"
)

CHECK = "--check" in sys.argv

scope = pd.read_csv("results_step2/dr_footnote_scope.csv")
dirs = sorted(scope.loc[scope["出現的DR"] != "—", "目錄"].astype(str))
print("=== ① 範圍（量出來的，⛔ 不是猜的）：{} 個目錄 ===".format(len(dirs)))
print("  " + "、".join(dirs))

targets = []
for d in dirs:
    for root, _, files in os.walk(d):
        for fn in sorted(files):
            if fn.lower().endswith(".md"):
                targets.append(os.path.join(root, fn))
targets.sort()
print()
print("=== ② 要加腳註的 .md 檔：{} 個（⛔ 不動任何 .csv）===".format(len(targets)))

done, skip, changed = 0, 0, []
for p in targets:
    src = io.open(p, encoding="utf-8").read()
    if MARK in src:
        skip += 1
        continue
    lines = src.split("\n")
    # ⭐ 插在第一個標題行之後；若第一行不是標題 ⇒ 插在最前面
    at = 1 if lines and lines[0].startswith("#") else 0
    new = "\n".join(lines[:at]) + ("\n" if at else "") + LINE + "\n".join(lines[at:])
    # ⛔ 自測：除了插入那一行，其餘每一行必須逐字不動
    a = [x for x in src.split("\n")]
    b = [x for x in new.split("\n")]
    ins = [x for x in b if MARK in x]
    assert len(ins) == 1, "⛔ {} 插入了 {} 行".format(p, len(ins))
    b2 = [x for x in b if MARK not in x]
    # 插入時在腳註後加了一個空行 ⇒ 允許恰好多一個空字串
    if b2 != a:
        assert [x for x in b2 if x != ""] == [x for x in a if x != ""], \
            "⛔ {} 除了腳註以外的內容被改動了".format(p)
    if not CHECK:
        io.open(p, "w", encoding="utf-8").write(new)
    done += 1
    changed.append(p)

print("  新增腳註 {} 個｜已有而跳過 {} 個".format(done, skip))
if CHECK:
    print("  （--check 模式，⛔ 沒有寫檔）")
print()
print("=== ③ 前 12 個被改的檔 ===")
for p in changed[:12]:
    print("  " + p)
if len(changed) > 12:
    print("  …共 {} 個".format(len(changed)))
