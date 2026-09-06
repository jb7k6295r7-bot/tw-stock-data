#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_history_probe.py — 月營收與財報的**歷史**要從哪裡來。

## 現況（2026-09-06 從 repo 實測，不是推測）

`data/mops/` 裡只有：`revenue/2026-07.csv`（1,975 檔）、
`fs/2026Q2_ci.csv`（1,930 檔）＋ `_basi`／`_bd`／`_ins`／`_fh`、`bs/` 同上。
**每一項都只有一期。**

原因很單純：`mops.py` 走的是 TWSE／TPEx 的 **OpenAPI**
（`t187ap05_L`、`t187ap06/07_L_*`），那些端點**沒有年度／季別參數，只給最新一期**。
所以現在的做法是「每天跑、往後累積」，**2015 以來一期都補不回來**。

代價：資料庫有 3,029 檔價格、2,661 檔法人、12,031 個還原事件，
但**基本面只有當期**。錯殺判定的 C1（獲利／毛利／財務）、
型態回測要加基本面過濾、任何「當時的財報長怎樣」的問題，全都做不了。

## 四批候選

| | 路 | 為什麼值得試 |
|---|---|---|
| A | OpenAPI 加上年度／季別參數 | 最便宜。**但要小心參數回音**——`TWT49U` 就是這樣騙過檢查的 |
| B | MOPS 本站的逐月靜態頁 | 舊路徑 `mops.twse.com.tw/nas/t21/sii/...` 實測 404，換 host 再試 |
| C | MOPS 本站的查詢表單（POST，吃年度／季別）| 官方唯一明確有歷史的路，但要 POST 且是 HTML |
| D | FinMind | **已確認有歷史**（2015 的月營收與財報都回得到），問題只在量 |

## D 的問題不是「行不行」，是「幾發」

FinMind 這兩個 dataset **必須帶 `data_id`**（不帶回 400，實測），
所以是**逐檔**抓：3,029 檔 × 2 個 dataset ≈ **6,058 發**。
免費額度有每小時上限，超過會被擋。所以這一批要量的是：

1. 連續打會不會被限流、第幾發開始被擋
2. 每發的耗時（決定要拆成幾個 Actions job）
3. 回來的欄位夠不夠用（財報是**長格式** `type`／`value`，要自己轉寬）

**不要用「能不能回一筆」當結論**——那個問題已經答完了，是「能」。

## 判準

每個候選都要回報：**HTTP 狀態／是不是我要的那一期（看回應自述，不是看我送的參數）／
列數／涵蓋幾檔**。少一項就不算驗過。
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

import backfill as B

TWSE_API = "https://openapi.twse.com.tw/v1/opendata/"
TPEX_API = "https://www.tpex.org.tw/openapi/v1/"
FINMIND = "https://api.finmindtrade.com/api/v4/data?dataset="

# ── A. OpenAPI 加期別參數（最便宜，但最可能是回音）────────────────
A_PARAMS = ["?year=104&season=1", "?年度=104&季別=1", "?queryYear=104",
            "?date=201503", "?yyy=104&season=01"]

# ── B. MOPS 逐月靜態頁：換 host 再試一次 ───────────────────────────
#   舊路徑 `mops.twse.com.tw/nas/t21/sii/t21sc03_104_7_0.html` 2026-09-06 實測 404。
#   MOPS 搬過家，`mopsov` 與 `mopsfin` 都要試。sii＝上市、otc＝上櫃。
B_HOSTS = ["https://mopsov.twse.com.tw", "https://mops.twse.com.tw",
           "https://mopsfin.twse.com.tw"]
B_PATHS = ["/nas/t21/sii/t21sc03_104_7_0.html",
           "/nas/t21/otc/t21sc03_104_7_0.html",
           "/server-java/t21sc03?step=1&年度=104&月份=7"]

