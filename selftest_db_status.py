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

    print("\n" + "=" * 60)
    if FAILED:
        print(f"✗ {len(FAILED)} 項失敗：")
        for x in FAILED:
            print("   -", x)
        return 1
    print("全部通過")
    return 0




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
