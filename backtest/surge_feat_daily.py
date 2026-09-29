# -*- coding: utf-8 -*-
"""每日起漲特徵（overlap 的 14 個 ＋ 買賣流程要用的幾欄）——回測線，給每日名單（daily_list.py）用。

⭐ 定義與 s5work 建表一字不差：逐行照抄 researchSurge5.stock() 對應的段落（壞根 S3、漲停旗標、營收可得日、財報 A2、注意處置、融資），
   橫斷面五等分用 researchSurge5.qtie（S10：當日有 K 棒的母體、同值同組）；母體 ＝ universe_gate.gate3（innov_ky 開）
   特徵清單 ＝ researchSurge6_overlap.FEATS（不另抄）
   只算需要的欄；營收、財報只在要的日子上算（其餘段落與建表同一順序、同一式子）
 ⭐ 原值一律先存成 float32 再排五等分（建表 F 表是 float32；float64 會讓少數剛好在分界的同值被分開）
資料：
   價量（stocks、adj、meta、mops/revenue_hist）＝ price_dir；融資、法人、財報、注意處置 ＝ aux_dir（有 stocks_margin、stocks_inst、mops/fin_hist、meta）
   每日名單：price_dir ＝ ~/h2data/<sha>/data（run_daily_list.sh 已 archive）；aux_dir ＝ ensure_aux(sha) 另外 archive 那四棵子樹到 ~/h2data/surgeaux_<key>/data（唯讀）
   閘門 G1（surge_feat_daily_check.py）：price_dir ＝ s5work 的接合版面、aux_dir ＝ s5work 的 main archive、early_dir ＝ 早年版面 ⇒ 與 s5work Q 表逐格比
"""
from __future__ import annotations

import glob
import os
import subprocess
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backtest import data as D
from backtest import universe_gate as UG
from backtest import research11 as R11
from backtest import research34 as R34
from backtest import p4_features as P4F
from backtest import surge_features as SF
from backtest import researchSurge5 as S5
from backtest.researchSurge6_overlap import FEATS, SHORT

UG.set_innov_ky(True)
REPO = os.path.expanduser("~/tw-p17")
EARLY = S5.EARLY                                          # 早年營收（2003～2014，固定版面 950ad26e12）：建表的營收可得值會一路往回找到最後一期有值（含早年）⇒ 每日也要帶，否則少數長期未申報的檔會從「0」變「沒值」
QCOLS = ["dlo_5", "dlo_10", "ma_5", "r_5", "turn_60", "r_120", "musage", "att_10", "lu_5", "disp_250"]      # 橫斷面五等分
LCOLS = ["d_px", "d_att60", "d_lu20", "d_bull", "d_R2a", "d_eps", "d_revhi"]                                # 值＋1（0 ＝ 沒值）
RCOLS = ["disp_60"]                                                                                          # 原值
SPAN = {"r_5": 6, "dlo_5": 6, "dlo_10": 11, "ma_5": 6, "turn_60": 61, "r_120": 121, "lu_5": 6}              # 同 researchSurge5.stock 的 span
_G: dict = {}


