#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 `adj_gap.main()`，⛔ 重點在**那條斷言真的會紅**。

這一支的斷言是「未歸因的筆數沒有比上一趟多」。
⛔ 一條永遠綠的斷言是裝飾，而這一條特別容易變成裝飾——
因為它比的是**自己上一趟寫的檔**，只要寫檔與比對的順序寫反，它就永遠相等。

⇒ 所以這裡直接**偽造一個「上一趟只有 1 筆未歸因」的舊檔**，
  再跑一次真的掃描（現在是 80 筆）⇒ 斷言必須紅。
"""
import io, os, sys, tempfile, csv
import runlog as _RL
import adj_gap as G

FAIL = []


def ck(n, c, note=""):
    print(("  ok   " if c else "  ✗    ") + n + (f"　（{note}）" if note else ""))
    if not c:
        FAIL.append(n)


def run(out, lr, low=None):
    # ⛔ 2026-09-09：`LOW`（歷史最低值）是後來加的，而這支一開始**沒有導走它**
    #   ⇒ 這支「離線」自測會寫到 repo 真的 `_adj_gap_low.txt`，
    #     而那個檔是斷言的基準——寫壞它等於把門檻改掉，**而且看起來完全正常**。
    #   ⚠ 同一族的坑今天第 N 次（runlog.PATH、holiday_schedule.csv…）。
    #   ⇒ 新增一個輸出路徑就要問一次：**這支自測有沒有把它導走？**
    old = (G.OUT, _RL.PATH, G.LOW)
    G.OUT, _RL.PATH = out, lr
    G.LOW = low or (out + ".low")
    try:
        sys.argv = ["adj_gap.py"]
        G.main()
        return io.open(lr, encoding="utf-8").read()
    finally:
        G.OUT, _RL.PATH, G.LOW = old


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
    t2 = run(out2, lr2, low2)
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
    t3 = run(out3, lr3, low3)
    ck("★ 未歸因低於歷史最低值 ⇒ 斷言是 ok（不是永遠紅）", "**✗**　未歸因的筆數沒有高於歷史最低值" not in t3)
    ck("★ 變化量印得出來且是正號（＝變少）", "本輪變化量 +50" in t3,
       [l for l in t3.splitlines() if "本輪變化量" in l])

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
