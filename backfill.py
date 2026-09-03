#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全市場日K歷史回補（2015 起）—— 在使用者自己的 GitHub Actions 上執行。

為什麼要有這一支：`fetch.py` 每天只抓「當天」。要做回測就需要長序列，
而**回補是一次性、跑幾小時的工作**，不該塞進每日流程。

★ 兩種模式，先探路再跑長工：

    python3 backfill.py --probe --date 2026-08-28
        對三個市場的每一條候選端點各試一次，把 HTTP 狀態、位元組數、
        實際欄位名寫進 data/universe/_backfill_probe.txt。**先跑這個。**

    python3 backfill.py --run --start 2015-01-01 --end 2015-12-31
        逐日回放。已經有檔案的日期直接跳過，所以**可以分批續跑**。

設計上刻意的幾件事
────
1. **一天一檔**（與 fetch.py 同格式）。git 存的是整個檔案的新版本，
   2,700 檔各自加一列＝每天把整個資料庫重存一遍。
2. **不完整的日子要標出來**：`_coverage.csv` 記每天三個市場各抓到幾列。
   **回測時若不知道那天上櫃沒抓到，會誤以為上櫃股全部沒交易**——
   那會讓任何「全市場排序」的策略靜默失真。
3. **限速**：交易所會擋太快的連線。預設每個請求間隔 1.5 秒，
   2,700 天 × 3 市場 ≈ 8,100 個請求 ≈ 3.4 小時，所以建議一次跑一年。
4. **休市日不是錯誤**：TWSE 回 `stat != OK` 就當休市，記錄後往下一天，不重試。
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; tw-stock-data-backfill/1.0; +https://github.com/)"
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
UNI_DIR = os.path.join(_ROOT, "universe")
DAILY_DIR = os.path.join(UNI_DIR, "daily")
INST_DIR = os.path.join(UNI_DIR, "inst")
COVERAGE = os.path.join(UNI_DIR, "_coverage.csv")
PROBE = os.path.join(UNI_DIR, "_backfill_probe.txt")

HEADER = ["key", "date", "stock_id", "name", "market",
          "open", "high", "low", "close", "volume", "amount", "change", "limit",
          "shares", "transactions", "price_basis"]
# ★ 欄位必須與 fetch.py 的 UNIVERSE_HEADER 逐字一致——兩邊產出同一批檔案，
#   格式一分岔，之後建 DB 就會有一半的日子欄位對不上。
COV_HEADER = ["date", "twse", "tpex", "emerging", "total", "note"]

SLEEP = 1.5


def roc(d):
    """2026-09-02 -> 115/09/02（TPEx 舊端點用民國）"""
    y, m, dd = d.split("-")
    return f"{int(y) - 1911}/{m}/{dd}"


def esb_month_url(code, ym, fmt="json"):
    """興櫃**逐檔逐月**歷史（使用者 2026-09-02 提供）。

    `www/zh-tw/emerging/historical?type=Monthly&date=YYYY/MM/01&code=<代號>&response=json`

    ★ 這是**逐檔**的，不是全市場——364 檔 × 132 個月 ≈ 48,000 個請求，不可能全跑。
      所以只對「使用者在意的那幾檔興櫃股」補歷史，其餘從今天起累積。
    """
    return ("https://www.tpex.org.tw/www/zh-tw/emerging/historical"
            f"?type=Monthly&date={ym}/01&code={code}&id=&response={fmt}")


def candidates(day):
    """每個市場的候選端點，依序試。**這些是假設，--probe 就是用來驗證的。**"""
    ymd = day.replace("-", "")
    slash = day.replace("-", "/")
    return {
        # 上市：今天（2026-09-02）已實測可用，且 date= 參數有效 → 可逐日回放
        "twse": [
            f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
            f"https://www.twse.com.tw/exchangeReport/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
        ],
        # 上櫃：每日用的 openapi **只給當日**，回補必須換帶日期的端點。全部未驗證。
        "tpex": [
            f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={slash}&type=EW&id=&response=json",
            # 舊版 PHP 端點拿掉了：2015 實測，非交易日它會回「今天」的資料
            # （被 _same_day 擋下，但留著只是每個假日多敲一次無用請求）。
            # ★★ 這裡**絕對不可以**放 openapi/v1/tpex_mainboard_daily_close_quotes。
            #   它沒有 date 參數、永遠回「今天」。2026-09-03 實測：2015 年回補時
            #   前面兩條失敗就落到它，於是把 2026-09-02 的 980 檔當成 2015-01-01 寫進檔案
            #   （2015 年上櫃其實只有 666～681 檔）。**元旦休市那天也有 980 列。**
            #   靜默、每個數字都是真的、只是屬於另一個年代——回補最危險的一種錯。
        ],
        # 興櫃：openapi 只有 latest。以下候選是照**新版網站的路徑模式**推出來的——
        # 上櫃通的那條是 `www/zh-tw/afterTrading/otc?date=...&response=json`，
        # 而使用者提供的興櫃頁面是 `zh-tw/esb/trading/info/stock-pricing.html`
        # （該頁本身是 JS，資料不在 HTML 裡，且對外直接讀會 403）。
        # **這些全是假設，probe 就是用來淘汰它們的。**
        "emerging": [
            # ★ 最有希望的一條：`emerging/historical` 已證實存在（使用者提供的 Monthly 版可用），
            #   所以 **type=Daily、不帶 code ＝ 全市場單日** 很可能也成立。
            #   若成立，興櫃就能跟上市上櫃一樣全市場逐日回補，不必逐檔跑 48,000 次。
            f"https://www.tpex.org.tw/www/zh-tw/emerging/historical?type=Daily&date={slash}&id=&response=json",
            f"https://www.tpex.org.tw/www/zh-tw/emerging/historical?type=Daily&date={slash}&code=&id=&response=json",
            # 由 `zh-tw/esb/trading/info/historical/day/com-pricing.html` 這個頁面路徑推出來的
            f"https://www.tpex.org.tw/www/zh-tw/esb/comPricing?date={slash}&id=&response=json",
            f"https://www.tpex.org.tw/www/zh-tw/esb/historical/day/com-pricing?date={slash}&response=json",
            f"https://www.tpex.org.tw/www/zh-tw/esb/stockPricing?date={slash}&id=&response=json",
            f"https://www.tpex.org.tw/www/zh-tw/esb/trading/info/stock-pricing?date={slash}&response=json",
            f"https://www.tpex.org.tw/www/zh-tw/esb/pricing?date={slash}&response=json",
            f"https://www.tpex.org.tw/www/zh-tw/emerging/dailyQuotes?date={slash}&response=json",
            f"https://www.tpex.org.tw/web/emergingstock/historical/daily/EMdaily_result.php?l=zh-tw&d={roc(day)}&o=json",
            # 同上：tpex_esb_latest_statistics 也是「latest」，回補一律不可用
        ],
    }


