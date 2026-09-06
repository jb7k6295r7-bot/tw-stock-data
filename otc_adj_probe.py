#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_adj_probe.py — 上櫃的除權息與減資要從哪裡來（取代 reduce_probe.py）。

## 先更正一件事：舊的 `reduce_probe.py` 印錯了

它對每一條 TPEx 候選都印「★ 有歷史」。**那是假的。** 判斷式是

    hist = (lo < "1150000" and ...) or (lo < "2026" and lo[:4].isdigit())

`lo` 是民國七碼 `"1150909"`，拿去跟 `"2026"` 做**字串**比較，`"1" < "2"` 永遠成立，
所以任何民國日期都會被標成有歷史。**判準本身壞掉，而輸出看起來很正常。**

正確的讀法（2026-09-06 Actions 實測）：

| 候選 | 實際結果 |
|---|---|
| `bulletin/revivt` 無參數 | stat=ok、**2 列**（1150909 益得、~1150914）|
| 同上 ＋ `date=115/03/20`、`date=115/03`、`d=115/03`、`year=104`、`year=104&month=03` | **回的列與無參數時一模一樣**＝參數被無視 |
| 同上 ＋ `startDate`/`endDate` | `stat=參數錯誤` |
| 舊站 `exright/*.php` 四條 | 全部 404（TPEx 舊站已退役）|
| `bulletin/*` 另外六個名字 | 全部 404 |
| TPEx OpenAPI 四個猜的名字 | 回 HTML（那幾個 dataset 不存在）|

**結論：TPEx 官方沒有上櫃除權息／減資的歷史來源。** `bulletin/revivt` 是純前瞻公告表。

★ 教訓：**判準是「帶參數與不帶參數回的東西一不一樣」**，不是「日期看起來像不像舊的」。
  前者一行就分得出參數有沒有被吃掉，後者要靠格式假設，而假設會錯。

## 那條走得通的路：FinMind（已驗到，含上櫃）

| 測試 | 結果 |
|---|---|
| `TaiwanStockCapitalReductionReferencePrice` data_id=**3536**（上市）| 2 筆，含 **2015-03-20 前收 6.58 → 參考 13.33**，與 TWSE **一字不差** |
| 同上 data_id=**8043 蜜望實（上櫃）** | 1 筆，**2014-10-06 前收 17.4 → 參考 18.51**「現金減資」→ **上櫃有涵蓋，而且有歷史** |
| `TaiwanStockDividendResult` data_id=**8299 群聯（上櫃）** | **17 筆**，2015-06-29 起 → **算得出因子** |

★★ **除權息的參考價欄是 `after_price`，不是 `reference_price`。**
`reference_price` 在「息」的紀錄裡與 `after_price` 相同，但在「權」（股票股利）的
紀錄裡**等於前收盤**——用它算出來的因子會是 1.0，等於**股票股利完全不還原**。
這是 2026-09-06 交叉驗證抓出來的（第一版 5.41% 不符，八筆全是同一檔的「權」）。
**不是 FinMind 錯，是欄位挑錯**——而這種錯只有拿官方資料對才看得出來。

兩個 dataset 都**必須帶 `data_id`**（不帶回 400），所以是逐檔抓。

## 這支要量的三件事

1. **覆蓋率**：1,148 檔上櫃裡有幾檔查得到事件、日期範圍到哪裡
2. **成本與限流**：每發多久、第幾發開始被擋（免費額度有每小時上限）
3. **★ 可信度**：拿**上市**那一半做交叉驗證——我們手上有 TWSE 官方的
   11,729 筆除權息與 302 筆減資，**FinMind 對不對要用它們來證明**，
   不能因為它回得出東西就信。對不上就不能拿去補上櫃。

