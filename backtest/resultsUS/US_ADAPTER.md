# 美股資料轉接層｜US_ADAPTER

**台北時戳**：2026-09-25 22:1x　**寫的人**：回測線（計算助手）
**給**：USREG-M／USREG-X／USREG-U／USREG-W1b 共用
**依據**：美股登錄 seq2（正文，sha a3c98a07e882a574）＋seq3（81bfc48eff6258f5）＋seq4（cbc7610923b9e53）；
裁定線 seq163、seq168、seq176；資料庫線 1550、1639、1753、2016

> ⛔ 本件不跑任何策略、不讀不算任何策略報酬（登錄還在等裁定核准）。
> ⛔ 本資料夾只放計數、sha、查核結果；**沒有任何美股價格或報酬數值**（us-stock-data 是私有 repo，授權限制）。
> 基準只報 ^SP500TR 與 SPY 的年化【差】。

---

## 〇、資料版本

```
repo       jb7k6295r7-bot/us-stock-data（私有；本線只讀）
commit     0043f97d974df78ffe5626623aed2caecfd4a5b8（＝ 登錄 seq4 §三 寫死的 0043f97；開工時 ~/us-stock-data 的 HEAD ＝ origin/main ＝ 同一個）
讀取位置   ~/usdata/0043f97/（git archive 出來、chmod a-w；.commit 記完整 sha）
           ⛔ 不讀 ~/us-stock-data 工作目錄（live.yml 每天改它）；可用環境變數 US_DATA_ROOT 改指
各檔 sha   resultsUS/fingerprint.csv（大目錄 panel 712 檔、prices 84 檔、prices_yahoo 597 檔各給一個合併 sha）
開跑前     呼叫 us_data.assert_pinned() ⇒ commit 不是 0043f97 就停
```

## 一、函式定義與讀法（backtest/us_data.py）

| 函式 | 回傳 | 定義 |
|---|---|---|
| `load_calendar()` | DatetimeIndex | NYSE 交易日＝`data/macro/yahoo_GSPC.csv` 的日期（資料庫 1639 §三） |
| `next_trading_day(d)` | Timestamp | 嚴格晚於 d 的第一個交易日 |
| `load_ohlc(t, scope="covered")` | DataFrame：open,high,low,close,src,hard_break,break_reason,piece | **covered（預設，登錄逐字）**：`_segments.csv` 的 kind＝covered 列；src 前綴 `yahoo:` ⇒ `prices_yahoo/<後綴>.csv`、`tiingo:` ⇒ `prices/<後綴>.csv`；只取該列 range。Yahoo 還原 X＝原始 X×adjclose÷close；Tiingo 直接用 adjOpen/adjHigh/adjLow/adjClose。**panel**：照面板每列的 src 取同一檔（含入指數前的暖身日），見 §五⑨ |
| `hard_breaks(t)` | DataFrame(date, reason) | 這一根與前一根不能相連：`seam`＝同一代號換檔（IR 2020-03-02）；`split_div`＝同一天拆股＋配息（面板 src 帶 * ∪ `_report.md`〈同一天拆股＋配息〉；DHR 2016-07-05、XRX 2017-01-03）。`piece`＝切出來的段號 |
| `long_gaps(t, min_days=5)` | DataFrame(prev, next, missing) | 相鄰兩根 K 棒之間缺 ≥5 個交易日（登錄 seq2 §二④ 的參數）。只列事實，要不要切由策略程式照登錄做 |
| `in_index(t)` | DataFrame(member, has_price)，窗首起每個交易日 | 面板那天有列 ⇒ 取面板 in_index；沒列 ⇒ 取 `membership/universe.csv` 的 spans（a ≤ d < b，跟 build_panel.py 同一條規則） |
| `universe(d, include_unpriced=False)` | list | 預設＝面板 in_index＝1 **而且當天有列**（登錄 seq2 §一「缺列 ⛔ 不補」）；include_unpriced＝True 時再加上當天在指數、沒有價格的（拿來對名冊）。d 不是交易日 ⇒ [] |
| `benchmark_tr(source="SP500TR")` | Series | ^SP500TR 的 adjclose（＝close）；`"SPY"` 備援＝SPY 的 adjclose。⛔ 不提供 ^GSPC |
| `quarterly_revenue()` | DataFrame | 讀 value（第一次公布）；**latest_value／latest_filed 用 usecols 排除，根本不讀進來**；avail_date＝first_filed 之後的第一個交易日；cal_q＝period_end 落在哪個曆季；derived＝1 照收；缺季就沒有列 |
| `revenue_asof(d)` | DataFrame | avail_date ≤ d 的列 |
| `no_ohlc_tickers()`／`partial_ohlc_tickers()` | list | 整段沒有 covered 段的代號／covered 段和 gap 段都有的代號 |
| `revenue_not_applicable()` | dict | 母體裡季營收一列都沒有的代號；原因取自 status 檔，status 檔裡沒有的記為 no_cik |
| `data_commit()`／`assert_pinned()`／`fingerprint()` | | 版本與 sha |

