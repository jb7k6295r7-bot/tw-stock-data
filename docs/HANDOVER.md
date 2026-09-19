# 交接（資料庫線）— 2026-09-19 24:00 台北

**這一頁給的是「下一個 session 接手時要先知道什麼」**，⛔ 不是做過什麼的流水帳。
⚠ 而流水帳在 commit 訊息裡（每一則都寫了病根、判準與突變結果）。

---

## 〇、接手第一件事（⛔ 順序是死的）

```
1. git config core.hooksPath .githooks      ← 新 session 進來第一件事（六點五）
2. 讀 CLAUDE.md                              ← ⛔ 它不是簡介，每一條後面都有一次事故
3. 掃收件夾（Drive 1xW08BfxVp0Y_BMly52I8ABVSlU5A4FZD）
4. 驗在飛的東西（見下面「一、在飛的」）
```

⛔ **本線的分支是 `claude/financial-market-analysis-mmm5kf`**（本機分支名是 `feature`）
⇒ 推的時候是 `git push -u origin feature:claude/financial-market-analysis-mmm5kf`，
⭐ 而**驗終點要用 `git ls-remote origin refs/heads/...`**，⛔ 不是看本機的 `origin/xxx`。

最後推上去的 commit：`2e1e9e7e5c`（分支上共 6 個 commit **還沒同步到 main**，見下）。

---

## 一、在飛的（⛔ 驗後果，不驗 conclusion；四點二④三件）

### ① feeds run 170（上櫃月表第三批）— **還在跑**

派工：`feeds.yml` mode=`official-months`／months_market=`tpex`／months_years=`all`／
months_limit=`5000`，**在 main 上派**（它讀 `data/`）。開始 2026-09-19 15:31Z，
預計約 3.5 小時（實測 2.55 秒/格）。

**驗收（⛔ 三件都要）**：
```
① list_workflow_jobs 看那一步的 conclusion（⛔ 不是 run 的 status；⚠ cancelled ≠ 什麼都沒做）
② 後果：git show origin/main:data/meta/_official_monthly_done_tpex.csv | wc -l
        要從 7,378 往上（母體 973 檔 × 12 年 ＝ 11,676 格）
        ⭐ 而且**表頭要變成四欄** stock_id,roc_year,asof,why
           ＝ official_stats._upgrade_sweep_header() 真的跑了
        official_monthly_tpex.csv 列數只增不減（上一版 74,641）
③ _last_run.md 的 `official_stats:months:tpex` 區塊要有**這一趟的時戳**
   ⛔ 那個檔是跨 workflow 累積的 ⇒ 很容易讀到上一趟那一塊
```
⇒ 沒補完就照同樣參數再派一趟（⛔ 前一趟 in_progress 時不要派：同 concurrency group
`feeds`，GitHub 只排得下一個 pending，再送會把還在等的那趟直接 cancel）。

已排了一個自我提醒在 **2026-09-19 19:17Z** 回來做這件事。

### ② 分支上 6 個 commit **還沒到 main**

```
2e1e9e7e5c  push_data: longhalt.csv 與月表台帳進 LEDGERS
ef3fe5deea  db_status: 草稿標記蓋進每一列
ac9f857c84  CLAUDE.md: 那三個零股百分比不可以引用
f374cd8149  月表加權均價: 判準是無條件捨去
ea696cda35  G2 長期停止買賣: 接成每日累積
a33ab72da7  TDR: kind 改判官方證券種類欄
```
⇒ 同步方式：**派 `probe.yml` 並指定分支**（`workflow_dispatch` ref＝本線分支）。
⛔ 不可以等排程——`schedule`／`push` 觸發的一律是 main，跑的是另一份程式（四點六③）。
⚠ 而 probe 只讀程式不讀 `data/` ⇒ 指定分支是安全的；⛔ 讀 `data/` 的那些（transpose、
各種重建）**只能在 main 上跑**。

⭐ 同步後要**驗後果**：main 上真的有 `longhalt.py`／`selftest_longhalt.py`／
`official_stats.monthly_avg_expected`／`push_data.sh` 的 LEDGERS 有 `longhalt.csv`／
`db_status` 逐列草稿標記。

