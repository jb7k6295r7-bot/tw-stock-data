# -*- coding: utf-8 -*-
"""scan64：資料快照固定在 tw-stock-data origin/main 9e1316ff3c（git archive 抽到 scan64/dbmain/data）。
程式碼沿用 ~/tw-p17 backtest/（D、research11、research34、researchLongPool）；⚠ import researchLongPool／addon_daily 會換 D.DATA ⇒ import 完一律呼叫 fix()。"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
# 補格（add/）用環境變數改快照與輸出根目錄；沒設時與 64 格原樣相同。
BASE = os.path.expanduser(os.environ.get("SCAN_BASE", HERE))
SNAP = os.path.expanduser(os.environ.get("SCAN_SNAP", os.path.join(HERE, "dbmain", "data")))
SHA = open(os.path.expanduser(os.environ.get("SCAN_SHA", os.path.join(HERE, "dbmain", "SHA.txt")))).read().split()[0]


def fix():
    from backtest import data as D
    D.DATA = SNAP
    assert D.DATA == SNAP and os.path.exists(os.path.join(SNAP, "meta", "calendar_twse.csv"))
    return D


def check():
    from backtest import data as D
    assert D.DATA == SNAP, f"⛔ D.DATA 被換成 {D.DATA}"
