#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reduce_ratio_probe.py — 上市減資的**換股率**到底在哪張表。**只測、不寫資料。**

## ⛔ 為什麼要有這一支：我寫過一句沒掃描範圍的否定句

2026-09-13 我寫：「上市那邊**沒有**官方公告的換股比率／權值欄位，
所以那 303 筆減資只有 `shares` 一個第二來源。」

⚠ 而使用者指出：TWSE 的**減資預告表**（`TWTAVU`）就有，欄名叫 **`減資換股率`**。
⇒ ⛔ repo 裡 grep `TWTAVU` **0 次** ⇒ 我根本沒掃到那一頁就下了結論。
⭐ 這正是 CLAUDE.md 三點①【掃描範圍】：
**「查過了、沒有」要寫清楚掃了哪些頁、用什麼詞查**——我兩樣都沒寫。

## ⭐⭐ 而同一次翻查還撿到第二件：我方把官方**已經給的**兩欄丟掉了

`parse_reduce` 的檔頭自己列著 `TWTAUU` 的官方 **11 欄**：

```
恢復買賣日期／股票代號／名稱／停止買賣前收盤價格／恢復買賣參考價／
⭐ 漲停價格／跌停價格 ⭐／開盤競價基準／除權參考價／減資原因／詳細資料
```

⚠ 而我方 `header` 只有 **7 欄**——`漲停價格`／`跌停價格` **被丟掉了**。
⛔ 而我 2026-09-13 花了一整輪**推論**交易所的漲跌停（`factor_limit_check.py`：
拿每一檔自己的歷史量「有沒有 ±10% 硬性上限」）⇒ **交易所自己就有給那兩個數**。

⇒ 本支要回答的兩件事：

```
① TWTAVU 有沒有 `減資換股率`？涵蓋期間多長？    ⇒ 補上市那 303 筆的第二來源
② TWTAUU 現在真的有 `漲停價格`／`跌停價格` 嗎？ ⇒ 把推論換成官方數字
```

## 判準（照 `parvalue_probe.py` 的四項，缺一不可）

1. `stat` 與標題　2. **完整欄位**　3. 列數　4. **日期欄的最小與最大值**

⭐ 而第一件事是 `describe_response()`（CLAUDE.md 第一點，⛔ 跳不過去）：
把 `notes`／`hints`／`params`／`total` 印出來再開始比對。

## ⚠ 參數回音

