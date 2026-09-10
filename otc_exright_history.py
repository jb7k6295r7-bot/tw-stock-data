#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_exright_history.py — 上櫃除權息的**歷史官方來源**（櫃買公告區「除權除息計算結果表」）。

## 這一支推翻了我自己寫過三次的一句話

我對三個地方寫過「上櫃除權息的**歷史**官方來源：仍然沒有」，依據是
`tpex_exright_daily` 只給當日、`hist.tpex` 查完只有興櫃 2002~2006。

⛔ **那句話是錯的。** 市場情報分析線 2026-09-10 09:41 在櫃買公告區找到：

    POST https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ
    body: startDate=2015/01/01&endDate=2026/09/09&response=json
    ⭐ **一次請求回完十一年半，10,232 筆**（日期選擇器下限 20080102）

⚠ 教訓跟今晚別的幾次同一族：**「我查過的那幾條端點沒有」不等於「官方沒有」。**
他們是照著櫃買的**全站選單**（485 條）找的，我是照著我想得到的路徑猜的。

## ⛔ 三個陷阱（照抄，不要「改良」）

    ① **GET 的 startDate／endDate 會被忽略**，靜靜回「今天～明天」⇒ **必須 POST**
    ② **日期一定要帶斜線**：`2015/01/01` 或 `104/01/01` 都行；
       `20150101` 會被忽略，一樣**靜靜回今天**
    ③ 名稱欄右側補空白 ⇒ 要 trim

⭐ ①②都是「回應合法、內容是別的東西」——今晚第 N 個同形狀。
⇒ 所以本支**一定要驗回應涵蓋的日期範圍**，對不上就整批拒收。

## 這一支做什麼／不做什麼

1. 抓全期，寫 `data/meta/otc_exright_history.csv`（**判準檔**）
2. `rl.info`：官方有、我方 `data/universe/otcexright/` 沒有 ⇒ 報筆數與分年
3. ⛔ **不寫 `data/universe/otcexright/`**——那個目錄的唯一寫入者是 `otc_adj.py`。
   要不要把供料換成官方端點是「**換維護者**」的決定，不是順手加一行；
   而這一支的產出正好就是做那個決定所需要的證據（全期規模，不是抽 20 檔）。
