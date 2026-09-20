"""虛擬貨幣（前 15 大市值，排除穩定幣）日K 收集——共用模組。

⛔ 這個開發容器對外部金融站台一律 403（我方閘道擋的，不是對方擋，
跟 CLAUDE.md 第六點記的 TW 交易所同一個問題）——所有會連網的函式
都只能在 GitHub Actions 上驗，本機跑起來的失敗不算數。

## 資料來源

- **價量歷史**：`data.binance.vision`（Binance 官方的公開歷史資料鏡像，
  CDN 服務）。⛔ **不是** `api.binance.com`——後者對這個環境的 IP 段
  回 451（法遵封鎖，2026-09-20 crypto_probe.py 實測逐字證實）。
- **市值排名**：CoinGecko `coins/markets`（免費、不需要 API key）。
  ⛔ Binance 本身不提供市值，不能拿它排「前 15 大」。

## 使用者 2026-09-20 裁定的規格

- 前 15 大 ＝ **市值排名**、**排除穩定幣**。
- **市值前 15 但幣安沒有對應 `<SYM>USDT` 交易對的幣，跳過、往後遞補**
  ——不是保留在清單裡換別的資料源（單一資料源，簡單維護）。
- **日K**，回補到 **2017 年**。

## ⛔⛔ 2026-09-20 實測踩到的坑：K 線時間戳的單位換過

`crypto_probe.py` 逐位元對過兩份真實檔案：

```
2017-08 月檔  open_time = 1502928000000       （13 碼 ⇒ 毫秒）
2026-09-19 日檔 open_time = 1789776000000000  （16 碼 ⇒ 微秒，多 1000 倍）
```

⇒ 官方在這幾年間把時間戳單位從毫秒換成微秒。⛔ 解析程式**不可以
寫死一種單位**，否則近期資料會被算出離譜的未來日期而且不會報錯
（乘除錯一個單位不會讓數字變成非數字，⇒ 靜默失敗，第二點那一族）。
⇒ `_ts_to_date()` 改用**數值量級**判斷（毫秒 ≈ 1e12、微秒 ≈ 1e15，
兩者差 1000 倍，門檻設在 1e14 中間，餘裕超過 8 個數量級），
⛔ 不是寫死某一天「從哪天起换算法」。
"""
import csv
import datetime
import io
import json
import os
import urllib.error
import urllib.request
import zipfile

TIMEOUT = 30
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
META = os.path.join(_ROOT, "meta")
CRYPTO_DIR = os.path.join(_ROOT, "crypto")

#: 上市最早的月份（BTCUSDT 在幣安現貨掛牌的月份，2026-09-20 探針實測
#  2017-08 有資料）——⛔ 只是**回補迴圈的起點**，不是每個幣都從這個月
#  開始有資料：更晚上市的幣，早期月份會 404，那是正常現象、不是錯誤，
#  見 `land_history()`。
EARLIEST_YEAR, EARLIEST_MONTH = 2017, 8


def universe_path():
    return os.path.join(META, "crypto_universe.csv")


def symbol_csv_path(symbol, root=None):
    return os.path.join(root or CRYPTO_DIR, f"{symbol}.csv")


def months_done_path():
    """月檔回補的續跑台帳。⭐ 鍵是 (代號, 年, 月)——跟官方月表那支同構。"""
    return os.path.join(META, "_crypto_months_done.csv")


UNIVERSE_HEADER = ["symbol", "name", "market_cap_rank", "asof"]
MONTHS_DONE_HEADER = ["symbol", "year", "month", "rows", "why"]

# ⭐ 讀寫一份「鍵值 CSV 判準表」這件事，official_stats.py 已經有一份
#   （`_load`/`_save`）——⛔ 四點五：同一件事只准一份實作，不要在這裡
#   再抄一份會走岔的拷貝。直接借那一份，⚠ 這裡不碰任何 TW 股票邏輯，
#   只是共用「讀成 dict／照鍵排序寫回去」這個純粹的 CSV 機制。
from official_stats import _load, _save                            # noqa: E402


