#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""official_stats.py — 把兩份**官方統計**抓回來存檔，當價格層的外部判準。

## 這兩支能驗什麼（⛔ 它們是判準，不是資料）

| 端點 | 內容 | 驗得到什麼 |
|---|---|---|
| `afterTrading/FMNPTK` | 逐檔**逐年**：成交股數／金額／筆數、最高最低、**收盤平均價** | ⭐ **一列驗一整年**：每天的收盤價都對、**沒缺日、沒多出非交易日** |
| `afterTrading/FMSRFK` | 逐檔**逐月**：最高最低、加權平均價、成交筆數／金額／股數、週轉率 | `amount`／`volume` 的月合計 |

⭐ **「收盤平均價」是日收盤價的簡單平均**，不是成交金額÷股數
（實證：2330 的 114 年 成交金額÷股數 ＝ 1,144.0，而收盤平均價 ＝ **1,163.06**，兩者不同）。
⇒ 所以它能一次驗掉四件事：收盤價、缺日、多日、用的是未還原價。

## 端點與參數（⛔ 全部是 Actions 上實測，不是猜的）

    https://www.twse.com.tw/rwd/zh/afterTrading/FMNPTK?date=YYYYMMDD&stockNo=NNNN&response=json
    https://www.twse.com.tw/rwd/zh/afterTrading/FMSRFK?date=YYYYMMDD&stockNo=NNNN&response=json

⚠ 區段名是 **`afterTrading/`**——我一開始不知道，逐個試四個區段才確定
（TWSE 的區段名沒有規律：`TWTAUU` 在 `reducation/`，前一輪就是猜錯區段才掃不到）。

⚠⚠ **`FMNPTK` 的回應沒有 `title`**（實測 `title=None`）
⇒ ⛔ **不能用 title 回音去驗參數有沒有生效**（那是 `TWT49U`／`TWTAWU` 的驗法）。
  改用它自己的 `年度` 欄——那是自我識別的，比 title 更硬。
  `FMSRFK` 有 title（`'114年2330 台積電  月成交資訊'`），兩支的驗法因此不同。

## ⛔⛔ 接上櫃那一條之前必讀：**兩邊的數字都對，而它們不是同一個量**

2026-09-16 probe 120 找到上櫃的對應端點（`db_status` 那條缺口從「沒有來源」
變成「還沒接上」）：

    GET/POST https://www.tpex.org.tw/www/zh-tw/statistics/yearlyStock?code=<代號>
    ⇒ 一發回 **12 年**（民國 104~115，`totalCount:12`）

⭐ 欄位跟 `FMNPTK` **看起來**同一組——⛔ 而**單位不同**，而且它自己講了：

```
回應裡有一個鍵 `flagField: "張數"`     ← ⭐ 它自己標的
TPEx  成交張數(A) 1,323,393    金額(仟元)(B) 1,066,891,796   （6488 環球晶 115 年）
      ⇒ B/A = 806.18 ＝ 加權平均價（仟元/張 ＝ 元/股）⇒ 兩欄都要 ×1,000
TWSE  volume 12,740,507,347    amount 916,448,075,621        （2330 100 年）
      ⇒ amount/volume = 71.93 元/股 ⇒ 兩欄的單位是**股**與**元**
```

⇒ ⛔ **直接寫進同一張 `official_yearly_close.csv` 會做出一張兩種單位的表**，
⚠ 而接縫不會報錯（主鍵是 `stock_id`＋`roc_year`，兩段代號根本不重疊）
——那正是 CLAUDE.md 第二點那條 `FMTQIK` 口徑接縫的同一個形狀。
⇒ ⭐ 接的時候要**換算成股與元**，並且在 runlog 寫出「這一段是換算過的」。

### ⭐⭐ 而「哪一欄可以信」已經**量過了**（⛔ 不是推的）

拿 6488 環球晶跟**我方日檔**（完全不同條路：逐日個股行情）對一次：

```
                    我方日檔          官方 yearlyStock      ⇒
114 年 收盤平均價    366.43            366.43               ⭐ **逐位相同**
115 年 收盤平均價    749.62            749.62               ⭐ **逐位相同**
114 年 成交股數      760,214,000       788,658,000 (×1000)  官方多 3.7%
114 年 成交金額      301,368,863,000   312,330,604,000      官方多 3.6%
115 年 成交股數    1,263,212,000     1,323,393,000 (×1000)  官方多 4.8%
115 年 成交金額  1,016,311,783,500 1,066,891,796,000        官方多 5.0%
```

⇒ ⭐ **收盤平均價那一欄可以直接用**（它就是日收盤的簡單平均，跟 `FMNPTK` 同一個定義），
⛔ 而**總量那三欄是另一種口徑**（零股／盤後定價／鉅額之類，⚠ 我沒有量出是哪幾種
⇒ **那就寫不知道**）。

#### ⛔⛔ 而「另一種口徑」**每一欄的幅度不一樣** ⇒ 不可以套同一個換算

```
             我方日檔          官方（×1,000 之後）    差
成交股數     1,263,212,000     1,323,393,000         ＋4.8%
成交金額   1,016,311,783,500  1,066,891,796,000      ＋5.0%
⛔ 成交筆數      919,431           2,354,000         ＋156%（**2.56 倍**）
```

⚠ 而我方 tpex 的 `transactions` 欄**不是缺值**（2026-09-15 那天 1,013 列 100% 有值，
6488 當天 6,274 筆）⇒ ⛔ 不是我方漏抓。
⭐ 候選（**未驗**）：官方可能買賣各算一筆（2×）、或含盤中零股。⛔ 我答不出來 ⇒ 寫不知道。

⇒ ⭐⭐ **落地判準：只有 `收盤平均價` 那一欄可以進共用的判準表。**
⛔ 其餘各欄原樣另存（張／仟元／仟筆都保留官方單位），
⚠ 一旦把它們換算後併進同一張表，就會做出一張**接縫不會報錯**的表
（主鍵是代號＋年度，兩段代號根本不重疊 ⇒ 第二點那條 FMTQIK 接縫）。

⚠⚠ 這**正是** CLAUDE.md 第二點 2026-09-14 那條（`FMTQIK`）的同一個形狀：
**同一張表裡，有的欄可以信、有的不行**，而差異只落在總量那幾欄。
⇒ ⛔ 「這個端點可不可信」問錯了問題，要問的是「這個【欄】可不可信」。

⚠ 順帶量到的：`yearlyStock` 我送了 `date=2024/01/01`，⛔ 而它**照樣回全部 12 年**
（`subtitle` 寫「統計至 1150915 止」）⇒ **`date` 不是篩選器**。
⭐ 那對我方是好事（一發拿全部），⛔ 但不可以拿它當「我指定的那一年」用。

### ✅ 而**月**那一半 probe 123 也答了：`code` ＋ `date=<西元年>`（**只有年**）

⭐ 七種格式只有一種中（其餘六種一律 `stat:"參數輸入錯誤"`）：

```
date='2024'        stat=ok｜回顯 code='6488'｜totalCount=12｜inner date=2024   ⭐ 中
date='113'／'2024/01/01'／'20240101'／'113/01/01'／'2024/01'／'11301'  ⛔ 參數輸入錯誤
```

⚠ 而**我送西元、它回民國**（`年` 欄第一列是 `113`）。

#### ⛔⛔ 而兩張表的欄**定義不同**，⚠ 名字就寫著，而我差點沒看見

```
yearly  ：成交張數(A)      盤中最高價／盤中最低價
monthly ：成交仟股(B)      **收市**最高價／**收市**最低價
```

⇒ 拿 6488 的 113/1（2024-01，22 個交易日）對我方日檔：

```
收市平均價   587.27   ＝ 我方**收盤價**的簡單平均      ⭐ 逐位相同
收市最高價   603.00   ＝ 我方**收盤價**的最高          ⭐ 逐位相同
                      （⛔ 而我方**盤中**最高是 604.00）
收市最低價   573.00   ＝ 我方**收盤價**的最低          ⭐ 逐位相同
                      （⛔ 而我方**盤中**最低是 561.00）
```

⇒ ⭐⭐ **同一族的兩張表，「最高價」是兩個不同的量**——年表是盤中、月表是收盤。
⛔ 把它們當同一欄用，差的不是誤差，是定義。⚠ 而兩邊都叫「最高價」。

#### ⛔⛔ 而拿**上市那張月表**（`FMSRFK`）一起量 ⇒ 差異有**三個**，不是一個

```
                上市 FMSRFK                上櫃 monthlyStock
high／low       **盤中**最高／最低          **收市**（收盤）最高／最低
avg             **加權**平均（金額÷股數）    **收盤價的簡單平均**
成交量單位      股                          **仟股**
```

⇒ 實測（2330，115/1、115/2、115/3 三個月，對我方日檔）：

```
官方 high/low  1835/1545、2025/1740、1995/1760
我方 **盤中**   1835/1545、2025/1740、1995/1760   ⭐ **3／3 逐位相同**
我方 **收盤**   1820/1585、2015/1765、1975/1760   ⛔ 三個月都不一樣
官方 avg 1718.05 vs 我方收盤簡單平均 1727.62
        而 金額÷股數 ＝ 1,463,745,509,957 ÷ 851,975,987 ＝ **1,717.82** ⇒ ⭐ 是加權
```

⇒ ⭐⭐ **兩張月表的 `high`／`low`／`avg` 是三對不同的量，而欄名都一樣。**
⛔ 併進同一張 `official_monthly_amount.csv` ＝ 一次做出**三道**靜默的定義接縫。
⇒ 所以上櫃的月表**還沒接**：它要自己一份檔、欄名自己帶定義
（`close_high`／`close_low`／`close_avg`／`volume_kshares`）。

#### ⇒ 而量那三欄**仍然**是另一種口徑，⛔ 而且比例還不一樣

```
筆數    我方 22,286      官方 44,168      **1.98 倍**
金額    16,859,161 仟元  17,258,302 仟元  ＋2.4%
股數    28,797 仟股      29,478 仟股      ＋2.4%
```

⚠ 年表那一年的筆數比是 **2.56 倍**，月表這一個月是 **1.98 倍**
⇒ ⛔ 不是一個固定倍數 ⇒ 「買賣各算一筆」**解釋不了全部** ⇒ **我還是不知道**。

### ⛔ 而那之前 probe 121 的紀錄留著（那個錯的形狀本身是紀錄）：**兩套參數名我都猜錯了**