# ── C. MOPS 查詢表單（POST）────────────────────────────────────────
#   官方唯一明確有歷史的路。t163sb04＝綜合損益、t163sb05＝資產負債。
C_ENDPOINTS = [
    ("t163sb04", {"encodeURIComponent": "1", "step": "1", "firstin": "1",
                  "off": "1", "isQuery": "Y", "TYPEK": "sii",
                  "year": "104", "season": "01"}),
    ("t163sb05", {"encodeURIComponent": "1", "step": "1", "firstin": "1",
                  "off": "1", "isQuery": "Y", "TYPEK": "sii",
                  "year": "104", "season": "01"}),
    ("t51sb02", {"encodeURIComponent": "1", "step": "1", "firstin": "1",
                 "TYPEK": "sii", "year": "104", "month": "07"}),
]

# ── D. FinMind：已知可用，量測用 ───────────────────────────────────
D_CODES = ["2330", "2317", "1101", "3661", "6550"]


def _get(url):
    raw, err = B.get(url, retries=1, timeout=45)
    if err:
        return None, err, 0
    try:
        return json.loads(raw.decode("utf-8")), None, len(raw)
    except Exception:                                     # noqa: BLE001
        head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
        return None, f"非 JSON（{len(raw)}B）：{head}", len(raw)


def _post(url, data, timeout=45):
    """MOPS 的查詢表單只吃 POST。**只有這裡用 urllib 直打**，
    理由是 `B.get` 沒有 POST；其餘一律走 `B.get` 以沿用限流處理。"""
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"User-Agent": "Mozilla/5.0", "Referer": url,
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.status, None
    except Exception as ex:                               # noqa: BLE001
        return b"", 0, f"{type(ex).__name__}: {ex}"


def sec_a(sleep):
    print("── A. OpenAPI 加期別參數（**要小心參數回音**）──")
    base = TWSE_API + "t187ap06_L_ci"
    d0, err, _ = _get(base)
    if err or not isinstance(d0, list) or not d0:
        print(f"   ✗ 無參數的基準也拿不到：{err}")
        return
    def sig(rows):
        r = rows[0] if isinstance(rows, list) and rows else {}
        return (str(r.get("年度", "")), str(r.get("季別", "")), len(rows))
    base_sig = sig(d0)
    print(f"   基準（無參數）：年度={base_sig[0]} 季別={base_sig[1]}｜{base_sig[2]:,} 筆")
    for p in A_PARAMS:
        d, err, _ = _get(base + p)
        if err:
            print(f"   ✗ {p}｜{err[:70]}")
        elif not isinstance(d, list) or not d:
            print(f"   △ {p}｜回空")
        else:
            s = sig(d)
            same = "**與基準相同＝參數被無視**" if s == base_sig else "★ 不一樣，值得追"
            print(f"   {'○' if s == base_sig else '✓'} {p}｜"
                  f"年度={s[0]} 季別={s[1]}｜{s[2]:,} 筆  {same}")
        time.sleep(sleep)
    print("   ※ 判準是**回來的資料自述的年度／季別**，不是它有沒有 200。\n")


def sec_b(sleep):
    print("── B. MOPS 逐月靜態頁（換 host）──")
    for h in B_HOSTS:
        for p in B_PATHS:
            raw, err = B.get(h + p, retries=1, timeout=30)
            if err:
                print(f"   ✗ {h.split('//')[1]}{p[:40]}｜{err[:60]}")
            else:
                txt = raw.decode("big5", "replace")
                n = txt.count("<tr")
                hit = "104" in txt and ("營業收入" in txt or "營收" in txt)
                print(f"   {'✓' if hit else '△'} {h.split('//')[1]}{p[:40]}｜"
                      f"{len(raw):,}B｜<tr> {n}｜含 104 年與營收字樣：{hit}")
            time.sleep(sleep)
    print()


