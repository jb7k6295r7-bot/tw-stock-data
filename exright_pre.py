#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exright_pre.py — 除權除息【預告表】（已公告、還沒到的除權息日）每日快照累積。

    python3 exright_pre.py          # 抓上市＋上櫃 → 併進 data/meta/exright_pre.csv → runlog

## 為什麼（情報 1127-1700 ④）

情報線看板「未來兩週除權息日」原本只能靠 FinMind；`data/universe/exright`、`otc_exright_*`
都是【已發生】的，缺「已公告、還沒到」那幾筆。

## 端點（2026-11-27 本機各一發實測）

    上市  GET https://www.twse.com.tw/rwd/zh/exRight/TWT48U?response=json
          → stat:"OK"、fields 13 欄、data 是 list（28 列，除權除息日期 115/11/26～115/12/30）
          ⚠ READ_CONTRACT：三個區間＋強制單一 date 六發回同樣的列 ⇒ 它【沒有歷史】，只有當下那份
    上櫃  GET https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost
          → list of dict（31 列，ExRrightsExDividendDate 1151118～1160105，含近幾天已過的）

⇒ ⛔ 只能從今天起往後累積；漏一天＝那天才公告、隔天就除權息的那幾筆可能永久沒記到。

## 寫法

- 鍵 (market, stock_id, ex_date)；每趟：本趟有的列【值取本趟】、first_seen 留最早、last_seen＝今天；
  本趟沒有的舊列原封不動（⛔ 不刪：過了除權息日官方就拿掉，那是正常的）。
- cash_div：官方寫「待公告實際收益分配金額」這種字（ETF 常見）⇒ 留空、原文進 note（⛔ 不寫 0）。
- 任一市場抓不到或形狀不對 ⇒ 另一市場照寫、rc＝1（⛔ 不寫 0 列假裝成功）。
- 0 列不算失敗（預告表真的可以是空的），但記進 runlog。
"""
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import backfill as B
import runlog
from twparse import roc_iso

TPE = timezone(timedelta(hours=8))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "meta", "exright_pre.csv")
TWSE_URL = "https://www.twse.com.tw/rwd/zh/exRight/TWT48U?response=json"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost"
HEADER = ["ex_date", "stock_id", "name", "market", "kind", "stock_div_ratio", "capinc_ratio",
          "capinc_price", "cash_div", "note", "first_seen", "last_seen"]
KEY = ("market", "stock_id", "ex_date")
TWSE_FIELDS = ["除權除息日期", "股票代號", "名稱", "除權息", "無償配股率", "現金增資配股率",
               "現金增資認購價", "現金股利"]
TPEX_FIELDS = ["ExRrightsExDividendDate", "SecuritiesCompanyCode", "CompanyName", "ExRrightsExDividend",
               "StockDividendRatio", "SubscriptionRatioToNewSharesIssued", "SubscriptionPricePerShare",
               "CashDividend"]
_TAG = re.compile(r"<[^>]*>")
_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _clean(v):
    return _TAG.sub("", str(v if v is not None else "")).replace("　", " ").strip()


def _num(v):
    """→ (數字字串, 備註)。認不出的數字 ⇒ ("", 原文)。"""
    t = _clean(v).replace(",", "")
    if _NUM.match(t):
        return t, ""
    return "", t


def _kind(v):
    return _clean(v).replace("除", "")          # 上櫃寫「除息」、上市寫「息」⇒ 統一成 權／息／權息


def _row(market, vals):
    """vals＝依 *_FIELDS 順序的 8 個值 → (dict, 錯誤或 None)。"""
    d, sid, name, kind, sdr, cir, cip, cash = vals
    iso = roc_iso(_clean(d))
    if not iso:
        return None, f"{market} {sid} 日期認不出：{d!r}"
    out = {"ex_date": iso, "stock_id": _clean(sid), "name": _clean(name), "market": market, "kind": _kind(kind)}
    notes = []
    for k, v in (("stock_div_ratio", sdr), ("capinc_ratio", cir), ("capinc_price", cip), ("cash_div", cash)):
        n, note = _num(v)
        out[k] = n
        if note:
            notes.append(f"{k}:{note}")
    out["note"] = "；".join(notes)
    if not out["stock_id"]:
        return None, f"{market} 代號空白：{vals!r}"
    return out, None


def parse_twse(raw):
    """→ (rows, bad, err)。err 非空＝整份不可用。"""
    try:
        d = json.loads(raw.decode("utf-8-sig", "replace"))
    except Exception as e:                       # noqa: BLE001
        return [], [], f"上市不是 JSON：{e}"
    if not isinstance(d, dict) or d.get("stat") != "OK":
        return [], [], f"上市 stat 不是 OK：{str(d)[:160]}"
    f = d.get("fields") or []
    miss = [x for x in TWSE_FIELDS if x not in f]
    if miss:
        return [], [], f"上市欄位變了，缺 {miss}；現有 {f}"
    idx = [f.index(x) for x in TWSE_FIELDS]
    rows, bad = [], []
    for r in d.get("data") or []:
        o, e = _row("twse", [r[i] if i < len(r) else "" for i in idx])
        (bad.append(e) if e else rows.append(o))
    return rows, bad, ""


def parse_tpex(raw):
    try:
        d = json.loads(raw.decode("utf-8-sig", "replace"))
    except Exception as e:                       # noqa: BLE001
        return [], [], f"上櫃不是 JSON：{e}"
    if not isinstance(d, list):
        return [], [], f"上櫃不是 list：{str(d)[:160]}"
    if d and any(x not in d[0] for x in TPEX_FIELDS):
        return [], [], f"上櫃欄位變了，缺 {[x for x in TPEX_FIELDS if x not in d[0]]}"
    rows, bad = [], []
    for r in d:
        o, e = _row("tpex", [r.get(x, "") for x in TPEX_FIELDS])
        (bad.append(e) if e else rows.append(o))
    return rows, bad, ""


def merge(old, new, today):
    """old／new：list of dict → 合併後 list（依 ex_date, market, stock_id 排）。"""
    by = {tuple(r[k] for k in KEY): dict(r) for r in old}
    for r in new:
        k = tuple(r[c] for c in KEY)
        prev = by.get(k)
        r = dict(r)
        r["first_seen"] = (prev or {}).get("first_seen") or today
        r["last_seen"] = today
        by[k] = r
    return sorted(by.values(), key=lambda r: (r["ex_date"], r["market"], r["stock_id"]))


def read(path):
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in HEADER})


def main():
    rl = runlog.Run("exright_pre")
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    got, errs, bads = [], [], []
    for name, url, parse in (("上市", TWSE_URL, parse_twse), ("上櫃", TPEX_URL, parse_tpex)):
        raw, e = B.get(url, retries=3, timeout=60)
        if e:
            errs.append(f"{name} 抓不到：{e}")
            continue
        rows, bad, err = parse(raw)
        if err:
            errs.append(err)
            continue
        got += rows
        bads += bad
        fut = sum(1 for r in rows if r["ex_date"] >= today)
        rl.info(name, f"{len(rows)} 列（今天起 {fut}）｜認不出 {len(bad)}")
    old = read(OUT)
    if got:
        write(OUT, merge(old, got, today))
    rl.info("累積", f"{len(read(OUT))} 列（本趟 {len(got)}）")
    rl.check("兩個市場都抓到且形狀對", not errs, "；".join(errs))
    rl.check("沒有認不出的列", not bads, "；".join(bads[:5]))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
