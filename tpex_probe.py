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
        # ⛔ 2026-09-09 這一行製造了一個假命中，而我把它當成結論報出去了：
        #   原本結尾寫 `(?:\.php|\.json|Ajax|/data)`，其中 **`/data` 太鬆**——
        #   它把頁尾導覽列的 `/zh-tw/service/data/overview.html`（「資訊購買」，
        #   **每一頁都有的頁尾連結**）截成 `/zh-tw/service/data`，
        #   於是三個頁面「都命中同一條路徑」⇒ 我推論成「它們呼叫同一條 API」。
        #   **那不是 API，是頁尾連結。** 三頁都有，只因為那是共用頁尾。
        #   ⇒ 收緊：要嘛是明確的資料副檔名，要嘛帶查詢字串，⛔ 不再用 `/data` 結尾。
        hits |= set(re.findall(
            r"[\"'\(](/[a-zA-Z0-9_/.-]{6,120}(?:\.php|\.json|Ajax)\b[^\"'\)]{0,80})",
            html))
        hits = {h for h in hits if "/" in h}
        if hits:
            say(f"     它自己呼叫的候選網址（{len(hits)} 個，逐字）：")
            for h in sorted(hits)[:20]:
                say(f"       {h}")
        # ⛔ 2026-09-09 第 10 節白跑一趟的教訓：我去 `global.js` 找 `service/data`，
        #   結果那支 103 KB 的 js **一次都沒提到它**（出現 0 次）。
        #   而 `service/data` 是從**這個頁面的 HTML** 撈到的——
        #   ⇒ 參數多半就寫在頁面自己的 inline script 裡，我卻跑去別的檔找。
        #   **命中在哪就在哪裡看上下文**，不要跑去別的地方找。
        # ★ 這三頁**載入的 js 全是共用的**（jquery、gsap、global.js…），
        #   沒有頁面專屬的 js ⇒ 取資料那一段若不在 global.js，就在**inline script** 裡。
        #   ⛔ 不猜，把 inline script 裡像在組請求的片段**逐字**印出來。
        inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                            html, re.S | re.I)
        say(f"     inline script {len(inline)} 段")
        shown = 0
        for blk in inline:
            for m in re.finditer(r"ajax|\$\.get|\$\.post|fetch\s*\(|url\s*:", blk):
                a, b = max(0, m.start() - 200), min(len(blk), m.end() + 300)
                say("     ── inline script 裡像在組請求的地方（逐字）──")
                say("       " + blk[a:b].replace("\n", " ")[:520])
                shown += 1
                break
            if shown >= 4:
                break
        if not shown:
            say("     （inline script 裡沒有像在組請求的片段）")
        # ⚠ 2026-09-09 實測到這裡為止的三個否定：
        #     ① `service/data` 是頁尾連結，不是 API（我自己的假命中）
        #     ② 三頁載入的 8 支 js **全是共用的**，沒有頁面專屬的
        #     ③ inline script 裡**沒有**在組請求
        #   而 `global.js` 只有一個 `_get_json(func, url, input1, input2)` ——
        #   **url 是傳進去的參數**，端點由呼叫端決定，而呼叫端不在上面任何一處。
        #   ⇒ 剩下最可能的地方：**HTML 的 `data-*` 屬性**（SPA 常把端點放在那裡）。
        #   ⛔ 一樣不猜，全部逐字印出來。這一頁才 11 KB，`data-*` 不會多。
        das = sorted(set(re.findall(r'(data-[a-z0-9-]{2,30})\s*=\s*"([^"]{0,120})"',
                                    html)))
        say(f"     `data-*` 屬性 {len(das)} 種：")
        for k, v in das[:24]:
            say(f"       {k}={v!r}")
        # 任何看起來像「路徑＋查詢字串」的字串
        qs = sorted(set(re.findall(r'["\'(]([/a-zA-Z0-9_.-]{4,90}\?[a-zA-Z0-9_=&%.-]{2,90})',
                                   html)))
        if qs:
            say(f"     像「路徑＋查詢字串」的（{len(qs)} 個，逐字）：")
            for x in qs[:15]:
                say(f"       {x}")
        else:
            say("     （沒有任何帶查詢字串的路徑）")
        mods = re.findall(r'<script[^>]*type=["\']module["\'][^>]*>', html, re.I)
        if mods:
            say(f"     ⚠ 有 {len(mods)} 個 `<script type=module>`：{mods[:3]}")
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

    # ── [10] ★★★ 那三個頁面呼叫的**同一個** API：`/zh-tw/service/data` ──
    #   ⭐ 2026-09-09 第 8 節量到的最重要一件事：三個頁面（恢復買賣參考價／預告表／
    #     彈性面額名冊）**呼叫的是同一條路徑** `/zh-tw/service/data`。
    #     ⇒ 櫃買新站是「一條通用資料端點 ＋ 參數指定報表」的設計。
    #       這正是專案早就記過的那條——**頁面路徑不等於 API 路徑**。
    #   ⇒ 現在缺的只剩「參數怎麼帶」。那寫在他們自己的 js 裡。
    #   ⛔ 不猜參數名。把 js 抓下來，**把提到 `service/data` 的地方逐字印出來**。
    #   ⚠ 三個頁面都載入 `/cdn-cgi/challenge-platform/...` ＝ Cloudflare 挑戰，
    #     所以就算找到參數，端點本身仍可能需要 Cookie；那要下一輪才知道。
    say("\n[10] ★★★ 誰在讀 `data-format`／`data-start`（那一支就知道端點）")
    hit_any = {"n": 0}
    # ⭐ 2026-09-09 第 8 節量到的**真線索**：頁面的 `data-*` 帶的是**參數**，不是端點——
    #     data-format='D' / 'csv' / 'print'　　data-start='20190909'
    #   `data-start` 是個**日期**（2019-09-09，看起來是查詢區間的預設起點）。
    #   ⇒ 端點不在 HTML 裡，但**讀這些屬性的那段 js 一定知道端點**。
    #   所以這一節改成：把三頁載入的 **8 支 js 全部**掃一遍，找誰在讀 `data-format`／`data-start`。
    #   ⛔ 這不是「再繞一圈」——是照剛量到的參數名去找它的使用者，範圍是封閉的 8 支。
    #   ⚠ 若 8 支**沒有一支**提到它們 ⇒ 處理那些屬性的 js 不在載入清單裡
    #     ⇒ **不執行 js 就走不通**，到那裡就停，不再找。
    BASEW = "https://www.tpex.org.tw"
    JS = ["/rsrc/asset/js/global.js",
          "/rsrc/asset/js/jquery.simplePagination.js",
          "/rsrc/asset/js/jquery.session.js",
          "/rsrc/asset/js/jquery.cookie.min.js",
          "/rsrc/asset/js/jquery.mousewheel.min.js",
          "/rsrc/asset/js/gsap.min.js",
          "/rsrc/asset/js/jquery-3.7.1.min.js"]
    for jp in JS:
        say(f"\n  ── {BASEW}{jp}")
        rj, ej = B.get(BASEW + jp, retries=2, timeout=60)
        if ej:
            say(f"     ✗ {str(ej)[:130]}　⛔ 抓不到不等於不存在")
            continue
        t = rj.decode("utf-8", "replace")
        # ⛔ 上一版在這裡找 `service/data`，出現 **0 次**——因為那根本不是 API 路徑
        #   （見第 8 節的更正：那是頁尾連結）。改成找**它怎麼組請求**。
        # ★ 判準：誰讀 `data-format`／`data-start`，誰就知道端點。
        keys = ["data-format", "data-start", "'format'", '"format"',
                "'start'", '"start"']
        found = {k: t.count(k) for k in keys if t.count(k)}
        say(f"     ✓ {len(rj):,} bytes｜`ajax(` {len(re.findall(r'ajax *[(:]', t))} 處"
            f"｜命中的參數名：{found or '（一個都沒有）'}")
        hit_any["n"] += sum(found.values())
        for k in ("data-format", "data-start"):
            for m in list(re.finditer(re.escape(k), t))[:2]:
                a, b = max(0, m.start() - 260), min(len(t), m.end() + 360)
                say(f"     ── `{k}` 的上下文（逐字，不整理）──")
                say("       " + t[a:b].replace("\n", " ")[:600])
        # 常見的參數名長相：`tables`、`response`、`date`、`type`…
        keys = sorted(set(re.findall(r"[\"'\{,]\s*([a-zA-Z_][a-zA-Z0-9_]{2,20})\s*:", t)))
        hit = [k for k in keys if re.search(
            r"date|type|table|resp|name|param|id|market|year|month", k, re.I)]
        if hit:
            say(f"     js 裡像參數名的鍵（{len(hit)} 個）：{hit[:30]}")

    if hit_any["n"] == 0:
        say("\n  ⛔ **八支 js 沒有一支提到 `data-format`／`data-start`。**")
        say("     ⇒ 處理那些屬性的程式**不在頁面載入的 js 清單裡**"
            "（可能是打包進別的檔、或執行時才注入）。")
        say("     ⇒ **在不執行 js 的前提下，這條路走不通。** 到這裡停，不再找。")
        say("     ⚠ 這是「我方取不到」，⛔ **不是「櫃買沒有這個端點」**——"
            "三個官方頁面都在、關鍵字也對得上。")
    else:
        say(f"\n  ★ 有 {hit_any['n']} 處命中 ⇒ 照上面的上下文找端點，⛔ 仍然不要猜參數名。")

    # ─────────────────────────────────────────────────────────────────
    say("\n[11] ★★★ 32／33 的中文名：ISIN 證券編碼查詢（使用者 2026-09-09 提供）")
    # ⛔ 網址由使用者提供，**不是自行生成**。它吃 `industry_code` 參數，
    #   而那正是我方一直缺名稱的那個欄位。
    # ★ 這個缺口今天變大了：上櫃 30 檔 ＋ 興櫃 11 檔，**兩邊是同一個缺口**。
    # ⚠ 判準寫在前面，⛔ 不是「有回東西就算找到」：
    #   ① 32 與 33 要回**不同**的公司清單（一樣就代表參數沒生效）
    #   ② 回來的代號要**真的落在我方標為 32／33 的那批裡**
    #   ③ 名稱要能從頁面上讀到，⛔ 讀不到就寫「查詢頁沒有寫名稱」，不要從清單去猜
    ISIN = ("https://isin.twse.com.tw/isin/class_main.jsp"
            "?owncode=&stockname=&isincode=&market=&issuetype="
            "&industry_code={}&Page=1&chklike=Y")
    # 我方標成 32／33 的代號，拿來做 ② 的比對靶
    mine = {"32": set(), "33": set()}
    # ⚠ `IND` 是第 7 節裡的區域變數，這裡不能用 ⇒ 重新組一次路徑。
    IND2 = os.path.join(_ROOT, "meta", "industry.csv")
    try:
        with io.open(IND2, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                c = (r.get("industry_code") or "").strip()
                if c in mine:
                    mine[c].add(r["stock_id"])
    except OSError:
        pass
    try:
        with io.open(os.path.join(_ROOT, "meta", "industry_esb.csv"),
                     encoding="utf-8") as f:
            for r in csv.DictReader(f):
                c = (r.get("industry_code") or "").strip()
                if c in mine:
                    mine[c].add(r["stock_id"])
    except OSError:
        pass
    say(f"  我方標成 32 的 {len(mine['32'])} 檔｜33 的 {len(mine['33'])} 檔"
        "（上市櫃＋興櫃合計）")
    got = {}
    for code in ("32", "33"):
        u = ISIN.format(code)
        say(f"\n  ── industry_code={code}")
        r11, e11 = B.get(u, retries=2, timeout=60)
        if e11:
            say(f"     ✗ {str(e11)[:140]}")
            continue
        # ⚠ 這個站是 Big5 系列的老頁面，⛔ 不要預設 utf-8
        t11 = None
        for enc in ("big5", "cp950", "utf-8"):
            try:
                t11 = r11.decode(enc)
                say(f"     ✓ {len(r11):,} bytes｜編碼 {enc}")
                break
            except UnicodeDecodeError:
                continue
        if t11 is None:
            t11 = r11.decode("utf-8", "replace")
            say(f"     ✓ {len(r11):,} bytes｜⚠ 三種編碼都不乾淨，用 replace")
        # 代號：四碼數字（可能帶英文字尾）
        ids = sorted(set(re.findall(r"<td[^>]*>\s*([0-9]{4}[A-Z]?)\s*</td>", t11)))
        got[code] = set(ids)
        say(f"     抓到證券代號 {len(ids)} 個：{ids[:12]}")
        inter = got[code] & mine[code]
        say(f"     ② 與我方標成 {code} 的交集：{len(inter)}／我方 {len(mine[code])}"
            + ("　← ✓ 對得上" if inter else "　← ⛔ **一個都對不上，參數可能沒生效**"))
        # ③ 名稱：頁面上有沒有寫這個代碼叫什麼
        plain = re.sub(r"<[^>]+>", " ", t11)
        plain = re.sub(r"\s+", " ", plain)
        near = [plain[max(0, m.start() - 60):m.start() + 60]
                for m in re.finditer(r"產業別|類別|industry", plain)][:4]
        say(f"     ③ 「產業別／類別」附近逐字：{near or '（沒有）'}")
    if "32" in got and "33" in got:
        same = got["32"] == got["33"]
        say(f"\n  ① 32 與 33 的清單{'**完全一樣 ⇒ 參數沒生效**' if same else '不同 ⇒ 參數有生效'}"
            f"（32 有 {len(got['32'])} 檔、33 有 {len(got['33'])} 檔、"
            f"交集 {len(got['32'] & got['33'])} 檔）")
    say("  ⇒ ⛔ 三項判準沒有全過，就不要把任何名稱寫進 `sectors.csv`。")

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
