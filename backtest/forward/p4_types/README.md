# 前瞻紀錄：四型（PREREGP4）——單一主檔

- 持有：回測線。⛔ 只有這一份（K線分析 2026-09-14 1935 §六③：兩份等於多一個事後選用哪一份的選擇權）。
- `v0_20260911_策略線投遞.md`：策略線 09-14 20:26 投遞（Drive `1WkKh0fQ41UTBjC6uw9y7B242nSE0NRAP`，6,066 B），量測日 2026-09-11（開檔日，⚠ 不是每月第一個交易日；⛔ 不事後對齊）、data_sha 59bfa274083e、asof 2026-09-14T18:47+0800、612 檔四型全列。
  匯入方式：Drive base64 下載後與 Drive 文字檢視逐行核對；位元組數 6,066 相符；⚠ 兩行的行首空白（金融股名單續行、逐月作業「在那之前」那行）文字檢視會修剪，逐位元無法驗，其餘逐行相同。
- v1 起（2026-10-01）：每月第一個交易日收盤後由 `backtest/forward_p4.py` 在 main 上寫（記原始輸入＋型號＋`asof`／`data_sha`／`has_adj`；母體名單累積只增不減、另記 `last_seen`）。
- ⛔ 開檔後 24 個月（最早 2028-09）才第一次判定；之前只累積、只報覆蓋。

## 逐月作業（v1 起，2026-10）
- 程式 `backtest/forward_p4.py`（特徵全 import `p4_features.py`）：`python3 -m backtest.forward_p4 [--centers centers.json]`
  ⚠ 在**量測日的次一交易日收盤後**跑（那天才有進場開盤價）；⛔ 讀 `data/` ⇒ 一定在 main 上跑。同一量測日重跑不重寫（冪等）。
- 輸出：`records.csv`（每月每檔一列：13 特徵原始值＋百分位、型號、`centers_version`、`n_filled`、`has_adj`、`shares_ok`、`close`、`open_next`、`asof`、`data_sha`）、`universe.csv`（累積名單，只增不減；v0 那 612 檔 first_seen 2026-09-11 已種入）、`runlog.md`。
- 型號欄在 `--centers` 沒給之前留空（PREREGP4 v2 的中心／mu／sd 待策略線投遞）；中心到了用同一份 `records.csv` 的百分位重貼，⛔ 原始輸入不重算。
- 自測 `selftest_forward_p4.py`（暫存目錄冒煙：列數重讀、冪等、名單只增不減、次日開盤、日曆外要紅）。
