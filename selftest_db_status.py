#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""db_status.py 的自測。造一個假的 data/ 再跑，**不連網、不碰 repo 的 data/**。

要釘住的是這一支特有的失效模式：**它是「回答缺什麼」用的，
所以「檔不存在」與「檔是空的」都必須被說出來，不可以安靜跳過**——
不然它會變成另一種循環自證：沒印出來的就當成沒問題。
"""
import csv
import io
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILED = []
DATA_BEFORE = os.path.exists(os.path.join(HERE, "data"))


def ck(cond, msg):
    print(("  ok   " if cond else "  ✗ 失敗 ") + msg)
    if not cond:
        FAILED.append(msg)


def w(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        c = csv.writer(f)
        c.writerow(header)
        for r in rows:
            c.writerow(r)


def run(tmp):
    import importlib
    import db_status as D
    importlib.reload(D)
    D.DATA = os.path.join(tmp, "data")
    D.META = os.path.join(D.DATA, "meta")
    D.OUT = os.path.join(D.META, "_db_status.md")
    sys.argv = ["db_status.py"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        D.main()
    return buf.getvalue()


def main():
    print("=" * 60)
    print("db_status.py 自測（不連網）")
    print("=" * 60)

    print("\n[1] 空資料庫：缺什麼都要講出來，不可以安靜跳過")
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "data", "meta"))
        t = run(tmp)
        ck("0（檔不存在或空的）" in t, "★ 事件三檔不存在時明講，不是略過不印")
        ck("沒有任何一支腳本用新版跑過" in t, "★ `_last_run.md` 不存在時明講")
        ck("★ 少於預期" in t, "★ 各層是 0 檔時被標成少於預期")
        ck("集保" in t, "沒有來源的清單有印出來")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n[2] 有資料：異常要被標出來，正常的不要亂標")
    tmp = tempfile.mkdtemp()
    try:
        d = os.path.join(tmp, "data")
        m = os.path.join(d, "meta")
        w(os.path.join(m, "capital.csv"),
          ["stock_id", "name", "market", "capital", "shares", "par", "source",
           "asof", "note"],
          [["2330", "台積電", "twse", "1", "1", "10", "s", "d", "ok"],
           ["5314", "世紀*", "tpex", "1", "1", "10", "s", "d", "mismatch:0.5"],
           ["9103", "美德醫療-DR", "twse", "1", "1", "10", "s", "d", "mismatch:1.5"],
           ["1234", "正常股", "tpex", "1", "1", "10", "s", "d", "mismatch:7.0"],
           ["4321", "沒股本", "tpex", "", "9", "", "s", "d", "feed-shares"]])
        w(os.path.join(m, "attention.csv"),
          ["stock_id", "name", "market", "sec_kind", "date", "count", "reason",
           "close", "per", "source", "asof"],
          [["2330", "台積電", "twse", "普通股", "2026-09-01", "1", "r", "", "",
            "s", "d"],
           ["8299", "群聯", "tpex", "普通股", "", "1", "r", "", "", "s", "d"]])
        t = run(tmp)
        ck("**其中 1 檔不帶 `*` 也不是 DR ★ 要查**" in t,
           "★ 只有 1234 被標成要查（世紀* 與 DR 不算）")
        ck("★ 空日期 1" in t, "★ 空日期的列被標出來")
        ck("股本空白 1" in t, "上櫃股本空白數有算對")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n[3] 沒有動到 repo 的 data/")
    ck(DATA_BEFORE == os.path.exists(os.path.join(HERE, "data")),
       "★ repo 的 data/ 存在與否沒有改變")

    print("\n── `data/universe/` 自動列舉 ──")
    _ok, _fail = _universe_dirs_section()
    if _fail:
        FAILED.append(f"universe_dirs 有 {_fail} 項失敗")

    print("\n── `shares` 兩條前緣（⛔ 每趟重算，不手抄）──")
    _ok, _fail = _shares_frontier_section()
    if _fail:
        FAILED.append(f"shares_frontier 有 {_fail} 項失敗")

    print("\n" + "=" * 60)
    if FAILED:
        print(f"✗ {len(FAILED)} 項失敗：")
        for x in FAILED:
            print("   -", x)
        return 1
    print("全部通過")
    return 0




def _shares_frontier_section():
    """⭐ `shares` 兩條前緣：**每趟重算**，⛔ 不是手抄的日期。

    ## 這一節在釘什麼（2026-09-10 情報分析線來信）

    來信給了兩個手抄的日期（`universe/daily` 至 2023-12-31、
    `data/stocks` 至 2018-12-31），並說中間那段不一致是預期的。
    ⚠ 手抄的**會過期，而且過期的方向通常是「看起來比實際好」**。
    ⇒ 所以要釘的不是那兩個日期，是**算法**：

      ① 逐市場算（⛔ 整格是空的會被別格的高填值率蓋掉）
      ② 「不一致」只在**兩邊都有那一天**時成立
         ⛔ 個股庫還沒轉置到那一天 ≠ shares 不一致
      ③ `shares` 是 `"0"` 算**沒有**（0 股是「沒填」的另一種寫法）
      ④ 日檔的 `date` 欄跟檔名不同 ⇒ 要被數出來（第二點：靜靜回了別天）
    """
    import io as _io
    import os as _o
    import shutil as _sh
    import tempfile as _tf
    import db_status as D

    ok = fail = 0

    def ck(name, cond, hint=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ok   {name}")
        else:
            fail += 1
            print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))

    d = _tf.mkdtemp(prefix="dbshare_")
    try:
        dy = _o.path.join(d, "daily")
        st = _o.path.join(d, "stocks")
        _o.makedirs(dy)
        _o.makedirs(st)

        # ── 假資料的形狀照真的做（CLAUDE.md 七：假的比真的簡單＝那段沒測）──
        # 日檔：四天。tpex 兩檔都有 shares；twse 一律空；
        #       ⚠ 第三天 tpex 的 shares 是 "0" ⇒ **算沒有**
        H = "key,date,stock_id,name,market,close,shares"
        # ⚠ 第一天 tpex 的 shares 是**空的** ⇒ 「有值的區間」起點是 09-01，
        #   ⛔ 不是 08-31。沒有這一天，`min(有值)` 與 `min(全部)` 會剛好一樣，
        #   那條斷言就永遠分不出對錯（2026-09-11 突變驗當場抓到）。
        days = ["2026-08-31", "2026-09-01", "2026-09-02",
                "2026-09-03", "2026-09-04"]
        for i, day in enumerate(days):
            sh = {"2026-08-31": "", "2026-09-03": "0"}.get(day, "1000")
            _io.open(_o.path.join(dy, day + ".csv"), "w", encoding="utf-8").write(
                H + "\n"
                + f"{day}_6488,{day},6488,環球晶,tpex,100,{sh}\n"
                + f"{day}_2330,{day},2330,台積電,twse,900,\n")
        # ⛔ 第四天的 `date` 欄故意寫成別天 ⇒ ④ 要數到
        p4 = _o.path.join(dy, "2026-09-04.csv")
        _io.open(p4, "w", encoding="utf-8").write(
            H + "\n"
            "2026-09-03_6488,2026-09-03,6488,環球晶,tpex,100,1000\n"
            "2026-09-03_2330,2026-09-03,2330,台積電,twse,900,\n")

        # 個股庫：⚠ 只轉置到 09-03（**還沒追上** 09-04）
        #        ⛔ 而且 6488 的 09-02 那一列 shares 是空的 ⇒ 這是**真的不一致**
        HS = "date,stock_id,name,market,close,shares"
        _io.open(_o.path.join(st, "6488.csv"), "w", encoding="utf-8").write(
            HS + "\n"
            "2026-08-31,6488,環球晶,tpex,100,\n"
            "2026-09-01,6488,環球晶,tpex,100,1000\n"
            "2026-09-02,6488,環球晶,tpex,100,\n"
            "2026-09-03,6488,環球晶,tpex,100,0\n")
        _io.open(_o.path.join(st, "2330.csv"), "w", encoding="utf-8").write(
            HS + "\n"
            "2026-08-31,2330,台積電,twse,900,\n"
            "2026-09-01,2330,台積電,twse,900,\n"
            "2026-09-02,2330,台積電,twse,900,\n"
            "2026-09-03,2330,台積電,twse,900,\n")

        import glob as _g
        cd, mism = D.shares_cells(sorted(_g.glob(_o.path.join(dy, "*.csv"))),
                                  day_from_name=True)
        cs, mism2 = D.shares_cells(sorted(_g.glob(_o.path.join(st, "*.csv"))))
        fr = D.shares_frontier(cd, cs)

        ck("⛔ 日檔 `date` 欄跟檔名不同的列**被數出來**（第二點：靜靜回了別天）",
           mism == 2, f"mism={mism}")
        ck("  個股庫沒有檔名可比 ⇒ 不誤報", mism2 == 0, f"mism2={mism2}")

        ck("⭐ 逐市場算（⛔ 不是一個總數）",
           sorted(fr) == ["tpex", "twse"], str(sorted(fr)))

        tp = fr["tpex"]
        ck("① 日檔 tpex：5 天裡 3 天有 shares（⛔ `\"0\"` 與空的都算沒有）",
           tp["daily"][:2] == (3, 5), str(tp["daily"]))
        ck("⭐ 區間是**有值的那些天**算出來的（⛔ 不是全部天）"
           "——起點 09-01，⛔ 不是 08-31",
           tp["daily"][2:] == ("2026-09-01", "2026-09-04"), str(tp["daily"]))
        ck("② 個股庫 tpex：4 天裡只有 1 天有（空的與 `\"0\"` 都算沒有）",
           tp["stocks"][:2] == (1, 4), str(tp["stocks"]))

        ck("⭐⭐ 真的不一致只報 09-02（日檔有、個股庫空）",
           tp["only_daily"] == ["2026-09-02"], str(tp["only_daily"]))
        ck("⛔⛔ 09-04 **不算不一致**——個股庫根本還沒轉置到那一天",
           "2026-09-04" not in tp["only_daily"], str(tp["only_daily"]))
        ck("⭐ 而那一天要出現在「還沒追上」欄，⛔ 不是靜靜消失",
           tp["lag"] == ["2026-09-04"], str(tp["lag"]))
        ck("  反方向（個股庫有、日檔沒有）是空的", tp["only_stocks"] == [],
           str(tp["only_stocks"]))

        tw = fr["twse"]
        ck("⛔ 整格是空的要看得見：twse 兩邊都 0（⛔ 不會被 tpex 蓋掉）",
           tw["daily"][:2] == (0, 5) and tw["stocks"][:2] == (0, 4),
           f"{tw['daily']} {tw['stocks']}")
        ck("  兩邊都 0 ⇒ 不報不一致",
           tw["only_daily"] == [] and tw["only_stocks"] == [])

        # ── 印出來的那一頁要**把不一致講出來** ──
        out = []
        _D_DATA, _D_META = D.DATA, D.META
        try:
            D.DATA = d
            _o.makedirs(_o.path.join(d, "universe"), exist_ok=True)
            _sh.move(dy, _o.path.join(d, "universe", "daily"))
            D.section_shares(out)
        finally:
            D.DATA, D.META = _D_DATA, _D_META
        txt = "\n".join(out)
        ck("⭐ 印出來的那一頁講出「兩邊對同一天給出相反答案」",
           "相反答案" in txt, txt[:200])
        ck("  並且點名 09-02", "2026-09-02" in txt)
        ck("  也把 `date` 欄不符講出來", "跟檔名不同" in txt)

        # ── ⭐ 反向：把不一致修掉 ⇒ 這一頁要改口說「一致」 ──
        _io.open(_o.path.join(st, "6488.csv"), "w", encoding="utf-8").write(
            HS + "\n"
            "2026-08-31,6488,環球晶,tpex,100,\n"
            "2026-09-01,6488,環球晶,tpex,100,1000\n"
            "2026-09-02,6488,環球晶,tpex,100,1000\n"
            "2026-09-03,6488,環球晶,tpex,100,0\n")
        cs2, _ = D.shares_cells(sorted(_g.glob(_o.path.join(st, "*.csv"))))
        fr2 = D.shares_frontier(cd, cs2)
        ck("⭐⭐ 修掉那一列 ⇒ 不一致變空（⛔ 證明上面那條會紅也會綠）",
           fr2["tpex"]["only_daily"] == [], str(fr2["tpex"]["only_daily"]))
        ck("  ⚠ 而「還沒追上」不受影響，⛔ 不可以跟著變空",
           fr2["tpex"]["lag"] == ["2026-09-04"], str(fr2["tpex"]["lag"]))

        # ── ⭐ 「放水」方向：把 `"0"` 也算成有值 ⇒ 09-03 會變成假的一致 ──
        #    這裡直接證明判準對 `"0"` 的處理是**有作用**的：
        #    如果 `"0"` 算有值，個股庫 tpex 就會是 2/3 而不是 1/3。
        ck("⛔ 放水檢查：`\"0\"` 若算有值，個股庫 tpex 會變 2/4"
           "（現在是 1/4 ⇒ 這條判準有在擋）",
           fr["tpex"]["stocks"][0] == 1, str(fr["tpex"]["stocks"]))

        # ── 目錄不存在 ⇒ **明講算不出來**，⛔ 不是印 0 ──
        out2 = []
        _D_DATA = D.DATA
        try:
            D.DATA = _o.path.join(d, "nope")
            D.section_shares(out2)
        finally:
            D.DATA = _D_DATA
        ck("⛔ 目錄不存在 ⇒ 明講「算不出來」，⛔ 不填任何數字",
           "算不出來" in "\n".join(out2), "\n".join(out2)[:200])
    finally:
        _sh.rmtree(d, ignore_errors=True)
    return ok, fail


def _universe_dirs_section():
    """⭐ `data/universe/` 要**自動列舉**，⛔ 不是寫死清單。

    ⛔⛔ 這一節的理由（2026-09-10 實測）：
      `_db_status.md` 是契約第一句指定用來回答「**有什麼**」的那份文件，
      ⚠ 而它原本只提到 **3** 個目錄——實際有 **21** 個。
      ⇒ `margin`／`per`／`inst`／`exright`／`sbl`／`tib`… 全部不在裡面。
    ⭐ 而這是第三次同一個形狀（前兩次：`push_data.sh` 的 mode 白名單、
      `feeds.yml` 的 feed 選單）⇒ 修法一律是**把清單拿掉**。
    """
    import glob as _g
    import os as _o
    import shutil as _sh
    import tempfile as _tf
    import db_status as D

    ok = fail = 0

    def ck(name, cond, hint=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ok   {name}")
        else:
            fail += 1
            print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))

    d = _tf.mkdtemp(prefix="dbstat_")
    try:
        uni = _o.path.join(d, "universe")
        # ① 逐日
        _o.makedirs(_o.path.join(uni, "margin"))
        for x in ("2015-01-05", "2026-09-09"):
            io.open(_o.path.join(uni, "margin", x + ".csv"), "w").write("a\n")
        # ② 逐檔（檔名是代號）
        _o.makedirs(_o.path.join(uni, "esb"))
        for x in ("5267", "6434"):
            io.open(_o.path.join(uni, "esb", x + ".csv"), "w").write("a\n")
        # ③ 巢狀
        _o.makedirs(_o.path.join(uni, "capital", "tpex"))
        io.open(_o.path.join(uni, "capital", "tpex", "1150908.csv"),
                "w").write("a\n")
        # ④ 空目錄
        _o.makedirs(_o.path.join(uni, "empty"))
        # ⚠ 非目錄的東西不可以被當成一層
        io.open(_o.path.join(uni, "_coverage.csv"), "w").write("a\n")

        got = {r[0]: r for r in D.universe_dirs(uni)}
        ck("⭐ **四個目錄都列出來**（⛔ 不是只列寫死的那幾個）",
           set(got) == {"margin", "esb", "capital", "empty"}, str(sorted(got)))
        ck("⛔ 非目錄的 `_coverage.csv` 不會被當成一層",
           "_coverage.csv" not in got, str(sorted(got)))
        ck("逐日的算得出區間",
           got["margin"][2:4] == ("2015-01-05", "2026-09-09"),
           str(got["margin"]))
        ck("  形狀標「逐日」", got["margin"][4] == "逐日", str(got["margin"]))
        ck("⚠ 逐檔的**不報區間**（⛔ 代號排序不是日期）",
           got["esb"][2] == "—" and "逐檔" in got["esb"][4], str(got["esb"]))
        ck("⭐ 巢狀的數得到子目錄底下的檔（⛔ 不是報 0）",
           got["capital"][1] == 1 and "巢狀" in got["capital"][4],
           str(got["capital"]))
        ck("⚠ 空目錄照樣列出來、檔數 0（⛔ 不是整個消失）",
           got["empty"][1] == 0, str(got["empty"]))
        ck("⛔ 目錄不存在時回空清單，不是丟例外",
           D.universe_dirs(_o.path.join(d, "nope")) == [])

        # ⭐ 反向：新增一個目錄 ⇒ **不必改任何清單**就會出現
        _o.makedirs(_o.path.join(uni, "brandnew"))
        io.open(_o.path.join(uni, "brandnew", "2026-09-10.csv"), "w").write("a\n")
        got2 = {r[0] for r in D.universe_dirs(uni)}
        ck("⭐⭐ 新開一個目錄 ⇒ **自己出現**（⛔ 這就是不寫死清單的重點）",
           "brandnew" in got2, str(sorted(got2)))
    finally:
        _sh.rmtree(d, ignore_errors=True)
    return ok, fail


if __name__ == "__main__":
    sys.exit(main())
