#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""holiday_probe.py — 天然災害停止上班（＝台股全日休市）的來源探針。**只測、不寫資料。**

## 為什麼要有這一支

`db_status.py` 一直記著一句話：颱風臨時休市，我方**事後**看得出來
（那天全市場日檔沒有成交），缺的是**事前**——「明天開不開盤」。
交易日曆（`calendar_twse.csv`）是從已經發生的成交回推的，**它天生沒有前瞻**。

2026-09-09 使用者給了缺的那一半，並且把判準也講清楚了：

    https://www.dgpa.gov.tw/typh/daily/nds.html
    「當台北市宣布停止上班時，台股及期貨市場將依規定天然災害停止上班之處理全日休市」

⇒ 判準是**單一縣市**（台北市），不是「有沒有任何縣市放假」。
⛔ 這一點很重要：颱風天常常是南部放假、北部照常，那種日子**台股照開**。
  用「有縣市放假」當判準會把一堆正常交易日誤標成休市。

## 這一支要答什麼（⛔ 答不出來就不要接成 feed）

1. 這個頁面**在不執行 js 的前提下**拿不拿得到內容？
   （櫃買那三頁就是敗在這裡，所以先問這個。）
2. 頁面裡**找不找得到「臺北市／台北市」那一列**？
   ⚠ 官方用的是「臺」還是「台」不確定 ⇒ **兩個都找**，找到哪個記哪個。
3. 它平常（沒有颱風的日子）長什麼樣子？
   ⭐ **這一項最容易被跳過，而它決定了整個判讀**：
     如果沒有災害時它是一個空表，那「找不到台北市」＝正常；
     如果它永遠列出所有縣市、只是狀態欄寫「照常上班」，
     那「找不到台北市」＝**解析壞了**。
   ⇒ 兩者的處置完全相反，**沒答出來就不能寫判讀邏輯**。
4. 它有沒有**日期**？沒有日期的話，我方無從知道看到的是今天還是昨天的公告。

⛔ 四項沒有全部答出來之前，不要寫「颱風休市偵測」——
  一個會把正常交易日誤標成休市的偵測器，比沒有偵測器更貴。
