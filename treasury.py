#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""treasury.py — 上市櫃公司買回庫藏股（MOPS t35sc09「買回自己公司股份彙總統計表」）⇒ data/meta/treasury_buyback.csv

    python3 treasury.py [--d1 0890101] [--d2 <今年底，民國>]

## 為什麼（2026-09-28，裁定 seq259 §四：PREREG事件 庫藏股；資料庫優先序 庫藏股 ＞ 臺灣50）

一發（POST mopsov ajax_t35sc09，TYPEK＝sii／otc，董事會決議日區間）回全市場全部件數；2000-08 起有資料。

## ⛔ 讀法（裁定 seq259 §四 已定）

  ・沒有「公告日」欄，只有【董事會決議日】⇒ 事件日＝決議日
  ・「註銷」不是獨立的目的代碼（1 轉讓員工／2 股權轉換／3 維護公司信用及股東權益），只能從事後結果欄看 ⇒ 前視
  ・結果欄（是否執行完畢、已買回股數、註銷或轉讓股數、比例、金額、均價、未執行原因）是【今天的最終狀態】，
    ⛔ 不是公告當時 ⇒ 回測一律不用；照收只為對帳
## 驗證

  ・頁面自述「日期：089/01/01~115/12/31」要等於請求的區間
  ・序號要從 1 連到 N、不跳號（跳號＝表格解析掉列）
  ・每列 20 格；公司代號四到六碼
  ⚠ mopsov 的 robots.txt 是 disallow ⇒ 一市場一發、之間長間隔
"""
import argparse
import csv
import datetime
import html
import io
import os
import re
import sys
import time
import urllib.request

import runlog
from backfill import visible_text

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "meta", "treasury_buyback.csv")
URL = "https://mopsov.twse.com.tw/mops/web/ajax_t35sc09"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HEADER = ["market", "seq", "stock_id", "name", "board_date", "purpose", "amount_cap_twd", "planned_shares",
          "price_low", "price_high", "period_start", "period_end",
          "done_now", "threshold_note", "bought_shares_now", "cancelled_or_transferred_now", "ratio_pct_now",
          "amount_now_twd", "avg_price_now", "pct_of_issued_now", "not_done_reason_now"]


def roc(s):
    """「94/08/30」→「2005-08-30」；空或解不出回空字串（⛔ 不猜）。"""
    m = re.fullmatch(r"(\d{2,3})/(\d{1,2})/(\d{1,2})", (s or "").strip())
    if not m:
        return ""
    return "%04d-%02d-%02d" % (int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))


def parse(body, market, d1, d2):
    """→ (rows, note)。⛔ 自述區間不符、序號跳號、欄數不對 ⇒ 丟 ValueError（整份不收）。"""
    t = body.decode("utf-8", "replace")
    said = re.search(r"日期：\s*(\d{2,3}/\d{2}/\d{2})\s*~\s*(\d{2,3}/\d{2}/\d{2})", t)
    want = ("%s/%s/%s" % (d1[:-4], d1[-4:-2], d1[-2:]), "%s/%s/%s" % (d2[:-4], d2[-4:-2], d2[-2:]))
    if not said or (said.group(1).lstrip("0"), said.group(2).lstrip("0")) != (want[0].lstrip("0"), want[1].lstrip("0")):
        raise ValueError("%s 頁面自述區間 %r ≠ 請求 %r：%s" % (market, said.groups() if said else None, want,
                                                     visible_text(t, " ")[:300]))
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
        c = [html.unescape(visible_text(x, "")).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
        if len(c) != 20 or not c[0].isdigit() or not re.fullmatch(r"[0-9A-Z]{4,6}", c[1]):
            continue
        num = [x.replace(",", "") for x in c]
        rows.append([market, c[0], c[1], c[2], roc(c[3]), c[4], num[5], num[6], num[7], num[8], roc(c[9]), roc(c[10]),
                     c[11], c[12], num[13], num[14], num[15], num[16], num[17], num[18], c[19]])
    seqs = sorted(int(r[1]) for r in rows)
    if not seqs or seqs != list(range(1, len(seqs) + 1)):
        miss = sorted(set(range(1, (seqs[-1] if seqs else 0) + 1)) - set(seqs))
        raise ValueError("%s 序號不連續：%d 列、缺 %s" % (market, len(seqs), miss[:20]))
    return rows, "%s %d 件（序號 1～%d 連續）" % (market, len(rows), seqs[-1])


def fetch(market, d1, d2):
    body = ("encodeURIComponent=1&step=1&firstin=1&off=1&RD=1&TYPEK=%s&d1=%s&d2=%s" % (market, d1, d2)).encode()
    req = urllib.request.Request(URL, data=body, headers={"User-Agent": UA,
                                                          "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d1", default="0890101")
    ap.add_argument("--d2", default="%03d1231" % (datetime.date.today().year - 1911))
    ap.add_argument("--sleep", type=float, default=10)
    a = ap.parse_args()
    rl = runlog.Run("treasury")
    out, notes = [], []
    for mk in ("sii", "otc"):
        rows, note = parse(fetch(mk, a.d1, a.d2), mk, a.d1, a.d2)
        out += rows
        notes.append(note)
        time.sleep(a.sleep)
    out.sort(key=lambda r: (r[4], r[2], r[0], int(r[1])))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(out)
    ds = [r[4] for r in out if r[4]]
    rl.info("區間", "董事會決議日 %s ~ %s（民國 %s～%s）" % (min(ds), max(ds), a.d1, a.d2))
    rl.info("件數", "｜".join(notes) + "｜合計 %d" % len(out))
    rl.info("目的", str(sorted({(r[5], sum(1 for x in out if x[5] == r[5])) for r in out})))
    rl.note("⛔ *_now 欄是今天的最終狀態，⛔ 不是公告當時；事件日＝董事會決議日（沒有公告日欄）")
    rl.check("兩市都有件數", all(any(r[0] == m for r in out) for m in ("sii", "otc")), str(notes))
    rl.check("決議日都解得出", all(r[4] for r in out), str([r[:4] for r in out if not r[4]][:5]))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
