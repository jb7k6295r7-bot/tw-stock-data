#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""twparse.py — 交易所回應裡**共用的小解析**。⛔ 這一份是唯一的一份。

## 為什麼獨立成一支

`otc_exright_history.py` 與 `otc_reduce_history.py` 原本**各有一份** `_iso`／`_pick`
（逐字相同）。2026-09-10 使用者指出「同一段邏輯抄兩份、只修一份」已經第三次——
往下掃是**第六次**，而這一對是第七、第八份。⇒ 收成一份。
規矩見 `CLAUDE.md` 第四點五：**同一件事只准有一份實作。**

## ⛔ 這一支存在的第二個理由：日期格式不是一種

`bulletin/revivt` 2026-09-10 在 Actions 上回了 **283 列，我方一列都認不出來**——
舊的 `_iso` 只吃 `115/09/10` 與 `2026-09-10` 兩種。
⚠ 而當時的失敗訊息只有「一列都認不出來（bad=283）」＋欄位名，
**不足以診斷** ⇒ 得再打對方一次才知道原因。
⇒ 這裡把官方會出現的寫法列齊，並且**逐一測過**。
⛔ 仍然「認不出就回 None」——⚠ 猜一個日期比認不出更糟。
"""
import re
import urllib.parse
import urllib.request

# 民國↔西元的分界：官方民國年一律 < 1000（例：115），西元 > 1990。
_ROC_ADD = 1911


def roc_iso(v):
    """官方各種日期寫法 → `YYYY-MM-DD`。⛔ 認不出回 `None`（不猜）。

    吃得下（每一種都在 `selftest_twparse.py` 裡有正例）：

        115/09/10   115/9/10    民國，斜線
        115-09-10               民國，連字號
        115年09月10日            民國，中文
        1150910                 民國，7 碼連寫
        2026-09-10  2026/09/10  西元
        20260910                西元，8 碼連寫
        前後有空白、全形空白

    ⛔ 認不出（一樣在自測裡有反例）：空字串、`--`、`115/13/01`、
      `115/09`、`abc`、`0000000`。
    """
    s = str(v).strip().replace("　", " ").strip()
    if not s:
        return None
    # 中文年月日 → 斜線
    s = re.sub(r"[年月]", "/", s).replace("日", "")
    s = s.replace("-", "/").replace(".", "/").strip("/")
    if s.isdigit():
        # ⚠ 靠**長度**分民國與西元，兩者不重疊：7 碼是民國、8 碼是西元。
        #   ⛔ 不可以只看數值：`1150910` 當成西元年就變成公元 1150910 年。
        if len(s) == 7:
            s = f"{s[:3]}/{s[3:5]}/{s[5:]}"
        elif len(s) == 8:
            s = f"{s[:4]}/{s[4:6]}/{s[6:]}"
        else:
            return None
    p = [x.strip() for x in s.split("/") if x.strip() != ""]
    if len(p) != 3 or not all(x.isdigit() for x in p):
        return None
    y, m, d = (int(x) for x in p)
    if y < 1000:
        y += _ROC_ADD
    if not (1990 < y < 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def pick_field(fields, *words):
    """欄位名**包含**其中任一個關鍵字 ⇒ 回它的位置。找不到回 None。

    ⚠ 是「包含」比對，所以呼叫端給的關鍵字要夠長——
      `"代號"` 會先撞上同一張表裡的 `ISIN代號`（2026-09-10 實測踩過）。
    """
    for i, f in enumerate(fields):
        if any(w in str(f) for w in words):
            return i
    return None


def post_form(url, form, timeout=120):
    """`application/x-www-form-urlencoded` 的 POST。→ (bytes, err)。

    ⛔ 這一份原本在 `otc_exright_history.py` 與 `otc_reduce_history.py` 各一份
      （逐字相同）——同一族的第九、第十份。2026-09-10 收成一份。

    ⚠ `Referer` 帶的是 url 自己：TPEx 的 `bulletin/*` 沒有它會被擋。
    ⚠ 例外一律吃掉並回成 `err` 字串（⛔ 不 raise）——呼叫端要能分辨
      「取不到」與「取到但內容不對」，那是兩種完全不同的處置。
    """
    body = urllib.parse.urlencode(form, encoding="utf-8").encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"User-Agent": "Mozilla/5.0", "Referer": url,
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except Exception as ex:                                      # noqa: BLE001
        return b"", f"{type(ex).__name__}: {str(ex)[:120]}"
