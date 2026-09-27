# -*- coding: utf-8 -*-
"""PREREG低頻擇時 seq1（台股策略線登錄 seq1 sha e117d462d9c0c796「大盤低頻擇時三件」；裁定 seq254 發號、N_組合 ＋3、⚠ 事後追加）。
回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLowFreq pre|body [--fake 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchLowFreq_check.py

═══ 沿用（登錄 §一；照原樣 import）═══
  資料   ＝ researchTri.load_all()：0050 早年 data/early（3edc0e2206）接主快照 edc6f（還原、接點比例）、00631L 主快照（還原）、合併日曆
  引擎   ＝ researchLev2.engine：t 開盤成交、換手金額 × 0.385%、窗首開盤建倉付一次成本、有一檔沒開盤 ⇒ 整筆延後；權重不變 ⇒ 不成交（漂移）
  指標   ＝ 0050 還原收盤、【有效 K 棒】上算（researchTri.ma_fsum）；0050 沒有 K 棒的日子：事件 False、狀態沿用前一根（researchTri T3）
  合成正2 ＝ researchTri T9 同式：L_c[t] ＝ L_c[t−1]×(1＋2(c_t／c_{t−1}−1) − 0.01／245)、L_o[t] ＝ L_c[t−1]×(1＋2(o_t／c_{t−1}−1))，
           從 0050 早年第一根起算；⚠ 逐字：「合成、非實際 ETF」
  現金   ＝ 0 息（登錄 §一）；描述另報年 1%（researchLev2 R6：每個交易日 ×1.01^(1/245)）
  段     ＝ 探索 2015-11-02～2021-12-30（挑）｜確認 2022-01-03～2026-08-24（判）｜早年合成 E0～2014-12-31（判；正2 用合成）
           各段獨立起跑（窗首開盤建倉）；丙的狀態機從全部指標可算日連續跑到 2026-08-24，各段讀同一條狀態路徑
  ⚠ 本線讀法 L1：早年段起點 E0 ＝ 所有格的訊號都可算之後的第一個月初交易日（登錄寫 2005-01；0050 早年資料 2004-02-11 起，
     12 個月線要 12 個月底、250 日高要 250 根 ⇒ 2005-01 當時還算不出來；同 researchTri「訊號要全部可算才起跑」前例）
═══ 三件（登錄 §二；⛔ 看數字前寫死）═══
  甲（8 格）：每月最後一個交易日判 0050 月底收盤 ＞ 均線 ⇒ 下個月抱 00631L 100%；否則 0050（a）／現金（b）
      均線：M6／M10／M12 ＝ 最近 6／10／12 個月底收盤（含本月底）平均；D200 ＝ 200 日線（有效 K 棒、含當根）在月底的值
  乙（12 格）：每月第一個交易日開盤調：w ＝ min(1, σ*／σ̂)，σ̂ ＝ 正2 過去 L 根日報酬標準差（ddof＝1，截至前一交易日）× √245；
      正2 ＝ 00631L（探索、確認段）／合成正2（早年段）；σ* ∈ {20%, 30%, 40%}、L ∈ {20, 60}；1 − w 放 0050（a）／現金（b）
  丙（24 格）：持有 0050（A）或 00631L（B）100%；停 ＝ 0050 收盤 ≤ 含當根 250 根最高收盤 × (1 − x)、x ∈ {10, 15, 20}% ⇒ 全換現金；
      回 R1 ＝ 0050 收盤 ＞ 前 59 根最高收盤（創 60 日新高）｜R2 ＝ 由下往上穿越 200 日線；檢查 D ＝ 每個有 K 棒的交易日、M ＝ 只在月底
      ⚠ 本線讀法 L2：M 版的 R2「穿越」＝ 相鄰兩次檢查之間：上個月底收 ≤ 200 日線、本月底收 ＞ 200 日線（字面「月底當天剛好穿越」另報描述）
  判定日 t−1 收盤、t 開盤換（全專案）
═══ 挑法與判定（登錄 §三）═══
  退化格：探索段＋早年段合計換手（權重改變）＜ 2 次、或一直待在同一狀態 ＞ 95%（甲：抱正2／不抱｜乙：w＝1／w＜1｜丙：持有／停出）⇒ 不進挑選
  挑法：每件探索段年化最高（同分取換手少、再同分取表列序）
  判定（每件 1 格、兩段）：主問 年化 ＞ 一直抱正2（同段；早年 ＝ 合成正2）⇒ 多賺／沒多賺；兩段都多賺 ⇒ 穩｜只一段 ⇒ 不穩｜都沒 ⇒ 沒多賺
        並列：對 0050 使用者判準、最大回落、2008 型最慘（早年段最大回落；100 萬在高點 ⇒ 谷底剩多少；是否超過使用者上限 −70%）
  必報（裁定 seq254）：每格並列同段「六四 v1」＝ 0050 60%＋00631L 40%（⚠ 逐字：「00685L 用 00631L 代」；早年用合成正2）、
        每年 1 月第一個交易日調回（researchMix70.reb_days 規則 Y）
  對照：一直抱 00631L（早年合成）｜一直抱 0050｜假訊號：挑中格在該段的權重序列保留「換手次數與依序經過的權重」、換手日改為段內隨機
        （不重複、均勻；rng default_rng(20260930)）1,000 次 ⇒ p ＝ 隨機年化 ≥ 本格的比例；p ≥ 0.05 ⇒ 句前「隨機換也做得到」
輸出 backtest/resultsLowFreq/
"""
from __future__ import annotations

