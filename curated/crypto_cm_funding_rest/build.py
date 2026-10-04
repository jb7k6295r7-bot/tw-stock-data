# -*- coding: utf-8 -*-
"""幣本位永續 XXXUSD_PERP 資金費率：data.binance.vision 封存只從 2022-07 起 ⇒ 之前那段用 REST 補（C10 §十①）。

    python3 curated/crypto_cm_funding_rest/build.py     （⛔ 只能在本機跑：dapi 從 GitHub Actions 回 451）

來源：GET https://dapi.binance.com/dapi/v1/fundingRate?symbol=<SYM>USD_PERP&startTime=&endTime=&limit=1000
區間：各幣上市日（exchangeInfo onboardDate）～ 跑的當下（封存 2022-07 起與本檔重疊，逐筆對帳）
輸出：<SYM>USD_PERP.csv  funding_time,funding_rate,rate_type（照官方欄位，⛔ 不換算）
判準：每一列 symbol 要等於送出的 symbol；時間要落在 [start, end]；翻頁以最後一筆 fundingTime+1 續，直到少於 limit
"""
import csv, io, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://dapi.binance.com/dapi/v1/fundingRate?symbol=%s&startTime=%d&endTime=%d&limit=1000"
ONBOARD = {"BTC": "2020-08-10", "ETH": "2020-08-18", "BNB": "2020-08-21", "XRP": "2020-09-09",
           "DOGE": "2021-02-01", "SOL": "2021-09-01"}
END_MS = int(time.time() * 1000)   # 跑的當下（2026-10-04 改：封存每月缺月底一天＋落後 ⇒ REST 全期）


def ms(d):
    import datetime
    return int(datetime.datetime.fromisoformat(d + "T00:00:00+00:00").timestamp() * 1000)


def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "tw-stock-data cm_funding_rest"}), timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:      # noqa: BLE001
            err = e
            time.sleep(5 * (i + 1))
    raise SystemExit(f"⛔ 取不到：{u}｜{err}")


def main():
    for s, d in ONBOARD.items():
        sym = s + "USD_PERP"
        start, rows = ms(d), {}
        while True:
            j = get(URL % (sym, start, END_MS))
            if not isinstance(j, list):
                raise SystemExit(f"⛔ {sym} 回應不是清單：{str(j)[:200]}")
            for r in j:
                if r["symbol"] != sym or not (ms(d) <= int(r["fundingTime"]) <= END_MS):
                    raise SystemExit(f"⛔ {sym} 自述不符：{r}")
                rows[int(r["fundingTime"])] = (r["fundingTime"], r["fundingRate"], r.get("rateType", ""))
            if len(j) < 1000:
                break
            start = int(j[-1]["fundingTime"]) + 1
            time.sleep(1.5)
        with io.open(os.path.join(HERE, sym + ".csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["funding_time", "funding_rate", "rate_type"])
            w.writerows(rows[k] for k in sorted(rows))
        print(sym, len(rows), "列", "第一筆", min(rows) if rows else "—")
        time.sleep(1.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