def get(url, retries=3, timeout=45):
    last = None
    for i in range(retries):
        try:
            # ★ Accept 一定要帶。fetch.py 的 get() 有帶、backfill 原本沒帶，
            #   而 fetch.py 每天抓 T86 都成功、backfill 抓同一條卻每天 JSONDecodeError
            #   （2026-09-03 實測 699 天全失敗）——兩者唯一的差別就是這個標頭。
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/json,text/plain,*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:  # noqa: BLE001
                body = "(讀不到 body)"
            last = f"HTTP {e.code} {e.reason} | {body}"
            if 400 <= e.code < 500 and e.code not in (408, 429):
                return None, last          # 4xx 重試沒有意義
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if i < retries - 1:
            time.sleep(3 * (i + 1))     # 3s、6s。交易所限流時退得太快等於白重試
    return None, last


# ── 解析：與 fetch.py 用同一套規則，刻意複製而不 import ──
# fetch.py 是每日腳本，這支是一次性工具；讓它們各自獨立，
# 改一邊不會意外弄壞另一邊。**兩邊的欄位順序必須一致**（HEADER 就是契約）。

def _num(v):
    if v is None:
        return ""
    t = str(v).replace(",", "").replace("+", "").replace("%", "").strip()
    if t in ("", "-", "--", "X", "N/A", "null", "None"):
        return ""
    try:
        float(t)
    except ValueError:
        return ""
    return t


def _isz(v):
    """_num() 的輸出是字串，"0.00" 是 truthy——要判零一律走這支。"""
    try:
        return float(v) == 0.0
    except (TypeError, ValueError):
        return True


def _kind(code):
    c = str(code)
    if len(c) == 6 and c[0] == "7":
        return "warrant"
    if c.startswith("00"):
        return "etf"
    if len(c) == 5:
        return "special"
    if len(c) == 6:
        return "other"
    return "stock"


def _tables(d):
    if not isinstance(d, dict):
        return []
    if isinstance(d.get("tables"), list):
        return [t for t in d["tables"] if isinstance(t, dict)]
    if d.get("fields") and d.get("data"):
        return [{"title": d.get("title", ""), "fields": d["fields"], "data": d["data"]}]
    # ★ 第三種形狀：**編號鍵**（`fields1`/`data1` … `fields9`/`data9`）。
    #   TWSE 舊版 MI_INDEX 就是這樣回的——一個回應裡塞好幾張表，
    #   用序號區分而不是放進 tables 陣列。
    #   2026-09-03 實測：2015 年整年回補時 twse 每一天都「失敗」，
    #   而 2026-08-28 的同一條端點卻正常，差別只在日期 → 高度懷疑是這個。
    #   不支援它的話，症狀是「連得上、stat=OK、解析出 0 列」，
    #   看起來跟「那天沒有資料」一模一樣。
    out = []
    for k in sorted(d.keys()):
        if not k.startswith("fields"):
            continue
        suffix = k[len("fields"):]
        dk = "data" + suffix
        if isinstance(d.get(k), list) and isinstance(d.get(dk), list):
            out.append({"title": d.get("title" + suffix, d.get("title", "")),
                        "fields": d[k], "data": d[dk]})
    if out:
        return out
    return []


def _same_day(d, day):
    """回應自己宣告的日期，是不是我們要的那一天。→ (是否相符, 它說的日期)

    ★ 這是回補的最後一道防線。端點「不吃日期參數」或「查無就回最近一天」時，
      HTTP 200、stat=OK、欄位全對、每個數字都是真的——**只是屬於別的日子**。
      2026-09-03 就是這樣把 2026-09-02 的資料寫成 2015-01-01。
      沒有這個檢查，錯誤在檔案裡完全看不出來。
    """
    want = day.replace("-", "")
    if not isinstance(d, dict):
        return True, ""            # 無從判斷就不擋，交給呼叫端的其他檢查
    raw = d.get("date") or d.get("Date") or ""
    got = "".join(ch for ch in str(raw) if ch.isdigit())
    if not got:
        return True, ""
    if len(got) == 7:              # 民國 1040105
        got = f"{int(got[:3]) + 1911}{got[3:]}"
    return got[:8] == want, str(raw)


def _idx(fields, *kws):
    for i, f in enumerate(fields):
        if all(k in f for k in kws):
            return i
    return None


def _idx_any(fields, *options):
    """★ 不可寫成 `_idx(a) or _idx(b)`——第 0 欄是 falsy，證券代號正好在第 0 欄。"""
    for kws in options:
        i = _idx(fields, *(kws if isinstance(kws, tuple) else (kws,)))
        if i is not None:
            return i
    return None


