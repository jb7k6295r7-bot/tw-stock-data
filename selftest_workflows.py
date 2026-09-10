#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_workflows.py — 驗每一支 workflow 的 **YAML ＋ 裡面每一段 shell**。

## ⛔ 為什麼會有這一支：1 小時 50 分鐘

2026-09-10 run 34426373917（甲的第一批，2015 全年）：

    「回補」   ✅ success   01:41 → 03:31（**1 小時 50 分**）
    「Commit」 ❌ failure   03:31 → 03:31（**1 秒**）
      /home/runner/.../f5803943.sh: line 82: **syntax error: unexpected end of file**

⇒ **不是 git 的問題，是我的 shell 少了一個 `fi`。**
我用 Python 批次改 workflow 時，把 `if/else` 的 `else` 區塊從中間切掉，
**closing `fi` 一起被切走了**。

⚠ 而我當時「驗過」了——我跑的是 `yaml.safe_load()`。
⛔ **YAML 合法不代表裡面的 shell 合法**：對 YAML 來說 `run:` 只是一個字串。
⇒ 那一步從寫出來的那一刻就是壞的，**任何一趟都會失敗**，
  而我讓它帶著 1 小時 50 分鐘的資料去撞。

## ⇒ 這一支做兩件事

1. 每一支 workflow 的 YAML 解得開
2. ⭐ **每一個 `run:` 區塊都通得過 `bash -n`**（只檢查語法，不執行）

⚠ `${{ ... }}` 在 shell 眼裡不是語法 ⇒ 驗之前先換成佔位字串，
⛔ 不換的話它會誤報，然後這支檢查就會被學會忽略。
"""
import glob
import io
import os
import re
import subprocess
import sys

import yaml

EXPR = re.compile(r"\$\{\{[^}]*\}\}")
OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(here, ".github", "workflows", "*.yml")))
    ck("找得到 workflow", bool(files), "一支都沒有")
    n_run = 0
    for f in files:
        short = os.path.basename(f)
        try:
            d = yaml.safe_load(io.open(f, encoding="utf-8"))
        except Exception as ex:                                  # noqa: BLE001
            ck(f"{short} YAML 解得開", False, f"{type(ex).__name__}: {ex}")
            continue
        ck(f"{short} YAML 解得開", True)
        for job in (d.get("jobs") or {}).values():
            for st in (job.get("steps") or []):
                run = st.get("run")
                if not run:
                    continue
                n_run += 1
                src = EXPR.sub("X", run)
                p = subprocess.run(["bash", "-n"], input=src,
                                   capture_output=True, text=True)
                ck(f"{short}｜「{st.get('name', '(無名)')}」的 shell 語法",
                   p.returncode == 0, p.stderr.strip()[:200])
    # ⭐ 共用腳本也要驗——push_data.sh 是八支 workflow 的最後一步，它壞掉＝全壞
    for sh in sorted(glob.glob(os.path.join(here, "*.sh"))):
        p = subprocess.run(["bash", "-n", sh], capture_output=True, text=True)
        ck(f"{os.path.basename(sh)} 語法", p.returncode == 0,
           p.stderr.strip()[:200])

    # ── ⛔ 反向驗：這支檢查自己有沒有效 ──
    #   ⚠ 沒有這一段的話，一支「永遠說 ok」的檢查跟真的一模一樣。
    broken = subprocess.run(["bash", "-n"], input="if true; then echo x",
                            capture_output=True, text=True)
    ck("★ 反向驗：故意少一個 `fi` 時 `bash -n` 真的會抓到",
       broken.returncode != 0, "⛔ 連壞的都說好 ⇒ 這支檢查是死的")

    print(f"\n[selftest] 檢查了 {len(files)} 支 workflow、{n_run} 個 run 區塊"
          f"｜通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
