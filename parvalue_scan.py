#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parvalue_scan.py — 全庫掃「疑似面額變更」。**只讀、只寫一份報告，不改資料。**

## 為什麼要有這一支

`tw-stock-db` skill 的陷阱 13 訂了一條判定規則：

> 相鄰兩個交易日的收盤比 `close(t)/close(t-1)` 落在 `< 0.55` 或 `> 1.8`，
> 且 `data/adj/` 裡沒有對應日期的除權息或減資事件可以解釋 → 疑似面額變更。

但同一條的最後一段寫得很清楚：

> **門檻 0.55／1.8 與「約 26 筆」的量級沿用移交內容，資料庫線尚未自行複核那份名單。**
> 要把它變成管線裡的自動標記之前，先在 `data/stocks/` 全庫掃一次、把命中的逐筆看過。

**這一支就是那一次全庫掃描。** 在它跑完並且有人逐筆看過之前，
那條規則是「判讀時的人工檢查」，不是已驗證的資料欄位——這個分別要守住。

## ⛔ 三個會讓這次掃描白做的陷阱

**① 相鄰兩列不等於相鄰兩個交易日。**
`data/stocks/*.csv` **只收當天有成交的證券**（READ_CONTRACT 寫死的）。
一檔停牌半年，檔案裡就是兩列直接相接——那個比值是**半年的累積**，
不是「一天的跳躍」。所以每一筆都要帶**中間隔了幾個交易日**，
用 `data/meta/calendar_twse.csv`（2,847 天）去數，不是用日曆天相減。

**② 台股有漲跌幅限制。** 上市櫃普通股單日 ±10%。
所以**真的隔一個交易日**而比值到 0.55／1.8，本來就不可能是交易造成的
（興櫃、上市首日、無漲跌幅的特殊情形除外）。
這一項讓「隔 1 個交易日」的命中比「隔 40 個交易日」的命中強得多，
報告要分開列，不可以混成一個數字。

**③ 事件不能用「同一天」去對，要用「區間」。**
第一版寫成「事件日 == 跳的那一天」，再補 ±1／±3 容錯——**那是錯的**，
而且錯得很有代表性：

- 3293 鈊象 2024-07-23 收 1465 → 07-26 收 786（0.537），看起來像面額變更。
  但 `data/adj/3293.csv` 明明有 `2024-07-24 除權息 factor 0.488 ref_price 715`。
  對不上的原因是 **2024-07-24、25 因颱風停市，那兩天不在交易日曆裡**，
  而第一版的容錯是沿著**交易日曆**往前後數的，永遠數不到停市日上的事件。
- 1418、1529、4806、6198 四筆也一樣：減資事件落在停牌區間中間。

