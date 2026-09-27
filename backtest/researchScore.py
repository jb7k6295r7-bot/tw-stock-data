# -*- coding: utf-8 -*-
"""PREREG合成分數 seq1（台股策略線登錄「多個弱訊號合成分數選股_十一票等權」sha dbc1881f24a76661；裁定 seq254 發號、N_組合 ＋1、§三 早年段同判準並報；
seq255 §五 5；排程 seq257 順 6、seq261）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchScore feat|body|report [--procs 2] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchScore_check.py

═══ 沿用的預設（登錄 §一；⭐ 逐條）═══
  母體 ＝ W1 eligible（換股日同月量測日的面板：主快照 resultsp9_engine/panel_ext.csv.gz、早年 A 段 early 版面 sig_main/panel.csv.gz）∩ gate3、含已下市
  權重 ＝ 等權投票（多方 ＋1、空方 −1）；⛔ 不擬合　　換股 ＝ 月換（每月第一個交易日開盤）｜季換（1／4／7／10 月）　　檔數 10｜20
  分數相同 ＝ 抽籤（固定種子：每個換股日 default_rng([20260928, e]) 對當日母體依代號排序後各抽一個均勻數，分數同者依它排）
  換股時仍入選 ＝ 續抱、只換落選的（researchSector.sim_book 的 U1 (i) 同一套：落選者開盤賣、新入選依名次開盤買、金額 min(前一日淨值 ÷ N, 現金)、
      買不到（停牌／開盤漲停）⇒ 該名額持現金、⛔ 不遞補；賣不掉（跌停／停牌）⇒ 之後第一個可成交開盤賣；另報「全賣全買」）
  成本 ＝ 來回 0.585%（賣出時扣進場金額 × 0.585%）　　月營收可用日 ＝ 次月 10 日後第一個交易日（panel_rev 的 signal_pos／entry_pos）
  ⭐ 停止交易強制出場：開（research11.stop_force_days：最後有效收盤 L ＜ 段尾 ⇒ L＋1 以最後收盤賣、扣成本；本檔 sim_book 內加這一步）
  ⭐ 資料尾：本件是換股簿（沒有固定持有天數的排程出場）⇒ 依構造不會有「出場日超出資料尾」的截斷；營量 v1 對照用 T1 版（rerun17.setup_and t1=True，1e7229c101）
═══ 11 票（登錄 §二；定義沿用既有落地；⛔ 不改參數；seq255 §五 5：①③⑧ 照登錄原定義）═══
  ① 最新可用月營收創 24 個月新高 ＝ panel_rev.rev_hi24（營飆 AND 同一份面板與讀法：research13.and_flags——signal_pos ≤ e−1 最新一列、距離 ≤ 45 日）
  ② 最新可用月營收年增率 ≥ 15% ＝ 同一列 panel_rev.yoy ≥ 0.15（research34 G2 同式）
  ③ 收盤創 250 日新高（近 L 日內）＝ 有效 K 棒上 c ≥ 含當根 250 根最高收盤（research11 c5 同式）的日子落在 [e−L, e−1]
  ④ 多頭排列 MA5 ＞ MA10 ＞ MA20 ＞ MA60（換股前一日 ＝ e−1 以前最後一根有效 K 棒；有效 K 棒上的簡單平均，math.fsum ＝ researchRev.ma_fsum 慣例）
  ⑤ 強勢股 5 條 ≥ 3 條 ＝ research11.stock_features 主格（C1 30%、C3 ×3）的 score ≥ 3 且該根合格（eligible 遮罩同原式）；取 e−1 以前最後一根 load_bars 根
     （⭐ 營飆的 S 訊號是同一條件再做 20 日去重的事件；本票是狀態，⛔ 不去重；閘：去重後 ＝ resultsN17/sig_edc6f/signals_S.csv.gz 逐列）
  ⑥ TD 9 買、⑦ RSI 30 站回（近 L 日；researchRev 個股原版，訊號日 T）、⑩ 上升趨勢線跌破（researchRev.up_line_events ＝ 上升趨勢線登錄主格）、
  ⑪ 高檔爆量長上影確認版（訊號日 ＝ 確認日 C）⇒ 全部取 researchSig.sig_days 的落地（resultsSig/sig_cache.pkl、sig_cache_earlyA.pkl，sha 照 PKL_SHA256.txt）
  ⑧ 上升三角往上突破（近 L 日）＝ patterns_all.detect_lines 的 S06（型態全量定義；閘：主快照 2017-03-02 起的 T 與 resultsPatAll/events_S06 逐列同）
  ⑨ 量能放大 ＝ 有效 K 棒 20 日均量 ÷ 250 日均量（volume 股數，含當根），e−1 以前最後一根；在當月母體（有值者）百分位 ＞ 0.8（前 20%）
  分數 ＝ 多方票數 − 空方票數（−2～＋9）；近 L 日 ＝ 日曆位置 [e−L, e−1]，L ∈ {5, 20, 60}
═══ 窗、挑法、判定（登錄 §三；裁定 seq254 §三）═══
  主快照連續一條權益：2017-03-02 開盤起（窗首全現金，窗首即建倉）～2026-08-24；探索 2017-03-02～2021-12-30（挑）｜確認 2022-01-03～2026-08-24（判）
  段落指標 ＝ research13.window_stats（245 日／年）在連續權益上切段（researchSector 同式）
  退化排除（seq246）：探索段平均持股 ＜ 一半檔數、或現金比例 ＞ 30% ⇒ 不進挑選（挑之前排除）
  挑法：探索段過使用者判準（年化 ＞ 0050 同段 且 比值 ≥ 0050）的裡取比值最高；都沒過取比值最高；同分取年化高、再 L 小、月換先、檔數小
  判定：確認段 合格／另列／不合格；早年段同判準並報（★ 早年 A 段 2012-06-01～2014-12-30 early 版面、只上市 ＝ 判定用；
        B 段 2015-08-03～2016-12-30 主快照、只上市 ⇒ 資料起點 2015-01 使 ①③⑤⑨ 依構造算不出或不足，⛔ 不用於判定、照報）
        確認段合格而早年段不合格 ⇒「只在看過的那段合格」，⛔ 不寫「合格」
  描述臂（⛔ 不判；同挑中格的 L／換股／檔數）：甲 ①～⑤、乙 ⑥～⑪、丙 隨機挑同檔數 1,000 次（default_rng([20260928, 1, r])；p ＝ 年化 ≥ 本格的比例）、
        丁 營量 v1（T1 版）、0050 同段
  必報：每格 年化、回落、比值、每年換手、成本／年、平均持股、現金比例、入選平均分數與分佈；每票命中率（入選中有該票的比例）；各票兩兩相關（母體股-月）
  出場敏感度（seq242 ③）：挑中格確認段判合格／另列才跑；否則不跑（寫明）
輸出 backtest/resultsScore/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import patterns_all as PA
from . import rerun17 as RR
from . import research11 as R
from . import research13 as R13
from . import tradability as TR
from . import universe_gate as UG
from . import p4_features as P4F

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsScore")
TAG = "停止交易強制出場：開"
COST = 0.00585
LS, REBS, NS = (5, 20, 60), ("月換", "季換"), (10, 20)
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
MAIN_W = ("2017-03-02", "2026-08-24")
EARLY_A = ("2012-06-01", "2014-12-30")
EARLY_B = ("2015-08-03", "2016-12-30")
EARLY_DATA = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
EARLY_SIG = os.path.expanduser("~/earlydata/3edc0e2206/sig_main")
PANEL_EXT = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
PANEL_REV = os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz")
SIG_CACHE = {"main": os.path.join(HERE, "resultsSig", "sig_cache.pkl"), "A": os.path.join(HERE, "resultsSig", "sig_cache_earlyA.pkl")}
STALE = 45
SEED_TIE, SEED_R = 20260928, 20260928
VOTES = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11"]
BEAR = {"v10", "v11"}
VNAME = {"v1": "① 月營收創 24 月新高", "v2": "② 營收年增 ≥15%", "v3": "③ 創 250 日新高", "v4": "④ 多頭排列", "v5": "⑤ 強勢股 5 取 3",
         "v6": "⑥ TD9 買", "v7": "⑦ RSI30 站回", "v8": "⑧ 上升三角突破", "v9": "⑨ 量能放大", "v10": "⑩ 上升線跌破（空）", "v11": "⑪ 高檔爆量長上影確認（空）"}
SETS = {"主版": VOTES, "甲": ["v1", "v2", "v3", "v4", "v5"], "乙": ["v6", "v7", "v8", "v9", "v10", "v11"]}
EVL = ("v3", "v6", "v7", "v8", "v10", "v11")          # 受 L 影響的事件票
_G: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def sha(p, n=16):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def label(c, m, c0, m0):
    r, r0 = c / abs(m), c0 / abs(m0)
    return "合格" if (c > c0 and r >= r0) else ("另列" if c > c0 else "不合格")


def seg_metrics(eq, a, b):
    c, m = R13.window_stats(eq, 0, len(eq), a, b + 1)
    return float(c), float(m), (float(c) / abs(float(m)) if m < 0 else float("nan"))


def pos_of(cal, d):
    p = int(cal.searchsorted(pd.Timestamp(d)))
    assert str(cal[p].date()) == d, (d, cal[p])
    return p


def reb_days(cal, t0, t1, quarterly=False):
    """每月第一個交易日（季換：1／4／7／10 月）∈ [t0, t1]，另加 t0 本身（窗首即建倉）。"""
    out = [t0]
    for t in range(t0 + 1, t1 + 1):
        if cal[t].month != cal[t - 1].month and (not quarterly or cal[t].month in (1, 4, 7, 10)):
            out.append(t)
    return out


# ═════════════════════════════ 逐檔特徵（票）
def s5_state(B):
    """research11.stock_features 主格的 score ≥ 3 且合格（逐字同式）⇒ 回 (idx, 布林)。"""
    idx, o, c, amt, up, skip, next_bad = (B[k] for k in ("idx", "o", "c", "amt", "up", "skip", "next_bad"))
    n = len(idx)
    ret20 = np.array(c / np.roll(c, 20) - 1, dtype=float); ret20[:20] = np.nan
    nup20 = pd.Series(up.astype(int)).rolling(20, min_periods=20).sum().to_numpy(float)
    amt_prev20 = np.array(R._roll_mean(np.roll(amt, 1), 20), dtype=float); amt_prev20[:21] = np.nan
    amt_ratio = amt / amt_prev20
    ma100 = R._roll_mean(c, 100)
    hi250 = R._roll_max(c, 250)
    nb_sig = np.array([next_bad[max(0, k - 20)] for k in range(n)])
    eligible = (np.arange(n) >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(amt_ratio)
    eligible &= nb_sig > np.arange(n)
    c1, c3 = R.MAIN_CELL[0], R.MAIN_CELL[1]
    with np.errstate(invalid="ignore"):
        score = ((ret20 >= c1).astype(int) + (nup20 >= 3).astype(int) + (amt_ratio >= c3).astype(int)
                 + (c > ma100).astype(int) + (c >= hi250).astype(int))
    return idx, eligible & (score >= 3)


def feat_one(args):
    sid, mk = args
    cal, REB, SIGC = _G["cal"], _G["REB"], _G["SIGC"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return None
    df = st.df
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); v = df["volume"].to_numpy(float)
    bars = np.flatnonzero(np.isfinite(c))
    if len(bars) < 2:
        return None
    cb, hb, lb, vb = c[bars], h[bars], l[bars], v[bars]
    s = pd.Series(cb)
    hi250 = s.rolling(250, min_periods=250).max().to_numpy(float)
    with np.errstate(invalid="ignore"):
        ev3 = bars[np.flatnonzero(cb >= hi250)]
        vs = pd.Series(vb)
        vr = (vs.rolling(20, min_periods=20).mean() / vs.rolling(250, min_periods=250).mean()).to_numpy(float)
    r60 = PA._rN(cb, PA.R60)
    o8 = PA.detect_lines(hb, lb, cb, r60)[PA.vid_s(6)]
    T8 = sorted({int(t) for t, _ in o8})
    ev8 = bars[np.array(T8, int)] if T8 else np.zeros(0, int)
    B = R.load_bars(sid, mk, cal)
    if B is not None:
        idx5, st5 = s5_state(B)
    else:
        idx5, st5 = np.zeros(0, int), np.zeros(0, bool)
    S = SIGC.get(sid, {})
    EV = {"v3": ev3, "v6": np.asarray(S.get("E:TD", []), int), "v7": np.asarray(S.get("E:RSI", []), int), "v8": ev8,
          "v10": np.asarray(S.get("X:TL", []), int), "v11": np.asarray(S.get("X:VSc", []), int)}
    REB = np.asarray(REB, int)
    j = np.searchsorted(bars, REB - 1, side="right") - 1
    ok = j >= 0
    jj = np.where(ok, j, 0)
    # ④ 均線用 math.fsum（專案慣例 researchRev.ma_fsum）：真值相等時（例 MA5 ＝ MA10）不會因捨入順序變成「＞」
    st4 = np.zeros(len(REB), bool)
    for i_, j_ in enumerate(j):
        if j_ >= 59:
            m_ = [math.fsum(cb[j_ - w + 1:j_ + 1]) / w for w in (5, 10, 20, 60)]
            st4[i_] = m_[0] > m_[1] > m_[2] > m_[3]
    out = {"sid": sid, "has_sig": sid in SIGC, "v4": st4, "vr": np.where(ok, vr[jj], np.nan)}
    j5 = np.searchsorted(idx5, REB - 1, side="right") - 1
    out["v5"] = (j5 >= 0) & (st5[np.maximum(j5, 0)] if len(st5) else False)
    for k, ev in EV.items():
        ev = np.sort(ev)
        for L in LS:
            lo = np.searchsorted(ev, REB - L, side="left"); hi = np.searchsorted(ev, REB - 1, side="right")
            out[f"{k}_L{L}"] = hi > lo
    out["ev8"] = ev8                                             # 閘用
    if _G.get("gate5"):
        cand = np.flatnonzero(st5); last = -10 ** 9; pk = []
        for k in cand:
            if k - last > R.MAIN_CELL[2]:
                pk.append(k); last = k
        out["s5_pos"] = [int(idx5[k]) for k in pk if k + 1 < len(idx5)]
    return out


def rev_votes(path, REB):
    """panel_rev ⇒ {sid: (v1 陣列, v2 陣列)}（research13.and_flags 讀法：signal_pos ≤ e−1 最新一列、距離 ≤ 45）。"""
    P_ = pd.read_csv(path, dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24", "yoy"])
    P_ = P_.sort_values(["stock_id", "signal_pos"], kind="stable")
    REB = np.asarray(REB, int); out = {}
    for sid, g in P_.groupby("stock_id"):
        sp = g["signal_pos"].to_numpy(int); hi = g["rev_hi24"].astype(str).eq("True").to_numpy(); yy = g["yoy"].to_numpy(float)
        j = np.searchsorted(sp, REB - 1, side="right") - 1
        ok = (j >= 0) & ((REB - 1) - sp[np.maximum(j, 0)] <= STALE)
        jj = np.maximum(j, 0)
        with np.errstate(invalid="ignore"):
            out[sid] = (ok & hi[jj], ok & (yy[jj] >= 0.15))
    return out


def eligible_by_reb(panel_path, cal, REB, keep):
    p = P4F.read_panel(panel_path)
    p = p[p["eligible"].astype(str).eq("True") & p["stock_id"].isin(keep)]
    pm = {d: g["stock_id"].tolist() for d, g in p.groupby("measure_date")}
    meas = sorted(pm)
    out = {}
    for e in REB:
        d = cal[e]; mm = [m for m in meas if m.year == d.year and m.month == d.month]
        out[e] = sorted(pm[max(mm)]) if mm else []
    return out


def build_part(part, a):
    """part ∈ {main, A}：特徵、票、母體 ⇒ 快取 feat_<part>.pkl。main 的換股日含 B 段（2015-08 起）。"""
    t0 = time.time()
    if part == "A":
        st_ = json.load(open(os.path.join(os.path.dirname(EARLY_DATA), "STATUS.json"), encoding="utf-8"))
        assert st_.get("complete"), "⛔ 早年版面不完整"
        D.DATA = EARLY_DATA
        panel, prev = os.path.join(EARLY_SIG, "panel.csv.gz"), os.path.join(EARLY_SIG, "panel_rev.csv.gz")
        wins = {"A": EARLY_A}
    else:
        RR.use_snapshot()
        panel, prev = PANEL_EXT, PANEL_REV
        wins = {"main": MAIN_W, "B": EARLY_B}
    cal = D.load_calendar()
    U = UG.gate3(pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str))
    if part == "A":
        U = U[U["market"] == "twse"]
    mk = U.set_index("stock_id")["market"]
    REB = sorted({e for w in wins.values() for q in (False, True) for e in reb_days(cal, pos_of(cal, w[0]), pos_of(cal, w[1]), q)})
    ELIG = eligible_by_reb(panel, cal, REB, set(U["stock_id"]))
    sids = sorted({s for v in ELIG.values() for s in v})
    if a.limit:
        sids = sids[:a.limit]
    SIG, _ = pickle.load(open(SIG_CACHE[part], "rb"))
    _G.update(cal=cal, REB=REB, SIGC=SIG, gate5=(part == "main"))
    F = {}
    with Pool(a.procs) as pool:
        for i, r in enumerate(pool.imap_unordered(feat_one, [(s, mk.get(s, "twse")) for s in sids], chunksize=4)):
            if r is not None:
                F[r["sid"]] = r
            if (i + 1) % 400 == 0:
                log(f"  [特徵 {part}] {i + 1}/{len(sids)}｜{time.time() - t0:.0f}s")
    RV = rev_votes(prev, REB)
    pickle.dump({"REB": REB, "ELIG": ELIG, "F": F, "RV": RV, "wins": wins, "data": D.DATA, "panel": panel, "panel_rev": prev,
                 "sig_cache": SIG_CACHE[part], "sig_cache_sha": sha(SIG_CACHE[part], 64)},
                open(os.path.join(OUT, f"feat_{part}.pkl"), "wb"))
    log(f"[特徵 {part}] 母體 {len(sids)} 檔、有特徵 {len(F)}、sig 快取缺 {sum(not v['has_sig'] for v in F.values())}｜換股日 {len(REB)}｜{time.time() - t0:.0f}s")
    RR.use_snapshot()


# ═════════════════════════════ 分數與挑股
def vote_table(FT, L):
    """⇒ {e: DataFrame(index＝sid, 欄＝11 票 0／1、vr)}（母體 ＝ ELIG[e] ∩ 有特徵 ∩ 有價）。"""
    REB, ELIG, F, RV = FT["REB"], FT["ELIG"], FT["F"], FT["RV"]
    P = FT["P"]
    out = {}
    for i, e in enumerate(REB):
        u = [s for s in ELIG[e] if s in F and s in P]
        if not u:
            out[e] = pd.DataFrame(columns=VOTES + ["vr"]); continue
        rows = {}
        for s in u:
            f = F[s]; rv = RV.get(s)
            rows[s] = {"v1": bool(rv[0][i]) if rv else False, "v2": bool(rv[1][i]) if rv else False,
                       "v3": bool(f[f"v3_L{L}"][i]), "v4": bool(f["v4"][i]), "v5": bool(f["v5"][i]),
                       "v6": bool(f[f"v6_L{L}"][i]), "v7": bool(f[f"v7_L{L}"][i]), "v8": bool(f[f"v8_L{L}"][i]),
                       "v10": bool(f[f"v10_L{L}"][i]), "v11": bool(f[f"v11_L{L}"][i]), "vr": float(f["vr"][i])}
        T = pd.DataFrame.from_dict(rows, orient="index")
        pr = T["vr"].rank(pct=True)
        T["v9"] = (pr > 0.8).fillna(False).astype(bool)
        out[e] = T[VOTES + ["vr"]]
    return out


def score_of(T, vs):
    sc = np.zeros(len(T), int)
    for v in vs:
        sc += np.where(T[v].to_numpy(bool), -1 if v in BEAR else 1, 0)
    return pd.Series(sc, index=T.index)


def tie_u(e, sids):
    u = np.random.default_rng([SEED_TIE, int(e)]).random(len(sids))
    return dict(zip(sids, u))


def select(VT, reb, vs, N):
    sel = {}; scs = {}
    for e in reb:
        T = VT[e]
        if len(T) == 0:
            sel[e] = []; continue
        sc = score_of(T, vs)
        sids = sorted(T.index)
        u = tie_u(e, sids)
        order = sorted(sids, key=lambda s: (-sc[s], u[s]))
        sel[e] = order[:N]; scs[e] = [int(sc[s]) for s in order[:N]]
    return sel, scs


# ═════════════════════════════ 換股簿模擬（researchSector.sim_book ＋ 停止交易強制出場）
def sim_book(sel_by_e, P, dl, SF, t0, t1, mode="hold", n_slots=10):
    ncal = len(next(iter(P.values()))["c"])
    eq = np.ones(ncal); cash = 1.0
    pos = {}; pend = set()
    npos = np.zeros(ncal, np.int16); cashf = np.zeros(ncal); costd = np.zeros(ncal)
    buys = {}; hold_after = {}
    cnt = {"buy": 0, "sell": 0, "buy_blocked_limit_up": 0, "buy_blocked_halt": 0, "sell_delayed_days": 0, "delist_settled": 0,
           "delist_ambig_days": 0, "stop_force": 0, "cost_paid": 0.0}
    for t in range(t0, t1 + 1):
        # ── 停止交易強制出場（L＋1 以最後收盤賣、扣成本）
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt = pos.pop(s)
            px = P[s]["c"][t]
            cash += u * px - amt * COST; costd[t] += amt * COST; cnt["cost_paid"] += amt * COST; cnt["stop_force"] += 1
            pend.discard(s)
        sel = sel_by_e.get(t)
        if sel is not None:
            pend = set(pos) if mode == "all" else (pend | (set(pos) - set(sel))) - set(sel)
        for s in sorted(pend):
            x = P[s]; o_t = x["o"][t]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; cnt["delist_settled"] += 1
            else:
                cnt["sell_delayed_days"] += 1
                if (not x["trd"][t]) and s in dl and t > dl[s]["last"]:
                    cnt["delist_ambig_days"] += 1
                continue
            u, amt = pos.pop(s)
            cash += u * px - amt * COST; costd[t] += amt * COST; cnt["cost_paid"] += amt * COST; cnt["sell"] += 1
            pend.discard(s)
        if sel is not None:
            free = n_slots - len(pos)
            new = [s for s in sel if s not in pos][:max(free, 0)]
            nb = 0
            for s in new:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0):
                    cnt["buy_blocked_halt"] += 1; continue
                if x["up_o"][t]:
                    cnt["buy_blocked_limit_up"] += 1; continue
                amt = min(eq[t - 1] / n_slots, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[s] = [amt / o_t, amt]; nb += 1; cnt["buy"] += 1
            buys[t] = nb; hold_after[t] = sorted(pos)
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
    eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buys": buys, "hold": hold_after, "cnt": cnt}


def cell_stats(res, a, b, N, reb_seg, scs):
    c, m, ratio = seg_metrics(res["eq"], a, b)
    yrs = (b + 1 - a) / 245
    nb = sum(res["buys"].get(e, 0) for e in reb_seg)
    meq = float(res["eq"][a:b + 1].mean())
    sc = [x for e in reb_seg for x in scs.get(e, [])]
    return {"年化": c, "回落": m, "比值": ratio, "每年換手": nb / N / yrs, "成本／年": float(res["costd"][a:b + 1].sum()) / meq / yrs,
            "平均持股": float(res["npos"][a:b + 1].mean()), "現金比例": float(np.nanmean(res["cashf"][a:b + 1])),
            "入選平均分數": float(np.mean(sc)) if sc else float("nan"), "入選分數分佈": dict(sorted(Counter(sc).items())),
            "強制出場筆數": int(res["cnt"]["stop_force"])}


def load_px(args):
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    c = pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(float)
    o = st.df["open"].to_numpy(float)
    tb = TR.one(sid, cal)
    return sid, {"c": c, "o": o, "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"], "valid": np.isfinite(st.df["close"].to_numpy(float))}


def prep_part(part, a):
    FT = pickle.load(open(os.path.join(OUT, f"feat_{part}.pkl"), "rb"))
    D.DATA = FT["data"]
    cal = D.load_calendar()
    U = UG.gate3(pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str))
    mk = U.set_index("stock_id")["market"]
    sids = sorted(FT["F"])
    _G.update(cal=cal)
    with Pool(a.procs) as pool:
        P = dict(pool.map(load_px, [(s, mk.get(s, "twse")) for s in sids], chunksize=16))
    P = {s: v for s, v in P.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=off)
    bench = RR.load_bench(cal)
    FT.update(P=P, dl=dl, cal=cal, bench=bench, mk=mk)
    return FT


def run_cell(FT, VT, win, L, rb, N, vs, mode="hold"):
    cal = FT["cal"]; t0, t1 = pos_of(cal, win[0]), pos_of(cal, win[1])
    reb = reb_days(cal, t0, t1, rb == "季換")
    sel, scs = select(VT, reb, vs, N)
    SF = R.stop_force_days({s: v["valid"] for s, v in FT["P"].items()}, t1)
    res = sim_book(sel, FT["P"], FT["dl"], SF, t0, t1, mode, N)
    return res, sel, scs, reb


def _rand(args):
    r = args
    FT, VT, win, L, rb, N = _G["RAND"]
    cal = FT["cal"]; t0, t1 = pos_of(cal, win[0]), pos_of(cal, win[1])
    reb = reb_days(cal, t0, t1, rb == "季換")
    rng = np.random.default_rng([SEED_R, 1, r])
    sel = {}
    for e in reb:
        u = sorted(VT[e].index)
        k = min(N, len(u))
        sel[e] = [u[i] for i in rng.choice(len(u), size=k, replace=False)] if k else []
    res = sim_book(sel, FT["P"], FT["dl"], _G["SF"], t0, t1, "hold", N)
    out = {"r": r}
    for nm, (a_, b_) in _G["SEGP"].items():
        c, m, ratio = seg_metrics(res["eq"], a_, b_)
        out.update({f"{nm}_年化": c, f"{nm}_回落": m, f"{nm}_比值": ratio})
    return out


# ═════════════════════════════ 本體
def body(a):
    t00 = time.time()
    S = {"登錄": "PREREG合成分數 seq1 sha dbc1881f24a76661；裁定 seq254（N ＋1、§三 早年同判）、seq255 §五 5、seq257 順 6、seq261", "停止交易強制出場": "開"}
    S["程式"] = {f: sha(os.path.join(HERE, f)) for f in ("researchScore.py", "research11.py", "patterns_all.py", "rerun17.py", "researchSig.py", "researchRev.py")}
    S["快取"] = {k: sha(v, 64) for k, v in SIG_CACHE.items()}
    ref = {ln.split()[1]: ln.split()[0] for ln in open(os.path.join(HERE, "resultsSig", "PKL_SHA256.txt"), encoding="utf-8") if ln.strip()}
    S["快取_對 PKL_SHA256.txt"] = {k: ref.get(os.path.basename(v)) == S["快取"][k] for k, v in SIG_CACHE.items()}
    if not all(S["快取_對 PKL_SHA256.txt"].values()):
        raise SystemExit("⛔ sig 快取 sha 不符")
    # ── 主快照
    FT = prep_part("main", a)
    cal = FT["cal"]; n = len(cal)
    t0, t1 = pos_of(cal, MAIN_W[0]), pos_of(cal, MAIN_W[1])
    SEGP = {nm: (pos_of(cal, x), pos_of(cal, y)) for nm, (x, y) in SEG.items()}
    bench = FT["bench"]
    cf, mf = R13.window_stats(bench, 0, n, t0, t1 + 1)
    anchor = repr(float(cf)) == repr(0.24020209886370614) and repr(float(mf)) == repr(-0.3395700527611012)
    Z = {nm: seg_metrics(bench, x, y) for nm, (x, y) in SEGP.items()}
    log(f"[0050] 主窗錨逐位元 {anchor}｜" + "｜".join(f"{k} {v[0]:.2%}／{v[1]:.2%}／{v[2]:.3f}" for k, v in Z.items()))
    if not anchor:
        raise SystemExit("⛔ 0050 錨不過")
    # 閘：⑤ 去重後 ＝ signals_S；⑧ S06 ＝ resultsPatAll
    SS = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "signals_S.csv.gz"), dtype={"sid": str}, usecols=["sid", "pos"])
    mine5 = {(s, p) for s, f in FT["F"].items() for p in f.get("s5_pos", [])}
    ref5 = {(s, int(p)) for s, p in zip(SS["sid"], SS["pos"]) if s in FT["F"]}
    E6 = pd.read_csv(os.path.join(HERE, "resultsPatAll", "events_S06_上升三角_向上.csv.gz"), dtype={"sid": str}, usecols=["sid", "T"])
    lo8, hi8 = pd.Timestamp("2017-03-02"), pd.Timestamp(E6["T"].max())
    mine8 = {(s, str(cal[p].date())) for s, f in FT["F"].items() for p in f["ev8"] if lo8 <= cal[p] <= hi8}
    ref8 = {(s, t) for s, t in zip(E6["sid"], E6["T"]) if s in FT["F"]}
    S["閘"] = {"0050錨": anchor, "⑤ 去重後 ＝ signals_S（本母體）": {"自算": len(mine5), "檔": len(ref5), "只在自算": len(mine5 - ref5), "只在檔": len(ref5 - mine5)},
              "⑧ S06 ＝ resultsPatAll（本母體、2017-03-02～檔尾）": {"自算": len(mine8), "檔": len(ref8), "只在自算": len(mine8 - ref8), "只在檔": len(ref8 - mine8)}}
    log(f"[閘] {json.dumps(S['閘'], ensure_ascii=False)}")
    if mine5 != ref5 or mine8 != ref8:
        raise SystemExit("⛔ 票的閘不過")
    # ── 12 格
    VTs = {L: vote_table(FT, L) for L in LS}
    ROWS = []; RES = {}
    for L in LS:
        for rb in REBS:
            for N in NS:
                key = f"L{L}_{rb}_N{N}"
                res, sel, scs, reb = run_cell(FT, VTs[L], MAIN_W, L, rb, N, SETS["主版"])
                RES[key] = (res, sel, scs, reb)
                for nm, (x, y) in SEGP.items():
                    rs = [e for e in reb if x <= e <= y]
                    st = cell_stats(res, x, y, N, rs, scs)
                    ROWS.append({"格": key, "L": L, "換股": rb, "N": N, "段": nm, **{k: v for k, v in st.items() if k != "入選分數分佈"},
                                 "入選分數分佈": json.dumps(st["入選分數分佈"])})
                log(f"  {key}｜{time.time() - t00:.0f}s")
    T = pd.DataFrame(ROWS)
    ex = T[T["段"] == "探索"].copy()
    ex["退化"] = (ex["平均持股"] < ex["N"] / 2) | (ex["現金比例"] > 0.30)
    c0, m0, r0 = Z["探索"]
    ex["過判準"] = (ex["年化"] > c0) & (ex["比值"] >= r0)
    cand = ex[~ex["退化"]]
    pool_ = cand[cand["過判準"]] if cand["過判準"].any() else cand
    pool_ = pool_.assign(_rb=pool_["換股"].map({"月換": 0, "季換": 1}))
    best = pool_.sort_values(["比值", "年化", "L", "_rb", "N"], ascending=[False, False, True, True, True]).iloc[0]
    ck = best["格"]; L, rb, N = int(best["L"]), best["換股"], int(best["N"])
    T = T.merge(ex[["格", "退化", "過判準"]], on="格", how="left")
    cfm = T[(T["格"] == ck) & (T["段"] == "確認")].iloc[0]
    lab = label(cfm["年化"], cfm["回落"], Z["確認"][0], Z["確認"][1])
    T["標籤"] = [label(r_["年化"], r_["回落"], Z[r_["段"]][0], Z[r_["段"]][1]) for _, r_ in T.iterrows()]
    T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    S["探索挑格"] = {"退化格": ex.loc[ex["退化"], "格"].tolist(), "過判準格數": int(cand["過判準"].sum()), "挑中": ck,
                 "探索": {k: float(best[k]) for k in ("年化", "回落", "比值")}}
    S["確認"] = {"年化": float(cfm["年化"]), "回落": float(cfm["回落"]), "比值": float(cfm["比值"]), "判定": lab}
    S["0050"] = {nm: dict(zip(("年化", "回落", "比值"), v)) for nm, v in Z.items()}
    log(f"[挑格] 退化 {S['探索挑格']['退化格']}｜過判準 {S['探索挑格']['過判準格數']}／{len(cand)}｜挑中 {ck}｜確認 {cfm['年化']:.2%}／{cfm['回落']:.2%} ⇒ 【{lab}】")
    # ── 挑中格：全賣全買、命中率、相關
    res_all, *_ = run_cell(FT, VTs[L], MAIN_W, L, rb, N, SETS["主版"], mode="all")
    res_h, sel_h, scs_h, reb_h = RES[ck]
    S["全賣全買"] = {nm: {"年化": seg_metrics(res_all["eq"], x, y)[0], "續抱年化": seg_metrics(res_h["eq"], x, y)[0],
                      "成本／年": float(res_all["costd"][x:y + 1].sum()) / float(res_all["eq"][x:y + 1].mean()) / ((y + 1 - x) / 245)} for nm, (x, y) in SEGP.items()}
    VT = VTs[L]
    # 落檔給查核：挑中格名單、挑中 L 的票表、權益
    pd.DataFrame([{"e": e, "date": str(cal[e].date()), "rank": i + 1, "sid": s_, "score": sc_} for e in reb_h for i, (s_, sc_) in enumerate(zip(sel_h[e], scs_h.get(e, [])))]
                 ).to_csv(os.path.join(OUT, "picks.csv.gz"), index=False)
    pd.concat([VT[e].assign(e=e) for e in reb_days(cal, t0, t1) if len(VT[e])]).rename_axis("sid").reset_index().to_csv(
        os.path.join(OUT, f"votes_L{L}.csv.gz"), index=False)
    np.savez_compressed(os.path.join(OUT, "eq.npz"), main=res_h["eq"], all=res_all["eq"], bench=bench, t0=t0, t1=t1)
    hit = {}
    for nm, (x, y) in SEGP.items():
        rs = [e for e in reb_h if x <= e <= y]
        tot = sum(len(sel_h[e]) for e in rs)
        hit[nm] = {VNAME[v]: sum(int(VT[e].loc[sel_h[e], v].sum()) for e in rs if sel_h[e]) / tot for v in VOTES}
        hit[nm]["母體平均（同段股-月）"] = {VNAME[v]: float(pd.concat([VT[e][v] for e in rs if len(VT[e])]).mean()) for v in VOTES}
    S["命中率"] = hit
    allrows = pd.concat([VT[e][VOTES].astype(int) for e in reb_days(cal, t0, t1) if len(VT[e])])
    C = allrows.corr()
    C.index = [VNAME[v] for v in C.index]; C.columns = [VNAME[v] for v in C.columns]
    C.to_csv(os.path.join(OUT, f"corr_L{L}.csv"))
    pairs = sorted(((C.iloc[i, j], C.index[i], C.columns[j]) for i in range(11) for j in range(i + 1, 11)), key=lambda z: -abs(z[0]) if np.isfinite(z[0]) else 0)
    S["兩兩相關"] = {"L": L, "股-月": int(len(allrows)), "前 10 對": [(a_, b_, float(r_)) for r_, a_, b_ in pairs[:10]],
                   "|r|≥0.3 的對數": int(sum(1 for r_, *_ in pairs if np.isfinite(r_) and abs(r_) >= 0.3))}
    # ── 描述臂 甲／乙
    ARM = {}
    for arm in ("甲", "乙"):
        res_, sel_, scs_, reb_ = run_cell(FT, VT, MAIN_W, L, rb, N, SETS[arm])
        ARM[arm] = {nm: cell_stats(res_, x, y, N, [e for e in reb_ if x <= e <= y], scs_) for nm, (x, y) in SEGP.items()}
    # ── 丙 隨機
    SF = R.stop_force_days({s: v["valid"] for s, v in FT["P"].items()}, t1)
    _G.update(RAND=(FT, VT, MAIN_W, L, rb, N), SF=SF, SEGP=SEGP)
    tr = time.time()
    with Pool(a.procs) as pool:
        RD = pd.DataFrame(pool.map(_rand, range(a.reps), chunksize=10))
    RD.to_csv(os.path.join(OUT, "random.csv.gz"), index=False)
    log(f"[丙 隨機] {a.reps} 次｜{time.time() - tr:.0f}s")
    RAND = {}
    for nm in SEGP:
        x = RD[f"{nm}_年化"].to_numpy(float)
        main_c = float(T[(T["格"] == ck) & (T["段"] == nm)]["年化"].iloc[0])
        RAND[nm] = {"中位": float(np.median(x)), "p10": float(np.quantile(x, .1)), "p90": float(np.quantile(x, .9)),
                    "回落中位": float(RD[f"{nm}_回落"].median()),
                    "p_主版": float(np.mean(x >= main_c)), "p_甲": float(np.mean(x >= ARM["甲"][nm]["年化"])), "p_乙": float(np.mean(x >= ARM["乙"][nm]["年化"])),
                    "贏0050比例": float(np.mean(x > Z[nm][0]))}
    # ── 丁 營量 v1（T1）
    RR.use_snapshot()
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", lambda x: None, t1=True)
    G = RR._G; AND = G["AND"]; e_ = AND["entry_pos"].to_numpy()
    sig13 = AND[(e_ >= G["w0"]) & (e_ <= G["w1"])]
    SF13 = R.stop_force_days(R.valid_from_data(sorted(G["closes"]), FT["mk"], cal), G["w1"])
    o13 = R.simulate_mtm(sig13, "H60", 20, np.random.default_rng(RR.P1_SEED0), G["closes"], G["opens"], G["ncal"], log=[], d_max=None,
                         pick="relvol", queue_days=0, return_equity=True, stop_force=SF13)
    eq13 = np.asarray(o13["equity"], float)
    c13, m13, _ = RR.win_metrics(eq13, o13["first"], o13["end"], G["w0"], G["w1"])
    Y13 = {nm: dict(zip(("年化", "回落"), R13.window_stats(eq13, min(o13["first"], x), max(o13["end"], y + 1), x, y + 1))) for nm, (x, y) in SEGP.items()}
    S["營量v1_T1"] = {"主窗": {"年化": float(c13), "回落": float(m13)}, **{k: {kk: float(vv) for kk, vv in v.items()} for k, v in Y13.items()},
                    "＝ resultsT1fix c13 t1（逐位元）": _t1ref(c13, m13)}
    if not S["營量v1_T1"]["＝ resultsT1fix c13 t1（逐位元）"]:
        raise SystemExit("⛔ 營量 v1 T1 與 resultsT1fix 不同")
    S["描述臂"] = {"甲": ARM["甲"], "乙": ARM["乙"], "丙": RAND}
    S["挑中格"] = {nm: cell_stats(res_h, x, y, N, [e for e in reb_h if x <= e <= y], scs_h) for nm, (x, y) in SEGP.items()}
    S["挑中格"]["計數"] = res_h["cnt"]
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # ── 早年
    early(a, S, ck, L, rb, N)
    S["秒"] = round(time.time() - t00)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report()


def _t1ref(c, m):
    t = pd.read_csv(os.path.join(HERE, "resultsT1fix", "cells.csv"), float_precision="round_trip").set_index("key")
    return repr(float(t.at["c13", "t1_年化"])) == repr(float(c)) and repr(float(t.at["c13", "t1_回落"])) == repr(float(m))


def early(a, S, ck, L, rb, N):
    OUTE = {}
    for part, win in (("A", EARLY_A), ("B", EARLY_B)):
        FT = prep_part("A" if part == "A" else "main", a)
        cal = FT["cal"]
        if part == "B":
            tw = {s for s, m_ in FT["mk"].items() if m_ == "twse"}
            FT["ELIG"] = {e: [s for s in v if s in tw] for e, v in FT["ELIG"].items()}
        VT = vote_table(FT, L)
        res, sel, scs, reb = run_cell(FT, VT, win, L, rb, N, SETS["主版"])
        x, y = pos_of(cal, win[0]), pos_of(cal, win[1])
        st = cell_stats(res, x, y, N, reb, scs)
        b = seg_metrics(FT["bench"], x, y)
        rows = pd.concat([VT[e][VOTES].astype(int) for e in reb if len(VT[e])])
        OUTE[part] = {"窗": list(win), "資料": FT["data"], **{k: v for k, v in st.items()}, "0050": dict(zip(("年化", "回落", "比值"), b)),
                      "標籤": label(st["年化"], st["回落"], b[0], b[1]), "母體股-月": int(len(rows)),
                      "各票母體成立比例": {VNAME[v]: float(rows[v].mean()) for v in VOTES}, "計數": res["cnt"]}
        log(f"[早年 {part}] {win}｜{st['年化']:.2%}／{st['回落']:.2%}（0050 {b[0]:.2%}／{b[1]:.2%}）⇒ {OUTE[part]['標籤']}")
    RR.use_snapshot()
    S["早年"] = OUTE
    la, lc = OUTE["A"]["標籤"], S["確認"]["判定"]
    S["判定句"] = ("只在看過的那段合格" if (lc == "合格" and la != "合格") else lc)


def _p(x):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    ck = S["探索挑格"]["挑中"]; cf = S["確認"]; Z = S["0050"]; E = S.get("早年", {}); RD = S["描述臂"]["丙"]; ARM = S["描述臂"]
    y13 = S["營量v1_T1"]
    L_ = ["# PREREG合成分數 seq1：11 票等權投票選股", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 sha dbc1881f24a76661；裁定 seq254、seq255 §五 5、seq257、seq261。回測線。⭐ **{TAG}**。", ""]
    part = ck.split("_")
    L_.append(f"**結論：11 個條件等權投票、每{part[1][0]}挑前 {part[2][1:]} 檔（近 {part[0][1:]} 日），2022～2026 年化 {_p(cf['年化'])}／回落 {_p(cf['回落'])}"
              f"（0050 {_p(Z['確認']['年化'])}／{_p(Z['確認']['回落'])}）⇒ 確認段【{cf['判定']}】；早年 A 段 {E.get('A', {}).get('標籤', '—')} ⇒ 判定句「{S.get('判定句', cf['判定'])}」。"
              f"只用弱的 6 個合起來：確認段年化 {_p(ARM['乙']['確認']['年化'])}，隨機挑 {_p(RD['確認']['中位'])}（p ＝ {RD['確認']['p_乙']:.3f}）⇒ 弱訊號合起來"
              + ("【有】" if RD['確認']['p_乙'] < 0.05 else "【沒有】") + "比隨機好。**")
    L_ += ["", "| 項（挑中格同 L／換股／檔數） | 探索 | 確認 | 早年 A（2012-06～2014-12） |", "|---|---|---|---|"]
    ex = T[(T["格"] == ck) & (T["段"] == "探索")].iloc[0]
    L_.append(f"| 主版 11 票 | {_p(ex['年化'])}／{_p(ex['回落'])} | {_p(cf['年化'])}／{_p(cf['回落'])} {cf['判定']} | "
              f"{_p(E['A']['年化'])}／{_p(E['A']['回落'])} {E['A']['標籤']} |" if E else "")
    for arm, nm in (("甲", "甲 只用強的 5 票"), ("乙", "乙 只用弱的 6 票")):
        L_.append(f"| {nm} | {_p(ARM[arm]['探索']['年化'])}／{_p(ARM[arm]['探索']['回落'])} | {_p(ARM[arm]['確認']['年化'])}／{_p(ARM[arm]['確認']['回落'])} | — |")
    L_.append(f"| 丙 隨機挑（1,000 次中位；p 主版） | {_p(RD['探索']['中位'])}（p {RD['探索']['p_主版']:.3f}） | {_p(RD['確認']['中位'])}（p {RD['確認']['p_主版']:.3f}） | — |")
    L_.append(f"| 丁 營量 v1（T1） | {_p(y13['探索']['年化'])}／{_p(y13['探索']['回落'])} | {_p(y13['確認']['年化'])}／{_p(y13['確認']['回落'])} | — |")
    L_.append(f"| 0050 | {_p(Z['探索']['年化'])}／{_p(Z['探索']['回落'])} | {_p(Z['確認']['年化'])}／{_p(Z['確認']['回落'])} | {_p(E['A']['0050']['年化'])}／{_p(E['A']['0050']['回落'])} |" if E else "")
    L_ += ["", "## 一、12 格（探索段挑、確認段判；⛔ 只有挑中那格計入判定）", "",
           "| 格 | 段 | 年化 | 回落 | 比值 | 標籤 | 每年換手 | 成本／年 | 平均持股 | 現金 | 入選平均分數 | 退化 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in T.sort_values(["格", "段"]).iterrows():
        L_.append(f"| {r['格']}{' ⭐' if r['格'] == ck else ''} | {r['段']} | {_p(r['年化'])} | {_p(r['回落'])} | {r['比值']:.3f} | {r['標籤']} | {r['每年換手']:.2f} | "
                  f"{r['成本／年'] * 100:.2f}% | {r['平均持股']:.1f} | {r['現金比例'] * 100:.1f}% | {r['入選平均分數']:.2f} | {'是' if r['退化'] else ''} |")
    L_ += ["", f"- 挑法：探索段排除退化格（{S['探索挑格']['退化格'] or '無'}）後，過判準 {S['探索挑格']['過判準格數']} 格；挑中 **{ck}**",
           f"- 0050：探索 {_p(Z['探索']['年化'])}／{_p(Z['探索']['回落'])}（比值 {Z['探索']['比值']:.3f}）；確認 {_p(Z['確認']['年化'])}／{_p(Z['確認']['回落'])}（比值 {Z['確認']['比值']:.3f}）",
           f"- 全賣全買（成本敏感度）：確認段 年化 {_p(S['全賣全買']['確認']['年化'])}（續抱 {_p(S['全賣全買']['確認']['續抱年化'])}）、成本／年 {S['全賣全買']['確認']['成本／年'] * 100:.2f}%",
           f"- 挑中格計數：{json.dumps(S['挑中格']['計數'], ensure_ascii=False)}", ""]
    L_ += ["## 二、早年段（裁定 seq254 §三：同判準並報；只上市）", ""]
    for p_, nm in (("A", "A 段（early 版面；⭐ 判定用）"), ("B", "B 段（主快照；⚠ 資料起點 2015-01 ⇒ 部分票依構造算不出，⛔ 不用於判定）")):
        e = E[p_]
        L_.append(f"- {nm} {e['窗'][0]}～{e['窗'][1]}：{_p(e['年化'])}／{_p(e['回落'])}（0050 {_p(e['0050']['年化'])}／{_p(e['0050']['回落'])}）⇒ {e['標籤']}；"
                  f"平均持股 {e['平均持股']:.1f}、現金 {e['現金比例'] * 100:.1f}%、每年換手 {e['每年換手']:.2f}")
        L_.append("  - 各票在母體成立比例：" + "、".join(f"{k} {v * 100:.1f}%" for k, v in e["各票母體成立比例"].items()))
    L_ += ["", f"- 判定句：**{S['判定句']}**（規則 seq254 §三：確認段合格而早年 A 段不合格才寫「只在看過的那段合格」；本件確認段已是「{S['確認']['判定']}」）", ""]
    L_ += ["## 三、每一票的命中率（入選股-月中有該票的比例）與母體成立比例", "", "| 票 | 探索 入選 | 探索 母體 | 確認 入選 | 確認 母體 |", "|---|---|---|---|---|"]
    H = S["命中率"]
    for v in VOTES:
        k = VNAME[v]
        L_.append(f"| {k} | {H['探索'][k] * 100:.1f}% | {H['探索']['母體平均（同段股-月）'][k] * 100:.1f}% | {H['確認'][k] * 100:.1f}% | {H['確認']['母體平均（同段股-月）'][k] * 100:.1f}% |")
    C = S["兩兩相關"]
    L_ += ["", f"## 四、各票兩兩相關（挑中格 L＝{C['L']}；主窗母體股-月 {C['股-月']:,}；全表 corr_L{C['L']}.csv）", "",
           f"- |r| ≥ 0.3 的對數：{C['|r|≥0.3 的對數']}／55", "- 前 10 對：" + "；".join(f"{a_}×{b_} {r_:+.2f}" for a_, b_, r_ in C["前 10 對"]), ""]
    L_ += ["## 五、描述臂（⛔ 不判）", ""]
    for arm, nm in (("甲", "甲 只用強的 5 票（①～⑤）"), ("乙", "乙 只用弱的 6 票（⑥～⑪）")):
        x = ARM[arm]
        L_.append(f"- {nm}：探索 {_p(x['探索']['年化'])}／{_p(x['探索']['回落'])}；確認 {_p(x['確認']['年化'])}／{_p(x['確認']['回落'])}；"
                  f"確認段入選平均分數 {x['確認']['入選平均分數']:.2f}、每年換手 {x['確認']['每年換手']:.2f}")
    L_ += [f"- 丙 隨機挑同檔數 1,000 次：確認中位 {_p(RD['確認']['中位'])}（p10 {_p(RD['確認']['p10'])}、p90 {_p(RD['確認']['p90'])}）；"
           f"p（隨機 ≥ 主版）＝ {RD['確認']['p_主版']:.3f}、≥ 甲 {RD['確認']['p_甲']:.3f}、≥ 乙 {RD['確認']['p_乙']:.3f}；隨機贏 0050 的比例 {RD['確認']['贏0050比例']:.3f}"
           + ("；⚠ p ≥ 0.05 ⇒ 隨機挑也做得到" if RD['確認']['p_主版'] >= 0.05 else ""),
           f"- 丁 營量 v1（T1、強制出場開）：主窗 {_p(y13['主窗']['年化'])}／{_p(y13['主窗']['回落'])}；確認 {_p(y13['確認']['年化'])}／{_p(y13['確認']['回落'])}", ""]
    L_ += ["## 六、出場敏感度（seq242 ③）", "", ("- 確認段判定為「" + cf["判定"] + "」⇒ " + ("見 exit_sens（另跑）" if cf["判定"] in ("合格", "另列") else "非合格／另列 ⇒ 不跑")), ""]
    L_ += ["## 七、閘與讀法", "", f"- 閘：{json.dumps(S['閘'], ensure_ascii=False)}",
           f"- sig 快取 sha 對 resultsSig/PKL_SHA256.txt：{S['快取_對 PKL_SHA256.txt']}",
           "- ★ 同分抽籤不優先舊持股（登錄「分數相同 ⇒ 抽籤」、「仍入選 ⇒ 續抱」照字面：先排名、再看舊持股在不在名單）",
           "- ★ 早年段：A 段 2012-06-01～2014-12-30 判定；B 段只報（主快照資料 2015-01 起 ⇒ ① 24 期、③ 250 日、⑤ 249 根、⑨ 250 日依構造不足）",
           "- ⑤ 是「5 條 ≥3」的狀態（⛔ 不做營飆 S 訊號的 20 日去重）；閘驗去重後與 signals_S 逐列同",
           "- 本件是換股簿、無排程出場 ⇒ 依構造沒有資料尾截斷；營量 v1 用 T1 版", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(x for x in L_ if x is not None) + "\n")


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["feat", "body", "report"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--part", default="main,A"); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--out", default="")
    a = ap.parse_args()
    global OUT
    if a.out:
        OUT = a.out
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    log(f"===== researchScore {a.mode} procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    if a.mode == "feat":
        for part in a.part.split(","):
            build_part(part, a)
    elif a.mode == "body":
        body(a)
    else:
        report()


if __name__ == "__main__":
    main()
