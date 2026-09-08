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
import calendar          # ★ cmd_probe 與 _months 都要用；原本只在 _months 內 import，
                         #   cmd_probe 改成逐月探測後會 NameError
import json
import os
import re
import sys
import time

import backfill as B
import runlog

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
    # ★ docstring 裡有正則（`\d`），**一定要用 r"""**。
    #   普通字串會在 Python 3.12 觸發 `SyntaxWarning: invalid escape sequence '\d'`，
    #   每次跑都印一行雜訊——而雜訊多了就會有人不看 log。
    r"""民國「104年07月16日」**或**「115/09/07」→ 西元 YYYY-MM-DD；抽不到回空字串。

    ★ 兩種寫法都要吃。`TWT49U` 的「資料日期」長「104年07月16日」，
      `TWTAUU`（減資恢復買賣參考價）的「恢復買賣日期」長 `115/09/07`。
      只認前者的話，減資那張表**每一列都會因為抽不到日期被丟掉**——
      而丟棄是靜默的，看起來就跟「那個月沒有減資」一模一樣。

    斜線那條刻意用 `(?<!\d)(\d{2,3})/`：西元 `2026/09/07` 不會誤中
    （四位數被前後不接數字的條件擋掉），所以不會把民國與西元搞混。
    """
    t = str(v)
    m = re.search(r"(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", t)
    if not m:
        m = re.search(r"(?<!\d)(\d{2,3})/(\d{1,2})/(\d{1,2})(?!\d)", t)
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


