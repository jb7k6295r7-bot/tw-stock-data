#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""factor_limit_check.py — 用**交易所的漲跌停**證明還原因子錯了。
**只讀 repo，不連外。**

## ⭐⭐ 為什麼這一條是「證明」而不是「推論」

事件日的漲跌停，交易所是用**參考價**算的（⛔ 不是前一日收盤）。
⇒ 若我方的 `ref_price` 就是交易所用的那個，成交價**不可能**超出 `ref × 1.10`。
⇒ **超出了 ⇒ 交易所用的參考價不是我方那個 ⇒ 我方的因子是錯的。**

⚠ 它跟「事件日漲跌幅落在 [0.895, 1.105] 之外」（回測線 PREREG9 的 F2）不同：
F2 抓到 21 筆，⛔ 而其中 3 筆是**無漲跌幅限制的 ETF 真的大跌**（2020-03-19 崩盤日）
⇒ F2 分不出「因子錯」與「那天真的走那麼多」。**這一條分得出來。**

## ⛔ 前提：那一檔要**真的有** ±10% 的硬性上限——而那是量出來的

⚠ 無漲跌幅限制的證券（國外成分 ETF、債券 ETF、槓桿型…）套上去就是誤報。
⇒ 判準不是一份清單，是**拿它自己的歷史問**：
   非事件日 ≥ 500 天，而且 `|日漲跌|` **一次都沒有**超過 10.5%。
⛔ 而「非事件日」這個排除是必要的：事件日本身的跳空會讓每一檔看起來都無限制
（⚠ 第一版沒排除 ⇒ 3562 的最大日漲跌算出 290%，整個判準當場失效）。

## 校準（2026-09-13 全庫實測）

