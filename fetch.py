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
  ── v7 全市場層（2026-09-02 起）──
  data/universe/daily/YYYY-MM-DD.csv  **當日全市場**日K（一天一檔，不是一檔一股）
  data/meta/stocks.csv                代號↔名稱↔市場別＋first_seen／last_seen
  data/latest/endpoint_probe.txt      端點偵察：哪一條通、位元組數、實際欄位名

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
# 核心：持股與正式追蹤清單（claude/holdings.md、claude/watchlist.md）
CORE = [
    "7879",  # 益材科技（興櫃）
    "8289",  # 泰藝
    "2609",  # 陽明
    "6209",  # 今國光
    "3017",  # 奇鋐
    "8996",  # 高力
]

# 論壇追蹤池（2026-09-02 起）。規則見專案的 claude/forum_watch.md。
# ★ 這裡的每一個代號都已用 FinMind TaiwanStockInfo 對過「代號↔名稱」（規範第 9 條），
#   名稱與市場別寫在註解裡，**下次改動也要照對一次再加**。
# ★ 這一批只是**候選來源**，不是正式追蹤清單；分數 <40 就從池子淘汰，
#   淘汰後要把它從這個清單移除，免得每天白抓。
FORUM = [
    "3406",  # 玉晶光        上市・光電業        觀察分 74（2026-09-02）
    "3661",  # 世芯-KY       上市・半導體業      觀察分 64
    "3234",  # 光環          上櫃・通信網路業    觀察分 61
    "3008",  # 大立光        上市・光電業        觀察分 54（留池觀察）
    "3443",  # 創意          上市・半導體業      觀察分 49（留池觀察）
]
# 2026-09-02 首次評分後淘汰、已從清單移除（不要再加回來，除非規則改變）：
#   2454 聯發科      觀察分 34（<40）
#   3711 日月光投控  觀察分 17（<40）
#   5267 龍翩        排除：20 日均額 0.03 億，未達 5,000 萬流動性門檻（興櫃）

STOCKS = CORE + FORUM

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
    # ★ v6.1（2026-09-02 實測修正）：**股本不在損益表裡**。
    #   v6 第一次跑完，六檔的 capital_not_found 全中，
    #   `meta/<代號>_fs_types.txt` 顯示 TaiwanStockFinancialStatements 只有
    #   Revenue／GrossProfit／EPS 這類損益項，**完全沒有股本**。
    #   股本屬於資產負債表，所以改抓這一個。
    "bs":      "TaiwanStockBalanceSheet",
}

# 財報裡「股本」可能的 type 名稱。**不確定 FinMind 用哪一個**，所以列一組候選，
# 並且把當次看到的所有 type 另外寫成檔案（見 FS_TYPES_FILE）——
# 對不上時不要靜默放棄，要留下證據讓下次能查（與 inst_unknown_names 同一個設計）。
_CAPITAL_TYPES = ("OrdinaryShare", "CommonStock", "CommonStocks", "CapitalStock",
                  "ShareCapital", "股本", "普通股股本")
# 上面是**照優先順序**的候選；對不上時用這個較寬的樣式再撈一次當候選回報，
# 把 type 與最新的值寫進 meta/<代號>_capital_candidates.txt，下次直接照著改就好。
_CAPITAL_HINT = ("stock", "share", "capital", "股本")

# 損益表要留下來的科目（v6.3，2026-09-02）。
# 觀察分的「基本面」那一項要算**毛利率與營益率有沒有較上一季改善**，
# 先前只把 type 清單 dump 出來、沒落成 CSV，那 5 分全體都拿不到。
# 科目名稱來自 2026-09-02 實測的 meta/<代號>_fs_types.txt，**不是猜的**。
_FS_KEEP = ("Revenue", "GrossProfit", "OperatingIncome", "OperatingExpenses",
            "PreTaxIncome", "IncomeAfterTaxes", "EPS",
            "TotalNonoperatingIncomeAndExpense")

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
              "margin": INST_START, "fs": "2024-01-01", "bs": "2024-01-01"}
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
FS_HEADER = ["key", "date", "type", "value"]
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
    """資產負債表 → 只抽「股本」那幾列，順便回報看到的所有 type 與候選。

    回傳 (lines, types_seen, candidates)。
    **對不上候選名單時不要靜默放棄**——types_seen 與 candidates 會被寫成檔案，
    下次照著改 _CAPITAL_TYPES 就好（與 inst_unknown_names 同一個設計）。
    """
    types, by_type = set(), {}
    for r in rows:
        t = str(r.get("type", ""))
        types.add(t)
        d, v = str(r.get("date", "")), _num(r.get("value"))
        if d and v:
            by_type.setdefault(t, []).append((d, v))

    pick = next((t for t in _CAPITAL_TYPES if t in by_type), None)
    lines = []
    if pick:
        for d, v in sorted(by_type[pick]):
            lines.append([d, pick, v])

    # 沒中就把「看起來像股本」的都列出來當候選，附最新一筆的值
    candidates = []
    if not pick:
        for t in sorted(by_type):
            low = t.lower()
            if any(h in low for h in _CAPITAL_HINT):
                d, v = sorted(by_type[t])[-1]
                candidates.append(f"{t}\t{d}\t{v}")
    return lines, sorted(types), candidates


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


