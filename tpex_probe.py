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
import json
import os
import re
import sys

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_tpex_probe.txt")

SWAGGER = "https://www.tpex.org.tw/openapi/swagger.json"

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
    sys.exit(main())