⛔⛔ **而同步那一步很容易被前面一支紅掉的自測擋住**：這一週就發生過一次，
`probe run 139` 的 step 6 紅 ⇒ 步驟 7~14（含「把程式同步到 main」）全部 skipped
⇒ **兩個 commit 卡在分支上三天**，而畫面上什麼都不會說。
⇒ 派工之後**一定要回頭看 job 的逐步 conclusion**，⛔ 不是看 run 的 status。

### ③ #30 的驗收要等**週一 09-21** 那趟 daily（⭐ 已經量成可證偽的預測）

上櫃還原因子已照情報線 0020 §三 (a) 接進 daily（三段式：**先抓 → 再補 → 才掃**），
而**驗收判準是裁定裡寫死的**：⛔ **修好之後若它還是天天紅，就是沒修對**
——⚠ 而處置**不可以**是放寬閘門。

現況（09-19 從 main 的 `_last_run.md` 量的，⛔ 不是推的）：
```
otc_exright_history ✗  「官方有、我方 data/adj/ 沒有｜涵蓋期內」**7 筆**
                       00853B 00985D 00986D 00998A 4420 4533 5498（全部 2026-09-17 除息）
adj_gap            ✗  未歸因 **3**（4420 −6.49%／4533 −1.20%／5498 −0.79%）
                       ⚠ 只有 3 筆是因為它只看普通股，那四檔 00 開頭的是 ETF／債券
⭐ 而兩塊**最後一次 ✓ 都在 09-17**（otc_exright 00:59、adj_gap 11:32）
   ⇒ ⭐ 它們**不是「一直都紅」**，是那批 09-17 的事件出現時才翻紅
   ⇒ 機制被證實：官方判準檔已經抓到了（asof 2026-09-19），只是沒進 data/adj/
```
⇒ **預測**：下一趟 daily 之後 **7 → 0、3 → 0、兩塊翻 ✓**。
⛔ 若沒有，就是沒修對，回去看那一步的三段有沒有照順序跑。

---

## 二、等別人裁的（⛔ 只回報，不自己裁；第五點）

| 事 | 誰裁 | 我送出去的東西 |
|---|---|---|
| `READ_CONTRACT` 的零股那一行寫數字還是只寫方向 | 市場情報分析線 | 件-…-20260919-2330（我建議 **(乙) 只寫方向**：那個檔每月重算，寫死的數字會從寫下去那刻開始過期） |
| D2 財報實際公告日要不要接成供料（ezsearch_query） | 市場情報分析線 | 三個量到的限制：1,000 列上限（⚠ 安靜截斷）／`TYPEK` 只有上市／`CO_ID` 被忽略 |
| ~~C4~~ | ~~—~~ | ✅ **已在這次會話裡解掉，不再等別人裁**——見下面新增的「一點六」 |

---

## 一點五、⚠ 2026-09-19 使用者接了幾個 MCP 連接器——⭐ 已經試過 Firecrawl，結果記在下面

`ListConnectors` 現況：Firecrawl／Google Drive／PDF Viewer／Spotify（四個都是 connected＋enabledInChat）。
Google Drive／PDF Viewer／Spotify 跟這個專案的資料型態無關或本來就在用，⛔ 不重複測。

## 一點六、⭐⭐ 試過 Firecrawl 了——**它只有 search，沒有會渲染 JS 的 scrape/extract**

⛔ 這個 session 實際暴露給我的 Firecrawl 工具只有 `firecrawl_search`（及論文／開發者索引的變體），
**沒有** `firecrawl_scrape`／`firecrawl_extract` 這種「給一個 URL、回渲染後全文」的工具。
⇒ 它回的是**搜尋索引的摘要片段**（title＋description，截斷），⛔ 不是即時抓取。

### ⭐ 而它意外證實了一件有用的事：Firecrawl 自己的爬蟲**會**執行 js

拿它搜 TPEx 的「減資恢復交易參考價」「變更股票面額」兩個 JS 卡點頁面，
`description` 裡回來的**不是**靜態 meta 描述，是**真的表格列資料**
（例：`2067 嘉鋼 1151007 0.75010068 0.00000000`）——這代表 Firecrawl 的索引式
爬蟲有能力把這類頁面的 JS 渲染出來。⚠ 而這**不能**當生產供料用：只有截斷片段、
不是全表、新鮮度未知（索引快照，不是即時抓）。

### ⛔⛔ 而真正解開 C4 的不是 Firecrawl——是去核對自己家已經寫好的程式

