#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""esb_day_repair.py — 把**某一天**被刪掉的興櫃列補回日檔。

    python3 esb_day_repair.py --date 2026-09-08 [--dry-run]

## ⛔ 它為什麼存在（一次我自己造成的遺失）

`data/universe/daily/2026-09-08.csv` 的 **363 列興櫃整批不見**：

    2026-09-04  emerging=363
    2026-09-07  emerging=363
    ⛔ 2026-09-08  emerging=**0**
    2026-09-09  emerging=363

成因是我那趟「一天實測」（`--markets twse,tpex --force`），
而當時的 `write_day` 是**整檔覆蓋** ⇒ 沒抓的市場被無聲刪掉。
⭐ `write_universe_day` 當天就修好了（現在保留沒抓的市場），⛔ 但那一天沒有補回來。

## ⭐ 探針怎麼回答「補不補得回來」（`esb_day_probe.py`，Actions 2026-09-10）

九條「帶日期、回全市場」的候選 **兩天都 0 條可用**——⚠ 而失敗訊息本身就是答案：

    stat：請輸入資料日期及股票代碼查詢個股行情

⇒ `type=Daily` **強制要 code**，沒有全市場模式。
⇒ ⭐ 但**逐檔**的月表（`type=Monthly&code=<代號>`）**是可用的**，
  而某一檔的九月月表裡就有 09-08 那一列。
⇒ **補得回來，只是要打 363 次**（一檔一發，約 30 分鐘）。

## ⭐⭐ 但**先問一件事**：那些列是不是根本還在別的 ref 上？

2026-09-10 實測，`data/universe/daily/2026-09-08.csv` 的兩份副本是**互補**的：

    main   ： twse 1382｜tpex 1013｜emerging **0**
    分支    ： twse **1**｜tpex 1013｜emerging **363**   ← 那 363 列一直在這裡

⚠ 那正是 CLAUDE.md 第四點六（「分支上的 `data/` 比 main 舊」）的**反面**：
這一次**舊的那一份反而是唯一還留著的**。
⭐ 而分支那 363 列與 09-07／09-09 的興櫃列**逐字不同** ⇒ 是真的那一天的資料，
⛔ 不是「上一個交易日被寫進今天」那種。

⇒ `--from-git <ref>` 就走這條：**一個請求都不打**，把那個 ref 的興櫃列讀出來合併。
⚠ 網路那條（`--from-esb`）留著，因為下一次未必這麼幸運。

## ⚠ 補回來的列與正常抓的列**不完全一樣**——這件事要說出來

月表給的是：`high／low／均價／volume／amount／transactions`。

    ⭐ 比每日那條路**多**了 `transactions`（openapi 那條沒有）
    ⛔ **少**了 `change`（漲跌）與 `last_price`（最新成交價）

⛔ `change` **留空，不推算**：興櫃的「漲跌」官方是拿什麼當基準沒有明文，
猜一個數字比留空更糟——留空下游看得見，猜錯的下游看不見。
（⚠ 而 2026-09-09 那天的 363 列 `last_price` 本來就是空的：
那一欄是同一天稍晚才上線的 ⇒ 這一點上兩天反而一致。）

## ⛔ 這一支不是第二個寫入者

