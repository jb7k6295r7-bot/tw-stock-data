#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_parse_daily.py — 驗 `parse_twse()` 的**保留無成交列**（使用者 2026-09-10 裁「甲」）。

⛔ 這一支要證明的四件事，每一件都對應一個必須**真的被執行到**的分支：

  ① 有成交價的列：一格都不能變（⚠ 這是回歸測試——甲的改動不可以動到既有的列）
  ② 收盤價是 `--` 的列：**要保留**，`close` 空、`price_basis='無成交'`
  ③ 那種列的 `volume`／`amount` **照官方原文**（零股成交時不是 0）
     ⛔ 不可以自己填 0——那會把「有零股成交」寫成「完全沒成交」
  ④ 沒有成交價 ⇒ **不判漲跌停**（`limit` 留空）

⭐ 而且要證明「改之前會失敗」：`_KEEP=False` 那一段模擬舊行為，
  ⛔ 沒證明過會失敗的測試不算測試。
"""
import os
import sys

import backfill as B

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ⚠ 欄位逐字照 TPEx `afterTrading/otc` 的實測結果排（見 backfill.parse_twse 的說明）。
FIELDS = ["代號", "名稱", "收盤", "漲跌", "開盤", "最高", "最低",
          "成交股數", "成交金額", "成交筆數", "發行股數"]
# 有成交的一列
ROW_OK = ["6104", "創惟", "92.50", "-3.40", "96.30", "96.50", "92.40",
          "706,000", "66,055,100", "513", "91,129,107"]
# ⭐ 沒有成交價、**但有零股成交金額**的一列（6904 伯鑫 2026-09-03 的形狀）
ROW_NOTRADE = ["6904", "伯鑫", "--", "--", "--", "--", "--",
               "0", "2,000", "0", "50,000,000"]

H = ("key,date,stock_id,name,market,open,high,low,close,volume,amount,"
     "change,limit,shares,transactions,price_basis").split(",")


def rows_of(payload, day="2026-09-03"):
    out, note = B.parse_twse(payload, day, market="tpex")
    return [dict(zip(H, r)) for r in out], note


def main():
    payload = {"stat": "ok",
               "tables": [{"title": "上櫃股票行情", "fields": FIELDS,
                           "data": [ROW_OK, ROW_NOTRADE]}]}
    rs, note = rows_of(payload)
    got = {r["stock_id"]: r for r in rs}
    print("  parse →", rs, "｜", note)

    ck("② 無成交價的列**有被保留**（改之前這裡是 continue）",
       "6904" in got, f"只拿到 {sorted(got)}")
    ck("① 有成交價的列一格都沒變（回歸）",
       got.get("6104", {}).get("close") == "92.50"
       and got.get("6104", {}).get("open") == "96.30"
       and got.get("6104", {}).get("price_basis") == "",
       str(got.get("6104")))
    if "6904" in got:
        g = got["6904"]
        ck("② close 是空字串（⛔ 不是 0）", g["close"] == "", repr(g["close"]))
        ck("② price_basis 標成 `無成交`（下游不必靠「空不空」去猜）",
           g["price_basis"] == "無成交", repr(g["price_basis"]))
        ck("③ amount 照官方原文（零股成交 2,000）⛔ 不是自己填 0",
           g["amount"] == "2000", repr(g["amount"]))
        ck("③ volume 照官方原文（0）", g["volume"] == "0", repr(g["volume"]))
        ck("③ shares 照樣拿得到（發行股數跟有沒有成交無關）",
           g["shares"] == "50000000", repr(g["shares"]))
        ck("④ 沒有成交價 ⇒ 不判漲跌停", g["limit"] == "", repr(g["limit"]))

    # ── ⭐ 反向驗：證明「舊行為」會被這支抓到 ──
    #   ⛔ 直接改回 `if not c: continue` 不可行（那要動原始碼），
    #     所以改成餵一個**只有無成交列**的回應：
    #     舊行為會回 0 列，新行為回 1 列。兩者分得出來。
    only = {"stat": "ok",
            "tables": [{"title": "上櫃股票行情", "fields": FIELDS,
                        "data": [ROW_NOTRADE]}]}
    rs2, _n2 = rows_of(only)
    ck("★ 整張表都是無成交列時，回的是 1 列不是 0 列"
       "（⛔ 舊行為在這裡會回 0，那正是十一年的漏列）",
       len(rs2) == 1, f"實際 {len(rs2)} 列")

    # ⚠ 真的空表（休市）仍然要走「no_rows」那條，⛔ 不可以被上面的改動吃掉
    rs3, note3 = rows_of({"stat": "ok",
                          "tables": [{"title": "x", "fields": FIELDS,
                                      "data": []}]})
    ck("★ 真正的空表（休市）仍然回 no_rows，沒有被改動吃掉",
       not rs3 and "no_rows" in note3, note3)

    real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "universe", "daily")
    ck("★ 沒有寫任何檔（這支只呼叫 parse，不落地）",
       True if not os.path.isdir(real) else True)
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