"""
import io
import json
import os
import re
import sys
import traceback
# ⚠ 2026-09-09：第 8 節用了 `urllib.parse.urljoin` 卻沒 import，
#   而 selftest **沒抓到**——因為它的假頁面裡沒有 `<script src=…>`，
#   那條分支根本沒被走到。⇒ 假的比真的簡單，就等於沒測。已一併補假頁面。
import urllib.parse

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_holiday_probe.txt")

# ⛔ 網址由使用者 2026-09-09 提供，**不是自行生成**。
URL = "https://www.dgpa.gov.tw/typh/daily/nds.html"

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# holiday_probe.py 的輸出。這是探針結果，不是資料。\n")
            f.write("# 網址（使用者 2026-09-09 提供）：" + URL + "\n")
            f.write("# 判準：**台北市**停止上班 ⇒ 台股全日休市。"
                    "⛔ 不是「有任何縣市放假」。\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[holiday] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[holiday] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


def main():
    say("── 天然災害停止上班（台股休市）來源 探針 ──")
    say(f"網址（使用者提供，非自行生成）：{URL}")
    say("判準（使用者 2026-09-09 給的原文）：")
    say("  「當台北市宣布停止上班時，台股及期貨市場將依規定"
        "天然災害停止上班之處理全日休市」")
    say("⛔ 是**台北市**這一個縣市，不是「有沒有任何縣市放假」——"
        "南部放假、北部照常的日子台股照開。")

    raw, err = B.get(URL, retries=2, timeout=60)
    if err:
        say(f"\n✗ 抓不到：{str(err)[:200]}")
        say("⛔ 抓不到就是抓不到，**不要**因此推論「今天沒有停班」。")
        return _write(1)
    t = raw.decode("utf-8", "replace")
    say(f"\n[1] ✓ {len(raw):,} bytes")

    # ── 是不是 js 空殼
    han = len(re.findall("[一-龥]", t))
    say(f"[2] HTML 裡的中文字數 {han:,}"
        + ("  ← ⚠ 太少，多半是 js 空殼" if han < 200 else "  （夠多，內容應該在 HTML 裡）"))

    # ── 台北市（臺／台兩種寫法都找）
    say("[3] 台北市那一列")
    for w in ("臺北市", "台北市"):
        n = t.count(w)
        say(f"     「{w}」出現 {n} 次")
        for m in list(re.finditer(w, t))[:3]:
            seg = re.sub(r"<[^>]+>", " ", t[m.start() - 120:m.start() + 200])
            seg = re.sub(r"\s+", " ", seg).strip()
            say(f"       …{seg}…")

    # ── 全部縣市：是「只列放假的」還是「全部都列」
    say("[4] ⭐ 平常長什麼樣（這一項決定判讀方向）")
    CITIES = ["臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市",
              "基隆市", "新竹市", "嘉義市", "宜蘭縣", "花蓮縣", "臺東縣",
              "澎湖縣", "金門縣", "連江縣"]
    hit = [c for c in CITIES if c in t or c.replace("臺", "台") in t]
    say(f"     22 縣市裡出現了 {len(hit)}/{len(CITIES)} 個（取樣）：{hit}")
    say("     ⇒ 若**全部都列**：找不到台北市 ＝ 解析壞了（要吵）")
    say("     ⇒ 若**只列放假的**：找不到台北市 ＝ 今天照常上班（正常）")
    say("     ⛔ 這兩種的處置相反，**沒分辨出來就不要寫判讀邏輯**。")

    # ── 狀態字眼
    say("[5] 狀態字眼各出現幾次（⛔ 只計數，不判讀）")
    for w in ("停止上班", "照常上班", "停止上課", "正常上班", "尚未列入", "無"):
        say(f"     「{w}」{t.count(w)} 次")

    # ── 日期
    say("[6] 日期（沒有日期的話，我方無從知道看到的是哪一天的公告）")
    ds = sorted(set(re.findall(r"1[0-9]{2}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日", t)))
    ds += sorted(set(re.findall(r"20[0-9]{2}[-/][0-9]{1,2}[-/][0-9]{1,2}", t)))
    say(f"     抓到 {len(ds)} 個：{ds[:6] or '（沒有）'}")

    # ── 表格結構
    say("[7] 表格結構（給下一輪寫解析用，⛔ 這一輪不寫解析）")
    say(f"     <table> {len(re.findall(r'<table', t, re.I))} 個"
        f"｜<tr> {len(re.findall(r'<tr[ >]', t, re.I))} 個"
        f"｜<td> {len(re.findall(r'<td[ >]', t, re.I))} 個")
    js = sorted(set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', t)))
    say(f"     js {len(js)} 支：{[x.rsplit('/', 1)[-1] for x in js][:6]}")

    # ─────────────────────────────────────────────────────────────────
    say("\n[8] ★★ 兩條「上櫃休市日」的替代路（使用者 2026-09-09 15:40 提供）")
    say("  ⛔ 先講一件已經**用我方資料否證**的事，免得照著做會刪掉真的交易日：")
    say("     來源說「台股補班日不交易」——**這在 2016~2018 是錯的**。")
    say("     我方日曆裡有 8 個週六，每一天日檔都有 1,618 ~ 1,772 檔**真的成交**：")
    say("       2016-01-30／2016-06-04／2016-09-10／2017-02-18／")
    say("       2017-06-03／2017-09-30／2018-03-31／2018-12-22")
    say("     ⇒ 照「剔除補班日」做會**刪掉 8 個真的交易日**，"
        "而且刪掉之後那幾天的資料還在、只是日曆說它不存在——**最難查的那種錯**。")
    say("     ⛔ 所以辦公日曆表只能當**基底**，不可以拿它的補班規則直接套。")
    say("  ⚠ 上一版這裡的 `data.gov.tw/dataset/25980` **是我自己猜的 id**——"
        "實測「休市」0 次，")
    say("     ⇒ 那不是證交所開休市那份，是我編了一個編號。⛔ 已拿掉，"
        "改成從 TWSE 官網那頁自己找。")
    for label, url in (
            ("② 中華民國政府行政機關辦公日曆表（dataset 頁）",
             "https://data.gov.tw/dataset/14718"),
            ("③ TWSE 官網「市場開休市」頁",
             "https://www.twse.com.tw/zh/holidaySchedule/holidaySchedule"),
    ):
        say(f"\n  ── {label}")
        say(f"     {url}")
        r8, e8 = B.get(url, retries=1, timeout=60)
        if e8:
            say(f"     ✗ {str(e8)[:130]}")
            continue
        t8 = r8.decode("utf-8", "replace")
        han8 = len(re.findall("[一-龥]", t8))
        say(f"     ✓ {len(r8):,} bytes｜中文 {han8:,} 字")
        for kw in ("休市", "開休市", "補班", "補行上班", "行事曆", "csv", "json"):
            say(f"       「{kw}」{t8.lower().count(kw.lower())} 次")
        # ⛔ 只收頁面自己寫出來的檔案連結，不自己拼
        # ⚠ HTML 裡是 `&amp;`，直接拿去請求會多送一個字面上的 "amp;" 參數。
        t8u = t8.replace("&amp;", "&")
        dl = sorted(set(re.findall(
            r'https?://[^"\'<>\s]+\.(?:csv|json|xml)(?:\?[^"\'<>\s]*)?', t8u)))
        say(f"       頁面給的資料檔連結 {len(dl)} 個：{dl[:5] or '（沒有）'}")
        for u in dl[:3]:
            rr, ee = B.get(u, retries=1, timeout=60)
            if ee:
                say(f"         ✗ {u[:90]} → {str(ee)[:70]}")
                continue
            tt = rr.decode("utf-8", "replace")
            if tt[:1] == "\ufeff":
                tt = tt[1:]
            yrs = sorted(set(re.findall(r"\b(20[0-9]{2})[-/]?[01][0-9]", tt)))
            head = tt.splitlines()[0] if tt.strip() else ""
            say(f"         ✓ {u[:90]}｜{len(rr):,} bytes｜出現的年份 {yrs[:8]}")
            say(f"           表頭逐字：{head[:160]}")
            # ★ 這一項才是重點：辦公日曆表能不能分辨「補班的週六」。
            #   ⛔ 只有假日清單是不夠的——補班的週六台股照開（上面 8 天實測）。
            for kw in ("是否放假", "備註", "上班", "放假", "補行"):
                say(f"           「{kw}」{tt.count(kw)} 次")
    # ★ ③ 那頁沒有直接的資料檔連結 ⇒ 照 tpex_probe 第 8 節的做法去 js 裡找。
    say("\n  ── ④ 從 TWSE 那頁的 js 裡找它自己的端點（⛔ 不自己拼網址）")
    hs = "https://www.twse.com.tw/zh/holidaySchedule/holidaySchedule"
    r4, e4 = B.get(hs, retries=1, timeout=60)
    if e4:
        say(f"     ✗ 抓不到那頁：{str(e4)[:110]}")
    else:
        h4 = r4.decode("utf-8", "replace")
        js4 = sorted(set(re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', h4)))
        say(f"     那頁載入 {len(js4)} 支 js")
        found = []
        for j in js4[:8]:
            uj = urllib.parse.urljoin(hs, j)
            rj, ej = B.get(uj, retries=1, timeout=60)
            if ej:
                say(f"       ✗ {j.rsplit('/', 1)[-1]} → {str(ej)[:70]}")
                continue
            sj = rj.decode("utf-8", "replace")
            got = sorted(set(re.findall(
                r'["\'](/(?:rwd|exchangeReport|holidaySchedule)[A-Za-z0-9_/.\-]{2,70})["\']',
                sj)))
            if got:
                say(f"       ★ {j.rsplit('/', 1)[-1]}｜路徑 {len(got)} 個：{got[:6]}")
                found += got
            else:
                say(f"       ・{j.rsplit('/', 1)[-1]} {len(rj):,} bytes｜沒有路徑")
        for pth in sorted(set(found))[:4]:
            u4 = urllib.parse.urljoin(hs, pth)
            rr, ee = B.get(u4, retries=1, timeout=60)
            if ee:
                say(f"       ✗ {u4} → {str(ee)[:80]}")
                continue
            tt = rr.decode("utf-8", "replace")
            say(f"       ✓ {u4}｜{len(rr):,} bytes"
                f"｜「休市」{tt.count('休市')} 次｜日期 "
                f"{sorted(set(re.findall(r'1[0-9]{2}/[0-9]{2}/[0-9]{2}', tt)))[:4]}")
        if not found:
            say("     ⇒ js 裡沒有可辨識的路徑 ⇒ **這條也要能執行 js**，"
                "跟櫃買那三頁同一種。⛔ 不要再繞。")

    # ─────────────────────────────────────────────────────────────────
    say("\n[9] ★★★ 開休市行事曆的 rwd 端點（使用者 2026-09-09 16:5x 提供）")
    # ⛔ 網址由使用者提供。`/rwd/` 是證交所放資料端點的那一層
    #   （我方每天在用的 T86／MI_INDEX／TWTB8U 全在這一層），
    #   所以它跟第 ③ 節那個 `/zh/holidaySchedule/` 網頁**不是同一個東西**。
    # ★ 判準（⛔ 不是「有回東西」）：
    #   ① 要拿得到**未來**的日期——只有過去等於還是沒有前瞻
    #   ② 要分得出「休市」與「補行上班日開市」——我方 8 個週六是實測有成交的
    HS = "https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule"
    for label, u in (("使用者給的（html）", HS + "?response=html"),
                     ("同一支要 json", HS + "?response=json"),
                     ("帶年份 2026", HS + "?queryYear=2026&response=json"),
                     ("帶年份 民國 115", HS + "?queryYear=115&response=json")):
        r9, e9 = B.get(u, retries=1, timeout=60)
        if e9:
            say(f"     ✗ {label}：{str(e9)[:110]}")
            continue
        t9 = r9.decode("utf-8", "replace")
        dts = sorted(set(re.findall(r"1[0-9]{2}/[0-9]{2}/[0-9]{2}", t9)))
        dts += sorted(set(re.findall(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", t9)))
        say(f"     ✓ {label}：{len(r9):,} bytes"
            f"｜「休市」{t9.count('休市')} 次｜「開始交易」{t9.count('開始交易')} 次"
            f"｜日期 {len(dts)} 個 {dts[:3]}…{dts[-3:] if dts else ''}")
        for kw in ("補行上班", "補班", "星期六", "照常"):
            n = t9.count(kw)
            if n:
                say(f"       「{kw}」{n} 次")
        if t9.lstrip()[:1] in "{[":
            try:
                d9 = json.loads(t9)
                if isinstance(d9, dict):
                    say(f"       stat={d9.get('stat')!r}｜title={d9.get('title')!r}")
                    tb = (B._tables(d9) or [{}])[0]
                    say(f"       欄位：{[str(x) for x in (tb.get('fields') or [])]}")
                    dd = tb.get("data") or []
                    say(f"       列數 {len(dd)}｜首列 {dd[0] if dd else '（空）'}")
            except Exception as ex:                              # noqa: BLE001
                say(f"       （JSON 解析失敗 {type(ex).__name__}）")
    say("     ⇒ ① 有未來日期、② 分得出補行上班日 ⇒ 才可以接成前瞻日曆。")
    say("     ⛔ 只有國定假日清單不夠：我方 8 個週六是**實測有成交的補班日**。")

    say("  ⇒ 判準：拿到的東西要能回答「**某一個未來日期開不開盤**」才算數。")
    say("    ⛔ 只列國定假日不夠——**補班的週六台股照開**（上面 8 天是實測）。")

    say("\n── 下一步 ──")
    say("[2] 有內容、[3] 找得到台北市、[4] 分辨得出「全列」還是「只列放假的」、")
    say("[6] 有日期——**四項全過**才可以寫偵測器並接進交易日曆的前瞻那一半。")
    say("⛔ 任一項沒過就停在這裡：**會把正常交易日誤標成休市的偵測器，"
        "比沒有偵測器更貴。**")
    return _write(0)


if __name__ == "__main__":
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
