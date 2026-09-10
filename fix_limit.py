#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性修正 `data/universe/daily/*.csv` 的 `limit` 欄（平盤鎖死被標成跌停）。

    python3 fix_limit.py            # 只報告，不寫
    python3 fix_limit.py --write    # 真的改

## 為什麼要有這一支

`fetch.py` 原本寫的是 `"down" if chg else "flat"`。`chg` 是**字串**，
`"0.0"` 是 truthy ⇒ **整天鎖死在平盤會被判成跌停**。
全庫實測 **50,382 列**中招，佔所有 `down` 的 47.7%；
而 `flat` 只在 `change` 是空字串時出現（5,379 列）——「平盤鎖死」這個值
**結構上根本走不到**。

`fetch.py` 已經修好，但它只影響**之後寫的**。歷史那 50,382 列要靠這一支補。

## ⚠ 為什麼是重算不是重抓

`limit` 是 `change` 的**純函數**（同一列裡就有），不需要連外。
重抓 2,847 天既慢又會引入來源變動；重算是確定性的、可重跑、可比對。

## 安全設計

⛔ **只改 `limit` 那一格**，其他欄位一個字都不動。
為了確定這件事，寫檔前先做**一次空跑往返**：把讀進來的列原封不動寫回去，
若產出的位元組與原檔不同，代表 csv 模組的引號規則與原檔不一致
——那就**整檔跳過並報告**，絕不冒著改壞別欄的風險去修一欄。
"""
import argparse
import csv
import glob
import io
import os
import sys

import fetch
import runlog
from twparse import render_csv as _render_csv

DAILY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "universe", "daily")


# ⛔ 第十二份：`_render` 兩支修復腳本各一份。
#   ⭐ 是 pre-commit 的「同一件事只准一份」**當場擋下來的**——
#     ⚠ 而那個守門是同一天才裝上去的，這是它抓到的第一件。
_render = _render_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="真的寫檔（預設只報告）")
    a = ap.parse_args()
    rl = runlog.Run("fix_limit")

    files = sorted(glob.glob(os.path.join(DAILY, "*.csv")))
    changed_rows = 0
    changed_files = 0
    skipped = []
    trans = {}
    for p in files:
        with io.open(p, encoding="utf-8", newline="") as f:
            raw = f.read()
        rows = list(csv.reader(io.StringIO(raw, newline="")))
        if not rows:
            continue
        header, body = rows[0], rows[1:]
        if "limit" not in header or "change" not in header:
            skipped.append((os.path.basename(p), "沒有 limit/change 欄"))
            continue
        # ★ 空跑往返：原封不動寫回去必須位元組相同，否則不碰這一檔
        if _render(header, body) != raw:
            skipped.append((os.path.basename(p), "空跑往返不相同，不敢改"))
            continue
        i_l, i_c = header.index("limit"), header.index("change")
        n = 0
        for r in body:
            if len(r) <= max(i_l, i_c) or not r[i_l]:
                continue
            new = fetch._lock_dir(r[i_c])
            if new != r[i_l]:
                trans[(r[i_l], new)] = trans.get((r[i_l], new), 0) + 1
                r[i_l] = new
                n += 1
        if n:
            changed_rows += n
            changed_files += 1
            if a.write:
                with io.open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(_render(header, body))

    rl.info("掃過的日檔", f"{len(files):,} 檔")
    rl.info("要改的", f"{changed_files:,} 檔／{changed_rows:,} 列"
            + ("（**已寫入**）" if a.write else "（只報告，加 --write 才寫）"))
    for (old, new), n in sorted(trans.items(), key=lambda x: -x[1]):
        rl.info(f"{old} → {new}", f"{n:,} 列")
    if skipped:
        rl.info("跳過", f"{len(skipped)} 檔：{skipped[:5]}")
    # ⛔ 跳過任何一檔都要看得見——「只改了一半」是最貴的形狀
    rl.check("沒有任何日檔被跳過", not skipped,
             f"{len(skipped)} 檔沒改到，清單在上面")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
