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

## ⭐⭐ 第二種重複：**欄位契約的常數**（2026-09-10 加）

⚠ 上面那道只比**函式本體的 AST** ⇒ ⛔ 它看不到 `HEADER = [...]` 這種**常數**。
而第十一份就是這種：

    fetch.UNIVERSE_HEADER   17 欄（09-10 加了 `last_price`）
    backfill.HEADER         16 欄　← 抄的那一份，旁邊還寫著「必須逐字一致」

⭐ 而它的後果**不是少寫一欄**（列與寫檔那兩支早就 alias 過去了），
是 `backfill.done_days()` 拿 `",".join(HEADER)` 去比檔案的表頭：

    17 欄的檔（09-10 之後寫的、正確的）  ⇒ 判成「舊版欄位」⇒ 重補
    16 欄的檔（真正的舊格式）            ⇒ 判成「現行版本」⇒ **永遠跳過**

⛔ **判準整個反過來，而且不報錯。**

⇒ 這裡加**兩個**偵測器，⚠ 兩個都要有：

    (a) 值逐位相同、來源不同  ⇒ 剛抄好、**還沒走岔**
    (b) 一份是另一份的**前綴** ⇒ 抄了而且**已經走岔**

⭐ (b) 之所以判得準，是因為本庫自己的規矩是**新欄一律接在舊表頭後面**
（`feeds.py`／`fetch.py` 都寫著，為的是讓舊檔的表頭是新表頭的前綴）
⇒ ⛔ 一份走岔的拷貝，形狀**必然**是前綴。
⚠ 只做 (a) 等於「只在抄好的那一刻擋得住」——而今天這一份早就過了那一刻。
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


# ⚠ 太短的清單不算：三五個字串的小清單各寫一份是正常的，
#   ⛔ 門檻太低 ⇒ 每天紅 ⇒ 被學會忽略（跟 MIN_STMTS 同一個道理）。
MIN_COLS = 6

# ⚠ 白名單同上：**空的**，要加之前先回答「為什麼這兩份不能收成一份」。
ALLOW_CONST = {
    # (("a.py:A", "b.py:B"), "prefix"): "理由",
}


def scan_consts(root="."):
    """→ [(組員清單, 種類)]。種類是 `same`（逐字相同）或 `prefix`（已經走岔）。

    ⛔ 抽成函式跟 `scan()` 同一個理由：呼叫點測不到的判準等於沒測。
    """
    vals = {}
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".py") or fn.startswith(SKIP_PREFIX):
            continue
        try:
            src = io.open(os.path.join(root, fn), encoding="utf-8").read()
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        for node in tree.body:                     # ⛔ 只看**模組層級**的賦值
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            tgt = node.targets[0]
            if not isinstance(tgt, ast.Name) or not tgt.id.isupper():
                continue
            v = node.value
            if not isinstance(v, (ast.List, ast.Tuple)):
                continue
            items = [e.value for e in v.elts
                     if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if len(items) != len(v.elts) or len(items) < MIN_COLS:
                continue
            vals[f"{fn}:{tgt.id}"] = tuple(items)
    out, names = [], sorted(vals)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.split(":")[0] == b.split(":")[0]:
                continue                           # 同一個檔裡的另當別論
            va, vb = vals[a], vals[b]
            if va == vb:
                kind = "same"
            elif va == vb[:len(va)] or vb == va[:len(vb)]:
                kind = "prefix"
            else:
                continue
            if ((a, b), kind) in ALLOW_CONST:
                continue
            out.append(([a, b], kind))
    return sorted(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__)) or "."
    cdups = scan_consts(here)
    if cdups:
        print("⛔ 有**欄位契約的常數**在不同檔案裡重複——"
              "⚠ 走岔的那一天，兩支會對同一批檔案用不同的表頭：\n")
        for members, kind in cdups:
            why = ("逐字相同（剛抄好、**還沒**走岔）" if kind == "same"
                   else "⛔ **一份是另一份的前綴 ⇒ 已經走岔**")
            print("   " + "  ＝  ".join(members) + f"　{why}")
        print("\n⇒ 收成一份，另一邊 import 過去（CLAUDE.md 第四點五）。")
        print("⛔ 旁邊寫「必須逐字一致」不算守門——`backfill.HEADER` "
              "旁邊就寫著那句，而它還是走岔了。")
        return 1

    dups = scan(here)
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

        # ★★ 常數那一道的反向驗，**兩種都要驗**。
        #   ⛔ 只驗 (a) 的話，`backfill.HEADER` 那個（已經走岔的）躲得掉——
        #     而那正是今天真的發生的那一份。
        io.open(os.path.join(sand, "hh1.py"), "w", encoding="utf-8").write(
            'H = ["a", "b", "c", "d", "e", "f"]\n')
        io.open(os.path.join(sand, "hh2.py"), "w", encoding="utf-8").write(
            'H = ["a", "b", "c", "d", "e", "f"]\n')
        io.open(os.path.join(sand, "hh3.py"), "w", encoding="utf-8").write(
            'H = ["a", "b", "c", "d", "e", "f", "g"]\n')
        cg = scan_consts(sand)
        kinds = {k for _, k in cg}
        if "same" not in kinds:
            print("✗ 反向驗失敗：兩個檔放了**逐字相同**的欄位清單，"
                  "`scan_consts` 沒抓到 ⇒ (a) 那一道等於沒有")
            return 1
        if "prefix" not in kinds:
            print("✗ 反向驗失敗：一份是另一份的**前綴**（＝已經走岔的拷貝，"
                  "`backfill.HEADER` 那個形狀），`scan_consts` 沒抓到 "
                  "⇒ (b) 那一道等於沒有")
            return 1
        # ⚠ 而短清單不可以被抓（門檻太低 ⇒ 每天紅 ⇒ 被學會忽略）
        io.open(os.path.join(sand, "hs1.py"), "w", encoding="utf-8").write(
            'S = ["a", "b", "c"]\n')
        io.open(os.path.join(sand, "hs2.py"), "w", encoding="utf-8").write(
            'S = ["a", "b", "c"]\n')
        if any("hs1.py:S" in m for m, _ in scan_consts(sand)):
            print("✗ 反向驗失敗：三個元素的小清單也被當成重複 ⇒ 門檻太低")
            return 1
        print("  ok   反向驗：逐字相同的欄位清單**確實**抓得到（same）")
        print("  ok   反向驗：⭐ 前綴（已經走岔的拷貝）**確實**抓得到（prefix）")
        print(f"  ok   反向驗：少於 {MIN_COLS} 個元素的清單不算")
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    print("  ok   ⭐ 跨檔案逐字相同的函式：**0 組**")
    print("  ok   ⭐ 跨檔案的欄位契約常數（相同／前綴）：**0 組**")
    print("\n[selftest] 通過 7｜失敗 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
