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
import runlog

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



# ★ `MI_INDEX` 拿不到名稱的代碼，另外從**官方 ISIN 證券編碼查詢**取得。
#   來源網址由使用者 2026-09-09 提供，探針在 `tpex_probe.py` 第 11 節，
#   三項判準全過才落地（`_tpex_probe.txt` 有實測輸出）：
#     ① 32 與 33 回**不同**的清單（交集 0）⇒ 參數確實生效
#     ② 我方標成 32 的 34 檔、33 的 7 檔 **全部**落在對應清單裡（34/34、7/7）
#     ③ 該頁「產業別」欄的相異值**各只有一種** ⇒ 那就是代碼的名稱
#   ⛔ 只在 `MI_INDEX` 沒有名稱時才用，**永遠不覆蓋官方指數表的用字**——
#     兩邊用字可能不同（櫃買把 17 叫「金融業」、上市表寫「金融保險」），
#     而「代碼對、名稱錯」是安靜的錯。
EXTRA_NAMES = {
    "32": "文化創意業",
    "33": "農業科技業",
}

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

    # ★★ 類股是**有層級的**，不是互斥的分類。2026-09-04 實測：
    #     13 電子工業 458 檔 ＝ 24(96)＋25(64)＋26(68)＋27(46)＋28(104)＋29(23)＋30(11)＋31(46)
    #     07 化學生技醫療 88 檔 ＝ 21 化學工業(28)＋22 生技醫療業(60)
    #   所以 1,655 檔次 > 1,094 檔——同一檔會同時出現在母類股與子類股。
    #
    #   母子關係**用集合包含關係推出來，不寫死**：官方增刪類股時不必改程式。
    parents = {}
    for a, ma in members.items():
        kids = [b for b, mb in members.items() if b != a and mb and mb <= ma]
        if kids and sum(len(members[b]) for b in kids) == len(ma):
            parents[a] = sorted(kids)
    for a, kids in parents.items():
        print(f"[industry] 母類股 {a} {names[a]}（{len(members[a])} 檔）"
              f"＝ {' ＋ '.join(f'{k} {names[k]}({len(members[k])})' for k in kids)}")

    # 驗算：基本資料給的產業別，必須是「MI_INDEX 說這檔待過的類股」之一。
    # ★ 不能寫成「必須等於 NN」——那會把母類股的成員全部判成不符（實測會多出 546 筆假警報）。
    where = {}
    for code, mem in members.items():
        for c in mem:
            where.setdefault(c, set()).add(code)
    bad = miss = 0
    for c, codes in where.items():
        r = rows.get(c)
        if r is None:
            miss += 1
            continue
        if r["industry"] and r["industry"] not in codes:
            bad += 1
            if bad <= 20:
                print(f"  ✗ {c} {r['name']}：MI_INDEX 說它在 "
                      f"{sorted(codes)}，基本資料說 {r['industry']}", file=sys.stderr)
    print(f"[industry] 交叉驗證：{len(where)} 檔（{sum(len(v) for v in members.values())} 檔次）"
          f"｜產業別對不上 {bad}｜基本資料查無 {miss}")
    if bad:
        print("[industry] ⚠ 對不上不是零就要看過——**兩條來源對同一檔給了不同的類股**，"
              "不可挑一個用。", file=sys.stderr)

    # 類股對照表另存一份，含母子關係
    with open(os.path.join(META_DIR, "sectors.csv"), "w", encoding="utf-8",
              newline="") as f:
        f.write("code,name,members,is_parent,children\n")
        for code in sorted(names):
            kids = parents.get(code, [])
            f.write(f"{code},{names[code]},{len(members[code])},"
                    f"{'Y' if kids else ''},{'|'.join(kids)}\n")
    print(f"[industry] 類股對照表 → {os.path.join(META_DIR, 'sectors.csv')}"
          f"（{len(names)} 個，其中 {len(parents)} 個是母類股）")

    # ── 寫檔 ──
    os.makedirs(META_DIR, exist_ok=True)
    n_named = 0
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(HEADER) + "\n")
        for c in sorted(rows):
            r = rows[c]
            # ⚠⚠ `names` **只有一份**，來自 TWSE `MI_INDEX?type=NN` 的類股標題，
            #    也就是**上市**那張表。這裡不分市場地套在每一列上
            #    ⇒ **上櫃的 `industry_name` 是拿代碼去查上市類股表填的**，
            #      不是上櫃來源自己給的名稱。
            #    2026-09-09 實測佐證：兩市場都有的 26 個代碼，名稱**逐字相同**（26/26）；
            #    而唯二沒有名稱的 tpex 32、33，正好是**上市沒有的兩個代碼**。
            #    另外櫃買官方 `mopsfin_t187ap05_OA` 把代碼 17 叫「金融業」，
            #    本庫（借自上市）寫的是「金融保險」——**用字確實不同**。
            #    ⛔ 這代表一個沒有被驗證過的假設：**兩個市場的代碼含意相同**。
            #      若哪天不同，每一列上櫃的名稱都會**安靜地錯**（代碼對、名稱錯）。
            #      `tpex_probe.py` 第 7 節的「分群一致性」就是在量這件事。
            nm = names.get(r["industry"], "") or EXTRA_NAMES.get(r["industry"], "")
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
        cover = have / len(uni) * 100 if uni else 0.0
    else:
        cover = None

    # ★ 寫進 data/meta/_last_run.md。這一支不是每天跑（約每月一次），
    #   區塊上的時間戳就是「產業別多久沒更新了」的答案——
    #   新上市的公司在更新之前查不到類股，而類股集中度是選股的硬條件。
    rl = runlog.Run("industry")
    rl.info("對照表", f"{len(rows)} 檔（{n_named} 檔查得到類股名稱）")
    rl.info("類股", f"{len(names)} 個，其中 {len(parents)} 個是母類股")
    if cover is not None:
        rl.info("覆蓋率", f"universe 的 {len(uni)} 檔 stock 中 {have} 檔有產業別"
                          f"（{cover:.1f}%）")
    # ⛔ 對不上不是零就要看過——兩條來源對同一檔給了不同的類股，不可挑一個用。
    rl.check("兩條來源的產業別沒有互相矛盾", bad == 0, f"對不上 {bad} 檔")
    # ⚠ 只驗「有沒有整批掉光」，不設高門檻：DR、興櫃與名稱表沒涵蓋的代碼
    #   本來就查不到，訂太高會天天誤殺。
    if cover is not None:
        rl.check("覆蓋率沒有整批掉光（> 80%）", cover > 80, f"{cover:.1f}%")
    return rl.finish()


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
