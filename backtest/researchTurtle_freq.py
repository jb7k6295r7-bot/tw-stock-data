# -*- coding: utf-8 -*-
"""海龜交易法 Donchian 突破 seq2【頻率表・乾跑】（台股策略線 單筆層登錄 sha 87b39da0f38816e0，2026-10-17 22:33；裁定 seq366 發號、
seq367 發 seq2；N_前段 ＋2）——回測線計算子代理。
⛔ 只數事件日期與個數、剔除計數、n_eff、曝險股日；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、出場日（裁定 seq366：試跑一律乾跑不含報酬欄）。
   S1／S2 用到的價格只有 ≤ T 的日高（觸價判斷）；D4 只用 ≤ T 的收盤；T 當日開盤只用來判「開盤鎖漲停全日鎖死」（快取 upl）。
⛔ 不 commit、不改既有程式與結果夾；researchAscTri_freq／researchUO_freq／research11／patterns ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtle_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtle_freq_check
輸出 backtest/resultsTurtle/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格：
  S1、S2              判定格（登錄 §一：盤中最高 ＞ 前 20／55 日最高 ⇒ 當日觸價買）
  D4_S1、D4_S2        描述 D4（收盤 ＞ 前 20／55 日最高 ⇒ 隔天開盤買）
  D3_S1、D3_S2        描述 D3：S1／S2 ∧ ADX(14)[T−1] ＞ 25
  D3_D4S1、D3_D4S2    描述 D3 × D4：D4 ∧ ADX(14)[T] ＞ 25
  D5_S1_同日、D5_S2_同日、D5_S1_20日內、D5_S2_20日內   描述 D5（營量／營飆候選池內的 S1／S2）
  （D1、D2 跳過規則要看上一筆突破的「賺賠／是否回到區間」＝ 進場後價格；假訊號臂、對照組要報酬 ⇒ ⛔ 不在頻率表）

═══ 讀法（T 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 T1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（UO 頻率表 Q1 同）：主 ＝ rerun17 快照（2015-01-05～資料尾）；早年 ＝ ~/earlydata
    （2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl sids（UG.gate3 GATE_V2 ∩ 四碼、首碼 1～9、非 91xx、含已下市）；
    research11.load_bars ＜ 260 根的股票不進。壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、價格斷點、幽靈還原）∪ ~/crashwork/bad_*.pkl
    ∪ 早年 researchAddOn.early_extra_bad（reduce_v2，seq341 §六）。
    T 的母體 ＝ patterns.Frame.gate[T]（含 T 的 20 個交易日都有成交 ∧ T−20～T−1 日均量 ≥ 500 張 ＝ 登錄「T 前一日 20 日均量 ≥ 500 張」）
    ∧ UG.pit_valid[T]。★ S1／S2 的 T ＝ 突破（進場）當天；D4 的 T ＝ 收盤判定日（進場 T＋1）——兩者都用「T 前一日」的 20 日均量。
 T2 價格 ＝ load_bars 有效 K 棒（有成交日）還原 o／h／l／c（data.load_stock 開高低收乘同一累積還原因子，登錄 §一）。
    ★「前 N 日」＝ 該股有效 K 棒序列上 T 之前的 N 根（停牌日不算；UO Q2、PatAll A1 同）〔另一讀法：日曆交易日——缺口 ≥ 5 日已切壞根，
    1～4 日停牌兩讀法只差在窗口多涵蓋幾根〕。
 T3 S1（登錄 §一 逐字）：h[k] ＞ max(h[k−20..k−1])（前 20 根、不含當日；嚴格大於；等於不算）；S2 同、N ＝ 55。
    不跨壞根：bad[j] ＝ 第 j 根與 j−1 根斷開；偵測要求 [k−N+1, k−1] 內無壞 K 棒（前 N 根彼此相連）；k 本身是壞 K 棒（T 與前 N 根斷開）
    ⇒ 偵測到但剔除為「壞根(T)」。k ＜ N ⇒ 無前 N 根、不偵測。
 T4 S1／S2 剔除（每筆只記第一個原因）：閘外(500張/pit) → 壞根(T) → T開盤缺值 → T開盤鎖漲停（快取 upl ＝ 開盤＝漲停價 ∧ 原始最低＝原始開盤
    ＝ 全日鎖死；登錄「開盤即漲停且全日鎖死 ⇒ 買不到、不算事件」）。保留 ＝ 事件數。★ 開盤漲停但盤中打開（最低 ＜ 開盤）⇒ 買得到、算事件。
 T5 D4（登錄 §三 D4）：★ c[k] ＞ max(h[k−20..k−1])（收盤 ＞ 前 N 日【最高價】，與 S1 同一條通道）〔另一讀法：收盤 ＞ 前 N 日最高收盤〕；
    剔除：閘外 → 壞根(T) → 壞根(T+1)（下一根是壞 K 棒）→ T+1無成交（下一根有效 K 棒不是日曆 T＋1、或無成交、或開盤缺值）→ T+1開盤鎖漲停
    （UO 頻率表 Q8 同一套）。
 T6 ADX(14)（描述 D3）：venv（~/tw-p16/.venv）沒有 ta／pandas_ta／talib／finta／tulipy／stockstats／btalib，repo 內也沒有現成 ADX；
    ⛔ 不安裝 ⇒ ★ 自寫 Wilder 原式，公式逐字依 StockCharts ChartSchool〈Average Directional Index (ADX)〉與〈ATR〉兩頁（2026-10-17 讀）：
      up ＝ h[k] − h[k−1]；dn ＝ l[k−1] − l[k]；
      +DM1 ＝ up（若 up ＞ dn 且 up ＞ 0）否則 0；−DM1 ＝ dn（若 dn ＞ up 且 dn ＞ 0）否則 0（「較大者得、負值記 0」；★ up ＝ dn 時兩者皆 0，該頁未寫）；
      TR1 ＝ max(h[k] − l[k], |h[k] − c[k−1]|, |l[k] − c[k−1]|)；
      第一個 TR14 ＝ 前 14 個 TR1 之和；之後 TR14 ＝ 前 TR14 − 前 TR14 ÷ 14 ＋ 當日 TR1（+DM14、−DM14 同法）；
      +DI14 ＝ 100 × +DM14 ÷ TR14；−DI14 ＝ 100 × −DM14 ÷ TR14；DX ＝ 100 × |+DI14 − −DI14| ÷ (+DI14 ＋ −DI14)；
      第一個 ADX ＝ 14 個 DX 的平均；之後 ADX ＝ (前 ADX × 13 ＋ 當日 DX) ÷ 14。
    不跨壞根：★ 每個無壞 K 棒段（段首 s ＝ 第 0 根或壞 K 棒）從頭起算：TR1／DM1 從 s＋1 起（要前一根）⇒ 第一個 DX 在 s＋14、第一個 ADX 在 s＋27；
      TR14 ＝ 0 或 +DI＋−DI ＝ 0 ⇒ DX 缺值 ⇒ ★ ADX 重新起算（再收 14 個 DX）。
    ⚠ 該頁註明約 150 根才完全吸收平滑起始值 ⇒ 另報「其中段齡 ＜ 150 根」筆數（段齡 ＝ 判定根 − 段首）。
    ★ 濾網時點：S1／S2（盤中觸價）用 ADX[k−1]（T 開盤前已知）；D4（收盤判）用 ADX[k]。濾網 ＝ ADX ＞ 25（嚴格）；ADX 缺值 ⇒ 不過濾網。
    對帳：check C3 以另一份逐根迴圈獨立重寫比對 20 檔全序列（無外部現成實作可對 ⇒ 報告標明「自寫、未與第三方套件對帳」）。
 T7 「同一檔持有中不重複進場、賣後可再進」要出場日（10／20 日低點、2N 停損 ⇒ 進場後價格）⇒ 頻率表 ⛔ 不套；本表事件數 ＝ 不套持有限制的【上限】，
    正式跑套持有限制後會減少（連續創新高的每一根都算一筆）。參考（⛔ 不用出場日）：同檔相鄰兩個保留事件間隔 ＝1、≤10、≤20 根的筆數，
    以及「前一根不是同格偵測事件」的筆數（＝ 一段連續突破的第一根）。
 T8 D5 營量／營飆候選池 ＝ ~/addonwork/world_{主,早年}.pkl 的 SIG[False]（營量 v1 已達成訊號表；營飆 v1 ＝ SIG[True] 子集），⛔ 只取 sid、pos 兩欄
    （researchUO_freq.load_sig 原樣）。★ D5_同日 ＝ S 保留事件中 T ＝ 該股某個訊號日〔另一讀法 D5_20日內：T−19 ≤ 訊號日 ≤ T〕；營飆子集另欄。
    ⚠ 只含已達成訊號；訊號表只涵蓋 主 2017-02～2026-09、早年 2005～2014 引擎窗。
 T9 段（登錄 §二）：探索 [2017-03-02, 2021-12-30]｜確認 [2022-01-03, 資料尾前一日]｜主全窗 ＝ 探索＋確認｜早年 [2005 第一個交易日, 2014-12-31]
    （T 的日曆位置）。★ 所有格同用「資料尾前一日」截（D4 要 T＋1；S 格同截以便格間可比，差 1 天）。
    n_eff ＝ min(保留數, 有保留事件的曆月數)；n_eff ＜ 30 ⇒ 標「依構造不可判定、不計 N」。
    每年事件數 ＝ 保留數 ÷ 段長（年 ＝ 日曆天 ÷ 365.25）；每檔每年次數 ＝ 保留數 ÷（母體股日 ÷ 段內每年交易日數），母體股日 ＝ 段內
    Frame.gate ∧ pit_valid ∧ 有成交 的 (股, 日) 數；另報 保留數 ÷ 相異檔數 ÷ 段長。
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
from backtest import researchUO_freq as RU                  # noqa: E402  load_sig 原樣（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402  Frame.gate（500 張閘）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = "87b39da0f38816e0"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsTurtle/freq"
NS = {"S1": 20, "S2": 55}
ADX_N = 14
ADX_TH = 25.0
ADX_WARM = 150
NEFF_MIN = 30
D5_WIN = 20
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None), "主全窗": ("2017-03-02", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CELLS = {"S1": "判定格 S1：盤中最高＞前20日最高，當日觸價買",
         "S2": "判定格 S2：盤中最高＞前55日最高，當日觸價買",
         "D4_S1": "描述D4：收盤＞前20日最高，隔天開盤買",
         "D4_S2": "描述D4：收盤＞前55日最高，隔天開盤買",
         "D3_S1": "描述D3：S1 且 ADX(14)[T−1]＞25",
         "D3_S2": "描述D3：S2 且 ADX(14)[T−1]＞25",
         "D3_D4S1": "描述D3×D4：D4_S1 且 ADX(14)[T]＞25",
         "D3_D4S2": "描述D3×D4：D4_S2 且 ADX(14)[T]＞25",
         "D5_S1_同日": "描述D5：S1 且 T＝營量/營飆訊號日",
         "D5_S2_同日": "描述D5：S2 且 T＝營量/營飆訊號日",
         "D5_S1_20日內": "描述D5另一讀法：S1 且 T−19≤訊號日≤T",
         "D5_S2_20日內": "描述D5另一讀法：S2 且 T−19≤訊號日≤T"}
ST_S = ["保留", "閘外(500張/pit)", "壞根(T)", "T開盤缺值", "T開盤鎖漲停"]
ST_D = ["保留", "閘外(500張/pit)", "壞根(T)", "壞根(T+1)", "T+1無成交", "T+1開盤鎖漲停"]
ST_ALL = ["保留", "閘外(500張/pit)", "壞根(T)", "T開盤缺值", "T開盤鎖漲停", "壞根(T+1)", "T+1無成交", "T+1開盤鎖漲停"]
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


# ═════════════ T3 突破偵測 ═════════════
def prev_high(h, N):
    """prevmax[k] ＝ max(h[k−N..k−1])（k ＜ N ⇒ 缺值）。"""
    s = pd.Series(np.asarray(h, float)).rolling(N, min_periods=N).max().shift(1)
    return s.to_numpy(float)


def detect(h, c, bad, N, close_confirm=False):
    """回偵測到的 k（有效 K 棒序號）：前 N 根彼此相連（[k−N+1, k−1] 無壞 K 棒）∧ h[k]（或 D4：c[k]）＞ max(h[k−N..k−1])。
    ⛔ 判 k 只用 ≤ k 的資料。bad[k] 本身不在偵測條件內（由剔除記為 壞根(T)）。"""
    n = len(h)
    pm = prev_high(h, N)
    CB = np.r_[0, np.cumsum(np.asarray(bad, bool))]
    k = np.arange(n)
    lo = np.clip(k - N + 1, 0, n); hi = k                      # [k−N+1, k−1] ⇒ CB[k] − CB[k−N+1]
    clean = (k >= N) & ((CB[hi] - CB[lo]) == 0)
    x = np.asarray(c if close_confirm else h, float)
    with np.errstate(invalid="ignore"):
        ok = clean & np.isfinite(pm) & (x > pm)
    return np.flatnonzero(ok), pm


# ═════════════ T6 ADX（Wilder 原式；段內起算）═════════════
def adx_wilder(h, l, c, bad, n=ADX_N):
    """回 (ADX, 段齡)。段首 s ＝ 第 0 根或壞 K 棒；段內第 s＋1 根起有 TR1／DM1；第一個 DX 在 s＋n、第一個 ADX 在 s＋2n−1。"""
    h = np.asarray(h, float); l = np.asarray(l, float); c = np.asarray(c, float); N = len(c)
    brk = np.asarray(bad, bool).copy(); brk[0] = True
    A = np.full(N, np.nan); age = np.zeros(N, np.int64)
    s = 0
    trs = pdm = mdm = None; cnt = 0; acc_tr = acc_p = acc_m = 0.0
    adx = None; dxbuf = []
    for k in range(N):
        if brk[k]:
            s = k; cnt = 0; acc_tr = acc_p = acc_m = 0.0; trs = pdm = mdm = None; adx = None; dxbuf = []
            age[k] = 0
            continue
        age[k] = k - s
        up = h[k] - h[k - 1]; dn = l[k - 1] - l[k]
        p1 = up if (up > dn and up > 0) else 0.0
        m1 = dn if (dn > up and dn > 0) else 0.0
        tr1 = max(h[k] - l[k], abs(h[k] - c[k - 1]), abs(l[k] - c[k - 1]))
        if trs is None:
            acc_tr += tr1; acc_p += p1; acc_m += m1; cnt += 1
            if cnt < n:
                continue
            trs, pdm, mdm = acc_tr, acc_p, acc_m
        else:
            trs = trs - trs / n + tr1; pdm = pdm - pdm / n + p1; mdm = mdm - mdm / n + m1
        if not trs > 0:
            adx = None; dxbuf = []; continue
        pdi = 100.0 * pdm / trs; mdi = 100.0 * mdm / trs
        if not (pdi + mdi) > 0:
            adx = None; dxbuf = []; continue
        dx = 100.0 * abs(pdi - mdi) / (pdi + mdi)
        if adx is None:
            dxbuf.append(dx)
            if len(dxbuf) < n:
                continue
            adx = sum(dxbuf) / n; dxbuf = []
        else:
            adx = (adx * (n - 1) + dx) / n
        A[k] = adx
    return A, age


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
    ADX, AGE = adx_wilder(h, l, c, bad)
    f = P.Frame(df, set())
    gate = np.asarray(f.gate, bool)
    PV = W["PV"][i]; TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]
    elig = gate & PV[:n0] & np.asarray(df["traded"].to_numpy(), bool)

    def st_s(k):
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

    def st_d(k):
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

    EV = {}
    for sysn, N in NS.items():
        for d4 in (False, True):
            ks, pm = detect(h, c, bad, N, close_confirm=d4)
            cell = ("D4_" if d4 else "") + sysn
            kset = set(int(x) for x in ks)
            rows = []
            for k in ks:
                k = int(k)
                ka = k if d4 else k - 1                          # T6 濾網時點
                av = float(ADX[ka]) if ka >= 0 else float("nan")
                rows.append({"sid": sid, "T": int(idx[k]), "k": k, "N": N, "前N日最高": float(pm[k]),
                             ("收盤" if d4 else "最高"): float(c[k] if d4 else h[k]),
                             "ADX參考": av, "ADX段齡": int(AGE[ka]) if ka >= 0 else 0, "ADX>25": bool(np.isfinite(av) and av > ADX_TH),
                             "前一根也是事件": bool((k - 1) in kset),
                             "st": st_d(k) if d4 else st_s(k)})
            EV[cell] = rows
    EV["D3_S1"] = [e for e in EV["S1"] if e["ADX>25"]]
    EV["D3_S2"] = [e for e in EV["S2"] if e["ADX>25"]]
    EV["D3_D4S1"] = [e for e in EV["D4_S1"] if e["ADX>25"]]
    EV["D3_D4S2"] = [e for e in EV["D4_S2"] if e["ADX>25"]]
    sg = W["SIGPOS"].get(sid, np.array([], np.int64)); sgF = W["SIGPOS_YF"].get(sid, np.array([], np.int64))
    for sysn in NS:
        for e in EV[sysn]:
            T = e["T"]
            e["D5_同日"] = bool(np.isin(T, sg)); e["D5_同日_營飆"] = bool(np.isin(T, sgF))
            e["D5_20日內"] = bool(((sg >= T - D5_WIN + 1) & (sg <= T)).any())
            e["D5_20日內_營飆"] = bool(((sgF >= T - D5_WIN + 1) & (sgF <= T)).any())
        EV[f"D5_{sysn}_同日"] = [e for e in EV[sysn] if e["D5_同日"]]
        EV[f"D5_{sysn}_20日內"] = [e for e in EV[sysn] if e["D5_20日內"]]
    expo = {sgn: int(elig[p0:p1 + 1].sum()) for sgn, (p0, p1) in W["win"].items()}
    return sid, {"ev": EV, "expo": expo, "nb": nb, "nadx": int(np.isfinite(ADX).sum())}


def gaps(kept):
    bys = {}
    for e in sorted(kept, key=lambda x: (x["sid"], x["k"])):
        bys.setdefault(e["sid"], []).append(e["k"])
    g1 = g10 = g20 = 0
    for ks in bys.values():
        d = np.diff(np.asarray(ks))
        g1 += int((d == 1).sum()); g10 += int((d <= 10).sum()); g20 += int((d <= 20).sum())
    return g1, g10, g20


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = OUT if a.limit is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "海龜 Donchian 突破 seq2 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
         "登錄": f"台股策略線 seq2 sha {REG_SHA}",
         "裁定": "seq366 發號、seq367 發 seq2；N_前段 ＋2；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N；試跑一律乾跑", "世界": {}, "格": CELLS}
    FREQ = []; YR = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x, y) in SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x)))
            p1 = n0 - 2 if y is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["SIGPOS"], W["SIGPOS_YF"], cover, nsig = RU.load_sig(wn, cal)
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
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            tdy = (p1 - p0 + 1) / yrs
            expo = int(sum(r["expo"][sg] for r in ok.values()))
            segj = {"期間": f"{cal[p0].date()}～{cal[p1].date()}", "年": round(yrs, 3), "母體股日": expo}
            for cell in CELLS:
                rows = [e for r in ok.values() for e in r["ev"][cell] if p0 <= e["T"] <= p1]
                kept = [e for e in rows if e["st"] == "保留"]
                acc = {s_: sum(1 for e in rows if e["st"] == s_) for s_ in ST_ALL[1:]}
                months = len({ym[e["T"]] for e in kept}); ne = min(len(kept), months)
                nsid = len({e["sid"] for e in kept})
                g1, g10, g20 = gaps(kept)
                j = {"偵測(段內)": len(rows), **acc, "事件數(保留)": len(kept), "相異檔數": nsid, "有事件曆月": months, "n_eff": ne,
                     "n_eff<30": bool(ne < NEFF_MIN), "判斷": "依構造不可判定、不計 N" if ne < NEFF_MIN else "可判（n_eff ≥ 30）",
                     "每年事件數": round(len(kept) / yrs, 1) if yrs > 0 else None,
                     "每檔每年次數(母體股年)": round(len(kept) / (expo / tdy), 3) if expo else None,
                     "每檔每年次數(有事件檔)": round(len(kept) / nsid / yrs, 3) if nsid else None,
                     "同檔相鄰間隔=1根": g1, "同檔相鄰間隔≤10根": g10, "同檔相鄰間隔≤20根": g20,
                     "前一根非事件(連續突破第一根)": int(sum(1 for e in kept if not e["前一根也是事件"])),
                     "ADX段齡<150": int(sum(1 for e in kept if e["ADX>25"] and e["ADX段齡"] < ADX_WARM)) if cell.startswith("D3") else None,
                     "逐年保留": {int(y): int(v) for y, v in sorted(pd.Series([cal[e["T"]].year for e in kept]).value_counts().items())} if kept else {}}
                if cell in NS:
                    j["其中營飆訊號同日"] = int(sum(1 for e in kept if e["D5_同日_營飆"]))
                    j["其中營飆訊號20日內"] = int(sum(1 for e in kept if e["D5_20日內_營飆"]))
                segj[cell] = j
                row = {"世界": wn, "段": sg, "格": cell, "說明": CELLS[cell], "期間": segj["期間"],
                       **{k_: j[k_] for k_ in ("偵測(段內)", *ST_ALL[1:], "事件數(保留)", "相異檔數", "有事件曆月", "n_eff", "n_eff<30",
                                               "每年事件數", "每檔每年次數(母體股年)", "每檔每年次數(有事件檔)",
                                               "同檔相鄰間隔=1根", "同檔相鄰間隔≤10根", "同檔相鄰間隔≤20根", "前一根非事件(連續突破第一根)", "ADX段齡<150")}}
                FREQ.append(row)
                for y, v in j["逐年保留"].items():
                    YR.append({"世界": wn, "段": sg, "格": cell, "年": y, "保留": v})
            Wj["段"][sg] = segj
            log(f"[{wn}/{sg}] 母體股日 {expo}｜" + "｜".join(f"{c_} n={segj[c_]['事件數(保留)']} n_eff={segj[c_]['n_eff']}" for c_ in CELLS))
        # 事件檔（⛔ 無任何進場後價格、無報酬欄；價格欄只有 ≤ T 的前N日最高、T 日高或收盤、ADX(≤T)）
        allrows = []
        for cell in ("S1", "S2", "D4_S1", "D4_S2"):
            rows = sorted([e for r in ok.values() for e in r["ev"][cell]], key=lambda x: (x["T"], x["sid"]))
            if not rows:
                continue
            dfo = pd.DataFrame(rows)
            dfo["T"] = [str(cal[x].date()) for x in dfo["T"]]
            dfo.insert(0, "格", cell)
            allrows.append(dfo)
        with gzip.open(os.path.join(out_dir, f"events_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            pd.concat(allrows, ignore_index=True).to_csv(fh, index=False)
        Wj["診斷"] = {"有效K棒": int(sum(r["nb"] for r in ok.values())), "ADX有值K棒": int(sum(r["nadx"] for r in ok.values()))}
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
