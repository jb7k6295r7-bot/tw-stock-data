#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""標成「零相依」的那幾步，**在缺少選用套件時真的跑得完嗎**。

## ⛔⛔ 這一支存在的理由：2026-09-15 probe run 115

我在 `selftest_tdcc.py` 加了一節，而它會走到 `write_hist` ⇒ `import pyarrow`。
⚠ 而 **probe runner 沒裝 pyarrow**（只有 daily／feeds 那兩支會裝）：

```
step 9  驗集保週檔的閘門（selftest_tdcc.py）  ⛔ failure
step 10 / 11                                  skipped
⛔ step 12 **把程式同步到 main**               skipped ⇒ 那一趟什麼都沒搬過去
```

⇒ ⭐ 六點五那條一字不差：
**一條在某個環境下【必然】不成立的斷言，等於把那個環境的整條線關掉。**

## ⛔ 而既有的守門**抓不到它**，三道都抓不到

```
`selftest_workflows`   驗 shell 語法、驗檔案存在 ⇒ ⛔ 不跑那支自測
`selftest_no_dup`      比函式本體 ⇒ ⛔ 跟相依性無關
AST 掃「有沒有 import pandas」⇒ ⛔ 抓不到：那個 import 在**別的模組的函式裡**
                                （`tdcc.write_hist`），而且是**間接**被呼叫到的
```

⇒ ⭐ 唯一抓得到的方式是**真的在那個環境跑一次**（四點二：斷言要驗終點）。
⇒ 做法：`PYTHONPATH` 指到一個放滿「一 import 就 `raise ImportError`」的假模組的目錄，
然後把每一支「零相依」自測**真的跑一遍**，斷言 `rc == 0`。

⚠ 而「跑得完」**不等於**「驗過了」：那幾支會印「⚠⚠ 這一層沒跑」——
⭐ 那正是要的行為（六點五：不算失敗，⛔ 也不算驗過）。
"""
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(HERE, ".github", "workflows")

# ⚠ 這幾個是 runner 上**不一定有**的。⛔ 清單要跟 workflow 裡「pip install」
#   那幾步對得上——多擋一個不痛（那只是更嚴），⛔ 少擋一個就是這次的洞。
OPTIONAL = ("pandas", "numpy", "pyarrow", "py7zr", "openpyxl",
            "yaml", "certifi", "requests", "bs4", "lxml")

OK = FAIL = 0


def ck(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}" + (f"　（{detail}）" if detail else ""))
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{detail}" if detail else ""))


def zero_dep_selftests():
    """→ {自測檔名}：被標成「零相依」的步驟裡跑到的那幾支。

    ⭐ 判準是 **workflow 裡的 `name:` 有沒有「零相依」**，⛔ 不是我另開一張清單
    ——⚠ 另開清單就是「兩份實作」，而它會跟 workflow 走岔（四點五）。
    """
    got = set()
    for fn in sorted(os.listdir(WF)):
        if not fn.endswith(".yml"):
            continue
        txt = io.open(os.path.join(WF, fn), encoding="utf-8").read()
        # 逐個 step 切開：`      - name:` 起頭
        for blk in re.split(r"\n      - name:", txt)[1:]:
            head = blk.split("\n", 1)[0]
            if "零相依" not in head:
                continue
            got |= set(re.findall(r"(selftest_[A-Za-z0-9_]+\.py)", blk))
    return got


def main():
    names = sorted(zero_dep_selftests() - {os.path.basename(__file__)})
    print(f"── 「零相依」步驟裡跑到的自測：{len(names)} 支 ──")
    # ⭐ 母體大小自己是一道斷言（第七點⑨：母體被判準悄悄縮小過一次）
    ck("⭐ 掃得到的母體 ≥ 6 支（⛔ 0 支與「全部合規」在紙上一模一樣）",
       len(names) >= 6, f"{len(names)} 支：{names}")
    if not names:
        print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
        return 1

    d = tempfile.mkdtemp(prefix="nodep_")
    for m in OPTIONAL:
        with io.open(os.path.join(d, m + ".py"), "w", encoding="utf-8") as f:
            f.write(f'raise ImportError("selftest_zero_dep：故意擋掉 {m}")\n')
    env = dict(os.environ)
    # ⛔ 假模組要排在**最前面**，否則真的那份會先被找到 ⇒ 這一整支等於沒測
    env["PYTHONPATH"] = d + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    for n in names:
        p = os.path.join(HERE, n)
        if not os.path.isfile(p):
            ck(f"{n} 存在", False, "⛔ workflow 叫得到但檔不在")
            continue
        r = subprocess.run([sys.executable, p], cwd=HERE, env=env,
                           capture_output=True, text=True, timeout=300)
        tail = (r.stdout or "")[-200:].replace("\n", " ")
        ck(f"⭐ {n} 在**沒有選用套件**時跑得完（rc=0）",
           r.returncode == 0,
           f"rc={r.returncode}｜{(r.stderr or tail)[-220:]}")

    # ⭐ 反向：這一道**真的擋得住**（⛔ 否則它跟沒有一樣）
    #   拿一支一 import pandas 就炸的假自測餵進去，它必須判紅。
    probe = os.path.join(d, "selftest_fake_hard_dep.py")
    io.open(probe, "w", encoding="utf-8").write("import pandas\n")
    r = subprocess.run([sys.executable, probe], cwd=HERE, env=env,
                       capture_output=True, text=True, timeout=60)
    ck("⭐⭐ 反向：一支**硬相依** pandas 的程式在這個環境下確實 rc≠0"
       "（⛔ 否則上面那幾條在假模組沒生效時也會全綠）",
       r.returncode != 0, f"rc={r.returncode}")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
