#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_hole_kinds.py — 驗「這個洞是哪一種」分得開。

⛔ 這一支要證明的是**一件會靜靜出錯的事**：
「相鄰兩筆日線隔了 N 個交易日」在資料上有**兩種**完全不同的成因，
而它們在「只看有收盤價的列」時**長得一模一樣**：

    ① 那幾天一列都沒有          ⇒ 真的停止交易
    ⭐ ② 那幾天每天都有列、`price_basis=無成交` ⇒ **市場開著，只是沒人買賣**

⚠ 分不開的表現**不是報錯**，是「每一個洞看起來都是斷點」
⇒ 2026-09-11 實測：4413 飛寶那 259 天全部是②，而它原本要被當成最長的斷點。
"""
import csv
import io
import os
import shutil
import sys
import tempfile

import hole_kinds as H

_ok = _bad = 0


def ck(name, cond, hint=""):
    global _ok, _bad
    if cond:
        _ok += 1
        print(f"  ok   {name}")
    else:
        _bad += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def main():
    sand = tempfile.mkdtemp(prefix="hk_")
    try:
        print("── ① classify：兩類要分得開 ──")
        # ⭐ ②：洞 100 天、每天都有列、全部無成交、0 天停牌
        ck("⭐ 每天都有列且全是無成交 ⇒ `notrade`（市場開著）",
           H.classify(100, 100, 100, 0, True) == "notrade",
           H.classify(100, 100, 100, 0, True))
        # ① 洞 100 天、一列都沒有、停牌 100 天
        ck("　一列都沒有、停牌完整覆蓋 ⇒ `halted`",
           H.classify(100, 0, 0, 100, True) == "halted",
           H.classify(100, 0, 0, 100, True))
        # ⛔ 真實案例：4415 台原藥 洞 156、洞中只有 1 列、停牌 155
        #   ⚠ 這一條**不區分順序**（155/156 也過 0.9，兩種順序都判 halted）——
        #     第一版我把它寫成順序的證據，⛔ 突變驗當場打掉那句。留著當一般正例。
        ck("　洞中只有 1 列、停牌 155 天 ⇒ `halted`（4415 台原藥實例）",
           H.classify(156, 1, 1, 155, True) == "halted",
           H.classify(156, 1, 1, 155, True))
        # ⭐⭐ 真正會分岔的：**兩邊都成立**（每天有列而且停牌覆蓋整段）⇒ 兩個來源矛盾
        ck("⭐⭐ 兩邊都成立時以**直接證據**為準 ⇒ `notrade`"
           "（⛔ 日檔說市場開著，公告表說停牌——採信日檔）",
           H.classify(100, 100, 100, 100, True) == "notrade",
           H.classify(100, 100, 100, 100, True))
        # ④ 6240 松崗：前段零成交 69 天、後段停牌 94 天，洞 163
        ck("　前段零成交後段停牌 ⇒ `mixed`（一段要拆成兩段）",
           H.classify(163, 69, 69, 94, True) == "mixed",
           H.classify(163, 69, 69, 94, True))
        ck("　一列都沒有、也沒停牌、而且**涵蓋得到** ⇒ `unexplained`（要查）",
           H.classify(50, 0, 0, 0, True) == "unexplained")
        ck("⛔ 同樣的情形但**涵蓋不到** ⇒ `uncovered`"
           "（⚠ 判不出來 ≠ 沒有；這個 0 不是結論）",
           H.classify(50, 0, 0, 0, False) == "uncovered")
        ck("⛔ 讀不到該檔的逐檔檔 ⇒ `no_perstock`，⚠ 不可以當成「那幾天沒有列」",
           H.classify(50, None, None, 0, True) == "no_perstock")

        print("── ② rows_in：兩端那兩天不算在洞裡 ──")
        d = os.path.join(sand, "stocks")
        os.makedirs(d)
        io.open(os.path.join(d, "4413.csv"), "w", encoding="utf-8").write(
            "date,stock_id,close,volume,price_basis\n"
            "2015-12-24,4413,16.50,5000,\n"            # ← 洞前最後一筆（有成交）
            "2015-12-25,4413,,0,無成交\n"
            "2015-12-28,4413,,0,無成交\n"
            "2015-12-29,4413,,0,無成交\n"
            "2017-01-17,4413,10.70,2000,\n")           # ← 洞後第一筆（有成交）
        n, nt = H.rows_in("4413", "2015-12-24", "2017-01-17", root=d)
        ck("⭐ 洞中有 3 列、3 列都是無成交"
           "（⛔ 含進兩端的話會變成 5／3，那兩天本來就有成交）",
           (n, nt) == (3, 3), f"{(n, nt)}")
        ck("　讀不到的檔回 (None, None)，⛔ 不是 (0, 0)",
           H.rows_in("9999", "a", "b", root=d) == (None, None))

        print("── ③ span_days：重疊判，⛔ 不是包含判 ──")
        sp = {"1785": [("2016-05-17", "2016-12-30", 158)]}
        ck("　停牌區間整段落在洞裡要算到",
           H.span_days(sp, "1785", "2016-05-16", "2017-01-03") == 158)
        # ⭐ 這一條才驗得到「重疊 vs 包含」：區間**比洞長**，兩端都超出去
        big = {"x": [("2016-01-01", "2017-12-31", 400)]}
        ck("⭐⭐ 停牌區間**比洞長**（兩端都超出）也要算到"
           "（⛔ 用包含判的話這種整段變 0，而長停牌本來就常常跨過洞）",
           H.span_days(big, "x", "2016-05-16", "2017-01-03") == 400,
           str(H.span_days(big, "x", "2016-05-16", "2017-01-03")))
        ck("　完全不重疊的算 0",
           H.span_days(sp, "1785", "2020-01-01", "2020-02-01") == 0)

        print("── ④ ⛔ 區間表讀不到／空殼：要大聲失敗，⚠ 不是「0 段停牌」 ──")
        miss = os.path.join(sand, "nope.csv")
        got, why = H.load_spans(miss)
        ck("⭐ 檔不在 ⇒ 回 None 而且說明裡講的是 **checkout**",
           got is None and "checkout" in why, why)
        empty = os.path.join(sand, "empty.csv")
        io.open(empty, "w", encoding="utf-8").write("market,stock_id,start,end,days,open_ended\n")
        got2, why2 = H.load_spans(empty)
        ck("⛔ 有表頭沒列的**空殼檔**也要擋"
           "（⚠ `os.path.exists` 會靜靜放行——第四點六的同一個陷阱）",
           got2 is None and "空殼" in why2, why2)
        io.open(empty, "a", encoding="utf-8").write("tpex,1785,2016-05-17,2016-12-30,158,0\n")
        got3, why3 = H.load_spans(empty)
        ck("　⚠ 正例：有列就要放行（⛔ 一個永遠擋的守門會被下一個人拿掉）",
           got3 is not None and got3.get("1785"), why3)

        print("── ⑤ covered_by：`chtm` 是**上櫃**的表 ──")
        ck("⛔ 上市（twse）一律判不出來（⚠ 那張表管不到上市）",
           not H.covered_by("2022-12-30", "twse", "2016-01-01"))
        ck("　上櫃、在涵蓋期內 ⇒ 判得出來",
           H.covered_by("2022-12-30", "tpex", "2016-01-01"))
        ck("⛔ 上櫃但超出回補前緣 ⇒ 判不出來"
           "（⚠ 這個 0 是「還沒補到」，不是「沒有停牌」）",
           not H.covered_by("2022-12-30", "tpex", "2024-09-05"))
    finally:
        shutil.rmtree(sand, ignore_errors=True)
    print(f"\n[selftest] 通過 {_ok}｜失敗 {_bad}")
    return 1 if _bad else 0


if __name__ == "__main__":
    sys.exit(main())
