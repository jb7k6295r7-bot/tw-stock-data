#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""calendar_audit.py 的寫檔行為自測。**不連網、不碰 repo 的 data/。**

★ 為什麼要有這一支
────────────────────────────────
`data/meta/calendar_twse.csv` 是「哪一天該有資料」的**唯一外部判準**
（來自 TWSE FMTQIK，與建日檔的個股端點不同條路）。

`--write` 舊版是**整份覆蓋**，只寫這一趟抓到的月份。把它排進每日排程、
只跑當月的話，2,845 天的日曆會被截成那個月的幾天——
**而且不會報錯，檔案格式完全正常、看起來就像一份完整的日曆。**
之後任何拿它當閘門的檢查都會把絕大多數交易日判成「非交易日」。

所以預設改成**併入（只增不減）**：交易日不會事後被取消，這是安全的。
真要整份重建請明講 `--replace`。第 1、2 節就是釘住這兩件事。

跑法：python3 selftest_calendar.py（不連網、不需要資料）
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ok = fail = 0

REPO_CAL = os.path.join(HERE, "data", "meta", "calendar_twse.csv")


def chk(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✓ {label}" + (f"　（{detail}）" if detail else ""))
    else:
        fail += 1
        print(f"  ✗ {label}" + (f"　（{detail}）" if detail else ""))


def read(path):
    if not os.path.exists(path):
        return set()
    return {l.split(",")[0] for l in
            io.open(path, encoding="utf-8").read().splitlines()[1:] if l.strip()}


def main():
    import calendar_audit as C

    tmp = tempfile.mkdtemp(prefix="caltest_")
    cal_before = io.open(REPO_CAL, "rb").read() if os.path.isfile(REPO_CAL) else None
    out = os.path.join(tmp, "calendar_twse.csv")
    C.OUT = out
    C.runlog = type("_N", (), {"Run": lambda *a, **k: type(
        "_R", (), {"info": lambda s, *a: s, "note": lambda s, *a: s,
                   "check": lambda s, *a, **k: s, "finish": lambda s: 0})()})

    # 假的官方回應：2026 年 8 月與 9 月各兩天
    MONTHS = {(2026, 8): {"2026-08-03", "2026-08-04"},
              (2026, 9): {"2026-09-01", "2026-09-02"}}
    C.fetch_month = lambda y, m, sleep: (MONTHS.get((y, m), set()), "假資料")
    # 我方日檔：假裝這些日子都有（否則會被算成漏抓）
    C.ours = lambda: {"2026-08-03", "2026-08-04", "2026-09-01", "2026-09-02"}

    def run(*argv):
        old = sys.argv
        sys.argv = ["calendar_audit.py"] + list(argv)
        try:
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                return C.main()
        finally:
            sys.argv = old

    try:
        print("── 1. 只跑當月，不可以把既有的日曆截掉 ──")
        # 先造一份「已經有很多天」的日曆，模擬 repo 的 2,845 天
        old_days = {f"2015-0{m}-0{d}" for m in (1, 2, 3) for d in (1, 2, 3)}
        with io.open(out, "w", encoding="utf-8") as f:
            f.write("date,source\n")
            for d in sorted(old_days):
                f.write(f"{d},FMTQIK\n")
        before = read(out)
        run("--start", "2026-09", "--end", "2026-09", "--sleep", "0", "--write")
        after = read(out)
        chk("★ 舊的日子一天都沒有掉", old_days <= after,
            f"{len(before)} → {len(after)} 天；掉了 {sorted(old_days - after)[:3]}")
        chk("這一趟抓到的日子有併進去", {"2026-09-01", "2026-09-02"} <= after)
        chk("總天數 = 舊的 + 新的", len(after) == len(old_days) + 2, f"{len(after)} 天")

        print("\n── 2. --replace 仍然是整份重建 ──")
        run("--start", "2026-08", "--end", "2026-08", "--sleep", "0",
            "--write", "--replace")
        after = read(out)
        chk("★ --replace 會把舊的清掉", not (old_days & after), f"{len(after)} 天")
        chk("只剩這一趟抓到的", after == {"2026-08-03", "2026-08-04"}, str(sorted(after)))

        print("\n── 3. 有月份沒問到就不寫 ──")
        with io.open(out, "w", encoding="utf-8") as f:
            f.write("date,source\n2015-01-05,FMTQIK\n")
        C.fetch_month = lambda y, m, sleep: (None, "請求失敗：假的")
        run("--start", "2026-09", "--end", "2026-09", "--sleep", "0", "--write")
        chk("★ 半套日曆不寫檔（原檔不動）", read(out) == {"2015-01-05"},
            "半套的獨立日曆比沒有更糟——它看起來像完整的")

        print("\n── 4. 沒有碰到 repo ──")
        cal_after = io.open(REPO_CAL, "rb").read() if os.path.isfile(REPO_CAL) else None
        chk("★ repo 的 calendar_twse.csv 逐位元沒變", cal_before == cal_after)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
