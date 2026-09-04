# -*- coding: utf-8 -*-
"""transpose.py — 把「按日切」的全市場資料轉成「按股票切」的個股庫。

為什麼要這一支：`data/universe/daily/<日期>.csv` 是一天一檔、每檔約 2,700 列。
要看單一檔股票的歷史就得掃過全部日檔再過濾——實測 2,844 個日檔約 17.6 秒、
**整批 0.55 GB**。分析環境是用完就丟的，每次都要重付一次下載成本。
轉置之後看一檔股票只要抓 `data/stocks/<代號>.csv`，約 230 KB、一個請求。

★ **一律全量重建，不寫增量。**
  實測全量只要 1～3 分鐘，一週跑一次的東西沒必要為了省這幾分鐘去寫增量邏輯。
  增量的 bug 是靜默的：2026-09-04 實測 `capital.py` 的 `cmd_run` 只補「還沒有的」、
  不更新「已經有的」，結果 1,400 多檔從第一次抓到之後就凍住，連程式改了都沒反應。
  **能不寫增量就不寫**，就不需要另外做一套比對去抓它。

★ 這是**衍生檔**，不是第二個真相來源。日檔才是原始資料。
  任何人都不可以直接編輯 `data/stocks/` 底下的檔——手改之後兩邊會無聲飄移。
  要改就改日檔，然後重跑這一支。

★ 含已下市的股票。`rebuild-meta` 做出來的 last_seen 顯示有 256 檔已下市；
  回測若只用今天還活著的那批就是生存者偏差。
"""
import csv, os, sys, argparse, time, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
UNI = os.path.join(ROOT, "data", "universe")
SRC = {"price": os.path.join(UNI, "daily"), "inst": os.path.join(UNI, "inst")}
OUT = {"price": os.path.join(ROOT, "data", "stocks"),
       "inst": os.path.join(ROOT, "data", "stocks_inst")}
# key 是「日期+代號」的複合鍵，轉置後沒有用途；其餘欄位全留。
DROP = {"key"}
CHUNK = 200          # 一次處理幾個日檔再落盤。限制記憶體用量，不影響結果。


def _days(kind):
    d = SRC[kind]
    if not os.path.isdir(d):
        print(f"[transpose] 找不到 {d}", file=sys.stderr)
        return []
    return sorted(n for n in os.listdir(d) if n.endswith(".csv") and n[0].isdigit())


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

    for i in range(0, len(days), CHUNK):
        buf = collections.defaultdict(list)
        for n in days[i:i + CHUNK]:
            with open(os.path.join(SRC[kind], n), encoding="utf-8") as f:
                rd = csv.DictReader(f)
                if rd.fieldnames is None:
                    continue
                if header is None:
                    header = [c for c in rd.fieldnames if c not in DROP]
                for r in rd:
                    code = (r.get("stock_id") or "").strip()
                    if not code:
                        continue
                    buf[code].append([r.get(c, "") for c in header])
                    rows_total += 1
        for code, rows in buf.items():
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
        print(f"  ...{days[min(i + CHUNK, len(days)) - 1][:10]} "
              f"（{min(i + CHUNK, len(days))}/{len(days)} 日檔）", flush=True)

    # 索引：一眼看出哪一檔有多少列、涵蓋到哪
    idx = os.path.join(out_dir, "_index.csv")
    with open(idx, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stock_id", "rows", "first", "last"])
        for code in sorted(stat):
            w.writerow([code, stat[code], span[code][0], span[code][1]])

    el = time.time() - t0
    print(f"[transpose] {kind}：{len(days)} 個日檔 → {len(stat)} 檔個股，"
          f"{rows_total:,} 列，{el:.1f} 秒")
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