import argparse
import json
import os
import time
from itertools import product

import numpy as np
import pandas as pd

from . import data as D
from . import rerun17 as RR
from . import researchLev2 as L2
from . import researchTri as T
from . import researchMix70 as MX

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsLowFreq")
ANN = 245
FEE = 0.01 / 245
COST = L2.COST
CASH_G = L2.CASH_G
EXP = ("2015-11-02", "2021-12-30"); CONF = ("2022-01-03", "2026-08-24"); EARLY_END = "2014-12-31"
P08 = ("2008-01-02", "2009-03-31")
LIMIT = -0.70
SEED = 20260930; NREP = 1000
TAG = "⚠ 事後追加（看過國外結果才提；裁定 seq254）"
SYN_TAG = "合成、非實際 ETF"
V64_TAG = "六四 v1 ＝ 0050 60%＋00685L 40%、每年 1 月調回；⚠ 00685L 用 00631L 代（早年用合成正2）"
CELLS = ([("甲", f"{m}_{v}") for m in ("M6", "M10", "M12", "D200") for v in ("a", "b")]
         + [("乙", f"s{s}_L{L}_{v}") for s in (20, 30, 40) for L in (20, 60) for v in ("a", "b")]
         + [("丙", f"{b}_x{x}_{r}_{f}") for b in ("A", "B") for x in (10, 15, 20) for r in ("R1", "R2") for f in ("D", "M")])
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


# ═════════════ 資料與指標 ═════════════
def load():
    G = T.load_all(); cal = G["cal"]; N = len(cal)
    o50 = G["O"]["0050"]; c50 = G["C"]["0050"]; b50 = pd.Series(c50).ffill().to_numpy()
    f0 = int(np.flatnonzero(np.isfinite(c50))[0])
    Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[f0] = 1.0
    for t in range(f0 + 1, N):
        Lo[t] = Lc[t - 1] * (1 + 2 * (o50[t] / b50[t - 1] - 1)) if np.isfinite(o50[t]) else np.nan
        Lc[t] = Lc[t - 1] * (1 + 2 * (b50[t] / b50[t - 1] - 1) - FEE)
    G["O"]["SYN"], G["C"]["SYN"] = Lo, Lc
    return G


def indicators(G):
    """0050 指標（日曆對齊）。"""
    cal = G["cal"]; N = len(cal)
    c = G["C"]["0050"]; valid = np.isfinite(c); bars = np.flatnonzero(valid); cb = c[bars]
    ma200b = T.ma_fsum(cb, 200)
    hi250b = np.full(len(cb), np.nan)
    if len(cb) >= 250:
        hi250b[249:] = np.lib.stride_tricks.sliding_window_view(cb, 250).max(axis=1)
    nh60b = np.zeros(len(cb), bool)
    if len(cb) >= 60:
        pm = np.lib.stride_tricks.sliding_window_view(cb[:-1], 59).max(axis=1)          # pm[k] ＝ max(cb[k..k+58])
        nh60b[59:] = cb[59:] > pm
    xupb = np.zeros(len(cb), bool)
    with np.errstate(invalid="ignore"):
        xupb[1:] = (cb[:-1] <= ma200b[:-1]) & (cb[1:] > ma200b[1:])
    lb = np.full(N, -1, int); lb[bars] = np.arange(len(bars)); lb = pd.Series(np.where(lb >= 0, lb, np.nan)).ffill().fillna(-1).to_numpy(int)
    ok = lb >= 0

    def st(xb):                     # 狀態：沿用最後一根
        out = np.full(N, np.nan); out[ok] = xb[lb[ok]]; return out

    def ev(xb):                     # 事件：只在有 K 棒的當天
        out = np.zeros(N, bool); out[bars] = xb; return out
    I = {"c": pd.Series(c).ffill().to_numpy(), "ma200": st(ma200b), "hi250": st(hi250b), "nh60": ev(nh60b), "xup": ev(xupb), "bar": valid}
    # 月底（合併日曆每月最後一個交易日）
    ym = np.array([s[:7] for s in cal])
    me = np.zeros(N, bool); me[:-1] = ym[:-1] != ym[1:]; me[-1] = False
    I["me"] = me
    mei = np.flatnonzero(me)
    mc = I["c"][mei]
    for k in (6, 10, 12):
        arr = np.full(N, np.nan)
        for j in range(k - 1, len(mei)):
            if np.isfinite(mc[j - k + 1:j + 1]).all():
                arr[mei[j]] = float(np.mean(mc[j - k + 1:j + 1]))
        I[f"M{k}"] = arr
    I["first_ok"] = {"M6": first_true(np.isfinite(I["M6"])), "M10": first_true(np.isfinite(I["M10"])), "M12": first_true(np.isfinite(I["M12"])),
                     "D200": first_true(np.isfinite(I["ma200"]) & me), "hi250": first_true(np.isfinite(I["hi250"])),
                     "nh60": first_true(I["nh60"]) if I["nh60"].any() else -1}
    return I


