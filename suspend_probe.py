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


def get(url, timeout=40):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
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
        for k in ("date", "title"):
            if d.get(k):
                return str(d[k])
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="round1",
                    choices=["round1", "params", "names"],
                    help="round1 = 端點是否存在｜params = 換參數名試打｜names = 抓官方頁名")
    ap.add_argument("--only", default="", help="只探這個市場（twse／tpex）")
    ap.add_argument("--sleep", type=float, default=3.0)
    a = ap.parse_args()

    head = [f"# 停牌／處置／注意 端點探針 {now_tpe().isoformat(timespec='seconds')}",
            f"# 指紋比對用的兩個區間：{R1[0]}~{R1[1]} 與 {R2[0]}~{R2[1]}",
            "# 欄位名一律照抄，**不可照猜的寫死**"]
    sets = {"round1": CANDIDATES, "params": PARAM_SWEEP, "names": NAME_HUNT}
    head.append(f"# 這一趟的選集：--set {a.set}")
    body = []
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
