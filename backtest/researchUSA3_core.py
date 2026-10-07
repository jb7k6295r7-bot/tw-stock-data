# -*- coding: utf-8 -*-
"""USREG-A3（A3-1～8、A3-10～17，16 件）共用底座：讀檔快取、基準、判定標籤、組合引擎包裝、條件出場必報量。

判準：美股策略線 登錄 USREG-A3A4 seq1（sha 0dc16d3267725d7c）＋ seq2（sha bc0927fed5996fd4）；裁定 seq318（發號）、seq319（疑點 16 條裁示）、
      seq316（只 S&P 400 與合併兩者都過才合格）、seq308（條件出場主臂）、seq242（組合層預設）、seq311（飆股＝網格中位）。
開跑前清單（⛔ 照它、不改）：backtest/researchUSA34_prep.py、backtest/resultsUSA34/prep/PREP_REPORT.md（補讀法 P1～P20、退化格 61 列）。

⛔⛔ 私有資料：us-stock-data 是私有 repo ⇒ resultsUSA34/A3/ 只放彙總（平均、CI、件數、比例、判語、sha）；
   逐日價格、逐筆事件、權益曲線、成交紀錄一律寫 ~/us_work/a3/（repo 外）並列 sha。

═══ A3 共同讀法（執行者寫死於 2026-10-07 11:43（台北）；寫死前 ⛔ 沒看任何 A3 報酬）═══
 C1 窗、段（＝ P1）：判定窗 2016-01-04～2026-09-30；凡原登錄有「探索／確認」兩段 ⇒ 探索 2016-01-04～2021-12-31、確認 2022-01-03～2026-09-30。
    裁定 seq319 Q1：美股沒有早年段 ⇒ 判定 ＝ 探索段挑、確認段判；原文「兩段取較嚴」⇒ 只看確認段；結果句標「缺早年段」（原登錄有早年段者）。
 C2 挑格在【合併】欄的探索段做（同一套規則一次挑出、兩欄同一格判）；⛔ 不在只 S&P 400 欄另挑（避免兩欄各挑各的＝兩條規則）。
 C3 三欄（＝ P2）：事件層 ＝ 事件日當天歸屬（只 S&P 400 ＝ m400、只 S&P 500 ＝ m500、合併 ＝ 全部）；
    組合層 ＝ 三組各自的組合回測（候選 ＝ 訊號日當天在該欄的指數）；持有中移出母體照抱（seq214 R4 E0）。
 C4 標籤（seq316＋seq319）：合格 ＝ 只 S&P 400 與合併都過；只有合併過 ⇒「事後擴母體」（最多暫定、只進前瞻紀錄）；合併沒過 ⇒ 不合格；
    依構造不能判 ⇒ 不可判定。組合層「另列」照 USREG-A2 W1b W7。只 S&P 500 ＝ 描述、⛔ 不判。
 C5 組合層預設（seq242）：8 槽等權、抽籤種子 102000＋r（200 顆）、T＋1 開盤、成本 0.05%（敏感度 0.02、0.10%）、無停損停利、
    引擎 research11.simulate_mtm（cash_mode zero、tradable＝有效 K 棒、delist＝tradability.delist_status）＝ USREG-A2 W1b 同一套。
    判準 ＝ ^SP500TR 同窗（段）：年化中位 ＞ 基準年化 且 年化÷|回落| ≥ 基準比值 ⇒ 合格；只前者 ⇒ 另列；否則不合格（researchUSW1b.label）。
 C6 條件出場必報（seq308、seq318）：⛔ 不設最長天數；窗（段）尾仍持有 ⇒ 尾日收盤結算、件數必報；持有天數分佈（平均、中位、p10、p90、最長）必報；
    「離頂多近」＝ 每筆 出場價 ÷ 持有期間（進場日～出場日）最高收盤 − 1 的中位（越接近 0 越貼近頂）；⛔ 不拿抱幾天當評價。
    固定 {20, 60, 120, 240} 日只描述（xpos ＝ entry＋H−1 收盤；超過窗尾 ⇒ 窗尾結算，同 W1b W4）。
 C7 事件層：超額 ＝ 原件式子，基準 ＝ 合併母體等權（MB.ew_us，A2 A2 同式）；統計 ＝ researchM.summ／verdict（曆月群集 CI、20 日區段 n_eff）。
 C8 |ret|＞50% 敏感度：S&P 400 未確認 23 列當硬斷點（A2 D6），碰到的事件／訊號剔除、另報判語。
 C9 存活者偏差：S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體 ⇒ 結果偏向存活股、偏樂觀（A2.coverage 必寫）。
 C10 每件結果句：標「想法來自台股（多數在台股不合格）」；原登錄有早年段者再標「缺早年段」。
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
import time
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
import researchM as TWM

READ_TS = "2026-10-07 11:43（台北）"
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A3")
WORK = os.path.expanduser("~/us_work/a3")
W0, W1 = A2.WINDOW
EXP_END = pd.Timestamp("2021-12-31")
CONF0 = pd.Timestamp("2022-01-03")
COLS = ("合併", "只400", "只500")
COST = U.COST_ROUNDTRIP
COST_SENS = U.COST_SENSITIVITY
N_SLOTS, SEED0, NSEED = 8, 102000, 200
FIXH = (20, 60, 120, 240)
RULE = "A3"
IDEA = "想法來自台股（多數在台股不合格）"
NO_EARLY = "缺早年段"
# 原登錄有早年段者（PREP_REPORT §四「早年段」拿掉的件）
EARLY_ITEMS = ("A3-3", "A3-6", "A3-7", "A3-8", "A3-10", "A3-11", "A3-12", "A3-14", "A3-15", "A3-16")
SURV = "S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體 ⇒ 結果偏向存活股、偏樂觀"
REG = {"登錄": "USREG-A3A4 seq1 sha 0dc16d3267725d7c＋seq2 sha bc0927fed5996fd4", "裁定": "seq318 發號、seq319 疑點裁示、seq316 兩母體",
       "開跑前清單": "researchUSA34_prep.py＋resultsUSA34/prep/PREP_REPORT.md（P1～P20）"}


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jdump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_jdef)


def _jdef(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp,)):
        return str(x.date())
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


# ═════════════ 日曆、母體 ═════════════
def setup_cal():
    """→ cal（從 MB.CAL0 起）、w0、w1、sp（探索段最後一天的位置）、c0（確認段第一天）。"""
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
    return t[:lim] if lim else t


# ═════════════ 每檔讀檔（快取）═════════════
_G = {}


def _init(d):
    _G.update(d)


def load_stock(t):
    """→ dict：O H L C（還原、無效 K 棒 NaN）、V（Yahoo 拆股調整量）、valid、pb（硬斷點）、bars、m5、m4、member、f50、spanst、
    closes（ffill 收盤，給引擎）、opens（有效且 >0 的開盤）。⛔ 只讀檔、不算任何報酬。"""
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A = RU.prep(df, cal)
    if len(A["bars"]) < 30:
        return None
    Lw = MB.low_aligned(df, cal)
    m5, m4 = A2.idx_member(t, cal)
    m5 = np.asarray(m5, bool); m4 = np.asarray(m4, bool)
    V = USX.volume_aligned(t, cal, A["valid"])
    valid = A["valid"]; O = A["O"]
    return {"t": t, "O": A["O"], "H": A["H"], "L": Lw, "C": A["C"], "V": V, "valid": valid, "pb": A["pb"], "bars": A["bars"],
            "m5": m5, "m4": m4, "member": m5 | m4, "f50": A2.flag50_pos(t, cal), "spanst": RU.span_start_array(t, cal),
            "closes": pd.Series(A["C"]).ffill().to_numpy(), "opens": np.where(valid & (np.nan_to_num(O) > 0), O, np.nan)}


def build_cache(procs=2, lim=None):
    """→ ~/us_work/a3/stocks.pkl（repo 外；⛔ 不進 repo）。"""
    os.makedirs(WORK, exist_ok=True)
    p = os.path.join(WORK, "stocks%s.pkl" % ("" if lim is None else "_lim%d" % lim))
    if os.path.exists(p):
        return p
    t0 = time.time()
    cal, w0, w1, sp, c0 = setup_cal()
    tick = tickers(lim)
    ST = {}
    with Pool(procs, initializer=_init, initargs=({"cal": cal, "w0": w0, "w1": w1},)) as pool:
        for k, r in enumerate(pool.imap(load_stock, tick, chunksize=8)):
            if r is not None:
                ST[r["t"]] = r
            if (k + 1) % 200 == 0:
                print("[cache] %d／%d %.0fs" % (k + 1, len(tick), time.time() - t0), flush=True)
    meta = {"cal": cal, "w0": w0, "w1": w1, "sp": sp, "c0": c0, "data_commit": A2.data_commit(), "n_tickers_try": len(tick)}
    pickle.dump({"meta": meta, "ST": ST}, open(p, "wb"), protocol=4)
    print("[cache] %d 檔 → %s %.0fs" % (len(ST), p, time.time() - t0), flush=True)
    return p


_CACHE = {}


def load_cache(lim=None):
    key = lim
    if key not in _CACHE:
        p = os.path.join(WORK, "stocks%s.pkl" % ("" if lim is None else "_lim%d" % lim))
        if not os.path.exists(p):
            build_cache(lim=lim)
        d = pickle.load(open(p, "rb"))
        _CACHE[key] = d
    d = _CACHE[key]
    return d["meta"], d["ST"]


def stk(d, w0, wE):
    """快取 dict ⇒ MB.Stk（硬斷點 brk、px＝開盤或退路收盤）。"""
    A = {"O": d["O"], "H": d["H"], "C": d["C"], "valid": d["valid"], "bars": d["bars"], "pb": d["pb"]}
    return MB.Stk(d["t"], A, d["L"], d["member"], d["spanst"], w0, wE)


def cnt(cs, a, b):
    return MB._cnt(cs, a, b)


# ═════════════ 基準 ═════════════
def ew_bench(ST, sids, Hs, pops=("合併",), f50_break=False):
    """事件層基準：EW_H(d) ＝ 當天在該欄指數∧有效∧開盤>0、(d, d+H] 無硬斷點的股票 PX(d+H)／O(d) − 1 等權（MB.ew_us 原式）。
    f50_break ⇒ S&P 400 未確認 |ret|>50% 列也當斷點（敏感度）。→ {(pop, H): 陣列}"""
    O = np.column_stack([ST[s]["O"] for s in sids])
    valid = np.column_stack([ST[s]["valid"] for s in sids])
    okO = valid & (np.nan_to_num(O) > 0)
    cff = np.column_stack([ST[s]["closes"] for s in sids])
    PX = np.where(okO, O, cff)
    brk = np.column_stack([ST[s]["pb"] | (ST[s]["f50"] if f50_break else False) for s in sids])
    CS = np.cumsum(brk.astype(np.int64), axis=0)
    out = {}
    for pop in pops:
        M = {"合併": np.column_stack([ST[s]["member"] for s in sids]), "只400": np.column_stack([ST[s]["m4"] for s in sids]),
             "只500": np.column_stack([ST[s]["m5"] for s in sids])}[pop]
        for H in Hs:
            out[(pop, H)] = MB.ew_us(O, okO & M, PX, CS, H)
    return out


def bench_tr(cal):
    return U.benchmark_tr("SP500TR").reindex(cal).ffill().to_numpy(float)


def bench_row(cal, a, b, arr=None):
    arr = bench_tr(cal) if arr is None else arr
    c, m = W.window_metrics(arr, a, b)
    return {"年化": c, "回落": m, "比值": c / abs(m)}


def pop_ew_level(ST, sids, pop):
    """母體等權（描述，W1b W9 同式）：每天在該欄、前一天也有收盤的股票日報酬等權（硬斷點那天不收）⇒ 水準。"""
    Cm = np.column_stack([ST[s]["closes"] for s in sids]); V = np.column_stack([ST[s]["valid"] for s in sids])
    PB = np.column_stack([ST[s]["pb"] for s in sids])
    MM = np.column_stack([ST[s]["member" if pop == "合併" else ("m4" if pop == "只400" else "m5")] for s in sids])
    with np.errstate(invalid="ignore", divide="ignore"):
        rr = Cm[1:] / Cm[:-1] - 1.0
    ok = V[1:] & V[:-1] & ~PB[1:] & np.isfinite(rr) & MM[:-1]
    ew = np.where(ok.sum(axis=1) > 0, np.where(ok, rr, 0).sum(axis=1) / np.maximum(ok.sum(axis=1), 1), 0.0)
    return np.r_[1.0, np.cumprod(1 + ew)]


# ═════════════ 判定標籤 ═════════════
def passed(res):
    return isinstance(res, str) and res.startswith("結果②")


def label_ev(r_comb, r_400, cannot=False, why=""):
    """事件層（結果①～④字樣）⇒ A3 標籤（C4）。"""
    if cannot:
        return "不可判定（{}）".format(why or "依構造")
    if passed(r_comb) and passed(r_400):
        return "合格"
    if passed(r_comb):
        return "事後擴母體"
    return "不合格"


def label_pf(lab_comb, lab_400, cannot=False, why=""):
    """組合層（合格／另列／不合格）⇒ A3 標籤（C4；另列照 W1b W7）。"""
    if cannot:
        return "不可判定（{}）".format(why or "依構造")
    order = {"合格": 2, "另列": 1, "不合格": 0}
    if lab_comb == "合格" and lab_400 == "合格":
        return "合格"
    if lab_comb == "合格":
        return "事後擴母體"
    if lab_comb == "另列":
        return "另列" if order.get(lab_400, 0) >= 1 else "事後擴母體（另列）"
    return "不合格"


def pf_label(c, m, bref):
    lab, ratio, rb = W.label(c, m, bref["年化"], bref["回落"])
    return lab, ratio, rb


def ev_summ(x, T, cal, w0, wE, blk=20, cap=None):
    """事件層統計（researchM.summ／verdict 原式）。cap 預設 ＝ ⌈(wE−w0+1)/blk⌉。"""
    if cap is None:
        cap = -(-(wE - w0 + 1) // blk)
    s = TWM.summ(x, T, cal, w0, blk=blk, cap=cap) if len(x) else {"n": 0}
    if s["n"]:
        ex, rs = TWM.verdict(s)
    else:
        ex, rs = "出口①", "—（無事件）"
    s = dict(s); s["出口"] = ex; s["結果"] = rs; s["區段上限"] = int(cap)
    return s


def gmask(idx, g):
    """idx：事件的 '400'／'500' 陣列 ⇒ 該欄遮罩。"""
    idx = np.asarray(idx)
    if g == "合併":
        return np.ones(len(idx), bool)
    return idx == ("400" if g == "只400" else "500")


# ═════════════ 組合引擎（W1b 同一套）═════════════
_S = {}


def pf_setup(ST, sids, cal, w0, w1):
    n = len(cal)
    z = np.zeros(n, bool)
    trad = {s: {"trd": ST[s]["valid"], "up_o": z, "dn_o": z, "dn_c": z} for s in sids}
    dl = TRD.delist_status(trad, cal)
    closes = {s: ST[s]["closes"] for s in sids}; opens = {s: ST[s]["opens"] for s in sids}
    _S.update(trad=trad, dl=dl, ncal=n, closes=closes, opens=opens, w0=w0, w1=w1)
    return trad, dl


def pf_sig(rows):
    """rows：list of dict(sid, entry_pos, xpos, g[, endhold]) ⇒ 引擎訊號表（依 entry_pos、sid 排序）與 endhold 對照。"""
    d = pd.DataFrame(rows)
    if len(d) == 0:
        d = pd.DataFrame(columns=["sid", "entry_pos", "xpos", "g", "endhold"])
    d = d.sort_values(["entry_pos", "sid"]).reset_index(drop=True)
    sig = pd.DataFrame({"sid": d["sid"].to_numpy(), "entry_pos": d["entry_pos"].to_numpy(int),
                        f"xpos_{RULE}": d["xpos"].to_numpy(int), f"g_{RULE}": d["g"].to_numpy(float)})
    endh = {(s, int(e)): bool(a) for s, e, a in zip(d["sid"], d["entry_pos"], d.get("endhold", pd.Series(False, index=d.index)))}
    xp = {(s, int(e)): (int(x), float(g)) for s, e, x, g in zip(d["sid"], d["entry_pos"], d["xpos"], d["g"])}
    return sig, endh, xp


def _pf_one(args):
    seed, key = args
    a = _S["arms"][key]
    R11.COST = a.get("cost", COST)
    aud = []
    try:
        out = R11.simulate_mtm(a["sig"], RULE, N_SLOTS, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                               return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero",
                               tradable=_S["trad"], delist=_S["dl"], audit=aud)
    finally:
        R11.COST = COST
    eq = np.asarray(out["equity"], float); s0, s1 = a["seg"]
    c, m = W.window_metrics(eq, s0, s1)
    r = {"key": key, "seed": seed, "cagr": c, "mdd": m, "trades": out["trades"], "slot_use": out["slot_use"],
         "delist_settled": out.get("tr_delist_settled"), "exit_delayed": out.get("tr_exit_delayed")}
    endh, xp = a["endhold"], a["xp"]; cl = _S["closes"]
    buy = {}; hold = []; nend = 0; peak = []; nsell = 0
    for x in aud:
        if x["side"] == "buy":
            buy[x["sid"]] = x["t"]
        elif x["side"] == "sell" and x["sid"] in buy:
            b = buy.pop(x["sid"]); t = int(x["t"]); hold.append(t - b); nsell += 1
            if endh.get((x["sid"], b), False) and t >= s1:
                nend += 1
            seg = cl[x["sid"]][b:t + 1]
            pk = np.nanmax(seg) if len(seg) else np.nan
            if np.isfinite(pk) and pk > 0 and np.isfinite(x["px"]):
                peak.append(float(x["px"]) / pk - 1.0)
    hold = np.asarray(hold, float); peak = np.asarray(peak, float)
    r.update({"hold_mean": float(hold.mean()) if len(hold) else np.nan, "hold_med": float(np.median(hold)) if len(hold) else np.nan,
              "hold_p10": float(np.percentile(hold, 10)) if len(hold) else np.nan, "hold_p90": float(np.percentile(hold, 90)) if len(hold) else np.nan,
              "hold_max": float(hold.max()) if len(hold) else np.nan, "n_sells": int(nsell), "n_end_hold": int(nend + len(buy)),
              "peak_gap_med": float(np.median(peak)) if len(peak) else np.nan})
    if a.get("keep_eq") and seed == SEED0:
        r["equity"] = eq
    return r


def pf_run(arms, procs=2, nseed=NSEED):
    """arms：{key: {"sig", "endhold", "xp", "seg": (s0, s1), "cost"?, "keep_eq"?}} ⇒ {key: [每顆結果]}。"""
    _S["arms"] = arms
    jobs = [(SEED0 + r, k) for k in arms for r in range(nseed)]
    res = {k: [] for k in arms}
    if procs <= 1:
        for j in jobs:
            x = _pf_one(j); res[x["key"]].append(x)
    else:
        with Pool(procs) as pool:
            for x in pool.imap_unordered(_pf_one, jobs, chunksize=4):
                res[x["key"]].append(x)
    for k in res:
        res[k].sort(key=lambda x: x["seed"])
    return res


def pf_agg(rows, bref):
    """200 顆 ⇒ 年化中位、回落中位、標籤、逐種子標籤比例、條件出場必報（C6）。"""
    if not rows:
        return {"標籤": "不可判定", "註": "無訊號"}
    c = np.array([x["cagr"] for x in rows], float); m = np.array([x["mdd"] for x in rows], float)
    cm, mm = float(np.median(c)), float(np.median(m))
    lab, ratio, rb = pf_label(cm, mm, bref)
    seedlab = [pf_label(a, b, bref)[0] for a, b in zip(c, m)]
    q = lambda k: float(np.nanmedian([x[k] for x in rows])) if any(np.isfinite(x[k]) for x in rows) else np.nan
    return {"年化中位": cm, "回落中位": mm, "比值": ratio, "基準年化": bref["年化"], "基準回落": bref["回落"], "基準比值": rb, "標籤": lab,
            "年化p10": float(np.percentile(c, 10)), "年化p90": float(np.percentile(c, 90)),
            "逐種子標籤比例": {k: float(np.mean([y == k for y in seedlab])) for k in ("合格", "另列", "不合格")},
            "交易數中位": float(np.median([x["trades"] for x in rows])), "槽位使用率中位": float(np.median([x["slot_use"] for x in rows])),
            "持有天數_平均（逐種子中位）": q("hold_mean"), "持有天數_中位（逐種子中位）": q("hold_med"),
            "持有天數_p10": q("hold_p10"), "持有天數_p90": q("hold_p90"),
            "最長持有（200 顆最大）": float(np.nanmax([x["hold_max"] for x in rows])) if any(np.isfinite(x["hold_max"]) for x in rows) else np.nan,
            "窗尾仍持有件數（逐種子中位）": float(np.median([x["n_end_hold"] for x in rows])),
            "窗尾仍持有件數（範圍）": [int(min(x["n_end_hold"] for x in rows)), int(max(x["n_end_hold"] for x in rows))],
            "離頂距離中位（出場價÷持有期最高收盤−1）": q("peak_gap_med"), "種子數": len(rows)}


def fixed_rows(rows_main, H, s1, closes, opens):
    """固定 H 日描述臂：同一批進場，xpos＝entry＋H−1 收盤；超過段尾 ⇒ 段尾收盤（W1b W4）。"""
    out = []
    for r in rows_main:
        s, e = r["sid"], int(r["entry_pos"]); o = opens[s][e]
        x = min(e + H - 1, s1)
        out.append({"sid": s, "entry_pos": e, "xpos": x, "g": closes[s][x] / o - 1.0, "endhold": bool(e + H - 1 > s1)})
    return out


# ═════════════ 條件出場：單筆路徑（給主臂訊號表）═════════════
def exit_after(xdays, e, s1):
    """進場日 e（開盤進）之後第一個出場訊號 d（收盤判、d ≥ e）⇒ 賣在 d＋1 開盤；沒有或 d＋1 ＞ s1 ⇒ (s1, True)＝段尾結算。"""
    i = int(np.searchsorted(xdays, e))
    if i < len(xdays) and xdays[i] + 1 <= s1:
        return int(xdays[i]) + 1, False
    return s1, True


def gross_exit(d, e, x, endhold):
    """毛報酬：段尾結算 ⇒ 收盤／進場開盤；否則 出場日開盤（無效改收盤）／進場開盤。"""
    o = d["opens"][e]
    if endhold:
        return d["closes"][x] / o - 1.0
    ox = d["opens"][x]
    return (ox if (np.isfinite(ox) and ox > 0) else d["closes"][x]) / o - 1.0


def coverage_cached(cal, w0, w1):
    p = os.path.join(WORK, "coverage.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    c = A2.coverage(cal, w0, w1)
    jdump(c, p)
    return c


if __name__ == "__main__":
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    build_cache(procs, lim)
