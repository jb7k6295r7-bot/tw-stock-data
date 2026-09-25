#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_ledger.py — 累積型 CSV 的**逐鍵合併**（給 `push_data.sh` 用）。

    用法： python3 merge_ledger.py <本趟的檔> <main 上的檔> <主鍵欄,以逗號分隔> [<移除清單>]
           python3 merge_ledger.py <本趟的檔> <main 上的檔> json     ← ⭐ JSON 字典台帳
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
    ⭐ ⑤（2026-09-25）**明確的移除清單**：聯集的代價是「錯的列永遠刪不掉」
       （實例：delisted.csv 早年誤收 72 筆轉上市，程式修好了、推上 main 又被併回來）
       ⇒ 呼叫端可以給一份 CSV（表頭至少含主鍵欄），列在裡面的鍵【合併後移除】
       ⛔ 只移除清單上逐字列出的鍵；④ 那道檢查照舊，只扣掉 main 裡【真的被清單點名】的列數
       ⛔ 清單是空的、或表頭缺主鍵欄 ⇒ 非 0 結束（⛔ 不猜）
"""
import csv
import io
import json
import sys


def merge(mine_text, main_text, keys, remove_text=None):
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
    removed = 0
    if remove_text is not None:
        hr, rr = rows(remove_text)
        if not hr or not rr:
            raise ValueError("移除清單是空的（⛔ 不猜：沒有要移除就不要給清單）")
        miss = [k for k in keys if k not in hr]
        if miss:
            raise ValueError(f"移除清單缺主鍵欄 {miss}：{hr}")
        ridx = [hr.index(k) for k in keys]
        rm = {tuple(r[i] if i < len(r) else "" for i in ridx) for r in rr}
        main_keys = {key(r) for r in r2}
        removed = len(rm & main_keys)
        for k in rm:
            merged.pop(k, None)
    if len(merged) < len(r2) - removed:
        raise ValueError(f"合併後 {len(merged)} 列，比 main 的 {len(r2)} 列（扣掉清單點名的 {removed}）還少")
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(h1)
    for k in sorted(merged):
        w.writerow(merged[k])
    note = (f"本趟 {len(r1)} 列｜main {len(r2)} 列 ⇒ 合併 {len(merged)} 列"
            f"（新增 {len(merged) - len(r2) + removed}）"
            + (f"｜⭐ 依移除清單刪掉 main 的 {removed} 列" if removed else ""))
    return out.getvalue(), note


def merge_json(mine_text, main_text):
    """JSON **字典**台帳的逐鍵合併 → (輸出文字, 說明)。⛔ 有問題就丟 ValueError。

    ## ⛔ 為什麼要有這一條（2026-09-12）

    上面那一段講的是累積型 **CSV**，⚠ 而 `feeds` 的台帳是 **JSON**：

        data/universe/<feed>/_fetched.json   逐月型：哪幾個月問過了
        data/universe/<feed>/_asked.json     ⭐ 逐日型：哪幾天問到了但沒資料

    ⛔ 它們一直走「整檔取本趟的」那條路 ⇒ **同一個道理又只做了一半**
      （CLAUDE.md 四點六那一節已經數到第三個位置，這是第四、第五個）。
    ⚠ 而它壞掉的樣子最難看見：分支上的 `_fetched.json` 少了 main 的幾個月
      ⇒ 那幾個月被當成「沒問過」⇒ 下一趟重問 ⇒ **看起來只是多花幾分鐘**，
      ⛔ 直到 `--limit` 分批補的那種跑法永遠補不完為止。

    判準跟 CSV 那條一字不差：**本趟的鍵覆蓋、其餘原封不動，
    ⚠ 而合併後的鍵數不可以少於 main 那一份。**
    """
    def load(t, who):
        if not t.strip():
            return {}
        try:
            v = json.loads(t)
        except ValueError as e:
            raise ValueError(f"{who} 不是合法 JSON：{e}")
        if not isinstance(v, dict):
            raise ValueError(f"{who} 的頂層不是字典，是 {type(v).__name__}")
        return v

    d1 = load(mine_text, "本趟那一份")
    d2 = load(main_text, "main 那一份")
    if not d1:
        raise ValueError("本趟那一份是空的")
    merged = dict(d2)
    merged.update(d1)              # ⭐ 本趟的覆蓋同鍵
    if len(merged) < len(d2):
        raise ValueError(f"合併後 {len(merged)} 鍵，比 main 的 {len(d2)} 鍵還少")
    out = json.dumps(merged, ensure_ascii=False, indent=0, sort_keys=True)
    note = (f"本趟 {len(d1)} 鍵｜main {len(d2)} 鍵 ⇒ 合併 {len(merged)} 鍵"
            f"（新增 {len(merged) - len(d2)}）")
    return out, note


def main():
    if len(sys.argv) not in (4, 5):
        print(__doc__.split("\n\n")[1].strip(), file=sys.stderr)
        return 2
    mine, main_, keys = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
    rm_text = None
    if len(sys.argv) == 5:
        try:
            rm_text = io.open(sys.argv[4], encoding="utf-8").read()
        except OSError as e:
            print(f"[merge_ledger] ⛔ 讀不到移除清單 {sys.argv[4]}：{e}", file=sys.stderr)
            return 1
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
        if keys == ["json"] and rm_text is not None:
            raise ValueError("JSON 台帳不支援移除清單")
        out, note = (merge_json(t1, t2) if keys == ["json"]
                     else merge(t1, t2, keys, rm_text))
    except ValueError as e:
        print(f"[merge_ledger] ⛔ {e}", file=sys.stderr)
        return 1
    sys.stdout.write(out)
    print(f"[merge_ledger] {note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
