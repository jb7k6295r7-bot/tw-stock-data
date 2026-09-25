#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""早年段（全庫起點 2015-01-05 之前）的全市場日 K ⇒ data/early/daily/<日期>.csv（裁定線 seq149 §二 ①②）。

⭐ 重用，⛔ 不另寫：抓取／驗日期／解析／寫檔全走既有的 backfill.fetch_day_market 與 fetch.write_universe_day，
   只把 fetch.UNI_DIR 指到 data/early ⇒ 輸出格式與 data/universe/daily 逐欄相同（17 欄）。
   ⭐ 2026-09-25 實測：既有解析器吃得下早年格式（上市 2004／2008／2012、上櫃 2007／2010 都解出 17 欄）。
⛔⛔ 放 data/early/，⛔ 不併進 data/universe、data/stocks（seq149：避免主窗程式不小心讀到）。
⛔⛔ 驗收段守則：本支【只做結構驗證】—— 列數、日期集合、low ≤ open,close ≤ high、零價、負價
   ⭐ 唯一的改值：早年上櫃「無成交」寫成 0.00 ⇒ 改成主庫慣例的空白（見 blank_notrade）
   ⛔ 不算任何報酬、漲跌幅分布（驗收段要保持沒看過）。

官方下限（本線 2026-09-25 實測，信 1423）：上市 MI_INDEX 2004-02-11；上櫃 afterTrading/otc 2007-07-02。
交易日：上市走 TWSE FMTQIK 逐月、上櫃走 TPEx tradingIndex 逐月（⛔ 0 列＋ok 有兩義 ⇒ 只在交易日上問）。
可續跑：該日檔已有該市場的列就跳過。
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backfill as B
import fetch as F
import runlog

EARLY = os.path.join(HERE, "data", "early")
UA = {"User-Agent": "Mozilla/5.0 (tw-stock-data early_backfill)", "Accept": "application/json"}
FLOOR = {"twse": "2004-02-11", "tpex": "2007-07-02"}


def _json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def trading_days(market, start, end, sleep):
    """官方月表 → 交易日（西元）。⛔ 取不到的月份大聲停，⛔ 不猜。"""
    y, m = int(start[:4]), int(start[5:7])
    out = []
    while (y, m) <= (int(end[:4]), int(end[5:7])):
        if market == "twse":
            d = _json("https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=%04d%02d01&response=json" % (y, m))
            rows = d.get("data") or []
        else:
            d = _json("https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingIndex?date=%03d/%02d&response=json"
                      % (y - 1911, m))
            rows = [r for t in (d.get("tables") or []) for r in (t.get("data") or [])]
        if str(d.get("stat", "")).lower() != "ok" or not rows:
            raise SystemExit("⛔ %s %04d-%02d 交易日表取不到（stat=%r、%d 列）⇒ ⛔ 不猜" % (market, y, m, d.get("stat"), len(rows)))
        for r in rows:
            yy, mm, dd = str(r[0]).strip().split("/")
            out.append("%04d-%s-%s" % (int(yy) + 1911, mm, dd))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        time.sleep(sleep)
    return sorted(d for d in out if start <= d <= end)


def has_market(day, market):
    p = os.path.join(EARLY, "daily", day + ".csv")
    if not os.path.exists(p):
        return False
    with io.open(p, encoding="utf-8") as f:
        return any(r.get("market") == market for r in csv.DictReader(f))


def blank_notrade(lines):
    """⭐ 早年上櫃把【無成交】寫成 0.00（2007-07-02 實測 6 列：量 0、額 0、筆數 0、四價 0.00）；
    主庫 data/universe/daily 的慣例是【四價空白】（2015-01-05 兩市 24 列、2020-03-02 37 列全是空白）。
    ⛔ 不改的話讀檔的人會把它當成「收盤 0 元」⇒ 報酬 −100%。
    ⇒ 只改【量為 0 且四價全為 0】這一種；量 > 0 的零價一律留原值、記成異常（structure 的 zero）。
    回傳改了幾列。"""
    H = F.UNIVERSE_HEADER
    px = [H.index(k) for k in ("open", "high", "low", "close")]
    iv = H.index("volume")
    n = 0
    for r in lines:
        try:
            if str(r[iv]).replace(",", "") in ("0", "") and all(float(str(r[i]).replace(",", "")) == 0 for i in px):
                for i in px:
                    r[i] = ""
                n += 1
        except (ValueError, TypeError):
            continue
    return n


