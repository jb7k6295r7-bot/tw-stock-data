#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hist_probe.py — 櫃買**歷史資料站** `hist.tpex.org.tw` 的探針。只測、不寫資料。

## 為什麼這一支值得單獨開一個檔

使用者 2026-09-09 給了：

    https://hist.tpex.org.tw/Hist/EMERGINGSTOCK/HISTORICAL/NSHISTORY.HTML

⭐ **重點不是這一頁，是這個主機**。今天為止我方所有櫃買相關的探測都打
`www.tpex.org.tw`，而**這是一個沒看過的主機**，路徑還寫著 `Hist/` 與 `HISTORICAL/`。

⛔ 而我今晚對三個地方講過「上櫃沒有歷史來源」：

| 我說過的話 | 如果這個站有歷史，它就是錯的 |
|---|---|
| 上櫃交易日曆 2015-01-05~2026-08-31 **2,841 天永遠拿不到判準** | ⇒ 要改 |
| 上櫃除權息的**歷史**官方來源：仍然沒有 | ⇒ 要改 |
| `otc_adj.py` 走 FinMind 是因為「TPEx 官方沒有歷史」 | ⇒ 要改 |

⚠ 那三句的依據都是「打 `www.tpex.org.tw` 打不到」——
**而「我查過的那個主機沒有」不等於「櫃買沒有」。**
⭐ 這正是今天反覆出現的形狀：**只否定我查過的那個範圍。**

## 這一支要答什麼

1. 這一頁**在不執行 js 的前提下**拿不拿得到內容？（`www` 那邊的頁面全敗在這裡）
2. 它給的是**什麼**？——⛔ 讓它自己說（標題、看得見的字、表格結構），不要從路徑猜。
3. ⭐ **這個站上還有什麼**？——從頁面自己的連結去看，
   ⛔ 不是我去拼 `Hist/STOCK/...` 之類的路徑。
4. 有沒有**日期範圍**？沒有日期就不是歷史檔案庫。

## ⛔ 判準

