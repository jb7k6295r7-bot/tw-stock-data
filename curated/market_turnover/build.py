#!/usr/bin/env python3
"""大盤每日成交量值（官方總額口徑）⇒ curated/market_turnover/
上市：TWSE FMTQIK（月一發；元；含大盤、零股、盤後定價、鉅額）1990-01 起
上櫃：TPEx tradingIndex（月一發；仟元／仟股；上櫃股票）2007-04 起
判準：stat OK、回應的月份＝查詢月份、每列日期都在該月、不同月內容不同；每發間隔 3.5 秒、一般 UA。"""
import csv, datetime, io, json, os, sys, time, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
def get(u):
    for i in range(3):
        try:
            time.sleep(3.5)
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8"))
        except Exception as e:
            print("  重試", i, u, e); time.sleep(20)
    raise RuntimeError(u)
def ad(roc):
    y, m, d = roc.split("/"); return "%04d-%02d-%02d" % (int(y) + 1911, int(m), int(d))
def num(x):
    return str(x).replace(",", "").strip()
def months(y0, m0):
    t = datetime.date.today(); y, m = y0, m0
    while (y, m) <= (t.year, t.month):
        yield y, m
        m += 1
        if m == 13: y, m = y + 1, 1
tw, tp, bad = [], [], []
prev = None
for y, m in months(1990, 1):
    j = get("https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=%04d%02d01&response=json" % (y, m))
    if j.get("stat") != "OK" or j.get("fields", [])[:3] != ["日期", "成交股數", "成交金額"]:
        bad.append(("twse", y, m, j.get("stat"))); continue
    rows = [[ad(r[0])] + [num(v) for v in r[1:]] for r in j.get("data") or []]
    if not rows or any(r[0][:7] != "%04d-%02d" % (y, m) for r in rows) or rows == prev:
        bad.append(("twse", y, m, "月份不符或與上月相同")); continue
    prev = rows; tw += rows
print("twse", len(tw), tw[0][0] if tw else None, tw[-1][0] if tw else None)
prev = None
for y, m in months(2007, 4):
    j = get("https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingIndex?date=%04d/%02d/01&response=json" % (y, m))
    t = (j.get("tables") or [{}])[0]
    rows = [[ad(r[0])] + [num(v) for v in r[1:]] for r in t.get("data") or []]
    if str(j.get("stat", "")).lower() != "ok" or not rows or any(r[0][:7] != "%04d-%02d" % (y, m) for r in rows) or rows == prev:
        bad.append(("tpex", y, m, j.get("stat"))); continue
    prev = rows; tp += rows
print("tpex", len(tp), tp[0][0] if tp else None, tp[-1][0] if tp else None)
os.makedirs(OUT, exist_ok=True)
with io.open(os.path.join(OUT, "twse_market_turnover.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n"); w.writerow(["date", "volume_shares", "amount_ntd", "transactions", "taiex", "change"]); w.writerows(tw)
with io.open(os.path.join(OUT, "tpex_market_turnover.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n"); w.writerow(["date", "volume_k", "amount_k_ntd", "transactions", "tpex_index", "change"]); w.writerows(tp)
print("bad", bad)
