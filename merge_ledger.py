#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_ledger.py — 累積型 CSV 的**逐鍵合併**（給 `push_data.sh` 用）。

    用法： python3 merge_ledger.py <本趟的檔> <main 上的檔> <主鍵欄,以逗號分隔>
    輸出： 合併結果印到 stdout；⛔ 任何問題一律非 0 結束（呼叫端才知道要退回整檔取代）

## ⛔ 為什麼要有這一支：一次**實際發生**的資料遺失

2026-09-10：

    07:15  一天實測（2026-09-09）推上 main
           ⇒ `_coverage_backfill.csv` 多一列 `2026-09-09,1382,1014,…`
    07:20  2015 那批開跑。它的 checkout 是**分支**，而分支上的 `data/`
           **沒有**那一列（那一列是 `push_data.sh` 推到 main 的，不是推到分支）
    07:22  它 append 自己的列之後，把**整個檔**搬到 main
           ⇒ ⛔ **五分鐘前寫進去的 09-09 那一列被刪掉了**

⚠ 而 `git diff` 看起來完全正常：一加一減，像是「這一趟重算過」。

## ⭐ 這跟 `_last_run.md` 是同一件事，只是它先被想到

`push_data.sh` 早就替 `_last_run.md` 做了**逐區塊**合併，理由一字不差：
「跨 workflow 累積 ⇒ ⛔ 不可以整份取本趟的」。
⛔ 而累積型 **CSV** 一直是整檔覆蓋——同一個道理只做了一半。

## 判準

    ① 兩邊表頭必須逐字相同 ⇒ 不同就非 0 結束（⛔ 不猜怎麼對齊欄位）
    ② 以主鍵取聯集；**同一個鍵兩邊都有 ⇒ 取本趟的**
       （本趟是為了那些鍵才去抓的，它比較新）
    ③ 輸出**照主鍵排序**，讓 diff 讀得出來
    ⚠ ④ 合併後的列數**不可以少於 main 那一份**——少了就代表這支自己在刪東西，
       ⛔ 那正是它要防的事。不符就非 0 結束。
"""
import csv
import io
import sys


def merge(mine_text, main_text, keys):
    """→ (輸出文字, 說明)。⛔ 有問題就丟 ValueError。"""
    def rows(t):
        rd = csv.reader(io.StringIO(t))
        all_ = [r for r in rd if r]
        if not all_:
            return [], []
        return all_[0], all_[1:]

    h1, r1 = rows(mine_text)
    h2, r2 = rows(main_text)
    if not h1:
        raise ValueError("本趟那一份是空的")
    if h2 and h1 != h2:
        raise ValueError(f"表頭不同，不合併：本趟={h1}｜main={h2}")
    idx = []
    for k in keys:
        if k not in h1:
            raise ValueError(f"主鍵欄 `{k}` 不在表頭裡：{h1}")
        idx.append(h1.index(k))

    def key(r):
        return tuple(r[i] if i < len(r) else "" for i in idx)

    merged = {}
    for r in r2:                 # 先放 main 的
        merged[key(r)] = r
    for r in r1:                 # ⭐ 本趟的覆蓋同鍵 —— 它是為了那些鍵才去抓的
        merged[key(r)] = r
    if len(merged) < len(r2):
        raise ValueError(f"合併後 {len(merged)} 列，比 main 的 {len(r2)} 列還少")
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(h1)
    for k in sorted(merged):
        w.writerow(merged[k])
    note = (f"本趟 {len(r1)} 列｜main {len(r2)} 列 ⇒ 合併 {len(merged)} 列"
            f"（新增 {len(merged) - len(r2)}）")
    return out.getvalue(), note


def main():
    if len(sys.argv) != 4:
        print(__doc__.split("\n\n")[1].strip(), file=sys.stderr)
        return 2
    mine, main_, keys = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
    try:
        t1 = io.open(mine, encoding="utf-8").read()
    except OSError as e:
        print(f"[merge_ledger] 讀不到 {mine}：{e}", file=sys.stderr)
        return 2
    try:
        t2 = io.open(main_, encoding="utf-8").read()
    except OSError:
        t2 = ""          # main 上還沒有這個檔 ⇒ 本趟就是全部
    try:
        out, note = merge(t1, t2, keys)
    except ValueError as e:
        print(f"[merge_ledger] ⛔ {e}", file=sys.stderr)
        return 1
    sys.stdout.write(out)
    print(f"[merge_ledger] {note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
