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

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 逐年分批的迴圈：**一批失敗不可以賠掉後面的批次**（2026-09-10 加）
    #
    # ⛔ run 104：`tib` 的 2023 那批有**一天**回 HTML 不是 JSON ⇒ 程式 exit 1
    #   ⇒ `set -e` 當場結束整個 step ⇒ **2024／2025／2026 三年一天都沒跑**。
    # ⚠ 而 CLAUDE.md 第四點寫的是「逐年分批 ⇒ **任何失敗最多賠一年**」
    #   ——⛔ 那句話當時**沒有被程式兌現**，而且沒有任何東西會說。
    #
    # ⇒ 判準：迴圈裡呼叫 `python` 的那一行必須帶 `|| RC=`，
    #   ⭐ 而且迴圈**之後**必須有一個「RC 不是 0 就 exit 1」
    #   （⛔ 只做前半 ＝ 把失敗吞掉，那比連坐更糟）。
    # ══════════════════════════════════════════════════════════════
    # ⭐ 判準抽成**一份**（第四點五）：逐年迴圈與 `RC-GUARD` 區塊共用它。
    def _rc_calls(body):
        """→ 該段裡呼叫 `python` 的行。⚠ 明示 `|| true` 的不算（那是刻意容錯）。"""
        return [ln for ln in body.split("\n")
                if re.search(r"^\s*python\s", ln) and "|| true" not in ln]

    def _rc_check(label, body, after):
        calls = _rc_calls(body)
        ck(f"{label}｜每個 python 呼叫都帶 `|| RC=`（⛔ 一行失敗不可以賠掉後面的）",
           bool(calls) and all("|| RC=" in ln for ln in calls),
           f"⛔ 沒帶的：{[ln.strip()[:60] for ln in calls if '|| RC=' not in ln]}")
        ck(f"{label}｜而**之後**要 `exit 1`（⛔ 不可以把失敗吞掉）",
           "RC" in after and "exit 1" in after, f"後面那一段：{after.strip()[:80]}")

    for f in files:
        short = os.path.basename(f)
        src = io.open(f, encoding="utf-8").read()
        for m in re.finditer(r"for Y in \$\(seq.*?\n(.*?)\n\s*done\n(.*?)\n",
                             src, re.S):
            _rc_check(f"{short}｜逐年迴圈", m.group(1), m.group(2))

        # ══════════════════════════════════════════════════════════════
        # ⭐⭐ `RC-GUARD`：**同一個 step 裡的多行**也會連坐（2026-09-11 加）
        #
        # ⛔ run 107：`otc-adj-official` 那一步的第 4 行 `otc_reduce_history.py`
        #   因為兩條**常駐假紅** exit 1 ⇒ `set -e` ⇒ 後面六行（含換供料本體
        #   `otc_adj.py --official` 與 `adjust.py`）**一行都沒跑**，全程 10 秒。
        #   ⇒ 四檔的除息事件沒進 `data/adj/` ⇒ ⚠ **那四檔今天的漲跌是錯的**。
        # ⚠ 跟 run 104（賠掉三年）是同一族，⛔ 只是當時只修了逐年迴圈。
        #
        # ⇒ 凡是標了 `RC-GUARD` 的 run 區塊，套用同一組判準。
        #   ⚠ 判準是**有沒有標記**，⛔ 不是「看起來像不像」——
        #     後者會對整個 repo 的每一個多行 step 誤判，然後被學會忽略。
        # ══════════════════════════════════════════════════════════════
        # ⚠ ⛔ 第一版用 regex 加 lookahead 抓區塊邊界——**它貪吃了整個檔**
        #   （run 區塊裡每一行都有縮排，`\n\S` 永遠等不到）⇒ 一次噴 12 條假違規。
        #   ⇒ 改成**照縮排切**：從 `run: |` 往下收，遇到縮排 ≤ 它自己的非空行就停。
        lines = src.split("\n")
        for i, ln in enumerate(lines):
            m = re.match(r"^( *)run: \|\s*$", ln)
            if not m:
                continue
            ind = len(m.group(1))
            body = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= ind:
                    break
                body.append(nxt)
            if not any("RC-GUARD" in b for b in body):
                continue
            _rc_check(f"{short}｜RC-GUARD 區塊（第 {i + 1} 行起）",
                      "\n".join(body), "\n".join(body[-3:]))

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
    # ⭐ 逐年迴圈那一道的反向驗：⛔ 沒證明過會失敗的檢查不算檢查。
    _bad = ('for Y in $(seq 1 3); do\n  python x.py\n  done\n  echo done\n')
    _calls = [ln for ln in re.search(r"for Y in \$\(seq.*?\n(.*?)\n\s*done",
                                     _bad, re.S).group(1).split("\n")
              if re.search(r"^\s*python\s", ln)]
    ck("★ 反向驗：一個**沒帶** `|| RC=` 的逐年迴圈確實會被判成不合格",
       _calls and not all("|| RC=" in ln for ln in _calls),
       f"⛔ 連沒帶的都說有 ⇒ 這一道是死的（掃到 {_calls}）")
    # ⭐ RC-GUARD 那一道的反向驗，⚠ 而且要**兩個方向**：
    _g_bad = "          # RC-GUARD\n          python a.py\n          python b.py\n"
    ck("★ 反向驗：`RC-GUARD` 區塊裡沒帶 `|| RC=` 的行**確實**掃得出來",
       len(_rc_calls(_g_bad)) == 2
       and not all("|| RC=" in ln for ln in _rc_calls(_g_bad)),
       f"⛔ 掃到 {_rc_calls(_g_bad)}")
    _g_ok = ("          # RC-GUARD\n          RC=0\n          python a.py || RC=1\n"
             "          python z.py || true\n")
    ck("★ 反向驗（另一方向）：明示 `|| true` 的行**不算**"
       "（⚠ 那是刻意容錯，⛔ 把它也判成違規會讓這道被學會忽略）",
       len(_rc_calls(_g_ok)) == 1
       and all("|| RC=" in ln for ln in _rc_calls(_g_ok)),
       f"⛔ 掃到 {_rc_calls(_g_ok)}")

    print(f"\n[selftest] 檢查了 {len(files)} 支 workflow、{n_run} 個 run 區塊"
          f"｜通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
