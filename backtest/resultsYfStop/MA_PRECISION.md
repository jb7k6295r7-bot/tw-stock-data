# 均線精度回查：yfstop_lines.ma_valid（cumsum 相減式）對已交件的影響

產出 2026-09-27（台北）。回測線。程式 `backtest/ma_precision.py`；數字取自 `ma_precision_summary.json`、`ma_precision_lines.csv`。
⛔ 只數線、沒跑引擎、沒算報酬。

## 結論：已查，零影響，結案

用到 `ma_valid` 的已交件，重建出來的每一條 M20／M50 線，觸發日全部不變：舊式和 fsum 版比出來 0 條會變、0 個部位受影響。
不止觸發日：兩式算出的均線值本身也逐位元相同（全序列約 495 萬根，0 根不同）。⇒ `yfstop_lines.ma_valid` 不必改、已交的臂不必重跑、已判的標籤不動。

## 一、用到 ma_valid 的已交件（arm＝state）

| 已交件 | 用到的線 | 用的訊號表 |
|---|---|---|
| researchYfStop（PREREG營飆停損） | M20、M50 主版（判定）、ⓐ 整份、ⓑ 跌停賣不掉 | 營飆 v1（listexit_lines.setup_t1） |
| researchYfStop ⓓ 補股池 | d_M20、d_M50 | 補股池 yfstop_lines.pool_rows |
| researchYfV2（營飆 v2 候選） | 候選一（M20 整份 ＝ 營飆停損 M20 ⓐ）；C1 的觸發根分佈取自候選一；C2 引用 M20 主版 | 營飆 v1 |
| researchV（早年段驗收） | v2 候選那一格會用 M20 線；⚠ 目前只到 pre 段，⛔ 還沒建過線 | — |

其他形式相同、但【不是】ma_valid 的（⛔ 不在本次範圍，只列出來）：
- `researchc1.sma`（PREREGC1 加密 SMA 濾網）也是 cumsum 相減式；它用的是別的資料，本次沒查。
- 許多研究用 pandas `rolling().mean()`，例如 `research11.regime_below` 的 0050 均線，這是另一種累加法；本次也沒查。

## 二、逐條比對觸發日（fsum 版 vs 舊式；觸發日 ＝ yfstop_lines.first_trigger，和引擎同一式）

| 批 | 線 | 線數 | 觸發日會變的線 | 涉及檔數 | 有任一天「收盤 ＜ 線」翻轉的線 |
|---|---|---|---|---|---|
| 營飆 v1 | M20 | 1,688 | 0 | 0 | 0 |
| 營飆 v1 | M50 | 1,688 | 0 | 0 | 0 |
| ⓓ 補股池 | M20 | 10,312 | 0 | 0 | 0 |
| ⓓ 補股池 | M50 | 10,312 | 0 | 0 | 0 |

訊號列：營飆 v1 2,036 列、補股池 13,370 列（xpos < 0 的不建線，和原件一樣）。`ma_precision_lines.csv` 是 0 列。

## 三、為什麼是零：引擎用的收盤是 float32 值

`rerun17.load_prices` 給引擎的 closes dtype 是 **float32**，有效位數只有 24 bit。
⇒ 在這批價格的量級內，float64 的 cumsum 和相減都沒有捨入，(cs[n:] − cs[:-n])／n 就等於「和先正確捨入一次再除」，也就是 fsum 版。

| 價格來源 | 檔數 | 比較根數（M20＋M50） | 均線值逐位元不同 | 「收盤 ＜ 均線」翻轉 |
|---|---|---|---|---|
| 引擎的 closes（float32；營飆 v1 ∪ 補股池全部檔、全部有效 K 棒） | 929 | 4,948,358 | 0 | 0 |
| 對照：researchAvg.prep 的 float64 還原價（營飆 v1 前 300 檔） | 300 | 1,671,680 | — | 654 |

對照組證明偵測是分得出來的：換成 float64 還原價，也就是 PREREG四類單獨用的那一套，同一個比法抓到 654 次翻轉。
這正是四類單獨查核抓到的問題（實例 1102、1301）；那一件已經改用 fsum，交件前查核全過。

## 四、給之後的呼叫端

`ma_valid` 只在輸入是 float32 值的時候才精確。之後若有人拿 float64 還原價餵它，例如直接用 `D.load_stock` 或 `researchAvg.prep` 的收盤，「恰等於均線」會被誤判。
⇒ 那時請改用 fsum 版。
researchV 早年段的 M20 線若沿用 rerun17.load_prices 的 float32 closes，就同樣是零影響；開跑前要再確認一次它的價格來源。
