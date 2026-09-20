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
"""
import json
import sys
import urllib.error
import urllib.request

TIMEOUT = 20


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:                                        # noqa: BLE001
        return None, str(e).encode()


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
STABLECOIN_SYMBOLS = {"usdt", "usdc", "dai", "fdusd", "tusd", "usde", "busd"}


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
    #   （用 vision 鏡像的目錄頁測，⛔ 不打 api.binance.com——那條已知 451）
    print("\n=== 逐幣驗證 Binance 現貨有沒有 <SYM>USDT 這個交易對 ===")
    avail = {}
    for c in top15:
        sym = c["symbol"].upper()
        url = f"https://data.binance.vision/?prefix=data/spot/daily/klines/{sym}USDT/1d/"
        st, body = _get(url)
        has_files = st == 200 and b"Contents" in (body or b"") or (
            st == 200 and f"{sym}USDT-1d-".encode() in (body or b""))
        avail[sym] = (st, has_files)
        print(f"  {sym}USDT：status={st}｜看起來有檔案={has_files}")

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

    missing = [s for s, (st, ok) in avail.items() if not ok]
    if missing:
        print(f"⚠⚠ 這幾個在 Binance 現貨**沒找到** <SYM>USDT 交易對：{missing}"
              "——⛔ 不能假設市值前 15 名一定都在 Binance 上市，"
              "這幾個需要另找資料來源或跟使用者確認要不要換一個幣頂替。")
    else:
        print("✅ 前 15 大市值幣種在 Binance 現貨全部找得到 <SYM>USDT 交易對。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
