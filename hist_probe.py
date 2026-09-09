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
    html = raw.decode("utf-8", "replace")
    if html.count("�") > len(html) * 0.02:      # ⚠ 可能是 big5
        html = raw.decode("cp950", "replace")
        say(f"{pad}   ⚠ utf-8 解不開，改用 cp950（櫃買舊站常見）")
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
    hrefs = []
    for h in re.findall(r'href=["\']([^"\']+)', html):
        if h.startswith(("javascript:", "mailto:", "#")):
            continue
        hrefs.append(urllib.parse.urljoin(url, h))
    hrefs = sorted(set(hrefs))
    say(f"{pad}   連結 {len(hrefs)} 個" + (f"：{[h.replace(ROOT,'/') for h in hrefs[:15]]}"
                                          if hrefs else "（沒有）"))
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