```
GET/POST monthlyStock?code=6488&date=2024/01/01  ⇒ {"stat":"參數輸入錯誤"}
GET/POST monthlyStock?stkno=6488&year=2024       ⇒ stat:"ok"、而 data:[]
    ⭐ 而它自己講了：`code: null`、`name: ""`、`title: "null "`、`totalCount: 0`
    ⇒ 那是「**我沒收到代號**」，⛔ 不是「這一檔沒有資料」（第二點①）
```

⭐ 而**欄位已經知道了**（回應帶了 `fields`，即使 `data` 是空的）：

    年／月／收市最高價／收市最低價／**收市平均價**／成交筆數／
    成交金額仟元(A)／成交張數(B)／成交週轉率(%)

⇒ 下一步**不是再猜第三套**，是把那一頁的 `<input>`／`<select>` 的 `name`／`id`
印出來（`tpex_probe` [14] 已加）——⭐ 跟讀 `action` 同一條路：
**從它自己寫的字讀，⛔ 不是從名字推**（三點5）。

## 為什麼要續跑

逐檔一個請求，2,000+ 檔 ⇒ 一趟跑不完。用 `--limit` 分批、`--resume` 記進度，
跟 `otc_adj.py` 同一個形狀。⛔ 排在 `feeds.yml` 不是 `daily.yml`。
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import backfill as B
import runlog
import twparse                     # ⭐ csv_cell 只有那一份（四點五）
from decimal import Decimal as _D, ROUND_DOWN as _ROUND_DOWN, \
    ROUND_HALF_EVEN as _ROUND_HALF_EVEN, ROUND_HALF_UP as _ROUND_HALF_UP

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
META = os.path.join(_ROOT, "meta")
# ⛔⛔ 路徑一律寫成**呼叫當下**才算的函式，⛔ 不是 import 當下就算好的常數。
#   ⚠ CLAUDE.md 第七點第五個那個坑：`mops.CHANGES` 在 import 當下就算好
#   ⇒ 之後再改 `OUT_DIR`，它不會跟著動 ⇒ 沙箱只導一個旋鈕，log 照樣寫進 repo。
#   ⭐ 這裡只有 **`META` 一個旋鈕**——⛔ 而「記得兩個都導」已經被否決過。
def yearly_path(market="twse"):
    """⭐ 兩個市場**共用同一張**價的判準表（⛔ 不是各一份）。

    ⚠ 那張表的欄位對上櫃只填得出**價**那五格：`avg_close`／`high`＋日期／
    `low`＋日期（跟我方日檔逐位相同，實測 6488 兩年）。
    ⛔ 而 `volume`／`amount`／`transactions` 留空——上櫃那三欄是**另一種口徑**
    （＋4.8%／＋5.0%／**＋156%**），⚠ 而留空是對的：那不是 0（五點三）。
    ⇒ 量的部分原樣另存在 `tpex_yearly_path()`，保留官方單位。
    """
    return os.path.join(META, "official_yearly_close.csv")


def monthly_path(market="twse"):
    return os.path.join(META, "official_monthly_amount.csv")


# ══════════════════════════════════════════════════════════════════
# ⭐⭐⭐ `avg_close` 的進位規則：**三段**，⛔ 不是「容許 ±0.01」
#
#   2026-09-16 母體級實測（17,832 個 (檔,年)，⛔ 不是抽樣。詳見
#   `docs/READ_CONTRACT.md` 的 `official_yearly_close.csv` 那一節）：
#
#     上櫃           7,948 格  無條件捨去                       100.0000%
#     上市 民107~    7,449 格  先到小數 3 位、再到 2 位用 banker's 100.0000%
#     上市 民104~106 2,435 格  直接四捨五入                      99.8768%（3 格例外）
#
#   ⭐ 有鑑別力的母體（兩條規則會給不同答案的）**503** 格：
#      民104~106 直接四捨五入 130／131｜民107~ banker's **372／372**。
#   ⛔ 拿全母體的命中率比是分不出來的（帶外兩條規則同答案）——第七點那一句。
#
#   ⚠ 已知 3 格解釋不了（都在民104~106、都恰好落在半分、官方都往下）：
#      2901/105 25.905→25.90｜3016/104 14.255→14.25｜4906/104 19.475→19.47
#   ⇒ ⛔ **成因不知道，那就寫不知道。**
#
#   ⛔ 這是**唯一**一份實作（四點五）。⚠ `backtest/audit_db.py` 目前是兩段
#     （上市 round／上櫃 trunc）⇒ 上市那半民107~ 有 372 格會誤報；已去信回測線。
TPE_ROUND_SWITCH_ROC = 107          # ⭐ 上市的進位規則在民國 107 年換掉


def avg_close_expected(mean, roc_year, market):
    """我方日收盤的簡單平均 `mean` → **官方會寫成的那個兩位小數**（`decimal.Decimal`）。

    `market`：`"twse"`／`"tpex"`（⛔ 必填，沒有預設值——四點五那條：
    兩種相反的語意，選哪一種的參數不可以有預設值）。
    ⚠ `mean` 要用 `Decimal` 傳進來；⛔ 傳 float 會先吃一次二進位誤差。
    """
    if market not in ("twse", "tpex"):
        raise ValueError(f"market 只能是 twse／tpex，收到 {market!r}")
    m = mean if isinstance(mean, _D) else _D(str(mean))
    if market == "tpex":
        return m.quantize(_D("0.01"), rounding=_ROUND_DOWN)
    if int(roc_year) >= TPE_ROUND_SWITCH_ROC:
        # ⭐ 兩步：先到 3 位（⚠ 第一步用哪一種進位不影響結果，實測三種同分），
        #    再到 2 位用 banker's ⇒ 帶內那些格會落在「分」位的**偶數**那一邊。
        return m.quantize(_D("0.001"), rounding=_ROUND_HALF_UP) \
                .quantize(_D("0.01"), rounding=_ROUND_HALF_EVEN)
    return m.quantize(_D("0.01"), rounding=_ROUND_HALF_UP)


def avg_close_matches(mean, roc_year, market, official):
    """官方寫的那個值對不對得上我方 ⇒ True／False。⛔ 逐位比，不留容許值。"""
    o = official if isinstance(official, _D) else _D(str(official))
    return avg_close_expected(mean, roc_year, market) == o


def tpex_yearly_path():
    return os.path.join(META, "official_yearly_tpex.csv")


def done_path(market="twse"):
    """續跑台帳。⭐ 兩個市場**各一份**——⛔ 它們的母體與端點都不同。"""
    sfx = "" if market == "twse" else f"_{market}"
    return os.path.join(META, f"_official_stats_done{sfx}.csv")


def miss_path(market="twse"):
    sfx = "" if market == "twse" else f"_{market}"
    return os.path.join(META, f"_official_stats_miss{sfx}.csv")


BASE = "https://www.twse.com.tw/rwd/zh/afterTrading/{rep}?date={d}&stockNo={s}&response=json"

# ⛔ 欄名逐字照抄實測結果（`_parvalue_probe.txt` [T12]）。
#   FMNPTK 有**兩個都叫「日期」**的欄（最高價日、最低價日）⇒ 用位置取，不用名字。
Y_HEADER = ["stock_id", "roc_year", "volume", "amount", "transactions",
            "high", "high_date", "low", "low_date", "avg_close", "asof"]
M_HEADER = ["stock_id", "roc_year", "month", "high", "low", "avg_price",
            "transactions", "amount", "volume", "turnover", "asof"]


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 上櫃那一半（2026-09-16 probe 120/121 實測）
#
#   一發回**全部 12 年**（`totalCount:12`，民國 104~115）；
#   ⛔ `date` **不是篩選器**（我送 2024 它照樣回全部）。
#   ⚠ `fields` 有**兩個都叫「日期」**的欄 ⇒ 跟 FMNPTK 一樣**用位置取**。
#
#   ⭐ 哪一欄可以信：拿 6488 環球晶跟我方日檔對 114／115 兩年——
#
#       收盤平均價        366.43／749.62      **逐位相同**
#       盤中最高價＋日期  558.00@10/27／1,600.00@7/15   **逐位相同**
#       盤中最低價＋日期  255.50@4/09／403.00@1/02      **逐位相同**
#       ⛔ 成交張數 ＋4.8%｜成交金額 ＋5.0%｜成交筆數 **＋156%**
#       ⛔ 加權平均價(B/A) ⇒ **由那兩個口徑不同的欄推導** ⇒ 一起不可信
#
#   ⇒ ⭐ **價那五格進共用判準表，量那三欄原樣另存**（保留官方單位：張／仟元／仟筆）。
#     ⛔ 換算後併進同一張表 ＝ 做出一張接縫不會報錯的表（第二點那條 FMTQIK）。
# ══════════════════════════════════════════════════════════════════
TPEX_YEARLY_URL = ("https://www.tpex.org.tw/www/zh-tw/statistics/yearlyStock"
                   "?code={s}&response=json")
TPEX_YEARLY = os.path.join(META, "official_yearly_tpex.csv")
# ⛔ 欄名帶單位：`_lots`（張）／`_kntd`（仟元）／`_k`（仟筆）
#   ⚠ 第十個那條：跨線交換一個量，欄名要講得出它是什麼單位／怎麼推導的。
TY_HEADER = ["stock_id", "roc_year", "volume_lots", "amount_kntd",
             "transactions_k", "wavg_price_derived", "asof"]


def fetch_one_tpex(sid):
    """打一發上櫃 `yearlyStock` → `(價那五格, 量那四格, err)`。

    ⛔ 沒有 `date` 參數：那一頁的表單欄位實測是 `['code', 'query']`
    （probe 122 從頁面自己讀到的）⇒ 它**本來就不吃日期**，一發回全部 12 年。
    """
    raw, err = B.get(TPEX_YEARLY_URL.format(s=sid), retries=2, timeout=45)
    if err or not raw:
        return [], [], f"yearlyStock {str(err)[:80]}"
    return parse_tpex_yearly(raw, sid)


