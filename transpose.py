# -*- coding: utf-8 -*-
"""transpose.py — 把「按日切」的全市場資料轉成「按股票切」的個股庫。

為什麼要這一支：`data/universe/daily/<日期>.csv` 是一天一檔、每檔約 2,700 列。
要看單一檔股票的歷史就得掃過全部日檔再過濾——實測 2,844 個日檔約 17.6 秒、
**整批 0.55 GB**。分析環境是用完就丟的，每次都要重付一次下載成本。
轉置之後看一檔股票只要抓 `data/stocks/<代號>.csv`，約 230 KB、一個請求。

★ **四層**（2026-09-07 起）：

| kind | 來源日檔 | 輸出 | 量級 |
|---|---|---|---|
| `price` | `universe/daily` | `data/stocks/` | 約 0.55 GB |
| `inst` | `universe/inst` ＋ `otcinst` | `data/stocks_inst/` | — |
| `margin` | `universe/margin` ＋ `otcmargin` | `data/stocks_margin/` | **約 240 MB** |
| `per` | `universe/per` ＋ `otcper` | `data/stocks_per/` | **約 250 MB** |

⚠ **`margin` 與 `per` 是 2026-09-07 新增的，加進去 repo 大約翻倍**（0.55 GB → 約 1 GB）。
這是使用者攤開成本之後選的：換到的是「一檔的融資／本益比長序列」從
**掃 2,845 個日檔、數百 MB** 變成**一個請求、約 170 KB**。
⚠ **第一次建立這兩層一定要走手動的 `transpose.yml`**（timeout 60 分），
不要讓 `daily.yml` 那 15 分鐘的步驟去扛第一次的 490 MB commit。

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

import runlog

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
SRC = {"price":  [os.path.join(UNI, "daily")],
       "inst":   [os.path.join(UNI, "inst"),   os.path.join(UNI, "otcinst")],
       # ★ 2026-09-07 新增。融資融券與本益比原本**只有日期軸**，
       #   要一檔的長序列得掃 2,845 個日檔、數百 MB——而融資使用率、券資比、
       #   本益比換季斷層都是每天在用的判讀項目。
       #   合併前實測過三件事（不要只看 feeds.py 宣告的 header，要看實際寫出來的檔）：
       #     ① 上市與上櫃的表頭**逐字相同**（margin/otcmargin、per/otcper 各自）
       #     ② 同一天的代號集合**交集 0**（2026-09-04：margin 1,297 vs 920、per 1,081 vs 886）
       #     ③ 兩者都有 `date` 與 `stock_id`
       #   三件都成立才敢合併成同一個輸出目錄。任一條不成立就要分開存。
       "margin": [os.path.join(UNI, "margin"), os.path.join(UNI, "otcmargin")],
       "per":    [os.path.join(UNI, "per"),    os.path.join(UNI, "otcper")]}
OUT = {"price":  os.path.join(ROOT, "data", "stocks"),
       "inst":   os.path.join(ROOT, "data", "stocks_inst"),
       "margin": os.path.join(ROOT, "data", "stocks_margin"),
       "per":    os.path.join(ROOT, "data", "stocks_per")}
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
    # ★ info 是給 runlog 用的**實際值**，不是「有沒有出事」。
    #   每一項都必須是這一趟真的量到的東西，不可以填預設值假裝有量。
    info = {"days": 0, "src_files": 0, "codes": 0, "rows": 0, "written": 0,
            "dup": 0, "prev_codes": None, "src_last": "", "out_last": ""}
    days = _days(kind)
    if not days:
        return 1, info
    info["days"] = len(days)
    info["src_files"] = sum(len(v) for _d, v in days)
    info["src_last"] = days[-1][0]
    out_dir = OUT[kind]
    # ★ 重建前先數一次舊的檔數。全量重建會先清空，清完就再也問不到了——
    #   而「來源目錄整個消失」正好長成「重建成功、只是檔變少了」的樣子
    #   （2026-09-05 `otcinst` 那次就是這個形狀）。**清空前量，才是直接證據。**
    if os.path.isdir(out_dir):
        info["prev_codes"] = len([n for n in os.listdir(out_dir)
                                  if n.endswith(".csv") and n != "_index.csv"])
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
                        return 1, info
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
    info["codes"] = len(stat)
    info["rows"] = rows_total
    info["written"] = sum(stat.values())
    info["dup"] = dup
    info["out_last"] = max((v[1] for v in span.values()), default="")
    if sum(stat.values()) != rows_total:
        print(f"[transpose] ✗ 列數對不起來：讀 {rows_total} 寫 {sum(stat.values())}",
              file=sys.stderr)
        return 1, info
    return 0, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="price",
                    choices=["price", "inst", "margin", "per", "both", "all"],
                    help="both＝price+inst（舊行為，保留不動）；all＝四層全做")
    a = ap.parse_args()
    # ⚠ `both` 的意思**維持原樣**（price+inst），不要偷偷擴成四層——
    #   舊的 workflow 與別人的腳本都還寫著 `--kind both`，
    #   改掉它的意思會讓那些呼叫端在不知情的狀況下多做兩層、多寫 490 MB。
    #   要四層就明寫 `all`。
    kinds = {"both": ["price", "inst"],
             "all": ["price", "inst", "margin", "per"]}.get(a.kind, [a.kind])
    # ★ 2026-09-07：一次跑多層時**要逐層報結果**，不要只把回傳碼 OR 起來。
    #   `--kind all` 有四層，舊寫法只給一個 exit code——
    #   四層裡有一層沒有來源目錄時，另外三層明明成功，讀 log 的人卻只看到「失敗」，
    #   而「哪一層失敗、為什麼」要自己往上翻。**摘要要說現況，不是說有沒有出事。**
    res, info = {}, {}
    for k in kinds:
        res[k], info[k] = build(k)
    if len(kinds) > 1:
        print("\n[transpose] 逐層結果：")
        for k in kinds:
            tag = "ok" if res[k] == 0 else "★ 失敗"
            print(f"        {k:8} {tag}")
    bad = [k for k in kinds if res[k]]
    if bad:
        print(f"[transpose] ✗ 這幾層沒有完成：{'、'.join(bad)}"
              f"（**其餘幾層的輸出仍然是新的，不要整批當成沒跑**）", file=sys.stderr)

    # ★ 寫進 data/meta/_last_run.md 的「transpose」區塊。
    #   四個檢查全部來自實際踩過的坑，而且每一個都拿**直接證據**：
    #     ① 有沒有哪一層沒完成      ← 逐層的回傳碼，不是一個 OR 起來的碼
    #     ② 讀進來幾列 vs 寫出去幾列 ← 兩邊各自數過的數字
    #     ③ 檔數有沒有變少          ← 清空**之前**量到的舊檔數（清完就問不到了）
    #     ④ 最後一天有沒有落後來源  ← 來源日檔的最後一天 vs 索引裡的最後一天。
    #        「每天落後一天而且看不出來」是這條管線最貴的一種壞法。
    rl = runlog.Run("transpose")
    rl.info("這一趟做的層", "、".join(kinds))
    for k in kinds:
        d = info[k]
        rl.info(k, f"{d['days']} 天／{d['src_files']} 個日檔 → "
                   f"{d['codes']} 檔、{d['rows']:,} 列"
                   f"（涵蓋到 {d['out_last'] or '—'}）")
    rl.check("每一層都完成", not bad,
             ("沒完成：" + "、".join(bad)) if bad else f"{len(kinds)} 層全過")
    okrows = all(info[k]["rows"] == info[k]["written"] for k in kinds if res[k] == 0)
    rl.check("讀進來的列數＝寫出去的列數", okrows,
             "；".join(f"{k} 讀 {info[k]['rows']:,} 寫 {info[k]['written']:,}"
                       for k in kinds if res[k] == 0))
    shrank = [k for k in kinds if res[k] == 0 and info[k]["prev_codes"]
              and info[k]["codes"] < info[k]["prev_codes"]]
    rl.check("檔數沒有變少", not shrank,
             "；".join(f"{k} {info[k]['prev_codes']} → {info[k]['codes']}"
                       for k in kinds if res[k] == 0 and info[k]["prev_codes"] is not None)
             or "沒有可比的前一版")
    lag = [k for k in kinds if res[k] == 0 and info[k]["src_last"]
           and info[k]["out_last"] != info[k]["src_last"]]
    rl.check("輸出的最後一天＝來源日檔的最後一天", not lag,
             "；".join(f"{k} 來源 {info[k]['src_last']} / 輸出 {info[k]['out_last'] or '—'}"
                       for k in kinds if res[k] == 0))
    # ⑤ 跨層比對：`price` 的日檔是 fetch.py 每天必寫的，拿它當基準。
    #    某一層的**來源**比 price 舊，代表上游那一步（法人／融資融券／本益比日檔）
    #    當天沒寫進去——2026-09-05 「每天落後一天而且看不出來」就是這個形狀：
    #    轉置本身完全成功，錯的是它讀到的日檔少了一天。
    #    ⚠ 只在同一趟有跑 price 時才驗，否則沒有基準（不可拿舊值當基準）。
    if "price" in kinds and res.get("price") == 0 and len(kinds) > 1:
        base = info["price"]["src_last"]
        behind = [k for k in kinds if k != "price" and res[k] == 0
                  and info[k]["src_last"] and info[k]["src_last"] < base]
        rl.check("各層的來源日檔都跟上 price", not behind,
                 f"price {base}；" + "、".join(
                     f"{k} {info[k]['src_last']}" for k in kinds if k != "price"))
    rc = rl.finish()
    return 1 if (bad or rc) else 0


if __name__ == "__main__":
    sys.exit(main())
