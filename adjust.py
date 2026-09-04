#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adjust.py — 由除權息事件算出**還原因子**。

## 為什麼存因子不存還原價

存還原後的價格，等於把 `data/stocks/` 的 0.55 GB 再複製一份，
而且**每多一次除權息就要把該檔整段歷史重寫一遍**（還原是往前回推的）。
存因子只有幾百 KB，且downstream 只要乘一下。
更重要的是：**公式改了不必重抓，重算即可。**

## 定義（後復權，back-adjustment）

- 單次事件因子 `f = 除權息參考價 ÷ 除權息前收盤價`
  - 純現金股利：`f < 1`
  - 純股票股利／分割：`f < 1`（參考價會除以配股倍數）
- 某日的累積因子 `F(d) = 所有除權息日 **嚴格大於** d 的事件因子連乘`
- **還原價 = 原始價 × F(d)**

### ★ 差一天就整段錯：因子適用「該列日期之前」，不含當日

除權息當日的收盤價**本身已經是除權後的價格**，再乘一次因子等於重複扣。
`cum_factor` 欄的意思是：**要把「這一列的日期之前」的價格還原，要乘這個數。**

查法（照抄，不要自己推）：

```python
# rows 由 data/adj/<code>.csv 讀進來，已按日期升冪
def factor_at(rows, d):
    for r in rows:                 # 找第一個「除權息日 > d」的事件
        if r["date"] > d:
            return float(r["cum_factor"])
    return 1.0                     # 最後一次事件之後 → 現價不動
```

worked example（3661，兩次除息 2025-08-01 f=0.9750、2026-09-03 f=0.9922）：

| 查詢日 | 命中哪一列 | F | 說明 |
|---|---|---|---|
| 2025-07-31 | 2025-08-01 | **0.96744** | 兩次都還沒發生 → 兩個因子連乘 |
| 2025-08-01 | 2026-09-03 | **0.99225** | 當日已除息，只需還原後面那一次 |
| 2026-09-03 | 無 | **1.0** | 最新，不動 |

**2025-08-01 那天用 0.96744 是錯的**——它會把已經扣過的股利再扣一次。

**最新價的 F = 1**，也就是**現價不動**。這是刻意的：
報告上寫的價位要跟看盤軟體對得起來，被還原過的現價會讓人對不上。
被調整的是**歷史**，所以長期報酬率才不會被除息吃掉。

## 三件不做的事

1. **不還原成交量。** 配股會讓股數變多、量自然放大，
   但配息不會。要精準就得分辨權與息，而 TWT49U 的「權/息」欄
   在同時配股又配息時是混合的。**沒把握就不動**，量一律維持原始值。
2. **不推估缺漏的事件。** 沒有事件檔的日期就是沒有事件，
   不用「股價當天跳空所以應該有除息」去補——那是把結論當資料。
3. **上櫃目前不還原。** TWT49U 只涵蓋上市；上櫃事件在 `otcexright` feed，
   端點尚未驗證。**`_index.csv` 會標明每一檔的來源市場**，
   不可把「沒有因子」讀成「沒有除權息」。
