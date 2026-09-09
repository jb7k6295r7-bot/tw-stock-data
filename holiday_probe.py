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
import os
import re
import sys
import traceback

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
