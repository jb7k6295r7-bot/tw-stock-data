#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_tdcc.py — 釘住集保週檔那道「累積週數只准往上」的閘門。

    python3 selftest_tdcc.py

## ⛔⛔ 這支要擋的第一件事：**閘門掛在一條走不到的路上**

2026-09-14 我加那道閘門時把它寫在 `main()` **最後面**，
⚠ 而 `main()` 在「這一週的檔已經存在」時**早就 return 了**
——⭐ 而那是**每天都會走的那條路**（一週只有一天會寫新檔）。

```
實測 daily run 49（2026-09-15 00:16 台北）：
  tdcc ✓ 正常｜「2026-09-11 已存在，跳過」
  ⛔ 而 `_tdcc_weeks_low.txt` **根本沒有被建立**
  ⇒ 那道閘門一週只跑一天，⚠ 而它要擋的事每天都可能發生
```

⇒ ⚠ 這正是 CLAUDE.md 第七點③那一族：**測了判準、沒測呼叫點**
——判準本身沒問題，⛔ 而它掛在一條正常情況下走不到的路上。
⭐ 所以這支的主角是「**每一條 return 之前都叫到了嗎**」，⛔ 不是 `weeks_gate` 本身。

## ⚠ 而它**不連外**

`tdcc.py` 的 `main()` 第一件事就是打端點（開發容器 403、runner 上要花時間）
⇒ 這支**只驗 `weeks_gate` 與呼叫點**，⛔ 不跑 `main()`。
⇒ 呼叫點那一半靠**掃原始碼的 AST**。
"""
import ast
import hashlib
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lowwater  # noqa: E402
import tdcc as T  # noqa: E402

REAL_LOW = os.path.join(HERE, "data", "meta", "_tdcc_weeks_low.txt")


def _dig(p):
    return (hashlib.sha256(io.open(p, "rb").read()).hexdigest()
            if os.path.exists(p) else None)


B4 = _dig(REAL_LOW)
_n = [0, 0]


def ck(name, cond, detail=""):
    _n[0] += 1
    if cond:
        print(f"  ✓ {name}" + (f"　{detail}" if detail else ""))
    else:
        _n[1] += 1
        print(f"  ✗ {name}　{detail}")


class FakeRun:
    def __init__(self):
        self.infos, self.checks = [], []

    def info(self, k, v=""):
        self.infos.append((k, v))

    def check(self, k, cond, detail=""):
        self.checks.append((k, bool(cond), detail))


print("\n── ① ⭐⭐ 每一條 return 之前都要叫到 `weeks_gate`（掃 AST）──")
_src = io.open(os.path.join(HERE, "tdcc.py"), encoding="utf-8").read()
_tree = ast.parse(_src)
_main = next((f for f in ast.walk(_tree)
              if isinstance(f, ast.FunctionDef) and f.name == "main"), None)
ck("找得到 `main()`", _main is not None)

# 每一個 `return rl.finish()` 之前，同一個 block 裡要有 weeks_gate(...)
def _returns_with_gate(node):
    """→ [(return 的行號, 它前面同一層有沒有 weeks_gate)]。"""
    out = []
    for blk in ast.walk(node):
        body = getattr(blk, "body", None)
        if not isinstance(body, list):
            continue
        for i, st in enumerate(body):
            if not (isinstance(st, ast.Return) and st.value is not None
                    and "finish" in ast.dump(st.value)):
                continue
            before = body[:i]
            has = any(isinstance(n, ast.Call)
                      and getattr(n.func, "id", "") == "weeks_gate"
                      for s in before for n in ast.walk(s))
            out.append((st.lineno, has))
    return out


_rets = _returns_with_gate(_main)
ck(f"⭐ `main()` 裡有 {len(_rets)} 個 `return rl.finish()`"
   "（⛔ 0 個代表這條掃描壞了）", len(_rets) >= 4, str(_rets))

# ⚠ 前面幾條是「端點掛了／欄位對不上」——那幾條**不必**叫閘門（目錄可能還沒建）。
#   ⭐ 要釘的是**「已存在，跳過」那一條**：它是每天都會走的。
_skip_ln = next((i + 1 for i, l in enumerate(_src.split("\n"))
                 if "已存在，跳過（--force 可覆寫）" in l), None)
ck("找得到「已存在，跳過」那一條路", _skip_ln is not None, str(_skip_ln))
_after_skip = [(ln, has) for ln, has in _rets if ln > (_skip_ln or 0)]
ck("⭐⭐ 「已存在，跳過」之後那個 return **前面有** `weeks_gate`"
   "（⛔ 這就是一週只守一天的那個 bug）",
   bool(_after_skip) and _after_skip[0][1],
   str(_after_skip[:2]))
_last = _rets[-1] if _rets else None
ck("⭐ 而正常寫完那一條也有", _last is not None and _last[1], str(_last))
_n_gate = sum(1 for n in ast.walk(_main)
              if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "weeks_gate")
ck("⭐ `weeks_gate` 在 `main()` 裡被叫**至少兩次**（跳過那條＋正常那條）",
   _n_gate >= 2, f"{_n_gate} 次")

print("\n── ② 方向是 `UP`，⛔ 不是 DOWN（週檔只會變多）──")
_dirs = [n.attr for n in ast.walk(_tree)
         if isinstance(n, ast.Attribute)
         and getattr(n.value, "id", "") == "lowwater"
         and n.attr in ("UP", "DOWN")]
ck("⭐⭐ 用到的方向**全部是 UP**（⛔ 抄成 DOWN ⇒ 週數變少也會綠）",
   _dirs and all(d == "UP" for d in _dirs), str(_dirs))

print("\n── ③ `weeks_gate` 自己：數目錄、退步要紅 ──")
with tempfile.TemporaryDirectory() as d:
    old_out, old_low = T.OUT_DIR, T.LOW
    try:
        T.OUT_DIR = os.path.join(d, "tdcc")
        T.LOW = os.path.join(d, "_tdcc_weeks_low.txt")
        os.makedirs(T.OUT_DIR)
        for w in ("2026-08-28", "2026-09-04", "2026-09-11"):
            io.open(os.path.join(T.OUT_DIR, f"{w}.csv"), "w").write("x\n")
        rl = FakeRun()
        ck("數得出 3 週", T.weeks_gate(rl) == 3)
        ck("  第一趟不判定（沒有水位檔）", not rl.checks, str(rl.checks))
        ck("  ⭐ 而水位檔被建立成 3",
           io.open(T.LOW, encoding="utf-8").read().startswith("3,"),
           io.open(T.LOW, encoding="utf-8").read())
        # ⛔ 少一週 ⇒ 要紅
        os.remove(os.path.join(T.OUT_DIR, "2026-08-28.csv"))
        rl = FakeRun()
        ck("⭐⭐ 週數從 3 掉到 2 ⇒ check 是 False", T.weeks_gate(rl) == 2
           and rl.checks and rl.checks[0][1] is False, str(rl.checks))
        ck("  ⛔ 而水位檔**還是 3**（⚠ 被寫小 = 那道閘門從此永遠綠）",
           io.open(T.LOW, encoding="utf-8").read().startswith("3,"),
           io.open(T.LOW, encoding="utf-8").read())
        # ⭐ 反向：多一週要綠並上修
        for w in ("2026-08-28", "2026-09-18"):
            io.open(os.path.join(T.OUT_DIR, f"{w}.csv"), "w").write("x\n")
        rl = FakeRun()
        ck("⭐ 反向：週數變多 ⇒ 綠，而且水位上修到 4",
           T.weeks_gate(rl) == 4 and rl.checks[0][1] is True
           and io.open(T.LOW, encoding="utf-8").read().startswith("4,"),
           io.open(T.LOW, encoding="utf-8").read())
        # ⛔ 目錄不存在不可以炸掉
        T.OUT_DIR = os.path.join(d, "沒這個目錄")
        rl = FakeRun()
        ck("⛔ 目錄不存在 ⇒ 回 0 而不是炸掉", T.weeks_gate(rl) == 0)
        ck("  ⭐ 而且明講「目錄是空的」（⚠ 0 週跟沒跑長得一樣）",
           any("目錄是空的" in f"{k}{v}" for k, v in rl.infos), str(rl.infos))
    finally:
        T.OUT_DIR, T.LOW = old_out, old_low

print("\n── ④ ★ 沒有動到 repo 真的 `_tdcc_weeks_low.txt` ──")
ck("★ 逐位元沒變（含「本來就不存在」這一種）", _dig(REAL_LOW) == B4,
   f"{B4} → {_dig(REAL_LOW)}")

print(f"\n[selftest] 通過 {_n[0] - _n[1]}｜失敗 {_n[1]}")
sys.exit(1 if _n[1] else 0)
