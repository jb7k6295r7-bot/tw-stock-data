#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_exright_history.py — 上櫃除權息的**歷史官方來源**（櫃買公告區「除權除息計算結果表」）。

## 這一支推翻了我自己寫過三次的一句話

我對三個地方寫過「上櫃除權息的**歷史**官方來源：仍然沒有」，依據是
`tpex_exright_daily` 只給當日、`hist.tpex` 查完只有興櫃 2002~2006。

⛔ **那句話是錯的。** 市場情報分析線 2026-09-10 09:41 在櫃買公告區找到：

    POST https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ
    body: startDate=2015/01/01&endDate=2026/09/09&response=json
    ⭐ **一次請求回完十一年半，10,232 筆**（日期選擇器下限 20080102）

⚠ 教訓跟今晚別的幾次同一族：**「我查過的那幾條端點沒有」不等於「官方沒有」。**
他們是照著櫃買的**全站選單**（485 條）找的，我是照著我想得到的路徑猜的。

## ⛔ 三個陷阱（照抄，不要「改良」）

    ① **GET 的 startDate／endDate 會被忽略**，靜靜回「今天～明天」⇒ **必須 POST**
    ② **日期一定要帶斜線**：`2015/01/01` 或 `104/01/01` 都行；
       `20150101` 會被忽略，一樣**靜靜回今天**
    ③ 名稱欄右側補空白 ⇒ 要 trim

⭐ ①②都是「回應合法、內容是別的東西」——今晚第 N 個同形狀。
⇒ 所以本支**一定要驗回應涵蓋的日期範圍**，對不上就整批拒收。

## ⛔⛔ 它**不是**上櫃 adj 的完整來源——照它重建會**刪掉減資因子**

市場情報分析線 2026-09-10 09:55 **更正了自己 09:41 那封**：
那封寫「定義與我方 `data/adj` 完全一致，可以直接當回補來源」，
⛔ **那句話太強**——他只做了單向比對（官方有的、我方有沒有），沒做反方向。

補做之後（59 檔上櫃普通股、我方視窗內 501 筆 adj 列）：

    官方 exDailyQ **沒有**的 22 筆
      event=reduce（減資）17 筆 ── 彌補虧損 11、現金減資 6
      kind=息 5 筆 ── 全部是 1752 南光 2022~2026

① **減資根本不在這張表裡**：它是「除權除息計算結果表」，**減資不是除權息**。
   ⇒ 拿它當完整來源重建，那 17 筆減資因子會被刪掉，**那幾檔的還原價整段錯**。
② 1752 南光那 5 筆不是缺口，是**它轉上市了**——`exDailyQ` 只涵蓋
   「該檔還在上櫃期間」的除權息，之後要走 TWSE `TWT49U`。
   （跟我方那 27 檔轉上市是同一件事的另一面。）

⭐ **正確的說法**：

    上櫃 adj ＝ exDailyQ（**上櫃期間**除權息）
              ＋ 減資來源（sources/reduce_source.md）
              ＋ TWT49U（該檔**轉上市之後**）

⚠ 乙級 5（ETF 配息 2,966 筆）不受這個更正影響——ETF 沒有減資、也沒有轉上市。

## ⭐ 而這正是「不順手接成寫入者」救到的一次

本支從第一版就只寫判準檔、不碰 `data/universe/otcexright/`，
理由是「換供料是**換維護者**的決定，不是順手加一行」。
⇒ 09:41 到 09:55 之間如果我把它接成寫入者並跑一次全量重建，
  **17 筆減資因子就沒了**，而且是靜默的（檔案在、筆數還變多）。

## 這一支做什麼／不做什麼

1. 抓全期，寫 `data/meta/otc_exright_history.csv`（**判準檔**）
2. `rl.info`：官方有、我方 `data/universe/otcexright/` 沒有 ⇒ 報筆數與分年
3. ⛔ **不寫 `data/universe/otcexright/`**——那個目錄的唯一寫入者是 `otc_adj.py`。
   要不要把供料換成官方端點是「**換維護者**」的決定，不是順手加一行；
   而這一支的產出正好就是做那個決定所需要的證據（全期規模，不是抽 20 檔）。
