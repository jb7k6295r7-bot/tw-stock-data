#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`mutate.py` 的自測。⛔ 造假的程式與假的自測，**不碰 repo 的任何 .py**。

## ⛔⛔ 為什麼這一支自己也要被測

`mutate.py` 是**判斷「斷言有沒有用」的那把尺**。
⚠ 尺壞了的方向只有一種，而且是最糟的那一種：
**它說「沒抓到」⇒ 有人會去刪掉一條其實有用的斷言。**

今天三次誤判各自的成因（`__pycache__`／只數 `✗`／錨點抄錯）
全部長成同一句「突變之後還是綠」。⇒ 這一支要釘的就是**分得開那三種**。

## 要釘的五件

    ① 真的會紅的突變 ⇒ 回 0「抓到」
    ② 什麼都沒影響的突變 ⇒ 回 1「沒抓到」
    ⭐ ③ 錨點對不上 ⇒ 回 **2**「突變沒套上去」，⛔ 不是 1
    ⭐ ④ 自測**崩潰**（沒有任何 `✗`）⇒ 照樣算「抓到」
    ⛔ ⑤ 跑完**一定要還原**——連自測崩潰的那一趟也要
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mutate as M                                             # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


TARGET = '''def answer():
    return 42


def helper():
    return "x"
'''

# ⚠ 假自測照真自測的形狀做：印 `  ok` / `  ✗`，失敗才回非 0
TEST = '''import sys
sys.path.insert(0, %r)
import importlib, target
importlib.reload(target)
bad = 0
if target.answer() == 42:
    print("  ok   答案是 42")
else:
    print("  ✗    答案不是 42")
    bad += 1
sys.exit(1 if bad else 0)
'''

# ⭐ 這一支會**崩潰**（沒有任何 ✗），用來驗第 ④ 件
TEST_CRASH = '''import sys
sys.path.insert(0, %r)
import importlib, target
importlib.reload(target)
print("  ok   先印一條")
target.nope()          # ⇒ AttributeError，⛔ 不會印任何 ✗
'''


def main():
    print("=" * 60)
    print("mutate.py 自測（不碰 repo 的任何 .py）")
    print("=" * 60)
    d = tempfile.mkdtemp(prefix="mut_")
    _old_here = M.HERE
    try:
        M.HERE = d
        tgt = os.path.join(d, "target.py")
        tst = os.path.join(d, "t_ok.py")
        crash = os.path.join(d, "t_crash.py")
        io.open(tgt, "w", encoding="utf-8").write(TARGET)
        io.open(tst, "w", encoding="utf-8").write(TEST % d)
        io.open(crash, "w", encoding="utf-8").write(TEST_CRASH % d)

        print("\n[1] 真的會紅的突變 ⇒ 抓到")
        rc, why = M.run_once(tgt, tst, "return 42", "return 43")
        ck("⭐ 回 0（抓到）", rc == 0, f"{rc} {why}")
        ck("  而且說得出紅幾條", "紅 1 條" in why, why)
        ck("⛔⛔ 而且**還原了**（⛔ 沒還原的話下一支測試會讀到突變版）",
           io.open(tgt, encoding="utf-8").read() == TARGET)

        print("\n[2] 什麼都沒影響的突變 ⇒ 沒抓到")
        rc2, why2 = M.run_once(tgt, tst, 'return "x"', 'return "y"')
        ck("  回 1（沒抓到）", rc2 == 1, f"{rc2} {why2}")
        ck("  而且明說是全綠", "全綠" in why2, why2)
        ck("  照樣還原", io.open(tgt, encoding="utf-8").read() == TARGET)

        print("\n[3] ⭐⭐ 錨點對不上 ⇒ **2**，⛔ 不是 1")
        rc3, why3 = M.run_once(tgt, tst, "return 4242", "x")
        ck("⭐⭐ 回 2（突變沒套上去），⛔ 不是 1（沒抓到）", rc3 == 2,
           f"{rc3} {why3}")
        ck("  ⚠ 而且明講這不是「斷言沒用」",
           "不是" in why3 and "斷言沒用" in why3, why3)
        ck("⛔ 錨點不對時**一個字都不可以動到**",
           io.open(tgt, encoding="utf-8").read() == TARGET)

        print("\n[4] 錨點出現多次 ⇒ 也是 2（⛔ 不可以只改第一個）")
        io.open(tgt, "w", encoding="utf-8").write(TARGET + "\nX = 42\n")
        rc4, why4 = M.run_once(tgt, tst, "42", "43")
        ck("  回 2，而且說得出出現幾次", rc4 == 2 and "2 次" in why4,
           f"{rc4} {why4}")
        ck("  ⭐ 而明示 `--count 2` 時就放行",
           M.run_once(tgt, tst, "42", "43", count=2)[0] == 0)
        io.open(tgt, "w", encoding="utf-8").write(TARGET)

        print("\n[5] ⭐ 自測**崩潰**（沒有任何 ✗）⇒ 照樣算抓到")
        rc5, why5 = M.run_once(tgt, crash, "return 42", "return 43")
        ck("⭐⭐ 崩潰也算抓到（⛔ 只數 ✗ 會回「沒抓到」）", rc5 == 0,
           f"{rc5} {why5}")
        ck("  而且講出它是**崩潰**，⚠ 不是默默算成紅",
           "崩潰" in why5, why5)
        ck("⛔ 崩潰的那一趟也要還原",
           io.open(tgt, encoding="utf-8").read() == TARGET)

        print("\n[6] ⛔ `__pycache__` **改檔之前**就要清掉")
        # ⚠ 第一版我只斷言「跑完之後 `__pycache__` 不在了」——⛔ 而 `finally`
        #   本來就會清一次 ⇒ 把**前面**兩次清掉的突變（M1）**沒紅**。
        #   ⭐ 而前面那兩次才是重點：`.pyc` 只看 mtime ＋ 檔案大小，
        #   同尺寸的突變（`42`→`43`）會讓 Python 判定 `.pyc` 還新
        #   ⇒ ⛔ **跑的是突變前的程式**。
        # ⇒ 改成驗**順序**：清 cache 一定要發生在「跑自測」**之前**。
        order = []
        _rc, _rr = M._clear_cache, M.subprocess.run

        def _spy_clear():
            order.append("clear")
            return _rc()

        def _spy_run(*a, **k):
            order.append("run")
            return _rr(*a, **k)

        try:
            M._clear_cache, M.subprocess.run = _spy_clear, _spy_run
            M.run_once(tgt, tst, "return 42", "return 43")
        finally:
            M._clear_cache, M.subprocess.run = _rc, _rr
        ck("⭐⭐ 跑自測之前**至少清過兩次**（改檔前、改檔後）"
           "⛔ 只靠 finally 那次等於沒清",
           order.count("clear") >= 2
           and order.index("run") > 1
           and all(x == "clear" for x in order[:order.index("run")]),
           str(order))
        ck("  ⚠ 而還原之後還要再清一次（⛔ 否則下一支讀到突變版）",
           order[-1] == "clear", str(order))

        print("\n[7] ⛔ 自測本身失敗時（不是崩潰）也不可以吞掉")
        io.open(tgt, "w", encoding="utf-8").write(
            TARGET.replace("return 42", "return 99"))
        rc7, _ = M.run_once(tgt, tst, 'return "x"', 'return "y"')
        ck("  原本就紅的情況照樣回 0（⚠ 這是使用者要自己注意的："
           "⛔ 突變前要先確認自測是綠的）", rc7 == 0, str(rc7))
    finally:
        M.HERE = _old_here
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
