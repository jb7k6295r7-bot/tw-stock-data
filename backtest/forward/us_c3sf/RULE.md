# USREG-C3sF seq1（動能＋大盤濾網）——前瞻紙上紀錄

建立：2026-10-17 00:10（台北），回測線。依據：裁定 seq353 §三.5（發號；只記前瞻；與 C3s forward 同起點；N_組合 ＋1 於判定時計）。
登錄：「登錄全文-USREG-C3sF_動能加大盤濾網_seq1_美股策略線_shad16267eb388f0711-2099B-20261016-2332.md」（整檔 sha 已驗）。
程式：`backtest/forward_us_c3sf.py`（補讀法 F1～F7 寫在 docstring）。⛔ 使用者不跟單本格、本格不影響換股單。

⛔ 本檔之後不改。

## 規則（登錄 §一；其餘逐字同 C3s）

- 選股、續抱、8 槽等權、成本 0.05%、換股日：與 C3s forward 簿同一來源（`researchUSC3s_ops.tables()`、`K.book` 同式）。
- 起點：2026-10-30 收盤量測、2026-11-02 開盤執行（＝ C3s forward 起點）。
- 濾網：每個月底收盤，SPY 還原收盤 ＜ SPY 最近 200 個交易日還原收盤平均（含當日）⇒ 下一換股日**不新買**；已持有照 C3s 原規則出場。SPY ≥ 200 日線 ⇒ 照 C3s 補滿空槽。只在月底看一次。
- 空槽資金：⭐ 擇**國庫券 DTB3**（被擋那個月現金每日 × (1 ＋ DTB3_{t−1}÷100÷252)）；未被擋的月份現金照 C3s（0 報酬）⇒ 濾網沒觸發時 C3sF ＝ C3s forward。
- 濾網決定寫進 `filter.csv` 後凍結，⛔ 不因 SPY 日後股利回補重判。

## 紀錄（只追加）

| 檔 | 內容 |
|---|---|
| `filter.csv` | 每個月底：SPY 還原收盤、200 日線、擋／不擋、作用換股日、資料 commit |
| `monthly.csv` | 每期：量測月底、濾網、換股日、月底、換股後持股 1～8（代號）、本月新進、本月賣出、持股數、現金占比、C3sF／^SP500TR 月報酬、C3sF／C3s 本體／^SP500TR 累積（起點 ＝ 1）|
| `state.json`、`runlog.md` | 記到哪裡、每次執行一行（重算與已寫列不同 ⇒ 保留已寫、記在這裡）|
| `selftest.json` | 閘：濾網全不擋 ⇒ ＝ K.book（差 0）；全擋 ⇒ 權益 ＝ 國庫券複利（差 0）；SMA200 另寫抽 5 個月底相同 |
| `describe_seen.json` | 看過段一行描述（⛔ 不判、偏向存活股） |

逐日權益只寫 `~/us_work/forward_us/c3sf_daily.csv`（repo 外）。

## 執行

```
cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_us_c3sf --month 2026-10-30   # 10/30 當晚：記第 0 列濾網決定
... -m backtest.forward_us_c3sf                 # 之後每月：補到最後一個已結束月底（或月底當晚加 --month）
```

前提同 C3s forward：world.npz（個股）要先更新到該月底；SPY、DTB3 讀 `~/us-stock-data`（⛔ 只讀）。

## 判定（登錄 §二、§三；⛔ 中途只報不判）

滿 36 期（2029-10 月底）與 C3s forward 同時判，對 ^SP500TR；另報對 C3s 本體的回落與年化差、被擋月份數、被擋期間 C3s 本體報酬（擋對／擋錯）、平均股票曝險與同曝險 C3s＋國庫券對照。
