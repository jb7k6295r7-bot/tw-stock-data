# 飆股回推 交接清單（回測線 → seq5 新子代理）

寫於 2026-09-29（台北）。⛔ 本檔不含任何結果數字或特徵名次。
seq4 的分析結果已移到 `backtest/resultsSurge/_seq4_seen/`，⛔ 新子代理不要讀。

## 一、可沿用的程式（都在 `~/tw-p17/backtest/`）

- `surge_features.py`：特徵庫模組，可 import，以 seq4 口徑寫成。
  - `world(tag)`：載入一個世界。「主」＝ main b53f5540a8 的唯讀 archive；「早年」＝ 早年版面，只有上市。
    載入內容：日曆、gate3（innov_ky 開）、W1 eligible 面板、月營收（早年＋main 接起來）、rev_hi24 旗標、0050 的 200 日線、產業、財報 A2、借券、注意、處置。
  - `stock()`：逐檔計算特徵原值、標籤、後續報酬。
  - `table()`：多行程組出整張特徵表。
  - `cross()`：當日五等分、產業排名、基準②。
  - `tdcc_feature()`：集保 400 張以上大戶 4 週變化。
    - 級數用資料庫 `tdcc.py` 抽出來的 `level_of` 原文。
    - 需要 pyarrow，已裝在 tw-p16 venv。
  - `FEATS`、`LVL`、`level_col()`：特徵清單與級距碼。
  - ⚠ 與 seq5 不同的地方，要改：
    - 母體：seq4 用 W1 eligible；seq5 不用 W1、不用處置閘。
    - 回看期：seq4 每個特徵固定一個；seq5 要 5／10／20／60／120／250 全列。
    - 門檻型特徵：seq4 是二元；seq5 要改成連續值五等分。
    - 飆股：seq4 固定 F1／F2／F3；seq5 是網格，H 10～250 × g 照裁定 seq277。
    - 壞根處理：seq4 標籤窗內有壞根就剔除，壞根含「≥5 日缺口」；seq5 規定「含停牌前後」，要重新決定。
  - 另含 1604 版 ending 用的欄位：f_E1～f_E8、px_c、px_on、y_ev_*。
- `researchSurge.py`：seq4 的建表與分析程式。
  - `--stage build`：建表，可參考流程。
  - `--stage analyze`：照 seq4 挑前 15 的分析。⛔ seq5 不適用。
  - `cr0()`、`band()`、`evaluate()`：曆月 CR0、成本帶，可參考。
- `researchSurgeEnd.py`：1604 版 ending 設計，已作廢，由 seq5 §十之六 取代；從來沒有跑過。
- `researchSurge_check.py`：獨立查核。
  - 逐列重算特徵、標籤、R60 的寫法，以及基準② 橫斷面重建，可沿用。
  - 最後一段比對 cells_all.csv 是 seq4 專用。
- 資料：
  - main archive（唯讀）：`~/h2data/surge_b53f5540a8ad/`。內含 adj、meta、revenue_hist、fin_hist、stocks、stocks_per、stocks_inst、stocks_margin、tdcc、tdcc_hist、universe/sbl、universe/otcsbl，以及 tdcc.py。
  - 早年版面：`~/earlydata/3edc0e2206/main`，只有上市。
  - W1 面板（舊快取）：`backtest/resultsp9_engine/panel_ext.csv.gz`；早年用 `~/earlydata/3edc0e2206/sig_main/panel.csv.gz`。

## 二、可沿用的中間檔（`backtest/resultsSurge/`；不含分析結果）

- `table_main.pkl`、`table_early.pkl`：seq4 口徑的特徵表，W1 母體股-日。
  - 內容：特徵原值、當日五等分、F1～F3 標籤、R20／60／120、X20／60／120（基準②）、ending 欄。
  - ⚠ 母體與回看期都是 seq4 口徑；只能拿來對照或抽用欄位，不能直接當 seq5 的表。
- `build.log`：建表紀錄，只有列數。

## 三、不可沿用的 seq4 結果檔（已移到 `_seq4_seen/`）

- `cells_all.csv`：seq4 全部特徵級距的 ①②③。
- `pairs_explore.csv`：seq4 探索段的配對。
- `top15.csv`：seq4 選前 15 與確認段結果。
- `yao_explore.csv`：seq4 的妖股特徵。
- `summary.json`：seq4 摘要。
- `REPORT.md`、`飆股回推_20260929.html`：seq4 報告與網頁。
- `run.log`：seq4 分析 log。
