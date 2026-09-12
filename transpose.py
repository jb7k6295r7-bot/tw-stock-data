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
import csv, io, json, os, sys, argparse, time, collections

import runlog

import valid_bar

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


# ══════════════════════════════════════════════════════════════════
# ⭐⭐ 輸入指紋 —— ⛔ 為了讓下游問得出「我讀的這份，是用現在的日檔做的嗎」
#
# ## 這一節的價格：一封寄出去的錯信（2026-09-11）
#
#     09-10 16:25  breakpoint_scan 跑完（_holes_scan.csv）
#     09-10 16:29  transpose 跑完（data/stocks/）
#     09-11 01:22  「甲」回補 2022 全年落地　← ⬇ 三整年的**無成交列**
#     09-11 03:46  「甲」回補 2023 全年落地
#     09-11 05:44  「甲」回補 2024 全年落地
#
# ⇒ 我拿那份**過期的個股庫**算了洞的分類、寄給 K線分析線
#   ⇒ ⛔ 17 段「未解釋」裡 **12 段其實是零成交**（日檔裡整段都有列、
#     而且 100% `price_basis=無成交`）。
#
# ## ⛔⛔ 而當時有一道閘門，它是**綠的**
#
#     ok　⭐ 個股庫跟得上日檔　（日檔到 2026-09-10｜個股庫到 2026-09-10）
#
# ⚠ 它比的是**最後一天**。而這次少掉的是**中間幾萬列**
#   ⇒ 最後一天一模一樣 ⇒ 閘門照樣綠。**CLAUDE.md 四點二那一族。**
#
# ## ⇒ 判準：比**輸入的指紋**，不是比最後一天
#
# 指紋 ＝ 每個來源目錄的（檔數、總位元組、最後一天）。
# ⚠ 用「總位元組」而不是列數：`os.stat` 掃一遍是毫秒級，
#   ⛔ 而數列數要讀 0.5 GB。⭐ 而它一樣抓得到「同一天的檔裡多了幾列」。
# ⚠ git checkout 寫出來的位元組是決定性的 ⇒ 在 Actions 上可比。
# ══════════════════════════════════════════════════════════════════
STAMP = "_built.json"


def source_fingerprint(kind):
    """→ `{"files": n, "bytes": n, "last": "YYYY-MM-DD"}`。⛔ 只 stat，不讀內容。"""
    files = total = 0
    last = ""
    for d in SRC[kind]:
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if not (n.endswith(".csv") and n[0].isdigit()):
                continue
            files += 1
            total += os.stat(os.path.join(d, n)).st_size
            day = n[:-4]
            if day > last:
                last = day
    return {"files": files, "bytes": total, "last": last}


def write_stamp(kind, rows_total, has_valid_bar=False):
    """建完就把指紋寫進 `<輸出目錄>/_built.json`。"""
    p = os.path.join(OUT[kind], STAMP)
    os.makedirs(OUT[kind], exist_ok=True)
    src = source_fingerprint(kind)
    body = {"kind": kind, "rows": rows_total, "src": src}
    # ⭐ 條件二（K線分析線 2026-09-11 裁定）：衍生欄要帶**定義版本**與
    #   **產生它那一趟的輸入指紋**。⛔ 沒有指紋的衍生欄會跟日檔早一趟就不一致，
    #   ⚠ 而它長得跟對的一模一樣。
    if has_valid_bar:
        body[valid_bar.COL] = valid_bar.contract(src)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return body


def stale_vs_source(kind, out_dir=None):
    """→ `(是不是新的, 說明)`。⛔ 讀不到指紋一律回「不是新的」。

    ⚠ 讀不到 ≠ 沒問題：**舊版建的個股庫就是沒有指紋的那一種**，
      ⛔ 而那正是要抓的情形。
    """
    p = os.path.join(out_dir or OUT[kind], STAMP)
    now = source_fingerprint(kind)
    if not os.path.exists(p):
        return False, (f"⛔ 沒有 `{STAMP}` ⇒ **無法證明它是用現在的日檔建的**"
                       f"（現在的來源：{now['files']} 檔／{now['bytes']:,} 位元組"
                       f"／最後一天 {now['last']}）")
    try:
        old = (json.load(io.open(p, encoding="utf-8")) or {}).get("src") or {}
    except (ValueError, OSError) as ex:                       # noqa: BLE001
        return False, f"⛔ `{STAMP}` 讀不動（{type(ex).__name__}）"
    diff = [k for k in ("files", "bytes", "last") if old.get(k) != now.get(k)]
    if diff:
        return False, ("⛔ **輸入在它建好之後變過**："
                       + "、".join(f"{k} {old.get(k)!r} → {now.get(k)!r}"
                                   for k in diff)
                       + "　⇒ ⚠ 只比『最後一天』看不出來（中間多幾萬列也一樣）")
    return True, (f"建好之後輸入沒變過（{now['files']} 檔／"
                  f"{now['bytes']:,} 位元組／最後一天 {now['last']}）")


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


