# PREREG名單出場 乙：引擎與停損線建構器交件報告（回測線）

產出 2026-09-26（台北）。依據：台股策略線登錄 名單出場 seq1（sha db11230f58632a0d）乙、二；裁定線 seq189（發號、跌停賣不掉描述版）、seq192（S2 起點（甲）、ATR 原文、20 日照括號、描述臂 D1／D2）。

⛔ 沒跑 6 格（200 顆）、⛔ 沒讀年化／回落（#1 逐位元閘只比 repr、不印；nonid 只報次數、等待、現金比例、部位大小）。⛔ 沒 commit。

| 項 | 值 |
|---|---|
| 改的既有檔 | `backtest/research11.py`（+77／−7，只這一支） |
| 改前 | blob **52ce7677**（b1717d5c19） |
| 改後 | blob **5331e1cd65e73d7ef3564e01d5ed625283eec596**（sha256 67a47ff9…9c22） |
| 新檔 | `backtest/listexit_lines.py`（S1／S2 建線、#1 t−1 包裝）、`backtest/selftest_listexit.py`、`backtest/resultsListExit/engine_{fixtures,gate1,gate2,t1gate,nonid}.json`、本報告 |
| 原檔備份 | scratchpad `lx_research11.orig.py`（＝ blob 52ce7677） |
| 總結 | fixture **48/48**、回歸閘 1 **3/3**（18＋6＋A/B 84）、回歸閘 2 **13/13**、#1 t−1 逐位元閘 **3/3**、nonid **3/3**（`taskset -c 3`，1,705 秒） |

## 一、引擎新參數（全部預設關閉 ⇒ 與 b1717d5c19 逐位元相同）

| 參數 | 預設 | 行為 |
|---|---|---|
| `stop_line_le` | False | True ⇒ stop_line 判「收盤 ≤ 線」（S1）；⛔ 只能與 stop_line 同開 |
| `stop_proceeds` | None | "next" ⇒ stop_line 停損全出的淨入帳（沒動過 amt×(1＋g−COST)；賣半過 amt×(1＋g) − B×COST）進 trim_proceeds 同一個待買佇列 |
| `stop_block` | None | tradability.build 的 {trd, dn_o} ⇒ 只擋停損賣出（開盤跌停／停牌延到下一個可成交開盤），回 sl_block_days |
| `nx_order` | "before" | "after"（D1）⇒ 一般新部位先配、只用一般現金（現金 − 待買）；一般買不起或總數 ≥ 當天容量，剩下的名單才給待買 |
| stop_line＋trim gain | — | 可同開；同日先停損再賣半；已停損、或停損已觸發在等可賣開盤的部位不賣半 |

讀法：登錄「次一交易日的訊號池」＝ 從觸發日（t−1 收盤）算的次一交易日 t ＝ 賣出那天；停損／賣半與新部位都在 t 開盤，順序 停損 → 排程出場 → 賣半 → 新部位 ⇒ 與 seq3 讀法 b 一致（fixture D3）。

**D2（併池）＝ 既有 trim_proceeds=None，⛔ 不加參數**：賣得現金併入一般現金，有空槽時一般新部位照 min(equity/N, 現金) 買。⚠ 但登錄描述臂 ⓐ 字面「賣得現金閒置到那檔出場」與它不同：引擎沒有「綁到那檔出場」的閒置，None 路徑那筆錢在任何槽空出來時都可能被一般新部位用到（上限 equity/N）。⇒ T1／T2 的 D2 與 ⓐ 是同一次跑；組合格的 D2 ＝ 停損照 next、賣半併池（和 ⓐ 不同）。

**20 日**：照（a）不加冷卻（seq192 ③）；現有 20 根去重在訊號建構器，是「同檔上一個訊號之後 > 20 根有效 K 棒」。

## 二、停損線建構器 `listexit_lines.py`

- `s1_lines`：線 ＝ (1−0.10)×ep 常數，ep 照引擎（開盤，無效則收盤；fixture C3），配 `stop_line_le=True`。
- `s2_lines`：起始 ep − 2×ATR(訊號日 k)；有效 K 棒上收盤創新高（嚴格 ＞）才上調到 max(舊線, 收盤 − 2×ATR(當日))；停牌日沿用；收盤取引擎 closes。`high_start="entry_close"`（seq192 定案（甲））；`"above_ep"` 留著、不跑。
- ATR ＝ research11.wilder_atr，seq192 ② 確認與 tw-ta-exit-position 原文一致。訊號日有效 K 棒 ＜ 114 根：**0 筆**（#1 訊號要求 k ≥ 249）；ATR 無效而略過：0 筆。建線 S1、S2 各 1,688 筆（主窗 t−1 訊號 2,036 列中 xpos_H120 ≥ 0 的）。

