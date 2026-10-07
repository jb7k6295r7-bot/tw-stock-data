# -*- coding: utf-8 -*-
"""USREG-A4（A4-1～7、A4-9～13；A4-8 撤回作廢、A4-14 作廢）——照登錄算報酬（裁定 seq318 發號、seq319 疑點裁示）。共用底座＋階段入口。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA4 --stage world  [--procs 2]
    ...                                                                   --stage panel
    ...                                                                   --stage items [--only A4-1,A4-4] [--seeds 200] [--reps 1000]
    ...                                                                   --stage ml | surge | report
    獨立查核：python -m backtest.researchUSA4_check     頁面：python -m backtest.researchUSA4_page

判準：美股策略線 登錄全文 USREG-A3A4 seq1（sha 0dc16d3267725d7c，本體）＋seq2（sha bc0927fed5996fd4，去重、四件主臂改條件出場）；
      裁定 seq318（發號 29 件；A4-14 作廢；A4-2 依墨菲 seq4；A4-3 營收創紀錄 20 日判、60 日描述；條件出場必報持有天數分佈與窗尾仍持有、看離頂多近；
      飆股用美股母體網格中位；結果句標「想法來自台股」；A4-6 並引台股兩件不合格）；
      裁定 seq319（Q1 判定 ＝ 探索挑、確認判＋seq316 兩母體；Q6 A4-7 x＝每季前 10%；Q7 A4-9 兩條「或」都留、名稱「年線戰法基本面季版」；
      Q8 A4-5／A4-6 類股 ＝ GICS industry group；Q9 A4-11 只跑 numpy 版 168560；Q10 A4-2 墨菲三套起點 2018-03；Q14 季版附註；
      Q15 A4-8 撤回、只跑 A4-13；Q16 A4-10 探索段挑特徵、挑定後停、⛔ 不開驗證段）；seq316（只 S&P 400 與合併兩者都過才合格）。
開跑前清單（⛔ 照它、不改；只有 P9 依 seq319 Q8 改寫）：backtest/researchUSA34_prep.py、backtest/resultsUSA34/prep/PREP_REPORT.md（補讀法 P1～P20）。
各件引用的台股原登錄（檔名＋sha）＝ resultsUSA34/prep/清單_29件.csv；本件各 item 的 docstring 逐條寫原登錄條號。

⛔⛔ 私有資料：us-stock-data 是私有 repo ⇒ resultsUSA34/A4/ 只放彙總（年化、回落、比值、件數、比例、判語、sha）；
   逐日價格、財報原值、逐筆成交、權益曲線、逐股月面板一律寫 ~/us_work/a4/（repo 外）並列 sha。

資料：~/usdata/881c86a（git archive 881c86a9a756，唯讀；＝ A2／A3／prep 同一份）；聯集轉接層 researchUSA2_data（A2.install()）；
     價格與硬斷點 researchUSM.prep（轉接層 hard_break）；量 researchUSX.volume_aligned；季財報 fundamentals/（B1）、股數 shares_outstanding（B2）、
     GICS sector_pit（B3，Wikipedia 歷史版、非官方）、名冊 membership／membership_sp400 changes；價格面板的逐月價格欄沿用 prep 的 ~/us_work/a34/px.pkl（MONTH 列）。
既有程式（只 import、⛔ 一行未改）：researchUSW1b（window_metrics、label）、research11（simulate_mtm、cl_stats）、tradability（delist_status）、
     researchM（summ、verdict）、researchUSA34_prep（q_last、yoy_of、fy_series、inst_at、shares_at）、researchUSA2_data、researchUSM、researchUSX。

═══ A4 共同讀法（執行者寫死於 2026-10-07 11:54（台北）；寫死前 ⛔ 沒看任何 A4 報酬）═══
 G1 窗、段（＝ P1）：判定窗 2016-01-04～2026-09-30；探索 2016-01-04～2021-12-31、確認 2022-01-03～2026-09-30（A4-13 原文同刀）。
    裁定 seq319 Q1：美股沒有早年段 ⇒ 判定 ＝ 探索段挑、確認段判；原文「兩段取較嚴」⇒ 只看確認段；結果句標「缺早年段」（原登錄有早年段者）。
    例外照 P1／seq319：A4-2 起點 2018-03（探索 2018-03～2021-12）；A4-11 訓練 ～2017-12、驗證 2018、探索 2019～2021、確認 2022～2026-09；
    A4-10 只用 2021-01～2026-09、探索 2021～2023（⛔ 不開 2024～2026-09 驗證段）；A4-3 X1、X2、X3 依 P12 全窗判（單一格、無挑選）。
 G2 挑格在【合併】欄的探索段做（同一套規則一次挑出、兩欄同一格判；＝ A3 C2 同讀法）；⛔ 不在只 S&P 400 欄另挑。
 G3 三欄（＝ P2）：組合層 ＝ 三組各自的組合回測（候選／排名母體 ＝ 換股日或訊號日當天在該欄指數者）；事件層 ＝ 事件日當天歸屬。
    換股簿型（選股類）：持股在下一個換股日若已不在該欄母體 ⇒ 不在排名名單 ⇒ 視為「不再符合」賣出（同台股換股簿：不在 eligible 就落選）；
    槽位型（事件／條件出場）：持有中移出母體照抱（seq214 R4 E0）。
 G4 標籤（seq316＋seq319）：合格 ＝ 只 S&P 400 與合併都過；只有合併過 ⇒「事後擴母體」（最多暫定、只進前瞻紀錄）；合併沒過 ⇒ 不合格；
    組合層另列照 USREG-A2 W1b W7；依構造不能判 ⇒ 不可判定。只 S&P 500 ＝ 描述、⛔ 不判。
    事件層（A4-3 X3）：「測得出（＋）」＝ 合併與只 S&P 400 的 CI 都整段 ＞ 0（researchM.verdict 出口②／③）；只合併 ⇒ 事後擴母體；其餘測不出。
 G5 組合層判準：^SP500TR 同窗（同段）：年化 ＞ 基準年化 且 年化÷|回落| ≥ 基準比值 ⇒ 合格；只前者 ⇒ 另列（researchUSW1b.label；ANN 252）。
    抽籤型（槽位）取 200 顆種子的年化中位、回落中位（seq242；種子 102000＋r）；換股簿型照原登錄是決定性排名 ⇒ 單一條權益。
 G6 成本 0.05% 來回（seq242；敏感度 0.02、0.10% 只在判定格描述）；換股簿：賣出時扣「進場金額 × 0.05%」（台股 sim_book 同式）。
 G7 主臂（seq308、seq318）：選股類 ＝ 「不再符合才換」：換股日照原頻率檢查，仍入選者續抱、落選者賣（台股「續抱仍入選」同一條）；
    條件出場臂 ⛔ 不設最長天數；窗（段）尾仍持有 ⇒ 尾日收盤結算、件數必報；持有天數分佈（平均、中位、p10、p90、最長）必報；
    「離頂多近」＝ 每筆 出場價 ÷ 持有期間（進場日～出場日）最高收盤 − 1 的中位（＝ A3 C6）；⛔ 不拿抱幾天當評價。
    固定 {20, 60, 120, 240} 日只描述：換股簿型 ＝ 同一份排名、新進場者抱滿 H 個交易日收盤賣、空槽到下一個換股日補（不因落選而賣）；
    槽位型 ＝ xpos ＝ entry＋H−1（收盤出；超過窗尾 ⇒ 窗尾結算，同 W1b W4）。原文寫死天數者照原文當主格（登錄 §〇；A4-7、A4-13）。
 G8 換股日與資料時點：月頻換股日 e ＝ 每月第一個交易日（＝ prep MSTART；W1b 量測日同一組）；價格特徵只用 e−1 以前（px.pkl MONTH 列 kb ＝ e 前最後一根），
    季財報可用日 av ＝ first_filed 的次一交易日、av ≤ e 才可用（prep load_fund 同式）；e 開盤成交 ⇒ 等於「訊號日 e−1 收盤 ⇒ T＋1 開盤」。
    季 ＝ 1、4、7、10 月的 e；半年 ＝ 1、7 月；年 ＝ 1 月。
 G9 季財報（P6、P7 照用）＋ 代號重用：cik_map（S&P 500）與 cik_map_sp400 有 seg_from／seg_to 的代號（AZPN COHR CR CZR HR RBC RCM VAL 等）
    依量測日挑該段 CIK（＋前身表 verdict＝ok 對到該 CIK 的列）；其餘代號照 prep（兩檔合併、同期取 first_filed 最早）。
 G10 市值（P8 照文字）：量測日前一交易日【原始】收盤 × 封面股數（filed ＜ 量測日、as_of 之後到量測日的拆股乘回）。
    ⚠ 實作差異（照 P8 文字、改正 prep 實作）：prices_yahoo 的 close 欄是「已按日後拆股調整」的價格（AAPL 2020-08-28 close 124.81），
      prep 直接當原始收盤 ⇒ 日後有拆股的股票市值被低估；本件原始收盤 ＝ Yahoo close × 該日之後的 Yahoo 拆股比連乘（Tiingo 來源 close 本來就是原始）。
      周轉率 TO(L) 照 P8（Yahoo 量已按日後拆股調整 ÷ 今日基準股數，兩者同基準，prep 同式）。
 G11 硬斷點：換股簿持股遇轉接層 hard_break（seam／split_div）那天 ⇒ 以前一日收盤結清（⛔ 不跨斷點算報酬）、計數必報；
    槽位型訊號的持有期 (entry, 出場日] 碰到斷點 ⇒ 剔除（W1b W5 同式）。
    |ret|＞50% 敏感度（seq316）：S&P 400 未確認 23 列（A2 D6）當斷點，判定格重跑一次另報標籤。
 G12 下市：換股簿持股在最後一根有效 K 棒之後 ⇒ 以最後收盤結清；槽位型照 simulate_mtm＋delist_status（W1b 同）。
 G13 存活者偏差（必寫）：S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體（A2.coverage）⇒ 結果偏向存活股、偏樂觀。
 G14 結果句：每件標「想法來自台股（多數在台股不合格）」；原登錄有早年段者標「缺早年段」；用到「創 8 季新高」者附「季版條件比月版寬：創 8 季新高觸發 34%」（Q14）；
    A4-6 並引台股兩件不合格（產業營收落後 seq2、產業落後買賣點 seq2）；A4-2 喜偉、歐沙那希句前加「常常湊不滿 10 檔」。
 G15 類股（Q8 改寫 P9）：GICS industry group（約 25 類）由 B3 的 sub-industry 名稱對照 GICS 官方結構推得
    （執行者依 GICS 2016／2018／2023 三版結構手寫對照表 GICS_IG，見 researchUSA4_gics.py；同名在不同版本屬不同 group 者用 B3 的 sector 欄分辨；
     沿用中的 group 用 2023 名稱：Retailing ⇒ Consumer Discretionary Distribution & Retail 等）；
    先報對照率（有 sub-industry 名稱的在指數股-月中對得上的比例，另報占全部在指數股-月），≥ 95% ⇒ 用 industry group；＜ 95% ⇒ 退回 sector 並附「k＝5 約半個市場」。
 G16 種子與亂數：槽位型抽籤 default_rng(102000＋r)；假訊號／隨機臂 default_rng([20261007, 件序, 臂序, r])。
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
from backtest import researchUSW1b as W          # ⚠ import 時會改 us_data 根目錄 ⇒ 先 import、再 install()
from backtest import researchUSA2_data as A2
A2.install()
from backtest import us_data as U
from backtest import researchUSM as RU
from backtest import researchUSM_body as MB
from backtest import researchUSX as USX
from backtest import research11 as R11
from backtest import tradability as TRD
from backtest import researchUSA4_gics as GICS

READ_TS = "2026-10-07 11:54（台北）"
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A4")
WORK = os.path.expanduser("~/us_work/a4")
PREP_WORK = os.path.expanduser("~/us_work/a34")
W0, W1 = A2.WINDOW
EXP_END = pd.Timestamp("2021-12-31")
CONF0 = pd.Timestamp("2022-01-03")
COLS = ("合併", "只400", "只500")
COST = U.COST_ROUNDTRIP
COST_SENS = U.COST_SENSITIVITY
SEED0, NSEED = 102000, 200
FIXH = (20, 60, 120, 240)
IDEA = "想法來自台股（多數在台股不合格）"
NO_EARLY = "缺早年段"
Q14 = "季版條件比月版寬：創 8 季新高觸發 34%"
SURV = "S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體 ⇒ 結果偏向存活股、偏樂觀"
REG = {"登錄": "USREG-A3A4 seq1 sha 0dc16d3267725d7c＋seq2 sha bc0927fed5996fd4",
       "裁定": "seq318 發號、seq319 疑點裁示（Q1、Q6～Q10、Q13～Q16）、seq316 兩母體",
       "開跑前清單": "researchUSA34_prep.py＋resultsUSA34/prep/PREP_REPORT.md（P1～P20；P9 依 Q8 改寫）"}
TW_REG = {  # 各件引用的台股原登錄（清單_29件.csv）
    "A4-1": ("品質因子選股 seq1", "24e7fb594193b9c0"), "A4-2": ("墨菲成長品質選股（大師三套）seq4", "48365ba96fb2b1a9"),
    "A4-3": ("外部研究三件 seq1", "d412ffe18178b3be"), "A4-4": ("低週轉選股 seq1", "47ac98f3c6b5fb02"),
    "A4-5": ("強勢類股選股 seq1", "bb1c8b224f5bb587"), "A4-6": ("產業營收加速 seq3", "42339de513c98702"),
    "A4-7": ("事件型兩件 seq2", "8eae2968c12438fc"), "A4-9": ("外部作者批七顆 seq1（W2）", "62e4026f16879fed"),
    "A4-10": ("飆股回推比對 seq7", "15a22c6b6c2c36d0"), "A4-11": ("機器學習選股改目標 seq1", "168560f97763a287"),
    "A4-12": ("多個弱訊號十一票 seq1", "dbc1881f24a76661"), "A4-13": ("探索批 seq4", "d41c9151eca3fd53")}
EARLY_ITEMS = ("A4-1", "A4-4", "A4-5", "A4-6", "A4-7", "A4-9", "A4-12", "A4-13")   # 原登錄有早年段（PREP §四）
_G: dict = {}


# ═════════════ 小工具 ═════════════
def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _jdef(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, float):
        return None if not np.isfinite(x) else x
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp,)):
        return str(x.date())
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (set, tuple)):
        return list(x)
    return str(x)


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float) and not np.isfinite(o):
        return None
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    return o


def jdump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(_clean(obj), open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_jdef)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def setup_cal():
    calF = U.load_calendar(); cal = calF[calF >= MB.CAL0]
    w0 = int(cal.searchsorted(W0)); w1 = int(cal.searchsorted(W1))
    assert cal[w0] == W0 and cal[w1] == W1, (cal[w0], cal[w1])
    sp = int(cal.searchsorted(EXP_END, side="right")) - 1
    c0 = sp + 1
    assert cal[c0] == CONF0, cal[c0]
    return cal, w0, w1, sp, c0


def tickers(lim=None):
    nos = set(A2.no_ohlc_tickers())
    t = [x for x in A2.tickers_all() if x not in nos]
    return t[::max(1, len(t) // lim)] if lim else t


def month_starts(cal, w0, w1):
    ms = pd.Series(np.arange(len(cal)), index=cal)
    ms = ms[(ms.index >= cal[w0]) & (ms.index <= cal[w1])]
    return ms.groupby([ms.index.year, ms.index.month]).first().to_numpy()


# ═════════════ 世界（每檔價量陣列）═════════════
_SPL = {}


def yahoo_splits(f):
    if f in _SPL:
        return _SPL[f]
    p = U._p("events_yahoo", f + ".csv")
    out = (np.zeros(0, "datetime64[D]"), np.zeros(0))
    dv = (np.zeros(0, "datetime64[D]"), np.zeros(0))
    if os.path.exists(p):
        d = pd.read_csv(p, dtype=str)
        s = d[d["type"] == "split"]
        if len(s):
            r = s["value"].str.split("/", expand=True).astype(float)
            out = (pd.to_datetime(s["date"]).values.astype("datetime64[D]"), (r[0] / r[1]).to_numpy())
        v = d[d["type"] == "div"]
        if len(v):
            dv = (pd.to_datetime(v["date"]).values.astype("datetime64[D]"), pd.to_numeric(v["value"], errors="coerce").to_numpy(float))
    _SPL[f] = (out, dv)
    return _SPL[f]


def raw_and_div(t, cal, valid):
    """→ RCu（真原始收盤，G10）、PXS（與配息同基準的收盤）、DIV（同基準每股配息，除息日）。"""
    pn = U.panel(t); n = len(cal)
    RCu = np.full(n, np.nan); PXS = np.full(n, np.nan); DIV = np.zeros(n)
    for src, g in pn.groupby("src", sort=False):
        kind, f = src.split(":", 1)
        idx = g.index[g.index.isin(cal)]
        pos = cal.get_indexer(idx)
        if kind == "yahoo":
            d = pd.read_csv(U._p("prices_yahoo", f + ".csv"), usecols=["date", "close"], dtype={"date": str})
            s = pd.Series(d["close"].to_numpy(float), index=pd.DatetimeIndex(pd.to_datetime(d["date"]))).reindex(idx).to_numpy(float)
            (sd, sr), (dd, dvv) = yahoo_splits(f)
            dD = idx.values.astype("datetime64[D]")
            fac = np.ones(len(idx))
            for a_, r_ in zip(sd, sr):
                fac[dD < a_] *= r_
            RCu[pos] = s * fac; PXS[pos] = s
            if len(dd):
                m = pd.Series(dvv, index=pd.DatetimeIndex(dd)).groupby(level=0).sum()
                hit = m.reindex(idx).to_numpy(float)
                DIV[pos] = np.nan_to_num(hit)
        else:
            d = pd.read_csv(U._p("prices", f + ".csv"), usecols=["date", "close", "divCash"], dtype={"date": str})
            d.index = pd.DatetimeIndex(pd.to_datetime(d["date"]))
            RCu[pos] = d["close"].reindex(idx).to_numpy(float); PXS[pos] = RCu[pos]
            DIV[pos] = np.nan_to_num(d["divCash"].reindex(idx).to_numpy(float))
    RCu[~valid] = np.nan; PXS[~valid] = np.nan
    return RCu, PXS, DIV


def _w_init(d):
    _G.update(d)


def world_one(t):
    cal = _G["cal"]; n = len(cal)
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A = RU.prep(df, cal)
    if len(A["bars"]) < 2:
        return None
    valid = A["valid"]
    Lw = MB.low_aligned(df, cal)
    V = USX.volume_aligned(t, cal, valid)
    RCu, PXS, DIV = raw_and_div(t, cal, valid)
    m5, m4 = A2.idx_member(t, cal)
    f50 = A2.flag50_pos(t, cal)
    return {"t": t, "O": np.where(valid & (np.nan_to_num(A["O"]) > 0), A["O"], np.nan), "C": A["C"], "H": A["H"], "L": Lw, "valid": valid,
            "V": V, "RCu": RCu, "PXS": PXS, "DIV": DIV, "m5": np.asarray(m5, bool), "m4": np.asarray(m4, bool),
            "pb": A["pb"], "f50": f50}


def stage_world(a):
    os.makedirs(WORK, exist_ok=True)
    cal, w0, w1, sp, c0 = setup_cal()
    tk = tickers(a.lim)
    t0 = time.time(); res = []
    with Pool(a.procs, initializer=_w_init, initargs=({"cal": cal},)) as pool:
        for i, r in enumerate(pool.imap(world_one, tk, chunksize=4)):
            if r is not None:
                res.append(r)
            if (i + 1) % 200 == 0:
                print("[world] %d／%d %.0fs" % (i + 1, len(tk), time.time() - t0), flush=True)
    S = [r["t"] for r in res]
    out = {"tick": np.array(S), "cal": cal.values}
    for k, dt in (("O", np.float64), ("C", np.float64), ("H", np.float32), ("L", np.float32), ("V", np.float32), ("RCu", np.float64),
                  ("PXS", np.float32), ("DIV", np.float32), ("valid", bool), ("m5", bool), ("m4", bool), ("pb", bool), ("f50", bool)):
        out[k] = np.column_stack([np.asarray(r[k], dt) for r in res])
    tag = "_lim" if a.lim else ""
    np.savez(os.path.join(WORK, "world%s.npz" % tag), **out)
    print("[world] %d 檔（可用 %d）%.0fs" % (len(tk), len(S), time.time() - t0), flush=True)


_WD = {}


def load_world(lim=False):
    tag = "_lim" if lim else ""
    if tag in _WD:
        return _WD[tag]
    z = np.load(os.path.join(WORK, "world%s.npz" % tag), allow_pickle=False)
    Wd = {k: z[k] for k in z.files}
    Wd["cal"] = pd.DatetimeIndex(Wd["cal"])
    Wd["ix"] = {t: j for j, t in enumerate(Wd["tick"])}
    Wd["CF"] = pd.DataFrame(Wd["C"]).ffill().to_numpy()             # 收盤 ffill（計值用）
    v = Wd["valid"]; n = v.shape[0]
    last = np.full(v.shape[1], -1); first = np.full(v.shape[1], n)
    anyv = v.any(axis=0)
    last[anyv] = n - 1 - np.argmax(v[::-1, :][:, anyv], axis=0)
    first[anyv] = np.argmax(v[:, anyv], axis=0)
    Wd["last"] = last; Wd["first"] = first
    Wd["mem"] = Wd["m5"] | Wd["m4"]
    _WD[tag] = Wd
    return Wd


# ═════════════ 季財報（G9）═════════════
FIELDS = {"revenue": None, "net_income": "quarterly_net_income.csv", "operating_income": "quarterly_operating_income.csv",
          "rnd": "quarterly_rnd.csv", "assets": "quarterly_assets.csv", "equity": "quarterly_equity.csv",
          "equity_nci": "quarterly_equity_incl_nci.csv", "cfo": "quarterly_cfo.csv", "buyback": "quarterly_buyback.csv"}


def seg_table():
    """代號重用分段：{ticker: [(k, seg_from, seg_to, {cik ∪ 前身})]}。"""
    out = {}
    pred = {}
    for fn in ("cik_predecessor.csv", "cik_predecessor_sp400.csv"):
        p = U._p("fundamentals", fn)
        if os.path.exists(p):
            pr = pd.read_csv(p, dtype=str, keep_default_na=False)
            for r in pr.itertuples():
                if getattr(r, "verdict", "ok") == "ok":
                    pred.setdefault(r.cik_now, set()).add(r.pred_cik)
    for fn in ("cik_map.csv", "cik_map_sp400.csv"):
        cm = pd.read_csv(U._p("fundamentals", fn), dtype=str, keep_default_na=False)
        if "seg_from" not in cm.columns:
            continue
        seg = cm[(cm["seg_from"] != "") | (cm["seg_to"] != "")]
        for t, g in seg.groupby("ticker"):
            if t in out:
                continue
            rows = []
            for k, r in enumerate(g.itertuples()):
                rows.append((k, pd.Timestamp(r.seg_from) if r.seg_from else None, pd.Timestamp(r.seg_to) if r.seg_to else None,
                             {r.cik} | pred.get(r.cik, set())))
            out[t] = rows
    return out


def key_at(SEG, t, d):
    """代號 t 在日 d 用哪一條財報序列（G9）。"""
    if t not in SEG:
        return t
    for k, a, b, _ in SEG[t]:
        if (a is None or d >= a) and (b is None or d < b):
            return "%s#%d" % (t, k)
    return None


def load_fund(cal):
    SEG = seg_table()
    out = {}
    cnt = {"分段代號": sorted(SEG), "分段外丟掉列": 0}
    for f, fn in FIELDS.items():
        if f == "revenue":
            a = pd.read_csv(U._p("fundamentals", "quarterly_revenue.csv"), dtype={"ticker": str, "cik": str})
            b = pd.read_csv(U._p("fundamentals", "quarterly_revenue_sp400.csv"), dtype={"ticker": str, "cik": str})
            q = pd.concat([a, b.drop(columns=["index"])], ignore_index=True)
        else:
            q = pd.read_csv(U._p("fundamentals", fn), dtype={"ticker": str, "cik": str}).drop(columns=["index"])
        q = q[["ticker", "cik", "period_end", "value", "first_filed", "first_form"]].copy()
        q["period_end"] = pd.to_datetime(q["period_end"]); q["first_filed"] = pd.to_datetime(q["first_filed"])
        keys = q["ticker"].to_numpy(object).copy()
        segm = q["ticker"].isin(list(SEG)).to_numpy()
        for i in np.flatnonzero(segm):
            t = keys[i]; ck = q["cik"].iat[i]; kk = None
            for k, _, _, cs in SEG[t]:
                if ck in cs:
                    kk = k; break
            keys[i] = ("%s#%d" % (t, kk)) if kk is not None else None
        q["key"] = keys
        cnt["分段外丟掉列"] += int(q["key"].isna().sum())
        q = q[q["key"].notna()]
        q = q.sort_values(["key", "period_end", "first_filed"]).drop_duplicates(["key", "period_end"], keep="first")
        i = cal.searchsorted(q["first_filed"].values, side="right")
        q["av"] = np.where(i < len(cal), i, 10 ** 9)
        q["fy"] = q["first_form"].astype(str).str.startswith("10-K")
        out[f] = {k: (g["period_end"].values.astype("datetime64[D]").astype(np.int64), g["value"].to_numpy(float), g["av"].to_numpy(int), g["fy"].to_numpy(bool))
                  for k, g in q.groupby("key")}
    sh = pd.read_csv(U._p("fundamentals", "shares_outstanding.csv"), dtype={"ticker": str, "cik": str, "share_class": str})
    sh["as_of_date"] = pd.to_datetime(sh["as_of_date"]); sh["filed"] = pd.to_datetime(sh["filed"])
    sh = sh.dropna(subset=["shares"])
    keys = sh["ticker"].to_numpy(object).copy()
    for i in np.flatnonzero(sh["ticker"].isin(list(SEG)).to_numpy()):
        t = keys[i]; ck = sh["cik"].iat[i]; kk = None
        for k, _, _, cs in SEG[t]:
            if ck in cs:
                kk = k; break
        keys[i] = ("%s#%d" % (t, kk)) if kk is not None else None
    sh["key"] = keys; sh = sh[sh["key"].notna()]
    sh = sh.groupby(["key", "as_of_date", "filed"], as_index=False)["shares"].sum()
    i = cal.searchsorted(sh["filed"].values, side="right")
    sh["av"] = np.where(i < len(cal), i, 10 ** 9)
    out["shares"] = {k: (g["as_of_date"].values.astype("datetime64[D]").astype(np.int64), g["shares"].to_numpy(float), g["av"].to_numpy(int))
                     for k, g in sh.sort_values(["key", "as_of_date"]).groupby("key")}
    spl = {}
    for fn in os.listdir(U._p("events_yahoo")):
        d = pd.read_csv(U._p("events_yahoo", fn), dtype=str)
        d = d[d["type"] == "split"]
        if len(d):
            r = d["value"].str.split("/", expand=True).astype(float)
            spl[fn[:-4]] = (pd.to_datetime(d["date"]).values.astype("datetime64[D]").astype(np.int64), (r[0] / r[1]).to_numpy())
    for t, rows in SEG.items():                     # 分段鍵沿用該代號的拆股事件
        if t in spl:
            for k, *_ in rows:
                spl["%s#%d" % (t, k)] = spl[t]
    out["splits"] = spl
    out["SEG"] = SEG
    out["_cnt"] = cnt
    return out


def q_last(F, f, t, e, k, stale=200, edays=None):
    """＝ researchUSA34_prep.q_last（逐字同式；這裡用分段鍵 t）。"""
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


def yoy_at(F, f, t, e, edays, back=0):
    """＝ prep yoy_of（back＝0）；back＝1 ⇒ 前一季的年增（prep rev_yoy_prev 同式）。"""
    x = F[f].get(t)
    if x is None:
        return np.nan
    pe, v, av, fy = x
    m = np.flatnonzero(av <= e)
    if len(m) < 1 + back:
        return np.nan
    j = m[-1 - back]
    if back == 0 and edays - pe[j] > 200:
        return np.nan
    pk = m[(pe[m] >= pe[j] - 380) & (pe[m] <= pe[j] - 350)]
    if not len(pk) or not (v[pk[-1]] > 0) or not np.isfinite(v[j]):
        return np.nan
    return v[j] / v[pk[-1]] - 1


def fy_series(F, f, t, e, nyears, stale=500, edays=None):
    """＝ prep fy_series。"""
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
    """＝ prep shares_at。"""
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


def rev_extra(F, k, e, ed):
    """季營收補充量：連續年增季數（最多 8）、距 8 季最高（最新 ÷ 最近 8 季最高 − 1）、最新一季期末日。"""
    x = F["revenue"].get(k)
    out = {"rev_streak": np.nan, "rev_dist8": np.nan}
    if x is None:
        return out
    q8 = q_last(F, "revenue", k, e, 8, edays=ed)
    if q8 is not None and q8[1].max() > 0:
        out["rev_dist8"] = float(q8[1][-1] / q8[1].max() - 1)
    pe, v, av, fy = x
    m = np.flatnonzero(av <= e)
    if not len(m) or ed - pe[m[-1]] > 200:
        return out
    stk = 0
    for back in range(0, 8):
        if len(m) < 1 + back:
            break
        j = m[-1 - back]
        pk = m[(pe[m] >= pe[j] - 380) & (pe[m] <= pe[j] - 350)]
        if not len(pk) or not (v[pk[-1]] > 0) or not np.isfinite(v[j]) or not (v[j] > v[pk[-1]]):
            break
        stk += 1
    out["rev_streak"] = float(stk)
    return out


def fund_row(F, k, e, ed, rcu, v20, v60, v120, pxs=np.nan, div365=np.nan):
    """一個（序列鍵, 量測日 e）的季財報量（prep fund_month 逐式同；市值照 G10 用真原始收盤 rcu ＝ RCu[e−1]）。"""
    rw = {}
    y0 = yoy_at(F, "revenue", k, e, ed); rw["rev_yoy"] = y0
    rw["rev_yoy_prev"] = yoy_at(F, "revenue", k, e, ed, back=1) if np.isfinite(y0) else np.nan
    q8 = q_last(F, "revenue", k, e, 8, edays=ed)
    rw["rev_hi8"] = (bool(q8[1][-1] > q8[1][:-1].max())) if q8 is not None else np.nan
    q2 = q_last(F, "revenue", k, e, 2, edays=ed)
    rw["rev_qoq"] = (q2[1][1] / q2[1][0] - 1) if (q2 is not None and q2[1][0] > 0) else np.nan
    rw.update(rev_extra(F, k, e, ed))
    tt = {}
    for f in ("net_income", "operating_income", "revenue", "rnd"):
        q4 = q_last(F, f, k, e, 4, edays=ed)
        tt[f] = float(q4[1].sum()) if q4 is not None else np.nan
    rw.update({"ttm_" + kk: vv for kk, vv in tt.items()})
    qn = q_last(F, "net_income", k, e, 2, edays=ed)
    rw["ni_turn"] = (bool(qn[1][1] > 0 and qn[1][0] <= 0)) if qn is not None else np.nan
    rw["ni_q"] = float(qn[1][1]) if qn is not None else np.nan
    qe = q_last(F, "equity", k, e, 2, edays=ed); qa = q_last(F, "assets", k, e, 2, edays=ed)
    eq0 = qe[1][1] if qe is not None else np.nan; eqm = qe[1].mean() if qe is not None else np.nan
    as0 = qa[1][1] if qa is not None else np.nan; asm = qa[1].mean() if qa is not None else np.nan
    rw["roe"] = tt["net_income"] / eqm if (np.isfinite(eqm) and eqm > 0) else np.nan
    rw["roe_q"] = rw["ni_q"] / eqm if (np.isfinite(eqm) and eqm > 0 and np.isfinite(rw["ni_q"])) else np.nan
    rw["oia"] = tt["operating_income"] / as0 if (np.isfinite(as0) and as0 > 0) else np.nan
    rw["roa"] = tt["net_income"] / asm if (np.isfinite(asm) and asm > 0) else np.nan
    rw["rnd_int"] = tt["rnd"] / tt["revenue"] if (np.isfinite(tt["revenue"]) and tt["revenue"] > 0 and np.isfinite(tt["rnd"])) else np.nan
    qo = q_last(F, "operating_income", k, e, 5, edays=ed); qr = q_last(F, "revenue", k, e, 5, edays=ed)
    if qo is not None and qr is not None and qr[1][0] > 0 and qr[1][-1] > 0 and qo[0][-1] == qr[0][-1]:
        rw["opm_up_yoy"] = bool(qo[1][-1] / qr[1][-1] > qo[1][0] / qr[1][0])
    else:
        rw["opm_up_yoy"] = np.nan
    shs = shares_at(F, k, e, ed); shs_today = shares_at(F, k, e, ed, today_basis=True)
    mcap = shs * rcu if np.isfinite(shs) and np.isfinite(rcu) else np.nan
    rw["shares"] = shs; rw["mcap"] = mcap
    rw["pe"] = mcap / tt["net_income"] if (np.isfinite(mcap) and np.isfinite(tt["net_income"]) and tt["net_income"] > 0) else np.nan
    rw["pe_computable"] = bool(np.isfinite(mcap) and np.isfinite(tt["net_income"]))
    rw["ep"] = (tt["net_income"] / mcap) if (np.isfinite(mcap) and mcap > 0 and np.isfinite(tt["net_income"]) and tt["net_income"] > 0) else np.nan
    rw["bp"] = eq0 / mcap if (np.isfinite(mcap) and mcap > 0 and np.isfinite(eq0)) else np.nan
    qb = q_last(F, "buyback", k, e, 1, edays=ed)
    rw["bb_q"] = float(qb[1][0]) if qb is not None else np.nan
    rw["bb_mcap"] = qb[1][0] / mcap if (qb is not None and np.isfinite(mcap) and mcap > 0) else np.nan
    for L, vv in ((20, v20), (60, v60), (120, v120)):
        rw["to%d" % L] = vv / shs_today if (np.isfinite(shs_today) and shs_today > 0 and np.isfinite(vv)) else np.nan
    rw["shares_today"] = shs_today
    rw["divy"] = div365 / pxs if (np.isfinite(pxs) and pxs > 0 and np.isfinite(div365)) else np.nan
    # 墨菲／喜偉／歐沙那希（prep 同式）
    q12o = q_last(F, "operating_income", k, e, 12, edays=ed); q12r = q_last(F, "revenue", k, e, 12, edays=ed)
    if q12o is not None and q12r is not None and (q12r[1] > 0).all() and (q12o[0] == q12r[0]).all():
        rw["M1"] = bool(np.mean(q12o[1] / q12r[1]) > 0.10)
    else:
        rw["M1"] = np.nan
    ni5 = fy_series(F, "net_income", k, e, 5, edays=ed)
    roe5 = roa5 = dr5 = np.nan
    if ni5 is not None:
        eqs = [inst_at(F, "equity", k, p, e) for p in ni5[1]]
        ass = [inst_at(F, "assets", k, p, e) for p in ni5[1]]
        eqn = [inst_at(F, "equity_nci", k, p, e) for p in ni5[1]]
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
    rv4 = fy_series(F, "revenue", k, e, 4, edays=ed)
    if rv4 is not None and all(x_ > 0 for x_ in rv4[0][:-1]):
        rw["M3"] = bool(np.mean([rv4[0][i + 1] / rv4[0][i] - 1 for i in range(3)]) > 0.10)
    else:
        rw["M3"] = np.nan
    rw["M4"] = bool(rw["rnd_int"] > 0.05) if np.isfinite(rw["rnd_int"]) else False
    ni4 = fy_series(F, "net_income", k, e, 4, edays=ed)
    rw["O3"] = np.nan
    if ni4 is not None:
        eps = []
        for v_, p_ in zip(ni4[0], ni4[1]):
            s_ = shares_at(F, k, e, p_ + 1)
            eps.append(v_ / s_ if np.isfinite(s_) and s_ > 0 else np.nan)
        if all(np.isfinite(eps)):
            g = [(eps[i + 1] / eps[i] - 1) if eps[i] > 0 else None for i in range(3)]
            rw["O3"] = bool(all(x_ is not None for x_ in g) and np.mean(g) > 0.30)
    rw["PE15"] = bool(rw["pe"] < 15) if np.isfinite(rw["pe"]) else (False if rw["pe_computable"] else np.nan)
    return rw


def load_sectors():
    s = pd.read_csv(U._p("sectors", "sector_pit.csv"), dtype=str, keep_default_na=False)
    toD = lambda x: int(np.datetime64(x, "D").astype(np.int64)) if x else None
    out = defaultdict(list)
    for r in s.itertuples(index=False):
        out[r.ticker].append((toD(r.valid_from), toD(r.valid_to), r.gics_sector, r.gics_sub_industry))
    return out


def sector_at(sec, t, ed):
    gs = gsub = None
    for vf, vt, a_, b_ in sec.get(t, ()):
        if vf <= ed and (vt is None or ed < vt):
            gs, gsub = a_, b_
    return gs, gsub


# ═════════════ 逐月面板（G8）═════════════
def _p_init(d):
    _G.update(d)


def panel_part(tks):
    F = _G["F"]; Wd = _G["Wd"]; cal = Wd["cal"]; cd = cal.values.astype("datetime64[D]").astype(np.int64)
    MR = _G["MR"]; sec = _G["sec"]; SEG = F["SEG"]
    out = []
    for t in tks:
        if t not in Wd["ix"]:
            continue
        j = Wd["ix"][t]
        RCu = Wd["RCu"][:, j]; PXS = Wd["PXS"][:, j]; DIV = Wd["DIV"][:, j]; valid = Wd["valid"][:, j]
        vb = np.flatnonzero(valid)
        for rw in MR.get(t, []):
            e = rw["e"]; ed = int(cd[e])
            kb = int(np.searchsorted(vb, e)) - 1
            if kb < 0:
                continue
            dl = int(vb[kb])
            k = key_at(SEG, t, cal[e])
            d365 = cal[e] - pd.Timedelta(days=365)
            i0 = int(cal.searchsorted(d365))
            div365 = float(np.nansum(DIV[i0:e]))
            r = dict(rw)
            r["skey"] = k
            if k is None:
                out.append(r); continue
            r.update(fund_row(F, k, e, ed, RCu[dl], rw.get("v20", np.nan), rw.get("v60", np.nan), rw.get("v120", np.nan), PXS[dl], div365))
            gs, gsub = sector_at(sec, t, ed)
            r["sector"] = gs; r["subind"] = gsub; r["ig"] = GICS.ig_of(gs, gsub)
            out.append(r)
    return out


def stage_panel(a):
    cal, w0, w1, sp, c0 = setup_cal()
    Wd = load_world(a.lim)
    assert (Wd["cal"] == cal).all()
    P = pickle.load(open(os.path.join(PREP_WORK, "px%s.pkl" % ("_lim" if a.lim else "")), "rb"))
    MR = defaultdict(list)
    keep = ("t", "mi", "e", "m5", "m4", "nbar", "r21", "r60", "r63", "r126", "r189", "r252", "r12_1", "vol60", "tv100n", "v20", "v60", "v120",
            "vr20_250", "d250hi", "c_ma60", "stack", "tmpl17", "rs", "strong", "hi250_L5", "hi250_L20", "hi250_L60", "td9_L5", "td9_L20", "td9_L60",
            "rsi_L5", "rsi_L20", "rsi_L60", "s06_L5", "s06_L20", "s06_L60", "utb_L5", "utb_L20", "utb_L60", "vsc_L5", "vsc_L20", "vsc_L60")
    for r in P["res"]:
        for rw in r["MONTH"]:
            MR[rw["t"]].append({k: rw.get(k) for k in keep})
    W2c = {r["t"]: r["W2c"] for r in P["res"]}
    t0 = time.time()
    F = load_fund(cal)
    sec = load_sectors()
    print("[panel] 財報 %.0fs" % (time.time() - t0), flush=True)
    tk = sorted(MR)
    parts = [tk[i::a.procs * 4] for i in range(a.procs * 4)]
    with Pool(a.procs, initializer=_p_init, initargs=({"F": F, "Wd": Wd, "MR": MR, "sec": sec},)) as pool:
        res = pool.map(panel_part, parts)
    M = pd.DataFrame([r for x in res for r in x])
    tag = "_lim" if a.lim else ""
    M.to_pickle(os.path.join(WORK, "panel%s.pkl" % tag))
    pickle.dump({"F": F, "W2c": W2c, "sec": dict(sec)}, open(os.path.join(WORK, "fund%s.pkl" % tag), "wb"))
    print("[panel] %d 股-月｜%.0fs" % (len(M), time.time() - t0), flush=True)


_PN = {}


def load_panel(lim=False):
    tag = "_lim" if lim else ""
    if tag not in _PN:
        M = pd.read_pickle(os.path.join(WORK, "panel%s.pkl" % tag))
        FD = pickle.load(open(os.path.join(WORK, "fund%s.pkl" % tag), "rb"))
        _PN[tag] = (M, FD)
    return _PN[tag]


# ═════════════ 基準 ═════════════
def bench_series(cal):
    return U.benchmark_tr("SP500TR").reindex(cal).ffill().to_numpy(float)


def seg_metrics(eq, a, b):
    c, m = W.window_metrics(eq, a, b)
    return {"年化": c, "回落": m, "比值": c / abs(m) if m < 0 else np.nan}


def bench_metrics(cal, segs):
    B = bench_series(cal)
    return {k: seg_metrics(B, a, b) for k, (a, b) in segs.items()}


def lab(c, m, cb, mb):
    if not (np.isfinite(c) and np.isfinite(m)) or m >= 0:
        return "—"
    return W.label(c, m, cb, mb)[0]


def final_label(l_comb, l_400):
    """G4（＝ W1b W7）。"""
    order = {"合格": 2, "另列": 1, "不合格": 0, "—": -1}
    if l_comb == "合格" and l_400 == "合格":
        return "合格"
    if l_comb == "合格":
        return "事後擴母體"
    if l_comb == "另列":
        return "另列" if order.get(l_400, -1) >= 1 else "事後擴母體（另列）"
    if l_comb == "—":
        return "不可判定"
    return "不合格"


# ═════════════ 引擎①：換股簿（等權、續抱仍入選；台股 researchMomX.sim_book 同式＋美股斷點／下市）═════════════
def sim_book(sel, Wd, N, t0, t1, cost=COST, fixed_h=None, brk=None, weights=None, full_rebal=False, trades_out=None, ma_stop=None):
    """sel：{t: [代號序號 j（依優先序）]}（t ＝ 換股日，e 開盤成交）。
    weights：None ＝ 等權 N 槽；{t: {j: 目標權重}} ＝ 依權重（full_rebal ⇒ 每個換股日全部調回目標，A4-3 X1）。
    fixed_h：None ＝ 主臂（落選才賣）；H ＝ 描述臂（新進者抱滿 H 根收盤賣、不因落選而賣、空槽換股日補）。
    brk：(n, S) bool 斷點陣列（G11；None ＝ Wd["pb"]）。
    ma_stop：None／(n, S) 均線陣列 ⇒ 持股 t−1 收盤 ＜ 均線[t−1] ⇒ t 開盤賣（出場敏感度描述臂；台股 sim_book ma_stop 同式）。"""
    O, CF, valid, last = Wd["O"], Wd["CF"], Wd["valid"], Wd["last"]
    brk = Wd["pb"] if brk is None else brk
    n = len(Wd["cal"])
    eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    npos = np.zeros(n, np.int16); cashf = np.zeros(n); costd = np.zeros(n); buyd = np.zeros(n)
    cnt = Counter()
    rebs = sorted(t for t in sel if t0 <= t <= t1)
    rset = set(rebs)
    tr = [] if trades_out is not None else None
    for t in range(t0, t1 + 1):
        # 斷點／下市 ⇒ 以前一日收盤結清（G11、G12）
        for j in list(pos):
            u, amt, b, hi = pos[j]
            if t > b and brk[t, j]:
                px = CF[t - 1, j]; why = "斷點"
            elif t > last[j]:
                px = CF[last[j], j]; why = "下市"
            else:
                continue
            pos.pop(j); pend.discard(j)
            cash += u * px - amt * cost; costd[t] += amt * cost; cnt["sell_" + why] += 1
            if tr is not None:
                tr.append((j, b, t - 1, px / (amt / u) - 1, px / hi - 1 if hi > 0 else np.nan, why))
        # 固定天數臂：第 H 根收盤賣（在本日計值後處理，見下）
        s_ = sel.get(t) if t in rset else None
        if s_ is not None and fixed_h is None:
            if weights is None:
                pend = (pend | (set(pos) - set(s_))) - set(s_)
            else:
                tw = weights[t]
                pend = (pend | (set(pos) - set(tw))) - set(tw)
        if ma_stop is not None and t > t0:
            for j in list(pos):
                mv = ma_stop[t - 1, j]
                if j not in pend and np.isfinite(mv) and valid[t - 1, j] and CF[t - 1, j] < mv:
                    pend.add(j); cnt["ma_stop"] += 1
        for j in sorted(pend):
            if j not in pos:
                pend.discard(j); continue
            o_t = O[t, j]
            if valid[t, j] and np.isfinite(o_t) and o_t > 0:
                px = o_t
            else:
                cnt["sell_delayed"] += 1; continue
            u, amt, b, hi = pos.pop(j)
            cash += u * px - amt * cost; costd[t] += amt * cost; cnt["sell"] += 1; pend.discard(j)
            if tr is not None:
                tr.append((j, b, t, px / (amt / u) - 1, px / max(hi, px) - 1, "換股"))
        if s_ is not None:
            if weights is None:
                free = N - len(pos)
                new = [j for j in s_ if j not in pos][:max(free, 0)]
                for j in new:
                    o_t = O[t, j]
                    if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                        cnt["buy_halt"] += 1; continue
                    amt = min(eq[t - 1] / N, cash)
                    if amt <= 1e-12:
                        break
                    cash -= amt; pos[j] = [amt / o_t, amt, t, o_t]; cnt["buy"] += 1; buyd[t] += amt
            else:
                tw = weights[t]
                # 以開盤價計值 ⇒ 全部調回目標（full_rebal）或只買新進（否則）
                val = cash + sum(u * (O[t, j] if np.isfinite(O[t, j]) and O[t, j] > 0 else CF[t - 1, j]) for j, (u, _, _, _) in pos.items())
                if full_rebal:
                    for j in sorted(tw, key=lambda x: -tw[x]):
                        o_t = O[t, j]
                        if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                            cnt["buy_halt"] += 1; continue
                        tgt = val * tw[j]
                        cur = pos[j][0] * o_t if j in pos else 0.0
                        d = tgt - cur
                        if d < 0 and j in pos:                     # 減碼：按比例結算進場金額
                            u, amt, b, hi = pos[j]; fr = -d / cur
                            cash += -d - amt * fr * cost; costd[t] += amt * fr * cost
                            pos[j] = [u * (1 - fr), amt * (1 - fr), b, hi]; cnt["trim"] += 1
                    for j in sorted(tw, key=lambda x: -tw[x]):
                        o_t = O[t, j]
                        if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                            continue
                        tgt = val * tw[j]
                        cur = pos[j][0] * o_t if j in pos else 0.0
                        d = min(tgt - cur, cash)
                        if d > 1e-12:
                            if j in pos:
                                u, amt, b, hi = pos[j]; pos[j] = [u + d / o_t, amt + d, b, hi]
                            else:
                                pos[j] = [d / o_t, d, t, o_t]; cnt["buy"] += 1
                            cash -= d; buyd[t] += d
        hv = 0.0
        for j, p in pos.items():
            c = CF[t, j]; hv += p[0] * c
            if c > p[3]:
                p[3] = c
        eq[t] = cash + hv
        if fixed_h is not None:
            for j in list(pos):
                u, amt, b, hi = pos[j]
                if t - b + 1 >= fixed_h:
                    px = CF[t, j]
                    pos.pop(j); cash += u * px - amt * cost; costd[t] += amt * cost; cnt["sell_fixed"] += 1
                    eq[t] -= amt * cost
                    if tr is not None:
                        tr.append((j, b, t, px / (amt / u) - 1, px / hi - 1 if hi > 0 else np.nan, "固定"))
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    openp = [(j, p[2], p[3]) for j, p in pos.items()]
    if tr is not None:
        trades_out.extend(tr)
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buyd": buyd, "cnt": dict(cnt), "open": openp}


def book_stats(res, a, b, N=None, sel=None, trades=None, Wd=None):
    m = seg_metrics(res["eq"], a, b)
    yrs = (b - a + 1) / 252
    meq = float(res["eq"][a:b + 1].mean())
    m.update({"平均持股": float(res["npos"][a:b + 1].mean()), "現金比例": float(np.nanmean(res["cashf"][a:b + 1])),
              "每年換手": float(res["buyd"][a:b + 1].sum()) / meq / yrs, "成本／年": float(res["costd"][a:b + 1].sum()) / meq / yrs})
    if trades is not None:
        m.update(hold_stats([x for x in trades if a <= x[1] <= b], b, res, Wd))
    return m


def hold_stats(tr, b, res=None, Wd=None):
    """持有天數分佈（交易日；出場日 − 進場日）、離頂多近（出場價 ÷ 持有期最高收盤 − 1 的中位）、段尾仍持有。"""
    done = [x for x in tr if x[2] <= b]
    hd = np.array([x[2] - x[1] for x in done], float)
    near = np.array([x[4] for x in done if np.isfinite(x[4])], float)
    tail = len(tr) - len(done)
    out = {"出場筆數": int(len(done)), "段尾仍持有（筆）": int(tail)}
    if len(hd):
        out.update({"持有天數_平均": float(hd.mean()), "持有天數_中位": float(np.median(hd)), "持有天數_p10": float(np.percentile(hd, 10)),
                    "持有天數_p90": float(np.percentile(hd, 90)), "持有天數_最長": float(hd.max()),
                    "離頂多近_中位": float(np.median(near)) if len(near) else np.nan, "出場勝率": float(np.mean([x[3] > 0 for x in done]))})
    return out


# ═════════════ 引擎②：槽位（research11.simulate_mtm；W1b 同包法）═════════════
_S = {}
RULE = "A4"


def slot_ctx(Wd):
    """closes／opens／tradable／delist（W1b 同式：trd ＝ 有效 K 棒；漲跌停旗標全 False）。"""
    if "ctx" in _S:
        return _S["ctx"]
    n, S = Wd["C"].shape
    z = np.zeros(n, bool)
    closes = {j: Wd["CF"][:, j] for j in range(S)}
    opens = {j: Wd["O"][:, j] for j in range(S)}
    trad = {j: {"trd": Wd["valid"][:, j], "up_o": z, "dn_o": z, "dn_c": z} for j in range(S)}
    dl = TRD.delist_status(trad, Wd["cal"])
    _S["ctx"] = {"closes": closes, "opens": opens, "trad": trad, "dl": dl, "n": n}
    return _S["ctx"]


def _slot_run(args):
    key, seed = args
    s = _S["arms"][key]; c = _S["ctx"]
    R11.COST = s["cost"]
    aud = [] if (s.get("audit") and seed == SEED0) else None
    try:
        out = R11.simulate_mtm(s["sig"], RULE, s["N"], np.random.default_rng(seed), c["closes"], c["opens"], c["n"], return_equity=True,
                               pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=c["trad"], delist=c["dl"], audit=aud)
    finally:
        R11.COST = U.COST_ROUNDTRIP
    eq = out["equity"]
    r = {"key": key, "seed": seed}
    for nm, (a, b) in s["segs"].items():
        mm = seg_metrics(eq, a, b); r[nm + "_年化"] = mm["年化"]; r[nm + "_回落"] = mm["回落"]
        r[nm + "_持股"] = np.nan
    r["trades"] = out["trades"]; r["slot_use"] = out["slot_use"]
    if aud is not None:
        buy = {}; hold = []
        for a_ in aud:
            if a_["side"] == "buy":
                buy[a_["sid"]] = a_["t"]
            elif a_["side"] == "sell" and a_["sid"] in buy:
                b_ = buy.pop(a_["sid"]); hold.append((int(a_["sid"]), int(b_), int(a_["t"])))
        r["holds"] = hold
    return r


def run_slots(arms, Wd, procs, nseed=NSEED):
    """arms：{key: {"sig": DataFrame, "N": 槽數, "segs": {名: (a, b)}, "cost": c, "audit": bool}} ⇒ {key: DataFrame(逐種子)}。"""
    slot_ctx(Wd)
    _S["arms"] = arms
    jobs = [(k, SEED0 + r) for k in arms for r in range(nseed)]
    with Pool(procs) as pool:
        out = pool.map(_slot_run, jobs, chunksize=max(1, len(jobs) // (procs * 20)))
    D = defaultdict(list)
    for r in out:
        D[r["key"]].append(r)
    return {k: pd.DataFrame(v) for k, v in D.items()}


def slot_summary(df, segs, bm):
    out = {}
    for nm in segs:
        c = float(df[nm + "_年化"].median()); m = float(df[nm + "_回落"].median())
        b = bm[nm]
        out[nm] = {"年化中位": c, "回落中位": m, "比值": c / abs(m) if m < 0 else np.nan, "標籤": lab(c, m, b["年化"], b["回落"]),
                   "年化p10": float(df[nm + "_年化"].quantile(0.1)), "年化p90": float(df[nm + "_年化"].quantile(0.9)),
                   "逐種子合格比例": float(np.mean([lab(x, y, b["年化"], b["回落"]) == "合格" for x, y in zip(df[nm + "_年化"], df[nm + "_回落"])]))}
    out["交易數中位"] = float(df["trades"].median()); out["槽位使用率中位"] = float(df["slot_use"].median())
    return out


def mk_sig(rows):
    """rows：[(j, entry, xpos, g, 月)] ⇒ simulate_mtm 訊號表。"""
    if not rows:
        return pd.DataFrame({"sid": pd.Series([], int), "entry_pos": pd.Series([], int), "xpos_" + RULE: pd.Series([], int),
                             "g_" + RULE: pd.Series([], float), "month": pd.Series([], str)})
    d = pd.DataFrame(rows, columns=["sid", "entry_pos", "xpos_" + RULE, "g_" + RULE, "month"])
    return d.sort_values(["entry_pos", "sid"]).reset_index(drop=True)


def crosses(brk, j, a, b):
    """(a, b] 內有斷點。"""
    if b <= a:
        return False
    return bool(brk[a + 1:b + 1, j].any())


# ═════════════ 事件層統計（researchM.summ／verdict 同式）═════════════
def ev_summ(x, T, cal, w0):
    import researchM as TWM
    s = TWM.summ(np.asarray(x, float), np.asarray(T, int), cal, w0, blk=20, cap=10 ** 6)
    if s.get("n", 0):
        s["出口"], s["判語"] = TWM.verdict(s)
    return s


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--lim", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--seeds", type=int, default=NSEED)
    ap.add_argument("--reps", type=int, default=1000)
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    if a.stage == "world":
        stage_world(a)
    elif a.stage == "panel":
        stage_panel(a)
    elif a.stage == "items":
        from backtest import researchUSA4_items as IT
        IT.run_items(a)
    elif a.stage == "ml":
        from backtest import researchUSA4_ml as ML
        ML.run(a)
    elif a.stage == "surge":
        from backtest import researchUSA4_surge as SG
        SG.run(a)
    elif a.stage == "followup":
        from backtest import researchUSA4_items as IT
        IT.followup(a)
    elif a.stage == "report":
        from backtest import researchUSA4_items as IT
        IT.report(a)
    else:
        raise SystemExit("unknown stage")


if __name__ == "__main__":
    main()
