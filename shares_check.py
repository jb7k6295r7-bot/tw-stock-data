#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""shares_check.py — `shares`（發行股數）的**第一條外部判準**（櫃買個股市值排行）。

## 為什麼今天才有這一支

`data/universe/daily/` 的 `shares` 欄一路是 **C 級**（只有自我一致）：
它從哪來、對不對，沒有任何獨立於它自己的東西驗過。
而 `shares` 是市值、周轉率、股本相關判讀的分母——錯了不會有人發現。

2026-09-10 00:20 市場情報分析線找到：

    https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyMarktVal?date=115/09/09&response=json
    欄位：排名、股票代號、股票名稱、發行股數、收盤價、市值(佰萬元)
    民國 96 年 1 月起；一次回全部（實測 889 檔），不必翻頁

他們比 2026-09-09：比對成功 868 檔 → 發行股數 868/868、收盤價 868/868，零例外。

## ⛔ 三個實測到的坑（照抄，不要「改良」）

```
⛔ WebFetch 對 tpex.org.tw 一律 403 ⇒ 這一支只能在 Actions 上跑
⛔ date=20260909（無斜線）或參數寫成 d= → **不報錯，靜靜回「今天」**
   ⇒ 所以本支一定要**驗回應裡的日期就是我請求的那一天**
⛔ 網址少了 /www/ 前綴 → 拿到「HTTP 200 的 404 頁面」
```

⚠ 第二條是今晚第 N 次遇到的同一族：**回應合法、內容是別的東西**。
沒有那道驗證的話，回補歷史時每一天都會拿到今天的數字，而且看起來完全正常。

## 這一支做什麼／不做什麼

1. 逐日累積到 `data/meta/shares_official_tpex.csv`
2. `rl.check`：官方 `發行股數` 對我方 `daily` 的 `shares` ⇒ **不符 0 筆**
3. `rl.check`：官方 `收盤價` 對我方 `close` ⇒ 不符 0 筆
4. `rl.info`：官方有、我方 `daily` 沒有 ⇒ 這就是漏列，**筆數報出來**
   （⛔ 不設 check：漏列是**已知的歷史欠帳**，天天紅的檢查會被學會忽略；
     規模由 `missing_rows.py` 用歷史最低值單調收斂。）

⛔ **這一支不寫 `data/meta/stocks.csv`，也不寫 `data/universe/daily/`。**
   單一寫入者原則——`otc_exright_check.py` 的檔頭記過同一個坑。

## ⚠ 涵蓋範圍：**只有上櫃**

