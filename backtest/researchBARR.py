# -*- coding: utf-8 -*-
"""PREREG碰撞回落底部（BARR 底）seq2（台股策略線登錄 sha e5021a177af9277d，2026-10-10 23:38；裁定 seq324 §三發號、seq326 §一三處改正）——回測線計算子代理。
⛔ freq 模式：出現頻率與各年筆數；⛔ 不算任何報酬（裁定 seq324 §三、seq326 §一：報酬排在 seq322 五件之後，另派）。
⭐ run 模式（報酬；裁定 seq332 照 seq2 跑）另加在本檔後段：讀法 R1～R14 見 RUN_DOC（寫死時間 RUN_TIME，台北）；freq 的程式與輸出不變。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBARR freq [--procs 2] [--smoke]
    ...                                                                     -m backtest.researchBARR run [--procs 4] [--reps 200] [--fake 200] [--smoke] [--reuse]
    ...                                                                     -m backtest.researchBARR check [--procs 4]     # 獨立寫法抽樣 ⇒ check.json
    ...                                                                     -m backtest.researchBARR page                  # ⇒ resultsBARR/碰撞回落底部BARR底.html

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
def detect(c, h, l, coll=COLL, hl_atr=HL_ATR, piv=PIV, hl_pct=None):
    """c、h、l：有效 K 棒序列（還原）。⇒ 每對 (H1, H2, B0, B, T, hL, atr) 的 list（尚未剔斷點）。
    hl_pct（run 模式描述臂「hL 用 1% 股價」才給）：門檻改 hL ≥ hl_pct × c[H2]；None ⇒ 原式 hL ≥ hl_atr × ATR20（freq 不變）。"""
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
            thr = hl_atr * atr[j] if hl_pct is None else hl_pct * c[j]
            if not (hL >= thr - EPS) or hL <= 0:
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


# ═══════════════════════════════════════ run 模式（報酬）═══════════════════════════════════════
# 讀法 R 標寫在檔頭 RUN_DOC（寫死時間 RUN_TIME，台北；寫死前 ⛔ 沒算任何本件報酬）
RUN_TIME = "2026-10-11 01:35（台北）"
RUN_DOC = """
⭐ run 模式讀法寫死時間：RUN_TIME（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何本件報酬（只看過登錄 seq2、裁定 seq324／326／332、台股 1011-0049、
   本件 freq 輸出（頻率，無報酬）、既有程式 research11.load_bars、researchRevLimitUp（組合層骨架）、researchPatAll／researchM（事件層骨架））。
 R1 事件：與 freq 同一支偵測（detect、B1～B13 原樣）；⭐ 唯一不同 ＝ 硬斷點（B7②）改用正式引擎 research11.load_bars 的壞根規則：
    逐版面（早年、main 各自）照抄 load_bars：① 幽靈事件（還原事件日原始收盤 ÷（前一根原始收盤 × factor）＜ 0.895 或 ＞ 1.105）② 有效 K 棒間缺口 ≥ 5 個交易日
    （⭐ 不帶流動性前提）③ data.breakpoints 且 applies()；另在相接序列上補算缺口 ≥ 5（含早年→main 交界）；
    再聯集 freq 原有的「相接序列 applies 斷點」與「adj 減資／面額事件」（B7③）與處置（B7①）⇒ H1～T 內有任一 ⇒ 剔（先剔後合成、再 GATE、再 20 根去重，同 freq）
    ⇒ 事件數會比 freq 少；另用 freq 原規則重跑一次，必須逐筆等於 events_freq.csv.gz（閘，不等就停）
 R2 事件層 H20（登錄 §二）：R_e ＝ 還原 close(第 k_T＋20 根有效 K 棒) ÷ 還原 open(第 k_T＋1 根) − 1（k_T ＝ T 的有效 K 棒序號；= research11.fixed_exit 同式，
    H 數有效 K 棒、進場那根算第 1 根）；要求第 k_T＋1 根 ＝ 日曆 T＋1（T＋1 停牌 ⇒ 買不到 ⇒ 不算，筆數照報）、開盤 ＞ 0、
    (k_T, k_T＋20] 內無壞根（R1 的同一組壞根；⇒ 不算，筆數照報）。成本兩邊相同 ⇒ 不扣（門檻 0.585% 用在判定）
    口徑 B（同日母體平均）：EW_20(T) ＝ T 當天「四碼普通股 ∧ 有 K 棒 ∧ pit_valid（GATE_V2）∧ 同式 R 可算（同上三條）」全部股票 R 的等權平均（含事件股本身、含日後下市）
    X_e ＝ R_e − EW_20(T)；窗 ＝ T ∈ [2005-01-03, 資料尾]（R 可算即算；早年上櫃 2007-07 起）；事件層母體 ＝ freq B10 的「全部」（不限 R1）
    主 CI：research11.cl_stats（T 所在曆月分群 CR0、1.96）；n_eff ＝ min(事件數, 有事件的月數)
    判（登錄 §二）：平均 ＞ 0.585% 且 CI 下界 ＞ 0 ⇒「測得出」；CI 不含 0 但平均 ≤ 0.585% ⇒「統計層測得出、扣成本不夠」；CI 全在 0 下 ⇒「反向」；
    CI 含 0 ⇒ 照「零」四條件（CI 含 0、|平均| ≤ 0.585%、n_eff ≥ 24、假訊號組 CI 半寬（30 次中位）≤ 0.585%）全過 ⇒「零」，否則「測不出」；n_eff ＜ 24 ⇒「還沒測」
 R3 事件層假訊號臂（登錄 §二、同型態全量 researchPatAll C8 新預設）：r ＝ 0…29；每檔 n ＝ 該檔 R2 有效真事件數；可抽日 ＝ 該檔有效 K 棒、pit_valid、
    T ≥ 2005-01-03、同式 R 可算（R2 三條）、且不存在真事件 T_r 落在 [T − 20 根, T]；不放回抽 n 天（不足 ⇒ 全取）；X ＝ R − EW_20(T)、同分群同判式；
    種子 default_rng([20261011, r])、依代號排序逐檔抽。x／30 ＝ 落「測得出」的次數；x ≥ 15 ⇒「這一格的過關不構成證據」
 R4 事件層描述（⛔ 不判、不計 N）：H60（同式、(k_T, k_T＋60] 無壞根；⚠ 月分群在 60 日持有偏窄）、只取上市（T 當天 market）、各段（早年／探索／確認）、
    變體 hL 用 1% 股價（hL ≥ 1% × c[H2]）、碰撞 1.5／2.5 倍、樞紐 3／10 根（各自重跑偵測與 R1 剔除、同 R2 式）
 R5 組合層母體 ＝ T 當天 R1 排名母體（freq B10 同一個 R1 矩陣：X ＝ 307／1528）的事件（先在全部事件上 20 根去重、再取 R1；⇒ 登錄「同檔 20 日只取第一筆」在定義層）
    版面 ＝ researchRevLimitUp.World（main ＝ rerun17 快照 H2D、早年 ＝ eotc；同一份快取 ~/rluwork/world_*.pkl；⛔ 不改）；進場 e ＝ 日曆 T＋1 開盤（無有效開盤 ⇒ 不進）
 R6 出場（seq308 §四；⛔ 不設最長天數）：在相接有效 K 棒序列上判，換成日曆位置再交給引擎
    E1：第 k_T＋1 根（含進場那根收盤）起，第一根「收盤 ＜ 趨勢線延伸值 L(k)」（L ＝ 該事件留下那一對 (H1, H2) 的線，K 棒序數延伸）⇒ 下一個有效開盤賣
    E2：第 k_T＋1 根起持有期最高收盤 × 0.8 ≥ 當根收盤 ⇒ 下一個有效開盤賣（= researchRevLimitUp E2 同式）
    ⭐ 補讀法（硬斷點落在持有期）：(k_T＋1, 賣出根] 內有壞根 kb（R1 同一組）⇒ 改在第 kb−1 根收盤強制出（原因「壞根前收盤強制出」，筆數照報）；
       沒觸發出場、之後有壞根 ⇒ 同樣強制出；都沒有 ⇒ 未完（以最後收盤計值）
    早年版面：出場位置落在 2015 之後 ⇒ 早年版面內視為未完（只影響窗外）
 R7 引擎 research11.simulate_mtm（rule "F"，經 researchRevLimitUp.sim／run_arms，⛔ 不改）：10 槽、等權（前一日權益 ÷ 10）、候選多於空位 ⇒ 抽籤
    （default_rng(20261010＋r)）、200 顆報中位、成本 0.585%／來回、停止交易強制出場（stop_force）開、GATE_V2 開、含下市
    現實版 ＝ researchSlip「現實版」（researchRevLimitUp M8 同一套：每邊 ＋0.3%、衝擊 σ20 × √(5 萬 ÷ ADV20)、一字漲停買不到、停牌買不到、一字跌停賣不掉、均價成交）
 R8 段：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、主窗 ＝ 兩段相接（同一條權益曲線切窗；rerun17 win_metrics）；早年 2005-01-03～2014-12-30（早年版面、只用價量）
    判準（使用者判準、對 0050 同段）：合格 ＝ 年化中位 ＞ 0050 且 年化中位 ÷ |回落中位| ≥ 0050 的；另列 ＝ 只過年化；其餘不合格
    挑格：探索段、非退化格中合格者取比值最大；沒有合格 ⇒ 取比值最大（照報不合格）；平手 ⇒ 年化、格序 E1、E2
    判定 ＝ 確認段與早年段兩段取較嚴（登錄 §三「兩段取較嚴」）；⭐ 沒人看過台股報酬 ⇒ 不是事後重切 ⇒ 最高可「合格」；現實版同表並報標籤
 R9 退化（登錄 §三必報）：⭐ 先寫 degeneracy.json（附台北時戳）再彙總任何報酬；平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）⇒ 照登錄排除並列出
 R10 組合層假訊號臂（挑中格）：= researchRevLimitUp.fake_rows（每個進場日訊號數不變 ⇒ e−1 的 R1 母體隨機同數量股、持有天數從挑中格已完成筆等機率抽）；200 抽；
    p ＝ 假訊號年化 ≥ 挑中格年化中位 的比例
 R11 描述（挑中格同進場、各 50 顆）：固定持有 {20, 60, 120} 根；0050 在 200 日線上才買（e−1 的 0050 收盤 ＞ 200 日均）——「擋長空頭、不是急跌保護」
 R12 必報：等效獨立檔數（r＝0、每個換股日持股 N、ρ ＝ 前 60 日日報酬兩兩相關平均、N_eff ＝ N ÷ (1＋(N−1)ρ)，researchRevLimitUp.eff_n）；現金比例；持有天數分佈；
    各出場原因次數；窗尾仍持有；一年內先跌 15%（researchRevLimitUp.trade_stats）；
    吃到「起漲→頂」幾成 ＝（賣價 − 起漲點收盤）÷（真頂收盤 − 起漲點收盤）；起漲點 ＝ 碰撞底 B；真頂 ＝ 從 B 起最高收盤、到進場後第一次從 [B, 當根] 最高回落 30% 為止
    （researchF4Launch L15 同式；真頂沒收斂、未完、強制出的筆不算）；另報買價基準（真頂 ≥ 進場價 × 1.05 的筆）
 R13 對照：營量 v1、營飆 v1（resultsYLmargin cells.csv 同窗段數字；持股重疊 researchRevLimitUp.yl_ref r0）、0050 同段
 R14 結果句必附（seq332）：「本件導入段平均比原文長（47.5 交易日）」「頻率每檔每年 0.72 次」；引用原文一律寫「原文平均 35 個日曆天」
