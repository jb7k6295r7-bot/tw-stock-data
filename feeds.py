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
import re
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


def _roc_date(v):
    """民國「104年07月16日」→ 2015-07-16；抽不到回空字串。"""
    m = re.search(r"(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", str(v))
    if not m:
        return ""
    return f"{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def parse_exright(d, day, known=None):
    """TWSE TWT49U → 除權除息計算結果。

    這是還原價的**事件來源**：還原因子 = 除權息參考價 ÷ 除權息前收盤價。
    ★ 因子在這裡**不算**，只存原始兩個價格。理由是還原要整段回推，
      屬於 `adjust.py` 的工作；在抓取端先算一半，日後改公式就得重抓。

    ★★ **日期取每一列自己的「資料日期」欄，不用傳進來的 `day`。**
      這支端點吃的是 startDate/endDate **區間**，一次可以回一整個月，
      所以同一份回應裡的列分屬不同日子。用 `day` 會把整個月都標成同一天。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_date = _exact(f, "資料日期")
    i_code = _exact(f, "股票代號", "證券代號", "代號")
    i_pre = _exact(f, "除權息前收盤價")
    i_ref = _exact(f, "除權息參考價")
    i_val = _exact(f, "權值+息值")
    i_kind = _exact(f, "權/息")
    i_open = _exact(f, "開盤競價基準")
    if i_code is None or i_pre is None or i_ref is None:
        return [], f"欄位對不上：{f}"
    out, nodate = [], 0
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
        dt = _roc_date(r[i_date]) if (i_date is not None and i_date < len(r)) else ""
        if not dt:
            nodate += 1
            continue          # ★ 沒有自述日期就不收——寧可少一列，不要標錯日子
        out.append([dt, code, pre, ref, g(i_val),
                    (str(r[i_kind]).strip() if i_kind is not None and i_kind < len(r) else ""),
                    g(i_open)])
    note = f"{len(out)} 列"
    if nodate:
        note += f"（{nodate} 列無資料日期，已丟棄）"
    return out, note


def _pick_stock_table(tabs, *codenames):
    """多張表時挑「有代號欄且欄數最多」那張。融資融券與三大法人的回應
    第一張多半是全市場彙總（3 列），個股在第二張。"""
    best, bf = None, None
    for t in tabs:
        f = _fieldmap(t)
        if _exact(f, *codenames) is not None and (bf is None or len(f) > len(bf)):
            best, bf = t, f
    return best, bf


def _margin_rows(t, day, known, idx, tag):
    """共用的融資融券輸出與驗算。

    ★ 這裡有一條**免費的恆等式**，一定要驗：
      `今日餘額 = 前日餘額 + 買進 − 賣出 − 現償`（融券的買賣方向相反）。
      位置定位一旦錯位，這條會整片不符——**它就是位置對不對的檢驗**。
      不符的列丟掉並計數，不要靜默寫進去。
    """
    out, bad = [], 0
    g = lambda r, i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
    n = lambda v: float(str(v).replace(",", "")) if str(v).strip() not in ("", "-") else 0.0
    for r in (t.get("data") or []):
        if not r or len(r) <= idx["code"]:
            continue
        code = str(r[idx["code"]]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        vals = {k: g(r, i) for k, i in idx.items() if k != "code"}
        try:
            # 融資：今日 = 前日 + 買 − 賣 − 現償
            okm = abs(n(vals["m_prev"]) + n(vals["m_buy"]) - n(vals["m_sell"])
                      - n(vals["m_ret"]) - n(vals["m_balance"])) <= 1
            # 融券：今日 = 前日 + 賣 − 買 − 券償
            oks = abs(n(vals["s_prev"]) + n(vals["s_sell"]) - n(vals["s_buy"])
                      - n(vals["s_ret"]) - n(vals["s_balance"])) <= 1
        except (ValueError, KeyError):
            bad += 1
            continue
        if not (okm and oks):
            bad += 1
            continue
        out.append([day, code, vals["m_buy"], vals["m_sell"], vals["m_balance"],
                    vals["m_limit"], vals["s_buy"], vals["s_sell"], vals["s_balance"]])
    return out, f"{len(out)} 列可用（{tag}；餘額恆等式不符丟棄 {bad} 列）"


def parse_margin(d, day, known=None):
    """TWSE MI_MARGN 個股融資融券。

    ★★ **欄名重複，只能用位置。** 2026-09-04 Actions 實測的個股表欄位：

        代號,名稱,買進,賣出,現金償還,前日餘額,今日餘額,次一營業日限額,
                 買進,賣出,現券償還,前日餘額,今日餘額,次一營業日限額,資券互抵,註記

    融資與融券**用同一組欄名**，`_exact()` 只會回第一個命中——
    融券會整片取到融資的值。這是 T86 那次「16,394 列驗算不符」的同一種病
    （那次是互相包含，這次是完全重複），**名字定位在這裡救不了**。

    用位置就必須有守衛，否則官方改版會靜默錯位：
      ① 欄數必須剛好 16 ② 第 2 欄與第 8 欄都必須是「買進」
      ③ 第 4 欄「現金償還」、第 10 欄「現券償還」
      ④ 最後靠餘額恆等式逐列驗算
    任何一條不符就整張表拒收並回報欄名，**不要猜著往下走**。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t, f = _pick_stock_table(tabs, "代號", "股票代號", "證券代號")
    if t is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(x) for x in tabs]}"
    if len(f) != 16 or f[2] != "買進" or f[8] != "買進" \
            or f[4] != "現金償還" or f[10] != "現券償還":
        return [], (f"欄位結構與 2026-09-04 實測不符，拒收（避免位置錯位）：{f}")
    idx = {"code": 0,
           "m_buy": 2, "m_sell": 3, "m_ret": 4, "m_prev": 5, "m_balance": 6, "m_limit": 7,
           "s_buy": 8, "s_sell": 9, "s_ret": 10, "s_prev": 11, "s_balance": 12}
    return _margin_rows(t, day, known, idx, "TWSE 位置定位")


