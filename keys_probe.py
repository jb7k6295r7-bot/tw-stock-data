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
