#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""永續合約資金費率【全期】落檔（C2 開跑前置，裁定線 20260924-2310 seq97 §三）。

  data/crypto_funding/<SYM>USDT.csv      逐月封存 zip 解開後串接
      表頭【逐字】calc_time,funding_interval_hours,last_funding_rate（⛔ 不改名、不換算）
  data/meta/crypto_funding_manifest.csv  一月一列：
      sym,month,url,zip_sha256,content_sha256,rows,interval_mix,status

⛔⛔ 為什麼不放 data/crypto/：那個目錄是 15 幣現貨日線，程式常用 data/crypto/*.csv 掃全部
   ⇒ 放進去會被當成第 16 個幣讀，⚠ 而且不報錯（裁定線 seq97 §三逐字的理由）。
⭐ 內容 sha 用【解開後】的位元組：zip 標頭帶時間戳 ⇒ 比 zip 會假紅（回測線 2259 實測過）。
⭐ 月份缺了就記 absent，⛔ 不補 0（absent 不是 0）。
⚠ 來源只走 data.binance.vision：fapi 從 Actions 回 451（crypto_probe 2026-09-20 付過代價）。
⚠ 只收【已完結】的月份：當月封存還沒發布 ⇒ 最後一個月 ＝ 上個月。
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

import runlog

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "crypto_funding")
MAN = os.path.join(HERE, "data", "meta", "crypto_funding_manifest.csv")
SYMS = ["BTC", "ETH", "XRP", "BNB", "DOGE", "SOL"]      # C2 的六幣
FIRST = (2020, 1)                                        # 封存下限（資料庫線 1857 實測）
HEADER = ["calc_time", "funding_interval_hours", "last_funding_rate"]
BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate/%sUSDT/%sUSDT-fundingRate-%04d-%02d.zip"
MAN_COLS = ["sym", "month", "url", "zip_sha256", "content_sha256", "rows", "interval_mix", "status"]


def months(until):
    y, m = FIRST
    while (y, m) <= until:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(url):
    """→ (位元組 或 None, 狀態字串)。404 ＝ absent；其他錯誤 ＝ error（⛔ 兩者不可混）。"""
    req = urllib.request.Request(url, headers={"User-Agent": "tw-stock-data crypto_funding"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, "absent"
            err = "HTTP %s" % e.code
        except (urllib.error.URLError, OSError) as e:
            err = str(e)[:80]
        time.sleep(2 * (i + 1))
    return None, "error: " + err


def parse_month(zbytes):
    """zip 位元組 → (rows, content 位元組)。⛔ 表頭不是逐字那三欄就丟 ValueError（不猜）。"""
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    names = [n for n in z.namelist() if n.endswith(".csv")]
    if len(names) != 1:
        raise ValueError("zip 裡的 csv 應為 1 個，實際 %r" % names)
    content = z.read(names[0])
    rows = list(csv.reader(io.StringIO(content.decode("utf-8"))))
    if not rows or rows[0] != HEADER:
        raise ValueError("表頭不是逐字 %r：%r" % (HEADER, rows[0] if rows else None))
    return rows[1:], content


def interval_mix(rows):
    c = {}
    for r in rows:
        c[r[1]] = c.get(r[1], 0) + 1
    return json.dumps({int(k) if k.isdigit() else k: v for k, v in sorted(c.items(), key=lambda x: -x[1])},
                      separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", help="YYYY-MM（預設：上個月）")
    ap.add_argument("--syms", nargs="*", default=SYMS)
    a = ap.parse_args()
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if a.until:
        until = tuple(int(x) for x in a.until.split("-"))
    else:
        until = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(MAN), exist_ok=True)
    # ⭐ 2026-09-25 補：第一版沒接 runlog ⇒ _last_run.md 沒有這一趟（三件式第③件落空，交件信自報過）
    rl = runlog.Run("crypto:funding")
    rl.info("這一趟", "C2 六幣永續資金費率全期（%s ~ %04d-%02d）" % ("%04d-%02d" % FIRST, until[0], until[1]))
    man = []
    errors = []
    for sym in a.syms:
        allrows = {}
        for y, m in months(until):
            url = BASE % (sym, sym, y, m)
            b, st = fetch(url)
            ym = "%04d-%02d" % (y, m)
            if st != "ok":
                man.append({"sym": sym, "month": ym, "url": url, "zip_sha256": "", "content_sha256": "",
                            "rows": 0, "interval_mix": "", "status": st})
                if st.startswith("error"):
                    errors.append((sym, ym, st))
                continue
            rows, content = parse_month(b)
            for r in rows:
                allrows[r[0]] = r        # calc_time 為鍵：月界重複只留一份
            man.append({"sym": sym, "month": ym, "url": url,
                        "zip_sha256": hashlib.sha256(b).hexdigest(),
                        "content_sha256": hashlib.sha256(content).hexdigest(),
                        "rows": len(rows), "interval_mix": interval_mix(rows), "status": "ok"})
            time.sleep(0.2)
        with io.open(os.path.join(OUT, sym + "USDT.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(HEADER)
            for k in sorted(allrows, key=int):
                w.writerow(allrows[k])
        ok = [x for x in man if x["sym"] == sym]
        first = min(allrows, key=int) if allrows else ""
        rl.info(sym, "%d 列｜ok %d 月｜absent %d 月｜error %d 月"
                % (len(allrows), sum(1 for x in ok if x["status"] == "ok"),
                   sum(1 for x in ok if x["status"] == "absent"),
                   sum(1 for x in ok if x["status"].startswith("error"))))
        print("%-4s %d 列｜月份 %d（ok %d／absent %d／error %d）｜第一筆 %s"
              % (sym, len(allrows), len(ok), sum(1 for x in ok if x["status"] == "ok"),
                 sum(1 for x in ok if x["status"] == "absent"),
                 sum(1 for x in ok if x["status"].startswith("error")),
                 datetime.datetime.fromtimestamp(int(first) / 1000, datetime.timezone.utc)
                 .strftime("%Y-%m-%d %H:%M UTC") if first else "—"))
    with io.open(MAN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MAN_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(man)
    # ⛔ 抓取錯誤 ≠ 官方沒有 ⇒ 大聲講，而且 rc≠0（manifest 照寫，status 欄有 error）
    rl.check("抓取錯誤 0 個月（⛔ error 不是 absent）", not errors, str(errors[:5]))
    rl.finish()
    if errors:
        print("⛔ 抓取錯誤 %d 個月：%s" % (len(errors), errors[:10]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
