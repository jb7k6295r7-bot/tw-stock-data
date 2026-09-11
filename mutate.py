#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mutate.py — 跑一次「突變驗」：改一行程式，看自測**會不會紅**。

    python3 mutate.py --file adjust.py --test selftest_adjust_official.py \
        --label "M1 拿掉停牌缺口那一半" \
        --old '舊字串' --new '新字串'

⛔ 這一支不是方便，是**為了三個今天各踩一次的坑**（2026-09-11）。
⚠ 三次的形狀一模一樣：**突變看起來沒紅，而我差點據此刪掉一條有用的斷言。**

## ① `__pycache__`：跑的是突變**前**的程式

`.pyc` 只用 **mtime ＋ 檔案大小**判斷要不要重編。
⚠ 而「交換兩個 if 的順序」「換比較方向」都是**同尺寸**的
⇒ 同一秒改完就跑 ⇒ `.pyc` 被判定還新 ⇒ ⛔ **跑的是舊的那一份**。
⇒ 本支在**改之前、改之後、還原之後**各清一次。

## ② 只數 `✗`：崩潰不會印 `✗`

拿掉一個不存在的函式 ⇒ `AttributeError` ⇒ traceback，**一個 `✗` 都沒有**
⇒ `grep -c "✗"` 回 0 ⇒ ⛔ 看起來像「這條斷言沒用」。
⇒ 判準是 **`rc != 0` 或輸出裡有 `✗`**。

## ③ ⭐ 錨點沒對上：突變**根本沒套上去**

我把錨點字串抄錯一個字（少了「的」）⇒ 取代了 0 次
⇒ 跑的是**原版**⇒ 當然全綠 ⇒ ⛔ 又看起來像「這條斷言沒用」。
⇒ 本支在取代之前先數，**不是剛好一次就大聲失敗**，
   ⛔ 而且回非 0——它跟「這條突變沒被抓到」是**兩件完全不同的事**，
   ⚠ 混在一起看就是上面那個誤判。
"""
import argparse
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _clear_cache():
    shutil.rmtree(os.path.join(HERE, "__pycache__"), ignore_errors=True)


def run_once(path, test, old, new, label="", count=1):
    """→ (0 抓到 / 1 沒抓到 / 2 突變沒套上去, 說明)。**一定會還原**。"""
    src = io.open(path, encoding="utf-8").read()
    n = src.count(old)
    if n != count:
        return 2, (f"⛔⛔ **突變沒套上去**：錨點在 {os.path.basename(path)} 裡"
                   f"出現 {n} 次（要 {count} 次）"
                   "　⇒ ⚠ 這**不是**「這條斷言沒用」，是我的錨點抄錯了")
    _clear_cache()
    io.open(path, "w", encoding="utf-8").write(src.replace(old, new, count))
    _clear_cache()
    try:
        p = subprocess.run([sys.executable, test], cwd=HERE,
                           capture_output=True, text=True, timeout=900)
        out = p.stdout + p.stderr
        # ⛔ 判準是「rc 非 0 **或** 有 ✗」——崩潰不會印 ✗
        marks = sum(1 for ln in out.splitlines() if ln.lstrip().startswith("✗")
                    or ln.startswith("  ✗"))
        crashed = "Traceback (most recent call last)" in out
        red = p.returncode != 0 or marks > 0
        why = (f"紅 {marks} 條" if marks else "") + \
              (("｜" if marks else "") + "⚠ **崩潰**（traceback）" if crashed else "") + \
              ("" if red else "⛔ **全綠**")
        return (0 if red else 1), why or ("紅（rc=%d）" % p.returncode)
    finally:
        io.open(path, "w", encoding="utf-8").write(src)
        _clear_cache()


def main():
    ap = argparse.ArgumentParser(description="跑一次突變驗")
    ap.add_argument("--file", required=True, help="要改的程式")
    ap.add_argument("--test", required=True, help="要跑的自測")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--count", type=int, default=1,
                    help="錨點應該出現幾次（預設 1）")
    a = ap.parse_args()
    rc, why = run_once(os.path.join(HERE, a.file), os.path.join(HERE, a.test),
                       a.old, a.new, a.label, a.count)
    tag = {0: "✅ 抓到", 1: "⛔ 沒抓到", 2: "⛔⛔ 突變沒套上去"}[rc]
    print(f"{tag}　{a.label or a.old[:40]}　｜{why}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
