#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_history.py — 把月營收與財報的**歷史**從 MOPS 補回來。

## 為什麼是這兩條路（2026-09-06 兩輪探測的結論）

| 路 | 結論 |
|---|---|
| TWSE／TPEx **OpenAPI**（`mops.py` 現在走的）| **只有最新一期。** 四種期別參數寫法回的東西與不帶參數**完全相同**＝參數被無視 |
| **`mopsov.twse.com.tw/nas/t21/{sii,otc}/t21sc03_<年>_<月>_0.html`** | ★ **月營收，有歷史。** 換月份指紋全不同，且頁面自述期別與請求相符 |
| **`mopsov.twse.com.tw/mops/web/ajax_t163sb04 / t163sb05`**（POST）| ★ **財報，有歷史。** 換年度季別指紋全不同，列數隨年份單調成長（sii 844→963→1096），與上市家數逐年增加獨立吻合 |
| FinMind | 可用，但官方更乾淨，留作備案 |

⚠ **這些頁面在 `robots.txt` 是 disallow 的**（WebFetch 會被擋）。
量很小（月營收 282 發、財報 188 發）且每發之間有 sleep，
但**這件事寫在這裡是要讓人看見的**，不是藏起來。

## ★ 先跑 `--dry`，不要直接回補

我寫這支的時候**看不到頁面的 HTML**（robots 擋住），表格結構是照 MOPS 的慣例推的。
所以預設是 `--dry`：**只抓一期、把解析出來的東西印出來、不寫任何檔**。

`--dry` 會印：抓到幾張表、哪幾張被認成資料表、表頭的每一欄、前三列、
以及**沒有被認出來的表的表頭**（那才是看得出漏掉什麼的地方）。

看過 `--dry` 的輸出確認欄位對得上，再加 `--run`。
**470 發的回補不該建立在猜出來的 parser 上。**

## 輸出要與 `mops.py` 併得起來

現有格式（實測 `data/mops/revenue/2026-07.csv`）：

    stock_id,name,period,market,出表日期,資料年月,公司代號,公司名稱,產業別,
    營業收入-當月營收,…,備註

前四欄是管線自己加的，後面照抄來源欄名。財報同理（`fs/2026Q2_ci.csv` 42 欄）。
**歷史頁的欄位不會跟 2026 完全一樣**——IFRS 改過好幾次。
現行設計是**逐期一個檔、每個檔自己的表頭**，所以跨期欄位漂移本來就吃得下，
不要為了「統一欄位」去補空欄或改名，那會把「當年沒有這一欄」偽裝成「當年是空值」。
"""

import argparse
import html
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MOPSOV = "https://mopsov.twse.com.tw"
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "mops")

MARKETS = [("sii", "twse"), ("otc", "tpex")]
# 財報的兩張表；業別分表由頁面自己切（見 `_split_by_kind`）
FS_FORMS = [("t163sb04", "fs"), ("t163sb05", "bs")]


class _Tables(HTMLParser):
    """把 HTML 拆成 [(表前文字, [[cell, …], …]), …]。**不裝 lxml，環境只有標準庫。**

    ★★ 2026-09-06 乾跑踩到的：第一版只收 `<table>` 裡面的東西，
      結果**產業別整欄空白**——月營收頁是「一個產業別一張表」（實測 68 張），
      產業別寫在**表格外面**，被整段丟掉了。財報的業別標題也一樣在表外。
      而它不會報錯：欄位齊、列數對、只有那一欄是空的。

    所以這版多做一件事：**累積「不在儲存格內」的文字**，
    每遇到一個 `<table>` 就把累積到的那段當成這張表的抬頭並清空。

    巢狀表用 stack 處理。第一版遇到內層 `<table>` 會把外層已累積的列先推出去，
    等於把一張表切成兩半——MOPS 的版面到處是 table 包 table，這一定會中。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []          # [(caption, rows)]
        self._stack = []          # [(caption, rows)]，處理巢狀
        self._row = None
        self._cell = []
        self._depth = 0           # 目前在幾層 td/th 裡
        self._text = []           # 不在儲存格內的文字

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            cap = _clean(" ".join(self._text))[-60:]
            self._text = []
            self._stack.append((cap, []))
        elif tag == "tr" and self._stack:
            self._row = []
        elif tag in ("td", "th") and self._stack:
            self._cell, self._depth = [], self._depth + 1

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._depth:
            self._depth -= 1
            if self._row is not None:
                self._row.append(_clean("".join(self._cell)))
            self._cell = []
        elif tag == "tr" and self._row is not None:
            if self._stack and self._row:
                self._stack[-1][1].append(self._row)
            self._row = None
        elif tag == "table" and self._stack:
            self.tables.append(self._stack.pop())
            self._text = []       # 表結束後重新累積，抬頭不要跨表沿用

    def handle_data(self, d):
        if self._depth:
            self._cell.append(d)
        else:
            self._text.append(d)