```
有硬性上限的證券 1,926 檔｜事件 19,767 筆
  在 ±10% 內   19,760   99.965%
  ⛔ 超出          7     0.035%   ← ⭐ 而 7 筆**全部**在 F2 那 21 筆裡
```
⇒ **誤報 0 / 19,760**，而且它抓到的每一筆都是獨立判準也認定有問題的。
"""
import argparse
import csv
import io
import os
import sys

import runlog

_HERE = os.path.dirname(os.path.abspath(__file__))
ADJ = os.path.join(_HERE, "data", "adj")
STOCKS = os.path.join(_HERE, "data", "stocks")
OUT = os.path.join(_HERE, "data", "meta", "_factor_limit_check.csv")
# ⭐ 歷史最低值：斷言的基準（跟 `adj_gap.py` 同一個慣例）。
#   ⛔ 用「上一趟」當基準會讓門檻停在補完後的低點；用固定數字則永遠不會降。
#   ⚠ 而這一支**現在就有 7 筆**（2026-09-13 逐筆判定過，見 docs/READ_CONTRACT.md）
#     ⇒ 若寫成「必須 0 筆」，它會天天紅、然後被學會忽略（六點五那條）。
#   ⇒ 判準改成「**不可以變多**」，⭐ 而那 7 筆仍然逐筆印進 runlog，
#     ⛔ 不是讓它們消失——消失的那一刻就再也沒有人會想起它。
LOW = os.path.join(_HERE, "data", "meta", "_factor_limit_low.txt")
LIMIT = 1.105        # ±10% ＋ 一點點分位與 tick 的餘裕
MIN_DAYS = 500       # 非事件日至少要這麼多天才判得出「它有沒有硬性上限」
LOOSE = 0.105        # 「超過這個就當它沒有 10% 上限」


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def closes(code):
    """→ [(日期, 收盤)]，⛔ 只留有收盤的天，按日期升冪。"""
    p = os.path.join(STOCKS, f"{code}.csv")
    if not os.path.exists(p):
        return []
    out = [(r["date"], _num(r.get("close")))
           for r in csv.DictReader(io.open(p, encoding="utf-8")) if r.get("date")]
    return sorted((d, c) for d, c in out if c is not None)


def event_dates(code):
    """→ 該檔所有事件日的集合。"""
    p = os.path.join(ADJ, f"{code}.csv")
    if not os.path.exists(p):
        return set()
    return {r["date"] for r in csv.DictReader(io.open(p, encoding="utf-8"))
            if r.get("date")}


def has_hard_limit(series, evd, min_days=MIN_DAYS, loose=LOOSE):
    """→ (這一檔有沒有硬性 ±10% 上限, 可用的非事件日數)。

    ⛔ **一定要排除事件日與其次日**：事件日的跳空本來就會超過 10%，
    ⚠ 不排除的話每一檔都會被判成「無限制」⇒ 這道閘門就永遠不會叫。
    """
    n = 0
    for i in range(1, len(series)):
        if series[i][0] in evd or series[i - 1][0] in evd:
            continue
        if series[i - 1][1] <= 0:
            continue
        n += 1
        if abs(series[i][1] / series[i - 1][1] - 1) > loose:
            return False, n
    return n >= min_days, n


def check_all(limit=LIMIT):
    """→ (超出漲跌停的事件, 有判的事件數, 有硬性上限的檔數)。⛔ 只讀。"""
    import bisect
    bad, checked, nhard = [], 0, 0
    if not os.path.isdir(ADJ):
        return bad, checked, nhard
    for fn in sorted(os.listdir(ADJ)):
        if not fn.endswith(".csv") or fn.startswith("_"):
            continue
        code = fn[:-4]
        ser = closes(code)
        if len(ser) < 2:
            continue
        evd = event_dates(code)
        ok, _n = has_hard_limit(ser, evd)
        if not ok:
            continue
        nhard += 1
        days = [d for d, _ in ser]
        for r in csv.DictReader(io.open(os.path.join(ADJ, fn), encoding="utf-8")):
            d = r.get("date") or ""
            ref = _num(r.get("ref_price"))
            if len(d) != 10 or not ref or ref <= 0:
                continue
            i = bisect.bisect_left(days, d)
            if i >= len(days) or days[i] != d:
                continue
            q = ser[i][1] / ref
            checked += 1
            if q > limit or q < 2 - limit:
                bad.append({"stock_id": code, "date": d,
                            "kind": (r.get("kind") or "").strip(),
                            "factor": r.get("factor", ""),
                            "ref_price": f"{ref:.4f}", "close": f"{ser[i][1]:.4f}",
                            "close_over_ref": f"{q:.4f}"})
    return bad, checked, nhard


def read_low():
    """→ (歷史最低筆數, 那一天)；讀不到回 (None, "")。"""
    try:
        n, d = io.open(LOW, encoding="utf-8").read().strip().split(",", 1)
        return int(n), d
    except (OSError, ValueError):
        return None, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    rl = runlog.Run("factor_limit")
    bad, checked, nhard = check_all()
    rl.info("⭐ 這一支在驗什麼",
            "事件日成交價**不可能**超出「參考價 ×1.10」——交易所的漲跌停就是這樣算的"
            "⇒ 超出了就**證明**我方的參考價不是交易所用的那個")
    rl.info("母體", f"有硬性 ±10% 上限的證券 {nhard} 檔｜事件 {checked:,} 筆"
                    f"（⛔ 無漲跌幅限制的 ETF 等已排除，它們套這條就是誤報）")
    # ⭐ 「掃到 0 筆」跟「根本沒掃到」長得一樣 ⇒ 先釘母體
    rl.check("⭐ 這道閘門真的有母體可掃（⛔ 掃到 0 筆事件跟全部通過長得一樣）",
             checked >= 1000, f"{checked:,} 筆")
    # ⭐ 逐筆印出來——⛔ 白名單／低水位**不可以讓它們從報表上消失**
    for x in sorted(bad, key=lambda t: t["date"]):
        rl.info(f"⛔ {x['stock_id']} {x['date']} {x['kind']}",
                f"收/參考 {x['close_over_ref']}｜factor {x['factor']}"
                f"｜參考價 {x['ref_price']}｜收盤 {x['close']}")
    low, lowday = read_low()
    if low is None:
        rl.check("沒有任何事件的成交價超出交易所漲跌停（⇒ 參考價與交易所一致）",
                 not bad, f"{len(bad)} 筆（⚠ 沒有低水位檔可比）")
    else:
        rl.check(f"⭐ 超出漲跌停的筆數**沒有變多**（歷史最低 {low} 筆，{lowday}）",
                 len(bad) <= low, f"這一趟 {len(bad)} 筆 vs 歷史最低 {low} 筆")
        if a.write and len(bad) < low:
            import datetime
            io.open(LOW, "w", encoding="utf-8").write(
                f"{len(bad)},{datetime.date.today().isoformat()}\n")
            rl.info("⭐ 低水位下修", f"{low} → {len(bad)}")
    if a.write and bad:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(bad[0]))
            w.writeheader()
            w.writerows(sorted(bad, key=lambda x: x["date"]))
        back = list(csv.DictReader(io.open(OUT, encoding="utf-8")))
        rl.check("清單寫得進去而且讀得回來", len(back) == len(bad),
                 f"寫 {len(bad)}、讀回 {len(back)}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
