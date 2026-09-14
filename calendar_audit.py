#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""calendar_audit.py — 拿**獨立來源**核對交易日曆，並把它存下來。

## 為什麼需要

到目前為止「交易日曆」＝ `data/universe/daily/` 的檔名集合。
那是**用自己的產出當自己的判準**：若當初某一天整批漏抓，那天就不會在日曆裡，
於是七個 feed **一致地缺同一天**——覆蓋率算出來是 2,845／2,845，**看起來完美**。
所有「覆蓋 100%」「失敗 0」的結論都建立在這個循環上。

## 用什麼當獨立來源

**TWSE `afterTrading/FMTQIK`（每日市場成交資訊）**，一個月一發。
它回的是**大盤層級**的資料（成交股數、金額、筆數、發行量加權股價指數、漲跌點數），
跟建立 `data/universe/daily/` 的個股行情端點**完全不同條路**——
這才叫獨立。拿另一條個股端點來比只是問同一個人兩次。

實測 2026-09-06（WebFetch）：`date=20150701` → stat=OK、
標題「104年07月市場成交資訊」、**22 列**，首列 `104/07/01`、末列 `104/07/31`。

### ★ 這支會回音 `date`，一定要看標題

回應裡**沒有** `strDate`／`endDate`，只有一個原樣抄回去的 `date`。
`TWT49U` 就是這樣把 2026 的資料寫進 2015 年的每一天的
（見 `sources/exright_incident.md`）。**所以核對只能看 `title`。**
本檔的 `_month_ok()` 只認標題裡的民國年月，抓不到就整月拒收。

## 涵蓋範圍的老實話

FMTQIK **只有上市**。上櫃的開休市在實務上與上市相同（同一組國定假日與颱風假），
但這支**證明不了**上櫃。所以：

- **官方有、我方無** → 幾乎確定是漏抓，要查。
- **我方有、官方無** → 不能直接判成錯。可能是上櫃單獨交易日，
  也可能是我方寫了一個不該存在的日檔。**要逐日看，不要自動刪。**

