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
REPO_MI = os.path.join(HERE, "data", "history", "market_index.csv")


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
    mi_before = io.open(REPO_MI, "rb").read() if os.path.isfile(REPO_MI) else None
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

        print("\n── 3.5 日曆落後於日檔要看得出來（K線線 2026-09-09 踩到的那個）──")
        # ⛔ 這一節在測的是**「三個 coverage 檔要 union」這件事有沒有被執行**。
        #   K線線只 union 了兩個，於是他們的窗口停在 09-03、而價格到 09-08，
        #   **閘門照跑、照回報通過**，只是看的窗裡沒有最近那幾天。
        #   ⇒ 假資料刻意做成「兩個舊、一個新」，只讀兩個就會得到舊答案。
        fake = os.path.join(tmp, "fakeroot")
        os.makedirs(os.path.join(fake, "universe", "daily"))
        _u = os.path.join(fake, "universe")
        for fn, last in (("_coverage.csv", "2026-09-03"),
                         ("_coverage_backfill.csv", "2026-09-01"),
                         ("_coverage_daily.csv", "2026-09-08")):
            with io.open(os.path.join(_u, fn), "w", encoding="utf-8") as f:
                f.write("date,twse,tpex,emerging,total,note\n")
                f.write(f"2026-09-01,1,1,0,2,\n{last},1,1,0,2,\n")
        for d in ("2026-09-01", "2026-09-08"):
            io.open(os.path.join(_u, "daily", d + ".csv"), "w").write("key\n")
        cov, last, pd = C.calendar_lag(fake)
        chk("三個檔各自的最後一天都讀得到", len(cov) == 3 and "（不存在）" not in cov.values(),
            str(cov))
        chk("★ union 取的是最新那一個（＝只讀兩個會拿到 09-03，是錯的）",
            last == "2026-09-08", f"union {last}")
        chk("日檔最後一天讀得到", pd == "2026-09-08", pd)
        chk("★ 沒落後時斷言成立", last >= pd, f"日曆 {last}｜日檔 {pd}")
        # ⛔ **證明它會失敗**：把最新那個 coverage 檔拿掉（＝模擬「只讀兩個」），
        #   斷言就該當場不成立。沒證明過會失敗的測試不算測試。
        os.remove(os.path.join(_u, "_coverage_daily.csv"))
        cov2, last2, pd2 = C.calendar_lag(fake)
        chk("★★ 少讀一個檔時斷言**真的會不成立**（否則這一節是裝飾）",
            last2 == "2026-09-03" and not (last2 >= pd2),
            f"union {last2}｜日檔 {pd2} ⇒ 落後 ⇒ 斷言為假")

        print("\n── 5. ⭐⭐ 收盤指數：照欄名取，⛔ 只取那一欄 ──")
        # 真回應的形狀（2026-09-14 probe run 77 逐字抄回來的）
        F = ["日期", "成交股數", "成交金額", "成交筆數",
             "發行量加權股價指數", "漲跌點數"]
        R = ["115/09/01", "13,000,849,196", "1,187,571,567,117",
             "5,301,801", "46,948.72", "820.25"]
        chk("⭐ 取得到收盤指數，而且千分位逗號被拿掉",
            C.index_of_row(F, R) == "46948.72", C.index_of_row(F, R))
        chk("⭐⭐ **照欄名**取，⛔ 不是位置（欄序換掉照樣要對）",
            C.index_of_row(["日期", "發行量加權股價指數"],
                           ["115/09/01", "46,948.72"]) == "46948.72")
        chk("⛔ 反向：沒有那個欄名時回空字串（⛔ 不是硬取 [4]）",
            C.index_of_row(["日期", "成交金額", "X", "Y", "Z"],
                           ["115/09/01", "1", "2", "3", "9999"]) == "")
        chk("⛔ 破折號／空值不可以變成 0（0 是一個指數值，空不是）",
            C.index_of_row(F, ["115/09/01", "", "", "", "--", ""]) == ""
            and C.index_of_row(F, ["115/09/01", "", "", "", "", ""]) == "")
        chk("⛔ 非數字不可以放行", C.index_of_row(F, R[:4] + ["休市", ""]) == "")

        print("\n── 6. ⭐⭐ 寫入端：重疊的日子是**閘門**，⛔ 不是跳過就算 ──")
        _mi = os.path.join(tmp, "market_index.csv")
        io.open(_mi, "w", encoding="utf-8").write(
            "date,close,change,change_pct\n"
            "2026-09-01,46948.72,820.25,1.78\n"
            "2026-09-02,46543.61,-405.11,0.86\n")
        _before = io.open(_mi, "rb").read()
        # ① 重疊相符 ＋ 有新日子 ⇒ 只寫新的，⛔ 舊的一列都不動
        n1, m1 = C.write_index({"2026-09-01": "46948.72", "2026-09-02": "46543.61",
                                "2015-01-05": "9274.11"}, path=_mi)
        rows = {l.split(",")[0]: l for l in
                io.open(_mi, encoding="utf-8").read().splitlines()[1:] if l.strip()}
        chk("⭐ 只補了沒有的那一天", n1 == 1 and "2015-01-05" in rows, f"{n1}｜{m1}")
        chk("⛔⛔ 而既有那兩列**逐字沒變**（change／change_pct 沒有被洗成空白）",
            rows.get("2026-09-01") == "2026-09-01,46948.72,820.25,1.78"
            and rows.get("2026-09-02") == "2026-09-02,46543.61,-405.11,0.86",
            str([rows.get("2026-09-01"), rows.get("2026-09-02")]))
        chk("⭐ 新那列的 change／change_pct 是**空的**"
            "（⛔ 不是 0、⛔ 也不是自己乘出來的）",
            rows.get("2015-01-05") == "2015-01-05,9274.11,,", rows.get("2015-01-05"))
        # ② ⛔⛔ 對不上 ⇒ **一列都不寫**（這一條是本節的主角）
        io.open(_mi, "w", encoding="utf-8").write(_before.decode("utf-8"))
        n2, m2 = C.write_index({"2026-09-01": "46948.73",      # ⚠ 差 0.01
                                "2015-01-05": "9274.11"}, path=_mi)
        chk("⛔⛔ 重疊那天對不上 ⇒ 回 -1 並講出兩邊的值",
            n2 == -1 and "46948.73" in m2 and "46948.72" in m2, f"{n2}｜{m2}")
        chk("⛔⛔ 而檔案**逐位元沒變**（⚠ 只看回傳值不夠——"
            "那個新日子本來是可以寫進去的）",
            io.open(_mi, "rb").read() == _before)
        # ③ 全部重疊且相符 ⇒ no-op（⛔ 否則它會天天產生 commit）
        n3, m3 = C.write_index({"2026-09-01": "46948.72"}, path=_mi)
        chk("⭐ 全部重疊且相符 ⇒ 0 列、no-op", n3 == 0 and "沒有新的日子" in m3, m3)
        chk("⛔ 而 no-op 也不可以動到檔案",
            io.open(_mi, "rb").read() == _before)
        # ④ ⭐ 呼叫點：main() 真的把 --write-index 接到 write_index
        #   （第七點第三個陷阱：測了純函式、沒測呼叫點）
        _src = io.open(os.path.join(HERE, "calendar_audit.py"),
                       encoding="utf-8").read()
        chk("⭐ main() 真的有 `--write-index` 這個參數",
            '"--write-index"' in _src)
        chk("⭐⭐ 而它接到 `write_index(idx_all)`，"
            "並且結果進了 `rl.check`（⛔ 只寫 rl.info 的話對不上也不會紅）",
            "write_index(idx_all)" in _src
            and "rl.check(\"⭐ 收盤指數與我方既有值對得上" in _src)

        print("\n── 7. ⭐⭐ `--index-only`：呼叫點與那條**會刪資料**的組合 ──")
        # ⛔ 純函式測不到這兩件，而它們都在 main()／workflow 裡（第七點第三個陷阱）。
        _src = io.open(os.path.join(HERE, "calendar_audit.py"),
                       encoding="utf-8").read()
        chk("⭐ `--index-only` 這個參數存在", '"--index-only"' in _src)
        chk("⭐⭐ 而它真的把「官方有我方沒有」那條 check **關掉**"
            "　（⚠ 我方日檔只有 2015 起，比 1990 年代必然全紅）",
            "if a.index_only:" in _src
            and _src.index("if a.index_only:\n        # ⛔ 不是「通過」")
                < _src.index('rl.check("官方有、我方沒有的日子為 0'))
        chk("⛔ 而它要講出「**沒比**」，⚠ 不可以只是安靜跳過"
            "（『沒比』跟『比對通過』在 runlog 裡長得一樣）",
            "**沒有做日曆比對**" in _src and "不是比對通過" in _src)
        chk("⛔ 回傳碼不可以被那個無意義的 miss 決定",
            "miss and not a.index_only" in _src)
        # ⛔⛔ 這一條是本節的主角：--index-only 配 --replace 會**洗掉整份日曆**
        _wf = io.open(os.path.join(HERE, ".github", "workflows", "feeds.yml"),
                      encoding="utf-8").read()
        _blk = _wf[_wf.index('cal_index_only'):]
        _blk = _blk[_blk.index('ARGS="--start'):][:900]
        _io_branch = _blk[_blk.index('cal_index_only }}" = "true"'):]
        _io_branch = _io_branch[:_io_branch.index("else")]
        # ⚠ 先濾掉**註解行**再比：那一支的註解裡本來就寫著「不可以帶 --replace」
        #   ⇒ ⛔ 直接 `in` 會抓到說明文字（第七點：斷言要比帶標籤的整串，
        #     不是一個裸字串）。第一版就是這樣假紅的。
        _io_code = "\n".join(x for x in _io_branch.splitlines()
                             if not x.strip().startswith("#"))
        chk("⛔⛔ workflow 的 index-only 那一支**沒有** `--replace`"
            "　（⚠ `--replace` 是整份重建 ⇒ 拿兩個月跑一趟會把 2,851 天洗成 2 個月）",
            "--replace" not in _io_code and "--index-only" in _io_code,
            _io_code.strip()[:120])
        chk("⭐ 而非 index-only 那一支**仍然**有 --write --replace（⛔ 別修壞原本的路）",
            "--write --replace" in _blk)

        print("\n── 4. 沒有碰到 repo ──")
        cal_after = io.open(REPO_CAL, "rb").read() if os.path.isfile(REPO_CAL) else None
        chk("★ repo 的 calendar_twse.csv 逐位元沒變", cal_before == cal_after)
        _repo_mi = os.path.join(HERE, "data", "history", "market_index.csv")
        chk("★★ 沒有動到 repo 真的 data/history/market_index.csv",
            io.open(_repo_mi, "rb").read() == mi_before
            if mi_before is not None else not os.path.exists(_repo_mi))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
