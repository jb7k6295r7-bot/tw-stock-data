# -*- coding: utf-8 -*-
"""Ultimate Oscillator 底背離 seq1【頻率表】（台股策略線 單筆層登錄 sha 5982a1082147efef，2026-10-17 21:09；裁定 seq364「試試看」、
seq365 發號；N_前段 ＋1）——回測線計算子代理。
⛔ 只數事件日期與個數、剔除計數、n_eff、曝險股日；⛔ 不讀、不算、不存任何 T＋1 開盤以後的價格或報酬，⛔ 不算持有天數（要碰出場後價格）。
⛔ 不 commit、不改既有程式與結果夾；research11／researchAscTri_freq／stop_fractal／patterns ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUO_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUO_freq_check
輸出 backtest/resultsUO/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格：
  A   判定格 ＝ 登錄 §二 ①②③（底背離 ＋ 背離期間 UO 低點 ＜ 30 ＋ P2 確認後 20 日內 UO 收盤 ＞ max(UO[P1..P2])）
  A_含確認日、A_新低作廢 ＝ Q5、Q6 的另一讀法（只報，⛔ 不判）
  D1_同日、D1_20日內 ＝ 描述格 D1（營量／營飆候選池內的 A 事件，Q9）；D2 ＝ 描述格 D2（UO 由 ＜30 回到 ≥30 就算，拿掉背離）
  （D3 固定抱 20／60 日、假訊號臂都要報酬 ⇒ ⛔ 不在頻率表）

═══ 讀法（Q 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝兩種讀法擇一，〔 〕內為另一讀法）═══
 Q1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（⛔ 不另寫資料層；PatC 頻率表同）：主 ＝ rerun17 快照 H2D edc6f8002f
    （2015-01-05～2026-09-24）；早年 ＝ ~/earlydata/eotc_f65bb03e11（2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl sids
    （UG.gate3 GATE_V2 開 ∩ 四碼、首碼 1～9、非 91xx、含已下市）；research11.load_bars ＜ 260 根的股票不進。
    壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、價格斷點、幽靈還原）∪ ~/crashwork/bad_*.pkl ∪ 早年 researchAddOn.early_extra_bad（reduce_v2，seq341 §六）。
    T 的母體 ＝ patterns.Frame.gate[T]（含 T 的 20 個交易日都有成交 ∧ T−20～T−1 日均量 ≥ 500 張 ＝「T 前一日 20 日均量」；
    AscTri／Dumb／MktDrop 同一條營量閘）∧ UG.pit_valid[T]（GATE_V2 開）。
 Q2 價格 ＝ load_bars 的有效 K 棒（有成交日）還原 o／h／l／c；data.load_stock 對開高低收乘同一個累積還原因子 F（登錄 §一「同一還原因子」）。
    幾何（左右 5 根、≤ 60 日、20 日內、A7／A14／A28）一律在【該股有效 K 棒序列】上數（PatAll A1、PREREGM M1 同）；T＋1 用交易日曆。
 Q3 UO（登錄 §一 逐字）：BP[k] ＝ c[k] − min(l[k], c[k−1])；TR[k] ＝ max(h[k], c[k−1]) − min(l[k], c[k−1])；
    A_n[k] ＝ Σ_{j=k−n+1..k} BP ÷ Σ TR（n ＝ 7、14、28）；UO ＝ 100 ×（4·A7 ＋ 2·A14 ＋ A28）÷ 7。
    不跨壞根：壞 K 棒 k（與前一根之間斷開）的 BP、TR 設缺值（前收不可用），第 0 根亦同 ⇒ rolling(min_periods ＝ n) 讓缺值傳染
    ⇒ UO[k] 有值 ⇔ [k−27, k] 內沒有壞 K 棒。ΣTR ＝ 0（28 根全一字且無跳空）⇒ 缺值。
 Q4 收盤轉折低點 ＝ stop_fractal.swing_lows(還原收盤, 5)（PREREG型態全量「乙」R＝5 嚴格，patterns_all.detect_lines 用的同一支；
    嚴格低於左右各 5 根）；第 s 根在 s＋5 收盤才確認（conf ＝ s＋5）。不跨壞根：[s−4, s＋5] 內有壞 K 棒的轉折作廢（比較跨斷點的收盤無意義）。
    「相鄰」＝ 有效轉折低點序列中緊鄰的兩個（P1 ＝ P2 之前最近的有效轉折低點）。
 Q5 ★ 突破窗 ＝ conf＋1 … conf＋20（「確認之後 20 個交易日內」；確認當天不算）〔另一讀法 A_含確認日：conf … conf＋20〕；
    T ＝ 窗內第一根 UO[t] ＞ max(UO[P1..P2]) 的 K 棒（登錄寫「收盤 ＞」⇒ 不要求前一日 ≤，即便 P2～conf 之間 UO 已在其上）；
    窗內碰到 UO 缺值（壞 K 棒或資料尾）⇒ 該組結束、無事件。①② 需 UO[P1..P2] 全部有值（⇒ [P1−27, P2] 無壞 K 棒）。
    ①：P2 − P1 ≤ 60（有效 K 棒差）、c[P2] ＜ c[P1]、UO[P2] ＞ UO[P1]；②：min(UO[P1..P2]) ＜ 30（含頭尾）。
 Q6 ★ 等突破期間又確認新的轉折低點 ⇒ 不影響（登錄只寫 20 日時限）〔另一讀法 A_新低作廢：新轉折 P3 在 conf3 ＝ P3＋5 ＜ t 時確認 ⇒
    舊組結束（PatAll B3 ②：同一根先用舊組判、再加新轉折）〕。
 Q7 同一檔同一個 T 由多組 (P1, P2) 產生 ⇒ 只算一筆（P2 取最早）。「同一檔持有中不重複進場」要出場日（UO ＞ 70、或過 50 後跌破 45）
    ⇒ 頻率表 ⛔ 不套；本表事件數 ＝「不套持有限制」的上限，正式跑套持有限制後會略減（另報同檔前後事件間隔 ≤ 20 根的筆數供參考）。
 Q8 剔除（每筆只記第一個原因）：閘外（500 張／pit_valid）→ 壞根（T＋1 那根是壞 K 棒）→ T＋1 無成交（下一根有效 K 棒不是日曆 T＋1、
    或無成交、或開盤缺值）→ T＋1 開盤鎖漲停（快取 upl）。（[P1−27, T] 無壞 K 棒已由 Q3、Q5 保證。）保留 ＝ 事件數。
    ⛔ 不查 T＋1 以後的硬斷點（要出場日，正式跑再做）。
 Q9 D1 營量／營飆候選池 ＝ ~/addonwork/world_{主,早年}.pkl 的 SIG[False]（營量 v1 訊號表 ＝ 營量營飆加碼件 U1 用的同一份；營飆 v1 ＝ SIG[True] 是其子集，
    聯集 ＝ SIG[False]），⛔ 只取 sid、pos（訊號日）兩欄，其他欄（含報酬）⛔ 不讀。
    ★ D1_同日 ＝ A 保留事件中 T ＝ 該股某個營量／營飆訊號日〔另一讀法 D1_20日內：T − 19 ≤ 訊號日 ≤ T（日曆位置）〕；營飆子集另欄。
    ⚠ 只含「已達成」訊號；MktDrop F 的「即將達成」沒有既有逐日表 ⇒ 未含（待辦）。訊號表只涵蓋 主 2017-02～2026-09、早年 2005～2014 的引擎窗。
 Q10 D2 ＝ UO[k−1] ＜ 30 ∧ UO[k] ≥ 30（兩者有值 ⇒ 不跨壞根）⇒ T ＝ k；同一套 Q8 剔除。
 Q11 段（登錄 §三）：探索 [2017-03-02, 2021-12-30]｜確認 [2022-01-03, 資料尾前一日]｜早年 [2005 第一個交易日, 2014-12-31]（T 的日曆位置；T＋1 需在日曆內）。
    n_eff ＝ min(保留數, 有保留事件的曆月數)；n_eff ＜ 30 ⇒ 標「依構造不可判定、不計 N」（登錄 §三）。判定以探索、確認各自報（⭐ 登錄沒指定單一判定窗 ⇒
    另報「主全窗」＝ 探索＋確認 2017-03-02～資料尾）。
    每年事件數 ＝ 保留數 ÷ 段長（年 ＝ 日曆天 ÷ 365.25）；每檔每年次數 ＝ 保留數 ÷（母體股日 ÷ 段內每年交易日數），
    母體股日 ＝ 段內 Frame.gate ∧ pit_valid ∧ 有成交 的 (股, 日) 數（＝ 平均每一檔「在母體內的一年」出幾次）；另報 保留數 ÷ 相異檔數 ÷ 段長。
"""
from __future__ import annotations

