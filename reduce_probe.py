#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reduce_probe.py — 找「減資恢復買賣參考價」的來源。

## 為什麼需要

`data/adj/` 的還原因子目前**只處理除權息**。
**減資的價格跳動動輒 30～50%**，現在會被當成真實漲跌——
任何跨過減資日的回測或長期報酬率都錯得離譜。這是資料庫目前最嚴重的錯法。

## 已知的兩條（2026-09-06 從開發環境實測）

| 來源 | 狀態 | 標題 | 欄位 |
|---|---|---|---|
| TPEx `bulletin/revivt` | ✓ 有回應 | 減資恢復買賣參考價 | 恢復買賣日期／股票代號／名稱／**最後交易日之收盤價格**／**減資恢復買賣開始日參考價格**／…／減資原因 |
| TWSE `change/TWTB8U` | ✓ stat=OK | **變更股票面額**恢復買賣參考價格 | 恢復買賣日期／股票代號／名稱／**停止買賣前收盤價格**／**恢復買賣參考價**／… |

**TWTB8U 是「變更面額」不是「減資」**，兩者是不同的公司行動。上市的減資表還沒找到。

## ★ 兩個結構問題，探測時要一起回答

1. **這些是前瞻式公告表**（TPEx 那張實測回未來十天），**不是逐日結果表**。
   若全部都是這種形狀，`feeds.py` 的逐日框架對它是錯的——
   要改成「定期抓一次、依事件自身日期累積」。
2. **有沒有歷史？** 公告表通常只有未來與近期。若拿不到歷史，
   **2015 年以來的減資事件就補不回來**，只能從現在起累積——
   那要在契約裡寫清楚，不能讓人以為 `data/adj/` 是完整的。
   FinMind 的資料集若能用，它吃 start_date/end_date，**是唯一可能有歷史的路**。

## 判準