「有歷史」要能指出**最早與最晚的日期**。
⛔ 只看到 `HISTORICAL` 這個字不算——那是路徑，不是資料。
"""
import io
import os
import re
import sys
import traceback
import urllib.parse

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_hist_probe.txt")

# ⛔ 網址由使用者 2026-09-09 提供，不是自行生成。
URL = "https://hist.tpex.org.tw/Hist/EMERGINGSTOCK/HISTORICAL/NSHISTORY.HTML"
ROOT = "https://hist.tpex.org.tw/"

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# hist_probe.py 的輸出。這是探針結果，不是資料。\n")
            f.write(f"# 主機：hist.tpex.org.tw（使用者 2026-09-09 提供）\n")
            f.write("# ⛔ 要答的：這個站有沒有**上櫃／興櫃的歷史**——"
                    "而我今晚說過三次「上櫃沒有歷史來源」。\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[hist] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[hist] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


def _text(html):
    t = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S)
    t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


def _dates(t):
    """抓民國與西元兩種日期，回排序後的清單。⛔ 兩種都找，不預設它用哪一種。"""
    out = set()
    for m in re.findall(r"\b(1[0-9]{2})[/-]([01]?[0-9])[/-]([0-3]?[0-9])\b", t):
        out.add(f"{int(m[0]) + 1911:04d}-{int(m[1]):02d}-{int(m[2]):02d}")
    for m in re.findall(r"\b(20[0-9]{2})[/-]([01]?[0-9])[/-]([0-3]?[0-9])\b", t):
        out.add(f"{int(m[0]):04d}-{int(m[1]):02d}-{int(m[2]):02d}")
    for m in re.findall(r"\b(1[0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])\b", t):
        out.add(f"{int(m[0]) + 1911:04d}-{m[1]}-{m[2]}")
    # ⛔ 2026-09-09 第二輪的教訓：上面三種都沒認出「**95年12月29日**」，
    #   於是我報「抓不到任何日期」——**而那個檔的表頭第一行就寫著日期**。
    #   ⚠ 同一個形狀今天第 N 次：**只查我想到的那幾種寫法，然後把 0 讀成沒有。**
    for m in re.findall(r"(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", t):
        y = int(m[0])
        out.add(f"{(y + 1911) if y < 200 else y:04d}-{int(m[1]):02d}-{int(m[2]):02d}")
    # ★ 檔名型的民國日期（AA951229.TXT）——這個站就是這樣命名的。
    #   ⛔ 不可以用 `\b`：`AA951229` 的 `A` 與 `9` 都是 word char，**中間沒有邊界**，
    #     所以 `\b` 在那裡不成立 ⇒ 整個 pattern 不會命中。
    #   ⇒ 改成「前面不是數字、後面不是數字」，這樣 `AA951229` 與 `_951229` 都認得。
    for m in re.findall(r"(?<!\d)([89]\d|1[0-2]\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)", t):
        out.add(f"{int(m[0]) + 1911:04d}-{m[1]}-{m[2]}")
    return sorted(out)


def _look(url, label, depth=0):
    """量一個頁面：形狀、看得見的字、表格、日期、連結。→ (連結清單, 文字)"""
    pad = "  " * depth
    say(f"{pad}── {label}")
    say(f"{pad}   {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        say(f"{pad}   ✗ 抓不到：{str(err)[:140]}")
        return [], ""
    # ⛔ 2026-09-09 第一輪的教訓：這裡本來是「亂碼率 > 2% 就改 cp950」，
    #   而實際那一頁的亂碼率是 **1.7%**（1,181 bytes 裡約 20 個 U+FFFD）
    #   ⇒ 門檻沒過、整頁維持亂碼，我看到的是 `���v��Ƭd��>`。
    #   ⚠ **寫死的門檻是在猜**。改成**比較法**：兩種都解，取亂碼少的那一個。
    #   ⭐ 這不需要知道對方用什麼編碼，也不需要挑一個數字。
    cands = []
    for enc in ("utf-8", "cp950", "big5hkscs"):
        try:
            d = raw.decode(enc, "replace")
        except LookupError:
            continue
        cands.append((d.count("\ufffd"), enc, d))
    cands.sort()
    bad, enc, html = cands[0]
    if enc != "utf-8":
        say(f"{pad}   ⚠ 編碼不是 utf-8：取亂碼最少的 **{enc}**"
            f"（{[(e, n) for n, e, _ in cands]}）")
    t = _text(html)
    han = len(re.findall("[一-龥]", t))
    tr = len(re.findall(r"<tr[ >]", html, re.I))
    say(f"{pad}   ✓ {len(raw):,} bytes｜中文 {han:,} 字｜<tr> {tr} 個"
        + ("  ← ⚠ 中文太少，可能是 js 空殼" if han < 50 else ""))
    say(f"{pad}   ★ 看得見的字（前 400）：{t[:400]}")
    ds = _dates(t)
    if ds:
        say(f"{pad}   ⭐ **日期 {len(ds)} 個｜{ds[0]} ~ {ds[-1]}**"
            "　← 這一行決定它算不算「有歷史」")
    else:
        say(f"{pad}   ⛔ **抓不到任何日期** ⇒ 這一頁不是歷史資料本身")
    # ⛔ 第一輪只抓 `href`，於是「連結 0 個」——**而那是我量錯，不是真的沒有**。
    #   1KB 的頁面 ＋ 0 個 <tr> ＋ 0 個 href ⇒ 典型的 **frameset**，
    #   而 frame 的目標寫在 `src=` 不是 `href=`。
    #   ⭐ 同一個形狀今天第 N 次：**只查我想到的那一種寫法，然後把 0 讀成沒有。**
    #   ⇒ 三種都收：`href=`、`src=`（frame／iframe／script）、以及原始碼裡任何
    #     像頁面路徑的字串（`.html`／`.php`／`.htm`）。
    links = []
    for pat in (r'href=["\']([^"\']+)', r'<i?frame[^>]+src=["\']([^"\']+)',
                r'src=["\']([^"\']+\.(?:html?|php))["\']'):
        links += re.findall(pat, html, re.I)
    loose = re.findall(r'["\'>\s]([A-Za-z0-9_./-]+\.(?:html?|php))["\'<\s]', html, re.I)
    hrefs = []
    for h in links + loose:
        if h.startswith(("javascript:", "mailto:", "#")):
            continue
        hrefs.append(urllib.parse.urljoin(url, h))
    hrefs = sorted(set(hrefs))
    say(f"{pad}   連結／frame／路徑字串 {len(hrefs)} 個"
        + (f"：{[h.replace(ROOT,'/') for h in hrefs[:15]]}" if hrefs else "（真的沒有）"))
    # ★ frameset 的話，原始碼本身要印出來看——1KB 全部印得完
    if len(raw) < 4000 and tr == 0:
        say(f"{pad}   ★ 這一頁只有 {len(raw):,} bytes 且沒有表格，**原始碼全印**：")
        for i in range(0, min(len(html), 1600), 200):
            say(f"{pad}     {html[i:i+200]!r}")
    return hrefs, t


def main():
    say("── 櫃買歷史資料站 hist.tpex.org.tw 探針 ──")
    say("⛔ 重點不是這一頁，是**這個主機**：今天為止所有櫃買探測都打 `www.tpex.org.tw`，")
    say("   而我今晚對三個地方說過「上櫃沒有歷史來源」，依據都是「打 www 打不到」。")
    say("   ⭐ 「我查過的那個主機沒有」**不等於**「櫃買沒有」。")
    say("判準：要能指出**最早與最晚的日期**才算有歷史。"
        "⛔ 路徑裡有 `HISTORICAL` 這個字不算。")

    say("\n[1] 使用者給的那一頁")
    hrefs, _t = _look(URL, "EMERGINGSTOCK/HISTORICAL/NSHISTORY.HTML")

    say("\n[2] 站台根目錄（看這個主機上還有什麼）")
    rhrefs, _ = _look(ROOT, "hist.tpex.org.tw/")

    # ★ 從**頁面自己的連結**往下走一層，⛔ 不是我去拼路徑
    say("\n[3] ★ 從上面兩頁**自己的連結**往下走一層"
        "（⛔ 只跟連結，不拼路徑）")
    seen = {URL, ROOT}
    cand = [h for h in (hrefs + rhrefs)
            if h.startswith("https://hist.tpex.org.tw/") and h not in seen]
    if not cand:
        say("     （兩頁都沒有可跟的站內連結——那本身就是結論："
            "要嘛是 js 空殼，要嘛這一頁是終點）")
    for h in cand[:8]:
        seen.add(h)
        _look(h, h.replace(ROOT, "/"), depth=1)

    say("\n[3.5] ⭐⭐ 查詢表單**自己**怎麼組檔名（⛔ 這是證據，不是我拼路徑）")
    say("     第二輪拆開 frameset 之後看到 `DAILY/AA951229.TXT`＝民國 95/12/29 的靜態日檔。")
    say("     ⇒ 剩下唯一的問題是：**它怎麼從「年＋月」算出檔名**，")
    say("       以及 **`EMERGINGSTOCK` 以外還有沒有別的區段**（上櫃在不在）。")
    say("     ⛔ 這兩件都不可以用猜的。查詢頁 `NSHISTORYQRY.HTML` 裡有下拉選單與 js，")
    say("       **它自己就會講**——所以把它的 `option` 與 js 原文印出來。")
    qry = ROOT + "Hist/EMERGINGSTOCK/HISTORICAL/NSHISTORYQRY.HTML"
    raw, err = B.get(qry, retries=2, timeout=60)
    if err:
        say(f"     ✗ 抓不到：{str(err)[:120]}")
    else:
        cands = []
        for enc in ("big5hkscs", "cp950", "utf-8"):
            try:
                d = raw.decode(enc, "replace")
            except LookupError:
                continue
            cands.append((d.count("\ufffd"), enc, d))
        cands.sort()
        h = cands[0][2]
        opts = re.findall(r"<option[^>]*value=[\"']?([^\"'> ]+)", h, re.I)
        say(f"     ★ `option` 的 value 共 {len(opts)} 個：{opts[:40]}")
        # ⭐ js 裡組檔名的那一段——找出現 'AA' 或 '.TXT' 或 location 的行
        js = re.findall(r"<script[^>]*>(.*?)</script>", h, re.S | re.I)
        say(f"     ★ inline <script> {len(js)} 段，逐段印（去空白，每段最多 900 字）：")
        for i, blk in enumerate(js):
            b = re.sub(r"\s+", " ", blk).strip()
            if not b:
                continue
            say(f"       ── 第 {i + 1} 段（{len(b)} 字）")
            for k in range(0, min(len(b), 900), 180):
                say(f"         {b[k:k + 180]}")
        # ★ 表單本身
        for m in re.finditer(r"<form[^>]*>", h, re.I):
            say(f"     ★ <form> 標籤原文：{m.group(0)}")
        names = sorted(set(re.findall(r"<(?:input|select)[^>]*name=[\"']?([A-Za-z0-9_]+)",
                                      h, re.I)))
        say(f"     ★ 表單欄位名：{names}")

    say("\n[4] 這一輪要回答的三句話")
    say("  ⛔ 以下三句，**只有在第 [1]~[3] 節真的看到日期範圍時才可以改**：")
    say("     ① 上櫃交易日曆 2015-01-05~2026-08-31 那 2,841 天永遠拿不到判準")
    say("     ② 上櫃除權息的**歷史**官方來源：仍然沒有")
    say("     ③ `otc_adj.py` 走 FinMind 是因為「TPEx 官方沒有歷史」")
    say("  ⚠ 若這個站只有**興櫃**（EMERGINGSTOCK）而沒有上櫃，那三句**不變**，")
    say("    ⛔ 但要改寫成「上櫃沒有；興櫃有」——**不要把興櫃的發現寫成上櫃的**。")
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
