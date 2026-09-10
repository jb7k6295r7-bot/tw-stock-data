#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""delisted.py — 終止上市（下市）清單。⭐ 它解的是**生存者偏誤**。

    python3 delisted.py            # 抓 → 寫 data/meta/delisted.csv → runlog

## ⛔ 為什麼這件事重要

下市公司會從母體消失 ⇒ 母體只收「**現在還在的**」
⇒ 「2015 買、後來下市」那一段**整段不見**
⇒ ⭐ **回測績效會系統性偏樂觀**，而且**不會有任何一格數字出錯**——
  它錯在「那些應該賠錢的標的根本沒被算進來」。

265 筆裡有 2888 新光金、2867 三商壽、2809 京城銀、3682 亞太電。

## 端點（情報分析線 2026-09-10 16:25 掃 TWSE 選單 280 條撿到，我方實測過）

    GET /rwd/zh/company/suspendListing?response=json
    → status:"ok"（⛔ 不是 `stat`）、total:265、minYear 2001、maxYear 2026
    → 欄位 ['終止上市日期', '公司名稱', '上市編號']，列是 list
    → 樣本 ["115/09/01", "三商壽", "2867"]

⚠ **`yy` 參數被無視**（帶 `yy=115` 也回全部 265 筆，實測兩趟同數）
⇒ ⛔ 不要拿它驗年份，也不要以為可以逐年抓。

## ⭐ 這一支的價值不只是「多一個檔」

它讓 `data/meta/stocks.csv` 的 `last_seen` 有了**外部判準**：
我方 `last_seen` 應該 ≤ 官方終止上市日。
⚠ 反過來若我方 `last_seen` **晚於**官方終止上市日 ⇒ 那是我方寫進了不該有的列。

## ⛔ 這一支不碰 `stocks.csv`

