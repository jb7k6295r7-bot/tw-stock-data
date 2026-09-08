#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adjust.py — 由**除權息與減資**事件算出**還原因子**。

## 為什麼存因子不存還原價

存還原後的價格，等於把 `data/stocks/` 的 0.55 GB 再複製一份，
而且**每多一次除權息就要把該檔整段歷史重寫一遍**（還原是往前回推的）。
存因子只有幾百 KB，且downstream 只要乘一下。
更重要的是：**公式改了不必重抓，重算即可。**

## 定義（後復權，back-adjustment）

- 單次事件因子 `f = 除權息參考價 ÷ 除權息前收盤價`
  - 純現金股利：`f < 1`
  - 純股票股利／分割：`f < 1`（參考價會除以配股倍數）
- 某日的累積因子 `F(d) = 所有除權息日 **嚴格大於** d 的事件因子連乘`
- **還原價 = 原始價 × F(d)**

### ★ 差一天就整段錯：因子適用「該列日期之前」，不含當日

除權息當日的收盤價**本身已經是除權後的價格**，再乘一次因子等於重複扣。
`cum_factor` 欄的意思是：**要把「這一列的日期之前」的價格還原，要乘這個數。**

查法（照抄，不要自己推）：

```python
# rows 由 data/adj/<code>.csv 讀進來，已按日期升冪
def factor_at(rows, d):
    for r in rows:                 # 找第一個「除權息日 > d」的事件
        if r["date"] > d:
            return float(r["cum_factor"])
    return 1.0                     # 最後一次事件之後 → 現價不動
```

worked example（3661，兩次除息 2025-08-01 f=0.9750、2026-09-03 f=0.9922）：

| 查詢日 | 命中哪一列 | F | 說明 |
|---|---|---|---|
| 2025-07-31 | 2025-08-01 | **0.96744** | 兩次都還沒發生 → 兩個因子連乘 |
| 2025-08-01 | 2026-09-03 | **0.99225** | 當日已除息，只需還原後面那一次 |
| 2026-09-03 | 無 | **1.0** | 最新，不動 |

**2025-08-01 那天用 0.96744 是錯的**——它會把已經扣過的股利再扣一次。

**最新價的 F = 1**，也就是**現價不動**。這是刻意的：
報告上寫的價位要跟看盤軟體對得起來，被還原過的現價會讓人對不上。
被調整的是**歷史**，所以長期報酬率才不會被除息吃掉。

## ★ 減資（2026-09-06 併入）

原本只還原除權息，**減資完全沒處理**——那是資料庫當時錯得最嚴重的一塊。
減資讓股數變少、每股價格跳上去，跳幅動輒 30～50%，甚至翻倍：

| 實例 | 停止買賣前收盤 | 恢復買賣參考價 | f | 減資原因 |
|---|---|---|---|---|
| 3536 誠創 2015-03-20 | 6.58 | 13.33 | **2.026** | 彌補虧損 |
| 3040 遠見 2015-01-23 | 31.90 | 41.28 | 1.294 | 退還股款 |
| 1563 巧新 2026-09-07 | 66.00 | 84.66 | 1.283 | 退還股款 |

沒有這一塊，跨過減資日的長期報酬率、均線、扣抵值全部是錯的。
事件來源 `data/universe/reduce/`（TWSE `reducation/TWTAUU`，2015 起有歷史）。

**因子的定義完全一樣**：`f = 恢復買賣參考價 ÷ 停止買賣前收盤價`，
適用於「該列日期之前」。差別只有三個，**每一個都會靜默出錯**：

1. **合理範圍不同。** 除權息是 `0.05 < f ≤ 1.5`；減資的 f 幾乎一定 > 1，
   減資九成的話接近 10。**沿用除權息的上限會把真事件整批丟掉**，
   而丟棄只印在 stderr，摘要上看起來就像「這檔沒有減資」。
