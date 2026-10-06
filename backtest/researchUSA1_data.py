# -*- coding: utf-8 -*-
"""USREG-A1-1～5（美股大盤／ETF 類五件）共用：資料讀取、合成 2 倍、引擎、績效。⛔ 本檔不算任何策略。

登錄：美股策略線 USREG-A1 seq1（sha 4d6b82a0d0fe84c3，正文）＋seq2（cea9cc6132c26f2f，QLD 改正式選項）＋seq3（2f26cfea3035d3a7，早年合成公式）；
裁定 seq308 §三§四、seq309、seq311 §二、seq313 §二。
⛔⛔ 授權：us-stock-data 是私有庫 ⇒ 本檔只【讀】快照 ~/usdata/60d2f99（git archive，唯讀）；任何逐日價格、權益曲線、逐筆事件只放 ~/us_work/usa1/（repo 外）。

══ 讀法（執行者補，⭐ 2026-10-07 台北 02:30 寫死於看任何 A1 數字之前；登錄沒寫清楚的地方）══
 D1 資料 us-stock-data 60d2f999（含 A1 資料：QQQ、SSO、QLD、DTB3）；日曆 ＝ yahoo_GSPC 日期（us_data 同法），截到 2026-09-30（確認段末；⛔ 不用 10-01 之後的盤中列）。
 D2 價：Yahoo 還原 X ＝ 原始 X × adjclose ÷ close（us_data 同法；含息、含分割）。SPY 1993-01-29、QQQ 1999-03-10、SSO／QLD 2006-06-21 起。
    ^SP500TR：收盤 ＝ adjclose；開高低 ＝ ^GSPC 開高低 × (^SP500TR 收 ÷ ^GSPC 收)（同日比例，Yahoo 還原同法；^SP500TR 早年開＝收，不能當開盤價）。
 D3 判斷序列 J（「一律看 SPY 還原收盤」）：SPY 上市（1993-01-29）以後 ＝ SPY 還原 OHLC；以前 ＝ D2 的 ^SP500TR OHLC × (SPY 首日還原收 ÷ ^SP500TR 同日收)
    （比例接，報酬不變）⇒ 早年合成段 1990～1993-01 的「SPY」是指數代用（⚠ 未扣 SPY 費用 0.0945%），照標。
 D4 現金 ＝ 3 個月國庫券 DTB3（%，FRED 缺值 ⇒ 用前一個有值日；t 日現金報酬 ＝ DTB3_{t−1} ÷ 100 ÷ 252，按交易日計）；0% 版描述。
 D5 合成 2 倍（seq3 逐字）：r_L,t ＝ 2 r_idx,t − (DTB3_{t−1}/100 ＋ s)/252 − f/252；s ＝ 0.25%（主）／0、0.50%（描述）；f：SSO 0.89%、QLD 0.95%。
    r_idx：SSO 版 ＝ ^SP500TR 日報酬；QLD 版 ＝ QQQ 含息日報酬（seq313：1999-03～2006-06 用 QQQ 含息價；⚠ QQQ 自身含 0.20% 費用 ⇒ 合成 QLD 略被多扣）。
    合成開盤（台股 researchTri T9 同式）：L_o,t ＝ L_c,t−1 × (1 ＋ 2 (o_idx,t ÷ c_idx,t−1 − 1))（隔夜段不扣融資與費用，收盤一次扣）。
    ⛔ QQQ 上市前（1999-03-10）沒有 Nasdaq-100 總報酬 ⇒ QQQ／QLD 早年段只從 QQQ 可算之後起，之前「不可判定」；⛔ 不用 ^NDX 價格指數代。
    早年合成段全段用合成（含 2006-06～2007-03 已有真實 SSO／QLD 的部分，段內一致；逐字標「合成、非實際 ETF」）。
 D6 引擎 ＝ 台股 researchLev2.engine（t 開盤成交、換手 ½Σ|目標−現有| × 成本、窗首開盤建倉付一次成本、有一檔沒開盤 ⇒ 整筆延後、權重不變不成交）逐行移植，
    只把「現金每日 × 固定 cash_g」改成「× (1 ＋ cash_g[t])」（DTB3 逐日）；閘：cash_g 為常數時與 L2.engine 逐日相同（≤ 1e-12）。
    成本 0.05%（換手金額，美股裁定）；敏感度 0.02%、0.10%。
 D7 年化 ＝ 末值^(252 ÷ 段內交易日數) − 1（權益含 1.0 起點，L2.perf 同式、ANN 252 ＝ USREG-W1b 先例）；回落 ＝ 含 1.0 起點的路徑最大回落。
    基準 ^SP500TR 同窗 ＝ research13.window_stats 同式（第一天收盤起、年數 ＝ 天數 ÷ 252）。判準（seq141 同式）：條件一 年化 ＞ 基準（嚴格）；條件二 比值 ≥ 基準比值。
 D8 預扣稅 30% 版（描述）：淨日報酬 ＝ 價格報酬 ＋ 0.7 ×（總報酬 − 價格報酬）（USREG-W1b 同式）；價格報酬用 Yahoo close（已含分割、不含息）、^SP500TR 對 ^GSPC。
"""
from __future__ import annotations

