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

輸出：
  data/latest/<代號>.json   每檔的日K與三大法人
  data/latest/market.json   大盤指數、成交統計、全市場三大法人
  data/latest/_manifest.json 這一輪的總表（誰成功誰失敗、基準日是哪天）
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
                 "下游請讀 <代號>_price.csv 與 <代號>_inst.csv——"
                 "JSON 檔太大，經 WebFetch 會被截斷並被憑空補齊。"),
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

        manifest["stocks"][code] = {
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
    print(f"  market: ok={manifest['market']['ok']} err={market['errors'] or '-'}")

    with open(os.path.join(OUT_DIR, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 全軍覆沒才視為執行失敗；個別失敗照實記錄在 manifest 裡，不讓整批停擺
    changed_total = sum((manifest["stocks"][c]["history"]["price"] or {}).get("changed") or 0
                        for c in STOCKS if manifest["stocks"][c].get("history"))
    manifest["history_rows_changed"] = changed_total or None
    if changed_total:
        print(f"[tw-stock-data] ⚠ 有 {changed_total} 列歷史資料被改寫，"
              f"詳見 data/_changes.log")

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
