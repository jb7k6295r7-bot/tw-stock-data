#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""factor_limit_check.py — 用**交易所的漲跌停**證明還原因子錯了。
**只讀 repo，不連外。**

## ⭐⭐ 判準：事件日的成交價不可能超出**那一天的漲停價**

⭐ 而「那一天的漲停價」**優先用官方給的**（`data/universe/exright|reduce` 的
`limit_up`／`limit_down` 兩欄，官方逐筆給、涵蓋自民國 92-05-05）。
⇒ 超出官方漲停 ⇒ 交易所用的基準不是我方那個 ⇒ 我方的因子有問題。

⚠ 它跟「事件日漲跌幅落在 [0.895, 1.105] 之外」（回測線 PREREG9 的 F2）不同：
F2 抓到 21 筆，⛔ 而其中 3 筆是**無漲跌幅限制的 ETF 真的大跌**（2020-03-19 崩盤日）
⇒ F2 分不出「因子錯」與「那天真的走那麼多」。**這一條分得出來。**

## ⛔⛔ 2026-09-13：官方數字回來了，而它**推翻了這一支原本的前提**

原本檔頭寫著：「事件日的漲跌停，交易所是用**參考價**算的
⇒ 成交價不可能超出 `ref × 1.10` ⇒ 超出了就**證明**因子錯。」

⚠ 補存官方 `漲停價格` 之後逐筆比對，那句話**對現金增資除權不成立**：

```
910482 2017-06-19  我方 ref 0.58    官方漲停 0.82   ⇒ 官方漲停 / 我方 ref = **1.41**
6224   2021-01-13  我方 ref 101.05  官方漲停 113.00 ⇒ 1.1183（收盤剛好鎖漲停）
8033   2023-03-06  我方 ref 55.24   官方漲停 62.30  ⇒ 1.1278
9105   2023-10-06  我方 ref 2.91    官方漲停 4.49   ⇒ **1.54**
```

⇒ ⭐ 因為**漲停的基準是 `減除股利參考價`，不是 `除權息參考價`**
（2353 那一格是逐位證據：22.80 ＝ ⌊21.35 × 1.07⌋）。
含現金增資的案子兩者差很多 ⇒ 官方讓價格從**比較高**的那個基準往上走。

⇒ ⛔⛔ **這四筆原本被這支判成「因子錯」，而官方的數字說它們在漲停之內。**
⚠ 它們是我方推論的**誤報**，⛔ 不是資料有問題。

### ⇒ 所以這一支的判準改成：**官方優先，推論只是退路**

```
有官方漲跌停        ⇒ ⭐ 用官方的
官方說無漲跌幅限制  ⇒ ⛔ 這一筆**沒有判準**（不進母體，也不算通過）
沒有官方數字        ⇒ 退回 price_limit 的公式，⚠ 而它對現增案會誤報
```

## ⛔ 退路那一半的前提：那一檔要**真的有** ±10% 的硬性上限——而那是量出來的

⚠ 無漲跌幅限制的證券（國外成分 ETF、債券 ETF、槓桿型…）套上去就是誤報。
⇒ 判準不是一份清單，是**拿它自己的歷史問**：
   非事件日 ≥ 500 天，而且 `|日漲跌|` **一次都沒有**超過 10.5%。
⛔ 而「非事件日」這個排除是必要的：事件日本身的跳空會讓每一檔看起來都無限制
（⚠ 第一版沒排除 ⇒ 3562 的最大日漲跌算出 290%，整個判準當場失效）。
⚠ 而這一格**故意不做年代切分**（⛔ 跟事件日那一側相反），理由見 `has_hard_limit()`
——⭐ 那裡記著 2015 上半年 148,484 組相鄰日對的逐組歸因（解釋不了的：**0 組**）。

⭐ 而 2026-09-13 起它**只管退路**：判成「無漲跌幅限制」的證券，
它**有官方數字**的那些事件照樣要判——⛔ 拿比較差的判準去否決比較好的沒有道理。

## 校準（2026-09-13 全庫實測，**官方漲跌停回補完之後**）

```
母體 20,207 筆事件
  判準來源  官方 11,106｜推論 9,101
            官方說無限制 506              ⛔ 這些**沒有判準**，不進母體
            無官方數字且推論說無限制 1,578 ⛔ 同上
  ⛔ 超出          2     0.010%
```

