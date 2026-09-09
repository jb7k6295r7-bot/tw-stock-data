#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tpex_probe.py — 把櫃買 OpenAPI 的**端點目錄**抓下來，不猜名字。

## 為什麼是「列目錄」而不是「試幾個網址」

`db_status.py` 還缺兩樣，兩樣都卡在同一件事——**不知道官方怎麼叫它**：

1. **上櫃的交易日曆從未被獨立驗證**。上市有 `FMTQIK`（大盤層級、與個股端點
   不同條路），上櫃沒有對應來源，所以 `calendar_twse.csv` 只涵蓋上市。
2. **上櫃類股 32、33 沒有中文名**。類股名稱取自 `MI_INDEX` 的標題，
   而它只涵蓋上市類股。

`tw-data-sources` 的坑第七條寫得很清楚：

> **「猜不到名字」不等於「這個東西不存在」。**
> 上櫃停牌猜了五個端點名全 404，就寫進文件說「沒有來源、永遠補不回來」。
> 實際上它在 `bulletin/sprcHis`，是 POST。
> **下結論說某個來源不存在之前，先打開官方頁面看它自己怎麼叫它。**

所以這一支不試候選網址，直接抓**官方自己的端點目錄**：

    https://www.tpex.org.tw/openapi/swagger.json

（網址來自 WebSearch 結果，非自行生成。）

## 為什麼要在 Actions 上跑

開發容器對 `tpex.org.tw` 直接讀是 403、WebFetch 也被 egress 擋。
那是環境差異，不是端點狀態——`feeds_prereg.md` 已寫死
**所有端點結論一律以 Actions 的 probe 為準**。

