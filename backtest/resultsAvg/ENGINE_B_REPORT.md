# PREREG攤平停利 乙：引擎擴充交件報告（交裁定線收下用；回測線）

產出 2026-09-25（台北）。依據：台股策略線登錄 **PREREG攤平停利 seq2**（sha 17449e5624991924）乙一 2-B ⓓ、乙二 2-C ⓘ；
裁定線 **seq177 §一①** 准 (a)「擴充引擎兩個參數（跌 x 加碼、漲 x 賣半）：照 P9 那次——預設關閉、兩道回歸閘＋fixture，交件收下才跑」；
回測線 2122 §三（引擎不支援的逐條證明）、§四①（門檻照登錄字面，裁定 seq177 收下）。

⛔ **本件沒有跑乙的 2 格**，⛔ 沒有讀任何年化／回落／比值（nonid 只取計數鍵與 equity 的 sha）。
⛔ 沒有 commit。改動只在工作樹 `~/tw-p17`（分支 claude/stock-analysis-backtest-iv9xji）。

| 項 | 值 |
|---|---|
| 改的檔 | `backtest/research11.py`（只改這一支既有 .py；**+39／−5 行**，8 個 hunk） |
| 改前版本 | `git rev-parse HEAD:backtest/research11.py` ＝ **e25799728f66ea494e1805ceb8b6caf9848a5d7e**（HEAD 69cdc62bd8；最後改它的 commit 9c72da5997＝P9 擴充；sha256 63b34766…5a187d） |
| 改後版本 | git hash-object **d8d177e7a597237c0318f1e9473584ee92a022e2**（sha256 2e518801…ffe093）；檔案權限維持 100644 |
| 原檔備份 | scratchpad `eng_research11.orig.py`（與 HEAD blob 逐位元組相同）；selftest 一律從 git blob 取改前引擎，⛔ 不靠備份 |
| 換檔方式 | 先在 scratchpad 暫存檔改好（`eng_research11.new.py`）、在暫存檔上跑完 fixture 56/56 與 A/B 矩陣 56/56，再 `cp` 到同目錄暫存名、`mv -f` 一次原子換上（⛔ 沒有邊改邊存） |
| 新檔 | `backtest/selftest_avgengine.py`、`backtest/resultsAvg/engine_b_{fixtures,gate1,gate2,nonid}.json`、本報告 |
| 總結 | **fixture 56/56、回歸閘 1 3/3（18＋6＋A/B 56）、回歸閘 2 13/13（P9 selftest 48＋4＋13＋12、builders 34＋11、addcount 逐位元組、P9 基準臂 +27.69%／−42.5% 逐位元）、nonid 3/3 ⇒ 全過** |

---

## 一、新參數（⛔ 沒有新增參數名；在既有兩個參數上各加一種 kind，⛔ 預設關閉）

| 參數 | 新 kind | 格 | 預設 | 定義 |
|---|---|---|---|---|
| `add_rule` | `{"kind": "loss", "x": 0.10[, "size": 0.5][, "short": "skip"]}` | 乙一 2-B ⓓ 個股攤平 | `add_rule=None`（關） | 部位**收盤[t−1] ≤ (1 − x) × 進場價** ⇒ t 開盤加 `size` ×【加碼當天的 slot】（equity[t−1]÷N）；每部位只一次；`short="skip"`（預設）現金不足不加並記 `x_add_short`，機會用掉、⛔ 不每天重試；`"partial"` 另備 |
| `trim_rule` | `{"kind": "gain", "x": 0.15[, "frac": 0.5]}` | 乙二 2-C ⓘ 個股停利 | `trim_rule=None`（關）；`kind` 省略 ＝ `"loss"` ＝ 原 2-C ⓐ | 部位**收盤[t−1] ≥ (1 + x) × 進場價** ⇒ t 開盤賣 `frac`（以股數計）；只一次；賣得現金照 2-C ⓐ 原樣留現金（cash_mode="zero" ⇒ 報酬 0）；剩下的照原排程（第 120 根收盤）出場 |

