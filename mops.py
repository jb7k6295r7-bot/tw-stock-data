#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops.py — 全市場月營收與財報（MOPS openapi）。

## 這支能做什麼、不能做什麼

**能**：一次拿到**全市場當期**的月營收、綜合損益表、資產負債表（上市＋上櫃）。
2026-09-06 實測完整性：上市月營收 1,085 筆（涵蓋 99.1%）、財報 1,048 筆（95.8%），
上櫃月營收 890 筆（99.9%）、財報 882 筆（99.1%），**分段涵蓋率無斷崖、末代號到 9958／9962**。

**不能**：拿歷史。**這些端點沒有日期參數**，只回「最新一期」。
→ **歷史只能從現在開始逐期累積**，或對特定個股用 FinMind 逐檔補。
   選股（看當期營收年增、毛利率）夠用；**回測要等累積**。

## 為什麼 2026-08-30 判它「不可用」是錯的

當時的結論是「大型全市場 JSON **靜默截斷**」，於是停用了 `t187ap06/07_L_ci`。
2026-09-06 用 urllib 重測，四條主力全部完整。
**那次是 WebFetch 的限制，不是端點的性質**——
`docs/READ_CONTRACT.md` 第四節本來就寫著「不要用 WebFetch 讀大 JSON」。

**教訓：端點的可用性結論要標明是用什麼工具測的。** 同一個誤判已經發生兩次
（`t187ap03_L`、`MI_MARGN`）。

## ★ 三個設計決定

**1. 業別分表不合併。** 銀行的損益表有「利息淨收益、存放央行及拆借銀行同業」，
一般業有「營業收入、營業成本、營業毛利」——**欄位意義完全不同**。
硬塞成一張表會產出幾百欄、絕大多數是空的怪物，而且**看不出哪一欄對哪一種公司有意義**。
→ 財報按業別各自存檔（`115Q2_ci.csv`、`115Q2_basi.csv`…）。
月營收所有業別共用同一組欄位，才合併成一檔。

**2. 期別從資料自己的欄位取，不從今天推算。**
月營收用 `資料年月`、財報用 `年度`＋`季別`。
**沙箱時鐘實測差過一天**，而且公告有落差——用今天推期別一定會錯。

