#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""停牌／處置／注意 的端點探針。**只讀不寫資料**，輸出一份照抄報告。

為什麼要先探再寫
────────────────
上市那三條 2026-09-07 已經用 WebFetch 驗過（見 sources/suspend_source.md），
**上櫃一條都還沒看到欄位名**——`tpex.org.tw/openapi/` 對 WebFetch 回 403。
在看到欄位名之前就寫解析式，就是「照猜的寫死」，這個專案被咬過一次
（興櫃逐月端點連 `fields` 鍵都沒有，只能靠 金額÷股數 反推）。

這支做兩件事：
  ① 上市三條在 Actions 的網路環境**再驗一次**（WebFetch 與這裡的 UA／出口不同）
  ② 上櫃候選路徑各打一發，**把回傳的鍵名與欄位名逐字抄下來**

★ 每一條都打**兩發不同區間**，比對指紋。
  這不是多此一舉：`TWTAWU` 吃 `date=` 但會**無視它**，兩個相隔六年的日期回一模一樣的東西，
  而且 stat 是 OK、不報錯。用 `date=` 回補歷史會得到 2,845 天全同一份資料，
  **看起來完全正常**。同樣的形狀 TPEx `bulletin/revivt` 也有過。
  **指紋一樣 = 這個參數是假的**，報告裡直接標 ✗。

用法
────
    python3 suspend_probe.py            # 全部探一遍
    python3 suspend_probe.py --only tpex

輸出：data/meta/_suspend_probe.txt（**不動 data/ 底下任何真資料**）
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
OUT = os.path.join("data", "meta", "_suspend_probe.txt")

# 兩個相隔很遠的區間。指紋一樣就代表參數被無視。
R1 = ("20150101", "20151231")
R2 = ("20200101", "20201231")

# (tag, 市場, url 樣板)。樣板裡的 {s}/{e} 會換成區間。
CANDIDATES = [
    # ── 上市：2026-09-07 已用 WebFetch 驗過，這裡是在 Actions 環境複驗
    ("twse-suspend", "twse",
     "https://www.twse.com.tw/rwd/zh/afterTrading/TWTAWU"
     "?startDate={s}&endDate={e}&response=json"),
    ("twse-punish", "twse",
     "https://www.twse.com.tw/rwd/zh/announcement/punish"
     "?startDate={s}&endDate={e}&response=json"),
    ("twse-notice", "twse",
     "https://www.twse.com.tw/rwd/zh/announcement/notice"
     "?startDate={s}&endDate={e}&response=json"),
    # ★ 反例：故意用錯的參數名，證明探針抓得到「參數被無視」
    ("twse-suspend-BAD-date", "twse",
     "https://www.twse.com.tw/rwd/zh/afterTrading/TWTAWU"
     "?date={s}&response=json"),

    # ── 上櫃：**全部是候選，一條都還沒驗過**。欄位名一律以這份報告抄回來的為準。
    ("tpex-openapi-disposal", "tpex",
     "https://www.tpex.org.tw/openapi/v1/tpex_disposal_information"),
    ("tpex-openapi-attention", "tpex",
     "https://www.tpex.org.tw/openapi/v1/tpex_attention_information"),
    ("tpex-openapi-suspend", "tpex",
     "https://www.tpex.org.tw/openapi/v1/tpex_suspension_information"),
    ("tpex-www-disposal", "tpex",
     "https://www.tpex.org.tw/www/zh-tw/bulletin/disposal"
     "?startDate={s}&endDate={e}&response=json"),
    ("tpex-www-attention", "tpex",
     "https://www.tpex.org.tw/www/zh-tw/bulletin/attention"
     "?startDate={s}&endDate={e}&response=json"),
    ("tpex-www-suspend", "tpex",
     "https://www.tpex.org.tw/www/zh-tw/bulletin/suspend"
     "?startDate={s}&endDate={e}&response=json"),
    ("tpex-www-halt", "tpex",
     "https://www.tpex.org.tw/www/zh-tw/bulletin/haltTrading"
     "?startDate={s}&endDate={e}&response=json"),
]

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def now_tpe():
    return datetime.now(TPE)


