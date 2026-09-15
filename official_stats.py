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

#: ⭐ 每幾檔落地一次。⛔ 太大＝被砍時賠得多；太小＝每次都重寫兩份大 CSV。
#  實測一趟 400 檔超過一小時 ⇒ 50 檔約 8 分鐘，賠得起。
FLUSH_EVERY = 50

# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 「問過而它答不出來」的台帳。⛔ 沒有它，這一條**永遠到不了終點**。
#
# 2026-09-15 實測（run 34976777901）：本趟 400 檔，成功 331／失敗 69。
# ⚠ 而**失敗的那 69 檔沒有被記下來** ⇒ 下一趟 `todo` 還是會挑到它們
#   ⇒ ⛔ 每一趟都拿越來越多的請求去問已知答不出來的檔，
#     而「還沒做 320 檔」這個數字**讀起來像是還有 320 檔可以補**。
#
# ⭐ 而那句失敗訊息（`很抱歉，沒有符合條件的資料!`）**講不出它是哪一種**
#   （第二點①那一族）：下市太久／那一年還沒上市／端點當下不穩，三種長得一樣。
# ⇒ 所以判準**不是**「失敗一次就放棄」，是**連續失敗 MISS_TRIES 次**，
#   ⛔ 而且只有在**那一趟有別的檔成功**（＝端點是活的）時才記一次。
#   ⚠ 沒有後面那個條件的話，端點掛掉一趟就會把全部 1,158 檔判死。
MISS = os.path.join(META, "_official_stats_miss.csv")
MISS_HEADER = "stock_id,tries,last_asof,why\n"
MISS_TRIES = 2


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


def load_miss(path=None):
    """→ {代號: (tries, last_asof, why)}。讀不到回 {}（⛔ 不是炸掉）。"""
    p = path or MISS
    out = {}
    if not os.path.exists(p):
        return out
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sid = (r.get("stock_id") or "").strip()
            if not sid:
                continue
            try:
                n = int(r.get("tries") or 0)
            except ValueError:
                n = 0
            out[sid] = (n, (r.get("last_asof") or "").strip(),
                        (r.get("why") or "").strip())
    return out


def bump_miss(fail, today, path=None, alive=True):
    """把本趟失敗的檔**累加**進 miss 台帳。→ 寫進去的檔數。

    ⛔⛔ `alive` 是**必填語意**：那一趟有沒有任何一檔成功。
    ⚠ 端點整個掛掉時每一檔都會失敗 ⇒ 若照樣累加，**兩趟就把全庫判死**，
    而畫面上完全正常（四點二那一族：這個綠燈在錯的時候也一樣綠）。
    ⇒ `alive=False` ⇒ **一個字都不寫**。

    ⭐ 而它是**合併**，⛔ 不是整份取代（四點六③ `save_done` 那個坑）：
    讀進來的 dict ＋ 本趟的鍵，再整份寫回。
    ⚠ 而**成功過的檔要從這裡消失**——那是由 `todo` 那一側保證的
    （成功之後它進 `DONE`，就再也不會被挑到）⇒ 這裡只管累加。
    """
    p = path or MISS
    if not alive or not fail:
        return 0
    cur = load_miss(p)
    for sid, why in fail:
        n, _, _ = cur.get(sid, (0, "", ""))
        cur[sid] = (n + 1, today, str(why)[:120])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(MISS_HEADER)
        for sid in sorted(cur):
            n, asof, why = cur[sid]
            f.write(f"{sid},{n},{asof},{str(why).replace(',', '；')}\n")
    return len(fail)


def split_todo(pool, done, miss, limit, tries=MISS_TRIES):
    """把母體切成三堆。→ (todo, 還沒問過的全部, 問到放棄的)。

    ⛔ **三堆要分開報**：「還沒做」把後兩者混在一起，
    ⚠ 而它們的意義完全不同——一個是還有得補，一個是**這條路到此為止**。
    """
    give_up = sorted(c for c in pool
                     if c not in done and miss.get(c, (0,))[0] >= tries)
    fresh = [c for c in pool if c not in done and c not in set(give_up)]
    return fresh[:limit], fresh, give_up


CONTROL_N = 3


