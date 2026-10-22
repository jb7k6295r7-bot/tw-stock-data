# -*- coding: utf-8 -*-
"""營收「轉強」之後是否勝過同類未轉強 seq2【頻率表・乾跑】（台股策略線 登錄 sha 03f8b072ecfcf67c，2026-10-22 16:41；裁定 seq447 §三 發號 N_單筆 ＋1、
最多暫定、「先交頻率表，含乙 vs G1、轉強起點 vs 營量／營飆的重疊率（seq377）」；價量拆分依構造不可判定、只報兩個代理）——回測線計算子代理。
⛔ 只數事件、配對、n_eff、拆組件數、走得完比例、重疊；⛔ 不讀、不算、不存任何進場後報酬（seq366）。
   用到的價格只有 ≤ 判日（可用日前一交易日）的還原收盤（前 12 月／前 60 日漲跌只用來分位配對、⛔ 不存數值）與市值（只存十分位）；
   進場日以後只用「有沒有有效 K 棒／壞根／下市／開盤鎖漲停」旗標。
⛔ 不 commit、不改既有檔；bigrun_monthly（load_rev_pit、rev_metrics、pub10、rev_avail、load_xbrl ＝ 轉強定義，⛔ 只 import、不寫第二份）、
   researchIndMom_freq（build_panel、reg_check、entry_flag、load_pit）、researchIndMom（build_exr）、researchTopSell_freq（merged_prices）、
   researchLongPool（load_filing、single、qkey）、rerun17（load_bench、regime_mask）⛔ 只 import。
本檔另提供共用（researchShortageExit_freq import）：ensure_data、rev_table、prices、gm_table、filing_pos、avail_pos、back_ret。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevTurn_freq [--procs 3] [--limit N（乾跑：隨機 N 檔，輸出 ~/rtfwork/dry_rt）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevTurn_freq_check [--dry]
輸出 backtest/resultsRevTurn/freq/：freq.json、freq_段.csv、yearly.csv、split.csv、group12.csv、overlap.csv、events.csv.gz（逐事件旗標，⛔ 無報酬、無價格）、run.log

═══ 讀法（V 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 V0 資料：tw-stock-data 最新 origin/main（git archive 到 ~/rtfwork/main_<sha12>，唯讀）：月營收（revenue_hist 2015 起＋early/revenue 2003～2014＋每日版 revenue）、
    industry_pit、fs_xbrl、fin_hist、filing_dates、exright／early exright／otcexright。價格 ＝ researchIndMom_freq.build_panel 兩世界快取（主 rerun17 H2D edc6f
    2015-01-05～2026-09-24、早年 eotc 2004-02-11～2014-12-31；四碼普通股（UG.gate3(GATE_V2)）、含已下市；壞根 ＝ 缺口 ≥5 日（seq335）∪ 價格斷點 ∪ 幽靈還原
    ∪ crashwork ∪ 早年 reduce_v2），兩世界接成合併日曆 ＝ researchTopSell_freq.merged_prices 原式。
 V1 exright（seq412）：researchIndMom.build_exr 原式（開盤鎖漲停、幽靈壞根改用 open_base）；★ 只把它讀的 exright 表換成「上市 exright＋early exright＋上櫃 otcexright」
    （原式只取上市，因當時上櫃 open_base 全空；最新 main 上櫃已補）。開盤鎖跌停 ★ 同式（原始開盤 ＝ limit_price(open_base, 跌, 7%／10%) ∧ 原始最高 ＝ 原始開盤），
    其他日子沿用世界快取 dnl。
 V2 轉強（＝ 大漲觀察月報；⛔ 不寫第二份）：bigrun_monthly.load_rev_pit（公告當時口徑；★ 它讀的 revenue_hist 目錄另放 early/revenue 2003～2014 的檔（同欄位）以便回到 2004）
    ＋ bigrun_monthly.rev_metrics 逐期呼叫（asof ＝ pub10(期)＋1 日 ⇒ 回該期；只取「我方庫該期有值」的股，即 rev_period ＝ 該期）。
    ★ rev_metrics 的月序列寫死從 2010-01 起 ⇒ 期別標籤一律平移 ＋7 年再呼叫（只改標籤、整年平移；月差、同列年增、去年同月皆不變）；
      _check 以 2012-01 之後抽期不平移重算、逐值相同驗證。期別 2004-01 起（前 12 月可算；24 月新高 2005-01 起才可能有值）。
    甲 ＝ accel ≥ 0.05；乙 ＝ hi24 ∧ ¬hi24_prev；up ＝ 甲 ∨ 乙（＝ 函式 up）；起點 ＝ up ∧ ¬up_prev（函式原值；上期不可判 ⇒ up_prev 為假，件數照報）。
 V3 可用日 A ＝ 合併日曆中第一個日期 ＞ bigrun_monthly.rev_avail(期)（次月 10 日；2026-01 期起 15 日）的交易日；進場 e ＝ A 的下一交易日開盤（登錄字面）。
    500 張閘 ★ ＝ 面板 G[A−1]（patterns.Frame.gate：含判日的 20 交易日都有成交 ∧ 判日前 20 日均量 ≥ 500 張；∧ UG.pit_valid）〔另一讀法：G[A]〕。
 V4 事件：起點 ∧ 在面板（四碼普通股）∧ 過閘；★ 同檔 12 個月內只取第一次 ＝ 過閘起點依期別排序，與上一個「取用」的期別相差 ＜ 12 個月 ⇒ 不取（照報）。
    進場剔除（researchIndMom_freq.entry_flag 原式，t ＝ A）：壞根(A,e] → e無成交 → e開盤鎖漲停（exright 版）。
 V5 配對（登錄 §二）：同期（＝同一可用日）、本期有值且 up 為假、同產業（PRE.PIT 在 A 的 industry_pit，含 fallback；★「其他」也算一類、無類別 ⇒ 配不到）、
    市值十分位同、前 12 月漲跌三分位同；★ 分位母體 ＝ 判日 A−1 過閘的面板股中該特徵可算者（pandas rank pct、average；十分位 ＝ ceil(pct×10)、三分位 ＝ ceil(pct×3)）；
    市值 ＝ 面板 MC[A−1]（原始收盤 × 股數，ffill）；前 12 月 ＝ c[A−1] ÷ c[A−1 日期 − 12 曆月當天或之前最後有效] − 1（A−1 須為有效 K 棒），★ 窗內有壞根 ⇒ 不可算（配不到）。
    對照也要過閘、e 可進場；★ 每事件候選 ≥ 3 抽 3、否則全取（1～2）；抽樣 ＝ np.random.default_rng(20261022)，事件依（A, 代號）序逐一抽。配不到 ⇒ 不入主格。
 V6 持有 H ∈ {60, 120, 250}：出場日 x ＝ e ＋ H（合併日曆位置；★「持有 H 個交易日後收盤」）；走得完 ＝ x ≤ 資料尾；窗內遇壞根 ＝ (e, x] 有壞根；
    下市 ＝ 最後有效 K 棒 ＜ x 且距資料尾 ≥ 5 日。★ 主格事件（頻率表口徑）＝ 配到 ∧ e 可進場 ∧ H＝250 走得完（遇壞根、下市照數，處理留正式跑）。
 V7 段 ★ 依可用日 A：早年(描述) 2005-01～2014-12｜2015～2016 不入段｜探索 2017-01～2021-12｜確認 2022-01～2025-08｜2025-09 起不入段（H＝250 走不完）。
    n_eff ＝ 該段主格事件的可用月數（月分群有效月數）；＜ 24 ⇒ 還沒測（〈四十九〉）。第二欄 ＝ 段內月依（月序 mod 12）分 12 組的件數與月數。
 V8 拆組（只數件數）：① a 原物料型（八業：A 的 industry_pit）vs 其他；b 毛利率年增 ＞0／≤0／不可算 ＝ 上傳日（AI1 優先、否則最早文件；researchLongPool.load_filing）
    ＜ A 日期的最新一季，單季毛利率 ＝ fs_xbrl 年初累計差分（合併 cr 優先；bigrun_monthly.load_xbrl）、缺 ⇒ fin_hist gp_q／rev_q ★；年增 ＝ 該季 − 去年同季。
    ② 甲單獨／乙單獨／甲且乙；③ 市值前 30%（pct ＞ 0.7）／後 70%；④ 前 60 日漲跌 ≥／＜ 當日母體中位（★ A−1 對 A−1−60 個日曆位置當天或之前最後有效；窗內壞根 ⇒ 不可算）；
    ⑤ H＝60、120 走得完。
 V9 重疊（seq377）：
    ① 乙 vs G1：G1 ＝ results3/panel.csv.gz（research34 原輸出，⛔ 只讀；判日 signal_pos ＝ 本件 A−1、閘為 research34 閘）rev_hi24 為真的列；以（代號, 期別）比，
       期別限 G1 有的範圍：本件過閘的乙（逐期狀態，非只起點）中 G1 也為真的比例、G1 列中為本件乙的比例；本件 hi24 狀態（＝ G1 定義）對 G1 的一致率（資料口徑差）；
       轉強起點事件中 G1 為真的比例。①′ 同式、期別限 2017-01 起（research34 只讀 revenue_hist 2015-01 起 ⇒ G1 的 24 月新高 2017-01 起才可能為真）。
    ② 轉強起點 vs 營量／營飆：營量 v1 訊號 ＝ resultsN17/sig_edc6f/and_signals.csv.gz（AND 訊號；訊號日 ＝ pos，主窗資料 edc6f）；
       營飆 v1 訊號 ＝ 同表且進場日前一日（entry_pos−1，通常即訊號日）0050 還原收盤 ＞ 200 日均（rerun17.regime_mask；＝ researchYL_integrate 營飆 v1 閘原式）；★ 同月 ＝ 訊號日與 A 同一曆月、同一檔；只比 2017-03～2026-08。
       報：事件（過閘去重後）中同月有營量／營飆訊號的比例；營量／營飆訊號中同月同檔為事件的比例；另報 ±1 個月。
 V10 必附：見 NOTES。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import bigrun_monthly as BM                   # noqa: E402  轉強定義（⛔ 只 import）
from backtest import researchIndMom_freq as IMF             # noqa: E402  build_panel、reg_check、entry_flag、load_pit
from backtest import researchIndMom as RIM                  # noqa: E402  build_exr
from backtest import researchTopSell_freq as TS             # noqa: E402  merged_prices
from backtest import researchLongPool as LP                 # noqa: E402  load_filing、single、qkey
from backtest import research11 as R                        # noqa: E402  limit_price
from backtest import tradability as TR                      # noqa: E402  CUT

REG_SHA = "03f8b072ecfcf67c"
OUT = "backtest/resultsRevTurn/freq"
WORK = os.path.expanduser("~/rtfwork")
PARTS = ["data/meta/industry_hist", "data/meta/industry.csv", "data/meta/stocks.csv", "data/meta/delisted.csv", "data/mops/revenue_hist",
         "data/mops/revenue", "data/mops/_changes.log", "data/early/revenue", "data/meta/fs_xbrl", "data/meta/filing_dates.csv", "data/mops/fin_hist",
         "data/universe/exright", "data/early/exright", "data/universe/otcexright"]
SHIFT_Y = 7
P_FIRST = "2004-01"
DEDUP_M = 12
HS = (60, 120, 250)
HJ = 250
SEED = 20261022
NEFF_MIN = 24
ACC = BM.ACC_UP
RAW8 = ["塑膠工業", "化學工業", "鋼鐵工業", "水泥工業", "玻璃陶瓷", "造紙工業", "橡膠工業", "油電燃氣業"]
SEGS = [("早年(描述)", "2005-01-01", "2014-12-31"), ("2015～2016(不入段)", "2015-01-01", "2016-12-31"), ("探索", "2017-01-01", "2021-12-31"),
        ("確認", "2022-01-01", "2025-08-31"), ("2025-09起(不入段)", "2025-09-01", "2099-12-31")]
AND_CSV = "backtest/resultsN17/sig_edc6f/and_signals.csv.gz"
G1_CSV = "backtest/results3/panel.csv.gz"
NOTES = ["頻率表、未算任何報酬（seq366）",
         "價量拆分依構造不可判定（月營收拆不出價與量），只報兩個代理：原物料型產業 vs 其他、毛利率年增 ＞0／≤0（代理，不是價量拆分）",
         "這是全市場事件統計，不是 4 檔小部位的表現；4 檔前瞻照跑、條件不改",
         "持有 250 日、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」；任一段 n_eff ＜ 24 ⇒ 還沒測",
         "2015～2018 下市 58 家月營收補不回（存活者偏差，seq406／411）",
         "早年上櫃 2007-07 前無價（不過閘）；2005-01～2007-06 只有上市",
         "價格面板 ＝ rerun17 H2D（edc6f，資料尾 2026-09-24）；月營收、產業、財報、exright ＝ 最新 origin/main"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True, text=True, check=True).stdout.strip()


# ═════════════ 資料（V0）═════════════
def ensure_data(sha=None):
    """最新 origin/main（或 --sha 指定；兩件同一版）⇒ ~/rtfwork/main_<sha12>/data（唯讀）＋ revpit/（load_rev_pit 用：revenue_hist ＝ early/revenue ＋ mops/revenue_hist 的符號連結）。"""
    subprocess.run(["git", "fetch", "-q", "origin"], check=False)
    sha = git("rev-parse", sha or "origin/main")
    root = os.path.join(WORK, f"main_{sha[:12]}")
    DN = os.path.join(root, "data"); MD = os.path.join(root, "revpit")
    if not os.path.isfile(os.path.join(root, ".done")):
        subprocess.run(["rm", "-rf", root], check=True); os.makedirs(root)
        ps = [p for p in PARTS if subprocess.run(["git", "cat-file", "-e", f"{sha}:{p}"]).returncode == 0]
        ar = subprocess.Popen(["git", "archive", "--format=tar", sha] + ps, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", root], stdin=ar.stdout, check=True)
        if ar.wait() != 0:
            raise SystemExit(f"⛔ git archive {sha[:12]} 失敗")
        os.makedirs(os.path.join(MD, "revenue_hist"))
        seen = set()
        for f in sorted(glob.glob(os.path.join(DN, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(DN, "mops", "revenue_hist", "*.csv"))):
            b = os.path.basename(f)
            if b in seen:
                raise SystemExit(f"⛔ 早年與 revenue_hist 檔名重複 {b}")
            seen.add(b); os.symlink(f, os.path.join(MD, "revenue_hist", b))
        if os.path.isdir(os.path.join(DN, "mops", "revenue")):
            os.symlink(os.path.join(DN, "mops", "revenue"), os.path.join(MD, "revenue"))
        else:
            os.makedirs(os.path.join(MD, "revenue"))
        if os.path.exists(os.path.join(DN, "mops", "_changes.log")):
            os.symlink(os.path.join(DN, "mops", "_changes.log"), os.path.join(MD, "_changes.log"))
        open(os.path.join(root, ".done"), "w").write(sha)
    return sha, DN, MD


# ═════════════ 轉強（V2：bigrun_monthly 原函式逐期呼叫）═════════════
def shiftp(p, y):
    return f"{int(p[:4]) + y:04d}{p[4:]}"


_RT: dict = {}


def _f(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return np.nan
    return v if np.isfinite(v) else np.nan


def _b(v):
    if isinstance(v, (bool, np.bool_)):
        return float(bool(v))
    return np.nan


def _rev_job(P):
    L2, codes, sh = _RT["L2"], _RT["codes"], _RT["shift"]
    Ps = shiftp(P, sh)
    asof = BM.pub10(Ps) + pd.Timedelta(days=1)
    res, Pr = BM.rev_metrics(L2, codes, asof, {})
    if Pr != Ps:
        raise SystemExit(f"⛔ rev_metrics 回期 {Pr} ≠ {Ps}")
    out = []
    for sid, r in res.items():
        if r.get("rev_period") != Ps:
            continue
        out.append((sid, P, _f(r["accel"]), _b(r["hi24"]), _b(r["hi24_prev"]), bool(r["up"]), bool(r["up_prev"]), _f(r["accel_prev"]),
                    _f(r["yoy"]), _f(r["mom"]), _f(r["mom_prev"]), _b(r["flag_mom2"]), str(r.get("rev_src", ""))))
    return P, out


RV_COLS = ["sid", "period", "accel", "hi24", "hi24_prev", "up", "up_prev", "accel_prev", "yoy", "mom", "mom_prev", "flag_mom2", "rev_src"]


def rev_table(MD, codes, procs, shift=SHIFT_Y, periods=None, tag="all"):
    """逐期 rev_metrics ⇒ 長表（每檔每期一列，只收該期有值者）。快取 ~/rtfwork/rv_<tag>_s<shift>.pkl。"""
    cp = os.path.join(WORK, f"rv_{tag}_s{shift}.pkl")
    if os.path.exists(cp):
        Z = pickle.load(open(cp, "rb"))
        if Z["codes"] == list(codes) and Z["MD"] == MD and (periods is None or Z["periods"] == list(periods)):
            log(f"[月營收] 讀快取 {cp}（{len(Z['RV'])} 列）")
            return Z["RV"], Z["diag"]
    t0 = time.time()
    L, diag = BM.load_rev_pit(MD)
    L = L[L["period"].str.fullmatch(r"\d{4}-\d{2}")].copy()
    L2 = L.copy(); L2["period"] = [shiftp(p, shift) for p in L2["period"]]
    allp = sorted(L["period"].unique())
    if periods is None:
        periods = [p for p in allp if p >= P_FIRST]
    _RT.update(L2=L2, codes=list(codes), shift=shift)
    rows = []
    with Pool(procs) as pool:
        for k, (P, out) in enumerate(pool.imap_unordered(_rev_job, periods, chunksize=2)):
            rows.extend(out)
            if (k + 1) % 40 == 0:
                log(f"  月營收 rev_metrics … {k + 1}／{len(periods)}｜{time.time() - t0:.0f}s")
    RV = pd.DataFrame(rows, columns=RV_COLS).sort_values(["sid", "period"]).reset_index(drop=True)
    diag = {**{k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in list(v.items())[:20]}) for k, v in diag.items()},
            "期別（呼叫）": f"{periods[0]}～{periods[-1]}（{len(periods)} 期）", "平移年": shift, "代號數": len(codes)}
    pickle.dump({"RV": RV, "diag": diag, "codes": list(codes), "MD": MD, "periods": list(periods)}, open(cp, "wb"), protocol=5)
    log(f"[月營收] rev_metrics {len(periods)} 期 ⇒ {len(RV)} 列｜{time.time() - t0:.0f}s")
    return RV, diag


def jia(RV):
    return RV["accel"].to_numpy(float) >= ACC


def yi(RV):
    return (RV["hi24"].to_numpy(float) == 1.0) & ~(RV["hi24_prev"].to_numpy(float) == 1.0)


# ═════════════ 價格（V0、V1）═════════════
def exr_table(sha, DN):
    cp = os.path.join(WORK, f"exrtab_{sha[:12]}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    fr = []
    for src, d in (("twse", "universe/exright"), ("twse", "early/exright"), ("otc", "universe/otcexright")):
        for f in sorted(glob.glob(os.path.join(DN, d, "*.csv"))):
            x = pd.read_csv(f, dtype=str)
            x["src"] = src; fr.append(x)
    X = pd.concat(fr, ignore_index=True)
    X["stock_id"] = X["stock_id"].astype(str).str.strip()
    X = X[X["stock_id"].str.fullmatch(r"\d{4}")].copy()
    X["ob"] = pd.to_numeric(X["open_base"].astype(str).str.replace(",", ""), errors="coerce")
    info = {"上市列(四碼)": int((X["src"] == "twse").sum()), "上櫃列(四碼)": int((X["src"] == "otc").sum()),
            "上市open_base有值": int(((X["src"] == "twse") & (X["ob"] > 0)).sum()), "上櫃open_base有值": int(((X["src"] == "otc") & (X["ob"] > 0)).sum())}
    T = X[X["ob"] > 0].drop_duplicates(["stock_id", "date"])
    info["同股同日重複（取第一筆）"] = int((X["ob"] > 0).sum() - len(T))
    tab = defaultdict(list)
    for s, d, ob in zip(T["stock_id"], T["date"], T["ob"]):
        tab[s].append((pd.Timestamp(d), float(ob)))
    out = {"tab": {k: sorted(v) for k, v in tab.items()}, "info": info, "sha": sha}
    pickle.dump(out, open(cp, "wb"))
    return out


_DX: dict = {}


def _dnl_job(a):
    wn, sid = a
    G = _DX[wn]; cal = G["cal"]; n0 = len(cal)
    rows = G["tab"].get(sid, [])
    fp = os.path.join(G["data"], "stocks", f"{sid}.csv")
    if not rows or not os.path.exists(fp):
        return sid, []
    raw = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "open", "high"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").reindex(cal)
    ro = np.array(pd.to_numeric(raw["open"], errors="coerce").to_numpy(float), copy=True)
    rh = np.array(pd.to_numeric(raw["high"], errors="coerce").to_numpy(float), copy=True)
    ro[~(ro > 0)] = np.nan; rh[~(rh > 0)] = np.nan
    out = []
    for d, ob in rows:
        p = int(cal.searchsorted(d))
        if p >= n0 or cal[p] != d:
            continue
        lim = 0.07 if d < TR.CUT else 0.10
        dn = bool(np.isfinite(ro[p]) and abs(ro[p] - R.limit_price(ob, False, lim)) < 1e-6 and np.isfinite(rh[p]) and rh[p] == ro[p])
        out.append((p, dn))
    return sid, out


def world_dnl(Z, wn, T, procs):
    """開盤鎖跌停：世界快取 dnl ⇒ exright 日改 open_base 判（V1）。"""
    cp = os.path.join(WORK, f"dnlx_{wn}_{T['sha'][:12]}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    part = {"主": "main", "早年": "early"}[wn]
    W = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{part}.pkl"), "rb"))
    wix = {s: k for k, s in enumerate(W["sids"])}
    if W["dnl"].shape[1] < Z["n0"]:
        raise SystemExit(f"⛔ 世界 dnl 日曆長 {W['dnl'].shape[1]} ＜ {Z['n0']}")
    DN_ = np.stack([np.asarray(W["dnl"][wix[s], :Z["n0"]], bool) for s in Z["sids"]])
    del W
    _DX[wn] = {"cal": Z["cal"], "data": Z["data"], "tab": T["tab"]}
    ix = {s: k for k, s in enumerate(Z["sids"])}
    cnt = Counter()
    with Pool(procs) as pool:
        for sid, rows in pool.imap_unordered(_dnl_job, [(wn, s) for s in Z["sids"] if s in T["tab"]], chunksize=8):
            i = ix[sid]
            for p, dn in rows:
                cnt["exright列(有日)"] += 1
                if bool(DN_[i, p]) != dn:
                    cnt["開盤鎖跌停_變"] += 1
                DN_[i, p] = dn
    X = {"DNL": DN_, "info": dict(cnt)}
    pickle.dump(X, open(cp, "wb"), protocol=5)
    return X


def prices(sha, DN, procs):
    """兩世界面板 ⇒ exright 版（UPL、BAD、DNL）⇒ 合併日曆（TopSell merged_prices 原式）＋ MC、O、DNL 同位置接上。"""
    t0 = time.time()
    T = exr_table(sha, DN)
    RIM.load_exr_table = lambda sha_=None: T              # ★ V1：只換表（上市＋上櫃）
    RIM.EXR_SHA = sha; RIM.WORK = WORK
    Zs = {}; info = {"exright表": T["info"]}
    for wn in ("早年", "主"):
        Z = IMF.build_panel(wn, procs, log)
        X = RIM.build_exr(Z, procs, log)
        Y = world_dnl(Z, wn, T, procs)
        Zx = {k: v for k, v in Z.items() if k not in ("CB", "VP")}
        Zx["UPL"] = X["UPLX"]; Zx["BAD"] = X["BADX"]; Zx["DNL"] = Y["DNL"]
        info[f"exright {wn}"] = {**X["info"]["計數"], **{f"DNL {k}": v for k, v in Y["info"].items()}}
        Zs[wn] = Zx
    Ze, Zm = Zs["早年"], Zs["主"]
    SIDS = sorted(set(Ze["sids"]) | set(Zm["sids"]))
    CAL, NE, C, BAD, G, TRD, UPL, seam, ie, im = TS.merged_prices(Ze, Zm, SIDS)
    N, NC = len(SIDS), len(CAL)
    MC = np.full((N, NC), np.nan); O = np.full((N, NC), np.nan); DNL = np.zeros((N, NC), bool)
    for i, s in enumerate(SIDS):
        if s in ie:
            j = ie[s]; MC[i, :NE] = Ze["MC"][j]; O[i, :NE] = Ze["O"][j]; DNL[i, :NE] = Ze["DNL"][j]
        if s in im:
            j = im[s]; MC[i, NE:] = Zm["MC"][j]; O[i, NE:] = Zm["O"][j]; DNL[i, NE:] = Zm["DNL"][j]
    VP = [np.flatnonzero(np.isfinite(r)) for r in C]
    CB = np.cumsum(BAD, axis=1, dtype=np.int32)
    LASTV = np.array([int(v[-1]) if len(v) else -1 for v in VP])
    PX = {"CAL": CAL, "NE": NE, "SIDS": SIDS, "ix": {s: i for i, s in enumerate(SIDS)}, "C": C, "BAD": BAD, "G": G, "TRD": TRD, "UPL": UPL, "DNL": DNL,
          "MC": MC, "O": O, "VP": VP, "CB": CB, "LASTV": LASTV, "seam": seam, "ie": ie, "im": im, "info": info,
          "main_cal": Zm["cal"], "main_data": Zm["data"], "early_data": Ze["data"]}
    log(f"[價格] 合併日曆 {CAL[0].date()}～{CAL[-1].date()}（{NC}）｜股 {N}｜接縫 {seam}｜exright {info}｜{time.time() - t0:.0f}s")
    return PX


def avail_pos(CAL, periods):
    """V3：期別 ⇒ 可用日 A（第一個日期 ＞ rev_avail 的交易日位置；超出 ⇒ len(CAL)）。"""
    return {P: int(CAL.searchsorted(BM.rev_avail(P), side="right")) for P in periods}


def back_ret(PX, i, p1, p0):
    """p1（須為有效 K 棒）對 p0 當天或之前最後有效 K 棒的漲跌；不存在、(p0', p1] 有壞根 ⇒ nan。只用 ≤ p1 的價格（分位用、⛔ 不存）。"""
    vp = PX["VP"][i]
    k1 = int(np.searchsorted(vp, p1, "right")) - 1
    if k1 < 0 or vp[k1] != p1:
        return np.nan
    k0 = int(np.searchsorted(vp, p0, "right")) - 1
    if k0 < 0 or k0 >= k1:
        return np.nan
    a = int(vp[k0])
    if PX["CB"][i, p1] - PX["CB"][i, a] > 0:
        return np.nan
    return float(PX["C"][i, p1] / PX["C"][i, a] - 1.0)


# ═════════════ 財報（V8 b；缺貨型 C7 共用）═════════════
def gm_table(DN):
    """{sid: {qk: 單季毛利率}}、來源計數。fs_xbrl 年初累計差分（cr 優先）⇒ 缺 ⇒ fin_hist gp_q／rev_q。"""
    X = BM.load_xbrl(DN, range(2013, 2027))
    fl = []
    for f in sorted(glob.glob(os.path.join(DN, "mops", "fin_hist", "*.csv"))):
        b = os.path.basename(f)[:6]
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "rev_q", "gp_q"]); x["qk"] = LP.qkey(b[:4], b[5]); fl.append(x)
    FN = pd.concat(fl).drop_duplicates(["stock_id", "qk"], keep="last")
    for c in ("rev_q", "gp_q"):
        FN[c] = pd.to_numeric(FN[c], errors="coerce")
    FNd = {s: dict(zip(g["qk"], zip(g["rev_q"], g["gp_q"]))) for s, g in FN.groupby("stock_id")}
    GM = {}; src = Counter()
    for s in set(X) | set(FNd):
        d = {}; df = X.get(s); fd = FNd.get(s, {})
        qs = set(fd) | (set(df.index) if df is not None else set())
        for q in qs:
            v = np.nan
            if df is not None:
                gp = LP.single(df["gross_profit_ytd"], q); rv = LP.single(df["revenue_ytd"], q)
                if np.isfinite(gp) and np.isfinite(rv) and rv > 0:
                    v = gp / rv; src["fs_xbrl"] += 1
            if not np.isfinite(v) and q in fd:
                rv, gp = fd[q]
                if np.isfinite(gp) and np.isfinite(rv) and rv > 0:
                    v = gp / rv; src["fin_hist"] += 1
            if np.isfinite(v):
                d[q] = float(v)
        GM[s] = d
    return GM, dict(src)


