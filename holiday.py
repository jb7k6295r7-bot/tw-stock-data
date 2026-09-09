#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""holiday.py — 天然災害停止上班 ⇒ 台股全日休市。**前瞻那一半。**

## 這一支補的是交易日曆天生沒有的東西

`calendar_twse.csv` 是從**已經發生的成交**回推出來的，所以它永遠只知道過去。
颱風臨時休市在我方是**事後**才看得出來（那天全市場日檔沒有成交）。
「明天開不開盤」它答不了。

判準由使用者 2026-09-09 提供，原文：

    當**台北市**宣布停止上班時，台股及期貨市場將依規定
    天然災害停止上班之處理全日休市。

⛔ 是**台北市**這一個縣市，不是「有沒有任何縣市放假」。
  颱風天常常南部放假、北部照常，那種日子**台股照開**。

## ⭐ 探針量到什麼（`_holiday_probe.txt`，2026-09-09 於 Actions）

    [1] 15,035 bytes｜[2] 中文 862 字（內容在 HTML 裡，**不需要執行 js**）
    [3] 「臺北市」0 次、「台北市」0 次
    [4] 22 縣市一個都沒出現
    [6] 頁面自己的日期：115年9月9日／2026/09/09 ＝ **當天**
    [7] <table> 1 個、<tr> **3** 個、<td> **2** 個

⇒ 那天沒有颱風，而表格是**空的**。所以這個頁面是「**今天有公告的縣市**」，
  不是「所有縣市今天的狀態」。

## ⛔ 有一件事**今天無法驗證**，而整支程式是照著它設計的

我只看過**平安日**的樣子。**停班那一列長什麼樣，我沒有樣本。**
⇒ 所以判讀規則寫成**單向**的：

    預設 = 開盤。**只有正面比對到「台北市」+「停止上班」才標休市。**

這樣即使我對停班列的猜測是錯的，最壞情況是「颱風天沒偵測到」——
系統退回今天的狀態（事後才知道）。
⛔ 反過來寫（找不到就當休市）的最壞情況是**把正常交易日標成休市**，
  那會讓下游整天不抓資料，而且沒有人會發現。**兩種錯的代價不對稱。**

## ★ 而且今天就要開始存原始頁面

第一個颱風天才會有真正的樣本，而那一天**沒存就永遠沒有**
（跟集保只留一年、`capital.py` 每天把快照丟掉是同一件事）。
⇒ 每趟把原始 HTML 存進 `data/holiday/<西元日期>.html`。
  ⚠ 只在**頁面自己宣告的日期**與今天相同時才存——
    存到一份不知道是哪天的 HTML，比沒存更糟。
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import backfill as B
import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ARCH = os.path.join(_ROOT, "holiday")
OUT = os.path.join(_ROOT, "meta", "holiday_status.csv")
HEADER = ["date", "verdict", "taipei_hit", "page_date", "source", "checked_at"]
URL = "https://www.dgpa.gov.tw/typh/daily/nds.html"

# ⚠ 官方到底寫「臺」還是「台」不確定 ⇒ 兩個都收。
TAIPEI = ("臺北市", "台北市")
STOP = "停止上班"


def page_date(html):
    """→ 頁面自己宣告的西元日期（YYYY-MM-DD），抓不到回 None。

    ⛔ 不可以用「今天」代替它。用今天的話，頁面若卡在昨天的公告，
      我方會把昨天的狀態當成今天的——而且完全看不出來。
    """
    m = re.search(r"(20[0-9]{2})[-/]([0-9]{1,2})[-/]([0-9]{1,2})", html)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # 民國：「115年\n 9月\n 9日」——中間可能有換行與空白
    m = re.search(r"(1[0-9]{2})\s*年\s*([0-9]{1,2})\s*月\s*([0-9]{1,2})\s*日", html)
    if m:
        return (f"{int(m.group(1)) + 1911}-"
                f"{int(m.group(2)):02d}-{int(m.group(3)):02d}")
    return None


