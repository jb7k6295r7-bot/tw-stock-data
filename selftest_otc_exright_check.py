#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_otc_exright_check.py — 驗「官方有、我方 data/adj 沒有」那道斷言。

⛔ 這一支存在的理由是一份 **runlog 裡自己跟自己矛盾**的輸出（2026-09-10 19:21）：

    - 2026-09-10 4541 晟田｜…｜✓ 已落地
    - 2026-09-10 5328 華容｜…｜✓ 已落地
    …
    - **✗** 官方有、我方 data/adj 沒有 ⇒ 0 筆（**4／4 筆沒落地**）

⭐ 成因：`mark` 那一行寫的是 `(r[1], r[0]) not in miss`，
而 `miss` 裝的是**列**（list）⇒ 拿一個 tuple 去 `in` 它**永遠是 True**
⇒ 每一列都印「✓ 已落地」。

⚠ 而**顯示**是騙人的那一半：check 是對的。
⛔ 但看 runlog 的人先看到的是那四個 ✓——
⭐ 一個「明細說沒事、結論說有事」的報告，會讓人去懷疑結論。

## 第二件事：官方會回**除權息日在未來**的預告列

⛔ 把預告當缺口 ⇒ 這道斷言**每天都會紅**，然後被學會忽略。
⭐ 而它們確實還不該落地：那一天還沒到，前收盤價根本還不存在。
"""
import io
import sys
from datetime import datetime, timedelta

import otc_exright_check as C

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ⛔ 判準**不在這裡抄一份**（那就是第四點五）——直接用它本人。
mark_of = C.classify


def main():
    today = "2026-09-10"
    tmr = (datetime.strptime(today, "%Y-%m-%d")
           + timedelta(days=1)).strftime("%Y-%m-%d")
    rows = [[today, "4541", "晟田", "60.00", "59.31", "除權"],
            [today, "5328", "華容", "58.80", "58.45", "除息"],
            [tmr, "3141", "晶宏", "92.10", "91.74", "除息"]]

    print("① ⭐⭐ 顯示與結論必須一致（⛔ 那次是每一列都印 ✓、結論說 4/4 沒落地）")
    m, miss, fut = mark_of(rows, set(), today)
    ck("  4541 沒落地 ⇒ 顯示「⛔ 沒有」，⛔ 不是「✓ 已落地」",
       m[("4541", today)] == "⛔ **data/adj 沒有**", str(m))
    ck("  5328 同上", m[("5328", today)] == "⛔ **data/adj 沒有**", str(m))
    ck("  ⭐ 結論的筆數與顯示對得起來（2 筆沒落地）", len(miss) == 2, str(miss))
    # ⛔ 反向：把舊寫法重現一次，證明它真的永遠印 ✓
    miss_list = [r for r in rows if (r[1], r[0]) not in set()]
    old_mark = ["✓" if (r[1], r[0]) not in miss_list else "⛔" for r in rows]
    ck("  ⭐⭐ 舊寫法（拿 tuple 去 `in` 一串**列**）**每一列都是 ✓**"
       "　⇒ 這一節不是憑空擔心",
       old_mark == ["✓", "✓", "✓"], str(old_mark))
    ck("  ⚠ 而它同時算得出「3 筆沒落地」⇒ **同一份報告自己矛盾**",
       len(miss_list) == 3, str(len(miss_list)))

    print("①之二 ⭐⭐ 基準要是**我方資料最後一天**，⛔ 不是「今天」（2026-09-11 踩到）")
    # ⚠ 實際情形：3141 的除息日**就是今天**（09-11），而我方日檔只到昨天（09-10，
    #   今天盤後才會有）。⇒ 拿 `today` 當基準 ⇒ 它不算未來 ⇒ 被報成「沒落地」
    #   ⇒ ⛔ runlog 寫「那幾檔今天的漲跌算出來是錯的」，⚠ 而我照那句寫信給 K線分析線。
    _t = "2026-09-11"                       # 今天
    _last = "2026-09-10"                    # ⭐ 我方資料最後一天（盤還沒收）
    _rows = [[_t, "3141", "晶宏", "92.10", "91.74", "除息"]]
    _m1, _miss1, _fut1 = mark_of(_rows, set(), _t)        # ⛔ 舊判準：跟今天比
    ck("  ⛔ 拿**今天**當基準 ⇒ 今天才除息的那筆被算成缺口（誤導性紅燈）",
       len(_miss1) == 1 and not _fut1, f"miss={_miss1}｜future={_fut1}")
    _m2, _miss2, _fut2 = mark_of(_rows, set(), _last)     # ⭐ 新判準：跟資料最後一天比
    ck("  ⭐⭐ 拿**資料最後一天**當基準 ⇒ 同一筆變成「⏳ 未來事件」，不是缺口",
       not _miss2 and len(_fut2) == 1, f"miss={_miss2}｜future={_fut2}")
    ck("  ⚠ 正例：昨天就除息、而且真的沒落地的 ⇒ **照樣算缺口**"
       "（⛔ 證明這不是把紅燈關掉）",
       len(mark_of([[_last, "5328", "華容", "58.80", "58.45", "除息"]],
                   set(), _last)[1]) == 1,
       str(mark_of([[_last, "5328", "華容", "58.80", "58.45", "除息"]],
                   set(), _last)))

    # ⛔⛔ 而「測了判準、沒測呼叫點」今天已經是第五次 ⇒ 這一條直接掃原始碼：
    #   `main()` 傳給 `classify` 的**必須是資料最後一天**，⚠ 不是 `datetime.now(...)`。
    _src = io.open(C.__file__, encoding="utf-8").read()
    ck("  ⭐⭐ `main()` 真的把**資料最後一天**傳進 classify"
       "（⛔ 只測 classify 的話，呼叫點改回 today 也不會紅）",
       "classify(rows, have, last_data)" in _src
       and "_adjust.trading_days()" in _src,
       "⛔ 呼叫點沒有用 last_data／沒有用 adjust.trading_days()")

    print("② ⛔ 未來的預告列不算缺口（否則這道斷言每天假紅）")
    ck("  ⏳ 3141（明天）被標成未來", m[("3141", tmr)] .startswith("⏳ 未來"), str(m))
    ck("  ⛔ 而且**不進** miss（不算缺口）",
       ("3141", tmr) not in miss, str(miss))
    ck("  ⚠ 但它有被單獨列出來（⭐ 好處是可以提前備妥因子）",
       ("3141", tmr) in fut, str(fut))
    ck("  ⭐ **今天**那兩筆照樣算缺口（邊界是 > today，不是 >=）",
       ("4541", today) in miss, str(miss))

    print("③ 落地了就要顯示落地（⛔ 否則變成永遠報缺口）")
    m2, miss2, fut2 = mark_of(rows, {("4541", today), ("5328", today)}, today)
    ck("  兩筆都落地 ⇒ 顯示 ✓", m2[("4541", today)] == "✓ 已落地"
       and m2[("5328", today)] == "✓ 已落地", str(m2))
    ck("  ⭐ miss 是空的 ⇒ 那道 check 會綠", not miss2, str(miss2))
    ck("  ⚠ 而未來那一筆仍然是未來（⛔ 不會因為別人落地就被改判）",
       m2[("3141", tmr)] .startswith("⏳ 未來"), str(m2))

    print("④ ⚠ 全部都是未來時：⛔ 不可以報成「全部落地」也不可以報成缺口")
    m3, miss3, fut3 = mark_of([rows[2]], set(), today)
    ck("  miss 空、future 1 筆", not miss3 and len(fut3) == 1,
       f"{miss3}｜{fut3}")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