"""
import argparse
import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "otc_exright_history.csv")
OURS = os.path.join(_ROOT, "universe", "otcexright")

URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ"
HEADER = ["date", "stock_id", "name", "pre_close", "ref_price", "kind", "asof"]


def _post(url, form, timeout=120):
    body = urllib.parse.urlencode(form, encoding="utf-8").encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"User-Agent": "Mozilla/5.0", "Referer": url,
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except Exception as ex:                                      # noqa: BLE001
        return b"", f"{type(ex).__name__}: {str(ex)[:120]}"


def _iso(v):
    """民國 `115/09/09` 或西元 `2026/09/09` → `2026-09-09`。⛔ 認不出回 None。"""
    s = str(v).strip().replace("-", "/")
    p = s.split("/")
    if len(p) != 3 or not all(x.strip().isdigit() for x in p):
        return None
    y, m, d = (int(x) for x in p)
    if y < 1000:
        y += 1911
    if not (1990 < y < 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def _pick(fields, *words):
    for i, f in enumerate(fields):
        if any(w in str(f) for w in words):
            return i
    return None


def parse(payload, want_from, want_to):
    """→ (rows, note)。⛔ 回應涵蓋的日期範圍對不上就整批拒收。"""
    tabs = payload.get("tables") if isinstance(payload, dict) else None
    if not tabs:
        tabs = [payload] if isinstance(payload, dict) and payload.get("data") else []
    if not tabs:
        return [], f"回應裡沒有表（鍵={list(payload)[:8] if isinstance(payload, dict) else type(payload).__name__}）"
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    data = t.get("data") or []
    if not data:
        return [], "回了 0 列 ⛔ 當失敗，不是「這十一年沒有除權息」"
    i_d = _pick(fields, "除權息日期", "日期")
    i_c = _pick(fields, "股票代號", "證券代號", "代號")
    i_n = _pick(fields, "股票名稱", "名稱")
    i_p = _pick(fields, "除權息前收盤價", "前收盤")
    i_r = _pick(fields, "除權息參考價", "參考價")
    i_k = _pick(fields, "權息值", "類別", "除權息")
    miss = [n for n, i in (("日期", i_d), ("代號", i_c), ("前收盤", i_p),
                           ("參考價", i_r)) if i is None]
    if miss:
        return [], f"欄位對不上，缺 {miss}：{fields}"
    rows, bad = [], 0
    for r in data:
        if not isinstance(r, list) or len(r) <= max(i_d, i_c, i_p, i_r):
            bad += 1
            continue
        dt = _iso(r[i_d])
        code = str(r[i_c]).strip()
        if not dt or not code:
            bad += 1
            continue
        rows.append([dt, code,
                     str(r[i_n]).strip() if i_n is not None else "",
                     str(r[i_p]).replace(",", "").strip(),
                     str(r[i_r]).replace(",", "").strip(),
                     str(r[i_k]).strip() if i_k is not None else ""])
    if not rows:
        return [], f"一列都認不出來（bad={bad}）：{fields}"
    ds = sorted(r[0] for r in rows)
    # ⛔⛔ 這一段是本支最重要的守門：GET、或日期不帶斜線，
    #   都會讓端點**靜靜回「今天～明天」** ⇒ 拿到 3 筆、看起來像成功。
    span = (ds[-1], ds[0])
    if ds[0] > want_from[:10] and ds[0] >= (datetime.now(TPE) - timedelta(days=7)
                                            ).strftime("%Y-%m-%d"):
        return [], (f"⛔ 回的只有最近的資料（{ds[0]} ~ {ds[-1]}，{len(rows)} 筆），"
                    f"我要的是 {want_from} 起"
                    "　⚠ 這就是『GET 或日期不帶斜線 ⇒ 靜靜回今天』那個陷阱")
    return rows, (f"{len(data)} 列｜認得出 {len(rows)}"
                  + (f"｜⚠ 認不出 {bad}" if bad else "")
                  + f"｜涵蓋 {ds[0]} ~ {ds[-1]}｜欄位 {fields}")


def ours_events():
    """→ {(代號, 日期)}，我方 `data/universe/otcexright/` 已經有的。"""
    out = set()
    if not os.path.isdir(OURS):
        return out
    for n in sorted(os.listdir(OURS)):
        if not n.endswith(".csv"):
            continue
        try:
            with io.open(os.path.join(OURS, n), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("stock_id") and r.get("date"):
                        out.add((r["stock_id"], r["date"]))
        except OSError:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2008/01/01")
    ap.add_argument("--end", default="")
    ap.add_argument("--json", help="離線用：讀一個檔當回應")
    a = ap.parse_args()

    rl = runlog.Run("otc_exright_history")
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    end = a.end or today.replace("-", "/")
    rl.info("端點", f"POST {URL}｜{a.start} ~ {end}"
                    "　⛔ 一定要 POST、日期一定要帶斜線（兩者都會靜靜回今天）")

    if a.json:
        raw, err = io.open(a.json, "rb").read(), None
    else:
        raw, err = _post(URL, {"startDate": a.start, "endDate": end,
                               "response": "json"})
    if err or not raw:
        rl.check("抓得到 exDailyQ", False, f"{str(err)[:100]}"
                 "｜⛔ 抓不到不等於沒有歷史（本機對 tpex 一律 403，要在 Actions 上跑）")
        return rl.finish()
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        head = raw[:80].decode("utf-8", "replace").replace("\n", " ")
        rl.check("回應是 JSON", False,
                 f"{str(ex)[:50]}｜開頭={head!r}　⚠ 若是 HTML 多半是被擋，不是端點壞了")
        return rl.finish()

    rows, note = parse(payload, a.start.replace("/", "-"), end.replace("/", "-"))
    rl.info("官方回的", note)
    rl.check("回應涵蓋我請求的整段期間（不是靜靜回今天）", bool(rows), note)
    if not rows:
        return rl.finish()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in sorted(rows):
            w.writerow(r + [today])
    rl.info("判準檔", f"data/meta/otc_exright_history.csv｜{len(rows):,} 筆")

    have = ours_events()
    miss = [r for r in rows if (r[1], r[0]) not in have]
    by_year = Counter(r[0][:4] for r in miss)
    etf = [r for r in miss if r[1].startswith("00")]
    rl.info("我方 data/universe/otcexright/", f"{len(have):,} 筆")
    rl.info("⭐ 官方有、我方沒有",
            f"**{len(miss):,} 筆／{len({r[1] for r in miss})} 檔**"
            f"（其中代號 00 開頭的 ETF／ETN {len(etf):,} 筆）")
    rl.info("  分年", "｜".join(f"{y} {n:,}" for y, n in sorted(by_year.items())))
    # ⛔ 不設 check：這是**歷史欠帳**，天天紅的檢查會被學會忽略。
    #   ⇒ 這一支的用途是給「要不要把供料換成官方端點」那個決定提供**全期規模**，
    #     不是每天叫。
    rl.info("⛔ 這一支不寫 data/universe/otcexright/",
            "那個目錄的唯一寫入者是 `otc_adj.py`（走 FinMind）。"
            "換供料是**換維護者**的決定，不是順手加一行。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
