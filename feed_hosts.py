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


# ⭐⭐ 2026-09-16 晚補：只看**主機**時，`www.tpex.org.tw` 有 18 支卡在
#   「要逐條看路徑」那一格 ⇒ ⛔ 那等於沒分類完。
#   ⇒ 實測我方在那個主機下用到的前綴只有四種：
#         /www/zh-tw **32**｜/openapi/v1 **19**｜/web/emergingstock 1｜/ 1
#   ⇒ ⭐ 分類升到**端點層**（主機 ＋ 前兩層路徑），那 18 支就拆開了。
# ⚠ 而「只有主機、沒有路徑」的（例如探針拿首頁當種子）仍然進
#   「要逐條看」那一格——⛔ 不可以猜它是哪一族。
OPEN_PATHS = ("/openapi/",)
# ⛔⛔ 2026-09-16 晚再補一層：第一版把 `api.finmindtrade.com`／`github.com`
#   也算進 B（網站型）⇒ ⛔ 而那份條款是 **TWSE／TPEx 自己的網站使用條款**
#   ⇒ 把第三方主機算進去會把暴露面**話大**，
#   而那又是一個「給別人拿去裁的數字」（第七點）。
# ⇒ ⭐ 先問「這個主機在不在**這份條款的管轄**裡」，再談 A／B。
# ⚠ 而 `mops.twse.com.tw`／`mopsov.twse.com.tw`／`isin.twse.com.tw` 這些
#   都是 `twse.com.tw` 底下 ⇒ 算在管轄裡；⛔ 而「管不管得到子網域」
#   本身也是**法律解讀**，這一支只按網域標，⛔ 不裁。
TERMS_DOMAINS = ("twse.com.tw", "tpex.org.tw", "gretai.org.tw")


def in_terms_scope(host):
    """這個主機在不在「交易所網站使用條款」的網域底下 → bool。

    ⛔ 這只是**網域比對**，不是「條款管不管得到它」的答案。
    """
    return any(host == d or host.endswith("." + d) for d in TERMS_DOMAINS)


def endpoints_of(path):
    """→ {`主機+前兩層路徑`}：比 `hosts_of` 細一層的那一版。

    ⛔ 同樣只從**非 docstring 的字串常量**取（判準②不變）。
    """
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return set()
    out = set()
    for s in W._nondoc_strings(tree):
        for m in re.finditer(r"https?://([A-Za-z0-9._-]+)(/[A-Za-z0-9_./{}-]*)?", s):
            h = m.group(1).lower()
            if "." not in h or h.endswith(".invalid"):
                continue
            seg = "/".join((m.group(2) or "").split("/")[:3])
            out.add(h + seg)
    return out


def classify_ep(eps):
    """端點層的分類 → (A 開放資料型, B 網站型, ❗ 讀不出來的)。

    ⭐ 判準順序是死的：**先看主機、再看路徑**。
    ⛔ 而「連路徑都沒有」的不猜，進第三格。
    """
    a, b, unk = set(), set(), set()
    for e in eps:
        host = e.split("/")[0]
        rest = e[len(host):]
        if host in OPEN_HOSTS:
            a.add(e)
        elif host in MIXED_HOSTS:
            if any(rest.startswith(x) for x in OPEN_PATHS):
                a.add(e)
            elif rest and rest != "/":
                b.add(e)
            else:
                unk.add(e)              # ⛔ 只有主機 ⇒ 不猜
        else:
            b.add(e)
    return a, b, unk


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

    # ⭐⭐ 端點層（主機 ＋ 前兩層路徑）——⛔ 主機層把 `www.tpex.org.tw` 那 18 支
    #   全丟進「要逐條看」，那等於沒分類完。
    P("")
    P("── ⭐⭐ 端點層（主機 ＋ 前兩層路徑）：`www.tpex.org.tw` 那一格拆開之後 ──")
    P(f"   ⚠ 母體**只收在條款網域底下**的（{'／'.join(TERMS_DOMAINS)}）"
      "——⛔ FinMind／GitHub 那些不在這份條款的管轄裡，算進去會把暴露面話大")
    ea = eb = eu = 0
    unk_list = []
    for mod in sorted(mods):
        eps = endpoints_of(os.path.join(HERE, mod))
        if not eps:
            continue
        eps = {e for e in eps if in_terms_scope(e.split("/")[0])}
        if not eps:
            continue
        a2, b2, u2 = classify_ep(eps)
        ea += bool(a2)
        eb += bool(b2)
        if u2:
            eu += 1
            unk_list.append((mod, sorted(u2)))
    P(f"     A 開放資料型端點：**{ea}** 支｜B 網站型端點：**{eb}** 支"
      f"｜❗ 讀不出來的：**{eu}** 支")
    for mod, u2 in unk_list:
        P(f"     ❗ {mod}：{'／'.join(u2)}"
          "（⛔ 只有主機、沒有路徑 ⇒ **不猜**）")
    # ⭐ 可見性由**資料**承擔，⛔ 不是由 log（四點二⑤：log 會捲掉）。
    os.makedirs(os.path.dirname(out_path()), exist_ok=True)
    io.open(out_path(), "w", encoding="utf-8").write(
        B.probe_stamp() + "\n".join(say) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
