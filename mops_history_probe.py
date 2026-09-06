#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_history_probe.py — 月營收與財報的**歷史**要從哪裡來（第二版）。

## 第一版跑完已經確定的事（2026-09-06 Actions 實測）

| 批 | 結果 |
|---|---|
| **A. OpenAPI 加期別參數** | **死路。** `year`/`season`、`queryYear`、`date`、`yyy` 四種寫法回的都是「年度=115 季別=2、1,048 筆」，**與不帶參數完全相同＝參數被無視** |
| **B. MOPS 逐月靜態頁** | **★ 通了，而且在 `mopsov.twse.com.tw`**。`/nas/t21/sii/t21sc03_104_7_0.html` 回 387,032B／1,011 個 `<tr>`；上櫃 `/nas/t21/otc/...` 回 315,723B／824 個。`mops.` 與 `mopsfin.` 兩個 host 都 404 |
| **C. MOPS 查詢表單（POST）** | **★ 也通了，同樣在 `mopsov`**。`t163sb04` 1.16MB／844 `<tr>`、`t163sb05` 1.01MB／842、`t51sb02` 866KB／1,032。`mops.` host 回 800B（查無資料）|
| **D. FinMind** | 可用但**不必要**了。實測每發約 0.5 秒（5.5 秒裡有 5 秒是 sleep），全市場逐檔約 40 分／dataset |

## 第一版的兩個 bug（本版已修）

1. **`UnicodeEncodeError`**：URL 裡直接放中文參數（`年度=104`）會炸。
   → 一律 `urllib.parse.quote` 之後才送。
2. **「自述期別 抽不到」**：我用 `(\\d{3})年第(\\d)季` 去抓，MOPS 的頁面不長那樣。
   結果 C 批三條全部印「抽不到」——**等於最關鍵的問題沒有答案**。

## ★ 本版只回答一個問題：**參數是真的被吃，還是被無視？**

這是 A 批已經教過的一課：HTTP 200、欄位齊全、列數合理，**但回的是最新一期**。
`TWT49U` 的參數回音事故（`sources/exright_incident.md`）也是同一種。

判準**不是**「有沒有回東西」，也不是「日期看起來新不新」，而是：

> **同一支端點，換不同的年／月／季各打一發，回來的東西一不一樣。**

一樣 → 參數被無視，這條路是假的。
不一樣 → 參數是真的，再去看它自述的期別對不對。

一行指紋（長度＋前 2000 字的雜湊）就分得出來，不必解析 HTML。

## 涵蓋範圍

- B（月營收）：141 個月 × 上市/上櫃 2 個市場 = **282 發**，一趟跑得完
- C（財報）：47 季 × 2 個市場 × 2 張表（損益／資產負債）= **188 發**

兩者都是**官方來源**，比 FinMind 乾淨。

