#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""keys_probe.py — 官方回應裡**我方一路丟掉的那些鍵**到底寫了什麼。

## 為什麼開這一支

使用者 2026-09-10 問：「官方回應裡有 `notes` 欄，我一直沒讀，對妳有用嗎？」
⇒ 先查我方到底有沒有讀。結果是**完全沒有**：

    _tables() 只取 title / fields / data
    ⛔ 被丟掉的：stat、date、notes、hints、params、total …
    而且丟的時候**沒有任何紀錄**——連「有這些鍵」都不知道。

⭐ 這一支不猜「notes 有沒有用」，它**把那些鍵原文印出來**，讓資料自己回答。

## ⭐ 三個已經看得出來的用處（各自對應一件我今晚手工做的事）

### ① `total`：官方自己說有幾列 ⇒ **免費的每次請求完整性斷言**

我今晚為了「有沒有漏」自己造了好幾個判準：
N₁、Σ上市 amount ÷ 官方大盤、六張官方清單差集（67,446 筆）……
⚠ 而端點可能**每一次都在告訴我它給了幾列**。
⇒ `total` vs `len(data)` vs 我方寫出的列數，三個數字對不上就該叫。

### ② `params`：⇒ **「參數有沒有生效」的直接檢查**

今天為了防「靜靜回今天」，我在三支程式裡各寫了一道
「回應要講出我請求的那一天」。而 `params` 是端點**把收到的參數回顯**——
情報分析線 09:47 就是靠它才看懂 `TWTAWU` 的 `date=` 是假參數
（`params` 回 `{date:"20150105", startDate:"20260813", endDate:"20260813"}`）。

### ③ `notes`：⇒ 可能是 **`X` 旗標的權威出處**

`adj_gap.py` 有五處寫著「官方 `X0.00`，`X` ＝ 無前一日收盤價可資比較」，
而那一句**我方沒有留下出處**——它是推論還是讀來的，現在說不清。
⚠ 而那句話正是「轉上市首日不算缺陷」這個歸因的地基。
⇒ 若 `notes` 裡有符號說明，它就是權威出處；若沒有，那句話要降級成推論。

