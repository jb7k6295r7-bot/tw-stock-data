# -*- coding: utf-8 -*-
"""PREREG期貨短線日線四題 seq2（台股策略線登錄 sha d1ae453b1a3d30e6，2026-10-06 13:35；裁定 seq307 發號）。回測線。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTXS body
    抽樣查核：--check（⛔ 不呼叫本體與 researchTXF 的 load_fut／daily；用 researchTXF_check.Raw 從原始列逐日走契約、契約口數記帳）｜網頁：page

⭐ 讀法寫死時間：2026-10-06 14:55（台北）；寫死前 ⛔ 沒看任何本件的報酬統計或輸出
   （只看過資料格式：TX 與加權指數交易日一致、星期分佈、週六交易日、TX 開盤價無缺、0050 還原價起日 2004-02-11）。
排序（裁定 seq307）：甲 → 丙 → 丁；乙 停判（台股 1006-1445：台指VIX 免費資料只有 2026-07 起約 3 個月 ⇒ 照登錄「缺 ⇒ 本題停」；
   ⛔ 不用 TXO 價格自行重算 VIX 代替）。
⛔ 期交所條款：私有庫原始數字不得重製散布 ⇒ repo 裡只放彙總（報酬、勝率、比例、CI、次數）；逐日／逐筆中間檔一律放 ~/txfwork/short/（不進 repo）。
⭐ 直接 import backtest.researchTXF（期貨六題 seq2）：load_fut、daily（主版轉倉連續序列）、cf（成本）、cl_stats（月分群 CI）、load_margin、load_rate、
   load_taiex、etf_close、seg_metrics、judge_user；⛔ 不改它。

═══ R0 共同讀法（沿用六題 R0；本件執行者補的寫在各題）═══
  價格：TX 近月主版連續（到期日以結算價了結、同日以次月一般盤收盤買進；結算價欄缺時以到期契約當日收盤代表）＝ researchTXF.daily(F, 1)。
  成本（判以高案）：每邊 ＝ 0.002% ＋ (1 點 ＋ 手續費÷50) ÷ 成交當時原始價；手續費高 NT$50、低 NT$20／小台口。一筆交易的成本 ＝ 進場一邊 ＋ 出場一邊
     ＋ 持有期內每次轉倉兩邊（了結那邊用結算價、新開那邊用次月收盤），各邊比例直接相加（不複利）。
  段：早年 1998-07-21（TX 資料起點）～2014-12-31｜探索 2015-01-01～2020-12-31｜確認 2021-01-01～2026-09-30。
     加權指數（只甲並報）早年 1990-01-04（資料起點）～2014-12-31，不扣成本。
  「平常」＝ 同段「所有」交易日（含事件日本身）、同持有長度、同進出時點的無條件報酬平均；差 X ＝ 事件報酬 − 平常；月分群 95% CI（cl_stats，1.96）。
  「有」＝ 探索、確認兩段 X 同號且兩段 CI 都不跨 0（方向不限）；「可交易」（執行者補）＝ 先「有」，再加：做多的扣成本後事件報酬（毛報酬 − 來回成本，
     ⛔ 不是差）兩段月分群 CI 下緣都 ＞ 0。早年方向相反（早年 X 與探索 X 異號）照寫。

═══ 甲 日曆效應（登錄 §二；N_單筆 3＝甲1、甲2、甲3）═══
  進出：收盤 → 收盤（登錄 §二 照文獻，與 §一 次日開盤不同）。段歸屬與月分群：以出場日。
  甲1 讀法（執行者補）：登錄括號同時寫「4 日窗」「本題進場用窗前一日收盤」與「前一月最後交易日收盤 → 第 3 日收盤」，後者只有 3 根日報酬、與前兩者不一致
     ⇒ 判定格取 4 日窗：月最後交易日 j 的前一個交易日（j−1）收盤進、次月第 3 個交易日（j＋3）收盤出（4 根日報酬，Lakonishok–Smidt 式）；
     括號的 3 日讀法（j 收 → j＋3 收）另報、⛔ 不判。平常 ＝ 同段所有「4 根日報酬」窗。
  甲2 國定假日辨識（執行者補；官方休市表本機只有 2021 起）：
     休市段 ＝ 相鄰兩個交易日之間的所有日曆日；段內至少一個「平日（週一～五）沒交易」且至少一天落在下列假日名單 ⇒ 假日休市段；節前日 ＝ 該段前最後一個交易日；
     報酬 ＝ 前一交易日收 → 節前日收。段內有平日休市但沒有任何假日名單日 ⇒ 颱風、地震、選舉等「非假日休市」，⛔ 不算（全數列在 summary 的「非假日休市」）。
     假日名單：元旦 01-01、01-02｜和平紀念日 02-28（1997 起）｜青年節 03-29（2000 以前）｜清明／兒童節／婦幼節 04-03～04-06｜勞動節 05-01｜
     教師節 09-28（1997 以前）｜國慶 10-10｜光復節 10-25、蔣公誕辰 10-31、國父誕辰 11-12、行憲紀念日 12-25（2000 以前）｜
     春節（農曆除夕～初三）、端午（五月初五）、中秋（八月十五）：農曆日期表 LUNAR 由 Windows .NET TaiwanLunisolarCalendar 產生（2026-10-06 14:40 台北），
     並以交易日曆驗：落在平日的初一、端午、中秋必須沒交易（不符次數記在 summary）。週六不當休市判斷（2000 年以前週六常有交易、之後有補行交易日）。
     彈性放假、補假、春節前「只辦結算交割」的日子都在同一休市段內 ⇒ 自動併入。⚠ 颱風休市剛好緊鄰假日時會併成假日段（照實註）。
     春節前另報 ＝ 休市段含農曆初一；另報「春節以外的節前」。
     ⚠（2026-10-06 15:05 台北補記）初版跑完後核對「非假日休市」清單，發現 2025 年起恢復放假的教師節 09-28（2025-09-29 補假）、光復節 10-25（2025-10-24 補假）、
       行憲紀念日 12-25 被當成非假日 ⇒ 名單補上這三個「2025 起」；屬事實更正、不是調參數。初版（少這 3 筆）甲2 也是「測不出」，判定不變（初版已看過，照實註）。
  甲3 星期一：週一交易日；前一個交易日收（多半是週五；2000 年以前與補行交易日可能是週六）→ 週一收；週二～五另報（同式，⛔ 不判）。
  加權指數並報：同樣的事件定義套在加權指數日曆（1990 起）與收盤，只算早年段、不扣成本。
  交易版（描述）：只在窗內持 TX 多單 1 倍（收盤進、收盤出）、其餘空手；與「TX 一直持多 1 倍」同引擎、同起點比 ⇒ 年化、最大回落（引擎見丁）。

═══ 丙 大跌隔天反彈（登錄 §四；N_單筆 3＝H1、H3、H5，每個 H 以 4 格 ≥ 3 格判）═══
  TX 一般盤收盤報酬 ＝ 近月主版連續的日報酬 daily().r（到期日用結算價代表、轉倉日起用次月）。
  2 日 RSI（執行者補）：Wilder 平滑、期數 2；用主版連續還原收盤 adjC 的逐日變化（漲幅 G、跌幅 L）；前 2 個變化取簡單平均起算，之後 AG ＝ (AG ＋ G)/2、AL 同；
     RSI ＝ 100 − 100/(1 ＋ AG/AL)（AL＝0 ⇒ 100；AG＝AL＝0 ⇒ 50）。
  觸發：訊號日 t 收盤符合就算一筆；連續多日都符合各算一筆（持有期可重疊，月分群處理相依）。
  R_H ＝ adjC(t＋H) ÷ adjO(t＋1) − 1（t＋1 開盤進、第 H 個交易日收盤出，進場那根算第 1 根）。段：t＋1 ≥ 段起、t＋H ≤ 段尾（同六題丁）；月分群以訊號日 t 所在月。
  成本：進場開盤價一邊 ＋ 出場一邊 ＋ 持有期 [t＋1, t＋H−1] 內轉倉兩邊。
  ⚠ 與舊「大盤反轉訊號」（RSI(14)＜30 站回、低檔爆量長下影等）同屬「超賣後反彈」一族（登錄 §八、裁定 seq307）⇒ 結果句必註「同族舊訊號已 0 格」；
     丙若成立最多「暫定」並進前瞻紀錄，⛔ 不得據以翻舊件結論。

═══ 丁 短週期趨勢多空（登錄 §五；N_組合 ＋1）═══
  訊號：s_L(t) ＝ adjC(t) ÷ adjC(t−L) − 1；＞0 ⇒ 多 1 倍、＜0 ⇒ 空 1 倍、＝0 ⇒ 維持前一訊號；t＋1 開盤換倉；訊號沒變不交易。L ∈ {5, 10, 20, 60}。
  引擎（執行者補，甲交易版共用）：權益 E、契約價值 V（可為小數口、帶正負號）。每日：
     利息 ＝ max(E − 原始保證金比例 × |V|, 0) × F5 利率 × 日曆天數 ÷ 365（以前一日收盤狀態；保證金 2004-09-30 前無資料 ⇒ 全額計息；利率 2001-01 前無資料 ⇒ 0）；
     夜間段 ＝ adjO(t)/adjC(t−1)；開盤換倉 ＝ 舊部位全平（|V| × 每邊成本）、新部位 V ＝ 方向 × E（再扣 |V| × 每邊成本）；日間段 ＝ adjC(t)/adjO(t)；
     收盤：到期日轉倉（了結扣一邊、次月開新部位並調回 方向 × E、扣一邊）或收盤換倉（甲交易版）。1 倍 ⇒ 不模擬追繳（六題乙：1～3 倍 0 次）。
  起點（所有路徑相同）：TX 第 61 個交易日（index 60，L60 可算的第一天）收盤；一直持多版當天收盤進場，丁各版次日開盤依訊號進場。
  判（使用者判準對 0050）：各段各 L 用 researchTXF.judge_user（條件一 年化 ＞ 0050；條件二 年化÷|最大回落| ≥ 0050）給 合格／另列／不合格；
     探索、確認兩段都 ≥ 3／4 格合格 ⇒ 合格｜兩段都 ≥ 3／4 格「合格或另列」⇒ 另列｜否則不合格；早年照報、不進判。
  早年窗（執行者補）：0050 還原價第一個有值的 TX 交易日（2004-02-11）之後 ～ 2014-12-31（兩邊同窗）。年化、回落、波動照 seg_metrics（同六題）。
  描述（⛔ 不判）：只做多（跌就空手）版；TX 一直持多 1 倍；換手次數（每年）；持多／持空天數比例。

═══ 乙 台指VIX：停判（台指VIX 免費資料只有約 3 個月，資料庫每日累積中）；N_單筆 −6 待裁定核 ═══
GATE_V2：本件無個股母體，不適用（照實寫）。
輸出 backtest/resultsTXS/（summary.json、A_cells.csv、A_trade.csv、C_cells.csv、D_cells.csv、check.json、run.log、期貨短線日線四題.html）；
逐日中間檔 ~/txfwork/short/（A_events.csv.gz、C_events.csv.gz、paths.npz；⛔ 不進 repo）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchTXF as X  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsTXS")
WORK = os.path.expanduser("~/txfwork/short")
TAGT = "2026-10-06 14:55（台北）"
REG = "PREREG期貨短線日線四題 seq2（sha d1ae453b1a3d30e6）"
END = X.END
SEG = {"早年": ("1998-07-21", "2014-12-31"), "探索": ("2015-01-01", "2020-12-31"), "確認": ("2021-01-01", END)}
IX_SEG = {"早年（加權指數）": ("1990-01-01", "2014-12-31")}
FEE = X.FEES["高"]; FEE_LO = X.FEES["低"]
T0 = 60
LS = (5, 10, 20, 60)
HS = (1, 3, 5)
LOG: list = []

# 農曆（西元年 → 初一、端午、中秋）：.NET System.Globalization.TaiwanLunisolarCalendar 產生（2026-10-06 14:40 台北），閏月已處理
LUNAR = {
    1989: ("1989-02-06", "1989-06-08", "1989-09-14"), 1990: ("1990-01-27", "1990-05-28", "1990-10-03"), 1991: ("1991-02-15", "1991-06-16", "1991-09-22"),
    1992: ("1992-02-04", "1992-06-05", "1992-09-11"), 1993: ("1993-01-23", "1993-06-24", "1993-09-30"), 1994: ("1994-02-10", "1994-06-13", "1994-09-20"),
    1995: ("1995-01-31", "1995-06-02", "1995-09-09"), 1996: ("1996-02-19", "1996-06-20", "1996-09-27"), 1997: ("1997-02-07", "1997-06-09", "1997-09-16"),
    1998: ("1998-01-28", "1998-05-30", "1998-10-05"), 1999: ("1999-02-16", "1999-06-18", "1999-09-24"), 2000: ("2000-02-05", "2000-06-06", "2000-09-12"),
    2001: ("2001-01-24", "2001-06-25", "2001-10-01"), 2002: ("2002-02-12", "2002-06-15", "2002-09-21"), 2003: ("2003-02-01", "2003-06-04", "2003-09-11"),
    2004: ("2004-01-22", "2004-06-22", "2004-09-28"), 2005: ("2005-02-09", "2005-06-11", "2005-09-18"), 2006: ("2006-01-29", "2006-05-31", "2006-10-06"),
    2007: ("2007-02-18", "2007-06-19", "2007-09-25"), 2008: ("2008-02-07", "2008-06-08", "2008-09-14"), 2009: ("2009-01-26", "2009-05-28", "2009-10-03"),
    2010: ("2010-02-14", "2010-06-16", "2010-09-22"), 2011: ("2011-02-03", "2011-06-06", "2011-09-12"), 2012: ("2012-01-23", "2012-06-23", "2012-09-30"),
    2013: ("2013-02-10", "2013-06-12", "2013-09-19"), 2014: ("2014-01-31", "2014-06-02", "2014-09-08"), 2015: ("2015-02-19", "2015-06-20", "2015-09-27"),
    2016: ("2016-02-08", "2016-06-09", "2016-09-15"), 2017: ("2017-01-28", "2017-05-30", "2017-10-04"), 2018: ("2018-02-16", "2018-06-18", "2018-09-24"),
    2019: ("2019-02-05", "2019-06-07", "2019-09-13"), 2020: ("2020-01-25", "2020-06-25", "2020-10-01"), 2021: ("2021-02-12", "2021-06-14", "2021-09-21"),
    2022: ("2022-02-01", "2022-06-03", "2022-09-10"), 2023: ("2023-01-22", "2023-06-22", "2023-09-29"), 2024: ("2024-02-10", "2024-06-10", "2024-09-17"),
    2025: ("2025-01-29", "2025-05-31", "2025-10-06"), 2026: ("2026-02-17", "2026-06-19", "2026-09-25"), 2027: ("2027-02-06", "2027-06-09", "2027-09-15"),
}
# (月-日, 起年, 迄年, 名)
FIXED = [("01-01", None, None, "元旦"), ("01-02", None, None, "元旦"), ("02-28", 1997, None, "和平紀念日"), ("03-29", None, 2000, "青年節"),
         ("04-03", None, None, "清明／兒童節"), ("04-04", None, None, "清明／兒童節"), ("04-05", None, None, "清明／兒童節"), ("04-06", None, None, "清明／兒童節"),
         ("05-01", None, None, "勞動節"), ("09-28", None, 1997, "教師節"), ("10-10", None, None, "國慶"), ("10-25", None, 2000, "光復節"),
         ("10-31", None, 2000, "蔣公誕辰"), ("11-12", None, 2000, "國父誕辰"), ("12-25", None, 2000, "行憲紀念日"),
         ("09-28", 2025, None, "教師節"), ("10-25", 2025, None, "光復節"), ("12-25", 2025, None, "行憲紀念日")]   # 2025 起恢復（15:05 補記，見 docstring）
WK = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
CELL_A = {"甲1": "甲1 月底月初（4 日窗）", "甲2": "甲2 節前", "甲3": "甲3 星期一"}
CELL_C = {"丙1": "丙1 收盤報酬 ≤ −2%", "丙2": "丙2 收盤報酬 ≤ −3%", "丙3": "丙3 2 日 RSI ≤ 10", "丙4": "丙4 2 日 RSI ≤ 5"}


def log(s):
    LOG.append(s)
    print(s, flush=True)


def holiday_names():
    H = {}
    for y in range(1989, 2028):
        for md, a, b, nm in FIXED:
            if (a is None or y >= a) and (b is None or y <= b):
                H[f"{y}-{md}"] = nm
        cny, dw, ma = LUNAR[y]
        g = pd.Timestamp(cny)
        for k in range(-1, 3):
            H[(g + pd.Timedelta(days=k)).strftime("%Y-%m-%d")] = "春節"
        H[dw] = "端午"; H[ma] = "中秋"
    return H


def holiday_blocks(cal):
    """cal：交易日字串（遞增）。回傳 假日休市段 [(節前日 index, 名稱集合)]、非假日休市段 [(前一交易日, [平日休市日])]。"""
    H = holiday_names()
    cal = [str(x) for x in cal]
    blocks = []; other = []
    for i in range(len(cal) - 1):
        a = pd.Timestamp(cal[i]); b = pd.Timestamp(cal[i + 1])
        gap = pd.date_range(a + pd.Timedelta(days=1), b - pd.Timedelta(days=1))
        wk = [d for d in gap if d.weekday() < 5]
        if not wk:
            continue
        names = {H[d.strftime("%Y-%m-%d")] for d in gap if d.strftime("%Y-%m-%d") in H}
        if names:
            blocks.append((i, names))
        else:
            other.append((cal[i], [d.strftime("%Y-%m-%d") for d in wk]))
    return blocks, other


def lunar_check(cal):
    s = set(cal); bad = []; n = 0
    for y, ds in LUNAR.items():
        for d in ds:
            if cal[0] <= d <= cal[-1] and pd.Timestamp(d).weekday() < 5:
                n += 1
                if d in s:
                    bad.append(d)
    return {"落在平日的初一／端午／中秋": n, "其中有交易（不符）": bad}


def cal_events(cal):
    """甲的事件（entry index, exit index）。"""
    n = len(cal); m = np.array([d[:7] for d in cal])
    wd = pd.to_datetime(pd.Series(cal)).dt.weekday.to_numpy()
    ev = {}
    tom = []; tom3 = []
    for j in range(1, n - 3):
        if m[j] != m[j + 1] and m[j + 1] == m[j + 3]:
            tom.append((j - 1, j + 3)); tom3.append((j, j + 3))
    ev[CELL_A["甲1"]] = tom
    ev["甲1 另報：3 日讀法"] = tom3
    blocks, other = holiday_blocks(cal)
    ev[CELL_A["甲2"]] = [(i - 1, i) for i, nm in blocks if i >= 1]
    ev["甲2 另報：春節前"] = [(i - 1, i) for i, nm in blocks if i >= 1 and "春節" in nm]
    ev["甲2 另報：春節以外的節前"] = [(i - 1, i) for i, nm in blocks if i >= 1 and "春節" not in nm]
    ev[CELL_A["甲3"]] = [(i - 1, i) for i in range(1, n) if wd[i] == 0]
    for k in range(1, 5):
        ev[f"甲3 另報：{WK[k]}"] = [(i - 1, i) for i in range(1, n) if wd[i] == k]
    return ev, blocks, other


def tx_cost(Dd, e0, e1, fee, open_entry=False):
    """一筆的來回成本（比例）：進場一邊 ＋ 出場一邊 ＋ 持有期內轉倉兩邊。e0＝進場日 index（收盤進：e0 收盤；開盤進：e0 開盤），e1＝出場日（收盤）。"""
    e0 = np.asarray(e0, int); e1 = np.asarray(e1, int)
    roll = Dd["roll"]; mark = Dd["mark"]; ref = Dd["ref"]
    pin = Dd["rawO"][e0] if open_entry else ref[e0]
    rc = np.where(roll, X.cf(mark, fee) + X.cf(ref, fee), 0.0)
    S = np.r_[0.0, np.cumsum(rc)]                       # S[k] ＝ rc[0..k−1] 加總
    lo = e0 if open_entry else e0 + 1
    inside = np.where(e1 > lo, S[np.maximum(e1, lo)] - S[lo], 0.0)   # 轉倉日 ∈ [lo, e1−1]
    return X.cf(pin, fee) + X.cf(Dd["mark"][e1], fee) + inside


def judge2(a_, b_, key="X"):
    return bool(a_["CI不跨0"] and b_["CI不跨0"] and np.sign(a_[key]) == np.sign(b_[key]))


# ═════════════ 甲 ═════════════
def a_cells(series, cal, C, evs, segs, Dd=None):
    n = len(cal); calA = np.asarray(cal)
    mon = np.array([d[:7] for d in cal])
    rows = []; evrows = []
    for cell, lst in evs.items():
        e0 = np.array([a for a, b in lst], int); e1 = np.array([b for a, b in lst], int)
        ks = np.unique(e1 - e0); assert len(ks) == 1, cell
        k = int(ks[0])
        R = C[e1] / C[e0] - 1.0
        allR = np.full(n, np.nan); allR[k:] = C[k:] / C[:-k] - 1.0
        if Dd is not None:
            ch = tx_cost(Dd, e0, e1, FEE); cl = tx_cost(Dd, e0, e1, FEE_LO)
        for seg, (a, b) in segs.items():
            ins = (calA[e1] >= a) & (calA[e1] <= b)
            okb = (calA >= a) & (calA <= b) & np.isfinite(allR)
            base = float(np.mean(allR[okb]))
            st = X.cl_stats(R[ins] - base, mon[e1[ins]])
            row = {"序列": series, "格": cell, "段": seg, "持有根數": k, "n": st["n"], "事件平均": float(np.mean(R[ins])), "平常": base,
                   "X": st["mean"], "lo": st["lo"], "hi": st["hi"], "月數": st["months"], "事件勝率": float(np.mean(R[ins] > 0)),
                   "CI不跨0": bool(st["lo"] > 0 or st["hi"] < 0), "平常窗數": int(okb.sum()),
                   "起": str(calA[e1[ins]][0]), "迄": str(calA[e1[ins]][-1])}
            if Dd is not None:
                for lab, cc in (("高", ch), ("低", cl)):
                    t_ = X.cl_stats(R[ins] - cc[ins], mon[e1[ins]])
                    row.update({f"扣成本{lab}_平均": t_["mean"], f"扣成本{lab}_lo": t_["lo"], f"扣成本{lab}_hi": t_["hi"], f"平均來回成本{lab}": float(np.mean(cc[ins]))})
            rows.append(row)
            evrows.append(pd.DataFrame({"序列": series, "格": cell, "段": seg, "entry": calA[e0[ins]], "exit": calA[e1[ins]], "R": R[ins],
                                        "cost_hi": ch[ins] if Dd is not None else np.nan, "cost_lo": cl[ins] if Dd is not None else np.nan}))
    return rows, evrows


# ═════════════ 引擎（甲交易版、丁） ═════════════
def run_engine(Dd, IM, rate, Aop, Acl, t0, t1, fee=FEE):
    days = Dd["days"]; aC = Dd["adjC"]; aO = Dd["adjO"]; roll = Dd["roll"]; mark = Dd["mark"]; ref = Dd["ref"]; entry = Dd["entry"]; rawO = Dd["rawO"]
    cd = np.r_[0, np.diff(pd.to_datetime(pd.Series(days)).to_numpy()).astype("timedelta64[D]").astype(int)]
    n = len(days)
    u = np.full(n, np.nan); pos = np.zeros(n, int)
    E = 1.0; V = 0.0; p = 0
    trades = []; cost = 0.0; intr = 0.0
    u[t0] = 1.0
    q = int(Acl[t0])
    if q != 0:
        V = q * E; c = abs(V) * X.cf(ref[t0], fee); E -= c; cost += c; p = q; trades.append(t0)
    pos[t0] = p
    for t in range(t0 + 1, t1 + 1):
        imf = IM[t - 1] / (X.MULT * ref[t - 1]) if np.isfinite(IM[t - 1]) else 0.0
        rt = rate[t - 1] if np.isfinite(rate[t - 1]) else 0.0
        it = max(E - imf * abs(V), 0.0) * rt * cd[t] / 365.0
        g1 = aO[t] / aC[t - 1] - 1.0
        E += V * g1 + it; V *= 1.0 + g1; intr += it
        q = int(Aop[t])
        if q != p:
            c1 = abs(V) * X.cf(rawO[t], fee); E -= c1
            V = q * E; c2 = abs(V) * X.cf(rawO[t], fee); E -= c2
            cost += c1 + c2; p = q; trades.append(t)
        g2 = aC[t] / aO[t] - 1.0
        E += V * g2; V *= 1.0 + g2
        q = int(Acl[t])
        if roll[t]:
            c1 = abs(V) * X.cf(mark[t], fee); E -= c1
            V = q * E; c2 = abs(V) * X.cf(entry[t], fee); E -= c2
            cost += c1 + c2
            if q != p:
                trades.append(t)
            p = q
        elif q != p:
            c1 = abs(V) * X.cf(mark[t], fee); E -= c1
            V = q * E; c2 = abs(V) * X.cf(mark[t], fee); E -= c2
            cost += c1 + c2; p = q; trades.append(t)
        u[t] = E; pos[t] = p
    return u, pos, {"交易次數": len(trades), "成本合計（×期初）": cost, "利息合計（×期初）": intr}, np.array(trades, int)


def path_rows(days, u, pos, trades, segs, label, extra=None):
    rows = []
    for seg, (a, b) in segs.items():
        m = X.seg_metrics(days, u, a, b)
        ins = (days >= a) & (days <= b)
        yrs = (pd.Timestamp(b if b < str(days[-1]) else str(days[-1])) - pd.Timestamp(a)).days / 365.25
        nt = int(np.isin(trades, np.flatnonzero(ins)).sum())
        r = {"版": label, "段": seg, "年化": m["年化"], "最大回落": m["最大回落"], "回落比": m["回落比"], "年化波動": m["年化波動"], "年化÷波動": m["年化÷波動"],
             "窗": f"{m['起']}～{m['迄']}", "交易日": m["交易日"], "換手次數": nt, "換手次數／年": nt / yrs,
             "持多比例": float(np.mean(pos[ins] > 0)), "持空比例": float(np.mean(pos[ins] < 0))}
        if extra:
            r.update(extra)
        rows.append(r)
    return rows


def part_A(F, Dd, IM, rate):
    days = Dd["days"]; aC = Dd["adjC"]
    t1 = int(np.searchsorted(days, END, side="right")) - 1
    ev, blocks, other = cal_events(days)                  # 全日曆辨識；各段以出場日 ≤ 段尾（確認段尾 2026-09-30）截
    rows, evr = a_cells("TX 近月", days, aC, ev, SEG, Dd)
    td, tc = X.load_taiex()
    evi, bi, oi = cal_events(td)
    r2, e2 = a_cells("加權指數", td, tc, evi, IX_SEG)
    C = pd.DataFrame(rows + r2); C.to_csv(os.path.join(OUT, "A_cells.csv"), index=False, float_format="%.10g")
    pd.concat(evr + e2).to_csv(os.path.join(WORK, "A_events.csv.gz"), index=False)
    J = {}
    for key, cell in CELL_A.items():
        q = C[(C["序列"] == "TX 近月") & (C["格"] == cell)].set_index("段")
        a_, b_, e_ = q.loc["探索"], q.loc["確認"], q.loc["早年"]
        qi = C[(C["序列"] == "加權指數") & (C["格"] == cell)].iloc[0]
        has = judge2(a_, b_)
        trd = bool(has and a_["扣成本高_lo"] > 0 and b_["扣成本高_lo"] > 0)
        J[key] = {"格": cell, "有": has, "可交易": trd, "探索X": a_["X"], "確認X": b_["X"], "早年X（TX）": e_["X"], "早年X（加權指數 1990 起）": qi["X"],
                  "早年方向相反（TX）": bool(np.sign(e_["X"]) != np.sign(a_["X"])), "早年方向相反（加權指數）": bool(np.sign(qi["X"]) != np.sign(a_["X"])),
                  "扣成本高 探索lo": a_["扣成本高_lo"], "扣成本高 確認lo": b_["扣成本高_lo"],
                  "標籤": "有、可交易" if trd else ("有、扣成本後不可交易" if has else "測不出")}
    # 交易版（描述）
    n = len(days)
    paths = {}; trows = []
    seg_tr = {"早年": (str(days[T0 + 1]), SEG["早年"][1]), "探索": SEG["探索"], "確認": SEG["確認"]}
    ones = np.ones(n, int)
    u, pos, st, tr = run_engine(Dd, IM, rate, ones, ones, T0, t1)
    paths["hold"] = u
    trows += path_rows(days, u, pos, tr, seg_tr, "TX 一直持多 1 倍", {"格": "（對照）"})
    for key in ("甲1", "甲2", "甲3"):
        want = np.zeros(n, int)
        for e0, e1 in ev[CELL_A[key]]:
            want[e0:e1] = 1                                    # e0 收盤 ～ e1 收盤持有
        Aop = np.r_[0, want[:-1]]
        u, pos, st, tr = run_engine(Dd, IM, rate, Aop, want, T0, t1)
        paths[{"甲1": "A1", "甲2": "A2", "甲3": "A3"}[key]] = u
        trows += path_rows(days, u, pos, tr, seg_tr, f"{CELL_A[key]} 交易版", {"格": key, "成本合計（×期初）": st["成本合計（×期初）"]})
    T = pd.DataFrame(trows); T.to_csv(os.path.join(OUT, "A_trade.csv"), index=False, float_format="%.10g")
    S = {"判定": J, "N_單筆": 3, "有 格數": sum(v["有"] for v in J.values()), "可交易格數": sum(v["可交易"] for v in J.values()),
         "假日辨識": {"TX 假日休市段": len(blocks), "其中春節": sum("春節" in nm for _, nm in blocks),
                  "TX 非假日平日休市（颱風、地震、選舉等；⛔ 不算節前）": [{"前一交易日": d, "休市平日": w} for d, w in other],
                  "加權指數 假日休市段": len(bi), "加權指數 非假日休市段數": len(oi),
                  "農曆驗證（TX 日曆）": lunar_check(list(days)), "農曆驗證（加權指數日曆）": lunar_check(list(td))}}
    tv = T.set_index(["格", "段"])
    S["交易版"] = {k: {s: {"年化": tv.loc[(k, s), "年化"], "最大回落": tv.loc[(k, s), "最大回落"], "持多比例": tv.loc[(k, s), "持多比例"]} for s in seg_tr}
                for k in ("（對照）", "甲1", "甲2", "甲3")}
    beat = {s: bool(tv.loc[("甲1", s), "年化"] > tv.loc[("（對照）", s), "年化"]) for s in ("探索", "確認")}
    S["先驗①"] = {"月底月初「有」": J["甲1"]["有"], "月底月初交易版探索、確認年化都不贏一直持多": not any(beat.values()),
                 "節前、星期一 測不出": (not J["甲2"]["有"]) and (not J["甲3"]["有"])}
    return S, C, paths


# ═════════════ 丙 ═════════════
def rsi_wilder(c, n=2):
    d = np.diff(c); g = np.maximum(d, 0.0); l_ = np.maximum(-d, 0.0)
    out = np.full(len(c), np.nan)

    def val(ag, al):
        if al == 0:
            return 50.0 if ag == 0 else 100.0
        return 100.0 - 100.0 / (1.0 + ag / al)
    ag = float(g[:n].mean()); al = float(l_[:n].mean()); out[n] = val(ag, al)
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + g[i]) / n; al = (al * (n - 1) + l_[i]) / n
        out[i + 1] = val(ag, al)
    return out


def part_C(Dd):
    days = Dd["days"]; nd = len(days); aC = Dd["adjC"]; aO = Dd["adjO"]; r = Dd["r"]
    rsi = rsi_wilder(aC, 2)
    trig = {CELL_C["丙1"]: r <= -0.02, CELL_C["丙2"]: r <= -0.03, CELL_C["丙3"]: rsi <= 10.0, CELL_C["丙4"]: rsi <= 5.0}
    mon = np.array([d[:7] for d in days])
    rows = []; evs = []
    for H in HS:
        R = np.full(nd, np.nan); t = np.arange(nd - H)
        R[t] = aC[t + H] / aO[t + 1] - 1.0
        ch = np.full(nd, np.nan); cl = np.full(nd, np.nan)
        ch[t] = tx_cost(Dd, t + 1, t + H, FEE, True); cl[t] = tx_cost(Dd, t + 1, t + H, FEE_LO, True)
        for seg, (a, b) in SEG.items():
            ok = np.zeros(nd, bool)
            ok[t] = (days[t + 1] >= a) & (days[t + H] <= b) & np.isfinite(R[t])
            base = float(np.mean(R[ok]))
            for cell, tg in trig.items():
                e = ok & tg
                st = X.cl_stats(R[e] - base, mon[e])
                row = {"格": cell, "H": H, "段": seg, "n": st["n"], "事件平均": float(np.mean(R[e])) if e.any() else np.nan, "平常": base, "X": st.get("mean"),
                       "lo": st.get("lo"), "hi": st.get("hi"), "月數": st.get("months"), "事件勝率": float(np.mean(R[e] > 0)) if e.any() else np.nan,
                       "CI不跨0": bool(st["n"] and (st["lo"] > 0 or st["hi"] < 0)), "平常日數": int(ok.sum())}
                for lab, cc in (("高", ch), ("低", cl)):
                    t_ = X.cl_stats(R[e] - cc[e], mon[e])
                    row.update({f"扣成本{lab}_平均": t_.get("mean"), f"扣成本{lab}_lo": t_.get("lo"), f"扣成本{lab}_hi": t_.get("hi"),
                                f"平均來回成本{lab}": float(np.mean(cc[e])) if e.any() else np.nan})
                rows.append(row)
                evs.append(pd.DataFrame({"格": cell, "H": H, "段": seg, "signal": days[e], "R": R[e], "cost_hi": ch[e], "cost_lo": cl[e]}))
    pd.concat(evs).to_csv(os.path.join(WORK, "C_events.csv.gz"), index=False)
    pd.DataFrame({"date": days, "r": r, "rsi2": rsi}).to_csv(os.path.join(WORK, "C_signals.csv.gz"), index=False)
    C = pd.DataFrame(rows); C.to_csv(os.path.join(OUT, "C_cells.csv"), index=False, float_format="%.10g")
    J = {}
    for H in HS:
        per = {}
        for key, cell in CELL_C.items():
            q = C[(C["格"] == cell) & (C["H"] == H)].set_index("段")
            a_, b_, e_ = q.loc["探索"], q.loc["確認"], q.loc["早年"]
            has = judge2(a_, b_)
            trd = bool(has and a_["扣成本高_lo"] > 0 and b_["扣成本高_lo"] > 0)
            per[key] = {"有": has, "可交易": trd, "探索X": a_["X"], "確認X": b_["X"], "早年X": e_["X"], "早年CI不跨0": bool(e_["CI不跨0"]),
                        "早年方向相反": bool(np.sign(e_["X"]) != np.sign(a_["X"])), "n（早／探／確）": [int(e_["n"]), int(a_["n"]), int(b_["n"])]}
        nh = sum(v["有"] for v in per.values()); nt = sum(v["可交易"] for v in per.values())
        J[f"H{H}"] = {"格": per, "有 格數（/4）": nh, "可交易格數（/4）": nt, "H 有": nh >= 3, "H 可交易": nt >= 3,
                      "標籤": ("有、可交易（最多暫定）" if nt >= 3 else ("有、扣成本後不可交易（最多暫定）" if nh >= 3 else "測不出"))}
    early_only = all((not J[f"H{H}"]["H 有"]) for H in HS) and any(v["早年CI不跨0"] for H in HS for v in J[f"H{H}"]["格"].values())
    S = {"判定": J, "N_單筆": 3, "成立 H 數": sum(v["H 有"] for v in J.values()), "可交易 H 數": sum(v["H 可交易"] for v in J.values()),
         "同族註": "四格與舊件「RSI(14)＜30 站回」「低檔爆量長下影」同屬超賣後反彈一族；同族舊訊號已 0 格（期貨六題 己 改期貨成本重算亦 0 格）；本題若成立最多「暫定」、進前瞻紀錄，⛔ 不翻舊件。",
         "觸發日數（全期）": {k: int(np.nansum(v)) for k, v in trig.items()},
         "先驗③": {"測不出或只有早年有": all(not v["H 有"] for v in J.values()), "（描述、非先驗）早年有格區間不跨 0": early_only}}
    return S, C


# ═════════════ 丁 ═════════════
def part_D(Dd, IM, rate, e50):
    days = Dd["days"]; n = len(days); aC = Dd["adjC"]
    t1 = int(np.searchsorted(days, END, side="right")) - 1
    f50 = int(np.flatnonzero(np.isfinite(e50))[0])
    segs = {"早年": (str(days[f50 + 1]), SEG["早年"][1]), "探索": SEG["探索"], "確認": SEG["確認"]}
    m50 = {s: X.seg_metrics(days, e50, a, b) for s, (a, b) in segs.items()}
    rows = []; paths = {}
    ones = np.ones(n, int)
    u, pos, st, tr = run_engine(Dd, IM, rate, ones, ones, T0, t1)
    paths["D_hold"] = u
    rows += path_rows(days, u, pos, tr, segs, "TX 一直持多 1 倍（描述）", {"L": "—"})
    for L in LS:
        s = np.full(n, np.nan); s[L:] = aC[L:] / aC[:-L] - 1.0
        sig = np.zeros(n, int); cur = 0
        for t in range(n):
            if np.isfinite(s[t]) and s[t] > 0:
                cur = 1
            elif np.isfinite(s[t]) and s[t] < 0:
                cur = -1
            sig[t] = cur
        for ver, sg in (("多空", sig), ("只做多（描述）", np.maximum(sig, 0))):
            Aop = np.r_[0, sg[:-1]]; Aop[:T0 + 1] = 0
            Acl = Aop.copy()
            u, pos, st, tr = run_engine(Dd, IM, rate, Aop, Acl, T0, t1)
            paths[f"D_L{L}_{'ls' if ver == '多空' else 'lo'}"] = u
            rows += path_rows(days, u, pos, tr, segs, f"L{L} {ver}", {"L": L, "成本合計（×期初）": st["成本合計（×期初）"], "利息合計（×期初）": st["利息合計（×期初）"]})
    D = pd.DataFrame(rows)
    for s in segs:
        D.loc[D["段"] == s, "0050_年化"] = m50[s]["年化"]; D.loc[D["段"] == s, "0050_最大回落"] = m50[s]["最大回落"]
        D.loc[D["段"] == s, "0050_回落比"] = m50[s]["回落比"]
    D["判準（對 0050）"] = [X.judge_user({"年化": r["年化"], "回落比": r["回落比"]}, {"年化": r["0050_年化"], "回落比": r["0050_回落比"]}) for _, r in D.iterrows()]
    D.loc[~D["版"].str.endswith("多空"), "判準（對 0050）"] = D.loc[~D["版"].str.endswith("多空"), "判準（對 0050）"] + "（描述）"
    D.to_csv(os.path.join(OUT, "D_cells.csv"), index=False, float_format="%.10g")
    main = D[D["版"].str.endswith("多空")]
    per = {s: dict(zip(main[main["段"] == s]["L"], main[main["段"] == s]["判準（對 0050）"])) for s in segs}
    cnt = {s: {"合格": sum(v == "合格" for v in per[s].values()), "合格或另列": sum(v in ("合格", "另列") for v in per[s].values())} for s in segs}
    if cnt["探索"]["合格"] >= 3 and cnt["確認"]["合格"] >= 3:
        lab = "合格"
    elif cnt["探索"]["合格或另列"] >= 3 and cnt["確認"]["合格或另列"] >= 3:
        lab = "另列"
    else:
        lab = "不合格"
    S = {"判定": {"各段各 L": per, "各段合格數": cnt, "標籤": lab, "N_組合": 1},
         "0050": {s: {**{k: m50[s][k] for k in ("年化", "最大回落", "回落比")}, "窗": f"{m50[s]['起']}～{m50[s]['迄']}"} for s in segs},
         "先驗④": {"不合格": lab == "不合格"}}
    return S, D, paths


# ═════════════ 主流程 ═════════════
def body(a):
    T_ = time.time()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    S = {"件": REG, "讀法寫死": TAGT, "產出": X.now_tpe(), "GATE_V2": "本件無個股母體，不適用",
         "條款": "期交所原始數字只在私有庫與 ~/txfwork/short；本資料夾只放彙總", "沿用": "backtest/researchTXF.py（期貨六題 seq2）的資料讀取、主版轉倉、成本、CI、判準函式"}
    F = X.load_fut("TX")
    Dd = X.daily(F, 1, FEE)
    IM, MM = X.load_margin(F["days"]); rate, rinfo = X.load_rate(F["days"])
    S["資料"] = {"TX 一般盤交易日": [str(F["days"][0]), str(F["days"][-1]), int(len(F["days"]))], "結算價來源": F["settle_src"], "利率": rinfo,
               "私有庫 commit": subprocess.run(["git", "-C", "/home/chemtim/us-stock-data", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
               "0050 快照": X.SNAP_SHA, "early": X.EARLY_SHA, "路徑起點（index 60）": str(F["days"][T0])}
    log(f"[資料] TX {F['days'][0]}～{F['days'][-1]}｜起點 {F['days'][T0]}")
    paths = {}
    S["甲"], _, pa = part_A(F, Dd, IM, rate); paths.update({f"A_{k}": v for k, v in pa.items()})
    log(f"[甲] 有 {S['甲']['有 格數']}／3、可交易 {S['甲']['可交易格數']}｜{time.time() - T_:.0f}s")
    S["乙"] = {"狀態": "停判", "原因": "台指VIX 免費資料只有約 3 個月（2026-07 起），資料庫每日累積中；照登錄「缺 ⇒ 本題停」（台股 1006-1445）",
              "⛔": "不用 TXO 價格自行重算 VIX 代替", "N_單筆": "−6 待裁定核"}
    S["丙"], _ = part_C(Dd)
    log(f"[丙] 成立 H {S['丙']['成立 H 數']}／3、可交易 H {S['丙']['可交易 H 數']}｜{time.time() - T_:.0f}s")
    e50s, einfo = X.etf_close("0050")
    e50 = e50s.reindex(F["days"]).ffill().to_numpy(float)
    S["丁"], _, pd_ = part_D(Dd, IM, rate, e50); paths.update(pd_)
    S["丁"]["0050 接法"] = einfo
    log(f"[丁] {S['丁']['判定']['標籤']}｜{S['丁']['判定']['各段合格數']}｜{time.time() - T_:.0f}s")
    np.savez_compressed(os.path.join(WORK, "paths.npz"), days=F["days"], **paths)
    S["耗時s"] = round(time.time() - T_)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else (list(o) if isinstance(o, (set, np.ndarray)) else str(o)))
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完] {time.time() - T_:.0f}s")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", nargs="?", default="body", choices=["body", "page"])
    ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check:
        from backtest import researchTXS_check as K
        return K.main()
    if a.mode == "page":
        from backtest import researchTXS_page as P
        return P.main()
    body(a)


if __name__ == "__main__":
    main()