def get(url, timeout=40, body=None, ctype=None):
    """body 不是 None 就變成 POST。TPEx 的暫停交易那條只吃 POST。"""
    try:
        hdr = {"User-Agent": UA, "Accept": "application/json,text/plain,*/*"}
        if ctype:
            hdr["Content-Type"] = ctype
        req = urllib.request.Request(url, data=body, headers=hdr)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:                                   # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def echoed_range(raw):
    """回應自己講它給了哪一段。TPEx 新站的 `date` 鍵就是直接證據，不必猜。"""
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:                                        # noqa: BLE001
        return ""
    if isinstance(d, dict):
        # `stat`／`message` 也算——`bulletin/sprc` 的無資料訊息裡就寫著「資料日期:115/09/07」
        for k in ("date", "title", "stat", "message"):
            v = d.get(k)
            if v and not (k == "stat" and str(v).lower() in ("ok", "okay")):
                return str(v)
    return ""


def describe(raw):
    """→ (指紋, 說明行的 list)。**照抄鍵名與欄位名，一個字都不改。**"""
    if raw is None:
        return None, ["（沒有內容）"]
    lines = [f"bytes={len(raw)}"]
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:                                   # noqa: BLE001
        head = raw[:200].decode("utf-8", "replace").replace("\n", " ")
        lines.append(f"不是 JSON（{type(e).__name__}）")
        lines.append(f"前 200 位元組照抄：{head}")
        return f"raw:{len(raw)}", lines

    if isinstance(d, dict):
        lines.append(f"頂層鍵照抄：{list(d.keys())}")
        for k in ("stat", "title", "date"):
            if k in d:
                lines.append(f"  {k} = {d[k]!r}")
        # 欄位名可能在頂層 fields，也可能在 tables[i].fields
        fset = []
        if isinstance(d.get("fields"), list):
            fset.append(("頂層", d["fields"]))
        for i, t in enumerate(d.get("tables") or []):
            if isinstance(t, dict) and isinstance(t.get("fields"), list):
                fset.append((f"tables[{i}]", t["fields"]))
        for where, f in fset:
            lines.append(f"  欄位名（{where}）照抄：{f}")
        rows = d.get("data")
        if not isinstance(rows, list) and (d.get("tables") or []):
            rows = (d["tables"][0] or {}).get("data")
        if isinstance(rows, list):
            lines.append(f"  資料 {len(rows)} 列")
            if rows:
                lines.append(f"  首列照抄：{rows[0]}")
        fp = json.dumps([d.get("stat"), d.get("title"),
                         len(rows) if isinstance(rows, list) else None,
                         rows[0] if isinstance(rows, list) and rows else None],
                        ensure_ascii=False, sort_keys=True)
        return fp, lines

    if isinstance(d, list):
        lines.append(f"回傳是 list，{len(d)} 筆")
        if d and isinstance(d[0], dict):
            lines.append(f"  欄位名照抄：{list(d[0].keys())}")
            lines.append(f"  首筆照抄：{d[0]}")
        return json.dumps([len(d), d[0] if d else None],
                          ensure_ascii=False, sort_keys=True), lines

    lines.append(f"回傳型別 {type(d).__name__}，不是 dict 也不是 list")
    return f"other:{type(d).__name__}", lines


# ══════════════════════════════════════════════ 第二輪：參數名試打
#
# 第一輪已證明 TPEx 新站無視 `startDate`／`endDate`（回應的 `date` 鍵照實回報
# 它給的是「今天～今天」）。這一輪只換參數名，**判準用回應自己講的那段**，
# 不必比指紋——它自己會招。
#
# 候選不是憑空想的：`bulletin/disposal` 回來的列裡夾著官方自己產的連結
#     ./attention.html?code=3324&startDate=20260807&endDate=20260907&type=code
# 也就是**官方那一頁有帶 `type=`**。所以 `type` 很可能是必要參數，
# 少了它就退回預設區間。另外 TPEx 新站別處的日期慣用 `2026/09/04` 這種西元帶斜線。
_D1 = "2015/01/05"      # 西元帶斜線
_D1R = "104/01/05"      # 民國帶斜線
_D1N = "1040105"        # 民國不帶斜線
_D1P = "20150105"       # 西元不帶斜線

