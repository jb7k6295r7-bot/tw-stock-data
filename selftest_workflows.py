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
import ast
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


# ══════════════════════════════════════════════════════════════════
# ⛔⛔ 同一個 `run:` 裡的多行會**連坐**（`set -e`），而它已經吃掉東西了
#
# 2026-09-15 現場證據：`daily.yml`「除權息與減資（當月）」是五行裸跑，
#   `feeds:exright`／`reduce`／`parvalue`／`etfsplit` 四塊都是**今天 00:17**，
#   ⛔ 而第五行寫的 `otcparvalue` 那一塊停在 **2026-09-11**
#   ⇒ ⚠ 四天沒跑，而 run 是綠的、那一步也沒有紅。
#
# ⇒ 而全 repo 掃一次：**34 個**多呼叫的 run 區塊沒有 RC-GUARD。
# ⛔ 不能一次機械式全改：其中有些是**有順序相依**的（前一行的產出是後一行的輸入）
#   ⇒ 讓失敗的那一行後面照樣跑，可能寫出**錯的資料**，而那比連坐更糟。
#
# ⇒ ⭐ 所以這一道是一個**只能往下的台帳**（跟 `lowwater.DOWN` 同一個道理）：
#     ① 名單**外**出現新的沒守護區塊 ⇒ 紅（⛔ 不准再欠新的）
#     ② 名單**裡**的區塊已經守護好了 ⇒ 也紅（⭐ 逼人把名單刪短）
#   ⚠ 只做①的話名單會永遠停在 34：修好了沒有人會去刪它。
# ══════════════════════════════════════════════════════════════════
KNOWN_UNGUARDED = {
    ('backfill.yml', '驗還原因子／興櫃 0 價／回補的「跑過了」判準（零相依，共 0.3 秒）'),
    ('backfill.yml', '驗解析規則（空值寫法＋無成交列，離線）'),
    ('backfill.yml', '興櫃單日修補（把被刪掉的那一天補回去）'),
    ('backfill.yml', '回補'),
    ('daily.yml', '驗還原因子／興櫃 0 價／回補的「跑過了」判準（零相依，共 0.3 秒）'),
    ('daily.yml', '全市場三大法人（上櫃 TPEx）'),
    ('daily.yml', '融資融券與本益比（上市＋上櫃）'),
    ('daily.yml', '借券賣出餘額（上市＋上櫃）'),
    ('daily.yml', '官方創新板成分清單（逐日，回到 2021-06-28）'),
    ('daily.yml', '變更交易（全額交割）名單（逐日，回到 2015-01-01）'),
    ('daily.yml', '停止買賣中的名單（上市，⛔ 沒有歷史、漏一天永久少一天）'),
    ('daily.yml', '上櫃變更交易／分盤／管理股票（逐日）'),
    ('daily.yml', '個股融資融券成數調整（逐日）'),
    ('daily.yml', '終止上市（下市）清單'),
    ('daily.yml', '面額變更（歷史回補，每趟 30 個月）'),
    ('daily.yml', 'ETF 分割（歷史回補，每趟 30 個月）'),
    ('daily.yml', '算還原因子'),
    ('daily.yml', '上櫃減資／除權息的官方判準（各一發請求）'),
    ('daily.yml', '上櫃減資對帳'),
    ('daily.yml', '逐日 feed 的列數閘門（只讀，不連外）'),
    ('daily.yml', '還原因子 vs 交易所漲跌停（只讀，不連外）'),
    ('daily.yml', '發行股數對帳（上櫃，官方個股市值排行）'),
    ('daily.yml', '母體漏列規模（六張官方清單差集，不連外）'),
    ('daily.yml', '無成交列水位（哪幾天已是新語意，不連外）'),
    ('daily.yml', '上櫃除權息判準（官方當日，逐日累積）'),
    ('daily.yml', '漲跌家數（當天 ＋ 分批回補）'),
    ('feeds.yml', '驗還原因子／興櫃 0 價／回補的「跑過了」判準（零相依，共 0.3 秒）'),
    ('feeds.yml', '回補'),
    ('feeds.yml', '上櫃除權息與減資（FinMind 回補｜⛔ 免費層）'),
    ('feeds.yml', '上櫃除權息與減資（只補指定的幾檔｜⛔ 免費層）'),
    ('feeds.yml', '上櫃除權息歷史（官方公告區，只寫判準檔）'),
    ('feeds.yml', '上櫃減資歷史（官方公告區）＋逐筆掃我方 data/adj 缺哪些'),
    ('feeds.yml', '核對每一天的內容'),
    ('feeds.yml', '算還原因子'),
}