def _find_table(market, key, title_kws=(), field_kw=None):
    """在某個區塊裡找出符合條件的表。title_kws 任一命中即可。"""
    blk = market.get(key)
    if not blk:
        return None
    for t in _twse_tables(blk.get("data")):
        title = str(t.get("title", ""))
        fields = [str(x) for x in (t.get("fields") or [])]
        if title_kws and not any(k in title for k in title_kws):
            continue
        if field_kw and not any(field_kw in f for f in fields):
            continue
        return t
    return None


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


def _split_paren(v):
    """『587(19)』→ ('587', '19')。沒有括號就回 (值, '')。"""
    t = str(v).strip()
    if "(" in t and t.endswith(")"):
        main, _, rest = t.partition("(")
        return _num(main), _num(rest[:-1])
    return _num(t), ""


# 三大法人買賣金額統計表的單位名稱 → 三大類。
# ★ 與個股籌碼同一個雙重計算陷阱：自營商有「自行買賣」「避險」兩列，
#   有些日期還會多一列合計。**拆開的兩列存在時，合計那列要跳過。**
_BFI_MAP = [
    ("外資及陸資(不含外資自營商)", "foreign"),
    ("外資自營商", "foreign"),
    ("外資及陸資", "foreign"),
    ("投信", "trust"),
    ("自營商(自行買賣)", "dealer"),
    ("自營商(避險)", "dealer"),
]
_BFI_DEALER_TOTAL = "自營商"
_BFI_SKIP = ("合計", "總計")