def parse_tpex_yearly(payload, sid):
    """上櫃 `yearlyStock` 的回應 → `(價那五格, 量那四格, err)`。

    → `price_rows` 每列 `(代號, 民國年, 最高, 最高日, 最低, 最低日, 收盤平均價)`
      `vol_rows`   每列 `(代號, 民國年, 張數, 仟元, 仟筆, 加權平均價)`

    ⛔ 判準是**回應自己回顯的 `code`**跟我請求的那一檔相同（第二點：
    「這一批要自己講出它是誰」）——⚠ 而 `monthlyStock` 那一發就是靠這個看出
    參數沒生效的（`code: null`、`stat` 照樣是 `ok`）。
    """
    try:
        d = json.loads(payload.decode("utf-8", "replace")
                       if isinstance(payload, bytes) else payload)
    except ValueError as ex:                                     # noqa: BLE001
        return [], [], f"yearlyStock 不是 JSON：{str(ex)[:80]}"
    if (d.get("stat") or "") != "ok":
        return [], [], f"yearlyStock stat={d.get('stat')!r}"
    tabs = d.get("tables") or []
    if not tabs:
        return [], [], "yearlyStock 回應沒有 tables"
    t = tabs[0]
    got = (t.get("code") or "").strip()
    if got != str(sid):
        # ⭐ 這一格就是「靜靜回了別的東西」的那一種（第二點①）
        return [], [], (f"yearlyStock 回顯的 code 是 {got!r}，"
                        f"⛔ 不是我送的 {sid!r} ⇒ 參數沒生效")
    pr, vr = [], []
    for row in (t.get("data") or []):
        if len(row) < 10:
            continue
        y = str(row[0]).strip()
        # ⚠ 位置取，⛔ 不用名字：`fields` 裡有兩個都叫「日期」
        pr.append((sid, y, _n(row[5]), str(row[6]).strip(),
                   _n(row[7]), str(row[8]).strip(), _n(row[9])))
        vr.append((sid, y, _n(row[1]), _n(row[2]), _n(row[3]), _n(row[4])))
    if not pr:
        return [], [], "yearlyStock 回了 0 列（⛔ 不是「這一檔沒有」）"
    return pr, vr, None


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ **月**那一半：一發只回一年 ⇒ 工作單位是 **(代號, 年)**，⛔ 不是代號
#
# 2026-09-16 回測線 0841 §四 4. 點名要它（「更早年份你抓了我就重跑」），
# ⚠ 而我自己也需要它當**外部錨點**：他們量到兩件我在「年」這一級分不出來的事——
#   ② 民國 109 的年成交金額，我方全部多 1~1,040 元（量與筆數逐位相同）
#   ④ 上市年均價有 1.9% 落在「四捨五入 +0.01」
#      ✅ **2026-09-16 結案：進位規則，三段**（見上面 `avg_close_expected`）
#      ⇒ ⛔ 這一件**不再**需要月表；②（民109 金額）才需要，而它也結了：
#        我方日檔 == 官方 `STOCK_DAY` 逐日（三檔×三欄逐位相同），
#        而官方月表 `FMSRFK` 比它**少** 317／105／20 元
#        ⇒ ⭐ 是官方**自己兩條路**不一致，⛔ 不是我方。成因不知道。
#
# ⛔ 而兩張月表的欄**同名不同量**（第二點那條的鏡像），所以**各一份檔**：
#
#     欄        上市 FMSRFK              上櫃 monthlyStock
#     high/low  **盤中**最高／最低        **收市**（收盤）最高／最低
#     avg       **加權**（金額÷股數）     **收盤價的簡單平均**
#     量單位    股                       **仟股**
#
# ⇒ 上櫃這一份的欄名**自己帶定義**（`close_high`／`close_avg`／`volume_kshares`），
#   ⛔ 不留「最高價」「平均價」這種對不上時無法判斷是誰錯的欄名（第七點第十個）。
# ══════════════════════════════════════════════════════════════════
TPEX_MONTHLY_URL = ("https://www.tpex.org.tw/www/zh-tw/statistics/monthlyStock"
                    "?code={s}&date={y}&response=json")
#: ⭐ 欄名帶推導方式與單位。⚠ `close_*` ＝ 收盤價的高/低/簡單平均，
#  ⛔ 不是盤中；`volume_kshares` ＝ 仟股，⛔ 不是股也不是張。
TM_HEADER = ["stock_id", "roc_year", "month", "close_high", "close_low",
             "close_avg", "transactions", "amount_kntd", "volume_kshares",
             "turnover_pct", "asof"]
#: ⛔⛔ 這個字串是**閘門**，不是註解：`code=null` 的空回應裡那一欄叫
#  `成交張數(B)`，⚠ 而**真的有資料**時它叫 `成交仟股(B)`——同一個端點、
#  同一個位置、兩個**差一千倍**的單位名。⇒ 對不上就整檔失敗，⛔ 不猜。
TM_VOL_FIELD = "成交仟股(B)"


def tpex_monthly_path():
    return os.path.join(META, "official_monthly_tpex.csv")


def sweep_done_path(market):
    """年份掃描的續跑台帳。⭐ 鍵是 **(代號, 民國年)**，⛔ 不是代號。

    ⚠ 跟 `done_path()` 分開的理由：那一份的工作單位是「一檔」（一發回全部年），
    ⛔ 而這一份是「一檔一年」——⭐ 混在同一份裡，`--market tpex` 那一趟會把
    掃過月表的檔當成「年表也做完了」，而畫面上完全正常。
    """
    return os.path.join(META, f"_official_monthly_done_{market}.csv")


def tm_key(row):
    """上櫃月表的主鍵 ＝ (代號, 民國年, 月)。⭐ 三格。"""
    return (row[0], row[1], row[2])


def roc_years(today=None):
    """要掃哪幾個民國年 → `[104, …, 今年]`。

    ⛔ **不是寫死的清單**：上限由今天算出來，⚠ 否則跨年那一天它會靜靜少掃一年
    （而「少掃一年」跟「那一年沒資料」在檔案上長得一模一樣）。
    ⭐ 下限 104 是我方日檔的起點（2015）——比它更早我方沒有東西可以對。
    """
    d = today or datetime.now(TPE)
    return list(range(104, d.year - 1911 + 1))


def parse_years(spec, today=None):
    """`"104-115"`／`"109"`／`""` → 年份清單。⛔ 空字串回**全部**。"""
    full = roc_years(today)
    spec = (spec or "").strip()
    if not spec or spec == "all":
        return full
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [y for y in out if y in full]


def parse_tpex_monthly(payload, sid, roc_y):
    """上櫃 `monthlyStock` 的回應 → `(rows, err)`。

    ⛔ 三道判準，缺一道就當失敗（第二點：這一批要自己講出它是誰、是哪一期）：
      ① 回顯的 `code` ＝ 我送的代號（⚠ 參數沒生效時它是 `null`，而 `stat` 仍是 ok）
      ② 回顯的 `date`（西元年）＝ 我送的那一年
      ③ ⭐ `fields` 裡的量欄名 ＝ `成交仟股(B)`
         ——⛔ 空回應裡它叫「成交張數」，差一千倍
    """
    try:
        d = json.loads(payload.decode("utf-8", "replace")
                       if isinstance(payload, bytes) else payload)
    except ValueError as ex:                                     # noqa: BLE001
        return [], f"monthlyStock 不是 JSON：{str(ex)[:80]}"
    if (d.get("stat") or "") != "ok":
        return [], f"monthlyStock stat={d.get('stat')!r}"
    tabs = d.get("tables") or []
    if not tabs:
        return [], "monthlyStock 回應沒有 tables"
    t = tabs[0]
    got = (t.get("code") or "").strip()
    if got != str(sid):
        return [], (f"monthlyStock 回顯的 code 是 {got!r}，"
                    f"⛔ 不是我送的 {sid!r} ⇒ 參數沒生效")
    ad = roc_y + 1911
    if str(t.get("date") or "").strip() != str(ad):
        return [], (f"monthlyStock 回顯的 date 是 {t.get('date')!r}，"
                    f"⛔ 不是我送的 {ad} ⇒ 那一年的參數沒生效")
    fields = [str(x).strip() for x in (t.get("fields") or [])]
    if TM_VOL_FIELD not in fields:
        return [], (f"monthlyStock 的量欄名是 {fields[7:8]!r}，"
                    f"⛔ 不是 {TM_VOL_FIELD!r} ⇒ **單位可能變了**，不落地")
    rows = []
    for r in (t.get("data") or []):
        if len(r) < 9:
            continue
        rows.append([sid, str(r[0]).strip(), str(r[1]).strip(),
                     _n(r[2]), _n(r[3]), _n(r[4]), _n(r[5]), _n(r[6]),
                     _n(r[7]), _n(r[8])])
    if not rows:
        return [], f"monthlyStock {ad} 回了 0 列（⛔ 不是「這一檔沒有」）"
    return rows, None


def fetch_month_tpex(sid, roc_y, today):
    rows, err = _fetch_json(TPEX_MONTHLY_URL.format(s=sid, y=roc_y + 1911),
                            lambda raw: parse_tpex_monthly(raw, sid, roc_y))
    return ([r + [today] for r in rows], err)


def fetch_month_twse(sid, roc_y, today):
    """上市 `FMSRFK`，`date=<西元年>0101` ⇒ 那一年的 12 個月。

    ⭐ 判準跟 `fetch_one()` 同一條：`title` 會回音代號**與年度**
    （`'114年2330 台積電  月成交資訊'`）⇒ 兩個都要對上。
    ⛔ 只比代號不夠：`date` 壞掉時它會靜靜回**今年**（第二點①）。
    """
    ad = roc_y + 1911
    raw, err = B.get(BASE.format(rep="FMSRFK", d=f"{ad}0101", s=sid),
                     retries=2, timeout=45)
    if err:
        return [], f"FMSRFK {str(err)[:60]}"
    data, title, e = _rows(raw)
    if e:
        return [], f"FMSRFK {e}"
    if title and sid not in title:
        return [], f"FMSRFK title 沒有回音代號：{title!r}"
    if title and f"{roc_y}年" not in title:
        return [], (f"FMSRFK title 是 {title!r}，⛔ 沒有回音我送的 {roc_y} 年"
                    " ⇒ 那一年的參數沒生效（⚠ 它會靜靜回最新一年）")
    ms = []
    for r in data:
        r = list(r) + [""] * 9
        y, mo = _n(r[0]), _n(r[1])
        if not (re.fullmatch(r"\d{2,3}", y) and re.fullmatch(r"\d{1,2}", mo)):
            continue
        ms.append([sid, y, mo, _n(r[2]), _n(r[3]), _n(r[4]), _n(r[5]),
                   _n(r[6]), _n(r[7]), _n(r[8]), today])
    if not ms:
        return [], f"FMSRFK {roc_y} 回了 0 列"
    return ms, None