def parse_twse(d, day, market="twse"):
    for t in _tables(d):
        fields = [str(x) for x in (t.get("fields") or [])]
        # 找表的條件放寬到「有代號欄 ＋ 有收盤欄」——TPEx 用「代號」，TWSE 用「證券代號」，
        # 寫死其中一種會找不到另一種（2026-09-02 probe 診斷發現）。
        if not (any("代號" in f for f in fields) and any("收盤" in f for f in fields)):
            continue
        i_code = _idx_any(fields, "證券代號", "股票代號", "代號")
        i_name = _idx_any(fields, "證券名稱", "股票名稱", "名稱")
        i_o, i_h = _idx_any(fields, "開盤"), _idx_any(fields, "最高")
        i_l, i_c = _idx_any(fields, "最低"), _idx_any(fields, "收盤")
        i_v, i_a = _idx_any(fields, "成交股數"), _idx_any(fields, "成交金額")
        i_sh = _idx_any(fields, "發行股數")
        i_tx = _idx_any(fields, "成交筆數")
        i_chg = _idx_any(fields, "漲跌價差")
        i_sign = _idx_any(fields, ("漲跌", "+"), "漲跌(+/-)", "漲跌")
        if any(x is None for x in (i_code, i_o, i_h, i_l, i_c)):
            return [], f"欄位對不上：{fields}"
        raw = t.get("data") or []
        # ★ 非交易日 TPEx 回的是「欄位齊全但一列資料都沒有」的空表，
        #   **不是** stat=休市。原本一律當成失敗，結果每個假日都觸發退避，
        #   冷卻一路爬到 300 秒（2026-09-03 掃 2015 週六時實測）。
        #   → 原始資料列數為 0 ＝ 休市；有資料卻解析不出來才是真的故障。
        if not raw:
            return [], "no_rows:空表（休市或無成交）"
        out = []
        for r in raw:
            if not r or len(r) <= i_c:
                continue
            code = str(r[i_code]).strip()
            if not code or not code[0].isdigit():
                continue
            o, h, l, c = _num(r[i_o]), _num(r[i_h]), _num(r[i_l]), _num(r[i_c])
            if not c:
                continue
            # 漲跌有兩種寫法：TWSE 拆成「方向欄（HTML 的 +/-）＋ 漲跌價差」，
            # TPEx 則是單一「漲跌」欄、正負號直接寫在值裡。兩種都要吃。
            if i_chg is not None:
                sign = -1 if (i_sign is not None and "-" in str(r[i_sign])) else 1
                chg = _num(r[i_chg])
                chg = str(sign * float(chg)) if chg else ""
            elif i_sign is not None:
                # ★ 這一欄的正負號直接寫在值裡（"+10.00" / "-5.50"），
                #   而 _num() 只清掉 "+"、**保留 "-"**——所以直接用就好。
                #   先前多做一次 -1 造成負負得正，跌停被標成漲停（2026-09-02 測到）。
                chg = _num(r[i_sign])
            else:
                chg = ""
            lim = ""
            if o and h and l and c and o == h == l == c:
                lim = "up" if (chg and float(chg) > 0) else ("down" if chg else "flat")
            out.append([f"{day}_{code}", day, code,
                        str(r[i_name]).strip() if i_name is not None else "", market,
                        o, h, l, c,
                        _num(r[i_v]) if i_v is not None else "",
                        _num(r[i_a]) if i_a is not None else "", chg, lim,
                        _num(r[i_sh]) if i_sh is not None else "",
                        _num(r[i_tx]) if i_tx is not None else "",
                        ""])          # price_basis：上市／上櫃是收盤價，留空
        return out, f"欄位={fields}"
    return [], "找不到含『證券代號』與『收盤』的表"


def parse_openapi(rows, day, market):
    if isinstance(rows, list) and not rows:
        return [], "no_rows:空 list（休市或無成交）"
    if not isinstance(rows, list):
        return [], "回傳不是 list"
    keys = list(rows[0].keys())

    def pick(*names):
        for n in names:
            for k in keys:
                if n.lower() == k.lower() or n in k:
                    return k
        return None

    k_code = pick("SecuritiesCompanyCode", "Code", "證券代號", "股票代號")
    k_name = pick("CompanyName", "Name", "證券名稱")
    k_c = pick("Close", "LatestPrice", "收盤")
    k_o, k_h, k_l = pick("Open", "開盤"), pick("High", "Highest", "最高"), pick("Low", "Lowest", "最低")
    k_v = pick("TradingShares", "TransactionVolume", "成交股數")
    k_a = pick("TransactionAmount", "成交金額")
    k_chg = pick("Change", "漲跌")

    def exact(*names):
        """完全相等才算。pick() 是「包含」比對，`pick("Average")` 會先撞上
        `PreviousAveragePrice`，把昨天的價格當成今天的收盤——靜默且每列都錯。"""
        for n in names:
            for k in keys:
                if str(k).strip() == n:
                    return k
        return None

    # 成交筆數不可用 pick("Transaction")，會撞上 TransactionVolume（成交量）
    k_tx = exact("成交筆數", "NumberOfTransactions", "Transactions", "Transaction")
    if not (k_code and k_c):
        return [], f"欄位對不上：{keys}"
    out = []
    for r in rows:
        code = str(r.get(k_code, "")).strip()
        if not code or not code[0].isdigit():
            continue
        o, h, l, c = (_num(r.get(k_o)), _num(r.get(k_h)),
                      _num(r.get(k_l)), _num(r.get(k_c)))
        if not c:
            continue
        chg = _num(r.get(k_chg))
        lim = ""
        if o and h and l and c and o == h == l == c:
            lim = "up" if (chg and float(chg) > 0) else ("down" if chg else "flat")
        out.append([f"{day}_{code}", day, code, str(r.get(k_name, "")).strip(), market,
                    o, h, l, c, _num(r.get(k_v)), _num(r.get(k_a)), chg, lim, "",
                    _num(r.get(k_tx)) if k_tx else "", ""])
    return out, f"欄位={keys}"


def fetch_day_market(day, market, urls, probe_lines=None):
    """回傳 (lines, note)。休市或查無回 ([], 'closed')；全失敗回 ([], 'all_failed:<原因>')。

    ★ 「日期不符」與「失敗」要分開回報（wrong_day vs all_failed）。
      2015 實測：17 個國定假日與颱風停市日，TWSE 乾脆回 stat=休市，
      但 TPEx 的端點會回「今天」的資料。日期核對擋下來了，**但那不是故障**，
      而是非交易日的正常表現。混在一起記成「失敗」，這 17 天會被永遠當成
      待補、每次重跑都再敲一次，而且 audit 的休市計數會是 0——
      **而「休市 0」正是這次抓到污染的那個訊號，不能讓它被雜訊淹掉。**
    """
    last_err = ""
    wrong_day = ""
    for u in urls:
        raw, err = get(u)
        if err:
            last_err = err
            if probe_lines is not None:
                probe_lines.append(f"  FAIL {u}\n        {err}")
            continue
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if probe_lines is not None:
                probe_lines.append(f"  BADJSON {u}\n        {type(e).__name__}")
            continue
        if isinstance(d, list):
            lines, note = parse_openapi(d, day, market)
            if not lines and str(note).startswith("no_rows"):
                if probe_lines is not None:
                    probe_lines.append(f"  OK   {u}\n        {note}")
                return [], "closed"
        else:
            stat = d.get("stat")
            # ★ 大小寫不敏感：TPEx 回的是小寫 "ok"，寫死 != "OK" 會把通的端點判成休市
            #   （2026-09-02 實測，上櫃回補因此整批被跳過）。
            if stat and str(stat).strip().lower() not in ("ok", "success"):
                if probe_lines is not None:
                    probe_lines.append(f"  OK   {u}\n        stat={stat}（休市／查無）")
                return [], "closed"
            same, said = _same_day(d, day)
            if not same:
                last_err = f"回應的日期是 {said}，不是 {day}"
                wrong_day = said
                if probe_lines is not None:
                    probe_lines.append(f"  OK   {u}\n        ✗ {last_err}")
                continue           # 換下一條，絕不採用
            lines, note = parse_twse(d, day, market)
            if not lines and str(note).startswith("no_rows"):
                if probe_lines is not None:
                    probe_lines.append(f"  OK   {u}\n        {note}")
                return [], "closed"
        if probe_lines is not None:
            probe_lines.append(f"  OK   {u}\n        bytes={len(raw)}\n"
                               f"        {note}\n        解析出 {len(lines)} 列")
            if not lines:
                # ★ 「連得上但解析出 0 列」是最需要診斷的情況——
                #   把實際結構印出來，下一輪才有東西可以照著改，不必用猜的。
                probe_lines.append(f"        [診斷] 頂層型別={type(d).__name__}")
                if isinstance(d, dict):
                    probe_lines.append(f"        [診斷] 頂層鍵={list(d.keys())[:15]}")
                    for k, v in list(d.items())[:8]:
                        if isinstance(v, list) and v:
                            probe_lines.append(
                                f"        [診斷] {k}: list[{len(v)}]，首筆="
                                f"{json.dumps(v[0], ensure_ascii=False)[:300]}")
                elif isinstance(d, list) and d:
                    probe_lines.append(
                        f"        [診斷] 首筆={json.dumps(d[0], ensure_ascii=False)[:300]}")
        if lines:
            return lines, u
        last_err = last_err or f"解析出 0 列（{note[:60]}）"
    # ★ 失敗原因一定要帶出去。只寫「失敗」的話，事後看 coverage 分不出是
    #   被限流（重跑就好）、端點改版（要改程式）、還是那天真的沒有資料。
    if wrong_day:
        return [], f"wrong_day:{wrong_day}"
    return [], f"all_failed:{last_err[:80]}"


