# -*- coding: utf-8 -*-
"""PREREG碰撞回落底部（BARR 底）seq2（台股策略線登錄 sha e5021a177af9277d，2026-10-10 23:38；裁定 seq324 §三發號、seq326 §一三處改正）——回測線計算子代理。
⛔ 本次只做 freq 模式：出現頻率與各年筆數；⛔ 不算任何報酬（裁定 seq324 §三、seq326 §一：報酬排在 seq322 五件之後，另派）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBARR freq [--procs 2] [--smoke]

⭐ 讀法寫死時間：2026-10-10 23:55（台北）；寫死前 ⛔ 沒算任何本件數字（只看過登錄全文 seq2、裁定 seq324／seq326、既有程式與資料格式）。

═══ 讀法（B 標；登錄沒寫清楚、執行者補的都在這裡）═══
 B1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ e5021a177af9277d 才跑（信箱只讀）
 B2 版面：早年 ~/earlydata/eotc_f65bb03e11/otc/data（2004-02-11～2014-12-31；上市＋上櫃，⚠ 上櫃日 K 2007-07 起）＋ main ＝ rerun17 快照 H2D
    （edc6f8002f；2015-01-05～2026-09-24）；每檔在記憶體裡逐列相接（日曆相接、不重疊）；還原：早年段 ＝ 早年還原價 × main 第一個（≥ 2015-01-05）事件的 cum_factor
    （＝ researchSurge5.stitch 同法），main 段 ＝ D.load_stock 還原價；收盤 ＝ 還原收盤（⛔ 不 ffill；只在有效 K 棒序列上算）
    股票 ＝ 兩版面 UG.gate3（GATE_V2 開）∩ 四碼、首碼 1～9、非 91xx 的聯集；⭐ 含已下市；pit_valid 依各自版面
 B3 「交易日」一律數有效 K 棒（該股有收盤的日子）：H1～H2 間隔、B→T、同檔 20 日去重、ATR20 都在有效 K 棒序列上數
 B4 樞紐高點：第 k 根收盤 ≥ 前 5 根與後 5 根每一根收盤（「不高於它」＝ ≤，同價可並列）；⭐ 第 k＋5 根收盤後才確認 ⇒ 要求 T ≥ H2＋5
 B5 ① 線 L(t) ＝ c[H1] ＋ (c[H2] − c[H1]) ÷ (H2 − H1) × (t − H1)（還原收盤、K 棒序數）；H2 收盤 ≤ H1 收盤；20 ≤ H2 − H1 ≤ 250；
       H1～H2 之間（不含兩端）任何收盤 ＞ L(t) ⇒ 該對作廢（⚠ 本線操作化選擇，非原文）
    ② hL ＝ max(L(t) − c[t])，t ∈ [H1, H1 ＋ ⌊(H2 − H1)/4⌋]（seq2：只量前四分之一）；hL ≥ 1 × ATR20(H2)
       ATR20 ＝ 含當根的最近 20 根真實區間平均（TR ＝ max(高−低, |高−前收|, |低−前收|)，還原價；不足 20 根 ⇒ 該對作廢）
    ③ 碰撞：H2 之後第一根滿足 L(t) − c[t] ≥ 2 × hL 的 K 棒 B0
       ⭐ 補讀法：H2 之後、B0 之前若已有收盤 ＞ L(t) ⇒ 該對作廢（線已被突破、不再是導入段趨勢線；否則一條平線可以在多年後才「碰撞」）
    ④ T ＝ B0 之後第一根收盤 ＞ L(T) 的 K 棒；B ＝ [B0, T−1] 的最低收盤（同價取最早）；T − B ≤ 120（⚠ 本線自訂候選，原文無此數字）否則作廢；
       T ≥ H2＋5（B4）；T 之後要有下一根日曆交易日（T＋1 開盤買；本次不算報酬）
 B6 同一個 T 可由多對 (H1, H2) 產生 ⇒ 合成一筆（報對數）；導入段長度等描述取「H2 最晚、再 H1 最晚」那一對
 B7 硬斷點剔除（共用規則）：H1～T（日曆位置閉區間）內有 ① 處置（兩版面 meta/disposal.csv 的 start～end 與 [H1, T] 重疊）② 停牌／價格斷點
    （data.breakpoints 在相接序列上、applies() 為真：連續缺 ≥ 5 交易日且流動性前提成立，或相鄰收盤比 ≤ 0.55／≥ 1.8 且其間無還原事件）
    ③ 減資、面額變更（adj 檔 event ∈ {reduce, parvalue}，事件日在 (H1, T]）⇒ 該對剔除（剔除後才合成 B6）
 B8 GATE_V2：T 當天 pit_valid 為真才算（板期、興櫃列剔）
 B9 同一檔 20 根 K 棒內只取第一筆：依 T 由早到晚，與上一筆「留下的」相隔 ≤ 20 根 ⇒ 不算（剔除、GATE 之後才去重）
 B10 計數單位：T 的日期（年、月）；全期 ＝ T ∈ [2005-01-03, 2026-09-23]（2004 當暖機不計；資料尾前一天）；另報探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、
     早年 2005～2014（上櫃 2007-07 起才有）
     事件層母體 ＝ 全部（四碼普通股、有 K 棒、pit_valid）；另報 T 當天落在 ① 5,000 萬母體（含 T 的 20 根成交金額平均 ≥ 5,000 萬）② R1 排名母體
     （seq321 §五：X ＝ 2016-01-04 5,000 萬母體檔數 ÷ 同日全市場檔數；之後每天 amt20 由大到小前 X%；全市場 ＝ 有 K 棒 ∧ pit_valid ∧ amt20 有值）
     「每檔每年幾次」＝ 事件數 ÷（該母體股-日數 ÷ 245）
 B11 E1／E2 是出場格，進場相同 ⇒ 兩格事件數相同（照報）
 B12 上市／上櫃 ＝ T 當天 stocks/<代號>.csv 該列的 market
 B13 原文條件不用（照標）：角度（0～45、60 度）、量能「偏高」；價格刻度（原文要算術刻度；本件距離都用 ATR 倍數或比例 ⇒ 偏離照列）
輸出 backtest/resultsBARR/freq.json、FREQ_REPORT.md、events_freq.csv.gz；大檔 ~/barrwork/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-10 23:55（台北）"
REG_SHA = "e5021a177af9277d"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
MAIN = RR.H2D
OUT = os.path.expanduser("~/tw-p17/backtest/resultsBARR")
WORK = os.path.expanduser("~/barrwork")
PIV = 5
GAP_LO, GAP_HI = 20, 250
HL_ATR = 1.0
COLL = 2.0
BT_MAX = 120
DEDUP = 20
LIQ = 5e7
R1_DAY = "2016-01-04"
SEGS = {"全期": ("2005-01-03", "2026-09-23"), "早年": ("2005-01-03", "2014-12-31"), "探索": ("2017-03-02", "2021-12-30"),
        "確認": ("2022-01-03", "2026-08-24")}
EPS = 1e-9
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


def okcode(s):
    return isinstance(s, str) and len(s) == 4 and s.isdigit() and s[0] in "123456789" and not s.startswith("91")


# ═════════════ 每檔相接序列 ═════════════
def load_part(sid, DATA, cal):
    D.DATA = DATA
    p = os.path.join(DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return None
    st = D.load_stock(sid, "twse", cal)
    if st is None:
        return None
    df = st.df
    raw = pd.read_csv(p, dtype=str, usecols=["date", "market"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"])
    mkt = raw["market"].reindex(cal).ffill().fillna("").to_numpy()
    pv = np.asarray(UG.pit_valid(sid, cal, DATA), bool)
    adj = D.load_adj(sid)
    return {"o": df["open"].to_numpy(float), "h": df["high"].to_numpy(float), "l": df["low"].to_numpy(float), "c": df["close"].to_numpy(float),
            "v": df["volume"].to_numpy(float), "amt": df["amount"].to_numpy(float), "mkt": mkt, "pv": pv, "adj": adj, "ev": st.event_dates}


def disposal_iv(DATA):
    p = os.path.join(DATA, "meta", "disposal.csv")
    d = pd.read_csv(p, dtype=str)
    out = {}
    for s, a, b in zip(d["stock_id"], d["start_date"], d["end_date"]):
        if isinstance(a, str) and a:
            out.setdefault(s, []).append((pd.Timestamp(a), pd.Timestamp(b) if isinstance(b, str) and b else pd.Timestamp(a)))
    return out


def stock_series(sid):
    calE, calM = _G["calE"], _G["calM"]; cal = _G["cal"]; nE = len(calE)
    E = load_part(sid, EOTC, calE); M = load_part(sid, MAIN, calM)
    if E is None and M is None:
        return None
    mult = 1.0
    if M is not None and M["adj"] is not None and len(M["adj"]):
        a = M["adj"][M["adj"]["date"] >= pd.Timestamp("2015-01-05")]
        if len(a):
            mult = float(a["cum_factor"].iloc[0])
    n = len(cal)
    X = {k: np.full(n, np.nan) for k in ("o", "h", "l", "c", "v", "amt")}
    X["mkt"] = np.full(n, "", dtype=object); X["pv"] = np.zeros(n, bool)
    for part, P, sl in (("E", E, slice(0, nE)), ("M", M, slice(nE, n))):
        if P is None:
            continue
        f = mult if part == "E" else 1.0
        for k in ("o", "h", "l", "c"):
            X[k][sl] = P[k] * f
        X["v"][sl] = P["v"]; X["amt"][sl] = P["amt"]; X["mkt"][sl] = P["mkt"]; X["pv"][sl] = P["pv"]
    # 硬斷點（B7）
    hb = np.zeros(n, bool)                     # 斷點／減資／面額變更：事件位置 k ⇒ 對 (H1, T] 含 k 的剔
    ev = set()
    for P in (E, M):
        if P is not None:
            ev |= set(P["ev"])
    df = pd.DataFrame({"close": X["c"], "volume": X["v"]}, index=cal)
    nbp = 0
    for b in D.breakpoints(df, ev):
        if D.applies(b):
            hb[b["pos"]] = True; nbp += 1
    nrd = 0
    for P in (E, M):
        if P is None or P["adj"] is None or not len(P["adj"]):
            continue
        a = P["adj"]
        for d, e in zip(a["date"], a["event"].astype(str)):
            if e in ("reduce", "parvalue"):
                k = int(cal.searchsorted(d))
                if k < n:
                    hb[k] = True; nrd += 1
    disp = np.zeros(n, bool)
    for a, b in _G["DISP"].get(sid, []):
        i, j = int(cal.searchsorted(a)), int(cal.searchsorted(b, side="right")) - 1
        if j >= i:
            disp[max(i, 0):min(j, n - 1) + 1] = True
    X.update(hb=hb, disp=disp, nbp=nbp, nrd=nrd)
    return X


# ═════════════ BARR 偵測 ═════════════
def detect(c, h, l, coll=COLL, hl_atr=HL_ATR, piv=PIV):
    """c、h、l：有效 K 棒序列（還原）。⇒ 每對 (H1, H2, B0, B, T, hL, atr) 的 list（尚未剔斷點）。"""
    m = len(c)
    if m < GAP_LO + 2 * piv + 2:
        return [], 0
    hh = np.where(np.isfinite(h), h, c); ll = np.where(np.isfinite(l), l, c)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([hh - ll, np.abs(hh - pc), np.abs(ll - pc)]), axis=0)
    tr[0] = hh[0] - ll[0]
    atr = pd.Series(tr).rolling(20, min_periods=20).mean().to_numpy()
    # 樞紐
    from numpy.lib.stride_tricks import sliding_window_view as swv
    W = swv(c, 2 * piv + 1)                                   # 中心 k ＝ i＋piv
    mx = W.max(axis=1)
    piv_k = np.flatnonzero(W[:, piv] >= mx) + piv
    out = []; npair = 0
    for jj, j in enumerate(piv_k):
        lo = j - GAP_HI; hi = j - GAP_LO
        cand = piv_k[(piv_k >= lo) & (piv_k <= hi)]
        if not len(cand) or not np.isfinite(atr[j]):
            continue
        for i in cand:
            if c[j] > c[i]:
                continue
            npair += 1
            slope = (c[j] - c[i]) / (j - i)
            t = np.arange(i + 1, j)
            Lt = c[i] + slope * (t - i)
            if (c[i + 1:j] > Lt + EPS * np.abs(Lt)).any():
                continue
            q = i + (j - i) // 4
            tq = np.arange(i, q + 1)
            hL = float(np.max(c[i] + slope * (tq - i) - c[i:q + 1]))
            if not (hL >= hl_atr * atr[j] - EPS) or hL <= 0:
                continue
            # 前掃：第一根「收盤 ＞ 線」與第一根「碰撞」
            start = j + 1; blk = 64; first_up = None; first_coll = None
            while start < m:
                end = min(m, start + blk)
                tt = np.arange(start, end); Lx = c[i] + slope * (tt - i); cx = c[start:end]
                up = np.flatnonzero(cx > Lx + EPS * np.abs(Lx))
                if first_coll is None:
                    co = np.flatnonzero(Lx - cx >= coll * hL - EPS)
                    if len(co):
                        first_coll = start + int(co[0])
                fu = start + int(up[0]) if len(up) else None
                if fu is not None and (first_coll is None or fu < first_coll):
                    break                                       # 碰撞前已突破 ⇒ 作廢（B5 ③）
                if fu is not None and first_coll is not None and fu > first_coll:
                    first_up = fu; break
                start = end; blk *= 2
            if first_coll is None or first_up is None:
                continue
            T = first_up; B0 = first_coll
            B = B0 + int(np.argmin(c[B0:T]))
            if T - B > BT_MAX or T < j + piv:
                continue
            out.append((int(i), int(j), int(B0), int(B), int(T), hL, float(atr[j]), float((c[i] + slope * (B - i) - c[B]) / hL)))
    return out, npair


def stock_job(args):
    s_i, sid = args
    X = stock_series(sid)
    if X is None:
        return sid, None
    cal = _G["cal"]; n = len(cal)
    bar = np.isfinite(X["c"])
    idx = np.flatnonzero(bar)
    a20 = np.full(n, np.nan)
    if len(idx) >= 20:
        a20[idx] = pd.Series(X["amt"][idx]).rolling(20, min_periods=20).mean().to_numpy()
    res = {"a20": a20.astype(np.float32), "mkt_ok": (bar & X["pv"]), "twse": np.array([m == "twse" for m in X["mkt"]]) & bar,
           "nbp": X["nbp"], "nrd": X["nrd"], "nbar": int(bar.sum())}
    pairs, npair = detect(X["c"][idx], X["h"][idx], X["l"][idx])
    res["npair"] = npair; res["ncand"] = len(pairs)
    hbc = np.cumsum(X["hb"]); dc = np.cumsum(X["disp"])
    rows = []
    for i, j, B0, B, T, hL, atr, depth in pairs:
        H1p, H2p, Bp, Tp = int(idx[i]), int(idx[j]), int(idx[B]), int(idx[T])
        if Tp + 1 >= n:
            continue
        hard = (hbc[Tp] - hbc[H1p]) > 0
        disp = (dc[Tp] - (dc[H1p - 1] if H1p > 0 else 0)) > 0
        rows.append((T, i, j, B0, B, H1p, H2p, Bp, Tp, hL, atr, depth, bool(hard), bool(disp), bool(X["pv"][Tp])))
    res["rows"] = rows
    res["mkt_T"] = {r[8]: X["mkt"][r[8]] for r in rows}
    return sid, res


# ═════════════ 主流程 ═════════════
def freq(a):
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run_freq.log"))
    log(f"===== researchBARR freq {now_tpe()}（台北）｜讀法寫死 {TIME}｜smoke {a.smoke} =====")
    regf = reg_check(); log(f"[sha] {REG_SHA} ✔ {regf}")
    D.DATA = EOTC; calE = D.load_calendar(); D.DATA = MAIN; calM = D.load_calendar()
    assert calE[-1] < calM[0]
    cal = calE.append(calM); n = len(cal)
    sids = set()
    for DATA in (EOTC, MAIN):
        D.DATA = DATA
        st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
        g = UG.gate3(st)
        sids |= {s for s in g["stock_id"] if okcode(s)}
    sids = sorted(sids)
    if a.smoke:
        sids = sids[::15]
    DISP = {}
    for DATA in (EOTC, MAIN):
        for k, v in disposal_iv(DATA).items():
            DISP.setdefault(k, []).extend(v)
    _G.update(calE=calE, calM=calM, cal=cal, DISP=DISP)
    log(f"[版面] 日曆 {cal[0].date()}～{cal[-1].date()}（{n}）；早年 {len(calE)}、main {len(calM)}；股票 {len(sids)}")
    t0 = time.time(); RES = {}
    with Pool(a.procs) as pool:
        for k, (sid, r) in enumerate(pool.imap_unordered(stock_job, list(enumerate(sids)), chunksize=4)):
            if r is not None:
                RES[sid] = r
            if k % 200 == 0:
                log(f"[偵測] {k}/{len(sids)}｜{time.time() - t0:.0f}s")
    sids = sorted(RES); S = len(sids)
    log(f"[偵測] 完 {S} 檔｜{time.time() - t0:.0f}s")
    A20 = np.vstack([RES[s]["a20"] for s in sids]); MK = np.vstack([RES[s]["mkt_ok"] for s in sids]) & np.isfinite(A20)
    TW = np.vstack([RES[s]["twse"] for s in sids])
    # R1
    d16 = int(cal.searchsorted(pd.Timestamp(R1_DAY)))
    assert str(cal[d16].date()) == R1_DAY
    nu = int((MK[:, d16] & (A20[:, d16] >= LIQ)).sum()); nm = int(MK[:, d16].sum()); X1 = nu / nm
    log(f"[R1] X ＝ {nu}／{nm} ＝ {X1:.4f}")
    U5 = MK & (np.nan_to_num(A20, nan=0.0) >= LIQ)
    R1 = np.zeros_like(MK)
    for d in range(n):
        ix = np.flatnonzero(MK[:, d])
        if not len(ix):
            continue
        k = int(np.ceil(X1 * len(ix)))
        R1[ix[np.argsort(-A20[ix, d], kind="stable")[:k]], d] = True
    # 事件表
    allrows = []
    for si, s in enumerate(sids):
        for (T, i, j, B0, B, H1p, H2p, Bp, Tp, hL, atr, depth, hard, disp, pv) in RES[s]["rows"]:
            allrows.append({"sid": s, "si": si, "Tk": T, "H1k": i, "H2k": j, "B0k": B0, "Bk": B, "H1": H1p, "H2": H2p, "B": Bp, "T": Tp, "hL": hL, "atr": atr,
                            "depth": depth, "hard": hard, "disp": disp, "pv": pv, "mkt": RES[s]["mkt_T"][Tp]})
    P = pd.DataFrame(allrows)
    cnt = {"候選對（通過①～④）": int(len(P))}
    P["剔"] = P["hard"] | P["disp"]
    cnt["剔：硬斷點（停牌／斷點／減資／面額）"] = int(P["hard"].sum()); cnt["剔：處置"] = int(P["disp"].sum())
    Q = P[~P["剔"]]
    G = Q.sort_values(["sid", "T", "H2", "H1"]).groupby(["sid", "T"], sort=False)
    E = G.tail(1).copy()
    E["對數"] = G.size().reindex(pd.MultiIndex.from_frame(E[["sid", "T"]])).to_numpy()
    cnt["合成後（同一 T）"] = int(len(E))
    E = E[E["pv"]]
    cnt["GATE_V2 後"] = int(len(E))
    keep = []
    for s, g in E.sort_values(["sid", "Tk"]).groupby("sid", sort=False):
        last = -10 ** 9
        for ix_, tk in zip(g.index, g["Tk"]):
            if tk - last > DEDUP:
                keep.append(ix_); last = tk
    E = E.loc[keep].sort_values(["T", "sid"]).reset_index(drop=True)
    cnt["同檔 20 根去重後"] = int(len(E))
    E["日期"] = [str(cal[t].date()) for t in E["T"]]
    E["H1日"] = [str(cal[t].date()) for t in E["H1"]]; E["H2日"] = [str(cal[t].date()) for t in E["H2"]]; E["B日"] = [str(cal[t].date()) for t in E["B"]]
    E["導入段K棒"] = E["H2k"] - E["H1k"]; E["B到T"] = E["Tk"] - E["Bk"]; E["hL÷ATR"] = E["hL"] / E["atr"]
    E["5000萬"] = U5[E["si"].to_numpy(), E["T"].to_numpy()]; E["R1"] = R1[E["si"].to_numpy(), E["T"].to_numpy()]
    E["年"] = E["日期"].str[:4]
    E.drop(columns=["si"]).to_csv(os.path.join(OUT, "events_freq.csv.gz"), index=False, float_format="%.6g")
    # 統計
    OUTJ = {"件": "PREREG碰撞回落底部（BARR 底）seq2 —— 頻率（⛔ 無報酬）", "登錄": regf, "sha": REG_SHA, "讀法寫死": TIME, "產出": now_tpe() + "（台北）",
            "smoke": bool(a.smoke), "版面": {"早年": [str(calE[0].date()), str(calE[-1].date())], "main": [str(calM[0].date()), str(calM[-1].date())], "股票": S},
            "篩選流程": cnt, "R1": {"X": X1, "2016-01-04 5,000萬母體": nu, "同日全市場": nm},
            "硬斷點": {"價格／停牌斷點（applies）": int(sum(RES[s]["nbp"] for s in sids)), "減資／面額事件": int(sum(RES[s]["nrd"] for s in sids))},
            "樞紐對（H2≤H1、間隔 20～250）": int(sum(RES[s]["npair"] for s in sids))}
    seg = {}
    for k, (x, y) in SEGS.items():
        a_, b_ = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1
        e = E[(E["T"] >= a_) & (E["T"] <= b_)]
        months = len(set(str(d)[:7] for d in cal[a_:b_ + 1]))
        sd_all = float(MK[:, a_:b_ + 1].sum()); sd5 = float(U5[:, a_:b_ + 1].sum()); sdr = float(R1[:, a_:b_ + 1].sum())
        tw = TW[:, a_:b_ + 1] & MK[:, a_:b_ + 1]
        seg[k] = {"起訖": [str(cal[a_].date()), str(cal[b_].date())], "月數": months, "事件": int(len(e)), "每月平均": len(e) / months,
                  "上市": int((e["mkt"] == "twse").sum()), "上櫃": int((e["mkt"] == "tpex").sum()),
                  "5000萬母體內": int(e["5000萬"].sum()), "R1母體內": int(e["R1"].sum()),
                  "每檔每年（全市場）": len(e) / (sd_all / 245) if sd_all else np.nan,
                  "每檔每年（上市）": int((e["mkt"] == "twse").sum()) / (float(tw.sum()) / 245) if tw.sum() else np.nan,
                  "每檔每年（上櫃）": int((e["mkt"] == "tpex").sum()) / (float((MK[:, a_:b_ + 1] & ~TW[:, a_:b_ + 1]).sum()) / 245) if (MK[:, a_:b_ + 1] & ~TW[:, a_:b_ + 1]).sum() else np.nan,
                  "每檔每年（5000萬母體）": int(e["5000萬"].sum()) / (sd5 / 245) if sd5 else np.nan,
                  "每檔每年（R1母體）": int(e["R1"].sum()) / (sdr / 245) if sdr else np.nan,
                  "R1母體每月平均": int(e["R1"].sum()) / months, "R1母體平均每天檔數": sdr / (b_ - a_ + 1),
                  "E1格事件": int(len(e)), "E2格事件": int(len(e))}
    OUTJ["各段"] = seg
    a_, b_ = int(cal.searchsorted(pd.Timestamp(SEGS["全期"][0]))), int(cal.searchsorted(pd.Timestamp(SEGS["全期"][1]), side="right")) - 1
    EF = E[(E["T"] >= a_) & (E["T"] <= b_)]
    yrs = []
    for y in range(2005, 2027):
        ya, yb = int(cal.searchsorted(pd.Timestamp(y, 1, 1))), min(int(cal.searchsorted(pd.Timestamp(y + 1, 1, 1))) - 1, b_)
        e = EF[EF["年"] == str(y)]
        sd = float(MK[:, ya:yb + 1].sum())
        yrs.append({"年": y, "事件": int(len(e)), "上市": int((e["mkt"] == "twse").sum()), "上櫃": int((e["mkt"] == "tpex").sum()),
                    "5000萬": int(e["5000萬"].sum()), "R1": int(e["R1"].sum()), "全市場平均每天檔數": sd / (yb - ya + 1),
                    "每檔每年（全市場）": len(e) / (sd / 245) if sd else np.nan})
    OUTJ["各年"] = yrs
    q = lambda x: {"n": int(len(x)), "平均": float(np.mean(x)), "p10": float(np.percentile(x, 10)), "p25": float(np.percentile(x, 25)),
                   "中位": float(np.median(x)), "p75": float(np.percentile(x, 75)), "p90": float(np.percentile(x, 90))} if len(x) else {"n": 0}
    bins = [20, 25, 40, 60, 100, 150, 200, 251]
    hist = pd.cut(EF["導入段K棒"], bins=bins, right=False).value_counts().sort_index()
    OUTJ["導入段長度（K 棒＝交易日）"] = {"全期": q(EF["導入段K棒"].to_numpy()), "R1母體": q(EF.loc[EF["R1"], "導入段K棒"].to_numpy()),
                                  "分組": {str(k): int(v) for k, v in hist.items()},
                                  "≤ 24 根（原文平均 35 天≈24 交易日）比例": float((EF["導入段K棒"] <= 24).mean()) if len(EF) else np.nan,
                                  "原文對照": "原文導入段平均 35 天（約 24 個交易日）；本件候選範圍 20～250 不改"}
    OUTJ["描述"] = {"B→T（K 棒）": q(EF["B到T"].to_numpy()), "hL÷ATR20": q(EF["hL÷ATR"].to_numpy()), "碰撞深度÷hL（B 日）": q(EF["depth"].to_numpy()),
                  "每個 T 的 (H1,H2) 對數": q(EF["對數"].to_numpy())}
    json.dump(OUTJ, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(OUTJ)
    log(f"[完] {json.dumps(cnt, ensure_ascii=False)}｜全期 {seg['全期']['事件']}")


def report(J):
    s = J["各段"]
    L = []
    L.append(f"# 碰撞回落底部（BARR 底）seq2：出現頻率（⛔ 未算任何報酬）\n")
    L.append(f"登錄 sha {J['sha']}｜讀法寫死 {J['讀法寫死']}｜產出 {J['產出']}｜回測線計算子代理｜程式 backtest/researchBARR.py freq\n")
    f = s["全期"]
    L.append("## 結論\n")
    L.append(f"- 全期（T 在 {f['起訖'][0]}～{f['起訖'][1]}）共 **{f['事件']} 筆**，每月平均 {f['每月平均']:.1f} 筆；上市 {f['上市']}、上櫃 {f['上櫃']}。")
    L.append(f"- 每檔每年 {f['每檔每年（全市場）']:.3f} 次（全市場四碼普通股）；R1 母體內 {f['R1母體內']} 筆、每檔每年 {f['每檔每年（R1母體）']:.3f} 次、每月 {f['R1母體每月平均']:.1f} 筆。")
    L.append(f"- 先驗 ①「每檔每年 ＜ 0.3 次」：全市場 {'成立' if f['每檔每年（全市場）'] < 0.3 else '不成立'}（只記錄，⛔ 不判）。")
    L.append(f"- E1／E2 是出場格、進場相同 ⇒ 兩格事件數相同（全期各 {f['E1格事件']} 筆）。")
    L.append("- ⛔ 本次不算報酬；報酬照裁定 seq326 排在 seq322 五件之後另派。\n")
    L.append("## 各段\n")
    L.append("| 段 | 起訖 | 事件 | 每月 | 上市 | 上櫃 | 5,000 萬母體內 | R1 母體內 | 每檔每年（全市場） | 每檔每年（R1） |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k, v in s.items():
        L.append(f"| {k} | {v['起訖'][0]}～{v['起訖'][1]} | {v['事件']} | {v['每月平均']:.1f} | {v['上市']} | {v['上櫃']} | {v['5000萬母體內']} | {v['R1母體內']} | {v['每檔每年（全市場）']:.3f} | {v['每檔每年（R1母體）']:.3f} |")
    L.append("\n## 各年（依 T 的日期）\n")
    L.append("| 年 | 事件 | 上市 | 上櫃 | 5,000 萬 | R1 | 全市場平均每天檔數 | 每檔每年 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for y in J["各年"]:
        L.append(f"| {y['年']} | {y['事件']} | {y['上市']} | {y['上櫃']} | {y['5000萬']} | {y['R1']} | {y['全市場平均每天檔數']:.0f} | {y['每檔每年（全市場）']:.3f} |")
    d = J["導入段長度（K 棒＝交易日）"]
    L.append("\n## 導入段長度（H1→H2，交易日）\n")
    g = d["全期"]
    if g["n"]:
        L.append(f"- 全期 {g['n']} 筆：平均 {g['平均']:.1f}、中位 {g['中位']:.0f}、p10～p90 {g['p10']:.0f}～{g['p90']:.0f}；≤ 24 根占 {d['≤ 24 根（原文平均 35 天≈24 交易日）比例']:.1%}。")
    L.append(f"- {d['原文對照']}。")
    L.append("- 分組：" + "、".join(f"{k} {v}" for k, v in d["分組"].items()))
    L.append("\n## 篩選流程\n")
    for k, v in J["篩選流程"].items():
        L.append(f"- {k}：{v}")
    L.append(f"- R1：X ＝ {J['R1']['2016-01-04 5,000萬母體']}／{J['R1']['同日全市場']} ＝ {J['R1']['X']:.4f}")
    L.append("\n## 描述（不判）\n")
    for k, v in J["描述"].items():
        if v.get("n"):
            L.append(f"- {k}：平均 {v['平均']:.2f}、中位 {v['中位']:.2f}、p10～p90 {v['p10']:.2f}～{v['p90']:.2f}")
    L.append("\n## 照標（登錄 §一、裁定 seq326 §一）\n")
    L.append("- hL 只量導入段前四分之一（seq2 改正）。")
    L.append("- B→T ≤ 120 日：⚠ 本線自訂候選、原文無此數字。")
    L.append("- H1～H2 全程沒有收盤在線上：本線操作化選擇、非原文。")
    L.append("- 角度（導入段 0～45 度、碰撞段 60 度以上）、量能「偏高」：不能機器化，照標不用。")
    L.append("- 原文要算術刻度；本件距離一律換成 ATR 倍數或比例（偏離）。")
    L.append("- 執行者補讀法（B5 ③）：H2 之後、碰撞成立前若已有收盤站上線 ⇒ 該線作廢；「交易日」一律數有效 K 棒；細節見程式檔頭 B1～B13。")
    L.append("- 早年上櫃日 K 2007-07 起才有 ⇒ 2005～2007-06 只有上市。")
    open(os.path.join(OUT, "FREQ_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["freq"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        global OUT
        OUT = os.path.join(WORK, "smoke")
    freq(a)


if __name__ == "__main__":
    main()
