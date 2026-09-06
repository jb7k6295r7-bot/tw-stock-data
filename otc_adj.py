#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_adj.py — 用 FinMind 補**上櫃**的除權息與減資事件。

## 為什麼是 FinMind（而不是官方）

TPEx 官方沒有歷史。2026-09-06 在 Actions 上實測：`bulletin/revivt` 帶
`date`／`year&month` 回的列與**不帶參數時完全相同**（＝參數被無視），
`startDate/endDate` 回「參數錯誤」；舊站 `.php` 四條與 `bulletin/*` 另外六個名字全 404。
詳見 `otc_adj_probe.py` 的檔頭。

## 憑什麼信 FinMind：拿**上市**那一半驗過

我們手上有 TWSE 官方的 11,729 筆除權息與 302 筆減資。抽 60 檔上市逐筆對：

| | 兩邊都有 | 相符 | 不符 | 只有我方有 |
|---|---|---|---|---|
| 除權息 | 555 | **555** | **0（0.00%）** | **0** |
| 減資 | 24 | **24** | **0（0.00%）** | **0** |

「只有我方有 = 0」是關鍵——代表 FinMind **沒有漏掉**任何我們有的事件。

### ★ 第一次驗的時候是 5.41% 不符，那是我挑錯欄位

**除權息的參考價欄是 `after_price`，不是 `reference_price`。**
兩者在「息」的紀錄裡相同，但在「權」（股票股利）的紀錄裡
`reference_price` **等於前收盤**：

    2867 2022-02-23  before 9.38 ｜ after **9.21** ｜ reference 9.38
    （TWSE 官方的除權息參考價是 9.21）

挑錯的後果是 f = 9.38/9.38 = **1.0**——**股票股利完全不還原**，而且不會報錯。
這種錯只有拿官方資料對才看得出來。**照抄下面的欄位對應，不要自己改。**

## 欄位對應（照抄）

| FinMind | 我方 |
|---|---|
| `TaiwanStockDividendResult.before_price` | `pre_close` |
| `TaiwanStockDividendResult.`**`after_price`** | `ref_price` |
| `.stock_or_cache_dividend`（權／息／權息）| `kind` |
| `TaiwanStockCapitalReductionReferencePrice.ClosingPriceonTheLastTradingDay` | `pre_close` |
| `.PostReductionReferencePrice` | `ref_price` |
| `.ReasonforCapitalReduction` | `reason` |

## ⚠ 一個已知的、會被 `adjust.py` 丟掉的情形

上市那邊有 9 筆「參考價高於前收盤」的合法事件（現金增資認股價高於市價，
`權值+息值` 為負）。`adjust.py` 靠那個**負的權值**來認定它合法。
**FinMind 沒有帶正負號的權值欄**，所以上櫃若有同類事件會被丟棄——
但**會逐筆印出來**，不是靜默。看到就是那一種，不是錯誤。

## 輸出

- `data/universe/otcexright/<日期>.csv`（表頭與 `exright` 相同 ＋ `source` 欄）
- `data/universe/otcreduce/<日期>.csv`（表頭與 `reduce` 相同 ＋ `source` 欄）