PARAM_SWEEP = []
for _page in ("disposal", "attention"):
    _b = f"https://www.tpex.org.tw/www/zh-tw/bulletin/{_page}"
    PARAM_SWEEP += [
        (f"{_page}-type=date", "tpex",
         _b + f"?startDate={_D1P}&endDate={_D1P}&type=date&response=json"),
        (f"{_page}-type=code", "tpex",
         _b + f"?startDate={_D1P}&endDate={_D1P}&type=code&response=json"),
        (f"{_page}-民國斜線", "tpex",
         _b + f"?startDate={_D1R}&endDate={_D1R}&response=json"),
        (f"{_page}-民國無斜線", "tpex",
         _b + f"?startDate={_D1N}&endDate={_D1N}&response=json"),
        (f"{_page}-西元斜線", "tpex",
         _b + f"?startDate={_D1}&endDate={_D1}&response=json"),
        (f"{_page}-date單一", "tpex", _b + f"?date={_D1}&response=json"),
        (f"{_page}-d", "tpex", _b + f"?d={_D1P}&response=json"),
        (f"{_page}-start_end", "tpex",
         _b + f"?start={_D1P}&end={_D1P}&response=json"),
        (f"{_page}-html帶參數", "tpex",
         _b + f".html?startDate={_D1P}&endDate={_D1P}&type=date&response=json"),
    ]

# ══════════════════════════════════════════════ 第四輪：上櫃停牌
#
# 頁名探勘（--set names）**失敗了**：`bulletin/disposal` 這個網址不管帶不帶
# `response=json` 都回 JSON（24,370 位元組），根本沒有 HTML 選單可抄；
# `attention.html` 與 `sitemap` 都是 404 外殼（10,892 位元組）。
#
# 改從官方自己的舊站網址回推。搜尋找到官方頁面
#     https://www.tpex.org.tw/web/stock/aftertrading/spendi/sprc.php?l=zh-tw
#     （標題：公布暫停/恢復交易有價證券）
# 所以那一頁的代號是 **spendi**，而且它歸在 **aftertrading** 底下，不是 bulletin。
# 這不是猜的第四個名字，是官方網址上寫的。
#
# 另外舊站已搬到 wwwov.tpex.org.tw（跟 MOPS 搬到 mopsov.twse.com.tw 同一套做法）。
# 舊站如果還活著，順便解掉「上櫃除權息只能靠 FinMind」那條——所以一起打。
#
# 日期一律帶斜線（第二輪已證明不帶斜線會被無視而且不報錯）。
_S, _E = "104/01/05", "104/12/31"
SUSPEND2 = [
    ("新站-afterTrading-spendi", "tpex",
     f"https://www.tpex.org.tw/www/zh-tw/afterTrading/spendi"
     f"?startDate={_S}&endDate={_E}&response=json"),
    ("新站-bulletin-spendi", "tpex",
     f"https://www.tpex.org.tw/www/zh-tw/bulletin/spendi"
     f"?startDate={_S}&endDate={_E}&response=json"),
    ("新站-afterTrading-sprc", "tpex",
     f"https://www.tpex.org.tw/www/zh-tw/afterTrading/sprc"
     f"?startDate={_S}&endDate={_E}&response=json"),
    ("舊站-spendi-sprc", "tpex",
     "https://wwwov.tpex.org.tw/web/stock/aftertrading/spendi/sprc_result.php"
     f"?l=zh-tw&d={_S}"),
    ("舊站-spendi-首頁", "tpex",
     "https://wwwov.tpex.org.tw/web/stock/aftertrading/spendi/sprc.php?l=zh-tw"),
    # ★ 順便：上櫃除權息的舊站端點。新站 bulletin/revivt 無視所有日期參數，
    #   目前只能靠 FinMind。舊站若還活著就能換回官方。
    ("舊站-除權息-revivt", "tpex",
     "https://wwwov.tpex.org.tw/web/stock/exright/revivt/revivt_result.php"
     f"?l=zh-tw&d={_S}"),
]


