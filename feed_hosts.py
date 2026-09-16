#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`feed_hosts.py` — **我方哪一支程式打哪一個主機**，逐支列出來。

## ⛔ 為什麼要有這一支（2026-09-16）

TWSE／TPEx 的「網站使用條款」第七條禁重製，⭐ 而它自己帶一個但書：

> 「…但臺灣證券交易所已授權**「政府資料開放平臺」**提供公眾使用之本網站資料，
> **不在此限**。」（櫃買那份一字不差，而且把 `data.gov.tw` 的網址寫出來了）

⇒ 市場情報分析線要裁「我方這樣用可不可以」時，需要知道**我方的來源怎麼分族**。

## ⛔⛔ 而這一支存在的真正理由是：**`grep` 的主機計數會給出錯的數字**

我 2026-09-16 早上送過一個沒分類的 `grep` 數字（「27 支程式讀 `kind`」，
⭐ 真正是 **13 支**，而其餘 15 支的 `kind` 是別的東西）⇒ 對方拿它去估改動半徑。
⇒ 同一天晚上要送主機計數時，`grep -o 'https?://…'` 給的是：

    www.tpex.org.tw 113｜www.twse.com.tw 58｜mopsov 14｜openapi.twse 12 …

⛔ 而那是**字面出現次數**，裡面混著：探針、假回應、註解與 docstring、
已經停用的路、以及同一個網址被寫在三個地方。

⇒ ⭐ 所以這一支的判準是**三層**，⛔ 一層都不可以少：

    ① 母體只收「**真的被 workflow 跑到**」的 .py（`selftest_workflows.run_blocks`）
    ② 主機只從 **AST 的字串常數**取，⛔ 而且**扣掉 docstring**
       （`selftest_workflows._nondoc_strings`——⚠ 我們的說明文字本來就會抄網址）
    ③ 分族的判準是**主機名**，⛔ 不是我對那個端點的印象

## ⚠ 而它答不出來的那一格要先標好

