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
    ⑥ ⛔⛔ **列的長度 ＝ 表頭的長度**，而且欄位要**照欄名**擺
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

        print("④ ⭐⭐ 母體的 `kinds`：官方模式**不可以只收普通股**")
        # ⛔ 這是換源當場抓到的：`otc_codes()` 預設 `("stock",)`，
        #   而官方除權息 13,105 筆裡 **2,967 筆是 00 開頭的 ETF／ETN**
        #   ⇒ 沿用預設值的話那批**一筆都不會進來**，
        #   ⚠ 而整趟會是綠的、`data/adj/` 也照樣長大（長的是普通股那一半）。
        #   ⭐ 而契約裡早就寫著「上櫃 ETF 完全沒有還原因子」——正是這一批。
        dd = os.path.join(d, "u")
        os.makedirs(os.path.join(dd, "daily"))
        io.open(os.path.join(dd, "daily", "2020-01-02.csv"), "w",
                encoding="utf-8").write(
            "key,date,stock_id,name,market\n"
            "a,2020-01-02,1111,甲,tpex\n"
            "b,2020-01-02,006201,寶富櫃,tpex\n"
            "c,2020-01-02,2330,台積電,twse\n")
        meta = os.path.join(d, "stocks.csv")
        io.open(meta, "w", encoding="utf-8").write(
            "stock_id,name,market,kind,first_seen,last_seen\n"
            "1111,甲,tpex,stock,,\n"
            "006201,寶富櫃,tpex,etf,,\n"
            "2330,台積電,twse,stock,,\n")
        k2 = (O.UNI, O.META)
        try:
            O.UNI, O.META = dd, meta
            only = set(O.otc_codes())
            allk = set(O.otc_codes(kinds=None))
            ck("  預設只收普通股 ⇒ ETF 不在裡面",
               only == {"1111"}, str(sorted(only)))
            ck("  ⭐ `kinds=None` ⇒ ETF 進得來",
               allk == {"1111", "006201"}, str(sorted(allk)))
            ck("  ⛔ 上市的 2330 兩邊都不會進來",
               "2330" not in allk, str(sorted(allk)))
            # ⭐ 反向：拿只收普通股的母體去跑官方模式 ⇒ ETF 那一列會被丟掉
            io.open(O.OFF_EX, "w", encoding="utf-8").write(
                "date,stock_id,name,pre_close,ref_price,kind,value,asof\n"
                "2020-02-02,1111,甲,10,9.8,息,0.2,x\n"
                "2020-02-02,006201,寶富櫃,20,19.5,息,0.5,x\n")
            ex_only, _, _ = O.official_rows(only)
            ex_all, _, _ = O.official_rows(allk)
            ck("  ⭐⭐ 只收普通股 ⇒ ETF 那一列**不見了**（1 筆）",
               sum(len(v) for v in ex_only.values()) == 1,
               str(ex_only))
            ck("  ⭐ 不限 kind ⇒ 兩筆都在（⇒ 這就是那 2,967 筆的差別）",
               sum(len(v) for v in ex_all.values()) == 2, str(ex_all))
            # ⭐⭐ 呼叫點也要測：`--official` 用的**就是**不限 kind 的那個母體
            #   ⛔ 只測 `otc_codes(kinds=None)` 的話，把 main 裡改回預設值
            #     一條斷言都不會紅（突變 Z1 當場證明）。
            ck("  ⭐⭐ `official_codes()`（`--official` 實際用的）**含 ETF**",
               O.official_codes() == {"1111", "006201"},
               str(sorted(O.official_codes())))
        finally:
            O.UNI, O.META = k2

        print("⑤ ⚠ 換源前的快照（裁定裡指名要的）")
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
        print("⑥ ⛔⛔ 欄位錯位：`official_factor` 插進中間之後的那個 bug")
        # ⚠ 2026-09-10 實際發生：FinMind 那條路的列是**照位置**堆的 8 個值，
        #   而 `RD_HEADER` 有 9 欄 ⇒ `"finmind"` 落到 `official_factor`、
        #   `source` 變成空的。⛔ 而 `data/adj/6461.csv` 照樣長出來、數字全對。
        ck("  ⭐ `_row()` 照欄名擺位，長度 ＝ 表頭長度",
           len(O._row(O.RD_HEADER, date="2026-09-09", stock_id="6461",
                      source="finmind")) == len(O.RD_HEADER))
        r = O._row(O.RD_HEADER, date="2026-09-09", stock_id="6461",
                   pre_close="16.65", ref_price="26.92", reason="彌補虧損",
                   open_base="26.9", ex_ref_price="0.0",
                   official_factor="1.61661100", source="finmind")
        got = dict(zip(O.RD_HEADER, r))
        ck("  ⭐ `official_factor` 真的在 `official_factor` 那一格",
           got["official_factor"] == "1.61661100", str(got))
        ck("  ⭐ `source` 真的在 `source` 那一格（⛔ 不是空的）",
           got["source"] == "finmind", str(got))
        bad_name = False
        try:
            O._row(O.RD_HEADER, offical_factor="1.0")   # ⚠ 故意拼錯
        except KeyError:
            bad_name = True
        ck("  ⛔ 欄名拼錯要**大聲失敗**（⚠ 靜靜留空 ＝ 那條裁定不生效）",
           bad_name)

        print("⑦ ⛔ 反向：短一格的列要被 `write_days` 擋下來")
        O.UNI = os.path.join(d, "uni7")
        short = ["2026-09-09", "6461", "16.65", "26.92", "彌補虧損",
                 "26.9", "0.0", "finmind"]              # ← 舊寫法，8 格
        ck("  （前提）舊寫法真的少一格",
           len(short) == len(O.RD_HEADER) - 1, str(len(short)))
        blocked = False
        try:
            O.write_days("otcreduce", O.RD_HEADER, {"2026-09-09": [short]})
        except ValueError:
            blocked = True
        ck("  ⭐⭐ 少一格 ⇒ **擋下來**（⛔ 不是靜靜寫成整片左移）", blocked)
        ck("  ⛔ 而且擋下來時**沒有寫出半個檔**",
           not os.path.exists(os.path.join(O.UNI, "otcreduce",
                                           "2026-09-09.csv")))

        print("⑧ ⭐ FinMind 那條路也要拿得到官方換股比例")
        O.OFF_RD = os.path.join(d, "rdh8.csv")
        io.open(O.OFF_RD, "w", encoding="utf-8").write(
            "date,stock_id,name,last_close,ref_price,factor,reason,"
            "shares_per_1000,cash_return,factor_official,asof\n"
            "2026-09-09,6461,益得,16.65,26.92,1.61681682,彌補虧損,"
            "618.578000,0.00000000,1.61661100,2026-09-11\n"
            "2020-01-02,9999,無比例,10,9.8,0.98,現金減資,,,,2026-09-11\n")
        m = O.official_factor_map()
        ck("  ⭐ 對照表取得到（6461 ⇒ 1.61661100）",
           m.get(("6461", "2026-09-09")) == "1.61661100", str(m))
        ck("  ⛔ `factor_official` 是空的那一列**不進表**（⚠ 不可以猜）",
           ("9999", "2020-01-02") not in m, str(m))

        print("⑨ ⛔⛔ 判準檔用不了時要**大聲失敗**，⛔ 不是靜靜寫空欄")
        # ⚠ run 101 實測：欄位錯位修好之後 `official_factor` **還是空的**——
        #   workflow checkout 的是**分支**，而判準檔只在 **main** 上。
        #   ⭐ 第四點六的鏡像：那一條是「分支比 main 舊」，這裡是「分支沒有那個檔」。
        O.OFF_RD = os.path.join(d, "不存在.csv")
        ok, m, why = O.check_official_table()
        ck("  ⭐⭐ 判準檔**不在** ⇒ 判成不可繼續", ok is False, why[:60])
        ck("  ⚠ 而說明要講得出**怎麼補**（⛔ 只說「失敗」等於再來一個來回）",
           "otc_reduce_history.csv" in why and "origin/main" in why, why[:120])
        # ⛔ 「檔在、但一列都沒有 factor_official」跟檔不在**等價**
        # ⚠ 檔名刻意用 ASCII：第一版叫「空殼.csv」，而下面那條斷言寫的是
        #   「說明裡不可以出現『空殼』」⇒ ⛔ **路徑本身**讓它紅了。
        #   ⭐ 斷言比對的字串裡混進了受測資料的名字，就測不到判準本身。
        O.OFF_RD = os.path.join(d, "hollow.csv")
        io.open(O.OFF_RD, "w", encoding="utf-8").write(
            "date,stock_id,name,last_close,ref_price,factor,reason,"
            "shares_per_1000,cash_return,factor_official,asof\n"
            "2026-09-09,6461,益得,16.65,26.92,1.61681682,彌補虧損,,,,2026-09-11\n")
        ok2, _m2, why2 = O.check_official_table()
        ck("  ⭐ 檔在、但一列都沒有 `factor_official` ⇒ **也**判成不可繼續"
           "（⛔ 只判 `os.path.exists` 會讓空殼檔靜靜放行）", ok2 is False, why2[:60])
        ck("  ⚠ 而說明要分得出是哪一種（檔不在／有檔但沒值）",
           "一列都沒有" in why2 and "檔不在" not in why2, why2[:80])
        # ⭐ 正例：有值就要放行（⛔ 一個永遠擋的守門會被直接拿掉）
        O.OFF_RD = os.path.join(d, "rdh8.csv")
        ok3, m3, why3 = O.check_official_table()
        ck("  ⭐ 有值 ⇒ **放行**，並回得出筆數（⛔ 門檻不可以卡到正常的）",
           ok3 is True and m3.get(("6461", "2026-09-09")) == "1.61661100",
           f"{ok3}｜{why3}")

    finally:
        (O.UNI, O.OFF_EX, O.OFF_RD, O._ROOT) = keep
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