def market_lines(market, day):
    """回傳 ({名稱: CSV 欄位 list}, errors)。抽不到的那一項就不放進 dict。

    ★ 三張表的實際形狀已於 2026-09-02 由 market_tables_raw.txt 確認，
      v6 的第一版三項有兩項解析失敗，就是因為當時是用猜的：
      - 大盤統計資訊的標題是「115年09月01日 大盤統計資訊」，**不含「成交」兩字**
      - 成交統計的欄位順序是 金額 → 股數 → 筆數，不是股數在前
      - 漲跌證券數合計是 **欄位＝整體市場／股票，列＝上漲／下跌／持平**，
        不是一列裡塞五個數字
    """
    out, errs = {}, {}

    # ── 加權指數 ──────────────────────────────────────────────
    # fields: ['指數','收盤指數','漲跌(+/-)','漲跌點數','漲跌百分比(%)','特殊處理註記']
    r = _find_row(market, "index", "價格指數(臺灣證券交易所)", "發行量加權股價指數") or \
        _find_row(market, "index", "", "發行量加權股價指數")
    if r and len(r) >= 5:
        sign = -1 if "-" in r[2] else 1
        chg, pct = _num(r[3]), _num(r[4])
        out["index"] = [day, _num(r[1]),
                        (str(sign * float(chg)) if chg else ""),
                        (str(sign * float(pct)) if pct else "")]
    else:
        errs["index"] = "找不到『發行量加權股價指數』那一列"

    # ── 漲跌家數 ──────────────────────────────────────────────
    # fields: ['類型','整體市場','股票'] ／ 列：上漲(漲停)、下跌(跌停)、持平…
    # ★ 一律取「股票」那一欄，**不是整體市場**（後者含權證與 ETF）。
    t = _find_table(market, "summary", ("漲跌證券數",), None)
    if t:
        fields = [str(x) for x in (t.get("fields") or [])]
        col = fields.index("股票") if "股票" in fields else 2
        if "股票" not in fields:
            errs["breadth_scope"] = f"欄位沒有『股票』，改用第 {col} 欄：{fields}"
        vals = {"up": "", "down": "", "flat": "", "lu": "", "ld": ""}
        for row in (t.get("data") or []):
            if not row or len(row) <= col:
                continue
            label = str(row[0])
            main, paren = _split_paren(row[col])
            if "上漲" in label:
                vals["up"], vals["lu"] = main, paren
            elif "下跌" in label:
                vals["down"], vals["ld"] = main, paren
            elif "持平" in label or "平盤" in label:
                vals["flat"] = main
        if vals["up"] and vals["down"]:
            out["breadth"] = [day, vals["up"], vals["down"], vals["flat"],
                              vals["lu"], vals["ld"]]
        else:
            errs["breadth"] = f"漲跌證券數表找到了但取不到值：{[r[:1] for r in (t.get('data') or [])][:6]}"
    else:
        errs["breadth"] = "找不到漲跌證券數合計那張表"

    # ── 成交統計 ──────────────────────────────────────────────
    # fields: ['成交統計','成交金額(元)','成交股數(股)','成交筆數']
    t = _find_table(market, "summary", ("大盤統計",), "成交金額")
    if t:
        # ★ 列名是「1.一般股票」，**不是「股票」**（2026-09-02 實測；
        #   同一張表還有 2.台灣存託憑證、認購售權證等，不可誤取）。
        def _is_stock_row(r):
            lab = str(r[0]).strip()
            return "一般股票" in lab or lab.split(".")[-1].strip() == "股票"
        row = next((r for r in (t.get("data") or []) if r and _is_stock_row(r)), None)
        if row and len(row) >= 4:
            out["amount"] = [day, _num(row[1]), _num(row[2]), _num(row[3])]
        else:
            errs["amount"] = "大盤統計資訊裡沒有『股票』那一列"
    else:
        errs["amount"] = "找不到大盤統計資訊那張表"

    # ── 三大法人買賣金額（單位：元） ────────────────────────────
    # fields: ['單位名稱','買進金額','賣出金額','買賣差額']
    t = _find_table(market, "bfi82u", ("三大法人",), "買賣差額")
    if t:
        rows = [[str(x) for x in r] for r in (t.get("data") or []) if r]
        names = {r[0].strip() for r in rows}
        has_split = any("自營商(" in n for n in names)
        agg = {"foreign": 0.0, "trust": 0.0, "dealer": 0.0}
        unknown, got = [], False
        for r in rows:
            name = r[0].strip()
            if any(k in name for k in _BFI_SKIP):
                continue
            if name == _BFI_DEALER_TOTAL and has_split:
                continue          # 拆開的已經算過，合計要跳過，否則自營商算兩次
            col = next((c for k, c in _BFI_MAP if name.startswith(k)), None)
            if col is None:
                col = "dealer" if name.startswith(_BFI_DEALER_TOTAL) else None
            if col is None:
                unknown.append(name)
                continue
            v = _num(r[3]) if len(r) >= 4 else ""
            if v:
                agg[col] += float(v)
                got = True
        if got:
            tot = agg["foreign"] + agg["trust"] + agg["dealer"]
            out["inst"] = [day, str(int(agg["foreign"])), str(int(agg["trust"])),
                           str(int(agg["dealer"])), str(int(tot))]
        else:
            errs["inst"] = "三大法人表找到了但取不到買賣差額"
        if unknown:
            errs["inst_unknown_names"] = unknown
    elif "bfi82u" not in market:
        errs["inst"] = "BFI82U 未取得"
    else:
        errs["inst"] = "找不到三大法人買賣金額統計表"

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


# ══════════════════════════════════════════════════════════
# 全市場層（v7，2026-09-02）
#
# 為什麼要有這一層：使用者要把資料庫擴到全市場（約 2,100 檔）。
# **逐檔抓是錯的做法**——2,100 檔 × 每天 2 個 dataset = 4,200 個請求，
# FinMind 免費版跑不完。交易所本來就有「當日全市場」端點，
# **一天幾個請求就涵蓋整個市場，800 檔和 2,100 檔成本一樣**。
#
# ★ 檔案是「一天一檔」，不是「一檔一股」。
#   git 存的是整個檔案的新版本，不是新增的那一列。2,100 個檔案每天各加一列，
#   等於每天把整個資料庫重存一遍（約 300MB/天）。一天一檔則是 200KB/天。
#
# ★ 端點路徑都是**待驗證的假設**。所以每個都給候選清單、逐一試，
#   並把實際的 HTTP 狀態、位元組數、欄位名寫進 endpoint_probe.txt。
#   **第一次執行自己回答哪一條可用**，不要用猜的當結論。
# ══════════════════════════════════════════════════════════