第 3 項最重要。第三方資料的可信度不是「它有沒有資料」，是「**在我們驗得動的地方它對不對**」。
"""

import argparse
import csv
import json
import os
import random
import sys
import time

import backfill as B

FINMIND = "https://api.finmindtrade.com/api/v4/data?dataset="
TPEX = "https://www.tpex.org.tw/www/zh-tw/bulletin/revivt?response=json"

DS_REDUCE = "TaiwanStockCapitalReductionReferencePrice"
DS_DIV = "TaiwanStockDividendResult"

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
META = os.path.join(_ROOT, "meta", "stocks.csv")
EXRIGHT_DIR = os.path.join(_ROOT, "universe", "exright")
REDUCE_DIR = os.path.join(_ROOT, "universe", "reduce")


def _get(url):
    raw, err = B.get(url, retries=1, timeout=45)
    if err:
        return None, err
    try:
        return json.loads(raw.decode("utf-8")), None
    except Exception:                                     # noqa: BLE001
        head = raw[:110].decode("utf-8", "replace").replace("\n", " ")
        return None, f"非 JSON（{len(raw)}B）：{head}"


def fm(ds, code, lo="2000-01-01", hi="2026-12-31"):
    """→ (list, err)。空清單與錯誤要分得開——**「查無」不是「失敗」**。"""
    d, err = _get(f"{FINMIND}{ds}&data_id={code}&start_date={lo}&end_date={hi}")
    if err:
        return None, err
    if not isinstance(d, dict):
        return None, "回的不是物件"
    if str(d.get("msg", "")).lower() not in ("success", ""):
        return None, f"msg={d.get('msg')}"
    data = d.get("data")
    return (data if isinstance(data, list) else []), None


def codes_by_market():
    out = {"twse": [], "tpex": []}
    if not os.path.exists(META):
        return out
    with open(META, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            m = r.get("market", "")
            if m in out and r.get("kind") == "stock":
                out[m].append(r["stock_id"])
    return out


def ours(dirpath, key_pre, key_ref):
    """→ {(代號, 日期): (前收, 參考)}，我方已有的官方事件。"""
    got = {}
    if not os.path.isdir(dirpath):
        return got
    for n in sorted(os.listdir(dirpath)):
        if not n.endswith(".csv"):
            continue
        with open(os.path.join(dirpath, n), encoding="utf-8") as fh:
            h = fh.readline().rstrip("\n").split(",")
            try:
                i_d, i_c = h.index("date"), h.index("stock_id")
                i_p, i_r = h.index(key_pre), h.index(key_ref)
            except ValueError:
                continue
            for ln in fh:
                q = ln.rstrip("\n").split(",")
                if len(q) > max(i_d, i_c, i_p, i_r):
                    got[(q[i_c], q[i_d])] = (q[i_p], q[i_r])
    return got


def sec_tpex(sleep):
    print("── A. TPEx 官方：確認參數到底有沒有被吃掉 ──")
    print("   判準＝**帶參數與不帶參數回的東西一不一樣**，不是日期看起來新舊。")
    base, err = _get(TPEX)
    if err:
        print(f"   ✗ 無參數的基準就拿不到：{err[:80]}")
        return
    def sig(d):
        t = (B._tables(d) or [{}])[0]
        return json.dumps(t.get("data") or [], ensure_ascii=False, sort_keys=True)
    s0 = sig(base)
    rows0 = len(json.loads(s0))
    print(f"   基準（無參數）：{rows0} 列")
    for p in ("&date=115/03/20", "&date=104/03", "&year=104&month=03"):
        d, err = _get(TPEX + p)
        time.sleep(sleep)
        if err:
            print(f"   ✗ {p}｜{err[:70]}")
            continue
        stat = str(d.get("stat", ""))
        if stat.lower() not in ("ok", "success"):
            print(f"   △ {p}｜stat={stat}（參數被拒，不是被無視）")
            continue
        same = sig(d) == s0
        print(f"   {'○' if same else '✓'} {p}｜"
              f"{'**與無參數完全相同＝參數被無視**' if same else '★ 內容不同，值得追'}")
    print("   → 若三條全是「相同」，這張表就是純前瞻公告，**上櫃沒有官方歷史**。\n")


def sec_coverage(market, codes, limit, sleep):
    print(f"── B. FinMind 覆蓋率（{market}，抽 {min(limit, len(codes))}／{len(codes)} 檔）──")
    random.seed(20260906)                    # 固定種子，換次跑結果可比
    pick = codes[:] if len(codes) <= limit else random.sample(codes, limit)
    out = {}
    for ds, label in ((DS_REDUCE, "減資"), (DS_DIV, "除權息")):
        t0, hit, rows, dates, errs = time.time(), 0, 0, [], []
        for i, c in enumerate(pick, 1):
            data, err = fm(ds, c)
            if err:
                errs.append((c, err))
                if len(errs) >= 5 and hit == 0:
                    print(f"   ★ 前 {i} 檔連續失敗且無一成功，收手。最後：{err[:70]}")
                    break
                if "429" in err or "limit" in err.lower():
                    print(f"   ★ 第 {i} 發被限流：{err[:70]}")
                    break
            elif data:
                hit += 1
                rows += len(data)
                dates += [str(r.get("date", "")) for r in data if r.get("date")]
            time.sleep(sleep)
        el = time.time() - t0
        n = max(len(pick), 1)
        print(f"   {label}｜{hit}/{n} 檔有事件、合計 {rows:,} 筆"
              f"｜失敗 {len(errs)} 發｜每發 {el / n:.2f} 秒")
        if dates:
            print(f"       日期範圍 {min(dates)} ~ {max(dates)}")
        if errs:
            print(f"       第一個錯誤：{errs[0][0]} {errs[0][1][:80]}")
        print(f"       → 全 {len(codes)} 檔約 **{el / n * len(codes) / 60:.0f} 分鐘**")
        out[ds] = hit
    print()
    return out


def sec_crosscheck(codes, limit, sleep):
    """★ 最重要的一節：拿**上市**那一半驗 FinMind 對不對。"""
    print(f"── C. 交叉驗證：FinMind vs 我方 TWSE 官方資料（抽 {limit} 檔上市）──")
    print("   第三方的可信度不是「有沒有資料」，是「**在我們驗得動的地方對不對**」。")
    mine_ex = ours(EXRIGHT_DIR, "pre_close", "ref_price")
    mine_rd = ours(REDUCE_DIR, "pre_close", "ref_price")
    print(f"   我方官方事件：除權息 {len(mine_ex):,} 筆、減資 {len(mine_rd):,} 筆")
    if not mine_ex and not mine_rd:
        print("   ✗ 我方沒有事件資料，無法驗證。先跑 feed=exright 與 feed=reduce")
        return
    random.seed(20260906)
    have = sorted({c for c, _ in mine_ex} | {c for c, _ in mine_rd})
    pick = have if len(have) <= limit else random.sample(have, limit)

    for ds, mine, label in ((DS_DIV, mine_ex, "除權息"), (DS_REDUCE, mine_rd, "減資")):
        same = diff = only_fm = only_us = 0
        bad = []
        for c in pick:
            data, err = fm(ds, c)
            time.sleep(sleep)
            if err:
                continue
            fmset = {}
            for r in (data or []):
                d = str(r.get("date", ""))
                # ★★ 2026-09-06 交叉驗證抓到的：**除權息要用 `after_price`，
                #   不是 `reference_price`。** 兩者在「息」的紀錄裡相同，
                #   但在「權」（股票股利）的紀錄裡 `reference_price` **等於前收盤**：
                #     2867 2022-02-23 before 9.38｜after **9.21**｜reference 9.38
                #     （TWSE 官方的除權息參考價是 9.21）
                #   挑錯欄位的後果是 f = 9.38/9.38 = 1.0——**股票股利完全不還原**，
                #   而且不會報錯，只是那幾檔的歷史價位悄悄少扣一次配股。
                #   第一版就是這樣跑出 5.41% 不符，八筆全是同一檔的「權」。
                pre = r.get("before_price", r.get("ClosingPriceonTheLastTradingDay"))
                ref = r.get("after_price",
                            r.get("PostReductionReferencePrice",
                                  r.get("reference_price")))
                if d and pre and ref:
                    fmset[d] = (float(pre), float(ref))
            usset = {d: v for (cc, d), v in mine.items() if cc == c}
            for d in set(fmset) | set(usset):
                if d in fmset and d in usset:
                    p1, r1 = fmset[d]
                    p2, r2 = float(usset[d][0]), float(usset[d][1])
                    if abs(p1 - p2) <= 0.011 and abs(r1 - r2) <= 0.011:
                        same += 1
                    else:
                        diff += 1
                        if len(bad) < 8:
                            bad.append(f"{c} {d} FinMind {p1}/{r1} vs 我方 {p2}/{r2}")
                elif d in fmset:
                    only_fm += 1
                else:
                    only_us += 1
        tot = same + diff
        rate = (diff / tot * 100) if tot else 0.0
        print(f"   {label}｜兩邊都有 {tot} 筆：**相符 {same}、不符 {diff}（{rate:.2f}%）**")
        print(f"       只有 FinMind 有 {only_fm} 筆（多半是 2015 以前，我方沒回補那麼早）")
        print(f"       只有我方有 {only_us} 筆 ← **這個才要緊**：FinMind 漏了事件")
        for b in bad:
            print(f"       ✗ {b}")
    print("   → 判準寫死：**不符率 > 0.5% 或「只有我方有」不是 0，就不可拿它補上櫃。**\n")


def main():
    ap = argparse.ArgumentParser(description="上櫃除權息與減資的來源")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--limit", type=int, default=120, help="每節抽幾檔")
    ap.add_argument("--only", default="", help="只跑某幾節，例如 a,c")
    a = ap.parse_args()
    B.SLEEP = a.sleep
    want = {x.strip().lower() for x in a.only.split(",") if x.strip()} or set("abc")

    cm = codes_by_market()
    print(f"[probe] 母體：上市 {len(cm['twse'])} 檔、上櫃 {len(cm['tpex'])} 檔\n")
    if "a" in want:
        sec_tpex(max(a.sleep, 1))
    if "b" in want:
        sec_coverage("上櫃 tpex", cm["tpex"], a.limit, a.sleep)
    if "c" in want:
        sec_crosscheck(cm["twse"], a.limit, a.sleep)

    print("[probe] 結論要寫成三選一：")
    print("  ① 交叉驗證過關（不符 0、只有我方有 0）→ 可用 FinMind 補上櫃，"
          "**但要在契約寫明上櫃因子來自第三方**，與上市不同來源")
    print("  ② 交叉驗證不過關 → **不可用**。有資料不等於可信")
    print("  ③ 限流擋住 → 先申請 FinMind 免費 token，或拆成多趟 job")


if __name__ == "__main__":
    sys.exit(main())
