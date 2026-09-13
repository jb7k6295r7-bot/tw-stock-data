#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""neighbor_floor.py — 「這一批**抓完了沒**」的通則：跟**鄰近同類**比數量。
**只讀 repo，不連外。⭐ 這個判準只有這一份實作（CLAUDE.md 四點五）。**

## ⭐⭐ 為什麼要有這一支：兩個看起來無關的事故是**同一個形狀**

市場情報分析線 2026-09-13 14:00 指出來的，而他們是對的：

```
① `--fill` 只問 `os.path.exists`      ⇒ 殘缺檔「在」就跳過 ⇒ **永遠補不到**
   （2026-08_twse 123 列 vs 鄰月 992）
② TPEx 憑證鏈壞掉、整批抓不到          ⇒ 那天的日檔**是空的**
```

⚠ 病因完全不同（一個是我方判準錯、一個是對方 TLS 設定壞），
⭐ **而它們在資料裡長得一模一樣**：「今天 93 列、昨天 859 列」。

⇒ ⭐ **所以閘門不需要知道失敗的原因。** 憑證鏈、403、端點改版、
參數被無視、對方那天只回一半——⛔ 全部都會呈現成這個形狀。

⛔⛔ 而**不可以拿區間端點去核**：`otcper 2015-01-05 ~ 2026-09-11` 看起來連續，
⚠ 而中間某一天列數塌掉在那個檢查裡**完全看不到**。⇒ **要逐日看列數。**

## 判準

```
n < median(最近 k 個鄰居，不含自己) × floor   ⇒ 判成殘缺
```

⭐ 基準是**鄰近**，⛔ 不是全庫中位數：上櫃家數十一年從 669 長到 860，
拿全庫中位數當基準會讓舊期別的門檻太高、新期別的太低。
⚠ 實測：`2022-02_tpex` 411 列（鄰月 797）用全庫中位數算是 52%，**剛好躲過 50%**。

## ⛔ 兩種錯的代價不對稱 ⇒ 往哪邊放是想過的

```
判太嚴 ⇒ 多抓一次（幾秒）
判太鬆 ⇒ ⛔ 那個洞**永遠補不到**，而且看起來像做完了
```

⚠ 但「判太嚴」有一個更貴的版本：**天天紅 ⇒ 被學會忽略**。
⇒ 所以 `min_median`（絕對量太小的不判）跟呼叫端的週六排除都是必要的，
⛔ 它們不是在放水，是在讓這道閘門**還有人看**。
"""
import statistics

VERSION = "v1"
FLOOR = 0.5          # 日檔用。⚠ 校準見 selftest_neighbor_floor.py 的實測那一節
FLOOR_PERIOD = 0.9   # 期別檔（月營收）用：一個月的家數幾乎不動 ⇒ 門檻可以更緊
K = 6                # 取幾個鄰居
MIN_MEDIAN = 30      # ⛔ 中位數低於這個就不判（小數字的比值毫無意義）
MIN_PEERS = 3        # ⛔ 鄰居太少就不判（⛔ 不要用猜的門檻擋）


def is_short(n, peers, floor=FLOOR, min_median=MIN_MEDIAN, min_peers=MIN_PEERS):
    """→ (判成殘缺嗎, 中位數 or None, 為什麼不判 or "")。⭐ 只有這一份實作。

    ⛔ 回三個值而不是一個 bool，是因為「**不判**」跟「判成沒事」必須分得開
    ——⚠ 兩者在呼叫端都是 `not short`，而在報表上意義完全相反
    （CLAUDE.md 第七點：回報「某群 0 筆」要附上該判準在該群抓到的正例數）。
    """
    vals = [v for v in peers if v is not None and v >= 0]
    if len(vals) < min_peers:
        return False, None, f"鄰居只有 {len(vals)} 個（要 {min_peers} 個）"
    med = statistics.median(vals)
    if med < min_median:
        return False, med, f"鄰近中位數 {med:g} < {min_median}（量太小，比值沒意義）"
    return (n < med * floor), med, ""


def neighbors(seq, i, k=K):
    """→ `seq` 中第 `i` 個位置的前後共 k 個鄰居（**不含自己**）。

    ⚠ 取的是**序列上的鄰居**，⛔ 不是日曆上的：中間漏抓的日子本來就不在序列裡，
    而「拿更遠的一天當鄰居」比「鄰居不夠就不判」好——⛔ 不判等於沒有閘門。
    """
    half = max(1, k // 2)
    lo, hi = max(0, i - half), min(len(seq), i + half + 1)
    return [v for j, v in enumerate(seq[lo:hi], start=lo) if j != i]