def parse_reduce(d, day, known=None):
    """TWSE `reducation/TWTAUU` → 股票減資恢復買賣參考價格。

    ## 為什麼一定要有這張表

    `data/adj/` 原本只還原除權息。**減資的價格跳動動輒 30～50%**：
    3536 誠創 2015-03-20 前收 6.58 → 參考 13.33（＋103%）、
    1563 巧新 2026-09-07 前收 66.00 → 參考 84.66（＋28%）。
    那是股數變少造成的，**不是真的漲**。沒有這張表，任何跨過減資日的
    回測、長期報酬率、均線與扣抵值全都是錯的。

    ## 欄位（11 欄）

    `恢復買賣日期／股票代號／名稱／停止買賣前收盤價格／恢復買賣參考價／
      漲停價格／跌停價格／開盤競價基準／除權參考價／減資原因／詳細資料`

    因子 = 恢復買賣參考價 ÷ 停止買賣前收盤價格，**在這裡不算**——
    理由同 `parse_exright`：還原要整段回推，是 `adjust.py` 的事，
    在抓取端先算一半，日後改公式就得重抓。

    ## ★ 三個跟除權息不一樣的地方

    1. **日期格式是 `115/09/07`（斜線）**，不是「115年09月07日」。
       `_roc_date()` 已同時吃兩種。
    2. **`pre_close` 不是「前一個交易日」的收盤。** 減資會停止買賣數個交易日，
       它是**停止買賣前**最後一個有成交的日子的收盤。核對要拿「該檔在恢復
       買賣日之前最後一筆收盤」比，拿日曆的前一交易日比會整片假警報
       （做法見 `adjust.py` 的 `_verify_reduce`）。
    3. **因子會 > 1，而且可以很大。** 減資九成的話接近 10。
       `adjust.py` 那組 `0.05 < f ≤ 1.5` 的除權息界線套上來會把真事件全丟掉，
       所以界線改成**按事件種類分開**。

    ## ★ 減資與除權息同一天時只能算一次

    官方公式明寫「退還股款：恢復買賣參考價＝（停止買賣前收盤價−息值−每股退還
    股款）／（減資換股率）」——**息值已經含在裡面了**。同一天 `TWT49U` 也會有
    一列，兩邊都收就會把除息扣兩次。去重在 `adjust.py`，這裡照實全收。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_date = _exact(f, "恢復買賣日期")
    i_code = _exact(f, "股票代號", "證券代號", "代號")
    i_pre = _exact(f, "停止買賣前收盤價格", "停止買賣前收盤價")
    i_ref = _exact(f, "恢復買賣參考價", "恢復買賣參考價格")
    i_reason = _exact(f, "減資原因")
    i_open = _exact(f, "開盤競價基準")
    i_exref = _exact(f, "除權參考價")
    if i_code is None or i_pre is None or i_ref is None or i_date is None:
        return [], f"欄位對不上：{f}"
    out, nodate, noprice = [], 0, 0
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
        if not pre or not ref:
            noprice += 1
            continue          # 兩個價格缺一就算不出因子，寧可少一列
        dt = _roc_date(r[i_date]) if i_date < len(r) else ""
        if not dt:
            nodate += 1
            continue          # ★ 沒有自述日期就不收——寧可少一列，不要標錯日子
        reason = (str(r[i_reason]).strip()
                  if i_reason is not None and i_reason < len(r) else "")
        out.append([dt, code, pre, ref, reason.replace(",", "；"),
                    g(i_open), g(i_exref)])
    note = f"{len(out)} 列"
    if nodate:
        note += f"（{nodate} 列無日期，已丟棄）"
    if noprice:
        note += f"（{noprice} 列缺價格，已丟棄）"
    return out, note


def parse_parvalue(d, day, known=None):
    """TWSE `change/TWTB8U` → 變更股票面額恢復買賣參考價格。

    ## 為什麼不直接用 `parse_reduce`

    欄位是 `TWTAUU` 的子集，解析邏輯一模一樣，所以**本函式就是呼叫它**——
    多一份幾乎相同的解析程式，等於多一處會各自飄移的地方。

    但 `parse_reduce` **把第 9 欄「詳細資料」丟掉了**，而那一欄是
    `代號,停止買賣起日,恢復買賣日`：

        8070,20200806,20200817
        7780,20260109,20260119

    ★ **那正是「停止買賣區間」，而且它是官方直接宣告的。** 2026-09-09 核對：
      8070 官方停止買賣起日 2020-08-06、恢復買賣日 2020-08-17；
      `parvalue_scan.py` 掃到的最後有成交日是 2020-08-05、復牌首成交日 2020-08-17。
      **恢復買賣日完全一致，停止買賣起日正好是最後有成交日的下一天。** 7780 同。

    ⚠ 為什麼非留不可：`data/meta/suspend.csv` **收的是暫停交易，不含換發新股票的
      停止買賣**——24 筆面額變更拿去對它，`resume_date` 命中 **0 筆**。
      丟掉這一欄，那段停止買賣區間就**整個資料庫都沒有第二個地方查得到**。

    所以本函式在 `parse_reduce` 的七欄之後補一欄 `halt_date`（停止買賣起日）。
    恢復買賣日不另存——它就是第一欄 `date`，存兩份會飄移。
    """
    rows, note = parse_reduce(d, day, known)
    if not rows:
        return rows, note
    tabs = B._tables(d)
    t = tabs[0] if tabs else {}
    f = _fieldmap(t)
    i_det = _exact(f, "詳細資料")
    i_code = _exact(f, "股票代號", "證券代號", "代號")
    # 「代號 → 停止買賣起日」對照。**用代號配對，不用列序**——
    # parse_reduce 會丟掉缺價格／缺日期的列，列序早就對不上了
    # （這正是 mops 那個「用位置對欄位」踩過的同一種坑）。
    halt = {}
    if i_det is not None and i_code is not None:
        for r in (t.get("data") or []):
            if not r or len(r) <= max(i_det, i_code):
                continue
            parts = [x.strip() for x in str(r[i_det]).split(",")]
            digits = [x for x in parts if x.isdigit() and len(x) == 8]
            if digits:
                halt[str(r[i_code]).strip()] = (
                    f"{digits[0][:4]}-{digits[0][4:6]}-{digits[0][6:]}")
    out = [row + [halt.get(row[1], "")] for row in rows]
    miss = sum(1 for row in out if not row[-1])
    if miss:
        note += f"（{miss} 列抽不到停止買賣起日）"
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

def _paren(v):
    """『587(19)』→ ('587', '19')。沒有括號就回 (值, '')。"""
    t = str(v).strip()
    if "(" in t and t.endswith(")"):
        main, _, rest = t.partition("(")
        return _blank_num(main), _blank_num(rest[:-1])
    return _blank_num(t), ""


def parse_breadth(d, day, known=None):
    """TWSE MI_INDEX → 當天上市的漲跌證券數（大盤層級彙總）。

    ★ 這是**日檔的外部判準**：日檔由個股端點建，這張表由大盤端點來，
      兩條不同的路。整批漏抓時日檔家數會掉、這裡不會。
      判讀方式見 `breadth_audit.py`。

    ⛔ **一律取「股票」那一欄，不是「整體市場」**——後者含權證與 ETF，
      拿它跟日檔的普通股比會多出好幾千，差值整個沒有意義。
      （這一條與 `fetch.py` 的當日版本同一個判準，不可分岔。）

    ⚠ MI_INDEX 一個回應塞好幾張表（`B._tables()` 已處理三種形狀），
      **不可以假設資料在第一張**——第二條坑就是這樣來的。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = None
    for x in tabs:
        f = [str(y) for y in (x.get("fields") or [])]
        labels = " ".join(str(r[0]) for r in (x.get("data") or []) if r)
        if "股票" in f and ("上漲" in labels or "漲跌證券數" in str(x.get("title", ""))):
            t = x
            break
    if t is None:
        return [], f"找不到漲跌證券數那張表（共 {len(tabs)} 張）"
    f = [str(y) for y in (t.get("fields") or [])]
    col = f.index("股票")
    v = {"up": "", "down": "", "flat": "", "lu": "", "ld": ""}
    for r in (t.get("data") or []):
        if not r or len(r) <= col:
            continue
        lab = str(r[0])
        main, paren = _paren(r[col])
        if "上漲" in lab:
            v["up"], v["lu"] = main, paren
        elif "下跌" in lab:
            v["down"], v["ld"] = main, paren
        elif "持平" in lab or "平盤" in lab:
            v["flat"] = main
    if not (v["up"] and v["down"]):
        return [], f"表找到了但取不到值：{[str(r[0]) for r in (t.get('data') or [])][:6]}"
    return ([[day, v["up"], v["down"], v["flat"], v["lu"], v["ld"]]],
            f"漲 {v['up']}／跌 {v['down']}／平 {v['flat']}")


