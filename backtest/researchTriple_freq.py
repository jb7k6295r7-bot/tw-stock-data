# -*- coding: utf-8 -*-
"""找下一個大漲股：訊號後 3 年內漲 3 倍命中率 seq1【頻率表・乾跑】（台股策略線 登錄 sha 8455d7003a62a190，2026-10-22 21:05；
裁定 seq449 §三 發號：判定 2 格 S1、V ⇒ N_單筆 ＋2、Bonferroni 2 格；S1 最多暫定；另加一欄描述 2005～2016（未看過期間）的 S1；
V 沒有資本支出欄就用營業現金流並標註；先交頻率表、⛔ 不附命中率）——回測線計算子代理。
⛔ 只數事件、配對、n_eff、走得完比例、各欄可算比例、召回率分母、重疊；⛔ 不讀、不算、不存任何進場後報酬、倍數、命中（seq366）。
   用到的價格只有 ≤ 判日（可用日前一交易日）的還原收盤（前 12 月漲跌、距一年低點只用來分位／判 V，⛔ 不存數值）與市值（只存分位）；
   進場日以後只用「有沒有有效 K 棒／壞根／下市／開盤鎖漲停」旗標。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices、rev_table、jia、yi、avail_pos、back_ret、filing_pos、ranks、mnum）＝
   甲、乙（＝ bigrun_monthly.rev_metrics 原函式）與價格面板，⛔ 只 import、不寫第二份；researchIndMom_freq（reg_check、entry_flag、load_pit）、
   researchLongPool（single、qkey、qlabel）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple_freq [--procs 3] [--limit N（乾跑：隨機 N 檔，輸出 ~/trpwork/dry）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple_freq_check [--dry]
輸出 backtest/resultsTriple/freq/：freq.json、freq_段.csv、v_coverage.csv、v_coverage_年.csv、recall_denom.csv、equiv.csv、desc_signals.csv、yearly.csv、
      events_S1.csv.gz、events_V.csv.gz（逐事件旗標，⛔ 無報酬、無價格、無倍數）、run.log

═══ 讀法（T 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 T0 資料：tw-stock-data 最新 origin/main（researchRevTurn_freq.ensure_data，git archive 唯讀）：月營收（early/revenue 2003～2014＋revenue_hist＋每日版）、
    industry_pit、fs_xbrl（2013Q1 起）、filing_dates（t57sb01 上傳時戳）、exright／early exright／otcexright。價格 ＝ researchRevTurn_freq.prices
    （rerun17 H2D edc6f 2015-01-05～2026-09-24 ＋ 早年 eotc 2004-02-11～2014-12-31 合併日曆；四碼普通股、含已下市；壞根 ＝ 缺口 ≥5 日（seq335）∪ 斷點
    ∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2；open_base 用 exright＋otcexright）。500 張閘 ＝ 面板 G[A−1]（含 pit_valid），＝ 營收轉強驗證 V3。
 T1 S1 ＝ 甲 ∧ 乙（甲 ＝ accel ≥ 0.05，乙 ＝ hi24 ∧ ¬hi24_prev；researchRevTurn_freq.jia／yi ＝ bigrun_monthly.rev_metrics 原值）。
    「本期成立、上期不成立」：乙 本身要求上期沒創 24 月新高，而上期 S1 要求上期創 ⇒ 依構造恆成立（等價自查逐列數 S1∧上期S1 ＝ 0）。
    上期 hi24 不可判（nan）⇒ 乙照 jia/yi 原式算「上期沒創」（同營收轉強驗證 V2，件數照報「上期不可判」）。
    可用日 A ＝ researchRevTurn_freq.avail_pos（次月 10 日後第一個交易日；2026-01 期起 15 日）；進場 e ＝ A＋1 開盤。
 T2 事件（兩格同式）：訊號 ∧ 在面板 ∧ G[A−1]；★ 同檔 36 個月內只取第一次 ＝ 過閘訊號依時間排序，與上一個「取用」的月序相差 ＜ 36 ⇒ 不取（照報）。
    進場剔除 ＝ researchIndMom_freq.entry_flag（壞根(A,e] → e 無成交 → e 開盤鎖漲停）。
    無流動性閘版本（描述）：★ 以「A−1 有有效 K 棒」代替 G[A−1]，其餘同式（只數件數）。
 T3 S1 配對（登錄 §五）：同期（＝同一可用日）、本期有月營收列且 S1 為假、同產業（industry_pit 在 A，含 fallback；★「其他」也算一類、無類別 ⇒ 配不到）、
    市值十分位同、前 12 月漲跌三分位同（分位母體 ＝ A−1 過閘面板股中可算者；＝ 營收轉強驗證 V5 原式、researchRevTurn_freq.back_ret／ranks）；
    對照也要過閘、e 可進場；★ 候選 ≥ 3 抽 3、否則全取（1～2）；np.random.default_rng(20261022)，事件依（A, 代號）序逐一抽。
 T4 V（Yartseva 型便宜小型股；登錄 §三字面）：★ 判日 ＝ 每季法定公告期限（Q1 5/15、Q2 8/14、Q3 11/14、年報 次年 3/31；IFRS 2013 起）之後第一個交易日 ＝ A
    （「同一財報可用日」⇒ 全市場同一日橫斷面；〔另一讀法：逐檔上傳時戳當日各自判〕）；e ＝ A＋1 開盤；價格、市值用 A−1。
    各檔用「上傳日（t57sb01，AI1 優先、否則最早文件；seq352）＜ A 日期」的最新一季 k；★ k 比法定目標季落後 ≥ 2 季 ⇒ 不可算（落後 1 季照用、照報）。
    現金流 ＝ 近 4 季（fs_xbrl 年初累計 ⇒ researchLongPool.single 差分、四季加總；合併 cr 優先），自由現金流 ＝ 營業現金流 ＋ capex（capex_ytd 負數 ＝ 流出，
    README 字面；★ 正值 39 列照原值）；capex 近 4 季不可算 ⇒ 用營業現金流（標「OCF代」）。分子 ÷ 市值（A−1；原始收盤 × 股數）。
    淨值 ＝ total_equity（★ 權益總計，含非控制權益；fs_xbrl 無「歸屬母公司權益」欄）在 k 季末 ÷ 市值。
    距一年低點 ＝ c[A−1] ÷ min(還原收盤，日期 ∈ [A−1 日期 − 1 年, A−1]) − 1（★ 收盤最低〔另一讀法：盤中最低〕；A−1 須為有效 K 棒、
    A−1 日期 − 1 年當天或之前須有有效 K 棒（滿一年）、窗內有壞根 ⇒ 不可算）。
    分位母體 ＝ A−1 過閘面板股中該欄可算者（rank pct average）：現金流市值 pct ＞ 0.7、淨值市值 pct ＞ 0.7、市值 pct ≤ 0.5、距一年低點 ≤ 0.20 ⇒ V。
    四欄皆可算 ＝ V 可判。無閘版本（描述）：分位母體 ＝ A−1 有有效 K 棒的面板股。
 T5 V 配對：同一 A、★ V 可判且 V 為假〔另一讀法：含不可判〕、過閘、e 可進場、市值十分位同（十分位母體 ＝ A−1 過閘面板股）；抽樣同 T3（另起一條 rng，同種子）。
 T6 天數：x ＝ e ＋ 750（合併日曆位置）；走得完 ＝ x ≤ 資料尾（2026-09-24）；另報 500 日（2 倍描述）走得完。主格事件 ＝ 配到 ∧ e 可進場 ∧ 750 走得完。
    窗內遇壞根 ＝ (e, x] 有壞根；下市 ＝ 最後有效 K 棒 ＜ x 且距資料尾 ≥ 5 日（處理留正式跑；登錄 §二「下市 ⇒ 之後以最後收盤計」）。
 T7 段（依可用日 A）：S1 探索 2007-01～2014-12｜確認 2015-01～2023-08｜描述「2005～2016（未看過期間，裁定 seq449）」2005-01～2016-12（與兩段重疊，另列）。
    V 探索 2013-05～2017-12｜確認 2018-01～2023-08。n_eff ＝ 主格事件的可用月數；＜ 24 ⇒ 還沒測（〈四十九〉）。
 T8 召回率分母（只報可算筆數、⛔ 不報命中）：resultsBigRun/乙_段_x3.csv.gz（3 倍段 3,316，⛔ 只讀「代號、市場、起點、起點左截斷」）；
    ★ 起漲前 12 個月 ＝ 訊號可用日 A ∈ [起點 − 12 曆月, 起點]；S1 可判 ＝ 窗內有一期 accel 與 hi24 皆可算；轉強可判 ＝ accel 或 hi24 可算；
    V 可判 ＝ 窗內有一個 V 判日四欄可算（過閘版／無閘版各報）。
 T9 描述訊號（不判；只數件數）：甲單獨（甲∧¬乙）、乙單獨（乙∧¬甲）、轉強起點（up∧¬up_prev，＝ 營收轉強驗證）、G1（hi24 狀態）、G1且甲；各自 T2 同式。
    S1 且 V：S1 事件在「A 當天或之前最近一個 V 判日」V 為真；V 事件在前 12 個月內（A_S1 ∈ (A_V − 12 曆月, A_V]）有 S1 狀態。
 T10 等價／退化（seq377）：S1∧上期S1 ＝ 0；S1 ⊂ G1且甲（列數、事件重疊）；S1 事件 vs 營收轉強驗證頻率表甲且乙事件（12 月去重）重疊；
    V 四條件各自通過率與兩兩聯合；V（FCF 優先）vs V（全用 OCF）事件重疊；V 對照池大小。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import pickle
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  轉強甲乙、價格面板、配對工具（⛔ 只 import）
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check、entry_flag、load_pit
from backtest import researchLongPool as LP                 # noqa: E402  single、qkey、qlabel
from backtest import bigrun_monthly as BM                   # noqa: E402  load_rev_pit（只為列期別）

REG_SHA = "8455d7003a62a190"
RUL = "seq449"
OUT = "backtest/resultsTriple/freq"
TW = os.path.expanduser("~/trpwork")
SEED = 20261022
DEDUP_M = 36
HJ = 750
H2 = 500
NEFF_MIN = 24
S1_SEGS = [("探索", "2007-01-01", "2014-12-31"), ("確認", "2015-01-01", "2023-08-31")]
S1_DESC = ("2005～2016(未看過,描述)", "2005-01-01", "2016-12-31")
V_SEGS = [("探索", "2013-05-01", "2017-12-31"), ("確認", "2018-01-01", "2023-08-31")]
Q_FIRST = (2013, 1)
X3_CSV = "backtest/resultsBigRun/乙_段_x3.csv.gz"
RT_EV = "backtest/resultsRevTurn/freq/events.csv.gz"
NOTES = ["頻率表、未算任何報酬、倍數、命中（seq366）",
         "S1 是看過營收轉強驗證（2017～2025-08）甲且乙描述才選的，兩段與已看期間重疊 ⇒ 最多暫定；2005～2016 另列描述（裁定 seq449）",
         "750 日重疊、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」；任一段 n_eff ＜ 24 ⇒ 還沒測",
         "V 自由現金流：capex 近 4 季不可算的檔用營業現金流（標 OCF代）；fs_xbrl 2013Q1 起 ⇒ 近 4 季現金流最早 2013Q4（2014-03-31 判日）",
         "V 是文獻型（美股、只比贏家之間；工作論文），台股首次",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）；早年上櫃 2007-07 前無價",
         "3 倍段是事後圈的 ⇒ 召回率只描述",
         "價格面板 ＝ rerun17 H2D（edc6f，資料尾 2026-09-24）；月營收、產業、財報、上傳時戳、exright ＝ 最新 origin/main"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


RT.log = log            # 共用函式的訊息寫進本件 run.log（不改檔，只換本行程內的輸出目標）


def segof(d, segs):
    s = str(pd.Timestamp(d).date())
    for nm, a, b in segs:
        if a <= s <= b:
            return nm
    return "段外"


def in_rng(d, rng_):
    s = str(pd.Timestamp(d).date())
    return rng_[1] <= s <= rng_[2]


def mnum_d(d):
    d = pd.Timestamp(d)
    return d.year * 12 + d.month - 1


def market_map(DN):
    m = {}
    for f in ("stocks.csv", "delisted.csv"):
        p = os.path.join(DN, "meta", f)
        if os.path.exists(p):
            x = pd.read_csv(p, dtype=str)
            for s, k in zip(x["stock_id"].astype(str).str.strip(), x["market"].astype(str)):
                m.setdefault(s, k)
    return m


# ═════════════ 財報（T4）═════════════
def load_cf(DN):
    """fs_xbrl ⇒ {sid: DataFrame(index=qk; ocf_ytd, capex_ytd, equity, tmpl)}（合併 cr 優先，同 bigrun_monthly.load_xbrl 去重式）。"""
    cols = ["period", "stock_id", "report", "industry_template", "total_equity", "operating_cash_flow_ytd", "capex_ytd"]
    L = []
    for f in sorted(glob.glob(os.path.join(DN, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        L.append(pd.read_csv(f, dtype={"stock_id": str}, usecols=lambda c: c in cols))
    X = pd.concat(L, ignore_index=True)
    X["_r"] = (X["report"] != "cr").astype(int)
    X = X.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
    X["qk"] = [LP.qkey(p[:4], p[5]) for p in X["period"]]
    for c in ("total_equity", "operating_cash_flow_ytd", "capex_ytd"):
        X[c] = pd.to_numeric(X[c], errors="coerce")
    info = {"列": int(len(X)), "季": f"{X['period'].min()}～{X['period'].max()}", "capex正值列": int((X["capex_ytd"] > 0).sum())}
    return {s: g.set_index("qk")[["operating_cash_flow_ytd", "capex_ytd", "total_equity", "industry_template"]].sort_index() for s, g in X.groupby("stock_id")}, info


def ttm(ytd, k):
    """近 4 季 ＝ researchLongPool.single(k−3..k) 加總；任一季缺 ⇒ nan。"""
    v = [LP.single(ytd, q) for q in range(k - 3, k + 1)]
    return float(sum(v)) if all(np.isfinite(x) for x in v) else np.nan


def deadline(qk):
    y, q = qk // 4, qk % 4 + 1
    return {1: pd.Timestamp(y, 5, 15), 2: pd.Timestamp(y, 8, 14), 3: pd.Timestamp(y, 11, 14), 4: pd.Timestamp(y + 1, 3, 31)}[q]


def latest_q(FP, sid, date):
    """上傳日 ＜ date 的最大季 qk；無 ⇒ −1。"""
    best = -1
    for d, q, _ in FP.get(sid, []):
        if d < date and q > best:
            best = q
    return best


def low1y(PX, i, p1):
    """距一年低點（T4）：c[p1] ÷ min(還原收盤, [p1 日期 − 1 年, p1]) − 1；不可算 ⇒ nan。⛔ 只用 ≤ p1 的價格、只回 ≤0.20 判斷用。"""
    vp = PX["VP"][i]; C = PX["C"]; CAL = PX["CAL"]
    k1 = int(np.searchsorted(vp, p1, "right")) - 1
    if k1 < 0 or vp[k1] != p1:
        return np.nan
    p0 = int(CAL.searchsorted(CAL[p1] - pd.DateOffset(years=1), side="left"))
    k0 = int(np.searchsorted(vp, p0, "right")) - 1
    if k0 < 0 or k0 >= k1:
        return np.nan
    a = int(vp[k0])
    if PX["CB"][i, p1] - PX["CB"][i, a] > 0:
        return np.nan
    w = vp[(vp >= p0) & (vp <= p1)]
    mn = float(np.nanmin(C[i, w]))
    return float(C[i, p1] / mn - 1.0) if mn > 0 else np.nan


def pct_of(vals, mask):
    out = np.full(len(vals), np.nan)
    ok = mask & np.isfinite(vals)
    if ok.any():
        out[ok] = RT.ranks(vals[ok])
    return out


# ═════════════ 事件（T2）═════════════
def make_events(cands, CEND, gate_fn):
    """cands：[(sid, i, A, mkey, extra)] ⇒ 過閘、36 月去重 ⇒ (kept, reasons)。mkey ＝ 月序（去重用）。"""
    reasons = Counter(); kept = []; last = {}
    for c in sorted(cands, key=lambda z: (z[0], z[3], z[2])):
        sid, i, A_, mk = c[0], c[1], c[2], c[3]
        if i < 0:
            reasons["非面板"] += 1; continue
        if A_ > CEND or A_ < 1:
            reasons["可用日超出日曆"] += 1; continue
        if not gate_fn(i, A_):
            reasons["閘外(判日A−1)"] += 1; continue
        lk = last.get(sid)
        if lk is not None and mk - lk < DEDUP_M:
            reasons["36個月內非第一次"] += 1; continue
        last[sid] = mk; kept.append(c)
    return kept, reasons


def walk_flags(PX, i, e, CEND, picks, ix):
    row = {}
    for H in (H2, HJ):
        x = e + H
        row[f"H{H}走得完"] = bool(x <= CEND)
    x = e + HJ
    if x <= CEND:
        row["H750窗內遇壞根"] = bool(PX["CB"][i, x] - PX["CB"][i, e] > 0)
        row["H750窗內遇下市"] = bool(PX["LASTV"][i] < x and CEND - PX["LASTV"][i] >= 5)
        cb = 0
        for s in picks:
            j = ix[s]
            cb += int(PX["CB"][j, x] - PX["CB"][j, e] > 0 or (PX["LASTV"][j] < x and CEND - PX["LASTV"][j] >= 5))
        row["H750對照遇壞根或下市"] = cb
    else:
        row["H750窗內遇壞根"] = None; row["H750窗內遇下市"] = None; row["H750對照遇壞根或下市"] = None
    return row


def seg_rows(E, sig, segs, CAL, extra_rng=None):
    rows = []
    allsegs = list(segs) + ([extra_rng] if extra_rng else [])
    for nm, x_, y_ in allsegs + [("段外", None, None)]:
        if nm == "段外":
            d = E[E["段"] == "段外"]
        elif extra_rng and nm == extra_rng[0]:
            d = E[E["未看過期間"]]
        else:
            d = E[E["段"] == nm]
        m = d[d["主格"]]; ok = d[d["進場"] == "保留"]
        ne = int(m["月"].nunique())
        rows.append({"訊號": sig, "段": nm, "可用日區間": (f"{x_}～{y_}" if x_ else "其餘"),
                     "事件(過閘去重)": len(d), "上市": int((d["市場"] == "twse").sum()), "上櫃": int((d["市場"] == "tpex").sum()),
                     "e可進場": len(ok), "配到": int(d["配到"].sum()),
                     "配對成功率(可進場中)": (float(ok["配到"].mean()) if len(ok) else np.nan),
                     "對照1檔": int((d["對照數"] == 1).sum()), "對照2檔": int((d["對照數"] == 2).sum()), "對照3檔": int((d["對照數"] == 3).sum()),
                     "候選數中位": (float(ok["候選數"].median()) if len(ok) else np.nan),
                     "H500走得完": int(d["H500走得完"].sum()), "H750走得完": int(d["H750走得完"].sum()),
                     "750走得完比例(配到中)": (float(d.loc[d["配到"], "H750走得完"].mean()) if d["配到"].any() else np.nan),
                     "主格事件": len(m), "主格月數=n_eff": ne, "n_eff≥24": ne >= NEFF_MIN,
                     "每月事件中位": (float(m.groupby("月").size().median()) if len(m) else np.nan),
                     "主格窗內遇壞根": int((m["H750窗內遇壞根"] == True).sum()), "主格窗內遇下市": int((m["H750窗內遇下市"] == True).sum()),  # noqa: E712
                     "主格對照遇壞根或下市(檔)": int(pd.to_numeric(m["H750對照遇壞根或下市"], errors="coerce").fillna(0).sum()),
                     "含下市股比例(主格)": (float(m["下市(資料尾前≥5日)"].mean()) if len(m) else np.nan),
                     "主格年數": int(m["年"].nunique())})
    return rows


# ═════════════ 月營收快取分段建（單一指令 ≤10 分鐘；結果與 rev_table 一次算相同：rev_metrics 逐期獨立）═════════════
RV_TAG = "trp"


def all_periods(MD):
    L, _ = BM.load_rev_pit(MD)
    L = L[L["period"].str.fullmatch(r"\d{4}-\d{2}")]
    return [p for p in sorted(L["period"].unique()) if p >= RT.P_FIRST]


def rv_chunk(MD, codes, procs, k, n):
    per = all_periods(MD)
    ch = [list(x) for x in np.array_split(np.array(per, dtype=object), n)][k]
    RT.rev_table(MD, codes, procs, periods=ch, tag=f"{RV_TAG}c{k}of{n}")


def rv_assemble(MD, codes, n):
    per = all_periods(MD)
    Zs = [pickle.load(open(os.path.join(RT.WORK, f"rv_{RV_TAG}c{k}of{n}_s{RT.SHIFT_Y}.pkl"), "rb")) for k in range(n)]
    if not all(Z["codes"] == list(codes) and Z["MD"] == MD for Z in Zs):
        raise SystemExit("⛔ 分段快取 codes／MD 不一致")
    got = [p for Z in Zs for p in Z["periods"]]
    if got != per:
        raise SystemExit("⛔ 分段期別接不起來")
    RV = pd.concat([Z["RV"] for Z in Zs]).sort_values(["sid", "period"]).reset_index(drop=True)
    diag = {**Zs[0]["diag"], "期別（呼叫）": f"{per[0]}～{per[-1]}（{len(per)} 期）", "分段": n}
    cp = os.path.join(RT.WORK, f"rv_{RV_TAG}_s{RT.SHIFT_Y}.pkl")
    pickle.dump({"RV": RV, "diag": diag, "codes": list(codes), "MD": MD, "periods": per}, open(cp, "wb"), protocol=5)
    log(f"[月營收] 分段 {n} 接成 {cp}（{len(RV)} 列）")


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sha", default=None)
    ap.add_argument("--rv-chunk", default=None, help="k/n：只建月營收快取第 k 段（共 n 段）後結束")
    ap.add_argument("--rv-assemble", type=int, default=None, help="n：把 n 段月營收快取接成一份後結束")
    a = ap.parse_args()
    if a.rv_chunk or a.rv_assemble:
        sha, DN, MD = RT.ensure_data(a.sha)
        codes = sorted(set(IMF.build_panel("早年", a.procs, log)["sids"]) | set(IMF.build_panel("主", a.procs, log)["sids"]))
        if a.rv_chunk:
            k, n = (int(x) for x in a.rv_chunk.split("/"))
            rv_chunk(MD, codes, a.procs, k, n)
        else:
            rv_assemble(MD, codes, a.rv_assemble)
        return
    t0 = time.time()
    out = os.path.join(TW, "dry") if a.limit else OUT
    os.makedirs(out, exist_ok=True); os.makedirs(TW, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    rul = [f for d in [IMF.MAILBOX] + sorted(glob.glob(os.path.join(IMF.MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if RUL in os.path.basename(f)]
    if not rul:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RUL}")
    log(f"[裁定] {os.path.basename(rul[0])}")
    sha, DN, MD = RT.ensure_data(a.sha); log(f"[資料] origin/main {sha}｜{DN}")
    PX = RT.prices(sha, DN, a.procs)
    CAL, SIDS, ix, NC = PX["CAL"], PX["SIDS"], PX["ix"], len(PX["CAL"])
    CEND = NC - 1
    SUB = np.ones(len(SIDS), bool)
    codes = SIDS
    if a.limit:
        rng0 = np.random.default_rng(SEED)
        codes = sorted(rng0.choice(SIDS, a.limit, replace=False).tolist())
        SUB = np.array([s in set(codes) for s in SIDS])
    G = PX["G"] & SUB[:, None]
    VALID = np.isfinite(PX["C"]) & SUB[:, None]
    MKT = market_map(DN)
    RV, rdiag = RT.rev_table(MD, codes, a.procs, tag=(RV_TAG if not a.limit else f"dry{a.limit}"))
    log(f"[月營收] {rdiag}")
    pit = IMF.load_pit(DN)
    FP, fsrc = RT.filing_pos(DN, CAL)
    XB, xinfo = load_cf(DN)
    log(f"[財報] 上傳時戳來源 {dict(fsrc)}｜fs_xbrl {xinfo}")
    periods = sorted(RV["period"].unique())
    APOS = RT.avail_pos(CAL, periods)
    RV["i"] = RV["sid"].map(ix).fillna(-1).astype(int)
    RV["A"] = RV["period"].map(APOS).astype(int)
    RV["甲"] = RT.jia(RV); RV["乙"] = RT.yi(RV)
    RV["S1"] = RV["甲"] & RV["乙"]
    RV["起點"] = RV["up"] & ~RV["up_prev"]
    RV["G1"] = RV["hi24"].to_numpy(float) == 1.0
    RV["上期不可判"] = ~np.isfinite(RV["hi24_prev"].to_numpy(float))
    RV["mk"] = [RT.mnum(p) for p in RV["period"]]

    def gate_ok(i, A_):
        return bool(i >= 0 and 1 <= A_ <= CEND and G[i, A_ - 1])

    def valid_ok(i, A_):
        return bool(i >= 0 and 1 <= A_ <= CEND and VALID[i, A_ - 1])
    RV["過閘"] = [gate_ok(i, A_) for i, A_ in zip(RV["i"], RV["A"])]

    # ── 等價自查 S1∧上期S1、上期 hi24 一致（T1、T10）
    RVs = RV.sort_values(["sid", "period"]).reset_index(drop=True)
    prev_ok = (RVs["sid"].shift(1) == RVs["sid"]) & (RVs["mk"].shift(1) == RVs["mk"] - 1)
    s1p = RVs["S1"].shift(1, fill_value=False).astype(bool) & prev_ok
    h24p = RVs["hi24"].shift(1)
    cons = prev_ok & np.isfinite(RVs["hi24_prev"]) & np.isfinite(h24p)
    EQV = {"S1列": int(RV["S1"].sum()), "S1∧上期S1(應為0)": int((RVs["S1"] & s1p).sum()),
           "上期hi24一致(上一列hi24＝本列hi24_prev)": f"{int((cons & (h24p == RVs['hi24_prev'])).sum())}／{int(cons.sum())}",
           "S1上期不可判(hi24_prev缺)": int((RV["S1"] & RV["上期不可判"]).sum()),
           "G1且甲列": int((RV["G1"] & RV["甲"]).sum()), "S1÷G1且甲(列)": float(RV["S1"].sum() / max(1, (RV["G1"] & RV["甲"]).sum()))}
    log(f"[等價 S1] {EQV}")

    # ── S1 事件（T2）
    def cands_of(mask):
        d = RV[mask]
        return [(s, int(i), int(A_), int(mk), P) for s, i, A_, mk, P in zip(d["sid"], d["i"], d["A"], d["mk"], d["period"])]
    s1_c = cands_of(RV["S1"])
    S1K, s1_rs = make_events(s1_c, CEND, gate_ok)
    S1K_ng, s1_rs_ng = make_events(s1_c, CEND, valid_ok)
    log(f"[S1] 訊號列 {len(s1_c)} ⇒ 過閘去重 {len(S1K)}｜剔除 {dict(s1_rs)}｜無閘版 {len(S1K_ng)}｜{dict(s1_rs_ng)}")

    # ── S1 分位（T3；＝ 營收轉強驗證 V5 原式）
    feat = {}
    s1_periods = sorted({c[4] for c in S1K})
    need_p = sorted(set(s1_periods))
    for P in need_p:
        A_ = APOS[P]
        p1 = A_ - 1
        U = np.flatnonzero(G[:, p1])
        if not len(U):
            continue
        p12 = int(CAL.searchsorted(CAL[p1] - pd.DateOffset(months=12), side="right")) - 1
        mc = PX["MC"][U, p1]; mc = np.where(np.isfinite(mc) & (mc > 0), mc, np.nan)
        r12 = np.array([RT.back_ret(PX, int(i), p1, p12) if p12 >= 0 else np.nan for i in U])
        pm = pct_of(mc, np.ones(len(U), bool)); pr = pct_of(r12, np.ones(len(U), bool))
        for k, i in enumerate(U):
            dec = int(math.ceil(pm[k] * 10)) if np.isfinite(pm[k]) else -1
            ter = int(math.ceil(pr[k] * 3)) if np.isfinite(pr[k]) else -1
            feat[(int(i), P)] = (dec, ter)
    log(f"[S1 分位] 期 {len(need_p)}｜股期 {len(feat)}｜{time.time() - t0:.0f}s")
    eflag_memo = {}

    def eflag(i, A_):
        k = (i, A_)
        if k not in eflag_memo:
            eflag_memo[k] = IMF.entry_flag(PX, i, A_, A_ + 1) if A_ + 1 <= CEND else "e超出資料尾"
        return eflag_memo[k]

    def ind_at(sid, A_):
        v, s = pit.at(sid, CAL[A_])
        return (v or ""), s
    pool = defaultdict(list)
    NON = RV[(~RV["S1"]) & RV["過閘"] & (RV["i"] >= 0) & RV["period"].isin(set(need_p))]
    for r in NON.itertuples(index=False):
        f = feat.get((r.i, r.period))
        if f is None or f[0] < 0 or f[1] < 0:
            continue
        ind, _ = ind_at(r.sid, r.A)
        if not ind or eflag(r.i, r.A) != "保留":
            continue
        pool[(r.period, ind, f[0], f[1])].append(r.sid)
    log(f"[S1 配對池] 格 {len(pool)}｜{time.time() - t0:.0f}s")

    # ── V 判日與特徵（T4）
    qks = list(range(LP.qkey(*Q_FIRST), LP.qkey(2026, 2) + 1))
    VJ = []                     # (qk, A)
    for qk in qks:
        A_ = int(CAL.searchsorted(deadline(qk), side="right"))
        if 1 <= A_ <= CEND:
            VJ.append((qk, A_))
    VS = {}                     # (i, A) -> dict
    COV = []
    for qk, A_ in VJ:
        p1 = A_ - 1
        U0 = np.flatnonzero(VALID[:, p1]); Ug = set(np.flatnonzero(G[:, p1]).tolist())
        n = len(U0)
        cf = np.full(n, np.nan); bm = np.full(n, np.nan); mcv = np.full(n, np.nan); lw = np.full(n, np.nan)
        src = [""] * n; stale = np.full(n, -1); ocfo = np.full(n, np.nan); tmpl = [""] * n
        cnt = Counter()
        for k, i in enumerate(U0):
            sid = SIDS[i]
            mc = PX["MC"][i, p1]
            if np.isfinite(mc) and mc > 0:
                mcv[k] = mc
            lw[k] = low1y(PX, int(i), p1)
            kq = latest_q(FP, sid, CAL[A_])
            if kq < 0:
                cnt["無上傳時戳"] += 1; continue
            st = qk - kq; stale[k] = st
            if st >= 2:
                cnt["落後≥2季"] += 1; continue
            df = XB.get(sid)
            if df is None or kq not in df.index:
                cnt["fs_xbrl無該季"] += 1; continue
            tmpl[k] = str(df.loc[kq, "industry_template"])
            o = ttm(df["operating_cash_flow_ytd"], kq); c_ = ttm(df["capex_ytd"], kq); eq = df.loc[kq, "total_equity"]
            if np.isfinite(o) and np.isfinite(mcv[k]):
                ocfo[k] = o / mcv[k]
                if np.isfinite(c_):
                    cf[k] = (o + c_) / mcv[k]; src[k] = "FCF"
                else:
                    cf[k] = o / mcv[k]; src[k] = "OCF代"
            if np.isfinite(eq) and np.isfinite(mcv[k]):
                bm[k] = eq / mcv[k]
        for tag, umask in (("g", np.array([int(i) in Ug for i in U0])), ("ng", np.ones(n, bool))):
            pc = pct_of(cf, umask); pb = pct_of(bm, umask); pmv = pct_of(mcv, umask); po = pct_of(ocfo, umask)
            for k, i in enumerate(U0):
                if not umask[k]:
                    continue
                jd = bool(np.isfinite(pc[k]) and np.isfinite(pb[k]) and np.isfinite(pmv[k]) and np.isfinite(lw[k]))
                c1 = bool(np.isfinite(pc[k]) and pc[k] > 0.7); c2 = bool(np.isfinite(pb[k]) and pb[k] > 0.7)
                c3 = bool(np.isfinite(pmv[k]) and pmv[k] <= 0.5); c4 = bool(np.isfinite(lw[k]) and lw[k] <= 0.20)
                jo = bool(np.isfinite(po[k]) and np.isfinite(pb[k]) and np.isfinite(pmv[k]) and np.isfinite(lw[k]))
                d = VS.setdefault((int(i), A_), {"qk": qk, "kq": int(qk - stale[k]) if stale[k] >= 0 else -1, "src": src[k], "tmpl": tmpl[k]})
                d[f"可判_{tag}"] = jd; d[f"V_{tag}"] = bool(jd and c1 and c2 and c3 and c4)
                d[f"c_{tag}"] = (c1, c2, c3, c4)
                d[f"Vocf_{tag}"] = bool(jo and po[k] > 0.7 and c2 and c3 and c4)
                if tag == "g":
                    d["dec"] = int(math.ceil(pmv[k] * 10)) if np.isfinite(pmv[k]) else -1
                    d["pc"] = float(pc[k]); d["pb"] = float(pb[k]); d["pm"] = float(pmv[k])
        gm = np.array([int(i) in Ug for i in U0])
        ng_ = int(gm.sum())

        def r_(m):
            return float(m[gm].mean()) if ng_ else np.nan
        COV.append({"財報季(目標)": LP.qlabel(qk), "判日A": str(CAL[A_].date()), "面板有效股": n, "過閘股": ng_,
                    "有上傳時戳且落後≤1季(過閘)": r_((stale >= 0) & (stale <= 1)), "落後1季(過閘)": r_(stale == 1),
                    "營業現金流近4季可算(過閘)": r_(np.isfinite(ocfo)), "capex近4季可算⇒FCF(過閘)": r_(np.array([s == "FCF" for s in src])),
                    "OCF代(過閘)": r_(np.array([s == "OCF代" for s in src])), "淨值可算(過閘)": r_(np.isfinite(bm)), "市值可算(過閘)": r_(np.isfinite(mcv)),
                    "距一年低點可算(過閘)": r_(np.isfinite(lw)),
                    "V可判(四欄,過閘)": float(np.mean([VS[(int(i), A_)].get("可判_g", False) for k, i in enumerate(U0) if gm[k]])) if ng_ else np.nan,
                    "V為真(過閘)": int(sum(VS[(int(i), A_)].get("V_g", False) for k, i in enumerate(U0) if gm[k])),
                    "V為真(無閘)": int(sum(VS[(int(i), A_)].get("V_ng", False) for i in U0)),
                    **{f"排除:{k}": v for k, v in cnt.items()}})
    COV = pd.DataFrame(COV)
    log(f"[V 判日] {len(VJ)}（{COV['判日A'].iloc[0]}～{COV['判日A'].iloc[-1]}）｜股日 {len(VS)}｜{time.time() - t0:.0f}s")

    # ── V 事件（T2）
    v_c = [(SIDS[i], i, A_, mnum_d(CAL[A_]), d["qk"]) for (i, A_), d in VS.items() if d.get("V_g")]
    VK, v_rs = make_events(v_c, CEND, gate_ok)
    v_c_ng = [(SIDS[i], i, A_, mnum_d(CAL[A_]), d["qk"]) for (i, A_), d in VS.items() if d.get("V_ng")]
    VK_ng, v_rs_ng = make_events(v_c_ng, CEND, valid_ok)
    v_c_o = [(SIDS[i], i, A_, mnum_d(CAL[A_]), d["qk"]) for (i, A_), d in VS.items() if d.get("Vocf_g")]
    VK_o, _ = make_events(v_c_o, CEND, gate_ok)
    log(f"[V] 狀態列 {len(v_c)} ⇒ 過閘去重 {len(VK)}｜剔除 {dict(v_rs)}｜無閘版 {len(VK_ng)}｜全用OCF版 {len(VK_o)}")
    vpool = defaultdict(list)
    for (i, A_), d in VS.items():
        if G[i, A_ - 1] and d.get("可判_g") and not d.get("V_g") and d.get("dec", -1) > 0 and eflag(i, A_) == "保留":
            vpool[(A_, d["dec"])].append(SIDS[i])

    # V 判日查找（S1 且 V 用）
    VJA = np.array([A_ for _, A_ in VJ])

    def v_at(i, A_):
        k = int(np.searchsorted(VJA, A_, "right")) - 1
        if k < 0:
            return None
        return VS.get((i, int(VJA[k])))

    # S1 狀態（過閘與否不論）時間索引：sid -> [A...]
    s1_state = defaultdict(list)
    for s, A_ in zip(RV.loc[RV["S1"], "sid"], RV.loc[RV["S1"], "A"]):
        if 0 <= A_ <= CEND:
            s1_state[s].append(int(A_))

    # ── S1 逐事件
    rng = np.random.default_rng(SEED)
    S1K = sorted(S1K, key=lambda z: (z[2], z[0]))
    RVi = RV.set_index(["sid", "period"])
    rows = []
    for sid, i, A_, mk, P in S1K:
        e = A_ + 1
        fl = eflag(i, A_)
        ind, isrc = ind_at(sid, A_)
        f = feat.get((i, P), (-1, -1))
        cand = sorted(pool.get((P, ind, f[0], f[1]), [])) if (ind and f[0] >= 0 and f[1] >= 0) else []
        pick = (sorted(rng.choice(cand, 3, replace=False).tolist()) if len(cand) >= 3 else cand) if (fl == "保留" and cand) else []
        why = ("e不可進場:" + fl) if fl != "保留" else ("無產業" if not ind else ("市值不可算" if f[0] < 0 else ("前12月不可算" if f[1] < 0 else ("" if cand else "同格無候選"))))
        rr = RVi.loc[(sid, P)]
        va = v_at(i, A_)
        row = {"sid": sid, "期別": P, "A": str(CAL[A_].date()), "e": (str(CAL[e].date()) if e <= CEND else ""), "段": segof(CAL[A_], S1_SEGS),
               "未看過期間": in_rng(CAL[A_], S1_DESC), "年": CAL[A_].year, "月": f"{CAL[A_].year}-{CAL[A_].month:02d}", "市場": MKT.get(sid, ""),
               "上期不可判": bool(rr["上期不可判"]), "產業": ind, "產業來源": isrc, "市值十分位": f[0], "前12月三分位(配對特徵)": f[1],
               "進場": fl, "候選數": len(cand), "對照": " ".join(pick), "對照數": len(pick), "配到": bool(pick), "配不到原因": why,
               "下市(資料尾前≥5日)": bool(PX["LASTV"][i] < CEND - 5),
               "當季V可判": (bool(va.get("可判_g")) if va else None), "當季V": (bool(va.get("V_g")) if va else None)}
        row.update(walk_flags(PX, i, e, CEND, pick, ix))
        row["主格"] = bool(row["配到"] and row["H750走得完"])
        rows.append(row)
    E1 = pd.DataFrame(rows)
    E1["同產業同月S1事件數"] = E1.groupby(["產業", "月"])["sid"].transform("size")
    log(f"[S1 配對] 事件 {len(E1)}｜可進場 {int((E1['進場'] == '保留').sum())}｜配到 {int(E1['配到'].sum())}｜主格 {int(E1['主格'].sum())}｜{time.time() - t0:.0f}s")

    # ── V 逐事件
    rngv = np.random.default_rng(SEED)
    VK = sorted(VK, key=lambda z: (z[2], z[0]))
    rows = []
    for sid, i, A_, mk, qk in VK:
        e = A_ + 1
        d = VS[(i, A_)]
        fl = eflag(i, A_)
        cand = sorted(vpool.get((A_, d["dec"]), [])) if d.get("dec", -1) > 0 else []
        pick = (sorted(rngv.choice(cand, 3, replace=False).tolist()) if len(cand) >= 3 else cand) if (fl == "保留" and cand) else []
        why = ("e不可進場:" + fl) if fl != "保留" else ("市值不可算" if d.get("dec", -1) <= 0 else ("" if cand else "同格無候選"))
        ind, isrc = ind_at(sid, A_)
        s1w = [x for x in s1_state.get(sid, []) if CAL[x] > CAL[A_] - pd.DateOffset(months=12) and x <= A_]
        row = {"sid": sid, "財報季(目標)": LP.qlabel(qk), "用季": (LP.qlabel(d["kq"]) if d["kq"] >= 0 else ""), "落後季數": (qk - d["kq"] if d["kq"] >= 0 else None),
               "A": str(CAL[A_].date()), "e": (str(CAL[e].date()) if e <= CEND else ""), "段": segof(CAL[A_], V_SEGS),
               "年": CAL[A_].year, "月": f"{CAL[A_].year}-{CAL[A_].month:02d}", "市場": MKT.get(sid, ""), "產業": ind, "產業來源": isrc,
               "現金流口徑": d["src"], "財報範本": d["tmpl"], "現金流市值分位": d["pc"], "BM分位": d["pb"], "市值分位": d["pm"], "市值十分位": d["dec"],
               "全用OCF版也為V": bool(d.get("Vocf_g")),
               "進場": fl, "候選數": len(cand), "對照": " ".join(pick), "對照數": len(pick), "配到": bool(pick), "配不到原因": why,
               "下市(資料尾前≥5日)": bool(PX["LASTV"][i] < CEND - 5), "前12月內有S1狀態": bool(s1w)}
        row.update(walk_flags(PX, i, e, CEND, pick, ix))
        row["主格"] = bool(row["配到"] and row["H750走得完"])
        rows.append(row)
    E2 = pd.DataFrame(rows)
    log(f"[V 配對] 事件 {len(E2)}｜可進場 {int((E2['進場'] == '保留').sum())}｜配到 {int(E2['配到'].sum())}｜主格 {int(E2['主格'].sum())}｜{time.time() - t0:.0f}s")

    # ── 段表
    FR = pd.DataFrame(seg_rows(E1, "S1", S1_SEGS, CAL, S1_DESC) + seg_rows(E2, "V", V_SEGS, CAL))
    # 無閘版件數
    NG = []
    for sig, K, segs in (("S1", S1K_ng, S1_SEGS), ("V", VK_ng, V_SEGS)):
        c = Counter(segof(CAL[z[2]], segs) for z in K)
        for nm, _, _ in segs:
            NG.append({"訊號": sig, "段": nm, "無閘事件(去重)": c.get(nm, 0),
                       "無閘且750走得完": sum(1 for z in K if segof(CAL[z[2]], segs) == nm and z[2] + 1 + HJ <= CEND)})
        if sig == "S1":
            NG.append({"訊號": sig, "段": S1_DESC[0], "無閘事件(去重)": sum(1 for z in K if in_rng(CAL[z[2]], S1_DESC)),
                       "無閘且750走得完": sum(1 for z in K if in_rng(CAL[z[2]], S1_DESC) and z[2] + 1 + HJ <= CEND)})
    NG = pd.DataFrame(NG)
    FR = FR.merge(NG, on=["訊號", "段"], how="left")

    # ── 描述訊號（T9）
    DS = []
    for lab, mask in (("甲單獨", RV["甲"] & ~RV["乙"]), ("乙單獨", RV["乙"] & ~RV["甲"]), ("轉強起點(甲或乙)", RV["起點"]),
                      ("G1(24月新高狀態)", RV["G1"]), ("G1且甲", RV["G1"] & RV["甲"]), ("S1", RV["S1"])):
        K, rs = make_events(cands_of(mask), CEND, gate_ok)
        for nm, x_, y_ in S1_SEGS + [S1_DESC]:
            kk = [z for z in K if x_ <= str(CAL[z[2]].date()) <= y_]
            ent = [z for z in kk if eflag(z[1], z[2]) == "保留"]
            w = [z for z in ent if z[2] + 1 + HJ <= CEND]
            DS.append({"描述訊號": lab, "段": nm, "事件(過閘36月去重)": len(kk), "e可進場": len(ent), "750走得完(可進場中)": len(w),
                       "月數(750走得完)": len({f"{CAL[z[2]].year}-{CAL[z[2]].month:02d}" for z in w})})
        if lab == "G1且甲":
            GJ = {(z[0], z[4]) for z in K}
    s1v = E1[E1["當季V可判"] == True]  # noqa: E712
    for nm in ("探索", "確認"):
        d1 = E1[(E1["段"] == nm) & (E1["當季V"] == True)]  # noqa: E712
        DS.append({"描述訊號": "S1且V(S1事件中當季V為真)", "段": f"S1 {nm}", "事件(過閘36月去重)": len(d1), "e可進場": int((d1["進場"] == "保留").sum()),
                   "750走得完(可進場中)": int(((d1["進場"] == "保留") & d1["H750走得完"]).sum()), "月數(750走得完)": int(d1.loc[d1["H750走得完"], "月"].nunique())})
    DS = pd.DataFrame(DS)

    # ── 等價／退化（T10）
    EQ = []
    s1ev = {(r.sid, r.期別) for r in E1.itertuples(index=False)}
    EQ.append({"項": "S1∧上期S1（依構造應為 0）", "值": EQV["S1∧上期S1(應為0)"], "註": "「上期不成立」與乙的「上期沒創」重複 ⇒ 不改變事件"})
    EQ.append({"項": "上期 hi24 一致（上一列 hi24 ＝ 本列 hi24_prev）", "值": EQV["上期hi24一致(上一列hi24＝本列hi24_prev)"], "註": "rev_metrics 內部一致"})
    EQ.append({"項": "S1 列 ÷ G1且甲 列", "值": round(EQV["S1÷G1且甲(列)"], 4), "註": "S1 ⊂ G1且甲；只差『上期沒創』"})
    EQ.append({"項": "S1 事件 ∩ G1且甲 事件（36 月去重，代號＋期別）", "值": f"{len(s1ev & GJ)}／S1 {len(s1ev)}／G1且甲 {len(GJ)}",
               "註": "兩者事件同期別同檔的比例"})
    if os.path.exists(RT_EV):
        rt = pd.read_csv(RT_EV, dtype={"sid": str, "期別": str}, usecols=["sid", "期別", "甲", "乙"])
        rtk = {(s, p) for s, p, j, y in zip(rt["sid"], rt["期別"], rt["甲"], rt["乙"]) if bool(j) and bool(y)}
        EQ.append({"項": "S1 事件 ∩ 營收轉強驗證頻率表『甲且乙』事件（12 月去重）", "值": f"{len(s1ev & rtk)}／S1 {len(s1ev)}／轉強甲且乙 {len(rtk)}",
                   "註": "36 vs 12 月去重、起點定義不同（轉強起點要求上期 up 為假）"})
    for nm in ("探索", "確認", "段外"):
        d = E2[E2["段"] == nm]
        if len(d):
            EQ.append({"項": f"V {nm}：現金流口徑 FCF／OCF代", "值": f"{int((d['現金流口徑'] == 'FCF').sum())}／{int((d['現金流口徑'] == 'OCF代').sum())}", "註": "登錄：沒有 capex 就用營業現金流並標"})
            EQ.append({"項": f"V {nm}：全用 OCF 也為 V 的比例", "值": round(float(d["全用OCF版也為V"].mean()), 4), "註": "FCF 優先 vs 全 OCF"})
            EQ.append({"項": f"V {nm}：財報範本", "值": json.dumps(d["財報範本"].value_counts().to_dict(), ensure_ascii=False), "註": "金融業（basi/fh/ins/bd/mim）的營業現金流口徑不同，照登錄不排除"})
            EQ.append({"項": f"V {nm}：前 12 月內有 S1 狀態（V 與 S1 重疊）", "值": round(float(d["前12月內有S1狀態"].mean()), 4), "註": "登錄 §七 必報"})
    vko = {(z[0], z[2]) for z in VK_o}; vkk = {(z[0], z[2]) for z in VK}
    EQ.append({"項": "V 事件（FCF 優先）∩ V 事件（全用 OCF）", "值": f"{len(vkk & vko)}／{len(vkk)}／{len(vko)}", "註": "去重後事件集合"})
    for nm in ("探索", "確認"):
        d = E1[(E1["段"] == nm) & (E1["當季V可判"] == True)]  # noqa: E712
        EQ.append({"項": f"S1 {nm}：當季 V 可判中 V 為真", "值": f"{int((d['當季V'] == True).sum())}／{len(d)}", "註": "S1 與 V 重疊"})  # noqa: E712
    # V 四條件通過率（過閘、可判）
    cc = np.array([d["c_g"] for d in VS.values() if d.get("可判_g")], bool)
    if len(cc):
        nmz = ["現金流市值前30%", "淨值市值前30%", "市值後50%", "距一年低點≤20%"]
        EQ.append({"項": "V 四條件各自通過率（過閘且可判股日）", "值": json.dumps({nmz[k]: round(float(cc[:, k].mean()), 4) for k in range(4)}, ensure_ascii=False),
                   "註": f"股日 {len(cc)}；四條件全過 {round(float(cc.all(axis=1).mean()), 4)}"})
        pair = {f"{nmz[a_]}∧{nmz[b_]}": round(float((cc[:, a_] & cc[:, b_]).mean()), 4) for a_ in range(4) for b_ in range(a_ + 1, 4)}
        EQ.append({"項": "V 兩兩聯合通過率", "值": json.dumps(pair, ensure_ascii=False), "註": "看是否某條件吃掉其他條件（退化）"})
    for sig, Ex in (("S1", E1), ("V", E2)):
        ok = Ex[Ex["進場"] == "保留"]
        EQ.append({"項": f"{sig} 候選數分佈（可進場事件）", "值": json.dumps(RT.qd(ok["候選數"].astype(float)), ensure_ascii=False), "註": "對照池大小"})
    EQ = pd.DataFrame(EQ)

    # ── 召回率分母（T8）
    X3 = pd.read_csv(X3_CSV, dtype={"代號": str}, usecols=["代號", "市場", "起點", "起點左截斷"])
    X3["起點"] = pd.to_datetime(X3["起點"])
    rvg = defaultdict(list)
    for s, A_, ac, h, gok in zip(RV["sid"], RV["A"], RV["accel"], RV["hi24"], RV["過閘"]):
        if 1 <= A_ <= CEND:
            rvg[s].append((CAL[A_], bool(np.isfinite(ac) and np.isfinite(h)), bool(np.isfinite(ac) or np.isfinite(h)), bool(gok)))
    vjd = defaultdict(list)
    for (i, A_), d in VS.items():
        vjd[SIDS[i]].append((CAL[A_], bool(d.get("可判_g")), bool(d.get("可判_ng"))))
    RC = []
    for s, st, lt, mk_ in zip(X3["代號"], X3["起點"], X3["起點左截斷"], X3["市場"]):
        if a.limit and s not in set(codes):
            continue
        lo = st - pd.DateOffset(months=12)
        r = [x for x in rvg.get(s, []) if lo <= x[0] <= st]
        v = [x for x in vjd.get(s, []) if lo <= x[0] <= st]
        RC.append({"代號": s, "市場": mk_, "起點年": st.year, "起點": st, "左截斷": bool(lt), "在面板": s in ix,
                   "S1可判(無閘)": any(x[1] for x in r), "S1可判(過閘)": any(x[1] and x[3] for x in r),
                   "轉強可判(無閘)": any(x[2] for x in r), "轉強可判(過閘)": any(x[2] and x[3] for x in r),
                   "V可判(無閘)": any(x[2] for x in v), "V可判(過閘)": any(x[1] for x in v)})
    RC = pd.DataFrame(RC)
    RD = []
    for lab, d in (("全部", RC), ("起點 2006 前", RC[RC["起點年"] < 2006]), ("起點 2006～2014", RC[(RC["起點年"] >= 2006) & (RC["起點年"] <= 2014)]),
                   ("起點 2015 起", RC[RC["起點年"] >= 2015]), ("起點 2014-04 起(V 現金流可算)", RC[RC["起點"] >= pd.Timestamp("2014-04-01")])):
        RD.append({"3倍段範圍": lab, "段數": len(d), "左截斷": int(d["左截斷"].sum()) if len(d) else 0, "在面板": int(d["在面板"].sum()) if len(d) else 0,
                   **{c: int(d[c].sum()) if len(d) else 0 for c in ["S1可判(無閘)", "S1可判(過閘)", "轉強可判(無閘)", "轉強可判(過閘)", "V可判(無閘)", "V可判(過閘)"]}})
    RD = pd.DataFrame(RD)

    # ── 分年
    YR = []
    for sig, Ex in (("S1", E1), ("V", E2)):
        for y, d in Ex.groupby("年"):
            YR.append({"訊號": sig, "年(可用日)": int(y), "事件": len(d), "e可進場": int((d["進場"] == "保留").sum()), "配到": int(d["配到"].sum()),
                       "主格": int(d["主格"].sum()), "上市": int((d["市場"] == "twse").sum()), "上櫃": int((d["市場"] == "tpex").sum()),
                       "含下市股比例": float(d["下市(資料尾前≥5日)"].mean())})
    YR = pd.DataFrame(YR)
    # 產業同動（S1 主格）
    IND = []
    for nm in ("探索", "確認"):
        m = E1[(E1["段"] == nm) & E1["主格"]]
        IND.append({"段": nm, "主格": len(m), "同產業同月≥3檔(事件)": int((m["同產業同月S1事件數"] >= 3).sum()),
                    "其月數": int(m.loc[m["同產業同月S1事件數"] >= 3, "月"].nunique())})

    # ── 輸出
    E1.to_csv(os.path.join(out, "events_S1.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    E2.to_csv(os.path.join(out, "events_V.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    FR.to_csv(os.path.join(out, "freq_段.csv"), index=False, encoding="utf-8-sig")
    COV.to_csv(os.path.join(out, "v_coverage.csv"), index=False, encoding="utf-8-sig")
    COV["年"] = COV["判日A"].str[:4]
    COVY = COV.groupby("年").agg({c: "mean" for c in COV.columns if "(過閘)" in c and "V為真" not in c}).reset_index()
    COVY.to_csv(os.path.join(out, "v_coverage_年.csv"), index=False, encoding="utf-8-sig")
    RD.to_csv(os.path.join(out, "recall_denom.csv"), index=False, encoding="utf-8-sig")
    EQ.to_csv(os.path.join(out, "equiv.csv"), index=False, encoding="utf-8-sig")
    DS.to_csv(os.path.join(out, "desc_signals.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    J = {"性質": "找下一個大漲股 3 年 3 倍命中率 seq1 頻率表（⛔ 未算任何報酬、倍數、命中）", "登錄": f"台股策略線 seq1 sha {REG_SHA}（{reg}）",
         "裁定": os.path.basename(rul[0]), "origin/main": sha, "價格面板": {"主": PX["main_data"], "早年": PX["early_data"]}, "合併日曆": [str(CAL[0].date()), str(CAL[-1].date()), NC],
         "接縫": PX["seam"], "exright": PX["info"], "月營收": rdiag, "上傳時戳來源": dict(fsrc), "fs_xbrl": xinfo, "乾跑": bool(a.limit), "乾跑股數": a.limit,
         "S1": {"訊號列": len(s1_c), "剔除": dict(s1_rs), "過閘去重事件": len(E1), "無閘版事件": len(S1K_ng), "無閘剔除": dict(s1_rs_ng)},
         "V": {"判日數": len(VJ), "判日": [str(CAL[A_].date()) for _, A_ in VJ], "狀態列(過閘)": len(v_c), "剔除": dict(v_rs), "過閘去重事件": len(E2),
               "無閘版事件": len(VK_ng), "全用OCF版事件": len(VK_o)},
         "等價S1": EQV, "段": FR.to_dict("records"), "產業同動": IND, "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
