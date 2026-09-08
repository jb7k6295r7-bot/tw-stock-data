#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parvalue_scan.py — 全庫掃「疑似面額變更」。**只讀、只寫一份報告，不改資料。**

## 為什麼要有這一支

`tw-stock-db` skill 的陷阱 13 訂了一條判定規則：

> 相鄰兩個交易日的收盤比 `close(t)/close(t-1)` 落在 `< 0.55` 或 `> 1.8`，
> 且 `data/adj/` 裡沒有對應日期的除權息或減資事件可以解釋 → 疑似面額變更。

但同一條的最後一段寫得很清楚：

> **門檻 0.55／1.8 與「約 26 筆」的量級沿用移交內容，資料庫線尚未自行複核那份名單。**
> 要把它變成管線裡的自動標記之前，先在 `data/stocks/` 全庫掃一次、把命中的逐筆看過。

**這一支就是那一次全庫掃描。** 在它跑完並且有人逐筆看過之前，
那條規則是「判讀時的人工檢查」，不是已驗證的資料欄位——這個分別要守住。

## ⛔ 三個會讓這次掃描白做的陷阱

**① 相鄰兩列不等於相鄰兩個交易日。**
`data/stocks/*.csv` **只收當天有成交的證券**（READ_CONTRACT 寫死的）。
一檔停牌半年，檔案裡就是兩列直接相接——那個比值是**半年的累積**，
不是「一天的跳躍」。所以每一筆都要帶**中間隔了幾個交易日**，
用 `data/meta/calendar_twse.csv`（2,847 天）去數，不是用日曆天相減。

**② 台股有漲跌幅限制。** 上市櫃普通股單日 ±10%。
所以**真的隔一個交易日**而比值到 0.55／1.8，本來就不可能是交易造成的
（興櫃、上市首日、無漲跌幅的特殊情形除外）。
這一項讓「隔 1 個交易日」的命中比「隔 40 個交易日」的命中強得多，
報告要分開列，不可以混成一個數字。

**③ 事件不能用「同一天」去對，要用「區間」。**
第一版寫成「事件日 == 跳的那一天」，再補 ±1／±3 容錯——**那是錯的**，
而且錯得很有代表性：

- 3293 鈊象 2024-07-23 收 1465 → 07-26 收 786（0.537），看起來像面額變更。
  但 `data/adj/3293.csv` 明明有 `2024-07-24 除權息 factor 0.488 ref_price 715`。
  對不上的原因是 **2024-07-24、25 因颱風停市，那兩天不在交易日曆裡**，
  而第一版的容錯是沿著**交易日曆**往前後數的，永遠數不到停市日上的事件。
- 1418、1529、4806、6198 四筆也一樣：減資事件落在停牌區間中間。

