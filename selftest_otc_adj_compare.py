#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_otc_adj_compare.py — 驗「官方 vs 我方」的雙向逐筆比對。

⛔ 這份比對是要拿來做**換供料決定**的 ⇒ 它自己算錯的代價是**決定做錯**。

⭐ 要證明的重點：

    ① 四類分得開，⛔ 而且**不合計成一個數字**
    ② ⭐ 官方那邊**必須跟著只取「曾經上櫃」的代號**
       ——⛔ 第一版忘了，`TWT49U` 是全上市的表，C 類從 2,998 膨脹到 14,497，
       ⚠ 而那看起來像「我方漏抓一萬多筆」：**方向剛好相反、而且很嚇人**
    ③ 比對窗兩端都要擋：窗前是我方還沒開始，⛔ 窗後是官方的**預告列**
    ④ ⛔ 這一支一列都不寫進 `data/adj/`
"""
import io
import os
import shutil
import sys
import tempfile

import otc_adj_compare as C

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
    print("① 四類分得開，⛔ 不合計")
    off = {("1111", "2020-01-02"): (0.98, "exDailyQ", 10.0, 9.8),
           ("1111", "2020-02-02"): (0.50, "revivt", 10.0, 5.0),
           ("2222", "2020-03-02"): (0.90, "exDailyQ", 10.0, 9.0)}
    mine = {("1111", "2020-01-02"): (0.98, "exright", "除息"),
            ("1111", "2020-02-02"): (0.55, "reduce", ""),
            ("3333", "2020-04-02"): (0.10, "parvalue", "面額變更")}
    r = C.classify(off, mine, "2015-01-05", "2026-09-10")
    ck("  A（兩邊同）1 筆", len(r["A"]) == 1, str(r["A"]))
    ck("  ⛔ B（兩邊都有但 factor 不同）1 筆", len(r["B"]) == 1, str(r["B"]))
    ck("  B 那一筆兩個數字都在（0.5 vs 0.55）",
       r["B"] and r["B"][0][2] == 0.5 and r["B"][0][3] == 0.55, str(r["B"]))
    ck("  C（官方有我方沒有）1 筆，且帶得出來源",
       len(r["C"]) == 1 and r["C"][0][3] == "exDailyQ", str(r["C"]))
    ck("  ⛔⛔ D（我方有官方沒有）1 筆，且帶得出 event",
       len(r["D"]) == 1 and r["D"][0][3] == "parvalue", str(r["D"]))
    ck("  ⚠ 四類加起來 = 兩邊鍵的聯集（⛔ 沒有列被吃掉）",
       sum(len(v) for v in r.values()) == len(set(off) | set(mine)),
       str({k: len(v) for k, v in r.items()}))

    print("② ⭐ 容差：捨入等級的差算 A，⛔ 真的不同算 B")
    off2 = {("1111", "2020-01-02"): (0.98000000, "exDailyQ", 10.0, 9.8)}
    ck("  差 1e-9 ⇒ A",
       len(C.classify(off2, {("1111", "2020-01-02"): (0.980000001, "e", "")},
                      "2015-01-05", "2026-09-10")["A"]) == 1)
    ck("  ⛔ 差 1e-4 ⇒ B",
       len(C.classify(off2, {("1111", "2020-01-02"): (0.9801, "e", "")},
                      "2015-01-05", "2026-09-10")["B"]) == 1)

    print("③ ⛔ 比對窗兩端都要擋")
    wide = {("1111", "2013-01-02"): (0.9, "exDailyQ", 10.0, 9.0),
            ("1111", "2026-09-21"): (0.6, "revivt", 10.0, 6.0),
            ("1111", "2020-01-02"): (0.9, "exDailyQ", 10.0, 9.0)}
    r3 = C.classify(wide, {}, "2015-01-05", "2026-09-10")
    ck("  ⚠ 涵蓋期**之前**那一筆不算缺口（我方日檔還沒開始）",
       all(x[1] != "2013-01-02" for x in r3["C"]), str(r3["C"]))
    ck("  ⛔⛔ **今天之後**那一筆也不算（`revivt` 會回未來的恢復買賣日）"
       "　⇒ 不擋的話這份報告每天假紅",
       all(x[1] != "2026-09-21" for x in r3["C"]), str(r3["C"]))
    ck("  窗內那一筆算", len(r3["C"]) == 1, str(r3["C"]))
    ck("  ⚠ 邊界是閉區間（等於起點與等於今天都算）",
       len(C.classify({("1", "2015-01-05"): (1.0, "x", 1, 1),
                       ("2", "2026-09-10"): (1.0, "x", 1, 1)},
                      {}, "2015-01-05", "2026-09-10")["C"]) == 2)

    print("④ ⭐⭐ 官方那邊必須跟著只取「曾經上櫃」的代號")
    d = tempfile.mkdtemp(prefix="otccmp_")
    keep = (C.EXH, C.RDH, C.TWEX, C.DAILY, C.ADJ, C.OUT)
    try:
        C.EXH = os.path.join(d, "ex.csv")
        C.RDH = os.path.join(d, "rd.csv")
        C.TWEX = os.path.join(d, "twex")
        C.DAILY = os.path.join(d, "daily")
        C.ADJ = os.path.join(d, "adj")
        os.makedirs(C.TWEX)
        io.open(C.EXH, "w", encoding="utf-8").write(
            "date,stock_id,name,pre_close,ref_price,kind,asof\n"
            "2020-01-02,1111,甲,10,9.8,息,x\n")
        io.open(C.RDH, "w", encoding="utf-8").write(
            "date,stock_id,name,last_close,ref_price,factor,reason,"
            "shares_per_1000,cash_return,factor_official,asof\n"
            "2020-02-02,1111,甲,10,5,0.5,彌補虧損,,,,x\n")
        # ⚠ `TWT49U` 是**全上市**的表：這裡故意放一檔從來不是上櫃的 2330
        io.open(os.path.join(C.TWEX, "2020-03-02.csv"), "w",
                encoding="utf-8").write(
            "date,stock_id,pre_close,ref_price,value,kind,open_base\n"
            "2020-03-02,1111,10,9,1,除息,\n"
            "2020-03-02,2330,600,590,10,除息,\n")
        off4, src4 = C.official({"1111"})
        ck("  ⭐ 只留 1111（曾經上櫃）", {k[0] for k in off4} == {"1111"},
           str(sorted(off4)))
        ck("  ⛔ 2330（從來不是上櫃）**不進來**",
           ("2330", "2020-03-02") not in off4, str(sorted(off4)))
        ck("  三支來源都算得出來", src4 == {"exDailyQ": 1, "revivt": 1,
                                          "TWT49U": 1}, str(src4))
        # ⛔ 反向：不濾的話 2330 會進來 ⇒ C 類被灌水
        off4b, _ = C.official({"1111", "2330"})
        ck("  ⭐⭐ 把 2330 放進 codes ⇒ 它就進來了"
           "（⇒ 證明那道過濾真的在做事，⛔ 不是碰巧）",
           ("2330", "2020-03-02") in off4b, str(sorted(off4b)))
        ck("  ⚠ 而多出來的那一筆會直接變成 C 類（官方有我方沒有）",
           len(C.classify(off4b, {}, "2015-01-05", "2026-09-10")["C"])
           - len(C.classify(off4, {}, "2015-01-05", "2026-09-10")["C"]) == 1)

        print("⑤ 母體判準取自**日檔的 market 欄**，⛔ 不是 stocks.csv")
        os.makedirs(C.DAILY)
        io.open(os.path.join(C.DAILY, "2020-01-02.csv"), "w",
                encoding="utf-8").write(
            "key,date,stock_id,name,market\n"
            "a,2020-01-02,1111,甲,tpex\n"
            "b,2020-01-02,2330,台積電,twse\n")
        io.open(os.path.join(C.DAILY, "2026-09-10.csv"), "w",
                encoding="utf-8").write(
            "key,date,stock_id,name,market\n"
            "c,2026-09-10,1111,甲,twse\n")     # ⭐ 它轉上市了
        got = C.otc_codes()
        ck("  ⭐ 1111 仍在母體裡（**曾經**上櫃，⛔ 不是「現在是」）",
           "1111" in got, str(sorted(got)))
        ck("  ⛔ 2330 不在", "2330" not in got, str(sorted(got)))

        print("⑥ ⛔ 這一支一列都不寫進 data/adj")
        os.makedirs(C.ADJ)
        io.open(os.path.join(C.ADJ, "1111.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            "2020-01-02,0.98,0.98,10,9.8,除息,exright\n")
        before = io.open(os.path.join(C.ADJ, "1111.csv"),
                         encoding="utf-8").read()
        C.OUT = os.path.join(d, "out.csv")
        # ⛔ runlog 也進沙箱：自測不可以動 repo 真的 `data/meta/_last_run.md`
        import runlog
        _rp, runlog.PATH = runlog.PATH, os.path.join(d, "_last_run.md")
        sys.argv = ["x"]
        C.main()
        ck("  ⭐ data/adj 的那一檔**逐字沒變**",
           io.open(os.path.join(C.ADJ, "1111.csv"),
                   encoding="utf-8").read() == before)
        ck("  差異清單有寫出來", os.path.exists(C.OUT))
        head = io.open(C.OUT, encoding="utf-8").readline().strip()
        ck("  清單第一欄就是 class（⇒ 四類讀得出來，⛔ 不是一個總數）",
           head.startswith("class,"), head)
        runlog.PATH = _rp
    finally:
        (C.EXH, C.RDH, C.TWEX, C.DAILY, C.ADJ, C.OUT) = keep
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
