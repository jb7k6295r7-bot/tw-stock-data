# 門檻B 逐檔判定（asof 2026-09-24）

資料：main `edc6f8002fed8803795e3486ad57db513f7e9f65`（最後交易日 2026-09-24）；母體 gate3；程式 `backtest/gate_b_status.py`。

## 附註

- 曾觸發 ≠ 會買到（W1 每月量測日判、8 檔名額隨機挑、抱 120 個交易日）
- 只在每月量測日判一次，量測日之間不換判定
- ma_stack 條件是等於 0（不是多頭排列）

## 逐欄說明（`gate_b_status_20260924.csv`）

| 欄 | 意思 |
|---|---|
| stock_id／name／market | 代號／名稱／市場（meta/stocks.csv） |
| status | 已判定｜不在門檻B 母體（原因：興櫃、非上市櫃普通股、-DR、創新板、查無代號；判定一律由 gate3 決定）｜量測日無成交或不在籍 ⇒ 本月無判定 |
| asof／data_last_day | 實際採用的判定日（≤ 指定 asof 的最後一個交易日）／資料快照的最後交易日 |
| measure_date | asof 以前最後一個量測日（每月第一個交易日）——下面九欄全是這一天的值 |
| liq_ok | 流動性閘：近 20 日均成交額 amt20 ≥ 5,000 萬元（T/F） |
| bars_ok | 根數閘：量測日有價收盤根數 bars ≥ 120（T/F） |
| inst_ok | 法人閘：外資與投信近 20 日淨買超都可算（窗內無缺值）（T/F） |
| eligible | 三閘都 T 才是 T（＝ liq_ok ∧ bars_ok ∧ inst_ok） |
| rev_hi24 | 100＝可得的最新一期月營收 ≥ 前 24 期最高（對稱容差 1e-4）；0＝否；NaN＝不明（覆蓋不足／存託憑證） |
| ma60_up | 100＝MA60 今日 > 20 個交易日前的 MA60；0＝否 |
| ma_stack | 100＝close > MA20 > MA60 > MA120（多頭排列）；0＝否。⭐ 門檻B 要的是 0 |
| signal | 門檻B 訊號（T/F）＝ eligible ∧ rev_hi24＝100 ∧ ma60_up＝100 ∧ ma_stack＝0（researchp7.build_sig_gate_b 的輸出） |
| amt20／bars | 參考：近 20 日均成交額（元）／有價收盤根數 |
| n_trig_120d／trig_measure_dates | 最近 120 個交易日內（asof 當日算第 1 個）觸發的次數／各次的量測日 |
| last_trig_measure_date | 最近一次觸發的量測日 |
| last_trig_entry_date | 進場日＝該量測日的次一交易日（開盤進） |
| last_trig_day_n | asof 是持有期的第幾個交易日（進場日＝第 1 個；0＝尚未進場） |
| last_trig_exit_date | 預計出場日＝持有第 120 個交易日（收盤出） |
| last_trig_exit_basis | 出場日的依據：資料日曆｜休市表外推｜只扣週末（該年休市表未公告 ⇒ 元旦、春節等休市沒扣，實際出場日只會更晚）；三者都不含颱風等臨時休市 |
| last_trig_entry_open_ok | 進場日有沒有開盤價（T/F；未到＝進場日在 asof 之後）。F ⇒ 回測（build_sig_gate_b）會剔除這一筆 |

事件表 `gate_b_events_20260924.csv`：量測日落在 [asof − 120 個交易日, asof] 的每一次觸發（多列一天給第二種讀法）；`in_window_120`＝落在最近 120 個交易日內（asof 當日算第 1 個）、`holding_on_asof`＝asof 當日仍在持有期內。

## 表

| stock_id | name | market | status | asof | measure_date | liq_ok | bars_ok | inst_ok | eligible | rev_hi24 | ma60_up | ma_stack | signal | amt20 | bars | n_trig_120d | trig_measure_dates | last_trig_measure_date | last_trig_entry_date | last_trig_day_n | last_trig_exit_date | last_trig_exit_basis | last_trig_entry_open_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2609 | 陽明 | twse | 已判定 | 2026-09-24 | 2026-09-01 | T | T | T | T | 0 | 100 | 100 | F | 5,037,124,934 | 2833 | 0 |  |  |  |  |  |  |  |
| 6209 | 今國光 | twse | 已判定 | 2026-09-24 | 2026-09-01 | T | T | T | T | 100 | 0 | 0 | F | 618,212,752 | 2842 | 0 |  |  |  |  |  |  |  |
| 3535 | 晶彩科 | twse | 已判定 | 2026-09-24 | 2026-09-01 | F | T | T | F | 0 | 0 | 0 | F | 47,150,730 | 2842 | 0 |  |  |  |  |  |  |  |
| 4164 | 承業醫 | twse | 已判定 | 2026-09-24 | 2026-09-01 | F | T | T | F | 0 | 0 | 0 | F | 9,529,641 | 2842 | 0 |  |  |  |  |  |  |  |
| 6282 | 康舒 | twse | 已判定 | 2026-09-24 | 2026-09-01 | T | T | T | T | 0 | 0 | 0 | F | 391,683,080 | 2841 | 1 | 2026-08-03 | 2026-08-03 | 2026-08-04 | 38 | 2027-01-25 | 只扣週末（2027 年休市表未公告） | T |
| 6443 | 元晶 | twse | 已判定 | 2026-09-24 | 2026-09-01 | T | T | T | T | 0 | 0 | 0 | F | 112,477,283 | 2657 | 0 |  |  |  |  |  |  |  |
| 8289 | 泰藝 | tpex | 已判定 | 2026-09-24 | 2026-09-01 | F | T | T | F | 100 | 0 | 0 | F | 23,482,888 | 2834 | 1 | 2026-08-03 | 2026-08-03 | 2026-08-04 | 38 | 2027-01-25 | 只扣週末（2027 年休市表未公告） | T |
| 6469 | 大樹 | tpex | 已判定 | 2026-09-24 | 2026-09-01 | F | T | T | F | 0 | 100 | 0 | F | 28,622,530 | 2542 | 0 |  |  |  |  |  |  |  |

## 事件

| stock_id | measure_date | entry_date | entry_pos | day_n | xpos_H120 | exit_date | exit_date_basis | in_window_120 | holding_on_asof | entry_open_ok |
|---|---|---|---|---|---|---|---|---|---|---|
| 6282 | 2026-08-03 | 2026-08-04 | 2821 | 38 | 2940 | 2027-01-25 | 只扣週末（2027 年休市表未公告） | True | True | T |
| 8289 | 2026-08-03 | 2026-08-04 | 2821 | 38 | 2940 | 2027-01-25 | 只扣週末（2027 年休市表未公告） | True | True | T |