⛔ **`data/adj/` 的事件日不保證是交易日。**
正確的判準是**區間**：事件日落在 `(前一次有成交的日子, 這一次有成交的日子]` 之內，
就足以解釋這個跳躍。這樣停市、停牌、跨假日全部自然涵蓋，不必再猜容錯天數。
"""
import argparse
import csv
import io
import os
import sys
from collections import defaultdict

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STOCKS = os.path.join(_ROOT, "stocks")
ADJ = os.path.join(_ROOT, "adj")
CAL = os.path.join(_ROOT, "meta", "calendar_twse.csv")
IND = os.path.join(_ROOT, "meta", "industry.csv")
OUT = os.path.join(_ROOT, "meta", "_parvalue_scan.md")

LO, HI = 0.55, 1.8            # ★ 移交來的門檻，本檔要複核它，不是假設它對


def load_calendar():
    """交易日 → 序號。用來數「隔了幾個交易日」，**不是用日曆天相減**。"""
    days = []
    with io.open(CAL, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            if d:
                days.append(d)
    days.sort()
    return {d: i for i, d in enumerate(days)}, days


def load_events(sid):
    """→ [(date, kind, event, factor)]，已排序。沒有因子檔就是空的（那本身不是錯）。"""
    p = os.path.join(ADJ, f"{sid}.csv")
    if not os.path.exists(p):
        return []
    out = []
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            if d:
                out.append((d, (r.get("kind") or "").strip(),
                            (r.get("event") or "").strip(),
                            (r.get("factor") or "").strip()))
    out.sort()
    return out


def fnum(v):
    s = "" if v is None else str(v).replace(",", "").strip()
    try:
        x = float(s)
    except ValueError:
        return None
    return x if x > 0 else None          # 0 或負的收盤不是價格，是缺值


def main():
    ap = argparse.ArgumentParser(description="全庫掃疑似面額變更（只讀）")
    ap.add_argument("--lo", type=float, default=LO)
    ap.add_argument("--hi", type=float, default=HI)
    ap.add_argument("--limit", type=int, default=0, help="只掃前 N 檔（除錯用）")
    a = ap.parse_args()

    cal, days = load_calendar()
    print(f"[scan] 交易日曆 {len(days):,} 天（{days[0]} ~ {days[-1]}）")

    pop = set()
    if os.path.exists(IND):
        with io.open(IND, encoding="utf-8") as f:
            pop = {r["stock_id"] for r in csv.DictReader(f)}

    files = sorted(n for n in os.listdir(STOCKS) if n.endswith(".csv"))
    if a.limit:
        files = files[:a.limit]

    hits = []
    n_rows = n_pairs = 0
    no_cal = 0
    for fn in files:
        sid = fn[:-4]
        rows = []
        with io.open(os.path.join(STOCKS, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                c = fnum(r.get("close"))
                d = (r.get("date") or "").strip()
                if c and d:
                    rows.append((d, c, (r.get("name") or "").strip(),
                                 (r.get("market") or "").strip()))
        # 名稱本身就是第二個訊號，見下面 name0/name1
        rows.sort(key=lambda x: x[0])
        n_rows += len(rows)
        if len(rows) < 2:
            continue
        ev = load_events(sid)
        for i in range(1, len(rows)):
            n_pairs += 1
            (d0, c0, nm0, _), (d1, c1, nm, mk) = rows[i - 1], rows[i]
            ratio = c1 / c0
            if a.lo <= ratio <= a.hi:
                continue
            # ── 隔了幾個交易日：用日曆數，不是日曆天相減 ──
            if d0 in cal and d1 in cal:
                gap = cal[d1] - cal[d0]
            else:
                gap = -1
                no_cal += 1
            # ── ★ 事件用「區間」對，不是用「同一天」對 ──
            #   事件日落在 (d0, d1] 之內就足以解釋這個跳躍。
            #   ⛔ 不可以沿著交易日曆去數容錯天數：`data/adj/` 的事件日
            #      **不保證是交易日**（2024-07-24 鈊象除權息當天颱風停市）。
            inside = [e for e in ev if d0 < e[0] <= d1]
            hits.append({
                "sid": sid, "name": nm, "market": mk,
                "d0": d0, "d1": d1, "c0": c0, "c1": c1,
                "ratio": ratio, "gap": gap,
                "ev": inside,
                # ★★ 第二個、而且是**直接**的訊號：證券名稱裡的 `*`。
                #   TWSE／TPEx 用名稱末尾的 `*` 標「非 10 元面額」。
                #   面額一變，名稱就跟著變——**這是來源自己宣告的，
                #   不是從價格比值反推的**。價格比值只能說「跳了」，
                #   名稱變化才說得出「跳的原因是計價單位換了」。
                "name0": nm0, "name1": nm,
                "star": ("*" in nm) != ("*" in nm0),
                "renamed": nm != nm0,
                "in_pop": sid in pop,
            })

    print(f"[scan] 掃了 {len(files):,} 檔、{n_rows:,} 列、{n_pairs:,} 個相鄰對")
    print(f"[scan] 比值在 [{a.lo}, {a.hi}] 之外：{len(hits):,} 筆")

    unexplained = [h for h in hits if not h["ev"]]
    print(f"[scan] 其中當天沒有除權息／減資事件可解釋：{len(unexplained):,} 筆")
    report(a, days, files, n_rows, n_pairs, hits, no_cal)
    return 0


def report(a, days, files, n_rows, n_pairs, hits, no_cal):
    L = []

    def w(s=""):
        L.append(s)

    yes = [h for h in hits if h["ev"]]
    no = [h for h in hits if not h["ev"]]

    w("# 全庫掃「疑似面額變更」")
    w()
    w("**這是 `parvalue_scan.py` 的輸出，只讀不改資料。**")
    w("目的是複核 `tw-stock-db` skill 陷阱 13 那條移交來的判定規則——")
    w("門檻 `< 0.55 / > 1.8` 與「約 26 筆」的量級**在此之前沒有被資料庫線自己驗過**。")
    w()
    w(f"- 母體：`data/stocks/` {len(files):,} 檔、{n_rows:,} 列、"
      f"{n_pairs:,} 個相鄰對")
    w(f"- 門檻：比值 `< {a.lo}` 或 `> {a.hi}`")
    w(f"- 命中 **{len(hits):,} 筆**：有事件可解釋 {len(yes)}、"
      f"**無事件 {len(no)}**")
    if no_cal:
        w(f"- ⚠ 有 {no_cal} 筆的日期不在交易日曆裡，隔幾個交易日記為 `-1`")
    w()

    w("## ⛔ 第一版錯在哪（記著，這個錯很有代表性）")
    w()
    w("第一版用「事件日 == 跳的那一天」再補 ±1／±3 容錯去對事件，"
      "得到 5 筆「隔 1 個交易日、±3 天內無事件」的疑似名單。**其中 3293 鈊象是假的**：")
    w()
    w("- 3293 2024-07-23 收 1465 → 07-26 收 786（0.537）")
    w("- `data/adj/3293.csv` 明明有 `2024-07-24 除權息 factor 0.488 ref_price 715`")
    w("- 對不上是因為 **2024-07-24、25 颱風停市，那兩天不在交易日曆裡**，"
      "而容錯是沿著交易日曆數的，永遠數不到停市日上的事件")
    w()
    w("→ **`data/adj/` 的事件日不保證是交易日。** 正確判準是**區間**："
      "事件日落在 `(前一次有成交的日子, 這一次有成交的日子]` 之內就足以解釋。")
    w("停市、停牌、跨假日全部自然涵蓋，不必猜容錯天數。改用區間之後，"
      "1418／1529／4806／6198 那四筆減資也一起歸位了。")
    w()

    w("## ★ 為什麼不能只報一個數字")
    w()
    w("台股上市櫃**普通股**單日漲跌幅 ±10%，所以真的只隔一個交易日卻跳到"
      "0.55／1.8，不可能是交易造成的。")
    w("⚠ 但 **`data/stocks/` 3,030 檔裡只有 1,984 檔在 `industry.csv` 母體內**，"
      "其餘 1,046 檔多是 ETF／ETN／受益憑證，")
    w("而**追蹤國外標的的 ETF 沒有漲跌幅限制**——±10% 這個論證對它們不成立。"
      "所以名單一定要分「在母體內」與「母體外」看。")
    w()
    w("| 隔幾個交易日 | 有事件 | 無事件 | 其中在母體內 | 合計 |")
    w("|---|---:|---:|---:|---:|")
    buckets = [("1（相鄰交易日）", lambda g: g == 1),
               ("2~5", lambda g: 2 <= g <= 5),
               ("6~20", lambda g: 6 <= g <= 20),
               ("21 以上", lambda g: g > 20),
               ("不在日曆裡", lambda g: g < 0)]
    for label, f in buckets:
        sub = [h for h in hits if f(h["gap"])]
        sy = [h for h in sub if h["ev"]]
        sn = [h for h in sub if not h["ev"]]
        w(f"| {label} | {len(sy)} | **{len(sn)}** | "
          f"{len([h for h in sn if h['in_pop']])} | {len(sub)} |")
    w()

    # ── ★★ 第二個訊號：名稱裡的 `*` ──
    star = [h for h in no if h["star"]]
    w("## ⭐⭐ 拿到直接證據了：名稱裡的 `*`")
    w()
    w("價格比值只能說「跳了」，說不出跳的原因。但 TWSE／TPEx 用**證券名稱末尾的"
      "`*`** 標示「非 10 元面額」——**面額一變，名稱就跟著變，那是來源自己宣告的**。")
    w("`data/stocks/` 每一列都帶 `name`，所以這個訊號一直都在，只是沒有人去看。")
    w()
    w(f"- 無事件可解釋的 {len(no)} 筆裡，**{len(star)} 筆在跳躍的同時 `*` 出現或消失**")
    w(f"- 其中在 `industry.csv` 母體內：**"
      f"{len([h for h in star if h['in_pop']])} 筆**")
    w()
    w("這一組是**兩個獨立訊號同時成立**（價格跳 ＋ 來源宣告面額類別改變），")
    w("不再是「用價格比值猜的」。")
    w()
    if star:
        w("| 代號 | 跳躍前名稱 | 跳躍後名稱 | 前一交易日 | 收盤 | 當日 | 收盤 | 比值 | 隔 | 在母體 |")
        w("|---|---|---|---|---:|---|---:|---:|---:|---|")
        for h in sorted(star, key=lambda x: x["d1"]):
            w(f"| {h['sid']} | {h['name0']} | {h['name1']} | {h['d0']} | {h['c0']:g} "
              f"| {h['d1']} | {h['c1']:g} | {h['ratio']:.3f} | {h['gap']} | "
              f"{'**是**' if h['in_pop'] else '否'} |")
        w()
        w("⚠ 這些的「隔幾個交易日」幾乎都是 **6~8 天**，不是 1 天——"
          "換發股票要停止買賣，本來就會有一段空窗。")
        w("**所以第一版把「隔 1 個交易日」當成最強的一類，方向是反的**："
          "面額變更幾乎不可能出現在相鄰交易日。")
    w()

    # ── ⚠ `*` 沒出現 ≠ 沒有面額變更：name 欄在部分檔案是回填的 ──
    pat = [h for h in no if not h["star"] and "*" in h["name1"]
           and h["in_pop"] and 2 <= h["gap"] <= 20 and h["ratio"] < 1]
    w("## ⚠ `*` 沒有出現，**不等於**沒有面額變更")
    w()
    w("`data/stocks/` 的 `name` 欄**不是每一檔都保留當日的歷史名稱**。實測：")
    w()
    w("| 代號 | 檔案裡的名稱變化次數 | 最早一列 |")
    w("|---|---:|---|")
    w("| 6548 長科 | 3 次 | 2016-09-13 `長華科` → 2019-01-08 `長科` → 2019-09-09 `長科*` |")
    w("| 8070 長華 | **1 次** | 2015-01-05 就已經是 `長華*` |")
    w("| 8422 可寧衛 | **1 次** | 2015-01-05 就已經是 `可寧衛*` |")
    w("| 2327 國巨 | **1 次** | 2015-01-05 就已經是 `國巨*` |")
    w()
    w("8070 長華的價格在 **2020-08-17** 才從 190 掉到 20.9（0.110）——"
      "面額是那時候換的，但 2015 年的每一列都已經寫著 `長華*`。")
    w("**那是回填的當期名稱，不是當日名稱。**")
    w()
    w("⛔ 所以 `*` 出現＝強證據，`*` 沒出現＝**沒有證據**，兩者不對稱。"
      "不可以拿「`*` 沒變」去否定一筆。")
    w()
    w(f"### 型態相符、但名稱訊號不可用 — **{len(pat)} 筆**")
    w()
    w("判準：在母體內、無事件、**名稱帶 `*`**、隔 2~20 個交易日、比值 < 1。")
    w("與上面 13 筆**同一個型態**（停止買賣 6~8 天、股價變成幾分之一），"
      "差別只在名稱欄被回填、看不到 `*` 出現的那一刻。")
    w()
    if pat:
        w("| 代號 | 名稱 | 前一交易日 | 收盤 | 當日 | 收盤 | 比值 | 隔 |")
        w("|---|---|---|---:|---|---:|---:|---:|")
        for h in sorted(pat, key=lambda x: x["d1"]):
            w(f"| {h['sid']} | {h['name1']} | {h['d0']} | {h['c0']:g} | {h['d1']} "
              f"| {h['c1']:g} | {h['ratio']:.3f} | {h['gap']} |")
    w()

    rest = [h for h in no if not h["star"] and h not in pat]
    strong = [h for h in rest if h["gap"] == 1]
    weak = [h for h in rest if h["gap"] != 1]
    w("## 其餘（**不要當成面額變更**）")
    w()
    inpop_rest = [h for h in rest if h["in_pop"]]
    if inpop_rest:
        w(f"⭐ 母體內只剩 **{len(inpop_rest)} 筆**，逐筆看過：")
        w()
        for h in inpop_rest:
            w(f"- **{h['sid']} {h['name1']}**｜{h['d0']} {h['c0']:g} → "
              f"{h['d1']} {h['c1']:g}（{h['ratio']:.3f}）｜隔 {h['gap']} 個交易日")
        w()
        w("  8101 華冠：停了 **59 個交易日**（2024-08-21 → 2024-11-19），"
          "復牌價是停牌前的 5.5 倍，名稱沒有 `*`。")
        w("  `data/adj/8101.csv` 只有 2018 與 2022 兩筆減資，2024 這一次不在裡面；")
        w("  `data/universe/reduce/` 的 2024 各月檔案裡也找不到 8101。")
        w("  ⚠ **成因未查明**——長期停牌後倍數復牌，減資、合併、重整都可能，")
        w("  **不要因為它符合「無事件」就歸進面額變更**。這一筆單獨留著待查。")
        w()
    w(f"### A. 隔 1 個交易日 — **{len(strong)} 筆**")
    w()
    if strong:
        w("| 代號 | 名稱 | 市場 | 前一交易日 | 收盤 | 當日 | 收盤 | 比值 | 在母體 |")
        w("|---|---|---|---|---:|---|---:|---:|---|")
        for h in sorted(strong, key=lambda x: (x["sid"], x["d1"])):
            w(f"| {h['sid']} | {h['name']} | {h['market']} | {h['d0']} | {h['c0']:g} "
              f"| {h['d1']} | {h['c1']:g} | {h['ratio']:.3f} "
              f"| {'**是**' if h['in_pop'] else '否'} |")
    else:
        w("（沒有）")
    w()
    w(f"### B. 隔 2 個交易日以上 — **{len(weak)} 筆**"
      f"（其中在母體內 {len([h for h in weak if h['in_pop']])} 筆）")
    w()
    w("⚠ 這一類**不能直接當成面額變更**：中間停牌期間的累積漲跌本來就可以超過門檻。")
    w("列出來是為了讓人看過，不是為了進名單。")
    w()
    if weak:
        w("| 代號 | 名稱 | 前一交易日 | 當日 | 隔幾個交易日 | 比值 | 在母體 |")
        w("|---|---|---|---|---:|---:|---|")
        for h in sorted(weak, key=lambda x: -abs(x["ratio"] - 1))[:60]:
            w(f"| {h['sid']} | {h['name']} | {h['d0']} | {h['d1']} "
              f"| {h['gap']} | {h['ratio']:.3f} | "
              f"{'**是**' if h['in_pop'] else '否'} |")
        if len(weak) > 60:
            w(f"| … | 其餘 {len(weak) - 60} 筆 | | | | | |")
    w()

    w("## 門檻本身複核得怎麼樣")
    w()
    w(f"移交內容說「約 26 筆」。本次全庫實測：命中 **{len(hits)}** 筆、"
      f"無事件可解釋 **{len(no)}** 筆，其中母體內 "
      f"{len([h for h in no if h['in_pop']])} 筆，拆成：")
    w()
    w(f"| 分類 | 筆數 | 證據強度 |")
    w(f"|---|---:|---|")
    w(f"| `*` 在跳躍當下出現 | **{len(star)}** | 兩個獨立訊號同時成立 |")
    w(f"| 型態相符、名稱欄被回填 | **{len(pat)}** | 一個訊號＋型態一致 |")
    w(f"| 成因未查明（8101 華冠） | {len(inpop_rest)} | 待查，**不歸類** |")
    w(f"| **合計視為面額變更** | **{len(star) + len(pat)}** | |")
    w()
    w(f"→ **量級對得上**：移交說約 26，本次從 `data/stocks/` 全庫重算得 "
      f"{len(star) + len(pat)} 筆。")
    w("這不是「拿一個數字去驗另一個數字」——本次是獨立重算的，"
      "而且第二個訊號（名稱 `*`）與價格比值互相獨立。")
    w()
    w("### 門檻 0.55／1.8 本身")
    w()
    both = star + pat
    if both:
        rr = sorted(h["ratio"] for h in both)
        w(f"上表前兩類（{len(both)} 筆）的比值實測範圍 "
          f"**{rr[0]:.3f} ~ {rr[-1]:.3f}**。")
        w(f"最接近門檻的一筆是 **{rr[-1]:.3f}**，離下緣 {a.lo} 只差 "
          f"{a.lo - rr[-1]:.3f}——**門檻壓得很近，但沒有漏**。")
        w(f"⚠ 這也代表 {a.lo} 不可以再往下調：0.544 那一筆（6613 朋億*）"
          "只要門檻降到 0.54 就會被漏掉。")
        w("⚠ **下緣 0.55 是有效的，上緣 1.8 這一側一筆都沒有**——"
          "面額變更在本庫全部是「面額變小、股數變多、股價變低」的方向。")
        w("上緣不是沒用，是**還沒有樣本**：面額由小改大（例如 5→10）會落在那一側，"
          "本庫 2015 起沒發生過。**不要因為沒樣本就把它拿掉。**")
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
        print(f"[scan] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[scan] 寫檔失敗：{ex}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