def months_key(row):
    return (row[0], row[1], row[2])


def day_key(row):
    """個股（幣種）日檔的主鍵 ＝ 日期。⛔ 只有一格。"""
    return (row[0],)


def universe_key(row):
    """市值榜快照的主鍵 ＝ (代號, 抓的那一天)——⭐ 不是只有代號。

    ⛔ 只用代號當鍵會讓這份表**只保留最新一次**，看不出「這個幣是
    哪一天進榜的」；⇒ 累積型檔案（四點六）：本趟只覆蓋同一天同一個
    代號那一格，其餘原封不動。
    """
    return (row[0], row[3])


def _row_from_kline(r, asof):
    return [r["date"], r["open"], r["high"], r["low"], r["close"],
            r["volume"], r["quote_volume"], r["trades"],
            r["taker_buy_base"], r["taker_buy_quote"], asof]


def write_universe(rows, today=None):
    """把這一趟排出來的前 15 大寫進 `crypto_universe.csv`。

    ⭐ **同一天**是一個整體快照（剛好 15 檔）——同一天重跑要把那一天的
    舊列**整批**換成新的，⛔ 不是逐檔合併：2026-09-20 首次實跑就中過
    這一坑（`STABLECOIN_SYMBOLS` 漏掉 `USDS` ⇒ 誤放進第 15 名；補好
    清單後同一天重跑，若只逐檔合併，被排除的 `USDS` 那一列會留著，
    讓那一天看起來有 16 檔）。⚠ **不同天**的快照互不影響——
    那才是四點六說的「累積型」：跨天的歷史紀錄不可以被蓋掉。
    """
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    asof = today.isoformat()
    path = universe_path()
    existing = _load(path, UNIVERSE_HEADER, universe_key)
    existing = {k: v for k, v in existing.items() if k[1] != asof}
    for r in rows:
        existing[(r["symbol"], asof)] = [
            r["symbol"], r["name"], str(r["market_cap_rank"]), asof]
    _save(path, UNIVERSE_HEADER, existing)
    return path


