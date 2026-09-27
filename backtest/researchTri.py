# -*- coding: utf-8 -*-
"""PREREG三態輪動（台股策略線登錄 seq3 sha c540678281cafde2；裁定 seq220～223、226；N_組合 ＋1）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTri pre     # ⛔ 不讀報酬
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTri body
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchTri_check.py

層：第二層（PREREGY 通過因素）＝ 0（3138bd5939）、第三層（反轉訊號＋上升趨勢線 大盤層通過者）＝ 0（502cf9761f、0feb35c37c）
   ⇒ 只跑第一層：轉弱 10 × 跌深 7 × 反彈 8 × B 態 2 ＝ 1,120 格

═══ 讀法（⭐ 看任何報酬前寫定；登錄沒寫死的地方）═══
  T1 0050 序列：早年 data/early（3edc0e2206；照 researchRev.market_series：除息因子＝參考價÷前收、接點比例 s＝主快照首根還原÷原始）
     ＋ 主快照 edc6f（data.load_stock 還原）⇒ 指標在【有效 K 棒】上算，再對回日曆（researchRev 同法）
     ⇒ 登錄 §三 探索段起點 2015-11-02 照字面；「200 日線與 250 日高首可算」在接早年序列下早已成立
  T2 指標：MA ＝ math.fsum 含當根（researchRev.ma_fsum）｜MACD(12,26,9)：DIF＝EMA12−EMA26（ewm adjust=False，第 26 根起）、
     訊號線 DEA ＝ DIF 從第 26 根起的 EMA9（adjust=False）｜KD(9,3,3) 台灣式（researchRev.kd）｜RSI(14) Wilder（researchRev.rsi）｜
     布林(20,2)：中軌＝MA20、σ＝20 根母體標準差（ddof＝0）｜乖離 ＝ c／MA60 − 1｜250 日高 ＝ 含當根 250 根收盤最高
  T3 事件 vs 狀態：「跌破／站回／上穿／下穿／死叉／金叉／後下穿／後上穿／後回落／連 N 日」＝ 事件（當根才成立；researchRev 的 60 日線同式：
     跌破＝c[t]＜MA[t] 且 c[t−1] ≥ MA[t−1]）；「連 N 日」＝ 連續計數【剛好到 N】那根（researchRev TD9 同式）；
     「＜／距」＝ 狀態（跌深 P1～P5、P7）；融資「20 日增 ＞ 10%」＝ 事件（由 ≤ 10% 變 ＞ 10% 那根）
     KD 高檔死叉 ＝ K[t]＜D[t] 且 K[t−1] ≥ D[t−1] 且 K[t−1]＞80；低檔金叉鏡像（K[t−1]＜20）
     RSI 跌破 50 ＝ RSI[t−1]＞50 且 RSI[t]＜50；站回鏡像（researchRev RSI70／30 同式）
     0050 沒有 K 棒的日子（2025-06-11～17 分割停牌）：事件 False、狀態沿用前一根
  T4 大盤外資 ＝ researchY.load_instamt 的 Fa（seq4 F＝a）；賣超 ＝ net ＜ 0、買超 ＝ net ＞ 0；
     大盤融資 ＝ researchY.load_marginmkt 的 prev（融資金額仟元）；20 日增 ＝ prev_T ÷ prev_(T−20) − 1（T−20 數 marginmkt 的檔；PREREGY #9 同式）
  T5 狀態機（逐日，用 t−1 的訊號決定 t 的狀態；t 開盤成交）：
     A：轉弱 ⇒ B｜B：反彈 ⇒ A（⭐ 同日兩者都出現 ⇒ 反彈優先，登錄「B 期間出現反彈訊號 ⇒ 直接回 A」）、否則 跌深 ⇒ C｜C：反彈 ⇒ A
     A 期間出現跌深、C 期間出現轉弱 ⇒ 不動；一天最多轉一次
     機器從「全部 25 個訊號都可算」的第一天以 A 起跑、連續跑到 2026-08-24；各段讀同一條狀態路徑（確認段承接探索段末的狀態，以 1.0 重新起算）
  T6 持有：A＝00631L 100%｜B＝0050 100%（B0050 版）或現金（B現金 版）｜C＝0050 100%；B0050→C 持有不變 ⇒ 不成交、不收成本
     引擎 ＝ researchLev2.engine（t 開盤成交、換手 ×0.385%、窗首付一次買進成本、有一檔沒開盤 ⇒ 整筆延後；閘二已對 P17.compose）
  T7 挑法：(乙) 探索段年化最高（判定）；(甲) 年化＞0050 且 比值 ≥ 0050 中比值最高（並列）；同分取轉換次數較少者，再同分取表列順序
     判定：挑法乙那格在確認段 年化 ＞ 0050 同窗 ⇒「只看報酬，贏 0050」；另標使用者判準 合格／另列／不合格（seq141 同式）
  T8 假訊號（⛔ 不判）：挑法乙那格在確認段的狀態序列，保留「轉換次數與依序經過的狀態」，轉換日改為確認段內隨機（不重複、均勻）；1,000 次
     （rng 20260929）⇒ 年化贏 0050 的比例 p；另報年化贏純抱 00631L 的比例
  T9 壓力段（合成、非實際 ETF）：合成正2 收盤 L_c[t] ＝ L_c[t−1]×(1＋2(c_t／c_{t−1}−1) − 0.01／245)、開盤 L_o[t] ＝ L_c[t−1]×(1＋2(o_t／c_{t−1}−1))
     （每日重設以前一日收盤為基準）；期間 ＝ 狀態機起跑日～2014-12-31（登錄「2004～2014」在訊號可算之後的部分）；另報 2008-01～2009-03 窗
     三列：輪動（A 抱合成正2）｜純抱合成正2｜0050；多久回本 ＝ 跌破 100 萬後、第一次回到 ≥ 100 萬的交易日數（沒回本 ⇒ 照實寫）
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import subprocess
import time
from itertools import product

import numpy as np
import pandas as pd

from . import data as D
from . import rerun17 as RR
from . import researchLev2 as L2
from . import researchY as Y

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsTri")
DB = os.path.expanduser("~/tw-stock-data")
EARLY_SHA = "3edc0e2206"
ANN = 245
FEE = 0.01 / 245
EXP = ("2015-11-02", "2021-12-30"); CONF = ("2022-01-03", "2026-08-24")
P08 = ("2008-01-02", "2009-03-31"); STRESS_END = "2014-12-31"
SEED = 20260929; NREP = 1000
WEAK = [("W1", "跌破 20 日線"), ("W2", "跌破 60 日線"), ("W3", "跌破 200 日線"), ("W4", "20 日線下穿 60 日線"), ("W5", "MACD 死叉"),
        ("W6", "KD 高檔死叉（K＞80 後下穿 D）"), ("W7", "RSI 跌破 50"), ("W8", "60 日正乖離＞10% 後回落"), ("W9", "大盤外資連 5 日賣超"),
        ("W10", "大盤融資 20 日增＞10%")]
DEEP = [("P1", "距 250 日高 −15%"), ("P2", "距 250 日高 −20%"), ("P3", "距 250 日高 −30%"), ("P4", "RSI＜30"), ("P5", "K＜20"),
        ("P6", "跌破布林下軌"), ("P7", "60 日負乖離＜−10%")]
UP = [("U1", "站回 20 日線"), ("U2", "站回 60 日線"), ("U3", "20 日線上穿 60 日線"), ("U4", "MACD 金叉"), ("U5", "KD 低檔金叉（K＜20 後上穿 D）"),
      ("U6", "RSI 站回 50"), ("U7", "站回布林中軌"), ("U8", "大盤外資連 3 日買超")]
BST = [("B0050", "B 態抱 0050"), ("Bcash", "B 態抱現金")]
NAME = dict(WEAK + DEEP + UP + BST)
LOGF = "pre_run.log"


def log(m):
    print(m, flush=True)
    with open(os.path.join(OUT, LOGF), "a", encoding="utf-8") as f:
        f.write(m + "\n")


def git(*a):
    return subprocess.run(["git", "-C", DB, *a], capture_output=True, text=True, check=True).stdout


# ═════════════ 資料 ═════════════
def load_all():
    RR.use_snapshot()
    Y.extract_db()
    cal_s, pos, gcal = Y.tw_calendar()                     # 早年＋主快照（字串）
    calm = D.load_calendar(); mstr = [str(x.date()) for x in calm]
    n = len(cal_s)
    off = cal_s.index(mstr[0])
    if cal_s[off:off + len(mstr)] != mstr:
        raise SystemExit("⛔ 合併日曆的主庫段 ≠ edc6f 日曆")
    # 主快照 0050、00631L（還原）
    O = {k: np.full(n, np.nan) for k in ("0050", "00631L")}; H = {k: np.full(n, np.nan) for k in O}; Lw = {k: np.full(n, np.nan) for k in O}
    Cc = {k: np.full(n, np.nan) for k in O}
    for s in O:
        st = D.load_stock(s, "twse", calm); df = st.df
        m = len(mstr)
        O[s][off:off + m] = df["open"].to_numpy(float); H[s][off:off + m] = df["high"].to_numpy(float)
        Lw[s][off:off + m] = df["low"].to_numpy(float); Cc[s][off:off + m] = df["close"].to_numpy(float)
    raw0 = pd.read_csv(os.path.join(D.DATA, "stocks", "0050.csv"), dtype={"date": str}, usecols=["date", "close"])
    raw0["close"] = pd.to_numeric(raw0["close"], errors="coerce")
    b0 = int(np.flatnonzero(np.isfinite(Cc["0050"]))[0])
    s_ = Cc["0050"][b0] / float(raw0.set_index("date").loc[cal_s[b0], "close"])
    # 早年 0050
    sha = git("rev-parse", EARLY_SHA).strip()
    rows = git("grep", "-h", "_0050,", sha, "--", "data/early/daily/")
    cols = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
            "shares", "transactions", "price_basis", "last_price"]
    d = pd.read_csv(io.StringIO(rows), header=None, names=cols, dtype=str)
    d = d[d["stock_id"] == "0050"].copy()
    for k in ("open", "high", "low", "close"):
        d[k] = pd.to_numeric(d[k], errors="coerce")
    bad = (d[["open", "high", "low", "close"]] <= 0).any(axis=1)
    d.loc[bad, ["open", "high", "low", "close"]] = np.nan
    d = d.sort_values("date").drop_duplicates("date")
    d = d[(d["date"] < mstr[0]) & d["close"].notna()].reset_index(drop=True)
    ex = git("grep", "-h", ",0050,", sha, "--", "data/early/exright/")
    e = pd.read_csv(io.StringIO(ex), header=None, names=["date", "stock_id", "pre_close", "ref_price", "value", "kind", "open_base",
                                                         "limit_up", "limit_down", "ex_div_ref"], dtype={"date": str, "stock_id": str})
    e = e[e["stock_id"] == "0050"].sort_values("date").reset_index(drop=True)
    f = e["ref_price"].astype(float).to_numpy() / e["pre_close"].astype(float).to_numpy()
    evd = e["date"].to_numpy()
    F = np.array([np.prod(f[evd > x]) for x in d["date"].to_numpy()]) * s_
    for k, arr in (("open", O), ("high", H), ("low", Lw), ("close", Cc)):
        for x, v in zip(d["date"], d[k].to_numpy(float) * F):
            arr["0050"][pos[x]] = v
    info = {"早年 sha": sha, "早年 0050 列": len(d), "早年首日": d["date"].iloc[0], "除息": len(e), "接點 s": float(s_),
            "合併日曆": [cal_s[0], cal_s[-1], n], "主庫段起點": mstr[0], "日曆閘": gcal}
    inst, a_inst = Y.load_instamt(cal_s)
    prev, _, a_mg = Y.load_marginmkt(cal_s)
    fa = pd.Series(inst["a"]).reindex(cal_s).to_numpy(float)
    return dict(cal=np.array(cal_s), pos=pos, O=O, H=H, L=Lw, C=Cc, fa=fa, prev=prev, a_inst=a_inst, a_mg=a_mg, info=info)


# ═════════════ 指標與訊號 ═════════════
def ma_fsum(c, n):
    out = np.full(len(c), np.nan)
    if len(c) >= n:
        W = np.lib.stride_tricks.sliding_window_view(c, n)
        out[n - 1:] = np.fromiter((math.fsum(r) for r in W), float, count=len(W)) / n
    return out


def kd(h, l, c):
    n = len(c); K = np.full(n, np.nan); Dd = np.full(n, np.nan); k_ = 50.0; d_ = 50.0
    for t in range(8, n):
        hh = float(np.max(h[t - 8:t + 1])); ll = float(np.min(l[t - 8:t + 1]))
        rsv = 50.0 if hh == ll else (c[t] - ll) / (hh - ll) * 100.0
        k_ = k_ * 2.0 / 3.0 + rsv / 3.0; d_ = d_ * 2.0 / 3.0 + k_ / 3.0
        K[t] = k_; Dd[t] = d_
    return K, Dd


def rsi(c, n=14):
    m = len(c); out = np.full(m, np.nan)
    dlt = np.diff(c); g = np.maximum(dlt, 0.0); lo = np.maximum(-dlt, 0.0)
    ag = float(np.mean(g[:n])); al = float(np.mean(lo[:n]))
    out[n] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for t in range(n + 1, m):
        ag = (ag * (n - 1) + g[t - 1]) / n; al = (al * (n - 1) + lo[t - 1]) / n
        out[t] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def macd(c):
    s = pd.Series(c)
    dif = (s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean()).to_numpy(float).copy()
    dif[:25] = np.nan
    dea = np.full(len(c), np.nan)
    dea[25:] = pd.Series(dif[25:]).ewm(span=9, adjust=False).mean().to_numpy()
    return dif, dea


def cross_dn(a, b):
    """a 由 ≥ b 變 ＜ b（當根）。"""
    out = np.zeros(len(a), bool)
    with np.errstate(invalid="ignore"):
        out[1:] = (a[1:] < b[1:]) & (a[:-1] >= b[:-1])
    return out


def cross_up(a, b):
    out = np.zeros(len(a), bool)
    with np.errstate(invalid="ignore"):
        out[1:] = (a[1:] > b[1:]) & (a[:-1] <= b[:-1])
    return out


def run_hit(x, n):
    """連續成立計數剛好到 n 的那根。"""
    out = np.zeros(len(x), bool); r = 0
    for i, v in enumerate(x):
        r = r + 1 if v else 0
        out[i] = r == n
    return out


def signals(G):
    cal = G["cal"]; N = len(cal)
    c0 = G["C"]["0050"]; bars = np.flatnonzero(np.isfinite(c0))
    c = c0[bars]; h = G["H"]["0050"][bars]; l = G["L"]["0050"][bars]
    ma20, ma60, ma200 = ma_fsum(c, 20), ma_fsum(c, 60), ma_fsum(c, 200)
    dif, dea = macd(c); K, Dd = kd(h, l, c); R = rsi(c)
    sd20 = np.full(len(c), np.nan)
    sd20[19:] = np.lib.stride_tricks.sliding_window_view(c, 20).std(axis=1, ddof=0)
    lower = ma20 - 2 * sd20
    bias = c / ma60 - 1
    hi250 = np.full(len(c), np.nan); hi250[249:] = np.lib.stride_tricks.sliding_window_view(c, 250).max(axis=1)
    dd = c / hi250 - 1
    Kp = np.concatenate([[np.nan], K[:-1]])
    with np.errstate(invalid="ignore"):
        bar = {
            "W1": cross_dn(c, ma20), "W2": cross_dn(c, ma60), "W3": cross_dn(c, ma200), "W4": cross_dn(ma20, ma60), "W5": cross_dn(dif, dea),
            "W6": cross_dn(K, Dd) & (Kp > 80), "W7": np.r_[False, (R[:-1] > 50) & (R[1:] < 50)],
            "W8": np.r_[False, (bias[:-1] > 0.10) & (bias[1:] <= 0.10)],
            "P1": dd <= -0.15, "P2": dd <= -0.20, "P3": dd <= -0.30, "P4": R < 30, "P5": K < 20, "P6": cross_dn(c, lower), "P7": bias < -0.10,
            "U1": cross_up(c, ma20), "U2": cross_up(c, ma60), "U3": cross_up(ma20, ma60), "U4": cross_up(dif, dea),
            "U5": cross_up(K, Dd) & (Kp < 20), "U6": np.r_[False, (R[:-1] < 50) & (R[1:] > 50)], "U7": cross_up(c, ma20)}
    # 可算的第一根（bar 序）：訊號所需指標在 t 與 t−1 都有值
    need = {"W1": ma20, "W2": ma60, "W3": ma200, "W4": ma60, "W5": dea, "W6": K, "W7": R, "W8": bias,
            "P1": dd, "P2": dd, "P3": dd, "P4": R, "P5": K, "P6": lower, "P7": bias,
            "U1": ma20, "U2": ma60, "U3": ma60, "U4": dea, "U5": K, "U6": R, "U7": ma20}
    level = {"P1", "P2", "P3", "P4", "P5", "P7"}
    S = {}; first = {}
    for k, v in bar.items():
        arr = np.zeros(N, bool)
        if k in level:
            full = np.full(N, np.nan); full[bars] = v.astype(float)
            arr = pd.Series(full).ffill().fillna(0).to_numpy().astype(bool)
        else:
            arr[bars] = v
        S[k] = arr
        fb = int(np.argmax(np.isfinite(need[k]))) + 1
        first[k] = bars[fb]
    fa = G["fa"]
    fok = np.isfinite(fa)
    S["W9"] = run_hit(np.where(fok, fa < 0, False), 5); S["U8"] = run_hit(np.where(fok, fa > 0, False), 3)
    first["W9"] = int(np.argmax(fok)) + 4; first["U8"] = int(np.argmax(fok)) + 2
    pv = G["prev"]; pd_ = np.asarray(pv.index, str); x = pv.to_numpy(float)
    chg = np.full(len(x), np.nan); chg[20:] = x[20:] / x[:-20] - 1
    ev = np.zeros(len(x), bool); ev[1:] = (chg[1:] > 0.10) & (chg[:-1] <= 0.10)
    arr = np.zeros(N, bool)
    for dte, v in zip(pd_, ev):
        if v:
            arr[G["pos"][dte]] = True
    S["W10"] = arr; first["W10"] = G["pos"][pd_[21]]
    # 資料缺日（instamt／marginmkt 在其起訖內缺的台北日）
    gaps = {"instamt": int(np.sum(~fok[int(np.argmax(fok)):])), "marginmkt": int(sum(1 for d_ in cal[G["pos"][pd_[0]]:] if d_ not in set(pd_)))}
    return S, first, gaps


# ═════════════ 狀態機 ═════════════
def machine(S, w, p, u, s0, N):
    """回 st[t]（0＝A、1＝B、2＝C）；t < s0 為 −1。用 t−1 的訊號決定 t。"""
    st = np.full(N, -1, np.int8); st[s0] = 0
    Wv, Pv, Uv = S[w], S[p], S[u]
    for t in range(s0 + 1, N):
        a = st[t - 1]; j = t - 1
        if a == 0:
            st[t] = 1 if Wv[j] else 0
        elif a == 1:
            st[t] = 0 if Uv[j] else (2 if Pv[j] else 1)
        else:
            st[t] = 0 if Uv[j] else 2
    return st


def weights(st, b):
    """assets (0050, LEV)：A [0,1]｜B [1,0] 或 [0,0]｜C [1,0]。"""
    W = np.zeros((len(st), 2))
    W[st == 0, 1] = 1.0; W[st == 2, 0] = 1.0
    if b == "B0050":
        W[st == 1, 0] = 1.0
    return W


def seg_run(G, W, i0, i1, lev="00631L"):
    n = i1 - i0 + 1
    O = {"0050": G["O"]["0050"], "LEV": G["O"][lev]}
    C = {"0050": pd.Series(G["C"]["0050"]).ffill().to_numpy(), "LEV": pd.Series(G["C"][lev]).ffill().to_numpy()}
    return L2.engine(("0050", "LEV"), W[i0:i1 + 1], np.zeros(n, bool), i0, O, C)


def seg_stats(r, st_seg, n):
    c, m = L2.perf(r["eq"])
    sw = int(np.sum(st_seg[1:] != st_seg[:-1]))
    stays = {}
    for k, nm in ((0, "A"), (1, "B"), (2, "C")):
        runs = []; t = 0
        while t < n:
            if st_seg[t] == k:
                s_ = t
                while t < n and st_seg[t] == k:
                    t += 1
                runs.append(t - s_)
            else:
                t += 1
        stays[nm] = (float(np.mean(runs)) if runs else 0.0, float(np.mean(st_seg == k)))
    return {"年化": c, "回落": m, "比值": L2.ratio(c, m), "狀態轉換": sw, "每年轉換": sw / (n / ANN), "成交次數": int(r["exec"][1:].sum()),
            "成本合計": float(r["cst"].sum()), "每年成本": float(r["cst"].sum()) / (n / ANN), "R8延後": r["delay"],
            "A平均停留": stays["A"][0], "A占比": stays["A"][1], "B平均停留": stays["B"][0], "B占比": stays["B"][1],
            "C平均停留": stays["C"][0], "C占比": stays["C"][1]}


def idx(G, d):
    return G["pos"][d]


# ═════════════ pre ═════════════
def pre(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = "pre_run.log"; open(os.path.join(OUT, LOGF), "w").close()
    log(f"===== researchTri pre {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）⛔ 不讀報酬 =====")
    G = load_all(); cal = G["cal"]; N = len(cal)
    Sx = {"登錄": "PREREG三態輪動 seq3 sha c540678281cafde2", "層": {"第二層 PREREGY": "0（3138bd5939）", "第三層 反轉／趨勢線大盤層": "0（502cf9761f、0feb35c37c）"},
          "資料": G["info"], "instamt": G["a_inst"], "marginmkt": G["a_mg"]}
    # 閘：0050 主窗錨（主快照段）
    calm = D.load_calendar(); w0, w1 = RR.win_bounds(calm)
    bw = RR.bench_row(calm, RR.load_bench(calm), w0, w1 + 1)
    Sx["閘_0050錨"] = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    # 閘：合併序列的主庫段 ＝ load_bench（ffill 前的有效根）
    off = G["pos"][str(calm[0].date())]
    lb = RR.load_bench(calm); cm = G["C"]["0050"][off:]
    Sx["閘_合併序列主庫段＝load_bench"] = bool(np.array_equal(pd.Series(cm).ffill().to_numpy()[:len(lb)], lb))
    log(f"[閘] 0050 錨 {Sx['閘_0050錨']}｜合併序列主庫段 {Sx['閘_合併序列主庫段＝load_bench']}｜{G['info']}")
    S, first, gaps = signals(G)
    s0 = max(first.values())
    Sx["狀態機起跑日（全部訊號可算）"] = str(cal[s0]); Sx["資料缺日"] = gaps
    segs = {"早年（起跑～2014-12-31）": (s0, idx(G, STRESS_END)), "探索": (idx(G, EXP[0]), idx(G, EXP[1])), "確認": (idx(G, CONF[0]), idx(G, CONF[1]))}
    rows = []
    for k, nm in WEAK + DEEP + UP:
        r = {"代號": k, "訊號": nm, "類": "轉弱" if k[0] == "W" else ("跌深" if k[0] == "P" else "反彈"),
             "型": "狀態" if k in ("P1", "P2", "P3", "P4", "P5", "P7") else "事件", "第一個可算日": str(cal[first[k]])}
        for sg, (i0, i1) in segs.items():
            r[f"{sg}_成立日數"] = int(S[k][i0:i1 + 1].sum())
        rows.append(r)
    sig = pd.DataFrame(rows); sig.to_csv(os.path.join(OUT, "pre_signals.csv"), index=False, encoding="utf-8")
    Sx["U1≡U7（站回20日線＝站回布林中軌）"] = bool(np.array_equal(S["U1"], S["U7"]))
    Sx["格數"] = {"字面": 10 * 7 * 8 * 2, "轉弱": 10, "跌深": 7, "反彈": 8, "B態": 2,
                "不同（U1≡U7 合併後）": 10 * 7 * (7 if Sx["U1≡U7（站回20日線＝站回布林中軌）"] else 8) * 2,
                "確認段判定": 1, "N_組合": "+1"}
    Sx["窗"] = {k: [str(cal[i0]), str(cal[i1]), i1 - i0 + 1] for k, (i0, i1) in segs.items()}
    Sx["00631L 在探索段起點有價"] = bool(np.isfinite(G["O"]["00631L"][idx(G, EXP[0])]))
    json.dump(Sx, open(os.path.join(OUT, "pre_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[訊號]\n{sig.to_string()}\n[起跑] {Sx['狀態機起跑日（全部訊號可算）']}｜缺日 {gaps}｜U1≡U7 {Sx['U1≡U7（站回20日線＝站回布林中軌）']}｜格數 {Sx['格數']}｜窗 {Sx['窗']}")
    if not (Sx["閘_0050錨"] and Sx["閘_合併序列主庫段＝load_bench"]):
        raise SystemExit("⛔ 閘不過")
    log("[完] pre（⛔ 未讀報酬）")


# ═════════════ body ═════════════
def body(a):
    global LOGF
    LOGF = "body_run.log"; open(os.path.join(OUT, LOGF), "w").close()
    log(f"===== researchTri body {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    G = load_all(); cal = G["cal"]; N = len(cal)
    S, first, _ = signals(G); s0 = max(first.values())
    e0, e1 = idx(G, EXP[0]), idx(G, EXP[1]); c0, c1 = idx(G, CONF[0]), idx(G, CONF[1])
    b50 = pd.Series(G["C"]["0050"]).ffill().to_numpy()

    def bperf(i0, i1):
        seg = b50[i0:i1 + 1]; c, m = L2.R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg)); return float(c), float(m)
    B = {"探索": bperf(e0, e1), "確認": bperf(c0, c1)}
    Sx = {"0050同窗": {k: {"年化": v[0], "回落": v[1], "比值": L2.ratio(*v)} for k, v in B.items()}}
    # 純抱 00631L
    hold = np.zeros((N, 2)); hold[:, 1] = 1.0
    PH = {}
    for sg, (i0, i1) in (("探索", (e0, e1)), ("確認", (c0, c1))):
        r = seg_run(G, hold, i0, i1); PH[sg] = (r, *L2.perf(r["eq"]))
    Sx["純抱00631L"] = {k: {"年化": v[1], "回落": v[2]} for k, v in PH.items()}
    log(f"[基準] 0050 {Sx['0050同窗']}｜純抱 00631L {Sx['純抱00631L']}")
    rows = []; ST = {}
    t0 = time.time()
    for (w, _), (p, _), (u, _), (b, _) in product(WEAK, DEEP, UP, BST):
        key = (w, p, u)
        if key not in ST:
            ST[key] = machine(S, w, p, u, s0, N)
        st = ST[key]; W = weights(st, b)
        for sg, (i0, i1) in (("探索", (e0, e1)), ("確認", (c0, c1))):
            r = seg_run(G, W, i0, i1)
            x = seg_stats(r, st[i0:i1 + 1], i1 - i0 + 1)
            c50, m50 = B[sg]
            rows.append({"段": sg, "轉弱": w, "跌深": p, "反彈": u, "B態": b, **x, "年化>0050": x["年化"] > c50,
                         "使用者判準": L2.label(x["年化"], x["回落"], c50, m50), "年化>純抱正2": x["年化"] > PH[sg][1]})
    df = pd.DataFrame(rows); df.to_csv(os.path.join(OUT, "body_cells.csv"), index=False, encoding="utf-8")
    log(f"[格] {len(df)} 列｜{time.time() - t0:.0f}s")
    ex = df[df["段"] == "探索"].reset_index(drop=True); ex["_o"] = range(len(ex))
    pick_b = ex.sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0]
    q = ex[(ex["年化"] > B["探索"][0]) & (ex["比值"] >= L2.ratio(*B["探索"]))]
    pick_a = q.sort_values(["比值", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0] if len(q) else None
    top10 = ex.sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).head(10)
    top10.to_csv(os.path.join(OUT, "body_top10_explore.csv"), index=False, encoding="utf-8")

    def cf(pk):
        return df[(df["段"] == "確認") & (df["轉弱"] == pk["轉弱"]) & (df["跌深"] == pk["跌深"]) & (df["反彈"] == pk["反彈"]) & (df["B態"] == pk["B態"])].iloc[0]

    def desc(pk):
        return f"{NAME[pk['轉弱']]} ⇒ 換{'0050' if pk['B態'] == 'B0050' else '現金'}｜{NAME[pk['跌深']]} ⇒ 抱 0050｜{NAME[pk['反彈']]} ⇒ 回 00631L"
    cb = cf(pick_b)
    Sx["挑法乙"] = {"格": [pick_b[k] for k in ("轉弱", "跌深", "反彈", "B態")], "白話": desc(pick_b),
                  "探索": {k: pick_b[k] for k in ("年化", "回落", "比值", "每年轉換")}, "確認": cb.drop(["段"]).to_dict(),
                  "判定": "只看報酬，贏 0050" if cb["年化"] > B["確認"][0] else "沒有贏 0050"}
    Sx["挑法甲"] = None if pick_a is None else {"格": [pick_a[k] for k in ("轉弱", "跌深", "反彈", "B態")], "白話": desc(pick_a),
                                              "探索": {k: pick_a[k] for k in ("年化", "回落", "比值")}, "確認": cf(pick_a).drop(["段"]).to_dict(),
                                              "探索合格格數": len(q)}
    log(f"[挑法乙] {Sx['挑法乙']}\n[挑法甲] {Sx['挑法甲']}")

    # 2022 谷底
    st_b = ST[(pick_b["轉弱"], pick_b["跌深"], pick_b["反彈"])]
    rb = seg_run(G, weights(st_b, pick_b["B態"]), c0, c1)
    y1 = idx(G, "2022-12-30"); ny = y1 - c0 + 1

    def y22(eq):
        p_ = np.concatenate([[1.0], eq[:ny]]); return float(p_.min() * 1e6), float(eq[ny - 1] * 1e6), str(cal[c0 + int(np.argmin(p_)) - 1]) if np.argmin(p_) > 0 else "起點"
    Sx["2022"] = {"輪動": y22(rb["eq"]), "純抱00631L": y22(PH["確認"][0]["eq"]), "0050": y22(b50[c0:c1 + 1] / b50[c0 - 1])}
    log(f"[2022 谷底／12-30／谷底日] {Sx['2022']}")

    # 假訊號
    stc = st_b[c0:c1 + 1]; n = len(stc)
    chg = np.flatnonzero(stc[1:] != stc[:-1]) + 1
    seq = [int(stc[0])] + [int(stc[i]) for i in chg]
    rng = np.random.default_rng(SEED); res = []; days = np.zeros((NREP, len(chg)), np.int32)
    for j in range(NREP):
        dd = np.sort(rng.choice(np.arange(1, n), size=len(chg), replace=False)); days[j] = dd
        s2 = np.full(n, seq[0], np.int8)
        for q_, dday in enumerate(dd):
            s2[dday:] = seq[q_ + 1]
        full = np.zeros(N, np.int8); full[c0:c1 + 1] = s2
        r = seg_run(G, weights(full, pick_b["B態"]), c0, c1); c_, m_ = L2.perf(r["eq"])
        res.append((c_, m_))
    res = np.array(res)
    np.savez_compressed(os.path.join(OUT, "body_null_days.npz"), days=days, seq=np.array(seq, np.int8))
    pd.DataFrame(res, columns=["年化", "回落"]).to_csv(os.path.join(OUT, "body_null.csv"), index=False, encoding="utf-8")
    Sx["假訊號"] = {"轉換次數": int(len(chg)), "p_年化贏0050": float(np.mean(res[:, 0] > B["確認"][0])),
                  "年化贏純抱00631L比例": float(np.mean(res[:, 0] > PH["確認"][1])),
                  "使用者判準合格比例": float(np.mean([L2.label(c_, m_, *B["確認"]) == "合格" for c_, m_ in res]))}
    log(f"[假訊號] {Sx['假訊號']}")

    # 壓力段（合成、非實際 ETF）
    o, c = G["O"]["0050"], b50
    Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 1] = 1.0
    for t in range(s0, N):
        Lo[t] = Lc[t - 1] * (1 + 2 * (o[t] / c[t - 1] - 1)) if np.isfinite(o[t]) else np.nan
        Lc[t] = Lc[t - 1] * (1 + 2 * (c[t] / c[t - 1] - 1) - FEE)
    G["O"]["SYN"], G["C"]["SYN"] = Lo, Lc
    st_rows = []
    for nm, (a_, b_) in (("早年全段（起跑～2014-12-31）", (s0, idx(G, STRESS_END))), ("2008-01～2009-03", (idx(G, P08[0]), idx(G, P08[1])))):
        n_ = b_ - a_ + 1
        for who, W in (("輪動（A 抱合成正2）", weights(st_b, pick_b["B態"])), ("純抱合成正2", hold), ("0050", None)):
            if W is None:
                eq = b50[a_:b_ + 1] / b50[a_ - 1]
            else:
                eq = seg_run(G, W, a_, b_, lev="SYN")["eq"]
            p_ = np.concatenate([[1.0], eq]); pk = np.maximum.accumulate(p_); il = int(np.argmin(p_))
            back = None
            if p_.min() < 1.0:
                after = np.flatnonzero(p_[il:] >= 1.0)
                back = int(after[0]) if len(after) else None
            ib = np.flatnonzero(p_ < 1.0)
            st_rows.append({"期間": nm, "起": str(cal[a_]), "迄": str(cal[b_]), "對象": who, "最大跌幅": float(((p_ - pk) / pk).min()),
                            "100萬谷底剩": float(p_.min() * 1e6), "谷底日": str(cal[a_ + il - 1]) if il > 0 else "起點",
                            "谷底後回到100萬的交易日數": back if back is not None else "期間內未回本",
                            "100萬期末": float(eq[-1] * 1e6), "年化": float(eq[-1] ** (ANN / n_) - 1)})
    stress = pd.DataFrame(st_rows); stress.to_csv(os.path.join(OUT, "body_stress.csv"), index=False, encoding="utf-8")
    Sx["壓力"] = st_rows
    log("[壓力（合成、非實際 ETF）]\n" + stress.to_string())
    json.dump(Sx, open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log("[完] body")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["pre", "body"])
    a = ap.parse_args()
    pre(a) if a.stage == "pre" else body(a)


if __name__ == "__main__":
    main()
