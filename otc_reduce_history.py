#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_reduce_history.py — 上櫃**減資**的官方歷史（櫃買公告區「減資恢復買賣」）。

## 為什麼今天才有

`sources/reduce_source.md` 記的是「形狀對，**但只回未來十天**」。
⛔ 那是**參數送錯**。市場情報分析線 2026-09-10 10:00 實測：

    POST https://www.tpex.org.tw/www/zh-tw/bulletin/revivt
    body: startDate=2015/01/01&endDate=2026/09/09&response=json
    → **234 筆，一次回完**（選擇器下限 data-start="20130101"，資料也真的從 2013 開始）

⭐ 而這一支是**必要的**，不是錦上添花：
`exDailyQ`（除權息）**不含減資**——59 檔的抽驗裡就少了 17 筆。
拿除權息表當上櫃 adj 的完整來源會**刪掉減資因子**，那幾檔的還原價整段錯。

    上櫃 adj ＝ exDailyQ（上櫃期間除權息）＋ **revivt（減資）** ＋ TWT49U（轉上市後）

## ⛔ 參數行為：同一個 `bulletin/` 家族，三支**並不相同**

情報分析線 10:06 自我更正過一次（他把 `exDailyQ` 的行為套到另兩支）：

    | | exDailyQ | revivt | pvChgRslt |
    | GET ＋斜線   | ⛔ 靜靜回今天 | ✅ 正常 | 未測 |
    | POST ＋無斜線 | ⛔ 靜靜回今天 | stat:參數錯誤（**大聲失敗**） | stat:參數錯誤 |
    | POST ＋斜線   | ✅ | ✅ | ✅ |

⇒ **最安全的寫法是 POST ＋ 斜線**（三支都過）。
⚠ 但錯誤處理不同：`exDailyQ` 必須自己檢查回應日期區間；
  這一支靠 `stat` 就擋得住——⛔ 儘管如此，本支**兩道都做**，
  因為「對方哪天改行為」不在我的控制範圍內。

## 這一支做什麼

1. 抓全期，寫 `data/meta/otc_reduce_history.csv`（判準檔）
2. ⭐ **逐筆掃「官方有、我方 `data/adj/` 沒有」**——這正是情報分析線
   10:00 說「那一掃你來做比較省」的那一掃（我手上就有全部 `data/adj/`）。
   他只驗過「我方已有的那些對得上」（12/12 逐位相符），**沒驗「我方缺哪些」**。
