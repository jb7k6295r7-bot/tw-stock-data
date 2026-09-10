#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""delist_probe.py — 下市清單與變更交易（全額交割）的端點探針。⛔ 只測不寫資料。

## 兩支都是情報分析線 2026-09-10 16:25 掃 TWSE 選單 **280 條**撿到的

### ① `company/suspendListing` —— 終止上市（下市）清單，我方**一筆都沒有**

⭐ **為什麼重要：生存者偏誤。**
下市公司會從母體消失 ⇒ 母體只收「現在還在的」
⇒ 「2015 買、後來下市」那一段**整段不見** ⇒ **回測績效系統性偏樂觀**。
265 筆裡有 2888 新光金、2867 三商壽、2809 京城銀、3682 亞太電。

⛔ **它的頂層鍵是第三種形狀**（情報分析線實測）：
`status`／`data`／`total`／`minYear`／`maxYear`
——**不是 `stat`，資料也不在 `tables`，是直接在頂層 `data`**。
⇒ 我方 `_tables()` 認得 `stat`+`tables` 與頂層 `fields`+`data` 兩種，
⚠ **這一種沒有 `fields`** ⇒ 欄位怎麼對？**這支探針就是要回答這個。**
⛔ 在看到真回應之前不寫 parser。

⚠ `yy` 參數被無視（帶 `yy=115` 也回全部 265 筆）⇒ 不要拿它驗年份。

### ② `fullDelivery/TWT85U` —— 變更交易（全額交割），**有逐日歷史**

⭐ 這一支解掉 K線線 15:45 的 Q5：他們的前置閘門有「全額交割股」一列，
而我方 `_db_status.md` 全文查「全額交割」**0 次** ⇒ 那一列**目前不可執行**。
⚠ 而 K線線自己說過：**「假裝有在擋」比沒有擋更危險**，因為下游會以為過了關。

情報分析線實測 `date` 是真的吃（title 與筆數都跟著變）：
2015-01-05 → 23 檔｜2020-01-03 → 21 檔｜2026-09-10 → 9 檔。
⇒ ⭐ **可以逐日回補。**

⚠ 官方 notes（`BFIHBU`）逐字：「變更交易有價證券**不得進行當日沖銷交易、
融資融券交易、借券交易、平盤以下借券賣出**」
⇒ ⛔ **「融資融券欄位是 0」至少有兩個成因**：
① 主管機關個別公告停止融資融券（`MI_MARGN` 備註欄，且那是**次一營業日**狀態）
② 被列為**變更交易**（全額交割）⇒ 連當沖與借券一起禁掉
**只查其中一個名單會誤判。**

### ⛔ 順帶驗一個解析陷阱：`violation/change` 的值裡混著**隱藏 span**

    "108年06月17日<span class=\\"hide\\">1213</span>"

⇒ 直接吃會把**代號混進日期**，⚠ **而且不報錯**
（日期解析失敗變 null，或字串比對永遠不相等）。
⇒ 這支探針把原始字串**原樣**印出來，讓人看得到那段 HTML 在不在。
"""
import io
import json
import os
import sys

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_delist_probe.txt")

TW = "https://www.twse.com.tw/rwd/zh"
DAYS = ("20150105", "20200103", "20260909")

TARGETS = [
    ("終止上市清單 company/suspendListing",
     f"{TW}/company/suspendListing?response=json", {}),
    ("⚠ 同上，帶 yy=115（情報分析線說這個參數被無視 ⇒ 驗它）",
     f"{TW}/company/suspendListing?yy=115&response=json", {"yy": "115"}),
] + [
    (f"變更交易 fullDelivery/TWT85U（{d}）",
     f"{TW}/fullDelivery/TWT85U?date={d}&response=json", {"date": d})
    for d in DAYS
] + [
    ("新增之變更交易證券 fullDelivery/BFIHBU",
     f"{TW}/fullDelivery/BFIHBU?response=json", {}),
    ("⛔ 隱藏 span 的陷阱 violation/change",
     f"{TW}/violation/change?response=json", {}),
]


def probe(label, url, want, out):
    out.append(f"── {label}")
    out.append(f"   {url}")
    raw, err = B.get(url, retries=2, timeout=45)
    if err:
        gw = ("Tunnel connection failed" in str(err)
              or "connect_rejected" in str(err))
        out.append(f"   ✗ {err[:200]}"
                   + ("　⚠ **這是我方閘道擋的**（Actions 上會是通的）" if gw else ""))
        return
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:                                       # noqa: BLE001
        out.append(f"   ✗ 不是 JSON（{type(e).__name__}）；bytes={len(raw)}；"
                   f"前 200：{raw[:200]!r}")
        return
    # ⭐ 規矩第一條：先把**全部頂層鍵**攤開
    out += ["   " + s for s in B.describe_response(d, want=want)]
    # ⛔ 這幾支可能**沒有 `tables`、也沒有 `fields`** ⇒ 三種形狀都要看得到
    if isinstance(d, dict):
        out.append(f"   頂層 `fields`：{d.get('fields')}")
        top_data = d.get("data")
        if isinstance(top_data, list):
            out.append(f"   ⭐ 頂層 `data`：{len(top_data)} 列"
                       f"（第一列的型別 {type(top_data[0]).__name__ if top_data else '—'}）")
            for r in top_data[:3]:
                out.append(f"     樣本：{json.dumps(r, ensure_ascii=False)[:220]}")
    tabs = B._tables(d)
    out.append(f"   `_tables()` 認出 {len(tabs)} 張表")
    for t in tabs[:2]:
        f = [str(x) for x in (t.get("fields") or [])]
        data = t.get("data") or []
        out.append(f"     欄位（{len(f)}）：{f}")
        out.append(f"     列數：{len(data)}")
        for r in data[:3]:
            out.append(f"       樣本：{json.dumps(r, ensure_ascii=False)[:220]}")
    # ⛔ 隱藏 span：**原樣**印出來，⚠ 不要先剝掉——要讓人看得到它在不在
    blob = raw.decode("utf-8", "replace")
    if "class=\\\"hide\\\"" in blob or 'class="hide"' in blob:
        i = blob.find("hide")
        out.append("   ⛔ **值裡有 `<span class=\"hide\">`**（排序用的隱藏 HTML）"
                   "⇒ 直接吃會把代號混進日期，⚠ **而且不報錯**")
        out.append(f"     附近原文：…{blob[max(0, i - 90):i + 60]}…")


def main():
    out = ["# 下市清單／變更交易 端點探針",
           "# ⛔ 只測不寫資料。開發容器對交易所一律 403（我方閘道）——看 Actions 的結果",
           "# ⚠ 這兩支的頂層形狀可能是**第三種**（`status`+頂層 `data`，沒有 `fields`）",
           "#   ⇒ 這支就是要回答「欄位怎麼對」，⛔ 在那之前不寫 parser。",
           ""]
    for label, url, want in TARGETS:
        try:
            probe(label, url, want, out)
        except Exception as e:                                   # noqa: BLE001
            out.append(f"   ✗ 探針自己炸了：{type(e).__name__}: {e}")
        out.append("")
    out += [
        "## ⇒ 拿到結果之後要回答的",
        "  Q1 `suspendListing` 的列是 list 還是 dict？欄位順序／鍵名是什麼？",
        "  Q2 `TWT85U` 的 `date` 真的吃嗎（三個日期的 title 與筆數要不同）？",
        "  Q3 `violation/change` 的隱藏 span 長什麼樣（剝法要照真形狀寫）？",
        "  ⚠ Q4 `suspendListing` 的 `yy` 是不是真的被無視（兩趟筆數要一樣）？",
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[delist_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
