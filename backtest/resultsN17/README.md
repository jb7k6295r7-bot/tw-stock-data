# resultsN17：候選 17 格主窗重跑（裁定線 seq143 §三②）

⛔ 只描述，不是判過／判不過；不改舊判定。標籤規則寫死如下（未捨入比較）：
條件一 年化中位 ＞ 0050 同窗年化；條件二 比值（年化中位 ÷ |回落中位|）≥ 0050 同窗比值
⇒ 兩條都成立＝合格；只成立條件一＝另列；條件一不成立＝不合格。合格而回落比 0050 深的，另註「深 x 點、多 y 點」。

## 檔案

| 檔 | 內容 |
|---|---|
| `rerun17.csv` | 17 列：原交件值（table219）→ 重現值（逐位元比對出處檔）→ 只換窗 → 只換資料 → 主窗值、比值、年化波動、年化÷波動、標籤、變動來源；0050 同窗四個數與錨閘 |
| `rerun17_seeds.csv` | 逐種子明細（stage × 格 × 200 顆；`cell=0` 是 P12 策略側本身，只作描述） |
| `seeds_<stage>.csv`、`meta_<stage>.json`、`run_<stage>.log` | 各階段的原始輸出、當次 0050 值、執行紀錄 |
| `sig_edc6f/` | edc6f 快照上重建的訊號：`panel_rev.csv.gz`（營收面板）、`signals_S.csv.gz`（3/5 主格）、`and_signals.csv.gz`（AND＋relvol）、`build.log` |

程式：`backtest/rerun17.py`（各階段）、`backtest/rerun17_build.py`（edc6f 訊號重建）、`backtest/rerun17_table.py`（彙總）。
全部呼叫原程式的函式：引擎 `research11.simulate_mtm`、窗內年化與回落 `research13.window_stats`、`research13.and_flags`、
`research34.process_stock`、`research11.stock_features`、`researchp1.attach_features`、`researchp7.build_sig_gate_b`、
`researchp14.blend`、`researchp17.{rebal_days, sigma_at, w_paths, compose}`。⛔ 既有 .py 一行都沒改。

## 各族怎麼跑（訊號、參數、種子照原件）

| 族 | 格的定義 | 種子 | 原件的年化／回落怎麼讀 |
|---|---|---|---|
| PREREG10（研究十三） | AND 訊號（3/5 ∧ 營收創 24 月新高）；regime＝進場日 0050 還原收盤 > 200MA；N 槽、rule H60／H120／LD；cash 0 | 1000+r | 引擎自己的 cagr／mdd（首筆進場～末筆出場＋2），200 顆中位 |
| P1 | 同一份 AND；rule 固定 H60；pick＝relvol 或隨機；d_max＝d、隊列 Q＝5（d 有限時）；log 照原樣傳 | 7000+r | 同上 |
| P3 乙臂 | 同 P1，cash_mode="bench"（閒置資金放 0050，單邊 COST/2） | 7000+r | `window_stats(eq, first, end, AND 首筆進場, 日曆尾)` |
| P14 w=0.50 | P12 (S1,C1,T1)：門檻B 訊號、N8、H120、cash 0、成本 0.585%；窗內 E 與 0050 B 各半，期初配置、不再平衡 | 102000+r | `window_stats(blend, 0, n, 0, n)` |
| P17 R_eq | 同一條 E；每月第一個交易日依 σ_B/(σ_E+σ_B) 再平衡（120 日回看、burn-in 0.50、換手 0.585%） | 102000+r | 同上 |

## 四個階段

| 階段 | 資料 | 訊號 | 窗 |
|---|---|---|---|
| repro（重現閘） | 各族當年的資料（見下） | 原件存檔 | 原窗 |
| winonly（只換窗） | 同 repro | 原件存檔 | 主窗、以現金起算 |
| dataonly（只換資料） | edc6f 快照 | edc6f 重建 | 原窗 |
| main（主窗值） | edc6f 快照 | edc6f 重建 | 主窗、以現金起算 |

**重現用的資料**：原件跑的那天的分支 `data/` 已被後來的更新蓋掉（09-14 的 cum_factor 改版、09-18 快照），
所以用 `git archive <commit> data/stocks data/adj data/meta` 取回當時的版本，放在 repo 外的 `~/r17data/<commit>/`（唯讀）：

- PREREG10 ⇒ `2b1ee1c16f`（研究十三結果的 commit，2026-09-12）
- P1、P3 ⇒ `487a756ecb`（P1 回歸的 commit，2026-09-14；與 P3 的 `5bf068f57b` 的 data 逐檔相同）
- P14、P17 ⇒ 分支目前的 `data/`（2026-09-18 快照，P17 報告腳註寫的那一份）；面板 `resultsp4/panel.csv.gz`

