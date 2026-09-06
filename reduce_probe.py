#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reduce_probe.py — 上櫃的減資與除權息歷史來源，還沒找到。這支專門找那個。

## 上市的部分**已經解決了，不用再探**（2026-09-06）

| 來源 | 結論 |
|---|---|
| TWSE `reducation/TWTAUU` | ✓ **就是它**。吃 `startDate`/`endDate`，2015 全年回 26 列、\
2026 上半年回 2 列。**有歷史**，不是前瞻十日的公告表 |
| TWSE `change/TWTB8U` | ✗ 那是**變更股票面額**恢復買賣參考價，不同的公司行動，不要混用 |

已接成 `feeds.py` 的 `reduce` feed，跑法：`python feeds.py --run --feed reduce
--start 2015-01-01 --end <今天>`。**上市不必再探測。**

★ 那次的教訓值得記：`TWTAUU` 不在 `change/` 也不在 `exRight/`，
  而在自己的 `reducation/` 區段（是的，官方就是拼成 reducation）。
  前一輪掃 `change/TWTB[1-9]U`、`change/TWTA[S-Z]U` 掃不到它，
  **不是因為端點不存在，是因為區段名猜錯了。**

## 還沒解決的：上櫃

`data/adj/` 目前 100% 是上市。上櫃佔母體將近一半，代表**上櫃股的長期報酬率、
均線、扣抵值目前全部沒有還原**——除權息沒有、減資也沒有。

已知：TPEx `bulletin/revivt` 有回應（stat=ok），標題「減資恢復買賣參考價」，
欄位有「最後交易日之收盤價格」與「減資恢復買賣開始日參考價格」——形狀是對的，
**但它回的是未來十天**。所以問題只剩一個：**它吃不吃日期參數。**

## 判準（每個候選都要回報這四項，缺一不可）

1. `stat` 與標題
2. **完整欄位**
3. 列數
4. **日期欄的最小與最大值** ← 最重要，它直接回答「有沒有歷史」

★ 只有第 4 項能分辨「端點可用」與「端點有我要的歷史」。
  前三項全對但日期全是未來十天，這條就是不能用——那正是 `bulletin/revivt` 的現況。

## ⚠ TPEx 只有在 Actions 上驗得到

