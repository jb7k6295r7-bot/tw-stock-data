# S59 興櫃轉上櫃：頻率表（⛔ 沒有任何報酬）

- 依據：登錄 1120-0053（事件後下一交易日收盤買，抱 20／60／120）、0134 讀法 3（事件只計進場前最近月底在母體內）；裁定 seq526 §2、seq529 §一（改用甲驗算；照 seq520 先頻率表）。
- 名單：tw-stock-data `data/meta/emerging_to_otc/emerging_to_otc.csv`，sha256 `00101a7581612213fc01988988416be3324f09d6f8abd83c7270f424142aac84`（與凍結值相同；main d8defa4512 取出），只用 inferred＝1 共 584 筆。判語固定附「名單為推定」，最高到「暫定」。
- 價量、母體：~/scanadd 快照（tw-stock-data dcefaa4ef3，資料最後日 2026-11-27），母體定義同 64 格。
- 程式：`add/code/s59_freq.py`（用 `add/code/run.sh` 跑）。

## 兩種讀法（看報酬前並列，請裁定擇一）
| | 讀法 A 字面 | 讀法 B 同 S58 實作 |
|---|---|---|
| 事件 | 日線第一個 tpex 交易日 | 第一次進入當年母體的月底（距上櫃首日 ≤550 天） |
| 探索事件／事件月（20／60／120 日） | 0／0 | 51／31、31、31 |
| 確認事件／事件月 | 0／0 | 52／34、34、32 |

- A 為 0：母體要求近 250 日有效根 ≥200，剛上櫃的股票進場前月底一定不在母體。
- B 全部落在同快照重建的 S58 事件裡（103／103），佔 S58 兩段事件 39.5%（S58 261 筆）⇒ 不等價。
- 584 筆推定裡，18 筆日線找不到 tpex 列（2015 年前上櫃，見 s59_missing.csv）；566 筆在價量面板內；上櫃首日與 IRB170 同月 300 筆。

描述，不是買賣建議。

## 報酬程式（裁定 seq531 選讀法 B；⛔ 本節只有乾跑與合成 fixture，沒有真報酬）
- 事件表：`add/code/s59_events.py` 把 s59_events_both.csv 的 B_form／B_entry 寫成 `~/scanadd/factors/S59_events.csv`，用 factors.save_events 原欄位。全期 217 筆，探索 51、確認 52。
- 報酬：`add/code/returns_evt_add.py dry|fixture|real`。
  - 不另寫算法：直接執行 `code/returns.py` 原始碼的這些段落：seg_of、自助法段（cbb_idx、boot）、事件段（RH／BENCH、load_events、event_excess、summarize_events、shuffle_events）、verdict_events、label_desc。
  - returns.py 一字不改（sha256 737ae0fa…，64 格不受影響）。
  - returns.py 在 module 層會讀 64 格自己的 cache 並用真價格算，所以不 import，改抽段落執行。
  - 本檔只備全域：面板母體同 returns_add.py、dry／fixture 換價格、門檻。
- 做法同 64 格事件型：
  - 持有 20／60／120 根（進場那根算第 1 根）。
  - 對進場前最近月底母體等權，壞根作廢。
  - 出場超過資料尾 2026-11-27 不計。
  - 同進場月成一群，群平均等權。
  - 循環區塊自助法 6 個月、4,000 次、seed 5。
  - 假訊號＝同進場日、同月底母體隨機一檔，default_rng(5)。
- 門檻：
  - 判語區間 3 期各 0.05/207（returns.py 的 loEV／hiEV）。
  - 0.05/69 只描述（loB／hiB）。
  - 群數 <24 的持有期不判。
- 欄位：
  - 「依門檻落點」只寫落在哪一類。
  - 「判語(裁定)」空著。
  - 「判語固定附註」寫三句：名單為推定；讀法 B（同 S58 實作，不是登錄字面）；S59 的事件全部包含在 S58 裡（佔 S58 約 4 成）。最高到「暫定」。
- 乾跑 `~/scanadd/dry/result_S59.csv`：
  - 群數 探索 31／31／31、確認 34／34／32，與 s59_freq.json 的 B 一致。
  - 事件數 51／51／51、52／52／49。
  - 平均超額、事件加權平均（真與假訊號）全 0。
- fixture `~/scanadd/fixture/`：隨機漫步假價格，非真報酬。跑完，欄位齊全，無 inf。
- 正式跑（主線）：`bash ~/tw-p17/backtest/resultsScan64/add/code/run.sh ~/tw-p17/backtest/resultsScan64/add/code/returns_evt_add.py real`
  - 輸出 ~/scanadd/result_S59.csv、monthly/S59_events_excess.csv.gz、monthly/S59_shuffle_cells.csv。

## 正式跑（2026-11-28 20:29，主線自己跑；裁定 seq531 選 B）
- `returns_evt_add.py real`（returns.py sha256 737ae0fa… 原始碼段落原樣執行，一字未改；資料 dcefaa4ef3）。結果 `result_S59.csv`、`monthly/`。
- 確認段依判語區間 0.05/207：20／60／120 日全部跨 0 ⇒ 依門檻落點「分不出」；假訊號同。判語待裁定（固定附三句、最高到暫定）。
- 描述（95%，不是判語）：120 日兩段 95% 都在 0 以下；同期假訊號（同進場日、同月底母體隨機一檔）確認段 120 日 95% 也在 0 以下。
