#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""資料庫現況總表 —— 一支腳本回答「現在有什麼、缺什麼」。

★ 為什麼要有這一支（2026-09-08）
────────────────────────────────
在這之前，要回答「資料庫還缺啥」得臨時拼十幾次查詢：讀 capital.csv 算空白、
讀 industry.csv 比對覆蓋、去猜哪個檔存不存在。**每次都重做一遍，而且每次拼法不同。**

這支把那些查詢固定下來。**它不抓網路、不改任何資料**，只讀 `data/` 然後印一頁。

⚠ 它報的是**資料庫現況**，不是「這一趟做了什麼」。
   `--fill`／`--resume`／狀態帳本都在這件事上騙過人：
   摘要說「0 失敗」而實際還有 5 個洞，因為它報的是那一趟碰到的東西。

用法
────
    python3 db_status.py              # 印出來
    python3 db_status.py --write      # 另外寫進 data/meta/_db_status.md

輸出的四段：
  ① 各層有多少、到哪一天
  ② 已知缺口（**寫死在 EXPECT 裡的預期值，對不上就標出來**）
  ③ 最近一輪各支腳本的檢查結果（讀 _last_run.md）
  ④ 完全沒有來源的東西（這一段是人維護的清單，不是算出來的）
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
DATA = "data"
META = os.path.join(DATA, "meta")
OUT = os.path.join(META, "_db_status.md")

# ★ 預期值。**對不上就會被標出來**，不是拿來當說明文字。
#   數字是 2026-09-08 的實測值；資料本來就會長，所以只檢查「不可以變少」。
EXPECT = {
    "stocks": 2100, "stocks_inst": 2600, "stocks_margin": 2400, "stocks_per": 2100,
    "adj": 2100, "daily": 2800, "esb": 300,
}

# ④ 這一段是人維護的。**算不出來的東西不要假裝算得出來。**
NO_SOURCE = [
    "⛔ **變更股票面額的還原因子**（2026-09-08 查明缺口）。`data/adj/` 實測"
    "只有除權息與減資兩種事件。10 元改 1 元會讓股數十倍、股價剩十分之一，"
    "未還原價跨過那天是單筆約 −90% 的假報酬——與 2026-09-06 之前的減資同一種病。"
    "★ **2026-09-08 已做全庫掃描**（`parvalue_scan.py` → "
    "`data/meta/_parvalue_scan.md`）：3,030 檔、552 萬個相鄰對，"
    "**實測 24 筆**（13 筆有名稱 `*` 出現的直接證據＋11 筆型態相符），"
    "與移交的「約 26 筆」量級對得上；判準與四個用錯的地方已寫進 "
    "`docs/READ_CONTRACT.md`。⚠ **但那只是讀取端的人工檢查，不是還原**——"
    "還缺官方事件來源（TWSE `change/TWTB8U`，`parvalue_probe.py` 09-08 那趟"
    "被限流沒答出四項判準）",
    "籌碼集中度／大戶持股的**歷史**（2026-09-08 起每週累積："
    "`data/tdcc/`，集保 17 級分級，四道驗算全過。⛔ 端點只回最新一週、"
    "不吃日期，**過去的補不回來**，跟上櫃停牌同一種性質）",
    "集保 17 級**各級距對應多少股**（來源只給代碼 1~17、沒給級距文字，"
    "官方對照表尚未查證。所以「400 張以上」這種定義還寫不出來）",
    "上櫃類股名稱 32、33 的中文名（代碼都在，名稱沒有。2026-09-08："
    "候選端點在探——`mopsfin_t187ap05_OA` 二十九大類股、"
    "`tpex_trading_volume_ratio` 類股成交價量比重）",
    # ⚠ 91（DR）已經不在這張清單裡：2026-09-08 查證它**不是類股**，
    #   是證券種類，見 READ_CONTRACT 產業別那一節。問錯問題不算缺資料。
    "「某一天到底有幾檔股票成交」的**帶寬**（判準本身 2026-09-08 有了："
    "`MI_INDEX` 漲跌家數 vs 日檔，見 `_breadth_audit.csv`；"
    "但只累積了五天，還不足以訂差值帶寬，目前只驗方向）",
    "上櫃的交易日曆從未被獨立驗證（FMTQIK 只有上市）",
]


def now_tpe():
    return datetime.now(TPE)


def _rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def _count_dir(d, pat="*.csv"):
    return len(glob.glob(os.path.join(d, pat))) if os.path.isdir(d) else 0


def _span(rows, key):
    ds = sorted({r[key] for r in rows if r.get(key)})
    return (ds[0], ds[-1], len(ds)) if ds else ("—", "—", 0)


def section_layers(out):
    out.append("## ① 各層現況\n")
    out.append("| 層 | 檔／列 | 區間 | 預期 |")
    out.append("|---|---|---|---|")
    uni = os.path.join(DATA, "universe")
    layers = [
        ("價格 `data/stocks/`", os.path.join(DATA, "stocks"), "stocks"),
        ("三大法人 `data/stocks_inst/`", os.path.join(DATA, "stocks_inst"), "stocks_inst"),
        ("融資融券 `data/stocks_margin/`", os.path.join(DATA, "stocks_margin"), "stocks_margin"),
        ("本益比 `data/stocks_per/`", os.path.join(DATA, "stocks_per"), "stocks_per"),
        ("還原因子 `data/adj/`", os.path.join(DATA, "adj"), "adj"),
        ("興櫃 `data/universe/esb/`", os.path.join(uni, "esb"), "esb"),
    ]
    for label, d, key in layers:
        n = _count_dir(d)
        exp = EXPECT.get(key, 0)
        mark = "" if n >= exp else f" ★ 少於預期 {exp}"
        out.append(f"| {label} | {n} 檔 | — | {exp}+{mark} |")

    days = sorted(os.path.basename(p)[:-4]
                  for p in glob.glob(os.path.join(uni, "daily", "*.csv")))
    exp = EXPECT["daily"]
    mark = "" if len(days) >= exp else f" ★ 少於預期 {exp}"
    out.append(f"| 日檔 `data/universe/daily/` | {len(days)} 天 | "
               f"{days[0] if days else '—'} ~ {days[-1] if days else '—'} | {exp}+{mark} |")

    cal = _rows(os.path.join(META, "calendar_twse.csv"))
    if cal and days:
        k = list(cal[0].keys())[0]
        cs = {r[k] for r in cal}
        miss = sorted(set(cs) - set(days))
        out.append(f"| 交易日曆 `calendar_twse.csv` | {len(cs)} 天 | — | "
                   f"日曆有而日檔沒有：**{len(miss)} 天**"
                   + (f"（{'、'.join(miss[:5])}…）" if miss else "") + " |")
    out.append("")


