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
import urllib.error          # ★ _fetch 的重試要判 HTTPError.code，不可靠隱式匯入
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MOPSOV = "https://mopsov.twse.com.tw"
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "mops")

MARKETS = [("sii", "twse"), ("otc", "tpex")]


def ledger_from_disk(state):
    """用**真的寫出來的檔案**補齊帳本，回傳補了幾筆。

    ⛔ 為什麼需要這一步：上面的 `state` 只裝得下這一趟真的去問過的期別。
      `--fill`／`--resume` 會先跳過已經有檔的期別，那些**永遠不會進 state**。
      2026-09-08 實測：資料庫 2015-01 起全數回補完成（revenue_hist 280 檔、
      fs_hist 與 bs_hist 各 372 檔），帳本卻只有 6 列而且全是 pending。
      而寫帳本那段的註解寫著「這是資料庫的狀態，不只是這一趟」——
      **註解說的是意圖，程式做的是另一件事**。一份宣稱是整體、實際只有這一趟
      的帳本，比沒有帳本更糟。

    規則：
      - 有檔 → ok。檔案存在是**直接證據**，勝過這一趟有沒有去問它。
      - 有檔但這一趟抓取失敗 → 仍記 ok，但把失敗原文留在 note 裡，不藏起來。
      - 沒檔 → 維持這一趟判定的 fail／pending；沒碰過的就不寫（答不出來就別答）。

    ⚠ 「檔案在」只證明那一期有寫出來，**不證明內容完整**。note 記的是張數，
      這是檔案層級的證據，不是內容層級的。
    """
    m2mkt = {m: k for k, m in MARKETS}
    seen = {}
    for sub, kind in (("revenue_hist", "revenue"), ("fs_hist", "fs"),
                      ("bs_hist", "bs")):
        d = os.path.join(OUT, f"{sub}")
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".csv"):
                continue
            # revenue_hist: <期別>_<市場>.csv／fs_hist、bs_hist: <期別>_<業別>_<市場>.csv
            parts = fn[:-4].rsplit("_", 1 if kind == "revenue" else 2)
            if len(parts) < 2:
                continue
            mkt = m2mkt.get(parts[-1])
            if not mkt:
                continue
            key = (kind, parts[0], mkt)
            seen[key] = seen.get(key, 0) + 1
    added = 0
    for key, n in seen.items():
        prev = state.get(key)
        note = f"{n} 張表（檔案實測；只證明有寫出來，不證明內容完整）"
        if prev is None:
            state[key] = ("ok", note)
            added += 1
        elif prev[0] != "ok":
            # 有檔但這一趟失敗／未公告：資料庫的狀態是「有」，失敗原文不丟掉
            state[key] = ("ok", f"{note}｜⚠ 這一趟：{prev[0]} {prev[1]}")
    return added
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
        self.sector = ""          # 最近看到的「產業別：X」
        self._secs = {}           # 表序 → 開表當下的產業別

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            # ★★ 第二次踩到：抬頭還是空的。原因是 MOPS 把整頁包在一張大 table 裡，
            #   所以「表格外的文字」幾乎不存在——產業別是寫在**外層表格的儲存格內**，
            #   後面才接一張巢狀的資料表。只收 `_depth == 0` 的文字等於什麼都收不到。
            #   → 改成收「最近看到的一段文字」，不管它在不在儲存格裡。
            # ★★★ 第三次才看到真相（前兩次都是猜的）。原始 HTML 長這樣：
            #   <table><tr><td><br>
            #     <table><tr><th>產業別：水泥工業</th><th>單位：千元</th></tr>
            #             <tr><td colspan=2>   ← 資料表在這裡面
            #   產業別是**上一層表格另一列的 `<th>`**，既不在資料表裡、
            #   也不在它前面的文字裡。前兩版一個收「表外文字」、一個收
            #   「當前儲存格」，都收不到那一格。
            #   → 改成：**任何一格長得像「產業別：X」就記下來**，之後開的表
            #     都掛這個產業別。文件順序保證它先出現。
            cap = _clean(" ".join(self._text) + " " + "".join(self._cell))[-60:]
            self._text = []
            self._secs[len(self.tables) + len(self._stack)] = self.sector
            self._stack.append((cap, []))
        elif tag == "tr" and self._stack:
            self._row = []
        elif tag in ("td", "th") and self._stack:
            self._cell, self._depth = [], self._depth + 1

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._depth:
            self._depth -= 1
            if self._row is not None:
                cell = _clean("".join(self._cell))
                m = re.match(r"^產業別\s*[:：]\s*(.+)$", cell)
                if m:
                    self.sector = _clean(m.group(1))
                self._row.append(cell)
            self._cell = []
        elif tag == "tr" and self._row is not None:
            if self._stack and self._row:
                self._stack[-1][1].append(self._row)
            self._row = None
        elif tag == "table" and self._stack:
            cap, rows = self._stack.pop()
            key = len(self.tables) + len(self._stack)
            self.tables.append((self._secs.get(key, "") or cap, rows))
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