輸出 backtest/resultsBARR/：degeneracy.json（先寫）、summary.json、grid.csv、seeds.csv.gz、events_run.csv.gz、run.log、check.json、碰撞回落底部BARR底.html；大檔 ~/barrwork/
── 事後註（寫死之後、照實記；判定讀法沒改）──
 ① 01:38～01:40 跑過 1/15 子樣本冒煙測試（輸出 ~/barrwork/smoke_run，數字不是本件結果）：只修了程式錯（浮點索引），讀法未改
 ② 第一次全量 run 在 R1 的閘停下：比對時對方檔含 2004 暖機年事件、我方只取全期 ⇒ 把對方也限在全期（SEGS 全期）後逐筆相同；偵測快取沿用（--reuse）
 ③ R9「退化 ⇒ 排除、不判合格」在確認段／早年段也適用：程式在寫死前就這樣寫（VERD），本次四格都沒退化，未觸發
"""
H_EV, H_D = 20, 60
COST_RT = 0.00585
E2_DD, TOP_DD = 0.20, 0.30
VARS = {"主": {}, "hL1%股價": {"hl_pct": 0.01}, "碰撞1.5倍": {"coll": 1.5}, "碰撞2.5倍": {"coll": 2.5}, "樞紐3根": {"piv": 3}, "樞紐10根": {"piv": 10}}
EV_FROM = "2005-01-03"
FK_REPS, FK_SEED, FK_EXCL = 30, 20261011, 20
PSEGS = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "主窗": ("2017-03-02", "2026-08-24")}
PEARLY = ("2005-01-03", "2014-12-30")
CELLS = ["E1", "E2"]
CN = {"E1": "E1（收盤跌回趨勢線下就賣）", "E2": "E2（從持有期最高收盤回落 20% 就賣）"}
PAGE_NAME = "碰撞回落底部BARR底.html"
ANCHOR = (0.24020209886370614, -0.3395700527611012)


def bad_part(sid, DATA, cal):
    """R1：research11.load_bars 的壞根（逐字照抄：幽靈事件 ∪ 有效 K 棒缺口 ≥ 5 ∪ applies 斷點）⇒ 日曆長布林（壞根所在日 True）。
    與 load_bars 唯一差別：不足 260 根也照算（load_bars 回 None）。"""
    D.DATA = DATA
    out = np.zeros(len(cal), bool)
    if not os.path.exists(os.path.join(DATA, "stocks", f"{sid}.csv")):
        return out
    st = D.load_stock(sid, "twse", cal)
    if st is None:
        return out
    df = st.df
    idx = np.flatnonzero(df["traded"].to_numpy())
    n = len(idx)
    if n == 0:
        return out
    raw = pd.read_csv(os.path.join(DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")["close"]
    rc = pd.to_numeric(raw.reindex(cal), errors="coerce").to_numpy(float)[idx]
    dates = cal[idx]
    adj = D.load_adj(sid)
    phantom = np.zeros(n, bool)
    if adj is not None and len(adj):
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dates, d))
            if k >= n:
                continue
            if k > 0 and not np.isnan(rc[k]) and not np.isnan(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    phantom[k] = True
    bad = phantom.copy()
    bad[1:] |= (np.diff(idx) - 1) >= 5
    for b in D.breakpoints(df, st.event_dates):
        if D.applies(b):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < n:
                bad[k] = True
    out[idx[bad]] = True
    return out


def barr_exits(c, o, idx, badk, i, j, T, B):
    """R6、R12：相接有效 K 棒序列上的 E1／E2 出場（日曆位置）、壞根強制出、起漲點與真頂。"""
    m = len(c); ke = T + 1
    out = {"oE": np.nan, "cB": float(c[B]), "top": np.nan, "top_closed": False}
    for cell in CELLS:
        out[f"{cell}_xk"], out[f"{cell}_x"], out[f"{cell}_why"] = "open", -1, "未完"
    if ke >= m:
        return out
    out["oE"] = float(o[ke])
    slope = (c[j] - c[i]) / (j - i)
    kk = np.arange(ke, m); L = c[i] + slope * (kk - i); cc = c[ke:]
    w1 = np.flatnonzero(cc < L - EPS * np.abs(L))
    rm = np.maximum.accumulate(cc)
    w2 = np.flatnonzero(cc <= rm * (1 - E2_DD) + 1e-12)
    trig = {"E1": ke + int(w1[0]) if len(w1) else -1, "E2": ke + int(w2[0]) if len(w2) else -1}
    why = {"E1": "跌回趨勢線下", "E2": "回落20%"}
    bk = np.flatnonzero(badk[ke + 1:])
    kb = ke + 1 + int(bk[0]) if len(bk) else -1
    for cell in CELLS:
        tg = trig[cell]
        sell = tg + 1 if tg >= 0 else None
        if kb >= 0 and (sell is None or kb <= sell):
            out[f"{cell}_xk"], out[f"{cell}_x"], out[f"{cell}_why"] = "close", int(idx[kb - 1]), "壞根前收盤強制出"
        elif tg >= 0:
            out[f"{cell}_xk"], out[f"{cell}_x"], out[f"{cell}_why"] = "open", int(idx[tg] + 1), why[cell]
    cs = c[B:]; rmB = np.maximum.accumulate(cs)
    st_ = np.flatnonzero((np.arange(B, m) >= ke) & (cs <= rmB * (1 - TOP_DD) + 1e-12))
    if len(st_):
        out["top"], out["top_closed"] = float(rmB[st_[0]]), True
    else:
        out["top"] = float(rmB[-1])
    return out


def stock_job_run(sid):
    X = stock_series(sid)
    if X is None:
        return sid, None
    cal, calE, calM = _G["cal"], _G["calE"], _G["calM"]; n = len(cal); nE = len(calE)
    bar = np.isfinite(X["c"]); idx = np.flatnonzero(bar); m = len(idx)
    lb = np.zeros(n, bool)
    lb[:nE] = bad_part(sid, EOTC, calE); lb[nE:] = bad_part(sid, MAIN, calM)
    lbj = lb.copy()
    if m > 1:
        g = np.flatnonzero(np.diff(idx) - 1 >= 5) + 1
        lbj[idx[g]] = True
    hb2 = X["hb"] | lbj
    a20 = np.full(n, np.nan)
    if m >= 20:
        a20[idx] = pd.Series(X["amt"][idx]).rolling(20, min_periods=20).mean().to_numpy()
    res = {"a20": a20.astype(np.float32), "bar": bar, "pv": X["pv"].copy(), "mkt_ok": bar & X["pv"],
           "twse": np.array([mm == "twse" for mm in X["mkt"]]) & bar, "nbar": m,
           "壞根（load_bars 規則，相接）": int(lbj.sum()), "freq 原硬斷點": int(X["hb"].sum()), "合計": int(hb2.sum()),
           "只在 load_bars 規則": int((lbj & ~X["hb"]).sum()), "lb_pos": np.flatnonzero(lbj).astype(np.int32)}
    c = X["c"][idx]; o = X["o"][idx]; h = X["h"][idx]; l = X["l"][idx]
    badk = hb2[idx]; cb = np.r_[0, np.cumsum(badk)]          # cb[k+1] ＝ 第 0..k 根壞根數
    for H in (H_EV, H_D):
        R_ = np.full(n, np.nan)
        if m > H + 1:
            k = np.arange(m - H)
            ok = (idx[k + 1] == idx[k] + 1) & np.isfinite(o[k + 1]) & (o[k + 1] > 0) & ((cb[k + H + 1] - cb[k + 1]) == 0)
            kk = k[ok]
            R_[idx[kk]] = c[kk + H] / o[kk + 1] - 1.0
        res[f"R{H}"] = R_
    hbc = np.cumsum(hb2); hbo = np.cumsum(X["hb"]); dc = np.cumsum(X["disp"])
    rows = {}
    for vn, kw in VARS.items():
        pairs, npair = detect(c, h, l, **kw)
        rr = []
        for i, j, B0, B, T, hL, atr, depth in pairs:
            H1p, H2p, Bp, Tp = int(idx[i]), int(idx[j]), int(idx[B]), int(idx[T])
            if Tp + 1 >= n:
                continue
            hard2 = bool((hbc[Tp] - hbc[H1p]) > 0); hard_old = bool((hbo[Tp] - hbo[H1p]) > 0)
            disp = bool((dc[Tp] - (dc[H1p - 1] if H1p > 0 else 0)) > 0)
            row = {"Tk": T, "H1k": i, "H2k": j, "B0k": B0, "Bk": B, "H1": H1p, "H2": H2p, "B": Bp, "T": Tp, "hL": hL, "atr": atr, "depth": depth,
                   "hard": hard_old, "hard2": hard2, "disp": disp, "pv": bool(X["pv"][Tp]), "mkt": X["mkt"][Tp], "lineH1": float(c[i]),
                   "slope": float((c[j] - c[i]) / (j - i))}
            if vn == "主" and not (hard2 or disp):
                row.update(barr_exits(c, o, idx, badk, i, j, T, B))
            rr.append(row)
        rows[vn] = rr
    res["rows"] = rows
    return sid, res


def build_events(P, hardcol, cnt=None):
    """freq 同一套：剔（hardcol｜處置）→ 同一 T 合成（H2 最晚、再 H1 最晚）→ GATE_V2 → 同檔 20 根去重。"""
    cnt = {} if cnt is None else cnt
    cnt["候選對"] = int(len(P))
    if not len(P):
        return P, cnt
    P = P.copy(); P["剔"] = P[hardcol] | P["disp"]
    cnt["剔：硬斷點"] = int(P[hardcol].sum()); cnt["剔：處置"] = int(P["disp"].sum())
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
    return E, cnt


def ev_verdict(st, fake_hw):
    if not st.get("n"):
        return "無事件"
    neff = min(st["n"], st["months"])
    if neff < 24:
        return "還沒測（n_eff ＜ 24）"
    if st["lo"] > 0:
        return "測得出" if st["mean"] > COST_RT else "統計層測得出、扣成本不夠（平均 ≤ 0.585%）"
    if st["hi"] < 0:
        return "反向（CI 全在 0 以下）"
    zero = abs(st["mean"]) <= COST_RT and np.isfinite(fake_hw) and fake_hw <= COST_RT
    return "零" if zero else "測不出"


def ev_stats(x, months, mk=None):
    x = np.asarray(x, float); months = np.asarray(months)
    ok = np.isfinite(x)
    st = R.cl_stats(x[ok], months[ok])
    if st.get("n"):
        st["n_eff"] = int(min(st["n"], st["months"])); st["hw"] = 1.96 * st["se"]
        st["p90"] = float(np.percentile(x[ok], 90))
        if mk is not None:
            mk = np.asarray(mk)[ok]
            st["上市"] = int((mk == "twse").sum()); st["上櫃"] = int((mk == "tpex").sum())
    return st


def run(a):
    from backtest import research11 as R_
    from backtest import researchRevLimitUp as RLU
    global R
    R = R_
    global OUT
    if a.smoke:
        OUT = os.path.join(WORK, "smoke_run")
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchBARR run {now_tpe()}（台北）｜讀法寫死 {RUN_TIME}｜reps {a.reps} fake {a.fake} smoke {a.smoke} =====")
    regf = reg_check(); log(f"[sha] {REG_SHA} ✔ {regf}")
    assert abs(R.COST - COST_RT) < 1e-12
    t00 = time.time()
    D.DATA = EOTC; calE = D.load_calendar(); D.DATA = MAIN; calM = D.load_calendar()
    cal = calE.append(calM); n = len(cal); nE = len(calE)
    sids = set()
    for DATA in (EOTC, MAIN):
        D.DATA = DATA
        st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
        sids |= {s for s in UG.gate3(st)["stock_id"] if okcode(s)}
    sids = sorted(sids)
    if a.smoke:
        sids = sids[::15]
    DISP = {}
    for DATA in (EOTC, MAIN):
        for k, v in disposal_iv(DATA).items():
            DISP.setdefault(k, []).extend(v)
    _G.update(calE=calE, calM=calM, cal=cal, DISP=DISP)
    log(f"[版面] 日曆 {cal[0].date()}～{cal[-1].date()}（{n}）；股票 {len(sids)}")
    cp = os.path.join(WORK, f"run_res{'_smoke' if a.smoke else ''}.pkl")
    if os.path.exists(cp) and a.reuse:
        RES = pickle.load(open(cp, "rb")); log("[偵測] 讀快取")
    else:
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for k, (sid, r) in enumerate(pool.imap_unordered(stock_job_run, sids, chunksize=4)):
                if r is not None:
                    RES[sid] = r
                if k % 200 == 0:
                    log(f"[偵測] {k}/{len(sids)}｜{time.time() - t0:.0f}s")
        pickle.dump(RES, open(cp, "wb"), protocol=5)
        log(f"[偵測] 完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
    sids = sorted(RES); S = len(sids); SI = {s: i for i, s in enumerate(sids)}
    A20 = np.vstack([RES[s]["a20"] for s in sids]); MK = np.vstack([RES[s]["mkt_ok"] for s in sids]) & np.isfinite(A20)
    BAR = np.vstack([RES[s]["bar"] for s in sids]); PV = np.vstack([RES[s]["pv"] for s in sids])
    MK2 = BAR & PV
    d16 = int(cal.searchsorted(pd.Timestamp(R1_DAY)))
    nu = int((MK[:, d16] & (A20[:, d16] >= LIQ)).sum()); nm = int(MK[:, d16].sum()); X1 = nu / nm
    R1M = np.zeros_like(MK)
    for d in range(n):
        ix = np.flatnonzero(MK[:, d])
        if len(ix):
            R1M[ix[np.argsort(-A20[ix, d], kind="stable")[:int(np.ceil(X1 * len(ix)))]], d] = True
    log(f"[R1] X ＝ {nu}／{nm} ＝ {X1:.4f}")
    BADINFO = {k: int(sum(RES[s][k] for s in sids)) for k in ("壞根（load_bars 規則，相接）", "freq 原硬斷點", "合計", "只在 load_bars 規則")}
    c3073 = None
    if "3073" in RES:
        p_ = int(cal.searchsorted(pd.Timestamp("2021-02-19")))
        c3073 = {"2021-02-19 在壞根（load_bars 規則）": bool(p_ in set(RES["3073"]["lb_pos"].tolist())),
                 "附近壞根日": [str(cal[q].date()) for q in RES["3073"]["lb_pos"] if abs(int(q) - p_) <= 30]}
    log(f"[壞根] {BADINFO}｜3073：{c3073}")
    # ── 事件（各變體）──
    EVV, CNT = {}, {}
    for vn in VARS:
        rows = []
        for si, s in enumerate(sids):
            for r in RES[s]["rows"][vn]:
                rows.append({"sid": s, "si": si, **r})
        P = pd.DataFrame(rows)
        E, cnt = build_events(P, "hard2")
        if vn == "主":
            Eo, cnto = build_events(P, "hard")
            fq = pd.read_csv(os.path.expanduser("~/tw-p17/backtest/resultsBARR/events_freq.csv.gz"), dtype={"sid": str})
            mine = set(zip(Eo["sid"], [str(cal[t].date()) for t in Eo["T"]]))
            mine = {x for x in mine if SEGS["全期"][0] <= x[1] <= SEGS["全期"][1]}
            theirs = {x for x in zip(fq["sid"], fq["日期"]) if SEGS["全期"][0] <= x[1] <= SEGS["全期"][1]}
            gate = (mine == theirs) if not a.smoke else (mine <= theirs)
            CNT["freq 原規則重跑"] = {**cnto, "全期筆數": len(mine), "＝ events_freq.csv.gz": bool(gate)}
            log(f"[閘] freq 原硬斷點規則重跑 {len(mine)} 筆 ⇒ 與 events_freq.csv.gz {'逐筆相同' if gate else '⛔ 不同'}")
            if not gate:
                raise SystemExit("⛔ freq 原規則重跑與 events_freq.csv.gz 不同 ⇒ 停")
        E["5000萬"] = (MK & (np.nan_to_num(A20, nan=0.0) >= LIQ))[E["si"].to_numpy(), E["T"].to_numpy()] if len(E) else []
        E["R1"] = R1M[E["si"].to_numpy(), E["T"].to_numpy()] if len(E) else []
        EVV[vn] = E; CNT[vn] = cnt
        log(f"[事件 {vn}] {json.dumps(cnt, ensure_ascii=False)}")
    # ── 事件層（R2～R4）──
    RM = {H: np.vstack([RES[s][f"R{H}"] for s in sids]) for H in (H_EV, H_D)}
    EW = {}
    with np.errstate(invalid="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore")
        for H in (H_EV, H_D):
            Z_ = np.where(MK2, RM[H], np.nan)
            EW[H] = np.nanmean(Z_, axis=0); EW[f"n{H}"] = np.isfinite(Z_).sum(axis=0)
    ev0 = int(cal.searchsorted(pd.Timestamp(EV_FROM)))
    MON = np.array([d.strftime("%Y-%m") for d in cal])

    def ev_table(E, H):
        e = E[E["T"] >= ev0]
        x = RM[H][e["si"].to_numpy(), e["T"].to_numpy()] - EW[H][e["T"].to_numpy()]
        return e, x
    EVL = {}
    Em = EVV["主"]
    e20, x20 = ev_table(Em, H_EV)
    Em = Em.copy()
    Em["R20"] = RM[H_EV][Em["si"].to_numpy(), Em["T"].to_numpy()]; Em["EW20"] = EW[H_EV][Em["T"].to_numpy()]; Em["X20"] = Em["R20"] - Em["EW20"]
    Em["R60"] = RM[H_D][Em["si"].to_numpy(), Em["T"].to_numpy()]; Em["EW60"] = EW[H_D][Em["T"].to_numpy()]; Em["X60"] = Em["R60"] - Em["EW60"]
    EVV["主"] = Em
    ew_ = Em[Em["T"] >= ev0]
    drop = {"T ≥ 2005-01-03 事件": int(len(ew_)), "R20 不可算（T＋1 停牌／開盤缺／持有期壞根／資料尾）": int((~np.isfinite(ew_["R20"])).sum())}
    # 不可算拆細
    nb_ = 0; nh_ = 0; nt_ = 0
    for s, T in zip(ew_.loc[~np.isfinite(ew_["R20"]), "sid"], ew_.loc[~np.isfinite(ew_["R20"]), "T"]):
        b = RES[s]["bar"]
        if T + 1 >= n or not b[T + 1]:
            nh_ += 1
        else:
            nb_ += 1
    drop["其中 T＋1 停牌或資料尾"] = nh_; drop["其中 持有期壞根／開盤缺／不足 20 根"] = nb_
    XE = ew_["X20"].to_numpy(); ME = MON[ew_["T"].to_numpy()]
    st_main = ev_stats(XE, ME, ew_["mkt"].to_numpy())
    log(f"[事件層 H20] n {st_main.get('n')}、平均 {st_main.get('mean', np.nan):+.4%}、CI [{st_main.get('lo', np.nan):+.4%}, {st_main.get('hi', np.nan):+.4%}]、月 {st_main.get('months')}")
    # 假訊號（R3）
    okX = np.isfinite(ew_["X20"].to_numpy())
    TE = ew_[okX]
    byS = {s: np.sort(g["T"].to_numpy()) for s, g in TE.groupby("sid")}
    CAND = {}
    for s, Ts in byS.items():
        si = SI[s]; P_ = np.flatnonzero(BAR[si])
        okc = MK2[si, P_] & np.isfinite(RM[H_EV][si, P_]) & (P_ >= ev0)
        kr = np.searchsorted(P_, Ts)
        ex = np.zeros(len(P_) + FK_EXCL + 2, int)
        np.add.at(ex, kr, 1); np.add.at(ex, np.minimum(kr + FK_EXCL + 1, len(ex) - 1), -1)
        ex = np.cumsum(ex)[:len(P_)] > 0
        CAND[s] = P_[okc & ~ex]
    FKR = []
    for r in range(FK_REPS):
        rng = np.random.default_rng([FK_SEED, r]); xs, ms_ = [], []
        short = 0
        for s in sorted(byS):
            k = len(byS[s]); C_ = CAND[s]
            if len(C_) < k:
                short += 1
            pk = rng.choice(C_, size=min(k, len(C_)), replace=False) if len(C_) else np.array([], int)
            xs.append(RM[H_EV][SI[s], pk] - EW[H_EV][pk]); ms_.append(MON[pk])
        stf = ev_stats(np.concatenate(xs), np.concatenate(ms_))
        FKR.append({"r": r, "n": stf["n"], "平均": stf["mean"], "下界": stf["lo"], "上界": stf["hi"], "半寬": stf["hw"], "月": stf["months"],
                    "測得出": bool(stf["lo"] > 0 and stf["mean"] > COST_RT), "CI不含0": bool(stf["lo"] > 0 or stf["hi"] < 0), "可抽不足檔": short})
    FKD = pd.DataFrame(FKR)
    fk_hw = float(FKD["半寬"].median()); xk = int(FKD["測得出"].sum())
    verdict = ev_verdict(st_main, fk_hw)
    EVL["H20"] = {**{k: v for k, v in st_main.items()}, "判定": verdict, "假訊號 x／30": xk, "假訊號 CI不含0 次數": int(FKD["CI不含0"].sum()),
                  "假訊號半寬中位": fk_hw, "這一格的過關不構成證據": bool(xk >= 15), "剔除": drop,
                  "零四條件": {"① CI 含 0": bool(st_main["lo"] <= 0 <= st_main["hi"]), "② |平均| ≤ 0.585%": bool(abs(st_main["mean"]) <= COST_RT),
                             "③ n_eff ≥ 24": bool(st_main["n_eff"] >= 24), "④ 假訊號半寬 ≤ 0.585%": bool(fk_hw <= COST_RT)},
                  "假訊號逐次": FKR}
    log(f"[事件層 H20] 判定 {verdict}｜假訊號 x／30 ＝ {xk}、半寬中位 {fk_hw:.4%}")
    # 描述（R4）
    DESC_EV = {}
    st60 = ev_stats(ew_["X60"].to_numpy(), ME, ew_["mkt"].to_numpy()); DESC_EV["H60（⚠ 月分群偏窄）"] = st60
    tw = ew_["mkt"].to_numpy() == "twse"
    DESC_EV["只取上市 H20"] = ev_stats(XE[tw], ME[tw])
    for k_, (x_, y_) in SEGS.items():
        a_, b_ = int(cal.searchsorted(pd.Timestamp(x_))), int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1
        mm = (ew_["T"].to_numpy() >= a_) & (ew_["T"].to_numpy() <= b_)
        DESC_EV[f"{k_} H20"] = ev_stats(XE[mm], ME[mm])
    DESC_EV["R1 母體內 H20"] = ev_stats(XE[ew_["R1"].to_numpy(bool)], ME[ew_["R1"].to_numpy(bool)])
    for vn in VARS:
        if vn == "主":
            continue
        e_, x_ = ev_table(EVV[vn], H_EV)
        DESC_EV[f"變體 {vn} H20"] = {**ev_stats(x_, MON[e_["T"].to_numpy()]), "事件（全期）": int(len(e_))}
    EVL["描述"] = DESC_EV
    EVL["R 的中位（事件、原始報酬）"] = float(np.nanmedian(ew_["R20"])); EVL["X 的中位"] = float(np.nanmedian(XE))
    EVL["EW20 每日檔數中位"] = float(np.median(EW[f"n{H_EV}"][ev0:][EW[f"n{H_EV}"][ev0:] > 0]))
    # 事件表存檔
    keepc = ["sid", "T", "Tk", "H1", "H2", "B", "H1k", "H2k", "Bk", "hL", "atr", "depth", "對數", "mkt", "5000萬", "R1", "R20", "EW20", "X20", "R60", "EW60", "X60",
             "oE", "cB", "top", "top_closed"] + [f"{c}_{k}" for c in CELLS for k in ("xk", "x", "why")] + ["lineH1", "slope"]
    EO = Em[keepc].copy()
    for k in ("T", "H1", "H2", "B"):
        EO[f"{k}日"] = [str(cal[t].date()) for t in EO[k]]
    for c in CELLS:
        EO[f"{c}_x日"] = [str(cal[int(x)].date()) if np.isfinite(x) and 0 <= x < n else "" for x in EO[f"{c}_x"].astype(float)]
    EO.to_csv(os.path.join(OUT, "events_run.csv.gz"), index=False, float_format="%.10g")
    # ═════ 組合層 ═════
    WM = RLU.World("main", a.procs, log); WE = RLU.World("early", a.procs, log)
    assert WM.n == len(calM) and (WM.cal == calM).all() and WE.n == nE and (WE.cal == calE).all()
    seg = {k: WM.segpos(*v) for k, v in PSEGS.items()}
    Z = {k: RR.bench_row(WM.cal, WM.bench, x, y + 1) for k, (x, y) in seg.items()}
    g0 = (repr(Z["主窗"]["cagr"]) == repr(ANCHOR[0]), repr(Z["主窗"]["mdd"]) == repr(ANCHOR[1]))
    log(f"[0050] 主窗錨逐位元 {g0}")
    if not all(g0):
        raise SystemExit("⛔ 0050 錨不對")
    w0, w1 = seg["主窗"]
    EP = Em[Em["R1"].astype(bool)].reset_index(drop=True)

    def wsig(W, off):
        rows, miss = [], 0
        for r in EP.itertuples(index=False):
            Tw = int(r.T) - off
            if not (0 <= Tw < W.n - 1):
                continue
            i = W.ix.get(r.sid)
            if i is None:
                miss += 1; continue
            rows.append((i, Tw + 1, r.sid, int(r.T)) + tuple(getattr(r, f"{c}_{k}") for c in CELLS for k in ("xk", "x", "why")) + (r.oE, r.cB, r.top, bool(r.top_closed)))
        cols = ["s", "e", "sid", "Tst"] + [f"{c}_{k}" for c in CELLS for k in ("xk", "x", "why")] + ["oE", "cB", "top", "top_closed"]
        return pd.DataFrame(rows, columns=cols), miss

    def wrows(W, off, S_, cell):
        out = []
        for r in S_.itertuples(index=False):
            xk, x, why = getattr(r, f"{cell}_xk"), int(getattr(r, f"{cell}_x")), getattr(r, f"{cell}_why")
            xw = x - off if x >= 0 else -1
            if xw >= W.n or xw < 0:
                xw, why = -1, "未完"
            out.append((int(r.s), int(r.e), xk, xw, why, np.nan))
        return pd.DataFrame(out, columns=["s", "e", "xk", "x", "why", "key"])
    SM, missM = wsig(WM, nE)
    SMw = SM[(SM["e"] >= w0) & (SM["e"] <= w1)].reset_index(drop=True)
    log(f"[訊號] 主段 R1 事件 {len(SM)}（版面缺 {missM}）、主窗內 {len(SMw)}")
    FB_, FR_ = {}, {}
    for c in CELLS:
        rw = wrows(WM, nE, SMw, c)
        FB_[c] = RLU.finalize_rows(WM, rw, False); FR_[c] = RLU.finalize_rows(WM, rw, True)
        log(f"[出場] {c}：可進 {len(FB_[c])}（e 無有效開盤剔 {len(rw) - len(FB_[c])}）、未完 {int(FB_[c]['end'].sum())}｜{FB_[c]['why'].value_counts().to_dict()}")
    arms = []
    for c in CELLS:
        arms.append((f"{c}|b", FB_[c], False, a.reps)); arms.append((f"{c}|r", FR_[c], True, a.reps))
    RES_ = RLU.run_arms(WM, arms, seg, w1, a.procs, log)
    # ── 退化（先寫）──
    DG = {}
    for nm_, ms in RES_.items():
        h = RLU.hold_only(ms, seg)
        DG[nm_] = {**h, "探索_退化": RLU.degen(h, "探索"), "確認_退化": RLU.degen(h, "確認"), "主窗_退化": RLU.degen(h, "主窗"), "種子": len(ms)}
    cand = {}
    for c in CELLS:
        g = FB_[c].groupby("e").size()
        cand[c] = {"有進場的日子": int(len(g)), "主窗訊號": int(len(FB_[c])), "每個進場日訊號數": RLU.q_(g.to_numpy()),
                   "訊號數逐年（進場日）": {str(k): int(v) for k, v in pd.Series([WM.cal[e].year for e in FB_[c]["e"]]).value_counts().sort_index().items()}}
    DJ = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在彙總任何報酬之前寫入（R9）；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）；退化格照登錄排除",
          "候選與訊號": cand, "持股與現金": DG,
          "排除的格（探索段退化）": sorted({k.split('|')[0] for k, v in DG.items() if k.endswith('|b') and v['探索_退化']}),
          "各段退化列表": {k: [sg for sg in ("探索", "確認", "主窗") if v[f"{sg}_退化"]] for k, v in DG.items()}}
    json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[退化] 已寫 degeneracy.json：" + "；".join(f"{k} 探索 {v['探索_平均持股']:.2f} 檔／現金 {v['探索_平均現金']:.1%}、確認 {v['確認_平均持股']:.2f}／{v['確認_平均現金']:.1%}"
                                              for k, v in DG.items()))
    # ── 早年：先跑、先寫退化，再彙總任何報酬 ──
    ea, eb = WE.segpos(*PEARLY); es = {"早年": (ea, eb)}
    SE_, missE = wsig(WE, 0)
    SE_ = SE_[(SE_["e"] >= ea) & (SE_["e"] <= eb)].reset_index(drop=True)
    FE, FER, arms = {}, {}, []
    for c in CELLS:
        rw = wrows(WE, 0, SE_, c)
        FE[c] = RLU.finalize_rows(WE, rw, False); FER[c] = RLU.finalize_rows(WE, rw, True)
        arms.append((f"{c}|b", FE[c], False, a.reps)); arms.append((f"{c}|r", FER[c], True, a.reps))
    RE_ = RLU.run_arms(WE, arms, es, eb, a.procs, log)
    HE = {k: RLU.hold_only(ms, es) for k, ms in RE_.items()}
    DJ = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
    DJ["早年"] = {"寫入時間": now_tpe() + "（台北）", "窗": list(PEARLY), "訊號": int(len(SE_)),
                "持股與現金": {k: {**h, "早年_退化": RLU.degen(h, "早年")} for k, h in HE.items()}}
    json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[退化] 早年已補寫：" + "；".join(f"{k} {h['早年_平均持股']:.2f} 檔／現金 {h['早年_平均現金']:.1%}" for k, h in HE.items()))
    # ── 報酬、挑格 ──
    GRID = [{"格": k.split("|")[0], "版本": k.split("|")[1], **RLU.summarize(ms, Z, seg), **DG[k]} for k, ms in RES_.items()]
    GR = pd.DataFrame(GRID)
    base = GR[GR["版本"] == "b"].copy(); base["_ord"] = [CELLS.index(c) for c in base["格"]]
    nd = base[~base["探索_退化"]]; all_deg = len(nd) == 0
    pool_ = nd if not all_deg else base
    qq = pool_[pool_["探索_標籤"] == "合格"]
    pick = (qq if len(qq) else pool_).sort_values(["探索_比值", "探索_年化", "_ord"], ascending=[False, False, True]).iloc[0]
    chosen = pick["格"]
    log(f"[挑格] 非退化 {len(nd)}／{len(base)}、探索合格 {len(qq)} ⇒ {chosen}{'（⚠ 全退化）' if all_deg else ''}")
    CH = {v: {k: x for k, x in GR[(GR["格"] == chosen) & (GR["版本"] == v)].iloc[0].to_dict().items() if not k.startswith("_")} for v in ("b", "r")}
    ZE = {"早年": RR.bench_row(WE.cal, WE.bench, ea, eb + 1)}
    EG = {k: {**{kk: v for kk, v in RLU.summarize(ms, ZE, es).items() if not kk.startswith("_")}, **HE[k], "早年_退化": RLU.degen(HE[k], "早年")} for k, ms in RE_.items()}
    lab_e, lab_er = EG[f"{chosen}|b"]["早年_標籤"], EG[f"{chosen}|r"]["早年_標籤"]
    deg_c = DG[f"{chosen}|b"]["確認_退化"]; deg_e = EG[f"{chosen}|b"]["早年_退化"]
    lab_c, lab_cr = CH["b"]["確認_標籤"], CH["r"]["確認_標籤"]
    fin_b = RLU.stricter(lab_c, lab_e); fin_r = RLU.stricter(lab_cr, lab_er)
    if deg_c or deg_e:
        fin_b = f"退化（{'確認' if deg_c else ''}{'早年' if deg_e else ''}段）⇒ 照登錄排除、不判合格"
    VERD = {"挑中格": chosen, "全退化": all_deg, "探索": CH["b"]["探索_標籤"], "確認": lab_c, "早年": lab_e, "判定": fin_b,
            "現實版探索": CH["r"]["探索_標籤"], "現實版確認": lab_cr, "現實版早年": lab_er, "現實版判定": fin_r, "事後重切": False}
    log(f"[判定] {VERD}")
    # ── 對照與描述 ──
    Fc = FB_[chosen]
    darms = [(f"固定{H}", RLU.finalize_rows(WM, RLU.fixed_rows(WM, Fc, H), False), False, 50) for H in (20, 60, 120)]
    ma = pd.Series(WM.bench).rolling(200, min_periods=200).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        keep = WM.bench[Fc["e"].to_numpy(int) - 1] > ma[Fc["e"].to_numpy(int) - 1]
    darms.append(("0050在200日線上才買", Fc[keep].reset_index(drop=True), False, 50))
    UW = np.zeros((WM.S, WM.n), bool)
    for i, s in enumerate(WM.sids):
        if s in SI:
            UW[i] = R1M[SI[s], nE:nE + WM.n]
    for i in range(a.fake):
        darms.append((f"假訊號#{i}", RLU.finalize_rows(WM, RLU.fake_rows(WM, Fc, UW, i), False), False, ("fake", i)))
    DRES = RLU.run_arms(WM, darms, seg, w1, a.procs, log)
    DESC = {k: {**{kk: v for kk, v in RLU.summarize(ms, Z, seg).items() if not kk.startswith("_")}, **RLU.hold_only(ms, seg)} for k, ms in DRES.items() if not k.startswith("假訊號#")}
    DESC["0050在200日線上才買"]["訊號（主窗）"] = int(keep.sum())
    FK = [RLU.summarize(ms, Z, seg) for k, ms in DRES.items() if k.startswith("假訊號#")]
    FAKE = {}
    for sg in PSEGS:
        v = np.array([x[f"{sg}_年化"] for x in FK]); d_ = np.array([x[f"{sg}_回落"] for x in FK])
        FAKE[sg] = {"抽數": len(v), "年化中位": float(np.nanmedian(v)), "年化p10": float(np.nanpercentile(v, 10)), "年化p90": float(np.nanpercentile(v, 90)),
                    "回落中位": float(np.nanmedian(d_)), "p（假訊號年化 ≥ 挑中格）": float(np.mean(v >= CH["b"][f"{sg}_年化"])),
                    "假訊號合格比例": float(np.mean([RLU.label(c_, m_, Z[sg])[0] == "合格" for c_, m_ in zip(v, d_)]))}
    # ── 必報 ──
    msC = RES_[f"{chosen}|b"]; msR = RES_[f"{chosen}|r"]
    TS = {"b": RLU.trade_stats(WM, msC, Fc, w1), "r": RLU.trade_stats(WM, msR, FR_[chosen], w1)}
    TS_other = {c: RLU.trade_stats(WM, RES_[f"{c}|b"], FB_[c], w1) for c in CELLS if c != chosen}
    TSE = RLU.trade_stats(WE, RE_[f"{chosen}|b"], FE[chosen], eb)

    def capture(ms, F, S_):
        info = {(r.sid, int(r.e)): (r.oE, r.cB, r.top, r.top_closed) for r in S_.itertuples(index=False)}
        key = {(sid, int(e)): k for k, (sid, e) in enumerate(zip(F["sid"], F["e"]))}
        eat, eat2 = [], []
        for m_ in ms:
            for sid, t0, t1, a_, p_ in m_["iv"]:
                k = key.get((sid, t0))
                if k is None:
                    continue
                row = F.iloc[k]
                if int(row["end"]) or t1 != int(row["xpos"]) or row["why"] == "壞根前收盤強制出":
                    continue
                oE, cB, top, cl = info[(sid, t0)]
                if not cl or not np.isfinite(oE):
                    continue
                sell = (1 + float(row["g"])) * oE
                eat.append((sell - cB) / (top - cB))
                if top >= oE * 1.05:
                    eat2.append((sell - oE) / (top - oE))
        return {"吃到起漲→頂幾成": RLU.q_(eat), "吃到（買價基準）": RLU.q_(eat2)}
    CAP = {c: capture(RES_[f"{c}|b"], FB_[c], SMw) for c in CELLS}
    NE = {}
    iv0 = msC[0]["iv"]; days = sorted({t0 for s_, t0, t1, a_, p_ in iv0})
    res_ne = RLU.eff_n(WM, iv0, days)
    for sg, (x_, y_) in seg.items():
        rr = [q for q in res_ne if x_ <= q[0] <= y_]
        if rr:
            NE[sg] = {"換股日": len(rr), "平均持股": float(np.mean([q[1] for q in rr])), "平均ρ": float(np.nanmean([q[2] for q in rr])),
                      "平均N_eff": float(np.nanmean([q[3] for q in rr])), "N_eff中位": float(np.nanmedian([q[3] for q in rr]))}
    YR = {k: float(np.median([RLU.years_ret(m_["eq"], WM.cal, w0, w1)[k] for m_ in msC])) for k in RLU.years_ret(msC[0]["eq"], WM.cal, w0, w1)}
    YRr = {k: float(np.median([RLU.years_ret(m_["eq"], WM.cal, w0, w1)[k] for m_ in msR])) for k in RLU.years_ret(msR[0]["eq"], WM.cal, w0, w1)}
    YR50 = RLU.years_ret(WM.bench, WM.cal, w0, w1)
    Y = RLU.yl_ref(log); YC = RLU.yl_cells()
    ovl = {}
    for fam, nmf in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        ivB = [(s_, WM.pos(a_), WM.pos(b_) if b_ != "9999-12-31" else WM.n + 1) for s_, a_, b_ in Y[fam]["iv"]]
        for sg, (x_, y_) in seg.items():
            ovl.setdefault(sg, {})[f"與{nmf}持股重疊率"] = RLU.overlap_daily(msC[0]["iv"], ivB, x_, y_)
    SLIP = {"現實版比 0.585% 版（年化點）": {c: {sg: (GR[(GR["格"] == c) & (GR["版本"] == "r")].iloc[0][f"{sg}_年化"] - GR[(GR["格"] == c) & (GR["版本"] == "b")].iloc[0][f"{sg}_年化"]) * 100
                                          for sg in PSEGS} for c in CELLS},
            "引擎（現實版，種子中位）": {c: {"漲停買不到": float(np.median([m_["lu"] for m_ in RES_[f"{c}|r"]])),
                                         "停牌買不到": float(np.median([m_["halt_in"] for m_ in RES_[f"{c}|r"]]))} for c in CELLS},
            "訊號層 e 開盤鎖漲停（一價到底）筆": int(sum(bool(WM.UPL[s_, e_]) for s_, e_ in zip(SMw["s"], SMw["e"]))), "主窗訊號": int(len(SMw))}
    EARLYR = {"窗": list(PEARLY), "0050": ZE["早年"], "格": EG, "訊號": int(len(SE_)), "版面缺": missE, "逐筆": TSE,
              "各年（策略種子中位）": {k: float(np.median([RLU.years_ret(m_["eq"], WE.cal, ea, eb)[k] for m_ in RE_[f"{chosen}|b"]]))
                                for k in RLU.years_ret(RE_[f"{chosen}|b"][0]["eq"], WE.cal, ea, eb)},
              "各年0050": RLU.years_ret(WE.bench, WE.cal, ea, eb), "說明": "早年上櫃日 K 2007-07 起；只用價量（日線判）"}
    fq = json.load(open(os.path.expanduser("~/tw-p17/backtest/resultsBARR/freq.json"), encoding="utf-8"))
    SUM = {"meta": {"件": "PREREG碰撞回落底部（BARR 底）seq2 —— 報酬（run）", "登錄": regf, "sha": REG_SHA, "freq 讀法寫死": TIME, "run 讀法寫死": RUN_TIME,
                    "run": now_tpe() + "（台北）", "reps": a.reps, "fake": a.fake, "smoke": bool(a.smoke), "N": "N_單筆 ＋1（H20）、N_組合 ＋1（E1／E2 兩格挑 1）；不是事後重切",
                    "版面": {"相接": [str(cal[0].date()), str(cal[-1].date()), n, S], "main": [str(WM.cal[0].date()), str(WM.cal[-1].date()), WM.n, WM.S],
                           "早年": [str(WE.cal[0].date()), str(WE.cal[-1].date()), WE.n, WE.S]},
                    "0050": Z, "成本": {"0.585%版": COST_RT, "現實版引擎成本": RLU.COST_R}, "R1": {"X": X1, "2016-01-04 5,000萬母體": nu, "同日全市場": nm},
                    "硬斷點": {"用哪一套": "research11.load_bars 壞根規則（幽靈事件 ∪ 缺口 ≥ 5（無流動性前提）∪ applies 斷點，逐版面照抄）＋ 相接序列缺口 ≥ 5 ＋ freq 原有（相接 applies 斷點、adj 減資／面額）＋ 處置；⛔ 不是只用 data.breakpoints applies()",
                             "計數（股-日）": BADINFO, "3073": c3073}},
           "結果句必附": ["本件導入段平均比原文長（47.5 交易日）", "頻率每檔每年 0.72 次", "原文平均 35 個日曆天"],
           "freq 對照": {"freq 全期事件": fq["各段"]["全期"]["事件"], "freq 導入段平均": fq["導入段長度（K 棒＝交易日）"]["全期"]["平均"],
                       "freq 每檔每年": fq["各段"]["全期"]["每檔每年（全市場）"]},
           "事件計數": CNT, "事件層": EVL, "判定": VERD, "挑中格": CH, "退化": DJ, "格": [{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID],
           "早年": EARLYR, "假訊號": FAKE, "描述": DESC, "逐筆": TS, "逐筆（另一格）": TS_other, "吃到起漲→頂": CAP, "等效獨立": NE,
           "各年": {"策略": YR, "策略現實版": YRr, "0050": YR50}, "營量營飆": YC, "營量營飆r0閘": Y["閘"], "重疊": ovl, "滑價與買不到": SLIP,
           "訊號": {"主段 R1 事件": int(len(SM)), "主窗內": int(len(SMw)), "早年窗內": int(len(SE_))}, "耗時秒": round(time.time() - t00)}
    # 導入段（run 事件）
    lead = (Em["H2k"] - Em["H1k"]).to_numpy()
    SUM["run 事件導入段（K 棒）"] = {"平均": float(lead.mean()), "中位": float(np.median(lead)), "n": int(len(lead))}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
    pd.DataFrame([{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID] +
                 [{"格": k.split("|")[0], "版本": k.split("|")[1] + "_早年", **v} for k, v in EG.items()]).to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    seeds = []
    for nm_, ms in list(RES_.items()) + list(DRES.items()):
        for m_ in ms:
            seeds.append({"arm": nm_, "r": m_["r"], **RLU.seg_ret(m_, seg), **m_["hold"], "trades": m_["trades"], "sha": hashlib.sha256(m_["eq"].tobytes()).hexdigest()[:16]})
    for nm_, ms in RE_.items():
        for m_ in ms:
            seeds.append({"arm": nm_ + "_早年", "r": m_["r"], **RLU.seg_ret(m_, es), **m_["hold"], "trades": m_["trades"], "sha": hashlib.sha256(m_["eq"].tobytes()).hexdigest()[:16]})
    pd.DataFrame(seeds).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.10g")
    FKD.to_csv(os.path.join(WORK, "fake_ev.csv"), index=False)
    log(f"[完] {VERD}｜事件層 {verdict}｜{time.time() - t00:.0f}s")


# ═════════════ --check（獨立寫法抽樣）═════════════
def _ck_lb(sid):
    from backtest import research11 as R11
    calE, calM = _G["calE"], _G["calM"]
    res = []
    for DATA, cl in ((MAIN, calM), (EOTC, calE)):
        D.DATA = DATA
        if not os.path.exists(os.path.join(DATA, "stocks", f"{sid}.csv")):
            continue
        B = R11.load_bars(sid, "twse", cl)
        mine = bad_part(sid, DATA, cl)
        D.DATA = DATA
        if B is None:
            continue
        nb = B["next_bad"][:len(B["idx"])]
        bad = nb == np.arange(len(B["idx"]))
        ref = np.zeros(len(cl), bool); ref[B["idx"][bad]] = True
        res.append(int((ref != mine).sum()))
    return sid, res


def _ck_one(sid):
    cal, calE, calM, Tset = _G["cal"], _G["calE"], _G["calM"], _G["Tset"]; n = len(cal); nE = len(calE)
    X = stock_series(sid)
    if X is None:
        return sid, None
    lb = np.zeros(n, bool); lb[:nE] = bad_part(sid, EOTC, calE); lb[nE:] = bad_part(sid, MAIN, calM)
    bars = [k for k in range(n) if np.isfinite(X["c"][k])]
    for q in range(1, len(bars)):
        if bars[q] - bars[q - 1] - 1 >= 5:
            lb[bars[q]] = True
    bad = lb | X["hb"]
    pos = {k: q for q, k in enumerate(bars)}
    r = {}
    for T in Tset:
        if T not in pos or not X["pv"][T]:
            continue
        q = pos[T]
        if q + 20 >= len(bars) or bars[q + 1] != T + 1:
            continue
        oo = X["o"][bars[q + 1]]
        if not (np.isfinite(oo) and oo > 0):
            continue
        if any(bad[bars[z]] for z in range(q + 1, q + 21)):
            continue
        r[T] = X["c"][bars[q + 20]] / oo - 1.0
    return sid, ((r, X, bad, bars) if sid in _G["smp_s"] else (r, None, None, None))


def check(a):
    """獨立寫法：純迴圈重算抽樣事件的 R20／EW20／X20、E1／E2 出場根與報酬、真頂；壞根集合對 research11.load_bars 本體；3073。"""
    from backtest import research11 as R11
    from backtest import researchRevLimitUp as RLU
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchBARR check {now_tpe()}（台北）=====")
    D.DATA = EOTC; calE = D.load_calendar(); D.DATA = MAIN; calM = D.load_calendar()
    cal = calE.append(calM); n = len(cal); nE = len(calE)
    _G.update(calE=calE, calM=calM, cal=cal, DISP={})
    EV = pd.read_csv(os.path.join(OUT, "events_run.csv.gz"), dtype={"sid": str}, keep_default_na=False, na_values=[""])
    rng = np.random.default_rng(20261011)
    ok = EV[np.isfinite(EV["R20"].astype(float))]
    smp = ok.iloc[np.sort(rng.choice(len(ok), size=min(150, len(ok)), replace=False))]
    out = {"時間": now_tpe() + "（台北）", "抽樣事件": int(len(smp))}
    # ① 壞根集合 vs research11.load_bars（main、早年各自；≥ 260 根者）
    D.DATA = MAIN
    st = pd.read_csv(os.path.join(MAIN, "meta", "stocks.csv"), dtype=str)
    allsid = sorted({s for s in UG.gate3(st)["stock_id"] if okcode(s)})
    lbsid = sorted(set(allsid[::5]) | set(smp["sid"]) | {"3073"})
    diff = 0; nst = 0
    with Pool(a.procs) as pool:
        for sid, r in pool.imap_unordered(_ck_lb, lbsid, chunksize=4):
            nst += len(r); diff += sum(r)
    out["壞根 vs research11.load_bars"] = {"檔-版面": nst, "不同的日": diff}
    log(f"[check] 壞根對 load_bars：{nst} 檔-版面、不同 {diff}")
    D.DATA = MAIN
    B = R11.load_bars("3073", "twse", calM)
    p_ = int(calM.searchsorted(pd.Timestamp("2021-02-19")))
    k_ = int(np.searchsorted(B["idx"], p_))
    out["3073 2021-02-19"] = {"load_bars 壞根": bool(B["next_bad"][k_] == k_ and B["idx"][k_] == p_),
                              "events_run 有 3073 的 H1～T 跨 2021-02-19": int(((EV["sid"] == "3073") & (EV["H1"] < nE + p_) & (EV["T"] >= nE + p_)).sum())}
    # ② 抽樣事件：純迴圈重算
    Tset = sorted(set(smp["T"].astype(int)))
    _G.update(Tset=Tset, smp_s=set(smp["sid"]))
    D.DATA = MAIN
    sids = set()
    for DATA in (EOTC, MAIN):
        stx = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
        sids |= {s for s in UG.gate3(stx)["stock_id"] if okcode(s)}
    sids = sorted(sids)
    acc = {T: [] for T in Tset}; keep = {}
    smp_s = set(smp["sid"])
    with Pool(a.procs) as pool:
        for sid, v in pool.imap_unordered(_ck_one, sids, chunksize=8):
            if v is None:
                continue
            for T, x in v[0].items():
                acc[T].append(x)
            if sid in smp_s:
                keep[sid] = v
    nd = {"R20": 0, "EW20": 0, "X20": 0, "E1出場日": 0, "E2出場日": 0, "真頂": 0}
    bad_rows = []
    for r in smp.itertuples(index=False):
        rr, X, bad, bars = keep[r.sid]
        T = int(r.T)
        R_ = rr.get(T, np.nan); EWv = float(np.mean(acc[T]))
        for nm_, mine, theirs in (("R20", R_, r.R20), ("EW20", EWv, r.EW20), ("X20", R_ - EWv, r.X20)):
            if not (abs(mine - float(theirs)) <= 1e-9 * max(1.0, abs(mine))):
                nd[nm_] += 1; bad_rows.append((r.sid, T, nm_, mine, theirs))
        # E1／E2（純迴圈）
        pos = {k: q for q, k in enumerate(bars)}
        q = pos[T]; c = X["c"]
        i, j = int(r.H1k), int(r.H2k)
        cH1 = c[bars[i]]; sl = (c[bars[j]] - cH1) / (j - i)
        e1 = e2 = None; mx = -np.inf; kb = None
        for z in range(q + 1, len(bars)):
            cz = c[bars[z]]; Lz = cH1 + sl * (z - i)
            if e1 is None and cz < Lz - EPS * abs(Lz):
                e1 = z
            mx = max(mx, cz)
            if e2 is None and cz <= mx * 0.8 + 1e-12:
                e2 = z
            if kb is None and z >= q + 2 and bad[bars[z]]:
                kb = z
        for nm_, tg in (("E1", e1), ("E2", e2)):
            if kb is not None and (tg is None or kb <= tg + 1):
                exp = ("close", bars[kb - 1])
            elif tg is not None:
                exp = ("open", bars[tg] + 1)
            else:
                exp = ("open", -1)
            got = (getattr(r, f"{nm_}_xk"), int(getattr(r, f"{nm_}_x")))
            if exp != got:
                nd[f"{nm_}出場日"] += 1; bad_rows.append((r.sid, T, nm_, exp, got))
        Bq = int(r.Bk); mx = -np.inf; top = None
        for z in range(Bq, len(bars)):
            mx = max(mx, c[bars[z]])
            if z >= q + 1 and c[bars[z]] <= mx * 0.7 + 1e-12:
                top = mx; break
        top = mx if top is None else top
        if abs(top - float(r.top)) > 1e-9 * top:
            nd["真頂"] += 1; bad_rows.append((r.sid, T, "top", top, r.top))
    out["抽樣不同"] = nd; out["不同列（前 20）"] = [list(map(str, x)) for x in bad_rows[:20]]
    # ③ 組合層：抽樣訊號的出場價、報酬（world 純迴圈）
    WM = RLU.World("main", a.procs, log)
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ch = S["判定"]["挑中格"]
    w0, w1 = WM.segpos(*PSEGS["主窗"])
    EP = EV[(EV["R1"].astype(str) == "True") & (EV["T"] >= nE)]
    EP = EP[(EP["T"] - nE + 1 >= w0) & (EP["T"] - nE + 1 <= w1)]
    sp = EP.iloc[np.sort(rng.choice(len(EP), size=min(100, len(EP)), replace=False))]
    pd_ = 0; pn = 0
    for r in sp.itertuples(index=False):
        i = WM.ix.get(r.sid)
        if i is None:
            continue
        e = int(r.T) - nE + 1
        if not np.isfinite(WM.O[i, e]):
            continue
        for cell in CELLS:
            xk, x = getattr(r, f"{cell}_xk"), int(getattr(r, f"{cell}_x"))
            xw = x - nE if x >= 0 else -1
            if xw < 0 or xw >= WM.n:
                exp = WM.C[i, -1] / WM.O[i, e] - 1
            elif xk == "close":
                exp = WM.C[i, xw] / WM.O[i, e] - 1
            else:
                y = xw
                while y < WM.n and not (WM.BAR[i, y] and np.isfinite(WM.O[i, y])):
                    y += 1
                exp = (WM.O[i, y] if y < WM.n else WM.C[i, -1]) / WM.O[i, e] - 1
            rw = pd.DataFrame([(i, e, xk, xw if 0 <= xw < WM.n else -1, "x", np.nan)], columns=["s", "e", "xk", "x", "why", "key"])
            got = float(RLU.finalize_rows(WM, rw, False)["g"].iloc[0])
            pn += 1
            if abs(got - exp) > 1e-12:
                pd_ += 1
    out["組合層抽樣（出場價→報酬，0.585% 版前）"] = {"筆": pn, "不同": pd_}
    tot = sum(nd.values()) + diff + pd_
    out["合計不同"] = tot
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[check] 完｜合計不同 {tot}｜{json.dumps(nd, ensure_ascii=False)}")


# ═════════════ 網頁 ═════════════
def page(outdir):
    import html as _h
    S = json.load(open(os.path.join(outdir, "summary.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(outdir, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(outdir, "check.json")) else {}
    e = _h.escape
    ok = lambda x: isinstance(x, (int, float)) and np.isfinite(x)
    p = lambda x, d=1: f"{x * 100:+.{d}f}%" if ok(x) else "—"
    pp = lambda x, d=1: f"{x * 100:.{d}f}%" if ok(x) else "—"
    f1 = lambda x, d=1: f"{x:.{d}f}" if ok(x) else "—"
    V = S["判定"]; ch = V["挑中格"]; ot = [c for c in CELLS if c != ch][0]
    G = {(r["格"], r["版本"]): r for r in S["格"]}
    Z = S["meta"]["0050"]; EY = S["早年"]; EV = S["事件層"]["H20"]; DJ = S["退化"]
    cb, cr = G[(ch, "b")], G[(ch, "r")]
    eb_, er_ = EY["格"][f"{ch}|b"], EY["格"][f"{ch}|r"]
    H = []
    H.append(f"<h1>碰撞回落底部（BARR 底）seq2：報酬結果</h1><p class=m>登錄 sha {e(S['sha'] if 'sha' in S else S['meta']['sha'])}｜run 讀法寫死 {e(S['meta']['run 讀法寫死'])}｜"
             f"產出 {e(S['meta']['run'])}｜回測線計算子代理｜程式 backtest/researchBARR.py run｜{e(S['meta']['N'])}</p>")
    H.append("<div class=box><h2>結論</h2><ul>")
    H.append(f"<li><b>單筆（事件層 H20）：{e(EV['判定'])}。</b>買進後 20 個交易日、扣掉同一天全市場平均之後，平均 {p(EV['mean'], 2)}"
             f"（95% 信賴區間 {p(EV['lo'], 2)}～{p(EV['hi'], 2)}；{EV['n']} 筆、{EV['months']} 個月）。門檻是平均要大於一趟來回成本 0.585% 且區間不含 0。"
             f"隨機挑日子的假訊號 30 次中有 {EV['假訊號 x／30']} 次也過關{'（≥ 15 次 ⇒ 這一格的過關不構成證據）' if EV['這一格的過關不構成證據'] else ''}。</li>")
    H.append(f"<li><b>組合（10 檔、扣 0.585%）：挑中 {e(CN[ch])}，判定「{e(str(V['判定']))}」</b>（確認段、早年段取較嚴）。"
             f"探索段 年化 {p(cb['探索_年化'])}／回落 {p(cb['探索_回落'])}（{e(cb['探索_標籤'])}）；確認段 {p(cb['確認_年化'])}／{p(cb['確認_回落'])}（{e(cb['確認_標籤'])}）；"
             f"早年段 {p(eb_['早年_年化'])}／{p(eb_['早年_回落'])}（{e(eb_['早年_標籤'])}）。同段 0050：探索 {p(Z['探索']['cagr'])}／{p(Z['探索']['mdd'])}、"
             f"確認 {p(Z['確認']['cagr'])}／{p(Z['確認']['mdd'])}、早年 {p(EY['0050']['cagr'])}／{p(EY['0050']['mdd'])}。</li>")
    H.append(f"<li>現實版（多算滑價、衝擊、漲停買不到）：探索 {e(V['現實版探索'])}、確認 {e(V['現實版確認'])}、早年 {e(V['現實版早年'])} ⇒ {e(str(V['現實版判定']))}。</li>")
    H.append("<li>本件導入段平均比原文長（47.5 交易日）；頻率每檔每年 0.72 次；原文平均 35 個日曆天。</li>")
    H.append("<li>沒有人在登錄前看過台股報酬 ⇒ 不是事後重切。⛔ 這不是買賣建議。</li></ul></div>")
    # 事件層
    H.append("<h2>一、單筆（事件層）</h2><table><tr><th>臂</th><th>筆</th><th>月</th><th>平均（扣同日母體）</th><th>95% CI（月分群）</th><th>中位</th><th>勝率</th><th>判讀</th></tr>")
    H.append(f"<tr><th>主臂 H20 ★</th><td>{EV['n']}</td><td>{EV['months']}</td><td>{p(EV['mean'], 2)}</td><td>{p(EV['lo'], 2)}～{p(EV['hi'], 2)}</td><td>{p(EV['median'], 2)}</td>"
             f"<td>{pp(EV['win'])}</td><td>{e(EV['判定'])}</td></tr>")
    for k, v in S["事件層"]["描述"].items():
        if v.get("n"):
            H.append(f"<tr><th>{e(k)}（描述）</th><td>{v['n']}</td><td>{v['months']}</td><td>{p(v['mean'], 2)}</td><td>{p(v['lo'], 2)}～{p(v['hi'], 2)}</td><td>{p(v['median'], 2)}</td><td>{pp(v['win'])}</td><td>不判</td></tr>")
    H.append("</table>")
    zc = EV["零四條件"]
    H.append(f"<p class=m>「零」四條件：" + "、".join(f"{e(k)} {'✔' if v else '✖'}" for k, v in zc.items()) +
             f"｜假訊號組 CI 半寬（30 次中位）{pp(EV['假訊號半寬中位'], 2)}｜剔除：" + "、".join(f"{e(k)} {v}" for k, v in EV["剔除"].items()) + "</p>")
    # 組合層
    H.append("<h2>二、組合（10 檔）</h2><table><tr><th>臂</th><th>探索 2017-03～2021-12</th><th>確認 2022-01～2026-08</th><th>早年 2005～2014</th></tr>")
    cell = lambda r, s: f"{p(r[f'{s}_年化'])}／{p(r[f'{s}_回落'])}<br><span class=m>{e(str(r[f'{s}_標籤']))}</span>"
    for c in (ch, ot):
        for v, nm_ in (("b", "0.585% 版"), ("r", "現實版")):
            r_ = G[(c, v)]; re_ = EY["格"][f"{c}|{v}"]
            H.append(f"<tr><th>{e(CN[c])} {nm_}{' ★' if (c == ch and v == 'b') else ''}</th><td>{cell(r_, '探索')}</td><td>{cell(r_, '確認')}</td><td>{cell(re_, '早年')}</td></tr>")
    H.append(f"<tr><th>0050</th><td>{p(Z['探索']['cagr'])}／{p(Z['探索']['mdd'])}</td><td>{p(Z['確認']['cagr'])}／{p(Z['確認']['mdd'])}</td><td>{p(EY['0050']['cagr'])}／{p(EY['0050']['mdd'])}</td></tr>")
    for nm_, r_ in S["營量營飆"].items():
        if isinstance(r_, dict) and "探索" in r_:
            H.append(f"<tr><th>{e(nm_)}</th><td>{p(r_['探索']['年化'])}／{p(r_['探索']['回落'])}</td><td>{p(r_['確認']['年化'])}／{p(r_['確認']['回落'])}</td><td>—</td></tr>")
    FK = S["假訊號"]
    H.append(f"<tr><th>假訊號臂（同進場數、同持有天數分佈、隨機 R1 股；200 抽中位）</th><td>{p(FK['探索']['年化中位'])}／{p(FK['探索']['回落中位'])}<br><span class=m>p {f1(FK['探索']['p（假訊號年化 ≥ 挑中格）'], 3)}</span></td>"
             f"<td>{p(FK['確認']['年化中位'])}／{p(FK['確認']['回落中位'])}<br><span class=m>p {f1(FK['確認']['p（假訊號年化 ≥ 挑中格）'], 3)}</span></td><td>—</td></tr></table>")
    H.append("<p class=m>判準：年化中位贏 0050 且「年化 ÷ 回落」不輸 0050 ⇒ 合格；只贏年化 ⇒ 另列。200 顆抽籤種子取中位。</p>")
    # 退化
    H.append("<h2>三、退化檢查（先寫死才算報酬）</h2><table><tr><th>格</th><th>探索 平均持股／現金</th><th>確認</th><th>早年</th></tr>")
    for k, v in DJ["持股與現金"].items():
        ve = DJ["早年"]["持股與現金"].get(k, {})
        H.append(f"<tr><th>{e(k)}</th><td>{f1(v['探索_平均持股'], 2)} 檔／{pp(v['探索_平均現金'])}{' ⚠退化' if v['探索_退化'] else ''}</td>"
                 f"<td>{f1(v['確認_平均持股'], 2)} 檔／{pp(v['確認_平均現金'])}{' ⚠退化' if v['確認_退化'] else ''}</td>"
                 f"<td>{f1(ve.get('早年_平均持股'), 2)} 檔／{pp(ve.get('早年_平均現金'))}{' ⚠退化' if ve.get('早年_退化') else ''}</td></tr>")
    H.append(f"</table><p class=m>degeneracy.json 寫入：{e(DJ['寫入時間'])}；早年補寫 {e(DJ['早年']['寫入時間'])}｜照登錄排除的格：{e('、'.join(DJ['排除的格（探索段退化）']) or '無')}</p>")
    # 必報
    TS = S["逐筆"]["b"]; NE = S["等效獨立"]; CP = S["吃到起漲→頂"][ch]
    H.append("<h2>四、必報（挑中格 0.585% 版、主窗）</h2><ul>")
    H.append("<li>等效獨立檔數：" + "；".join(f"{e(k)} 平均持股 {f1(v['平均持股'])}、平均相關 {f1(v['平均ρ'], 2)} ⇒ 約 {f1(v['平均N_eff'])} 檔" for k, v in NE.items()) + "</li>")
    hd = TS["持有天數（交易日，已出場，種子合計）"]
    H.append(f"<li>持有天數（已出場）：中位 {f1(hd.get('中位'), 0)}、p10～p90 {f1(hd.get('p10'), 0)}～{f1(hd.get('p90'), 0)} 個交易日；窗尾仍持有（種子中位）{f1(TS['窗尾仍持有（檔，種子中位）'])} 檔</li>")
    H.append("<li>出場原因（每顆平均筆）：" + "、".join(f"{e(k)} {f1(v)}" for k, v in TS["出場原因（每顆平均）"].items()) + "</li>")
    H.append(f"<li>一年內先跌 15%：{pp(TS['一年內先跌15%比例'])}（{TS['觀察窗滿250筆']} 筆）；吃到「起漲→頂」幾成：中位 {pp(CP['吃到起漲→頂幾成'].get('中位'))}"
             f"（{CP['吃到起漲→頂幾成'].get('n', 0)} 筆）；買價基準中位 {pp(CP['吃到（買價基準）'].get('中位'))}</li>")
    H.append(f"<li>現金比例（探索／確認，種子中位）：{pp(DJ['持股與現金'][f'{ch}|b']['探索_平均現金'])}／{pp(DJ['持股與現金'][f'{ch}|b']['確認_平均現金'])}</li>")
    ov = S["重疊"]
    H.append("<li>與營量 v1、營飆 v1 持股重疊（主窗、r0）：" + "、".join(f"{e(k)} {pp(v)}" for k, v in ov["主窗"].items()) + "</li>")
    TO = S["逐筆（另一格）"][ot]; hdo = TO["持有天數（交易日，已出場，種子合計）"]; tho = TO["窗尾仍持有已持有天數"]
    H.append(f"<li>另一格 {e(CN[ot])}：已出場持有中位 {f1(hdo.get('中位'), 0)} 個交易日；窗尾仍持有 {f1(TO['窗尾仍持有（檔，種子中位）'])} 檔、已抱中位 {f1(tho.get('中位'), 0)} 個交易日；"
             "出場原因（每顆平均筆）：" + "、".join(f"{e(k)} {f1(v)}" for k, v in TO["出場原因（每顆平均）"].items()) + "</li></ul>")
    # 描述
    H.append("<h2>五、描述（不判、不計 N；各 50 顆）</h2><table><tr><th>臂</th><th>探索</th><th>確認</th></tr>")
    for k, r_ in S["描述"].items():
        H.append(f"<tr><th>{e(k)}</th><td>{p(r_['探索_年化'])}／{p(r_['探索_回落'])}</td><td>{p(r_['確認_年化'])}／{p(r_['確認_回落'])}</td></tr>")
    H.append("</table><p class=m>0050 濾網的角色：擋長空頭、不是急跌保護。固定天數只描述，不當出場對照。</p>")
    # 方法
    hb = S["meta"]["硬斷點"]
    H.append("<h2>六、做法與偏離</h2><ul>")
    H.append(f"<li>硬斷點：{e(hb['用哪一套'])}。3073 2021-02-19：{e(json.dumps(hb['3073'], ensure_ascii=False))}。</li>")
    fr = S["事件計數"]["freq 原規則重跑"]
    H.append(f"<li>用 freq 原規則重跑 {fr['全期筆數']} 筆，與已交的頻率檔逐筆相同：{'是' if fr['＝ events_freq.csv.gz'] else '否'}；改用正式引擎壞根後事件："
             + "、".join(f"{e(k)} {v}" for k, v in S["事件計數"]["主"].items()) + "。</li>")
    H.append("<li>原文要算術刻度；本件距離一律換成 ATR 倍數或比例（偏離）。角度、量能「偏高」不能機器化，照標不用。B→T ≤ 120 日是本線自訂候選、原文無此數字；H1～H2 無收盤在線上是本線操作化選擇。</li>")
    H.append("<li>執行者補讀法（freq 已寫死）：H2 之後、碰撞前已有收盤站上線 ⇒ 該線作廢；T ≥ H2＋5。run 補讀法：持有期遇壞根 ⇒ 壞根前一根收盤強制出（程式檔頭 R6）。</li>")
    if ck:
        H.append(f"<li>獨立寫法抽樣查核（--check）：合計不同 {ck.get('合計不同')}｜{e(json.dumps(ck.get('抽樣不同', {}), ensure_ascii=False))}｜壞根對 load_bars {e(json.dumps(ck.get('壞根 vs research11.load_bars', {}), ensure_ascii=False))}</li>")
    H.append("</ul>")
    css = """:root{--bg:#fff;--fg:#1d1d1f;--m:#666;--bd:#ddd;--box:#f4f7fb}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#16181c;--fg:#e8e8ea;--m:#9aa;--bd:#333;--box:#1f252d}}
:root[data-theme="dark"]{--bg:#16181c;--fg:#e8e8ea;--m:#9aa;--bd:#333;--box:#1f252d}
body{background:var(--bg);color:var(--fg);font-family:system-ui,"Noto Sans TC",sans-serif;max-width:980px;margin:0 auto;padding:16px;line-height:1.6}
table{border-collapse:collapse;width:100%;display:block;overflow-x:auto;font-size:14px}th,td{border:1px solid var(--bd);padding:4px 8px;text-align:right}
th{text-align:left;font-weight:600}.m{color:var(--m);font-size:13px}.box{background:var(--box);padding:8px 16px;border-radius:8px}"""
    doc = f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>碰撞回落底部報酬</title><style>{css}</style></head><body>{''.join(H)}</body></html>"
    open(os.path.join(outdir, PAGE_NAME), "w", encoding="utf-8").write(doc)
    print("[page] ⇒", os.path.join(outdir, PAGE_NAME))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["freq", "run", "check", "page"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200); ap.add_argument("--reuse", action="store_true")
    a = ap.parse_args()
    global OUT
    if a.cmd == "freq":
        if a.smoke:
            OUT = os.path.join(WORK, "smoke")
        freq(a)
    elif a.cmd == "run":
        run(a)
    elif a.cmd == "check":
        if a.smoke:
            OUT = os.path.join(WORK, "smoke_run")
        check(a)
    else:
        page(os.path.join(WORK, "smoke_run") if a.smoke else OUT)


if __name__ == "__main__":
    main()