def first_true(m):
    w = np.flatnonzero(m)
    return int(w[0]) if len(w) else -1


def lev_sigma(G, lev, L):
    """sig[t] ＝ lev 在 t−1（含）以前最後 L 個日報酬的標準差 × √245（有效 K 棒；ddof＝1）。"""
    c = G["C"][lev]; N = len(c); valid = np.isfinite(c); bars = np.flatnonzero(valid)
    r = c[bars][1:] / c[bars][:-1] - 1.0
    sd = np.full(len(r), np.nan)
    if len(r) >= L:
        sd[L - 1:] = np.lib.stride_tricks.sliding_window_view(r, L).std(axis=1, ddof=1) * np.sqrt(ANN)
    # 第 k 個報酬屬於 bars[k+1]；sig 在 t 用「t−1 以前最後一根」
    at = np.full(N, np.nan); at[bars[1:]] = sd
    at = pd.Series(at).ffill().to_numpy()
    out = np.full(N, np.nan); out[1:] = at[:-1]
    return out


# ═════════════ 權重（日曆長度 N、(N, 2)：0050、LEV）═════════════
def W_jia(I, N, m, v):
    W = np.full((N, 2), np.nan); state = np.full(N, -1, np.int8)
    ma = I["ma200"] if m == "D200" else I[m]
    cur = None
    for t in range(N):
        if cur is not None:
            W[t] = cur[0]; state[t] = cur[1]
        if I["me"][t] and np.isfinite(ma[t]):
            on = I["c"][t] > ma[t]
            cur = (np.array([0.0, 1.0]) if on else (np.array([1.0, 0.0]) if v == "a" else np.array([0.0, 0.0])), 1 if on else 0)
    return W, state


def W_yi(I, G, N, s, L, v, lev_of):
    """lev_of(t) ⇒ 該日用哪條正2 的 σ̂（段決定）。回 (W, w)。"""
    sig = {k: lev_sigma(G, k, L) for k in set(lev_of)}
    W = np.full((N, 2), np.nan); wv = np.full(N, np.nan)
    cur = None
    ms = np.zeros(N, bool); ms[1:] = I["me"][:-1]            # 月初第一個交易日 ＝ 月底的次一日
    for t in range(N):
        if ms[t]:
            sg = sig[lev_of[t]][t]
            if np.isfinite(sg) and sg > 0:
                w = min(1.0, (s / 100.0) / sg)
                cur = (np.array([1.0 - w, w]) if v == "a" else np.array([0.0, w]), w)
        if cur is not None:
            W[t] = cur[0]; wv[t] = cur[1]
    return W, wv


def W_bing(I, N, b, x, r, f, start):
    """狀態機（start 起以「持有」起跑）；回 (W, state)。state：1 持有、0 停出。事件記錄 ev：[(判定日, 0／1)]。"""
    W = np.full((N, 2), np.nan); state = np.full(N, -1, np.int8); evs = []
    hold = np.array([1.0, 0.0]) if b == "A" else np.array([0.0, 1.0])
    s = 1; prev_me_below = None
    for t in range(start, N):
        state[t] = s; W[t] = hold if s == 1 else np.zeros(2)
        chk = I["bar"][t] if f == "D" else I["me"][t]
        if not chk:
            continue
        c = I["c"][t]
        below = bool(np.isfinite(I["ma200"][t]) and c <= I["ma200"][t])
        if s == 1:
            if np.isfinite(I["hi250"][t]) and c <= I["hi250"][t] * (1 - x / 100.0):
                s = 0; evs.append((t, 0))
        else:
            if r == "R1":
                go = bool(I["nh60"][t])
            elif f == "D":
                go = bool(I["xup"][t])
            else:
                go = prev_me_below is True and np.isfinite(I["ma200"][t]) and c > I["ma200"][t]
            if go:
                s = 1; evs.append((t, 1))
        if f == "M":
            prev_me_below = below
    # state[t] 是 t 當天持有的狀態（t−1 收盤判 ⇒ t 開盤換）：把判定後的新狀態移到次日
    st2 = np.full(N, -1, np.int8); W2 = np.full((N, 2), np.nan)
    st2[start] = 1; W2[start] = hold
    cur = 1
    evd = dict(evs)
    for t in range(start + 1, N):
        if (t - 1) in evd:
            cur = evd[t - 1]
        st2[t] = cur; W2[t] = hold if cur == 1 else np.zeros(2)
    return W2, st2, evs


def bing_literal_M_R2(I, N, b, x, start):
    """描述：M 版 R2 取字面「月底當天剛好由下往上穿越」。"""
    hold = np.array([1.0, 0.0]) if b == "A" else np.array([0.0, 1.0])
    W = np.full((N, 2), np.nan); s = 1
    W[start] = hold
    for t in range(start, N - 1):
        if I["me"][t]:
            c = I["c"][t]
            if s == 1 and np.isfinite(I["hi250"][t]) and c <= I["hi250"][t] * (1 - x / 100.0):
                s = 0
            elif s == 0 and I["xup"][t]:
                s = 1
        W[t + 1] = hold if s == 1 else np.zeros(2)
    return W