def taipei_stopped(html):
    """台北市那一列有沒有「停止上班」。→ (是不是, 命中的原文片段)。

    ⛔ 不是「整頁有沒有出現『停止上班』」——探針實測那四個字在**平安日**
      也出現 12 次（頁面自己的說明文字）。所以要**同一列**才算。
    ⇒ 以「台北市」出現的位置為中心取一段，只在那一段裡找。
    """
    for w in TAIPEI:
        for m in re.finditer(w, html):
            seg = html[m.start():m.start() + 400]
            seg = re.sub(r"<[^>]+>", " ", seg)
            if STOP in seg:
                return True, re.sub(r"\s+", " ", seg[:160]).strip()
    return False, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="改讀本機檔案（給測試用，不連外）")
    a = ap.parse_args()
    rl = runlog.Run("holiday")
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    now = datetime.now(TPE).isoformat(timespec="seconds")

    if a.html:
        html = io.open(a.html, encoding="utf-8", errors="replace").read()
        err = None
    else:
        raw, err = B.get(URL, retries=2, timeout=60)
        html = raw.decode("utf-8", "replace") if raw else ""

    if err or not html:
        # ⛔ 抓不到 ≠ 沒有停班。判定寫 unknown，**不可以寫成 open**。
        rl.info("抓取", f"✗ {str(err)[:120]}")
        rl.check("抓得到人事行政總處公告頁", False,
                 "⛔ 抓不到只代表我方不知道，**不代表今天照常開盤**")
        _append(today, "unknown", "", "", "fetch_failed", now)
        return rl.finish()

    pd = page_date(html)
    hit, seg = taipei_stopped(html)
    rl.info("頁面", f"{len(html):,} bytes｜頁面自己的日期 {pd or '（抓不到）'}")

    if pd != today:
        # 頁面沒更新到今天 ⇒ 我方**不知道**今天的狀態。
        verdict = "unknown"
        rl.info("判定", f"unknown（頁面日期 {pd} ≠ 今天 {today}）")
    else:
        verdict = "closed" if hit else "open"
        rl.info("判定", f"{verdict}"
                        + (f"｜命中：{seg}" if hit else "｜台北市沒有停止上班的公告"))

    # ⛔ 只在日期對得上時才存檔。存一份不知道是哪天的 HTML 比沒存更糟。
    if pd == today:
        try:
            os.makedirs(ARCH, exist_ok=True)
            p = os.path.join(ARCH, f"{today}.html")
            io.open(p, "w", encoding="utf-8").write(html)
            rl.info("原始頁面", f"存了 {os.path.relpath(p, os.path.dirname(ARCH))}")
        except OSError as ex:                                    # noqa: BLE001
            rl.info("原始頁面", f"✗ 存不了：{ex}")

    _schedule(rl, today)
    _append(today, verdict, "1" if hit else "0", pd or "", URL, now)
    # ⛔ 這裡**只檢查日期對不對得上**，不檢查「今天是不是休市」——
    #   後者沒有獨立判準可以驗，硬要驗就變成拿自己的產出驗自己。
    rl.check("頁面日期就是今天", pd == today,
             f"頁面 {pd}｜今天 {today}｜⇒ 判定寫成 unknown，"
             "⛔ 不可以當成照常開盤")
    return rl.finish()


SCHED_URL = ("https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule"
             "?response=json")
SCHED_CSV = os.path.join(_ROOT, "meta", "holiday_schedule.csv")