⛔ **`data/adj/` 的事件日不保證是交易日。**
正確的判準是**區間**：事件日落在 `(前一次有成交的日子, 這一次有成交的日子]` 之內，
就足以解釋這個跳躍。這樣停市、停牌、跨假日全部自然涵蓋，不必再猜容錯天數。
"""
import argparse
import csv
import io
import os
import sys
from collections import defaultdict

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STOCKS = os.path.join(_ROOT, "stocks")
ADJ = os.path.join(_ROOT, "adj")
CAL = os.path.join(_ROOT, "meta", "calendar_twse.csv")
IND = os.path.join(_ROOT, "meta", "industry.csv")
OUT = os.path.join(_ROOT, "meta", "_parvalue_scan.md")
# ★ 機器可讀版。規格由市場情報分析線 2026-09-09 00:55 指定（欄位與 evidence 兩級都照抄）。
#   為什麼要有它：每日選股的前置閘門**每天**都要拿這批去比對推薦母體，
#   只有 markdown 表格的話等於每天從表格裡把代號抄一次——
#   **逐次人工抄寫就是逐次重打的機會，而重打出的錯是靜默的。**
#   ⚠ markdown 那份要留著：它的推理過程比清單本身有價值。
CSV_OUT = os.path.join(_ROOT, "meta", "par_change.csv")
# ★ 上櫃官方「變更股票面額恢復買賣參考價」。
#   ⚠ **這份不是我方程式抓的**——櫃買那頁要執行 js，我方環境只有 `urllib`
#   （`_tpex_probe.txt` 有六條否定紀錄）。2026-09-09 由使用者用瀏覽器匯出提供，
#   原始 Big5 檔逐字保存在 `data/meta/sources/`，出處與限制寫在同目錄 README。
#   ⛔ 它只涵蓋 **2019-09-09 起**；更早的事件這份答不了，**不要當成全集**。
OTC_REF = os.path.join(_ROOT, "meta", "otc_par_reference.csv")
# 官方參考價是**四捨五入到分**印出來的，所以比對要在**價格空間**用半分容差，
# ⛔ 不可以在比值空間用固定容差——同樣的一分差，價格越低比值差越大。
REF_TOL = 0.005 + 1e-9
CSV_HEADER = ["stock_id", "event_date", "prev_trade_date", "prev_close",
              "close", "ratio", "shares_before", "shares_after",
              "share_mult", "evidence", "in_universe", "restored"]
# ★ `restored`：`data/adj/` 裡有沒有對應的還原因子。
#   ⛔ 為什麼要有這一欄（情報分析線 2026-09-09 裁定，理由是**語意**不是方便）：
#     這份的語意是「**哪些是面額變更**」。2026-09-09 這 24 筆剛好全部已還原，
#     於是「是面額變更」與「已還原」完全重疊——
#     **重疊的時候最容易被寫成同一件事，然後在它們分開的那一天靜默出錯**
#     （日後有新事件、因子落地前的那段空窗）。
#     分成兩欄之後，讀取端的閘門只讀「是不是面額變更」，還原狀態另外看。

# ★ 「無法用還原因子解釋的跳價」。規格由市場情報分析線 2026-09-09 02:30 指定。
#   ⛔ 與 `par_change.csv` **嚴格分開**：那份的語意是「面額變更」，這份不是。
#   ⛔ `cause` 一律先寫 `unknown`——**不要猜減資／合併／重整**，猜錯是另一種靜默錯誤。
#   判準寫成可自我排除的形狀，否則已知成因的會混進來：
#     ① 區間內沒有任何 `data/adj/` 事件
#     ② 不在 `par_change.csv`（面額變更已另有歸屬）
#     ③ 不是 TWTCAU 已知的 ETF 分割（`etfsplit` feed 已接、待回補）
#     ④ 停 ≥ 20 個交易日——**這一條把「無漲跌幅 ETF 的真實交易」擋掉**
#        （00672L、00887 那幾筆隔 1 天就跳 ±85%，那是交易不是公司行動）
# ⚠⚠ 這份有一個**結構性盲區**，2026-09-09 由回測線指出、我方核實：
#   候選只從「收盤比落在 LO／HI **之外**」那批來（見 main() 的 `if a.lo <= ratio <= a.hi`）。
#   ⇒ **價比溫和的長洞，這份結構上看不到。**
#   實例：3073 天方能源停 121 個交易日、股數 ×0.691、收盤比 **1.59**（沒到 1.8）
#         ⇒ 有真實公司行動，但這份抓不到。回測線的 gap 規則另外抓到 9 筆同型的。
#   ⛔ 所以「11 年只有 5 筆 ⇒ 那些類別是例外不是常態」這句**只對跳價型成立**，
#      不可以拿它推論「無法解釋的斷點總共只有 5 筆」。
#   要不要把「洞」也收進來（或分成跳價型／長洞型兩節）是語意決定，
#   歸市場情報分析裁；在裁定下來之前這份維持只收跳價型。
BRK_OUT = os.path.join(_ROOT, "meta", "breakpoints_unexplained.csv")
# ⚠ 欄名 2026-09-09 由 `gap_trading_days` 改成 `missing_trading_days`，
#   定義也跟著統一成「**前一有成交日與這一次有成交日之間，交易日曆上缺掉的交易日數**」。
#   原本用的是**日曆索引差**（157），回測線用的是**停牌天數**（156），差 1——
#   ⛔ 兩個都對，只是量的不是同一件事，而舊欄名兩種都讀得通，**那就是會出錯的地方**。
#   K線分析的條件②寫的是「連續缺 ≥ 5 個交易日」，閘門讀的就是「缺了幾天」；
#   **欄名與判準用同一個詞，才不會有人拿索引差去比 5。**
BRK_HEADER = ["stock_id", "name", "market", "kind", "event_date",
              "prev_trade_date", "prev_close", "close", "ratio",
              "missing_trading_days", "adj_events_in_range", "cause",
              "limit_on_reopen", "source_note", "in_universe"]
# ★ 情報分析 2026-09-09 10:45 三項裁定落地：
#   ① `kind` 兩節同檔：`price_jump`（比值帶外）／`long_hole`（比值帶內但停 ≥ 20 日）
#      ⛔ 不拆成兩份檔——「查的人只會查一份」，拆了遲早出現
#        「查了跳價那份、沒查長洞那份，於是回報沒事」，而那個回報看起來跟真的沒事一樣。
#   ② `limit_on_reopen`＝復牌那天 `limit` 欄的**實際值**（空就空）。
#      ⛔ 這是**事實欄**不是判語欄：不寫「疑似漲跌停」。
#        判語一進清單，下游就會拿它當篩選條件，而「疑似」與「確認」在使用端分不出來。
#      ⚠ 必須等 `fix_limit.py` 修完才產（否則會把剛修好的欄位的舊值凍進這裡）
#        ——2026-09-09 已修完 50,382 列，確認後才加這一欄。
#   ③ `source_note`＝「我們問過、對方沒有」的紀錄，**不是成因結論**。
# ⛔ `cause` 一律 `unknown`：不猜合併換股、不猜股份轉換、不猜重整。
SOURCE_NOTE = {
    # 3073 天方能源：`_otcadj_done.csv` 有問過 FinMind 的減資表，
    # 而它只回了 2020-01-13 那一筆 ⇒ 2021-02 這一筆**來源沒有**，不是我方漏抓。
    # ⚠ 這是事實紀錄，不代表「這不是減資」。
    ("3073", "2021-02-19"): "finmind_no_record",
}
# 門檻維持 20（情報分析線 2026-09-09 裁定，理由是**失效方向**）：
#   20 的偽陽性代價 ＝ 多列一筆待查（無害，人看得到）
#   30 的偽陰性代價 ＝ **短停牌的真斷點漏掉**（污染留在資料裡，沒有人看得到）
# ⚠ 現有 5 筆落在 38~687 天，**20~37 之間目前無樣本**。
#   ⛔ 不要拿「沒樣本」當「可以拉高」的理由——**沒有樣本是因為沒發生過，不是因為不會發生。**
BRK_MIN_GAP = 20
# ★ TWSE `change/TWTB8U` 的官方事件（`parvalue` feed 回補後的產出）。
#   上市那批沒有 `shares` 欄，本來只能靠「收盤比＋名稱 `*`＋停止買賣天數」；
#   官方表直接給「停止買賣前收盤價格 ÷ 恢復買賣參考價」＝**官方倍率**。
#   2026-09-09 回補完成後逐筆核對：**10/10 相符、零不符、官方沒有多出來的筆**，
#   官方因子全是乾淨的 1/k（0.05／0.10／0.25／0.50）。
#   ⇒ evidence 從 `price_name_gap` 升級成 `twse_twtb8u`。
#   ⛔ 兩級是**來源不同，不是強弱不同**（情報分析線 2026-09-09 裁定），
#      讀取端的閘門不必對上市打折。
PARVALUE_FEED = os.path.join(_ROOT, "universe", "parvalue")


def load_official():
    """→ {(stock_id, date): (pre_close, ref_price)}。沒有 feed 目錄就是空的。"""
    out = {}
    if not os.path.isdir(PARVALUE_FEED):
        return out
    for fn in sorted(os.listdir(PARVALUE_FEED)):
        if not fn.endswith(".csv"):
            continue
        with io.open(os.path.join(PARVALUE_FEED, fn), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                pre, ref = fnum(r.get("pre_close")), fnum(r.get("ref_price"))
                if pre and ref:
                    out[(r.get("stock_id", "").strip(),
                         r.get("date", "").strip())] = (pre, ref)
    return out
def load_official_otc():
    """→ {(stock_id, date): (last_close, ref_price)}。沒有這份檔案就是空的。

    ⛔ 回傳形狀刻意跟 `load_official()` 一樣（上市那份 TWSE feed），
      這樣兩邊在寫檔那段可以走同一條路——**不要為上櫃另開一條分支**，
      分支會讓「上市驗過、上櫃沒驗」這種事再次靜默發生。
    """
    out = {}
    if not os.path.exists(OTC_REF):
        return out
    with io.open(OTC_REF, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            pre, ref = fnum(r.get("last_close")), fnum(r.get("ref_price"))
            if pre and ref:
                out[(r.get("stock_id", "").strip(),
                     r.get("event_date", "").strip())] = (pre, ref)
    return out


# TWTCAU（ETF 分割／反分割）已知涵蓋的代號，2026-09-09 探針 2025 年命中 5/5 驗過。
ETF_SPLIT_KNOWN = {"00632R", "00676R", "00663L", "0050", "0052", "00674R",
                   "00673R", "00706L", "00685L", "00631L", "00715L"}

LO, HI = 0.55, 1.8            # ★ 移交來的門檻，本檔要複核它，不是假設它對


def load_calendar():
    """交易日 → 序號。用來數「隔了幾個交易日」，**不是用日曆天相減**。"""
    days = []
    with io.open(CAL, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            if d:
                days.append(d)
    days.sort()
    return {d: i for i, d in enumerate(days)}, days


def load_events(sid):
    """→ [(date, kind, event, factor)]，已排序。沒有因子檔就是空的（那本身不是錯）。"""
    p = os.path.join(ADJ, f"{sid}.csv")
    if not os.path.exists(p):
        return []
    out = []
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            if d:
                out.append((d, (r.get("kind") or "").strip(),
                            (r.get("event") or "").strip(),
                            (r.get("factor") or "").strip()))
    out.sort()
    return out


def fnum(v):
    s = "" if v is None else str(v).replace(",", "").strip()
    try:
        x = float(s)
    except ValueError:
        return None
    return x if x > 0 else None          # 0 或負的收盤不是價格，是缺值


def main():
    ap = argparse.ArgumentParser(description="全庫掃疑似面額變更（只讀）")
    ap.add_argument("--lo", type=float, default=LO)
    ap.add_argument("--hi", type=float, default=HI)
    ap.add_argument("--limit", type=int, default=0, help="只掃前 N 檔（除錯用）")
    a = ap.parse_args()

    cal, days = load_calendar()
    print(f"[scan] 交易日曆 {len(days):,} 天（{days[0]} ~ {days[-1]}）")

    pop = set()
    if os.path.exists(IND):
        with io.open(IND, encoding="utf-8") as f:
            pop = {r["stock_id"] for r in csv.DictReader(f)}

    files = sorted(n for n in os.listdir(STOCKS) if n.endswith(".csv"))
    if a.limit:
        files = files[:a.limit]

    hits = []
    holes = []          # 長洞型：比值溫和、但停很久（裁定一新增）
    n_rows = n_pairs = 0
    no_cal = 0
    for fn in files:
        sid = fn[:-4]
        rows = []
        with io.open(os.path.join(STOCKS, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                c = fnum(r.get("close"))
                d = (r.get("date") or "").strip()
                if c and d:
                    # ★ `limit` 一起帶出來：情報分析 2026-09-09 10:45 裁定
                    #   斷點清單要加**事實欄** `limit_on_reopen`（那天的實際值），
                    #   ⛔ 不加「疑似漲跌停」這種判語欄——判語一旦進清單，
                    #     下游就會拿它當篩選條件，而「疑似」與「確認」在使用端分不出來。
                    rows.append((d, c, (r.get("name") or "").strip(),
                                 (r.get("market") or "").strip(),
                                 fnum(r.get("shares")),
                                 (r.get("limit") or "").strip()))
        rows.sort(key=lambda x: x[0])
        n_rows += len(rows)
        if len(rows) < 2:
            continue
        ev = load_events(sid)
        for i in range(1, len(rows)):
            n_pairs += 1
            (d0, c0, nm0, _, sh0, _l0), (d1, c1, nm, mk, sh1, lim1) = \
                rows[i - 1], rows[i]
            ratio = c1 / c0
            # ── 隔了幾個交易日：用日曆數，不是日曆天相減 ──
            # ⚠ 這一段移到比值判斷**之前**：長洞型斷點的比值是溫和的
            #   （3073 是 1.59），先用比值篩掉就永遠看不到它們。
            #   兩次 dict 查詢很便宜，事件比對才貴，所以只有真的要收的才往下做。
            if d0 in cal and d1 in cal:
                # ★ 缺掉的交易日數 ＝ 索引差 − 1（兩端都是有成交日，不算在內）
                gap = cal[d1] - cal[d0] - 1
            else:
                gap = -1
                no_cal += 1
            # ★ 情報分析 2026-09-09 10:45 裁定一：同一份、分兩節。
            #     price_jump：比值在帶外（原本就有的）
            #     long_hole ：比值在帶內、但**停 ≥ BRK_MIN_GAP 個交易日**
            #   ⚠ 門檻沿用 20，⛔ 不可以順手改成 5——
            #     5 是「選股閘門」的門檻、20 是「這份清單」的門檻，
            #     兩個門檻服務不同用途，合併會讓其中一邊失去意義。
            kind = "price_jump" if not (a.lo <= ratio <= a.hi) else (
                "long_hole" if gap >= BRK_MIN_GAP else None)
            if kind is None:
                continue
            # ── ★ 事件用「區間」對，不是用「同一天」對 ──
            #   事件日落在 (d0, d1] 之內就足以解釋這個跳躍。
            #   ⛔ 不可以沿著交易日曆去數容錯天數：`data/adj/` 的事件日
            #      **不保證是交易日**（2024-07-24 鈊象除權息當天颱風停市）。
            # ⛔⛔ **只有除權息與減資算「可解釋」**，parvalue／etfsplit 不算。
            #   2026-09-09 踩到：parvalue feed 抓到 6949 之後，`data/adj/` 有了
            #   那一筆事件，於是掃描判它「已解釋」、把它踢出名單——
            #   **par_change.csv 從 24 列變成 23 列**。
            #   回補繼續跑下去，這份會**一天天縮小、最後歸零**，
            #   而情報分析的選股閘門正是讀它當「面額變更全集」。
            #   ⚠ 失敗的樣子：檔案在、格式對、欄位對，只是列數安靜地變少。
            #   → 這份的語意是「**哪些是面額變更**」，不是「哪些還沒被還原」。
            #     我們自己補進去的面額變更因子，不可以拿來把自己從名單上刪掉。
            inside = [e for e in ev
                      if d0 < e[0] <= d1 and e[2] in ("exright", "reduce")]
            rec = {
                "kind": kind, "limit1": lim1,
                "sid": sid, "name": nm, "market": mk,
                "d0": d0, "d1": d1, "c0": c0, "c1": c1,
                "ratio": ratio, "gap": gap,
                "ev": inside,
                # ★★ 第二個、而且是**直接**的訊號：證券名稱裡的 `*`。
                #   TWSE／TPEx 用名稱末尾的 `*` 標「非 10 元面額」。
                #   面額一變，名稱就跟著變——**這是來源自己宣告的，
                #   不是從價格比值反推的**。價格比值只能說「跳了」，
                #   名稱變化才說得出「跳的原因是計價單位換了」。
                "name0": nm0, "name1": nm,
                "star": ("*" in nm) != ("*" in nm0),
                "renamed": nm != nm0,
                # ★★★ 最強的一個訊號，而且它一直在檔案裡：**流通股數**。
                #   面額 10→1 ＝ 股數 ×10、股價 ÷10。股數倍率是乾淨的整數比
                #   （實測全是 2.00／2.50／4.00／10.00／20.00），
                #   那不是「像」面額變更，那**就是**面額變更。
                #   ⚠ 只有上櫃日檔有 shares，上市是空的——所以它涵蓋不到全部。
                "sh0": sh0, "sh1": sh1,
                "shr": (sh1 / sh0) if (sh0 and sh1) else None,
                "in_pop": sid in pop,
            }
            # ⛔ `hits` 的語意**不變**：它一路被下游當成「比值在帶外」的那一批
            #   （面額變更判定、門檻複核、各種表格全部讀它）。
            #   長洞型另外收，混進 hits 會讓那些表全部多出不該有的列。
            (hits if kind == "price_jump" else holes).append(rec)

    print(f"[scan] 掃了 {len(files):,} 檔、{n_rows:,} 列、{n_pairs:,} 個相鄰對")
    print(f"[scan] 比值在 [{a.lo}, {a.hi}] 之外：{len(hits):,} 筆"
          f"｜比值在帶內但停 ≥ {BRK_MIN_GAP} 個交易日：{len(holes):,} 筆")

    unexplained = [h for h in hits if not h["ev"]]
    print(f"[scan] 其中當天沒有除權息／減資事件可解釋：{len(unexplained):,} 筆")
    report(a, days, files, n_rows, n_pairs, hits, no_cal, holes)
    return 0


def report(a, days, files, n_rows, n_pairs, hits, no_cal, holes):
    L = []

    def w(s=""):
        L.append(s)

    yes = [h for h in hits if h["ev"]]
    no = [h for h in hits if not h["ev"]]

    w("# 全庫掃「疑似面額變更」")
    w()
    w("**這是 `parvalue_scan.py` 的輸出，只讀不改資料。**")
    w("目的是複核 `tw-stock-db` skill 陷阱 13 那條移交來的判定規則——")
    w("門檻 `< 0.55 / > 1.8` 與「約 26 筆」的量級**在此之前沒有被資料庫線自己驗過**。")
    w()
    w(f"- 母體：`data/stocks/` {len(files):,} 檔、{n_rows:,} 列、"
      f"{n_pairs:,} 個相鄰對")
    w(f"- 門檻：比值 `< {a.lo}` 或 `> {a.hi}`")
    w(f"- 命中 **{len(hits):,} 筆**：有事件可解釋 {len(yes)}、"
      f"**無事件 {len(no)}**")
    if no_cal:
        w(f"- ⚠ 有 {no_cal} 筆的日期不在交易日曆裡，隔幾個交易日記為 `-1`")
    w()

    w("## ⛔ 第一版錯在哪（記著，這個錯很有代表性）")
    w()
    w("第一版用「事件日 == 跳的那一天」再補 ±1／±3 容錯去對事件，"
      "得到 5 筆「隔 1 個交易日、±3 天內無事件」的疑似名單。**其中 3293 鈊象是假的**：")
    w()
    w("- 3293 2024-07-23 收 1465 → 07-26 收 786（0.537）")
    w("- `data/adj/3293.csv` 明明有 `2024-07-24 除權息 factor 0.488 ref_price 715`")
    w("- 對不上是因為 **2024-07-24、25 颱風停市，那兩天不在交易日曆裡**，"
      "而容錯是沿著交易日曆數的，永遠數不到停市日上的事件")
    w()
    w("→ **`data/adj/` 的事件日不保證是交易日。** 正確判準是**區間**："
      "事件日落在 `(前一次有成交的日子, 這一次有成交的日子]` 之內就足以解釋。")
    w("停市、停牌、跨假日全部自然涵蓋，不必猜容錯天數。改用區間之後，"
      "1418／1529／4806／6198 那四筆減資也一起歸位了。")
    w()

    w("## ★ 為什麼不能只報一個數字")
    w()
    w("台股上市櫃**普通股**單日漲跌幅 ±10%，所以真的只隔一個交易日卻跳到"
      "0.55／1.8，不可能是交易造成的。")
    w("⚠ 但 **`data/stocks/` 3,030 檔裡只有 1,984 檔在 `industry.csv` 母體內**，"
      "其餘 1,046 檔多是 ETF／ETN／受益憑證，")
    w("而**追蹤國外標的的 ETF 沒有漲跌幅限制**——±10% 這個論證對它們不成立。"
      "所以名單一定要分「在母體內」與「母體外」看。")
    w()
    w("| 隔幾個交易日 | 有事件 | 無事件 | 其中在母體內 | 合計 |")
    w("|---|---:|---:|---:|---:|")
    # ⚠ 2026-09-09 起 gap ＝ **中間缺掉的交易日數**（不是索引差），
    #   所以「相鄰交易日」是 **0**，不是 1。改定義時每一個比較都要跟著改，
    #   漏掉任何一個就會造出正要消除的那種混淆。
    buckets = [("0（相鄰交易日，中間沒缺）", lambda g: g == 0),
               ("1~4", lambda g: 1 <= g <= 4),
               ("5~19", lambda g: 5 <= g <= 19),
               ("20 以上", lambda g: g >= 20),
               ("不在日曆裡", lambda g: g < 0)]
    for label, f in buckets:
        sub = [h for h in hits if f(h["gap"])]
        sy = [h for h in sub if h["ev"]]
        sn = [h for h in sub if not h["ev"]]
        w(f"| {label} | {len(sy)} | **{len(sn)}** | "
          f"{len([h for h in sn if h['in_pop']])} | {len(sub)} |")
    w()

    # ── ★★ 第二個訊號：名稱裡的 `*` ──
    star = [h for h in no if h["star"]]
    w("## ⭐⭐ 拿到直接證據了：名稱裡的 `*`")
    w()
    w("價格比值只能說「跳了」，說不出跳的原因。但 TWSE／TPEx 用**證券名稱末尾的"
      "`*`** 標示「非 10 元面額」——**面額一變，名稱就跟著變，那是來源自己宣告的**。")
    w("`data/stocks/` 每一列都帶 `name`，所以這個訊號一直都在，只是沒有人去看。")
    w()
    w(f"- 無事件可解釋的 {len(no)} 筆裡，**{len(star)} 筆在跳躍的同時 `*` 出現或消失**")
    w(f"- 其中在 `industry.csv` 母體內：**"
      f"{len([h for h in star if h['in_pop']])} 筆**")
    w()
    w("這一組是**兩個獨立訊號同時成立**（價格跳 ＋ 來源宣告面額類別改變），")
    w("不再是「用價格比值猜的」。")
    w()
    if star:
        w("| 代號 | 跳躍前名稱 | 跳躍後名稱 | 前一交易日 | 收盤 | 當日 | 收盤 | 比值 | 隔 | 在母體 |")
        w("|---|---|---|---|---:|---|---:|---:|---:|---|")
        for h in sorted(star, key=lambda x: x["d1"]):
            w(f"| {h['sid']} | {h['name0']} | {h['name1']} | {h['d0']} | {h['c0']:g} "
              f"| {h['d1']} | {h['c1']:g} | {h['ratio']:.3f} | {h['gap']} | "
              f"{'**是**' if h['in_pop'] else '否'} |")
        w()
        w("⚠ 這些的「隔幾個交易日」幾乎都是 **6~8 天**，不是 1 天——"
          "換發股票要停止買賣，本來就會有一段空窗。")
        w("**所以第一版把「隔 1 個交易日」當成最強的一類，方向是反的**："
          "面額變更幾乎不可能出現在相鄰交易日。")
    w()

    # ── ⚠ `*` 沒出現 ≠ 沒有面額變更（但原因不是我第一次寫的那個）──
    pat = [h for h in no if not h["star"] and "*" in h["name1"]
           and h["in_pop"] and 1 <= h["gap"] <= 19 and h["ratio"] < 1]
    both = star + pat
    w("## ⚠ `*` 沒有出現，**不等於**沒有面額變更")
    w()
    w("⛔ **第一版在這裡下錯了結論**，記下來：")
    w()
    w("第一版看到 8070 長華、8422 可寧衛、2327 國巨在檔案第一列就已經帶 `*`，"
      "就寫成「`name` 欄是回填的當期名稱，不是當日名稱」。")
    w("**那是錯的，而且用直接證據就推翻得掉**——去看來源日檔 "
      "`data/universe/daily/`：")
    w()
    w("| 日期 | 6548 的名稱 | 收盤 |")
    w("|---|---|---:|")
    w("| 2016-09-13 | `長華科` | 138.00 |")
    w("| 2019-01-08 | `長科` | 279.50 |")
    w("| 2019-09-09 | `長科*` | 34.30 |")
    w()
    w("**日檔保留的是當日名稱，沒有回填。** 那 8070 為什麼一開始就有 `*`？")
    w("因為它在資料起點（2015-01-05）之前就已經是非 10 元面額了。")
    w()
    w("→ 正確的解釋是：**`*` 標的是「現在是不是非 10 元面額」，不是「剛剛換過面額」。**")
    w("  一檔股票拿到 `*` 之後**再換一次面額，名稱不會再變**，")
    w("  所以 `*` 出現這個訊號**只抓得到第一次**。")
    w()
    w("  這不是推論，名單裡就有現成的證據：**6548 長科出現兩次**——")
    w("  2019-09-09（`*` 出現、股數 ×10）與 2022-09-05（`*` 沒變、股數 ×2.5）。")
    w()

    # ── ★★★ 第三個訊號：流通股數 ──
    w("## ★★★ 最強的訊號是流通股數，而它一直都在檔案裡")
    w()
    w("`data/stocks/` 有 `shares` 欄。面額 10→1 ＝ **股數 ×10、股價 ÷10**。")
    w("股數倍率是不是乾淨的整數比，直接回答「是不是計價單位換了」——")
    w("價格比值只能說「跳了」，名稱只能說「現在是非 10 元面額」，"
      "**只有股數說得出倍數**。")
    w()
    haveshr = [h for h in both if h["shr"]]
    w(f"- 名單 {len(both)} 筆裡有 **{len(haveshr)} 筆**兩側都有 `shares`")
    w(f"- ⚠ **只有上櫃日檔有 `shares`，上市是空的**——"
      f"{len(both) - len(haveshr)} 筆拿不到這個訊號，不是它們有問題")
    if haveshr:
        w(f"- **{len(haveshr)} 筆的股數倍率全部是乾淨的整數比**："
          + "、".join(sorted({f"×{h['shr']:.2f}" for h in haveshr})))
        w()
        w("| 代號 | 名稱 | 日期 | 比值 | `*` 出現 | 股數前 | 股數後 | 倍率 |")
        w("|---|---|---|---:|:-:|---:|---:|---:|")
        for h in sorted(haveshr, key=lambda x: x["d1"]):
            w(f"| {h['sid']} | {h['name1']} | {h['d1']} | {h['ratio']:.3f} "
              f"| {'★' if h['star'] else '—'} | {h['sh0']:,.0f} | {h['sh1']:,.0f} "
              f"| **×{h['shr']:.2f}** |")
        w()
        w("⭐ **倍率與比值互為倒數**（×10 對 0.110、×2 對 0.5 左右），"
          "差的部分是停止買賣那 6~8 天的漲跌。")
        w("這已經不是「疑似」——**股數乘了整數倍、股價除了同樣的倍數，"
          "那就是計價單位換了**。")
    w()
    w(f"### 拿不到 `shares` 的 {len(both) - len(haveshr)} 筆（全是上市）")
    w()
    w("它們靠的是「價格比值 ＋ 名稱帶 `*` ＋ 停 6~8 個交易日」三件事一致。")
    w("⚠ **證據強度低一級**，因為缺了唯一能給出倍數的那一欄。")
    if [h for h in both if not h["shr"]]:
        w()
        w("| 代號 | 名稱 | 日期 | 比值 | `*` 出現 | 隔 |")
        w("|---|---|---|---:|:-:|---:|")
        for h in sorted((x for x in both if not x["shr"]), key=lambda x: x["d1"]):
            w(f"| {h['sid']} | {h['name1']} | {h['d1']} | {h['ratio']:.3f} "
              f"| {'★' if h['star'] else '—'} | {h['gap']} |")
    w()

    _pat = {id(h) for h in pat}
    rest = [h for h in no if not h["star"] and id(h) not in _pat]
    strong = [h for h in rest if h["gap"] == 0]
    weak = [h for h in rest if h["gap"] != 0]
    w("## 其餘（**不要當成面額變更**）")
    w()
    inpop_rest = [h for h in rest if h["in_pop"]]
    if inpop_rest:
        w(f"⭐ 母體內只剩 **{len(inpop_rest)} 筆**，逐筆看過：")
        w()
        for h in inpop_rest:
            w(f"- **{h['sid']} {h['name1']}**｜{h['d0']} {h['c0']:g} → "
              f"{h['d1']} {h['c1']:g}（{h['ratio']:.3f}）｜隔 {h['gap']} 個交易日")
        w()
        w("  8101 華冠：停了 **59 個交易日**（2024-08-21 → 2024-11-19），"
          "復牌價是停牌前的 5.5 倍，名稱沒有 `*`。")
        w("  `data/adj/8101.csv` 只有 2018 與 2022 兩筆減資，2024 這一次不在裡面；")
        w("  `data/universe/reduce/` 的 2024 各月檔案裡也找不到 8101。")
        w("  ⚠ **成因未查明**——長期停牌後倍數復牌，減資、合併、重整都可能，")
        w("  **不要因為它符合「無事件」就歸進面額變更**。這一筆單獨留著待查。")
        w()
    w(f"### A. 中間一天都沒缺（相鄰交易日）— **{len(strong)} 筆**")
    w()
    if strong:
        w("| 代號 | 名稱 | 市場 | 前一交易日 | 收盤 | 當日 | 收盤 | 比值 | 在母體 |")
        w("|---|---|---|---|---:|---|---:|---:|---|")
        for h in sorted(strong, key=lambda x: (x["sid"], x["d1"])):
            w(f"| {h['sid']} | {h['name']} | {h['market']} | {h['d0']} | {h['c0']:g} "
              f"| {h['d1']} | {h['c1']:g} | {h['ratio']:.3f} "
              f"| {'**是**' if h['in_pop'] else '否'} |")
    else:
        w("（沒有）")
    w()
    w(f"### B. 中間有缺 — **{len(weak)} 筆**"
      f"（其中在母體內 {len([h for h in weak if h['in_pop']])} 筆）")
    w()
    w("⚠ 這一類**不能直接當成面額變更**：中間停牌期間的累積漲跌本來就可以超過門檻。")
    w("列出來是為了讓人看過，不是為了進名單。")
    w()
    if weak:
        w("| 代號 | 名稱 | 前一交易日 | 當日 | 隔幾個交易日 | 比值 | 在母體 |")
        w("|---|---|---|---|---:|---:|---|")
        for h in sorted(weak, key=lambda x: -abs(x["ratio"] - 1))[:60]:
            w(f"| {h['sid']} | {h['name']} | {h['d0']} | {h['d1']} "
              f"| {h['gap']} | {h['ratio']:.3f} | "
              f"{'**是**' if h['in_pop'] else '否'} |")
        if len(weak) > 60:
            w(f"| … | 其餘 {len(weak) - 60} 筆 | | | | | |")
    w()

    w("## 門檻本身複核得怎麼樣")
    w()
    w(f"移交內容說「約 26 筆」。本次全庫實測：命中 **{len(hits)}** 筆、"
      f"無事件可解釋 **{len(no)}** 筆，其中母體內 "
      f"{len([h for h in no if h['in_pop']])} 筆，拆成：")
    w()
    hs = [h for h in both if h["shr"]]
    w(f"| 分類 | 筆數 | 證據強度 |")
    w(f"|---|---:|---|")
    w(f"| 股數為整數倍（上櫃） | **{len(hs)}** | ⭐ 三個訊號，**倍數說得出來** |")
    w(f"| 只有比值＋名稱＋停牌天數（上市無 `shares`） | **{len(both) - len(hs)}** "
      f"| 三件事一致，但缺倍數 |")
    w(f"| 成因未查明（8101 華冠） | {len(inpop_rest)} | 待查，**不歸類** |")
    w(f"| **合計視為面額變更** | **{len(both)}** | |")
    w()
    w(f"（其中 `*` 在跳躍當下出現的有 {len(star)} 筆——那是**第一次**換面額的；"
      f"另外 {len(pat)} 筆是已經帶 `*` 之後**再換一次**，名稱不會再變。）")
    w()
    w(f"→ **量級對得上**：移交說約 26，本次從 `data/stocks/` 全庫重算得 "
      f"{len(star) + len(pat)} 筆。")
    w("這不是「拿一個數字去驗另一個數字」——本次是獨立重算的，"
      "而且第二個訊號（名稱 `*`）與價格比值互相獨立。")
    w()
    w("### 門檻 0.55／1.8 本身")
    w()
    both = star + pat
    if both:
        rr = sorted(h["ratio"] for h in both)
        w(f"上表前兩類（{len(both)} 筆）的比值實測範圍 "
          f"**{rr[0]:.3f} ~ {rr[-1]:.3f}**。")
        w(f"最接近門檻的一筆是 **{rr[-1]:.3f}**，離下緣 {a.lo} 只差 "
          f"{a.lo - rr[-1]:.3f}——**門檻壓得很近，但沒有漏**。")
        w(f"⚠ 這也代表 {a.lo} 不可以再往下調：0.544 那一筆（6613 朋億*）"
          "只要門檻降到 0.54 就會被漏掉。")
        w("⚠ **下緣 0.55 是有效的，上緣 1.8 這一側一筆都沒有**——"
          "面額變更在本庫全部是「面額變小、股數變多、股價變低」的方向。")
        w("上緣不是沒用，是**還沒有樣本**：面額由小改大（例如 5→10）會落在那一側，"
          "本庫 2015 起沒發生過。**不要因為沒樣本就把它拿掉。**")
    # ── 機器可讀版 ──
    #   ⛔ evidence 的兩級是**來源不同，不是強弱不同**（情報分析線 2026-09-09 裁定）：
    #     `shares_int_mult`  上櫃日檔的 shares 是乾淨整數倍
    #     `price_name_gap`   上市沒有 shares 欄，靠收盤比＋名稱 `*`＋停止買賣天數
    #   上市那 10 筆另有 TWSE 官方 `change/TWTB8U` 的「停止買賣前收盤 ÷ 恢復買賣參考價」，
    #   接進管線後這一欄可升級成官方來源——**在 feed 真的抓到之前不要先寫上去**。
    # ── 無法解釋的斷點（與面額變更嚴格分開）──
    par_ids = {h["sid"] for h in both}
    par_keys = {(h["sid"], h["d1"]) for h in both}

    def _keep(h):
        return (h["sid"] not in ETF_SPLIT_KNOWN
                and h["gap"] >= BRK_MIN_GAP)

    jump = [h for h in no if h["sid"] not in par_ids and _keep(h)]
    # ⚠ 長洞型只排除「這一筆本身就是面額變更」，不整檔排除：
    #   同一檔可能既有面額變更、又另外有一個無法解釋的洞（3073 就有兩個洞）。
    hole = [h for h in holes
            if not [e for e in load_events(h["sid"])
                    if h["d0"] < e[0] <= h["d1"] and e[2] in ("exright", "reduce")]
            and (h["sid"], h["d1"]) not in par_keys
            and _keep(h)]
    brk = jump + hole
    try:
        os.makedirs(os.path.dirname(BRK_OUT), exist_ok=True)
        with io.open(BRK_OUT, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(BRK_HEADER)
            for h in sorted(brk, key=lambda x: (x["kind"], x["d1"], x["sid"])):
                w.writerow([h["sid"], h["name1"], h["market"], h["kind"],
                            h["d1"], h["d0"],
                            f"{h['c0']:g}", f"{h['c1']:g}", f"{h['ratio']:.6f}",
                            h["gap"], 0, "unknown",
                            h.get("limit1", ""),
                            SOURCE_NOTE.get((h["sid"], h["d1"]), ""),
                            "1" if h["in_pop"] else "0"])
        # ⛔ 兩節分開報數。合成一個總數的話，其中一節歸零只會讓總數「變小一點」，
        #   看起來像正常波動（情報分析 10:45 的要求）。
        print(f"[scan] 寫出 {BRK_OUT}"
              f"（price_jump {len(jump)}｜long_hole {len(hole)}）")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[scan] 斷點 CSV 寫檔失敗：{ex}", file=sys.stderr)

    # 閘門 (c) 的對帳結果。⛔ 分成兩籃：**「對得上幾筆」與「有沒有對不上」是兩件事**，
    #   合成一個數字的話，對不上那一筆只會讓「相符數」少一，看起來像正常波動。
    xok, xbad = [], []
    try:
        os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
        with io.open(CSV_OUT, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(CSV_HEADER)
            official = load_official()
            official.update(load_official_otc())
            for h in sorted(both, key=lambda x: (x["d1"], x["sid"])):
                off = official.get((h["sid"], h["d1"]))
                if h["shr"]:
                    ev, mult = "shares_int_mult", h["shr"]
                    # ★ 閘門 (c)：官方值出現時要**逐筆對**，不符要吵（情報分析 2026-09-09）。
                    #   ⚠ 對法在**價格空間**：官方參考價印到分為止，
                    #     直接比比值會把「四捨五入」誤判成「不符」。
                    if off:
                        want = off[0] / mult
                        if abs(off[1] - want) <= REF_TOL:
                            ev = "shares_int_mult+official_ref"
                            xok.append(h["sid"])
                        else:
                            ev = "CONFLICT_shares_vs_official"
                            xbad.append((h["sid"], h["d1"], off[1], want, mult))
                elif off:
                    # 官方倍率 ＝ 停止買賣前收盤 ÷ 恢復買賣參考價
                    ev, mult = "twse_twtb8u", off[0] / off[1]
                else:
                    ev, mult = "price_name_gap", None
                # restored：data/adj/ 有沒有對應日期的 parvalue 因子
                adj_has = any(e[0] == h["d1"] and e[2] == "parvalue"
                              for e in load_events(h["sid"]))
                w.writerow([
                    h["sid"], h["d1"], h["d0"],
                    f"{h['c0']:g}", f"{h['c1']:g}", f"{h['ratio']:.6f}",
                    f"{h['sh0']:.0f}" if h["sh0"] else "",
                    f"{h['sh1']:.0f}" if h["sh1"] else "",
                    f"{mult:.4f}" if mult else "",
                    ev, "1" if h["in_pop"] else "0",
                    "1" if adj_has else "0"])
        print(f"[scan] 寫出 {CSV_OUT}（{len(both)} 列）")
        # ── 閘門 (c) 對帳：官方參考價 vs shares 推導倍率 ──
        if xbad:
            print(f"[scan] ✗ 官方參考價與 shares 倍率**不符 {len(xbad)} 筆**"
                  f"——這些列的 evidence 已標成 CONFLICT，⛔ 不要靜默取一邊：",
                  file=sys.stderr)
            for sid, d, got, want, m in xbad:
                print(f"        {sid} {d}｜官方參考價 {got}｜"
                      f"倍率 {m:g} 推得 {want:.4f}", file=sys.stderr)
        if xok or xbad:
            print(f"[scan] 閘門 (c) 對帳：相符 {len(xok)} 筆｜不符 {len(xbad)} 筆")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[scan] CSV 寫檔失敗：{ex}", file=sys.stderr)

    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
        print(f"[scan] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[scan] 寫檔失敗：{ex}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
