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
import re
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
# ⭐ 2026-09-10 新增末三欄：官方**自己給的**換股比例（第 11 欄 `詳細資料`）。
#   ⛔ 原有的 `factor`（＝參考價 ÷ 最後收盤）**留著不動**——
#     改判準是 K線線的事，這裡只把兩個都存下來並且逐筆比。
HEADER = ["date", "stock_id", "name", "last_close", "ref_price", "factor",
          "reason", "shares_per_1000", "cash_return", "factor_official", "asof"]


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


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 第 11 欄 `詳細資料`：官方**自己給的**減資換股比例
#
#   情報分析線 2026-09-10 16:15 實測（`startDate=2011/01/01`）：
#     287/287 解析成功、零 null，內容長這樣——
#
#       每壹仟股換發新股票: 618.578 股
#       每股退還股款: 0.00000000 元/股
#
#   ⭐ 而且它**自帶驗算**（他們逐筆跑過，287 筆全過、不符 0、缺值 0）：
#
#       恢復買賣參考價 ＝（最後交易日收盤價 − 每股退還股款）÷（每壹仟股換發新股 ÷ 1000）
#
#   ⇒ 「每壹仟股換發新股票」**就是**減資因子的分母，
#     ⛔ 而我方原本的 `factor` 是從**印到分為止**的參考價回推的 ⇒ 帶著四捨五入殘差。
#
# ⛔ 但這裡**只存不換**：`factor` 用哪一個是判準問題 ⇒ K線線裁定。
#   ⚠ 我方 `data/adj/` 的單一寫入者也不是這一支。
#
# ⚠ 這一欄是 HTML ⇒ ⛔ 不可以只認一種寫法：
#   全形冒號、標籤、`&nbsp;`、千分位、「每仟股」少一個「壹」，都得吃得下。
#   ⭐ 而認不出來時**要把原文印出來**——`bulletin/revivt` 那次 283 列全部認不出，
#     失敗訊息只給了一個數字，代價是再打對方一趟才知道為什麼。
# ══════════════════════════════════════════════════════════════════
_TAG = re.compile(r"<[^>]*>")
_NUM_AFTER = r"[^0-9]{0,12}([0-9][0-9,]*(?:\.[0-9]+)?)"
_RE_RATIO = re.compile(r"每\s*[壹一]?\s*仟\s*股\s*換\s*發\s*新\s*股\s*票?" + _NUM_AFTER)
_RE_CASH = re.compile(r"每\s*股\s*退\s*還\s*股\s*款" + _NUM_AFTER)


def parse_detail(raw):
    """第 11 欄 → (每壹仟股換發新股, 每股退還股款)。認不出來一律回 None。

    ⛔ 認不出來**不可以回 0**：`每股退還股款 = 0` 是真的會發生的值
    （彌補虧損那一類就是 0）⇒ 用 0 當「沒讀到」會讓恆等式**看起來過了**。
    """
    if raw is None:
        return None, None
    txt = _TAG.sub(" ", str(raw))
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("\u3000", " ")):
        txt = txt.replace(a, b)
    def _one(rx):
        m = rx.search(txt)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return _one(_RE_RATIO), _one(_RE_CASH)


