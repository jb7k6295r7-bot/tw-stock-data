#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""missing_rows.py — 母體日檔**整列漏掉**的規模，用**我方自己已有的官方清單**去量。

## 這一支在答什麼

市場情報分析線 2026-09-10 00:20 拿到官方直接證據：

    tpex afterTrading/tradingStock?code=6904&date=2026/09/01
    6904 伯鑫 2026 年 9 月，官方 7 個交易日；我方 data/stocks/6904.csv 只有 3 天

⇒ 官方**確實發布了那一列**，是我方不寫。根因在 `backfill.parse_twse()`：

    o, h, l, c = _num(...)
    if not c:
        continue          # ← 收盤價空或 "--" ⇒ 整列丟掉，還沒到寫檔就沒了

⛔ 而「成交張數 0」**不等於「沒有交易」**：6904 在 09-03／09-04／09-09 的
成交仟元分別是 2／8／2 ⇒ 那是**零股成交**。
⇒ 丟掉的不只是「完全沒人買賣的日子」，還包括**有零股成交、官方有掛牌價的日子**。

## ⭐ 判準：用**我方自己已經存著的六張官方清單**做差集

    data/universe/{per, margin, inst, otcper, otcmargin, otcinst}/<日期>.csv

這六張都是**官方當天發的清單**，而且它們列的是「掛牌中的證券」或
「當天有法人／信用交易的證券」——**不是「有成交的證券」**。
⇒ 「這六張任一有、`data/universe/daily/` 沒有」＝ 該列一定漏了。

⭐ 這個做法的三個好處：
  ① **完全不必連外**：資料早就在 repo 裡，2,848 天一次算完。
  ② `inst`／`otcinst` 那一部分是**鐵證**：三大法人有交易 ⇒ 一定有成交。
  ③ 每天自動重算 ⇒ 修好之後數字會自己降下來，不必有人記得回來量。

## ⛔ 這是**下界**，不是總數

某一檔某一天若**六張清單全都沒有它**（不是融資融券標的、法人沒動、
虧損所以沒有本益比），這支就抓不到。
⛔ 所以報告裡一律寫「**至少**」，⚠ 不可以把這個數字當成「全部」。

## ⛔ 判準是「不得高於歷史最低值」，不是「不得比上一趟多」