### ⛔⛔ 而「超出」從 **7 筆降到 2 筆**，⚠ 這不是修好了，是**原本那 5 筆是誤報**

```
910482 2017-06-19  我方 ref 0.58    官方漲停 0.82    收 0.75   ⇒ ✅ 在內
6224   2021-01-13  我方 ref 101.05  官方漲停 113.00  收 113.00 ⇒ ✅ 剛好鎖漲停
8033   2023-03-06  我方 ref 55.24   官方漲停 62.30   收 61.50  ⇒ ✅ 在內
9105   2023-10-06  我方 ref 2.91    官方漲停 4.49    收 3.44   ⇒ ✅ 在內
2464   2026-09-02  ——官方數字回來之後也在內
```
⇒ ⭐ **五筆全是上市**，而官方的數字說它們沒有超出。

### ⛔ 剩下的 2 筆都是**上櫃**，而上櫃沒有官方漲跌停

```
2736 高野    2024-05-28  tpex
4991 F-環宇  2025-12-22  tpex
```
⚠ TWT49U 只涵蓋**上市** ⇒ 這兩筆走的是**已經被推翻的那個推論**
⇒ ⛔ 它們要標成「**未證實**」，不是「已證明因子錯」。
"""
import argparse
import csv
import io
import os
import sys

import price_limit
import runlog

_HERE = os.path.dirname(os.path.abspath(__file__))
ADJ = os.path.join(_HERE, "data", "adj")
STOCKS = os.path.join(_HERE, "data", "stocks")
# ⭐⭐ 官方**逐筆**給的漲跌停就在這兩個目錄的日檔裡（2026-09-13 才開始存）。
#   ⇒ 有官方數字的事件**一律用官方的**，⛔ 推論只是沒有官方數字時的退路。
UNI = os.path.join(_HERE, "data", "universe")
OFFICIAL_DIRS = ("exright", "reduce")
OUT = os.path.join(_HERE, "data", "meta", "_factor_limit_check.csv")
# ⭐ 歷史最低值：斷言的基準（跟 `adj_gap.py` 同一個慣例）。
#   ⛔ 用「上一趟」當基準會讓門檻停在補完後的低點；用固定數字則永遠不會降。
#   ⚠ 而這一支**現在就有 7 筆**（2026-09-13 逐筆判定過，見 docs/READ_CONTRACT.md）
#     ⇒ 若寫成「必須 0 筆」，它會天天紅、然後被學會忽略（六點五那條）。
#   ⇒ 判準改成「**不可以變多**」，⭐ 而那 7 筆仍然逐筆印進 runlog，
#     ⛔ 不是讓它們消失——消失的那一刻就再也沒有人會想起它。
LOW = os.path.join(_HERE, "data", "meta", "_factor_limit_low.txt")
# ⭐⭐ 2026-09-13：原本這裡寫的是 `LIMIT = 1.105`（＝一律 ±10%）。
#   ⛔ **那是一個有年代的數字**：台股 2015-06-01 才由 7% 放寬為 10%。
#   ⚠ 而它錯的方向是**放行**——用 10% 去量 7% 的日子，超出 7% 的那些靜靜通過
#     ⇒ ⛔ 不會有任何地方叫，只會少抓。⇒ 改走 `price_limit`（唯一的一份實作）。
SLACK = 0.005        # 相對餘裕（⛔ 不是絕對值，三點6）：我方 ref 只存到分
MIN_DAYS = 500       # 非事件日至少要這麼多天才判得出「它有沒有硬性上限」
LOOSE = 0.005        # 判「有沒有硬性上限」時，在 10% 之外再讓一點


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
        # ⛔⛔ 這裡**故意不做**年代切分（⚠ 跟事件日那一側相反）。
        #
        #   ⭐ 2026-09-13 全庫實測 2015-01-05 ~ 2015-05-29（7% 年代）：
        #     非事件日的相鄰日對 **148,484 組**，超過 ±7.5% 的只有 **58 組**
        #     （0.039%），⇒ 7% 這件事本身**成立得很乾淨**。
        #   ⚠ 而那 58 組**一組都不是謎**：
        #       33 組  無漲跌幅限制族（00 開頭的 ETF／槓桿／指數）
        #        8 組  新上市（櫃）**前五個交易日**（官方本來就不設漲跌幅）
        #       17 組  中間隔了不只一個交易日（停牌／長假 ⇒ 那不是「一天」）
        #       ⛔ 0 組  解釋不了
        #   ⇒ ⭐ 所以「3374／4530／8341 被踢出母體」的成因也知道了：
        #     3374、8341 是**上市（櫃）次日**（首五日無漲跌幅），4530 是跨了停牌。
        #
        #   ⇒ 那為什麼還是不切？因為要切就得**同時**加上那兩個排除
        #     （首五日、跨交易日），⚠ 而實測結果完全一樣（7 筆）
        #     ⇒ ⛔ 多寫兩個排除換 0 個新發現，而每一個排除都是一個新的錯法。
        #   ⭐ 放寬（一律 10%）在這裡只會讓母體**大一點**，方向是安全的；
        #     ⛔ 收緊則會在沒有任何收穫的情況下刪掉母體。
        if abs(series[i][1] / series[i - 1][1] - 1) > price_limit.CAP_NEW + loose:
            return False, n
    return n >= min_days, n


def official_limits(dirs=OFFICIAL_DIRS):
    """→ {(股票代號, 日期): (漲停, 跌停)}，官方逐筆給的那兩欄。⛔ 只讀。

    ⚠ 舊日檔**沒有**這兩欄（2026-09-13 才加）⇒ 這份對照表一開始會是空的，
    ⛔ 而「空的」跟「全部都在範圍內」長得一模一樣
      ⇒ 呼叫端一定要把**涵蓋率**印出來（`main()` 有）。
    """
    out = {}
    for sub in dirs:
        d = os.path.join(UNI, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".csv") or fn.startswith("_"):
                continue
            try:
                with io.open(os.path.join(d, fn), encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        up, dn = r.get("limit_up"), r.get("limit_down")
                        code, day = r.get("stock_id"), r.get("date")
                        if not code or not day or not up or not dn:
                            continue
                        out[(code, day)] = (up, dn)
            except OSError:
                continue
    return out


def judge(close, ref, day, official, slack=SLACK, etf=False):
    """→ ("官方"|"推論"|"官方說無限制", 有沒有超出)。

    ⭐ 這一支是整個判定的**唯一**入口（四點五），而它把三種情形分開：
    ```
    官方給了漲跌停          ⇒ ⭐ 用官方的，⛔ 不再推
    官方說「無漲跌幅限制」  ⇒ 這一筆**沒有判準**，⛔ 不可以算成「通過」
    官方沒給（舊日檔）      ⇒ 退回 price_limit 的公式
    ```
    ⚠ 第二種最重要：把它算成「通過」等於**把母體灌水**，
    ⛔ 而那正是第七點那句「0 筆與沒掃到長得一樣」。
    """
    if official:
        up, dn = official
        if price_limit.is_unlimited(up, dn):
            return "官方說無限制", False
        u, d_ = price_limit._num(up), price_limit._num(dn)
        if u is not None and d_ is not None and u > 0:
            return "官方", not (d_ * (1.0 - slack) <= close <= u * (1.0 + slack))
    return "推論", not price_limit.within(close, ref, day, slack, etf)


def check_all(slack=SLACK):
    """→ (超出漲跌停的事件, 有判的事件數, 有硬性上限的檔數, 各判準來源的筆數)。⛔ 只讀。"""
    import bisect
    import collections
    bad, checked, nhard = [], 0, 0
    how = collections.Counter()
    off = official_limits()
    if not os.path.isdir(ADJ):
        return bad, checked, nhard, how
    for fn in sorted(os.listdir(ADJ)):
        if not fn.endswith(".csv") or fn.startswith("_"):
            continue
        code = fn[:-4]
        ser = closes(code)
        if len(ser) < 2:
            continue
        evd = event_dates(code)
        ok, _n = has_hard_limit(ser, evd)
        # ⭐⭐ 2026-09-13：`has_hard_limit` 只再管**退路**那一半。
        #   ⛔ 原本它是整檔的門：判成「無漲跌幅限制」的證券，
        #     連它**有官方漲跌停**的那些事件也一起被跳過。
        #   ⚠ 而那道推論本來就是官方旗標的替代品（`9,999.95`／`0.01`），
        #     ⇒ 有官方數字時拿推論去擋它，等於**用比較差的那個判準否決比較好的**。
        #   ⭐ 而它還有一個推論版處理不了的情形：**同一檔可以在不同時期換**
        #     （加掛、改型態）⇒ 一檔一個布林值本來就不夠。
        if ok:
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
            o = off.get((code, d))
            # ⛔ 沒有官方數字、而且這一檔被判成無漲跌幅限制 ⇒ **這一筆沒有判準**
            #   ⚠ 不是「通過」——所以它連 `checked` 都不進（見下面那一段）。
            if o is None and not ok:
                how["沒有判準（無官方數字＋推論說無限制）"] += 1
                continue
            src, over = judge(ser[i][1], ref, d, o, slack,
                              etf=price_limit.is_fine_tick(code))
            how[src] += 1
            # ⛔ 官方說「無漲跌幅限制」的那一筆**沒有判準** ⇒ 不進母體
            if src == "官方說無限制":
                continue
            checked += 1
            if over:
                bad.append({"stock_id": code, "date": d, "src": src,
                            "kind": (r.get("kind") or "").strip(),
                            "factor": r.get("factor", ""),
                            "cap": f"{price_limit.cap(d):.2f}",
                            "ref_price": f"{ref:.4f}", "close": f"{ser[i][1]:.4f}",
                            "limit_up": f"{price_limit.up(ref, d):.2f}",
                            "limit_down": f"{price_limit.down(ref, d):.2f}",
                            "close_over_ref": f"{q:.4f}"})
    return bad, checked, nhard, how


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
    bad, checked, nhard, how = check_all()
    rl.info("⭐ 這一支在驗什麼",
            "事件日成交價**不可能**超出該日的漲停價——交易所的漲跌停是用**參考價**算的"
            "⇒ 超出了就**證明**我方的參考價不是交易所用的那個"
            "（⚠ 而「該日的」是有年代的：2015-06-01 以前是 7%）")
    rl.info("母體", f"有硬性 ±10% 上限的證券 {nhard} 檔｜事件 {checked:,} 筆"
                    f"（⛔ 無漲跌幅限制的 ETF 等已排除，它們套這條就是誤報）")
    # ⭐⭐ 判準來源要分開講：⛔ 「官方」與「推論」的可信度差很遠，
    #   ⚠ 而兩者在最後那個筆數上長得一模一樣。
    tot = sum(how.values()) or 1
    rl.info("⭐ 判準來源",
            "｜".join(f"{k} {v:,}（{v / tot * 100:.1f}%）"
                      for k, v in sorted(how.items(), key=lambda x: -x[1]))
            + "　⚠ 官方那兩欄 2026-09-13 才開始存 ⇒ 舊日檔要 `--need-col limit_up`")
    # ⭐ 「官方涵蓋率 0%」跟「官方全部通過」長得一樣 ⇒ 這一條專門把它講出來
    rl.info("⚠ 官方逐筆漲跌停的涵蓋率",
            f"{how.get('官方', 0) + how.get('官方說無限制', 0):,} / {tot:,}"
            + ("　⛔ **是 0** ⇒ 這一趟完全靠推論（回補還沒跑）"
               if not (how.get("官方", 0) + how.get("官方說無限制", 0)) else ""))
    # ⭐ 「掃到 0 筆」跟「根本沒掃到」長得一樣 ⇒ 先釘母體
    rl.check("⭐ 這道閘門真的有母體可掃（⛔ 掃到 0 筆事件跟全部通過長得一樣）",
             checked >= 1000, f"{checked:,} 筆")
    # ⭐ 逐筆印出來——⛔ 白名單／低水位**不可以讓它們從報表上消失**
    for x in sorted(bad, key=lambda t: t["date"]):
        rl.info(f"⛔ {x['stock_id']} {x['date']} {x['kind']}",
                f"收/參考 {x['close_over_ref']}｜factor {x['factor']}"
                f"｜參考價 {x['ref_price']}｜收盤 {x['close']}"
                f"｜該日漲跌停 {x['limit_down']}~{x['limit_up']}（±{x['cap']}）")
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
