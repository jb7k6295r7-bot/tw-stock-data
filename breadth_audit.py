#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""breadth_audit.py — 拿大盤漲跌家數當日檔的**外部判準**。離線、只讀。

## 為什麼要有這一支

`db_status.py` 的「沒有來源」那一節列著：

    「某一天到底有幾檔股票成交」的外部判準
    （唯一外部來源是日曆，且只有上市）

日曆（FMTQIK）只證明**那一天存不存在**，不證明那天收到幾檔。
`content_audit.py` 的家數檢查是拿**前後交易日的中位數**比——那是同一條管線
不同趟次，算不上外部。

★ 但外部判準其實已經在手上：`data/history/market_breadth.csv` 的漲跌家數來自
**`MI_INDEX`（大盤層級彙總表）**，與建 `data/universe/daily/` 的個股端點
**不是同一條路**。整批漏抓時 daily 的家數會掉，MI_INDEX 不會——差值就會爆開。

## ⚠ 為什麼現在只報告、不設門檻

2026-09-08 實測五天（breadth 只從 2026-09-01 起累積）：

    09-01  1067 / 1089  差 22        09-04  1074 / 1091  差 17
    09-02  1067 / 1092  差 25        09-07  1077 / 1095  差 18
    09-03  1071 / 1086  差 15

**差值不固定（15～25）**，因為兩邊的母體定義本來就不同：MI_INDEX 的「股票」
欄不含 ETF／權證／受益證券，而「四位數代號」這個近似會多收 DR 與部分證券。

**五個觀察值不足以訂帶寬。** 事後看資料再訂門檻，就是這個專案一路在防的
「事後才定門檻等於沒有門檻」。

★ 2026-09-08 更正：原本寫「等 30 天累積」——**那是錯的，歷史抓得到**。
`MI_INDEX` 吃 date 參數，2015 起都問得到；`market_breadth.csv` 只有五天是因為
那是 v6 才開始存的，**不是端點沒有歷史**。已改成 `feeds.py` 的 `breadth` feed
分批回補（daily.yml 每趟 200 天）。回補完成後樣本會是兩千多天，
**那時才有資格把帶寬寫死**，並在那次的 commit 裡說明依據。

唯一現在就成立、不必量的是**方向**：daily 的普通股家數應該 **≥** breadth 的
股票家數（後者的母體是前者的子集）。反過來就一定有問題，那一條可以現在就當
硬判準。
"""
import csv
import io
import os
import sys

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BREADTH = os.path.join(_ROOT, "history", "market_breadth.csv")
FEED = os.path.join(_ROOT, "universe", "breadth")   # feeds.py 回補的逐日檔
DAILY = os.path.join(_ROOT, "universe", "daily")
OUT = os.path.join(_ROOT, "meta", "_breadth_audit.csv")
MIN_SAMPLE = 30          # 帶寬要訂死之前至少要這麼多個交易日


def daily_common(day):
    """那一天日檔裡的上市普通股家數（四位數代號）。檔不在回 None。"""
    p = os.path.join(DAILY, f"{day}.csv")
    if not os.path.exists(p):
        return None
    n = 0
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = r.get("stock_id") or ""
            if r.get("market") == "twse" and c.isdigit() and len(c) == 4:
                n += 1
    return n


def main():
    if not os.path.exists(BREADTH):
        print(f"[breadth] 找不到 {BREADTH}", file=sys.stderr)
        return 1
    # ★ 兩個來源併集：`universe/breadth/`（feeds.py 回補，2015 起）
    #   與 `history/market_breadth.csv`（fetch.py 當日寫，2026-09-01 起）。
    #   同一天兩邊都有時以 feed 為準——它是逐日檔，不會被視窗截斷。
    src = {}
    if os.path.isdir(FEED):
        for fn in sorted(os.listdir(FEED)):
            if not fn.endswith(".csv"):
                continue
            with io.open(os.path.join(FEED, fn), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("date"):
                        src[r["date"]] = r
    with io.open(BREADTH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            src.setdefault(r.get("date", ""), r)
    rows = []
    if True:
        for r in [src[k] for k in sorted(src) if k]:
            tot = 0
            for k in ("up", "down", "flat"):
                v = (r.get(k) or "").replace(",", "").strip()
                if not v.isdigit():
                    tot = None
                    break
                tot += int(v)
            if tot is None:
                continue
            n = daily_common(r["date"])
            if n is None:
                continue
            rows.append((r["date"], tot, n, n - tot))

    print(f"[breadth] 可比對 {len(rows)} 個交易日"
          f"（來源：universe/breadth/ 回補 ＋ history/market_breadth.csv）")
    for d, b, n, gap in rows[-10:]:
        print(f"  {d}  MI_INDEX 股票 {b:,}｜日檔普通股 {n:,}｜差 {gap:+,}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "mi_index_stocks", "daily_common", "gap"])
        w.writerows(rows)
    print(f"[breadth] 寫出 {OUT}")

    rl = runlog.Run("breadth")
    rl.info("樣本", f"{len(rows)} 個交易日（帶寬要訂死至少要 {MIN_SAMPLE} 天）")
    if rows:
        gaps = [g for _, _, _, g in rows]
        d, b, n, g = rows[-1]
        rl.info("最新一天", f"{d}｜MI_INDEX 股票 {b:,}｜日檔普通股 {n:,}｜差 {g:+,}")
        rl.info("差值範圍", f"{min(gaps):+,} ~ {max(gaps):+,}")
        # ★ 唯一不必量就成立的硬判準：方向。
        #   MI_INDEX 的「股票」母體是日檔四位數普通股的子集，所以差值不該是負的。
        #   整批漏抓時日檔家數會掉、MI_INDEX 不會——差值就會翻負。
        neg = [(x[0], x[3]) for x in rows if x[3] < 0]
        rl.check("日檔的普通股家數 ≥ MI_INDEX 的股票家數", not neg,
                 ("翻負：" + "、".join(f"{d}({g})" for d, g in neg[:5])) if neg
                 else f"最小差 {min(gaps):+,}")
        # ⛔ 帶寬**不在這裡訂**。事後看資料再訂門檻等於沒有門檻——
        #    等樣本夠了再把數字寫死，並在那次的 commit 裡說明依據。
        if len(rows) < MIN_SAMPLE:
            rl.note(f"⚠ 樣本只有 {len(rows)} 天，**還不足以訂差值帶寬**。"
                    f"目前只驗方向，不驗大小。")
    else:
        rl.note("還沒有可比對的日子")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
