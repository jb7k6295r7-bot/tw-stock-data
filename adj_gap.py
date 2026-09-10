#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adj_gap.py — 找出**缺還原因子**的公司行動日，並逐筆歸因。

## 判準（⛔ 三個條件，缺一不可）——K線線 2026-09-09 21:55 給的

    ① change ∈ {'', '0.0', '0.00', '0'}
    ② close(t) ≠ close(t−1)          ← 把「真平盤」擋掉
    ③ 前一列必須是**緊鄰的前一個交易日**（對 calendar_twse.csv）
    ④ **前一列的 `market` 必須與本列相同**   ← K線線 2026-09-09 22:50 加的

### ⭐ ④ 是怎麼被找出來的——一句邏輯，不是靠掃更多資料

我算出 twse 83 筆、K線線算出 88 筆，我寫「差 8 筆多半是母體差異，不打算對齊」。
他們一句話駁掉：**「我的母體比你小（2,363 檔），卻數出比你多的筆數
⇒ 母體變小不可能讓筆數變多 ⇒ 差的不是母體，是判準。」**

⇒ 逐筆回看那 88 列的**前一列 `market`**：**16 筆是 `tpex → twse`，全部是轉上市首日。**
  官方在**不比價**時寫 `X0.00`，我方存 `0.0`；
  而轉上市首日的前一日在**另一個市場** ⇒ `change='0.0'` 成立、
  `close ≠ 前收` 也成立（換市場當然換價位）⇒ **三條件全中，但它不是除權息。**

⚠ ④ 的成本是零（`market` 就在 `data/stocks/` 的欄位裡），效果是**砍掉整整一類偽陽性**。

### ⭐ ① 為什麼要收兩種寫法：**兩市在除權息日寫 `change` 的方式不一樣**

    上櫃除權息日  change = ''     （空白）
    上市除權息日  change = '0.0'  （字串零）

⛔ 我原本的偵測器只收空白 ⇒ **它在上市抓到的已知正例是 0／9,597**，
  而我把那個 0 讀成「上市乾淨」，還對外報了兩次。
  ⭐ 教訓（K線線抽出來的，我照收）：
  **回報「某群 0 筆」時，必須附上「該判準在該群抓到的正例數」。**

⚠ 根源：TWSE 官方在那一格寫的是 `X0.00`。
  ⭐ 2026-09-10 拿到**官方出處**（`MI_INDEX` 的 `notes`，市場情報分析線 10:44 讀到的）：

      「漲跌(+/-)欄位符號說明:**+/-/X 表示漲/跌/不比價**。」
      「**"無比價"含前一日無收盤價、當日除權、除息、新上市、恢復交易者。**」

  ⇒ `X` ＝「**不比價**」，而不比價有 **5 種**成因：
      ① 前一日無收盤價 ② 當日除權 ③ 當日除息 ④ 新上市 ⑤ 恢復交易
  ⛔ 我方原本五處寫「`X` ＝ 無前一日收盤價可資比較」——**只涵蓋第 ① 種，是不完整的**。
  ⭐ ②③ 正是本支要抓的（除權息日官方寫 X ⇒ 我方存 `0.0`）；
     ④ 讓「轉上市首日不算缺陷」**有了官方依據**（不再只是我的推論）；
     ⚠ ⑤「恢復交易」是**新的偽陽性來源**，見下面條件 ⑤。
  ⚠ 範圍：以上是 **`MI_INDEX`／`STOCK_TIB` 的 `notes`（上市）**。
    上櫃 `otc` 的 `notes` 只有一條 ETF 外幣說明 ⇒ **上櫃那側仍然沒有出處**。
  而 `parse_twse()` 的 `sign = -1 if "-" in ...` 只看有沒有 `-` ⇒ `X` 被吃掉、存成 `0.0`。
  **旗標一直在我們手上。** 要不要存成 `change_flag` 欄是待決事項（會動到日檔表頭）。