def _twse(path, day, extra=""):
    return f"https://www.twse.com.tw/rwd/zh/{path}?date={day.replace('-', '')}{extra}&response=json"


def _tpex(path, day, extra=""):
    return f"https://www.tpex.org.tw/www/zh-tw/{path}?date={day.replace('-', '/')}{extra}&response=json"


FEEDS = {
    # ── 已驗證 ──────────────────────────────────────────────
    "breadth": {
        "dir": "breadth",
        "header": ["date", "up", "down", "flat", "limit_up", "limit_down"],
        "parse": parse_breadth,
        "known": False,          # 這是大盤合計，沒有個股代號要過濾
        "urls": lambda day: [_twse("afterTrading/MI_INDEX", day,
                                   "&type=ALLBUT0999")],
        "status": ("大盤漲跌證券數，**日檔的外部判準**。MI_INDEX 吃 date 參數，"
                   "所以 2015 起可以回補——`market_breadth.csv` 只有 2026-09-01 起，"
                   "是 v6 才開始存的，不是端點沒有歷史"),
    },
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
        # 探測用的「已知有事件」區間：2015-07 是除權息旺季，一定回得到列。
        "probe_range": ("20150701", "20150731"),
        "status": ("已驗證 2026-09-04：startDate=20150716&endDate=20150716 → "
                   "stat=OK、30 列。**逐月抓**，日期取每列自己的「資料日期」欄"),
    },

    "reduce": {
        "dir": "reduce",
        "header": ["date", "stock_id", "pre_close", "ref_price", "reason",
                   "open_base", "ex_ref_price"],
        "parse": parse_reduce,
        "known": False,   # 減資表會有已下市或非 universe 的標的，先全收
        "range": True,
        # ★ **這是前瞻式公告表**：恢復買賣參考價在停止買賣期間就先公告，
        #   所以當月的回應會帶**未來日期**的列（2026-09-06 實測回到 115/09/29）。
        #   舊的 stray 檢查是 `a <= 日期 <= b`，b 取 min(月底, --end)，
        #   於是當月**整月被拒收**——2026-09 一列都沒寫進來。
        #
        #   ★★ 2026-09-06 二修：第一版讓它「照收未來列」，**那是錯的**。
        #     `data/universe/<feed>/<日期>.csv` 的意思是「那一天發生了什麼」，
        #     而還原因子的不變量是「**最新價的 F = 1，現價不動**」。
        #     收下 09/07 的減資，今天 1563 的收盤 66.00 會被一個**還沒發生**的
        #     事件還原成 84.66——報告上的價位就跟看盤軟體對不起來了。
        #     而且公告可能延期或取消，日檔會留在原地變成幽靈。
        #
        #   → `announce_ahead` 的正確語意是：**未來日期的列丟掉，但不因此拒收整月**，
        #     並在摘要把它們列出來（知道有減資要來是有用的，只是不進因子）。
        #     等事件日過了，下次跑同一個月自然就收進來。
        "announce_ahead": True,
        # ★ 2026-09-06 用 WebFetch 實測（工具要標明——見 READ_CONTRACT 的教訓）：
        #   `startDate=20150101&endDate=20151231` → stat=OK、
        #   title「104年01月01日 至 104年12月31日 股票減資恢復買賣參考價格」、**26 列**，
        #   首列 104/01/23 3040 遠見 31.90 → 41.28「退還股款」。
        #   **有歷史，2015 年以來補得回來**，不是只有前瞻十日的公告表。
        #   回應是平的（沒有 tables），有 strDate／endDate，`_same_day` 擋得住參數回音。
        #
        #   ⚠ **沒有事件的月份回 `{"stat":"很抱歉，沒有符合條件的資料!"}`**——
        #   沒有 title、沒有 data。減資本來就少（一年 20~30 件），
        #   多數月份都是這個回應。`cmd_feed_range` 已把它認成「無事件」而不是失敗，
        #   否則會報成七成的月份都失敗，真的失敗就被雜訊蓋掉。
        #
        #   ※ TWTB8U 是**變更股票面額**恢復買賣參考價，是另一種公司行動，不要混用。
        "urls_range": lambda a, b: [
            "https://www.twse.com.tw/rwd/zh/reducation/TWTAUU"
            f"?startDate={a}&endDate={b}&response=json"],
        # ★ 探測用的「已知有事件」區間。**減資一年只有 20~30 件**，
        #   隨便挑一天去探幾乎一定回「查無資料」——那不是端點壞掉。
        #   2015 全年實測 26 列，拿它當探測基準才驗得到「解析得出來」。
        "probe_range": ("20150101", "20151231"),
        "status": ("已驗證 2026-09-06（WebFetch）：2015 全年 26 列、2026 上半年 2 列。"
                   "**逐月抓**，日期取每列自己的「恢復買賣日期」欄（格式 115/09/07）"),
    },

    # ★★ 變更股票面額恢復買賣參考價。2026-09-09 00:30 於 Actions 驗到，
    #   四項判準全過（`parvalue_probe.py` → `data/meta/_parvalue_probe.txt`）：
    #     [1] stat=OK、title「變更股票面額恢復買賣參考價格」
    #     [2] 9 欄完整
    #     [3] 三個區間列數不同（0／1／2）
    #     [4] 日期欄 109/08/17、115/01/19 ~ 115/09/07 → **有歷史**
    #   而且**參數確定有生效**（三個區間回不同內容，不是 TWT49U 那種參數回音）。
    #
    #   ★ 官方回的數字與 `parvalue_scan.py` 的全庫掃描**逐格對上**：
    #     109/08/17 8070 長華 停止買賣前收盤 190.00 → 恢復買賣參考價 19.00
    #       掃描：8070 T=2020-08-17，前一次有成交收 190 → 復牌收 20.90
    #     115/01/19 7780 大研生醫 185.00 → 18.50
    #       掃描：7780 T=2026-01-19，185 → 20.35
    #   **前收盤兩邊一模一樣**，官方因子 19/190 ＝ 18.5/185 ＝ 0.10（面額 10→1）。
    #   掃描的比值 0.110 略高，差的是停止買賣那 7~8 天的漲跌——
    #   所以**因子要用官方的 ref/pre，不是用價格比值**。
    #
    #   ⚠ 這張表**只涵蓋上市**。上櫃 14 筆（6548、5314、5904…）還沒有來源，
    #     TPEx 的對應端點尚未找到——`db_status` 那條缺口只收掉一半。
    #
    #   欄位是 TWTAUU 的子集（少了「減資原因」與「除權參考價」），
    #   `parse_reduce` 的 `_exact` 找不到就給空字串，所以**沿用它、不另寫解析**：
    #   多一份幾乎一樣的解析程式＝多一處會各自飄移的地方。
    "parvalue": {
        "dir": "parvalue",
        # ★ 比減資多一欄 `halt_date`＝**停止買賣起日**（取自官方「詳細資料」欄）。
        #   `suspend.csv` 收的是暫停交易、不含換發新股票的停止買賣，
        #   24 筆面額變更拿去對它 `resume_date` 命中 0 筆——
        #   **丟掉這一欄，那段區間整個資料庫就沒有第二個地方查得到。**
        #   恢復買賣日不另存：它就是第一欄 `date`。
        "header": ["date", "stock_id", "pre_close", "ref_price", "reason",
                   "open_base", "ex_ref_price", "halt_date"],
        "parse": parse_parvalue,
        "known": False,
        "range": True,
        "announce_ahead": True,     # 與減資同一張形態的前瞻公告表
        "urls_range": lambda a, b: [
            "https://www.twse.com.tw/rwd/zh/change/TWTB8U"
            f"?startDate={a}&endDate={b}&response=json"],
        # 面額變更比減資更少（全庫 2015 起上市只有 10 筆），
        # 隨便挑一個月去探幾乎一定空手——拿 2020 全年當基準（實測 1 列）。
        "probe_range": ("20200101", "20201231"),
        "status": ("已驗證 2026-09-09（Actions probe）：2015 全年 0 列、"
                   "2020 全年 1 列（8070 長華）、2026 至今 2 列（7780、6949）。"
                   "**只有上市**，上櫃無對應端點"),
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
    # NODATA 代表「端點答了、只是那天沒有資料」——回傳 url 讓呼叫端歸到「休市」。
    if last.startswith("NODATA"):
        return [], last[7:], (spec["urls"](day) or [None])[0]
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


# 端點自己說「查無資料」時的字樣。**這代表那段期間沒有事件，不是抓取失敗。**
_EMPTY_STAT_RE = re.compile(r"沒有符合條件的資料|查無資料|無符合條件|沒有資料")
_EMPTY = object()          # cmd_feed_range 內部用的哨符：這個月沒有事件


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
    fwd = bool(spec.get("announce_ahead"))
    n_future, future_rows = 0, []
    for i, (a, b) in enumerate(rng, 1):
        # 前瞻式公告表：請求與 stray 檢查都用**月底**當上界，否則當月的未來日期列
        # 會落在區間外，整月被拒收（見 FEEDS["reduce"] 的 announce_ahead 註解）。
        # ★ 上界放寬只是為了「不要整月拒收」，**未來的列照樣不寫**，見下方。
        b_lim = (f"{a[:7]}-{calendar.monthrange(int(a[:4]), int(a[5:7]))[1]:02d}"
                 if fwd else b)
        aa, bb = a.replace("-", ""), b_lim.replace("-", "")
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
                # ★ 「查無資料」與「失敗」是兩件事，不可混為一談。
                #   除權息每個月都有事件，所以踩不到；**減資一年只有 20~30 件**，
                #   七成以上的月份會回「很抱歉，沒有符合條件的資料!」。
                #   把它算成失敗的話：①摘要會寫「失敗 100 個月」，真的失敗被蓋掉
                #   ②前三個月剛好都沒事件就會觸發「全部失敗」的提早收手。
                if _EMPTY_STAT_RE.search(str(stat)):
                    got, note = _EMPTY, f"stat={stat}"
                    break
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
        if got is _EMPTY:
            empty += 1
            time.sleep(B.SLEEP)
            continue

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
        stray = [r[0] for r in lines if not (a <= r[0] <= b_lim)]
        if fwd:
            # ★ 未來日期的列**不寫檔**。它們是公告、不是已發生的事件，
            #   寫進去會讓還原因子由尚未發生的事件產生（見上方註解）。
            fut = [r for r in lines if r[0] > b]
            if fut:
                n_future += len(fut)
                future_rows.extend(fut)
                lines = [r for r in lines if r[0] <= b]
                nt += (f"（另有 {len(fut)} 列**尚未到期的公告，未寫入**："
                       f"{sorted({r[0] for r in fut})[:4]}）")
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
          f"合計 {total_rows} 列"
          + (f"；另有 {n_future} 列**尚未到期的公告，未寫入**" if n_future else ""))
    if future_rows:
        # 印出來是刻意的：知道有減資要來很有用（那幾天會停止買賣），
        # 只是它不該進還原因子。等事件日過了再跑一次同一個月就會收進來。
        print(f"[{name}] 尚未到期的公告（**不在資料庫裡**，僅供知悉）：")
        for r in sorted(future_rows)[:20]:
            print(f"        {r[0]}  {r[1]}  {'  '.join(str(x) for x in r[2:5])}")

    # ★ 寫進 data/meta/_last_run.md。⛔ 區塊名帶 feed 名——`daily.yml` 一趟裡
    #   exright 與 reduce 都走這條路徑，共用名字會互相蓋掉。
    #   ⚠ **不檢查「ok > 0」**：exright／reduce 抓的是當月區間，
    #     整個月沒有任何除權息或減資事件是**正常**的（尤其月初）。
    #     拿它當失敗會讓這一頁每個月初都紅（防護誤殺跟防護失效一樣糟）。
    rl = runlog.Run(f"feeds:{name}")
    rl.info("區間", f"{args.start} ~ {args.end}｜{len(rng)} 個月")
    rl.info("結果", f"有資料 {ok} 個月、無事件 {empty} 個月、失敗 {failed} 個月，"
                    f"合計 {total_rows} 列")
    # ⚠ 尚未到期的公告做成 info 不做成 check：減資與除權息本來就提前公告，
    #   擋下來是正常運作。要抓的是「擋漏了」，那一條在 adjust 那邊
    #   （寫出去的因子有沒有晚於資料最後一天）。
    if n_future:
        rl.info("尚未到期的公告", f"{n_future} 列（正常，事件日到了會自然進來）")
    rl.check("每個月都問到了", failed == 0,
             f"失敗 {failed} / {len(rng)} 個月" if failed else f"{len(rng)} 個月全問到")
    # ⛔ finish() 一定要無條件呼叫——寫在三元運算的其中一支，
    #    「這一趟成功」時區塊就不會寫出去，而那正是最常見的情況。
    rc = rl.finish()
    base = 0 if (ok or not rng) else 1
    return 1 if (base or rc) else 0


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


