# BTCUSDT 永續資金費：2019 段（官方 REST 補）

⭐ 由 backfill.yml mode=curated 原樣複製到 `data/meta/crypto_usdt_funding_early/`。起因：加密 C17（裁定 seq330 §三，2026-10-11）。

- 主檔 `data/crypto_funding/BTCUSDT.csv` 來自 data.binance.vision 月封存，**2020-01-01 起**（7,395 筆、每 8 小時一筆、缺口 0，到 2026-09-30）
- BTCUSDT 永續 **2019-09-10 上市**；2019-09-10 08:00 UTC ～ 2019-12-31 這段只有官方 REST `fapi/v1/fundingRate` 有 ⇒ 本檔（338 筆）
- ⛔ fapi 從 GitHub Actions 回 451 ⇒ 本機跑 build.py 一次；欄位與主檔相同（calc_time 毫秒 UTC、funding_interval_hours、last_funding_rate）
- 合併時以 calc_time 為鍵；2020-01-01 00:00 那一筆屬主檔（本檔不含）
- ⚠ 2019-09-10 以前 BTCUSDT 永續不存在 ⇒ 沒有資金費（⛔ 不是缺漏）
