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
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
