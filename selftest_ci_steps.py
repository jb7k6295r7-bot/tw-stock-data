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
# ⭐ 導走的旋鈕只有**一個**（環境變數），⛔ 不是 `S.TSV` 與 `R.TSV` 兩個
#   ——⚠ 兩個旋鈕遲早會漏掉一個，而漏掉那次寫的是 repo 真的台帳。
os.environ[S.TSV_ENV] = TSV
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
old_lr = runlog.PATH
try:
    runlog.PATH = os.path.join(d, "_last_run.md")
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
    runlog.PATH = old_lr

print("\n── ⑧ ⭐⭐ `ci_report` 那一步的**前提**：Commit 是 `if: always()` ──")
# ⛔⛔ `ci_report` 那一步故意**沒有** `continue-on-error`——理由是
#   「它炸掉時 run 要紅，⭐ 而資料照樣進 commit」。
#   ⚠ 而後半句完全靠下面這個事實：**Commit 那一步是 `if: always()`**。
#   ⇒ 有人把它拿掉的那一天，`ci_report` 一炸就會**賠掉整趟抓到的資料**，
#     ⛔ 而那正是這兩支程式當初要防的事。⇒ 這一條釘住那個前提。
_wf = os.path.join(HERE, ".github", "workflows", "daily.yml")
if not os.path.exists(_wf):
    print("  ⚠⚠ **這一層沒跑**：找不到 `.github/workflows/daily.yml`"
          "　⇒ ⛔ 不算失敗，⛔ **也不算驗過**")
else:
    _t = io.open(_wf, encoding="utf-8").read()
    _lines = _t.split("\n")
    _i = next((i for i, l in enumerate(_lines) if "run: python ci_report.py" in l), -1)
    ck("daily.yml 裡真的有 `ci_report.py` 這一步", _i >= 0)
    if _i >= 0:
        # 這一步自己**不可以**有 continue-on-error（見上面的理由）
        # ⛔⛔ 只看這一步**`- name:` 與 `run:` 之間那幾行設定**。
        #   ⚠ 兩次被自己的文字命中（CLAUDE.md：包含比對會命中一個很像的鄰居）：
        #     ① 我上面寫了一段註解解釋「為什麼這裡沒有 continue-on-error」
        #     ② 而這一步的**標題**就叫「⛔ continue-on-error 會把它藏起來」
        #   ⇒ ⭐ 判準要落在**設定行**上，⛔ 不是「這一步附近有沒有這串字」。
        _nm = max((j for j in range(_i, -1, -1)
                   if _lines[j].lstrip().startswith("- name:")), default=_i)
        _blk = [l for l in _lines[_nm + 1:_i]          # ⛔ 不含 name 那一行
                if not l.lstrip().startswith("#")]
        ck("⭐ 而它**沒有** `continue-on-error`（⛔ 有的話炸掉就沒人知道）",
           not any("continue-on-error" in l for l in _blk), str(_blk))
        ck("  ★ 而這一節真的看到設定行了（⛔ 空 list 跟「沒有那一行」長得一樣）",
           any("if:" in l or "timeout" in l for l in _blk), str(_blk))
        # 它之後的第一個 Commit 步驟要有 if: always()
        _after = _lines[_i:]
        _ci = next((j for j, l in enumerate(_after) if "name: Commit 回 repo" in l), -1)
        ck("⭐ `ci_report` **排在** Commit 之前（⇒ 那一塊來得及進 commit）", _ci >= 0)
        if _ci >= 0:
            ck("⭐⭐ 而 Commit 那一步是 `if: always()`"
               "（⛔ 拿掉 ⇒ ci_report 一炸就賠掉整趟抓到的資料）",
               "if: always()" in _after[_ci + 1], repr(_after[_ci + 1]))

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

# ══════════════════════════════════════════════════════════════════
# ⑨ ⛔⛔ 多餘的參數要**大聲拒絕**（2026-09-15 付過代價）
#
# `daily.yml` 裡有一行是**上一個 `run:` 的續行** ⇒ YAML 折成一個純量：
#   `python ci_step.py selftest_mops_history.py python selftest_revenue_complete.py`
# ⇒ 這支照樣跑第一支、照樣 rc=0，⚠ 而第二支**從來沒有被執行過**，
#   ⭐ 而「每一支自測都有人跑」那道守門看的是**檔名有沒有出現在 workflow 文字裡**
#   ⇒ 它一直是綠的。⇒ 「檔名在 workflow 裡」≠「它會被執行」（四點二）。
# ⇒ ⭐ 靜靜忽略多餘參數，就是這件事藏了那麼久的原因。
# ══════════════════════════════════════════════════════════════════
print("\n[⑨ 多餘參數]")
# ⛔⛔ 子行程要**把台帳導走**：⚠ `ci_step.TSV = …` 只改得到這個行程，
#   子行程看不到 ⇒ 2026-09-15 一次突變跑就把 `x.py` 寫進 repo 真的台帳，
#   ⛔ 而它跟著 commit 上分支 ⇒ main 的 `_last_run.md` 出現一塊假報告。
#   ⇒ ⭐ 走環境變數（`ci_step.tsv_path()` 吃它）——子行程也導得走。
_env9 = dict(os.environ, **{S.TSV_ENV: os.path.join(
    tempfile.mkdtemp(prefix="ci9_"), "_ci_steps.tsv")})
_ok9 = subprocess.run([sys.executable, os.path.join(HERE, "ci_step.py"),
                 "x.py", "python", "y.py"], capture_output=True, text=True,
                env=_env9)
ck("⑨.1 ⛔ 多給一支就**大聲拒絕**（rc≠0）"
   "（⚠ 靜靜忽略 ⇒ 那一支根本沒跑，而 rc 記成 0）",
   _ok9.returncode != 0, f"rc={_ok9.returncode}")
ck("⑨.2 而訊息要講出**為什麼**（YAML 續行）⇒ 讀的人才知道去改哪裡",
   "續行" in (_ok9.stderr + _ok9.stdout), (_ok9.stderr + _ok9.stdout)[:200])
# ⭐ 而**最重要的一條**：不管它拒絕與否，⛔ 都不可以寫到 repo 真的台帳
ck("⑨.3 ⛔⛔ 子行程**不會**寫到 repo 真的 `_ci_steps.tsv`"
   "（⚠ 環境變數導得走 ⇒ 突變跑也污染不了 repo）",
   _dig(REAL_TSV) == B4[1],
   f"⛔ 被動到了：{B4[1]} → {_dig(REAL_TSV)}")
ck("⑨.4 ⭐ `tsv_path()` 是**呼叫當下**才算的（⛔ 不是 import 當下的常數）"
   "——⚠ 兩個旋鈕遲早會漏掉一個",
   S.tsv_path is R.tsv_path and "CI_STEPS_TSV" == S.TSV_ENV,
   f"{S.tsv_path} vs {R.tsv_path}")

print(f"\n[selftest] 通過 {_n[0] - _n[1]}｜失敗 {_n[1]}")
sys.exit(1 if _n[1] else 0)
