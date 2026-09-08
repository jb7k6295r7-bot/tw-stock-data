#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_runlog.py — 離線驗 runlog.py。**不碰真的 data/。**

★ 為什麼要有這一支
────────────────────────────────
`runlog` 現在是 fetch／mops／adjust／transpose／suspend／capital 六支共用的出口，
`data/meta/_last_run.md` 是「一次讀完就知道整個資料庫最近一輪的狀況」的那一份。
它壞掉的方式最貴的一種是**安靜的**：某一支把別支的區塊蓋掉，
於是那一頁看起來完整、其實只剩最後跑的那一支——
**一份看起來完整、其實殘缺的摘要，比沒有摘要更糟。**

跑法：python3 selftest_runlog.py（不連網、不需要資料）
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ok = fail = 0


def chk(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✓ {label}" + (f"　（{detail}）" if detail else ""))
    else:
        fail += 1
        print(f"  ✗ {label}" + (f"　（{detail}）" if detail else ""))


def run(root, code):
    """在沙盒裡跑一段用 runlog 的程式，回傳 (exit code, _last_run.md 內容)。"""
    p = os.path.join(root, "_t.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("import sys, runlog\n" + code)
    r = subprocess.run([sys.executable, "_t.py"], cwd=root,
                       capture_output=True, text=True)
    path = os.path.join(root, "data", "meta", "_last_run.md")
    txt = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    return r.returncode, txt


def main():
    root = tempfile.mkdtemp(prefix="runlogtest_")
    before = sorted(os.listdir(os.path.join(HERE, "data"))) \
        if os.path.isdir(os.path.join(HERE, "data")) else None
    try:
        shutil.copy(os.path.join(HERE, "runlog.py"), root)

        print("── 1. 第一次寫 ──")
        rc, t = run(root, "r=runlog.Run('甲')\n"
                          "r.info('列數','10')\n"
                          "r.check('沒有空值', True, '實際 0 列')\n"
                          "sys.exit(r.finish())\n")
        chk("全過回傳 0", rc == 0, f"rc={rc}")
        chk("建出表頭", t.startswith("# 各支腳本最近一次執行"))
        chk("有甲的區塊且標 ✓", "## 甲　✓ 正常" in t)
        chk("detail 寫的是實際值", "實際 0 列" in t)

        print("── 2. 第二支不會蓋掉第一支 ──")
        rc, t = run(root, "r=runlog.Run('乙')\n"
                          "r.check('列數沒有變少', False, '100 → 3')\n"
                          "sys.exit(r.finish())\n")
        chk("檢查沒過就回傳 1", rc == 1, f"rc={rc}")
        chk("甲還在", "## 甲　✓ 正常" in t)
        chk("乙標成 ✗", "## 乙　✗ 有問題" in t)
        chk("表頭只有一份", t.count("# 各支腳本最近一次執行") == 1)

        print("── 3. 同一支重跑只換自己那一塊 ──")
        rc, t = run(root, "r=runlog.Run('甲')\n"
                          "r.info('列數','20')\n"
                          "sys.exit(r.finish())\n")
        chk("甲換成新內容", "**列數**：20" in t and "**列數**：10" not in t)
        chk("乙的 ✗ 沒有被清掉", "## 乙　✗ 有問題" in t)
        chk("甲仍排在乙前面（順序穩定）",
            t.index("## 甲") < t.index("## 乙"))
        chk("沒有變成兩塊甲", t.count("## 甲") == 1)

        print("── 4. 沒有 check 的區塊 ──")
        rc, t = run(root, "r=runlog.Run('丙')\n"
                          "r.note('這一趟沒有東西要驗')\n"
                          "sys.exit(r.finish())\n")
        chk("沒有 check 時視為正常", rc == 0 and "## 丙　✓ 正常" in t)
        chk("不印空的『檢查：』", "## 丙" in t and
            t.split("## 丙")[1].split("## ")[0].count("檢查：") == 0)

        print("── 5. 從別的目錄叫它（路徑錨定）──")
        # ★ 這一條是 2026-09-08 真的踩到的：runlog 原本用相對路徑，
        #   `selftest_reduce.py` 把 adjust.py 複製到暫存目錄再跑、但 CWD 還是 repo，
        #   於是它**寫進真的 repo**，把 suspend 那一塊洗掉了。
        #   「不碰真的 data/」那句保證就是這樣失效的，而且看起來完全成功。
        other = os.path.join(root, "另一個目錄")
        os.makedirs(other, exist_ok=True)
        env = dict(os.environ, PYTHONPATH=root)
        subprocess.run([sys.executable, os.path.join(root, "_t.py")],
                       cwd=other, env=env, capture_output=True, text=True)
        chk("寫在 runlog.py 旁邊，不是 CWD 底下",
            os.path.exists(os.path.join(root, "data", "meta", "_last_run.md")) and
            not os.path.exists(os.path.join(other, "data")))

        after = sorted(os.listdir(os.path.join(HERE, "data"))) \
            if os.path.isdir(os.path.join(HERE, "data")) else None
        chk("真的 repo 的 data/ 沒有被建立或改動", before == after)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
