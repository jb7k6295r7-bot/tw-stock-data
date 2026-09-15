#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`otc_parvalue_history` 的自測。**不連網、不碰真的 data/。**

## ⭐ 假回應是**真的那一份**（截到 3 列）

⛔ 不是我照著欄名編的：`詳細資料` 是一整段 HTML、`/` 逃脫成 `\\u002f`、
證券名稱後面帶一串空白（`"長科*           "`）——⚠ 這些形狀我編不出來，
⭐ 而它們每一個都會讓解析壞掉。

⇒ 三列是**挑過**的：
```
6548 1080909  換股率 10（整數比）
6548 1110905  換股率 2.5（**非整數**）
3093 1111212  ⭐ 參考價 27.38，而我方是 27.375 ⇒ **差恰好半分**那一種
```
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import runlog                                                  # noqa: E402
import otc_parvalue_history as H                               # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}" + (f"　（{hint}）" if hint else ""))
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


RAW = r'''{"date": "20150101~20260915", "tables": [{"title": "", "totalCount": 4, "fields": ["恢復買賣日期", "證券代號", "證券名稱", "最後交易日之收盤價格", "恢復買賣開始參考價", "漲停價格", "跌停價格", "開始交易基準價", "詳細資料"], "data": [["1080909", "6548", "長科*           ", "312.00", "31.20", "34.30", "28.10", "31.20", "<table><tr><th>證券代號/證券名稱:</th><td>6548&nbsp/&nbsp長科*</td></tr><tr><th>停止買賣日期:</th><td>108/08/29</td></tr><tr><th>恢復買賣日期:</th><td>108/09/09</td></tr><tr><th>變更股票面額換股率:</th><td>10.00000000</td></tr><tr><th>變更前股票面額:</th><td>10.00</td></tr><tr><th>變更後股票面額:</th><td>1.00</td></tr></table>"], ["1110905", "6548", "長科*           ", "90.60", "36.24", "39.85", "32.65", "36.25", "<table><tr><th>證券代號/證券名稱:</th><td>6548&nbsp/&nbsp長科*</td></tr><tr><th>停止買賣日期:</th><td>111/08/25</td></tr><tr><th>恢復買賣日期:</th><td>111/09/05</td></tr><tr><th>變更股票面額換股率:</th><td>2.50000000</td></tr><tr><th>變更前股票面額:</th><td>1.00</td></tr><tr><th>變更後股票面額:</th><td>0.40</td></tr></table>"], ["1111212", "3093", "港建*           ", "109.50", "27.38", "30.10", "24.65", "27.40", "<table><tr><th>證券代號/證券名稱:</th><td>3093&nbsp/&nbsp港建*</td></tr><tr><th>停止買賣日期:</th><td>111/12/01</td></tr><tr><th>恢復買賣日期:</th><td>111/12/12</td></tr><tr><th>變更股票面額換股率:</th><td>4.00000000</td></tr><tr><th>變更前股票面額:</th><td>10.00</td></tr><tr><th>變更後股票面額:</th><td>2.50</td></tr></table>"], ["1150413", "8937", "合騏*           ", "145.50", "36.38", "40.00", "32.75", "36.40", "<table><tr><th>證券代號/證券名稱:</th><td>8937&nbsp/&nbsp合騏*</td></tr><tr><th>停止買賣日期:</th><td>115/04/01</td></tr><tr><th>恢復買賣日期:</th><td>115/04/13</td></tr><tr><th>變更股票面額換股率:</th><td>4.00000000</td></tr><tr><th>變更前股票面額:</th><td>10.00</td></tr><tr><th>變更後股票面額:</th><td>2.50</td></tr></table>"]], "summary": []}], "stat": "ok"}'''
WANT = "20150101~20260915"


