#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""停牌（暫停/恢復交易）、處置股、注意股 —— 抓取與回補。

來源與參數全部來自 2026-09-07 的五輪探針，**沒有一條是猜的**。
完整探查紀錄見專案文件 sources/suspend_source.md。

| 資料 | 上市 | 上櫃 |
|---|---|---|
| 停牌 | `afterTrading/TWTAWU`，2015 起歷史 | `bulletin/sprcHis`（POST，逐年）**2011 起有歷史**；當日用 `bulletin/sprc` |
| 處置 | `announcement/punish`，2015 起 | `bulletin/disposal`，2015 起 |
| 注意 | `announcement/notice`，2015 起 | `bulletin/attention`，2015 起 |

★★ 四個會靜默出錯的地方，每一個都對應程式裡一段防護：

  ① **同樣的參數名，兩個交易所的日期格式相反。**
     TWSE 要 `20150105`（不帶斜線），TPEx 要 `2015/01/05`（帶斜線）。
     **寫錯的那一邊不報錯**，它會回「今天」的資料，`stat` 仍然是 ok。
     → 防護：`_check_echo()`。每一發都拿回應自己回報的日期跟我要的比對，
       對不上就**丟掉那一發**並記進 `_suspend_skipped.txt`，
       絕不把「今天」的資料寫成那一天的。

  ② **`bulletin/disposal` 的「本日無資料」是一列，不是空陣列。**
     那一列長這樣：`[1,'104/01/05','','','','','','本日無處置資料','','','']`
     → 防護：`_drop_placeholder()`。用列數判斷有沒有資料會數到 6。

  ③ **同一個站兩種無資料慣例。** `bulletin/sprc` 反而是空陣列 + `totalCount`。
     → 防護：兩條各自處理，不共用判斷。

  ④ **證券名稱欄夾著連結**：`雙鴻(../../mainboard/listed/company-detail.html?code=3324)`
     → 防護：`_clean_name()`。

用法
────
    python3 suspend.py --backfill --start 2015 --end 2026
        上市三條 + 上櫃處置/注意，逐年（TWSE）逐月（TPEx）回補。可重複跑，會覆蓋同鍵。

    python3 suspend.py --daily
        近 30 天的上市三條 + 上櫃處置/注意，**加上上櫃停牌的當日快照**。
        ⚠ 上櫃停牌沒有歷史，只能從啟用日起每天累積。

輸出（都在 data/meta/）
    suspend.csv   停牌：stock_id,name,market,sec_kind,halt_date,resume_date,source,asof
    disposal.csv  處置：stock_id,name,market,sec_kind,announce_date,start_date,end_date,
                        count,reason,source,asof
    attention.csv 注意：stock_id,name,market,sec_kind,date,count,reason,close,per,source,asof
    _suspend_skipped.txt  被防護擋下來的每一發（**這個檔不是空的就要看**）

⚠ `sec_kind` 是**用代號形狀判的**（四位數字＝普通股，其餘＝權證/債券/ETF 等），
   不是來源給的。報告只用普通股時要自己過濾，不要假設來源已經分好。
