#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_exright_check.py — 上櫃除權息的**外部判準**（櫃買 `/tpex_exright_daily`）。

## 為什麼今天才有這一支

上櫃除權息走 `otc_adj.py` ← **FinMind**（`otcexright/` 每一列的 `source` 都是 `finmind`）。
它當初的驗證是「抽 **60 檔上市**逐筆對官方，只有我方有 = 0 筆」。

⛔ **那個驗證套不到上櫃**：它證明的是「FinMind 沒漏掉**我們有的上市事件**」，
   而且方向只有一個（FinMind ⊇ 我方）。**「官方有而我方沒有」從來沒被驗過**，
   因為上櫃當時**沒有官方來源可比**。

2026-09-09 市場情報分析線找到了 `/tpex_exright_daily`（櫃買 openapi），
**第一次讓那個反方向可驗**。

## 這一支做什麼

1. 每天取官方當日的上櫃除權息，逐日累積到 `data/meta/otc_exright_official.csv`
   （⛔ 端點**只給當日** ⇒ 跟集保、跟開休市行事曆同一族：**不累積就永久失去**）
2. **`rl.check`：官方有、我方 `data/adj/` 沒有 ⇒ 0 筆。**
   ⭐ 這就是十一年來第一條能驗上櫃除權息「有沒有漏」的斷言。

## ⛔ 這一支**不寫** `data/universe/otcexright/`

那個目錄的**唯一寫入者是 `otc_adj.py`**。多一個寫入者＝後寫的贏、跟新舊無關，
`probe.yml` 檔頭記過同一個坑（兩支寫同一批檔，四個地方都顯示正常，內容卻退回舊版）。
⇒ **要不要改由官方端點供料，是「換維護者」的決定，不是順手加一行。**
  在那個決定做出來之前，這一支只當判準，把缺口每天報出來。

## 實測到的欄位陷阱（⛔ 照抄，不要「修正」）

- `Diviend`（不是 `Dividend`）、`CashDivdend`（少一個 i）——**官方就是這樣拼的**
- `Date` 是**民國無分隔**（`1150909`）
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import backfill as B
import runlog
import adjust as _adjust

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "otc_exright_official.csv")
ADJ_DIR = os.path.join(_ROOT, "adj")

URL = "https://www.tpex.org.tw/openapi/v1/tpex_exright_daily"
# ⭐⭐ 2026-09-14 從 7 欄加到 14 欄。⛔ 而理由不是「多存一點比較好」：
#
#   這一支原本只留 `pre_close`／`ref_price`／`kind` 六欄 ——
#   ⚠ 而官方這張表**一直有給** 21 欄，其中六欄正好是我方今天證明有用的：
#
#     LimitUp / LimitDown            上櫃的**官方漲跌停**
#        ⇒ F2 那 6 筆「未證實」全部是上櫃，卡的就是沒有這個
#        ⇒ `factor_limit_check` 上櫃那半只能靠推論，而那條推論對現增除權
#          會誤報（上市實測漲停側只中 95.39%）
#     DividendDeductedQuote          減除股利參考價（＝**不計現增稀釋**的口徑）
#        ⛔ 2026-09-14 訂正：不是「只扣現金股利」——它有除以**無償**配股率
#        ⇒ 上市那一欄（`ex_div_ref`）今天證實**同時是官方漲停的基準**
#     StockDividend / CashDividend   ⭐ **權值與息值分開**
#        ⇒ 上市只給合併值（notes 自己寫著它 = 前收 − 參考價，是導出值）
#          ⇒ 這是上市**沒有**而上櫃有的東西
#     SubscriptionPricePerShare / CashCapitalIncreaseShares  現增認購價與股數
#
#   ⇒ ⭐ 這與集保、行事曆同一族：**拿不到過去，但可以從今天起不再丟掉。**
#   ⚠ 而現在加幾乎不損失——累積檔到 2026-09-14 只有 13 列。
#   ⛔ 舊列那幾欄會是空的，⚠ 而「空」跟「官方沒給」要分得出來
#     ⇒ 靠 `asof`：2026-09-14 以前的列本來就不會有。
HEADER = ["date", "stock_id", "name", "pre_close", "ref_price", "kind",
          "limit_up", "limit_down", "ex_div_ref", "open_base",
          "stock_div", "cash_div", "sub_price", "sub_shares", "asof"]

