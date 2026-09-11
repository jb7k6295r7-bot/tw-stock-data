#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reduce_check.py — 上櫃減資的還原因子 vs 官方參考價。**只讀 repo，不連外。**

## 為什麼要有這一支

2026-09-09 第一次把減資拿去跟官方雙向對，才發現一個沒人問過的缺口：

    上市減資：TWTAUU 對過 → 漏抓 0 筆
    **上櫃減資 217 筆：只有我方自己算的一個來源**

同一天使用者用瀏覽器把櫃買的「減資恢復交易參考價」匯出給我方（284 筆，
民國 102/09/01 ~ 115/09/21），這一支就是拿它逐筆對帳。

⛔ 這份是**人工匯出的**，新事件不會自己進來——所以本檔的檢查裡有一項
是「官方表有、我方沒有」，它會在我方漏抓時吵，也會在**匯出檔過期**時吵。
兩種原因都需要人處理，所以不分開。

## 對法（跟面額變更那條同一套，理由也一樣）

比 `pre_close` 與 `ref_price`，**在價格空間、容差半分**：
官方參考價是四捨五入到分印出來的，在比值空間用固定容差會把四捨五入誤判成不符。

## ⚠ 官方那份自己有一列對不上，這裡寫清楚免得日後被當成我方的錯

    "1070925","6109","亞元","10.50","10.63","11.65","9.57","10.65","0.00","現金減資"
    "1090925","6109","亞元","10.50","10.63","11.65","9.57","10.65","0.00","現金減資"