DAILY_DIR = os.path.join(UNI_DIR, "daily")


def trading_calendar():
    """交易日曆＝`data/universe/daily/` 的檔名集合。→ 升冪日期字串 list。

    ★★ 為什麼不再掃「週一到週六」（2026-09-05 改）：

    | 做法 | 天數 | 5.5s/天 |
    |---|---|---|
    | 週一～五 | 3,047 | 279 分 ← **會漏掉補行交易的週六** |
    | 週一～六 | 3,656 | 335 分 ← 舊做法，**超過 job 上限 350 分** |
    | **照交易日曆** | **2,844** | **261 分** ← 一趟跑得完 |

    掃非交易日是純粹的浪費：812 個請求（22%）、74 分鐘，換來的只有
    一整排「沒有符合條件的資料」。而且那些雜訊還害過一次——
    `margin` 續跑時前五天剛好全是休市，觸發「連續失敗」收手，
    訊息還寫成「連問都問不到」，完全誤導。

    **補行交易的週六本來就在日曆裡**（價格資料是逐日抓的，那幾天有檔），
    所以照日曆走比 `--saturdays` 更準，不是更省而已。

    ★ 上市與上櫃共用同一份交易日曆（`tw-technical-analysis` 實測
      8096、5274 對 3042 皆 728/728 完全相同），所以 TPEx 的 feed
      也適用這份日曆。

    拿不到日曆時回空 list，呼叫端會退回原本的掃描法——
    **不要在拿不到日曆時安靜地少抓**。
    """
    if not os.path.isdir(DAILY_DIR):
        return []
    return sorted(n[:-4] for n in os.listdir(DAILY_DIR)
                  if n.endswith(".csv") and n[0].isdigit())