常數：`COST_ROUNDTRIP=0.0005`（0.05% 來回，每邊 0.025%）、`COST_SENSITIVITY=(0.0002, 0.0010)`、`PRICE_LIMIT=None`（沒有每日漲跌停）、
停牌＝面板那天沒有列（⛔ 不補 0、⛔ 不補前值）、`GAP_BREAK_DAYS=5`、`WINDOW=2016-01-04～2026-08-31`、`EVENT_FWD=21`（事件須 T+21 ≤ 窗尾）。

⛔ 台股共用引擎（research11.py、data.py、tradability.py…）一行都沒改；美股轉接另外開檔（照裁定）。

## 二、覆蓋數

```
母體（membership/universe.csv）     747 檔
有 OHLC（至少一個 covered 段）       712 檔（_segments covered 713 列：只有 IR 是兩段）
整段沒有 OHLC                          35 檔 ＝ 資料庫 1753 名單，逐檔相同
  ADT ANSS APC BBBY CA CAM CBS CCE CCEP CSRA DNB DO EMC ENDP ESV FL FRC FTR HBI HFC
  INFO MNK MON NFX PARA PCL POM SBNY SE SIVB SPLS STI TE VIAC WRK
部分缺（有 covered 也有 gap）          5 檔：ARNC DOW FOX FOXA SNDK
窗內（2016-01-04～2026-08-31）在指數的股-日   1,351,751
  35 檔                                21,498（1.59%）⇐ 登錄 seq2 §一 要求必報的佔比
  所有沒價格的股-日                   23,873（1.77%）＝ 35 檔 ＋ 有 OHLC 的檔當天沒列 2,375
  （資料庫 1550 寫 1.58%；差 0.01 個百分點，應該是兩邊的窗不一樣）
還原 K 棒（covered）                   1,341,954 根
季營收                                 34,411 列、728 檔有營收；一列都沒有的 19 檔（見 §四 C5）
```

## 三、查核結果（selftest_us_data.py；PASS 31｜WARN 3｜FAIL 0；跑一次約 2 分 45 秒，單一行程）

逐條原文在 `checks.csv`、`selftest_us_data.log`。⭐ 主要的查核都附了一個「故意做錯就會紅」的反例，證明這些查核分得出對錯。

### A 還原 OHLC