def filing_pos(DN, CAL):
    """{sid: [(上傳日, qk, 可判位置)]}（上傳日升冪）：可判位置 ＝ 第一個日期 ＞ 上傳日（日）的交易日（AI1 優先、否則最早文件；seq352）。"""
    AV, SRC = LP.load_filing(DN)
    out = defaultdict(list)
    for (s, q), t in AV.items():
        d = pd.Timestamp(t).normalize()
        out[s].append((d, int(q), int(CAL.searchsorted(d, side="right"))))
    for s in out:
        out[s].sort()
    return dict(out), Counter(SRC.values())


def gm_yoy_at(GM, FP, sid, date):
    """date 之前（上傳日 ＜ date）已公告的最新一季：毛利率年增（該季 − 去年同季）；不可算 ⇒ nan。"""
    best = -1
    for d, q, _ in FP.get(sid, []):
        if d < date and q > best:
            best = q
    if best < 0:
        return np.nan, -1
    g = GM.get(sid, {})
    a, b = g.get(best, np.nan), g.get(best - 4, np.nan)
    return (a - b if np.isfinite(a) and np.isfinite(b) else np.nan), best


# ═════════════ 小工具 ═════════════
def segof(d):
    s = str(pd.Timestamp(d).date())
    for nm, a, b in SEGS:
        if a <= s <= b:
            return nm
    return "2004(不入段)"