def _target_days(args):
    """→ (日期 list, 用了哪種來源)。"""
    cal = trading_calendar()
    if cal:
        return [d for d in cal if args.start <= d <= args.end], f"交易日曆（{len(cal)} 天）"
    # ★ 退路一律**含週六**，不看 --saturdays。
    #   兩種錯的代價不對稱：多掃週六只是浪費時間，
    #   漏掉補行交易日是**安靜的資料缺口**——事後從檔案上看不出來。
    #   （`--saturdays` 保留只為相容既有指令，實際不影響結果。）
    # ★ daterange 回的是 generator，這裡一定要 list() ——
    #   否則呼叫端第二次用到它時已經耗盡，會安靜地變成 0 天。
    return (list(B.daterange(args.start, args.end, True)),
            "逐日掃描（找不到交易日曆，退回含週六的全掃）")


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
    days, how = _target_days(args)
    days = [x for x in days if args.force or x not in done]
    if args.limit:
        days = days[:args.limit]
    print(f"[{name}] {FEEDS[name]['status']}")
    print(f"[{name}] {args.start} ~ {args.end}｜{how}｜"
          f"待處理 {len(days)} 天（已存在 {len(done)} 天）")
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
    ok = closed = failed = dropped_days = 0
    bailed = ""     # 提前收手的原因；空字串＝跑完整個區間
    for i, day in enumerate(days, 1):
        lines, note, url = fetch_one(name, day, known)
        # ★★ 成敗**看 `url` 有沒有拿到，不要比對訊息字串**。
        #   `fetch_one` 只有在「請求成功 ＋ stat 正常 ＋ 日期核對通過」時才回傳 url，
        #   所以 url 就是「這一天確實問到了、只是可能沒有資料」的信號。
        #
        #   原本寫 `note.endswith("0 列")`，而 parser 後來改成回
        #   「0 列可用（名稱定位；驗算不符丟棄 0 列）」——結尾是全形括號，對不到，
        #   於是**休市日被算成失敗**。區間開頭若撞上農曆年（連休 5～9 天），
        #   `failed >= 5 且 ok == 0` 就會收手，並印一句「端點或參數不對」，
        #   而端點根本沒問題。**訊息字串是給人看的，不是狀態機的輸入。**
        if lines:
            n = write_day(name, day, lines)
            ok += 1
            # ★ **不要把 parser 的訊息蓋掉。** 它帶著「恆等式不符丟棄 N 列」，
            #   蓋掉之後每天默默丟幾十列也看不出來——正是這個專案一路在防的靜默。
            #   丟棄數為 0 時才簡化成「N 列」，避免每行都拖一串括號。
            note = f"{n} 列" if "丟棄 0 列" in note or "丟棄" not in note else f"{n} 列｜{note}"
            if "丟棄" in note and "丟棄 0 列" not in note:
                dropped_days += 1
        elif url is not None:
            closed += 1               # 問到了，那天沒有資料（休市或無事件）
        else:
            failed += 1               # 根本沒問到
        if i % 20 == 0 or url is None:
            print(f"  [{i}/{len(days)}] {day} {note}", flush=True)
        # ★ 與 cmd_inst 同一條收手規則：一開始就全失敗代表端點或參數不對，
        #   不是隨機故障。放著跑只是燒時間，而且跑出來的全是錯的。
        # ★ 端點一直回「沒有符合條件的資料」也要收手。
        #   這種情況 failed 恆為 0（它有回應），舊的閘門擋不住——
        #   若端點有**日期下限**（例如只回得到近幾年），整趟會安靜跑滿
        #   5.8 小時、一列都沒寫，最後才發現。30 天足以跨過任何連假。
        if closed >= 30 and ok == 0:
            bailed = f"連續 {i} 天回「沒有資料」且無一有列（很可能有日期下限）"
            print(f"[{name}] 前 {i} 天全部回「沒有資料」且無一有列，收手。"
                  f"端點是通的，但這個區間查不到東西——**很可能有日期下限**，"
                  f"不是連假。最後一則：{note}", file=sys.stderr)
            break
        # 只數「根本沒問到」的天數。休市不算失敗，否則農曆年會被誤判成端點壞掉。
        if failed >= 5 and ok == 0:
            bailed = f"前 {i} 天有 {failed} 天連問都問不到且無一成功"
            print(f"[{name}] 前 {i} 天有 {failed} 天連問都問不到且無一成功，收手。"
                  f"最後一則：{note}", file=sys.stderr)
            break
        time.sleep(B.SLEEP)
    print(f"[{name}] 完成：有資料 {ok} 天、無資料/休市 {closed} 天、失敗 {failed} 天")
    if dropped_days:
        print(f"[{name}] ⚠ 有 {dropped_days} 天出現驗算不符而丟棄的列（詳見上面各該日）。"
              f"**丟棄不是零就要看過**——可能是欄位對應在某個年代變了。", file=sys.stderr)
    # ★ 只有「真的失敗」才回非零。**「一天資料都沒有」不等於出錯**——
    #   補單一缺日時，區間內其餘天數可能全是週六或連假，
    #   那時 ok=0、failed=0，是正常結果。
    #   原本寫 `return 0 if (ok or not days) else 1`，這種情況會回 exit code 1，
    #   Actions 上顯示紅叉。**讓成功的跑印出紅叉，會訓練人忽略紅叉**，
    #   下次真的失敗就看不見了。

    # ★ 寫進 data/meta/_last_run.md。
    #   ⛔ 區塊名一定要帶 feed 名。`daily.yml` 一趟裡呼叫本支三次
    #      （otcinst／exright／reduce），共用一個名字的話後面兩次會蓋掉前面，
    #      那一頁只剩最後跑的 reduce——**正是 runlog 存在要防的那件事**。
    #   ⚠ 每條檢查都先問「今天有沒有收到東西」才驗內容：exright／reduce 抓的是
    #     當月區間，沒有事件的月份 ok=0 是**正常**的，不可以拿它當失敗
    #     （防護誤殺跟防護失效一樣糟）。
    rl = runlog.Run(f"feeds:{name}")
    rl.info("區間", f"{args.start} ~ {args.end}｜待處理 {len(days)} 天")
    rl.info("結果", f"有資料 {ok} 天、無資料/休市 {closed} 天、失敗 {failed} 天")
    # ⛔ 提前收手在 Actions 上是看不見的（這幾步都是 continue-on-error），
    #    而收手代表整趟根本沒跑完——這是要紅的，不是資訊。
    rl.check("跑完整個區間，沒有提前收手", not bailed, bailed or "跑完")
    rl.check("沒有「連問都問不到」的日子", failed == 0,
             f"失敗 {failed} 天" if failed else "0 天")
    # ⛔ 丟棄不是零就要看過——可能是欄位對應在某個年代變了，
    #    而每天默默丟幾十列外表完全正常。
    rl.check("沒有因驗算不符而丟棄列的日子", dropped_days == 0,
             f"{dropped_days} 天有丟棄" if dropped_days else "0 天")
    rc = rl.finish()
    return 1 if (failed or rc) else 0


