# 已封存（2026-09-09）

這個目錄是 2026-09-08 產出的 skill 更新包（`tw-technical-analysis` v2、`tw-stock-db` v2／v3）與審查回覆。
分工重訂之後（analysis 歸 K線線、報告與其他來源歸情報分析線、資料庫歸 CODE 線），**skill 一律由各線自己改，回測線只寄信到跨線信箱**，
這裡的包不再出卡、也不再更新。

裡面有幾個數字已經被 `backtest/PREREG.md` 更正三取代，**別再引用**：

- 「26 筆、24 檔」→ 資料庫線定案 **24 筆／22 檔**（`data/meta/par_change.csv`）。
- 「前 121 日～後 20 日」→ 方向反了，正確是訊號日 ∈ [T−H, T+L−1]，H、L 由各研究從參數算。
- 「< 0.55 或 > 1.8」→ 非嚴格 **≤ 0.55 或 ≥ 1.8**，且要看區間 (前一次有成交, 這一次有成交] 內有無事件。
- `backtest/results/par_change_candidates.csv` → 已刪除，改為 `results/breakpoints.csv`。
