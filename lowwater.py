#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lowwater.py — 「低水位檔」的**唯一一份**實作（CLAUDE.md 四點五第九次）。

★ 為什麼要有這一支（2026-09-14）
────────────────────────────────
要替 `tdcc.py` 加一條「累積週數只能往上」的閘門之前先 grep 一次 repo
——⛔ **低水位檔已經有八個，而讀寫實作至少七份**：

    _adj_gap_low        adj_gap.py              _delisted_low       delisted.py
    _err_cut_low        selftest_feed_days.py   _factor_limit_low   factor_limit_check.py
    _holiday_years_low  holiday.py              _missing_rows_low   missing_rows.py
    _otc_exright_adjgap_low  otc_exright_history.py
    _otc_reduce_gap_low      otc_reduce_history.py

⚠⚠ 而 `holiday.py` 的檔頭**自己就寫著**這一族最危險的地方：

    「⛔ 跟 `_factor_limit_low.txt` 存**最低值**方向相反——**別照抄語意**。」

⇒ ⭐ **八個檔、兩種相反的語意、七份各自的實作。**
⛔ 而 `selftest_no_dup.py` **抓不到**：七份的函式本體長得都不一樣
（讀的檔名不同、回傳的形狀不同）——正是四點五第八次那條講的
「同一個判準的兩份實作，只要外觀不同就躲得過那道守門」。

## ⛔⛔ `direction` 是**必填**的，而且**不可以有預設值**

預設值就是「照抄語意」那個坑的自動化版本：
下一個人加第九個低水位檔時，不寫 `direction` 也會跑，
而它會**默默套上多數派的那個方向**（六個 down／兩個 up）
⇒ 那個檔從此在錯的方向上守門，⚠ 而畫面上永遠是 ✓。

    direction="down"   記錄的量**只准往下**（越少越好：未歸因、超出漲跌停）
                       ⇒ 本趟 > 記錄值 就是**退步**
    direction="up"     記錄的量**只准往上**（越多越好：下市累積列數、行事曆涵蓋年數）
                       ⇒ 本趟 < 記錄值 就是**退步**

## ⛔⛔ 怎麼選方向：**問那個量會不會回到 0**

    DOWN 只能用在「**修得完**」的量——它應該收斂到 0
         （未歸因的缺口、超出漲跌停的筆數、砍錯誤訊息尾巴的地方）
    ⛔ **只會隨時間長大的量，一律不可以用 DOWN**
         ——那種量套上 DOWN，從某一天起**每天都紅**，然後被學會忽略。

⚠ 2026-09-14 實際踩到：`_missing_rows_low` 守的是「漏列**總筆數**」，
而每個交易日固定多 2~9 筆（那是 `parse_twse()` 跳過 `--` 的已知結構問題）：

    11:07Z 那趟   6,799 筆 ／ 可比 2,850 天   ✓ 綠
    16:22Z 那趟   6,807 筆 ／ 可比 2,851 天   ✗ 紅   ← 只差一個新的可比日

⇒ ⭐ 那不是「門檻訂太嚴」，是**量錯了東西**。
⇒ 處置不是換方向（UP 會讓它永遠綠），是**換一個會回到 0 的量**：
  `missing_rows.day_regressions()` 改成數「**既有的日子變差了幾天**」
  ——新的日子多幾筆是新資訊，⛔ 不是退步。

⭐ 全庫九個低水位檔照這條掃過一次（2026-09-14）：

    DOWN 六個｜⭐ 都是「修得完」的量（未歸因、超出漲跌停、砍尾巴）
    UP   三個｜⭐ 都是累積量（下市列數、行事曆年數、集保週數）⇒ 方向本來就對
    ⛔ 只有 `_missing_rows_low` 是「累積量 × DOWN」這個錯配 ⇒ 已改

## ⛔ 這一族的傷害方向是已知的

**低水位檔被寫小（往改善方向寫錯）一次，那道閘門從此永遠綠**，而畫面上是 ✓。
2026-09-14 早上 `_holiday_years_low` 被自測寫成 2 就是實例
（`selftest_holiday` 沙箱導走漏了一個旋鈕）。
⇒ 所以 `write()` **只在改善方向寫**，⛔ 而且每一支的自測都要有一條
「★ 沒有動到 repo 真的 `_xxx_low.txt`」。

## 用法

    import lowwater as LW

    low, lowday = LW.read(PATH, "down")         # 讀不到回 (None, "")
    LW.gate(rl, PATH, len(bad), "down",
            "⭐ 超出漲跌停的筆數**沒有變多**")    # info + check + 改善才寫

