#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""suspend_twse.py — 上市**短期暫停交易**的完整歷史（TWSE `afterTrading/TWTAWU`）。

## 這一份是什麼、⛔ 不是什麼

**是**：上市證券的**短期**暫停交易紀錄，2015-03-30 起，7,215 筆／6,656 檔。
      每一筆有暫停日期／時間與恢復日期／時間。

⛔ **不是**「長期停止買賣」的來源。這一句是**實測**出來的，不是推測：

    停牌長度（恢復日 − 暫停日）n=7,182：最短 0｜p50 **1**｜p90 3｜p99 3｜最長 37 天
    其中 ≥ 30 天的只有 **1 筆（0.0%）**

而最乾淨的一個證據是 **4414 如興**：它 2022-08-17 ~ 2023-06-26 那段
203 個交易日的長期停止買賣**不在這裡**，但它在這個端點裡**有 3 筆**——
2018-02-26→27、2019-02-12→13、2019-12-10→11，全都是一天。

⇒ 所以不是「這檔沒被收錄」，是**這個端點的收錄範圍就是短期暫停**。
  ⭐ 這個分辨很重要：「整檔不在」要換來源，「有紀錄但兜不攏」要改自己的程式，
  **兩者的處置相反**，而只報「找不到」的話它們長得一模一樣。

## 為什麼還是要收

我方原有的 `data/meta/suspend.csv` 共 10,034 列，其中 **9,594 列是權證**，
普通股只有 409 列。也就是說**上市普通股的暫停交易，我方幾乎沒有紀錄**。
這一支補的就是那一塊，而且一次拿得到 11 年。

## ⚠ 端點的兩個坑（都是實測，⛔ 不要照別的端點的慣例推）

1. **`date=` 單日完全沒生效。** `date=20150701` 與 `date=20260909` 回**同一份**
   （都是 `期間：115/08/13 到 115/08/13`）。**只有 `startDate`/`endDate` 有效。**
2. `title` 會把**要求的區間**寫回來 ⇒ **對帳只能看 title**。
   （`sources/exright_incident.md`：`TWT49U` 就是回音沒對上，
    把 2026 的資料寫進 2015 的每一天。）
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

import backfill as B
import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "suspend_twse.csv")
HOLES = os.path.join(_ROOT, "meta", "_holes_scan.csv")

URL = ("https://www.twse.com.tw/rwd/zh/afterTrading/TWTAWU"
       "?startDate={a}&endDate={b}&response=json")
START = "20150101"
HEADER = ["stock_id", "name", "susp_date", "susp_time", "resume_date",
          "resume_time", "days"]