"""
import argparse
import collections
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import runlog
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
META = os.path.join("data", "meta")
OUT_HALT = os.path.join(META, "suspend.csv")
OUT_DISP = os.path.join(META, "disposal.csv")
OUT_ATTN = os.path.join(META, "attention.csv")
SKIPPED = os.path.join(META, "_suspend_skipped.txt")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

H_HALT = ["stock_id", "name", "market", "sec_kind", "halt_date", "resume_date",
          "source", "asof"]
H_DISP = ["stock_id", "name", "market", "sec_kind", "announce_date", "start_date",
          "end_date", "count", "reason", "source", "asof"]
H_ATTN = ["stock_id", "name", "market", "sec_kind", "date", "count", "reason",
          "close", "per", "source", "asof"]

_SKIP_LOG = []


def now_tpe():
    return datetime.now(TPE)


# ⛔ TWSE 限流時回的是 **307**，不是 429。
#   2026-09-07 連續跑三趟之後，`punish` 與 `notice` 兩條整段回 307，
#   上市的處置與注意當趟一列都沒收到——而 workflow 是綠的，
#   因為那兩發被防護正常擋下並記錄了。**沒有 skipped 清單就會完全看不出來。**
#   307 是暫時性的，要退避重試，不可以當成「這個端點不存在」。
RETRYABLE = {307, 403, 408, 429, 500, 502, 503, 504}
BACKOFF = [5, 15, 40]      # 秒。TWSE 的限流窗口實測要等到十秒以上才會放行


def get(url, body=None, ctype=None, retries=3, timeout=45):
    last = ""
    for i in range(retries + 1):
        try:
            hdr = {"User-Agent": UA, "Accept": "application/json,text/plain,*/*"}
            if ctype:
                hdr["Content-Type"] = ctype
            req = urllib.request.Request(url, data=body, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in RETRYABLE:
                return None, last          # 404／400 這種重試也沒用，直接回
            if i == retries:
                return None, f"{last}（重試 {retries} 次都失敗）"
        except Exception as e:                               # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            if i == retries:
                return None, f"{last}（重試 {retries} 次都失敗）"
        if i < len(BACKOFF):
            time.sleep(BACKOFF[i])
    return None, f"{last}（重試 {retries} 次都失敗）"


# ────────────────────────────────────────────── 小工具

def roc_to_iso(v):
    """民國 115/08/13 → 2026-08-13。認不出來回空字串，**不要自己補**。

    ⛔ 分隔符號有三種，全部出自實測，不是防呆寫爽的：
        `announcement/punish`  → `115/08/21`（斜線）
        `announcement/notice`  → `115.09.01`（**點**）
        `afterTrading/TWTAWU`  → `115/08/13`（斜線）
      標題那邊還有第四種 `115年08月08日`（由 `_check_echo` 只留數字處理）。
      **同一個交易所的同一個網站，四種寫法。**
      2026-09-07 首跑時只認斜線，134 列上市注意股的日期全部變空白——
      而且不報錯，因為「認不出來就留空」本身是對的設計。
    """
    m = re.match(r"^\s*(\d{2,3})[/.\-](\d{1,2})[/.\-](\d{1,2})\s*$", str(v or ""))
    if not m:
        return ""
    y, mo, d = int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))
    try:
        return datetime(y, mo, d).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def roc_any(v):
    """民國日期 → ISO。吃 `115/06/25`、`115.06.25`、`115-06-25` 與 `1000929` 七碼。

    `-` 或空字串一律回空（那是「這一列沒有這個日期」，不是錯誤）。
    """
    t = str(v or "").strip()
    if not t or t == "-":
        return ""
    iso = roc_to_iso(t)
    if iso:
        return iso
    m = re.fullmatch(r"(\d{3})(\d{2})(\d{2})", t)
    if m:
        return roc_to_iso(f"{m.group(1)}/{m.group(2)}/{m.group(3)}")
    return ""


def _clean_name(v):
    """`雙鴻(../../mainboard/...)` → `雙鴻`。TPEx 的名稱欄夾著連結。"""
    return re.sub(r"\s*\([^)]*\)\s*$", "", str(v or "")).strip()


def sec_kind(code):
    """⚠ 用代號形狀判的，不是來源給的。四位純數字＝普通股，其餘＝其他。

    上市權證（087319）、債券 ETF（00679B）、可轉債（33245）都會落到「其他」。
    報告只看普通股時要自己過濾——2015 年 TWTAWU 只有 9 筆而 2020 有 485 筆，
    差 54 倍幾乎都是權證，混在一起看會以為資料量爆增。
    """
    c = str(code or "").strip()
    return "普通股" if re.fullmatch(r"\d{4}", c) else "其他"


def _num(v):
    s = str(v or "").replace(",", "").strip()
    return s if re.fullmatch(r"-?\d+(\.\d+)?", s) else ""


def _check_echo(tag, want_iso, payload):
    """★ 防護①：回應自己回報的日期，跟我要的對不對得上。

    對不上就回 False——**那一發整個丟掉**。這是整支程式最重要的一段：
    日期格式寫錯時交易所不會報錯，只會安靜地回「今天」，
    照收的話會得到「每一天都是今天」的資料庫，而且一路成功、零例外。
    """
    echo = ""
    if isinstance(payload, dict):
        for k in ("date", "title", "stat", "message"):
            v = payload.get(k)
            if v and str(v).lower() not in ("ok", "okay"):
                echo = str(v)
                break
    if not echo:
        return True, "（回應沒有回報日期，無法核對）"
    # ⛔ 2026-09-07 首跑就誤殺了一發：原本只把 `/` 與 `-` 拿掉，
    #   而 `announcement/notice` 的標題寫的是「115年08月08日 至 115年09月07日」，
    #   `年月日` 沒被拿掉就比不到，整條上市注意股資料被丟光（attention.csv 上市 0 列）。
    #   **交易所同一個網站的日期寫法就有三種**（`115/08/01`、`115年08月08日`、
    #   `20150105`），所以這裡一律**只留數字**再比。
    #   ⚠ 防護誤殺跟防護失效一樣糟：它會安靜地少收一整塊，而且外表看起來成功。
    #   `_suspend_skipped.txt` 就是為了讓這種事被看見。
    ymd = want_iso.replace("-", "")
    roc = f"{int(want_iso[:4]) - 1911}{want_iso[5:7]}{want_iso[8:10]}"
    flat = re.sub(r"\D", "", echo)
    ok = ymd in flat or roc in flat
    if not ok:
        _SKIP_LOG.append(f"{tag}\t要 {want_iso}\t它回報 {echo!r}\t→ 丟棄這一發")
    return ok, echo


def _rows_of(payload):
    """頂層 data，或 tables[0].data。"""
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("data"), list):
        return payload["data"]
    for t in payload.get("tables") or []:
        if isinstance(t, dict) and isinstance(t.get("data"), list):
            return t["data"]
    return []


def _drop_placeholder(rows):
    """★ 防護②：TPEx 用「一列假資料」表示本日無資料，不是空陣列。

    判準是**證券代號為空**，不是去比對「本日無處置資料」這串字——
    字串會改，欄位空不空不會。
    """
    out = []
    for r in rows:
        if len(r) < 3 or not str(r[2] or "").strip():
            continue
        out.append(r)
    return out


KEY = {OUT_HALT: ("stock_id", "halt_date"),
       OUT_DISP: ("stock_id", "start_date"),
       OUT_ATTN: ("stock_id", "date")}


def _key(path, row, header):
    return tuple(row[header.index(k)] for k in KEY[path])


def _load(path, header):
    rows = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rd = csv.reader(f)
            head = next(rd, None)
            if head and head != header:
                raise ValueError(f"{path} 欄位不符：{head}")
            for q in rd:
                if not q:
                    continue
                # ⛔ 2026-09-07 自測抓到：這裡原本寫 `tuple(q[:len(KEY[path])])`，
                #   拿「前 N 欄」當鍵，而落檔時 `_key()` 是**按欄名**取。
                #   兩邊的鍵不一樣，重跑同一段就會長出重複列——
                #   而且 CSV 看起來完全正常，只是變胖。**讀寫要用同一支鑰匙。**
                row = (q + [""] * len(header))[:len(header)]
                k = _key(path, row, header)
                # ⛔ 鍵有一段是空的就丟掉。理由有兩個：
                #   ① 沒有日期的列本來就沒用——不知道哪一天發生的事等於沒有資料。
                #   ② 同一檔的多列會全部撞成同一個鍵，**互相蓋掉而不報錯**。
                #   2026-09-07 首跑就寫進 134 列這種（notice 的日期用點分隔，
                #   當時的解析認不出來）。這一行同時負責把舊的爛列清掉。
                if any(not x for x in k):
                    continue
                rows[k] = row
    return rows


def _save(path, header, rows):
    os.makedirs(META, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for k in sorted(rows):
            w.writerow(rows[k])
    return len(rows)


# ────────────────────────────────────────────── 上市（TWSE，日期不帶斜線）

TWSE = "https://www.twse.com.tw/rwd/zh"


def twse_pull(kind, s_iso, e_iso):
    path = {"halt": "afterTrading/TWTAWU", "disposal": "announcement/punish",
            "attention": "announcement/notice"}[kind]
    s, e = s_iso.replace("-", ""), e_iso.replace("-", "")
    url = f"{TWSE}/{path}?startDate={s}&endDate={e}&response=json"
    raw, err = get(url)
    if err:
        _SKIP_LOG.append(f"twse-{kind}\t{s_iso}~{e_iso}\t{err}")
        return []
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                  # noqa: BLE001
        _SKIP_LOG.append(f"twse-{kind}\t{s_iso}~{e_iso}\tJSON 失敗 {ex}")
        return []
    ok, _echo = _check_echo(f"twse-{kind}", s_iso, d)
    if not ok:
        return []
    return _rows_of(d)


# ────────────────────────────────────────────── 上櫃（TPEx，日期帶斜線）

TPEX = "https://www.tpex.org.tw/www/zh-tw/bulletin"


def tpex_pull(kind, s_iso, e_iso):
    page = {"disposal": "disposal", "attention": "attention"}[kind]
    s = s_iso.replace("-", "/")          # ★ 帶斜線。不帶的話它會安靜回「今天」
    e = e_iso.replace("-", "/")
    url = f"{TPEX}/{page}?startDate={s}&endDate={e}&response=json"
    raw, err = get(url)
    if err:
        _SKIP_LOG.append(f"tpex-{kind}\t{s_iso}~{e_iso}\t{err}")
        return []
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                  # noqa: BLE001
        _SKIP_LOG.append(f"tpex-{kind}\t{s_iso}~{e_iso}\tJSON 失敗 {ex}")
        return []
    ok, _echo = _check_echo(f"tpex-{kind}", s_iso, d)
    if not ok:
        return []
    return _drop_placeholder(_rows_of(d))


def tpex_halt_hist(year):
    """★ 上櫃停牌的歷史：`bulletin/sprcHis`，**POST，逐年**。

    ⛔ 2026-09-07 我一度寫下「上櫃停牌沒有歷史、永久補不回來」——**那是錯的**。
      前五輪猜了 `bulletin/suspend`／`haltTrading`／`afterTrading/spendi`／
      `bulletin/spendi`／`afterTrading/sprc` 全部 404，原因不是端點不存在，是
      ① 它是 **POST**，② 名字是當日那條 `sprc` 加 **His**。
      最後是打開官方頁面 /zh-tw/announce/market/halt/historical.html
      看它自己發什麼請求才拿到的。
      **教訓：猜第 N 個名字之前，先去看官方頁面自己怎麼叫它。**

    回傳的 `date` 是年份（例 "2026"），`tables[0].totalCount` 是筆數。
    ★ 這一條**有官方自己給的「有價證券類別」欄**（權證／上櫃股票／轉(交)換公司債／
      興櫃-一般板），比用代號形狀猜準——`5314 世紀*` 帶星號、`19094 榮成四` 是可轉債，
      形狀規則都會判錯。**有這一欄就用它，`sec_kind` 的啟發式只當退路。**
    """
    body = json.dumps({"year": str(year)}).encode()
    raw, err = get(f"{TPEX}/sprcHis", body=body, ctype="application/json")
    if err:
        _SKIP_LOG.append(f"tpex-halt-hist\t{year}\t{err}")
        return []
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                  # noqa: BLE001
        _SKIP_LOG.append(f"tpex-halt-hist\t{year}\tJSON 失敗 {ex}")
        return []
    # ★ 直接證據：回應的 `date` 就是它給的年份。對不上整年丟掉。
    got = str(d.get("date") or "")
    if got and got != str(year):
        _SKIP_LOG.append(f"tpex-halt-hist\t要 {year}\t它回報 {got!r}\t→ 丟棄這一發")
        return []
    return _rows_of(d)


def tpex_halt_today():
    """上櫃停牌的當日快照。`bulletin/sprc` 不吃任何日期參數（空 body 對照組實測）。"""
    raw, err = get(f"{TPEX}/sprc", body=b"{}", ctype="application/json")
    if err:
        _SKIP_LOG.append(f"tpex-halt\t當日\t{err}")
        return [], ""
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                  # noqa: BLE001
        _SKIP_LOG.append(f"tpex-halt\t當日\tJSON 失敗 {ex}")
        return [], ""
    # ★ 防護③：這一條的無資料是空陣列 + totalCount，不是假資料列
    stat = str(d.get("stat") or "")
    m = re.search(r"(\d{2,3}[/.\-]\d{1,2}[/.\-]\d{1,2})", stat)
    return _rows_of(d), roc_to_iso(m.group(1)) if m else ""


# ────────────────────────────────────────────── 正規化

def norm_halt_twse(rows, today):
    """TWTAWU：編號,證券代號,證券名稱,暫停交易日期,暫停交易時間,恢復交易日期,恢復交易時間"""
    out = []
    for r in rows:
        if len(r) < 6:
            continue
        code = str(r[1] or "").strip()
        if not code:
            continue
        out.append([code, _clean_name(r[2]), "twse", sec_kind(code),
                    roc_to_iso(r[3]), roc_to_iso(r[5]), "twse-TWTAWU", today])
    return out


# 官方「有價證券類別」→ 我方 sec_kind。**這是來源給的，優先於代號形狀。**
_TPEX_KIND = {"上櫃股票": "普通股", "興櫃-一般板": "興櫃", "興櫃": "興櫃",
              "權證": "其他", "轉(交)換公司債": "其他"}


def norm_halt_tpex_hist(rows, today):
    """sprcHis：編號,有價證券類別,有價證券代號,有價證券名稱,暫停交易日期,暫停交易時間,
                恢復交易日期,恢復交易時間

    ⛔ 兩個坑，都是實測看到的：
      ① **一個事件拆成兩列**：一列只填暫停、另一列只填恢復，另一半是 `-`。
         照收會得到一半 halt_date 空白、一半 resume_date 空白的資料。
         → 用（代號＋停牌日）與（代號＋恢復日）配對合併。
      ② **檔內兩種日期格式**：早期 `1000929`（七碼民國）＋ `80000`（時分秒），
         近期 `115/06/25` ＋ `09:00`。只認一種會漏掉整段早期資料。
    """
    halts, resumes = {}, []
    for r in rows:
        if len(r) < 7:
            continue
        code = str(r[2] or "").strip()
        if not code:
            continue
        kind = _TPEX_KIND.get(str(r[1] or "").strip()) or sec_kind(code)
        h, rs = roc_any(r[4]), roc_any(r[6])
        name = _clean_name(r[3])
        if h:
            halts.setdefault(code, []).append([code, name, "tpex", kind, h, "",
                                               "tpex-sprcHis", today])
        elif rs:
            resumes.append((code, rs))
    # 恢復日配給同一檔「最近一次還沒配到恢復日」的停牌
    for code, rs in sorted(resumes, key=lambda x: x[1]):
        cand = [x for x in halts.get(code, []) if not x[5] and x[4] <= rs]
        if cand:
            max(cand, key=lambda x: x[4])[5] = rs
    return [x for v in halts.values() for x in v]


def norm_halt_tpex(rows, day, today):
    """sprc：有價證券類別,有價證券代號,有價證券名稱,暫停交易,恢復交易

    ⚠ 這一條沒有歷史，`day` 是它自己回報的資料日期。
    暫停/恢復兩欄的格式在無資料時看不到（探針當天是 0 列），
    所以**認不出來就留空，不要自己填 day**——填了就是拿今天冒充事件日。
    """
    out = []
    for r in rows:
        if len(r) < 5:
            continue
        code = str(r[1] or "").strip()
        if not code:
            continue
        out.append([code, _clean_name(r[2]), "tpex", sec_kind(code),
                    roc_to_iso(r[3]) or day, roc_to_iso(r[4]),
                    "tpex-sprc", today])
    return out


def norm_disp_twse(rows, today):
    """punish：編號,公布日期,證券代號,證券名稱,累計,處置條件,處置起迄時間,處置措施,處置內容,備註"""
    out = []
    for r in rows:
        if len(r) < 7:
            continue
        code = str(r[2] or "").strip()
        if not code:
            continue
        span = str(r[6] or "")
        pair = re.findall(r"(\d{2,3}[/.\-]\d{1,2}[/.\-]\d{1,2})", span)
        out.append([code, _clean_name(r[3]), "twse", sec_kind(code),
                    roc_to_iso(r[1]),
                    roc_to_iso(pair[0]) if pair else "",
                    roc_to_iso(pair[1]) if len(pair) > 1 else "",
                    _num(r[4]), str(r[5] or "").strip()[:60],
                    "twse-punish", today])
    return out


def norm_disp_tpex(rows, today):
    """disposal：編號,公布日期,證券代號,證券名稱,累計,處置起訖時間,處置原因,處置內容,收盤價,本益比,(空)"""
    out = []
    for r in rows:
        if len(r) < 7:
            continue
        code = str(r[2] or "").strip()
        if not code:
            continue
        pair = re.findall(r"(\d{2,3}[/.\-]\d{1,2}[/.\-]\d{1,2})", str(r[5] or ""))
        out.append([code, _clean_name(r[3]), "tpex", sec_kind(code),
                    roc_to_iso(r[1]),
                    roc_to_iso(pair[0]) if pair else "",
                    roc_to_iso(pair[1]) if len(pair) > 1 else "",
                    _num(r[4]),
                    re.sub(r"\s*\([^)]*\)\s*$", "", str(r[6] or "")).strip()[:60],
                    "tpex-disposal", today])
    return out


def norm_attn_twse(rows, today):
    """notice：編號,證券代號,證券名稱,累計次數,注意交易資訊,日期,收盤價,本益比"""
    out = []
    for r in rows:
        if len(r) < 8:
            continue
        code = str(r[1] or "").strip()
        if not code:
            continue
        out.append([code, _clean_name(r[2]), "twse", sec_kind(code),
                    roc_to_iso(r[5]), _num(r[3]), str(r[4] or "").strip()[:80],
                    _num(r[6]), _num(r[7]), "twse-notice", today])
    return out


def norm_attn_tpex(rows, today):
    """attention：編號,證券代號,證券名稱,累計,注意交易資訊,公告日期,收盤價,本益比,link"""
    out = []
    for r in rows:
        if len(r) < 8:
            continue
        code = str(r[1] or "").strip()
        if not code:
            continue
        out.append([code, _clean_name(r[2]), "tpex", sec_kind(code),
                    roc_to_iso(r[5]), _num(r[3]), str(r[4] or "").strip()[:80],
                    _num(r[6]), _num(r[7]), "tpex-attention", today])
    return out


# ────────────────────────────────────────────── 主流程

def _months(s_iso, e_iso):
    y, m = int(s_iso[:4]), int(s_iso[5:7])
    ey, em = int(e_iso[:4]), int(e_iso[5:7])
    while (y, m) <= (ey, em):
        last = (datetime(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
        yield f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def collect(s_iso, e_iso, sleep, with_tpex_halt):
    today = now_tpe().strftime("%Y-%m-%d")
    halt = _load(OUT_HALT, H_HALT)
    disp = _load(OUT_DISP, H_DISP)
    attn = _load(OUT_ATTN, H_ATTN)
    n0 = (len(halt), len(disp), len(attn))

    dropped = {"n": 0}

    def put(store, path, header, newrows):
        for row in newrows:
            k = _key(path, row, header)
            if any(not x for x in k):
                # 日期解析不出來的列不落檔。**寧可少一列，不要一列沒有日期的資料**。
                dropped["n"] += 1
                _SKIP_LOG.append(f"{os.path.basename(path)}\t{row[0]} {row[1]}\t"
                                 f"鍵有空值 {k}\t→ 不落檔")
                continue
            store[k] = row

    # ⛔ 迄日不可以超過今天。TWTAWU 對未來日期**整發拒收**
    #   （回「查詢日期大於今日，請重新查詢!」），2026 全年那一發因此整年沒抓到。
    cap = now_tpe().strftime("%Y-%m-%d")
    e_iso = min(e_iso, cap)

    # 上市：整段一發就好，端點吃得下整年
    for y in range(int(s_iso[:4]), int(e_iso[:4]) + 1):
        a = max(s_iso, f"{y}-01-01")
        b = min(e_iso, f"{y}-12-31")
        put(halt, OUT_HALT, H_HALT, norm_halt_twse(twse_pull("halt", a, b), today))
        time.sleep(sleep)
        put(disp, OUT_DISP, H_DISP, norm_disp_twse(twse_pull("disposal", a, b), today))
        time.sleep(sleep)
        put(attn, OUT_ATTN, H_ATTN, norm_attn_twse(twse_pull("attention", a, b), today))
        time.sleep(sleep)
        print(f"  [twse {y}] 停牌 {len(halt)}／處置 {len(disp)}／注意 {len(attn)}（累計）")

    # 上櫃：逐月。★ 範圍上限沒有實測過，逐月是為了萬一它有上限時不會安靜截斷
    for a, b in _months(s_iso, e_iso):
        put(disp, OUT_DISP, H_DISP, norm_disp_tpex(tpex_pull("disposal", a, b), today))
        time.sleep(sleep)
        put(attn, OUT_ATTN, H_ATTN, norm_attn_tpex(tpex_pull("attention", a, b), today))
        time.sleep(sleep)
        if a.endswith("-12-01"):
            print(f"  [tpex {a[:4]}] 處置 {len(disp)}／注意 {len(attn)}（累計）")

    # ★ 上櫃停牌的歷史（2026-09-08 補上，`sprcHis` 逐年）
    for y in range(int(s_iso[:4]), int(e_iso[:4]) + 1):
        got = norm_halt_tpex_hist(tpex_halt_hist(y), today)
        put(halt, OUT_HALT, H_HALT, got)
        if got:
            print(f"  [tpex 停牌 {y}] {len(got)} 個事件")
        time.sleep(sleep)

    if with_tpex_halt:
        rows, day = tpex_halt_today()
        put(halt, OUT_HALT, H_HALT, norm_halt_tpex(rows, day, today))
        print(f"  [tpex 停牌] 當日快照 {day or '（沒回報日期）'}，{len(rows)} 列")

    n1 = (_save(OUT_HALT, H_HALT, halt), _save(OUT_DISP, H_DISP, disp),
          _save(OUT_ATTN, H_ATTN, attn))
    os.makedirs(META, exist_ok=True)
    # ⛔ 這個檔原本是每趟覆蓋。回補要分很多趟跑（一次一兩年），
    #   覆蓋等於**只看得到最後一趟**，前面幾趟被擋掉什麼永遠不知道。
    #   2026-09-07 的 2015 年資料就是這樣消失的：查不出當時被擋的原因。
    #   改成累加，每趟一個標頭。
    new_file = not os.path.exists(SKIPPED)
    with open(SKIPPED, "a", encoding="utf-8") as f:
        if new_file:
            f.write("# 被防護擋下來的請求（**累加**，不會被下一趟蓋掉）\n"
                    "# 不是空的就要看：多半是日期格式寫錯"
                    "（TWSE 不帶斜線、TPEx 帶斜線），\n"
                    "# 交易所不會報錯，只會安靜回「今天」。擋下來總比寫進去好。\n")
        f.write(f"\n# ── {now_tpe().isoformat(timespec='seconds')}　"
                f"{s_iso}~{e_iso}　擋下 {len(_SKIP_LOG)} 筆\n")
        for x in _SKIP_LOG:
            f.write(x + "\n")

    print(f"\n[suspend] 停牌 {n0[0]}→{n1[0]}／處置 {n0[1]}→{n1[1]}／"
          f"注意 {n0[2]}→{n1[2]}　列")

    # ★ 把「跑完要人工比對的事」變成程式自己檢查（2026-09-08）
    rl = runlog.Run("suspend", os.path.join(META, "_last_run.md"))
    rl.info("區間", f"{s_iso} ~ {e_iso}")
    kinds = collections.Counter(v[3] for v in halt.values())
    rl.info("停牌", f"{n1[0]} 列（{dict(kinds)}）")
    rl.info("處置", f"{n1[1]} 列")
    rl.info("注意", f"{n1[2]} 列")

    # ① 鍵有空值的列一列都不該落檔（2026-09-07 曾寫進 134 列）
    empty = sum(1 for st, path, hd in ((halt, OUT_HALT, H_HALT),
                                       (disp, OUT_DISP, H_DISP),
                                       (attn, OUT_ATTN, H_ATTN))
                for row in st.values() if any(not x for x in _key(path, row, hd)))
    rl.check("沒有鍵含空值的列", empty == 0, f"實際 {empty} 列")

    # ② 這一趟不該有被擋下來的請求。有就是日期格式或限流出事，
    #    而那兩種**都不會讓程式失敗**——2026-09-07 兩次都是這樣漏掉一整塊。
    rl.check("這一趟沒有被擋下來的請求", not _SKIP_LOG,
             f"{len(_SKIP_LOG)} 筆，見 {os.path.basename(SKIPPED)}")

    # ③ 列數只能增不能減。回補是可重複跑的，變少代表讀寫的鍵對不上或誤刪
    rl.check("列數沒有變少",
             n1[0] >= n0[0] and n1[1] >= n0[1] and n1[2] >= n0[2],
             f"{n0} → {n1}")

    # ④ 涵蓋 30 天以上時，上市與上櫃都該有注意股。整邊掛零就是那一邊被擋掉了
    span = (datetime.strptime(e_iso, "%Y-%m-%d")
            - datetime.strptime(s_iso, "%Y-%m-%d")).days
    mk = collections.Counter(v[2] for v in attn.values())
    rl.check("注意股兩個市場都有資料",
             span < 30 or (mk.get("twse", 0) > 0 and mk.get("tpex", 0) > 0),
             f"上市 {mk.get('twse', 0)}／上櫃 {mk.get('tpex', 0)}")

    rc = rl.finish()
    if dropped["n"]:
        print(f"[suspend] ★ 有 {dropped['n']} 列因為鍵有空值沒有落檔", file=sys.stderr)
    if _SKIP_LOG:
        print(f"[suspend] ★ 有 {len(_SKIP_LOG)} 筆被擋下來 → {SKIPPED}", file=sys.stderr)
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--start", default="", help="回補起年（YYYY）或起日（YYYY-MM-DD）")
    ap.add_argument("--end", default="", help="回補迄年／迄日")
    ap.add_argument("--sleep", type=float, default=5.0)
    a = ap.parse_args()

    today = now_tpe()
    if a.daily:
        s = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        e = today.strftime("%Y-%m-%d")
        return collect(s, e, a.sleep, with_tpex_halt=True)
    if a.backfill:
        s = a.start if "-" in a.start else f"{a.start or 2015}-01-01"
        e = a.end if "-" in a.end else f"{a.end or today.year}-12-31"
        # ★ 上櫃停牌沒有歷史，回補時不抓——抓了也只會拿到今天，
        #   寫進去就變成「2015 年那天有這些停牌」。
        return collect(s, e, a.sleep, with_tpex_halt=False)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
