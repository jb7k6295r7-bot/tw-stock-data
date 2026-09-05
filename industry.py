#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""industry.py — 全市場產業別（類股）對照表。

## 為什麼需要

選股規則有兩條直接依賴產業別：
**排除金融保險與生技醫療**、**同一類股當日推薦最多 2 檔**。
但 `data/meta/stocks.csv` 只有代號／名稱／市場／kind／first_seen／last_seen，
**沒有產業別**——那兩條規則等於沒有可查證的依據，只能靠公司名稱猜。
而規則自己寫的是「不確定就排除」，猜的結果是誤殺一堆。

## 為什麼 2026-08-29 判定 `t187ap03_L` 不可用，現在又能用

當時的結論是「抓取工具對該端點嚴重截斷（查 7 個指定代號只回傳得到 1101）」。
**那是 WebFetch 的問題，不是端點的問題**——`docs/READ_CONTRACT.md` 自己就寫了
「不要用 WebFetch 讀大 JSON，會被截斷而且**被憑空補齊**，看起來像完整的」。

2026-09-05 複測：WebFetch 讀 `t187ap03_L` 回 **50 筆**、最後一筆是 1432
（上市有一千多家）——**確認是截斷**。用 urllib 從管線讀就沒有這個問題。

**教訓：端點的可用性結論要標明「用什麼工具測的」。** 換工具就要重測，
不要讓一個工具的限制被記成端點的性質。

## ★ 只寫產業別，不寫股本

`t187ap03_L` 同時有實收資本額、已發行股數、面額——**刻意不寫進來**。
`capital.py` 已經在維護那些欄位；兩支程式維護同一個數字就會**無聲飄移**
（`docs/READ_CONTRACT.md` 第二節記過 `data/history` 與 `data/stocks` 的同一種病）。
本檔只負責產業別與上市日期（後者目前沒有別的地方有）。

## 交叉驗證

兩條獨立來源互相檢查，這是本檔最重要的部分：

1. **`t187ap03_L`** → 每一檔的產業別**代碼**（例如 `01`）
2. **`MI_INDEX?type=NN`** → 該類股當日的**實際成員名單**，且標題直接寫類股名稱
   （實測 `type=01` → 「115年09月04日 每日收盤行情(**水泥工業**)」）

