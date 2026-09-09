#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tdcc_probe.py — 集保戶股權分散表的端點探針。**只測、不寫資料。**

## 為什麼要有這一支

籌碼集中度目前沒有歷史序列（`db_status.py` 把「集保流通股數」列在「沒有來源」
那一節）。FinMind 的 `TaiwanStockHoldingSharesPer` 回 **HTTP 400**，
所以要走集保官方。

端點來自 WebSearch 結果，**不是自行生成**（`tw-data-sources` 3-4 的 `tdcc.com.tw`
一列明寫這條規矩）：

    https://opendata.tdcc.com.tw/getOD.ashx?id=1-5      集保戶股權分散表

## ★ 怎麼證明「拿到的是完整的一週」

「有回東西」不構成可用的證據——這個專案已經被靜默截斷騙過兩次
（`t187ap03_L`、`MI_MARGN`）。所以本檔的判準全部是**獨立於回應自己**的：

1. **分級筆數**：`tw-data-sources` 第四節第 10 項記載集保分成 **17 級**
   （第 1～15 級是持股級距，另有「合計」與「差異數調整」）。
   每一檔都應該剛好 17 列——不是 17 就是欄位或期別搞錯。
2. **恆等式**：`合計 ＝ Σ(第 1～15 級) − 差異數調整`，人數與股數各驗一次。
   **對不上就是抓錯期別或欄位錯位，整批丟棄，不要只修那一列。**
3. **涵蓋率分段看**：對照 `data/meta/industry.csv`（上市＋上櫃 1,984 檔）。
   截斷的特徵是「前段 100%、後段 0%」的斷崖，不是均勻地少。
   **這一項最有力**——均勻缺少可能是它本來就不含某類證券。
4. **資料日期**：應該只有一個（單週檔）。多個日期代表這是累計檔，
   拿它當單週會整批錯。

## 為什麼結論只能在 Actions 上下

`feeds_prereg.md` 已經寫死：**所有端點結論一律以 Actions 的 probe 為準**。
開發容器對外是 403，那是環境差異，不是端點狀態。

