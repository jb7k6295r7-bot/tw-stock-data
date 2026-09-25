#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_merge_ledger.py — 驗累積型 CSV 的逐鍵合併。

⛔ 這一支的存在理由是一次**實際發生的資料遺失**（2026-09-10）：

    07:15  一天實測（2026-09-09）推上 main ⇒ `_coverage_backfill.csv` 多一列
    07:20  2015 那批開跑，checkout 的是**分支**（分支上沒有那一列）
    07:22  它把整個檔搬到 main ⇒ ⛔ **五分鐘前那一列被刪掉**

⚠ 而 `git diff` 看起來完全正常：一加一減，像是「這一趟重算過」。

⭐ 所以第一節就是**把那一天重演一次**，並且證明合併之後不會再掉。
"""
import sys

import merge_ledger as M

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


H = "date,twse,tpex,emerging,total,note\n"


def main():
    print("① ⭐ 把 2026-09-10 那次遺失重演一次")
    # 分支上的（過期）：沒有 09-09 那一列，但多了本趟剛寫的 2015-01-05
    mine = H + "2015-01-05,1569,0,0,1569,ok\n"
    # main 上的（比較新）：五分鐘前推上去的 09-09
    main_ = H + "2026-09-09,1382,1014,0,2396,ok\n"
    out, note = M.merge(mine, main_, ["date"])
    ck("  ⭐ main 上那一列**還在**（這就是原本會被刪掉的那一列）",
       "2026-09-09,1382,1014,0,2396,ok" in out, out)
    ck("  本趟那一列也在", "2015-01-05,1569,0,0,1569,ok" in out, out)
    ck("  合併後 2 列", out.count("\n") == 3, repr(out))
    ck("  說明講得出數字", "合併 2 列" in note, note)

    print("② 同一個鍵兩邊都有 ⇒ **取本趟的**（本趟是為了那個鍵才去抓的）")
    out2, _ = M.merge(H + "2026-09-09,1,1,1,3,新的\n",
                      H + "2026-09-09,9,9,9,27,舊的\n", ["date"])
    ck("  取到新的", "2026-09-09,1,1,1,3,新的" in out2, out2)
    ck("  ⛔ 舊的不留", "舊的" not in out2, out2)

    print("③ 輸出照主鍵排序（讓 diff 讀得出來）")
    out3, _ = M.merge(H + "2026-01-02,1,1,1,3,a\n2015-01-05,1,1,1,3,b\n",
                      H, ["date"])
    ck("  2015 在 2026 前面",
       out3.index("2015-01-05") < out3.index("2026-01-02"), out3)

    print("④ ⛔ 反向：這些情形一律**不合併**（丟 ValueError ⇒ 呼叫端退回整檔）")
    for label, a, b, k in (
            ("表頭不同", H + "x,1,1,1,3,a\n",
             "date,twse\n2026-09-09,1\n", ["date"]),
            ("主鍵欄不存在", H + "2015-01-05,1,1,1,3,a\n", H, ["不存在"]),
            ("本趟那一份是空的", "", H, ["date"])):
        try:
            M.merge(a, b, k)
            ck(f"  {label} ⇒ 要丟 ValueError", False, "沒有丟")
        except ValueError as e:
            ck(f"  {label} ⇒ 丟 ValueError（{str(e)[:40]}）", True)

    print("⑤ ⚠ 最重要的一條：**合併後不可以比 main 少**")
    #   那正是這支要防的事——它自己絕不可以變成刪東西的那個人。
    class _Sneaky(str):
        pass
    try:
        # 造一個「兩列 main、本趟一列且鍵重複」⇒ 正常會是 2 列
        out5, _ = M.merge(H + "2026-09-09,1,1,1,3,a\n",
                          H + "2026-09-09,9,9,9,27,b\n2026-09-08,1,1,1,3,c\n",
                          ["date"])
        ck("  正常情形：main 2 列 ⇒ 合併後仍然 2 列",
           out5.count("\n") == 3, repr(out5))
    except ValueError as e:
        ck("  正常情形不該丟", False, str(e))
    # ★ 反向驗：把守門條件本身測出來——主鍵重複到讓列數縮水時必須丟
    try:
        M.merge(H + "2026-09-09,1,1,1,3,a\n",
                H + "2026-09-09,9,9,9,27,b\n2026-09-09,8,8,8,24,c\n",
                ["date"])
        ck("  ★ main 自己有重複鍵（2 列同鍵）⇒ 合併後會少 ⇒ **必須丟**",
           False, "沒有丟")
    except ValueError as e:
        ck(f"  ★ main 自己有重複鍵 ⇒ 合併後會少 ⇒ **確實丟了**（{str(e)[:40]}）", True)

    print("⑥ main 上還沒有這個檔 ⇒ 本趟就是全部")
    out6, _ = M.merge(H + "2015-01-05,1,1,1,3,a\n", "", ["date"])
    ck("  只有本趟那一列", out6.count("\n") == 2, repr(out6))

    print("⑦ ⚠ 多欄主鍵（例如 停牌是 代號＋日期）")
    HH = "stock_id,susp_date,name\n"
    out7, _ = M.merge(HH + "1101,2020-01-02,A\n",
                      HH + "1101,2020-01-03,B\n2330,2020-01-02,C\n",
                      ["stock_id", "susp_date"])
    ck("  三列都在（⛔ 不會因為代號相同就被當成同一個鍵）",
       out7.count("\n") == 4, repr(out7))

    print("⑧ ⭐ 明確的移除清單（2026-09-25：delisted.csv 誤收的轉上市聯集刪不掉）")
    HD = "delist_date,stock_id,name,asof,market\n"
    RM = "market,stock_id,delist_date\n"
    main8 = HD + "2011-07-22,3454,晶睿,x,tpex\n2016-01-04,6211,福登,x,tpex\n"
    mine8 = HD + "2016-01-04,6211,福登,y,tpex\n2020-01-13,3452,益通,y,tpex\n"
    keys8 = ["market", "stock_id", "delist_date"]
    out8, n8 = M.merge(mine8, main8, keys8, RM + "tpex,3454,2011-07-22\n")
    ck("  ⭐ 清單點名的 3454 從合併結果消失、其餘照聯集", "3454" not in out8
       and "6211" in out8 and "3452" in out8 and out8.count("\n") == 3, repr(out8))
    ck("  ⭐ 說明講得出刪了幾列", "刪掉 main 的 1 列" in n8, n8)
    out8b, _ = M.merge(mine8, main8, keys8)
    ck("  ⛔ 反向：不給清單 ⇒ 3454 照舊被併回來（⇒ 這條機制是必要的）", "3454" in out8b, repr(out8b))
    out8c, n8c = M.merge(mine8, main8, keys8, RM + "tpex,9999,2011-07-22\n")
    ck("  ⭐ 清單上的鍵 main 沒有 ⇒ 什麼都不刪、不報錯", out8c.count("\n") == 4, n8c)
    for bad, why in ((RM, "空清單"), ("market,stock_id\ntpex,3454\n", "缺主鍵欄")):
        try:
            M.merge(mine8, main8, keys8, bad)
            ck("  ⛔ %s ⇒ 必須丟" % why, False, "沒有丟")
        except ValueError as e:
            ck("  ⛔ %s ⇒ 確實丟了（%s）" % (why, str(e)[:30]), True)
    try:
        M.merge(mine8, main8 + "2012-01-01,1111,甲,x,tpex\n", keys8.__class__(keys8), RM + "tpex,3454,2011-07-22\n")
        ck("  ⭐ ④ 那道還在：本趟沒有 1111、清單也沒點名 ⇒ 聯集保留它（不少）", True)
    except ValueError as e:
        ck("  ⭐ ④ 那道還在", False, str(e))
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
