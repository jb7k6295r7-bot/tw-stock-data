# -*- coding: utf-8 -*-
"""被公開收購／經營權變動／私募 事件層描述 seq2【頻率表・乾跑】（台股策略線 登錄 sha 41a4f93d8210932e，2026-10-22 04:58；裁定 seq441 發號（描述、不計 N）、
seq443 §四 核 seq2、seq448 §三 E2 主表改 v1c（71 筆；12 個月內第一次且不與 E1 重疊 51 筆）、v1b（76 筆）只當敏感度描述）——回測線計算子代理。
⛔ 只數事件、剔除、配對可行性、各窗走得完比例、n_eff、重疊；⛔ 不讀、不算、不存任何報酬（seq366）。
   用到的價格只有 ≤ 判日 T 的還原收盤（前 12 月漲跌只用來分五分位、⛔ 不存數值）與 T 的市值（只存 ≤10 億／＞10 億組別）；
   判日之後只用「有沒有有效 K 棒／壞根／最後 K 棒位置」旗標。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices）、researchIndMom_freq（reg_check）、researchIndRev_prereg（okcode）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_freq [--procs 2] [--dry（輸出 ~/tkowork/dry）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_freq_check [--dry]
輸出 backtest/resultsTakeover/freq/：freq.json、freq.csv（組×段）、by_year.csv、drop.csv、equiv.csv、events.csv.gz（逐事件旗標，⛔ 無報酬、無價格）、run.log

═══ 讀法（U 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 U0 資料：tw-stock-data 最新 origin/main（researchRevTurn_freq.ensure_data 原樣，git archive 到 ~/rtfwork/main_<sha12>，唯讀）；
    事件表 ＝ 同一 sha 的 data/meta/takeover_events/takeover_events.csv（git show，唯讀）。
    價格 ＝ researchRevTurn_freq.prices 原樣：兩世界面板（主 rerun17 H2D 2015-01-05～2026-09-24、早年 eotc 2004-02-11～2014-12-31；四碼普通股
    UG.gate3(GATE_V2)、含已下市、load_bars ≥ 260 根）接成合併日曆；壞根 ＝ 缺口 ≥ 5 日（seq335）∪ 價格斷點 ∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2，
    exright 版（上市 exright＋early exright＋上櫃 otcexright 的 open_base，seq412）。⚠ 價格資料尾 2026-09-24 ＜ 事件表尾 ⇒ 之後的事件「超出價格資料尾」。
    pit_valid（板期／興櫃排除）＝ 世界快取 ~/rluwork/world_<part>.pkl 的 pv（面板 G 用的同一份），接到合併日曆。⭐ 500 張閘不設（登錄 §二）。
 U1 組（登錄 §六）：
    E1 ＝ class E1 ∧ followup 0 ∧ first12m 1（★ 登錄 §二「同公司 12 個月內同類只取第一次」；〔另一讀法：§六 的 125 筆全收〕⇒ 另報「E1含非首次」）。
       分組 outcome：success／fail／空白（⚠ 空白≠仍在進行，照標）。
    E2 ＝ v1c（＝ origin/main 表 class E2）∧ first12m 1 ∧ overlap_e1 0（主表 51）；「E2含重疊」＝ first12m 1（67）。
       v1b（敏感度描述）＝ 同一 sha 的 curated/takeover_events/build.py 複製到 ~/tkowork 只把規則 A 改回 v1b（第三條 本公司股東.{0,30}超過.{0,20}三分之一、
       不排除 通知已取得／低於／減少／降低；build.py 文件寫明 v1b→v1c 只改這兩處）重建；first12m、overlap_e1 由 build.py 原式算。⚠ 須得 76 筆，否則照報。
    E3 ＝ class E3 ∧ first12m 1（1,875）；分組 with_reduction 1／0（有／無減資）。策略投資人分組 ⛔ 本表不做（待 seq3）。
    共同分組：市值 ★ ＝ 判日 T 的面板市值（原始收盤 × 股數、ffill）≤ 10 億 ／ ＞ 10 億。
 U2 事件日 day0：★ 重訊時戳 time ≥ 13:30:00（收盤後）⇒ date 之後第一個交易日；否則 date 當天或之後第一個交易日（date 非交易日同）；time 空白 ★ 當盤中。
    E1 主 ＝ 最早公開日：有 acq_date ⇒ min(day0(被收購方 date, time), day0(acq_date, 收購方時戳))；★ 事件表的 acq_date 沒有時戳 ⇒ 以 build.py 同一規則
    （他代號、前 30 天內、主旨「公開收購.{0,12}<簡稱>」、非後續公告）在同一 sha 的 data/mops/news 重找收購方那則重訊，取 acq_date 當天最早的 time
    （重找的日期須等於表的 acq_date，不等照報）〔另一讀法：只用日期、acq_date 當天算 day0 ⇒ 差異件數照報〕；E1對照 ＝ 只用被收購方 day0。
    判日 T ＝ day0 − 1（合併日曆位置）。
 U3 可接價格（依序，每筆只記第一個原因）：非四碼普通股 → 早於價格日曆（day0 ≤ 2004-02-11）→ 超出價格資料尾 → 不在價格面板（gate3／不足 260 根）
    → 首根 K 棒晚於判日（⭐ 上市櫃前發的重訊、或早年上櫃無價；登錄 §六「自然掉」）→ 判日後已無 K 棒（下市後）→ pit_valid 否（板期／興櫃）→ 保留。
    ★ 判日 T 停牌（無 K 棒）不剔除，用 T 當天或之前最後一根有效 K 棒當基準（件數照報「判日停牌」）。
 U4 窗（登錄 §三；交易日、合併日曆位置）：前 [−30,−1]、當 [0,+1]、後 [+2,+20]、[+2,+60]、[+2,+250]。窗 [a,b] 的基準 ＝ day0＋a−1、窗尾 ＝ day0＋b。
    狀態（依序）：超出資料尾（窗尾 ＞ 價格資料尾）→ 起點無 K 棒（基準當天或之前沒有有效 K 棒）→ 窗內壞根（(基準最後有效, min(窗尾, 最後 K 棒)] 有壞根）
    → 下市／長停截斷（最後 K 棒 ＜ 窗尾；⭐ 登錄「被收購成功而下市：下市前最後收盤出場」⇒ 照報筆數，正式跑當走得完處理）→ 走得完。
    「走得完比例」分母 ＝ 可接價格事件；另報「走得完＋截斷」。
 U5 配對（登錄 §三：同月、市值最接近、前 12 個月報酬同五分位、前後 12 月無同類事件）；⛔ 只取配對對象與它的窗狀態，不取任何配對後價格：
    ★「同月」讀成同一判日 T 的橫斷面〔另一讀法：公告月月底橫斷面〕。橫斷面 ＝ 面板股 ∧ pit_valid[T] ∧ T 有有效 K 棒 ∧ 市值[T] ＞ 0 ∧ 前 12 月報酬可算。
    前 12 月報酬 ＝ c[T] ÷ c[a] − 1，a ＝ (T 日期 − 12 曆月) 當天或之前最後一根有效 K 棒，(a, T] 無壞根（IndMom I3 同式）；事件公司 T 停牌 ⇒ 以 U3 基準 K 棒代 c[T]。
    ★ 五分位切點以該橫斷面計（事件公司若自己在橫斷面內就含）；池 ＝ 橫斷面 − 事件公司 − 同類（★ 同 class 表內任一列，E1 含後續公告；E2 依所用版本）
    [d − 12 曆月, d ＋ 12 曆月] 內有事件的公司 ∧ 同五分位；★ 市值最接近 ＝ |市值差| 最小（同值取代號小）。
    事件公司前 12 月不可算 ⇒「配對不可算」（多為上市未滿 12 個月）；池空 ⇒「配對失敗」。另報 d ＋ 12 月超過事件表尾（2026-10-21）的筆數（向後只看到表尾）。
    「雙方走得完」＝ 事件與配對公司同一窗都「走得完」（★ 截斷不算）。
 U6 段 ★ 依公告日 date：早年 2005-01-01～2016-12-31（描述）｜探索 2017-03-01～2021-12-31｜確認 2022-01-01～資料尾；另報全期（2005～）與全表（含 2005 前）。
    n_eff ＝ min(事件數, 有事件的公告月數)（★ 登錄「CI 依公告月分群」）；＜ 30 照標「事件少」。描述件、⛔ 不計 N。
 U7 已下市 ＝ 代號不在 origin/main stocks.csv 或其 last_seen 早於最晚 last_seen 10 天以上（SEO 頻率表 S7 同式）。
 U8 seq377 等價／退化：E1 最早日 vs 被收購方日（day0 相同比例、差幾天）；E2 vs E1 重疊（自算 ±60 天 vs 表的 overlap_e1）、E2 v1c vs v1b；
    E3 vs E1／E2 同代號 ±60、±365 天；E3 有／無減資比例；E1 outcome 各組件數；配對公司重複使用率；各組 n_eff ＜ 30。
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import io
import json
import os
import pickle
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check（⛔ 只 import）
from backtest import researchRevTurn_freq as RT             # noqa: E402  ensure_data、prices（⛔ 只 import）
from backtest import researchIndRev_prereg as PRE           # noqa: E402  okcode（⛔ 只 import）

REG_SHA = "41a4f93d8210932e"
OUT = "backtest/resultsTakeover/freq"
WORK = os.path.expanduser("~/tkowork")
EVP = "data/meta/takeover_events/takeover_events.csv"
BUILD = "curated/takeover_events/build.py"
CUT = "13:30:00"
WINS = {"前[-30,-1]": (-30, -1), "當[0,+1]": (0, 1), "後[+2,+20]": (2, 20), "後[+2,+60]": (2, 60), "後[+2,+250]": (2, 250)}
SEGS = [("早年", "2005-01-01", "2016-12-31"), ("探索", "2017-03-01", "2021-12-31"), ("確認", "2022-01-01", "2099-12-31"),
        ("全期(2005～)", "2005-01-01", "2099-12-31"), ("全表", "1990-01-01", "2099-12-31")]
NEFF_MIN = 30
MC_SPLIT = 1e9
DROP_ORDER = ["非四碼普通股", "早於價格日曆", "超出價格資料尾", "不在價格面板", "首根K棒晚於判日", "判日後已無K棒", "pit_valid否", "保留"]
W_ORDER = ["超出資料尾", "起點無K棒", "窗內壞根", "下市長停截斷", "走得完"]
NOTES = ["描述，不是選股規則（登錄 §四）", "事件少（E1、E2 各段 n_eff ＜ 30）", "被收購方報酬受收購價壓住（登錄 §四；本表不算報酬）", "台灣文獻只讀到摘要（登錄 §一）",
         "頻率表、未算任何報酬（seq366）", "價格面板資料尾 2026-09-24（rerun17 H2D）；事件表、exright、stocks.csv ＝ 最新 origin/main",
         "news 市場別是現在市場 ⇒ 上市櫃前發的重訊無價自然掉（U3「首根K棒晚於判日」）",
         "E3 是私募股權決議全體，分不出策略投資人（待 seq3）；E2 只涵蓋公司股東取得 1/3 以上，個人入主抓不到",
         "人工抽查正確率（資料庫 README）：E1 98%（第二輪）、E3 96%（第二輪）、E2 v1c 嚴格 72%／寬鬆 100%（修後 46 則）"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True, check=True).stdout


# ═════════════ 事件表（U1）═════════════
def load_table(sha):
    return pd.read_csv(io.BytesIO(git("show", f"{sha}:{EVP}")), dtype=str, keep_default_na=False)


def load_build(sha, tag, patch_v1b):
    """同一 sha 的 build.py 複製到 ~/tkowork/build_<tag>_<sha12>/（唯讀來源；輸出全在該夾）。patch_v1b ⇒ 規則 A 改回 v1b。回（輸出表路徑, 模組）。"""
    d = os.path.join(WORK, f"build_{tag}_{sha[:12]}")
    cp = os.path.join(d, "takeover_events.csv")
    os.makedirs(d, exist_ok=True)
    src = os.path.join(d, f"tko_build_{tag}.py")
    if not os.path.exists(src):
        open(src, "wb").write(git("show", f"{sha}:{BUILD}"))
    spec = importlib.util.spec_from_file_location(f"tko_build_{tag}", src)
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    M.REPO = os.getcwd(); M.OUT = cp; M.OUT_E2 = os.path.join(d, "e2_candidates.csv")
    if patch_v1b:
        M.E2_A[2] = re.compile(r"本公司股東.{0,30}超過.{0,20}三分之一")
        M.E2_A_EXC = re.compile(r"(?!)")
    if os.path.isfile(os.path.join(d, ".done")):
        return cp, M
    argv = sys.argv
    sys.argv = ["build", "--ref", sha]
    try:
        M.main()
    finally:
        sys.argv = argv
    open(os.path.join(d, ".done"), "w").write(sha)
    return cp, M


def acq_times(sha, M, e1):
    """U2：E1 主事件的收購方重訊時戳（build.py acq_date 同一規則重找）⇒ {(sid, date): (重找 acq_date, 當天最早 time)}。"""
    yrs = sorted({int(x[:4]) for x in e1["date"]} | {int(x[:4]) - 1 for x in e1["date"]})
    tko = []
    for y in yrs:
        p = subprocess.run(["git", "show", f"{sha}:data/mops/news/{y}.csv"], capture_output=True)
        if p.returncode != 0:
            continue
        x = pd.read_csv(io.BytesIO(p.stdout), dtype=str, keep_default_na=False)
        x = x[x["market"].isin(["sii", "otc"])].copy()
        x["s"] = x["subject"].map(lambda t: re.sub(r"\s+", "", t))
        tko.append(x[x["s"].str.contains("公開收購", regex=False)])
    T = pd.concat(tko, ignore_index=True); T["d"] = pd.to_datetime(T["date"])
    out = {}
    for _, r in e1.iterrows():
        d0 = pd.Timestamp(r["date"]); nm = M.short(r.get("name")); sid = r["stock_id"]
        if len(nm) < 2:
            out[(sid, r["date"])] = ("", ""); continue
        g = T[(T["stock_id"] != sid) & ((d0 - T["d"]).dt.days.between(0, 30))]
        pat = re.compile("公開收購.{0,12}" + re.escape(nm))
        g = g[[bool(pat.search(t)) and not M.E1_FU.search(t) for t in g["s"]]]
        if len(g) == 0:
            out[(sid, r["date"])] = ("", ""); continue
        ad = g["date"].min()
        out[(sid, r["date"])] = (ad, g.loc[g["date"] == ad, "time"].min())
    return out


# ═════════════ 價格（U0）═════════════
def price_panel(sha, DN, procs):
    PX = RT.prices(sha, DN, procs)
    CAL, NE, SIDS = PX["CAL"], PX["NE"], PX["SIDS"]; N, NC = len(SIDS), len(CAL)
    PV = np.ones((N, NC), bool)
    for part, lo, hi, idx in (("early", 0, NE, PX["ie"]), ("main", NE, NC, PX["im"])):
        W = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{part}.pkl"), "rb"))
        pv = np.asarray(W["pv"], bool)
        if pv.shape[1] < hi - lo:
            raise SystemExit(f"⛔ world_{part} pv 日曆長 {pv.shape[1]} ＜ {hi - lo}")
        wix = {s: k for k, s in enumerate(W["sids"])}
        for i, s in enumerate(SIDS):
            if s in idx and s in wix:
                PV[i, lo:hi] = pv[wix[s], :hi - lo]
        del W, pv
    valid = np.isfinite(PX["C"])
    LV = np.where(valid, np.arange(NC)[None, :], -1).astype(np.int32)
    np.maximum.accumulate(LV, axis=1, out=LV)
    PX["PV"] = PV; PX["LV"] = LV
    PX["FIRSTV"] = np.array([int(v[0]) if len(v) else NC for v in PX["VP"]])
    return PX


def day0_of(CAL, date, tm):
    NC = len(CAL)
    d = pd.Timestamp(date)
    p = int(CAL.searchsorted(d, "left"))
    if p < NC and CAL[p] == d and tm and tm >= CUT:
        p += 1
    return p


def walk(PX, i, p0, a, b):
    NC = len(PX["CAL"]); base = p0 + a - 1; end = p0 + b
    if end >= NC:
        return "超出資料尾"
    if base < 0 or PX["LV"][i, base] < 0:
        return "起點無K棒"
    bv = int(PX["LV"][i, base]); last = int(PX["LASTV"][i])
    if last <= base:
        return "下市長停截斷"
    hi = min(end, last)
    if PX["CB"][i, hi] - PX["CB"][i, bv] > 0:
        return "窗內壞根"
    if last < end:
        return "下市長停截斷"
    return "走得完"


def xsec(PX, T, memo):
    """T 橫斷面：idx、市值、前 12 月報酬（⛔ 只在記憶體、不存）、五分位切點。"""
    if T in memo:
        return memo[T]
    CAL = PX["CAL"]; C = PX["C"]
    a = int(CAL.searchsorted(CAL[T] - pd.DateOffset(months=12), side="right")) - 1
    M = np.flatnonzero(PX["PV"][:, T] & np.isfinite(C[:, T]) & (np.nan_to_num(PX["MC"][:, T]) > 0))
    if a < 0 or len(M) == 0:
        memo[T] = (np.array([], int), np.array([]), np.array([]), None); return memo[T]
    pa = PX["LV"][M, a]
    ok = pa >= 0
    M, pa = M[ok], pa[ok]
    ok = (PX["CB"][M, T] - PX["CB"][M, pa]) == 0
    M, pa = M[ok], pa[ok]
    r = C[M, T] / C[M, pa] - 1.0
    mc = PX["MC"][M, T]
    qr = np.quantile(r, [0.2, 0.4, 0.6, 0.8]) if len(r) >= 10 else None
    memo[T] = (M, mc, r, qr)
    return memo[T]


def own_r12(PX, i, T):
    CAL = PX["CAL"]
    bv = int(PX["LV"][i, T])
    a = int(CAL.searchsorted(CAL[T] - pd.DateOffset(months=12), side="right")) - 1
    if bv < 0 or a < 0:
        return np.nan
    pa = int(PX["LV"][i, a])
    if pa < 0 or PX["CB"][i, bv] - PX["CB"][i, pa] > 0:
        return np.nan
    return PX["C"][i, bv] / PX["C"][i, pa] - 1.0


# ═════════════ 逐事件 ═════════════
def process(units, PX, alive, cls_dates, tail_ev, memo):
    CAL = PX["CAL"]; NC = len(CAL); ix = PX["ix"]
    rows = []
    for u in units:
        s = u["sid"]; d = pd.Timestamp(u["date"]); p0 = u["p0"]
        row = dict(u); row.update({"已下市": s not in alive, "day0": "", "T": "", "st": "", "判日停牌": False, "市值組": "", "r12五分位": "",
                                   "配對": "", "配對sid": "", "池候選數": np.nan, "後12月超表尾": bool(d + pd.DateOffset(months=12) > tail_ev)})
        row.pop("p0", None)
        for w in WINS:
            row[f"窗{w}"] = ""; row[f"配窗{w}"] = ""
        st = None
        if not PRE.okcode(s):
            st = "非四碼普通股"
        elif p0 <= 0:
            st = "早於價格日曆"
        elif p0 >= NC:
            st = "超出價格資料尾"
        elif s not in ix:
            st = "不在價格面板"
        else:
            i = ix[s]; T = p0 - 1
            row["day0"] = str(CAL[p0].date()); row["T"] = str(CAL[T].date())
            if PX["FIRSTV"][i] > T:
                st = "首根K棒晚於判日"
            elif PX["LASTV"][i] < T:
                st = "判日後已無K棒"
            elif not PX["PV"][i, T]:
                st = "pit_valid否"
            else:
                st = "保留"
        row["st"] = st
        if st != "保留":
            rows.append(row); continue
        row["判日停牌"] = not bool(np.isfinite(PX["C"][i, T]))
        mc0 = PX["MC"][i, T]
        row["市值組"] = "" if not (np.isfinite(mc0) and mc0 > 0) else ("≤10億" if mc0 <= MC_SPLIT else "＞10億")
        for w, (a, b) in WINS.items():
            row[f"窗{w}"] = walk(PX, i, p0, a, b)
        # 配對
        M, mc, r, qr = xsec(PX, T, memo)
        r0 = own_r12(PX, i, T)
        if qr is None or not np.isfinite(r0) or not (np.isfinite(mc0) and mc0 > 0):
            row["配對"] = "配對不可算"
        else:
            q0 = int(np.searchsorted(qr, r0, "right")); row["r12五分位"] = q0 + 1
            qj = np.searchsorted(qr, r, "right")
            lo = np.datetime64(d - pd.DateOffset(months=12)); hi = np.datetime64(d + pd.DateOffset(months=12))
            cd = cls_dates[u["類"]]
            cand = []
            for k in np.flatnonzero(qj == q0):
                j = int(M[k])
                if j == i:
                    continue
                v = cd.get(PX["SIDS"][j])
                if v is not None:
                    kk = np.searchsorted(v, lo, "left")
                    if kk < len(v) and v[kk] <= hi:
                        continue
                cand.append((abs(float(mc[k]) - float(mc0)), PX["SIDS"][j], j))
            row["池候選數"] = len(cand)
            if not cand:
                row["配對"] = "配對失敗"
            else:
                _, js, j = min(cand)
                row["配對"] = "配對成功"; row["配對sid"] = js
                for w, (a, b) in WINS.items():
                    row[f"配窗{w}"] = walk(PX, j, p0, a, b)
        rows.append(row)
    return rows


def segof(date, x, y):
    return (date >= x) & (date <= y)


def summarize(sub):
    n_tab = len(sub)
    ok = sub[sub["st"] == "保留"]
    n = len(ok); mon = ok["date"].str[:7]; nm = int(mon.nunique()); ne = min(n, nm)
    g = {"表列數": n_tab, "可接價格": n, "可接比例": round(n / n_tab, 4) if n_tab else None, "相異公司(可接)": int(ok["sid"].nunique()),
         "公告月數": nm, "n_eff": ne, "n_eff<30": bool(ne < NEFF_MIN), "已下市比例(可接)": round(float(ok["已下市"].mean()), 4) if n else None,
         "判日停牌": int(ok["判日停牌"].sum()), "市值≤10億": int((ok["市值組"] == "≤10億").sum()), "市值＞10億": int((ok["市值組"] == "＞10億").sum())}
    for k in DROP_ORDER[:-1]:
        g[f"掉_{k}"] = int((sub["st"] == k).sum())
    mc = Counter(ok["配對"])
    g["配對成功"] = mc.get("配對成功", 0); g["配對失敗"] = mc.get("配對失敗", 0); g["配對不可算"] = mc.get("配對不可算", 0)
    g["配對成功率"] = round(g["配對成功"] / n, 4) if n else None
    pc = ok["池候選數"].dropna().to_numpy(float)
    g["池候選數中位"] = float(np.median(pc)) if len(pc) else None
    g["池候選數0"] = int((pc == 0).sum())
    g["後12月超表尾"] = int(ok["後12月超表尾"].sum())
    for w in WINS:
        c = Counter(ok[f"窗{w}"])
        g[f"{w}_走得完"] = c.get("走得完", 0)
        g[f"{w}_走得完比例"] = round(c.get("走得完", 0) / n, 4) if n else None
        g[f"{w}_截斷"] = c.get("下市長停截斷", 0)
        g[f"{w}_走得完＋截斷比例"] = round((c.get("走得完", 0) + c.get("下市長停截斷", 0)) / n, 4) if n else None
        g[f"{w}_壞根"] = c.get("窗內壞根", 0); g[f"{w}_起點無K"] = c.get("起點無K棒", 0); g[f"{w}_超出資料尾"] = c.get("超出資料尾", 0)
        both = ok[(ok[f"窗{w}"] == "走得完") & (ok[f"配窗{w}"] == "走得完")]
        g[f"{w}_雙方走得完"] = len(both)
        g[f"{w}_雙方n_eff"] = min(len(both), int(both["date"].str[:7].nunique()))
    return g


GROUPS = {
    "E1": lambda E: E[(E["類"] == "E1") & (E["臂"] == "最早日") & (E["first12m"] == "1")],
    "E1_success": lambda E: E[(E["類"] == "E1") & (E["臂"] == "最早日") & (E["first12m"] == "1") & (E["outcome"] == "success")],
    "E1_fail": lambda E: E[(E["類"] == "E1") & (E["臂"] == "最早日") & (E["first12m"] == "1") & (E["outcome"] == "fail")],
    "E1_空白": lambda E: E[(E["類"] == "E1") & (E["臂"] == "最早日") & (E["first12m"] == "1") & (E["outcome"] == "")],
    "E1對照(被收購方日)": lambda E: E[(E["類"] == "E1") & (E["臂"] == "被收購方日") & (E["first12m"] == "1")],
    "E1含非首次(125)": lambda E: E[(E["類"] == "E1") & (E["臂"] == "最早日")],
    "E2(v1c主)": lambda E: E[(E["類"] == "E2") & (E["臂"] == "v1c") & (E["first12m"] == "1") & (E["overlap_e1"] == "0")],
    "E2含重疊(v1c)": lambda E: E[(E["類"] == "E2") & (E["臂"] == "v1c") & (E["first12m"] == "1")],
    "E2(v1b敏感度)": lambda E: E[(E["類"] == "E2b") & (E["first12m"] == "1") & (E["overlap_e1"] == "0")],
    "E2含重疊(v1b敏感度)": lambda E: E[(E["類"] == "E2b") & (E["first12m"] == "1")],
    "E3": lambda E: E[(E["類"] == "E3")],
    "E3_有減資": lambda E: E[(E["類"] == "E3") & (E["with_reduction"] == "1")],
    "E3_無減資": lambda E: E[(E["類"] == "E3") & (E["with_reduction"] == "0")],
}
MAIN_GROUPS = ["E1", "E1對照(被收購方日)", "E2(v1c主)", "E2含重疊(v1c)", "E2(v1b敏感度)", "E3", "E3_有減資", "E3_無減資"]


def near(A, B, days):
    Bd = defaultdict(list)
    for s, d in zip(B["sid"], pd.to_datetime(B["date"])):
        Bd[s].append(d)
    return int(sum(any(abs((d - x).days) <= days for x in Bd.get(s, ())) for s, d in zip(A["sid"], pd.to_datetime(A["date"]))))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    out = os.path.join(WORK, "dry") if a.dry else OUT
    os.makedirs(out, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    reg = IMF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DN, MD = RT.ensure_data(None)
    log(f"[資料] origin/main {sha}｜{DN}")
    ev = load_table(sha)
    tail_ev = pd.Timestamp(ev["date"].max())
    log(f"[事件表] {len(ev)} 列 {ev['date'].min()}～{ev['date'].max()}｜{dict(Counter(ev['class']))}")
    b1, MB = load_build(sha, "v1b", True)
    evb = pd.read_csv(b1, dtype=str, keep_default_na=False)
    e2b = evb[evb["class"] == "E2"].copy()
    log(f"[v1b 重建] E2 {len(e2b)} 列（應 76）｜first12m {int((e2b['first12m'] == '1').sum())}｜overlap_e1 {int((e2b['overlap_e1'] == '1').sum())}"
        f"｜E1/E3 與 main 表相同：{evb[evb['class'] != 'E2'].reset_index(drop=True).equals(ev[ev['class'] != 'E2'].reset_index(drop=True))}")
    st = pd.read_csv(os.path.join(DN, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st["last_seen"], errors="coerce"); alive = set(st.loc[ls >= ls.max() - pd.Timedelta(days=10), "stock_id"])
    PX = price_panel(sha, DN, a.procs)
    CAL = PX["CAL"]
    log(f"[價格] {CAL[0].date()}～{CAL[-1].date()}（{len(CAL)}）｜股 {len(PX['SIDS'])}｜{time.time() - t0:.0f}s")
    i2330 = PX["ix"].get("2330")
    if i2330 is not None:
        log(f"[市值單位檢查] 2330 於 {CAL[-1].date()} 市值 {PX['MC'][i2330, -1]:.3e}（元）")
    # 同類日期（U5 池排除）
    def cd_of(df):
        m = defaultdict(list)
        for s, d in zip(df["stock_id"], df["date"]):
            m[s].append(np.datetime64(pd.Timestamp(d)))
        return {s: np.array(sorted(v)) for s, v in m.items()}
    cls_dates = {"E1": cd_of(ev[ev["class"] == "E1"]), "E2": cd_of(ev[ev["class"] == "E2"]), "E2b": cd_of(e2b), "E3": cd_of(ev[ev["class"] == "E3"])}
    # 單位
    units = []
    base_cols = ["first12m", "outcome", "acq_date", "with_reduction", "reduction_type", "overlap_e1", "market", "time"]

    def mk(r, cls, arm, p0, extra=None):
        u = {"類": cls, "臂": arm, "sid": r["stock_id"], "date": r["date"], "p0": p0, **{c: r[c] for c in base_cols}}
        if extra:
            u.update(extra)
        return u
    e1 = ev[(ev["class"] == "E1") & (ev["followup"] == "0")]
    AQ = acq_times(sha, MB, e1)
    aq_bad = [(k, v[0]) for (k, v), t_ad in zip(AQ.items(), e1["acq_date"]) if v[0] != t_ad]
    log(f"[acq 時戳] 重找 {sum(1 for v in AQ.values() if v[0])} 筆｜與表 acq_date 不同 {len(aq_bad)} {aq_bad[:5]}")
    for _, r in e1.iterrows():
        pt = day0_of(CAL, r["date"], r["time"])
        ad, at = AQ[(r["stock_id"], r["date"])]
        if r["acq_date"]:
            pa = day0_of(CAL, r["acq_date"], at if ad == r["acq_date"] else "")
            pa_d = int(CAL.searchsorted(pd.Timestamp(r["acq_date"]), "left"))
        else:
            pa = pa_d = pt
        pe = min(pt, pa); pe_d = min(pt, pa_d)
        ex = {"最早日提前(交易日)": int(pt - pe), "acq_time": at if r["acq_date"] else "", "日期版day0差": int(pe - pe_d)}
        units.append(mk(r, "E1", "最早日", pe, ex))
        units.append(mk(r, "E1", "被收購方日", pt, ex))
    for _, r in ev[ev["class"] == "E2"].iterrows():
        units.append(mk(r, "E2", "v1c", day0_of(CAL, r["date"], r["time"])))
    for _, r in e2b.iterrows():
        units.append(mk(r, "E2b", "v1b", day0_of(CAL, r["date"], r["time"])))
    for _, r in ev[(ev["class"] == "E3") & (ev["first12m"] == "1")].iterrows():
        units.append(mk(r, "E3", "全體", day0_of(CAL, r["date"], r["time"])))
    log(f"[單位] {dict(Counter((u['類'], u['臂']) for u in units))}｜time 空白 {sum(1 for u in units if not u['time'])}")
    memo = {}
    rows = process(units, PX, alive, cls_dates, tail_ev, memo)
    E = pd.DataFrame(rows)
    E["date_dt"] = pd.to_datetime(E["date"])
    log(f"[逐事件] {len(E)} 列｜橫斷面 {len(memo)} 個｜{time.time() - t0:.0f}s")
    # 頻率表
    FREQ = []; J = {"性質": "公開收購／經營權變動／私募 seq2 頻率表乾跑（⛔ 未讀、未算任何報酬；描述件、不計 N）", "登錄": f"台股策略線 seq2 sha {REG_SHA}",
                    "裁定": "seq441 發號、seq443 §四 核 seq2、seq448 §三 E2 主表 v1c", "origin/main": sha,
                    "事件表": {"列數": int(len(ev)), "期間": [ev["date"].min(), ev["date"].max()], "class": dict(Counter(ev["class"]))},
                    "v1b重建": {"E2列數": int(len(e2b)), "first12m": int((e2b["first12m"] == "1").sum()),
                              "first12m∧不重疊": int(((e2b["first12m"] == "1") & (e2b["overlap_e1"] == "0")).sum())},
                    "價格日曆": [str(CAL[0].date()), str(CAL[-1].date())], "注意": NOTES, "段": {}}
    for sg, x, y in SEGS:
        x_, y_ = pd.Timestamp(x), pd.Timestamp(y)
        J["段"][sg] = {}
        for gname, f in GROUPS.items():
            sub = f(E); sub = sub[segof(sub["date_dt"], x_, y_)]
            g = summarize(sub)
            J["段"][sg][gname] = g
            FREQ.append({"段": sg, "組": gname, **g})
            if gname in ("E1", "E2(v1c主)", "E3", "E3_有減資", "E3_無減資"):
                for mg in ("≤10億", "＞10億"):
                    s2 = sub[(sub["st"] == "保留") & (sub["市值組"] == mg)]       # 市值分組只對可接價格（表列數＝可接）
                    FREQ.append({"段": sg, "組": f"{gname}_市值{mg}", **summarize(s2)})
        log(f"[段 {sg}] " + "｜".join(f"{gn} 可接 {J['段'][sg][gn]['可接價格']} n_eff {J['段'][sg][gn]['n_eff']} 雙方+250 {J['段'][sg][gn]['後[+2,+250]_雙方走得完']}"
                                     for gn in MAIN_GROUPS))
    # 每年
    BY = []
    E["年"] = E["date"].str[:4].astype(int)
    for gname in MAIN_GROUPS + ["E1_success", "E1_fail", "E1_空白"]:
        sub = GROUPS[gname](E)
        for yy, s in sub.groupby("年"):
            ok = s[s["st"] == "保留"]
            BY.append({"組": gname, "公告年": yy, "表列數": len(s), "可接價格": len(ok), **{f"掉_{k}": int((s["st"] == k).sum()) for k in DROP_ORDER[:-1]},
                       "配對成功": int((ok["配對"] == "配對成功").sum()), "後[+2,+250]_走得完": int((ok["窗後[+2,+250]"] == "走得完").sum()),
                       "後[+2,+250]_雙方走得完": int(((ok["窗後[+2,+250]"] == "走得完") & (ok["配窗後[+2,+250]"] == "走得完")).sum())})
    # 剔除總表
    DROP = []
    for gname in MAIN_GROUPS:
        c = Counter(GROUPS[gname](E)["st"])
        DROP.append({"組": gname, **{k: c.get(k, 0) for k in DROP_ORDER}})
    # 等價／退化（U8）
    EQ = []
    e1m = GROUPS["E1"](E); gap = e1m["最早日提前(交易日)"].astype(int)
    EQ.append({"項": "E1 最早日 vs 被收購方日：day0 相同", "值": int((gap == 0).sum()), "分母": len(e1m)})
    EQ.append({"項": "E1 最早日提前 1 日", "值": int((gap == 1).sum()), "分母": len(e1m)})
    EQ.append({"項": "E1 最早日提前 ≥2 日", "值": int((gap >= 2).sum()), "分母": len(e1m), "註": f"最大 {int(gap.max()) if len(gap) else None}"})
    EQ.append({"項": "E1 有 acq_date", "值": int((e1m["acq_date"] != "").sum()), "分母": len(e1m)})
    dd = e1m["日期版day0差"].astype(int)
    EQ.append({"項": "E1 最早日：收購方時戳版 vs 只用日期版 day0 不同（另一讀法）", "值": int((dd != 0).sum()), "分母": len(e1m),
               "註": f"時戳版晚 1 日 {int((dd == 1).sum())}；有 acq 且收購方盤後 {int(((e1m['acq_date'] != '') & (e1m['acq_time'].fillna('').astype(str) >= CUT)).sum())}"})
    e1all = E[(E["類"] == "E1") & (E["臂"] == "最早日")]
    for nm_, B_ in (("E2含重疊(v1c)", GROUPS["E2含重疊(v1c)"](E)), ("E2含重疊(v1b敏感度)", GROUPS["E2含重疊(v1b敏感度)"](E))):
        h = near(B_, e1all, 60)
        EQ.append({"項": f"{nm_} 與 E1 主事件同代號 ±60 天（自算）", "值": h, "分母": len(B_), "註": f"表 overlap_e1＝1：{int((B_['overlap_e1'] == '1').sum())}"})
    v1c = E[(E["類"] == "E2")]; v1b = E[(E["類"] == "E2b")]
    kc = set(zip(v1c["sid"], v1c["date"])); kb = set(zip(v1b["sid"], v1b["date"]))
    EQ.append({"項": "E2 v1c ⊂ v1b（同代號同日）", "值": len(kc & kb), "分母": len(kc), "註": f"v1b 多出 {sorted(kb - kc)}；v1c 多出 {sorted(kc - kb)}"})
    e3 = GROUPS["E3"](E)
    for nm_, B_ in (("E1", e1all), ("E2(v1c全)", v1c)):
        for days in (60, 365):
            EQ.append({"項": f"E3 與 {nm_} 同代號 ±{days} 天", "值": near(e3, B_, days), "分母": len(e3)})
    EQ.append({"項": "E3 有減資", "值": int((e3["with_reduction"] == "1").sum()), "分母": len(e3),
               "註": str(dict(Counter(e3.loc[e3["with_reduction"] == "1", "reduction_type"])))})
    for gname in ("E3_有減資", "E3_無減資"):
        ok = GROUPS[gname](E); ok = ok[ok["st"] == "保留"]
        for w in WINS:
            EQ.append({"項": f"{gname} {w} 窗內壞根（減資本身是價格斷點 ⇒ 構造性退化檢查）", "值": int((ok[f"窗{w}"] == "窗內壞根").sum()), "分母": len(ok)})
    EQ.append({"項": "E1 outcome", "值": None, "分母": len(e1m), "註": str(dict(Counter(e1m["outcome"].replace("", "空白"))))})
    for gname in MAIN_GROUPS:
        sub = GROUPS[gname](E); m = sub[sub["配對"] == "配對成功"]
        EQ.append({"項": f"{gname} 配對公司重複使用", "值": int(len(m) - m["配對sid"].nunique()), "分母": len(m), "註": f"相異配對公司 {m['配對sid'].nunique()}"})
        EQ.append({"項": f"{gname} 配對公司本身也是同組事件公司", "值": int(m["配對sid"].isin(set(sub["sid"])).sum()), "分母": len(m)})
    J["seq377等價"] = EQ
    J["剔除總表"] = DROP
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(out, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DROP).to_csv(os.path.join(out, "drop.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EQ).to_csv(os.path.join(out, "equiv.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(out, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        E.drop(columns=["date_dt", "年"]).to_csv(fh, index=False)
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