輸出寫進 `data/meta/_tdcc_probe.txt`（與 `_suspend_probe.txt`、`_capital_probe.txt`
同一個做法），這樣結論會進 repo，不必有人去翻 Actions log。
"""
import csv
import io
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
IND = os.path.join(_ROOT, "meta", "industry.csv")

# 查詢頁與它背後的 ajax。**兩個都取自 [5] 節的實測輸出**，不是自行拼的：
#   [5] 從 qryStock 頁面抓到 `/portal/smWeb/qryStockAjax`。
QRY_PAGE = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"
AJAX = "https://www.tdcc.com.tw/portal/smWeb/qryStockAjax"
OUT = os.path.join(_ROOT, "meta", "_tdcc_probe.txt")

# 查詢頁多半要指定標的才肯回東西，所以每一發都帶一檔。
# ⛔ 這個值只是「隨便一檔活著的上市股」，不是判定的一部分——
#   判定一律看**回應自己宣告的日期**，不是看我送出去的參數。
SAMPLE = "2330"

URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"

# ★ 兩個還沒解決的問題，兩個都不猜、都去看官方頁面自己怎麼說（網址來自 WebSearch）：
#   ① `getOD.ashx?id=1-5` 只回最新一週。但**查詢頁有「資料日期」下拉選單**，
#      代表歷史查得到——要找出那個清單與它背後的請求長什麼樣。
#   ② 開放資料專區列出所有 dataset id（1-5 只是其中一個），
#      其他 id 可能就是歷史或別的切面。
#   ③ 分級代碼 1~17 各自對應多少股，**CSV 沒有給文字**，查詢頁上有。
PAGES = [
    ("開放資料專區（所有 dataset id）",
     "https://www.tdcc.com.tw/portal/zh/stats/openData"),
    ("集保戶股權分散表查詢頁（資料日期清單＋級距文字）",
     "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"),
]

# 欄名不確定，兩種寫法都收（民國／英文都可能）。找不到就把實際表頭印出來。
CODE_KEYS = ("證券代號", "股票代號", "代號", "SecuritiesCompanyCode", "StockNo")
DATE_KEYS = ("資料日期", "日期", "Date")
LEVEL_KEYS = ("持股分級", "分級", "HoldingLevel")
PEOPLE_KEYS = ("人數", "HolderCount", "people")
SHARE_KEYS = ("股數", "持股股數", "Shares", "shares")

LINES = []


def _post(url, form, referer=None):
    """POST 一發表單。`B.get` 只有 GET，而查詢頁那條是 POST。

    ⚠ 回傳與 `B.get` 同形狀 `(bytes, err)`，而且**保留 `LIMITED|` 前綴**——
      「被限流」與「端點沒有這個東西」必須分得出來，否則會去改根本沒錯的參數。

    `referer`：查詢頁那條 AJAX 多半會檢查來源頁；帶上它才像是從頁面送出的。
    ⚠ 2026-09-09：第 7 節呼叫時傳了 `referer=`，而這裡當時**沒有這個參數**，
      於是 `TypeError: _post() got an unexpected keyword argument 'referer'`。
      本地 403 走不到那一行，而 selftest 的假 `_post` 寫成 `(url, form, **kw)`
      ——**假的比真的寬鬆，就把簽章不符藏起來了**。已一併修 selftest。
    """
    data = urllib.parse.urlencode(form).encode()
    headers = {
        "User-Agent": B.UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,*/*"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read(), None
    except urllib.error.HTTPError as e:                          # noqa: BLE001
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:160]
        except Exception:                                        # noqa: BLE001
            pass
        loc = e.headers.get("Location") if e.headers else None
        if (e.code in (301, 302, 303, 307, 308) and not loc) or e.code == 429:
            return None, f"LIMITED|HTTP {e.code}（被擋／限流）| {body}"
        return None, f"HTTP {e.code} {e.reason} | {body}"
    except Exception as ex:                                      # noqa: BLE001
        return None, f"{type(ex).__name__}: {ex}"


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def pick(row, keys):
    for k in keys:
        if k in row and str(row[k]).strip() != "":
            return str(row[k]).strip()
    return ""


def num(v):
    # ⛔ 不可以寫 `str(v or "")`：**整數 0 是 falsy**，會被換成空字串然後回 None，
    #   於是「這一格是 0」與「這一格沒有值」變得分不出來。CSV 來源全是字串
    #   （"0" 是 truthy）所以看不出問題，JSON 來源就會中——這種錯不會報錯，
    #   只會讓恆等式莫名其妙對不上。（2026-09-08 寫集保驗算時抓到）
    s = "" if v is None else str(v).replace(",", "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def parse(raw):
    """→ (list[dict], 說明)。CSV 與 JSON 都試，**不預設是哪一種**。"""
    txt = None
    for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if txt is None:
        return [], "四種編碼都解不開"
    t = txt.lstrip()
    if t[:1] in ("[", "{"):
        try:
            d = json.loads(t)
        except Exception as ex:                                  # noqa: BLE001
            return [], f"看起來是 JSON 但解析失敗：{type(ex).__name__}"
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list):
                    d = v
                    break
        if not isinstance(d, list):
            return [], "JSON 頂層不是 list"
        # ⚠ 這個函式的契約是 `list[dict]`，而 JSON 的 list 裡**什麼都可能有**
        #   （字串、數字、又一層 list）。放行的話下游 `pick()` 的 `k in row`
        #   會對 int 丟 `TypeError: argument of type 'int' is not iterable`——
        #   而那是在**探針的後段**才會踩到，本地 403 永遠碰不到。
        #   ⇒ 在這裡就把契約守住，並且**把丟掉幾筆講出來**（不是安靜過濾）。
        rows = [x for x in d if isinstance(x, dict)]
        drop = len(d) - len(rows)
        note = f"JSON {len(rows):,} 筆"
        if drop:
            note += f"（⚠ 另有 {drop:,} 筆不是物件，已排除——這個端點的形狀和其他的不一樣）"
        return rows, note
    rows = list(csv.DictReader(io.StringIO(txt)))
    return rows, f"CSV {len(rows):,} 列"


def main():
    say("── 集保戶股權分散表探針 ──")
    say(f"端點（WebSearch 結果，非自行生成）：{URL}")
    raw, err = B.get(URL, retries=2, timeout=90)
    if err:
        say(f"✗ 請求失敗：{err[:200]}")
        say("  ⚠ 若這是在開發容器跑的，403 是環境差異不是端點狀態；"
            "結論一律以 Actions 的 probe 為準。")
        return _write(1)
    say(f"✓ 取得 {len(raw):,} bytes")
    say(f"  開頭：{raw[:120].decode('utf-8', 'replace').replace(chr(10), ' ')}")

    rows, note = parse(raw)
    say(f"  解析：{note}")
    if not rows:
        return _write(1)
    say(f"  表頭：{list(rows[0].keys())}")

    code_k = next((k for k in rows[0] if k in CODE_KEYS), None)
    if not code_k:
        say("✗ 找不到代號欄——**上面的表頭就是要拿去對的東西**，不要猜欄名")
        return _write(1)

    dates = {pick(r, DATE_KEYS) for r in rows} - {""}
    say(f"\n[1] 資料日期：{sorted(dates)[:5]}（共 {len(dates)} 個）")
    say("    ⚠ 單週檔應該只有一個日期；多個代表這是累計檔，"
        "拿它當單週會整批錯" if len(dates) != 1 else "    ✓ 只有一個日期，是單週檔")

    by = {}
    for r in rows:
        by.setdefault(str(r[code_k]).strip(), []).append(r)
    say(f"\n[2] 證券檔數 {len(by):,}｜總列數 {len(rows):,}")
    lv = {}
    for c, rs in by.items():
        lv[len(rs)] = lv.get(len(rs), 0) + 1
    say(f"    每檔的列數分布：{dict(sorted(lv.items()))}")
    say("    ✓ 全部 17 級" if list(lv) == [17]
        else "    ⚠ 不是全部 17 級——分級結構與紀錄不符（skill 第四節第 10 項），要重看欄位")

    # [3] 恆等式：合計 = Σ(1..15) − 差異數調整
    say("\n[3] 恆等式 合計 ＝ Σ(第 1～15 級) − 差異數調整")
    lvl_k = next((k for k in rows[0] if k in LEVEL_KEYS), None)
    ppl_k = next((k for k in rows[0] if k in PEOPLE_KEYS), None)
    shr_k = next((k for k in rows[0] if k in SHARE_KEYS), None)
    if not (lvl_k and shr_k):
        say(f"    ⚠ 找不到分級／股數欄（分級={lvl_k} 股數={shr_k}），"
            "無法驗算——**這時不可以宣告端點可用**")
    else:
        bad, checked = [], 0
        for c, rs in list(by.items())[:200]:          # 抽驗前 200 檔就夠看出系統性錯位
            tot = adj = None
            parts = []
            for r in rs:
                lab = str(r[lvl_k]).strip()
                v = num(r[shr_k])
                if v is None:
                    continue
                if "合計" in lab or lab == "17":
                    tot = v
                elif "差異" in lab or lab == "16":
                    adj = v
                else:
                    parts.append(v)
            if tot is None or not parts:
                continue
            checked += 1
            if tot != sum(parts) - (adj or 0):
                bad.append((c, tot, sum(parts), adj))
        say(f"    抽驗 {checked} 檔｜不符 {len(bad)} 檔")
        for b in bad[:5]:
            say(f"      {b[0]} 合計 {b[1]:,}／分級加總 {b[2]:,}／差異調整 {b[3]}")
        say("    ✓ 恆等式全通過" if checked and not bad
            else "    ⚠ 對不上就是抓錯期別或欄位錯位——**整批丟棄，不要只修那一列**")
        if ppl_k:
            say(f"    （人數欄 `{ppl_k}` 存在，正式抓取時要再驗一次人數那一道）")

    # [4] 涵蓋率**分段**看：截斷的特徵是斷崖，不是均勻地少
    say("\n[4] 涵蓋率（對照 data/meta/industry.csv）")
    if not os.path.exists(IND):
        say("    ⚠ 找不到 industry.csv，跳過")
    else:
        want = set()
        with io.open(IND, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                want.add(r["stock_id"])
        got = set(by)
        hit = want & got
        say(f"    母體 {len(want):,} 檔｜命中 {len(hit):,} 檔"
            f"（{len(hit) / len(want) * 100:.1f}%）｜集保有而母體沒有 {len(got - want):,}")
        say("    分段（截斷會是斷崖，不是均勻地少）：")
        for lo in range(1000, 10000, 1000):
            seg = {c for c in want if c.isdigit() and lo <= int(c) < lo + 1000}
            if not seg:
                continue
            h = len(seg & got)
            say(f"      {lo}-{lo + 999}：{h}/{len(seg)}（{h / len(seg) * 100:.0f}%）")

    # ── [5] 歷史與級距：去看官方頁面自己怎麼說 ──
    say("\n[5] ★ 歷史與級距對照（官方頁面）")
    for label, url in PAGES:
        say(f"\n  ── {label}")
        say(f"     {url}")
        raw2, err2 = B.get(url, retries=2, timeout=60)
        if err2:
            say(f"     ✗ 抓不到：{err2[:120]}")
            continue
        html = raw2.decode("utf-8", "replace")
        say(f"     ✓ {len(raw2):,} bytes")
        # 資料日期清單：頁面上的 <option> 值，多半就是可查的週別
        opts = re.findall(r"<option[^>]*value=[\"']?(\d{8})[\"']?", html)
        if opts:
            say(f"     ★ 資料日期選項 {len(opts)} 個：{opts[:5]} … {opts[-3:]}")
            say("       → **歷史查得到**，不是只有最新一週")
        # 級距文字：像「1-999」「1,000-5,000」這種
        lv = re.findall(r"([0-9,]{1,12}\s*[-~至]\s*[0-9,]{1,12})", html)
        lv = [x for x in dict.fromkeys(lv) if "," in x or len(x) > 5][:20]
        if lv:
            say(f"     ★ 疑似級距文字：{lv}")
        # dataset id：開放資料專區列的 getOD.ashx?id=N-M
        ids = sorted(set(re.findall(r"getOD\.ashx\?id=([0-9]+-[0-9]+)", html)))
        if ids:
            say(f"     ★ dataset id：{ids}")
        # 這一頁背後的 API
        api = sorted(set(re.findall(r"[\"'\(](/?[a-zA-Z0-9_/-]*(?:smWeb|opendata|api)[a-zA-Z0-9_/-]*)", html)))
        if api:
            say(f"     疑似 API 路徑：{api[:10]}")
        if not (opts or lv or ids or api):
            say("       （什麼都沒抓到——頁面可能是 JS 動態組的）")
            js = sorted(set(re.findall(r"[\"'\(]([^\"'\(\)]+\.js)[\"'\)]", html)))
            say(f"       載入的 js：{js[:8]}")

    # ── [6] ★ 人數那一道恆等式：直接把不符的 17 列印出來 ──
    #   2026-09-08 正式抓取（tdcc.py）第一趟就卡在這裡：股數 4,051 檔全過，
    #   **人數 66 檔不符**，而且清一色是 00 開頭（0050、00406A、00642U…）。
    #   本節的用意是**拿直接證據**——把那幾檔的 17 列原樣印出來，
    #   才知道是「來源本來就這樣」還是「我方欄位錯位」。
    #   ⛔ 在看到這 17 列之前不可以去放寬 tdcc.py 的驗算：那等於用猜的
    #      把一道守門條件拆掉，而它擋下來的東西本來就看不見。
    say("\n[6] ★ 人數那一道：不符的檔案長什麼樣")
    if not (lvl_k and ppl_k and shr_k):
        say("    ⚠ 欄位不齊，跳過")
    else:
        def _idcheck(rs, key):
            tot = adj = None
            parts = []
            for r in rs:
                lab = str(r[lvl_k]).strip()
                v = num(r[key])
                if v is None:
                    continue
                if "合計" in lab or lab == "17":
                    tot = v
                elif "差異" in lab or lab == "16":
                    adj = v
                else:
                    parts.append(v)
            if tot is None or not parts:
                return None
            return tot, sum(parts), adj

        bad_p, bad_s = [], []
        for c, rs in by.items():                   # ★ 全部驗，不抽樣
            for key, box in ((ppl_k, bad_p), (shr_k, bad_s)):
                got = _idcheck(rs, key)
                if got and got[0] != got[1] - (got[2] or 0):
                    box.append((c, got))
        say(f"    全部 {len(by):,} 檔｜人數不符 {len(bad_p)}｜股數不符 {len(bad_s)}")
        # 不符的是哪一類證券？**用代號形狀分類，不用猜**
        def _shape(c):
            if c.startswith("00"):
                return "00 開頭（ETF／受益憑證）"
            return "四碼數字（普通股）" if c.isdigit() and len(c) == 4 else "其他"
        for box, label in ((bad_p, "人數"), (bad_s, "股數")):
            if not box:
                continue
            kinds = {}
            for c, _ in box:
                kinds[_shape(c)] = kinds.get(_shape(c), 0) + 1
            say(f"    {label}不符的代號形狀：{kinds}")
        for c, (tot, ssum, adj) in bad_p[:3]:
            say(f"\n    ── {c}｜人數 合計 {tot:,}／分級加總 {ssum:,}／差異調整 {adj}"
                f"｜差 {tot - (ssum - (adj or 0)):+,}")
            say(f"       {'級':>4} {'人數':>12} {'股數':>16}")
            for r in sorted(by[c], key=lambda x: (str(x[lvl_k]).zfill(2))):
                say(f"       {str(r[lvl_k]).strip():>4} {str(r[ppl_k]).strip():>12} "
                    f"{str(r[shr_k]).strip():>16}")
        if bad_p and not bad_s:
            say("\n    → 股數全過、只有人數不符：**這是來源自己的性質，不是欄位錯位**"
                "（錯位會兩欄一起壞）。要不要放寬，看上面 17 列的實際數字再決定。")

    # ── [7] ★ 歷史週別到底抓不抓得到（第二版）──
    #
    #   ⛔ 第一版兩發都只回 **2 bytes**。那不是「參數被無視」，是**空回應**：
    #     `SYNCHRONIZER_TOKEN` 多半是一次性的，照抄頁面那一顆送第二次就失效。
    #   本版改三件事：
    #     ① **每一發都先重抓查詢頁、拿新的 token**（這是上一版的結論）
    #     ② 日期欄名**兩個都試**：form 裡是 `firDate`、select 是 `scaDate`，
    #        上一版的挑法會先撞到 `firDate`，可能挑錯那一個
    #     ③ 查詢多半要指定標的，所以帶 `stockNo=2330`、`sqlMethod=StockNo`
    #   ⚠ 為什麼這件事值得多花一輪：集保端點**只回最新一週、不吃日期**，
    #     **漏掉一週就永久少一週**。查詢頁列了 51 週（20250912~20260904），
    #     那是目前唯一看得到的歷史來源。
    say("\n[7] ★ 歷史週別（第二版：每發重抓 token、兩個日期欄名都試）")

    def _form_and_dates():
        """每次都重抓查詢頁 → (form, 日期選項)。token 一次性，不可重用。"""
        raw, err = B.get(QRY_PAGE, retries=2, timeout=60)
        if err:
            return None, [], err
        html = raw.decode("utf-8", "replace")
        f = {}
        for m in re.finditer(r"<input[^>]*>", html, re.I):
            tag = m.group(0)
            n = re.search(r"name=[\"']([^\"']+)", tag)
            v = re.search(r"value=[\"']([^\"']*)", tag)
            t = re.search(r"type=[\"']([^\"']+)", tag)
            if n and (not t or t.group(1).lower() not in ("submit", "button", "reset")):
                f[n.group(1)] = v.group(1) if v else ""
        opts = re.findall(r"<option[^>]*value=[\"']?(\d{8})[\"']?", html)
        return f, opts, None

    form0, opts, err7 = _form_and_dates()
    if err7:
        say(f"    ✗ 查詢頁抓不到：{str(err7)[:140]}")
        if str(err7).startswith("LIMITED"):
            say("    ⚠ 被限流擋下，不是端點沒有——換個時間再測。")
    elif len(opts) < 2:
        say(f"    ⚠ 日期選項只有 {len(opts)} 個，沒得比對新舊")
    else:
        newest, older = opts[0], opts[len(opts) // 2]
        say(f"    日期選項 {len(opts)} 個｜最新 {newest}｜較舊 {older}｜"
            f"最舊 {opts[-1]}")
        seen = {}
        for field in ("scaDate", "firDate"):
            say(f"\n    ── 日期欄名試 `{field}`")
            for tag, day in (("最新", newest), ("較舊", older)):
                f, _, e = _form_and_dates()          # ★ 每一發都重抓，拿新 token
                if e:
                    say(f"       {tag} {day}：✗ 查詢頁重抓失敗 {str(e)[:80]}")
                    continue
                f[field] = day
                f["sqlMethod"] = "StockNo"
                f["stockNo"] = SAMPLE
                f["stockName"] = ""
                raw2, e2 = _post(AJAX, f, referer=QRY_PAGE)
                if e2:
                    say(f"       {tag} {day}：✗ {str(e2)[:110]}")
                    continue
                txt = raw2.decode("utf-8", "replace")
                # ⛔ 用**回應自己宣告的日期**判斷，不是用我送出去的參數
                echoed = sorted(set(re.findall(r"\b(20\d{6})\b", txt)))
                nums = len(re.findall(r"\b\d{1,3}(?:,\d{3}){2,}\b", txt))
                say(f"       {tag} {day}：{len(raw2):,} bytes｜"
                    f"回應裡的日期 {echoed[:4]}｜大數字 {nums} 個")
                seen[(field, tag)] = (len(raw2), tuple(echoed[:4]))
        say("")
        tiny = [k for k, v in seen.items() if v[0] < 200]
        if tiny and len(tiny) == len(seen):
            say("    ⛔ **每一發都還是空回應（< 200 bytes）。**")
            say("       重抓 token 沒有解決，代表擋點不在 token——")
            say("       可能還要 Cookie／Session，或這條 ajax 不接受直接呼叫。")
            say("       ⛔ 仍然**不可以**下「沒有歷史」的結論：查詢頁確實列了"
                f" {len(opts)} 個週別，只是我方取不到。")
        elif len(seen) >= 2:
            vals = set(seen.values())
            if len(vals) == 1:
                say("    ⛔ **所有組合回的長度與日期完全一樣——參數被無視。**")
            else:
                say("    ✓ **不同週別回不同內容——歷史真的抓得到。**")
                for k, v in sorted(seen.items()):
                    say(f"       {k[0]}／{k[1]}：{v[0]:,} bytes｜日期 {list(v[1])}")

    # ── [8] 另一條路：開放資料專區還有哪些 dataset id ──
    #   [5] 抓到 1-1 ~ 1-16 等一整排 id，我方只用了 1-5。
    #   ⚠ **不是去猜哪個是歷史**，是把每個的形狀量出來讓人看：
    #     回幾列、有幾個相異的資料日期。**有多個日期的才可能是歷史檔。**
    say("\n[8] 開放資料專區其他 dataset id 的形狀（只量，不猜用途）")
    for did in ("1-1", "1-2", "1-3", "1-4", "1-6", "1-7"):
        r9, e9 = B.get(f"https://opendata.tdcc.com.tw/getOD.ashx?id={did}",
                       retries=1, timeout=60)
        if e9:
            say(f"    id={did}: ✗ {str(e9)[:80]}")
            continue
        rows, note = parse(r9)
        dates = sorted({pick(x, DATE_KEYS) for x in rows} - {""})
        say(f"    id={did}: {len(r9):,} bytes｜{note}｜"
            f"相異資料日期 {len(dates)} 個 {dates[:3]}"
            f"{' ← ★ 多個日期' if len(dates) > 1 else ''}")
        if rows:
            say(f"             欄位：{list(rows[0])[:8]}")

    # ── [9] ★★ 政府資料開放平臺 dataset 11452 ──
    #   網址由使用者 2026-09-09 提供，**非自行生成**。
    #   為什麼值得試：集保官方端點只回最新一週，而 data.gov.tw 是**中介目錄**——
    #   它會列出資料集的**實際下載網址**與更新頻率。若那裡登的是另一個網址
    #   （或帶期別參數的網址），就是我們一直找不到的歷史來源。
    #
    #   ⛔ 兩條路都試、都印出來，**不猜哪條對**：
    #     ① 網頁本身（人看的頁面）
    #     ② `api/v2/rest/dataset/<id>`（該站的公開 API，回 JSON）
    #   哪一條成功、哪一條失敗，都照實記——這樣下一個人不必重猜。
    say("\n[9] ★★ 政府資料開放平臺 dataset 11452（使用者 2026-09-09 提供）")
    DGT = [("網頁", "https://data.gov.tw/dataset/11452"),
           ("公開 API", "https://data.gov.tw/api/v2/rest/dataset/11452")]
    dl = set()
    for label, url in DGT:
        say(f"\n  ── {label}：{url}")
        r10, e10 = B.get(url, retries=2, timeout=60)
        if e10:
            say(f"     ✗ {str(e10)[:140]}")
            continue
        txt = r10.decode("utf-8", "replace")
        say(f"     ✓ {len(r10):,} bytes")
        # 資料集自己宣告的欄位：名稱、更新頻率、時間範圍、提供機關
        for kw in ("資料集名稱", "更新頻率", "資料時間", "起始時間", "結束時間",
                   "提供機關", "檔案格式", "授權"):
            hit = [x.strip()[:90] for x in
                   re.findall(r"[^\n\r]{0,40}" + kw + r"[^\n\r]{0,70}", txt)][:2]
            if hit:
                say(f"     {kw}：{hit}")
        # ★ 下載網址：全部撈出來，**逐字印**，不整理
        for m in re.findall(r'https?://[^\s"\'<>\\)]{10,200}', txt):
            if any(k in m.lower() for k in ("getod", "download", ".csv", ".zip",
                                            "tdcc", "opendata", "ashx")):
                dl.add(m)
    if dl:
        say(f"\n  ★ 撈到的下載網址（{len(dl)} 個，逐字）：")
        for u in sorted(dl)[:15]:
            say(f"     {u}")
    else:
        say("\n  （沒撈到下載網址——上面兩條都失敗，或頁面是 JS 動態組的）")

    # ── [10] 撈到的網址逐一量形狀：**有多個資料日期的才可能是歷史** ──
    say("\n[10] ★ 撈到的網址逐一量形狀（只量，不猜用途）")
    known = {URL}
    todo = [u for u in sorted(dl) if u not in known][:4]
    if not todo:
        say("    （沒有新的網址可量，或撈到的就是我方已在用的那一條）")
    for u in todo:
        r11, e11 = B.get(u, retries=1, timeout=90)
        if e11:
            say(f"    {u[:80]}\n       ✗ {str(e11)[:90]}")
            continue
        rows, note = parse(r11)
        dates = sorted({pick(x, DATE_KEYS) for x in rows} - {""})
        say(f"    {u[:80]}")
        say(f"       {len(r11):,} bytes｜{note}｜相異資料日期 {len(dates)} 個 {dates[:4]}"
            f"{'  ← ★★ 多個日期＝可能是歷史檔' if len(dates) > 1 else ''}")
        if rows:
            say(f"       欄位：{list(rows[0])[:8]}")

    # ── [11] ★ 17 級的「級距文字」到底在哪一頁 ──
    #   目前 `data/tdcc/` 只有代碼 1~17，沒有「1-999」「1,000-5,000」這種文字，
    #   所以「400 張以上算大戶」這種定義**寫不出來**。
    #   ⛔ 我知道坊間流傳的對照表，但那是**間接證據**——級距寫錯會讓
    #     大戶持股的定義整個偏掉，而且不會有任何地方報錯。**只抄官方頁面上的字。**
    #
    #   ⚠ 第 5 節在查詢頁只撈到 `['11-7410', '02-2719']`——那是**電話號碼**，
    #     不是級距。原因很可能是：級距文字只出現在**查詢結果**的表格裡，
    #     不在查詢頁本身。所以這一節多試幾個地方，並且換一個嚴一點的判準。
    say("\n[11] ★ 級距文字（1-999、1,000-5,000…）在哪一頁")

    def _cands(txt):
        """撈出所有「小-大」的數字對。⚠ 這一步**不做判斷**，電話號碼也會進來。"""
        out = []
        for m in re.finditer(r"([0-9][0-9,]{0,14})\s*[-~至]\s*([0-9][0-9,]{0,14})", txt):
            a, b = m.group(1), m.group(2)
            try:
                ia, ib = int(a.replace(",", "")), int(b.replace(",", ""))
            except ValueError:
                continue
            if ia < ib:
                out.append((ia, ib, f"{a}-{b}"))
        return list(dict.fromkeys(out))

    def _chain(cands):
        """找最長的「接得起來」的鏈：下一段的下界 ＝ 上一段的上界 ＋ 1。

        ⛔ **這才是級距與電話號碼的差別。**
          第 5 節只用 `\d+-\d+`，於是撈到 `02-2719`（集保客服電話）與 `11-7410`，
          而且它們也符合「小-大」——用大小關係濾不掉。
          但級距是**連續分段**：1-999 → 1,000-5,000 → 5,001-10,000 …
          電話號碼接不上任何東西。

        實測（假文字）：只有電話 → 最長鏈 1 段；真的級距表＋電話 → 14 段。
        """
        byl = {}
        for lo, hi, t in cands:
            byl.setdefault(lo, (hi, t))
        best = []
        for lo, hi, t in sorted(cands):
            cur, nxt = [(lo, hi, t)], hi + 1
            while nxt in byl:
                h2, t2 = byl[nxt]
                cur.append((nxt, h2, t2))
                nxt = h2 + 1
            if len(cur) > len(best):
                best = cur
        return best

    def _upper(txt):
        """最後一級那種「N 以上」單獨收。"""
        return list(dict.fromkeys(
            f"{m.group(1)} 以上"
            for m in re.finditer(r"([0-9][0-9,]{2,14})\s*(?:股|單位)?以上", txt)))

    #   ⚠ 這幾個網址的來源：第 5 節從官方頁面自己撈到的「疑似 API 路徑」，
    #     以及 2026-09-09 WebSearch 的結果（`/investor/` 那個變體、`smart.` 那台主機）。
    #     ⛔ 都不是我自己拼的。
    CAND = [
        ("查詢頁（本體）", QRY_PAGE),
        ("查詢頁 /investor/ 變體",
         "https://www.tdcc.com.tw/portal/zh/investor/smWeb/qryStock"),
        ("另一台主機的開放資料", "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"),
        ("開放資料專區", "https://www.tdcc.com.tw/portal/zh/stats/openData"),
    ]
    for label, url in CAND:
        say(f"\n  ── {label}：{url}")
        r11, e11 = B.get(url, retries=1, timeout=60)
        if e11:
            say(f"     ✗ {str(e11)[:120]}")
            continue
        txt = r11.decode("utf-8", "replace")
        cands = _cands(txt)
        chain = _chain(cands)
        ups = _upper(txt)
        say(f"     ✓ {len(r11):,} bytes｜「小-大」數字對 {len(cands)} 個"
            f"｜**最長連續鏈 {len(chain)} 段**｜「N 以上」{len(ups)} 個")
        if len(chain) >= 3:
            for _, _, t in chain:
                say(f"       {t}")
            for u in ups[:3]:
                say(f"       {u}（上界那一格）")
            # ★ 官方是 17 級 ⇒ 16 段區間 ＋ 1 段「以上」。
            #   ⛔ 不是這個數也照實記，**不要湊**。
            tot = len(chain) + (1 if ups else 0)
            say(f"     {'★★ 鏈長 ＋ 上界 ＝ 17，與官方級數相符' if tot == 17 else f'（合計 {tot} 段，不是 17，⛔ 不可以當成那張表）'}")
        elif cands:
            say(f"       （接不成鏈，最長只有 {len(chain)} 段——"
                f"這些多半是電話或代碼，不是級距）")
        else:
            say("       （一個都沒有）")

    say("\n  ⛔ 以上任何一條都**不可以**拿去填 `data/tdcc/` 的級距欄位——"
        "要先有人看過、確認那是官方定義而不是頁面上剛好長得像的字串。")

    # ── [12] ★★★ 集保自己的 OpenAPI 文件 ──
    #   第 10 節從 data.gov.tw 的資料集頁撈到一個我方**完全不知道**的網址：
    #       https://openapi.tdcc.com.tw/tdcc-opendata-api-docs
    #   66,918 bytes、JSON、頂層只有一個 `url` 欄 ⇒ 那是**文件索引**，
    #   真正的規格在它指的地方。
    #
    #   ⭐ 這一條同時可能解掉兩個缺口，所以優先度最高：
    #     ① **集保歷史**——規格裡若有吃日期／期別的端點，那就是找了三輪的東西
    #     ② **17 級的級距文字**——規格通常會寫欄位定義與 enum
    #   ⛔ 但一樣：**量到才算數**，不從欄名猜用途。
    say("\n[12] ★★★ 集保自己的 OpenAPI 文件（第 10 節撈到的新網址）")
    DOCS = "https://openapi.tdcc.com.tw/tdcc-opendata-api-docs"
    specs, seen12 = [], set()
    r12, e12 = B.get(DOCS, retries=2, timeout=90)
    if e12:
        say(f"  ✗ 抓不到索引：{str(e12)[:130]}　⛔ 抓不到不等於不存在")
    else:
        t12 = r12.decode("utf-8", "replace")
        say(f"  ✓ 索引 {len(r12):,} bytes")
        # 索引裡的 url 欄；同時把整份文字裡的絕對網址也撈出來（不整理）
        for m in re.finditer(r'"url"\s*:\s*"([^"]{4,300})"', t12):
            specs.append(m.group(1))
        for m in re.finditer(r'https?://[^\s"\'<>\\)]{10,200}', t12):
            if "tdcc" in m.group(0):
                specs.append(m.group(0))
        specs = [x for x in dict.fromkeys(specs)][:8]
        say(f"  索引裡的網址（{len(specs)} 個，逐字）：")
        for x in specs:
            say(f"    {x}")

    def _abs(u):
        if u.startswith("http"):
            return u
        return "https://openapi.tdcc.com.tw" + ("" if u.startswith("/") else "/") + u

    for u in specs:
        au = _abs(u)
        if au in seen12 or au == DOCS:
            continue
        seen12.add(au)
        say(f"\n  ── 規格：{au}")
        r13, e13 = B.get(au, retries=1, timeout=90)
        if e13:
            say(f"     ✗ {str(e13)[:120]}")
            continue
        t13 = r13.decode("utf-8", "replace")
        say(f"     ✓ {len(r13):,} bytes")
        try:
            d13 = json.loads(t13)
        except Exception:                                        # noqa: BLE001
            say("     （不是 JSON——照實記，下一輪再看要怎麼讀）")
            d13 = None
        if isinstance(d13, dict) and isinstance(d13.get("paths"), dict):
            ps = sorted(d13["paths"])
            say(f"     端點 {len(ps)} 個：")
            for pth in ps[:25]:
                ops = d13["paths"][pth] or {}
                pars = []
                for op in ops.values():
                    if isinstance(op, dict):
                        for q in (op.get("parameters") or []):
                            if isinstance(q, dict) and q.get("name"):
                                pars.append(q["name"])
                pars = sorted(set(pars))
                # ★ 吃日期的端點＝回補歷史的前提。這是這一節最想找的東西。
                datey = any(re.search(r"date|day|ym|year|month|期別|週|week",
                                      x, re.I) for x in pars)
                say(f"       {pth}｜參數 {pars}{'  ← ★★ 吃日期！' if datey else ''}")
        # ★ 級距：規格裡若寫了欄位定義，鏈就接得起來
        ch12 = _chain(_cands(t13))
        up12 = _upper(t13)
        if len(ch12) >= 3:
            say(f"     ★ 規格裡找到連續鏈 {len(ch12)} 段（＋「以上」{len(up12)} 個）：")
            for _, _, t in ch12:
                say(f"       {t}")
            for x in up12[:3]:
                say(f"       {x}")
        else:
            say(f"     （沒有可辨識的級距鏈，最長 {len(ch12)} 段）")

    say("\n── 結論要人看過再決定 ──")
    say("上面四項全過才可以寫正式抓取。任一項不過，先解決那一項，")
    say("**不要因為「有幾萬列」就當它完整**。")
    return _write(0)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# tdcc_probe.py 的輸出。這是探針結果，不是資料。\n")
            f.write("# 端點：" + URL + "\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[tdcc] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[tdcc] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    # ⚠ 探針炸掉時，traceback 只留在 Actions log 裡——而 log 要翻好幾百行才找得到，
    #   （2026-09-09 實測：tail 900 行都還沒回到那一步）。
    #   ⇒ **把 traceback 寫進輸出檔**，它會跟著 commit 進 repo。
    #   這樣「哪一節炸的」下一趟就是既成事實，不必再去考古。
    #   ⛔ 覆蓋掉上一次成功的內容是**故意的**：這一份的語意是「這一趟看到什麼」，
    #     上一次的內容在 git 歷史裡找得到，而「看起來是完整結果、其實是上一趟的」
    #     比缺一份更貴。開頭那個 ✗ 也讓下一趟的重跑條件自動成立。
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                        # noqa: BLE001
        say("")
        say("✗ 這一趟在下面這裡炸掉了，以下是 traceback 原文（沒有整理）：")
        say(traceback.format_exc())
        _write(1)
        raise
