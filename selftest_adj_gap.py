#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 `adj_gap.main()`，⛔ 重點在**那條斷言真的會紅**。

這一支的斷言是「未歸因的筆數沒有比上一趟多」。
⛔ 一條永遠綠的斷言是裝飾，而這一條特別容易變成裝飾——
因為它比的是**自己上一趟寫的檔**，只要寫檔與比對的順序寫反，它就永遠相等。

⇒ 所以這裡直接**偽造一個「上一趟只有 1 筆未歸因」的舊檔**，
  再跑一次真的掃描（現在是 80 筆）⇒ 斷言必須紅。
"""
import io, os, shutil, sys, tempfile, csv
import runlog as _RL
import adj_gap as G

FAIL = []


def ck(n, c, note=""):
    print(("  ok   " if c else "  ✗    ") + n + (f"　（{note}）" if note else ""))
    if not c:
        FAIL.append(n)


# ⛔⛔ 2026-09-10：這支「離線」自測**跑了 4 次全庫掃描**（2,212 個 `data/adj/` 檔
#   ＋ 全部 `data/stocks/`）——本機 75 秒，Actions 上超過 11 分鐘。
#   ⚠ 而這個成本**會跟著資料庫一起長**：`data/adj/` 每天都在變多。
#   ⛔ 更正我自己當天寫錯的一句：我原本在這裡寫「Actions 上超過 11 分鐘、
#     正在把每日那趟吃掉」——**那是錯的**。實測 run 34449288399 那一步是
#     **1 分 56 秒**；我讀到的是過期的 API 快照就當成「它還在跑」。
#   ⇒ 這個最佳化仍然值得做（本機 75 → 49 秒，而且成本會長），
#     ⛔ 但它當時**不是**每日逾時的原因——那句話我不該寫。
#   ⭐ 而後兩趟（[2][3]）根本不需要真的掃：它們驗的是「斷言的算術」，
#     掃出來的結果每一趟都一樣。
#   ⇒ `cached=True` 時把 `G.scan` 換成「回第一趟的結果」。
#   ⛔ [1] 仍然是真的掃（`n_un` 要真的）；[3.5] 也不快取（它換了 STOCKS 目錄）。
_SCAN_CACHE = []


def run(out, lr, low=None, cached=False):
    # ⛔ 2026-09-09：`LOW`（歷史最低值）是後來加的，而這支一開始**沒有導走它**
    #   ⇒ 這支「離線」自測會寫到 repo 真的 `_adj_gap_low.txt`，
    #     而那個檔是斷言的基準——寫壞它等於把門檻改掉，**而且看起來完全正常**。
    #   ⚠ 同一族的坑今天第 N 次（runlog.PATH、holiday_schedule.csv…）。
    #   ⇒ 新增一個輸出路徑就要問一次：**這支自測有沒有把它導走？**
    old = (G.OUT, _RL.PATH, G.LOW)
    real_scan = G.scan
    G.OUT, _RL.PATH = out, lr
    G.LOW = low or (out + ".low")
    if cached and _SCAN_CACHE:
        # ⚠ 簽章照綁：⛔ 不可以比真的寬鬆，否則 `scan()` 改參數時這裡不會紅。
        import inspect
        _sig = inspect.signature(real_scan)

        def _stub(*a, **k):
            _sig.bind(*a, **k)
            return _SCAN_CACHE[0]
        G.scan = _stub
    try:
        sys.argv = ["adj_gap.py"]
        if not _SCAN_CACHE:
            def _rec(*a, **k):
                r = real_scan(*a, **k)
                _SCAN_CACHE.append(r)
                return r
            G.scan = _rec
        G.main()
        return io.open(lr, encoding="utf-8").read()
    finally:
        G.OUT, _RL.PATH, G.LOW = old
        G.scan = real_scan


def G_last_file(d):
    """⚠ 與 `adj_gap.main()` 裡那一段同一個判準（日檔：從**檔名**看）。"""
    try:
        xs = [n[:-4] for n in os.listdir(d) if n.endswith(".csv")
              and n[0].isdigit()]
        return max(xs) if xs else ""
    except OSError:
        return ""


def G_last_row(d):
    """⚠ 個股庫是按股票切的 ⇒ 最後一天要從**列**看，不是從檔名看。"""
    best = ""
    try:
        names = [n for n in sorted(os.listdir(d))
                 if n.endswith(".csv") and not n.startswith("_")]
    except OSError:
        return ""
    for n in names[:80]:
        try:
            with io.open(os.path.join(d, n), encoding="utf-8") as f:
                last = ""
                for ln in f:
                    if ln[:1].isdigit():
                        last = ln.split(",", 1)[0]
                best = max(best, last)
        except OSError:
            pass
    return best


def main():
    d = tempfile.mkdtemp()
    real_out, real_lr = G.OUT, _RL.PATH
    b4 = (os.path.getmtime(real_out) if os.path.exists(real_out) else None,
          os.path.getmtime(real_lr) if os.path.exists(real_lr) else None)
    b4_low = os.path.getmtime(G.LOW) if os.path.exists(G.LOW) else None

    print("[1] 第一趟（沒有舊檔）⇒ 只記錄不判定")
    out1, lr1 = os.path.join(d, "a.csv"), os.path.join(d, "a.md")
    t1 = run(out1, lr1)
    ck("寫得出 _adj_gap.csv", os.path.exists(out1))
    with io.open(out1, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ck("表頭逐字", list(rows[0].keys()) == G.HEADER if rows else False,
       str(list(rows[0].keys())) if rows else "(空)")
    n_un = sum(1 for r in rows if r["why"] == "未歸因")
    # ⚠ 2026-09-09：加了條件 ④ 之後「轉上市首日」被擋在**偵測器外**（不再出現在清單裡），
    #   現在會出現的是「事件掛在休市日」。⛔ 測試要跟著判準走，不是反過來。
    ck("有歸因欄且分得出類別",
       {r["why"] for r in rows} >= {"未歸因", "事件掛在休市日"},
       str({r["why"] for r in rows}))
    ck("第一趟斷言不判定", "**✗**　未歸因的筆數沒有高於歷史最低值" not in t1)
    print(f"       （本機現況：未歸因 {n_un} 筆）")

    print("[2] ★★ 偽造一個『上一趟只有 1 筆』的舊檔 ⇒ 斷言必須紅")
    out2, lr2 = os.path.join(d, "b.csv"), os.path.join(d, "b.md")
    with io.open(out2, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(G.HEADER)
        w.writerow(["9999", "假的", "2020-01-02", "twse", "twse",
                    "10.00", "9.00", "-10.00%", "未歸因"])
    low2 = os.path.join(d, "b.low")
    io.open(low2, "w").write("1,2026-09-09\n")     # ⭐ 偽造「歷史最低值 = 1」
    t2 = run(out2, lr2, low2, cached=True)
    ck("★ 未歸因高於歷史最低值 ⇒ 斷言變 ✗", "**✗**　未歸因的筆數沒有高於歷史最低值" in t2)
    ck("★ ✗ 的細節寫得出前後值", f"歷史最低 1｜本輪 {n_un}" in t2,
       [l for l in t2.splitlines() if "歷史最低" in l])

    print("[3] ★ 反向：偽造一個『上一趟很多』的舊檔 ⇒ 斷言要綠")
    out3, lr3 = os.path.join(d, "c.csv"), os.path.join(d, "c.md")
    with io.open(out3, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(G.HEADER)
        for i in range(n_un + 50):
            w.writerow([f"{9000+i}", "假的", "2020-01-02", "twse", "twse",
                        "10.00", "9.00", "-10.00%", "未歸因"])
    low3 = os.path.join(d, "c.low")
    io.open(low3, "w").write(f"{n_un + 50},2026-09-09\n")   # 歷史最低值很高
    t3 = run(out3, lr3, low3, cached=True)
    ck("★ 未歸因低於歷史最低值 ⇒ 斷言是 ok（不是永遠紅）", "**✗**　未歸因的筆數沒有高於歷史最低值" not in t3)
    ck("★ 變化量印得出來且是正號（＝變少）", "本輪變化量 +50" in t3,
       [l for l in t3.splitlines() if "本輪變化量" in l])

    print("[3.5] ⭐ 條件 ⑤：前一列**沒有成交價**就不比（甲跑完之後才會用到）")
    # ⛔ 為什麼要有這一段：官方 `MI_INDEX` 的 `notes` 明列
    #   「無比價含前一日無收盤價、當日除權、除息、**新上市**、**恢復交易**者」
    #   ⇒ 停牌**恢復交易**當天官方也寫 `X` ⇒ 我方存 `0.0` ⇒ 條件 ① 會中。
    #   ⚠ 而它不是除權息 ⇒ 不擋掉就會多報。
    #
    #   ⭐ 甲之前：停牌那幾天日檔**整列不存在** ⇒ 條件 ③ 自己擋掉（實測 0 筆）。
    #     甲之後：那些列補回來了（`close` 空、`price_basis='無成交'`）
    #     ⇒ 條件 ③ 會過，改由條件 ⑤ 擋。**這一段就是在測那個未來。**
    sand = tempfile.mkdtemp()
    old_stocks, old_daily = G.STOCKS, G.DAILY
    try:
        G.STOCKS = sand
        H = "date,close,change,market,price_basis"
        # 2020-01-06 停牌（close 空、無成交）；01-07 恢復交易 ⇒ change='0.0'、價格跳動
        io.open(os.path.join(sand, "8888.csv"), "w", encoding="utf-8").write(
            H + "\n"
            "2020-01-03,10.00,0.50,twse,\n"
            "2020-01-06,,,twse,無成交\n"
            "2020-01-07,9.00,0.0,twse,\n")
        # ⚠ 對照組：同樣的形狀但前一列**有價格** ⇒ 這才是真的要抓的除權息
        io.open(os.path.join(sand, "7777.csv"), "w", encoding="utf-8").write(
            H + "\n"
            "2020-01-03,10.00,0.50,twse,\n"
            "2020-01-06,10.00,0.0,twse,\n"
            "2020-01-07,9.00,0.0,twse,\n")
        cal = ["2020-01-03", "2020-01-06", "2020-01-07"]
        meta = {"8888": {"kind": "stock"}, "7777": {"kind": "stock"}}
        got = G.scan(cal, {}, meta)
        ids = {x[0] for x in got}
        ck("★ 恢復交易日（前一列無成交價）**不被標成缺還原因子**",
           "8888" not in ids, str(got))
        ck("★ 對照組：前一列**有價格**時照樣抓得到（判準沒有被改鬆）",
           "7777" in ids, str(got))
    finally:
        G.STOCKS, G.DAILY = old_stocks, old_daily
        shutil.rmtree(sand, ignore_errors=True)

    # ══════════════════════════════════════════════════════════
    # ⭐⭐ [3.5] 這一支讀的是 `data/stocks/`（`transpose.py` 的產出）
    #   ⇒ 排在 transpose **之前**就會拿到上一趟的結果。
    #   實測代價（2026-09-10 19:21）：報「未歸因 22（歷史最低 12）」，其中
    #   **`2330 台積電 2460.00 → 2.00　−99.92%`**
    #   ——⭐ 而 2330 那幾天的收盤 2410／2460／2470／2465／2450，一格都沒錯。
    #   ⛔ 一個會報「台積電跌 99.92%」的斷言，下一次真的有事時沒有人會信它。
    # ⇒ 步驟順序已經調到 transpose 之後；⚠ 順序**會被下一個人改回去**
    #   ⇒ 這一節測那道「自己驗終點」的斷言。
    # ══════════════════════════════════════════════════════════
    print("[3.6] ⭐ 個股庫必須跟得上日檔（⛔ 否則這一趟的結果不可信）")
    sand2 = tempfile.mkdtemp()
    old_stocks2, old_daily2 = G.STOCKS, G.DAILY
    try:
        stk = os.path.join(sand2, "stocks")
        dly = os.path.join(sand2, "daily")
        os.makedirs(stk)
        os.makedirs(dly)
        G.STOCKS = stk
        io.open(os.path.join(stk, "2330.csv"), "w", encoding="utf-8").write(
            "date,close,change,market\n2026-09-09,2465,-5.0,twse\n")
        for d in ("2026-09-08", "2026-09-09"):
            io.open(os.path.join(dly, d + ".csv"), "w",
                    encoding="utf-8").write("key,date\n")
        ck("★ 個股庫最後一天讀得出來（⛔ 是從**列**看，不是從檔名）",
           G_last_row(stk) == "2026-09-09", G_last_row(stk))
        ck("★ 日檔最後一天讀得出來（這一邊是從檔名看）",
           G_last_file(dly) == "2026-09-09", G_last_file(dly))
        ck("⭐ 兩邊一樣 ⇒ 判準成立", G_last_row(stk) >= G_last_file(dly))
        # ⛔ 反向：日檔多了一天而個股庫沒跟上 ⇒ 判準要不成立
        io.open(os.path.join(dly, "2026-09-10.csv"), "w",
                encoding="utf-8").write("key,date\n")
        ck("⭐⭐ 日檔多一天、個股庫沒跟上 ⇒ **判準不成立**"
           "（⇒ 那一趟的結果不可信）",
           not (G_last_row(stk) >= G_last_file(dly)),
           f"{G_last_row(stk)} vs {G_last_file(dly)}")
        ck("⚠ 個股庫是空的時候也不會誤判成「跟上了」",
           not (G_last_row(os.path.join(sand2, "nope")) >= G_last_file(dly)))
    finally:
        G.STOCKS, G.DAILY = old_stocks2, old_daily2
        shutil.rmtree(sand2, ignore_errors=True)

    print("[4] ⛔ 沒有動到 repo")
    ck("★ 沒動到真的 _adj_gap_low.txt",
       (os.path.getmtime(G.LOW) if os.path.exists(G.LOW) else None) == b4_low,
       "⛔ 它是斷言的基準，寫壞了等於把門檻改掉")
    ck("★ 沒動到真的 _adj_gap.csv",
       (os.path.getmtime(real_out) if os.path.exists(real_out) else None) == b4[0])
    ck("★ 沒動到真的 _last_run.md",
       (os.path.getmtime(real_lr) if os.path.exists(real_lr) else None) == b4[1])

    print()
    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    # ══════════════════════════════════════════════════════════════
    print("⑧ ⭐⭐ 分格覆蓋率：**同一種證券在一個市場有、另一個市場整格空**")
    # ⚠ 這一節不碰真資料（⛔ 這支已經因為掃全庫吃掉過 11 分鐘）——純函式，毫秒級。
    #   照市場情報分析線 2026-09-11 13:05 的實測形狀做：
    #     twse × etf  有（00929 38 列）　⛔ tpex × etf  119 檔全空
    sand = tempfile.mkdtemp(prefix="grid_")
    try:
        adjd = os.path.join(sand, "adj")
        os.makedirs(adjd)
        meta = {}
        for i in range(30):                      # twse × etf：有一半有因子
            meta[f"t{i:03d}"] = {"market": "twse", "kind": "etf"}
            if i < 15:
                io.open(os.path.join(adjd, f"t{i:03d}.csv"), "w").write("date\n")
        for i in range(119):                     # ⛔ tpex × etf：整格空
            meta[f"p{i:03d}"] = {"market": "tpex", "kind": "etf"}
        for i in range(40):                      # tpex × stock：有 ⇒ 不該被報
            meta[f"s{i:03d}"] = {"market": "tpex", "kind": "stock"}
            io.open(os.path.join(adjd, f"s{i:03d}.csv"), "w").write("date\n")
        for i in range(50):                      # ⚠ 兩邊都空的 kind ⇒ **不報**
            meta[f"b{i:03d}"] = {"market": "tpex", "kind": "beneficiary"}
            meta[f"c{i:03d}"] = {"market": "twse", "kind": "beneficiary"}
        grid = G.coverage_grid(meta, adjd)
        ck("⭐ 分格算得對（tpex×etf 是 0/119）",
           grid.get(("tpex", "etf")) == (0, 119), str(grid.get(("tpex", "etf"))))
        ck("  twse×etf 是 15/30", grid.get(("twse", "etf")) == (15, 30),
           str(grid.get(("twse", "etf"))))
        gaps, waived = G.grid_gap(grid)
        ck("⭐⭐ 抓到 tpex×etf 整格空（⛔ 而它的總填值率很高，看總數抓不到）",
           [(k, m) for k, m, *_ in gaps] == [("etf", "tpex")], str(gaps))
        ck("  ⚠ 報出來時附**對照組**（另一個市場有多少）",
           gaps and gaps[0][3] == "twse" and gaps[0][4] == "15/30", str(gaps))
        ck("⛔ 兩邊都空的 kind **不報**（⚠ 那是問錯問題，不是缺資料）",
           not [g for g in gaps if g[0] == "beneficiary"], str(gaps))
        # ⛔ 上面那條用的是**混著別的 kind** 的 grid ⇒ 拿掉對照組那一行時
        #   它會炸在 `max()` 而不是被斷言抓到——⚠ **紅在錯的地方等於指錯兇手**。
        #   ⇒ 再加一個**只有兩邊都空**的 grid，讓它紅在該紅的那一條上。
        only_empty = {("tpex", "beneficiary"): (0, 50),
                      ("twse", "beneficiary"): (0, 50)}
        _o, _w = (G.grid_gap(only_empty) if True else ([], []))
        ck("  ⭐ 而且**整張 grid 都沒有對照組**時回空，⛔ 不是炸掉",
           _o == [] and _w == [], f"{_o}｜{_w}")
        ck("  ⛔ 有覆蓋的格不報（tpex×stock）",
           not [g for g in gaps if g[0] == "stock"], str(gaps))
        # ⚠ 正例的反面：格子太小就不報（⛔ 三檔剛好都沒事件是正常的）
        small = {("tpex", "reit"): (0, 3), ("twse", "reit"): (2, 5)}
        ck("⚠ 檔數低於 GRID_MIN 的格**不報**（⛔ 否則會每天假紅）",
           not G.grid_gap(small)[0], str(G.grid_gap(small)))
        ck("  ⭐ 而把門檻調低它就報得出來 ⇒ 證明那一格確實是 0",
           len(G.grid_gap(small, min_n=2)[0]) == 1, str(G.grid_gap(small, min_n=2)))

        print("  ⭐⭐ 白名單：降成 ⚠、⛔ 但不可以消失")
        wg = {("emerging", "stock"): (0, 363), ("twse", "stock"): (9, 10)}
        out2, wv2 = G.grid_gap(wg)
        ck("  ⭐ 白名單裡的格**不進 ✗**", not out2, str(out2))
        ck("  ⛔ 但它**還在 waived 裡**（⚠ 消失的那一刻就再也沒人想起它）",
           [(k, m) for k, m, *_ in wv2] == [("stock", "emerging")], str(wv2))
        ck("  ⚠ 而白名單每一格都要有**理由字串**（⛔ 不可以是空的）",
           all(isinstance(v, str) and len(v) > 20 for v in G.GRID_WAIVED.values()),
           str(G.GRID_WAIVED))
        ck("  ⛔ 理由裡不可以只寫「暫時」就了事",
           all("暫時" not in v for v in G.GRID_WAIVED.values()))
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    print("全過" if not FAIL else f"⛔ {len(FAIL)} 條沒過")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
