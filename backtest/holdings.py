# -*- coding: utf-8 -*-
"""使用者持股清單（回測線與情報共用一份）——回測線，2026-09-30。

來源：跨線信箱 `_持股/持股.csv`（信箱的共用資料夾，⛔ 不是情報的資料夾）；⛔ 程式只讀、不寫
  格式：代號,買進日,買進價,備註[,來源[,正式進場日]]（來源：營量／營飆／營飆營量（金額 2:1 分兩份，情報 0929 口徑）／其他，空白＝其他；2026-09-30 使用者：營量、營飆買的照正式規則出場）；第 6 欄「正式進場日」可省略，只在使用者先買、之後才入選營量／營飆時填（正式出場從這天數第 60／120 個交易日；空白＝買進日；2026-10-06 6213）；# 開頭是註解；買進日、買進價可以留空；全形逗號與前後空白都接受；代號一律當字串
  首列若是欄名（代號,…）略過；編碼先試 UTF-8（含 BOM），不行再試 cp950（Excel 存檔）
用途：
  daily_list 第五節（買賣流程）⇒ flow_rows()：只取買進日與買進價都有的列；缺的列另列「代號｜缺買進日／價，無法追蹤流程」
  same_state ⇒ codes()：代號欄，照檔內順序（同一代號出現多次只列一次；來源是營量／營飆的策略股不列，情報 0930-2153）
退路：檔案不存在或讀檔失敗 ⇒ 退回 repo 的舊檔（backtest/holdings_flow.txt、backtest/holdings_same_state.txt），並記 log 一行
測試用：環境變數 HOLDINGS_CSV 可把 csv 指到暫存處
"""
from __future__ import annotations

import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_DEFAULT = "/mnt/c/SynologyDrive/跨線信箱/_持股/持股.csv"
TXT_FLOW = os.path.join(HERE, "holdings_flow.txt")
TXT_SS = os.path.join(HERE, "holdings_same_state.txt")


def csv_path():
    return os.environ.get("HOLDINGS_CSV", CSV_DEFAULT)


def _lines(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp950"):
        try:
            return raw.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    raise ValueError("編碼不是 UTF-8 也不是 cp950")


def read_csv(path=None):
    """⇒ [(代號, 買進日 'YYYY-MM-DD' 或 None, 買進價 float 或 None, 備註)]；檔案不存在或讀不了 ⇒ 丟例外。"""
    p = path or csv_path()
    out = []
    for ln in _lines(p):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        a = [x.strip() for x in ln.replace("，", ",").split(",", 5)]
        a += [""] * (6 - len(a))
        code = a[0]
        if not code or code == "代號":
            continue
        bd = None
        if a[1]:
            try:
                bd = str(pd.Timestamp(a[1]).date())
            except (ValueError, TypeError):
                bd = None
        try:
            bp = float(a[2]) if a[2] else None
        except ValueError:
            bp = None
        if bp is not None and not bp > 0:
            bp = None
        src = a[4].replace("＋", "").replace("+", "").replace("、", "").replace(" ", "")
        src = "營飆營量" if src in ("營飆營量", "營量營飆") else src if src in ("營量", "營飆") else "其他"
        out.append((code, bd, bp, a[3], src))
    return out


def flow_rows(log=print):
    """daily 第五節用 ⇒ (flows [(代號, 買進日, 買進價)], 缺日期或價格的代號 [..], 來源說明)。"""
    p = csv_path()
    try:
        rows = read_csv(p)
    except Exception as ex:                                           # 不存在或讀檔失敗 ⇒ 退回 holdings_flow.txt
        from . import surge_flow_daily as SFL
        log(f"持股：讀 {p} 失敗（{type(ex).__name__}: {ex}）⇒ 退回 {SFL.FLOW}")
        return SFL.read_flow(), [], "txt"
    flows = [(c, d, b) for c, d, b, _, _ in rows if d is not None and b is not None]
    miss = [c for c, d, b, _, _ in rows if d is None or b is None]
    log(f"持股：{p}｜可追蹤 {len(flows)} 列、缺買進日／價 {len(miss)} 列")
    return flows, miss, "csv"


def codes(log=print):
    """same_state 用 ⇒ (代號 [..] 照檔內順序、去重, 來源說明)。"""
    p = csv_path()
    try:
        rows = read_csv(p)
    except Exception as ex:                                           # 不存在或讀檔失敗 ⇒ 退回 holdings_same_state.txt
        log(f"持股：讀 {p} 失敗（{type(ex).__name__}: {ex}）⇒ 退回 {TXT_SS}")
        return [x.strip() for x in open(TXT_SS, encoding="utf-8") if x.strip() and not x.startswith("#")], "txt"
    out = []
    for c, _, _, _, src in rows:                                      # 情報 0930-2153：策略股（營量／營飆）不進同狀態表
        if src == "其他" and c not in out:
            out.append(c)
    log(f"持股：{p}｜同狀態 {len(out)} 檔")
    return out, "csv"


def sources():
    """⇒ {代號: 營量／營飆／其他}；讀不到 ⇒ {}（全部當其他）。"""
    try:
        return {c: s for c, _, _, _, s in read_csv()}
    except Exception:
        return {}


def entry_dates():
    """⇒ {代號: 正式進場日 'YYYY-MM-DD'}（第 6 欄有填且是日期的列）；讀不到 ⇒ {}。"""
    try:
        out = {}
        for ln in _lines(csv_path()):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            a = [x.strip() for x in ln.replace("，", ",").split(",", 5)]
            if len(a) == 6 and a[0] and a[0] != "代號" and a[5]:
                try:
                    out[a[0]] = str(pd.Timestamp(a[5]).date())
                except (ValueError, TypeError):
                    pass
        return out
    except Exception:
        return {}