def _clean(s):
    s = html.unescape(str(s))
    s = s.replace("　", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def _decode(raw):
    """MOPS 有 Big5 也有 UTF-8。**用內容判，不要用主機名猜。**"""
    for enc in ("utf-8", "big5", "cp950"):
        try:
            t = raw.decode(enc)
            if "公司" in t or "代號" in t:
                return t, enc
        except UnicodeDecodeError:
            continue
    return raw.decode("big5", "replace"), "big5(replace)"


def _fetch(url, form=None, timeout=90):
    data = urllib.parse.urlencode(form, encoding="utf-8").encode() if form else None
    req = urllib.request.Request(
        url, data=data,
        headers={"User-Agent": "Mozilla/5.0", "Referer": MOPSOV,
                 **({"Content-Type": "application/x-www-form-urlencoded"} if form else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except Exception as ex:                                # noqa: BLE001
        return b"", f"{type(ex).__name__}: {ex}"


def _is_data_table(rows):
    """→ (表頭索引, 表頭) 或 (None, None)。判準是**有沒有「公司代號」那一欄**。"""
    for i, r in enumerate(rows[:6]):
        cells = [c.replace(" ", "") for c in r]
        if any(c in ("公司代號", "公司 代號", "代號") for c in cells) and len(r) >= 4:
            return i, r
    return None, None


def _num(s):
    s = _clean(s).replace(",", "")
    return "" if s in ("", "-", "--", "N/A", "不適用") else s


# ── 月營收 ────────────────────────────────────────────────────────
def parse_revenue(raw, year, month, market):
    """t21sc03 → (rows, header, note, nosector)。

    ★ 這張表**一個產業別一張表**（實測 104/7 上市 68 張、上櫃 58 張），
      產業別是表格**外面**的抬頭文字，不在任何一格裡。
      抓不到就是抓不到——**留空並回報筆數，不要用今天的 industry.csv 補**。
      那是不同的東西：頁面上的是「當時的」產業別，`industry.csv` 是「現在的」，
      而且它沒有已下市公司。混著用會讓回測拿到未來資訊。
    """
    txt, enc = _decode(raw)
    p = _Tables()
    p.feed(txt)
    out, header, skipped, nosector = [], None, [], 0
    for cap, rows in p.tables:
        hi, hd = _is_data_table(rows)
        if hi is None:
            continue
        if header is None:
            header = [_clean(c) for c in hd]
        sector = _sector_of(cap)
        for r in rows[hi + 1:]:
            if len(r) < 3:
                skipped.append(r)
                continue
            code = _clean(r[0])
            if not code or not code[0].isdigit():
                skipped.append(r)      # 合計列、備註列
                continue
            if not sector:
                nosector += 1
            out.append([code, _clean(r[1]) if len(r) > 1 else "", sector] +
                       [_num(x) for x in r[2:len(header)]])
    note = f"編碼 {enc}｜{len(p.tables)} 張表｜{len(out)} 列"
    if skipped:
        note += f"｜跳過 {len(skipped)} 列"
    if nosector:
        note += f"｜★ **{nosector} 列沒有產業別**"
    return out, header, note, skipped


def _sector_of(cap):
    """從表格抬頭抽產業別。抬頭常黏著頁首雜訊，取**最後**一段像類股名的字。"""
    c = _clean(cap)
    if not c:
        return ""
    m = re.findall(r"[\u4e00-\u9fff]{2,10}(?:工業|業|類|事業)", c)
    if m:
        return m[-1]
    # 沒有「業／類」結尾的（例如「其他」「文化創意」），取最後一段中文
    m = re.findall(r"[\u4e00-\u9fff]{2,10}", c)
    return m[-1] if m else ""


def rev_url(market, year, month):
    return f"{MOPSOV}/nas/t21/{market}/t21sc03_{year}_{month}_0.html"


# ── 財報 ──────────────────────────────────────────────────────────
def fs_form(market, year, season):
    return {"encodeURIComponent": "1", "step": "1", "firstin": "1", "off": "1",
            "isQuery": "Y", "TYPEK": market, "year": str(year),
            "season": f"{int(season):02d}"}


# 業別分表的判定。**用欄位特徵，不用抬頭。**
#   抬頭是排版、隨時會改；欄位是內容本身。乾跑實測 104Q1 六張表的欄位特徵：
#     銀行 8 家   ：利息淨收益 ＋ 呆帳費用…，**沒有**保險負債準備
#     金控 13 家  ：利息淨收益 ＋ 淨收益 ＋ **保險負債準備淨變動**
#     證券 3 家   ：收益 ＋ 支出及費用
#     一般業 794 家：營業收入 ＋ 營業成本
#   保險則有保費收入／保險負債準備而沒有利息淨收益。
#   ★ 順序有意義：金控要排在銀行前面，否則金控會被吃成銀行。
FS_KINDS = [
    ("fh",   lambda h: "利息淨收益" in h and any("保險負債準備" in x for x in h)),
    ("ins",  lambda h: any("保費收入" in x for x in h)
                       or (any("保險負債準備" in x for x in h)
                           and "利息淨收益" not in h)),
    ("basi", lambda h: "利息淨收益" in h),
    ("bd",   lambda h: "收益" in h and any("支出及費用" in x for x in h)),
    ("ci",   lambda h: "營業收入" in h and "營業成本" in h),
]


def fs_kind(header):
    """→ ci／basi／bd／ins／fh，判不出來回空字串。**不要瞎猜一個。**"""
    h = [_clean(x) for x in header]
    for tag, f in FS_KINDS:
        try:
            if f(h):
                return tag
        except Exception:                                 # noqa: BLE001
            continue
    return ""


def parse_fs(raw):
    """t163sb04／sb05 → ([(kind, caption, 表頭, 列)], 編碼)。

    ★ 不合併不同業別。銀行的損益表有「利息淨收益」，一般業有「營業收入」，
      **欄位意義完全不同**，硬併會產出幾百欄、絕大多數是空的怪物
      （這是 `mops.py` 早就寫下的設計決定，這裡照著走）。
    """
    txt, enc = _decode(raw)
    p = _Tables()
    p.feed(txt)
    got = []
    for cap, rows in p.tables:
        hi, hd = _is_data_table(rows)
        if hi is None:
            continue
        header = [_clean(c) for c in hd]
        body = []
        for r in rows[hi + 1:]:
            if len(r) < 3:
                continue
            code = _clean(r[0])
            if not code or not code[0].isdigit():
                continue
            body.append([code] + [_num(x) for x in r[1:len(header)]])
        if body:
            got.append((fs_kind(header), _clean(cap)[-40:], header, body))
    return got, enc


# ── 輸出 ──────────────────────────────────────────────────────────
def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(",".join(h.replace(",", "；") for h in header) + "\n")
        for r in rows:
            fh.write(",".join(str(x).replace(",", "") for x in r) + "\n")


def dump(title, header, rows, note, extra=None):
    print(f"── {title} ──")
    print(f"   {note}")
    if header:
        print(f"   表頭（{len(header)} 欄）：")
        for i, h in enumerate(header):
            print(f"       [{i}] {h}")
    for r in rows[:3]:
        print(f"   列：{r[:12]}{' …' if len(r) > 12 else ''}")
    if extra:
        print(f"   ★ 沒被認成資料表的表（前 3 張的第一列）：")
        for e in extra[:3]:
            print(f"       {e[:8]}")
    print()


def main():
    ap = argparse.ArgumentParser(description="從 MOPS 補月營收與財報的歷史")
    ap.add_argument("--kind", default="both", choices=["revenue", "fs", "both"])
    ap.add_argument("--start", default="2015-01")
    ap.add_argument("--end", default="")
    ap.add_argument("--sleep", type=float, default=3)
    ap.add_argument("--run", action="store_true",
                    help="真的回補並寫檔。**沒有這個旗標就是 --dry**")
    a = ap.parse_args()

    if not a.run:
        print("[hist] **乾跑模式**：只抓一期、印解析結果、不寫任何檔。\n")
        if a.kind in ("revenue", "both"):
            for mkt, _ in MARKETS:
                raw, err = _fetch(rev_url(mkt, 104, 7))
                if err:
                    print(f"── 月營收 {mkt} 104/7 ── 抓取失敗：{err}\n")
                    continue
                rows, header, note, skipped = parse_revenue(raw, 104, 7, mkt)
                print(f"── 月營收 {mkt} 104/7 ──\n   {note}")
                print(f"   表頭（{len(header or [])} 欄）：{header}")
                for r in rows[:3]:
                    print(f"   列：{r[:6]}")
                # ★ 產業別是這一輪的重點，單獨統計
                secs = {}
                for r in rows:
                    secs[r[2]] = secs.get(r[2], 0) + 1
                blank = secs.pop("", 0)
                print(f"   產業別：{len(secs)} 種、空白 {blank} 列")
                print(f"       前 8 種={list(secs.items())[:8]}")
                if blank:
                    print("       ★ **還是有空白**，抬頭抽取式要再改")
                # ★ 跳過的列要看，不能只報數字
                print(f"   跳過的列（前 5，用來確認丟掉的是合計／備註而不是資料）：")
                for r in skipped[:5]:
                    print(f"       {r[:6]}")
                time.sleep(a.sleep)
                print()
        if a.kind in ("fs", "both"):
            for form, _ in FS_FORMS:
                raw, err = _fetch(f"{MOPSOV}/mops/web/ajax_{form}",
                                  fs_form("sii", 104, 1))
                if err:
                    print(f"── 財報 {form} sii 104Q1 ── 抓取失敗：{err}\n")
                    continue
                got, enc = parse_fs(raw)
                print(f"── 財報 {form} sii 104Q1 ──")
                print(f"   編碼 {enc}｜認出 {len(got)} 張業別分表（**全部列出**）")
                seen = {}
                for kind, cap, hdr, body in got:
                    seen[kind] = seen.get(kind, 0) + 1
                    print(f"   [{kind or '★判不出'}] {len(hdr)} 欄 / {len(body)} 列"
                          f"｜抬頭「{cap}」")
                    print(f"       前 6 欄={hdr[:6]}")
                    print(f"       首列={body[0][:4]}")
                dupes = [k for k, v in seen.items() if v > 1 and k]
                if "" in seen:
                    print(f"   ★ 有 {seen['']} 張**判不出業別**——命名規則要補")
                if dupes:
                    print(f"   ★ 業別重複 {dupes}——同一個 kind 兩張表會互相覆蓋")
                time.sleep(a.sleep)
                print()
        print("[hist] 這一輪要看的三件事：")
        print("  ① 產業別空白列數是不是 0")
        print("  ② 六張業別分表是不是都判出 kind，且**沒有重複**")
        print("  ③ 跳過的列是不是合計／備註，不是真資料")
        return 0

    print("[hist] 回補模式。**確認過 --dry 的欄位了嗎？**")
    print("[hist] （這一版只做月營收；財報的業別分表命名要等 --dry 的結果才敢寫死）")
    y, m = int(a.start[:4]) - 1911, int(a.start[5:7])
    end = a.end or time.strftime("%Y-%m")
    ey, em = int(end[:4]) - 1911, int(end[5:7])
    ok = fail = 0
    while (y, m) <= (ey, em):
        for mkt, market in MARKETS:
            raw, err = _fetch(rev_url(mkt, y, m))
            if err:
                print(f"  ✗ {y}/{m} {mkt}｜{err[:60]}")
                fail += 1
                time.sleep(a.sleep)
                continue
            rows, header, note = parse_revenue(raw, y, m, mkt)
            if not rows:
                print(f"  △ {y}/{m} {mkt}｜0 列（{note}）")
                fail += 1
                time.sleep(a.sleep)
                continue
            per = f"{y + 1911:04d}-{m:02d}"
            full = ["stock_id", "name", "產業別"] + header[2:]
            write_csv(os.path.join(OUT, "revenue_hist", f"{per}_{market}.csv"),
                      full, rows)
            ok += 1
            if ok % 24 == 0:
                print(f"  [{ok}] {per} {mkt} {note}", flush=True)
            time.sleep(a.sleep)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    print(f"[hist] 完成：成功 {ok} 期、失敗 {fail} 期")
    print("[hist] ★ 寫在 data/mops/revenue_hist/，**與 mops.py 的 revenue/ 分開**——"
          "兩者欄位可能不同，先分開存，對照過再決定要不要合併。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
