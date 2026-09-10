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
TPX = "https://www.tpex.org.tw"
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
    # ⭐ K線線 16:40 §3 的第三個成因（他們自己標【未查證】，⛔ 沒有寫進 skill）：
    #   「該檔**本來就不是信用交易標的**——不是被停掉的，是從來就沒有。」
    #   ⚠ ①② 是**負面訊號**（被主管機關盯上），③ 是**中性的**（新股、制度性），
    #   ⛔ 而三者在資料上**都長成「融資餘額 0」**。
    #   ⇒ 先問「有沒有這種名單」。⛔ 路徑是**照同站模式推的**，這裡就是要淘汰它們。
    ("信用交易標的？ marginTrading/MI_MARGN_MSTOCK（推的）",
     f"{TW}/marginTrading/MI_MARGN_MSTOCK?response=json", {}),
    ("信用交易標的？ marginTrading/TWT78U（推的）",
     f"{TW}/marginTrading/TWT78U?response=json", {}),
    ("信用交易標的？ marginTrading/MI_MARGN?selectType=MS（推的）",
     f"{TW}/marginTrading/MI_MARGN?date={DAYS[-1]}&selectType=MS&response=json",
     {"date": DAYS[-1], "selectType": "MS"}),
    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 上櫃那半邊（K線分析線 2026-09-11 01:40 的三分類卡在這裡）
    #
    # ⚠ 這兩條**不是推的**：它們逐字寫在我方自己的
    #   `data/meta/_tpex_probe.txt`（TPEx openapi 225 個端點的快照）裡：
    #     /tpex_spendi_history｜上櫃歷史公布暫停/恢復交易股票｜參數 無
    #     /tpex_spendi_today  ｜上櫃當日公布暫停/恢復交易股票｜參數 無
    #   ⭐ 它是 TWSE `TWTAWU`（我方 `data/meta/suspend`）的**上櫃對應**，
    #   而我方那一半**完全沒有**。
    #
    # ⛔ 而「暫停／恢復交易」**不等於**「終止上櫃」——今天已經因為
    #   「名字很像就當成同一件事」摔過一次（`meta/suspend` 那張表叫
    #   「停止買賣」，實際上是短暫停牌後復牌，10,034 列裡 9,594 列是權證）。
    #   ⇒ 這支探針要回答的是「它到底是哪一種」，⛔ 不是「它就是我要的那個」。
    #
    # ⚠ `參數 無` ⇒ 很可能**沒有日期參數**（回全部或回今天）
    #   ⇒ ⭐ 要看它自己講不講得出涵蓋期間（第二點的判準）。
    ("⭐ 上櫃歷史暫停/恢復交易 openapi tpex_spendi_history",
     f"{TPX}/openapi/v1/tpex_spendi_history", {}),
    ("上櫃當日暫停/恢復交易 openapi tpex_spendi_today",
     f"{TPX}/openapi/v1/tpex_spendi_today", {}),
    # ⚠ 「終止上櫃」在 openapi 那 225 條裡**一條都沒有**（我方已掃過）。
    #   ⛔ 而那只證明**那一層**沒有——上櫃的減資、除權息歷史也都不在 swagger 裡，
    #   它們住在 `www/zh-tw/<path>` 那一層。⇒ 這裡放**兩條明示是猜的**候選，
    #   ⭐ 這支探針的用途就是**淘汰它們**；淘汰掉就把「請情報分析線掃 TPEx 選單」
    #   當成下一步，⛔ 不要再自己編路徑。
    ("終止上櫃？ www/zh-tw/bulletin/delist（⛔ 推的）",
     f"{TPX}/www/zh-tw/bulletin/delist?response=json", {}),
    ("終止上櫃？ www/zh-tw/company/suspendListing（⛔ 推的）",
     f"{TPX}/www/zh-tw/company/suspendListing?response=json", {}),
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
        "  ⭐ Q5 **K線線 16:40 §8 指名要的**：`TWT85U` 的 `**` 符號說明逐字是什麼？",
        "     ⚠ 他們整條「分盤撮合有兩個來源」的裁定建在這個符號上，",
        "     ⛔ 而目前的依據是一句**轉述**，不是官方 `notes` 的逐字。",
        "     ⇒ 若 `**` 其實是別的意思（例如「本日新增」），那條裁定要整條作廢。",
        "  ⭐⭐ Q7 `tpex_spendi_history` 到底是哪一種？（K線分析線 01:40 卡在這裡）",
        "     ⚠ 要分清楚：**短暫停牌後復牌**（＝TWSE 的 TWTAWU，我方 meta/suspend）",
        "     還是**長期停止買賣中**。⛔ 名字很像不算證據——今天已經摔過一次。",
        "     判準：① 權證佔幾成？② 有沒有『恢復日』欄？③ 未恢復的那些起日落在哪幾年？",
        "     （TWSE 那張：9,594/10,034 是權證、未復牌的 21 檔普通股全停在 2013~2014）",
        "  ⭐ Q8 它涵蓋到哪一年？`參數 無` ⇒ 它必須**自己講得出**涵蓋期間，",
        "     ⛔ 否則「回了很多列」不能當成「有歷史」（第二點）。",
        "  ⛔ Q9 那兩條「終止上櫃」是**明示推的**——這一趟就是要淘汰它們。",
        "     ⇒ 兩條都不通的話，下一步是**請情報分析線掃 TPEx 選單**",
        "     （他們掃 TWSE 280 條那次撿到四支新端點），⛔ 不要再自己編路徑。",
        "  ⭐ Q6 有沒有「信用交易標的名單」？（K線線 §3 的第三個成因，他們標【未查證】）",
        "     ⚠ 「本來就不是信用交易標的」是**中性**的，而 ①② 是**負面訊號**，",
        "     ⛔ 三者在資料上都長成「融資餘額 0」。",
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[delist_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
