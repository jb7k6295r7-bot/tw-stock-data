# -*- coding: utf-8 -*-
"""transpose.py — 把「按日切」的全市場資料轉成「按股票切」的個股庫。

為什麼要這一支：`data/universe/daily/<日期>.csv` 是一天一檔、每檔約 2,700 列。
要看單一檔股票的歷史就得掃過全部日檔再過濾——實測 2,844 個日檔約 17.6 秒、
**整批 0.55 GB**。分析環境是用完就丟的，每次都要重付一次下載成本。
轉置之後看一檔股票只要抓 `data/stocks/<代號>.csv`，約 230 KB、一個請求。

★ **一律全量重建，不寫增量。**
  實測全量只要 1～3 分鐘，即使每天跑兩次也划算，沒必要為了省這幾分鐘去養增量邏輯。
  增量的 bug 是靜默的：2026-09-04 實測 `capital.py` 的 `cmd_run` 只補「還沒有的」、
  不更新「已經有的」，結果 1,400 多檔從第一次抓到之後就凍住，連程式改了都沒反應。
  **能不寫增量就不寫**，就不需要另外做一套比對去抓它。

★ 全量重建是**決定性的**：同一批日檔、同樣的排序，產出位元組完全相同。
  所以資料沒變動時 2,300 個檔會被重寫成一模一樣的內容，
  `git diff --staged --quiet` 成立、**根本不會 commit**——只有真的有變動才付成本。
  這就是為什麼併進 `daily.yml` 之後，19:00 與 23:59 兩班都跑也無所謂。
  23:59 那班尤其不能省：它存在的目的就是修正 19:00 抓錯或缺漏的資料
  （被改的列寫在 `data/_changes.log`），不重建的話個股庫會帶著舊值撐到隔天。

★ 執行位置：`daily.yml` 的「抓資料」之後、「Commit 回 repo」之前。
  **不要另開每日排程**——兩支各自 push 同一個 repo，就是 2026-09-04
  白跑兩趟（各 35 分鐘）的那個 git 衝突。`transpose.yml` 只留手動重建用。

★ 這是**衍生檔**，不是第二個真相來源。日檔才是原始資料。
  任何人都不可以直接編輯 `data/stocks/` 底下的檔——手改之後兩邊會無聲飄移。
  要改就改日檔，然後重跑這一支。

★ 含已下市的股票。`rebuild-meta` 做出來的 last_seen 顯示有 256 檔已下市；
  回測若只用今天還活著的那批就是生存者偏差。
"""
import csv, os, sys, argparse, time, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
UNI = os.path.join(ROOT, "data", "universe")
# ★★ 一種 kind 可以有**多個來源目錄**。
#   `inst` 就是這樣：上市走 TWSE T86（`universe/inst`），
#   上櫃走 TPEx（`universe/otcinst`），兩者欄位相同、代號不重疊，
#   合併成同一個 `data/stocks_inst/<代號>.csv` 才符合
#   `docs/READ_CONTRACT.md`「**一檔一條路徑**」的承諾——
#   讀的人不該先知道某檔在上市還上櫃才知道要去哪裡查。
#
#   ⚠ 2026-09-05 踩過：`otcinst` 補完 2,844 天之後跑 transpose，
#   個股庫仍然是 1,515 檔、列數一模一樣——因為這支程式**只讀 `inst`**，
#   剛補的上櫃資料躺在日檔裡沒進去。**加了新的日檔來源就要改這裡。**
SRC = {"price": [os.path.join(UNI, "daily")],
       "inst": [os.path.join(UNI, "inst"), os.path.join(UNI, "otcinst")]}
OUT = {"price": os.path.join(ROOT, "data", "stocks"),
       "inst": os.path.join(ROOT, "data", "stocks_inst")}
# key 是「日期+代號」的複合鍵，轉置後沒有用途；其餘欄位全留。
DROP = {"key"}
CHUNK = 200          # 一次處理幾個日檔再落盤。限制記憶體用量，不影響結果。


def _days(kind):
    """→ [(日期, [檔案路徑, ...])]，依日期升冪。

    ★ 以**日期**為單位，不是以檔案為單位。同一天可能有多個市場的日檔，
      它們必須落在同一個 chunk 裡，否則同一檔股票的列會被切開、
      跨 chunk 之後日期就不再是升冪。
    """
    by_day = {}
    for d in SRC[kind]:
        if not os.path.isdir(d):
            print(f"[transpose] （沒有 {d}，略過）")
            continue
        for n in sorted(os.listdir(d)):
            if n.endswith(".csv") and n[0].isdigit():
                by_day.setdefault(n[:-4], []).append(os.path.join(d, n))
    if not by_day:
        print(f"[transpose] {kind} 找不到任何來源目錄", file=sys.stderr)
    return sorted(by_day.items())


