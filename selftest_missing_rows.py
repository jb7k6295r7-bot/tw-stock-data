#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_missing_rows.py — 離線驗 missing_rows.scan()。**不碰真的 data/。**

⛔ 這一支要防的四件事，每一件都對應一個 fixture：

  ① 官方清單有、日檔沒有 ⇒ **要抓到**
  ② 官方清單**檔案不存在** ⇒ ⛔ 不可以當成「那天官方沒有這些檔」
     （那會把「我沒存」讀成「它沒有」——今晚這個形狀已經出現十幾次）
  ③ ETF／權證不算：`kind != stock` 的要濾掉，否則數字虛胖
  ④ `sources` 欄要講得出是**哪一張清單**指認的
"""
import io
import os
import shutil
import sys
import tempfile

import missing_rows as M

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def w(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")


def build(root):
    uni = os.path.join(root, "data", "universe")
    w(os.path.join(root, "data", "meta", "stocks.csv"),
      "stock_id,name,market,kind,first_seen,last_seen",
      [["2330", "台積電", "twse", "stock", "2015-01-05", "2026-09-08"],
       ["6904", "伯鑫", "tpex", "stock", "2018-01-02", "2026-09-08"],
       ["8921", "沈氏", "tpex", "stock", "2015-01-05", "2026-09-08"],
       ["0050", "元大台灣50", "twse", "etf", "2015-01-05", "2026-09-08"]])
    # ⭐ 8921 在 09-01 官方公告暫停交易 ⇒ 那一筆漏列要被歸因；6904 沒有 ⇒ 要留空
    w(os.path.join(root, "data", "meta", "suspend_twse.csv"),
      "stock_id,name,susp_date,susp_time,resume_date,resume_time,days",
      [["8921", "沈氏", "2026-09-01", "8:00", "2026-09-02", "8:00", "1"]])
    DH = ("key,date,stock_id,name,market,open,high,low,close,volume,amount,"
          "change,limit,shares,transactions,price_basis")
    # D1：2330 與 0050 有成交；6904／8921 沒有 ⇒ 日檔裡沒有它們
    w(os.path.join(uni, "daily", "2026-09-01.csv"), DH,
      [[f"2026-09-01_{c}", "2026-09-01", c, "N", m, 1, 1, 1, 1, 1, 1, 0,
        "", "", 1, ""] for c, m in (("2330", "twse"), ("0050", "twse"))])
    # D2：四檔都有成交 ⇒ 一筆都不該漏
    w(os.path.join(uni, "daily", "2026-09-02.csv"), DH,
      [[f"2026-09-02_{c}", "2026-09-02", c, "N", m, 1, 1, 1, 1, 1, 1, 0,
        "", "", 1, ""] for c, m in (("2330", "twse"), ("0050", "twse"),
                                    ("6904", "tpex"), ("8921", "tpex"))])
    # D3：只有 2330 ⇒ 但這一天**六張官方清單一張都沒存**
    #     ⛔ 必須整天跳過，不可以算成「漏了 3 檔」
    w(os.path.join(uni, "daily", "2026-09-03.csv"), DH,
      [["2026-09-03_2330", "2026-09-03", "2330", "N", "twse", 1, 1, 1, 1,
        1, 1, 0, "", "", 1, ""]])
    PR = "date,stock_id,close,yield_pct,dividend_year,per,pbr,fs_quarter"
    IN = "date,stock_id,foreign,trust,dealer,total"
    for d in ("2026-09-01", "2026-09-02"):
        # otcper：列 6904 與 8921（掛牌中，不管有沒有成交）
        w(os.path.join(uni, "otcper", d + ".csv"), PR,
          [[d, c, "", 0, 114, 0, 0, "115Q2"] for c in ("6904", "8921")])
        # otcinst：只列 8921（法人有交易 ⇒ **鐵證**）
        w(os.path.join(uni, "otcinst", d + ".csv"), IN,
          [[d, "8921", 1, 0, 0, 1]])
        # per：列 2330 與 0050（0050 是 etf，⛔ 不該被算進去）
        w(os.path.join(uni, "per", d + ".csv"), PR,
          [[d, c, 100, 1, 114, 10, 1, "115/2"] for c in ("2330", "0050")])


def main():
    real = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    before = os.path.isdir(real)
    root = tempfile.mkdtemp(prefix="misrows_")
    try:
        build(root)
        rows, byday, bysrc, n_cmp = M.scan(root=root)
        got = {(r[0], r[1]): r[4] for r in rows}
        got_why = {(r[0], r[1]): r[5] for r in rows}
        print("  scan →", rows, "｜byday", byday, "｜bysrc", bysrc, "｜可比", n_cmp)
        ck("① 官方有、日檔沒有 ⇒ 09-01 抓到 6904 與 8921",
           ("2026-09-01", "6904") in got and ("2026-09-01", "8921") in got,
           str(sorted(got)))
        ck("① 09-02 四檔都有成交 ⇒ 一筆都不漏", byday.get("2026-09-02") == 0,
           f"byday={byday}")
        ck("② 官方清單整天沒存的 09-03 ⛔ 整天跳過（不是算成漏 3 檔）",
           "2026-09-03" not in byday and n_cmp == 2, f"byday={byday} n_cmp={n_cmp}")
        ck("③ 0050 是 etf ⇒ 不算（否則數字虛胖）",
           not any(r[1] == "0050" for r in rows), str(rows))
        # ⭐ 歸因欄：官方那天公告暫停交易的，要標出來；沒有的要留空。
        #   ⛔ 這一項要**兩個方向都驗**——只驗「標得出來」的話，
        #     一個「全部都標成暫停交易」的 bug 也會通過。
        ck("⑤ 官方暫停交易那一筆有標出來",
           got_why.get(("2026-09-01", "8921")) == "官方暫停交易", str(got_why))
        ck("⑤ ⛔ 沒有暫停紀錄的那一筆**留空**（不是全部都標）",
           got_why.get(("2026-09-01", "6904")) == "", str(got_why))
        ck("④ sources 講得出是哪一張清單指認的",
           got.get(("2026-09-01", "8921")) == "otcper+otcinst"
           and got.get(("2026-09-01", "6904")) == "otcper",
           str(got))
        # ⚠ 這裡我第一次寫成 `== 2`，**錯的是我不是程式**：
        #   09-02 那天四檔都在日檔裡 ⇒ otcinst 指認不到任何一筆。
        #   ⇒ 只有 09-01 的 8921 一筆。⛔ 期望值也要自己先算過。
        ck("⭐ 鐵證（otcinst）有被單獨數出來（只有 09-01 的 8921）",
           bysrc.get("otcinst") == 1, str(bysrc))
        # ── 反向驗：把 otcper 那兩天的檔刪掉，漏列數必須**變少**（不是不變）──
        #   ⛔ 沒有這一項的話，「掃不到來源」與「來源說沒漏」會長得一模一樣。
        for d in ("2026-09-01", "2026-09-02"):
            os.remove(os.path.join(root, "data", "universe", "otcper", d + ".csv"))
        rows2, _b2, _s2, _n2 = M.scan(root=root)
        ck("★ 拿掉一張官方清單，抓到的筆數會變少（證明它真的在用那張清單）",
           len(rows2) < len(rows), f"{len(rows)} → {len(rows2)}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    ck("★ 沒有動到 repo 真的 data/", os.path.isdir(real) == before)

    # ══════════════════════════════════════════════════════════════
    # ⑥ ⭐⭐ `excuse()`：兩個歸因來源，⛔ 而它們的**可及範圍完全不同**
    #
    # ⚠ 2026-09-15 量到：只用 `suspend_twse.csv` 時整欄是 **0／6,799**，
    #   ⛔ 而那是**結構上**的 0（那張表只有上市；而被停牌的證券也會從
    #   六張清單上消失 ⇒ 進不了母體）。
    #   ⇒ 加上 `halt_spans.csv`（上櫃 chtm）之後：**2,958／6,799**（43.5%），
    #     上櫃那一半 **88.6%**。
    #
    # ⭐ 判準拿**合成**資料驗（環境無關，第七點⑦），
    #   ⛔ 不拿現場那 6,799 筆——那個數字會變，而斷言的壽命不該綁在它上面。
    # ══════════════════════════════════════════════════════════════
    print("\n── ⑥ `excuse()`：兩個來源、兩種範圍（合成資料）──")
    _susp = {("1101", "2026-03-04")}
    _spans = {"6129": [("2026-09-03", "2026-09-11")]}
    ck("⭐ 上市名單命中那一天 ⇒ 「官方暫停交易」",
       M.excuse("1101", "2026-03-04", _susp, _spans) == "官方暫停交易",
       M.excuse("1101", "2026-03-04", _susp, _spans))
    ck("⛔ 差一天就不算（那張表是**逐日**的，不是區間）",
       M.excuse("1101", "2026-03-05", _susp, _spans) == "",
       M.excuse("1101", "2026-03-05", _susp, _spans))
    ck("⭐⭐ 上櫃停止交易是**區間** ⇒ 區間**中間**那一天也要命中"
       "（⛔ 這就是只比起始日時整欄 0 的原因）",
       M.excuse("6129", "2026-09-08", _susp, _spans) == "官方停止交易",
       M.excuse("6129", "2026-09-08", _susp, _spans))
    ck("  兩個端點都算在內（閉區間）",
       M.excuse("6129", "2026-09-03", _susp, _spans) == "官方停止交易"
       and M.excuse("6129", "2026-09-11", _susp, _spans) == "官方停止交易")
    ck("⛔ 區間外不算",
       M.excuse("6129", "2026-09-12", _susp, _spans) == ""
       and M.excuse("6129", "2026-09-02", _susp, _spans) == "")
    ck("⛔ 沒有任何來源說得出理由 ⇒ **留空**（⚠ 不是隨便給一個）",
       M.excuse("9999", "2026-09-08", _susp, _spans) == "")
    # ⛔ 兩個來源同時命中時，要回**上市那個**（先問逐日、再問區間）——
    #   ⚠ 這一條釘的是**順序是定死的**，⛔ 不是「反正都算歸因」：
    #   兩個字串進了逐筆 CSV 的 `why` 欄，下游會照字串分類。
    ck("⭐ 兩個都命中時，回傳是**定死的那一個**（⛔ 不隨字典順序飄）",
       M.excuse("1101", "2026-03-04", {("1101", "2026-03-04")},
                {"1101": [("2026-03-01", "2026-03-31")]}) == "官方暫停交易")

    # ⭐ 而**讀檔那一層**也要驗：`_halt_spans` 讀不到檔要回空字典，
    #   ⛔ 不是炸掉——⚠ 分支上可能根本沒有那個檔（四點六那條）。
    _d = tempfile.mkdtemp(prefix="mr_halt_")
    try:
        os.makedirs(os.path.join(_d, "meta"))
        ck("⛔ 沒有 halt_spans.csv ⇒ 回空字典（⚠ 不是例外）",
           M._halt_spans(_d) == {})
        io.open(os.path.join(_d, "meta", "halt_spans.csv"), "w",
                encoding="utf-8").write(
            "market,stock_id,start,end,days,open_ended\n"
            "tpex,6129,2026-09-03,2026-09-11,7,1\n")
        ck("⭐ 讀得到就要解出那一段", M._halt_spans(_d)
           == {"6129": [("2026-09-03", "2026-09-11")]}, str(M._halt_spans(_d)))
    finally:
        shutil.rmtree(_d, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 判準換了：從「總筆數不得高於歷史最低值」換成
    #   「**以前好好的那一天變差了**才算退步」（2026-09-14）
    #
    # ⛔⛔ 為什麼要換——原本那個總數**只會單調增加**：
    #
    #     11:07Z 那趟   6,799 筆 ／ 可比 2,850 天   ✓ 綠
    #     16:22Z 那趟   6,807 筆 ／ 可比 2,851 天   ✗ 紅
    #
    #   差別只是**多了一個可比日**（當天的融資融券傍晚才發），
    #   而每個交易日固定多 2~9 筆（09-08:4、09-10:9、09-11:9、09-14:8）
    #   ⇒ ⛔ 從那天起它**每個交易日都紅**，然後被學會忽略（六點五）。
    # ══════════════════════════════════════════════════════════════
    print("\n[N] ⭐⭐ 新的日子多幾筆**不算**退步，既有的日子變差才算")
    OLD = {"2026-09-10": 9, "2026-09-11": 9}
    ck("新增一天（09-14 八筆）⇒ 沒有退步",
       M.day_regressions({**OLD, "2026-09-14": 8}, OLD) == [],
       str(M.day_regressions({**OLD, "2026-09-14": 8}, OLD)))
    ck("  ⭐ 新那天就算很多筆（999）也一樣不算",
       M.day_regressions({**OLD, "2026-09-14": 999}, OLD) == [])
    ck("  ⭐⭐ 而這正是原本那道閘門紅掉的那一組（總數變大、但沒有退步）",
       sum({**OLD, "2026-09-14": 8}.values()) > sum(OLD.values())
       and M.day_regressions({**OLD, "2026-09-14": 8}, OLD) == [])
    ck("⛔ 09-10 從 9 變 12 ⇒ 抓到，而且講得出舊值與新值",
       M.day_regressions({"2026-09-10": 12, "2026-09-11": 9}, OLD)
       == [("2026-09-10", 9, 12)],
       str(M.day_regressions({"2026-09-10": 12, "2026-09-11": 9}, OLD)))
    # ⚠ 這一組原本是 09-10 與 09-11 同時變差 ⇒ 期待 2 筆。
    #   ⛔ 而 2026-09-16 加了「上一份快照裡**最新**那一天不可比」之後，
    #   09-11（= max(OLD)）被讓掉 ⇒ 只剩 1 筆。
    #   ⇒ ⭐ 母體要往前挪一天才測得到「兩天同時變差」這件事本身。
    OLD3 = {"2026-09-10": 9, "2026-09-11": 9, "2026-09-12": 9}
    ck("  ⭐ 兩天同時變差 ⇒ 兩筆都列出來（⚠ 09-12 是沉澱中那天，不算）",
       len(M.day_regressions({"2026-09-10": 10, "2026-09-11": 11,
                              "2026-09-12": 99}, OLD3)) == 2,
       str(M.day_regressions({"2026-09-10": 10, "2026-09-11": 11,
                              "2026-09-12": 99}, OLD3)))

    # ── ⭐⭐ 「上一份快照裡最新的那一天」不可比（2026-09-16 加）──
    #
    # ⛔ 實際代價：2026-09-15 那晚被判成「1 天變差」，⚠ 而什麼都沒變差
    #   11:26Z（台北 19:26）0 筆 ← 官方融資融券清單還沒發完
    #   16:24Z（台北 00:24）8 筆 ← 同一晚第二班，清單齊了
    # ⭐ 病根：「第一次出現」與「官方清單第一次完整」是兩件事，
    #   而上面 [N] 那一節只擋掉了第一種。
    print("\n[N2] ⭐⭐ 上一份快照裡**最新**那一天不可比（清單還在沉澱）")
    OLD4 = {"2026-09-11": 3, "2026-09-12": 4, "2026-09-15": 0}
    ck("⭐ 09-15（= 上一份的最新那天）0 → 8 ⇒ **不算退步**"
       "（⚠ daily.yml 一天兩班，當天必定被量兩次）",
       M.day_regressions({**OLD4, "2026-09-15": 8, "2026-09-16": 2}, OLD4) == [],
       str(M.day_regressions({**OLD4, "2026-09-15": 8, "2026-09-16": 2}, OLD4)))
    ck("⛔ 而**更早**那幾天變差照樣抓（⇒ 這不是把閘門關掉）",
       M.day_regressions({**OLD4, "2026-09-11": 9, "2026-09-15": 8}, OLD4)
       == [("2026-09-11", 3, 9)],
       str(M.day_regressions({**OLD4, "2026-09-11": 9, "2026-09-15": 8}, OLD4)))
    ck("⭐ ③ 還有誰在守：**隔天那一趟** 09-15 不再是最新那天 ⇒ 真的退步會紅",
       M.day_regressions({"2026-09-15": 8, "2026-09-16": 5},
                         {"2026-09-15": 2, "2026-09-16": 5})
       == [("2026-09-15", 2, 8)],
       str(M.day_regressions({"2026-09-15": 8, "2026-09-16": 5},
                             {"2026-09-15": 2, "2026-09-16": 5})))
    ck("⛔ 而它只讓掉**一天**（⚠ 不是「最近幾天」）",
       M.day_regressions({"2026-09-11": 9, "2026-09-12": 9, "2026-09-15": 8},
                         {"2026-09-11": 3, "2026-09-12": 4, "2026-09-15": 0})
       == [("2026-09-11", 3, 9), ("2026-09-12", 4, 9)])
    ck("  ⛔ 舊快照是空的 ⇒ 沒有「最新那天」可讓 ⇒ 一筆都不算退步",
       M.day_regressions({"2026-09-15": 8}, {}) == [])
    ck("⭐ 反向：既有日子**變好**不算退步（⇒ 補好東西不可以假紅）",
       M.day_regressions({"2026-09-10": 3, "2026-09-11": 9}, OLD) == [])
    ck("⭐ 反向：完全一樣 ⇒ 沒有退步", M.day_regressions(dict(OLD), OLD) == [])
    ck("⛔ 沒有上一趟的計數 ⇒ 回空 list（⚠ 不是全部當成退步）",
       M.day_regressions({"2026-09-10": 9}, {}) == [])

    print("\n[N2] `read_byday`：讀得回來、壞了不炸")
    d2 = tempfile.mkdtemp()
    try:
        pth = os.path.join(d2, "by_day.csv")
        io.open(pth, "w", encoding="utf-8").write(
            "date,missing\n2026-09-10,9\n2026-09-11,9\n")
        ck("讀得回 2 天",
           M.read_byday(pth) == {"2026-09-10": 9, "2026-09-11": 9})
        io.open(pth, "w", encoding="utf-8").write(
            "date,missing\n2026-09-10,9\n2026-09-11,壞掉\n")
        ck("  ⛔ 壞掉那一列跳過，其餘照讀（⚠ 不是整份丟掉）",
           M.read_byday(pth) == {"2026-09-10": 9})
        ck("  檔不存在 ⇒ {}（⛔ 不是炸掉）",
           M.read_byday(os.path.join(d2, "沒這個檔.csv")) == {})
    finally:
        shutil.rmtree(d2, ignore_errors=True)

    print("\n[N3] ⭐ 原始碼：判準真的換了，而總數**還在報表上**")
    import ast as _a
    src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "missing_rows.py"), encoding="utf-8").read()
    tree = _a.parse(src)
    _checks = [n for n in _a.walk(tree)
               if isinstance(n, _a.Call) and getattr(n.func, "attr", "") == "check"]
    ck("⭐⭐ 有一條 check 用的是 `day_regressions` 的結果",
       any("_reg" in _a.dump(c.args[1]) for c in _checks if len(c.args) >= 2))
    ck("⛔ 而**沒有**任何一條 check 還在拿總筆數比低水位（⚠ 留著等於沒換）",
       "lowwater.gate" not in src)
    _infos = [n for n in _a.walk(tree)
              if isinstance(n, _a.Call) and getattr(n.func, "attr", "") == "info"]
    ck("⭐ 總筆數與歷史最低值仍然 `rl.info` 出來（⛔ 換判準 ≠ 把數字藏起來）",
       any("漏列總筆數" in _a.dump(i) for i in _infos))
    ck("  ⭐ 而那一行要講出**它為什麼不能當判準**（⚠ 否則下一個人會改回去）",
       "只會單調增加" in src)
    _read_ln = next((n.lineno for n in _a.walk(tree)
                     if isinstance(n, _a.Call)
                     and getattr(n.func, "id", "") == "read_byday"), None)
    _open_ln = next((n.lineno for n in _a.walk(tree)
                     if isinstance(n, _a.Call)
                     and getattr(n.func, "attr", "") == "open"
                     and any(getattr(x, "id", "") == "SUM" for x in n.args)), None)
    ck("⭐⭐ `read_byday(SUM)` 排在覆蓋 `SUM` **之前**"
       "（⛔ 之後就再也問不到昨天是幾筆）",
       _read_ln is not None and _open_ln is not None and _read_ln < _open_ln,
       f"read 第 {_read_ln} 行、open 第 {_open_ln} 行")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
