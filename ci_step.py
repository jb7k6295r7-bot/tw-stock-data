#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ci_step.py — 跑一支自測，把結果**記下來**，然後**一律 exit 0**。

★ 為什麼要有這一支（2026-09-14）
────────────────────────────────
`daily.yml` 裡有 **62 個** `continue-on-error: true` 的步驟
⇒ ⛔ 它們紅了，run 的 conclusion 還是 **success**。

⚠ 而其中大多數是**抓資料**的步驟，它們呼叫的程式自己會寫 `runlog` 區塊
⇒ 紅了會在 `_last_run.md` 裡留下 ✗ ⇒ **看得到**。

⛔⛔ **13 支自測不是**：它們沒有 `runlog` 區塊
⇒ 紅了之後**沒有任何地方會說**，而 run 是綠的。

⇒ 實際發生過（2026-09-14 找到）：`selftest_adj_gap.py` 的一條斷言
要求現場**一定要有未歸因的樣本**才造得出「本輪高於水位」的情境，
⚠ 而未歸因收斂到 0 正是那一族的**目標**
⇒ 目標達成的那一天它必然紅，⛔ 而沒有任何地方會說。
（實測同一天：main 上 3 筆 ⇒ 綠；分支上 0 筆 ⇒ 紅。）

## ⛔ 而「這支自測紅了」與「這支自測沒被寫進 workflow」在畫面上一模一樣

兩種都是**綠的一趟**、兩種都**沒有人被告知**。
⚠ 後者已經有守門（`selftest_workflows.py`「每一支自測都至少有一支 workflow 會跑它」），
⛔ 而前者一直沒有。

## 用法

    python ci_step.py selftest_adj_gap.py

- 子行程的 stdout／stderr **原樣透出去**（⛔ 不吃掉，log 要看得到）
- 結果追加到 `data/meta/_ci_steps.tsv`
- ⭐ **一律 exit 0** ⇒ 這一支**取代** `continue-on-error`，行為一模一樣，
  ⛔ 差別只在「紅掉這件事被記下來了」

⚠ 而它**自己不判定**：判定在 `ci_report.py`，那一支把紀錄寫成 `runlog` 區塊
⇒ 進 `_last_run.md` ⇒ 進 commit ⇒ ⭐ **四條線讀得到**。
⛔ 分成兩支的理由：這一支要 `exit 0`，而判定那一支要講得出「哪幾支紅了」。
"""
import io
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
#: ⛔⛔ 2026-09-15 付過代價：這裡本來是一個**import 當下**就算好的常數。
#  ⇒ 自測要把它導走時，`ci_step.TSV` 與 `ci_report.TSV` 是**兩個旋鈕**，
#    ⚠ 而子行程（`python ci_step.py …`）**兩個都看不到**
#    ⇒ 一次突變跑（S1「多餘參數靜靜忽略」）就把 `x.py<TAB>2` 寫進 repo 真的台帳，
#    ⛔ 而它跟著 commit 上了分支 ⇒ probe run 101 讀到它
#    ⇒ **main 上的 `_last_run.md` 出現一塊「x.py 紅了」的假報告**。
#  ⇒ ⭐ 照 `mops.changes_path()` 那條：收成**一個**在呼叫當下才算的函式，
#    並吃一個環境變數 ⇒ 子行程也導得走。
TSV_ENV = "CI_STEPS_TSV"


def tsv_path():
    """單趟台帳的位置。⭐ 只有這一份實作（四點五），⛔ 不是 import 當下的常數。"""
    return os.environ.get(TSV_ENV) or os.path.join(
        _ROOT, "data", "meta", "_ci_steps.tsv")


def record(name, rc, path=None):
    """把一次結果追加進台帳。→ 寫進去的那一行。

    ⚠ 這是**追加**（`a`），⛔ 不是整份取代——CLAUDE.md 四點六：
    「任何『這一趟只知道自己那一部分』的寫入，一律是合併，不是取代」。
    ⭐ 而整份清空的責任在 `ci_report.py`（它跑完就砍檔），
    ⛔ 不在這裡：這一支只知道自己那一格。
    """
    line = f"{name}\t{rc}\n"
    p = path or tsv_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "a", encoding="utf-8").write(line)
    except OSError:
        pass                    # ⛔ 記不下來不可以害這一步失敗
    return line


def main(argv):
    if len(argv) < 2:
        print("用法：python ci_step.py <script.py> [args...]", file=sys.stderr)
        return 2
    # ⛔⛔ 2026-09-15 付過代價：`daily.yml` 裡有一行是**上一個 `run:` 的續行**
    #   ⇒ YAML 把單行純量折成一串 ⇒ 這支收到的是
    #     `selftest_mops_history.py python selftest_revenue_complete.py`
    #   ⇒ 它照樣跑第一支、照樣 rc=0，⚠ 而 `selftest_revenue_complete.py`
    #     **從來沒有被執行過**——⭐ 而「每一支自測都有人跑」那道守門看的是
    #     檔名有沒有出現在 workflow 文字裡 ⇒ 它一直是綠的。
    # ⇒ ⭐ 多的參數一律**大聲拒絕**：⛔ 靜靜忽略就是這次藏了多久的原因。
    if len(argv) > 2:
        print(f"⛔ ci_step 只收一支自測，實得 {argv[1:]}"
              "　⇒ ⚠ 多半是 YAML 把上一個 `run:` 的續行折進來了"
              "（那支自測其實沒有被跑）", file=sys.stderr)
        return 2
    name = os.path.basename(argv[1])
    rc = subprocess.call([sys.executable, argv[1]], cwd=_ROOT)
    record(name, rc)
    # ⭐ 寫成**不會被讀成「驗過了」**的樣子（⛔ 一行 skipped 跟一行 ok 長得一樣）
    print(f"[ci_step] {name} ⇒ rc={rc}"
          + ("" if rc == 0 else "　⛔ **這一支紅了**（本步驟仍然 exit 0，"
                               "⚠ 判定在這一輪最後的 `ci_report.py`）"))
    return 0                    # ⭐ 一律 0——這一支**就是** continue-on-error


if __name__ == "__main__":
    sys.exit(main(sys.argv))