`gate()` 之外也可以只用 `read`／`ok`／`write` 三顆自己組
（`selftest_feed_days.py` 沒有 `rl`，走的就是那條）。
"""
import io
import os

import runlog

DOWN = "down"
UP = "up"
_DIRECTIONS = (DOWN, UP)


def _check_direction(direction):
    """⛔ 打錯字要**大聲**失敗，不可以靜靜套一個方向。

    ⚠ `direction="min"`／`"lower"`／`None` 都會走到這裡——
    而「靜靜套上多數派那個方向」正是這一支存在的理由。
    """
    if direction not in _DIRECTIONS:
        raise ValueError(
            f"direction 必須是 {DOWN!r} 或 {UP!r}，收到 {direction!r}"
            "　⇒ ⛔ 這裡**沒有預設值**：低水位檔有兩種相反的語意，"
            "照抄語意會讓那道閘門在錯的方向上守門，而畫面上永遠是 ✓")
    return direction


def read(path, direction):
    """→ (歷史水位, 那一天)；讀不到／壞掉回 `(None, "")`。

    ⚠ `direction` 在這裡**不影響回傳值**，要它是為了讓呼叫點
    **一定要把方向寫出來**——⛔ 讀的時候不寫，寫的時候就會抄錯。
    """
    _check_direction(direction)
    try:
        txt = io.open(path, encoding="utf-8").read().strip()
    except OSError:
        return None, ""
    parts = txt.split(",", 1)
    try:
        return int(parts[0].strip()), (parts[1].strip() if len(parts) > 1 else "")
    except (ValueError, IndexError):
        return None, ""


def ok(value, low, direction):
    """本趟的 `value` 有沒有退步。⛔ 沒有水位（第一趟）一律回 True。"""
    _check_direction(direction)
    if low is None:
        return True
    return value <= low if direction == DOWN else value >= low


def improved(value, low, direction):
    """本趟是不是**比水位更好**（⇒ 才可以改寫那個檔）。"""
    _check_direction(direction)
    if low is None:
        return True
    return value < low if direction == DOWN else value > low


def write(path, value, direction, today=None):
    """改善方向才寫。→ (有沒有寫, 檔裡的新值)。

    ⛔ **退步的時候一個字都不寫**——那正是「寫小一次，閘門從此永遠綠」的入口。
    ⚠ 寫不進去（唯讀、目錄不在）不丟例外：這一支是**守門的附帶動作**，
      ⛔ 不可以讓它自己變成那一趟失敗的原因。
    """
    _check_direction(direction)
    low, _ = read(path, direction)
    if not improved(value, low, direction):
        return False, low
    if today is None:
        today = runlog.now_tpe().strftime("%Y-%m-%d")
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        io.open(path, "w", encoding="utf-8").write(f"{value},{today}\n")
    except OSError:
        return False, low
    return True, value


def gate(rl, path, value, direction, title, detail="", write_it=True, today=None):
    """`read` → `rl.info` → `rl.check` → 改善才 `write`。→ 這一趟有沒有過。

    ⚠ `title` 只寫**那件事**（例如「超出漲跌停的筆數」），
    水位與方向由這裡補上去——⛔ 八個檔各自造一句話正是飄移的起點。
    """
    _check_direction(direction)
    low, lowday = read(path, direction)
    word = "最低" if direction == DOWN else "最高"
    arrow = "**沒有變多**" if direction == DOWN else "**沒有變少**"
    if low is None:
        rl.info(f"  ⚠ 沒有水位檔：{title}",
                f"第一趟只記錄不判定（本趟 {value:,}）"
                f"　⇒ ⛔ 不算失敗，⛔ **也不算驗過**"
                + (f"｜{detail}" if detail else ""))
        passed = True
    else:
        rl.info(f"  歷史{word}值", f"{low:,}（{lowday}）→ 本趟 {value:,}"
                "　⭐ 斷言用這個，不是用上一趟"
                "——否則補完之後門檻會停在低點")
        passed = ok(value, low, direction)
        rl.check(f"{title} {arrow}（歷史{word} {low:,}，{lowday}）",
                 passed,
                 f"本趟 {value:,} vs 歷史{word} {low:,}"
                 + (f"｜{detail}" if detail else ""))
    if write_it:
        did, new = write(path, value, direction, today=today)
        if did and low is not None:
            rl.info(f"  ⭐ 水位{'下修' if direction == DOWN else '上修'}",
                    f"{low:,} → {new:,}")
    return passed
