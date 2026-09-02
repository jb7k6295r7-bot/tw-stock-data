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
COVERAGE = os.path.join(UNI_DIR, "_coverage.csv")
PROBE = os.path.join(UNI_DIR, "_backfill_probe.txt")

HEADER = ["key", "date", "stock_id", "name", "market",
          "open", "high", "low", "close", "volume", "amount", "change", "limit",
          "shares"]
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
            f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&d={roc(day)}&o=json",
            f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
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
            f"https://www.tpex.org.tw/openapi/v1/tpex_esb_latest_statistics",
        ],
    }


def get(url, retries=2, timeout=45):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
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
            time.sleep(2 * (i + 1))
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
    return []


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
        i_chg = _idx_any(fields, "漲跌價差")
        i_sign = _idx_any(fields, ("漲跌", "+"), "漲跌(+/-)", "漲跌")
        if any(x is None for x in (i_code, i_o, i_h, i_l, i_c)):
            return [], f"欄位對不上：{fields}"
        out = []
        for r in (t.get("data") or []):
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
                        _num(r[i_sh]) if i_sh is not None else ""])
        return out, f"欄位={fields}"
    return [], "找不到含『證券代號』與『收盤』的表"


def parse_openapi(rows, day, market):
    if not isinstance(rows, list) or not rows:
        return [], "回傳不是非空 list"
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
                    o, h, l, c, _num(r.get(k_v)), _num(r.get(k_a)), chg, lim, ""])
    return out, f"欄位={keys}"


def fetch_day_market(day, market, urls, probe_lines=None):
    """回傳 (lines, note)。休市或查無回 ([], 'closed')。"""
    for u in urls:
        raw, err = get(u)
        if err:
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
        else:
            stat = d.get("stat")
            # ★ 大小寫不敏感：TPEx 回的是小寫 "ok"，寫死 != "OK" 會把通的端點判成休市
            #   （2026-09-02 實測，上櫃回補因此整批被跳過）。
            if stat and str(stat).strip().lower() not in ("ok", "success"):
                if probe_lines is not None:
                    probe_lines.append(f"  OK   {u}\n        stat={stat}（休市／查無）")
                return [], "closed"
            lines, note = parse_twse(d, day, market)
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
    return [], "all_failed"


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
    exists = os.path.exists(COVERAGE)
    with open(COVERAGE, "a", encoding="utf-8") as f:
        if not exists:
            f.write(",".join(COV_HEADER) + "\n")
        f.write("{},{},{},{},{},{}\n".format(
            day, per_market.get("twse", 0), per_market.get("tpex", 0),
            per_market.get("emerging", 0), sum(per_market.values()), note))


def done_days():
    if not os.path.isdir(DAILY_DIR):
        return set()
    return {n[:-4] for n in os.listdir(DAILY_DIR) if n.endswith(".csv")}


def daterange(start, end):
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    while d0 <= d1:
        if d0.weekday() < 5:              # 週末直接跳過，不浪費請求
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
    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    skip = done_days() if not args.force else set()
    days = [d for d in daterange(args.start, args.end) if d not in skip]
    if args.limit:
        days = days[:args.limit]
    print(f"[backfill] {args.start} ~ {args.end}｜市場 {markets}｜"
          f"待處理 {len(days)} 天（已存在 {len(skip)} 天，略過）")
    ok = closed = failed = 0
    for i, day in enumerate(days, 1):
        per, notes, all_lines = {}, [], []
        for m in markets:
            rows, src = fetch_day_market(day, m, candidates(day)[m])
            # ★ coverage 要記「真的寫進檔案的列數」——權證會被 write_day 濾掉，
            #   這裡若記過濾前的數字，coverage 就對不上檔案本身。
            rows = [r for r in rows if _kind(r[2]) != "warrant"]
            per[m] = len(rows)
            if src == "closed":
                notes.append(f"{m}:休市")
            elif src == "all_failed":
                notes.append(f"{m}:失敗")
            all_lines.extend(rows)
            time.sleep(SLEEP)
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
    ap.add_argument("--run", action="store_true", help="逐日回補")
    ap.add_argument("--date", default="2026-08-28", help="probe 用的測試日（要是交易日）")
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default="2015-12-31")
    ap.add_argument("--markets", default="twse,tpex,emerging")
    ap.add_argument("--limit", type=int, default=0, help="最多處理幾天（試跑用）")
    ap.add_argument("--force", action="store_true", help="已存在的日期也重抓")
    ap.add_argument("--esb", action="store_true",
                    help="興櫃逐檔逐月回補（要配 --codes，start/end 用 YYYY-MM）")
    ap.add_argument("--codes", default="", help="興櫃代號，逗號分隔")
    a = ap.parse_args()
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