`source` 欄一律 `finmind`。`adjust.py` 用欄名定位，多一欄不影響它，
但**看檔案就知道這批不是官方來的**——契約裡也要寫明上櫃與上市不同來源。
"""

import argparse
import csv
import json
import os
import sys
import time

import backfill as B

FINMIND = "https://api.finmindtrade.com/api/v4/data"
DS_DIV = "TaiwanStockDividendResult"
DS_RED = "TaiwanStockCapitalReductionReferencePrice"

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
META = os.path.join(_ROOT, "meta", "stocks.csv")
UNI = os.path.join(_ROOT, "universe")
DONE = os.path.join(_ROOT, "meta", "_otcadj_done.csv")

EX_HEADER = ["date", "stock_id", "pre_close", "ref_price", "value",
             "kind", "open_base", "source"]
RD_HEADER = ["date", "stock_id", "pre_close", "ref_price", "reason",
             "open_base", "ex_ref_price", "source"]


def _f(v):
    try:
        x = float(str(v).replace(",", "").strip())
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None


def fm(ds, code, lo, hi, token=""):
    url = (f"{FINMIND}?dataset={ds}&data_id={code}"
           f"&start_date={lo}&end_date={hi}" + (f"&token={token}" if token else ""))
    raw, err = B.get(url, retries=2, timeout=45)
    if err:
        return None, err
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:                                     # noqa: BLE001
        return None, f"非 JSON（{len(raw)}B）"
    if not isinstance(d, dict):
        return None, "回的不是物件"
    msg = str(d.get("msg", ""))
    if msg.lower() not in ("success", ""):
        return None, f"msg={msg}"
    data = d.get("data")
    return (data if isinstance(data, list) else []), None


def otc_codes():
    out = []
    if not os.path.exists(META):
        return out
    with open(META, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("market") == "tpex" and r.get("kind") == "stock":
                out.append(r["stock_id"])
    return sorted(set(out))


def load_done():
    got = set()
    if os.path.exists(DONE):
        with open(DONE, encoding="utf-8") as fh:
            fh.readline()
            for ln in fh:
                q = ln.strip().split(",")
                if len(q) >= 2:
                    got.add((q[0], q[1]))
    return got


def save_done(done):
    os.makedirs(os.path.dirname(DONE), exist_ok=True)
    with open(DONE, "w", encoding="utf-8") as fh:
        fh.write("stock_id,dataset\n")
        for c, d in sorted(done):
            fh.write(f"{c},{d}\n")


def write_days(subdir, header, byday):
    """一天一檔。**同一天多檔股票要一起寫**，所以先收集完再分組。"""
    d = os.path.join(UNI, subdir)
    os.makedirs(d, exist_ok=True)
    n = 0
    for day, rows in sorted(byday.items()):
        with open(os.path.join(d, f"{day}.csv"), "w", encoding="utf-8") as fh:
            fh.write(",".join(header) + "\n")
            for r in sorted(rows, key=lambda x: x[1]):
                fh.write(",".join(str(x).replace(",", "；") for x in r) + "\n")
        n += len(rows)
    return len(byday), n


def main():
    ap = argparse.ArgumentParser(description="用 FinMind 補上櫃的除權息與減資")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--limit", type=int, default=0, help="只做前 N 檔（試跑）")
    ap.add_argument("--resume", action="store_true",
                    help="沿用 data/meta/_otcadj_done.csv，跳過做過的")
    a = ap.parse_args()
    B.SLEEP = a.sleep
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    hi = a.end or time.strftime("%Y-%m-%d")

    codes = otc_codes()
    if not codes:
        print("[otc] 找不到上櫃代號——先確認 data/meta/stocks.csv", file=sys.stderr)
        return 1
    if a.limit:
        codes = codes[:a.limit]
    done = load_done() if a.resume else set()
    print(f"[otc] 上櫃 {len(codes)} 檔｜區間 {a.start} ~ {hi}"
          f"｜token {'有' if token else '**無**（免費額度較低，被擋就會停下來續跑）'}")
    if done:
        print(f"[otc] 續跑：已完成 {len(done)} 個（代號,dataset）組合")

    ex, rd = {}, {}
    drop_up = []                 # 參考價高於前收盤、無法證明合法的
    limited = False
    stats = {DS_DIV: [0, 0], DS_RED: [0, 0]}     # [有事件檔數, 列數]
    for i, c in enumerate(codes, 1):
        for ds in (DS_DIV, DS_RED):
            if (c, ds) in done:
                continue
            data, err = fm(ds, c, a.start, hi, token)
            time.sleep(a.sleep)
            if err:
                low = err.lower()
                if "429" in err or "limit" in low or "too many" in low:
                    print(f"[otc] ★ 第 {i} 檔（{c}）被限流：{err[:80]}", file=sys.stderr)
                    limited = True
                    break
                print(f"[otc] ✗ {c} {ds}｜{err[:70]}", file=sys.stderr)
                continue
            done.add((c, ds))
            if not data:
                continue
            stats[ds][0] += 1
            for r in data:
                day = str(r.get("date", "")).strip()
                if not day or day < a.start:
                    continue
                if ds is DS_DIV:
                    # ★ ref 用 after_price。理由見檔頭——用 reference_price 會讓
                    #   「權」的因子變成 1.0，等於股票股利完全不還原。
                    pre, ref = _f(r.get("before_price")), _f(r.get("after_price"))
                    if not pre or not ref:
                        continue
                    if ref > pre * 1.0001:
                        drop_up.append((c, day, pre, ref))
                    ex.setdefault(day, []).append(
                        [day, c, f"{pre:g}", f"{ref:g}",
                         str(r.get("stock_and_cache_dividend", "")),
                         str(r.get("stock_or_cache_dividend", "")).strip(),
                         "", "finmind"])
                    stats[ds][1] += 1
                else:
                    pre = _f(r.get("ClosingPriceonTheLastTradingDay"))
                    ref = _f(r.get("PostReductionReferencePrice"))
                    if not pre or not ref:
                        continue
                    rd.setdefault(day, []).append(
                        [day, c, f"{pre:g}", f"{ref:g}",
                         str(r.get("ReasonforCapitalReduction", "")).strip(),
                         str(r.get("OpeningReferencePrice", "")),
                         str(r.get("ExrightReferencePrice", "")), "finmind"])
                    stats[ds][1] += 1
        if limited:
            break
        if i % 100 == 0:
            print(f"  [{i}/{len(codes)}] 除權息 {stats[DS_DIV][1]:,} 列、"
                  f"減資 {stats[DS_RED][1]:,} 列", flush=True)

    # ★ 就算被限流也要把已經拿到的寫出去，並存進度。
    #   半途而廢還不寫檔＝這一趟全白跑，而且下一趟還是從頭。
    d1, n1 = write_days("otcexright", EX_HEADER, ex)
    d2, n2 = write_days("otcreduce", RD_HEADER, rd)
    save_done(done)
    print(f"[otc] 除權息：{stats[DS_DIV][0]} 檔有事件、{n1:,} 列、{d1} 個日檔")
    print(f"[otc] 減資　：{stats[DS_RED][0]} 檔有事件、{n2:,} 列、{d2} 個日檔")
    if drop_up:
        # 不在這裡丟——丟不丟是 adjust.py 的事。這裡只是先讓人知道有幾筆。
        print(f"[otc] ⚠ {len(drop_up)} 筆參考價高於前收盤。"
              f"FinMind 沒有帶正負號的權值欄，**adjust.py 會把它們丟棄並逐筆印出**。"
              f"前 5 筆：{drop_up[:5]}")
    if limited:
        print(f"[otc] ★ 被限流中斷，已寫出拿到的部分並存進度到 {DONE}。")
        print(f"[otc]   等額度回復後加 --resume 續跑；或設 FINMIND_TOKEN 提高額度。")
        return 2
    print("[otc] 接下來跑 adjust.py 才會產生上櫃的還原因子。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
