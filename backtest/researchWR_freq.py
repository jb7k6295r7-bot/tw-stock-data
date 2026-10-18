# -*- coding: utf-8 -*-
"""Williams %R 當「KD 的未平滑版」seq1【頻率表・乾跑】（台股策略線 單筆層登錄 sha 92d0b5b84554d22e，2026-10-18 11:08；裁定 seq369 §二、
seq372 發號；N_前段 ＋1）——回測線計算子代理。
⛔ 只數事件日期與個數、剔除計數、n_eff、曝險股日；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、出場日（裁定 seq366、372：乾跑）。
   用到的價格只有 ≤ T 的日（週）高低收；T＋1 只判「有沒有成交、開盤是否鎖漲停」（快取 trd／o／upl）。
⛔ 不 commit、不改既有程式與結果夾；researchAscTri_freq／researchTurtle_freq／researchWeekly／research11／patterns ⛔ 只 import。
本檔另含三件共用的頻率表驅動 run_freq()（researchBB_freq、researchDMI_freq import 使用；聚合口徑 ＝ researchTurtle_freq.main 原樣搬出）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWR_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWR_freq_check
輸出 backtest/resultsWR/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格：
  W        判定格（登錄 §二）：%R(14)[T−1] ＜ −80 ∧ %R(14)[T] ≥ −80，T＋1 開盤進場；同檔 20 個交易日內只算第一次
  K        對照格（描述、⛔ 不判）：日線 KD(9,3,3) K[T−1] ≤ D[T−1] ∧ K[T] ＞ D[T] ∧ K[T] ≤ 30；同檔 20 日內只算第一次
  W∩K_同日 W 保留事件中同檔同日也是 K 保留事件者（必報「重疊比例」）
  週_W、週_K  週線版（只描述）：%R(14 週) 由 ＜ −80 回到 ≥ −80；週 KD S1（researchWeekly 原定義）
  （H20／H60 報酬、對照十分位、假訊號臂、W − K 差都要報酬 ⇒ ⛔ 不在頻率表）

═══ 讀法（R 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 R1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（UO／海龜頻率表同）：主 ＝ rerun17 快照（2015-01-05～資料尾）；早年 ＝ ~/earlydata
    （2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl sids（UG.gate3 GATE_V2 ∩ 四碼、首碼 1～9、非 91xx、含已下市）；
    research11.load_bars ＜ 260 根的股票不進。壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、價格斷點、幽靈還原）∪ ~/crashwork/bad_*.pkl
    ∪ 早年 researchAddOn.early_extra_bad（reduce_v2，seq341 §六）。
    T 的母體 ＝ patterns.Frame.gate[T]（含 T 的 20 個交易日都有成交 ∧ T−20～T−1 日均量 ≥ 500 張 ＝ 登錄「T 前一日 20 日均量 ≥ 500 張」）∧ UG.pit_valid[T]。
 R2 價格 ＝ load_bars 有效 K 棒（有成交日）還原 o／h／l／c（同一累積還原因子）；所有「N 日」一律在【該股有效 K 棒序列】上數（停牌日不算）。
 R3 %R(14)（登錄逐字）＝（HH14 − c）÷（HH14 − LL14）× −100；★ HH14／LL14 ＝ 含當日最近 14 根的【最高價／最低價】（Williams 原作、
    StockCharts 同）〔另一讀法：最高／最低收盤——不採〕；HH14 ＝ LL14 ⇒ 缺值（無訊號）。不跨壞根：[k−13, k] 內除第一根外有壞 K 棒 ⇒ 缺值。
 R4 W：%R[k−1]、%R[k] 都有值 ∧ %R[k−1] ＜ −80（嚴格）∧ %R[k] ≥ −80 ⇒ T ＝ k（收盤判），T＋1 開盤進場。
 R5 KD(9,3,3)：直接呼叫 researchWeekly.kd（週 S1 那一支；RSV ＝ (c − 9 根最低) ÷ (9 根最高 − 9 根最低) × 100、區間 0 ⇒ 50；
    K ＝ ⅔K前 ＋ ⅓RSV、D ＝ ⅔D前 ＋ ⅓K、起始 K ＝ D ＝ 50）搬到日線。不跨壞根：★ 每個無壞 K 棒段（段首 ＝ 第 0 根或壞 K 棒）各自呼叫一次
    （段內第 8 根起有值）；★ 暖機：段內位置 ＜ KD_WARM ＝ 30 的 K 棒不產生訊號（起始 50 的權重 (⅔)^22 ＜ 1e−4；週 S1 是 52 週暖機）。
    K 訊號：K[k−1]、D[k−1] 同段有值 ∧ K[k−1] ≤ D[k−1] ∧ K[k] ＞ D[k] ∧ K[k] ≤ 30（週 S1 原式）。
 R6 ★ 20 日內只算第一次（照 PREREG型態全量頻率表 Q2 的處理順序）：先合併、再剔除——同檔同格依時間走，k 落在「上一個未被合併的偵測 k0」的
    (k0, k0＋20]（有效 K 棒序號）⇒ 合併掉（不看 k0 後來有沒有被剔除）；未被合併者再判剔除。〔另一讀法：被剔除者不開合併窗 ⇒ 並列「保留_另一順序」〕。
 R7 剔除（每筆只記第一個原因；UO Q8／海龜 T5 同一套）：閘外(500張/pit) → 壞根(T) → 壞根(T+1)（下一根是壞 K 棒）→ T+1無成交（下一根有效 K 棒
    不是日曆 T＋1、或無成交、或開盤缺值）→ T+1開盤鎖漲停（快取 upl）。保留 ＝ 事件數。
 R8 「持有中不重複」：本件登錄只寫「20 個交易日內只算第一次」，持有 H20 固定 ⇒ 與 R6 等價（H60 描述會略多重疊，正式跑再報）。
 R9 週線版（只描述；researchWeekly 甲 的週 K 慣例原樣）：週 ＝ 週一起算的日曆週（researchWeekly.weeks_of），週 K ＝ researchWeekly.weekly_bars
    （有效 K 棒的週開高低收）；週 KD ＝ researchWeekly.kd 全序列（S1 原樣、不分段）；★ 週 %R(14) ＝ 同 R3 在週 K 上算，另要求 [j−14, j] 週內
    無壞 K 棒（不跨壞根）；共同：週序列位置 ≥ 52（A1）、壞根所在週與前後各 1 週不產生訊號（W2）、同檔同訊號與上一個保留訊號週相隔 ≤ 8 週併掉（A2）。
    ★ T ＝ 該股該週最後一根有效 K 棒（母體閘用這天）；進場日 ＝ 下一個日曆週第一個交易日（W3），剔除：閘外 → T+1無成交（進場日無成交或開盤缺值）
    → T+1開盤鎖漲停。
 R10 段（登錄 §三）：探索 [2017-03-02, 2021-12-30]｜確認 [2022-01-03, 資料尾前一日]｜主全窗 ＝ 探索＋確認｜早年 [2005 第一個交易日, 2014-12-31]
    （T 的日曆位置）。n_eff ＝ min(保留數, 有保留事件的曆月數)；n_eff ＜ 30 ⇒ 標「依構造不可判定、不計 N」。
    每年事件數 ＝ 保留數 ÷ 段長（年 ＝ 日曆天 ÷ 365.25）；每檔每年次數 ＝ 保留數 ÷（母體股日 ÷ 段內每年交易日數），母體股日 ＝ 段內
    Frame.gate ∧ pit_valid ∧ 有成交 的 (股, 日) 數；另報 保留數 ÷ 相異檔數 ÷ 段長。
 R11 W 與 K 同日重疊比例（登錄 §四 必報）＝ 段內 W 保留事件中「同檔同 T 也是 K 保留事件」的筆數 ÷ W 保留數（另報 ÷ K 保留數）。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣（⛔ 只 import）
from backtest import researchWeekly as RW                   # noqa: E402  kd、weeks_of、weekly_bars 原樣（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402  Frame.gate（500 張閘）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = "92d0b5b84554d22e"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsWR/freq"
WR_N = 14
WR_TH = -80.0
KD_WARM = 30
KD_TH = 30.0
DEDUP = 20
W_WARM = 52
W_DEDUP = 8
NEFF_MIN = 30
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None), "主全窗": ("2017-03-02", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CELLS = {"W": "判定格：%R(14) 由 <−80 回到 ≥−80（收盤判、T+1 開盤進），20 日內只算第一次",
         "K": "對照格（描述）：日線 KD(9,3,3) K 上穿 D 且 K≤30，20 日內只算第一次",
         "W∩K_同日": "W 保留事件中同檔同日也是 K 保留事件",
         "週_W": "週線版（描述）：週 %R(14) 由 <−80 回到 ≥−80，8 週內併",
         "週_K": "週線版（描述）：週 KD S1（K 上穿 D 且 K≤30），8 週內併"}
ST_ALL = ["保留", "閘外(500張/pit)", "壞根(T)", "T開盤缺值", "T開盤鎖漲停", "壞根(T+1)", "T+1無成交", "T+1開盤鎖漲停", "合併掉"]
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check(sha, mailbox=MAILBOX):
    fs = [f for f in glob.glob(os.path.join(mailbox, "*.md")) if f"sha{sha}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{sha}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != sha:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}")
    return os.path.basename(fs[0])


# ═════════════ 共用：逐股基本資料、剔除 ═════════════
def base(wn, sid):
    """回 None 或 dict：B、idx、nb、bad、h/l/c/o、gate、elig、PV/TRD/O/UPL（日曆）、df。bad[k] ＝ 第 k 根與前一根斷開。"""
    W = _G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if len(df) != n0:
        raise SystemExit(f"⛔ {wn} {sid} df 長 {len(df)} ≠ 日曆 {n0}")
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    if not (np.isfinite(c).all() and np.isfinite(h).all() and np.isfinite(l).all()):
        raise SystemExit(f"⛔ {wn} {sid} 有效 K 棒 OHLC 有缺值")
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    f = P.Frame(df, set())
    gate = np.asarray(f.gate, bool)
    PV = W["PV"][i]; TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]
    elig = gate & PV[:n0] & np.asarray(df["traded"].to_numpy(), bool)
    expo = {sgn: int(elig[p0:p1 + 1].sum()) for sgn, (p0, p1) in W["win"].items()}
    return {"W": W, "B": B, "df": df, "idx": idx, "nb": nb, "bad": bad, "o": o, "h": h, "l": l, "c": c, "gate": gate,
            "PV": PV, "TRD": TRD, "O": O, "UPL": UPL, "n0": n0, "cal": cal, "expo": expo, "sid": sid}


def st_next_open(X, k):
    """收盤判、T＋1 開盤進（UO Q8／海龜 T5）。"""
    idx, nb, bad, gate, PV, TRD, O, UPL, n0 = (X[z] for z in ("idx", "nb", "bad", "gate", "PV", "TRD", "O", "UPL", "n0"))
    T = int(idx[k]); e = T + 1
    if not (gate[T] and PV[T]):
        return "閘外(500張/pit)"
    if bad[k]:
        return "壞根(T)"
    if k + 1 < nb and bad[k + 1]:
        return "壞根(T+1)"
    if not (k + 1 < nb and idx[k + 1] == e and e < n0 and TRD[e] and np.isfinite(O[e]) and O[e] > 0):
        return "T+1無成交"
    if UPL[e]:
        return "T+1開盤鎖漲停"
    return "保留"


def st_same_day(X, k):
    """盤中觸價、當日進（海龜 T4）。"""
    idx, bad, gate, PV, O, UPL = (X[z] for z in ("idx", "bad", "gate", "PV", "O", "UPL"))
    T = int(idx[k])
    if not (gate[T] and PV[T]):
        return "閘外(500張/pit)"
    if bad[k]:
        return "壞根(T)"
    if not (np.isfinite(O[T]) and O[T] > 0):
        return "T開盤缺值"
    if UPL[T]:
        return "T開盤鎖漲停"
    return "保留"


def clean_window(bad, w):
    """ok[k] ＝ [k−w+1, k] 內除第一根外沒有壞 K 棒（窗內 w 根彼此相連）∧ k ≥ w−1。"""
    n = len(bad); CB = np.r_[0, np.cumsum(np.asarray(bad, bool))]
    k = np.arange(n); lo = np.clip(k - w + 2, 0, n)
    return (k >= w - 1) & ((CB[k + 1] - CB[lo]) == 0)


def dedup_then_status(ks, status_fn, win=DEDUP):
    """R6：先合併（k ∈ (k0, k0＋win] ⇒ 合併掉）、再剔除；另回『另一順序』保留集合（被剔除者不開合併窗）。"""
    st = {}; last = -10 ** 9
    for k in ks:
        if k - last <= win:
            st[k] = "合併掉"
        else:
            st[k] = None; last = k
    alt = set(); last2 = -10 ** 9
    raw = {k: status_fn(k) for k in ks}
    for k in ks:
        if st[k] is None:
            st[k] = raw[k]
        if raw[k] == "保留" and k - last2 > win:
            alt.add(k); last2 = k
    return st, alt


# ═════════════ R3 %R、R5 KD ═════════════
def willr(h, l, c, bad, n=WR_N):
    hh = pd.Series(h).rolling(n, min_periods=n).max().to_numpy(float)
    ll = pd.Series(l).rolling(n, min_periods=n).min().to_numpy(float)
    rng = hh - ll
    with np.errstate(invalid="ignore", divide="ignore"):
        wr = np.where(rng > 0, (hh - c) / rng * -100.0, np.nan)
    wr[~clean_window(bad, n)] = np.nan
    return wr


def kd_daily(h, l, c, bad):
    """researchWeekly.kd 逐無壞 K 棒段呼叫；回 K、D、段內位置。"""
    N = len(c); K = np.full(N, np.nan); Dd = np.full(N, np.nan); pos = np.zeros(N, np.int64)
    starts = [0] + [k for k in range(1, N) if bad[k]]
    ends = starts[1:] + [N]
    for s, e in zip(starts, ends):
        k_, d_ = RW.kd(c[s:e], h[s:e], l[s:e])
        K[s:e] = k_; Dd[s:e] = d_; pos[s:e] = np.arange(e - s)
    return K, Dd, pos


def detect_w(wr):
    k = np.arange(1, len(wr))
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(wr[k - 1]) & np.isfinite(wr[k]) & (wr[k - 1] < WR_TH) & (wr[k] >= WR_TH)
    return [int(x) for x in k[ok]]


def detect_k(K, Dd, pos):
    k = np.arange(1, len(K))
    with np.errstate(invalid="ignore"):
        ok = (pos[k] >= KD_WARM) & (pos[k - 1] == pos[k] - 1) & np.isfinite(K[k - 1]) & np.isfinite(K[k]) & \
             (K[k - 1] <= Dd[k - 1]) & (K[k] > Dd[k]) & (K[k] <= KD_TH)
    return [int(x) for x in k[ok]]


# ═════════════ R9 週線 ═════════════
def weekly_signals(X):
    """回 {週_W: [...], 週_K: [...]}：每筆 T＝該週最後有效 K 棒的日曆位置、e＝下一個日曆週第一個交易日。"""
    W = X["W"]; wk, wf = W["wk"], W["wf"]; n0 = X["n0"]; df = X["df"]; idx = X["idx"]; bad = X["bad"]
    o, h, l, c = (df[z].to_numpy(float) for z in ("open", "high", "low", "close"))
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
    valid = np.asarray(df["traded"].to_numpy(), bool)
    wks, WO, WH, WL, WC, WV = RW.weekly_bars(valid, o, h, l, c, vol, wk)
    nwb = len(wks)
    out = {"週_W": [], "週_K": []}
    if nwb < W_WARM + 2:
        return out
    # 每個週 K 的最後一根有效 K 棒（日曆位置）、週內有無壞 K 棒
    wv = wk[idx]
    last_pos = np.full(nwb, -1, np.int64); badwb = np.zeros(nwb, bool)
    j = np.searchsorted(wks, wv)
    for q in range(len(idx)):
        last_pos[j[q]] = idx[q]
        if bad[q]:
            badwb[j[q]] = True
    nw = len(wf)
    badw = np.zeros(nw, bool); badw[wks[badwb]] = True
    near = badw.copy(); near[1:] |= badw[:-1]; near[:-1] |= badw[1:]
    K, Dd = RW.kd(WC, WH, WL)
    s1 = np.zeros(nwb, bool); s1[1:] = (K[:-1] <= Dd[:-1]) & (K[1:] > Dd[1:]) & (K[1:] <= 30)
    hh = pd.Series(WH).rolling(WR_N, min_periods=WR_N).max().to_numpy(float)
    ll = pd.Series(WL).rolling(WR_N, min_periods=WR_N).min().to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        wr = np.where(hh - ll > 0, (hh - WC) / (hh - ll) * -100.0, np.nan)
    CB = np.r_[0, np.cumsum(badwb)]
    q = np.arange(nwb); lo = np.clip(q - WR_N, 0, nwb)
    cleanw = (q >= WR_N) & ((CB[q + 1] - CB[lo]) == 0)                      # [j−14, j] 週內無壞 K 棒
    sW = np.zeros(nwb, bool)
    with np.errstate(invalid="ignore"):
        sW[1:] = cleanw[1:] & np.isfinite(wr[:-1]) & np.isfinite(wr[1:]) & (wr[:-1] < WR_TH) & (wr[1:] >= WR_TH)
    gate, PV, TRD, O, UPL = (X[z] for z in ("gate", "PV", "TRD", "O", "UPL"))
    for cell, S, vals in (("週_W", sW, wr), ("週_K", s1, K)):
        last = -10 ** 9
        for p in np.flatnonzero(S & (np.arange(nwb) >= W_WARM)):
            w = int(wks[p])
            if near[w]:
                continue
            if w - last <= W_DEDUP:
                continue
            last = w
            T = int(last_pos[p])
            e = int(wf[w + 1]) if w + 1 < nw else -1
            if not (gate[T] and PV[T]):
                st = "閘外(500張/pit)"
            elif not (0 <= e < n0 and TRD[e] and np.isfinite(O[e]) and O[e] > 0):
                st = "T+1無成交"
            elif UPL[e]:
                st = "T+1開盤鎖漲停"
            else:
                st = "保留"
            out[cell].append({"sid": X["sid"], "T": T, "k": int(np.searchsorted(idx, T)), "週序": int(p), "進場日位置": e,
                              "值": float(vals[p]), "st": st})
    return out


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    X = base(wn, sid)
    if X is None:
        return sid, None
    h, l, c, bad, idx = X["h"], X["l"], X["c"], X["bad"], X["idx"]
    WR = willr(h, l, c, bad)
    K, Dd, pos = kd_daily(h, l, c, bad)
    EV = {}
    for cell, ks, extra in (("W", detect_w(WR), lambda k: {"%R[T-1]": float(WR[k - 1]), "%R[T]": float(WR[k])}),
                            ("K", detect_k(K, Dd, pos), lambda k: {"K[T-1]": float(K[k - 1]), "D[T-1]": float(Dd[k - 1]),
                                                                   "K[T]": float(K[k]), "D[T]": float(Dd[k])})):
        st, alt = dedup_then_status(ks, lambda k: st_next_open(X, k))
        EV[cell] = [{"sid": sid, "T": int(idx[k]), "k": k, **extra(k), "st": st[k], "alt保留": bool(k in alt)} for k in ks]
    kK = {e["T"] for e in EV["K"] if e["st"] == "保留"}
    for e in EV["W"]:
        e["同日K"] = bool(e["T"] in kK)
    EV["W∩K_同日"] = [e for e in EV["W"] if e["同日K"]]
    EV.update(weekly_signals(X))
    return sid, {"ev": EV, "expo": X["expo"], "nb": X["nb"], "nwr": int(np.isfinite(WR).sum()), "nkd": int(np.isfinite(K).sum())}


# ═════════════ 共用驅動（researchTurtle_freq.main 的聚合原樣搬出）═════════════
def gaps(kept):
    bys = {}
    for e in sorted(kept, key=lambda x: (x["sid"], x["k"])):
        bys.setdefault(e["sid"], []).append(e["k"])
    g1 = g10 = g20 = 0
    for ks in bys.values():
        d = np.diff(np.asarray(ks))
        g1 += int((d == 1).sum()); g10 += int((d <= 10).sum()); g20 += int((d <= 20).sum())
    return g1, g10, g20


def run_freq(cfg):
    """cfg：sha、out、cells、job（模組層函式，(wn, sid) → (sid, {ev, expo, nb, ...})）、ev_cells、title、ruling、doc、
    seg_extra(ok, p0, p1, cal) → dict（選）、diag(ok) → dict（選）、st_all（選）。"""
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = cfg["out"] if a.limit is None else os.path.join(cfg["out"], "_try")
    os.makedirs(out_dir, exist_ok=True)
    LOG.clear()
    reg = reg_check(cfg["sha"])
    log(f"[登錄] {reg}（sha {cfg['sha']} 已驗）")
    stall = cfg.get("st_all", ST_ALL)
    cells = cfg["cells"]
    J = {"性質": cfg["title"], "登錄": f"台股策略線 seq1 sha {cfg['sha']}", "裁定": cfg["ruling"], "世界": {}, "格": cells}
    FREQ = []; YR = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x, y) in SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x)))
            p1 = n0 - 2 if y is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["wk"], W["wf"], W["wl"] = RW.weeks_of(cal)
        _G[wn] = W
        log(f"[{wn}] 段 " + "｜".join(f"{k} {cal[p].date()}～{cal[q].date()}" for k, (p, q) in win.items()))
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        res = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(cfg["job"], [(wn, s) for s in sids], chunksize=8)):
                res[sid] = r
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        ok = {s: r for s, r in res.items() if r is not None}
        n_skip = len(res) - len(ok)
        log(f"[{wn}] 逐股完｜load_bars 不足 260 根 {n_skip} 檔｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "閘": W["gate"], "壞根": W["bad_info"],
              "檔數": len(sids), "load_bars不足260根檔數": n_skip, "段": {}}
        ym = np.array([d.strftime("%Y-%m") for d in cal])
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            tdy = (p1 - p0 + 1) / yrs
            expo = int(sum(r["expo"][sg] for r in ok.values()))
            segj = {"期間": f"{cal[p0].date()}～{cal[p1].date()}", "年": round(yrs, 3), "母體股日": expo}
            for cell in cells:
                rows = [e for r in ok.values() for e in r["ev"].get(cell, []) if p0 <= e["T"] <= p1]
                kept = [e for e in rows if e["st"] == "保留"]
                acc = {s_: sum(1 for e in rows if e["st"] == s_) for s_ in stall[1:]}
                months = len({ym[e["T"]] for e in kept}); ne = min(len(kept), months)
                nsid = len({e["sid"] for e in kept})
                g1, g10, g20 = gaps(kept)
                j = {"偵測(段內)": len(rows), **acc, "事件數(保留)": len(kept), "相異檔數": nsid, "有事件曆月": months, "n_eff": ne,
                     "n_eff<30": bool(ne < NEFF_MIN), "判斷": "依構造不可判定、不計 N" if ne < NEFF_MIN else "可判（n_eff ≥ 30）",
                     "每年事件數": round(len(kept) / yrs, 1) if yrs > 0 else None,
                     "每檔每年次數(母體股年)": round(len(kept) / (expo / tdy), 4) if expo else None,
                     "每檔每年次數(有事件檔)": round(len(kept) / nsid / yrs, 3) if nsid else None,
                     "同檔相鄰間隔=1根": g1, "同檔相鄰間隔≤10根": g10, "同檔相鄰間隔≤20根": g20,
                     "保留_另一順序": int(sum(1 for e in rows if e.get("alt保留"))) if any("alt保留" in e for e in rows) else None,
                     "前一根非事件(連續段第一根)": int(sum(1 for e in kept if not e["前一根也是事件"])) if any("前一根也是事件" in e for e in kept) else None,
                     "逐年保留": {int(y): int(v) for y, v in sorted(pd.Series([cal[e["T"]].year for e in kept]).value_counts().items())} if kept else {}}
                segj[cell] = j
                row = {"世界": wn, "段": sg, "格": cell, "說明": cells[cell], "期間": segj["期間"],
                       **{k_: j[k_] for k_ in ("偵測(段內)", *stall[1:], "事件數(保留)", "相異檔數", "有事件曆月", "n_eff", "n_eff<30",
                                               "每年事件數", "每檔每年次數(母體股年)", "每檔每年次數(有事件檔)",
                                               "同檔相鄰間隔=1根", "同檔相鄰間隔≤10根", "同檔相鄰間隔≤20根", "保留_另一順序", "前一根非事件(連續段第一根)")}}
                FREQ.append(row)
                for y, v in j["逐年保留"].items():
                    YR.append({"世界": wn, "段": sg, "格": cell, "年": y, "保留": v})
            if cfg.get("seg_extra"):
                segj["附加"] = cfg["seg_extra"](ok, p0, p1, cal)
            Wj["段"][sg] = segj
            log(f"[{wn}/{sg}] 母體股日 {expo}｜" + "｜".join(f"{c_} n={segj[c_]['事件數(保留)']} n_eff={segj[c_]['n_eff']}" for c_ in cells)
                + (f"｜附加 {segj['附加']}" if "附加" in segj else ""))
        allrows = []
        for cell in cfg["ev_cells"]:
            rows = sorted([e for r in ok.values() for e in r["ev"].get(cell, [])], key=lambda x: (x["T"], x["sid"]))
            if not rows:
                continue
            dfo = pd.DataFrame(rows)
            for col in ("T", "c日", "進場日位置"):
                if col in dfo:
                    dfo[col] = [str(cal[x].date()) if 0 <= x < n0 else "" for x in dfo[col]]
            dfo.insert(0, "格", cell)
            allrows.append(dfo)
        with gzip.open(os.path.join(out_dir, f"events_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            pd.concat(allrows, ignore_index=True).to_csv(fh, index=False)
        Wj["診斷"] = cfg["diag"](ok) if cfg.get("diag") else {"有效K棒": int(sum(r["nb"] for r in ok.values()))}
        J["世界"][wn] = Wj
    J["讀法"] = cfg["doc"].split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(out_dir, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YR).to_csv(os.path.join(out_dir, "freq_by_year.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def seg_extra(ok, p0, p1, cal):
    w = [e for r in ok.values() for e in r["ev"]["W"] if p0 <= e["T"] <= p1 and e["st"] == "保留"]
    k = [e for r in ok.values() for e in r["ev"]["K"] if p0 <= e["T"] <= p1 and e["st"] == "保留"]
    both = sum(1 for e in w if e["同日K"])
    return {"W保留": len(w), "K保留": len(k), "同檔同日重疊": both,
            "重疊÷W": round(both / len(w), 4) if w else None, "重疊÷K": round(both / len(k), 4) if k else None}


def main():
    run_freq({"sha": REG_SHA, "out": OUT, "cells": CELLS, "job": stock_job, "ev_cells": ("W", "K", "週_W", "週_K"),
              "title": "Williams %R 對日線 KD seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
              "ruling": "seq369 §二、seq372 發號；N_前段 ＋1；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N；乾跑",
              "doc": __doc__, "seg_extra": seg_extra,
              "diag": lambda ok: {"有效K棒": int(sum(r["nb"] for r in ok.values())), "%R有值K棒": int(sum(r["nwr"] for r in ok.values())),
                                  "KD有值K棒": int(sum(r["nkd"] for r in ok.values()))}})


if __name__ == "__main__":
    main()
