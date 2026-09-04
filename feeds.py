#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feeds.py — 全市場「每日一請求」型資料的回補器。

為什麼另開一支：`backfill.py` 已經 54 KB 且是驗證過的路徑，
價格與法人的回補全靠它。把五種新資料塞進去，等於每加一種就冒一次
「動到已經對的東西」的風險。**這支只做新增的 feed，價格與法人不碰。**

**共用的脆弱函式一律 import backfill，不複製**——`get()` 的退避、
`daterange()` 的交易日與週六補班、`_same_day()` 的日期核對、
`_num()` 的數字清洗，每一個都踩過坑。複製一份等於未來兩份各修一次，
而且會靜默分岔。

---

## 已驗證（2026-09-04，實測 date=20260903）

| feed | 端點 | 結果 |
|---|---|---|
| `per`     | TWSE `BWIBBU_d` | stat=OK、**1,580 列**、8 欄（本益比／殖利率／股價淨值比） |
| `exright` | TWSE `TWT49U`   | stat=OK、**4 列**、15 欄（除權息前收盤價／參考價／權值+息值） |

`exright` 那天的 4 列含 3661 世芯-KY 除息 32.551656、參考價 4,167.44，
與 `claude/watchlist_state.md` 記的「09/03 除息 32.55、參考價 4,167.45」對得起來。

## 未驗證（候選清單，靠 --probe 淘汰）

`margin`（上市融資融券）、`otcinst`（上櫃三大法人）、`otcper`、`otcmargin`、`otcexright`。

**上市融資融券 `MI_MARGN` 在 2026-09-04 用 selectType=ALL／ALLBUT0999／MS
三種參數實測都回「很抱歉，沒有符合條件的資料」**——端點在、參數不對。
候選清單裡放了其他幾種寫法，由 probe 決定。

**TPEx 的端點無法從開發環境驗證**（對外直接讀一律 403），
但**管線在 GitHub Actions 裡讀得到**——上櫃日檔就是這樣抓的。
所以 TPEx 的候選只能在 Actions 上 probe，不能在本機下結論。

---

## 一條紀律：候選清單裡不准放「只回今天」的端點