def build(kind):
    days = _days(kind)
    if not days:
        return 1
    out_dir = OUT[kind]
    # 全量重建：先清空，避免留下已經不該存在的檔（例如代號改過）
    if os.path.isdir(out_dir):
        for n in os.listdir(out_dir):
            if n.endswith(".csv"):
                os.remove(os.path.join(out_dir, n))
    os.makedirs(out_dir, exist_ok=True)

    t0 = time.time()
    header = None
    seen = set()                       # 已經寫過表頭的代號
    stat = collections.Counter()
    span = {}                          # code -> [first, last]
    rows_total = 0

    dup = 0
    for i in range(0, len(days), CHUNK):
        buf = collections.defaultdict(list)
        for _day, paths in days[i:i + CHUNK]:
            for path in paths:
                with open(path, encoding="utf-8") as f:
                    rd = csv.DictReader(f)
                    if rd.fieldnames is None:
                        continue
                    cols = [c for c in rd.fieldnames if c not in DROP]
                    if header is None:
                        header = cols
                    elif cols != header:
                        # ★ 多來源合併時，欄位不一致就是災難：同一個 CSV 裡
                        #   前後段的欄意義不同，而且**看不出來**。整支中止。
                        print(f"[transpose] ✗ {path} 欄位與先前不同\n"
                              f"    先前={header}\n    本檔={cols}", file=sys.stderr)
                        return 1
                    for r in rd:
                        code = (r.get("stock_id") or "").strip()
                        if not code:
                            continue
                        buf[code].append([r.get(c, "") for c in header])
                        rows_total += 1
        di = header.index("date")
        for code, rows in buf.items():
            # ★ 同一檔在同一天出現兩次＝兩個市場都收錄了它（轉板當天最可能）。
            #   不擋、照寫，但要數出來——**默默留下重複列，日後算均線會多算一天。**
            ds = [r[di] for r in rows]
            if len(set(ds)) != len(ds):
                dup += len(ds) - len(set(ds))
            rows.sort(key=lambda r: r[di])       # 多來源合併後再排一次，確保升冪
            p = os.path.join(out_dir, f"{code}.csv")
            new = code not in seen
            with open(p, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(header)
                    seen.add(code)
                w.writerows(rows)
            stat[code] += len(rows)
            d0, d1 = rows[0][header.index("date")], rows[-1][header.index("date")]
            if code in span:
                span[code][1] = d1
            else:
                span[code] = [d0, d1]
        j = min(i + CHUNK, len(days))
        print(f"  ...{days[j - 1][0]} （{j}/{len(days)} 天）", flush=True)

    # 索引：一眼看出哪一檔有多少列、涵蓋到哪
    idx = os.path.join(out_dir, "_index.csv")
    with open(idx, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stock_id", "rows", "first", "last"])
        for code in sorted(stat):
            w.writerow([code, stat[code], span[code][0], span[code][1]])

    el = time.time() - t0
    nfiles = sum(len(v) for _k, v in days)
    print(f"[transpose] {kind}：{len(days)} 天 / {nfiles} 個日檔"
          f"（來源 {len([d for d in SRC[kind] if os.path.isdir(d)])} 個目錄）"
          f" → {len(stat)} 檔個股，{rows_total:,} 列，{el:.1f} 秒")
    if dup:
        print(f"[transpose] ⚠ 有 {dup} 列是「同一檔同一天出現兩次」"
              f"（兩個市場都收錄，轉板當天最可能）。已照寫，請確認是否要去重。",
              file=sys.stderr)
    print(f"            輸出 {out_dir}／_index.csv")
    # 一致性自檢：寫出去的列數必須等於讀進來的列數
    if sum(stat.values()) != rows_total:
        print(f"[transpose] ✗ 列數對不起來：讀 {rows_total} 寫 {sum(stat.values())}",
              file=sys.stderr)
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="price", choices=["price", "inst", "both"])
    a = ap.parse_args()
    kinds = ["price", "inst"] if a.kind == "both" else [a.kind]
    rc = 0
    for k in kinds:
        rc |= build(k)
    return rc


if __name__ == "__main__":
    sys.exit(main())
