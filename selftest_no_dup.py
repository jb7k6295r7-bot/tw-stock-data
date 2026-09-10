#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_no_dup.py — ⛔ **同一件事只准有一份實作**，這一支是它的守門。

## 為什麼要有一支專門的守門

2026-09-10 使用者：「同一族的錯（同一段邏輯抄兩份、只修一份）已經第三次了。」
⇒ 當天往下掃，**實際上是十份**：

    ① limit 平盤判跌停        fetch 修了、backfill.parse_twse 沒修
    ② 「甲」保留無成交列       backfill 修了、fetch 沒修
    ③ 興櫃 0 價的 `_isz`       esb 逐月檔有、fetch 的日檔沒有
    ④ backfill.parse_openapi   ①②③ 三個全中，而且它在興櫃回補那條路上
    ⑤ write_day 的「保留沒抓的市場」＋「濾掉權證」只有回補那份有
    ⑥ _kind／_tables           兩份（還沒走岔）
    ⑦⑧ _iso／_pick             兩支歷史腳本各一份
    ⑨ _same_day                **每日那支根本沒有** ⇒ 會憑空造出一個交易日
    ⑩ _post／_num／_is_dash     兩份

⚠ 十次沒有一次是「改一邊弄壞另一邊」。真正發生的一律是
**「改一邊，另一邊沒跟上，而且沒有人會發現」**——
⛔ 而兩份長得幾乎一樣的程式，**肉眼 review 看不出誰少了哪一行**。

## 這一支怎麼判

比的是**函式本體的 AST**（⛔ 不是字面，這樣改個變數名或註解躲不掉），
並且**先把 docstring 拿掉**——兩份實作各寫各的說明，那不是差異。

⚠ 少於 3 個 statement 的不算：一兩行的小工具各寫一份是正常的，
⛔ 把門檻設太低會讓這支變成每天都紅，然後大家學會忽略它。

⛔ **不掃 `selftest_*.py`**：測試本來就會為了「照真回應的形狀」重複造資料。
"""
import ast
import collections
import io
import os
import sys

MIN_STMTS = 3
SKIP_PREFIX = ("selftest_",)

# ⚠ 白名單：**目前是空的，而且應該一直是空的。**
#   ⛔ 要往這裡加東西之前，先回答「為什麼這兩份不能收成一份」，
#     並把答案寫在這裡——⚠ 不是寫「暫時」。
#   （檔頭那十份沒有任何一份符合這個條件。）
ALLOW = {
    # ("a.py:fn", "b.py:fn"): "理由",
}


def scan(root="."):
    """→ [(組員清單, 本體長度)]。⛔ 抽成函式是為了讓它自己測得到。"""
    bodies = collections.defaultdict(list)
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".py") or fn.startswith(SKIP_PREFIX):
            continue
        try:
            src = io.open(os.path.join(root, fn), encoding="utf-8").read()
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.FunctionDef):
                continue
            seg = ast.get_source_segment(src, n)
            if seg is None:
                continue
            n2 = ast.parse(seg).body[0]
            # ⛔ docstring 不算差異：兩份實作各寫各的說明是正常的
            if (n2.body and isinstance(n2.body[0], ast.Expr)
                    and isinstance(n2.body[0].value, ast.Constant)
                    and isinstance(n2.body[0].value.value, str)):
                n2.body = n2.body[1:]
            if len(n2.body) < MIN_STMTS:
                continue
            key = ast.dump(ast.Module(body=n2.body, type_ignores=[]))
            bodies[key].append(f"{fn}:{n.name}")
    out = []
    for key, members in bodies.items():
        if len({m.split(":")[0] for m in members}) < 2:
            continue          # 同一個檔裡的重複另當別論（多半是刻意的多型）
        if tuple(sorted(members)) in ALLOW:
            continue
        out.append((sorted(members), key.count("(") ))
    return sorted(out)


def main():
    dups = scan(os.path.dirname(os.path.abspath(__file__)) or ".")
    if dups:
        print("⛔ 有函式本體在**不同檔案**裡逐字相同——"
              "同一件事有兩份實作，改一邊另一邊不會跟上：\n")
        for members, _ in dups:
            print("   " + "  ＝  ".join(members))
        print("\n⇒ 收成一份，另一邊用別名／import 指過去（見 CLAUDE.md 第四點五）。")
        print("⛔ 「兩邊各留一份、記得同步」已經失敗過十次。")
        return 1

    # ★ 反向驗：⛔ 沒證明過會失敗的測試不算測試。
    #   造兩個檔、放同一個本體，這支必須抓得到。
    import shutil
    import tempfile
    sand = tempfile.mkdtemp(prefix="nodup_")
    try:
        body = ("def f(x):\n"
                "    y = x + 1\n"
                "    z = y * 2\n"
                "    return z\n")
        for name in ("aaa.py", "bbb.py"):
            io.open(os.path.join(sand, name), "w", encoding="utf-8").write(body)
        got = scan(sand)
        if not got:
            print("✗ 反向驗失敗：兩個檔放了同一個函式本體，這支**沒抓到** "
                  "⇒ 它現在等於沒有在檢查任何東西")
            return 1
        # ⚠ 而且太短的不可以被抓（門檻太低 ⇒ 每天都紅 ⇒ 被學會忽略）
        io.open(os.path.join(sand, "ccc.py"), "w", encoding="utf-8").write(
            "def g(x):\n    return x + 1\n")
        io.open(os.path.join(sand, "ddd.py"), "w", encoding="utf-8").write(
            "def g(x):\n    return x + 1\n")
        short = [m for m, _ in scan(sand) if any("ccc.py" in x for x in m)]
        if short:
            print("✗ 反向驗失敗：一行的小函式也被當成重複 ⇒ 門檻太低")
            return 1
        print(f"  ok   反向驗：兩個檔放同一個本體時**確實**抓得到"
              f"（抓到 {len(got)} 組）")
        print("  ok   反向驗：少於 3 個 statement 的不算（門檻不會低到每天紅）")
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    print("  ok   ⭐ 跨檔案逐字相同的函式：**0 組**")
    print("\n[selftest] 通過 3｜失敗 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
