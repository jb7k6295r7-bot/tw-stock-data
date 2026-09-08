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

    print("\n" + "=" * 60)
    if FAILED:
        print(f"✗ {len(FAILED)} 項失敗：")
        for x in FAILED:
            print("   -", x)
        return 1
    print("全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