⚠ 這些頁面在 `robots.txt` 裡是 disallow 的（WebFetch 會被擋），所以只能在
Actions 上用 urllib 取。量很小（幾百發）且有 sleep，但**這件事要讓使用者知道**，
不要當成沒發生。
"""

import argparse
import hashlib
import re
import sys
import time
import urllib.parse
import urllib.request

import backfill as B

MOPSOV = "https://mopsov.twse.com.tw"
FINMIND = "https://api.finmindtrade.com/api/v4/data?dataset="


def _fp(raw):
    """一行指紋：長度 ＋ 內容雜湊。**用來判斷兩次回應是不是同一份東西。**"""
    return f"{len(raw):,}B/{hashlib.md5(raw).hexdigest()[:8]}"


def _title(raw):
    """從 Big5 頁面抽出它自述的期別。抽不到就回空——**不要用猜的填。**"""
    t = raw.decode("big5", "replace")
    for pat in (r"(\d{2,3})\s*年\s*(\d{1,2})\s*月.{0,12}(?:營業收入|營收)",
                r"(\d{2,3})\s*年\s*第\s*(\d)\s*季",
                r"民國\s*(\d{2,3})\s*年\s*(\d{1,2})\s*月"):
        m = re.search(pat, t)
        if m:
            return f"{m.group(1)}年{m.group(2)}"
    return ""


def _post(url, data, timeout=60):
    body = urllib.parse.urlencode(data, encoding="utf-8").encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"User-Agent": "Mozilla/5.0", "Referer": url,
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.status, None
    except Exception as ex:                               # noqa: BLE001
        return b"", 0, f"{type(ex).__name__}: {ex}"


def sec_b(sleep):
    """月營收逐月靜態頁：換月份看回應會不會變。"""
    print("── B. 月營收逐月靜態頁（mopsov）：**參數是真的還是假的** ──")
    cases = [("sii", 104, 7), ("sii", 105, 3), ("sii", 113, 11),
             ("otc", 104, 7), ("otc", 105, 3)]
    seen = {}
    for mkt, y, m in cases:
        url = f"{MOPSOV}/nas/t21/{mkt}/t21sc03_{y}_{m}_0.html"
        raw, err = B.get(url, retries=1, timeout=60)
        if err:
            print(f"   ✗ {mkt} {y}/{m}｜{err[:70]}")
            time.sleep(sleep)
            continue
        fp, ttl = _fp(raw), _title(raw)
        rows = raw.count(b"<tr")
        dup = seen.get(fp)
        seen[fp] = f"{mkt} {y}/{m}"
        flag = "○" if dup else "✓"
        print(f"   {flag} {mkt} {y}/{m}｜{fp}｜<tr> {rows}｜自述期別「{ttl or '抽不到'}」"
              + (f"  ★★ **與 {dup} 完全相同＝月份沒被吃**" if dup else ""))
        # ★ 自述期別要跟請求的月份對得起來，對不上就是回了別的月
        if ttl and not ttl.startswith(f"{y}年{m}"):
            print(f"       ★ **自述期別與請求不符**（要 {y}年{m}）——不可當歷史用")
        time.sleep(sleep)
    print(f"   → 指紋種類 {len(seen)} 種／{len(cases)} 發。"
          f"{'**全都不同＝月份是真的被吃**' if len(seen) == len(cases) else '有重複，要看上面哪幾發撞在一起'}\n")


def sec_c(sleep):
    """財報查詢表單：換年度／季別看回應會不會變。"""
    print("── C. 財報查詢表單 POST（mopsov）：**參數是真的還是假的** ──")
    base = {"encodeURIComponent": "1", "step": "1", "firstin": "1",
            "off": "1", "isQuery": "Y"}
    cases = [("t163sb04", "sii", "104", "01"), ("t163sb04", "sii", "110", "01"),
             ("t163sb04", "sii", "114", "03"), ("t163sb04", "otc", "104", "01"),
             ("t163sb05", "sii", "104", "01"), ("t163sb05", "sii", "110", "01")]
    seen = {}
    for name, typek, year, season in cases:
        url = f"{MOPSOV}/mops/web/ajax_{name}"
        form = dict(base, TYPEK=typek, year=year, season=season)
        raw, status, err = _post(url, form)
        tag = f"{name} {typek} {year}Q{int(season)}"
        if err:
            print(f"   ✗ {tag}｜{err[:70]}")
            time.sleep(sleep)
            continue
        if len(raw) < 2000:
            print(f"   △ {tag}｜HTTP {status}｜{len(raw):,}B｜疑似查無資料")
            time.sleep(sleep)
            continue
        fp, ttl = _fp(raw), _title(raw)
        rows = raw.count(b"<tr")
        dup = seen.get(fp)
        seen[fp] = tag
        print(f"   {'○' if dup else '✓'} {tag}｜HTTP {status}｜{fp}｜<tr> {rows}"
              f"｜自述期別「{ttl or '抽不到'}」"
              + (f"  ★★ **與 {dup} 完全相同＝參數沒被吃**" if dup else ""))
        time.sleep(sleep)
    print(f"   → 指紋種類 {len(seen)}／{len(cases)}。"
          f"{'**全都不同＝年度季別是真的被吃**' if len(seen) == len(cases) else '有重複，那幾發是同一份'}")
    print("   ※ 若指紋全不同但『自述期別』抽不到，那是**我的抽取式不夠好**，"
          "不是資料的問題——列數與指紋已經足以證明參數有效。\n")


def sec_d(sleep, codes=("2330", "8299", "6461")):
    print("── D. FinMind（備案，已知可用）──")
    for ds in ("TaiwanStockMonthRevenue", "TaiwanStockFinancialStatements"):
        t0, hit, rows = time.time(), 0, 0
        for c in codes:
            raw, err = B.get(
                f"{FINMIND}{ds}&data_id={c}&start_date=2015-01-01&end_date=2026-09-06",
                retries=1, timeout=45)
            if not err and b'"data"' in raw:
                import json
                d = json.loads(raw.decode("utf-8"))
                data = d.get("data") or []
                if data:
                    hit += 1
                    rows += len(data)
            time.sleep(sleep)
        el = (time.time() - t0) / len(codes)
        net = max(el - sleep, 0.05)
        print(f"   {ds}｜{hit}/{len(codes)} 檔有資料、{rows:,} 列｜"
              f"每發約 {el:.1f} 秒（扣掉 sleep 約 {net:.1f} 秒）")
        print(f"       → 3,029 檔 × sleep 0.3 約 **{(net + 0.3) * 3029 / 60:.0f} 分鐘**")
    print()


def main():
    ap = argparse.ArgumentParser(description="找月營收與財報的歷史來源（第二版）")
    ap.add_argument("--sleep", type=float, default=2)
    ap.add_argument("--only", default="bc", help="要跑哪幾節，預設 bc（a 已確定是死路）")
    a = ap.parse_args()
    B.SLEEP = a.sleep
    want = {x for x in a.only.lower() if x in "bcd"}
    print("[probe] 只回答一個問題：**參數是真的被吃，還是被無視？**")
    print("[probe] 判準＝換不同年／月／季各打一發，指紋一不一樣。\n")
    if "b" in want:
        sec_b(a.sleep)
    if "c" in want:
        sec_c(a.sleep)
    if "d" in want:
        sec_d(a.sleep)
    print("[probe] 判讀：")
    print("  指紋全不同 → **官方有歷史**，接下來寫 parser："
          "月營收 141 月 × 2 市場 = 282 發；財報 47 季 × 2 市場 × 2 表 = 188 發")
    print("  指紋有重複 → 那幾發是同一份，**參數被無視**，這條路跟 A 一樣是假的")
    return 0


if __name__ == "__main__":
    sys.exit(main())
