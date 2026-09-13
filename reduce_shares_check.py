#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reduce_shares_check.py — 用**我方自己的 `shares` 欄**重算官方減資參考價。
**只讀 repo，不連外。**

## ⭐⭐ 為什麼要有這一支：那個「沒有外部裁判」的結論是錯的

2026-09-13 我寫過一句：

> 上市那 303 筆減資的還原因子全是「官方參考價 ÷ 前收」回推的，
> **而它們沒有任何第二來源可以驗**。

⛔ **錯。** `data/stocks/<代號>.csv` 的 **`shares`（發行股數）**就是那個第二來源：
它來自日檔，**完全不從價格推**——⇒ 拿它算出換股比，就能**獨立**重算參考價。

```
換股比 keep = 減資日的 shares ÷ 前一個有值的交易日的 shares
減資比例 r  = 1 − keep
```

## ⛔ 而兩種減資的算式**不一樣**——這是本支最核心的一格

```
彌補虧損型   ref = 前收 ÷ keep                    ← 股東**沒有**拿到現金
現金型       ref = (前收 − 面額 10 × r) ÷ keep    ← 股東**拿回**每股 10×r 元
（現金型 ＝ `退還股款`／`現金減資`）
```

⚠ 用錯算式的後果是**系統性**的，不是隨機誤差：
2026-09-13 實測，把現金型套上彌補虧損型的算式 ⇒ 1563 差 3.34 元（3.9%）。

⭐ 而這一格正好解釋了 TradingView 為什麼跟我方不同：
它的還原只做 `1 ÷ keep`（純股數），⛔ **沒有把退還的現金扣掉**
⇒ 用它算跨過現金型減資的報酬，會**多算跌幅**（1563 實測多 3.80pp）。
⇒ ⭐ **我方的 `factor = ref ÷ 前收` 才是總價值連續的那一個**：
   `0.75 × 84.66 + 2.505 = 66.00` 逐位相符。

## 判準

`abs(算出來的 ref − 官方 ref) <= 0.05`（官方參考價印到分，容差放寬到 5 分）。
⚠ 在**價格空間**比，⛔ 不在比值空間——四捨五入在比值空間會被放大成假不符。