UNI_DIR = os.path.join(_ROOT, "universe")
PROBE = "endpoint_probe.txt"

UNIVERSE_HEADER = ["key", "date", "stock_id", "name", "market",
                   "open", "high", "low", "close", "volume", "amount",
                   "change", "limit", "shares"]
# shares＝發行股數。**只有上櫃那條端點有給**，上市與興櫃留空。
# 有它才算得出市值與周轉率，所以拿得到就存——事後補要另外跑 2,000 個請求。
STOCKS_HEADER = ["stock_id", "name", "market", "kind", "first_seen", "last_seen"]


def _kind(code, name):
    """粗分類，只用代號規則，**不猜**。

    2026-09-02 實測（v7.0 第一次全市場執行）：
    - 上市走 `ALLBUT0999`，**本來就不含權證**；1,371 列 = 4碼 1,092 ＋ 5碼 134 ＋ 6碼 145。
    - **上櫃的 openapi 沒有這個過濾**：5,709 列裡有 **4,844 是權證**
      （`706985 原相永豐5B購02` 這種，代號 70～73 開頭）。
    → 權證必須排除：它不是股票，而且佔了 70% 的體積。
    """
    c = str(code)
    if len(c) == 6 and c[0] == "7":
        return "warrant"      # 權證（上櫃 70～73 開頭），**不寫進 daily**
    if c.startswith("00"):
        return "etf"          # ETF／ETN／期信
    if len(c) == 5:
        return "special"      # 特別股、TDR 等
    if len(c) == 6:
        return "other"        # 受益證券、REITs 等
    return "stock"            # 四碼＝真正的股票


def _candidates(ymd, day_slash=""):
    """每個市場的候選端點，依序試，第一個成功的就用。

    ymd = 20260902（TWSE 用）；day_slash = 2026/09/02（TPEx 新站用）。
    """
    return {
        "twse": [
            # 每日收盤行情（全部，**不含權證與債券**）
            f"{TWSE}/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
            f"https://www.twse.com.tw/exchangeReport/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
            f"{TWSE}/afterTrading/STOCK_DAY_ALL?response=json",
        ],
        # ★ 2026-09-02 回補 probe 證實：`afterTrading/otc` 比 openapi 好很多，改為第一順位。
        #   openapi 回 5,709 列（含 4,844 檔權證）；這一條回 998 列、**原生就不含權證**，
        #   而且多了「發行股數」（＝在外流通股數，可直接算市值與周轉率）
        #   與「次日漲停價／次日跌停價」。**回補與每日用同一條，形狀才會一致。**
        "tpex": [
            f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={day_slash}&type=EW&id=&response=json",
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
        ],
        "emerging": [
            "https://www.tpex.org.tw/openapi/v1/tpex_esb_latest_statistics",
        ],
    }


def _probe_write(lines):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, PROBE), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _rows_from_twse(d):
    """TWSE 的 tables 裡找出「有證券代號與收盤價」的那張表。

    不寫死表名——TWSE 的表標題含民國日期，每天都不一樣（2026-09-02 踩過）。
    改用**欄位名**辨識，那個才穩定。
    """
    for t in _twse_tables(d):
        fields = [str(x) for x in (t.get("fields") or [])]
        # 條件放寬到「有代號欄 ＋ 有收盤欄」：TPEx 用「代號」、TWSE 用「證券代號」
        if any("代號" in f for f in fields) and any("收盤" in f for f in fields):
            return t, fields
    return None, []


def _idx(fields, *kws):
    for i, f in enumerate(fields):
        if all(k in f for k in kws):
            return i
    return None


def _idx_any(fields, *options):
    """依序試多組關鍵字，回第一個命中的欄位位置。

    ★ 不可以寫成 `_idx(a) or _idx(b)`——**第一欄的索引是 0，在 Python 是 falsy**，
      證券代號正好就在第 0 欄，寫 `or` 會讓整張表解析出 0 列（2026-09-02 實測踩到）。
    """
    for kws in options:
        i = _idx(fields, *(kws if isinstance(kws, tuple) else (kws,)))
        if i is not None:
            return i
    return None


