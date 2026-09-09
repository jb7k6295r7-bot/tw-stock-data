#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otccal_probe.py — **上櫃交易日曆的第二來源**探針。只測、不寫資料。

## 為什麼要有這一支（2026-09-09）

`data/meta/_data_audit.md` 裡，上櫃交易日曆是**唯一一列 C 級**：

    | 上櫃交易日曆 | **自我一致 0 天差異，但那只證明自洽** | 櫃買官方休市公告（端點我方取不到） |

「自我一致」的意思是：日曆 ＝ `data/universe/daily/` 裡有上櫃成交的日期集合。
那是**拿自己的產出當自己的判準**——當初若某一天整批漏抓，那天就不在日曆裡，
於是每一個 feed **一致地缺同一天**，覆蓋率算出來還是 100%。
C 級最危險的地方就在這裡：**它長得跟 A 級一模一樣。**

上市那邊已經有第二判準了（`calendar_audit.py` 用 TWSE `FMTQIK` 大盤月報，
跟個股行情是兩條不同的端點）。⛔ **但 FMTQIK 只有上市**，
上櫃至今沒有任何外部判準。這一支就是去找它。

## 判準（⛔ 先寫在這裡，跑之前就定好，免得看到結果再挑一個能過的）

一個候選要算數，**四項全過**：

1. **是上櫃這一邊的。** 拿上市的日曆套上櫃不算——那是假設不是證據。
   （實務上兩市開休市相同，但「相同」正是要被檢驗的那句話。）
2. **有日期序列**，而且要問清楚**日期的最小值與最大值**。
   ⭐ 這一項最重要：形狀對、欄位對、但日期只有最近一年的，那就只能驗一年。
3. **一天一列**，能回答「某一天到底有沒有開盤」。
   ⛔ **只列國定假日不夠**——我方日曆裡有 8 個週六是**實測有成交的補班日**
     （2016-01-30 / 2016-06-04 / 2016-09-10 / 2017-02-18 /
      2017-06-03 / 2017-09-30 / 2018-03-31 / 2018-12-22）。
     照「補班日不交易」的規則做，會刪掉 8 個真的交易日。
4. **跟我方日檔是兩條不同的路。** 我方上櫃日檔走的是
   `www/zh-tw/afterTrading/otc`（逐檔行情）。
   再打一次逐檔行情不叫第二來源，那叫**問同一個人兩次**。

## 這一支**不做**什麼

⛔ 不寫日曆、不改任何資料、不下「上櫃日曆是對的／錯的」的結論。
   它只回報「有沒有一條路可以走」。真的比對要等這支報出**可用的端點**之後，
   由 `calendar_audit.py` 那一半來做（那支才是有 rl.check 的）。

## ⚠ TPEx 只有在 Actions 上驗得到