def write_day(day, lines):
    kept = [r for r in lines if _kind(r[2]) != "warrant"]
    if not kept:
        return 0
    os.makedirs(DAILY_DIR, exist_ok=True)
    path = os.path.join(DAILY_DIR, f"{day}.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(HEADER) + "\n")
        for r in sorted(kept, key=lambda r: r[2]):
            f.write(",".join(str(x).replace(",", "") for x in r) + "\n")
    return len(kept)


def append_coverage(day, per_market, note):
    """★ 不完整的日子一定要留紀錄。

    某一天只抓到上市、沒抓到上櫃，如果不標，回測時會把「沒抓到」當成
    「上櫃股當天全部沒交易」——那是**靜默失真**，比整天缺資料還糟。
    """
    os.makedirs(UNI_DIR, exist_ok=True)
    # ★ 以日期為主鍵合併後整份重寫，**不可以用 "a" 純追加**。
    #   2026-09-03 實測：同一天重跑三次就留下三列（2015-01-01 出現 3 次），
    #   而且檔案不是排序的。read_coverage() 取最後一筆所以判斷還是對的，
    #   但檔案本身會越長越髒，任何直接讀它的人（例如之後建 DB）都會重複計算。
    old = {}
    if os.path.exists(COVERAGE):
        with open(COVERAGE, encoding="utf-8") as f:
            for i, ln in enumerate(f):
                q = ln.rstrip("\n").split(",")
                if i and q and q[0][:1].isdigit():
                    old[q[0]] = q
    old[day] = [day, str(per_market.get("twse", 0)), str(per_market.get("tpex", 0)),
                str(per_market.get("emerging", 0)), str(sum(per_market.values())),
                str(note)]
    with open(COVERAGE, "w", encoding="utf-8") as f:
        f.write(",".join(COV_HEADER) + "\n")
        for k in sorted(old):
            f.write(",".join(old[k]) + "\n")


def read_coverage():
    """→ {date: note}。沒有檔案就回空。"""
    out = {}
    if not os.path.exists(COVERAGE):
        return out
    with open(COVERAGE, encoding="utf-8") as f:
        for i, ln in enumerate(f):
            q = ln.rstrip("\n").split(",")
            if i and q and q[0][:1].isdigit():
                out[q[0]] = q[5] if len(q) > 5 else ""
    return out


def done_days():
    """真的可以跳過的日期。**三個條件都要看，少一個就會留下靜默的洞。**

    1. 檔案存在 —— 最基本的
    2. **欄位是現行版本** —— HEADER 加欄位時舊檔會少一截。只看檔案在不在，
       那些舊檔會永遠停在舊格式，等到建 DB 才發現有一半的日子對不上。
    3. **coverage 的 note 裡沒有「失敗」** —— 這一條是 2026-09-03 補的。
       某個市場失敗時，另一個市場的列**照樣會寫成檔案**（例：2015-07-15
       只有上櫃 675 列、上市整批沒抓到）。只看檔案存不存在的話，
       重跑會直接跳過它，**那一天的上市資料就永遠補不回來**，
       而且回測讀起來像「那天上市股全部沒交易」，不像「沒抓到」。

    全市場都休市的日子沒有檔案，但那是正常的，也要算跑過，否則每次重跑
    都會再去敲一次那些國定假日。
    """
    cov = read_coverage()
    files, stale = set(), 0
    want = ",".join(HEADER)
    if os.path.isdir(DAILY_DIR):
        for n in os.listdir(DAILY_DIR):
            if not n.endswith(".csv"):
                continue
            try:
                with open(os.path.join(DAILY_DIR, n), encoding="utf-8") as f:
                    head = f.readline().rstrip("\n")
            except OSError:
                continue
            if head == want:
                files.add(n[:-4])
            else:
                stale += 1
    ok, partial = set(), 0
    for d in files:
        note = cov.get(d, "")
        if "失敗" in note:
            partial += 1            # 有檔案，但缺了某個市場 → 要重抓
        else:
            ok.add(d)
    for d, note in cov.items():
        if d not in files and "失敗" not in note and "休市" in note:
            ok.add(d)               # 全市場休市，沒有檔案是正常的
    if stale:
        print(f"[backfill] {stale} 個日檔是舊欄位版本，將重抓覆蓋")
    if partial:
        print(f"[backfill] {partial} 天有市場抓失敗（檔案不完整），將重抓覆蓋")
    return ok


def daterange(start, end, saturdays=False):
    """交易日候選。週日一定跳過；週六預設也跳過。

    ★ 已知風險（2026-09-03 記，**尚未驗證**）：台股偶有**補行交易日**落在週六。
      預設跳過週六的話，那一天會整天沒有資料，而且在檔案裡看起來就像
      「那天沒開盤」——與真正的休市無法分辨。
      → 每一年回補完之後，用 `--saturdays` 單獨掃一次該年的週六（約 52 天、
        多數會回休市），或拿一檔已驗證的長序列做交易日曆核對
        （見 `tw-technical-analysis` 回測方法論第四條）。
    """
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    while d0 <= d1:
        wd = d0.weekday()
        if wd < 5 or (saturdays and wd == 5):
            yield d0.isoformat()
        d0 += timedelta(days=1)


# ══════════════════════════════════════════════════════════
# 興櫃逐檔逐月回補（2026-09-02 定案）
#
# `emerging/historical?type=Monthly&date=YYYY/MM/01&code=<代號>` 可用；
# **`type=Daily` 不可用**——它強制要 code，沒有全市場模式
# （回「請輸入資料日期及股票代碼查詢個股行情」）。
# 所以興櫃只能挑幾檔補，364 檔全補要 48,000 個請求。
#
# ★★ 回傳的表**沒有欄位名**，欄位是靠算術反推的：
#    ["115/08/03","28,863","1,650,513","57.70","56.40","57.18","43", …]
#    1,650,513 ÷ 28,863 = 57.18 → 第 6 欄確定是**加權平均價**（另兩列也吻合）。
#    → 日期／成交股數／成交金額／最高／最低／均價／成交筆數
#
# ★★★ **興櫃沒有開盤與收盤價**（非集合競價、無漲跌幅限制），
#      所以 close 欄放的是**均價**，open 留空、limit 留空。
#      這件事一定要標明——把均價當收盤跟上市股混算，那是兩種不同的東西。
# ══════════════════════════════════════════════════════════

ESB_DIR = os.path.join(UNI_DIR, "esb")
ESB_HEADER = ["date", "stock_id", "high", "low", "avg_price",
              "volume", "amount", "transactions", "price_basis"]


def roc_to_ad(d):
    """115/08/03 -> 2026-08-03。轉不了回 None（不要猜）。"""
    try:
        y, m, dd = str(d).strip().split("/")
        return f"{int(y) + 1911:04d}-{int(m):02d}-{int(dd):02d}"
    except Exception:  # noqa: BLE001
        return None


def parse_esb_month(d, code):
    """→ (lines, note)。欄位靠位置，因為回傳沒有 fields。"""
    tabs = _tables(d)
    if not tabs:
        return [], f"沒有 tables；頂層鍵={list(d.keys())[:10] if isinstance(d, dict) else type(d).__name__}"
    rows = tabs[0].get("data") or []
    out = []
    for r in rows:
        if not r or len(r) < 7:
            continue
        day = roc_to_ad(r[0])
        if not day:
            continue
        vol, amt = _num(r[1]), _num(r[2])
        hi, lo, avg = _num(r[3]), _num(r[4]), _num(r[5])
        # ★ 無成交日：交易所照樣給一列，價格與量全部填 0（2026-09-02 實測：
        #   5267 有 753 列、6434 有 311 列是這種）。**不可以留成 0**——
        #   回測讀到「均價 0」會算出 -100% 報酬，而且完全不會報錯。
        #   也不整列丟掉：那一天市場有開、這檔沒成交，本身就是流動性訊號。
        #   → 價格欄留空、price_basis 標「無成交」，讓下游只能明確處理、不能誤用。
        # ★ 判空要用「轉成數字後是不是 0」，不能寫 `if not avg`——
        #   _num() 回傳的是字串，"0.00" 是 truthy，這個坑踩過一次。
        if _isz(avg):
            out.append([day, code, "", "", "", "0", "0", _num(r[6]) or "0", "無成交"])
            continue
        out.append([day, code, hi, lo, avg, vol, amt, _num(r[6]), "均價"])
    return out, f"{len(rows)} 列原始、{len(out)} 列可用"


def merge_esb(code, lines):
    """一檔一檔存（興櫃只補少數幾檔，不會有 git 膨脹問題）。主鍵 date，冪等。"""
    os.makedirs(ESB_DIR, exist_ok=True)
    path = os.path.join(ESB_DIR, f"{code}.csv")
    old = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for i, ln in enumerate(f):
                q = ln.rstrip("\n").split(",")
                if i and q and q[0][:1].isdigit():
                    old[q[0]] = q
    added = 0
    for r in lines:
        if r[0] not in old:
            added += 1
        old[r[0]] = [str(x) for x in r]
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(ESB_HEADER) + "\n")
        for k in sorted(old):
            f.write(",".join(old[k]) + "\n")
    return len(old), added