def _fetch_json(url, parse):
    raw, err = B.get(url, retries=2, timeout=45)
    if err or not raw:
        return [], str(err)[:80]
    return parse(raw)


def sweep_spec(market):
    """每個市場的「抓一檔一年」是哪一支 ＋ 寫到哪一份檔 ＋ 表頭 ＋ 主鍵。

    ⭐ 只有這一份對照表（四點五）：⚠ ⛔ 不要在 `run_sweep()` 或 `main()` 裡
    再 if 一次市場——那就是「同一件事兩份實作」的起點。
    ⛔ 寫成函式而不是模組層的 dict，是因為 `m_key` 定義在這一行**後面**
    ⇒ 模組層會當場 NameError（⚠ 而且是 import 時，不是呼叫時）。
    """
    return {
        "twse": (fetch_month_twse, monthly_path, M_HEADER, m_key),
        "tpex": (fetch_month_tpex, tpex_monthly_path, TM_HEADER, tm_key),
    }[market]


def sweep_todo(pool, years, done, limit):
    """→ 本趟要問的 `[(代號, 民國年)]`。⭐ **先把一檔的所有年做完**再換下一檔。

    ⚠ 反過來（先掃完一年的所有檔）的話，任何一趟被砍都會讓**每一檔都只有幾年**
    ⇒ ⛔ 那份檔在任何時間點都「看起來有資料、而且每一檔都殘缺」，
    而殘缺跟「那一檔那幾年沒上市」長得一模一樣（第二點）。
    """
    out = []
    for sid in pool:
        for y in years:
            if (sid, str(y)) in done:
                continue
            out.append((sid, y))
            if len(out) >= limit:
                return out
    return out


def load_sweep_done(path):
    done = set()
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as f:
            f.readline()
            for ln in f:
                p = ln.strip().split(",")
                if len(p) >= 2:
                    done.add((p[0].strip(), p[1].strip()))
    return done


SWEEP_HEADER = "stock_id,roc_year,asof,why"


def _upgrade_sweep_header(path):
    """舊檔的表頭沒有 `why` 欄 ⇒ 把表頭提上來（舊列的 `why` 留空）。→ bool。

    ## ⛔ 為什麼要有這一步

    `why` 欄是 2026-09-16 早上才加的 ⇒ **tpex 那份台帳是舊表頭**
    （`stock_id,roc_year,asof`，3,691 列，run 167 寫的）。
    ⇒ 而 `save_sweep_done` 是**追加** ⇒ 下一趥會把 **4 欄**的列
    接在**3 欄**的表頭後面 ⇒ ⚠ 一個欄數不齊的 CSV。

    ⭐ 本程式自己讀得下去（`load_sweep_done` 只取前兩欄）
    ——⛔ **而那正是它危險的地方**：下一個用 `csv.DictReader` 讀它的人
    會拿到一個 `None` 鍵，而不會有任何地方報錯
    （本 repo 記過的「同一個 feed 的 header 會隨時間增欄」那一族）。

    ⚠ 而它是**合併不是取代**（四點六）：舊列一列都不動，
    ⭐ 而「寫完的列數不可以少於原來那份」是這一步自己的閘門。
    """
    if not os.path.exists(path):
        return False
    with io.open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() == SWEEP_HEADER:
        return False
    before = len(lines) - 1
    body = [ln + "," if ln and ln.count(",") == 2 else ln for ln in lines[1:]]
    out = [SWEEP_HEADER] + body
    if len(out) - 1 < before:                       # ⛔ 永遠不可以變少
        raise RuntimeError(
            f"⛔ 升表頭會讓列數變少（{before} → {len(out) - 1}），不寫。")
    io.open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return True


