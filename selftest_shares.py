#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_shares.py — 離線驗 shares_check 的守門，**尤其是那道日期驗證**。

⛔ 這一支要逼出來的四條分支：

  ① 正常：欄位對得上、日期對得上 ⇒ 解析得出列
  ② ⛔⛔ **端點靜靜回「今天」**（日期格式寫錯時的真實行為）⇒ 必須整批拒收
     ⚠ 沒有這道驗證的話，回補歷史時每天都拿到今天的數字，而且看起來完全正常
  ③ 回 0 列 ⇒ 當失敗，⛔ 不是「那天沒有股票」
  ④ 欄位對不上 ⇒ 講得出缺哪一個，不猜別的欄

⭐ 每一條都要**證明它會擋下來**，不是只證明正常情況會過。
"""
import io
import json
import os
import sys

import shares_check as S

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


FIELDS = ["排名", "股票代號", "股票名稱", "發行股數", "收盤價", "市值(佰萬元)"]


def payload(roc, rows, fields=None):
    return {"stat": "ok", "date": roc,
            "tables": [{"title": f"{roc} 個股市值排行",
                        "fields": fields or FIELDS, "data": rows}]}


def main():
    real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "meta", "shares_official_tpex.csv")
    before = os.path.exists(real)

    # ① 正常
    good = payload("115/09/09",
                   [[1, "6104", "創惟", "91,129,107", "92.50", "8,429"],
                    [2, "8921", "沈氏", "1,000,000", "10.00", "10"]])
    rows, note = S.parse(good, "2026-09-09")
    ck("① 正常回應解析得出兩列", len(rows) == 2, note)
    ck("① 逗號有拿掉、日期填成 ISO",
       rows and rows[0][3] == "91129107" and rows[0][0] == "2026-09-09",
       str(rows[:1]))

    # ② ⛔⛔ 端點靜靜回「今天」——我請求 2015-01-05，它回 115/09/09
    rows2, note2 = S.parse(good, "2015-01-05")
    ck("② ⛔ 回應講的是別天時**整批拒收**（不是照收）", not rows2, note2)
    ck("② 而且訊息講得出那個陷阱",
       "靜靜回今天" in note2 or "沒有講出我請求的日期" in note2, note2)

    # ③ 0 列
    rows3, note3 = S.parse(payload("115/09/09", []), "2026-09-09")
    ck("③ 回 0 列 ⇒ 當失敗，⛔ 不是「那天沒有股票」",
       not rows3 and "0 列當失敗" in note3, note3)

    # ④ 欄位對不上
    rows4, note4 = S.parse(
        payload("115/09/09", [[1, "6104", "創惟", "1"]],
                fields=["排名", "股票代號", "股票名稱", "成交量"]),
        "2026-09-09")
    ck("④ 欄位對不上 ⇒ 講得出缺哪一個",
       not rows4 and "缺" in note4 and "shares" in note4, note4)

    # ⑤ roc_slash 的兩端
    ck("⑤ 2026-09-09 → 115/09/09", S.roc_slash("2026-09-09") == "115/09/09",
       S.roc_slash("2026-09-09"))
    ck("⑤ 2015-01-05 → 104/01/05", S.roc_slash("2015-01-05") == "104/01/05",
       S.roc_slash("2015-01-05"))

    ck("★ 沒有動到 repo 真的累積檔", os.path.exists(real) == before)
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
