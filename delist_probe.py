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
import csv
import io
import json
import os
import re
import sys

import backfill as B
from twparse import roc_iso as _roc_iso

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
    # ⭐⭐ K線分析線 2026-09-11 02:10 報的**第二支終止上市名單**，⛔ 不同網域家族
    #   我方 `delisted.py` 用的是 www.twse.com.tw/rwd/zh/company/suspendListing（265 筆）
    #   他們用的是 openapi.twse.com.tw/v1/...（他們說「約 400 筆」）
    #   ⚠ 兩個數字不一致，⛔ 而在看到真回應之前**不可以宣稱哪一份完整**（第三點）。
    #   ⭐ 而他們自己也說那個數字不可信：同一份快取問三次回 397／400／155。
    #     ⇒ 他們的取得方式（WebFetch 摘要）**會靜默截斷**，
    #     ⛔ 而漏掉的正好是最新那一筆（2867 三商壽 2026-09-01，我方有、他們沒有）。
    #   ⇒ 這支探針要做的是**拿到原始陣列**，然後**雙向**跟我方 265 筆比（見 §compare）。
    ("⭐⭐ 終止上市（第二來源）openapi/v1/company/suspendListingCsvAndHtml",
     "https://openapi.twse.com.tw/v1/company/suspendListingCsvAndHtml", {}),
]


OURS = os.path.join(_ROOT, "meta", "delisted.csv")
_ROC = re.compile(r"^\d{2,3}[/-]\d{1,2}[/-]\d{1,2}$")
_CODE = re.compile(r"^[0-9A-Z]{4,6}$")


def _guess_keys(rows):
    """→ (date_key, code_key, why)。⛔ **看值的形狀**，不是看鍵名。

    ⚠ K線分析線給的鍵名（`Code`／`Company`／`DelistingDate`）是**WebFetch 轉述**的，
    ⛔ 而他們同一份快取問三次回三個不同的數字 ⇒ 那個轉述不算實測。
    ⇒ 這裡照值認：民國斜線日期認 date、四到六碼認 code。
    ⚠ 認不出來就**大聲說認不出來並且把鍵名印出來**，
    ⛔ 不是挑一個最像的硬上——挑錯的那一欄會整批靜靜錯位（今天已經摔過一次）。
    """
    d = [x for x in rows if isinstance(x, dict)]
    if not d:
        return None, None, "一列 dict 都沒有"
    keys = sorted({k for x in d for k in x})
    hit = {k: [0, 0] for k in keys}
    for x in d:
        for k in keys:
            v = str(x.get(k, "")).strip()
            if _ROC.match(v):
                hit[k][0] += 1
            if _CODE.match(v):
                hit[k][1] += 1
    n = len(d)
    dk = [k for k in keys if hit[k][0] >= n * 0.9]
    ck = [k for k in keys if hit[k][1] >= n * 0.9 and k not in dk]
    why = "｜".join(f"{k}: 像日期 {hit[k][0]}/{n}、像代號 {hit[k][1]}/{n}" for k in keys)
    if len(dk) != 1 or len(ck) != 1:
        return None, None, f"⛔ 認不出（日期候選 {dk}、代號候選 {ck}）｜{why}"
    return dk[0], ck[0], why