驗算：**MI_INDEX 說屬於類股 NN 的每一檔，在 `t187ap03_L` 的產業別也必須是 NN。**
不符就逐筆印出來。類股名稱也由 MI_INDEX 的標題取得，不寫死對照表——
**寫死的對照表會在官方改名時安靜地錯下去。**
"""

import argparse
import json
import os
import re
import sys
import time

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
META_DIR = os.path.join(_ROOT, "meta")
OUT = os.path.join(META_DIR, "industry.csv")
HEADER = ["stock_id", "name", "market", "industry_code", "industry_name", "listed_date"]

TWSE_BASIC = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
# 上櫃：從開發環境讀 tpex.org.tw 一律 403，**只能在 Actions 上驗**。
# 這批是候選，由 --probe 淘汰。
TPEX_BASIC = [
    "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
    "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_o",
    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_basic_info",
    "https://www.tpex.org.tw/openapi/v1/company_basic_info",
]


def _mi_index(day, code):
    return ("https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
            f"?date={day.replace('-', '')}&type={code}&response=json")


def _get_json(url, retries=3):
    raw, err = B.get(url, retries=retries)
    if err:
        return None, err
    try:
        return json.loads(raw.decode("utf-8")), None
    except Exception as ex:                                   # noqa: BLE001
        head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
        return None, f"JSON {type(ex).__name__}｜{len(raw)}B｜開頭：{head}"


def fetch_basic(url):
    """→ ({代號: {name, industry, listed}}, note)。t187ap03_L 型的回應。"""
    d, err = _get_json(url)
    if err:
        return None, err
    if not isinstance(d, list):
        return None, f"不是 list，頂層是 {type(d).__name__}"
    out = {}
    for r in d:
        if not isinstance(r, dict):
            continue
        code = str(r.get("公司代號") or r.get("SecuritiesCompanyCode") or "").strip()
        if not code:
            continue
        out[code] = {
            "name": str(r.get("公司簡稱") or r.get("CompanyAbbreviation") or "").strip(),
            "industry": str(r.get("產業別") or r.get("SecuritiesIndustryCode") or "").strip(),
            "listed": str(r.get("上市日期") or r.get("上櫃日期") or "").strip(),
        }
    return out, f"{len(out)} 檔"


def fetch_sectors(day, lo=1, hi=40):
    """掃 MI_INDEX 的類股代碼 → ({代碼: 名稱}, {代碼: set(成員代號)})。

    ★ 不寫死代碼清單，逐一試到哪些回得到——官方增刪類股時不必改程式。
      類股名稱從標題取（「…每日收盤行情(水泥工業)」），**不寫死對照表**：
      寫死的表會在官方改名時安靜地錯下去。
    """
    names, members = {}, {}
    for i in range(lo, hi + 1):
        code = f"{i:02d}"
        d, err = _get_json(_mi_index(day, code), retries=1)
        time.sleep(B.SLEEP)
        if err or not isinstance(d, dict):
            continue
        if str(d.get("stat", "")).strip().lower() not in ("ok", "success"):
            continue
        # 日期核對：MI_INDEX 也可能回別天的資料
        same, said = B._same_day(d, day)
        if not same:
            print(f"  [類股 {code}] 日期不符（{said}），略過", file=sys.stderr)
            continue
        # ★★ **不可以假設資料在第一張表。**
        #   2026-09-05 實測：`MI_INDEX?type=01` 回 **9 張表，個股在第 9 張（index 8）**，
        #   前 8 張是空物件。原本寫 `tabs[0]` → 每個類股都被跳過，掃出 0 個，
        #   而且**不會報錯**（欄位對不上就 continue），只是安靜地什麼都沒有。
        #   `margin` 那次也是同一種錯（個股在第二張）。
        #   → 掃過所有表，挑「有 證券代號 欄 且 標題結尾有括號類股名」那張。
        t = f = m = None
        for cand in B._tables(d):
            cf = [str(x).strip() for x in (cand.get("fields") or [])]
            if "證券代號" not in cf:
                continue
            title = str(cand.get("title") or d.get("title") or "")
            cm = re.search(r"[(（]([^)）]+)[)）]\s*$", title.strip())
            if cm:
                t, f, m = cand, cf, cm
                break
        if t is None:
            continue
        i_code = f.index("證券代號")
        s = set()
        for r in (t.get("data") or []):
            if r and len(r) > i_code:
                c = str(r[i_code]).strip()
                if c and c[0].isdigit():
                    s.add(c)
        if not s:
            continue
        names[code] = m.group(1)
        members[code] = s
        print(f"  [類股 {code}] {m.group(1)}：{len(s)} 檔", flush=True)
    return names, members


def cmd_probe(args):
    """只測端點、不寫檔。上櫃那幾條只有在 Actions 上才驗得到。"""
    print(f"[probe] 測試日 {args.date}\n")
    print("── 上市基本資料 t187ap03_L ──")
    basic, note = fetch_basic(TWSE_BASIC)
    if basic:
        n_ind = sum(1 for v in basic.values() if v["industry"])
        print(f"   ✓ {note}｜有產業別的 {n_ind} 檔")
        for c in list(basic)[:3]:
            print(f"       {c} {basic[c]}")
    else:
        print(f"   ✗ {note}")

    print("\n── 上櫃基本資料（候選）──")
    for url in TPEX_BASIC:
        d, note = fetch_basic(url)
        short = url.replace("https://www.", "")
        if d:
            n_ind = sum(1 for v in d.values() if v["industry"])
            print(f"   ✓ {short}｜{note}｜有產業別的 {n_ind} 檔")
            for c in list(d)[:3]:
                print(f"       {c} {d[c]}")
            break
        print(f"   ✗ {short}｜{note[:100]}")
    else:
        print("   → 沒有可用候選（上櫃產業別待解）")

    print(f"\n── 類股成員（MI_INDEX，用來交叉驗證與取類股名稱）──")
    names, members = fetch_sectors(args.date, 1, args.hi)
    print(f"   共 {len(names)} 個類股、{sum(len(v) for v in members.values())} 檔次")
    return 0


def cmd_run(args):
    if args.sleep:
        B.SLEEP = args.sleep
    # ── 上市 ──
    basic, note = fetch_basic(TWSE_BASIC)
    if not basic:
        print(f"[industry] 上市基本資料抓不到：{note}", file=sys.stderr)
        return 1
    print(f"[industry] 上市基本資料 {note}")
    rows = {c: dict(v, market="twse") for c, v in basic.items()}

    # ── 上櫃 ──
    otc_ok = False
    for url in TPEX_BASIC:
        d, note = fetch_basic(url)
        if d:
            print(f"[industry] 上櫃基本資料 {note}（{url}）")
            for c, v in d.items():
                rows.setdefault(c, dict(v, market="tpex"))
            otc_ok = True
            break
    if not otc_ok:
        print("[industry] ⚠ 上櫃基本資料全部候選都失敗——**本次只有上市有產業別**。"
              "不要把上櫃的空白讀成「沒有產業別」。", file=sys.stderr)

    # ── 類股名稱與成員（交叉驗證）──
    print(f"[industry] 掃類股成員（測試日 {args.date}）")
    names, members = fetch_sectors(args.date, 1, args.hi)

    # ★ 驗算：MI_INDEX 說屬於類股 NN 的，t187ap03_L 的產業別也必須是 NN
    bad = miss = 0
    for code, mem in members.items():
        for c in mem:
            r = rows.get(c)
            if r is None:
                miss += 1
                continue
            if r["industry"] and r["industry"] != code:
                bad += 1
                if bad <= 20:
                    print(f"  ✗ {c} {r['name']}：MI_INDEX 說 {code}({names[code]})，"
                          f"基本資料說 {r['industry']}", file=sys.stderr)
    tot = sum(len(v) for v in members.values())
    print(f"[industry] 交叉驗證：{tot} 檔次｜產業別不符 {bad}｜基本資料查無 {miss}")
    if bad:
        print("[industry] ⚠ 不符不是零就要看過——**兩條來源對同一檔給了不同的類股**，"
              "不可挑一個用。", file=sys.stderr)

    # ── 寫檔 ──
    os.makedirs(META_DIR, exist_ok=True)
    n_named = 0
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(HEADER) + "\n")
        for c in sorted(rows):
            r = rows[c]
            nm = names.get(r["industry"], "")
            if nm:
                n_named += 1
            # 名稱可能含逗號，用引號包起來
            def q(v):
                v = str(v or "")
                return f'"{v}"' if "," in v else v
            f.write(",".join([c, q(r["name"]), r["market"], r["industry"],
                              q(nm), r["listed"]]) + "\n")
    print(f"[industry] 寫出 {len(rows)} 檔 → {OUT}")
    print(f"[industry] 其中 {n_named} 檔查得到類股名稱"
          f"（其餘是名稱表沒涵蓋的代碼，代碼本身仍在）")

    # 覆蓋率：meta/stocks.csv 裡的 kind=stock 有多少查得到產業別
    sp = os.path.join(META_DIR, "stocks.csv")
    if os.path.exists(sp):
        import csv as _csv
        with open(sp, encoding="utf-8") as f:
            uni = [r for r in _csv.DictReader(f) if r.get("kind") == "stock"]
        have = sum(1 for r in uni if rows.get(r["stock_id"], {}).get("industry"))
        print(f"[industry] 覆蓋率：universe 的 {len(uni)} 檔 stock 中，"
              f"{have} 檔有產業別（{have/len(uni)*100:.1f}%）")
    return 0


def main():
    ap = argparse.ArgumentParser(description="全市場產業別對照表")
    ap.add_argument("--probe", action="store_true", help="只測端點，不寫資料")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--date", default="2026-09-04", help="掃類股成員用的交易日")
    ap.add_argument("--hi", type=int, default=40, help="類股代碼掃到幾號")
    ap.add_argument("--sleep", type=float, default=3)
    a = ap.parse_args()
    if a.probe:
        return cmd_probe(a)
    if a.run:
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