### ⭐ ③ 那道閘是關鍵，沒有它整份結果是垃圾

薄量股在檔案裡有洞（`data/universe/daily/` 只收當天有成交的證券）。
拿「前一列」當「前一日」，遇到洞就會假跳。K線線實測：上市只有 ①② 是 7,824 筆，
加上 ③ 剩 **27 筆**——**偽陽性 289 倍差**。

## 歸因（⛔ 不是每一筆都是缺陷）

| 類別 | 是不是缺陷 |
|---|---|
| `轉上市首日` | ✅ 不是。官方 `notes` 明列「**新上市**」是不比價的成因之一 |
| `事件在休市日` | ✅ 不是。`adj` 有因子，只是日期掛在颱風休市日；`cum_factor` 是 `date <` 查找，邊界一樣 |
| `未歸因` | ⛔ **是**。這才是要補的 |

## ⛔ 這一支為什麼不設絕對門檻

歷史欠帳一開就是幾十筆，絕對門檻會**天天紅**，而天天紅的檢查會被學會忽略。
⇒ 依市場情報分析線 2026-09-09 的裁定：**用「有沒有變多」當判準**，
  那才回答得了「**今天有沒有變壞**」。
  ⚠ 並且**同時印總數與本輪變化量**——只印總數的話，
  「補了 100 筆」與「新增 100 筆」會互相抵銷成 0。