那個檔的唯一寫入者是 `fetch.merge_stocks_meta`。這裡只寫自己的判準檔並出報告。
（換供料是**換維護者**的決定，不是順手加一行。）
"""
import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import backfill as B
import runlog
from twparse import roc_iso as _roc_iso

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "delisted.csv")
LOW = os.path.join(_ROOT, "meta", "_delisted_low.txt")
STOCKS = os.path.join(_ROOT, "meta", "stocks.csv")
URL = "https://www.twse.com.tw/rwd/zh/company/suspendListing?response=json"
HEADER = ["delist_date", "stock_id", "name", "asof"]
FIELDS = ["終止上市日期", "公司名稱", "上市編號"]


def parse(payload):
    """→ (rows, note)。⛔ 抽成函式是為了讓 selftest 測得到。"""
    if not isinstance(payload, dict):
        return [], f"回應不是 dict，是 {type(payload).__name__}"
    # ⛔ 這一支回的是 `status` 不是 `stat`（同一站第三種寫法）
    #   ⚠ 只檢查 `stat` 的話這裡永遠是 None ⇒ 等於沒檢查。
    st = str(payload.get("status") or payload.get("stat") or "").strip()
    if st and st.lower() not in ("ok", "success"):
        return [], f"⛔ 端點自己說失敗：status={st!r}"
    tabs = B._tables(payload)
    if not tabs:
        return [], f"沒有表；頂層鍵={sorted(payload)}"
    t = tabs[0]
    f = [str(x) for x in (t.get("fields") or [])]
    if f != FIELDS:
        return [], f"欄位結構與實測不符，拒收：{f}"
    data = t.get("data") or []
    if not data:
        return [], "回了 0 列 ⛔ 當失敗——這是一份累積清單，不可能是空的"
    asof = datetime.now(TPE).strftime("%Y-%m-%d")
    rows, bad = [], []
    for r in data:
        if not isinstance(r, list) or len(r) < 3:
            bad.append(str(r)[:60])
            continue
        d = _roc_iso(r[0])
        code = str(r[2]).strip()
        if not d or not code:
            bad.append(str(r)[:60])
            continue
        rows.append([d, code, str(r[1]).strip(), asof])
    rows.sort(key=lambda x: (x[0], x[1]))
    # ⭐ `total` 是官方自己說的列數 ⇒ 免費的完整性斷言
    total = payload.get("total")
    note = (f"官方 {len(data)} 列｜認得出 {len(rows)}"
            + (f"｜⛔ 認不出 {len(bad)}：{bad[:3]}" if bad else "")
            + (f"｜total={total}" if total is not None else "｜⚠ 沒有 total")
            + (f"｜涵蓋 {rows[0][0]} ~ {rows[-1][0]}" if rows else ""))
    return rows, note


def cross_check(rows, meta):
    """→ (兩邊都有的, 我方 last_seen **晚於**官方終止上市日的)。

    ⛔ 抽成函式是為了讓 selftest 測得到——這一段是這支程式真正的產出，
    ⚠ 而它埋在 main() 裡就只有「跑一趟正式抓取」才驗得到，
      而這個開發容器對交易所一律 403 ⇒ 等於永遠沒驗過。
    """
    both = [(r[1], r[0], (meta.get(r[1]) or {}).get("last_seen", "")) for r in rows
            if r[1] in meta]
    # ⚠ 我方 `last_seen` 應該 ≤ 官方終止上市日。
    #   ⛔ 反過來（我方晚於官方）代表我方寫進了**不該有的列**。
    return both, [x for x in both if x[2] and x[2] > x[1]]


def main():
    rl = runlog.Run("delisted")
    rl.info("端點", f"{URL}　⚠ `yy` 參數被無視（實測帶與不帶同為 265 筆）")
    raw, err = B.get(URL, retries=3, timeout=60)
    if err:
        rl.check("抓得到 suspendListing", False,
                 f"{str(err)[:140]}｜⛔ 抓不到不等於沒有下市公司"
                 "（開發容器對交易所一律 403，這一支要在 Actions 上跑）")
        return rl.finish()
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        rl.check("回應是 JSON", False, f"{ex}｜前 120：{raw[:120]!r}")
        return rl.finish()

    rows, note = parse(payload)
    rl.info("官方回的", note)
    rl.check("解得出列（⛔ 0 列當失敗，這是累積清單不可能是空的）", bool(rows), note)
    if not rows:
        return rl.finish()

    total = payload.get("total")
    rl.check("官方 total 與我方認出的列數一致",
             total is None or int(total) == len(rows),
             f"total={total}｜我方 {len(rows)}"
             + ("　⚠ 沒有 total 可比" if total is None else ""))

    # ⛔ 只進不出：這是一份**累積**清單，列數不可以變少
    low = None
    if os.path.exists(LOW):
        try:
            low = int(io.open(LOW, encoding="utf-8").read().split(",")[0])
        except (ValueError, IndexError):
            low = None
    rl.check("列數沒有比上一趟少（⛔ 下市是不可逆的，只會變多）",
             low is None or len(rows) >= low,
             f"上一趟 {low}｜本輪 {len(rows)}" if low is not None else "第一趟")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    try:
        io.open(LOW, "w", encoding="utf-8").write(
            f"{max(low or 0, len(rows))},{datetime.now(TPE).strftime('%Y-%m-%d')}\n")
    except OSError:
        pass
    rl.info("判準檔", f"data/meta/delisted.csv｜{len(rows)} 筆"
                      f"｜{rows[0][0]} ~ {rows[-1][0]}")

    # ══════════════════════════════════════════════════════════════
    # ⭐ 這一份的真正用途：給 `stocks.csv` 的 `last_seen` 一個**外部判準**
    # ══════════════════════════════════════════════════════════════
    meta = {}
    if os.path.exists(STOCKS):
        with io.open(STOCKS, encoding="utf-8") as f:
            meta = {r["stock_id"]: r for r in csv.DictReader(f)}
    both, after = cross_check(rows, meta)
    rl.info("⭐ 與 stocks.csv 對得起來的",
            f"{len(both)} 檔（官方 {len(rows)} 筆裡，我方 meta 也有的）")
    rl.check("⛔ 沒有任何一檔的 last_seen **晚於**官方終止上市日",
             not after,
             f"{len(after)} 檔：{[(c, o, l) for c, o, l in after[:5]]}"
             "　⇒ 那代表我方在下市之後還寫進了列" if after
             else f"{len(both)} 檔全部 last_seen ≤ 官方終止上市日")
    # ⚠ 只 info 不 check：母體本來就只收「進過母體的」，
    #   2015 之前就下市的當然不在 `stocks.csv` 裡——⛔ 那不是缺陷。
    rl.info("⚠ 官方有、我方 meta 沒有",
            f"{len(rows) - len(both)} 檔"
            "　（多半是我方涵蓋期（2015）之前就下市的 ⇒ ⛔ 不是缺陷）")
    rl.info("⛔ 這一支不碰 stocks.csv",
            "那個檔的唯一寫入者是 `fetch.merge_stocks_meta`。這裡只出判準。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