⛔ 本支**只讀不寫資料**，輸出進 `data/meta/_keys_probe.txt`。
"""
import io
import csv
import json
import os
import sys
import traceback

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_keys_probe.txt")

DAY = "2026-09-09"
YMD = DAY.replace("-", "")
TW = "https://www.twse.com.tw/rwd/zh"
TP = "https://www.tpex.org.tw"

# ⛔ 只挑**我方每天真的在用**的端點。加一堆沒在用的只會讓報告變長。
# ⭐ 第三個元素是「我送出去的參數」——有了它才對得起 `params` 回顯，
#   而那正是看穿「假參數」的方法（TWTAWU 的 `date=` 就是假的）。
TARGETS = [
    ("上市每日收盤行情 MI_INDEX",
     f"{TW}/afterTrading/MI_INDEX?date={YMD}&type=ALLBUT0999&response=json",
     {"date": YMD, "type": "ALLBUT0999"}),
    ("上市三大法人 T86",
     f"{TW}/fund/T86?date={YMD}&selectType=ALLBUT0999&response=json", {"date": YMD}),
    ("上市融資融券 MI_MARGN",
     f"{TW}/marginTrading/MI_MARGN?date={YMD}&selectType=ALL&response=json", {"date": YMD}),
    ("上市外資持股 MI_QFIIS（上市 shares 的來源）",
     f"{TW}/fund/MI_QFIIS?date={YMD}&selectType=ALLBUT0999&response=json", {"date": YMD}),
    ("上市除權息 TWT49U",
     f"{TW}/afterTrading/TWT49U?date={YMD}&response=json", {"date": YMD}),
    ("上市暫停交易 TWTAWU",
     f"{TW}/afterTrading/TWTAWU?startDate=20150101&endDate={YMD}&response=json",
     {"startDate": "20150101", "endDate": YMD}),
    ("上櫃每日收盤行情",
     f"{TP}/www/zh-tw/afterTrading/otc?date={DAY.replace('-', '/')}&response=json",
     {"date": DAY.replace('-', '/')}),
    ("上櫃融資融券 margin/balance",
     f"{TP}/www/zh-tw/margin/balance?date={DAY.replace('-', '/')}&response=json",
     {"date": DAY.replace('-', '/')}),
    # ⭐⭐ 2026-09-14 加：回測線問「本庫有沒有加權指數日線」。
    #   ⇒ `data/history/market_index.csv` **有**，⛔ 只有 9 列（2026-09-01 起累積）。
    #   ⚠ 而 `calendar_audit.py` **早就在逐月抓這一支**（2015-01 起、140 個月、
    #     已有標題驗證），⛔ 而它只留首欄日期，**其餘欄整列丟掉**
    #     ——正是本檔開頭在講的那件事，只是這次丟掉的是加權指數本身。
    #   ⇒ 動手改之前先照第一點把 `fields` 原文印出來：⛔ 我**沒有**印過它，
    #     「第 4 欄是發行量加權股價指數」目前是**推測**，不是實測。
    ("上市大盤日成交資訊 FMTQIK（月頻｜⭐ 加權指數日線的候選來源）",
     f"{TW}/afterTrading/FMTQIK?date={YMD[:6]}01&response=json",
     {"date": YMD[:6] + "01"}),
]

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def _write(rc):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write(B.probe_stamp())
            f.write("# keys_probe.py 的輸出。**只讀不寫資料。**\n")
            f.write("# 問的是：官方回應裡那些我方一路丟掉的鍵，到底寫了什麼。\n")
            f.write("# ⛔ 我方 `_tables()` 只取 title/fields/data，其餘全丟，"
                    "而且丟的時候沒有紀錄。\n\n")
            f.write("\n".join(LINES) + "\n")
        print(f"\n[keys] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[keys] 寫檔失敗：{ex}", file=sys.stderr)
    return rc


def show(label, url, want=None):
    say(f"── {label}")
    say(f"   {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err or not raw:
        say(f"   ✗ 抓不到：{str(err)[:120]}")
        say("")
        return
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        head = raw[:100].decode("utf-8", "replace").replace("\n", " ")
        say(f"   ✗ 不是 JSON（{str(ex)[:40]}）｜開頭={head!r}"
            "　⚠ 若是 HTML 多半是被擋")
        say("")
        return
    if not isinstance(d, dict):
        say(f"   ⚠ 頂層不是 dict，是 {type(d).__name__}")
        say("")
        return
    # ⛔ 這裡本來自己抄了一份「攤開被丟掉的鍵」的邏輯。
    #   同一段邏輯抄兩份今晚已經害過一次（`limit` 的 bug 在兩支裡各一份）。
    #   ⇒ 改用共用的 `B.describe_response()`，那也是使用者
    #     「新端點第一件事就是把 notes／hints／title 印出來」那條規矩的執行者。
    for ln in B.describe_response(d, want=want):
        say(f"   {ln}")
    # ⭐⭐ 2026-09-14 加：**把 `fields` 逐字印出來**。
    #   ⛔ 起因是我要替 T86 加「自營商(自行買賣)／(避險)」兩欄，
    #     而我**不知道官方那兩欄叫什麼**——而第二點⑤說得很清楚：
    #     **名字不是證據**，⛔ 不可以照別張表的欄名去猜這一張。
    #   ⚠ 而這支探針本來就打了 T86，卻**只印被丟掉的鍵、沒印 fields**
    #     ⇒ 要寫解析的人還是得自己再打一次。⇒ 一起印。
    #   ⚠ `_tables()` 那一族（tables 包起來的）也要照顧到。
    fs = d.get("fields")
    if not fs:
        for t in (d.get("tables") or []):
            if isinstance(t, dict) and t.get("fields"):
                fs = t["fields"]
                break
    if fs:
        say(f"   ⭐ fields（{len(fs)} 欄，逐字）：")
        for i, c in enumerate(fs):
            say(f"      [{i:>2}] {c}")
    else:
        say("   ⚠ 這個回應**沒有 fields**（⛔ 不是「我沒印」）")
    # ⭐⭐ 2026-09-14 加：**第一列資料逐字印出來，對齊 fields**。
    #   ⛔ 起因：FMTQIK 我印到了 `[5] 漲跌點數`，⚠ 而「它帶不帶正負號」
    #     欄名**講不出來**——MI_INDEX 那張表的正負號在**另一個欄**
    #     （`漲跌(+/-)`），⇒ 照它去猜 FMTQIK 就是第二點⑤「名字不是證據」。
    #   ⚠ 同理還有千分位逗號、破折號代表的空值、數字有沒有引號。
    #   ⇒ 只印**一列**（⛔ 不洗版），而且是 `repr`：逗號、空白、全形字
    #     在 repr 裡看得見，⛔ 在 print 裡看不見。
    rows = d.get("data")
    if not rows:
        for t in (d.get("tables") or []):
            if isinstance(t, dict) and t.get("data"):
                rows = t["data"]
                break
    if rows:
        r0 = rows[0]
        say(f"   ⭐ 第一列（共 {len(rows):,} 列，逐字 repr）：")
        if isinstance(r0, (list, tuple)):
            for i, v in enumerate(r0):
                nm = fs[i] if fs and i < len(fs) else "?"
                say(f"      [{i:>2}] {nm}　= {v!r}")
        else:
            say(f"      {r0!r}")
    else:
        say("   ⚠ 這個回應**沒有 data 列**（⛔ 不是「我沒印」）")
    say("")


def _our_twse_total(iso):
    """我方日檔那一天的 **twse 合計**。→ dict 或 None（那一天不在這個 ref 上）。

    ⛔ 讀不到要回 None 讓呼叫端說「這一格沒量到」，⚠ 不是回 0
    ——0 跟「那一天真的沒有成交」長得一樣。
    """
    p = os.path.join(_ROOT, "universe", "daily", f"{iso}.csv")
    if not os.path.exists(p):
        return None
    out = {"n": 0, "volume": 0.0, "amount": 0.0, "transactions": 0.0}
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("market") != "twse":
                continue
            out["n"] += 1
            for k in ("volume", "amount", "transactions"):
                v = (r.get(k) or "").replace(",", "").strip()
                try:
                    out[k] += float(v)
                except ValueError:
                    pass
    return out if out["n"] else None


def _row_for_day(fields, rows, day):
    """挑出「日期」欄等於 `day` 的**那一列**，解成 {欄名: 數字}。→ dict 或 {}。

    ⛔⛔ 沒有這一支的時候，F2 那一節把 FMTQIK 的**整月合計**跟我方的**單日**
    並排印 ⇒ ⚠ 兩個數字長得一樣可比，而它們不是同一個量。

    ⚠ 官方的日期是民國（`115/09/09`），⭐ 而傳進來的 `day` 是西元 `20260909`
    ⇒ 兩種都比得上（⛔ 不要只比一種：換一個端點格式就不一樣了）。
    """
    if not fields or not rows:
        return {}
    di = next((i for i, f in enumerate(fields) if "日期" in str(f)), None)
    if di is None:
        return {}
    y, m, d = day[:4], day[4:6], day[6:]
    want = {f"{y}{m}{d}", f"{y}/{m}/{d}", f"{int(y) - 1911}/{m}/{d}",
            f"{y}-{m}-{d}"}
    for r in rows:
        if di >= len(r):
            continue
        if str(r[di]).strip() in want:
            return _sum_by_name(fields, [r])
    return {}


def _sum_by_name(fields, rows):
    """把**看起來像總量**的欄逐欄加總。→ dict[欄名, 合計]（沒有就回 {}）。

    ⛔ 照**欄名**取，⚠ 不是位置（`calendar_audit.index_of_row` 那條：
    「今天在 [4]」不保證 2015 年那幾個月也在 [4]）。
    """
    want = ("成交股數", "成交金額", "成交筆數", "成交數量", "成交值")
    idx = {c: i for i, c in enumerate(fields or []) if str(c).strip() in want}
    if not idx:
        return {}
    out = {}
    for name, i in idx.items():
        t = 0.0
        for r in rows:
            if i >= len(r):
                continue
            v = str(r[i]).replace(",", "").strip()
            try:
                t += float(v)
            except ValueError:
                pass
        out[name] = t
    return out


def f2_kou_jing(day):
    """⭐⭐ F2：**大盤總量那三欄的口徑差，到底差在哪**——四條路同一天各量一次。

    ## ⛔ 為什麼要有這一段

    `calendar_audit.index_of_row` 的檔頭寫著（2026-09-14 實測）：

    ```
    2026-09-01   我方(MI_INDEX)          FMTQIK
    成交金額     1,090,449,046,456   1,187,571,567,117   ＋8.9%
    成交股數         5,209,282,128      13,000,849,196   ⛔ **2.5 倍**
    ```

    ⇒ 結論是「口徑不同 ⇒ FMTQIK 那三欄不可用來回補」。**那個結論本身沒有錯**，
    ⚠ 而它只比了**兩條路**——⛔ 而我方其實有**第三條**：
    `data/universe/daily/` 的 twse 列**自己加總**。

    ⭐ 2026-09-15 離線量一次（同一天 2026-09-01，1,377 列 twse）：

    ```
                  我方日檔合計        FMTQIK             差
    成交金額   1,182,898,779,151   1,187,571,567,117   **−0.40%**
    成交筆數           5,163,637           5,301,801   **−2.6%**
    成交股數       9,235,110,196      13,000,849,196   ⛔ −29%
    ```

    ⇒ ⭐⭐ **金額與筆數幾乎對得上**，⛔ 而股數還差 29%
    ⇒ 「口徑差」不是一個籠統的差，**它落在不同欄、幅度也不同**。

    ⚠ 而官方自己有一張 `BFIAUU`（**鉅額交易**日成交量值統計）
    ——⭐ 那正是 `notes` 提過的口徑項之一。⇒ 這一段把**四條路**擺在一起：

    ```
    ① FMTQIK 的三欄
    ② 鉅額交易日統計（BFIAUU）
    ③ 我方日檔 twse 列的合計（⛔ 離線算，這裡只提醒要去算）
    ④ MI_INDEX 的大盤列
    ```

    ⛔ 這一段**不下結論**：口徑要採哪一種是**換供料的決定**（第五點），
    ⇒ 歸市場情報分析線裁。⭐ 這裡只負責把四個數字擺在同一頁上。
    """
    say("")
    say("── ⭐⭐ F2：大盤總量三欄的**口徑差落在哪**（四條路同一天各量一次）──")
    say(f"   測試日 {day}｜⛔ 這一段不下結論：採哪一種口徑是**換供料的決定**（第五點）")
    say("   ⭐ 離線已量到的兩項（2026-09-01，我方日檔 twse 1,377 列）：")
    say("      我方日檔合計  金額 1,182,898,779,151｜筆數 5,163,637｜股數 9,235,110,196")
    say("      FMTQIK        金額 1,187,571,567,117｜筆數 5,301,801｜股數 13,000,849,196")
    say("      ⇒ ⭐ 金額 **−0.40%**、筆數 **−2.6%**，⛔ 而股數 **−29%**")
    say("      ⇒ ⚠ 口徑差**不是一個籠統的差**：它落在不同欄、幅度也不同")
    # ⛔⛔ 上面那三行是 **2026-09-01** 量的，而下面打的是 `DAY`
    #   ⇒ ⚠ 兩個不同的日子並排，讀的人會以為是同一天（錨點要落在同一格）。
    #   ⭐ ⇒ 下面**同一天**把三條路各算一次，讓算術當場成立或不成立。
    iso = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    mine = _our_twse_total(iso)
    say("")
    say(f"  ── ⭐ 同一天（{iso}）三條路並排")
    if mine is None:
        say(f"     ⚠⚠ **這一格沒量到**：這個 ref 上沒有 "
            f"`data/universe/daily/{iso}.csv` ⇒ ⛔ 不算失敗，⛔ 也不算驗過")
    else:
        say(f"     ① 我方日檔 twse {mine['n']:,} 列｜"
            f"股數 {mine['volume']:,.0f}｜金額 {mine['amount']:,.0f}｜"
            f"筆數 {mine['transactions']:,.0f}")

    for label, url, note in (
            ("FMTQIK（同一天，⭐ 拿來當被減數）",
             f"{TW}/afterTrading/FMTQIK?date={day}&response=json", "fmtqik"),
            ("鉅額交易**日**成交量值統計 BFIAUU",
             f"{TW}/block/BFIAUU?date={day}&response=json&type=day", "block"),
            ("每日上市上櫃跨市場成交資訊 MI_INDEX4",
             f"{TW}/indices/MI_INDEX4?date={day}&response=json", "x"),
            # ⭐⭐ 2026-09-15 加：F2 卡在一句**未驗的候選**——
            #   「那 29% 的股數缺口是**權證**」（我方母體刻意排除、FMTQIK 含）。
            # ⛔ 而我方庫裡沒有權證的量 ⇒ 離線量不到。
            # ⇒ MI_INDEX 的回應裡有**分類別**的大盤統計（股票／權證／ETF／…），
            #   ⭐ 而下面那個迴圈本來就會逐表印標題、欄名與逐欄合計
            #   ⇒ 把它加進來，那張表**自己會講出**權證那一列是多少。
            # ⛔ 這裡**不猜 type**：用我方既有那一個（`ALLBUT0999`，第 62 行那條）。
            ("上市每日收盤行情 MI_INDEX（⭐ 要的是它的**分類別**大盤統計）",
             f"{TW}/afterTrading/MI_INDEX?date={day}&type=ALLBUT0999"
             "&response=json", "x")):
        say("")
        say(f"  ── {label}")
        say(f"     {url}")
        raw, err = B.get(url, retries=2, timeout=60)
        if err:
            say(f"     ⛔ 取不回來：{B.why(err, 200)}　⇒ 這一條**沒量到**"
                "（⛔ 不是「官方沒有」）")
            continue
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            # ⭐ 不是 JSON 時要把**前 300 字**印出來——⛔ 只寫「不是 JSON」
            #   跟「官方沒有這條」在紙上一樣（第二點④：被 CDN 擋回 HTML）
            say(f"     ⛔ 不是 JSON（{len(raw):,} bytes）⇒ 這一條**沒量到**")
            say(f"     ⭐ 前 300 字：{B.visible_text(raw, ' ')[:300]}")
            continue
        # ⭐ 第一點：先把**全部頂層鍵**攤開再看資料
        for ln in B.describe_response(d, want={"date": day}):
            say("     " + ln)
        # ⭐⭐ 而**數字**要印出來，⛔ 不是只印被丟掉的鍵
        #   ——沒有數字，「口徑差落在哪一欄」這個問題答不了。
        for ti, t in enumerate(B._tables(d) or []):
            rows = t.get("data") or []
            fl = t.get("fields") or []
            say(f"     表{ti}：{str(t.get('title'))[:60]!r}｜{len(fl)} 欄 × "
                f"{len(rows)} 列")
            say(f"          欄名：{fl}")
            tot = _sum_by_name(fl, rows)
            if tot:
                say("          ⭐ 逐欄合計："
                    + "｜".join(f"{k} {v:,.0f}" for k, v in tot.items()))
            # ⛔⛔ 這裡本來是 `elif`（2026-09-15 當場踩到）：分類別那張大盤統計表
            #   **有可加總的欄** ⇒ 走 `tot` 那一支 ⇒ ⛔ 逐列**永遠印不出來**，
            #   ⚠ 而 F2 要的正是它的「認購(售)權證」**那一列**，不是合計。
            # ⇒ ⭐ 兩個都印：合計說總量，逐列說**分佈在誰身上**。
            if rows and len(rows) <= 20:
                # ⭐ 標籤要有：⛔ 一堆裸 list 在捲動的輸出裡看不出是什麼，
                #   ⚠ 而斷言也只能比帶標籤的整串（第七點）。
                say(f"          ── ⭐ 逐列（{len(rows)} 列，⛔ 不是只有合計）──")
                for r in rows:
                    say(f"             {r}")
            elif rows:
                say(f"          首列：{rows[0]}　⚠ 另 {len(rows) - 1} 列未印（表太大）")
            # ⛔⛔ 2026-09-15 第一版的病根：FMTQIK 回的是**整個月**（11 列）
            #   ⇒ 只印「逐欄合計」＝ 整月合計，⚠ 而上面①是**單日**
            #   ⇒ 兩個數字並排，而它們**不是同一個量**。
            #   ⭐ 這就是第三點 5 那條（要判一件事只准動一個變數）套在錨點上：
            #     ⛔ 一個月對一天，差異可以被歸給任何一件事。
            #   ⇒ 把 `日期` ＝ 本次測試日的**那一列**單獨挑出來印。
            one = _row_for_day(fl, rows, day)
            if one:
                say(f"          ⭐⭐ 其中 {day} **那一列**（⇒ 這才跟①可比）："
                    + "｜".join(f"{k} {v:,.0f}" for k, v in one.items()))
            elif rows and any("日期" in str(x) for x in fl):
                say(f"          ⚠ 這張表裡**找不到** {day} 那一列"
                    f"（{len(rows)} 列）⇒ ⛔ 不可以拿整月合計去跟①比")


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 零股：**我方日檔的量欄不含它，而官方年／月表含**（2026-09-16）
#
# 起因：回測線 0841 §三報「上市年量 651 列我方略少」。逐格量完是零股——
# ⭐ 最乾淨的一格是 1470／民107：官方 − 我方 ＝ **1 股、1 筆、17 元**
#   （單價 17.00 落在該年價格區間內）⇒ 整股交易做不出 1 股。
#
# ⇒ 這一節要回答的是**三件我還不知道的事**（⛔ 在它們有答案之前不寫抓取程式）：
#   ① `twt53u`／`twtc7u` 吃不吃 `date` ⇒ **回應要自己講出它是哪一天**
#      ⛔ 路徑在 `historical/` 底下**不是證據**（第二點⑤：端點的名字不是證據）
#   ② 歷史回得到多久：2015 那一發拿不拿得到列
#   ③ 盤中零股（`twtc7u`）實際上從哪一年開始有列
#      ⚠ 制度是 2020-10-26 上路 ⇒ ⛔ 2015 那一發**應該**是空的，
#        ⭐ 而「應該」要用資料證實：若它 2015 也回列，那就代表它**不吃日期**。
#
# ⭐ 判準一律是 `describe_response()` 印出來的 `params`／`date`／`total`，
#   ⛔ 不是「有沒有回列」（第二點：靜靜回今天／靜靜回最新一期都長成 stat:OK）。
# ══════════════════════════════════════════════════════════════════
ODD_DAYS = ["20150105", "20190102", "20201026", "20240102", YMD]


def odd_lot():
    """零股端點的日期參數與歷史涵蓋。⛔ 只問，不抓、不寫任何資料檔。"""
    say("── ⭐⭐ 零股（我方日檔不含它，而官方年／月表含）──")
    say("  ⛔ 要回答的是：吃不吃 `date`／歷史回得到多久／盤中零股從哪一年開始。")
    say("  ⚠ 判準是**回應自己講出它是哪一天**，⛔ 不是「有沒有回列」。")
    for rep, name in (("TWT53U", "上市**盤後**零股"),
                      ("TWTC7U", "上市**盤中**零股（制度 2020-10-26 上路）")):
        for d in ODD_DAYS:
            show(f"{name}　{rep}　date={d}",
                 f"{TW}/afterTrading/{rep}?date={d}&response=json", {"date": d})
    say("  ⛔ **上櫃那一半不在這裡問**：我不知道它的 action 叫什麼，"
        "⚠ 而從網址猜正是三點5 已經付過代價的那一種"
        "（`otcsbl`／`monthlyStock` 兩次都是猜錯的）")
    say("     ⇒ 改走 `tpex_probe` [15]：**讀那三頁自己寫的 `action:`**，"
        "⛔ 讀到了才打。")
    say("  ⇒ ⭐ 讀法：`params`／`date` 回顯**不是我送的那一天** ⇒ 那個參數是假的；")
    say("     回 0 列**而且**日期回顯正確 ⇒ 那一天真的沒有（盤中零股在 2020 前就該是這樣）。")
    say("     ⛔ 兩者在「筆數 0」這個畫面上長得一模一樣。")
    say("")


# ══════════════════════════════════════════════════════════════════
# ⭐⭐⭐ 民國 109 年的年成交金額：**定位到一個月了**（2026-09-16）
#
# 回測線 0841 §三② 報「109 年金額 606 列，我方全部多 1~1,040 元」。
# ⇒ 我先量形狀：Δ股數與Δ筆數 **157／157 都是 0** ⇒ 同樣的成交、不同的金額。
# ⇒ 再拿**剛抓回來的上市月表**（feeds run 163，`official_monthly_amount.csv`
#   從 8,420 列長到 12,731 列）逐月拆 ⇒ ⭐⭐ **全部落在同一個月**：
#
#     1101 年差 −317 元 ⇒ 月表只有 **10 月**有差，−317
#     1229 年差 −105 元 ⇒ 只有 **10 月**，−105
#     1104／1201／1215／1219／1234／1303 ⇒ ⭐ **8／8 都只有 10 月**
#     （而 1256/109 年差 0 ⇒ 月表 12 個月全對 ⇒ 反向也對得上）
#
# ⚠ 民國 109 年 10 月 ＝ **2020 年 10 月**，而**盤中零股交易 2020-10-26 上路**。
# ⛔ 而方向不合：官方年／月表**含**零股（已證實）⇒ 多了零股該是官方**多**，
#   ⚠ 實際是官方**少** ⇒ ⭐ 那個巧合**不是答案**，只是同一個月。
#
# ⇒ ⭐ 下一步只要**一發**就定得出是哪一天：
#     STOCK_DAY?date=20201001&stockNo=1101  ⇒ 回整個 10 月的**逐日**列
#   ⛔ 而我方日檔的逐日 amount 肉眼看不出異常（10 月 19 個交易日，
#     每天的「金額÷股數」都落在該日高低價之間）⇒ 只能逐日對。
#
# ⚠ 這一支**只問、不寫任何資料檔**（跟 odd_lot() 同一條規矩）。
# ══════════════════════════════════════════════════════════════════
OCT2020 = ("1101", "1229", "1303")          # ⭐ 三檔：年差 −317／−105／−20


def oct_2020():
    say("── ⭐⭐⭐ 民國 109 年金額差：已定位到 **109/10**，這一節要定到**哪一天**──")
    say("  拿月表逐月拆的結果：8／8 受影響的檔，**全年的差額 100% 在 10 月**。")
    say("  ⛔ 而 `盤中零股 2020-10-26 上路` 這個巧合**不是答案**：方向不合"
        "（官方含零股 ⇒ 該是官方多，實際是官方少）。")
    for sid in OCT2020:
        show(f"{sid} 的 2020 年 10 月**逐日**　STOCK_DAY",
             f"{TW}/afterTrading/STOCK_DAY?date=20201001&stockNo={sid}&response=json",
             {"date": "20201001", "stockNo": sid})
        # ⛔⛔ 我方那一邊**要現算**，⚠ 不可以寫死。
        #   2026-09-16 我第一版把合計憑印象打進去，1101 打成 7,665,468,935
        #   （真值 7,665,469,135）、1229 打成 1,181,381,908（真值 1,225,384,008）
        #   ⇒ ⭐ 一個寫死的對照值，錯了**沒有任何地方會說**，
        #     而讀的人會拿它去比官方的數字然後查錯方向。
        for ln in _our_oct_2020(sid):
            say(f"   {ln}")
        # ⭐⭐ 2026-09-16 離線量到的新事實：**差額不在日檔那一層**
        #
        #     1101／109-10  股數 Δ=0（逐位相同）  金額 官方月表**少 317 元**
        #     1229／109-10  股數 Δ=0            金額 官方月表**少 105 元**
        #
        # ⇒ ⛔ 所以要比的是**三方**，⚠ 不是兩方：
        #     ① 我方日檔合計
        #     ② 官方 `STOCK_DAY` 逐日合計   ← 這一節現在才算
        #     ③ 官方月表 `FMSRFK`
        #   ⭐ ①==② 而 ②≠③ ⇒ 是**官方自己兩條路不一致**，⛔ 不是我方的問題
        #   ⭐ ①≠② ⇒ 那才是我方日檔跟官方逐日對不上
        #   ⇒ ⛔ 只比 ①③ 的話這兩種**分不開**（而它們的處置完全相反）。
        for ln in _official_vs_month(sid):
            say(f"   {ln}")
    say("  ⇒ ⭐ 讀法：看上面那三方。⛔ 而 `盤中零股 10-26 上路` 只是同一個月，")
    say("     ⚠ 方向不合（官方含零股 ⇒ 該是官方多，實際是官方少）。")
    say("")


def _official_vs_month(sid):
    """官方 `STOCK_DAY` 逐日合計 vs 官方月表 `FMSRFK`（民109/10）→ 幾行字。

    ⛔ 這一節**只問官方自己**：兩條官方路徑對不對得上。
    ⚠ 月表讀的是 `data/meta/official_monthly_amount.csv`（我方抓回來存的那份）
    ⇒ 讀不到就**大聲說沒跑**，⛔ 不是靜靜跳過。
    """
    raw, err = B.get(f"{TW}/afterTrading/STOCK_DAY"
                     f"?date=20201001&stockNo={sid}&response=json",
                     retries=2, timeout=45)
    if err or not raw:
        return [f"⚠ **這一層沒跑**：官方逐日取不回來（{B.why(err)}）"]
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        return [f"⚠ **這一層沒跑**：官方逐日不是 JSON（{str(ex)[:60]}）"]
    ov = oa = 0
    for row in (d.get("data") or []):
        if len(row) < 3:
            continue
        v, a = B._num(str(row[1])), B._num(str(row[2]))
        if v and a:
            ov += int(float(v)); oa += int(float(a))
    out = [f"⭐ 官方 **STOCK_DAY 逐日合計**：股數 {ov:,}｜金額 **{oa:,}**"]
    mp = os.path.join(_ROOT, "meta", "official_monthly_amount.csv")
    if not os.path.exists(mp):
        out.append("⚠ **這一層沒跑**：讀不到 official_monthly_amount.csv ⇒ 月表那一邊沒得比")
        return out
    hit = None
    with io.open(mp, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["stock_id"] == sid and r["roc_year"] == "109" and r["month"] in ("10", "10 "):
                hit = r
                break
    if not hit:
        out.append("⚠ **這一層沒跑**：月表裡沒有這一格（109/10）")
        return out
    mv, ma = int(hit["volume"]), int(hit["amount"])
    out.append(f"⭐ 官方 **月表 FMSRFK**：股數 {mv:,}｜金額 **{ma:,}**")
    out.append(f"⭐⭐ 官方兩條路的差（月表 − 逐日）：股數 {mv - ov:+,}｜金額 **{ma - oa:+,}**"
               "　⇒ ⭐ 不是 0 的話，那是**官方自己**兩條路不一致，⛔ 不是我方的問題")
    return out


def _our_oct_2020(sid):
    """我方 `data/stocks/<sid>.csv` 的 2020-10 逐日與合計 → 幾行字。

    ⭐ **現算**（⛔ 不是寫死的對照值）：這一支跑在 Actions 上，
    而 `data/stocks/` 就在 checkout 裡 ⇒ 算得到就不要抄。
    """
    path = os.path.join(_ROOT, "stocks", f"{sid}.csv")
    if not os.path.exists(path):
        return [f"⚠ **這一層沒跑**：讀不到 {os.path.relpath(path, _ROOT)}"
                "（⇒ 官方那一邊仍然印出來了，只是沒得比）"]
    v = a = n = 0
    days = []
    try:
        with io.open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if not r["date"].startswith("2020-10") or not r.get("close"):
                    continue
                dv = int(r["volume"] or 0)
                da = int(r["amount"] or 0)
                v += dv
                a += da
                n += 1
                days.append(f"{r['date']} {dv:,}股 {da:,}元")
    except OSError as ex:                                        # noqa: BLE001
        return [f"⚠ **這一層沒跑**：讀 {sid} 失敗（{ex}）"]
    return ([f"⭐ 我方 2020-10（{n} 個交易日）合計：股數 {v:,}｜金額 **{a:,}**"]
            + [f"     {d}" for d in days])


# ══════════════════════════════════════════════════════════════════
# ⭐⭐⭐ 年均價那 391 列 ±0.01：**整個「進位規則」那一族被排除掉了**
#
# 回測線 0841 §三 4. 報「年收盤平均 ±0.01 殘差 391 列，全部上市」。
# 我方抽樣（扣掉轉板年，上市 2,610 個 (檔,年)）：
#   四捨五入 95.33%｜（四捨 或 捨去）98.08% ⇒ 剩 **107 列**兩種都對不上…
#   ⚠ 更正：剩 **50 列**（官方比我方大 +0.01）⇒ 而另外 57 列是四捨五入對得上、
#     **雙重進位會弄壞**的那一批。
#
# ⇒ ⭐⭐ 把兩批的「精確平均換算成分之後的小數」並排：
#
#     雙重進位**修好**的 50 個：min 0.4504｜p50 0.4715｜max 0.4980
#     雙重進位**弄壞**的 57 個：min 0.4504｜p50 0.4737｜max 0.4959
#     ⇒ ⭐⭐ **兩批落在同一個帶 [0.45,0.50)，而且幾乎同分佈**
#
# ⇒ ⛔⛔ **任何「平均值的函數」都做不到這件事**：小數同樣是 0.472 的兩格，
#   官方一個進位、一個不進位 ⇒ **官方的 `avg_close` 不是我方那組收盤價的函數**。
#   ⇒ ⭐ 整個「進位規則」那一族（四捨／捨去／雙重進位／先月後年）**被排除**。
#
# ⇒ 那剩下什麼？**官方平均的那組數字跟我方不一樣。** 而量級對得起來：
#
#     要把小數從 f 推過 0.5，Σ收盤 需要多 (0.5−f)×n/100 元
#     f=0.4980 ⇒ 0.005 元（**半天** 差 0.01）
#     f=0.4715 ⇒ 0.070 元（約 7 天各差 0.01）
#     f=0.4504 ⇒ 0.122 元（約 12 天各差 0.01）
#   ⇒ ⭐ 需要的「差 0.01 的天數」是 **1~13 天**，⚠ 而那正好是這個帶的寬度。
#   ⛔ 而「官方多／少一整天」做不出 ±0.01（那會差一整格以上）⇒ 也被排除。
#
# ⇒ ⭐ 所以這一節問**一件事**：拿 `STOCK_DAY` 把官方的**逐日收盤**抓回來，
#   跟我方 `data/stocks/<sid>.csv` 逐日比 ⇒ **到底有沒有幾天差 0.01**。
#   ⚠ 一檔一年 12 發。⛔ 只問，不寫任何資料檔。
# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
# ⭐⭐⭐ 2026-09-16 第一發回來了，而它**把上面那段推論翻了一半**
#
# probe run 132 實測 1471／民108：
#
#     我方 242 天｜官方 242 天｜只有我方有 0｜只有官方有 0
#     ⭐⭐ **收盤價不同的日子：0** ⇒ 逐日逐位相同
#
# ⇒ ⛔ 所以上面那句「官方平均的那組數字跟我方不一樣」在**這一格**是錯的
#   ——兩組數字**一模一樣**，而年均價還是差 0.01（我方 4.2949、官方 4.30）。
#
# ## ⇒ 而離線再量一次，形狀出來了：**它是逐【檔】的，不是逐格的**
#
# 母體 2,698 個 (檔,年)（可比、⭐ 排除轉板年＝`market` 欄變過的那一年、n≥200）：
#
#     ⭐ 收盤簡單平均   2,039／2,698 ＝ **75.6%**   ← 公式本身是對的
#       (高+低+收)/3      327／2,698 ＝ 12.1%
#       (開+高+低+收)/4   299／2,698 ＝ 11.1%
#       (高+低)/2         233／2,698 ＝  8.6%
#     ⇒ ⛔ 「年均價其實是別的公式」**被排除**（差距一個量級）
#
# ⇒ 再把「判別得出來」的那一批（小數第三位 ≥5 ⇒ 捨去與四捨五入會分岔）拆開：
#
#     官方 ＝ 無條件捨去  827／1,811 ＝ 45.7%
#     官方 ＝ 四捨五入    984／1,811 ＝ 54.3%
#     ⛔ 兩個都不是           0
#
# ⇒ ⭐⭐ 而**它按檔分群**：只出現捨去的 143 檔、只出現四捨五入的 147 檔，
#   ⛔ 同一檔兩種都有的只有 37 檔（≈11%）。
#   ⚠ 一個**進位規則**不會逐檔不同 ⇒ ⛔ 那就不是進位規則。
#
#     3141（27~130 元）民106/108/109/110/112/113 **六年全部**是捨去
#     2305（6~8 元）  民104/105/107/108/109     **五年全部**是四捨五入
#     ⇒ ⭐ 兩群的差別看起來是**價位**（⇒ 檔位：<10 元 0.01、10~50 元 0.05…）
#
# ⇒ 而算術對得起來：3141／民106 要讓官方寫 36.32，官方的 Σ 必須比我方**低 0.10**
#   ⇒ 246 天裡約 **2 天各差 0.05** ——⭐ 而 0.05 正是 3141 那個價位的檔位。
#
# ⇒ ⛔⛔ **成因我還不知道**（候選：除權息參考價那一天、最後成交價 vs 收盤價），
#   ⇒ ⭐ 所以這一節改成**三個錨點各問一次**，一群一個：
#
#     ("3141", 106)  捨去那一群（檔位 0.05）  ← 若逐日有差，差的應該是 0.05 的倍數
#     ("2305", 109)  四捨五入那一群（檔位 0.01）
#     ("1471", 108)  ⭐ 已知逐日逐位相同的那一格（**對照組**）
#
# ⚠ 對照組不可以省：⛔ 沒有它的話，「另外兩個也沒差」與「這支探針壞了」
#   在輸出上長得一模一樣（第七點第四個）。
# ══════════════════════════════════════════════════════════════════
#: ⭐ 三個錨點，⛔ 不是一個——一群一個 ＋ 一個已知相同的對照組。
AVG_RESID = (("3141", 106), ("2305", 109), ("1471", 108))


def avg_residual():
    for _sid, _roc in AVG_RESID:
        _avg_residual_one(_sid, _roc)


def _avg_residual_one(sid, roc):
    ad = roc + 1911
    say(f"── ⭐⭐⭐ 年均價 ±0.01：{sid}／民{roc} 逐日比對 ──")
    say("  ⛔ 「年均價是別的公式」已排除（收盤簡單平均 75.6% vs 次高 12.1%）")
    say("  ⛔ 「進位規則」也排除（它**逐檔**分群：143 檔只捨去、147 檔只四捨五入）")
    say("  ⇒ 這一節只問：**官方的逐日收盤跟我方有沒有幾天不一樣、差多少**。")
    ours = _our_closes(sid, ad)
    say(f"  我方 {ad} 年有收盤的天數：{len(ours)}")
    got = {}
    for mo in range(1, 13):
        raw, err = B.get(f"{TW}/afterTrading/STOCK_DAY"
                         f"?date={ad}{mo:02d}01&stockNo={sid}&response=json",
                         retries=2, timeout=45)
        if err or not raw:
            say(f"   {ad}-{mo:02d} ✗ 抓不到：{str(err)[:80]}")
            continue
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except ValueError as ex:                                 # noqa: BLE001
            say(f"   {ad}-{mo:02d} ✗ 不是 JSON：{str(ex)[:60]}")
            continue
        title = str(d.get("title") or "")
        # ⛔ 第二點：這一批要自己講出它是哪一檔、哪一期
        if sid not in title or f"{roc}年{mo:02d}月" not in title.replace(" ", ""):
            say(f"   {ad}-{mo:02d} ⛔ title 沒有回音我送的代號與月份：{title!r}")
            continue
        for row in (d.get("data") or []):
            if len(row) < 7:
                continue
            iso = _roc_date(str(row[0]))
            # ⛔⛔ 這裡本來寫 `_n(...)`，⚠ 而 `_n` **這個檔裡根本沒有**
            #   ⇒ probe run 131 在 Actions 上 `NameError` 炸掉整支（rc=1）。
            #   ⭐ 而離線自測**全綠**：假回應讓上面那道「title 要回音代號與月份」
            #     提前 `continue`，⇒ 這一行**一次都沒被走過**（第七點第三個）。
            #   ⇒ 用**唯一那一份**數字清洗（四點五：`backfill._num` ＝ `fetch._num`）。
            c = B._num(str(row[6]))
            if iso and c not in ("", "--", "X0.00"):
                got[iso] = c
    say(f"  官方回到的天數：{len(got)}")
    only_ours = sorted(set(ours) - set(got))
    only_off = sorted(set(got) - set(ours))
    # ⛔⛔ 這裡**不可以比字串**：我方 CSV 寫 `4.3`、官方回 `4.30`
    #   ⇒ 比字串會把**每一天**都判成「收盤不同」，⚠ 而那個結論剛好是
    #     這一節在找的東西 ⇒ ⛔ 它會**確認一個假的發現**，而畫面上完全正常。
    #   ⇒ ⭐ 比**數值**。轉不成數字的兩邊都當「比不了」，⛔ 不當成不同。
    diff = sorted(d for d in set(ours) & set(got)
                  if _same_price(ours[d], got[d]) is False)
    n_incomp = sum(1 for d in set(ours) & set(got)
                   if _same_price(ours[d], got[d]) is None)
    if n_incomp:
        say(f"  ⚠ **這一層沒跑**：{n_incomp} 天兩邊有一邊不是數字 ⇒ 比不了"
            "（⛔ 不算「相同」也不算「不同」）")
    say(f"  ⭐ 只有我方有的日子：{len(only_ours)} {only_ours[:5]}")
    say(f"  ⭐ 只有官方有的日子：{len(only_off)} {only_off[:5]}"
        "　⇒ ⚠ 若 >0，那就是「官方多算了幾天」（⛔ 而那做不出 ±0.01）")
    say(f"  ⭐⭐ **收盤價不同的日子：{len(diff)}**"
        + ("（⇒ ⛔ 一天都沒有 ⇒ 連這一條也被排除，那就寫不知道）" if not diff else ""))
    for d in diff[:20]:
        say(f"      {d}  我方 {ours[d]}　官方 {got[d]}"
            f"　差 {float(got[d]) - float(ours[d]):+.2f}")
    # ⭐ 差額的**形狀**要自己講出來：檔位假說成立的話，差會是檔位的倍數。
    #   ⛔ 只印「有幾天不同」講不出是哪一種（第二點）。
    if diff:
        ds = sorted({round(float(got[d]) - float(ours[d]), 4) for d in diff})
        say(f"  ⭐ 差額的相異值（{len(ds)} 種）：{ds[:12]}")
        say(f"  ⭐ 差額合計：{sum(float(got[d]) - float(ours[d]) for d in diff):+.4f} 元"
            f"　（⇒ 年均價會被推動 {sum(float(got[d]) - float(ours[d]) for d in diff) / max(len(ours), 1):+.5f}）")
    say("")
    say("")


def _roc_date(s):
    """`109/10/05` → `2020-10-05`。⛔ 認不出來就回 None（不猜）。"""
    p = s.strip().split("/")
    if len(p) != 3 or not p[0].isdigit():
        return None
    return f"{int(p[0]) + 1911:04d}-{p[1].zfill(2)}-{p[2].zfill(2)}"


def _same_price(a, b):
    """兩個價格字串相不相同 → `True`／`False`／`None`（比不了）。

    ⛔ **三種回答，不是兩種**（五點三那條的形狀）：`None` 是「有一邊不是數字」，
    ⚠ 而把它壓進 `False` 就等於報一筆假的「收盤不同」。
    """
    fa, fb = B._num(str(a)), B._num(str(b))
    if fa == "" or fb == "":
        return None
    return float(fa) == float(fb)


def _our_closes(sid, ad_year):
    """我方 `data/stocks/<sid>.csv` 那一年的 `{日期: 收盤}`。⭐ 現算，⛔ 不寫死。"""
    path = os.path.join(_ROOT, "stocks", f"{sid}.csv")
    out = {}
    if not os.path.exists(path):
        return out
    try:
        with io.open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["date"].startswith(str(ad_year)) and r.get("close"):
                    out[r["date"]] = r["close"]
    except OSError:
        pass
    return out


def main():
    say("── 官方回應裡我方丟掉的鍵 ──")
    say("⛔ `_tables()` 只取 title/fields/data。其餘（stat／date／notes／hints／"
        "params／total…）**全部丟掉，而且沒有紀錄**。")
    say("⭐ 這一支不猜它們有沒有用——把原文印出來，讓資料自己回答。")
    say(f"⚠ 測試日固定 {DAY}（交易日）。")
    say("")
    for label, url, want in TARGETS:
        show(label, url, want)
    say("── 要從這份輸出回答的三件事 ──")
    say("  ① `total` 對得上我方解析出的列數嗎 ⇒ 若對得上，這是**免費的**每次請求完整性斷言")
    say("  ② `params` 有沒有把我送的參數回顯 ⇒ 那是「參數有沒有生效」的直接檢查")
    say("  ③ `notes` 裡有沒有**符號說明** ⇒ `adj_gap.py` 五處寫的"
        "「官方 X0.00 ＝ 無前一日收盤價可資比較」目前**沒有留下出處**；")
    say("     有的話它就是權威出處，⛔ 沒有的話那句話要降級成推論"
        "（而它是「轉上市首日不算缺陷」那個歸因的地基）。")
    odd_lot()                 # ⭐ 2026-09-16 加，見上面那一段的理由
    oct_2020()                # ⭐⭐ 同上：109 年金額差已定位到 109/10
    avg_residual()            # ⭐⭐⭐ 年均價 ±0.01：進位那一族已排除
    f2_kou_jing(YMD)          # ⭐ 走既有的那一份，⛔ 不再算一次
    return _write(0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                        # noqa: BLE001
        say("")
        say("✗ 這一趟炸了，traceback 原文：")
        say(traceback.format_exc())
        _write(1)
        raise