去查這兩個「要能執行 js」的卡點時，發現 **db_status.py 的敘述本身已經過期**：
`otc_parvalue_history.py`（2026-09-15）早就找到 `bulletin/pvChgRslt` 是一支
**不需要 js** 的 POST／JSON 端點，14/14 對上官方值；`otc_reduce_history.py`
（2026-09-10）也早就用 `bulletin/revivt` 解掉了「上櫃減資 217 筆沒有官方交叉核對」。
⛔ 兩處「⛔ 卡住、要能執行 js」的敘述都是**寫下之後就沒人跟著更新**
——跟 CLAUDE.md 3.5④ 同一族（答案在自己家），只是這次連 grep 都不用，
是另一支程式的**檔頭自己講過**。

⇒ 已修正（commit `6248c11350`）：
- `db_status.py` C4 改標 ✅ 完成，敘述訂正
- `otc_parvalue_history.py --apply` 掛進 `capital.yml` 月排程（`continue-on-error: true`）
- NOT_YET 清單裡「上櫃減資 217 筆」那條移除，指到 C3

⚠ **仍然真的卡在「要能執行 js」的**（還沒有解，下一個人不用重試）：
- TWSE `zh/listed/violations/stop.html`（長期停止買賣，⛔ 但 G2 已經用 JSON 端點
  `t187ap26_L/O`／`tpex_cmode` 繞過這個問題，這頁不再是唯一路徑，只是覆蓋範圍較窄）
- TPEx `announce/market/change/reference.html` 的「上櫃休市日」那一半（⚠ 不是面額變更
  參考價那半——那半已經被 `pvChgRslt` 解掉；db_status 這條寫得有點混，兩件事共用了同一個 URL 描述）

⇒ ⭐ 判準沒有變：**换供料是換維護者的決定**（第五點）——這次是「發現已有的程式解決了」，
不是「新工具解決了」，⛔ 所以連裁定都不用送，是修 bug 等級的訂正。
下一次若真的要用 Firecrawl 之類的工具去接一個新供料，接不接一樣要先量、再送市場情報分析線裁。

---

## 三、這一輪學到、已經寫進 CLAUDE.md 的（⭐ 接手的人請讀那幾節）

1. **`grep` 把防呆濾掉了**（3.5④ 第七次）：我用
   `db_status.py | grep -E "^\| [A-Z][0-9] "` 只抓表格那幾列 ⇒ 讀到
   `B1／B2 0/2,850` ⇒ 差一點去派一趟多小時的回補，⛔ 而 main 上那兩格**早就 100%**。
   那道「這一趟是在分支上跑的」警語就印在表格正上方，**剛好被我的 grep 濾掉**。
   ⇒ ⭐ 落地：草稿標記蓋進**每一列**（可見性要由資料承擔，⛔ 不是由旁邊那行字）。
2. **一支掃全庫的自測紅掉 ⇒ 整條同步線關掉**（已第二次）⇒ 收成一條會自己算的守門：
   AST 掃誰在掃全庫，每一支都要在 pre-commit 清單裡或具名列在 `# SLOW-SCANNERS:`。
3. **沒寫母體的百分比事後重建不出來**（#29）：三個舊數字沒一個算錯，
   ⛔ 而我自己那兩個的母體今天**重建不出來**。
4. **一個「相對距離的單調函數」族被一個反例殺掉**（#35），⚠ 而那句話只否定那一族，
   ⛔ 不是「沒有函數」（三點 6.5 付過的代價）。

---

## 四、常駐的規矩（⛔ 最容易忘的幾條）

- 寫新檔之前先拿「它要做的那件事」**grep 一次 repo**（四點五第七次）。
- 新斷言要用 `mutate.py` 證明**會紅也會綠**；⚠ 「沒抓到」要先排除「突變沒套上去」
  與「baseline 本來就是紅的」。
- 突變若回「⚠ 崩潰」⇒ 把那一條斷言改成**自己接住例外**再判（七點②）。
- 累積型的檔一律**合併不是取代**；新增一個就要進 `push_data.sh` 的 `LEDGERS`。
- 信件歸檔：✅ 我是唯一收件線且已答覆／會同信簽收全 ✔ 才移走；
  ⛔ 還有人 ✖ 的只簽我自己那一格。