def parse_twse_daily(d, day, market="twse"):
    """→ (lines, note)。抓不到就回 ([], 原因)。"""
    t, fields = _rows_from_twse(d)
    if not t:
        return [], "找不到含『證券代號』與『收盤』欄位的表"
    i_code = _idx_any(fields, "證券代號", "股票代號", "代號")
    i_name = _idx_any(fields, "證券名稱", "股票名稱", "名稱")
    i_open, i_high = _idx_any(fields, "開盤"), _idx_any(fields, "最高")
    i_low, i_close = _idx_any(fields, "最低"), _idx_any(fields, "收盤")
    i_vol = _idx_any(fields, "成交股數")
    i_amt = _idx_any(fields, "成交金額")
    i_chg = _idx_any(fields, "漲跌價差")
    # 漲跌有兩種寫法：TWSE 拆成「方向欄（HTML 的 +/-）＋ 漲跌價差」；
    # TPEx 是單一「漲跌」欄、正負號直接寫在值裡。**兩種都要吃**
    #（2026-09-02：只修了 backfill.py 沒同步這裡，TPEx 的漲跌整欄變空）。
    i_sign = _idx_any(fields, ("漲跌", "+"), "漲跌(+/-)", "漲跌")
    i_shares = _idx_any(fields, "發行股數")
    need = [i_code, i_open, i_high, i_low, i_close]
    if any(x is None for x in need):
        return [], f"欄位對不上：{fields}"
    out = []
    for r in (t.get("data") or []):
        if not r or len(r) <= max(x for x in need if x is not None):
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        o, h, l, c = (_num(r[i_open]), _num(r[i_high]),
                      _num(r[i_low]), _num(r[i_close]))
        if not c:
            continue                       # 無成交就沒有收盤價，跳過不補值
        if i_chg is not None:
            sign = -1 if (i_sign is not None and "-" in str(r[i_sign])) else 1
            chg = _num(r[i_chg])
            chg = str(sign * float(chg)) if chg else ""
        elif i_sign is not None:
            # 正負號已在值裡，_num() 只清 "+"、保留 "-"——**不要再乘一次 -1**
            chg = _num(r[i_sign])
        else:
            chg = ""
        # 漲跌停鎖死：開＝高＝低＝收且有量。**回測必須知道這一天買不到。**
        lim = ""
        if o and h and l and c and o == h == l == c:
            lim = "up" if (chg and float(chg) > 0) else ("down" if chg else "flat")
        out.append([f"{day}_{code}", day, code,
                    str(r[i_name]).strip() if i_name is not None else "",
                    market, o, h, l, c,
                    _num(r[i_vol]) if i_vol is not None else "",
                    _num(r[i_amt]) if i_amt is not None else "",
                    chg, lim,
                    _num(r[i_shares]) if i_shares is not None else ""])
    return out, f"欄位={fields}"


def parse_openapi_daily(rows, day, market):
    """TPEx openapi 是一個 list of dict，欄位名為英文或中文，兩種都試。"""
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
    # ★ 興櫃（tpex_esb_latest_statistics）沒有 Open/Close，只有 LatestPrice／Highest／
    #   Lowest／TransactionVolume（2026-09-02 實測，v7.0 因此解析出 0 列）。
    #   **開盤價刻意不映射**——興櫃的開盤是參考價，會落在當日高低之外，
    #   依專案規範本來就不可拿來畫K棒實體。
    k_close = pick("Close", "LatestPrice", "收盤")
    k_open = pick("Open", "開盤")
    k_high = pick("High", "Highest", "最高")
    k_low = pick("Low", "Lowest", "最低")
    k_vol = pick("TradingShares", "TransactionVolume", "成交股數")
    k_amt = pick("TransactionAmount", "成交金額")
    k_chg = pick("Change", "漲跌")
    if not (k_code and k_close):
        return [], f"欄位對不上：{keys}"
    out = []
    for r in rows:
        code = str(r.get(k_code, "")).strip()
        if not code or not code[0].isdigit():
            continue
        o, h, l, c = (_num(r.get(k_open)), _num(r.get(k_high)),
                      _num(r.get(k_low)), _num(r.get(k_close)))
        if not c:
            continue
        chg = _num(r.get(k_chg))
        lim = ""
        if o and h and l and c and o == h == l == c:
            lim = "up" if (chg and float(chg) > 0) else ("down" if chg else "flat")
        out.append([f"{day}_{code}", day, code,
                    str(r.get(k_name, "")).strip(), market,
                    o, h, l, c, _num(r.get(k_vol)), _num(r.get(k_amt)), chg, lim, ""])
    return out, f"欄位={keys}"


