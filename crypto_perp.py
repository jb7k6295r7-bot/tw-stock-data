#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""永續合約（USDⓈ-M）日 K 全期落檔（C5 永續價複核，裁定線 20260925-0443 seq124 §三）。

  data/crypto_perp/<SYM>USDT.csv       逐月封存 zip 解開後串接
      表頭：open_time,open,high,low,close,volume,close_time,quote_volume,count,
            taker_buy_volume,taker_buy_quote_volume,ignore（照 Binance 官方 klines 欄序）
  data/meta/crypto_perp_manifest.csv   一月一列：sym,month,url,zip_sha256,content_sha256,rows,had_header,status

⛔⛔ 不放 data/crypto/（同 crypto_funding：那個目錄常被整個掃 ⇒ 多一個「幣」而且不報錯）。
⚠ 舊的月檔【沒有表頭】、新的有（Binance 中途加的）⇒ 逐檔判斷，⛔ 不假設；manifest 記 had_header。
⭐ 內容 sha 用解開後的位元組；absent（官方 404）與 error（抓取錯）分開記，⛔ 不補。
⚠ 只收已完結月份（當月封存還沒發布）。
"""
import argparse
import csv
import datetime
import hashlib
import io
import os
import sys
import time
import zipfile

import runlog
from crypto_funding import SYMS, FIRST, months, fetch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "crypto_perp")
MAN = os.path.join(HERE, "data", "meta", "crypto_perp_manifest.csv")
HEADER = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
          "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
BASE = "https://data.binance.vision/data/futures/um/monthly/klines/%sUSDT/1d/%sUSDT-1d-%04d-%02d.zip"
MAN_COLS = ["sym", "month", "url", "zip_sha256", "content_sha256", "rows", "had_header", "status"]


def parse_month(zbytes):
    """→ (rows, content, had_header)。⛔ 欄數不是 12 或表頭不是逐字那 12 欄 ⇒ ValueError。"""
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    names = [n for n in z.namelist() if n.endswith(".csv")]
    if len(names) != 1:
        raise ValueError("zip 裡的 csv 應為 1 個，實際 %r" % names)
    content = z.read(names[0])
    rows = [r for r in csv.reader(io.StringIO(content.decode("utf-8"))) if r]
    if not rows:
        return [], content, False
    had = not rows[0][0].strip().isdigit()
    if had:
        if rows[0] != HEADER:
            raise ValueError("表頭不是逐字 %r：%r" % (HEADER, rows[0]))
        rows = rows[1:]
    bad = [r for r in rows if len(r) != 12]
    if bad:
        raise ValueError("有 %d 列欄數不是 12：%r" % (len(bad), bad[0]))
    return rows, content, had


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", help="YYYY-MM（預設：上個月）")
    ap.add_argument("--syms", nargs="*", default=SYMS)
    a = ap.parse_args()
    today = datetime.datetime.now(datetime.timezone.utc).date()
    until = (tuple(int(x) for x in a.until.split("-")) if a.until else
             ((today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)))
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(MAN), exist_ok=True)
    rl = runlog.Run("crypto:perp")
    rl.info("這一趟", "C5 永續日 K 全期（%04d-%02d ~ %04d-%02d）" % (FIRST[0], FIRST[1], until[0], until[1]))
    man, errors = [], []
    for sym in a.syms:
        allrows = {}
        for y, m in months(until):
            url = BASE % (sym, sym, y, m)
            b, st = fetch(url)
            ym = "%04d-%02d" % (y, m)
            if st != "ok":
                man.append({"sym": sym, "month": ym, "url": url, "zip_sha256": "", "content_sha256": "",
                            "rows": 0, "had_header": "", "status": st})
                if st.startswith("error"):
                    errors.append((sym, ym, st))
                continue
            rows, content, had = parse_month(b)
            for r in rows:
                allrows[r[0]] = r
            man.append({"sym": sym, "month": ym, "url": url, "zip_sha256": hashlib.sha256(b).hexdigest(),
                        "content_sha256": hashlib.sha256(content).hexdigest(), "rows": len(rows),
                        "had_header": int(had), "status": "ok"})
            time.sleep(0.2)
        with io.open(os.path.join(OUT, sym + "USDT.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(HEADER)
            for k in sorted(allrows, key=int):
                w.writerow(allrows[k])
        mine = [x for x in man if x["sym"] == sym]
        first = min(allrows, key=int) if allrows else ""
        msg = "%d 列｜ok %d 月｜absent %d｜error %d｜第一根 %s" % (
            len(allrows), sum(1 for x in mine if x["status"] == "ok"),
            sum(1 for x in mine if x["status"] == "absent"),
            sum(1 for x in mine if x["status"].startswith("error")),
            datetime.datetime.fromtimestamp(int(first) / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
            if first else "—")
        rl.info(sym, msg)
        print("%-4s %s" % (sym, msg))
    with io.open(MAN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MAN_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(man)
    rl.check("抓取錯誤 0 個月（⛔ error 不是 absent）", not errors, str(errors[:5]))
    rl.finish()
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
