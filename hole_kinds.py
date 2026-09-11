#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hole_kinds.py — 「這個洞**是哪一種**」。⛔ 只讀，不連外，不設門檻。

    python3 hole_kinds.py        # → data/meta/hole_kinds.csv

## ⭐ 它解的是 2026-09-11 發現的一件事：**「洞」不是一種東西**

K線分析線 0210：「洞就是洞，相鄰兩筆日線之間隔了 N 個交易日……
**不需要官方告訴我為什麼**。」

⭐ 前半對，⛔ 後半錯——而且區分**確實不需要官方名單**，只需要一件我方現成的東西：
**看日檔那幾天有沒有那一檔的列。**

```
① halted      那幾天**一列都沒有**，而 `chtm.halted` 覆蓋 ⇒ 真的停止交易
⭐ ② notrade   那幾天**每天都有列**、`price_basis=無成交`、`volume=0`
              ⇒ **市場一直開著、有撮合機制，只是沒有人下單**
③ unexplained 一列都沒有、也沒有停牌紀錄 ⇒ 真正要查的
④ mixed       前段零成交、後段停牌（或反過來）⇒ 一段要拆成兩段
⑤ uncovered   `chtm` 涵蓋不到（上市；或上櫃但超出回補範圍）⇒ ⛔ **判不出來，不是沒有**
```

## ⛔ 為什麼這一條非分開不可：4413 飛寶企業

K線分析線列的最長一筆：`4413 tpex 259 天｜2015-12-24 → 2017-01-17`。

    洞中有列 259 天（無成交 259 天）　停牌 0 天
    chtm 2016-06-01：changed=1 split_auction=1 match_cycle_min=30 **halted=0**

⇒ 它是**全額交割＋30 分鐘分盤撮合、而且一筆都沒成交**，⛔ 不是停止交易。
⚠ 而 K線分析線原本要把「時間不連續」擴進〈硬斷點〉並拿這批當正例集
⇒ ⛔ **會把整整一類「市場開著但沒人買賣」當成斷點。**

⚠ 反過來也要講清楚：②**一樣不能正常判讀**（連 259 天零成交，均線／ATR 全無意義），
⛔ 但它該進的是**流動性閘門**，不是硬斷點——
①少了一段**不存在的時間**（整檔不適用），②時間都在、只是價格沒更新（**那一段**不適用）。

## ⛔ 這一支不裁任何門檻

「幾個交易日算斷」「②要不要擋」是 **K線分析線**的裁定。
⇒ 這裡**每一段洞都分類**，⛔ 不過濾、不設 `min_gap`；下游自己挑。
⚠ runlog 裡印的幾個門檻是**參考**，不是判準。

## ⛔ 洞與區間都不是這一支算的（第四點五）

    洞    `data/meta/_holes_scan.csv`（回測線那支的附表，`breakpoint_check.py` 搬過來）
    停牌  `data/meta/halt_spans.csv`（`halt_spans.py`，而它又 import `margin_universe`）

