#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site_inventory.py — 「這個站到底有沒有我要的東西」**一次問完**。

## 為什麼開這一支

使用者 2026-09-10：
> 「以後網站到底有沒有需要的資料**可以一次跟我說**，
>   不需要我多次甚至分批給你測試！」

⛔ 我今天的做法正好相反：`hist.tpex` 我跑了**七輪**探針、
上櫃的東西我一條一條問、使用者一次一個網址餵我。
⚠ 而那七輪裡有兩輪的結論是錯的（判準是我自己編的），
  等於**讓使用者陪我試錯**。

⭐ 而正確的做法今天早上就出現了——市場情報分析線是照**全站選單**找的：

    TWSE  https://www.twse.com.tw/res/data/zh/menu-mega.html   （195 條）
    TPEx  https://www.tpex.org.tw/data/menu/zh-tw/menu.json     （485 條）

⇒ 他們兩次推翻我「官方沒有」的結論（上櫃交易日曆、上櫃除權息歷史），
  兩次都是因為**他們看的是全站清單，我看的是我想得到的路徑**。

## 這一支做什麼

1. 抓兩站的**全站選單**，攤平成 (標題, 連結) 清單
2. 拿 `WANTED`（我方還缺什麼）逐條去比對標題
3. 印出「**這個站有沒有**」——一次一份，⛔ 不必來回

⛔ 它只回答「**選單上有沒有這個名字**」，不回答「那條端點能不能用」。
  ⚠ 兩者差很遠：`chtm` 的選擇器寫 `data-start=20080409`，實際下限在民國 99~100
  之間——**選擇器騙人**。⇒ 命中之後仍然要照 `docs/NEW_ENDPOINT.md` 走一次。
