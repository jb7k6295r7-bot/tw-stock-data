#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""official_formula.py — 官方回應裡的 `formula` 鍵：**留下來，而且盯著它變**。
**純計算，不連外、不寫資料。**

## ⭐⭐ 為什麼：`_tables()` 只取 `title`／`fields`／`data`，其餘整個丟掉

CLAUDE.md 第一點講的就是這件事，⚠ 而 2026-09-13 的探針證實 `formula` 是其中之一：

```
TWTAUU（減資恢復買賣參考價）的 formula：
  彌補虧損之減資並現金增資：
    恢復買賣參考價＝(停止買賣前收盤價)/(減資換股率)
    減資後現金增資除權參考價＝(恢復買賣參考價+現金增資認購價*減資後現金增資配股率)
                              /(1+減資後現金增資配股率)
TWT48U（除權除息預告表）的 formula：
    無償配股率＝(股東之盈餘及資本公積增資股數)/(參與除權之發行股數)
    現金增資配股率＝(現金增資股數)/(參與除權之發行股數)
```

⛔ 而我方在 2026-09-12~13 花了兩輪去**推**那兩條式子（`reduce_shares_check.py`
的「兩種減資算式」「兩種除權算式」）——⚠ **官方每天都在同一個回應裡給我們**。

## ⇒ 而「留下來」只做了一半，另一半是**盯著它變**

⚠ 官方改公式的時候，回應仍然 `stat=OK`、欄位不變、列數不變
⇒ ⛔ 我方算出來的參考價會**整批**跟著錯，而沒有任何地方會叫（第二點那一族）。
⇒ 本支把**看過的**公式釘在 `KNOWN` 裡（⭐ 判準寫在程式裡，會被 review），
  對不上就大聲講。

## ⛔ 而「沒有記錄」跟「一樣」**必須分開**

```
same      ⇒ 跟釘住的那份逐字相同
changed   ⇒ ⛔⛔ 官方改了公式（或我方打到了別張表）
unknown   ⇒ ⚠ 這條端點有 formula 而我方**沒有記錄** ⇒ 要有人去看一眼再釘
absent    ⇒ 這個回應沒有 formula 鍵（⛔ 不是「沒有公式」，只是這張表沒給）
```
⚠ 把 `unknown` 併進 `same` 的話，新端點的公式**永遠不會有人看**；
⛔ 把它併進 `changed` 的話，它會天天紅、然後被學會忽略（六點五）。
"""
import re

# ⭐ 看過的公式。⛔ 要加一條之前，先真的把官方那一段讀過一次。
#   ⚠ 鍵是**我方的 feed 名**（`FEEDS` 的鍵），⛔ 不是端點代號
#     ——同一個代號可以被不同 feed 用，而 feed 才是「誰在讀它」。
KNOWN = {
    # 2026-09-13 `_reduce_ratio_probe.txt` 逐字抄回來的（TWSE reducation/TWTAUU）
    # ⭐⭐ 而抄的過程就撿到一件我**推錯**的事：退還股款那一條有 **息值** 這一項，
    #   而且「每股退還股款」是官方**直接給的欄位**（TWTAVU 有那一欄）
    #   ——⛔ 而我方 `reduce_shares_check.implied_cash()` 推的是「面額 10 × 減資比率」。
    #   ⚠ 兩件事都不是猜得到的：`除息併案辦理減資` 這種案子（TWTAVU 的 notes 就舉了
    #     2323 中環）會同時扣掉現金股利，⛔ 而我方的式子裡根本沒有那一項。
    "reduce": [
        "退還股款：恢復買賣參考價＝（停止買賣前收盤價-息值-每股退還股款）/（減資換股率）",
        "彌補虧損：恢復買賣參考價＝（停止買賣前收盤價）/（減資換股率）",
        "彌補虧損之減資並現金增資：<br>　恢復買賣參考價＝（停止買賣前收盤價）/（減資換股率）"
        "<br>　減資後現金增資除權參考價＝（恢復買賣參考價+現金增資認購價*減資後現金增資配股率）"
        "/（1+減資後現金增資配股率）",
    ],
    # 2026-09-13 `_reduce_ratio_probe.txt`：TWSE exRight/TWT48U（除權除息預告表）
    "exright_pre": [
        "無償配股率＝(股東之盈餘及資本公積增資股數)/(參與除權之發行股數)"
        "<br>現金增資配股率＝(現金增資股數)/(參與除權之發行股數)",
    ],
}

_TAG = re.compile(r"<[^>]{1,80}>")
_WS = re.compile(r"\s+")


def normalize(s):
    """→ 可以逐字比的字串。⛔ `<br>` 與空白不算差異，⚠ 而**字**算。"""
    t = _TAG.sub("", str(s))
    t = t.replace("　", " ").replace("：", ":").replace("；", ";")
    return _WS.sub("", t)


def pull(d):
    """→ 回應裡的 formula 清單（沒有就回 `[]`）。

    ⚠ 官方給過兩種形狀：字串、字串陣列 ⇒ 兩種都收。
    """
    if not isinstance(d, dict):
        return []
    f = d.get("formula")
    if f is None:
        return []
    if isinstance(f, str):
        return [f]
    if isinstance(f, (list, tuple)):
        return [str(x) for x in f]
    return [str(f)]


def check(feed, d):
    """→ (狀態, 訊息)。狀態是 absent／unknown／same／changed 四選一。

    ⛔ 四種**不可以**合併，理由見檔頭。
    """
    got = pull(d)
    if not got:
        return "absent", ""
    known = KNOWN.get(feed)
    if known is None:
        return "unknown", ("⚠ 這條端點有 `formula` 而我方**沒有記錄**"
                           f"（{len(got)} 段）：" + " ｜ ".join(
                               normalize(x)[:160] for x in got))
    a = [normalize(x) for x in got]
    b = [normalize(x) for x in known]
    if sorted(a) == sorted(b):
        return "same", f"{len(a)} 段，與釘住的那份逐字相同"
    only_new = [x for x in a if x not in b]
    gone = [x for x in b if x not in a]
    return "changed", (
        f"⛔⛔ 官方公式**變了**（我方 {len(b)} 段、官方 {len(a)} 段）"
        + (f"｜⭐ 官方多出來：{ ' ｜ '.join(x[:200] for x in only_new) }" if only_new else "")
        + (f"｜⛔ 我方有而官方沒有：{ ' ｜ '.join(x[:200] for x in gone) }" if gone else ""))