共同（⭐ 全部沿用 P9 那次的同一段程式，只多一個觸發分支）：

- **時序**：只讀 t−1 收盤；成交在 t 開盤（還原開盤）。新兩行都標了 `# _XLAG`（鑑別力突變點由 6 個變 7 個；乙二與 2-C ⓐ 共用同一行讀取）。
- **可交易性**：買（加碼）要開盤有限且 > 0，tradable 開啟時另要有成交、開盤不是漲停；賣（賣半）同上但改成開盤不是跌停。做不成 ⇒ 下一個交易日開盤再試（每天記 `x_add_blocked_days`／`x_trim_blocked_days`），直到排程出場日為止；撞到出場日 ⇒ 不做。
- **計數鍵與 audit**：沿用既有的 `x_add_trig／x_add_n／x_add_short／x_add_blocked_days`、`x_trim_n／x_trim_blocked_days`，audit `kind` 仍是 `"add"`／`"trim"` ⇒ `p9_controls.mbar_of(o, "add")`、`researchAvg._b_arm` 不必改就能用。
- **成本**：P9 慣例（成本基礎 B；賣 f 付 f×B×COST；加買 a ⇒ B＋a；沒動過的部位走原式）。
- **防呆**：`x` 必須明給（⛔ 不給預設值，免得 −10%／+15% 靠預設值帶進來）；loss 的 x ∈ (0,1)、gain 的 x ＞ 0、frac ∈ (0,1)；kind 打錯、乙一乙二同開、與 stop／stop_line／weight_fn／bench 同開 ⇒ ValueError（互斥規則沿用 P9）。
- **等號與寫法**：照登錄字面「收盤 ≤ 0.90 × P0」「收盤 ≥ 1.15 × P0」（裁定 seq177 §一① 收下回測 2122 §四①）⇒ 程式式 `c1 <= (1.0 - x) * ep`、`c1 >= (1.0 + x) * ep`，等號算觸發；`1 − 0.10 == 0.90`、`1 + 0.15 == 1.15` 在浮點上逐位元成立（fixture 驗）。⚠ 既有 2-B ⓐ／2-C ⓐ 是比值式 `c1/ep − 1 ≥ x`、`≤ −x`，⛔ 沒改（改了會破壞 P9 的逐位元重現）⇒ 見 §六 讀法①。

---

## 二、回歸閘 1（新 kind 不傳 ⇒ 與改前逐位元相同）

| 閘 | 比了什麼 | 結果 |
|---|---|---|
| `regress_tradability.py check` | 18 組（6 種組態 × 3 種子）：equity sha、全部純量、log | ✅ 18/18 逐位元相同 |
| `regress_delist.py check` | 6 組（3 種組態 × 2 種子）：equity sha、全部純量 | ✅ 6/6 逐位元相同 |
| 改前（git blob e2579972）／改後 A/B 矩陣 | 真資料（tw-p17 工作樹、門檻B、H120、N=8）上 **28 種既有參數組合 × 種子 0、1 ＝ 56 組**。其中 14 種是 P9 之前就有的（plain、stop fix／trail、log、queue＋d_max、bench、weak＋report_maxw＋maxw_detail、weight_fn、逐日 caps、cap_fn、pick、tradable、tradable＋delist＋audit＋log、stop_line＋tradable），14 種是 **P9 的五個參數**（entry_tranches k=2＋audit、k=3；add_rule gain＋audit、gain partial、flag、hold；trim_rule＋audit、trim kind="loss" 明寫、trim＋tradable＋delist＋audit＋log、gain＋tradable＋delist＋audit；size_mult_by_regime 1.5×MA60、0.5×MA20；regime_trim MA60＋audit、MA10＋tradable）。比 equity bytes、**全部回傳鍵（含 x_ 鍵與 x_cost_days）**、log、audit | ✅ 56/56 逐位元相同 |

## 三、回歸閘 2（既有 selftest 全過；P9 基準臂在原資料原窗重現）