| 編號 | 結果 | 內容 |
|---|---|---|
| A0 | ✅ | commit 0043f97d974d 符合登錄寫死的版本 |
| A1 | ✅ | Yahoo 換算後的 close 與 adjclose 比了 1,251,909 根，最大相對誤差 2.2e-16（容差 1e-12）。反例：係數誤用 adjclose÷open，誤差 1.6e-01，會紅 |
| A2 | ⚠ | 還原後 low ≤ open,close ≤ high：1,341,954 根裡只有 **1 根違反：UA 2021-05-05（yahoo:UA）**，而且原始檔那根本來就違反（是來源的問題，不是換算造成的）。反例：用合成的壞 K 棒會紅 |
| A3 | ✅ | 面板 ret 對照還原收盤算出的日報酬，排除硬斷點日：covered 比了 1,341,239 天、panel 範圍比了 1,527,793 天，**\|差\| > 1e-8 的 0 天**，最大 5.0e-9。容差 1e-8 的依據：面板存到小數 8 位，捨入誤差 ≤ 5e-9；浮點誤差 < 1e-12。非斷點日面板 ret 空白 0 天。反例：硬斷點日不排除 ⇒ DHR、XRX 會紅 |
| A4a | ✅ | 同日拆股＋配息三處來源互相一致：面板 src 帶 * ＝ `_report.md` ＝ 本層標的 split_div ＝ {DHR 2016-07-05, XRX 2017-01-03} |
| A4b | ✅ | covered 範圍內的來源接縫只有 IR 2020-03-02（yahoo:TT → yahoo:IR）；scope＝panel 也只有這一處 |
| A4c | ✅ | 面板 ret 空白（每檔第一列除外）只有 1 天，就是 IR 的接縫日 |
| A4d | ✅ | 驗證斷點確實必要：DHR 2016-07-05 跨日還原收盤比和面板 ret 差了 50 個百分點以上（Yahoo 重複還原造成的假跳空）⇒ 已切成新的 piece |
| A4e | ✅ | 每一根 covered K 棒在面板上都有同一天、同一個 src 的列 |
| A5 | ✅ | 在 covered 日期上，scope＝panel 和 scope＝covered 的結果逐位元相同 |
| A6 | ✅ | 窗內每一根 K 棒都在 NYSE 日曆上（0 根例外）；窗內每年平日休市 8～11 天（2016 年從 01-04 起算；2018、2025 年各多一天國喪），正常。窗內 K 棒之間缺 ≥1 個交易日的空缺共 7 處（合計 15 天）；**缺 ≥5 個交易日的只有 1 處：CVC 2016-04-20 → 2016-05-02（缺 7 天）** |

### B 母體

| 編號 | 結果 | 內容 |
|---|---|---|
| B1 | ⚠ | 128 個月底：**universe(d) 和名冊 has_price＝1 的列完全一致（0 個月不符）**。include_unpriced 的全名冊有 7 個月、8 列不符，全部是名冊多出 has_price＝0 的列，而且那天剛好是該檔的移出日：CCE、CCEP 2016-05-31；BCR 2017-12-29；WYND 2018-05-31；PX 2018-10-31；KMX 2025-10-31；IPG 2025-11-28；CAG 2026-06-30 ⇒ 見 §五① |
| B2 | ✅ | 三家倒閉銀行在指數期間都有列、都沒有 OHLC：SIVB 1,256 個交易日（2018-03-19～2023-03-14）、FRC 1,092 日（2019-01-02～2023-05-03）、SBNY 309 日（2021-12-20～2023-03-14）；有價 0 日、OHLC 0 根；名冊裡都是 has_price＝0（60、52、15 個月） |
| B3 | ✅ | 712／35／747 三個數都對上；35 檔和資料庫 1753 的名單相同 |
| B4 | ✅ | 35 檔佔在指數股-日 1.59%（見 §二） |

### C 季營收

