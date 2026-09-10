#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_adjust_official.py — 驗「還原用官方換股比例、斷點門檻用參考價」。

K線線 2026-09-10 20:20 裁定，逐字：

> **同一個公司行動可以有兩個正確的數字，因為它們回答的是兩個不同的問題。**
> 「持有人的財富怎麼變」用原始比例；「當天開盤從哪裡開始」用官方參考價。
> ⛔ 統一成一個看起來比較乾淨，**但那會讓其中一個問題被錯的數字回答。**

⭐ 要證明的重點：

    ① `factor` **原封不動**＝參考價 ÷ 前收（⛔ 硬斷點的 0.55／1.8 是從它推出來的）
    ② `cum_factor`（**還原用的那一個**）改用 `factor_official`
    ③ ⛔ 沒有官方值時 fallback 回 `factor`，⚠ 而 `factor_official` 欄**留空**
       （⛔ 不可以用 `factor` 頂替——那會讓「有官方值」與「沒有」長得一樣）
    ④ ⛔ 加欄位造成的**位置索引錯位**：`ADJ_HEADER` 中間插一欄之後，
       原本寫死的 `r[6]`（event）會指到 `kind` ⇒ ⚠ **減資事件數靜靜變成 0**
"""
import sys

import adjust as A

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def main():
    H = A.ADJ_HEADER
    i = {k: H.index(k) for k in H}
    CAL = ["2020-01-02", "2020-06-01", "2021-01-04"]

    print("① 官方值存在時：`cum_factor` 用官方，`factor` 不動")
    # 減資：前收 16.65 → 官方參考價 26.92（印到分）；官方比例回推 1.61662
    rows = [("2020-06-01", 26.92 / 16.65, 16.65, 26.92, "", "tpex",
             "reduce", 1.61662)]
    lines, chk, mis, sk = A.build("6461", rows, CAL, verify=False)
    r = lines[0]
    ck("  列長 = ADJ_HEADER", len(r) == len(H), f"{len(r)} vs {len(H)}")
    ck("  ⭐ `factor` 仍是**參考價回推**（1.61681…）",
       r[i["factor"]].startswith("1.6168"), r[i["factor"]])
    ck("  ⭐ `factor_official` 是官方比例（1.61662）",
       r[i["factor_official"]].startswith("1.61662"), r[i["factor_official"]])
    ck("  ⭐⭐ `cum_factor`（還原用）跟的是**官方值**，⛔ 不是 factor",
       r[i["cum_factor"]].startswith("1.61662"), r[i["cum_factor"]])
    ck("  ⚠ 而兩者確實不同（⇒ 這條裁定不是空談）",
       r[i["factor"]] != r[i["factor_official"]],
       f"{r[i['factor']]}｜{r[i['factor_official']]}")

    print("② ⛔ 沒有官方值時：fallback 回 factor，而那一欄**留空**")
    rows2 = [("2020-06-01", 0.98, 10.0, 9.8, "息", "tpex", "exright", None)]
    l2 = A.build("1111", rows2, CAL, verify=False)[0][0]
    ck("  `factor` = 0.98", l2[i["factor"]].startswith("0.98"), l2[i["factor"]])
    ck("  ⭐ `cum_factor` 也是 0.98（fallback）",
       l2[i["cum_factor"]].startswith("0.98"), l2[i["cum_factor"]])
    ck("  ⛔⛔ `factor_official` **是空字串**，⚠ 不是把 factor 抄過去"
       "（否則「有官方值」與「沒有」在檔案裡長得一模一樣）",
       l2[i["factor_official"]] == "", repr(l2[i["factor_official"]]))

    print("③ ⭐ 連乘：殘差是**系統性**的，不會互相抵銷")
    # 兩次減資，官方值都比參考價回推的小一點點
    rows3 = [("2020-01-02", 2.0, 10.0, 20.0, "", "tpex", "reduce", 1.99),
             ("2020-06-01", 2.0, 10.0, 20.0, "", "tpex", "reduce", 1.99)]
    l3 = A.build("2222", rows3, CAL, verify=False)[0]
    ck("  ⭐ 兩列連乘用的是官方值：1.99 × 1.99 = 3.9601",
       l3[0][i["cum_factor"]].startswith("3.9601"), l3[0][i["cum_factor"]])
    ck("  ⛔ 而不是 2.0 × 2.0 = 4（⇒ 差距**隨事件數放大**）",
       not l3[0][i["cum_factor"]].startswith("4."), l3[0][i["cum_factor"]])
    ck("  ⚠ 每一列的 `factor` 都還是 2.0（斷點門檻不受影響）",
       all(x[i["factor"]].startswith("2.0") for x in l3), str(l3))

    print("④ ⛔ 加欄位造成的位置錯位（這一節是為了一個我差點留下的 bug）")
    # `ADJ_HEADER` 中間插了 `factor_official` ⇒ 原本寫死的 r[6] 從 event 變成 kind
    ck("  ⭐ `event` 現在在第 7 欄，⛔ 不是第 6",
       i["event"] == 7 and H[6] == "kind", f"event={i['event']}｜H[6]={H[6]}")
    ck("  ⚠ 而寫死 r[6] 不會炸——它會拿到 `kind`，"
       "比對 `== \"reduce\"` 永遠 False ⇒ **減資事件數靜靜變成 0**",
       lines[0][6] != "reduce" and lines[0][i["event"]] == "reduce",
       f"r[6]={lines[0][6]!r}｜event={lines[0][i['event']]!r}")
    ck("  ⭐ `cum_factor` 也從第 2 欄移到第 3 欄",
       i["cum_factor"] == 3, str(i["cum_factor"]))

    print("⑤ ⚠ 邊界：官方值是 0 或負數時**不可以**拿來連乘")
    for bad in (0.0, -1.0):
        rb = [("2020-06-01", 0.98, 10.0, 9.8, "息", "tpex", "exright", bad)]
        lb = A.build("3333", rb, CAL, verify=False)[0]
        ck(f"  官方值 {bad} ⇒ 退回 factor 0.98",
           lb and lb[0][i["cum_factor"]].startswith("0.98"),
           str(lb[0][i["cum_factor"]]) if lb else "（空）")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
