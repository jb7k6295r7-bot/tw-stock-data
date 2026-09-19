#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""odd_lot_share.py — 量「我方日檔的 `volume` 有多少不是 1,000 的倍數」。⛔ 只讀不寫資料。

## ⛔ 為什麼要有這一支（⚠ 它是一個【量法】的守門，不是一份新資料）

2026-09-16~17 同一個量出現過**三個**數字，而三個都寫成「上市日檔 volume 非千倍數的比例」：

    回測線 1547  93.7%（2020-10-26 前 89.3%／後 97.6%）
    資料庫線 1600 95.7%
    資料庫線 1615 94.3%

⇒ 市場情報分析線 0005 §五／0020 §五：**在收斂成一個數字＋一行沿革之前，
  `READ_CONTRACT` 那一行只寫方向（「日檔含零股」），⛔ 不要寫百分比。**

⭐ 而三個都不是算錯——它們是**三個不同的母體**，而沒有人把母體寫出來。
⛔ 而抽樣在這個量上**一律偏高**，理由是結構性的：
  任何「挑長歷史的股票」的抽法都會**少掉權證**，而權證正是非千倍數比例
  最低的一族（22.82%）⇒ ⚠ 抽出來的數字看起來比全庫高，而且**每次抽都不一樣**。

⇒ ⭐ 所以這一支存在的理由不是「再算一次」，是**把那個量變成有現成紀錄可以直接數的東西**
  （CLAUDE.md 七點：要送一個數字給別人做決定之前，先問這個量有沒有現成的紀錄）。

## ⛔ 判準：母體要**逐格**印出來，不是只印一個總數

