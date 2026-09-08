#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tdcc.py — 集保戶股權分散表（大戶持股的來源）。

## 這支補的是哪個缺口

`db_status.py` 的「沒有來源」列著「集保流通股數」與「籌碼集中度的歷史序列」。
**大戶持股就是這份資料**——17 級分級裡高級距的人數與股數。

端點來自 WebSearch 結果、**不是自行生成**（`tw-data-sources` 3-4 的規矩）：

    https://opendata.tdcc.com.tw/getOD.ashx?id=1-5

2026-09-08 Actions 實測（`tdcc_probe.py`）：2.36 MB、68,867 列、4,051 檔，
每檔剛好 17 級，恆等式抽驗 200 檔 0 不符，對 `industry.csv` 涵蓋 99.9%
且分段全 100%（無截斷斷崖）。

## ⛔ 沒有歷史，只能每週累積

這支端點**不吃日期參數，只回最新一週**。資料日期是「每週最後一個營業日」，
週六 09:00 後產生。所以：

- **漏跑一週就永久少一週**，跟上櫃停牌同一種性質。排程要穩。
- 檔名用**資料自己宣告的日期**，不是今天——沙箱時鐘實測差過一天。

## 三道恆等式（來自 `tw-data-sources` 第四節第 10 項）

    ① 合計 ＝ Σ(第 1～15 級) − 差異數調整      人數與股數各驗一次
    ② 每一檔都必須剛好 17 級
    ③ 整份只能有一個資料日期（多個代表這是累計檔）

⛔ **對不上就是抓錯期別或欄位錯位，整批丟棄，不要只修那一列。**

## ⚠ 分級代碼的意義本檔不宣稱

