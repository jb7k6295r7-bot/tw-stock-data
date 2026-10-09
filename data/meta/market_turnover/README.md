# 大盤每日成交量值（官方總額口徑）

⭐ 由 backfill.yml mode=curated 原樣複製到 `data/meta/market_turnover/`。起因：台股 1009-1542 §五 ④（R2 連動門檻要大盤成交金額）。

| 檔 | 來源 | 起訖 | 單位 | 口徑 |
|---|---|---|---|---|
| twse_market_turnover.csv | TWSE `afterTrading/FMTQIK`（月一發） | 1990-01-04 ～ 2026-10-08，9,437 天 | 股數／元／筆 | ⭐ 含大盤、零股、盤後定價、鉅額（官方 notes） |
| tpex_market_turnover.csv | TPEx `afterTrading/tradingIndex`（月一發） | 2007-04-02 ～ 2026-10-08，4,799 天 | 仟股／仟元／筆 | 上櫃股票（含零股與定價、不含鉅額；同 calendar_tpex） |

欄位：twse＝date, volume_shares, amount_ntd, transactions, taiex, change｜tpex＝date, volume_k, amount_k_ntd, transactions, tpex_index, change
⚠ 上櫃 2015 年量欄名「成交股數（仟股）」、2026 年「成交張數」⇒ 數值單位相同（仟股＝張）

## 驗收（2026-10-09）
- twse 日期集合＝data/history/market_index.csv（1990 起）逐日相同；taiex 欄對 market_index close 0 筆不符
- tpex 2015 起日期集合＝calendar_twse 逐日相同
- 抽 2015-01-05、2026-09-01、2026-10-07：twse 81,345,264,521／1,187,571,567,117／986,280,041,197 元；tpex 21,033,444／252,387,965／297,728,502 仟元（與官方頁一致；tpex 9/01 ＝ calendar_tpex 252,387,964,702 元）

## ⛔ 讀法
- ⛔ 不要用我方日檔 `amount` 加總代替：上市日檔不含權證（Σ≈FMTQIK×0.996，比值隨權證占比漂）、上櫃日檔只有一般交易（不含零股）
- ⛔ 不要併進 data/history/market_amount.csv：那是 MI_INDEX「1.一般股票」口徑（2026-09-01 起），兩者差約 8%
- 此檔為一次回補；之後每日要累積時另接 daily（目前尚未接）⇒ 用到最近日期前先看 max(date)
