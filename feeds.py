#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feeds.py — 全市場「每日一請求」型資料的回補器。

為什麼另開一支：`backfill.py` 已經 54 KB 且是驗證過的路徑，
價格與法人的回補全靠它。把五種新資料塞進去，等於每加一種就冒一次
「動到已經對的東西」的風險。**這支只做新增的 feed，價格與法人不碰。**

**共用的脆弱函式一律 import backfill，不複製**——`get()` 的退避、
`daterange()` 的交易日與週六補班、`_same_day()` 的日期核對、
`_num()` 的數字清洗，每一個都踩過坑。複製一份等於未來兩份各修一次，
而且會靜默分岔。

---

## 已驗證（2026-09-04，實測 date=20260903）

| feed | 端點 | 結果 |
|---|---|---|
| `per`     | TWSE `BWIBBU_d` | stat=OK、**1,580 列**、8 欄（本益比／殖利率／股價淨值比） |
| `exright` | TWSE `TWT49U`   | stat=OK、**4 列**、15 欄（除權息前收盤價／參考價／權值+息值） |

`exright` 那天的 4 列含 3661 世芯-KY 除息 32.551656、參考價 4,167.44，
與 `claude/watchlist_state.md` 記的「09/03 除息 32.55、參考價 4,167.45」對得起來。

## 未驗證（候選清單，靠 --probe 淘汰）

`margin`（上市融資融券）、`otcinst`（上櫃三大法人）、`otcper`、`otcmargin`、`otcexright`。

**上市融資融券 `MI_MARGN` 在 2026-09-04 用 selectType=ALL／ALLBUT0999／MS
三種參數實測都回「很抱歉，沒有符合條件的資料」**——端點在、參數不對。
候選清單裡放了其他幾種寫法，由 probe 決定。

**TPEx 的端點無法從開發環境驗證**（對外直接讀一律 403），
但**管線在 GitHub Actions 裡讀得到**——上櫃日檔就是這樣抓的。
所以 TPEx 的候選只能在 Actions 上 probe，不能在本機下結論。

---

## 一條紀律：候選清單裡不准放「只回今天」的端點