# ══════════════════════════════════════════════ 第五輪：上櫃停牌的 POST 參數
#
# 2026-09-07 用瀏覽器打開官方頁面 /zh-tw/announce/market/halt.html，
# 看它自己發了什麼請求，**不是猜的**：
#
#     POST https://www.tpex.org.tw/www/zh-tw/bulletin/sprc
#     回傳 fields：['有價證券類別','有價證券代號','有價證券名稱','暫停交易','恢復交易']
#     無資料時：stat = '資料日期:115/09/07，本日無暫停/恢復交易股票資訊'，totalCount = 0
#
# 前四輪全部 404 的原因就在這裡：**它是 POST，不是 GET**，而且掛在 bulletin 底下、
# 不是頁面網址上的 announce/market。**頁面路徑和 API 路徑對不起來**，
# 所以從頁名回推 API 名這條路本來就不會通。
#
# 還缺的只有一件：日期參數叫什麼、放 query 還是 body。下面把六種一次打完，
# 判準用它自己回報的「資料日期」——跟第二輪同一招。
_HS = "104/01/05"
_SPRC = "https://www.tpex.org.tw/www/zh-tw/bulletin/sprc"
_JSON = "application/json"
_FORM = "application/x-www-form-urlencoded"
HALT = [
    ("sprc-GET-startEnd", "GET", f"{_SPRC}?startDate={_HS}&endDate={_HS}&response=json",
     None, None),
    ("sprc-GET-date", "GET", f"{_SPRC}?date={_HS}&response=json", None, None),
    ("sprc-POST-json-date", "POST", _SPRC,
     json.dumps({"date": _HS}).encode(), _JSON),
    ("sprc-POST-json-startEnd", "POST", _SPRC,
     json.dumps({"startDate": _HS, "endDate": _HS}).encode(), _JSON),
    ("sprc-POST-form-date", "POST", _SPRC, f"date={_HS}".encode(), _FORM),
    ("sprc-POST-form-startEnd", "POST", _SPRC,
     f"startDate={_HS}&endDate={_HS}".encode(), _FORM),
    # 對照組：不帶任何日期。它會回「今天」，用來確認上面哪幾個真的有換到日期
    ("sprc-POST-空body-對照組", "POST", _SPRC, b"{}", _JSON),
]


def probe_halt(tag, method, url, body, ctype, want):
    out = [f"\n{'=' * 70}", f"== {tag}", f"   {method} {url}"]
    if body:
        out.append(f"   body: {body.decode('utf-8')}  ({ctype})")
    raw, err = get(url, body=body, ctype=ctype)
    if err:
        return out + [f"       ✗ {err}", "   判定：✗ 打不通"]
    _fp, lines = describe(raw)
    out += ["       " + x for x in lines]
    e = echoed_range(raw)
    if not e:
        return out + ["   判定：（回應沒有講它給了哪一天，無法判定）"]
    out.append(f"   ★ 回應自己回報的日期：{e!r}")
    hit = any(w in e.replace("/", "") or w in e for w in want)
    return out + ["   判定：" + ("✓ **參數生效**（它自己回報的日期就是我要的）"
                              if hit else
                              "✗ 這個寫法沒換到日期（回報的不是我要的那天）")]


# ══════════════════════════════════════════════ 第三輪：頁名探勘
# 上櫃停牌的頁名猜了兩個都 404。**不要再猜第三個**——去把官方頁面自己列的
# bulletin/* 連結抄回來。SPA 外殼可能沒有選單，那就照實說沒有，不要腦補。
NAME_HUNT = [
    ("頁名探勘-bulletin根", "tpex", "https://www.tpex.org.tw/www/zh-tw/bulletin/disposal"),
    ("頁名探勘-attention頁", "tpex", "https://www.tpex.org.tw/www/zh-tw/bulletin/attention.html"),
    ("頁名探勘-網站地圖", "tpex", "https://www.tpex.org.tw/www/zh-tw/sitemap"),
]


def probe_names(tag, url):
    out = [f"\n{'=' * 70}", f"== {tag}", f"   {url}"]
    raw, err = get(url)
    if err:
        out.append(f"       ✗ {err}")
        return out
    txt = raw.decode("utf-8", "replace")
    out.append(f"       bytes={len(raw)}")
    found = sorted(set(re.findall(r"bulletin/([A-Za-z][A-Za-z0-9_-]{2,30})", txt)))
    if found:
        out.append(f"       ★ 頁面自己出現過的 bulletin 頁名照抄：{found}")
    else:
        out.append("       （這一頁裡找不到任何 bulletin/xxx 字串——"
                   "多半是 SPA 外殼，選單是 JS 產的。**不要據此推論頁名不存在**）")
    return out


