#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 crypto_funding.py 的判準。⛔ 離線：餵合成 zip，不連網。

⭐ 要釘住的是三件「壞掉時不報錯」的事：
  ① 表頭不是逐字那三欄 ⇒ 必須丟錯（⛔ 不可以默默照位置讀）
  ② 月份產生器：跨年要對、上限要含（⛔ 少一個月不會報錯）
  ③ 間隔組成照實數（SOL 2022-11 那種 8／4／2 混合）
"""
import io
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crypto_funding as C

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok     " + name)
    else:
        FAIL += 1
        print("  ✗      " + name + ("｜" + hint if hint else ""))


def mkzip(text, name="X-fundingRate-2022-11.csv"):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(name, text)
    return b.getvalue()


print("§一　表頭逐字")
rows, content = C.parse_month(mkzip("calc_time,funding_interval_hours,last_funding_rate\n"
                                    "1667260800000,8,-0.00010000\n1667289600000,4,0.00002000\n"))
ck("逐字表頭 ⇒ 讀得出 2 列", len(rows) == 2 and rows[0][0] == "1667260800000")
for bad in ("calc_time,interval,last_funding_rate\n1,8,0\n",
            "funding_time,funding_interval_hours,last_funding_rate\n1,8,0\n",
            "1667260800000,8,-0.0001\n"):
    try:
        C.parse_month(mkzip(bad))
        ck("表頭錯 ⇒ 要丟錯：%r" % bad[:30], False)
    except ValueError:
        ck("表頭錯 ⇒ 丟錯：%r" % bad[:30], True)
try:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("a.csv", "calc_time,funding_interval_hours,last_funding_rate\n")
        z.writestr("b.csv", "calc_time,funding_interval_hours,last_funding_rate\n")
    C.parse_month(b.getvalue())
    ck("zip 裡兩個 csv ⇒ 要丟錯", False)
except ValueError:
    ck("zip 裡兩個 csv ⇒ 丟錯（⛔ 不挑一個讀）", True)

print("\n§二　月份產生器")
ms = list(C.months((2021, 2)))
ck("2020-01 ~ 2021-02 共 14 個月、含上限", len(ms) == 14 and ms[0] == (2020, 1) and ms[-1] == (2021, 2), str(ms[-2:]))
ck("跨年接得上（2020-12 之後是 2021-01）", (2020, 12) in ms and ms[ms.index((2020, 12)) + 1] == (2021, 1))

print("\n§三　間隔組成")
rows = [["1", "8", "0"]] * 64 + [["2", "4", "0"]] * 2 + [["3", "2", "0"]] * 99
ck("{8:64,4:2,2:99} 照實數", C.interval_mix(rows) == '{"2":99,"8":64,"4":2}', C.interval_mix(rows))

print("\n[selftest] 通過 %d｜失敗 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