def save_sweep_done(path, pairs, today, why=""):
    """⭐ **追加**（四點六）：這一趟只知道自己那一部分。

    ⚠ `why` 空字串＝真的抓到了；`"nodata"`＝官方說沒有而我方那一年也沒有
    （`sweep_consistent_nodata()`）⇒ ⭐ **兩種要分得出來**，
    ⛔ 混在一起的話，日後我方日檔補齊時沒有辦法把那幾格重開。
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _upgrade_sweep_header(path)
    new = not os.path.exists(path)
    with io.open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(SWEEP_HEADER + "\n")
        for sid, y in pairs:
            f.write(f"{sid},{y},{today},{why}\n")
    return len(pairs)


def sweep_fail_note(todo, ok, fail):
    """那道閘門的說明文字。→ 一句話。

    ⛔⛔ 2026-09-16 run 163 實測：它**通過**了（392／400 成功），
    ⚠ 而說明印的是「本趟 400 格**全部失敗**」——⭐ 一個通過的檢查，
    說明寫著相反的話。⇒ 讀的人會照那句去查一個根本沒發生的故障。

    ⚠ 而這**正是**同一支檔裡 `batch_fail_note()` 已經修過一次的那個錯
    ——⛔ 我寫 `run_sweep` 時沒去看它，又寫了一次（四點五：同一件事兩份實作）。
    ⇒ ⭐ 收成具名函式的理由就是「它要驗得到」：一個 f-string 驗不到。
    """
    if not todo:
        return "本趟沒有要做的格（⇒ 這個市場這些年份都做完了）"
    if ok:
        return (f"成功 {len(ok)}／{len(todo)} 格"
                + (f"｜失敗 {len(fail)} 格，例：{fail[:2]}" if fail else "｜0 失敗"))
    return f"⛔ 本趟 {len(todo)} 格**全部失敗**｜例：{fail[:2]}"


def our_market_years(sid, market, root=None):
    """→ {西元年字串}：我方 `data/stocks/<sid>.csv` 裡 `market == market` 的那幾年。

    ⭐ 判準用**資料自己**（第四點），⛔ 不是去 `delisted.csv` 查
    ——CLAUDE.md 記過：**上櫃轉上市**在我方資料裡就是 `market` 欄從 `tpex`
    變成 `twse`，⛔ 而 `delisted.csv` 記的是**下市**，轉上市不是下市。
    ⚠ 讀不到那個檔就回**空集合**（⇒ 呼叫端會當成「那一年我方也沒有」）。
    """
    p = os.path.join(root or _ROOT, "stocks", f"{sid}.csv")
    out = set()
    if not os.path.exists(p):
        return out
    try:
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r.get("market") or "") == market:
                    out.add((r.get("date") or "")[:4])
    except OSError:
        return set()
    return out


#: ⭐ 官方「這一格沒有資料」的那句話。⛔ 它**講不出**是哪一種
#  （未上市／參數越界／端點壞掉都長這樣，CLAUDE.md 第二點）
#  ⇒ 所以它**單獨**不可以當判準，一定要跟我方資料做「且」。
# ⛔⛔ 2026-09-16 晚：這一行本來是**一個字串**，而那是 **TWSE** 的話。
#   ⇒ feeds run 167（tpex 月表）實測：本趥 5,000 格**失敗 1,309**，
#     訊息全部是 `monthlyStock stat='**查無該筆資料**,請重新查詢!!'`
#   ⇒ ⛔ 比不中 ⇒ 那 1,309 格**一格都沒被記起來** ⇒ 每一趥都回來
#   ⇒ ⭐ 跟早上幫 twse 修好的**同一個 bug**，只是另一個市場沒跟上
#     ——CLAUDE.md 四點五那一族：**修好一支、另一支沒跟上，而沒有人會發現**。
#
# ⇒ ⭐ 改成**逐市場**，而且查不到要**大聲丟例外**：
#   ⛔ 不可以有預設值——預設值會讓下一個市場默默套上**別人的那句話**，
#   而那個 bug 的畫面是「掉這麼多格而一路沒人說」（四點五的通則）。
# ⚠ 比的是**子串**，⛔ 不含標點：官方兩邊的驚嘆號個數不同（`!` vs `!!`）。
NODATA_MARK = {"twse": "沒有符合條件的資料",
               "tpex": "查無該筆資料"}


def nodata_mark(market):
    """這個市場的「官方說沒有」是哪一句 → str。⛔ 查不到就丟例外。"""
    if market not in NODATA_MARK:
        raise ValueError(
            f"⛔ market={market!r} 沒有登記「官方說沒有」那一句話；"
            f"目前只有 {sorted(NODATA_MARK)}。"
            " ⚠ 默默套別人的那句會讓這個掃描永遠不收斂。")
    return NODATA_MARK[market]


def sweep_consistent_nodata(err, sid, roc_y, market, root=None):
    """這一格的失敗是不是「**官方說沒有，而我方那一年也沒有**」→ bool。

    ## ⛔ 為什麼要有這一條：不然這個掃描**永遠不會收斂**

    `save_sweep_done()` 只記成功的格子 ⇒ ⭐ 失敗的每一趟都回到 todo。
    ⚠ 而 2026-09-16 run 166 實測：本趟 5,000 格**失敗 2,097**（42%），
    訊息全部是 `FMSRFK stat='很抱歉，沒有符合條件的資料!'`。
    ⇒ 離線拆開來看（母體：還沒完成的 3,067 格）：

    ```
    ⭐ 我方那一年**沒有 twse 日檔**  **2,180**（71.1%）⇒ 官方說沒有是**一致**的
    ⚠ 我方那一年**有** twse 日檔       **887**  ⇒ 那才是真的還沒問到
    ```

    ⇒ ⛔ 不修的話，往後每一趟有 **71%** 的預算花在**永遠不會成功**的格子上，
    ⚠ 而且到最後「剩下的剛好全部失敗」⇒ `sweep_fail_note` 那道閘門必然誤判
    （CLAUDE.md 七點五第三個：**以「全部 X」為故障判準的閘門，
    在「剩下的剛好全部 X」時必然誤判**）。

    ## ⇒ ⭐ 判準是**兩個條件的「且」**，⛔ 缺一個都不可以

    ```
    ① 官方的訊息是那一句「沒有符合條件的資料」
       ⛔ 它單獨講不出是哪一種（第二點）⇒ 單獨**不算**
    ② ⭐ 而我方那一年**也沒有那個市場的日檔**
       ⇒ 兩邊一致 ⇒ 這一格是**問完了**，不是「還沒問到」
    ```

    ⚠ 前提（我自己標）：②用的是我方資料，⛔ 而我方那一年沒有日檔**也可能是我方漏了**
    ⇒ 那時這一格會被記成「問完了」而其實沒有。⭐ 而它**看得出來**：
    台帳裡那幾格帶 `nodata` 標記，⇒ 我方日檔日後補齊時可以拿它重開。
    """
    if nodata_mark(market) not in str(err):
        return False
    return str(roc_y + 1911) not in our_market_years(sid, market, root)


def run_sweep(a, rl, today):
    """月表的年份掃描（兩個市場走**同一條**路）。→ exit code。"""
    fetch, path_of, header, key = sweep_spec(a.market)
    years = parse_years(a.months_years)
    pool = codes(covered=(a.market,))
    dp = sweep_done_path(a.market)
    done = set() if a.force else load_sweep_done(dp)
    todo = sweep_todo(pool, years, done, a.limit)
    out = path_of()
    R = _load(out, header, key)
    n0 = len(R)
    rl.info("這一趟", f"**月表年份掃描**｜市場 **{a.market}**"
                      f"｜年份 {years[0]}~{years[-1]}（{len(years)} 年）"
            + ("｜端點 `afterTrading/FMSRFK?date=<西元>0101`"
               if a.market == "twse" else
               "｜端點 `statistics/monthlyStock?code=&date=<西元年>`"))
    rl.info("續跑", f"母體 **{len(pool):,}** 檔 × {len(years)} 年 ＝ "
                    f"**{len(pool)*len(years):,}** 格"
                    f"｜**本趟開始前**已完成 {len(done):,}｜本趟要做 {len(todo):,}"
                    f"　⇒ ⭐ 本趟跑完之後大約還剩 "
                    f"**{max(0, len(pool)*len(years)-len(done)-len(todo)):,}** 格"
                    "（⚠ 是**大約**：本趟失敗的那幾格還會再回來）")
    ok, fail, nodata, flushed = [], [], [], 0
    for i, (sid, y) in enumerate(todo, 1):
        rows, err = fetch(sid, y, today)
        if err:
            fail.append((f"{sid}/{y}", err))
            # ⭐ 「官方說沒有」**而且**「我方那一年也沒有那個市場的日檔」
            #   ⇒ 這一格是**問完了**，記進台帳（帶 `nodata` 標記）
            #   ⇒ ⛔ 否則它每一趟都回到 todo ⇒ 這個掃描永遠不收斂
            #     （run 166 實測：5,000 格裡 2,097 失敗，而其中 71% 是這一種）
            if sweep_consistent_nodata(err, sid, y, a.market):
                nodata.append((sid, str(y)))
            print(f"  [{i}/{len(todo)}] {sid}/{y} ✗ {err}", flush=True)
        else:
            for r in rows:
                R[key(r)] = r
            ok.append((sid, str(y)))
            print(f"  [{i}/{len(todo)}] {sid}/{y} ✓ {len(rows)} 月", flush=True)
            if len(ok) - flushed >= FLUSH_EVERY:
                _save(out, header, R)
                flushed += save_sweep_done(dp, ok[flushed:], today)
                print(f"  ⭐ 期中落地：{flushed}／{len(todo)}", flush=True)
                # ⛔⛔ 這裡的「落地」只寫到**工作區**，⛔ 不是推到 main——
                #   推是 workflow 最後那一步（`push_data.sh`）做的。
                #
                # ⛔⛔⛔ 而我 2026-09-16 在這裡寫過一句**錯的**：
                #   「擋不住的是 job 層級被砍 ⇒ 那一趟做的**全部**都不會進 main。」
                #   ⭐ 同一天 **run 165 實測推翻了它**：
                #
                #     conclusion **cancelled**（02:34:40 開跑，08:24:54 撞 350 分上限）
                #     ⇒ ⭐⭐ 而台帳 776 → **7,926 格**、月表 16,912 → **94,909 列**
                #       ——**7,150 格進了 main**
                #
                #   ⇒ 原因：那一步的 commit 是 `if: always()` ⇒ **被砍時它照樣跑**，
                #     而期中落地已經把東西寫進工作區了 ⇒ ⭐ **期中落地救得回來**。
                #
                # ⚠ 而**真的丟掉的是 runlog 區塊**：`run_sweep` 沒走到 `rl.finish()`
                #   ⇒ `_last_run.md` 裡 `official_stats:months:twse` 那一塊停在**上一趟**
                #   ⇒ ⛔⛔ 讀那一塊的人會以為這一趟沒跑（四點二④③：**一定要看時戳**）。
                #   ⇒ ⭐ 所以被砍那一趟的**可見性要靠資料**（台帳的格數），
                #     ⛔ 不是靠 runlog——而那正是 CLAUDE.md 四點二⑧那一條。
                #
                # ⇒ ⭐ `months_limit` 的上限仍然要留餘裕（實測 **2.55 秒/格**，
                #   ⛔ 不是我當初只算 `--sleep` 的 1 秒）：5,000 格 ≈ 212 分，
                #   而 8,000 ≈ 340 分 ⇒ 撞上限（run 165 就是）。
                #   ⚠ 而「撞上限」的代價現在量清楚了：**不是全丟**，是
                #   ⭐ 丟掉最後不到 50 格 ＋ **整塊 runlog**。
        if a.sleep:
            time.sleep(a.sleep)
    if R:
        _save(out, header, R)
    save_sweep_done(dp, ok[flushed:], today)
    if nodata:
        save_sweep_done(dp, nodata, today, why="nodata")
    rl.info("⭐ 問完了但官方沒有",
            f"**{len(nodata):,}** 格（官方說「{nodata_mark(a.market)}」**而且**我方那一年"
            f"也沒有 `{a.market}` 的日檔 ⇒ 兩邊一致）"
            "　⇒ ⭐ 記進台帳、**不再重問**；⛔ 而它帶 `nodata` 標記，"
            "我方日檔日後補齊時拿它重開"
            if nodata else
            "**0** 格（⚠ 本趟沒有這一種 ⇒ ⛔ 不代表這條判準沒用，"
            "只代表本趟失敗的都不是那一種）")
    rl.info("月表", f"{out.split('data/')[-1]}｜{len(R):,} 列（本趟 +{len(R)-n0}）")
    rl.info("本趟", f"成功 {len(ok)}／失敗 {len(fail)}"
            + (f"｜失敗例：{fail[:3]}" if fail else ""))
    if a.market == "tpex":
        rl.info("⛔ 欄名帶定義（⚠ 跟上市月表**不是同一個量**）",
                "`close_high`／`close_low`／`close_avg` ＝ **收盤價**的高／低／"
                "簡單平均（⛔ 上市那張是**盤中**高低＋**加權**均價）；"
                "`volume_kshares` ＝ **仟股**（⛔ 上市那張是股）"
                "　⇒ ⛔ 兩張表不可以合併，⚠ 而主鍵不重疊 ⇒ 合了也不會報錯")
    # ⛔ 只增不減：這是外部判準，寫短了等於判準消失。
    rl.check("月表只增不減", len(R) >= n0, f"{n0}→{len(R)}")
    # ⚠ 本趟有東西要做而**一格都沒成功** ⇒ 當場紅（⛔ 不是靜靜跑完）
    rl.check("本趟不是全失敗", (not todo) or bool(ok), sweep_fail_note(todo, ok, fail))
    return rl.finish()


def _n(v):
    return str(v).replace(",", "").strip()


def _rows(raw):
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None, None, "不是 JSON"
    if str(d.get("stat")) != "OK":
        return None, None, f"stat={d.get('stat')!r}"
    tb = (B._tables(d) or [{}])[0]
    return (tb.get("data") or []), str(d.get("title") or ""), None


def fetch_one(sid, today):
    """→ (yearly_rows, monthly_rows, err)。⛔ 任何一支失敗就整檔失敗，不半套落地。"""
    raw, err = B.get(BASE.format(rep="FMNPTK", d=today, s=sid), retries=2, timeout=45)
    if err:
        return None, None, f"FMNPTK {str(err)[:60]}"
    data, _t, e = _rows(raw)
    if e:
        return None, None, f"FMNPTK {e}"
    ys = []
    for r in data:
        r = list(r) + [""] * 9
        # ⛔ 用位置取：這一支有兩個欄位都叫「日期」
        y = _n(r[0])
        if not re.fullmatch(r"\d{2,3}", y):
            continue
        ys.append([sid, y, _n(r[1]), _n(r[2]), _n(r[3]), _n(r[4]), _n(r[5]),
                   _n(r[6]), _n(r[7]), _n(r[8]), today])

    raw, err = B.get(BASE.format(rep="FMSRFK", d=today, s=sid), retries=2, timeout=45)
    if err:
        return None, None, f"FMSRFK {str(err)[:60]}"
    data, title, e = _rows(raw)
    if e:
        return None, None, f"FMSRFK {e}"
    # ⭐ FMSRFK **有** title，而且會回音代號 ⇒ 用它擋「回了別檔的資料」。
    #   ⛔ FMNPTK 沒有 title，所以上面那一支只能靠「年度」欄自我識別。
    if title and sid not in title:
        return None, None, f"FMSRFK title 沒有回音代號：{title!r}"
    ms = []
    for r in data:
        r = list(r) + [""] * 9
        y, mo = _n(r[0]), _n(r[1])
        if not (re.fullmatch(r"\d{2,3}", y) and re.fullmatch(r"\d{1,2}", mo)):
            continue
        ms.append([sid, y, mo, _n(r[2]), _n(r[3]), _n(r[4]), _n(r[5]),
                   _n(r[6]), _n(r[7]), _n(r[8]), today])
    return ys, ms, None


def _load(path, header, key):
    """讀回一份判準表 → `{主鍵: 列}`。

    ⛔⛔ `key` **必填**：它必須跟寫入端用的是**同一支**。
    ⚠ 2026-09-16 我把寫入端從 `r[:3]` 改成 `y_key`（兩格）卻**忘了改這裡**
    ⇒ 讀進來的列掛在三格的鍵上、本趟抓到的掛在兩格的鍵上
    ⇒ ⛔ 同一檔同一年會變成**兩列**——⭐ 比原本那個 bug 更糟（半修）。
    ⇒ 所以它沒有預設值：忘了傳會**當場 TypeError**，⛔ 而不是靜靜寫出兩列。
    """
    rows = {}
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                row = [r.get(k, "") for k in header]
                rows[key(row)] = row
    return rows


def y_key(row):
    """年度表的主鍵 ＝ **(代號, 民國年)**。⛔ 只有兩格。

    ## ⛔ 舊版是 `tuple(r[:3])`，而**年表的第三欄是 `volume`**

    ⚠ 那一版對**月**表是對的（第三欄是 `month`），對年表則把**成交股數**
    寫進了主鍵 ⇒ 同一檔同一年的數字若被官方修正過，`--force` 重抓會**多出一列**，
    ⛔ 而不是覆蓋掉舊的。
    ⭐ 而它至今沒有發作，只因為成功過的檔會進 `done` ⇒ **從來沒有被重問過**
    （實測 21,459 列，(代號,年度) 相異也是 21,459 ⇒ 0 筆重複）。
    ⇒ ⛔ 「還沒發作」不是判準（四點五⑥那句）。

    ⚠ 病根是**一個表達式做兩件事**：`r[:3]` 對月表對、對年表錯，
    而兩邊長得一模一樣。⇒ 收成兩支具名的。
    """
    return (row[0], row[1])


def m_key(row):
    """月表的主鍵 ＝ **(代號, 民國年, 月)**。⭐ 三格才對。"""
    return (row[0], row[1], row[2])


def _save(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for k in sorted(rows):
            w.writerow(rows[k])


#: ⭐ 這兩支端點**只涵蓋上市**——2026-09-15 量出來的，⛔ 不是推的。
#  第一趟 `--limit 400` 的逐檔結果按市場拆開：
#
#      twse      成功 325 / 嘗試 343  = **94%**
#      tpex      成功   0 / 嘗試  44  = **0%**
#      emerging  成功   0 / 嘗試  13  = **0%**
#
#  ⇒ 跟 `TWTB8U` 那次一模一樣的形狀（同一發請求裡上市全中、上櫃全不中）
#    ⇒ **端點不涵蓋上櫃**，⛔ 不是「那幾檔剛好沒資料」。
#  ⚠ 而失敗訊息是 `stat='很抱歉，沒有符合條件的資料!'`
#    ——⛔ 它講不出「是這一檔沒有」還是「這個市場整個沒有」（第二點）
#    ⇒ ⭐ 分辨它的**不是訊息，是拿兩個市場的命中率對一次**。
COVERED = ("twse",)

#: ⭐ 每幾檔落地一次。⛔ 太大＝被砍時賠得多；太小＝每次都重寫兩份大 CSV。
#  實測一趟 400 檔超過一小時 ⇒ 50 檔約 8 分鐘，賠得起。
FLUSH_EVERY = 50

# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 「問過而它答不出來」的台帳。⛔ 沒有它，這一條**永遠到不了終點**。
#
# 2026-09-15 實測（run 34976777901）：本趟 400 檔，成功 331／失敗 69。
# ⚠ 而**失敗的那 69 檔沒有被記下來** ⇒ 下一趟 `todo` 還是會挑到它們
#   ⇒ ⛔ 每一趟都拿越來越多的請求去問已知答不出來的檔，
#     而「還沒做 320 檔」這個數字**讀起來像是還有 320 檔可以補**。
#
# ⭐ 而那句失敗訊息（`很抱歉，沒有符合條件的資料!`）**講不出它是哪一種**
#   （第二點①那一族）：下市太久／那一年還沒上市／端點當下不穩，三種長得一樣。
# ⇒ 所以判準**不是**「失敗一次就放棄」，是**連續失敗 MISS_TRIES 次**，
#   ⛔ 而且只有在**那一趟有別的檔成功**（＝端點是活的）時才記一次。
#   ⚠ 沒有後面那個條件的話，端點掛掉一趟就會把全部 1,158 檔判死。
MISS_HEADER = "stock_id,tries,last_asof,why\n"
MISS_TRIES = 2


def codes(covered=COVERED):
    """這個端點**答得出來**的普通股（含已下市）。→ sorted list[str]。

    ⛔ 本來是「`kind == stock` 全收」（2,493 檔）⇒ 而其中 1,335 檔
    （tpex 972 ＋ emerging 363）**這個端點根本不涵蓋**
    ⇒ ⚠ 續跑永遠到不了 100%，而每一趟都像有在跑（四點六③那個形狀）。

    ⭐ 回傳的是**母體**；被排掉的那些由 `excluded()` 講出來，
    ⛔ 不可以靜靜消失——「排掉了」與「沒有這種股票」不是同一件事。
    """
    out = []
    p = os.path.join(META, "stocks.csv")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("kind") == "stock" and r.get("market") in covered:
                    out.append(r["stock_id"])
    return sorted(set(out))


def excluded(covered=COVERED):
    """被排掉的市場各有幾檔。→ dict[market, n]。⛔ 排掉要講出來，不是消失。"""
    n = {}
    p = os.path.join(META, "stocks.csv")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                m = r.get("market")
                if r.get("kind") == "stock" and m not in covered:
                    n[m] = n.get(m, 0) + 1
    return n


def is_code(sid):
    """看起來像不像一個證券代號。⭐ 只有這一份實作（`load_miss` 與 `bad_rows` 共用）。

    ⛔ 它不是「這個代號存不存在」——那要查母體。⚠ 它擋的是**根本不是代號**的東西：
    2026-09-16 實測 `_official_stats_miss.csv` 106 列裡有兩列的 `stock_id` 是
    `<head>` 與 `<meta h`（整頁 HTML 被寫進 `why` 欄，⇒ 換行把一列切成好幾列）。
    ⇒ 寫入端已經收成 `twparse.csv_cell`；這一支是**讀入端**的第二層
    （⭐ 兩層都要：舊檔裡已經有的那幾列不會自己消失）。
    """
    return bool(re.fullmatch(r"[0-9A-Z]{4,6}", (sid or "").strip()))


def bad_rows(path=None):
    """→ miss 台帳裡**不像代號**的那幾列（原始 `stock_id` 字串）。

    ⭐ 它存在的理由是第七點那句：「回報某群 0 筆時，要附上該判準抓到的正例數」
    ——⛔ 靜靜丟掉那幾列的話，檔案被污染這件事**沒有任何地方會說**。
    """
    p = path or miss_path()
    out = []
    if not os.path.exists(p):
        return out
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sid = (r.get("stock_id") or "").strip()
            if sid and not is_code(sid):
                out.append(sid[:40])
    return out


def load_miss(path=None):
    """→ {代號: (tries, last_asof, why)}。讀不到回 {}（⛔ 不是炸掉）。

    ⛔ 不像代號的列**丟掉**（見 `is_code`），⚠ 而丟了幾列由 `bad_rows()` 報出來
    ——⭐ 丟掉而不說，跟沒有被污染在畫面上一模一樣。
    """
    p = path or miss_path()
    out = {}
    if not os.path.exists(p):
        return out
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sid = (r.get("stock_id") or "").strip()
            if not sid or not is_code(sid):
                continue
            try:
                n = int(r.get("tries") or 0)
            except ValueError:
                n = 0
            out[sid] = (n, (r.get("last_asof") or "").strip(),
                        (r.get("why") or "").strip())
    return out


def bump_miss(fail, today, path=None, alive=True):
    """把本趟失敗的檔**累加**進 miss 台帳。→ 寫進去的檔數。

    ⛔⛔ `alive` 是**必填語意**：那一趟有沒有任何一檔成功。
    ⚠ 端點整個掛掉時每一檔都會失敗 ⇒ 若照樣累加，**兩趟就把全庫判死**，
    而畫面上完全正常（四點二那一族：這個綠燈在錯的時候也一樣綠）。
    ⇒ `alive=False` ⇒ **一個字都不寫**。

    ⭐ 而它是**合併**，⛔ 不是整份取代（四點六③ `save_done` 那個坑）：
    讀進來的 dict ＋ 本趟的鍵，再整份寫回。
    ⚠ 而**成功過的檔要從這裡消失**——那是由 `todo` 那一側保證的
    （成功之後它進 `done_path()`，就再也不會被挑到）⇒ 這裡只管累加。
    """
    p = path or miss_path()
    if not alive or not fail:
        return 0
    cur = load_miss(p)
    for sid, why in fail:
        n, _, _ = cur.get(sid, (0, "", ""))
        cur[sid] = (n + 1, today, str(why)[:120])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(MISS_HEADER)
        for sid in sorted(cur):
            n, asof, why = cur[sid]
            # ⭐ 走 `twparse.csv_cell`（全庫唯一那一份）：⛔ 只換逗號是不夠的,
            #   `why` 可能是整頁 HTML ⇒ 裡面的換行會把一列切成好幾列。
            f.write(f"{sid},{n},{asof},{twparse.csv_cell(why)}\n")
    return len(fail)


def split_todo(pool, done, miss, limit, tries=MISS_TRIES):
    """把母體切成三堆。→ (todo, 還沒問過的全部, 問到放棄的)。

    ⛔ **三堆要分開報**：「還沒做」把後兩者混在一起，
    ⚠ 而它們的意義完全不同——一個是還有得補，一個是**這條路到此為止**。
    """
    give_up = sorted(c for c in pool
                     if c not in done and miss.get(c, (0,))[0] >= tries)
    fresh = [c for c in pool if c not in done and c not in set(give_up)]
    return fresh[:limit], fresh, give_up


CONTROL_N = 3


def controls(pool, done, n=CONTROL_N):
    """→ 對照組：**已經答得出來過**而且**還在母體裡**的前 n 個代號。

    ⭐ 它回答的是「全失敗是**哪一種**」——⛔ 而那兩種在 runlog 上長得一模一樣：

    ```
    ① 端點被擋／參數壞了          ⇒ 真的要紅，⛔ 而且一個字都不可以寫進 miss
    ② 剩下的那一批**剛好**全部是
       這個端點答不出來的         ⇒ 這是**收斂的正常終局**，⛔ 不是故障
    ```

    ⚠ 2026-09-16 04:00（run 35010414869）就是②的形狀：母體 1,158、已完成 1,054、
    本趟 104 檔**全部失敗** ⇒ 舊判準 `alive=bool(ok)` 把它判成①（不記 miss）
    ⇒ ⛔ 那 104 檔永遠停在「還沒問過」，下一趟再問同一批、再全失敗
    ⇒ ⭐ **這道閘門從此每一趟都紅**——而 CLAUDE.md 四點五那條已經寫過代價：
    一道天天紅的閘門會被學會忽略，⚠ 而它一旦被忽略，真的壞掉那天也沒有人會看。

    ⭐ 而對照組是**算出來的**，⛔ 不是寫死的代號清單：
    `pool ∩ done` ＝「還在母體裡」∩「以前答得出來」——兩件事都是本趟現場量到的。
    ⚠ `sorted(...)[:n]` 只是要**同一批母體每趟挑到同一組**（可重現），
    ⛔ 不是因為那幾個代號有什麼特別。
    """
    return sorted(set(pool) & set(done))[:n]


def endpoint_alive(ctrl, today, fetch=None):
    """拿對照組問一次 ⇒ (True／False／**None**, 說明)。

    ⛔ `None` 是**第三種**，⚠ 而它跟 `False` 不可以混在一起：
    沒有對照組可用（`--force` 把 done 清掉，或母體與 done 沒有交集）
    ⇒ 意思是**這一層沒跑**，⛔ 不是「端點掛了」。
    ⇒ 照 CLAUDE.md 六點五那條：條件不成立就**大聲印出「這一層沒跑」**，
      ⛔ 不可以寫成斷言（那會把這條線整個關掉），而**退回舊判準**由呼叫端做。
    """
    f = fetch or fetch_one
    if not ctrl:
        return None, ("⛔ **這一層沒跑**：沒有對照組可用"
                      "（`--force` 清掉了 done，或母體與 done 沒有交集）"
                      "　⇒ ⚠ 退回舊判準「本趟有沒有任何一檔成功」")
    got, bad = [], []
    for sid in ctrl:
        _ys, _ms, err = f(sid, today)
        if err:
            bad.append((sid, str(err)[:60]))
        else:
            got.append(sid)
    if got:
        return True, (f"✓ 對照組 {len(got)}／{len(ctrl)} 答得出來（{','.join(got)}）"
                      "　⇒ ⭐ 端點是好的 ⇒ **本趟全失敗是那一批自己的性質**，"
                      "⛔ 不是故障 ⇒ 照常記 miss")
    return False, (f"✗ 對照組 {len(ctrl)} 檔**也**答不出來（{bad}）"
                   "　⇒ ⛔ 端點側的問題 ⇒ ⭐ 一個字都不寫進 miss 台帳")


def batch_fail_note(n_todo, n_ok, alive):
    """那道「不是整批失敗」閘門的**說明文字**。→ str。⭐ 抽出來是為了驗得到。

    ⛔⛔ 它一定要講**實際發生的那一種**。
    ⚠ 2026-09-16 run 158 實測：那一格**過了**（對照組 3／3 答得出來），
    而說明照樣印「且對照組也答不出來」
    ⇒ ⭐ 一個通過的檢查，說明寫著相反的話——**比沒有說明更糟**：
    讀的人會照那句去查一個根本沒發生的故障。
    """
    if not n_todo:
        return "本趟沒有要問的（⇒ 問得到的都問完了）"
    if n_ok:
        return f"成功 {n_ok}／{n_todo}"
    if alive:
        return (f"本趟 {n_todo} 檔全部失敗，⭐ **而對照組答得出來**"
                " ⇒ 端點是好的，那是**那一批自己的性質** ⇒ 照常記 miss")
    return f"⛔ 本趟 {n_todo} 檔全部失敗，**而且對照組也答不出來**"


def land(Y, M, ok, today, market="twse", T=None, rl=None):
    """把這一批**落地**：兩份判準檔 ＋ 續跑台帳。→ 這次寫進台帳的檔數。

    ⭐ 只有這一份實作（四點五）：**期中 flush 與最後一次走同一條路**。
    ⛔ 兩條路的話，期中那條遲早會少寫一個檔，而且沒有人會發現。

    ## ⛔ 為什麼要期中落地（CLAUDE.md 第四點）

    這一步 `--limit 400`，實測一趟 **超過一小時**。⚠ 而它本來只在**最後**寫檔
    ⇒ job 被砍（350 分上限）、runner 掉、任何例外 ⇒ ⛔ **整批 400 檔全部白跑**，
    而下一趟從同一個起點重來 ⇒ ⭐ 那正是「永遠跑不完，每趟都像有在跑」。

    ⇒ 台帳是 **append**（⛔ 不是整份取代——四點六③那個 `save_done` 的坑），
    ⚠ 而 `_save` 是「讀進來的 dict ＋ 本趟的鍵」再整份寫回 ⇒ 那是**逐鍵合併**，
    ⛔ 不是覆蓋。
    """
    yp, mp = yearly_path(market), monthly_path(market)
    if Y or os.path.exists(yp):
        _save(yp, Y_HEADER, Y)
    if M or os.path.exists(mp):
        _save(mp, M_HEADER, M)
    if T or os.path.exists(tpex_yearly_path()):
        _save(tpex_yearly_path(), TY_HEADER, T)
    if not ok:
        return 0
    dp = done_path(market)
    new = not os.path.exists(dp)
    with io.open(dp, "a", encoding="utf-8") as f:
        if new:
            f.write("stock_id,asof\n")
        for s in ok:
            f.write(f"{s},{today}\n")
    return len(ok)


def progress_lines(pool, done, todo, ex, give_up=(), market="twse"):
    """續跑那兩行怎麼寫。→ [(label, value)]。⭐ 抽出來是為了驗得到（第七點）。

    ⛔ **分母是 `pool`（這一趟這個市場涵蓋得到的），不是全部普通股。**
    ⚠ 用全部當分母的話，13% 這個數字會永遠爬不上去，
    而每一趟都像有在跑——那正是「永遠跑不完，每趟都像有在跑」那個形狀。

    ⛔⛔ `market` **必須進來**：2026-09-16 接上上櫃之後，
    「這個端點答不出來的」那一行若照舊寫，在 tpex 那一趟會把 **twse 1,158 檔**
    報成「答不出來」——⚠ 而它們只是**另一趟**在做，⛔ 完全不是缺口。
    """
    pct = len(done) * 100 // max(1, len(pool))
    gu = list(give_up or [])
    reach = len(pool) - len(gu)
    rp = len(done) * 100 // max(1, reach)
    mk = {"twse": "上市", "tpex": "上櫃"}.get(market, market)
    other = {"twse": "tpex", "tpex": "twse"}.get(market, "")
    n_other = ex.get(other, 0)
    n_esb = ex.get("emerging", 0)
    return [
        ("續跑", f"母體 **{len(pool):,}** 檔（⭐ 這一趟只有**{mk}**）"
                 f"｜已完成 {len(done):,}｜**{pct}%**｜本趟 {len(todo)}"),
        # ⭐⭐ 三堆分開報。⛔ 「還沒做」把後兩堆混在一起 ⇒ 那個數字會**永遠不歸零**，
        #   而每一趟都像有在跑（四點六③那個形狀）。
        ("⭐ 還剩下的分兩種（⛔ 不可以合著看）",
         f"**還沒問過** {max(0, reach - len(done)):,} 檔"
         f"｜**問到放棄** {len(gu):,} 檔"
         f"（連續 {MISS_TRIES} 趟答不出來，記在 `{os.path.basename(miss_path(market))}`）"
         f"　⇒ ⭐ 對**問得到**的那 {reach:,} 檔而言是 **{rp}%**"
         "　⚠ 而「問到放棄」⛔ 不等於「這檔沒有官方統計」"
         "——那句失敗訊息（`很抱歉，沒有符合條件的資料!`）講不出它是哪一種"),
        # ⛔ 排掉的要講出來：「排掉了」與「沒有這種股票」**不是同一件事**
        # ⭐ 而**兩種被排掉的意義完全不同**，⛔ 不可以並排寫成一行
        ("⚠ 這一趟不涵蓋的（⛔ 分兩種，意義不同）",
         f"**{other} {n_other:,} 檔**　⇒ ⭐ 那是**另一趟**在做"
         f"（`--market {other}`），⛔ **不是缺口**"
         f"　｜**emerging {n_esb:,} 檔**　⇒ ⛔ 興櫃**兩支端點都不涵蓋**，"
         "這一條**還開著**"),
        ("⭐ 上櫃那一半的現況（2026-09-16）",
         "✅ **年**：`statistics/yearlyStock?code=<代號>` 一發回 12 年，"
         "已接上（`--market tpex`）"
         "　⇒ ⭐ 只有**價**那五格進共用判準表（收盤平均價／盤中最高最低＋日期，"
         "實測 6488 兩年跟我方日檔**逐位相同**）；"
         "量那四欄原樣另存（張／仟元／仟筆），⛔ 因為它們是另一種口徑"
         "（＋4.8%／＋5.0%／**＋156%**）"
         "　⇒ ⭐ **月**那一半端點也解了（probe 123）："
         "`statistics/monthlyStock?code=<代號>&date=<**西元年**>`"
         "（⛔ 只有年；七種格式只有這一種中，⚠ 我送西元它回民國）"
         "　⇒ ✅ **已接**（2026-09-16，回測線 0841 §四 4. 點名要）："
         "自己一份檔 `official_monthly_tpex.csv`，⛔ 不併進上市那張"
         "（上市月表的 high／low 是**盤中**、上櫃是**收市**，"
         "avg 一個加權一個簡單平均，單位一個股一個仟股 ⇒ 併了 ＝ **三道**靜默接縫）"
         "　⇒ ⚠ 而它一發只回**一年** ⇒ 工作單位是 (代號, 年)、母體 972×12 格，"
         "跑法是 `--months-years`（`feeds.yml` 的 `official-months`）"
         "　⇒ ⛔ 而**興櫃**的年表與月表這一格**還開著**：兩支端點都不涵蓋它"
         "　⇒ ⚠ 而線索一直在我方自己的 `data/meta/_site_inventory.txt` 裡"
         "（3.5④「自己家查過沒有」）"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=150)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--force", action="store_true")
    # ⛔ **必填語意、但有預設值是刻意的**：`twse` 是這一支原本唯一做的事，
    #   ⚠ 而它跟 `lowwater.direction` 那條不同——這裡兩種**沒有相反的語意**，
    #   只是兩個不同的端點與母體 ⇒ 預設值不會讓人「照抄錯的語意」。
    ap.add_argument("--market", choices=("twse", "tpex"), default="twse")
    # ⭐⭐ 月表的年份掃描：工作單位是 **(代號, 年)**，⛔ 不是代號
    #   ⚠ 空字串 ＝「不跑這一段」，`"all"` ＝ 全部年份，`"104-109"` ＝ 指定區間。
    #   ⛔ 它跟 `--market` **不是**兩種相反的語意（那條要必填、無預設值）——
    #     這裡是「要不要多做一件事」⇒ 預設不做是安全的那一邊。
    ap.add_argument("--months-years", default="",
                    help="月表年份掃描：'all'／'104-115'／'109'；空 ＝ 不跑")
    a = ap.parse_args()
    B.SLEEP = a.sleep

    if a.months_years:
        rl = runlog.Run(f"official_stats:months:{a.market}")
        return run_sweep(a, rl, datetime.now(TPE).strftime("%Y%m%d"))

    rl = runlog.Run("official_stats"
                    + ("" if a.market == "twse" else f":{a.market}"))
    rl.info("這一趟的市場", f"**{a.market}**"
            + ("｜端點 `afterTrading/FMNPTK`＋`FMSRFK`（逐年＋逐月）"
               if a.market == "twse" else
               "｜端點 `statistics/yearlyStock`（⭐ 一發回全部 12 年）"
               "　⇒ ⛔ 只有**價**那五格進共用判準表，量那四欄原樣另存"))
    today = datetime.now(TPE).strftime("%Y%m%d")
    done = set()
    _dp = done_path(a.market)
    if os.path.exists(_dp) and not a.force:
        with io.open(_dp, encoding="utf-8") as f:
            f.readline()
            done = {ln.split(",")[0].strip() for ln in f if ln.strip()}
    pool = codes(covered=(a.market,))
    # ⭐ 三堆只在**這裡切一次**（四點五）：⛔ 不要在別處再算一次 `c not in done`。
    miss = load_miss(miss_path(a.market)) if not a.force else {}
    # ⛔ 台帳被污染過就要**講出來**（⚠ 丟掉而不說 ＝ 沒被污染，看起來一樣）
    _bad = bad_rows(miss_path(a.market))
    if _bad:
        rl.info("⛔ miss 台帳裡有**不是代號**的列（已跳過，下次寫入時會消失）",
                f"{len(_bad)} 列：{_bad[:5]}"
                "　⇒ 病根是舊版把整頁 HTML 寫進 `why` 欄而只換了逗號沒換換行"
                "（第二點④：TWSE 被 CDN 擋時回 HTTP 428 ＋ HTML）"
                "　⇒ 寫入端已改走 `twparse.csv_cell`")
    todo, fresh, give_up = split_todo(pool, done, miss, a.limit)
    ex = excluded(covered=(a.market,))
    for label, value in progress_lines(pool, done, todo, ex, give_up,
                                       market=a.market):
        rl.info(label, value)
    if not todo:
        rl.info("狀態", "✓ **問得到的全部問完了**"
                        f"（⛔ 不等於「全市場都有官方統計」；⚠ 另有 {len(give_up):,} 檔"
                        "連續答不出來而放棄，見 `_official_stats_miss.csv`）")

    Y = _load(yearly_path(a.market), Y_HEADER, y_key)
    M = _load(monthly_path(a.market), M_HEADER, m_key)
    T = _load(tpex_yearly_path(), TY_HEADER, y_key) if a.market == "tpex" else {}
    n0y, n0m = len(Y), len(M)
    ok = []
    flushed = 0
    fail = []
    for i, sid in enumerate(todo, 1):
        if a.market == "tpex":
            # ⭐ 上櫃：價那五格填進共用表（`Y_HEADER` 其餘欄留空，⛔ 不是 0），
            #   量那四欄原樣進 `T`。⚠ 兩者的 key 都是 (代號, 民國年)。
            prs, vrs, err = fetch_one_tpex(sid)
            ys = [(r[0], r[1], "", "", "", r[2], r[3], r[4], r[5], r[6], today)
                  for r in prs]
            ms = []
            for r in vrs:
                T[(r[0], r[1])] = list(r) + [today]
        else:
            ys, ms, err = fetch_one(sid, today)
        if err:
            fail.append((sid, err))
            print(f"  [{i}/{len(todo)}] {sid} ✗ {err}", flush=True)
            continue
        for r in ys:
            Y[y_key(r)] = r
        for r in ms:
            M[m_key(r)] = r
        ok.append(sid)
        print(f"  [{i}/{len(todo)}] {sid} ✓ 年 {len(ys)}／月 {len(ms)}", flush=True)
        # ⭐ 每 FLUSH_EVERY 檔落地一次 ⇒ 被砍最多賠 FLUSH_EVERY 檔，⛔ 不是整批 400
        if len(ok) - flushed >= FLUSH_EVERY:
            land(Y, M, ok[flushed:], today, market=a.market, T=T)
            flushed = len(ok)
            print(f"  ⭐ 期中落地：已完成 {flushed}／{len(todo)}"
                  "（⇒ 這一趟就算被砍，前面這些不會白跑）", flush=True)
        if a.sleep:
            time.sleep(a.sleep)

    # ⛔ 一筆都沒抓到、而且檔案本來就不存在 ⇒ **不要建立空檔**。
    #   2026-09-09 本機 smoke test（403 全失敗）就留下兩個只有表頭、零列的殘骸——
    #   **一個存在但空的判準檔，讀起來像是「有這份判準」**，
    #   而那正是今晚一路在抓的形狀（孤兒檔、恆真的 0 筆、留著不標的停更檔）。
    #   ⇒ 有舊內容就照常寫回（不能因為本趟失敗就讓舊的消失）；
    #     完全沒有內容就不落地。
    # ⭐ 最後一次落地走**同一個函式**（⛔ 不是另寫一段）
    land(Y, M, ok[flushed:], today, market=a.market, T=T)
    # ⭐⭐ 失敗也要落地，⛔ 否則下一趟還會再問同一批（本節開頭那 69 檔）。
    #   ⚠ `alive` ＝ 這一趟有沒有任何一檔成功：端點整個掛掉時**一個字都不寫**。
    #   ⭐⭐ 而「本趟全失敗」有**兩種**（見 `controls()`），⛔ 它們長得一模一樣
    #     ⇒ 拿**對照組**（還在母體裡而且以前答得出來的幾檔）當**外部錨點**問一次。
    #     ⚠ 只在需要判別的時候問（`fail and not ok`）⇒ 正常那幾趟一發都不多打。
    alive = bool(ok)
    if fail and not ok:
        probed, ctrl_why = endpoint_alive(controls(pool, done), today)
        rl.info("⭐ 全失敗 ⇒ 拿**對照組**問一次（⛔ 不是在兩種成因之間猜）", ctrl_why)
        if probed is True:
            alive = True
    n_miss = bump_miss(fail, today, path=miss_path(a.market), alive=alive)
    if fail and not ok and not alive:
        rl.info("⛔ 本趟全失敗、**而且對照組也答不出來** ⇒ 不記 miss",
                f"{len(fail):,} 檔全部失敗 ⇒ 判定是**端點側**的問題，"
                "⚠ 而不是這些檔沒有資料　⇒ ⭐ 一個字都不寫進 miss 台帳"
                "（⛔ 寫了的話，掛掉兩趟就把全庫判死，而畫面上完全正常）")
    elif n_miss:
        rl.info("本趟記進 miss 台帳",
                f"{n_miss:,} 檔　⇒ 連續 {MISS_TRIES} 趟才會被跳過，"
                "⭐ 而它們仍然留在母體裡（⛔ 不是從報表上消失）")
    if not Y and not M:
        rl.info("處置", "⛔ 一筆都沒抓到且檔案不存在 ⇒ **不建立空檔**"
                        "（空的判準檔讀起來像是有這份判準）")
    rl.info("期中落地", f"每 {FLUSH_EVERY} 檔寫一次"
                        f"｜本趟落地 {len(ok):,} 檔"
                        "　⇒ ⭐ 被砍最多賠 {} 檔，⛔ 不是整批".format(FLUSH_EVERY))

    rl.info("年度表", f"{yearly_path(a.market).split('data/')[-1]}"
                      f"｜{len(Y):,} 列（本趟 +{len(Y)-n0y}）")
    rl.info("月表", f"{monthly_path(a.market).split('data/')[-1]}"
                    f"｜{len(M):,} 列（本趟 +{len(M)-n0m}）")
    if a.market == "tpex":
        rl.info("⭐ 上櫃的**量**那四欄（原樣，保留官方單位：張／仟元／仟筆）",
                f"{tpex_yearly_path().split('data/')[-1]}｜{len(T):,} 列"
                "　⇒ ⛔ 它們跟上市那三欄**不是同一個口徑**，不可以合著算")
    rl.info("本趟", f"成功 {len(ok)}／失敗 {len(fail)}"
            + (f"｜失敗例：{fail[:3]}" if fail else ""))
    # ⛔ 只增不減：這兩份是外部判準，寫短了等於判準消失。
    rl.check("兩份判準檔都只增不減", len(Y) >= n0y and len(M) >= n0m,
             f"年 {n0y}→{len(Y)}｜月 {n0m}→{len(M)}")
    # ⚠ 全失敗**而且對照組也答不出來**＝被擋或參數壞了，要當場紅；
    #   零星失敗（下市檔沒有資料）、以及「剩下的剛好全都答不出來」都是正常的。
    # ⭐⭐ 放行之後還有誰在守（CLAUDE.md 四點五⑥③，⛔ 這段要留在原始碼裡）：
    #   ① **對照組自己**——它答不出來的那一趟立刻 ✗，而它是每趟現場重算的
    #   ② 那 104 檔照常累加進 miss 台帳 ⇒ 連續 MISS_TRIES 趟之後轉進「問到放棄」，
    #      ⭐ 而那一欄**照常印在報表上**（⛔ 不是從報表消失）⇒ 收斂得到、也看得見
    #   ③ 「兩份判準檔只增不減」那道沒有動
    # ⛔⛔ 說明文字要講**實際發生的那一種**。
    #   ⚠ 2026-09-16 run 158 實測：這一格**過了**（對照組 3／3 答得出來），
    #   而說明照樣印「且對照組也答不出來」——⭐ 一個通過的檢查，說明寫著相反的話。
    #   ⇒ 它比沒有說明更糟：讀的人會照那句去查一個根本沒發生的故障。
    rl.check("不是整批失敗（全失敗**而且對照組也答不出來**＝被擋或參數壞了）",
             not todo or bool(ok) or alive,
             batch_fail_note(len(todo), len(ok), alive))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