2. **核對的比較對象不同。** 除權息的「前收盤」是**前一個交易日**的收盤；
   減資的「停止買賣前收盤價」是停牌前最後一個有成交的日子——中間隔了好幾天。
   拿日曆的前一交易日去比會整片假警報。
3. **同一天可能兩邊都有，只能算一次。** 官方公式寫明
   「退還股款：恢復買賣參考價＝（停止買賣前收盤價−**息值**−每股退還股款）／減資換股率」，
   **息值已經含在裡面**。同日的 `TWT49U` 那一列要丟掉，否則除息被扣兩次。

## 三件不做的事

1. **不還原成交量。** 配股會讓股數變多、量自然放大，
   但配息不會。要精準就得分辨權與息，而 TWT49U 的「權/息」欄
   在同時配股又配息時是混合的。**沒把握就不動**，量一律維持原始值。
2. **不推估缺漏的事件。** 沒有事件檔的日期就是沒有事件，
   不用「股價當天跳空所以應該有除息」去補——那是把結論當資料。
3. **上櫃目前不還原。** TWT49U 與 TWTAUU 都只涵蓋上市；上櫃的除權息在
   `otcexright`、減資在 TPEx `bulletin/revivt`，兩者的歷史來源都還沒驗到。
   **`_index.csv` 會標明每一檔的來源市場**，
   不可把「沒有因子」讀成「沒有除權息也沒有減資」。