"""
import argparse
import bisect
import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

import lowwater
import runlog
# ⛔ 用**同一支** classify_gaps 與 adj_rows，不再抄一份（CLAUDE.md 第四點五）
from otc_reduce_history import adj_rows as _adj_rows, classify_gaps as _classify_gaps
from twparse import (pick_field as _pick_field, post_form as _post_form,
                     roc_iso as _roc_iso)

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "otc_exright_history.csv")
LOW = os.path.join(_ROOT, "meta", "_otc_exright_adjgap_low.txt")
OURS = os.path.join(_ROOT, "universe", "otcexright")

URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ"
# ⭐ 2026-09-10 換供料時補 `value`（官方「權值+息值」）：
#   ⚠ `adjust.py` 靠**負的權值**認定「參考價高於前收盤」那一類**合法**事件
#     （現金增資認股價高於市價，上市那邊有 9 筆）。
#   ⛔ 沒有這一欄的話，那一類會被丟掉——而 FinMind 也沒有這一欄，
#     ⇒ ⭐ **換成官方之後才第一次拿得到**，這是換源附帶的實質好處。
HEADER = ["date", "stock_id", "name", "pre_close", "ref_price", "kind",
          "value", "asof"]


# ⛔ 第九／第十份：`_post` 也收進 `twparse.py`。
_post = _post_form



# ⛔ `_iso` 與 `_pick` 原本在這兩支各有一份（逐字相同）——同一族的第七、第八份。
#   2026-09-10 收進 `twparse.py`，⭐ 而且順便把日期格式做寬並測它：
#   `bulletin/revivt` 那天回了 283 列、我方**一列都認不出來**。
_iso = _roc_iso
_pick = _pick_field


def parse(payload, want_from, want_to):
    """→ (rows, note)。⛔ 回應涵蓋的日期範圍對不上就整批拒收。"""
    tabs = payload.get("tables") if isinstance(payload, dict) else None
    if not tabs:
        tabs = [payload] if isinstance(payload, dict) and payload.get("data") else []
    if not tabs:
        return [], f"回應裡沒有表（鍵={list(payload)[:8] if isinstance(payload, dict) else type(payload).__name__}）"
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    data = t.get("data") or []
    if not data:
        return [], "回了 0 列 ⛔ 當失敗，不是「這十一年沒有除權息」"
    i_d = _pick(fields, "除權息日期", "日期")
    i_c = _pick(fields, "股票代號", "證券代號", "代號")
    i_n = _pick(fields, "股票名稱", "名稱")
    i_p = _pick(fields, "除權息前收盤價", "前收盤")
    i_r = _pick(fields, "除權息參考價", "參考價")
    # ⛔⛔ 2026-09-10：這一行原本寫 `_pick(fields, "權息值", "類別", "除權息")`，
    #   而 `_pick` 是**包含**比對、且**依欄位順序**取第一個命中的
    #   ⇒ `"除權息"` 命中的是**第 0 欄「除權息日期」** ⇒ `kind` 存進去的是**日期**。
    #   ⚠ 實測後果：`otc_exright_history.csv` 的 `kind` 欄 **13,105 列全是民國日期**
    #     （`97/01/10` 這種），而檔案格式完全正常、沒有任何錯誤訊息。
    #   ⭐ 這正是 `_pick` docstring 自己警告的那件事（「關鍵字要夠長」），
    #     ⛔ 只是那句話寫的是「太短會撞上別的欄」，
    #       ⚠ 這裡是**太短撞上了自己那一族的另一欄**——同一個坑的另一面。
    #   ⇒ 實測欄名是 `權/息`（第 8 欄），拿它比對；⛔ 拿掉 `"除權息"` 這個關鍵字。
    i_k = _pick(fields, "權/息", "類別")
    # ⚠ 逐字比對「權值+息值」，⛔ 不可以只寫「權值」——那會先命中第 5 欄「權值」。
    #   （跟 `kind` 那個坑同一族：`_pick` 是包含比對、依欄位順序取第一個命中。）
    i_v = _pick(fields, "權值+息值")
    miss = [n for n, i in (("日期", i_d), ("代號", i_c), ("前收盤", i_p),
                           ("參考價", i_r)) if i is None]
    if miss:
        return [], f"欄位對不上，缺 {miss}：{fields}"
    rows, bad = [], 0
    for r in data:
        if not isinstance(r, list) or len(r) <= max(i_d, i_c, i_p, i_r):
            bad += 1
            continue
        dt = _iso(r[i_d])
        code = str(r[i_c]).strip()
        if not dt or not code:
            bad += 1
            continue
        rows.append([dt, code,
                     str(r[i_n]).strip() if i_n is not None else "",
                     str(r[i_p]).replace(",", "").strip(),
                     str(r[i_r]).replace(",", "").strip(),
                     str(r[i_k]).strip() if i_k is not None else "",
                     (str(r[i_v]).replace(",", "").strip()
                      if i_v is not None and len(r) > i_v else "")])
    if not rows:
        return [], f"一列都認不出來（bad={bad}）：{fields}"
    ds = sorted(r[0] for r in rows)
    # ⛔⛔ 這一段是本支最重要的守門：GET、或日期不帶斜線，
    #   都會讓端點**靜靜回「今天～明天」** ⇒ 拿到 3 筆、看起來像成功。
    span = (ds[-1], ds[0])
    if ds[0] > want_from[:10] and ds[0] >= (datetime.now(TPE) - timedelta(days=7)
                                            ).strftime("%Y-%m-%d"):
        return [], (f"⛔ 回的只有最近的資料（{ds[0]} ~ {ds[-1]}，{len(rows)} 筆），"
                    f"我要的是 {want_from} 起"
                    "　⚠ 這就是『GET 或日期不帶斜線 ⇒ 靜靜回今天』那個陷阱")
    return rows, (f"{len(data)} 列｜認得出 {len(rows)}"
                  + (f"｜⚠ 認不出 {bad}" if bad else "")
                  + f"｜涵蓋 {ds[0]} ~ {ds[-1]}｜欄位 {fields}")


def ours_events():
    """→ {(代號, 日期)}，我方 `data/universe/otcexright/` 已經有的。"""
    out = set()
    if not os.path.isdir(OURS):
        return out
    for n in sorted(os.listdir(OURS)):
        if not n.endswith(".csv"):
            continue
        try:
            with io.open(os.path.join(OURS, n), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("stock_id") and r.get("date"):
                        out.add((r["stock_id"], r["date"]))
        except OSError:
            pass
    return out


def _transfer_out():
    """→ `{代號: 從上櫃轉出的日子}`（`delisted.csv` 裡 `market=tpex` 的**最後一筆**）。

    ⚠ 取最後一筆的理由：一個代號可能有多列（轉板一筆＋真下市一筆）
    ——2026-09-16 全庫掃過，436 列／429 檔裡有 7 檔是多列的。
    ⛔ 而這張表的上櫃那一半**不完整**（`delist_probe` 檔頭寫著 265 筆全是上市）
    ⇒ 查不到**不代表**它沒轉板 ⇒ 呼叫端要有第二條路（`_market_on`）。
    """
    p = os.path.join(_ROOT, "meta", "delisted.csv")
    out = {}
    if not os.path.isfile(p):
        return out
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("market") or "") != "tpex":
                continue
            sid, d = (r.get("stock_id") or "").strip(), (r.get("delist_date") or "").strip()
            if sid and d and d > out.get(sid, ""):
                out[sid] = d
    return out


def _market_on(code, date, days, ahead=5):
    """事件當天（或其後最多 `ahead` 個交易日）我方**日檔**記的市場。⛔ 查不到回 None。

    ⭐ 它是 `_transfer_out()` 的**第二條路**：`delisted.csv` 的上櫃那一半不完整，
    ⚠ 而日檔逐日記著每一檔掛在哪個市場——那是完全獨立的一份證據。
    ⛔ 往後找幾天的理由：除權息日**當天**該檔可能無成交而不在日檔裡。
    """
    i = bisect.bisect_left(days, date)
    for d in days[i:i + ahead]:
        fp = os.path.join(_ROOT, "universe", "daily", f"{d}.csv")
        try:
            with io.open(fp, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("stock_id") == code:
                        return r.get("market")
        except OSError:
            continue
    return None


def ours_only_verdict(only, out_day, days):
    """「我方有、官方沒有」那一批各是什麼 → `(轉板後, ⛔ 轉板前, 日檔說是上市, 仍未判定)`。

    ## ⛔ 為什麼要有這一段（三點①）

    2026-09-16 之前這一支**只比一個方向**（官方有、我方沒有 189 筆），
    ⚠ 而反方向是 **246 筆／26 檔**，⛔ 報表上一個字都沒有。
    ⚠ 而三點①那條的原始事故就發生在這一族：
    「只比一個方向 ⇒ 宣告某端點可當完整來源；補比反方向才發現它少 17 筆減資。」

    ⭐ 而 246 筆量完的結論是**官方一筆都沒漏**：

    ```
    223 筆  事件日在該檔**轉出上櫃之後**（`delisted.csv` 的 tpex 那一列）
     23 筆  該檔查不到 tpex 那一列（上櫃下市清單我方不完整）
            ⇒ 改問我方**日檔**：事件當天它掛哪個市場 ⇒ **23／23 都是 twse**
      0 筆  事件日落在轉板**之前** ← ⭐ 只有這一格才代表官方漏了
    ```

    ⇒ ⭐ 所以判準是**第二格 == 0**，⛔ 不是「兩邊筆數要一樣」
    （那永遠不會一樣：我方那個目錄裝的是 FinMind 給的，含轉板之後的上市事件）。
    """
    after = before = via_day = unknown = 0
    bad = []
    for code, date in sorted(only):
        t = out_day.get(code)
        if t:
            if date > t:
                after += 1
            else:
                before += 1
                bad.append((code, date, f"事件 {date} ≤ 轉出上櫃 {t}"))
            continue
        m = _market_on(code, date, days)
        if m == "twse":
            via_day += 1
        elif m == "tpex":
            before += 1
            bad.append((code, date, "日檔說事件當天它還在上櫃"))
        else:
            unknown += 1
    return after, before, via_day, unknown, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2008/01/01")
    ap.add_argument("--end", default="")
    ap.add_argument("--json", help="離線用：讀一個檔當回應")
    # ═══════════════════════════════════════════════════════════════
    # ⭐⭐ 兩半場可以分開跑（市場情報分析線 0020 §三裁的那件事）
    #
    # 這一支做兩件事：**抓官方判準檔** ＋ **逐筆掃我方 `data/adj/` 缺哪些**。
    # ⛔ 而在 `daily.yml` 裡它排在 `otc_adj.py --official` **之前**
    #   ⇒ 掃的是**還沒補之前**的 `data/adj/` ⇒ ⭐ 那一塊**每天都紅**，
    #   ⚠ 即使這一趟補的正好就是它報的那幾筆（feeds.yml 的註解⑥實測過）。
    #
    # ⇒ ⭐ 而「天天紅的閘門會被學會忽略」是本 repo 付過代價的（四點五）。
    #   ⇒ ⛔ 而處置**不是**把閘門放寬（那會讓它**永遠不紅**），
    #     ⭐ 是把**順序**改成「先抓 → 再補 → 才掃」。
    #
    # ⚠ 而兩半場的 runlog 區塊名字**不同**，理由是實際的：
    #   同名的區塊會互相覆蓋 ⇒ ⛔ 先跑的那一半就看不見了。
    #   ⭐ 而**掃描那一半留著原名**（`otc_exright_history`），
    #   因為別的線與歷史紀錄跟的是那一個名字。
    ap.add_argument("--no-scan", action="store_true",
                    help="只抓官方判準檔，⛔ 不掃缺口（daily 的第一半）")
    ap.add_argument("--scan-only", action="store_true",
                    help="不連外，讀回已經抓下來的判準檔再掃（daily 的第二半）")
    a = ap.parse_args()
    if a.no_scan and a.scan_only:
        raise SystemExit("⛔ `--no-scan` 與 `--scan-only` 不可以同時給")

    rl = runlog.Run("otc_exright_history:fetch" if a.no_scan
                    else "otc_exright_history")
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    end = a.end or today.replace("-", "/")
    rl.info("端點", f"POST {URL}｜{a.start} ~ {end}"
                    "　⛔ 一定要 POST、日期一定要帶斜線（兩者都會靜靜回今天）")

    if a.scan_only:
        # ⭐ 不連外：讀回第一半場剛寫下的那一份。
        #   ⛔ 而「讀不到」要**大聲失敗**，⚠ 不是當成 0 筆往下跑
        #   ——四點六那一條：讀不到判準檔的表現是**空值**，不是錯誤。
        if not os.path.exists(OUT):
            rl.check("`--scan-only` 要讀的判準檔在不在", False,
                     f"{OUT} 不在 ⇒ ⛔ 這一半什麼都沒掃到，"
                     "⚠ 請先跑一趟 `--no-scan`")
            return rl.finish()
        with io.open(OUT, encoding="utf-8") as f:
            rd = list(csv.reader(f))
        rows = [r[:len(HEADER) - 1] for r in rd[1:] if r]
        rl.info("判準檔（`--scan-only` 讀回來的）",
                f"data/meta/otc_exright_history.csv｜{len(rows):,} 筆"
                "　⛔ 這一半沒有連外")
        rl.check("判準檔讀回來不是空的", bool(rows), f"{len(rows)} 筆")
        if not rows:
            return rl.finish()
    elif a.json:
        raw, err = io.open(a.json, "rb").read(), None
    else:
        raw, err = _post(URL, {"startDate": a.start, "endDate": end,
                               "response": "json"})
    if not a.scan_only:
        if err or not raw:
            rl.check("抓得到 exDailyQ", False, f"{str(err)[:100]}"
                     "｜⛔ 抓不到不等於沒有歷史（本機對 tpex 一律 403，要在 Actions 上跑）")
            return rl.finish()
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
        except ValueError as ex:                                 # noqa: BLE001
            head = raw[:80].decode("utf-8", "replace").replace("\n", " ")
            rl.check("回應是 JSON", False,
                     f"{str(ex)[:50]}｜開頭={head!r}　⚠ 若是 HTML 多半是被擋，不是端點壞了")
            return rl.finish()

        rows, note = parse(payload, a.start.replace("/", "-"),
                           end.replace("/", "-"))
        rl.info("官方回的", note)
        rl.check("回應涵蓋我請求的整段期間（不是靜靜回今天）", bool(rows), note)
        if not rows:
            return rl.finish()

    if not a.scan_only:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            for r in sorted(rows):
                w.writerow(r + [today])
        rl.info("判準檔",
                f"data/meta/otc_exright_history.csv｜{len(rows):,} 筆")

    if a.no_scan:
        # ⭐ 第一半場到此為止：判準檔抓回來了，⛔ 而**還沒補**，所以現在掃沒有意義。
        #   ⇒ daily.yml 接下來會跑 `otc_adj.py --official` ＋ `adjust.py`，
        #     再回頭用 `--scan-only` 掃一次。
        rl.info("⭐ 這一半只抓不掃",
                "⇒ 補完（`otc_adj.py --official` ＋ `adjust.py`）之後"
                "再跑一次 `--scan-only`，⛔ 那時掃的才是補過的 `data/adj/`")
        return rl.finish()

    have = ours_events()
    miss = [r for r in rows if (r[1], r[0]) not in have]
    by_year = Counter(r[0][:4] for r in miss)
    etf = [r for r in miss if r[1].startswith("00")]
    rl.info("我方 data/universe/otcexright/", f"{len(have):,} 筆")
    rl.info("⭐ 官方有、我方沒有",
            f"**{len(miss):,} 筆／{len({r[1] for r in miss})} 檔**"
            f"（其中代號 00 開頭的 ETF／ETN {len(etf):,} 筆）")
    rl.info("  分年", "｜".join(f"{y} {n:,}" for y, n in sorted(by_year.items())))

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ **反方向**（三點①：只比一個方向就宣告一致）
    #   2026-09-16 之前這一支只比了上面那一個方向，⚠ 而反方向是 246 筆／26 檔
    #   ——⛔ 報表上一個字都沒有。詳見 `ours_only_verdict` 的說明。
    # ══════════════════════════════════════════════════════════════
    # ⚠ `have` 是 `(代號, 日期)`，官方 `rows` 是 `(日期, 代號, …)`
    #   ⇒ **先轉成同一個方向**再比。⛔ 第一版我把 key 轉反了 ⇒ 13,197 筆全判成
    #     「我方獨有」、其中 12,951 筆「官方漏了」——⭐ 數字大到離譜才看得出來，
    #     ⚠ 而若只差幾筆，那個方向錯**看起來會跟真的一模一樣**。
    _off_keys = {(r[1], r[0]) for r in rows}
    only = sorted(k for k in have if k not in _off_keys)
    dd2 = os.path.join(_ROOT, "universe", "daily")
    days2 = sorted(n[:-4] for n in os.listdir(dd2)) if os.path.isdir(dd2) else []
    _after, _before, _via, _unk, _bad = ours_only_verdict(only, _transfer_out(), days2)
    rl.info("⭐ **反方向**：我方有、官方沒有",
            f"**{len(only):,} 筆／{len({c for c, _ in only})} 檔**"
            f"　⇒ 轉出上櫃**之後**的上市事件 {_after:,}"
            f"｜`delisted.csv` 查不到但**日檔說是上市** {_via:,}"
            f"｜⛔ **轉板之前**（＝官方真的漏了）**{_before:,}**"
            f"｜仍未判定 {_unk:,}")
    for b in _bad[:5]:
        rl.info(f"  ⛔ {b[0]} {b[1]}", b[2])
    # ⭐ 判準是「轉板之前那一格 == 0」，⛔ 不是「兩邊筆數一樣」
    #   （那永遠不會一樣：我方那個目錄裝的是 FinMind 給的，含轉板之後的上市事件）
    # ⇒ 放行之後誰在守：這一格本身（它是**算出來的**，每趟現場重算），
    #   ＋ 下面那道「官方有、我方 data/adj 沒有」的低水位閘門。
    rl.check("⭐⭐ **反方向**沒有一筆是「事件還在上櫃時官方就漏了」"
             "（⛔ 判準不是兩邊筆數一樣）",
             _before == 0,
             f"⛔ **{_before} 筆**：{_bad[:3]}" if _before
             else f"{len(only):,} 筆全部解釋得了"
                  f"（轉板後 {_after:,}＋日檔判定 {_via:,}＋未判定 {_unk:,}）")
    # ⛔ 上面那個比的是「我方的**判準目錄**」⇒ 不設 check：
    #   `data/universe/otcexright/` 是逐日累積的，早年本來就是空的，
    #   那是**歷史欠帳**，天天紅的檢查會被學會忽略。

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 但還有一個**完全不同**的方向要比：官方有、而我方 `data/adj/` 沒有。
    #   那不是「判準還沒累積到」，那是**還原因子真的缺了** ⇒ 假報酬。
    #
    # ⚠ 這一段是 2026-09-10 補的，因為**姊妹那一支（減資）當天就靠它抓到一筆**：
    #   6461 益得 2026-09-09 減資，我方 `data/adj/` 沒有
    #   ⇒ 用我方自己的價格證實：09-01 收 16.65（＝官方前收，一分不差）、
    #     09-02～09-08 停牌無列、09-09 收 25.75 ⇒ **+54.7% 的假報酬**。
    #   ⚠ 上櫃的 adj 只有人手動跑那個幾小時的 FinMind 全掃才會更新
    #     ⇒ 這種「新鮮的缺口」本來沒有任何東西會叫。
    #
    # ⛔ 涵蓋期內／外要分開數，判準與那一支共用**同一支** `classify_gaps`
    #   （⚠ 不可以再抄一份——今天同一族已經十二次）。
    # ══════════════════════════════════════════════════════════════
    adj = _adj_rows()
    adj_miss = [r for r in rows if (r[1], r[0]) not in adj]
    dd = os.path.join(_ROOT, "universe", "daily")
    days = sorted(n[:-4] for n in os.listdir(dd)) if os.path.isdir(dd) else []
    cover = days[0] if days else ""
    inside, named, live = _classify_gaps(adj_miss, cover, known={})
    rl.info("⭐ 官方有、我方 **data/adj/** 沒有",
            f"{len(adj_miss):,} 筆｜其中**落在涵蓋期內**（≥ {cover or '—'}）"
            f"**{len(inside)} 筆**")
    for r in live[:10]:
        rl.info(f"  ⛔ 涵蓋期內 {r[1]} {r[0]}",
                f"{r[2] if len(r) > 2 else ''}"
                "　⇒ 沒有這個因子，那一檔的還原序列在這一天是**假報酬**")
    lowwater.gate(rl, LOW, len(live), lowwater.DOWN,
                  "涵蓋期內、我方 data/adj 缺的除權息")
    rl.info("⛔ 這一支不寫 data/universe/otcexright/",
            "那個目錄的唯一寫入者是 `otc_adj.py`（走 FinMind）。"
            "換供料是**換維護者**的決定，不是順手加一行。")
    rl.info("⛔⛔ 而且它**不是完整來源**",
            "這張表是「除權除息計算結果表」⇒ **不含減資**（實測 59 檔裡少 17 筆），"
            "也**不含該檔轉上市之後**的事件（1752 南光 5 筆）。"
            "⇒ 拿它整批重建會**刪掉減資因子**，那幾檔還原價整段錯。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
