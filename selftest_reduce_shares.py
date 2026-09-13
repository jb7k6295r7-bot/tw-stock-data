#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`reduce_shares_check` 的自測。**不連網、不碰真的 data/。**

⭐ 這一支要釘的是那個**最貴的一格**：兩種減資的算式不一樣。
⛔ 用錯的後果是**系統性偏差**，不是隨機誤差——而它看起來完全正常。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reduce_shares_check as R                                # noqa: E402

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
    print("=" * 64)
    print("reduce_shares_check：兩種減資的算式不一樣（不連網）")
    print("=" * 64)

    print("\n── ① 分類：哪一種有退還現金 ──")
    ck("`退還股款` 是現金型", R.is_cash("退還股款"))
    ck("`現金減資` 是現金型", R.is_cash("現金減資"))
    ck("⛔ `彌補虧損` **不是**現金型（股東沒拿到錢）", not R.is_cash("彌補虧損"))
    ck("空值不會爆，而且判成非現金型", not R.is_cash(None) and not R.is_cash(""))
    ck("前後空白照樣判得出來（⛔ CSV 讀進來常帶空白）", R.is_cash(" 退還股款 "))

    print("\n── ② 算式：拿**真實事件**驗（⛔ 不是我編的數字）──")
    # 1563 巧新 2026-09-07｜shares 225,608,140 → 169,206,105（＝ 0.75）
    #   官方參考價 84.66。⭐ 這三個數字都在 repo 裡查得到。
    got = R.expected_ref(66.00, 0.75, True)
    ck("1563 現金型：(66.00 − 10×0.25) ÷ 0.75 ⇒ 官方的 84.66",
       abs(got - 84.66) <= R.TOL, f"算出 {got:.4f}")
    # 6176 瑞儀 2026-08-24｜465,027,263 → 348,770,447（＝ 0.75）｜官方 105.06
    got = R.expected_ref(81.30, 0.75, True)
    ck("6176 現金型：(81.30 − 2.50) ÷ 0.75 ⇒ 官方的 105.06",
       abs(got - 105.06) <= R.TOL, f"算出 {got:.4f}")
    # 4174 浩鼎 2026-02-03｜彌補虧損｜前收 27.6 → 官方 55.2（換股比 0.5）
    got = R.expected_ref(27.60, 0.5, False)
    ck("4174 彌補虧損型：27.60 ÷ 0.5 ⇒ 官方的 55.20",
       abs(got - 55.20) <= R.TOL, f"算出 {got:.4f}")

    print("\n── ③ ⛔ 反向：用錯算式會差多少（這一節是本支存在的理由）──")
    wrong = R.expected_ref(66.00, 0.75, False)      # 現金型誤用彌補虧損式
    ck("⛔ 現金型誤套彌補虧損式 ⇒ 88.00，比官方的 84.66 高 3.34（3.9%）",
       abs(wrong - 88.00) < 0.01 and abs(wrong - 84.66) > 3.0,
       f"算出 {wrong:.4f}")
    ck("★ 反向驗：兩種算式**真的不同**（⛔ 一樣的話上面每一條都是假的）",
       R.expected_ref(66.00, 0.75, True) != R.expected_ref(66.00, 0.75, False))
    # ⭐ 而 88.00 正是 TradingView 2026-09-13 實測回的值（87.99978）
    ck("⭐ 88.00 就是 TradingView 量到的那個數（87.99978）"
       "⇒ ⛔ 它的還原只做股數、沒扣退還的現金",
       abs(wrong - 87.99978) < 0.01, f"算出 {wrong:.4f}")

    print("\n── ④ 總價值連續：⭐ 我方那個 factor 才是對報酬率對的那一個 ──")
    keep, ref, pre = 0.75, 84.66, 66.00
    cash_back = R.PAR * (1 - keep)
    ck("0.75 股 × 84.66 ＋ 退還 2.50 元 ＝ 前收 66.00（總價值連續）",
       abs(keep * ref + cash_back - pre) <= 0.01,
       f"{keep * ref + cash_back:.4f}")
    ck("⛔ 而純股數還原（88.00）**做不到**總價值連續",
       abs(keep * 88.00 + cash_back - pre) > 1.0,
       f"{keep * 88.00 + cash_back:.4f}")

    print("\n── ⑤ 面額是 10（⛔ 改了它，現金型整批會歪）──")
    ck("`PAR` 是 10.0", R.PAR == 10.0, str(R.PAR))

    print("\n── ⑥ `shares_around`：要找**前一個有值**的，⛔ 不是前一列 ──")
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="rsc_")
    old = R.STOCKS
    try:
        R.STOCKS = d
        io.open(os.path.join(d, "9999.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n"
            "2026-01-05,10,1000000\n"
            "2026-01-06,10,\n"          # ⚠ 空的：上市的 shares 常常是空的
            "2026-01-07,10,\n"
            "2026-01-08,10,750000\n")
        a, b = R.shares_around("9999", "2026-01-08")
        ck("跳過中間兩天空值，抓到 2026-01-05 那筆 1,000,000",
           (a, b) == (750000.0, 1000000.0), f"{(a, b)}")
        ck("⛔ 問一個不存在的日期 ⇒ 回 (None, None)，不爆",
           R.shares_around("9999", "2026-02-02") == (None, None))
        ck("⛔ 問一個沒有個股檔的代號 ⇒ 回 (None, None)，不爆",
           R.shares_around("0000", "2026-01-08") == (None, None))
    finally:
        R.STOCKS = old
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
