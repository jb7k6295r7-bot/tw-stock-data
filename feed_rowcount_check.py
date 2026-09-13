#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feed_rowcount_check.py — 逐日 feed 的**落地閘門**：每一天的列數跟鄰近幾天比。
**只讀 repo，不連外。**

市場情報分析線 2026-09-13 14:00 的建議，判準抽在 `neighbor_floor.py`
（⭐ 跟 `mops_history.revenue_complete` 同一份實作）。理由與形狀見那支的檔頭。

## ⛔ 事件型的 feed **不可以**套這道

`exright`／`otcexright`／`reduce`／`parvalue`／`etfsplit`／`stophalt` 的每日列數
本來就是 1~44 之間跳（變異係數 1.9）⇒ 套上去會天天紅，**然後被學會忽略**。
⇒ 判準不是寫死清單，是**量出來的**：`min_median`（`neighbor_floor`）自動把
「鄰近中位數 < 30」的那些排除掉，⚠ 而排除掉哪些會**印出來**，⛔ 不是靜靜跳過。

## ⭐ 週六（補行交易日）要單獨一格

全庫 2,850 個交易日裡有 **8 個週六**（2016-01-30、2016-06-04、2016-09-10、
2017-02-18、2017-06-03、2017-09-30、2018-03-31、2018-12-22）。
⚠ 那幾天的參與者本來就少：`otcinst` 2016-06-04 只有 189 列（鄰近中位 458）。
⛔ 把它們算成殘缺 ⇒ 這道閘門一上線就有 4 個誤報。

## 校準（2026-09-13 全庫實測，10 支逐日 feed × 2,850 天）

```
floor 0.5、排除週六之後：per／sbl／margin／chtm／marginratio／otcper／
otcmargin／breadth／otcinst／tib **全部 0 筆** ⇒ 誤報率 0 / 25,650
```
⭐ 而它抓得到真的：`2026-08_twse` 123 列 vs 鄰月 992 ⇒ 比值 0.12。
"""
import argparse
import datetime as dt
import os
import sys

import neighbor_floor as NF
import runlog

_HERE = os.path.dirname(os.path.abspath(__file__))
UNIVERSE = os.path.join(_HERE, "data", "universe")
OUT = os.path.join(_HERE, "data", "meta", "_feed_rowcount_check.csv")


def day_rows(path):
    """→ 該日檔的資料列數（扣表頭）；讀不到回 None。⛔ 用 bytes 數換行，2,850 檔要快。"""
    try:
        with open(path, "rb") as f:
            n = f.read().count(b"\n") - 1
    except OSError:
        return None
    return max(n, 0)


def is_saturday(day):
    """→ 這一天是不是週六（補行交易日）。⭐ 只有這一份實作。"""
    try:
        return dt.date.fromisoformat(day).weekday() == 5
    except ValueError:
        return False


def scan_feed(d, floor=NF.FLOOR):
    """→ (逐筆疑似殘缺, 統計 dict)。⛔ 只讀，不寫。"""
    days = sorted(x[:-4] for x in os.listdir(d) if x.endswith(".csv")
                  and not x.startswith("_"))
    rows = [day_rows(os.path.join(d, f"{x}.csv")) for x in days]
    bad, stat = [], {"天數": len(days), "疑似殘缺": 0, "週六（另計）": 0, "沒判": 0}
    for i, day in enumerate(days):
        n = rows[i]
        if n is None:
            continue
        short, med, why = NF.is_short(n, NF.neighbors(rows, i), floor=floor)
        if why:
            stat["沒判"] += 1
            stat["不判的原因"] = why
            continue
        if not short:
            continue
        if is_saturday(day):
            stat["週六（另計）"] += 1
            continue
        stat["疑似殘缺"] += 1
        bad.append({"feed": os.path.basename(d), "date": day, "rows": str(n),
                    "neighbor_median": f"{med:g}",
                    "ratio": f"{n / med:.3f}" if med else ""})
    return bad, stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--floor", type=float, default=NF.FLOOR)
    a = ap.parse_args()
    rl = runlog.Run("feed_rowcount")
    rl.info("⭐ 這一支在驗什麼",
            "每個逐日 feed 的**每一天**列數 vs 鄰近幾天的中位數"
            "（⛔ 不是看區間端點——中間塌掉在那裡完全看不到）")

    allbad, checked, skipped = [], [], []
    for name in sorted(os.listdir(UNIVERSE)) if os.path.isdir(UNIVERSE) else []:
        d = os.path.join(UNIVERSE, name)
        if not os.path.isdir(d):
            continue
        bad, st = scan_feed(d, a.floor)
        if st["天數"] == 0:
            continue
        # ⭐ 「這一支整支沒判」要**大聲印**，⛔ 不可以跟「判過、沒事」長得一樣
        if st["沒判"] == st["天數"]:
            skipped.append(f"{name}（{st['天數']} 天：{st.get('不判的原因', '?')}）")
            continue
        checked.append(name)
        allbad += bad
        if bad or st["週六（另計）"]:
            rl.info(name, f"{st['天數']} 天｜⛔ 疑似殘缺 {st['疑似殘缺']}"
                          f"｜週六另計 {st['週六（另計）']}")

    rl.info("有判的 feed", f"{len(checked)} 支：{'、'.join(checked)}")
    # ⛔ 這一行要寫成不會被讀成「驗過了」的樣子
    rl.info("⚠ **整支沒判**的 feed（量太小，⛔ 不是驗過沒事）",
            f"{len(skipped)} 支：{'、'.join(skipped) if skipped else '無'}")

    # ⭐ 判準要能自己講出它在這一批抓到幾個正例（第七點）
    rl.check("⭐ 這道閘門真的掃到東西了（⛔ 掃到 0 支跟全部通過長得一樣）",
             len(checked) >= 5, f"有判的 feed {len(checked)} 支")
    rl.check("逐日 feed 沒有列數塌掉的日子",
             not allbad,
             f"⛔ {len(allbad)} 天：" + "、".join(
                 f"{x['feed']} {x['date']} {x['rows']}列(鄰中位{x['neighbor_median']})"
                 for x in allbad[:8]) if allbad else "0 天")

    if a.write and allbad:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        import csv
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(allbad[0]))
            w.writeheader()
            w.writerows(allbad)
        back = list(csv.DictReader(open(OUT, encoding="utf-8")))
        rl.check("清單寫得進去而且讀得回來", len(back) == len(allbad),
                 f"寫 {len(allbad)}、讀回 {len(back)}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