def _compare_with_ours(rows, out):
    """⭐ **雙向**跟我方 `delisted.csv` 比。⛔ 只比一個方向不算一致（第三點）。"""
    out.append("")
    out.append("   ══ 與我方 data/meta/delisted.csv 雙向比對 ══")
    if not os.path.exists(OURS):
        out.append(f"   ⚠ 我方那份不在這個 ref 上（{OURS}）"
                   "　⇒ ⛔ 這不是「我方沒有」，是 checkout 的問題（第四點六鏡像）")
        return
    ours = {}
    with io.open(OURS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ours[str(r.get("stock_id", "")).strip()] = str(r.get("delist_date", "")).strip()
    dk, ck, why = _guess_keys(rows)
    out.append(f"   鍵的形狀：{why}")
    if not dk:
        out.append("   ⛔ 認不出日期／代號欄 ⇒ **不比**（⚠ 硬挑一欄會整批錯位）")
        return
    out.append(f"   ⇒ 日期欄＝{dk!r}、代號欄＝{ck!r}（⭐ 照值認出來的，不是照鍵名）")
    theirs = {}
    for x in rows:
        if not isinstance(x, dict):
            continue
        c = str(x.get(ck, "")).strip()
        iso = _roc_iso(str(x.get(dk, "")).strip())
        if c:
            theirs[c] = iso or ""
    only_a = sorted(set(theirs) - set(ours))
    only_b = sorted(set(ours) - set(theirs))
    both = sorted(set(ours) & set(theirs))
    diff = [(c, ours[c], theirs[c]) for c in both if theirs[c] and ours[c] != theirs[c]]
    out.append(f"   我方 {len(ours)} 筆｜openapi {len(theirs)} 筆｜重疊 {len(both)}")
    out.append(f"   A 官方 openapi 有、我方**沒有**：{len(only_a)} 檔　{only_a[:20]}")
    out.append(f"   B 我方有、openapi **沒有**：{len(only_b)} 檔　{only_b[:20]}")
    # ⭐ 第七點：報「0 筆」要附該判準在該群抓到的正例數 ⇒ 重疊數就是它
    out.append(f"   ⭐ 重疊處日期**不一致**的：{len(diff)} 檔"
               f"（正例 {len(both)} 檔重疊）　{diff[:10]}")
    out.append("   ⇒ 判讀：A、B 兩邊都不是 0 ⇒ **這是兩張不同母體的表**，"
               "⛔ 不是誰漏了誰；只有一邊不是 0 才是「那一邊比較完整」")


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
    # ⛔ 這幾支可能**沒有 `tables`、也沒有 `fields`** ⇒ 四種形狀都要看得到
    # ⭐ 第四種：**頂層就是一個陣列**（openapi.twse.com.tw 那一族）
    #   ⚠ 它沒有 `stat`／`total`／`notes` 可以問 ⇒ ⛔ 第二點的「自己講出它是哪一期」
    #   這一支**做不到** ⇒ 完整性只能靠**跟另一份比**，不能靠它自己。
    if isinstance(d, list):
        out.append(f"   ⭐ 頂層就是**陣列**：{len(d)} 列"
                   f"（第一列型別 {type(d[0]).__name__ if d else '—'}）")
        if d and isinstance(d[0], dict):
            out.append(f"   ⭐ 鍵名（照真回應，⛔ 不是轉述）：{sorted(d[0])}")
            ks = {frozenset(x) for x in d if isinstance(x, dict)}
            out.append(f"   ⚠ 不同鍵組合的種類：{len(ks)}"
                       + ("　⛔ 超過 1 種 ⇒ 逐列取值不可以寫死鍵名" if len(ks) > 1 else ""))
        for r in d[:3]:
            out.append(f"     樣本：{json.dumps(r, ensure_ascii=False)[:220]}")
        _compare_with_ours(d, out)
        return
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
        "  ⭐⭐ Q10 **終止上市有兩支官方端點，數字不一樣**——哪一支是哪一張表？",
        "     我方 rwd/company/suspendListing：官方自己說 `total:265`，回到民國 090",
        "     K線分析線 openapi/v1/…CsvAndHtml：他們說「約 400」",
        "     ⚠ 而他們自己也說那個數字不可信（同一份快取問三次回 397／400／155）",
        "     ⇒ 這支探針的 §雙向比對 直接給 A／B 兩個方向的數字：",
        "       ⛔ **兩邊都不是 0 ⇒ 是兩張不同母體的表**（例如一張含終止興櫃／",
        "       終止公開發行），⛔ 不是誰漏了誰；只有一邊不是 0 才叫「那邊比較完整」",
        "     ⭐ 已知事實一枚：2867 三商壽（2026-09-01）**我方有**，",
        "       而他們的逐列輸出**沒有** ⇒ 他們的取得方式會靜默截斷尾巴，",
        "       ⚠ 而尾巴正是「最近下市的公司」＝最需要的那一段。",
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
