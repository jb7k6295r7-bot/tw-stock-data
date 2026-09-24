# -*- coding: utf-8 -*-
"""8 件數格 —— 第二版：⭐ 照【判定欄】數，⛔ 不照關鍵字數。

⛔ 第一版（count8_prereg.py）用關鍵字（測得出／測不出／通過／贏／較差）掃表格列
   ⇒ 在 results8 上只抓到 3 列，⛔ 而它的「判定」欄實際印了 18 格：
      「分不出來」15 ＋「較差」3（另 3 列是「基準」）
   ⇒ ⭐ 「分不出來」不在關鍵字清單裡 ⇒ 整批漏掉 ⇒ 這正是「看取值集合，不看名字」那一條
✅ 第二版：在每一張 md 表裡找表頭叫【判定／統計層／新判定】的那一欄，逐列讀它的值、列出取值集合。
"""
from __future__ import annotations
import os
import io
import re
from collections import Counter, OrderedDict

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
VCOL = re.compile(r"^(判定|統計層|新判定|原判定|結果|事前判定|判)$")
NOT_CELL = {"基準", "—", "-", "", "對照"}

ITEMS = [
    ("PREREG15", "results15/summary.md"),
    ("PREREG（無號）", "results/CONCLUSIONS.md"),
    ("PREREG3 全庫", "results3/summary.md"),
    ("PREREG3 5,000 萬", "results3_amt/summary.md"),
    ("PREREG4", "results5/summary.md"),
    ("PREREG6", "results7/summary.md"),
    ("PREREG7", "results8/summary.md"),
    ("PREREG18", "results18/summary.md"),
]


def tables(txt):
    """回傳 [(節名, 表頭 list, 各列 list[list])]"""
    out, sec, cur = [], "", None
    for l in txt.split("\n"):
        if l.startswith("#"):
            sec = l.strip("# ").strip()[:44]
        if l.startswith("|"):
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if cur is None:
                cur = (sec, cells, [])
            else:
                cur[2].append(cells)
        else:
            if cur is not None:
                out.append(cur)
                cur = None
    if cur is not None:
        out.append(cur)
    return out


for name, p in ITEMS:
    txt = io.open(p, encoding="utf-8", errors="replace").read()
    print("=" * 96)
    print("■ {}　{}".format(name, p))
    total = 0
    agg = Counter()
    for sec, head, rows in tables(txt):
        idx = [i for i, h in enumerate(head) if VCOL.match(h.replace("*", "").strip())]
        if not idx:
            continue
        i = idx[-1]  # 有「原判定／新判定」兩欄時取【新判定】（最後一欄）
        vals = Counter()
        for r in rows:
            v = r[i].replace("*", "").strip() if i < len(r) else ""
            vals[v] += 1
        n = sum(c for v, c in vals.items() if v not in NOT_CELL)
        total += n
        agg.update({v: c for v, c in vals.items() if v not in NOT_CELL})
        skip = {v: c for v, c in vals.items() if v in NOT_CELL}
        print("   【{}】欄「{}」⇒ 判定格 {:3d}｜取值 {}{}".format(
            sec, head[i], n, dict(vals.most_common(6)),
            "｜⛔不算 {}".format(skip) if skip else ""))
    print("   ⇒ 合計 **{}** 格（判定欄非空、非「基準」）｜全檔取值 {}".format(total, dict(agg.most_common(8))))
