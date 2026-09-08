# backtest/ — 研究二：型態全市場回測

| 檔 | 內容 |
|---|---|
| `PREREG.md` | **事前登錄**：母體、閘門、六種型態的機器定義、出場、基準、通過門檻。跑資料前 commit；之後只追加「更正」。 |
| `data.py` | 讀資料庫：還原價、日曆對齊（洞留 NaN）、處置區間、first_seen/last_seen 母體。 |
| `patterns.py` | 六種偵測器：P1 箱型突破、P2 突破缺口、P3 假突破、P4 錘子／射擊之星、P5 底穿上、P6 杯柄（日線柄高／杯蓋、週線）。 |
| `evaluate.py` | 出場（固定 20 日、2×ATR 追蹤、固定停損）、成本、目標價達成、統計（非重疊筆數、CI）。 |
| `report.py` | 產出 `results/summary.md`。 |
| `run.py` | 執行器。 |
| `selftest_patterns.py` | 合成資料自我測試：每種型態一段教科書序列，確認在預期那天發訊號、不該發時不發。 |
| `results/` | `signals.csv`（逐筆，含所有出場模式的報酬）、`variants.csv`（敏感度）、`baseline.json`、`summary.md`。 |

```
python3 -m backtest.selftest_patterns          # 先跑這個
python3 -m backtest.run                        # 全市場，約 10 分鐘（4 核）
python3 -m backtest.run --stocks 2330 2454 --print --out /tmp/x   # 幾檔，印訊號核對
```

需要 `pandas`、`numpy`。

**改門檻的規矩**：`patterns.PARAMS` 裡的值要與 `PREREG.md` 一致；要改就先在 PREREG 追加「更正 N」寫明理由與時點（是在看結果之前還是之後），再改程式。
