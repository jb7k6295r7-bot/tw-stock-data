#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`transpose.source_fingerprint` / `write_stamp` / `stale_vs_source` 的自測。

## ⛔⛔ 這一支的價格是一封寄出去的錯信（2026-09-11）

    09-10 16:29  transpose 跑完（建 data/stocks/）
    09-11 01:22  「甲」回補 2022 全年落地　← ⬇ 三整年的**無成交列**進日檔
    09-11 03:46  「甲」2023
    09-11 05:44  「甲」2024

⇒ 我拿那份**過期的個股庫**算了洞的分類寄給 K線分析線
  ⇒ ⛔ 17 段「未解釋」裡 **12 段其實是零成交**。

## ⛔ 而當時那道閘門是**綠的**

    ok　⭐ 個股庫跟得上日檔　（日檔到 2026-09-10｜個股庫到 2026-09-10）

⚠ 它比**最後一天**。而少掉的是**中間幾萬列** ⇒ 最後一天一樣 ⇒ 照樣綠。

## ⇒ 這一支要釘的四件

    ⭐ ① **同一天的檔裡多了幾列** ⇒ 要判成「不是新的」（⛔ 這正是漏掉的那一種）
       ② 沒有指紋檔 ⇒ 判成「不是新的」（⛔ 讀不到 ≠ 沒問題）
       ③ 指紋一致 ⇒ 判成新的（⛔ 否則天天紅，然後被學會忽略）
       ④ 新增一天 ⇒ 也要判成「不是新的」
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import transpose as T                                          # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def day(path, rows):
    """照真日檔的形狀寫（⛔ 假的比真的簡單＝那段沒測）。"""
    with io.open(path, "w", encoding="utf-8") as f:
        f.write("key,date,stock_id,name,market,close,volume,price_basis\n")
        for r in rows:
            f.write(",".join(r) + "\n")


def main():
    print("=" * 60)
    print("transpose 的輸入指紋（不連網、不碰 repo 的 data/）")
    print("=" * 60)

    d = tempfile.mkdtemp(prefix="tstamp_")
    src = os.path.join(d, "daily")
    out = os.path.join(d, "stocks")
    os.makedirs(src)
    os.makedirs(out)
    _oldsrc, _oldout = T.SRC["price"], T.OUT["price"]
    try:
        T.SRC["price"] = [src]
        T.OUT["price"] = out

        day(os.path.join(src, "2026-09-08.csv"),
            [["2026-09-08_2330", "2026-09-08", "2330", "台積電", "twse",
              "900", "1000", ""]])
        day(os.path.join(src, "2026-09-09.csv"),
            [["2026-09-09_2330", "2026-09-09", "2330", "台積電", "twse",
              "905", "1200", ""]])

        print("\n[1] 蓋章之後 ⇒ 判成**新的**")
        T.write_stamp("price", 2)
        ok1, why1 = T.stale_vs_source("price")
        ck("⭐ 剛建好 ⇒ 新的（⛔ 否則天天紅，然後被學會忽略）", ok1, why1)
        ck("  說明裡講得出檔數與最後一天",
           "2 檔" in why1 and "2026-09-09" in why1, why1)

        print("\n[2] ⭐⭐ **同一天的檔裡多了幾列**（＝「甲」回補的形狀）")
        # ⚠ 天數沒變、最後一天沒變 ⇒ ⛔ 舊判準（比最後一天）**看不出來**
        day(os.path.join(src, "2026-09-08.csv"),
            [["2026-09-08_2330", "2026-09-08", "2330", "台積電", "twse",
              "900", "1000", ""],
             ["2026-09-08_4419", "2026-09-08", "4419", "元勝", "tpex",
              "", "0", "無成交"]])
        ok2, why2 = T.stale_vs_source("price")
        ck("⛔⛔ 同一天多了一列 ⇒ 判成**不是新的**（⛔ 這正是漏掉的那一種）",
           not ok2, why2)
        ck("  而且講得出是哪一項變了（bytes）", "bytes" in why2, why2)
        # ⭐ 反向：證明「只比最後一天」在這裡**分不出來**
        fp = T.source_fingerprint("price")
        ck("⭐ 反向驗：這一步的**最後一天沒有變**"
           "（⇒ 舊判準必定放行，⛔ 證明新判準不是多此一舉）",
           fp["last"] == "2026-09-09" and fp["files"] == 2, str(fp))

        print("\n[3] 新增一天 ⇒ 也要判成不是新的")
        T.write_stamp("price", 3)
        day(os.path.join(src, "2026-09-10.csv"),
            [["2026-09-10_2330", "2026-09-10", "2330", "台積電", "twse",
              "910", "900", ""]])
        ok3, why3 = T.stale_vs_source("price")
        ck("  新增一天 ⇒ 不是新的", not ok3, why3)
        ck("  講得出 files 與 last 都變了",
           "files" in why3 and "last" in why3, why3)

        print("\n[4] ⛔ 沒有指紋檔 ⇒ 判成不是新的（⛔ 讀不到 ≠ 沒問題）")
        os.remove(os.path.join(out, T.STAMP))
        ok4, why4 = T.stale_vs_source("price")
        ck("  舊版建的個股庫沒有指紋 ⇒ 一律判成不新", not ok4, why4)
        ck("  而且說得出是**沒有指紋**，不是「輸入變了」",
           "沒有" in why4 and "_built.json" in why4, why4)

        print("\n[5] ⛔ 指紋檔壞掉 ⇒ 也是不新（⛔ 不是丟例外）")
        io.open(os.path.join(out, T.STAMP), "w").write("{ 這不是 json")
        ok5, why5 = T.stale_vs_source("price")
        ck("  壞掉的指紋 ⇒ 不新", not ok5, why5)

        print("\n[6] 蓋章的內容照真的形狀")
        T.write_stamp("price", 42)
        body = json.load(io.open(os.path.join(out, T.STAMP), encoding="utf-8"))
        ck("  有 kind／rows／src 三個鍵",
           set(body) == {"kind", "rows", "src"}, str(sorted(body)))
        ck("  src 有 files／bytes／last",
           set(body["src"]) == {"files", "bytes", "last"},
           str(sorted(body["src"])))
        ck("  rows 記的是這一趟讀進來的列數", body["rows"] == 42, str(body))
        ok6, _ = T.stale_vs_source("price")
        ck("⭐ 重新蓋章之後又是新的（⇒ 上面那些紅不是永久紅）", ok6)
    finally:
        T.SRC["price"], T.OUT["price"] = _oldsrc, _oldout
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