輸出寫進 `data/meta/_tpex_probe.txt` 進 repo，不必有人去翻 Actions log。
"""
import io
import csv
import io
import json
import os
import re
import sys
import traceback

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_tpex_probe.txt")

SWAGGER = "https://www.tpex.org.tw/openapi/swagger.json"

# ★ openapi 那一層**沒有任何端點吃日期參數**（2026-09-08 實測 225 個）。
#   但現行的上櫃日檔走的是**另一層**，而且吃日期：
#       https://www.tpex.org.tw/www/zh-tw/<path>?date=YYYY/MM/DD&response=json
#   otcinst（insti/dailyTrade）、otcper（afterTrading/peQryDate）、
#   otcmargin（margin/balance）三個都是這樣抓的。swagger 完全不涵蓋這一層。
#
#   ⛔ 但**頁面路徑不等於 API 路徑**——專案踩過：官方頁面
#   `announce/market/halt.html` 對應的 API 是 `bulletin/sprcHis`。
#   所以不從頁名回推，而是**把官方頁面抓下來，看它自己呼叫哪個網址**。
#   下面兩個頁面的報表名稱來自 WebSearch，不是自行生成：
PAGES = [
    ("日成交量值指數（上櫃大盤層級統計，交易日曆的候選）",
     "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_index/st41.php?l=zh-tw"),
    ("上櫃股價指數收盤行情（類股指數，類股名稱的候選）",
     "https://www.tpex.org.tw/web/stock/aftertrading/index_summary/summary.php?l=zh-tw"),
]

# 兩個缺口各自的關鍵字。**只用來排序、不用來過濾**——
# 全部端點都要列出來，不然就變成「用我猜的關鍵字去決定看得到什麼」。
WANT = {
    "日曆／大盤統計": ("index", "market", "summary", "statistic", "daily",
                       "trading", "指數", "大盤", "市場", "成交", "統計"),
    "類股名稱": ("industry", "sector", "category", "類股", "產業", "分類"),
}
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def main():
    say("── 櫃買 OpenAPI 端點目錄 ──")
    say(f"來源（WebSearch 結果，非自行生成）：{SWAGGER}")
    raw, err = B.get(SWAGGER, retries=2, timeout=90)
    if err:
        say(f"✗ 請求失敗：{err[:200]}")
        say("  ⚠ 開發容器對 tpex.org.tw 是 403（WebFetch 也被 egress 擋）——"
            "那是環境差異，端點結論一律以 Actions 為準。")
        return _write(1)
    say(f"✓ 取得 {len(raw):,} bytes")
    try:
        doc = json.loads(raw.decode("utf-8-sig", "replace"))
    except Exception as ex:                                      # noqa: BLE001
        say(f"✗ 不是合法 JSON：{type(ex).__name__}")
        say(f"  開頭：{raw[:200].decode('utf-8', 'replace')}")
        return _write(1)

    paths = doc.get("paths") or {}
    say(f"\n[1] 端點總數 {len(paths)}")
    if not paths:
        say("  ✗ swagger 裡沒有 paths——**格式可能改了，先看實際結構再下結論**")
        say(f"  頂層鍵：{list(doc)[:12]}")
        return _write(1)

    rows = []
    for p, ops in sorted(paths.items()):
        desc, params = "", []
        for m, op in (ops or {}).items():
            if not isinstance(op, dict):
                continue
            desc = desc or op.get("summary") or op.get("description") or ""
            for q in (op.get("parameters") or []):
                n = q.get("name") if isinstance(q, dict) else None
                if n:
                    params.append(n)
        rows.append((p, str(desc).strip().replace("\n", " ")[:70],
                     sorted(set(params))))

    # [2] 吃日期參數的端點——回補歷史的前提
    say("\n[2] ★ 吃日期參數的端點（能回補歷史的前提）")
    datey = [r for r in rows
             if any(re.search(r"date|day|ym|year|month|^d$", x, re.I) for x in r[2])]
    if datey:
        for p, d, q in datey:
            say(f"    {p}｜{d}｜參數 {q}")
    else:
        say("    （一個都沒有——那就代表 openapi 這一層只給當日，"
            "歷史要走別的路，不要硬湊）")

    # [3] 兩個缺口各自的候選。**全部端點都列在第 4 節**，這裡只是先排序。
    for label, kws in WANT.items():
        say(f"\n[3] 「{label}」的候選")
        hit = [r for r in rows
               if any(k.lower() in (r[0] + r[1]).lower() for k in kws)]
        for p, d, q in hit[:25]:
            say(f"    {p}｜{d}｜參數 {q or '無'}")
        if not hit:
            say("    （沒有命中——**這不代表沒有，代表我的關鍵字不對**，"
                "去看第 4 節的完整清單）")

    # [4] 完整清單。⛔ 一定要全印——只印關鍵字命中的，就是
    #     「用自己猜的字去決定看得到什麼」，坑第七條講的就是這個。
    say(f"\n[4] 完整端點清單（{len(rows)} 個）")
    for p, d, q in rows:
        say(f"    {p}｜{d}｜參數 {q or '無'}")

    # ── 第 5 節：從官方頁面挖出它自己呼叫的 API 路徑 ──
    say("\n[5] ★ 官方頁面自己呼叫的 API（openapi 之外那一層，吃日期）")
    for label, url in PAGES:
        say(f"\n  ── {label}")
        say(f"     {url}")
        raw2, err2 = B.get(url, retries=2, timeout=60)
        if err2:
            say(f"     ✗ 抓不到：{err2[:120]}")
            continue
        html = raw2.decode("utf-8", "replace")
        say(f"     ✓ {len(raw2):,} bytes")
        # 只抓 www/zh-tw 那一層與相對路徑寫法，兩種都收
        hits = set(re.findall(r"[\"'\(]([a-zA-Z0-9_/-]*www/zh-tw/[a-zA-Z0-9_/-]+)", html))
        hits |= set(re.findall(r"url\s*[:=]\s*[\"'\`]([^\"'\`]{4,120})", html))
        hits = {h for h in hits if "/" in h and not h.startswith("http")
                or "tpex.org.tw" in h}
        if hits:
            for h in sorted(hits)[:20]:
                say(f"       {h}")
        else:
            say("       （抓不到 API 路徑——頁面可能是 JS 動態組的，"
                "那就要看它載入的 .js）")
        js = set(re.findall(r"[\"'\(]([^\"'\(\)]+\.js)[\"'\)]", html))
        if js:
            say(f"     載入的 js（下一輪要看的）：{sorted(js)[:8]}")

    # ── [6] 上櫃類股 32、33 的中文名 ──
    #   端點名稱**取自上面第 4 節的官方目錄**，不是自己拼的。
    say("\n[6] ★ 上櫃類股名稱的候選端點（欄位與樣本列）")
    OPEN = "https://www.tpex.org.tw/openapi/v1/"
    for name, why in (
            ("mopsfin_t187ap05_OA", "二十九大類股營收變化統計表"),
            ("tpex_trading_volume_ratio", "上櫃歷史類股成交價量比重"),
            ("tpex_3insti_qfii_industry", "上櫃各類股僑外資及陸資持股比例表")):
        say(f"\n  ── /{name}｜{why}")
        r2, e2 = B.get(OPEN + name, retries=2, timeout=60)
        if e2:
            say(f"     ✗ {e2[:120]}")
            continue
        try:
            d2 = json.loads(r2.decode("utf-8-sig", "replace"))
        except Exception as ex:                                  # noqa: BLE001
            say(f"     ✗ 不是 JSON：{type(ex).__name__}｜開頭 "
                f"{r2[:80].decode('utf-8', 'replace')}")
            continue
        if isinstance(d2, dict):
            d2 = next((v for v in d2.values() if isinstance(v, list)), [])
        say(f"     ✓ {len(r2):,} bytes｜{len(d2)} 筆")
        if d2 and isinstance(d2[0], dict):
            say(f"     欄位：{list(d2[0])}")
            say(f"     首列：{d2[0]}")
            # 這些表的「類股」欄若同時有代碼與名稱，32/33 就解得開
            vals = set()
            for r3 in d2[:80]:
                for k, v in r3.items():
                    if any(w in k for w in ("類股", "產業", "業別", "Industry")):
                        vals.add(f"{k}={v}")
            if vals:
                say(f"     類股相關欄的值（前 12）：{sorted(vals)[:12]}")

    # ── [7] 上櫃「沒有中文名」的類股代碼，能不能靠官方的產業別欄對出來 ──
    #   ⚠ 這一節**只量、只報，不寫進 industry.csv**。
    #   交接清單有一條「不要用成員名單去猜名稱」——用成員反推名稱是**實測推定**，
    #   不是官方對照表。比照先前 DR 91 的處理：記錄下來，採不採用是情報分析的決定。
    say("\n[7] ★ 沒有中文名的上櫃類股代碼：拿官方產業別欄對對看（只量不寫）")
    IND = os.path.join(_ROOT, "meta", "industry.csv")
    rows = []
    try:
        with io.open(IND, encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("market") == "tpex"]
    except OSError as ex:                                        # noqa: BLE001
        say(f"  ✗ 讀不到 {IND}：{ex}")
        rows = []
    if rows:
        by_code = {}
        for r in rows:
            by_code.setdefault(r.get("industry_code", ""), []).append(r)
        # ⛔ 不寫死 32／33——從資料裡找「名稱是空的」那些代碼，
        #    以後多一個少一個都不必回來改這支。
        blank = sorted(c for c, rs in by_code.items()
                       if c and all(not r.get("industry_name") for r in rs))
        named = {c: rs[0]["industry_name"] for c, rs in by_code.items()
                 if c and rs[0].get("industry_name")}
        say(f"  industry.csv 的 tpex：{len(rows)} 檔／{len(by_code)} 個代碼；"
            f"名稱空白的代碼 {blank}（{[len(by_code[c]) for c in blank]} 檔）")

        r7, e7 = B.get(OPEN + "mopsfin_t187ap05_OA", retries=2, timeout=60)
        off = {}
        if e7:
            say(f"  ✗ 抓不到 mopsfin_t187ap05_OA：{e7[:120]}")
        else:
            try:
                d7 = json.loads(r7.decode("utf-8-sig", "replace"))
            except Exception as ex:                              # noqa: BLE001
                say(f"  ✗ 不是 JSON：{type(ex).__name__}")
                d7 = []
            if isinstance(d7, dict):
                d7 = next((v for v in d7.values() if isinstance(v, list)), [])
            for r3 in d7:
                if isinstance(r3, dict):
                    cid = str(r3.get("公司代號") or "").strip()
                    nm = str(r3.get("產業別") or "").strip()
                    if cid and nm:
                        off[cid] = nm
            say(f"  官方 mopsfin_t187ap05_OA：{len(d7)} 筆，"
                f"帶得出代號＋產業別的 {len(off)} 檔，"
                f"相異產業別 {len(set(off.values()))} 個")

        if off:
            # ★ 先在**已知答案**上驗這個方法對不對。
            #   若連有名稱的代碼都對不起來，32／33 的推定就不可信——
            #   這是唯一能讓推定站得住的非循環檢查。
            say("\n  ── 先驗方法：有中文名的代碼，官方產業別對不對得上 ──")
            agree = dis = nohit = 0
            bad = []
            for c in sorted(named):
                got = [off[r["stock_id"]] for r in by_code[c]
                       if r["stock_id"] in off]
                if not got:
                    nohit += 1
                    continue
                top = max(set(got), key=got.count)
                if top == named[c]:
                    agree += 1
                else:
                    dis += 1
                    bad.append(f"{c} 本庫「{named[c]}」／官方多數「{top}」"
                               f"（{got.count(top)}/{len(got)}）")
            say(f"     對得上 {agree}／對不上 {dis}／官方沒收到成員 {nohit}"
                f"（共 {len(named)} 個有名稱的代碼）")
            for b in bad[:10]:
                say(f"       ✗ {b}")
            # ★ 第二道，比對標籤字串更該問的：**分群一不一致**。
            #   ⚠ 本庫的 tpex 名稱是拿代碼去查**上市** MI_INDEX 的類股標題填的
            #     （`industry.py` 裡就一份 `names`，不分市場），所以上市與上櫃
            #     用字不同時，「標籤對不上」量到的是**用字**，不是分群錯。
            #   真正要問的是：官方的產業別欄，有沒有把同一個代碼的成員
            #   **全部**歸到同一格（不管那一格叫什麼），而且不同代碼不共用同一格。
            pure = mixed = 0
            share = {}
            for c in sorted(named):
                got = [off[r["stock_id"]] for r in by_code[c]
                       if r["stock_id"] in off]
                if not got:
                    continue
                if len(set(got)) == 1:
                    pure += 1
                    share.setdefault(got[0], []).append(c)
                else:
                    mixed += 1
            dup = {n: cs for n, cs in share.items() if len(cs) > 1}
            say(f"     ── 分群一致性（不看名稱，只看分組）──")
            say(f"        成員全歸到同一格的代碼 {pure}／被拆成多格的 {mixed}"
                f"／多個代碼共用同一格 {len(dup)}"
                + (f"：{dup}" if dup else ""))
            if mixed == 0 and not dup:
                say("        ⇒ 官方的分群與本庫的代碼**一一對應**。"
                    "此時標籤對不上只代表兩邊用字不同，不代表 join 錯。")
            trust = (dis == 0 and agree >= 10)
            if trust:
                say("     ⇒ 方法在已知答案上全中，下面對空白代碼的推定可信度較高。")
            else:
                say("     ⚠ 方法在已知答案上就有不合——下面的推定**一律不可採用**，"
                    "即使某個代碼看起來 1:1。")

            say("\n  ── 空白代碼的對照結果 ──")
            for c in blank:
                mem = by_code[c]
                got = [(r["stock_id"], off.get(r["stock_id"], "")) for r in mem]
                hit = [n for _, n in got if n]
                say(f"     代碼 {c}：{len(mem)} 檔，官方對到 {len(hit)} 檔")
                if not hit:
                    say("       （官方一檔都沒收到——這條路對這個代碼無效）")
                    continue
                cnt = {n: hit.count(n) for n in set(hit)}
                for n, k in sorted(cnt.items(), key=lambda x: -x[1]):
                    clash = [c2 for c2, n2 in named.items() if n2 == n]
                    tag = f"  ⚠ 這個名稱已經是代碼 {clash} 的" if clash else ""
                    say(f"       {n}：{k}/{len(hit)}{tag}")
                if len(cnt) == 1 and len(hit) == len(mem):
                    n = next(iter(cnt))
                    if any(n2 == n for n2 in named.values()):
                        say(f"       ⇒ 全部對到同一個名稱，但該名稱**已被別的代碼用掉**，"
                            f"不是 1:1，不可採用")
                    else:
                        say(f"       ⇒ {len(mem)}/{len(mem)} 全對到「{n}」，"
                            f"且沒有別的代碼在用 ⇒ 看起來是 1:1"
                            + ("" if trust else "，但**方法先驗沒過，仍不可採用**"))
                else:
                    say("       ⇒ 不是 1:1（有多個名稱或有成員對不到），不可採用")
            say("\n  ⛔ 以上一律**不寫進 industry.csv**：這是實測推定，不是官方對照表。"
                "要不要採用是市場情報分析的決定。")

    # ── [8] ★★ 使用者 2026-09-09 提供的四個頁面：面額變更那條路可能一直找錯層 ──
    #   ⚠ **先講一個我自己的敘述要更正的地方。**
    #     `_db_status.md` 寫著「TPEx swagger 225 個端點裡沒有減資／面額／參考價」。
    #     那句**是真的**，但它**證明不了「TPEx 沒有這個來源」**——
    #     因為我方每天在用的 `otcinst`／`otcper`／`otcmargin` 三條，
    #     **也一個都不在 swagger 裡**（它們住在 `www/zh-tw/<path>?date=…` 那一層）。
    #     ⇒ 「swagger 裡沒有」只說明**那一層**沒有。拿它當「不存在」，
    #       就是拿一層的缺席去推論全部——與「猜不到名字 ≠ 不存在」同一個形狀。
    #
    #   網址由使用者提供（**非自行生成**），照第 5 節的做法：
    #   ⛔ **不從頁名回推 API**，而是把頁面抓下來、看它自己呼叫哪個網址。
    say("\n[8] ★★ 面額變更／休市日：使用者提供的頁面（看它們自己呼叫什麼）")
    PAGES8 = [
        ("⭐ 變更面額**恢復買賣參考價**（上櫃那 14 筆缺的就是這個）",
         "https://www.tpex.org.tw/zh-tw/announce/market/change/reference.html"),
        ("變更股票面額**預告表**",
         "https://www.tpex.org.tw/zh-tw/announce/market/change.html"),
        ("採**彈性面額**之上（興）櫃公司名冊",
         "https://www.tpex.org.tw/zh-tw/mainboard/listed/flexible-face-value.html"),
    ]
    for why, url in PAGES8:
        say(f"\n  ── {why}")
        say(f"     {url}")
        r8, e8 = B.get(url, retries=2, timeout=60)
        if e8:
            say(f"     ✗ 抓不到：{str(e8)[:130]}")
            say("     ⛔ 抓不到**不等於不存在**——照實記，下一輪再試。")
            continue
        html = r8.decode("utf-8", "replace")
        say(f"     ✓ {len(r8):,} bytes")
        # 它自己呼叫哪些網址：相對路徑與絕對路徑都收
        hits = set(re.findall(r"[\"'\(]([a-zA-Z0-9_/.-]*(?:www|web)/zh-tw/[a-zA-Z0-9_/.-]+)",
                              html))
        hits |= set(re.findall(r"url\s*[:=]\s*[\"'`]([^\"'`]{4,140})", html))
        hits |= set(re.findall(r"[\"'\(](/[a-zA-Z0-9_/.-]{6,120}(?:\.php|\.json|Ajax|/data))",
                               html))
        hits = {h for h in hits if "/" in h}
        if hits:
            say(f"     它自己呼叫的候選網址（{len(hits)} 個，逐字）：")
            for h in sorted(hits)[:20]:
                say(f"       {h}")
        else:
            say("     （抓不到 API 路徑——頁面可能是 JS 動態組的，下一輪要看它載入的 .js）")
        js = sorted(set(re.findall(r"[\"'\(]([^\"'\(\)]+\.js)[\"'\)]", html)))
        if js:
            say(f"     載入的 js（下一輪要看的）：{js[:8]}")
        # 頁面上有沒有「日期」或「參考價」這種欄名，判斷值不值得接
        for kw in ("恢復買賣", "參考價", "停止買賣", "面額", "換發", "生效日"):
            n = html.count(kw)
            if n:
                say(f"       出現「{kw}」{n} 次")

    # ── [9] 上櫃交易日曆：官方休市日公告在哪 ──
    #   ⚠ 現況：上櫃日曆**沒有獨立外部判準**，是用我方日檔自我一致性驗的（0 天差異），
    #     但那只證明自洽。使用者 2026-09-09 指出正解是**對接官方休市日公告**。
    #   ⚠ 另外一件要講清楚的：颱風臨時休市**事後**在我方是抓得到的
    #     （日檔那天全市場沒有成交），真正缺的是**事前**——
    #     也就是「明天開不開盤」這種前瞻問題。⇒ 官方公告解的是前瞻那一半。
    #   ⛔ swagger 那 225 個端點裡沒有休市日（已查），所以要看頁面那一層。
    say("\n[9] 上櫃休市日公告（前瞻用；事後靠日檔就看得出來）")
    for why, url in (
            ("櫃買中心 休市日／交易日曆",
             "https://www.tpex.org.tw/zh-tw/announce/market/holiday.html"),
            ("櫃買中心 公告專區（找得到休市日的入口就好）",
             "https://www.tpex.org.tw/zh-tw/announce/market.html")):
        say(f"\n  ── {why}\n     {url}")
        r9, e9 = B.get(url, retries=1, timeout=60)
        if e9:
            say(f"     ✗ {str(e9)[:120]}　⛔ 抓不到不等於不存在")
            continue
        h9 = r9.decode("utf-8", "replace")
        say(f"     ✓ {len(r9):,} bytes｜出現「休市」{h9.count('休市')} 次"
            f"｜「開市」{h9.count('開市')} 次")
        for m in sorted(set(re.findall(r"[\"'\(]([a-zA-Z0-9_/.-]*holiday[a-zA-Z0-9_/.-]*)",
                                       h9, re.I)))[:10]:
            say(f"       {m}")

    say("\n── 下一步 ──")
    say("從第 2、4 節挑出真正的端點名，再寫抓取與驗算。")
    say("**沒有命中不等於不存在**——先看清單，不要回頭去猜網址。")
    return _write(0)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# tpex_probe.py 的輸出。這是端點目錄，不是資料。\n")
            f.write("# 來源：" + SWAGGER + "\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[tpex] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[tpex] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    # ⚠ 探針炸掉時，traceback 只留在 Actions log 裡——而 log 要翻好幾百行才找得到，
    #   （2026-09-09 實測：tail 900 行都還沒回到那一步）。
    #   ⇒ **把 traceback 寫進輸出檔**，它會跟著 commit 進 repo。
    #   這樣「哪一節炸的」下一趟就是既成事實，不必再去考古。
    #   ⛔ 覆蓋掉上一次成功的內容是**故意的**：這一份的語意是「這一趟看到什麼」，
    #     上一次的內容在 git 歷史裡找得到，而「看起來是完整結果、其實是上一趟的」
    #     比缺一份更貴。開頭那個 ✗ 也讓下一趟的重跑條件自動成立。
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                        # noqa: BLE001
        say("")
        say("✗ 這一趟在下面這裡炸掉了，以下是 traceback 原文（沒有整理）：")
        say(traceback.format_exc())
        _write(1)
        raise
