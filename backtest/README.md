# backtest/ — 研究二：型態全市場回測

| 檔 | 內容 |
|---|---|
| `PREREG.md` | **事前登錄**：母體、閘門、六種型態的機器定義、出場、基準、通過門檻。跑資料前 commit；之後只追加「更正」。 |
| `data.py` | 讀資料庫：還原價、日曆對齊（洞留 NaN）、處置區間、first_seen/last_seen 母體、**斷點**（`breakpoints`：比值 ≤ 0.55／≥ 1.8 或連續缺 ≥ 5 個交易日、且區間內無 `data/adj/` 事件；`breakpoint_window`：訊號日 ∈ [T−H, T+L−1] 剔除，H、L 由各研究從參數算）。 |
| `breakpoint_scan.py` | 全母體掃斷點並與資料庫線的 `data/meta/par_change.csv` 對帳（改斷點規則後先跑這個）。 |
| `research34.py` | 研究三（月營收動能）、研究四（價值型）月度面板；判準在 `PREREG3.md`，結果在 `results3/`。 |
| `research5.py` | 研究五（出場規則比較：固定百分比停損／百分比追蹤／ATR 追蹤 vs 固定持有）；判準在 `PREREG4.md`，結果在 `results5/`。進場集合取自 `results/`、`results3/`，要先跑前兩個。 |
| `patterns.py` | 六種偵測器：P1 箱型突破、P2 突破缺口、P3 假突破、P4 錘子／射擊之星、P5 底穿上、P6 杯柄（日線柄高／杯蓋、週線）。 |
| `evaluate.py` | 出場（固定 20 日、2×ATR 追蹤、固定停損）、成本、目標價達成、統計（非重疊筆數、CI）。 |
| `report.py` | 產出 `results/summary.md`。 |
| `run.py` | 執行器。 |
| `selftest_patterns.py` | 合成資料自我測試：每種型態一段教科書序列，確認在預期那天發訊號、不該發時不發。 |
| `results/` | `signals.csv`（逐筆，含所有出場模式的報酬）、`variants.csv`（敏感度）、`baseline.json`、`summary.md`、`breakpoints.csv`（本次剔除用的斷點清單）、`CONCLUSIONS.md`。 |
| `PROGRESS.md` | 回測線的進度、版本識別與跨線信箱讀取水位。 |
| `skill_patch/` | **已封存**：2026-09-08 的 skill 更新包與 diff。分工重訂後 skill 一律由各線自己改，本線只寄信；裡面的數字（26 筆／24 檔、前 121／後 20）已被更正三取代，別再引用。 |

```
python3 -m backtest.selftest_patterns          # 先跑這個
python3 -m backtest.breakpoint_scan            # 斷點對帳（par_change.csv 24 筆要全部說得清楚）
python3 -m backtest.run                        # 全市場，約 10 分鐘（4 核）
python3 -m backtest.research34                 # 研究三／四，結果在 results3/
python3 -m backtest.run --stocks 2330 2454 --print --out /tmp/x   # 幾檔，印訊號核對
```

需要 `pandas`、`numpy`。

**改門檻的規矩**：`patterns.PARAMS` 裡的值要與 `PREREG.md` 一致；要改就先在 PREREG 追加「更正 N」寫明理由與時點（是在看結果之前還是之後），再改程式。