**六個數字一模一樣，只有民國年不同（107 vs 109）。** 我方資料的證據：
2018-09-25 那次我方有（`pre_close 10.5 → ref 10.63`，而且 09-12~09-25 之間
確實停止買賣）；2020-09-25 那天我方價格是 **14.45 → 13.95，沒有跳、沒有停牌**。
⇒ 這裡把 `1090925` 那一列列為**已知不一致**並排除，⛔ 但**不改動官方原始檔**
（原檔逐字保存在 `data/meta/sources/`）。
⚠ 這是「多筆一致要先問一致的原因是不是共同來源，再問是不是共同錯誤」的實例。
"""
import csv
import glob
import io
import os
import sys

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
REF = os.path.join(_ROOT, "meta", "otc_reduce_reference.csv")
ADJ = os.path.join(_ROOT, "adj")
IND = os.path.join(_ROOT, "meta", "industry.csv")
TOL = 0.005 + 1e-9

# ⛔ 已知官方那份自己重複的列（見檔頭）。**只排除這一筆**，
#   ⚠ 而且排除本身要被看見——所以它會出現在 runlog 的資訊列裡，不是靜靜地跳過。
KNOWN_BAD = {("6109", "2020-09-25"): "官方表把 1070925 那列重打成 1090925，"
                                     "六個數字完全相同；我方該日無跳價無停牌"}


def _load_ref():
    out = {}
    if not os.path.exists(REF):
        return out
    with io.open(REF, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                out[(r["stock_id"], r["event_date"])] = (
                    float(r["last_close"]), float(r["ref_price"]), r["reason"])
            except (ValueError, KeyError):
                continue
    return out


def _load_mine():
    out = {}
    for p in glob.glob(os.path.join(ADJ, "*.csv")):
        sid = os.path.basename(p)[:-4]
        if sid.startswith("_"):
            continue
        try:
            with io.open(p, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("event") == "reduce":
                        out[(sid, (r.get("date") or "").strip())] = r
        except OSError:
            continue
    return out


def main():
    rl = runlog.Run("reduce_check")
    ref = _load_ref()
    if not ref:
        rl.check("官方上櫃減資對照表存在", False, REF)
        return rl.finish()
    mine = _load_mine()
    mkt = {}
    if os.path.exists(IND):
        with io.open(IND, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                mkt[r["stock_id"]] = r.get("market", "")
    rl.info("來源", f"官方 {len(ref)} 筆｜我方 reduce {len(mine)} 筆")

    # ── ① 逐筆比數字
    same = []
    diff = []
    for k, (lc, rp, reason) in ref.items():
        q = mine.get(k)
        if not q:
            continue
        try:
            pre, mref = float(q["pre_close"]), float(q["ref_price"])
        except (ValueError, KeyError):
            diff.append((k, "我方數字讀不出來"))
            continue
        if abs(pre - lc) <= TOL and abs(mref - rp) <= TOL:
            same.append(k)
        else:
            diff.append((k, f"我方 {pre}/{mref}｜官方 {lc}/{rp}"))
    rl.info("逐筆比對", f"相符 {len(same)}｜不符 {len(diff)}"
                        "（比 pre_close 與 ref_price，價格空間、容差半分）")
    rl.check("官方參考價與我方因子沒有一筆不符", not diff,
             "；".join(f"{k[0]} {k[1]} {n}" for k, n in diff[:5]))

    # ── ② 官方有、我方沒有
    #   ⛔ 恢復買賣日在**今天或以後**的不算漏抓——那是預告，價格還沒發生。
    today = runlog.now_tpe().strftime("%Y-%m-%d") \
        if hasattr(runlog, "now_tpe") else ""
    if not today:
        from datetime import datetime, timedelta, timezone
        today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    # ⛔ **只比兩邊都涵蓋的區間**：官方這份從 2013-09 起，我方價格從日曆第一天起。
    #   拿更早的官方事件說我方漏抓是錯的比法（第一版就是這樣，一次噴出 8 筆假漏抓）。
    cal = os.path.join(_ROOT, "meta", "calendar_twse.csv")
    start = ""
    if os.path.exists(cal):
        with io.open(cal, encoding="utf-8") as f:
            ds = sorted((r.get("date") or "").strip()
                        for r in csv.DictReader(f) if (r.get("date") or "").strip())
            start = ds[0] if ds else ""
    rl.info("比對區間", f"{start or '（日曆讀不到）'} 起"
                       "（我方價格的第一天；更早的官方事件不算漏抓）")
    # ⛔⛔ **不可以就地換掉 `ref`**（2026-09-11 付過代價）。
    #   `same` 是上面用**完整的** `ref` 算出來的 ⇒ 把 `ref` 縮窄之後，
    #   下面 ④ 的 `ref[k][2]` 就會踩到一個已經被濾掉的鍵
    #   ⇒ `KeyError: ('6291', '2013-09-14')`，⚠ 而它炸在**最後一行**，
    #     `set -e` 連坐把同一個 step 後面的步驟全掐死（四點二 ④ 那一族）。
    #   ⇒ 窄的那一份**另外命名**，⛔ 原本那份原封不動。
    ref_win = {k: v for k, v in ref.items() if not start or k[1] >= start}
    ahead = sorted(k for k in ref_win if k not in mine and k[1] >= today)
    known = sorted(k for k in ref_win if k not in mine and k[1] < today
                   and k in KNOWN_BAD)
    miss = sorted(k for k in ref_win if k not in mine and k[1] < today
                  and k not in KNOWN_BAD)
    rl.info("官方有我方沒有", f"未來／今天 {len(ahead)} 筆（預告，不算漏抓）"
                            f"｜已知官方自己重複 {len(known)} 筆"
                            f"｜**真的沒有 {len(miss)} 筆**")
    for k in known:
        rl.info(f"  ⚠ 排除 {k[0]} {k[1]}", KNOWN_BAD[k])
    rl.check("沒有一筆官方減資是我方漏抓的", not miss,
             "；".join(f"{k[0]} {k[1]}" for k in miss[:8])
             + "｜⚠ 也可能是那份人工匯出檔過期了，兩種都要人看")

    # ── ③ 我方有、官方沒有（只看上櫃）
    # ⛔⛔ 這一邊要拿**完整的** `ref` 比，⛔ 不是 ② 用的那個窄版。
    #   ⚠ 兩個方向的「區間」不是同一個：
    #     ② 問「我方漏抓嗎」⇒ 早於**我方價格**的官方事件不算漏抓
    #     ③ 問「我方編造嗎」⇒ 官方表裡**有**就不算編造，跟我方價格從哪天開始無關
    #   ⇒ 用窄版比 ③ 會把「兩邊都有、只是早於我方日曆」那幾筆
    #     誤報成「我方編出官方沒有的減資」（自測 [1] 當場抓到）。
    # ⚠ 而另一邊要擋的是**官方表自己的起點**：早於官方表第一天的我方事件
    #   不算編造（官方那份從 2013-09 起）。
    _ref_from = min((k[1] for k in ref), default="")
    extra = sorted(k for k in mine
                   if mkt.get(k[0]) == "tpex" and k not in ref
                   and (not _ref_from or k[1] >= _ref_from))
    rl.info("我方上櫃有、官方沒有", f"{len(extra)} 筆"
                                  + (f"：{extra[:6]}" if extra else "（沒有）"))
    rl.check("我方沒有編出官方沒有的上櫃減資", not extra,
             f"{len(extra)} 筆")

    # ── ④ 減資原因字串
    rs = [k for k in same if mine[k].get("kind") == ref[k][2]]
    rl.info("減資原因字串", f"一致 {len(rs)}/{len(same)}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
