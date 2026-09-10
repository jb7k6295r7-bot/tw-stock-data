#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_otc_exright_history.py — 驗 `exDailyQ` 的解析與守門。**不連外、不寫 repo。**

⛔ 四條分支，每一條都要證明它會擋下來：

  ① 正常：民國日期解得開、逗號去掉、名稱 trim
  ② ⛔⛔ **靜靜回今天**（GET 或日期不帶斜線時的真實行為）⇒ 整批拒收
     ⚠ 這是本支最重要的一條：拿到 3 筆會**看起來像成功**
  ③ 回 0 列 ⇒ 當失敗，⛔ 不是「這十一年沒有除權息」
  ④ 欄位對不上 ⇒ 講得出缺哪一個
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import otc_exright_history as H

TPE = timezone(timedelta(hours=8))
OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


F = ["除權息日期", "股票代號", "股票名稱", "除權息前收盤價", "除權息參考價", "權息值"]


def pack(rows, fields=None):
    return {"tables": [{"title": "除權除息計算結果表", "fields": fields or F,
                        "data": rows}]}


def main():
    real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "meta", "otc_exright_history.csv")
    before = os.path.exists(real)

    rows, note = H.parse(pack([
        ["104/06/15", "6104", "創惟   ", "1,234.00", "1,200.00", "息"],
        ["2026/09/09", "8096", "擎亞", "45.50", "44.00", "權息"],
    ]), "2015-01-01", "2026-09-09")
    ck("① 兩列都解得出來", len(rows) == 2, note)
    ck("① 民國 104/06/15 → 2015-06-15",
       rows and rows[0][0] == "2015-06-15", str(rows[:1]))
    ck("① 西元 2026/09/09 也吃", any(r[0] == "2026-09-09" for r in rows), str(rows))
    ck("① 逗號去掉、名稱 trim",
       rows and rows[0][3] == "1234.00" and rows[0][2] == "創惟", str(rows[:1]))

    # ② ⛔⛔ 靜靜回今天：只回最近兩天的資料
    t0 = datetime.now(TPE).strftime("%Y/%m/%d")
    t1 = (datetime.now(TPE) + timedelta(days=1)).strftime("%Y/%m/%d")
    rows2, note2 = H.parse(pack([[t0, "6104", "創惟", "1", "1", "息"],
                                 [t1, "8096", "擎亞", "1", "1", "息"]]),
                           "2015-01-01", "2026-09-09")
    ck("② ⛔ 只回「今天～明天」時整批拒收（⚠ 這裡會看起來像成功）",
       not rows2, note2)
    ck("② 而且訊息點名那個陷阱",
       "靜靜回今天" in note2 or "不帶斜線" in note2, note2)

    # ③ 0 列
    rows3, note3 = H.parse(pack([]), "2015-01-01", "2026-09-09")
    ck("③ 0 列 ⇒ 當失敗，⛔ 不是「這十一年沒有除權息」",
       not rows3 and "不是" in note3, note3)

    # ④ 欄位對不上
    rows4, note4 = H.parse(
        pack([["104/06/15", "6104", "創惟"]],
             fields=["除權息日期", "股票代號", "股票名稱"]),
        "2015-01-01", "2026-09-09")
    ck("④ 欄位對不上 ⇒ 講得出缺哪一個",
       not rows4 and "前收盤" in note4 and "參考價" in note4, note4)

    # ⑤ _iso 的邊界
    ck("⑤ _iso 認不出來回 None（⛔ 不亂猜）",
       H._iso("abc") is None and H._iso("115/13/01") is None
       and H._iso("115/09/09") == "2026-09-09",
       f"{H._iso('abc')} {H._iso('115/13/01')} {H._iso('115/09/09')}")

    ck("★ 沒有動到 repo 真的判準檔", os.path.exists(real) == before)
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