跟 `adj_gap.py` 同一條理由：用「比上一趟多」的話，補好一次之後
基準就停在那個低點，**下一次新的漏抓要累積到超過舊基準才會紅**。
用歷史最低值 ⇒ **單調收斂**：每補好一次，門檻自動變嚴一次。
"""
import csv
import io
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
UNI = os.path.join(_ROOT, "universe")
META = os.path.join(_ROOT, "meta", "stocks.csv")
OUT = os.path.join(_ROOT, "meta", "_missing_rows.csv")
SUM = os.path.join(_ROOT, "meta", "_missing_rows_by_day.csv")
LOW = os.path.join(_ROOT, "meta", "_missing_rows_low.txt")

# ⛔ 順序有意義：印出來時要看得出是哪一張清單指認的。
#   `inst`／`otcinst` 排最後是因為它們是**最強的證據**（法人有交易 ⇒ 一定有成交），
#   在 `sources` 欄裡出現時要特別看得見。
SRCS = ("per", "margin", "otcper", "otcmargin", "inst", "otcinst")
SUSP = os.path.join(_ROOT, "meta", "suspend_twse.csv")
HEADER = ["date", "stock_id", "name", "market", "sources", "why"]


def _codes(path):
    """→ {代號} 或 None（檔案不存在）。⛔ 兩者要分得出來：
    「這一天官方清單沒存」和「這一天官方清單是空的」意思完全不同。"""
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as f:
        return {r["stock_id"] for r in csv.DictReader(f) if r.get("stock_id")}


def _susp(base=None):
    """→ {(代號, 日期)}，官方公告**暫停交易**的那一天。

    ⭐ 市場情報分析線 2026-09-10 09:47 指出：那些漏列裡有一部分**有官方正當理由**
      （那天根本不准交易），跟「冷門股當天沒人買賣」意義完全不同——
      對 MA／ATR／均額的影響也不同。
    ⛔ 但範圍要寫死：他們量到的是 212／214，**只佔全部漏列的 0.3%**，
      其餘仍然是 `parse_twse()` 跳過 `--` 那一條。
      ⇒ 這一欄是**歸因**，不是「漏列已解決」。
    """
    p = os.path.join(base, "meta", "suspend_twse.csv") if base else SUSP
    out = set()
    if not os.path.exists(p):
        return out
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d, c = (r.get("susp_date") or "").strip(), (r.get("stock_id") or "").strip()
            if d and c:
                out.add((c, d))
    return out


def _meta():
    m = {}
    if os.path.exists(META):
        with io.open(META, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                m[r["stock_id"]] = r
    return m


def scan(root=None):
    """→ (逐筆 rows, 每日計數 dict, 每個 feed 各自的貢獻 dict, 可比天數)

    ⛔ 抽成函式（不是 inline 在 main 裡）是為了讓 selftest 測得到——
      測不到的檢查等於不存在。
    """
    base = os.path.join(root, "data") if root else _ROOT
    uni = os.path.join(base, "universe")
    meta = {}
    mp = os.path.join(base, "meta", "stocks.csv")
    if os.path.exists(mp):
        with io.open(mp, encoding="utf-8") as f:
            meta = {r["stock_id"]: r for r in csv.DictReader(f)}
    dd = os.path.join(uni, "daily")
    if not os.path.isdir(dd):
        return [], {}, {}, 0
    days = sorted(n[:-4] for n in os.listdir(dd) if n.endswith(".csv"))
    susp = _susp(base if root else None)
    rows, byday, bysrc, n_cmp = [], {}, Counter(), 0
    for d in days:
        have = _codes(os.path.join(dd, d + ".csv"))
        if have is None:
            continue
        nm, mk = {}, {}
        with io.open(os.path.join(dd, d + ".csv"), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                nm[r["stock_id"]] = r.get("name", "")
                mk[r["stock_id"]] = r.get("market", "")
        seen_any = False
        who = defaultdict(list)
        for s in SRCS:
            c = _codes(os.path.join(uni, s, d + ".csv"))
            if c is None:
                continue
            seen_any = True
            for code in c - have:
                who[code].append(s)
        if not seen_any:
            continue
        n_cmp += 1
        # ⛔ 只算普通股：ETF／權證／特別股不在「母體」的定義裡，
        #   混進來會讓數字看起來更嚴重，而那是假的。
        miss = {c: v for c, v in who.items()
                if meta.get(c, {}).get("kind") == "stock"}
        byday[d] = len(miss)
        for code, srcs in sorted(miss.items()):
            for s in srcs:
                bysrc[s] += 1
            rows.append([d, code, meta.get(code, {}).get("name", nm.get(code, "")),
                         meta.get(code, {}).get("market", mk.get(code, "")),
                         "+".join(srcs),
                         "官方暫停交易" if (code, d) in susp else ""])
    return rows, byday, dict(bysrc), n_cmp


def main():
    rl = runlog.Run("missing_rows")
    rows, byday, bysrc, n_cmp = scan()
    if not rows and n_cmp == 0:
        rl.info("狀態", "✗ 沒有可比的日子（`data/universe/daily/` 或六張官方清單都不在）")
        return rl.finish()

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
    with io.open(SUM, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "missing"])
        for d in sorted(byday):
            w.writerow([d, byday[d]])

    codes = {r[1] for r in rows}
    byyear, ndays = Counter(), Counter()
    for d, n in byday.items():
        byyear[d[:4]] += n
        ndays[d[:4]] += 1
    rl.info("判準", "六張官方清單（per/margin/inst 與上櫃三張）任一有、"
                    "`universe/daily/` 沒有 ⇒ 該列漏了。"
                    "⛔ 這是**下界**：六張都沒列到的檔抓不到。")
    rl.info("⭐ 至少漏掉", f"**{len(rows):,} 筆／{len(codes)} 檔**"
                          f"（可比 {n_cmp} 個交易日）")
    rl.info("  逐年", "｜".join(f"{y} {byyear[y]:,}筆/每日{byyear[y]/ndays[y]:.1f}檔"
                               for y in sorted(byyear)))
    # ⭐ 逐 feed 印出來：哪一張清單指認得最多，就代表哪一類漏得最兇。
    #   ⛔ 這幾個數字**會重複計算**（同一筆可能被兩張清單同時指認），
    #     所以它們的和不等於總筆數——要講明，否則有人會去加總。
    rl.info("  各清單各自指認（⛔ 會重複計，和不等於總數）",
            "｜".join(f"{k} {v:,}" for k, v in sorted(bysrc.items(),
                                                     key=lambda x: -x[1])))
    strong = sum(v for k, v in bysrc.items() if k in ("inst", "otcinst"))
    rl.info("  ⭐ 其中鐵證（法人有交易 ⇒ 一定有成交）", f"{strong:,} 筆")
    # ⭐ 歸因：其中有多少是**官方那天公告暫停交易**（＝有正當理由，不是抓取端漏抓）
    n_susp = sum(1 for r in rows if r[5])
    rl.info("  歸因",
            f"官方暫停交易 **{n_susp:,} 筆**（{n_susp / max(1, len(rows)) * 100:.2f}%）"
            f"｜未歸因 {len(rows) - n_susp:,} 筆"
            "　⛔ 暫停交易只解釋千分之三，其餘仍是 `parse_twse()` 跳過 `--` 那一條")
    top = Counter(r[1] for r in rows).most_common(8)
    rl.info("  最常被漏的 8 檔", "｜".join(f"{c} {n}天" for c, n in top))
    recent = sorted(byday)[-5:]
    rl.info("  最近五個可比日", "｜".join(f"{d} {byday[d]}檔" for d in recent))
    rl.info("完整清單", "data/meta/_missing_rows.csv（逐筆）／"
                        "_missing_rows_by_day.csv（每日計數）")

    base = len(rows) if low is None else min(low, len(rows))
    rl.info("歷史最低值", f"{low if low is not None else '（第一趟）'} → {base}"
            "　⭐ 斷言用這個，不是用上一趟——否則補完之後門檻會停在低點")
    rl.check("漏列筆數沒有高於歷史最低值",
             low is None or len(rows) <= low,
             f"歷史最低 {low}｜本輪 {len(rows)}" if low is not None
             else "第一趟，只記錄不判定")
    try:
        io.open(LOW, "w", encoding="utf-8").write(
            f"{base},{datetime.now(TPE).strftime('%Y-%m-%d')}\n")
    except OSError:
        pass
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
