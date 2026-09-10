#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_twparse.py — 驗共用的日期解析。

⛔ 這一支的存在理由是一次**真的失敗**：`bulletin/revivt` 在 Actions 上回了
283 列，我方**一列都認不出來**——舊的解析只吃兩種寫法。
⇒ 每一種官方寫法都要有正例，每一種不該吃的都要有反例。
⚠ 而反例比正例重要：**猜一個日期出來，比認不出更糟。**
"""
import sys

import twparse as T

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


GOOD = [
    ("115/09/10", "2026-09-10", "民國斜線"),
    ("115/9/10", "2026-09-10", "民國斜線、月日不補零"),
    ("115-09-10", "2026-09-10", "民國連字號"),
    ("115年09月10日", "2026-09-10", "⭐ 民國中文（revivt 那 283 列的嫌疑犯）"),
    ("115年9月10日", "2026-09-10", "民國中文、不補零"),
    ("1150910", "2026-09-10", "⭐ 民國 7 碼連寫"),
    ("2026-09-10", "2026-09-10", "西元連字號"),
    ("2026/09/10", "2026-09-10", "西元斜線"),
    ("20260910", "2026-09-10", "西元 8 碼連寫"),
    ("  115/09/10  ", "2026-09-10", "前後空白"),
    ("　115/09/10", "2026-09-10", "全形空白"),
    ("109/06/22", "2020-06-22", "情報分析線實測的那一筆"),
    ("115.09.10", "2026-09-10", "點分隔"),
]
BAD = ["", "   ", "--", "----", "abc", "115/13/01", "115/09/32",
       "115/09", "0000000", "99999999", "1899/01/01", "None", None]


def main():
    print("① 官方各種寫法都要吃得下")
    for src, want, why in GOOD:
        got = T.roc_iso(src)
        ck(f"  {why}｜{src!r} → {want}", got == want, repr(got))

    print("② ⛔ 反向：認不出的**一律回 None**（⚠ 猜一個日期比認不出更糟）")
    for src in BAD:
        got = T.roc_iso(src)
        ck(f"  {src!r} → None", got is None, repr(got))

    print("③ ⚠ 民國 7 碼與西元 8 碼**不可以**混淆")
    ck("  '1150910' 不會被當成西元 1150910 年",
       T.roc_iso("1150910") == "2026-09-10", repr(T.roc_iso("1150910")))
    ck("  '20260910' 不會被 +1911", T.roc_iso("20260910") == "2026-09-10",
       repr(T.roc_iso("20260910")))

    print("④ pick_field")
    F = ["恢復買賣日期", "股票代號", "ISIN代號", "名稱"]
    ck("  找得到「恢復買賣日期」", T.pick_field(F, "恢復買賣日期", "日期") == 0)
    ck("  ⚠ 只給「代號」會先撞上 `股票代號`（包含比對）",
       T.pick_field(F, "代號") == 1, str(T.pick_field(F, "代號")))
    ck("  找不到回 None", T.pick_field(F, "不存在的欄") is None)
    ck("  ⚠ 第 0 欄要回 0，⛔ 不是 falsy 就當沒找到",
       T.pick_field(F, "恢復買賣日期") == 0)

    print("⑤ ⛔ 兩支歷史腳本用的是**同一支**（不是各抄一份）")
    import otc_exright_history as E
    import otc_reduce_history as R
    ck("  otc_exright_history._iso is twparse.roc_iso", E._iso is T.roc_iso)
    ck("  otc_reduce_history._iso is twparse.roc_iso", R._iso is T.roc_iso)
    ck("  兩支的 _pick 也是同一支",
       E._pick is T.pick_field and R._pick is T.pick_field)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