寫檔走的是 `fetch.write_universe_day` **本人**（不是拷貝）——
它只覆蓋這一趟真的抓了的市場，所以 twse／tpex 那 2,395 列原封不動。
"""
import argparse
import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import backfill as B
import fetch as F
import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = B._ROOT
DAILY = os.path.join(_ROOT, "universe", "daily")
H = list(F.UNIVERSE_HEADER)


def _day_rows(day):
    """→ 那一天日檔的列（dict）。沒有檔就回 []。"""
    p = os.path.join(DAILY, f"{day}.csv")
    if not os.path.exists(p):
        return []
    with io.open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def neighbours(day, n=1):
    """→ 目標日**前後**各 n 個有日檔的日子。⛔ 用資料自己，不算日曆。"""
    days = sorted(x[:-4] for x in os.listdir(DAILY)) if os.path.isdir(DAILY) else []
    before = [d for d in days if d < day][-n:]
    after = [d for d in days if d > day][:n]
    return before, after


def expected_codes(day):
    """→ ({代號: 名稱}, 說明)。母體取自**前後兩天的興櫃列**。

    ⛔ 不用 `stocks.csv`：那個檔的 `last_seen` 會被這一天的缺漏影響
    ⇒ 拿它當母體等於拿被污染的東西當判準。
    ⭐ 前後兩天都在的那些才是「這一天應該要有」的最穩底線。
    """
    before, after = neighbours(day)
    got, seen = {}, []
    for d in before + after:
        rs = [r for r in _day_rows(d) if (r.get("market") or "") == "emerging"]
        seen.append(f"{d}:{len(rs)}")
        for r in rs:
            got.setdefault(r.get("stock_id", "").strip(),
                           r.get("name", "").strip())
    got.pop("", None)
    return got, f"母體取自前後兩天的興櫃列（{'、'.join(seen) or '沒有鄰居'}）"


def month_of(day):
    return f"{day[:4]}/{day[5:7]}"


def fetch_one(code, day, sleep=5.0):
    """→ (那一天的月表列, 說明)。⛔ 挑出來的列必須**自己講出它是那一天**。"""
    raw, err = B.get(B.esb_month_url(code, month_of(day)))
    time.sleep(sleep)
    if err:
        return None, f"抓不到：{str(err)[:80]}"
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        return None, f"不是 JSON：{str(ex)[:60]}｜前 80：{raw[:80]!r}"
    lines, note = B.parse_esb_month(d, code)
    # ⭐ `lines` 的第 0 欄是月表**自己**寫的日期 ⇒ 這就是「這一批要自己講出它是哪一天」。
    hit = [r for r in lines if r[0] == day]
    if not hit:
        return None, f"月表裡沒有 {day}（{note}）"
    return hit[0], note


def rows_from_git(ref, day, market="emerging"):
    """→ (那個 ref 上這一天的該市場列, 說明)。⛔ 一個請求都不打。

    ⚠ 用 `git show`，⛔ 不是 checkout：checkout 會動到工作區的其他檔。
    ⭐ 欄位**按欄名對應**，不按位置——那份舊副本少了 `last_price`（16 欄），
      按位置搬會整排錯位，⚠ 而錯位之後每一格都還是「看起來正常的數字」。
    """
    import subprocess
    try:
        raw = subprocess.run(
            ["git", "show", f"{ref}:data/universe/daily/{day}.csv"],
            capture_output=True, check=True).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.CalledProcessError) as ex:       # noqa: BLE001
        return [], f"{ref} 上取不到 {day} 的日檔：{str(ex)[:80]}"
    rd = list(csv.DictReader(io.StringIO(raw)))
    hit = [r for r in rd if (r.get("market") or "") == market]
    out = []
    for r in hit:
        # ⭐ 這一批要自己講出它是哪一天（跟網路那條同一道守門）
        if (r.get("date") or "") != day:
            continue
        out.append([r.get(h, "") for h in H])
    return out, (f"{ref} 上 {day} 共 {len(rd)} 列｜其中 {market} {len(hit)} 列"
                 f"｜日期對得上 {len(out)} 列")


def fetch_all(todo, codes, day, sleep):
    """逐檔打月表。→ (universe 列, 缺的)。⛔ 抽成函式是為了讓 main 只挑來源。"""
    rows, miss = [], []
    for i, c in enumerate(todo, 1):
        r, note = fetch_one(c, day, sleep)
        if r is None:
            miss.append((c, note))
        else:
            rows.append(to_universe(r, codes[c]))
        if i % 50 == 0:
            print(f"  [{i}/{len(todo)}] 取得 {len(rows)}、缺 {len(miss)}", flush=True)
    return rows, miss


def to_universe(esb_row, name):
    """月表列（ESB_HEADER）→ 日檔列（UNIVERSE_HEADER）。

    ⛔ 沒有的欄位一律留空，**不要填 0 也不要推算**：
    `close=0` 那件事（52 列寫進去、回測算出 −100%）就是「沒有」被寫成「零」。
    """
    day, code, hi, lo, avg, vol, amt, tx, basis = (list(esb_row) + [""] * 9)[:9]
    r = {h: "" for h in H}
    r["key"] = f"{day}_{code}"
    r["date"] = day
    r["stock_id"] = code
    r["name"] = name
    r["market"] = "emerging"
    r["high"], r["low"], r["close"] = str(hi), str(lo), str(avg)
    r["volume"], r["amount"] = str(vol), str(amt)
    r["transactions"] = str(tx)
    # ⚠ 月表的 `price_basis` 只有兩種：「均價」與「無成交」。
    #   ⛔ 日檔那邊用的是「均價/額推算」——不同來源就寫不同的值，
    #     ⭐ 讓讀的人**看得出這一列是補回來的**，而不是假裝一模一樣。
    r["price_basis"] = "無成交" if basis == "無成交" else "均價（月表補回）"
    return [r[h] for h in H]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--from-git", default="",
                    help="⭐ 先試這個：從另一個 git ref 讀那一天的興櫃列（不連外）")
    ap.add_argument("--sleep", type=float, default=5.0)
    ap.add_argument("--dry-run", action="store_true")
    # ⚠ `--limit` 是**試跑**用的，⛔ 一律不寫檔（見下面那道）。
    ap.add_argument("--limit", type=int, default=0,
                    help="只跑前 N 檔（試跑用，⛔ 一律不寫檔）")
    a = ap.parse_args()
    day = a.date

    rl = runlog.Run("esb_day_repair")
    rl.info("目標日", f"{day}　⚠ 只補 emerging，⛔ 其他市場的列由 "
                      "`fetch.write_universe_day` 原封保留")

    cur = _day_rows(day)
    have = [r for r in cur if (r.get("market") or "") == "emerging"]
    other = len(cur) - len(have)
    rl.info("這一天現況", f"共 {len(cur)} 列｜其中興櫃 **{len(have)}** 列｜其他市場 {other} 列")
    # ⛔ 已經有興櫃列就不要動：這一支是**修補**，不是重抓。
    #   ⚠ 而「重抓」在這裡特別危險：月表少 change／last_price，
    #     蓋掉正常抓的列 = 拿比較差的來源換掉比較好的。
    if have:
        rl.check("這一天的興櫃列本來就是空的（⇒ 才需要補）", False,
                 f"已經有 {len(have)} 列 ⇒ ⛔ 不動它。"
                 "月表少 `change`／`last_price`，覆蓋等於用較差的來源換掉較好的")
        return rl.finish()
    if not cur:
        rl.check("這一天有日檔", False, f"{day} 沒有日檔 ⇒ 這不是「少了興櫃」的問題")
        return rl.finish()

    codes, how = expected_codes(day)
    rl.info("應該要有的興櫃檔數", f"**{len(codes)}** 檔　{how}")
    rl.check("算得出母體（⛔ 前後兩天都沒有興櫃列的話這一支無從判斷）",
             bool(codes), how)
    if not codes:
        return rl.finish()

    # ── 兩條來源，⭐ 先試不必連外的那一條 ─────────────────────
    dry = a.dry_run
    if a.from_git:
        rows, gnote = rows_from_git(a.from_git, day)
        got = {r[H.index("stock_id")] for r in rows}
        miss = [(c, "那個 ref 上也沒有") for c in sorted(codes) if c not in got]
        todo = sorted(codes)
        rl.info("⭐ 來源：另一個 git ref（⛔ 一個請求都不打）",
                f"{a.from_git}　{gnote}")
    else:
        # ⛔ `--limit` 只能試跑：抓 1 檔就寫進去，日檔會從「明顯缺一整個市場」
        #   變成「看起來齊了」——⚠ 那正是這一支要修的那種**看不出來的**壞法。
        dry = dry or bool(a.limit)
        todo = sorted(codes)[:a.limit] if a.limit else sorted(codes)
        if a.limit:
            rl.info("⚠ --limit 試跑", f"只打 {len(todo)} 檔，⛔ 這一趟一律不寫檔")
        rows, miss = fetch_all(todo, codes, day, a.sleep)

    rl.info("取回來的", f"**{len(rows)}** 列／母體 {len(codes)} 檔"
                        + (f"｜⚠ 缺 {len(miss)}：{miss[:5]}" if miss else ""))
    # ⛔ 只補一半比不補更糟：日檔會從「明顯缺一整個市場」變成「看起來齊了」。
    # ⛔ 分母是**母體**（len(codes)），不是這一趟打了幾檔（len(todo)）。
    #   ⚠ 用 todo 當分母的話，`--limit 1` 抓到 1 檔就是 100% ⇒ 這道形同虛設。
    #   ⭐ 這個洞是 selftest ④ 抓出來的，不是我 review 出來的。
    floor = int(len(codes) * 0.95)
    rl.check(f"抓回來的列數 ≥ **母體**的 95%（{floor} 列／母體 {len(codes)}）",
             len(rows) >= floor,
             f"{len(rows)}／母體 {len(codes)}（這一趟打了 {len(todo)} 檔）"
             "　⛔ 只補一半比不補更糟："
             "日檔會從「明顯缺一整個市場」變成「看起來齊了」")
    if len(rows) < floor:
        return rl.finish()
    bad_day = [r for r in rows if r[H.index("date")] != day]
    rl.check("⭐ 每一列都自己講出它是**目標那一天**", not bad_day,
             f"⛔ {len(bad_day)} 列不是：{bad_day[:2]}" if bad_day else f"{len(rows)} 列全對")
    if bad_day:
        return rl.finish()

    if dry:
        rl.info("⚠ 沒有寫檔（--dry-run／--limit）", f"前 2 列：{rows[:2]}")
        return rl.finish()

    n = F.write_universe_day(day, rows)
    after = _day_rows(day)
    n_esb = sum(1 for r in after if (r.get("market") or "") == "emerging")
    n_other = len(after) - n_esb
    rl.info("寫入", f"write_universe_day 收下 {n} 列")
    rl.check("寫完之後興櫃列數 = 抓回來的列數", n_esb == len(rows),
             f"{n_esb} vs {len(rows)}")
    # ⭐ 這一條才是重點：**其他市場一列都不可以少**。
    #   ⚠ 這一支修的就是「另一個市場被無聲刪掉」，⛔ 它自己絕不可以再犯一次。
    rl.check("⭐ 其他市場的列數**一列都沒少**（⛔ 這一支修的就是這件事）",
             n_other == other, f"補之前 {other}｜補之後 {n_other}")
    rl.info("⚠ 與正常抓的列的差別",
            f"{a.from_git} 上的列**就是當初正常抓的那一批**，逐欄原封不動"
            if a.from_git else
            "月表**多** `transactions`、**少** `change` 與 `last_price`；"
            "`price_basis` 寫「均價（月表補回）」⇒ ⭐ 讀的人看得出這一批是補回來的")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