def structure(lines):
    """⛔ 只看結構：→ dict。"""
    H = F.UNIVERSE_HEADER
    io_, ih, il, ic = H.index("open"), H.index("high"), H.index("low"), H.index("close")
    bad_hl = zero = neg = traded = 0
    for r in lines:
        try:
            o, h, l, c = (float(str(r[i]).replace(",", "")) for i in (io_, ih, il, ic))
        except (ValueError, TypeError):
            continue                   # 無成交列（空價）不算
        traded += 1
        if min(o, h, l, c) < 0:
            neg += 1
        if min(o, h, l, c) == 0:
            zero += 1
        if not (l <= o <= h and l <= c <= h):
            bad_hl += 1
    return {"rows": len(lines), "traded": traded, "bad_hl": bad_hl, "zero": zero, "neg": neg}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", required=True, choices=["twse", "tpex"])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--sleep", type=float, default=5.0)
    ap.add_argument("--max-days", type=int, default=100000)
    a = ap.parse_args()
    start = max(a.start, FLOOR[a.market])
    end = min(a.end, "2015-01-04")        # ⛔ 早年段只到全庫起點（2015-01-05）之前
    F.UNI_DIR = EARLY                                  # ⭐ 唯一的改動：輸出路徑
    os.makedirs(os.path.join(EARLY, "daily"), exist_ok=True)
    rl = runlog.Run("early:%s" % a.market)
    days = trading_days(a.market, start, end, a.sleep)
    rl.info("交易日", "%d 天（%s ~ %s，官方月表）" % (len(days), days[0], days[-1]))
    st_path = os.path.join(EARLY, "_structure.csv")
    st_rows = []
    done = skipped = failed = 0
    fails = []
    for day in days:
        if done >= a.max_days:
            break
        if has_market(day, a.market):
            skipped += 1
            continue
        lines, note = B.fetch_day_market(day, a.market, B.candidates(day)[a.market])
        time.sleep(a.sleep)
        if not lines:
            failed += 1
            fails.append((day, str(note)[:60]))
            continue
        blanked = blank_notrade(lines)
        F.write_universe_day(day, lines)
        s = structure(lines)
        st_rows.append([day, a.market] + [s[k] for k in ("rows", "traded", "bad_hl", "zero", "neg")] + [blanked])
        done += 1
    # 結構台帳（累加，同一天同市場以新的為準）
    old = {}
    if os.path.exists(st_path):
        with io.open(st_path, encoding="utf-8") as f:
            for r in csv.reader(f):
                if r and r[0] != "date":
                    old[(r[0], r[1])] = r
    for r in st_rows:
        old[(r[0], r[1])] = [str(x) for x in r]
    with io.open(st_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "market", "rows", "traded", "bad_hl", "zero", "neg", "notrade_blanked"])
        for k in sorted(old):
            w.writerow(old[k])
    tot = lambda k: sum(int(r[k]) for r in st_rows) if st_rows else 0
    rl.info("本趟", "寫 %d 天｜已有跳過 %d｜失敗 %d｜結構：bad_hl %d、零價 %d、負價 %d｜無成交 0.00 改空白 %d 列"
            % (done, skipped, failed, tot(4), tot(5), tot(6), tot(7)))
    if fails:
        rl.info("失敗的日子（前 10）", str(fails[:10]))
    rl.check("失敗 0 天（⛔ 交易日上拿不到 ≠ 休市）", not fails, str(fails[:5]))
    rl.finish()
    print("%s 寫 %d｜跳過 %d｜失敗 %d｜bad_hl %d 零價 %d 負價 %d｜改空白 %d"
          % (a.market, done, skipped, failed, tot(4), tot(5), tot(6), tot(7)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