| 編號 | 結果 | 內容 |
|---|---|---|
| C0 | ✅ | 轉接後 34,411 列＝原檔 34,411 列（不增列、不補季）；輸出欄位沒有 latest_value／latest_filed |
| C1 | ✅ | 可用日一律晚於期末（最少晚 9 天、中位 37 天），也一律晚於 first_filed，而且都是交易日；另用逐日往後找的獨立寫法重算，結果完全相同。可用日為 NaT 的 2 列都是 first_filed ≥ 快照日曆最後一天（2026-09-24），在窗外。可用日落在窗內的共 27,574 列 |
| C2 | ✅ | 抽查 5 家（只看日期，不列數值）：AAPL 期末 2023-07-01，10-Q 在 2023-08-04（週五）申報 ⇒ 可用日 2023-08-07（週一）；MSFT derived＝1 的 Q4，期末 2022-06-30，10-K 在 2022-07-28 申報 ⇒ 2022-07-29；DIS 前身 CIK 0001001039，期末 2017-04-01，申報 2017-05-09 ⇒ 2017-05-10；WAT（52／53 週會計年度）期末 2016-07-02，申報 2016-08-05（週五）⇒ 2016-08-08；NVDA 期末 2023-04-30，申報 2023-05-26（週五）⇒ 2023-05-30（跨過 Memorial Day） |
| C3 | ✅ | 缺季不補 0：總列數不變；XOM 2025 年以前 0 列（缺的季就是沒有列）。⚠ 另外兩件事見 §五④⑤ |
| C4 | ✅ | 重編過的季共 3,595 個：轉接後的值全部等於 value（第一次公布），沒有一個等於 latest_value |
| C5 | ⚠ | 季營收一列都沒有的 19 檔，和登錄的「不適用 16 家與 FRC、SBNY」名單對不上 ⇒ 見 §五⑥ |

### D 基準

| 編號 | 結果 | 內容 |
|---|---|---|
| D1 | ✅ | 窗內 2,680 個 NYSE 日：^SP500TR、SPY 都不缺也不多 |
| D2 | ✅ | 同窗年化差（^SP500TR − SPY 還原；從 2015-12-31 收盤到 2026-08-31 收盤，年數＝日曆日÷365.25）＝ **+10.4 基點**。方向與大小符合 SPY 0.09% 的費用率。^SP500TR 的 adjclose 與 close 相同 |

### E 無前視

| 編號 | 結果 | 內容 |
|---|---|---|
| E1 | ✅ | 取 22 個日子（隨機 12 天，加上 SIVB／FRC／SBNY 進出指數的日子和 IR 接縫前後）：只用 d 以前的面板列、spans 右端晚於 d 的一律當「還沒移出」重建，結果和 universe(d) 完全相同。反例：改用隔天的名冊，在 228 個成分變動日會不一樣 |
| E2 | ✅ | 同樣 22 個日子，revenue_asof(d) 都只含可用日 ≤ d 的列；抽一列檢查：可用日前一個交易日不在、可用日當天才出現；first_filed 本身是交易日的 34,389 列，沒有一列在申報當天就能用。反例：若可用日＝first_filed 當天，這 34,389 列都會提早一天 |

## 四、讀的人一定要知道的（寫策略程式時）

```
① 母體：universe(d) 預設只含「當天有 K 棒」的成分股；三家倒閉銀行與 35 檔永遠不會出現在預設母體
   ⇒ M／U／X 結論句後照登錄 seq3 §一① 附「缺價的 35 檔不在事件母體，結果偏向存活股」
② 硬斷點：load_ohlc 的 piece 已經切開 seam 與 split_div；登錄 seq2 §二④ 的「≥5 交易日無 K 棒」要另外用 long_gaps() 切
   （窗內只有 CVC 一處）
③ 停牌：面板沒列＝沒有 K 棒；⛔ 不要 reindex 到日曆後 ffill
④ 還原價水準：Yahoo／Tiingo 的還原價是用「之後的配息」往回縮放的
   ⇒ 同一個 piece 內的比值（報酬、斜率比例）不受影響；⛔ 但任何看「絕對價位」的條件（例如 $ 門檻）會帶到未來資訊
⑤ 季營收：avail_date ≤ 量測日才能用；缺季就是沒有列；cal_q 照登錄 seq4 §二以期末歸季（§五⑤ 的問題本層不替你們決定）
```

## 五、資料問題與待裁事項（⛔ 本層都沒有自己改）

