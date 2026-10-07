# -*- coding: utf-8 -*-
"""USREG-A3／A4（裁定 seq318 §三，以美股登錄 seq2 sha bc0927fed5996fd4 發號，29 件）——開跑前清單（⛔ 不含任何報酬）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA34_prep --stage px   [--procs 3] [--lim N]
    ...                                                                       --stage fund
    ...                                                                       --stage report

判準：美股策略線 登錄全文 USREG-A3A4 seq1（sha 0dc16d3267725d7c，本體）＋seq2（sha bc0927fed5996fd4，去重、四件主臂改條件出場）；
      裁定 seq318 §三（發號 29 件；A3-9、A4-14 作廢；A4-2 依墨菲 seq4、A3-10 依爆量突破 seq2；四件主臂改條件；A4-3 營收創紀錄 20 日判；
      飆股用美股母體網格中位；先交「被換掉／拿掉的條件清單＋退化格清單＋各件 N 實數」，⛔ 不含報酬）；裁定 seq316（只 S&P 400 與合併兩者都過才合格）；
      裁定 seq311（飆股＝seq6 網格取格中位，⛔ 不寫 N 天漲一倍）。各件引用的台股原登錄見 ITEMS 表（檔名＋sha）。

⛔⛔ 本支只算：條件可不可得、覆蓋率、事件數、格數、退化格（觸發率 ＜1%／＞99%、兩格條件相同、事件數 ＜ 登錄門檻）。
   ⛔ 不算、不讀、不存任何報酬、勝率、飆股標籤（起漲日之後漲幅）、目標價達成、持有報酬；
   「事件之後」只讀【成交可不可行】與【條件出場訊號何時出現】（＝持有天數／段尾未出場；裁定 seq318「條件出場臂必報持有天數分佈」同一類），⛔ 不讀價差。
⛔⛔ 授權：us-stock-data 是私有 repo ⇒ resultsUSA34/prep/ 只放彙總（件數、比例、覆蓋率）；逐檔中間檔放 ~/us_work/a34/（repo 外）。

資料：~/usdata/881c86a（git archive 881c86a9a756，唯讀；＝ 開跑當下 us-stock-data main，origin/main 同 sha，台北 2026-10-07 09:1x 核過）；
      讀法照 backtest/researchUSA2_data.py（聯集轉接層 D1～D7，A2.install()）；價格、硬斷點、量照 researchUSM／researchUSX（V1～V5）。
偵測器（台股同一支，只 import、⛔ 一行未改）：patterns_all（型態全量）、patterns_x（W 底／頭肩底／箱型／杯柄）、researchRev（反轉訊號、上升趨勢線）、
      researchSig.sig_days（訊號系統 E1／E2／X）、researchExtAuth.detect／researchExtAuth2.detect_new（外部作者七顆＋三顆）、
      researchWeekly（週 K、四訊號）、researchWashDist（洗盤事件與四條）、researchNpattern（N字底／N型掃描）、researchLongD.box_machine、researchLongI.ichimoku。

═══ 執行者補讀法（登錄沒寫清楚 ⇒ 先寫死再算；台北 2026-10-07 09:14，寫死前 ⛔ 沒看任何本批美股數字）═══
 P1 窗 ＝ 2016-01-04 ～ 2026-09-30（登錄 §〇）。凡原登錄有「探索／確認」兩段者：探索 2016-01-04～2021-12-31｜確認 2022-01-03～2026-09-30
    （＝ A4-13 登錄寫明的切法，全批同一刀）；原登錄的「早年段」美股沒有資料 ⇒ 整段拿掉（⚠ 疑點 Q1：缺早年段是否一律「最多暫定」，請裁定）。
    例外：A4-11 機器學習 ＝ 訓練 至 2017-12、驗證 2018、探索 2019～2021、確認 2022～2026-09（台股原切法，美股資料同年份可得）；
          A3-17／A4-10 飆股 ＝ 台股 seq6 §十一：只用 2021-01～2026-09，找 2021～2023、驗 2024～2026-09。
 P2 母體 ＝ 當天在 S&P 500 或 S&P 400（聯集實體）且當天有有效 K 棒；三欄 ＝ 只 S&P 400／合併／只 S&P 500（事件日當天歸屬，A2 A1 同規則）。
 P3 價格面板從 2015-12-01 起（資料庫 panel 最早一列）⇒ 回看 200／250 日的條件最早約 2016-09～2016-12 才算得出：照實報覆蓋率，⛔ 不補。
 P4 台股「開盤漲停／跌停買不到」「處置／注意」「漲跌停天數」美股沒有 ⇒ 拿掉（USREG-X V4／V5 先例）；T+1 沒有有效 K 棒 ⇒ 剔除。
 P5 硬斷點 ＝ 轉接層 hard_break（seam／split_div）＋ 任一天沒有有效 K 棒（MB.Stk.brk）；範圍照各原登錄（型態視窗＋未來窗）。
 P6 季營收同義版（登錄 §〇 ①）：「創 N 月新高」⇒「創 ⌈N÷3⌉ 季新高」＝ 最新一季（可用日 ≤ d）＞ 之前 ⌈N÷3⌉−1 季每一季（要求最近 ⌈N÷3⌉ 季連續都有值）；
    「月營收年增率」⇒「季營收年增率」＝ 最新一季 ÷ 期末日早 350～380 天那一季 − 1（分母 ≤ 0 ⇒ 缺）；「近 3 個月累計年增」⇒ ⌈3÷3⌉＝1 季 ⇒ 與單季年增率相同；
    「月增率」⇒「季增率」（最新一季 ÷ 前一季 − 1）；「連續 N 個月年增」⇒ 連續 ⌈N÷3⌉ 季年增 ＞ 0。可用日 ＝ first_filed 次一交易日（登錄 §〇）。
    「最新一季」須新鮮：期末日距量測日 ≤ 200 天（10-K 最晚 90 天＋一季），否則當缺。
 P7 季財報量（A4）：TTM ＝ 最近 4 個連續（相鄰期末差 60～120 天）已可用單季相加；「年」＝ first_form 為 10-K 的那一季期末（會計年度末）往回 4 季相加；
    期末權益／資產 ＝ 該期末 instant 值；負債 ＝ 資產 − 權益（含非控制權益者優先，缺用權益）；EPS（美股 B1 沒有）⇒ 年淨利 ÷ 年末前最新封面股數（代理，⚠ 標）。
 P8 市值 ＝ 量測日前一交易日【原始】收盤 × 封面股數（filed ＜ 量測日的最新 as_of_date；同一 as_of_date 多個類別相加；
    as_of_date 之後、量測日之前的 Yahoo 拆股事件乘回）；股數距量測日 ＞ 400 天當缺。本益比 ＝ 市值 ÷ TTM 淨利（淨利 ≤ 0 ⇒ 不符）。
    周轉率 TO(L) ＝ L 日均量（Yahoo 量已按之後所有拆股調整）÷ 股數（同樣乘到「今天的股數基準」）。
 P9 類股（A4-5、A4-6）：GICS 歷史版（B3）；層級 ＝ sector（11）與 sub-industry 兩層都報「成分 ≥5 的類別數」，
    主讀法 ＝ 兩層中「成分 ≥5 類別數」月中位最接近台股產業別數（約 30）的那一層（⭐ 只看類別數、⛔ 不看任何報酬；結果寫在報告）。
 P10 A4-6 產業營收換股日：台股「M＋1 月 10 日」是月營收法定期限；美股季報 10-K 最晚 90 天 ⇒ 換股月照台股 1、4、7、10 月的第一個交易日，
    用「期末日 ≤ 換股日 − 90 天的最近一個曆季」（Jan ⇒ 前一年 Q3、Apr ⇒ Q4、Jul ⇒ Q1、Oct ⇒ Q2）；只收可用日 ≤ 換股日的公司。
 P11 A4-7 庫藏股代理 ＝ 季買回金額（quarterly_buyback，現金流量表）÷ 市值，可用日 ＝ first_filed 次一交易日；登錄「前 x%」的 x 沒寫 ⇒ 本步只報覆蓋，
    x 請裁定（⚠ 疑點 Q6）。成分剔除 ＝ membership changes 的 removed（生效日 ＝ date 欄）；「公告日後進場」臂：資料沒有公告日 ⇒ 拿掉。
 P12 A3-11 件 I 母體甲「臺灣50 成分」⇒ 當月 S&P 500 成分中市值前 50（代理，⚠ 標；疑點 Q5）；乙 ＝ 全母體。件 I 原「TEJ 用過的期間只描述」
    是台股期間 ⇒ 美股全窗都是沒看過的資料 ⇒ 全窗判（主格甲 × k3）。同理 A4-3 X1、X2 的「原文期間」是台股期間 ⇒ 美股全窗判。
 P13 型態全量（A3-5）：USREG-X 測過的五型（箱型、杯柄、W 底、頭肩底、旗形）本來就不在 96 變體內（台股型態全量 §一 已排除）⇒ 扣 0；
    判定格 ＝ 96 變體 × H20、H60；n_eff（合併欄）≥ 30 才可判定、計 N；只 S&P 400 欄 n_eff ＜ 30 的格另列（⇒ 依構造最多「事後擴母體」）。
    「無影」用還原價同日逐位相等（同日還原係數相同 ⇒ 與原始價等價，patterns_all A5 註）。
 P14 週線（A3-8）：週 K ＝ researchWeekly.weekly_bars；斷點週與前後各 1 週不產生訊號；暖機 ＝ 週 K ≥ 35 根（MACD 26＋9）才收訊號；
    同檔同訊號 8 週內只算第一次；k 週持有須 k 週後仍在窗內。
 P15 突破過濾（A3-13）：F 三道全加 ＝ D（T 日放量）與 B（第 b 日 ≥ N×1.03）都成立後，從 b＋1 起到 T＋20 照 E 找回測日；同檔同型 20 日先合併再剔除（型態全量 Q2 順序）。
 P16 洗盤（A3-16）：硬斷點範圍 ＝ [P−60, T＋H]；事件 T 須 T＋1 有效 K 棒；分組照 researchWashDist.conds；⛔ 不算 T 之後是否創前高（事後標籤）。
 P17 N字底／N型（A3-3）：掃描照 researchNpattern（ndb_candidates／ndb_scan／nwave_scan）；量能四條照其 R6；
    事件數報「不去重」版（台股 R13 的去重要用出場日 ＝ 停損／目標價路徑 ⇒ 本步不讀）⇒ 為上限；P 臂（法人）拿掉 ⇒ 與 M 相同 ⇒ 退化。
 P18 條件出場的「段尾未出場」與「每年觸發」：以事件為單位（每個進場訊號各自往後找第一個出場訊號，⛔ 不模擬組合、不讀價差）。
 P19 A3-10 平均持有天數：同檔一次只持一筆（作者原文 not is_in_position），訊號 t ⇒ t＋1 開盤進、第一個收盤 ＜ EMA(L) 的 x ⇒ x＋1 開盤出；持有 ＝ x − t 根。
 P20 A3-14 W2 年線戰法基本面（A4-9）：「最近一期月營收 YoY ＞ 0」⇒ 最新一季季營收 YoY ＞ 0；「最近一季淨利由負轉正」照字面（季淨利，不需換）；兩者「或」。
    ⚠ 登錄 A4-9 名稱寫「季淨利轉正版」，本步照全批規則兩條都留（疑點 Q7）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA2_data as A2
A2.install()
from backtest import us_data as U
from backtest import researchUSM as RU
from backtest import researchUSM_body as MB
from backtest import researchUSX as USX
from backtest import patterns_all as PA
from backtest import patterns_x as PX
import researchRev as RV
import researchSig as RS
import researchExtAuth as EA
import researchExtAuth2 as EA2
from backtest import researchWeekly as RW
import researchWashDist as RWD
from backtest import researchNpattern as NP
from backtest import researchLongD as LD
from backtest import researchLongI as LI

READ_TS = "2026-10-07 09:14（台北）"
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/prep")
WORK = os.path.expanduser("~/us_work/a34")
W0, W1 = pd.Timestamp("2016-01-04"), pd.Timestamp("2026-09-30")
EXP_END = pd.Timestamp("2021-12-31")
SURGE0, SURGE_CONF = pd.Timestamp("2021-01-04"), pd.Timestamp("2024-01-01")
COLS = ("合併", "只400", "只500")
_G: dict = {}


# ═════════════ 小工具 ═════════════
def popcnt(x):
    return bin(x).count("1")


def bitmask(idx):
    m = 0
    for i in set(int(v) for v in idx):
        m |= 1 << i
    return m


def pack(T, m4, m5, MON, w0, seg_pos):
    """kept 事件日（日曆位置）⇒ {欄: [n, n探索, n確認, 月 bitmask, 20 日區段 bitmask, 60 日區段 bitmask]}。"""
    T = np.asarray(T, int)
    out = {}
    for col in COLS:
        sel = T if col == "合併" else (T[m4[T]] if col == "只400" else T[m5[T]])
        if len(sel) == 0:
            out[col] = [0, 0, 0, 0, 0, 0]
            continue
        out[col] = [int(len(sel)), int((sel <= seg_pos).sum()), int((sel > seg_pos).sum()),
                    bitmask(MON[sel]), bitmask((sel - w0) // 20), bitmask((sel - w0) // 60)]
    return out


def add_pack(acc, p):
    for col, v in p.items():
        a = acc.setdefault(col, [0, 0, 0, 0, 0, 0])
        a[0] += v[0]; a[1] += v[1]; a[2] += v[2]; a[3] |= v[3]; a[4] |= v[4]; a[5] |= v[5]


def merge_first(T, first, S, H, lo, hi, merge=20, need_next=True):
    """型態全量 Q2 順序：窗內且在母體 ⇒ 先合併（上一個未被合併者的 (t0, t0＋merge]）⇒ 再剔除（硬斷點 [first, T＋H]、T＋1 無有效 K 棒）。"""
    acc = Counter(); keep = []; t0 = -10 ** 9
    for T_, f_ in sorted(zip(T, first)):
        if not (lo <= T_ <= hi):
            continue
        if not (S.member[T_] and S.valid[T_]):
            acc["窗內不在母體"] += 1
            continue
        acc["原始"] += 1
        if t0 < T_ <= t0 + merge:
            acc["合併掉"] += 1
            continue
        t0 = T_
        if T_ + H >= S.n or S.brk(f_, T_ + H):
            acc["剔除_硬斷點"] += 1
            continue
        if need_next and not S.valid[T_ + 1]:
            acc["剔除_T+1無K棒"] += 1
            continue
        acc["保留"] += 1
        keep.append(T_)
    return keep, acc


def keep_first(T, first, S, H, lo, hi, merge=20):
    """H2／USM 順序：被剔除者不開合併窗。"""
    acc = Counter(); keep = []; t0 = -10 ** 9
    for T_, f_ in sorted(zip(T, first)):
        if not (lo <= T_ <= hi):
            continue
        if not (S.member[T_] and S.valid[T_]):
            acc["窗內不在母體"] += 1
            continue
        acc["原始"] += 1
        if t0 < T_ <= t0 + merge:
            acc["合併掉"] += 1
            continue
        if T_ + H >= S.n or S.brk(f_, T_ + H):
            acc["剔除_硬斷點"] += 1
            continue
        if not S.valid[T_ + 1]:
            acc["剔除_T+1無K棒"] += 1
            continue
        acc["保留"] += 1
        keep.append(T_); t0 = T_
    return keep, acc


def roll_mean(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def first_exit(entries, exits, end):
    """每個進場訊號 t（日曆位置）⇒ 第一個 ≥ t＋1 的出場訊號；≤ end 才算 ⇒ (觸發數, 段尾未出場數, 持有天數 list)。"""
    ex = np.asarray(sorted(set(int(x) for x in exits)), int)
    trig = 0; tail = 0; hold = []
    for t in entries:
        i = int(np.searchsorted(ex, t + 1))
        if i < len(ex) and ex[i] <= end:
            trig += 1; hold.append(int(ex[i] - t))
        else:
            tail += 1
    return trig, tail, hold


# ═════════════ 價格：讀檔 ═════════════
_RC = {}


def _raw_close_src(src):
    if src in _RC:
        return _RC[src]
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(U._p("prices_yahoo", f + ".csv"), usecols=["date", "close"], dtype={"date": str})
    else:
        d = pd.read_csv(U._p("prices", f + ".csv"), usecols=["date", "close"], dtype={"date": str})
    s = pd.Series(d["close"].to_numpy(float), index=pd.DatetimeIndex(pd.to_datetime(d["date"])))
    _RC[src] = s
    return s


def raw_close_aligned(t, cal, valid):
    pn = U.panel(t)
    R = np.full(len(cal), np.nan)
    for src, g in pn.groupby("src", sort=False):
        s = _raw_close_src(src)
        idx = g.index[g.index.isin(cal)]
        R[cal.get_indexer(idx)] = s.reindex(idx).to_numpy(float)
    R[~valid] = np.nan
    return R


# ═════════════ worker：每檔價量 ═════════════
def _init(d):
    _G.update(d)


def px_one(t):
    cal = _G["cal"]; n = len(cal); w0 = _G["w0"]; w1 = _G["w1"]; MON = _G["MON"]; sp = _G["seg_pos"]
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A = RU.prep(df, cal)
    if len(A["bars"]) < 30:
        return None
    Lw = MB.low_aligned(df, cal)
    m5, m4 = A2.idx_member(t, cal)
    m5 = np.asarray(m5, bool); m4 = np.asarray(m4, bool); member = m5 | m4
    S = MB.Stk(t, A, Lw, member, RU.span_start_array(t, cal), w0, w1)
    O, H, C, valid, bars = A["O"], A["H"], A["C"], A["valid"], A["bars"]
    V = USX.volume_aligned(t, cal, valid)
    RCl = raw_close_aligned(t, cal, valid)
    ob, hb, lb, cb, vb = O[bars], H[bars], Lw[bars], C[bars], V[bars]
    nb = len(bars)
    pbdays = set(cal[A["pb"]])
    R = {"t": t}
    expo = valid & member
    R["expo"] = {"合併": int(expo[w0:w1 + 1].sum()), "只400": int((valid & m4)[w0:w1 + 1].sum()), "只500": int((valid & m5)[w0:w1 + 1].sum())}
    R["expo_seg"] = [int(expo[w0:sp + 1].sum()), int(expo[sp + 1:w1 + 1].sum())]
    tocal = lambda arr: bars[np.asarray(arr, int)] if len(arr) else np.zeros(0, int)

    # ── A3-1 H1 月線 3 日站回 ──
    sma = roll_mean(cb, 20)
    smac = np.full(n, np.nan); smac[bars] = sma
    acc = Counter(); grpT = {"站回": [], "未站回": []}; kept_t0 = -10 ** 9
    for i in range(25, nb):
        if not (sma[i] > sma[i - 5] and cb[i] < sma[i] and cb[i - 1] >= sma[i - 1]):
            continue
        T = int(bars[i])
        if not (w0 <= T <= w1 - 23):
            continue
        if not (member[T] and valid[T]):
            continue
        acc["原始"] += 1
        if T <= kept_t0 + 23:
            acc["合併掉"] += 1; continue
        if S.brk(T - 24, T):
            acc["剔除_事前硬斷點"] += 1; continue
        if T + 4 >= n or not valid[T + 1:T + 4].all():
            acc["無法分組"] += 1; continue
        g = "站回" if any(C[T + s] >= smac[T + s] for s in (1, 2, 3)) else "未站回"
        if S.brk(T + 1, T + 23) or not valid[T + 4]:
            acc["剔除_未來窗_" + g] += 1; continue
        acc["保留_" + g] += 1; grpT[g].append(T); kept_t0 = T
    R["H1"] = {"acc": acc, "站回": pack(grpT["站回"], m4, m5, MON, w0, sp), "未站回": pack(grpT["未站回"], m4, m5, MON, w0, sp)}

    # ── A3-2 H2 144／200 雙翻揚 ──
    ma144 = roll_mean(cb, 144); ma200 = roll_mean(cb, 200)
    ev = []
    for i in range(205, nb):
        mx, mx1 = max(ma144[i], ma200[i]), max(ma144[i - 1], ma200[i - 1])
        if ma144[i] > ma144[i - 5] and ma200[i] > ma200[i - 5] and cb[i] >= mx and cb[i - 1] < mx1:
            ev.append((int(bars[i]), int(bars[i - 199])))
    kp, acc = keep_first([e[0] for e in ev], [e[1] for e in ev], S, 20, w0, w1 - 20)
    R["H2"] = {"acc": acc, "p": pack(kp, m4, m5, MON, w0, sp)}

    # ── A3-4 上升趨勢線跌破（主格 甲 兩點法 R＝5、1% 穿越）──
    ul = RV.up_line_events(ob, lb, cb)
    kp, acc = keep_first([int(bars[a]) for a, _ in ul], [int(bars[b]) for _, b in ul], S, 20, w0, w1 - 20)
    R["UT"] = {"acc": acc, "p": pack(kp, m4, m5, MON, w0, sp)}

    # ── A3-5 型態全量 96 變體 ──
    det = PA.detect_all(ob, hb, lb, cb, np.nan_to_num(vb), ob, hb, lb, cb)
    R["PAT"] = {}
    s06_days = np.zeros(0, int)
    for vid, e in det.items():
        Tc = tocal(e["T"]); Fc = tocal(e["first"])
        if vid == PA.vid_s(6):
            s06_days = Tc
        rr = {}
        for Hh in (20, 60):
            kp, acc = merge_first(Tc, Fc, S, Hh, w0, w1 - Hh)
            rr[Hh] = {"acc": acc, "p": pack(kp, m4, m5, MON, w0, sp)}
        R["PAT"][vid] = rr

    # ── A3-8 週線四訊號 ──
    wk = _G["wk"]; wl = _G["wl"]
    wks, WO, WH, WL, WC, WV = RW.weekly_bars(valid, O, H, Lw, C, np.nan_to_num(V), wk)
    R["WK"] = {}
    wk_w1 = int(wk[w1])
    if len(wks) > 40:
        sig = RW.signals(WO, WH, WL, WC, WV)
        badw = np.zeros(int(wk.max()) + 3, bool); badw[wk[A["pb"]]] = True
        near = badw[wks] | badw[np.maximum(wks - 1, 0)] | badw[wks + 1]
        ix = np.flatnonzero(valid); w_ = wk[ix]; stt = np.r_[0, np.flatnonzero(np.diff(w_)) + 1]; en = np.r_[stt[1:], len(ix)] - 1
        wlast = ix[en]
        for s_ in RW.SIGS:
            last = -10 ** 9; Ts = []
            for i in np.flatnonzero(sig[s_]):
                if i < 35 or near[i]:
                    continue
                if wks[i] - last <= 8:
                    continue
                d = int(wlast[i])
                if not (w0 <= d <= w1) or not (member[d] and valid[d]):
                    continue
                last = wks[i]
                Ts.append((d, int(wks[i])))
            for k in (4, 8, 12, 26):
                ok = [d for d, w in Ts if w + k <= wk_w1]
                R["WK"][(s_, k)] = pack(ok, m4, m5, MON, w0, sp)

    # ── A3-13 突破過濾（W 底、頭肩底、箱型 × B～F）──
    fd = pd.DataFrame({"open": O, "high": H, "low": Lw, "close": C, "volume": np.nan_to_num(V), "traded": valid}, index=cal)
    fr = PX.frame_open(fd, pbdays)
    BRK = {}
    for kind in ("w", "hs"):
        r = PX.detect_turn(kind, cb)
        BRK[kind] = [(int(bars[e["T"]]), int(bars[e["first"]]), float(e["level"])) for e in r["events"]]
    BRK["box"] = [(int(e["T"]), int(e["first"]), float(e["level"])) for e in PX.box_events(fr)]
    R["BF"] = {}
    for kind, evs in BRK.items():
        lv = {T_: L_ for T_, _, L_ in evs}
        kp, acc = merge_first([e[0] for e in evs], [e[1] for e in evs], S, 60, w0, w1 - 60)
        st = Counter()
        for T_ in kp:
            N_ = lv[T_]
            st["事件"] += 1
            # B 幅度
            bday = -1
            for d in range(T_, T_ + 5):
                if d < n and valid[d] and C[d] >= N_ * 1.03:
                    bday = d; break
            if bday >= 0 and bday + 1 < n and valid[bday + 1]:
                st["B_買到"] += 1; st["B_同A日"] += int(bday == T_)
            # C 站穩
            if kind != "box" and T_ + 3 < n and valid[T_:T_ + 3].all() and (C[T_:T_ + 3] > N_).all() and valid[T_ + 3]:
                st["C_買到"] += 1
            # D 放量
            pv = V[T_ - 5:T_]
            dok = bool(np.isfinite(pv).all() and pv.mean() > 0 and np.isfinite(V[T_]) and V[T_] >= 1.5 * pv.mean())
            if dok:
                st["D_買到"] += 1; st["D_同A日"] += 1

            def e_search(d0, d1):
                for d in range(d0, min(d1, n - 2) + 1):
                    if not valid[d]:
                        continue
                    if C[d] < N_ * 0.97:
                        return -1
                    if not (Lw[d] <= N_ * 1.02 and C[d] >= N_):
                        continue
                    pv_ = V[d - 5:d]
                    if not (np.isfinite(pv_).all() and np.isfinite(V[d]) and V[d] < pv_.mean()):
                        continue
                    o_, h_, l_, c_ = O[d], H[d], Lw[d], C[d]
                    B_ = abs(c_ - o_); Rg = h_ - l_
                    Up = h_ - max(o_, c_); Dn = min(o_, c_) - l_
                    ham = Rg > 0 and B_ > 0.1 * Rg and Dn >= 2 * B_ and Up <= 0.1 * Rg
                    q = d - 1
                    eng = (valid[q] and C[q] < O[q] and c_ > o_ and max(o_, c_) >= max(O[q], C[q]) and min(o_, c_) <= min(O[q], C[q])
                           and B_ > abs(C[q] - O[q]))
                    if ham or eng:
                        return d
                return -1
            ed = e_search(T_ + 1, T_ + 20)
            if ed >= 0 and valid[ed + 1]:
                st["E_買到"] += 1
            if dok and bday >= 0:
                fdd = e_search(bday + 1, T_ + 20)
                if fdd >= 0 and valid[fdd + 1]:
                    st["F_買到"] += 1
        R["BF"][kind] = {"acc": acc, "st": st, "p": pack(kp, m4, m5, MON, w0, sp)}

    # ── A3-16 洗盤還是出貨 ──
    R["WASH"] = {}
    vb0 = np.nan_to_num(vb)
    ma60b = roll_mean(cb, 60)
    for Uu in RWD.US:
        for Dd in RWD.DS:
            E_, norb, short = RWD.find_events(cb, Uu, Dd, True)
            for (P_, j_, L_, T_) in E_:
                Tc = int(bars[T_])
                if not (w0 <= Tc <= w1 - 5) or not (member[Tc] and valid[Tc]):
                    continue
                if Tc + 1 >= n or not valid[Tc + 1]:
                    continue
                seg = 0 if Tc <= sp else 1
                col4 = bool(m4[Tc])
                for Pthr in RWD.PS:
                    for sup in RWD.SUPS:
                        cd = RWD.conds(cb, vb0, P_, L_, T_, Pthr, sup, ma60b[T_])
                        nw = sum(x[0] for x in cd.values()); nd = sum(x[1] for x in cd.values())
                        grp = "洗盤" if nw == 4 else ("出貨" if nd >= 3 else "混合")
                        for Hh in (5, 20, 60):
                            if Tc + Hh > w1 or S.brk(int(bars[max(P_ - 60, 0)]), Tc + Hh):
                                continue
                            key = (Uu, Dd, Pthr, sup, Hh, grp, seg)
                            a = R["WASH"].setdefault(key, [0, 0, 0])
                            a[0] += 1; a[1] += int(col4); a[2] += int(m5[Tc])

    # ── A3-3 N字底／N型（不去重版事件數）──
    i0 = int(np.searchsorted(bars, max(w0 - 120, 0)))
    NPc = {"N1S": np.zeros((2, 3, 4, NP.NSC), int), "N2S": np.zeros((2, 3, 4, NP.NSC), int),
           "N1M": np.zeros((2, 3, 4, NP.NSC, 12), int), "N2M": np.zeros((2, 3, 4, NP.NSC, 36), int),
           "TS": np.zeros((2, 3, len(NP.REDS), len(NP.NWS)), int), "TM": np.zeros((2, 3, len(NP.REDS), len(NP.NWS)), int)}
    if nb > 80:
        cands = NP.ndb_candidates(hb, lb, max(i0, 40))
        ND = NP.ndb_scan(cb, hb, lb, cands)
        cs = np.r_[0.0, np.cumsum(vb0)]
        mv = lambda a, b: (cs[b + 1] - cs[a]) / (b - a + 1) if b >= a else np.nan
        seen = {}
        for (sc, i, hpos, d1, res, j, sf, b, B_, plo1, plo2) in ND:
            q = sum(d1 >= x for x in NP.D1S) - 1
            if q < 0:
                continue
            pre = mv(hpos - 20, hpos - 1); dn = mv(hpos + 1, i); rb = mv(i + 1, j)
            for kind, s_ in (("1", sf if res == 1 else -1), ("2", b)):
                if s_ < 0:
                    continue
                d = int(bars[s_])
                if not (w0 <= d <= w1 - 1) or not (member[d] and valid[d]) or not valid[d + 1]:
                    continue
                if S.brk(int(bars[max(hpos - 20, 0)]), d):
                    continue
                key = (kind, sc, d)
                prev = seen.get(key)
                if prev is not None and prev[0] >= i:
                    continue
                rt = mv(j + 1, sf)
                vd = vb0[s_] / mv(s_ - 20, s_ - 1) if kind == "2" and mv(s_ - 20, s_ - 1) > 0 else np.nan
                seen[key] = (i, q, pre, dn, rb, rt, vd, d)
        for (kind, sc, d), (i, q, pre, dn, rb, rt, vd, _) in seen.items():
            seg = 0 if d <= sp else 1
            cols = [0] + ([1] if m4[d] else []) + ([2] if m5[d] else [])
            M = []
            for a1 in NP.V1:
                for a2 in NP.V2:
                    for a3 in NP.V3:
                        ok = (pre > 0 and dn < pre * a1 and dn > 0 and rb > dn * a2 and rb > 0 and rt < rb * a3)
                        if kind == "1":
                            M.append(ok)
                        else:
                            for a4 in NP.V4:
                                M.append(bool(ok and np.isfinite(vd) and vd > a4))
            M = np.array(M, bool)
            for cI in cols:
                for qq in range(q + 1):
                    NPc["N%sS" % kind][seg, cI, qq, sc] += 1
                    NPc["N%sM" % kind][seg, cI, qq, sc] += M
        F = NP.red_flags(cb, ob, hb, lb)
        NW = NP.nwave_scan(cb, hb, lb, vb0, F, max(i0, 1))
        seenT = {}
        for (r_, wi, res, kf, viol) in NW:
            if res != 1:
                continue
            d = int(bars[kf])
            if not (w0 <= d <= w1 - 1) or not (member[d] and valid[d]) or not valid[d + 1]:
                continue
            for qv in np.flatnonzero(F[r_]):
                key = (int(qv), wi, d)
                if key not in seenT or seenT[key][0] < r_:
                    seenT[key] = (r_, bool(viol))
        for (qv, wi, d), (r_, viol) in seenT.items():
            seg = 0 if d <= sp else 1
            cols = [0] + ([1] if m4[d] else []) + ([2] if m5[d] else [])
            for cI in cols:
                NPc["TS"][seg, cI, qv, wi] += 1
                NPc["TM"][seg, cI, qv, wi] += int(not viol)
    R["NP"] = NPc

    # ── A3-6／A3-7 訊號系統（E1、E2、X）＋ 均線穿越出場 ──
    SG, _ = RS.sig_days(O, H, Lw, C, np.nan_to_num(V), O, H, Lw, C, fd, pbdays, n)
    inwin = lambda arr: np.asarray([d for d in arr if w0 <= d <= w1 and member[d] and valid[d]], int)
    R["SIG"] = {k: pack(inwin(v), m4, m5, MON, w0, sp) for k, v in SG.items()}
    E1d = sorted(set().union(*[set(SG.get("E:" + k, [])) for k in RS.E1]))
    E2d = sorted(set().union(*[set(SG.get("E:" + k, [])) for k in RS.E2]))
    Xall = sorted(set().union(*[set(SG.get("X:" + k, [])) for k in RS.XS]))
    madn = {}
    for k in (10, 20, 60):
        m = roll_mean(cb, k); x = np.zeros(nb, bool)
        with np.errstate(invalid="ignore"):
            x[1:] = (cb[:-1] >= m[:-1]) & (cb[1:] < m[1:])
        madn[k] = bars[np.flatnonzero(x)]
    R["MADN"] = {k: int(len(inwin(v))) for k, v in madn.items()}
    R["SYS"] = {}
    for fam, Ed in (("E1", E1d), ("E2", E2d)):
        for segn, (lo, hi) in (("探索", (w0, sp)), ("確認", (sp + 1, w1))):
            ent = [d for d in Ed if lo <= d <= hi - 1 and member[d] and valid[d]]
            for xo in ["ANY"] + list(RS.XS):
                xs = Xall if xo == "ANY" else list(SG.get("X:" + xo, []))
                xset = set(xs)
                e2 = [d for d in ent if d not in xset]
                tr, ta, hd = first_exit(e2, xs, hi)
                R["SYS"][(fam, segn, "X:" + xo)] = (len(e2), tr, ta, float(np.median(hd)) if hd else np.nan)
            for k in (10, 20, 60):
                tr, ta, hd = first_exit(ent, madn[k], hi)
                R["SYS"][(fam, segn, "MA%d" % k)] = (len(ent), tr, ta, float(np.median(hd)) if hd else np.nan)

    # ── A3-10 爆量突破＋跌破 EMA ──
    redk = cb > ob
    va = pd.Series(vb).rolling(20, min_periods=20).mean().shift(1).to_numpy()
    ema = {L: pd.Series(cb).ewm(span=L, adjust=False).mean().to_numpy() for L in (5, 10, 20, 60)}
    R["VB"] = {}
    for Bb in (5, 10, 20, 60, 120):
        hh = pd.Series(hb).rolling(Bb, min_periods=Bb).max().shift(1).to_numpy()
        with np.errstate(invalid="ignore"):
            brk = (cb > hh) & redk & np.isfinite(hh)
        for kk in (None, 1.5, 2.0, 3.0):
            with np.errstate(invalid="ignore"):
                sig_ = brk if kk is None else (brk & np.isfinite(va) & (va > 0) & (vb > kk * va))
            sidx = np.flatnonzero(sig_)
            for L in (5, 10, 20, 60):
                below = cb < ema[L]
                for segn, (lo, hi) in (("探索", (w0, sp)), ("確認", (sp + 1, w1))):
                    trades = 0; holds = []; tail = 0; nxt = -1
                    for i in sidx:
                        d = int(bars[i])
                        if i < 3 * L or not (lo <= d <= hi - 1) or not (member[d] and valid[d]) or i < nxt:
                            continue
                        xs = np.flatnonzero(below[i + 1:]) + i + 1
                        trades += 1
                        if len(xs) and bars[xs[0]] <= hi:
                            holds.append(int(xs[0] - i)); nxt = int(xs[0]) + 1
                        else:
                            tail += 1; nxt = 10 ** 9
                    R["VB"][(Bb, kk, L, segn)] = (trades, tail, float(np.sum(holds)), len(holds))

    # ── A3-11 件 D 週線達華斯、件 I 一目 ──
    R["DARVAS"] = []
    if len(wks) > 60:
        near2 = badw[wks] | badw[np.maximum(wks - 1, 0)] | badw[wks + 1]
        for bb, s_, top, bot, bfin in LD.box_machine(WH, WL, WC, near2, 52):
            d = int(wlast[bb])
            if not (w0 <= d <= w1) or not member[d]:
                continue
            R["DARVAS"].append((int(wks[bb]), int(wks[s_]) if s_ is not None else -1, bool(m4[d]), bool(m5[d])))
    cond, ok, tk, kj, sa, sbb = LI.ichimoku(hb, lb, cb)
    sigI = np.flatnonzero(cond[1:] & ok[:-1] & ~cond[:-1]) + 1
    R["ICHI"] = [int(bars[k_]) for k_ in sigI if k_ >= 77 and w0 <= bars[k_] <= w1 - 1 and member[bars[k_]] and valid[bars[k_] + 1]]

    # ── A3-14／A3-15 外部作者 ──
    ex, first = EA.detect(ob, hb, lb, cb, vb0)
    ex2 = EA2.detect_new(ob, hb, lb, cb, vb0)
    R["EXT"] = {}
    codes = {"W1": ex["W1"], "Y1": ex["Y1"], "Y2in": ex["Y2in"], "Y2out": ex["Y2out"], "Y3": ex["Y3"], "Y5": ex["Y5"],
             "S1": ex2["S1"], "F1": ex2["F1"], "F1c": ex2["F1c"], "O1": ex2["O1"]}
    madn_cal = {k: madn[k] for k in (10, 20, 60)}
    o1low = dict(zip([int(bars[j]) for j in ex2["O1"]], ex2["O1_low"]))
    for code, arr in codes.items():
        days = inwin(bars[np.asarray(arr, int)] if len(arr) else [])
        R["EXT"][code] = pack(days, m4, m5, MON, w0, sp)
        if code in ("W1", "Y1", "Y2in", "Y3", "F1", "F1c", "O1"):
            for segn, (lo, hi) in (("探索", (w0, sp)), ("確認", (sp + 1, w1))):
                ent = [d for d in days if lo <= d <= hi - 1]
                for k in (10, 20, 60):
                    tr, ta, hd = first_exit(ent, madn_cal[k], hi)
                    R["EXT"][(code, segn, "MA%d" % k)] = (len(ent), tr, ta)
                if code == "O1":
                    tr = ta = 0
                    for d in ent:
                        lowk = o1low[d]
                        xs = np.flatnonzero((C[d + 1:hi + 1] < lowk) & valid[d + 1:hi + 1])
                        if len(xs):
                            tr += 1
                        else:
                            ta += 1
                    R["EXT"][(code, segn, "OWN")] = (len(ent), tr, ta)
    # W2 候選（基本面在主行程判）
    R["W2c"] = [(int(bars[s]), int(bars[j])) for s, j in ex["W2c"] if w0 <= bars[j] <= w1 - 1 and member[bars[j]] and valid[bars[j]]]

    # ── 每月量測日快照（A3-11 T、A3-12、A4 各件的價格欄；⛔ 只存 e−1 以前的量）──
    rows = []
    rsi14 = RW.rsi(cb, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        ma = {k: roll_mean(cb, k) for k in (5, 10, 20, 50, 60, 100, 150, 200)}
        hi250 = pd.Series(cb).rolling(250, min_periods=250).max().to_numpy()
        lo250 = pd.Series(cb).rolling(250, min_periods=250).min().to_numpy()
        ret = np.r_[np.nan, cb[1:] / cb[:-1] - 1]
        amt = cb * vb0
        amt20p = pd.Series(amt).rolling(20, min_periods=20).mean().shift(1).to_numpy()
        v20 = roll_mean(vb0, 20); v250 = roll_mean(vb0, 250)
        hi250d = np.zeros(nb, bool); hi250d[249:] = cb[249:] >= hi250[249:]
    tdb = set(SG.get("E:TD", [])); rsb = set(SG.get("E:RSI", [])); tlx = set(SG.get("X:TL", [])); vsc = set(SG.get("X:VSc", []))
    s06 = set(int(x) for x in s06_days)
    hi_days = set(int(x) for x in bars[hi250d])
    for mi, e in enumerate(_G["MSTART"]):
        kb = int(np.searchsorted(bars, e)) - 1
        if kb < 0 or not (m5[e] or m4[e]):
            continue
        dlast = int(bars[kb])
        if e - dlast > 5:
            continue
        rw = {"t": t, "mi": mi, "e": int(e), "m5": bool(m5[e]), "m4": bool(m4[e]), "rc": float(RCl[dlast]), "nbar": kb + 1}

        def rN(nn):
            return float(cb[kb] / cb[kb - nn] - 1) if kb - nn >= 0 else np.nan
        rw.update({"r21": rN(21), "r60": rN(60), "r63": rN(63), "r126": rN(126), "r189": rN(189), "r252": rN(252),
                   "r12_1": float(cb[kb - 21] / cb[kb - 252] - 1) if kb - 252 >= 0 else np.nan,
                   "vol60": float(np.std(ret[kb - 59:kb + 1], ddof=1)) if kb >= 60 else np.nan,
                   "tv100n": int(np.isfinite(ret[max(kb - 99, 0):kb + 1]).sum()),
                   "v20": float(np.mean(vb0[kb - 19:kb + 1])) if kb >= 19 else np.nan,
                   "v60": float(np.mean(vb0[kb - 59:kb + 1])) if kb >= 59 else np.nan,
                   "v120": float(np.mean(vb0[kb - 119:kb + 1])) if kb >= 119 else np.nan,
                   "vr20_250": float(v20[kb] / v250[kb]) if np.isfinite(v250[kb]) and v250[kb] > 0 else np.nan,
                   "d250hi": float(cb[kb] / hi250[kb]) if np.isfinite(hi250[kb]) else np.nan,
                   "c_ma60": float(cb[kb] / ma[60][kb] - 1) if np.isfinite(ma[60][kb]) else np.nan,
                   "stack": bool(ma[5][kb] > ma[10][kb] > ma[20][kb] > ma[60][kb]) if np.isfinite(ma[60][kb]) else np.nan})
        if np.isfinite(ma[200][kb]) and kb >= 249 + 21:
            m200_21 = ma[200][kb - 21]
            t17 = (cb[kb] > ma[150][kb] and cb[kb] > ma[200][kb] and ma[150][kb] > ma[200][kb] and ma[200][kb] > m200_21
                   and ma[50][kb] > ma[150][kb] and ma[50][kb] > ma[200][kb] and cb[kb] > ma[50][kb]
                   and cb[kb] >= lo250[kb] * 1.30 and cb[kb] >= hi250[kb] * 0.75)
            rw["tmpl17"] = bool(t17)
        else:
            rw["tmpl17"] = np.nan
        rw["rs"] = (2 * rw["r63"] + rw["r126"] + rw["r189"] + rw["r252"]) if np.isfinite(rw["r252"]) else np.nan
        # ⑤ 強勢股（漲停那條拿掉 ⇒ 4 條中 ≥3）
        if kb >= 249 and np.isfinite(ma[100][kb]) and np.isfinite(amt20p[kb]) and amt20p[kb] > 0:
            c1 = rN(20) >= 0.30; c3 = amt[kb] / amt20p[kb] >= 3.0; c4 = cb[kb] > ma[100][kb]; c5 = bool(hi250d[kb])
            rw["strong"] = bool((int(c1) + int(c3) + int(c4) + int(c5)) >= 3)
        else:
            rw["strong"] = np.nan
        for L in (5, 20, 60):
            lo_ = e - L; hi_ = e - 1
            rw["hi250_L%d" % L] = any(lo_ <= d <= hi_ for d in hi_days) if kb >= 249 else np.nan
            rw["td9_L%d" % L] = any(lo_ <= d <= hi_ for d in tdb)
            rw["rsi_L%d" % L] = any(lo_ <= d <= hi_ for d in rsb)
            rw["s06_L%d" % L] = any(lo_ <= d <= hi_ for d in s06)
            rw["utb_L%d" % L] = any(lo_ <= d <= hi_ for d in tlx)
            rw["vsc_L%d" % L] = any(lo_ <= d <= hi_ for d in vsc)
        rows.append(rw)
    R["MONTH"] = rows

    # ── A3-17 飆股價量特徵：二元特徵逐股日觸發率（2021-01～窗尾、在母體）──
    sd = _G["surge0"]
    with np.errstate(invalid="ignore", divide="ignore"):
        Kk, Dk = RW.kd(cb, hb, lb)
        kgt = np.nan_to_num(Kk) > 80
        run3 = np.zeros(nb, bool); rr_ = 0
        for i in range(nb):
            rr_ = rr_ + 1 if kgt[i] else 0
            run3[i] = rr_ >= 3
        sd20 = pd.Series(cb).rolling(20, min_periods=20).std(ddof=0).to_numpy()
        K2 = (cb > ma[20] + 2 * sd20) & (amt >= 2 * amt20p)
        K3 = rsi14 > 50
        r6 = RW.rsi(cb, 6); r12 = RW.rsi(cb, 12)
        K3b = np.r_[False, (r6[:-1] <= r12[:-1]) & (r6[1:] > r12[1:])]
        mx3 = np.fmax(np.fmax(ma[5], ma[10]), ma[20]); mn3 = np.fmin(np.fmin(ma[5], ma[10]), ma[20])
        tangle = pd.Series(mx3).shift(1).rolling(20, min_periods=20).max().to_numpy() / pd.Series(mn3).shift(1).rolling(20, min_periods=20).min().to_numpy() - 1 <= 0.02
        body = (cb - ob) / ob
        K4 = tangle & (body >= 0.04) & (cb > ma[20]) & (cb > ma[100]) & (amt >= 2 * amt20p)
        c60x = pd.Series(cb).shift(1).rolling(60, min_periods=60).max().to_numpy(); c60n = pd.Series(cb).shift(1).rolling(60, min_periods=60).min().to_numpy()
        amt120p = pd.Series(amt).rolling(120, min_periods=120).mean().shift(21).to_numpy()
        V1f = (c60x / c60n - 1 <= 0.25) & (amt20p <= 0.7 * amt120p) & (cb > c60x) & (amt >= 2 * amt20p)
        e5 = pd.Series(cb).ewm(span=5, adjust=False).mean().to_numpy(); e10 = pd.Series(cb).ewm(span=10, adjust=False).mean().to_numpy()
        e20 = pd.Series(cb).ewm(span=20, adjust=False).mean().to_numpy()
        X3f = (np.fmax(np.fmax(e5, e10), e20) / np.fmin(np.fmin(e5, e10), e20) - 1 <= 0.02) & np.r_[np.zeros(3, bool), (e5[3:] > e5[:-3]) & (e10[3:] > e10[:-3]) & (e20[3:] > e20[:-3])]
        MA100 = cb > ma[100]
        STK = (ma[5] > ma[20]) & (ma[20] > ma[60]) & (ma[60] > ma[100])
        a20 = roll_mean(amt, 20)
        SHR = a20 <= 0.7 * amt120p
        X1f = (pd.Series(cb).pct_change(60).to_numpy() >= 0.10) & (pd.Series(cb).pct_change(60).to_numpy() <= 0.30) & (pd.Series(cb).pct_change(20).to_numpy() <= 0.03)
    feats = {"K1 KD 高檔鈍化（K＞80 連 3 日）": run3, "K2 布林上軌帶量突破": K2, "K3 RSI14＞50": K3, "K3b RSI6 上穿 RSI12": K3b,
             "K4 均線糾結後發動": K4, "V1 量縮盤整後帶量突破": V1f, "X1 篩選（價部分；額門檻是橫斷面另算）": X1f, "X3 EMA 糾結向上": X3f,
             "收盤站上 MA100": MA100, "均線多頭排列 5＞20＞60＞100": STK, "量縮狀態（20 日均額 ≤ 前 120 日 ×0.7）": SHR}
    selb = (bars >= sd) & (bars <= w1)
    selm = selb & member[bars] & np.isfinite(ma[100])
    R["SURGE"] = {}
    for k, arr in feats.items():
        a = np.nan_to_num(arr.astype(float)) > 0
        R["SURGE"][k] = (int((a & selm).sum()), int(selm.sum()), int((a & selm & m4[bars]).sum()), int((selm & m4[bars]).sum()))
    return R


# ═════════════ SPY 層（A3-6 0050 層的美股代理）═════════════
def spy_layer(cal):
    d = pd.read_csv(U._p("macro", "yahoo_SPY.csv"), dtype={"date": str})
    d.index = pd.to_datetime(d["date"]); d = d.reindex(cal)
    k = d["adjclose"] / d["close"]
    O = (d["open"] * k).to_numpy(float); H = (d["high"] * k).to_numpy(float)
    L = (d["low"] * k).to_numpy(float); C = (d["close"] * k).to_numpy(float); V = d["volume"].to_numpy(float)
    valid = np.isfinite(C)
    fd = pd.DataFrame({"open": O, "high": H, "low": L, "close": C, "volume": np.nan_to_num(V), "traded": valid}, index=cal)
    SG, _ = RS.sig_days(O, H, L, C, np.nan_to_num(V), O, H, L, C, fd, set(), len(cal))
    return SG


# ═════════════ 季財報（主行程）═════════════
FIELDS = {"revenue": None, "net_income": "quarterly_net_income.csv", "operating_income": "quarterly_operating_income.csv",
          "rnd": "quarterly_rnd.csv", "assets": "quarterly_assets.csv", "equity": "quarterly_equity.csv",
          "equity_nci": "quarterly_equity_incl_nci.csv", "cfo": "quarterly_cfo.csv", "buyback": "quarterly_buyback.csv"}


def load_fund(cal):
    out = {}
    for f, fn in FIELDS.items():
        if f == "revenue":
            a = pd.read_csv(U._p("fundamentals", "quarterly_revenue.csv"), dtype={"ticker": str, "cik": str})
            b = pd.read_csv(U._p("fundamentals", "quarterly_revenue_sp400.csv"), dtype={"ticker": str, "cik": str})
            q = pd.concat([a, b.drop(columns=["index"])], ignore_index=True)
        else:
            q = pd.read_csv(U._p("fundamentals", fn), dtype={"ticker": str, "cik": str}).drop(columns=["index"])
        q = q[["ticker", "period_start", "period_end", "value", "first_filed", "first_form", "derived"]].copy()
        q["period_end"] = pd.to_datetime(q["period_end"]); q["first_filed"] = pd.to_datetime(q["first_filed"])
        q = q.sort_values(["ticker", "period_end", "first_filed"]).drop_duplicates(["ticker", "period_end"], keep="first")
        i = cal.searchsorted(q["first_filed"].values, side="right")
        q["av"] = np.where(i < len(cal), i, 10 ** 9)
        q["fy"] = q["first_form"].astype(str).str.startswith("10-K")
        out[f] = {t: (g["period_end"].values.astype("datetime64[D]").astype(np.int64), g["value"].to_numpy(float), g["av"].to_numpy(int), g["fy"].to_numpy(bool))
                  for t, g in q.groupby("ticker")}
    sh = pd.read_csv(U._p("fundamentals", "shares_outstanding.csv"), dtype={"ticker": str, "share_class": str})
    sh["as_of_date"] = pd.to_datetime(sh["as_of_date"]); sh["filed"] = pd.to_datetime(sh["filed"])
    sh = sh.dropna(subset=["shares"])
    sh = sh.groupby(["ticker", "as_of_date", "filed"], as_index=False)["shares"].sum()
    i = cal.searchsorted(sh["filed"].values, side="right")
    sh["av"] = np.where(i < len(cal), i, 10 ** 9)
    out["shares"] = {t: (g["as_of_date"].values.astype("datetime64[D]").astype(np.int64), g["shares"].to_numpy(float), g["av"].to_numpy(int))
                     for t, g in sh.sort_values(["ticker", "as_of_date"]).groupby("ticker")}
    spl = {}
    for fn in os.listdir(U._p("events_yahoo")):
        d = pd.read_csv(U._p("events_yahoo", fn), dtype=str)
        d = d[d["type"] == "split"]
        if len(d):
            r = d["value"].str.split("/", expand=True).astype(float)
            spl[fn[:-4]] = (pd.to_datetime(d["date"]).values.astype("datetime64[D]").astype(np.int64), (r[0] / r[1]).to_numpy())
    out["splits"] = spl
    return out


def q_last(F, f, t, e, k, stale=200, edays=None):
    """最近 k 個連續已可用單季（可用日 ≤ e、期末日距 e ≤ stale 天）⇒ (期末日陣列, 值陣列, fy 陣列) 或 None。"""
    x = F[f].get(t)
    if x is None:
        return None
    pe, v, av, fy = x
    m = np.flatnonzero(av <= e)
    if len(m) < k:
        return None
    sel = m[-k:]
    if edays - pe[sel[-1]] > stale:
        return None
    if k > 1:
        dd = np.diff(pe[sel])
        if not ((dd >= 60) & (dd <= 120)).all():
            return None
    if not np.isfinite(v[sel]).all():
        return None
    return pe[sel], v[sel], fy[sel]


def yoy_of(F, f, t, e, edays):
    x = F[f].get(t)
    if x is None:
        return np.nan
    pe, v, av, fy = x
    m = np.flatnonzero(av <= e)
    if not len(m):
        return np.nan
    j = m[-1]
    if edays - pe[j] > 200:
        return np.nan
    pk = m[(pe[m] >= pe[j] - 380) & (pe[m] <= pe[j] - 350)]
    if not len(pk) or not (v[pk[-1]] > 0) or not np.isfinite(v[j]):
        return np.nan
    return v[j] / v[pk[-1]] - 1


def fy_series(F, f, t, e, nyears, stale=500, edays=None):
    """最近 nyears 個會計年度（10-K 那一季為年末；年值 ＝ 年末往回 4 個連續季相加）⇒ list 或 None。"""
    x = F[f].get(t)
    if x is None:
        return None
    pe, v, av, fy = x
    m = np.flatnonzero(av <= e)
    ends = [j for j in m if fy[j]]
    if len(ends) < nyears:
        return None
    ends = ends[-nyears:]
    if edays - pe[ends[-1]] > stale:
        return None
    vals = []
    for j in ends:
        k = int(np.searchsorted(m, j))
        if k < 3:
            return None
        sel = m[k - 3:k + 1]
        dd = np.diff(pe[sel])
        if not ((dd >= 60) & (dd <= 120)).all() or not np.isfinite(v[sel]).all():
            return None
        vals.append(float(v[sel].sum()))
    return vals, [int(pe[j]) for j in ends]


def inst_at(F, f, t, pe_target, e):
    x = F[f].get(t)
    if x is None:
        return np.nan
    pe, v, av, fy = x
    j = np.flatnonzero((pe == pe_target) & (av <= e))
    return float(v[j[0]]) if len(j) else np.nan


def shares_at(F, t, e, edays, today_basis=False):
    x = F["shares"].get(t)
    if x is None:
        return np.nan
    ad, sh, av = x
    m = np.flatnonzero(av <= e)
    if not len(m):
        return np.nan
    j = m[np.argmax(ad[m])]
    if edays - ad[j] > 400:
        return np.nan
    s = sh[j]
    sp = F["splits"].get(t)
    if sp is not None:
        sd, r = sp
        hi = np.iinfo(np.int64).max if today_basis else edays
        sel = (sd > ad[j]) & (sd <= hi)
        s *= float(np.prod(r[sel])) if sel.any() else 1.0
    return float(s)


def fund_month(F, M, cal, sec):
    """每股-月：季財報量的可得性與條件（⛔ 不讀價格以外的任何未來資料；價格只用 e−1 收盤算市值）。"""
    out = []
    cal_days = cal.values.astype("datetime64[D]").astype(np.int64)
    for r in M.itertuples(index=False):
        t, e = r.t, r.e
        ed = int(cal_days[e])
        rw = {"t": t, "mi": r.mi}
        y0 = yoy_of(F, "revenue", t, e, ed)
        rw["rev_yoy"] = y0
        q8 = q_last(F, "revenue", t, e, 8, edays=ed)
        rw["rev_hi8"] = (bool(q8[1][-1] > q8[1][:-1].max())) if q8 is not None else np.nan
        q2 = q_last(F, "revenue", t, e, 2, edays=ed)
        rw["rev_qoq"] = (q2[1][1] / q2[1][0] - 1) if (q2 is not None and q2[1][0] > 0) else np.nan
        # 前一季的年增（R1 轉折、A4-6 A3 用）
        x = F["revenue"].get(t)
        y1 = np.nan
        if x is not None and np.isfinite(y0):
            pe, v, av, fy = x
            m = np.flatnonzero(av <= e)
            if len(m) >= 2:
                j1 = m[-2]; pk = m[(pe[m] >= pe[j1] - 380) & (pe[m] <= pe[j1] - 350)]
                if len(pk) and v[pk[-1]] > 0:
                    y1 = v[j1] / v[pk[-1]] - 1
        rw["rev_yoy_prev"] = y1
        tt = {}
        for f in ("net_income", "operating_income", "revenue", "rnd"):
            q4 = q_last(F, f, t, e, 4, edays=ed)
            tt[f] = float(q4[1].sum()) if q4 is not None else np.nan
        rw.update({"ttm_" + k: v for k, v in tt.items()})
        qn = q_last(F, "net_income", t, e, 2, edays=ed)
        rw["ni_turn"] = (bool(qn[1][1] > 0 and qn[1][0] <= 0)) if qn is not None else np.nan
        qe = q_last(F, "equity", t, e, 2, edays=ed); qa = q_last(F, "assets", t, e, 2, edays=ed)
        eq0 = qe[1][1] if qe is not None else np.nan; eqm = qe[1].mean() if qe is not None else np.nan
        as0 = qa[1][1] if qa is not None else np.nan; asm = qa[1].mean() if qa is not None else np.nan
        rw["roe"] = tt["net_income"] / eqm if (np.isfinite(eqm) and eqm > 0) else np.nan
        rw["oia"] = tt["operating_income"] / as0 if (np.isfinite(as0) and as0 > 0) else np.nan
        rw["roa"] = tt["net_income"] / asm if (np.isfinite(asm) and asm > 0) else np.nan
        rw["rnd_int"] = tt["rnd"] / tt["revenue"] if (np.isfinite(tt["revenue"]) and tt["revenue"] > 0 and np.isfinite(tt["rnd"])) else np.nan
        # 營益率比去年同季升（飆股財報特徵）
        qo = q_last(F, "operating_income", t, e, 5, edays=ed); qr = q_last(F, "revenue", t, e, 5, edays=ed)
        if qo is not None and qr is not None and qr[1][0] > 0 and qr[1][-1] > 0 and qo[0][-1] == qr[0][-1]:
            rw["opm_up_yoy"] = bool(qo[1][-1] / qr[1][-1] > qo[1][0] / qr[1][0])
        else:
            rw["opm_up_yoy"] = np.nan
        # 市值、本益比、淨值比、買回、周轉率
        shs = shares_at(F, t, e, ed); shs_today = shares_at(F, t, e, ed, today_basis=True)
        mcap = shs * r.rc if np.isfinite(shs) and np.isfinite(r.rc) else np.nan
        rw["mcap"] = mcap
        rw["pe"] = mcap / tt["net_income"] if (np.isfinite(mcap) and np.isfinite(tt["net_income"]) and tt["net_income"] > 0) else np.nan
        rw["pe_computable"] = bool(np.isfinite(mcap) and np.isfinite(tt["net_income"]))
        rw["bp"] = eq0 / mcap if (np.isfinite(mcap) and mcap > 0 and np.isfinite(eq0)) else np.nan
        qb = q_last(F, "buyback", t, e, 1, edays=ed)
        rw["bb_mcap"] = qb[1][0] / mcap if (qb is not None and np.isfinite(mcap) and mcap > 0) else np.nan
        for L, col in ((20, "v20"), (60, "v60"), (120, "v120")):
            vv = getattr(r, col)
            rw["to%d" % L] = vv / shs_today if (np.isfinite(shs_today) and shs_today > 0 and np.isfinite(vv)) else np.nan
        # 墨菲／喜偉／歐沙那希（年度）
        q12o = q_last(F, "operating_income", t, e, 12, edays=ed); q12r = q_last(F, "revenue", t, e, 12, edays=ed)
        if q12o is not None and q12r is not None and (q12r[1] > 0).all() and (q12o[0] == q12r[0]).all():
            rw["M1"] = bool(np.mean(q12o[1] / q12r[1]) > 0.10)
        else:
            rw["M1"] = np.nan
        ni5 = fy_series(F, "net_income", t, e, 5, edays=ed)
        roe5 = roa5 = dr5 = np.nan
        if ni5 is not None:
            eqs = [inst_at(F, "equity", t, p, e) for p in ni5[1]]
            ass = [inst_at(F, "assets", t, p, e) for p in ni5[1]]
            eqn = [inst_at(F, "equity_nci", t, p, e) for p in ni5[1]]
            if all(np.isfinite(x_) and x_ > 0 for x_ in eqs):
                roe5 = float(np.mean([a / b for a, b in zip(ni5[0], eqs)]))
            if all(np.isfinite(x_) and x_ > 0 for x_ in ass):
                roa5 = float(np.mean([a / b for a, b in zip(ni5[0], ass)]))
                eqx = [(n_ if np.isfinite(n_) else q_) for n_, q_ in zip(eqn, eqs)]
                if all(np.isfinite(x_) for x_ in eqx):
                    dr5 = float(np.mean([(a - b) / a for a, b in zip(ass, eqx)]))
        rw["M2"] = (roe5 > 0.08) if np.isfinite(roe5) else np.nan
        rw["O1"] = (roa5 > 0.08) if np.isfinite(roa5) else np.nan
        rw["X2"] = (dr5 < 0.30) if np.isfinite(dr5) else np.nan
        rv4 = fy_series(F, "revenue", t, e, 4, edays=ed)
        if rv4 is not None and all(x_ > 0 for x_ in rv4[0][:-1]):
            rw["M3"] = bool(np.mean([rv4[0][i + 1] / rv4[0][i] - 1 for i in range(3)]) > 0.10)
        else:
            rw["M3"] = np.nan
        rw["M4"] = bool(rw["rnd_int"] > 0.05) if np.isfinite(rw["rnd_int"]) else False
        rw["M4_rnd_avail"] = bool(np.isfinite(rw["rnd_int"]))
        ni4 = fy_series(F, "net_income", t, e, 4, edays=ed)
        if ni4 is not None:
            eps = []
            for v_, p_ in zip(ni4[0], ni4[1]):
                s_ = shares_at(F, t, e, p_ + 1)
                eps.append(v_ / s_ if np.isfinite(s_) and s_ > 0 else np.nan)
            if all(np.isfinite(eps)):
                g = [(eps[i + 1] / eps[i] - 1) if eps[i] > 0 else None for i in range(3)]
                rw["O3"] = bool(all(x_ is not None for x_ in g) and np.mean(g) > 0.30)
                rw["O3_computable"] = True
            else:
                rw["O3"] = np.nan; rw["O3_computable"] = False
        else:
            rw["O3"] = np.nan; rw["O3_computable"] = False
        rw["PE15"] = bool(rw["pe"] < 15) if np.isfinite(rw["pe"]) else (False if rw["pe_computable"] else np.nan)
        s_ = sec.get(t)
        gs = gsub = None
        if s_ is not None:
            for vf, vt, a_, b_ in s_:
                if vf <= ed and (vt is None or ed < vt):
                    gs, gsub = a_, b_
        rw["sector"] = gs; rw["subind"] = gsub
        out.append(rw)
    return pd.DataFrame(out)


def load_sectors():
    s = pd.read_csv(U._p("sectors", "sector_pit.csv"), dtype=str, keep_default_na=False)
    toD = lambda x: int(np.datetime64(x, "D").astype(np.int64)) if x else None
    out = defaultdict(list)
    for r in s.itertuples(index=False):
        out[r.ticker].append((toD(r.valid_from), toD(r.valid_to), r.gics_sector, r.gics_sub_industry))
    return out


# ═════════════ 主流程 ═════════════
def setup():
    calF = U.load_calendar(); cal = calF[calF >= MB.CAL0]; n = len(cal)
    w0 = int(cal.searchsorted(W0)); w1 = int(cal.searchsorted(W1))
    assert cal[w0] == W0 and cal[w1] == W1, (cal[w0], cal[w1])
    sp = int(cal.searchsorted(EXP_END, side="right")) - 1
    MON = np.array([(d.year - 2016) * 12 + d.month - 1 for d in cal]); MON[MON < 0] = 0
    ms = pd.Series(np.arange(n), index=cal)
    ms = ms[(ms.index >= W0) & (ms.index <= W1)]
    MSTART = ms.groupby([ms.index.year, ms.index.month]).first().to_numpy()
    wk, wf, wl = RW.weeks_of(cal)
    return {"cal": cal, "w0": w0, "w1": w1, "seg_pos": sp, "MON": MON, "MSTART": MSTART, "wk": wk, "wf": wf, "wl": wl,
            "surge0": int(cal.searchsorted(SURGE0)), "surge_conf": int(cal.searchsorted(SURGE_CONF))}


def stage_px(a):
    os.makedirs(WORK, exist_ok=True)
    d = setup()
    tick = [t for t in A2.tickers_all() if t not in set(A2.no_ohlc_tickers())]
    if a.lim:
        tick = tick[::max(1, len(tick) // a.lim)]
    t0 = time.time()
    res = []
    with Pool(a.procs, initializer=_init, initargs=(d,)) as pool:
        for i, r in enumerate(pool.imap_unordered(px_one, tick, chunksize=2)):
            if r is not None:
                res.append(r)
            if (i + 1) % 100 == 0:
                print("[px] %d／%d  %.0fs" % (i + 1, len(tick), time.time() - t0), flush=True)
    spy = spy_layer(d["cal"])
    with open(os.path.join(WORK, "px%s.pkl" % ("_lim" if a.lim else "")), "wb") as f:
        pickle.dump({"res": res, "spy": spy, "n_tick": len(tick), "secs": time.time() - t0}, f)
    print("[px] 完成 %d 檔（可用 %d）%.0fs" % (len(tick), len(res), time.time() - t0), flush=True)


def stage_fund(a):
    d = setup(); cal = d["cal"]
    P = pickle.load(open(os.path.join(WORK, "px%s.pkl" % ("_lim" if a.lim else "")), "rb"))
    M = pd.DataFrame([rw for r in P["res"] for rw in r["MONTH"]])
    t0 = time.time()
    F = load_fund(cal)
    sec = load_sectors()
    FM = fund_month(F, M, cal, sec)
    M = M.merge(FM, on=["t", "mi"], how="left")
    M.to_pickle(os.path.join(WORK, "month%s.pkl" % ("_lim" if a.lim else "")))
    # X3 季營收創紀錄、W2 基本面、A4-6 產業營收、A4-7 剔除事件
    xtra = {}
    cal_days = cal.values.astype("datetime64[D]").astype(np.int64)
    memb = {}
    for r in P["res"]:
        memb[r["t"]] = r
    # X3：事件 T ＝ 可用日；> 之前所有季（≥ 8 季歷史）
    ev = []
    for t, (pe, v, av, fy) in F["revenue"].items():
        o = np.argsort(pe); pe, v, av = pe[o], v[o], av[o]
        for j in range(8, len(v)):
            if np.isfinite(v[j]) and v[j] > np.nanmax(v[:j]) and av[j] < len(cal):
                ev.append((t, int(av[j])))
    xtra["X3_raw"] = ev
    sh = {}
    pk = os.path.join(WORK, "x3m%s.pkl" % ("_lim" if a.lim else ""))
    pickle.dump({"X3": ev}, open(pk, "wb"))
    # W2 基本面
    w2 = Counter(); w2_days = []
    for r in P["res"]:
        t = r["t"]
        for s, j in r["W2c"]:
            sd_ = int(cal_days[s])
            y = yoy_of(F, "revenue", t, s, sd_)
            qn = q_last(F, "net_income", t, s, 2, edays=sd_)
            turn = bool(qn[1][1] > 0 and qn[1][0] <= 0) if qn is not None else None
            comp = np.isfinite(y) or (turn is not None)
            w2["候選（技術面成立）"] += 1
            w2["基本面可算"] += int(comp)
            if (np.isfinite(y) and y > 0) or turn:
                w2["成立"] += 1; w2_days.append((t, j))
    xtra["W2"] = dict(w2); xtra["W2_days"] = w2_days
    pickle.dump({"X3": ev, "W2": dict(w2), "W2_days": w2_days}, open(pk, "wb"))
    print("[fund] 股-月 %d 列｜%.0fs" % (len(M), time.time() - t0), flush=True)


# ═════════════ 彙總（report）═════════════
def pct(a, b):
    return (100.0 * a / b) if b else float("nan")


def stage_report(a):
    d = setup(); cal = d["cal"]; w0, w1, sp = d["w0"], d["w1"], d["seg_pos"]
    tag = "_lim" if a.lim else ""
    P = pickle.load(open(os.path.join(WORK, "px%s.pkl" % tag), "rb"))
    M = pd.read_pickle(os.path.join(WORK, "month%s.pkl" % tag))
    X = pickle.load(open(os.path.join(WORK, "x3m%s.pkl" % tag), "rb"))
    res = P["res"]
    os.makedirs(OUT, exist_ok=True)
    S = {"讀法寫死": READ_TS, "資料": A2.data_commit(), "檔數_有OHLC": P["n_tick"], "檔數_可用": len(res)}
    BLK20 = (w1 - w0 + 1) // 20; BLK60 = (w1 - w0 + 1) // 60; NMON = 129
    S["區段上限"] = {"月": NMON, "20日": BLK20, "60日": BLK60}
    yrs = {"合併": sum(r["expo"]["合併"] for r in res) / 252.0, "只400": sum(r["expo"]["只400"] for r in res) / 252.0,
           "只500": sum(r["expo"]["只500"] for r in res) / 252.0}
    S["股票年"] = {k: round(v, 1) for k, v in yrs.items()}
    neff = lambda v, which: min(v[0], popcnt(v[which]))

    def agg_packs(getter):
        acc = {}
        for r in res:
            p = getter(r)
            if p is not None:
                add_pack(acc, p)
        return acc

    def accsum(getter):
        c = Counter()
        for r in res:
            x = getter(r)
            if x:
                c.update(x)
        return dict(c)
    EV = []       # 事件數表
    DEG = []      # 退化格表

    # A3-1 H1
    for g in ("站回", "未站回"):
        p = agg_packs(lambda r: r["H1"][g])
        for col in COLS:
            v = p.get(col, [0] * 6)
            EV.append({"件": "A3-1", "格": "H1 " + g + "組", "欄": col, "事件": v[0], "探索": v[1], "確認": v[2], "n_eff上限(20日區段)": neff(v, 4)})
    S["A3-1_acc"] = accsum(lambda r: r["H1"]["acc"])
    # A3-2 H2
    p = agg_packs(lambda r: r["H2"]["p"])
    for col in COLS:
        v = p.get(col, [0] * 6)
        EV.append({"件": "A3-2", "格": "H2 主格", "欄": col, "事件": v[0], "探索": v[1], "確認": v[2], "n_eff上限(20日區段)": neff(v, 4)})
    S["A3-2_acc"] = accsum(lambda r: r["H2"]["acc"])
    # A3-4
    p = agg_packs(lambda r: r["UT"]["p"])
    for col in COLS:
        v = p.get(col, [0] * 6)
        EV.append({"件": "A3-4", "格": "上升趨勢線跌破 主格", "欄": col, "事件": v[0], "探索": v[1], "確認": v[2], "n_eff上限(月)": neff(v, 3)})
    S["A3-4_acc"] = accsum(lambda r: r["UT"]["acc"])
    # A3-5 型態全量
    pat_rows = []
    vids = list(res[0]["PAT"].keys())
    for vid in vids:
        for Hh in (20, 60):
            p = agg_packs(lambda r: r["PAT"][vid][Hh]["p"])
            vc = p.get("合併", [0] * 6); v4 = p.get("只400", [0] * 6)
            which = 3 if Hh == 20 else 5
            ne, ne4 = neff(vc, which), neff(v4, which)
            pat_rows.append({"變體": vid, "名": PA.VMAP[vid]["name"] if "name" in PA.VMAP[vid] else vid, "H": Hh, "合併事件": vc[0], "合併n_eff": ne,
                             "只400事件": v4[0], "只400n_eff": ne4, "可判定(合併≥30)": ne >= 30, "只400≥30": ne4 >= 30})
    PT = pd.DataFrame(pat_rows)
    PT.to_csv(os.path.join(OUT, "A3-5_型態全量_頻率表.csv"), index=False, encoding="utf-8-sig")
    S["A3-5"] = {"判定格上限": int(len(PT)), "可判定(合併n_eff≥30)": int(PT["可判定(合併≥30)"].sum()),
                 "其中只400n_eff<30": int((PT["可判定(合併≥30)"] & ~PT["只400≥30"]).sum()),
                 "H20可判定": int(PT[PT.H == 20]["可判定(合併≥30)"].sum()), "H60可判定": int(PT[PT.H == 60]["可判定(合併≥30)"].sum())}
    for r_ in pat_rows:
        if not r_["可判定(合併≥30)"]:
            DEG.append({"件": "A3-5", "格": "%s %s H%d" % (r_["變體"], r_["名"], r_["H"]), "類型": "事件數不足（依構造不可判定）",
                        "理由": "合併 n_eff＝%d ＜ 30（事件 %d）" % (r_["合併n_eff"], r_["合併事件"])})
    # A3-8 週線
    wk_rows = []
    for s_ in RW.SIGS:
        for k in (4, 8, 12, 26):
            p = agg_packs(lambda r: r["WK"].get((s_, k)))
            vc = p.get("合併", [0] * 6); v4 = p.get("只400", [0] * 6)
            wk_rows.append({"訊號": s_, "k週": k, "合併事件": vc[0], "合併n_eff(月)": neff(vc, 3), "只400事件": v4[0], "只400n_eff(月)": neff(v4, 3),
                            "探索": vc[1], "確認": vc[2]})
            EV.append({"件": "A3-8", "格": "%s k%d" % (s_, k), "欄": "合併", "事件": vc[0], "探索": vc[1], "確認": vc[2], "n_eff上限(月)": neff(vc, 3)})
            if neff(vc, 3) < 30:
                DEG.append({"件": "A3-8", "格": "%s k%d" % (s_, k), "類型": "事件數不足", "理由": "合併 n_eff（月）＝%d ＜ 30" % neff(vc, 3)})
    pd.DataFrame(wk_rows).to_csv(os.path.join(OUT, "A3-8_週線_頻率表.csv"), index=False, encoding="utf-8-sig")
    # A3-13 突破過濾
    bf_rows = []
    for kind in ("w", "hs", "box"):
        st = accsum(lambda r: r["BF"][kind]["st"])
        p = agg_packs(lambda r: r["BF"][kind]["p"])
        vc = p.get("合併", [0] * 6); v4 = p.get("只400", [0] * 6)
        nev = st.get("事件", 0)
        for flt in ("B", "C", "D", "E", "F"):
            if kind == "box" and flt == "C":
                continue
            bought = st.get(flt + "_買到", 0); same = st.get(flt + "_同A日", 0)
            ne = neff(vc, 5); ne4 = neff(v4, 5)
            row = {"型": {"w": "W 底", "hs": "頭肩底", "box": "箱型"}[kind], "買法": flt, "事件": nev, "買到比例%": round(pct(bought, nev), 1),
                   "與A同日比例%": round(pct(same, nev), 1), "60日區段(合併)": popcnt(vc[5]), "n_eff(合併)": ne, "n_eff(只400)": ne4}
            bf_rows.append(row)
            if ne < 30:
                DEG.append({"件": "A3-13", "格": row["型"] + "×" + flt, "類型": "依構造不可判定", "理由": "合併 n_eff（60 日區段）＝%d ＜ 30" % ne})
            elif nev and same / nev >= 0.95:
                DEG.append({"件": "A3-13", "格": row["型"] + "×" + flt, "類型": "依構造退化（≥95% 與 A 同日）", "理由": "與 A 同日 %.1f%%" % pct(same, nev)})
        S["A3-13_" + kind + "_acc"] = accsum(lambda r: r["BF"][kind]["acc"])
    pd.DataFrame(bf_rows).to_csv(os.path.join(OUT, "A3-13_突破過濾_開跑前算術.csv"), index=False, encoding="utf-8-sig")
    # A3-16 洗盤
    W = defaultdict(lambda: [0, 0, 0])
    for r in res:
        for k, v in r["WASH"].items():
            w_ = W[k]; w_[0] += v[0]; w_[1] += v[1]; w_[2] += v[2]
    wash_rows = []
    for Uu in RWD.US:
        for Dd in RWD.DS:
            for Pthr in RWD.PS:
                for sup in RWD.SUPS:
                    for Hh in (5, 20, 60):
                        row = {"U": Uu, "D": Dd, "P": Pthr, "支撐": sup, "H": Hh}
                        for g in ("洗盤", "出貨", "混合"):
                            for seg, sn in ((0, "探索"), (1, "確認")):
                                v = W[(Uu, Dd, Pthr, sup, Hh, g, seg)]
                                row["%s_%s_合併" % (g, sn)] = v[0]; row["%s_%s_只400" % (g, sn)] = v[1]
                        wash_rows.append(row)
    WT = pd.DataFrame(wash_rows); WT.to_csv(os.path.join(OUT, "A3-16_洗盤_事件數.csv"), index=False, encoding="utf-8-sig")
    for r_ in WT[WT.H == 20].itertuples(index=False):
        lows = [k for k in ("洗盤_探索_合併", "洗盤_確認_合併", "出貨_探索_合併", "出貨_確認_合併", "洗盤_探索_只400", "洗盤_確認_只400")
                if getattr(r_, k) < 30]
        if lows:
            DEG.append({"件": "A3-16", "格": "U%.0f%% D%.0f%% P%.0f%% %s（H20；H5／H60 同形）" % (r_.U * 100, r_.D * 100, r_.P * 100, r_.支撐),
                        "類型": "樣本少（某組 ＜30：照報、⛔ 不併格；過半以足夠樣本格為分母）",
                        "理由": "；".join("%s＝%d" % (k, getattr(r_, k)) for k in lows)})
    S["A3-16"] = {}
    for Hh in (5, 20, 60):
        sub = WT[WT.H == Hh]
        for g in ("洗盤", "出貨"):
            for sn in ("探索", "確認"):
                for col in ("合併", "只400"):
                    S["A3-16"]["H%d_%s_%s_%s_≥30格數" % (Hh, g, sn, col)] = int((sub["%s_%s_%s" % (g, sn, col)] >= 30).sum())
    # A3-3 N字底／N型
    NPs = {k: sum(r["NP"][k] for r in res) for k in res[0]["NP"]}
    np_rows = []
    for kind in ("1", "2"):
        Sm = NPs["N%sS" % kind]; Mm = NPs["N%sM" % kind]
        for seg in (0, 1):
            for cI, col in enumerate(COLS[:2]):
                s_cells = Sm[seg, cI].reshape(-1); m_cells = Mm[seg, cI].reshape(-1)
                np_rows.append({"型": "N字底 甲%s" % kind, "段": ("探索", "確認")[seg], "欄": col, "S格數": len(s_cells), "S≥30格": int((s_cells >= 30).sum()),
                                "S事件中位": float(np.median(s_cells)), "M格數": len(m_cells), "M≥30格": int((m_cells >= 30).sum()), "M事件中位": float(np.median(m_cells))})
    for seg in (0, 1):
        for cI, col in enumerate(COLS[:2]):
            s_cells = NPs["TS"][seg, cI].reshape(-1); m_cells = NPs["TM"][seg, cI].reshape(-1)
            np_rows.append({"型": "N型走法", "段": ("探索", "確認")[seg], "欄": col, "S格數": len(s_cells), "S≥30格": int((s_cells >= 30).sum()),
                            "S事件中位": float(np.median(s_cells)), "M格數": len(m_cells), "M≥30格": int((m_cells >= 30).sum()), "M事件中位": float(np.median(m_cells))})
    pd.DataFrame(np_rows).to_csv(os.path.join(OUT, "A3-3_N字底N型_格事件數.csv"), index=False, encoding="utf-8-sig")
    # 雙段都 ≥30 的格數（M 與 S 配對：兩臂都 ≥30）
    S["A3-3"] = {}
    for kind in ("1", "2"):
        Mm = NPs["N%sM" % kind]; Sm = NPs["N%sS" % kind]
        for cI, col in enumerate(COLS[:2]):
            both = (Mm[0, cI] >= 30) & (Mm[1, cI] >= 30)
            pair = both & (Sm[0, cI][..., None] >= 30) & (Sm[1, cI][..., None] >= 30)
            S["A3-3"]["甲%s_%s_M兩段都≥30格" % (kind, col)] = "%d／%d" % (int(both.sum()), both.size)
            S["A3-3"]["甲%s_%s_M−S兩臂兩段都≥30格" % (kind, col)] = "%d／%d" % (int(pair.sum()), pair.size)
    for cI, col in enumerate(COLS[:2]):
        both = (NPs["TM"][0, cI] >= 30) & (NPs["TM"][1, cI] >= 30)
        S["A3-3"]["N型_%s_M兩段都≥30格" % col] = "%d／%d" % (int(both.sum()), both.size)
    # A3-6 訊號系統、A3-7 均線出場
    sig_rows = []
    for k in sorted(res[0]["SIG"].keys()):
        p = agg_packs(lambda r: r["SIG"][k]); vc = p.get("合併", [0] * 6)
        sig_rows.append({"訊號": k, "名": RS.NAME.get(k.split(":")[1], k), "窗內在母體事件": vc[0], "每股票年": round(vc[0] / yrs["合併"], 3),
                         "只400": p.get("只400", [0])[0]})
    pd.DataFrame(sig_rows).to_csv(os.path.join(OUT, "A3-6_訊號頻率.csv"), index=False, encoding="utf-8-sig")
    SYS = defaultdict(lambda: [0, 0, 0])
    for r in res:
        for k, v in r["SYS"].items():
            a_ = SYS[k]; a_[0] += v[0]; a_[1] += v[1]; a_[2] += v[2]
    sys_rows = []
    for (fam, segn, xo), v in sorted(SYS.items()):
        sys_rows.append({"族": fam, "段": segn, "出場": xo, "進場訊號": v[0], "出場觸發": v[1], "段尾未出場": v[2], "段尾未出場%": round(pct(v[2], v[0]), 1)})
    SY = pd.DataFrame(sys_rows); SY.to_csv(os.path.join(OUT, "A3-6_A3-7_條件出場_開跑前.csv"), index=False, encoding="utf-8-sig")
    madn = Counter()
    for r in res:
        madn.update(r["MADN"])
    S["A3-7_均線穿越每股票年"] = {"MA%d" % k: round(v / yrs["合併"], 2) for k, v in madn.items()}
    for fam in ("E1", "E2"):
        for k in (10, 20, 60):
            row = SY[(SY["族"] == fam) & (SY["段"] == "探索") & (SY["出場"] == "MA%d" % k)].iloc[0]
            if row["段尾未出場%"] > 50 or madn[k] / yrs["合併"] < 1:
                DEG.append({"件": "A3-7", "格": "%s × MA%d" % (fam, k), "類型": "退化格（seq246）", "理由": "探索段段尾未出場 %.1f%%" % row["段尾未出場%"]})
        for xo in ["ANY"] + list(RS.XS):
            row = SY[(SY["族"] == fam) & (SY["段"] == "探索") & (SY["出場"] == "X:" + xo)].iloc[0]
            if row["段尾未出場%"] > 50:
                DEG.append({"件": "A3-6", "格": "%s × %s" % (fam, xo), "類型": "退化（描述；登錄未設排除規則）", "理由": "探索段段尾未出場 %.1f%%" % row["段尾未出場%"]})
    spy = P["spy"]
    S["A3-6_SPY層"] = {k: {"探索": int(sum(1 for x in v if w0 <= x <= sp)), "確認": int(sum(1 for x in v if sp < x <= w1))} for k, v in spy.items()}
    # A3-10
    VB = defaultdict(lambda: [0, 0, 0.0, 0])
    for r in res:
        for k, v in r["VB"].items():
            a_ = VB[k]; a_[0] += v[0]; a_[1] += v[1]; a_[2] += v[2]; a_[3] += v[3]
    vb_rows = []
    for (Bb, kk, L, segn), v in sorted(VB.items(), key=lambda x: (x[0][0], -1 if x[0][1] is None else x[0][1], x[0][2], x[0][3])):
        vb_rows.append({"B": Bb, "k": "S臂（不看量）" if kk is None else kk, "L": L, "段": segn, "交易筆數": v[0], "段尾未出場": v[1],
                        "平均持有根數": round(v[2] / v[3], 2) if v[3] else np.nan})
    VBT = pd.DataFrame(vb_rows); VBT.to_csv(os.path.join(OUT, "A3-10_爆量突破_開跑前.csv"), index=False, encoding="utf-8-sig")
    sub = VBT[(VBT["段"] == "探索") & (VBT["k"] != "S臂（不看量）")]
    S["A3-10"] = {"M格": int(len(sub)), "平均持有<2根格數(探索)": int((sub["平均持有根數"] < 2).sum()),
                  "交易筆數<30格數(探索)": int((sub["交易筆數"] < 30).sum())}
    for r_ in sub.itertuples():
        if r_.平均持有根數 < 2:
            DEG.append({"件": "A3-10", "格": "B%d k%s L%d" % (r_.B, r_.k, r_.L), "類型": "退化標記（只標、仍計分母）", "理由": "平均持有 %.2f 根 ＜ 2" % r_.平均持有根數})
    # A3-11 D、I
    dar = [x for r in res for x in r["DARVAS"]]
    wk = d["wk"]; wk0, wkE, wks1 = int(wk[w0]), int(wk[sp]), int(wk[w1])
    conc = np.zeros(wks1 + 2, int)
    for bw, sw, _, _ in dar:
        e_ = sw if sw >= 0 else wks1
        conc[bw + 1:min(e_, wks1) + 1] += 1
    S["A3-11_D"] = {"週線買訊(窗內在母體)": len(dar), "每年": round(len(dar) / 10.75, 1),
                    "探索段平均同時持有": round(float(conc[wk0:wkE + 1].mean()), 1), "確認段平均同時持有": round(float(conc[wkE + 1:wks1 + 1].mean()), 1)}
    # 件 T：樣板（①～⑦）＋ RS 前 30%
    M["in"] = M["m5"] | M["m4"]
    tT = []
    for mi, g in M.groupby("mi"):
        rsq = g["rs"].rank(pct=True)
        tm = (g["tmpl17"] == True) & (rsq >= 0.70)
        tT.append({"mi": mi, "可算": int(g["tmpl17"].notna().sum()), "股數": len(g), "甲樣板": int(tm.sum()),
                   "乙樣板∩8季新高": int((tm & (g["rev_hi8"] == True)).sum())})
    TT = pd.DataFrame(tT)
    S["A3-11_T"] = {"樣板可算比例(全期股-月)": round(pct(TT["可算"].sum(), TT["股數"].sum()), 1),
                    "甲每月檔數中位": float(TT["甲樣板"].median()), "甲 <10 檔月數": int((TT["甲樣板"] < 10).sum()), "甲 <20 檔月數": int((TT["甲樣板"] < 20).sum()),
                    "乙每月檔數中位": float(TT["乙樣板∩8季新高"].median()), "乙 <10 檔月數": int((TT["乙樣板∩8季新高"] < 10).sum()),
                    "乙 <20 檔月數": int((TT["乙樣板∩8季新高"] < 20).sum()), "月數": int(len(TT))}
    # 件 I：甲 ＝ S&P 500 市值前 50（月）
    top50 = set()
    for mi, g in M[M["m5"]].groupby("mi"):
        top50 |= {(mi, t) for t in g.nlargest(50, "mcap")["t"]}
    MON = d["MON"]
    ichi_all = [(r["t"], x) for r in res for x in r["ICHI"]]
    ichi_a = [x for x in ichi_all if (int(MON[x[1]]), x[0]) in top50]
    S["A3-11_I"] = {"乙 全母體進場訊號": len(ichi_all), "乙每年": round(len(ichi_all) / 10.75, 1), "甲 S&P500 市值前50 進場訊號": len(ichi_a),
                    "甲每年": round(len(ichi_a) / 10.75, 1), "市值可算比例(S&P500 股-月)": round(pct(M[M["m5"]]["mcap"].notna().sum(), int(M["m5"].sum())), 1)}
    # A3-12 動能
    S["A3-12"] = {}
    for F_, col in ((3, "r63"), (6, "r126"), (12, "r252")):
        S["A3-12"]["R(%d) 可算比例" % F_] = round(pct(M[col].notna().sum(), len(M)), 1)
    S["A3-12"]["M3 殘差（≥24 個月月報酬）可算比例"] = round(pct((M["nbar"] >= 24 * 21 + 21).sum(), len(M)), 1)
    S["A3-12"]["M3 最早可算月"] = str(cal[int(M[M["nbar"] >= 24 * 21 + 21]["e"].min())].date()) if (M["nbar"] >= 525).any() else "無"
    # A3-14／A3-15 外部作者
    ext_rows = []
    years_main = (w1 - w0 + 1) / 252.0
    for code in ("W1", "Y1", "Y2in", "Y3", "Y2out", "Y5", "S1", "F1", "F1c", "O1"):
        p = agg_packs(lambda r: r["EXT"][code]); vc = p.get("合併", [0] * 6); v4 = p.get("只400", [0] * 6)
        row = {"顆": code, "名": {**EA.NAME, **EA2.NAME}.get(code, code), "主窗事件(合併)": vc[0], "年均(合併)": round(vc[0] / years_main, 1),
               "主窗事件(只400)": v4[0], "年均(只400)": round(v4[0] / years_main, 1)}
        ext_rows.append(row)
        if code in ("W1", "Y1", "Y2in", "Y3", "F1", "F1c", "O1"):
            for col, v_ in (("合併", vc), ("只400", v4)):
                if v_[0] < 200 or v_[0] / years_main < 10:
                    DEG.append({"件": "A3-14" if code in ("W1", "Y1", "Y2in", "Y3") else "A3-15", "格": "%s（%s）全部出場格" % (code, col),
                                "類型": "退化格（seq248 ④：主窗事件 ＜200 或年均 ＜10）", "理由": "事件 %d、年均 %.1f" % (v_[0], v_[0] / years_main)})
    pd.DataFrame(ext_rows).to_csv(os.path.join(OUT, "A3-14_A3-15_外部作者_事件數.csv"), index=False, encoding="utf-8-sig")
    EXX = defaultdict(lambda: [0, 0, 0])
    for r in res:
        for k, v in r["EXT"].items():
            if isinstance(k, tuple):
                a_ = EXX[k]; a_[0] += v[0]; a_[1] += v[1]; a_[2] += v[2]
    ex_rows = [{"顆": k[0], "段": k[1], "出場": k[2], "進場": v[0], "出場觸發": v[1], "段尾未出場%": round(pct(v[2], v[0]), 1)} for k, v in sorted(EXX.items())]
    EXT = pd.DataFrame(ex_rows); EXT.to_csv(os.path.join(OUT, "A3-14_A3-15_出場段尾.csv"), index=False, encoding="utf-8-sig")
    for r_ in EXT[EXT["段"] == "探索"].itertuples():
        if r_._6 > 50:
            DEG.append({"件": "A3-14" if r_.顆 in ("W1", "Y1", "Y2in", "Y3") else "A3-15", "格": "%s × %s" % (r_.顆, r_.出場), "類型": "退化格（段尾未出場 ＞50%）",
                        "理由": "探索段 %.1f%%" % r_._6})
    # A4-9 W2
    w2d = X.get("W2_days", [])
    MONd = d["MON"]
    S["A4-9_W2"] = dict(X.get("W2", {}))
    S["A4-9_W2"]["年均"] = round(len(w2d) / years_main, 1)
    m4of = {}
    for r in res:
        m4of[r["t"]] = r
    S["A4-9_W2"]["事件有月數"] = len({int(MONd[j]) for _, j in w2d})
    # A4-3 X3
    x3 = X["X3"]
    memb = {r["t"]: r for r in res}
    S["A4-3_X3_原始(全期)"] = len(x3)
    S["A4-3_X3_窗內(≤窗尾−21)"] = int(sum(1 for t, T in x3 if w0 <= T <= w1 - 21))
    # 月份與母體：用月快照的在指數旗標（量測月）近似 ⇒ 精確母體在本體算
    inM = set(zip(M["t"], M["mi"]))
    x3_in = [(t, T) for t, T in x3 if w0 <= T <= w1 - 21 and (t, int(MONd[T])) in inM]
    S["A4-3_X3_窗內且當月在指數"] = len(x3_in)
    S["A4-3_X3_有事件的月數"] = len({int(MONd[T]) for _, T in x3_in})
    # ── A4：覆蓋率表 ──
    cov_rows = []

    def cov(name, ser, item, src, note=""):
        for col, msk in (("S&P 500", M["m5"]), ("S&P 400", M["m4"])):
            s_ = ser[msk]
            cov_rows.append({"件": item, "量": name, "母體": col, "可算股-月": int(s_.notna().sum()), "在指數股-月": int(msk.sum()),
                             "覆蓋率%": round(pct(int(s_.notna().sum()), int(msk.sum())), 1), "資料來源": src, "註": note})
    B1 = "B1 SEC companyfacts（first_filed、value 第一次公布）"
    cov("季營收年增率（月營收年增率的同義版）", M["rev_yoy"], "A4-3／A4-8／A4-12／A4-13／A4-9", B1 + " quarterly_revenue(+_sp400)")
    cov("創 8 季新高（創 24 月新高的同義版）", M["rev_hi8"], "A3-11／A4-1／A4-4／A4-5／A4-6／A4-12／A3-17", B1 + " quarterly_revenue")
    cov("季營收季增率（月增率的同義版）", M["rev_qoq"], "A4-13 F03", B1)
    cov("TTM 淨利", M["ttm_net_income"], "A4-1／A4-2／A4-8", B1 + " quarterly_net_income")
    cov("ROE（TTM 淨利÷兩期權益平均）", M["roe"], "A4-1 Q1／A4-3 X1／A4-11", B1 + " net_income＋equity")
    cov("營業利益÷資產", M["oia"], "A4-1 Q2／A4-11", B1 + " operating_income＋assets")
    cov("ROA", M["roa"], "A4-1 Q3／A4-11", B1 + " net_income＋assets")
    cov("研發強度（TTM 研發÷TTM 營收）", M["rnd_int"], "A4-1 Q4／A4-2 M4／A4-11", B1 + " quarterly_rnd", "研發不是每家都申報")
    cov("市值（封面股數×前一日原始收盤）", M["mcap"], "A4-2／A4-8／A4-13／A3-11 I", "B2 shares_outstanding＋Yahoo 拆股＋原始收盤")
    cov("本益比（市值÷TTM 淨利；淨利≤0 ⇒ 不符）", M["pe"].where(M["pe_computable"], np.nan).where(~M["pe_computable"] | True), "A4-2 X3/O4／A4-8 N5／A4-13 F16", "B1＋B2",
        "可算＝市值與 TTM 淨利都有")
    cov("淨值股價比", M["bp"], "A4-8 N5／A4-13 F18", "B1 equity＋B2")
    cov("季買回÷市值（庫藏股代理）", M["bb_mcap"], "A4-7", B1 + " quarterly_buyback＋B2", "買回欄不是每家都有")
    for L in (20, 60, 120):
        cov("周轉率 TO(%d)" % L, M["to%d" % L], "A4-4／A4-3 X2(CGO 的 V)／A3-17 K5／A4-11", "Yahoo 量＋B2 股數")
    cov("墨菲 M1（12 季營益率平均）", M["M1"], "A4-2", B1 + " operating_income＋revenue")
    cov("M2／X1／O2（5 年 ROE 平均）", M["M2"], "A4-2", B1 + " net_income＋equity（年末）")
    cov("M3／X4（3 年營收成長平均）", M["M3"], "A4-2", B1 + " revenue（年）")
    cov("X2（5 年負債比平均；負債＝資產−權益）", M["X2"], "A4-2", B1 + " assets＋equity(_incl_nci)", "美股 B1 沒有負債欄 ⇒ 代理")
    cov("O1（5 年 ROA 平均）", M["O1"], "A4-2", B1 + " net_income＋assets")
    cov("O3（3 年 EPS 增率平均；EPS＝年淨利÷封面股數）", M["O3"].where(M["O3_computable"] == True, np.nan), "A4-2", B1 + "＋B2", "B1 沒有 EPS ⇒ 代理")
    cov("營益率比去年同季升（飆股財報特徵）", M["opm_up_yoy"], "A4-10", B1)
    cov("季淨利由負轉正（EPS 轉正的代理）", M["ni_turn"], "A4-10／A4-9", B1 + " quarterly_net_income")
    cov("GICS sector", M["sector"].where(M["sector"].notna(), np.nan), "A4-5／A4-6／A4-1(剔金融)", "B3 sector_pit（Wikipedia 歷史版，非官方）")
    cov("RS（IBD 式 2r63＋r126＋r189＋r252）", M["rs"], "A3-11 T／D", "價格面板")
    cov("趨勢樣板 ①～⑦", M["tmpl17"], "A3-11 T", "價格面板（需 250＋21 根）")
    cov("12−1 動能", M["r12_1"], "A3-12／A4-8 N4／A4-13 F08／A4-11", "價格面板")
    cov("60 日波動", M["vol60"], "A4-3 X1／A4-13 F11／A4-11", "價格面板")
    CV = pd.DataFrame(cov_rows); CV.to_csv(os.path.join(OUT, "覆蓋率_換掉與新算的量.csv"), index=False, encoding="utf-8-sig")
    # 觸發率（二元條件；在可算者中）
    trg_rows = []

    def trig(name, ser, item):
        for col, msk in (("合併", M["m5"] | M["m4"]), ("S&P 400", M["m4"])):
            s_ = ser[msk].dropna().astype(bool)
            r_ = pct(int(s_.sum()), len(s_))
            flag = "＜1%" if r_ < 1 else ("＞99%" if r_ > 99 else "")
            trg_rows.append({"件": item, "條件": name, "母體": col, "可算股-月": len(s_), "觸發%": round(r_, 2), "退化旗標": flag})
            if flag and col == "合併":
                typ = ("票的觸發率 %s（只標；十一票是加總分數 ⇒ 不刪格、不改 N）" % flag) if item.startswith("A4-12") else ("觸發率退化（%s）" % flag)
                DEG.append({"件": "A4-12" if item.startswith("A4-12") else item, "格": name, "類型": typ, "理由": "合併股-月觸發 %.2f%%" % r_})
    trig("創 8 季新高", M["rev_hi8"], "A4-1乙／A4-4乙／A4-5(b)／A4-12①／A3-11乙")
    trig("季營收年增率 ≥15%", (M["rev_yoy"] >= 0.15).where(M["rev_yoy"].notna()), "A4-12②")
    trig("X1 池：季年增 10%～150%（連 1 季年增＞0 被它包含）", ((M["rev_yoy"] > 0.10) & (M["rev_yoy"] < 1.50)).where(M["rev_yoy"].notna()), "A4-3 X1")
    trig("M1 營益率>10%", M["M1"], "A4-2 墨菲"); trig("M2 ROE5>8%", M["M2"], "A4-2"); trig("M3 營收成長3年>10%", M["M3"], "A4-2")
    trig("M4 研發>5%（無研發＝不符）", M["M4"], "A4-2"); trig("X2 負債比<30%", M["X2"], "A4-2 喜偉"); trig("本益比<15", M["PE15"], "A4-2 喜偉/歐沙那希")
    trig("O1 ROA5>8%", M["O1"], "A4-2 歐沙那希"); trig("O3 EPS 增率>30%", M["O3"].where(M["O3_computable"] == True), "A4-2 歐沙那希")
    trig("多頭排列 5>10>20>60", M["stack"], "A4-12④")
    trig("強勢股 4 取 3（漲停條拿掉）", M["strong"], "A4-12⑤")
    for L in (5, 20, 60):
        trig("250 日新高（近 %d 日）" % L, M["hi250_L%d" % L], "A4-12③")
        trig("TD9 買（近 %d 日）" % L, M["td9_L%d" % L], "A4-12⑥")
        trig("RSI30 站回（近 %d 日）" % L, M["rsi_L%d" % L], "A4-12⑦")
        trig("上升三角往上突破 S06（近 %d 日）" % L, M["s06_L%d" % L], "A4-12⑧")
        trig("上升趨勢線跌破（近 %d 日）" % L, M["utb_L%d" % L], "A4-12⑩")
        trig("高檔爆量長上影確認（近 %d 日）" % L, M["vsc_L%d" % L], "A4-12⑪")
    trig("季淨利由負轉正", M["ni_turn"], "A4-10")
    trig("營益率比去年同季升", M["opm_up_yoy"], "A4-10")
    trig("R1 季營收轉折（最新季年增>0、前一季≤0）", ((M["rev_yoy"] > 0) & (M["rev_yoy_prev"] <= 0)).where(M["rev_yoy"].notna() & M["rev_yoy_prev"].notna()), "A3-17/A4-10 R1")
    trig("R2 季營收年增 ≥50%", (M["rev_yoy"] >= 0.5).where(M["rev_yoy"].notna()), "A3-17/A4-10 R2")
    trig("R2 季營收年增 ≥100%", (M["rev_yoy"] >= 1.0).where(M["rev_yoy"].notna()), "A3-17/A4-10 R2")
    TR_ = pd.DataFrame(trg_rows); TR_.to_csv(os.path.join(OUT, "觸發率_二元條件.csv"), index=False, encoding="utf-8-sig")
    # 飆股價量二元特徵（逐股日）
    SUa = defaultdict(lambda: [0, 0, 0, 0])
    for r in res:
        for k, v in r["SURGE"].items():
            a_ = SUa[k]
            for i in range(4):
                a_[i] += v[i]
    su_rows = []
    for k, v in SUa.items():
        r_ = pct(v[0], v[1]); r4 = pct(v[2], v[3])
        flag = "＜1%" if r_ < 1 else ("＞99%" if r_ > 99 else "")
        su_rows.append({"特徵": k, "合併股-日": v[1], "合併觸發%": round(r_, 3), "只400觸發%": round(r4, 3), "退化旗標": flag})
        if flag:
            DEG.append({"件": "A3-17", "格": k, "類型": "觸發率 %s（K7：照報、標樣本少）" % flag, "理由": "2021-01～窗尾 合併股-日 %.3f%%" % r_})
    pd.DataFrame(su_rows).to_csv(os.path.join(OUT, "A3-17_飆股價量二元特徵_觸發率.csv"), index=False, encoding="utf-8-sig")
    # 候選池大小（每月）
    pool_rows = []
    nonfin = M["sector"] != "Financials"
    insel = M["m5"] | M["m4"]
    for name, msk in (("A4-1 乙 池＝8季新高（非金融）", (M["rev_hi8"] == True) & nonfin),
                      ("A4-1 乙 Q1 ROE 可排名", (M["rev_hi8"] == True) & nonfin & M["roe"].notna()),
                      ("A4-1 乙 Q4 研發可排名", (M["rev_hi8"] == True) & nonfin & M["rnd_int"].notna()),
                      ("A4-1 甲 Q4 研發可排名（非金融）", nonfin & M["rnd_int"].notna()),
                      ("A4-2 墨菲 4 條全成立", (M["M1"] == True) & (M["M2"] == True) & (M["M3"] == True) & (M["M4"] == True)),
                      ("A4-2 喜偉 4 條全成立", (M["M2"] == True) & (M["X2"] == True) & (M["PE15"] == True) & (M["M3"] == True)),
                      ("A4-2 歐沙那希 4 條全成立", (M["O1"] == True) & (M["M2"] == True) & (M["O3"] == True) & (M["PE15"] == True)),
                      ("A4-3 X1 池（季年增 10%～150%）", (M["rev_yoy"] > 0.10) & (M["rev_yoy"] < 1.50)),
                      ("A4-4 乙 池＝8季新高 ∩ TO(20) 可算", (M["rev_hi8"] == True) & M["to20"].notna()),
                      ("A4-5 (b) 8季新高（全母體；類股內另切）", (M["rev_hi8"] == True))):
        cnt = M[insel & msk].groupby("mi").size().reindex(range(int(M["mi"].max()) + 1), fill_value=0)
        pool_rows.append({"池": name, "每月中位": float(cnt.median()), "p10": float(cnt.quantile(0.1)), "p90": float(cnt.quantile(0.9)),
                          "＜10 檔月數": int((cnt < 10).sum()), "＜20 檔月數": int((cnt < 20).sum()), "月數": int(len(cnt)),
                          "第一個≥10檔的月": str(cal[int(d["MSTART"][int(cnt[cnt >= 10].index.min())])].date()) if (cnt >= 10).any() else "無"})
    PO = pd.DataFrame(pool_rows); PO.to_csv(os.path.join(OUT, "候選池大小_每月.csv"), index=False, encoding="utf-8-sig")
    # A4-2 起點規則（三套可算比例都首次 ≥90%）
    st_rows = []
    for mi, g in M[insel].groupby("mi"):
        a_ = g[["M1", "M2", "M3"]].notna().all(axis=1).mean()   # M4 研發缺 ⇒ 不符（可算）
        b_ = g[["M2", "X2", "M3"]].notna().all(axis=1).mean() * g["PE15"].notna().mean()
        c_ = (g[["O1", "M2"]].notna().all(axis=1) & (g["O3_computable"] == True)).mean() * g["PE15"].notna().mean()
        st_rows.append({"mi": mi, "墨菲可算": a_, "喜偉可算": b_, "歐沙那希可算": c_})
    ST = pd.DataFrame(st_rows)
    ok90 = ST[(ST["墨菲可算"] >= 0.9) & (ST["喜偉可算"] >= 0.9) & (ST["歐沙那希可算"] >= 0.9)]
    S["A4-2_起點"] = {"三套可算比例都≥90%的第一個月": str(cal[int(d["MSTART"][int(ok90["mi"].min())])].date()) if len(ok90) else "從未達到",
                     "各套可算比例中位": {k: round(float(ST[k].median()) * 100, 1) for k in ("墨菲可算", "喜偉可算", "歐沙那希可算")},
                     "各套可算比例最高": {k: round(float(ST[k].max()) * 100, 1) for k in ("墨菲可算", "喜偉可算", "歐沙那希可算")}}
    # 描述：排除 GICS Financials（銀行保險沒有營業利益／營收欄）後
    st2 = []
    for mi, g in M[insel & nonfin & M["sector"].notna()].groupby("mi"):
        a_ = g[["M1", "M2", "M3"]].notna().all(axis=1).mean()
        b_ = g[["M2", "X2", "M3"]].notna().all(axis=1).mean() * g["PE15"].notna().mean()
        c_ = (g[["O1", "M2"]].notna().all(axis=1) & (g["O3_computable"] == True)).mean() * g["PE15"].notna().mean()
        st2.append({"mi": mi, "墨菲": a_, "喜偉": b_, "歐沙那希": c_})
    ST2 = pd.DataFrame(st2)
    ok2 = ST2[(ST2["墨菲"] >= 0.9) & (ST2["喜偉"] >= 0.9) & (ST2["歐沙那希"] >= 0.9)]
    S["A4-2_起點"]["描述_排除Financials_各套可算比例最高"] = {k: round(float(ST2[k].max()) * 100, 1) for k in ("墨菲", "喜偉", "歐沙那希")}
    S["A4-2_起點"]["描述_排除Financials_都≥90%第一個月"] = str(cal[int(d["MSTART"][int(ok2["mi"].min())])].date()) if len(ok2) else "從未達到"
    ok80 = ST2[(ST2["墨菲"] >= 0.8) & (ST2["喜偉"] >= 0.8) & (ST2["歐沙那希"] >= 0.8)]
    S["A4-2_起點"]["描述_排除Financials_都≥80%第一個月"] = str(cal[int(d["MSTART"][int(ok80["mi"].min())])].date()) if len(ok80) else "從未達到"
    for r_ in PO.itertuples(index=False):
        if r_.池.startswith("A4-2") and r_._4 > 0.3 * r_.月數:
            DEG.append({"件": "A4-2", "格": r_.池.replace(" 4 條全成立", ""), "類型": "常常湊不滿 10 檔（原文：句前加警語、照跑、⛔ 不放寬）",
                        "理由": "候選 ＜10 檔的月 %d／%d（每月中位 %.0f）" % (r_._4, r_.月數, r_.每月中位)})
    # A4-5／A4-6 類股層級
    lv = {}
    for lvl, col in (("sector", "sector"), ("sub-industry", "subind")):
        cnts = M[insel & M[col].notna()].groupby(["mi", col]).size()
        n5 = (cnts >= 5).groupby(level=0).sum()
        lv[lvl] = {"成分≥5類別數 月中位": float(n5.median()), "最少": int(n5.min()), "最多": int(n5.max())}
    S["A4-5_類股層級"] = lv
    # A4-7 剔除事件
    ev7 = []
    for idx, (pdir, mdir) in A2.DIRS.items():
        ch = pd.read_csv(A2._p(mdir, "changes.csv"), dtype=str, keep_default_na=False)
        ch = ch[(ch["removed_ticker"] != "") & (ch["date"] >= "2016-01-04") & (ch["date"] <= "2026-09-30")]
        for r_ in ch.itertuples(index=False):
            dd = pd.Timestamp(r_.date); pos = int(cal.searchsorted(dd))
            t = r_.removed_ticker
            has_px = False
            srcs = set()
            for ii in A2.IDX:
                sg = A2.segments_idx(ii)
                srcs |= set(sg.loc[(sg["ticker"] == t) & (sg["src"] != ""), "src"])
            for src in srcs:
                try:
                    s_ = _raw_close_src(src)
                except Exception:
                    continue
                if ((s_.index > dd) & (s_.index <= dd + pd.Timedelta(days=10))).any():
                    has_px = True; break
            ev7.append({"指數": idx, "日": r_.date, "年": r_.date[:4], "ticker": t, "原因類": r_.reason_cat, "生效後10天內有價": has_px})
    E7 = pd.DataFrame(ev7)
    yr = E7.groupby(["指數", "年"]).agg(剔除=("ticker", "size"), 有價=("生效後10天內有價", "sum")).reset_index()
    yr.to_csv(os.path.join(OUT, "A4-7_成分剔除_逐年.csv"), index=False, encoding="utf-8-sig")
    S["A4-7_剔除"] = {idx: {"窗內剔除": int((E7["指數"] == idx).sum()), "生效後有價": int(E7[(E7["指數"] == idx)]["生效後10天內有價"].sum()),
                          "年均有價": round(E7[(E7["指數"] == idx)]["生效後10天內有價"].sum() / 10.75, 1)} for idx in ("sp500", "sp400")}
    S["A4-7_剔除"]["合併 年均有價"] = round(E7["生效後10天內有價"].sum() / 10.75, 1)
    S["A4-7_原因類"] = E7.groupby(["指數", "原因類"]).size().to_dict()
    S["A4-7_原因類"] = {"%s|%s" % k: int(v) for k, v in S["A4-7_原因類"].items()}
    # A4-6 產業營收（換股月 1、4、7、10）
    F = load_fund(cal)
    sec = load_sectors()
    a46 = []
    cal_days = cal.values.astype("datetime64[D]").astype(np.int64)
    for mi, e in enumerate(d["MSTART"]):
        dt = cal[e]
        if dt.month not in (1, 4, 7, 10):
            continue
        ed = int(cal_days[e])
        qend = (dt - pd.Timedelta(days=90)).to_period("Q").start_time - pd.Timedelta(days=1)
        qd = int(np.datetime64(qend.date(), "D").astype(np.int64))
        g = M[(M["mi"] == mi) & insel]
        per = defaultdict(int); per_sub = defaultdict(int)
        for r_ in g.itertuples(index=False):
            x = F["revenue"].get(r_.t)
            if x is None:
                continue
            pe, v, av, fy = x
            j = np.flatnonzero((pe > qd - 92) & (pe <= qd) & (av <= e))
            k_ = np.flatnonzero((pe > qd - 92 - 365) & (pe <= qd - 365) & (av <= e))
            if len(j) and len(k_) and v[j[-1]] > 0 and v[k_[-1]] > 0:
                if r_.sector:
                    per[r_.sector] += 1
                if r_.subind:
                    per_sub[r_.subind] += 1
        a46.append({"換股日": str(dt.date()), "季": str(qend.date()), "sector≥5": sum(1 for v in per.values() if v >= 5),
                    "sub≥5": sum(1 for v in per_sub.values() if v >= 5), "在指數": len(g)})
    A46 = pd.DataFrame(a46); A46.to_csv(os.path.join(OUT, "A4-6_產業營收_可排名產業數.csv"), index=False, encoding="utf-8-sig")
    S["A4-6"] = {"換股日數": int(len(A46)), "sector 可排名(≥5)中位": float(A46["sector≥5"].median()), "sub-industry 可排名中位": float(A46["sub≥5"].median()),
                 "sub-industry 最少": int(A46["sub≥5"].min())}
    # 依構造（拿掉／換掉條件後相同）的退化格
    STATIC = [
        ("A3-3", "P 代理臂（M＋三大法人近 5 日買超）× H4", "拿掉後與另一格相同", "法人條件美股沒有 ⇒ P＝M；台股 N 28 中的 P 臂 4 格不計"),
        ("A4-7", "庫藏股 目的 1（轉讓員工）× 視窗 4", "拿掉後與另一格相同", "美股無逐筆庫藏股公告與目的 ⇒ 與「全部」相同"),
        ("A4-7", "庫藏股 目的 3（維護股東權益）× 視窗 4", "拿掉後與另一格相同", "同上"),
        ("A4-7", "庫藏股 組合層 目的 1、目的 3（各 H3）", "拿掉後與另一格相同", "同上；組合層只剩「全部」× H{20,60,120}"),
        ("A4-7", "成分剔除 公告日後進場 × 視窗 4", "條件拿掉（資料沒有公告日）", "membership changes 只有生效日"),
        ("A4-8", "N2 近三月營收累計年增率", "換掉後與另一格相同", "⌈3÷3⌉＝1 季 ⇒ ≡ N1 季營收年增率"),
        ("A4-8", "N6 外資買超強度", "條件拿掉 ⇒ 不成格", "法人美股沒有；該格只有這一條"),
        ("A4-13", "F02 單一格＋F02 與其他 13 條的兩兩格（F01×F02 ≡ F01 單一格）", "換掉後與另一格相同", "F02 ≡ F01 ⇒ 15 格退化"),
        ("A4-13", "F13 外資、F14 投信、F15 融資 的單一格與所有含它們的兩兩格", "條件拿掉 ⇒ 不成格", "3＋48＝51 格；171 → 120 → 扣 F02 15 格 → 105 格"),
        ("A4-3", "X1 池「連 3 個月年增＞0」子條件", "換掉後被另一條包含（不是格）", "⌈3÷3⌉＝1 季年增＞0，已被「季年增 10%～150%」包含"),
        ("A4-12", "⑤ 強勢股 的「20 日漲停 ≥3 次」那一條", "條件拿掉（票內，特徵不全）", "⑤ 改 4 條中 ≥3；不是格、不改 N"),
    ]
    for it_, cell_, typ_, why_ in STATIC:
        DEG.insert(0, {"件": it_, "格": cell_, "類型": "依構造退化：" + typ_, "理由": why_})
    # 表寫出
    pd.DataFrame(EV).to_csv(os.path.join(OUT, "事件數_單筆層.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DEG).to_csv(os.path.join(OUT, "退化格清單.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(OUT, "prep_summary.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o if not isinstance(o, (np.integer, np.floating)) else o.item())
    print(json.dumps(S, ensure_ascii=False, indent=1, default=str)[:20000])


# ═════════════ 29 件清單（靜態部分：登錄、出場型、換掉／拿掉的條件；N 計法）═════════════
F_ = lambda s: s  # 台股登錄檔名（信箱，⚠ 封存＝在 _封存-2026-10-04_台股策略線附件-已結案或逾七天/）
ITEMS = [
 ("A3-1", "月線 3 日站回（H1，分類器讀法）", "登錄全文-PREREGH1_月線3日站回_台股策略線_seq2_shaa2d23aa8f7dc400c-13738B-20260925-0121.md（封存）", "a2d23aa8f7dc400c",
  "③ 事件（判定 20 日＝原文 H20；60／120／240 描述）",
  "超額基準 gate3 母體等權 → 合併母體等權（同段）",
  "T+1 開盤漲停剔除（美股無漲跌停）；處置閘（原本就擋不到）", "否", "1", "前段 1 格（原文）"),
 ("A3-2", "144／200MA 雙翻揚 20 日內觸及 ×1.3（H2）", "登錄全文-PREREGH2_144與200MA雙翻揚_台股策略線_seq2_sha239b4fac2cd6b856-15401B-20260925-0117.md（封存）", "239b4fac2cd6b856",
  "③ 事件（判定 20 日；60／120／240 描述）",
  "對照池 gate3 同日同 vol60 五分位 → 合併母體同日同 vol60 五分位；上市／上櫃組成 → S&P 500／400 組成",
  "T+1 開盤漲停不成交（美股無）；處置閘", "否", "1", "前段 1 格（原文）"),
 ("A3-3", "N字底與 N型走法（照作者原文含量能）", "登錄全文-N字底與N型走法_照作者原文含量能_登錄_台股策略線_seq1_sha4df1f473b005da3c-6376B-20261004-0200.md", "4df1f473b005da3c",
  "① 條件（seq2：停損或目標價先到先出、⛔ 無時間上限、窗尾結算；原文 H{5,10,20,60} 降描述）",
  "母體 W1 eligible → 合併母體；量 原始股數 → Yahoo 拆股調整量；段 探索 2017-03～2021-12／確認 2022-01～2026-08 → P1",
  "P 代理臂（三大法人近 5 日買超）⇒ P＝M ⇒ 退化；隔天鎖漲停「買不買得到」；處置中；早年段",
  "是（P 臂）", "6", "seq2：照原文訊號格數 ⛔ 不乘 H ＝（甲1、甲2、N型）× {站得住, 量能加分}＝6；台股 28 的 P 臂 4 格拿掉"),
 ("A3-4", "上升趨勢線跌破（個股層）", "登錄全文-上升趨勢線跌破_個股層_登錄_台股策略線_seq1_shaffac12dee65c6bf1-2944B-20260927-1238.md（封存）", "ffac12dee65c6bf1",
  "③ 事件（主格 20 日判）", "同月全母體 → 合併母體；上市／上櫃 → S&P 500／400", "（無）", "否", "1", "主格 1 格；17 格描述"),
 ("A3-5", "型態全量 單筆層（96 變體）", "登錄全文-型態全量_單筆層登錄_台股策略線_seq3_shab7b4a05af0341797-24408B-20260925-2043.md（封存）", "b7b4a05af0341797",
  "③ 事件（H20、H60 判；H120 描述）",
  "配對對照 gate3 → 合併母體同日同十分位；「無影」原始價 → 還原價同日逐位相等（P13）；上市／上櫃 → 兩指數",
  "T+1 開盤漲停／跌停剔除（美股無）", "否", "動態", "可判定格（合併 n_eff ≥30）；USREG-X 五型不在 96 變體內 ⇒ 扣 0（P13）"),
 ("A3-6", "訊號對訊號交易系統（E1／E2 進、X 出、可再進；停損停利 16 組；0050 層）", "登錄全文-訊號對訊號交易系統_築底反轉進高檔出_登錄_台股策略線_seq1_sha8e8595d3ce5f3c51-9449B-20260927-1710.md", "8e8595d3ce5f3c51",
  "① 條件（X 訊號出場；固定 20／60／120 描述）",
  "0050 層 → SPY 層（含息、同規則）；判準 0050 → ^SP500TR；母體 W1 → 合併母體",
  "早年段；開盤漲停買不到", "否", "4", "E1、E2、SPY 層、停損停利挑出 1 格（挑中「無」⇒ 不另加，本體才知道）"),
 ("A3-7", "訊號系統均線出場（跌破 10／20／60 日線）", "登錄全文-訊號系統均線出場_10與20與60日線_登錄_台股策略線_seq1_sha39c29b1596b81dba-5446B-20260927-1910.md", "39c29b1596b81dba",
  "① 條件（由上往下穿越 MA）", "母體 → 合併母體；判準 → ^SP500TR", "早年段", "否", "動態", "2 族 × 1；某族 3 格全退化（seq246）⇒ 該族依構造不可判定、不計"),
 ("A3-8", "週線訊號單測（S1～S4 × k{4,8,12,26} 週）", "登錄全文-週線兩件_週線訊號單測與營量週收盤出場_登錄_台股策略線_seq1_sha3c7ad365dc7a2f33-5007B-20260928-2230.md（封存）", "3c7ad365dc7a2f33",
  "③ 事件＋（原文 k 週持有＝格；營量週收盤出場件不搬）",
  "基準① eligible 等權 → 合併母體等權；基準② 前 4 週報酬十分位 → 合併母體；週內硬斷點（面額變更、減資）→ 轉接層 hard_break",
  "乙件（營量 v1 週收盤出場）不搬；早年段", "否", "動態", "16 格扣「合併 n_eff（月）＜30」的依構造不可判定格"),
 ("A3-10", "爆量突破進場、跌破 EMA 出場（網格 60 格，seq2）", "登錄全文-爆量突破進場與跌破EMA出場_Threads作者指標常見值網格_登錄_台股策略線_seq2_sha0c44c9e73bba2397-7319B-20261004-2120.md", "0c44c9e73bba2397",
  "① 條件（收盤 ＜ EMA 即賣；作者原文）",
  "紅K 原始開收 → 還原開收（同日係數相同）；量 原始股數 → Yahoo 拆股調整量；UG.set_gate_v2 → 合併母體；判準 0050 → ^SP500TR",
  "開盤鎖漲停買不到、鎖跌停順延；早年段（原文「早年 ＜31 格合格 ⇒ 最多暫定」⇒ 疑點 Q1）", "否", "1", "60 格整套一判（過半 ≥31／60）"),
 ("A3-11", "外部長線三件（趨勢樣板 T、週線達華斯 D、一目三役 I）", "登錄全文-外部長線戰法三件_趨勢樣板與週線達華斯與一目三役_登錄_台股策略線_seq2_sha04f9758bb33bc345-7448B-20260928-2353.md（封存）", "04f9758bb33bc345",
  "① 條件（T 換股簿續抱；D 週收破箱底；I ATR 移動停損）",
  "T 乙 月營收創 24 月新高 → 季營收創 8 季新高；I 甲 臺灣50 成分 → 當月 S&P 500 市值前 50（代理，P12）；I 判定段（TEJ 台股期間外）→ 美股全窗；溫斯坦（描述）股價÷0050 → ÷^SP500TR",
  "早年段；-KY創 閘（台股限定）", "是（T 乙族營收條件換成季版，不算拿掉）", "3", "T、D、I 各 1"),
 ("A3-12", "動能改良版四件（剔極端、持續、殘差、波動縮放）", "登錄全文-動能改良版四件_剔極端持續殘差波動縮放_登錄_台股策略線_seq1_shaf9b6932850aa4ea7-4366B-20260927-2052.md（封存）", "f9b6932850aa4ea7",
  "② 不再符合才換", "M3 殘差迴歸 對 0050 月報酬 → 對 ^SP500TR 月報酬；判準 → ^SP500TR", "營量 v1 對照（美股無）；早年段", "否", "4", "四件各 1"),
 ("A3-13", "突破後過濾（直接買 vs 幅度／站穩／放量／等回測／三道全加）", "登錄全文-突破後過濾_直接買對加過濾_登錄_台股策略線_seq4_shad01e9d830657bb38-8682B-20260926-2339.md（封存）", "d01e9d830657bb38",
  "③ 事件（終點＝A 的 H60）", "W 底／頭肩底 ＝ patterns_x、箱型 ＝ 研究二 box_breakout（美股 OHLCV）", "原始價漲跌停判定", "否", "動態", "14 格扣依構造不可判定（60 日區段 ＜30）與退化（≥95% 與 A 同日）"),
 ("A3-14", "外部作者七顆之六顆（W1、Y1～Y5）", "登錄全文-外部作者批七顆_波段醫生與楊爸_登錄_台股策略線_seq1_sha62e4026f16879fed-10494B-20260927-1910.md", "62e4026f16879fed",
  "① 條件（跌破 MA10／20／60、作者出場）", "母體 → 合併母體；判準 → ^SP500TR",
  "W2 年線戰法 → 另立 A4-9；早年段", "否", "6", "六顆各 1（一顆全部格退化 ⇒ 依構造不可判定，N 照計＝原文 seq248 ⑦）"),
 ("A3-15", "外部作者追加三顆（S1、F1、O1）", "登錄全文-外部作者追加三顆_量縮補量跌與三線反紅與假跌破_登錄_台股策略線_seq1_sha48cbe3c0f1fccd3e-4973B-20260927-1914.md", "48cbe3c0f1fccd3e",
  "① 條件", "S1 基準＝五顆進場任一（W2 用季營收版）；F1 與多頭吞噬重疊 ＝ patterns_all K56", "早年段", "否", "3", "三顆各 1（照原文 N 照計）"),
 ("A3-16", "洗盤還是出貨（圖卡四條合判）", "登錄全文-洗盤還是出貨_圖卡四條合判_全市場當下可判版_登錄_台股策略線_seq1_shabed6ad77174957ec-5722B-20261004-2159.md", "bed6ad77174957ec",
  "③ 事件（H{5,20,60} 原文各自判）", "對 0050（另報）→ ^SP500TR；UG.set_gate_v2 → 合併母體；量 原始股數 → Yahoo 拆股調整量", "鎖漲停買不到；早年段", "否", "9", "3 問 × 3 H；每問過半格門檻（≥9／16，有足夠樣本格為分母另報）"),
 ("A3-17", "飆股回推比對 價量特徵部分（seq7 §十一：2021～2026）", "登錄全文-飆股回推比對_起漲前特徵與可交易性_登錄_台股策略線_seq7_sha15a22c6b6c2c36d0-22678B-20261002-0029.md", "15a22c6b6c2c36d0",
  "描述（③ 可交易曲線另標）",
  "飆股 ＝ seq6 網格（H 25 × g 10 ＝ 250 格）在美股母體重算、取格中位（裁定 seq311、seq318）；股價級距（台幣元）→ 價位五等分；股本 → B2 股數；周轉率 → Yahoo 量÷B2 股數；產業 → GICS；大盤 0050 在 200 日線上 → ^GSPC 在 200 日線上",
  "20 日內漲停天數；「買不買得到」版（漲停鎖死、處置分盤）；法人（外資／投信淨買、投信連買）；融資（餘額變化、使用率、停止融資）；借券；集保大戶；注意／處置次數；新聞 N1～N3；分點",
  "是", "待定", "＝ 確認段實際驗的特徵數（要用飆股標籤挑 ⇒ ⛔ 本步不算）"),
 ("A4-1", "品質因子選股（ROE、營業利益÷資產、ROA、研發強度；甲單用／乙營收創高池內）", "登錄全文-品質因子選股_ROE與營業利益資產與研發_登錄_台股策略線_seq1_sha24e7fb594193b9c0-5052B-20260927-2052.md", "24e7fb594193b9c0",
  "② 不再符合才換", "fin_hist TTM → B1 TTM（P7）；母公司淨利／權益 → B1 淨利／權益；金融保險業 → GICS Financials；乙池 月營收創 24 月新高 → 季營收創 8 季新高",
  "早年段；營量 v1 對照（改「同池量放大挑」並列）", "否", "2", "兩族各 1"),
 ("A4-2", "大師三套（墨菲 seq4：墨菲／喜偉／歐沙那希）", "登錄全文-墨菲成長品質選股_登錄_台股策略線_seq4_sha48365ba96fb2b1a9-11229B-20260927-1710.md", "48365ba96fb2b1a9",
  "② 不再符合才換（三套各一；原文 H{20,60,120} 降描述）",
  "官方本益比 → 市值÷TTM 淨利（P8）；負債比 → (資產−權益)÷資產（B1 無負債欄）；EPS → 年淨利÷封面股數（B1 無 EPS）；t57sb01 可用日 → first_filed 次一交易日；研發 XBRL → B1 rnd",
  "（無；研發缺 ⇒ M4 不符＝原文）", "否", "3", "seq2：9→3（3 套 × 1）"),
 ("A4-3", "外部研究三件（X1 多因子、X2 CGO＋低波動、X3 營收創紀錄季版）", "登錄全文-外部研究三件_多因子_CGO_營收創紀錄_登錄_台股策略線_seq1_shad412ffe18178b3be-8333B-20260927-1710.md", "d412ffe18178b3be",
  "X1、X2 ② 不再符合才換｜X3 ③ 事件（20 日判、60 日描述）",
  "X1 月營收年增率 → 季年增率、「連 3 個月年增＞0」→ 連 1 季（被 10%～150% 包含 ⇒ 子條件自然消失）、營收延後 14 天 → first_filed；X2 日成交均價（金額÷股數）→ (高＋低＋收)÷3（美股無成交金額）、週轉率 → Yahoo 量÷B2 股數；X3 月營收創紀錄 → 季營收創紀錄（＞之前所有季、≥8 季歷史）、公告日 → first_filed 次一交易日、只上市 → 全母體；原文期間（台股）→ 美股全窗判",
  "X3 描述格「公告日三大法人淨賣超」⇒ 只剩「公告前 20 日漲 ≥10%」", "是（X3 描述格）", "3", "X1、X2 組合各 1＋X3 前段 1"),
 ("A4-4", "低週轉選股（甲單用、乙營收創高池內）", "登錄全文-低週轉選股_單用與營收創高池內_登錄_台股策略線_seq1_sha47ac98f3c6b5fb02-4221B-20260928-1324.md（封存）", "47ac98f3c6b5fb02",
  "② 不再符合才換", "發行股數 → B2 封面股數＋Yahoo 拆股（P8）；乙池 月營收創 24 月新高 → 季營收創 8 季新高", "早年段；營量 v1 對照（改同池量放大挑並列）", "否", "1", "原文 N_組合 ＋1（兩族各挑 1）"),
 ("A4-5", "強勢類股選股（熱力圖邏輯）", "登錄全文-強勢類股選股_熱力圖邏輯_登錄_台股策略線_seq1_shabb1c8b224f5bb587-4985B-20260927-1710.md", "bb1c8b224f5bb587",
  "② 不再符合才換", "資料庫產業別 → GICS（B3，層級照 P9）；(b) 月營收創 24 月新高 → 季營收創 8 季新高；換股日「每月 10 日後第一個交易日」照用", "營量 v1 對照；早年段", "否", "1", "探索挑 1"),
 ("A4-6", "產業營收加速（季版；E0～E3 出場臂）", "登錄全文-產業營收加速_挑正在爆發的產業與吃到起漲到頂幾成_登錄_台股策略線_seq3_sha42339de513c98702-12287B-20261002-1047.md（封存）", "42339de513c98702",
  "② 不再符合才換（E1～E3 條件出場臂）",
  "產業營收（月）→ 季：A1 近 3 月年增 → 近 1 季年增；A2 近 3 月−近 12 月 → 近 1 季年增 − 近 4 季合計年增；A3 → 近 1 季年增 − 前 1 季的同一數字；S3 創 24 月新高 → 8 季新高；E1 營收轉減速 → 季版 A2 由正轉負；換股日 → P10；industry_pit → GICS；市值 → B2×原始收盤",
  "早年段", "否", "1", "216 格挑 1；結果句並引台股兩件不合格（seq315、317）"),
 ("A4-7", "事件型兩件（庫藏股代理、指數成分剔除）", "登錄全文-事件型兩件_庫藏股與指數成分剔除_登錄_台股策略線_seq2_sha8eae2968c12438fc-5871B-20260928-0101.md（封存）", "8eae2968c12438fc",
  "③ 事件（單筆 4 視窗；組合層各 1）",
  "庫藏股董事會決議日 → 季買回÷市值前 x%（代理，可用日 first_filed，P11）；0050 剔除 → S&P 500／S&P 400 剔除（生效日）",
  "庫藏股目的 1／目的 3 分類（無逐筆事件）⇒ 兩類與「全部」相同 ⇒ 退化；成分剔除「公告日後進場」臂（資料無公告日）", "是", "動態", "組合層：庫藏股 1（x 待裁定）＋成分剔除 1（年均 ≥10 件才計）"),
 ("A4-8", "新選股來源第一批（六個單一條件前 10%）", "登錄全文-新選股來源第一批_單一條件_登錄_台股策略線_seq1_sha0b7bba5f1184cc5a-8108B-20260925-2119.md（封存）", "0b7bba5f1184cc5a",
  "② 不再符合才換（原文第 120 根收盤出場降描述）",
  "N1 月營收年增率 → 季年增率；N2 近三月累計年增 → 近 1 季 ⇒ ≡N1；N5 本益比 → 市值÷TTM 淨利、現金殖利率 → Yahoo 配息÷價、股淨比 → B1 權益÷市值",
  "N6 外資買超強度（整格只有這一條 ⇒ 不成格）；對照「門檻B（W1）」（美股無）", "否", "4", "6 格 − N2（≡N1 退化）− N6（拿掉）＝ 4"),
 ("A4-9", "外部作者七顆之 W2 年線戰法（季財報版）", "（同 A3-14）登錄全文-外部作者批七顆_波段醫生與楊爸_登錄_台股策略線_seq1_sha62e4026f16879fed-10494B-20260927-1910.md", "62e4026f16879fed",
  "① 條件（跌破 MA10／20／60）", "最近一期月營收 YoY＞0 → 最新一季季營收 YoY＞0；季淨利由負轉正 照字面（P20）", "早年段", "否", "1", "1 顆 1 格（退化也照計）"),
 ("A4-10", "飆股回推比對 季財報特徵部分", "（同 A3-17）登錄全文-飆股回推比對_起漲前特徵與可交易性_登錄_台股策略線_seq7_sha15a22c6b6c2c36d0-22678B-20261002-0029.md", "15a22c6b6c2c36d0",
  "描述", "營收各特徵 → 季版（創 24 月新高 → 8 季、年增率、月增率 → 季增率、連續年增月數 → 季數、距 24 月最高 → 距 8 季最高、R1 轉折、R2 跳級）；EPS 轉正 → 季淨利轉正（代理）；ROE、營益率比去年同季升 → B1",
  "毛利率比上季升（B1 沒有毛利）", "是", "待定", "＝ 確認段實際驗的特徵數（⛔ 本步不算）"),
 ("A4-11", "機器學習選股兩件（RF／GB／LIN seq1；改目標 numpy seq1）", "登錄全文-機器學習選股_隨機森林梯度提升_登錄_台股策略線_seq1_sha78af43d3df5bd042-3951B-20260927-2109.md（封存）＋登錄全文-機器學習選股改目標_預測對0050超額與大贏家與波動中性_登錄_台股策略線_seq1_sha168560f97763a287-5452B-20260928-0924.md（封存）", "78af43d3df5bd042／168560f97763a287",
  "② 不再符合才換", "特有波動 對 0050 → 對 ^SP500TR；目 A 超額 對 0050 → 對 ^SP500TR；營收四特徵 → 季版；周轉率 → B2；Amihud 用 收盤×量；財報 → B1",
  "籌碼（投信、外資近 20 日淨買）；營量 v1 對照", "是", "2", "兩件各 1"),
 ("A4-12", "多個弱訊號十一票（等權投票）", "登錄全文-多個弱訊號合成分數選股_十一票等權_登錄_台股策略線_seq1_shadbc1881f24a76661-5709B-20260927-1938.md（封存）", "dbc1881f24a76661",
  "② 不再符合才換", "① 創 24 月新高 → 8 季新高；② 月營收年增 ≥15% → 季年增 ≥15%", "⑤ 強勢股 5 條中的「20 日漲停 ≥3 次」⇒ ⑤ 改 4 條中 ≥3（票數仍 11）；營量 v1 對照", "是（⑤）", "1", "主版 1 格"),
 ("A4-13", "探索批（18 條件、171 格 → 5 條線索 → 確認）", "登錄全文-探索批_不用門檻B放開試_規格_台股策略線_seq4_shad41c9151eca3fd53-9587B-20260926-2336.md（封存）", "d41c9151eca3fd53",
  "照原文（8 槽、第 120 根收盤出）", "F01 → 季年增；F02 → ≡F01；F03 月增 → 季增；F04 距 24 月最高 → 距 8 季最高；F16 → 市值÷TTM 淨利；F17 → Yahoo 配息÷價；F18 → B1 權益÷市值；窗 探索 2016～2021／確認 A 2022～2026-09",
  "F13 外資、F14 投信、F15 融資；確認窗 B（早年）", "是", "5", "5 條線索（確認段 N＋5）；格 171 → 拿掉含 F13～F15 的 51 格 → 120 → F02 退化 15 格 → 105"),
]


def stage_md(a):
    S = json.load(open(os.path.join(OUT, "prep_summary.json"), encoding="utf-8"))
    DEG = pd.read_csv(os.path.join(OUT, "退化格清單.csv"))
    CV = pd.read_csv(os.path.join(OUT, "覆蓋率_換掉與新算的量.csv"))
    PO = pd.read_csv(os.path.join(OUT, "候選池大小_每月.csv"))
    TRG = pd.read_csv(os.path.join(OUT, "觸發率_二元條件.csv"))
    EVT = pd.read_csv(os.path.join(OUT, "事件數_單筆層.csv"))
    BF = pd.read_csv(os.path.join(OUT, "A3-13_突破過濾_開跑前算術.csv"))
    WK = pd.read_csv(os.path.join(OUT, "A3-8_週線_頻率表.csv"))
    SY = pd.read_csv(os.path.join(OUT, "A3-6_A3-7_條件出場_開跑前.csv"))
    VB = pd.read_csv(os.path.join(OUT, "A3-10_爆量突破_開跑前.csv"))
    EX = pd.read_csv(os.path.join(OUT, "A3-14_A3-15_外部作者_事件數.csv"))
    EXS = pd.read_csv(os.path.join(OUT, "A3-14_A3-15_出場段尾.csv"))
    PT = pd.read_csv(os.path.join(OUT, "A3-5_型態全量_頻率表.csv"))
    NPT = pd.read_csv(os.path.join(OUT, "A3-3_N字底N型_格事件數.csv"))
    SU = pd.read_csv(os.path.join(OUT, "A3-17_飆股價量二元特徵_觸發率.csv"))
    # 動態 N
    nA35 = int(S["A3-5"]["可判定(合併n_eff≥30)"])
    deg7 = DEG[DEG["件"] == "A3-7"]
    nA37 = sum(1 for fam in ("E1", "E2") if sum(1 for g in deg7["格"] if g.startswith(fam)) < 3)
    nA38 = int((WK["合併n_eff(月)"] >= 30).sum())
    bad13 = DEG[DEG["件"] == "A3-13"]["格"].nunique()
    nA313 = 14 - bad13
    yr7 = S["A4-7_剔除"]["合併 年均有價"]
    nA47 = 1 + (1 if yr7 >= 10 else 0)
    dyn = {"A3-5": nA35, "A3-7": nA37, "A3-8": nA38, "A3-13": nA313, "A4-7": nA47}
    rows = []
    for it in ITEMS:
        k = it[0]
        N = dyn.get(k, it[8])
        rows.append({"件號": k, "名稱": it[1], "引用台股登錄（檔名）": it[2], "sha": it[3], "出場型": it[4], "被換掉的條件（台股→美股）": it[5],
                     "被拿掉的條件": it[6], "特徵不全": it[7], "N實數": N, "N計法": it[9],
                     "退化格數": int((DEG["件"] == k).sum()) if k not in ("A3-5",) else int((DEG["件"] == k).sum())})
    IT = pd.DataFrame(rows)
    IT.to_csv(os.path.join(OUT, "清單_29件.csv"), index=False, encoding="utf-8-sig")
    nums = [int(x) for x in IT["N實數"] if str(x).lstrip("-").isdigit()]
    S["N合計_可數"] = int(sum(nums))
    pend = list(IT[~IT["N實數"].astype(str).str.lstrip("-").str.isdigit()]["件號"])
    L = []
    w = L.append
    w("# USREG-A3／A4 開跑前清單（⛔ 不含報酬）")
    w("")
    w("**回測線計算子代理｜讀法寫死 %s｜資料 us-stock-data %s（＝ main HEAD）**" % (READ_TS, S["資料"][:10]))
    w("依據：美股登錄 seq1（sha 0dc16d3267725d7c）＋seq2（sha bc0927fed5996fd4）；裁定 seq318 §三、seq316、seq311。")
    w("")
    w("⛔ 本報告只有條件可得性、覆蓋率、事件數、格數、退化格；**沒有算任何報酬、勝率、飆股標籤、目標價達成**。")
    w("")
    w("## 一、結論")
    w("")
    w("- 29 件，N 實數合計 **%d**（可數部分）；%s 兩件 N 待探索段（要用飆股標籤挑特徵，本步不能算）。" % (S["N合計_可數"], "、".join(pend)))
    w("- 退化格共 %d 列（見 `退化格清單.csv`）。" % len(DEG))
    w("- 需要裁定的疑點見 §六。")
    w("")
    w("## 二、逐件一覽（出場型、換掉／拿掉、N）")
    w("")
    w("| 件 | 名稱 | 出場型 | 被換掉 | 被拿掉 | 特徵不全 | 退化格 | N |")
    w("|---|---|---|---|---|---|---|---|")
    for r in IT.itertuples(index=False):
        w("| %s | %s | %s | %s | %s | %s | %d | %s |" % (r.件號, r.名稱, r.出場型, r._5, r.被拿掉的條件, r.特徵不全, r.退化格數, r.N實數))
    w("")
    w("引用的台股登錄（檔名＋sha）與 N 計法逐件在 `清單_29件.csv`。")
    w("")
    w("## 三、換掉的條件：美股資料來源與覆蓋率")
    w("")
    w("覆蓋率 ＝ 在指數期間的股-月（每月第一個交易日、當天在該指數）中，該量算得出來的比例。")
    w("")
    w("| 量 | 用在 | S&P 500 | S&P 400 | 資料來源 | 註 |")
    w("|---|---|---|---|---|---|")
    for q, g in CV.groupby("量", sort=False):
        a5 = g[g["母體"] == "S&P 500"].iloc[0]; a4 = g[g["母體"] == "S&P 400"].iloc[0]
        w("| %s | %s | %.1f%% | %.1f%% | %s | %s |" % (q, a5["件"], a5["覆蓋率%"], a4["覆蓋率%"], a5["資料來源"], "" if pd.isna(a5["註"]) else a5["註"]))
    w("")
    w("⚠ 價格面板從 2015-12 起 ⇒ 回看 250 日的量（樣板、12−1 動能、RS、250 日新高）最早 2016-12 才算得出；這拉低全期覆蓋率。")
    w("")
    w("## 四、拿掉的條件與「特徵不全」")
    w("")
    w("全批規則（登錄 §〇 ②）：月營收以外、美股沒有的條件一律拿掉。本批實際拿掉的：")
    w("")
    for r in IT.itertuples(index=False):
        if r.被拿掉的條件 and r.被拿掉的條件 != "（無）":
            w("- **%s**：%s%s" % (r.件號, r.被拿掉的條件, "（標「特徵不全」）" if str(r.特徵不全).startswith("是") else ""))
    w("")
    w("## 五、退化格與事件數")
    w("")
    w("### 退化格分類（逐列見 `退化格清單.csv`）")
    w("")
    w("| 件 | 類型 | 列數 | 例 |")
    w("|---|---|---|---|")
    for (k_, t_), g in DEG.groupby(["件", "類型"], sort=False):
        w("| %s | %s | %d | %s |" % (k_, t_, len(g), "；".join(list(g["格"])[:3]) + ("…" if len(g) > 3 else "")))
    w("")
    w("### A3-5 型態全量")
    w("- 判定格上限 %d（96 變體 × H20、H60）；**可判定（合併 n_eff ≥30）%d 格**（H20 %d、H60 %d）；其中只 S&P 400 欄 n_eff ＜30 的 %d 格 ⇒ 依構造最多「事後擴母體」。" % (
        S["A3-5"]["判定格上限"], nA35, S["A3-5"]["H20可判定"], S["A3-5"]["H60可判定"], S["A3-5"]["其中只400n_eff<30"]))
    w("- 不可判定格逐列見 `退化格清單.csv`；全表 `A3-5_型態全量_頻率表.csv`。")
    w("")
    w("### 單筆層事件數（合併欄；n_eff 上限）")
    w("")
    w("| 件 | 格 | 欄 | 事件 | 探索 | 確認 | n_eff 上限 |")
    w("|---|---|---|---|---|---|---|")
    for r in EVT.itertuples(index=False):
        ne = r[-1] if not pd.isna(r[-1]) else (r[-2] if len(r) > 7 else "")
        vals = [x for x in r[6:] if not pd.isna(x)]
        w("| %s | %s | %s | %d | %d | %d | %s |" % (r.件, r.格, r.欄, r.事件, r.探索, r.確認, int(vals[0]) if vals else ""))
    w("")
    w("### A3-13 突破過濾 開跑前算術")
    w("")
    w("| 型 | 買法 | 事件 | 買到 % | 與 A 同日 % | n_eff（合併） | n_eff（只 400） |")
    w("|---|---|---|---|---|---|---|")
    for r in BF.itertuples(index=False):
        w("| %s | %s | %d | %.1f | %.1f | %d | %d |" % (r.型, r.買法, r.事件, r._3, r._4, r._6, r._7))
    w("")
    w("### A3-3 N字底／N型（不去重版，事件數為上限）")
    w("")
    for k_, v_ in S["A3-3"].items():
        w("- %s：%s" % (k_, v_))
    w("")
    w("### A3-6／A3-7 條件出場（探索段，事件為單位）")
    w("")
    sub = SY[SY["段"] == "探索"]
    w("| 族 | 出場 | 進場訊號 | 段尾未出場 % |")
    w("|---|---|---|---|")
    for r in sub.itertuples(index=False):
        w("| %s | %s | %d | %.1f |" % (r.族, r.出場, r.進場訊號, r._6))
    w("")
    w("均線穿越每股票年：%s；SPY 層訊號數：見 prep_summary.json。" % S["A3-7_均線穿越每股票年"])
    w("")
    w("### A3-10 爆量突破（探索段）")
    w("- M 格 %d；平均持有 ＜2 根的格 %d（只標、仍計分母）；交易筆數 ＜30 的格 %d。" % (S["A3-10"]["M格"], S["A3-10"]["平均持有<2根格數(探索)"], S["A3-10"]["交易筆數<30格數(探索)"]))
    w("")
    w("### A3-11")
    w("- T 趨勢樣板：%s" % S["A3-11_T"])
    w("- D 週線達華斯：%s" % S["A3-11_D"])
    w("- I 一目：%s" % S["A3-11_I"])
    w("")
    w("### A3-12：%s" % S["A3-12"])
    w("")
    w("### A3-14／A3-15 外部作者（seq248 ④：主窗事件 ＜200 或年均 ＜10 ⇒ 退化）")
    w("")
    w("| 顆 | 名 | 主窗事件（合併） | 年均 | 主窗事件（只 400） | 年均 |")
    w("|---|---|---|---|---|---|")
    for r in EX.itertuples(index=False):
        w("| %s | %s | %d | %.1f | %d | %.1f |" % tuple(r))
    w("")
    w("### A3-16 洗盤：每格兩組事件 ≥30 的格數（16 格中）")
    w("")
    for k_, v_ in S["A3-16"].items():
        w("- %s：%d" % (k_, v_))
    w("")
    w("### A3-17 飆股價量二元特徵觸發率（2021-01～窗尾，股-日）")
    w("")
    w("| 特徵 | 合併觸發 % | 只 400 觸發 % | 旗標 |")
    w("|---|---|---|---|")
    for r in SU.itertuples(index=False):
        w("| %s | %.3f | %.3f | %s |" % (r.特徵, r._2, r._3, "" if pd.isna(r.退化旗標) else r.退化旗標))
    w("")
    w("### A4：候選池大小（每月，在指數）")
    w("")
    w("| 池 | 每月中位 | p10 | p90 | ＜10 檔月數 | ＜20 檔月數 | 第一個 ≥10 檔的月 |")
    w("|---|---|---|---|---|---|---|")
    for r in PO.itertuples(index=False):
        w("| %s | %.0f | %.0f | %.0f | %d | %d | %s |" % (r.池, r.每月中位, r.p10, r.p90, r._4, r._5, r._7))
    w("")
    w("- A4-2 起點規則（三套可算比例都首次 ≥90%%）：%s" % S["A4-2_起點"])
    w("- A4-3 X3 季營收創紀錄：窗內事件 %s；窗內且當月在指數 %s；有事件的月 %s。" % (S["A4-3_X3_窗內(≤窗尾−21)"], S["A4-3_X3_窗內且當月在指數"], S["A4-3_X3_有事件的月數"]))
    w("- A4-5／A4-6 類股層級（P9）：%s；A4-6 可排名產業數：%s" % (S["A4-5_類股層級"], S["A4-6"]))
    w("- A4-7 成分剔除：%s" % S["A4-7_剔除"])
    w("- A4-9 W2：%s" % S["A4-9_W2"])
    w("")
    w("### 觸發率退化旗標（二元條件，股-月）")
    w("")
    fl = TRG[TRG["退化旗標"].notna() & (TRG["母體"] == "合併")]
    if len(fl):
        for r in fl.itertuples(index=False):
            w("- %s｜%s：%.2f%%（%s）" % (r.件, r.條件, r._4, r.退化旗標))
    else:
        w("- 無")
    w("")
    w("## 六、需要裁定決定的疑點")
    w("")
    for q in QUESTIONS(S, dyn):
        w("- " + q)
    w("")
    w("## 七、執行者補讀法（寫死於 %s）" % READ_TS)
    w("")
    doc = __doc__.split("═══ 執行者補讀法")[1].split('"""')[0]
    for line in doc.strip().splitlines()[1:]:
        w(line.rstrip())
    w("")
    w("## 八、確認")
    w("")
    w("- ⛔ 沒有算任何報酬、勝率、飆股標籤、目標價達成、持有報酬；事件之後只讀成交可不可行與條件出場訊號的日期。")
    w("- 輸出只有彙總；逐檔中間檔在 ~/us_work/a34/（repo 外）。")
    open(os.path.join(OUT, "PREP_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(S, open(os.path.join(OUT, "prep_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L)[:3000])


