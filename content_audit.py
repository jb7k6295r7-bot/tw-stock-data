#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""content_audit.py — 每一天的**內容**齊不齊（日曆稽核的另一半）。

## 這支要回答的問題

`calendar_audit.py` 已經證明「2015-01-05 ~ 2026-09-04 每一個上市交易日都有日檔」，
官方 2,845 天 = 我方 2,845 天、兩個方向 0 差異。

**但那只證明「那一天有檔案」。** 一天的檔案存在，跟那一天**該有的股票都在裡面**，
是兩件事。假設某天上櫃端點掛掉，日檔仍然會產生、仍然會進 git、
`daily/` 的檔名集合仍然完整——只是裡面少了 983 檔。
半年後回測讀到那一天，會以為**上櫃股全部沒有交易**，而不是「這天沒抓到」。
那會讓任何「全市場排序」的策略靜默失真。

## 判準從哪裡來（為什麼這不是又一次循環自證）

`_coverage_*.csv` 帳本是**抓取程式自己記的**「我抓到幾列」。
拿它當判準，就是再一次「用自己的產出當自己的判準」——
抓取程式漏抓時它就記漏抓後的數字，帳本永遠是對的。

所以這支的證據**不取自那一天自己**，取自**時間軸上的鄰居**：

1. **帳本 vs 實際檔案**：帳本說 983 列，檔案裡真的有 983 列嗎。
   兩者是不同時間點寫的，對不上就代表其中一份不可信。
2. **家數的滾動中位數**：某市場某天的家數，跟前後各 10 個交易日比。
   整批漏抓的症狀是「那一天特別少」，而**單一天的檔案自己看不出這件事**。
   ★ 一定要用**局部**中位數：2015 年上市 903 檔、2026 年 1,368 檔，
     拿全期平均當基準會把 2015 年整年判成漏抓。
3. **逐檔的時間軸缺漏**：某檔在 d-1 與 d+1 都有、d 沒有。
   d 那天的檔案由**那一趟**寫、d±1 由**另外兩趟**寫，互相是獨立證據。
4. **有列但沒有值**：列在裡面、`close` 卻是空的或不是數字。
   這種「列數對、內容空」是最難發現的一種——覆蓋率、家數統計全都會說沒事。

## 這支**不**做的事

- **不判斷單一檔的缺漏是停牌還是漏抓。** 那需要停牌公告，本庫沒有。
  停牌是真實而且常見的（全額交割、重大訊息、減資換發新股期間動輒停 5~10 天），
  所以逐檔缺漏**本來就不會是 0**，數字大不等於有問題。
  這支只做一件事：把 `data/adj/` 裡的**減資事件**對上去，
  把「已知有減資、缺漏就落在那前後」的部分標成**已解釋**，剩下的才需要人看。
- **不刪任何東西、不補任何東西。** 只讀、只報告、只寫一份稽核表。
- **不涵蓋興櫃的價格欄。** 興櫃端點根本沒有開盤與收盤（`price_basis` 那欄就是為此存在），
  對它做 `close` 缺值檢查會產出 100% 的假警報。

## 輸出

- 終端報告（給人看的判讀）
- `--write` 時另寫 `data/meta/_content_audit.csv`：
  逐日逐市場的 實際家數／局部中位數／比值／帳本家數／旗標。
  2,845 × 3 列在 log 裡看不完，要查某一天得看這份。
