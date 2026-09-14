#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_lowwater.py — 釘住 `lowwater.py`，**尤其是那兩個相反的方向**。

    python3 selftest_lowwater.py

## 這支要擋的四件事

① **`direction` 不可以有預設值。** 有預設值 ⇒ 下一個人加第九個低水位檔時
   不寫方向也會跑，而它會默默套上多數派那個方向
   ⇒ 那道閘門在**錯的方向**上守門，⚠ 而畫面上永遠是 ✓。
   ⇒ ⭐ 這裡用 `inspect.signature` 直接釘「沒有 default」，
     ⛔ 不是「呼叫時忘了傳會 TypeError」——後者換一版就可能加上預設值還是綠的。

② **兩個方向的判定是相反的。** 同一組 (水位 10, 本趟 12)：
   `down` ⇒ 退步（紅）、`up` ⇒ 進步（綠）。⛔ 少了任何一邊，照抄語意就過得了。

③ **退步的時候一個字都不寫。** 「低水位檔被寫大／寫小一次，
   那道閘門從此永遠綠」是這一族已知的傷害方向。

④ **★ 沒有動到 repo 真的那八個 `_*_low.txt`。**
   ⚠ 2026-09-14 早上 `_holiday_years_low` 就是被自測寫成 2 的
   （沙箱導走漏了一個旋鈕）⇒ 這一條是那個坑的直接對策。