def fetch_universe(today):
    """全市場日K。回傳 (manifest 片段, 所有列)。任何一個市場失敗都不影響其他。"""
    ymd = today.replace("-", "")
    probe, all_lines, counts, errs = [], [], {}, {}
    probe.append(f"# 端點偵察 {now_tpe().isoformat(timespec='seconds')} 目標日 {today}")

    for market, urls in _candidates(ymd, today.replace("-", "/")).items():
        got = False
        for u in urls:
            raw, err = get(u, retries=2, timeout=40)
            if err:
                probe.append(f"{market} FAIL {u}\n    {err}")
                continue
            probe.append(f"{market} OK   {u}\n    bytes={len(raw)}")
            try:
                d = json.loads(raw.decode("utf-8"))
            except Exception as e:  # noqa: BLE001
                probe.append(f"    JSON 解析失敗 {type(e).__name__}")
                continue
            if isinstance(d, list):
                lines, note = parse_openapi_daily(d, today, market)
            else:
                stat = d.get("stat")
                if stat and str(stat).strip().lower() not in ("ok", "success"):
                    probe.append(f"    stat={stat}（休市或查無）")
                    errs[market] = f"stat={stat}"
                    got = True          # 明確的「今天沒有」，不要再試下一條
                    break
                lines, note = parse_twse_daily(d, today, market)
            probe.append(f"    {note}")
            probe.append(f"    解析出 {len(lines)} 列")
            if lines:
                all_lines.extend(lines)
                counts[market] = len(lines)
                got = True
                break
        if not got and market not in errs:
            errs[market] = "所有候選端點都失敗"

    # ★ 權證不寫進資料庫：不是股票，而且 2026-09-02 實測佔了上櫃回傳的 70%（4,844/5,709）。
    #   **排除幾檔要回報**，不要靜靜地丟掉。
    kept, dropped = [], 0
    for r in all_lines:
        if _kind(r[2], r[3]) == "warrant":
            dropped += 1
            continue
        kept.append(r)
    counts["warrants_excluded"] = dropped
    counts["total"] = len(kept)
    # 依類型細分，讓「到底幾檔股票」有明確答案
    bykind = {}
    for r in kept:
        k = _kind(r[2], r[3])
        bykind[k] = bykind.get(k, 0) + 1
    counts["by_kind"] = bykind
    _probe_write(probe)
    return {"counts": counts, "errors": errs or None}, kept