def months(start, end):
    """'2015-01' ~ '2026-09' -> ['2015/01', ...]"""
    y, m = (int(x) for x in start.split("-")[:2])
    ey, em = (int(x) for x in end.split("-")[:2])
    while (y, m) <= (ey, em):
        yield f"{y:04d}/{m:02d}"
        m += 1
        if m > 12:
            y, m = y + 1, 1


def cmd_esb(args):
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    if not codes:
        print("[esb] 沒有指定 --codes", file=sys.stderr)
        return 1
    ms = list(months(args.start, args.end))
    print(f"[esb] {len(codes)} 檔 × {len(ms)} 個月 = {len(codes) * len(ms)} 個請求")
    for code in codes:
        got, empty, fail = [], 0, 0
        for ym in ms:
            raw, err = get(esb_month_url(code, ym))
            if err:
                fail += 1
                time.sleep(SLEEP)
                continue
            try:
                d = json.loads(raw.decode("utf-8"))
            except Exception:  # noqa: BLE001
                fail += 1
                time.sleep(SLEEP)
                continue
            lines, _note = parse_esb_month(d, code)
            if lines:
                got.extend(lines)
            else:
                empty += 1               # 該月沒交易或還沒上興櫃，正常
            time.sleep(SLEEP)
        total, added = merge_esb(code, got)
        notrade = sum(1 for r in got if r[8] == "無成交")
        print(f"  {code}: 抓到 {len(got)} 列（有成交 {len(got) - notrade}、"
              f"無成交 {notrade}；新增 {added}，累計 {total}）"
              f"｜空月 {empty}｜失敗 {fail}", flush=True)
    return 0


META_DIR = os.path.join(_ROOT, "meta")
STOCKS_HEADER = ["stock_id", "name", "market", "kind", "first_seen", "last_seen"]


INST_HEADER = ["date", "stock_id", "foreign", "trust", "dealer", "total"]


def inst_url(day):
    """上市全市場三大法人（T86）。**吃 date 參數，所以可以逐日回補。**

    2026-09-03 實測 date=20260903：16,833 列、19 欄，`stat=OK`。
    列數遠多於上市檔數是因為**含權證**，用 `_kind()` 濾掉即可。
    驗算：外陸資 ＋ 外資自營 ＋ 投信 ＋ 自營商 ＝ 三大法人合計，前 500 列 0 筆不符。
    """
    return ("https://www.twse.com.tw/rwd/zh/fund/T86"
            f"?date={day.replace('-', '')}&selectType=ALL&response=json")