`selftest_avgengine.py gate2`：13/13 過（574 秒；整支 `taskset -c 3` 綁在 1 個核心上跑）。

| 項 | 結果 |
|---|---|
| `selftest_p9engine.py all`（改後引擎；它的「改前」是 P9 之前的 blob 664e2ea2） | ✅ 結束碼 0；fixtures **48/48**、gate1 **4/4**（regress 18＋6、A/B 28、AFC W1 前 40 顆 × 5 欄）、gate2 **13/13**、nonid **12/12**，與 P9 交件時的條數相同（417 秒） |
| **P9 基準臂**：0dc5d62b2a archive、浮動窗 [523, 2855)，200 顆 | ✅ 年化中位 **+27.69%**（0.2768772767858816）／回落中位 **−42.5%**（−0.4250499165027687）＋p10/p90、槽、筆、曝險，與 `resultsp9/cells.csv` **逐位元相同**；b 臂、seeds.csv 14 欄、k=1、開著沒觸發、ⓑ 共用、P7 兩列也都逐位元相同 |
| `selftest_p9_builders fixtures` | ✅ **34/34** |
| `selftest_p9_builders real` | ✅ **11/11** |
| `selftest_p9_builders addcount --procs 1`（2-B 三格 × 200 顆、改後引擎） | ✅ `b2_addcounts.csv` 與入庫版**逐位元組相同**；summary 的 cells 也相同 |
| 既有結果檔 | ✅ 兩支 selftest 會改寫 `resultsp9_engine/` 的 14 個入庫檔 ⇒ 跑前把位元組存在記憶體、跑完逐檔寫回，**確認逐位元組相同、沒有多出新檔**；這次的輸出摘要記在 `engine_b_gate2.json` |

⚠ 附帶的副作用（照 P9 selftest 的設計）：`selftest_p9engine gate2` 會把工作樹的 research11.py 複製到 `~/p9run/0dc5d62b2a/backtest/`（repo 外的執行目錄），所以那裡現在放的是改後引擎。

## 四、fixture（`selftest_avgengine.py fixtures`：56/56 過）

預期值一律用獨立手算式，⛔ 不呼叫引擎內部函式；容差 1e-12；N 與價格都是手寫的小世界（`selftest_p9engine.px`）。