def roc_to_iso(v):
    """民國 115/08/13 → 2026-08-13。⛔ 認不出回 None，不猜。"""
    m = re.fullmatch(r"\s*(\d{2,3})/(\d{1,2})/(\d{1,2})\s*", str(v))
    if not m:
        return None
    y, mo, d = int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))
    if not (1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def title_range(title):
    """從 title 抽出「期間：104/01/01 到 115/09/09」的兩個日期。

    ⛔ 這是**唯一**能確認參數有生效的東西：回應裡沒有 startDate/endDate 欄，
      而 TWSE 有把參數原樣抄回去的前科。
    """
    m = re.search(r"期間[：:]\s*(\d{2,3}/\d{1,2}/\d{1,2})\s*到\s*"
                  r"(\d{2,3}/\d{1,2}/\d{1,2})", str(title))
    if not m:
        return None, None
    return roc_to_iso(m.group(1)), roc_to_iso(m.group(2))


def _diff_days(a, b):
    try:
        ad = date(*map(int, a.split("-")))
        bd = date(*map(int, b.split("-")))
        return (bd - ad).days
    except (ValueError, AttributeError):
        return None


def parse(raw):
    """→ (rows, title, err)。⛔ 欄位用名字找，不用位置——位置會變。"""
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        return [], "", f"不是 JSON：{ex}"
    tb = (B._tables(d) or [{}])[0]
    fields = [str(x) for x in (tb.get("fields") or [])]
    want = ("證券代號", "證券名稱", "暫停交易日期", "暫停交易時間",
            "恢復交易日期", "恢復交易時間")
    idx = {w: fields.index(w) for w in want if w in fields}
    if "證券代號" not in idx or "暫停交易日期" not in idx:
        return [], str(d.get("title") or ""), f"欄位對不上：{fields}"
    out = []
    for r in (tb.get("data") or []):
        r = list(r)
        def g(k):
            i = idx.get(k, -1)
            return str(r[i]).strip() if 0 <= i < len(r) else ""
        sid, s1 = g("證券代號"), roc_to_iso(g("暫停交易日期"))
        if not sid or not s1:
            continue
        s2 = roc_to_iso(g("恢復交易日期")) or ""
        out.append([sid, g("證券名稱"), s1, g("暫停交易時間"), s2,
                    g("恢復交易時間"),
                    str(_diff_days(s1, s2)) if s2 else ""])
    return out, str(d.get("title") or ""), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="離線用：讀一個檔當回應（selftest 用）")
    args = ap.parse_args()

    rl = runlog.Run("suspend_twse")
    today = datetime.now(TPE).strftime("%Y%m%d")
    today_iso = datetime.now(TPE).strftime("%Y-%m-%d")

    if args.json:
        raw, err = io.open(args.json, "rb").read(), None
    else:
        raw, err = B.get(URL.format(a=START, b=today), retries=3, timeout=90)
    if err or not raw:
        rl.info("端點", f"✗ 抓不到：{str(err)[:120]}")
        rl.check("抓得到 TWTAWU", False, str(err)[:90])
        return rl.finish()

    rows, title, perr = parse(raw)
    rl.info("回應", f"{len(raw):,} bytes｜title={title!r}｜解析出 {len(rows):,} 筆")
    if perr:
        rl.check("回應解析得出來", False, perr)
        return rl.finish()

    # ⭐ 唯一能確認參數有生效的檢查：title 裡的期間要對得上我要求的區間。
    #   ⛔ 回應裡沒有 startDate/endDate 欄，而 TWSE 有把參數原樣抄回去的前科
    #     （TWT49U 把 2026 的資料寫進 2015 的每一天）。
    t0, t1 = title_range(title)
    want0 = f"{START[:4]}-{START[4:6]}-{START[6:]}"
    rl.check("title 的期間對得上我要求的區間（⛔ 這是唯一能證明參數生效的東西）",
             t0 == want0 and t1 == today_iso,
             f"title 說 {t0} ~ {t1}｜我要的是 {want0} ~ {today_iso}")

    ids = {r[0] for r in rows}
    ds = sorted(r[2] for r in rows)
    rl.info("涵蓋", f"{len(rows):,} 筆／{len(ids):,} 檔｜暫停日 {ds[0]} ~ {ds[-1]}")

    # ⛔ 只增不減：這一支每趟整份重寫，寫短了就是資料掉了。
    old_n = 0
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            old_n = sum(1 for _ in csv.reader(f)) - 1
    rl.check("列數只增不減（整份重寫，寫短了就是掉資料）",
             len(rows) >= old_n, f"{old_n:,} → {len(rows):,}")
    if len(rows) < old_n:
        rl.info("處置", "✗ 比上一趟少 ⇒ **不寫檔**，保留舊的")
        return rl.finish()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in sorted(rows, key=lambda x: (x[2], x[0])):
            w.writerow(r)

    # ── 性質：⛔ 這一段要一直印，因為它是「這份不是長期停牌」的憑據 ──────
    dur = sorted(int(r[6]) for r in rows if r[6].lstrip("-").isdigit())
    if dur:
        def q(p):
            return dur[min(len(dur) - 1, int(len(dur) * p))]
        lng = sum(1 for x in dur if x >= 30)
        rl.info("停牌長度（恢復日−暫停日）",
                f"n={len(dur):,}｜最短 {dur[0]}｜p50 {q(.5)}｜p90 {q(.9)}"
                f"｜p99 {q(.99)}｜最長 {dur[-1]} 天｜"
                f"**≥30 天 {lng} 筆（{lng / len(dur) * 100:.1f}%）**")
        rl.note("⛔ 這一份是**短期暫停**，**不是長期停止買賣的來源**。"
                "最乾淨的證據：4414 如興 2022-08~2023-06 那段 203 個交易日"
                "不在這裡，而它在這個端點裡有 3 筆、全是一天 ⇒ "
                "不是「這檔沒收錄」，是**收錄範圍就是短期**。")

    # ── 它解釋得掉幾個長洞（⛔ 只報，不設 check）────────────────────
    #   ⛔ 不設 check 的理由：這一份本來就不是為了解釋長洞而存在的，
    #     拿「解釋率」當門檻會逼人把不相干的東西塞進來湊數。
    if os.path.exists(HOLES):
        by = {}
        for r in rows:
            by.setdefault(r[0], []).append(r[2])
        with io.open(HOLES, encoding="utf-8") as f:
            hs = [r for r in csv.DictReader(f) if r.get("market") == "twse"]
        hit = sum(1 for r in hs
                  if any(r["prev_date"] <= s <= r["date"]
                         for s in by.get(r["stock_id"], [])))
        rl.info("順帶：解釋得掉幾個上市長洞",
                f"{hit}／{len(hs)}（⛔ 只報不設門檻——這一份不是為了解長洞而存在的）")

    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
