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

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_site_inventory.txt")

SITES = [
    ("TWSE", "https://www.twse.com.tw/res/data/zh/menu-mega.html"),
    ("TPEx", "https://www.tpex.org.tw/data/menu/zh-tw/menu.json"),
]

# ⭐ 我方**還缺什麼**。一條一組關鍵詞（任一命中就算）。
#   ⛔ 這份清單就是「要問的全部」——問一次問完，不要一條一封信。
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


def parse_menu(label, raw):
    """→ [(標題, 連結)]。JSON 與 HTML 兩種都吃。"""
    txt = raw.decode("utf-8", "replace")
    try:
        d = json.loads(txt)
    except ValueError:
        d = None
    if d is not None:
        out = []
        flatten(d, out)
        return out
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
    for label, url in SITES:
        say(f"── {label}｜{url}")
        raw, err = B.get(url, retries=2, timeout=60)
        if err or not raw:
            say(f"   ✗ 抓不到：{str(err)[:120]}")
            say("   ⛔ 抓不到**不等於**這個站沒有——這一趟對它一無所知。")
            say("")
            continue
        items = parse_menu(label, raw)
        menus[label] = items
        say(f"   ✓ {len(raw):,} bytes｜攤平出 **{len(items)} 條**選單項目")
        say("")

    if not menus:
        say("⛔ 兩站的選單都抓不到 ⇒ 這一趟什麼都沒問到。")
        return _write(1)

    say("── 逐條比對「我方還缺什麼」──")
    say("")
    for want, words in WANTED:
        say(f"★ {want}")
        for label, items in menus.items():
            hits = [(n, h) for n, h in items if any(w in n for w in words)]
            if not hits:
                say(f"   {label}：⛔ 選單上**沒有**這個名字"
                    "（⚠ 這不代表站上沒有，只代表選單沒列）")
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
                if len(seen) >= 6:
                    say(f"      …（另有 {len(hits) - 6} 條）")
                    break
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
