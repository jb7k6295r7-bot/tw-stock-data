#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_holiday.py — 釘住 holiday.py 的判讀，**尤其是那個不對稱**。

    python3 selftest_holiday.py

## 這支要擋的三件事

① **平安日的頁面上「停止上班」本來就出現 12 次**（探針實測）——
   那是頁面自己的說明文字。寫成 `if "停止上班" in html` 會**天天判成休市**。
   ⇒ 必須是「台北市」**那一列**裡有，才算。

② 頁面卡在昨天的公告時，**不可以**當成今天照常開盤。

③ 判讀是**單向**的：找不到 ⇒ open，⛔ 不是「找不到 ⇒ closed」。
   兩種錯的代價不對稱（見 holiday.py 檔頭）。

⛔ 這支**不驗**「今天到底有沒有休市」——那要有颱風天的真實樣本，
  而我方目前沒有。**沒有樣本就承認沒有**，不要拿編的樣本當證據。
  下面那份 `TYPHOON` 是**我編的**，只用來驗「同一列比對」這個機制走不走得通。
"""
import io
import os
import sys
import tempfile

import holiday as H

# 平安日：照抄探針量到的特徵——有日期、22 縣市一個都沒有、但「停止上班」出現很多次
CALM = """<html><body>
<h1>天然災害停止上班及上課情形</h1>
<p>本表僅列出<b>停止上班</b>之機關。未列出者均照常上班上課。</p>
<p>停止上班 停止上班 停止上班 停止上班 停止上班</p>
<p>停止上班 停止上班 停止上班 停止上班 停止上班 停止上班</p>
<div>115年
            9月
            9日 (2026/09/09)</div>
<table><tr><th>縣市</th><th>情形</th></tr><tr><td>無</td><td>無</td></tr></table>
</body></html>"""

# ⚠ **我編的**颱風日樣本。只驗機制，不當證據。
TYPHOON = """<html><body>
<h1>天然災害停止上班及上課情形</h1>
<p>本表僅列出<b>停止上班</b>之機關。</p>
<div>115年9月9日 (2026/09/09)</div>
<table><tr><th>縣市</th><th>情形</th></tr>
<tr><td>臺北市</td><td>停止上班及上課</td></tr>
<tr><td>新北市</td><td>停止上班及上課</td></tr></table>
</body></html>"""

# 只有南部放假——⛔ 這種日子**台股照開**
SOUTH_ONLY = """<html><body>
<div>115年9月9日 (2026/09/09)</div>
<p>本表僅列出停止上班之機關。</p>
<table><tr><td>高雄市</td><td>停止上班及上課</td></tr>
<tr><td>屏東縣</td><td>停止上班及上課</td></tr></table>
</body></html>"""

STALE = CALM.replace("2026/09/09", "2026/09/08").replace("9月\n            9日",
                                                         "9月\n            8日")

FAIL = []


def ck(name, cond, note=""):
    print(f"  {'ok  ' if cond else '✗   '} {name}" + (f"　（{note}）" if note else ""))
    if not cond:
        FAIL.append(name)


def main():
    print("[1] ★ 平安日：「停止上班」出現很多次，但**不是台北市那一列**")
    hit, seg = H.taipei_stopped(CALM)
    ck("平安日不會被判成休市", hit is False,
       f"整頁「停止上班」{CALM.count('停止上班')} 次，仍然 hit=False")
    ck("平安日抓得到日期", H.page_date(CALM) == "2026-09-09", H.page_date(CALM))

    print("[2] 颱風日（⚠ 樣本是編的，只驗機制）")
    hit2, seg2 = H.taipei_stopped(TYPHOON)
    ck("台北市停班會被抓到", hit2 is True, seg2[:60])

    print("[3] ★★ 只有南部放假 ⇒ 台股照開")
    hit3, _ = H.taipei_stopped(SOUTH_ONLY)
    ck("南部放假不會被判成休市", hit3 is False,
       f"整頁「停止上班」{SOUTH_ONLY.count('停止上班')} 次，但沒有台北市")

    print("[4] 頁面日期不是今天 ⇒ unknown，⛔ 不是 open")
    ck("抓得到舊日期", H.page_date(STALE) == "2026-09-08", H.page_date(STALE))

    print("[5] 端到端（沙箱，⛔ 不碰 repo 的 data/）")
    d = tempfile.mkdtemp()
    old_out, old_arch = H.OUT, H.ARCH
    H.OUT = os.path.join(d, "holiday_status.csv")
    H.ARCH = os.path.join(d, "holiday")
    # ⚠ 這一段是本檔第一版**漏掉的**：`H.main()` 裡有 `runlog.Run("holiday")`，
    #   而 runlog 的路徑是用 `__file__` 錨定的 ⇒ 它會寫進 **repo 真的**
    #   `data/meta/_last_run.md`。runlog.py 的檔頭早就寫過這個坑
    #   （「跑一次 selftest_reduce.py 就把 suspend 那一塊蓋掉」），
    #   我還是踩了一次。⇒ 連 runlog 的輸出路徑一起導走。
    import runlog as _RL
    old_rl = _RL.PATH
    _RL.PATH = os.path.join(d, "_last_run.md")
    real_lastrun = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "meta", "_last_run.md")
    before = os.path.getmtime(real_lastrun) if os.path.exists(real_lastrun) else None
    try:
        for label, html in (("calm", CALM), ("typhoon", TYPHOON)):
            p = os.path.join(d, label + ".html")
            io.open(p, "w", encoding="utf-8").write(html)
            sys.argv = ["holiday.py", "--html", p]
            H.main()
        txt = io.open(H.OUT, encoding="utf-8").read()
        ck("寫得出 holiday_status.csv", "date,verdict" in txt)
        ck("同一天重跑不會疊列", len(txt.strip().splitlines()) == 2,
           f"實際 {len(txt.strip().splitlines())} 行（含表頭）")
    finally:
        H.OUT, H.ARCH = old_out, old_arch
        _RL.PATH = old_rl
    # ⛔ 這一項要**真的去看檔案系統**，不是宣告自己沒事
    #   （上一版寫成 `… or True`，那等於永遠通過——比沒有這一項更糟）。
    after = os.path.getmtime(real_lastrun) if os.path.exists(real_lastrun) else None
    ck("★ 沒有動到 repo 真的 _last_run.md", before == after,
       f"mtime {before} → {after}")

    print()
    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