def section_events(out):
    out.append("## ② 事件類與基本面\n")
    specs = [
        ("停牌 `suspend.csv`", "suspend.csv", "halt_date"),
        ("處置 `disposal.csv`", "disposal.csv", "start_date"),
        ("注意 `attention.csv`", "attention.csv", "date"),
    ]
    out.append("| 檔 | 列數 | 區間 | 市場 | 種類 |")
    out.append("|---|---|---|---|---|")
    for label, fn, dk in specs:
        r = _rows(os.path.join(META, fn))
        if not r:
            out.append(f"| {label} | **0（檔不存在或空的）** | — | — | — |")
            continue
        lo, hi, nd = _span(r, dk)
        mk = collections.Counter(x.get("market", "") for x in r)
        kd = collections.Counter(x.get("sec_kind", "") for x in r)
        empt = sum(1 for x in r if not x.get(dk))
        note = f"｜★ 空日期 {empt}" if empt else ""
        out.append(f"| {label} | {len(r)}{note} | {lo} ~ {hi}（{nd} 天）| "
                   f"{dict(mk)} | {dict(kd)} |")
    out.append("")

    cap = _rows(os.path.join(META, "capital.csv"))
    if cap:
        by = collections.Counter(x["market"] for x in cap)
        blank = collections.Counter(x["market"] for x in cap
                                    if not (x.get("capital") or "").strip())
        mis = [x for x in cap if (x.get("note") or "").startswith("mismatch")]
        odd = [x for x in mis if "*" not in x["name"] and "DR" not in x["name"]]
        out.append("**股本 `capital.csv`**\n")
        for m in sorted(by):
            out.append(f"- {m}：{by[m]} 檔，股本空白 {blank.get(m, 0)}")
        out.append(f"- mismatch {len(mis)} 檔"
                   + (f"，**其中 {len(odd)} 檔不帶 `*` 也不是 DR ★ 要查**" if odd
                      else "（全部帶 `*` 或 DR，屬已知限制）"))
        out.append("")

    ind = _rows(os.path.join(META, "industry.csv"))
    if ind and cap:
        ii = {x["stock_id"] for x in ind}
        cc = {x["stock_id"] for x in cap}
        noname = collections.Counter(
            (x["market"], x.get("industry_code", ""))
            for x in ind if not (x.get("industry_name") or "").strip())
        out.append("**產業別 `industry.csv`**\n")
        out.append(f"- {len(ind)} 檔；有股本但無產業別 {len(cc - ii)}、"
                   f"有產業別但無股本 **{len(ii - cc)}**")
        if noname:
            out.append("- 無中文名的代碼：" +
                       "、".join(f"{m} {c}（{n} 檔）" for (m, c), n in sorted(noname.items())))
        out.append("")

    hist = os.path.join(DATA, "mops", "_hist_status.csv")
    hr = _rows(hist)
    if hr:
        st = collections.Counter(x.get("status", "") for x in hr)
        out.append(f"**財報回補帳本 `_hist_status.csv`**：{len(hr)} 列 {dict(st)}")
        out.append("　⚠ 這個帳本記的是**上一趟碰到的期別**，不是資料庫現況。"
                   "要判斷有沒有洞得看 `data/mops/*_hist/` 本身。\n")


def section_lastrun(out):
    out.append("## ③ 最近一輪各支腳本\n")
    p = os.path.join(META, "_last_run.md")
    if not os.path.exists(p):
        out.append("（`_last_run.md` 還不存在——**沒有任何一支腳本用新版跑過**）\n")
        return
    txt = open(p, encoding="utf-8").read()
    bad = [ln for ln in txt.splitlines() if ln.startswith("- **✗**")]
    heads = [ln for ln in txt.splitlines() if ln.startswith("## ")]
    for h in heads:
        out.append(f"- {h[3:]}")
    if bad:
        out.append("\n**沒過的檢查：**")
        out += [f"  {x}" for x in bad]
    out.append("")


def section_nosource(out):
    out.append("## ④ 完全沒有來源（人維護的清單，不是算出來的）\n")
    for x in NO_SOURCE:
        out.append(f"- {x}")
    out.append("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(DATA):
        print("[db_status] 找不到 data/，要在 repo 根目錄跑", file=sys.stderr)
        return 1

    out = [f"# 資料庫現況　{now_tpe().isoformat(timespec='seconds')}（台北）", "",
           "**這一頁報的是資料庫現況，不是某一趟做了什麼。**", ""]
    section_layers(out)
    section_events(out)
    section_lastrun(out)
    section_nosource(out)
    text = "\n".join(out)
    print(text)
    if a.write:
        os.makedirs(META, exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\n[db_status] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