def ensure_aux(sha):
    """把 stocks_margin、stocks_inst、mops/fin_hist、meta 四棵子樹 git archive 到 ~/h2data/surgeaux_<key>/data（唯讀；依內容 key，重跑不重做）。"""
    subs = ["data/meta", "data/mops/fin_hist", "data/stocks_inst", "data/stocks_margin"]
    tid = [subprocess.run(["git", "-C", REPO, "rev-parse", f"{sha}:{p}"], capture_output=True, text=True, check=True).stdout.strip() for p in subs]
    key = subprocess.run(["sha1sum"], input="\n".join(tid) + "\n", capture_output=True, text=True).stdout[:16]
    dk = os.path.expanduser(f"~/h2data/surgeaux_{key}")
    if not os.path.isdir(os.path.join(dk, "data", "stocks_margin")):
        os.makedirs(dk, exist_ok=True)
        p1 = subprocess.Popen(["git", "-C", REPO, "archive", sha, *subs], stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", dk], stdin=p1.stdout, check=True); p1.wait()
        subprocess.run(["chmod", "-R", "a-w", dk], check=True)
    return os.path.join(dk, "data")


def world(price_dir, aux_dir, early_dir=None):
    """researchSurge5.world 的對應段落（營收、營收旗標、可得日、財報、注意處置），路徑參數化。"""
    D.DATA = price_dir
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(price_dir, "meta", "stocks.csv"), dtype=str)
    uni = UG.gate3(stocks)
    have = {f[:-4] for f in os.listdir(os.path.join(price_dir, "stocks"))}
    uni = uni[uni["stock_id"].isin(have)].sort_values("stock_id").reset_index(drop=True)
    rev_dir = aux_dir if os.path.isdir(os.path.join(aux_dir, "mops", "revenue_hist")) else price_dir          # 建表：main archive；每日：每日 archive
    fs = (sorted(glob.glob(os.path.join(early_dir, "mops", "revenue_hist", "*.csv"))) if early_dir else []) + sorted(glob.glob(os.path.join(rev_dir, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    calf = cal
    if early_dir:                                          # 每日版的日曆從 2015 起 ⇒ 營收旗標先在「早年＋main」日曆上算、再切回（建表的接合日曆本來就含早年）
        ec = pd.to_datetime(pd.read_csv(os.path.join(early_dir, "meta", "calendar_twse.csv"))["date"])
        ec = ec[ec < cal[0]]
        if len(ec):
            calf = pd.DatetimeIndex(list(ec) + list(cal))
    W = {"cal": cal, "REV": rev, "REVFLAG": P4F.rev_hi24_flags(rev, calf).reindex(cal), "price_dir": price_dir, "aux_dir": aux_dir}
    rd = R34.rebalance_dates(list(rev.index), cal, 10)
    W["REV_EFF"] = np.array([rd[p][1] if p in rd else (n + 10 if pd.Period(p) > pd.Period(str(cal[-1])[:7]) else -1) for p in rev.index])
    W.update(SF.fin_table(aux_dir, cal)); W["ATT"], W["DISP"] = SF.att_disp(aux_dir, cal)
    W["ATT_FIRST"] = int(cal.searchsorted(pd.Timestamp("2011-01-03")))
    return W, uni


def _init(W, d0, d1):
    _G.clear(); _G.update(W); _G["d0"] = d0; _G["d1"] = d1; D.DATA = W["price_dir"]


def _roll(x, w, fn):
    return getattr(pd.Series(x).rolling(w, min_periods=w), fn)().to_numpy()


def stock(args):
    """⇒ (si, {欄: 日曆位置 d0..d1 的原值（沒 K 棒 ＝ NaN）, "bar": ...})；式子逐行同 researchSurge5.stock。"""
    si, sid, mk = args
    W = _G; cal = W["cal"]; n = len(cal); d0, d1 = W["d0"], W["d1"]; PD = W["price_dir"]; AX = W["aux_dir"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return si, None
    df = st.df
    cA = df["close"].to_numpy(float); hA = df["high"].to_numpy(float); lA = df["low"].to_numpy(float)
    idx = np.flatnonzero(np.isfinite(cA)); m = len(idx)
    if m < 2:
        return si, None
    raw = pd.read_csv(os.path.join(PD, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "open", "high", "low", "close", "shares"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rr = {k: np.array(pd.to_numeric(raw[k], errors="coerce"), dtype=float) for k in ("open", "high", "low", "close")}
    for k in rr:
        rr[k][~(rr[k] > 0)] = np.nan
    shA = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float); shA = np.where(shA > 0, shA, np.nan)
    c = cA[idx]
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
    rc = rr["close"][idx]; sh = shA[idx]; dates = cal[idx]
    # 壞根（S3）
    adj = D.load_adj(sid)
    ev_bar = np.zeros(m, bool); bad_k = np.zeros(m, bool)
    if adj is not None and len(adj):
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dates, d))
            if k >= m:
                continue
            ev_bar[k] = True
            if k > 0 and np.isfinite(rc[k]) and np.isfinite(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    bad_k[k] = True
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < m:
                bad_k[k] = True
    cbk = np.r_[0, np.cumsum(bad_k)]
    skip = ev_bar.copy()
    if dates[0] > pd.Timestamp("2015-01-12"):
        skip[:5] = True
    up, _dn = R11.limit_flags(rc, dates, skip)
    Fk = {}
    rS = lambda w_: np.r_[np.full(w_, np.nan), c[w_:] / c[:-w_] - 1] if w_ < m else np.full(m, np.nan)
    ma = {w_: _roll(c, w_, "mean") for w_ in (5, 20, 60, 100)}
    Fk["r_5"] = rS(5); Fk["r_120"] = rS(120)
    Fk["dlo_5"] = c / _roll(c, 5, "min") - 1; Fk["dlo_10"] = c / _roll(c, 10, "min") - 1
    Fk["ma_5"] = c / ma[5] - 1
    Fk["turn_60"] = _roll(vol / sh, 60, "mean")
    Fk["lu_5"] = _roll(up.astype(float), 5, "sum")
    Fk["d_bull"] = np.where(np.isfinite(ma[100]), ((ma[5] > ma[20]) & (ma[20] > ma[60]) & (ma[60] > ma[100])).astype(float), np.nan)
    Fk["d_px"] = np.where(np.isfinite(rc), np.where(rc < 20, 0, np.where(rc < 50, 1, np.where(rc < 100, 2, 3))), np.nan).astype(float)
    Fk["d_lu20"] = np.minimum(_roll(up.astype(float), 20, "sum"), 3)
    pos_d = idx; want = np.flatnonzero((pos_d >= d0) & (pos_d <= d1))
    # 營收（只在要的日子）
    Fk["d_R2a"] = np.full(m, np.nan); Fk["d_revhi"] = np.full(m, np.nan)
    V = W["REV"][sid].to_numpy(float) if sid in W["REV"].columns else None
    if V is not None:
        eff = W["REV_EFF"]
        yoy = np.full(len(V), np.nan); yoy[12:] = np.where((V[:-12] > 0) & np.isfinite(V[:-12]), V[12:] / V[:-12] - 1, np.nan)
        order = np.argsort(eff, kind="stable"); effs = eff[order]
        for i in want:
            j = int(np.searchsorted(effs, pos_d[i], side="right")) - 1
            if j < 0:
                continue
            kx = order[j]
            while kx >= 0 and not np.isfinite(V[kx]):
                kx -= 1
            if kx < 0:
                continue
            Fk["d_R2a"][i] = float(yoy[kx] >= 0.5) if np.isfinite(yoy[kx]) else np.nan
    if sid in W["REVFLAG"].columns:
        fv = W["REVFLAG"][sid].to_numpy(float)[pos_d]
        Fk["d_revhi"] = np.where(np.isfinite(fv), (fv == 100).astype(float), np.nan)
    # 財報 A2（只在要的日子）
    Fk["d_eps"] = np.full(m, np.nan)
    fr = W["FIN"].get(sid)
    if fr:
        fpos = np.array([x[0] for x in fr])
        for i in want:
            cj = np.flatnonzero(fpos <= pos_d[i])
            if len(cj) == 0:
                continue
            j = int(cj[-1]); _, y, q, eps, gm, opm, roe = fr[j]
            pv = fr[j - 1] if j >= 1 else None
            if pv is not None and (pv[1], pv[2]) == ((y, q - 1) if q > 1 else (y - 1, 4)):
                if np.isfinite(eps) and np.isfinite(pv[3]):
                    Fk["d_eps"][i] = float(eps > 0 and pv[3] <= 0)
    # 融資使用率
    Fk["musage"] = np.full(m, np.nan)
    p_ = os.path.join(AX, "stocks_margin", sid + ".csv")
    if os.path.exists(p_):
        mg = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "m_balance", "m_limit", "note"]).drop_duplicates("date", keep="last")
        mg.index = pd.to_datetime(mg["date"])
        mb = pd.to_numeric(mg["m_balance"], errors="coerce").reindex(cal).ffill().to_numpy()
        ml = pd.to_numeric(mg["m_limit"], errors="coerce").reindex(cal).ffill().to_numpy()
        has = mg["m_balance"].reindex(cal).notna().to_numpy()
        Fk["musage"] = np.where(has[pos_d] & (ml[pos_d] > 0), mb[pos_d] / np.where(ml[pos_d] > 0, ml[pos_d], 1), np.nan)
    # 注意、處置
    af = W["ATT_FIRST"]; ad = W["ATT"].get(sid, np.zeros(0, int))
    dday = np.zeros(n, bool)
    for a_, b_ in W["DISP"].get(sid, []):
        dday[max(a_, 0):min(b_, n - 1) + 1] = True
    cdd = np.r_[0, np.cumsum(dday)]
    for L, nm in ((10, "att_10"),):
        cnt = np.searchsorted(ad, pos_d, side="right") - np.searchsorted(ad, pos_d - L + 1, side="left")
        Fk[nm] = np.where(pos_d - L + 1 >= af, cnt, np.nan).astype(float)
    for L in (60, 250):
        Fk[f"disp_{L}"] = np.where(pos_d - L + 1 >= af, cdd[pos_d + 1] - cdd[np.maximum(pos_d - L + 1, 0)], np.nan).astype(float)
    cnt60 = np.searchsorted(ad, pos_d, side="right") - np.searchsorted(ad, pos_d - 59, side="left")
    Fk["d_att60"] = np.where(pos_d - 59 >= af, np.where(cnt60 == 0, 0, np.where(cnt60 <= 2, 1, 2)), np.nan).astype(float)
    # 回看窗內有壞根 ⇒ NaN（S3）
    for k_, sp in SPAN.items():
        kk = np.arange(m); nb_ = cbk[kk + 1] - cbk[np.maximum(kk + 1 - sp, 0)]
        Fk[k_] = np.where(nb_ > 0, np.nan, Fk[k_])
    out = {}
    nd = d1 - d0 + 1; sel = pos_d[want] - d0
    for k_ in QCOLS + LCOLS + RCOLS:
        v = np.full(nd, np.nan); v[sel] = np.asarray(Fk[k_], float)[want]; out[k_] = v
    b = np.zeros(nd, bool); b[sel] = True; out["bar"] = b
    return si, out


def compute(price_dir, aux_dir, d0=None, d1=None, early_dir=None, procs=2, log=print, W=None, uni=None):
    """⇒ dict：cal、uni、d0、d1、bar (S×nd)、code {欄: S×nd int8（Q 表同碼）}、raw {原值欄: S×nd}。"""
    if W is None:
        W, uni = world(price_dir, aux_dir, early_dir)
    cal = W["cal"]; n = len(cal)
    d1 = n - 1 if d1 is None else d1; d0 = d1 if d0 is None else d0
    S = len(uni); nd = d1 - d0 + 1
    RAW = {k: np.full((S, nd), np.nan, np.float32) for k in QCOLS + LCOLS + RCOLS}; BAR = np.zeros((S, nd), bool)          # ⭐ float32：建表的 F 表是 float32、五等分在 float32 上排（同值同組）; BAR = np.zeros((S, nd), bool)
    args = list(zip(range(S), uni["stock_id"], uni["market"]))
    with Pool(procs, initializer=_init, initargs=(W, d0, d1)) as pool:
        for si, o in pool.imap_unordered(stock, args, chunksize=8):
            if o is None:
                continue
            BAR[si] = o["bar"]
            for k in RAW:
                RAW[k][si] = o[k]
    CODE = {}
    for k in QCOLS:
        q = np.zeros((S, nd), np.int8)
        for t in range(nd):
            b = BAR[:, t]
            if b.any():
                q[b, t] = S5.qtie(RAW[k][b, t])
        CODE[k] = q
    for k in LCOLS:
        CODE[k] = np.where(np.isfinite(RAW[k]) & BAR, RAW[k] + 1, 0).astype(np.int8)
    log(f"[起漲特徵] {S} 檔｜{cal[d0].date()}～{cal[d1].date()}")
    return {"cal": cal, "uni": uni, "d0": d0, "d1": d1, "bar": BAR, "code": CODE, "raw": RAW, "W": W}


def feat14(R):
    """⇒ (有 S×nd×14 bool, 個數 S×nd)"""
    has = np.stack([R["code"][col] == code for _, col, code in FEATS], -1)
    return has, has.sum(-1)