def _known_codes():
    """`data/meta/stocks.csv` 裡的代號集合。拿來當 T86 的白名單。

    ★ 不能用 `_kind()` 濾權證：那條規則認的是「6 碼開頭 7」（上櫃權證），
      **上市權證是 03xxxx／04xxxx 之類**，濾不掉。2026-09-03 實測 T86 回 16,833 列，
      其中只有約 1,360 檔是我們要的上市證券，其餘全是權證。
      用 universe 已經整理好的清單當白名單，比再猜一次代號規則可靠。
    """
    path = os.path.join(_ROOT, "meta", "stocks.csv")
    out = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for i, ln in enumerate(f):
                if i:
                    q = ln.split(",")
                    if q and q[0]:
                        out.add(q[0].strip())
    return out


def parse_inst(d, day, known=None):
    """→ (lines, note)。欄位靠名稱找，**不寫死位置**——欄名改過版就會整批錯位。"""
    tabs = _tables(d)
    if not tabs:
        return [], f"沒有 tables；頂層鍵={list(d.keys())[:10] if isinstance(d, dict) else type(d).__name__}"
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    def ex(*names):
        """★ 這裡一定要**完全相等**比對，不可以用「包含」。
        T86 的欄名互相包含，用 `_idx()`（all(k in f)）會全部撞在一起：
          「外資自營商」 命中『外陸資買賣超股數(**不含外資自營商**)』→ 外資被算兩次
          「自營商買賣超股數」 命中『**外資自營商買賣超股數**』→ 自營商取到外資自營商
        2026-09-03 實測：16,833 列裡有 16,394 列因此驗算不符被丟掉，只剩 439 列。
        """
        for n in names:
            for i, f in enumerate(fields):
                if f.strip() == n:
                    return i
        return None

    i_code = ex("證券代號", "股票代號", "代號")
    # 外資分兩欄（外陸資、外資自營商），要相加才是完整外資
    i_f1 = ex("外陸資買賣超股數(不含外資自營商)", "外資買賣超股數")
    i_f2 = ex("外資自營商買賣超股數")
    i_tr = ex("投信買賣超股數")
    # ★ 自營商取「合計」那一欄，不是自行買賣或避險的分項
    i_dl = ex("自營商買賣超股數")
    i_tt = ex("三大法人買賣超股數")
    if any(x is None for x in (i_code, i_tr, i_tt)):
        return [], f"欄位對不上：{fields}"
    out, bad = [], 0
    for r in (t.get("data") or []):
        if not r or len(r) <= i_tt:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue                      # 權證與非 universe 標的
        g = lambda i: float(_num(r[i]) or 0) if i is not None else 0.0
        fo = g(i_f1) + g(i_f2)
        tr, dl, tt = g(i_tr), g(i_dl), g(i_tt)
        if abs(fo + tr + dl - tt) > 1:      # 恆等式，不符就丟掉那一列並回報
            bad += 1
            continue
        out.append([day, code, f"{fo:.0f}", f"{tr:.0f}", f"{dl:.0f}", f"{tt:.0f}"])
    return out, f"{len(out)} 列可用（驗算不符丟棄 {bad} 列）"


def write_inst(day, lines):
    if not lines:
        return 0
    os.makedirs(INST_DIR, exist_ok=True)
    with open(os.path.join(INST_DIR, f"{day}.csv"), "w", encoding="utf-8") as f:
        f.write(",".join(INST_HEADER) + "\n")
        for r in sorted(lines, key=lambda r: r[1]):
            f.write(",".join(r) + "\n")
    return len(lines)


def cmd_inst(args):
    """全市場三大法人逐日回補（上市）。上櫃另有端點，本模式尚未涵蓋。"""
    global SLEEP
    if args.sleep:
        SLEEP = args.sleep
    done = set()
    if os.path.isdir(INST_DIR):
        done = {n[:-4] for n in os.listdir(INST_DIR) if n.endswith(".csv")}
    days = [d for d in daterange(args.start, args.end, args.saturdays) if d not in done]
    if args.limit:
        days = days[:args.limit]
    print(f"[inst] {args.start} ~ {args.end}｜待處理 {len(days)} 天"
          f"（已存在 {len(done)} 天，略過）")
    known = _known_codes()
    if not known:
        print("[inst] 找不到 data/meta/stocks.csv，先跑 fetch.py 或 --rebuild-meta",
              file=sys.stderr)
        return 1
    print(f"[inst] universe 白名單 {len(known)} 檔")
    ok = closed = failed = 0
    streak = 0
    for i, day in enumerate(days, 1):
        if streak >= 3:
            cool = min(30 * 2 ** (streak - 3), 300)
            print(f"    連續失敗 {streak} 次，冷卻 {cool}s", flush=True)
            time.sleep(cool)
        raw, err = get(inst_url(day))
        note = ""
        if err:
            failed += 1; streak += 1; note = f"失敗({err[:60]})"
        else:
            try:
                d = json.loads(raw.decode("utf-8"))
            except Exception as ex:          # noqa: BLE001
                # ★ 不要只印 JSONDecodeError——那句話不帶任何可以往下查的資訊。
                #   把原始回應的開頭照抄出來，才看得出是 HTML 錯誤頁、被擋、還是空回應。
                head = raw[:160].decode("utf-8", "replace").replace("\n", " ")
                failed += 1; streak += 1
                note = f"JSON {type(ex).__name__}｜{len(raw)}B｜開頭：{head}"
                d = None
            if d is not None:
                stat = d.get("stat") if isinstance(d, dict) else None
                same, said = _same_day(d, day)
                if stat and str(stat).strip().lower() not in ("ok", "success"):
                    closed += 1; streak = 0; note = "休市"
                elif not same:
                    closed += 1; streak = 0; note = f"日期不符({said})"
                else:
                    lines, nt = parse_inst(d, day, known)
                    n = write_inst(day, lines)
                    if n:
                        ok += 1; streak = 0; note = f"{n} 列"
                    else:
                        closed += 1; streak = 0; note = f"0 列（{nt}）"
        if i % 20 == 0 or not note.endswith("列"):
            print(f"  [{i}/{len(days)}] {day} {note}", flush=True)
        # ★ 一開始就連續失敗代表端點或參數不對，不是隨機故障——繼續跑只是燒時間。
        #   一天失敗最壞要 3 次重試 ×45s 逾時 ＋ 退避 ≈ 144 秒，再加上冷卻最多 300 秒，
        #   等於**每天 7 分鐘**。放著跑一小時也只會前進十幾天，而且全是錯的。
        #   （2026-09-03 實測：699 天全 JSONDecodeError，使用者 8 分鐘後才發現。）
        if failed >= 5 and ok == 0:
            print(f"[inst] 前 {i} 天全部失敗且無一成功，收手——先確認端點與參數，"
                  f"不要放著跑。最後一則：{note}", file=sys.stderr)
            break
        time.sleep(SLEEP)
    print(f"[inst] 完成：有資料 {ok} 天、休市 {closed} 天、失敗 {failed} 天")
    return 0