def _fetch(url, form=None, timeout=90, retries=4, backoff=8):
    """★ 一定要重試。乾跑時 `t163sb05` 就吃到一發 **502 Bad Gateway**——
    單發失敗在 188 發的回補裡一定會再遇到，不重試等於每次都要人工補洞。
    只重試「暫時性」的（5xx、逾時、連線中斷）；4xx 是請求本身錯了，重試沒意義。
    """
    data = urllib.parse.urlencode(form, encoding="utf-8").encode() if form else None
    last = ""
    for i in range(retries):
        req = urllib.request.Request(
            url, data=data,
            headers={"User-Agent": "Mozilla/5.0", "Referer": MOPSOV,
                     **({"Content-Type": "application/x-www-form-urlencoded"}
                        if form else {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except urllib.error.HTTPError as ex:
            last = f"HTTP {ex.code}"
            if ex.code < 500:
                return b"", last          # 4xx：重試沒意義
        except Exception as ex:                            # noqa: BLE001
            last = f"{type(ex).__name__}: {ex}"
        if i < retries - 1:
            time.sleep(backoff * (i + 1))
    return b"", f"{last}（重試 {retries} 次仍失敗）"


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
        # cap 現在多半就是產業別本身（`_Tables` 已認過「產業別：X」），
        # 抽不到才退回舊的猜法。
        sector = cap if (cap and "：" not in cap and len(cap) <= 12) else _sector_of(cap)
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
    # 乾跑實測還有第六張：18 欄 4 列、欄位是「收入／支出」、首列 1409 新纖。
    # 那是 MOPS 的**異業**（子公司跨業別者）。現有 data/mops/fs/ 只有五種，
    # 是因為 OpenAPI 那一期剛好沒有這張——**不要因此假設它不存在**。
    ("other", lambda h: "收入" in h and "支出" in h),
    # ── 以下是**資產負債表**（t163sb05）的規則 ──
    #   2026-09-06 回補實測：bs 的六張表用上面那些規則**一張都判不出**——
    #   上面全是損益表的欄位（營業收入、利息淨收益…），資產負債表沒有那些字。
    #   幸好三種「資產總額」的用詞剛好不一樣，可以當判別式：
    #     證券 `資產合計`／一般業 `資產總計`／異業 `資產總額`
    #   金融三類則看資產科目本身。★ 金控與銀行只差一個字（金融／銀行），別看漏。
    ("fh",   lambda h: any("存放央行及拆借金融同業" in x for x in h)),
    ("basi", lambda h: any("存放央行及拆借銀行同業" in x for x in h)),
    ("ins",  lambda h: any("待出售資產" in x for x in h)
                       and any("應收款項" in x for x in h)),
    ("bd",   lambda h: any(x == "資產合計" for x in h)),
    ("ci",   lambda h: any(x == "資產總計" for x in h)),
    ("other", lambda h: any(x == "資產總額" for x in h)),
]


def load_learned(per, market):
    """從**已經寫出來的** `fs_hist/<期別>_<業別>_<市場>.csv` 讀回該期的業別歸屬。

    ★ 2026-09-06 實測到的連鎖反應：`fs 2025Q2 sii` 連線中斷 → 同期沒有損益表
      可參考 → `bs 2025Q2 sii` 退回脆弱的欄名規則 → **ci 撞名，整期不寫**。
      一個網路抖動變成兩個期別的資料缺口。
      只要損益表**曾經**成功過（檔案在），就不必再靠當下那一發。
    """
    got, d = {}, os.path.join(OUT, "fs_hist")
    if not os.path.isdir(d):
        return got
    suffix = f"_{market}.csv"
    for n in os.listdir(d):
        if not (n.startswith(f"{per}_") and n.endswith(suffix)):
            continue
        kind = n[len(per) + 1:-len(suffix)]
        with open(os.path.join(d, n), encoding="utf-8") as fh:
            fh.readline()
            for ln in fh:
                c = ln.split(",", 1)[0].strip()
                if c and c[0].isdigit():
                    got[c] = kind
    return got


def _kinds_on_disk(sub, per, market):
    """該期別＋市場**已經寫出哪些業別**。"""
    d = os.path.join(OUT, f"{sub}_hist")
    if not os.path.isdir(d):
        return set()
    pre, suf = f"{per}_", f"_{market}.csv"
    return {x[len(pre):-len(suf)] for x in os.listdir(d)
            if x.startswith(pre) and x.endswith(suf)}


def has_output(sub, per, market):
    """該期別＋市場**是否已經完整**。`--fill` 用來只補缺的，不重跑全部。

    ★★ 2026-09-06 踩到：第一版問的是「有沒有**任何**檔案」。
      但實際的缺口是**六張表裡缺一張**——`bs 2025Q2 sii` 因為 ci 撞名沒寫，
      另外五張都在，於是被判成已完成、`--fill` 直接跳過。
      那一趟印出「月營收 0 期檔、財報 0 個業別檔、0 個失敗」，
      **看起來像都做完了，其實 5 個洞原封不動。**

      判準改成**業別齊不齊**：資產負債表應該有的業別＝同期損益表有的那些。
      這是資料自己給的答案，不是猜的——兩張表本來就對應同一批公司。
      損益表沒有可比對的對象，只能沿用「有沒有檔案」（它的失敗是整期抓不到，
      不會只缺一張）。
    """
    if sub == "revenue":
        return os.path.exists(os.path.join(OUT, "revenue_hist",
                                           f"{per}_{market}.csv"))
    got = _kinds_on_disk(sub, per, market)
    if not got:
        return False
    if sub == "bs":
        want = _kinds_on_disk("fs", per, market)
        if want and not want.issubset(got):
            return False          # 缺業別 → 要補
    return True


def load_kind_map():
    """從**現有的** `data/mops/fs/*_<業別>.csv` 建 {代號: 業別}。

    ★★ 這比欄位特徵可靠得多，而且用的是我們手上已經有的資料。
      乾跑實測欄位特徵有兩個死穴：
        ① 保險（2816 旺旺保）的損益表欄位是「營業收入／營業成本／營業費用」，
           **跟一般業長得一樣**，被判成 ci → 同一個 kind 兩張表會互相覆蓋
        ② 資產負債表（t163sb05）的欄位跟損益表完全不同，六張全部判不出
      公司的業別**極少變**，所以拿 2026 那一期的分類回推 2015 幾乎一定對。
      判不出的是已下市公司，用同表其他成員的多數決補。
    """
    out = {}
    for sub in ("fs", "bs"):
        d = os.path.join(OUT, sub)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if not n.endswith(".csv") or "_" not in n:
                continue
            kind = n[:-4].split("_")[-1]
            with open(os.path.join(d, n), encoding="utf-8") as fh:
                fh.readline()
                for ln in fh:
                    c = ln.split(",", 1)[0].strip()
                    if c and c[0].isdigit():
                        out.setdefault(c, kind)
    return out


# ★★ 異業的欄位是**硬證據**，要在代號多數決之前判。
#   2026-09-06 回補實測：2015 全年**上櫃**的 fs 與 bs 都出現「ci 重複」，
#   八個期別因此整張不寫。根因是——
#   **對照表來自 OpenAPI，而 OpenAPI 只有五類、沒有異業**。
#   所以任何異業公司在對照表裡一定被標成別的類（多半 ci），
#   代號多數決對這一類是**系統性錯誤**，涵蓋率再高也一樣錯
#   （上一版加的涵蓋率門檻擋不住這種：它涵蓋率高、答案錯）。
#
#   幸好異業的欄位跟誰都不一樣，而且是精確欄名比對、不會誤中：
#     損益表　　異業「收入」「支出」 vs 一般業「營業收入」「營業成本」
#     資產負債表 異業「資產總額」 vs 一般業「資產總計」 vs 證券「資產合計」
#   → 欄位命中異業就直接判 other，不讓多數決覆蓋。
def _is_other(h):
    return (("收入" in h and "支出" in h)
            or any(x == "資產總額" for x in h))


def fs_kind(header, codes=(), kmap=None, learned=None):
    """→ (業別, 依據)。判不出來回 ("", 理由)——**不要瞎猜一個**。

    先用已知代號多數決（依據＝`代號`），不行才退回欄位特徵（依據＝`欄位`）。
    """
    # ★★★ 最可靠的一層：**同一期損益表已經認出來的業別。**
    #   2026-09-06 第三次踩到撞名：2018 的**異業資產負債表用「資產總計」**，
    #   跟一般業一模一樣（我那條規則是照 2015 的「資產總額」寫的），
    #   兩張表只差最後一個權益欄（權益總計 vs 權益總額）。
    #   **欄名本身會隨年份漂移**，靠單一字眼判遲早再中一次。
    #
    #   但同一期的**損益表**分得開——異業是「收入／支出」，那是結構差異不是用詞差異。
    #   損益表（t163sb04）在 FS_FORMS 裡排在資產負債表前面，所以跑到 bs 時
    #   同期的業別歸屬已經知道了。用它，比任何欄名規則都準。
    #
    #   ⚠ 上一版寫成 `kmap.setdefault(code, kind)` 是**沒有作用的**——
    #     那些代號早就被 OpenAPI 標成 ci，setdefault 什麼都不會做。
    #     所以要用獨立的 `learned`，而且**優先於** kmap。
    if learned and codes:
        v = {}
        for c in codes:
            k = learned.get(c)
            if k:
                v[k] = v.get(k, 0) + 1
        if v:
            best = max(v, key=v.get)
            if v[best] / max(len(codes), 1) >= 0.5:
                return best, f"同期損益表 {v[best]}/{len(codes)} 家"
    h0 = [_clean(x) for x in header]
    if _is_other(h0):
        return "other", "異業欄位（硬證據，不看多數決）"
    if kmap and codes:
        votes = {}
        for c in codes:
            k = kmap.get(c)
            if k:
                votes[k] = votes.get(k, 0) + 1
        if votes:
            best = max(votes, key=votes.get)
            nv, tot, all_n = votes[best], sum(votes.values()), max(len(codes), 1)
            # ★ 乾跑實測的坑：異業那張表 4 家、只有 1 家查得到，
            #   1/1 = 100% 看起來很篤定，實際上**只認得四分之一**，
            #   而那一家在 2026 被歸到 ci → 整張表被判成 ci，與一般業撞名。
            #   → 涵蓋率（查得到的 ÷ 全部）也要過關，否則退回欄位特徵。
            if nv / tot >= 0.7 and tot / all_n >= 0.5:
                return best, f"代號多數決 {nv}/{tot}（{all_n} 家）"
            why = (f"★ 只認得 {tot}/{all_n} 家、涵蓋不足" if tot / all_n < 0.5
                   else f"★ 多數決只有 {nv}/{tot}")
            h2 = [_clean(x) for x in header]
            for tag, f in FS_KINDS:
                try:
                    if f(h2):
                        return tag, f"{why}，退回欄位特徵 → {tag}"
                except Exception:                         # noqa: BLE001
                    continue
            return best, why + "，欄位特徵也判不出，暫用多數決"
    h = [_clean(x) for x in header]
    for tag, f in FS_KINDS:
        try:
            if f(h):
                return tag, "欄位特徵"
        except Exception:                                 # noqa: BLE001
            continue
    return "", "判不出"


def parse_fs(raw, kmap=None, learned=None):
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
            kind, how = fs_kind(header, [r[0] for r in body], kmap, learned)
            got.append((kind, how, _clean(cap)[-40:], header, body))

    # ★ 最後一道：同一頁若還有兩張表判成同一個業別，**那一定有一張是錯的**。
    #   對撞名的那幾張改用純欄位特徵重判一次（不看代號）。
    #   欄位是內容本身，代號多數決是統計推論——衝突時信前者。
    seen = {}
    for i, (k, _how, _c, _h, _b) in enumerate(got):
        seen.setdefault(k, []).append(i)
    for k, idxs in seen.items():
        if k and len(idxs) > 1:
            for i in idxs:
                kk, hh = _kind_by_header(got[i][3])
                if kk:
                    got[i] = (kk, f"撞名重判：{hh}") + got[i][2:]
    return got, enc


def _kind_by_header(header):
    """只看欄位、不看代號。撞名時用它拆。"""
    h = [_clean(x) for x in header]
    for tag, f in FS_KINDS:
        try:
            if f(h):
                return tag, "欄位特徵"
        except Exception:                                 # noqa: BLE001
            continue
    return "", "判不出"


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
    ap.add_argument("--period", default="",
                    help="乾跑指定期別，例如 2018Q1（財報）或 2018-03（月營收）")
    ap.add_argument("--market", default="sii", choices=["sii", "otc"])
    ap.add_argument("--form", default="", help="t163sb04 或 t163sb05")
    ap.add_argument("--fill", action="store_true",
                    help="只補**還沒有產出**的期別。修完失敗清單後用它，不用整批重跑")
    a = ap.parse_args()

    if not a.run and a.period:
        # ★ 指定期別的乾跑：把**整張表的每一欄**印出來。
        #   撞名這種問題不能靠猜，要看欄位本身長什麼樣。
        kmap = load_kind_map()
        print(f"[hist] 指定期別乾跑：{a.period} {a.market}"
              f"｜對照表 {len(kmap)} 檔\n")
        if "Q" in a.period:
            y, q = int(a.period.split("Q")[0]) - 1911, int(a.period.split("Q")[1])
            forms = [a.form] if a.form else [f for f, _ in FS_FORMS]
            learned = {}          # 與 --run 同樣的做法，乾跑才驗得到真行為
            for form in forms:
                raw, err = _fetch(f"{MOPSOV}/mops/web/ajax_{form}",
                                  fs_form(a.market, y, q))
                if err:
                    print(f"── {form} ── 失敗：{err}")
                    continue
                got, enc = parse_fs(raw, kmap, learned)
                if form == "t163sb04":
                    for kind, _how, _cap, _hdr, body in got:
                        if kind:
                            for r in body:
                                learned[r[0]] = kind
                print(f"── {form} {a.market} {a.period}｜編碼 {enc}"
                      f"｜{len(got)} 張表 ──")
                for kind, how, cap, hdr, body in got:
                    print(f"  [{kind or '★判不出'}] {len(hdr)} 欄 / {len(body)} 列"
                          f"｜依據：{how}")
                    print(f"      代號前 6：{[r[0] for r in body[:6]]}")
                    print(f"      **完整欄位**：{hdr}")
                ks = {}
                for kind, *_ in got:
                    ks[kind] = ks.get(kind, 0) + 1
                dup = [k for k, v in ks.items() if v > 1]
                print(f"  → 業別分布 {ks}"
                      + (f"｜★★ 撞名 {dup}" if dup else "｜無撞名"))
                time.sleep(a.sleep)
                print()
        else:
            y, m = int(a.period[:4]) - 1911, int(a.period[5:7])
            raw, err = _fetch(rev_url(a.market, y, m))
            if err:
                print(f"失敗：{err}")
            else:
                rows, header, note, sk = parse_revenue(raw, y, m, a.market)
                print(f"{note}\n表頭={header}")
                for r in rows[:5]:
                    print("  ", r[:6])
        return 0

    if not a.run:
        print("[hist] **乾跑模式**：只抓一期、印解析結果、不寫任何檔。\n")
        if a.kind in ("revenue", "both"):
            for mkt, _ in MARKETS:
                raw, err = _fetch(rev_url(mkt, 104, 7))
                if err:
                    print(f"── 月營收 {mkt} 104/7 ── 抓取失敗：{err}\n")
                    continue
                rows, header, note, skipped = parse_revenue(raw, 104, 7, mkt)
                # ★ 抬頭已經猜錯兩次。這次直接把資料表前面的原始 HTML 印出來看。
                txt, _e = _decode(raw)
                hits = [m.start() for m in re.finditer(r"<table", txt, re.I)]
                print(f"   ── 原始 HTML：前 3 張 <table> 之前的 260 字 ──")
                for k, pos in enumerate(hits[:3], 1):
                    ctx = txt[max(0, pos - 260):pos].replace("\n", " ")
                    print(f"       [{k}] …{ctx[-260:]}")
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
            kmap = load_kind_map()
            print(f"[hist] 已知業別對照表：{len(kmap)} 檔"
                  f"（取自現有的 data/mops/fs、bs）\n")
            for form, _ in FS_FORMS:
                raw, err = _fetch(f"{MOPSOV}/mops/web/ajax_{form}",
                                  fs_form("sii", 104, 1))
                if err:
                    print(f"── 財報 {form} sii 104Q1 ── 抓取失敗：{err}\n")
                    continue
                got, enc = parse_fs(raw, kmap)
                print(f"── 財報 {form} sii 104Q1 ──")
                print(f"   編碼 {enc}｜認出 {len(got)} 張業別分表（**全部列出**）")
                seen = {}
                for kind, how, cap, hdr, body in got:
                    seen[kind] = seen.get(kind, 0) + 1
                    print(f"   [{kind or '★判不出'}] {len(hdr)} 欄 / {len(body)} 列"
                          f"｜依據：{how}｜抬頭「{cap}」")
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

    print("[hist] 回補模式。**確認過 --dry 的三項了嗎？**"
          "（產業別空白 0／六張分表不重複／跳過的是合計）")
    end = a.end or time.strftime("%Y-%m")
    now = time.strftime("%Y-%m")          # 只當「有沒有公告」的參考，不當資料日期
    fails, pending = [], []
    # ★ 帳本要記「**資料庫的狀態**」，不是「這一趟做了什麼」。
    #   `--fill` 跳過的期別也要記成 ok，否則一個只補兩個洞的 --fill
    #   會寫出一份 `fail 0` 的帳本，讀的人以為整體沒問題——
    #   這正是這一輪反覆出現的形狀：摘要講的是這一趟，讀的人以為是整體。
    state = {}

    def _pending(per):
        """這個期別是不是**還沒公告**（而不是失敗）。

        ★★ 2026-09-06 踩到：第一版寫 `per >= now[:len(per)]`，
          季別長 `2026Q1`、now 長 `2026-09`，`now[:6]` 是 `2026-0`，
          而 `"2026Q1" >= "2026-0"` 因為 `Q`(0x51) > `-`(0x2D) **永遠成立**——
          於是 2026Q1／Q2 被歸成「尚未公告」，**把真正的失敗藏起來了**。
          （那兩期明明早就公告，我們自己的 `fs/2026Q2_ci.csv` 就在 repo 裡。）
          跨格式的字串比較不能當日期比。季別要換算成季末月再比。
        """
        if "Q" in per:
            y, q = per.split("Q")
            last = f"{int(y):04d}-{int(q) * 3:02d}"       # 季末月
            # 財報約季末後 45 天才公告，寬鬆抓「季末月的次月」還沒到就算未公告
            return last >= now
        return per >= now

    def _note(kind, per, mkt, msg):
        """★ 尚未公告的期別**不是失敗**——但判準要對，否則會反過來把失敗藏起來。"""
        st = "pending" if _pending(per) else "fail"
        state[(kind, per, mkt)] = (st, msg)
        (pending if st == "pending" else fails).append((kind, per, mkt, msg))

    if a.kind in ("revenue", "both"):
        y, m = int(a.start[:4]) - 1911, int(a.start[5:7])
        ey, em = int(end[:4]) - 1911, int(end[5:7])
        ok = 0
        while (y, m) <= (ey, em):
            for mkt, market in MARKETS:
                per = f"{y + 1911:04d}-{m:02d}"
                if a.fill and has_output("revenue", per, market):
                    state[("revenue", per, mkt)] = ("ok", "已存在，--fill 跳過")
                    continue
                raw, err = _fetch(rev_url(mkt, y, m))
                if err:
                    _note("revenue", per, mkt, err[:50])
                    time.sleep(a.sleep)
                    continue
                rows, header, note, _sk = parse_revenue(raw, y, m, mkt)
                if not rows or not header:
                    # ★ HTTP 200 但解析出 0 張表 → 多半是一次壞回應，重抓一次再判。
                    #   2026-09-06 實測 2026-03 sii 就中過（編碼 big5(replace)、0 張表），
                    #   同一個網址後來是好的。
                    time.sleep(a.sleep)
                    raw, err = _fetch(rev_url(mkt, y, m))
                    rows, header, note, _sk = (
                        parse_revenue(raw, y, m, mkt) if not err
                        else ([], None, err[:50], []))
                if not rows or not header:
                    _note("revenue", per, mkt, f"0 列（{note}）")
                    time.sleep(a.sleep)
                    continue
                blank = sum(1 for r in rows if not r[2])
                if blank:
                    # 產業別是這張表唯一拿得到的來源，缺了就要吵，不可靜默寫出去
                    fails.append(("revenue", per, mkt, f"★ {blank} 列沒有產業別"))
                full = (["stock_id", "name", "period", "market", "產業別"]
                        + header[2:])
                out = [[r[0], r[1], per, market, r[2]] + r[3:] for r in rows]
                write_csv(os.path.join(OUT, "revenue_hist", f"{per}_{market}.csv"),
                          full, out)
                state.setdefault(("revenue", per, mkt), ("ok", note))
                ok += 1
                if ok % 24 == 0:
                    print(f"  [月營收 {ok}] {per} {mkt} {note}", flush=True)
                time.sleep(a.sleep)
            m += 1
            if m == 13:
                y, m = y + 1, 1
        print(f"[hist] 月營收完成 {ok} 期檔")

    if a.kind in ("fs", "both"):
        kmap = load_kind_map()
        print(f"[hist] 業別對照表 {len(kmap)} 檔")
        y, q = int(a.start[:4]) - 1911, (int(a.start[5:7]) - 1) // 3 + 1
        ey, eq = int(end[:4]) - 1911, (int(end[5:7]) - 1) // 3 + 1
        ok = 0
        while (y, q) <= (ey, eq):
            per = f"{y + 1911:04d}Q{q}"
            # ★ 每一期、每個市場各自一份「同期損益表認出的業別」。
            #   損益表先跑（FS_FORMS 的順序），資產負債表才有得參考。
            # ★ 先從**已寫出的檔案**讀回該期的業別歸屬。這樣即使這一趟的損益表
            #   抓失敗（或 --fill 跳過了它），資產負債表照樣判得出來。
            learned = {mk: load_learned(per, mrk) for mk, mrk in MARKETS}
            for form, sub in FS_FORMS:
                for mkt, market in MARKETS:
                    if a.fill and has_output(sub, per, market):
                        state[(sub, per, mkt)] = ("ok", "已存在，--fill 跳過")
                        continue
                    raw, err = _fetch(f"{MOPSOV}/mops/web/ajax_{form}",
                                      fs_form(mkt, y, q))
                    if err:
                        _note(sub, per, mkt, err[:50])
                        if sub == "fs":
                            # ★ 損益表失敗會讓同期的資產負債表失去依據，
                            #   下游那個「ci 重複」不是獨立的錯，是這個的後果。
                            print(f"  ⚠ {per} {mkt} 損益表失敗，"
                                  f"同期資產負債表可能跟著判不準", flush=True)
                        time.sleep(a.sleep)
                        continue
                    got, _enc = parse_fs(raw, kmap, learned[mkt])
                    if not got:
                        _note(sub, per, mkt, "0 張表")
                        time.sleep(a.sleep)
                        continue
                    seen = {}
                    for kind, how, _cap, hdr, body in got:
                        if not kind:
                            _note(sub, per, mkt, f"★ 一張表判不出業別（{how}）")
                            continue
                        if kind in seen:
                            # ★ 撞名就是**不寫**。覆蓋掉會少一整張表且看不出來。
                            _note(sub, per, mkt, f"★ 業別 {kind} 重複，兩張都不寫")
                            continue
                        seen[kind] = True
                        if sub == "fs":
                            # 損益表分得開，把結果記下來給同期的資產負債表用
                            for cc in [r[0] for r in body]:
                                learned[mkt][cc] = kind
                        full = (["stock_id", "name", "period", "market"] + hdr[2:])
                        out = [[r[0], r[1] if len(r) > 1 else "", per, market]
                               + r[2:] for r in body]
                        write_csv(os.path.join(
                            OUT, f"{sub}_hist", f"{per}_{kind}_{market}.csv"),
                            full, out)
                        state.setdefault((sub, per, mkt), ("ok", ""))
                        ok += 1
                    time.sleep(a.sleep)
            if ok and ok % 60 == 0:
                print(f"  [財報 {ok}] {per}", flush=True)
            q += 1
            if q == 5:
                y, q = y + 1, 1
        print(f"[hist] 財報完成 {ok} 個業別檔")

    # ★ 把每一期的結果寫成帳本。只靠「檔案在不在」推斷完整性遲早會再錯一次
    #   （這一輪就錯過），有帳本才查得到「哪一期為什麼沒有」。
    _added = ledger_from_disk(state)
    if _added:
        print(f"[hist] 帳本補進 {_added} 個這一趟沒碰到、但檔案已經在的期別"
              f"（`--fill` 會跳過已完成的期別，那些不會進這一趟的 state）")
    try:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "_hist_status.csv"), "w",
                  encoding="utf-8") as fh:
            fh.write("kind,period,market,status,note\n")
            for (k, per, mkt), (st, msg) in sorted(state.items()):
                fh.write(f"{k},{per},{mkt},{st},{str(msg).replace(',', '；')}\n")
        nok = sum(1 for v in state.values() if v[0] == "ok")
        print(f"[hist] 狀態帳本：data/mops/_hist_status.csv"
              f"｜ok {nok}、fail {len(fails)}、pending {len(pending)}"
              f"（**這是資料庫的狀態，不只是這一趟**）")
    except OSError as ex:                                   # noqa: BLE001
        print(f"[hist] 寫狀態帳本失敗：{ex}", file=sys.stderr)

    if pending:
        print(f"[hist] {len(pending)} 個期別**尚未公告**（正常，不是失敗）："
              f"{sorted({x[1] for x in pending})}")
    if fails:
        print(f"[hist] ★ {len(fails)} 個期別有問題（**不要當成沒發生**）：")
        for f in fails[:30]:
            print(f"        {f[0]} {f[1]} {f[2]}｜{f[3]}")
        if len(fails) > 30:
            print(f"        …另外 {len(fails) - 30} 個")
        print("[hist] 這些期別重跑一次即可（已成功的會被覆蓋、不會重複累積）")
    print("[hist] 寫在 data/mops/revenue_hist、fs_hist、bs_hist，"
          "**與 mops.py 的 revenue/、fs/、bs/ 分開**——"
          "欄位不同期不一樣，先分開存，對照過再決定要不要合併。")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