def QUESTIONS(S, dyn):
    q = []
    q.append("Q1 早年段：台股原登錄多件「確認段＋早年段取較嚴」或「早年不足 ⇒ 最多暫定」（A3-10 等），美股沒有早年段 ⇒ 是否一律標「最多暫定」，或只看確認段＋seq316 兩母體？")
    q.append("Q2 A3-5：USREG-X 測過的五型不在 96 變體內，美股登錄「扣五型」扣 0；只 S&P 400 欄 n_eff ＜30 的格（%d 格）是否仍計 N（本步計入）？" % S["A3-5"]["其中只400n_eff<30"])
    q.append("Q3 A3-8：週線 16 格原文是「k 週持有」各自判；seq308 事件研究「20 日判」是否改成只判 4 週、其餘描述（會讓 N 由 %d 變 4）？本步照原文。" % dyn["A3-8"])
    q.append("Q4 A3-3：N字底 P 臂（法人）拿掉 ⇒ N 6；停損兩版（回測低點／前低）是否算格軸（台股當格軸、不另計 N）？本步照台股讀法。")
    q.append("Q5 A3-11 件 I 母體甲「臺灣50」⇒ 本步用「當月 S&P 500 市值前 50」代理；或改 S&P 500 全體？")
    q.append("Q6 A4-7 庫藏股代理「季買回占市值前 x%%」的 x 登錄未寫；建議裁定給值（例：每季前 10%%）後才能數事件；成分剔除年均可交易事件 %.1f 件（≥10 才開組合層）。" % S["A4-7_剔除"]["合併 年均有價"])
    q.append("Q7 A4-9 名稱「季淨利轉正版」與全批規則（月營收 YoY → 季營收 YoY 保留）不一致；本步兩條「或」都留。")
    lv = S["A4-5_類股層級"]
    q.append("Q8 A4-5／A4-6 類股層級：成分 ≥5 的類別數 月中位 sector %.0f、sub-industry %.0f；照 P9 取較接近台股約 30 類的 ⇒ **sector**；"
             "但 A4-5 的 k ∈ {1,3,5} 在 11 類裡 k＝5 幾乎是半個市場、A4-6 K＝3 也近三成 ⇒ 請裁定用 sector 還是 sub-industry。" % (
                 lv["sector"]["成分≥5類別數 月中位"], lv["sub-industry"]["成分≥5類別數 月中位"]))
    q.append("Q9 A4-11 ML seq1（78af）在台股已被 seq264 暫停（判定版），美股登錄仍各計 1；seq1 需 LightGBM／RF 套件（使用者規矩：先用現有環境簡單版）⇒ 美股是否照 168560 的 numpy 版做、seq1 降描述？")
    st = S["A4-2_起點"]
    q.append("Q10 A4-2 原文 §三 起點規則「三套可算比例都首次 ≥90%%」在美股 **%s**（各套可算比例最高 %s；排除 GICS Financials 後最高 %s）：缺的是營業利益標籤、"
             "5 個會計年度（B1 2013 起 ⇒ 最早 2018）與銀行保險；台股 §八③ 是「上市不滿年數 ⇒ 依定義不符」。請裁定：比照把「資料缺 ⇒ 不符」、起點改「5 年條件首次可算」"
             "（墨菲候選首次 ≥10 檔 2018-03），或其他。另：喜偉每月候選中位 2 檔、123／129 個月 ＜10 檔（原文：句前加「常常湊不滿 10 檔」照跑）。" % (
                 st["三套可算比例都≥90%的第一個月"], st["各套可算比例最高"], st["描述_排除Financials_各套可算比例最高"]))
    q.append("Q11 A3-16 洗盤組太少：每格「洗盤組」事件 ≥30 的格，合併欄 5～6／16、只 S&P 400 欄 2／16（出貨組 16／16）⇒ Q1、Q2 過半門檻的分母（足夠樣本格）在只 S&P 400 欄只剩 2 格，"
             "seq316 兩欄都要過 ⇒ 依構造幾乎只能「事後擴母體」；請裁定是否照跑。")
    q.append("Q12 A3-6 訊號系統：出場「黃昏之星」（X:EVE）探索段段尾未出場 E1 85%、E2 81%，高檔爆量長上影確認（X:VSc）約 50%（台股正是挑中 EVE 而依構造不可判定）；"
             "A3-6 原登錄沒有退化格排除規則（A3-7 有 seq246）⇒ 請裁定是否比照 seq246 事前排除。")
    q.append("Q13 外部作者（A3-14／A3-15）seq248 ④ 退化：Y2in 合併 59 件、F1 46、F1c 33 ⇒ 依構造不可判定（N 照計）；Y3 合併 232 件但只 S&P 400 欄 114 件（＜200）⇒ 只 400 欄不可判定 ⇒ 最多「事後擴母體」。")
    q.append("Q14 創 8 季新高（季版的創 24 月新高）合併股-月觸發 34%、季年增 ≥15% 為 23%：季資料只比 8 個值，比台股月資料寬鬆很多（同義版的機械結果，非退化；結果句宜附註）。")
    q.append("Q15 A4-8 與 A4-13：台股「新選股來源第一批」已被探索批取代撤回，美股兩件都登錄、都計 N（N1～N6 與 F01、F02、F07、F08、F13、F16～F18 重疊），是否兩件都跑？")
    q.append("Q16 A3-17／A4-10 飆股兩件 N ＝ 確認段實際驗的特徵數，要先用美股母體的飆股網格（標籤）在探索段挑 ⇒ 本步無法給數，請裁定准許下一步只算探索段挑選（含標籤）。")
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["px", "fund", "report", "md"])
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--lim", type=int, default=0)
    a = ap.parse_args()
    {"px": stage_px, "fund": stage_fund, "report": stage_report, "md": stage_md}[a.stage](a)


if __name__ == "__main__":
    main()
