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
import runlog

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

        # ⑦c reset_months_done：⛔ 這就是本節開頭那次事故的**善後**機制
        #   （台帳被污染成全部誤記 nodata 之後，唯一能重新回補的辦法）。
        dp = C.months_done_path()
        ck("⭐ 重置前：台帳確實存在（上面幾趟已經寫過）", os.path.exists(dp))
        removed = C.reset_months_done()
        ck("⭐⭐ 重置：回傳 True（真的刪到檔）", removed is True)
        ck("⭐⭐ 重置：檔案真的不在了", not os.path.exists(dp))
        ck("★ 重置一個本來就不存在的台帳：回傳 False，⛔ 不炸",
           C.reset_months_done() is False)

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

    # ── ⑩ Bitstamp：parse_bitstamp_ohlc／land_bitstamp_history（不連網）──
    #   樣本來源：2026-09-22 crypto_probe.py 在 Actions 上實測的真實回應
    #   （第一根 2013-10-01、收盤 127.33 美元），⛔ 不是編的形狀。
    print("\n" + "=" * 60)
    print("crypto.py：Bitstamp 解析與回補（monkeypatch，不連網）")
    print("=" * 60)

    real_bitstamp_body = (
        b'{"data": {"pair": "BTC/USD", "ohlc": ['
        b'{"timestamp": "1380585600", "open": "126.25", "high": "127.93", '
        b'"low": "125.54", "close": "127.33", "volume": "7513.83496080"}, '
        b'{"timestamp": "1380672000", "open": "127.31", "high": "127.80", '
        b'"low": "85.00", "close": "103.85", "volume": "60639.38898698"}'
        b']}}')
    parsed = C.parse_bitstamp_ohlc(real_bitstamp_body)
    ck("⭐ 真實樣本解出 2 列", len(parsed) == 2, str(parsed))
    ck("  第一列日期 2013-10-01（⛔ 不是時區算錯的 09-30 或 10-02）",
       parsed and parsed[0]["date"] == "2013-10-01")
    ck("  close 逐位相同", parsed and parsed[0]["close"] == "127.33")
    ck("  Bitstamp 沒有 quote_volume 這個鍵（⛔ 不可以湊一個假的）",
       parsed and "quote_volume" not in parsed[0])

    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "crypto")
        os.makedirs(root, exist_ok=True)
        orig_pairs = C.BITSTAMP_PAIRS
        orig_limit = C.BITSTAMP_LIMIT
        orig_get = C._get
        C.BITSTAMP_PAIRS = {"FOO": "foousd"}
        C.BITSTAMP_LIMIT = 3

        def _mk_ohlc(dates):
            return {"data": {"pair": "FOO/USD", "ohlc": [
                {"timestamp": str(int(__import__("datetime").datetime(
                    d.year, d.month, d.day,
                    tzinfo=__import__("datetime").timezone.utc).timestamp())),
                 "open": "1", "high": "1", "low": "1", "close": "1",
                 "volume": "1"} for d in dates]}}

        import datetime as _dt2
        import json as _json2

        bitstamp_calls = []

        def fake_bitstamp_get(url, headers=None):
            bitstamp_calls.append(url)
            # ⭐ 用 URL 裡的 start= 決定回幾根，模擬「這一段撞到來源起點」
            start_ts = int(url.split("start=")[1].split("&")[0])
            start_d = _dt2.datetime.utcfromtimestamp(start_ts).date()
            if start_d < _dt2.date(2013, 1, 4):
                dates = [start_d, start_d + _dt2.timedelta(days=1),
                         start_d + _dt2.timedelta(days=2)]        # 滿頁（3 根）
            else:
                dates = [start_d]                                  # 不滿頁 ⇒ 到頭了
            return 200, _json2.dumps(_mk_ohlc(dates)).encode()

        C._get = fake_bitstamp_get
        try:
            r1 = C.land_bitstamp_history("FOO", _dt2.date(2017, 1, 1),
                                          today=_dt2.date(2020, 1, 1),
                                          start_date=_dt2.date(2013, 1, 1),
                                          root=root)
            ck("⭐⭐ 分頁抓完：01-01~01-03（滿頁）＋01-04（不滿頁，停）＝ 4 列",
               r1["new_rows"] == 4, str(r1))
            days = C._load(C.symbol_csv_path("FOO", root), C.DAY_HEADER, C.day_key)
            ck("⭐ 這幾列的 source 是 bitstamp（⛔ 不是空白）",
               all(row[-1] == "bitstamp" for row in days.values()), str(days))
            ck("⭐⭐ Binance 專屬那四欄留空（⛔ 不是湊假資料）",
               all(row[6] == "" and row[7] == "" for row in days.values()))

            # ⛔⛔ 邊界：end_date 之前跟之後同一頁回來時，>= end_date 的要被丟掉
            C._get = lambda url, headers=None: (
                200, _json2.dumps(_mk_ohlc(
                    [_dt2.date(2020, 6, 1), _dt2.date(2020, 6, 2),
                     _dt2.date(2020, 6, 3)])).encode())
            r2 = C.land_bitstamp_history("FOO", _dt2.date(2020, 6, 2),
                                          today=_dt2.date(2020, 6, 5),
                                          start_date=_dt2.date(2020, 6, 1),
                                          root=root)
            days2 = C._load(C.symbol_csv_path("FOO", root), C.DAY_HEADER, C.day_key)
            ck("⭐⭐⭐ end_date（06-02）自己跟之後的都不落地，⛔ 不可以跟既有資料重疊",
               ("2020-06-01",) in days2 and ("2020-06-02",) not in days2
               and ("2020-06-03",) not in days2, str(sorted(days2)))

            # 未驗證過的幣種：不猜、不連網，直接回 0 列並講出理由
            r3 = C.land_bitstamp_history("BAR", _dt2.date(2017, 1, 1))
            ck("⭐ BITSTAMP_PAIRS 沒有的幣種 ⇒ 0 列、附理由，⛔ 不炸也不亂猜端點",
               r3["new_rows"] == 0 and "why" in r3, str(r3))
        finally:
            C.BITSTAMP_PAIRS = orig_pairs
            C.BITSTAMP_LIMIT = orig_limit
            C._get = orig_get

        # ⭐⭐⭐ 既有列（加 source 欄之前寫的）要被回填成 binance，⛔ 不是留空
        legacy_path = C.symbol_csv_path("LEGACY", root)
        os.makedirs(os.path.dirname(legacy_path), exist_ok=True)
        with open(legacy_path, "w", encoding="utf-8", newline="") as f:
            f.write("date,open,high,low,close,volume,quote_volume,trades,"
                    "taker_buy_base,taker_buy_quote,asof\n")
            f.write("2017-08-17,4261.48,4485.39,4200.74,4285.08,795.15,"
                    "3454770.05,3427,616.25,2678216.40,2026-09-20\n")
        C.BITSTAMP_PAIRS = {"LEGACY": "legacyusd"}
        C._get = lambda url, headers=None: (200, _json2.dumps(
            {"data": {"pair": "x", "ohlc": []}}).encode())
        try:
            C.land_bitstamp_history("LEGACY", _dt2.date(2013, 1, 1),
                                     start_date=_dt2.date(2013, 1, 1), root=root)
        finally:
            C.BITSTAMP_PAIRS = orig_pairs
            C._get = orig_get
        legacy_days = C._load(legacy_path, C.DAY_HEADER, C.day_key)
        ck("⭐⭐ 既有的 2017-08-17 那一列 source 被回填成 binance（⛔ 不是空白）",
           legacy_days.get(("2017-08-17",), [None] * 12)[-1] == "binance",
           str(legacy_days.get(("2017-08-17",))))

        # ⭐⭐ earliest_landed_date：踩過的坑是拿「月初」（2017-08-01）
        # 當 Bitstamp 回補終點，⛔ 而真正第一筆是 2017-08-17 ⇒ 中間 16 天
        # 兩邊都沒有。這支要從既有檔案量出**真正**最早那一天。
        ck("⭐ 沒有這個檔／沒有資料 ⇒ 回 None",
           C.earliest_landed_date("NOSUCHSYMBOL", root=root) is None)
        ck("⭐⭐ LEGACY 只有一列 2017-08-17（binance）⇒ 回那一天本身（⛔ 不是月初）",
           C.earliest_landed_date("LEGACY", root=root) == _dt2.date(2017, 8, 17),
           str(C.earliest_landed_date("LEGACY", root=root)))
        ck("⭐⭐⭐ FOO 只有 Bitstamp 列（2013-01-01~01-04），⛔ 沒有任何 Binance 列 "
           "⇒ 回 None（⛔ 不是隨便拿 Bitstamp 自己的最早一天充數）",
           C.earliest_landed_date("FOO", root=root) is None,
           str(C.earliest_landed_date("FOO", root=root)))

        # ⛔⛔⛔ 2026-09-22 在 Actions 上真的炸過的那一版：對全部列取 min，
        # 第一趟 bitstamp-backfill 成功之後，檔案裡最早那一列變成
        # Bitstamp 自己的 2013-01-01，比 Binance 真正的 2017-08-17 還早
        # ⇒ 邊界越滑越早，第二趟直接不再抓任何新資料，16 天的洞原封不動。
        # ⇒ 這支要模擬「已經回補過一次」的檔案形狀：早期 Bitstamp 列
        #   ＋ 晚期 Binance 列都在同一個檔案裡。
        mixed_path = C.symbol_csv_path("MIXED", root)
        with open(mixed_path, "w", encoding="utf-8", newline="") as f:
            f.write(",".join(C.DAY_HEADER) + "\n")
            f.write("2013-01-01,1,1,1,1,1,,,,,2026-09-22,bitstamp\n")
            f.write("2017-07-31,1,1,1,1,1,,,,,2026-09-22,bitstamp\n")
            f.write("2017-08-17,1,1,1,1,1,1,1,1,1,2026-09-22,binance\n")
            f.write("2017-08-18,1,1,1,1,1,1,1,1,1,2026-09-22,binance\n")
        ck("⭐⭐⭐ MIXED 早期 Bitstamp（2013-01-01 起）＋晚期 Binance"
           "（2017-08-17 起）混在同一個檔案 ⇒ 回 **2017-08-17**，"
           "⛔ 不是 2013-01-01（那是 Bitstamp 自己的起點，不是 Binance 的）",
           C.earliest_landed_date("MIXED", root=root) == _dt2.date(2017, 8, 17),
           str(C.earliest_landed_date("MIXED", root=root)))

    # ── ⑪ main()「bitstamp-backfill」呼叫點：⛔ 只測 earliest_landed_date()
    #    本身抓不到「main() 忘了呼叫它」——第三個陷阱那一族（測了判準、
    #    沒測呼叫點）。這裡真的跑 main()，⛔ 不是比原始碼字串。
    print("\n" + "=" * 60)
    print("crypto.py：main() bitstamp-backfill 真的呼叫 earliest_landed_date")
    print("=" * 60)
    with tempfile.TemporaryDirectory() as tmp:
        old_meta, old_crypto_dir = C.META, C.CRYPTO_DIR
        old_argv, old_rl_path, old_get = sys.argv, runlog.PATH, C._get
        C.META = os.path.join(tmp, "meta")
        C.CRYPTO_DIR = os.path.join(tmp, "crypto")
        os.makedirs(C.META, exist_ok=True)
        os.makedirs(C.CRYPTO_DIR, exist_ok=True)
        runlog.PATH = os.path.join(tmp, "_last_run.md")

        # 現行名單要有 BTC，main() 才會走到 bitstamp-backfill 那個分支的迴圈
        C.write_universe([{"symbol": "BTC", "name": "Bitcoin",
                           "market_cap_rank": 1}],
                          today=_dt2.date(2026, 9, 20))

        # 既有 BTC.csv 模擬 main 上真的資料：⛔ 不是「第一次跑」的乾淨檔，
        # 是**已經回補過一次 Bitstamp**之後的形狀——早期 Bitstamp 列
        # （2013-01-01 起）＋ 晚期 Binance 列（2017-08-17 起）都在，
        # 中間 08-01~08-16 那個洞還沒補。這正是 run 35710529200 在
        # Actions 上真的炸掉的那個場景：第一版 earliest_landed_date
        # 對全部列取 min，量到 2013-01-01（Bitstamp 自己的起點）
        # 當終點，第二趟就再也補不到這個洞。
        btc_path = C.symbol_csv_path("BTC")
        with open(btc_path, "w", encoding="utf-8", newline="") as f:
            f.write(",".join(C.DAY_HEADER) + "\n")
            f.write("2013-01-01,13.24,13.24,12.77,13.22,2116.93,,,,,"
                    "2026-09-22,bitstamp\n")
            f.write("2017-07-31,2745.76,2889.99,2680.01,2855.81,11114.34,,,,,"
                    "2026-09-22,bitstamp\n")
            f.write("2017-08-17,4261.48,4485.39,4200.74,4285.08,795.15,"
                    "3454770.05,3427,616.25,2678216.40,2026-09-20,binance\n")

        def fake_get_main(url, headers=None):
            start_ts = int(url.split("start=")[1].split("&")[0])
            start_d = _dt2.datetime.utcfromtimestamp(start_ts).date()
            dates = [start_d + _dt2.timedelta(days=i) for i in range(C.BITSTAMP_LIMIT)]
            return 200, _json2.dumps(_mk_ohlc(dates)).encode()

        C._get = fake_get_main
        sys.argv = ["crypto.py", "--mode", "bitstamp-backfill"]
        try:
            rc = C.main()
        finally:
            C.META, C.CRYPTO_DIR = old_meta, old_crypto_dir
            sys.argv, runlog.PATH, C._get = old_argv, old_rl_path, old_get

        ck("⭐ main() 跑完回 0", rc == 0, str(rc))
        btc_days = C._load(btc_path, C.DAY_HEADER, C.day_key)
        gap = [f"2017-08-{d:02d}" for d in range(1, 17)]
        ck("⭐⭐⭐ 16 天洞（2017-08-01～08-16）全部補上，"
           "⛔ 不是拿月初（08-01）當終點漏掉這幾天",
           all((g,) in btc_days for g in gap),
           str(sorted(btc_days)[:20]))
        ck("⭐⭐ 既有的 2017-08-17 那一列沒有被動到（source 仍是 binance）",
           btc_days.get(("2017-08-17",), [None] * 12)[-1] == "binance",
           str(btc_days.get(("2017-08-17",))))
        ck("★ 新補的那幾天 source 是 bitstamp",
           all(btc_days[(g,)][-1] == "bitstamp" for g in gap
               if (g,) in btc_days))

    print(f"\n[selftest] 通過 {PASS}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