情報分析線信裡寫明「上市沒有用這條路徑驗過」。
⇒ 接完之後 `shares` **只有上櫃那一半**有外部判準，上市那一半仍然是 C 級。
⛔ 不可以在任何文件裡寫成「shares 已有外部判準」。
"""
import argparse
import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import backfill as B
import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "shares_official_tpex.csv")
DAILY = os.path.join(_ROOT, "universe", "daily")

# ⛔ 斜線格式是必要的（無斜線會靜靜回「今天」），`/www/` 前綴也是。
URL = ("https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyMarktVal"
       "?date={roc}&response=json")
HEADER = ["date", "stock_id", "name", "shares", "close", "mktval_m", "asof"]


def roc_slash(iso):
    """2026-09-09 → 115/09/09。⛔ 這個格式是端點唯一吃的兩種之一。"""
    y, m, d = iso.split("-")
    return f"{int(y) - 1911}/{m}/{d}"


def _num(v):
    s = str(v).replace(",", "").strip()
    if s in ("", "-", "--", "null", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def pick(row, *names):
    """從一列 dict 取欄位；⛔ 找不到回 None，不猜別的欄。"""
    for n in names:
        if n in row:
            return row[n]
    return None


def parse(payload, want_iso):
    """→ (rows, note)。⛔ 回應裡的日期必須就是 `want_iso`，否則整批拒收。

    端點對錯誤的日期格式**不報錯、靜靜回今天** ⇒ 沒有這道驗證的話，
    回補歷史時每一天都會拿到今天的數字，而且看起來完全正常。
    """
    tabs = B._tables(payload)
    if not tabs:
        return [], "回應裡找不到表"
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    data = t.get("data") or []
    title = str(t.get("title") or payload.get("date") or "")
    want_roc = roc_slash(want_iso)
    # ⭐ 端點自己講的日期。兩種寫法都收（115/09/09 與 20260909），
    #   ⛔ 但**必須出現我請求的那一天**，否則拒收。
    stamp = f"{title} {payload.get('date', '')}"
    if want_roc not in stamp and want_iso.replace("-", "") not in stamp \
            and want_iso not in stamp:
        return [], (f"⛔ 回應沒有講出我請求的日期（要 {want_roc}）"
                    f"｜它說的是 {stamp[:80]!r}"
                    "　⚠ 這正是「日期格式寫錯就靜靜回今天」那個陷阱")
    if not data:
        return [], f"回了 0 列（{stamp[:60]!r}）⛔ 0 列當失敗，不是「那天沒有股票」"
    idx = {}
    for i, f in enumerate(fields):
        for key, words in (("code", ("股票代號", "證券代號", "代號")),
                           ("name", ("股票名稱", "證券名稱", "名稱")),
                           ("shares", ("發行股數",)),
                           ("close", ("收盤價",)),
                           ("mkt", ("市值",))):
            if key not in idx and any(w in f for w in words):
                idx[key] = i
    missing = [k for k in ("code", "shares", "close") if k not in idx]
    if missing:
        return [], f"欄位對不上，缺 {missing}：{fields}"
    rows = []
    for r in data:
        if not isinstance(r, list) or len(r) <= max(idx.values()):
            continue
        code = str(r[idx["code"]]).strip()
        if not code:
            continue
        rows.append([want_iso, code,
                     str(r[idx.get("name", idx["code"])]).strip(),
                     str(r[idx["shares"]]).replace(",", "").strip(),
                     str(r[idx["close"]]).replace(",", "").strip(),
                     str(r[idx["mkt"]]).replace(",", "").strip()
                     if "mkt" in idx else ""])
    return rows, f"{len(data)} 列｜認得出 {len(rows)}｜欄位 {fields}"


def ours(iso):
    """→ {代號: (shares, close)}，我方日檔裡的上櫃列。"""
    p = os.path.join(DAILY, iso + ".csv")
    out = {}
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("market") == "tpex":
                out[r["stock_id"]] = (r.get("shares", ""), r.get("close", ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="", help="要對的交易日（預設：我方日檔最新那天）")
    ap.add_argument("--json", help="離線用：讀一個檔當回應")
    a = ap.parse_args()

    rl = runlog.Run("shares_check")
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    day = a.date
    if not day:
        if not os.path.isdir(DAILY):
            rl.check("找得到 data/universe/daily", False, "目錄不在")
            return rl.finish()
        ds = sorted(n[:-4] for n in os.listdir(DAILY) if n.endswith(".csv"))
        if not ds:
            rl.check("data/universe/daily 有日檔", False, "目錄是空的")
            return rl.finish()
        day = ds[-1]
    rl.info("對帳日", f"{day}　⚠ 涵蓋範圍**只有上櫃**，上市那一半仍然沒有外部判準")

    if a.json:
        raw, err = io.open(a.json, "rb").read(), None
    else:
        raw, err = B.get(URL.format(roc=roc_slash(day)), retries=3, timeout=60)
    if err or not raw:
        rl.check("抓得到 dailyMarktVal", False,
                 f"{str(err)[:100]}｜⛔ 抓不到不等於那天沒有資料"
                 "（本機對 tpex 一律 403，這一支要在 Actions 上跑）")
        return rl.finish()
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        rl.check("回應是 JSON", False, str(ex)[:80])
        return rl.finish()

    rows, note = parse(payload, day)
    rl.info("官方回的", note)
    rl.check("回應講出的日期就是我請求的那一天，而且有列",
             bool(rows), note)
    if not rows:
        return rl.finish()

    keep = {}
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("date") and r.get("stock_id"):
                    keep[(r["date"], r["stock_id"])] = [r.get(k, "")
                                                        for k in HEADER]
    n0 = len(keep)
    for r in rows:
        keep[(r[0], r[1])] = r + [today]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for k in sorted(keep):
            w.writerow(keep[k])
    rl.info("累積檔", f"meta/shares_official_tpex.csv｜{len(keep)} 筆"
            f"（本趟新增 {len(keep) - n0}）")
    rl.check("累積檔只增不減", len(keep) >= n0, f"{n0} → {len(keep)}")

    mine = ours(day)
    if mine is None:
        rl.check(f"我方有 {day} 的日檔", False, "沒有那一天的日檔 ⇒ 對不了")
        return rl.finish()
    bad_s, bad_c, only_off = [], [], []
    for r in rows:
        code = r[1]
        if code not in mine:
            only_off.append(code)
            continue
        os_, oc = _num(r[3]), _num(r[4])
        ms, mc = _num(mine[code][0]), _num(mine[code][1])
        if os_ is not None and ms is not None and abs(os_ - ms) > 0.5:
            bad_s.append((code, r[3], mine[code][0]))
        if oc is not None and mc is not None and abs(oc - mc) > 0.005:
            bad_c.append((code, r[4], mine[code][1]))
    n_cmp = len(rows) - len(only_off)
    rl.info("逐檔對帳", f"官方 {len(rows)} 檔｜對得起來 {n_cmp} 檔"
            f"｜官方有我方無 {len(only_off)} 檔")
    rl.check("發行股數逐檔相符",
             not bad_s, f"{len(bad_s)}／{n_cmp} 不符：{bad_s[:6]}"
             if bad_s else f"{n_cmp}／{n_cmp} 全中")
    rl.check("收盤價逐檔相符",
             not bad_c, f"{len(bad_c)}／{n_cmp} 不符：{bad_c[:6]}"
             if bad_c else f"{n_cmp}／{n_cmp} 全中")
    # ⛔ 這一項**不設 check**：漏列是已知的歷史欠帳（見 missing_rows.py），
    #   天天紅的檢查會被學會忽略。規模由那一支用歷史最低值單調收斂。
    rl.info("⚠ 官方有、我方日檔沒有",
            f"**{len(only_off)} 檔**：{sorted(only_off)[:12]}"
            "　⇒ 這就是漏列，規模見 `_missing_rows.csv`"
            if only_off else "0 檔")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
