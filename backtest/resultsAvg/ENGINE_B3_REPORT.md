# PREREG攤平停利 乙二：nx_cap（待買總檔數上限放寬）交件報告（回測線）

產出 2026-09-26（台北）。依據：裁定線 seq186 §三 選（乙）「賣得現金買下一檔」總檔數上限放寬到 10；seq188（#1 N＝10 的停損／停利換股同在 10 槽上限內）。前一版 12c39cb810（trim_proceeds="next"，ENGINE_B2_REPORT.md）。

⛔ 沒有跑乙的 2 格、⛔ 沒有讀年化／回落（nonid 只取計數鍵、等待天數、equity sha）。⛔ 沒有 commit。

| 項 | 值 |
|---|---|
| 改的既有檔 | `backtest/research11.py` 只有這一支（+31／−3，7 處） |
| 改前 | blob **daf1f75d21548cc11b0da87301d0f200c57a5999**（12c39cb810） |
| 改後 | blob **52ce7677bced465cc7a0ce2ab03b9be84f9420b4**（sha256 bbf99768…56d2dd），100644 |
| 原檔備份 | scratchpad `rei2_research11.orig.py`（＝ blob daf1f75d）；selftest 從 git blob 取改前引擎 |
| 換檔 | 暫存檔先過 fixture 27/27、A/B 76/76；換檔前驗工作樹仍是 daf1f75d，同目錄暫存名 `mv -f` 原子換上 |
| 新檔 | `backtest/selftest_avgengine3.py`、`resultsAvg/engine_b3_{fixtures,gate1,gate2,nonid}.json`、本報告 |
| 總結 | **fixture 27/27、回歸閘 1 3/3（18＋6＋A/B 76）、回歸閘 2 15/15、nonid 3/3**（`selftest_avgengine3.py all`，`taskset -c 3`，1,422 秒） |

## 一、參數

`simulate_mtm(..., trim_rule={"kind":"gain","x":0.15,"frac":0.5}, trim_proceeds="next", nx_cap=10)`

- `nx_cap=None`（預設）：待買容量 ＝ 當天容量 ⇒ 與 12c39cb810 逐位元相同；seq188 #1（N＝10）就是這條路徑（fixture：nx_cap＝N 與 None 逐位元同，只多 `x_nx_over＝0`）。
- 整數 K：待買可以用到總部位數 ≤ K_t ＝ max(K, 當天容量)；**一般新部位只在總部位數 ＜ 當天容量時才買**（裁定線的讀法，寫進 docstring）。
- 同一天：挑中名單長度 ＝ max(min(待買筆數, K_t − 總數), 當天容量 − 總數)，待買先配 ⇒ 一般新部位買完時總數 ≤ 當天容量、待買買完時總數 ≤ K_t。
- 防呆：只能與 `trim_proceeds="next"` 同開；純量 n_slots 時 K ≥ n_slots；K 要是整數（bool／9.5／'10' ⇒ ValueError）；caps 開啟時 K ＜ caps 不報錯。
- 多回傳（只在 K 給了時）：`x_nx_over`（總數已 ≥ 當天容量時由待買買進的筆數）。

⚠ 附記：`max(K, caps[t])` 在行為上只影響 `x_nx_full_days` 的計數——caps[t] ＞ K 時一般容量那條已經讓待買進得去（待買先配）；突變體 MK_caps 是靠 full_days 抓到的。

## 二、回歸閘

- 閘 1：`regress_tradability` 18、`regress_delist` 6 逐位元；改前（daf1f75d）／改後 A/B **38 種組合 × 2 種子 ＝ 76 組**逐位元（含 trim_proceeds="next" 6 種：audit、log、tradable＋delist＋audit＋log、caps、pick＋queue、明寫 nx_cap=None）。
- 閘 2：`selftest_avgengine2.py all` 結束碼 0：29/29、3/3、18/18、3/3；內含 selftest_avgengine 56/3/13/3、selftest_p9engine 48/4/13/12、builders 34/11/addcount、selftest_avgdown F1～F10、**P9 基準臂 +27.69%／−42.5% 逐位元**。被改寫的入庫檔（resultsp9_engine 14、resultsAvg engine_b_*／engine_b2_* 8）已逐位元組寫回、沒有多出檔。副作用：`~/p9run/0dc5d62b2a/backtest/research11.py` 是改後版。