來源只給代碼（1～17），**沒有給級距文字**。第 1～15 級是持股級距、
另有「合計」與「差異數調整」兩列——這是 `tw-data-sources` 記載的結構，
本檔照它驗，但**每一級各自對應多少股，來源端沒說，本檔也不猜**。
要用「400 張以上」這種定義，得先從官方頁面查證級距對照表再寫進文件。
"""
import argparse
import csv
import io
import os
import sys

import backfill as B
import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_DIR = os.path.join(_ROOT, "tdcc")
IND = os.path.join(_ROOT, "meta", "industry.csv")

URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
HEADER = ["date", "stock_id", "level", "people", "shares", "pct"]

CODE_KEYS = ("證券代號", "股票代號", "代號")
DATE_KEYS = ("資料日期", "日期")
LEVEL_KEYS = ("持股分級", "分級")
PEOPLE_KEYS = ("人數",)
SHARE_KEYS = ("股數", "持股股數")
PCT_KEYS = ("占集保庫存數比例%", "占集保庫存數比例", "比例")

TOTAL_LEVEL = "17"        # 合計
ADJUST_LEVEL = "16"       # 差異數調整
N_LEVELS = 17


def pick(row, keys):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def num(v):
    s = str(v or "").replace(",", "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def iso(v):
    """`20260904` → `2026-09-04`。抓不到就回空字串（**不猜**）。"""
    s = "".join(ch for ch in str(v) if ch.isdigit())
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else ""


def parse(raw):
    """→ (rows, note)。四種編碼都試，解不開就說出來。"""
    txt = None
    for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if txt is None:
        return [], "四種編碼都解不開"
    rows = list(csv.DictReader(io.StringIO(txt)))
    return rows, f"{len(rows):,} 列"


def main():
    ap = argparse.ArgumentParser(description="集保戶股權分散表（每週）")
    ap.add_argument("--run", action="store_true", help="抓最新一週並寫檔")
    ap.add_argument("--force", action="store_true", help="已存在也重寫")
    a = ap.parse_args()
    if not a.run:
        ap.print_help()
        return 1

    rl = runlog.Run("tdcc")
    raw, err = B.get(URL, retries=3, timeout=120)
    if err:
        print(f"[tdcc] 請求失敗：{err[:160]}", file=sys.stderr)
        rl.check("端點有回應", False, err[:100])
        return rl.finish()
    rows, note = parse(raw)
    print(f"[tdcc] {len(raw):,} bytes｜{note}")
    if not rows:
        rl.check("解析得到列", False, note)
        return rl.finish()

    code_k = next((k for k in rows[0] if k in CODE_KEYS), None)
    lvl_k = next((k for k in rows[0] if k in LEVEL_KEYS), None)
    shr_k = next((k for k in rows[0] if k in SHARE_KEYS), None)
    ppl_k = next((k for k in rows[0] if k in PEOPLE_KEYS), None)
    date_k = next((k for k in rows[0] if k in DATE_KEYS), None)
    pct_k = next((k for k in rows[0] if k in PCT_KEYS), None)
    missing = [n for n, k in (("代號", code_k), ("分級", lvl_k), ("股數", shr_k),
                              ("人數", ppl_k), ("日期", date_k)) if not k]
    if missing:
        # ⛔ 欄位對不上就整批不寫。**把實際表頭印出來**，不然下次還是只能猜。
        print(f"[tdcc] 欄位對不上，缺 {missing}；實際表頭 {list(rows[0])}",
              file=sys.stderr)
        rl.check("欄位對得上", False, f"缺 {missing}｜實際 {list(rows[0])}")
        return rl.finish()

    # ── ③ 整份只能有一個資料日期 ──
    dates = {pick(r, DATE_KEYS) for r in rows} - {""}
    day = iso(sorted(dates)[0]) if dates else ""
    rl.info("資料日期", f"{day}（原始 {sorted(dates)}）")
    ok_date = len(dates) == 1 and bool(day)
    rl.check("整份只有一個資料日期（單週檔）", ok_date,
             f"{len(dates)} 個：{sorted(dates)[:3]}")

    # ── ② 每一檔剛好 17 級 ──
    by = {}
    for r in rows:
        by.setdefault(str(r[code_k]).strip(), []).append(r)
    bad_lv = {c: len(v) for c, v in by.items() if len(v) != N_LEVELS}
    rl.info("證券檔數", f"{len(by):,}｜總列數 {len(rows):,}")
    rl.check(f"每一檔都剛好 {N_LEVELS} 級", not bad_lv,
             f"{len(bad_lv)} 檔不是：{list(bad_lv.items())[:5]}" if bad_lv
             else f"{len(by):,} 檔全對")

    # ── ① 恆等式：合計 ＝ Σ(1~15) − 差異數調整。人數與股數各驗一次 ──
    bad = {"人數": [], "股數": []}
    for c, rs in by.items():
        for label, key in (("人數", ppl_k), ("股數", shr_k)):
            tot = adj = None
            parts = []
            for r in rs:
                lv = str(r[lvl_k]).strip()
                v = num(r[key])
                if v is None:
                    continue
                if lv == TOTAL_LEVEL:
                    tot = v
                elif lv == ADJUST_LEVEL:
                    adj = v
                else:
                    parts.append(v)
            if tot is None or not parts:
                continue
            if tot != sum(parts) - (adj or 0):
                bad[label].append(c)
    for label in ("人數", "股數"):
        rl.check(f"恆等式（{label}）合計 ＝ Σ(1~15) − 差異數調整",
                 not bad[label],
                 f"{len(bad[label])} 檔不符：{bad[label][:5]}" if bad[label]
                 else f"{len(by):,} 檔全過")

    # ── 涵蓋率（分段看，截斷是斷崖不是均勻地少）──
    ok_seg = True          # 沒有 industry.csv 可對時視為通過（答不出來就不誤殺）
    if os.path.exists(IND):
        want = {r["stock_id"] for r in
                csv.DictReader(io.open(IND, encoding="utf-8"))}
        hit = want & set(by)
        rl.info("涵蓋", f"母體 {len(want):,} 檔命中 {len(hit):,} 檔"
                        f"（{len(hit) / len(want) * 100:.1f}%）")
        seg = []
        for lo in range(1000, 10000, 1000):
            s = {c for c in want if c.isdigit() and lo <= int(c) < lo + 1000}
            if s:
                seg.append(len(s & set(by)) / len(s) * 100)
        ok_seg = all(x > 50 for x in seg)
        rl.check("涵蓋率沒有斷崖（每個代號千位段都 > 50%）", ok_seg,
                 "最低段 " + (f"{min(seg):.0f}%" if seg else "—"))

    # ⛔ 任何一道恆等式沒過就整批不寫。對不上就是抓錯期別或欄位錯位，
    #    寫進去等於把錯的數字混進資料庫，而它看起來完全正常。
    # ⛔ 涵蓋率斷崖也算致命：**一份被截斷、卻看起來完整的週檔**混進資料庫之後
    #    分不出來——截斷是無聲的，每一列都是真的，只是少了後面。
    fatal = (bad["人數"] or bad["股數"] or bad_lv or not ok_date or not ok_seg)
    if fatal:
        print("[tdcc] ★ 驗算沒過，**整批不寫**。對不上就是抓錯期別或欄位錯位，"
              "不要只修那一列。", file=sys.stderr)
        return rl.finish()

    path = os.path.join(OUT_DIR, f"{day}.csv")
    if os.path.exists(path) and not a.force:
        rl.note(f"{day} 已存在，跳過（--force 可覆寫）")
        print(f"[tdcc] {path} 已存在，跳過")
        return rl.finish()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = []
    for r in rows:
        out.append([day, str(r[code_k]).strip(), str(r[lvl_k]).strip(),
                    pick(r, PEOPLE_KEYS), pick(r, SHARE_KEYS),
                    pick(r, PCT_KEYS) if pct_k else ""])
    out.sort(key=lambda x: (x[1], int(x[2]) if x[2].isdigit() else 99))
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(out)
    print(f"[tdcc] 寫出 {path}（{len(out):,} 列）")
    rl.info("寫出", f"{day}.csv（{len(out):,} 列）")
    have = sorted(n[:-4] for n in os.listdir(OUT_DIR) if n.endswith(".csv"))
    rl.info("已累積", f"{len(have)} 週（{have[0]} ~ {have[-1]}）")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
