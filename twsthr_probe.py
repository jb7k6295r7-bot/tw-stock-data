#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""twsthr_probe.py — 集保大戶持股彙整站的探針。**只測、不寫資料。**

## 這一支要回答哪兩個缺口

`db_status.py` 的「沒有來源」還掛著兩條，兩條都跟集保有關：

1. **集保 17 級各級距對應多少股**——來源只給代碼 1~17，沒給級距文字，
   所以「400 張以上大戶」這種定義**現在寫不出來**。
2. **籌碼集中度的長期歷史**——官方 `getOD.ashx?id=1-5` 只回最新一週；
   查詢頁看到 51 個週別（20250912~20260904），**再往前就沒有了**。

網址由使用者提供（2026-09-08），非自行生成：

    https://norway.twsthr.info/StockHolders.aspx

## ⛔ 它不是官方，所以規矩不一樣

`tw-data-sources` 的來源優先序是「官方原文 → 官方端點 → 第三方」。
這是**第三方彙整站**，所以：

- **級距文字**：就算它寫得清清楚楚，那也只是**線索**。
  要寫進文件得回官方（集保或證交所）查證。**不可以拿它當出處。**
- **歷史序列**：可以用，但**必須跟官方交叉核對過**才算數。

## ★ 交叉核對怎麼做（本檔最重要的一段）

我方已經有官方的一份：`tdcc_probe.py` 2026-09-08 實測
`getOD.ashx?id=1-5` 回 **資料日期 20260904、4,051 檔、68,867 列、每檔 17 級**。

→ **拿同一週、同一檔股票，比對第三方站與官方的人數與股數。**
  對得上才可以往前用它的歷史；對不上就是它自己重算過或期別定義不同，
  那條路直接斷掉，不要「差不多就好」。

⚠ 沒有這一步的話，用它補歷史等於**把一個沒驗過的來源接進資料庫**，
  而且錯了不會報錯——跟本專案一路在防的靜默錯誤同一種。

## ⚠ 這是 ASP.NET 頁面