def _month_iter(y0, m0, y1, m1):
    """[(y0,m0), …, (y1,m1) 之前一個月]——⛔ 不含 (y1,m1) 自己（那個月
    通常還沒結束，月檔還沒發布，要靠 `land_recent_days` 補）。"""
    y, m = y0, m0
    while (y, m) < (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            m = 1
            y += 1


def land_history(symbol, today=None, root=None):
    """回補一個幣種**已經結束的月份**（月檔），從 2017-08 到上個月。

    ⛔ 已經問過的月份（不論成功或「官方 404＝這個月沒有」）都記進
    `_crypto_months_done.csv`，⛔ 不重問——不然過去的月份不會變，
    每一趟都白問一次；⚠ 而**真的失敗**（不是 404 的錯誤）不記進 done，
    讓下一趟自然重試（跟 official_stats 的 sweep 台帳同一個道理）。
    """
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    dp = months_done_path()
    done = _load(dp, MONTHS_DONE_HEADER, months_key)
    csvp = symbol_csv_path(symbol, root)
    days = _load(csvp, DAY_HEADER, day_key)
    n0 = len(days)
    asof = today.isoformat()
    ok = fail = skipped = nodata = 0
    for y, m in _month_iter(EARLIEST_YEAR, EARLIEST_MONTH, today.year, today.month):
        k = months_key([symbol, str(y), str(m)])
        if k in done:
            skipped += 1
            continue
        rows, err = fetch_zip_rows(monthly_url(_pair(symbol), y, m))
        if err == "404":
            done[k] = [symbol, str(y), str(m), "0", "nodata"]
            nodata += 1
        elif err:
            fail += 1                       # ⛔ 真的失敗，不記進 done
        else:
            for r in rows:
                days[day_key([r["date"]])] = _row_from_kline(r, asof)
            done[k] = [symbol, str(y), str(m), str(len(rows)), ""]
            ok += 1
    _save(csvp, DAY_HEADER, days)
    _save(dp, MONTHS_DONE_HEADER, done)
    return {"ok": ok, "fail": fail, "skipped": skipped, "nodata": nodata,
            "new_rows": len(days) - n0}


def land_recent_days(symbol, today=None, root=None, lookback=35):
    """補**還沒結束的當月**與最近幾天（月檔要等月底才發布）。

    ⛔ 不記續跑台帳——這一段本來就每天都要重新掃一次缺口
    （官方偶爾會補發前幾天漏掉的日檔，逐日檢查比較保險，
    ⚠ 而 `lookback=35` 給的餘裕夠蓋過一整個月，成本只是幾十次
    HEAD 等級的小請求，賠得起）。
    """
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    csvp = symbol_csv_path(symbol, root)
    days = _load(csvp, DAY_HEADER, day_key)
    n0 = len(days)
    asof = today.isoformat()
    ok = fail = 0
    for i in range(1, lookback + 1):
        d = today - datetime.timedelta(days=i)
        if day_key([d.isoformat()]) in days:
            continue
        rows, err = fetch_zip_rows(daily_url(_pair(symbol), d))
        if err:
            if err != "404":
                fail += 1
            continue
        for r in rows:
            days[day_key([r["date"]])] = _row_from_kline(r, asof)
        ok += 1
    _save(csvp, DAY_HEADER, days)
    return {"ok": ok, "fail": fail, "new_rows": len(days) - n0}

#: ⛔⛔ 2026-09-20 首次跑 `--mode universe` 就抓到自己的坑：這份手寫清單
#  漏掉了 `USDS`（Sky／原 MakerDAO 的美元穩定幣，2024 年才改名上市），
#  結果它混進了「前 15 大」的第 15 名——⚠ 手寫清單**必然**會漏掉之後
#  才出現的穩定幣，不是補一個名字就會好（第三點：只比一個方向就宣告
#  一致；這裡是「清單裡沒有 ⇒ 我以為代表『不是穩定幣』」的同一個錯）。
#  ⇒ 這份**只當最後一道防線**（CoinGecko 分類抓不到時的退路），
#  正式判準改成 `stablecoin_symbols()`——動態抓 CoinGecko 官方
#  「stablecoins」分類，⛔ 不要再手動維護會過期的清單。
#  ⭐ 這是唯一一份底線清單——crypto_probe.py 從這裡 import。
STABLECOIN_SYMBOLS = {"usdt", "usdc", "dai", "fdusd", "tusd", "usde", "busd", "usds"}

VISION_BASE = "https://data.binance.vision/data/spot"
COINGECKO_MARKETS = ("https://api.coingecko.com/api/v3/coins/markets"
                     "?vs_currency=usd&order=market_cap_desc&per_page={n}&page=1")
#: CoinGecko 官方「穩定幣」分類——⛔ 不能只認 `vs_currency=usd`，
#  分類本身才是「這是不是穩定幣」的官方判準，不是我方用價格猜的。
COINGECKO_STABLECOINS = ("https://api.coingecko.com/api/v3/coins/markets"
                        "?vs_currency=usd&category=stablecoins"
                        "&order=market_cap_desc&per_page=250&page=1")

#: klines 原始 12 欄的意義（照官方文件順序，⛔ 不要用名字猜位置）。
#  最後一欄「ignore」官方說不用管——2026-09-20 實測它在新舊檔案裡
#  逐位的內容不一致（舊檔非 0、新檔是 0），⇒ 這裡直接不落地那一欄，
#  不對它做任何假設。
KLINE_FIELDS = ("open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades",
                "taker_buy_base", "taker_buy_quote", "ignore")

#: 落地的日檔欄位（⛔ 只有一份，backfill／daily 兩條路都寫這個表頭）。
DAY_HEADER = ["date", "open", "high", "low", "close", "volume",
              "quote_volume", "trades", "taker_buy_base", "taker_buy_quote",
              "asof"]


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:                                        # noqa: BLE001
        return None, str(e).encode()


def _ts_to_date(raw):
    """K 線時間戳（毫秒或微秒，量級自動判斷）→ `datetime.date`（UTC）。

    ⛔ 見檔頭那段：不可以寫死一種單位。門檻 1e14 離兩種真實量級
    （毫秒 ~1.5e12、微秒 ~1.8e15）都差好幾個數量級，不會誤判。
    """
    v = int(raw)
    if v >= 10 ** 14:
        v //= 1000                                # 微秒 → 毫秒
    return datetime.datetime.utcfromtimestamp(v / 1000).date()


def parse_kline_csv(text):
    """klines CSV 原始文字 → `[{date, open, high, low, close, volume,
    quote_volume, trades, taker_buy_base, taker_buy_quote}, ...]`。

    ⛔ 逐列至少要有 11 欄才收（第 12 欄「ignore」不落地，見檔頭）；
    ⚠ 而且要先看第一列**是不是表頭**（第一格不是數字就跳過那一列）
    ——2026-09-20 實測到的兩個真實樣本都沒有表頭，⛔ 但不能因此就
    假設「以後也不會有」，這道判斷不貴、留著。
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    first_cell = lines[0].split(",", 1)[0].strip()
    if not first_cell.lstrip("-").replace(".", "", 1).isdigit():
        lines = lines[1:]
    rows = []
    for ln in lines:
        c = ln.split(",")
        if len(c) < 11:
            continue
        rows.append({
            "date": _ts_to_date(c[0]).isoformat(),
            "open": c[1], "high": c[2], "low": c[3], "close": c[4],
            "volume": c[5], "quote_volume": c[7], "trades": c[8],
            "taker_buy_base": c[9], "taker_buy_quote": c[10],
        })
    return rows


def _unzip_first_csv(zip_bytes):
    """zip 的 bytes → 裡面第一個檔案的文字內容。⛔ 不是 zip 就丟例外。"""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        name = z.namelist()[0]
        return z.read(name).decode("utf-8", "replace")


def _pair(symbol):
    """我方存的是**現貨基礎資產代號**（`BTC`），幣安的交易對是 `BTCUSDT`
    ——⛔⛔ 2026-09-20 第一趟實跑 backfill 就中這個坑：`land_history`／
    `land_recent_days` 當時直接把 `symbol` 傳給 `monthly_url`／`daily_url`
    （沒加 USDT），15 幣 × 109 個月**全部 404**，而 runlog 把它顯示成
    「官方沒有」——看起來像正常的『這個月沒資料』，其實是**打錯網址**。
    ⚠ `binance_pair_exists()` 當時就有補這個字尾（沒中招），但
    `monthly_url`／`daily_url` 的呼叫端沒有跟著做——四點五那一族：
    「我方符號→交易對」這個轉換一個地方做對、另一個地方漏掉。
    ⇒ 收成**一份**，兩邊都改呼叫這個函式，⛔ 不要各自兜字尾。
    """
    return f"{symbol}USDT"


def monthly_url(pair, year, month):
    """⚠ `pair` 是**幣安的交易對名稱**（如 `BTCUSDT`），不是我方代號
    ——呼叫端要先過 `_pair()`。"""
    return f"{VISION_BASE}/monthly/klines/{pair}/1d/{pair}-1d-{year:04d}-{month:02d}.zip"


def daily_url(pair, date):
    """⚠ 同上，`pair` 已經是幣安交易對名稱。"""
    return f"{VISION_BASE}/daily/klines/{pair}/1d/{pair}-1d-{date.isoformat()}.zip"


def fetch_zip_rows(url):
    """打一個 klines zip 網址 → `(rows, err)`。

    ⛔ 三種失敗要分得出來（第二點：靜默失敗要講出是哪一種）：
      ① 404（那個月／那一天官方沒有——可能是幣還沒上市、也可能是還沒發布）
      ② 200 但不是 zip（⚠ 目錄頁或錯誤頁偽裝成 200，先前 probe 就中過一次）
      ③ 200 且是 zip，但解壓縮/解析失敗
    """
    status, body = _get(url)
    if status == 404:
        return None, "404"
    if status != 200:
        return None, f"status={status}"
    if (body or b"")[:2] != b"PK":
        return None, "200 但不是 zip（⛔ 可能是偽裝成 200 的錯誤頁）"
    try:
        text = _unzip_first_csv(body)
    except Exception as e:                                        # noqa: BLE001
        return None, f"解壓縮失敗：{e}"
    return parse_kline_csv(text), None


def binance_pair_exists(symbol, today=None, lookback_days=3):
    """`<symbol>USDT` 這個交易對在幣安現貨是不是真的有日K ⇒ bool。

    ⛔ 不比目錄頁的字串（crypto_probe.py 2026-09-20 訂正過的坑）——
    直接試下載最近幾天的日檔，200 且是真的 zip 才算數。
    """
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    for d in (today - datetime.timedelta(days=n) for n in range(1, lookback_days + 1)):
        status, body = _get(daily_url(_pair(symbol), d))
        if status == 200 and (body or b"")[:2] == b"PK":
            return True
    return False


def stablecoin_symbols():
    """→ `(set_of_lowercase_symbols, err)`。

    ⭐ 正式判準：CoinGecko 官方「stablecoins」分類——⛔ 不是我方手寫、
    會過期的清單（2026-09-20 首次實跑就漏掉 `USDS`，見 `STABLECOIN_SYMBOLS`
    上面那段記錄）。⚠ 而動態抓取本身也會失敗（端點掛掉／改格式），
    ⇒ 失敗時回傳**手寫清單當底線**＋非 None 的 `err`（六點五：條件不成立
    就大聲講「這一層沒跑」、退回舊判準，⛔ 不是當作沒事發生）；
    **成功時回傳「官方分類 ∪ 手寫底線」**——多一層保險，不是互斥。
    """
    status, body = _get(COINGECKO_STABLECOINS)
    if status != 200:
        return STABLECOIN_SYMBOLS, f"CoinGecko 穩定幣分類 status={status}（已退回手寫底線清單）"
    try:
        coins = json.loads(body)
        official = {c["symbol"].lower() for c in coins}
    except Exception as e:                                        # noqa: BLE001
        return STABLECOIN_SYMBOLS, f"CoinGecko 穩定幣分類解析失敗：{e}（已退回手寫底線清單）"
    return official | STABLECOIN_SYMBOLS, None


def top15_symbols(today=None, candidate_pool=100):
    """→ `(rows, err, sc_warn)`。`rows` 每筆 `{symbol, name, market_cap_rank}`。

    ⭐ 使用者 2026-09-20 裁定：市值前 15、排除穩定幣、
    **幣安沒有交易對的跳過、往後遞補**——⛔ 不是保留在清單裡換資料源。
    ⚠ `sc_warn` 非 None ⇒ 動態穩定幣分類抓取失敗、退回手寫底線清單
    （見 `stablecoin_symbols()`）——⛔ 不是失敗，但呼叫端要**講出來**，
    不能悄悄吞掉（六點五：條件不成立就大聲印，不算失敗）。
    """
    stablecoins, sc_warn = stablecoin_symbols()
    status, body = _get(COINGECKO_MARKETS.format(n=candidate_pool))
    if status != 200:
        return None, f"CoinGecko status={status}", sc_warn
    try:
        coins = json.loads(body)
    except Exception as e:                                        # noqa: BLE001
        return None, f"CoinGecko 回應解析失敗：{e}", sc_warn
    out = []
    for c in coins:
        if c["symbol"].lower() in stablecoins:
            continue
        sym = c["symbol"].upper()
        if not binance_pair_exists(sym, today):
            continue
        out.append({"symbol": sym, "name": c["name"],
                    "market_cap_rank": c.get("market_cap_rank")})
        if len(out) == 15:
            break
    if len(out) < 15:
        return None, (f"CoinGecko 前 {candidate_pool} 大濾完穩定幣、"
                      f"再濾完幣安沒有的，只湊到 {len(out)} 個"), sc_warn
    return out, None, sc_warn


def current_symbols():
    """→ 目前這一批前 15 大的代號 list（⛔ 沒有清單就回空的，不猜）。

    ⭐ 「現行清單」＝ `crypto_universe.csv` 裡 **asof 最新那一天** 的那 15 列
    ——⛔ 這份表本身是累積型（四點六），不是每次重寫，讀的時候要自己
    挑出最新那一批，不是整份都當現行名單。
    """
    rows = _load(universe_path(), UNIVERSE_HEADER, universe_key)
    if not rows:
        return []
    latest = max(r[3] for r in rows.values())
    return sorted(r[0] for r in rows.values() if r[3] == latest)


def main():
    import argparse
    import runlog

    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=("universe", "backfill", "daily"))
    a = ap.parse_args()
    today = datetime.datetime.now(datetime.timezone.utc).date()

    if a.mode == "universe":
        rl = runlog.Run("crypto:universe")
        rl.info("這一趟", "重新排前 15 大市值（排除穩定幣、幣安要有 <SYM>USDT 交易對）")
        rows, err, sc_warn = top15_symbols(today)
        if sc_warn:
            rl.info("⚠ 這一層沒跑", f"動態穩定幣分類抓取失敗，退回手寫底線清單：{sc_warn}")
        if err:
            rl.info("⛔ 失敗", err)
            rl.check("排出前 15 大", False, err)
            rl.finish()
            return 1
        write_universe(rows, today)
        names = [f"{r['symbol']}({r['name']})" for r in rows]
        rl.info("結果", "、".join(names))
        rl.check("排出前 15 大", len(rows) == 15, f"實際 {len(rows)} 個")
        rl.finish()
        return 0

    symbols = current_symbols()
    if not symbols:
        print("⛔ 還沒有 crypto_universe.csv，先跑 --mode universe")
        return 1

    if a.mode == "backfill":
        rl = runlog.Run("crypto:backfill")
        rl.info("這一趟", f"回補歷史月檔（2017-{EARLIEST_MONTH:02d} 起）｜{len(symbols)} 個幣種")
        totals = {"ok": 0, "fail": 0, "skipped": 0, "nodata": 0, "new_rows": 0}
        detail = []
        for sym in symbols:
            r = land_history(sym, today=today)
            for k in totals:
                totals[k] += r[k]
            detail.append(f"{sym}：+{r['new_rows']} 列（成功 {r['ok']}／"
                          f"官方沒有 {r['nodata']}／失敗 {r['fail']}／略過 {r['skipped']}）")
        rl.info("逐幣", "；".join(detail))
        rl.info("合計", f"新增 {totals['new_rows']:,} 列｜成功 {totals['ok']}｜"
                       f"官方沒有 {totals['nodata']}｜失敗 {totals['fail']}｜"
                       f"略過（已完成）{totals['skipped']}")
        rl.check("本趟不是全失敗", totals["ok"] > 0 or totals["fail"] == 0,
                 f"成功 {totals['ok']}｜失敗 {totals['fail']}")
        rl.finish()
        return 0

    # a.mode == "daily"
    rl = runlog.Run("crypto:daily")
    rl.info("這一趟", f"補當月與最近日檔缺口｜{len(symbols)} 個幣種")
    totals = {"ok": 0, "fail": 0, "new_rows": 0}
    detail = []
    for sym in symbols:
        r = land_recent_days(sym, today=today)
        for k in totals:
            totals[k] += r[k]
        detail.append(f"{sym}：+{r['new_rows']} 列")
    rl.info("逐幣", "；".join(detail))
    rl.info("合計", f"新增 {totals['new_rows']:,} 列｜成功 {totals['ok']}｜失敗 {totals['fail']}")
    rl.check("本趟不是全失敗", totals["ok"] > 0 or totals["fail"] == 0,
             f"成功 {totals['ok']}｜失敗 {totals['fail']}")
    rl.finish()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
