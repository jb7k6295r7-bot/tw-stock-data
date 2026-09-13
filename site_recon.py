#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site_recon.py — 第 −1 步：**先拿整站清單**，再用我要的東西的名字去搜。
**只讀、只印，⛔ 不寫任何 `data/` 以外的資料檔。**

## ⛔ 為什麼要有這一支

使用者 2026-09-10 定：**「每次網站都是全掃描資料，看有沒有用，真的找不到再換網站！」**
⇒ `docs/NEW_ENDPOINT.md` 第 −1 步。⚠ 而我到今天為止**每一次**都是反過來做的：
心裡先有一條路徑（`TWT49U`、`TWTAUU`…），打不通就說「官方沒有」。

```
2026-09-13 的帳：
  我寫「上市沒有官方換股比率欄位」  ⇒ ⛔ repo 裡 grep TWTAVU **0 次**
  我寫「TWT49U 只有合併的權值+息值」⇒ ⛔ 那是**我方取了什麼**，不是官方有什麼
```
⇒ ⭐ 兩次的形狀一模一樣：**把「我掃過的範圍」寫成了「官方的全部」**（三點①）。

## ⇒ 這一支做的事，就是把那個範圍**變成一份可以貼出來的清單**

```
① 抓**機器可讀的整站目錄**（OpenAPI／sitemap／選單），⛔ 不是逐條猜路徑
② 用一份**寫下來的關鍵詞表**去搜（三點②：「查過了、沒有」要寫用什麼詞查）
③ 命中的頁再抓一次，把它自己送出的 **`rwd/zh/...` 端點**撈出來
④ ⭐ 最後印**掃描範圍表**：哪幾份目錄拿到了、各幾筆、哪幾份**失敗**
```

## ⛔⛔ 最重要的一條：**目錄拿不到 ≠ 官方沒有**

⚠ 這一支若有任何一份目錄抓失敗，它的結論就只涵蓋拿到的那幾份。
⇒ 輸出最後那張表會把失敗的那幾份**單獨列出來**，
⛔ 而只要那張表上有失敗項，就**不可以**從這份輸出寫出任何「官方沒有」的句子。