import hashlib
import io
import os

import numpy as np
import pandas as pd

DATA_COMMIT = "60d2f9992a88dea9f7ac0bc2b64cecdf583db8b5"
ROOT = os.environ.get("US_DATA_ROOT_A1", os.path.expanduser("~/usdata/60d2f99"))
WORK = os.path.expanduser("~/us_work/usa1")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA1")
CAL_END = "2026-09-30"
ANN = 252
EXP = ("2007-04-02", "2021-12-31")
CONF = ("2022-01-03", "2026-09-30")
EARLY_END = "2007-03-30"
COST = 0.0005
COST_SENS = (0.0002, 0.0010)
SPREAD = 0.0025
SPREAD_SENS = (0.0, 0.005)
FEE = {"SSO": 0.0089, "QLD": 0.0095}
NET_DIV = 0.7
ETFS = ("SPY", "QQQ")
LEVS = ("SSO", "QLD")
SYN_TAG = "合成、非實際 ETF"
LIMITS_SP400 = ("⚠ 母體限制（資料庫線 1321、0245；裁定 seq308 §三）：S&P 400 名冊缺 70 檔（多為已下市）⇒ 存活者偏差、結果偏樂觀；"
                "名冊日期來自 Wikipedia 變動表、可能有數日誤差；S&P 500／400 面板 2015-12 起 ⇒ 個股層只能 2016 起")


def p_(*a):
    return os.path.join(ROOT, "data", *a)


def data_commit():
    return io.open(os.path.join(ROOT, ".commit"), encoding="utf-8").read().strip()