`backfill.py` 的註解已經記過這個事故：openapi 型端點沒有 date 參數、
永遠回當日資料，回補時會把今天的數字寫進 2015 年的檔案——
**靜默、每個數字都是真的、只是屬於另一個年代。**
本檔所有候選都必須帶日期參數，且一律經過 `_same_day()` 核對。
"""
import argparse
import calendar          # ★ cmd_probe 與 _months 都要用；原本只在 _months 內 import，
                         #   cmd_probe 改成逐月探測後會 NameError
import csv
import io
import json
import os
import re
import sys
import time

import backfill as B
import fetch as _F
import runlog

_ROOT = B._ROOT
UNI_DIR = B.UNI_DIR


# ────────────────────────────────────────────────────────────
# 解析器
# ────────────────────────────────────────────────────────────

def _fieldmap(t):
    return [str(x).strip() for x in (t.get("fields") or [])]


def _exact(fields, *names):
    """★ 完全相等比對，不用「包含」。

    T86 踩過這個坑：欄名互相包含，用子字串比對會讓「自營商買賣超股數」
    命中「外資自營商買賣超股數」，16,833 列裡 16,394 列驗算不符。
    """
    for n in names:
        for i, f in enumerate(fields):
            if f == n:
                return i
    return None


def _blank_num(v):
    """數字欄的清洗：拿不到就回空字串，**不要回 0**。

    `--esb` 踩過：1,064 列零價被當成真的價格，回測算出 −100%。
    「沒有」和「零」在這裡是完全不同的事實。
    """
    s = B._num(v)
    if s is None:
        return ""
    s = str(s).strip()
    if s in ("", "-", "--", "N/A", "不適用", "除權息"):
        return ""
    return s


def parse_tib(d, day, known=None):
    """TWSE `STOCK_TIB` → **官方創新板成分清單**（逐日）。

    ## 為什麼要存它

    ⛔ 我方原本靠**名稱後綴**（`/(?:-|KY)創$/`）認創新板。
    市場情報分析線 2026-09-10 10:44 找到官方清單，並比對 **2026-09-09 零差異**
    （官方 30 檔 vs 字串法 30 檔，兩個方向都 0）。
    ⇒ 字串法在那一天是對的，⭐ **但它是猜的**：改名就會失效，而且不會有人發現。

    ## ⚠ 為什麼存成**逐日**，不是一份現況清單

    K線線的判準一句話：「問的是『它**現在**是什麼』還是『它**那時候**是什麼』。」
    ⇒ 圈選歷史區間時要的是那一天的成分 ⇒ **逐日**。
    （這也是 `stocks.csv` 的 `market` 欄不可以拿來圈歷史那條的同一個理由。）

    ## ⛔ 兩個邊界

    ① **歷史下限 2021-06-28**（創新板 2021-07-20 開板，所以夠用）。
       越界時官方**明說**：`stat:"查詢日期小於110年6月28日，請重新查詢!"`
       ⇒ 這一支是**大聲失敗**，不是靜默回最新——這件事本身要記著。
    ② ⛔ **最後一列是「合計」，代號欄是空字串**，要丟掉。
       ⚠ 而它不是垃圾：情報分析線驗過那一列的成交金額
       ＝ `MI_INDEX` 大盤統計「14.創新板股票」，**差 0**。
       ⇒ 丟掉是因為它不是一檔股票，⛔ 不是因為它不可信。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_code = _exact(f, "證券代號", "股票代號", "代號")
    i_name = _exact(f, "證券名稱", "股票名稱", "名稱")
    if i_code is None:
        return [], f"欄位對不上：{f}"
    out, skipped = [], 0
    for r in (t.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        # ⛔ 「合計」那一列的代號欄是空字串 ⇒ 這一條就是在丟它。
        #   ⚠ 用 `code[0].isdigit()` 而不是 `code != "合計"`：
        #     名稱欄才寫「合計」，代號欄是空的——照名稱擋會擋不到。
        if not code or not code[0].isdigit():
            skipped += 1
            continue
        if known and code not in known:
            continue
        out.append([day, code,
                    str(r[i_name]).strip() if i_name is not None else ""])
    return out, f"{len(out)} 檔（丟掉 {skipped} 列沒有代號的，含「合計」）"


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 借券賣出（SBL）—— K線線 2026-09-10 15:45 列為**第一優先**
#
#   借券賣出是融券的 **77.5 倍**（2002 中鋼差 3,225 倍），
#   缺口逐年惡化（2015 是 9.2 倍 → 2026 是 72.7 倍）
#   ⇒ **融券現在只佔空方的 1.4%**。
#   ⇒ K線線的 `券資比 = 融券餘額 ÷ 融資餘額` **分子只涵蓋空方的 1.4%**，
#     而「券資比低 ＝ 空方壓力小」是拿那 1.4% 對整體下結論。
#   ⚠ 偏誤方向**單一**：借券賣出越集中的股票（大型權值股、外資愛用），
#     判讀就越樂觀。⭐ 而它**不會炸、不會缺值、不會有人抱怨**。
#
# ── 實測（`sbl_probe.py`，2026-09-09，Actions）────────────────────
#   兩市場的 title 都是「信用額度總量管制餘額表」，**15 欄、兩段併在一起**：
#
#     欄 0-1   股票（代號、名稱）
#     欄 2-7   **融券**：前日餘額／賣出／買進／現券／今日餘額／限額
#     欄 8-13  **借券賣出**：前日餘額／當日賣出／當日還券／當日調整／當日餘額／次一營業日可限額
#     欄 14    備註
#
#   ⛔ **兩段的「前日餘額」「當日餘額」欄名重複** ⇒ 只看欄名一定取錯。
#
# ⭐ 而上市那一側**官方自己講出了邊界**——一個我方從來沒讀過的鍵：
#     groups: [{"title":"股票","span":2},{"title":"融券","span":6},
#              {"title":"借券賣出","span":6},{"title":"","span":1}]
#   ⇒ 借券那一段從哪一欄開始，**不必猜也不必寫死**：照 `groups` 累加就好。
#   ⚠ 上櫃**沒有** `groups`（頂層鍵只有 date／stat／tables）
#     ⇒ 只能靠位置，⛔ 所以守衛要更嚴：欄名結構逐字比對實測。
#
# ⚠ 官方 notes 明文（上市那側才有）：
#     「借券賣出當日餘額＝前日餘額＋當日賣出−當日還券＋當日調整」
#   ⇒ ⭐ **免費的逐列驗算**，位置取錯時它會整片不符。
#     「借券賣出股數含鉅額交易股數。」⇒ 引用倍數時要標。
#   ⛔ 上櫃那側**沒有 notes 也沒有 total** ⇒ 完整性只能靠恆等式。
#
# ⚠ `TWT93U` 每日晚間**二次更新**（約 20:30 與 22:30）
#   ⇒ 排程落在兩次之間會拿到**不完整**的版本，而它看起來完全正常。
# ══════════════════════════════════════════════════════════════════
# 實測欄名（2026-09-09）。⛔ 這是**契約**：對不上就整張表拒收。
SBL_TWSE_FIELDS = ["代號", "名稱", "前日餘額", "賣出", "買進", "現券", "今日餘額",
                   "次一營業日限額", "前日餘額", "當日賣出", "當日還券",
                   "當日調整", "當日餘額", "次一營業日可限額", "備註"]
SBL_TPEX_FIELDS = ["股票代號", "股票名稱", "前日餘額", "賣出", "買進", "現券",
                   "當日餘額", "限額", "前日餘額", "當日賣出", "當日還券",
                   "當日調整數額", "當日餘額", "次一營業日可借券賣出限額", "備註"]


def _sbl_seg_from_groups(d):
    """→ 借券那一段的起始欄位（照官方 `groups` 累加）。取不到回 None。

    ⭐ `groups` 是我方一路丟掉的鍵之一，⚠ 而它正好解掉「兩段欄名重複」——
      ⛔ 不必猜、不必寫死位置，**官方自己講**。
    """
    g = d.get("groups") if isinstance(d, dict) else None
    if not isinstance(g, list):
        return None
    at = 0
    for seg in g:
        if not isinstance(seg, dict):
            return None
        if "借券" in str(seg.get("title", "")):
            return at
        try:
            at += int(seg.get("span", 0))
        except (TypeError, ValueError):
            return None
    return None


_DROP_WHO_RE = re.compile(r"\('(\d[\dA-Za-z]*)',\s*'([^']*)'\)")


def _drop_codes(note):
    """從說明的樣本裡撈出 (代號, 原因)。→ list。⛔ 撈不到回空清單。

    ⚠ 這是**從給人看的字串反向取值**，本來就是這個檔案警告過的做法
    ⇒ 之所以可以，是因為那串樣本是我方自己在 `_drop_note()` 裡格式化的，
      ⛔ 不是官方回應的原文；⚠ 而且撈不到只會讓歸因少一筆，不會誤判成瑕疵。
    """
    return _DROP_WHO_RE.findall(str(note))


def _tally_drop(n_written, day, note):
    """→ (這一天丟了幾列, 要印出來的說明)。⛔ 抽成函式是為了讓 selftest 測得到。

    ⚠ 這裡有兩件事**必須一起做**，分開就會走岔：
    ① 丟棄數要取**數字**（`_dropped_in`），⛔ 不是「有沒有出現『丟棄』兩個字」
       ——那樣一天丟 40 列會被記成 1。
    ② 丟棄不是 0 時，**parser 的原始說明要保留**（它帶著是哪幾檔、差多少）
       ⛔ 蓋掉之後每天默默丟幾十列也看不出來。
    """
    n_drop = _dropped_in(note)
    return n_drop, (f"{n_written} 列" if not n_drop
                    else f"{n_written} 列｜{note}")


def _explain_drops(name, dropped_who, days):
    """→ (已歸因, 未歸因)。⛔ 判準用**資料自己**，不另開台帳。

    ## ⭐ 情報分析線 2026-09-10 23:00 查出來的那一筆

        2015-01-22　3416 融程電
        前日餘額 1,000　賣出 0　還券 0　調整 0　當日餘額 **0**　⇒ 差 1,000 股
        備註欄：**空的**

    成因：**那天是它在上櫃的最後一個交易日**（01-23 轉上市）。
    ⇒ 官方在它離開上櫃時把借券餘額**直接歸零**，
      ⛔ 沒有走「還券」也沒有走「調整」欄 ⇒ 恆等式當然不成立。

    ⚠ 所以這不是資料瑕疵，**是恆等式的定義邊界**——
    ⭐ 而它跟 `exDailyQ`「不含該檔轉上市之後」是**同一個形狀，第二次出現**。

    ⇒ 判準：不符時看該檔**次一交易日還在不在這張表上**
      不在 ⇒ 離開本市場（轉上市／終止櫃買）⇒ ⛔ 不是瑕疵
      還在 ⇒ 才是真的要查

    ⛔ **不可以靠備註欄判斷**——那一筆的備註是空的。
    """
    idx = {d: i for i, d in enumerate(days)}
    left, unexplained = [], []
    for day, code in dropped_who:
        i = idx.get(day)
        nxt = days[i + 1] if i is not None and i + 1 < len(days) else None
        if nxt is None:
            # ⚠ 區間最後一天沒有「次一日」可看 ⇒ ⛔ 不可判定，一律當未歸因
            #   （寧可多查一筆，不要把真的瑕疵歸成「它離開了」）
            unexplained.append((day, code, "區間最後一天，無次一日可比"))
            continue
        path = os.path.join(UNI_DIR, name, f"{nxt}.csv")
        if not os.path.exists(path):
            unexplained.append((day, code, f"次一日 {nxt} 沒有檔可比"))
            continue
        with io.open(path, encoding="utf-8") as f:
            codes = {r.get("stock_id", "") for r in csv.DictReader(f)}
        (left if code not in codes else unexplained).append(
            (day, code, f"次一日 {nxt} {'已不在表上' if code not in codes else '仍在表上'}"))
    return left, unexplained


def _drop_note(kept, tag, bad, samples):
    """驗算不符時的說明。⛔ **要講得出是哪幾列**，不是只給一個數字。

    ⚠ 這是 `bulletin/revivt` 那次的教訓（283 列全部認不出，訊息只說「bad=283」
      ＋欄位名 ⇒ **不足以診斷**，我得再打對方一趟才知道為什麼）。
    ⭐ 而丟棄這一族更難：它一次只掉幾列，數量小到不會有人想去追，
      ⛔ 於是「1 天有丟棄」這種紅燈會一直紅著沒有人動它——
      `feeds:otcsbl` 就是這樣紅著的，而 runlog 連**哪一天**都沒寫。
    """
    # ⚠ `丟棄 {bad} 列` 這幾個字**是有人在比對的**（`cmd_feed` 用它算 `dropped_days`）
    #   ⇒ ⛔ 格式不可以亂改。⭐ 而那本身就是這個檔自己警告過的事
    #     （「訊息字串是給人看的，不是狀態機的輸入」）——
    #     ⇒ 那一邊已經改成用 `_dropped_in()` 明確取數，這裡維持相容格式。
    if not bad:
        return f"{kept} 列可用（{tag}；驗算不符丟棄 0 列）"
    return (f"{kept} 列可用（{tag}；⛔ 驗算不符丟棄 {bad} 列"
            f"｜前 {len(samples[:3])} 筆：{samples[:3]}）")


_DROP_RE = re.compile(r"丟棄\s*(\d+)\s*列")


def _dropped_in(note):
    """從 parser 的說明取出丟棄列數。→ int（取不到回 0）。

    ⛔ 這一支存在的理由寫在 `cmd_feed` 裡：那裡原本用
    `"丟棄" in note and "丟棄 0 列" not in note` 判斷有沒有丟棄
    ——⚠ 而同一個檔案裡就記著「**訊息字串是給人看的，不是狀態機的輸入**」
    （休市日被算成失敗那次，就是因為結尾是全形括號對不到）。
    ⇒ 收成一條具名的規則，⛔ 而且它取得出**數字**，不只是有無。
    """
    m = _DROP_RE.search(str(note))
    return int(m.group(1)) if m else 0


def _sbl_rows(t, day, known, i0, tag):
    """共用的借券輸出與驗算。`i0` ＝ 借券那一段的起始欄。

    ⭐ 官方恆等式（notes 明文）：**當日餘額 ＝ 前日餘額＋當日賣出−當日還券＋當日調整**
      ⇒ 位置取錯時它會**整片不符** ⇒ 它就是「位置對不對」的檢驗。
      ⛔ 不符的列丟掉並計數，⚠ 不要靜默寫進去。
    """
    out, bad, samples = [], 0, []
    n = lambda v: (float(str(v).replace(",", "").strip())
                   if str(v).strip() not in ("", "-", "--") else 0.0)
    for r in (t.get("data") or []):
        if not r or len(r) < i0 + 6:
            continue
        code = str(r[0]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        vals = [_blank_num(r[i]) for i in range(i0, i0 + 6)]
        try:
            ok = abs(n(vals[0]) + n(vals[1]) - n(vals[2]) + n(vals[3])
                     - n(vals[4])) <= 1
        except ValueError:
            bad += 1
            samples.append((code, "數字轉不動", vals))
            continue
        if not ok:
            bad += 1
            # ⭐ 把**差多少**也記下來：差 1~2 股是進位、差一個量級是欄位對錯位。
            #   ⚠ 那兩種的處置完全不同，⛔ 只給「不符」分不出來。
            gap = (n(vals[0]) + n(vals[1]) - n(vals[2])
                   + n(vals[3]) - n(vals[4]))
            samples.append((code, f"前{vals[0]}+賣{vals[1]}-還{vals[2]}"
                                  f"+調{vals[3]}≠餘{vals[4]}（差 {gap:+.0f}）"))
            continue
        # ⛔ 備註是**文字**（X／Y／V／%／Z／!），不可以走 `_blank_num`
        note = str(r[14]).strip() if len(r) > 14 else ""
        # 融券那一段（欄 2~7）照官方原文一起存：⚠ 這張表的融券是**總量管制**視角，
        #   跟 `margin` feed 那一份不是同一個口徑，⛔ 不可以互相取代。
        s_seg = [_blank_num(r[i]) for i in range(2, 8)] if len(r) > 7 else [""] * 6
        out.append([day, code] + s_seg + vals + [note])
    return out, _drop_note(len(out), tag, bad, samples)


def parse_sbl(d, day, known=None):
    """TWSE `TWT93U` 借券賣出餘額。⭐ **段落邊界照官方 `groups`**，不寫死。"""
    tabs = B._tables(d)
    if not tabs:
        return [], f"沒有 tables；頂層鍵={sorted(d) if isinstance(d, dict) else type(d).__name__}"
    t = tabs[0]
    f = _fieldmap(t)
    if f != SBL_TWSE_FIELDS:
        return [], f"欄位結構與 2026-09-09 實測不符，拒收：{f}"
    i0 = _sbl_seg_from_groups(d)
    # ⛔ `groups` 取不到就**拒收**，不要退回寫死的 8：
    #   官方哪天調整段落而 `groups` 跟著變，寫死那條會靜靜取錯欄。
    #   ⚠ 而欄名比對已經擋住「欄變了」的情形 ⇒ 這裡拒收只會在 groups 消失時發生，
    #     那本身就是要有人看一眼的事。
    if i0 is None:
        return [], ("拒收：`groups` 裡找不到「借券」那一段 "
                    f"⇒ 段落邊界無從得知（groups={d.get('groups')!r}）")
    if i0 != 8:
        return [], f"⚠ `groups` 說借券從第 {i0} 欄開始，與實測的 8 不同 ⇒ 先拒收，要有人看"
    return _sbl_rows(t, day, known, i0, "TWSE groups 定位")


def parse_otcsbl(d, day, known=None):
    """TPEx `margin/sbl`。⛔ **沒有 `groups`、沒有 `total`、沒有 `notes`** ⇒ 守衛更嚴。"""
    tabs = B._tables(d)
    if not tabs:
        return [], f"沒有 tables；頂層鍵={sorted(d) if isinstance(d, dict) else type(d).__name__}"
    t = tabs[0]
    f = _fieldmap(t)
    if f != SBL_TPEX_FIELDS:
        return [], f"欄位結構與 2026-09-09 實測不符，拒收：{f}"
    # ⚠ 這一側只能靠位置（欄名重複、又沒有 groups）
    #   ⇒ 上面那條「欄名逐字相同」就是唯一的守衛，⛔ 不可以放寬成「包含」比對。
    return _sbl_rows(t, day, known, 8, "TPEx 位置定位（⛔ 沒有 groups）")


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 變更交易（全額交割）—— K線線 2026-09-10 15:45 的 Q5
#
#   他們的前置閘門有「全額交割股」一列，而我方全文查「全額交割」**0 次**
#   ⇒ 那一列**目前不可執行**。⚠ 而他們自己說過：
#     **「假裝有在擋」比沒有擋更危險**，因為下游會以為過了關。
#
# ── 實測（`delist_probe.py`，Actions）─────────────────────────────
#   `date=` **是真的吃的**：2015-01-05 → 23 列、2020-01-03 → 21、2026-09-09 → 23
#   `stat=OK`、`total` 與列數一致、欄位 3 個、⚠ 值是 `["1213","大飲","  "]` 這種
#
# ⭐ 官方 `notes` 的符號說明**逐字**（K線線 §8 指名要的，⛔ 不是轉述）：
#
#     `**` 代表上市證券除應預先收足款券外，其交易採**分盤集合競價**方式，
#     該方式係採每 30 分鐘以人工管制之撮合終端機執行撮合作業一次為原則，
#     並得視交易情形因應公告調整撮合時間。
#
#   ⇒ 他們「閘門第一列拆成【狀態＝分盤集合競價】＋【成因 A 處置／成因 B 變更交易】」
#     那條裁定**成立**，不必作廢。
#
# ⚠ 而另一支 `BFIHBU` 的 notes 講的是這一群**還被禁掉什麼**：
#     「變更交易有價證券**不得進行當日沖銷交易、融資融券交易、借券交易、
#       平盤以下借券賣出**」
#   ⇒ ⛔ 「融資融券欄位是 0」至少有**兩個**成因：
#     ① 主管機關個別公告停止融資融券（`MI_MARGN` 備註欄，且那是**次一營業日**）
#     ② 被列為變更交易 ⇒ 連當沖與借券一起禁掉，**比 ① 嚴**
#   ⚠ 只查其中一個名單會誤判。
# ══════════════════════════════════════════════════════════════════
FULLDEL_FIELDS = ["證券代號", "證券名稱", "分盤集合競價(以**表示)"]


def parse_fulldelivery(d, day, known=None):
    """TWSE `fullDelivery/TWT85U` 變更交易（全額交割）名單。"""
    tabs = B._tables(d)
    if not tabs:
        return [], f"沒有 tables；頂層鍵={sorted(d) if isinstance(d, dict) else type(d).__name__}"
    t = tabs[0]
    f = _fieldmap(t)
    # ⛔ 欄名逐字比對：只有 3 欄、而且第 3 欄的欄名本身帶著符號說明
    #   ⇒ 官方哪天改欄名（例如拿掉「(以**表示)」）就代表符號可能也改了。
    if f != FULLDEL_FIELDS:
        return [], f"欄位結構與 2026-09-09 實測不符，拒收：{f}"
    out = []
    for r in (t.get("data") or []):
        if not r or len(r) < 3:
            continue
        code = str(r[0]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        # ⭐ 第 3 欄是 `**` 或**兩個空白**（實測：`["1213","大飲","  "]`）
        #   ⛔ 存成 1/0，不存原文：原文是空白時 CSV 讀回來分不出「空白」與「沒有值」。
        #   ⚠ 判準用「含 `*`」而不是 `== "**"`：⭐ 借券那件才學到的
        #     ——分類欄可能是複合的，等號比對會漏掉。
        raw = str(r[2])
        out.append([day, code, str(r[1]).strip(), "1" if "*" in raw else "0"])
    n_split = sum(1 for r in out if r[3] == "1")
    return out, f"{len(out)} 檔｜其中併採分盤集合競價 {n_split} 檔"


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 上市「**停止買賣中**」——`violation/stop`
#
# K線分析線 2026-09-11 01:40（端點是使用者給的）。⚠ 他們同時訂正了自己
# 「這一頁抓不到」那句：他們**只試了給人看的那個網址**
# （`/zh/listed/violations/stop.html`，那個確實是 JS 殼），
# ⛔ 沒試 `/rwd/` 的資料端點就下了結論。
# ⇒ ⭐ 可執行化的規矩：**寫「抓不到」時要附試過的網址清單**，只試一個不算。
#
# ## ⛔⛔ 這一支**沒有歷史**——漏抓一天就永久少一天
#
# K線線實測 `?date=20240401` ⇒ **參數被忽略**，`title` 仍是當天。
# ⇒ 它是「**今天仍在停止買賣中**」的即時名單。
# ⚠ 補抓成本是**無限大**（拿不回來）⇒ 這一支的優先度比一般回補高，
#   ⛔ 而它壞掉的樣子是「那一天沒有檔」，不是錯誤。
#
# ⭐ 但每一列都附**停止買賣開始日期** ⇒ 第一次抓到的那天，
#   就能把「當下這一段」的**起點**整段補回去，不必等它累積。
#
# ## ⭐ 它解掉的是「停止買賣中」與「已下市」分不開的問題
#
# K線線的〈硬斷點〉閘門要走兩條不同分支：
#   已下市     ⇒ 永遠不會回來，不進母體
#   停止買賣中 ⇒ ⚠ **它會復牌**，而復牌後前後兩段中間隔了好幾個月
#              ⛔ 接起來算均線／扣抵／ATR ＝ 把一段不存在的時間當成交易日
# ⚠ 而在資料庫裡這兩者**現在長得一模一樣**（都只是「日線沒有列了」）。
#
# ⛔ 而 `meta/suspend`（TWTAWU）**不是**這張表：那一支是「短暫停牌後復牌」，
#   9,594/10,034 列是權證，未復牌的 21 檔普通股 `halt_date` 全停在 2013~2014。
#
# ⚠ 上櫃的對應來源**還沒找到** ⇒ ⛔ 這裡不猜，`stophalt_tpex` 由探針決定。
STOPHALT_FIELDS = ["證券代號", "證券名稱", "違反營業細則條款",
                   "停止買賣原因", "停止買賣開始日期"]


def parse_stophalt(d, day, known=None):
    """TWSE `violation/stop` 停止買賣中的名單。→ (lines, note)。

    ⛔ `day` 是**快照日**，不是查詢日：這一支的 `date=` 參數官方會忽略
    （K線線實測）⇒ ⚠ 寫進檔名的那一天必須是「我方抓它的那一天」。
    ⭐ 而 `fetch_one` 的 `_same_day` 仍然會擋一層：`title` 講的日子
    要對得上，⛔ 對不上代表那份名單不是今天的。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], (f"沒有 tables；頂層鍵="
                    f"{sorted(d) if isinstance(d, dict) else type(d).__name__}")
    t = tabs[0]
    f = _fieldmap(t)
    # ⛔ 欄名逐字比對：⚠ 這一支只有五欄，而「停止買賣開始日期」那一欄
    #   是本支**唯一**能回推歷史的東西——欄名一變就代表它可能不在了。
    if f != STOPHALT_FIELDS:
        return [], f"欄位結構與 K線線 2026-09-11 實測不符，拒收：{f}"
    out = []
    for r in (t.get("data") or []):
        if not r or len(r) < len(STOPHALT_FIELDS):
            continue
        code = str(r[0]).strip()
        if not code or not code[0].isdigit():
            continue
        # ⛔ **不用 `known` 濾**：停止買賣中的個股很可能已經不在我方母體裡
        #   （它就是因為停了才不再出現在日檔）⇒ 濾掉等於把最該記的那些丟掉。
        # ⭐ 「115年04月07日」⇒ `2026-04-07`。⛔ 這裡不自己算民國年——
        #   `first_date_compact` 是**唯一**那一份（`_same_day` 把 2021 讀成
        #   1932 那個 bug 就是自己算年份算出來的），⚠ 認不出來就留空、不猜。
        since = _iso_dash(_F.first_date_compact(r[4]))
        out.append([day, code, str(r[1]).strip(), "twse",
                    since, str(r[2]).strip(), str(r[3]).strip()])
    # ⭐ 說明要講得出**最早的那一段從哪天開始**：那一格就是可回推的歷史。
    starts = sorted(x[4] for x in out if x[4])
    return out, (f"{len(out)} 檔停止買賣中"
                 + (f"｜最早自 {starts[0]}" if starts else "｜⚠ 一列都沒有開始日期"))


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 上櫃「變更交易／分盤／管理股票／停止交易」——`afterTrading/chtm`
#
# 上市只有 `TWT85U` 一欄 `**`（要自己從「變更交易」推「有沒有分盤」）；
# ⭐ 上櫃這一支**四個狀態各一欄**，而且**直接給撮合循環時間**。
#
# ── 我方實測（`chtm_probe.py`，Actions 2026-09-10）───────────────
#   頂層鍵 `date`／`stat`／`tables`；`date` 回顯**我請求的那一天**（20150105）
#   欄位 **10 個**，逐字：
#     ['證券代號','證券名稱','變更交易','分盤交易','屬管理股票',
#      '分盤或管理股票撮合循環時間(分鐘)','停止交易','財務資訊重點專區',
#      '公告連結','財務重點專區連結']
#
# ⛔⛔ 兩處把情報分析線 18:00 那封**推翻**了（我方自己量的）：
#   ① 他們說 8 欄——**實際 10 欄**（漏了兩個連結欄）。
#      ⚠ 照 8 欄寫死位置，後面兩欄會被當成不存在；⛔ 而我方一律用欄名定位，
#        所以這裡的代價只是「少存兩欄」，不是錯位。
#   ② 他們說 `98/06/01` **靜靜回今天**——**不是**。
#      實測回 `date: 20090601`、38 列，與今天那一份**逐位元組不同**
#      ⇒ ⭐ 這支的歷史至少回到 **2009**，比他們說的 2015 更早。
#      ⚠ 那是「越界」與「參數不吃」被混為一談；⛔ 兩者的處置完全不同。
#
# ⛔⛔ 而有一個會讓整欄靜默變空的坑（情報分析線這一條是對的，我方實測證實）：
#   **那個 `Ｙ` 是全形（U+FF39），不是半形 `Y`。**
#   ⇒ 寫 `== "Y"` 會**一筆都不匹配**，而且不報錯——整欄變成「沒有任何一檔被標記」。
# ⚠ 而撮合時間是**零填三位的字串**（`"030"`／`"045"`），不是整數也不是 `30`。
#   ⇒ 我方**原樣存字串**，⛔ 不轉成整數：轉了就分不出「沒有值」與「0 分鐘」。
#
# ⭐ 五個旗標欄實測都只有兩種值（`""` 與 `Ｙ`）⇒ **不是複合值**，可以當布林讀。
#   ⚠ ⛔ 但「實測是兩種」不等於「永遠是兩種」——所以我方存的是
#     「有沒有被標記」而**不是**原文字元，並且**任何非空值都算被標記**
#     （含 `*` 那條同一個道理：⛔ 不用等號比對）。
# ══════════════════════════════════════════════════════════════════
CHTM_FIELDS = ["證券代號", "證券名稱", "變更交易", "分盤交易", "屬管理股票",
               "分盤或管理股票撮合循環時間(分鐘)", "停止交易",
               "財務資訊重點專區", "公告連結", "財務重點專區連結"]
# ⭐ 全形 Ｙ。⛔ 這一行是這支解析器最容易被下一個人「順手改成 'Y'」的地方。
CHTM_YES = "\uff39"


def _chtm_flag(v):
    """→ "1"／"0"。⛔ 判準是「**非空**」，不是 `== 'Ｙ'`。

    ⚠ 兩個理由，都不是理論：
    ① 那個 `Ｙ` 是**全形**（U+FF39）⇒ 寫成半形會一筆都不匹配、而且不報錯。
    ② ⭐ 分類欄要當「集合」讀不要當「值」讀（K線線 20:20 抽的通則）：
       一格裡可以同時裝 `OX!`、`XV`、`**`、`*ABCD`。
       ⛔ `==` 的偏誤不是隨機的，它**系統性地放行狀態最多、最該被擋的那一批**。
    """
    return "1" if str(v).strip() else "0"


def parse_chtm(d, day, known=None):
    """TPEx `afterTrading/chtm` → 上櫃變更交易／分盤／管理股票／停止交易。"""
    tabs = B._tables(d)
    if not tabs:
        return [], (f"沒有 tables；頂層鍵="
                    f"{sorted(d) if isinstance(d, dict) else type(d).__name__}")
    t = tabs[0]
    f = _fieldmap(t)
    # ⛔ 欄名逐字比對：這一支的欄名**自己就是欄位語意**
    #   （「分盤或管理股票撮合循環時間(分鐘)」講明了單位是分鐘）
    #   ⇒ 官方改欄名就代表語意可能也改了。
    if f != CHTM_FIELDS:
        return [], f"欄位結構與 2026-09-10 實測不符，拒收：{f}"
    out = []
    for r in (t.get("data") or []):
        if not isinstance(r, list) or len(r) < 8:
            continue
        code = str(r[0]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        out.append([day, code, str(r[1]).strip(),
                    _chtm_flag(r[2]),          # 變更交易
                    _chtm_flag(r[3]),          # 分盤交易
                    _chtm_flag(r[4]),          # 屬管理股票
                    # ⭐ 原樣存字串（"030"／"045"），⛔ 不轉整數
                    str(r[5]).strip(),
                    _chtm_flag(r[6]),          # 停止交易
                    _chtm_flag(r[7])])         # 財務資訊重點專區
    n = {k: sum(1 for r in out if r[i] == "1")
         for i, k in ((3, "變更交易"), (4, "分盤"), (5, "管理股票"),
                      (7, "停止交易"))}
    cyc = sorted({r[6] for r in out if r[6]})
    return out, (f"{len(out)} 檔｜" + "／".join(f"{k} {v}" for k, v in n.items())
                 + f"｜撮合循環時間出現的值 {cyc or '（都沒有）'}")


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 個股融資成數的**調整幅度**——`marginTrading/BFIB9U`（上市）
#
# K線線那條 166.67 的基準值：官方明文「最高融資比率 60%、最低融券保證金成數 90%」
# ⚠ 而那是**上櫃頁面**的字，上市那一半還沒有逐字 ⇒ ⛔ 先不要套過去。
#
# ── 我方實測（`chtm_probe.py`，Actions 2026-09-10）───────────────
#   欄位（8）：編號／證券代號／證券名稱／調整成數原因／調整成數起日／恢復日
#              ／降低融資比率／提高融券保證金成數
#   不帶日期 → 471 列；`startDate=endDate=20150105` → 126 列 ⇒ **有逐日歷史**
#
# ⛔⛔ 三件會讓人讀錯的事，每一件都在實測值裡看得到：
#
# ① **同一檔會有很多列**：471 列裡只有 **94 個相異代號**
#    ⇒ 一檔 × 每個「調整成數原因」一列（實測 6 種原因）
#    ⇒ ⛔ 主鍵是（日期, 代號, **原因**），不是（日期, 代號）。
#
# ② **值不是純數字**：`降低融資比率` 的相異值是
#    `''`／`'1'`／`'6'`／`'累計：1'`／`'累計：6'`
#    ⇒ ⭐ `累計：N` 與 `N` 是**兩件事**（累計降低 vs 這一次降低）
#      ⛔ 直接 `int()` 會炸，`replace("累計：","")` 會把兩者混成一個數字。
#
# ③ 空值有**兩種寫法**：空字串與**單一半形空白**
#    （實測 `["1203","味王","監視第二次處置","","",  " ", " "]`）
#    ⇒ ⛔ 只判 `== ""` 會把那些讀成「有值」。
#
# ⚠ 而 ⛔ **這支不算「現行成數」**：官方給的是**調整幅度**，
#   要逐檔彙總再用「基準 − 累計調整」推——⭐ 而那是**判準**，屬 K線線。
#   ⇒ 我方只把原始欄位存下來，⛔ 不在這裡算，也不寫進契約當成「成數」。
#
# ⛔⛔ 而它有一種**沒有東西擋得住**的靜默失敗：
#   回應**沒有 `date`、`title` 也不帶日期** ⇒ `fetch_one` 的 `_same_day` 找不到
#   自述日期 ⇒ **一律放行**。⚠ 而不帶日期參數時它回的是**前一個營業日**
#   （實測 09-10 問，`hints` 說「期間：115年09月09日到115年09月09日」）。
#   ⇒ ⭐ 日期只寫在 `hints` 裡 ⇒ **這一支自己驗 `hints`**。
#   ⛔ 不把 `hints` 加進 `_same_day` 的通用鍵：別的端點的 `hints` 常寫著
#     「資料自 104 年起提供」這種**與本次查詢無關**的日期
#     ⇒ 那會變成大規模誤擋（`feeds:tib` 剛剛才因為誤擋掉了 1,050 天）。
# ══════════════════════════════════════════════════════════════════
MRATIO_FIELDS = ["編號", "證券代號", "證券名稱", "調整成數原因", "調整成數起日",
                 "恢復日", "降低融資比率", "提高融券保證金成數"]


def _mratio_val(v):
    """`降低融資比率`／`提高融券保證金成數` → (數字字串, 是否累計)。

    ⭐ 實測相異值：`''`／`'1'`／`'6'`／`'累計：1'`／`'累計：6'`／`' '`（單一空白）
    ⛔ `累計：N` 與 `N` 是兩件事，不可以混成一個數字。
    ⚠ 認不出來一律回 `("", "")`——⛔ 不要猜成 0（0 是「不調整」的真值）。
    """
    t = str(v).replace("：", ":").strip()
    cum = "1" if t.startswith("累計") else "0"
    if cum == "1":
        t = t.split(":", 1)[-1].strip() if ":" in t else t[2:].strip()
    if not t:
        return "", ""
    try:
        float(t)
    except ValueError:
        return "", ""
    return t, cum


def parse_marginratio(d, day, known=None):
    """TWSE `BFIB9U` 調整融資融券成數。⛔ 主鍵含**原因**，一檔多列。"""
    tabs = B._tables(d)
    if not tabs:
        return [], (f"沒有 tables；頂層鍵="
                    f"{sorted(d) if isinstance(d, dict) else type(d).__name__}")
    t = tabs[0]
    f = _fieldmap(t)
    if f != MRATIO_FIELDS:
        return [], f"欄位結構與 2026-09-10 實測不符，拒收：{f}"
    # ⭐⭐ 這一支的日期**只寫在 `hints` 裡** ⇒ 自己驗，⛔ 不靠 `_same_day`
    hints = str((d or {}).get("hints", "")) if isinstance(d, dict) else ""
    said = _F.first_date_compact(hints)
    if not said:
        return [], (f"⛔ `hints` 裡讀不出日期 ⇒ **無從確認這批是哪一天**"
                    f"（hints={hints[:80]!r}）"
                    "　⚠ 這一支沒有 `date`／`title` 可比，hints 是唯一的自述")
    if said != day.replace("-", ""):
        return [], (f"⛔ 回的是**別天**：hints 說 {said}，我要 {day}"
                    "　⚠ 不帶日期參數時它回的是前一個營業日")
    out = []
    for r in (t.get("data") or []):
        if not isinstance(r, list) or len(r) < 8:
            continue
        code = str(r[1]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        m_v, m_c = _mratio_val(r[6])
        s_v, s_c = _mratio_val(r[7])
        out.append([day, code, str(r[2]).strip(), str(r[3]).strip(),
                    _F.first_date_compact(r[4]) and
                    _iso_dash(_F.first_date_compact(r[4])),
                    _F.first_date_compact(r[5]) and
                    _iso_dash(_F.first_date_compact(r[5])),
                    m_v, m_c, s_v, s_c])
    codes = {r[1] for r in out}
    cum = sum(1 for r in out if r[7] == "1" or r[9] == "1")
    return out, (f"{len(out)} 列／**{len(codes)} 檔**（⚠ 一檔多列：一個原因一列）"
                 f"｜其中標「累計」的 {cum} 列")


def _iso_dash(compact):
    """`20210924` → `2021-09-24`。⛔ 空字串照樣回空字串。"""
    return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}" if compact else ""


def parse_per(d, day, known=None):
    """TWSE BWIBBU_d → 本益比／殖利率／股價淨值比。

    ★ 本益比欄常是 "-"（虧損公司算不出來）。**留空，不可填 0**——
      填 0 會讓「最便宜的股票」篩選結果整批是虧損股。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_code = _exact(f, "證券代號", "股票代號", "代號")
    i_close = _exact(f, "收盤價")
    i_yield = _exact(f, "殖利率(%)")
    i_dyear = _exact(f, "股利年度")
    i_per = _exact(f, "本益比")
    i_pbr = _exact(f, "股價淨值比")
    i_fsq = _exact(f, "財報年/季")
    if i_code is None or i_per is None or i_pbr is None:
        return [], f"欄位對不上：{f}"
    out = []
    for r in (t.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        g = lambda i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
        out.append([day, code, g(i_close), g(i_yield),
                    str(r[i_dyear]).strip() if i_dyear is not None and i_dyear < len(r) else "",
                    g(i_per), g(i_pbr),
                    str(r[i_fsq]).strip() if i_fsq is not None and i_fsq < len(r) else ""])
    return out, f"{len(out)} 列"


def _roc_date(v):
    # ★ docstring 裡有正則（`\d`），**一定要用 r"""**。
    #   普通字串會在 Python 3.12 觸發 `SyntaxWarning: invalid escape sequence '\d'`，
    #   每次跑都印一行雜訊——而雜訊多了就會有人不看 log。
    r"""民國「104年07月16日」**或**「115/09/07」→ 西元 YYYY-MM-DD；抽不到回空字串。

    ★ 兩種寫法都要吃。`TWT49U` 的「資料日期」長「104年07月16日」，
      `TWTAUU`（減資恢復買賣參考價）的「恢復買賣日期」長 `115/09/07`。
      只認前者的話，減資那張表**每一列都會因為抽不到日期被丟掉**——
      而丟棄是靜默的，看起來就跟「那個月沒有減資」一模一樣。

    斜線那條刻意用 `(?<!\d)(\d{2,3})/`：西元 `2026/09/07` 不會誤中
    （四位數被前後不接數字的條件擋掉），所以不會把民國與西元搞混。
    """
    t = str(v)
    m = re.search(r"(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", t)
    if not m:
        m = re.search(r"(?<!\d)(\d{2,3})/(\d{1,2})/(\d{1,2})(?!\d)", t)
    if not m:
        return ""
    return f"{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def parse_exright(d, day, known=None):
    """TWSE TWT49U → 除權除息計算結果。

    這是還原價的**事件來源**：還原因子 = 除權息參考價 ÷ 除權息前收盤價。
    ★ 因子在這裡**不算**，只存原始兩個價格。理由是還原要整段回推，
      屬於 `adjust.py` 的工作；在抓取端先算一半，日後改公式就得重抓。

    ★★ **日期取每一列自己的「資料日期」欄，不用傳進來的 `day`。**
      這支端點吃的是 startDate/endDate **區間**，一次可以回一整個月，
      所以同一份回應裡的列分屬不同日子。用 `day` 會把整個月都標成同一天。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_date = _exact(f, "資料日期")
    i_code = _exact(f, "股票代號", "證券代號", "代號")
    i_pre = _exact(f, "除權息前收盤價")
    i_ref = _exact(f, "除權息參考價")
    i_val = _exact(f, "權值+息值")
    i_kind = _exact(f, "權/息")
    i_open = _exact(f, "開盤競價基準")
    if i_code is None or i_pre is None or i_ref is None:
        return [], f"欄位對不上：{f}"
    out, nodate = [], 0
    for r in (t.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        g = lambda i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
        pre, ref = g(i_pre), g(i_ref)
        # 兩個價格缺一就不寫。**寧可少一列，不要寫一列算不出因子的**。
        if not pre or not ref:
            continue
        dt = _roc_date(r[i_date]) if (i_date is not None and i_date < len(r)) else ""
        if not dt:
            nodate += 1
            continue          # ★ 沒有自述日期就不收——寧可少一列，不要標錯日子
        out.append([dt, code, pre, ref, g(i_val),
                    (str(r[i_kind]).strip() if i_kind is not None and i_kind < len(r) else ""),
                    g(i_open)])
    note = f"{len(out)} 列"
    if nodate:
        note += f"（{nodate} 列無資料日期，已丟棄）"
    return out, note


def parse_reduce(d, day, known=None):
    """TWSE `reducation/TWTAUU` → 股票減資恢復買賣參考價格。

    ## 為什麼一定要有這張表

    `data/adj/` 原本只還原除權息。**減資的價格跳動動輒 30～50%**：
    3536 誠創 2015-03-20 前收 6.58 → 參考 13.33（＋103%）、
    1563 巧新 2026-09-07 前收 66.00 → 參考 84.66（＋28%）。
    那是股數變少造成的，**不是真的漲**。沒有這張表，任何跨過減資日的
    回測、長期報酬率、均線與扣抵值全都是錯的。

    ## 欄位（11 欄）

    `恢復買賣日期／股票代號／名稱／停止買賣前收盤價格／恢復買賣參考價／
      漲停價格／跌停價格／開盤競價基準／除權參考價／減資原因／詳細資料`

    因子 = 恢復買賣參考價 ÷ 停止買賣前收盤價格，**在這裡不算**——
    理由同 `parse_exright`：還原要整段回推，是 `adjust.py` 的事，
    在抓取端先算一半，日後改公式就得重抓。

    ## ★ 三個跟除權息不一樣的地方

    1. **日期格式是 `115/09/07`（斜線）**，不是「115年09月07日」。
       `_roc_date()` 已同時吃兩種。
    2. **`pre_close` 不是「前一個交易日」的收盤。** 減資會停止買賣數個交易日，
       它是**停止買賣前**最後一個有成交的日子的收盤。核對要拿「該檔在恢復
       買賣日之前最後一筆收盤」比，拿日曆的前一交易日比會整片假警報
       （做法見 `adjust.py` 的 `_verify_reduce`）。
    3. **因子會 > 1，而且可以很大。** 減資九成的話接近 10。
       `adjust.py` 那組 `0.05 < f ≤ 1.5` 的除權息界線套上來會把真事件全丟掉，
       所以界線改成**按事件種類分開**。

    ## ★ 減資與除權息同一天時只能算一次

    官方公式明寫「退還股款：恢復買賣參考價＝（停止買賣前收盤價−息值−每股退還
    股款）／（減資換股率）」——**息值已經含在裡面了**。同一天 `TWT49U` 也會有
    一列，兩邊都收就會把除息扣兩次。去重在 `adjust.py`，這裡照實全收。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = tabs[0]
    f = _fieldmap(t)
    i_date = _exact(f, "恢復買賣日期")
    # ⚠ `ETF代號` 是 2026-09-09 探針實測 TWTCAU 的欄名。
    #   `_exact` 是**完全相等**比對（T86 踩過子字串互相包含的坑），
    #   所以少列一個候選字就會 `i_code is None` → **整批不寫、回「欄位對不上」**。
    #   探針在第一個有事件的月份到來之前就抓到了，沒有真的漏過資料。
    i_code = _exact(f, "股票代號", "證券代號", "代號", "ETF代號")
    i_pre = _exact(f, "停止買賣前收盤價格", "停止買賣前收盤價")
    i_ref = _exact(f, "恢復買賣參考價", "恢復買賣參考價格")
    # TWTAUU 是「減資原因」、TWTCAU 是「分割(反分割)」——兩者都放進 reason 欄，
    # 因為它們回答的是同一個問題：**這一筆是哪一種公司行動**。
    i_reason = _exact(f, "減資原因", "分割(反分割)")
    i_open = _exact(f, "開盤競價基準")
    i_exref = _exact(f, "除權參考價")
    if i_code is None or i_pre is None or i_ref is None or i_date is None:
        return [], f"欄位對不上：{f}"
    out, nodate, noprice = [], 0, 0
    for r in (t.get("data") or []):
        if not r or len(r) <= i_code:
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        g = lambda i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
        pre, ref = g(i_pre), g(i_ref)
        if not pre or not ref:
            noprice += 1
            continue          # 兩個價格缺一就算不出因子，寧可少一列
        dt = _roc_date(r[i_date]) if i_date < len(r) else ""
        if not dt:
            nodate += 1
            continue          # ★ 沒有自述日期就不收——寧可少一列，不要標錯日子
        reason = (str(r[i_reason]).strip()
                  if i_reason is not None and i_reason < len(r) else "")
        out.append([dt, code, pre, ref, reason.replace(",", "；"),
                    g(i_open), g(i_exref)])
    note = f"{len(out)} 列"
    if nodate:
        note += f"（{nodate} 列無日期，已丟棄）"
    if noprice:
        note += f"（{noprice} 列缺價格，已丟棄）"
    return out, note


def parse_parvalue(d, day, known=None):
    """TWSE `change/TWTB8U` → 變更股票面額恢復買賣參考價格。

    ## 為什麼不直接用 `parse_reduce`

    欄位是 `TWTAUU` 的子集，解析邏輯一模一樣，所以**本函式就是呼叫它**——
    多一份幾乎相同的解析程式，等於多一處會各自飄移的地方。

    但 `parse_reduce` **把第 9 欄「詳細資料」丟掉了**，而那一欄是
    `代號,停止買賣起日,恢復買賣日`：

        8070,20200806,20200817
        7780,20260109,20260119

    ★ **那正是「停止買賣區間」，而且它是官方直接宣告的。** 2026-09-09 核對：
      8070 官方停止買賣起日 2020-08-06、恢復買賣日 2020-08-17；
      `parvalue_scan.py` 掃到的最後有成交日是 2020-08-05、復牌首成交日 2020-08-17。
      **恢復買賣日完全一致，停止買賣起日正好是最後有成交日的下一天。** 7780 同。

    ⚠ 為什麼非留不可：`data/meta/suspend.csv` **收的是暫停交易，不含換發新股票的
      停止買賣**——24 筆面額變更拿去對它，`resume_date` 命中 **0 筆**。
      丟掉這一欄，那段停止買賣區間就**整個資料庫都沒有第二個地方查得到**。

    所以本函式在 `parse_reduce` 的七欄之後補一欄 `halt_date`（停止買賣起日）。
    恢復買賣日不另存——它就是第一欄 `date`，存兩份會飄移。
    """
    rows, note = parse_reduce(d, day, known)
    if not rows:
        return rows, note
    tabs = B._tables(d)
    t = tabs[0] if tabs else {}
    f = _fieldmap(t)
    i_det = _exact(f, "詳細資料")
    i_code = _exact(f, "股票代號", "證券代號", "代號")
    # 「代號 → 停止買賣起日」對照。**用代號配對，不用列序**——
    # parse_reduce 會丟掉缺價格／缺日期的列，列序早就對不上了
    # （這正是 mops 那個「用位置對欄位」踩過的同一種坑）。
    halt = {}
    if i_det is not None and i_code is not None:
        for r in (t.get("data") or []):
            if not r or len(r) <= max(i_det, i_code):
                continue
            parts = [x.strip() for x in str(r[i_det]).split(",")]
            digits = [x for x in parts if x.isdigit() and len(x) == 8]
            # ⛔ **要兩個以上日期才認**。TWTB8U 的詳細資料是
            #   `代號,停止買賣起日,恢復買賣日`（兩個日期），第一個才是起日；
            #   但 TWTAUU 只給 `代號,恢復買賣日`（一個日期，2026-09-09 探針實測
            #   `'3040  ,20150204'`）。只取 digits[0] 的話，單日期那種會把
            #   **恢復買賣日誤標成停止買賣起日**——欄位名對、數字合法、不會報錯。
            if len(digits) >= 2:
                halt[str(r[i_code]).strip()] = (
                    f"{digits[0][:4]}-{digits[0][4:6]}-{digits[0][6:]}")
    out = [row + [halt.get(row[1], "")] for row in rows]
    miss = sum(1 for row in out if not row[-1])
    if miss:
        note += f"（{miss} 列抽不到停止買賣起日）"
    return out, note


def _pick_stock_table(tabs, *codenames):
    """多張表時挑「有代號欄且欄數最多」那張。融資融券與三大法人的回應
    第一張多半是全市場彙總（3 列），個股在第二張。"""
    best, bf = None, None
    for t in tabs:
        f = _fieldmap(t)
        if _exact(f, *codenames) is not None and (bf is None or len(f) > len(bf)):
            best, bf = t, f
    return best, bf


def _margin_rows(t, day, known, idx, tag):
    """共用的融資融券輸出與驗算。

    ★ 這裡有一條**免費的恆等式**，一定要驗：
      `今日餘額 = 前日餘額 + 買進 − 賣出 − 現償`（融券的買賣方向相反）。
      位置定位一旦錯位，這條會整片不符——**它就是位置對不對的檢驗**。
      不符的列丟掉並計數，不要靜默寫進去。
    """
    out, bad, samples = [], 0, []
    g = lambda r, i: _blank_num(r[i]) if (i is not None and i < len(r)) else ""
    # ⛔ `note` 是**文字**（`O`／`X`／`@`／`%`／`!`），不可以走 `_blank_num`
    #   ——那支是給數字用的，會把整欄清成空字串，而且不會有人發現。
    gt = lambda r, i: (str(r[i]).strip() if (i is not None and i < len(r)) else "")
    n = lambda v: float(str(v).replace(",", "")) if str(v).strip() not in ("", "-") else 0.0
    for r in (t.get("data") or []):
        if not r or len(r) <= idx["code"]:
            continue
        code = str(r[idx["code"]]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        vals = {k: g(r, i) for k, i in idx.items() if k not in ("code", "note")}
        vals["note"] = gt(r, idx.get("note"))
        try:
            # 融資：今日 = 前日 + 買 − 賣 − 現償
            okm = abs(n(vals["m_prev"]) + n(vals["m_buy"]) - n(vals["m_sell"])
                      - n(vals["m_ret"]) - n(vals["m_balance"])) <= 1
            # 融券：今日 = 前日 + 賣 − 買 − 券償
            oks = abs(n(vals["s_prev"]) + n(vals["s_sell"]) - n(vals["s_buy"])
                      - n(vals["s_ret"]) - n(vals["s_balance"])) <= 1
        except (ValueError, KeyError):
            bad += 1
            samples.append((code, "數字轉不動或缺欄"))
            continue
        if not (okm and oks):
            bad += 1
            # ⭐ 講清楚**是融資那條還是融券那條**不符：兩者的成因不一樣。
            which = ("融資" if not okm else "") + ("融券" if not oks else "")
            samples.append((code, f"{which}恆等式不符"
                                  f"｜資 前{vals['m_prev']}+買{vals['m_buy']}"
                                  f"-賣{vals['m_sell']}-償{vals['m_ret']}"
                                  f"≠{vals['m_balance']}"
                                  f"｜券 前{vals['s_prev']}+賣{vals['s_sell']}"
                                  f"-買{vals['s_buy']}-償{vals['s_ret']}"
                                  f"≠{vals['s_balance']}"))
            continue
        # ★★ 2026-09-09 補存 `m_prev/m_ret/s_prev/s_ret`（前日餘額與現／券償）。
        #   ⚠ 這四欄**本來就已經解析出來了**，只是沒寫出去——上面那條恆等式就在用它們。
        #   ⛔ 為什麼不能用「昨天的今日餘額」回推、非補不可？**因為量過了**：
        #     `現償 = 昨日餘額 + 買 − 賣 − 今日餘額` 這樣代換，
        #     margin 有 4,574 列、otcmargin 有 3,205 列會算出**負的現償**
        #     ⇒ 代換一定錯（這還只是下限：算出非負的不代表對）。
        #   ⚠ 我原本的假說是「那些是除權息調整日」——**假說被自己的資料推翻了**：
        #     落在該檔 adj 事件日的只有 2.95%／2.78%（負控 0.37%／0.41%）。
        #     ⇒ 有統計上真的關聯，但**只解釋得了 3%**，其餘 97% 原因不明。
        #   ⭐ 結論：這兩組數字是**真的遺失資訊**，不是可推導的冗餘欄。
        #   ★ 新欄一律**接在舊表頭後面**，讓舊檔的表頭是新表頭的前綴——
        #     transpose 才有辦法在回補進行到一半時仍然合併得起來（見那支的說明）。
        # ⭐⭐ 2026-09-10 新增 `note`（官方註記欄），K線線排最高優先。
        #   ⛔ 它不是清潔工作——**它會讓一批負面訊號被讀成正面訊號**：
        #     官方 `O` ＝ **停止融資買進**（停的是新增，既有餘額還在）
        #     ⇒ 那一檔的「融資餘額低、且持續下降」不是槓桿出清，
        #       是**被官方掐住信用交易**（波動過劇／股權過度集中）。
        #     兩者在數字上長得一模一樣，方向完全相反。
        #   ⚠ 而它專打**飆股**——被停止融資的往往正是波動最大、
        #     也最需要看融資水位的那一群。
        #   ⛔ 這一欄**照官方原文存**，不解析、不翻譯、不補空白：
        #     兩張表的符號集不同（`X` 在 `MI_MARGN` 是停止融券、
        #     在 `TWT93U` 是停券），在這裡翻譯就等於把某一天的解讀寫死。
        #   ⛔⛔ 而且 TWSE 的這一欄講的是**次一營業日**（官方明文，
        #     見 `docs/READ_CONTRACT.md`）——⚠ 那是**讀取端**要處理的偏移，
        #     ⛔ 不可以在這裡先移一天：移了就分不出「官方那天說的」
        #     與「我方推的」，而官方若改口，也追不回來。
        out.append([day, code, vals["m_buy"], vals["m_sell"], vals["m_balance"],
                    vals["m_limit"], vals["s_buy"], vals["s_sell"], vals["s_balance"],
                    vals["m_prev"], vals["m_ret"], vals["s_prev"], vals["s_ret"],
                    vals.get("note", "")])
    return out, _drop_note(len(out), tag, bad, samples)


def parse_margin(d, day, known=None):
    """TWSE MI_MARGN 個股融資融券。

    ★★ **欄名重複，只能用位置。** 2026-09-04 Actions 實測的個股表欄位：

        代號,名稱,買進,賣出,現金償還,前日餘額,今日餘額,次一營業日限額,
                 買進,賣出,現券償還,前日餘額,今日餘額,次一營業日限額,資券互抵,註記

    融資與融券**用同一組欄名**，`_exact()` 只會回第一個命中——
    融券會整片取到融資的值。這是 T86 那次「16,394 列驗算不符」的同一種病
    （那次是互相包含，這次是完全重複），**名字定位在這裡救不了**。

    用位置就必須有守衛，否則官方改版會靜默錯位：
      ① 欄數必須剛好 16 ② 第 2 欄與第 8 欄都必須是「買進」
      ③ 第 4 欄「現金償還」、第 10 欄「現券償還」
      ④ 最後靠餘額恆等式逐列驗算
    任何一條不符就整張表拒收並回報欄名，**不要猜著往下走**。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t, f = _pick_stock_table(tabs, "代號", "股票代號", "證券代號")
    if t is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(x) for x in tabs]}"
    # ⛔ `f[15] != "註記"` 是 2026-09-10 加的第五條守衛：`note` 一樣靠位置取，
    #   而它取錯的失敗方式最安靜——存進去的是「資券互抵」的數字，
    #   看起來就只是「這一欄大部分是空的」。
    if len(f) != 16 or f[2] != "買進" or f[8] != "買進" \
            or f[4] != "現金償還" or f[10] != "現券償還" or f[15] != "註記":
        return [], (f"欄位結構與 2026-09-04 實測不符，拒收（避免位置錯位）：{f}")
    idx = {"code": 0,
           "m_buy": 2, "m_sell": 3, "m_ret": 4, "m_prev": 5, "m_balance": 6, "m_limit": 7,
           "s_buy": 8, "s_sell": 9, "s_ret": 10, "s_prev": 11, "s_balance": 12,
           "note": 15}
    return _margin_rows(t, day, known, idx, "TWSE 位置定位")


def parse_otcmargin(d, day, known=None):
    """TPEx 融資融券。**欄名不重複，可以用名字**（與 TWSE 不同，所以分開寫）。

    2026-09-04 Actions 實測欄位：
        代號,名稱,前資餘額(張),資買,資賣,現償,資餘額,資屬證金,資使用率(%),資限額,
                 前券餘額(張),券賣,券買,券償,券餘額,券屬證金,券使用率(%),券限額,
                 資券相抵(張),備註

    ★ 注意券的欄序是「**券賣在券買之前**」——照名字取就不會受影響，
      但這也是為什麼這裡不沿用 TWSE 那套位置。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t, f = _pick_stock_table(tabs, "代號", "股票代號", "證券代號")
    if t is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(x) for x in tabs]}"
    need = {"code": ("代號", "股票代號", "證券代號"),
            "m_prev": ("前資餘額(張)",), "m_buy": ("資買",), "m_sell": ("資賣",),
            "m_ret": ("現償",), "m_balance": ("資餘額",), "m_limit": ("資限額",),
            "s_prev": ("前券餘額(張)",), "s_sell": ("券賣",), "s_buy": ("券買",),
            "s_ret": ("券償",), "s_balance": ("券餘額",)}
    idx = {k: _exact(f, *names) for k, names in need.items()}
    missing = [k for k, v in idx.items() if v is None]
    # ⛔ `備註` 單獨處理、**不放進 `need`**：need 缺一個就整張表拒收，
    #   而這一欄是新加的 ⇒ 官方哪天改欄名就會讓一整條 feed 停掉。
    #   ⚠ 反過來也要看得見：取不到時留空，並在 note 訊息裡講出來，
    #     ⛔ 不可以靜靜地整欄空白（那跟「今天大家都沒有註記」長得一樣）。
    idx["note"] = _exact(f, "備註", "註記")
    if missing:
        return [], f"欄位對不上，缺 {missing}：{f}"
    tag = "TPEx 名稱定位" + ("" if idx["note"] is not None
                          else "；⚠ **找不到「備註」欄，note 整欄留空**")
    return _margin_rows(t, day, known, idx, tag)


def parse_otcinst(d, day, known=None):
    """TPEx 上櫃三大法人。**兩個年代的欄位完全不同，先試名稱、再退位置。**

    ── 舊版（2015 實測，16 欄，**欄名不重複**）──────────────────
        代號, 名稱,
        外資及陸資買股數, 外資及陸資賣股數, **外資及陸資淨買股數**,
        投信買進股數, 投信賣股數, **投信淨買股數**,
        **自營淨買股數**,                      ← 合計，單獨一欄
        自營商(自行買賣)買/賣/淨買股數,
        自營商(避險)買/賣/淨買股數,
        **三大法人買賣超股數**

    ── 新版（2026-09-03 實測，24 欄，**欄名重複七次**）───────────
        代號, 名稱, ①②③④⑤⑥⑦ 各三欄（買進/賣出/買賣超）, 三大法人買賣超股數合計
        七組依序為：①外資及陸資(不含外資自營商) ②外資自營商 **③外資合計**
                    **④投信** ⑤自營商(自行買賣) ⑥自營商(避險) **⑦自營商合計**

    **名稱定位優先。** 舊版欄名互不重複，用名字就對得到，比位置安全得多；
    新版欄名全是「買賣超股數」，名字對不到才退到位置。

    ★ 兩條路都要取**合計欄不是分項**。T86 那次就是把自營商取成避險分項——
      2018-01-03 玉山金合計 224,000、避險只有 104,000，**取錯少一半**。

    ★ 恆等式 外資 ＋ 投信 ＋ 自營 ＝ 合計 是最後的檢驗。
      不論走哪條路，對應錯了就會整片不符、整批丟棄並回報，
      **不會靜默寫進錯的數字**。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t, f = _pick_stock_table(tabs, "代號", "股票代號", "證券代號")
    if t is None:
        return [], f"找不到含代號欄的表；各表欄名={[_fieldmap(x) for x in tabs]}"

    # ── 路一：名稱定位（舊版欄名不重複時走這條）──
    i_code = _exact(f, "代號", "股票代號", "證券代號")
    i_fo = _exact(f, "外資及陸資淨買股數", "外資及陸資買賣超股數", "外資買賣超股數")
    i_tr = _exact(f, "投信淨買股數", "投信買賣超股數")
    i_dl = _exact(f, "自營淨買股數", "自營商淨買股數", "自營商買賣超股數")
    i_tt = _exact(f, "三大法人買賣超股數", "三大法人買賣超股數合計", "三大法人淨買股數")
    how = None
    if None not in (i_code, i_fo, i_tr, i_dl, i_tt):
        how = "名稱定位"
    else:
        # ── 路二：位置定位（新版欄名重複，名字救不了）──
        if len(f) != 24 or "三大法人" not in f[-1]:
            return [], (f"欄位既對不上名稱、結構也與 2026-09-04 實測的 24 欄不符，"
                        f"拒收（避免位置錯位）：{f}")
        if not all(f[i] == "買賣超股數" for i in (4, 10, 22)):
            return [], f"買賣超欄不在預期位置，拒收：{f}"
        i_code, i_fo, i_tr, i_dl, i_tt = 0, 10, 13, 22, 23
        how = "位置定位（24 欄新版）"

    out, bad, samples = [], 0, []
    g = lambda r, i: float(B._num(r[i]) or 0) if i < len(r) else 0.0
    for r in (t.get("data") or []):
        if not r or len(r) <= max(i_code, i_tt):
            continue
        code = str(r[i_code]).strip()
        if not code or not code[0].isdigit():
            continue
        if known and code not in known:
            continue
        fo, tr, dl, tt = g(r, i_fo), g(r, i_tr), g(r, i_dl), g(r, i_tt)
        if abs(fo + tr + dl - tt) > 1:
            bad += 1
            samples.append((code, f"外{fo:.0f}+投{tr:.0f}+自{dl:.0f}"
                                  f"≠合計{tt:.0f}（差 {fo + tr + dl - tt:+.0f}）"))
            continue
        out.append([day, code, f"{fo:.0f}", f"{tr:.0f}", f"{dl:.0f}", f"{tt:.0f}"])
    return out, _drop_note(len(out), how, bad, samples)


# ────────────────────────────────────────────────────────────
# feed 定義
# ────────────────────────────────────────────────────────────

def _paren(v):
    """『587(19)』→ ('587', '19')。沒有括號就回 (值, '')。"""
    t = str(v).strip()
    if "(" in t and t.endswith(")"):
        main, _, rest = t.partition("(")
        return _blank_num(main), _blank_num(rest[:-1])
    return _blank_num(t), ""


def parse_breadth(d, day, known=None):
    """TWSE MI_INDEX → 當天上市的漲跌證券數（大盤層級彙總）。

    ★ 這是**日檔的外部判準**：日檔由個股端點建，這張表由大盤端點來，
      兩條不同的路。整批漏抓時日檔家數會掉、這裡不會。
      判讀方式見 `breadth_audit.py`。

    ⛔ **一律取「股票」那一欄，不是「整體市場」**——後者含權證與 ETF，
      拿它跟日檔的普通股比會多出好幾千，差值整個沒有意義。
      （這一條與 `fetch.py` 的當日版本同一個判準，不可分岔。）

    ⚠ MI_INDEX 一個回應塞好幾張表（`B._tables()` 已處理三種形狀），
      **不可以假設資料在第一張**——第二條坑就是這樣來的。
    """
    tabs = B._tables(d)
    if not tabs:
        return [], "沒有 tables"
    t = None
    for x in tabs:
        f = [str(y) for y in (x.get("fields") or [])]
        labels = " ".join(str(r[0]) for r in (x.get("data") or []) if r)
        if "股票" in f and ("上漲" in labels or "漲跌證券數" in str(x.get("title", ""))):
            t = x
            break
    if t is None:
        return [], f"找不到漲跌證券數那張表（共 {len(tabs)} 張）"
    f = [str(y) for y in (t.get("fields") or [])]
    col = f.index("股票")
    v = {"up": "", "down": "", "flat": "", "lu": "", "ld": ""}
    for r in (t.get("data") or []):
        if not r or len(r) <= col:
            continue
        lab = str(r[0])
        main, paren = _paren(r[col])
        if "上漲" in lab:
            v["up"], v["lu"] = main, paren
        elif "下跌" in lab:
            v["down"], v["ld"] = main, paren
        elif "持平" in lab or "平盤" in lab:
            v["flat"] = main
    if not (v["up"] and v["down"]):
        return [], f"表找到了但取不到值：{[str(r[0]) for r in (t.get('data') or [])][:6]}"
    return ([[day, v["up"], v["down"], v["flat"], v["lu"], v["ld"]]],
            f"漲 {v['up']}／跌 {v['down']}／平 {v['flat']}")


def _twse(path, day, extra=""):
    return f"https://www.twse.com.tw/rwd/zh/{path}?date={day.replace('-', '')}{extra}&response=json"


def _tpex(path, day, extra="", roc=False):
    """TPEx 端點。⚠ `roc=True` 送**民國**斜線（`115/09/10`）。

    ⛔ 同一站的日期格式**不是一致的**：`margin/balance` 這幾支吃西元斜線，
    而 `afterTrading/chtm` 我方實測用的是民國斜線。
    ⚠ 送錯格式在這一站是**靜默**的（第二條規矩的第①種），
      ⇒ ⛔ 不要「推論它應該也吃西元」——實測過哪一種就送哪一種。
      （真的送錯時 `fetch_one` 的 `_same_day` 還會擋一層，但那是第二道，不是第一道。）
    """
    d = (f"{int(day[:4]) - 1911:03d}/{day[5:7]}/{day[8:10]}" if roc
         else day.replace("-", "/"))
    return f"https://www.tpex.org.tw/www/zh-tw/{path}?date={d}{extra}&response=json"


FEEDS = {
    # ── 已驗證 ──────────────────────────────────────────────
    "breadth": {
        "dir": "breadth",
        "header": ["date", "up", "down", "flat", "limit_up", "limit_down"],
        "parse": parse_breadth,
        "known": False,          # 這是大盤合計，沒有個股代號要過濾
        "urls": lambda day: [_twse("afterTrading/MI_INDEX", day,
                                   "&type=ALLBUT0999")],
        "status": ("大盤漲跌證券數，**日檔的外部判準**。MI_INDEX 吃 date 參數，"
                   "所以 2015 起可以回補——`market_breadth.csv` 只有 2026-09-01 起，"
                   "是 v6 才開始存的，不是端點沒有歷史"),
    },
    "per": {
        "dir": "per",
        "header": ["date", "stock_id", "close", "yield_pct", "dividend_year",
                   "per", "pbr", "fs_quarter"],
        "parse": parse_per,
        "known": True,
        "urls": lambda day: [_twse("afterTrading/BWIBBU_d", day, "&selectType=ALL")],
        "status": "已驗證 2026-09-04：20260903 → stat=OK、1,580 列",
    },
    # ⭐ 2026-09-10 新增。它取代的是一條**猜的**判準（名稱後綴 `-創`／`KY創`）。
    #   ⛔ 存逐日不存現況：K線線的判準是「問的是它**現在**是什麼、
    #     還是它**那時候**是什麼」——圈歷史區間要的是那一天的成分。
    "tib": {
        "dir": "tib",
        "header": ["date", "stock_id", "name"],
        "parse": parse_tib,
        # ⛔ known=False：創新板有下市／轉板的，先全收，篩母體是讀取端的事。
        "known": False,
        "urls": lambda day: [_twse("afterTrading/STOCK_TIB", day)],
        "status": ("市場情報分析線 2026-09-10 實測：2026-09-09 回 31 列"
                   "＝ 30 檔 ＋ 1 列「合計」，與名稱後綴法**兩個方向都 0 差異**。"
                   "⛔ 歷史下限 **2021-06-28**，越界時官方明說"
                   "（`stat:\"查詢日期小於110年6月28日，請重新查詢!\"`）"
                   "——**大聲失敗，不是靜默回最新**"),
    },
    # ⭐ 借券賣出。K線線 15:45 的第一優先——融券只佔空方 1.4%。
    #   ⚠ 欄名前綴：`s_*` 是這張表的**融券**段（總量管制視角，⛔ 與 `margin` feed 不同口徑），
    #     `sbl_*` 是**借券賣出**段。`sbl_balance` 才是 K線線要的那一個。
    #   ⛔ `sbl_limit`（次一營業日可借券賣出限額）**不是餘額**，兩者不可互換（K線線 Q2）。
    "sbl": {
        "dir": "sbl",
        "header": ["date", "stock_id",
                   "s_prev", "s_sell", "s_buy", "s_ret", "s_balance", "s_limit",
                   "sbl_prev", "sbl_sell", "sbl_return", "sbl_adj",
                   "sbl_balance", "sbl_limit", "note"],
        "parse": parse_sbl,
        "known": False,
        "urls": lambda day: [_twse("marginTrading/TWT93U", day)],
        "status": ("實測 2026-09-09（Actions）：stat=OK、**total=1302 與解析列數一致**、"
                   "15 欄兩段。⭐ 段落邊界照官方 `groups` 取，不寫死。"
                   "⚠ 每日晚間**二次更新**（約 20:30／22:30）"
                   "⇒ 排程落在兩次之間會拿到不完整的版本，而它看起來完全正常"),
    },
    "otcsbl": {
        "dir": "otcsbl",
        "header": ["date", "stock_id",
                   "s_prev", "s_sell", "s_buy", "s_ret", "s_balance", "s_limit",
                   "sbl_prev", "sbl_sell", "sbl_return", "sbl_adj",
                   "sbl_balance", "sbl_limit", "note"],
        "parse": parse_otcsbl,
        "known": False,
        "urls": lambda day: [_tpex("margin/sbl", day, "&id=")],
        "status": ("實測 2026-09-09（Actions）：stat=ok、932 列、15 欄。"
                   "⛔ **沒有 `groups`、沒有 `total`、沒有 `notes`** ⇒ "
                   "只能靠位置，欄名逐字比對是唯一的守衛"),
    },
    # ⭐ 變更交易（全額交割）。K線線 Q5——他們的閘門那一列從【不可執行】改回【可執行】靠這個。
    #   ⚠ `split_auction` = 官方 `**` 標示 ⇒ **併採分盤集合競價**（官方 notes 逐字，見上）
    #   ⛔ 那是「狀態」不是「成因」：處置股也會分盤，**兩個名單都要查**。
    "fulldelivery": {
        "dir": "fulldelivery",
        "header": ["date", "stock_id", "name", "split_auction"],
        "parse": parse_fulldelivery,
        "known": False,
        "urls": lambda day: [_twse("fullDelivery/TWT85U", day)],
        "status": ("實測 2026-09-09（Actions）：stat=OK、total 與列數一致、3 欄。"
                   "⭐ `date=` **是真的吃的**（2015-01-05 → 23 列、2020-01-03 → 21）"
                   "⇒ 可逐日回補；頁面年份選單最早到 2004"),
    },
    # ⭐⭐ 上市「停止買賣中」的即時名單。⛔ **沒有歷史**，漏抓一天永久少一天。
    #   ⚠ `known: False` 是**必要**的，不是省事：停止買賣中的個股正是
    #     「日檔已經沒有它」的那些 ⇒ 用母體濾會把它們全部濾掉。
    #   ⛔ `date=` 官方會忽略（K線線實測）⇒ 這一支**不可以**走區間回補，
    #     `cmd_feed` 只抓「今天」那一份；⚠ 而 `_same_day` 仍會擋一層。
    "stophalt": {
        "dir": "stophalt",
        "header": ["date", "stock_id", "name", "market",
                   "halt_since", "rule", "reason"],
        "parse": parse_stophalt,
        "known": False,
        "urls": lambda day: [_twse("violation/stop", day)],
        "status": ("⚠ **未經我方實測**（開發容器對交易所一律 403）。"
                   "K線分析線 2026-09-11 01:40 實測：`stat=ok`、5 欄、"
                   "`title=115年09月11日 停止買賣`；⛔ `date=` 被忽略 ⇒ 只有即時狀態。"
                   "⭐ 每一列附「停止買賣開始日期」⇒ 第一次抓到就能回推當下那一段。"),
    },
    # ⭐⭐ 上櫃分盤／變更交易／管理股票／停止交易。K線線 20:20 指名要「逐檔讀撮合週期」。
    #   ⚠ 上市**沒有**同等來源：只有 `TWT85U` 的 `**`（狀態）與 notes 那句
    #     「每 30 分鐘為原則、得公告調整」⇒ ⛔ 只知原則值，不知該檔實際值。
    #   ⚠ `known: False`——變更交易／管理股票的個股**可能不在我方母體裡**，
    #     ⛔ 用母體濾掉等於把最該被擋的那些濾掉。
    "chtm": {
        "dir": "chtm",
        "header": ["date", "stock_id", "name", "changed", "split_auction",
                   "managed", "match_cycle_min", "halted", "fin_watch"],
        "parse": parse_chtm,
        "known": False,
        # ⛔ 民國斜線（實測用的就是這個）。⚠ 送西元在這一站是**靜默**失敗。
        "urls": lambda day: [_tpex("afterTrading/chtm", day, roc=True)],
        "status": ("我方實測 2026-09-10（Actions）：`date` 回顯我請求的那一天、"
                   "10 欄、stat=ok。⭐ 歷史至少到 **2009**"
                   "（098/06/01 回 38 列、與今天逐位元組不同）"
                   "⇒ ⛔ 情報分析線說的「98/06/01 靜默回今天」不成立。"
                   "⚠ 旗標值是**全形 Ｙ**（U+FF39）；撮合時間是零填三位字串"),
    },
    # ⭐⭐ 個股融資融券成數的**調整幅度**（上市）。K線線那條 166.67 的個股面。
    #   ⛔ 它給的**不是現行成數**，是調整幅度 ⇒ 要逐檔彙總再用「基準 − 累計」推，
    #     ⚠ 而那是**判準**，屬 K線線 ⇒ 我方只存原始欄位，⛔ 不在這裡算。
    #   ⚠ `known: False`——被調成數的往往是**波動最大的飆股**，
    #     ⛔ 用母體濾掉等於把最該看的那些濾掉。
    "marginratio": {
        "dir": "marginratio",
        "header": ["date", "stock_id", "name", "reason", "adjust_from",
                   "restore_date", "margin_cut", "margin_cum",
                   "short_raise", "short_cum"],
        "parse": parse_marginratio,
        "known": False,
        "urls": lambda day: [
            _twse("marginTrading/BFIB9U", day,
                  extra=("&startDate={d}&endDate={d}&sortType=ALL&stockNo="
                         "&selectType=%E5%85%A8%E9%83%A8").format(
                             d=day.replace("-", "")))],
        "status": ("我方實測 2026-09-10（Actions）：不帶日期 471 列、"
                   "`20150105` 126 列 ⇒ **有逐日歷史**。"
                   "⛔ 一檔多列（471 列只有 94 個相異代號，一個原因一列）；"
                   "值有 `累計：N` 前綴；空值有『空字串』與『單一空白』兩種。"
                   "⭐ 日期**只寫在 `hints` 裡** ⇒ 本 parser 自己驗"),
    },
    "exright": {
        "dir": "exright",
        "header": ["date", "stock_id", "pre_close", "ref_price", "value",
                   "kind", "open_base"],
        "parse": parse_exright,
        "known": False,   # 除權息表會有已下市或非 universe 的標的，先全收
        # ★★ 2026-09-04 事故：原本用 `date=` 參數——**這支端點根本不吃 `date`**，
        #   但會把收到的 `date` 原樣放回 response，於是 `_same_day()` 被參數回音騙過，
        #   把 2026-09-07 的四列寫進 2015 年的每一個日期檔。
        #   實測 `date=20150123` 與 `date=20150716` 回的是同一批資料，
        #   標題都是「115年09月07日 至 115年09月07日」。
        #   正確參數是 **startDate / endDate**：
        #   `startDate=20150716&endDate=20150716` → stat=OK、標題「104年07月16日…」、30 列。
        #
        #   ★ 意外的好處：**它吃區間**，所以逐月抓一次即可，
        #     不必一天打一發。3,656 發 → 約 140 發。
        "range": True,
        "urls_range": lambda a, b: [
            "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"
            f"?startDate={a}&endDate={b}&response=json"],
        # 探測用的「已知有事件」區間：2015-07 是除權息旺季，一定回得到列。
        "probe_range": ("20150701", "20150731"),
        "status": ("已驗證 2026-09-04：startDate=20150716&endDate=20150716 → "
                   "stat=OK、30 列。**逐月抓**，日期取每列自己的「資料日期」欄"),
    },

    "reduce": {
        "dir": "reduce",
        "header": ["date", "stock_id", "pre_close", "ref_price", "reason",
                   "open_base", "ex_ref_price"],
        "parse": parse_reduce,
        "known": False,   # 減資表會有已下市或非 universe 的標的，先全收
        "range": True,
        # ★ **這是前瞻式公告表**：恢復買賣參考價在停止買賣期間就先公告，
        #   所以當月的回應會帶**未來日期**的列（2026-09-06 實測回到 115/09/29）。
        #   舊的 stray 檢查是 `a <= 日期 <= b`，b 取 min(月底, --end)，
        #   於是當月**整月被拒收**——2026-09 一列都沒寫進來。
        #
        #   ★★ 2026-09-06 二修：第一版讓它「照收未來列」，**那是錯的**。
        #     `data/universe/<feed>/<日期>.csv` 的意思是「那一天發生了什麼」，
        #     而還原因子的不變量是「**最新價的 F = 1，現價不動**」。
        #     收下 09/07 的減資，今天 1563 的收盤 66.00 會被一個**還沒發生**的
        #     事件還原成 84.66——報告上的價位就跟看盤軟體對不起來了。
        #     而且公告可能延期或取消，日檔會留在原地變成幽靈。
        #
        #   → `announce_ahead` 的正確語意是：**未來日期的列丟掉，但不因此拒收整月**，
        #     並在摘要把它們列出來（知道有減資要來是有用的，只是不進因子）。
        #     等事件日過了，下次跑同一個月自然就收進來。
        "announce_ahead": True,
        # ★ 2026-09-06 用 WebFetch 實測（工具要標明——見 READ_CONTRACT 的教訓）：
        #   `startDate=20150101&endDate=20151231` → stat=OK、
        #   title「104年01月01日 至 104年12月31日 股票減資恢復買賣參考價格」、**26 列**，
        #   首列 104/01/23 3040 遠見 31.90 → 41.28「退還股款」。
        #   **有歷史，2015 年以來補得回來**，不是只有前瞻十日的公告表。
        #   回應是平的（沒有 tables），有 strDate／endDate，`_same_day` 擋得住參數回音。
        #
        #   ⚠ **沒有事件的月份回 `{"stat":"很抱歉，沒有符合條件的資料!"}`**——
        #   沒有 title、沒有 data。減資本來就少（一年 20~30 件），
        #   多數月份都是這個回應。`cmd_feed_range` 已把它認成「無事件」而不是失敗，
        #   否則會報成七成的月份都失敗，真的失敗就被雜訊蓋掉。
        #
        #   ※ TWTB8U 是**變更股票面額**恢復買賣參考價，是另一種公司行動，不要混用。
        "urls_range": lambda a, b: [
            "https://www.twse.com.tw/rwd/zh/reducation/TWTAUU"
            f"?startDate={a}&endDate={b}&response=json"],
        # ★ 探測用的「已知有事件」區間。**減資一年只有 20~30 件**，
        #   隨便挑一天去探幾乎一定回「查無資料」——那不是端點壞掉。
        #   2015 全年實測 26 列，拿它當探測基準才驗得到「解析得出來」。
        "probe_range": ("20150101", "20151231"),
        "status": ("已驗證 2026-09-06（WebFetch）：2015 全年 26 列、2026 上半年 2 列。"
                   "**逐月抓**，日期取每列自己的「恢復買賣日期」欄（格式 115/09/07）"),
    },

    # ★★ 變更股票面額恢復買賣參考價。2026-09-09 00:30 於 Actions 驗到，
    #   四項判準全過（`parvalue_probe.py` → `data/meta/_parvalue_probe.txt`）：
    #     [1] stat=OK、title「變更股票面額恢復買賣參考價格」
    #     [2] 9 欄完整
    #     [3] 三個區間列數不同（0／1／2）
    #     [4] 日期欄 109/08/17、115/01/19 ~ 115/09/07 → **有歷史**
    #   而且**參數確定有生效**（三個區間回不同內容，不是 TWT49U 那種參數回音）。
    #
    #   ★ 官方回的數字與 `parvalue_scan.py` 的全庫掃描**逐格對上**：
    #     109/08/17 8070 長華 停止買賣前收盤 190.00 → 恢復買賣參考價 19.00
    #       掃描：8070 T=2020-08-17，前一次有成交收 190 → 復牌收 20.90
    #     115/01/19 7780 大研生醫 185.00 → 18.50
    #       掃描：7780 T=2026-01-19，185 → 20.35
    #   **前收盤兩邊一模一樣**，官方因子 19/190 ＝ 18.5/185 ＝ 0.10（面額 10→1）。
    #   掃描的比值 0.110 略高，差的是停止買賣那 7~8 天的漲跌——
    #   所以**因子要用官方的 ref/pre，不是用價格比值**。
    #
    #   ⚠ 這張表**只涵蓋上市**。上櫃 14 筆（6548、5314、5904…）還沒有來源，
    #     TPEx 的對應端點尚未找到——`db_status` 那條缺口只收掉一半。
    #
    #   欄位是 TWTAUU 的子集（少了「減資原因」與「除權參考價」），
    #   `parse_reduce` 的 `_exact` 找不到就給空字串，所以**沿用它、不另寫解析**：
    #   多一份幾乎一樣的解析程式＝多一處會各自飄移的地方。
    "parvalue": {
        "dir": "parvalue",
        # ★ 比減資多一欄 `halt_date`＝**停止買賣起日**（取自官方「詳細資料」欄）。
        #   `suspend.csv` 收的是暫停交易、不含換發新股票的停止買賣，
        #   24 筆面額變更拿去對它 `resume_date` 命中 0 筆——
        #   **丟掉這一欄，那段區間整個資料庫就沒有第二個地方查得到。**
        #   恢復買賣日不另存：它就是第一欄 `date`。
        "header": ["date", "stock_id", "pre_close", "ref_price", "reason",
                   "open_base", "ex_ref_price", "halt_date"],
        "parse": parse_parvalue,
        "known": False,
        "range": True,
        "announce_ahead": True,     # 與減資同一張形態的前瞻公告表
        "urls_range": lambda a, b: [
            "https://www.twse.com.tw/rwd/zh/change/TWTB8U"
            f"?startDate={a}&endDate={b}&response=json"],
        # 面額變更比減資更少（全庫 2015 起上市只有 10 筆），
        # 隨便挑一個月去探幾乎一定空手——拿 2020 全年當基準（實測 1 列）。
        "probe_range": ("20200101", "20201231"),
        "status": ("已驗證 2026-09-09（Actions probe）：2015 全年 0 列、"
                   "2020 全年 1 列（8070 長華）、2026 至今 2 列（7780、6949）。"
                   "**只有上市**，上櫃無對應端點"),
    },

    # ★★ ETF 分割／反分割恢復買賣參考價。端點由使用者 2026-09-09 查到並提供，
    #   **非自行生成**。與 TWTAUU／TWTB8U 是同一張形態（恢復買賣參考價表）。
    #
    #   ★ 資料庫線獨立重算過（規矩一：數字有爭議由這邊重算）——**11/11 全中**：
    #     對方點名 00632R、00676R、00663L、0050、0052、00674R、00673R、
    #     00706L、00685L、00631L、00715L；
    #     `parvalue_scan.py` 掃到「無事件可解釋且在 industry.csv 母體外」的
    #     19 筆命中裡，這 11 檔一檔不差，**沒有對方有我沒有的**。
    #
    #   ★★ 而且「隔幾個交易日」把三群分得乾乾淨淨，互不重疊：
    #         分割／反分割（本表）        隔 5~6 天   11 筆
    #         境外成分 ETF（無漲跌幅限制）  隔 1 天      4 筆  ← 真實交易，不是事件
    #         長期停牌後復牌（成因未查）    隔 38~687 天  4 筆
    #     ⛔ 中間那一群**不可以**當成事件去還原：00672L、00887 那幾筆是
    #       追蹤國外標的的 ETF 沒有漲跌幅限制，單日真的可以跳 ±85%。
    #
    #   ⚠ 欄位尚未實測（我方容器對 twse 是 403）。沿用 `parse_parvalue`：
    #     它用**欄名**查（`_exact`），對不上會回「欄位對不上：{實際欄名}」
    #     而不是寫進錯的數字——**失敗形態是自己說出來，不是靜默寫錯**。
    "etfsplit": {
        "dir": "etfsplit",
        "header": ["date", "stock_id", "pre_close", "ref_price", "reason",
                   "open_base", "ex_ref_price", "halt_date"],
        "parse": parse_parvalue,
        "known": False,           # ETF 不在 industry.csv 母體裡，一定要全收
        "range": True,
        "announce_ahead": True,
        "urls_range": lambda a, b: [
            "https://www.twse.com.tw/rwd/zh/split/TWTCAU"
            f"?startDate={a}&endDate={b}&response=json"],
        "probe_range": ("20250101", "20251231"),   # 實測那年有 5 筆
        "status": ("端點由使用者 2026-09-09 提供；資料庫線以全庫掃描交叉核對 11/11 全中。"
                   "**欄位待第一趟 Actions 實測**"),
    },

    # ── 未驗證，候選清單 ────────────────────────────────────
    "margin": {
        "dir": "margin",
        # ★ 後四欄 2026-09-09 新增，⛔ **一定要接在最後**（見 `_margin_rows`）。
        "header": ["date", "stock_id", "m_buy", "m_sell", "m_balance", "m_limit",
                   "s_buy", "s_sell", "s_balance",
                   "m_prev", "m_ret", "s_prev", "s_ret", "note"],
        "parse": parse_margin,
        "known": True,
        "urls": lambda day: [_twse("marginTrading/MI_MARGN", day, "&selectType=ALL")],
        "status": ("已驗證 2026-09-04（Actions）：stat=OK、2 表，個股在第二張、16 欄。"
                   "★ 開發環境打同一條回「沒有符合條件的資料」，Actions 上正常——"
                   "**端點可用性要在 Actions 上判定**"),
    },
    "otcinst": {
        "dir": "otcinst",
        "header": ["date", "stock_id", "foreign", "trust", "dealer", "total"],
        "parse": parse_otcinst,
        "known": True,
        "urls": lambda day: [_tpex("insti/dailyTrade", day, "&type=Daily&sect=EW&id=")],
        "status": "已驗證 2026-09-04（Actions）：stat=ok、900 列、24 欄（七組買賣超＋合計）",
    },
    "otcper": {
        "dir": "otcper",
        "header": ["date", "stock_id", "close", "yield_pct", "dividend_year",
                   "per", "pbr", "fs_quarter"],
        "parse": parse_per,
        "known": True,
        "urls": lambda day: [_tpex("afterTrading/peQryDate", day, "&id=")],
        "status": ("已驗證 2026-09-04（Actions）：stat=ok、886 列。"
                   "★ **沒有收盤價欄**，close 一律留空（不是 0）"),
    },
    "otcmargin": {
        "dir": "otcmargin",
        # ★ 後四欄 2026-09-09 新增，⛔ **一定要接在最後**（見 `_margin_rows`）。
        "header": ["date", "stock_id", "m_buy", "m_sell", "m_balance", "m_limit",
                   "s_buy", "s_sell", "s_balance",
                   "m_prev", "m_ret", "s_prev", "s_ret", "note"],
        "parse": parse_otcmargin,
        "known": True,
        "urls": lambda day: [_tpex("margin/balance", day, "&id=")],
        "status": "已驗證 2026-09-04（Actions）：stat=ok、920 列、20 欄（欄名不重複，用名稱定位）",
    },
    "otcexright": {
        "dir": "otcexright",
        "header": ["date", "stock_id", "pre_close", "ref_price", "value",
                   "kind", "open_base"],
        "parse": parse_exright,
        "known": False,
        # ★ 2026-09-04 兩批共 10 條候選的結果：
        #   afterTrading/* 與 exright/* 全部 404（同一張 TPEx 404 頁）。
        #   **唯一有回應的是 `bulletin/revivt`**——stat=ok，但那是
        #   「減資恢復買賣參考價」不是除權息，而且回的是**未來十天**
        #   （20260905~20260914），被 `_same_day` 擋下。
        #
        #   兩個推論：
        #   ① **`bulletin` 才是公司行動類的區段名**，前兩批猜錯方向。
        #   ② TPEx 這類表可能是**前瞻式公告表**，不是 TWSE `TWT49U` 那種逐日結果表。
        #      若是如此，**逐日 feed 的框架對它是錯的**——要改成
        #      「定期抓一次、依事件自身日期累積」，不能用 `_same_day` 核對。
        #      所以下面這批若有一條回 stat=ok 但日期不符，**那多半就是它**，
        #      要改框架而不是繼續換網址。
        "urls": lambda day: [
            _tpex("bulletin/exRight", day, "&id="),
            _tpex("bulletin/exRightResult", day, "&id="),
            _tpex("bulletin/exDividend", day, "&id="),
            _tpex("bulletin/exRightDividend", day, "&id="),
            _tpex("bulletin/exRightAndDividend", day, "&id="),
            _tpex("bulletin/exRightCalc", day, "&id="),
        ],
        "status": ("**未驗證**。第一、二批共 10 條：afterTrading/* 與 exright/* 全 404，"
                   "只有 bulletin/revivt 有回應但那是減資表且為前瞻式。"
                   "第三批集中在 bulletin/*"),
    },
}


def feed_dir(name):
    return os.path.join(UNI_DIR, FEEDS[name]["dir"])


# ────────────────────────────────────────────────────────────
# 通用逐日回補
# ────────────────────────────────────────────────────────────

def write_day(name, day, lines):
    if not lines:
        return 0
    d = feed_dir(name)
    os.makedirs(d, exist_ok=True)
    # ⛔ 寫之前先驗寬度：少一格會讓後面每一欄**整片左移**，⚠ 而且不報錯。
    #   ⭐ 判準只有一份（`fetch.assert_row_width`），15 個 feed 共用它。
    _F.assert_row_width(FEEDS[name]["header"], lines, f"{name}/{day}")
    with open(os.path.join(d, f"{day}.csv"), "w", encoding="utf-8") as f:
        f.write(",".join(FEEDS[name]["header"]) + "\n")
        for r in sorted(lines, key=lambda r: r[1]):
            f.write(",".join(r) + "\n")
    return len(lines)


def fetch_one(name, day, known):
    """回 (lines, note, used_url)。候選依序試，第一個通過 _same_day 的就用。"""
    spec = FEEDS[name]
    if spec.get("range"):
        return [], "這是區間型 feed，應走 cmd_feed_range", None
    # ⛔⛔ 情報分析線 2026-09-10 要了兩次的東西：**失敗時要附上實際打出去的 URL**。
    #   `feeds:tib` 那條的狀態檔只寫「回了 0 列」，沒說打的是哪一支端點
    #   ⇒ 他們得自己去驗 `STOCK_TIB` 才敢說是接線問題。
    #   ⚠ 而候選是**一串**，「哪一支失敗了」跟「失敗成什麼樣」一樣重要。
    #   ⭐ 同一族的第三次：會叫、但叫不出**哪裡**，代價一樣是一整個來回。
    last = "沒有候選"
    for url in spec["urls"](day):
        raw, err = B.get(url)
        # 只留路徑與參數，⛔ 不印整串（`_last_run.md` 是給人看的）
        u_ = url.split("//", 1)[-1][:140]
        if err:
            last = f"失敗({err[:50]})｜URL={u_}"
            continue
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception as ex:                       # noqa: BLE001
            head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
            last = f"JSON {type(ex).__name__}｜{len(raw)}B｜開頭：{head}｜URL={u_}"
            continue
        stat = d.get("stat") if isinstance(d, dict) else None
        if stat and str(stat).strip().lower() not in ("ok", "success"):
            last = f"stat={stat}｜URL={u_}"
            continue
        # ★ 日期核對是防「只回今天」的最後一道閘。不可為了讓某個候選通過而拿掉。
        same, said = B._same_day(d, day)
        if not same:
            last = f"日期不符({said})｜URL={u_}"
            continue
        lines, nt = spec["parse"](d, day, known if spec["known"] else None)
        return lines, nt, url
    # NODATA 代表「端點答了、只是那天沒有資料」——回傳 url 讓呼叫端歸到「休市」。
    if last.startswith("NODATA"):
        return [], last[7:], (spec["urls"](day) or [None])[0]
    return [], last, None


def _months(start, end):
    """→ [(該月起日, 該月迄日)]，兩端都夾在 [start, end] 內。"""
    import calendar
    y, m = int(start[:4]), int(start[5:7])
    out = []
    while True:
        last = calendar.monthrange(y, m)[1]
        a = max(f"{y:04d}-{m:02d}-01", start)
        b = min(f"{y:04d}-{m:02d}-{last:02d}", end)
        if a > end:
            break
        if a <= b:
            out.append((a, b))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def load_ledger(path):
    """讀一份台帳 JSON → dict。⛔ 壞掉／不存在都回 `{}`（不要因為台帳停擺）。

    ⭐ **只有這一份實作**（CLAUDE.md 四點五）：逐月那支（`cmd_feed_range`）
      與逐日那支（`cmd_feed`）共用。⚠ 原本逐月那支在函式裡就地 `json.load`，
      ⛔ 而逐日那支**根本沒有台帳**——「同一件事只做了一半」的第七次。
    """
    if not os.path.exists(path):
        return {}
    try:
        return json.load(io.open(path, encoding="utf-8")) or {}
    except (ValueError, OSError):
        return {}


def save_ledger(path, add):
    """把 `add` **合併**進 `path` 的台帳 → 回 (合併後鍵數, 本趟新增鍵數)。

    ## ⛔ 為什麼是合併不是取代（CLAUDE.md 四點六）

    這一趟只知道**自己問過的那幾天**。整份取代 ＝ `--limit` 分批補的時候，
    後一趟會把前幾趟的紀錄洗掉 ⇒ **永遠補不完，而且每趟都像有在跑**
    （`otc_adj.save_done` 把 1,996 列洗成一列表頭，就是這個形狀）。

    ## ⭐ 斷言驗的是**終點**（四點二）

    ⛔ 不斷言「寫檔成功」⇒ ⭐ 寫完**重讀**，斷言讀回來的鍵數沒有變少。
    """
    cur = load_ledger(path)
    before = len(cur)
    cur.update(add)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(
        json.dumps(cur, ensure_ascii=False, indent=0, sort_keys=True))
    back = load_ledger(path)      # ⭐ 重讀。⛔ 寫檔沒丟例外 ≠ 內容還在
    if len(back) < before:
        raise RuntimeError(
            f"台帳 {path} 合併後從 {before} 鍵變成 {len(back)} 鍵——"
            "這支絕不可以變成刪東西的那個人")
    return len(back), len(back) - before


def day_is_open(day, today=None):
    """`day` ＝ `"YYYY-MM-DD"`。→ 這一天**還沒結束**（含今天）。

    ⭐ 跟 `month_is_open()` 同一個道理，只是粒度換成天：
      台帳記「問過了」⇒ 問過就永遠不再問，⚠ 而**今天**的那一批
      在盤中問是空的、收盤後才有 ⇒ 記上去就等於今天永遠抓不到。
    """
    return day >= (today or runlog.now_tpe().strftime("%Y-%m-%d"))


def days_to_ask(days, done, ledger, force=False, today=None):
    """→ `(這一趟要問的 [日期], 台帳有但因為是今天而重問的 [日期])`。

    - `done`   ＝ 已經有日檔的日期集合（**資料自己**，最可信的那一份）
    - `ledger` ＝ 問過、但那天沒有資料的日期（⛔ 沒有日檔，光看檔案分不出
      「那天沒資料」與「從來沒問過」）

    ## ⛔⛔ 沒有它的時候會怎樣（2026-09-12 量到的）

    `feeds:tib` 每晚從區間第一天開始問，前 30 天都回「沒有資料」⇒ 收手。
    ⚠ 而那 30 天**不寫任何檔**⇒ 明晚的 `done` 一模一樣 ⇒ **問一樣的 30 天**。
    ⇒ 2021-06-28 之後的 377 個交易日永遠走不到，⛔ 而每一趟看起來都有在跑。

    ⭐ 抽成純函式的理由跟 `months_to_ask()` 一樣：這段壞掉時**整趟是綠的**。
    """
    if force:
        return list(days), []
    todo = [x for x in days
            if x not in done and (x not in ledger or day_is_open(x, today))]
    reask = [x for x in todo if x in ledger]
    return todo, reask


def month_is_open(ym, today=None):
    """`ym` ＝ `"YYYY-MM"`。→ 這個月**還沒結束**（含今天所在的那個月）。

    ## ⛔⛔ 為什麼需要它（2026-09-11，付出的代價是 6 檔的還原因子）

    `cmd_feed_range` 的台帳記的是「這個月問過了」⇒ 問過就**永遠不再問**。
    ⚠ 而公告型的表（除權息／減資／面額變更／ETF 分割）**當月還在長**：

        2026-09 月初問過一次 ⇒ 台帳記上
        ⇒ 09-10 才公告的那幾檔，**這個月再也不會被問到**
        ⇒ `data/universe/exright/2026-09-10.csv` 根本不存在
        ⇒ `adj_gap` 報 5906／4912／9802／2062／9906／6504 **未歸因**
        ⚠ 而 `feeds:exright` 那一趟是 **✓ 正常**：
          「這個區間的 1 個月台帳裡都問過了，本趟沒有要問的」

    ⭐ 這正是 CLAUDE.md 第四點那句：**續跑判準要用資料自己，⛔ 不要另開台帳**
      ——台帳會跟資料不一致，⚠ 而不一致的方向是「看起來比實際好」。

    ⇒ ⭐ 台帳只對**已經結束的月份**有效。還沒結束的月份一律重問
      （一趟只多一發，⛔ 而漏掉的是整批公司行動）。

    ## ⛔ 判準是**日曆上的月底**，不是 `--end` 夾出來的那一天

    `_months()` 回的迄日被 `args.end` 夾過 ⇒ 拿它去判，
    「我只查到 9/5」會被誤判成「9 月已經結束」。
    """
    import calendar
    y, m = int(ym[:4]), int(ym[5:7])
    last = f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"
    return last >= (today or runlog.now_tpe().strftime("%Y-%m-%d"))


def months_to_ask(rng, ledger, force=False, today=None):
    """→ `(這一趟要問的 [(起,迄)], 台帳有但因為當月而重問的 ["YYYY-MM"])`。

    ⭐ 抽成純函式的理由：這段判準壞掉時**整趟是綠的**
      （「台帳裡都問過了，本趟沒有要問的」），⛔ 只有下游的 `adj_gap`
      會在幾天後間接叫一聲。⇒ 要能餵假台帳直接驗它。
    """
    if force:
        return list(rng), []
    todo = [m for m in rng
            if m[0][:7] not in ledger or month_is_open(m[0][:7], today)]
    reask = [m[0][:7] for m in todo
             if m[0][:7] in ledger and month_is_open(m[0][:7], today)]
    return todo, reask


# 端點自己說「查無資料」時的字樣。**這代表那段期間沒有事件，不是抓取失敗。**
_EMPTY_STAT_RE = re.compile(r"沒有符合條件的資料|查無資料|無符合條件|沒有資料")
_EMPTY = object()          # cmd_feed_range 內部用的哨符：這個月沒有事件


def cmd_feed_range(args, name):
    """區間型 feed：逐月抓一次，再依**每列自己的日期**拆成日檔。

    為什麼不逐日：`TWT49U` 吃 startDate/endDate，一次可以回一整個月。
    逐日要 3,656 發（含休市日也得打一發才知道休市），逐月只要約 140 發。

    ★ 防呆：回應自述的日期區間必須與請求的相符（`_same_day` 已強化為
      同時檢查 title／strDate／endDate，不再只看會被回音的 `date`），
      而且**每一列的日期都必須落在請求區間內**——
      有一列落在區間外就整個月拒收並回報，不寫任何檔案。
      這是 2026-09-04 那次「2026 資料寫進 2015」之後補的第二道閘。
    """
    spec = FEEDS[name]
    known = B._known_codes()
    d = feed_dir(name)
    rng = _months(args.start, args.end)

    # ── ★ 台帳：哪幾個月**真的問過** ──
    #
    # ⛔ 這類 feed（減資、面額變更、ETF 分割）**沒有事件的月份不寫檔**，
    #   所以「`data/universe/<feed>/` 裡沒有那個月的檔」**分不出**
    #   「那個月沒有事件」與「那個月從來沒問過」。
    #   拿檔案存在與否當進度，就是本專案一路在防的
    #   「拿間接證據代替直接證據」——`mops_history.py` 已經為同一件事吃過虧。
    #
    # → 所以另外記一份台帳，只記「問過、結果是什麼」。
    #   有了它，`--limit` 才能挑出**還沒問過**的月份分批補，
    #   而不是每趟都把 141 個月重打一遍（減資／面額那三支各要十幾分鐘）。
    led_path = os.path.join(d, "_fetched.json")
    ledger = load_ledger(led_path)     # ⭐ 讀寫都收在一支（四點五）
    # ⭐ 台帳只對**已經結束的月份**有效（理由見 `month_is_open()`）。
    todo, reask = months_to_ask(rng, ledger, args.force)
    if args.limit:
        todo = todo[:args.limit]
    skipped = len(rng) - len(todo)
    rng = todo

    print(f"[{name}] {spec['status']}")
    print(f"[{name}] {args.start} ~ {args.end}｜逐月抓，本趟 {len(rng)} 個月"
          f"（台帳已問過 {skipped} 個月，--force 可重問）"
          + (f"｜⭐ 其中 {len(reask)} 個月是**還沒結束的月份，台帳有也照樣重問**"
             f"：{reask}" if reask else ""))
    if not rng:
        rl = runlog.Run(f"feeds:{name}")
        rl.info("區間", f"{args.start} ~ {args.end}")
        rl.note(f"這個區間的 {skipped} 個月台帳裡都問過了，本趟沒有要問的"
                "　⚠ 而**還沒結束的月份一律重問** ⇒ 這裡是 0 就代表"
                "這個區間裡沒有任何一個月是當月")
        rl.check("跑完整個區間，沒有提前收手", True, "沒有待處理的月份")
        return rl.finish()
    ok = empty = failed = 0
    total_rows = 0
    fetched_now = {}
    fwd = bool(spec.get("announce_ahead"))
    n_future, future_rows = 0, []
    for i, (a, b) in enumerate(rng, 1):
        # 前瞻式公告表：請求與 stray 檢查都用**月底**當上界，否則當月的未來日期列
        # 會落在區間外，整月被拒收（見 FEEDS["reduce"] 的 announce_ahead 註解）。
        # ★ 上界放寬只是為了「不要整月拒收」，**未來的列照樣不寫**，見下方。
        b_lim = (f"{a[:7]}-{calendar.monthrange(int(a[:4]), int(a[5:7]))[1]:02d}"
                 if fwd else b)
        aa, bb = a.replace("-", ""), b_lim.replace("-", "")
        got, note = None, "沒有候選"
        for url in spec["urls_range"](aa, bb):
            raw, err = B.get(url)
            if err:
                note = f"失敗({err[:60]})"
                continue
            try:
                doc = json.loads(raw.decode("utf-8"))
            except Exception as ex:                    # noqa: BLE001
                head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
                note = f"JSON {type(ex).__name__}｜{len(raw)}B｜開頭：{head}"
                continue
            stat = doc.get("stat") if isinstance(doc, dict) else None
            if stat and str(stat).strip().lower() not in ("ok", "success"):
                # ★ 「查無資料」與「失敗」是兩件事，不可混為一談。
                #   除權息每個月都有事件，所以踩不到；**減資一年只有 20~30 件**，
                #   七成以上的月份會回「很抱歉，沒有符合條件的資料!」。
                #   把它算成失敗的話：①摘要會寫「失敗 100 個月」，真的失敗被蓋掉
                #   ②前三個月剛好都沒事件就會觸發「全部失敗」的提早收手。
                if _EMPTY_STAT_RE.search(str(stat)):
                    got, note = _EMPTY, f"stat={stat}"
                    break
                note = f"stat={stat}"
                continue
            # 自述區間核對：起日看 strDate/title，迄日看 endDate
            s_ok, s_said = B._same_day(
                {k: doc.get(k) for k in ("strDate", "title") if doc.get(k)}, a)
            if not s_ok:
                note = f"回應自述的起日不符（要 {a}）：{s_said}"
                continue
            got = doc
            break
        if got is _EMPTY:
            empty += 1
            fetched_now[a[:7]] = "empty"      # ★ 問過了、那個月真的沒事件
            time.sleep(B.SLEEP)
            continue

        if got is None:
            # ⛔ 失敗**不記台帳**——記了就永遠不會再問，
            #   而失敗多半是限流那種會自己好的事。
            failed += 1
            print(f"  [{i}/{len(rng)}] {a[:7]} {note}", flush=True)
            if failed >= 3 and ok == 0:
                print(f"[{name}] 前 {i} 個月全部失敗且無一成功，收手。最後一則：{note}",
                      file=sys.stderr)
                break
            time.sleep(B.SLEEP)
            continue

        lines, nt = spec["parse"](got, a, known if spec["known"] else None)
        stray = [r[0] for r in lines if not (a <= r[0] <= b_lim)]
        if fwd:
            # ★ 未來日期的列**不寫檔**。它們是公告、不是已發生的事件，
            #   寫進去會讓還原因子由尚未發生的事件產生（見上方註解）。
            fut = [r for r in lines if r[0] > b]
            if fut:
                n_future += len(fut)
                future_rows.extend(fut)
                lines = [r for r in lines if r[0] <= b]
                nt += (f"（另有 {len(fut)} 列**尚未到期的公告，未寫入**："
                       f"{sorted({r[0] for r in fut})[:4]}）")
        if stray:
            print(f"[{name}] ★ {a[:7]} 有 {len(stray)} 列日期落在請求區間外"
                  f"（例：{stray[:3]}），整月拒收，不寫檔。", file=sys.stderr)
            failed += 1
            time.sleep(B.SLEEP)
            continue

        byday = {}
        for r in lines:
            byday.setdefault(r[0], []).append(r)
        for day, rs in byday.items():
            write_day(name, day, rs)
        if byday:
            ok += 1
            total_rows += len(lines)
            fetched_now[a[:7]] = f"ok:{len(lines)}"
        else:
            empty += 1
            # ★ 端點回了 stat=OK 但解析後 0 列——也算問過了
            fetched_now[a[:7]] = "empty"
        if i % 12 == 0 or not byday:
            print(f"  [{i}/{len(rng)}] {a[:7]} {len(byday)} 天 / {len(lines)} 列"
                  f"（{nt}）", flush=True)
        time.sleep(B.SLEEP)
    # ── 台帳寫回。⛔ 只**合併**，不整份取代：--limit 分批補時，
    #    整份取代會把前幾趟的紀錄洗掉，於是永遠補不完。
    #    （`calendar_audit.py --write` 2026-09-08 踩過同一個坑：
    #      全量取代把 2,845 天砍成 5 天，而且沒有任何錯誤。）
    if fetched_now:
        try:
            n_all, n_new = save_ledger(led_path, fetched_now)
            print(f"[{name}] 台帳 {led_path}：本趟問了 {len(fetched_now)} 個月"
                  f"（其中 {n_new} 個是新的），累計 {n_all} 個月")
        except (OSError, RuntimeError) as ex:                    # noqa: BLE001
            print(f"[{name}] 台帳寫檔失敗：{ex}", file=sys.stderr)
    print(f"[{name}] 完成：有資料 {ok} 個月、無事件 {empty} 個月、失敗 {failed} 個月，"
          f"合計 {total_rows} 列"
          + (f"；另有 {n_future} 列**尚未到期的公告，未寫入**" if n_future else ""))
    if future_rows:
        # 印出來是刻意的：知道有減資要來很有用（那幾天會停止買賣），
        # 只是它不該進還原因子。等事件日過了再跑一次同一個月就會收進來。
        print(f"[{name}] 尚未到期的公告（**不在資料庫裡**，僅供知悉）：")
        for r in sorted(future_rows)[:20]:
            print(f"        {r[0]}  {r[1]}  {'  '.join(str(x) for x in r[2:5])}")

    # ★ 寫進 data/meta/_last_run.md。⛔ 區塊名帶 feed 名——`daily.yml` 一趟裡
    #   exright 與 reduce 都走這條路徑，共用名字會互相蓋掉。
    #   ⚠ **不檢查「ok > 0」**：exright／reduce 抓的是當月區間，
    #     整個月沒有任何除權息或減資事件是**正常**的（尤其月初）。
    #     拿它當失敗會讓這一頁每個月初都紅（防護誤殺跟防護失效一樣糟）。
    rl = runlog.Run(f"feeds:{name}")
    rl.info("區間", f"{args.start} ~ {args.end}｜{len(rng)} 個月")
    # ⛔ 這一列即使是 0 也要在：⚠ 0 跟「這道根本沒做」在紙上看起來一樣。
    rl.info("⭐ 台帳有、但**還沒結束所以照樣重問**的月份",
            (f"{len(reask)} 個：{reask}"
             "　⇒ ⛔ 公告型的表當月還在長，問過一次就不再問 ＝ "
             "當月後半的公司行動永遠抓不到（2026-09 漏掉 6 檔）")
            if reask else "0 個（這個區間裡沒有當月）")
    rl.info("結果", f"有資料 {ok} 個月、無事件 {empty} 個月、失敗 {failed} 個月，"
                    f"合計 {total_rows} 列")
    # ⚠ 尚未到期的公告做成 info 不做成 check：減資與除權息本來就提前公告，
    #   擋下來是正常運作。要抓的是「擋漏了」，那一條在 adjust 那邊
    #   （寫出去的因子有沒有晚於資料最後一天）。
    if n_future:
        rl.info("尚未到期的公告", f"{n_future} 列（正常，事件日到了會自然進來）")
    rl.check("每個月都問到了", failed == 0,
             f"失敗 {failed} / {len(rng)} 個月" if failed else f"{len(rng)} 個月全問到")
    # ⛔ finish() 一定要無條件呼叫——寫在三元運算的其中一支，
    #    「這一趟成功」時區塊就不會寫出去，而那正是最常見的情況。
    rc = rl.finish()
    base = 0 if (ok or not rng) else 1
    return 1 if (base or rc) else 0


def cmd_purge(args):
    """刪掉某個 feed 已寫出的所有日檔。

    ★ 存在的理由：2026-09-04 的 exright 事故寫出了一批**內容是錯的**日檔
      （每個檔都是 2026-09-07 的四列）。這種錯不能靠 `--force` 覆蓋修掉——
      改用區間模式後檔名的集合會不一樣，覆蓋不到的舊檔會留在原地，
      而且它們長得跟正常檔一模一樣。**必須整個刪掉重來。**
    """
    name = args.feed
    if name not in FEEDS:
        print(f"未知的 feed：{name}", file=sys.stderr)
        return 1
    d = feed_dir(name)
    if not os.path.isdir(d):
        print(f"[{name}] {d} 不存在，沒有東西要刪")
        return 0
    files = [n for n in os.listdir(d) if n.endswith(".csv")]
    for n in files:
        os.remove(os.path.join(d, n))
    print(f"[{name}] 已刪除 {len(files)} 個日檔（{d}）")
    return 0


DAILY_DIR = os.path.join(UNI_DIR, "daily")


def trading_calendar():
    """交易日曆＝`data/universe/daily/` 的檔名集合。→ 升冪日期字串 list。

    ★★ 為什麼不再掃「週一到週六」（2026-09-05 改）：

    | 做法 | 天數 | 5.5s/天 |
    |---|---|---|
    | 週一～五 | 3,047 | 279 分 ← **會漏掉補行交易的週六** |
    | 週一～六 | 3,656 | 335 分 ← 舊做法，**超過 job 上限 350 分** |
    | **照交易日曆** | **2,844** | **261 分** ← 一趟跑得完 |

    掃非交易日是純粹的浪費：812 個請求（22%）、74 分鐘，換來的只有
    一整排「沒有符合條件的資料」。而且那些雜訊還害過一次——
    `margin` 續跑時前五天剛好全是休市，觸發「連續失敗」收手，
    訊息還寫成「連問都問不到」，完全誤導。

    **補行交易的週六本來就在日曆裡**（價格資料是逐日抓的，那幾天有檔），
    所以照日曆走比 `--saturdays` 更準，不是更省而已。

    ★ 上市與上櫃共用同一份交易日曆（`tw-technical-analysis` 實測
      8096、5274 對 3042 皆 728/728 完全相同），所以 TPEx 的 feed
      也適用這份日曆。

    拿不到日曆時回空 list，呼叫端會退回原本的掃描法——
    **不要在拿不到日曆時安靜地少抓**。
    """
    if not os.path.isdir(DAILY_DIR):
        return []
    return sorted(n[:-4] for n in os.listdir(DAILY_DIR)
                  if n.endswith(".csv") and n[0].isdigit())


def _target_days(args):
    """→ (日期 list, 用了哪種來源)。"""
    cal = trading_calendar()
    if cal:
        return [d for d in cal if args.start <= d <= args.end], f"交易日曆（{len(cal)} 天）"
    # ★ 退路一律**含週六**，不看 --saturdays。
    #   兩種錯的代價不對稱：多掃週六只是浪費時間，
    #   漏掉補行交易日是**安靜的資料缺口**——事後從檔案上看不出來。
    #   （`--saturdays` 保留只為相容既有指令，實際不影響結果。）
    # ★ daterange 回的是 generator，這裡一定要 list() ——
    #   否則呼叫端第二次用到它時已經耗盡，會安靜地變成 0 天。
    return (list(B.daterange(args.start, args.end, True)),
            "逐日掃描（找不到交易日曆，退回含週六的全掃）")


def cmd_feed(args):
    name = args.feed
    if name not in FEEDS:
        print(f"未知的 feed：{name}；可用：{', '.join(FEEDS)}", file=sys.stderr)
        return 1
    if args.sleep:
        B.SLEEP = args.sleep
    if FEEDS[name].get("range"):
        return cmd_feed_range(args, name)
    d = feed_dir(name)
    done = set()
    if os.path.isdir(d):
        done = {n[:-4] for n in os.listdir(d) if n.endswith(".csv")}
    days, how = _target_days(args)
    need = getattr(args, "need_col", "")
    stale = set()
    if need:
        # ⛔ 只讀第一行。2,846 個檔全部讀完是幾百 MB，而我只要表頭。
        for x in sorted(done):
            p_ = os.path.join(d, x + ".csv")
            try:
                with open(p_, encoding="utf-8") as f_:
                    head = f_.readline()
            except OSError:
                continue
            if need not in [c.strip() for c in head.rstrip("\n").split(",")]:
                stale.add(x)
        print(f"[{name}] --need-col {need}：已存在的 {len(done)} 天裡，"
              f"**{len(stale)} 天的表頭缺這一欄**，要重抓")
        if not stale:
            print(f"[{name}] ⇒ 這個區間已經全部有 `{need}` 欄了，沒有要重抓的")
    # ── ⭐⭐ 台帳：哪幾天**問過了、而那天沒有資料** ──
    #
    # ⛔ 這是 2026-09-12 量到的 `feeds:tib` 那個缺陷（見 `days_to_ask()`）：
    #   「沒有資料」的那一天**不寫檔** ⇒ 光看 `data/universe/<feed>/`
    #   分不出「那天沒資料」與「從來沒問過」⇒ 每晚問一樣的前 30 天、
    #   一樣收手，⚠ 而每一趟看起來都有在跑。
    # ⭐ 逐月那支（`cmd_feed_range`）一開始就有台帳，⛔ 逐日這支沒有——
    #   **同一件事只做了一半**，跟 CLAUDE.md 四點六③ `save_done` 同一個形狀。
    day_led_path = os.path.join(d, "_asked.json")
    day_ledger = load_ledger(day_led_path)
    if stale:
        # ⚠ 補欄位的那條路徑要**無視台帳**：那些天有檔，只是表頭缺一欄。
        days = [x for x in days if args.force or x not in done or x in stale]
        day_reask = []
    else:
        days, day_reask = days_to_ask(days, done, day_ledger, args.force)
    if args.limit:
        days = days[:args.limit]
    print(f"[{name}] {FEEDS[name]['status']}")
    print(f"[{name}] {args.start} ~ {args.end}｜{how}｜"
          f"待處理 {len(days)} 天（已存在 {len(done)} 天、"
          f"台帳記著「問過但那天沒資料」{len(day_ledger)} 天）"
          + (f"｜⭐ 其中 {len(day_reask)} 天是**今天**，台帳有也照樣重問"
             if day_reask else ""))
    known = B._known_codes()
    if FEEDS[name]["known"] and not known:
        print(f"[{name}] 找不到 data/meta/stocks.csv，先跑 --rebuild-meta", file=sys.stderr)
        return 1
    # ★ 先打一發，但**只有「被限流」才收手**。
    #   未驗證的 feed 第一個候選本來就可能 404／欄位不符——
    #   那是候選清單該由 run 淘汰的正常結果，不是中止理由。
    #   （backfill 的 preflight 兩種都擋，因為它的端點是已驗證的，
    #     第一發失敗就一定有鬼；這裡的前提不同，所以判斷也不同。）
    if days:
        cands = FEEDS[name]["urls"](days[0])
        if cands:
            _raw, _err = B.get(cands[0], retries=1, timeout=30)
            if _err and _err.startswith("LIMITED"):
                print(f"[{name}] **被交易所限流擋下**，不是端點或參數的問題。\n"
                      f"        {_err[:160]}\n"
                      f"        等一段時間再跑，或錯開同日其他回補工作。"
                      f"**不要改標頭、不要加大重試。**", file=sys.stderr)
                return 2
    ok = closed = failed = dropped_days = dropped_rows = 0
    asked_now = {}           # ⭐ 本趟問到、但那天沒有資料的日期
    dropped_at = []          # ⭐ 哪幾天丟了幾列（⛔ 不是只給天數）
    dropped_who = []         # ⭐ (日期, 代號)——歸因那一步要用
    bailed = ""     # 提前收手的原因；空字串＝跑完整個區間
    # ⛔⛔ 2026-09-10：`feeds:tib` 紅了，而 `_last_run.md` 只寫
    #   「前 5 天有 5 天連問都問不到」——**沒有寫為什麼**。
    #   ⚠ 是 HTTP 428（CDN 限流）？403？逾時？路徑錯？
    #     四種的下一步完全不同，而我必須**再跑一趟**才知道是哪一種。
    #   ⭐ 這跟今天早上 `revivt` 那件是同一族：
    #     **一個會叫、但叫不出原因的斷言，代價是一整個來回。**
    #   ⇒ 把 parser／抓取回的最後一則訊息帶進 runlog。
    last_fail = ""
    for i, day in enumerate(days, 1):
        lines, note, url = fetch_one(name, day, known)
        # ★★ 成敗**看 `url` 有沒有拿到，不要比對訊息字串**。
        #   `fetch_one` 只有在「請求成功 ＋ stat 正常 ＋ 日期核對通過」時才回傳 url，
        #   所以 url 就是「這一天確實問到了、只是可能沒有資料」的信號。
        #
        #   原本寫 `note.endswith("0 列")`，而 parser 後來改成回
        #   「0 列可用（名稱定位；驗算不符丟棄 0 列）」——結尾是全形括號，對不到，
        #   於是**休市日被算成失敗**。區間開頭若撞上農曆年（連休 5～9 天），
        #   `failed >= 5 且 ok == 0` 就會收手，並印一句「端點或參數不對」，
        #   而端點根本沒問題。**訊息字串是給人看的，不是狀態機的輸入。**
        if lines:
            n = write_day(name, day, lines)
            ok += 1
            # ★ **不要把 parser 的訊息蓋掉。** 它帶著「恆等式不符丟棄 N 列」，
            #   蓋掉之後每天默默丟幾十列也看不出來——正是這個專案一路在防的靜默。
            #   丟棄數為 0 時才簡化成「N 列」，避免每行都拖一串括號。
            n_drop, note = _tally_drop(n, day, note)
            if n_drop:
                dropped_days += 1
                dropped_rows += n_drop
                dropped_at.append(f"{day}（{n_drop} 列）")
                dropped_who += [(day, c) for c, _why in _drop_codes(note)]
        elif url is not None:
            closed += 1               # 問到了，那天沒有資料（休市或無事件）
            # ⭐ 記台帳。⛔ 只記**已經結束**的日子——今天的那一批盤中是空的、
            #   收盤後才有，記上去就等於今天永遠抓不到（`day_is_open()`）。
            if not day_is_open(day):
                asked_now[day] = "empty"
        else:
            failed += 1               # 根本沒問到
            last_fail = str(note)[:260]
        if i % 20 == 0 or url is None:
            print(f"  [{i}/{len(days)}] {day} {note}", flush=True)
        # ★ 與 cmd_inst 同一條收手規則：一開始就全失敗代表端點或參數不對，
        #   不是隨機故障。放著跑只是燒時間，而且跑出來的全是錯的。
        # ★ 端點一直回「沒有符合條件的資料」也要收手。
        #   這種情況 failed 恆為 0（它有回應），舊的閘門擋不住——
        #   若端點有**日期下限**（例如只回得到近幾年），整趟會安靜跑滿
        #   5.8 小時、一列都沒寫，最後才發現。30 天足以跨過任何連假。
        if closed >= 30 and ok == 0:
            # ⛔⛔ 這句原本寫「很可能有日期下限」——**那是錯的診斷**（2026-09-12 訂正）。
            #   有日期下限的端點是**大聲失敗**：`STOCK_TIB` 越界時回
            #   `stat:"查詢日期小於110年6月28日，請重新查詢!"` ⇒ 那會算進 `failed`。
            #   ⚠ 這裡 `failed == 0` ⇒ 端點**明確回答了「這一天沒有資料」**。
            #   ⇒ 真正剩下的可能只有一種：那幾天的母體是空的
            #     （例：創新板 2021-07-20 才開板，而端點下限是 2021-06-28）。
            # ⭐ 而「把錯的原因寫進 runlog」的代價是一整個來回——
            #   下一個人會照著那句話去找根本不存在的日期下限。
            bailed = (f"連續 {i} 天回「沒有資料」且無一有列"
                      f"｜⚠ 失敗 {failed} 天 ⇒ 端點是通的、也明講了「這天沒資料」，"
                      f"⛔ 這**不是**日期下限（越界會大聲失敗，會算進失敗天數）")
            print(f"[{name}] 前 {i} 天全部回「沒有資料」且無一有列，收手。\n"
                  f"        ⚠ 失敗 {failed} 天 ⇒ 端點通、參數對，它就是說那幾天沒有資料。\n"
                  f"        ⭐ 這一趟問過的天數**已經記進台帳**，下一趟會從沒問過的接著跑，"
                  f"⛔ 不會再從第一天重來。\n"
                  f"        最後一則：{note}", file=sys.stderr)
            break
        # 只數「根本沒問到」的天數。休市不算失敗，否則農曆年會被誤判成端點壞掉。
        if failed >= 5 and ok == 0:
            bailed = (f"前 {i} 天有 {failed} 天連問都問不到且無一成功"
                      + (f"｜最後一則：{last_fail}" if last_fail else ""))
            print(f"[{name}] 前 {i} 天有 {failed} 天連問都問不到且無一成功，收手。"
                  f"最後一則：{note}", file=sys.stderr)
            break
        time.sleep(B.SLEEP)
    # ── 台帳寫回。⭐ **收手（break）之後也會走到這裡**，那正是重點：
    #    提前收手的那一趟問過的天數一樣要留下來，⛔ 否則下一趟又從第一天重來。
    led_all = led_new = 0
    led_err = ""
    if asked_now:
        try:
            led_all, led_new = save_ledger(day_led_path, asked_now)
            print(f"[{name}] 台帳 {day_led_path}：本趟 +{led_new} 天"
                  f"（問到但沒資料），累計 {led_all} 天")
        except (OSError, RuntimeError) as ex:                    # noqa: BLE001
            led_err = str(ex)[:200]
            print(f"[{name}] ⛔ 台帳寫檔失敗：{ex}", file=sys.stderr)
    print(f"[{name}] 完成：有資料 {ok} 天、無資料/休市 {closed} 天、失敗 {failed} 天")
    if dropped_days:
        print(f"[{name}] ⚠ 有 {dropped_days} 天出現驗算不符而丟棄的列（詳見上面各該日）。"
              f"**丟棄不是零就要看過**——可能是欄位對應在某個年代變了。", file=sys.stderr)
    # ★ 只有「真的失敗」才回非零。**「一天資料都沒有」不等於出錯**——
    #   補單一缺日時，區間內其餘天數可能全是週六或連假，
    #   那時 ok=0、failed=0，是正常結果。
    #   原本寫 `return 0 if (ok or not days) else 1`，這種情況會回 exit code 1，
    #   Actions 上顯示紅叉。**讓成功的跑印出紅叉，會訓練人忽略紅叉**，
    #   下次真的失敗就看不見了。

    # ★ 寫進 data/meta/_last_run.md。
    #   ⛔ 區塊名一定要帶 feed 名。`daily.yml` 一趟裡呼叫本支三次
    #      （otcinst／exright／reduce），共用一個名字的話後面兩次會蓋掉前面，
    #      那一頁只剩最後跑的 reduce——**正是 runlog 存在要防的那件事**。
    #   ⚠ 每條檢查都先問「今天有沒有收到東西」才驗內容：exright／reduce 抓的是
    #     當月區間，沒有事件的月份 ok=0 是**正常**的，不可以拿它當失敗
    #     （防護誤殺跟防護失效一樣糟）。
    rl = runlog.Run(f"feeds:{name}")
    rl.info("區間", f"{args.start} ~ {args.end}｜待處理 {len(days)} 天")
    rl.info("結果", f"有資料 {ok} 天、無資料/休市 {closed} 天、失敗 {failed} 天")
    # ⛔ 這一列即使是 0 也要在：⚠ 0 跟「這道根本沒做」在紙上看起來一樣。
    rl.info("⭐ 記進台帳的「問到了、那天沒資料」",
            (f"本趟 +{led_new} 天，累計 {led_all} 天"
             "　⇒ 下一趟會從**沒問過**的接著跑，⛔ 不是從區間第一天重來")
            if asked_now else
            "0 天（這一趟沒有任何一天是『問到了但沒資料』）")
    # ⭐ 台帳寫不進去是**要紅的**：它一失敗，下一趟就會再從第一天重來，
    #   ⚠ 而那個失敗在紙上長得跟「這個區間本來就沒東西」一模一樣。
    rl.check("台帳寫得進去", not led_err, led_err or "沒有要寫的或已寫入")
    # ⛔ 提前收手在 Actions 上是看不見的（這幾步都是 continue-on-error），
    #    而收手代表整趟根本沒跑完——這是要紅的，不是資訊。
    rl.check("跑完整個區間，沒有提前收手", not bailed, bailed or "跑完")
    if last_fail:
        # ⭐ 這一行就是「為什麼」。⛔ 不要只留在 Actions log 裡——
        #   `_last_run.md` 才是進 repo、下一個人會看到的那一份。
        rl.info("⛔ 最後一則「沒問到」的原因", last_fail)
    rl.check("沒有「連問都問不到」的日子", failed == 0,
             f"失敗 {failed} 天" if failed else "0 天")
    # ⛔ 丟棄不是零就要看過——可能是欄位對應在某個年代變了，
    #    而每天默默丟幾十列外表完全正常。
    # ⭐ 歸因：不符的列裡，哪些是「該檔離開了本市場」（⛔ 不是瑕疵）
    left, unexplained = _explain_drops(name, dropped_who, days)
    if left:
        rl.info("⭐ 已歸因：**離開本市場**（轉上市／終止櫃買）⇒ ⛔ 不是瑕疵",
                f"{len(left)} 筆：{[(d, c) for d, c, _ in left[:6]]}"
                "　⚠ 官方在該檔離開時把餘額**直接歸零**，"
                "⛔ 沒有走「還券」也沒有走「調整」欄 ⇒ 恆等式當然不成立")
    # ⛔ 判準只看**未歸因**的。⚠ 而「已歸因」不可以自動長大：
    #   歸因靠的是「次一交易日不在表上」——那是**資料自己**講的，
    #   ⛔ 不是靠備註欄（情報分析線查到的那一筆備註是空的）。
    rl.check("沒有**未歸因**的驗算不符列", not unexplained,
             (f"⛔ **{len(unexplained)} 筆未歸因**："
              f"{[(d, c, w) for d, c, w in unexplained[:6]]}"
              "　⇒ 差 1~2 股是進位、差一個量級是**欄位對錯位**"
              "（那兩種的處置完全不同）")
             if unexplained else
             (f"0 筆（⚠ 另有 {len(left)} 筆已歸因為離開本市場）"
              if left else f"0 筆｜丟棄 {dropped_rows} 列"
              if dropped_rows else "0 天"))
    rc = rl.finish()
    return 1 if (failed or rc) else 0


def cmd_probe(args):
    r"""只測端點、不寫任何檔案。把每個候選的結果照實印出來。

    **這是 TPEx 那幾個 feed 唯一的驗證途徑**——開發環境對 tpex.org.tw
    一律 403，只有在 Actions 上跑得到。

    ★★ **事件型的區間 feed 不能用單日探測。**（2026-09-06 踩到）

      `--probe --feed reduce --date 2026-09-03` 回報「沒有可用候選」並 exit 1，
      看起來像端點壞掉。實際上端點是好的、參數是對的、日期核對也過了，
      只是**那天沒有減資事件**，所以 TWSE 回
      `{"stat":"很抱歉，沒有符合條件的資料!"}`。
      減資一年只有 20~30 件，**隨便挑一天去探幾乎一定是空的**。

      這正是這個專案一路在防的那種錯：把「查無資料」讀成「端點不可用」。
      判準錯了會讓人去修一個根本沒壞的東西，或反過來把壞掉的當成正常。

      → 改成兩段探測：
        ① 先試**該日所在的整月**（貼近實際使用形狀——本來就是逐月抓）
        ② 仍為空就試 spec 的 `probe_range`，那是**已知有事件**的區間

      **探測要驗的是「解析得出來」，不是「那天剛好有事」。**
      兩段都空才算失敗，而且會明說是空、不是不通。
    """
    names = list(FEEDS) if args.feed in ("", "all") else [args.feed]
    day = args.date
    known = B._known_codes()
    print(f"[probe] 測試日 {day}｜universe 白名單 {len(known)} 檔\n")
    rc = 0
    for name in names:
        spec = FEEDS[name]
        print(f"── {name}｜{spec['status']}")

        # 探測窗：非區間型就是那一天；區間型是「該月」→「已知有事件的區間」
        if spec.get("range"):
            y, m = int(day[:4]), int(day[5:7])
            last = calendar.monthrange(y, m)[1]
            wins = [(f"{y:04d}-{m:02d}-01",
                     f"{y:04d}{m:02d}01", f"{y:04d}{m:02d}{last:02d}", "該月")]
            pr = spec.get("probe_range")
            if pr:
                wins.append((f"{pr[0][:4]}-{pr[0][4:6]}-{pr[0][6:8]}",
                             pr[0], pr[1], "已知有事件的區間"))
        else:
            wins = [(day, None, None, "")]

        hit = emptied = False
        for cmp_day, aa, bb, tag in wins:
            if spec.get("range"):
                cands = spec["urls_range"](aa, bb)
                print(f"   [{tag} {aa}~{bb}]")
            else:
                cands = spec["urls"](day)
            for url in cands:
                raw, err = B.get(url, retries=1, timeout=30)
                short = url.replace("https://www.", "")
                if err:
                    print(f"   ✗ {short}\n       {err[:100]}")
                    continue
                try:
                    d = json.loads(raw.decode("utf-8"))
                except Exception as ex:               # noqa: BLE001
                    head = raw[:100].decode("utf-8", "replace").replace("\n", " ")
                    print(f"   ✗ {short}\n       非 JSON（{len(raw)}B）"
                          f"{type(ex).__name__}：{head}")
                    continue
                # ⭐⭐ 使用者 2026-09-10 定的規矩，做在**探路模式的第一行**：
                #   「以後新端點第一件事，就是把 `notes`／`hints`／`title` 印出來，
                #     再開始比對。」
                #   ⇒ 接新 feed 一定會先跑 `--probe`，所以放在這裡＝**跳不過去**。
                #   ⛔ 寫成文件會被忘記；寫在這裡不會。
                # ⚠ `params` 那一項最有用：端點會把收到的參數**回顯**，
                #   ⇒ 被換掉就代表**那個參數是假的**（TWTAWU 的 `date=` 就是這樣）。
                print(f"   ── {short}")
                for _ln in B.describe_response(
                        d, want=({"date": aa, "startDate": aa, "endDate": bb}
                                 if aa else {"date": day.replace("-", "")})):
                    print(f"       {_ln}")

                stat = d.get("stat") if isinstance(d, dict) else None

                # ★ 「查無資料」先攔下來，**不要落進「沒有可用候選」**。
                #   端點通、參數對，只是那個區間沒有事件——這是結論，不是失敗。
                if stat and _EMPTY_STAT_RE.search(str(stat)):
                    print(f"   ○ {short}")
                    print(f"       stat={stat}")
                    print("       → **端點通、這個區間沒有事件**（不是端點不可用）")
                    emptied = True
                    continue

                # ★ 區間型不能整包丟給 `_same_day`：它會拿 `endDate` 去比起日，
                #   多日區間**一定不符**（20151231 ≠ 20150101），
                #   於是好端端的回應被標成 △、解析根本不會跑。
                #   `cmd_feed_range` 早就只挑 strDate／title 比，這裡照做。
                if spec.get("range"):
                    same, said = B._same_day(
                        {k: d.get(k) for k in ("strDate", "title") if d.get(k)},
                        cmp_day)
                else:
                    same, said = B._same_day(d, cmp_day)
                tabs = B._tables(d)
                fields = _fieldmap(tabs[0]) if tabs else []
                rows = len(tabs[0].get("data") or []) if tabs else 0
                flag = "✓" if (str(stat or "").lower() in ("ok", "success") and same) \
                    else "△"
                print(f"   {flag} {short}")
                print(f"       stat={stat}｜日期核對="
                      f"{'通過' if same else f'不符({said})'}"
                      f"｜表數={len(tabs)}｜首表 {rows} 列")
                if fields:
                    print(f"       欄位={fields}")
                if flag == "✓":
                    lines, nt = spec["parse"](
                        d, cmp_day, known if spec["known"] else None)
                    print(f"       解析結果：{nt}")
                    if lines:
                        print(f"       首列={lines[0]}")
                        hit = True
                    break
            if hit:
                break

        if not hit:
            if emptied:
                # 端點是通的，只是探到的區間沒有事件。這**不是**端點問題，
                # 但也還沒驗到解析——照實說，不要含糊成「可用」或「不可用」。
                print("   → **端點通但探測區間內沒有事件，解析未驗到。**"
                      "換一個確定有事件的區間再探（改 probe_range 或 --date）")
            else:
                print("   → 沒有可用候選")
                rc = 1
        print()
    return rc


def main():
    ap = argparse.ArgumentParser(description="全市場每日 feed 回補")
    ap.add_argument("--feed", default="", help=f"{', '.join(FEEDS)}；probe 可用 all")
    ap.add_argument("--probe", action="store_true", help="只測端點，不寫資料")
    ap.add_argument("--run", action="store_true", help="逐日（或逐月）回補")
    ap.add_argument("--purge", action="store_true",
                    help="刪掉該 feed 已寫出的所有日檔（內容錯掉時用，覆蓋救不回來）")
    ap.add_argument("--date", default="2026-09-03", help="probe 用的測試日（要是交易日）")
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--end", default="2026-09-03")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="已存在的日期也重抓")
    # ★★ 2026-09-09。加新欄位之後**舊日檔要重抓**，而 `--force` 是「全部重抓」：
    #   一趟跑不完（2,846 天 × 5 秒 ≈ 4 小時，job 上限 350 分鐘）就會被砍在半路，
    #   而下一趟又從第一天重來 ⇒ **永遠補不完，而且每趟看起來都很正常**。
    #   ⇒ `--need-col` 用「檔案自己的表頭」當進度：有這一欄就跳過。
    #   ⭐ 不需要另外開一個進度台帳——**資料本身就是進度**，也就不會有台帳與資料不一致。
    ap.add_argument("--need-col", default="",
                    help="重抓「表頭缺這一欄」的既有日期（補欄位用，可續跑）")
    ap.add_argument("--saturdays", action="store_true",
                    help="（已無作用）改照 data/universe/daily 的交易日曆走；"
                         "拿不到日曆時的退路一律含週六。保留只為相容既有指令。")
    ap.add_argument("--sleep", type=float, default=0)
    a = ap.parse_args()
    if a.probe:
        return cmd_probe(a)
    if a.purge:
        if not a.feed:
            print("--purge 要指定 --feed", file=sys.stderr)
            return 1
        return cmd_purge(a)
    if a.run:
        if not a.feed:
            print("--run 要指定 --feed", file=sys.stderr)
            return 1
        return cmd_feed(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