def probe_one(tag, market, tpl, sleep):
    out = [f"\n{'=' * 70}", f"== {tag}  [{market}]"]
    has_range = "{s}" in tpl
    urls = [tpl.format(s=R1[0], e=R1[1])] if not has_range else [
        tpl.format(s=R1[0], e=R1[1]), tpl.format(s=R2[0], e=R2[1])]
    fps, echoes, verdict = [], [], ""
    for i, u in enumerate(urls):
        out.append(f"   [{i + 1}] {u}")
        raw, err = get(u)
        if err:
            out.append(f"       ✗ {err}")
            fps.append(None)
        else:
            fp, lines = describe(raw)
            fps.append(fp)
            echoes.append(echoed_range(raw))
            out += ["       " + x for x in lines]
        if i + 1 < len(urls):
            time.sleep(sleep)

    # ★ 回應自己講了區間，就用它當判準——那是直接證據，比指紋更硬。
    want = [R1[0], R1[0][:4], str(int(R1[0][:4]) - 1911)]
    for e in echoes:
        if e and any(w in e.replace("/", "") or w in e for w in want):
            out.append(f"   ★ 回應自己回報的區間含我要的日期：{e!r}")
            return out + ["   判定：✓ **參數生效**（依回應自己回報的區間判定，不是靠指紋）"]
    if echoes and any(echoes):
        out.append(f"   ★ 回應自己回報的區間是 {echoes[0]!r}，**不是我要的 {R1[0]}**")
        return out + ["   判定：✗ **這個參數名是假的**（它自己招了，不必猜）"]

    if not has_range:
        verdict = "（這條沒有日期參數，指紋測試不適用）"
    elif fps[0] is None and fps[1] is None:
        verdict = "✗ 兩發都失敗"
    elif fps[0] == fps[1]:
        verdict = ("★✗ **兩個相隔五年的區間回一模一樣的東西 → 這個參數是假的**。"
                   "用它回補歷史會拿到整片重複資料，而且不報錯。")
    else:
        verdict = "✓ 指紋不同 → 參數真的有作用，可以拿來回補歷史"
    out.append(f"   判定：{verdict}")
    return out


def _finish(head, body):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(head + body) + "\n")
    print("\n".join(head + body))
    print(f"\n[probe] 寫出 {OUT}")


# ★★ 第六輪：**長期停止買賣**（2026-09-09 傍晚新增）
#
# 為什麼要有這一輪：`breakpoints_unexplained.csv` 的 227 個長洞分層之後，
# 剩下 6 筆「流動性足夠卻停了 27~203 個交易日」的（4414 如興、1785 光洋科、
# 5481 新華、6131 鈞泰、1225 福懋油、1591 駿吉-KY），**一筆都不在 `suspend.csv` 裡**。
#
# 去看 `suspend.csv` 本身：來源是 `TWTAWU`／`sprcHis`，兩個都是**暫停交易**，
# 10,034 列裡 **9,594 列是權證**，普通股只有 409 列
# ⇒ **我方沒有「長期停止買賣」的來源。**
#
# ⭐ 而線索早就在我們自己的紀錄裡：`parvalue_probe` 為了找面額變更時量過
#   `zh/listed/violations/stop.html`，當時的結論是——
#       「⛔ 不是這一族——它只收**財務業務異常**，明文排除組織變更、重整、減資。」
#   那句話對**面額變更**是正確的排除理由，但**對這一輪剛好是命中理由**：
#   長期停止買賣最典型的成因就是財務業務異常。
#   ⇒ **同一個發現，在另一個問題上是相反的答案。**
#
# ⛔ 這一輪只量、不寫資料，判準寫在前面：
#   ① 頁面／端點裡要**出現我方那 6 檔中的任何一檔**——出現才算對到路
#   ② 要有**起訖日期**，只有代號清單無法對上洞的區間
#   ③ ⛔ 「有回東西」不算：`stop.html` 是網頁，可能要 js
LONGHALT = [
    # 這一條的網址取自 parvalue_probe 的實測紀錄，⛔ 非自行生成。
    ("twse-violations-stop", "twse",
     "https://www.twse.com.tw/zh/listed/violations/stop.html"),
    # `/rwd/` 是證交所放資料端點的那一層；同名路徑先量一發看有沒有。
    # ⚠ 這一條**是我依站台慣例拼的**，標明出來——量得到才算，量不到就是量不到。
    ("twse-rwd-stop（⚠ 我拼的）", "twse",
     "https://www.twse.com.tw/rwd/zh/listed/violations/stop?response=json"),
]