| # | fixture | 結果 |
|---|---|---|
| 0 | 浮點前提：`1−0.10 == 0.90`、`1+0.15 == 1.15` | ✅ |
| **乙一 loss** | | |
| L1 | **觸發日**：收盤[20]＝8.9 ≤ 9.0 ⇒ t=21 開盤 8.8 加 0.23625（＝0.5×equity[20]/2）；之後跌到 −30% **不再加（只一次）**；期末 ＝ (0.5−w)＋(0.5＋w×10/8.8)×0.7 − (0.5＋w)×COST | ✅ 0.797369073864 |
| L2 | **等號邊界**：收盤 ＝ 9.0 ＝ 0.90×10 ⇒ 觸發；期末 ＝ 0.95 − 0.7375×COST | ✅ |
| L2' | 收盤 9.01 ⇒ 整段不觸發 | ✅ |
| L2'' | **讀法鑑別**：同一個 9.0 換比值式（9.0/10−1 ＝ −0.09999999999999998）⇒ 不觸發 ⇒ 字面式／比值式在這筆分得出來 | ✅ |
| L3 | 進場當天收盤就 ≤ 0.90×進場開盤 ⇒ 次日加（與 gain 型、甲 A3 同口徑） | ✅ |
| L4 | **現金不足（skip）**：要 ≈0.105、現金只有 0.031 ⇒ 不加、`x_add_short=1`；之後別的部位出場現金回來、股價仍在 −12%～−30% ⇒ **也不再加**（機會已用掉）；期末 ＝ 0.6 − COST | ✅ |
| L4' | 現金不足（partial，非預設）⇒ 只加 0.031 | ✅ |
| L5 | **漲停遞延**：t=21 開盤漲停 ⇒ t=22 加、金額用 t=22 的 slot、`blocked=1`；期末手算相符 | ✅ |
| L5' | 停牌 t=21、22 ⇒ t=23 加、`blocked=2` | ✅ |
| L5'' | 加碼日開盤**跌停**不擋買 | ✅ |
| L6 | 遞延撞到排程出場（t=59 漲停、t=60 出場）⇒ 不加（trig 1、n 0） | ✅ |
| L7 | 錨是**進場價**、不是高點：漲到 12 再回 10.8 ⇒ 不加；收盤 9.0 ⇒ 加 | ✅ |
| L8 | **逐部位狀態**：同一檔兩段持有（進場 10／9.0）⇒ 各自對自己的進場價判、各加一次（t=16、t=46） | ✅ |
| **乙二 gain** | | |
| G1 | **觸發日**：收盤[20]＝11.6 ≥ 11.5 ⇒ t=21 開盤 11.8 賣半（拿回 0.59、成本 0.5×COST、現金留著）；漲到 +30% 不再賣；期末 ＝ 1.24 − COST | ✅ 1.234150000000 |
| G2 | **等號邊界**：收盤 ＝ 11.5 ＝ 1.15×10 ⇒ 觸發；期末 ＝ 1.15 − COST | ✅ |
| G2' | 收盤 11.49 ⇒ 不觸發；期末 ＝ 1.149 − COST（沒動過的部位走原式） | ✅ |
| G2'' | **讀法鑑別**：11.5 換比值式（11.5/10−1 ＝ 0.1499999…）⇒ 不觸發 | ✅ |
| G3 | 進場當天收盤就 ≥ 1.15×進場開盤 ⇒ 次日賣半 | ✅ |
| G4／G4' | **跌停遞延**、停牌遞延 ⇒ t=22 賣、`blocked=1`；期末同 G1 | ✅ |
| G4'' | 賣出日開盤**漲停**不擋賣 | ✅ |
| G5 | 遞延撞到排程出場 ⇒ 不賣半；期末 ＝ 1.16 − COST | ✅ |
| G6 | 錨是**進場價**、不是低點：先跌到 8 再反彈 +15% 到 9.2 ⇒ 不賣 | ✅ |
| G7 | 逐部位狀態：同一檔兩段持有（進場 10／11.5）⇒ 各自判（t=16、t=46） | ✅ |
| G8 | 方向：跌的路徑 gain 型不賣、漲的路徑 loss 型不加 | ✅ |
| **不變性** | | |
| 6 條 | 既有型（trim 省略 kind、trim kind="loss" 明寫、add gain）× 跌／漲兩條路徑 ⇒ 改前（git blob）／改後逐位元同（**含 x_ 鍵與 audit**） | ✅ |
| 1 條 | 全關 ⇒ 與改前逐位元同（equity bytes＋全部回傳＋audit） | ✅ |
| 2 條 | 新型開著但沒觸發（loss x=0.999、gain x=1e9）⇒ 與改前逐位元同（x_ 鍵除外） | ✅ |
| 2 條 | ENGINE_KW_B 兩格明寫 size／short／frac ＝ 省略時的預設（逐位元） | ✅ |
| **無前視＋鑑別力** | 突變體 ＝ 7 個 `# _XLAG` 讀取點 [t−1] ⇒ [t]（改讀當天） | |
| 2＋2 條 | 手寫：個股收盤 t=30 起 −20%（loss）／+20%（gain）⇒ 正確引擎 t≤30 的交易與 equity[:30] 不變、之後確實不同；突變體前段就不同（**被抓到**） | ✅ |
| 2＋2 條 | **隨機突變 300 個世界 × 兩型**（3 檔隨機漫步、5～7 筆訊號、隨機 s、一半世界開隨機漲跌停／停牌；改 t=s 的收盤與 s+1 起的開盤收盤，t=s 的開盤不動；s 避開排程出場日）：正確引擎 **300/300、300/300** 前段不變；突變體被抓到 **56/300（loss）、95/300（gain）**；有觸發的世界 244／213、後段確實不同 242／245 | ✅ |
| **防呆** | loss 沒給 x／x=0／x=1／x<0、gain 沒給 x／x=0／frac=1、兩個 kind 打錯、乙一乙二同開、loss 與 stop 同開 ⇒ ValueError | ✅ 11 條 |