def cmd_probe(args):
    r"""只測端點、不寫任何檔案。把每個候選的結果照實印出來。

    **這是 TPEx 那幾個 feed 唯一的驗證途徑**——開發環境對 tpex.org.tw
    一律 403，只有在 Actions 上跑得到。

    ★★ **事件型的區間 feed 不能用單日探測。**（2026-09-06 踩到）

      `--probe --feed reduce --date 2026-09-03` 回報「沒有可用候選」並 exit 1，
      看起來像端點壞掉。實際上端點是好的、參數是對的、日期核對也過了，
      只是**那天沒有減資事件**，所以 TWSE 回
      `{"stat":"很抱歉，沒有符合條件的資料!"}`。
      減資一年只有 20~30 件，**隨便挑一天去探幾乎一定是空的**。

      這正是這個專案一路在防的那種錯：把「查無資料」讀成「端點不可用」。
      判準錯了會讓人去修一個根本沒壞的東西，或反過來把壞掉的當成正常。

      → 改成兩段探測：
        ① 先試**該日所在的整月**（貼近實際使用形狀——本來就是逐月抓）
        ② 仍為空就試 spec 的 `probe_range`，那是**已知有事件**的區間

      **探測要驗的是「解析得出來」，不是「那天剛好有事」。**
      兩段都空才算失敗，而且會明說是空、不是不通。
    """
    names = list(FEEDS) if args.feed in ("", "all") else [args.feed]
    day = args.date
    known = B._known_codes()
    print(f"[probe] 測試日 {day}｜universe 白名單 {len(known)} 檔\n")
    rc = 0
    for name in names:
        spec = FEEDS[name]
        print(f"── {name}｜{spec['status']}")

        # 探測窗：非區間型就是那一天；區間型是「該月」→「已知有事件的區間」
        if spec.get("range"):
            y, m = int(day[:4]), int(day[5:7])
            last = calendar.monthrange(y, m)[1]
            wins = [(f"{y:04d}-{m:02d}-01",
                     f"{y:04d}{m:02d}01", f"{y:04d}{m:02d}{last:02d}", "該月")]
            pr = spec.get("probe_range")
            if pr:
                wins.append((f"{pr[0][:4]}-{pr[0][4:6]}-{pr[0][6:8]}",
                             pr[0], pr[1], "已知有事件的區間"))
        else:
            wins = [(day, None, None, "")]

        hit = emptied = False
        for cmp_day, aa, bb, tag in wins:
            if spec.get("range"):
                cands = spec["urls_range"](aa, bb)
                print(f"   [{tag} {aa}~{bb}]")
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
                except Exception as ex:               # noqa: BLE001
                    head = raw[:100].decode("utf-8", "replace").replace("\n", " ")
                    print(f"   ✗ {short}\n       非 JSON（{len(raw)}B）"
                          f"{type(ex).__name__}：{head}")
                    continue
                stat = d.get("stat") if isinstance(d, dict) else None

                # ★ 「查無資料」先攔下來，**不要落進「沒有可用候選」**。
                #   端點通、參數對，只是那個區間沒有事件——這是結論，不是失敗。
                if stat and _EMPTY_STAT_RE.search(str(stat)):
                    print(f"   ○ {short}")
                    print(f"       stat={stat}")
                    print("       → **端點通、這個區間沒有事件**（不是端點不可用）")
                    emptied = True
                    continue

                # ★ 區間型不能整包丟給 `_same_day`：它會拿 `endDate` 去比起日，
                #   多日區間**一定不符**（20151231 ≠ 20150101），
                #   於是好端端的回應被標成 △、解析根本不會跑。
                #   `cmd_feed_range` 早就只挑 strDate／title 比，這裡照做。
                if spec.get("range"):
                    same, said = B._same_day(
                        {k: d.get(k) for k in ("strDate", "title") if d.get(k)},
                        cmp_day)
                else:
                    same, said = B._same_day(d, cmp_day)
                tabs = B._tables(d)
                fields = _fieldmap(tabs[0]) if tabs else []
                rows = len(tabs[0].get("data") or []) if tabs else 0
                flag = "✓" if (str(stat or "").lower() in ("ok", "success") and same) \
                    else "△"
                print(f"   {flag} {short}")
                print(f"       stat={stat}｜日期核對="
                      f"{'通過' if same else f'不符({said})'}"
                      f"｜表數={len(tabs)}｜首表 {rows} 列")
                if fields:
                    print(f"       欄位={fields}")
                if flag == "✓":
                    lines, nt = spec["parse"](
                        d, cmp_day, known if spec["known"] else None)
                    print(f"       解析結果：{nt}")
                    if lines:
                        print(f"       首列={lines[0]}")
                        hit = True
                    break
            if hit:
                break

        if not hit:
            if emptied:
                # 端點是通的，只是探到的區間沒有事件。這**不是**端點問題，
                # 但也還沒驗到解析——照實說，不要含糊成「可用」或「不可用」。
                print("   → **端點通但探測區間內沒有事件，解析未驗到。**"
                      "換一個確定有事件的區間再探（改 probe_range 或 --date）")
            else:
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
    ap.add_argument("--saturdays", action="store_true",
                    help="（已無作用）改照 data/universe/daily 的交易日曆走；"
                         "拿不到日曆時的退路一律含週六。保留只為相容既有指令。")
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