import argparse
import glob
import gzip
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
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402  Frame.gate（500 張閘）
from backtest import stop_fractal as SF                     # noqa: E402  swing_lows（轉折乙 R＝5）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = "5982a1082147efef"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsUO/freq"
PIV_R = 5          # 登錄 §二：左右各 5 根
GAP_MAX = 60       # P2 − P1 ≤ 60
BRK_WIN = 20       # 確認後 20 日內
UO_LOW = 30.0
NEFF_MIN = 30
D1_WIN = 20
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None), "主全窗": ("2017-03-02", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CELLS = {"A": "判定格：底背離＋UO低點<30＋確認後20日內突破背離期間UO高點",
         "A_含確認日": "另一讀法：突破窗含確認當天（只報）",
         "A_新低作廢": "另一讀法：等突破期間確認新轉折低點即作廢（只報）",
         "D1_同日": "描述D1：A 且 T＝營量/營飆訊號日",
         "D1_20日內": "描述D1另一讀法：A 且 T−19≤營量/營飆訊號日≤T",
         "D2": "描述D2：UO 由<30 回到≥30 就算（不要背離）"}
ST = ["保留", "閘外(500張/pit)", "壞根(T+1)", "T+1無成交", "T+1開盤鎖漲停"]
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


# ═════════════ Q3 UO ═════════════
def uo(h, l, c, bad):
    """有效 K 棒序列上的 UO；bad[k] ＝ 第 k 根與前一根斷開 ⇒ 第 k 根 BP／TR 缺值（不跨壞根）。"""
    n = len(c)
    pc = np.full(n, np.nan); pc[1:] = c[:-1]
    lo = np.minimum(l, pc); hi = np.maximum(h, pc)
    bp = c - lo; tr = hi - lo
    brk = np.asarray(bad, bool).copy(); brk[0] = True
    bp[brk] = np.nan; tr[brk] = np.nan
    A = {}
    for w in (7, 14, 28):
        sb = pd.Series(bp).rolling(w, min_periods=w).sum().to_numpy(float)
        st = pd.Series(tr).rolling(w, min_periods=w).sum().to_numpy(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            A[w] = np.where(st > 0, sb / st, np.nan)
    return 100.0 * (4 * A[7] + 2 * A[14] + A[28]) / 7.0


# ═════════════ Q4 轉折低點 ═════════════
def pivots(c, bad, R_=PIV_R):
    sw = SF.swing_lows(np.asarray(c, float), R_)
    CB = np.r_[0, np.cumsum(np.asarray(bad, bool))]
    out = []
    for s in np.flatnonzero(sw):
        a_, b_ = s - R_ + 1, s + R_
        if CB[b_ + 1] - CB[max(a_, 0)] == 0:
            out.append(int(s))
    return out


# ═════════════ Q5、Q6 事件 ═════════════
def detect(c, U, piv, R_=PIV_R, incl_conf=False, cancel_new=False):
    """回 [(T, P1, P2, conf)]（有效 K 棒序號）。⛔ 判 t 只用 ≤ t 的資料（P2 在 conf ＝ P2＋R 收盤確認、conf ＜ t 或 ＝ t 於含確認日讀法）。"""
    n = len(c); out = []
    for q in range(1, len(piv)):
        p1, p2 = piv[q - 1], piv[q]
        if p2 - p1 > GAP_MAX:
            continue
        if not (c[p2] < c[p1]):
            continue
        seg = U[p1:p2 + 1]
        if not np.isfinite(seg).all():
            continue
        if not (U[p2] > U[p1]):
            continue
        if not (seg.min() < UO_LOW):
            continue
        M = seg.max(); conf = p2 + R_
        nxt_conf = (piv[q + 1] + R_) if q + 1 < len(piv) else None
        t0 = conf if incl_conf else conf + 1
        for t in range(t0, min(conf + BRK_WIN, n - 1) + 1):
            if cancel_new and nxt_conf is not None and nxt_conf < t:
                break
            if not np.isfinite(U[t]):
                break
            if U[t] > M:
                out.append((t, p1, p2, conf)); break
        # 中間 [P2, conf) 的 UO 也要有值（不跨壞根）：t ≥ conf 時 U[t] 有值 ⇒ [t−27, t] 無壞根 ⇒ 已涵蓋 [P2, conf]
    return out


def detect_d2(U):
    k = np.arange(1, len(U))
    ok = np.isfinite(U[k - 1]) & np.isfinite(U[k]) & (U[k - 1] < UO_LOW) & (U[k] >= UO_LOW)
    return [int(x) for x in k[ok]]


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
    h, l, c = (np.asarray(B[k], float) for k in ("h", "l", "c"))
    if not (np.isfinite(c).all() and np.isfinite(h).all() and np.isfinite(l).all()):
        raise SystemExit(f"⛔ {wn} {sid} 有效 K 棒 OHLC 有缺值")
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    U = uo(h, l, c, bad)
    piv = pivots(c, bad)
    f = P.Frame(df, set())
    gate = np.asarray(f.gate, bool)
    PV = W["PV"][i]; TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]
    elig = gate & PV[:n0] & np.asarray(df["traded"].to_numpy(), bool)

    def status(k):
        T = int(idx[k]); e = T + 1
        if not (gate[T] and PV[T]):
            return "閘外(500張/pit)"
        if k + 1 < nb and bad[k + 1]:
            return "壞根(T+1)"
        if not (k + 1 < nb and idx[k + 1] == e and e < n0 and TRD[e] and np.isfinite(O[e]) and O[e] > 0):
            return "T+1無成交"
        if UPL[e]:
            return "T+1開盤鎖漲停"
        return "保留"

    EV = {}
    for cell, kw in (("A", {}), ("A_含確認日", {"incl_conf": True}), ("A_新低作廢", {"cancel_new": True})):
        d = {}
        for (t, p1, p2, cf) in detect(c, U, piv, **kw):
            if t not in d or p2 < d[t][1]:
                d[t] = (p1, p2, cf)
        EV[cell] = [{"sid": sid, "T": int(idx[t]), "k": int(t), "P1": int(idx[p1]), "P2": int(idx[p2]), "conf": int(idx[cf]),
                     "uoP1": float(U[p1]), "uoP2": float(U[p2]), "uoMin": float(np.min(U[p1:p2 + 1])), "uoMax": float(np.max(U[p1:p2 + 1])),
                     "uoT": float(U[t]), "st": status(t)} for t, (p1, p2, cf) in sorted(d.items())]
    EV["D2"] = [{"sid": sid, "T": int(idx[t]), "k": int(t), "uoT": float(U[t]), "uoPrev": float(U[t - 1]), "st": status(t)} for t in detect_d2(U)]
    sg = W["SIGPOS"].get(sid, np.array([], np.int64)); sgF = W["SIGPOS_YF"].get(sid, np.array([], np.int64))
    for e in EV["A"]:
        T = e["T"]
        e["D1_同日"] = bool(np.isin(T, sg)); e["D1_同日_營飆"] = bool(np.isin(T, sgF))
        e["D1_20日內"] = bool(((sg >= T - D1_WIN + 1) & (sg <= T)).any())
        e["D1_20日內_營飆"] = bool(((sgF >= T - D1_WIN + 1) & (sgF <= T)).any())
    EV["D1_同日"] = [e for e in EV["A"] if e["D1_同日"]]
    EV["D1_20日內"] = [e for e in EV["A"] if e["D1_20日內"]]
    expo = {sgn: int(elig[p0:p1 + 1].sum()) for sgn, (p0, p1) in W["win"].items()}
    return sid, {"ev": EV, "expo": expo, "npiv": len(piv), "nuo": int(np.isfinite(U).sum()), "nb": nb}


def load_sig(wn, cal):
    Wa = pickle.load(open(os.path.expanduser(f"~/addonwork/world_{wn}.pkl"), "rb"))
    if not (len(Wa["cal"]) == len(cal) and (Wa["cal"] == cal).all()):
        raise SystemExit(f"⛔ {wn} addonwork 日曆 ≠ 版面日曆")
    out = {}
    for G in (False, True):
        s = Wa["SIG"][G][["sid", "pos"]].copy()          # ⛔ 只取 sid、pos
        out[G] = {k: np.sort(g["pos"].to_numpy(np.int64)) for k, g in s.groupby("sid")}
    cover = (str(cal[int(Wa["w0"])].date()), str(cal[int(Wa["w1"])].date()))
    n = (int(sum(len(v) for v in out[False].values())), int(sum(len(v) for v in out[True].values())))
    del Wa
    return out[False], out[True], cover, n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = OUT if a.limit is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "UO 底背離 seq1 頻率表（⛔ 未讀、未算任何報酬或持有天數）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
         "裁定": "seq364 試試看、seq365 發號；N_前段 ＋1；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N", "世界": {}, "格": CELLS}
    FREQ = []; YR = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x, y) in SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x)))
            p1 = n0 - 2 if y is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["SIGPOS"], W["SIGPOS_YF"], cover, nsig = load_sig(wn, cal)
        _G[wn] = W
        log(f"[{wn}] 營量/營飆訊號表 涵蓋 {cover}｜營量 {nsig[0]} 筆、營飆 {nsig[1]} 筆｜段 " +
            "｜".join(f"{k} {cal[p].date()}～{cal[q].date()}" for k, (p, q) in win.items()))
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        res = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                res[sid] = r
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        ok = {s: r for s, r in res.items() if r is not None}
        n_skip = len(res) - len(ok)
        log(f"[{wn}] 逐股完｜load_bars 不足 260 根 {n_skip} 檔｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "閘": W["gate"], "壞根": W["bad_info"],
              "檔數": len(sids), "load_bars不足260根檔數": n_skip, "營量營飆訊號表": {"涵蓋": cover, "營量筆數": nsig[0], "營飆筆數": nsig[1]},
              "段": {}}
        ym = np.array([d.strftime("%Y-%m") for d in cal])
        allrows = []
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            tdy = (p1 - p0 + 1) / yrs
            expo = int(sum(r["expo"][sg] for r in ok.values()))
            segj = {"期間": f"{cal[p0].date()}～{cal[p1].date()}", "年": round(yrs, 3), "母體股日": expo}
            for cell in CELLS:
                rows = [e for r in ok.values() for e in r["ev"][cell] if p0 <= e["T"] <= p1]
                kept = [e for e in rows if e["st"] == "保留"]
                acc = {s_: sum(1 for e in rows if e["st"] == s_) for s_ in ST}
                months = len({ym[e["T"]] for e in kept}); ne = min(len(kept), months)
                nsid = len({e["sid"] for e in kept})
                # 同檔前後保留事件間隔 ≤ 20 根（持有限制會吃掉的上限參考；⛔ 不是出場日）
                close20 = 0
                bys = {}
                for e in sorted(kept, key=lambda x: (x["sid"], x["k"])):
                    bys.setdefault(e["sid"], []).append(e["k"])
                for ks in bys.values():
                    close20 += int(sum(1 for u, v in zip(ks[:-1], ks[1:]) if v - u <= 20))
                j = {"偵測(段內)": len(rows), **acc, "事件數(保留)": len(kept), "相異檔數": nsid, "有事件曆月": months, "n_eff": ne,
                     "n_eff<30": bool(ne < NEFF_MIN), "判斷": "依構造不可判定、不計 N" if ne < NEFF_MIN else "可判（n_eff ≥ 30）",
                     "每年事件數": round(len(kept) / yrs, 2) if yrs > 0 else None,
                     "每檔每年次數(母體股年)": round(len(kept) / (expo / tdy), 4) if expo else None,
                     "每檔每年次數(有事件檔)": round(len(kept) / nsid / yrs, 3) if nsid else None,
                     "同檔前後間隔≤20根筆數": close20,
                     "逐年保留": {int(y): int(v) for y, v in sorted(pd.Series([cal[e["T"]].year for e in kept]).value_counts().items())} if kept else {}}
                if cell == "A":
                    j["其中營飆訊號同日"] = int(sum(1 for e in kept if e["D1_同日_營飆"]))
                    j["其中營飆訊號20日內"] = int(sum(1 for e in kept if e["D1_20日內_營飆"]))
                segj[cell] = j
                row = {"世界": wn, "段": sg, "格": cell, "說明": CELLS[cell], "期間": segj["期間"],
                       **{k_: j[k_] for k_ in ("偵測(段內)", *ST[1:], "事件數(保留)", "相異檔數", "有事件曆月", "n_eff", "n_eff<30",
                                               "每年事件數", "每檔每年次數(母體股年)", "每檔每年次數(有事件檔)", "同檔前後間隔≤20根筆數")}}
                FREQ.append(row)
                for y, v in j["逐年保留"].items():
                    YR.append({"世界": wn, "段": sg, "格": cell, "年": y, "保留": v})
            Wj["段"][sg] = segj
            log(f"[{wn}/{sg}] 母體股日 {expo}｜" + "｜".join(f"{c_} n={segj[c_]['事件數(保留)']} n_eff={segj[c_]['n_eff']}" for c_ in CELLS))
        # 事件檔（⛔ 無價格、無報酬欄；UO 值只用到 ≤ T 的資料）
        for cell in ("A", "A_含確認日", "A_新低作廢", "D2"):
            rows = sorted([e for r in ok.values() for e in r["ev"][cell]], key=lambda x: (x["T"], x["sid"]))
            if not rows:
                continue
            dfo = pd.DataFrame(rows)
            for col in ("T", "P1", "P2", "conf"):
                if col in dfo:
                    dfo[col] = [str(cal[x].date()) for x in dfo[col]]
            dfo.insert(0, "格", cell)
            allrows.append(dfo)
        with gzip.open(os.path.join(out_dir, f"events_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            pd.concat(allrows, ignore_index=True).to_csv(fh, index=False)
        Wj["診斷"] = {"有效轉折低點總數": int(sum(r["npiv"] for r in ok.values())), "UO有值K棒": int(sum(r["nuo"] for r in ok.values())),
                    "有效K棒": int(sum(r["nb"] for r in ok.values()))}
        J["世界"][wn] = Wj
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(out_dir, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YR).to_csv(os.path.join(out_dir, "freq_by_year.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