def assert_pinned():
    c = data_commit()
    if c != DATA_COMMIT:
        raise RuntimeError(f"資料 commit {c} ≠ 寫死的 {DATA_COMMIT}")
    return c


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 讀檔 ═════════════
def yahoo(name):
    d = pd.read_csv(p_("macro", f"yahoo_{name}.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close", "volume", "adjclose"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def fred(name):
    d = pd.read_csv(p_("macro", f"fred_{name}.csv"), dtype=str, keep_default_na=False)
    v = pd.to_numeric(d["value"].replace({"": None, ".": None}), errors="coerce")
    return pd.Series(v.to_numpy(float), index=d["date"].to_numpy(str))


def calendar():
    d = pd.read_csv(p_("macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)["date"]
    cal = np.array(sorted(x for x in d if x <= CAL_END))
    return cal


def _on_cal(s, cal):
    return np.array(s.reindex(cal).to_numpy(float), dtype=float, copy=True)


def load_market():
    """→ M：cal（字串陣列）、pos、各資產 O／H／L／C（還原；無列 ⇒ NaN）、RO／RH／RL／RC（原始）、V、NC／NO（預扣稅 30% 淨股息版）、
    J（判斷序列，D3）、dtb3（%，ffill）、cash_g（t 日現金報酬）、資料帳。"""
    cal = calendar(); n = len(cal)
    M = {"cal": cal, "pos": {d: i for i, d in enumerate(cal)}, "O": {}, "H": {}, "L": {}, "C": {}, "RO": {}, "RH": {}, "RL": {}, "RC": {}, "V": {},
         "NC": {}, "NO": {}, "audit": {}}
    for k in ("SPY", "QQQ", "SSO", "QLD"):
        y = yahoo(k)
        kf = y["adjclose"] / y["close"]
        raw = {c: _on_cal(y[c], cal) for c in ("open", "high", "low", "close", "volume")}
        adj = {c: _on_cal(y[c] * kf, cal) for c in ("open", "high", "low", "close")}
        bad = ~(np.isfinite(adj["open"]) & np.isfinite(adj["close"]) & (adj["open"] > 0) & (adj["close"] > 0))
        for c in ("open", "high", "low", "close"):
            adj[c][bad] = np.nan
        M["O"][k], M["H"][k], M["L"][k], M["C"][k] = adj["open"], adj["high"], adj["low"], adj["close"]
        M["RO"][k], M["RH"][k], M["RL"][k], M["RC"][k], M["V"][k] = raw["open"], raw["high"], raw["low"], raw["close"], raw["volume"]
        first = int(np.flatnonzero(np.isfinite(adj["close"]))[0])
        miss = int((~np.isfinite(adj["close"][first:])).sum())
        M["audit"][k] = {"首日": cal[first], "日曆內缺日（首日後）": miss, "非日曆日列": int(len(set(y.index) - set(cal) - {d for d in y.index if d > CAL_END}))}
        # 淨股息（D8）
        tr = adj["close"][1:] / adj["close"][:-1]; pr = raw["close"][1:] / raw["close"][:-1]
        nr = np.r_[np.nan, pr + NET_DIV * (tr - pr)]
        M["NC"][k], M["NO"][k] = _net_series(nr, adj["close"], raw["open"], raw["close"], first)
    # ^SP500TR（D2）
    tr = yahoo("SP500TR"); gs = yahoo("GSPC")
    c_tr = _on_cal(tr["adjclose"], cal); c_gs = _on_cal(gs["close"], cal)
    f = c_tr / c_gs
    M["C"]["TR"] = c_tr
    M["O"]["TR"], M["H"]["TR"], M["L"]["TR"] = _on_cal(gs["open"], cal) * f, _on_cal(gs["high"], cal) * f, _on_cal(gs["low"], cal) * f
    M["RO"]["TR"], M["RH"]["TR"], M["RL"]["TR"], M["RC"]["TR"] = (_on_cal(gs[c], cal) for c in ("open", "high", "low", "close"))
    M["V"]["TR"] = _on_cal(gs["volume"], cal)
    M["C"]["GSPC"] = c_gs
    trr = np.r_[np.nan, c_tr[1:] / c_tr[:-1]]; grr = np.r_[np.nan, c_gs[1:] / c_gs[:-1]]
    M["NC"]["TR"] = np.r_[c_tr[0], c_tr[0] * np.cumprod(grr[1:] + NET_DIV * (trr[1:] - grr[1:]))]
    M["audit"]["TR"] = {"首日": cal[0], "缺日": int((~np.isfinite(c_tr)).sum()), "GSPC缺日": int((~np.isfinite(c_gs)).sum()),
                        "^SP500TR 開＝收 的日數（1990～2006）": int(np.sum((_on_cal(tr["open"], cal) == c_tr)[:np.searchsorted(cal, "2007-01-01")]))}
    # J（D3）
    s0 = int(np.flatnonzero(np.isfinite(M["C"]["SPY"]))[0])
    k = M["C"]["SPY"][s0] / c_tr[s0]
    J = {}
    for nm in ("O", "H", "L", "C"):
        a = M[nm]["SPY"].copy(); a[:s0] = M[nm]["TR"][:s0] * k; J[nm] = a
    for nm in ("RO", "RH", "RL", "RC", "V"):
        a = M[nm]["SPY"].copy(); a[:s0] = M[nm]["TR"][:s0]; J[nm] = a
    for nm in J:
        M[nm]["J"] = J[nm]
    M["J_splice"] = {"SPY首日": cal[s0], "比例": float(k)}
    # DTB3（D4）
    r = fred("DTB3")
    r = r[r.index <= CAL_END]
    lv = pd.Series(r.to_numpy(), index=r.index).dropna()
    dt = pd.Series(lv.to_numpy(), index=lv.index).reindex(sorted(set(lv.index) | set(cal))).ffill().reindex(cal).to_numpy(float)
    M["dtb3"] = dt
    g = np.zeros(n); g[1:] = dt[:-1] / 100.0 / ANN
    M["cash_g"] = g
    have = set(lv.index)
    M["audit"]["DTB3"] = {"FRED 缺值列": int(r.isna().sum()), "日曆日無當日值（用前值）": int(sum(1 for d in cal if d not in have)),
                          "末筆": str(lv.index[-1])}
    return M


def _net_series(nr, adj_c, raw_o, raw_c, first):
    n = len(adj_c); NC = np.full(n, np.nan); NO = np.full(n, np.nan)
    cum = adj_c[first]
    NC[first] = cum
    for t in range(first + 1, n):
        x = nr[t]
        if np.isfinite(x):
            cum *= x
        NC[t] = cum if np.isfinite(adj_c[t]) else np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        NO = raw_o * (NC / raw_c)
    return NC, NO


def synth(M, kind, s=SPREAD):
    """D5 合成 2 倍 ⇒ (O, C) 日曆長度；kind ∈ {SSO, QLD}。"""
    idx = "TR" if kind == "SSO" else "QQQ"
    o, c = M["O"][idx], M["C"][idx]
    n = len(c); f = FEE[kind]
    Lc = np.full(n, np.nan); Lo = np.full(n, np.nan)
    st = int(np.flatnonzero(np.isfinite(c))[0])
    Lc[st] = 1.0
    dprev = np.r_[np.nan, M["dtb3"][:-1]]
    for t in range(st + 1, n):
        if not (np.isfinite(c[t]) and np.isfinite(c[t - 1])):
            Lc[t] = np.nan
            continue
        r = c[t] / c[t - 1] - 1.0
        Lc[t] = Lc[t - 1] * (1.0 + 2.0 * r - (dprev[t] / 100.0 + s) / ANN - f / ANN)
        Lo[t] = Lc[t - 1] * (1.0 + 2.0 * (o[t] / c[t - 1] - 1.0)) if np.isfinite(o[t]) else np.nan
    return Lo, Lc


# ═════════════ 引擎（D6）═════════════
def engine(o, c, W, R, cash_g, cost=COST, init_cost=True):
    """o、c：(n,k) 該段各資產開盤、收盤（收盤已 ffill）；W：(n,k) 目標權重（現金 ＝ 1 − 和）；R：(n,) 再平衡到期；cash_g：(n,) t 日現金報酬。
    逐行移植 researchLev2.engine（mode＝open），只有現金逐日報酬不同。"""
    n, k = W.shape
    u = np.zeros(k); cash = 1.0
    eq = np.empty(n); turn = np.zeros(n); cst = np.zeros(n)
    held = np.full((n, k), np.nan); exec_day = np.zeros(n, bool)
    tgt_held = None; pending = True; delay = 0
    with np.errstate(invalid="ignore", divide="ignore"):
        for t in range(n):
            if t > 0 and (R[t] or not np.array_equal(W[t], tgt_held)):
                pending = True
            if pending:
                need = (u > 0) | (W[t] > 0)
                if np.all(np.isfinite(o[t][need])):
                    px = o[t]
                    hold = np.where(u > 0, u * px, 0.0)
                    V = hold.sum() + cash
                    tgt = W[t] * V; tc = (1.0 - W[t].sum()) * V
                    tr = 0.5 * (np.abs(tgt - hold).sum() + abs(tc - cash))
                    cc = tr * cost if (t > 0 or init_cost) else 0.0
                    V2 = V - cc
                    u = np.where(W[t] > 0, W[t] * V2 / px, 0.0)
                    cash = (1.0 - W[t].sum()) * V2
                    turn[t] = tr; cst[t] = cc; exec_day[t] = True
                    tgt_held = W[t].copy(); pending = False
                else:
                    delay += 1
            if t > 0:
                cash *= 1.0 + cash_g[t]
            eq[t] = np.where(u > 0, u * c[t], 0.0).sum() + cash
            held[t] = tgt_held
    return {"eq": eq, "turn": turn, "cst": cst, "held": held, "exec": exec_day, "delay": delay}


def run(M, assets, W, i0, i1, R=None, cash=True, cost=COST, OC=None):
    """assets：名稱 tuple（M["O"]／M["C"] 的鍵，或 OC 給的 {名: (O, C)}）；W：(N,k) 全日曆或 (n,k) 段內。"""
    n = i1 - i0 + 1
    O = []; C = []
    for a in assets:
        if OC is not None and a in OC:
            oo, cc = OC[a]
        else:
            oo, cc = M["O"][a], M["C"][a]
        O.append(oo[i0:i1 + 1]); C.append(pd.Series(cc).ffill().to_numpy()[i0:i1 + 1])
    o = np.stack(O, 1); c = np.stack(C, 1)
    Wd = W[i0:i1 + 1] if len(W) != n else W
    g = M["cash_g"][i0:i1 + 1] if cash else np.zeros(n)
    return engine(o, c, Wd, np.zeros(n, bool) if R is None else R, g, cost=cost)


def perf(eq):
    n = len(eq)
    cagr = float(eq[-1]) ** (ANN / n) - 1.0
    path = np.concatenate([[1.0], eq]); pk = np.maximum.accumulate(path)
    return float(cagr), float(((path - pk) / pk).min())


def bench(series, i0, i1):
    seg = np.asarray(series[i0:i1 + 1], float)
    cagr = (seg[-1] / seg[0]) ** (ANN / len(seg)) - 1.0
    pk = np.maximum.accumulate(seg)
    return float(cagr), float(((seg - pk) / pk).min())


def ratio(c, m):
    return c / abs(m) if m < 0 else float("nan")


def label(c, m, cb, mb):
    k1 = c > cb; k2 = ratio(c, m) >= ratio(cb, mb)
    return "合格" if (k1 and k2) else ("另列" if k1 else "不合格")


def reb_mask(cal, i0, i1, freq):
    """窗內每年（Y）／每季（Q）／每月（M）第一個交易日；⛔ 窗首當天不算（researchLev2.reb_mask 同式＋月）。"""
    s = cal[i0:i1 + 1]
    key = np.array([x[:4] for x in s]) if freq == "Y" else (np.array([x[:4] + str((int(x[5:7]) - 1) // 3) for x in s]) if freq == "Q" else np.array([x[:7] for x in s]))
    out = np.zeros(len(s), bool); out[1:] = key[1:] != key[:-1]
    return out


def seg_idx(M, a, b):
    i0, i1 = M["pos"][a], M["pos"][b]
    return i0, i1


def dd_info(eq, cal, i0):
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p); dd = (p - pk) / pk; it = int(np.argmin(dd))
    ip = int(np.argmax(p[:it + 1])) if it > 0 else 0
    back = np.flatnonzero(p[it:] >= p[ip])
    return {"最大回落": float(dd.min()), "高點日": str(cal[i0 + ip - 1]) if ip > 0 else "起點", "谷底日": str(cal[i0 + it - 1]) if it > 0 else "起點",
            "100萬在高點_谷底剩（萬）": float((1 + dd.min()) * 100), "回到高點的交易日數": int(back[0]) if len(back) else "段內未回本"}


def year_window(eq, cal, i0, a, b):
    """100 萬在 a 前一交易日收盤（段首 ⇒ 1.0）⇒ [a, b] 內最大回落、期末、谷底。"""
    ia, ib = a - i0, b - i0
    base = eq[ia - 1] if ia > 0 else 1.0
    seg = np.r_[1.0, eq[ia:ib + 1] / base]
    pk = np.maximum.accumulate(seg); it = int(np.argmin(seg))
    return {"年內最大回落": float(((seg - pk) / pk).min()), "期末（萬）": float(seg[-1] * 100), "谷底剩（萬）": float(seg.min() * 100),
            "谷底日": str(cal[a + it - 1]) if it > 0 else "起點"}


def fixed_hold_path(on, H):
    """描述（seq308 §四③）：條件路徑 on（bool，t 日持有風險部位）⇒ 固定 H 日版：每次由 False→True 的進場日 e 起抱滿 H 天（[e, e+H−1]），
    期間內的新進場不算；到期後要等下一次「由 False→True」才再進。回 (路徑, 進場次數)。"""
    n = len(on); out = np.zeros(n, bool); t = 0; k = 0
    prev = False
    while t < n:
        if on[t] and not prev:
            e = t; out[e:e + H] = True; k += 1
            t = e + H
            prev = bool(on[t - 1]) if t - 1 < n else False
            continue
        prev = bool(on[t]); t += 1
    return out, k
