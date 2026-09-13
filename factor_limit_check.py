#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""factor_limit_check.py — 用**交易所的漲跌停**證明還原因子錯了。
**只讀 repo，不連外。**

## ⭐⭐ 為什麼這一條是「證明」而不是「推論」

事件日的漲跌停，交易所是用**參考價**算的（⛔ 不是前一日收盤）。
⇒ 若我方的 `ref_price` 就是交易所用的那個，成交價**不可能**超出該日的漲停價。
⚠ 而「該日的漲停價」是有年代的：**2015-06-01 以前是 7%**（`price_limit.py`）。
⇒ **超出了 ⇒ 交易所用的參考價不是我方那個 ⇒ 我方的因子是錯的。**

⚠ 它跟「事件日漲跌幅落在 [0.895, 1.105] 之外」（回測線 PREREG9 的 F2）不同：
F2 抓到 21 筆，⛔ 而其中 3 筆是**無漲跌幅限制的 ETF 真的大跌**（2020-03-19 崩盤日）
⇒ F2 分不出「因子錯」與「那天真的走那麼多」。**這一條分得出來。**

## ⛔ 前提：那一檔要**真的有** ±10% 的硬性上限——而那是量出來的

⚠ 無漲跌幅限制的證券（國外成分 ETF、債券 ETF、槓桿型…）套上去就是誤報。
⇒ 判準不是一份清單，是**拿它自己的歷史問**：
   非事件日 ≥ 500 天，而且 `|日漲跌|` **一次都沒有**超過 10.5%。
⚠ 而這一格**故意不做年代切分**（⛔ 跟事件日那一側相反），理由見 `has_hard_limit()`
——⭐ 那裡記著 2015 上半年 148,484 組相鄰日對的逐組歸因（解釋不了的：**0 組**）。
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
            src, over = judge(ser[i][1], ref, d, off.get((code, d)), slack,
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
