#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_otc_adj_official.py — 驗換供料第 2 步：官方為主、FinMind 退備援。

市場情報分析線 2026-09-10 23:00 裁定（依據是雙向比對 `B=0`、`D` 只有 15 筆）：

    ✅ 官方三支聯集為主（exDailyQ ＋ revivt ＋ TWT49U）
    ✅ otcparvalue.py 保留為第四支來源，面額變更由它負責
    ✅ FinMind 退為備援，且每一列標 source
    ⚠ 換源前留一份 data/adj 快照

⭐ 要證明的重點：

    ① ⛔ **FinMind 的列不可以蓋掉官方的**，⚠ 而反過來可以（那才叫換源）
    ② ⛔ 沒有這一條的話，兩支的**執行順序**就決定了資料內容
       ——而順序是排程的細節，**不該決定資料**
    ③ 官方判準檔 → 我方欄位的對應（含新補的 `value`）
    ④ 快照真的把現況記下來（⚠ 裁定裡指名要的）
"""
import csv
import io
import os
import shutil
import sys
import tempfile

import otc_adj as O

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def read_day(d, sub, day):
    p = os.path.join(d, sub, f"{day}.csv")
    with io.open(p, encoding="utf-8") as f:
        return {r["stock_id"]: r for r in csv.DictReader(f)}


def main():
    d = tempfile.mkdtemp(prefix="otcoff_")
    keep = (O.UNI, O.OFF_EX, O.OFF_RD, O._ROOT)
    try:
        O.UNI = d
        O.OFF_EX = os.path.join(d, "ex_hist.csv")
        O.OFF_RD = os.path.join(d, "rd_hist.csv")

        print("① ⭐⭐ FinMind **不可以**蓋掉官方的（⚠ 反過來可以）")
        # 先寫一列官方的
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-02": [
            ["2020-01-02", "1111", "10", "9.8", "0.2", "息", "", "exDailyQ"]]})
        # 再讓 FinMind 寫同一個鍵、不同的數字
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-02": [
            ["2020-01-02", "1111", "10", "9.5", "", "息", "", "finmind"]]})
        got = read_day(d, "otcexright", "2020-01-02")["1111"]
        ck("  ⭐ 留下來的是**官方**那一列（ref_price 9.8）",
           got["ref_price"] == "9.8" and got["source"] == "exDailyQ", str(got))
        ck("  ⛔ 而不是 FinMind 的 9.5", got["ref_price"] != "9.5", str(got))
        # ⚠ 反過來：官方蓋得掉 FinMind 的——那正是「換源」本身
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-03": [
            ["2020-01-03", "2222", "20", "19.0", "", "息", "", "finmind"]]})
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-03": [
            ["2020-01-03", "2222", "20", "19.5", "0.5", "息", "", "exDailyQ"]]})
        g2 = read_day(d, "otcexright", "2020-01-03")["2222"]
        ck("  ⭐ 官方蓋得掉 FinMind（19.0 → 19.5）⇒ **這才叫換源**",
           g2["ref_price"] == "19.5" and g2["source"] == "exDailyQ", str(g2))
        ck("  ⚠ 而且順便補上了 FinMind 沒有的 `value`", g2["value"] == "0.5",
           str(g2))
        # ⭐ 官方**蓋得掉官方**——⛔ 少了這一條，官方事後更正就永遠進不來
        #   （⚠ 而那種壞法完全看不出來：檔案在、數字是官方的，只是舊的）
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-03": [
            ["2020-01-03", "2222", "20", "19.7", "0.3", "息", "", "exDailyQ"]]})
        g3 = read_day(d, "otcexright", "2020-01-03")["2222"]
        ck("  ⭐ 官方**更正**進得來（19.5 → 19.7）"
           "⇒ ⛔ 先後規則只擋 FinMind，不是擋所有覆蓋",
           g3["ref_price"] == "19.7", str(g3))

        print("② ⛔ 反向：沒有這條先後規則時，**執行順序**就決定了資料")
        # ⚠ 這一節不是理論：兩支程式在排程裡誰先誰後是會變的。
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-04": [
            ["2020-01-04", "3333", "30", "29.5", "0.5", "息", "", "exDailyQ"]]})
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-04": [
            ["2020-01-04", "3333", "30", "29.0", "", "息", "", "finmind"]]})
        a_ = read_day(d, "otcexright", "2020-01-04")["3333"]["ref_price"]
        # 反序：FinMind 先、官方後
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-05": [
            ["2020-01-05", "3333", "30", "29.0", "", "息", "", "finmind"]]})
        O.write_days("otcexright", O.EX_HEADER, {"2020-01-05": [
            ["2020-01-05", "3333", "30", "29.5", "0.5", "息", "", "exDailyQ"]]})
        b_ = read_day(d, "otcexright", "2020-01-05")["3333"]["ref_price"]
        ck("  ⭐⭐ 兩種順序**結果相同**（都留官方的 29.5）"
           "⇒ ⛔ 順序不再決定資料", a_ == b_ == "29.5", f"{a_}｜{b_}")

        print("③ 官方判準檔 → 我方欄位")
        io.open(O.OFF_EX, "w", encoding="utf-8").write(
            "date,stock_id,name,pre_close,ref_price,kind,value,asof\n"
            "2020-02-02,1111,甲,10,9.8,息,0.2,x\n"
            "2020-02-02,9999,不在母體,10,9.8,息,0.2,x\n"
            "2020-02-03,1111,甲,,,息,,x\n")          # ⛔ 缺價格
        io.open(O.OFF_RD, "w", encoding="utf-8").write(
            "date,stock_id,name,last_close,ref_price,factor,reason,"
            "shares_per_1000,cash_return,factor_official,asof\n"
            "2020-03-03,1111,甲,16.65,26.92,1.6168,彌補虧損,618.578,0,1.6166,x\n")
        ex, rd, note = O.official_rows({"1111"})
        ck("  ⭐ 只收母體內的（9999 被跳過）",
           [r[1] for v in ex.values() for r in v] == ["1111"], str(ex))
        ck("  ⛔ 缺價格的那一列不收（⚠ 那會變成 factor 算不出來）",
           "2020-02-03" not in ex, str(sorted(ex)))
        row = ex["2020-02-02"][0]
        ck("  欄位對得上 EX_HEADER", len(row) == len(O.EX_HEADER),
           f"{len(row)} vs {len(O.EX_HEADER)}")
        m = dict(zip(O.EX_HEADER, row))
        ck("  ⭐ `value`（官方權值+息值）有帶進來", m["value"] == "0.2", str(m))
        ck("  ⭐ `source` 標的是 `exDailyQ`", m["source"] == "exDailyQ", str(m))
        r2 = dict(zip(O.RD_HEADER, rd["2020-03-03"][0]))
        ck("  減資：前收取的是 `last_close`（⛔ 不是 pre_close 欄名）",
           r2["pre_close"] == "16.65" and r2["ref_price"] == "26.92", str(r2))
        ck("  減資的 `source` 是 `revivt`", r2["source"] == "revivt", str(r2))
        ck("  說明講得出兩邊的筆數", "官方除權息 1 筆" in note
           and "官方減資 1 筆" in note, note)
        ck("  ⚠ 跳過的也數得出來", "跳過" in note and "除權息 2" in note, note)

        print("④ ⚠ 換源前的快照（裁定裡指名要的）")
        O._ROOT = d
        os.makedirs(os.path.join(d, "adj"))
        io.open(os.path.join(d, "adj", "1111.csv"), "w",
                encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            "2020-01-02,0.98,0.98,10,9.8,息,exright\n")
        io.open(os.path.join(d, "adj", "_index.csv"), "w",
                encoding="utf-8").write("stock_id,events\n1111,1\n")
        n = O.snapshot_adj(os.path.join(d, "snap.csv"))
        ck("  1 列（⛔ `_index.csv` 不算）", n == 1, str(n))
        snap = list(csv.DictReader(io.open(os.path.join(d, "snap.csv"),
                                           encoding="utf-8")))
        ck("  ⭐ 帶得出代號、日期、因子",
           snap[0]["stock_id"] == "1111" and snap[0]["factor"] == "0.98",
           str(snap))
        ck("  ⚠ 快照是**一張表**不是複製整棵目錄（⇒ 好 diff、好查）",
           os.path.isfile(os.path.join(d, "snap.csv")))
    finally:
        (O.UNI, O.OFF_EX, O.OFF_RD, O._ROOT) = keep
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