```
① 名冊與面板對「移出日當天」的規則不一致（資料庫線）
   build_panel.py：a ≤ d < b（移出日當天不在指數）；roster.py 補無價列：a ≤ d ≤ b（含移出日）
   ⇒ _month_end_roster 在 7 個月底多出 8 列 has_price＝0（B1）；有價的列完全一致 ⇒ 不影響事件母體
   本層照面板規則（d < b）
② ^GSPC 與 ^SP500TR 缺 2026-09-22（週二，正常開盤日；SPY 和 66 檔個股有這一天，其餘 527 檔也缺）（資料庫線）
   ⇒ 這一天在窗外（窗到 2026-08-31），不影響本件；但缺這天的檔，面板 2026-09-23 的 ret 其實是兩天的報酬，日後延長窗之前要補
③ UA 2021-05-05 的 Yahoo 原始 K 棒本身就不自洽（A2）：1 根，來源的問題；本層不改
④ 季營收來源裡有 value＝0 73 列、value＜0 27 列，共 29 檔（例：SCG 21 列、VRT 11、ALK 11）
   ⇒ 不是本層補的；但「8 季創新高」遇到 0 或負值要怎麼處理，登錄沒寫 ⇒ 請美股策略線／裁定線決定
⑤ ⭐ 以期末歸曆季（登錄 seq4 §二）遇到 52／53 週會計年度會出現假缺季：
   兩個相接的會計季落在同一個曆季（撞季）298 處／84 檔；相接的會計季卻跳過一個曆季（假缺季）325 處／86 檔
   （例：NUE 10 處、AAP 8、GD 8、MSI 7、HSY 7…）；時間上真的沒接上的真缺季 180 處／72 檔
   ⇒ 照 seq4 §二「中間缺任何一季 ⇒ 不列候選」逐字執行，這 86 檔會因為會計日曆被排除，而不是因為缺資料
   ⇒ 撞季時該取哪一季、假缺季算不算缺 ⇒ 登錄的事，請美股策略線／裁定線在 W1b 開跑前定（本層只提供 cal_q 與這些計數）
⑥ 季營收不適用名單對不上（資料庫線 2016 §二 與 登錄 seq4 §三）
   實際上一列都沒有的 19 檔：no_revenue_tag 16 檔（ANDV CCEP CMA DFS FDXF FITB HBAN NAVI PBCT PCL POM RF SE SIVB SYF TFC）
                           ＋ FRC（no_companyfacts）＋ SBNY、GAS（no_cik：cik_map 沒對上）
   信中的名單寫了 CVC、MJN，但這兩檔實際有營收（CVC 13 季到 2016-03、MJN 17 季到 2017-03）；信中漏了 NAVI；GAS 沒有任何信提到
   ⇒ W1b「名單必報」請以 revenue_not_applicable() 的 19 檔為準，或由資料庫線更正信中的名單
⑦ 35 檔的股-日佔比：本層算 1.59%，資料庫 1550 寫 1.58% ⇒ 差 0.01 個百分點（應該是窗不一樣）；登錄要報的時候以本層窗內數字為準
⑧ ≥5 交易日的空缺：窗內只有 CVC（2016-04-20 → 05-02，缺 7 天）
⑨ 暖身日（待裁）：登錄 seq2 §一 寫「只取該列日期範圍」⇒ covered 的 range 從入指數第一天開始，⛔ 不含入指數前的歷史
   ⇒ 窗中途才加入指數的檔，入指數後的頭 60 天算不出 MA60，趨勢線也缺前段
   面板本身從入指數前約 400 天就有列（in_index＝0）；scope="panel" 可以取到，而且在 covered 日期上與預設逐位元相同（A5）
   ⇒ 要不要用暖身日是登錄的事；本層預設照登錄逐字（不用）
```

## 六、檔案

```
backtest/us_data.py                  轉接層（新檔）
backtest/selftest_us_data.py         fixture＋查核（新檔）；跑法：PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_us_data
backtest/resultsUS/US_ADAPTER.md     本件
backtest/resultsUS/checks.csv        34 條查核（id,status,summary）
backtest/resultsUS/selftest_us_data.log  完整輸出（只有計數、日期、代號、誤差量）
backtest/resultsUS/fingerprint.csv   資料 commit 與各檔 sha256
⛔ 未 commit、未 push
```

— 回測線（計算助手）