一個沒有母體的百分比，跟沒有那個數字一樣——⚠ 三個舊數字就是這樣來的。
⇒ 逐市場 × 逐期間 × 逐種類（個股／ETF／權證）× 轉板與否，全部一次印出來。
"""
import csv
import io
import os
import sys
from collections import defaultdict

import runlog

_HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(_HERE, "data", "stocks")
OUT = os.path.join(_HERE, "data", "meta", "_odd_lot_share.txt")

# ⭐ 盤中零股（**上市**）上路日。⛔ 它不是「零股從這天才有」——
#   2020-10-26 之前就有**盤後**零股，而本支量到的 83.89% 就是它。
#   ⇒ 這個日期只是一個**已知的口徑轉折**，拿來當分界看得出前後差多少。
TWSE_INTRADAY_ODD = "2020-10-26"


def shape_of(sid):
    """代號形狀 → `etf`／`warrant`／`stock`。⛔ 沒有預設值以外的猜測。

    ⚠ 這是**代號形狀**，不是官方證券種類欄——⛔ 兩者不是同一個東西
    （CLAUDE.md 七點：名字對得上不代表那是同一個量）。
    ⇒ 它只用在「拆開看比例」這一件事上，⛔ 不要拿去當分類依據。
    """
    if sid.startswith("00"):
        return "etf"
    if len(sid) >= 6 and any(c.isalpha() for c in sid):
        return "warrant"
    return "stock"


def scan(src=None):
    """→ `(cells, n_files, transfer, span)`；`cells[(market, axis, bucket)] = [日數, 非千倍數]`。

    ⛔ 只數 `volume > 0` 的交易日：沒有成交的那一天講不出它是整張還是零股。

    ⭐ `span` ＝ `(最早, 最晚)` 有成交的日期——⛔ 它不是裝飾，是這一批**自己講出
    它量的是哪一段**（CLAUDE.md 第二點）。⚠ 理由很具體：分支上的 `data/` 永遠比
    main 舊（四點六）⇒ 同一支程式在兩個 ref 上跑會給不同的分母，而**兩份輸出檔
    在畫面上一模一樣**。
    """
    src = src or SRC
    cells = defaultdict(lambda: [0, 0])
    transfer = set()
    dmin = dmax = None
    names = sorted(n for n in os.listdir(src) if n.endswith(".csv"))
    for fn in names:
        sid = fn[:-4]
        rows = []
        markets = set()
        with io.open(os.path.join(src, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    vol = int(float(r.get("volume") or 0))
                except (TypeError, ValueError):
                    continue
                if vol <= 0:
                    continue
                mk = r.get("market") or "?"
                markets.add(mk)
                rows.append((r.get("date") or "", mk, vol))
        if len(markets) > 1:
            transfer.add(sid)
        shape = shape_of(sid)
        moved = "transfer" if sid in transfer else "notransfer"
        for date, mk, vol in rows:
            bad = 1 if vol % 1000 else 0
            era = "after" if date >= TWSE_INTRADAY_ODD else "before"
            if date:
                dmin = date if dmin is None or date < dmin else dmin
                dmax = date if dmax is None or date > dmax else dmax
            for key in ((mk, "all", "all"), (mk, "era", era),
                        (mk, "shape", shape), (mk, "moved", moved)):
                cell = cells[key]
                cell[0] += 1
                cell[1] += bad
    return cells, len(names), transfer, (dmin, dmax)


SPAN_MARK = "⭐ 這一份量到的區間：**"


def span_of(txt):
    """從一份既有的輸出檔讀回它量到的**最後一天**；讀不出來回 `None`。

    ⛔ 它不是裝飾功能——它是四點六那道閘門的輸入：
    **分支上的 `data/` 永遠比 main 舊**，而這個檔是**整份覆蓋**的
    ⇒ 在分支上派一趟，就會把 main 上比較新的那一份換成比較舊的，
    ⚠ 而 `git diff` 看起來像「這一趟重算過」。
    """
    for ln in txt.splitlines():
        if ln.startswith(SPAN_MARK):
            tail = ln[len(SPAN_MARK):].split("**")[0]
            hi = tail.split("~")[-1].strip()
            return hi if hi and hi != "—" else None
    return None


def pct(cell):
    return (100.0 * cell[1] / cell[0]) if cell[0] else None


def _line(cells, mk, axis, bucket, label):
    c = cells.get((mk, axis, bucket))
    if not c or not c[0]:
        return f"  {label:24s} —（0 日）"
    return (f"  {label:24s} {c[1]:>9,}／{c[0]:>9,} ＝ {pct(c):6.2f}%")


def report(cells, n_files, transfer, span=(None, None)):
    out = [runlog.probe_stamp("odd_lot_share")]
    out.append("# 我方日檔 `volume` 非 1,000 倍數的比例（⭐ 全庫，⛔ 不是抽樣）\n")
    out.append(f"母體：`data/stocks/` 共 {n_files:,} 檔｜⛔ 只數 `volume > 0` 的交易日")
    lo, hi = span
    out.append(f"{SPAN_MARK}{lo or '—'} ~ {hi or '—'}**"
               "（⛔ 分支上的 `data/` 比 main 舊 ⇒ 換個 ref 跑，分母會不一樣）\n")
    for mk in ("twse", "tpex", "esb"):
        if not cells.get((mk, "all", "all"), [0])[0]:
            continue
        out.append(f"\n## {mk}")
        out.append(_line(cells, mk, "all", "all", "⭐ 全期（這一個是答案）"))
        out.append(_line(cells, mk, "era", "before", f"{TWSE_INTRADAY_ODD} 之前"))
        out.append(_line(cells, mk, "era", "after", f"{TWSE_INTRADAY_ODD} 起"))
        for s, lab in (("stock", "個股"), ("etf", "ETF／ETN（00 開頭）"),
                       ("warrant", "權證（6 碼含英文）")):
            out.append(_line(cells, mk, "shape", s, lab))
        out.append(_line(cells, mk, "moved", "transfer", "轉板過的"))
        out.append(_line(cells, mk, "moved", "notransfer", "沒轉板的"))
    out.append(f"\n轉板（`market` 欄變過）的檔數：{len(transfer)}")
    return "\n".join(out) + "\n"


def main():
    rl = runlog.Run("odd_lot_share")
    if not os.path.isdir(SRC):
        rl.check("`data/stocks/` 在不在", False,
                 f"{SRC} 不在 ⇒ ⛔ 這一趟什麼都沒量到")
        return rl.finish()
    cells, n_files, transfer, span = scan()
    txt = report(cells, n_files, transfer, span)
    # ⭐ 四點六那道閘門：這個檔是**整份覆蓋**的 ⇒ 在分支上跑一趟（分支的 `data/`
    #   永遠比 main 舊）就會把 main 上比較新的那一份換成比較舊的。
    #   ⛔ 判準不是「這一趟成功了沒」，是**這一趟量到的區間有沒有退步**。
    prev = (span_of(io.open(OUT, encoding="utf-8").read())
            if os.path.exists(OUT) else None)
    now_hi = span[1]
    if prev and now_hi and now_hi < prev:
        rl.check("⛔ 不可以拿比較舊的一份蓋掉比較新的", False,
                 f"既有那一份量到 {prev}，而這一趟只量到 {now_hi}"
                 "（⚠ 多半是在分支上跑的）⇒ ⛔ 這一趟**一個字都不寫**")
        return rl.finish()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    # ⭐ 驗終點：寫完**重讀**，斷言讀回來的內容（四點二）。
    back = io.open(OUT, encoding="utf-8").read()
    rl.check("寫出去的那一份讀得回來而且含全庫那一格", "⭐ 全期" in back,
             f"{len(back)} 字元")
    # ⭐ 第二點：這一批要**自己講出它量的是哪一段**。⛔ 斷言的是「寫出去那一份裡
    #   真的有那兩個日期」——⚠ 不是「span 不是 None」（那只證明 scan 算得出來）。
    lo, hi = span
    rl.check("那一份自己講得出它量到哪一段", bool(lo and hi and lo in back and hi in back),
             f"{lo} ~ {hi}")
    for mk in ("twse", "tpex"):
        c = cells.get((mk, "all", "all"))
        if c and c[0]:
            rl.info(f"{mk} 全庫非千倍數", f"{c[1]:,}／{c[0]:,} ＝ {pct(c):.2f}%")
    # ⛔ 不設 check 的那一格：**比例本身沒有「該是多少」**
    #   ⇒ 拿它設門檻就是憑空造一個判準（CLAUDE.md 七點）。
    rl.info("⛔ 這一支不設數值門檻",
            "比例會隨掛牌結構變（權證多寡）⇒ 訂門檻等於憑空造判準。"
            "⭐ 它要回答的是「這個量的母體是什麼」，不是「它有沒有變」。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
