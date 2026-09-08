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
    tw, tp = listed_codes()
    print(f"[mops] 對照基準：上市 {len(tw):,} 檔、上櫃 {len(tp):,} 檔\n")
    total = {"new": 0, "changed": 0, "unchanged": 0, "skip": 0}
    # ★ 逐「表×市場」記下實際結果。**不要只留一個總數**——
    #   22 個請求裡少收一個，總數看起來還是很像正常的一天
    #   （限流回 307、端點改名，兩種都不會讓程式失敗）。
    calls = []          # (kind, tag, market, 有沒有回應, 列數, 涵蓋率)
    for kind, srcs in SOURCES.items():
        if args.kind not in ("all", kind):
            continue
        for tag, u_tw, u_tp in srcs:
            recs, market_of = [], {}
            for mk, url, want in (("twse", u_tw, tw), ("tpex", u_tp, tp)):
                d, note = fetch(url)
                time.sleep(B.SLEEP)
                if d is None:
                    calls.append((kind, tag, mk, False, 0, 0.0))
                    print(f"  [{kind}/{tag}/{mk}] 略過：{note[:70]}")
                    continue
                got = {_pick(r, CODE_KEYS) for r in d}
                cov = len(got & want) / len(want) * 100 if want else 0
                calls.append((kind, tag, mk, True, len(d), cov))
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
             ("沒回應：" + "、".join(dead)) if dead else f"{len(calls)} 個全有")
    zero = [f"{c[0]}/{c[1]}/{c[2]}" for c in calls if c[3] and c[5] == 0]
    rl.check("有回應的都對得上我方母體（涵蓋 > 0%）", not zero,
             ("涵蓋 0%：" + "、".join(zero)) if zero
             else (f"最低 {min((c[5] for c in calls if c[3]), default=0):.1f}%"))
    rl.check("沒有表因為取不到期別而不寫檔", total["skip"] == 0,
             f"略過 {total['skip']} 張")
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