"""
import hashlib
import inspect
import io
import os
import sys
import tempfile

import lowwater as LW

HERE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(HERE, "data", "meta")

_n = [0, 0]


def ck(name, cond, detail=""):
    _n[0] += 1
    if cond:
        print(f"  ✓ {name}" + (f"　{detail}" if detail else ""))
    else:
        _n[1] += 1
        print(f"  ✗ {name}　{detail}")


def _digests():
    """repo 真的那八個低水位檔的逐位元指紋（不存在的記成 None）。"""
    out = {}
    for fn in sorted(os.listdir(META)) if os.path.isdir(META) else []:
        if fn.startswith("_") and fn.endswith("_low.txt"):
            out[fn] = hashlib.sha256(
                io.open(os.path.join(META, fn), "rb").read()).hexdigest()
    return out


BEFORE = _digests()

print("\n── ① `direction` 是必填的，⛔ 不可以有預設值 ──")
for fname in ("read", "ok", "improved", "write", "gate"):
    sig = inspect.signature(getattr(LW, fname))
    p = sig.parameters.get("direction")
    ck(f"`{fname}()` 有 direction 這個參數", p is not None)
    if p is not None:
        ck(f"⭐ `{fname}(direction=)` **沒有預設值**",
           p.default is inspect.Parameter.empty,
           f"default={p.default!r}")

for bad in ("min", "lower", "DOWN", "", None, 0):
    try:
        LW.ok(1, 1, bad)
        ck(f"direction={bad!r} 要被擋下來", False, "⛔ 沒有丟例外")
    except ValueError as ex:
        ck(f"direction={bad!r} 丟 ValueError", "direction" in str(ex))

print("\n── ② 兩個方向的判定是**相反**的 ──")
# 同一組數字，兩個方向的答案必須相反——⛔ 這是「照抄語意」唯一擋得住的地方
CASES = [
    # (水位, 本趟, down 該不該過, up 該不該過)
    (10, 12, False, True),
    (10, 8, True, False),
    (10, 10, True, True),      # 持平兩邊都算過
    (0, 0, True, True),
    (0, 1, False, True),
    (6, 2, True, False),       # ⚠ 就是 _holiday_years_low 被寫成 2 的那一組
]
for low, cur, want_d, want_u in CASES:
    ck(f"down：水位 {low}｜本趟 {cur} ⇒ {'過' if want_d else '⛔ 紅'}",
       LW.ok(cur, low, "down") is want_d)
    ck(f"up　：水位 {low}｜本趟 {cur} ⇒ {'過' if want_u else '⛔ 紅'}",
       LW.ok(cur, low, "up") is want_u)
ck("⭐ 六組裡至少有四組兩個方向的答案**不一樣**（⛔ 否則這節等於沒測）",
   sum(1 for _, _, d, u in CASES if d is not u) >= 4)

print("\n── ③ 沒有水位檔（第一趟）一律放行，⛔ 不是一律擋下 ──")
ck("down：low=None ⇒ 過", LW.ok(999999, None, "down") is True)
ck("up　：low=None ⇒ 過", LW.ok(0, None, "up") is True)
ck("down：low=None ⇒ improved（第一趟要寫下去）",
   LW.improved(999999, None, "down") is True)

print("\n── ④ 退步的時候**一個字都不寫** ──")
with tempfile.TemporaryDirectory() as td:
    p = os.path.join(td, "_x_low.txt")

    did, new = LW.write(p, 5, "down", today="2026-01-01")
    ck("第一趟（檔不存在）會寫下去", did is True and new == 5)
    ck("  寫出來的格式是 `值,日期`",
       io.open(p, encoding="utf-8").read() == "5,2026-01-01\n",
       repr(io.open(p, encoding="utf-8").read()))

    did, new = LW.write(p, 9, "down", today="2026-01-02")
    ck("⭐ down 退步（5→9）**不寫**", did is False and new == 5)
    ck("  檔案逐位元沒變", io.open(p, encoding="utf-8").read() == "5,2026-01-01\n")

    did, new = LW.write(p, 5, "down", today="2026-01-02")
    ck("down 持平（5→5）也不寫（⛔ 不改日期）",
       did is False and io.open(p, encoding="utf-8").read() == "5,2026-01-01\n")

    did, new = LW.write(p, 3, "down", today="2026-01-03")
    ck("down 改善（5→3）會寫", did is True and new == 3)
    ck("  檔裡是新值與新日期",
       io.open(p, encoding="utf-8").read() == "3,2026-01-03\n")

    q = os.path.join(td, "_y_low.txt")
    LW.write(q, 5, "up", today="2026-01-01")
    did, _ = LW.write(q, 3, "up", today="2026-01-02")
    ck("⭐ up 退步（5→3）**不寫**",
       did is False and io.open(q, encoding="utf-8").read() == "5,2026-01-01\n")
    did, new = LW.write(q, 7, "up", today="2026-01-03")
    ck("up 進步（5→7）會寫", did is True and new == 7)

    print("\n── ⑤ 讀壞掉的檔要回 (None, '')，⛔ 不可以丟例外 ──")
    for txt, why in [("", "空檔"), ("abc,2026-01-01", "值不是數字"),
                     ("\n", "只有換行"), ("12", "沒有日期那一半")]:
        z = os.path.join(td, "_z_low.txt")
        io.open(z, "w", encoding="utf-8").write(txt)
        v, d = LW.read(z, "down")
        if why == "沒有日期那一半":
            ck(f"{why} ⇒ 值讀得到、日期是空的", v == 12 and d == "")
        else:
            ck(f"{why} ⇒ (None, '')", v is None and d == "", f"{v!r},{d!r}")
    ck("檔不存在 ⇒ (None, '')", LW.read(os.path.join(td, "沒這個檔"), "up") == (None, ""))

    print("\n── ⑥ 目錄不在也不可以丟例外（⛔ 守門不可以自己變成失敗的原因）──")
    deep = os.path.join(td, "a", "b", "_d_low.txt")
    did, new = LW.write(deep, 1, "down", today="2026-01-01")
    ck("會自己造目錄", did is True and os.path.exists(deep))

    print("\n── ⑦ `gate()`：info＋check＋改善才寫 ──")

    class FakeRun:
        def __init__(self):
            self.infos, self.checks = [], []

        def info(self, k, v=""):
            self.infos.append((k, v))

        def check(self, k, cond, detail=""):
            self.checks.append((k, bool(cond), detail))

    g = os.path.join(td, "_g_low.txt")
    rl = FakeRun()
    ok1 = LW.gate(rl, g, 7, "down", "漏列筆數", today="2026-01-01")
    ck("第一趟：放行、⛔ 不產生 check", ok1 is True and not rl.checks)
    ck("  ⭐ 而它要**大聲說這一層沒驗過**",
       any("也不算驗過" in f"{k}{v}" for k, v in rl.infos),
       str(rl.infos))

    rl = FakeRun()
    ok2 = LW.gate(rl, g, 9, "down", "漏列筆數", today="2026-01-02")
    ck("退步 ⇒ check 是 False", ok2 is False and rl.checks[0][1] is False)
    ck("  標題講得出方向（down ⇒ 『沒有變多』）",
       "沒有變多" in rl.checks[0][0], rl.checks[0][0])
    ck("  ⛔ 退步不改檔",
       io.open(g, encoding="utf-8").read() == "7,2026-01-01\n")

    rl = FakeRun()
    ok3 = LW.gate(rl, g, 4, "down", "漏列筆數", today="2026-01-03")
    ck("改善 ⇒ check 是 True 且檔被下修",
       ok3 is True and rl.checks[0][1] is True
       and io.open(g, encoding="utf-8").read() == "4,2026-01-03\n")
    ck("  而且有一行「水位下修」", any("下修" in k for k, _ in rl.infos), str(rl.infos))

    h = os.path.join(td, "_h_low.txt")
    LW.gate(FakeRun(), h, 6, "up", "行事曆涵蓋年數", today="2026-01-01")
    rl = FakeRun()
    ok4 = LW.gate(rl, h, 2, "up", "行事曆涵蓋年數", today="2026-01-02")
    ck("⭐ up 退步（6→2，就是那次實例）⇒ check 是 False", ok4 is False)
    ck("  標題講得出方向（up ⇒ 『沒有變少』）",
       "沒有變少" in rl.checks[0][0], rl.checks[0][0])
    ck("  ⛔ 而那個檔**還是 6**（⚠ 被寫成 2 正是那道閘門從此永遠綠的方式）",
       io.open(h, encoding="utf-8").read() == "6,2026-01-01\n",
       io.open(h, encoding="utf-8").read())

    rl = FakeRun()
    LW.gate(rl, g, 1, "down", "漏列筆數", write_it=False, today="2026-01-04")
    ck("`write_it=False` ⇒ 檔不動",
       io.open(g, encoding="utf-8").read() == "4,2026-01-03\n")

print("\n── ⑨ ⭐⭐ 全 repo 掃一次：**沒有第九份實作** ──")
# ⛔ `selftest_no_dup.py` **抓不到這一族**：八份的函式本體長得都不一樣
#   （讀的檔名不同、回傳的形狀不同）⇒ 那道守門比的是 AST 函式本體，躲得過。
#   ⚠ CLAUDE.md 四點五第八次：「同一個判準的兩份實作，只要外觀不同
#     就躲得過那道守門」⇒ ⭐ 這一族要**自己**的守門。
import ast as _ast

_owners, _bad_impl, _dirs_seen, _skipped_selftests = {}, [], {}, []
for _fn in sorted(os.listdir(HERE)):
    if not _fn.endswith(".py") or _fn in ("lowwater.py", "selftest_lowwater.py"):
        continue
    _src = io.open(os.path.join(HERE, _fn), encoding="utf-8").read()
    if "_low.txt" not in _src:
        continue
    try:
        _t = _ast.parse(_src)
    except SyntaxError:
        continue
    # 這個檔宣告了哪幾個低水位檔（字串常值裡的檔名）
    _names = sorted({n2.value for n2 in _ast.walk(_t)
                     if isinstance(n2, _ast.Constant)
                     and isinstance(n2.value, str)
                     and n2.value.endswith("_low.txt")})
    if not _names:
        continue
    _owners[_fn] = _names
    # ⭐ 它有沒有走共用的那一份
    _uses = [n2.attr for n2 in _ast.walk(_t)
             if isinstance(n2, _ast.Attribute)
             and getattr(n2.value, "id", "") in ("lowwater", "_LW", "LW")
             and n2.attr in ("UP", "DOWN")]
    if _uses:
        _dirs_seen[_fn] = sorted(set(_uses))
    elif not _fn.startswith("selftest_"):
        _bad_impl.append(f"{_fn}（{','.join(_names)}）")
    else:
        # ⚠ `selftest_*.py` 提到這些檔名多半是**沙箱導走**或**斷言標題**
        #   （`selftest_holiday` 導 `H.SCHED_LOW`、`selftest_adj_gap` 的 ck 標題）
        #   ⇒ 它們不必走 `lowwater`。⛔ 而「選自測就放行」會讓下一道閘門
        #     藏進某支自測裡逃掉（`_err_cut_low` 本來就住在 `selftest_feed_days`）
        #   ⇒ ⭐ 所以下面那條**自己開檔**的掃描對**所有**檔生效，一個都不例外。
        _skipped_selftests.append(_fn)

ck(f"⭐ 掃到 {len(_owners)} 個檔宣告了低水位檔（⛔ 0 個跟全部乾淨長得一樣）",
   len(_owners) >= 8, str(_owners))
ck("⭐⭐ 每一個都走 `lowwater` 這一份（⛔ 有漏掉的就是第九份實作）",
   not _bad_impl, str(_bad_impl))
ck("⭐ 而這一族真的有**兩種相反**的方向在用（⛔ 只剩一種 ⇒ 有人把語意抄平了）",
   {"UP", "DOWN"} <= {d for ds in _dirs_seen.values() for d in ds},
   str(_dirs_seen))

# ⛔ 而「自己再寫一份讀寫」要擋在字面之外：掃 AST 找 `io.open(<那個常數>)`
# ⛔⛔ 這一條對**所有**檔生效（自測也算）——`_err_cut_low` 就住在
#   `selftest_feed_days.py` 裡，⚠ 下一道閘門一樣可能藏進某支自測。
#   ⭐ 判準是「**變數名以 LOW 結尾的東西被拿去開檔**」，
#   ⛔ 不是一份手抄的變數名清單（四點五：手抄清單會讓 `err2`／`e7` 全部逃掉）。
_own_rw = []
for _fn in sorted(os.listdir(HERE)):
    if not _fn.endswith(".py") or _fn in ("lowwater.py", "selftest_lowwater.py"):
        continue
    try:
        _t = _ast.parse(io.open(os.path.join(HERE, _fn), encoding="utf-8").read())
    except SyntaxError:
        continue
    for n2 in _ast.walk(_t):
        if not isinstance(n2, _ast.Call) or not n2.args:
            continue
        _isopen = (getattr(n2.func, "attr", "") == "open"
                   or getattr(n2.func, "id", "") == "open")
        # ⭐ 只看**裸的名字**（`io.open(LOW,...)`）——那才是「這個檔自己在讀寫」。
        #   ⛔ `io.open(H.SCHED_LOW,...)` 是 `Attribute`：自測把**別的模組**的路徑
        #     導到沙箱之後回頭核它寫了什麼，⚠ 那正是本 repo 要求的 ★ 斷言寫法
        #     （「每一個被導走的路徑都要有一條『★ 沒有動到 repo 真的 ___』」），
        #     ⛔ 不是第九份實作。把它也算進來 ⇒ 這條會擋掉唯一在做對事的那支。
        _arg = getattr(n2.args[0], "id", "")
        if _isopen and _arg.upper().endswith("LOW"):
            _own_rw.append(f"{_fn}:{n2.lineno}（{_arg}）")
ck("⭐⭐ 全 repo 沒有人自己開低水位檔來讀寫（⛔ 那就是第九份）",
   not _own_rw, str(_own_rw))
ck(f"  ⚠ 而 {len(_skipped_selftests)} 支自測只是提到檔名／導沙箱，"
   "上面那條仍然掃過它們",
   True, str(_skipped_selftests))

print("\n── ⑧ ★ 沒有動到 repo 真的那八個 `_*_low.txt` ──")
AFTER = _digests()
ck(f"★ repo 的 {len(BEFORE)} 個低水位檔逐位元沒變", BEFORE == AFTER,
   str({k: (BEFORE.get(k), AFTER.get(k))
        for k in set(BEFORE) | set(AFTER) if BEFORE.get(k) != AFTER.get(k)}))
# ⛔⛔ 這一條**不可以**寫成「一定要有 8 個」：那八個檔是 workflow 在 **main** 上
#   建立的 ⇒ 某些 ref 上它們**必然**不全在 ⇒ 斷言必然失敗
#   ⇒ 而這一步排在同步與 commit 之前 ⇒ 整條線被關掉。
#   ⚠ CLAUDE.md 六點五：「一條在某個環境下【必然】不成立的斷言，
#     等於把那個環境的整條線關掉」——已經踩過「套件在不在」與「在哪個 ref」兩次。
if len(BEFORE) < 8:
    # ⭐ 寫成**不會被讀成「驗過了」**的樣子（⛔ 一行 skipped 跟一行 ok 長得一樣）
    print(f"  ⚠⚠ **這一層沒跑**：這個 ref 上只有 {len(BEFORE)} 個 `_*_low.txt`"
          "（⛔ 它們由 workflow 在 main 上建立）⇒ 不算失敗，⛔ **也不算驗過**")
    # ⇒ 而「跳掉之後還有沒有人在守？」**有**：上面 ④~⑦ 全部走沙箱、
    #   ⑨ 掃的是原始碼——⛔ 兩節都不依賴這八個檔在不在，每一個 ref 都會跑。
    print("      ⇒ 守著的是 ④~⑦（沙箱）與 ⑨（掃原始碼），兩節都不看這八個檔")
else:
    ck("★ 而這一節真的有東西可比（⛔ 0 個檔跟全部沒變長得一樣）", len(BEFORE) >= 8,
       f"{len(BEFORE)} 個")

print(f"\n通過 {_n[0] - _n[1]}｜失敗 {_n[1]}")
sys.exit(1 if _n[1] else 0)
