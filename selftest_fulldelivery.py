#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_fulldelivery.py — 驗變更交易（全額交割）名單的解析。

⛔ 這一支存在的理由是 K線線的閘門有一列**假裝有在擋**：
他們的前置閘門寫著「全額交割股」，而我方全文查「全額交割」**0 次**
⇒ 那一列**過不過都一樣**，而下游會以為過了關。

⚠ 假回應**照真回應的形狀做**（`delist_probe.py` 2026-09-09 於 Actions 的實測）：
3 欄、`["1213","大飲","  "]` 這種**兩個空白**、標記股是 `"**"`。

⭐ 要證明的重點：

    ① `**` ⇒ `split_auction=1`；**兩個空白** ⇒ `0`（⛔ 不是空字串、不是原文）
    ② ⭐ 判準是「**含 `*`**」而不是 `== "**"`
       ——⛔ 那是借券那件才學到的：分類欄可能是複合的，等號比對會漏掉。
       這一節用**反向**證明：等號比對在同一批假回應上會少抓一列。
    ③ 欄名逐字比對 ⇒ 官方改欄名就**拒收**（第 3 欄的欄名本身就是符號說明）
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


# ⚠ 逐字照 2026-09-09 實測（`delist_probe.py` 的輸出）
ROWS = [["1213", "大飲", "  "],
        ["2314", "台揚", "**"],
        ["4104", "佳醫", "  "]]
H = F.FEEDS["fulldelivery"]["header"]
DAY = "2026-09-09"


def tw(fields=None, data=None, **top):
    d = {"stat": "OK", "date": "20260909", "total": 3,
         "title": "115年09月09日 變更交易方法有價證券",
         "tables": [{"title": "變更交易方法有價證券",
                     "fields": F.FULLDEL_FIELDS if fields is None else fields,
                     "data": ROWS if data is None else data}]}
    d.update(top)
    return d


def main():
    print("① 照真形狀的回應：解得出來，欄位對得上 header")
    out, note = F.parse_fulldelivery(tw(), DAY)
    ck("  3 列", len(out) == 3, f"{len(out)}｜{note}")
    ck("  每一列的長度 = header 長度",
       all(len(r) == len(H) for r in out), f"{H}｜{out[:1]}")
    a = dict(zip(H, out[0])) if out else {}
    ck("  日期是**我方傳進去的那一天**（⛔ 不是官方回的 20260909 字串）",
       a.get("date") == DAY, str(a.get("date")))
    ck("  股號、股名都在", a.get("stock_id") == "1213" and a.get("name") == "大飲",
       str(out[:1]))
    ck("  說明講得出兩個數字", "3 檔" in note and "1 檔" in note, note)

    print("② ⭐ `**` ⇒ 1，**兩個空白** ⇒ 0")
    m = {r[1]: r[3] for r in out}
    ck("  2314 台揚（`**`）= '1'", m.get("2314") == "1", str(m))
    ck("  1213 大飲（兩個空白）= '0'", m.get("1213") == "0", str(m))
    ck("  ⛔ 存的是 1/0 不是原文（原文是空白，CSV 讀回來分不出「空白」與「沒有值」）",
       "  " not in {r[3] for r in out}, str({r[3] for r in out}))
    ck("  ⛔ 也不是空字串", all(r[3] in ("0", "1") for r in out),
       str([r[3] for r in out]))

    print("③ ⭐ 反向：判準若寫成 `== \"**\"` 會漏掉哪些")
    # ⚠ 官方在別的表用過 `*`（單星）與 `**`＋其他字的複合寫法。
    #   ⛔ 這一節不是假設——借券那件（`note == 'X'` 漏掉 55 列 `XV`）就是同一個形狀：
    #     **一個分類欄裡放了不只一個值，等號比對只認得其中一種。**
    odd = [["1213", "大飲", "*"],
           ["2314", "台揚", "** "],
           ["4104", "佳醫", "  "]]
    out3, _ = F.parse_fulldelivery(tw(data=odd), DAY)
    got = {r[1]: r[3] for r in out3}
    ck("  單星 `*` ⇒ 1（含 `*` 判準抓得到）", got.get("1213") == "1", str(got))
    ck("  `** ` 帶尾空白 ⇒ 1", got.get("2314") == "1", str(got))
    ck("  真的空白 ⇒ 0", got.get("4104") == "0", str(got))
    eq_hits = sum(1 for r in odd if str(r[2]) == "**")
    star_hits = sum(1 for r in out3 if r[3] == "1")
    ck("  ⭐ 等號比對只會抓到 0 列、含 `*` 抓到 2 列 ⇒ 這條判準有在做事",
       eq_hits == 0 and star_hits == 2, f"等號 {eq_hits}｜含星 {star_hits}")

    print("④ ⛔ 欄名逐字比對：改一個字就拒收（⇒ 符號可能也改了）")
    bad = ["證券代號", "證券名稱", "分盤集合競價"]          # 拿掉「(以**表示)」
    out4, note4 = F.parse_fulldelivery(tw(fields=bad), DAY)
    ck("  0 列", not out4, str(out4))
    ck("  說明講得出實際看到的欄位", "拒收" in note4 and "分盤集合競價" in note4, note4)
    out4b, note4b = F.parse_fulldelivery(
        tw(fields=["證券代號", "證券名稱"], data=[["1213", "大飲"]]), DAY)
    ck("  少一欄也拒收", not out4b, note4b)
    ck("  ⭐ 而正常的那一批**通過**了（否則這一節等於在測「永遠拒收」）",
       len(F.parse_fulldelivery(tw(), DAY)[0]) == 3)

    print("⑤ ⛔ 沒有表 ⇒ 拒收，而且說明講得出頂層鍵（不是「解析失敗」四個字）")
    out5, note5 = F.parse_fulldelivery({"stat": "OK", "total": 0}, DAY)
    ck("  0 列", not out5)
    ck("  說明有頂層鍵", "stat" in note5 and "total" in note5, note5)
    out5b, note5b = F.parse_fulldelivery("<html>428</html>", DAY)
    ck("  ⛔ 被 CDN 擋回字串也不會炸（回的是 str 不是 dict）", not out5b, note5b)
    ck("  說明講得出型別", "str" in note5b, note5b)

    print("⑥ 非個股列（合計／說明）不進來")
    out6, _ = F.parse_fulldelivery(
        tw(data=ROWS + [["合計", "3", ""], ["", "", "**"]]), DAY)
    ck("  還是 3 列（`合計` 與空股號都被丟掉）", len(out6) == 3, str(out6))
    out6b, _ = F.parse_fulldelivery(tw(data=[["1213", "大飲"]]), DAY)
    ck("  ⛔ 短列（只有 2 格）被丟掉，不會 IndexError", not out6b)

    print("⑦ `known` 過濾（feed 設 known=False，但參數本身要能用）")
    out7, _ = F.parse_fulldelivery(tw(), DAY, known={"2314"})
    ck("  只留 2314", [r[1] for r in out7] == ["2314"], str(out7))
    ck("  ⚠ 而 feed 設定是 known=False（全額交割股可能不在我方母體裡 ⇒ ⛔ 不可以濾掉）",
       F.FEEDS["fulldelivery"]["known"] is False,
       str(F.FEEDS["fulldelivery"]["known"]))

    print(f"\n{OK} ok, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