"""

import argparse
import os
import sys

import runlog
from collections import defaultdict

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
UNI_DIR = os.path.join(_ROOT, "universe")
STOCK_DIR = os.path.join(_ROOT, "stocks")
META_DIR = os.path.join(_ROOT, "meta")
ADJ_DIR = os.path.join(_ROOT, "adj")

# （市場, 事件種類, 目錄）。**種類會決定因子的合理範圍與核對方式**，不只是標籤。
EVENT_DIRS = [("twse", "exright", os.path.join(UNI_DIR, "exright")),
              ("tpex", "exright", os.path.join(UNI_DIR, "otcexright")),
              ("twse", "reduce", os.path.join(UNI_DIR, "reduce")),
              # ★ 上櫃這兩個目錄的來源是 **FinMind，不是官方**（TPEx 沒有歷史）。
              #   憑據是拿上市那一半交叉驗證過：除權息 555/555、減資 24/24，
              #   不符 0.00%，且「只有我方有」= 0（沒漏事件）。
              #   `_index.csv` 的 market 欄會是 tpex——**契約裡要寫明來源不同**。
              ("tpex", "reduce", os.path.join(UNI_DIR, "otcreduce")),
              # ★ 2026-09-09 接上。**只有上市**——TWSE `change/TWTB8U`。
              #   上櫃的 14 筆面額變更還沒有來源，見下方 BOUNDS 旁的說明。
              ("twse", "parvalue", os.path.join(UNI_DIR, "parvalue")),
              # ★ ETF 分割／反分割（TWSE `split/TWTCAU`）。2026-09-09 接上。
              #   ⚠ 這一類**不在 `industry.csv` 母體裡**，但它們在 `data/stocks/`，
              #     所以照樣要還原——否則算 ETF 長期報酬會踩到同一種靜默錯誤。
              ("twse", "etfsplit", os.path.join(UNI_DIR, "etfsplit"))]

# 每種事件的因子合理範圍**必須分開**，用同一組會兩頭錯：
#   除權息：參考價幾乎一定 ≤ 前收盤，> 1 是罕見的現金增資折價案例（約 0.09%）。
#   減資　：參考價幾乎一定 > 前收盤（股數變少）。3536 誠創 2015-03-20 是 2.026，
#           減資九成的話接近 10。**沿用 1.5 的上限會把真事件整批丟掉。**
BOUNDS = {"exright": (0.05, 1.5), "reduce": (0.20, 12.0),
          # ★ 面額變更：因子 ＝ 恢復買賣參考價 ÷ 停止買賣前收盤，**官方直接給**，
          #   所以它是乾淨的 1/k（實測 19/190 ＝ 18.5/185 ＝ 0.10，面額 10→1）。
          #   ⚠ **方向兩邊都要留**：10→1 是 0.1、10→0.5 是 0.05；
          #     反過來 1→10 會是 10、0.5→10 會是 20。
          #     除權息那組 0.05~1.5 套上來會把「面額變大」那一半全丟掉。
          #   界線取 0.03 ~ 25：比理論範圍（0.05 ~ 20）寬一點點，
          #   留給罕見倍率，但仍然擋得住欄位錯位那種離譜值。
          "parvalue": (0.03, 25.0),
          # ★ ETF 分割／反分割：與面額變更同一個道理，**兩個方向都有**。
          #   實測價格比 0.040 ~ 7.049（00685L ÷25、00632R ×7）——
          #   那是含 5~6 天停止買賣期間漲跌的比值；官方 ref/pre 會更乾淨。
          #   界線取 0.02 ~ 30，比實測寬一點，仍擋得住欄位錯位那種離譜值。
          "etfsplit": (0.02, 30.0)}

# ── 面額變更：2026-09-09 已接上，但**只有上市那一半** ──
#
# 2026-09-08 查明缺口、09-09 於 Actions 驗到來源（TWSE `change/TWTB8U`，
# 四項判準全過、參數確定生效），已接成 `parvalue` feed 並列進 EVENT_DIRS。
#
# ⚠⚠ **上櫃還是沒有還原。** `parvalue_scan.py` 全庫掃到 24 筆，
#   其中 **14 筆是上櫃**（6548 長科 ×10 與 ×2.5、5314 世紀 ×20、5904 寶雅 ×10…），
#   TWTB8U 只涵蓋上市，TPEx 的對應端點**還沒找到**。
#   → 跨過那 14 筆的長期報酬、均線、扣抵值**現在仍然是錯的**。
#   名單在 `data/meta/_parvalue_scan.md`，判準在 `docs/READ_CONTRACT.md`。
#
# 以下是查明當時的紀錄，留著當理由：
#
# ⛔⛔ **變更股票面額原本完全沒有還原**（2026-09-08 查明）。
#   台股 2014 年起開放彈性面額，10 元改 5 元會讓股數加倍、股價腰斬——
#   `data/stocks/` 是未還原價，跨過那一天會看到約 **50% 的假跌**，
#   與 2026-09-06 之前的減資是同一種病。
#
#   來源是 TWSE `change/TWTB8U`（變更股票面額恢復買賣參考價）。
#   `reduce_probe.py` 2026-09-06 已辨識出它「是另一種公司行動、不要混進減資」——
#   **那句話寫對了，但只寫成註解，從來沒有人去抓它。**
#   `data/adj/` 實測只有 exright 與 reduce 兩種事件，面額變更一筆都沒有。
#
#   ⚠ 這個缺口原本是**看不見的**：下面對減資有「一筆都沒讀到就警告」，
#     對面額變更連警告都沒有，因為它根本不在 EVENT_DIRS 裡。
#     跨過面額變更日的長期報酬、均線、扣抵值現在全部是錯的，而且不會報錯。
#
#   → 端點的參數與欄位尚未驗證（`parvalue_probe.py` 排在每日探針裡）。
#     驗到之後才加 feed 與這裡的第三種 kind，**在那之前不要假裝它有被還原**。
DAILY_DIR = os.path.join(UNI_DIR, "daily")


def trading_days():
    """全市場交易日曆＝`data/universe/daily/` 的檔名集合。

    ★ 為什麼需要它：核對「除權息前收盤價」要拿**前一個交易日**的收盤來比。
      但冷門股在那一天可能**根本沒有成交**，序列裡就沒有那一列。
      沒有日曆時只能退而取「前一個有資料的日子」——那可能是一個半月前，
      於是價格當然對不上，**被報成「對不上」，其實是「無法核對」**。
      實測 2026-09-04：6 筆「不符」全部是這個原因，真正的不符是 0 筆。
      把兩者混在一起，真的錯誤就會被雜訊蓋掉。
    """
    if not os.path.isdir(DAILY_DIR):
        return []
    return sorted(n[:-4] for n in os.listdir(DAILY_DIR) if n.endswith(".csv"))

# ★ `event` 是 2026-09-06 新增的**最後一欄**（exright／reduce）。
#   加在最後是刻意的：用欄名定位的讀取端不受影響，
#   而要區分「這個因子是除息還是減資」的人查得到——兩者的意義完全不同。
ADJ_HEADER = ["date", "factor", "cum_factor", "pre_close", "ref_price",
              "kind", "event"]
IDX_HEADER = ["stock_id", "market", "events", "reduce_events",
              "date_min", "date_max", "cum_factor_first", "checked", "mismatch"]


def _f(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def read_events():
    """→ {code: [(date, factor, pre, ref, kind, market, src)]}，日期升冪。

    `src` 是 `exright` 或 `reduce`。**它決定因子的合理範圍與核對方式**，
    不是拿來裝飾的欄位。
    """
    ev = defaultdict(list)
    up = 0                      # 參考價高於前收盤（現金增資認股價 > 市價）的筆數
    n_src = defaultdict(int)
    for market, srck, d in EVENT_DIRS:
        if not os.path.isdir(d):
            continue
        lo, hi = BOUNDS[srck]
        for name in sorted(os.listdir(d)):
            if not name.endswith(".csv"):
                continue
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                head = fh.readline().rstrip("\n").split(",")
                # ★ 兩種來源的表頭不一樣：除權息有 `kind`／`value`，
                #   減資有 `reason` 而**沒有** `value`。用「找得到就用」而不是
                #   寫死索引——寫死的話減資檔會整批被判成欄位不符而跳過。
                ix = {k: (head.index(k) if k in head else None) for k in
                      ("date", "stock_id", "pre_close", "ref_price",
                       "kind", "value", "reason")}
                if any(ix[k] is None for k in
                       ("date", "stock_id", "pre_close", "ref_price")):
                    print(f"[adj] {name} 欄位不符，跳過：{head}", file=sys.stderr)
                    continue
                for ln in fh:
                    q = ln.rstrip("\n").split(",")

                    def g(k, q=q):
                        i = ix[k]
                        return q[i] if (i is not None and i < len(q)) else ""

                    pre, ref = _f(g("pre_close")), _f(g("ref_price"))
                    code = g("stock_id").strip()
                    date = g("date").strip()
                    if not code or not date:
                        continue
                    if not pre or not ref or pre <= 0 or ref <= 0:
                        continue
                    f = ref / pre
                    val = _f(g("value"))

                    # ★★ 2026-09-04 修正：原本寫死 `f <= 1.0001`，理由是
                    #   「除權息不會讓參考價高於前收盤」——**那個假設是錯的**。
                    #   實例：3312 弘憶股 2016-04-14，前收 5.88 → 參考 5.89（f=1.0017），
                    #   `權值+息值` 是 **−0.018676**（負值）。
                    #   成因是**現金增資的認股價高於市價**，理論除權參考價因此上調。
                    #   少見但合法（240 個交易日抽樣的 1,144 筆裡有 1 筆，約 0.09%）。
                    #
                    #   ★ 2026-09-06：這整段方向性檢查**只適用除權息**。
                    #     減資的 f 本來就 > 1（股數變少），套上去會全部丟掉。
                    if not (lo < f <= hi):
                        print(f"[adj] 因子超出 {srck} 的合理範圍 ({lo}, {hi}]，丟棄："
                              f"{code} {date} 前收={pre} 參考={ref} f={f:.4f}",
                              file=sys.stderr)
                        continue
                    if srck == "exright" and f > 1.0001:
                        if val is not None and val < 0:
                            up += 1          # 合理的上調，計數但不吵
                        else:
                            print(f"[adj] 參考價高於前收盤但權值非負，方向矛盾，丟棄："
                                  f"{code} {date} 前收={pre} 參考={ref} "
                                  f"f={f:.4f} 權值+息值={val}", file=sys.stderr)
                            continue
                    kind = (g("kind") or g("reason")).strip()
                    ev[code].append((date, f, pre, ref, kind, market, srck))
                    n_src[srck] += 1

    # ★★ **同一（代號,日期）在減資表裡會重複出現。** 2026-09-06 實測：
    #   3536 於 2015-03-20 出現 **3 次**、5906 於 2016-07-14 出現 **2 次**，
    #   四個價格欄一模一樣，只有「除權參考價」欄有空有值。
    #   不去重的後果是**因子被連乘**：3536 的 f=2.0258 變成 2.0258³ = **8.32**，
    #   該檔 2015-03-20 之前的每一根 K 棒都被灌大四倍。
    #   而這**不會有任何錯誤訊息**——前收盤核對照樣 0 不符，因為每一列自己都是對的。
    #
    #   ⚠ 除權息表**沒有**這個問題（11,729 列實測重複 0 組），
    #     所以不可以把去重寫成「所有來源都只留一列」而不驗——
    #     若哪天 TWT49U 真的把權與息拆成兩列，兩列都是真的、都要乘。
    #     判準因此是**因子是否相同**，不是「同一天只能有一筆」。
    dupdrop = 0
    for c in list(ev):
        grp = defaultdict(list)
        for r in ev[c]:
            grp[(r[0], r[6])].append(r)          # (日期, 來源)
        if all(len(v) == 1 for v in grp.values()):
            continue
        keep = []
        for key in sorted(grp):
            v = grp[key]
            if len(v) == 1:
                keep.append(v[0])
                continue
            fs = {round(x[1], 9) for x in v}
            if len(fs) == 1:
                keep.append(v[0])                 # 純重複，收一列
                dupdrop += len(v) - 1
            else:
                # 因子不同＝同一天有兩個**不一樣**的事件，或資料矛盾。
                # 這在目前的資料裡是 0 件。真的發生就是要有人看，不可靜默決定。
                print(f"[adj] ★ 同一（代號,日期,來源）出現因子不同的多列，"
                      f"**已全部保留、請人工判斷**：{c} {key[0]} {key[1]} "
                      f"f={sorted(fs)}", file=sys.stderr)
                keep.extend(v)
        ev[c] = sorted(keep)
    if dupdrop:
        print(f"[adj] 同一事件的重複列丟棄 {dupdrop} 列（四個價格欄完全相同）。"
              f"**不丟的話因子會被連乘**")

    # ★ 同一天既有減資又有除權息 → **只能算一次**。
    #   官方公式：恢復買賣參考價＝（停止買賣前收盤價 − **息值** − 每股退還股款）／減資換股率。
    #   息值已經含在減資的參考價裡，兩邊都收就會把除息扣兩次。
    #   留減資那一列（它涵蓋兩者），丟同日的除權息列。
    dup = 0
    for c in ev:
        ev[c].sort()
        red_days = {r[0] for r in ev[c] if r[6] == "reduce"}
        if not red_days:
            continue
        keep = [r for r in ev[c] if not (r[6] == "exright" and r[0] in red_days)]
        if len(keep) != len(ev[c]):
            for r in ev[c]:
                if r[6] == "exright" and r[0] in red_days:
                    print(f"[adj] 同日既有減資又有除權息，丟除權息列（減資參考價已含息值）："
                          f"{c} {r[0]} f={r[1]:.4f}", file=sys.stderr)
            dup += len(ev[c]) - len(keep)
            ev[c] = keep
    if up:
        print(f"[adj] 其中 {up} 筆的參考價高於前收盤（權值為負＝現金增資認股價高於市價），"
              f"已照實收下，不是錯誤")
    print(f"[adj] 事件來源：除權息 {n_src['exright']:,} 筆、減資 {n_src['reduce']:,} 筆"
          + (f"；同日重疊丟棄 {dup} 筆除權息" if dup else ""))
    if not n_src["reduce"]:
        print("[adj] ⚠ **一筆減資事件都沒讀到**。若 data/universe/reduce/ 是空的，"
              "先跑 feeds.py --run --feed reduce。"
              "**不要把「沒有減資因子」讀成「這段期間沒有減資」。**", file=sys.stderr)
    return ev


def read_close(code):
    """→ {date: close}。用 `data/stocks/<code>.csv`。"""
    p = os.path.join(STOCK_DIR, f"{code}.csv")
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p, encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split(",")
        try:
            i_d = head.index("date"); i_c = head.index("close")
        except ValueError:
            return {}
        for ln in fh:
            q = ln.rstrip("\n").split(",")
            if len(q) > max(i_d, i_c):
                v = _f(q[i_c])
                if v is not None:
                    out[q[i_d]] = v
    return out


def build(code, rows, cal, verify=True):
    """→ (lines, checked, mismatch, skipped)。

    `cum_factor` 適用於**該列日期之前**（不含當日）的價格。
    事件當日的收盤已經是事件後的價，再乘一次就重複扣——
    查法見檔頭的 `factor_at()`，照抄不要自己推。
    最後一次事件之後沒有列，查不到就是 1.0，所以現價不動。
    """
    closes = read_close(code) if verify else {}
    have = sorted(closes) if closes else []

    checked = mismatch = skipped = 0
    if closes:
        for (d, f, pre, ref, kind, mk, srck) in rows:
            if srck == "reduce":
                # ★ 減資會**停止買賣數個交易日**，「停止買賣前收盤價」是停牌前
                #   最後一個有成交的日子——不是恢復買賣日的前一個交易日。
                #   拿日曆的前一交易日去比，比到的是停牌期間（該檔根本沒有那一列），
                #   於是全部變成「無法核對」；真要比就會比錯對象。
                #   正確做法：拿**該檔自己在 d 之前的最後一筆收盤**。
                prev = None
                for x in reversed(have):
                    if x < d:
                        prev = x
                        break
                if prev is None:
                    skipped += 1          # 事件早於我們的資料起點
                    continue
            else:
                # 除權息前收盤價應該等於**前一個交易日**的收盤。
                # ★ 「前一個交易日」由日曆決定，**不是「前一個有資料的日子」**。
                #   冷門股那天可能無成交，序列裡沒有那一列——那是無法核對，
                #   不是對不上。退而取更早的收盤去比，只會製造假警報。
                prev = None
                for x in reversed(cal):
                    if x < d:
                        prev = x
                        break
                if prev is None:
                    continue
                if prev not in closes:
                    skipped += 1          # 前一交易日該檔無成交 → 無法核對
                    continue
            checked += 1
            if abs(closes[prev] - pre) > max(0.02, pre * 0.005):
                mismatch += 1
                print(f"[adj] 前收盤對不上（{srck}）：{code} 事件日={d} "
                      f"官方前收={pre} 我方 {prev} 收盤={closes[prev]}", file=sys.stderr)

    # 累積因子由後往前連乘
    lines, cum = [], 1.0
    for (d, f, pre, ref, kind, mk, srck) in reversed(rows):
        cum *= f
        lines.append([d, f"{f:.8f}", f"{cum:.8f}", f"{pre:g}", f"{ref:g}",
                      kind, srck])
    lines.reverse()
    return lines, checked, mismatch, skipped


def main():
    ap = argparse.ArgumentParser(description="由除權息與減資事件算還原因子")
    ap.add_argument("--verify", action="store_true", default=True,
                    help="與 data/stocks 的前一交易日收盤交叉核對（預設開）")
    ap.add_argument("--no-verify", dest="verify", action="store_false")
    ap.add_argument("--codes", default="", help="只做這幾檔，逗號分隔（試跑用）")
    a = ap.parse_args()

    ev = read_events()
    if not ev:
        print("[adj] 找不到任何事件——先跑 feeds.py --run --feed exright"
              "，減資再跑一次 --feed reduce", file=sys.stderr)
        return 1
    os.makedirs(ADJ_DIR, exist_ok=True)
    cal = trading_days()

    # ★★ **尚未發生的事件不得產生還原因子。**（2026-09-06 補的閘門）
    #   還原因子的不變量是「最新價的 F = 1，現價不動」——報告上的價位要跟
    #   看盤軟體對得起來。若事件目錄裡混進一筆日期在**資料最後一天之後**的事件，
    #   `factor_at()` 會對今天的收盤回傳那個因子：1563 今天的 66.00 會被
    #   一個還沒發生的減資還原成 84.66，而且**沒有任何地方會報錯**。
    #
    #   抓取端已經不寫未來的列了（`announce_ahead`），這裡是第二道——
    #   閘門放在算因子的地方，才不會依賴「上游有沒有記得擋」。
    #   基準是**交易日曆的最後一天**（＝資料到哪一天），不是系統時鐘：
    #   容器的時鐘曾經差過一天，不能拿它當判準。
    pending = []
    if cal:
        last = cal[-1]
        for c in list(ev):
            fut = [r for r in ev[c] if r[0] > last]
            if not fut:
                continue
            pending.extend((c,) + r for r in fut)
            ev[c] = [r for r in ev[c] if r[0] <= last]
            if not ev[c]:
                del ev[c]
        if pending:
            print(f"[adj] **尚未發生的事件 {len(pending)} 筆，不採用**"
                  f"（資料最後一天 {last}）：")
            for p in sorted(pending)[:20]:
                print(f"        {p[1]}  {p[0]}  {p[5]}  f={p[2]:.4f}  {p[6]}")
            print("[adj] 它們會在事件日過後自然進來。"
                  "**不擋的話今天的收盤會被還沒發生的事件還原。**")
    else:
        print("[adj] ⚠ 沒有交易日曆，**無法擋掉尚未發生的事件**。"
              "若事件目錄裡有未來日期的列，今天的還原價會是錯的。", file=sys.stderr)

    want = {c.strip() for c in a.codes.split(",") if c.strip()}
    codes = sorted(c for c in ev if not want or c in want)
    if a.verify and not cal:
        print("[adj] 找不到 data/universe/daily/，無法取得交易日曆——"
              "**核對會退化成「拿前一個有資料的日子比」並產生假警報**，"
              "本次改為不核對。", file=sys.stderr)
    # ★ 全量重建。舊的檔數與事件數只有**現在**問得到，寫完就沒了。
    prev_codes, prev_events = None, None
    _pidx = os.path.join(ADJ_DIR, "_index.csv")
    if os.path.exists(_pidx) and not want:
        _pl = [l for l in open(_pidx, encoding="utf-8").read().splitlines()[1:] if l]
        prev_codes = len(_pl)
        prev_events = sum(int(l.split(",")[2]) for l in _pl if l.split(",")[2].isdigit())

    idx, tot_ev, tot_chk, tot_mis, tot_skip, no_price = [], 0, 0, 0, 0, 0
    for code in codes:
        rows = ev[code]
        lines, chk, mis, skp = build(code, rows, cal, a.verify and bool(cal))
        if not lines:
            continue
        with open(os.path.join(ADJ_DIR, f"{code}.csv"), "w", encoding="utf-8") as fh:
            fh.write(",".join(ADJ_HEADER) + "\n")
            for r in lines:
                fh.write(",".join(r) + "\n")
        if a.verify and chk == 0 and skp == 0:
            no_price += 1
        n_red = sum(1 for r in lines if r[6] == "reduce")
        idx.append([code, rows[0][5], str(len(lines)), str(n_red),
                    lines[0][0], lines[-1][0], lines[0][2], str(chk), str(mis)])
        tot_ev += len(lines); tot_chk += chk; tot_mis += mis; tot_skip += skp

    with open(os.path.join(ADJ_DIR, "_index.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(IDX_HEADER) + "\n")
        for r in idx:
            fh.write(",".join(r) + "\n")

    tot_red = sum(int(r[3]) for r in idx)
    print(f"[adj] {len(idx)} 檔、{tot_ev} 個事件"
          f"（其中減資 {tot_red} 個，分布在 {sum(1 for r in idx if r[3] != '0')} 檔）")
    if a.verify:
        rate = (tot_mis / tot_chk * 100) if tot_chk else 0.0
        print(f"[adj] 前收盤交叉核對：查了 {tot_chk} 個事件、對不上 {tot_mis} 個（{rate:.3f}%）")
        if tot_skip:
            print(f"[adj] 另有 {tot_skip} 個事件**無法核對**：前一交易日該檔無成交，"
                  f"序列裡沒有那一列。這不是不符，不要算進去。")
        if no_price:
            print(f"[adj] 另有 {no_price} 檔在 data/stocks 查無價格")
        # ★ 不設「自動通過」門檻。對不上就是要有人看，不是四捨五入掉。
        if tot_mis:
            print("[adj] ↑ 上面每一筆都印出來了，逐筆看過再決定要不要用", file=sys.stderr)

    # ★ 寫進 data/meta/_last_run.md 的「adjust」區塊。
    #   還原因子壞掉的兩種形狀都**不會讓程式失敗**：
    #     ① 混進尚未發生的事件 → 今天的收盤被還原，報價跟看盤軟體對不起來
    #     ② 沒有交易日曆 → 上面那道閘門整個關掉，而 log 只印一行 warning
    #   所以兩者都要變成 check，不是印一行了事。
    rl = runlog.Run("adjust")
    rl.info("還原因子", f"{len(idx)} 檔、{tot_ev} 個事件（其中減資 {tot_red} 個）")
    if a.verify:
        rl.info("前收盤交叉核對", f"查 {tot_chk} 筆、不符 {tot_mis} 筆"
                                  f"（另有 {tot_skip} 筆前一交易日無成交、無法核對）")
    else:
        rl.note("這一趟沒有核對（--no-verify）")
    rl.check("有交易日曆可用（未來事件閘門才有作用）", bool(cal),
             f"交易日曆 {len(cal)} 天，最後一天 {cal[-1]}" if cal
             else "**沒有 data/universe/daily/，閘門等於關閉**")
    # ⚠ **擋下未來事件是正常運作，不是異常。** 除權息本來就會提前公告，
    #   天天都可能擋到幾筆；把它做成 check 會讓這一頁長年掛 ✗、紅字失去意義
    #   （「防護誤殺跟防護失效一樣糟」）。要驗的是**閘門有沒有漏掉**——
    #   直接去看真的寫出去的因子裡，有沒有哪一筆的日期晚於資料最後一天。
    rl.info("擋下的未來事件", f"{len(pending)} 筆（正常，事件日到了會自然進來）")
    if cal and idx:
        _late = [r[0] for r in idx if r[5] > cal[-1]]
        rl.check("寫出去的因子沒有一筆晚於資料最後一天", not _late,
                 f"最晚 {max(r[5] for r in idx)}，資料最後一天 {cal[-1]}"
                 + (f"；越線 {len(_late)} 檔：{'、'.join(_late[:5])}" if _late else ""))
    if a.verify and tot_chk:
        rl.check("前收盤交叉核對 0 不符", tot_mis == 0, f"不符 {tot_mis} / 查 {tot_chk}")
    rl.check("檔數與事件數沒有變少", not (
        (prev_codes is not None and len(idx) < prev_codes) or
        (prev_events is not None and tot_ev < prev_events)),
        (f"{prev_codes} 檔／{prev_events} 事件 → {len(idx)} 檔／{tot_ev} 事件"
         if prev_codes is not None else "沒有可比的前一版（或這趟只做部分代號）"))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