"""

import argparse
import os
import statistics
import sys

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DAILY_DIR = os.path.join(_ROOT, "universe", "daily")
ADJ_DIR = os.path.join(_ROOT, "adj")
CAL_TWSE = os.path.join(_ROOT, "meta", "calendar_twse.csv")
OUT = os.path.join(_ROOT, "meta", "_content_audit.csv")
LEDGERS = [os.path.join(_ROOT, "universe", n) for n in
           ("_coverage.csv", "_coverage_backfill.csv", "_coverage_daily.csv")]

MARKETS = ("twse", "tpex", "emerging")
OUT_HEADER = ["date", "market", "rows", "median", "ratio", "ledger", "flag"]


# ── 讀檔 ──────────────────────────────────────────────────────────
def load_calendar():
    """→ (交易日 list, 來源說明)。

    ★ 優先用 `calendar_twse.csv`（FMTQIK 這條獨立來源產的）。
      拿 `daily/` 的檔名集合當日曆，就是用被稽核的對象當日曆——
      那樣「官方有我方無」永遠是 0，因為判準是從我方長出來的。
      沒有那份檔就退回檔名集合，並**在報告裡講明退回了**，不要默默降級。
    """
    if os.path.exists(CAL_TWSE):
        days = []
        with open(CAL_TWSE, encoding="utf-8") as f:
            for i, ln in enumerate(f):
                q = ln.rstrip("\n").split(",")
                if i and q and q[0][:1].isdigit():
                    days.append(q[0])
        if days:
            return sorted(days), f"calendar_twse.csv（FMTQIK 獨立來源，{len(days)} 天）"
    if not os.path.isdir(DAILY_DIR):
        return [], "找不到日曆，也找不到 daily/"
    days = sorted(n[:-4] for n in os.listdir(DAILY_DIR) if n.endswith(".csv"))
    return days, (f"★ **退回** daily/ 的檔名集合（{len(days)} 天）"
                  "——沒有 calendar_twse.csv，這一項是循環自證，結論打折")


def load_ledger():
    """合併三份 coverage 帳本 → {date: {market: int, 'note': str, 'src': str}}。

    ★ 三份是按**寫入者**拆的（legacy／回補／每日），不是按時間。
      同一天可能出現在兩份裡（回補跑過又被每日覆蓋），**後讀的贏**，
      順序＝ legacy → backfill → daily，與 `backfill.read_coverage()` 一致。
    """
    out = {}
    for path in LEDGERS:
        if not os.path.exists(path):
            continue
        tag = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            head = None
            for ln in f:
                q = ln.rstrip("\n").split(",")
                if head is None:
                    head = q
                    continue
                if not q or not q[0][:1].isdigit():
                    continue
                rec = {"note": q[5] if len(q) > 5 else "", "src": tag}
                for i, m in enumerate(MARKETS, start=1):
                    try:
                        rec[m] = int(q[i])
                    except (IndexError, ValueError):
                        rec[m] = None
                out[q[0]] = rec
    return out


def scan_days(cal):
    """掃過每一個日檔。→ (counts, empty_close, present, missing_files, bad_rows)

    - counts[date][market]   = 列數
    - empty_close[date]      = 上市＋上櫃裡 close 空白或不是數字的列數
    - present[stock_id]      = bytearray(len(cal))，第 i 天有沒有這一檔
    - missing_files          = 日曆上有、但 daily/ 沒有這個檔的日子
    - bad_rows[date]         = 欄位數不足、解析不了的列數
    - mkt_of[stock_id]       = 這一檔屬於哪個市場（第 5 節分類用）

    ★ 用 bytearray 存在場矩陣：3,500 檔 × 2,845 天 ≈ 10MB。
      改用 set-of-set 會到 GB 級，runner 上會被 OOM 砍掉，
      而 OOM 的症狀是「跑到一半沒了」，很容易被當成別的問題。
    """
    n = len(cal)
    idx = {d: i for i, d in enumerate(cal)}
    counts, empty_close, bad_rows = {}, {}, {}
    present, missing_files, mkt_of = {}, [], {}
    for d in cal:
        path = os.path.join(DAILY_DIR, f"{d}.csv")
        if not os.path.exists(path):
            missing_files.append(d)
            continue
        i = idx[d]
        c = {m: 0 for m in MARKETS}
        ec = bad = 0
        with open(path, encoding="utf-8") as f:
            head = None
            for ln in f:
                q = ln.rstrip("\n").split(",")
                if head is None:
                    head = q
                    continue
                if len(q) < 9:
                    bad += 1
                    continue
                sid, mkt, close = q[2], q[4], q[8]
                if mkt in c:
                    c[mkt] += 1
                else:
                    bad += 1
                    continue
                b = present.get(sid)
                if b is None:
                    b = present[sid] = bytearray(n)
                b[i] = 1
                mkt_of[sid] = mkt          # 同一檔轉市場的話以最後一次為準
                # 興櫃沒有收盤價（price_basis 欄就是為此存在），不列入缺值檢查
                if mkt != "emerging":
                    try:
                        float(close)
                    except ValueError:
                        ec += 1
        counts[d] = c
        empty_close[d] = ec
        bad_rows[d] = bad
    return counts, empty_close, present, missing_files, bad_rows, mkt_of


def load_reduce_days():
    """→ {stock_id: set(減資事件日)}。沒有 data/adj/ 就回空 dict。

    只拿來**解釋**逐檔缺漏（減資換發新股期間會停牌數日），不拿來判定對錯。
    """
    out = {}
    if not os.path.isdir(ADJ_DIR):
        return out
    for n in os.listdir(ADJ_DIR):
        if not n.endswith(".csv") or n.startswith("_"):
            continue
        sid = n[:-4]
        days = set()
        with open(os.path.join(ADJ_DIR, n), encoding="utf-8") as f:
            head = None
            for ln in f:
                q = ln.rstrip("\n").split(",")
                if head is None:
                    head = q
                    continue
                if len(q) >= 7 and q[6] == "reduce":
                    days.add(q[0])
        if days:
            out[sid] = days
    return out


# ── 檢查 ──────────────────────────────────────────────────────────
def rolling_median(vals, i, half=10):
    """第 i 天的局部中位數，**不含自己**。樣本不足回 None（不要用全期平均頂替）。"""
    lo, hi = max(0, i - half), min(len(vals), i + half + 1)
    w = [v for j, v in enumerate(vals) if lo <= j < hi and j != i and v is not None]
    return statistics.median(w) if len(w) >= 5 else None


def main():
    ap = argparse.ArgumentParser(description="稽核每一天的內容齊不齊")
    ap.add_argument("--ratio", type=float, default=0.90,
                    help="家數低於局部中位數的這個比例就標記（預設 0.90）")
    ap.add_argument("--half", type=int, default=10, help="滾動窗口的半寬（交易日）")
    ap.add_argument("--top", type=int, default=25, help="每一節最多印幾列")
    ap.add_argument("--write", action="store_true",
                    help="寫出 data/meta/_content_audit.csv（預設只報告）")
    a = ap.parse_args()

    cal, cal_src = load_calendar()
    if not cal:
        print("[content] 沒有交易日曆，無法稽核", file=sys.stderr)
        return 1
    print(f"[content] 交易日曆來源：{cal_src}")
    print(f"[content] 區間 {cal[0]} ~ {cal[-1]}｜{len(cal)} 個交易日")

    counts, empty_close, present, missing_files, bad_rows, mkt_of = scan_days(cal)
    ledger = load_ledger()
    print(f"[content] 讀到 {len(counts)} 個日檔、{len(present)} 個代號、"
          f"帳本 {len(ledger)} 天")

    problems = 0

    # ── 0. 日曆上有、daily/ 卻沒有這個檔 ──
    if missing_files:
        problems += len(missing_files)
        print(f"\n[0] ★★ **日曆上有、daily/ 沒有檔案：{len(missing_files)} 天**")
        for d in missing_files[:a.top]:
            print(f"        {d}")
        if len(missing_files) > a.top:
            print(f"        …另外 {len(missing_files) - a.top} 天")
    else:
        print("\n[0] 日曆上的每一天都有日檔：**0 天缺檔**")

    # ── 1. 各市場從哪一天開始才算數 ──
    #    興櫃是 2026 才加的層。把它 2015~2026 的 0 全部當成漏抓，
    #    會產出 2,800 筆假警報，把真的警報淹掉。
    first = {}
    for m in MARKETS:
        f = next((d for d in cal if counts.get(d, {}).get(m, 0) > 0), None)
        first[m] = f
    print("\n[1] 各市場的第一個有資料的日子（在此之前不列入稽核）：")
    for m in MARKETS:
        print(f"        {m:9s} {first[m] or '**整段都沒有資料**'}")

    # ── 2. 帳本 vs 實際檔案 ──
    mismatch, no_ledger = [], []
    for d in cal:
        if d not in counts:
            continue
        rec = ledger.get(d)
        if not rec:
            no_ledger.append(d)
            continue
        for m in MARKETS:
            if rec.get(m) is None or first[m] is None or d < first[m]:
                continue
            if rec[m] != counts[d][m]:
                mismatch.append((d, m, rec[m], counts[d][m], rec["src"]))
    print(f"\n[2] 帳本 vs 實際檔案：對不上 **{len(mismatch)}** 筆"
          f"｜帳本沒有這一天 {len(no_ledger)} 天")
    problems += len(mismatch)
    for d, m, lv, av, src in mismatch[:a.top]:
        print(f"        {d} {m:9s} 帳本 {lv:>5} ／ 實際 {av:>5}"
              f"（差 {av - lv:+d}，帳本來源 {src}）")
    if len(mismatch) > a.top:
        print(f"        …另外 {len(mismatch) - a.top} 筆")
    if no_ledger:
        print(f"        帳本缺的日子（前 {min(a.top, len(no_ledger))} 個）："
              f"{'、'.join(no_ledger[:a.top])}")

    # ── 3. 家數的局部離群 ──
    print(f"\n[3] 家數 vs 前後各 {a.half} 個交易日的中位數"
          f"（低於 {a.ratio:.0%} 就標記）")
    rows_out, flagged = [], []
    bad_days = {m: set() for m in MARKETS}   # 第 5 節用：這一天這個市場本來就有問題
    for m in MARKETS:
        if first[m] is None:
            print(f"        {m}：整段都沒有資料，跳過")
            continue
        sub = [d for d in cal if d >= first[m]]
        vals = [counts.get(d, {}).get(m) for d in sub]
        low = []
        for i, d in enumerate(sub):
            v = vals[i]
            med = rolling_median(vals, i, a.half)
            ratio = (v / med) if (v is not None and med) else None
            flag = ""
            if v is None:
                flag = "缺檔"
            elif v == 0:
                flag = "**0 列**"
            elif ratio is not None and ratio < a.ratio:
                flag = f"偏低 {ratio:.1%}"
            if flag:
                low.append((d, v, med, ratio, flag))
                bad_days[m].add(d)
            rows_out.append([d, m, "" if v is None else v,
                             "" if med is None else f"{med:.0f}",
                             "" if ratio is None else f"{ratio:.4f}",
                             "" if not ledger.get(d) else
                             ("" if ledger[d].get(m) is None else ledger[d][m]),
                             flag])
        flagged.extend((m, *x) for x in low)
        worst = sorted((x for x in zip(sub, vals) if x[1] is not None),
                       key=lambda t: t[1])[:3]
        print(f"        {m:9s} 標記 {len(low)} 天"
              f"｜最少的三天 {'、'.join(f'{d}={v}' for d, v in worst)}")
    problems += len(flagged)
    if flagged:
        print(f"        ── 被標記的日子（共 {len(flagged)}）──")
        for m, d, v, med, ratio, flag in flagged[:a.top]:
            print(f"        {d} {m:9s} {str(v):>5} 列"
                  f"（中位數 {'-' if med is None else f'{med:.0f}'}）{flag}")
        if len(flagged) > a.top:
            print(f"        …另外 {len(flagged) - a.top} 天")

    # ── 4. 有列但沒有值 ──
    ec = [(d, v) for d, v in empty_close.items() if v]
    ec.sort(key=lambda t: -t[1])
    tot_ec = sum(v for _, v in ec)
    br = [(d, v) for d, v in bad_rows.items() if v]
    print(f"\n[4] 上市＋上櫃「有列但 close 不是數字」：共 **{tot_ec}** 列，"
          f"分布在 {len(ec)} 天｜解析不了的列 {sum(v for _, v in br)} 列")
    problems += tot_ec
    for d, v in ec[:a.top]:
        print(f"        {d} {v} 列")
    if len(ec) > a.top:
        print(f"        …另外 {len(ec) - a.top} 天")

    # ── 5. 逐檔的時間軸缺漏 ──
    #
    # ★ 分類的順序有意義。第一版沒有「市場級」這一類，結果那一天整批漏抓時，
    #   **每一檔都各報一段缺漏**——2,000 檔就是 2,000 段「未解釋」，
    #   把真正需要人看的那幾段淹掉。市場級的問題第 3 節已經報過了，
    #   這裡只要說「有幾段是它造成的」，不要再列一次。
    reduce_days = load_reduce_days()
    gaps = {"market": 0, "reduce": 0, "other": 0}
    by_date, unexplained = {}, []
    for sid, b in present.items():
        lo = hi = -1
        for i, x in enumerate(b):
            if x:
                if lo < 0:
                    lo = i
                hi = i
        if lo < 0 or hi <= lo:
            continue
        rd = reduce_days.get(sid)
        bad = bad_days.get(mkt_of.get(sid, ""), set())
        i = lo
        while i <= hi:
            if b[i]:
                i += 1
                continue
            j = i
            while j <= hi and not b[j]:
                j += 1
            seg = [cal[k] for k in range(i, j)]
            if all(d in bad for d in seg):
                gaps["market"] += 1            # 第 3 節已經報過那幾天了
            elif rd and (rd & set(cal[max(0, i - 2):min(len(cal), j + 2)])):
                gaps["reduce"] += 1            # 減資換發新股期間停牌
            else:
                gaps["other"] += 1
                unexplained.append((sid, cal[i], j - i))
                for d in seg:
                    by_date[d] = by_date.get(d, 0) + 1
            i = j
    tot = sum(gaps.values())
    print(f"\n[5] 逐檔的時間軸缺漏（在該檔首末之間、日曆上是交易日、卻沒有那一列）")
    print(f"        缺漏區間 **{tot}** 段：")
    print(f"          市場級 {gaps['market']:>6} 段"
          f"（那幾天第 3 節已經標記過，不重複列）")
    print(f"          減資   {gaps['reduce']:>6} 段（前後 2 個交易日內有該檔減資事件）")
    print(f"          其餘   {gaps['other']:>6} 段 ← **只有這一類需要人看**")
    print("        ※ 停牌（全額交割、重大訊息、減資換發）是真實而且常見的，"
          "**「其餘」本來就不會是 0**。")
    print("        ※ 真正的警訊是**同一天被大量個股同時命中、而第 3 節卻沒標記那天**"
          "——家數看起來正常、卻少了特定一批。")
    hot = sorted(by_date.items(), key=lambda t: -t[1])[:a.top]
    if hot:
        print(f"        ── 「其餘」最集中的日子 ──")
        for d, k in hot:
            tot_rows = sum(counts.get(d, {}).values()) or 1
            print(f"        {d} {k:>5} 檔缺這一天（當天實際 {tot_rows} 列，"
                  f"約 {k / (k + tot_rows):.1%}）")
    if unexplained:
        print(f"        ── 最長的「其餘」缺漏 ──")
        for sid, d, ln in sorted(unexplained, key=lambda t: -t[2])[:a.top]:
            print(f"        {sid:>7} 自 {d} 起連續缺 {ln} 個交易日")

    # ── 寫檔 ──
    if a.write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(",".join(OUT_HEADER) + "\n")
            for r in rows_out:
                f.write(",".join(str(x) for x in r) + "\n")
        print(f"\n[content] 已寫出 {OUT}（{len(rows_out)} 列）")

    print(f"\n[content] 需要人看的項目合計 {problems} 個"
          f"（第 5 節的逐檔缺漏不計入——它本來就不會是 0）")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
