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
import json
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


def _stat(p):
    """檔案的 mtime，不存在回 None。"""
    return os.path.getmtime(p) if os.path.exists(p) else None


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
    # ⚠ `main()` 裡的 `_schedule()` 會**真的連外**並寫 `holiday_schedule.csv`
    #   ⇒ 不導走的話，這支「離線」自測會在 Actions 上寫進真的 repo。
    #   ⛔ 同一個坑今天已經踩過一次（runlog 的路徑）。這次是同一族的第二個。
    old_sched = H.SCHED_CSV
    H.SCHED_CSV = os.path.join(d, "holiday_schedule.csv")
    import backfill as _B
    old_get = _B.get
    # ⛔⛔ 這裡**不可以**寫成「一律回錯誤」。2026-09-09 實測代價：
    #   上一版是 `lambda *a, **k: (None, "selftest：不連外")`，
    #   於是 `_schedule()` 在第一個 `if err` 就 return，
    #   **`json.loads` 那一行一次都沒跑到** ⇒ `holiday.py` 少 import 了
    #   `json` 與 `csv` 兩個模組，本檔全綠、Actions 上整段丟 NameError，
    #   而且被印成「✗ 不是 JSON」——看起來像對方的問題。
    #   ⇒ 假回應要**回真的形狀**（逐字照 `_holiday_probe.txt` [9] 實測到的），
    #     這樣 `_schedule()` 會從頭走到尾，寫檔那一段也會被執行。
    SCHED_JSON = json.dumps({
        "stat": "ok", "title": "115 年市場開休市日期",
        "fields": ["日期", "名稱", "說明"],
        "data": [["2026-01-01", "中華民國開國紀念日", "依規定放假1日。"],
                 ["2026-02-11", "農曆除夕前一日", "依規定放假1日。"],
                 ["2026-12-25", "行憲紀念日", "依規定放假1日。"]],
    }, ensure_ascii=False).encode()

    def _fake_get(url, *a, **k):
        if "holidaySchedule" in str(url):
            return SCHED_JSON, None
        return None, "selftest：不連外"          # ⛔ 其餘一律不連外
    _B.get = _fake_get
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
    before = _stat(real_lastrun)
    real_sched = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "meta",
        "holiday_schedule.csv")
    # ⛔ 「跑之前」就要記下來，⛔ 不可以在跑完之後才取兩次——
    #   那會拿同一個值跟自己比，**永遠通過**（今天已經寫過一次 `… or True`）。
    sched_before = _stat(real_sched)
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
        # ★★ 這三項是這一版新加的，因為上一版**根本沒走到 `_schedule()` 的本體**。
        #   ⛔ 只驗「沒炸」不夠：要驗它**真的把列寫進去了**。
        sched = io.open(H.SCHED_CSV, encoding="utf-8").read()
        ck("_schedule() 寫得出 holiday_schedule.csv",
           os.path.exists(H.SCHED_CSV))
        ck("表頭是 date,name,note,asof",
           sched.splitlines()[0] == "date,name,note,asof",
           sched.splitlines()[0] if sched else "(空的)")
        ck("三列假資料都併進去了", len(sched.strip().splitlines()) == 4,
           f"實際 {len(sched.strip().splitlines())} 行（含表頭）")
        ck("同一天跑兩趟不會疊列（第二趟是覆蓋）",
           sched.count("2026-01-01") == 1, f"出現 {sched.count('2026-01-01')} 次")
    finally:
        H.OUT, H.ARCH = old_out, old_arch
        H.SCHED_CSV = old_sched
        _B.get = old_get
        _RL.PATH = old_rl
    # ⛔ 這一項要**真的去看檔案系統**，不是宣告自己沒事
    #   （上一版寫成 `… or True`，那等於永遠通過——比沒有這一項更糟）。
    after = _stat(real_lastrun)
    ck("★ 沒有動到 repo 真的 _last_run.md", before == after,
       f"mtime {before} → {after}")
    ck("★ 沒有動到 repo 真的 holiday_schedule.csv",
       sched_before == _stat(real_sched), f"{sched_before} → {_stat(real_sched)}")

    print()
    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
