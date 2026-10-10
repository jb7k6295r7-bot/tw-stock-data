#!/usr/bin/env python3
"""BTCUSDT 永續資金費：月封存（data/crypto_funding，2020-01 起）之前那段（2019-09-10 上市～2019-12-31）⇒ 官方 REST 補。
⛔ fapi 從 GitHub Actions 回 451 ⇒ 本機跑一次、手工落檔；欄位與 data/crypto_funding 相同。"""
import csv, json, sys, urllib.request
U = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1546300800000&endTime=1577836799999&limit=1000"
j = json.load(urllib.request.urlopen(urllib.request.Request(U, headers={"User-Agent": "Mozilla/5.0"}), timeout=60))
assert all(x["symbol"] == "BTCUSDT" for x in j)
w = csv.writer(sys.stdout, lineterminator="\n")
w.writerow(["calc_time", "funding_interval_hours", "last_funding_rate"])
for x in j:
    if int(x["fundingTime"]) < 1577836800000:          # 2020-01-01 起由月封存提供
        w.writerow([x["fundingTime"], "8", x["fundingRate"]])