`.aspx` 的查詢多半要帶 `__VIEWSTATE`／`__EVENTVALIDATION`。
**參數名不猜**：把頁面的 form 欄位整組抓下來照抄，只改要換的那一格。
"""
import io
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_twsthr_probe.txt")

BASE = "https://norway.twsthr.info"
PAGES = [("大戶持股查詢頁", f"{BASE}/StockHolders.aspx"),
         ("站台首頁（看它自己怎麼介紹資料範圍）", f"{BASE}/")]

# 交叉核對用：官方那一份的實測值（tdcc_probe.py 2026-09-08 於 Actions 取得）
OFFICIAL = {"date": "20260904", "stocks": 4051, "rows": 68867, "levels": 17}
SAMPLE = "2330"

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def _post(url, form, referer=None):
    """POST 一發表單（`B.get` 只有 GET）。保留 `LIMITED|` 前綴以區分被擋與端點沒有。"""
    data = urllib.parse.urlencode(form).encode()
    h = {"User-Agent": B.UA,
         "Content-Type": "application/x-www-form-urlencoded",
         "Accept": "text/html,application/xhtml+xml,*/*"}
    if referer:
        h["Referer"] = referer
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, data=data, headers=h), timeout=60) as r:
            return r.read(), None
    except urllib.error.HTTPError as e:                          # noqa: BLE001
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:160]
        except Exception:                                        # noqa: BLE001
            pass
        loc = e.headers.get("Location") if e.headers else None
        if (e.code in (301, 302, 303, 307, 308) and not loc) or e.code == 429:
            return None, f"LIMITED|HTTP {e.code}（被擋／限流）| {body}"
        return None, f"HTTP {e.code} {e.reason} | {body}"
    except Exception as ex:                                      # noqa: BLE001
        return None, f"{type(ex).__name__}: {ex}"


def text_of(html):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"[ \t\xa0]+", " ", t)


def main():
    say("── 集保大戶持股彙整站 探針 ──")
    say(f"網址由使用者提供（2026-09-08），非自行生成：{BASE}/StockHolders.aspx")
    say("⛔ **這是第三方彙整站，不是官方。** 級距文字只能當線索，"
        "歷史序列要跟官方交叉核對過才算數。")

    got = {}
    for label, url in PAGES:
        say(f"\n── {label}")
        say(f"   {url}")
        raw, err = B.get(url, retries=2, timeout=60)
        if err:
            say(f"   ✗ {err[:180]}")
            if str(err).startswith("LIMITED"):
                say("   ⚠ 這是**被限流／擋下**，不是站台沒有東西——換個時間再測。")
            continue
        html = raw.decode("utf-8", "replace")
        got[url] = html
        say(f"   ✓ {len(raw):,} bytes")

        # [1] ★ 級距文字——缺口①，這一項是本檔的主要目的之一
        lv = re.findall(r"([0-9][0-9,]{0,12}\s*[-~至]\s*[0-9][0-9,]{0,12})", html)
        lv += re.findall(r"([0-9][0-9,]{0,12}\s*張(?:以上|以下))", html)
        lv = list(dict.fromkeys(lv))[:30]
        if lv:
            say(f"   [1] ★ 疑似級距文字（{len(lv)}）：{lv}")
            say("       ⚠ **這是線索不是出處**——要寫進文件得回官方查證。")
        else:
            say("   [1] 抓不到級距文字（可能在 JS 或另一頁）")

        # [2] ★ 歷史深度——缺口②
        ymd = sorted(set(re.findall(r"\b(20[0-2]\d[01]\d[0-3]\d)\b", html)))
        ym = sorted(set(re.findall(r"\b(20[0-2]\d)[/-]([01]?\d)[/-]([0-3]?\d)\b", html)))
        if ymd:
            say(f"   [2] ★ 八碼日期 {len(ymd)} 個：{ymd[:4]} … {ymd[-3:]}")
        if ym:
            f2 = [f"{a}-{int(b):02d}-{int(c):02d}" for a, b, c in ym]
            say(f"   [2] ★ 分隔式日期 {len(f2)} 個：{sorted(f2)[:4]} … {sorted(f2)[-3:]}")
        if not (ymd or ym):
            say("   [2] 頁面上抓不到日期——**不能據此說它沒有歷史**，"
                "可能要送出查詢才會出現")

        # [3] form 欄位：**照抄，不猜**（.aspx 多半要帶 __VIEWSTATE）
        form = {}
        for m in re.finditer(r"<input[^>]*>", html, re.I):
            tag = m.group(0)
            n = re.search(r"name=[\"']([^\"']+)", tag)
            v = re.search(r"value=[\"']([^\"']*)", tag)
            t = re.search(r"type=[\"']([^\"']+)", tag)
            if n and (not t or t.group(1).lower() not in ("submit", "button", "reset")):
                form[n.group(1)] = v.group(1) if v else ""
        sels = re.findall(r"<select[^>]*name=[\"']([^\"']+)", html, re.I)
        show = {k: (v[:40] + "…" if len(v) > 40 else v) for k, v in form.items()}
        say(f"   [3] form input（{len(form)}）：{show}")
        say(f"       select：{sels}")
        say(f"       __VIEWSTATE 有沒有：{'有' if '__VIEWSTATE' in form else '沒有'}")

        # [4] 下載／API
        dl = sorted(set(re.findall(
            r"[\"'(]([^\"'()\s]{4,120}\.(?:csv|json|txt|zip|xls|xlsx))", html, re.I)))
        say(f"   [4] 疑似下載連結：{dl[:10] if dl else '（沒有）'}")

        # [5] 站台自己怎麼講資料範圍與更新頻率
        t = text_of(html)
        for kw in ("更新", "資料來源", "每週", "集保", "大戶", "張以上"):
            hit = [x.strip() for x in re.findall(
                r"[^。\n]{0,60}" + kw + r"[^。\n]{0,60}", t)][:2]
            if hit:
                say(f"   [5] 「{kw}」附近：{hit}")

    # ── [6] ★★ 交叉核對：對不上就不要用 ──
    say("\n[6] ★★ 跟官方交叉核對（本檔最重要的一段）")
    say(f"    官方基準（tdcc_probe 2026-09-08 於 Actions 實測 getOD.ashx?id=1-5）：")
    say(f"      資料日期 {OFFICIAL['date']}｜{OFFICIAL['stocks']:,} 檔｜"
        f"{OFFICIAL['rows']:,} 列｜每檔 {OFFICIAL['levels']} 級")
    q = f"{BASE}/StockHolders.aspx"
    if q not in got:
        say("    （查詢頁沒抓到，這一步做不了——先解決上面的失敗）")
    else:
        form = {}
        for m in re.finditer(r"<input[^>]*>", got[q], re.I):
            tag = m.group(0)
            n = re.search(r"name=[\"']([^\"']+)", tag)
            v = re.search(r"value=[\"']([^\"']*)", tag)
            t2 = re.search(r"type=[\"']([^\"']+)", tag)
            if n and (not t2 or t2.group(1).lower() not in ("submit", "reset")):
                form[n.group(1)] = v.group(1) if v else ""
        code_k = next((k for k in form
                       if re.search(r"stock|code|txt|no|id$", k, re.I)
                       and not k.startswith("__")), None)
        if not code_k:
            say(f"    ⚠ 找不到「股票代號」那一格——**不要猜一個塞進去**。"
                f"欄位是：{list(form)}")
        else:
            say(f"    送出：{code_k}={SAMPLE}（其餘欄位照抄頁面原值）")
            form[code_k] = SAMPLE
            raw2, err2 = _post(q, form, referer=q)
            if err2:
                say(f"    ✗ {err2[:160]}")
            else:
                h2 = raw2.decode("utf-8", "replace")
                say(f"    ✓ 回 {len(raw2):,} bytes")
                nums = re.findall(r"\b(\d{1,3}(?:,\d{3}){2,})\b", h2)[:12]
                say(f"    回應裡的大數字（前 12）：{nums}")
                d2 = sorted(set(re.findall(r"\b(20[0-2]\d)[/-]?([01]\d)[/-]?([0-3]\d)\b", h2)))
                if d2:
                    ds = [f"{a}{b}{c}" for a, b, c in d2]
                    say(f"    回應裡的日期 {len(ds)} 個：{ds[:3]} … {ds[-3:]}")
                    say(f"    ★ 官方那一週 {OFFICIAL['date']} "
                        f"{'有' if OFFICIAL['date'] in ds else '**不在**'}回應裡")
                say("    ⚠ **人數／股數要逐格比對才算核對過**，"
                    "上面只是把回應的形狀印出來給人看。")

    say("\n── 下一步 ──")
    say("① 級距文字抓到了 → **回官方查證**，不可以拿第三方當出處")
    say("② 歷史比官方的 51 週深 → 先做 [6] 的逐格比對，**對得上才用**")
    say("③ 有下載連結 → 那條比爬頁面穩，優先")
    say("⛔ 三項都沒答出來之前，`db_status.py` 那兩條缺口維持原狀，不要先寫上去。")

    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write(
            "# twsthr_probe.py 的輸出。這是探針結果，不是資料。\n"
            f"# 網址（使用者提供）：{BASE}/StockHolders.aspx\n"
            "# ⛔ 第三方彙整站，不是官方——級距文字只是線索，"
            "歷史要跟官方交叉核對過才算數。\n\n" + "\n".join(LINES) + "\n")
        print(f"\n[twsthr] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[twsthr] 寫檔失敗：{ex}", file=sys.stderr)
    return 0 if got else 1


if __name__ == "__main__":
    # ⚠ 探針炸掉時，traceback 只留在 Actions log 裡——而 log 要翻好幾百行才找得到，
    #   （2026-09-09 實測：tail 900 行都還沒回到那一步）。
    #   ⇒ **把 traceback 寫進輸出檔**，它會跟著 commit 進 repo。
    #   這樣「哪一節炸的」下一趟就是既成事實，不必再去考古。
    #   ⛔ 覆蓋掉上一次成功的內容是**故意的**：這一份的語意是「這一趟看到什麼」，
    #     上一次的內容在 git 歷史裡找得到，而「看起來是完整結果、其實是上一趟的」
    #     比缺一份更貴。開頭那個 ✗ 也讓下一趟的重跑條件自動成立。
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                        # noqa: BLE001
        say("")
        say("✗ 這一趟在下面這裡炸掉了，以下是 traceback 原文（沒有整理）：")
        say(traceback.format_exc())
        _write(1)
        raise
