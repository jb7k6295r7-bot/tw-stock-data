#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""單一上市證券（預設 0050）在全庫起點（2015-01-05）【之前】的日線＋還原因子 ⇒ data/extra/。

⭐ 為什麼有這一支（裁定線 20260925-0548 seq127 §二）：PREREGH 的 L＝36 閘門有 11 個月（2017-03～2018-01）
   因 0050 始於 2015 無法判 ⇒ 要 0050 的 2012-01～2014-12 日線（同 data/stocks 格式與還原口徑，官方來源）。
⛔⛔ 不寫 data/stocks/：那一族由 transpose.py 從 data/universe/daily 轉置產生，手寫會與全市場日檔無聲飄移
   （transpose.py 檔頭：「任何人都不可以直接編輯 data/stocks/」）
   ⇒ 另存 data/extra/<code>_<起>_<迄>.csv 與 data/extra/<code>_adj_<起>_<迄>.csv；
   ⛔ 全市場回補到 2015 以前是跨線的決定（seq142「只查、不落地」），⛔ 不是這一支的事。

來源（官方，⛔ 不走 FinMind）：
  日線  TWSE STOCK_DAY?date=YYYYMM01&stockNo=<code>（下限 2010-01-04，官方越界大聲回）
  事件  TWSE exRight/TWT49U?startDate=&endDate=（下限 2003-05-05）
還原因子：factor ＝ 除權息參考價 ÷ 除權息前收盤價；cum_factor ＝ factor × 【下一次事件】的 cum_factor
   ⇒ 接上 data/adj/<code>.csv 現有最早那一筆（2015-10-26 cum 0.17539226 ＝ 0.96965099 × 0.18088185，已驗）
"""
import argparse
import csv
import datetime
import io
import json
import os
import sys
import time
import urllib.request

import runlog

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (tw-stock-data etf_pre2015)", "Accept": "application/json"}
STOCK_COLS = ["date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount",
              "change", "limit", "shares", "transactions", "price_basis", "last_price", "valid_bar"]
from adjust import ADJ_HEADER as ADJ_COLS   # ⭐ 同一份表頭只留一份（CLAUDE.md 第四點五）


def get(url, tries=3, sleep=5.0):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                        # noqa: BLE001
            err = e
            time.sleep(sleep * (i + 1))
    raise SystemExit("⛔ 三次都取不到 %s：%s" % (url, err))


def num(s):
    s = str(s).replace(",", "").strip()
    return "" if s in ("", "--", "-", "X0.00") else s


def roc2iso(s):
    y, m, d = str(s).strip().split("/")
    return "%04d-%s-%s" % (int(y) + 1911, m, d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="0050")
    ap.add_argument("--start", default="2012-01")
    ap.add_argument("--end", default="2014-12")
    ap.add_argument("--sleep", type=float, default=5.0)
    a = ap.parse_args()
    rl = runlog.Run("etf_pre2015:%s" % a.code)
    out_dir = os.path.join(HERE, "data", "extra")
    os.makedirs(out_dir, exist_ok=True)
    tag = "%s_%s" % (a.start[:4], a.end[:4])

    # ── 日線
    y, m = int(a.start[:4]), int(a.start[5:7])
    ey, em = int(a.end[:4]), int(a.end[5:7])
    rows, months, name = [], 0, ""
    while (y, m) <= (ey, em):
        d = get("https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=%04d%02d01&stockNo=%s&response=json"
                % (y, m, a.code))
        if str(d.get("stat", "")).upper() != "OK":
            raise SystemExit("⛔ %04d-%02d stat=%r（⛔ 不跳過：跳過＝靜默少一個月）" % (y, m, d.get("stat")))
        f = d["fields"]
        want = ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"]
        if f[:9] != want:
            raise SystemExit("⛔ 欄位不是預期的 %r：%r" % (want, f))
        # 標題形如「101年01月 0050 元大台灣50       各日成交資訊」⇒ 取名稱
        name = name or " ".join(str(d.get("title", "")).split()[2:-1])
        for r in d["data"]:
            vol = num(r[1])
            rows.append([roc2iso(r[0]), a.code, name, "twse", num(r[3]), num(r[4]), num(r[5]), num(r[6]),
                         vol, num(r[2]), num(r[7]).replace("+", ""), "", "", num(r[8]), "", "",
                         "1" if vol not in ("", "0") else "0"])
        months += 1
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        time.sleep(a.sleep)
    rows.sort()
    p = os.path.join(out_dir, "%s_%s.csv" % (a.code, tag))
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(STOCK_COLS)
        w.writerows(rows)
    rl.info("日線", "%d 個月｜%d 列｜%s ~ %s｜名稱 %s" % (months, len(rows), rows[0][0], rows[-1][0], name))

    # ── 除權息事件
    d = get("https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate=%s01&endDate=%s31&response=json"
            % (a.start.replace("-", ""), a.end.replace("-", "")))
    if str(d.get("stat", "")).upper() != "OK":
        raise SystemExit("⛔ TWT49U stat=%r" % d.get("stat"))
    f = d["fields"]
    iD, iC, iP, iR, iK = (f.index("資料日期"), f.index("股票代號"), f.index("除權息前收盤價"),
                          f.index("除權息參考價"), f.index("權/息"))
    ev = []
    for r in d["data"]:
        if str(r[iC]).strip() != a.code:
            continue
        date = roc2iso(str(r[iD]).replace("年", "/").replace("月", "/").replace("日", "")) \
            if "年" in str(r[iD]) else roc2iso(r[iD])
        pre, ref = float(num(r[iP])), float(num(r[iR]))
        ev.append([date, ref / pre, pre, ref, str(r[iK]).strip()])
    ev.sort()
    # 接上現有 data/adj 最早一筆
    with io.open(os.path.join(HERE, "data", "adj", a.code + ".csv"), encoding="utf-8") as fh:
        existing = list(csv.DictReader(fh))
    nxt = float(existing[0]["cum_factor"])
    out = []
    for date, fac, pre, ref, kind in reversed(ev):
        cum = fac * nxt
        out.append([date, "%.8f" % fac, "", "%.8f" % cum, pre, ref, kind, "exright"])
        nxt = cum
    out.reverse()
    pa = os.path.join(out_dir, "%s_adj_%s.csv" % (a.code, tag))
    with io.open(pa, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(ADJ_COLS)
        w.writerows(out)
    rl.info("除權息", "%d 筆：%s｜接上 data/adj 最早 %s（cum %s）"
            % (len(out), "、".join(x[0] for x in out), existing[0]["date"], existing[0]["cum_factor"]))
    rl.check("日線月數 ＝ 要求的月數（⛔ 不可少一個月）",
             months == (ey - int(a.start[:4])) * 12 + em - int(a.start[5:7]) + 1, str(months))
    rl.finish()
    print("日線 %d 列（%s~%s）｜事件 %d 筆 ⇒ %s、%s" % (len(rows), rows[0][0], rows[-1][0], len(out), p, pa))
    return 0


if __name__ == "__main__":
    sys.exit(main())