開發容器與 WebFetch 打 twse／tpex／taifex 一律 403（2026-09-09 再次實測）。
**「這條路不通」這種結論，只有 Actions 上跑出來的才算數。**
"""
import io
import json
import os
import re
import sys
import traceback
# ⚠ 2026-09-09：第 [3] 節第二輪用了 `urllib.parse.urljoin` 卻沒 import。
#   `selftest_probes.py` 當場炸出 NameError——**這一次是在推之前**。
#   今早 holiday_probe 犯同一個錯時假頁面沒有 `<script src>`，那條分支
#   從沒被走到，於是一路過關到 Actions。⇒ 假回應的形狀對，測試才有用。
import urllib.parse

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_otccal_probe.txt")
DAILY_DIR = os.path.join(_ROOT, "universe", "daily")

OPENAPI = "https://www.tpex.org.tw/openapi/v1/"

# ── 候選 A：櫃買 openapi 裡「大盤層級／歷史」的端點 ────────────────────
#   ⛔ 這一批**不是我編的**：全部逐字來自 `data/meta/_tpex_probe.txt`，
#     那份是 tpex_probe.py 從 https://www.tpex.org.tw/openapi/swagger.json
#     實際抓下來的 225 個端點目錄。名稱與說明都照抄。
#   ⚠ swagger 說這些端點「參數 無」⇒ 它們很可能只回一份固定內容；
#     所以第 2 項（日期 min/max）就是它們能不能用的**唯一**分水嶺。
OPENAPI_CANDS = [
    ("tpex_daily_trading_index", "上櫃日成交量值指數", "★ 最像 FMTQIK 的那一個"),
    ("tpex_index", "櫃買指數歷史資料", "★ 櫃買指數＝上櫃大盤，名字就寫著歷史"),
    ("tpex_reward_index", "櫃買指數與報酬指數之收市指數", ""),
    ("tpex50_index", "富櫃50指數歷史收盤指數", ""),
    ("tpcgi_reward_index", "上櫃公司治理指數歷史收盤指數", ""),
    ("tpci_reward_index", "櫃買「薪酬指數」歷史收盤指數", ""),
    ("tphd_index", "高殖利率指數歷史收盤指數", ""),
    ("tpex_emp88_reward_index", "櫃買「勞工就業88指數」歷史收盤指數", ""),
]

# ── 候選 B：櫃買新站「休市日」那一頁自己呼叫的端點 ─────────────────────
#   TWSE 那邊就是這樣找到的（頁面是空殼，但它載入的 js 裡有 rwd 路徑）。
HOLIDAY_PAGE = "https://www.tpex.org.tw/zh-tw/announce/market/holiday.html"

#   ⚠⚠ 下面這一組是**我猜的路徑**，不是從任何官方文件抄來的。
#     猜的依據：櫃買新站的資料端點慣例是 `www/zh-tw/<區段>/<名稱>?response=json`
#     （我方已在用的 `www/zh-tw/afterTrading/otc`、`www/zh-tw/bulletin/revivt`
#      都是這個形狀），而那一頁的網址是 `/zh-tw/announce/market/holiday.html`。
#     ⛔ **猜的路徑只有「回了真的資料」才算數**，回 404／空殼一律當成不存在，
#       ⛔ 更不可以把猜的網址寫進報告當結論——2026-09-09 我才犯過一次
#         （憑空編了一個 data.gov.tw dataset id，實測「休市」0 次）。
GUESS = [
    "https://www.tpex.org.tw/www/zh-tw/announce/holiday?response=json",
    "https://www.tpex.org.tw/www/zh-tw/announce/market/holiday?response=json",
    "https://www.tpex.org.tw/www/zh-tw/bulletin/holiday?response=json",
    "https://www.tpex.org.tw/www/zh-tw/market/holiday?response=json",
]

# ── 候選 C：TWSE 那支已經通了的開休市行事曆，問它「涵不涵蓋上櫃」 ────────
#   ⚠ 它的標題是「115 年市場開休市日期」。「市場」兩個字**沒有說是哪個市場**。
#     ⛔ 那正是不可以用假設補的地方 ⇒ 這一節只做一件事：
#       數它的內文裡有沒有「櫃」「上櫃」「證券商營業處所」。
TWSE_CAL = ("https://www.twse.com.tw/rwd/zh/holidaySchedule/"
            "holidaySchedule?response=json")

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# otccal_probe.py 的輸出。這是探針結果，不是資料。\n")
            f.write("# 要答的問題：**上櫃交易日曆有沒有第二來源**"
                    "（目前唯一一列 C 級：只有自我一致）。\n")
            f.write("# 判準四項見 otccal_probe.py 檔頭，"
                    "⛔ 其中第 2 項（日期 min/max）是分水嶺。\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[otccal] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[otccal] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


# ────────────────────────────────────────────────────────────────────
def _to_iso(v):
    """把看得懂的日期寫法轉成 YYYY-MM-DD；看不懂就回 None。

    ⛔ 不做「抓到數字就當日期」。台股的坑是民國年：`1150909` 與 `20260909`
      長得像同一種東西，錯一個世紀不會有人發現。
    """
    s = str(v).strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    elif re.fullmatch(r"\d{8}", s):
        y, mo, d = int(s[:4]), int(s[4:6]), int(s[6:])
    elif re.fullmatch(r"(\d{2,3})[-/](\d{1,2})[-/](\d{1,2})", s):
        m = re.fullmatch(r"(\d{2,3})[-/](\d{1,2})[-/](\d{1,2})", s)
        y, mo, d = int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))
    elif re.fullmatch(r"\d{7}", s):          # 民國 1150909
        y, mo, d = int(s[:3]) + 1911, int(s[3:5]), int(s[5:])
    else:
        return None
    if not (1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def _rows_of(raw):
    """把回應解成 list[dict]。回 (rows, 形狀說明)。⛔ 解不出來就老實說解不出來。"""
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        return [], f"不是 JSON（{type(ex).__name__}）"
    if isinstance(d, list):
        if d and isinstance(d[0], dict):
            return d, "list[dict]"
        return [], f"list 但元素是 {type(d[0]).__name__ if d else '空'}"
    if isinstance(d, dict):
        # TWSE/TPEx 新站的 {stat, fields, data} 形狀
        f, data = d.get("fields"), d.get("data") or d.get("aaData")
        if isinstance(f, list) and isinstance(data, list):
            out = []
            for r in data:
                if isinstance(r, list):
                    out.append({f[i] if i < len(f) else f"_{i}":
                                (r[i] if i < len(r) else "")
                                for i in range(max(len(f), len(r)))})
            return out, f"dict{{stat={d.get('stat')!r}, title={str(d.get('title'))[:40]!r}}}"
        return [], "dict 但沒有 fields/data：鍵 " + str(list(d.keys())[:8])
    return [], f"型別 {type(d).__name__}"


def _date_cols(rows):
    """回報**每一個欄位**有多少值解得出日期。⛔ 不挑欄位名，用解析成功率決定。"""
    if not rows:
        return []
    keys, out = list(rows[0].keys()), []
    for k in keys:
        vals = [_to_iso(r.get(k, "")) for r in rows]
        ok = [v for v in vals if v]
        if len(ok) >= max(2, len(rows) * 0.9):    # 九成以上解得出來才算日期欄
            out.append((k, len(ok), sorted(set(ok))))
    return out


def _gaps(days):
    """最大相鄰間隔幾天——用來分辨「逐日」與「一年只有幾筆」。"""
    import datetime as _dt
    if len(days) < 2:
        return None
    ds = [_dt.date(*map(int, d.split("-"))) for d in days]
    return max((ds[i + 1] - ds[i]).days for i in range(len(ds) - 1))


def _ours():
    """我方目前的上櫃日曆：`data/universe/daily/` 裡**有上櫃列**的日期集合。

    ⛔ 這就是那個 C 級的東西本身，不是判準。列在這裡是為了讓下面的比對有得比。
    """
    out = []
    if not os.path.isdir(DAILY_DIR):
        return out
    for fn in sorted(os.listdir(DAILY_DIR)):
        if not fn.endswith(".csv"):
            continue
        try:
            with io.open(os.path.join(DAILY_DIR, fn), "rb") as f:
                if b",tpex," in f.read():
                    out.append(fn[:-4])
        except OSError:
            pass
    return out


def _compare(name, theirs, ours):
    """在**交集區間**內雙向比對。⛔ 交集之外不比——那是「他們沒有」不是「不一致」。"""
    if not theirs or not ours:
        say("     （其中一邊是空的，不比）")
        return
    lo, hi = max(theirs[0], ours[0]), min(theirs[-1], ours[-1])
    if lo > hi:
        say(f"     ⚠ 與我方日曆**沒有重疊區間**（對方 {theirs[0]}~{theirs[-1]}／"
            f"我方 {ours[0]}~{ours[-1]}）⇒ 驗不了")
        return
    T = {d for d in theirs if lo <= d <= hi}
    O = {d for d in ours if lo <= d <= hi}
    only_t, only_o = sorted(T - O), sorted(O - T)
    say(f"     ★ 重疊區間 {lo} ~ {hi}｜對方 {len(T)} 天／我方 {len(O)} 天")
    say(f"       對方有、我方無 {len(only_t)} 天" +
        (f"：{only_t[:8]}" if only_t else "  ← 這一類幾乎確定是我方漏抓"))
    say(f"       我方有、對方無 {len(only_o)} 天" +
        (f"：{only_o[:8]}" if only_o else "  ← 這一類要逐日看，⛔ 不可以自動刪"))
    if not only_t and not only_o:
        say(f"       ⇒ 【{name}】在這個區間內與我方**完全一致**——"
            "這就是上櫃日曆缺的那個外部判準。")


def _probe_json(url, label, note=""):
    """一個候選的完整回報：形狀／欄位／列數／**日期 min-max**。"""
    say(f"\n  ── {label}{('  ' + note) if note else ''}")
    say(f"     {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        say(f"     ✗ 抓不到：{str(err)[:160]}")
        return None
    rows, shape = _rows_of(raw)
    say(f"     ✓ {len(raw):,} bytes｜{shape}｜列數 {len(rows)}")
    if not rows:
        say("     ⇒ 解不出列 ⇒ 這一條這一輪沒有結論（⛔ 不等於端點不存在）")
        return None
    say(f"     欄位：{list(rows[0].keys())}")
    say(f"     首列：{json.dumps(rows[0], ensure_ascii=False)[:220]}")
    dc = _date_cols(rows)
    if not dc:
        say("     ⇒ **沒有日期欄** ⇒ 判準第 2 項不過，這一條不能當日曆來源")
        return None
    best = None
    for k, n, days in dc:
        g = _gaps(days)
        say(f"     日期欄「{k}」：解得出 {n}/{len(rows)}｜唯一 {len(days)} 天｜"
            f"{days[0]} ~ {days[-1]}｜最大相鄰間隔 {g} 天")
        if best is None or len(days) > len(best[1]):
            best = (k, days)
    return best[1] if best else None


# ────────────────────────────────────────────────────────────────────
def main():
    say("── 上櫃交易日曆的第二來源 探針 ──")
    say("問題：上櫃日曆目前**只有自我一致**（C 級）。上市那邊有 FMTQIK 當第二判準，"
        "⛔ 但 FMTQIK 只有上市。")
    say("判準四項（跑之前就定好的，見檔頭）："
        "① 是上櫃這邊的 ② 日期 min/max 蓋得到 ③ 一天一列 ④ 與我方日檔不同條路")

    # ── [1] 先量清楚「被驗的東西」長什麼樣 ────────────────────────────
    say("\n[1] 我方現況（⛔ 這是被驗的對象，不是判準）")
    ours = _ours()
    if ours:
        say(f"     `data/universe/daily/` 裡**有上櫃列**的日期："
            f"{len(ours):,} 天｜{ours[0]} ~ {ours[-1]}")
        g = _gaps(ours)
        say(f"     最大相鄰間隔 {g} 天"
            + ("（過年那一段）" if g and g >= 5 else ""))
    else:
        say("     ✗ 讀不到日檔目錄——這一支在 repo 之外跑的？下面的比對會全部跳過")

    # ── [2] 櫃買 openapi 的大盤／指數歷史端點 ─────────────────────────
    say("\n[2] ★ 候選 A：櫃買 openapi 的「大盤層級／歷史」端點")
    say("     來源：`data/meta/_tpex_probe.txt`（swagger.json 實抓的 225 個端點目錄），"
        "⛔ 端點名逐字照抄，不是我拼的")
    say("     ④ 為什麼算「不同條路」：我方上櫃日檔走 `www/zh-tw/afterTrading/otc`"
        "（逐檔行情），這一批是 openapi 的**指數／大盤合計**，不同端點、不同彙總層級。")
    hit = []
    for path, desc, note in OPENAPI_CANDS:
        days = _probe_json(OPENAPI + path, f"/{path}｜{desc}", note)
        if days:
            _compare(path, days, ours)
            hit.append((path, days))

    # ── [3] 櫃買休市日那一頁 ─────────────────────────────────────────
    say("\n[3] 候選 B：櫃買新站「休市日」那一頁，以及它自己呼叫的端點")
    say("     ⚠ 已知（`_tpex_probe.txt` [9]）：那一頁是 **js 空殼**，"
        "HTML 裡「休市」只出現 5 次、沒有表格。這一節是去看它載入的 js。")
    raw, err = B.get(HOLIDAY_PAGE, retries=2, timeout=60)
    if err:
        say(f"     ✗ 頁面抓不到：{str(err)[:160]}")
    else:
        t = raw.decode("utf-8", "replace")
        han = len(re.findall("[一-龥]", t))
        say(f"     ✓ {len(raw):,} bytes｜中文 {han:,} 字｜<tr> {t.count('<tr')} 個"
            + ("  ← 空殼確認" if t.count("<tr") == 0 else ""))
        js = re.findall(r'<script[^>]+src=["\']([^"\']+)', t)
        say(f"     載入的 js {len(js)} 支：{js[:10]}")
        # ★ 從頁面自己的字串裡撈路徑，⛔ 不是從我腦袋裡撈
        paths = sorted(set(re.findall(r'["\'](/www/[a-zA-Z0-9_\-/]+)["\']', t)))
        say(f"     頁面字串裡的 /www/ 路徑 {len(paths)} 個：{paths[:10]}")
        # ★★ 2026-09-09 第二輪（使用者再次給了這一頁）。上一輪只**數**了
        #   中文字數與 <tr> 個數，⛔ **沒有印出這一頁到底寫了什麼**——
        #   而「頁面是空殼」與「頁面說『請見公告專區』」是兩種完全不同的結論，
        #   前者要去翻 js，後者要去翻它指過去的地方。**數字分不出這兩者。**
        txt = re.sub(r"<script[^>]*>.*?</script>", " ", t, flags=re.S)
        txt = re.sub(r"<style[^>]*>.*?</style>", " ", txt, flags=re.S)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        say(f"     ★ 這一頁**看得見的字**（{len(txt)} 字，全部印出來）：")
        for i in range(0, min(len(txt), 2000), 160):
            say("       " + txt[i:i + 160])
        # ★ 頁面裡的連結：空殼頁常常只是把人導去別的地方
        hrefs = sorted(set(re.findall(r'href=["\']([^"\'#]+)', t)))
        hrefs = [h for h in hrefs if not h.endswith((".css", ".ico", ".png", ".jpg"))]
        say(f"     頁面裡的連結 {len(hrefs)} 個：{hrefs[:20]}")

        # ★★★ 第四輪（2026-09-09 20:2x）。第三輪的結論是**否定的**：
        #   `tables.js` 那 142 處 `calendar` 全是 **moment.js 的語系表與
        #   daterangepicker**，唯一像端點的字串是 Google reCAPTCHA。
        #   ⇒ **關鍵字次數多≠有端點**。11 支 js 裡一條寫死的路徑都沒有。
        #   而 js 裡夾帶一個真線索：`isROC`／`yearOnly`／`monthOnly`
        #   ——那是**民國年**的日期選擇器，和頁面上「歷年開休市日期：民國 ___」
        #   對得起來 ⇒ 資料是**選了年份之後才去要**的。
        #   ⇒ 網址只剩兩個地方可能：**頁面自己的 inline `<script>`**，
        #     或 **`data-*` 屬性**（`_tpex_probe.txt` [10] 就記過 TPEx 用 data-）。
        inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", t, re.S)
        say(f"     ★★ 頁面自己的 inline <script> {len(inline)} 段"
            f"（共 {sum(len(x) for x in inline):,} 字）：")
        for i, blk in enumerate(inline):
            b = re.sub(r"\s+", " ", blk).strip()
            if not b:
                continue
            say(f"       ── 第 {i + 1} 段（{len(b)} 字）")
            for k in range(0, min(len(b), 1200), 160):
                say(f"         {b[k:k + 160]}")
        # ★ data-* 屬性：TPEx 新站把參數放在這裡（見 _tpex_probe.txt [10]）
        das = sorted(set(re.findall(r'(data-[a-zA-Z0-9_\-]+)\s*=\s*["\']([^"\']*)',
                                    t)))
        say(f"     ★ `data-*` 屬性 {len(das)} 種：")
        for k, v in das[:40]:
            say(f"       {k} = {v[:90]!r}")

        # ★★ 翻它載入的**每一支** js。上一輪只翻過 global.js。
        #   ⛔ 這裡找的是**它自己寫的路徑**，不是我拼的——差別在於
        #     前者是證據，後者是猜測。
        say("     ★ 逐支 js 裡的路徑與關鍵字（⛔ 只回報找到的，不拼網址）")
        for j in js:
            if j.startswith("http") and "tpex.org.tw" not in j:
                say(f"       ・{j}｜（外部網域，跳過）")
                continue
            ju = urllib.parse.urljoin(HOLIDAY_PAGE, j)
            jr, je = B.get(ju, retries=1, timeout=45)
            if je:
                say(f"       ✗ {j}｜{str(je)[:70]}")
                continue
            jt = jr.decode("utf-8", "replace")
            paths = sorted(set(re.findall(
                r'["\'](/(?:www|openapi|web)/[A-Za-z0-9_\-/.]{3,80})["\']', jt)))
            kw = {w: jt.count(w) for w in ("holiday", "Holiday", "休市", "calendar",
                                           "Calendar", "announce")}
            kw = {k: v for k, v in kw.items() if v}
            say(f"       ・{j}｜{len(jr):,} bytes｜路徑 {len(paths)} 個"
                + (f"：{paths[:8]}" if paths else "")
                + (f"｜關鍵字 {kw}" if kw else "｜（沒有關鍵字）"))
            # ★★ 第三輪（2026-09-09 20:3x）。上一輪在 `tables.js` 裡量到
            #   `calendar` 56 次、`Calendar` 86 次，**而路徑抓到 0 個**。
            #   ⇒ 那不代表沒有端點，代表**網址是字串拼出來的**，
            #     而我的正則只認寫死的絕對路徑。
            #   ⛔ 所以這裡改成「把那些字附近的原文印出來」——
            #     ⛔ 不是再拼一次網址，是去看它自己怎麼拼。
            if kw.get("calendar") or kw.get("Calendar") or kw.get("holiday"):
                say(f"         ★★ 這一支有關鍵字，印出附近的原文（最多 12 段）：")
                seen, shown = set(), 0
                for m in re.finditer(r"[Cc]alendar|[Hh]oliday", jt):
                    seg = jt[max(0, m.start() - 150):m.start() + 150]
                    seg = re.sub(r"\s+", " ", seg).strip()
                    key = seg[100:200]
                    if key in seen:
                        continue
                    seen.add(key)
                    say(f"           …{seg}…")
                    shown += 1
                    if shown >= 12:
                        break
                # ★ 另外把這一支裡**所有像端點的字串**撈出來，不限開頭
                eps = sorted(set(re.findall(
                    r'["\']((?:https?://[^"\']{6,90}|/[A-Za-z0-9_\-/.]{6,60}'
                    r'(?:\.(?:php|json|html|do|ashx)|/[a-z\-]{3,30})))["\']', jt)))
                say(f"         ★ 這一支裡像端點的字串 {len(eps)} 個：{eps[:25]}")

    say("\n     ⚠⚠ 下面這一組**是我猜的路徑**（依據：櫃買新站端點的命名慣例）。")
    say("       ⛔ 只有「回了真的資料」才算數；404／空殼一律當不存在，"
        "⛔ 而且不論結果如何，猜的網址**不會**被寫成結論。")
    for u in GUESS:
        raw, err = B.get(u, retries=1, timeout=45)
        if err:
            say(f"     ✗ {u.split('zh-tw/')[-1]}：{str(err)[:90]}")
            continue
        rows, shape = _rows_of(raw)
        say(f"     ? {u.split('zh-tw/')[-1]}：{len(raw):,} bytes｜{shape}｜列數 {len(rows)}")
        if rows:
            say(f"       欄位：{list(rows[0].keys())}｜"
                f"首列 {json.dumps(rows[0], ensure_ascii=False)[:160]}")

    # ── [4] TWSE 行事曆到底涵不涵蓋上櫃 ──────────────────────────────
    say("\n[4] 候選 C：TWSE 開休市行事曆——**它說的「市場」包不包含上櫃？**")
    say("     ⛔ 這一節不是去拿日曆（那支已經通了），是去問一句話：")
    say("       它的標題是「115 年市場開休市日期」，而「市場」兩個字沒有指名哪一個市場。")
    say("       ⇒ 若內文完全沒提到櫃買／上櫃，那就**不能**拿它當上櫃的判準——"
        "那會是拿假設當證據。")
    raw, err = B.get(TWSE_CAL, retries=2, timeout=60)
    if err:
        say(f"     ✗ 抓不到：{str(err)[:160]}")
    else:
        t = raw.decode("utf-8", "replace")
        try:
            d = json.loads(t)
        except ValueError:
            d = {}
        say(f"     ✓ {len(raw):,} bytes｜stat={d.get('stat')!r}｜"
            f"title={d.get('title')!r}")
        for w in ("櫃買", "上櫃", "證券商營業處所", "興櫃", "臺灣證券交易所",
                  "集中交易市場", "期貨", "補行上班", "補班"):
            say(f"       「{w}」出現 {t.count(w)} 次")
        say("     ⇒ ⛔ 若「櫃買／上櫃／證券商營業處所」全是 0 次，"
            "這一支就只證明上市，**不可以拿來當上櫃日曆的判準**。")

    # ── [5] 結論 ────────────────────────────────────────────────────
    say("\n[5] 這一輪的結論")
    if hit:
        say(f"     ✓ 有 {len(hit)} 個候選端點回了帶日期序列的資料：")
        for p, days in hit:
            say(f"       /{p}：{len(days)} 天｜{days[0]} ~ {days[-1]}")
        say("     ⇒ 下一步：把**唯一一個涵蓋期間最長、且與我方 0 差異**的接進"
            "`calendar_audit.py`，寫成有 rl.check 的比對。")
        say("     ⛔ 但先看清楚涵蓋期間：只蓋得到近一年的，就只能把那一年升級成 B，"
            "**2015~2025 仍然是 C**——⛔ 不可以整列寫成「已升 B」。")
    else:
        say("     ✗ 這一輪沒有任何候選端點回出帶日期的序列。")
        say("     ⛔ 那就是「還沒找到」，**不是**「不存在」，"
            "更不是「所以我方日曆是對的」。")
    say("\n── 下一步 ──")
    say("⛔ 在拿到第二來源之前，`_data_audit.md` 裡那一列**維持 C 級**。")
    say("⛔ 不論這一支報什麼，都不要因此去刪／補任何一天的日檔——"
        "這支只回答「有沒有路」，真正的比對要有 rl.check 的那一半來做。")
    return _write(0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                            # noqa: BLE001
        traceback.print_exc()
        say("\n✗ 探針自己炸了（traceback 在上面）——"
            "⛔ 這不代表任何一條路不通，代表這一支沒跑完。")
        _write(1)
        raise