⇒ 這一支只做「把兩邊對起來、再去日檔確認那幾天到底有沒有列」。
"""
import csv
import io
import os
import sys
from collections import Counter, defaultdict

import runlog
import transpose as _T

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HOLES = os.path.join(_ROOT, "meta", "_holes_scan.csv")
STOCKS_META = os.path.join(_ROOT, "meta", "stocks.csv")
SPANS = os.path.join(_ROOT, "meta", "halt_spans.csv")
PERSTOCK = os.path.join(_ROOT, "stocks")
OUT = os.path.join(_ROOT, "meta", "hole_kinds.csv")
HEADER = ["stock_id", "name", "market", "prev_date", "date",
          "missing_trading_days", "rows_in_hole", "notrade_in_hole",
          "halted_days", "kind"]
# ⚠ 參考門檻，⛔ **不是判準**——只是為了讓 runlog 講得出分佈。
REPORT_GAPS = (5, 20, 60)


def load_spans(path=None):
    """→ {代號: [(起, 迄, 天數)]}　⛔ 檔不在就**大聲失敗**（第四點六鏡像）。"""
    p = path or SPANS
    if not os.path.exists(p):
        return None, (
            f"⛔ 停牌區間表不在這個 ref 上：{p}\n"
            "     ⚠ 這**不是**「沒有人停過牌」，是 checkout 的問題——"
            "那個檔是 `halt_spans.py` 寫的、推到 main。\n"
            "     ⇒ workflow 裡先 `git checkout origin/main -- data/meta/halt_spans.csv`。")
    out = defaultdict(list)
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["stock_id"]].append((r["start"], r["end"], int(r["days"] or 0)))
    if not out:
        return None, f"⛔ 停牌區間表有檔沒列：{p}　⚠ 空殼檔會讓「0 段停牌」變成假結論"
    return out, f"{sum(len(v) for v in out.values()):,} 段／{len(out):,} 檔"


def span_days(spans, code, a, b):
    """洞 (a, b) 之內被停牌區間覆蓋到的天數。⚠ 用重疊判，⛔ 不是包含判。"""
    return sum(n for s, e, n in spans.get(code, []) if s <= b and e >= a)


def rows_in(code, a, b, root=None):
    """→ (洞中有幾列, 其中幾列是『無成交』)。⛔ 讀不到該檔就回 (None, None)。

    ⭐ 這就是分辨 ① 與 ② 的全部——⛔ 不需要任何官方名單。
    ⚠ 而「有列」必須排除兩端那兩天（它們是洞的邊界，本來就有成交）。
    """
    p = os.path.join(root or PERSTOCK, f"{code}.csv")
    if not os.path.exists(p):
        return None, None
    n = nt = 0
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            if a < d < b:
                n += 1
                if (r.get("price_basis") or "").strip() == "無成交":
                    nt += 1
    return n, nt


def classify(gap, rows, notrade, halted, covered):
    """→ kind。⛔ 這裡**沒有**任何可調門檻是判準，0.9 只是「幾乎整段」。

    ⚠ 順序有意義，⛔ 但不是我第一版寫的理由（那句是錯的，突變驗當場打掉）：
    4415 台原藥「洞中 1 列、停牌 155 天」**兩種順序都判 halted**（155/156 也過 0.9）。
    ⭐ 真正會分岔的是**兩邊都成立**的那種：每天都有列（無成交）**而且**停牌覆蓋整段
    ——那是兩個來源互相矛盾。⇒ 這時以**直接證據**為準：
    日檔那幾天真的有列 ⇒ 市場開著 ⇒ `notrade`，
    ⛔ 不採信公告表，因為公告表說的是「應該怎樣」，日檔說的是「實際怎樣」。
    """
    if not gap:
        return "unknown"
    if rows is None:
        return "no_perstock"                      # ⛔ 讀不到該檔 ≠ 那幾天沒有列
    if rows / gap >= 0.9 and notrade >= rows * 0.9:
        return "notrade"
    if halted / gap >= 0.9:
        return "halted"
    if rows or halted:
        return "mixed"
    return "unexplained" if covered else "uncovered"


def covered_by(spans_days, market, end_day):
    """`chtm` 是**上櫃**的表，而且回補有進度前緣 ⇒ 判不判得出來要先問這個。"""
    return market == "tpex" and bool(spans_days) and end_day <= spans_days


def _holes_fp():
    """洞掃描表的指紋。⛔ 它不是這一支產的（回測線那支的附表）⇒ 蓋不了章，
    ⭐ 只能把**內容的短雜湊與列數**印出來，讓引用數字的人指認得出是哪一版。
    ⚠ 用內容雜湊，⛔ 不是 mtime——git checkout 出來的 mtime 是 checkout 當下。
    """
    import hashlib
    raw = io.open(HOLES, "rb").read()
    return (f"{{'sha1': '{hashlib.sha1(raw).hexdigest()[:12]}', "
            f"'rows': {max(0, raw.count(chr(10).encode()[0]) - 1)}}}")


def main():
    ap_cov = None
    rl = runlog.Run("hole_kinds")
    # ══════════════════════════════════════════════════════════
    # ⭐⭐ 輸入指紋 —— ⛔ 這一節的價格是一封寄出去的錯信（2026-09-11）
    #
    # 「甲」把 2022~2024 三整年的**無成交列**補進日檔之後，個股庫還沒重建，
    # ⇒ 我拿那份算了洞的分類寄給 K線分析線
    # ⇒ ⛔ 17 段「未解釋」裡 **12 段其實是零成交**（日檔裡整段都有列）。
    #
    # ⚠ 而當時 `adj_gap` 那道「個股庫跟得上日檔」**是綠的**——它比**最後一天**，
    #   而少掉的是**中間幾萬列**。
    #
    # ⇒ 兩件：① 個股庫不是用現在這份日檔建的 ⇒ **這一趟的分類不可信**，要大聲說
    #        ② 把指紋印進 runlog ⇒ ⭐ 讀的人自己看得出來這批數字用的是哪一份輸入
    #          （我已經答應 K線分析線每次附上）
    # ══════════════════════════════════════════════════════════
    _fresh, _why = _T.stale_vs_source("price", PERSTOCK)
    rl.check("⭐⭐ 個股庫是用**現在這份**日檔建的"
             "（⛔ 不是只比最後一天——那道在 2026-09-11 是綠的，而中間少了幾萬列）",
             _fresh, _why + ("　⇒ ⛔ **這一趟的分類不可信**：`rows_in_hole` 會少算，"
                             "⚠ 而少算的方向是把 `notrade` 說成 `unexplained`"
                             if not _fresh else ""))
    rl.info("⭐ 這一批數字的輸入指紋（⛔ 引用數字時請一起帶上）",
            f"日檔 {_T.source_fingerprint('price')}"
            + (f"｜洞掃描表 {_holes_fp()}" if os.path.exists(HOLES) else
               "｜⛔ 洞掃描表不在"))
    rl.info("⛔ 這一支只讀不連外、不設門檻",
            "只回答「這個洞是哪一種」，⛔ 「算不算斷點」是 K線分析線的裁定")
    spans, note = load_spans()
    rl.check("⭐ 停牌區間表讀得到而且有內容"
             "（⛔ 讀不到 ≠ 沒人停過牌，見說明）", spans is not None, note)
    if spans is None:
        return rl.finish()
    rl.info("停牌區間表", note)
    # ⭐ `chtm` 補到哪一天：區間表裡最大的 end ⇒ 之後的洞一律「判不出來」
    ap_cov = max((e for v in spans.values() for _s, e, _n in v), default="")
    rl.info("⚠ 停牌資料的涵蓋上限", f"{ap_cov}"
            "　⇒ ⛔ 這之後的洞一律標 `uncovered`（判不出來），不是 `unexplained`")

    if not os.path.exists(HOLES):
        rl.check("洞掃描表讀得到", False, f"⛔ {HOLES} 不在")
        return rl.finish()
    meta = {}
    if os.path.exists(STOCKS_META):
        with io.open(STOCKS_META, encoding="utf-8") as f:
            meta = {r["stock_id"]: r for r in csv.DictReader(f)}

    rows_out, kinds = [], Counter()
    with io.open(HOLES, encoding="utf-8") as f:
        holes = list(csv.DictReader(f))
    for h in holes:
        c, a, b = h["stock_id"], h["prev_date"], h["date"]
        gap = int(float(h.get("missing_trading_days") or 0))
        mk = h.get("market", "")
        n, nt = rows_in(c, a, b)
        hd = span_days(spans, c, a, b)
        k = classify(gap, n, nt, hd, covered_by(ap_cov, mk, b))
        kinds[k] += 1
        rows_out.append([c, (meta.get(c) or {}).get("name", ""), mk, a, b,
                         str(gap), "" if n is None else str(n),
                         "" if nt is None else str(nt), str(hd), k])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(sorted(rows_out, key=lambda r: (r[0], r[3])))
    # ⭐ 寫完**重讀**再斷言（第四點二：不要斷言「寫檔成功」）
    with io.open(OUT, encoding="utf-8") as f:
        back = list(csv.DictReader(f))
    rl.check("⭐ 寫出去的檔**重讀回來**列數一致", len(back) == len(rows_out),
             f"寫 {len(rows_out):,}／讀回 {len(back):,}")

    rl.info("全部的洞", f"{len(rows_out):,} 段｜" +
            "、".join(f"{k} {v:,}" for k, v in kinds.most_common()))
    # ⭐ 第七點：報「某群 0 筆」要附該判準在該群抓到的正例數
    rl.check("⭐ `notrade` 這一類抓得到（⛔ 0 的話代表判準壞了，"
             "⚠ 而它壞掉的表現是「每個洞看起來都是斷點」）",
             kinds.get("notrade", 0) > 0,
             f"notrade {kinds.get('notrade', 0):,}｜halted {kinds.get('halted', 0):,}"
             f"（⇒ 兩類都不是 0 才證明分得開）")
    rl.check("⭐ `halted` 這一類也抓得到（⚠ 正例，⛔ 一個只會回 notrade 的分類器沒有用）",
             kinds.get("halted", 0) > 0, f"halted {kinds.get('halted', 0):,}")
    for g in REPORT_GAPS:
        sub = Counter(r[9] for r in rows_out if int(r[5]) >= g)
        rl.info(f"　⚠ 參考：缺 ≥{g} 個交易日的（⛔ 這不是判準，門檻歸 K線分析線）",
                f"{sum(sub.values()):,} 段｜" +
                "、".join(f"{k} {v:,}" for k, v in sub.most_common()))
    rl.info("⇒ 讀法",
            "`kind=notrade` ⇒ **市場一直開著**，那幾天有列、`price_basis=無成交`"
            "｜`halted` ⇒ 真的停止交易｜`uncovered` ⇒ ⛔ **判不出來**，不是沒有")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