## 三、閘門

- 回歸閘 1：regress_tradability 18、regress_delist 6 逐位元；改前（52ce7677）／改後 A/B **42 種組合 × 2 ＝ 84 組**逐位元（含 trim_proceeds next＋nx_cap、stop_line 無 tradable＋audit＋log、stop_line＋tradable＋delist、明寫新參數預設值）。
- 回歸閘 2：`selftest_avgengine3.py all` 27/3/15/3 全過（內含 avgengine2、avgengine、P9 全套、P9 基準臂 +27.69%／−42.5%、avgdown F1～F10）；resultsp9_engine 14 檔、resultsAvg engine_b*_ 12 檔逐位元組寫回、沒有多出檔。
- #1 t−1 閘：`listexit_lines.sim` 不開新參數 20 顆 ⇒ 與 resultsN17/regime_t1/seeds.csv t1 #1 逐位元（cagr／mdd／vol repr、first／end／trades、eq_sha）20/20。
- 查證：rerun17 opens 在停牌日（traded＝False）**129,159／129,159 全是 NaN**、有成交日 0 筆無效 ⇒ 原版停損在停牌日本來就延到下一個有效開盤；描述版 stop_block 與原版的差別**只在開盤跌停**。

## 四、fixture（48/48）

ATR 手算與獨立迴圈（A1、A2）；S2 兩讀法手算、進引擎、停牌日、ATR 無效（B1～B5）；S1 等號、9.01 不出、ep 規則（C1～C3）；停損待買全額、閒置版、同日（D1～D3）；S1＋T1 先 L1 後 L2、同日先停損不賣半、停損待賣中不賣半（E1～E3）；stop_block 只擋停損（F1、F2）；D1 兩例（G1、G2）；D2（H1）；隨機獨立重建 300/300（停損時點、停損＋賣半待買先進先出、每日待買數、不重複買、計數鍵）；整條管線無前視 200/200；突變體 12 個全抓到（ML_le、ML_nxstop、ML_block、ML_pend、ML_lag、MN_after、MN_gen、MB_hs、MB_ge、MB_down、MB_atr0、MB_fut）；None 路徑 600/600；防呆 11 條。

## 五、nonid（5 顆中位；⛔ 只報次數與結構量）

| 臂 | 停損 | 賣半 | 一般新部位 | 待買買進 | 期末未買 | 等待中位／p90 | 現金比例 均值／中位 | 待買部位占權益中位 | 待買大小占 slot 中位 | 停損後 20 日內又買回 |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 177 | 0 | 100 | 177 | 1 | 2／66.5 | 0.30／0.15 | 0.35 | 0.77 | 5 |
| S2 | 883 | 0 | **10** | 873 | 10 | 3／20 | 0.46／0.41 | 0.57 | 0.84 | 44 |
| T1 | 0 | 111 | 58 | 105 | 6 | 50／108 | 0.65／0.66 | 0.13 | 0.29 | 0 |
| T2 | 0 | 88 | 82 | 81 | 7 | 43.5／106 | 0.50／0.50 | 0.13 | 0.43 | 0 |
| S1＋T1 | 177 | 136 | **6** | 271 | 43 | 121.5／318 | **0.94／0.99** | 0.007 | **0.012** | 5 |
| S2＋T1 | 883 | 298 | **4** | 879 | 302 | 182／534 | **0.96／0.98** | 0.017 | **0.031** | 44 |
| ⓐ S1／S2 | 178／885 | — | 全部 | 0 | — | — | 0.23／0.46 均值 | — | — | 4／43 |
| ⓐ T1／T2（＝D2） | — | 111／88 | 全部 | 0 | — | — | 0.39／0.32 均值 | — | — | — |
| ⓐ S1＋T1／S2＋T1 | | | 全部 | 0 | — | — | 0.42／0.53 均值 | — | — | 5／44 |
| 跌停賣不掉 S1／S2 | 176／891 | | 100／10 | 175／881 | | 2／3 | 0.30／0.46 均值 | | | 4／41（擋賣 7／5 天次） |
| 跌停賣不掉 S1＋T1／S2＋T1 | | | 6／4 | 266／887 | 42／299 | 131／177 | 0.94／0.96 均值 | | | （擋賣 7／5） |
| D1 T1／T2 | | | 107／114 | 56／49 | 54／39 | 481.5／447 | 0.68／0.58 均值 | 0.06／0.07 | 0.31／0.34 | |
| D1 S1＋T1／S2＋T1 | | | 78／10 | 200／873 | 116／308 | 387.5／193 | 0.83／0.93 均值 | 0.08／0.04 | 0.15／0.07 | |
| D2 S1＋T1／S2＋T1 | | | 100／10 | 177／873 | 1／10 | 2／3 | 0.58／**0.97** 均值 | 0.20／0.00 | 0.48／0.0001 | |