def official_ref(last_close, ratio, cash):
    """官方恆等式：參考價 ＝（最後收盤 − 退還股款）÷（每壹仟股換發新股 ÷ 1000）。"""
    if not last_close or not ratio:
        return None
    return (last_close - (cash or 0.0)) * 1000.0 / ratio


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
    # ⚠ 第 11 欄。⛔ 不設成必要欄位：官方哪天拿掉它，我方不該整批停擺——
    #   那一欄是**加值**，`factor` 沒有它照樣算得出來。
    i_dt = _pick(fields, "詳細資料", "詳細資料說明", "備註")
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
    why = {"不是 list": 0, "欄數不足": 0, "日期認不出": 0, "代號是空的": 0,
           # ⚠ 這一種**不會讓那一列被丟掉**（第 11 欄是加值，不是必要欄）
           #   ⇒ 它只影響 `shares_per_1000`／`factor_official`，所以不加進 `bad`。
           "第11欄認不出": 0}
    sample = detail_sample = None
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
        # ⭐ 官方自己給的換股比例（第 11 欄）。⛔ 認不出來就留空，不要猜。
        ratio = cash = None
        if i_dt is not None and len(r) > i_dt:
            ratio, cash = parse_detail(r[i_dt])
            if ratio is None:
                why["第11欄認不出"] += 1
                if detail_sample is None:
                    detail_sample = str(r[i_dt])[:300]
        ref_o = official_ref(lc, ratio, cash)
        rows.append([dt, code, str(r[i_n]).strip() if i_n is not None else "",
                     str(r[i_lc]).replace(",", "").strip(),
                     str(r[i_rp]).replace(",", "").strip(), f,
                     str(r[i_rs]).strip() if i_rs is not None else "",
                     "" if ratio is None else f"{ratio:.6f}",
                     "" if cash is None else f"{cash:.8f}",
                     f"{ref_o / lc:.8f}" if (ref_o and lc) else ""])
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
    n_ratio = sum(1 for r in rows if r[7])
    return rows, (f"{len(data)} 列｜認得出 {len(rows)}"
                  + (f"｜⚠ 認不出 {bad}" if bad else "")
                  + f"｜⭐ 第 11 欄換股比例 {n_ratio}/{len(rows)}"
                  + (f"　⛔ 認不出 {why['第11欄認不出']} 列，第一列原文={detail_sample!r}"
                     if why["第11欄認不出"] else "")
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


# ⭐ `factor` 與 `factor_official` 兩欄都只存到**小數 8 位**
#   ⇒ 各自的捨入誤差 ≤ 5e-9，兩個相減 ⇒ **最多 1e-8**。
#   ⛔ 第一版的上界漏了這一項 ⇒ 四筆常駐紅燈，超出量全是 2~4e-9（正好落在這裡面）。
#   ⚠ 而那種紅燈最糟：它天天紅、永遠修不好，然後**大家學會忽略它**。
FACTOR_DP = 1e-8


def over_bound(rows, cents=0.005):
    """→ 兩種 factor 的差**超過捨入理論上界**的那些。⛔ 抽成函式是為了測得到。

    上界有**兩項**，⛔ 少算任何一項都會製造常駐假紅：

        ① 官方參考價印到**分** ⇒ 與真值差 ≤ 0.005 元
           ⇒ 回推的 factor 與原始比例差 ≤ **0.005 ÷ 最後收盤價**
        ⭐ ② 我方兩個 factor 欄各只存 **8 位小數** ⇒ 相減的捨入誤差 ≤ **1e-8**

    ⚠ ①**跟前收成反比**：10 元的股票是 5e-4、100 元的是 5e-5
    ⇒ ⛔ 不可以用固定常數當門檻（對低價股太鬆、對高價股太嚴）。
    ⚠ ②是**固定**的，而且在高價股那一端會變成主導項
    （100 元的股票①只有 5e-5，②的 1e-8 相對就不可忽略）。

    ⛔ 這不是「加個 epsilon 讓它變綠」：2026-09-11 那四筆的超出量是
    **2~4e-9**，而 8 位小數的捨入本來就能製造到 1e-8——⭐ 是上界寫漏了，不是資料錯。
    """
    out = []
    for r in rows:
        lc = _num(r[3])
        if not (r[5] and r[9] and lc):
            continue
        try:
            gap, bound = abs(float(r[5]) - float(r[9])), cents / lc + FACTOR_DP
        except ValueError:
            continue
        if gap > bound:
            out.append((r[1], r[0], round(gap, 8), round(bound, 8), r[5], r[9]))
    out.sort(key=lambda x: -x[2])
    return out


# ⚠ 容差照情報分析線量到的：絕對 0.005（官方參考價印到分為止）＋相對 1e-4。
# ⭐ 而 `REPR_EPS` 是第三項，2026-09-11 補的：**0.005 在二進位不可表示**
#   ⇒ `abs(48.125 - 48.13)` 算出來是 0.005000000000002558，比 0.005 大 **2.5e-15**
#   ⇒ 官方參考價是 `x.xx5` 進位上去的那幾筆，會**全部落在邊界外、天天紅**。
#   ⛔ 這一項純粹是浮點表示誤差，⚠ 而真正的解析錯誤至少差 0.01 ⇒ 1e-9 藏不住它。
IDENT_ABS, IDENT_REL, REPR_EPS = 0.005, 1e-4, 1e-9


def identity_check(rows):
    """官方自帶的恆等式逐筆驗。→ (過的, 不過的)。⛔ 抽成函式是為了測得到。

        恢復買賣參考價 ＝（最後收盤 − 每股退還股款）÷（每壹仟股換發新股 ÷ 1000）

    ⭐ 它的價值不是「多一個數字」，是**把兩個獨立欄位綁在一起**：
    換股比例讀錯、參考價欄位錯位、我方欄位對應搞反——任一種都會讓它不符，
    ⛔ 而那三種失敗**單看任何一欄都完全正常**。
    """
    ok, bad = [], []
    for r in rows:
        lc, rp = _num(r[3]), _num(r[4])
        if not r[7] or not lc or not rp:
            continue
        ref_o = official_ref(lc, float(r[7]), float(r[8] or 0))
        tol = max(IDENT_ABS, rp * IDENT_REL) + REPR_EPS
        (ok if abs(ref_o - rp) <= tol else bad).append(
            (r[1], r[0], round(ref_o, 4), rp))
    return ok, bad


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

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 官方**自帶的**驗算（情報分析線 16:15：287 筆全過、不符 0、缺值 0）
    #
    #     恢復買賣參考價 ＝（最後收盤 − 每股退還股款）÷（每壹仟股換發新股 ÷ 1000）
    #
    # ⚠ 這條恆等式的價值不是「多一個數字」，是**它把兩個獨立欄位綁在一起**：
    #   換股比例讀錯、參考價欄位錯位、我方欄位對應搞反——任一種都會讓它不符。
    #   ⛔ 而那三種失敗**單看任何一欄都完全正常**。
    # ══════════════════════════════════════════════════════════════
    n_ratio = sum(1 for r in rows if r[7])
    rl.check("⭐ 第 11 欄（官方換股比例）每一列都解得出來",
             n_ratio == len(rows),
             f"{n_ratio}/{len(rows)}　⛔ 缺 {len(rows) - n_ratio} 列"
             "（說明欄有第一列原文，⇒ 不必再打對方一趟才知道為什麼）"
             if n_ratio != len(rows) else f"{n_ratio}/{len(rows)}")
    ident_ok, ident_bad = identity_check(rows)
    rl.check("⭐ 官方自洽恆等式（參考價 ＝（收盤−退款）÷（換股數÷1000））逐筆成立",
             not ident_bad,
             f"⛔ {len(ident_bad)} 筆不符：{ident_bad[:6]}" if ident_bad
             else f"{len(ident_ok)} 筆全過"
                  f"（容差 {IDENT_ABS} ＋ 相對 {IDENT_REL}"
                  f" ＋ {REPR_EPS} 表示誤差）")

    # ⛔ 只 info 不 check：**用哪一個當 factor 是判準問題 ⇒ K線線裁定。**
    #   ⚠ 我方原本的 `factor` 是從「印到分為止」的參考價回推的 ⇒ 帶四捨五入殘差；
    #     官方比例是原始值。兩者差多少要先量出來，⛔ 不是先改掉。
    diffs = []
    for r in rows:
        if r[5] and r[9]:
            try:
                diffs.append((abs(float(r[5]) - float(r[9])), r[1], r[0],
                              r[5], r[9]))
            except ValueError:
                pass
    diffs.sort(reverse=True)
    if diffs:
        big = [d for d in diffs if d[0] > 1e-4]
        rl.info("⚠ 兩種 factor 的差（參考價回推 vs 官方比例）",
                f"{len(diffs)} 筆可比｜最大 {diffs[0][0]:.8f}"
                f"（{diffs[0][1]} {diffs[0][2]}：{diffs[0][3]} vs {diffs[0][4]}）"
                f"｜差 > 1e-4 的有 **{len(big)}** 筆")
        # ⭐ 分布（K線線 20:20 指名要的）。⚠ 他們要的不是為了改裁定，
        #   是為了訂下面那條斷言 ⇒ 這裡照級距給，⛔ 不要只給一個最大值。
        bins = [(0, 1e-6), (1e-6, 1e-5), (1e-5, 1e-4), (1e-4, 1e-3),
                (1e-3, 1e-2), (1e-2, float("inf"))]
        dist = {f"<{hi:g}": sum(1 for d in diffs if lo <= d[0] < hi)
                for lo, hi in bins}
        rl.info("  ⭐ 殘差分布（K線線 20:20 要的）", dist)

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ K線線 20:20 裁定的新斷言：**捨入殘差有理論上界，超過的就不是捨入**
    #
    #   官方參考價印到**分**為止 ⇒ 它與真值的差 ≤ 0.005 元
    #   ⇒ 由它回推的 factor 與原始比例的差 ≤ **0.005 ÷ 最後收盤價**
    #
    # ⭐ 這條斷言的價值：它把「兩個數字有點不一樣」這種**沒有判準的觀察**，
    #   變成一條**有理論上界**的判準。
    # ⛔ 超過上界的那些**不是捨入，是解析錯了**（換股比例讀錯一位、
    #   退還股款漏掉、欄位錯位）——⚠ 而那三種單看任何一欄都完全正常。
    #
    # ⚠ 具名列出，⛔ 不只給數量：一個「有幾筆超標」的訊息不足以診斷，
    #   `bulletin/revivt` 那次（283 列全認不出、只給一個數字）的代價是一整個來回。
    # ══════════════════════════════════════════════════════════════
    over = over_bound(rows)
    rl.check("⭐ 兩種 factor 的差都在**捨入的理論上界**（0.005 ÷ 前收）之內",
             not over,
             f"⛔ **{len(over)} 筆超過上界 ⇒ 那不是捨入，是解析錯了**："
             + "；".join(f"{c} {d} 差 {g}＞上界 {b}（{f1} vs {f2}）"
                         for c, d, g, b, f1, f2 in over[:6])
             if over else
             f"{len([1 for r in rows if r[5] and r[9]])} 筆全在界內"
             "（⚠ 上界逐筆算，⛔ 不是一個固定常數——它跟前收成反比）")

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
