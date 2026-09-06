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
import csv
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

CODE_KEYS = ("公司代號", "SecuritiesCompanyCode")
YM_KEYS = ("資料年月",)
Y_KEYS = ("年度", "Year")
Q_KEYS = ("季別", "Season")


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


def period_of(kind, recs):
    """從資料自己的欄位取期別。**不從今天推算。**

    回 (期別字串, 是否一致)。同一批資料裡若出現多個期別，回最常見的那個並回報——
    **不要靜默挑一個**。
    """
    vals = []
    for r in recs:
        if kind == "revenue":
            v = _roc_ym(_pick(r, YM_KEYS))
        else:
            y, q = _roc_y(_pick(r, Y_KEYS)), _pick(r, Q_KEYS)
            v = f"{y}Q{q}" if y and q else ""
        if v:
            vals.append(v)
    if not vals:
        return "", True
    from collections import Counter
    c = Counter(vals)
    top, n = c.most_common(1)[0]
    return top, len(c) == 1


def write_period(kind, tag, period, recs, market_of):
    """寫一期一業別的檔。已存在且內容不同 → 逐欄差異寫進 changes log。"""
    d = os.path.join(OUT_DIR, kind)
    os.makedirs(d, exist_ok=True)
    name = f"{period}.csv" if tag == "all" else f"{period}_{tag}.csv"
    path = os.path.join(d, name)

    # 欄位：以第一筆的鍵為準，再併入後續出現的新鍵（上市上櫃欄名可能不同）
    cols = []
    for r in recs:
        for k in r:
            if k not in cols:
                cols.append(k)
    cols = ["market"] + cols
    rows = []
    for r in recs:
        code = _pick(r, CODE_KEYS)
        rows.append([market_of.get(id(r), "")] + [str(r.get(c, "")).strip() for c in cols[1:]])
    rows.sort(key=lambda x: (x[0], x[1] if len(x) > 1 else ""))

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


def _log_changes(kind, name, old, new):
    def index(txt):
        rd = list(csv.reader(txt.splitlines()))
        if not rd:
            return {}, []
        h = rd[0]
        ic = next((i for i, c in enumerate(h) if c in CODE_KEYS), 1)
        return {r[ic]: r for r in rd[1:] if len(r) > ic}, h
    o, oh = index(old)
    n, nh = index(new)
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    lines = []
    for code in sorted(set(o) | set(n)):
        if code not in o:
            lines.append(f"{ts}\t{kind}/{name}\t{code}\t新增")
        elif code not in n:
            lines.append(f"{ts}\t{kind}/{name}\t{code}\t消失")
        elif o[code] != n[code]:
            diff = [f"{oh[i] if i < len(oh) else i}: {a}→{b}"
                    for i, (a, b) in enumerate(zip(o[code], n[code])) if a != b][:6]
            lines.append(f"{ts}\t{kind}/{name}\t{code}\t{'; '.join(diff)}")
    if lines:
        with open(CHANGES, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  ⚠ {name} 有 {len(lines)} 檔內容變動（**財報更正**），已記入 _changes.log",
              file=sys.stderr)


def listed_codes():
    tw, tp = set(), set()
    if os.path.exists(IND):
        with open(IND, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                (tw if r["market"] == "twse" else tp).add(r["stock_id"])
    return tw, tp


def cmd_run(args):
    B.SLEEP = args.sleep
    tw, tp = listed_codes()
    print(f"[mops] 對照基準：上市 {len(tw):,} 檔、上櫃 {len(tp):,} 檔\n")
    total = {"new": 0, "changed": 0, "unchanged": 0, "skip": 0}
    for kind, srcs in SOURCES.items():
        if args.kind not in ("all", kind):
            continue
        for tag, u_tw, u_tp in srcs:
            recs, market_of = [], {}
            for mk, url, want in (("twse", u_tw, tw), ("tpex", u_tp, tp)):
                d, note = fetch(url)
                time.sleep(B.SLEEP)
                if d is None:
                    print(f"  [{kind}/{tag}/{mk}] 略過：{note[:70]}")
                    continue
                got = {_pick(r, CODE_KEYS) for r in d}
                cov = len(got & want) / len(want) * 100 if want else 0
                print(f"  [{kind}/{tag}/{mk}] {note}｜涵蓋 {cov:.1f}%")
                for r in d:
                    market_of[id(r)] = mk
                recs += d
            if not recs:
                total["skip"] += 1
                continue
            period, uniform = period_of(kind, recs)
            if not period:
                print(f"  [{kind}/{tag}] ✗ 取不到期別，**不寫檔**"
                      f"（不從今天推算）", file=sys.stderr)
                total["skip"] += 1
                continue
            if not uniform:
                print(f"  [{kind}/{tag}] ⚠ 同一批資料含多個期別，取最常見的 {period}",
                      file=sys.stderr)
            st, n = write_period(kind, tag, period, recs, market_of)
            total[st] += 1
            print(f"  [{kind}/{tag}] 期別 {period}｜{n:,} 列｜{st}")
    print(f"\n[mops] 完成：新增 {total['new']}、更新 {total['changed']}、"
          f"無變動 {total['unchanged']}、略過 {total['skip']}")
    print("[mops] ★ 這些端點只給最新一期，**沒有歷史**。回測要等逐期累積。")
    return 0


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
