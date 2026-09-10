#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性修正 `data/universe/daily/*.csv` 裡**興櫃無成交日被寫成 0 價**的列。

    python3 fix_emerging_zero.py            # 只報告，不寫
    python3 fix_emerging_zero.py --write    # 真的改

## ⛔ 為什麼要有這一支

`fetch.parse_openapi_daily` 原本用 `if not c: continue` 判零，
而 `_num()` 回的是**字串**、`"0.00"` 是 truthy ⇒ **判不掉**。
⇒ 興櫃無成交日**帶著 `0` 被寫進去**（`data/universe/esb/` 那一份早就用
`_isz()` 擋掉了——又是同一段判斷抄兩份、只修了一份）。

⭐ 寫入端 2026-09-10 已經修好，⛔ **但它只影響之後寫的**。歷史那些要靠這一支。

## ⛔⛔ 真正咬人的不是那個 0，是**從它算出來的 `change`**

K線線 2026-09-10 14:55：

> 我 09-09 稽核量到 6518 康科特 **−31.60%**、6539 麗彤 **−41.05%**、
> 6816 捷智商訊 **−35.32%**——**那幾天成交量都是 0**。
> 在我的判讀層，一根 −31.6% 的長黑會**同時**觸發：跌破所有均線、長黑 K、
> 單日停損、爆量下跌。⛔ **它不是「一格數字不好看」，
> 它是一個完整的、會通過所有型別檢查的假出場訊號。**

⚠ 我方實測比那更糟：**61 列／36 檔／5 天，每一列的 `change` 都是編出來的**，
最大 **−139.50**（＝比前一日均價低 139.5 元，換算超過 −100%）。
⛔ 而那些列的 `price_basis` 還寫著 `均價/額推算` ⇒ **照 `price_basis` 篩會篩進來。**

⭐ K線線抽出來的通則，這一支照做：
**一個壞掉的來源欄會沿著「用它算出來的欄位」擴散，而下游只看到後者。**
⇒ ⛔ 擋壞資料要**連同衍生欄位一起擋**，光擋來源欄不夠。

## 改什麼（與現在的寫入端逐格一致）

    open / high / low / close  → 空字串
    change                     → 空字串   ← ⭐ 這一格才是重點
    limit                      → 空字串   （沒有價格就沒有「停」）
    price_basis                → `無成交`
    ⛔ volume / amount 不動：照官方原文（雖然這些列本來就是 0）

## 安全設計（照抄 `fix_limit.py` 的那一套）

⛔ 只改**中招那幾列的那幾格**，其他一個字都不動。
寫檔前先做**空跑往返**：把讀進來的列原封不動寫回去，位元組不同就整檔跳過
——⚠ 絕不冒著改壞別欄的風險去修一欄。
⛔ 跳過任何一檔都要看得見：「只改了一半」是最貴的形狀。
"""
import argparse
import csv
import glob
import io
import os
import sys

import runlog
from twparse import render_csv as _render_csv
from fetch import _isz

DAILY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "universe", "daily")
# ⚠ 這幾欄清空，⛔ `volume`／`amount` 不在裡面（照官方原文）
BLANK = ("open", "high", "low", "close", "change", "limit")


# ⛔ 第十二份：`_render` 兩支修復腳本各一份。
#   ⭐ 是 pre-commit 的「同一件事只准一份」**當場擋下來的**——
#     ⚠ 而那個守門是同一天才裝上去的，這是它抓到的第一件。
_render = _render_csv


def fix_body(header, body):
    """→ (改了幾列, 這一批被清掉的 change 樣本)。⛔ 抽成函式是為了讓 selftest 測得到。"""
    need = ("market", "close", "price_basis") + BLANK
    if any(c not in header for c in need):
        return None, []
    idx = {c: header.index(c) for c in set(need)}
    n, samples = 0, []
    for r in body:
        if len(r) <= max(idx.values()):
            continue
        if r[idx["market"]] != "emerging":
            continue
        c = r[idx["close"]]
        # ⭐ 判零一律走 `_isz`：`_num()` 回的是字串，`"0.00"` 是 truthy
        #   ——⛔ 這正是當初漏掉的那一條。
        if c.strip() == "" or not _isz(c):
            continue
        old_chg = r[idx["change"]]
        for col in BLANK:
            r[idx[col]] = ""
        r[idx["price_basis"]] = "無成交"
        n += 1
        if old_chg.strip():
            samples.append(old_chg)
    return n, samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="真的寫檔（預設只報告）")
    a = ap.parse_args()
    rl = runlog.Run("fix_emerging_zero")

    files = sorted(glob.glob(os.path.join(DAILY, "*.csv")))
    rows_fixed = files_fixed = 0
    skipped, all_samples, days = [], [], []
    for p in files:
        with io.open(p, encoding="utf-8", newline="") as f:
            raw = f.read()
        rows = list(csv.reader(io.StringIO(raw, newline="")))
        if not rows:
            continue
        header, body = rows[0], rows[1:]
        # ★ 空跑往返：原封不動寫回去必須位元組相同，否則不碰這一檔
        if _render(header, body) != raw:
            skipped.append((os.path.basename(p), "空跑往返不相同，不敢改"))
            continue
        n, samples = fix_body(header, body)
        if n is None:
            skipped.append((os.path.basename(p), "缺必要欄位"))
            continue
        if n:
            rows_fixed += n
            files_fixed += 1
            days.append(os.path.basename(p)[:-4])
            all_samples += samples
            if a.write:
                with io.open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(_render(header, body))

    rl.info("掃過的日檔", f"{len(files):,} 檔")
    rl.info("中招的", f"**{files_fixed} 檔／{rows_fixed} 列**"
            + ("（**已寫入**）" if a.write else "（只報告，加 --write 才寫）"))
    if days:
        rl.info("  哪幾天", "｜".join(sorted(days)))
    if all_samples:
        worst = sorted(all_samples, key=lambda s: float(s or 0))[:5]
        rl.info("⛔ 被清掉的假 `change`（最極端的 5 個）", "｜".join(worst)
                + "　⚠ 那幾天成交量都是 0 ⇒ 這是**完整的、會通過所有型別檢查的假出場訊號**")
    if skipped:
        rl.info("跳過", f"{len(skipped)} 檔：{skipped[:5]}")
    # ⛔ 跳過任何一檔都要看得見——「只改了一半」是最貴的形狀
    rl.check("沒有任何日檔被跳過", not skipped,
             f"{len(skipped)} 檔沒改到，清單在上面")
    # ⭐ 寫入之後要**真的沒有了**（⛔ 不是「我以為改完了」）
    if a.write:
        left, _ = 0, None
        for p in files:
            with io.open(p, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("market") == "emerging" and (r.get("close") or "").strip() \
                            and _isz(r.get("close")):
                        left += 1
        rl.check("寫完之後**一列都不剩**", left == 0, f"還有 {left} 列")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
