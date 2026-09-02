#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台股資料抓取腳本 —— 在「你自己的」GitHub Actions 上執行。

為什麼存在：Claude 的排程在凌晨無人值守時，WebFetch 每一條網址都會跳核可對話框，
沒有人按就逾時，什麼都拿不到（2026-08-30 / 08-31 連續實測）。
這支腳本把「抓資料」搬到你自己這端——那是你本來就有權做的事——
Claude 的排程只讀這個 repo 產出的固定網址檔案。

設計原則（照專案的資料品質規範走）：
  1. 只用標準函式庫，不需要 pip install。
  2. 每一批資料都驗 stock_id 與日期，**驗不過就標 failed，絕不靜默填補**。
  3. 缺的就寫缺。任何欄位都不推估、不內插。
  4. 每個檔案都帶 meta（來源網址、抓取時間、筆數、最新日期），讓下游能自己複查。

輸出（**下游一律讀 CSV，不要讀 JSON**）：
  data/history/<代號>_price.csv    日K（append-only，這才是資料庫）
  data/history/<代號>_inst.csv     三大法人，一天一列
  data/history/<代號>_per.csv      本益比／股價淨值比／殖利率   ← v6
  data/history/<代號>_revenue.csv  月營收                        ← v6
  data/history/<代號>_margin.csv   融資融券餘額                  ← v6
  data/history/<代號>_capital.csv  股本（找得到才有）            ← v6
  data/history/market_*.csv        大盤指數／漲跌家數／成交統計  ← v6
  data/latest/*.csv                以上各檔的最後 300 列（報告讀這裡）
  data/latest/market_tables_raw.txt TWSE 各表的欄位偵察檔        ← v6
  data/meta/<代號>_fs_types.txt    財報裡出現過的所有 type       ← v6
  data/latest/<代號>.json、market.json  原始回應，供回頭查
  data/latest/_manifest.json       這一輪的總表（誰成功誰失敗、基準日是哪天）

v6（2026-09-02）補的是「報告一直缺、每天都寫查無」的那幾項：
本益比／淨值比、月營收、融資融券、股本（→ 周轉率與法人佔股本比重），
以及大盤的指數、漲跌家數與成交統計。
**新項目全部做成「抓不到就記錯誤、不影響其他項」**——
第一次執行的 _manifest.json 會自己回答哪幾個 dataset 真的可用。
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

# ────────────────────────────────────────────────────────────
# 設定：要抓哪些股票
# 只放代號。這裡不放持股成本、張數或任何個人資料——repo 是公開的。
# ────────────────────────────────────────────────────────────
STOCKS = [
    "7879",  # 益材科技（興櫃）
    "8289",  # 泰藝
    "2609",  # 陽明
    "6209",  # 今國光
    "3017",  # 奇鋐
    "8996",  # 高力
]

PRICE_START = "2025-01-01"   # 日K起日：要夠長才算得出 240MA
INST_START = "2026-01-01"    # 三大法人起日

TPE = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; tw-stock-data/1.0; +https://github.com/)"
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_DIR = os.path.join(_ROOT, "latest")      # 最近視窗的快照，報告讀這裡
HIST_DIR = os.path.join(_ROOT, "history")    # 累積歷史，**只增不減**，這才是資料庫
DIV_DIR = os.path.join(_ROOT, "dividend")    # 除權息事件（抓得到才有）
CHANGES = os.path.join(_ROOT, "_changes.log")
CALENDAR = os.path.join(_ROOT, "calendar.csv")

# latest 只放最近這麼多個交易日。**目的是把檔案做小**——
# 下游用 WebFetch 讀，大檔會被截斷而且會被憑空補齊（2026-08-31 實測）。
LATEST_WINDOW = 300

# 除權息事件的 dataset 名稱。**這是一個尚未在本環境驗證過的假設**，
# 所以做成「抓不到就記錯誤、不影響其他項」——讓第一次執行自己回答可不可用，
# 不要我在這裡猜完就當成事實。可用性確認後再寫進 tw-data-sources。
DIVIDEND_DATASET = "TaiwanStockDividend"

# ── v6（2026-09-02）新增的 dataset：一次把「報告一直缺的那幾項」補起來 ──
# 每一項都做成**抓不到就記錯誤、不影響其他項**，讓第一次執行自己回答可不可用，
# 不要在這裡猜完就當成事實（專案工作方法第 3、4 條）。
#
#   per      每日本益比／股價淨值比／殖利率 → 報告的 pe_pb 與 data/valuation 不必再另外抓
#   revenue  月營收 → C1 基本面
#   margin   融資融券餘額 → 融資水位、券資比、槓桿風險
#   fs       財務報表 → 財報警示三條，**同時用來找「股本」**（在外流通股數目前完全查無，
#            導致周轉率與法人佔股本比重每天都寫「查無」）
EXTRA_DATASETS = {
    "per":     "TaiwanStockPER",
    "revenue": "TaiwanStockMonthRevenue",
    "margin":  "TaiwanStockMarginPurchaseShortSale",
    "fs":      "TaiwanStockFinancialStatements",
}

# 財報裡「股本」可能的 type 名稱。**不確定 FinMind 用哪一個**，所以列一組候選，
# 並且把當次看到的所有 type 另外寫成檔案（見 FS_TYPES_FILE）——
# 對不上時不要靜默放棄，要留下證據讓下次能查（與 inst_unknown_names 同一個設計）。
_CAPITAL_TYPES = {"CommonStocks", "CommonStock", "CapitalStock", "Capital",
                  "股本", "普通股股本", "OrdinaryShare"}

META_DIR = os.path.join(_ROOT, "meta")

FINMIND = "https://api.finmindtrade.com/api/v4/data"
TWSE = "https://www.twse.com.tw/rwd/zh"


def now_tpe():
    return datetime.now(TPE)


def get(url, retries=3, timeout=30):
    """回傳 (bytes, error)。失敗不丟例外，讓呼叫端決定怎麼記錄。

    ★ HTTPError 要把**狀態碼與回應內容的開頭**一起記下來（2026-08-31 加）。
      只記 `HTTP Error 400: Bad Request` 這種字串，看不出是額度用完、要 token、
      還是參數不合——那三種的處理方式完全不同。伺服器通常會在 body 裡講清楚。
    """
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:  # noqa: BLE001
                body = "(讀不到 body)"
            last = f"HTTP {e.code} {e.reason} | body: {body}"
            # 4xx 重試沒有意義（額度、權限、參數錯），直接放棄
            if 400 <= e.code < 500 and e.code not in (408, 429):
                return None, last
        except Exception as e:  # noqa: BLE001 — 這裡就是要吞下所有錯並記錄
            last = f"{type(e).__name__}: {e}"
        if i < retries - 1:
            time.sleep(2 * (i + 1))
    return None, last


def get_json(url, **kw):
    raw, err = get(url, **kw)
    if err:
        return None, err
    try:
        return json.loads(raw.decode("utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, f"JSON 解析失敗 {type(e).__name__}: {e}"


def finmind(dataset, data_id, start, end):
    url = (f"{FINMIND}?dataset={dataset}&data_id={data_id}"
           f"&start_date={start}&end_date={end}")
    d, err = get_json(url)
    if err:
        return None, url, err
    if not isinstance(d, dict) or d.get("msg") != "success":
        # 把整個回應的開頭留下來——FinMind 會在 msg 裡寫明原因（額度、token、參數）
        return None, url, f"回傳非 success：{str(d)[:300]}"
    rows = d.get("data") or []
    if not rows:
        return None, url, "回傳 0 筆"
    return rows, url, None


def check_stock_id(rows, code):
    """逐筆核對代號。這是唯一能擋住『張冠李戴』的防線，不可省。"""
    bad = {str(r.get("stock_id")) for r in rows} - {str(code)}
    if bad:
        return f"stock_id 不符，出現 {sorted(bad)[:5]}"
    return None


def date_range(rows):
    ds = sorted(str(r.get("date", "")) for r in rows if r.get("date"))
    return (ds[0], ds[-1]) if ds else ("", "")


def fetch_stock(code, today):
    """單一檔股票。任何一項失敗都照實記錄，不影響其他項。"""
    out = {
        "stock_id": code,
        "fetched_at": now_tpe().isoformat(timespec="seconds"),
        "price": None,
        "institutional": None,
        "dividend": None,
        "errors": {},
    }

    rows, url, err = finmind("TaiwanStockPrice", code, PRICE_START, today)
    if err:
        out["errors"]["price"] = err
    else:
        bad = check_stock_id(rows, code)
        if bad:
            out["errors"]["price"] = bad          # 整批丟棄，不是只換欄位
        else:
            lo, hi = date_range(rows)
            out["price"] = {
                "source": url, "rows": len(rows),
                "date_min": lo, "date_max": hi, "data": rows,
            }

    rows, url, err = finmind(
        "TaiwanStockInstitutionalInvestorsBuySell", code, INST_START, today)
    if err:
        out["errors"]["institutional"] = err
    else:
        bad = check_stock_id(rows, code)
        if bad:
            out["errors"]["institutional"] = bad
        else:
            lo, hi = date_range(rows)
            out["institutional"] = {
                "source": url, "rows": len(rows),
                "date_min": lo, "date_max": hi, "data": rows,
            }

    # 除權息事件（可選）。**這個 dataset 名稱尚未在本環境驗證過**，
    # 所以抓不到只記錯誤、不影響其他項——讓第一次執行自己回答可不可用。
    rows, url, err = finmind(DIVIDEND_DATASET, code, PRICE_START, today)
    if err:
        out["errors"]["dividend"] = err
    else:
        out["dividend"] = {"source": url, "rows": len(rows), "data": rows}

    # ── v6：本益比／月營收／融資融券／財報。每一項獨立，失敗只記錯誤 ──
    # 起日各自不同：per 跟日K一樣長（要畫本益比河流圖也夠），
    # revenue 與 fs 要往前多拿一年才看得出年增與去年同期。
    starts = {"per": PRICE_START, "revenue": "2024-01-01",
              "margin": INST_START, "fs": "2024-01-01"}
    out["extra"] = {}
    for kind, dataset in EXTRA_DATASETS.items():
        rows, url, err = finmind(dataset, code, starts[kind], today)
        if err:
            out["errors"][kind] = err
            continue
        bad = check_stock_id(rows, code)
        if bad:
            out["errors"][kind] = bad          # 一樣是整批丟棄
            continue
        lo, hi = date_range(rows)
        out["extra"][kind] = {"source": url, "rows": len(rows),
                              "date_min": lo, "date_max": hi, "data": rows}

    return out


# ────────────────────────────────────────────────────────────
# 精簡 CSV 輸出（2026-08-31 加）
#
# 為什麼要有這個：下游用 WebFetch 讀檔，而 **WebFetch 對大檔會靜默截斷，
# 而且被要求「逐字輸出」時會憑空補齊到宣稱的筆數**（當日實測 77KB 的 3017.json：
# 價格段完整、籌碼段只到 1/8，後面全是 1234567、987654 這種湊出來的假數字）。
#
# 解法不是叫它「不要編」——那管不住——而是**把檔案做小**。
# 同一批資料，JSON 約 77KB，CSV 約 14KB，一次就讀得完，也就沒有補的餘地。
# JSON 仍然保留（完整、可回頭查），但**下游一律讀 CSV**。
# ────────────────────────────────────────────────────────────

# FinMind 的 name 欄位 → 三大類。
#
# 自營商有兩種寫法：上市櫃通常拆成 Dealer_self（自行買賣）＋ Dealer_Hedging（避險），
# **興櫃則是單一的 Dealer**（2026-08-31 由 7879 的 inst_unknown_names 發現）。
# ★ 兩種寫法**不可以同時累加**——那會把自營商算成兩倍。
#   所以 Dealer 只在「當天沒有出現拆開的那兩種」時才採用，邏輯在 inst_lines()。
_INST_MAP = {
    "Foreign_Investor": "foreign",
    "Foreign_Dealer_Self": "foreign",
    "Investment_Trust": "trust",
    "Dealer_self": "dealer",
    "Dealer_Hedging": "dealer",
}
_DEALER_SPLIT = {"Dealer_self", "Dealer_Hedging"}
_DEALER_TOTAL = "Dealer"

PRICE_HEADER = ["date", "open", "high", "low", "close", "volume"]
INST_HEADER = ["date", "foreign", "trust", "dealer", "total"]
PER_HEADER = ["date", "per", "pbr", "dividend_yield"]
REVENUE_HEADER = ["date", "revenue_year", "revenue_month", "revenue"]
MARGIN_HEADER = ["date", "margin_balance", "short_balance",
                 "margin_limit", "offset"]
CAPITAL_HEADER = ["date", "type", "value"]
MKT_INDEX_HEADER = ["date", "close", "change", "change_pct"]
MKT_BREADTH_HEADER = ["date", "up", "down", "flat", "limit_up", "limit_down"]
MKT_AMOUNT_HEADER = ["date", "trade_value", "trade_volume", "transactions"]
MKT_INST_HEADER = ["date", "foreign", "trust", "dealer", "total"]


def _read_csv(path):
    """回傳 (header, {鍵: [欄位…]})。檔案不存在就回 (None, {})。"""
    if not os.path.exists(path):
        return None, {}
    rows = {}
    header = None
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.rstrip("\n")
            if not line:
                continue
            if i == 0:
                header = line.split(",")
                continue
            parts = line.split(",")
            rows[parts[0]] = parts
    return header, rows


def merge_history(path, header, new_lines, tag):
    """把 new_lines（已是 CSV 欄位 list）併進 path。

    回傳 (total, added, changed)，changed 是 [(date, 舊列, 新列), ...]。
    **主鍵是第一欄（date）**，同一天重跑不會產生重複列——排程會重試，必須冪等。
    """
    old_header, old = _read_csv(path)
    if old_header is not None and old_header != header:
        # 欄位變了就不要硬併——那是結構改變，要人看過
        raise ValueError(f"{path} 的欄位與現行不符：{old_header} vs {header}")
    changed = []
    added = 0
    merged = dict(old)
    for parts in new_lines:
        k = parts[0]
        if k not in merged:
            merged[k] = parts
            added += 1
        elif merged[k] != parts:
            changed.append((k, merged[k], parts))
            merged[k] = parts
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for k in sorted(merged):
            f.write(",".join(str(x) for x in merged[k]) + "\n")
    if changed:
        with open(CHANGES, "a", encoding="utf-8") as f:
            for k, oldrow, newrow in changed:
                f.write("{}\t{}\t{}\t舊:{}\t新:{}\n".format(
                    now_tpe().isoformat(timespec="seconds"), tag, k,
                    ",".join(str(x) for x in oldrow),
                    ",".join(str(x) for x in newrow)))
    return len(merged), added, changed


def write_window(src_path, dst_path, n=LATEST_WINDOW):
    """把歷史檔的最後 n 列複製成 latest 的小檔。"""
    header, rows = _read_csv(src_path)
    if header is None:
        return 0
    keys = sorted(rows)[-n:]
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for k in keys:
            f.write(",".join(str(x) for x in rows[k]) + "\n")
    return len(keys)


def price_lines(rows):
    """FinMind 日K → CSV 欄位 list（已排序）。"""
    out = []
    for r in sorted(rows, key=lambda r: str(r.get("date", ""))):
        out.append([str(r.get("date", "")), str(r.get("open", "")),
                    str(r.get("max", "")), str(r.get("min", "")),
                    str(r.get("close", "")), str(r.get("Trading_Volume", ""))])
    return out


def inst_lines(rows):
    """FinMind 三大法人 → **一天一列**的 CSV 欄位 list。

    回傳 (lines, unknown_names)。未知的 name 會被回報，**不會被默默丟掉**。
    """
    # 先看每一天各自出現了哪些 name，才能決定自營商要用拆開的還是總計的
    names_by_day = {}
    for r in rows:
        d = str(r.get("date", ""))
        if d:
            names_by_day.setdefault(d, set()).add(str(r.get("name", "")))

    by_day, unknown = {}, set()
    for r in rows:
        d = str(r.get("date", ""))
        if not d:
            continue
        name = str(r.get("name", ""))
        if name == _DEALER_TOTAL:
            # 當天若已有拆開的自營商，總計那筆要跳過，否則自營商會被算兩次
            if names_by_day.get(d, set()) & _DEALER_SPLIT:
                continue
            col = "dealer"
        else:
            col = _INST_MAP.get(name)
        if col is None:
            unknown.add(name)
            continue
        try:
            net = int(r.get("buy", 0)) - int(r.get("sell", 0))
        except (TypeError, ValueError):
            continue
        day = by_day.setdefault(d, {"foreign": 0, "trust": 0, "dealer": 0})
        day[col] += net
    lines = []
    for d in sorted(by_day):
        v = by_day[d]
        lines.append([d, str(v["foreign"]), str(v["trust"]), str(v["dealer"]),
                      str(v["foreign"] + v["trust"] + v["dealer"])])
    return lines, sorted(unknown)


def _num(v):
    """TWSE／FinMind 的數字字串 → 純數字字串。轉不了就回空字串（**不填 0**）。

    填 0 會讓「沒有資料」看起來像「當天是 0」，那是靜默造假。
    """
    if v is None:
        return ""
    t = str(v).replace(",", "").replace("+", "").replace("%", "").strip()
    if t in ("", "-", "--", "X", "N/A"):
        return ""
    try:
        float(t)
    except ValueError:
        return ""
    return t


def extra_lines(kind, rows):
    """v6 的四個新 dataset → CSV 欄位 list。欄位名照抄 FinMind 的原始欄位。"""
    out = []
    for r in sorted(rows, key=lambda r: str(r.get("date", ""))):
        d = str(r.get("date", ""))
        if not d:
            continue
        if kind == "per":
            out.append([d, _num(r.get("PER")), _num(r.get("PBR")),
                        _num(r.get("dividend_yield"))])
        elif kind == "revenue":
            out.append([d, str(r.get("revenue_year", "")),
                        str(r.get("revenue_month", "")), _num(r.get("revenue"))])
        elif kind == "margin":
            out.append([d,
                        _num(r.get("MarginPurchaseTodayBalance")),
                        _num(r.get("ShortSaleTodayBalance")),
                        _num(r.get("MarginPurchaseLimit")),
                        _num(r.get("OffsetLoanAndShort"))])
    return out


def fs_capital_lines(rows):
    """財報 → 只抽「股本」那幾列，順便回報看到的所有 type。

    回傳 (lines, types_seen)。**對不上候選名單時不要靜默放棄**——
    types_seen 會被寫成檔案，下次照著改 _CAPITAL_TYPES 就好
    （與 inst_unknown_names 同一個設計：未知的要講出來）。
    """
    lines, types = [], set()
    for r in sorted(rows, key=lambda r: str(r.get("date", ""))):
        t = str(r.get("type", ""))
        types.add(t)
        if t in _CAPITAL_TYPES:
            d = str(r.get("date", ""))
            v = _num(r.get("value"))
            if d and v:
                lines.append([d, t, v])
    return lines, sorted(types)


# ────────────────────────────────────────────────────────────
# 大盤：從 market.json 抽成小 CSV（v6，2026-09-02）
#
# 為什麼要抽：market.json 裡的 T86 是全市場約 1,000 檔，檔案很大，
# **下游用 WebFetch 讀大檔會被截斷並憑空補齊**（規範第 14 條）。
# 所以大盤也照個股的作法：JSON 留著回頭查，另外產出一天一列的小 CSV。
#
# ★ TWSE 這幾張表的實際欄位順序**尚未在本環境驗證過**，所以：
#   1. 解析失敗只記錯誤，不影響其他項；
#   2. 不論成功失敗，都把表名與前幾列原樣寫進 market_tables_raw.txt，
#      讓下一次可以照著改，而不是靠猜。
# ────────────────────────────────────────────────────────────

def _twse_tables(d):
    """TWSE 的 json 有兩種形狀：新的 {"tables":[…]}、舊的 {"fields":…,"data":…}。"""
    if not isinstance(d, dict):
        return []
    if isinstance(d.get("tables"), list):
        return [t for t in d["tables"] if isinstance(t, dict)]
    if d.get("fields") and d.get("data"):
        return [{"title": d.get("title", ""), "fields": d["fields"], "data": d["data"]}]
    return []


def _dump_tables(market, path):
    """把所有表的標題、欄位名與前兩列寫成純文字。**這是給人看的偵察檔。**"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for key in ("index", "summary", "bfi82u"):
            blk = market.get(key)
            if not blk:
                f.write(f"== {key}: （未取得）\n")
                continue
            for t in _twse_tables(blk.get("data")):
                f.write(f"== {key} / {t.get('title', '')}\n")
                f.write(f"   fields: {t.get('fields')}\n")
                for row in (t.get("data") or [])[:2]:
                    f.write(f"   row: {row}\n")
        f.write("（本檔只供對欄位，解析穩定後可以不必再看）\n")


def _find_row(market, key, title_kw, row_kw):
    """在某個表裡找出第一欄含 row_kw 的那一列。找不到回 None。"""
    blk = market.get(key)
    if not blk:
        return None
    for t in _twse_tables(blk.get("data")):
        if title_kw and title_kw not in str(t.get("title", "")):
            continue
        for row in (t.get("data") or []):
            if row and row_kw in str(row[0]):
                return [str(x) for x in row]
    return None


def market_lines(market, day):
    """回傳 ({名稱: CSV 欄位 list}, errors)。抽不到的那一項就不放進 dict。"""
    out, errs = {}, {}

    r = _find_row(market, "index", "", "發行量加權股價指數")
    if r and len(r) >= 5:
        # [名稱, 收盤指數, 漲跌(+/-), 漲跌點數, 漲跌百分比]
        sign = -1 if "-" in r[2] else 1
        chg = _num(r[3])
        pct = _num(r[4])
        out["index"] = [day, _num(r[1]),
                        (str(sign * float(chg)) if chg else ""),
                        (str(sign * float(pct)) if pct else "")]
    else:
        errs["index"] = "找不到『發行量加權股價指數』那一列（欄位可能改了，看 market_tables_raw.txt）"

    # ★ 漲跌家數要取「股票」那一欄／那一列，**不是「整體市場」**——
    #   整體市場含權證與 ETF，數字會大很多（2026-09-01 三源不一致就是這個原因）。
    #   「股票」找不到才退而用整體市場，並且在 errs 裡講明用的是哪一個。
    r = _find_row(market, "summary", "漲跌證券數", "股票")
    if r is None:
        r = _find_row(market, "summary", "漲跌證券數", "整體市場")
        if r is not None:
            errs["breadth_scope"] = "找不到『股票』列，改用『整體市場』（含權證，偏大）"
    if r and len(r) >= 6:
        out["breadth"] = [day] + [_num(x) for x in r[1:6]]
    else:
        errs["breadth"] = "找不到漲跌證券數那一列"

    r = _find_row(market, "summary", "成交", "股票")
    if r and len(r) >= 4:
        # [項目, 成交股數, 成交筆數, 成交金額]
        out["amount"] = [day, _num(r[3]), _num(r[1]), _num(r[2])]
    else:
        errs["amount"] = "找不到成交統計的『股票』那一列"

    r = _find_row(market, "bfi82u", "", "外資")
    if r:
        errs.setdefault("inst", "BFI82U 有取得，但欄位對應尚未定案（看 market_tables_raw.txt）")
    elif "bfi82u" not in market:
        errs["inst"] = "BFI82U 未取得"

    return out, errs


def write_calendar(all_dates):
    """交易日曆：各檔日期集合的聯集。

    **用日期集合比對，不要用筆數。** 台股有颱風停市這類不規則缺口，
    比筆數會漏掉——這個專案已經踩過（見規範第 8 條）。
    """
    os.makedirs(os.path.dirname(CALENDAR), exist_ok=True)
    with open(CALENDAR, "w", encoding="utf-8") as f:
        f.write("date\n")
        for d in sorted(all_dates):
            f.write(d + "\n")
    return len(all_dates)


def fetch_market(today):
    """大盤：指數、成交統計、全市場三大法人。

    T86 經 WebFetch 會被靜默截斷（實測），從這裡抓則是完整的原始回應。
    """
    ymd = today.replace("-", "")
    out = {"fetched_at": now_tpe().isoformat(timespec="seconds"), "errors": {}}

    targets = {
        # 發行量加權股價指數（收盤指數與漲跌）
        "index": f"{TWSE}/afterTrading/MI_INDEX?date={ymd}&type=IND&response=json",
        # 成交金額、漲跌家數等大盤統計
        "summary": f"{TWSE}/afterTrading/MI_INDEX?date={ymd}&type=MS&response=json",
        # 全市場三大法人買賣超
        "t86": f"{TWSE}/fund/T86?date={ymd}&selectType=ALL&response=json",
        # 三大法人買賣金額總表
        "bfi82u": f"{TWSE}/fund/BFI82U?dayDate={ymd}&type=day&response=json",
    }
    for key, url in targets.items():
        d, err = get_json(url)
        if err:
            out["errors"][key] = err
            continue
        stat = (d or {}).get("stat")
        if stat and stat != "OK":
            # TWSE 對休市日／查無資料會回一段中文，照抄不改寫
            out["errors"][key] = f"stat={stat}"
            continue
        out[key] = {"source": url, "data": d}
    return out


def latest_trading_day_guess(now):
    """只用來決定要跟 TWSE 要哪一天，**不是**報告基準日的判定。

    真正的基準日以抓回來的資料為準（見 manifest 的 data_max）。
    """
    d = now
    if d.hour < 15:          # 當日收盤資料尚未齊全，往前一天
        d -= timedelta(days=1)
    while d.weekday() >= 5:  # 週六日往前推
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    now = now_tpe()
    today = latest_trading_day_guess(now)
    print(f"[tw-stock-data] 台北時間 {now:%Y-%m-%d %H:%M}，目標交易日 {today}")

    manifest = {
        "generated_at": now.isoformat(timespec="seconds"),
        "target_trading_day": today,
        "stocks": {},
        "market": {},
        "note": ("date_max 才是真正的資料基準日；target_trading_day 只是查詢用的猜測值。"
                 "下游一律讀 data/latest 底下的 CSV，不要讀 JSON——"
                 "JSON 檔太大，經 WebFetch 會被截斷並被憑空補齊。"
                 "可讀的檔：<代號>_price／_inst／_per／_revenue／_margin／_capital，"
                 "以及 market_index／market_breadth／market_amount。"),
        "version": "v6 2026-09-02",
    }

    all_dates = set()
    for code in STOCKS:
        data = fetch_stock(code, today)
        path = os.path.join(OUT_DIR, f"{code}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

        # ── 併進歷史（append-only），再切出 latest 的小視窗 ──
        st = {"price": None, "inst": None, "dividend_rows": None}
        unknown = []
        if data["price"]:
            hp = os.path.join(HIST_DIR, f"{code}_price.csv")
            total, added, changed = merge_history(
                hp, PRICE_HEADER, price_lines(data["price"]["data"]),
                f"{code}_price")
            write_window(hp, os.path.join(OUT_DIR, f"{code}_price.csv"))
            st["price"] = {"total": total, "added": added,
                           "changed": len(changed) or None}
            all_dates.update(r[0] for r in price_lines(data["price"]["data"]))
        if data["institutional"]:
            lines, unknown = inst_lines(data["institutional"]["data"])
            hi_ = os.path.join(HIST_DIR, f"{code}_inst.csv")
            total, added, changed = merge_history(
                hi_, INST_HEADER, lines, f"{code}_inst")
            write_window(hi_, os.path.join(OUT_DIR, f"{code}_inst.csv"))
            st["inst"] = {"total": total, "added": added,
                          "changed": len(changed) or None}
        if data.get("dividend"):
            dl = [[str(r.get("date", "")), json.dumps(r, ensure_ascii=False)]
                  for r in data["dividend"]["data"]]
            # 除權息一天可能有多筆，先原樣留著，欄位定案前不強行正規化
            os.makedirs(DIV_DIR, exist_ok=True)
            with open(os.path.join(DIV_DIR, f"{code}.json"), "w",
                      encoding="utf-8") as f:
                json.dump(data["dividend"]["data"], f, ensure_ascii=False)
            st["dividend_rows"] = len(dl)

        # ── v6：四個新 dataset 各自併進歷史 ──
        extra_stat, fs_types = {}, None
        for kind, blk in (data.get("extra") or {}).items():
            try:
                if kind == "fs":
                    lines, fs_types = fs_capital_lines(blk["data"])
                    header, tag = CAPITAL_HEADER, f"{code}_capital"
                    hpath = os.path.join(HIST_DIR, f"{code}_capital.csv")
                    # 看到的所有 type 都寫出來——對不上候選名單時才有東西可查
                    os.makedirs(META_DIR, exist_ok=True)
                    with open(os.path.join(META_DIR, f"{code}_fs_types.txt"),
                              "w", encoding="utf-8") as f:
                        f.write("\n".join(fs_types) + "\n")
                    if not lines:
                        manifest.setdefault("capital_not_found", []).append(code)
                        continue
                else:
                    lines = extra_lines(kind, blk["data"])
                    header = {"per": PER_HEADER, "revenue": REVENUE_HEADER,
                              "margin": MARGIN_HEADER}[kind]
                    tag = f"{code}_{kind}"
                    hpath = os.path.join(HIST_DIR, f"{code}_{kind}.csv")
                if not lines:
                    continue
                total, added, changed = merge_history(hpath, header, lines, tag)
                write_window(hpath, os.path.join(
                    OUT_DIR, os.path.basename(hpath)))
                extra_stat[kind] = {"total": total, "added": added,
                                    "changed": len(changed) or None,
                                    "date_max": lines[-1][0]}
            except Exception as ex:  # noqa: BLE001 — 新項目不可以拖垮既有的
                data["errors"][kind] = f"寫檔失敗 {type(ex).__name__}: {ex}"

        manifest["stocks"][code] = {
            "extra": extra_stat or None,
            "fs_types_seen": (len(fs_types) if fs_types else None),
            "price_date_max": (data["price"] or {}).get("date_max"),
            "inst_date_max": (data["institutional"] or {}).get("date_max"),
            "history": st,
            "inst_unknown_names": unknown or None,
            "errors": data["errors"] or None,
        }
        print(f"  {code}: price={manifest['stocks'][code]['price_date_max']} "
              f"inst={manifest['stocks'][code]['inst_date_max']} "
              f"hist={st} err={data['errors'] or '-'}")

    manifest["calendar_days"] = write_calendar(all_dates)

    market = fetch_market(today)
    with open(os.path.join(OUT_DIR, "market.json"), "w", encoding="utf-8") as f:
        json.dump(market, f, ensure_ascii=False, separators=(",", ":"))
    manifest["market"] = {
        "ok": [k for k in ("index", "summary", "t86", "bfi82u") if k in market],
        "errors": market["errors"] or None,
    }
    # ── v6：大盤也抽成一天一列的小 CSV（market.json 含全市場 T86，太大） ──
    _dump_tables(market, os.path.join(OUT_DIR, "market_tables_raw.txt"))
    try:
        mlines, merrs = market_lines(market, today)
        hdrs = {"index": MKT_INDEX_HEADER, "breadth": MKT_BREADTH_HEADER,
                "amount": MKT_AMOUNT_HEADER, "inst": MKT_INST_HEADER}
        mstat = {}
        for kind, line in mlines.items():
            hpath = os.path.join(HIST_DIR, f"market_{kind}.csv")
            total, added, changed = merge_history(
                hpath, hdrs[kind], [line], f"market_{kind}")
            write_window(hpath, os.path.join(OUT_DIR, f"market_{kind}.csv"))
            mstat[kind] = {"total": total, "added": added,
                           "changed": len(changed) or None}
        manifest["market"]["csv"] = mstat or None
        manifest["market"]["parse_errors"] = merrs or None
    except Exception as ex:  # noqa: BLE001
        manifest["market"]["parse_errors"] = {
            "fatal": f"{type(ex).__name__}: {ex}"}
    print(f"  market csv: {manifest['market'].get('csv')} "
          f"parse_err={manifest['market'].get('parse_errors') or '-'}")
    print(f"  market: ok={manifest['market']['ok']} err={market['errors'] or '-'}")

    # ★ 統計歷史被改寫的列數。**價格與籌碼都要算**——原本只算 price，
    #   籌碼被改寫時警示不會亮（2026-08-31 實測：7879 有 13 列籌碼被改寫，
    #   history_rows_changed 卻是 null）。
    # ★★ 而且這一段**必須在寫出 _manifest.json 之前**跑完。
    #   先寫檔再算，log 裡的 ⚠ 會亮，但下游讀到的檔案裡沒有這個欄位——
    #   **警示看得到卻傳不下去，等於沒有警示。**
    # ★ v6：新增的四項也要算進來。**統計要涵蓋所有會變動的資料種類**——
    #   漏算哪一種，那一種被改寫時就不會亮燈（8/31 就是漏算籌碼才被抓到）。
    changed_total = 0
    for c in STOCKS:
        h = manifest["stocks"][c].get("history") or {}
        for kind in ("price", "inst"):
            changed_total += ((h.get(kind) or {}).get("changed") or 0)
        x = manifest["stocks"][c].get("extra") or {}
        for kind in x:
            changed_total += ((x.get(kind) or {}).get("changed") or 0)
    for kind in (manifest.get("market", {}).get("csv") or {}):
        changed_total += ((manifest["market"]["csv"][kind] or {}).get("changed") or 0)
    manifest["history_rows_changed"] = changed_total or None
    if changed_total:
        print(f"[tw-stock-data] ⚠ 有 {changed_total} 列歷史資料被改寫（價格＋籌碼合計），"
              f"詳見 data/_changes.log")

    with open(os.path.join(OUT_DIR, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 全軍覆沒才視為執行失敗；個別失敗照實記錄在 manifest 裡，不讓整批停擺
    got = [c for c in STOCKS if manifest["stocks"][c]["price_date_max"]]
    if not got:
        # 全軍覆沒時把第一檔的完整錯誤再印一次，log 最下面就看得到，不必往上捲
        first_err = manifest["stocks"][STOCKS[0]]["errors"]
        print("[tw-stock-data] 所有個股都沒抓到，視為失敗", file=sys.stderr)
        print(f"[tw-stock-data] 第一檔的錯誤：{first_err}", file=sys.stderr)
        return 1
    print(f"[tw-stock-data] 完成：{len(got)}/{len(STOCKS)} 檔有日K")
    return 0


if __name__ == "__main__":
    sys.exit(main())
