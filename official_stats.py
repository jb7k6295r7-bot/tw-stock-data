#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""official_stats.py — 把兩份**官方統計**抓回來存檔，當價格層的外部判準。

## 這兩支能驗什麼（⛔ 它們是判準，不是資料）

| 端點 | 內容 | 驗得到什麼 |
|---|---|---|
| `afterTrading/FMNPTK` | 逐檔**逐年**：成交股數／金額／筆數、最高最低、**收盤平均價** | ⭐ **一列驗一整年**：每天的收盤價都對、**沒缺日、沒多出非交易日** |
| `afterTrading/FMSRFK` | 逐檔**逐月**：最高最低、加權平均價、成交筆數／金額／股數、週轉率 | `amount`／`volume` 的月合計 |

⭐ **「收盤平均價」是日收盤價的簡單平均**，不是成交金額÷股數
（實證：2330 的 114 年 成交金額÷股數 ＝ 1,144.0，而收盤平均價 ＝ **1,163.06**，兩者不同）。
⇒ 所以它能一次驗掉四件事：收盤價、缺日、多日、用的是未還原價。

## 端點與參數（⛔ 全部是 Actions 上實測，不是猜的）

    https://www.twse.com.tw/rwd/zh/afterTrading/FMNPTK?date=YYYYMMDD&stockNo=NNNN&response=json
    https://www.twse.com.tw/rwd/zh/afterTrading/FMSRFK?date=YYYYMMDD&stockNo=NNNN&response=json

⚠ 區段名是 **`afterTrading/`**——我一開始不知道，逐個試四個區段才確定
（TWSE 的區段名沒有規律：`TWTAUU` 在 `reducation/`，前一輪就是猜錯區段才掃不到）。

⚠⚠ **`FMNPTK` 的回應沒有 `title`**（實測 `title=None`）
⇒ ⛔ **不能用 title 回音去驗參數有沒有生效**（那是 `TWT49U`／`TWTAWU` 的驗法）。
  改用它自己的 `年度` 欄——那是自我識別的，比 title 更硬。
  `FMSRFK` 有 title（`'114年2330 台積電  月成交資訊'`），兩支的驗法因此不同。

## 為什麼要續跑

逐檔一個請求，2,000+ 檔 ⇒ 一趟跑不完。用 `--limit` 分批、`--resume` 記進度，
跟 `otc_adj.py` 同一個形狀。⛔ 排在 `feeds.yml` 不是 `daily.yml`。
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import backfill as B
import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
META = os.path.join(_ROOT, "meta")
YEARLY = os.path.join(META, "official_yearly_close.csv")
MONTHLY = os.path.join(META, "official_monthly_amount.csv")
DONE = os.path.join(META, "_official_stats_done.csv")

BASE = "https://www.twse.com.tw/rwd/zh/afterTrading/{rep}?date={d}&stockNo={s}&response=json"

# ⛔ 欄名逐字照抄實測結果（`_parvalue_probe.txt` [T12]）。
#   FMNPTK 有**兩個都叫「日期」**的欄（最高價日、最低價日）⇒ 用位置取，不用名字。
Y_HEADER = ["stock_id", "roc_year", "volume", "amount", "transactions",
            "high", "high_date", "low", "low_date", "avg_close", "asof"]
M_HEADER = ["stock_id", "roc_year", "month", "high", "low", "avg_price",
            "transactions", "amount", "volume", "turnover", "asof"]


def _n(v):
    return str(v).replace(",", "").strip()


def _rows(raw):
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None, None, "不是 JSON"
    if str(d.get("stat")) != "OK":
        return None, None, f"stat={d.get('stat')!r}"
    tb = (B._tables(d) or [{}])[0]
    return (tb.get("data") or []), str(d.get("title") or ""), None


