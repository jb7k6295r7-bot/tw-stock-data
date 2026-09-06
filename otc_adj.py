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


# FinMind 撞到額度時的字樣。**要寬鬆比對**——它可能來自 HTTP 402/429，
# 也可能是 msg 裡的一句話；漏認的話會被當成一般錯誤，整批安靜跳過。
_RATE_HINTS = ("429", "402", "upper limit", "too many", "rate limit",
               "limit", "quota", "額度")


def _is_rate(err):
    low = str(err).lower()
    return any(h in low for h in _RATE_HINTS)


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
    """一天一檔，**與既有檔案合併**（鍵＝日期＋代號，新的蓋舊的）。

    ★★ 2026-09-06 踩到的資料流失：第一版是整檔覆寫。
      配上 `--resume` 就變成——這一趟只抓剩下的 97 檔，
      卻把 363 個日檔改寫成「只含這 97 檔的事件」，
      **前一趟同一天的其他個股全被蓋掉**。
      實測 `2015-06-29` 從幾十檔被壓成只剩 8923 一檔，
      而且**沒有任何錯誤訊息**：檔案在、格式對、內容少了九成。

      逐檔抓 ＋ 一天一檔 ＝ 每一趟都只有全體的一部分。
      所以寫入**必須是合併，不是覆寫**——這樣續跑與重跑才都是冪等的。
    """
    d = os.path.join(UNI, subdir)
    os.makedirs(d, exist_ok=True)
    n = 0
    for day, rows in sorted(byday.items()):
        path = os.path.join(d, f"{day}.csv")
        merged = {}
        if os.path.exists(path):                    # 先讀既有的
            with open(path, encoding="utf-8") as fh:
                old = fh.readline().rstrip("\n").split(",")
                for ln in fh:
                    q = ln.rstrip("\n").split(",")
                    if len(q) >= 2:
                        # 舊檔若欄位不同，照欄名對位補齊，缺的留空
                        merged[q[1]] = [dict(zip(old, q)).get(k, "") for k in header]
        for r in rows:
            merged[str(r[1])] = r                   # 新的蓋舊的
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(",".join(header) + "\n")
            for k in sorted(merged):
                fh.write(",".join(str(x).replace(",", "；")
                                  for x in merged[k]) + "\n")
        n += len(merged)
    return len(byday), n