def mnum(p):
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def qd(a):
    a = np.asarray([x for x in a if x is not None and np.isfinite(x)], float)
    if not len(a):
        return None
    return {"n": int(len(a)), "中位": float(np.median(a)), "p25": float(np.percentile(a, 25)), "p75": float(np.percentile(a, 75)),
            "min": float(a.min()), "max": float(a.max())}


def ranks(vals):
    s = pd.Series(vals)
    pct = s.rank(pct=True, method="average").to_numpy(float)
    return pct


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sha", default=None, help="資料版本（預設最新 origin/main；兩件同跑時傳同一個）")
    a = ap.parse_args()
    t0 = time.time()
    out = os.path.join(WORK, "dry_rt") if a.limit else OUT
    os.makedirs(out, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DN, MD = ensure_data(a.sha); log(f"[資料] origin/main {sha}｜{DN}")
    PX = prices(sha, DN, a.procs)
    CAL, SIDS, ix, NC = PX["CAL"], PX["SIDS"], PX["ix"], len(PX["CAL"])
    CEND = NC - 1
    codes = SIDS
    if a.limit:
        rng0 = np.random.default_rng(SEED)
        codes = sorted(rng0.choice(SIDS, a.limit, replace=False).tolist())
    RV, rdiag = rev_table(MD, codes, a.procs, tag=("all" if not a.limit else f"dry{a.limit}"))
    log(f"[月營收] {rdiag}")
    pit = IMF.load_pit(DN)
    GM, gsrc = gm_table(DN); FP, fsrc = filing_pos(DN, CAL)
    log(f"[財報] 毛利率來源 {gsrc}｜上傳時戳來源 {dict(fsrc)}")
    periods = sorted(RV["period"].unique())
    APOS = avail_pos(CAL, periods)
    RV["i"] = RV["sid"].map(ix).fillna(-1).astype(int)
    RV["A"] = RV["period"].map(APOS).astype(int)
    RV["甲"] = jia(RV); RV["乙"] = yi(RV)
    RV["起點"] = RV["up"] & ~RV["up_prev"]
    RV["上期不可判"] = ~np.isfinite(RV["accel_prev"].to_numpy(float)) & ~np.isfinite(RV["hi24_prev"].to_numpy(float))
    G = PX["G"]

    def gate_ok(i, A):
        return bool(i >= 0 and 1 <= A <= CEND and G[i, A - 1])
    RV["過閘"] = [gate_ok(i, A_) for i, A_ in zip(RV["i"], RV["A"])]
    # ── 起點 ⇒ 事件（V4）
    ST = RV[RV["起點"]].copy()
    reasons = Counter()
    ev = []
    last_kept = {}
    for r in ST.itertuples(index=False):
        if r.i < 0:
            reasons["非面板（非四碼普通股或 K 棒 ＜260）"] += 1; continue
        if r.A > CEND or r.A < 1:
            reasons["可用日超出日曆"] += 1; continue
        if not r.過閘:
            reasons["閘外（500張／pit_valid，判日 A−1）"] += 1; continue
        lk = last_kept.get(r.sid)
        if lk is not None and mnum(r.period) - mnum(lk) < DEDUP_M:
            reasons["12個月內非第一次"] += 1; continue
        last_kept[r.sid] = r.period
        ev.append(r)
    EV = pd.DataFrame(ev)
    log(f"[事件] 起點 {len(ST)} ⇒ 過閘去重 {len(EV)}｜剔除 {dict(reasons)}")
    # ── 每期：分位母體、配對池（V5）
    feat = {}           # (i, P) -> (dec, ter, mcpct, r60flag) ；只存分位
    medr60 = {}
    for P in periods:
        A_ = APOS[P]
        if not (1 <= A_ <= CEND):
            continue
        p1 = A_ - 1
        U = np.flatnonzero(G[:, p1])
        if not len(U):
            continue
        p12 = int(CAL.searchsorted(CAL[p1] - pd.DateOffset(months=12), side="right")) - 1
        mc = PX["MC"][U, p1]; mc = np.where(np.isfinite(mc) & (mc > 0), mc, np.nan)
        r12 = np.array([back_ret(PX, int(i), p1, p12) if p12 >= 0 else np.nan for i in U])
        r60 = np.array([back_ret(PX, int(i), p1, p1 - 60) if p1 - 60 >= 0 else np.nan for i in U])
        okm = np.isfinite(mc); okr = np.isfinite(r12); ok6 = np.isfinite(r60)
        pm = np.full(len(U), np.nan); pr = np.full(len(U), np.nan)
        if okm.any():
            pm[okm] = ranks(mc[okm])
        if okr.any():
            pr[okr] = ranks(r12[okr])
        med = float(np.median(r60[ok6])) if ok6.any() else np.nan
        medr60[P] = med
        for k, i in enumerate(U):
            dec = int(math.ceil(pm[k] * 10)) if np.isfinite(pm[k]) else -1
            ter = int(math.ceil(pr[k] * 3)) if np.isfinite(pr[k]) else -1
            r6 = (bool(r60[k] >= med) if (np.isfinite(r60[k]) and np.isfinite(med)) else None)
            feat[(int(i), P)] = (dec, ter, float(pm[k]) if np.isfinite(pm[k]) else np.nan, r6)
    log(f"[分位] 期 {len(medr60)}｜股期 {len(feat)}｜{time.time() - t0:.0f}s")

    def ind_at(sid, A_):
        v, s = pit.at(sid, CAL[A_])
        return (v or ""), s
    pool = defaultdict(list)
    eflag_memo = {}

    def eflag(i, A_):
        k = (i, A_)
        if k not in eflag_memo:
            eflag_memo[k] = IMF.entry_flag(PX, i, A_, A_ + 1) if A_ + 1 <= CEND else "e超出資料尾"
        return eflag_memo[k]
    NONUP = RV[(~RV["up"]) & RV["過閘"] & (RV["i"] >= 0)]
    for r in NONUP.itertuples(index=False):
        f = feat.get((r.i, r.period))
        if f is None or f[0] < 0 or f[1] < 0:
            continue
        ind, _ = ind_at(r.sid, r.A)
        if not ind:
            continue
        if eflag(r.i, r.A) != "保留":
            continue
        pool[(r.period, ind, f[0], f[1])].append(r.sid)
    log(f"[配對池] 格 {len(pool)}｜{time.time() - t0:.0f}s")
    # ── 逐事件（依 A、代號序；V5 抽樣）
    rng = np.random.default_rng(SEED)
    EV = EV.sort_values(["A", "sid"]).reset_index(drop=True)
    rows = []
    for r in EV.itertuples(index=False):
        i, A_, P = int(r.i), int(r.A), r.period
        e = A_ + 1
        fl = eflag(i, A_)
        ind, isrc = ind_at(r.sid, A_)
        f = feat.get((i, P), (-1, -1, np.nan, None))
        cand = sorted(pool.get((P, ind, f[0], f[1]), [])) if (ind and f[0] >= 0 and f[1] >= 0) else []
        if fl == "保留" and cand:
            pick = sorted(rng.choice(cand, 3, replace=False).tolist()) if len(cand) >= 3 else cand
        else:
            pick = []
        why = ("e不可進場:" + fl) if fl != "保留" else ("無產業" if not ind else ("市值不可算" if f[0] < 0 else ("前12月不可算" if f[1] < 0 else ("" if cand else "同格無候選"))))
        gy, gq = gm_yoy_at(GM, FP, r.sid, CAL[A_])
        row = {"sid": r.sid, "_i": i, "期別": P, "A": str(CAL[A_].date()), "e": (str(CAL[e].date()) if e <= CEND else ""), "_A": A_, "段": segof(CAL[A_]),
               "年": CAL[A_].year, "月": f"{CAL[A_].year}-{CAL[A_].month:02d}", "甲": bool(r.甲), "乙": bool(r.乙),
               "上期不可判": bool(r.上期不可判), "產業": ind, "產業來源": isrc, "原物料型": ind in RAW8, "市值十分位": f[0], "前12月三分位(配對特徵)": f[1],
               "市值前30%": (bool(f[2] > 0.7) if np.isfinite(f[2]) else None), "前60日≥中位": f[3],
               "毛利率年增>0": (bool(gy > 0) if np.isfinite(gy) else None), "毛利率季": (LP.qlabel(gq) if gq >= 0 else ""),
               "進場": fl, "候選數": len(cand), "對照": " ".join(pick), "對照數": len(pick), "配到": bool(pick), "配不到原因": why,
               "下市(資料尾前≥5日)": bool(PX["LASTV"][i] < CEND - 5)}
        for H in HS:
            x = e + H
            row[f"H{H}走得完"] = bool(x <= CEND)
            if x <= CEND:
                row[f"H{H}窗內遇壞根"] = bool(PX["CB"][i, x] - PX["CB"][i, e] > 0)
                row[f"H{H}窗內遇下市"] = bool(PX["LASTV"][i] < x and CEND - PX["LASTV"][i] >= 5)
                cb = 0
                for s in pick:
                    j = ix[s]
                    cb += int(PX["CB"][j, x] - PX["CB"][j, e] > 0 or (PX["LASTV"][j] < x and CEND - PX["LASTV"][j] >= 5))
                row[f"H{H}對照遇壞根或下市"] = cb
            else:
                row[f"H{H}窗內遇壞根"] = None; row[f"H{H}窗內遇下市"] = None; row[f"H{H}對照遇壞根或下市"] = None
        row["主格"] = bool(row["配到"] and row[f"H{HJ}走得完"])
        rows.append(row)
    E = pd.DataFrame(rows)
    log(f"[配對] 事件 {len(E)}｜可進場 {int((E['進場'] == '保留').sum())}｜配到 {int(E['配到'].sum())}｜主格 {int(E['主格'].sum())}｜{time.time() - t0:.0f}s")
    # ── 段表（V7）
    FR = []; G12 = []
    for nm, x_, y_ in SEGS:
        d = E[E["段"] == nm]; m = d[d["主格"]]
        ne = int(m["月"].nunique())
        allm = sorted({f"{dd.year}-{dd.month:02d}" for dd in CAL if x_ <= str(dd.date()) <= y_})
        FR.append({"段": nm, "可用日區間": f"{x_}～{y_}", "段內月數": len(allm), "事件(過閘去重)": len(d), "e可進場": int((d["進場"] == "保留").sum()),
                   "配到": int(d["配到"].sum()), "配對成功率(可進場中)": (float(d.loc[d["進場"] == "保留", "配到"].mean()) if (d["進場"] == "保留").any() else np.nan),
                   "對照1檔": int((d["對照數"] == 1).sum()), "對照2檔": int((d["對照數"] == 2).sum()), "對照3檔": int((d["對照數"] == 3).sum()),
                   "候選數中位": (float(d.loc[d["進場"] == "保留", "候選數"].median()) if (d["進場"] == "保留").any() else np.nan),
                   "H60走得完": int(d["H60走得完"].sum()), "H120走得完": int(d["H120走得完"].sum()), "H250走得完": int(d["H250走得完"].sum()),
                   "主格事件": len(m), "主格月數=n_eff": ne, "n_eff≥24": ne >= NEFF_MIN, "每月事件中位": (float(m.groupby("月").size().median()) if len(m) else np.nan),
                   "主格窗內遇壞根": int((m["H250窗內遇壞根"] == True).sum()), "主格窗內遇下市": int((m["H250窗內遇下市"] == True).sum()),  # noqa: E712
                   "主格對照遇壞根或下市(檔)": int(m["H250對照遇壞根或下市"].fillna(0).sum()),
                   "含下市股比例(主格)": (float(m["下市(資料尾前≥5日)"].mean()) if len(m) else np.nan),
                   "甲占比(主格)": (float(m["甲"].mean()) if len(m) else np.nan), "乙占比(主格)": (float(m["乙"].mean()) if len(m) else np.nan),
                   "上期不可判(主格)": int(m["上期不可判"].sum())})
        if len(m) and nm in ("探索", "確認", "早年(描述)"):
            m0 = mnum(allm[0])
            gg = m.groupby(m["月"].map(lambda s: (mnum(s) - m0) % 12))
            for g, dd in gg:
                G12.append({"段": nm, "組(月序mod12)": int(g), "件數": len(dd), "月數": int(dd["月"].nunique()),
                            "月": " ".join(sorted(dd["月"].unique()))})
    FR = pd.DataFrame(FR)
    # 分年
    YR = []
    stp = RV[RV["起點"]].copy(); stp["年"] = [CAL[A_].year if 1 <= A_ <= CEND else -1 for A_ in stp["A"]]
    for y, d in E.groupby("年"):
        s_ = stp[stp["年"] == y]
        m = d[d["主格"]]
        YR.append({"年(可用日)": int(y), "起點(全部)": len(s_), "起點中在面板": int((s_["i"] >= 0).sum()), "事件(過閘去重)": len(d),
                   "e可進場": int((d["進場"] == "保留").sum()), "配到": int(d["配到"].sum()), "主格": len(m),
                   "甲占比": float(d["甲"].mean()), "乙占比": float(d["乙"].mean()), "甲且乙": int((d["甲"] & d["乙"]).sum()),
                   "含下市股比例": float(d["下市(資料尾前≥5日)"].mean()), "原物料型": int(d["原物料型"].sum())})
    YR = pd.DataFrame(YR)
    # 拆組（V8）
    SP = []
    for nm in ("早年(描述)", "探索", "確認"):
        m = E[(E["段"] == nm) & E["主格"]]

        def add(grp, lab, mask):
            dd = m[mask]
            SP.append({"段": nm, "拆組": grp, "組": lab, "主格事件": len(dd), "月數": int(dd["月"].nunique())})
        add("①a 原物料型代理（代理，不是價量拆分）", "原物料型八業", m["原物料型"])
        add("①a 原物料型代理（代理，不是價量拆分）", "其他產業", ~m["原物料型"])
        add("①b 毛利率年增代理", "毛利率年增>0", m["毛利率年增>0"] == True)  # noqa: E712
        add("①b 毛利率年增代理", "毛利率年增≤0（≈轉嫁型）", m["毛利率年增>0"] == False)  # noqa: E712
        add("①b 毛利率年增代理", "毛利率不可算", m["毛利率年增>0"].isna())
        add("② 甲乙", "甲單獨", m["甲"] & ~m["乙"])
        add("② 甲乙", "乙單獨", ~m["甲"] & m["乙"])
        add("② 甲乙", "甲且乙", m["甲"] & m["乙"])
        add("③ 市值", "前30%", m["市值前30%"] == True)  # noqa: E712
        add("③ 市值", "後70%", m["市值前30%"] == False)  # noqa: E712
        add("④ 前60日", "≥當日中位", m["前60日≥中位"] == True)  # noqa: E712
        add("④ 前60日", "＜當日中位", m["前60日≥中位"] == False)  # noqa: E712
        add("④ 前60日", "不可算", m["前60日≥中位"].isna())
        d2 = E[(E["段"] == nm) & E["配到"]]
        for H in (60, 120):
            dd = d2[d2[f"H{H}走得完"]]
            SP.append({"段": nm, "拆組": "⑤ 天數", "組": f"H{H}（配到且走得完）", "主格事件": len(dd), "月數": int(dd["月"].nunique())})
    SP = pd.DataFrame(SP)
    # ── 重疊（V9）
    OV = []
    # ① 乙 vs G1
    g1 = pd.read_csv(G1_CSV, dtype={"stock_id": str}, usecols=["stock_id", "period", "gate", "rev_hi24"])
    g1 = g1[g1["gate"].astype(str) == "True"]
    g1p = sorted(g1["period"].unique()); lo_, hi_ = g1p[0], g1p[-1]
    G1S = set(zip(g1.loc[g1["rev_hi24"].astype(str) == "True", "stock_id"], g1.loc[g1["rev_hi24"].astype(str) == "True", "period"]))
    G1ALL = set(zip(g1["stock_id"], g1["period"]))
    rvw = RV[(RV["period"] >= lo_) & (RV["period"] <= hi_) & RV["過閘"]]
    YI = set(zip(rvw.loc[rvw["乙"], "sid"], rvw.loc[rvw["乙"], "period"]))
    H24 = set(zip(rvw.loc[rvw["hi24"] == 1.0, "sid"], rvw.loc[rvw["hi24"] == 1.0, "period"]))
    BOTH = set(zip(rvw["sid"], rvw["period"])) & G1ALL
    yi_b = {k for k in YI if k in BOTH}; h24_b = {k for k in H24 if k in BOTH}; g1_b = {k for k in G1S if k in BOTH}
    evw = E[(E["期別"] >= lo_) & (E["期別"] <= hi_)]
    evk = set(zip(evw["sid"], evw["期別"]))
    OV.append({"比較": "① 乙 vs G1", "範圍": f"期別 {lo_}～{hi_}；兩邊都過閘且都有列的（代號,期別）{len(BOTH)}",
               "本件乙列": len(yi_b), "G1列": len(g1_b), "交集": len(yi_b & g1_b),
               "乙中G1也為真": (len(yi_b & g1_b) / len(yi_b) if yi_b else np.nan), "G1中為乙(首創)": (len(yi_b & g1_b) / len(g1_b) if g1_b else np.nan),
               "本件hi24狀態列": len(h24_b), "hi24∩G1": len(h24_b & g1_b),
               "hi24中G1也為真(口徑一致率)": (len(h24_b & g1_b) / len(h24_b) if h24_b else np.nan), "G1中hi24也為真": (len(h24_b & g1_b) / len(g1_b) if g1_b else np.nan),
               "轉強起點事件(同期別範圍)": len(evk), "事件中G1為真": (len(evk & G1S) / len(evk) if evk else np.nan)})
    # ①′ 同上、期別限 2017-01 起（research34 只讀 revenue_hist 2015-01 起 ⇒ 24 月新高 2017-01 才可能有值；本件含早年營收，2015-12～2016-12 會有、G1 不會有）
    lo2 = max(lo_, "2017-01")
    yi2 = {k for k in yi_b if k[1] >= lo2}; h2 = {k for k in h24_b if k[1] >= lo2}; g2 = {k for k in g1_b if k[1] >= lo2}; ev2 = {k for k in evk if k[1] >= lo2}
    OV.append({"比較": "①′ 乙 vs G1（期別 2017-01 起）", "範圍": f"期別 {lo2}～{hi_}；同上",
               "本件乙列": len(yi2), "G1列": len(g2), "交集": len(yi2 & g2),
               "乙中G1也為真": (len(yi2 & g2) / len(yi2) if yi2 else np.nan), "G1中為乙(首創)": (len(yi2 & g2) / len(g2) if g2 else np.nan),
               "本件hi24狀態列": len(h2), "hi24∩G1": len(h2 & g2),
               "hi24中G1也為真(口徑一致率)": (len(h2 & g2) / len(h2) if h2 else np.nan), "G1中hi24也為真": (len(h2 & g2) / len(g2) if g2 else np.nan),
               "轉強起點事件(同期別範圍)": len(ev2), "事件中G1為真": (len(ev2 & G1S) / len(ev2) if ev2 else np.nan)})
    # ② 轉強起點 vs 營量／營飆
    from backtest import rerun17 as RR
    import backtest.data as D
    D.DATA = RR.H2D
    mcal = D.load_calendar()
    if not (len(mcal) == len(PX["main_cal"]) and (mcal == PX["main_cal"]).all()):
        raise SystemExit("⛔ H2D 日曆 ≠ 面板主世界日曆")
    reg = RR.regime_mask(RR.load_bench(mcal))
    AN = pd.read_csv(AND_CSV, dtype={"sid": str}, usecols=["sid", "pos", "entry_pos"])
    n_gap = int((AN["entry_pos"] != AN["pos"] + 1).sum())          # 訊號日後停牌 ⇒ 進場日延後（照報；訊號月用 pos、閘用 entry_pos−1 ＝ researchYL_integrate 原式）
    AN = AN[(AN["pos"] < len(mcal)) & (AN["entry_pos"] <= len(mcal))].copy()
    AN["d"] = mcal[AN["pos"].to_numpy()]; AN["m"] = [f"{d.year}-{d.month:02d}" for d in AN["d"]]
    AN["飆"] = reg[AN["entry_pos"].to_numpy() - 1]
    w0, w1 = "2017-03", "2026-08"
    AN = AN[(AN["m"] >= w0) & (AN["m"] <= w1)]
    evm = E[(E["月"] >= w0) & (E["月"] <= w1)]
    EVK = set(zip(evm["sid"], evm["月"]))

    def mshift(m, k):
        n = mnum(m) + k
        return f"{n // 12}-{n % 12 + 1:02d}"
    for lab, sub in (("營量 v1（AND 訊號）", AN), ("營飆 v1（AND ∧ 0050＞200MA）", AN[AN["飆"]])):
        SK = set(zip(sub["sid"], sub["m"]))
        SK1 = {(s, mshift(m, k)) for s, m in SK for k in (-1, 0, 1)}
        EK1 = {(s, mshift(m, k)) for s, m in EVK for k in (-1, 0, 1)}
        OV.append({"比較": f"② 轉強起點 vs {lab}", "範圍": f"可用日月／訊號日月 {w0}～{w1}（AND 進場日≠訊號日＋1 的列 {n_gap}，照用）", "事件": len(EVK), "訊號(檔月)": len(SK),
                   "事件中同月有訊號": (len(EVK & SK) / len(EVK) if EVK else np.nan), "事件中±1月有訊號": (len(EVK & SK1) / len(EVK) if EVK else np.nan),
                   "訊號中同月同檔為事件": (len(SK & EVK) / len(SK) if SK else np.nan), "訊號中±1月為事件": (len(SK & EK1) / len(SK) if SK else np.nan)})
        E[f"同月{lab[:2]}訊號"] = [((s, m) in SK) if (w0 <= m <= w1) else None for s, m in zip(E["sid"], E["月"])]
    E["G1同期"] = [((s, p) in G1S) if (lo_ <= p <= hi_) else None for s, p in zip(E["sid"], E["期別"])]
    OV = pd.DataFrame(OV)
    # 甲乙重疊（等價自查）
    EQ = {}
    for nm in ("早年(描述)", "探索", "確認"):
        m = E[(E["段"] == nm) & E["主格"]]
        if len(m):
            EQ[nm] = {"主格": len(m), "甲且乙÷主格": float((m["甲"] & m["乙"]).mean()), "只甲": float((m["甲"] & ~m["乙"]).mean()), "只乙": float((~m["甲"] & m["乙"]).mean()),
                      "配對成功率": float(E[(E["段"] == nm) & (E["進場"] == "保留")]["配到"].mean()),
                      "候選數分佈": qd(E[(E["段"] == nm) & (E["進場"] == "保留")]["候選數"].astype(float))}
    # 輸出
    cols_drop = ["_i", "_A"]
    E.drop(columns=cols_drop).to_csv(os.path.join(out, "events.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    FR.to_csv(os.path.join(out, "freq_段.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    SP.to_csv(os.path.join(out, "split.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(G12).to_csv(os.path.join(out, "group12.csv"), index=False, encoding="utf-8-sig")
    OV.to_csv(os.path.join(out, "overlap.csv"), index=False, encoding="utf-8-sig")
    st_all = RV[RV["起點"]]
    J = {"性質": "營收轉強驗證 seq2 頻率表（⛔ 未算任何報酬）", "登錄": f"台股策略線 seq2 sha {REG_SHA}", "裁定": "seq447 §三",
         "origin/main": sha, "價格面板": {"主": PX["main_data"], "早年": PX["early_data"]}, "接縫": PX["seam"], "exright": PX["info"],
         "月營收": rdiag, "毛利率來源": gsrc, "上傳時戳來源": dict(fsrc), "乾跑": bool(a.limit), "乾跑股數": a.limit,
         "起點": {"全部": int(len(st_all)), "上期不可判": int(st_all["上期不可判"].sum()), "剔除": dict(reasons), "過閘去重事件": int(len(E))},
         "期別×股 列數": int(len(RV)), "轉強(up)列": int(RV["up"].sum()), "甲列": int(RV["甲"].sum()), "乙列": int(RV["乙"].sum()),
         "段": FR.to_dict("records"), "等價自查": EQ, "重疊": OV.to_dict("records"), "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1],
         "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


def jdef(o):
    if hasattr(o, "item"):
        v = o.item()
        return None if isinstance(v, float) and not np.isfinite(v) else v
    return str(o)


if __name__ == "__main__":
    main()