停損後 20 日內又買回的那幾筆，自己的價格報酬（出場價 ÷ 進場價 − 1）：S1 平均 −4.6%、中位 −10.0%；S2 平均 +4.3%、中位 −4.3%。

⚠ **結構性發現（跑 6 格前請裁定線看）**：
1. 「待買先配、一筆一檔」＋停損頻繁 ⇒ **一般新部位幾乎進不來**：S2 整窗只有開頭 10 筆一般新部位，其餘 873 筆全是待買（同一份本金在換手）；S1＋T1 只有 6 筆、S2＋T1 只有 4 筆。
2. 組合格會**碎片化螺旋**：賣半 ⇒ 待買只是半份；待買買進的部位再賣半或停損，下一筆更小，但每筆都佔一整槽；一般現金（賣半版的現金、閒置的錢）因槽被小部位佔滿而投不出去 ⇒ **S1＋T1、S2＋T1 現金比例均值 0.94～0.96、中位 0.98～0.99**，待買部位中位只有 slot 的 1～3%。D2 S2＋T1 更極端（現金均值 0.97、待買部位 slot 的 0.01%）。
3. D1（一般優先）讓一般新部位回來（T1 58→107），但待買等待中位拉到 450～480 天，期末未買 39～116 筆。
⇒ 照登錄字面跑，組合格的結果主要反映「現金放著」，不是停損停利本身。這是登錄規則 × 引擎口徑的後果；本件照規則做、⛔ 沒改。

## 六、6 格＋描述臂的完整參數

共同：`simulate_mtm(sig, "H120", 10, np.random.default_rng(1000 + r), closes, opens, ncal, return_equity=True, **kw)`
- sig、closes、opens、ncal ＝ `listexit_lines.setup_t1()`（rerun17 快照、AND、t−1 閘、主窗）
- nx_cap 不給（＝ None ＝ 10 槽）；不開 tradable、不傳 delist
- `S1L = listexit_lines.s1_lines(sig, "H120", opens, closes, x=0.10)`
- `S2L, _ = listexit_lines.s2_lines(sig, "H120", opens, closes, lambda s: research11.load_bars(s, mk.get(s, "twse"), cal), mult=2.0, high_start="entry_close")`
- `BLK = tradability.build(set(sig["sid"]), cal)`
- `TR15 = {"kind": "gain", "x": 0.15, "frac": 0.5}`；`TR30 = {"kind": "gain", "x": 0.30, "frac": 0.5}`

| 臂 | kw |
|---|---|
| S1 | stop_line=S1L, stop_line_le=True, stop_proceeds="next" |
| S2 | stop_line=S2L, stop_proceeds="next" |
| T1 | trim_rule=TR15, trim_proceeds="next" |
| T2 | trim_rule=TR30, trim_proceeds="next" |
| S1＋T1 | stop_line=S1L, stop_line_le=True, stop_proceeds="next", trim_rule=TR15, trim_proceeds="next" |
| S2＋T1 | stop_line=S2L, stop_proceeds="next", trim_rule=TR15, trim_proceeds="next" |
| ⓐ 閒置（各格） | 同上但去掉 stop_proceeds 與 trim_proceeds |
| 跌停賣不掉（S1、S2、S1＋T1、S2＋T1） | 同上格再加 stop_block=BLK |
| D1（T1、T2、S1＋T1、S2＋T1） | 同上格再加 nx_order="after" |
| D2（T1、T2） | ＝ ⓐ 閒置（trim_rule 不帶 trim_proceeds） |
| D2（S1＋T1、S2＋T1） | 停損照 stop_proceeds="next"、去掉 trim_proceeds |