# ═════════════ 跑一段 ═════════════
def run_seg(G, W, i0, i1, lev, cash_g=0.0, R=None):
    n = i1 - i0 + 1
    O = {"0050": G["O"]["0050"], "LEV": G["O"][lev]}
    C = {"0050": pd.Series(G["C"]["0050"]).ffill().to_numpy(), "LEV": pd.Series(G["C"][lev]).ffill().to_numpy()}
    return L2.engine(("0050", "LEV"), W[i0:i1 + 1], np.zeros(n, bool) if R is None else R, i0, O, C, cash_g=cash_g)


def dd_info(eq, cal, i0):
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p); dd = (p - pk) / pk; it = int(np.argmin(dd))
    ip = int(np.argmax(p[:it + 1])) if it > 0 else 0
    back = np.flatnonzero(p[it:] >= p[ip])
    return {"最大回落": float(dd.min()), "高點日": str(cal[i0 + ip - 1]) if ip > 0 else "起點", "谷底日": str(cal[i0 + it - 1]) if it > 0 else "起點",
            "100萬在高點_谷底剩（萬）": float((1 + dd.min()) * 100), "回到高點的交易日數": int(back[0]) if len(back) else "段內未回本"}


def window_trough(eq, cal, i0, a, b):
    """100 萬在 a 的前一交易日收盤 ⇒ [a, b] 內最低與期末、回到 100 萬的交易日數。"""
    ia, ib = a - i0, b - i0
    base = eq[ia - 1] if ia > 0 else 1.0
    seg = eq[ia:ib + 1] / base
    it = int(np.argmin(seg)); after = np.flatnonzero(eq[ia + it:] / base >= 1.0)
    return {"谷底剩（萬）": float(min(1.0, seg.min()) * 100), "期末（萬）": float(seg[-1] * 100), "谷底日": str(cal[a + it]),
            "谷底後回到100萬的交易日數": int(after[0]) if len(after) else "段內未回本"}


def stats(G, r, W, i0, i1, extra_state=None):
    cal = G["cal"]; n = i1 - i0 + 1; eq = r["eq"]
    c, m = L2.perf(eq)
    Wd = W[i0:i1 + 1]
    ch = int(np.sum(np.any(np.abs(Wd[1:] - Wd[:-1]) > 1e-12, axis=1)))
    prev = np.r_[1.0, eq[:-1]]
    out = {"年化": c, "回落": m, "比值": L2.ratio(c, m), "換手次數": ch, "每年換手": ch / (n / ANN),
           "成本／年": float(np.sum(r["cst"][1:] / prev[1:])) / (n / ANN), "延後日": r["delay"],
           "正2平均比例": float(np.nanmean(Wd[:, 1])), "0050平均比例": float(np.nanmean(Wd[:, 0])), "現金平均比例": float(np.nanmean(1 - Wd.sum(1))),
           "正2比例_最低": float(np.nanmin(Wd[:, 1])), "正2比例_最高": float(np.nanmax(Wd[:, 1]))}
    out.update(dd_info(eq, cal, i0))
    return out


# ═════════════ 主程式 ═════════════
def build(G, I):
    cal = G["cal"]; N = len(cal); pos = G["pos"]
    e0, e1 = pos[EXP[0]], pos[EXP[1]]; c0, c1 = pos[CONF[0]], pos[CONF[1]]
    # 丙起跑：hi250、ma200 可算且 nh60 可算
    g0 = max(I["first_ok"]["hi250"], first_true(np.isfinite(I["ma200"])), 60)
    # 早年段 E0：全部格可算之後第一個月初交易日（甲 M12／D200 月底值、乙 60 根、丙起跑）
    need = max(I["first_ok"]["M12"], I["first_ok"]["D200"], I["first_ok"]["M6"], I["first_ok"]["M10"], g0,
               first_true(np.isfinite(lev_sigma(G, "SYN", 60))))
    ms = np.zeros(N, bool); ms[1:] = I["me"][:-1]
    E0 = int(np.flatnonzero(ms & (np.arange(N) > need))[0])
    E1 = pos[EARLY_END] if EARLY_END in pos else int(np.searchsorted(cal, EARLY_END, side="right")) - 1
    SEGS = {"探索": (e0, e1, "00631L"), "確認": (c0, c1, "00631L"), "早年": (E0, E1, "SYN")}
    lev_of = np.array(["00631L"] * N, object); lev_of[:e0] = "SYN"
    WS = {}
    for fam, key in CELLS:
        p = key.split("_")
        if fam == "甲":
            W, st = W_jia(I, N, p[0], p[1]); WS[(fam, key)] = (W, (st == 1).astype(int), None)
        elif fam == "乙":
            W, wv = W_yi(I, G, N, int(p[0][1:]), int(p[1][1:]), p[2], lev_of); WS[(fam, key)] = (W, (np.abs(wv - 1.0) < 1e-12).astype(int), wv)
        else:
            W, st, evs = W_bing(I, N, p[0], int(p[1][1:]), p[2], p[3], g0); WS[(fam, key)] = (W, st, evs)
    return SEGS, WS, g0, E0


