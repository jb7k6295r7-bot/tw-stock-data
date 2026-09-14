#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ci_report.py — 把 `ci_step.py` 記下的結果寫成一個 `runlog` 區塊。

⭐ 這一支的存在理由見 `ci_step.py` 檔頭：
`continue-on-error` 的自測紅了之後**沒有任何地方會說**。

## ⛔ 它自己**不可以**讓那一趟失敗

`continue-on-error` 存在的理由是正當的：一支離線自測不該賠掉整趟抓取
（那一趟抓到的資料會整批丟掉）。⇒ 這一支**一律 exit 0**。

⇒ ⭐ 可見性改由**資料**承擔：區塊寫進 `data/meta/_last_run.md`
⇒ 進 commit ⇒ 四條線讀得到，而且 `db_status` 也讀得到。
⛔ 而 log 裡那一行會捲掉——**捲掉的東西不算守門**。

## ⛔⛔ 而「沒有台帳」跟「全部都綠」長得一模一樣

⇒ 所以這一支在**找不到台帳**時要**大聲說這一層沒跑**，
⛔ 不可以印一行「全部通過」——那正是 CLAUDE.md 六點五那個坑。
⚠ 而找不到台帳是**正常**的：不是每一支 workflow 都有自測步驟。
"""
import io
import os
import sys

import runlog

_ROOT = os.path.dirname(os.path.abspath(__file__))
TSV = os.path.join(_ROOT, "data", "meta", "_ci_steps.tsv")


def read(path=None):
    """→ [(名字, rc), ...]；沒有台帳回 `None`。

    ⛔ 回 `None` 與回 `[]` **是兩件事**：
    前者是「這一趟根本沒有自測步驟」，後者是「有台帳但裡面沒有列」。
    ⚠ 兩者在畫面上長得一樣，而處置不同 ⇒ 這裡分開。
    """
    p = path or TSV
    if not os.path.exists(p):
        return None
    out = []
    for ln in io.open(p, encoding="utf-8").read().splitlines():
        if not ln.strip():
            continue
        name, _, rc = ln.partition("\t")
        try:
            out.append((name, int(rc)))
        except ValueError:
            out.append((name, -1))          # ⚠ 壞掉的列當成紅的，⛔ 不是忽略
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    keep = "--keep" in argv
    rl = runlog.Run("ci_steps")
    rl.info("⭐ 這一支在驗什麼",
            "`continue-on-error: true` 的自測步驟紅了，run 的 conclusion 仍然是 "
            "**success** ⇒ ⛔ 沒有任何地方會說。這一塊就是那個「說」。")
    rows = read()
    if rows is None:
        # ⭐ 寫成不會被讀成「驗過了」的樣子
        rl.info("⚠⚠ **這一層沒跑**",
                "這一趟沒有 `_ci_steps.tsv`（⇒ 沒有走 `ci_step.py` 的步驟）"
                "　⇒ ⛔ 不算失敗，⛔ **也不算驗過**")
        return rl.finish()
    red = [(n, rc) for n, rc in rows if rc != 0]
    rl.info("跑過的自測", f"{len(rows)} 支｜" + "、".join(n for n, _ in rows))
    for n, rc in red:
        rl.info(f"⛔ {n}", f"rc={rc}　⇒ 這一支紅了，"
                           "⚠ 而那一步是 `continue-on-error` ⇒ run 仍然是綠的")
    # ⛔ 這裡用 `rl.check`：它會讓**這個區塊**在 `_last_run.md` 裡標成 ✗，
    #   ⚠ 而 `main()` 仍然回 0（下面那一行）——⭐ 兩件事是分開的。
    rl.check("⭐⭐ 所有 `continue-on-error` 的自測都是綠的",
             not red,
             f"{len(red)} 支紅了：" + "、".join(n for n, _ in red) if red
             else f"{len(rows)} 支全綠")
    rl.finish()
    if not keep:
        try:
            os.remove(TSV)      # ⭐ 台帳是**單趟**的 ⇒ 報完就砍
        except OSError:         # ⛔ 留著的話下一趟會把上一趟的紅列再報一次
            pass
    # ⛔⛔ **一律 0**：這一支不可以賠掉那一趟抓到的資料（見檔頭）。
    return 0


if __name__ == "__main__":
    sys.exit(main())