## ⛔ 回報「對不上 N 筆」時一定要附「對得上幾筆」（CLAUDE.md 第七點）
"""
import argparse
import collections
import csv
import io
import os
import sys

import runlog

_HERE = os.path.dirname(os.path.abspath(__file__))
ADJ = os.path.join(_HERE, "data", "adj")
STOCKS = os.path.join(_HERE, "data", "stocks")
OUT = os.path.join(_HERE, "data", "meta", "_reduce_shares_check.csv")
CASH_KINDS = ("退還股款", "現金減資")
PAR = 10.0          # 台股面額。⚠ 非 10 元面額的個股會落進「對不上」，那是刻意的
TOL = 0.05


def is_cash(kind):
    """→ 這一筆減資有沒有退還現金。⭐ 只有這一份實作。"""
    return (kind or "").strip() in CASH_KINDS


def expected_ref(pre_close, keep, cash):
    """→ 用換股比重算的官方參考價。⛔ 兩種算式不可以混用（見檔頭）。"""
    r = 1.0 - keep
    return ((pre_close - PAR * r) / keep) if cash else (pre_close / keep)


def load_events():
    """→ [(代號, 那一列)]，只取 `event == reduce`。"""
    out = []
    if not os.path.isdir(ADJ):
        return out
    for fn in sorted(os.listdir(ADJ)):
        if not fn.endswith(".csv") or fn.startswith("_"):
            continue
        for r in csv.DictReader(io.open(os.path.join(ADJ, fn), encoding="utf-8")):
            if (r.get("event") or "").strip() == "reduce":
                out.append((fn[:-4], r))
    return out


def shares_around(code, day):
    """→ (減資日的 shares, 前一個有值交易日的 shares)；問不到就回 (None, None)。

    ⚠ 「前一個」要找**有值**的那一天，⛔ 不是前一列——`shares` 欄上市留空，
      而興櫃／某些日子也可能空。
    """
    p = os.path.join(STOCKS, f"{code}.csv")
    if not os.path.exists(p):
        return None, None
    rows = {r["date"]: r for r in csv.DictReader(io.open(p, encoding="utf-8"))}
    days = sorted(rows)
    if day not in rows:
        return None, None
    i = days.index(day)
    a = (rows[day].get("shares") or "").strip()
    b = next(((rows[days[j]].get("shares") or "").strip()
              for j in range(i - 1, -1, -1)
              if (rows[days[j]].get("shares") or "").strip()), "")
    try:
        return (float(a) if a else None), (float(b) if b else None)
    except ValueError:
        return None, None


def check_all():
    """→ (逐筆結果 list, 統計 Counter)。⛔ 只讀，不寫。"""
    res, stat = [], collections.Counter()
    for code, r in load_events():
        day, kind = r["date"], (r.get("kind") or "").strip()
        sa, sb = shares_around(code, day)
        try:
            pre, ref = float(r["pre_close"]), float(r["ref_price"])
        except (ValueError, KeyError, TypeError):
            stat["算不了：價格欄壞掉"] += 1
            continue
        if sa is None or sb is None:
            stat["算不了：問不到 shares"] += 1
            continue
        if sb <= 0 or sa <= 0 or sa >= sb:
            # ⚠ 股數沒變少 ⇒ 這一筆的 shares 對不上這個事件（可能是別的原因改了股數）
            stat["算不了：股數沒變少"] += 1
            continue
        keep = sa / sb
        calc = expected_ref(pre, keep, is_cash(kind))
        diff = abs(calc - ref)
        tag = "現金型" if is_cash(kind) else "彌補虧損型"
        stat[f"{tag}｜{'對得上' if diff <= TOL else '對不上'}"] += 1
        res.append({"stock_id": code, "date": day, "kind": kind,
                    "keep": f"{keep:.6f}", "pre_close": f"{pre:.2f}",
                    "ref_official": f"{ref:.2f}", "ref_calc": f"{calc:.2f}",
                    "diff": f"{diff:.4f}", "ok": "1" if diff <= TOL else "0"})
    return res, stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="把逐筆結果寫成 CSV")
    a = ap.parse_args()
    res, stat = check_all()
    rl = runlog.Run("reduce_shares_check")

    good = sum(v for k, v in stat.items() if k.endswith("對得上"))
    bad = sum(v for k, v in stat.items() if k.endswith("對不上"))
    cant = sum(v for k, v in stat.items() if k.startswith("算不了"))
    rl.info("⭐ 這一支在驗什麼",
            "用**我方自己的 `shares` 欄**算換股比，重算官方減資參考價"
            "（⛔ 不連外、不靠人工匯出的表）")
    for k in sorted(stat):
        rl.info(k, str(stat[k]))
    # ⛔ 「對不上 N 筆」一定要跟「對得上幾筆」放在一起（CLAUDE.md 第七點）
    rl.info("總計", f"對得上 {good}｜對不上 {bad}｜算不了 {cant}")

    # ⭐ 兩種算式**都要有正例**。⛔ 只有一種有，代表另一種其實沒被測到
    #   ——而那正是「某群 0 筆」那個陷阱。
    cash_ok = stat.get("現金型｜對得上", 0)
    loss_ok = stat.get("彌補虧損型｜對得上", 0)
    rl.check("⭐ 兩種算式都各自對上過（⛔ 只有一種有正例 ＝ 另一種沒被測到）",
             cash_ok > 0 and loss_ok > 0,
             f"現金型 {cash_ok} 筆、彌補虧損型 {loss_ok} 筆")
    rl.check("九成以上的減資參考價重算得出來",
             good + bad > 0 and good / (good + bad) >= 0.90,
             f"{good}/{good + bad}"
             + (f"　⚠ 對不上的逐筆在 {os.path.relpath(OUT, _HERE)}" if bad else ""))

    if a.write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(res[0]) if res else
                               ["stock_id", "date", "kind", "keep", "pre_close",
                                "ref_official", "ref_calc", "diff", "ok"])
            w.writeheader()
            w.writerows(sorted((x for x in res if x["ok"] == "0"),
                               key=lambda x: -float(x["diff"])))
        # ⭐ 寫完**重讀**，斷言讀回來的內容（四點二：驗終點）
        back = list(csv.DictReader(io.open(OUT, encoding="utf-8")))
        rl.check("對不上的清單寫得進去而且讀得回來",
                 len(back) == bad, f"寫 {bad} 列、讀回 {len(back)} 列")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