## 五、⛔ 不是恆等輸出（`nonid`：3/3 過；⛔ 只報計數與 sha 是否不同）

設定 ＝ 乙要跑的那一組：`researchP9run.setup`（edc6f8002f 快照、主窗 2017-03-02～2026-08-24、S1 2,881 筆、H120、N=8、種子 99000＋r），r＝0～4。

| r | 基準臂 sha ＝ pre_B_seeds.csv | By：觸發／加成／現金不足／遞延 | Ci：賣半／遞延 | By、Ci 與全關不同 |
|---|---|---|---|---|
| 0 | ✅ | 92／15／77／0 | 67／0 | ✅ ✅ |
| 1 | ✅ | 85／16／69／0 | 73／0 | ✅ ✅ |
| 2 | ✅ | 80／13／67／0 | 66／0 | ✅ ✅ |
| 3 | ✅ | 90／13／77／0 | 72／0 | ✅ ✅ |
| 4 | ✅ | 82／10／72／0 | 77／0 | ✅ ✅ |

描述（⛔ 不判）：
- 與回測 2122 §三 的開跑前近似對帳：Ci 賣半次數與 pre「+15% 成交」5 顆逐顆相同；By 觸發比 pre「−10% 觸發」多 0～3（開啟後加碼吃掉現金、之後的新部位金額變了，pre 是在基準臂部位上數的近似 ⇒ 本來就不要求相等）。加成 10～16 次 ⇒ 與 2122「實際加成約 15 次、不會落『結構上近乎不可得』」一致（正式的 200 顆中位由 body 報）。
- 字面式 vs 比值式（讀法①）：這 5 顆 By、Ci 的 equity sha **完全相同**、觸發數差 0 ⇒ 實務上兩式在這組資料沒有分岔到（小世界 fixture L2''／G2'' 證明它們在剛好落在門檻的價格上分得出來）。

---

## 六、有兩種讀法、本件選了一種的地方（⛔ 沒有改規則；請裁定線過目）

| # | 登錄原文 | 兩種讀法 | 本件選 |
|---|---|---|---|
| ① | 乙一「收盤 ≤ 進場價 × 0.90」、乙二「收盤 ≥ 進場價 × 1.15」 | 字面式 `c ≤ 0.90·ep`／引擎既有 2-B ⓐ、2-C ⓐ 的比值式 `c/ep − 1 ≤ −0.10` | **字面式**（與甲 A2 同；裁定 seq177 §一① 已收下 2122 §四①）。⚠ 因此乙與 P9 的鏡像格（2-B ⓐ、2-C ⓐ）在「價格剛好落在門檻」時式子不同；真資料 5 顆沒有分岔 |
| ② | 乙一「加碼半份（0.5 slot）」 | 加碼當天的 slot（equity[t−1]÷N）／進場日的 slot | **加碼當天的 slot**（＝ P9 讀法④，裁定 seq162 收下；登錄「同 2-B」） |
| ③ | 乙一「現金不足 ⇒ 不加、記次數（同 2-B）」 | 當天不加、之後每天重試／這個部位的機會就用掉 | **用掉、不重試**（＝ 2-B 現行；fixture L4） |
| ④ | 「持有中某檔收盤」 | 含進場當天收盤／從進場次日收盤起 | **含進場當天**（＝ 2-B ⓐ gain 現行、甲 A3「觀察期含 e 當天」；fixture L3、G3） |
| ⑤ | 次日開盤成交、漲跌停／停牌（登錄乙沒寫） | 放棄／延到下一個可成交開盤 | **延到下一個可成交開盤**，直到排程出場日（＝ P9 讀法③）；加碼金額用實際成交那天的 slot（fixture L5、L6、G4、G5） |
| ⑥ | 「進場價」 | 該部位進場日的還原開盤／該檔之前某次進場價或持有期高低點 | **該部位自己的進場價**（ep＝進場日還原開盤），同一檔再進場重新計（fixture L7、L8、G6、G7） |
| ⑦ | 乙二「賣一半」 | 以股數一半／以當時市值一半 | **以股數計 frac＝0.5**（＝ 2-C ⓐ 現行；兩者在同一價位賣出時相同） |
| ⑧ | 乙二「賣得現金的處理照 2-C ⓐ 原樣」 | — | 留現金（cash_mode="zero"，報酬 0）；之後新部位的 slot 照 equity÷N、金額 min(slot, 現金)（＝ 2-C ⓐ） |

