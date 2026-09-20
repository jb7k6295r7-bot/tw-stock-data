"""虛擬貨幣資料來源探針（只讀，不寫 data/）。

⛔ 這個開發容器對外部金融站台一律 403（跟 CLAUDE.md 第六點記的 TW 交易所
一樣，是我方閘道擋的，不是對方擋）——本機測過 api.binance.com／
data.binance.vision／fapi.binance.com／api.coingecko.com 全部
`connect_rejected`（organization policy）。⇒ 這支探針**只能在 Actions
上驗**，本機跑起來的失敗不算數。

⭐ 2026-09-20 第一輪已經打過 api.binance.com（ping／time／ticker／klines），
四個全部 451「restricted location」——跟猜的一樣，Actions runner 的
IP 段被 Binance 法遵封鎖擋掉，⛔ 這條路死了，第二輪不重打。

這一輪回答的問題：
  ① `data.binance.vision`（歷史資料鏡像，CloudFront 服務）**真的下載得到
     資料檔**，不只是目錄頁 200——目錄頁通不代表檔案本體通得過同一道封鎖。
     ⭐ 順便驗 2017 年的月檔在不在（使用者要求回補到 2017）。
  ② CoinGecko 抓前 30 大市值、濾掉穩定幣後湊出前 15 大（使用者裁定：
     市值排名、排除穩定幣）。
  ③ 這 15 個幣種是不是每一個在 Binance 現貨都有 `<SYM>USDT` 交易對
     ——⛔ 不能假設「市值前 15」跟「Binance 上市的前 15」是同一組。

⛔⛔ 2026-09-20 第二輪自己踩到一個坑（記下來，⛔ 不要重犯）：第一版
「逐幣驗證」用 `?prefix=...` 的目錄頁去猜有沒有檔案，比對字串
`b"Contents"`——⚠ 而那個網址回的是**空殼 HTML 外殼**（JS 前端頁面，
真正的檔案清單是前端另外發 XHR 才拿到的），⛔ 不是原始的 S3 XML 清單。
⇒ 連**已經證實下載得到 zip**的 BTCUSDT 都被判成「沒有檔案」——
第二點那句「靜默失敗要講出是哪一種」，這次連自己寫的探針都中了同一招。
⇒ 改法：**直接試下載一個一定存在的近期日檔**（用昨天的 UTC 日期，
抓不到就退一天再試），200 才算數、⛔ 不比目錄頁的字串。

⛔ 2026-09-20 補：`crypto.py` 寫完之後才發現 `_get()` 與
`STABLECOIN_SYMBOLS` 在這裡跟那邊各有一份逐字相同的拷貝——
`selftest_no_dup.py` 沒抓到是因為 `_get` 只有 2 個 statement（低於
MIN_STMTS）、`STABLECOIN_SYMBOLS` 是 `set` 常數（`scan_consts` 當時
只認 list／tuple）。⇒ 兩處都改成從 `crypto.py` import（四點五：
同一件事只准一份實作），並把 `scan_consts` 補上 `ast.Set`。
"""
import datetime
import io
import json
import sys

from crypto import STABLECOIN_SYMBOLS, _get                        # noqa: F401


def _peek_kline_csv(zip_bytes, label):
    """解開一個 klines zip，印出**真正的欄位長什麼樣**——⛔ 不要用猜的。

    已知 Binance 在某個時間點把 daily klines 的 CSV 從「純數字、無表頭」
    改成「第一列是表頭文字」——兩種格式混著解析會把表頭那一列當成一筆
    假資料，或者把真資料的第一欄當成表頭跳過。⇒ 這裡直接印出來看，
    不要靠記憶或猜測。
    """
    print(f"\n--- {label}：解開 zip 看真正的 CSV 內容 ---")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = z.namelist()
            print(f"zip 內的檔案：{names}")
            with z.open(names[0]) as f:
                lines = f.read().decode("utf-8", "replace").splitlines()
    except Exception as e:                                        # noqa: BLE001
        print(f"⛔ 解壓縮或讀取失敗：{e}")
        return
    print(f"總行數：{len(lines)}")
    for i, ln in enumerate(lines[:3]):
        cols = ln.split(",")
        print(f"  第 {i+1} 行（{len(cols)} 欄）：{ln}")
    if lines:
        first_cell = lines[0].split(",")[0].strip()
        looks_like_header = not first_cell.lstrip("-").replace(".", "", 1).isdigit()
        print(f"⇒ 第一列第一格是 {first_cell!r}，"
              f"{'看起來像表頭文字' if looks_like_header else '看起來是數字（無表頭）'}")


def probe(label, url, headers=None):
    print(f"\n=== {label} ===")
    print(f"URL: {url}")
    status, body = _get(url, headers)
    print(f"status: {status}")
    snippet = body[:300] if isinstance(body, (bytes, bytearray)) else body
    try:
        snippet = snippet.decode("utf-8", "replace")
    except Exception:                                             # noqa: BLE001
        pass
    print(f"body[:300]: {snippet!r}")
    return status, body


#: 2026-09-20 第一輪探針已證實 api.binance.com 全面 451（法遵封鎖，
#  訊息逐字是「restricted location」）——這輪不重打，省一輪配額。
#: 使用者裁定：前 15 大＝市值排名、排除穩定幣、日K、回補到 2017。
#  （`STABLECOIN_SYMBOLS` 從 `crypto` import，見檔頭補記——不在這裡重寫。）