def fetch_one(sid, today):
    """→ (yearly_rows, monthly_rows, err)。⛔ 任何一支失敗就整檔失敗，不半套落地。"""
    raw, err = B.get(BASE.format(rep="FMNPTK", d=today, s=sid), retries=2, timeout=45)
    if err:
        return None, None, f"FMNPTK {str(err)[:60]}"
    data, _t, e = _rows(raw)
    if e:
        return None, None, f"FMNPTK {e}"
    ys = []
    for r in data:
        r = list(r) + [""] * 9
        # ⛔ 用位置取：這一支有兩個欄位都叫「日期」
        y = _n(r[0])
        if not re.fullmatch(r"\d{2,3}", y):
            continue
        ys.append([sid, y, _n(r[1]), _n(r[2]), _n(r[3]), _n(r[4]), _n(r[5]),
                   _n(r[6]), _n(r[7]), _n(r[8]), today])

    raw, err = B.get(BASE.format(rep="FMSRFK", d=today, s=sid), retries=2, timeout=45)
    if err:
        return None, None, f"FMSRFK {str(err)[:60]}"
    data, title, e = _rows(raw)
    if e:
        return None, None, f"FMSRFK {e}"
    # ⭐ FMSRFK **有** title，而且會回音代號 ⇒ 用它擋「回了別檔的資料」。
    #   ⛔ FMNPTK 沒有 title，所以上面那一支只能靠「年度」欄自我識別。
    if title and sid not in title:
        return None, None, f"FMSRFK title 沒有回音代號：{title!r}"
    ms = []
    for r in data:
        r = list(r) + [""] * 9
        y, mo = _n(r[0]), _n(r[1])
        if not (re.fullmatch(r"\d{2,3}", y) and re.fullmatch(r"\d{1,2}", mo)):
            continue
        ms.append([sid, y, mo, _n(r[2]), _n(r[3]), _n(r[4]), _n(r[5]),
                   _n(r[6]), _n(r[7]), _n(r[8]), today])
    return ys, ms, None


def _load(path, header):
    rows = {}
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows[tuple(r.get(k, "") for k in header[:3])] = \
                    [r.get(k, "") for k in header]
    return rows


