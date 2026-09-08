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
PATH = os.path.join("data", "meta", "_last_run.md")


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
        out = [f"## {self.name}　{head}", f"", f"最後執行：{t}（台北）", ""]
        out += self.lines
        if self.checks:
            out += ["", "檢查："]
            for label, ok, detail in self.checks:
                mark = "ok" if ok else "**✗**"
                out.append(f"- {mark}　{label}" + (f"　（{detail}）" if detail else ""))
        return "\n".join(out) + "\n\n"

    def finish(self):
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