開發環境與 WebFetch 打 TPEx 一律 403（2026-09-06 再次確認）。
**「TPEx 這條不通」這種結論，只有 Actions 上跑出來的才算數。**
"""

import argparse
import json
import sys
import time

import backfill as B

TPEX = "https://www.tpex.org.tw/www/zh-tw/"
TPEX_OLD = "https://www.tpex.org.tw/web/stock/"
OPENAPI = "https://www.tpex.org.tw/openapi/v1/"

DATE_HINT = ("日期", "date", "Date", "Date")

# ── 候選 A：新站 bulletin/revivt ＋ 各種日期參數寫法 ──────────────────
#   已知它本身有回應。**這一批在測的是「它吃不吃日期」**，不是它存不存在。
#   TPEx 新站的日期慣例是 `date=115/03/01`（民國、斜線），但區間型參數
#   在別的 TPEx 端點看過 `startDate`/`endDate` 與 `d`，三種都試。
REVIVT_PARAMS = [
    "",                                   # 對照組：不帶參數（已知回未來十天）
    "&date=115/03/20",
    "&date=115/03",
    "&d=115/03",
    "&startDate=104/01/01&endDate=104/12/31",
    "&startDate=20150101&endDate=20151231",
    "&year=104",
    "&year=104&month=03",
]

# ── 候選 B：舊站 .php（新站上線後多半還活著，且舊站本來就是逐月查詢）──
#   舊站的減資恢復買賣在 `exright/revivt/revivt_result.php`，
#   除權息在 `exright/preAnnouncement/`。**舊站吃 `d=民國年/月`。**
OLD_PATHS = [
    "exright/revivt/revivt_result.php?l=zh-tw&d=104/03",
    "exright/revivt/revivt_result.php?l=zh-tw&d=115/09",
    "exright/preAnnouncement/prepost_result.php?l=zh-tw&d=104/03",
    "exright/exright_result.php?l=zh-tw&d=104/03",
]

# ── 候選 C：新站 bulletin 區段的其他表（找上櫃除權息）──────────────────
BULLETIN_PATHS = [
    "bulletin/exright", "bulletin/exRight", "bulletin/preExright",
    "bulletin/prepost", "bulletin/exDividend", "bulletin/revivtHist",
]

# ── 候選 D：TPEx OpenAPI（有些表只在這裡，而且不吃日期＝只有當期）──────
OPENAPI_PATHS = [
    "tpex_capital_reduction", "tpex_revivt", "tpex_exright_result",
    "tpex_ex_dividend",
]


def _get(url):
    raw, err = B.get(url, retries=1, timeout=45)
    if err:
        return None, err
    try:
        return json.loads(raw.decode("utf-8")), None
    except Exception:                                     # noqa: BLE001
        head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
        return None, f"非 JSON（{len(raw)}B）：{head}"


def _dates(fields, rows):
    """→ (欄名, 最小, 最大)。**這一項回答「有沒有歷史」，是本次探測的重點。**"""
    for i, f in enumerate(fields):
        if any(h in str(f) for h in DATE_HINT):
            vals = [str(r[i]).strip() for r in rows if len(r) > i and str(r[i]).strip()]
            if vals:
                return str(f), min(vals), max(vals)
    return "", "", ""


def _show(label, d):
    """把一個回應攤開來印。回 True 代表這條至少有欄位可看。"""
    if isinstance(d, list):                     # OpenAPI 是純陣列
        if not d:
            print(f"   △ {label}｜空陣列")
            return False
        keys = list(d[0]) if isinstance(d[0], dict) else []
        dv = [str(r.get(k, "")) for r in d for k in keys
              if any(h in k for h in DATE_HINT)]
        print(f"   ✓ {label}｜{len(d):,} 筆｜欄位={keys}")
        if dv:
            print(f"       日期範圍 {min(dv)} ~ {max(dv)}")
        print(f"       首筆={d[0]}")
        return True

    if not isinstance(d, dict):
        print(f"   ✗ {label}｜回的不是 dict 也不是 list：{type(d).__name__}")
        return False

    stat = str(d.get("stat", "")).strip()
    tabs = B._tables(d)
    if not tabs:
        print(f"   △ {label}｜stat={stat or '(無)'}｜沒有 fields/data，"
              f"top-level keys={sorted(d)[:12]}")
        return False
    seen = False
    for t in tabs:
        f = [str(x) for x in (t.get("fields") or [])]
        rows = t.get("data") or []
        if not f:
            continue
        seen = True
        dk, lo, hi = _dates(f, rows)
        print(f"   ✓ {label}｜stat={stat}｜{t.get('title') or d.get('title') or ''}")
        print(f"       {len(rows)} 列｜欄位={f}")
        if dk:
            # ★ 判斷「是不是只有未來十天」：民國年 <= 114 或西元 <= 2025 就是有歷史。
            hist = (lo < "1150000" and lo[:3].isdigit()) or (lo < "2026" and lo[:4].isdigit())
            print(f"       日期欄「{dk}」範圍 {lo} ~ {hi}"
                  f"{'  ← ★ 有歷史' if hist else '  ← 只有近期／未來，不能用'}")
        else:
            print("       ⚠ 找不到日期欄——**無法判斷有沒有歷史**，不要當成可用")
        if rows:
            print(f"       首列={rows[0]}")
    return seen


def main():
    ap = argparse.ArgumentParser(
        description="找上櫃的減資／除權息歷史來源（上市已解決，見檔頭）")
    ap.add_argument("--sleep", type=float, default=1)
    a = ap.parse_args()
    B.SLEEP = a.sleep
    hit = 0

    print("── A. 新站 bulletin/revivt：它吃不吃日期參數 ──")
    print("   （不帶參數那條是對照組，已知回未來十天。**要看的是有沒有哪條回到過去。**）")
    for p in REVIVT_PARAMS:
        url = f"{TPEX}bulletin/revivt?response=json{p}"
        d, err = _get(url)
        label = "revivt" + (p or "（無參數）")
        if err:
            print(f"   ✗ {label}｜{err[:90]}")
        elif _show(label, d):
            hit += 1
        time.sleep(a.sleep)
    print()

    print("── B. 舊站 .php（舊站本來就是逐月查詢，最可能有歷史）──")
    for p in OLD_PATHS:
        d, err = _get(TPEX_OLD + p)
        if err:
            print(f"   ✗ {p.split('?')[0]}｜{err[:90]}")
        elif _show(p, d):
            hit += 1
        time.sleep(a.sleep)
    print()

    print("── C. 新站 bulletin 區段的其他表（找上櫃除權息）──")
    for p in BULLETIN_PATHS:
        d, err = _get(f"{TPEX}{p}?response=json&date=115/09/01")
        if err:
            print(f"   ✗ {p}｜{err[:90]}")
        elif _show(p, d):
            hit += 1
        time.sleep(a.sleep)
    print()

    print("── D. TPEx OpenAPI ──")
    for p in OPENAPI_PATHS:
        d, err = _get(OPENAPI + p)
        if err:
            print(f"   ✗ openapi/{p}｜{err[:90]}")
        elif _show(f"openapi/{p}", d):
            hit += 1
        time.sleep(a.sleep)

    print(f"\n[probe] 有回應的候選：{hit} 條")
    print("[probe] ★ 重點不是「有沒有回應」，是**日期欄的最小值**——"
          "那決定 2015 年以來的上櫃減資能不能補回來，還是只能從現在累積。")
    print("[probe] 若全部只有未來十天：那就**在契約裡寫死「上櫃只能從啟用日往後累積」**，"
          "不要讓人以為 data/adj/ 是完整的。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
