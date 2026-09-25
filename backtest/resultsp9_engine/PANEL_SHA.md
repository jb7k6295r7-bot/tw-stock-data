# resultsp4/panel.csv.gz 的指紋（裁定線 seq162 §四④）

量測 2026-09-25 18:10（台北）；工作樹 `~/tw-p17`（HEAD 9c72da5997，分支 claude/stock-analysis-backtest-iv9xji）。
由 `python -m backtest.selftest_p9_builders panelsha` 產生（hashlib.sha256 讀整個檔的位元組）。

⭐ 為什麼要記：這一份【沒有進 git】（.gitignore 擋掉）⇒ 別人要能確認拿到的是同一份（〈一百〇一〉）。
P9 回歸閘 2（ENGINE_REPORT §三）與 P8、P9 2-C ⓑ 的 sig 都是從這一份建的。

| 項 | 值 |
|---|---|
| 路徑 | `backtest/resultsp4/panel.csv.gz` |
| **sha256** | `fc1ed89d202aeb1d0cffe885e358390f3d1048d2a17d30555ce5feefc59fc39e` |
| **位元組數** | 24,566,946（24566946 B） |
| 檔案時戳 | 2026-09-23 18:05:29（台北） |
| 進 git？ | 否（`.gitignore:14:backtest/resultsp4/panel.csv.gz	backtest/resultsp4/panel.csv.gz`） |
| git hash-object（未入庫，只供比對） | `6129739af835ef0254da182d929a3fee1cb6acc6` |
| 內容 | 229,851 列、量測日 2015-01-05～2026-03-02、eligible 59,718 列 |

## 參照：主窗（edc6f8002f 快照）用的 panel

`backtest/resultsAFC/panel.csv.gz` 有進 git（git blob `6d43a32ce7d94fe67650804837c96298d71dbc40`）⇒ 以 git 為準；另記 sha256 `4b7b22d7cc21aa696ec7fa531e8ce84aee3ee3cb1a50fb7915acb958421b030c`、24,464,861 B、228,790 列、量測日 2015-01-05～2026-03-02、eligible 59,661 列。
rerun17 main（主窗重跑）與本件 2-B 加成次數分佈用的是這一份。

## 延伸面板 panel_ext（裁定線 seq167 §四：面板補 2026-04～08 量測日；新 sha 與舊 sha 並列）

量測 2026-09-25 19:15（台北）；工作樹 `~/tw-p17`（HEAD 9ff2b9f01a，分支 claude/stock-analysis-backtest-iv9xji）。
由 `python backtest/p9_panel_ext.py --sha` 產生（hashlib.sha256 讀整個檔的位元組）。

| 項 | resultsp4/panel.csv.gz（舊，P8 用） | resultsAFC/panel.csv.gz（舊，主窗） | **resultsp9_engine/panel_ext.csv.gz（新）** |
|---|---|---|---|
| **sha256** | `fc1ed89d202aeb1d0cffe885e358390f3d1048d2a17d30555ce5feefc59fc39e` | `4b7b22d7cc21aa696ec7fa531e8ce84aee3ee3cb1a50fb7915acb958421b030c` | `d75bf50baae15ed0445219a6f8003f166d65a6ce93b930d729a789fc364e0788` |
| 位元組數 | 24,566,946 B | 24,464,861 B | 25,295,142 B |
| git hash-object | `6129739af835ef0254da182d929a3fee1cb6acc6` | `6d43a32ce7d94fe67650804837c96298d71dbc40` | `ef86231c0419388f4d6f450729d72e4f4a618cfd` |
| 進 git？ | 否（未入庫；本件不 commit） | 是 | 否（未入庫；本件不 commit） |
| 列數 | 229,851 | 228,790 | 238,411 |
| 量測日 | 2015-01-05～2026-03-02（135 個） | 2015-01-05～2026-03-02（135 個） | 2015-01-05～2026-08-03（140 個） |
| eligible 列 | 59,718 | 59,661 | 63,295 |

- 資料：main `edc6f8002fed8803795e3486ad57db513f7e9f65` 快照（~/h2data/<sha>/data，唯讀）＝ resultsAFC 同一份；母體 gate3 全體；`researchp4.build_panel` 同一支。
- panel_ext ＝ resultsAFC/panel.csv.gz 的全部列（讀回原樣）＋ 新增量測日 2026-04-01、05-04、06-01、07-01、08-03 的列；欄名欄序與 resultsAFC 完全相同。
- ⛔ 新增量測日的 fwd_20／fwd_60／fwd_120 一律 NaN（本件只為 2-B ⓑ 旗標，⛔ 不讀不存報酬）。
- 重疊處（2026-03-02 以前）與 resultsAFC 逐列逐欄逐位元相同：fixture `backtest/selftest_p9_panel_ext.py`（結果 `panel_ext_fixtures.json`）。
- panel_ext 的 gzip 標頭 mtime＝0 ⇒ 同內容、同檔名 panel_ext.csv.gz 重寫 sha 不變（已驗：讀回再寫到別的目錄同名檔，sha 相同；gzip 標頭含檔名，換名就變）；兩份舊面板是 pandas 預設（mtime＝寫檔時間），⛔ 不能拿重寫的檔對它們的 sha，要比內容。
- ⚠ resultsp4 那一份是分支舊快照、母體不是 gate3，與另兩份不同源，只並列備查（P8、P9 回歸閘 2 用它）。