# ⛔ 欄名逐字照抄官方（含拼字錯誤）。用 .get 找不到就留空，不自己「修正」拼字，
#   因為「修正」等於假設官方哪天會改，而那個假設沒有根據。
F_DATE = "Date"
F_CODE = "SecuritiesCompanyCode"
F_NAME = "CompanyName"
F_PRE = "ClosePriceBeforeExRightsDiviend"
F_REF = "ExRightsDiviendQuote"
F_KIND = "ExRightsDiviend"
# ⭐ 2026-09-14 探針（`_tpex_probe.txt` [12]）逐字抄回來的另外八個欄名
F_UP = "LimitUp"
F_DOWN = "LimitDown"
F_XDIV = "DividendDeductedQuote"
F_OPEN = "OpeningReferencePrice"
F_SDIV = "StockDividend"
F_CDIV = "CashDividend"
F_SUBP = "SubscriptionPricePerShare"
F_SUBS = "CashCapitalIncreaseShares"


def roc7(v):
    """民國 1150909 → 2026-09-09。⛔ 認不出回 None。"""
    s = str(v).strip()
    if not re.fullmatch(r"1[0-9]{6}", s):
        return None
    return f"{int(s[:3]) + 1911:04d}-{s[3:5]}-{s[5:7]}"


def to_row(r, dt, sid, today):
    """官方一列 → 我方一列（順序＝`HEADER`）。⛔ 抽成純函式才驗得到。

    ⚠ 「測了判準、沒測呼叫點」這一族在本專案已經兩次（CLAUDE.md 第七點③）
    ⇒ 呼叫點只剩一行 `rows.append(to_row(...))`，⭐ 而欄序由這裡與 `HEADER` 一起定。
    """
    def g(k):
        return str(r.get(k, "")).strip()
    out = [dt, sid, g(F_NAME), g(F_PRE), g(F_REF), g(F_KIND),
           g(F_UP), g(F_DOWN), g(F_XDIV), g(F_OPEN),
           g(F_SDIV), g(F_CDIV), g(F_SUBP), g(F_SUBS), today]
    # ⛔ 欄數與 `HEADER` 對不上就是有人只改了一邊（四點五那一族）
    assert len(out) == len(HEADER), f"欄數 {len(out)} != HEADER {len(HEADER)}"
    return out