def sec_c(sleep):
    print("── C. MOPS 查詢表單（POST，官方唯一明確有歷史的路）──")
    for name, form in C_ENDPOINTS:
        for host in ("https://mopsov.twse.com.tw/mops/web/ajax_",
                     "https://mops.twse.com.tw/mops/web/ajax_"):
            url = host + name
            raw, status, err = _post(url, form)
            if err:
                print(f"   ✗ {url.split('//')[1]}｜{err[:70]}")
                time.sleep(sleep)
                continue
            txt = raw.decode("utf-8", "replace")
            if "查詢無資料" in txt or len(raw) < 2000:
                print(f"   △ {name} @{host.split('//')[1][:12]}｜HTTP {status}｜"
                      f"{len(raw):,}B｜疑似查無資料")
            else:
                rows = txt.count("<tr")
                # ★ 要確認它回的是**我要的那一期**，不是預設的最新一期
                yr = re.findall(r"(\d{3})\s*年\s*第?\s*(\d)\s*季", txt)[:2]
                print(f"   ✓ {name} @{host.split('//')[1][:12]}｜HTTP {status}｜"
                      f"{len(raw):,}B｜<tr> {rows}｜自述期別 {yr or '抽不到'}")
                print(f"       ★ 自述期別若不是 104 年第 1 季，**就是回了最新一期**，"
                      f"不能當成歷史可用")
            time.sleep(sleep)
    print()


def sec_d(sleep):
    print("── D. FinMind：已知有歷史，這裡量的是**幾發、多久、會不會被擋** ──")
    sets = [("TaiwanStockMonthRevenue", "2015-01-01", "2026-09-06"),
            ("TaiwanStockFinancialStatements", "2015-01-01", "2026-09-06")]
    for ds, s, e in sets:
        t0, okn, rows, err1 = time.time(), 0, 0, ""
        for c in D_CODES:
            d, err, nb = _get(f"{FINMIND}{ds}&data_id={c}&start_date={s}&end_date={e}")
            if err:
                err1 = err1 or err
                continue
            data = d.get("data") if isinstance(d, dict) else None
            if isinstance(data, list) and data:
                okn += 1
                rows += len(data)
            time.sleep(sleep)
        el = time.time() - t0
        per = el / max(len(D_CODES), 1)
        print(f"   {ds}")
        print(f"       {okn}/{len(D_CODES)} 檔有資料｜合計 {rows:,} 列｜"
              f"每發約 {per:.1f} 秒（含 sleep {sleep}）")
        if err1:
            print(f"       第一個錯誤：{err1[:90]}")
        est = per * 3029 / 60
        print(f"       → 全市場 3,029 檔約 **{est:.0f} 分鐘**"
              f"（Actions 單一 job 上限 350 分，{'一趟跑得完' if est < 300 else '要拆成多趟'}）")
    print("   ※ 財報是**長格式**（date/stock_id/type/value/origin_name），"
          "要自己轉寬，欄名也與 MOPS 不同——**併進現有 `data/mops/` 之前要先對照欄位**。\n")


def main():
    ap = argparse.ArgumentParser(description="找月營收與財報的歷史來源")
    ap.add_argument("--sleep", type=float, default=2)
    ap.add_argument("--only", default="", help="只跑某幾批，例如 a,d")
    a = ap.parse_args()
    B.SLEEP = a.sleep
    want = {x.strip().lower() for x in a.only.split(",") if x.strip()} or set("abcd")
    if "a" in want:
        sec_a(a.sleep)
    if "b" in want:
        sec_b(a.sleep)
    if "c" in want:
        sec_c(a.sleep)
    if "d" in want:
        sec_d(a.sleep)
    print("[probe] 結論要寫成三選一：")
    print("  ① 官方有歷史（B 或 C 通了）→ 走官方，最乾淨")
    print("  ② 只有 FinMind → 要接受第三方依賴與逐檔 6,000 發，"
          "而且**欄位要對照**，不能直接倒進 data/mops/")
    print("  ③ 都不行 → **在契約裡寫死「基本面只有 2026-07 起」**，"
          "不要讓人以為有歷史。這也是一種結論，不是失敗。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