def main():
    d = json.loads(RAW)

    print("── ① 解析（⭐ 假回應是真的那一份）──")
    rows, note = H.parse(d, WANT)
    ck("解出 4 列", len(rows) == 4, note)
    ck("⭐ 民國日期轉成西元（1080909 → 2019-09-09）", rows[0][0] == "2019-09-09",
       rows[0][0])
    ck("⭐ 代號與名稱（⚠ 名稱後面那一串空白要去掉）",
       rows[0][1] == "6548" and rows[0][2] == "長科*", repr(rows[0][2]))
    ck("⭐⭐ **換股率**從 `詳細資料` 那段 HTML 裡挖得出來（⚠ `/` 是 `\\u002f`）",
       [r[8] for r in rows] == [10.0, 2.5, 4.0, 4.0], str([r[8] for r in rows]))
    ck("  面額前後也挖得出來（10.00→1.00／1.00→0.40／10.00→2.50）",
       [(r[9], r[10]) for r in rows]
       == [(10.0, 1.0), (1.0, 0.4), (10.0, 2.5), (10.0, 2.5)],
       str([(r[9], r[10]) for r in rows]))
    ck("  停止買賣日期也挖得出來（⭐ 它跟恢復日不同天 ⇒ 停牌缺口）",
       rows[0][11] == "2019-08-29", rows[0][11])

    print("\n── ② ⛔ 回應要**自己講出**它涵蓋哪一段（第二點）──")
    r2, n2 = H.parse(d, "20200101~20201231")
    ck("⭐⭐ 回顯的期間**不是**我請求的那一段 ⇒ 一列都不回",
       r2 == [] and "參數被忽略" in n2, n2)
    r3, n3 = H.parse({"tables": d["tables"]}, WANT)
    ck("⛔ 連 `date` 鍵都沒有 ⇒ 判**不出**（⚠ 不可以讀成「有生效」）",
       r3 == [] and "判不出" in n3, n3)

    print("\n── ③ 官方那一列自己內部一致（最後收盤 ÷ 參考價 ≟ 換股率）──")
    ck("四列都過", all(H.ratio_ok(r) for r in rows))
    bad = list(rows[0])
    bad[8] = 3.0                                  # 換股率亂改
    ck("⛔ 換股率被改掉 ⇒ 判不一致", H.ratio_ok(bad) is False)
    miss = list(rows[0])
    miss[8] = None
    ck("⭐ 缺值 ⇒ 回 None（**判不出**），⛔ 不是「過」", H.ratio_ok(miss) is None)
    # ⛔⛔ 而那個 0.005 的門檻**不可以**用浮點差比（本檔頭那一段）
    ck("⭐⭐ 3093 那一筆（官方 27.38）在**分**的尺度上算一致",
       H.ratio_ok(rows[2]) is True,
       f"最後收盤 {rows[2][3]}｜參考價 {rows[2][4]}｜換股率 {rows[2][8]}")

    print("\n── ④ ⭐ 對帳是**雙向**的（⛔ 只比一個方向不算一致）──")
    mine = {("2019-09-09", "6548"): {"pre_close": "312", "ref_price": "31.2"},
            ("2022-09-05", "6548"): {"pre_close": "90.6", "ref_price": "36.24"},
            ("2022-12-12", "3093"): {"pre_close": "109.5", "ref_price": "27.375"},
            # ⭐ 8937 是**分辨得出兩種比法**的那一列（36.375 vs 36.38）
            #   ⛔ 少了它，「拿浮點差比門檻」那個突變什麼都不會改變（第七點第四個）
            ("2026-04-13", "8937"): {"pre_close": "145.5", "ref_price": "36.375"}}
    res = H.reconcile(rows, mine)
    ck("四筆換股率都相同", len(res["same"]) == 4, str(res["same"]))
    # ⛔⛔ 我第一版斷言「3093 的參考價差半分要被列出來」——**那是錯的**：
    #   27.375 與 27.38 在**分**的尺度上是**同一個數**（round(2737.5)==2738）。
    #   ⚠ 而我先前那句「2 筆差恰好半分」是拿**浮點差**比出來的假差異。
    #   ⇒ ⭐ 全庫 14 筆實測：參考價在分的尺度上 **14/14 相同**。
    ck("⭐⭐ 參考價在**分**的尺度上相同 ⇒ `ref_cents` 是空的"
       "（⚠ 我方多留一位，⛔ 那不是差異）",
       res["ref_cents"] == [], str(res["ref_cents"]))
    # ⭐ 而那個偵測器**仍然要會叫**：塞一個真的差一分的進去
    bad_ref = dict(mine)
    bad_ref[("2022-12-12", "3093")] = {"pre_close": "109.5", "ref_price": "27.39"}
    ck("  ⛔ 而真的差一分時它要叫（⇒ 這不是把偵測器關掉）",
       len(H.reconcile(rows, bad_ref)["ref_cents"]) == 1,
       str(H.reconcile(rows, bad_ref)["ref_cents"]))
    ck("⛔ 只有官方有的要列出來",
       len(H.reconcile(rows, {})["only_official"]) == 4)
    ck("⛔ **只有我方有**的也要列出來（⚠ 這就是反方向，少了它不算一致）",
       H.reconcile(rows[:1], mine)["only_mine"] != [],
       str(H.reconcile(rows[:1], mine)["only_mine"]))
    bad_mine = dict(mine)
    bad_mine[("2019-09-09", "6548")] = {"pre_close": "312", "ref_price": "62.4"}
    ck("⭐⭐ 換股率真的衝突 ⇒ 進 `ratio_diff`（⛔ 不自己選一邊）",
       len(H.reconcile(rows, bad_mine)["ratio_diff"]) == 1,
       str(H.reconcile(rows, bad_mine)["ratio_diff"]))

    print("\n── ⑤ ★ 沒有動到 repo 真的檔 ──")
    # ⛔⛔ 這裡**不可以**自己 `open` 低水位檔（`selftest_lowwater` ⑨ 當場擋下來：
    #   「全 repo 沒有人自己開低水位檔來讀寫」——⚠ 而那條守的正是「第九份實作」）。
    #   ⇒ ⭐ 走 `lowwater.read()`，⛔ 而路徑走 `H.low_path()`（唯一那一份）。
    import lowwater as _lw
    real_out = os.path.join(HERE, "data", "meta", "otc_parvalue_history.csv")
    b1 = _lw.read(H.low_path(), _lw.UP)
    b2 = io.open(real_out, "rb").read() if os.path.isfile(real_out) else None
    tmp = tempfile.mkdtemp(prefix="opv_")
    old_root, old_rl = H._ROOT, runlog.PATH
    try:
        H._ROOT = os.path.join(tmp, "data")
        runlog.PATH = os.path.join(tmp, "rl.md")
        os.makedirs(os.path.join(H._ROOT, "meta"))
        ck("⭐ 路徑是**呼叫當下**才算的（⇒ 沙箱只要導 `_ROOT` 一個旋鈕）",
           H.out_path().startswith(tmp) and H.low_path().startswith(tmp),
           H.out_path())
    finally:
        H._ROOT, runlog.PATH = old_root, old_rl
        shutil.rmtree(tmp, ignore_errors=True)
    a1 = _lw.read(H.low_path(), _lw.UP)
    a2 = io.open(real_out, "rb").read() if os.path.isfile(real_out) else None
    ck("★ 沒有動到 repo 真的 `_otc_parvalue_low.txt`", b1 == a1)
    ck("★ 沒有動到 repo 真的 `otc_parvalue_history.csv`", b2 == a2)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
