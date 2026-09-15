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
import csv
import io
import re
import time
import urllib.error
import urllib.parse
import urllib.request
# ⭐ 補上 TPEx 漏送的憑證鏈（⛔ 不降低驗證，見 `ca_chain.py`）。
import ca_chain  # noqa: F401

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


def actions_in(raw, prefix=None):
    """TPEx 頁面的 inline script → 它自己寫的 `action:` 清單（已排序去重）。

    ## ⛔ 為什麼要從**頁面自己寫的字**讀，不是從網址猜

    2026-09-15 付過代價：第一版是從 `url` 推（`"pvChgAnn" if "pvChgAnn" in url`），
    ⚠ 而那兩頁的網址是 `/announce/market/change.html`——`action` 根本不在網址裡。
    ⇒ 那一版對**真的頁面**也永遠推不出東西。
    ⭐ 這是三點5 那條的同一個形狀：**不要照名字推一個東西管什麼。**

    配上 `API_PATTERN = "/www/{LANG}/{ACTION}"`，資料端點就是 `/www/<lang>/<action>`。

    ⛔⛔ `prefix` 預設是 **None ＝ 全收**。⚠ 這一條是有代價才寫成這樣的：
    上一版把 `bulletin/` **寫死在正規式裡** ⇒ 想問別的區段（`afterTrading/` …）
    的人只能再寫一份 ⇒ 那就是第二份實作（四點五）。
    ⇒ 要縮範圍的人自己傳 `prefix`，⛔ 而預設不縮——
    **一個預設就把掃描範圍縮小的函式，下一個人不會知道它縮了**（三點①）。
    """
    txt = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else (raw or "")
    got = re.findall(r'action\s*:\s*["\']([A-Za-z0-9_]+/[A-Za-z0-9_]+)["\']', txt)
    return sorted({a for a in got if prefix is None or a.startswith(prefix)})


def pick_field(fields, *words):
    """欄位名**包含**其中任一個關鍵字 ⇒ 回它的位置。找不到回 None。

    ⚠ 是「包含」比對，所以呼叫端給的關鍵字要夠長——
      `"代號"` 會先撞上同一張表裡的 `ISIN代號`（2026-09-10 實測踩過）。
    """
    for i, f in enumerate(fields):
        if any(w in str(f) for w in words):
            return i
    return None


def post_form(url, form, timeout=120, retries=3, sleep=None):
    """`application/x-www-form-urlencoded` 的 POST。→ (bytes, err)。

    ⛔ 這一份原本在 `otc_exright_history.py` 與 `otc_reduce_history.py` 各一份
      （逐字相同）——同一族的第九、第十份。2026-09-10 收成一份。

    ⚠ `Referer` 帶的是 url 自己：TPEx 的 `bulletin/*` 沒有它會被擋。
    ⚠ 例外一律吃掉並回成 `err` 字串（⛔ 不 raise）——呼叫端要能分辨
      「取不到」與「取到但內容不對」，那是兩種完全不同的處置。

    ## ⭐ 重試（2026-09-10 加）

    `mops_probe.py` 連兩趟都是**暫時性**網路錯誤斷掉：

        _ssl.c:993: The handshake operation timed out
        RemoteDisconnected: Remote end closed connection without response

    ⚠ 而那兩趟的結論都寫成「**未驗**」——⭐ 結論是對的（沒取到就是沒驗到），
      ⛔ 但代價是**要有人再按一次**。
    ⇒ 退避重試 3 次（2s、4s）。⚠ **只重試連線層的失敗**：
      ⛔ HTTP 4xx 不重試（那是參數錯，重試幾次都一樣，只是多打對方幾發）。

    ⚠ `sleep` 可注入 ⇒ 自測不必真的等（⛔ 會等好幾秒的測試沒有人會跑）。
    """
    _sleep = time.sleep if sleep is None else sleep
    body = urllib.parse.urlencode(form, encoding="utf-8").encode("utf-8")
    last = ""
    for i in range(max(1, retries)):
        req = urllib.request.Request(
            url, data=body,
            headers={"User-Agent": "Mozilla/5.0", "Referer": url,
                     "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except urllib.error.HTTPError as ex:
            last = f"HTTPError: HTTP {ex.code} {ex.reason}"
            # ⛔ 4xx 是「我送錯了」，重試沒有意義（408／429 例外：那是時間問題）
            if 400 <= ex.code < 500 and ex.code not in (408, 429):
                return b"", last
        except Exception as ex:                                  # noqa: BLE001
            last = f"{type(ex).__name__}: {str(ex)[:120]}"
        if i < retries - 1:
            _sleep(2 * (i + 1))
    return b"", last + (f"（重試 {retries} 次都失敗）" if retries > 1 else "")


def csv_cell(v, sep="；"):
    """任意文字 → **可以直接塞進一格 CSV** 的字串。⭐ 全庫唯一那一份（四點五）。

    ## ⛔ 這一支存在的理由：`_official_stats_miss.csv` 裡有 HTML

    2026-09-16 實測，那份判準檔 106 列裡有 **2 列是 `<head>` 與 `<meta h`**：

    ```python
    f.write(f"{sid},{n},{asof},{str(why).replace(',', '；')}\n")   # ⛔ 只換了逗號
    ```

    ⚠ 而 `why` 可能是**整頁 HTML**——CLAUDE.md 第二點④：TWSE 被 CDN 擋時回的是
    HTTP 428 ＋ HTML。⇒ 那串字裡的 `\n` 把**一列切成好幾列**
    ⇒ ⛔ 判準檔被污染，而 `load_miss()` 讀到的是 `stock_id="<head>"` 這種列。

    ⭐ 它的壞法是最難看出來的那一種：檔案在、格式看起來對、程式不報錯，
    ⚠ 只是**列數多了**、而多出來的那幾列永遠對不到任何代號。

    ⇒ 這裡把**所有**空白（含 `\n`／`\r`／`\t`）收成一個空格，再換掉逗號與引號。
    ⛔ 不截斷：錯誤訊息可行動的部分常常在後面（六點六）——要截由呼叫端自己決定。
    """
    t = " ".join(str(v).split())
    return t.replace(",", sep).replace('"', "'")


def render_csv(header, rows):
    """→ CSV 文字（`\n` 結尾符，跟 repo 裡的日檔一致）。

    ⛔ 這一份原本在 `fix_limit.py` 與 `fix_emerging_zero.py` 各一份——
      ⭐ 而且是 `.githooks/pre-commit` 的「同一件事只准一份」**當場擋下來的**
      （2026-09-10，第十二份）。⚠ 那個守門是同一天才裝上去的。

    ⚠ 這一支的用途很特定：**修復腳本的「空跑往返」**——
      把讀進來的列原封不動寫回去，位元組要跟原檔相同；
      不同就代表 csv 模組的引號規則跟原檔不一致 ⇒ ⛔ 那一檔不敢改。
    """
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()
