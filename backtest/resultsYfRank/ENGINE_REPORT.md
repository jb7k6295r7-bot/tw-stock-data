# PREREG營飆排名：引擎 pick_tie 交件報告（回測線，2026-09-26）

依據：登錄 seq1（sha 6a1a8643d7e61b4a）§二「同分用同一顆種子的抽籤決定」；裁定 seq199；退化檢查 9d07d9505d（PRE_REPORT §四 建議）。
⛔ 判定 4 格＋K0 沒跑、⛔ 沒讀報酬（gate_c 只比 repr、不印）；⛔ 沒 commit。

| 項 | 值 |
|---|---|
| research11.py | blob 5331e1cd（84de67ccaf）⇒ **e237a0f8b0f908593699a8fbb13a57bd1a898fbd**（+21／−2） |
| researchYfRank.py | 加 body 段（§三 判定＋K0；寫好、⛔ 未跑）⇒ blob 7bb3872f |
| 新檔 | backtest/selftest_yfrank.py（blob 2a6ee13f）、resultsYfRank/engine_{fixtures,gate_a,gate_b,gate_c,gate1,gate2}.json、本報告 |
| 原檔備份 | scratchpad yfr2_research11.orig.py、yfr2_researchYfRank.orig.py |
| 結果 | fixtures 14/14、(a) 1/1、(b) 1/1、(c) 1/1、gate1 3/3、gate2 11/11（taskset 2 核，1,864 秒） |

## 參數
`pick_tie=None`（預設：pick 照舊，依欄遞減、同分照候選列序、不動 rng）／`"rng"`：`perm = rng.permutation(len(cand))`（與抽籤版同一次抽、抽的次數逐日相同）⇒ `order = perm[argsort(−key[perm], stable)]`；NaN 照舊排最後；只能與 pick 同開。
互動：候選 ＝ 當天訊號 ＋ queue_days 隊列列（各帶自己的鍵）去掉已持有；d_max 只限名額；cap_fn、待買（trim／stop_proceeds）照排好的順序 ⇒ 與 pick 原路徑同一段（fixture F3、隨機世界含 d_max＋queue＋T1 待買）。營飆 v1 的 d 是 None。
順手修：pick 欄原本必須在 _LOG_COLS 裡（relvol 在），其他欄會在 sig 瘦身時被丟掉 ⇒ KeyError；現在自訂鍵欄一併帶進來（只影響原本會報錯的呼叫；對照：改前引擎用 K 欄確實 KeyError）。

## 閘
- (a) 引擎 pick=K0～K4, pick_tie="rng" ＝ pre 的診斷包裝 RankRng：200 顆 × 5 鍵 ＝ 1,000 組逐位元（全部回傳、audit；買進清單逐筆）
- (b) 常數鍵＋pick_tie ＝ 抽籤版（pick=None）200 顆逐位元，eq_sha ＝ regime_t1 t1 #1
- (c) pick_tie 不給 ⇒ #13（AND N20 d=inf relvol）rerun17 main／win 20 顆逐位元（cagr／mdd／vol repr、first／end／trades、eq_sha）
- (d) regress_tradability 18、regress_delist 6；改前（5331e1cd）／改後 A/B 43 種組合（含 pick relvol＋d_max＋queue＋log 明寫 pick_tie=None）× 2 ＝ 86 組逐位元；
  selftest_listexit all（48/3/13/3/3；內含 selftest_avgengine3 all ⇒ avgengine2、avgengine、P9 全套、P9 基準臂 +27.69%／−42.5%、avgdown）全過；
  31 個入庫檔（resultsp9_engine、resultsAvg/engine_b*_、resultsListExit/engine_*）逐位元組寫回、沒有多出檔
- fixture：F1 同分照同顆種子抽籤（30 顆、B／C 都出現；不給 pick_tie 永遠 B）、F2 NaN 排最後、F3 d_max＋queue、F4 自訂欄；隨機 300 世界 ＝ RankRng；隨機 200 世界 常數鍵 ＝ 抽籤；None 路徑 180/180；防呆 2；突變體 3 個全抓到（MT_noperm、MT_asc、MT_nodraw）

## body 段（未跑）的讀法，跑前請裁定確認
- 百分位 ＝ 中位秩（比 x 小的 ＋ 一半等於 x 的）÷ 200 × 100；對抽籤運氣的位置（seq199 ②）
- 排名版「比值」＝ 年化中位 ÷ |回落中位|（與標籤同式）；抽籤分佈用逐顆的 年化 ÷ |回落|
- 閘：0050 錨、鍵 ＝ pre_keys.csv 逐位元、抽籤版 200 顆 ＝ regime_t1 t1 #1
- 結果句前綴：「排名最多只影響約 x% 的買進」（退化檢查總差最大值）、K1「這個鍵多半靠抽籤決勝」、K0 落在 10～90 之外 ⇒「連隨便排都偏離抽籤…」
