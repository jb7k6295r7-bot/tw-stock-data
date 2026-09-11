#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""halt_spans.py — 「這一檔在哪一段期間**停止交易**」（上櫃）。⛔ 只讀，不連外。

    python3 halt_spans.py        # → data/meta/halt_spans.csv

## ⭐ 它解的是 K線分析線 2026-09-11 02:10 那題：**洞是中間、下市是尾巴**

他們算出 39 檔普通股有「≥20 個交易日的中間洞」（上櫃 27 ／上市 12），
而 TWSE 的停止買賣端點**只有即時快照**（漏抓一天就永久少一天）
⇒ 上櫃那 27 檔，他們手上**沒有任何**官方名單可以解釋。

⭐ 而我方有：`data/universe/chtm/` 的 `halted` 欄是**逐日**的，回到 2015
（端點本身回到 2009）。⇒ 把它壓成區間，那 27 檔的洞就有了名字。

⚠ 而這是一條**雙向**的驗算，⛔ 不是「我方有沒有」：
洞要對得上區間，**對不上的那幾檔才是真正要查的**。

## ⛔ 為什麼不另寫一支壓縮程式

CLAUDE.md 第四點五：同一件事只准有一份實作。
`margin_universe.py` 已經有「逐日集合 → 逐檔區間」那一整套，
含**不可判定日**的守門（鄰近 ±10 日中位數）與**終點斷言**（天數總和相等）。
⇒ 這一支只提供兩樣東西：**哪個目錄**、**哪些列算成員**。

## ⭐⭐ 而這裡有一個 margin 沒有的陷阱：成員只是整檔的**一小撮**

```
margin／otcmargin   成員集合 ＝ 整個檔     ⇒ 列數變少 ＝ 抓壞了
⭐ chtm.halted      成員集合 ＝ 20 列裡 3~6 檔 ⇒ **成員數少是正常的**
```

⚠ 若把「不可判定」的判準套在**成員數**上：
「今天沒有人停止交易」會被判成故障 ⇒ 那一天被跳過
⇒ ⛔ **停牌區間會跨過復牌日、連成一整段**，而那正好是要找的那一刻。
（`selftest_margin_universe.py` ⑦ 的突變 M3 實測：c000 的兩段變成一段 29 天。）

⇒ 所以 `day_sets(..., keep=...)` 另外回**總列數**，不可判定一律看總列數。

## ⛔ 「停止交易」與「下市」是兩件事

停止交易**會回來**，下市不會。這支只回答前者；
後者在 `data/meta/delisted.csv`（`delisted.py`，上市；上櫃那份我方還沒有）。
⚠ 兩者在日線資料裡**長得一模一樣**（都是「某天之後就沒有列了」）
⇒ ⛔ 只看日線分不出來，一定要查這兩張表。
"""
import argparse
import os
import sys

import runlog
# ⛔ 唯一一份壓縮實作在 `margin_universe`，這裡 import 過去，不抄。
from margin_universe import UNI, compress, write_spans  # noqa: F401

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "halt_spans.csv")
# ⚠ `halted` 欄的值實測是 "0"／"1"（`chtm` 2015-01-05 ~ 2026-09-10）。
#   ⛔ 用 truthy 判不行——`"0"` 是**真值**，整批會被當成停牌中。
DIRS = (("chtm", "tpex"),)


def is_halted(r):
    """⛔ 逐字比 `"1"`。⚠ 空字串／`"0"` 都不是停牌。"""
    return str(r.get("halted") or "").strip() == "1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", type=float, default=0.7,
                    help="總列數低於鄰近中位數這個比例的日子視為不可判定")
    a = ap.parse_args()

    rl = runlog.Run("halt_spans")
    rl.info("⛔ 這一支只讀不連外",
            "把 `chtm/` 的 `halted` 欄**逐日序列**壓成**逐檔停止交易區間**")
    rl.info("⛔ 壓縮邏輯不是這支寫的",
            "`margin_universe.compress()`／`write_spans()`（第四點五：只准一份）")

    rows, ok = [], 0
    for dname, market in DIRS:
        got = compress(dname, market, rl, a.floor,
                       keep=is_halted, noun="停止交易")
        if got is None:
            continue
        ok += 1
        rows += got
    rl.check("`chtm/` 讀得到（⛔ 讀不到 ≠ 沒有停牌，八成是 checkout 的問題）",
             ok == len(DIRS), f"{ok}／{len(DIRS)}")
    if not rows:
        return rl.finish()
    write_spans(rows, OUT, rl, "停止交易區間")
    # ⭐ 給 K線分析線的那一句：⛔ 未結束的那些才是「現在就停著」
    open_ended = [r for r in rows if r[5] == "1"]
    rl.info("⭐ 目前仍停止交易中", f"{len(open_ended)} 檔："
            + "、".join(f"{r[1]}（自 {r[2]}）" for r in open_ended[:12]))
    rl.info("⇒ 讀法", "「某檔在 D 那天有沒有停止交易」＝ 有沒有一段 "
                      "`start ≤ D ≤ end`。⛔ `open_ended=1` 代表**還沒復牌**，"
                      "⚠ 不是「到今天為止」——那一段還會長。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
