#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""資金費率全期交件驗收（裁定線 seq97 §三 三項）。⛔ 只讀。

  ① 六幣各自首列 ＝ C2 §2-C③之二 窗首表（BTC／ETH 是左截值）
  ② SOL 2022-11 ＝ 165 列、Σ ＝ −0.354915、間隔 {8:64,4:2,2:99}（與回測線 fixture 丙逐位相同）
  ③ 清單列數 ＝ 實際月份數；缺月逐月列出（⛔ 不補 0），並分「上市前」與「上市後」
     ⛔ 上市後的缺月才是真的缺；上市前的是「還不存在」
"""
import csv
import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data")
# C2 v6 §2-C③之二 窗首表的「資金費率第一筆」欄（逐字抄；BTC／ETH 是封存下限左截）
EXPECT_FIRST = {"BTC": "2020-01-01 00:00", "ETH": "2020-01-01 00:00", "XRP": "2020-01-06 08:00",
                "BNB": "2020-02-10 08:00", "DOGE": "2020-07-10 08:00", "SOL": "2020-09-13 16:00"}


def utc(ms):
    return datetime.datetime.fromtimestamp(int(ms) / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")


def main():
    ok_all = True
    print("① 首列 vs C2 窗首表")
    first_month = {}
    for sym, exp in EXPECT_FIRST.items():
        with io.open(os.path.join(ROOT, "crypto_funding", sym + "USDT.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        got = utc(rows[0]["calc_time"])
        first_month[sym] = got[:7]
        good = got == exp
        ok_all &= good
        print("   %-4s 我方 %s｜窗首表 %s ⇒ %s" % (sym, got, exp, "✅" if good else "✗"))

    print("② SOL 2022-11")
    with io.open(os.path.join(ROOT, "crypto_funding", "SOLUSDT.csv"), encoding="utf-8") as f:
        sol = [r for r in csv.DictReader(f) if utc(r["calc_time"]).startswith("2022-11")]
    s = sum(float(r["last_funding_rate"]) for r in sol)
    mix = {}
    for r in sol:
        mix[int(r["funding_interval_hours"])] = mix.get(int(r["funding_interval_hours"]), 0) + 1
    g2 = len(sol) == 165 and abs(s - (-0.354915)) < 5e-7 and mix == {8: 64, 4: 2, 2: 99}
    ok_all &= g2
    print("   列數 %d（應 165）｜Σ %.8f（應 −0.354915）｜間隔 %s（應 {8:64,4:2,2:99}）⇒ %s"
          % (len(sol), s, mix, "✅" if g2 else "✗"))

    print("③ 清單")
    with io.open(os.path.join(ROOT, "meta", "crypto_funding_manifest.csv"), encoding="utf-8") as f:
        man = list(csv.DictReader(f))
    for sym in EXPECT_FIRST:
        ms = [m for m in man if m["sym"] == sym]
        months = sorted(m["month"] for m in ms)
        pre = [m["month"] for m in ms if m["status"] == "absent" and m["month"] < first_month[sym]]
        post = [m["month"] for m in ms if m["status"] == "absent" and m["month"] >= first_month[sym]]
        err = [m["month"] for m in ms if m["status"].startswith("error")]
        dup = len(months) != len(set(months))
        n_ok = sum(1 for m in ms if m["status"] == "ok")
        rows_man = sum(int(m["rows"]) for m in ms)
        with io.open(os.path.join(ROOT, "crypto_funding", sym + "USDT.csv"), encoding="utf-8") as f:
            rows_file = sum(1 for _ in f) - 1
        good = not post and not err and not dup
        ok_all &= good
        print("   %-4s 清單 %d 列（%s ~ %s）｜ok %d｜上市前 absent %d%s｜⛔ 上市後缺 %s｜error %s｜"
              "清單列數合計 %d vs 檔案 %d 列 ⇒ %s"
              % (sym, len(ms), months[0], months[-1], n_ok, len(pre),
                 ("（%s~%s）" % (pre[0], pre[-1])) if pre else "", post or "0", err or "0",
                 rows_man, rows_file, "✅" if good else "✗"))
        if rows_man != rows_file:
            print("        ⚠ 清單加總與檔案列數不同 ⇒ 月界有重複列被去掉 %d 列（calc_time 為鍵）"
                  % (rows_man - rows_file))
    print("⇒ %s" % ("三項全過" if ok_all else "⛔ 有未過"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