def probe_longhalt(say, sleep):
    """→ None。只印，不判。"""
    TARGET = {"4414": "如興", "1785": "光洋科", "5481": "新華",
              "6131": "鈞泰", "1225": "福懋油", "1591": "駿吉-KY"}
    say("\n═══ 第六輪：長期停止買賣（我方目前完全沒有來源）═══")
    say("判準：① 出現我方那 6 檔中的任何一檔 ② 有起訖日期 ③ ⛔ 有回東西不算")
    say(f"靶子：{TARGET}")
    for tag, _mkt, url in LONGHALT:
        say(f"\n── {tag}\n   {url}")
        raw, err = get(url)
        if err:
            say(f"   ✗ {str(err)[:140]}")
            continue
        t = raw.decode("utf-8", "replace")
        han = len(re.findall("[一-龥]", t))
        say(f"   ✓ {len(raw):,} bytes｜中文 {han:,} 字"
            + ("　← ⚠ 太少，多半是 js 空殼" if han < 200 else ""))
        hit = [k for k in TARGET if k in t]
        say(f"   ① 靶子命中：{len(hit)}／6 {[(k, TARGET[k]) for k in hit] or '（一檔都沒有）'}")
        ds = sorted(set(re.findall(r"1[0-9]{2}/[0-9]{2}/[0-9]{2}", t)))
        ds += sorted(set(re.findall(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", t)))
        say(f"   ② 日期 {len(ds)} 個{('｜' + ds[0] + ' ~ ' + ds[-1]) if ds else ''}")
        for kw in ("停止買賣", "終止上市", "恢復買賣", "財務業務"):
            say(f"      「{kw}」{t.count(kw)} 次")
        n_tr = len(re.findall(r"<tr[ >]", t, re.I))
        n_js = len(re.findall(r"\.js[\"'?]", t))
        say(f"   ③ <tr> {n_tr} 個｜js {n_js} 支")
        time.sleep(sleep)
    say("\n⇒ ① 沒有命中 ⇒ 這條路不對，⛔ **不要**因為名字像就接上去。")
    say("⇒ ① 有命中但 ③ 是 js 空殼 ⇒ 記成「我方取不到」，"
        "跟櫃買那三頁同一種，⛔ 不是「證交所沒有」。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="round1",
                    choices=["round1", "params", "names", "suspend2", "halt",
                             "longhalt"],
                    help="round1 = 端點在不在｜params = 換參數名｜names = 抓官方頁名｜"
                         "suspend2 = 上櫃停牌（舊站，已證實 DNS 不存在）｜"
                         "halt = 上櫃停牌的 POST 參數（第五輪）")
    ap.add_argument("--only", default="", help="只探這個市場（twse／tpex）")
    ap.add_argument("--sleep", type=float, default=3.0)
    a = ap.parse_args()

    head = [f"# 停牌／處置／注意 端點探針 {now_tpe().isoformat(timespec='seconds')}",
            f"# 指紋比對用的兩個區間：{R1[0]}~{R1[1]} 與 {R2[0]}~{R2[1]}",
            "# 欄位名一律照抄，**不可照猜的寫死**"]
    sets = {"round1": CANDIDATES, "params": PARAM_SWEEP,
            "names": NAME_HUNT, "suspend2": SUSPEND2, "longhalt": LONGHALT}
    head.append(f"# 這一趟的選集：--set {a.set}")
    body = []
    if a.set == "longhalt":
        out = []
        probe_longhalt(out.append, a.sleep)
        _finish(head, out)
        return 0
    if a.set == "halt":
        want = ["104", "20150105", "1040105"]
        hbody = []
        for tag, method, url, hb, ctype in HALT:
            print(f"[probe] {tag} …", file=sys.stderr)
            hbody += probe_halt(tag, method, url, hb, ctype, want)
            time.sleep(a.sleep)
        _finish(head, hbody)
        return 0
    if a.set == "names":
        for tag, _m, url in NAME_HUNT:
            print(f"[probe] {tag} …", file=sys.stderr)
            body += probe_names(tag, url)
            time.sleep(a.sleep)
        _finish(head, body)
        return 0
    for tag, market, tpl in sets[a.set]:
        if a.only and market != a.only:
            continue
        print(f"[probe] {tag} …", file=sys.stderr)
        body += probe_one(tag, market, tpl, a.sleep)
        time.sleep(a.sleep)

    _finish(head, body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