**3. 同一期的內容變了要記錄，不是靜默覆蓋。**
**財報會更正**。已存在的期別若內容不同，逐欄差異寫進 `data/mops/_changes.log`，
與價格管線的 `data/_changes.log` 同一個做法。**靜默覆蓋等於把更正藏起來。**
"""

import argparse

import runlog
import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_DIR = os.path.join(_ROOT, "mops")
IND = os.path.join(_ROOT, "meta", "industry.csv")
CHANGES = os.path.join(OUT_DIR, "_changes.log")

TWSE = "https://openapi.twse.com.tw/v1/opendata/"
TPEX = "https://www.tpex.org.tw/openapi/v1/"

# kind → [(業別標籤, 上市網址, 上櫃網址)]
#   業別標籤 ci=一般業 basi=銀行 bd=證券 ins=保險 fh=金控 oth=其他
#   ★ 抓不到的直接略過並回報，**不要當成錯誤**——不是每個業別在兩個市場都有分表。
SOURCES = {
    "revenue": [("all", TWSE + "t187ap05_L", TPEX + "mopsfin_t187ap05_O")],
    "fs": [
        ("ci",   TWSE + "t187ap06_L_ci",   TPEX + "mopsfin_t187ap06_O_ci"),
        ("basi", TWSE + "t187ap06_L_basi", TPEX + "mopsfin_t187ap06_O_basi"),
        ("bd",   TWSE + "t187ap06_L_bd",   TPEX + "mopsfin_t187ap06_O_bd"),
        ("ins",  TWSE + "t187ap06_L_ins",  TPEX + "mopsfin_t187ap06_O_ins"),
        ("fh",   TWSE + "t187ap06_L_fh",   TPEX + "mopsfin_t187ap06_O_fh"),
    ],
    "bs": [
        ("ci",   TWSE + "t187ap07_L_ci",   TPEX + "mopsfin_t187ap07_O_ci"),
        ("basi", TWSE + "t187ap07_L_basi", TPEX + "mopsfin_t187ap07_O_basi"),
        ("bd",   TWSE + "t187ap07_L_bd",   TPEX + "mopsfin_t187ap07_O_bd"),
        ("ins",  TWSE + "t187ap07_L_ins",  TPEX + "mopsfin_t187ap07_O_ins"),
        ("fh",   TWSE + "t187ap07_L_fh",   TPEX + "mopsfin_t187ap07_O_fh"),
    ],
}

# ★★ **上市與上櫃的欄名不同**，2026-09-06 實測：
#     上市 t187ap06_L_ci  → 公司代號／公司名稱／年度／季別
#     上櫃 mopsfin_..._O_ci → SecuritiesCompanyCode／CompanyName／Year／Season
#   直接把欄位聯集起來寫檔，會產出「1,930 列但 `公司代號` 有 882 列是空的」——
#   讀的人用 `公司代號` 查只拿到上市那一半，**而檔案看起來是完整的**。
#   → 一律正規化出 `stock_id`／`name`／`period` 三個欄位放最前面，
#     原始欄位保留在後面。這也與資料庫其他地方的 `stock_id` 命名一致。
CODE_KEYS = ("公司代號", "SecuritiesCompanyCode")
NAME_KEYS = ("公司名稱", "CompanyName")
YM_KEYS = ("資料年月",)
Y_KEYS = ("年度", "Year")
Q_KEYS = ("季別", "Season")
# ★ 出表日期兩種欄名都要收。**來源端每一張表、每個市場用哪一組是不固定的**：
#   2026-09-08 實測 fs/2026Q2_ci.csv 上櫃全用英文、上市全用中文；
#   fs/2026Q2_bd.csv 上櫃**同一列混用**（Date 英文 ＋ 年度／季別／公司代號中文
#   ＋ CompanyName 英文）；bs/2026Q2_bd.csv 兩個市場又都用中文。
#   規則不存在，所以不能靠「哪個市場用哪一組」去讀——**只能兩種都收**。
DATE_KEYS = ("出表日期", "Date")


def _pick(rec, keys):
    for k in keys:
        v = rec.get(k)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def _roc_ym(v):
    """民國年月 `11507` → `2026-07`。抓不到就回原字串（**不猜**）。"""
    s = "".join(ch for ch in str(v) if ch.isdigit())
    if len(s) in (5, 6):
        y, m = int(s[:-2]) + 1911, int(s[-2:])
        if 1 <= m <= 12:
            return f"{y:04d}-{m:02d}"
    return str(v).strip()


def _roc_y(v):
    s = "".join(ch for ch in str(v) if ch.isdigit())
    return str(int(s) + 1911) if s and len(s) <= 4 and int(s) < 1000 else str(v).strip()


def fetch(url):
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        return None, err
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                   # noqa: BLE001
        head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
        return None, f"非 JSON（{len(raw):,}B）{type(ex).__name__}：{head}"
    if not isinstance(d, list):
        return None, f"不是 list，頂層是 {type(d).__name__}"
    return d, f"{len(d):,} 筆"


def period_of_row(kind, r):
    """→ **這一列自己**講出來的期別（取不到回 ""）。⛔ 不從今天推算。"""
    if kind == "revenue":
        return _roc_ym(_pick(r, YM_KEYS))
    y, q = _roc_y(_pick(r, Y_KEYS)), _pick(r, Q_KEYS)
    return f"{y}Q{q}" if y and q else ""


def group_by_period(kind, recs):
    """→ ({期別: [列, …]}, 取不到期別的列數)。

    ⛔⛔ 2026-09-14 之前這裡是 `period_of()`：把整批資料**取最常見的那一期**，
    然後把**所有**列寫進那一期的檔。實測踩到的後果：

        data/mops/revenue/2026-07.csv　1,976 列
          twse 1,085 列　資料年月 = 11507　✅
          tpex 　891 列　資料年月 = **11508**　⛔ 八月的資料，貼著七月的檔名

    ⚠ 成因是兩個市場的**申報進度不同步**（上市 7 月、上櫃已經 8 月），
    而它們被併成一批才取期別 ⇒ **少數那一邊被貼上多數那一邊的期別**。
    ⛔ 而 `period` 欄整欄會被覆蓋成檔名那一期 ⇒ 每一列自己的 `資料年月` 是對的，
    **只有檔名與 `period` 欄是錯的**——而大部分人是照檔名讀的。

    ⚠ 舊版**有印警告**（「同一批資料含多個期別，取最常見的」），
    ⛔ 而它照樣把兩期寫進同一個檔 ⇒ **警告不是閘門**。

    ⇒ ⭐ 判準改成 CLAUDE.md 第二點那一句：**這一批要自己講出它是哪一期**
      ——一批資料含兩期就寫**兩個檔**，⛔ 不是挑一個。
    """
    groups, noperiod = {}, 0
    for r in recs:
        v = period_of_row(kind, r)
        if not v:
            noperiod += 1
            continue
        groups.setdefault(v, []).append(r)
    return groups, noperiod


def write_period(kind, tag, period, recs, market_of):
    """寫一期一業別的檔。已存在且內容不同 → 逐欄差異寫進 changes log。"""
    d = os.path.join(OUT_DIR, kind)
    os.makedirs(d, exist_ok=True)
    name = f"{period}.csv" if tag == "all" else f"{period}_{tag}.csv"
    path = os.path.join(d, name)

    # 原始欄位（兩市場的聯集），正規化欄放最前面
    raw_cols = []
    for r in recs:
        for k in r:
            if k not in raw_cols:
                raw_cols.append(k)
    # ★ 正規化欄放最前面。原始欄位原樣保留在後面，供逐欄對來源用。
    #   `報表日期` 是第五個正規化欄（2026-09-08 新增）：年度／季別已經被 `period`
    #   涵蓋、公司代號與名稱被 `stock_id`／`name` 涵蓋，只有出表日期沒有對應，
    #   而它的原始欄名在來源端是浮動的（見 DATE_KEYS）。
    #   ⚠ 下游一律讀正規化欄；原始欄有沒有值取決於來源那天給哪一組欄名。
    cols = ["stock_id", "name", "period", "market", "報表日期"] + raw_cols

    rows, nocode = [], 0
    for r in recs:
        code = _pick(r, CODE_KEYS)
        if not code:
            nocode += 1
            continue
        rows.append([code, _pick(r, NAME_KEYS), period,
                     market_of.get(id(r), ""), _pick(r, DATE_KEYS)]
                    + [str(r.get(c, "")).strip() for c in raw_cols])
    # ★ 取不到代號的列**不寫**，並回報。寧可少一列，不要寫一列查不到是誰的。
    if nocode:
        print(f"  ⚠ {kind}/{tag} 有 {nocode} 列取不到代號，已丟棄", file=sys.stderr)
    # ⛔⛔ 2026-09-14：這裡本來是**整檔取代**，而分期之後那會刪資料（四點六①）。
    #   實際會發生的：run 47 把上市 1,074 列寫進 2026-08.csv；
    #   下一趟上櫃也換到 8 月 ⇒ 這一批的 2026-08 組**只有上櫃 891 列**
    #   ⇒ 整檔取代 ⇒ ⛔ **上市那 1,074 列被刪掉**，而 git diff 看起來像「重算過」。
    # ⇒ ⭐ 判準照四點六那一句：**這一趟只知道自己那一部分 ⇒ 一律合併，不是取代。**
    #   本趟的鍵覆蓋、其餘原封不動；鍵是 (market, 代號)。
    kept = 0
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as f:
            rd = csv.DictReader(f)
            oldcols = list(rd.fieldnames or [])
            oldrows = list(rd)
        mine = {(r[3], r[0]) for r in rows}
        for c in oldcols:                      # ⚠ 舊欄不可以因為本趟沒有就消失
            if c not in cols:
                cols.append(c)
        add = []
        for r in oldrows:
            k = (r.get("market", ""), r.get("stock_id", ""))
            if k in mine:
                continue
            add.append([str(r.get(c, "")).strip() for c in cols])
            kept += 1
        rows = [row + [""] * (len(cols) - len(row)) for row in rows] + add
    if kept:
        print(f"  [{kind}/{tag}] ⭐ 合併：本趟 {len(rows) - kept} 列 ＋ "
              f"保留檔上原有的 {kept} 列（⛔ 不是整檔取代）")
    rows.sort(key=lambda x: (x[3], x[0]))

    new = [",".join('"' + c.replace('"', '""') + '"' if ("," in c or '"' in c) else c
                    for c in row) for row in [cols] + rows]
    body = "\n".join(new) + "\n"

    if os.path.exists(path):
        old = open(path, encoding="utf-8").read()
        if old == body:
            return "unchanged", len(rows)
        # ★ 財報會更正。差異要留痕，不可靜默覆蓋。
        _log_changes(kind, name, old, body)
        open(path, "w", encoding="utf-8").write(body)
        return "changed", len(rows)
    open(path, "w", encoding="utf-8").write(body)
    return "new", len(rows)


def repair_periods(kind, apply=True):
    """把**已經寫錯期別**的舊列搬回它自己那一期的檔。→ (搬了幾列, 訊息)

    ⛔ 這一支存在的理由是 `group_by_period` 修不到的那一半：
    修好之後只有**未來**的資料會分對，⚠ 而 main 上已經躺著

        data/mops/revenue/2026-07.csv 裡的上櫃 891 列，`資料年月` 是 **11508**

    ⇒ 而它不會自己好：下一趟上市若也換到 8 月，就**沒有人會再寫 2026-07.csv**，
    那 891 列會**永遠**掛在錯的檔名下。

    ⭐ 判準只有一句（第二點）：**每一列自己講出來的期別，要跟檔名那一期相同。**

    ⛔⛔ 而這一支自己絕不可以變成刪東西的那個人（四點六）：
      ① 搬家前後的**總列數必須相同**——不相等就**一列都不寫**並大聲失敗
      ② 取不到期別的列**原地不動**（⛔ 不是丟掉）
      ③ 目的檔已經有同一個代號時，**以那一列自己期別對的那份為準**，
         ⚠ 而且要講出來（同一檔同一期同一代號出現兩次是異常，不是雜訊）
    """
    d = os.path.join(OUT_DIR, kind)
    if not os.path.isdir(d):
        return 0, "沒有這個目錄"
    files = sorted(f for f in os.listdir(d) if f.endswith(".csv"))
    # tag → {期別 → {代號 → 列(dict)}}；並記下每個 tag 的欄序
    buckets, colorder, n_in, stay = {}, {}, 0, 0
    for fn in files:
        base = fn[:-4]
        period, tag = (base.split("_", 1) + ["all"])[:2]
        with io.open(os.path.join(d, fn), encoding="utf-8") as f:
            rd = csv.DictReader(f)
            cols = list(rd.fieldnames or [])
            rows = list(rd)
        colorder.setdefault(tag, cols)
        # ⭐ 每一個**來源檔**都要被重寫一次，⛔ 否則「整批都搬走了」的檔
        #   會原封不動留在原地 ⇒ 同一列在兩個檔裡各有一份（實測踩到）。
        buckets.setdefault(tag, {}).setdefault(period, {})
        for r in rows:
            n_in += 1
            own = period_of_row(kind, r) or period      # ② 取不到 ⇒ 留在原地
            if own == period:
                stay += 1
            buckets.setdefault(tag, {}).setdefault(own, {})
            code = r.get("stock_id") or _pick(r, CODE_KEYS)
            key = (code, r.get("market", ""))
            prev = buckets[tag][own].get(key)
            if prev is not None and prev is not r:
                print(f"  ⚠ {kind}/{tag}/{own} 同一個代號出現兩次：{key}",
                      file=sys.stderr)
            r["period"] = own                            # ⭐ 欄也要跟著改
            buckets[tag][own][key] = r
    moved = n_in - stay
    n_out = sum(len(v) for t in buckets.values() for v in t.values())
    if n_out != n_in:
        # ① 不相等就一列都不寫
        return -1, (f"⛔ 搬家前 {n_in} 列、搬家後 {n_out} 列 ⇒ **一列都不寫**"
                    f"（差 {n_in - n_out} 列，多半是同一期同一代號重複）")
    if not moved:
        return 0, f"{len(files)} 個檔、{n_in} 列，每一列都在對的期別"
    if not apply:
        return moved, f"⚠ 有 {moved} 列在錯的期別（--repair-periods 才會搬）"
    for tag, byper in buckets.items():
        cols = colorder[tag]
        for period, rows in byper.items():
            name = f"{period}.csv" if tag == "all" else f"{period}_{tag}.csv"
            out = sorted(rows.values(), key=lambda x: (x.get("market", ""),
                                                       x.get("stock_id", "")))
            body = ",".join(cols) + "\n" + "".join(
                ",".join('"' + str(r.get(c, "")).replace('"', '""') + '"'
                         if ("," in str(r.get(c, "")) or '"' in str(r.get(c, "")))
                         else str(r.get(c, "")) for c in cols) + "\n"
                for r in out)
            path = os.path.join(d, name)
            if not out:
                # ⚠ 整批都搬走了 ⇒ **刪掉這個檔**，⛔ 不是留一個只有表頭的空殼：
                #   空殼會被讀成「那一期沒有資料」（四點二②：檔案存在 ≠ 內容還在）。
                if os.path.exists(path):
                    os.remove(path)
                    print(f"  ⚠ {kind}/{name} 整批都搬走了 ⇒ 刪掉這個空檔",
                          file=sys.stderr)
                continue
            old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if old != body:
                if old:
                    _log_changes(kind, name, old, body)
                io.open(path, "w", encoding="utf-8").write(body)
    return moved, f"⭐ 搬了 {moved} 列回它自己那一期（總列數 {n_in} 不變）"


def _log_changes(kind, name, old, new):
    """逐欄比對並記錄差異。

    ⛔ **一律按欄名比對，不可按位置。**
    舊版是 `zip(舊列, 新列)` 按位置配、欄名卻取自舊表頭——**欄序改一次，
    每一格都對到別人的值**：2026-09-06 一次塞進上百筆「market: twse→2816」
    這種鬼影，而實際檔案是對齊的、一個數字都沒變。

    財報本來就會更正，這個 log 存在的唯一理由就是「更正不可以被靜默覆蓋」。
    真的更正被鬼影淹掉，這個機制等於不存在——**比沒有還糟，因為它看起來在運作。**

    表頭變動（新增欄／移除欄／換順序）記成**一行檔案層級的紀錄**，
    不讓它變成每一列都在變。值的比對只取兩邊都有的欄。
    """
    def index(txt):
        rd = list(csv.reader(txt.splitlines()))
        if not rd:
            return {}, []
        h = rd[0]
        ic = next((i for i, c in enumerate(h) if c in CODE_KEYS), 1)
        # 每一列存成 {欄名: 值}，之後一律用欄名取值
        return {r[ic]: dict(zip(h, r)) for r in rd[1:] if len(r) > ic}, h
    o, oh = index(old)
    n, nh = index(new)
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    lines, nrow = [], 0
    if oh != nh:
        added = [c for c in nh if c not in oh]
        removed = [c for c in oh if c not in nh]
        what = []
        if added:
            what.append("新增欄 " + "、".join(added))
        if removed:
            what.append("移除欄 " + "、".join(removed))
        if not what:
            what.append("欄序改變（欄名集合相同，值不受影響）")
        lines.append(f"{ts}\t{kind}/{name}\t(表頭)\t{'；'.join(what)}")
    common = [c for c in nh if c in oh]
    for code in sorted(set(o) | set(n)):
        if code not in o:
            lines.append(f"{ts}\t{kind}/{name}\t{code}\t新增")
            nrow += 1
        elif code not in n:
            lines.append(f"{ts}\t{kind}/{name}\t{code}\t消失")
            nrow += 1
        else:
            diff = [f"{c}: {o[code].get(c, '')}→{n[code].get(c, '')}"
                    for c in common if o[code].get(c, "") != n[code].get(c, "")]
            if diff:
                # ★ 截斷要說出來。舊版直接 [:6]，看起來就像「只差 6 欄」。
                more = f"（另有 {len(diff) - 6} 欄）" if len(diff) > 6 else ""
                lines.append(f"{ts}\t{kind}/{name}\t{code}\t"
                             f"{'; '.join(diff[:6])}{more}")
                nrow += 1
    if lines:
        with open(CHANGES, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        parts = []
        if oh != nh:
            parts.append("表頭變動")
        if nrow:
            parts.append(f"{nrow} 檔內容變動（**財報更正**）")
        print(f"  ⚠ {name} {'＋'.join(parts)}，已記入 _changes.log", file=sys.stderr)


def listed_codes():
    tw, tp = set(), set()
    if os.path.exists(IND):
        with open(IND, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                (tw if r["market"] == "twse" else tp).add(r["stock_id"])
    return tw, tp


def cmd_run(args):
    B.SLEEP = args.sleep
    # ⭐ 先自癒再抓：⛔ 抓完再搬的話，這一趟寫進去的列會先跟舊的錯列混在一起。
    #   ⚠ 乾淨的時候它是 no-op（不寫檔、不產生 commit）。
    repaired = []
    for _k in SOURCES:
        if args.kind in ("all", _k):
            _n, _msg = repair_periods(_k)
            if _n:
                repaired.append((_k, _n, _msg))
                print(f"[mops] 期別自癒 {_k}：{_msg}",
                      file=sys.stderr if _n < 0 else sys.stdout)
    tw, tp = listed_codes()
    print(f"[mops] 對照基準：上市 {len(tw):,} 檔、上櫃 {len(tp):,} 檔\n")
    total = {"new": 0, "changed": 0, "unchanged": 0, "skip": 0}
    # ★ 逐「表×市場」記下實際結果。**不要只留一個總數**——
    #   22 個請求裡少收一個，總數看起來還是很像正常的一天
    #   （限流回 307、端點改名，兩種都不會讓程式失敗）。
    calls = []          # (kind, tag, market, 有沒有回應, 列數, 涵蓋率)
    # ★ 涵蓋 0% 時要留下**證據**，不是只留一個數字。
    #   「有回應但一列都對不上母體」有兩種完全不同的成因，處置相反：
    #     ① 鍵對不起來（代號格式變了、期別 parser 不吃上櫃格式）→ 改解析
    #     ② 端點根本回了另一個市場的表（市場參數被無視）→ 這條路不能用
    #   ⛔ **光看涵蓋率分不出是哪一種**，而先改 parser 會把 0% 變成
    #     看起來正常的假值。所以這裡把原始列**原樣**留下來，讓人下一趟直接看。
    zero_raw = {}
    retried = []          # ⭐ 第一次失敗、重試才成功的：**要留在 runlog 裡**
    # ⭐ 同一批資料含多個期別的：⛔ 這件事只印在 stderr 是不夠的
    #   （舊版就是「有印警告、照樣寫錯檔」）⇒ 要進 runlog 讓人看得到。
    multi = []            # (kind, tag, {期別: 列數})
    for kind, srcs in SOURCES.items():
        if args.kind not in ("all", kind):
            continue
        for tag, u_tw, u_tp in srcs:
            recs, market_of = [], {}
            for mk, url, want in (("twse", u_tw, tw), ("tpex", u_tp, tp)):
                d, note = fetch(url)
                time.sleep(B.SLEEP)
                if d is None:
                    # ⛔ 22 個請求裡掛 1 個（2026-09-11 是 `fs/ci/tpex`），
                    #   而 `B.get` 的 retries=2 是**同一個時間窗**內連打三發
                    #   ⇒ 被限流時三發一起掛，跟「這張表不存在」長得一模一樣。
                    # ⇒ ⭐ 隔久一點再試**一次**，⛔ 而且要把「是重試才活的」講出來：
                    #   一張天天要重試才活的表，跟一張一次就過的表**不是同一件事**，
                    #   ⚠ 靜靜重試成功會把那個訊號抹掉。
                    time.sleep(B.SLEEP * 4)
                    d2, note2 = fetch(url)
                    time.sleep(B.SLEEP)
                    if d2 is None:
                        calls.append((kind, tag, mk, False, 0, 0.0, 0.0))
                        print(f"  [{kind}/{tag}/{mk}] 略過（**隔久再試一次也不行**）："
                              f"{note[:70]}｜重試：{note2[:70]}")
                        continue
                    retried.append((f"{kind}/{tag}/{mk}", note[:60]))
                    print(f"  [{kind}/{tag}/{mk}] ⚠ 第一次失敗（{note[:60]}），"
                          f"**隔久再試一次成功**：{note2}")
                    d, note = d2, note2
                # ⛔ **一列沒有公司代號的列，不是一列資料。**
                #   2026-09-09 實測：上櫃的 fs/bs × basi／ins／fh 六張表
                #   **各回 1 列，而那一列的「公司代號」是空的**、年度季別也是空的，
                #   只有一個出表日期（bs/ins 甚至是 1100616，2021 年的舊日期）。
                #   那是 TPEx 表示「這個業別在上櫃沒有公司」的方式——
                #   上櫃的 9 檔金融全是證券商、期貨與保經，銀行／保險／金控真的是 0 家。
                #
                #   原本用 `len(d)` 當列數，於是「1 列佔位列」被當成「有 1 列資料」，
                #   涵蓋率算成 0% → 六張表天天報 ✗。**天天紅的紅字沒有人會看。**
                #   → 只有**帶得出代號**的列才算資料列。
                #   ⚠ 這樣做**沒有削弱防護**：真正要抓的是「代號有值、但格式變了對不上母體」，
                #     那種情形代號不空，照樣會被抓到。這一改只是不再把空列當資料列。
                real = [r for r in d if _pick(r, CODE_KEYS)]
                got = {_pick(r, CODE_KEYS) for r in real}
                cov = len(got & want) / len(want) * 100 if want else 0
                # ★★ `cov` 的分母是**整個市場母體**，對「業別表」幾乎沒有意義：
                #   證券商（bd）全市場只有 10 家，就算一家不漏，
                #   1,094 檔當分母也只有 **0.3%**。所以「涵蓋 > 0%」這道檢查
                #   對業別表**只擋得住全滅**，任何一列對得上就過關——
                #   而它本來要抓的「代號格式變了」剛好會留下少數幾列對得上。
                #   ⛔ 這是**分母選錯**，不是門檻訂太鬆；調門檻救不了。
                #
                #   → 另外算一個分母正確的：**回來的列裡有幾列是母體認得的**。
                #     格式一變，這個數字會直接掉到接近 0，不受業別大小影響。
                #   2026-09-09 實測：11 張表全部 100%（revenue 99.9%，
                #   差的 2 列是已下市或尚未進母體的，屬正常）。
                known = sum(1 for r in real if _pick(r, CODE_KEYS) in want)
                recog = known / len(real) * 100 if real else 100.0
                calls.append((kind, tag, mk, True, len(real), cov, recog))
                if len(real) != len(d):
                    print(f"  [{kind}/{tag}/{mk}] 回 {len(d)} 列，其中 "
                          f"{len(d) - len(real)} 列沒有公司代號（佔位列，不計）")
                if real and cov == 0:
                    # 原樣留前 3 列的鍵欄位，不整理、不轉型
                    zero_raw[f"{kind}/{tag}/{mk}"] = {
                        "回應前3列的鍵": [
                            {k: r.get(k) for k in list(r)
                             if any(w in k for w in ("代號", "Code", "年度", "季別",
                                                     "Year", "Season", "Date", "日期"))}
                            for r in d[:3]],
                        "我方母體的鍵樣本": sorted(want)[:5],
                        "母體檔數": len(want),
                        # ⚠ 情報分析線 2026-09-09 指出：**只吐鍵樣本會漏掉
                        #   「回了 0 列」與「回了 500 列但全對不上」的差別**，
                        #   而那兩種的處置不一樣。所以列數三個都要吐。
                        "回應列數（原始）": len(d),
                        "回應列數（帶得出代號的）": len(real),
                        "回應裡的相異代號數": len(got),
                        "對得上母體的列數": len(got & want)}
                print(f"  [{kind}/{tag}/{mk}] {note}｜涵蓋 {cov:.1f}%")
                for r in d:
                    market_of[id(r)] = mk
                recs += d
            if not recs:
                total["skip"] += 1
                continue
            groups, noperiod = group_by_period(kind, recs)
            if noperiod:
                # ★ 取不到期別的列**不寫**（不從今天推算），但要講出來
                print(f"  [{kind}/{tag}] ✗ {noperiod} 列取不到期別，**不寫**"
                      f"（不從今天推算）", file=sys.stderr)
            if not groups:
                total["skip"] += 1
                continue
            if len(groups) > 1:
                # ⭐ 不再是「取最常見的」——每一期各寫各的檔
                print(f"  [{kind}/{tag}] ⚠ 同一批資料含 {len(groups)} 個期別："
                      + "、".join(f"{k}({len(v)} 列)"
                                  for k, v in sorted(groups.items()))
                      + " ⇒ **分開寫檔**", file=sys.stderr)
                multi.append((kind, tag,
                              {k: len(v) for k, v in sorted(groups.items())}))
            for period in sorted(groups):
                st, n = write_period(kind, tag, period, groups[period], market_of)
                total[st] += 1
                print(f"  [{kind}/{tag}] 期別 {period}｜{n:,} 列｜{st}")
    print(f"\n[mops] 完成：新增 {total['new']}、更新 {total['changed']}、"
          f"無變動 {total['unchanged']}、略過 {total['skip']}")
    print("[mops] ★ 這些端點只給最新一期，**沒有歷史**。回測要等逐期累積。")

    # ★ 寫進 data/meta/_last_run.md 的「mops」區塊。
    #   這支的壞法都是**安靜的**，而且長得跟「今天沒換期」一模一樣：
    #     ① 限流／端點改名 → 那一張表整個沒收到，總數看起來仍正常
    #     ② 有回應但代號對不上我方母體（格式變了）→ 涵蓋 0% 卻照樣寫檔
    #     ③ 取不到期別 → 不寫檔（對的），但只印一行 stderr
    #   三個都要變成 check。
    rl = runlog.Run("mops")
    rl.info("這一趟", f"新增 {total['new']}、更新 {total['changed']}、"
                      f"無變動 {total['unchanged']}、略過 {total['skip']}")
    rl.info("請求", f"{len(calls)} 個（表 × 市場），"
                    f"有回應 {sum(1 for c in calls if c[3])} 個")
    dead = [f"{c[0]}/{c[1]}/{c[2]}" for c in calls if not c[3]]
    rl.check("每一個表×市場都有回應", not dead,
             ("沒回應（**隔久再試一次也不行**）：" + "、".join(dead))
             if dead else f"{len(calls)} 個全有")
    # ⛔ 這一列即使是 0 也要在：⚠ 靜靜重試成功 ＝ 把「這張表在惡化」的訊號抹掉。
    rl.info("⚠ 第一次失敗、隔久再試才成功的",
            (f"{len(retried)} 個："
             + "、".join(f"{k}（{w}）" for k, w in retried[:5])
             + "　⇒ ⛔ 連續幾趟都出現同一個 ⇒ 那不是限流，是那張表在惡化")
            if retried else "0 個")
    # ⚠ **回 0 列不算失敗。** 2026-09-08 第一次上線就誤殺六張表：
    #   fs/bs 的 basi（銀行）／ins（保險）／fh（金控）在**上櫃根本沒有公司**——
    #   上櫃的 9 檔金融全是證券商、期貨與保經。那三張表回 0 列是事實，不是抓不到。
    #   要抓的是「**回了列、卻一列都對不上我方母體**」——那才代表代號格式變了。
    #   （防護誤殺跟防護失效一樣糟：天天紅的紅字沒有人會看。）
    empty = [f"{c[0]}/{c[1]}/{c[2]}" for c in calls if c[3] and c[4] == 0]
    if empty:
        rl.info("回 0 列的表", "、".join(empty) + "（該市場沒有這個業別的公司）")
    zero = [f"{c[0]}/{c[1]}/{c[2]}" for c in calls if c[3] and c[4] > 0 and c[5] == 0]
    live = [c[5] for c in calls if c[3] and c[4] > 0]
    rl.check("有列的表都對得上我方母體（涵蓋 > 0%）", not zero,
             ("涵蓋 0%：" + "、".join(zero)) if zero
             else f"{len(live)} 張有列的表，最低 {min(live, default=0):.1f}%"
                  "（⚠ 分母是整個市場，業別表本來就低，見下一項）")
    # ★ 這一項才是真的在抓「代號格式變了」：分母是**回來的列數**，
    #   與業別大小無關。低於 90% 就是回來的東西我方大半不認得。
    poor = [f"{c[0]}/{c[1]}/{c[2]}（{c[6]:.0f}%）"
            for c in calls if c[3] and c[4] > 0 and c[6] < 90]
    rec = [c[6] for c in calls if c[3] and c[4] > 0]
    rl.check("回來的列有 ≥ 90% 是母體認得的代號", not poor,
             ("不足 90%：" + "、".join(poor)) if poor
             else f"{len(rec)} 張有列的表，最低 {min(rec, default=100):.1f}%")
    if zero_raw:
        # ⛔ 這一段是**證據**不是摘要：兩邊的鍵擺在一起才判得出是
        #   「鍵對不起來」還是「端點回了另一個市場的表」。
        rl.note("涵蓋 0% 的原始證據（未整理）：\n```\n"
                + json.dumps(zero_raw, ensure_ascii=False, indent=1)[:2500]
                + "\n```")
    rl.check("沒有表因為取不到期別而不寫檔", total["skip"] == 0,
             f"略過 {total['skip']} 張")
    # ⭐⭐ 兩個市場的申報進度不同步時，同一批資料會含兩期。
    #   ⛔ 這**不是錯**（對方本來就可以不同步），⚠ 而它以前的處置是錯的：
    #     取最常見的那一期、把兩期寫進同一個檔 ⇒ 少數那一邊被貼上錯的檔名。
    #   ⇒ 現在是分開寫檔 ⇒ 所以這裡是 `info` 不是 `check`，
    #     ⛔ 但一定要印出來：它會讓「某一期只有單邊市場」看起來像缺資料。
    # ⛔ 自癒搬過的列一定要進 runlog：它會讓某一期的列數**變多或變少**，
    #   ⚠ 而那看起來跟「來源改了」一模一樣。
    if repaired:
        rl.info("⭐ 期別自癒（把寫錯期的舊列搬回它自己那一期）",
                "；".join(f"{k}：{m}" for k, _n, m in repaired))
    rl.check("⛔ 期別自癒沒有因為列數對不上而中止",
             all(n > 0 for _k, n, _m in repaired),
             "；".join(m for _k, n, m in repaired if n < 0) or "（沒有中止）")
    if multi:
        rl.info("⭐ 同一批含多個期別（**已分開寫檔**，⛔ 不是取最常見的）",
                "；".join(f"{k}/{t}：" + "、".join(f"{p}({n} 列)"
                                                  for p, n in g.items())
                          for k, t, g in multi))
    return rl.finish()


def main():
    ap = argparse.ArgumentParser(description="全市場月營收與財報")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--kind", default="all", choices=["all", "revenue", "fs", "bs"])
    ap.add_argument("--sleep", type=float, default=2)
    a = ap.parse_args()
    if a.run:
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
