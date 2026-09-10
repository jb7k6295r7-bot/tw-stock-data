#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""keys_probe.py — 官方回應裡**我方一路丟掉的那些鍵**到底寫了什麼。

## 為什麼開這一支

使用者 2026-09-10 問：「官方回應裡有 `notes` 欄，我一直沒讀，對妳有用嗎？」
⇒ 先查我方到底有沒有讀。結果是**完全沒有**：

    _tables() 只取 title / fields / data
    ⛔ 被丟掉的：stat、date、notes、hints、params、total …
    而且丟的時候**沒有任何紀錄**——連「有這些鍵」都不知道。

⭐ 這一支不猜「notes 有沒有用」，它**把那些鍵原文印出來**，讓資料自己回答。

## ⭐ 三個已經看得出來的用處（各自對應一件我今晚手工做的事）

### ① `total`：官方自己說有幾列 ⇒ **免費的每次請求完整性斷言**

我今晚為了「有沒有漏」自己造了好幾個判準：
N₁、Σ上市 amount ÷ 官方大盤、六張官方清單差集（67,446 筆）……
⚠ 而端點可能**每一次都在告訴我它給了幾列**。
⇒ `total` vs `len(data)` vs 我方寫出的列數，三個數字對不上就該叫。

### ② `params`：⇒ **「參數有沒有生效」的直接檢查**

今天為了防「靜靜回今天」，我在三支程式裡各寫了一道
「回應要講出我請求的那一天」。而 `params` 是端點**把收到的參數回顯**——
情報分析線 09:47 就是靠它才看懂 `TWTAWU` 的 `date=` 是假參數
（`params` 回 `{date:"20150105", startDate:"20260813", endDate:"20260813"}`）。

### ③ `notes`：⇒ 可能是 **`X` 旗標的權威出處**

`adj_gap.py` 有五處寫著「官方 `X0.00`，`X` ＝ 無前一日收盤價可資比較」，
而那一句**我方沒有留下出處**——它是推論還是讀來的，現在說不清。
⚠ 而那句話正是「轉上市首日不算缺陷」這個歸因的地基。
⇒ 若 `notes` 裡有符號說明，它就是權威出處；若沒有，那句話要降級成推論。

⛔ 本支**只讀不寫資料**，輸出進 `data/meta/_keys_probe.txt`。
"""
import io
import json
import os
import sys
import traceback

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_keys_probe.txt")

DAY = "2026-09-09"
YMD = DAY.replace("-", "")
TW = "https://www.twse.com.tw/rwd/zh"
TP = "https://www.tpex.org.tw"

# ⛔ 只挑**我方每天真的在用**的端點。加一堆沒在用的只會讓報告變長。
# ⭐ 第三個元素是「我送出去的參數」——有了它才對得起 `params` 回顯，
#   而那正是看穿「假參數」的方法（TWTAWU 的 `date=` 就是假的）。
TARGETS = [
    ("上市每日收盤行情 MI_INDEX",
     f"{TW}/afterTrading/MI_INDEX?date={YMD}&type=ALLBUT0999&response=json",
     {"date": YMD, "type": "ALLBUT0999"}),
    ("上市三大法人 T86",
     f"{TW}/fund/T86?date={YMD}&selectType=ALLBUT0999&response=json", {"date": YMD}),
    ("上市融資融券 MI_MARGN",
     f"{TW}/marginTrading/MI_MARGN?date={YMD}&selectType=ALL&response=json", {"date": YMD}),
    ("上市外資持股 MI_QFIIS（上市 shares 的來源）",
     f"{TW}/fund/MI_QFIIS?date={YMD}&selectType=ALLBUT0999&response=json", {"date": YMD}),
    ("上市除權息 TWT49U",
     f"{TW}/afterTrading/TWT49U?date={YMD}&response=json", {"date": YMD}),
    ("上市暫停交易 TWTAWU",
     f"{TW}/afterTrading/TWTAWU?startDate=20150101&endDate={YMD}&response=json",
     {"startDate": "20150101", "endDate": YMD}),
    ("上櫃每日收盤行情",
     f"{TP}/www/zh-tw/afterTrading/otc?date={DAY.replace('-', '/')}&response=json",
     {"date": DAY.replace('-', '/')}),
    ("上櫃融資融券 margin/balance",
     f"{TP}/www/zh-tw/margin/balance?date={DAY.replace('-', '/')}&response=json",
     {"date": DAY.replace('-', '/')}),
]

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# keys_probe.py 的輸出。**只讀不寫資料。**\n")
            f.write("# 問的是：官方回應裡那些我方一路丟掉的鍵，到底寫了什麼。\n")
            f.write("# ⛔ 我方 `_tables()` 只取 title/fields/data，其餘全丟，"
                    "而且丟的時候沒有紀錄。\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[keys] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[keys] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


def show(label, url, want=None):
    say(f"── {label}")
    say(f"   {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err or not raw:
        say(f"   ✗ 抓不到：{str(err)[:120]}")
        say("")
        return
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        head = raw[:100].decode("utf-8", "replace").replace("\n", " ")
        say(f"   ✗ 不是 JSON（{str(ex)[:40]}）｜開頭={head!r}"
            "　⚠ 若是 HTML 多半是被擋")
        say("")
        return
    if not isinstance(d, dict):
        say(f"   ⚠ 頂層不是 dict，是 {type(d).__name__}")
        say("")
        return
    # ⛔ 這裡本來自己抄了一份「攤開被丟掉的鍵」的邏輯。
    #   同一段邏輯抄兩份今晚已經害過一次（`limit` 的 bug 在兩支裡各一份）。
    #   ⇒ 改用共用的 `B.describe_response()`，那也是使用者
    #     「新端點第一件事就是把 notes／hints／title 印出來」那條規矩的執行者。
    for ln in B.describe_response(d, want=want):
        say(f"   {ln}")
    say("")


def main():
    say("── 官方回應裡我方丟掉的鍵 ──")
    say("⛔ `_tables()` 只取 title/fields/data。其餘（stat／date／notes／hints／"
        "params／total…）**全部丟掉，而且沒有紀錄**。")
    say("⭐ 這一支不猜它們有沒有用——把原文印出來，讓資料自己回答。")
    say(f"⚠ 測試日固定 {DAY}（交易日）。")
    say("")
    for label, url, want in TARGETS:
        show(label, url, want)
    say("── 要從這份輸出回答的三件事 ──")
    say("  ① `total` 對得上我方解析出的列數嗎 ⇒ 若對得上，這是**免費的**每次請求完整性斷言")
    say("  ② `params` 有沒有把我送的參數回顯 ⇒ 那是「參數有沒有生效」的直接檢查")
    say("  ③ `notes` 裡有沒有**符號說明** ⇒ `adj_gap.py` 五處寫的"
        "「官方 X0.00 ＝ 無前一日收盤價可資比較」目前**沒有留下出處**；")
    say("     有的話它就是權威出處，⛔ 沒有的話那句話要降級成推論"
        "（而它是「轉上市首日不算缺陷」那個歸因的地基）。")
    return _write(0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                        # noqa: BLE001
        say("")
        say("✗ 這一趟炸了，traceback 原文：")
        say(traceback.format_exc())
        _write(1)
        raise