⚠ 而這一支在**開發容器裡一定全紅**（我方閘道對交易所一律 403，第六點）
⇒ ⛔ 它的失敗在本機**不是事實**，一定要在 Actions 上跑。
"""
import json
import os
import re
import sys
import traceback

import backfill as B
import ca_chain  # noqa: F401
# ⭐ 同一件事只准有一份實作（四點五）：錯誤訊息**中間**省略那條規矩
#   ⛔ 不要再抄一份 try/except 包裝——抄的那一份不會跟著改。
from feeds import _why                                        # noqa: E402

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_site_recon.txt")

# ⭐ 【掃描範圍】機器可讀的整站目錄。⛔ 這一份就是日後「我掃了哪裡」的出處。
CATALOGS = [
    ("TWSE OpenAPI 目錄", "https://openapi.twse.com.tw/v1/swagger.json", "openapi"),
    ("TPEx OpenAPI 目錄", "https://www.tpex.org.tw/openapi/swagger.json", "openapi"),
    ("TWSE sitemap", "https://www.twse.com.tw/sitemap.xml", "text"),
    ("TWSE 中文首頁（選單）", "https://www.twse.com.tw/zh/index.html", "text"),
    ("TPEx 中文首頁（選單）", "https://www.tpex.org.tw/zh-tw/index.html", "text"),
    ("MOPS 公開資訊觀測站首頁", "https://mopsov.twse.com.tw/mops/web/index", "text"),
]

# ⭐ 【查詢用詞】⛔ 這一份要寫下來——「查過了、沒有」沒有附詞表就不算查過（三點②）
WORDS = [
    "減資", "換股", "增資", "認購", "除權", "除息", "權值", "息值",
    "股利", "配股", "配息", "恢復買賣", "停止買賣", "面額", "合併",
    "漲停", "跌停", "參考價", "基準日",
]

# ⚠ 命中的頁要再抓一次，把它**自己送出的**端點撈出來（第 −1 步④的可做版本）
EP_RE = re.compile(r"(?:rwd/zh|/v1|openapi)/[A-Za-z0-9_\-/]{2,60}")
MAX_PAGES = 25

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def fetch(url):
    """→ (文字, 錯誤字串)。⛔ 失敗一律把**完整**原因帶回來。"""
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        return None, _why(err)
    return raw.decode("utf-8", "replace"), None


def entries_openapi(txt):
    """→ [(路徑, 說明)]，從 OpenAPI/Swagger 文件。"""
    try:
        d = json.loads(txt)
    except ValueError as ex:
        return None, f"不是 JSON：{ex}"
    paths = d.get("paths")
    if not isinstance(paths, dict):
        return None, f"沒有 `paths` 鍵（有的鍵：{sorted(d)[:12]}）"
    out = []
    for p, v in paths.items():
        desc = ""
        if isinstance(v, dict):
            for _m, op in v.items():
                if isinstance(op, dict):
                    desc = op.get("summary") or op.get("description") or desc
                    if desc:
                        break
        out.append((p, str(desc)))
    return out, None


def entries_text(txt, base):
    """→ [(連結, 該連結前後的文字)]，從 HTML／sitemap 撈連結與標題。

    ⚠ 這是**粗的**：撈 `href` 與 `<loc>`，並把同一行的中文帶出來當說明。
    ⛔ 而「粗」比「猜路徑」好——它的範圍是可以數的。
    """
    out = []
    for m in re.finditer(r"<loc>\s*([^<\s]+)\s*</loc>", txt):
        out.append((m.group(1), ""))
    for m in re.finditer(r'href="([^"#?]{2,200})"[^>]*>([^<]{0,80})', txt):
        href, label = m.group(1), m.group(2).strip()
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = base.split("/zh")[0].rstrip("/") + href
        out.append((href, label))
    seen, uniq = set(), []
    for h, la in out:
        if h in seen:
            continue
        seen.add(h)
        uniq.append((h, la))
    return uniq, None


def hits(entries):
    """→ {詞: [(路徑, 說明)]}，⛔ 詞表是寫死的，不是臨場想的。"""
    got = {}
    for w in WORDS:
        for p, desc in entries:
            if w in p or w in desc:
                got.setdefault(w, []).append((p, desc))
    return got


def main():
    say("=" * 74)
    say("site_recon — 第 −1 步：先拿整站清單，再用名字搜（⛔ 不逐條猜路徑）")
    say("=" * 74)
    say("⛔ 起因：我兩次把「我掃過的範圍」寫成「官方的全部」（CLAUDE.md 三點①）")
    say(f"⭐ 【查詢用詞】共 {len(WORDS)} 個：{'、'.join(WORDS)}")

    scope = []          # (目錄名, 拿到幾筆, 失敗原因或 "")
    allhit = {}

    for name, url, kind in CATALOGS:
        say(f"\n{'=' * 74}\n【{name}】\n{url}")
        txt, err = fetch(url)
        if err:
            say(f"  ✗ 抓不到：{err}")
            say("  ⛔ ⇒ 這一份**沒有掃到**，它涵蓋的東西一律不可以寫成「官方沒有」")
            scope.append((name, 0, err))
            continue
        ents, perr = (entries_openapi(txt) if kind == "openapi"
                      else entries_text(txt, url))
        if ents is None:
            say(f"  ✗ 解析不出清單：{perr}｜開頭 {txt[:160]!r}")
            scope.append((name, 0, perr or "解析失敗"))
            continue
        say(f"  ✅ 清單 {len(ents)} 筆")
        scope.append((name, len(ents), ""))
        got = hits(ents)
        if not got:
            say("  ⛔ 詞表一個都沒命中（⚠ 這句話的範圍就是**這一份清單**）")
        for w in WORDS:
            for p, desc in got.get(w, [])[:12]:
                allhit.setdefault((p, desc), set()).add(w)
        for w in sorted(got, key=lambda x: -len(got[x])):
            say(f"  ⭐ 「{w}」命中 {len(got[w])} 筆")
            for p, desc in got[w][:8]:
                say(f"       {p}　{desc[:60]}")
            if len(got[w]) > 8:
                say(f"       …（另 {len(got[w]) - 8} 筆）")

    # ── ③ 命中的頁再抓一次，撈它自己送出的端點 ──────────────
    say(f"\n{'=' * 74}\n③ 命中的頁面裡出現的 `rwd/zh` / `/v1` 端點")
    pages = [p for (p, _d) in allhit
             if p.startswith("http") and p.endswith((".html", ".htm"))][:MAX_PAGES]
    say(f"  ⚠ 只抓前 {len(pages)} 頁（⛔ 不是全部 ⇒ 這一節的範圍也是有限的）")
    for p in pages:
        txt, err = fetch(p)
        if err:
            say(f"  ✗ {p}｜{err}")
            continue
        eps = sorted(set(EP_RE.findall(txt)))
        say(f"  {p}｜端點 {len(eps)}：{eps[:10]}")

    # ── ④ ⭐ 掃描範圍表：⛔ 沒有這張表，上面的每一句否定都不成立 ──
    say(f"\n{'=' * 74}\n④ ⭐ 掃描範圍表（⛔ 只要有任何一列失敗，就不可以寫「官方沒有」）")
    bad = [s for s in scope if s[2]]
    for name, n, err in scope:
        say(f"  {'✗' if err else '✅'} {name}｜{n} 筆" + (f"｜{err}" if err else ""))
    say(f"\n  ⇒ 成功 {len(scope) - len(bad)} / {len(scope)} 份目錄")
    if bad:
        say("  ⛔⛔ **有目錄沒掃到** ⇒ 這一趟的結論只涵蓋成功的那幾份，")
        say("      ⚠ 而在開發容器裡全失敗是我方閘道擋的（第六點），**不是事實**")
    else:
        say("  ⭐ 六份目錄全部掃到 ⇒ 這一趟的否定句可以寫，⚠ 但要連同詞表一起寫")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    say(f"\n[recon] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                            # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