def main():
    # ② Binance 歷史資料鏡像：光有目錄頁通不代表真的抓得到檔案——
    #   這次追加抓**一個真的月檔**（monthly，比 daily 檔小很多的那種也試）
    #   跟 2017 年那個月，直接驗證「回補到 2017」這個需求做不做得到。
    s5a, _ = probe("Binance vision｜BTCUSDT 2017-08 月檔清單（驗 2017 年有沒有資料）",
                    "https://data.binance.vision/?prefix="
                    "data/spot/monthly/klines/BTCUSDT/1d/")
    s5b, b5b = probe("Binance vision｜BTCUSDT 2017-08 月檔本體（真的下載一個檔）",
                       "https://data.binance.vision/data/spot/monthly/klines/"
                       "BTCUSDT/1d/BTCUSDT-1d-2017-08.zip")
    if s5b == 200:
        _peek_kline_csv(b5b, "2017-08（舊）月檔")
    s5c, _ = probe("Binance vision｜昨天的日檔清單（驗每日更新的時效）",
                    "https://data.binance.vision/?prefix="
                    "data/spot/daily/klines/BTCUSDT/1d/")

    # ③ 市值排名來源（Binance 不提供市值，這裡另找一個免費、不用 key 的）
    #   多抓一點（30 筆）才夠濾掉穩定幣還留 15 個。
    s6, b6 = probe("CoinGecko 前 30 大市值（免 API key，濾穩定幣後才夠 15 個）",
                    "https://api.coingecko.com/api/v3/coins/markets"
                    "?vs_currency=usd&order=market_cap_desc&per_page=30&page=1")

    top15 = []
    if s6 == 200:
        try:
            coins = json.loads(b6)
            for c in coins:
                if c["symbol"].lower() in STABLECOIN_SYMBOLS:
                    continue
                top15.append(c)
                if len(top15) == 15:
                    break
        except Exception as e:                                    # noqa: BLE001
            print(f"⚠ 解析 CoinGecko 回應失敗：{e}")

    # ④ 逐一驗證這 15 個幣種在 Binance 現貨有沒有 USDT 交易對
    #   ⛔ 不比目錄頁的字串（見檔頭那段訂正）——直接試下載一個近期日檔，
    #   200 才算數；抓不到就往前找幾天（有些交易所日檔會晚一兩天才發布）。
    print("\n=== 逐幣驗證 Binance 現貨有沒有 <SYM>USDT 這個交易對 ===")
    today = datetime.datetime.now(datetime.timezone.utc).date()
    candidate_dates = [today - datetime.timedelta(days=d) for d in (1, 2, 3)]
    avail = {}
    for c in top15:
        sym = c["symbol"].upper()
        hit = None
        for d in candidate_dates:
            url = (f"https://data.binance.vision/data/spot/daily/klines/"
                   f"{sym}USDT/1d/{sym}USDT-1d-{d.isoformat()}.zip")
            st, body = _get(url)
            if st == 200 and (body or b"")[:2] == b"PK":   # 真的是 zip 檔頭
                hit = (st, d.isoformat())
                if sym == "BTC":
                    _peek_kline_csv(body, f"{d.isoformat()}（新）日檔")
                break
        avail[sym] = hit is not None
        if hit:
            print(f"  {sym}USDT：✅ {hit[1]} 那天的日檔抓得到（zip 檔頭確認）")
        else:
            print(f"  {sym}USDT：⛔ 近 3 天都抓不到日檔（最後一次 status={st}）")

    print("\n\n=== 判讀 ===")
    print("⛔⛔ 上一輪已證實 api.binance.com 全面 451（法遵封鎖，"
          "訊息逐字是 restricted location）⇒ 現貨 REST API 這條路死了，"
          "不管 ping／klines／哪個端點都一樣，⛔ 不用再測。")

    if s5b == 200:
        print("✅✅ data.binance.vision 的月檔**真的下載得到**"
              "（2017-08 那個月檔 200）⇒ 回補到 2017 年做得到。")
    elif s5a == 200:
        print("⚠ 目錄頁通但月檔本體沒抓到（見上面 s5b 那段的原始回應），"
              "要確認是不是檔名／路徑猜錯，而不是整條路不通。")
    else:
        print(f"⛔ data.binance.vision 連目錄頁都不通（{s5a}），"
              "回補到 2017 這個需求要重新找路。")
    print(f"⚠ 昨天的日檔目錄頁 status={s5c}"
          "（用來判斷『每天更新』這件事能不能靠它做，不是只能靠歷史月檔）。")

    if top15:
        names = [f"{c['symbol'].upper()}({c['name']})" for c in top15]
        print(f"✅ 前 15 大市值（已排除穩定幣）：{names}")
    else:
        print("⛔ 沒能湊出 15 個非穩定幣，看上面 CoinGecko 那段原始回應。")

    missing = [s for s, ok in avail.items() if not ok]
    if missing:
        print(f"⚠⚠ 這幾個在 Binance 現貨**沒找到** <SYM>USDT 交易對：{missing}"
              "——⛔ 不能假設市值前 15 名一定都在 Binance 上市，"
              "這幾個需要另找資料來源或跟使用者確認要不要換一個幣頂替。")
    else:
        print("✅ 前 15 大市值幣種在 Binance 現貨全部找得到 <SYM>USDT 交易對。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