"""

import argparse
import os
import sys
from collections import defaultdict

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
UNI_DIR = os.path.join(_ROOT, "universe")
STOCK_DIR = os.path.join(_ROOT, "stocks")
META_DIR = os.path.join(_ROOT, "meta")
ADJ_DIR = os.path.join(_ROOT, "adj")

EVENT_DIRS = [("twse", os.path.join(UNI_DIR, "exright")),
              ("tpex", os.path.join(UNI_DIR, "otcexright"))]
DAILY_DIR = os.path.join(UNI_DIR, "daily")


def trading_days():
    """全市場交易日曆＝`data/universe/daily/` 的檔名集合。

    ★ 為什麼需要它：核對「除權息前收盤價」要拿**前一個交易日**的收盤來比。
      但冷門股在那一天可能**根本沒有成交**，序列裡就沒有那一列。
      沒有日曆時只能退而取「前一個有資料的日子」——那可能是一個半月前，
      於是價格當然對不上，**被報成「對不上」，其實是「無法核對」**。
      實測 2026-09-04：6 筆「不符」全部是這個原因，真正的不符是 0 筆。
      把兩者混在一起，真的錯誤就會被雜訊蓋掉。
    """
    if not os.path.isdir(DAILY_DIR):
        return []
    return sorted(n[:-4] for n in os.listdir(DAILY_DIR) if n.endswith(".csv"))

ADJ_HEADER = ["date", "factor", "cum_factor", "pre_close", "ref_price", "kind"]
IDX_HEADER = ["stock_id", "market", "events", "date_min", "date_max",
              "cum_factor_first", "checked", "mismatch"]


def _f(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def read_events():
    """→ {code: [(date, factor, pre, ref, kind, market)]}，日期升冪。"""
    ev = defaultdict(list)
    up = 0                      # 參考價高於前收盤（現金增資認股價 > 市價）的筆數
    for market, d in EVENT_DIRS:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".csv"):
                continue
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                head = fh.readline().rstrip("\n").split(",")
                try:
                    i_d = head.index("date"); i_c = head.index("stock_id")
                    i_p = head.index("pre_close"); i_r = head.index("ref_price")
                    i_k = head.index("kind"); i_v = head.index("value")
                except ValueError:
                    print(f"[adj] {name} 欄位不符，跳過：{head}", file=sys.stderr)
                    continue
                for ln in fh:
                    q = ln.rstrip("\n").split(",")
                    if len(q) <= max(i_d, i_c, i_p, i_r, i_k):
                        continue
                    pre, ref = _f(q[i_p]), _f(q[i_r])
                    if not pre or not ref or pre <= 0 or ref <= 0:
                        continue
                    f = ref / pre
                    val = _f(q[i_v]) if i_v < len(q) else None

                    # ★★ 2026-09-04 修正：原本寫死 `f <= 1.0001`，理由是
                    #   「除權息不會讓參考價高於前收盤」——**那個假設是錯的**。
                    #   實例：3312 弘憶股 2016-04-14，前收 5.88 → 參考 5.89（f=1.0017），
                    #   `權值+息值` 是 **−0.018676**（負值）。
                    #   成因是**現金增資的認股價高於市價**，理論除權參考價因此上調。
                    #   少見但合法（240 個交易日抽樣的 1,144 筆裡有 1 筆，約 0.09%）。
                    #
                    #   所以判準改成兩層：
                    #   ① 明顯壞掉的（f ≤ 0.05 或 f > 1.5）一律丟棄
                    #   ② f > 1 但「權值+息值」是負的 → **合理，收下**
                    #   ③ f > 1 而權值是正的 → 方向矛盾，丟棄並回報
                    if not (0.05 < f <= 1.5):
                        print(f"[adj] 因子超出合理範圍，丟棄：{q[i_c]} {q[i_d]} "
                              f"前收={pre} 參考={ref} f={f:.4f}", file=sys.stderr)
                        continue
                    if f > 1.0001:
                        if val is not None and val < 0:
                            up += 1          # 合理的上調，計數但不吵
                        else:
                            print(f"[adj] 參考價高於前收盤但權值非負，方向矛盾，丟棄："
                                  f"{q[i_c]} {q[i_d]} 前收={pre} 參考={ref} "
                                  f"f={f:.4f} 權值+息值={val}", file=sys.stderr)
                            continue
                    ev[q[i_c]].append((q[i_d], f, pre, ref, q[i_k], market))
    for c in ev:
        ev[c].sort()
    if up:
        print(f"[adj] 其中 {up} 筆的參考價高於前收盤（權值為負＝現金增資認股價高於市價），"
              f"已照實收下，不是錯誤")
    return ev


def read_close(code):
    """→ {date: close}。用 `data/stocks/<code>.csv`。"""
    p = os.path.join(STOCK_DIR, f"{code}.csv")
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p, encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split(",")
        try:
            i_d = head.index("date"); i_c = head.index("close")
        except ValueError:
            return {}
        for ln in fh:
            q = ln.rstrip("\n").split(",")
            if len(q) > max(i_d, i_c):
                v = _f(q[i_c])
                if v is not None:
                    out[q[i_d]] = v
    return out


def build(code, rows, cal, verify=True):
    """→ (lines, checked, mismatch)。

    `cum_factor` 適用於**該列日期之前**（不含當日）的價格。
    除權息當日的收盤已經是除權後的價，再乘一次就重複扣——
    查法見檔頭的 `factor_at()`，照抄不要自己推。
    最後一次事件之後沒有列，查不到就是 1.0，所以現價不動。
    """
    closes = read_close(code) if verify else {}

    checked = mismatch = skipped = 0
    if closes:
        for (d, f, pre, ref, kind, mk) in rows:
            # 除權息前收盤價應該等於**前一個交易日**的收盤。
            # ★ 「前一個交易日」由日曆決定，**不是「前一個有資料的日子」**。
            #   冷門股那天可能無成交，序列裡沒有那一列——那是無法核對，
            #   不是對不上。退而取更早的收盤去比，只會製造假警報。
            prev = None
            for x in reversed(cal):
                if x < d:
                    prev = x
                    break
            if prev is None:
                continue
            if prev not in closes:
                skipped += 1          # 前一交易日該檔無成交 → 無法核對
                continue
            checked += 1
            if abs(closes[prev] - pre) > max(0.02, pre * 0.005):
                mismatch += 1
                print(f"[adj] 前收盤對不上：{code} 除權息日={d} "
                      f"官方前收={pre} 我方 {prev} 收盤={closes[prev]}", file=sys.stderr)

    # 累積因子由後往前連乘
    lines, cum = [], 1.0
    for (d, f, pre, ref, kind, mk) in reversed(rows):
        cum *= f
        lines.append([d, f"{f:.8f}", f"{cum:.8f}", f"{pre:g}", f"{ref:g}", kind])
    lines.reverse()
    return lines, checked, mismatch, skipped


def main():
    ap = argparse.ArgumentParser(description="由除權息事件算還原因子")
    ap.add_argument("--verify", action="store_true", default=True,
                    help="與 data/stocks 的前一交易日收盤交叉核對（預設開）")
    ap.add_argument("--no-verify", dest="verify", action="store_false")
    ap.add_argument("--codes", default="", help="只做這幾檔，逗號分隔（試跑用）")
    a = ap.parse_args()

    ev = read_events()
    if not ev:
        print("[adj] 找不到任何除權息事件——先跑 feeds.py --run --feed exright",
              file=sys.stderr)
        return 1
    want = {c.strip() for c in a.codes.split(",") if c.strip()}
    codes = sorted(c for c in ev if not want or c in want)

    os.makedirs(ADJ_DIR, exist_ok=True)
    cal = trading_days()
    if a.verify and not cal:
        print("[adj] 找不到 data/universe/daily/，無法取得交易日曆——"
              "**核對會退化成「拿前一個有資料的日子比」並產生假警報**，"
              "本次改為不核對。", file=sys.stderr)
    idx, tot_ev, tot_chk, tot_mis, tot_skip, no_price = [], 0, 0, 0, 0, 0
    for code in codes:
        rows = ev[code]
        lines, chk, mis, skp = build(code, rows, cal, a.verify and bool(cal))
        if not lines:
            continue
        with open(os.path.join(ADJ_DIR, f"{code}.csv"), "w", encoding="utf-8") as fh:
            fh.write(",".join(ADJ_HEADER) + "\n")
            for r in lines:
                fh.write(",".join(r) + "\n")
        if a.verify and chk == 0 and skp == 0:
            no_price += 1
        idx.append([code, rows[0][5], str(len(lines)), lines[0][0], lines[-1][0],
                    lines[0][2], str(chk), str(mis)])
        tot_ev += len(lines); tot_chk += chk; tot_mis += mis; tot_skip += skp

    with open(os.path.join(ADJ_DIR, "_index.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(IDX_HEADER) + "\n")
        for r in idx:
            fh.write(",".join(r) + "\n")

    print(f"[adj] {len(idx)} 檔、{tot_ev} 個事件")
    if a.verify:
        rate = (tot_mis / tot_chk * 100) if tot_chk else 0.0
        print(f"[adj] 前收盤交叉核對：查了 {tot_chk} 個事件、對不上 {tot_mis} 個（{rate:.3f}%）")
        if tot_skip:
            print(f"[adj] 另有 {tot_skip} 個事件**無法核對**：前一交易日該檔無成交，"
                  f"序列裡沒有那一列。這不是不符，不要算進去。")
        if no_price:
            print(f"[adj] 另有 {no_price} 檔在 data/stocks 查無價格")
        # ★ 不設「自動通過」門檻。對不上就是要有人看，不是四捨五入掉。
        if tot_mis:
            print("[adj] ↑ 上面每一筆都印出來了，逐筆看過再決定要不要用", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
