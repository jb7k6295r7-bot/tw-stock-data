# -*- coding: utf-8 -*-
"""策略股出場日固定檔——回測線，2026-11-20（情報 1116-1650、使用者 11/16「好」）。

每晚 daily_list 產完名單後呼叫 write()：讀 _持股/持股.csv（⛔ 只讀），寫 resultsDaily/出場日.csv；包裝（run_daily_list.sh）再複製到信箱 _營量觀察/出場日.csv
（⛔ 信箱只寫 _營量觀察/，run_daily_list 規則 6；情報只讀）。
欄位：代號,買進日,策略,出場日,依據,更新時間
  - 一列一個「代號＋買進日＋策略」；營飆營量那列拆兩列（營飆、營量）
  - 營量 ＝ 正式進場日（持股檔第 6 欄，空白＝買進日）起第 60 個交易日收盤；營飆 ＝ 第 120 個（備註含「60 天同日賣」⇒ 60，AD.hold_days）；
    口徑同 daily_list 第五節（D.exit_pos ＋ GB.future_trading_days(fixed_holidays_uncovered=True)）⇒ 名單第五節與本檔同一個日子
  - 高10 ＝ 前瞻帳 forward/pth10/positions_user.csv 同代號同買進日、狀態「持有中」那列的排程賣出日
  - 大跌4檔、其他：不列（大跌看加權指數，沒有固定日）
  - 買進日空白 ⇒ 出場日空白、依據寫「買進日不明」
更新時間：該列內容（出場日、依據）跟上一版相同 ⇒ 沿用上一版時間；變了 ⇒ 本次時間（台北）。休市表一改，受影響的列自然換新時間。
"""
from __future__ import annotations

import csv
import os

import pandas as pd

from . import data as D
from . import gate_b_status as GB
from . import holdings as HD

HERE = os.path.dirname(os.path.abspath(__file__))
PU = os.path.join(HERE, "forward", "pth10", "positions_user.csv")
COLS = ["代號", "買進日", "策略", "出場日", "依據", "更新時間"]


def _basis(b):
    return "依證交所休市表外推（颱風假不可預知）" if b == "休市表外推" else b


def _prev(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {(r["代號"], r["買進日"], r["策略"]): r for r in csv.DictReader(f)}


def rows(cal, hold_days):
    """⇒ [dict(代號, 買進日, 策略, 出場日, 依據)]。cal ＝ 資料日曆（最後一天＝資料日）；hold_days ＝ AD.hold_days。"""
    n = len(cal)
    fut, basis = GB.future_trading_days(cal, 2 * 120 + 10, fixed_holidays_uncovered=True)
    cal_ext = cal.append(fut)
    ED = HD.entry_dates()
    try:
        pu = pd.read_csv(PU, dtype=str, encoding="utf-8-sig").fillna("")
        pu = pu[pu["狀態"] == "持有中"]
    except Exception:
        pu = None
    out = []
    for c, bd, _bp, nt, src in HD.read_csv():
        if src in ("營飆營量", "營飆", "營量"):
            ed = ED.get(c) or bd
            for part in ("營飆", "營量"):
                if part not in src:
                    continue
                H = hold_days(part, nt)
                if ed is None:
                    out.append(dict(代號=c, 買進日=bd or "", 策略=part, 出場日="", 依據="買進日不明，出場日不可算"))
                    continue
                xp = D.exit_pos(int(cal.searchsorted(pd.Timestamp(ed))), H)
                if xp >= len(cal_ext):
                    out.append(dict(代號=c, 買進日=bd or "", 策略=part, 出場日="", 依據=f"第 {H} 個交易日超出外推範圍"))
                    continue
                why = [f"第 {H} 個交易日收盤"]
                if ed != bd:
                    why.append(f"從正式進場日 {ed} 起算")
                if part == "營飆" and H != 120:
                    why.append("你定與營量同日賣")
                why.append("已到期" if xp <= n - 1 else _basis(basis[xp - n]))
                out.append(dict(代號=c, 買進日=bd or "", 策略=part, 出場日=str(cal_ext[xp].date()), 依據="；".join(why)))
        elif src == "高10":
            sx = ""
            if pu is not None:
                m = pu[(pu["代號"] == c) & (pu["買進日"] == (bd or ""))]
                if not len(m):
                    m = pu[pu["代號"] == c]
                if len(m):
                    sx = m["排程賣出日"].iloc[0]
            d = sx[:10]
            if not d:
                why = "高10 帳沒有這筆持有中的列"
            else:                                                      # 用本檔同一份外推日曆覆核「該月最後交易日」（帳上的「外推」字樣是買進當時寫的）
                why = "高10 帳排程賣出日（4 月最後交易日）"
                ts = pd.Timestamp(d)
                if ts in cal_ext:
                    i = cal_ext.get_loc(ts)
                    last = i + 1 >= len(cal_ext) or cal_ext[i + 1].month != ts.month
                    why += ("；" + _basis(basis[i - n]) if i >= n else "；已到期") + ("" if last else "；⚠ 依目前休市表不是該月最後交易日，請回測線重算")
                else:
                    why += "；⚠ 依目前休市表這天不是交易日，請回測線重算"
            out.append(dict(代號=c, 買進日=bd or "", 策略="高10", 出場日=d, 依據=why))
    return out


def write(cal, path, hold_days):
    """寫 path（UTF-8 BOM，Excel 可開）；⇒ 一行 log。"""
    old = _prev(path)
    now = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    R = rows(cal, hold_days)
    ch = 0
    for r in R:
        o = old.get((r["代號"], r["買進日"], r["策略"]))
        if o and o["出場日"] == r["出場日"] and o["依據"] == r["依據"]:
            r["更新時間"] = o["更新時間"]
        else:
            r["更新時間"] = now
            ch += 1
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(R)
    os.replace(tmp, path)
    return f"[出場日] {path}｜{len(R)} 列｜本次變動 {ch} 列"
