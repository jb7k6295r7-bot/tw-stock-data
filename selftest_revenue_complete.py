#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`mops_history.revenue_complete` 的自測。**不連網、不碰真的 data/。**

## ⛔⛔ 它擋的是一個「永遠補不到」的洞

`--fill` 用 `has_output()` 決定跳不跳過，而 `revenue` 那一支**一直是
`os.path.exists`** ⇒ 檔案只要在（哪怕只有 12% 的列）就被跳過
⇒ ⚠ 那一趟印「0 期檔、0 個失敗」，**看起來像都做完了**。

⭐ 而 `has_output` 的說明**早就記著**這個教訓（2026-09-06 那次），
⛔ 只是當時只修了 `bs`——同一個檔案裡，同一個道理只做了一半（CLAUDE.md 四點六③）。
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mops_history as M                                       # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def write(d, per, market, rows):
    """照真檔的形狀寫（表頭＋rows 列）。⛔ 假的比真的簡單＝那段沒測。"""
    p = os.path.join(d, "revenue_hist", f"{per}_{market}.csv")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("period,stock_id,name,market,revenue,yoy\n")
        for i in range(rows):
            f.write(f"{per},{1000+i},X,{market},1,0\n")


def main():
    print("=" * 64)
    print("revenue_complete：判的是**抓完了沒**，⛔ 不是「檔案在不在」")
    print("=" * 64)
    d = tempfile.mkdtemp(prefix="mrev_")
    old = M.OUT
    try:
        M.OUT = d
        # 12 期正常（800 列），中間塞一期只有 12% 的
        for i in range(1, 13):
            write(d, f"2022-{i:02d}", "tpex", 800)
        write(d, "2022-06", "tpex", 96)          # ⛔ 這一期沒抓完

        print("\n── ① 核心：檔在、但列數只有鄰期的 12% ──")
        ck("⛔ 判成**沒抓完**（⚠ 舊版 `os.path.exists` 會說「完整」）",
           M.revenue_complete("2022-06", "tpex") is False,
           f"列數 {M.revenue_rows('2022-06', 'tpex')}")
        ck("★ 反向驗：正常的那幾期判成完整（⛔ 不然是每期都紅）",
           all(M.revenue_complete(f"2022-{i:02d}", "tpex")
               for i in (1, 2, 3, 11, 12)))
        ck("⛔ 檔不存在 ⇒ 沒抓完", not M.revenue_complete("2023-01", "tpex"))
        ck("`revenue_rows` 扣掉表頭", M.revenue_rows("2022-01", "tpex") == 800,
           str(M.revenue_rows("2022-01", "tpex")))

        print("\n── ② 基準是**鄰近期別**，⛔ 不是全庫中位數 ──")
        # 家數會長期漂移：早期 400、晚期 900。中間那期 420 對鄰期是正常的
        d2 = tempfile.mkdtemp(prefix="mrev2_")
        M.OUT = d2
        for i in range(1, 13):
            write(d2, f"2015-{i:02d}", "tpex", 400)
        for i in range(1, 13):
            write(d2, f"2026-{i:02d}", "tpex", 900)
        ck("⭐ 早期 400 列在**鄰期也是 400** 的情況下判成完整"
           "（⛔ 用全庫中位數 650 × 0.9 會誤判成沒抓完）",
           M.revenue_complete("2015-06", "tpex"))
        ck("★ 反向驗：把它砍到 40 列就要判成沒抓完",
           (write(d2, "2015-06", "tpex", 40) or True)
           and not M.revenue_complete("2015-06", "tpex"))
        shutil.rmtree(d2, ignore_errors=True)

        print("\n── ③ 沒有可比的對象時**不判**（⛔ 不要用猜的門檻擋）──")
        d3 = tempfile.mkdtemp(prefix="mrev3_")
        M.OUT = d3
        write(d3, "2026-01", "tpex", 3)
        ck("只有一期、沒有鄰居 ⇒ 判成完整（⛔ 不硬擋）",
           M.revenue_complete("2026-01", "tpex"))
        shutil.rmtree(d3, ignore_errors=True)

        print("\n── ④ 呼叫點：`has_output('revenue', …)` 真的走這一支 ──")
        M.OUT = d
        # ⭐ 比行為，⛔ 不比字串
        ck("`has_output` 對那個殘缺期別回 False",
           M.has_output("revenue", "2022-06", "tpex") is False)
        ck("`has_output` 對正常期別回 True",
           M.has_output("revenue", "2022-01", "tpex") is True)
    finally:
        M.OUT = old
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
