#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bsr_probe.py — TWSE「券商買賣證券日報表」的端點探針。⛔ 只測、不寫資料。

    https://bsr.twse.com.tw/bshtm/

## 來源

**使用者 2026-09-12 提供**，⛔ 不是我自行生成的路徑
（`tw-data-sources` 3-4 的規矩：端點要有出處）。

## 為什麼重要

K線分析線 0040~0115 四封信在 goodinfo／wantgoo／MoneyDJ／永豐金 四個第三方站
之間找「**分點**」，最後收斂到 FinMind ⇒ ⛔ 而 FinMind 免費層實測回 HTTP 400
（`_finmind_probe.txt`：`"Your level is free"`，連**近期**都拿不到）。

⚠ 而我方**從來沒拿「券商／分點」去問過官方選單** ⇒ 那個「官方沒有」從來沒成立過。

## ⛔ 這一支不是「抓資料」，是回答四個問題

⚠ 這是**HTML 表單頁**，⛔ 不是 JSON API ⇒ 第二點那六步要換成等價的做法：

    ① 全部頂層鍵  → 改成：HTTP 狀態／content-type／位元組數／`<title>`
    ② notes/hints → 改成：頁面上的說明文字、表單旁的提示
    ③ params      → 改成：**表單有哪些欄位**（`<input>`／`<select>` 的 name）
                    ⭐ 那就是「它自己會送什麼」——⛔ 比猜參數可靠
    ④ total       → 改成：`<select>` 的選項（日期／市場範圍）
                    ⚠ ⛔ **選擇器會騙人**（`chtm` 寫 20080409、實際下限差兩年）
                      ⇒ 它只是線索，⛔ 不是涵蓋期間的結論

## ⛔ 要當場判掉的三件（它們決定這條路可不可行）

    ① 有沒有**驗證碼**（`<img>` 指向 captcha／verify 之類）
       ⇒ 有的話這條路不能自動化，⛔ 那是「技術上取不到」不是「官方沒有」
    ② 需不需要**session cookie**（第一發就給不給資料）
    ③ 它是**一次一檔**還是**一次一天全市場**
       ⇒ 決定回補成本是 2,850 發還是 2,850 × 2,000 發

⚠ 本支**只印證據，不下結論**。結論等看到輸出再寫。
"""
import io
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backfill as B                                           # noqa: E402

TPE = timezone(timedelta(hours=8))
BASE = "https://bsr.twse.com.tw/bshtm/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "data", "meta", "_bsr_probe.txt")


def get(url):
    raw, err = B.get(url, retries=2, timeout=45)
    if err:
        return None, f"⛔ {err}"
    return raw, f"{len(raw):,}B"


def decode(raw):
    """⚠ 這一族常見 Big5／MS950。⛔ 猜錯會讓整頁變亂碼而看起來像「沒有內容」。"""
    for enc in ("utf-8", "big5hkscs", "cp950", "big5"):
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace"), "utf-8(replace)"


def main():
    out = ["# bsr_probe.py 的輸出。⛔ 這是探針結果，不是資料。",
           f"# 產生時間：{datetime.now(TPE).isoformat(timespec='seconds')}（台北）",
           "# 端點來源：**使用者 2026-09-12 提供**，⛔ 非自行生成",
           ""]
    for path in ("", "bsMenu.aspx", "bsContent.aspx"):
        url = BASE + path
        out.append(f"\n{'=' * 62}\n── {url} ──")
        raw, note = get(url)
        out.append(f"  回應：{note}")
        if raw is None:
            continue
        txt, enc = decode(raw)
        out.append(f"  解碼：{enc}")
        t = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
        out.append(f"  <title>：{(t.group(1).strip() if t else '（沒有）')!r}")

        # ③ 表單有哪些欄位 ＝ 它自己會送什麼（⛔ 比猜參數可靠）
        forms = re.findall(r'<form[^>]*action=["\']([^"\']*)["\']', txt, re.I)
        out.append(f"  <form action>：{forms or '（沒有 form）'}")
        names = re.findall(r'<input[^>]*name=["\']([^"\']+)["\']', txt, re.I)
        out.append(f"  <input name>（{len(names)} 個）：{sorted(set(names))[:25]}")
        sels = re.findall(r'<select[^>]*name=["\']([^"\']+)["\']', txt, re.I)
        out.append(f"  <select name>：{sorted(set(sels))}")

        # ④ 選項 ＝ 涵蓋期間的**線索**，⛔ 不是結論（選擇器會騙人）
        for m in re.finditer(r'<select[^>]*name=["\']([^"\']+)["\'][^>]*>(.*?)</select>',
                             txt, re.S | re.I):
            opts = re.findall(r'<option[^>]*value=["\']?([^"\'>]*)["\']?[^>]*>([^<]*)',
                              m.group(2), re.I)
            vals = [v.strip() for v, _ in opts if v.strip()]
            out.append(f"    `{m.group(1)}` 有 {len(vals)} 個選項"
                       + (f"：最小 {min(vals)}｜最大 {max(vals)}" if vals else "")
                       + (f"｜全部 {vals}" if 0 < len(vals) <= 12 else ""))
        out.append("    ⚠ ⛔ **選擇器不是涵蓋期間的結論**"
                   "（`chtm` 的選擇器寫 20080409、實際下限差兩年）")

        # ⛔ ① 驗證碼：有的話這條路不能自動化
        cap = re.findall(r'<img[^>]*src=["\']([^"\']*)["\']', txt, re.I)
        hit = [c for c in cap if re.search(r"captcha|verify|valid|code|rand", c, re.I)]
        out.append(f"  <img>（{len(cap)} 個）｜⛔ 疑似驗證碼 {len(hit)} 個：{hit[:5]}")
        if hit:
            out.append("    ⛔⛔ **有驗證碼 ⇒ 這條路不能自動化**"
                       "　⚠ 而那是「技術上取不到」，⛔ 不是「官方沒有」")

        # ② 說明文字（等價於 notes）
        for kw in ("日報表", "查詢", "保留", "僅提供", "限", "天", "年"):
            for mm in re.finditer(r"[^<>]{0,60}" + kw + r"[^<>]{0,60}", txt):
                s = " ".join(mm.group(0).split())
                if len(s) > 12 and "function" not in s:
                    out.append(f"    說明：{s[:110]}")
                    break

    txt = "\n".join(out)
    print(txt)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(txt + "\n")
    print(f"\n[bsr_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
