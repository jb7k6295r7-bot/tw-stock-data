#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑完之後寫一份摘要，並把「該檢查的事」變成程式自己檢查。

★ 為什麼要有這一支（2026-09-08）
────────────────────────────────
在這之前，每支腳本跑完都要靠人去 repo 逐檔比對才知道對不對。
2026-09-07 一天之內，四次「跑完了、workflow 是綠的」其實都有問題：

  ① TWSE 限流回 307 → 上市處置與注意整段沒收到
  ② 日期分隔符是點不是斜線 → 134 列日期全空
  ③ 鍵有空值 → 同一檔多列互相覆蓋
  ④ TWTAWU 對未來日期整發拒收 → 2026 整年沒抓到

**四個都不會讓程式失敗，全部是人工比對才發現的。**
把那些比對寫成 assert，跑完不過就 exit 1——**機器該做的事不要留給人做**。

用法
────
    import runlog
    rl = runlog.Run("suspend")
    rl.info("停牌", f"{n} 列")
    rl.check("空日期 0", empty == 0, f"實際 {empty} 列")
    return rl.finish()          # 有 check 失敗就回 1

輸出：data/meta/_last_run.md
  **每支腳本一個區塊，只覆蓋自己那一塊**，不會蓋掉別支的紀錄。
  這樣一次讀這個檔就知道整個資料庫最近一輪的狀況，不必逐檔去翻。
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
# ★ 一定要用 `__file__` 錨定，不可以用相對路徑。
#   相對路徑是相對 **CWD**，不是相對這支程式——GitHub Actions 的 CWD 剛好是 repo 根目錄，
#   所以看起來一直是對的；但只要有人從別的地方叫（selftest 把腳本複製到暫存目錄再跑，
#   CWD 仍然是 repo），就會**寫進真的 repo**，把別支的區塊蓋掉。
#   2026-09-08 實測：跑一次 `selftest_reduce.py` 就把 suspend 那一塊洗成 adjust。
#   ⚠ 這正是「不碰真的 data/」那句保證失效的方式，而且**看起來完全成功**。
_ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(_ROOT, "data", "meta", "_last_run.md")
# ⛔ 守門要比的是**repo 裡那個真的檔**，⚠ 不是 `PATH` 這個變數——
#   自測就是靠改 `PATH` 把輸出導到暫存檔的，
#   拿 `PATH` 來比等於「改了也照樣被擋」（第一版就是這樣，反向驗當場抓到）。
_REAL = PATH


class Run:
    def __init__(self, name, path=None):
        self.name = name
        self.path = path or PATH
        self.lines = []
        self.checks = []

    def info(self, label, value):
        self.lines.append(f"- **{label}**：{value}")
        return self

    def note(self, text):
        self.lines.append(f"- {text}")
        return self

    def check(self, label, ok, detail=""):
        """ok 為假就是這一趟有問題。detail 要寫**實際值**，不是重複 label。"""
        self.checks.append((label, bool(ok), detail))
        return self

    def _block(self):
        t = datetime.now(TPE).isoformat(timespec="seconds")
        bad = [c for c in self.checks if not c[1]]
        head = "✗ 有問題" if bad else "✓ 正常"
        # ⛔⛔ 2026-09-10 的教訓，做成程式而不是「我會記得」：
        #   我在**開發容器**裡跑了一次 `feeds.py --run` 當測試，
        #   而這個容器對交易所一律 403（是**我方閘道**擋的，不是交易所）。
        #   ⇒ 它把一塊 `feeds:margin ✗ 失敗 3 天` 寫進這份**跨 workflow 共用**的報告，
        #     還跟著我的 commit 上去。⚠ 那一塊看起來跟真的失敗一模一樣。
        #   ⭐ 這裡不擋寫入（本地跑 `missing_rows.py` 之類算本地資料的是正當的），
        #     但**一定要標出來**：讀的人要分得出「這是 Actions 跑的」還是
        #     「某人在容器裡跑的」——後者的網路結果一律不可信。
        where = ("" if os.environ.get("GITHUB_ACTIONS") == "true"
                 else "　⚠ **這一塊不是 Actions 跑的**（本機／開發容器；"
                      "⛔ 若內容含抓取結果，一律不可信：這裡對交易所是我方閘道 403）")
        out = [f"## {self.name}　{head}", f"", f"最後執行：{t}（台北）{where}", ""]
        out += self.lines
        if self.checks:
            out += ["", "檢查："]
            for label, ok, detail in self.checks:
                mark = "ok" if ok else "**✗**"
                out.append(f"- {mark}　{label}" + (f"　（{detail}）" if detail else ""))
        return "\n".join(out) + "\n\n"

    def finish(self):
        # ⛔⛔ 自測**永遠不可以**寫進真的 `_last_run.md`。
        #   ⚠ 上面 2026-09-08 那段註解講的就是這件事（`selftest_reduce.py` 把
        #   suspend 那一塊洗成 adjust），⭐ 而那之後只留了註解、**沒有守門**
        #   ⇒ 2026-09-11 又發生一次（`selftest_margin_universe.py` ⑧ 直接呼叫
        #   `halt_spans.main()`，把假資料的區塊寫進 repo 裡那個檔）。
        #   ⛔ 而它**看起來完全成功**：檔在、格式對、程式回 0。
        # ⇒ 判準是「跑的人是誰」，⚠ 不是「path 對不對」——
        #   自測正是**沒有**改 path 的那一個，所以只有這個方向擋得住。
        if (os.path.abspath(self.path) == _REAL
                and os.path.basename(sys.argv[0] or "").startswith("selftest_")):
            raise RuntimeError(
                f"⛔ `{os.path.basename(sys.argv[0])}` 想寫進真的 runlog "
                f"（{_REAL}）——⚠ 那會把 repo 裡的紀錄洗成假資料，"
                "而且不會有任何地方報錯。\n"
                "⇒ 改法：呼叫受測的 `main()` 之前先把 `runlog.PATH` 指到暫存檔"
                "（或給 `runlog.Run(name, path=...)`）。")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        old = ""
        if os.path.exists(self.path):
            old = open(self.path, encoding="utf-8").read()
        block = self._block()
        # 只換掉自己那一塊。用「## <name>　」開頭到下一個 ## 之間。
        pat = re.compile(r"^## " + re.escape(self.name) + r"　.*?(?=^## |\Z)",
                         re.S | re.M)
        if pat.search(old):
            new = pat.sub(block, old)
        else:
            header = ("# 各支腳本最近一次執行\n\n"
                      "**這個檔是給人看的**：一次讀完就知道整個資料庫最近一輪的狀況。\n"
                      "任何一塊標成 ✗ 就要去看該支的 log。\n\n")
            new = (old or header) + ("\n" if old else "") + block
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(new)

        bad = [c for c in self.checks if not c[1]]
        print(f"\n[runlog] 寫出 {self.path}")
        if bad:
            print(f"[runlog] ✗ {len(bad)} 項檢查沒過：", file=sys.stderr)
            for label, _ok, detail in bad:
                print(f"          - {label}" + (f"（{detail}）" if detail else ""),
                      file=sys.stderr)
            return 1
        return 0