def cmd_rebuild_meta(_args):
    """掃過所有日檔，重建 data/meta/stocks.csv 的 first_seen／last_seen。

    ★ 為什麼非做不可：`fetch.py` 只在每日流程裡更新 stocks.csv，
      **回補寫進來的十年資料它一列都沒看過**。所以回補完之後，
      stocks.csv 裡每一檔的 first_seen 都還是資料庫開張那天。

      而 first_seen／last_seen 正是**生存者偏差**的解藥：回測到 2018 年時，
      universe 必須是「當時真的存在的那些股票」，不是今天還活著的這批。
      欄位在、值卻是假的，比沒有這個欄位更危險。

    只讀本地檔，不連外。
    """
    if not os.path.isdir(DAILY_DIR):
        print("[meta] 沒有 daily 目錄")
        return 1
    files = sorted(n for n in os.listdir(DAILY_DIR) if n.endswith(".csv"))
    seen = {}
    for n in files:
        day = n[:-4]
        with open(os.path.join(DAILY_DIR, n), encoding="utf-8") as f:
            head = f.readline().rstrip("\n").split(",")
            try:
                i_id, i_nm, i_mk = (head.index("stock_id"), head.index("name"),
                                    head.index("market"))
            except ValueError:
                print(f"  ⚠ {n} 欄位不符，跳過")
                continue
            for ln in f:
                q = ln.rstrip("\n").split(",")
                if len(q) <= i_mk or not q[i_id]:
                    continue
                code = q[i_id]
                if code in seen:
                    r = seen[code]
                    r[1] = q[i_nm] or r[1]      # 名稱以最新的為準
                    r[2] = q[i_mk] or r[2]      # 市場別同理（會轉板）
                    r[5] = day if day > r[5] else r[5]
                    r[4] = day if day < r[4] else r[4]
                else:
                    seen[code] = [code, q[i_nm], q[i_mk], _kind(code), day, day]
    # 權證不進資料庫（與 fetch.py 同一條規則）
    purged = [c for c in seen if seen[c][3] == "warrant"]
    for c in purged:
        del seen[c]
    os.makedirs(META_DIR, exist_ok=True)
    path = os.path.join(META_DIR, "stocks.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(STOCKS_HEADER) + "\n")
        for k in sorted(seen):
            f.write(",".join(seen[k]) + "\n")
    firsts = {}
    for r in seen.values():
        firsts[r[4][:4]] = firsts.get(r[4][:4], 0) + 1
    print(f"[meta] 掃了 {len(files)} 個日檔，寫出 {len(seen)} 檔（權證排除 {len(purged)}）")
    print("  first_seen 年份分布:", dict(sorted(firsts.items())))
    lasts = {}
    for r in seen.values():
        lasts[r[5][:4]] = lasts.get(r[5][:4], 0) + 1
    print("  last_seen  年份分布:", dict(sorted(lasts.items())),
          "← 最後一年以外的，就是**已下市／已轉板**的股票")
    return 0


def cmd_purge(args):
    """刪掉一個區間的日檔與 coverage 列。**確認資料被污染時用。**

    為什麼需要它：回補寫出來的檔案在格式上完全正常，錯的是「內容屬於別的日子」。
    這種檔案不能靠重跑覆蓋——只要 done_days() 認得它就會跳過。先刪乾淨再重跑。
    """
    lo, hi = args.start, args.end
    killed = 0
    if os.path.isdir(DAILY_DIR):
        for n in sorted(os.listdir(DAILY_DIR)):
            if n.endswith(".csv") and lo <= n[:-4] <= hi:
                os.remove(os.path.join(DAILY_DIR, n))
                killed += 1
    cov = {}
    if os.path.exists(COVERAGE):
        with open(COVERAGE, encoding="utf-8") as f:
            for i, ln in enumerate(f):
                q = ln.rstrip("\n").split(",")
                if i and q and q[0][:1].isdigit():
                    cov[q[0]] = q
    dropped = [d for d in cov if lo <= d <= hi]
    for d in dropped:
        del cov[d]
    with open(COVERAGE, "w", encoding="utf-8") as f:
        f.write(",".join(COV_HEADER) + "\n")
        for k in sorted(cov):
            f.write(",".join(cov[k]) + "\n")
    print(f"[purge] {lo} ~ {hi}：刪掉 {killed} 個日檔、{len(dropped)} 列 coverage")
    return 0


def cmd_audit(_args):
    """把 _coverage.csv 讀成一張表：哪一年幾天完整、幾天缺市場、缺哪個。

    **回測前一定要看這張表。** 缺市場的日子在檔案裡長得跟「那天沒交易」一模一樣。
    """
    cov = read_coverage()
    if not cov:
        print("[audit] 還沒有 _coverage.csv")
        return 1
    rows = {}
    if os.path.exists(COVERAGE):
        with open(COVERAGE, encoding="utf-8") as f:
            for i, ln in enumerate(f):
                q = ln.rstrip("\n").split(",")
                if i and q and q[0][:1].isdigit():
                    rows[q[0]] = q
    years = {}
    for d, note in sorted(cov.items()):
        y = d[:4]
        st = years.setdefault(y, {"ok": 0, "closed": 0, "fail": 0, "days": []})
        if "失敗" in note:
            st["fail"] += 1
            st["days"].append(d)
        elif "休市" in note and str(rows.get(d, ["", "", "", "", "0"])[4]) in ("0", ""):
            st["closed"] += 1
        else:
            st["ok"] += 1
    print(f"{'年':<6}{'完整':>6}{'休市':>6}{'缺市場':>8}")
    for y in sorted(years):
        st = years[y]
        print(f"{y:<6}{st['ok']:>6}{st['closed']:>6}{st['fail']:>8}")
    bad = [d for y in sorted(years) for d in years[y]["days"]]
    if bad:
        print(f"\n缺市場的日子共 {len(bad)} 天，前 30 天：")
        for d in bad[:30]:
            print(f"  {d}  {cov[d]}")
        print("\n→ 直接重跑同一條 run 指令即可，done_days() 會只挑這些天。")
    return 0


def cmd_probe(args):
    day = args.date
    lines = [f"# 回補端點偵察 {datetime.now(TPE).isoformat(timespec='seconds')}  測試日 {day}"]
    summary = {}
    for market, urls in candidates(day).items():
        lines.append(f"\n== {market}")
        rows, src = fetch_day_market(day, market, urls, probe_lines=lines)
        summary[market] = len(rows)
        lines.append(f"  → 採用：{src if rows else '（無可用端點）'}")
    # 興櫃逐檔逐月（使用者提供的端點）——單獨測一次，用 7879 與測試日的月份
    lines.append("\n== emerging(逐檔逐月，7879)")
    u = esb_month_url("7879", day[:7].replace("-", "/"))
    raw, err = get(u)
    if err:
        lines.append(f"  FAIL {u}\n        {err}")
    else:
        lines.append(f"  OK   {u}\n        bytes={len(raw)}")
        try:
            d = json.loads(raw.decode("utf-8"))
            lines.append(f"        頂層型別={type(d).__name__}")
            if isinstance(d, dict):
                lines.append(f"        頂層鍵={list(d.keys())[:15]}")
                for k, v in list(d.items())[:8]:
                    if isinstance(v, list) and v:
                        lines.append(f"        {k}: list[{len(v)}]，首筆="
                                     f"{json.dumps(v[0], ensure_ascii=False)[:400]}")
            elif isinstance(d, list) and d:
                lines.append(f"        首筆={json.dumps(d[0], ensure_ascii=False)[:400]}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"        JSON 解析失敗 {type(e).__name__}；前 300 字："
                         f"{raw[:300].decode('utf-8', 'replace')!r}")

    os.makedirs(UNI_DIR, exist_ok=True)
    with open(PROBE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n[probe] 結果：{summary}")
    print(f"[probe] 已寫入 {PROBE}")
    return 0 if any(summary.values()) else 1


def cmd_run(args):
    global SLEEP
    if args.sleep:
        SLEEP = args.sleep
    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    skip = done_days() if not args.force else set()
    days = [d for d in daterange(args.start, args.end, args.saturdays) if d not in skip]
    if args.limit:
        days = days[:args.limit]
    print(f"[backfill] {args.start} ~ {args.end}｜市場 {markets}｜"
          f"待處理 {len(days)} 天（已存在 {len(skip)} 天，略過）")
    ok = closed = failed = 0
    # ★ 連續失敗要真的退下來。245/261 天 twse 失敗（2026-09-03 實測）就是
    #   固定間隔硬打的下場——交易所擋人之後，每 1.5 秒再敲一次只是延長封鎖。
    streak = {m: 0 for m in markets}
    for i, day in enumerate(days, 1):
        per, notes, all_lines = {}, [], []
        for m in markets:
            urls = candidates(day)[m]
            if streak[m] >= 3:
                cool = min(30 * 2 ** (streak[m] - 3), 300)
                print(f"    {m} 已連續失敗 {streak[m]} 次，冷卻 {cool}s", flush=True)
                time.sleep(cool)
            rows, src = fetch_day_market(day, m, urls)
            # ★ coverage 要記「真的寫進檔案的列數」——權證會被 write_day 濾掉，
            #   這裡若記過濾前的數字，coverage 就對不上檔案本身。
            rows = [r for r in rows if _kind(r[2]) != "warrant"]
            per[m] = len(rows)
            if src == "closed":
                notes.append(f"{m}:休市")
            elif str(src).startswith("wrong_day"):
                notes.append(f"{m}:日期不符({str(src).split(':', 1)[1]})")
            elif str(src).startswith("all_failed"):
                why = str(src).split(":", 1)[1] if ":" in str(src) else ""
                why = why.replace(",", "；").replace("\n", " ").strip()
                notes.append(f"{m}:失敗({why})" if why else f"{m}:失敗")
            elif src in urls and urls.index(src) > 0:
                # 用到第 2、3 條候選要留痕跡：主力端點壞掉是要修的事，
                # 不能因為備援剛好也能跑就永遠不知道。
                notes.append(f"{m}#候選{urls.index(src) + 1}")
            # 日期不符不算連續失敗——那是非交易日，不是被限流
            streak[m] = streak[m] + 1 if str(src).startswith("all_failed") else 0
            all_lines.extend(rows)
            # 某個市場整條失敗多半是被限流 → 多等一下再打下一個，
            # 否則接下來的日子會連鎖失敗（2026-09-03 2015 回補實測到 twse 失敗）
            time.sleep(SLEEP * 4 if str(src).startswith("all_failed") else SLEEP)
        n = write_day(day, all_lines)
        note = ";".join(notes) or "ok"
        append_coverage(day, per, note)
        if n:
            ok += 1
        elif "休市" in note:
            closed += 1
        else:
            failed += 1
        if i % 20 == 0 or n == 0:
            print(f"  [{i}/{len(days)}] {day} 寫入 {n} 列（{note}）", flush=True)
    print(f"[backfill] 完成：有資料 {ok} 天、休市 {closed} 天、失敗 {failed} 天")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="只測端點，不寫資料")
    ap.add_argument("--inst", action="store_true",
                    help="全市場三大法人逐日回補（上市 T86），配 --start／--end")
    ap.add_argument("--rebuild-meta", dest="rebuild_meta", action="store_true",
                    help="用所有日檔重建 stocks.csv 的 first_seen／last_seen（只讀本地）")
    ap.add_argument("--purge", action="store_true",
                    help="刪掉 --start~--end 的日檔與 coverage 列（資料被污染時用）")
    ap.add_argument("--audit", action="store_true",
                    help="讀 _coverage.csv，列出每年完整／休市／缺市場的天數")
    ap.add_argument("--run", action="store_true", help="逐日回補")
    ap.add_argument("--date", default="2026-08-28", help="probe 用的測試日（要是交易日）")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="2015-12-31")
    ap.add_argument("--markets", default="twse,tpex,emerging")
    ap.add_argument("--limit", type=int, default=0, help="最多處理幾天（試跑用）")
    ap.add_argument("--force", action="store_true", help="已存在的日期也重抓")
    ap.add_argument("--saturdays", action="store_true",
                    help="連週六也掃（抓補行交易日；多數會回休市）")
    ap.add_argument("--sleep", type=float, default=0,
                    help="每個請求間隔秒數（預設 1.5；被限流就調大，例如 3）")
    ap.add_argument("--esb", action="store_true",
                    help="興櫃逐檔逐月回補（要配 --codes，start/end 用 YYYY-MM）")
    ap.add_argument("--codes", default="", help="興櫃代號，逗號分隔")
    a = ap.parse_args()
    if a.inst:
        return cmd_inst(a)
    if a.rebuild_meta:
        return cmd_rebuild_meta(a)
    if a.purge:
        return cmd_purge(a)
    if a.audit:
        return cmd_audit(a)
    if a.probe:
        return cmd_probe(a)
    if a.esb:
        return cmd_esb(a)
    if a.run:
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
