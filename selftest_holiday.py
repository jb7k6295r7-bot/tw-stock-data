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

HERE = os.path.dirname(os.path.abspath(__file__))

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
    # ⛔⛔ 2026-09-14 又踩了**同一族的第三個**：`_schedule()` 新加的涵蓋率低水位
    #   `SCHED_LOW` 沒被導走 ⇒ 這支自測拿假資料（3 個年份）跑一趟，就把 repo 真的
    #   `_holiday_years_low.txt` 從 `6` **寫成 `2`**，⚠ 而它是「只往上寫」的檔
    #   ⇒ 看起來像「涵蓋率本來就只有 2 年」，那道閘門從此永遠綠。
    #   ⭐ 判準不是「記得導走」，是**下面那條「沒有動到 repo 真的檔」的斷言**：
    #     前兩個坑都是它抓到的，⛔ 而這個新檔當時沒有跟著加一條。
    old_low = H.SCHED_LOW
    H.SCHED_LOW = os.path.join(d, "_holiday_years_low.txt")
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

    # ⛔⛔ 2026-09-09 加逐年回補之後，這個假回應**不夠**：
    #   它對每一年都回同一份 2026 的資料，於是只走得到「端點忽略了 date」那一條。
    #   ⇒ 再造一個「回 0 列」的年份（2019），把
    #     「拿到 0 列一律當失敗，⛔ 不是『那年沒有休市日』」那條分支也逼出來。
    #   ⚠ 這兩條正是這一版要防的東西；沒被執行過的分支不算測過。
    SCHED_EMPTY = json.dumps({"stat": "ok", "title": "108 年市場開休市日期",
                              "fields": ["日期", "名稱", "說明"], "data": [],
                              "total": 0}, ensure_ascii=False).encode()
    SCHED_2021 = json.dumps({
        "stat": "ok", "title": "110 年市場開休市日期",
        "fields": ["日期", "名稱", "說明"],
        "data": [[f"2021-{m:02d}-01", "測試", "依規定放假1日。"]
                 for m in range(1, 13)],
    }, ensure_ascii=False).encode()

    def _fake_get(url, *a, **k):
        u = str(url)
        if "holidaySchedule" in u:
            if "date=20190101" in u:
                return SCHED_EMPTY, None      # ⇒ 逼出「0 列＝失敗」那一條
            if "date=20210101" in u:
                return SCHED_2021, None       # ⇒ 逼出「列數不在 20~27」那一條
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
    # ⭐⭐ 沙箱的低水位先**填一個很高的值**（9 年）。理由：
    #   ⛔ 不填的話這一趟是「第一次跑」⇒ 直接建檔、那道 check 根本不會被評估
    #   ⇒ 「閘門會不會紅」與「檔會不會被寫小」兩件事**一條都測不到**
    #     （實測：AB2／AB4 兩個突變在沒有這一段時**全綠**）。
    io.open(H.SCHED_LOW, "w", encoding="utf-8").write("9,2026-01-01\n")
    real_low = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "meta",
        "_holiday_years_low.txt")
    low_before = _stat(real_low)
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
        # ⚠ 逐年回補上線後這裡不再是 3 列：2026 的 3 列 ＋ 2021 的 12 列 ＝ 15 列。
        #   ⛔ 舊的 `== 4` 沒改的話會紅，而**紅得像程式壞了**，其實是測試過期。
        ck("假資料都併進去了（2026 三列 ＋ 2021 十二列）",
           len(sched.strip().splitlines()) == 16,
           f"實際 {len(sched.strip().splitlines())} 行（含表頭）")
        ck("同一天跑兩趟不會疊列（第二趟是覆蓋）",
           sched.count("2026-01-01") == 1, f"出現 {sched.count('2026-01-01')} 次")
        # ── ⛔ 逐年回補那三條「不可以把沒查到讀成沒有」的分支，要**真的印得出來** ──
        lr = io.open(_RL.PATH, encoding="utf-8").read()
        ck("⛔ 回 0 列的年份被判成失敗，不是「那年沒有休市日」",
           "回了 0 列" in lr and "不是「那年沒有休市日」" in lr, lr[-400:])
        ck("⛔ 端點忽略 date 參數時講得出來（而不是當成那年沒資料）",
           "端點忽略了 date 參數" in lr, lr[-400:])
        ck("⚠ 列數不在 20~27 時有標出來",
           "不在 20~27" in lr, lr[-400:])
        ck("★ 2021 那一年的列真的併進檔案了（不是只印訊息）",
           sched.count("2021-") == 12, f"實際 {sched.count('2021-')} 列")
        # ── ⭐⭐ 涵蓋率閘門的**執行期**三條（⛔ 上面 ⑨ 那幾條只測得到純函式）──
        # ⚠ 假資料只有 2021／2026 兩年 ⇒ 缺 2015~2020、2022~2025 共 10 年。
        ck("⭐ 缺的年份**逐年**印在 runlog 裡（⛔ 只報一個數字的話，"
           "沒有人知道要去補哪幾年）",
           "缺 10 年" in lr and "2015,2016,2017,2018,2019,2020" in lr,
           lr[-500:])
        _red = [ln for ln in lr.splitlines()
                if "✗" in ln and "行事曆涵蓋的年份數" in ln]
        ck("⭐⭐ 涵蓋率從 9 年掉到 2 年 ⇒ 那道 check **真的紅**"
           "（⛔ 只掃 AST 的話，改成 `True` 以外的假通過抓不到）",
           len(_red) == 1, f"掃到 {len(_red)} 行｜{lr[-500:]}")
        ck("⛔⛔ 而低水位檔**沒有被寫小**（⚠ 方向寫反 ⇒ 下一趟拿 2 當基準，"
           "這道閘門從此永遠綠）",
           io.open(H.SCHED_LOW, encoding="utf-8").read().startswith("9,"),
           io.open(H.SCHED_LOW, encoding="utf-8").read())
        # ⭐ 反向：涵蓋率**變多**時要真的上修（⛔ 否則「不會寫小」用「都不寫」
        #   就能通過，而那樣第一次跑之後低水位就凍住了）
        io.open(H.SCHED_LOW, "w", encoding="utf-8").write("1,2020-01-01\n")
        sys.argv = ["holiday.py", "--html",
                    os.path.join(d, "calm.html")]
        H.main()
        ck("⭐ 涵蓋率變多（1 → 2 年）⇒ 低水位真的上修",
           io.open(H.SCHED_LOW, encoding="utf-8").read().startswith("2,"),
           io.open(H.SCHED_LOW, encoding="utf-8").read())
    finally:
        H.OUT, H.ARCH = old_out, old_arch
        H.SCHED_CSV = old_sched
        H.SCHED_LOW = old_low
        _B.get = old_get
        _RL.PATH = old_rl
    # ⛔ 這一項要**真的去看檔案系統**，不是宣告自己沒事
    #   （上一版寫成 `… or True`，那等於永遠通過——比沒有這一項更糟）。
    after = _stat(real_lastrun)
    ck("★ 沒有動到 repo 真的 _last_run.md", before == after,
       f"mtime {before} → {after}")
    ck("★ 沒有動到 repo 真的 holiday_schedule.csv",
       sched_before == _stat(real_sched), f"{sched_before} → {_stat(real_sched)}")
    ck("★★ 沒有動到 repo 真的 _holiday_years_low.txt"
       "（⛔ 導走漏一個 ⇒ 假資料會把低水位寫小，而那道閘門從此永遠綠）",
       low_before == _stat(real_low), f"{low_before} → {_stat(real_low)}")

    print("\n⑨ ⭐⭐ 行事曆**涵蓋率**（2026-09-14 加：原本沒有任何閘門在管）")
    # ⛔ 起因：那一塊在報表上是 ✓ 正常，而 2015~2020 每天回 0 列、
    #   六年的交易日曆**沒有外部判準**在核，⚠ 而沒有人會被告知。
    have, miss = H.sched_year_coverage(["2021-01-01", "2022-02-28", "2026-12-25"])
    ck("⭐ 有資料的年份認得出來（2021／2022／2026）",
       have == {"2021", "2022", "2026"}, str(sorted(have)))
    ck("⭐ 缺的年份逐年列出來（⛔ 不是只報一個數字）",
       miss == ["2015", "2016", "2017", "2018", "2019", "2020",
                "2023", "2024", "2025"], str(miss))
    ck("⛔ 上界是**有資料的最大年**，不是今年"
       "（⚠ 否則每年 1 月 1 日會固定多出一個「缺今年」）",
       "2027" not in miss and "2026" not in miss)
    ck("⭐ 沒有缺口時回空 list",
       H.sched_year_coverage(["2015-01-01", "2016-06-06"])[1] == [])
    # ⭐ 有預設值的參數，一定要有一條**不傳它**的斷言（第七點③）
    ck("⭐ `first`／`last` 不傳 ⇒ 走預設（⛔ 這是 `main()` 唯一會走的路）",
       H.sched_year_coverage(["2021-01-01"])[1]
       == ["2015", "2016", "2017", "2018", "2019", "2020"])
    # ⛔ 低水位的方向：這一個存的是**最高**值（涵蓋越多越好），
    #   ⚠ 跟 `_factor_limit_low.txt` 存最低值方向**相反**
    # ⛔⛔ 這一層**不可以寫成無條件的斷言**：那個檔是 workflow 在 **main** 上建立的
    #   ⇒ 某些 ref 上它**必然不存在** ⇒ 斷言必然失敗 ⇒ daily.yml 的自測步驟紅掉
    #     ⇒ 排在它後面的 `holiday.py` 與同步／commit **整條被 skip**。
    #   ⚠ CLAUDE.md 六點五：「一條在某個環境下【必然】不成立的斷言，
    #     等於把那個環境的整條線關掉」——已經踩過「套件在不在」與「在哪個 ref」兩次，
    #     ⛔ 而我差一點用同一個形狀踩第三次。
    n, day = H.read_sched_low()
    if n is None:
        # ⭐ 這一行要寫成**不會被讀成「驗過了」**的樣子（⛔ 一行 skipped 跟 ok 長得一樣）
        print("  ⚠⚠ **這一層沒跑**：這個 ref 上沒有 `_holiday_years_low.txt`"
              "（⛔ 它由 workflow 在 main 上建立）⇒ 不算失敗，⛔ **也不算驗過**")
        # ⇒ 而「跳掉之後還有沒有人在守？」有：下面兩條 AST 呼叫點 ＋ 上面 ⑤ 節
        #   沙箱那四條執行期斷言**不依賴這個檔**，每一個 ref 都會跑。
    else:
        ck("⭐ 讀得到涵蓋率低水位（年數是整數、日期 10 碼）",
           isinstance(n, int) and len(day) == 10, f"{n},{day}")
        # ⛔ 判準是「**不小於**今天實測的 6 年」，⚠ 不是 `== 6`：
        #   涵蓋率變多時這個檔本來就會上修（那是好事），寫死 6 會在那一天假紅。
        #   ⭐ 而危險的方向是**變小**（靜靜變綠）——這一條擋的就是那個方向。
        ck("⭐ 而它不小於今天實測的 6 年（2021~2026）⛔ 被寫小 = 閘門從此永遠綠",
           n >= 6, str(n))
    # ⛔⛔ 上面七條測的是**純函式**，而那道閘門在 `main()` 的連網路徑裡
    #   ⇒ 自測走不到 ⇒ 把 `rl.check` 的條件改成 `True` 的突變**全綠**（實測 AB1）。
    #   ⚠ 「測了判準、沒測呼叫點」在本專案這是第三次（CLAUDE.md 第七點③）。
    #   ⇒ 這一條掃**原始碼的 AST**：那個 check 的條件真的是「不可以變少」嗎。
    import ast as _ast
    _src = io.open(os.path.join(HERE, "holiday.py"), encoding="utf-8").read()
    _cmp = [n2 for n2 in _ast.walk(_ast.parse(_src))
            if isinstance(n2, _ast.Compare)
            and isinstance(n2.ops[0], _ast.GtE)
            and isinstance(n2.left, _ast.Call)
            and getattr(n2.left.func, "id", "") == "len"
            and getattr(n2.left.args[0], "id", "") == "have"
            and getattr(n2.comparators[0], "id", "") == "low"]
    ck("⭐ 呼叫點真的是 `len(have) >= low`（⛔ 比 AST 不比字串）"
       "——⚠ 改成 True 的突變原本全綠",
       len(_cmp) == 1, f"掃到 {len(_cmp)} 處")
    # ⛔ 而 `rl.check` 真的有拿它當條件（⚠ 算出來卻沒接上去也是全綠）
    _chk = [n2 for n2 in _ast.walk(_ast.parse(_src))
            if isinstance(n2, _ast.Call)
            and getattr(n2.func, "attr", "") == "check"
            and len(n2.args) >= 2 and isinstance(n2.args[1], _ast.Compare)
            and isinstance(n2.args[1].ops[0], _ast.GtE)]
    ck("⭐ 而它真的被餵進 `rl.check` 的第二個引數（⛔ 算了不用也是全綠）",
       len(_chk) >= 1, f"掃到 {len(_chk)} 處")

    print()
    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
