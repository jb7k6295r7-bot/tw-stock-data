# -*- coding: utf-8 -*-
"""落地裁定線 seq92 §二：創新板比照 DR ⇒ 只加腳註、不重跑；腳註擴成「-DR 7 檔＋創新板 26 檔」一條。

做法（與 dr_footnote.py 同形，冪等）：
  ① 範圍【掃出來】：26 檔（分支快照母體名稱含 -創）＋ 7 檔 -DR 的代號，在 results* 的
     .csv/.md/.gz/.json/.txt 裡有沒有真的出現 ⇒ 聯集的目錄
  ② 已有舊 DR 腳註的 .md ⇒ 【換掉那一行】（⛔ 不另加第二行）；範圍內但沒有腳註的 .md ⇒ 插一行
  ③ ⛔ 只動 .md；逐檔驗「除腳註那一行外逐字不動」；第二次跑必須 0 動作
"""
from __future__ import annotations
import os
import io
import re
import sys
import glob
import gzip
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D

CHECK = "--check" in sys.argv
OLD_MARK = "資料快照腳註（裁定線 20260924-2051 §一②）"
NEW_MARK = "資料快照腳註（裁定線 20260924-2051 §一②＋20260924-2229 §二）"

uni = D.load_universe()
INN = sorted(uni.loc[uni["name"].str.contains("-創", na=False, regex=False), "stock_id"])
DRS = ["9103", "9105", "9106", "9110", "9136", "9157", "9188"]
assert len(INN) == 26, "⛔ 分支快照創新板不是 26 檔：{}".format(len(INN))
LINE = (
    "> ⚠ **" + NEW_MARK + "**：本件的普通股母體來自分支 `data/` 快照 **2026-09-18**，"
    "`load_universe()` 當時沒有排除兩類：① 7 檔 `-DR` 被誤標成 `kind=='stock'`（main 自 2026-09-21 起已是 `dr`）；"
    "② **26 檔創新板（名稱含 -創）**從來沒被排除（裁定線 1611 §二 裁剔除）。"
    "實際進到 P4 面板 `eligible` 的：-DR 只有 9103／9105 共 50 股-月（0.0837%）；創新板只有 2258／6949 共 7 股-月（0.012%）"
    "（D4 elig_d4 另含 2258／6949 共 51 股-月，0.027%）。"
    "⇒ 出處與量測見 `backtest/DR_SNAPSHOT_FOOTNOTE.md`。⛔ 依裁定【不重跑】；新跑件一律用 `universe_gate.gate3()`。\n"
)
PAT = re.compile(r"(?<![0-9])(" + "|".join(INN + DRS) + r")(?![0-9])")

os.chdir("backtest")
scope = []
for d in sorted(x for x in glob.glob("results*") if os.path.isdir(x)):
    if d == "results_step2":
        continue  # ⛔ 本線今晚的掃描輸出，不是交件
    hit_inn, hit_dr = set(), set()
    for p in glob.glob(os.path.join(d, "**", "*"), recursive=True):
        if not os.path.isfile(p) or os.path.splitext(p)[1].lower() not in (".csv", ".md", ".gz", ".json", ".txt"):
            continue
        try:
            txt = gzip.open(p, "rt", encoding="utf-8", errors="replace").read() if p.endswith(".gz") \
                else io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        #  ⛔ 腳註本身含 DR 代號 ⇒ 掃描前先把腳註那一行拿掉，否則會自我命中
        txt = "\n".join(l for l in txt.split("\n") if "資料快照腳註" not in l)
        for m in PAT.findall(txt):
            (hit_inn if m in INN else hit_dr).add(m)
    if hit_inn or hit_dr:
        scope.append(dict(目錄=d, 創新板代號=len(hit_inn), DR代號=len(hit_dr)))
S = pd.DataFrame(scope)
print("=== ① 範圍（掃出來的）：{} 個目錄 ===".format(len(S)))
print("  只因創新板才進範圍的：{}".format(list(S.loc[(S["創新板代號"] > 0) & (S["DR代號"] == 0), "目錄"])))
print("  只因 DR 才進範圍的：  {}".format(list(S.loc[(S["創新板代號"] == 0) & (S["DR代號"] > 0), "目錄"])))

n_rep = n_ins = n_skip = 0
touched = []
for d in S["目錄"]:
    for p in sorted(glob.glob(os.path.join(d, "**", "*.md"), recursive=True)):
        src = io.open(p, encoding="utf-8").read()
        if NEW_MARK in src:
            n_skip += 1
            continue
        lines = src.split("\n")
        old_idx = [i for i, l in enumerate(lines) if OLD_MARK in l]
        if old_idx:
            assert len(old_idx) == 1, "⛔ {} 有 {} 行舊腳註".format(p, len(old_idx))
            new_lines = lines[:old_idx[0]] + [LINE.rstrip("\n")] + lines[old_idx[0] + 1:]
            kind = "換"
            n_rep += 1
        else:
            at = 1 if lines and lines[0].startswith("#") else 0
            new_lines = lines[:at] + [LINE.rstrip("\n")] + lines[at:]
            kind = "插"
            n_ins += 1
        new = "\n".join(new_lines)
        a = [l for l in src.split("\n") if "資料快照腳註" not in l]
        b = [l for l in new.split("\n") if "資料快照腳註" not in l]
        assert a == b, "⛔ {} 除腳註外有別的行被動".format(p)
        assert new.count(NEW_MARK) == 1 and OLD_MARK not in new.replace(NEW_MARK, ""), "⛔ {} 腳註數不對".format(p)
        if not CHECK:
            io.open(p, "w", encoding="utf-8").write(new)
        touched.append((kind, p))

print()
print("=== ② 動作：換舊腳註 {}｜新插 {}｜已是新版跳過 {}{} ===".format(
    n_rep, n_ins, n_skip, "（--check，⛔ 沒寫檔）" if CHECK else ""))
for k, p in touched:
    if k == "插":
        print("  新插：" + p)
S.to_csv("results_step2/footnote_scope_v2.csv", index=False, encoding="utf-8")
print("⇒ 落檔 backtest/results_step2/footnote_scope_v2.csv")