⚠ 用分支目前的 `data/` 跑 PREREG10、P1、P3 會重現不了（例：格 3 年化 0.404274 vs 0.404478），原因是資料被改版，⛔ 不是程式不一樣。

**主窗讀法**（看結果之前就寫定）：
- 訊號只留 entry_pos ∈ [2017-03-02, 2026-08-24]，所以組合在窗首之前全是現金。
- 年化、回落 ＝ `window_stats(eq, min(first, w0), max(end, w1+1), w0, w1+1)`，以 eq[w0] 為起點、2313 日 ÷ 245 年化。這與 0050 錨（P17 W0 ＝ B/B[0]）同一口徑；先取 min(first, w0) 是照 `researchp12.win_read` 的做法，避免 window_stats 把起點 clamp 到 first。
- w1 仍持有的部位以 w1 收盤市值計。
- 年化波動 ＝ 窗內日報酬（2312 個）的標準差（ddof=1）× √245。√245 是 repo 慣例（`p4_features.vol60`、`researchp13` te、`researchAFC`），245 也與引擎年化用的天數一致。
- 比值 ＝ 年化中位 ÷ |回落中位|（不是逐種子比值的中位）。
- P14、P17 的原件本來就是這個窗，而且門檻B 訊號的第一筆進場就在 w0（e_min=523），所以只有「換資料」一步。

**edc6f 上的重建**（`rerun17_build.py`）：
- 資料 ＝ `~/h2data/edc6f8002f…/data`。
- 母體 ＝ `load_universe()` ∩ `gate3()`，比原件少 27 檔創新板（-DR 在這份快照的 stocks.csv 已經不是 kind=stock）。
- 營收面板、S、AND、relvol 各自用原件的產生器與原常數（SIG_START／SIG_END、liq_mode=shares、pub_day 10、STALE_MAX 45）。
- P14、P17 用 `resultsAFC/panel.csv.gz`（同一份快照、gate3 的 P4 面板）。價格一律從快照 `D.load_stock` 讀。⛔ tradable／delist 不開，與原件一樣。

## 兩道閘

**閘一 重現**：17 格全部與出處檔（`results13/portfolio.csv`、`resultsp1/portfolio.csv`、`resultsp3/summary.csv`、`resultsp14/w_summary.csv`、P17 交件值）的年化中位、回落中位**逐位元相同**。
另外逐種子比對了四格：P17 R_eq、P14 w=0.50 各 200/200 對上 `resultsp17/per_seed_arm.csv`、`resultsp14/blend_by_seed.csv`；P3 乙 d=1、d=2 各 200/200 對上 `resultsp3/seeds.csv`。
⚠ `resultsN219/table219.csv` 只存 16 位有效數字，對它比會差 1 ulp（5.55e−17），所以逐位元一律對出處檔。

**閘二 0050 錨**：主窗 0050 買進持有 年化 0.24020209886370614、回落 −0.3395700527611012，在 edc6f 快照、分支 09-18 快照、`2b1ee1c16f`、`487a756ecb` 四份資料上**全部逐位元相同**。
0050 同窗四個數：年化 +24.0202%、回落 −33.9570%、比值 0.70737、年化波動 20.3079%、年化÷波動 1.1828。

## 要知道的幾件事

1. **AND 訊號在 edc6f 上變多**：2,199 → 2,339 筆（原件 2,199 筆全在新集合裡，另外多 140 筆）。兩邊共有的訊號裡，g_H60 相同的只有 84.7%（還原因子改版），relvol 100% 相同。這是 P1、P3 那幾格「換資料」一步掉很多的來源。
2. **P12 門檻B 訊號**：edc6f＋gate3 上是 2,881 筆／918 檔，原件驗收數是 2,882／919，面板少了 gate3 剔掉的 27 檔（-DR 與 -創），資料也換了版本；少的那 1 筆是從哪一步來的，⛔ 沒有逐筆拆。⛔ 這一步照 researchAFC 的做法，不斷言原件的驗收數。
3. **主窗首筆進場**：PREREG10、P1、P3 在主窗的第一筆進場都是 2017-03-07（w0＋3）。P3 乙臂在引擎裡的 0050 持有從首筆進場前一日才開始，所以 03-03、03-06 這兩個交易日的閒置資金沒有放 0050，報酬記 0。原件在自己的窗裡也是同樣的做法。
4. PREREG10 原件的判準窗從 2016 年起（0050 錨 0.248），P1、P3 從 2017-02-13 起（0.241）；這次的主窗都統一到 2017-03-02～2026-08-24。
5. 沒有讀、也沒有算 2015 年以前的任何報酬：日曆本身從 2015-01-05 開始。MA200、relvol 等暖身用到的 2015～2016 年價格，是原程式本來就在用的。