每個候選都要回報：stat／標題／**完整欄位**／列數／**日期欄的最小與最大值**。
最後那一項最重要——**它直接回答「有沒有歷史」**，而不是靠猜。
"""

import argparse
import json
import re
import sys
import time

import backfill as B

TWSE = "https://www.twse.com.tw/rwd/zh/"
TPEX = "https://www.tpex.org.tw/www/zh-tw/"
FINMIND = "https://api.finmindtrade.com/api/v4/data?dataset="

# TWSE：`change/` 區段已證實存在（TWTB8U 通）。同區段的其他報表代碼逐一試。
TWSE_CODES = [f"TWTB{i}U" for i in range(1, 10)] + \
             [f"TWTA{c}U" for c in "STUVWXYZ"] + ["TWT88U", "TWT89U", "TWT90U"]
TWSE_SECTIONS = ["change", "exRight"]

TPEX_PATHS = ["bulletin/revivt", "bulletin/capitalReduction", "bulletin/reduction",
              "bulletin/resumeTrading", "afterTrading/revivt"]

FINMIND_SETS = ["TaiwanStockCapitalReductionReferencePrice",
                "TaiwanStockCapitalReduction",
                "TaiwanStockDividendResult"]

DATE_HINT = ("日期", "date", "Date")


def _get(url, retries=1):
    raw, err = B.get(url, retries=retries, timeout=45)
    if err:
        return None, err
    try:
        return json.loads(raw.decode("utf-8")), None
    except Exception as ex:                                   # noqa: BLE001
        head = raw[:100].decode("utf-8", "replace").replace("\n", " ")
        return None, f"非 JSON（{len(raw)}B）：{head}"


def _dates(fields, rows):
    """→ (欄名, 最小, 最大)。**這一項回答「有沒有歷史」，是本次探測的重點。**"""
    for i, f in enumerate(fields):
        if any(h in str(f) for h in DATE_HINT):
            vals = [str(r[i]).strip() for r in rows if len(r) > i and str(r[i]).strip()]
            if vals:
                return str(f), min(vals), max(vals)
    return "", "", ""


def show_twse(sec, code):
    url = f"{TWSE}{sec}/{code}?response=json"
    d, err = _get(url)
    if err or not isinstance(d, dict):
        return False
    stat = str(d.get("stat", "")).strip()
    if stat.lower() not in ("ok", "success"):
        return False
    for t in (B._tables(d) or [d]):
        f = [str(x) for x in (t.get("fields") or [])]
        rows = t.get("data") or []
        if not f:
            continue
        title = str(t.get("title") or d.get("title") or "")
        dk, lo, hi = _dates(f, rows)
        print(f"   ✓ change/{code}｜{title}")
        print(f"       {len(rows)} 列｜欄位={f}")
        if dk:
            print(f"       日期欄「{dk}」範圍 {lo} ~ {hi}"
                  f"{'  ← **可能有歷史**' if lo < '11400' and lo < '2025' else '  ← 只有近期／未來'}")
        if rows:
            print(f"       首列={rows[0]}")
    return True


def main():
    ap = argparse.ArgumentParser(description="找減資恢復買賣參考價的來源")
    ap.add_argument("--sleep", type=float, default=1)
    a = ap.parse_args()
    B.SLEEP = a.sleep

    print("── TWSE：掃 change／exRight 區段的報表代碼 ──")
    hit = 0
    for sec in TWSE_SECTIONS:
        for code in TWSE_CODES:
            if show_twse(sec, code):
                hit += 1
            time.sleep(a.sleep)
    print(f"   → {hit} 個代碼有回應\n")

    print("── TPEx：減資恢復買賣（開發環境 403，只有這裡驗得到）──")
    for p in TPEX_PATHS:
        for extra in ("", "&date=2026/09/06"):
            url = f"{TPEX}{p}?response=json{extra}"
            d, err = _get(url)
            short = p + (extra or "")
            if err:
                print(f"   ✗ {short}｜{err[:80]}")
                time.sleep(a.sleep)
                continue
            tabs = B._tables(d) if isinstance(d, dict) else []
            for t in (tabs or ([d] if isinstance(d, dict) else [])):
                f = [str(x) for x in (t.get("fields") or [])]
                rows = t.get("data") or []
                if not f:
                    continue
                dk, lo, hi = _dates(f, rows)
                print(f"   ✓ {short}｜{t.get('title') or ''}")
                print(f"       {len(rows)} 列｜欄位={f}")
                if dk:
                    print(f"       日期欄「{dk}」範圍 {lo} ~ {hi}")
                if rows:
                    print(f"       首列={rows[0]}")
            time.sleep(a.sleep)
    print()

    print("── FinMind：唯一可能有歷史的路（吃 start_date/end_date）──")
    for ds in FINMIND_SETS:
        for q in (f"{ds}&start_date=2015-01-01&end_date=2026-09-06",
                  f"{ds}&data_id=2330&start_date=2015-01-01&end_date=2026-09-06"):
            d, err = _get(FINMIND + q)
            short = q.split("&")[0] + ("（帶 data_id）" if "data_id" in q else "")
            if err:
                print(f"   ✗ {short}｜{err[:90]}")
                time.sleep(a.sleep)
                continue
            msg = d.get("msg") if isinstance(d, dict) else None
            data = d.get("data") if isinstance(d, dict) else None
            if not isinstance(data, list) or not data:
                print(f"   △ {short}｜msg={msg}｜data 空")
                time.sleep(a.sleep)
                continue
            ds_dates = [str(r.get("date", "")) for r in data if r.get("date")]
            print(f"   ✓ {short}｜msg={msg}｜{len(data):,} 筆")
            print(f"       欄位={list(data[0])}")
            if ds_dates:
                print(f"       date 範圍 {min(ds_dates)} ~ {max(ds_dates)}"
                      f"{'  ← **有歷史**' if min(ds_dates) < '2020' else ''}")
            print(f"       首筆={data[0]}")
            time.sleep(a.sleep)
    print("\n[probe] 重點不是「有沒有回應」，是**日期範圍**——"
          "那決定 2015 年以來的減資能不能補回來，還是只能從現在累積。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
