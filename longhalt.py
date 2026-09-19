#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""longhalt.py — 長期停止買賣（G2）：**每天累積一次**。

市場情報分析線 2026-09-17 0020 裁：⭐【接成每日累積】。
理由是**這三條端點只有當日** ⇒ ⛔ 每天不抓就是**永久損失**
（`_suspend_probe.txt` 第六輪：三條的 `Date`／`出表日期` 相異值都只有 **1 種**
⇒ 它們是**快照**，沒有歷史；第二點⑤：陣列型只能靠相異值分佈問這件事）。

## ⛔ 三個限定（0020 裁定裡寫死的，⛔ 一條都不可以省）

### ① 逐列帶**抓取日**

每一列都有 `first_asof`／`last_asof`／`n_obs`。⛔ 沒有這一欄的話，
「這一筆是什麼時候看到的」事後問不出來——⚠ 而這一族**只有**我方的觀測紀錄，
沒有官方歷史可以回頭核對。

### ② ⭐⭐「現行有效案件」**不是事件流** ⇒ 去重鍵要分兩種

⛔ 這三條回的是「**現在還有效的案件**」，⚠ 而那跟「今天發生了什麼」是兩件事：
同一筆案件會**每天回來一次**，而它消失的那天**沒有任何欄位會說它結束了**。

⇒ ⭐ 而兩種來源的形狀**不一樣**，所以去重鍵也不一樣：

```
event  `t187ap26_L`（上市）／`mopsfin_t187ap26_O`（上櫃）
       ⭐ 有「**停止買賣開始日**」⇒ 它講得出自己是哪一筆
       ⇒ 鍵 ＝ (來源, 代號, **開始日**)

state  `tpex_cmode`（上櫃）
       ⛔ **沒有任何日期欄**（只有出表日期）⇒ 它講不出自己是哪一筆
       ⇒ 鍵 ＝ (來源, 代號, **那一組旗標**)
       ⭐ 旗標變了就是**新的一段**（⚠ 而「變了」跟「換了一筆案件」我方分不出來
         ⇒ 那就寫不知道，⛔ 不要把它記成事件）
```

### ③ ⛔ 保留期**未驗** ⇒ 一律寫「至少 N 天，上限未知」

⚠ 我方**只知道自己看了幾天**。⇒ `retention_line()` 算出來的那一句是：

    觀測 N 天（YYYY-MM-DD ~ YYYY-MM-DD）｜單筆最長連續出現 M 天
    ⇒ 官方**至少**保留 M 天，⛔ **上限未知**（M ≤ N，因為我方只看了 N 天）

⛔ 不可以因為「跑了三個月都還在」就宣稱歷史補得回來。

## ⛔ 涵蓋範圍（0020 §G2 已經標過，這裡再寫一次）

`t187ap26_L/O` 只收「**經營權異動且營業範圍重大變更**」那一類，
⛔ **不是全部的長期停止買賣**。而 `tpex_cmode` 收的是上櫃的**交易方式**旗標
（停止交易／變更交易／分盤／管理股票）⇒ ⭐ 兩者**不是同一個母體**，合著數會錯。

## ⚠ 而 `t187ap26_L` 有一個會騙人的形狀（實測）