本檔**只讀不刪**。它產生 `data/meta/calendar_twse.csv`（獨立日曆）與一份差異報告，
要不要動資料由人決定。
"""

import argparse
import calendar as _cal
import io
import json
import os
import re
import sys
import time

import backfill as B
from backfill import why as _W
import runlog

URL = "https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={}&response=json"

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DAILY_DIR = os.path.join(_ROOT, "universe", "daily")
OUT = os.path.join(_ROOT, "meta", "calendar_twse.csv")


def _roc(v):
    """`104/07/01` → `2015-07-01`；抽不到回空字串。"""
    m = re.match(r"\s*(\d{2,3})/(\d{1,2})/(\d{1,2})\s*$", str(v))
    if not m:
        return ""
    return f"{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def _month_ok(titles, y, m):
    """標題是不是**我們要的那個月**。→ (是否相符, 它說的)

    ★ 只看標題。`date` 是原樣回音，看它等於沒檢查。

    ★ 2026-09-07 補：標題可能在**頂層**，也可能在 `tables[i].title` 裡
      （TWSE 兩種回應形狀都有）。只讀頂層的話，遇到多表形狀會變成
      「標題抽不到年月」而**整年 140 個月全部拒收**——看起來像端點壞了，
      其實是我少讀一個地方。所以把所有候選標題都傳進來，任一個對上就算。
    """
    said = []
    for t in titles:
        t = str(t or "")
        mm = re.search(r"(\d{2,3})\s*年\s*(\d{1,2})\s*月", t)
        if not mm:
            continue
        got = (int(mm.group(1)) + 1911, int(mm.group(2)))
        if got == (y, m):
            return True, f"{got[0]}-{got[1]:02d}"
        said.append(f"{got[0]}-{got[1]:02d}")
    if said:
        return False, "／".join(sorted(set(said)))
    joined = "｜".join(str(t or "")[:30] for t in titles if t)
    return False, f"標題抽不到年月：{joined[:60] or '（沒有標題）'}"


def index_of_row(fields, row):
    """→ 這一列的**發行量加權股價指數**（取不到回 ""）。

    ⭐ 照**欄名**取，⛔ 不是位置——第二點⑤（名字不是證據）的反面同樣成立：
    位置也不是證據。2026-09-14 實測 `fields` 是 6 欄、指數在 [4]，
    ⚠ 而「今天在 [4]」不保證 2015 年那幾個月也在 [4]。

    ⛔⛔ **只取這一欄。** 同一張表的 `成交股數`／`成交金額`／`成交筆數`
    **不可以**拿來補 `market_amount.csv`——實測同一天兩條路差很遠：

        2026-09-01   我方(MI_INDEX)          FMTQIK
        成交金額     1,090,449,046,456   1,187,571,567,117   ＋8.9%
        成交股數         5,209,282,128      13,000,849,196   ⛔ **2.5 倍**
        成交筆數             4,224,598           5,301,801   ＋25%

    ⚠ 而**指數那一欄逐位相同**（46,948.72）⇒ 這不是「FMTQIK 壞掉」，
    ⭐ 是**同一張表裡有的欄可以信、有的不行**——口徑差異只落在總量那三欄。
    """
    idx = None
    for i, c in enumerate(fields or []):
        if str(c).strip() == "發行量加權股價指數":
            idx = i
            break
    if idx is None or idx >= len(row):
        return ""
    v = str(row[idx]).replace(",", "").strip()
    if not v or v in ("--", "---", "－"):
        return ""
    try:
        float(v)
    except ValueError:
        return ""
    return v


def fetch_month(y, m, sleep):
    """→ (set(日期), 說明)。整月拒收時回 (None, 原因)。

    ⭐ 2026-09-14 起同時收 `{日期: 收盤指數}`（`fetch_month.index` 放最後一次的結果）。
    """
    doc, err = None, ""
    raw, err = B.get(URL.format(f"{y:04d}{m:02d}01"), retries=2, timeout=45)
    if err:
        return None, f"請求失敗：{_W(err, 70)}"
    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as ex:                               # noqa: BLE001
        return None, f"非 JSON（{len(raw)}B）{type(ex).__name__}"
    stat = str(doc.get("stat", "")).strip()
    if stat.lower() not in ("ok", "success"):
        return None, f"stat={stat}"
    tabs = B._tables(doc)
    if not tabs:
        return None, "沒有 fields/data"
    ok, said = _month_ok([doc.get("title")] + [t.get("title") for t in tabs], y, m)
    if not ok:
        # ★ 這一條就是 exright 事故的防線。標題不符＝它回的是別的月份。
        return None, f"標題不符（要 {y}-{m:02d}，它說 {said}）"

    # ★ 不要盲抓 tabs[0]。TWSE 有些端點一個回應塞好幾張表（見 backfill._tables
    #   的註解），日期表不見得排第一張。抓錯表的症狀是「解析出 0 天」，
    #   跟「那個月沒開市」長得一模一樣——後者根本不存在，但沒人會發現。
    tab = None
    for t in tabs:
        rows = t.get("data") or []
        if rows and rows[0] and _roc(rows[0][0]):
            tab = t
            break
    if tab is None:
        return None, f"{len(tabs)} 張表，沒有一張的首欄是民國日期"

    days, bad, idx_rows = set(), 0, {}
    fetch_month.index = idx_rows
    for r in (tab.get("data") or []):
        if not r:
            continue
        d = _roc(r[0])
        if not d:
            bad += 1
            continue
        if not d.startswith(f"{y:04d}-{m:02d}"):
            # 落在別的月份的列 → 整月不可信，寧可拒收也不要收一半
            return None, f"有列落在區間外（{d}）"
        days.add(d)
        iv = index_of_row(tab.get("fields"), r)
        if iv:
            idx_rows[d] = iv
    fetch_month.index = idx_rows
    return days, (f"{len(days)} 天"
                  + (f"（{bad} 列日期抽不到，已丟棄）" if bad else "")
                  + f"｜指數 {len(idx_rows)} 天")


def write_index(idx_rows, path=None, apply=True):
    """把 FMTQIK 的收盤指數併進 `data/history/market_index.csv`。→ (寫了幾列, 訊息)

    ## ⛔ 三件事寫死在這裡，每一件都對應一條已經付過代價的規矩

    **① 欄位與合併只准有一份實作**（四點五＋第五點）
    這個檔的**唯一寫入者**本來是 `fetch.py`。⇒ 這裡不自己造欄序、不自己寫檔，
    一律用 `fetch.MKT_INDEX_HEADER` ＋ `fetch.merge_history`。

    **② 已經有的日子一律不動**——⛔ 連「看起來一樣」都不動。
    `merge_history` 的主鍵是 date、而且是**整列取代**。
    ⚠ 而我方既有那 9 列是 `fetch` 寫的，`change`／`change_pct` **有值**；
    FMTQIK 給不出 `change_pct` ⇒ 我若把它們一起寫進去，
    那兩欄會被**洗成空白**——⛔ 而 `git diff` 看起來只是「這一趟重算過」（四點六）。

    **③ 而那 9 列正好是天然對照組** ⇒ 不是跳過就算了，是**拿來當閘門**：
    兩條不同的路（FMTQIK 月報 vs MI_INDEX type=IND 日報）算同一個數字，
    對不上就**一列都不寫**。⛔ 不可以先灌進去再說。

    ## ⛔ 為什麼只寫 `close`

    `change` 官方那一欄（`漲跌點數`）2026-09-14 實測是 `'820.25'`，**沒有正負號**，
    ⚠ 而那天本來就是漲的 ⇒ **「它跌的時候有沒有負號」我沒有量到**。
    ⭐ 而 `change` 從 `close` 減得出來 ⇒ **存一個正負號可能是錯的值，
    比留空更糟**（錯的跟對的在檔案裡長得一模一樣）。⇒ 留空。
    """
    import fetch as _F
    path = path or os.path.join(_ROOT, "history", "market_index.csv")
    if not idx_rows:
        return 0, "沒有指數列"
    _, old = _F._read_csv(path)
    same, diff = 0, []
    for d, v in sorted(idx_rows.items()):
        if d not in old:
            continue
        mine_v = old[d][1] if len(old[d]) > 1 else ""
        try:
            if abs(float(mine_v) - float(v)) < 5e-9:
                same += 1
                continue
        except ValueError:
            pass
        diff.append((d, mine_v, v))
    if diff:
        # ③ 對不上 ⇒ 一列都不寫。⚠ 這是「兩條路算同一個數字」的閘門，
        #   ⛔ 它紅的時候要**大聲**，不可以只回一個數字。
        return -1, ("⛔ 與我方既有值對不上 {} 天 ⇒ **一列都不寫**（重疊 {} 天、"
                    "相符 {} 天）：{}".format(
                        len(diff), same + len(diff), same,
                        "；".join(f"{d} 我方 {a}／FMTQIK {b}" for d, a, b in diff[:5])))
    new = [[d, v, "", ""] for d, v in sorted(idx_rows.items()) if d not in old]
    if not new:
        return 0, f"重疊 {same} 天全部相符，沒有新的日子要寫"
    if not apply:
        return len(new), f"⚠ 有 {len(new)} 天可以補（重疊 {same} 天全部相符）"
    total, added, changed = _F.merge_history(
        path, _F.MKT_INDEX_HEADER, new, "market_index")
    if changed:
        # ⛔ 不該發生：上面已經濾掉既有的日子。發生就是 old 讀錯了。
        return -1, f"⛔ merge_history 回報改動了 {len(changed)} 列，**這不該發生**"
    return added, (f"⭐ 補了 {added} 天（重疊 {same} 天逐位相符，⛔ 一列都沒動）"
                   f"｜檔內共 {total} 天")


def ours():
    if not os.path.isdir(DAILY_DIR):
        return set()
    return {n[:-4] for n in os.listdir(DAILY_DIR) if n.endswith(".csv")}


def calendar_lag(root=None):
    """→ (三個 coverage 檔各自的最後一天 dict, union 最後一天, 日檔最後一天)。

    ⛔ **只讀不寫**，任何一個檔不存在都不可以丟例外——這是附加的能見度，
      不是資料管線。抽成函式是因為 **inline 在 main() 裡的東西測不到**，
      而測不到的檢查等於不存在。
    """
    uni = os.path.join(root or _ROOT, "universe")
    cov, last = {}, ""
    for f in ("_coverage.csv", "_coverage_backfill.csv", "_coverage_daily.csv"):
        d = ""
        try:
            with io.open(os.path.join(uni, f), encoding="utf-8") as fh:
                for i, ln in enumerate(fh):
                    q = ln.split(",", 1)[0].strip()
                    if i and q[:1].isdigit() and q > d:
                        d = q
        except OSError:
            d = ""
        cov[f] = d or "（不存在）"
        if d > last:
            last = d
    daily = os.path.join(uni, "daily")
    pd = ""
    if os.path.isdir(daily):
        ns = sorted(x[:-4] for x in os.listdir(daily) if x.endswith(".csv"))
        pd = ns[-1] if ns else ""
    return cov, last, pd


def main():
    ap = argparse.ArgumentParser(description="拿 FMTQIK 當獨立來源核對交易日曆")
    ap.add_argument("--start", default="2015-01", help="起月 YYYY-MM")
    ap.add_argument("--end", default="", help="迄月 YYYY-MM，空＝我方日曆的最後一個月")
    ap.add_argument("--sleep", type=float, default=5)
    ap.add_argument("--write", action="store_true",
                    help="把獨立日曆併進 data/meta/calendar_twse.csv（預設只報告）")
    ap.add_argument("--replace", action="store_true",
                    help="⛔ 整份重建，不保留既有的日子。只有在跑完整區間時才可以用")
    ap.add_argument("--write-index", action="store_true",
                    help="⭐ 順便把收盤指數補進 data/history/market_index.csv"
                         "（⛔ 只補沒有的日子；重疊的日子拿來當對照組，對不上就一列都不寫）")
    a = ap.parse_args()
    B.SLEEP = a.sleep

    mine = ours()
    if not mine:
        print("[cal] 找不到 data/universe/daily/，沒有東西可以核對", file=sys.stderr)
        return 1
    end = a.end or max(mine)[:7]
    y, m = int(a.start[:4]), int(a.start[5:7])
    ey, em = int(end[:4]), int(end[5:7])

    print(f"[cal] 獨立來源：TWSE FMTQIK（大盤成交資訊），一個月一發")
    print(f"[cal] {a.start} ~ {end}｜我方日曆 {len(mine)} 天 "
          f"（{min(mine)} ~ {max(mine)}）")
    official, failed, idx_all = set(), [], {}
    n = 0
    while (y, m) <= (ey, em):
        n += 1
        days, note = fetch_month(y, m, a.sleep)
        if days is None:
            failed.append((f"{y}-{m:02d}", note))
            print(f"  ✗ {y}-{m:02d} {note}", flush=True)
        else:
            official |= days
            idx_all.update(getattr(fetch_month, "index", None) or {})
            if n % 12 == 0:
                print(f"  [{n}] {y}-{m:02d} {note}", flush=True)
        m += 1
        if m == 13:
            y, m = y + 1, 1
        time.sleep(a.sleep)

    if failed:
        # ★ 有月份沒問到就**不能下「日曆是對的」這個結論**。
        #   官方集合缺了那些月份，比對出來的「我方多出來的日子」全是假的。
        print(f"\n[cal] ★ {len(failed)} 個月沒問到，**本次比對不完整、結論不成立**：")
        for k, v in failed[:12]:
            print(f"        {k} {v}")
        print("[cal] 先把這些月份補問到，再看下面的差異。")

    # ★ 比對窗口要**兩邊都收斂**。只用 max(official) 當上界的話，
    #   今天已經開市、但我方的每日排程還沒跑到，那幾天會被算成「漏抓」——
    #   那不是漏抓，是還沒排到。差一天就足以讓整份稽核的頭條數字說錯話。
    lo = f"{a.start}-01"
    hi = min(max(official), max(mine)) if official else ""
    scope = {d for d in mine if official and lo <= d <= hi}
    off_scope = {d for d in official if lo <= d <= hi}
    ahead = sorted(d for d in official if hi and d > hi)
    miss = sorted(off_scope - scope)         # 官方有、我方無 → 漏抓
    extra = sorted(scope - off_scope)        # 我方有、官方無 → 要人看

    print(f"\n[cal] 比對窗口 {lo} ~ {hi}"
          f"（上界＝官方最後一天與我方最後一天取小）")
    if ahead:
        print(f"[cal] 官方已開市、但超出我方日曆的 {len(ahead)} 天："
              f"{'、'.join(ahead[:8])}"
              f"{' …' if len(ahead) > 8 else ''}"
              "（**不算漏抓**，是每日排程還沒跑到）")
    print(f"[cal] 官方交易日 {len(off_scope)} 天｜我方同區間 {len(scope)} 天")
    print(f"[cal] **官方有、我方無（疑似漏抓）：{len(miss)} 天**")
    for d in miss[:40]:
        print(f"        {d}")
    if len(miss) > 40:
        print(f"        …另外 {len(miss) - 40} 天")
    print(f"[cal] 我方有、官方無：{len(extra)} 天"
          f"（**不等於錯**——FMTQIK 只有上市，上櫃單獨交易日會落在這裡）")
    for d in extra[:40]:
        print(f"        {d}")
    if len(extra) > 40:
        print(f"        …另外 {len(extra) - 40} 天")

    added = kept = 0
    if a.write and official and not failed:
        # ⛔ **預設是「併進去」，不是整份覆蓋。**
        #   舊版直接把 official 寫成整個檔。跑當月一個月就會把 2,845 天的日曆
        #   截成那個月的幾天——**而且不會報錯，檔案看起來完全正常**。
        #   交易日不會事後被取消，所以「只增不減」是安全的預設；
        #   真要重建整份請明講 --replace。
        prev = set()
        if os.path.exists(OUT) and not a.replace:
            for ln in open(OUT, encoding="utf-8").read().splitlines()[1:]:
                if ln.strip():
                    prev.add(ln.split(",")[0])
        merged = prev | official
        added, kept = len(merged - prev), len(prev)
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write("date,source\n")
            for d in sorted(merged):
                fh.write(f"{d},FMTQIK\n")
        how = "整份重建" if a.replace else f"併入（原有 {kept} 天、新增 {added} 天）"
        print(f"[cal] 已寫出 {OUT}（{len(merged)} 天，{how}）")
        official = merged
    elif a.write and failed:
        # 半套日曆比沒有日曆更危險——它看起來像一份完整的獨立來源。
        print("[cal] ★ 有月份沒問到，**不寫檔**。半套的獨立日曆比沒有更糟："
              "它看起來像完整的，之後沒人會記得它缺了幾個月。", file=sys.stderr)

    # ★ 寫進 data/meta/_last_run.md。日曆是「哪一天該有資料」的唯一外部判準，
    #   它自己落後的話，任何拿它當閘門的檢查都會把最新那天判成非交易日。
    rl = runlog.Run("calendar")
    rl.info("區間", f"{a.start} ~ {end}｜問了 {n} 個月")
    if a.write:
        rl.info("日曆", f"{len(official)} 天"
                        + (f"，本趟新增 {added} 天" if not a.replace else "（整份重建）"))
    rl.check("每個月都問到了", not failed,
             ("沒問到：" + "、".join(k for k, _ in failed[:6])) if failed else f"{n} 個月")
    rl.check("官方有、我方沒有的日子為 0（疑似漏抓）", not miss,
             f"{len(miss)} 天：{'、'.join(miss[:5])}" if miss else "0 天")

    # ⭐ 收盤指數：順便補進 data/history/market_index.csv（同一批回應，0 次額外請求）
    if a.write_index:
        _n, _msg = write_index(idx_all)
        print(f"\n[cal] 收盤指數：{_msg}")
        rl.info("收盤指數", f"解析到 {len(idx_all)} 天｜{_msg}")
        # ⛔ 閘門：兩條路（FMTQIK 月報 vs MI_INDEX 日報）算同一個數字，
        #   對不上就是 -1，而那**一定要紅**——⚠ 不紅的話它只是一行 info，
        #   而「沒補到」跟「補了錯的」在檔案裡長得一模一樣。
        rl.check("⭐ 收盤指數與我方既有值對得上（重疊那幾天）", _n >= 0, _msg)
    elif idx_all:
        rl.info("收盤指數", f"解析到 {len(idx_all)} 天"
                            "（⚠ 這一趟**沒有寫入**，要寫請加 --write-index）")

    # ★★ 2026-09-09 補：**把日曆自己的最後一天印出來**（K線線 19:22 要的）。
    #
    #   為什麼：K線線那一側算出「日曆缺 09-04、09-07、09-08」而回報通過——
    #   **他們的日曆是舊的，而舊得看不出來**。原因是「交易日曆」在我方
    #   **分成三個檔**，他們只 union 了兩個：
    #     `_coverage.csv`（回補檔）／`_coverage_backfill.csv`／`_coverage_daily.csv`
    #   ⛔ 而「三個都要 union」這件事**只寫在 backfill.coverage_rows() 裡，
    #     沒有寫在任何一個檔的檔頭** ⇒ 少讀一個的人會拿到一個**看起來完全正常的舊窗口**。
    #
    #   ⇒ 所以這裡把**三個檔各自的最後一天**都印出來，讓「它們不一樣」這件事
    #     在 `_last_run.md` 上一眼看得到，而不是要去讀程式才知道。
    #   ⚠ 這一段**只讀不寫**，任何一個檔不存在都不可以讓這一步炸掉——
    #     它是附加的能見度，不是資料管線。
    # ★★ 2026-09-09 補：**把日曆自己的最後一天印出來**（K線線 19:22 要的）。
    #
    #   為什麼：K線線那一側算出「日曆缺 09-04、09-07、09-08」而回報通過——
    #   **他們的日曆是舊的，而舊得看不出來**。原因是「交易日曆」在我方
    #   **分成三個檔**，他們只 union 了兩個。
    #   ⛔ 而「三個都要 union」這件事**只寫在 backfill.coverage_rows() 裡，
    #     沒有寫在任何一個檔的檔頭** ⇒ 少讀一個的人會拿到一個
    #     **看起來完全正常的舊窗口**。
    _cov, _last, _pd = calendar_lag()
    rl.info("交易日曆三個檔各自的最後一天",
            "｜".join(f"{k} {v}" for k, v in _cov.items())
            + f"｜**union {_last or '（都讀不到）'}**"
            + "　⛔ 三個都要 union，少讀一個會拿到看起來正常的舊窗口")
    rl.info("日檔最後一天", _pd or "（讀不到 data/universe/daily/）")
    # ⛔ 這一條就是 K線線那一側缺的那個斷言。日曆落後於價格 ⇒ 任何拿它當閘門的
    #   檢查都會**靜默往前平移**，而且照樣回報通過。
    rl.check("交易日曆（三檔 union）沒有落後於日檔", bool(_pd) and _last >= _pd,
             f"日曆 {_last or '?'}｜日檔 {_pd or '?'}"
             + ("　⇒ 落後的話，以日曆為基準的近 20／60 日窗會靜默往前平移"
                if not (_pd and _last >= _pd) else ""))

    rc = rl.finish()
    return 1 if (failed or miss or rc) else 0


if __name__ == "__main__":
    sys.exit(main())
