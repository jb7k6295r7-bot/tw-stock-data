#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_syntax_warnings.py — 全庫**一個 `SyntaxWarning` 都不准有**。

## ⛔ 為什麼這值得一支守門：警告會**混在正常輸出裡**，然後被讀成正常

2026-09-10 run 99 的 log 第三行：

    fetch.py:1068: SyntaxWarning: invalid escape sequence '\\d'
      舊的第一條規則是 `(\\d{2,3})\\s*年`（只認民國年），

⚠ 成因是我把一段**正規表示式**寫進了非 raw 的 docstring 裡
（那一段正是在解釋 `_same_day` 把 2021 讀成 1932 的那個 bug）。
⛔ 它不影響行為——⭐ **而那正是問題**：它會一直在那裡，
夾在一堆正常輸出中間，**下一個真的有意義的警告出現時，沒有人會注意到**。

⚠ 而 Python 只在**第一次編譯**時發這個警告 ⇒ 有 `__pycache__` 的機器上
**它根本不會出現** ⇒ ⛔ 本機看不到、Actions 上才看得到。
⇒ 這一支自己 `compile()`，⛔ 不靠 import。

## ⚠ 判準是「零」，而零要證明得出來

⛔ 「掃出 0 個」在這個專案裡從來不算結論（第七點）
⇒ 第 ② 節餵一段**已知會發警告**的程式，證明這支抓得到。
"""
import io
import os
import sys
import warnings

SKIP_DIRS = {".git", "__pycache__", "data", "docs"}


def scan(root):
    """→ [(檔名, 行號, 訊息)]。⛔ 自己 compile，不 import（import 會被快取跳過）。"""
    out = []
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".py"):
            continue
        p = os.path.join(root, fn)
        try:
            src = io.open(p, encoding="utf-8").read()
        except OSError:
            continue
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                compile(src, p, "exec")
            except SyntaxError as e:
                out.append((fn, e.lineno or 0, f"SyntaxError: {e.msg}"))
                continue
            for x in w:
                # ⛔⛔ 分類**不可以只認 `SyntaxWarning`**：同一件事在
                #   `compile()` 一個字串時，這個 Python 版本發的是
                #   **`DeprecationWarning`**（import 一個 .py 檔時才是
                #   `SyntaxWarning`）⇒ ⚠ 只認前者的話，這支會**永遠回 0 個**。
                #   ⭐ 第一版就是這樣寫的，而反向驗當場抓到它
                #     ——那正是「沒證明過會失敗的測試不算測試」的用處。
                #   ⇒ 判準改成**訊息內容**（`invalid escape sequence` 等），
                #     ⛔ 不是警告的類別。
                if (issubclass(x.category, SyntaxWarning)
                        or "escape sequence" in str(x.message)
                        or "is not" in str(x.message)):
                    out.append((fn, x.lineno, f"{x.category.__name__}: "
                                              f"{x.message}"))
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__)) or "."
    found = scan(here)
    n_ok = 0

    # ② ⛔ 反向先做：先證明這支抓得到，再報「0 個」。
    import shutil
    import tempfile
    sand = tempfile.mkdtemp(prefix="synw_")
    try:
        io.open(os.path.join(sand, "bad.py"), "w", encoding="utf-8").write(
            'def f():\n    """一段沒有 r 前綴的說明：`(\\d{2,3})` 年"""\n    return 1\n')
        io.open(os.path.join(sand, "good.py"), "w", encoding="utf-8").write(
            'def f():\n    r"""一段有 r 前綴的說明：`(\\d{2,3})` 年"""\n    return 1\n')
        got = scan(sand)
        if not any(f == "bad.py" for f, _l, _m in got):
            print("✗ 反向驗失敗：一段**已知**會發 SyntaxWarning 的程式沒被抓到 "
                  "⇒ 這支等於沒有在檢查任何東西")
            return 1
        if any(f == "good.py" for f, _l, _m in got):
            print("✗ 反向驗失敗：加了 `r` 前綴的**乾淨**程式被誤報 "
                  "⇒ 這支會天天紅，然後被學會忽略")
            return 1
        n_ok += 2
        print("  ok   反向驗：沒有 `r` 前綴的 regex docstring **確實**被抓到")
        print("  ok   反向驗：加了 `r` 前綴的**不會**被誤報")
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    if found:
        print(f"⛔ 全庫有 {len(found)} 個 SyntaxWarning／SyntaxError：\n")
        for fn, ln, msg in found:
            print(f"   {fn}:{ln}　{msg}")
        print("\n⇒ 正規表示式寫進說明時，那段字串要加 `r` 前綴。")
        print("⚠ 它不影響行為——⭐ 而那正是問題：它會一直夾在正常輸出裡，"
              "**下一個真的有意義的警告出現時，沒有人會注意到**。")
        return 1
    n_ok += 1
    print("  ok   ⭐ 全庫 SyntaxWarning：**0 個**"
          "（⚠ 而上面兩條反向驗證明了這個 0 是真的掃過）")
    print(f"\n[selftest] 通過 {n_ok}｜失敗 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
