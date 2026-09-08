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

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
IND = os.path.join(_ROOT, "meta", "industry.csv")
OUT = os.path.join(_ROOT, "meta", "_tdcc_probe.txt")

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


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def pick(row, keys):
    for k in keys:
        if k in row and str(row[k]).strip() != "":
            return str(row[k]).strip()
    return ""


def num(v):
    s = str(v or "").replace(",", "").strip()
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
        return (d, f"JSON {len(d):,} 筆") if isinstance(d, list) else ([], "JSON 頂層不是 list")
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
    sys.exit(main())
