#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_chtm.py — 驗上櫃「變更交易／分盤／管理股票／停止交易」的解析。

⚠ 假回應**照真回應的形狀做**（`chtm_probe.py` 2026-09-10 於 Actions 的實測）：
**10 欄**（⛔ 不是情報分析線信裡說的 8 欄）、旗標是**全形 Ｙ**（U+FF39）、
撮合時間是**零填三位的字串**（`"030"`／`"045"`）。

⭐ 要證明的重點：

    ① ⛔⛔ 全形 Ｙ：寫 `== "Y"`（半形）會**一筆都不匹配，而且不報錯**
       ——整欄變成「沒有任何一檔被標記」。這一節用**反向**釘住它。
    ② ⭐ 判準是「**非空**」不是 `== "Ｙ"`（K線線 20:20 抽的通則：
       分類欄要當「集合」讀不要當「值」讀；⛔ `==` 系統性地放行最該擋的那批）
    ③ ⛔ 撮合時間**原樣存字串**：轉成整數就分不出「沒有值」與「0 分鐘」
    ④ 欄名逐字比對 ⇒ 官方改欄名就拒收
"""
import sys

import feeds as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


Y = "Ｙ"                      # ⭐ 全形 Ｙ，實測值
LINK = "/zh-tw/announce/market/announce/detail.html?docId=MTA=&content_file=XX"
MOPS = "https://mops.twse.com.tw/mops/#/web/t211sb01_q1"
# ⚠ 逐字照 2026-09-10 實測（104/01/05 那一批）
ROWS = [["3126", "信億", Y, Y, "", "030", "", Y, LINK, MOPS],
        ["3066", "李洲", Y, "", "", "", "", Y, "", MOPS],
        ["1107", "建台", "", "", Y, "045", "", "", "", MOPS],
        ["3085", "久大", "", "", "", "", Y, Y, "", MOPS]]
H = F.FEEDS["chtm"]["header"]
DAY = "2015-01-05"


def tp(fields=None, data=None, **top):
    d = {"stat": "ok", "date": "20150105",
         "tables": [{"fields": F.CHTM_FIELDS if fields is None else fields,
                     "data": ROWS if data is None else data}]}
    d.update(top)
    return d


def main():
    print("① 照真形狀（10 欄）的回應：解得出來")
    out, note = F.parse_chtm(tp(), DAY)
    ck("  4 列", len(out) == 4, f"{len(out)}｜{note}")
    ck("  每一列長度 = header 長度",
       all(len(r) == len(H) for r in out), f"{H}｜{out[:1]}")
    m = {r[1]: dict(zip(H, r)) for r in out}
    ck("  日期是我方傳進去的那一天", all(r[0] == DAY for r in out), str(out[:1]))
    ck("  ⭐ 3126 信億：變更交易 1、分盤 1、撮合 030",
       (m["3126"]["changed"], m["3126"]["split_auction"],
        m["3126"]["match_cycle_min"]) == ("1", "1", "030"), str(m.get("3126")))
    ck("  ⭐ 1107 建台：管理股票 1、撮合 045、變更交易 0",
       (m["1107"]["managed"], m["1107"]["match_cycle_min"],
        m["1107"]["changed"]) == ("1", "045", "0"), str(m.get("1107")))
    ck("  ⭐ 3085 久大：停止交易 1", m["3085"]["halted"] == "1", str(m.get("3085")))
    ck("  說明講得出四個計數與撮合時間的相異值",
       "變更交易 2" in note and "030" in note and "045" in note, note)

    print("② ⛔⛔ 那個 Ｙ 是**全形**（U+FF39）——半形比對會一筆都不中")
    ck("  ⭐ 常數就是全形", F.CHTM_YES == "Ｙ", repr(F.CHTM_YES))
    ck("  ⚠ 而它**不等於**半形 'Y'", F.CHTM_YES != "Y")
    # ⛔ 反向：把半形比對重現一次，證明它真的會全滅
    half = sum(1 for r in ROWS if str(r[2]) == "Y")
    real = sum(1 for r in out if r[3] == "1")
    ck("  ⭐⭐ 半形 `== \"Y\"` 在同一批資料上抓到 **0** 列，"
       "我方判準抓到 2 列（⇒ 那種寫法會讓整欄靜默變空）",
       half == 0 and real == 2, f"半形 {half}｜我方 {real}")

    print("③ ⭐ 判準是「非空」，⛔ 不是 `== \"Ｙ\"`（分類欄當集合讀）")
    odd = [["3126", "信億", "Ｙ*", "ｖ", "", "030", "1", "Ｙ", "", MOPS]]
    out3, _ = F.parse_chtm(tp(data=odd), DAY)
    a = dict(zip(H, out3[0])) if out3 else {}
    ck("  複合值 `Ｙ*` ⇒ 1", a.get("changed") == "1", str(a))
    ck("  別的字母 `ｖ` ⇒ 1（⚠ 官方哪天改字元也擋得住）",
       a.get("split_auction") == "1", str(a))
    ck("  數字 `1` ⇒ 1", a.get("halted") == "1", str(a))
    eq = sum(1 for r in odd if str(r[2]) == F.CHTM_YES)
    ck("  ⭐ 等號比對在這一批抓到 0，非空判準抓到 1",
       eq == 0 and a.get("changed") == "1", f"等號 {eq}")
    ck("  ⚠ 而真的空白仍然是 0",
       dict(zip(H, F.parse_chtm(tp(data=[["3126", "x", "", " ", "", "", "",
                                          "", "", MOPS]]), DAY)[0][0]))
       ["changed"] == "0")

    print("④ ⛔ 撮合時間**原樣存字串**（轉整數就分不出「沒有值」與「0 分鐘」）")
    vals = {r[6] for r in out}
    ck("  是 '030' 不是 30 也不是 '30'", "030" in vals, str(vals))
    ck("  ⛔ 沒有撮合時間的那些存**空字串**，不是 '0'",
       "" in vals and "0" not in vals, str(vals))
    ck("  ⚠ 型別是 str（⇒ 零填不會掉）",
       all(isinstance(r[6], str) for r in out))

    print("⑤ ⛔ 欄名逐字比對：8 欄的舊猜測要被拒收")
    # ⚠ 情報分析線信裡列的就是這 8 欄（漏了兩個連結欄）
    #   ⇒ 這一節同時釘住「我方實測 10 欄」這件事。
    eight = F.CHTM_FIELDS[:8]
    out5, note5 = F.parse_chtm(tp(fields=eight,
                                  data=[r[:8] for r in ROWS]), DAY)
    ck("  0 列", not out5, str(out5))
    ck("  說明講得出實際看到的欄位", "拒收" in note5, note5)
    ck("  ⭐ 而 10 欄那一批**通過**（否則這節等於在測「永遠拒收」）",
       len(F.parse_chtm(tp(), DAY)[0]) == 4)

    print("⑥ ⛔ 這些不會炸、也不會混進來")
    out6, note6 = F.parse_chtm({"stat": "ok"}, DAY)
    ck("  沒有表 ⇒ 0 列且說明有頂層鍵", not out6 and "stat" in note6, note6)
    ck("  ⛔ 被擋回字串也不炸", not F.parse_chtm("<html>", DAY)[0])
    out6c, _ = F.parse_chtm(tp(data=ROWS + [["合計", "4", "", "", "", "", "",
                                             "", "", ""],
                                            ["", "", Y, "", "", "", "", "",
                                             "", ""]]), DAY)
    ck("  合計列與空股號被丟掉（還是 4 列）", len(out6c) == 4, str(len(out6c)))
    ck("  ⛔ 短列不會 IndexError",
       not F.parse_chtm(tp(data=[["3126", "x", Y]]), DAY)[0])

    print("⑦ URL：⛔ 民國斜線（實測用的就是這個）")
    u = F.FEEDS["chtm"]["urls"]("2015-01-05")[0]
    ck("  帶 date=104/01/05", "date=104/01/05" in u, u)
    ck("  ⚠ 不是西元", "2015/01/05" not in u, u)
    ck("  今天那一天也換得對",
       "date=115/09/10" in F.FEEDS["chtm"]["urls"]("2026-09-10")[0],
       F.FEEDS["chtm"]["urls"]("2026-09-10")[0])
    ck("  ⚠ 而 `known` 是 False（⛔ 用母體濾掉等於把最該擋的那些濾掉）",
       F.FEEDS["chtm"]["known"] is False)

    print(f"\n{OK} ok, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