def check_rc_debt(files):
    """⭐ 沒有 RC-GUARD 的多呼叫區塊：**只准變少**。"""
    now = set()
    for f in files:
        short = os.path.basename(f)
        for name, body in run_blocks(f):
            calls = [ln for ln in body.split("\n")
                     if re.search(r"^\s*python\s", ln) and "|| true" not in ln]
            if len(calls) >= 2 and any("|| RC=" not in ln for ln in calls):
                now.add((short, name))
    added = sorted(now - KNOWN_UNGUARDED)
    fixed = sorted(KNOWN_UNGUARDED - now)
    ck("⛔⛔ 沒有新的「多行裸跑」區塊"
       "（⚠ `set -e` 會讓前一行掛掉時，後面幾行一次都不跑，而 run 是綠的）",
       not added, f"⛔ 新欠的：{[a[1][:40] for a in added]}")
    ck("⭐ 而名單裡已經修好的要**從名單刪掉**"
       "（⛔ 只擋新的 ⇒ 名單永遠停在原地，修好了沒有人會去刪它）",
       not fixed, f"⭐ 已修好、請從 KNOWN_UNGUARDED 刪除：{[a[1][:40] for a in fixed]}")
    ck(f"★ 而這一道真的掃到了（⛔ 0 個區塊跟全部通過長得一樣）｜目前欠 {len(now)} 個",
       len(now) + len(fixed) >= 20, f"只掃到 {len(now)} 個")


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

    # ⭐⭐ `.githooks/` 底下的 hook **也是 shell**，而 2026-09-16 之前
    #   **沒有任何地方驗它的語法**——⚠ 而六點五那一整節講的就是
    #   「shell 合法要在 commit 的那一刻驗」，⛔ 結果驗它的那支自己沒人驗。
    #   ⭐ 而母體大小自己要是一道斷言（第七點第九個）：
    #     ⛔ glob 掃不到（例如有人把 hook 改名或搬走）與「全部通過」長得一樣。
    _hooks = sorted(g for g in glob.glob(os.path.join(here, ".githooks", "*"))
                    if os.path.isfile(g))
    ck("⭐ `.githooks/` 底下真的有 hook（⛔ 掃到 0 個跟全部通過長得一樣）",
       len(_hooks) >= 1, f"{len(_hooks)} 個：{[os.path.basename(h) for h in _hooks]}")
    for _h in _hooks:
        _p = subprocess.run(["bash", "-n", _h], capture_output=True, text=True)
        ck(f".githooks/{os.path.basename(_h)} 語法", _p.returncode == 0,
           _p.stderr.strip()[:200])

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
    # ⛔⛔ 2026-09-15：這一道**要找兩個地方**，⚠ 而我是撞上去才知道的。
    #   回測線的 8 支自測住在 `backtest/`（⛔ 不在 repo 根），
    #   ⇒ 只找根目錄的話，任何一句提到 `selftest_exits.py` 的**註解**
    #     都會讓這一道紅——⚠ 而它紅得**沒有道理**：那個檔是存在的。
    #   ⭐ 而這正是第七點⑧那一族從另一邊咬：這一道**本來就**是比原始碼字串的
    #     （它問的是「有沒有人提到這個檔名」）⇒ ⛔ 它連**註解裡**的檔名也會撿走。
    #     ⚠ 這裡不改成 AST：比字串是這一道的**本意**（提到就算數），
    #     ⛔ 錯的是「該去哪裡找那個檔」，不是「該不該比字串」。
    SELFTEST_DIRS = (here, os.path.join(here, "backtest"))
    called = sorted(set(re.findall(r"(selftest_[A-Za-z0-9_]+\.py)", wf_text)))
    missing = [n for n in called
               if not any(os.path.exists(os.path.join(d, n)) for d in SELFTEST_DIRS)]
    ck("⭐⭐ workflow 叫到的每一支 selftest 都**存在**",
       not missing,
       f"⛔ 叫得到但檔不在（找過 {[os.path.basename(d) or '.' for d in SELFTEST_DIRS]}）：{missing}"
       "　⇒ 那一步會在 Actions 上跑起來才失敗，⚠ 而且往往在抓完之後")

    # ── ⭐⭐ `forward.yml` 那個「至少 N 支」的下限，**沒有人在守**（2026-09-16 加）
    #
    # ⛔ 突變 W2（把 `-lt 9` 改成 `-lt 0`）**全綠** ⇒ 那個下限可以被靜靜調小，
    #   ⚠ 而調小之後「glob 沒掃到 ⇒ 母體縮小」那件事就**再也不會紅**
    #   ——它正是第七點⑨那一族（母體被判準悄悄縮小），只是主詞換成門檻自己。
    #
    # ⭐ 判準是 **`下限 == backtest/ 底下自測的支數`**：
    #   ⛔ 用 `<=` 會放行「調小」（就是 W2）；
    #   ⛔ 用 `>=` 會在**加了一支還沒調**的那一刻紅——⚠ 而那是對的時機：
    #     兩者本來就該在**同一個 commit** 裡動（六點五：先改門檻 ⇒ main 必然紅）。
    _fw = os.path.join(here, ".github", "workflows", "forward.yml")
    if os.path.isfile(_fw):
        _m = re.search(r'\[\s*"\$N"\s+-lt\s+(\d+)\s*\]',
                       io.open(_fw, encoding="utf-8").read())
        _n_bt = len([n for n in os.listdir(os.path.join(here, "backtest"))
                     if n.startswith("selftest_") and n.endswith(".py")]) \
            if os.path.isdir(os.path.join(here, "backtest")) else 0
        ck("⭐⭐ `forward.yml` 的「至少 N 支」下限 == `backtest/` 底下的自測支數"
           "（⛔ 調小 ⇒ 母體縮小再也不會紅；⚠ 加了一支沒調也要紅，兩者該同一個 commit）",
           bool(_m) and int(_m.group(1)) == _n_bt,
           f"下限 {_m.group(1) if _m else '找不到'}｜實際 {_n_bt} 支")

    # ⛔⛔ 而**孤兒那一道刻意不擴到 `backtest/`**，理由要寫下來，
    #   ⚠ 否則下一個人會「順手補齊」，而那會讓它天天紅：
    #   `forward.yml` 跑那 8 支用的是 **glob ＋ `-m backtest.<name>`**
    #   ⇒ ⛔ **它們的檔名一個都不會出現在 workflow 文字裡**
    #   ⇒ 照基本名去找會判它們全是孤兒——⚠ 而它們每一支都真的有人跑。
    #   ⭐ 那一層的守門改由 `forward.yml` 自己帶：「跑了 N 支」且 N < 8 就紅
    #     （第七點⑨：母體大小自己要是一道斷言）。

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 而第三道：**自測本身必須零相依**（2026-09-15 加，付過兩次代價）
    #
    # CLAUDE.md 六點五寫死了：「第二步的自測是【零相依】的，⛔ 這是硬規定不是習慣」
    # ⚠ 而那條規矩**沒有任何地方在守**——它只寫在判準檔裡。
    #
    # ⛔ 實際發生（probe run 84／86，2026-09-15）：
    #   `selftest_tdcc.py` 的 ⑦ 節裸 `import pyarrow.parquet`
    #   ⇒ runner 上沒有 pyarrow ⇒ 這支 **traceback**（⛔ 不是印 ✗）
    #   ⇒ `set -e` 把同一個 job 後面**六個步驟**掐死，
    #     其中一個是「**把程式同步到 main**」⇒ 那兩趟什麼都沒搬。
    # ⚠ 而畫面上看起來只是「有一支自測紅了」——⛔ 沒有任何地方會說
    #   「因為它，另外六步沒跑」。
    #
    # ⇒ 判準：`selftest_*.py` 裡凡是 import 選用套件的，一定要包在 `try` 裡。
    #   ⭐ 而**包起來之後要做什麼**這支管不到（那是各支自己的事）——
    #     ⛔ 這道只擋「缺套件就整支炸掉」這一種。
    # ⚠ 而它跟上面兩道是同一族：
    #   「自測存在」≠「自測會被跑」≠「自測**跑得起來**」。
    # ══════════════════════════════════════════════════════════════
    OPTIONAL = ("pyarrow", "numpy", "pandas", "yaml", "certifi",
                "requests", "zstandard", "py7zr", "lxml", "bs4")
    naked = []
    for t in sorted(glob.glob(os.path.join(here, "selftest_*.py"))):
        tree = ast.parse(io.open(t, encoding="utf-8").read())
        guarded = {id(sub)
                   for n in ast.walk(tree) if isinstance(n, ast.Try)
                   for sub in ast.walk(n)
                   if isinstance(sub, (ast.Import, ast.ImportFrom))}
        for n in ast.walk(tree):
            if not isinstance(n, (ast.Import, ast.ImportFrom)):
                continue
            if id(n) in guarded:
                continue
            mods = ([a.name for a in n.names] if isinstance(n, ast.Import)
                    else [n.module or ""])
            for m in mods:
                if m.split(".")[0] in OPTIONAL:
                    naked.append(f"{os.path.basename(t)}:{n.lineno} {m}")
    ck("⭐⭐ 沒有任何自測**裸 import** 選用套件（⛔ 缺套件要印字，不是炸掉）",
       not naked,
       f"⛔ {naked}"
       "　⇒ 那一支在 runner 上會 traceback，⚠ 而 `set -e` 會把同一個 job 後面"
       "的步驟（含『把程式同步到 main』）一起掐死"
       if naked else f"掃了 {len(glob.glob(os.path.join(here, 'selftest_*.py')))} 支")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ **job 的 timeout 必須大於任何單一步驟的 timeout**（2026-09-15 加）
    #
    # ⛔⛔ `probe.yml` 本來 job 是 **15**，而「跑十四支探針」那一步**自己就是 15**
    #   ⇒ 探針一跑滿，整個 job 先被 job-level timeout 砍掉
    #   ⇒ 畫面上是 `cancelled`，⚠ 而真正的後果是**後面四步一步都沒跑**：
    #     「MOPS 橋接」「長期停止買賣探針」「Commit 回 repo」全部沒有
    #   ⇒ ⭐ **那一趟什麼都沒推**，而 run 的樣子只是「被取消」。
    # ⚠ 實測 2026-09-15 吃掉四趟（run 86／87／97／98，都在開始後約 15 分被砍）
    #   ——⛔ 而我一度把它讀成「基礎設施問題」，⚠ 那讓我少查了一整天。
    #
    # ⚠ 而判準**不是**「各步驟 timeout 的合計 > job」：
    #   `feeds.yml`／`daily.yml` 有一堆互斥的 `if:` 步驟，一趟只跑其中一個
    #   ⇒ 那樣寫會誤報兩支（實測：合計 459 與 450，而它們其實沒問題）。
    #   ⭐ 對的判準是**單一步驟 ≥ job**——那一步自己就吃得完整個 job。
    # ══════════════════════════════════════════════════════════════
    for path in files:
        txt = io.open(path, encoding="utf-8").read()
        lines = txt.split("\n")
        job = [int(m.group(1)) for m in
               (re.match(r"^    timeout-minutes:\s*(\d+)", l) for l in lines) if m]
        step = [(int(m.group(1)), i + 1) for i, l in enumerate(lines)
                for m in [re.match(r"^        timeout-minutes:\s*(\d+)", l)] if m]
        if not job:
            continue
        j = min(job)
        bad = [(v, ln) for v, ln in step if v >= j]
        ck(f"⭐⭐ {os.path.basename(path)}：沒有**單一步驟**的 timeout ≥ job 的 "
           f"({j} 分)（⛔ 有的話那一步吃得完整個 job，後面的步驟一步都不跑）",
           not bad,
           f"⛔ {[(v, f'行 {ln}') for v, ln in bad]}"
           "　⇒ 那一趟會顯示 `cancelled`，⚠ 而真正的後果是**什麼都沒推**")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 「蒐證」那一步要排在「修好」**之後**（2026-09-15 加）
    #
    # ⛔ `feeds.yml` 的 `otc-adj-official`：`otc_reduce_history.py` 與
    #   `otc_exright_history.py` **同時**做兩件事——抓官方判準檔，
    #   以及「逐筆掃我方 `data/adj` 缺哪些」。
    #   ⚠ 而它們排在 `adjust.py` **前面** ⇒ 掃到的是**還沒補之前**的狀態
    #   ⇒ ⭐ 這個 mode **每一趟都以那兩塊紅著收尾**，⛔ 即使這一趟補的
    #     正好就是它報的那幾筆（run 150 實測：09:33 報三筆缺、09:34 就補進去了）。
    # ⚠ 而「一道天天紅的閘門」的代價 CLAUDE.md 寫過：**會被學會忽略**。
    # ⇒ 判準：那兩支必須**也**出現在 `adjust.py` 之後。
    #   ⛔ 不是「只能在後面」——①那一次是拿官方判準檔當輸入，本來就該在前面。
    # ⚠ 這跟 `daily.yml` 那條（`adj_gap` 讀 transpose 的產出 ⇒ 要排在它後面）
    #   是**同一族**：**「讀別人產出的那一步」排在產出之前，量到的是上一趟。**
    # ══════════════════════════════════════════════════════════════
    # ⚠ `run_blocks()` 回的是 **(步驟名, shell 原文)**，⛔ 不是字串
    #   ——第一版我當成字串去 `in` ⇒ 每一塊都被 `continue` 掉
    #   ⇒ ⛔ **掃到 0 塊，而輸出跟「全部通過」一模一樣**（第七點④）。
    #   ⇒ ⭐ 所以底下多一條「這道判準真的掃到東西」。
    _evi = ("otc_reduce_history.py", "otc_exright_history.py")
    _seen = 0
    for path in files:
        for step, body in run_blocks(path):
            if "adjust.py" not in body:
                continue
            i_adj = body.rindex("adjust.py")
            for name in _evi:
                if name not in body:
                    continue
                _seen += 1
                ck(f"⭐⭐ {os.path.basename(path)}／{step}：`{name}` 也排在 "
                   f"`adjust.py` **之後**（⛔ 否則它量到的是補之前的狀態）",
                   body.rindex(name) > i_adj,
                   "⛔ 最後一次出現在 adjust.py 之前"
                   "　⇒ 這個 step 會**以那一塊紅著收尾**，"
                   "而它報的缺口可能就是同一趟補掉的")
    ck("★ 這道「蒐證排在修好之後」真的**掃到了**（⛔ 0 塊跟全部通過長得一樣）",
       _seen >= 2, f"{_seen} 塊")

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
        # ⛔⛔ 2026-09-15 當場抓到：這一條本來比的是文字裡有沒有 `exit 1`，
        #   ⚠ 而既有每一個區塊的寫法是 `exit $RC` ＋ 一句**註解**
        #   「⭐ 記下來之後仍然 exit 1：⛔ 吞掉失敗比連坐更糟。」
        #   ⇒ ⛔ **它一直是被那句註解滿足的**（第七點第八個：那幾個字在註解裡也有一份）
        #   ⇒ 把 `exit $RC` 整行刪掉、只留註解，這一條**照樣綠**。
        # ⇒ ⭐ 改成**先把註解剝掉**再比，而且 `exit $RC` 與 `exit 1` 都算
        #   （前者是這個 repo 的慣例，⛔ 而註解不算數）。
        _code = "\n".join(ln.split("#", 1)[0] for ln in after.splitlines())
        ck(f"{label}｜而**之後**真的有 `exit $RC`／`exit 1`"
           "（⛔ 比**程式**不比註解——註解裡也寫著 exit 1）",
           "RC" in after and ("exit $RC" in _code or "exit 1" in _code),
           f"後面那一段（剝掉註解）：{_code.strip()[:80]}")

    # ⛔⛔ 2026-09-13 當場踩到：這個 pattern 原本寫死 `for Y in $(seq`，
    #   ⚠ 而我把迴圈改成 `for Y in $YEARS`（為了支援 newest 順序）⇒ **一條都沒match**
    #   ⇒ 那兩道檢查**靜靜不再檢查**，而總數從 186 掉到 184——
    #   ⛔ 「掃到 0 個迴圈、全部通過」跟「掃到 2 個迴圈、全部通過」在紙上一模一樣。
    # ⇒ 兩件：① pattern 放寬成任何 `for Y in `
    #        ② ⭐ **數出來的迴圈數要自己是一道檢查**（下面 `_loops`）
    _loops = 0
    _loops_by = {}
    for f in files:
        short = os.path.basename(f)
        src = io.open(f, encoding="utf-8").read()
        for m in re.finditer(r"for Y in .*?\n(.*?)\n\s*done\n(.*?)\n",
                             src, re.S):
            _loops += 1
            _loops_by[short] = _loops_by.get(short, 0) + 1
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

    # ⭐⭐ 「取 main 的資料」一定要排在**用那份資料的步驟之前**。
    #   2026-09-12 付過代價：feeds.yml 的「取 main 的日檔與台帳」寫在
    #   `回補` **後面** 180 行 ⇒ ⛔ 回補讀的是**分支那份過期的 data/**，
    #   ⚠ 而那一步照樣 `skipped`／`success`，**沒有任何地方會說**。
    #   ⇒ 判準是**順序**，⛔ 不是「有沒有這一步」——有這一步但排在後面，
    #     跟沒有這一步的後果一模一樣（CLAUDE.md 四點六）。
    def _order(text):
        """→ (取 main 那一步的位置, 用它的那一步的位置)；找不到回 None。"""
        a = text.find("- name: 取 main 的日檔與台帳")
        b = text.find("- name: 回補")
        return (a, b) if a >= 0 and b >= 0 else None

    _fe = io.open(".github/workflows/feeds.yml", encoding="utf-8").read()
    _o = _order(_fe)
    ck("★ feeds.yml：「取 main 的日檔與台帳」排在「回補」**之前**",
       _o is not None and _o[0] < _o[1],
       f"⛔ 位置 {_o} ⇒ 回補拿到的是分支那份過期的 data/")
    # 反向驗（⛔ 沒證明過會失敗的檢查不算檢查）
    _rev = "x\n      - name: 回補\ny\n      - name: 取 main 的日檔與台帳\n"
    _ro = _order(_rev)
    ck("★ 反向驗：把兩步對調的 workflow **確實**會被判成不合格",
       _ro is not None and not (_ro[0] < _ro[1]),
       f"⛔ 對調了還說通過（位置 {_ro}）⇒ 這一道是死的")

    # ⛔ 判準要**指名那一支**：`_loops >= 1` 全庫加總的話，
    #   feeds.yml 的迴圈改寫法時 backfill.yml 那個還在 ⇒ 照樣綠（突變 M1 實測）。
    ck("★ `feeds.yml` 的逐年迴圈真的**掃到了**（⛔ 掃到 0 個跟全部通過長得一樣）",
       _loops_by.get("feeds.yml", 0) >= 1,
       f"⛔ feeds.yml 只掃到 {_loops_by.get('feeds.yml', 0)} 個 `for Y in …`"
       "　⇒ 多半是迴圈改寫法了、而這道 pattern 沒跟上")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ `order: newest` 那一支：⛔ 不比字串，**真的把那幾行交給 bash 跑**
    #
    # 使用者 2026-09-13 要「先跑 2026 的讓我先用」⇒ 逐年順序要能反過來。
    # ⚠ 而「順序錯了」的表現是：它照樣成功、照樣推、照樣寫 runlog，
    #   ⛔ 只是先補的是 2015——**要三小時之後才看得出來**。
    # ⇒ 這一節把 workflow 裡算 `YEARS` 的那幾行抽出來，兩種 order 各跑一次。
    # ══════════════════════════════════════════════════════════════
    _fe = io.open(".github/workflows/feeds.yml", encoding="utf-8").read()
    _m = re.search(r"( *Y0=.*?\n)(.*?\n *fi\n)", _fe, re.S)

    def _years(order):
        """→ bash 真的算出來的年份序列（字串）。⛔ 算不出來回 ''。"""
        if not _m:
            return ""
        frag = (_m.group(1) + _m.group(2)).replace(
            "${{ inputs.start }}", "2015-01-01").replace(
            "${{ inputs.end }}", "2026-09-12").replace(
            "${{ inputs.order }}", order)
        r = subprocess.run(["bash", "-c", frag + "\necho $YEARS"],
                           capture_output=True, text=True)
        return " ".join(r.stdout.split())

    _old, _new = _years("oldest"), _years("newest")
    ck("★ `order=oldest` ⇒ bash 真的算出 2015 → 2026",
       _old.startswith("2015 ") and _old.endswith(" 2026"), f"⛔ 算出 {_old!r}")
    ck("★⭐ `order=newest` ⇒ bash 真的算出 **2026 → 2015**"
       "（⛔ 不是比字串——把那一支拿掉時字串檢查照樣綠）",
       _new.startswith("2026 ") and _new.endswith(" 2015"), f"⛔ 算出 {_new!r}")
    ck("★ 反向驗：兩種順序**真的不同**，而且年份集合一樣"
       "（⛔ 只換順序，不可以換範圍）",
       bool(_old) and _old != _new and sorted(_old.split()) == sorted(_new.split()),
       f"oldest={_old!r}｜newest={_new!r}")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ YAML 本身合不合法。⛔ 這一道**本來完全沒有**，而它今天出事了
    #
    # CLAUDE.md 六點五 記的是「**YAML 合法 ≠ 裡面的 shell 合法**」，
    # ⇒ 我們做了 shell 那一半，⚠ 而 YAML 那一半因為 runner 上沒有 `yaml`
    #   被拿掉了，**從此沒有任何地方驗它**。
    #
    # 2026-09-13 的災情（`forward.yml`）：
    #     run: bash push_data.sh "forward: 前瞻紀錄（…）"
    #   單行 `run:` 的值裡有 `forward: `（冒號＋空白）⇒ YAML 讀成對映 ⇒ **整份解析失敗**。
    # ⛔⛔ 而 GitHub **照樣把它註冊成一支 workflow**（`state: active`），
    #   只是名字顯示成檔案路徑、`workflow_dispatch` **靜靜不存在**
    #   ——派工時才回「Workflow does not have 'workflow_dispatch' trigger」。
    #   ⚠ 排程那一半會不會跑？**沒有任何地方會說。**
    #
    # ⇒ 兩層：① 有 `yaml` 就真的 parse（本機 pre-commit 一定有）
    #        ② ⭐ 沒有也擋得住這一類：**單行 `run:` 的值含 `: ` 就要整串加引號**
    #          ——零相依，而且 runner 上跳不掉。
    # ══════════════════════════════════════════════════════════════
    try:
        import yaml as _yaml
    except ImportError:
        _yaml = None
    # ⛔⛔ 這裡**不可以用 `ck`**。第一版我寫成斷言 ⇒ runner 上沒有 `yaml`
    #   ⇒ 這一步 `exit 1` ⇒ ⛔ **九支 workflow 的第二步全部當場紅**，
    #   而「把程式同步到 main」在它後面 ⇒ 那一趟什麼都沒搬（實測 probe run 52）。
    # ⚠ 這一節本來就是「有就多驗一層」——⛔ 環境缺套件不是**這個 repo** 壞掉。
    # ⇒ 大聲印出來，但不算失敗；真正跳不掉的是下面那道零相依的。
    print("  " + ("--   有 `yaml`，多驗一層（parse／name／workflow_dispatch）"
                  if _yaml is not None else
                  "--   ⚠ 這台**沒有** `yaml` ⇒ 上面那一層整個沒跑，"
                  "只剩下面那道零相依的（⛔ 不要把這行讀成『驗過了』）"))
    if _yaml is not None:
        for f in files:
            short = os.path.basename(f)
            try:
                doc = _yaml.safe_load(io.open(f, encoding="utf-8"))
                bad = None
            except Exception as ex:                            # noqa: BLE001
                doc, bad = None, str(ex).replace("\n", " ")[:120]
            ck(f"{short}｜YAML 真的 parse 得過", bad is None, f"⛔ {bad}")
            if doc:
                # ⛔ YAML 1.1 把 `on:` 讀成布林 True ⇒ 要兩個鍵都問
                trig = doc.get(True, doc.get("on"))
                ck(f"{short}｜有 `name:` 與觸發條件"
                   "（⛔ 缺 name 時 GitHub 會拿檔案路徑當名字，那是解析壞掉的徵兆）",
                   bool(doc.get("name")) and bool(trig),
                   f"name={doc.get('name')!r} 觸發={trig!r}")
                # ⭐ 每一支都要有 `workflow_dispatch`，⛔ 不是「有觸發就好」。
                #   CLAUDE.md 四點六③：**排程與 push 觸發的一律是 `main`**
                #   ⇒ 要驗分支上剛加的東西，**只能** `workflow_dispatch` 指定分支。
                #   ⚠ 沒有它，分支上的新步驟永遠只能「等排程跑到」——而那跑的是另一份程式。
                ck(f"{short}｜有 `workflow_dispatch`"
                   "（⛔ 沒有的話，分支上剛改的東西沒有任何辦法驗）",
                   isinstance(trig, dict) and "workflow_dispatch" in trig,
                   f"⛔ 觸發只有 {list(trig) if isinstance(trig, dict) else trig}")

    # ⭐ 零相依那一道：單行 `run:`（⛔ 不是 `run: |`）的值含 `: ` 就一定要整串加引號。
    _rx = re.compile(r"^\s*run:\s*(?![|>])(.+)$")
    for f in files:
        short = os.path.basename(f)
        for i, ln in enumerate(io.open(f, encoding="utf-8").read().split("\n"), 1):
            m = _rx.match(ln)
            if not m:
                continue
            v = m.group(1).strip()
            quoted = (v[:1] == v[-1:] and v[:1] in ("'", '"'))
            ck(f"{short}:{i}｜單行 `run:` 的值含 `: ` 時有整串加引號"
               "（⛔ 沒加 ⇒ YAML 讀成對映 ⇒ 整份解析失敗，而 GitHub 照樣註冊）",
               (": " not in v) or quoted, f"⛔ {v[:70]}")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ `sync_code.sh` 的排除清單 ＝「main 是唯一寫入者」的樹
    #
    # ⚠ 2026-09-13 付過代價：`forward.yml` 在 main 上寫了
    #   `backtest/forward/runlog.md` 的 02:42 區塊，⇒ 同步那一步把**分支上那份舊的**
    #   搬過去 ⇒ 那一塊被刪掉（−4 行）。⛔ 而 `git diff` 看起來完全正常、那一趟是綠的。
    #   ⭐ 這正是 CLAUDE.md 四點六，只是主詞從 `data/` 換成 `backtest/forward/`。
    #
    # ⇒ 這一節**真的把那幾行交給 bash 跑**，⛔ 不是比字串——
    #   排除清單打錯字的話，它照樣同步、照樣綠，而累積檔會被蓋掉。
    # ══════════════════════════════════════════════════════════════
    _sc = io.open("sync_code.sh", encoding="utf-8").read()
    _m2 = re.search(r"(EXCLUDE_TREES=\"\n.*?\n\")", _sc, re.S)
    ck("★ `sync_code.sh` 有排除清單", bool(_m2), "⛔ 找不到 EXCLUDE_TREES")
    _spec = []          # ⛔ 先給預設值：下面那一層在 main 上是**唯一**的守衛，
                        #   ⚠ 而它讀 `_spec` ⇒ 抓不到區塊時要判紅，⛔ 不是 NameError
    if _m2:
        _frag = (_m2.group(1) + '\nSPEC=""\n'
                 'for T in $EXCLUDE_TREES; do SPEC="$SPEC :(exclude)$T"; done\n'
                 'echo $SPEC')
        _r = subprocess.run(["bash", "-c", _frag], capture_output=True, text=True)
        _spec = _r.stdout.split()
        ck("★ bash 真的算出 `:(exclude)data`（⛔ 少了它，別的 workflow 剛寫的資料會被蓋）",
           ":(exclude)data" in _spec, f"⛔ 算出 {_spec}")
        ck("★ bash 真的算出 `:(exclude)backtest/forward`"
           "（⛔ 少了它，main 上的前瞻紀錄會被分支那份舊的蓋掉）",
           ":(exclude)backtest/forward" in _spec, f"⛔ 算出 {_spec}")
    # ⛔ 比**非註解**那幾行，⚠ 不是「這個路徑在不在檔案裡」
    #   ——它在說明註解裡也有一份 ⇒ 第一版突變全綠（2026-09-13，今天第四次）。
    _scbody = "\n".join(ln for ln in _sc.split("\n")
                        if not ln.lstrip().startswith("#"))
    # ⛔ 而且要比**真的取檔那一行**：只比「這個路徑有沒有出現」的話，
    #   前面那道 `git cat-file -e` 就足以讓它綠，⚠ 而 checkout 那行早就壞了。
    _rulechk = [ln for ln in _scbody.split("\n")
                if "git checkout" in ln and "backtest/forward/RULE.md" in ln]
    ck("★ 而 `RULE.md` 有例外放行（⛔ 整個目錄排除的話，判準檔永遠到不了 main）",
       len(_rulechk) == 1, f"⛔ 取 RULE.md 的那一行：{_rulechk}")
    # ⭐ 累積檔**不可以留在這個分支上**——留著的話，排除清單一旦被拿掉就會再犯一次。
    #   ⚠ 這是第二道，跟排除清單是**兩層**，⛔ 不是重複。
    #
    # ⛔⛔ 2026-09-13 付過代價：第一版直接斷言「工作區裡沒有這些檔」，
    #   ⚠ 而它的**主詞是分支**——在 **main** 上那些檔本來就該在（forward.yml 寫的）
    #   ⇒ ⛔ 這一步在 main 上一跑就紅 ⇒ **九支 workflow 的第二步全部紅**，
    #     而「把程式同步到 main」排在它後面 ⇒ 那一趟什麼都沒搬。
    #   ⭐ 這跟今天早上那條 `yaml` 斷言是**同一個形狀**（六點五）：
    #     ⛔ 一條「在某個環境下必然不成立」的斷言，等於把整條線鎖死。
    # ⇒ 只在**不是 main** 的 ref 上驗；在 main 上**大聲印出這一層沒跑**。
    _ref = (os.environ.get("GITHUB_REF_NAME")
            or subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                              capture_output=True, text=True).stdout.strip())
    # ⭐⭐ 2026-09-15 加後兩個：`p4_types/` 的 `universe.csv` 與 `records.csv`。
    #   ⚠ 它們 09-15 之前是**回測線分支上的種子檔**，我一次性搬上 main
    #   ⇒ ⭐ **從那一刻起它們換了寫入者**：main 上的 `forward.yml` 每月 append
    #     （`universe.csv` 的 `first_seen` 取小／`last_seen` 取大是讀既有檔算的）
    #   ⇒ ⛔ 分支上再留一份，就是四點六那個「分支那份永遠是舊的」。
    # ⚠ 而同一個目錄的 `README.md` 與 `v0_…md` **不進這張清單**：
    #   它們是靜態文件、沒有人在 append ⇒ ⛔ 判準是**誰寫它**，不是「同一個目錄」。
    _accum = ("backtest/forward/runlog.md", "backtest/forward/state_N30.json",
              "backtest/forward/state_N40.json", "backtest/forward/_runs.jsonl",
              "backtest/forward/p4_types/universe.csv",
              "backtest/forward/p4_types/records.csv")
    if _ref == "main":
        # ⛔ 這一行要寫成**不會被讀成「驗過了」**的樣子（六點五）
        print("  --   ⚠ 這一趟在 **main** 上 ⇒ 「分支不留累積檔」那一層**整個沒跑**"
              "（⛔ 不要把這行讀成『驗過了』；那些檔在 main 上本來就該在）")
    else:
        for _bad in _accum:
            ck(f"★ 分支（{_ref}）上**沒有** `{_bad}`（⛔ 那是 main 上 forward.yml 寫的累積檔）",
               not os.path.exists(_bad),
               "⛔ 它在分支上 ⇒ 排除清單一旦失效就會蓋掉 main 的")
    # ⭐ 而**不論在哪個 ref**，排除清單都必須擋住它們——⛔ 上面那一層跳過時，
    #   這一層就是唯一的守衛，所以它不可以跟著跳過。
    for _bad in _accum:
        ck(f"★ 排除清單真的擋得住 `{_bad}`（⛔ 這一層在 main 上也要跑）",
           any(_bad.startswith(x[len(":(exclude)"):])
               for x in _spec if x.startswith(":(exclude)"))
           or _bad == "backtest/forward/RULE.md",
           f"⛔ 排除清單算出來是 {_spec}")

    # ⭐ 八支的同步段只准有一份實作（四點五）——⛔ 這一段本來逐字抄了八份。
    _inline = [os.path.basename(f) for f in files
               if "git checkout -q -B _sync origin/main" in
               io.open(f, encoding="utf-8").read()]
    ck("★ 沒有任何 workflow 還把同步邏輯 inline 抄一份（⛔ 一律呼叫 `sync_code.sh`）",
       not _inline, f"⛔ 還 inline 的：{_inline}")

    # ══════════════════════════════════════════════════════════════
    # ⭐ 相依套件要裝在**用它之前**。⛔ 判準是**順序**，不是「有沒有那一步」
    #   （跟上面「取 main 排在回補之前」同一個形狀）。
    # ⚠ 2026-09-13 回測線在我的分支上讀出來的：`forward.yml` 少了
    #   `pip install pandas numpy` ⇒ 會在「跑前瞻紀錄」那步 ImportError，
    #   ⛔ 而失敗的樣子是「那個月沒跑」——正是前瞻紀錄最怕的形狀。
    # ══════════════════════════════════════════════════════════════
    for f in files:
        src = io.open(f, encoding="utf-8").read()
        use = src.find("backtest.forward_and")
        if use < 0:
            continue
        inst = src.find("pip install")
        ck(f"{os.path.basename(f)}｜`pip install` 排在跑 `forward_and` **之前**",
           0 <= inst < use,
           f"⛔ 位置 pip={inst} / forward_and={use}"
           "　⇒ 會 ImportError，而失敗的樣子是「那個月沒跑」")
        # ⛔ 比的是**那一行 `pip install` 本身**，⚠ 不是「這兩個字在不在檔案裡」
        #   ——第一版我寫 `"numpy" in src`，而 `numpy` 在我自己的註解裡也有一份
        #   ⇒ 把 numpy 從安裝行拿掉的突變 **全綠**（2026-09-13 當場踩到）。
        _pipln = [ln for ln in src.split("\n")
                  if "pip install" in ln and not ln.lstrip().startswith("#")]
        ck(f"{os.path.basename(f)}｜`pip install` 那一行**真的**同時裝 pandas 與 numpy"
           "（⛔ `forward_and` 兩個都 import）",
           bool(_pipln) and all("pandas" in ln and "numpy" in ln for ln in _pipln),
           f"⛔ 安裝行：{_pipln}")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ `push_data.sh` 的 `PUSH_TREES`：⛔ 預設值壞掉 ＝ **八支全部推空**
    #
    # 2026-09-13 為了 `forward.yml`（輸出在 `backtest/forward/`，不在 `data/`）
    # 把三個寫死的 `data` 換成 `$TREES`。⚠ 而如果預設值打錯，
    # 八支 workflow 會**照樣綠、照樣說「沒有變動，不 commit」**——
    # ⛔ 那正是 CLAUDE.md 四點二那一族：中間那一步成功了，就被當成整件事成功了。
    # ⇒ 這一節**真的把那一行交給 bash 跑**，⛔ 不是比字串。
    # ══════════════════════════════════════════════════════════════
    _pd = io.open("push_data.sh", encoding="utf-8").read()
    _defline = [ln for ln in _pd.split("\n") if ln.startswith("TREES=")]
    ck("★ `push_data.sh` 有且只有一行定義 `TREES`", len(_defline) == 1, _defline)
    if _defline:
        _r = subprocess.run(["bash", "-c", _defline[0] + "; echo $TREES"],
                            capture_output=True, text=True)
        ck("★ 不帶 `PUSH_TREES` 時，bash 真的算出 `data`"
           "（⛔ 八支 workflow 全靠這個預設值）",
           _r.stdout.strip() == "data", f"⛔ 算出 {_r.stdout.strip()!r}")
        _r2 = subprocess.run(
            ["bash", "-c", "PUSH_TREES=backtest/forward; " + _defline[0]
             + "; echo $TREES"], capture_output=True, text=True)
        ck("★ 帶了 `PUSH_TREES` 時真的換過去", _r2.stdout.strip() == "backtest/forward",
           f"⛔ 算出 {_r2.stdout.strip()!r}")
    _hard = [ln for ln in _pd.split("\n")
             if ("git add -A data" in ln or 'git diff --name-only "$BASE" "$DC" -- data' in ln)
             and not ln.lstrip().startswith("#")]
    ck("★ 沒有任何一處還寫死 `data`（⛔ 漏改一處 ⇒ 那一處永遠只搬 data）",
       not _hard, f"⛔ 還寫死的：{_hard}")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 前瞻紀錄那三道**要一起成立**（回測線 2026-09-15 0141 §一）
    #
    # `p4_types/universe.csv` 的 `first_seen` 取小／`last_seen` 取大，
    # 是 `forward_p4` 讀既有檔時算的 ⇒ ⛔ 它算得對的**前提**有三個：
    #
    #   ① `forward.yml` 有「只准在 main 上跑」            ⇒ 讀到的是最新那份
    #   ② `sync_code.sh` 的 EXCLUDE_TREES 有 backtest/forward ⇒ 分支不會反向蓋回去
    #   ③ `push_data.sh` 的 LEDGERS 有那兩個檔            ⇒ 推回去時逐鍵合併不掉列
    #
    # ⛔ 缺**任何一道**，取小取大就會錯，⚠ 而錯的樣子是「某個月不見了」
    #   ——⭐ 而前瞻紀錄**補不回來**（重算出來的就不是前瞻了）。
    # ⇒ 三道釘成**一條**斷言：拿掉任何一道都紅，⛔ 不是分成三條讓人以為可以少一道。
    # ══════════════════════════════════════════════════════════════
    _sc = io.open(os.path.join(here, "sync_code.sh"), encoding="utf-8").read()
    _fw = io.open(os.path.join(here, ".github", "workflows",
                               "forward.yml"), encoding="utf-8").read()
    _three = {
        "① forward.yml 只准在 main 上跑": '"$BR" != "main"' in _fw,
        "② sync_code.sh 排除 backtest/forward":
            re.search(r"EXCLUDE_TREES=\"[^\"]*backtest/forward", _sc) is not None,
        "③ push_data.sh 的 LEDGERS 有 p4_types 那兩個檔":
            "backtest/forward/p4_types/records.csv:" in _pd
            and "backtest/forward/p4_types/universe.csv:" in _pd,
    }
    _bad3 = [k for k, v in _three.items() if not v]
    ck("⭐⭐ 前瞻紀錄那三道**全部**還在（⛔ 缺一道，`first_seen`／`last_seen` 就會錯）",
       not _bad3,
       f"⛔ 沒了：{_bad3}"
       "　⇒ 錯的樣子是「某個月不見了」，⚠ 而前瞻紀錄**補不回來**"
       if _bad3 else "三道都在")

    # ⭐⭐ 而第四道：**排程本身**。⛔ 上面那三道都在、而 cron 被拿掉的話，
    #   那一支從此再也不會跑，⚠ 而畫面上什麼都不會說（沒有失敗、沒有紅）
    #   ——正是「不累積就永久失去」那一族最怕的形狀。
    # ⇒ 判準**兩個方向都比**（三點1）：
    #   ① 每一條 cron 都有人認得（⛔ 否則那一趟會 `exit 1`，白跑）
    #   ② 每一個 case 分支都對得上一條 cron（⛔ 否則是 cron 被拿掉了，而分支留著）
    _crons = set(re.findall(r'-\s*cron:\s*"([^"]+)"', _fw))
    _arms = set(re.findall(r'^\s*"([0-9*/, -]+)"\)\s*RUN_', _fw, re.M))
    ck("⭐⭐ forward.yml：每一條 cron 都有對應的分支"
       "（⛔ 少一條 ⇒ 那一趟 exit 1 白跑）",
       _crons <= _arms, f"⛔ 沒人認得：{sorted(_crons - _arms)}｜cron={sorted(_crons)}")
    ck("⭐⭐ 而反過來：每一個分支都對得上一條 cron"
       "（⛔ 對不上 ＝ **cron 被拿掉了**，而那一支從此不會跑、沒有任何地方會說）",
       _arms <= _crons, f"⛔ 沒有 cron 的分支：{sorted(_arms - _crons)}")
    ck("★ 這兩道真的**掃到了**（⛔ 0 條 cron 跟全部通過長得一樣）",
       len(_crons) >= 2, f"{len(_crons)} 條 cron｜{len(_arms)} 個分支")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 自測步驟紅了，**有沒有任何地方會說**（2026-09-15 加）
    #
    # ⛔ 已經發生過：`probe.yml` 的「驗十四支探針跑得完」寫成
    #   `run: python selftest_probes.py`，而註解說「不加 continue-on-error
    #   ⇒ 連跑都跑不完就不必往下打」。⚠ **那句話是假的**：後面兩步都是
    #   `if: always()` ⇒ 它紅了，整趟照樣跑完、照樣 commit，
    #   ⛔ 而 `_last_run.md` 裡沒有任何一塊提到它。
    #
    # ⇒ 判準：**一支 workflow 只要有任何 `if: always()` 的步驟，
    #   它裡面的自測步驟就一定要走 `ci_step.py`**（記下 rc ⇒ 進 runlog ⇒ 進 commit）。
    # ⚠ 例外是「零相依」那幾道：它們排在 `if: always()` 步驟**之前**而且
    #   本來就該擋住同步，⛔ 而那個「擋得住」現在也只是說法——
    #   ⇒ 所以判準只放行**檔名帶 `selftest_` 而且在同一支裡沒有 always 步驟**的。
    # ══════════════════════════════════════════════════════════════
    for f in files:
        short = os.path.basename(f)
        txt = io.open(f, encoding="utf-8").read()
        if "if: always()" not in txt:
            continue
        naked = re.findall(r"^\s*run:\s*python3?\s+(selftest_[A-Za-z0-9_]+\.py)\s*$",
                           txt, re.M)
        # ⭐ 零相依那幾道（排在同步之前、要擋住同步的）不算：它們是**擋門**的，
        #   ⛔ 走 ci_step 會把它們變成「記一筆就放行」。
        gate = set(re.findall(r"零相依[^\n]*\n\s*run:\s*python3?\s+"
                              r"(selftest_[A-Za-z0-9_]+\.py)", txt))
        gate |= set(re.findall(r"run:\s*python3?\s+(selftest_[A-Za-z0-9_]+\.py)"
                               r"[\s\S]{0,200}?零相依", txt))
        bare = [n for n in naked if n not in gate]
        ck(f"⭐⭐ {short}：自測步驟紅了會被說出來"
           "（⛔ `if: always()` 在後面 ⇒ 不走 `ci_step.py` 的紅**沒有任何地方會說**）",
           not bare, f"⛔ 這幾支是裸跑的：{sorted(set(bare))}")
        # ⛔ 比的是**真的有一行 `run:` 在跑它**，⚠ 不是「這三個字出現在檔案裡」
        #   ——`probe.yml` 的註解裡本來就寫著 `ci_report.py`
        #   ⇒ 比字串的話這一條永遠綠（突變 R3 當場證明）。
        runs_step = re.search(r"^\s*run:\s*python3?\s+ci_step\.py\b", txt, re.M)
        runs_report = re.search(r"^\s*run:\s*python3?\s+ci_report\.py\b", txt, re.M)
        if runs_step:
            ck(f"  {short}：有 `ci_step.py` 就一定要有 `ci_report.py`"
               "（⛔ 只記不說 ＝ 沒說）", bool(runs_report),
               "⛔ 記了 rc 卻沒有人把它寫成 runlog 區塊")

    # ══════════════════════════════════════════════════════════════
    # ⛔⛔ 單行 `run:` **不可以有續行**（2026-09-15 付過代價）
    #
    # ```yaml
    # run: python ci_step.py selftest_mops_history.py
    #   python selftest_revenue_complete.py        ← ⛔ 這是**續行**
    # ```
    # ⇒ YAML 把它折成**一個純量**：
    #   `python ci_step.py selftest_mops_history.py python selftest_revenue_complete.py`
    # ⇒ ⭐ 第二支**從來沒有被跑過**，⚠ 而它的檔名出現在 workflow 裡
    #   ⇒ 「每一支自測都有人跑」那道守門一直是綠的。
    #
    # ⇒ ⭐ 這是四點二的又一個：**「檔名在 workflow 裡」≠「它會被執行」。**
    # ⚠ 要兩個方向都有人守：這一道擋 YAML 折行，`ci_step.py` 自己擋多餘參數。
    # ══════════════════════════════════════════════════════════════
    for f in files:
        short = os.path.basename(f)
        lines = io.open(f, encoding="utf-8").read().splitlines()
        folded = []
        for i, ln in enumerate(lines):
            m = re.match(r"^(\s*)run:\s*(?!\||>)(\S.*)$", ln)
            if not m:
                continue
            ind = len(m.group(1))
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if nxt.strip() and not nxt.lstrip().startswith("#") \
                    and len(nxt) - len(nxt.lstrip()) > ind:
                folded.append(f"第 {i + 1} 行：{m.group(2)[:50]} ← {nxt.strip()[:40]}")
        ck(f"⛔⛔ {short}：單行 `run:` 沒有續行"
           "（⚠ 有續行 ⇒ YAML 折成一串 ⇒ 後面那支**根本沒被跑**，而守門照樣綠）",
           not folded, "；".join(folded))

    # ⛔⛔ 每一支都要 `fetch-depth: 0`（2026-09-15 加）
    #   shallow clone（預設 depth 1）⇒ `push_data.sh` 的 rebase 與
    #   `sync_code.sh` 的比較都拿不到歷史，⚠ 而失敗的方式包含「看起來正常」。
    #   ⭐ 而它最安靜的後果是：在 shallow clone 裡量「倉庫多大／歷史佔多少」
    #     **一律是錯的**——2026-09-15 我照那個數字連錯三次，三次都作廢。
    for f in files:
        short = os.path.basename(f)
        txt = io.open(f, encoding="utf-8").read()
        m = re.search(r"uses:\s*actions/checkout@[^\n]*\n(?:[^\n]*\n){0,12}?"
                      r"\s*fetch-depth:\s*0", txt)
        ck(f"⛔ {short}：checkout 有 `fetch-depth: 0`"
           "（⚠ shallow clone ⇒ rebase／比較拿不到歷史，而失敗方式包含「看起來正常」）",
           bool(m), "⛔ 沒有 ⇒ 預設 depth 1")

    check_rc_debt(files)

    print(f"\n[selftest] 檢查了 {len(files)} 支 workflow、{n_run} 個 run 區塊"
          f"｜通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
