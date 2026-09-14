#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_ci_steps.py — 釘住 `ci_step.py`／`ci_report.py`。

    python3 selftest_ci_steps.py

## 這支要擋的四件事

① **紅掉的自測要被記下來，而那一步仍然 exit 0。**
   ⛔ 少了前半 ⇒ 回到原本那個坑（紅了沒人知道）；
   ⛔ 少了後半 ⇒ 一支離線自測會賠掉整趟抓到的資料。
   ⚠ 兩半**必須同時成立**，而它們在畫面上都是「那一步是綠的」。

② **`ci_report` 要在 `_last_run.md` 裡留下 ✗**，⛔ 而 `main()` 仍然回 0。

③ **「沒有台帳」跟「全部都綠」不可以長得一樣。**
   ⚠ 不是每一支 workflow 都有自測步驟 ⇒ 沒有台帳是**正常**的
   ⇒ ⭐ 要大聲說「這一層沒跑」，⛔ 不是印「全部通過」。

④ **★ 沒有動到 repo 真的 `_last_run.md` 與 `_ci_steps.tsv`。**
"""
import hashlib
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ci_report as R          # noqa: E402
import ci_step as S            # noqa: E402
import runlog                  # noqa: E402

REAL_LR = os.path.join(HERE, "data", "meta", "_last_run.md")
REAL_TSV = os.path.join(HERE, "data", "meta", "_ci_steps.tsv")


def _dig(p):
    return (hashlib.sha256(io.open(p, "rb").read()).hexdigest()
            if os.path.exists(p) else None)


B4 = (_dig(REAL_LR), _dig(REAL_TSV))

_n = [0, 0]


def ck(name, cond, detail=""):
    _n[0] += 1
    if cond:
        print(f"  ✓ {name}" + (f"　{detail}" if detail else ""))
    else:
        _n[1] += 1
        print(f"  ✗ {name}　{detail}")


d = tempfile.mkdtemp()
GREEN = os.path.join(d, "green.py")
RED = os.path.join(d, "red.py")
BOOM = os.path.join(d, "boom.py")
io.open(GREEN, "w").write("print('綠的')\n")
io.open(RED, "w").write("import sys\nprint('  ✗ 一條沒過')\nsys.exit(1)\n")
# ⚠ 第三種形狀：**炸掉**（traceback），⛔ 它不會印 ✗
#   （CLAUDE.md 第七點第二個陷阱：突變的「紅」不可以只數 ✗）
io.open(BOOM, "w").write("raise SystemExit(RuntimeError('炸了'))\n")

print("\n── ① 紅掉要被記下來，而那一步仍然 exit 0 ──")
TSV = os.path.join(d, "_ci_steps.tsv")
S.TSV = TSV
for path, want_rc, label in ((GREEN, 0, "綠的"), (RED, 1, "紅的"), (BOOM, 1, "炸掉的")):
    rc = S.main(["ci_step.py", path])
    ck(f"{label}：`ci_step` 本身 exit 0（⛔ 不可以賠掉那一趟）", rc == 0, f"rc={rc}")
rows = R.read(TSV)
ck("三支都被記下來了", rows is not None and len(rows) == 3, str(rows))
ck("  ⭐ 綠的記成 0", rows[0] == ("green.py", 0), str(rows[0]))
ck("  ⭐ 紅的記成非 0（⛔ 記成 0 = 回到原本那個坑）", rows[1][1] != 0, str(rows[1]))
ck("  ⭐⭐ **炸掉的也記成非 0**（⚠ 它不會印 ✗，只數 ✗ 會漏掉它）",
   rows[2][1] != 0, str(rows[2]))

print("\n── ② 台帳是**追加**的，⛔ 不是整份取代（四點六）──")
S.record("later.py", 0, TSV)
ck("追加之後前三列還在", len(R.read(TSV)) == 4, str(R.read(TSV)))

print("\n── ③ `ci_report`：留下 ✗，⛔ 而 main() 仍然回 0 ──")
old_lr, old_tsv = runlog.PATH, R.TSV
try:
    runlog.PATH = os.path.join(d, "_last_run.md")
    R.TSV = TSV
    rc = R.main([])
    ck("⭐⭐ `ci_report.main()` 回 0（⛔ 它不可以賠掉那一趟抓到的資料）",
       rc == 0, f"rc={rc}")
    t = io.open(runlog.PATH, encoding="utf-8").read()
    ck("⭐ 而 `_last_run.md` 裡那一塊是 ✗（⇒ 看得到）", "**✗**" in t,
       [l for l in t.splitlines() if "✗" in l][:2])
    ck("  而且**點名**是哪幾支紅的", "red.py" in t and "boom.py" in t,
       [l for l in t.splitlines() if "red.py" in l][:2])
    ck("  ⛔ 綠的那兩支不可以被列成紅的",
       not any("⛔ green.py" in l or "⛔ later.py" in l for l in t.splitlines()))
    ck("⭐ 報完就把台帳砍掉（⛔ 留著 ⇒ 下一趟把這一趟的紅列再報一次）",
       not os.path.exists(TSV))

    print("\n── ④ 「沒有台帳」⛔ 不可以長得像「全部都綠」──")
    ck("讀不到台帳回 None（⛔ 不是空 list：兩者處置不同）", R.read(TSV) is None)
    rc = R.main([])
    t2 = io.open(runlog.PATH, encoding="utf-8").read()
    ck("  ⭐ 而它大聲說「這一層沒跑」", "**這一層沒跑**" in t2,
       [l for l in t2.splitlines() if "這一層" in l][:1])
    ck("  ⛔ 而且**沒有**任何一句說全綠／通過",
       "全綠" not in t2.split("ci_steps")[-1].split("\n##")[0], "")
    ck("  而 main() 還是回 0", rc == 0)

    print("\n── ⑤ 全綠的那一趟要講得出**母體**（⛔ 0 不附正例數就是第七點那個坑）──")
    io.open(TSV, "w", encoding="utf-8").write("a.py\t0\nb.py\t0\n")
    R.main([])
    t3 = io.open(runlog.PATH, encoding="utf-8").read()
    blk = t3.split("ci_steps")[-1]
    ck("全綠時是 ok，⛔ 不是 ✗", "**✗**" not in blk.split("\n## ")[0], blk[:200])
    ck("  ⭐ 而它講得出跑了幾支（⛔ 「0 支紅」跟「0 支跑過」長得一樣）",
       "2 支全綠" in blk, [l for l in blk.splitlines() if "全綠" in l][:1])

    print("\n── ⑥ 壞掉的台帳列當成**紅的**，⛔ 不是忽略 ──")
    io.open(TSV, "w", encoding="utf-8").write("a.py\t0\nb.py\t這不是數字\nc.py\n")
    rows = R.read(TSV)
    ck("三列都讀回來", len(rows) == 3, str(rows))
    ck("  ⭐ 壞掉的那兩列是非 0（⇒ 會被報成紅的）",
       rows[1][1] != 0 and rows[2][1] != 0, str(rows))
finally:
    runlog.PATH, R.TSV = old_lr, old_tsv

print("\n── ⑦ ★ 沒有動到 repo 真的 `_last_run.md` 與 `_ci_steps.tsv` ──")
now = (_dig(REAL_LR), _dig(REAL_TSV))
ck("★ `_last_run.md` 逐位元沒變", B4[0] == now[0])
ck("★ `_ci_steps.tsv` 沒有被建立／改動", B4[1] == now[1])
# ⛔ 這一條**不可以**寫成「`_last_run.md` 一定要在」：它是 workflow 在 **main**
#   上寫的 ⇒ 某些 ref 上它必然不在 ⇒ 斷言必然失敗 ⇒ 整條線被關掉（六點五）。
if B4[0] is None:
    print("  ⚠⚠ **這一層沒跑**：這個 ref 上沒有 `data/meta/_last_run.md`"
          "（⛔ 它由 workflow 在 main 上寫）⇒ 不算失敗，⛔ **也不算驗過**")
    # ⇒ 而「跳掉之後還有沒有人在守？」有：①~⑥ 全部走 tempdir，
    #   ⛔ 一條都不依賴這個檔在不在 ⇒ 每一個 ref 都會跑。
    print("      ⇒ 守著的是 ①~⑥（全部走 tempdir），一條都不看這個檔")
else:
    ck("★ 而這一節真的有東西可比（⛔ 檔不存在跟沒變長得一樣）",
       B4[0] is not None, f"_last_run.md 存在={B4[0] is not None}")

print(f"\n[selftest] 通過 {_n[0] - _n[1]}｜失敗 {_n[1]}")
sys.exit(1 if _n[1] else 0)