TWSE 踩過 `TWT49U` **不吃 `date` 卻把它原樣回傳**。
⇒ 本支**換三個不同區間各打一發**，比對標題與列數——一樣就是參數被無視。
"""
import json
import os
import sys
import traceback

import backfill as B
import ca_chain  # noqa: F401
# ⭐ 同一件事只准有一份實作（四點五）：⛔ 這裡原本自己包了一份 `B_why`
from feeds import _why as B_why                               # noqa: E402

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_reduce_ratio_probe.txt")

# ⚠ 路徑來自使用者 2026-09-13 提供的官方頁（announcement/reduction/twtavu.html），
#   ⛔ 而 rwd 的 JSON 路徑是**待驗的假設**，不是已知事實——所以下面三個區間對打。
TARGETS = [
    ("TWTAVU（減資預告表）", "https://www.twse.com.tw/rwd/zh/reducation/TWTAVU"),
    ("TWTAUU（恢復買賣參考價，⭐ 只為看漲跌停兩欄）",
     "https://www.twse.com.tw/rwd/zh/reducation/TWTAUU"),
    # ⭐⭐ 2026-09-13 加：F2 那 4 筆未判定（911608／2429／6225／7610）要的是
    #   **權值與息值分開**＋現增認購價／認購率。而我方 `parse_exright` 只取
    #   `權值+息值`（**一個合併欄**）⇒ 拆不開。
    # ⛔ 而官方 TWT49U **完整**有幾欄，我方沒有紀錄——`_keys_probe` 那次被擋回 HTML。
    #   ⇒ 先把它的完整欄位印出來（第一點），⛔ 不要再憑「我們取的那幾個」推論它只有那些。
    # ⛔⛔ 上一趟我把它猜成 `afterTrading/TWT49U` ⇒ **六發全部回一頁 HTML**。
    #   ⚠ 而「回 404 頁面」跟「參數不對」處理方式**相反**（NEW_ENDPOINT 第 −1 步③），
    #     ⛔ 我差一點把它讀成「這張表問不到」。
    #   ⭐ 而正確路徑**我方自己就有**：`FEEDS["exright"]["urls_range"]` 寫著
    #     `rwd/zh/exRight/TWT49U`。⇒ 猜路徑之前先 grep 我方在用哪一條。
    ("TWT49U（除權除息計算結果，⭐ 只為看完整欄位）",
     "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"),
    # ⭐ 這一條上一趟**打通了**（13 欄，含無償配股率／現金增資配股率／現金增資認購價／
    #   現金股利）——⛔ 而三個區間回同樣的 68 列 ⇒ 它是**預告表**，沒有歷史。
    ("TWT48U（除權除息預告表，✅ 已驗證路徑）",
     "https://www.twse.com.tw/rwd/zh/exRight/TWT48U"),
]
# ⭐ 有些表**一定**要再用單一 `date` 打一次才知道有沒有歷史
#   ——⛔ 區間有回列的時候，原本的自動退路不會觸發。
FORCE_DATE = {"TWT48U（除權除息預告表，✅ 已驗證路徑）"}
RANGES = [("20150101", "20151231"), ("20200101", "20201231"),
          ("20260101", "20260913")]
# ⭐⭐ 分割重取（`data-source-recon` §二④）：這一族的回應**沒有 `total`**
#   （頂層鍵只有 data/endDate/extraNotes/fields/formula/notes/stat/strDate/title）
#   ⇒ 「它就是這麼多列」與「它截斷在某個上限」**回應裡沒有任何欄位分得出來**。
#   ⇒ 唯一的驗法：把同一段切小、各取一次再加總，跟一次大區間比。
#   ⚠ 差 0 才可以說「沒有截斷」；⛔ 「看起來不是整數」不算證據。
SPLIT_YEAR = "2015"
SPLIT_PARTS = [("20150101", "20150331"), ("20150401", "20150630"),
               ("20150701", "20150930"), ("20151001", "20151231")]
WANT = ("減資換股率", "換股率", "漲停價格", "跌停價格", "權值", "息值",
        "股利", "認購", "增資")

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def one(base, a, b, param="range"):
    # ⚠ 同一站不同端點的參數**互不相同**（三點②）：TWTAUU 吃 startDate/endDate，
    #   ⛔ 而 TWT49U 實測是吃單一 `date` ⇒ 兩種都要試，不要假設。
    url = (f"{base}?startDate={a}&endDate={b}&response=json" if param == "range"
           else f"{base}?date={a}&response=json")
    say(f"\n  ── {a} ~ {b}")
    say(f"     {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        # ⛔ 錯誤訊息不可以砍尾巴（六點六）——可行動的部分永遠在後面
        say(f"     ✗ {B_why(err)}")
        return "LIMITED" if str(err).startswith("LIMITED") else None
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except Exception as ex:                                      # noqa: BLE001
        say(f"     ✗ 非 JSON：{type(ex).__name__}｜開頭 "
            f"{raw[:120].decode('utf-8', 'replace')}")
        return None
    # ⭐ CLAUDE.md 第一點：**第一件事**是把平常丟掉的那些鍵印出來
    for ln in B.describe_response(d, want={"startDate": a, "endDate": b}):
        say(f"     {ln}")
    stat = d.get("stat") if isinstance(d, dict) else None
    say(f"     [1] stat={stat!r}")
    tabs = B._tables(d)
    if not tabs:
        say("     [2] 沒有 tables——⚠ 沒有事件的區間本來就會這樣，⛔ 不等於端點壞掉")
        return {"stat": stat, "n": 0, "fields": [], "title": ""}
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    data = t.get("data") or []
    say(f"     [2] 欄位（{len(fields)}）：{fields}")
    hit = [w for w in WANT if any(w in f for f in fields)]
    say(f"     ⭐ 命中我要的欄名：{hit if hit else '⛔ 一個都沒有'}")
    say(f"     [3] 列數：{len(data)}")
    if data:
        say(f"         首列：{data[0]}")
    return {"stat": stat, "n": len(data), "fields": fields,
            "title": str(t.get("title") or ""), "hit": hit}


def main():
    say("=" * 70)
    say("上市減資的『換股率』在哪張表｜只測不寫")
    say("=" * 70)
    say("⛔ 起因：我 2026-09-13 寫過「上市沒有官方換股比率」，")
    say("   ⚠ 而 repo 裡 grep TWTAVU **0 次** ⇒ 我沒掃到那一頁就下了結論。")
    res = {}
    for name, base in TARGETS:
        say(f"\n{'=' * 70}\n【{name}】\n{base}")
        got = [one(base, a, b) for a, b in RANGES]
        if name in FORCE_DATE:
            say("\n  ⭐ 這張表**強制**再用單一 `date` 打一輪"
                "（⛔ 區間有回列 ⇒ 自動退路不會觸發，而那正是它騙人的方式）")
            got += [one(base, d, d, param="date")
                    for d in ("20150716", "20200619", "20260902")]
        # ⭐ 區間參數全掛的話，再用單一 `date` 試一次（⛔ 不要一種打不通就判死）
        if not any(isinstance(g, dict) and g.get("n") for g in got):
            say("\n  ⚠ 區間參數沒拿到列 ⇒ 改用單一 `date` 再試（⛔ 不是端點沒有）")
            got += [one(base, d, d, param="date")
                    for d in ("20150619", "20200619", "20260619")]
        res[name] = got
        ok = [g for g in got if isinstance(g, dict)]
        # ⚠ 參數回音：三個區間的標題／列數一樣 ⇒ 參數被無視，⛔ 不是有歷史
        if len(ok) >= 2:
            titles = {g["title"] for g in ok}
            ns = {g["n"] for g in ok}
            if len(titles) == 1 and len(ns) == 1 and list(ns)[0] > 0:
                say(f"\n  ⛔⛔ 三個區間的標題與列數**完全相同**（{list(ns)[0]} 列）"
                    f" ⇒ 參數很可能被無視，⛔ 不可以當成有歷史")
            else:
                say(f"\n  ✅ 不同區間回不同內容（列數 {sorted(ns)}）⇒ 參數有生效")
        allhit = sorted({h for g in ok for h in g.get("hit", [])})
        say(f"\n  ⭐⭐ 這張表命中的欄名：{allhit if allhit else '⛔ 一個都沒有'}")
    # ── ⭐⭐ 分割重取：一次大區間 vs 切成四段各取一次 ──────────
    say("\n" + "=" * 70)
    say("【分割重取】⛔ 沒有 `total` 就分不出「就是這麼多」與「截斷在上限」")
    say(f"  ⇒ {SPLIT_YEAR} 一次整年 vs 切成四季各一次，比總列數（⚠ 差 0 才算沒截斷）")
    base = "https://www.twse.com.tw/rwd/zh/exRight/TWT49U"
    whole = one(base, f"{SPLIT_YEAR}0101", f"{SPLIT_YEAR}1231")
    parts, psum, pok = [], 0, True
    for a, b in SPLIT_PARTS:
        g = one(base, a, b)
        if not isinstance(g, dict):
            pok = False
            continue
        parts.append(g["n"])
        psum += g["n"]
    if isinstance(whole, dict) and pok:
        wn = whole["n"]
        say(f"\n  ⭐ 整年一次 **{wn:,}** 列　vs　四季加總 **{psum:,}** 列"
            f"（各季 {parts}）")
        if wn == psum:
            say("  ✅ 差 0 ⇒ 這個區間長度**沒有**被截斷"
                f"（⚠ 而這句話的範圍就是「{SPLIT_YEAR} 這一年、這一支端點」）")
        else:
            say(f"  ⛔⛔ 差 {psum - wn:,} 列 ⇒ **一次大區間被截斷了**"
                "　⇒ 逐月／逐季抓才拿得到全部")
    else:
        say("  ⚠ 這一節沒跑完（有一發沒回來）⇒ ⛔ **不可以**當成「沒有截斷」")

    say("\n" + "=" * 70)
    say("⇒ 判讀：TWTAVU 若有 `減資換股率` ⇒ 上市那 303 筆就有了與價格**無關**的第二來源")
    say("   （等同上櫃 `otc_reduce_history.csv` 的 `shares_per_1000`）")
    say("⇒ 而 TWTAUU 若真的有 `漲停價格／跌停價格` ⇒ `factor_limit_check` 可以")
    say("   從『拿歷史推論有沒有 ±10% 上限』換成**直接比官方給的漲跌停**")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    say(f"\n[probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                            # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
