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

        # ══════════════════════════════════════════════
        # ⭐⭐ 端點層：只看主機的話，`www.tpex.org.tw` 有 **18 支**卡在
        #   「要逐條看」那一格 ⇒ ⛔ 那等於沒分類完，而我本來要把那個
        #   數字送出去給人裁——第七點那句：**分類完才送**。
        # ══════════════════════════════════════════════
        eps = F.endpoints_of(os.path.join(d, "real_feed.py"))
        ck("⑥ ⭐ 端點層拆得出**主機 ＋ 前兩層路徑**",
           "www.tpex.org.tw/openapi/z" in eps, str(sorted(eps)))
        ea, eb, eu = F.classify_ep(eps)
        ck("⑥ ⭐⭐ `www.tpex.org.tw**/openapi/**` 落在 **A**"
           "（⛔ 主機層時它卡在「要逐條看」）",
           "www.tpex.org.tw/openapi/z" in ea, str(sorted(ea)))
        ck("⑥ ⭐ 而同一個主機的**別的路徑**落在 **B**",
           not any(x.startswith("www.tpex.org.tw/www") for x in ea),
           str(sorted(ea)))
        eps2 = F.classify_ep({"www.tpex.org.tw/www/zh-tw"})
        ck("⑥ ⭐ `/www/zh-tw` 那一族是 **B 網站型**",
           eps2[1] == {"www.tpex.org.tw/www/zh-tw"}, str(eps2))
        eps3 = F.classify_ep({"www.tpex.org.tw/"})
        ck("⑥ ⛔⛔ 而**只有主機、沒有路徑**的 ⇒ 進第三格，**不猜**"
           "（⚠ 猜錯一邊就是給別人拿去裁的錯數字）",
           eps3[2] == {"www.tpex.org.tw/"} and not eps3[0] and not eps3[1],
           str(eps3))
        ck("⑥ ⭐ 而官方開放資料主機**不看路徑**就是 A"
           "（⚠ 判準順序：先主機再路徑）",
           F.classify_ep({"openapi.twse.com.tw/"})[0] == {"openapi.twse.com.tw/"},
           str(F.classify_ep({"openapi.twse.com.tw/"})))

        ck("⑥ ⭐⭐ 第三方主機（FinMind／GitHub）**不在這份條款的管轄**"
           "（⛔ 算進去會把暴露面話大）",
           not F.in_terms_scope("api.finmindtrade.com")
           and not F.in_terms_scope("github.com"))
        ck("⑥ ⭐ 而交易所的**子網域**算在管轄裡"
           "（mopsov／isin／openapi 都是 twse.com.tw 底下）",
           F.in_terms_scope("mopsov.twse.com.tw")
           and F.in_terms_scope("openapi.twse.com.tw")
           and F.in_terms_scope("www.tpex.org.tw"))
        # ⛔⛔ 這兩條的第一版我寫成 `… is False or True` ⇒ **恆真**。
        #   ⚠ 而它印出來跟真的一模一樣（四點五那個坑）。
        ck("⑥ ⛔ `twse.com.tw.evil.example`（把網域放在**前面**）不算",
           F.in_terms_scope("twse.com.tw.evil.example") is False)
        ck("⑥ ⛔ `faketwse.com.tw`（**不是子網域**，只是後綴像）不算",
           F.in_terms_scope("faketwse.com.tw") is False)

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
