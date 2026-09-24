#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【本機工具】fapi 的 fundingRate 與封存檔 last_funding_rate 是不是同一個量（C2 ⓐ）。

⛔⛔ 只能在本機跑（WSL）：Actions 打 api.binance.com／fapi 回 451（地區限制，crypto_probe 2026-09-20）
   ⇒ ⛔ 不要放進任何 workflow：它會天天紅，而紅的原因是地區、不是資料。
⭐ 裁定線 20260924-2229 seq92 §四：「探針放進 repo 當常設 ⇒ 要；它是 ⓐ 的可重跑」
   ⇒ 本檔就是 2026-09-24 22:2x 那一次比對的原程式（三筆同號同值、同一毫秒、含一筆負值）。

判準：SOLUSDT 2022-11 取一筆 8h、一筆 2h ＋ 2020-10 月中一筆，逐筆比字串與時間戳。
⛔ 只讀：三個 fapi 請求＋兩個封存 zip，不寫任何檔。
"""
import csv
import datetime as dt
import io
import json
import sys
import urllib.request
import zipfile

UA = {"User-Agent": "Mozilla/5.0 (tw-stock-data fapi_check; read-only)"}


def get(url, raw=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
    return b if raw else json.loads(b.decode("utf-8"))


def archive(sym, ym):
    u = ("https://data.binance.vision/data/futures/um/monthly/fundingRate/%s/%s-fundingRate-%s.zip"
         % (sym, sym, ym))
    z = zipfile.ZipFile(io.BytesIO(get(u, raw=True)))
    return list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))))


def iso(ms):
    return dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def main():
    picks = []
    rows = archive("SOLUSDT", "2022-11")
    by = {}
    for r in rows:
        by.setdefault(r["funding_interval_hours"], []).append(r)
    picks += [by["8"][5], by["2"][10]]
    rows = archive("SOLUSDT", "2020-10")
    picks.append(rows[len(rows) // 2])
    bad = 0
    for r in picks:
        t = int(r["calc_time"])
        api = get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=SOLUSDT&startTime=%d&endTime=%d&limit=10"
                  % (t - 60000, t + 60000))
        if len(api) != 1:
            print("⚠ %s fapi 回 %d 筆" % (iso(t), len(api)))
            bad += 1
            continue
        a = api[0]
        same = a["fundingRate"] == r["last_funding_rate"] and int(a["fundingTime"]) == t
        bad += not same
        print("%s UTC｜間隔 %sh｜封存 %s｜fapi %s｜時間差 %d ms ⇒ %s"
              % (iso(t), r["funding_interval_hours"], r["last_funding_rate"], a["fundingRate"],
                 int(a["fundingTime"]) - t, "✅ 逐字相同" if same else "✗"))
    print("⇒ %s" % ("三筆全對" if not bad else "⛔ %d 筆不對" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
