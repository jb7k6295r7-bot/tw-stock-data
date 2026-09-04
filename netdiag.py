#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""netdiag.py — 診斷 TWSE 端點在 Actions 上被擋的真正原因。

## 為什麼要有這支

2026-09-04：`backfill.py --inst` 回補 2015 年，**第一個請求就 HTTP 307**，
body 是 `<html><head><meta http-equiv...`。

`urllib` 是支援 307 的（Python 3.11 實測 `http_error_307` 存在），
所以會拋出 HTTPError 只有一種可能：**這個 307 沒有 `Location` 標頭**。
沒有 Location 就不是真的轉址，而是**擋機器人的中介頁**。

同一時間，同一條 URL 從開發環境用別的工具打**回得到正常 JSON**——
所以端點是好的，被擋的是 runner 的請求。

**問題是「哪個條件讓它被擋」有六種可能，猜錯一次就是一趟白跑。**
這支把六種一次測完，直接告訴你哪一種通。

## 紀律

- **不寫任何資料。** 純診斷。
- **測兩個日期**（一個 2015、一個近期），才分得出是「舊日期被擋」還是「IP 被擋」。
- **把 Location 標頭與 body 開頭照實印出來**，不要只印狀態碼——
  `backfill.py` 的註解已經記過：只印 `JSONDecodeError` 那句話不帶任何可以往下查的資訊。
"""

import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.request

TARGETS = [
    ("T86 2015", "https://www.twse.com.tw/rwd/zh/fund/T86"
                 "?date=20150105&selectType=ALL&response=json"),
    ("T86 近期", "https://www.twse.com.tw/rwd/zh/fund/T86"
                 "?date=20260903&selectType=ALL&response=json"),
    ("MI_INDEX 2015", "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
                      "?date=20150105&type=ALLBUT0999&response=json"),
]

BOT_UA = "Mozilla/5.0 (compatible; tw-stock-data-backfill/1.0; +https://github.com/)"
OLD_UA = "Mozilla/5.0 (compatible; tw-stock-data/1.0; +https://github.com/)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HOME = "https://www.twse.com.tw/zh/"

STRATEGIES = [
    ("A 現況（backfill UA ＋ Accept json）",
     {"User-Agent": BOT_UA, "Accept": "application/json,text/plain,*/*"}, False),
    ("B fetch.py UA，不帶 Accept",
     {"User-Agent": OLD_UA}, False),
    ("C 瀏覽器 UA ＋ Accept json",
     {"User-Agent": BROWSER_UA, "Accept": "application/json,text/plain,*/*"}, False),
    ("D 瀏覽器 UA ＋ Accept ＋ Referer",
     {"User-Agent": BROWSER_UA, "Accept": "application/json,text/plain,*/*",
      "Referer": HOME, "Accept-Language": "zh-TW,zh;q=0.9"}, False),
    ("E 先取首頁 cookie，再帶 cookie 打 API",
     {"User-Agent": BROWSER_UA, "Accept": "application/json,text/plain,*/*",
      "Referer": HOME, "Accept-Language": "zh-TW,zh;q=0.9"}, True),
    ("F 不帶任何自訂標頭（urllib 預設）", {}, False),
]


def _meta_refresh(body):
    """沒有 Location 的 307，轉址目標可能藏在 meta http-equiv=refresh 裡。"""
    m = re.search(r'http-equiv=["\']?refresh["\']?[^>]*content=["\'][^"\']*url=([^"\'>\s]+)',
                  body, re.I)
    return m.group(1) if m else None


def attempt(url, headers, use_cookie):
    """→ dict(ok, code, reason, location, meta, kind, note, rows)"""
    if use_cookie:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        try:
            opener.open(urllib.request.Request(HOME, headers=headers), timeout=30).read()
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "note": f"取首頁 cookie 就失敗：{type(e).__name__}: {e}"}
        names = sorted(c.name for c in cj)
    else:
        opener = urllib.request.build_opener()
        names = None

    try:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=45) as r:
            raw = r.read()
            final = r.geturl()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:                             # noqa: BLE001
            pass
        return {"ok": False, "code": e.code, "reason": e.reason,
                "location": e.headers.get("Location"),
                "meta": _meta_refresh(body),
                "note": f"HTTP {e.code} {e.reason}",
                "body": body[:200].replace("\n", " "),
                "cookies": names}
    except Exception as e:                            # noqa: BLE001
        return {"ok": False, "note": f"{type(e).__name__}: {e}", "cookies": names}

    txt = raw.decode("utf-8", "replace")
    try:
        d = json.loads(txt)
    except Exception:                                 # noqa: BLE001
        return {"ok": False, "note": f"200 但不是 JSON（{len(raw)}B）",
                "body": txt[:200].replace("\n", " "),
                "meta": _meta_refresh(txt), "final": final, "cookies": names}
    stat = d.get("stat") if isinstance(d, dict) else None
    n = 0
    if isinstance(d, dict):
        for k in ("data", "tables"):
            v = d.get(k)
            if isinstance(v, list):
                n = len(v[0].get("data", [])) if (k == "tables" and v and
                                                  isinstance(v[0], dict)) else len(v)
                break
    return {"ok": str(stat or "").lower() in ("ok", "success"),
            "note": f"JSON stat={stat}", "rows": n, "final": final, "cookies": names}


def main():
    print("netdiag — TWSE 端點診斷（只讀，不寫任何資料）\n")
    winners = {}
    for tag, url in TARGETS:
        print("=" * 70)
        print(f"■ {tag}")
        print(f"  {url}")
        for name, headers, cookie in STRATEGIES:
            r = attempt(url, headers, cookie)
            mark = "✅" if r.get("ok") else "❌"
            line = f"  {mark} {name}｜{r.get('note', '')}"
            if r.get("rows"):
                line += f"｜{r['rows']} 列"
            print(line)
            if r.get("cookies") is not None:
                print(f"        首頁 cookie：{r['cookies'] or '（一個都沒有）'}")
            if r.get("location"):
                print(f"        Location: {r['location']}")
            elif r.get("code") in (301, 302, 303, 307, 308):
                print("        Location: （沒有這個標頭 → 不是真的轉址，是中介頁）")
            if r.get("meta"):
                print(f"        meta refresh 指向：{r['meta']}")
            if r.get("body"):
                print(f"        body 開頭：{r['body']}")
            if r.get("ok") and tag not in winners:
                winners[tag] = name
        print()

    print("=" * 70)
    print("結論")
    for tag, _ in TARGETS:
        w = winners.get(tag)
        print(f"  {tag}：{'第一個通過的是 ' + w if w else '★ 六種全部失敗'}")
    if not winners:
        print("\n  六種全失敗 ＝ 不是標頭的問題，是這個 IP 被擋。")
        print("  這種情況不要加大重試，換時間或換出口才有意義。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
