#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runlog.py 的自測。**不連網、不碰 repo 的 data/**。

要釘住的是這一支特有的兩種失效模式：

**① 寫到錯的地方，而且看起來完全成功。**
`PATH` 若是相對路徑，相對的是 **CWD 不是這支程式**。Actions 的 CWD 剛好是 repo
根目錄，所以一直看起來是對的；但 `selftest_reduce.py` 把 `adjust.py` 複製到暫存
目錄再跑、**CWD 還留在 repo**，於是它寫進真的 repo——把 `_last_run.md` 裡別支的
區塊洗掉。「不碰真的 data/」那句保證就是這樣失效的，**而且測試照樣全綠**。
所以第 3 組用子行程在**別的 CWD** 實際跑一次，證明檔案落在程式旁邊、不在 CWD。

**② 蓋掉別支的紀錄。**
`_last_run.md` 是四條以上的管線共用的，`finish()` 只能換自己那一塊。換錯了不會
報錯，只會讓別支的狀態安靜消失——而這個檔存在的理由正是「一次讀完就知道整個
資料庫最近一輪的狀況」。
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILED = []

REPO_LOG = os.path.join(HERE, "data", "meta", "_last_run.md")
REPO_LOG_BEFORE = (io.open(REPO_LOG, encoding="utf-8").read()
                   if os.path.exists(REPO_LOG) else None)


def ck(cond, msg):
    print(("  ok   " if cond else "  ✗ 失敗 ") + msg)
    if not cond:
        FAILED.append(msg)


def main():
    import runlog

    tmp = tempfile.mkdtemp(prefix="selftest_runlog_")
    try:
        print("── 1. 路徑錨定 ──")
        ck(os.path.isabs(runlog.PATH), "PATH 是絕對路徑（相對路徑會跟著 CWD 跑）")
        ck(os.path.dirname(os.path.dirname(os.path.dirname(runlog.PATH))) == HERE,
           "PATH 錨定在 runlog.py 同一層的 data/meta/")
        cwd0 = os.getcwd()
        os.chdir(tmp)
        try:
            import importlib
            importlib.reload(runlog)
            ck(os.path.dirname(os.path.dirname(os.path.dirname(runlog.PATH))) == HERE,
               "換到別的 CWD 再 reload，PATH 仍指向 runlog.py 旁邊")
        finally:
            os.chdir(cwd0)
            importlib.reload(runlog)

        print("\n── 2. 只換自己那一塊 ──")
        log = os.path.join(tmp, "data", "meta", "_last_run.md")
        rc = runlog.Run("alpha", log).info("區間", "A1").check("甲檢查", True).finish()
        ck(rc == 0, "check 全過時 finish() 回 0")
        ck(os.path.exists(log), "第一次 finish() 會把檔案建出來")
        s = io.open(log, encoding="utf-8").read()
        ck("# 各支腳本最近一次執行" in s, "第一次會寫出總標題")
        ck("## alpha" in s and "A1" in s, "info() 的內容有寫進自己的區塊")

        runlog.Run("beta", log).note("乙的備註").check("乙檢查", True).finish()
        s = io.open(log, encoding="utf-8").read()
        ck("## alpha" in s and "A1" in s, "★ 第二支寫入後，第一支的區塊還在")
        ck("## beta" in s and "乙的備註" in s, "第二支自己的區塊也在")
        alpha_before = s[s.index("## alpha"):s.index("## beta")]

        runlog.Run("beta", log).info("區間", "B2").check("乙檢查", True).finish()
        s = io.open(log, encoding="utf-8").read()
        ck(s.count("## beta") == 1, "同一支重跑不會堆疊出第二個自己的區塊")
        ck("B2" in s and "乙的備註" not in s, "同一支重跑會換掉自己的舊內容")
        ck(s[s.index("## alpha"):s.index("## beta")] == alpha_before,
           "★ 同一支重跑，別支的區塊逐字沒變")

        print("\n── 3. 失敗要說出來 ──")
        rc = runlog.Run("gamma", log).check("丙檢查", False, "實際 3 列").finish()
        ck(rc == 1, "有 check 沒過時 finish() 回 1（workflow 才會紅）")
        s = io.open(log, encoding="utf-8").read()
        ck("## gamma　✗ 有問題" in s, "沒過的區塊標頭是 ✗")
        ck("實際 3 列" in s, "detail 寫的是實際值，有進到檔案裡")
        ck("## alpha　✓ 正常" in s, "全過的區塊標頭是 ✓")

        print("\n── 4. 子行程在別的 CWD 跑（原本的 bug 現場）──")
        # 把 runlog.py 複製到暫存目錄，從「另一個 CWD」跑一支用它的程式。
        # 相對路徑的舊寫法會把檔案寫到 CWD 底下；錨定之後必須寫在副本旁邊。
        sub = os.path.join(tmp, "pkg")
        os.makedirs(sub)
        shutil.copy(os.path.join(HERE, "runlog.py"), sub)
        script = os.path.join(sub, "fake_adjust.py")
        io.open(script, "w", encoding="utf-8").write(
            "import os, sys\n"
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            "import runlog\n"
            "sys.exit(runlog.Run('adjust').info('來源', 'x').finish())\n")
        cwd = os.path.join(tmp, "elsewhere")
        os.makedirs(cwd)
        r = subprocess.run([sys.executable, script], cwd=cwd,
                           capture_output=True, text=True)
        ck(r.returncode == 0, "子行程正常結束")
        ck(os.path.exists(os.path.join(sub, "data", "meta", "_last_run.md")),
           "★ 檔案寫在 runlog.py 副本旁邊（錨定生效）")
        ck(not os.path.exists(os.path.join(cwd, "data")),
           "★ 檔案沒有寫到子行程的 CWD（這就是原本的 bug）")

        print("\n── 5. 全程沒有碰到 repo ──")
        now = (io.open(REPO_LOG, encoding="utf-8").read()
               if os.path.exists(REPO_LOG) else None)
        ck(now == REPO_LOG_BEFORE, "★ repo 的 data/meta/_last_run.md 逐字沒變")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 60)
    if FAILED:
        print(f"✗ {len(FAILED)} 項失敗：")
        for x in FAILED:
            print("   -", x)
        return 1
    print("全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
