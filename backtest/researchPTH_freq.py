# -*- coding: utf-8 -*-
"""接近 52 週新高 PTH seq1【頻率表・乾跑】（台股策略線 登錄 sha e5d57b29ddb34ee7，2026-10-20 11:38；裁定 seq388 發號 N_前段 ＋1；
George & Hwang 2004：月底收盤 ÷ 過去 12 個月最高收盤，前 30% 做多、抱 6 個月）——回測線計算子代理。
⛔ 只數入選、事件個數、剔除計數、n_eff、重疊比例、排序相關；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有期結果（裁定 seq388：頻率表先交、
   裁定過目後才開跑）。用到的價格只有 ≤ 月底 t 的還原收盤（PTH、12−1 動能）；進場日 e 只用「有沒有成交、開盤是否有效、是否開盤鎖漲停」旗標（快取 trd／o／upl）。
⛔ 不 commit、不改既有程式與結果夾；researchAscTri_freq／researchUO_freq／research11／patterns ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH_freq_check
輸出 backtest/resultsPTH/freq/：freq.json、freq.csv、freq_by_year.csv、monthly.csv、equiv.csv、events_<世界>.csv.gz、run.log

═══ 讀法（P 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 P1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（UO／海龜頻率表同）：主 ＝ rerun17 快照（2015-01-05～2026-09-24）；早年 ＝ ~/earlydata
    （2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl sids（UG.gate3 GATE_V2 ∩ 四碼、首碼 1～9、非 91xx ⇒ 排 -DR／ETF／創新板、含已下市）；
    research11.load_bars ＜ 260 根的股票不進。壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、價格斷點、幽靈還原）∪ ~/crashwork/bad_*.pkl
    ∪ 早年 researchAddOn.early_extra_bad（reduce_v2，seq341 §六）。
 P2 月底 ＝ 日曆內每個曆月最後一個交易日；★ 日曆最後一個月若資料尾早於該月最後一個營業日（主：2026-09-24）⇒ 不算月底（不排序）。
    排序日 t 的母體 ＝ patterns.Frame.gate[t]（含 t 的 20 個交易日都有成交 ∧ t−20～t−1 日均量 ≥ 500 張 ＝ 登錄「500 張閘在排序日判」）∧ UG.pit_valid[t]。
 P3 PTH(i,t) ＝ c[t] ÷ max(c[k])，k ＝ 該股有效 K 棒中日曆位置落在（前 12 個月底, t］的全部（還原收盤，登錄 §一「本件用還原價」）。
    ★ 需「上市滿 12 個月」：前 12 個月底當天或之前要有至少一根有效 K 棒，否則剔除「未滿12月」〔另一讀法：窗內有幾根算幾根〕。
    ★「12 個月最高價不跨壞根」（登錄 §四）讀成：窗內第 2 根起任一根是壞 K 棒（與前一根斷開）⇒ 該股該月剔除「窗內壞根」〔另一讀法：只用最後一個壞根之後的窗〕。
    排序母體 ＝ P2 母體 ∧ PTH 可算。
 P4 前 30%：排序母體 n 檔，PTH 遞減排序，k ＝ ⌈0.3 n⌉，切點 ＝ 第 k 名的 PTH；★ PTH ≥ 切點全部入選（同值併入；PTH ＝ 1 即「月底就是 12 個月最高收盤」者常同值）。
    後 30%（登錄：只描述）同法反向，只報檔數。
 P5 進場（登錄 §一）：主臂「跳 1 個月」⇒ 形成月 m 的 t 排序後，第 m＋2 個曆月第一個交易日 e 開盤；「不跳」⇒ 第 m＋1 個曆月第一個交易日。
    e 超出日曆 ⇒ 不計（記「超出資料尾」）。進場剔除（每筆只記第一個原因）：壞根(t,e]（t 那根之後到 e 當天或之前最後一根有效 K 棒之間有壞 K 棒）
    → e無成交（e 當天無成交或開盤無效，含已下市）→ e開盤鎖漲停（快取 upl ＝ 開盤＝漲停價 ∧ 最低＝開盤 ＝ 全日鎖死）。保留 ＝ 事件數。
    ★ 入選母體不因進場剔除而改（排序在 t 完成）；剔除不遞補。
 P6 段（登錄 §二）：探索 [2017-03-02, 2021-12-30]｜確認 [2022-01-03, 資料尾]｜早年 [2005 第一個交易日, 2014-12-31]；
    ★ 事件依【進場日 e】歸段（CI 依進場月分群）；每月描述統計（排序母體、入選數、PTH 與 12−1 相關、重疊）依【排序日 t】歸段。
    n_eff ＝ min(事件數, 有事件的進場月數)（月頻事件：獨立月數）；n_eff ＜ 30 ⇒ 標「依構造不可判定、不計 N」。
    另報（參考）不重疊 6 個月段數 ＝ 有事件進場月數 ÷ 6（6 個月重疊持有，月與月之間不獨立）。
 P7 同檔連續入選月數：入選（P4，不看進場剔除）中同一檔連續形成月的段長分布；★ 段依第一個月的排序日歸段。
 P8 12−1 動能（登錄 §五必報）：mom(i,t) ＝ c[前 1 個月底那根] ÷ c[前 12 個月底那根] − 1（各取該日當天或之前最後一根有效 K 棒）；
    ★ 兩根之間（含前 12 個月底那根之後第一根）不可有壞 K 棒，否則不算。每月在排序母體內、兩者都有值的股票上算 Spearman（平均名次的 Pearson；
    venv 無 scipy ⇒ pandas rank 自算）；≥ 10 檔才算；報各段中位數與四分位。
 P9 重疊（同月同檔）：入選 (股, 形成月 m) 與
      營量 v1 ＝ ~/addonwork/world_{主,早年}.pkl SIG[False] 訊號（營飆 v1 ＝ SIG[True] 子集另欄）；researchUO_freq.load_sig 原樣、⛔ 只取 sid、pos；
        ★ 同月 ＝ 訊號日在（前月底, t］；只算訊號表涵蓋整月的形成月。
      去年漲最多 ＝ backtest/resultsTopPrevTW/rank_top10.csv 形成期「整年」前 10 名（★ 該件主表 T2；扣一月、＋營收兩版不用）；
        ★ 同月 ＝ 形成月 m 所在年 Y ＝ 該表「持有年」Y 的名單（持有一整年）。
      海龜 S2 ＝ backtest/resultsTurtle/freq/events_{主,早年}.csv.gz 格 S2、st＝保留 的事件日 T；★ 同月 ＝ T 在（前月底, t］。
    報兩個方向：入選中有對方的比例；對方 (股, 月) 中也在 PTH 前 30% 的比例（分母只算形成月有排序的月份）。
 P10 seq377 乾跑等價檢查（跳月 vs 不跳）：同一進場月 M：跳月保留集合 A（形成月 M−2）、不跳保留集合 B（形成月 M−1）；報 |A∩B|÷|A|、Jaccard
    的月中位與合計；另報入選層（不看進場剔除）相鄰兩形成月的重疊。兩者幾乎相同 ⇒ 兩臂近乎同一件、先報。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣（⛔ 只 import）
from backtest import researchUO_freq as RU                  # noqa: E402  load_sig 原樣（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402  Frame.gate（500 張閘）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = "e5d57b29ddb34ee7"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
ARCH = os.path.join(MAILBOX, "_封存-2026-10-19_附件與登錄全文-舊")
OUT = "backtest/resultsPTH/freq"
TOPQ = 0.30
LOOK = 12
NEFF_MIN = 30
ARMS = {"跳月": 2, "不跳": 1}                                # 進場月 ＝ 形成月 ＋ L
TOPPREV = "backtest/resultsTopPrevTW/rank_top10.csv"
TURTLE = "backtest/resultsTurtle/freq/events_{}.csv.gz"
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None), "主全窗": ("2017-03-02", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
# 形成月狀態
S_NA, S_GATE, S_YOUNG, S_BAD, S_OK = 0, 1, 2, 3, 4
SNAME = {S_GATE: "閘外(500張/pit)", S_YOUNG: "未滿12月", S_BAD: "窗內壞根", S_OK: "排序母體"}
# 進場狀態
E_NA, E_TAIL, E_BAD, E_NOTRD, E_UPL, E_KEEP = 0, 1, 2, 3, 4, 5
ENAME = {E_TAIL: "超出資料尾", E_BAD: "壞根(t,e]", E_NOTRD: "e無成交", E_UPL: "e開盤鎖漲停", E_KEEP: "保留"}
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check():
    fs = [f for d in (MAILBOX, ARCH) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) < 1:
        raise SystemExit(f"⛔ 信箱找不到登錄全文 sha{REG_SHA}")
    for f in fs:
        b = open(f, "rb").read()
        h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
        if h != REG_SHA:
            raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}（{f}）")
    return os.path.basename(fs[0])


# ═════════════ 月底、進場日 ═════════════
def month_ends(cal):
    """回 (ME, MK)：ME ＝ 每個完整曆月最後交易日的日曆位置；MK ＝ 對應 (年, 月)。資料尾不完整月不算（P2）。"""
    s = pd.Series(np.arange(len(cal)), index=cal)
    g = s.groupby([cal.year, cal.month]).max()
    ME = g.to_numpy(np.int64); MK = list(g.index)
    last = cal[ME[-1]]
    if last < last + pd.offsets.BMonthEnd(0):
        ME = ME[:-1]; MK = MK[:-1]
    return ME, MK


def entry_pos(cal, MK, L):
    """形成月 (y, m) ⇒ 第 m＋L 個曆月第一個交易日的日曆位置；超出日曆 ⇒ −1。"""
    n0 = len(cal); out = np.full(len(MK), -1, np.int64)
    for j, (y, m) in enumerate(MK):
        ts = pd.Timestamp(int(y), int(m), 1) + pd.DateOffset(months=L)
        p = int(cal.searchsorted(ts))
        if p < n0 and cal[p] < ts + pd.DateOffset(months=1):
            out[j] = p
    return out


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    W = _G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if len(df) != n0:
        raise SystemExit(f"⛔ {wn} {sid} df 長 {len(df)} ≠ 日曆 {n0}")
    c = np.asarray(B["c"], float)
    if not np.isfinite(c).all():
        raise SystemExit(f"⛔ {wn} {sid} 有效 K 棒收盤有缺值")
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    CB = np.r_[0, np.cumsum(bad)]                                   # CB[k] ＝ bad[0..k−1] 個數
    nbad = lambda a_, b_: int(CB[b_ + 1] - CB[a_]) if b_ >= a_ else 0  # bad[a..b] 個數
    f = P.Frame(df, set())
    gate = np.asarray(f.gate, bool)
    PV = W["PV"][i]; TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]
    posk = np.full(n0, -1, np.int64); posk[idx] = np.arange(nb)
    lastk = lambda p: int(np.searchsorted(idx, p, "right")) - 1     # 日曆位置 p 當天或之前最後一根
    ME = W["ME"]; nm = len(ME)
    ST = np.zeros(nm, np.int8); PTH = np.full(nm, np.nan); MOM = np.full(nm, np.nan)
    ENT = {L: np.zeros(nm, np.int8) for L in ARMS.values()}
    for j in range(LOOK, nm):
        t = int(ME[j]); s0 = int(ME[j - LOOK])
        if not (gate[t] and PV[t]) or posk[t] < 0:
            ST[j] = S_GATE; continue
        kt = int(posk[t]); k12 = lastk(s0)
        if k12 < 0:
            ST[j] = S_YOUNG; continue
        k0 = k12 + 1
        if nbad(k0 + 1, kt) > 0:
            ST[j] = S_BAD; continue
        ST[j] = S_OK
        PTH[j] = c[kt] / c[k0:kt + 1].max()
        k1 = lastk(int(ME[j - 1]))
        if k1 >= k0 and nbad(k0, k1) == 0:
            MOM[j] = c[k1] / c[k12] - 1.0
        for L in ARMS.values():
            e = int(W["EP"][L][j])
            if e < 0:
                ENT[L][j] = E_TAIL; continue
            ke = lastk(e)
            if nbad(kt + 1, ke) > 0:
                ENT[L][j] = E_BAD
            elif not (posk[e] >= 0 and TRD[e] and np.isfinite(O[e]) and O[e] > 0):
                ENT[L][j] = E_NOTRD
            elif UPL[e]:
                ENT[L][j] = E_UPL
            else:
                ENT[L][j] = E_KEEP
    return sid, {"ST": ST, "PTH": PTH, "MOM": MOM, "ENT": ENT}


# ═════════════ 排序、統計 ═════════════
def select(PTHj, U, top=True):
    """P4：回入選布林、n、k、切點。"""
    v = PTHj[U]; n = len(v)
    if n == 0:
        return np.zeros_like(U), 0, 0, np.nan
    k = int(math.ceil(TOPQ * n))
    srt = np.sort(v)[::-1] if top else np.sort(v)
    cut = srt[k - 1]
    with np.errstate(invalid="ignore"):
        sel = U & ((PTHj >= cut) if top else (PTHj <= cut))
    return sel, n, k, float(cut)


def spearman(x, y):
    if len(x) < 10:
        return np.nan
    rx = pd.Series(x).rank().to_numpy(); ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def qd(a):
    a = np.asarray([x for x in a if np.isfinite(x)], float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "中位": round(float(np.median(a)), 4), "p25": round(float(np.percentile(a, 25)), 4),
            "p75": round(float(np.percentile(a, 75)), 4), "min": round(float(a.min()), 4), "max": round(float(a.max()), 4)}


def runs_of(row):
    out = []; r = 0; st = -1
    for j, v in enumerate(row):
        if v:
            if r == 0:
                st = j
            r += 1
        elif r:
            out.append((st, r)); r = 0
    if r:
        out.append((st, r))
    return out


def run_bins(lens):
    lens = np.asarray(lens, int)
    if len(lens) == 0:
        return {}
    b = {"1": int((lens == 1).sum()), "2": int((lens == 2).sum()), "3": int((lens == 3).sum()), "4～6": int(((lens >= 4) & (lens <= 6)).sum()),
         "7～12": int(((lens >= 7) & (lens <= 12)).sum()), "13～24": int(((lens >= 13) & (lens <= 24)).sum()), "≥25": int((lens >= 25).sum())}
    b["段數"] = int(len(lens)); b["中位"] = float(np.median(lens)); b["平均"] = round(float(lens.mean()), 2); b["最長"] = int(lens.max())
    return b


def load_overlap_sets(wn, cal, sids, ME, MK):
    """回 {名稱: (集合 {(sid, j)}, 可比形成月集合)}。"""
    ix = {s: k for k, s in enumerate(sids)}
    nm = len(ME)
    out = {}
    # 營量 v1／營飆 v1
    SG, SGF, cover, nsig = RU.load_sig(wn, cal)
    c0, c1 = int(cal.searchsorted(pd.Timestamp(cover[0]))), int(cal.searchsorted(pd.Timestamp(cover[1])))
    okm = {j for j in range(1, nm) if int(ME[j - 1]) + 1 >= c0 and int(ME[j]) <= c1}
    for nmx, dct in (("營量v1", SG), ("營飆v1", SGF)):
        S = set()
        for s, ps in dct.items():
            if s not in ix:
                continue
            jj = np.searchsorted(ME, ps, "left")                      # 訊號日 p ∈ (ME[j−1], ME[j]] ⇒ j
            for j in set(int(x) for x in jj if x < nm):
                if j in okm:
                    S.add((s, j))
        out[nmx] = (S, okm, {"涵蓋": cover, "訊號筆數": nsig[0] if nmx == "營量v1" else nsig[1]})
    # 海龜 S2
    ev = pd.read_csv(TURTLE.format(wn), dtype={"sid": str}, usecols=["格", "sid", "T", "st"])
    ev = ev[(ev["格"] == "S2") & (ev["st"] == "保留")]
    pos = cal.searchsorted(pd.to_datetime(ev["T"]))
    jj = np.searchsorted(ME, pos, "left")
    S = {(s, int(j)) for s, j in zip(ev["sid"], jj) if j < nm and j >= 1 and s in ix}
    out["海龜S2"] = (S, set(range(1, nm)), {"保留事件": int(len(ev))})
    # 去年漲最多 整年 前 10
    tp = pd.read_csv(TOPPREV, dtype={"代號": str})
    tp = tp[(tp["世界"] == wn) & (tp["形成期"] == "整年") & (tp["名次"] <= 10)]
    byY = {}
    for y, s in zip(tp["持有年"], tp["代號"]):
        byY.setdefault(int(y), set()).add(s)
    S = set(); okm = set()
    for j, (y, m) in enumerate(MK):
        if int(y) in byY:
            okm.add(j)
            for s in byY[int(y)]:
                if s in ix:
                    S.add((s, j))
    out["去年漲最多T2"] = (S, okm, {"持有年": sorted(byY)})
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = OUT if a.limit is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "接近 52 週新高 PTH seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有期結果）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq388 發號；N_前段 ＋1；頻率表先交、裁定過目後才開跑；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N",
         "世界": {}}
    FREQ = []; YR = []; MON = []; EQ = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        ME, MK = month_ends(cal)
        W["ME"] = ME; W["EP"] = {L: entry_pos(cal, MK, L) for L in ARMS.values()}
        _G[wn] = W
        nm = len(ME)
        log(f"[{wn}] 月底 {nm} 個：{cal[ME[0]].date()}～{cal[ME[-1]].date()}｜第一個可排序月 {cal[ME[LOOK]].date()}")
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        res = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                res[sid] = r
                if (k_ + 1) % 500 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        ok = sorted(s for s, r in res.items() if r is not None)
        n_skip = len(res) - len(ok)
        S = len(ok)
        ST = np.stack([res[s]["ST"] for s in ok]); PT = np.stack([res[s]["PTH"] for s in ok]); MO = np.stack([res[s]["MOM"] for s in ok])
        EN = {L: np.stack([res[s]["ENT"][L] for s in ok]) for L in ARMS.values()}
        U = ST == S_OK
        SEL = np.zeros_like(U); BOT = np.zeros_like(U)
        NU = np.zeros(nm, int); KK = np.zeros(nm, int); CUT = np.full(nm, np.nan); SP = np.full(nm, np.nan)
        for j in range(LOOK, nm):
            SEL[:, j], NU[j], KK[j], CUT[j] = select(PT[:, j], U[:, j], True)
            BOT[:, j] = select(PT[:, j], U[:, j], False)[0]
            m = U[:, j] & np.isfinite(MO[:, j])
            SP[j] = spearman(PT[m, j], MO[m, j])
        log(f"[{wn}] 逐股完｜load_bars 不足 260 根 {n_skip} 檔｜{time.time() - t0:.0f}s")
        # 重疊
        OV = load_overlap_sets(wn, cal, ok, ME, MK)
        selset = {(ok[i], j) for i, j in zip(*np.nonzero(SEL))}
        # 段（排序日 t 歸段、進場日 e 歸段）
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "閘": W["gate"], "壞根": W["bad_info"],
              "檔數": len(sids), "load_bars不足260根檔數": n_skip, "月底": [str(cal[ME[0]].date()), str(cal[ME[-1]].date())],
              "第一個可排序月": str(cal[ME[LOOK]].date()), "段": {}}
        ymE = {L: np.array([cal[e].strftime("%Y-%m") if e >= 0 else "" for e in W["EP"][L]]) for L in ARMS.values()}
        for sg, (x, y) in SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x)))
            p1 = n0 - 1 if y is None else int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1
            jt = [j for j in range(LOOK, nm) if p0 <= ME[j] <= p1]              # 排序日歸段
            segj = {"期間": f"{cal[p0].date()}～{cal[p1].date()}", "年": round((cal[p1] - cal[p0]).days / 365.25, 3)}
            # 每月描述（t 歸段）
            segj["形成月數(t在段內)"] = len(jt)
            segj["每月排序母體"] = qd(NU[jt]); segj["每月入選(前30%含同值)"] = qd([int(SEL[:, j].sum()) for j in jt])
            segj["每月⌈0.3n⌉"] = qd(KK[jt]); segj["同值併入多出檔數合計"] = int(sum(int(SEL[:, j].sum()) - KK[j] for j in jt))
            segj["每月切點PTH"] = qd(CUT[jt]); segj["每月PTH=1檔數"] = qd([int((U[:, j] & (PT[:, j] >= 1.0)).sum()) for j in jt])
            segj["每月後30%檔數(描述)"] = qd([int(BOT[:, j].sum()) for j in jt])
            segj["形成月剔除合計"] = {SNAME[k]: int(sum(int((ST[:, j] == k).sum()) for j in jt)) for k in (S_GATE, S_YOUNG, S_BAD, S_OK)}
            segj["PTH與12−1每月Spearman"] = qd(SP[jt])
            segj["12−1可算比例(排序母體內)"] = round(float(np.mean([np.isfinite(MO[U[:, j], j]).mean() for j in jt if NU[j]])), 4) if jt else None
            # 連續入選
            jts = set(jt)
            lens = [r for i in range(S) for (st, r) in runs_of(SEL[i]) if st in jts]
            segj["同檔連續入選月數(段依首月t)"] = run_bins(lens)
            # 重疊
            ovj = {}
            for nmx, (Sx, okm, info) in OV.items():
                jj = [j for j in jt if j in okm]
                sel_n = sum(int(SEL[:, j].sum()) for j in jj)
                hit = sum(1 for (s, j) in selset if j in jj and (s, j) in Sx)
                Sx_in = [(s, j) for (s, j) in Sx if j in jj]
                hit2 = sum(1 for p in Sx_in if p in selset)
                ovj[nmx] = {"可比形成月": len(jj), "PTH入選股月": sel_n, "其中同月有對方": hit,
                            "比例_PTH中有對方": round(hit / sel_n, 4) if sel_n else None,
                            "對方股月": len(Sx_in), "其中在PTH前30%": hit2, "比例_對方在PTH前30%": round(hit2 / len(Sx_in), 4) if Sx_in else None,
                            "註": info}
            segj["重疊(同月同檔,依t)"] = ovj
            # 事件（進場日 e 歸段）
            for arm, L in ARMS.items():
                EP = W["EP"][L]
                je = [j for j in range(LOOK, nm) if EP[j] >= 0 and p0 <= EP[j] <= p1]
                sel_n = sum(int(SEL[:, j].sum()) for j in je)
                acc = {ENAME[k]: int(sum(int((SEL[:, j] & (EN[L][:, j] == k)).sum()) for j in je)) for k in (E_BAD, E_NOTRD, E_UPL, E_KEEP)}
                kept_m = [int((SEL[:, j] & (EN[L][:, j] == E_KEEP)).sum()) for j in je]
                nev = int(sum(kept_m)); months = int(sum(1 for v in kept_m if v > 0)); ne = min(nev, months)
                nsid = len({ok[i] for j in je for i in np.flatnonzero(SEL[:, j] & (EN[L][:, j] == E_KEEP))})
                yrs = segj["年"]
                byy = {}
                for j, v in zip(je, kept_m):
                    yy = int(cal[EP[j]].year); byy[yy] = byy.get(yy, 0) + v
                jarm = {"入選(進場日在段內)": sel_n, **{f"剔除_{k}": v for k, v in acc.items() if k != "保留"}, "事件數(保留)": nev,
                        "相異檔數": nsid, "有事件進場月": months, "n_eff": ne, "n_eff<30": bool(ne < NEFF_MIN),
                        "判斷": "依構造不可判定、不計 N" if ne < NEFF_MIN else "可判（n_eff ≥ 30）",
                        "不重疊6個月段數(參考)": round(months / 6, 1), "每月事件": qd(kept_m), "每年事件數": round(nev / yrs, 1) if yrs else None,
                        "逐年保留": byy, "進場月範圍": [ymE[L][je[0]], ymE[L][je[-1]]] if je else None}
                segj[arm] = jarm
                FREQ.append({"世界": wn, "段": sg, "臂": arm, "期間": segj["期間"], **{k: v for k, v in jarm.items() if not isinstance(v, (dict, list))},
                             "每月事件中位": jarm["每月事件"]["中位"] if jarm["每月事件"] else None,
                             "每月事件min": jarm["每月事件"]["min"] if jarm["每月事件"] else None,
                             "每月事件max": jarm["每月事件"]["max"] if jarm["每月事件"] else None})
                for yy, v in sorted(byy.items()):
                    YR.append({"世界": wn, "段": sg, "臂": arm, "年": yy, "保留": v})
            # seq377 等價：同一進場月 跳月(形成 M−2) vs 不跳(形成 M−1)
            EP2, EP1 = W["EP"][2], W["EP"][1]
            ov = []; inter = 0; na = 0; nb_ = 0; uni = 0
            for j in range(LOOK + 1, nm):
                e2 = EP2[j - 1]; e1 = EP1[j]
                if e2 < 0 or e1 < 0 or e2 != e1 or not (p0 <= e2 <= p1):
                    continue
                A = set(np.flatnonzero(SEL[:, j - 1] & (EN[2][:, j - 1] == E_KEEP))); Bs = set(np.flatnonzero(SEL[:, j] & (EN[1][:, j] == E_KEEP)))
                if not A:
                    continue
                ia = len(A & Bs); ov.append((ia / len(A), ia / len(A | Bs)))
                inter += ia; na += len(A); nb_ += len(Bs); uni += len(A | Bs)
                EQ.append({"世界": wn, "段": sg, "進場月": cal[e2].strftime("%Y-%m"), "跳月保留": len(A), "不跳保留": len(Bs), "交集": ia,
                           "交集÷跳月": round(ia / len(A), 4), "Jaccard": round(ia / len(A | Bs), 4)})
            selpair = [(int((SEL[:, j - 1] & SEL[:, j]).sum()), int(SEL[:, j - 1].sum())) for j in range(LOOK + 1, nm) if p0 <= ME[j] <= p1 and SEL[:, j - 1].sum()]
            segj["seq377等價_跳月vs不跳"] = {
                "同進場月數": len(ov), "交集÷跳月_月中位": round(float(np.median([x[0] for x in ov])), 4) if ov else None,
                "Jaccard_月中位": round(float(np.median([x[1] for x in ov])), 4) if ov else None,
                "合計交集÷跳月": round(inter / na, 4) if na else None, "合計Jaccard": round(inter / uni, 4) if uni else None,
                "入選層相鄰兩形成月重疊(÷前月)_月中位": round(float(np.median([a_ / b_ for a_, b_ in selpair])), 4) if selpair else None}
            Wj["段"][sg] = segj
            log(f"[{wn}/{sg}] " + "｜".join(f"{arm} n={segj[arm]['事件數(保留)']} n_eff={segj[arm]['n_eff']}" for arm in ARMS) +
                f"｜Spearman 中位 {segj['PTH與12−1每月Spearman']['中位'] if segj['PTH與12−1每月Spearman'] else None}"
                f"｜等價 交集÷跳月 {segj['seq377等價_跳月vs不跳']['合計交集÷跳月']}")
        # 每月表
        for j in range(LOOK, nm):
            row = {"世界": wn, "形成月底": str(cal[ME[j]].date()), "排序母體": int(NU[j]), "k=⌈0.3n⌉": int(KK[j]), "入選": int(SEL[:, j].sum()),
                   "切點PTH": CUT[j], "PTH=1檔數": int((U[:, j] & (PT[:, j] >= 1.0)).sum()), "後30%": int(BOT[:, j].sum()),
                   **{f"剔除_{SNAME[k]}": int((ST[:, j] == k).sum()) for k in (S_GATE, S_YOUNG, S_BAD)},
                   "Spearman_PTH_12-1": SP[j]}
            for arm, L in ARMS.items():
                e = W["EP"][L][j]
                row[f"{arm}_進場日"] = str(cal[e].date()) if e >= 0 else ""
                row[f"{arm}_保留"] = int((SEL[:, j] & (EN[L][:, j] == E_KEEP)).sum())
            for nmx, (Sx, okm, info) in OV.items():
                row[f"重疊_{nmx}"] = int(sum(1 for i in np.flatnonzero(SEL[:, j]) if (ok[i], j) in Sx)) if j in okm else None
            MON.append(row)
        # 事件檔（只含排序母體列；⛔ 無任何進場後價格、無報酬欄；價格衍生只有 ≤ t 的 PTH、12−1）
        rows = []
        for j in range(LOOK, nm):
            ii = np.flatnonzero(U[:, j])
            rk = pd.Series(-PT[ii, j]).rank(method="min").to_numpy()
            for q, i in enumerate(ii):
                rows.append({"sid": ok[i], "形成月底": str(cal[ME[j]].date()), "PTH": PT[i, j], "名次": int(rk[q]), "排序母體": int(NU[j]),
                             "入選": bool(SEL[i, j]), "後30%": bool(BOT[i, j]), "mom12_1": MO[i, j],
                             **{f"{arm}_進場日": (str(cal[W['EP'][L][j]].date()) if W["EP"][L][j] >= 0 else "") for arm, L in ARMS.items()},
                             **{f"{arm}_st": ENAME.get(int(EN[L][i, j]), "") for arm, L in ARMS.items()}})
        with gzip.open(os.path.join(out_dir, f"events_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            pd.DataFrame(rows).to_csv(fh, index=False)
        J["世界"][wn] = Wj
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(out_dir, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YR).to_csv(os.path.join(out_dir, "freq_by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(MON).to_csv(os.path.join(out_dir, "monthly.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EQ).to_csv(os.path.join(out_dir, "equiv.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