def parse_otcmargin(d, day, known=None):
    """TPEx 融資融券。**欄名不重複，可以用名字**（與 TWSE 不同，所以分開寫）。

    2026-09-04 Actions 實測欄位：
        代號,名稱,前資餘額(張),資買,資賣,現償,資餘額,資屬證金,資使用率(%),資限額,
                 前券餘額(張),券賣,券買,券償,券餘額,券屬證金,券使用率(%),券限額,
                 資券相抵(張),備註

    ★ 注意券的欄序是「**券賣在券買之前**」——照名字取就不會受影響，
      但這也是為什麼這裡不沿用 TWSE 那套位置。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t, f = _pick_stock_table(tabs, "代號", "股票代號", "證券代號")
    if t is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(x) for x in tabs]}"
    need = {"code": ("代號", "股票代號", "證券代號"),
            "m_prev": ("前資餘額(張)",), "m_buy": ("資買",), "m_sell": ("資賣",),
            "m_ret": ("現償",), "m_balance": ("資餘額",), "m_limit": ("資限額",),
            "s_prev": ("前券餘額(張)",), "s_sell": ("券賣",), "s_buy": ("券買",),
            "s_ret": ("券償",), "s_balance": ("券餘額",)}
    idx = {k: _exact(f, *names) for k, names in need.items()}
    missing = [k for k, v in idx.items() if v is None]
    if missing:
        return [], f"欄位對不上，缺 {missing}：{f}"
    return _margin_rows(t, day, known, idx, "TPEx 名稱定位")


def parse_otcinst(d, day, known=None):
    """TPEx 上櫃三大法人。**兩個年代的欄位完全不同，先試名稱、再退位置。**

    ── 舊版（2015 實測，16 欄，**欄名不重複**）──────────────────
        代號, 名稱,
        外資及陸資買股數, 外資及陸資賣股數, **外資及陸資淨買股數**,
        投信買進股數, 投信賣股數, **投信淨買股數**,
        **自營淨買股數**,                      ← 合計，單獨一欄
        自營商(自行買賣)買/賣/淨買股數,
        自營商(避險)買/賣/淨買股數,
        **三大法人買賣超股數**

    ── 新版（2026-09-03 實測，24 欄，**欄名重複七次**）───────────
        代號, 名稱, ①②③④⑤⑥⑦ 各三欄（買進/賣出/買賣超）, 三大法人買賣超股數合計
        七組依序為：①外資及陸資(不含外資自營商) ②外資自營商 **③外資合計**
                    **④投信** ⑤自營商(自行買賣) ⑥自營商(避險) **⑦自營商合計**

    **名稱定位優先。** 舊版欄名互不重複，用名字就對得到，比位置安全得多；
    新版欄名全是「買賣超股數」，名字對不到才退到位置。

    ★ 兩條路都要取**合計欄不是分項**。T86 那次就是把自營商取成避險分項——
      2018-01-03 玉山金合計 224,000、避險只有 104,000，**取錯少一半**。

    ★ 恆等式 外資 ＋ 投信 ＋ 自營 ＝ 合計 是最後的檢驗。
      不論走哪條路，對應錯了就會整片不符、整批丟棄並回報，
      **不會靜默寫進錯的數字**。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t, f = _pick_stock_table(tabs, "代號", "股票代號", "證券代號")
    if t is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(x) for x in tabs]}"

    # ── 路一：名稱定位（舊版欄名不重複時走這條）──
    i_code = _exact(f, "代號", "股票代號", "證券代號")
    i_fo = _exact(f, "外資及陸資淨買股數", "外資及陸資買賣超股數", "外資買賣超股數")
    i_tr = _exact(f, "投信淨買股數", "投信買賣超股數")
    i_dl = _exact(f, "自營淨買股數", "自營商淨買股數", "自營商買賣超股數")
    i_tt = _exact(f, "三大法人買賣超股數", "三大法人買賣超股數合計", "三大法人淨買股數")
    how = None
    if None not in (i_code, i_fo, i_tr, i_dl, i_tt):
        how = "名稱定位"
    else:
        # ── 路二：位置定位（新版欄名重複，名字救不了）──
        if len(f) != 24 or "三大法人" not in f[-1]:
            return [], (f"欄位既對不上名稱、結構也與 2026-09-04 實測的 24 欄不符，"
                        f"拒收（避免位置錯位）：{f}")
        if not all(f[i] == "買賣超股數" for i in (4, 10, 22)):
            return [], f"買賣超欄不在預期位置，拒收：{f}"
        i_code, i_fo, i_tr, i_dl, i_tt = 0, 10, 13, 22, 23
        how = "位置定位（24 欄新版）"

    out, bad = [], 0
    g = lambda r, i: float(B._num(r[i]) or 0) if i < len(r) else 0.0
    for r in (t.get("data") or []):
        if not r or len(r) <= max(i_code, i_tt):
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        fo, tr, dl, tt = g(r, i_fo), g(r, i_tr), g(r, i_dl), g(r, i_tt)
        if abs(fo + tr + dl - tt) > 1:
            bad += 1
            continue
        out.append([day, code, f"{fo:.0f}", f"{tr:.0f}", f"{dl:.0f}", f"{tt:.0f}"])
    return out, f"{len(out)} 列可用（{how}；驗算不符丟棄 {bad} 列）"


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
        # ★★ 2026-09-04 事故：原本用 `date=` 參數——**這支端點根本不吃 `date`**，
        #   但會把收到的 `date` 原樣放回 response，於是 `_same_day()` 被參數回音騙過，
        #   把 2026-09-07 的四列寫進 2015 年的每一個日期檔。
        #   實測 `date=20150123` 與 `date=20150716` 回的是同一批資料，
        #   標題都是「115年09月07日 至 115年09月07日」。
        #   正確參數是 **startDate / endDate**：
        #   `startDate=20150716&endDate=20150716` → stat=OK、標題「104年07月16日…」、30 列。
        #
        #   ★ 意外的好處：**它吃區間**，所以逐月抓一次即可，
        #     不必一天打一發。3,656 發 → 約 140 發。
        "range": True,
        "urls_range": lambda a, b: [
            "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"
            f"?startDate={a}&endDate={b}&response=json"],
        "status": ("已驗證 2026-09-04：startDate=20150716&endDate=20150716 → "
                   "stat=OK、30 列。**逐月抓**，日期取每列自己的「資料日期」欄"),
    },

    # ── 未驗證，候選清單 ────────────────────────────────────
    "margin": {
        "dir": "margin",
        "header": ["date", "stock_id", "m_buy", "m_sell", "m_balance", "m_limit",
                   "s_buy", "s_sell", "s_balance"],
        "parse": parse_margin,
        "known": True,
        "urls": lambda day: [_twse("marginTrading/MI_MARGN", day, "&selectType=ALL")],
        "status": ("已驗證 2026-09-04（Actions）：stat=OK、2 表，個股在第二張、16 欄。"
                   "★ 開發環境打同一條回「沒有符合條件的資料」，Actions 上正常——"
                   "**端點可用性要在 Actions 上判定**"),
    },
    "otcinst": {
        "dir": "otcinst",
        "header": ["date", "stock_id", "foreign", "trust", "dealer", "total"],
        "parse": parse_otcinst,
        "known": True,
        "urls": lambda day: [_tpex("insti/dailyTrade", day, "&type=Daily&sect=EW&id=")],
        "status": "已驗證 2026-09-04（Actions）：stat=ok、900 列、24 欄（七組買賣超＋合計）",
    },
    "otcper": {
        "dir": "otcper",
        "header": ["date", "stock_id", "close", "yield_pct", "dividend_year",
                   "per", "pbr", "fs_quarter"],
        "parse": parse_per,
        "known": True,
        "urls": lambda day: [_tpex("afterTrading/peQryDate", day, "&id=")],
        "status": ("已驗證 2026-09-04（Actions）：stat=ok、886 列。"
                   "★ **沒有收盤價欄**，close 一律留空（不是 0）"),
    },
    "otcmargin": {
        "dir": "otcmargin",
        "header": ["date", "stock_id", "m_buy", "m_sell", "m_balance", "m_limit",
                   "s_buy", "s_sell", "s_balance"],
        "parse": parse_otcmargin,
        "known": True,
        "urls": lambda day: [_tpex("margin/balance", day, "&id=")],
        "status": "已驗證 2026-09-04（Actions）：stat=ok、920 列、20 欄（欄名不重複，用名稱定位）",
    },
    "otcexright": {
        "dir": "otcexright",
        "header": ["date", "stock_id", "pre_close", "ref_price", "value",
                   "kind", "open_base"],
        "parse": parse_exright,
        "known": False,
        # ★ 2026-09-04 兩批共 10 條候選的結果：
        #   afterTrading/* 與 exright/* 全部 404（同一張 TPEx 404 頁）。
        #   **唯一有回應的是 `bulletin/revivt`**——stat=ok，但那是
        #   「減資恢復買賣參考價」不是除權息，而且回的是**未來十天**
        #   （20260905~20260914），被 `_same_day` 擋下。
        #
        #   兩個推論：
        #   ① **`bulletin` 才是公司行動類的區段名**，前兩批猜錯方向。
        #   ② TPEx 這類表可能是**前瞻式公告表**，不是 TWSE `TWT49U` 那種逐日結果表。
        #      若是如此，**逐日 feed 的框架對它是錯的**——要改成
        #      「定期抓一次、依事件自身日期累積」，不能用 `_same_day` 核對。
        #      所以下面這批若有一條回 stat=ok 但日期不符，**那多半就是它**，
        #      要改框架而不是繼續換網址。
        "urls": lambda day: [
            _tpex("bulletin/exRight", day, "&id="),
            _tpex("bulletin/exRightResult", day, "&id="),
            _tpex("bulletin/exDividend", day, "&id="),
            _tpex("bulletin/exRightDividend", day, "&id="),
            _tpex("bulletin/exRightAndDividend", day, "&id="),
            _tpex("bulletin/exRightCalc", day, "&id="),
        ],
        "status": ("**未驗證**。第一、二批共 10 條：afterTrading/* 與 exright/* 全 404，"
                   "只有 bulletin/revivt 有回應但那是減資表且為前瞻式。"
                   "第三批集中在 bulletin/*"),
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
    if spec.get("range"):
        return [], "這是區間型 feed，應走 cmd_feed_range", None
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


def _months(start, end):
    """→ [(該月起日, 該月迄日)]，兩端都夾在 [start, end] 內。"""
    import calendar
    y, m = int(start[:4]), int(start[5:7])
    out = []
    while True:
        last = calendar.monthrange(y, m)[1]
        a = max(f"{y:04d}-{m:02d}-01", start)
        b = min(f"{y:04d}-{m:02d}-{last:02d}", end)
        if a > end:
            break
        if a <= b:
            out.append((a, b))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def cmd_feed_range(args, name):
    """區間型 feed：逐月抓一次，再依**每列自己的日期**拆成日檔。

    為什麼不逐日：`TWT49U` 吃 startDate/endDate，一次可以回一整個月。
    逐日要 3,656 發（含休市日也得打一發才知道休市），逐月只要約 140 發。

    ★ 防呆：回應自述的日期區間必須與請求的相符（`_same_day` 已強化為
      同時檢查 title／strDate／endDate，不再只看會被回音的 `date`），
      而且**每一列的日期都必須落在請求區間內**——
      有一列落在區間外就整個月拒收並回報，不寫任何檔案。
      這是 2026-09-04 那次「2026 資料寫進 2015」之後補的第二道閘。
    """
    spec = FEEDS[name]
    known = B._known_codes()
    d = feed_dir(name)
    rng = _months(args.start, args.end)
    print(f"[{name}] {spec['status']}")
    print(f"[{name}] {args.start} ~ {args.end}｜逐月抓，共 {len(rng)} 個月")
    ok = empty = failed = 0
    total_rows = 0
    for i, (a, b) in enumerate(rng, 1):
        aa, bb = a.replace("-", ""), b.replace("-", "")
        got, note = None, "沒有候選"
        for url in spec["urls_range"](aa, bb):
            raw, err = B.get(url)
            if err:
                note = f"失敗({err[:60]})"
                continue
            try:
                doc = json.loads(raw.decode("utf-8"))
            except Exception as ex:                    # noqa: BLE001
                head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
                note = f"JSON {type(ex).__name__}｜{len(raw)}B｜開頭：{head}"
                continue
            stat = doc.get("stat") if isinstance(doc, dict) else None
            if stat and str(stat).strip().lower() not in ("ok", "success"):
                note = f"stat={stat}"
                continue
            # 自述區間核對：起日看 strDate/title，迄日看 endDate
            s_ok, s_said = B._same_day(
                {k: doc.get(k) for k in ("strDate", "title") if doc.get(k)}, a)
            if not s_ok:
                note = f"回應自述的起日不符（要 {a}）：{s_said}"
                continue
            got = doc
            break
        if got is None:
            failed += 1
            print(f"  [{i}/{len(rng)}] {a[:7]} {note}", flush=True)
            if failed >= 3 and ok == 0:
                print(f"[{name}] 前 {i} 個月全部失敗且無一成功，收手。最後一則：{note}",
                      file=sys.stderr)
                break
            time.sleep(B.SLEEP)
            continue

        lines, nt = spec["parse"](got, a, known if spec["known"] else None)
        stray = [r[0] for r in lines if not (a <= r[0] <= b)]
        if stray:
            print(f"[{name}] ★ {a[:7]} 有 {len(stray)} 列日期落在請求區間外"
                  f"（例：{stray[:3]}），整月拒收，不寫檔。", file=sys.stderr)
            failed += 1
            time.sleep(B.SLEEP)
            continue

        byday = {}
        for r in lines:
            byday.setdefault(r[0], []).append(r)
        for day, rs in byday.items():
            write_day(name, day, rs)
        if byday:
            ok += 1
            total_rows += len(lines)
        else:
            empty += 1
        if i % 12 == 0 or not byday:
            print(f"  [{i}/{len(rng)}] {a[:7]} {len(byday)} 天 / {len(lines)} 列"
                  f"（{nt}）", flush=True)
        time.sleep(B.SLEEP)
    print(f"[{name}] 完成：有資料 {ok} 個月、無事件 {empty} 個月、失敗 {failed} 個月，"
          f"合計 {total_rows} 列")
    return 0 if (ok or not rng) else 1


def cmd_purge(args):
    """刪掉某個 feed 已寫出的所有日檔。

    ★ 存在的理由：2026-09-04 的 exright 事故寫出了一批**內容是錯的**日檔
      （每個檔都是 2026-09-07 的四列）。這種錯不能靠 `--force` 覆蓋修掉——
      改用區間模式後檔名的集合會不一樣，覆蓋不到的舊檔會留在原地，
      而且它們長得跟正常檔一模一樣。**必須整個刪掉重來。**
    """
    name = args.feed
    if name not in FEEDS:
        print(f"未知的 feed：{name}", file=sys.stderr)
        return 1
    d = feed_dir(name)
    if not os.path.isdir(d):
        print(f"[{name}] {d} 不存在，沒有東西要刪")
        return 0
    files = [n for n in os.listdir(d) if n.endswith(".csv")]
    for n in files:
        os.remove(os.path.join(d, n))
    print(f"[{name}] 已刪除 {len(files)} 個日檔（{d}）")
    return 0


def cmd_feed(args):
    name = args.feed
    if name not in FEEDS:
        print(f"未知的 feed：{name}；可用：{', '.join(FEEDS)}", file=sys.stderr)
        return 1
    if args.sleep:
        B.SLEEP = args.sleep
    if FEEDS[name].get("range"):
        return cmd_feed_range(args, name)
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
    # ★ 先打一發，但**只有「被限流」才收手**。
    #   未驗證的 feed 第一個候選本來就可能 404／欄位不符——
    #   那是候選清單該由 run 淘汰的正常結果，不是中止理由。
    #   （backfill 的 preflight 兩種都擋，因為它的端點是已驗證的，
    #     第一發失敗就一定有鬼；這裡的前提不同，所以判斷也不同。）
    if days:
        cands = FEEDS[name]["urls"](days[0])
        if cands:
            _raw, _err = B.get(cands[0], retries=1, timeout=30)
            if _err and _err.startswith("LIMITED"):
                print(f"[{name}] **被交易所限流擋下**，不是端點或參數的問題。\n"
                      f"        {_err[:160]}\n"
                      f"        等一段時間再跑，或錯開同日其他回補工作。"
                      f"**不要改標頭、不要加大重試。**", file=sys.stderr)
                return 2
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
        # 區間型 feed 用「該日到該日」的單日區間探測
        if spec.get("range"):
            ymd = day.replace("-", "")
            cands = spec["urls_range"](ymd, ymd)
        else:
            cands = spec["urls"](day)
        for url in cands:
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
    ap.add_argument("--run", action="store_true", help="逐日（或逐月）回補")
    ap.add_argument("--purge", action="store_true",
                    help="刪掉該 feed 已寫出的所有日檔（內容錯掉時用，覆蓋救不回來）")
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
    if a.purge:
        if not a.feed:
            print("--purge 要指定 --feed", file=sys.stderr)
            return 1
        return cmd_purge(a)
    if a.run:
        if not a.feed:
            print("--run 要指定 --feed", file=sys.stderr)
            return 1
        return cmd_feed(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
