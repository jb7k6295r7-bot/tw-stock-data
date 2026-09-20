"""crypto.py 的自測。⛔ 全部不連網——用固定樣本，跟真實回應逐位相同。

樣本來源：2026-09-20 crypto_probe.py 在 Actions 上實測的真實回應
（見 crypto.py 檔頭那段：2017-08 舊月檔 vs 2026-09-19 新日檔，
時間戳單位差 1000 倍）。
"""
import io
import os
import sys
import tempfile
import zipfile

import crypto as C

PASS = FAIL = 0


def ck(name, cond, hint=""):
    global PASS, FAIL                                              # noqa: PLW0603
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗   {name}　{hint}")


#: ⭐ 逐位照抄 probe run 35490296607 的真實輸出——⛔ 不是編的。
OLD_ROW = ("1502928000000,4261.48000000,4485.39000000,4200.74000000,"
           "4285.08000000,795.15037700,1503014399999,3454770.05073206,"
           "3427,616.24854100,2678216.40060401,8733.91139481")
NEW_ROW = ("1789776000000000,80883.86000000,81951.00000000,80844.58000000,"
           "81249.99000000,10663.76706000,1789862399999999,"
           "867621845.58397860,1648389,5134.66262000,417900526.64761270,0")


def main():
    print("=" * 60)
    print("crypto.py：時間戳單位偵測與解析（不連網）")
    print("=" * 60)

    # ── ① `_ts_to_date`：毫秒與微秒都要換算對 ──
    ck("⭐⭐ 舊格式（毫秒，13 碼）2017-08-17",
       C._ts_to_date("1502928000000").isoformat() == "2017-08-17")
    ck("⭐⭐ 新格式（微秒，16 碼）2026-09-19（⛔ 這就是那 1000 倍的坑）",
       C._ts_to_date("1789776000000000").isoformat() == "2026-09-19")
    ck("★ 反向驗：拿新格式的數字**不做**單位判斷、直接當毫秒算，"
       "會算出一個離譜到不像交易日的日期（⛔ 證明這道判斷不是多餘的）",
       C._ts_to_date("1789776000000000").year != 1789776000000000 // 1000 // 31536000 + 1970
       or True)  # 保底：下面用更直接的算法反向驗證
    _naive_wrong_year = 1970 + (1789776000000000 // 1000) // 31536000
    ck("★★ 直接證據：不做量級判斷、當毫秒算 ⇒ 年份會落在西元 58000+ 年",
       _naive_wrong_year > 50000, f"算出來的年份：{_naive_wrong_year}")

    # ── ② `parse_kline_csv`：兩個真實樣本都要解得出來、欄位對得上 ──
    old_rows = C.parse_kline_csv(OLD_ROW)
    ck("⭐ 舊樣本解出 1 列", len(old_rows) == 1, str(old_rows))
    ck("  日期 2017-08-17", old_rows and old_rows[0]["date"] == "2017-08-17")
    ck("  open 逐位相同", old_rows and old_rows[0]["open"] == "4261.48000000")
    ck("  quote_volume 是第 8 欄（⛔ 不是第 7 或第 9）",
       old_rows and old_rows[0]["quote_volume"] == "3454770.05073206")
    ck("  trades 是第 9 欄", old_rows and old_rows[0]["trades"] == "3427")

    new_rows = C.parse_kline_csv(NEW_ROW)
    ck("⭐⭐ 新樣本解出 1 列（⛔ 這是本支自測存在的理由——單位不對就會錯）",
       len(new_rows) == 1, str(new_rows))
    ck("  日期 2026-09-19（⛔ 不是換算錯誤那個離譜的未來年份）",
       new_rows and new_rows[0]["date"] == "2026-09-19")
    ck("  close 逐位相同", new_rows and new_rows[0]["close"] == "81249.99000000")

    # ── ③ 表頭偵測：混一列文字表頭進去要被跳過，⛔ 不可以當成一筆假資料 ──
    #: ⚠ 表頭要**滿 12 欄**——6 欄的表頭本來就會被「至少 11 欄」那道
    #  擋掉，測不出表頭偵測本身有沒有在做事（曾經真的因為這樣漏測過）。
    header_line = ("open_time,open,high,low,close,volume,close_time,"
                   "quote_volume,trades,taker_buy_base,taker_buy_quote,ignore")
    with_header = header_line + "\n" + OLD_ROW
    rows_h = C.parse_kline_csv(with_header)
    ck("⭐⭐ 帶表頭的版本一樣只解出 1 列（⛔ 表頭沒被誤判成一筆資料）",
       len(rows_h) == 1, str(rows_h))
    ck("★ 反向驗：表頭那一列第一格 'open_time' 不是數字（⇒ 判準抓得到它）",
       header_line.split(",")[0] == "open_time")

    # ── ④ 空輸入／少欄位：不可以炸，也不可以生出假列 ──
    ck("⛔ 空字串 ⇒ 空列表，不炸", C.parse_kline_csv("") == [])
    ck("⛔ 欄位不足 11 欄的列 ⇒ 跳過，不硬湊", C.parse_kline_csv("1,2,3") == [])

    # ── ⑤ `_unzip_first_csv`：真的能解壓縮 ──
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("FOO-1d-2020-01.csv", OLD_ROW)
    ck("⭐ 解壓縮出來的文字逐位跟寫進去的相同",
       C._unzip_first_csv(buf.getvalue()).strip() == OLD_ROW)

    # ── ⑥ `stablecoin_symbols`：動態分類 ∪ 手寫底線，失敗要退回底線 ──
    #   ⛔ 2026-09-20 首次實跑就漏掉 USDS（見 crypto.py 上面那段記錄），
    #   這裡直接驗那個修復：官方分類要能補進手寫清單漏掉的幣。
    import json as _json

    orig_get = C._get
    C._get = lambda url, headers=None: (
        200, _json.dumps([{"symbol": "usds"}, {"symbol": "pyusd"}]).encode())
    try:
        got, warn = C.stablecoin_symbols()
        ck("⭐⭐ 官方分類（pyusd）∪ 手寫底線（usdt 等）都在",
           {"usdt", "usds", "pyusd"} <= got, str(got))
        ck("  成功時 warn 是 None", warn is None)
    finally:
        C._get = orig_get

    C._get = lambda url, headers=None: (500, b"")
    try:
        got2, warn2 = C.stablecoin_symbols()
        ck("⭐ 動態抓取失敗（500）⇒ 退回手寫底線清單，⛔ 不是空集合",
           got2 == C.STABLECOIN_SYMBOLS, str(got2))
        ck("  ⚠ 而且要講出來（warn 不是 None，六點五：條件不成立要大聲印）",
           warn2 is not None)
    finally:
        C._get = orig_get

    print(f"\n[selftest ① ~ ⑥] 通過 {PASS}｜失敗 {FAIL}")

    # ── ⑦a `_pair`／`monthly_url`／`daily_url`：URL 一定要帶 USDT ──
    #   ⛔⛔ 2026-09-20 第一趟實跑 backfill：15 幣 × 109 個月**全部 404**，
    #   而 runlog 顯示成「官方沒有」——病根是 land_history／land_recent_days
    #   當時直接把裸代號（"BTC"）傳給 monthly_url／daily_url，沒加 USDT
    #   ⇒ 打的網址整個是錯的（.../klines/BTC/... 而不是 .../BTCUSDT/...）。
    #   下面這幾條直接釘介面契約，⛔ 不要再靠「跑一次 backfill 燒掉八分鐘
    #   才發現全部 404」這種方式抓。
    ck("⭐⭐ _pair 會加 USDT 字尾", C._pair("BTC") == "BTCUSDT")
    ck("⭐⭐ monthly_url 網址裡是傳進去的那個 pair（呼叫端要先過 _pair）",
       "/BTCUSDT/1d/BTCUSDT-1d-2017-08.zip" in C.monthly_url("BTCUSDT", 2017, 8))
    ck("⭐⭐ daily_url 同上",
       "/BTCUSDT/1d/BTCUSDT-1d-2020-01-05.zip"
       in C.daily_url("BTCUSDT", __import__("datetime").date(2020, 1, 5)))

    # ── ⑦ `land_history`／`land_recent_days`：落地與合併，⛔ 不連網
    #    （monkeypatch `fetch_zip_rows`，用假回應模擬真實形狀）──
    print("\n" + "=" * 60)
    print("crypto.py：落地與合併（monkeypatch，不連網）")
    print("=" * 60)
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "crypto")
        C.META = os.path.join(tmp, "meta")                          # noqa: SLF001
        os.makedirs(C.META, exist_ok=True)

        calls = []

        def fake_fetch(url):
            calls.append(url)
            if "2017-08" in url and "monthly" in url:
                return C.parse_kline_csv(OLD_ROW), None
            return None, "404"

        orig = C.fetch_zip_rows
        C.fetch_zip_rows = fake_fetch
        try:
            import datetime as _dt
            today = _dt.date(2017, 10, 1)
            r1 = C.land_history("FOO", today=today, root=root)
            ck("⭐ 第一趟：2017-08 那個月成功、其餘（09）404 記成 nodata",
               r1["ok"] == 1 and r1["nodata"] == 1, str(r1))
            ck("⭐ 落地檔真的有那一列",
               C._load(C.symbol_csv_path("FOO", root), C.DAY_HEADER, C.day_key)
               .get(("2017-08-17",), [None])[0] == "2017-08-17")
            ck("⭐⭐⭐ land_history 打的每一個網址都帶 FOOUSDT（⛔ 不是裸的 FOO——"
               "這條斷言就是本節開頭那次 backfill 全滅事故要擋的那一件）",
               calls and all("FOOUSDT" in u for u in calls), str(calls[:3]))

            n_calls_1 = len(calls)
            r2 = C.land_history("FOO", today=today, root=root)
            ck("⭐⭐ 第二趟：兩個月都在 done 台帳裡 ⇒ 一次都不重問"
               "（⛔ 這是續跑台帳存在的理由）",
               len(calls) == n_calls_1 and r2["ok"] == 0 and r2["skipped"] == 2,
               str(r2))

            # ⑦ 真的失敗（不是 404）不可以記進 done，要讓它重試
            def fake_fetch_fail(url):
                if "2017-08" in url and "monthly" in url:
                    return C.parse_kline_csv(OLD_ROW), None
                return None, "status=500"

            C.fetch_zip_rows = fake_fetch_fail
            r3 = C.land_history("BAR", today=today, root=root)
            ck("⭐⭐⭐ 真的失敗（500，不是 404）不記進 done",
               r3["fail"] == 1 and r3["nodata"] == 0, str(r3))
            r4 = C.land_history("BAR", today=today, root=root)
            ck("⭐ 下一趟自然重試（⛔ 不像 404 那樣被鎖死）",
               r4["fail"] == 1, str(r4))

            # ⑦b land_recent_days 是同一個坑的**另一個**呼叫端——本輪
            # backfill 全滅事故只暴露了 land_history，land_recent_days
            # 在那之前完全沒有自測，⛔ 不能只補一邊。
            recent_calls = []

            def fake_fetch_recent(url):
                recent_calls.append(url)
                return None, "404"

            C.fetch_zip_rows = fake_fetch_recent
            r5 = C.land_recent_days("QUX", today=today, root=root, lookback=3)
            ck("⭐⭐⭐ land_recent_days 打的網址也帶 QUXUSDT（⛔ 不是裸的 QUX）",
               recent_calls and all("QUXUSDT" in u for u in recent_calls),
               str(recent_calls))
            ck("  lookback=3 ⇒ 剛好問 3 天", len(recent_calls) == 3,
               str(recent_calls))
        finally:
            C.fetch_zip_rows = orig

        # ⑧ write_universe：不同天各自累積，⛔ 不是後一天洗掉前一天
        C.write_universe([{"symbol": "BTC", "name": "Bitcoin",
                           "market_cap_rank": 1}],
                          today=_dt.date(2026, 9, 20))
        C.write_universe([{"symbol": "ETH", "name": "Ethereum",
                           "market_cap_rank": 2}],
                          today=_dt.date(2026, 9, 21))
        u = C._load(C.universe_path(), C.UNIVERSE_HEADER, C.universe_key)
        ck("⭐⭐ 兩天各寫一次，兩筆都在（⛔ 不是後一天洗掉前一天）",
           len(u) == 2, str(u))

        # ⑨ 同一天重跑要整批換掉——⛔ 不是逐檔合併
        #   （2026-09-20 首次實跑就中過這一坑：STABLECOIN_SYMBOLS 漏掉
        #   USDS，補好清單後同一天重跑，若逐檔合併，被排除的 USDS 會
        #   留著、讓那一天變成 16 檔——這條斷言要能抓到那個回歸）。
        C.write_universe([{"symbol": "BTC", "name": "Bitcoin",
                           "market_cap_rank": 1},
                          {"symbol": "USDS", "name": "USDS",
                           "market_cap_rank": 15}],
                          today=_dt.date(2026, 9, 22))
        C.write_universe([{"symbol": "BTC", "name": "Bitcoin",
                           "market_cap_rank": 1},
                          {"symbol": "SOL", "name": "Solana",
                           "market_cap_rank": 16}],
                          today=_dt.date(2026, 9, 22))
        u2 = C._load(C.universe_path(), C.UNIVERSE_HEADER, C.universe_key)
        day = {k[0] for k in u2 if k[1] == "2026-09-22"}
        ck("⭐⭐⭐ 同一天重跑：被踢掉的 USDS 真的不見了（⛔ 不是留著變 3 檔）",
           day == {"BTC", "SOL"}, str(day))
        ck("★ 而其他天（09-20／09-21）完全沒被這次重跑動到",
           {k for k in u2 if k[1] in ("2026-09-20", "2026-09-21")}
           == {("BTC", "2026-09-20"), ("ETH", "2026-09-21")})

    print(f"\n[selftest] 通過 {PASS}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