def controls(pool, done, n=CONTROL_N):
    """→ 對照組：**已經答得出來過**而且**還在母體裡**的前 n 個代號。

    ⭐ 它回答的是「全失敗是**哪一種**」——⛔ 而那兩種在 runlog 上長得一模一樣：

    ```
    ① 端點被擋／參數壞了          ⇒ 真的要紅，⛔ 而且一個字都不可以寫進 miss
    ② 剩下的那一批**剛好**全部是
       這個端點答不出來的         ⇒ 這是**收斂的正常終局**，⛔ 不是故障
    ```

    ⚠ 2026-09-16 04:00（run 35010414869）就是②的形狀：母體 1,158、已完成 1,054、
    本趟 104 檔**全部失敗** ⇒ 舊判準 `alive=bool(ok)` 把它判成①（不記 miss）
    ⇒ ⛔ 那 104 檔永遠停在「還沒問過」，下一趟再問同一批、再全失敗
    ⇒ ⭐ **這道閘門從此每一趟都紅**——而 CLAUDE.md 四點五那條已經寫過代價：
    一道天天紅的閘門會被學會忽略，⚠ 而它一旦被忽略，真的壞掉那天也沒有人會看。

    ⭐ 而對照組是**算出來的**，⛔ 不是寫死的代號清單：
    `pool ∩ done` ＝「還在母體裡」∩「以前答得出來」——兩件事都是本趟現場量到的。
    ⚠ `sorted(...)[:n]` 只是要**同一批母體每趟挑到同一組**（可重現），
    ⛔ 不是因為那幾個代號有什麼特別。
    """
    return sorted(set(pool) & set(done))[:n]


def endpoint_alive(ctrl, today, fetch=None):
    """拿對照組問一次 ⇒ (True／False／**None**, 說明)。

    ⛔ `None` 是**第三種**，⚠ 而它跟 `False` 不可以混在一起：
    沒有對照組可用（`--force` 把 done 清掉，或母體與 done 沒有交集）
    ⇒ 意思是**這一層沒跑**，⛔ 不是「端點掛了」。
    ⇒ 照 CLAUDE.md 六點五那條：條件不成立就**大聲印出「這一層沒跑」**，
      ⛔ 不可以寫成斷言（那會把這條線整個關掉），而**退回舊判準**由呼叫端做。
    """
    f = fetch or fetch_one
    if not ctrl:
        return None, ("⛔ **這一層沒跑**：沒有對照組可用"
                      "（`--force` 清掉了 done，或母體與 done 沒有交集）"
                      "　⇒ ⚠ 退回舊判準「本趟有沒有任何一檔成功」")
    got, bad = [], []
    for sid in ctrl:
        _ys, _ms, err = f(sid, today)
        if err:
            bad.append((sid, str(err)[:60]))
        else:
            got.append(sid)
    if got:
        return True, (f"✓ 對照組 {len(got)}／{len(ctrl)} 答得出來（{','.join(got)}）"
                      "　⇒ ⭐ 端點是好的 ⇒ **本趟全失敗是那一批自己的性質**，"
                      "⛔ 不是故障 ⇒ 照常記 miss")
    return False, (f"✗ 對照組 {len(ctrl)} 檔**也**答不出來（{bad}）"
                   "　⇒ ⛔ 端點側的問題 ⇒ ⭐ 一個字都不寫進 miss 台帳")


def land(Y, M, ok, today, rl=None):
    """把這一批**落地**：兩份判準檔 ＋ 續跑台帳。→ 這次寫進台帳的檔數。

    ⭐ 只有這一份實作（四點五）：**期中 flush 與最後一次走同一條路**。
    ⛔ 兩條路的話，期中那條遲早會少寫一個檔，而且沒有人會發現。

    ## ⛔ 為什麼要期中落地（CLAUDE.md 第四點）

    這一步 `--limit 400`，實測一趟 **超過一小時**。⚠ 而它本來只在**最後**寫檔
    ⇒ job 被砍（350 分上限）、runner 掉、任何例外 ⇒ ⛔ **整批 400 檔全部白跑**，
    而下一趟從同一個起點重來 ⇒ ⭐ 那正是「永遠跑不完，每趟都像有在跑」。

    ⇒ 台帳是 **append**（⛔ 不是整份取代——四點六③那個 `save_done` 的坑），
    ⚠ 而 `_save` 是「讀進來的 dict ＋ 本趟的鍵」再整份寫回 ⇒ 那是**逐鍵合併**，
    ⛔ 不是覆蓋。
    """
    if Y or os.path.exists(YEARLY):
        _save(YEARLY, Y_HEADER, Y)
    if M or os.path.exists(MONTHLY):
        _save(MONTHLY, M_HEADER, M)
    if not ok:
        return 0
    new = not os.path.exists(DONE)
    with io.open(DONE, "a", encoding="utf-8") as f:
        if new:
            f.write("stock_id,asof\n")
        for s in ok:
            f.write(f"{s},{today}\n")
    return len(ok)


