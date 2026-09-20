"""虛擬貨幣資料來源探針（只讀，不寫 data/）。

⛔ 這個開發容器對外部金融站台一律 403（跟 CLAUDE.md 第六點記的 TW 交易所
一樣，是我方閘道擋的，不是對方擋）——本機測過 api.binance.com／
data.binance.vision／fapi.binance.com／api.coingecko.com 全部
`connect_rejected`（organization policy）。⇒ 這支探針**只能在 Actions
上驗**，本機跑起來的失敗不算數。

目的：回答三個問題，⛔ 不是「能不能連上」而已（第二點：靜默失敗要講出是哪一種）：
  ① Binance 現貨 API（api.binance.com）從 Actions 的 IP 打不打得到
     ——⚠ Binance 對美國地區 IP 有法遵封鎖（451），而 GitHub-hosted
     runner 多半是美國/歐洲的雲端 IP，這是已知的高風險點，不是猜的。
  ② Binance 的歷史資料鏡像（data.binance.vision，CloudFront 服務）
     是不是走不同的封鎖規則（有時候 CDN 級的資源不擋雲端 IP）。
  ③ 排「前 15 大」需要市值排名，⛔ Binance 本身不提供市值——
     這裡用 CoinGecko 的公開 `coins/markets` 端點測通不通，
     它是免費、不需要 API key 的排名來源。
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


def main():
    # ① Binance 現貨：能不能連、會不會被地區法遵擋（451）
    s1, _ = probe("Binance ping", "https://api.binance.com/api/v3/ping")
    s2, b2 = probe("Binance server time", "https://api.binance.com/api/v3/time")
    s3, b3 = probe("Binance BTCUSDT 24hr ticker",
                    "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT")
    s4, b4 = probe("Binance BTCUSDT 近 3 天日K",
                    "https://api.binance.com/api/v3/klines"
                    "?symbol=BTCUSDT&interval=1d&limit=3")

    # ② Binance 歷史資料鏡像（CDN，走不走同一套地區封鎖不確定，實測見真章）
    s5, _ = probe("Binance vision（歷史 zip 目錄，只探測能不能連）",
                   "https://data.binance.vision/?prefix=data/spot/daily/klines/BTCUSDT/1d/")

    # ③ 市值排名來源（Binance 不提供市值，這裡另找一個免費、不用 key 的）
    s6, b6 = probe("CoinGecko 前 15 大市值（免 API key）",
                    "https://api.coingecko.com/api/v3/coins/markets"
                    "?vs_currency=usd&order=market_cap_desc&per_page=15&page=1")

    print("\n\n=== 判讀 ===")
    if s1 == 451 or s2 == 451 or s3 == 451:
        print("⛔⛔ Binance 主站回 451（法遵封鎖，Actions runner 的 IP 段被擋）"
              "⇒ 不能直接打 api.binance.com，要走 data.binance.vision"
              "或別的資料來源。")
    elif s1 == 200 and s2 == 200 and s3 == 200 and s4 == 200:
        print("✅ Binance 現貨 API 從這個環境打得通（ping／time／ticker／klines 都 200）。")
    else:
        print(f"⚠ 部分失敗，狀態碼分別是 ping={s1} time={s2} ticker={s3} klines={s4}"
              "——不是乾淨的『通』或『451』，要看上面各段的原始回應才知道是哪一種。")

    if s5 == 200:
        print("✅ data.binance.vision（歷史資料鏡像）打得通。")
    else:
        print(f"⚠ data.binance.vision 狀態碼 {s5}——若這裡也擋，"
              "歷史回補會需要另一條路（例如逐日打現貨 API 的 klines，量會大很多）。")

    if s6 == 200:
        try:
            names = [f"{c['symbol'].upper()}({c['name']})" for c in json.loads(b6)]
            print(f"✅ CoinGecko 前 15 大市值抓得到：{names}")
        except Exception as e:                                    # noqa: BLE001
            print(f"⚠ CoinGecko 回 200 但解析失敗：{e}")
    else:
        print(f"⚠ CoinGecko 狀態碼 {s6}，前 15 大市值排名需要換一個來源"
              "（例如 CoinMarketCap，但它多數端點要 API key）。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
