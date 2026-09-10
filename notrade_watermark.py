#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""notrade_watermark.py — 「這一天已經是新語意了嗎」的判準，**從資料自己算**。

## 這一支在答什麼

K線線 2026-09-10 13:00 提的條件（他們的閘門在回補期間會誤判）：

    A｜這一天這一檔**真的沒成交**  ← 市場事實，不該擋
    B｜這一天**還沒被回補到**      ← 資料缺陷，該擋

⛔ **在檔案上長得一模一樣**（都是「沒有那一列」）
⇒ 混雜期會把 A 誤判成 B ⇒ **大量冷門股被誤擋**，
⚠ 而誤擋不會有人抱怨（少推薦幾檔而已）⇒ 它會**安靜地跑完整段回補期**。

## ⭐ 判準：那一天的日檔裡**有沒有任何 `price_basis == '無成交'` 的列**

⇒ 有 ＝ 這一天已經用新語意重抓過 ＝ 「沒有那一列」就真的是 B（缺陷）。
⇒ 沒有 ＝ 還沒補到 ＝ 「沒有那一列」**不可判定**，不可以當缺陷。

⛔ **這不是台帳。** 它每一趟從 `data/universe/daily/` 全量重算、整份覆蓋，
沒有任何「上次跑到哪」的狀態——⇒ 不可能跟資料不一致。
（`--need-notrade` 續跑判準用的是**同一件事**：⭐ 續跑判準就是成功判準。）

⚠ 這個判準有一個已知的偽陰性，講清楚：
**某一天若全市場真的沒有任何一檔無成交，它會被判成「還沒補」。**
⇒ 量過：2,848 個可比日裡 `missing=0` 的有 **0 天**（`missing_rows.py`），
  ⇒ 實務上不會發生。⛔ 但別把它寫成「不可能」——那是把觀察寫成通則。

## 順帶回 K線線 Q1：「補完那輪會不會印哪幾檔列數變了、各多幾列」

會。`_notrade_by_stock.csv` 就是那份清單：一檔多幾列 ＝ 它有幾個無成交日。
⭐ 他們要這個是為了**知道重算範圍，而不是猜**——
⚠ 影響比 `cum_factor` 那次廣：列數變了會動到**每一個「近 N 個交易日」的視窗**。
"""
import csv
import io
import os
import sys
from collections import Counter

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DAILY = os.path.join(_ROOT, "universe", "daily")
OUT_DAY = os.path.join(_ROOT, "meta", "_notrade_days.csv")
OUT_STK = os.path.join(_ROOT, "meta", "_notrade_by_stock.csv")

DAY_HEADER = ["date", "new_semantics", "n_rows", "n_notrade",
              "n_notrade_twse", "n_notrade_tpex", "n_notrade_emerging"]
STK_HEADER = ["stock_id", "market", "n_notrade_days", "first", "last"]


def scan(daily_dir=None):
    """→ (每日 rows, 每檔 rows)。⛔ 抽成函式是為了讓 selftest 測得到。"""
    dd = daily_dir or DAILY
    if not os.path.isdir(dd):
        return [], []
    days = sorted(n[:-4] for n in os.listdir(dd) if n.endswith(".csv"))
    per_day, per_stock = [], {}
    for d in days:
        n_rows = 0
        by_mk = Counter()
        with io.open(os.path.join(dd, d + ".csv"), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                n_rows += 1
                # ⭐ 用 price_basis 判，⛔ 不用「close 是不是空的」——
                #   那一欄是正面標記，close 空不空只是它的副作用。
                if (r.get("price_basis") or "").strip() != "無成交":
                    continue
                mk = (r.get("market") or "").strip()
                by_mk[mk] += 1
                code = (r.get("stock_id") or "").strip()
                if not code:
                    continue
                e = per_stock.get(code)
                if e is None:
                    per_stock[code] = [code, mk, 1, d, d]
                else:
                    e[2] += 1
                    e[4] = d
        n_nt = sum(by_mk.values())
        per_day.append([d, "1" if n_nt else "0", str(n_rows), str(n_nt),
                        str(by_mk.get("twse", 0)), str(by_mk.get("tpex", 0)),
                        str(by_mk.get("emerging", 0))])
    return per_day, sorted(per_stock.values(), key=lambda e: (-e[2], e[0]))


def _write(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    rl = runlog.Run("notrade:水位（哪幾天已經是新語意）")
    per_day, per_stock = scan()
    if not per_day:
        rl.info("狀態", "data/universe/daily/ 不存在或沒有日檔")
        rl.check("有日檔可掃", False, "0 天")
        return rl.finish()

    _write(OUT_DAY, DAY_HEADER, per_day)
    _write(OUT_STK, STK_HEADER, per_stock)

    done = [r for r in per_day if r[1] == "1"]
    n_nt = sum(int(r[3]) for r in per_day)
    rl.info("可掃天數", f"{len(per_day):,} 天（{per_day[0][0]} ～ {per_day[-1][0]}）")
    rl.info("⭐ 已是新語意（該日有無成交列）",
            f"**{len(done):,} 天**"
            + (f"｜{done[0][0]} ～ {done[-1][0]}" if done else "｜（還沒有任何一天）"))
    rl.info("尚未補到（K線線的閘門對這些日子要標**不可判定**，⛔ 不是不通過）",
            f"{len(per_day) - len(done):,} 天")
    rl.info("無成交列總數", f"{n_nt:,} 筆｜涉及 {len(per_stock):,} 檔")
    if per_stock:
        rl.info("⭐ 列數變最多的 8 檔（回 K線線 Q1：這就是重算範圍）",
                "｜".join(f"{e[0]} +{e[2]}列" for e in per_stock[:8]))
    rl.info("兩份清單", "data/meta/_notrade_days.csv（逐日水位）／"
                        "_notrade_by_stock.csv（逐檔多幾列）")
    # ⛔ 這一支**不判成敗**：它是量測，不是抓取。
    #   回補做到哪裡是進度，不是錯誤——在這裡 check 會讓每一趟都紅到補完為止，
    #   然後這個 ✗ 就會被學會忽略（而它旁邊真正的 ✗ 也一起被忽略）。
    #   ⇒ 只有「連日檔都掃不到」才是真的失敗，那一條在上面。
    rl.check("兩份清單都寫出來了",
             os.path.exists(OUT_DAY) and os.path.exists(OUT_STK),
             f"{OUT_DAY}／{OUT_STK}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
