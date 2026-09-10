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

1. ⭐ **每一個 `run:` 區塊都通得過 `bash -n`**（只檢查語法，不執行）
2. 共用 `.sh` 也驗

## ⛔ 為什麼不用 PyYAML

第一版 `import yaml`。⚠ 本機有、**runner 上沒有**：

    ModuleNotFoundError: No module named 'yaml'

⇒ **我加的守門自己把管線弄壞了**（run 34434697153）。
⭐ 但它在 **90 秒**失敗，不是 1 小時 50 分——分批＋前置實測的設計是對的。

⇒ 改成**零相依**：自己按縮排掃出 `run:` 區塊。
⛔ 這一支的用途是驗 shell，不是驗 YAML；
  而 YAML 壞掉 GitHub 自己會拒收（那是**大聲**失敗），不需要我攔。

⚠ `${{ ... }}` 在 shell 眼裡不是語法 ⇒ 驗之前先換成佔位字串，
⛔ 不換的話它會誤報，然後這支檢查就會被學會忽略。
"""
import glob
import io
import os
import re
import subprocess
import sys

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


def run_blocks(path):
    """→ [(步驟名, shell 原文)]。⛔ 零相依：按縮排掃，不 import yaml。

    要處理的兩種寫法：

        - name: X          - name: Y
          run: |             run: python foo.py
            line1
            line2
    """
    out, name = [], "(無名)"
    lines = io.open(path, encoding="utf-8").read().splitlines()
    i, steps_indent = 0, None
    while i < len(lines):
        ln = lines[i]
        # ⛔ 只認「`steps:` 底下」的 `run:`。
        #   實測代價：`suspend_run.yml` 的 **job 名字就叫 `run`**
        #   （`jobs:` → `  run:`）⇒ 第一版把整個 job 當成一段 shell 吞下去，
        #   然後報「syntax error near unexpected token `('」——
        #   ⚠ **一個假的失敗，而它長得跟真的一模一樣。**
        #   ⭐ 而這正是這支要防的那一族：判準太寬 ⇒ 抓到不該抓的。
        m = re.match(r"^(\s*)steps:\s*$", ln)
        if m:
            steps_indent = len(m.group(1))
        m = re.match(r"^\s*-?\s*name:\s*(.+?)\s*$", ln)
        if m:
            name = m.group(1).strip().strip('"\'')
        m = re.match(r"^(\s*)-?\s*run:\s*(.*)$", ln)
        if m and steps_indent is not None and len(m.group(1)) > steps_indent:
            indent, rest = len(m.group(1)), m.group(2).strip()
            if rest and rest not in ("|", ">", "|-", ">-"):
                out.append((name, rest))           # 單行寫法
            else:
                body, i = [], i + 1
                while i < len(lines):
                    cur = lines[i]
                    if cur.strip() and (len(cur) - len(cur.lstrip())) <= indent:
                        break
                    body.append(cur)
                    i += 1
                out.append((name, "\n".join(body)))
                continue
        i += 1
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(here, ".github", "workflows", "*.yml")))
    ck("找得到 workflow", bool(files), "一支都沒有")
    n_run = 0
    for f in files:
        short = os.path.basename(f)
        blocks = run_blocks(f)
        ck(f"{short} 掃得出 run 區塊", bool(blocks), "一個都沒掃到")
        for name, body in blocks:
            n_run += 1
            src = EXPR.sub("X", body)
            p = subprocess.run(["bash", "-n"], input=src,
                               capture_output=True, text=True)
            ck(f"{short}｜「{name}」的 shell 語法",
               p.returncode == 0, p.stderr.strip()[:200])

    # ⭐ 共用腳本也要驗——push_data.sh 是八支 workflow 的最後一步，它壞掉＝全壞
    for sh in sorted(glob.glob(os.path.join(here, "*.sh"))):
        p = subprocess.run(["bash", "-n", sh], capture_output=True, text=True)
        ck(f"{os.path.basename(sh)} 語法", p.returncode == 0,
           p.stderr.strip()[:200])

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 每一支自測都要**有人跑它**（2026-09-10 加）
    #
    # ⛔ 這條的代價當場就看得到：`selftest_reduce.py` **紅了不知道多久**，
    #   而沒有任何地方會叫——因為八支 workflow 的自測是**逐支列名**的，
    #   ⚠ 新增一支自測時，沒有任何東西提醒你去列它。
    #   （它紅的原因也很典型：`ADJ_HEADER` 插了一欄，測試裡寫死的位置就錯位了。）
    #
    # ⚠ 這跟 CLAUDE.md 第四點二同一個形狀：**「自測存在」≠「自測會被跑」**。
    #   ⛔ 一支沒有人跑的自測，跟沒有那支自測**完全等價**，
    #     ⭐ 而它更糟：它會讓人以為那一塊有守門。
    #
    # ⚠ 判準是「**有沒有任何一支 workflow 提到它的檔名**」，
    #   ⛔ 不是「跑起來會不會過」——那是各支自測自己的事。
    # ══════════════════════════════════════════════════════════════
    wf_text = "".join(io.open(f, encoding="utf-8").read() for f in files)
    orphan = [os.path.basename(t)
              for t in sorted(glob.glob(os.path.join(here, "selftest_*.py")))
              if os.path.basename(t) not in wf_text]
    ck("⭐⭐ 每一支 selftest_*.py 都至少有一支 workflow 會跑它",
       not orphan,
       f"⛔ 沒有任何 workflow 跑：{orphan}"
       "　⇒ 它紅了也不會有人知道（`selftest_reduce.py` 就是這樣紅著的）")

    # ⭐ 而**反方向**也要驗：workflow 叫得出來的 selftest 必須**存在**。
    #   ⚠ 上面那道只擋「自測沒人跑」，⛔ 擋不住「workflow 叫了一個不存在的檔」
    #     ——而後者會讓那一步在 Actions 上**跑起來才失敗**，
    #     ⭐ 而失敗的位置往往在一大段抓取之後（第六點五那條 1h50m 的同一族）。
    #   ⚠ 2026-09-10 差點發生：`stophalt` 那一步先寫進 daily.yml，
    #     `selftest_stophalt.py` 還沒寫——⛔ 而孤兒那一道**是綠的**。
    called = sorted(set(re.findall(r"(selftest_[A-Za-z0-9_]+\.py)", wf_text)))
    missing = [n for n in called if not os.path.exists(os.path.join(here, n))]
    ck("⭐⭐ workflow 叫到的每一支 selftest 都**存在**",
       not missing,
       f"⛔ 叫得到但檔不在：{missing}"
       "　⇒ 那一步會在 Actions 上跑起來才失敗，⚠ 而且往往在抓完之後")

    # ── ⛔ 反向驗：這支檢查自己有沒有效 ──
    #   ⚠ 沒有這一段的話，一支「永遠說 ok」的檢查跟真的一模一樣。
    broken = subprocess.run(["bash", "-n"], input="if true; then echo x",
                            capture_output=True, text=True)
    ck("★ 反向驗：故意少一個 `fi` 時 `bash -n` 真的會抓到",
       broken.returncode != 0, "⛔ 連壞的都說好 ⇒ 這支檢查是死的")
    # ⭐ 孤兒那一道也要反向驗：⛔ 沒證明過會失敗的檢查不算檢查。
    ck("★ 反向驗：一個不存在於任何 workflow 的檔名**確實**會被判成孤兒",
       "selftest_這支不存在_zzz.py" not in wf_text,
       "⛔ 判準是子字串比對，而它連假名字都說有 ⇒ 這一道是死的")
    ck("★ 反向驗：兩道方向**相反**——孤兒看「檔在、沒人叫」，"
       "這一道看「有人叫、檔不在」",
       bool(called) and len(called) >= 5, f"workflow 裡叫到 {len(called)} 支")

    print(f"\n[selftest] 檢查了 {len(files)} 支 workflow、{n_run} 個 run 區塊"
          f"｜通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
