#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`feed_hosts.py` 的自測。**不連網。**

⭐ 這一支要釘的是**三層判準**（見 `feed_hosts` 檔頭），⛔ 因為它們每一層
都對應一次「`grep` 給了錯的數字」：

    ① 母體只收「真的被 workflow 跑到」的  ⇒ ⛔ 否則探針與一次性腳本會混進來
    ② 主機只從 AST 字串常數取、扣 docstring ⇒ ⛔ 否則說明文字裡的網址會被算進去
    ③ `www.tpex.org.tw` 不可以被歸進任何一族 ⇒ ⚠ 它底下兩族都有
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_hosts as F                                          # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(s)


def main():
    global OK, FAIL
    print("=" * 64)
    print("feed_hosts：我方哪一支打哪一個主機（不連網）")
    print("=" * 64)

    d = tempfile.mkdtemp(prefix="feedhosts_")
    real_here, real_wf = F.HERE, F.WF_DIR
    try:
        F.HERE = d
        F.WF_DIR = os.path.join(d, ".github", "workflows")
        write(os.path.join(F.WF_DIR, "daily.yml"),
              "jobs:\n  a:\n    steps:\n"
              "      - name: 抓\n        run: python real_feed.py\n")
        # ⭐ 被跑到的那一支：**註解**與 **docstring** 裡各放一個假主機，
        #   ⛔ 兩個都不可以被算進去（②）。
        write(os.path.join(d, "real_feed.py"),
              '"""說明：我們本來是打 https://docstring.example.com 的。"""\n'
              "# 註解：舊路 https://comment.example.com 已停用\n"
              'BASE = "https://openapi.twse.com.tw/v1/x"\n'
              'ALT = "https://www.twse.com.tw/rwd/zh/y"\n'
              'OTC = "https://www.tpex.org.tw/openapi/z"\n'
              'FAKE = "https://x.invalid/nope"\n'
              'OUT = "data/universe/daily"\n')
        # ⛔ 這一支**沒有**被任何 workflow 跑到 ⇒ 不進母體（①）
        write(os.path.join(d, "lonely_probe.py"),
              'BASE = "https://never.example.org/q"\n')

        mods = F.invoked_modules()
        ck("① ⭐ 母體只收**被 workflow 跑到**的（`real_feed.py` 在）",
           "real_feed.py" in mods, str(sorted(mods)))
        ck("① ⛔ 而沒有被跑到的那一支**不在**母體裡"
           "（⚠ 否則探針與一次性腳本會混進來）",
           "lonely_probe.py" not in mods, str(sorted(mods)))

        hs = F.hosts_of(os.path.join(d, "real_feed.py"))
        ck("② ⭐⭐ **docstring** 裡的主機**不算**"
           "（⚠ 我們的說明文字本來就會抄網址）",
           "docstring.example.com" not in hs, str(sorted(hs)))
        ck("② ⭐ **註解**裡的主機也不算（⛔ 註解不是字串常數 ⇒ AST 看不到）",
           "comment.example.com" not in hs, str(sorted(hs)))
        ck("② ⭐ 而真的在用的那三個都在",
           {"openapi.twse.com.tw", "www.twse.com.tw",
            "www.tpex.org.tw"} <= hs, str(sorted(hs)))
        ck("② ⛔ `.invalid`（假回應用的）不算",
           "x.invalid" not in hs, str(sorted(hs)))

        a, b, mix = F.classify(hs)
        ck("③ ⭐ `openapi.twse.com.tw` 落在 **A 開放資料型**",
           a == {"openapi.twse.com.tw"}, str(a))
        ck("③ ⭐ `www.twse.com.tw` 落在 **B 網站型**",
           b == {"www.twse.com.tw"}, str(b))
        ck("③ ⭐⭐ `www.tpex.org.tw` **兩族都不進**，落在「要逐條看路徑」"
           "（⚠ 它底下有 /openapi/ 也有一般報表頁）",
           mix == {"www.tpex.org.tw"}, f"a={a}｜b={b}｜mix={mix}")
        ck("③ ⛔ 三族**互斥**（⚠ 合併成兩種就會把 tpex 判進錯的那一邊）",
           not (a & b) and not (a & mix) and not (b & mix))

        wr = F.writes_of(os.path.join(d, "real_feed.py"))
        ck("④ ⭐ 「寫哪裡」取得到（`universe`）", wr == {"universe"}, str(wr))
    finally:
        F.HERE, F.WF_DIR = real_here, real_wf
        shutil.rmtree(d, ignore_errors=True)

    # ⭐⭐ ⑤ 現場：拿 repo 真的跑一次，斷言**母體不是 0**
    #   ⛔ 第七點那一句：回報「某群 0 筆」要附上正例數——
    #   ⚠ 而這一支最可能的壞法就是「母體被判準縮小成 0」而報表照樣印得很漂亮。
    mods = F.invoked_modules()
    ck("⑤ ⭐⭐ 現場母體不是 0（實際 ≥ 20 支被 workflow 跑到）",
       len(mods) >= 20, f"{len(mods)} 支")
    ext = [m for m in mods if F.hosts_of(os.path.join(HERE, m))]
    ck("⑤ ⭐ 而其中會連外的也不是 0（≥ 10 支）",
       len(ext) >= 10, f"{len(ext)} 支")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