---

## 七、`researchAvg.py` 的 `ENGINE_KW_B` 應填的值（⛔ 本件沒改 researchAvg.py）

```python
ENGINE_KW_B = {"By": {"add_rule": {"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}},    # 乙一 2-B ⓓ
               "Ci": {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}}                     # 乙二 2-C ⓘ
```

- size／short／frac 明寫的值 ＝ 引擎預設，逐位元相同（fixture 驗）；明寫是為了讓登錄的「0.5 slot」「現金不足不加」「賣一半」在呼叫端看得到。
- `_b_arm` 的 `C.mbar_of(o, "add")`、`x_add_n`「結構上近乎不可得」判斷、`x_` 欄的彙總 ⇒ 鍵名沿用，**不必改**。
- ⚠ **跟著要處理的（researchAvg 的維護者，⛔ 不是本件）**：
  1. `selftest_avgdown.py` 的 **F10 現在會紅**（ⓑ 斷言「add_rule kind＝loss 會 ValueError」已不成立；本線實跑確認 `AssertionError: ⛔ add_rule kind＝loss 居然能跑`）⇒ F10 是「引擎沒有這個能力」的證明，引擎補上後它本來就該改寫或退役；`main_pre_B` 會呼叫它（pre 已跑完、body 不呼叫）。
  2. researchAvg.py 讀法 B0 與 `main_body_B` 的 docstring 仍寫「引擎沒有」，填值時一併改。

---

## 八、research11.py 改動範圍（`git diff -U0` 的 hunk，新檔行號）

| 位置（新檔行號） | 內容 |
|---|---|
| 491 | docstring：add_rule 列出 `{"kind": "loss", "x": 0.10}` ⓓ |
| 496–497 | docstring：trim_rule 列出 `{"kind": "gain", "x": 0.15, "frac": 0.5}` ⓘ |
| 510–524 | docstring：「PREREG攤平停利 乙」一段（規格、等號與字面式、與比值式的差、x 必須明給） |
| 630 | `_trim_kind = None`（trim_rule 關時為 None） |
| 652–655 | 防呆：add kind 多 `"loss"`、loss 要明給 x ∈ (0,1) |
| 660–668 | 防呆：trim_rule 讀 kind（預設 "loss"）；gain 要明給 x＞0、frac ∈ (0,1)；loss 走原本那一行檢查 |
| 747–750 | `_x_day` 減半：`if _trim_kind == "gain": c1 >= (1+tx)·ep` 分支；原式 `c1/ep − 1 <= −tx` 由 `if` 改成 `elif`，運算式一字未改 |
| 827–829 | `_x_day` 加碼：`elif _add_kind == "loss": c1 <= (1−x)·ep` 分支（`# _XLAG`） |

−5 行 ＝ 兩行 add kind 檢查（加 "loss"）、兩行 trim 檢查（拆成 kind 分流）、一行 trim 條件（if → elif）。
⭐ 原路徑的運算式一個字都沒改；新分支只在 `add_rule["kind"]=="loss"`／`trim_rule["kind"]=="gain"` 時走到。
