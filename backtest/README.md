# backtest/ — 研究二：型態全市場回測

| 檔 | 內容 |
|---|---|
| `PREREG.md` | **事前登錄**：母體、閘門、六種型態的機器定義、出場、基準、通過門檻。跑資料前 commit；之後只追加「更正」。 |
| `data.py` | 讀資料庫：還原價、日曆對齊（洞留 NaN）、處置區間、first_seen/last_seen 母體、**斷點**（`breakpoints`：比值 ≤ 0.55／≥ 1.8 或連續缺 ≥ 5 個交易日、且區間內無 `data/adj/` 事件；`breakpoint_window`：訊號日 ∈ [T−H, T+L−1] 剔除，H、L 由各研究從參數算）。 |
| `breakpoint_scan.py` | 全母體掃斷點並與資料庫線的 `data/meta/par_change.csv` 對帳（改斷點規則後先跑這個）。 |
| `research34.py` | 研究三（月營收動能）、研究四（價值型）月度面板；判準在 `PREREG3.md`，結果在 `results3/`。 |
| `patterns.py` | 六種偵測器：P1 箱型突破、P2 突破缺口、P3 假突破、P4 錘子／射擊之星、P5 底穿上、P6 杯柄（日線柄高／杯蓋、週線）。 |
| `evaluate.py` | 出場（固定 20 日、2×ATR 追蹤、固定停損）、成本、目標價達成、統計（非重疊筆數、CI）。 |
| `report.py` | 產出 `results/summary.md`。 |
| `run.py` | 執行器。 |
| `selftest_patterns.py` | 合成資料自我測試：每種型態一段教科書序列，確認在預期那天發訊號、不該發時不發。 |
| `results/` | `signals.csv`（逐筆，含所有出場模式的報酬）、`variants.csv`（敏感度）、`baseline.json`、`summary.md`、`breakpoints.csv`（本次剔除用的斷點清單）、`CONCLUSIONS.md`。 |
| `PROGRESS.md` | 回測線的進度、版本識別與跨線信箱讀取水位。 |
| ~~`skill_patch/`~~ | ⛔ **併入 main 時刻意排除，不在這裡。** 見下方「出處」。 |

```
python3 -m backtest.selftest_patterns          # 先跑這個
python3 -m backtest.breakpoint_scan            # 斷點對帳（par_change.csv 24 筆要全部說得清楚）
python3 -m backtest.run                        # 全市場，約 10 分鐘（4 核）
python3 -m backtest.research34                 # 研究三／四，結果在 results3/
python3 -m backtest.run --stocks 2330 2454 --print --out /tmp/x   # 幾檔，印訊號核對
```

需要 `pandas`、`numpy`。

**改門檻的規矩**：`patterns.PARAMS` 裡的值要與 `PREREG.md` 一致；要改就先在 PREREG 追加「更正 N」寫明理由與時點（是在看結果之前還是之後），再改程式。

---

## 出處：這個目錄是怎麼進 main 的（2026-09-09）

原本只在分支 `claude/stock-analysis-backtest-iv9xji`，**從未併入 main**。
於是兩支 skill 引用的 `backtest/results3/CONCLUSIONS.md` 在 main 上是 404——
結論有出處，但出處在一條隨時可能被刪的分支上。

使用者 2026-09-09 裁示併入，**但排除 `skill_patch/`**（12 個檔、137 KB）。

**為什麼排除**：那是回測線掛「資料庫線」名義寄出的 skill 更新包 v1~v3，
回測線自己已宣告**全部作廢**（數字是 26 筆／24 檔、前 121／後 20，都已被更正取代）。
併進 main 等於在 repo 裡放三份過期的 skill 副本——
**那正是這個專案一路在防的「第二份權威，它會跟原版飄移」。**
skill 的權威在各線自己手上，不在這裡。

**為什麼連 `.gz` 一起帶**：`CONCLUSIONS.md` 的內文引用 `panel.csv.gz` 與 `summary.md`。
只併結論、不併資料，等於把斷掉的引用往下移一層——與原本的毛病同一種。
三個 `.gz` 合計約 14.5 MB，對 `data/` 已有的 2.3 GB 是 0.6%，不是成本問題。

**為什麼 `PREREG*.md` 一定要在**：本專案的紀律是「判準事前寫死、跑完只追加不修改」。
事前判準留在分支、結論進 main，等於**把「說好的門檻」與「宣稱的結果」分開存放**，
日後無法證明結論沒有事後調參。兩者必須同進退。

⚠ **`selftest_patterns.py` 刻意不排進 `daily.yml`。**
它是好的（6/6 通過，2026-09-09 於 main 實測），但 `daily.yml` 是**資料管線**：
回測邏輯壞掉不應該讓當天的資料收集變紅。要跑就手動：

```
python3 -m backtest.selftest_patterns
```

⚠ 併入的是**當時分支上的快照**。分支仍在，後續回測工作在那邊繼續；
main 這一份不會自動跟上。**要更新請再併一次，不要在 main 上就地改。**