def main():
    ap = argparse.ArgumentParser(description="用 FinMind 補上櫃的除權息與減資")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--limit", type=int, default=0, help="只做前 N 檔（試跑）")
    ap.add_argument("--resume", action="store_true",
                    help="沿用 data/meta/_otcadj_done.csv，跳過做過的")
    ap.add_argument("--fresh", action="store_true",
                    help="清掉進度檔，全部重抓。**寫入是合併的，重跑安全**")
    ap.add_argument("--limit-wait", type=float, default=900,
                    help="撞到額度上限時等幾秒再續（0＝不等、直接收工）")
    ap.add_argument("--max-waits", type=int, default=6,
                    help="最多等幾次。預設 6×15 分＝1.5 小時")
    ap.add_argument("--budget-min", type=float, default=0,
                    help="跑滿幾分鐘就收工並存進度（0＝不限）。留給 job timeout 的餘裕")
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
    if a.fresh and os.path.exists(DONE):
        os.remove(DONE)
        print(f"[otc] --fresh：已清掉進度檔，全部重抓")
    done = load_done() if (a.resume and not a.fresh) else set()
    print(f"[otc] 上櫃 {len(codes)} 檔｜區間 {a.start} ~ {hi}"
          f"｜token {'有' if token else '**無**（免費額度較低，被擋就會停下來續跑）'}")
    if done:
        print(f"[otc] 續跑：已完成 {len(done)} 個（代號,dataset）組合")

    t_start = time.time()
    ex, rd = {}, {}
    drop_up = []                 # 參考價高於前收盤、無法證明合法的
    limited = False
    stats = {DS_DIV: [0, 0], DS_RED: [0, 0]}     # [有事件檔數, 列數]
    for i, c in enumerate(codes, 1):
        for ds in (DS_DIV, DS_RED):
            if (c, ds) in done:
                continue
            # ★★ 撞到額度**不要直接收工**。FinMind 免費層是「每小時」上限，
            #   等一段時間就會回復；1,942 發本來就跨得過一個小時。
            #   直接收工的話每一趟只跑得到額度用完為止，而且要人一直手動重跑。
            #   等 → 續 → 再撞就再等，等滿次數才收工並存進度。
            waits = 0
            while True:
                data, err = fm(ds, c, a.start, hi, token)
                time.sleep(a.sleep)
                if not (err and _is_rate(err)):
                    break
                if a.limit_wait <= 0 or waits >= a.max_waits:
                    print(f"[otc] ★ 第 {i} 檔（{c}）額度用完，等過 {waits} 次仍未回復："
                          f"{err[:70]}", file=sys.stderr)
                    limited = True
                    break
                waits += 1
                print(f"[otc] 額度用完（第 {i}/{len(codes)} 檔），"
                      f"等 {a.limit_wait / 60:.0f} 分鐘後續跑（第 {waits}/{a.max_waits} 次）"
                      f"｜{err[:60]}", flush=True)
                time.sleep(a.limit_wait)
            if limited:
                break
            if err:
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
        # ★ 預算到了就收工。Actions 的 job 有硬性 timeout，被砍的話
        #   **這一趟抓到的全部消失、進度也沒存**——寧可自己先收。
        if a.budget_min and (time.time() - t_start) / 60 >= a.budget_min:
            print(f"[otc] 跑滿 {a.budget_min:.0f} 分鐘，先收工存進度（第 {i} 檔）")
            limited = True
            break
        if i % 100 == 0:
            print(f"  [{i}/{len(codes)}] 除權息 {stats[DS_DIV][1]:,} 列、"
                  f"減資 {stats[DS_RED][1]:,} 列", flush=True)

    # ★ 就算被限流也要把已經拿到的寫出去，並存進度。
    #   半途而廢還不寫檔＝這一趟全白跑，而且下一趟還是從頭。
    d1, n1 = write_days("otcexright", EX_HEADER, ex)
    d2, n2 = write_days("otcreduce", RD_HEADER, rd)
    save_done(done)
    # ★ 印的是**合併後檔案裡的總列數**，不是這一趟抓到的——
    #   續跑時那兩個數字差很多，只報後者會讓人以為資料只有這麼點。
    print(f"[otc] 除權息：本趟 {stats[DS_DIV][0]} 檔有事件；"
          f"合併後 {d1} 個日檔、共 {n1:,} 列")
    print(f"[otc] 減資　：本趟 {stats[DS_RED][0]} 檔有事件；"
          f"合併後 {d2} 個日檔、共 {n2:,} 列")
    if drop_up:
        # 不在這裡丟——丟不丟是 adjust.py 的事。這裡只是先讓人知道有幾筆。
        print(f"[otc] ⚠ {len(drop_up)} 筆參考價高於前收盤。"
              f"FinMind 沒有帶正負號的權值欄，**adjust.py 會把它們丟棄並逐筆印出**。"
              f"前 5 筆：{drop_up[:5]}")
    if limited:
        left = len(codes) * 2 - len(done)
        print(f"[otc] ★ 中斷收工。已寫出拿到的部分並存進度到 {DONE}。")
        print(f"[otc]   已完成 {len(done)}／{len(codes) * 2} 個組合，**還剩 {left} 個**。")
        print(f"[otc]   直接**再跑一次同一個 mode 即可**（--resume 會接著做，"
              f"寫入是合併的，重跑安全）。設 FINMIND_TOKEN 可提高額度。")
        return 2
    print("[otc] 接下來跑 adjust.py 才會產生上櫃的還原因子。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
