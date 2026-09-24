# 670 vs 671：差的那一檔是 **8034 榮群**，而且是【定義差】不是【資料差】
> ⚠ **資料快照腳註（裁定線 20260924-2051 §一②＋20260924-2229 §二）**：本件的普通股母體來自分支 `data/` 快照 **2026-09-18**，`load_universe()` 當時沒有排除兩類：① 7 檔 `-DR` 被誤標成 `kind=='stock'`（main 自 2026-09-21 起已是 `dr`）；② **26 檔創新板（名稱含 -創）**從來沒被排除（裁定線 1611 §二 裁剔除）。實際進到 P4 面板 `eligible` 的：-DR 只有 9103／9105 共 50 股-月（0.0837%）；創新板只有 2258／6949 共 7 股-月（0.012%）（D4 elig_d4 另含 2258／6949 共 51 股-月，0.027%）。⇒ 出處與量測見 `backtest/DR_SNAPSHOT_FOOTNOTE.md`。⛔ 依裁定【不重跑】；新跑件一律用 `universe_gate.gate3()`。

回測線 2026-09-20 19:30（台北）。來源：策略線投遞的 671 檔代號清單
（`資料投遞-members_671_20230703_策略線_sha51c46aebc7a13e4c-20260920-1830`，fileId `1pXSv3Ge2js8TaXvfglDeHI-QbMi2S-f7`）。

## 結論

```
量測日 2023-07-03（面板月 2023-07）
  本線 liq_ok ∧ bars_ok          ＝ **671 檔**  ⇐ ⭐ 與策略線 `_liq` 的 671 **逐數字相同**
  本線 liq_ok ∧ bars_ok ∧ inst_ok ＝ **670 檔**（＝ panel 的 `eligible`）
  差集：策略線有而本線沒有 ＝ 【8034】；本線有而策略線沒有 ＝ 【無】
```

⇒ ⭐ **兩線的前兩條閘門（近 20 日均額 ≥ 5,000 萬、有效 K 棒 ≥ 120）沒有分岔。**
⇒ 差的是本線多的**第三條**：【(c) 法人欄可算】（K線分析線 2026-09-15 2035 裁定：法人欄 NaN ⇒ 不進母體、⛔ 不補）。

```
實作（backtest/forward_p4.py:68 逐字）：
  inst_ok = bool(pd.notna(row["fore20"]) and pd.notna(row["trust20"]))

8034 榮群（tpex；universe first_seen 2015-01-05／last_seen 2026-09-18）在 2023-07-03：
  liq_ok=True（amt20 ＝ 73,794,910）　bars_ok=True（bars ＝ 2,064）　inst_ok=**False**
  面板欄 inst_win_missing_traded ＝ **2**　⇒ 法人視窗裡有 2 天【有成交卻沒有法人列】
  ⇒ fore20／trust20 ＝ NaN ⇒ 被 (c) 擋掉 ⇒ eligible=False
```

## ⛔ 怎麼寫這件事

```
⭕ 【兩線的閘門差一條 (c)】；⭕【本線 671 → 670 是 (c) 擋掉 8034】
⛔ 不可寫「兩線母體差 1 檔、來源未查」（已經查出來了）
⛔ 不可寫「兩線母體相同」（它們不同，差一條閘門）—— 〈七十〉：計數定義要跟著數字走
⏳ 要不要對齊（策略線 cap5.py 加 (c)，或兩線各自保留但每次引用標明）⇒ ⛔ 不是回測線的格子
```

## 重現方式

```python
theirs = <投遞檔的 671 個代號>
p = backtest.p4_features.read_panel("backtest/resultsp4/panel.csv.gz")
m = p[p["measure_date"] == pd.Timestamp("2023-07-03")]
mine = set(m.loc[m["eligible"].astype(bool), "stock_id"].astype(str))
set(theirs) - mine   # {'8034'}
mine - set(theirs)   # set()
int((m["liq_ok"].astype(bool) & m["bars_ok"].astype(bool)).sum())   # 671
int(m["eligible"].astype(bool).sum())                               # 670
```