"""
import argparse
import csv
import io
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CAL = os.path.join(_ROOT, "meta", "calendar_twse.csv")
STOCKS = os.path.join(_ROOT, "stocks")
DAILY = os.path.join(_ROOT, "universe", "daily")
ADJ = os.path.join(_ROOT, "adj")
META = os.path.join(_ROOT, "meta", "stocks.csv")
OUT = os.path.join(_ROOT, "meta", "_adj_gap.csv")
# ⭐ 歷史最低值：斷言的基準。⛔ 用「上一趟」當基準會讓門檻停在補完後的低點。
LOW = os.path.join(_ROOT, "meta", "_adj_gap_low.txt")

ZERO = {"", "0.0", "0.00", "0", "0.000"}
HEADER = ["stock_id", "name", "date", "market_then", "market_now",
          "prev_close", "close", "pct", "why"]
SINCE = "2018-01-01"          # ⛔ 2015~2017 上櫃 change 欄大量空白，是另一件事


def _cal():
    with io.open(CAL, encoding="utf-8") as f:
        return sorted(r["date"] for r in csv.DictReader(f) if r.get("date"))


def _adj_dates():
    out = defaultdict(set)
    if not os.path.isdir(ADJ):
        return out
    for fn in os.listdir(ADJ):
        if not fn.endswith(".csv"):
            continue
        with io.open(os.path.join(ADJ, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = (r.get("date") or "").strip()
                if d:
                    out[fn[:-4]].add(d)
    return out


def scan(cal, adj, meta):
    """→ [(sid, date, prev_close, close)]，符合三條件且不在 adj 的普通股。"""
    cidx = {d: i for i, d in enumerate(cal)}
    out = []
    for fn in sorted(os.listdir(STOCKS)):
        if not fn.endswith(".csv") or fn.startswith("_"):
            continue
        sid = fn[:-4]
        if meta.get(sid, {}).get("kind") != "stock":
            continue
        rows = []
        with io.open(os.path.join(STOCKS, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append((r.get("date", ""), (r.get("change") or "").strip(),
                             r.get("close", ""), r.get("market", "")))
        rows.sort()
        for i in range(1, len(rows)):
            d, ch, cl, mkt = rows[i]
            pd, _, pcl, pmkt = rows[i - 1]
            if d < SINCE or ch not in ZERO:              # ①
                continue
            # ⑤ ⛔⛔ 前一列**沒有成交價**就不比。
            #   官方 `notes` 把「**恢復交易**」列為不比價（`X`）的五種成因之一
            #   ⇒ 停牌恢復當天也會是 `X` ⇒ 我方存 `0.0` ⇒ 條件 ① 會中。
            #   ⚠ 而它**不是**除權息 ⇒ 不擋掉就會多報。
            #
            #   ⭐ 為什麼以前沒事、以後會有事：
            #     甲之前——停牌那幾天日檔**整列不存在** ⇒ 條件 ③（前一列要是緊鄰
            #       的前一個交易日）自己就擋掉了。實測未歸因 0 筆落在恢復交易日。
            #     甲之後——那些列**補回來了**（`price_basis='無成交'`、`close` 空）
            #       ⇒ 條件 ③ 會過，改由這一條擋。
            #   ⛔ 這一條原本是 `except ValueError: continue` 的**副作用**——
            #     能擋，但沒有人知道它在擋這個。⇒ 寫成明示條件，並且測它。
            if not str(cl).strip() or not str(pcl).strip():
                continue
            try:
                c, p = float(cl), float(pcl)
            except ValueError:
                continue
            if c == p or p <= 0:                          # ②（＋前收 0 的興櫃跳過）
                continue
            if cidx.get(d, -1) - cidx.get(pd, -99) != 1:  # ③
                continue
            # ④ ⛔ 換市場的那一天，基準本來就不可比（官方寫 X0.00）——
            #   它不是除權息。這一條砍掉「轉上市首日」整整一類偽陽性。
            #   ⭐ 官方 `notes` 把「新上市」列為不比價的五種成因之一 ⇒ 有出處。
            if mkt and pmkt and mkt != pmkt:
                continue
            if d not in adj.get(sid, ()):
                out.append((sid, d, p, c))
    return out


def market_then(hits):
    """那一天日檔裡記的 market（⛔ 不是 stocks.csv 的現在狀態）。"""
    byday = defaultdict(set)
    for sid, d, _, _ in hits:
        byday[d].add(sid)
    out = {}
    for d, ss in byday.items():
        p = os.path.join(DAILY, d + ".csv")
        if not os.path.exists(p):
            continue
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["stock_id"] in ss:
                    out[(r["stock_id"], d)] = r.get("market", "")
    return out


def first_twse():
    """每檔第一次以 twse 出現的日期。用來認出『轉上市首日』。"""
    out = {}
    if not os.path.isdir(DAILY):
        return out
    for fn in sorted(os.listdir(DAILY)):
        if not fn.endswith(".csv"):
            continue
        d = fn[:-4]
        with io.open(os.path.join(DAILY, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("market") == "twse" and r["stock_id"] not in out:
                    out[r["stock_id"]] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", default=True)
    ap.parse_args()

    rl = runlog.Run("adj_gap")
    cal = _cal()
    calset = set(cal)
    meta = {}
    with io.open(META, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            meta[r["stock_id"]] = r
    adj = _adj_dates()

    hits = scan(cal, adj, meta)
    then = market_then(hits)
    ft = first_twse()

    # ⭐ 「事件掛在休市日」的判法：事件日**不是這一天**，而是落在
    #   「前一個交易日」與「這一天」之間的某個**非交易日**上。
    #   ⛔ 用 `d not in calset` 判是錯的——`d` 一定是交易日（它是日檔的日期）。
    #   實例：2024-07-26（凱米颱風後第一個交易日）有三檔中，
    #        而它們的 adj 事件掛在休市的 07-24／07-25。
    #   ⇒ 那不是缺漏：`cum_factor` 是 `date <` 查找，休市日沒有價格，邊界一樣。
    cpos = {d: i for i, d in enumerate(cal)}

    def _on_closed_day(sid, d):
        i = cpos.get(d)
        if i is None or i == 0:
            return False
        prev = cal[i - 1]
        return any(prev < x < d for x in adj.get(sid, ()))

    rows, why_n = [], defaultdict(int)
    for sid, d, p, c in sorted(hits):
        if ft.get(sid) == d:
            why = "轉上市首日"          # 官方 notes：「新上市」是不比價成因之一
        elif _on_closed_day(sid, d):
            why = "事件掛在休市日"      # 因子存在，只是日期落在颱風休市日
        else:
            why = "未歸因"
        why_n[why] += 1
        rows.append([sid, meta.get(sid, {}).get("name", ""), d,
                     then.get((sid, d), ""), meta.get(sid, {}).get("market", ""),
                     f"{p:.2f}", f"{c:.2f}", f"{(c / p - 1) * 100:+.2f}%", why])

    # ⛔ 先讀舊的再寫新的，才算得出「本輪變化量」
    old_un = None
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            old_un = sum(1 for r in csv.DictReader(f) if r.get("why") == "未歸因")
    # ⭐ 歷史最低值（K線線 2026-09-09 22:50 加的，理由見下）
    low = None
    if os.path.exists(LOW):
        try:
            low = int(io.open(LOW, encoding="utf-8").read().split(",")[0].strip())
        except (ValueError, IndexError, OSError):
            low = None
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)

    un = [r for r in rows if r[8] == "未歸因"]
    rl.info("判準", "① change ∈ {'', '0.0'}（**兩市寫法不同**）"
                    " ② close ≠ 前收（擋真平盤） ③ 前一列是緊鄰交易日（擋薄量股的洞）"
                    " ④ **前一列 market 相同**（擋轉上市首日：換市場基準本來就不可比）")
    rl.info("偵測到的公司行動日", f"{len(hits):,} 筆（{SINCE} 起，普通股，含下市檔）")
    rl.info("歸因", "｜".join(f"{k} {v}" for k, v in sorted(why_n.items()))
            + "　⛔ 只有『未歸因』是缺陷")
    # ⭐ 總數與變化量**一起印**：只印總數的話，補 100 與新增 100 會互相抵銷
    delta = "（第一趟，沒有前值可比）" if old_un is None else f"{old_un - len(un):+d}"
    rl.info("⭐ 未歸因",
            f"**總數 {len(un)}**／{len({r[0] for r in un})} 檔｜"
            f"**本輪變化量 {delta}**（負號＝變多）")
    by_then = defaultdict(int)
    for r in un:
        by_then[r[3] or "（日檔無此列）"] += 1
    rl.info("  未歸因按**當時**的市場", dict(by_then))
    for r in sorted(un, key=lambda x: float(x[7].rstrip("%")))[:8]:
        rl.note(f"  {r[0]} {r[1]}｜{r[2]}｜{r[5]} → {r[6]}｜**{r[7]}**"
                f"｜當時 {r[3] or '?'}／現在 {r[4]}")
    rl.info("完整清單", "data/meta/_adj_gap.csv")

    # ⛔ 不設絕對門檻（歷史欠帳會讓它天天紅，而天天紅的檢查會被學會忽略）。
    #   ⇒ 用「有沒有變多」當判準——那才回答得了「今天有沒有變壞」。
    # ⭐ 判準是「不得高於**歷史最低值**」，不是「不得比上一趟多」。
    #   ⛔ 用「比上一趟多」的話：那 27 檔補回來時它會變少（好事），
    #     但補完之後基準就停在那個低點——**下一次新的漏抓要累積到超過舊基準才會紅**。
    #   ⇒ 用歷史最低值 ⇒ **單調收斂**：每補好一次，門檻自動變嚴一次。
    base = len(un) if low is None else min(low, len(un))
    rl.info("歷史最低值", f"{low if low is not None else '（第一趟）'} → {base}"
            "　⭐ 斷言用這個，不是用上一趟——否則補完之後門檻會停在低點")
    rl.check("未歸因的筆數沒有高於歷史最低值",
             low is None or len(un) <= low,
             f"歷史最低 {low}｜本輪 {len(un)}" if low is not None
             else "第一趟，只記錄不判定")
    try:
        io.open(LOW, "w", encoding="utf-8").write(
            f"{base},{datetime.now(TPE).strftime('%Y-%m-%d')}\n")
    except OSError:
        pass
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