## 三、fixture（27/27）

| # | 內容 | 結果 |
|---|---|---|
| K1 | N=8、K=10：8 檔持有＋2 筆待買 ⇒ 第 9、10 檔由待買買進（全額）、一般 0 | ✅ |
| K2 | 第 11 筆待買：總數 10 ⇒ 等（full 1）；有檔出場 ⇒ 下一個量測日買第 10 檔（waits 9／7／14） | ✅ |
| K3 | 總數 8（其中 2 檔是待買買進的）、沒待買 ⇒ 一般新部位不買；總數 7 ⇒ 只買 1 檔 | ✅ |
| K4 | x_nx_over＝3、最多 10 檔、獨立重建相符 | ✅ |
| K5 | 同例 nx_cap=None ⇒ 最多 8 檔、待買要等到 t=55 | ✅ |
| K6／K7 | 同日混合：總數 7＋待買 2 ⇒ 兩檔待買、一般 0；總數 5＋待買 1 ⇒ 待買 1＋一般 2 | ✅ ✅ |
| K8／K9 | caps：K_t＝max(K, caps)（caps 11 ⇒ 第 11 檔、full 0）；caps 5＋K 10 ⇒ 待買開到第 6、7 檔 | ✅ ✅ |
| 隨機 | 獨立重建 300 世界（K＝N＋0～3）300/300：待買數 ＝ min(K−總數, 候選, 待買)、一般新部位買進時總數 ＜ N、總數 ≤ K、全額先進先出、計數鍵；有 over 122、到 K 而等 49 個世界 | ✅ ✅ |
| 無前視 | 200 世界（一半 tradable）200/200 前段不變、198 後段不同 | ✅ |
| 突變體 | MK_free0（K 沒作用）、MK_norm（一般新部位也用到 K）、MK_over（待買到 K＋1）、MK_enter（總數 ≥ N 不進挑股區）、MK_caps（不取 max）⇒ 全部抓到 | ✅ ×5 |
| None | 省略／明寫 None × next／閒置版／全關 × 60 世界 ⇒ 與 12c39cb810 逐位元 240/240；nx_cap＝N ≡ None 60/60 | ✅ ✅ |
| 防呆 | 6 條 ValueError＋caps 時 K＜caps 不報錯 | ✅ ×7 |

## 四、nonid：8 版與放寬 10 版並列（乙的設定、5 顆；⛔ 只報次數與等待天數）

| r | 8 版 待買買進／槽滿等／期末未買 | 8 版 等待 p25／中位／p75／p90／最長 | 10 版 待買買進／over／到 10 而等／期末未買 | 10 版 等待 p25／中位／p75／p90／最長 |
|---|---|---|---|---|
| 0 | 64／45／3 | 16／46.5／76.5／98.4／120 | 89／43／6／3 | 10／16／21／39／102 |
| 1 | 71／47／2 | 30／69／94／107／120 | 75／34／8／3 | 7／14／19／39.4／102 |
| 2 | 62／48／4 | 28.25／63／91／102／120 | 74／35／8／3 | 8／13／18.75／30.1／102 |
| 3 | 71／58／1 | 28.5／58／92／102／120 | 68／32／6／3 | 7／14／18／22.1／102 |
| 4 | 75／51／2 | 19.5／58／79.5／98.2／131 | 74／41／8／2 | 5.25／15／23.75／39.1／102 |
| 合併 | 343 筆 | p10 11、**中位 56**、平均 56.8、≤20 天 83 筆 | 380 筆 | p10 2、**中位 14**、平均 18.2、≤20 天 299 筆 |

✅ 基準臂 sha ＝ pre_B_seeds；✅ nx_cap=None 明寫 ＝ 8 版；✅ 10 版 5 顆都與 8 版不同、over 32～43。

## 五、researchAvg 乙兩格應填（⛔ 本件沒改 researchAvg.py）

```python
ENGINE_KW_B = {"By": {"add_rule": {"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}},
               "Ci": {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}, "trim_proceeds": "next", "nx_cap": 10}}
# 乙三 描述（閒置版）：{"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}
```