3. ⛔ 不寫 `data/adj/` 也不寫 `data/universe/otcreduce/`（單一寫入者）。
"""
import argparse
import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

import runlog
from twparse import (pick_field as _pick_field, post_form as _post_form,
                     roc_iso as _roc_iso)

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "otc_reduce_history.csv")
ADJ = os.path.join(_ROOT, "adj")
LOW = os.path.join(_ROOT, "meta", "_otc_reduce_gap_low.txt")

URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/revivt"
HEADER = ["date", "stock_id", "name", "last_close", "ref_price", "factor",
          "reason", "asof"]


# ⛔ 第九／第十份：`_post` 也收進 `twparse.py`。
_post = _post_form



# ⛔ `_iso` 與 `_pick` 原本在這兩支各有一份（逐字相同）——同一族的第七、第八份。
#   2026-09-10 收進 `twparse.py`，⭐ 而且順便把日期格式做寬並測它：
#   `bulletin/revivt` 那天回了 283 列、我方**一列都認不出來**。
_iso = _roc_iso
_pick = _pick_field


def _num(v):
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse(payload, want_from):
    """→ (rows, note)。⛔ 兩道守門都做：`stat` 與**回應涵蓋的日期範圍**。"""
    if isinstance(payload, dict):
        stat = str(payload.get("stat", "")).strip()
        # ⛔ 這一支參數錯會**大聲失敗**（stat:參數錯誤）——跟 exDailyQ 不同。
        #   但仍然不能只靠它，見檔頭：對方哪天改行為不在我的控制範圍內。
        if stat and stat.lower() not in ("ok", "success"):
            return [], f"⛔ 端點自己說失敗：stat={stat!r}"
    tabs = (payload.get("tables") if isinstance(payload, dict) else None) or []
    if not tabs and isinstance(payload, dict) and payload.get("data"):
        tabs = [payload]
    if not tabs:
        return [], f"回應裡沒有表（鍵={list(payload)[:8] if isinstance(payload, dict) else type(payload).__name__}）"
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    data = t.get("data") or []
    if not data:
        return [], "回了 0 列 ⛔ 當失敗，不是「這十一年沒有減資」"
    i_d = _pick(fields, "恢復買賣日期", "日期")
    i_c = _pick(fields, "股票代號", "證券代號", "代號")
    i_n = _pick(fields, "名稱")
    i_lc = _pick(fields, "最後交易日之收盤價", "最後交易日")
    i_rp = _pick(fields, "恢復買賣開始日參考價", "參考價格", "參考價")
    i_rs = _pick(fields, "減資原因", "原因")
    miss = [n for n, i in (("日期", i_d), ("代號", i_c),
                           ("最後收盤", i_lc), ("參考價", i_rp)) if i is None]
    if miss:
        return [], f"欄位對不上，缺 {miss}：{fields}"
    rows, bad = [], 0
    # ⛔⛔ 2026-09-10 的教訓：這裡原本只數 `bad`，於是 Actions 上的失敗訊息是
    #   「一列都認不出來（bad=283）」＋欄位名——**那不足以診斷**，
    #   我必須再跑一趟（再打對方一次）才知道是日期格式、還是列的形狀、還是代號空的。
    #   ⚠ 一個會叫、但叫不出原因的斷言，代價是一整個來回。
    #   ⇒ 分開數每一種原因，並附**第一列原文**。
    why = {"不是 list": 0, "欄數不足": 0, "日期認不出": 0, "代號是空的": 0}
    sample = None
    for r in data:
        if sample is None:
            sample = r
        if not isinstance(r, list):
            why["不是 list"] += 1
            bad += 1
            continue
        if len(r) <= max(i_d, i_c, i_lc, i_rp):
            why["欄數不足"] += 1
            bad += 1
            continue
        dt, code = _iso(r[i_d]), str(r[i_c]).strip()
        lc, rp = _num(r[i_lc]), _num(r[i_rp])
        if not dt:
            why["日期認不出"] += 1
            bad += 1
            continue
        if not code:
            why["代號是空的"] += 1
            bad += 1
            continue
        # ⭐ factor ＝ 參考價 ÷ 最後交易日收盤價（與 `data/adj` 同定義）
        f = f"{rp / lc:.8f}" if (lc and rp) else ""
        rows.append([dt, code, str(r[i_n]).strip() if i_n is not None else "",
                     str(r[i_lc]).replace(",", "").strip(),
                     str(r[i_rp]).replace(",", "").strip(), f,
                     str(r[i_rs]).strip() if i_rs is not None else ""])
    if not rows:
        # ⭐ 把「為什麼」講出來，⛔ 不要只給一個數字。
        detail = "｜".join(f"{k} {v}" for k, v in why.items() if v)
        return [], (f"一列都認不出來（{len(data)} 列；{detail}）"
                    f"　欄位={fields}"
                    f"　第一列原文={str(sample)[:300]}")
    ds = sorted(r[0] for r in rows)
    recent = (datetime.now(TPE) - timedelta(days=30)).strftime("%Y-%m-%d")
    if ds[0] > want_from and ds[0] >= recent:
        return [], (f"⛔ 回的只有最近的資料（{ds[0]} ~ {ds[-1]}，{len(rows)} 筆），"
                    f"我要的是 {want_from} 起　⚠ 參數多半沒生效")
    return rows, (f"{len(data)} 列｜認得出 {len(rows)}"
                  + (f"｜⚠ 認不出 {bad}" if bad else "")
                  + f"｜涵蓋 {ds[0]} ~ {ds[-1]}｜欄位 {fields}")


# ⚠ 已歸因的偽陽性：官方自己重複的那一列。
#   證據：6109 把 `1070925` 重打成 `1090925`（六個數字完全相同），
#   而我方 2020-09-25 **無跳價、無停牌** ⇒ 那天沒有減資。
#   （`reduce_check.py` 2026-09-09 對 284 筆匯出檔時就查出同一件事。）
#   ⛔ 具名排除只准放**已經查證過**的，⚠ 而且要寫得出證據。
KNOWN_OFFICIAL_DUP = {
    ("6109", "2020-09-25"): "官方自己重複的列（1070925 誤打成 1090925）",
}


def classify_gaps(miss, cover, known=None):
    """「官方有、我方沒有」分成三堆。→ (涵蓋期內, 已歸因, 未歸因)

    ⭐⭐ 2026-09-10：**「涵蓋期內」與「涵蓋期外」是兩件事，不可以混在一起數。**

    ⛔ 原本一律不設 check，理由是「那是歷史欠帳，天天紅會被學會忽略」
      ——⚠ 對**涵蓋期外**（我方日檔還沒開始的年份）成立，
        ⛔ 對**涵蓋期內**完全不成立：那是**現在就錯的還原因子**。

    ⚠ 而這個區分不是理論：本支第一次跑完，51 筆裡涵蓋期內只有 2 筆，
      其中 **1 筆是昨天發生的**（6461 益得 2026-09-09）——
      ⭐ 用我方自己的價格證實：09-01 收 16.65（＝官方 `last_close`，一分不差）、
      09-02~09-08 停牌無列、09-09 收 25.75。
      **沒有那個因子，序列上就是 +54.7% 的假報酬。**
      ⚠ 上櫃的 adj 只有人手動跑那個幾小時的 FinMind 全掃才會更新
        ⇒ 這種「新鮮的缺口」本來沒有任何東西會叫。

    ⚠ **恢復買賣日在未來的列一律排除**：那是官方的預告，事件還沒發生，
      我方當然沒有 ⇒ ⛔ 不排除的話這道檢查**每天假紅**。
      ⭐ 但那些列本身有用（可以提前備妥因子），所以只在「缺口」這道檢查裡排除。

    ⛔ `cover`（涵蓋起點）由呼叫端**從資料自己算**，不寫死——
      寫死的話資料庫往前長之後就對不上。
      ⚠ 算不出來（沒有日檔）時 `cover` 是空字串 ⇒ **一律當涵蓋期外**，
        ⛔ 不可以反過來當成「全部都在涵蓋期內」，那會憑空生出一堆假警報。
    """
    known = KNOWN_OFFICIAL_DUP if known is None else known
    if not cover:
        return [], [], []
    # ⛔⛔ 2026-09-10 情報分析線 16:15 點出、⚠ 而我今早才把這支接進每日：
    #   `revivt` **會回恢復買賣日在未來的預告列**（當天可見四筆：
    #   09-14 6129、09-21 3710／8059／8277）。
    #   ⭐ 那是好事——**可以提前備妥因子**，不必等當天才發現漏抓。
    #   ⛔ 但「官方有、我方沒有」這道檢查**必須排除它們**，否則**每天假紅**：
    #     那些事件根本還沒發生，我方當然沒有。
    #   ⚠ 而一條每天紅的斷言，三天之後就沒有人看了——
    #     它會連旁邊真正的 ✗ 一起帶走。
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    inside = [r for r in miss if cover <= r[0] <= today]
    named = [r for r in inside if (r[1], r[0]) in known]
    live = [r for r in inside if (r[1], r[0]) not in known]
    return inside, named, live


def adj_rows():
    """→ {(代號, 日期): factor 字串}，我方 `data/adj/` 的全部事件。"""
    out = {}
    if not os.path.isdir(ADJ):
        return out
    for n in os.listdir(ADJ):
        if not n.endswith(".csv") or n == "_index.csv":
            continue
        try:
            with io.open(os.path.join(ADJ, n), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("date"):
                        out[(n[:-4], r["date"])] = r.get("factor", "")
        except OSError:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2013/01/01")
    ap.add_argument("--end", default="")
    ap.add_argument("--json", help="離線用：讀一個檔當回應")
    a = ap.parse_args()

    rl = runlog.Run("otc_reduce_history")
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    end = a.end or today.replace("-", "/")
    rl.info("端點", f"POST {URL}｜{a.start} ~ {end}"
                    "　⛔ POST ＋日期帶斜線（無斜線這一支會 stat:參數錯誤，"
                    "⚠ 但 exDailyQ 是靜默的——同族三支行為不同）")

    if a.json:
        raw, err = io.open(a.json, "rb").read(), None
    else:
        raw, err = _post(URL, {"startDate": a.start, "endDate": end,
                               "response": "json"})
    if err or not raw:
        rl.check("抓得到 revivt", False, f"{str(err)[:100]}"
                 "｜⛔ 抓不到不等於沒有歷史（本機對 tpex 一律 403）")
        return rl.finish()
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        head = raw[:80].decode("utf-8", "replace").replace("\n", " ")
        rl.check("回應是 JSON", False, f"{str(ex)[:50]}｜開頭={head!r}")
        return rl.finish()

    rows, note = parse(payload, a.start.replace("/", "-"))
    rl.info("官方回的", note)
    rl.check("回應涵蓋我請求的整段期間", bool(rows), note)
    if not rows:
        return rl.finish()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in sorted(rows):
            w.writerow(r + [today])
    rl.info("判準檔", f"data/meta/otc_reduce_history.csv｜{len(rows):,} 筆")
    rl.info("  原因分布", dict(Counter(r[6] for r in rows).most_common(6)))

    # ── ⭐ 情報分析線 10:00 指名要我做的那一掃 ──────────────────────
    #   他驗過的是「我方已有的那些對得上」（12/12 逐位相符），
    #   ⛔ **沒驗「我方缺哪些」**——而那要全部 `data/adj/` 才掃得動。
    have = adj_rows()
    miss = [r for r in rows if (r[1], r[0]) not in have]
    bad_f = []
    for r in rows:
        k = (r[1], r[0])
        if k in have and r[5] and have[k]:
            try:
                if abs(float(r[5]) - float(have[k])) > 1e-6:
                    bad_f.append((r[1], r[0], r[5], have[k]))
            except ValueError:
                pass
    rl.info("⭐ 官方有、我方 data/adj 沒有",
            f"**{len(miss)} 筆／{len({r[1] for r in miss})} 檔**"
            + (f"｜前 10：{[(r[1], r[0], r[6]) for r in miss[:10]]}" if miss else ""))
    rl.info("  分年", dict(Counter(r[0][:4] for r in miss).most_common()))
    rl.check("兩邊都有的那些 factor 逐位相符",
             not bad_f, f"{len(bad_f)} 筆不符：{bad_f[:6]}"
             if bad_f else f"{len(rows) - len(miss)} 筆全中")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 2026-09-10：**「涵蓋期內」與「涵蓋期外」是兩件事，不可以混在一起數。**
    #
    # ⛔ 原本這裡一律不設 check，理由寫著「那是歷史欠帳，天天紅會被學會忽略」
    #   ——⚠ 對**涵蓋期外**（我方日檔還沒開始的年份）成立，
    #     ⛔ 對**涵蓋期內**完全不成立：那是**現在就錯的還原因子**。
    #
    # ⚠ 而這個區分不是理論：本支 2026-09-10 第一次跑完，51 筆裡
    #   涵蓋期內只有 2 筆，其中 **1 筆是昨天發生的**（6461 益得 2026-09-09）
    #   ——⭐ 用我方自己的價格證實：09-01 收 16.65（＝官方 last_close，一分不差）、
    #   09-02~09-08 停牌無列、09-09 收 25.75。**沒有那個因子，序列上就是 +54.7% 的假報酬。**
    #   ⚠ 上櫃的 adj 只有人手動跑那個幾小時的 FinMind 全掃才會更新
    #     ⇒ 這種「新鮮的缺口」本來沒有任何東西會叫。
    #
    # ⛔ 涵蓋起點**從資料自己算**，不寫死：寫死的話資料庫往前長之後就對不上。
    # ══════════════════════════════════════════════════════════════
    dd = os.path.join(_ROOT, "universe", "daily")
    days = sorted(n[:-4] for n in os.listdir(dd)) if os.path.isdir(dd) else []
    cover = days[0] if days else ""

    inside, named, live = classify_gaps(miss, cover)

    rl.info("  ⭐ 其中**落在我方涵蓋期內**（≥ 首個日檔 " + (cover or "—") + "）",
            f"**{len(inside)} 筆**"
            + (f"｜已歸因 {len(named)}｜⛔ **未歸因 {len(live)}**" if inside else ""))
    for r in named:
        rl.info(f"    已歸因 {r[1]} {r[0]}", KNOWN_OFFICIAL_DUP[(r[1], r[0])])
    for r in live:
        rl.info(f"    ⛔ 未歸因 {r[1]} {r[2]} {r[0]}",
                f"{r[6]}｜官方 前收 {r[3]} → 參考價 {r[4]}｜factor {r[5]}"
                "　⇒ 沒有這個因子，那一檔的還原序列在這一天是**假報酬**")
    # ⛔ 判準用**歷史最低值**，不是「比上一趟多」——跟 `missing_rows.py`／`adj_gap.py`
    #   同一條理由：用「比上一趟」的話，補好一次基準就停在低點，
    #   下一個新缺口要累積到超過舊基準才會紅。用歷史最低 ⇒ **單調收斂**。
    low = None
    if os.path.exists(LOW):
        try:
            low = int(io.open(LOW, encoding="utf-8").read().split(",")[0])
        except (ValueError, IndexError):
            low = None
    base = len(live) if low is None else min(low, len(live))
    rl.info("  歷史最低值", f"{low if low is not None else '（第一趟）'} → {base}")
    rl.check("涵蓋期內未歸因的缺口沒有高於歷史最低值",
             low is None or len(live) <= low,
             f"歷史最低 {low}｜本輪 {len(live)}" if low is not None
             else f"第一趟，只記錄不判定（本輪 {len(live)}）")
    try:
        io.open(LOW, "w", encoding="utf-8").write(
            f"{base},{datetime.now(TPE).strftime('%Y-%m-%d')}\n")
    except OSError:
        pass
    # ⛔ 涵蓋期**外**那些仍然不設 check：那才是真的歷史欠帳，天天紅會被學會忽略。
    rl.info("⛔ 這一支不寫 data/adj/",
            "單一寫入者是 `adjust.py`／`otc_adj.py`。這裡只提供證據。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
