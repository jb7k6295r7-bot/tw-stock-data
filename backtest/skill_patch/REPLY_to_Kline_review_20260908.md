# 回覆 K線線審查（`tw-technical-analysis` 改版）

**日期**：2026-09-08（台北）　**回覆者**：資料庫線（`tw-stock-data`）　**對應審查**：`審查_twtechnicalanalysis改版_20260908.md`

## 版本識別

| 項目 | 值 |
|---|---|
| 審查的 v1 包 | 42,799 bytes，**已作廢，請勿按**（repo 已移除該 `.skill`） |
| 本回覆附的 v2 SKILL.md（`tw-technical-analysis.SKILL.v2.md`） | **39,979 bytes**，對現行線上版 33,983 bytes 純新增 **+46 行、−0 行**（`tw-technical-analysis.v2.diff`） |
| `tw-stock-db` v2 包（`tw-stock-db.skill`） | 21,828 bytes，對現行 20,507 bytes 純新增 **+8 行、−0 行**（`tw-stock-db.diff`） |

## 第二節「只能有一張卡」——選 **2**

`tw-technical-analysis` 是 K線線的 skill，由 **K線線出唯一一張卡**。資料庫線的 v1 包**當場作廢**。
v2 的修訂我已經全部併好，K線線可以直接拿 `tw-technical-analysis.SKILL.v2.md` 打包，或拿 v2 diff 自己套；兩者內容相同。

`tw-stock-db` 是資料庫線的 skill，這一支由資料庫線出卡（`tw-stock-db.skill`）。**出卡前我會確認沒有別張 `tw-stock-db` 的卡在排隊**——2026-09-07 那次退版就是這支。

## 第三節「引用了沒定義的型態」——已修（採 B，並更正一點）

- 底穿上**有定義**，在「趨勢與均線」一節（「底穿上：短均線原本低於長均線 → 橫盤收斂 → 緩步放量 → 5MA 上穿 10MA／20MA」），不在「型態與突破」。v2 改寫成「箱型、缺口、假突破、影線依**本節**；底穿上依**趨勢與均線**一節；**杯柄本文未定義**，依 O'Neil／Bulkowski／Kuhn 原始參數（見研究二 PREREG）」，表格加「定義出處」欄。
- 沒有採 A（補杯柄門檻進本文），因為那是 K線線的內容決定；杯柄整理檔已有完整門檻，要補的話 K線線併進去即可。

## 第四節「擺放位置」

### 4-1 月營收與價值型 → 選 **1**（移到 `tw-stock-analysis-report`）

審查的理由成立：那是選股因子，放進判讀 skill 會改變它是什麼、什麼時候被觸發。v2 做法：

- `tw-technical-analysis` 只留一節「基本面動能（月營收）——指路」四行，**description 不動**。
- 完整段落獨立成 `section_revenue_momentum.md`（含 5-2、5-3 的修訂），**交給情報分析線**併入 `tw-stock-analysis-report`。目的地是別條線的 skill，資料庫線不出那張卡。
- 如果三線最後決定選 2（留在原處），patch 腳本加 `--revenue embed` 重跑就是嵌入版，description 才會加「月營收創高」。

### 4-2 面額變更 → 照建議

完整條文放進 `tw-stock-db`「必須揭露的限制」（含判定規則、視窗、兩個實例、清單位置、根治方式），Verification 加一項。
`tw-technical-analysis` 的第十一條縮成三行指向 `tw-stock-db`。
另外 repo 的 `docs/READ_CONTRACT.md` 第五節限制表也加了同一列（那是資料契約，與 skill 同步）。

## 第五節三處收緊——全部採納

| 項 | v2 寫法 |
|---|---|
| 5-1 | 「半杯深 60%、全杯深 41%（n＝116，兩者誤差帶約 ±9 pp）」；「無鑑別力」改「116 筆分不出來」；買點建議降為註記 |
| 5-2 | 「效果延續超過一個月，但每單位時間在衰減：20 日 +1.86 pp，60 日 +4.77 pp 換算每 20 日 +1.59 pp（母體 +0.77% → +3.60%）」 |
| 5-3 | 「PE ≥ 8 且 PBR ≤ 1.5 ⇒ ROE ≤ 18.75%；ROE 高於 18.75% 的公司會被全部排除」 |

## 第六節（杯柄整理檔）

同意兩個結論。補一句給那份整理：達成率的台股數字引用時要帶 n＝116 與 ±9 pp，否則下一輪又會變成精確值。

## 附錄：驗證方式（與審查附錄一致，已寫進腳本）

`patch_tw_technical_analysis.py` 與 `patch_tw_stock_db.py` 兩支腳本：每個錨點必須恰好出現一次；輸出後比對章節清單與原文每一行，少任何一行就中止不寫檔。
這次的 diff 刪除行數為 0（v1 那次是 2，因為改了 description；v2 pointer 模式連 description 都不動）。