def degenerate(WS, SEGS):
    rows = []
    for (fam, key), (W, st, _) in WS.items():
        ch = 0; same = []; ntot = 0
        for sg in ("探索", "早年"):
            i0, i1, _ = SEGS[sg]; Wd = W[i0:i1 + 1]
            ch += int(np.sum(np.any(np.abs(Wd[1:] - Wd[:-1]) > 1e-12, axis=1)))
            s_ = np.asarray(st[i0:i1 + 1]); same.append(s_); ntot += len(s_)
        s_all = np.concatenate(same)
        vals, cnt = np.unique(s_all, return_counts=True)
        top = float(cnt.max() / ntot)
        bad = []
        if ch < 2:
            bad.append("換手 ＜ 2")
        if top > 0.95:
            bad.append(f"同一狀態 {top:.1%} ＞ 95%")
        rows.append({"件": fam, "格": key, "探索＋早年換手": ch, "最常狀態占比": top, "退化": "；".join(bad)})
    return pd.DataFrame(rows)


def pre(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "pre_run.log"); open(LOGF, "w").close()
    log(f"===== researchLowFreq pre {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG}｜⛔ 不讀報酬 =====")
    G = load(); I = indicators(G); cal = G["cal"]
    SEGS, WS, g0, E0 = build(G, I)
    Dg = degenerate(WS, SEGS); Dg.to_csv(os.path.join(OUT, "pre_degenerate.csv"), index=False, encoding="utf-8")
    calm = D.load_calendar(); w0, w1 = RR.win_bounds(calm)
    bw = RR.bench_row(calm, RR.load_bench(calm), w0, w1 + 1)
    gate = abs(bw["cagr"] - RR.ANCHOR[0]) < 1e-12 and abs(bw["mdd"] - RR.ANCHOR[1]) < 1e-12
    off = G["pos"][str(calm[0].date())]; lb = RR.load_bench(calm)
    gate2 = bool(np.array_equal(pd.Series(G["C"]["0050"][off:]).ffill().to_numpy()[:len(lb)], lb))
    Sx = {"登錄": "PREREG低頻擇時 seq1 sha e117d462d9c0c796；裁定 seq254；N_組合 ＋3", "性質": TAG, "資料": G["info"],
          "格數": {"甲": 8, "乙": 12, "丙": 24, "合計": len(CELLS)},
          "窗": {k: [str(cal[v[0]]), str(cal[v[1]]), v[1] - v[0] + 1, v[2]] for k, v in SEGS.items()},
          "指標第一個可算日": {k: (str(cal[v]) if v >= 0 else None) for k, v in I["first_ok"].items()},
          "丙狀態機起跑": str(cal[g0]), "早年段起點 E0（讀法 L1）": str(cal[E0]),
          "閘_0050錨": gate, "閘_合併序列主庫段＝load_bench": gate2,
          "退化格": {f"{r.件}|{r.格}": r.退化 for r in Dg.itertuples() if r.退化}}
    ev = {}
    for (fam, key), (W, st, evs) in WS.items():
        if fam == "丙":
            for sg, (i0, i1, _) in SEGS.items():
                ev[f"{key}|{sg}"] = {"停出": sum(1 for t, k in evs if k == 0 and i0 - 1 <= t < i1), "買回": sum(1 for t, k in evs if k == 1 and i0 - 1 <= t < i1)}
    Sx["丙_停出與買回次數"] = ev
    json.dump(Sx, open(os.path.join(OUT, "pre_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[閘] 0050 錨 {gate}｜合併序列主庫段 {gate2}")
    log(f"[窗] {Sx['窗']}｜丙起跑 {Sx['丙狀態機起跑']}｜指標可算 {Sx['指標第一個可算日']}")
    log("[退化判定（探索＋早年；⛔ 不讀報酬）]\n" + Dg.to_string())
    if not (gate and gate2):
        raise SystemExit("⛔ 閘不過")
    log("[完] pre")


def body(a):
    global LOGF
    LOGF = os.path.join(OUT, "body_run.log"); open(LOGF, "w").close()
    log(f"===== researchLowFreq body {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    G = load(); I = indicators(G); cal = G["cal"]; N = len(cal)
    SEGS, WS, g0, E0 = build(G, I)
    Dg = degenerate(WS, SEGS)
    pre_d = pd.read_csv(os.path.join(OUT, "pre_degenerate.csv"), encoding="utf-8")
    kc = ["件", "格", "探索＋早年換手", "退化"]
    if not (pre_d[kc].fillna("").astype(str).values == Dg[kc].fillna("").astype(str).values).all():
        raise SystemExit("⛔ 閘：body 重算的退化判定 ≠ pre")
    log("[閘] body 重算的退化判定 ＝ pre（逐格）")
    b50 = pd.Series(G["C"]["0050"]).ffill().to_numpy()
    BASE = {}
    for sg, (i0, i1, lev) in SEGS.items():
        seg = b50[i0:i1 + 1]; c_, m_ = L2.R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg))
        hold = np.zeros((N, 2)); hold[:, 1] = 1.0
        rh = run_seg(G, hold, i0, i1, lev); ch_, mh_ = L2.perf(rh["eq"])
        v64 = np.tile([0.6, 0.4], (N, 1))
        r64 = run_seg(G, v64, i0, i1, lev, R=MX.reb_days(list(cal), i0, i1, "Y", 1)); c64, m64 = L2.perf(r64["eq"])
        o50 = np.zeros((N, 2)); o50[:, 0] = 1.0
        r50 = run_seg(G, o50, i0, i1, lev); c5e, m5e = L2.perf(r50["eq"])
        BASE[sg] = {"0050": {"年化": float(c_), "回落": float(m_), "比值": L2.ratio(float(c_), float(m_))},
                    "0050_引擎（含建倉成本）": {"年化": c5e, "回落": m5e},
                    "一直抱正2": {"年化": ch_, "回落": mh_, **dd_info(rh["eq"], cal, i0)}, "六四v1": {"年化": c64, "回落": m64, **dd_info(r64["eq"], cal, i0)},
                    "_eq": {"hold": rh["eq"], "v64": r64["eq"], "e50": r50["eq"]}}
    log(f"[基準] " + json.dumps({k: {kk: vv for kk, vv in v.items() if kk != '_eq'} for k, v in BASE.items()}, ensure_ascii=False, default=str)[:1500])
    rows = []; EQ = {}
    for (fam, key), (W, st, extra) in WS.items():
        for sg, (i0, i1, lev) in SEGS.items():
            r = run_seg(G, W, i0, i1, lev); x = stats(G, r, W, i0, i1)
            B = BASE[sg]
            x.update({"件": fam, "格": key, "段": sg, "對0050判準": L2.label(x["年化"], x["回落"], B["0050"]["年化"], B["0050"]["回落"]),
                      "比一直抱正2（點）": (x["年化"] - B["一直抱正2"]["年化"]) * 100, "比六四v1（點）": (x["年化"] - B["六四v1"]["年化"]) * 100,
                      "狀態占比": float(np.mean(np.asarray(st[i0:i1 + 1]) == 1)), "退化": Dg[(Dg["件"] == fam) & (Dg["格"] == key)]["退化"].iloc[0]})
            if fam == "丙":
                evs = extra; outs = [(t, k) for t, k in evs]
                eps = []; cur = None
                for t, k in outs:
                    if k == 0:
                        cur = t
                    elif cur is not None:
                        eps.append((cur, t)); cur = None
                if cur is not None:
                    eps.append((cur, None))
                eps = [e for e in eps if i0 - 1 <= e[0] < i1]
                asset = "0050" if key.startswith("A") else lev
                miss = []; dur = []
                cff = pd.Series(G["C"][asset]).ffill().to_numpy()
                for s_, e_ in eps:
                    a_ = s_ + 1
                    if e_ is not None and e_ + 1 <= i1:
                        b_ = e_ + 1; ob = G["O"][asset][b_]
                    else:
                        b_ = i1; ob = cff[i1]
                    oa = G["O"][asset][a_]
                    if np.isfinite(oa) and np.isfinite(ob):
                        miss.append(ob / oa - 1.0)
                    dur.append(b_ - a_)
                x.update({"停出次數": len(eps), "平均停出天數": float(np.mean(dur)) if dur else np.nan,
                          "停出期間持有標的漲跌（放棄組）_平均": float(np.mean(miss)) if miss else np.nan,
                          "停出期間漲跌_中位": float(np.median(miss)) if miss else np.nan, "停出期間上漲的比例": float(np.mean(np.array(miss) > 0)) if miss else np.nan})
            if sg == "早年":
                x["2008窗（100萬在2007-12-31）"] = window_trough(r["eq"], cal, i0, G["pos"][P08[0]], G["pos"][P08[1]])
            if sg == "確認":
                x["2022窗（100萬在2021-12-30）"] = window_trough(r["eq"], cal, i0, G["pos"]["2022-01-03"], G["pos"]["2022-12-30"])
            rows.append(x); EQ[(fam, key, sg)] = r["eq"]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8")
    # 挑格
    PICK = {}; TOP5 = {}
    for fam in ("甲", "乙", "丙"):
        ex = df[(df["件"] == fam) & (df["段"] == "探索")].copy(); ex["_o"] = range(len(ex))
        TOP5[fam] = ex.sort_values(["年化", "換手次數", "_o"], ascending=[False, True, True]).head(5)[["格", "年化", "回落", "每年換手", "退化"]].to_dict("records")
        ok = ex[ex["退化"].fillna("") == ""]
        if not len(ok):
            PICK[fam] = None; continue
        PICK[fam] = ok.sort_values(["年化", "換手次數", "_o"], ascending=[False, True, True]).iloc[0]["格"]
    log(f"[挑格] {PICK}")
    # 判定
    J = {}
    for fam, key in PICK.items():
        if key is None:
            J[fam] = {"判定": "依構造不可判定（全部格退化）"}; continue
        seg = {sg: df[(df["件"] == fam) & (df["格"] == key) & (df["段"] == sg)].iloc[0] for sg in SEGS}
        more = {sg: bool(seg[sg]["年化"] > BASE[sg]["一直抱正2"]["年化"]) for sg in ("確認", "早年")}
        read = "穩" if all(more.values()) else ("沒多賺" if not any(more.values()) else ("不穩，只在多頭段（確認段）有用" if more["確認"] else "不穩，只在空頭段（早年段，含 2008）有用"))
        mdd_e = float(seg["早年"]["最大回落"])
        J[fam] = {"格": key, "多賺": more, "讀法": read,
                  **{f"{sg}": {k: (float(seg[sg][k]) if isinstance(seg[sg][k], (int, float, np.floating, np.integer)) else seg[sg][k])
                               for k in ("年化", "回落", "比值", "每年換手", "成本／年", "對0050判準", "比一直抱正2（點）", "比六四v1（點）", "正2平均比例", "狀態占比")}
                     for sg in ("探索", "確認", "早年")},
                  "2008型最慘（早年段最大回落、100萬在高點）": {"剩（萬）": (1 + mdd_e) * 100, "最大回落": mdd_e, "超過使用者上限 −70%": bool(mdd_e < LIMIT),
                                                     "高點日": seg["早年"]["高點日"], "谷底日": seg["早年"]["谷底日"], "回到高點的交易日數": seg["早年"]["回到高點的交易日數"]},
                  "2008窗": seg["早年"]["2008窗（100萬在2007-12-31）"], "2022窗": seg["確認"]["2022窗（100萬在2021-12-30）"]}
    # 對照：假訊號（確認段、早年段）
    rng = np.random.default_rng(SEED); FK = {}
    for fam, key in PICK.items():
        if key is None:
            continue
        W = WS[(fam, key)][0]; FK[fam] = {}
        for sg in ("確認", "早年"):
            i0, i1, lev = SEGS[sg]; Wd = W[i0:i1 + 1]; n = len(Wd)
            chg = np.flatnonzero(np.any(np.abs(Wd[1:] - Wd[:-1]) > 1e-12, axis=1)) + 1
            seqW = [Wd[0]] + [Wd[i] for i in chg]
            res = []
            for j in range(a.fake):
                dd_ = np.sort(rng.choice(np.arange(1, n), size=len(chg), replace=False)) if len(chg) else np.zeros(0, int)
                W2 = np.repeat(seqW[0][None, :], n, axis=0)
                for q_, d_ in enumerate(dd_):
                    W2[d_:] = seqW[q_ + 1]
                full = np.full((N, 2), np.nan); full[i0:i1 + 1] = W2
                res.append(L2.perf(run_seg(G, full, i0, i1, lev)["eq"])[0])
            res = np.array(res); real = float(df[(df["件"] == fam) & (df["格"] == key) & (df["段"] == sg)]["年化"].iloc[0])
            FK[fam][sg] = {"換手次數": int(len(chg)), "中位": float(np.median(res)), "p10": float(np.percentile(res, 10)), "p90": float(np.percentile(res, 90)),
                           "p（隨機 ≥ 本格）": float(np.mean(res >= real)), "隨機贏一直抱正2比例": float(np.mean(res > BASE[sg]["一直抱正2"]["年化"])),
                           "隨機贏六四v1比例": float(np.mean(res > BASE[sg]["六四v1"]["年化"]))}
        log(f"  [假訊號 {fam}] {FK[fam]}")
    # 描述：現金年 1%（挑中格、兩段）；丙 M×R2 字面讀法
    DESC = {}
    for fam, key in PICK.items():
        if key is None:
            continue
        W = WS[(fam, key)][0]
        DESC[f"{fam}_現金年1%"] = {sg: dict(zip(("年化", "回落"), L2.perf(run_seg(G, W, SEGS[sg][0], SEGS[sg][1], SEGS[sg][2], cash_g=CASH_G)["eq"])))
                                 for sg in ("確認", "早年")}
    lit = {}
    for b in ("A", "B"):
        for x in (10, 15, 20):
            W = bing_literal_M_R2(I, N, b, x, g0)
            lit[f"{b}_x{x}_R2_M（字面：月底當天剛好穿越）"] = {sg: dict(zip(("年化", "回落"), L2.perf(run_seg(G, W, i0, i1, lev)["eq"]))) | {
                "換手次數": int(np.sum(np.any(np.abs(W[i0 + 1:i1 + 1] - W[i0:i1]) > 1e-12, axis=1)))} for sg, (i0, i1, lev) in SEGS.items()}
    DESC["丙_M×R2_字面讀法"] = lit
    S = {"登錄": "PREREG低頻擇時 seq1 sha e117d462d9c0c796；裁定 seq254；N_組合 ＋3", "性質": TAG, "六四v1": V64_TAG, "合成": SYN_TAG,
         "窗": {k: [str(cal[v[0]]), str(cal[v[1]]), v[1] - v[0] + 1, v[2]] for k, v in SEGS.items()}, "早年段起點 E0（讀法 L1）": str(cal[E0]),
         "丙狀態機起跑": str(cal[g0]), "基準": {k: {kk: vv for kk, vv in v.items() if kk != "_eq"} for k, v in BASE.items()},
         "挑格": PICK, "探索段前5": TOP5, "判定": J, "假訊號": FK, "描述": DESC, "退化格": {f"{r.件}|{r.格}": r.退化 for r in Dg.itertuples() if r.退化}}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    np.savez_compressed(os.path.join(OUT, "eq_picked.npz"), **{f"{f}_{k}_{s}": v for (f, k, s), v in EQ.items() if PICK.get(f) == k},
                        **{f"base_{sg}_{nm}": v for sg, B in BASE.items() for nm, v in B["_eq"].items()})
    log(f"[判定] " + json.dumps({f: (j.get("讀法"), j.get("確認", {}).get("對0050判準")) for f, j in J.items()}, ensure_ascii=False))
    log("[完] body")


SENS = ("SL10", "SL20", "AT2", "TP30h", "TP50h", "R0-40")
SENS_NOTE = ("出場敏感度（新規矩 ③、裁定 seq242 ②；描述、⛔ 不判）：擇時件只有一檔正2，⇒ 套在【正2 那一腳】：段落 ＝ 規則兩次換手之間；"
             "參考價 ＝ 段落第一天正2 開盤；SL10／SL20 收盤 ≤ 參考價 ×0.9／0.8 ⇒ 次日開盤正2 那腳全換現金到規則下次換手；"
             "AT2 ＝ 段落以來正2 最高收盤 − 2×ATR14（Wilder、00631L 高低收；早年合成無高低價 ⇒ 不適用）；TP30h／TP50h 收盤 ≥ 參考價 ×1.3／1.5 ⇒ 次日正2 那腳賣半（一次）；"
             "R0-40 ＝ 段落第 40 根收盤 ≤ 參考價 ⇒ 次日正2 那腳全換現金；檔數 {5, 10, 20} 不適用（單一 ETF）；0050 那腳不動")


def overlay(G, W, i0, i1, lev, kind, atr_cal=None):
    """回改過的 W（日曆長度）；只動正2 那腳。"""
    W2 = W.copy(); Wd = W[i0:i1 + 1]
    chg = [0] + list(np.flatnonzero(np.any(np.abs(Wd[1:] - Wd[:-1]) > 1e-12, axis=1)) + 1) + [i1 - i0 + 1]
    Cl = pd.Series(G["C"][lev]).ffill().to_numpy(); Ol = G["O"][lev]; valid = np.isfinite(G["C"][lev])
    for a_, b_ in zip(chg[:-1], chg[1:]):
        s, e = i0 + a_, i0 + b_ - 1
        if W[s, 1] <= 0:
            continue
        ref = Ol[s] if np.isfinite(Ol[s]) else Cl[s]
        hi = -np.inf; nb = 0
        for t in range(s, e):
            if not valid[t]:
                continue
            nb += 1; hi = max(hi, Cl[t]); cut = None
            if kind in ("SL10", "SL20") and Cl[t] <= ref * (0.9 if kind == "SL10" else 0.8):
                cut = 0.0
            elif kind == "AT2" and atr_cal is not None and np.isfinite(atr_cal[t]) and Cl[t] < hi - 2 * atr_cal[t]:
                cut = 0.0
            elif kind in ("TP30h", "TP50h") and Cl[t] >= ref * (1.3 if kind == "TP30h" else 1.5):
                cut = 0.5
            elif kind == "R0-40" and nb == 40 and Cl[t] <= ref:
                cut = 0.0
            if cut is not None:
                W2[t + 1:e + 1, 1] = W[t + 1:e + 1, 1] * cut
                break
    return W2


def sens(a):
    global LOGF
    LOGF = os.path.join(OUT, "sens_run.log"); open(LOGF, "w").close()
    from . import research11 as R11
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    lab = [f for f, j in S["判定"].items() if "確認" in j and (j["確認"]["對0050判準"] in ("合格", "另列") or j["早年"]["對0050判準"] in ("合格", "另列"))]
    log(f"===== researchLowFreq sens（描述）｜合格／另列：{lab} =====")
    G = load(); I = indicators(G); N = len(G["cal"])
    SEGS, WS, g0, E0 = build(G, I)
    c = G["C"]["00631L"]; b = np.flatnonzero(np.isfinite(c))
    atr_b = R11.wilder_atr(G["H"]["00631L"][b], G["L"]["00631L"][b], c[b])
    atr = np.full(N, np.nan); atr[b] = atr_b
    OUTS = {}
    for f in lab:
        key = S["挑格"][f]; W = WS[(f, key)][0]; OUTS[f] = {}
        for kind in ("原規則",) + SENS:
            OUTS[f][kind] = {}
            for sg in ("確認", "早年"):
                i0, i1, lev = SEGS[sg]
                if kind == "原規則":
                    Wk = W
                elif kind == "AT2" and lev == "SYN":
                    OUTS[f][kind][sg] = [float("nan"), float("nan")]; continue
                else:
                    Wk = overlay(G, W, i0, i1, lev, kind, atr if lev == "00631L" else None)
                OUTS[f][kind][sg] = list(L2.perf(run_seg(G, Wk, i0, i1, lev)["eq"]))
        log(f"  [{f} {key}] " + json.dumps(OUTS[f], ensure_ascii=False))
    S["出場敏感度"] = OUTS; S["出場敏感度_註"] = SENS_NOTE
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log("[完] sens")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pre", "body", "sens"])
    ap.add_argument("--fake", type=int, default=NREP)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    {"pre": pre, "body": body, "sens": sens}[a.mode](a)


if __name__ == "__main__":
    main()
