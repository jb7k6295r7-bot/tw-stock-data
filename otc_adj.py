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
    """→ **曾經**是上櫃的普通股代號。⛔ 不是「現在是上櫃」。

    ## ⛔ 2026-09-09 抓到的根因：這裡本來寫 `market == "tpex"`

    `stocks.csv` 的 `market` 是**當下**的市場。一檔股票**轉上市**之後，
    它的 `market` 就變成 `twse` ⇒ **它從此不在這份清單裡**，
    於是它**上櫃時期的除權息永遠不會被抓**。

    而 TWSE 的 `TWT49U`（`exright` feed 的來源）**只收上市**
    ⇒ 那段歷史**兩個 feed 都沒有**，而且不會有任何錯誤訊息。

    **實證（10 檔，每一檔的 `data/adj/` 最早事件都緊接在轉上市之後）**：

    | 代號 | 最後一次是 tpex | 第一次是 twse | `adj` 最早事件 |
    |---|---|---|---|
    | 6472 保瑞 | 2023-12-18 | 2023-12-19 | **2024-08-12** |
    | 4736 泰博 | 2023-12-21 | 2023-12-22 | **2024-09-09** |
    | 8476 台境 | 2023-10-30 | 2023-10-31 | **2024-07-09** |
    | 2233 宇隆 | 2019-09-16 | 2019-09-17 | **2020-08-21** |
    | 1597 直得 | 2020-12-22 | 2020-12-23 | **2021-06-07** |

    ⇒ 後果是**還原線上的假跌幅**：6472 保瑞 2021-09-07 從 303.00 掉到 226.00
      （**−25.41%**），而那是除權息，不是真跌。
    ⚠ `_otcadj_done.csv` 佐證：這 10 檔**一筆續跑紀錄都沒有**，從沒被跑過。

    ## ⇒ 改成「曾經是上櫃」

    判準來源是**日檔本身**（`data/universe/daily/*.csv` 的 `market` 欄），
    那是「那一天它在哪個市場」的第一手紀錄，⛔ 不是事後的狀態欄。

    ⚠ 要掃 2,800+ 個日檔（約十秒）。這一支跑在 `feeds.yml` 不是每日管線，
      成本可以接受；⛔ 而**用抽樣代替全掃會漏掉短期上櫃的個股**，不值得省。
    """
    out = set()
    # ① 現在就是上櫃的
    if os.path.exists(META):
        with open(META, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("market") == "tpex" and r.get("kind") == "stock":
                    out.add(r["stock_id"])
    now = len(out)
    # ② ⭐ 曾經是上櫃的（含已轉上市、已下市）
    kind = {}
    if os.path.exists(META):
        with open(META, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                kind[r["stock_id"]] = r.get("kind", "")
    daily = os.path.join(UNI, "daily")
    if os.path.isdir(daily):
        for fn in sorted(os.listdir(daily)):
            if not fn.endswith(".csv"):
                continue
            try:
                with open(os.path.join(daily, fn), encoding="utf-8") as fh:
                    for r in csv.DictReader(fh):
                        if (r.get("market") == "tpex"
                                and kind.get(r.get("stock_id", "")) == "stock"):
                            out.add(r["stock_id"])
            except OSError:
                pass
    print(f"[otc] 上櫃普通股清單：現在是上櫃 {now} 檔"
          f"｜**曾經是上櫃** {len(out)} 檔（多 {len(out) - now} 檔＝轉上市或已下市）")
    return sorted(out)


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 官方模式（2026-09-10，市場情報分析線 23:00 裁定「進第 2 步」）
#
#   ✅ 官方三支聯集為主：`exDailyQ`（除權息）＋ `revivt`（減資）
#      ＋ `TWT49U`（該檔轉上市之後——那一批本來就由 `exright` feed 落地）
#   ✅ `otcparvalue.py` 保留為**第四支來源**，面額變更由它負責
#   ✅ FinMind 退為**備援**，每一列標 `source`
#
# ## ⛔ 為什麼是 `--official` 而不是新開一支程式
#
# `data/universe/otcexright/`／`otcreduce/` 的**唯一寫入者**是這一支
# （CLAUDE.md 第五點）。⚠ 換供料是換維護者的決定，⛔ 不是多一個寫入者
#   ——兩支寫同一批檔＝後寫的贏、跟新舊無關，而且四個地方都顯示正常。
#
# ## ⭐ 雙向比對的結果（`otc_adj_compare.py`，換源的依據）
#
#     A 兩邊都有、factor 逐位相同   7,717 筆
#     B 兩邊都有、factor 不同      **0 筆**   ← 沒有分歧
#     C 官方有、我方沒有            2,998 筆（多數是上櫃 ETF）
#     D 我方有、官方沒有           **15 筆，全部是面額變更**
#
# ⚠ D 類**不必**去官方三支找——情報分析線把它講成一條可重用的規則：
#   **「一個來源的『沒有』，要先分成『它不該有』與『它漏了』。」**
#   面額變更不在那三支的定義裡 ⇒ ⭐ 它們沒有是**正確**的，去那裡找等於問錯對象。
# ══════════════════════════════════════════════════════════════════
OFF_EX = os.path.join(_ROOT, "meta", "otc_exright_history.csv")
OFF_RD = os.path.join(_ROOT, "meta", "otc_reduce_history.csv")


def _csv_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def snapshot_adj(path):
    """把 `data/adj/` 的現況寫成一張 CSV。→ 列數。

    ⚠ 情報分析線 2026-09-10 23:00 裁定裡指名的：**換源前留一份快照**。
    ⭐ 做成一張表而不是複製整棵目錄：快照的用途是**事後比對**，
      ⛔ 2,212 個檔進 git 既難 diff 也難查。
    """
    adj = os.path.join(_ROOT, "adj")
    rows = []
    if os.path.isdir(adj):
        for fn_ in sorted(os.listdir(adj)):
            if not fn_.endswith(".csv") or fn_.startswith("_"):
                continue
            for r in _csv_rows(os.path.join(adj, fn_)):
                if r.get("date"):
                    rows.append([fn_[:-4], r["date"], r.get("factor", ""),
                                 r.get("cum_factor", ""), r.get("kind", ""),
                                 r.get("event", "")])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["stock_id", "date", "factor", "cum_factor", "kind", "event"])
        w.writerows(sorted(rows))
    return len(rows)


def official_rows(codes=None):
    """→ (除權息 byday, 減資 byday, 說明)。⛔ 只讀本地判準檔，不連外。

    ⚠ 那兩個判準檔是 `otc_exright_history.py`／`otc_reduce_history.py` 寫的
      ⇒ ⛔ 這裡**不重抓**，避免同一份官方資料有兩條解析路徑（第四點五）。
    """
    ex, rd, skip = {}, {}, {"ex": 0, "rd": 0}
    for r in _csv_rows(OFF_EX):
        c, day = r.get("stock_id", ""), r.get("date", "")
        pre, ref = _f(r.get("pre_close")), _f(r.get("ref_price"))
        if not (c and day and pre and ref) or (codes and c not in codes):
            skip["ex"] += 1
            continue
        ex.setdefault(day, []).append(
            [day, c, f"{pre:g}", f"{ref:g}", r.get("value", ""),
             r.get("kind", ""), "", "exDailyQ"])
    for r in _csv_rows(OFF_RD):
        c, day = r.get("stock_id", ""), r.get("date", "")
        pre, ref = _f(r.get("last_close")), _f(r.get("ref_price"))
        if not (c and day and pre and ref) or (codes and c not in codes):
            skip["rd"] += 1
            continue
        rd.setdefault(day, []).append(
            [day, c, f"{pre:g}", f"{ref:g}", r.get("reason", ""), "", "",
             "revivt"])
    n_ex = sum(len(v) for v in ex.values())
    n_rd = sum(len(v) for v in rd.values())
    return ex, rd, (f"官方除權息 {n_ex:,} 筆／{len(ex)} 天"
                    f"｜官方減資 {n_rd:,} 筆／{len(rd)} 天"
                    f"｜⚠ 跳過（缺價格或不在母體）除權息 {skip['ex']}"
                    f"、減資 {skip['rd']}")


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
    """⛔⛔ **與磁碟上那一份合併**，絕不整份取代（2026-09-10 實跑抓到）。

    ## 這一支自己就吃過同一種虧，而且檔頭寫著

    `write_days()` 的註記：「第一版是整檔覆寫…前一趟同一天的其他個股全被蓋掉，
    **而且沒有任何錯誤訊息**」。⚠ 這裡是**同一個病的第二個位置**：

        不帶 `--resume` 跑 ⇒ `done` 是空集合
        ⇒ 這一支把 **1,996 列的續跑台帳整份洗成一列表頭**

    ⚠ 而它看起來完全正常：檔案在、格式對、程式回 0。
    下一趟帶 `--resume` 時「已完成 0 個」⇒ **從頭重跑 1,942 發**，
    ⛔ 而那正是免費額度撐不過的那種跑法 ⇒ 它會永遠跑不完，每趟都像有在跑。

    ⭐ 這也是 CLAUDE.md 第四點六（累積型的檔不可以整份覆蓋）的同一條道理，
    ⛔ 那一條原本只做在 `push_data.sh` 的 CSV 上。
    """
    os.makedirs(os.path.dirname(DONE), exist_ok=True)
    merged = load_done() | set(done)          # ← ⭐ 併集，⛔ 不是取代
    with open(DONE, "w", encoding="utf-8") as fh:
        fh.write("stock_id,dataset\n")
        for c, d in sorted(merged):
            fh.write(f"{c},{d}\n")
    return len(merged)


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
    n = kept_official = 0
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
            code = str(r[1])
            # ⭐⭐ 2026-09-10 換供料（情報分析線 23:00 裁定）：
            #   **官方三支為主、FinMind 退為備援**
            #   ⇒ ⛔ `finmind` 的列**不可以蓋掉**已經是官方來源的那一列。
            #   ⚠ 而反過來可以：官方的列蓋得掉 FinMind 的（那正是「換源」）。
            #   ⛔ 沒有這一條的話，兩支的執行**順序**就決定了資料內容
            #     ——而順序是排程的細節，不該決定資料。
            old_src = (merged.get(code) or [""] * len(header))[-1]
            if (str(r[-1]) == "finmind" and old_src
                    and old_src != "finmind"):
                kept_official += 1
                continue
            merged[code] = r                        # 新的蓋舊的
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(",".join(header) + "\n")
            for k in sorted(merged):
                fh.write(",".join(str(x).replace(",", "；")
                                  for x in merged[k]) + "\n")
        n += len(merged)
    if kept_official:
        print(f"[otc] ⭐ {kept_official} 列保留**官方**版本"
              f"（FinMind 沒有蓋過去）｜{subdir}", flush=True)
    return len(byday), n


def main():
    ap = argparse.ArgumentParser(description="用 FinMind 補上櫃的除權息與減資")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--limit", type=int, default=0, help="只做前 N 檔（試跑）")
    # ⭐ 2026-09-10：補**已知的單一缺口**用。
    #   `reduce_check` 抓到 6461 益得 2026-09-09 我方漏抓
    #   （官方 16.65 → 26.92，⇒ 沒有那個因子，序列上就是 **+54.7% 的假報酬**），
    #   ⛔ 而在這之前唯一的補法是重跑整個 FinMind 全掃（幾個小時、1,942 發）。
    #   ⚠ 一個「要補一檔就得跑幾小時」的補法，實際上等於不會被補。
    ap.add_argument("--codes", default="",
                    help="⭐ 只做這幾檔（逗號分隔）。補已知單一缺口用")
    # ⭐⭐ 換供料第 2 步：官方三支為主、FinMind 退備援（見上面那一節）
    ap.add_argument("--official", action="store_true",
                    help="⭐ 從官方判準檔寫入（⛔ 不連外、不跑 FinMind）")
    ap.add_argument("--snapshot", default="",
                    help="換源**之前**先把 data/adj 的現況寫成一份快照 CSV")
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

    # ⚠ 情報分析線裁定裡指名的一件事：**換源前留一份 `data/adj/` 快照**，
    #   至少留到下一輪稽核過了為止。
    # ⭐ 快照做成**一張 CSV**（代號＋日期＋因子），⛔ 不是複製 2,212 個檔：
    #   快照的用途是**事後比對**，一張表比一整棵目錄好比、也好 diff。
    if a.snapshot:
        n = snapshot_adj(a.snapshot)
        print(f"[otc] ⭐ 換源前快照：{a.snapshot}｜{n:,} 列")
        if not a.official and not a.codes:
            return 0

    if a.official:
        codes = set(otc_codes())
        ex, rd, note = official_rows(codes)
        print(f"[otc] ⭐ 官方模式（⛔ 不連外）：{note}")
        d1, n1 = write_days("otcexright", EX_HEADER, ex)
        d2, n2 = write_days("otcreduce", RD_HEADER, rd)
        print(f"[otc] 除權息 {d1} 天／累計 {n1:,} 列"
              f"｜減資 {d2} 天／累計 {n2:,} 列")
        print("[otc] ⚠ 接下來要跑 `adjust.py` 才會反映到 `data/adj/`")
        return 0

    B.SLEEP = a.sleep
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    hi = a.end or time.strftime("%Y-%m-%d")

    codes = otc_codes()
    if not codes:
        print("[otc] 找不到上櫃代號——先確認 data/meta/stocks.csv", file=sys.stderr)
        return 1
    if a.codes:
        want = [c.strip() for c in a.codes.split(",") if c.strip()]
        codes = [c for c in codes if c in want]
        # ⛔ 指名了卻一檔都不在母體裡 ⇒ **大聲失敗**。
        #   ⚠ 靜靜跑 0 檔會讓「補過了」與「代號打錯」長得一模一樣。
        if not codes:
            print(f"[otc] ⛔ --codes 指名 {want}，但一檔都不在上櫃母體裡"
                  "（打錯代號？或那幾檔不是上櫃？）", file=sys.stderr)
            return 1
        miss = [c for c in want if c not in codes]
        print(f"[otc] --codes：只做 {codes}"
              + (f"　⚠ 不在上櫃母體裡而跳過的：{miss}" if miss else ""))
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