⛔ **這一支不判「合不合條款」**——那是市場情報分析線的裁定。
⛔ 它也不判「(A) 那一族是不是就等於但書講的那批資料」：
⚠ 主機叫 `openapi.twse.com.tw` **不等於**「它已授權政府資料開放平臺」
——⭐ 那要去 `data.gov.tw` 對，而**我沒有對過**。
⇒ 所以 (A) 的欄名是 `開放資料型主機`，⛔ 不是「但書涵蓋的」。
"""
import ast
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backfill as B                                             # noqa: E402
import selftest_workflows as W                                  # noqa: E402

WF_DIR = os.path.join(HERE, ".github", "workflows")
# ⛔ 路徑寫成呼叫當下才算的函式（第七點第五個那個坑：`mops.CHANGES`
#   在 import 當下就算好 ⇒ 沙箱只導一個旋鈕，log 照樣寫進 repo）。


def out_path():
    return os.path.join(HERE, "data", "meta", "_feed_hosts.txt")

# ⭐ 分族只看**主機名**。⛔ 不看路徑、不看我對那個端點的印象。
#   ⚠ 而 `data.gov.tw` 放在 (A) 是因為它**就是**那個平臺本身。
OPEN_HOSTS = ("openapi.twse.com.tw", "openapi.tdcc.com.tw",
              "opendata.tdcc.com.tw", "data.gov.tw")
# ⚠ `www.tpex.org.tw` **兩族都有**（它底下有 `/openapi/` 也有一般報表頁）
#   ⇒ ⛔ 不可以用主機名判它 ⇒ 另外標成「要逐條看路徑」。
MIXED_HOSTS = ("www.tpex.org.tw",)


def invoked_modules():
    """→ {模組檔名: {workflow 檔名}}：**真的被 workflow 的 `run:` 跑到**的 .py。

    ⛔ 不是「repo 裡所有的 .py」——那會把探針與一次性腳本算進來。
    """
    out = {}
    for fn in sorted(os.listdir(WF_DIR)):
        if not fn.endswith(".yml"):
            continue
        for _name, sh in W.run_blocks(os.path.join(WF_DIR, fn)):
            for m in re.finditer(r"python3?\s+(?:-m\s+)?([A-Za-z0-9_./]+\.py)", sh):
                mod = m.group(1).split("/")[-1]
                if os.path.exists(os.path.join(HERE, m.group(1))):
                    out.setdefault(m.group(1), set()).add(fn)
                elif os.path.exists(os.path.join(HERE, mod)):
                    out.setdefault(mod, set()).add(fn)
    return out


def hosts_of(path):
    """→ {主機名}：這支程式的**非 docstring 字串常數**裡出現的主機。

    ⛔ 不掃註解（註解不是字串常數 ⇒ AST 看不到，⭐ 那正是要的）。
    """
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return set()
    out = set()
    for s in W._nondoc_strings(tree):
        for m in re.finditer(r"https?://([A-Za-z0-9._-]+)", s):
            h = m.group(1).lower()
            if "." in h and not h.endswith(".invalid"):
                out.add(h)
    return out


def writes_of(path):
    """→ {`data/` 底下的第一層目錄}：這支程式的字串常數裡提到的資料目錄。

    ⚠ 這一欄是**線索**，⛔ 不是「唯一寫入者」的證明（第五點那件事要人來判）。
    """
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return set()
    out = set()
    for s in W._nondoc_strings(tree):
        for m in re.finditer(r"data/([A-Za-z0-9_]+)", s):
            out.add(m.group(1))
    return out


def classify(hosts):
    """→ (開放資料型, 網站型, 要逐條看的)。⛔ 三種分開，不合併成兩種。"""
    a = {h for h in hosts if h in OPEN_HOSTS}
    mix = {h for h in hosts if h in MIXED_HOSTS}
    b = hosts - a - mix
    return a, b, mix


def main():
    mods = invoked_modules()
    say = []

    def P(t=""):
        say.append(t)
        print(t)

    P("=" * 78)
    P("我方哪一支程式打哪一個主機（母體＝真的被 workflow 跑到的 .py）")
    P("⛔ 這一支不判合不合條款，也不判『開放資料型主機』是不是但書涵蓋的那批")
    P("=" * 78)
    rows = []
    for mod in sorted(mods):
        hs = hosts_of(os.path.join(HERE, mod))
        if not hs:
            continue
        a, b, mix = classify(hs)
        rows.append((mod, sorted(mods[mod]), a, b, mix, sorted(writes_of(
            os.path.join(HERE, mod)))))
    P(f"\n母體：{len(mods)} 支被 workflow 跑到，其中 **{len(rows)} 支**會連外\n")
    for mod, wfs, a, b, mix, wr in rows:
        tag = []
        if a:
            tag.append("A 開放資料型:" + "／".join(sorted(a)))
        if b:
            tag.append("B 網站型:" + "／".join(sorted(b)))
        if mix:
            tag.append("⚠ 要逐條看路徑:" + "／".join(sorted(mix)))
        P(f"  {mod}")
        P(f"      workflow：{'／'.join(wfs)}")
        for t in tag:
            P(f"      {t}")
        if wr:
            P(f"      寫（線索）：{'／'.join(wr)}")
    na = sum(1 for r in rows if r[2])
    nb = sum(1 for r in rows if r[3])
    nm = sum(1 for r in rows if r[4])
    P(f"\n⇒ 會連外的 {len(rows)} 支裡：")
    P(f"     打到 **A 開放資料型**主機的：{na} 支")
    P(f"     打到 **B 網站型**主機的：　　{nb} 支")
    P(f"     打到 `www.tpex.org.tw`（⚠ 兩族都有，要逐條看路徑）：{nm} 支")
    P("  ⛔ 三個數字會相加超過總數——**一支可以同時打兩族**，那不是錯。")
    # ⭐ 可見性由**資料**承擔，⛔ 不是由 log（四點二⑤：log 會捲掉）。
    os.makedirs(os.path.dirname(out_path()), exist_ok=True)
    io.open(out_path(), "w", encoding="utf-8").write(
        B.probe_stamp() + "\n".join(say) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