def _save(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for k in sorted(rows):
            w.writerow(rows[k])


#: ⭐ 這兩支端點**只涵蓋上市**——2026-09-15 量出來的，⛔ 不是推的。
#  第一趟 `--limit 400` 的逐檔結果按市場拆開：
#
#      twse      成功 325 / 嘗試 343  = **94%**
#      tpex      成功   0 / 嘗試  44  = **0%**
#      emerging  成功   0 / 嘗試  13  = **0%**
#
#  ⇒ 跟 `TWTB8U` 那次一模一樣的形狀（同一發請求裡上市全中、上櫃全不中）
#    ⇒ **端點不涵蓋上櫃**，⛔ 不是「那幾檔剛好沒資料」。
#  ⚠ 而失敗訊息是 `stat='很抱歉，沒有符合條件的資料!'`
#    ——⛔ 它講不出「是這一檔沒有」還是「這個市場整個沒有」（第二點）
#    ⇒ ⭐ 分辨它的**不是訊息，是拿兩個市場的命中率對一次**。
COVERED = ("twse",)


def codes(covered=COVERED):
    """這個端點**答得出來**的普通股（含已下市）。→ sorted list[str]。

    ⛔ 本來是「`kind == stock` 全收」（2,493 檔）⇒ 而其中 1,335 檔
    （tpex 972 ＋ emerging 363）**這個端點根本不涵蓋**
    ⇒ ⚠ 續跑永遠到不了 100%，而每一趟都像有在跑（四點六③那個形狀）。

    ⭐ 回傳的是**母體**；被排掉的那些由 `excluded()` 講出來，
    ⛔ 不可以靜靜消失——「排掉了」與「沒有這種股票」不是同一件事。
    """
    out = []
    p = os.path.join(META, "stocks.csv")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("kind") == "stock" and r.get("market") in covered:
                    out.append(r["stock_id"])
    return sorted(set(out))


def excluded(covered=COVERED):
    """被排掉的市場各有幾檔。→ dict[market, n]。⛔ 排掉要講出來，不是消失。"""
    n = {}
    p = os.path.join(META, "stocks.csv")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                m = r.get("market")
                if r.get("kind") == "stock" and m not in covered:
                    n[m] = n.get(m, 0) + 1
    return n


def progress_lines(pool, done, todo, ex):
    """續跑那兩行怎麼寫。→ [(label, value)]。⭐ 抽出來是為了驗得到（第七點）。

    ⛔ **分母是 `pool`（這個端點涵蓋得到的），不是全部普通股。**
    ⚠ 用全部當分母的話，13% 這個數字會永遠爬不上去，
    而每一趟都像有在跑——那正是「永遠跑不完，每趟都像有在跑」那個形狀。
    """
    pct = len(done) * 100 // max(1, len(pool))
    return [
        ("續跑", f"母體 **{len(pool):,}** 檔（⭐ 只有上市——這個端點不涵蓋別的）"
                 f"｜已完成 {len(done):,}｜**{pct}%**｜本趟 {len(todo)}"),
        # ⛔ 排掉的要講出來：「排掉了」與「沒有這種股票」**不是同一件事**
        ("⚠ 這個端點答不出來的（⛔ 不是缺口，是涵蓋範圍）",
         "｜".join(f"{k} {v:,} 檔" for k, v in sorted(ex.items()))
         + "　⇒ ⭐ 實測命中率 twse 94%／tpex 0%／emerging 0%"
           "（⛔ 判準是**兩個市場的命中率**，不是那句「沒有符合條件的資料」"
           "——那句話講不出它是哪一種）"
         + "　⇒ ⚠ 上櫃的官方年度／月統計**仍然沒有來源**，這一條還開著"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=150)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    B.SLEEP = a.sleep

    rl = runlog.Run("official_stats")
    today = datetime.now(TPE).strftime("%Y%m%d")
    done = set()
    if os.path.exists(DONE) and not a.force:
        with io.open(DONE, encoding="utf-8") as f:
            f.readline()
            done = {ln.split(",")[0].strip() for ln in f if ln.strip()}
    pool = codes()
    todo = [c for c in pool if c not in done][:a.limit]
    ex = excluded()
    for label, value in progress_lines(pool, done, todo, ex):
        rl.info(label, value)
    if not todo:
        rl.info("狀態", "✓ 這個端點涵蓋得到的**全部跑完了**"
                        "（⛔ 不等於「全市場都有官方統計」）")

    Y, M = _load(YEARLY, Y_HEADER), _load(MONTHLY, M_HEADER)
    n0y, n0m = len(Y), len(M)
    ok = []
    fail = []
    for i, sid in enumerate(todo, 1):
        ys, ms, err = fetch_one(sid, today)
        if err:
            fail.append((sid, err))
            print(f"  [{i}/{len(todo)}] {sid} ✗ {err}", flush=True)
            continue
        for r in ys:
            Y[tuple(r[:3])] = r
        for r in ms:
            M[tuple(r[:3])] = r
        ok.append(sid)
        print(f"  [{i}/{len(todo)}] {sid} ✓ 年 {len(ys)}／月 {len(ms)}", flush=True)
        if a.sleep:
            time.sleep(a.sleep)

    # ⛔ 一筆都沒抓到、而且檔案本來就不存在 ⇒ **不要建立空檔**。
    #   2026-09-09 本機 smoke test（403 全失敗）就留下兩個只有表頭、零列的殘骸——
    #   **一個存在但空的判準檔，讀起來像是「有這份判準」**，
    #   而那正是今晚一路在抓的形狀（孤兒檔、恆真的 0 筆、留著不標的停更檔）。
    #   ⇒ 有舊內容就照常寫回（不能因為本趟失敗就讓舊的消失）；
    #     完全沒有內容就不落地。
    if Y or os.path.exists(YEARLY):
        _save(YEARLY, Y_HEADER, Y)
    if M or os.path.exists(MONTHLY):
        _save(MONTHLY, M_HEADER, M)
    if not Y and not M:
        rl.info("處置", "⛔ 一筆都沒抓到且檔案不存在 ⇒ **不建立空檔**"
                        "（空的判準檔讀起來像是有這份判準）")
    if ok:
        new = not os.path.exists(DONE)
        with io.open(DONE, "a", encoding="utf-8") as f:
            if new:
                f.write("stock_id,asof\n")
            for s in ok:
                f.write(f"{s},{today}\n")

    rl.info("年度表", f"{YEARLY.split('data/')[-1]}｜{len(Y):,} 列（本趟 +{len(Y)-n0y}）")
    rl.info("月表", f"{MONTHLY.split('data/')[-1]}｜{len(M):,} 列（本趟 +{len(M)-n0m}）")
    rl.info("本趟", f"成功 {len(ok)}／失敗 {len(fail)}"
            + (f"｜失敗例：{fail[:3]}" if fail else ""))
    # ⛔ 只增不減：這兩份是外部判準，寫短了等於判準消失。
    rl.check("兩份判準檔都只增不減", len(Y) >= n0y and len(M) >= n0m,
             f"年 {n0y}→{len(Y)}｜月 {n0m}→{len(M)}")
    # ⚠ 全失敗＝被擋或參數壞了，要當場紅；零星失敗（下市檔沒有資料）是正常的。
    rl.check("不是整批失敗（全失敗＝被擋或參數壞了）",
             not todo or len(ok) > 0,
             f"本趟 {len(todo)} 檔全部失敗" if todo and not ok else f"成功 {len(ok)}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