`backfill.py` 的註解已經記過這個事故：openapi 型端點沒有 date 參數、
永遠回當日資料，回補時會把今天的數字寫進 2015 年的檔案——
**靜默、每個數字都是真的、只是屬於另一個年代。**
本檔所有候選都必須帶日期參數，且一律經過 `_same_day()` 核對。
"""

import argparse
import json
import os
import sys
import time

import backfill as B

_ROOT = B._ROOT
UNI_DIR = B.UNI_DIR


# ────────────────────────────────────────────────────────────
# 解析器
# ────────────────────────────────────────────────────────────

def _fieldmap(t):
    return [str(x).strip() for x in (t.get("fields") or [])]


def _exact(fields, *names):
    """★ 完全相等比對，不用「包含」。

    T86 踩過這個坑：欄名互相包含，用子字串比對會讓「自營商買賣超股數」
    命中「外資自營商買賣超股數」，16,833 列裡 16,394 列驗算不符。
    """
    for n in names:
        for i, f in enumerate(fields):
            if f == n:
                return i
    return None


def _blank_num(v):
    """數字欄的清洗：拿不到就回空字串，**不要回 0**。

    `--esb` 踩過：1,064 列零價被當成真的價格，回測算出 −100%。
    「沒有」和「零」在這裡是完全不同的事實。
    """
    s = B._num(v)
    if s is None:
        return ""
    s = str(s).strip()
    if s in ("", "-", "--", "N/A", "不適用", "除權息"):
        return ""
    return s


def parse_per(d, day, known=None):
    """TWSE BWIBBU_d → 本益比／殖利率／股價淨值比。

    ★ 本益比欄常是 "-"（虧損公司算不出來）。**留空，不可填 0**——
      填 0 會讓「最便宜的股票」篩選結果整批是虧損股。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_code = _exact(f, "證券代號", "股票代號", "代號")
    i_close = _exact(f, "收盤價")
    i_yield = _exact(f, "殖利率(%)")
    i_dyear = _exact(f, "股利年度")
    i_per = _exact(f, "本益比")
    i_pbr = _exact(f, "股價淨值比")
    i_fsq = _exact(f, "財報年/季")
    if i_code is None or i_per is None or i_pbr is None:
        return [], f"欄位對不上：{f}"
    out = []
    for r in (t.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        g = lambda i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
        out.append([day, code, g(i_close), g(i_yield),
                    str(r[i_dyear]).strip() if i_dyear is not None and i_dyear < len(r) else "",
                    g(i_per), g(i_pbr),
                    str(r[i_fsq]).strip() if i_fsq is not None and i_fsq < len(r) else ""])
    return out, f"{len(out)} 列"


def parse_exright(d, day, known=None):
    """TWSE TWT49U → 除權除息計算結果。

    這是還原價的**事件來源**：還原因子 = 除權息參考價 ÷ 除權息前收盤價。
    ★ 因子在這裡**不算**，只存原始兩個價格。理由是還原要整段回推，
      屬於 `adjust.py` 的工作；在抓取端先算一半，日後改公式就得重抓。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_code = _exact(f, "股票代號", "證券代號", "代號")
    i_pre = _exact(f, "除權息前收盤價")
    i_ref = _exact(f, "除權息參考價")
    i_val = _exact(f, "權值+息值")
    i_kind = _exact(f, "權/息")
    i_open = _exact(f, "開盤競價基準")
    if i_code is None or i_pre is None or i_ref is None:
        return [], f"欄位對不上：{f}"
    out = []
    for r in (t.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        g = lambda i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
        pre, ref = g(i_pre), g(i_ref)
        # 兩個價格缺一就不寫。**寧可少一列，不要寫一列算不出因子的**。
        if not pre or not ref:
            continue
        out.append([day, code, pre, ref, g(i_val),
                    (str(r[i_kind]).strip() if i_kind is not None and i_kind < len(r) else ""),
                    g(i_open)])
    return out, f"{len(out)} 列"


def parse_margin(d, day, known=None):
    """TWSE 融資融券。**欄位尚未實測**，先照名稱找，對不上就回報整串欄名。

    不猜位置：端點一旦通了，probe 會把真實欄名印出來，再照抄進來。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    # 融資融券的回應通常有多張表（彙總在前、個股在後），取欄數最多且有代號欄的那張
    best, bf = None, None
    for t in tabs:
        f = _fieldmap(t)
        if _exact(f, "股票代號", "證券代號", "代號") is not None:
            if best is None or len(f) > len(bf):
                best, bf = t, f
    if best is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(t) for t in tabs]}"
    f = bf
    i_code = _exact(f, "股票代號", "證券代號", "代號")
    i_mb = _exact(f, "融資買進")
    i_ms = _exact(f, "融資賣出")
    i_mnow = _exact(f, "融資今日餘額", "融資餘額")
    i_mlim = _exact(f, "融資限額")
    i_sb = _exact(f, "融券買進")
    i_ss = _exact(f, "融券賣出")
    i_snow = _exact(f, "融券今日餘額", "融券餘額")
    if i_mnow is None or i_snow is None:
        return [], f"欄位對不上：{f}"
    out = []
    for r in (best.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        g = lambda i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
        out.append([day, code, g(i_mb), g(i_ms), g(i_mnow), g(i_mlim),
                    g(i_sb), g(i_ss), g(i_snow)])
    return out, f"{len(out)} 列"


def parse_otcinst(d, day, known=None):
    """上櫃三大法人。**欄位尚未實測。**

    上櫃的欄名與 T86 不同（自營商分「自行買賣」與「避險」，外資也可能分兩欄），
    所以外資與自營商都採「先找合計欄、找不到再把分項相加」。
    ★ 驗算恆等式照做：外資 ＋ 投信 ＋ 自營 ＝ 三大法人，不符就丟該列並計數。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    best, bf = None, None
    for t in tabs:
        f = _fieldmap(t)
        if _exact(f, "代號", "證券代號", "股票代號") is not None and len(f) >= 6:
            if best is None or len(f) > len(bf):
                best, bf = t, f
    if best is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(t) for t in tabs]}"
    f = bf
    i_code = _exact(f, "代號", "證券代號", "股票代號")
    i_fo = _exact(f, "外資及陸資買賣超股數", "外資買賣超股數",
                  "外資及陸資(不含外資自營商)買賣超股數")
    i_fo2 = _exact(f, "外資自營商買賣超股數")
    i_tr = _exact(f, "投信買賣超股數")
    i_dl = _exact(f, "自營商買賣超股數")
    i_dl1 = _exact(f, "自營商買賣超股數(自行買賣)")
    i_dl2 = _exact(f, "自營商買賣超股數(避險)")
    i_tt = _exact(f, "三大法人買賣超股數")
    if i_code is None or i_tt is None:
        return [], f"欄位對不上：{f}"
    out, bad = [], 0
    for r in (best.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        g = lambda i: float(B._num(r[i]) or 0) if (i is not None and i < len(r)) else 0.0
        fo = g(i_fo) + g(i_fo2)
        tr = g(i_tr)
        dl = g(i_dl) if i_dl is not None else (g(i_dl1) + g(i_dl2))
        tt = g(i_tt)
        if abs(fo + tr + dl - tt) > 1:
            bad += 1
            continue
        out.append([day, code, f"{fo:.0f}", f"{tr:.0f}", f"{dl:.0f}", f"{tt:.0f}"])
    return out, f"{len(out)} 列可用（驗算不符丟棄 {bad} 列）"


# ────────────────────────────────────────────────────────────
# feed 定義
# ────────────────────────────────────────────────────────────

def _twse(path, day, extra=""):
    return f"https://www.twse.com.tw/rwd/zh/{path}?date={day.replace('-', '')}{extra}&response=json"


def _tpex(path, day, extra=""):
    return f"https://www.tpex.org.tw/www/zh-tw/{path}?date={day.replace('-', '/')}{extra}&response=json"


FEEDS = {
    # ── 已驗證 ──────────────────────────────────────────────
    "per": {
        "dir": "per",
        "header": ["date", "stock_id", "close", "yield_pct", "dividend_year",
                   "per", "pbr", "fs_quarter"],
        "parse": parse_per,
        "known": True,
        "urls": lambda day: [_twse("afterTrading/BWIBBU_d", day, "&selectType=ALL")],
        "status": "已驗證 2026-09-04：20260903 → stat=OK、1,580 列",
    },
    "exright": {
        "dir": "exright",
        "header": ["date", "stock_id", "pre_close", "ref_price", "value",
                   "kind", "open_base"],
        "parse": parse_exright,
        "known": False,   # 除權息表會有已下市或非 universe 的標的，先全收
        "urls": lambda day: [_twse("exRight/TWT49U", day)],
        "status": "已驗證 2026-09-04：20260903 → stat=OK、4 列（含 3661 除息 32.551656）",
    },

    # ── 未驗證，候選清單 ────────────────────────────────────
    "margin": {
        "dir": "margin",
        "header": ["date", "stock_id", "m_buy", "m_sell", "m_balance", "m_limit",
                   "s_buy", "s_sell", "s_balance"],
        "parse": parse_margin,
        "known": True,
        "urls": lambda day: [
            _twse("marginTrading/MI_MARGN", day, "&selectType=ALL"),
            _twse("marginTrading/MI_MARGN", day, "&selectType=ALLBUT0999"),
            _twse("marginTrading/MI_MARGN", day, "&selectType=STOCK"),
            _twse("marginTrading/MI_MARGN", day, "&selectType=0999"),
            _twse("marginTrading/MI_MARGN", day),
            _twse("marginTrading/TWT93U", day),
            f"https://www.twse.com.tw/exchangeReport/MI_MARGN"
            f"?date={day.replace('-', '')}&selectType=ALL&response=json",
        ],
        "status": "未驗證。ALL／ALLBUT0999／MS 三種 2026-09-04 實測皆回「沒有符合條件的資料」",
    },
    "otcinst": {
        "dir": "otcinst",
        "header": ["date", "stock_id", "foreign", "trust", "dealer", "total"],
        "parse": parse_otcinst,
        "known": True,
        "urls": lambda day: [
            _tpex("insti/dailyTrade", day, "&type=Daily&sect=EW&id="),
            _tpex("insti/dailyTrade", day, "&type=Daily&sect=AL&id="),
            _tpex("insti/summary", day, "&type=Daily&sect=EW"),
            _tpex("afterTrading/insti", day, "&type=EW&id="),
            _tpex("insti/institutional_trading", day, "&type=Daily&sect=EW"),
            f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php"
            f"?l=zh-tw&se=EW&t=D&d={B.roc(day)}&o=json",
        ],
        "status": "未驗證。TPEx 從開發環境讀一律 403，只能在 Actions 上 probe",
    },
    "otcper": {
        "dir": "otcper",
        "header": ["date", "stock_id", "close", "yield_pct", "dividend_year",
                   "per", "pbr", "fs_quarter"],
        "parse": parse_per,
        "known": True,
        "urls": lambda day: [
            _tpex("afterTrading/peRatioAnalysis", day, "&id="),
            _tpex("afterTrading/peQryDate", day, "&id="),
            _tpex("afterTrading/pe", day, "&id="),
            f"https://www.tpex.org.tw/web/stock/aftertrading/peratio_analysis/pera_result.php"
            f"?l=zh-tw&d={B.roc(day)}&c=&o=json",
        ],
        "status": "未驗證",
    },
    "otcmargin": {
        "dir": "otcmargin",
        "header": ["date", "stock_id", "m_buy", "m_sell", "m_balance", "m_limit",
                   "s_buy", "s_sell", "s_balance"],
        "parse": parse_margin,
        "known": True,
        "urls": lambda day: [
            _tpex("margin/balance", day, "&id="),
            _tpex("margin/marginTrading", day, "&id="),
            _tpex("afterTrading/margin", day, "&id="),
            f"https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php"
            f"?l=zh-tw&d={B.roc(day)}&o=json",
        ],
        "status": "未驗證",
    },
    "otcexright": {
        "dir": "otcexright",
        "header": ["date", "stock_id", "pre_close", "ref_price", "value",
                   "kind", "open_base"],
        "parse": parse_exright,
        "known": False,
        "urls": lambda day: [
            _tpex("exRight/exRightResult", day, "&id="),
            _tpex("exRight/dailyResult", day, "&id="),
            _tpex("afterTrading/exRight", day, "&id="),
            f"https://www.tpex.org.tw/web/stock/exright/revivt/revivt_result.php"
            f"?l=zh-tw&d={B.roc(day)}&o=json",
        ],
        "status": "未驗證",
    },
}


def feed_dir(name):
    return os.path.join(UNI_DIR, FEEDS[name]["dir"])


# ────────────────────────────────────────────────────────────
# 通用逐日回補
# ────────────────────────────────────────────────────────────

def write_day(name, day, lines):
    if not lines:
        return 0
    d = feed_dir(name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{day}.csv"), "w", encoding="utf-8") as f:
        f.write(",".join(FEEDS[name]["header"]) + "\n")
        for r in sorted(lines, key=lambda r: r[1]):
            f.write(",".join(r) + "\n")
    return len(lines)


def fetch_one(name, day, known):
    """回 (lines, note, used_url)。候選依序試，第一個通過 _same_day 的就用。"""
    spec = FEEDS[name]
    last = "沒有候選"
    for url in spec["urls"](day):
        raw, err = B.get(url)
        if err:
            last = f"失敗({err[:50]})"
            continue
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception as ex:                       # noqa: BLE001
            head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
            last = f"JSON {type(ex).__name__}｜{len(raw)}B｜開頭：{head}"
            continue
        stat = d.get("stat") if isinstance(d, dict) else None
        if stat and str(stat).strip().lower() not in ("ok", "success"):
            last = f"stat={stat}"
            continue
        # ★ 日期核對是防「只回今天」的最後一道閘。不可為了讓某個候選通過而拿掉。
        same, said = B._same_day(d, day)
        if not same:
            last = f"日期不符({said})"
            continue
        lines, nt = spec["parse"](d, day, known if spec["known"] else None)
        return lines, nt, url
    return [], last, None


def cmd_feed(args):
    name = args.feed
    if name not in FEEDS:
        print(f"未知的 feed：{name}；可用：{', '.join(FEEDS)}", file=sys.stderr)
        return 1
    if args.sleep:
        B.SLEEP = args.sleep
    d = feed_dir(name)
    done = set()
    if os.path.isdir(d):
        done = {n[:-4] for n in os.listdir(d) if n.endswith(".csv")}
    days = [x for x in B.daterange(args.start, args.end, args.saturdays)
            if args.force or x not in done]
    if args.limit:
        days = days[:args.limit]
    print(f"[{name}] {FEEDS[name]['status']}")
    print(f"[{name}] {args.start} ~ {args.end}｜待處理 {len(days)} 天（已存在 {len(done)} 天）")
    known = B._known_codes()
    if FEEDS[name]["known"] and not known:
        print(f"[{name}] 找不到 data/meta/stocks.csv，先跑 --rebuild-meta", file=sys.stderr)
        return 1
    ok = closed = failed = 0
    for i, day in enumerate(days, 1):
        lines, note, url = fetch_one(name, day, known)
        if lines:
            n = write_day(name, day, lines)
            ok += 1
            note = f"{n} 列"
        elif note.startswith(("stat=", "日期不符")) or note.endswith("0 列"):
            closed += 1
        else:
            failed += 1
        if i % 20 == 0 or not note.endswith("列"):
            print(f"  [{i}/{len(days)}] {day} {note}", flush=True)
        # ★ 與 cmd_inst 同一條收手規則：一開始就全失敗代表端點或參數不對，
        #   不是隨機故障。放著跑只是燒時間，而且跑出來的全是錯的。
        if failed >= 5 and ok == 0:
            print(f"[{name}] 前 {i} 天全部失敗且無一成功，收手。最後一則：{note}",
                  file=sys.stderr)
            break
        time.sleep(B.SLEEP)
    print(f"[{name}] 完成：有資料 {ok} 天、無資料/休市 {closed} 天、失敗 {failed} 天")
    return 0 if (ok or not days) else 1


def cmd_probe(args):
    """只測端點、不寫任何檔案。把每個候選的結果照實印出來。

    **這是 TPEx 那幾個 feed 唯一的驗證途徑**——開發環境對 tpex.org.tw
    一律 403，只有在 Actions 上跑得到。
    """
    names = list(FEEDS) if args.feed in ("", "all") else [args.feed]
    day = args.date
    known = B._known_codes()
    print(f"[probe] 測試日 {day}｜universe 白名單 {len(known)} 檔\n")
    rc = 0
    for name in names:
        spec = FEEDS[name]
        print(f"── {name}｜{spec['status']}")
        hit = False
        for url in spec["urls"](day):
            raw, err = B.get(url, retries=1, timeout=30)
            short = url.replace("https://www.", "")
            if err:
                print(f"   ✗ {short}\n       {err[:100]}")
                continue
            try:
                d = json.loads(raw.decode("utf-8"))
            except Exception as ex:                   # noqa: BLE001
                head = raw[:100].decode("utf-8", "replace").replace("\n", " ")
                print(f"   ✗ {short}\n       非 JSON（{len(raw)}B）{type(ex).__name__}：{head}")
                continue
            stat = d.get("stat") if isinstance(d, dict) else None
            same, said = B._same_day(d, day)
            tabs = B._tables(d)
            fields = _fieldmap(tabs[0]) if tabs else []
            rows = len(tabs[0].get("data") or []) if tabs else 0
            flag = "✓" if (str(stat or "").lower() in ("ok", "success") and same) else "△"
            print(f"   {flag} {short}")
            print(f"       stat={stat}｜日期核對={'通過' if same else f'不符({said})'}"
                  f"｜表數={len(tabs)}｜首表 {rows} 列")
            if fields:
                print(f"       欄位={fields}")
            if flag == "✓":
                lines, nt = spec["parse"](d, day, known if spec["known"] else None)
                print(f"       解析結果：{nt}")
                if lines:
                    print(f"       首列={lines[0]}")
                    hit = True
                break
        if not hit:
            print("   → 沒有可用候選")
            rc = 1
        print()
    return rc


def main():
    ap = argparse.ArgumentParser(description="全市場每日 feed 回補")
    ap.add_argument("--feed", default="", help=f"{', '.join(FEEDS)}；probe 可用 all")
    ap.add_argument("--probe", action="store_true", help="只測端點，不寫資料")
    ap.add_argument("--run", action="store_true", help="逐日回補")
    ap.add_argument("--date", default="2026-09-03", help="probe 用的測試日（要是交易日）")
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--end", default="2026-09-03")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="已存在的日期也重抓")
    ap.add_argument("--saturdays", action="store_true", help="納入補行交易的週六")
    ap.add_argument("--sleep", type=float, default=0)
    a = ap.parse_args()
    if a.probe:
        return cmd_probe(a)
    if a.run:
        if not a.feed:
            print("--run 要指定 --feed", file=sys.stderr)
            return 1
        return cmd_feed(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