def adj_events():
    """→ {(stock_id, date)}，我方已落地的還原事件。"""
    out = set()
    if not os.path.isdir(ADJ_DIR):
        return out
    for fn in os.listdir(ADJ_DIR):
        if not fn.endswith(".csv"):
            continue
        try:
            with io.open(os.path.join(ADJ_DIR, fn), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    d = (r.get("date") or "").strip()
                    if d:
                        out.add((fn[:-4], d))
        except OSError:
            pass
    return out


def classify(rows, have, today):          # ⚠ `today` ＝ **資料最後一天**
    """→ ({(代號,日期): 標記}, 缺口的鍵, 未來預告的鍵)。

    ⛔ 抽成函式有兩個理由，兩個都是付過代價的：

    ① **顯示與結論必須用同一段判準。**
       2026-09-10 19:21 那份 runlog 裡，明細每一列都印「✓ 已落地」，
       ⚠ 而同一份裡的 check 說「**4／4 筆沒落地**」。
       成因：`mark` 那一行寫 `(r[1], r[0]) not in miss`，
       而 `miss` 裝的是**列**（list）⇒ 拿 tuple 去 `in` 它**永遠是 True**。
       ⭐ 一個「明細說沒事、結論說有事」的報告，會讓人去懷疑結論。

    ② ⛔ 抽出來才測得到（selftest 自己抄一份就是第四點五）。

    ⚠ 官方會回**除權息日在未來**的預告列 ⇒ ⛔ 把預告當缺口會每天假紅；
      ⭐ 而它們確實還不該落地：那一天還沒到，前收盤價根本還不存在。

    ## ⛔⛔ 而「未來」要跟**我方資料的最後一天**比，不是跟 `today` 比

    2026-09-11 實際踩到：3141 晶宏的除息日**就是今天**，而我方日檔只到昨天
    （09-10，今天盤後才會有）。⇒ `k[1] > today` 判它**不是**未來事件
    ⇒ ⛔ 報成「沒落地 ⇒ **那幾檔今天的漲跌算出來是錯的**」
    ⇒ ⚠ 而我照那句話寫信給 K線分析線，**那封信是錯的**。

    ⭐ 正確的判準是 `adjust.py` 用的那一個：**事件日 > 我方資料最後一天 ⇒ 未來**。
    ⛔ 跟 `today` 比會在「事件日 == 今天、但盤還沒收」那一段製造誤導性紅燈，
    ⚠ 而那一段**每天都會出現一次**——那正是最容易被當成真事故的時候。
    """
    miss_keys = {(r[1], r[0]) for r in rows if (r[1], r[0]) not in have}
    future = {k for k in miss_keys if k[1] > today}
    miss_keys -= future
    marks = {}
    for r in rows:
        k = (r[1], r[0])
        marks[k] = ("⏳ 未來事件（預告，還不該落地）" if k in future
                    else "⛔ **data/adj 沒有**" if k in miss_keys
                    else "✓ 已落地")
    return marks, miss_keys, future


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="離線用：讀一個檔當回應")
    args = ap.parse_args()

    rl = runlog.Run("otc_exright_check")
    today = datetime.now(TPE).strftime("%Y-%m-%d")

    if args.json:
        raw, err = io.open(args.json, "rb").read(), None
    else:
        raw, err = B.get(URL, retries=3, timeout=60)
    if err or not raw:
        rl.info("端點", f"✗ 抓不到：{str(err)[:120]}")
        # ⛔ 抓不到**不是**「今天沒有除權息」。這一支唯一的失敗處置是報 ✗ 收手。
        rl.check("抓得到 tpex_exright_daily", False,
                 f"{str(err)[:80]}｜⛔ 抓不到不等於今天沒有事件")
        return rl.finish()

    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        rl.check("回應是 JSON", False, str(ex)[:80])
        return rl.finish()
    if not isinstance(d, list):
        rl.check("回應是 list", False, f"型別 {type(d).__name__}")
        return rl.finish()

    rows, bad = [], 0
    for r in d:
        if not isinstance(r, dict):
            bad += 1
            continue
        dt = roc7(r.get(F_DATE, ""))
        sid = str(r.get(F_CODE, "")).strip()
        if not dt or not sid:
            bad += 1
            continue
        rows.append(to_row(r, dt, sid, today))
    rl.info("本趟官方回的", f"{len(d)} 列｜認得出的 {len(rows)}"
            + (f"｜⚠ 認不出 {bad}" if bad else ""))
    # ⛔ 這一項是為了防「我把我取到的範圍寫成它的全部」——
    #   情報分析線 2026-09-09 20:50 就是這樣把 9 筆報成 2 筆的。
    rl.check("官方回的每一列都認得出日期與代號", bad == 0, f"認不出 {bad} 列")
    # ⭐⭐ 欄名不見了要**大聲講**，⛔ 不是靜靜留空——`.get()` 找不到就是空字串，
    #   而「官方這一列沒填」與「官方把欄名改掉了」在檔案裡長得一模一樣。
    if d and isinstance(d[0], dict):
        want = {F_UP, F_DOWN, F_XDIV, F_OPEN, F_SDIV, F_CDIV, F_SUBP, F_SUBS}
        miss = sorted(want - set(d[0]))
        rl.check("⭐ 官方那八個新欄名都還在（⛔ 改名了會靜靜變成整欄空白）",
                 not miss, f"⛔ 不見了：{miss}｜官方實際欄位：{sorted(d[0])}"
                           if miss else f"{len(want)} 個都在")
    if not rows:
        rl.info("今天", "官方回 0 筆上櫃除權息")
        return rl.finish()

    # ── 累積（端點只給當日）──────────────────────────────────────
    keep = {}
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("date") and r.get("stock_id"):
                    keep[(r["date"], r["stock_id"])] = [r.get(k, "")
                                                        for k in HEADER]
    n0 = len(keep)
    for r in rows:
        keep[(r[0], r[1])] = r
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for k in sorted(keep):
            w.writerow(keep[k])
    rl.info("累積檔", f"meta/otc_exright_official.csv｜{len(keep)} 筆"
            f"（本趟新增 {len(keep) - n0}）")
    rl.check("累積檔只增不減", len(keep) >= n0, f"{n0} → {len(keep)}")

    # ── ⭐ 十一年來第一條「官方有、我方無」的斷言 ─────────────────────
    have = adj_events()
    # ⛔⛔ 2026-09-10：這裡本來是 `(r[1], r[0]) not in miss`，
    #   而 `miss` 裝的是**列**（list），拿一個 tuple 去 `in` 它**永遠是 True**
    #   ⇒ 每一列都印「✓ 已落地」，⚠ **而下面那道 check 同時說「4／4 筆沒落地」**。
    #   ⭐ 同一份 runlog 裡兩句話互相矛盾，而矛盾的那一半（顯示）是騙人的那一半。
    #   （CLAUDE.md 第四點二：⛔ 顯示說落地了 ≠ 真的落地了。）
    #   ⇒ 用**鍵的集合**比，⛔ 不是拿鍵去比對一串列。
    # ⭐⭐ 「未來」要跟**我方資料的最後一天**比，⛔ 不是跟今天比（見 `classify` 的說明）。
    #   ⛔ 日檔列表不在這裡自己算——`adjust.trading_days()` 就是那一份（第四點五）。
    #   ⚠ 而它讀不到（目錄不在／checkout 問題）時**退回今天**，
    #     ⭐ 並在 runlog 裡講出來：⛔ 靜靜退回去會讓判準悄悄變回舊的那一個。
    # ⛔ 這一段**不在這裡自己算**——`adjust.last_data_day()` 就是那一份（四點五）。
    #   ⚠ 2026-09-14 付過代價：這支修好了、`otc_reduce_history` 沒跟上
    #     ⇒ 6129 普誠 2026-09-14 的減資被那一支報成「未歸因缺口」。
    last_data, _fellback = _adjust.last_data_day()
    if _fellback:
        rl.info("⛔ 讀不到日檔目錄，退回用今天當基準",
                "⚠ 這會讓「事件日就是今天」的那幾筆被報成缺口（誤導性紅燈）")
    else:
        rl.info("⚠ 「未來事件」的比較基準",
                f"我方資料最後一天 **{last_data}**（⛔ 不是今天 "
                f"{datetime.now(TPE).strftime('%Y-%m-%d')}）"
                "　⇒ 事件日晚於它的算預告，不算缺口")
    marks, miss_keys, future = classify(rows, have, last_data)
    for r in rows:
        rl.note(f"  {r[0]} {r[1]} {r[2]}｜前收 {r[3]}／參考價 {r[4]}"
                f"｜{r[5]}｜{marks[(r[1], r[0])]}")
    if future:
        rl.info("⏳ 除權息日在未來的預告列（⛔ 不算缺口）",
                f"{len(future)} 筆：{sorted(future)}"
                "　⭐ 好處是可以提前備妥因子；⛔ 但拿它當缺口會每天假紅")
    rl.check("官方有、我方 data/adj 沒有 ⇒ 0 筆（⚠ 不含未來的預告列）",
             not miss_keys,
             f"{len(miss_keys)}／{len(rows)} 筆沒落地："
             f"{sorted(miss_keys)[:10]}"
             "｜⛔ 沒落地那幾檔**今天的漲跌算出來是錯的**"
             if miss_keys else
             f"{len(rows) - len(future)} 筆全部落地"
             + (f"（⚠ 另有 {len(future)} 筆是未來預告）" if future else ""))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