def _header(kind, days):
    """先掃過**每一個來源日檔的第一行**，決定全庫共用的表頭。

    ⭐ 為什麼要先掃一遍：2026-09-09 融資融券補存 `m_prev/m_ret/s_prev/s_ret`，
      新欄接在舊表頭後面 ⇒ 回補進行到一半時，同一個 kind 底下會同時有
      9 欄的舊檔與 13 欄的新檔。⛔ 照舊「不一致就中止」的話，
      個股庫在回補的那幾小時（其實是好幾趟）**整個是壞的**。

    ⛔ 但放行的只有**前綴**這一種：所有檔的表頭排序之後，
      短的必須逐字等於長的前 n 欄。欄序一變、欄名一改就中止——那是真的錯位。
    → (表頭, 說明字串) 或 (None, 錯誤字串)
    """
    seen = {}
    for _d, paths in days:
        for path in paths:
            with open(path, encoding="utf-8") as f:
                line = f.readline()
            cols = tuple(c for c in next(csv.reader([line])) if c not in DROP)
            seen.setdefault(cols, []).append(path)
    if not seen:
        return None, "一個來源檔都沒有"
    ordered = sorted(seen, key=len)
    longest = ordered[-1]
    for c in ordered:
        if longest[:len(c)] != c:
            return None, ("表頭彼此**不是前綴關係**（＝真的錯位，不是加欄）："
                          f"{list(c)}（例：{seen[c][0]}） vs {list(longest)}")
    note = "｜".join(f"{len(c)} 欄 × {len(seen[c])} 檔" for c in ordered)
    return list(longest), note


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
    header, note = _header(kind, days)
    if header is None:
        print(f"[transpose] ✗ {kind} {note}", file=sys.stderr)
        return 1, info
    # ⭐⭐ `valid_bar`：一根 K 棒可不可以拿來算的單一判準（K線分析線 方案乙）。
    #   ⛔ 只在 price 層發——其他層沒有 `price_basis`，發出來會是不可反證的一欄。
    #   ⚠ 而它**接在表頭最後面**：來源日檔的欄位仍然是全庫表頭的前綴
    #     ⇒ 下面那道「本檔是不是前綴」的檢查照樣成立。
    vb_i = None
    if kind == "price":
        okc, vbnote = valid_bar.assert_coexists(header)
        info["valid_bar_note"] = vbnote
        if okc:
            header = header + [valid_bar.COL]
            vb_i = len(header) - 1
        else:
            print(f"[transpose] ⚠ {kind} 不發 `{valid_bar.COL}`：{vbnote}",
                  file=sys.stderr)
    info["header_cols"] = len(header)
    info["header_note"] = note
    if len(set(note.split("｜"))) > 1:
        # ⚠ 混欄數是**回補進行中**的正常狀態，但要講出來：
        #   不講的話「舊檔那幾欄是空的」會被當成「那天的值是 0」。
        print(f"[transpose] ⚠ {kind} 來源檔欄數不一致（{note}）"
              "⇒ 取最長的當表頭，舊檔缺的欄補**空字串**（⛔ 不是 0）")
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
                    # ⛔ 表頭在進迴圈**之前**就算好了（見 `_header()`）。
                    #   這裡只驗「本檔是不是它的前綴」——不再就地改 header：
                    #   ⚠ 就地改會壞掉，而且壞得看不出來：
                    #     ① 前面幾個 chunk 已經用**短表頭**建好列了，
                    #     ② 已經寫出去的個股檔開頭是**短表頭**，
                    #     ⇒ 後面接上長列 ⇒ 同一個 CSV 前後段欄數不同。
                    if header[:len(cols)] != cols:
                        print(f"[transpose] ✗ {path} 欄位不是全庫表頭的前綴"
                              "（＝真的錯位，不是加欄）\n"
                              f"    全庫={header}\n    本檔={cols}", file=sys.stderr)
                        return 1, info
                    for r in rd:
                        code = (r.get("stock_id") or "").strip()
                        if not code:
                            continue
                        row = [r.get(c, "") for c in header]
                        if vb_i is not None:
                            # ⛔ 這一格不是從來源抄的（來源沒有這一欄），
                            #   是**算出來的** ⇒ 一定要蓋掉 `r.get()` 的那個空字串。
                            row[vb_i] = valid_bar.flag(r)
                        buf[code].append(row)
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
    # ⭐ **通過之後才蓋章**：⛔ 失敗的那一趟絕不可以留下「我是新的」這個說法
    #   ——⚠ 那會讓下游把一份壞掉的個股庫當成最新的來用，
    #   比「沒有指紋」更糟（沒有指紋至少會被判成不新）。
    info["stamp"] = write_stamp(kind, rows_total, vb_i is not None)
    return 0, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="price",
                    choices=["price", "inst", "margin", "per", "both", "all"],
                    help="both＝price+inst（舊行為，保留不動）；all＝四層全做")
    # ⛔⛔ 2026-09-10：下面那條「各層的來源日檔都跟上 price」在
    #   **每天 19:00 那一趟一定是紅的**，而那不是缺陷：
    #     台股 13:30 收盤，price 19:00 就有；⚠ 而融資融券／本益比／借券
    #     是**當天晚間才發布**（TWT93U 官方是 20:30 與 22:30 兩次）
    #     ⇒ 19:00 那趟 margin／per 必然停在前一個交易日。
    #   ⚠ 而「每天紅」的代價我們已經寫在 CLAUDE.md 裡：**會被學會忽略**，
    #     然後真的落後兩天那次沒有人看。
    #
    # ⛔ 但「一律容忍一天」會把 2026-09-05 那個洞原封不動打開回去
    #   ——那次的形狀正是「**每天**落後一天，而且看不出來」。
    # ⇒ 容忍度**由呼叫端給**，不由這支猜：
    #     19:00 那一趟   --lag-tolerance 1   （晚間資料還沒發布，容忍一個交易日）
    #     23:59 那一趟   （預設 0）           ⭐ 那一趟必須完全跟上
    #   ⚠ workflow 知道自己是哪一趟，這支不知道 ⇒ ⛔ 不要在這裡讀時鐘猜排程。
    ap.add_argument("--lag-tolerance", type=int, default=0,
                    help="容忍非 price 層落後幾個**交易日**（19:00 那趟填 1）")
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
        # ⭐ 用**交易日**數，⛔ 不是日曆天：連假四天不代表落後四天。
        #   日曆就是 price 的來源目錄本身（⚠ 不另外開一份，那會跟資料不一致）。
        # ⚠ `_days()` 回的是 [(日期, [檔案…])]，⛔ 只取日期那一欄
        cal = [d for d, _ in _days("price")]
        def _lag(d):
            try:
                return cal.index(base) - cal.index(d)
            except ValueError:
                return None          # ⛔ 算不出來就不要猜，交給下面當「未知」
        lags = {k: _lag(info[k]["src_last"]) for k in kinds
                if k != "price" and res[k] == 0 and info[k]["src_last"]}
        behind = [k for k, n in lags.items()
                  if n is None or n > a.lag_tolerance]
        rl.check(f"各層的來源日檔都跟上 price（容忍 {a.lag_tolerance} 個交易日）",
                 not behind,
                 f"price {base}；" + "、".join(
                     f"{k} {info[k]['src_last']}"
                     + (f"（落後 {lags[k]} 個交易日）" if lags.get(k) else "")
                     for k in kinds if k != "price")
                 + ("　⚠ 19:00 那一趟 margin／per 落後一個交易日是正常的"
                    "（晚間才發布）⇒ 那一趟要帶 --lag-tolerance 1"
                    if behind and a.lag_tolerance == 0 else ""))
    # ⑥ ⭐⭐ 衍生欄 `valid_bar`：要**講出它有沒有發、以及是哪一版**。
    #   ⛔ 不講的話，「沒發這一欄」跟「這一欄全是 0」在下游長得一模一樣，
    #   ⚠ 而兩者的意思完全相反（一個是沒資料、一個是那幾天全部無效）。
    if "price" in kinds:
        vbn = info["price"].get("valid_bar_note") or "⛔ 這一趟沒有走到表頭那一步"
        st = (info["price"].get("stamp") or {}).get(valid_bar.COL) or {}
        rl.check(f"⭐ `{valid_bar.COL}` 有發，而且與 `price_basis` **並存**",
                 bool(st.get("version")),
                 f"{vbn}"
                 + (f"｜{st['version']}：{st['rule']}｜用 {st['from']['files']} 檔／"
                    f"{st['from']['bytes']:,} 位元組／最後一天 {st['from']['last']}"
                    " 的日檔算的" if st.get("version") else ""))
    rc = rl.finish()
    return 1 if (bad or rc) else 0


if __name__ == "__main__":
    sys.exit(main())