def _schedule(rl, today):
    """開休市行事曆：**前瞻那一半**，每年一份、逐年累積。

    ⚠ 端點只給**當年**：實測 `queryYear=2026`／`queryYear=115`／不帶參數
      三種回應**完全相同**（title 永遠是「115 年市場開休市日期」）
      ⇒ **拿不到明年的**。年底時最需要前瞻，而那正是它給不了的時候。
    ⇒ 所以每天抓、逐年存檔：今年的存下來，明年一月它換年之後就接得上。
      ⛔ 這跟集保只留一年是同一種「不存就永久失去」，只是週期是一年。
    """
    raw, err = B.get(SCHED_URL, retries=2, timeout=60)
    if err or not raw:
        rl.info("開休市行事曆", f"✗ 抓不到：{str(err)[:100]}")
        return
    # ⛔ 這裡**只接 ValueError**（＝真的不是 JSON）。
    #   2026-09-09 這一行原本是 `except Exception`，而 `json` 根本沒 import ⇒
    #   NameError 被接住、印成「✗ 不是 JSON：NameError」。
    #   **那句話是假的**：對方回的是好好的 JSON，壞的是我方的程式，
    #   而報告上看起來像對方的問題 ⇒ 去查對方，永遠查不到。
    #   ⇒ 我方自己的例外**不要接**，讓它炸出 traceback。
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        rl.info("開休市行事曆",
                f"✗ 對方回的**不是 JSON**：{type(ex).__name__}: {str(ex)[:80]}")
        return
    tb = (B._tables(d) or [{}])[0]
    fields = [str(x) for x in (tb.get("fields") or [])]
    data = tb.get("data") or []
    if not data:
        rl.info("開休市行事曆", f"✗ 回應沒有列（title={d.get('title')!r}）")
        return
    rows = {}
    if os.path.exists(SCHED_CSV):
        with io.open(SCHED_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("date"):
                    rows[r["date"]] = [r["date"], r.get("name", ""),
                                       r.get("note", ""), r.get("asof", "")]
    added = 0
    for r in data:
        r = list(r) + [""] * 3
        dt = str(r[0]).strip()
        if not re.match(r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}$", dt):
            continue
        if dt not in rows:
            added += 1
        # ⛔ 同一天重抓要覆蓋（公告會更正），但 asof 記下來，看得出是哪天抓的
        rows[dt] = [dt, str(r[1]).strip(), str(r[2]).strip(), today]
    try:
        os.makedirs(os.path.dirname(SCHED_CSV), exist_ok=True)
        with io.open(SCHED_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "name", "note", "asof"])
            for k in sorted(rows):
                w.writerow(rows[k])
    except OSError as ex:                                        # noqa: BLE001
        rl.info("開休市行事曆", f"✗ 寫檔失敗：{ex}")
        return
    ds = sorted(rows)
    ahead = [x for x in ds if x > today]
    rl.info("開休市行事曆",
            f"{d.get('title')!r}｜本趟 {len(data)} 列（新增 {added}）"
            f"｜累積 {len(rows)} 列 {ds[0]} ~ {ds[-1]}"
            f"｜**今天之後還有 {len(ahead)} 天**")
    rl.info("  欄位", str(fields))
    # ⛔ 不寫成 check：年底時「今天之後 0 天」是**正常**的（端點只給當年），
    #   拿它當錯誤會在每年 12 月底固定紅一次，然後大家學會忽略它。
    if not ahead:
        rl.info("  ⚠ 前瞻用盡",
                "今天之後沒有已知的休市日 ⇒ 端點多半還沒換年，"
                "⛔ 此時**不可以**把「不在清單裡」當成「開盤」")


def _append(date, verdict, hit, pd, src, now):
    """同一天重跑就覆蓋那一列，不要疊。"""
    rows = {}
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue
                p = line.rstrip("\n").split(",")
                if p and p[0]:
                    rows[p[0]] = p
    rows[date] = [date, verdict, hit, pd, src, now]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(HEADER) + "\n")
        for k in sorted(rows):
            f.write(",".join(rows[k]) + "\n")
    print(f"[holiday] 寫出 {OUT}（{len(rows)} 列）")


if __name__ == "__main__":
    sys.exit(main())