def write_universe_day(day, lines):
    """一天一檔。**同一天重跑會整份覆蓋**（當日資料以最後一次為準）。"""
    if not lines:
        return 0
    path = os.path.join(UNI_DIR, "daily", f"{day}.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(UNIVERSE_HEADER) + "\n")
        for r in sorted(lines, key=lambda r: r[2]):
            f.write(",".join(str(x).replace(",", "") for x in r) + "\n")
    return len(lines)


def merge_stocks_meta(day, lines):
    """代號↔名稱↔市場別，並記 first_seen／last_seen。

    ★ first/last_seen 是回測的必需品：回測到 2018 年時，universe 必須是
      **當時真的存在的那些股票**，不是今天還活著的這批（生存者偏差的另一半）。
    """
    path = os.path.join(META_DIR, "stocks.csv")
    header, old = _read_csv(path)
    if header is not None and header != STOCKS_HEADER:
        raise ValueError(f"{path} 欄位不符：{header}")
    merged = dict(old)
    added = 0
    for r in lines:
        code, name, market = r[2], r[3], r[4]
        if code in merged:
            row = merged[code]
            row[1] = name or row[1]
            row[2] = market or row[2]
            row[3] = _kind(code, name)
            row[5] = day                      # last_seen
        else:
            merged[code] = [code, name, market, _kind(code, name), day, day]
            added += 1
    # ★ 自我修復：每次都重算 kind，並把權證清掉。
    #   「只進不出」是對的（避免生存者偏差），但它同時讓**錯誤也永久留下**——
    #   v7.0 那次把 4,844 檔權證寫進 stocks.csv，靠只進不出永遠清不掉（2026-09-02 實測）。
    #   所以規則要精確化：**股票只進不出，分類錯誤要能修正。**
    purged = 0
    for code in list(merged):
        row = merged[code]
        row[3] = _kind(code, row[1])          # 重算分類，修正舊資料
        if row[3] == "warrant":
            del merged[code]
            purged += 1

    os.makedirs(META_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(STOCKS_HEADER) + "\n")
        for k in sorted(merged):
            f.write(",".join(str(x) for x in merged[k]) + "\n")
    return len(merged), added, purged


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
        if stat and str(stat).strip().lower() not in ("ok", "success"):
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
        "version": "v7.6 2026-09-03",   # ★ 改程式就要改這一行，否則從 manifest 看不出跑的是哪一版
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
        extra_stat, fs_types, cap_type = {}, None, None
        for kind, blk in (data.get("extra") or {}).items():
            try:
                if kind in ("fs", "bs"):
                    # fs（損益表）只留 type 清單供查；**股本在 bs（資產負債表）**
                    os.makedirs(META_DIR, exist_ok=True)
                    if kind == "fs":
                        _, fs_types, _ = fs_capital_lines(blk["data"])
                        with open(os.path.join(META_DIR, f"{code}_fs_types.txt"),
                                  "w", encoding="utf-8") as f:
                            f.write("\n".join(fs_types) + "\n")
                        # ★ 主鍵是 date+type（一天有多個科目），所以第一欄放合成鍵，
                        #   否則 merge_history 只看第一欄會把同一天的科目互相覆蓋。
                        lines = []
                        for r in sorted(blk["data"],
                                        key=lambda r: (str(r.get("date", "")),
                                                       str(r.get("type", "")))):
                            t, dt, v = (str(r.get("type", "")), str(r.get("date", "")),
                                        _num(r.get("value")))
                            if t in _FS_KEEP and dt and v:
                                lines.append([f"{dt}_{t}", dt, t, v])
                        if not lines:
                            continue
                        header, tag = FS_HEADER, f"{code}_fs"
                        hpath = os.path.join(HIST_DIR, f"{code}_fs.csv")
                        total, added, changed = merge_history(hpath, header, lines, tag)
                        write_window(hpath, os.path.join(OUT_DIR, f"{code}_fs.csv"))
                        extra_stat["fs"] = {"total": total, "added": added,
                                            "changed": len(changed) or None,
                                            "date_max": lines[-1][1]}
                        continue
                    lines, bs_types, cands = fs_capital_lines(blk["data"])
                    with open(os.path.join(META_DIR, f"{code}_bs_types.txt"),
                              "w", encoding="utf-8") as f:
                        f.write("\n".join(bs_types) + "\n")
                    if cands:
                        with open(os.path.join(
                                META_DIR, f"{code}_capital_candidates.txt"),
                                "w", encoding="utf-8") as f:
                            f.write("type\tdate\tvalue\n" + "\n".join(cands) + "\n")
                    header, tag = CAPITAL_HEADER, f"{code}_capital"
                    hpath = os.path.join(HIST_DIR, f"{code}_capital.csv")
                    if not lines:
                        manifest.setdefault("capital_not_found", []).append(code)
                        continue
                    cap_type = lines[0][1]
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
            "capital_source": cap_type,
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

    # ── v7：全市場層（一天一檔）。失敗不影響核心檔 ──
    try:
        uni, uni_lines = fetch_universe(today)
        uni["rows_written"] = write_universe_day(today, uni_lines)
        total, added, purged = merge_stocks_meta(today, uni_lines)
        uni["stocks_meta"] = {"total": total, "added_today": added,
                              "purged_warrants": purged or None}
        manifest["universe"] = uni
        c = uni["counts"]
        print(f"  universe: 上市 {c.get('twse', 0)}｜上櫃 {c.get('tpex', 0)}｜"
              f"興櫃 {c.get('emerging', 0)}｜合計 {c.get('total', 0)}｜"
              f"stocks.csv 累計 {total}（今日新增 {added}）")
        if uni.get("errors"):
            print(f"  universe 失敗的市場：{uni['errors']}")
    except Exception as ex:  # noqa: BLE001 — 新層不可以拖垮既有的
        manifest["universe"] = {"fatal": f"{type(ex).__name__}: {ex}"}
        print(f"  universe FATAL: {type(ex).__name__}: {ex}")

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