"""
import io
import json
import os
import re
import sys
import traceback

import backfill as B
# ⭐ 同一件事只准有一份實作（四點五）：錯誤訊息**中間**省略那條規矩
from feeds import _why

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_site_inventory.txt")

SITES = [
    ("TWSE", "https://www.twse.com.tw/res/data/zh/menu-mega.html"),
    ("TPEx", "https://www.tpex.org.tw/data/menu/zh-tw/menu.json"),
    # ⭐⭐ 2026-09-13 加這兩份，理由是**選單掃不到它們**：
    #   openapi 那一族（`openapi.twse.com.tw` / `tpex.org.tw/openapi`）是
    #   另一套目錄，⛔ 不在 mega menu／menu.json 裡。
    #   ⚠ 而我方已經有四條端點走的就是 openapi（`delist_probe` 那一族）
    #     ⇒ 「選單上沒有」曾經**同時**意味著「我方正在用它」。
    #   ⇒ 少了這兩份，這一支的「⛔ 選單上沒有」就會漏掉一整族。
    ("TWSE-OpenAPI", "https://openapi.twse.com.tw/v1/swagger.json"),
    ("TPEx-OpenAPI", "https://www.tpex.org.tw/openapi/swagger.json"),
    # ⭐⭐ 2026-09-13 加：sitemap 有 **3,109 條**，比 mega menu 的 195 條寬得多。
    #   ⛔ 而它**只有網址、沒有中文** ⇒ 拿中文詞表去搜必定 0 命中
    #     ——⚠ 而那個 0 跟「這個站沒有」長得一模一樣（第七點）。
    #   ⇒ 所以 `WANTED` 每一列多帶一組**路徑詞**（英文），並在最後那張表
    #     把「這份目錄有幾條含中文」講出來，讓那個 0 自己說明它是結構造成的。
    ("TWSE-sitemap", "https://www.twse.com.tw/sitemap.xml"),
]

# ⭐ 我方**還缺什麼**。一條一組關鍵詞（任一命中就算）。
#   ⛔ 這份清單就是「要問的全部」——問一次問完，不要一條一封信。
# ⚠ 每一組最多印幾條。⛔ 6 太少（「分點」那一組有 34 條）——
#   而這份輸出的用途是**挑哪一條去開**，挑之前要看得到全部。
CAP = 40

WANTED = [
    ("月營收（歷史，逐月）", ("月營業收入", "營業收入彙總", "月營收")),
    ("財報（歷史，逐季）", ("財務報表", "綜合損益", "資產負債")),
    ("本益比（歷史段，含收盤價欄）", ("本益比", "殖利率", "股價淨值比")),
    ("創新板成分清單", ("創新板",)),
    ("集保／股權分散（歷史）", ("股權分散", "集保", "持股分級")),
    ("上櫃交易日曆（歷史）", ("日成交量值", "成交量值指數", "統計資訊")),
    ("上櫃除權息（歷史）", ("除權息", "除權除息")),
    ("上櫃減資（歷史）", ("減資", "恢復買賣")),
    ("變更股票面額", ("面額", "變更股票")),
    ("暫停／停止交易（歷史）", ("暫停交易", "停止交易", "終止上市", "終止櫃檯")),
    # ⭐⭐ 2026-09-11 新增，⛔ 而它是從一個**假的 0** 來的：
    #   上一列的關鍵詞在 TPEx 那 485 條選單上「終止」相關**0 命中**，
    #   ⚠ 而我差一點把它讀成「上櫃沒有終止名單」。
    #   ⛔ 實際上那一列的關鍵詞只有「終止**上市**」與「終止**櫃檯**」
    #     ——上櫃的說法可能是「下櫃」「終止有價證券」「撤銷」。
    #   ⭐ 第七點：報「某群 0 筆」要附上該判準在該群抓到的**正例數**；
    #     上一列在 TPEx 抓到 4 條（都是停止／暫停交易），⇒ 判準活著，
    #     但**「終止」那一半沒有正例** ⇒ ⛔ 那個 0 不能當結論。
    #   ⇒ 拆成獨立一列，關鍵詞放寬，讓它自己講得出有沒有。
    ("⭐ 終止上市／上櫃（下市下櫃名單）",
     ("終止上市", "終止櫃檯", "終止有價證券", "終止買賣",
      "下市", "下櫃", "撤銷", "停止買賣")),
    ("處置／注意股（歷史）", ("處置", "注意", "警示")),
    ("外資持股比率", ("外資", "陸資", "僑外")),
    ("發行股數／股本", ("發行股數", "股本", "實收資本")),
    ("借券／融券（歷史）", ("借券", "融券", "信用交易")),
    ("盤後定價／零股／鉅額", ("盤後", "零股", "鉅額")),
    # ⭐⭐ 2026-09-12 新增。K線分析線 0040~0115 四封信在四個第三方站之間找「分點」，
    #   最後收斂到 FinMind ⇒ ⛔ 而 FinMind 免費層回 400（實測，見 `_finmind_probe.txt`）。
    # ⚠ 而我方**從來沒有拿「券商／分點」去問過官方選單**
    #   ⇒ 先前查不到不是「官方沒有」，是**沒有人問過**（第三點②那個「假的 0」）。
    # ⭐ 這正是 K線分析線自己那句教訓：
    #   「去外面找答案之前，沒有先查自己手上的來源清單。」
    ("⭐ 分點／券商買賣（K線分析線 2026-09-12 要的）",
     ("券商", "分公司", "分點", "買賣證券", "經紀商", "各券商")),
    ("八大行庫／官股買賣", ("行庫", "官股", "公股")),
    # ⭐⭐ 2026-09-13 加這三組——⛔ 而它們是從我**兩句沒有掃描範圍的否定句**來的：
    #   ①「上市沒有官方換股比率欄位」⇒ 使用者指出 `TWTAVU` 就有（我 grep 0 次）
    #   ②「上市沒有官方除權息明細」  ⇒ 實測 `exRight/TWT48U` 有 13 欄，
    #      含無償配股率／現金增資配股率／現金增資認購價／現金股利（權值息值是分開的）
    #   ⚠ 而那兩張都是**預告表**（三個區間回同一批列）⇒ 只能從今天起累積。
    #   ⇒ ⭐ 所以要問的是**歷史**那一半：官方有沒有逐日／逐期的明細表。
    ("⭐ 除權息明細（權值／息值分開、現增認購價與認購率）",
     ("除權除息預告", "除權息預告", "除權除息計算", "配股率", "認購", "權值", "息值")),
    ("⭐ 減資換股率／退還股款（歷史）",
     ("減資預告", "減資換股", "退還股款", "恢復買賣參考價")),
    ("⭐ 漲跌停價格（官方直接給的）", ("漲停", "跌停", "漲跌幅")),
    # ⭐⭐ 2026-09-15 新增。⛔ 而它也是從一個**沒有人問過**來的：
    #   清單 F2（大盤成交金額／股數／筆數的歷史）被記成「⛔ 卡住」，
    #   理由是 `FMTQIK` 那三欄**口徑不同**（同日實測成交股數 2.5 倍）。
    # ⚠ 那個理由只說得了 **FMTQIK 這一條**——⛔ 它沒有說「官方沒有別的」。
    #   ⭐ 而這份目錄從頭到尾**沒有一列**在問市場成交統計
    #     ⇒ F2 那句「卡住」是在一個**沒掃過的範圍**上下的（三點①）。
    # ⚠ 而 F2 真正要問的是**口徑**，⛔ 不只是「有沒有這張表」：
    #   我方 `MI_INDEX type=IND` 那份含不含鉅額／零股／盤後定價／外幣
    #   ——⭐ 而 `notes` 自己 24 分鐘內講過兩種相反的說法（CLAUDE.md 二）
    #   ⇒ ⛔ 找到新端點也**不可以**照 `notes` 判，仍然要拿重疊日逐位對。
    ("⭐ 大盤／市場成交統計（金額、股數、筆數的歷史）",
     ("市場成交", "成交統計", "成交量值", "日成交量", "成交筆數",
      "市場統計", "交易統計", "大盤統計")),
    ("當日沖銷（歷史）", ("當日沖銷", "現股當沖", "當沖")),
]

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# site_inventory.py 的輸出。**只讀不寫資料。**\n")
            f.write("# 問的是：「這個站到底有沒有我要的東西」——一次問完。\n")
            f.write("# ⛔ 它只回答「選單上有沒有這個名字」，"
                    "不回答「那條端點能不能用」。\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[inv] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[inv] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


# ⭐ 路徑詞（英文）：⛔ 只有中文詞表的話，sitemap 那 3,109 條**結構上**一條都不會中。
#   ⚠ 鍵要跟 WANTED 的標籤一字不差，⛔ 對不上就等於那一列沒有路徑詞（會被下面驗出來）。
PATH_WORDS = {
    "⭐ 除權息明細（權值／息值分開、現增認購價與認購率）":
        ("exright", "exRight", "TWT48U", "TWT49U", "dividend", "t187ap45"),
    "⭐ 減資換股率／退還股款（歷史）":
        ("reduction", "reducation", "TWTAVU", "TWTAUU", "capitalreduction"),
    "⭐ 漲跌停價格（官方直接給的）": ("limit", "fluctuation"),
    "月營收（歷史，逐月）": ("t187ap05", "revenue"),
    "財報（歷史，逐季）": ("t187ap06", "t163sb", "financial"),
    "⭐ 終止上市／上櫃（下市下櫃名單）": ("suspend", "delist", "terminat"),
    "⭐ 分點／券商買賣（K線分析線 2026-09-12 要的）": ("broker", "brk", "bsr"),
}


def match(items, words, path_words=()):
    """→ 命中的 [(標題, 連結)]。

    ⭐ 兩層：中文詞比**標題**，路徑詞比**標題＋連結**且不分大小寫。
    ⛔ 少了第二層，sitemap 那一族（只有網址）**結構上**一條都不會中，
    ⚠ 而那個 0 跟「這個站沒有」長得一模一樣（第七點）。
    """
    out = []
    for n, h in items:
        if any(w in n for w in words):
            out.append((n, h))
            continue
        if path_words:
            hay = (str(n) + " " + str(h)).lower()
            if any(str(q).lower() in hay for q in path_words):
                out.append((n, h))
    return out


def has_cjk(s):
    """→ 這個字串裡有沒有中日韓字。⛔ 一份沒有中文的清單，中文詞表搜不到是**必然**。"""
    return any("\u4e00" <= c <= "\u9fff" for c in str(s))


def flatten(obj, out, trail=""):
    """把選單（不管是 JSON 樹還是 HTML）攤平成 (標題, 連結)。"""
    if isinstance(obj, dict):
        name = ""
        for k in ("name", "title", "text", "label", "cname"):
            if isinstance(obj.get(k), str) and obj[k].strip():
                name = obj[k].strip()
                break
        href = ""
        for k in ("url", "link", "href", "path"):
            if isinstance(obj.get(k), str) and obj[k].strip():
                href = obj[k].strip()
                break
        full = (trail + " / " + name) if (trail and name) else (name or trail)
        if name:
            out.append((full, href))
        for v in obj.values():
            if isinstance(v, (dict, list)):
                flatten(v, out, full)
    elif isinstance(obj, list):
        for v in obj:
            flatten(v, out, trail)


def parse_openapi(d):
    """OpenAPI/Swagger 文件 → [(中文說明, 路徑)]。

    ⛔ 它的形狀跟選單**完全不同**：名字在 `paths[p][method].summary` 裡，
    ⚠ 而 `flatten()` 抓的是 `name/title/text/label/cname` ⇒ 它一條都撈不到。
    ⇒ 少了這一支，兩份 OpenAPI 目錄會「抓得到、攤平出 0 條」——
      ⛔ 而那看起來跟「這個站沒有」**一模一樣**。
    """
    paths = d.get("paths")
    if not isinstance(paths, dict):
        return None
    out = []
    for p, v in paths.items():
        desc = ""
        if isinstance(v, dict):
            for _m, op in v.items():
                if isinstance(op, dict):
                    desc = op.get("summary") or op.get("description") or ""
                    if desc:
                        break
        out.append((str(desc) or p, p))
    return out


def parse_menu(label, raw):
    """→ [(標題, 連結)]。選單 JSON／HTML／OpenAPI 三種都吃。"""
    txt = raw.decode("utf-8", "replace")
    try:
        d = json.loads(txt)
    except ValueError:
        d = None
    if d is not None:
        api = parse_openapi(d) if isinstance(d, dict) else None
        if api is not None:
            return api
        out = []
        flatten(d, out)
        return out
    # sitemap.xml：只有 <loc>網址</loc>，⛔ 沒有任何標題
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", txt)
    if locs:
        return [(u, u) for u in locs]
    # HTML：抓 <a href=...>文字</a>
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         txt, re.S | re.I):
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip()
        if name:
            out.append((name, m.group(1).strip()))
    return out


def main():
    say("── 「這個站到底有沒有我要的東西」一次問完 ──")
    say("⛔ 這一支只回答「**選單上有沒有這個名字**」，不回答「那條端點能不能用」。")
    say("  ⚠ 兩者差很遠：`chtm` 的選擇器寫 `data-start=20080409`，"
        "實際下限在民國 99~100 之間——**選擇器騙人**。")
    say("  ⇒ 命中之後仍然要照 `docs/NEW_ENDPOINT.md` 走一次"
        "（第 0 步：先印 notes／hints／title／params／total）。")
    say("")

    menus = {}
    scope = []          # ⭐ (目錄, 網址, 幾條, 失敗原因)：最後那張掃描範圍表
    for label, url in SITES:
        say(f"── {label}｜{url}")
        # ⭐⭐ 這一行的參數是**實驗設計**，⛔ 不是隨手調大的。
        #
        #   2026-09-13：這裡 `retries=2, timeout=60` 抓 TPEx 的 swagger.json
        #   連兩次 `IncompleteRead`（476,923 bytes 只讀到 24,064）。
        #   ⭐ 而**同一趟 job** 裡 `tpex_probe.py` 抓**同一個 URL 成功**了
        #     （`✓ 取得 476,923 bytes`）⇒ ⛔ 不是對方壞掉。
        #   ⇒ 兩邊唯一的差別是 **`timeout` 90 vs 60**。
        #
        #   ⛔ 我第一版把 `retries` 也一起改成 4 ——那就**測不出是哪一個**
        #     （CLAUDE.md 三點5：要判一個參數管什麼，只准動那一個變數）。
        #   ⇒ 改回跟那支**一模一樣**的參數：只有 timeout 從 60 變 90。
        #     ⚠ 下一趟若還是失敗，就證明 timeout **不是**成因，要往別處找。
        raw, err = B.get(url, retries=2, timeout=90)
        if err or not raw:
            # ⛔⛔ 這裡原本是 `str(err)[:120]`——**砍尾巴**（六點六）。
            #   ⚠ SSL／憑證／逾時那一族，可行動的部分永遠在後面，
            #     而前 120 個字元每一次都長得一樣。⇒ 改走 `_why`（中間省略）。
            say(f"   ✗ 抓不到：{_why(err)}")
            say("   ⛔ 抓不到**不等於**這個站沒有——這一趟對它一無所知。")
            scope.append((label, url, 0, _why(err)))
            say("")
            continue
        items = parse_menu(label, raw)
        menus[label] = items
        say(f"   ✓ {len(raw):,} bytes｜攤平出 **{len(items)} 條**選單項目")
        scope.append((label, url, len(items),
                      "" if items else "⛔ 攤平出 0 條（抓得到但解析不出清單）"))
        say("")

    if not menus:
        say("⛔ 兩站的選單都抓不到 ⇒ 這一趟什麼都沒問到。")
        return _write(1)

    say("── 逐條比對「我方還缺什麼」──")
    say("")
    for want, words in WANTED:
        say(f"★ {want}")
        for label, items in menus.items():
            pw = PATH_WORDS.get(want, ())
            hits = match(items, words, pw)
            if not hits:
                # ⭐⭐ 第七點：報「0 筆」一定要附這一群的**正例數**。
                #   ⛔ 這份目錄若一條中文都沒有，這個 0 是**結構**造成的，
                #     ⚠ 而它跟「這個站沒有」在紙上一模一樣。
                ncjk = sum(1 for n, _h in items if has_cjk(n))
                if ncjk == 0 and not pw:
                    say(f"   {label}：⛔⛔ 這份目錄 {len(items)} 條**一條中文都沒有**"
                        "，而這一列沒有路徑詞 ⇒ 這個 0 是結構造成的，"
                        "**不是「站上沒有」**")
                else:
                    say(f"   {label}：⛔ 選單上**沒有**這個名字"
                        f"（⚠ 這不代表站上沒有，只代表選單沒列"
                        f"｜這份目錄 {ncjk}/{len(items)} 條含中文）")
                continue
            say(f"   {label}：⭐ **{len(hits)} 條**")
            seen = set()
            for n, h in hits:
                if n in seen:
                    continue
                seen.add(n)
                say(f"      {n}")
                if h:
                    say(f"        → {h}")
                # ⛔ 2026-09-12：上限 6 讓「分點」那一組只看得到 6/34 條
                #   ⇒ 而**要挑哪一條去開，必須看完全部** ⇒ 拉到 40。
                # ⚠ 這一節本來就是「一次問完」用的，⛔ 截斷等於又要再問一次。
                if len(seen) >= CAP:
                    say(f"      …（另有 {len(hits) - CAP} 條，⛔ 被 CAP={CAP} 截斷）")
                    break
        say("")
    # ── ⭐⭐ 掃描範圍表 ────────────────────────────────────
    #   ⛔ 沒有這張表，上面每一句「選單上沒有」都不知道成立範圍（三點①）。
    say("── ⭐ 掃描範圍表（⛔ 只要有一列失敗，這一趟就不可以寫出「官方沒有」）──")
    bad = [x for x in scope if x[3]]
    for label, url, n, err in scope:
        ncjk = sum(1 for nm, _h in menus.get(label, []) if has_cjk(nm))
        say(f"  {'✗' if err else '✅'} {label}｜{n} 條"
            f"（含中文 {ncjk}）｜{url}" + (f"｜{err}" if err else ""))
    say(f"  ⇒ 成功 {len(scope) - len(bad)} / {len(scope)} 份目錄"
        f"｜合計 {sum(x[2] for x in scope):,} 條")
    if bad:
        say("  ⛔⛔ **有目錄沒掃到** ⇒ 這一趟的否定句只涵蓋成功的那幾份。")
        say("      ⚠ 而在開發容器裡全失敗是我方閘道擋的（第六點），**不是事實**。")
    say("")
    say("── ⇒ 這份輸出的用法 ──")
    say("  ① 有命中的：拿連結照 `docs/NEW_ENDPOINT.md` 走一次，⛔ 不要直接當成可用")
    say("  ② 沒命中的：那才是**真的要請人去站上翻**的——"
        "而且是**一次把這幾條一起請託**，⛔ 不要一條一封信")
    return _write(0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                        # noqa: BLE001
        say("")
        say("✗ 這一趟炸了，traceback 原文：")
        say(traceback.format_exc())
        _write(1)
        raise
