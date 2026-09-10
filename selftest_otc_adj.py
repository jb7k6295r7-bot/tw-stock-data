#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_otc_adj.py — 驗上櫃事件回補的**續跑台帳**與 `--codes` 過濾。

⛔ 這一支存在的理由是一個 2026-09-10 **實跑當場抓到**的資料流失：

    不帶 `--resume` 跑一趟 ⇒ `done` 是空集合
    ⇒ `save_done()` 把 **1,996 列的續跑台帳整份洗成一列表頭**

⚠ 而它看起來完全正常：檔案在、格式對、程式回 0。
下一趟帶 `--resume` 時「已完成 0 個」⇒ **從頭重跑 1,942 發**，
⛔ 而那正是免費額度撐不過的那種跑法 ⇒ 永遠跑不完，每趟都像有在跑。

⭐ 而 `otc_adj.py` 的檔頭**早就寫著同一個病**（`write_days` 第一版整檔覆寫，
「前一趟同一天的其他個股全被蓋掉，而且沒有任何錯誤訊息」）
——⛔ 同一個道理只做了一半，這是這個專案第 N 次。
"""
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


def main():
    d = tempfile.mkdtemp(prefix="otcadj_")
    real = O.DONE
    O.DONE = os.path.join(d, "_otcadj_done.csv")
    try:
        print("① ⭐⭐ 續跑台帳：`save_done` 必須**合併**，⛔ 不可以整份取代")
        O.save_done({("1240", O.DS_DIV), ("1240", O.DS_RED),
                     ("6461", O.DS_DIV)})
        ck("  第一趟寫進 3 筆", len(O.load_done()) == 3, str(O.load_done()))
        # ⛔ 這一行就是那次實跑：不帶 --resume ⇒ done 是空集合
        n = O.save_done(set())
        after = O.load_done()
        ck("  ⭐⭐ 用**空集合**存一次，舊的 3 筆**還在**"
           "（⛔ 這正是那次洗掉 1,996 列的那一步）",
           len(after) == 3, str(after))
        ck("  回傳的是合併後的筆數", n == 3, str(n))
        O.save_done({("9999", O.DS_RED)})
        ck("  新的那一筆也進得去", len(O.load_done()) == 4, str(O.load_done()))
        ck("  ⚠ 而且是併集不是覆蓋（1240 那兩筆仍在）",
           ("1240", O.DS_DIV) in O.load_done(), str(O.load_done()))

        print("② ⛔ 反向：證明「整份取代」的寫法會被上面那條抓到")
        # ⭐ 這一節不是裝飾：它證明 ① 真的在測「合併」，
        #   ⛔ 而不是碰巧因為別的原因通過。
        def replace_style(done):
            with io.open(O.DONE, "w", encoding="utf-8") as fh:
                fh.write("stock_id,dataset\n")
                for c, ds in sorted(done):
                    fh.write(f"{c},{ds}\n")
        replace_style(set())
        ck("  ⭐ 整份取代的寫法：用空集合存一次就**只剩表頭**",
           len(O.load_done()) == 0, str(O.load_done()))
        ck("  ⚠ 而檔案還在、格式還對（⇒ 這種壞法不會有錯誤訊息）",
           os.path.exists(O.DONE)
           and io.open(O.DONE, encoding="utf-8").readline().strip()
           == "stock_id,dataset")

        print("③ 台帳的讀寫是對稱的（⛔ 不對稱的話續跑會漏掉一部分）")
        pairs = {(f"{i:04d}", O.DS_DIV) for i in range(1000, 1010)}
        O.save_done(pairs)
        ck("  10 筆進去、10 筆出來", O.load_done() >= pairs, str(len(O.load_done())))
        ck("  ⚠ 檔案沒有第 11 列以外的垃圾",
           len([ln for ln in io.open(O.DONE, encoding="utf-8")
                if ln.strip()]) == 11, O.DONE)

        print("④ `--codes` 過濾：⛔ 指名了卻一檔都不在母體裡要**大聲失敗**")
        # ⚠ 這一段是 main() 裡的分支，這裡照它的邏輯重現一次判準本身。
        universe = ["1240", "6461", "8299"]
        def pick(spec):
            want = [c.strip() for c in spec.split(",") if c.strip()]
            return [c for c in universe if c in want], \
                   [c for c in want if c not in universe]
        got, miss = pick("6461")
        ck("  指名一檔 ⇒ 只做那一檔", got == ["6461"] and not miss, str((got, miss)))
        got2, miss2 = pick("6461,9999999")
        ck("  ⚠ 混著不存在的代號 ⇒ 做得到的照做，做不到的**要講出來**",
           got2 == ["6461"] and miss2 == ["9999999"], str((got2, miss2)))
        got3, _ = pick("9999999")
        ck("  ⛔ 一檔都不在母體裡 ⇒ 空的（呼叫端要據此回非 0，"
           "⚠ 靜靜跑 0 檔會讓「補過了」與「代號打錯」長得一模一樣）",
           got3 == [], str(got3))

        print("⑤ ⛔ 這一支沒有動到 repo 真的台帳")
        ck("  DONE 指向沙箱", O.DONE.startswith(d), O.DONE)
        ck("  真的那一份還在且不只表頭",
           os.path.exists(real)
           and len([1 for _ in io.open(real, encoding="utf-8")]) > 1, real)
    finally:
        O.DONE = real
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
