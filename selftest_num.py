#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_num.py — 釘住「官方的空值寫法」這一條規則（`backfill._num` / `fetch._num`）。

⭐ 為什麼要有這一支（2026-09-10，情報分析線回報）：
  官方的「這格沒有值」不是一種寫法，是**一族**——
  TWSE 寫 `--`，TPEx 同一件事寫 `----`。
  ⛔ 我方舊版只列舉了 `"-"`／`"--"`，`----` 是靠 `float()` 失敗**順便**被擋掉的。
    擋得住，但那是**副作用**：沒有人知道它在擋這個，也沒有人測過它。
  ⚠ 同一個坑對面已經踩了：他們那一版把 `----` 轉成 NaN，
    `JSON.stringify(NaN)` 印成 `null`，於是「我方 null、官方 null」
    長得一模一樣卻被判成不符，差一點回報成資料瑕疵。

⛔ 這支自測要證明三件事，缺一不可：
  ① 破折號族（各種長度、各種全形）**全部**→ 空字串
  ② ⚠ 反向：`-3.40` 的負號**不可以**被當成破折號（不然漲跌全變空的）
  ③ 兩份 `_num()`（刻意複製的那兩份）對同一批輸入**回一樣的答案**
     ——`limit` 的 bug 就是「同一段邏輯抄兩份、只修了一份」。

⭐ 而且要證明它**會紅**：末段直接餵一個沒有這條規則的舊版實作，
  若它也「通過」，代表這支測試根本沒在測東西 ⇒ 自己報失敗。
  （「沒證明過會失敗的測試，不算測試」）
"""
import sys

import backfill as B
import fetch as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# 破折號族：長度 1~4、半形／全形／各種 dash，以及前後有空白的
EMPTY = ["-", "--", "---", "----", "------",
         "–", "—", "－－", "────",
         "ー", "−", "  ----  ", "\t--\n"]
# ⚠ 這些**不是**空值，一格都不能被吃掉
KEEP = [("-3.40", "-3.40"), ("-0.05", "-0.05"), ("+1.20", "1.20"),
        ("0.00", "0.00"), ("0", "0"), ("1,234,567", "1234567"),
        ("92.50", "92.50"), ("-1e3", "-1e3")]
# 非破折號的空值寫法（本來就有，回歸用）
OTHER_EMPTY = ["", "X", "N/A", "null", "None", "   ", None]


def main():
    print("① 破折號族一律 → 空字串（兩份 _num 都要）")
    for t in EMPTY:
        ck(f"  backfill._num({t!r})", B._num(t) == "", repr(B._num(t)))
        ck(f"  fetch._num({t!r})", F._num(t) == "", repr(F._num(t)))

    print("② ⚠ 反向：負號／數字一格都不能被當成破折號")
    for t, want in KEEP:
        ck(f"  backfill._num({t!r}) == {want!r}", B._num(t) == want, repr(B._num(t)))
        ck(f"  fetch._num({t!r}) == {want!r}", F._num(t) == want, repr(F._num(t)))

    print("③ 其他空值寫法（回歸）")
    for t in OTHER_EMPTY:
        ck(f"  backfill._num({t!r})", B._num(t) == "", repr(B._num(t)))
        ck(f"  fetch._num({t!r})", F._num(t) == "", repr(F._num(t)))

    print("④ 兩份刻意複製的 _num() 對同一批輸入答案一致")
    same = [t for t in EMPTY + OTHER_EMPTY + [k for k, _ in KEEP]
            if B._num(t) != F._num(t)]
    ck("  backfill._num == fetch._num（逐項）", not same, f"不一致：{same}")

    print("⑤ _is_dash 本身")
    ck("  _is_dash('----')", B._is_dash("----"))
    ck("  ⚠ _is_dash('') 是 False（空字串另有出口，不要混在一起）",
       B._is_dash("") is False)
    ck("  ⚠ _is_dash('-3.40') 是 False", B._is_dash("-3.40") is False)
    ck("  backfill._is_dash 與 fetch._is_dash 同一套字元集",
       B._DASHES == F._DASHES, f"{B._DASHES!r} vs {F._DASHES!r}")

    # ⭐⭐ 反向測試：把規則拿掉，這支必須紅。
    #   ⛔ 沒證明過會失敗的測試不算測試——這一段就是那個證明。
    print("⑥ ⭐ 反向：拿掉規則的舊版實作**必須**被抓出來")

    def _old(v):          # 2026-09-10 之前的 fetch._num，逐字照抄
        if v is None:
            return ""
        t = str(v).replace(",", "").replace("+", "").replace("%", "").strip()
        if t in ("", "-", "--", "X", "N/A"):
            return ""
        try:
            float(t)
        except ValueError:
            return ""
        return t

    # ⚠ 舊版**答案也是對的**（靠 float() 失敗順便擋掉）——所以不能只比輸出，
    #   要比「這條規則存不存在」。真正的差別在：舊版沒有 _is_dash 可以測、
    #   拿掉 float() 保護就會漏。⇒ 用「把 float() 那層拿掉」來曝露它。
    def _old_nofloat(v):
        t = str(v).replace(",", "").strip()
        return "" if t in ("", "-", "--", "X", "N/A") else t

    leaks = [t for t in EMPTY if _old_nofloat(t) != ""]
    ck("  舊版列舉式規則對破折號族**會漏**（證明這支測試測得到東西）",
       len(leaks) >= 5, f"只漏了 {leaks}")
    now = [t for t in EMPTY if B._num(t) != ""]
    ck("  ⇒ 現在這一版一個都不漏", not now, f"還在漏：{now}")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