def progress_lines(pool, done, todo, ex, give_up=()):
    """續跑那兩行怎麼寫。→ [(label, value)]。⭐ 抽出來是為了驗得到（第七點）。

    ⛔ **分母是 `pool`（這個端點涵蓋得到的），不是全部普通股。**
    ⚠ 用全部當分母的話，13% 這個數字會永遠爬不上去，
    而每一趟都像有在跑——那正是「永遠跑不完，每趟都像有在跑」那個形狀。
    """
    pct = len(done) * 100 // max(1, len(pool))
    gu = list(give_up or [])
    reach = len(pool) - len(gu)
    rp = len(done) * 100 // max(1, reach)
    return [
        ("續跑", f"母體 **{len(pool):,}** 檔（⭐ 只有上市——這個端點不涵蓋別的）"
                 f"｜已完成 {len(done):,}｜**{pct}%**｜本趟 {len(todo)}"),
        # ⭐⭐ 三堆分開報。⛔ 「還沒做」把後兩堆混在一起 ⇒ 那個數字會**永遠不歸零**，
        #   而每一趟都像有在跑（四點六③那個形狀）。
        ("⭐ 還剩下的分兩種（⛔ 不可以合著看）",
         f"**還沒問過** {max(0, reach - len(done)):,} 檔"
         f"｜**問到放棄** {len(gu):,} 檔"
         f"（連續 {MISS_TRIES} 趟答不出來，記在 `_official_stats_miss.csv`）"
         f"　⇒ ⭐ 對**問得到**的那 {reach:,} 檔而言是 **{rp}%**"
         "　⚠ 而「問到放棄」⛔ 不等於「這檔沒有官方統計」"
         "——那句失敗訊息（`很抱歉，沒有符合條件的資料!`）講不出它是哪一種"),
        # ⛔ 排掉的要講出來：「排掉了」與「沒有這種股票」**不是同一件事**
        ("⚠ 這個端點答不出來的（⛔ 不是缺口，是涵蓋範圍）",
         "｜".join(f"{k} {v:,} 檔" for k, v in sorted(ex.items()))
         + "　⇒ ⭐ 實測命中率 twse 94%／tpex 0%／emerging 0%"
           "（⛔ 判準是**兩個市場的命中率**，不是那句「沒有符合條件的資料」"
           "——那句話講不出它是哪一種）"
         + "　⇒ ⛔⛔ **2026-09-16 推翻**「上櫃的官方年度／月統計沒有來源」："
           "probe 120 實測 `POST/GET https://www.tpex.org.tw/www/zh-tw/"
           "statistics/yearlyStock?code=<代號>` ⇒ **一發回 12 年**"
           "（民國 104~115，`totalCount:12`），"
           "⭐ 欄位跟 `FMNPTK` **同一組**：年度／成交張數／金額(仟元)／筆數／"
           "加權平均價／盤中最高最低＋日期／**收盤平均價**"
           "　⇒ ⚠ 而線索一直在我方自己的 `data/meta/_site_inventory.txt` 裡"
           "（3.5④「自己家查過沒有」）"
           "　⇒ ⛔ 而**月**那一半還沒答完：`statistics/monthlyStock` 吃的是"
           "`stkno`＋`year`（`code`＋`date` 回 `參數輸入錯誤`），"
           "⚠ 而它回顯的 `date` 是**今天**（20260916）"
           "⇒ 我還不知道 `year` 有沒有生效（第二點①靜靜回今天）"
           "　⇒ ⭐ 所以這一條**還開著**，⛔ 但開著的理由已經從「沒有來源」"
           "變成「還沒接上」"),
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
    # ⭐ 三堆只在**這裡切一次**（四點五）：⛔ 不要在別處再算一次 `c not in done`。
    miss = load_miss() if not a.force else {}
    todo, fresh, give_up = split_todo(pool, done, miss, a.limit)
    ex = excluded()
    for label, value in progress_lines(pool, done, todo, ex, give_up):
        rl.info(label, value)
    if not todo:
        rl.info("狀態", "✓ **問得到的全部問完了**"
                        f"（⛔ 不等於「全市場都有官方統計」；⚠ 另有 {len(give_up):,} 檔"
                        "連續答不出來而放棄，見 `_official_stats_miss.csv`）")

    Y, M = _load(YEARLY, Y_HEADER), _load(MONTHLY, M_HEADER)
    n0y, n0m = len(Y), len(M)
    ok = []
    flushed = 0
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
        # ⭐ 每 FLUSH_EVERY 檔落地一次 ⇒ 被砍最多賠 FLUSH_EVERY 檔，⛔ 不是整批 400
        if len(ok) - flushed >= FLUSH_EVERY:
            land(Y, M, ok[flushed:], today)
            flushed = len(ok)
            print(f"  ⭐ 期中落地：已完成 {flushed}／{len(todo)}"
                  "（⇒ 這一趟就算被砍，前面這些不會白跑）", flush=True)
        if a.sleep:
            time.sleep(a.sleep)

    # ⛔ 一筆都沒抓到、而且檔案本來就不存在 ⇒ **不要建立空檔**。
    #   2026-09-09 本機 smoke test（403 全失敗）就留下兩個只有表頭、零列的殘骸——
    #   **一個存在但空的判準檔，讀起來像是「有這份判準」**，
    #   而那正是今晚一路在抓的形狀（孤兒檔、恆真的 0 筆、留著不標的停更檔）。
    #   ⇒ 有舊內容就照常寫回（不能因為本趟失敗就讓舊的消失）；
    #     完全沒有內容就不落地。
    # ⭐ 最後一次落地走**同一個函式**（⛔ 不是另寫一段）
    land(Y, M, ok[flushed:], today)
    # ⭐⭐ 失敗也要落地，⛔ 否則下一趟還會再問同一批（本節開頭那 69 檔）。
    #   ⚠ `alive` ＝ 這一趟有沒有任何一檔成功：端點整個掛掉時**一個字都不寫**。
    #   ⭐⭐ 而「本趟全失敗」有**兩種**（見 `controls()`），⛔ 它們長得一模一樣
    #     ⇒ 拿**對照組**（還在母體裡而且以前答得出來的幾檔）當**外部錨點**問一次。
    #     ⚠ 只在需要判別的時候問（`fail and not ok`）⇒ 正常那幾趟一發都不多打。
    alive = bool(ok)
    if fail and not ok:
        probed, ctrl_why = endpoint_alive(controls(pool, done), today)
        rl.info("⭐ 全失敗 ⇒ 拿**對照組**問一次（⛔ 不是在兩種成因之間猜）", ctrl_why)
        if probed is True:
            alive = True
    n_miss = bump_miss(fail, today, alive=alive)
    if fail and not ok and not alive:
        rl.info("⛔ 本趟全失敗、**而且對照組也答不出來** ⇒ 不記 miss",
                f"{len(fail):,} 檔全部失敗 ⇒ 判定是**端點側**的問題，"
                "⚠ 而不是這些檔沒有資料　⇒ ⭐ 一個字都不寫進 miss 台帳"
                "（⛔ 寫了的話，掛掉兩趟就把全庫判死，而畫面上完全正常）")
    elif n_miss:
        rl.info("本趟記進 miss 台帳",
                f"{n_miss:,} 檔　⇒ 連續 {MISS_TRIES} 趟才會被跳過，"
                "⭐ 而它們仍然留在母體裡（⛔ 不是從報表上消失）")
    if not Y and not M:
        rl.info("處置", "⛔ 一筆都沒抓到且檔案不存在 ⇒ **不建立空檔**"
                        "（空的判準檔讀起來像是有這份判準）")
    rl.info("期中落地", f"每 {FLUSH_EVERY} 檔寫一次"
                        f"｜本趟落地 {len(ok):,} 檔"
                        "　⇒ ⭐ 被砍最多賠 {} 檔，⛔ 不是整批".format(FLUSH_EVERY))

    rl.info("年度表", f"{YEARLY.split('data/')[-1]}｜{len(Y):,} 列（本趟 +{len(Y)-n0y}）")
    rl.info("月表", f"{MONTHLY.split('data/')[-1]}｜{len(M):,} 列（本趟 +{len(M)-n0m}）")
    rl.info("本趟", f"成功 {len(ok)}／失敗 {len(fail)}"
            + (f"｜失敗例：{fail[:3]}" if fail else ""))
    # ⛔ 只增不減：這兩份是外部判準，寫短了等於判準消失。
    rl.check("兩份判準檔都只增不減", len(Y) >= n0y and len(M) >= n0m,
             f"年 {n0y}→{len(Y)}｜月 {n0m}→{len(M)}")
    # ⚠ 全失敗**而且對照組也答不出來**＝被擋或參數壞了，要當場紅；
    #   零星失敗（下市檔沒有資料）、以及「剩下的剛好全都答不出來」都是正常的。
    # ⭐⭐ 放行之後還有誰在守（CLAUDE.md 四點五⑥③，⛔ 這段要留在原始碼裡）：
    #   ① **對照組自己**——它答不出來的那一趟立刻 ✗，而它是每趟現場重算的
    #   ② 那 104 檔照常累加進 miss 台帳 ⇒ 連續 MISS_TRIES 趟之後轉進「問到放棄」，
    #      ⭐ 而那一欄**照常印在報表上**（⛔ 不是從報表消失）⇒ 收斂得到、也看得見
    #   ③ 「兩份判準檔只增不減」那道沒有動
    rl.check("不是整批失敗（全失敗**而且對照組也答不出來**＝被擋或參數壞了）",
             not todo or bool(ok) or alive,
             f"本趟 {len(todo)} 檔全部失敗，且對照組也答不出來"
             if todo and not ok else f"成功 {len(ok)}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