2026-09-17 那一發回的是**一列，而每一欄都是空的**（`出表日期` 有值）
⇒ ⛔ 那是「目前沒有案件」的佔位列，⚠ 而它跟「端點壞掉」在列數上一模一樣
（`suspend.py` ② 同一族）。⇒ `_drop_blank()` 把它丟掉，⛔ 而**不是**當成失敗。
"""
import argparse
import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

# ⭐ 只有一份 HTTP 實作（四點五）：交易所那條路一律走 `backfill.get`。
#   ⛔ 不要在這裡再寫第十一份 `get()`。
from backfill import get as _get, why as _why
import runlog

TPE = timezone(timedelta(hours=8))
_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_HERE, "data", "meta", "longhalt.csv")

HEADER = ["src", "market", "stock_id", "name", "shape", "start_date",
          "flags", "first_asof", "last_asof", "n_obs"]

# ⭐ 欄名**逐字照 `_suspend_probe.txt` 第六輪抄回來的**，⛔ 一個都不是猜的。
#   ⚠ 兩家的鍵名不同語言（上市中文、上櫃英文）——⛔ 不可以共用一份對照。
SOURCES = [
    {"src": "twse-t187ap26_L", "market": "twse", "shape": "event",
     "url": "https://openapi.twse.com.tw/v1/opendata/t187ap26_L",
     "code": "公司代號", "name": "公司名稱", "start": "停止買賣開始日",
     "asof": "出表日期", "flags": ()},
    {"src": "tpex-t187ap26_O", "market": "tpex", "shape": "event",
     "url": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap26_O",
     "code": "SecuritiesCompanyCode", "name": "CompanyName",
     "start": "停止買賣開始日", "asof": "Date", "flags": ()},
    {"src": "tpex-cmode", "market": "tpex", "shape": "state",
     "url": "https://www.tpex.org.tw/openapi/v1/tpex_cmode",
     "code": "SecuritiesCompanyCode", "name": "CompanyName",
     "start": None, "asof": "Date",
     # ⭐ 六個旗標**全部收**，⛔ 不是只收 `SuspensionOfTrading`：
     #   「只取我現在要的那幾個鍵」正是 CLAUDE.md 第一點那個代價
     #   （`_tables()` 丟掉 notes／params，而每一個都對應一件手工做過的事）。
     "flags": ("SuspensionOfTrading", "AlteredTrading", "PeriodicTrading",
               "MatchingFrequency", "ManagedStock", "FinancialAnnouncements")},
]


def today_tpe():
    return datetime.now(TPE).strftime("%Y-%m-%d")


def roc_iso(v):
    """民國 `1150903` → `2026-09-03`；認不出來就**原樣回傳**（⛔ 不猜、不丟掉）。"""
    s = str(v or "").strip()
    if len(s) == 7 and s.isdigit():
        return f"{int(s[:3]) + 1911:04d}-{s[3:5]}-{s[5:7]}"
    return s


def _drop_blank(rows, code_key):
    """丟掉「目前沒有案件」的佔位列（⛔ 代號欄是空的那種）。

    ⚠ 它**不是失敗**：`t187ap26_L` 沒有案件時就是回一列全空的
    ⇒ ⛔ 用列數判斷「有沒有資料」會數到 1（`suspend.py` ② 同一族）。
    """
    return [r for r in rows if str(r.get(code_key) or "").strip()]


def parse(payload, spec):
    """一發回應 → `[{HEADER 的前七欄}]`；⛔ 解析不出來丟 ValueError。

    ⭐ 回來的東西要**自己講出它是哪一期**（第二點）⇒ 一併回 `asof_src`
    （官方那一列自己寫的出表日期），⛔ 而它跟我方的抓取日是**兩件事**。
    """
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError(f"⛔ {spec['src']} 的頂層不是陣列（是 {type(data).__name__}）")
    rows = _drop_blank(data, spec["code"])
    asof_src = ""
    for r in data:
        v = str(r.get(spec["asof"]) or "").strip()
        if v:
            asof_src = roc_iso(v)
            break
    out = []
    for r in rows:
        flags = "|".join(f"{k}={str(r.get(k) or '').strip()}"
                         for k in spec["flags"] if str(r.get(k) or "").strip())
        out.append({
            "src": spec["src"], "market": spec["market"],
            "stock_id": str(r.get(spec["code"]) or "").strip(),
            "name": str(r.get(spec["name"]) or "").strip(),
            "shape": spec["shape"],
            "start_date": roc_iso(r.get(spec["start"])) if spec["start"] else "",
            "flags": flags,
        })
    return out, asof_src


def key_of(row):
    """去重鍵。⭐ **兩種形狀用兩種鍵**（0020 限定②）。

    ⛔ 不可以只用 (來源, 代號)：`t187ap26` 同一檔可以有第二筆案件（不同開始日）
    ⇒ 那會把第二筆**吃掉**，而畫面上只是「那一列的 last_asof 又更新了一次」。
    """
    if row["shape"] == "event":
        return (row["src"], row["stock_id"], row["start_date"])
    return (row["src"], row["stock_id"], row["flags"])


def load(path=None):
    """→ `{鍵: 列}`。讀不到回 `{}`（⛔ 不是丟例外——第一次跑本來就沒有）。"""
    p = path or OUT
    if not os.path.exists(p):
        return {}
    with io.open(p, encoding="utf-8") as f:
        return {key_of(r): dict(r) for r in csv.DictReader(f)}


def merge(cur, seen, today):
    """本趟看到的併進既有的。→ `(合併後, 新增幾筆, 更新幾筆)`。

    ⭐ **追加式合併**（四點六）：這一趟只知道自己那一部分
    ⇒ ⛔ 沒看到的列**原封不動**留著（它可能只是今天沒回來）。

    ⚠ 而它必須是**冪等**的：`daily.yml` 一天跑兩趟
    ⇒ `n_obs` 數的是**不同的抓取日**，⛔ 不是「跑過幾次」。
    """
    add = upd = 0
    for row in seen:
        k = key_of(row)
        old = cur.get(k)
        if old is None:
            cur[k] = dict(row, first_asof=today, last_asof=today, n_obs="1")
            add += 1
            continue
        if old.get("last_asof") == today:
            continue                      # ⭐ 同一天再跑一次：不重複計數
        old["name"] = row["name"] or old.get("name", "")
        old["last_asof"] = today
        try:
            old["n_obs"] = str(int(old.get("n_obs") or 0) + 1)
        except ValueError:
            old["n_obs"] = "1"
        upd += 1
    return cur, add, upd


def save(cur, path=None):
    """寫檔並**重讀驗終點**（四點二）。→ 讀回來的列數。

    ⛔ 列數不可以少於寫之前那一份——這支絕不可以變成刪東西的那個人
    （`merge_ledger.py` 同一條）。
    """
    p = path or OUT
    before = len(load(p))
    if len(cur) < before:
        raise RuntimeError(
            f"⛔ 合併後 {len(cur)} 列 < 既有 {before} 列 ⇒ 這一趟**一個字都不寫**")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, extrasaction="ignore")
        w.writeheader()
        for k in sorted(cur, key=lambda x: (x[0], x[1], x[2])):
            w.writerow(cur[k])
    return len(load(p))


def retention_line(cur):
    """0020 限定③ 那一句。→ 一行字；沒有資料回一句**說它沒有資料**的話。

    ⛔ 它只可以說「**至少** M 天」：我方看了 N 天 ⇒ M ≤ N ⇒ 上限**未知**。
    ⚠ 而 `n_obs` 是「出現過幾個抓取日」，⛔ 不是「連續」——
    中間我方漏跑一天也會少一個 ⇒ ⭐ 所以這句話寫的是**觀測到的下界**。
    """
    if not cur:
        return "⚠ 還沒有任何觀測 ⇒ ⛔ 保留期**一個字都還不能說**"
    firsts = [r.get("first_asof", "") for r in cur.values() if r.get("first_asof")]
    lasts = [r.get("last_asof", "") for r in cur.values() if r.get("last_asof")]
    if not firsts or not lasts:
        return "⚠ 列裡沒有抓取日 ⇒ ⛔ 保留期問不出來"
    lo, hi = min(firsts), max(lasts)
    days = (datetime.strptime(hi, "%Y-%m-%d") - datetime.strptime(lo, "%Y-%m-%d")).days + 1
    m = max(int(r.get("n_obs") or 0) for r in cur.values())
    return (f"觀測 {days} 天（{lo} ~ {hi}）｜單筆最多出現過 {m} 個抓取日 "
            f"⇒ 官方**至少**保留 {m} 天，⛔ **上限未知**"
            f"（{m} ≤ {days}，因為我方只看了 {days} 天）")


def run(fetch=None, today=None, path=None):
    """→ `(rl, 本趟看到幾列, 新增, 更新)`。`fetch(url)` 可注入（自測用）。"""
    rl = runlog.Run("longhalt")
    fetch = fetch or (lambda u: _get(u))
    day = today or today_tpe()
    cur = load(path)
    seen, bad = [], []
    for spec in SOURCES:
        body, err = fetch(spec["url"])
        if err or not body:
            bad.append((spec["src"], _why(err or "空回應")))
            continue
        try:
            rows, asof_src = parse(body, spec)
        except (ValueError, json.JSONDecodeError) as ex:            # noqa: BLE001
            bad.append((spec["src"], f"{type(ex).__name__}: {ex}"))
            continue
        seen.extend(rows)
        rl.info(f"{spec['src']}（{spec['shape']}）",
                f"{len(rows)} 列｜官方出表日 {asof_src or '（沒寫）'}")
    # ⛔ 三條**全部**失敗才算這一趟失敗：其中一條沒有案件是**正常**的
    #   （`t187ap26_L` 那一發就是全空）⇒ 判準是「有沒有一條答得出來」。
    rl.check("至少有一條來源答得出來", len(bad) < len(SOURCES),
             "；".join(f"{s}：{e}" for s, e in bad) or "三條都回了")
    if len(bad) == len(SOURCES):
        rl.note("⛔ 三條全部失敗 ⇒ 這一趟**一個字都不寫**"
                "（⚠ 而『全部失敗』在這一族有兩種：端點掛了／剛好都沒有案件"
                "——⭐ 而『沒有案件』會回 200 ⇒ 走不到這裡）")
        return rl, 0, 0, 0
    for s, e in bad:
        rl.note(f"⚠ {s} 這一趟沒回來：{e}（⛔ 它的既有列**原封不動**留著）")
    cur, add, upd = merge(cur, seen, day)
    n = save(cur, path)
    rl.check("寫出去的那一份讀得回來，而且列數 ≥ 本趟看到的",
             n >= len(seen), f"{n} 列（本趟看到 {len(seen)}）")
    rl.info("本趟", f"看到 {len(seen)} 列｜新增 {add}｜更新 {upd}｜累積 {n}")
    rl.info("⛔ 保留期（0020 限定③）", retention_line(cur))
    rl.info("⛔ 涵蓋範圍",
            "`t187ap26_L/O` 只收「經營權異動且營業範圍重大變更」那一類，"
            "⛔ 不是全部的長期停止買賣；`tpex_cmode` 收的是上櫃**交易方式**旗標"
            "⇒ ⭐ 兩者不是同一個母體，合著數會錯")
    return rl, len(seen), add, upd


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print", action="store_true",
                    help="只把累積檔的摘要印出來，⛔ 不連外、不寫檔")
    a = ap.parse_args()
    if a.print:
        cur = load()
        print(f"{OUT}｜{len(cur)} 列")
        print(retention_line(cur))
        return 0
    rl, _seen, _add, _upd = run()
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
