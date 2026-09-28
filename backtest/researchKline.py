# -*- coding: utf-8 -*-
"""K線 研究九、十二（V）、十三、十四 重跑（稽核 seq3 §八；裁定 seq258 §二、seq262 §四 3）。回測線，2026-09-28。
定義出處：信箱附件「附件-K線研究九十二十三十四_機器定義原文摘錄_裁定線-20260928.md」（K線分析線原文摘錄）；K線 研究十「被取代」不重跑。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchKline [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchKline_check.py

═══ 改動（裁定 seq262 §四 3）與本線讀法（⭐ 看數字前寫定）═══
  K1 價格：還原價（data.load_stock，main 快照 edc6f）；原件是未還原價＋「疑似公司行動日」剔除 ⇒ 改用回測現行剔除窗：
     [窗起點, T＋H] 內有硬斷點（價格斷點或連續 ≥ 5 日無 K 棒；下市者最後成交後的缺日不算）⇒ 剔除（researchH2.brk 同式）；
     窗起點：研究九 ＝ 第一個局部點（P1／L1）；研究十二、十三、十四 ＝ T−120（回看量用到 120 根）
  K2 母體 gate3（含已下市）；判定窗 2017-03-02～2026-08-24（本線單筆層現行窗）；T ∈ [窗起點, 窗尾 − H]；幾何一律在有效 K 棒上數
  K3 天數 H ∈ {5, 10, 20, 60}（交易日曆）；報酬 R_H ＝ 收盤(T＋H，無成交 ⇒ 之前最後收盤) ÷ 收盤(T) − 1（原件「進場＝T 收盤」；研究十四 X1 從自己的進場日算）
  K4 基準①（原件「同母體同期隨便一天」）＝ T 日有收盤的全部 gate3 股票同式 R_H 的等權平均；基準② ＝ T 日近 20 日報酬十分位同格、[T, T＋H] 無硬斷點、非本股 的控制組 R_H 平均
  K5 扣成本版：個股 0.585%，只有動手的一側付（判定量往不利方向移）；兩組相減的判定量（研究十二 V 對無 V、研究十三 有對無、研究十四 X1 對 X0）成本相消 ⇒ 另報「動手那組 − 0.585%」
  K6 「局部高／低點」鄰域原文沒給 ⇒ ⭐ 本線定 k＝5（左右各 5 根有效 K 棒嚴格最高／最低收盤；同 PREREGU、PREREGM、型態全量的擺動點慣例），⛔ 不掃；
     擺動點在 p＋5 收盤才確認 ⇒ T 只能用 p＋5 ≤ T 的點（不偷看）
  K7 研究九：三尊頭 ＝ 最近三個已確認局部高點 P1<P2<P3 都在 [T−59, T]；A 空方 ⇒ 有利方向是負（「報酬取負」），判定量照報 X、測得出（−）才是有利；
     W 底 ＝ 最近兩個已確認局部低點 L1<L2 都在 [T−59, T]；T ＝ P3／L2 之後第一個符合的收盤；同檔同型態 20 日內取第一筆
  K8 研究十二：G1 當日漲 ≥ 7%（對前一根收盤）、G2 收盤 ＞ MA60、G3 成交額 ≥ 前 20 根均額 × 2；E 近 20 根漲幅 ＜ 15%；V 前 21～60 根均額 ≤ 前 61～120 根均額 × 0.8；
     判定量 D ＝ G＋E 事件中「有 V − 無 V」的 X 差（兩組迴歸、月分群）；同檔 20 日去重（在 G＋E 上）；MA100 版 ⛔ 不跑（只報主版）
  K9 研究十三：B ＝ 當日漲 ≥ 7% ＋ 收盤 ＞ MA60（暖身 ≥ 500 根）；⭐「收紅」讀法 ＝ 紅 K（收盤 ＞ 開盤，台股 K 棒顏色慣例）；R2／R3 ＝ T 起往回 2／3 根都紅；
     T ＝ [T−120, T−21] 收盤區間（最高÷最低 − 1）≤ 30%；S ＝ [T−499, T] 內有某根 20 日漲 ≥ 50%；W ＝ 收盤 ≥ 近 60 根最低 ＋ 區間 × 0.5；
     每個條件 D ＝ B 事件中「有 − 無」；同檔 20 日去重（在 B 上，回測現行）
  K10 研究十四：B 同研究十三；X0 ＝ T 收盤進；X1 ＝ T＋1～T＋6（有效 K 棒）第一個「收盤 ＜ 前一根收盤 且 成交額 ＜ 訊號日成交額」那根收盤進；
      找到之前（含當根）任一根最低 ＜ 訊號日最低 ⇒ 放棄；6 根內等不到 ⇒ 放棄；判定量 D ＝ 執行組「X1 − X0」配對差；必報放棄組在 X0 下的 X；
      另報「X1 執行組的 X」對「X0 全部的 X」（不配對，原件「照規則做 vs 當天追」口徑）⇒ 配對差只回答「同一批執行的，等一下有沒有比較便宜」
  K11 統計：月分群 CR0 SE（T 曆月）；n_eff ＝ min(事件數, H 日區段數)（兩組件取兩組較小者）；< 30 出口①、30～99 ②、≥ 100 ③；95% CI
      「穩」照 seq253 收緊讀法；引用一律寫「K線 研究X」
  K12 stop_force、t1_censor：單筆層、無組合權益 ⇒ 不適用（寫明）
輸出 backtest/resultsKline/：cells.csv、events.csv.gz、summary.json、REPORT.md、run.log
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                                  # 快照、gate3、硬斷點（researchH2.brk）
import researchM_freq as RF                              # _g5（delist on）

D, TR, UG = H2.D, H2.TR, H2.UG
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsKline")
HS = (5, 10, 20, 60)
COST = 0.00585
K_PIV = 5
MERGE = 20
_G: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def pivots(x, k, high=True):
    """有效 K 棒序列上嚴格局部極值（左右各 k 根）。"""
    n = len(x); out = np.zeros(n, bool)
    for i in range(k, n - k):
        w = x[i - k:i + k + 1]
        if not np.isfinite(w).all():
            continue
        others = np.delete(w, k)
        out[i] = (x[i] > others.max()) if high else (x[i] < others.min())
    return np.flatnonzero(out)


def dedup(Ts, merge=MERGE):
    keep = []; last = -10 ** 9
    for t in Ts:
        if t - last > merge:
            keep.append(t); last = t
    return keep


def one(args):
    sid, market = args
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 30:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    S = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    cb, ob, lb, ab = c[bars], o[bars], l[bars], amt[bars]
    nb = len(bars)
    ev = []
    wlast = w1 - min(HS)

    def inwin(t):
        return w0 <= bars[t] <= wlast
    # ── K線 研究九
    PH = pivots(cb, K_PIV, True); PL = pivots(cb, K_PIV, False)
    for typ, P_ in (("九A三尊頭", PH), ("九B W底", PL)):
        cand = []
        for t in range(nb):
            if not inwin(t):
                continue
            conf = P_[P_ + K_PIV <= t]
            need = 3 if typ.startswith("九A") else 2
            if len(conf) < need:
                continue
            pts = conf[-need:]
            if pts[0] < t - 59:
                continue
            if typ.startswith("九A"):
                p1, p2, p3 = pts
                if not (cb[p2] > cb[p1] and cb[p2] > cb[p3] and abs(cb[p1] - cb[p3]) / cb[p2] <= 0.05):
                    continue
                v1 = cb[p1:p2 + 1].min(); v2 = cb[p2:p3 + 1].min(); neck = (v1 + v2) / 2
                if (cb[p2] - neck) / neck < 0.10:
                    continue
                if cb[t] < neck and t > p3 and not (cb[p3 + 1:t] < neck).any():
                    cand.append((t, p1))
            else:
                l1, l2 = pts
                if abs(cb[l1] - cb[l2]) / cb[l1] > 0.05:
                    continue
                A = cb[l1:l2 + 1].max(); mn = min(cb[l1], cb[l2])
                if (A - mn) / mn < 0.10:
                    continue
                if cb[t] > A and t > l2 and not (cb[l2 + 1:t] > A).any():
                    cand.append((t, l1))
        last = -10 ** 9
        for t, f in cand:
            if bars[t] - last > MERGE:
                ev.append({"研究": typ, "T": int(bars[t]), "first": int(bars[f])}); last = bars[t]
    # ── 共用序列（有效 K 棒）
    ret1 = np.full(nb, np.nan); ret1[1:] = cb[1:] / cb[:-1] - 1
    ma60 = pd.Series(cb).rolling(60, min_periods=60).mean().to_numpy()
    am20 = pd.Series(ab).shift(1).rolling(20, min_periods=20).mean().to_numpy()
    r20b = np.full(nb, np.nan); r20b[20:] = cb[20:] / cb[:-20] - 1
    m_21_60 = pd.Series(ab).shift(21).rolling(40, min_periods=40).mean().to_numpy()
    m_61_120 = pd.Series(ab).shift(61).rolling(60, min_periods=60).mean().to_numpy()
    red = cb > ob
    # ── K線 研究十二（G＋E 事件；V 標記）
    ge = [t for t in range(nb) if inwin(t) and ret1[t] >= 0.07 and cb[t] > ma60[t] and np.isfinite(am20[t]) and ab[t] >= 2 * am20[t] and r20b[t] < 0.15]
    for t in dedup(ge):
        if not (np.isfinite(m_21_60[t]) and np.isfinite(m_61_120[t])):
            continue
        ev.append({"研究": "十二", "T": int(bars[t]), "first": int(bars[max(0, t - 120)]), "V": bool(m_21_60[t] <= 0.8 * m_61_120[t])})
    # ── K線 研究十三／十四（基準組 B）
    B = [t for t in range(nb) if inwin(t) and t >= 500 and ret1[t] >= 0.07 and cb[t] > ma60[t]]
    r20all = r20b
    for t in dedup(B):
        seg = cb[t - 120:t - 20]
        T_ = (seg.max() / seg.min() - 1) <= 0.30
        S_ = bool((r20all[max(20, t - 499):t + 1] >= 0.5).any())
        w60 = cb[t - 59:t + 1]; W_ = cb[t] >= w60.min() + 0.5 * (w60.max() - w60.min())
        e = {"研究": "十三", "T": int(bars[t]), "first": int(bars[t - 120]), "R2": bool(red[t] and red[t - 1]), "R3": bool(red[t] and red[t - 1] and red[t - 2]),
             "Tc": bool(T_), "S": S_, "W": bool(W_)}
        ev.append(e)
        # 研究十四：X1
        j_ = None; why = "6日等不到"
        for j in range(t + 1, min(t + 7, nb)):
            if lb[j] < lb[t]:
                why = "跌破訊號日最低"; break
            if cb[j] < cb[j - 1] and ab[j] < ab[t]:
                j_ = j; why = "執行"; break
        ev.append({"研究": "十四", "T": int(bars[t]), "first": int(bars[t - 120]), "X1": int(bars[j_]) if j_ is not None else -1, "結局": why})
    return {"sid": sid, "c": c, "valid": valid, "S": S, "ev": ev}


def brk(S, a, b):
    return H2.brk(S, a, b)


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = float(x.mean()); d = x - m
    keys, inv = np.unique(np.asarray(g), return_inverse=True); s = np.zeros(len(keys)); np.add.at(s, inv, d)
    return m, float(np.sqrt((s ** 2).sum()) / n)


def reg2(y, grp, cl):
    """y ＝ α ＋ β·grp（CR0 分群）⇒ β、SE。"""
    X = np.column_stack([np.ones(len(y)), grp.astype(float)])
    Xi = np.linalg.inv(X.T @ X); b = Xi @ X.T @ y; u = y - X @ b
    meat = np.zeros((2, 2))
    for c_ in np.unique(cl):
        m_ = cl == c_; s_ = X[m_].T @ u[m_]; meat += np.outer(s_, s_)
    V = Xi @ meat @ Xi
    return float(b[1]), float(np.sqrt(V[1, 1]))


def exres(m, lo, hi, neff):
    ex = "出口①" if neff < 30 else ("出口②" if neff < 100 else "出口③")
    rs = "—" if ex == "出口①" else ("結果①（測不出）" if lo <= 0 <= hi else ("結果②（測得出（＋））" if m > 0 else "結果③（測得出（−））"))
    return ex, rs


def main():
    global LOGF
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    t00 = time.time()
    log(f"===== researchKline {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜k＝{K_PIV}｜H {HS} =====")
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(H2.W0))); w1 = int(cal.searchsorted(pd.Timestamp(H2.W1)))
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    _G.update(cal=cal, w0=w0, w1=w1, off=TR.load_official())
    with Pool(a.procs) as pool:
        res = [r for r in pool.map(one, list(zip(U["stock_id"], U["market"])), chunksize=8) if r is not None]
    sids = [r["sid"] for r in res]; ix = {s: i for i, s in enumerate(sids)}
    C = np.column_stack([np.where(r["valid"], r["c"], np.nan) for r in res])
    CFF = np.column_stack([pd.Series(r["c"]).ffill().to_numpy() for r in res])
    VAL = np.column_stack([r["valid"] for r in res])
    PB = np.column_stack([r["S"]["cs_pb"] for r in res]); G5 = np.column_stack([r["S"]["cs_g5"] for r in res])
    R20 = np.full((n, len(sids)), np.nan)
    for i, r in enumerate(res):
        b = np.flatnonzero(r["valid"]); cc = r["c"][b]
        if len(b) > 20:
            R20[b[20:], i] = cc[20:] / cc[:-20] - 1
    log(f"[讀檔＋事件] {len(res)} 檔｜{time.time() - t00:.0f}s")
    EV = pd.DataFrame([dict(e, sid=r["sid"]) for r in res for e in r["ev"]])
    SS = {r["sid"]: r["S"] for r in res}
    rows = []
    RH = {}; EWc = {}; HBm = {}
    for H in HS:
        rh = np.full((n, len(sids)), np.nan); rh[:n - H] = CFF[H:] / C[:n - H] - 1
        RH[H] = rh
        with np.errstate(invalid="ignore"):
            EWc[H] = np.where(np.isfinite(rh).sum(1) > 0, np.nansum(rh, 1) / np.maximum(np.isfinite(rh).sum(1), 1), np.nan)
        Tr = np.arange(n - H)
        pbc = PB[Tr + H] - np.where(Tr[:, None] > 0, PB[np.maximum(Tr - 1, 0)], 0)
        g5c = np.where((Tr + H >= Tr + 4)[:, None], G5[Tr + H] - G5[Tr + 3], 0)
        hb = np.ones((n, len(sids)), bool); hb[:n - H] = (pbc > 0) | (g5c > 0)
        HBm[H] = hb
    DEC = {}

    def dec_at(T):
        if T not in DEC:
            v = R20[T].copy(); v[~VAL[T]] = np.nan
            d = np.full(len(v), -1); ok = np.flatnonzero(np.isfinite(v))
            if len(ok):
                order = ok[np.lexsort((ok, v[ok]))]; d[order] = (np.arange(len(ok)) * 10) // len(ok)
            DEC[T] = d
        return DEC[T]

    def xvals(sub, H, tcol="T"):
        """每事件（sid, T＝進場日）⇒ R、X1（基準①）、X2（基準②）、保留旗標（窗尾、硬斷點）。"""
        out = []
        for s, T, f in zip(sub["sid"], sub[tcol], sub["first"]):
            T = int(T)
            if T < 0 or T + H > w1 or brk(SS[s], int(f), T + H):
                out.append((np.nan, np.nan, np.nan)); continue
            i = ix[s]; r = RH[H][T, i]
            if not np.isfinite(r):
                out.append((np.nan, np.nan, np.nan)); continue
            dq = dec_at(T)
            x2 = np.nan
            if dq[i] >= 0:
                cm = (dq == dq[i]) & ~HBm[H][T] & np.isfinite(RH[H][T]); cm[i] = False
                if cm.any():
                    x2 = r - float(RH[H][T, cm].mean())
            out.append((r, r - EWc[H][T], x2))
        return np.array(out, float)

    def one_group(x, T, H, sh=0.0):
        ok = np.isfinite(x); x = x[ok] + sh; T = np.asarray(T)[ok]
        if len(x) < 2:
            return {"n": int(len(x)), "n_eff": 0, "平均": np.nan, "lo": np.nan, "hi": np.nan, "出口": "出口①", "結果": "—"}
        m, se = cr0(x, [str(cal[t])[:7] for t in T]); neff = int(min(len(x), len(set(((T - w0) // H).tolist()))))
        ex, rs = exres(m, m - 1.96 * se, m + 1.96 * se, neff)
        return {"n": int(len(x)), "n_eff": neff, "平均": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se, "出口": ex, "結果": rs}

    def two_group(x, g, T, H):
        ok = np.isfinite(x); x, g, T = x[ok], np.asarray(g)[ok].astype(bool), np.asarray(T)[ok]
        if g.sum() < 2 or (~g).sum() < 2:
            return {"D": np.nan, "lo": np.nan, "hi": np.nan, "n_eff": 0, "出口": "出口①", "結果": "—", "n有": int(g.sum()), "n無": int((~g).sum())}
        b, se = reg2(x, g, np.array([str(cal[t])[:7] for t in T]))
        neff = int(min(min(int(g.sum()), len(set(((T[g] - w0) // H).tolist()))), min(int((~g).sum()), len(set(((T[~g] - w0) // H).tolist())))))
        ex, rs = exres(b, b - 1.96 * se, b + 1.96 * se, neff)
        return {"D": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "n_eff": neff, "出口": ex, "結果": rs, "n有": int(g.sum()), "n無": int((~g).sum())}

    for H in HS:
        # 研究九
        for typ in ("九A三尊頭", "九B W底"):
            sub = EV[EV["研究"] == typ]
            xv = xvals(sub, H); T = sub["T"].to_numpy()
            for bn, col in (("基準①", 1), ("基準②", 2)):
                g0 = one_group(xv[:, col], T, H)
                sh = COST if typ.startswith("九A") else -COST          # 空方：有利方向是負 ⇒ 扣成本往 ＋ 移
                gc = one_group(xv[:, col], T, H, sh)
                rows.append({"研究": "K線 研究九", "格": typ, "H": H, "基準": bn, "量": "X", **{f"毛_{k}": v for k, v in g0.items()}, **{f"扣_{k}": v for k, v in gc.items()}})
        # 研究十二
        sub = EV[EV["研究"] == "十二"]; xv = xvals(sub, H); T = sub["T"].to_numpy(); gV = sub["V"].to_numpy(bool)
        for bn, col in (("基準①", 1), ("基準②", 2)):
            d = two_group(xv[:, col], gV, T, H)
            gc = one_group(np.where(gV, xv[:, col], np.nan), T, H, -COST)
            rows.append({"研究": "K線 研究十二", "格": "V 有 − 無（G＋E）", "H": H, "基準": bn, "量": "D", **{f"毛_{k}": v for k, v in d.items()},
                         **{f"扣_{k}": v for k, v in gc.items()}, "扣_註": "有 V 組 X − 0.585%"})
        # 研究十三
        sub = EV[EV["研究"] == "十三"]; xv = xvals(sub, H); T = sub["T"].to_numpy()
        for cnd in ("R2", "R3", "Tc", "S", "W"):
            g = sub[cnd].to_numpy(bool)
            for bn, col in (("基準①", 1), ("基準②", 2)):
                d = two_group(xv[:, col], g, T, H)
                gc = one_group(np.where(g, xv[:, col], np.nan), T, H, -COST)
                rows.append({"研究": "K線 研究十三", "格": f"{cnd} 有 − 無（B）", "H": H, "基準": bn, "量": "D", **{f"毛_{k}": v for k, v in d.items()},
                             **{f"扣_{k}": v for k, v in gc.items()}, "扣_註": "有條件組 X − 0.585%"})
        # 研究十四
        sub = EV[EV["研究"] == "十四"]
        x0 = xvals(sub, H, "T"); x1 = xvals(sub.assign(T1=sub["X1"]), H, "T1"); T = sub["T"].to_numpy()
        exe = (sub["結局"] == "執行").to_numpy()
        for bn, col in (("基準①", 1), ("基準②", 2)):
            dd = np.where(exe, x1[:, col] - x0[:, col], np.nan)
            g0 = one_group(dd, T, H)
            gc = one_group(np.where(exe, x1[:, col], np.nan), T, H, -COST)
            rows.append({"研究": "K線 研究十四", "格": "X1 − X0（執行組配對）", "H": H, "基準": bn, "量": "D", **{f"毛_{k}": v for k, v in g0.items()},
                         **{f"扣_{k}": v for k, v in gc.items()}, "扣_註": "X1 執行組 X − 0.585%"})
            for why in ("跌破訊號日最低", "6日等不到"):
                gg = one_group(np.where((sub["結局"] == why).to_numpy(), x0[:, col], np.nan), T, H)
                rows.append({"研究": "K線 研究十四", "格": f"放棄組（{why}）在 X0 下", "H": H, "基準": bn, "量": "X", **{f"毛_{k}": v for k, v in gg.items()}})
            gx1 = np.where(exe, x1[:, col], np.nan)
            rows.append({"研究": "K線 研究十四", "格": "X1 執行組（等拉回，從自己的進場日算）", "H": H, "基準": bn, "量": "X", **{f"毛_{k}": v for k, v in one_group(gx1, T, H).items()},
                         **{f"扣_{k}": v for k, v in one_group(gx1, T, H, -COST).items()}})
            g_all = one_group(x0[:, col], T, H)
            rows.append({"研究": "K線 研究十四", "格": "X0 全部（當天追）", "H": H, "基準": bn, "量": "X", **{f"毛_{k}": v for k, v in g_all.items()},
                         **{f"扣_{k}": v for k, v in one_group(x0[:, col], T, H, -COST).items()}})
        log(f"  [H{H}] {time.time() - t00:.0f}s")
    Tt = pd.DataFrame(rows); Tt.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    EV.to_csv(os.path.join(OUT, "events.csv.gz"), index=False)
    cnt = EV.groupby("研究").size().to_dict()
    S = {"件": "K線 研究九、十二（V）、十三、十四 重跑", "定義出處": "附件-K線研究九十二十三十四_機器定義原文摘錄_裁定線-20260928.md", "局部點鄰域 k": K_PIV,
         "事件數（去重後、窗內）": cnt, "十四 結局": EV[EV["研究"] == "十四"]["結局"].value_counts().to_dict(),
         "十二 V 比例": float(EV[EV["研究"] == "十二"]["V"].mean()) if "V" in EV else None, "秒": round(time.time() - t00)}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report()
    log(f"[完成] {time.time() - t00:.0f}s")


def _p(x, pct=True):
    return "—" if x is None or not np.isfinite(x) else (f"{x * 100:+.2f}%")


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    L_ = ["# K線 研究九、十二（V）、十三、十四 重跑（還原價、現行剔除窗、5／10／20／60 日、基準②、扣成本）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。稽核 seq3 §八；裁定 seq258 §二、seq262 §四 3。回測線。K線 研究十「被取代」不重跑。", ""]
    judged = T[(T["量"] == "D") | T["格"].str.startswith("九")]
    pos = judged[judged["毛_結果"].astype(str).str.startswith("結果②")]
    neg = judged[judged["毛_結果"].astype(str).str.startswith("結果③")]
    L_.append(f"**結論：{len(judged)} 個判定格（研究 × 格 × 天數 × 基準）裡，測得出（＋）{len(pos)} 格、測得出（−）{len(neg)} 格；"
              f"三尊頭（空方）的有利方向是（−）。事件數：{S['事件數（去重後、窗內）']}。逐格見下表與 cells.csv。**")
    L_ += ["", "| 研究 | 格 | H | 基準 | n／n_eff | 判定量〔95% CI〕 | 結果 | 扣 0.585% 的那組 〔CI〕 | 結果 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in T.to_dict("records"):
        m = r.get("毛_D") if r["量"] == "D" and pd.notna(r.get("毛_D")) else r.get("毛_平均")
        nn = f"{int(r['毛_n有'])}／{int(r['毛_n無'])}" if pd.notna(r.get("毛_n有")) else (f"{int(r['毛_n'])}" if pd.notna(r.get("毛_n")) else "—")
        L_.append(f"| {r['研究']} | {r['格']} | {r['H']} | {r['基準']} | {nn}／{int(r['毛_n_eff']) if pd.notna(r.get('毛_n_eff')) else '—'} | "
                  f"{_p(m)}〔{_p(r.get('毛_lo'))}, {_p(r.get('毛_hi'))}〕 | {r.get('毛_出口', '')} {r.get('毛_結果', '')} | "
                  f"{_p(r.get('扣_平均'))}〔{_p(r.get('扣_lo'))}, {_p(r.get('扣_hi'))}〕 | {r.get('扣_結果', '') if pd.notna(r.get('扣_結果')) else '—'} |")
    L_ += ["", "## 讀法", "", "- 見本檔程式開頭 K1～K12（還原價、剔除窗、k＝5、收紅＝紅 K、判定窗 2017-03-02～2026-08-24、T 收盤進場、兩組相減時成本相消）",
           f"- 研究十四 結局：{S['十四 結局']}；研究十二 G＋E 中有 V 的比例 {S['十二 V 比例']:.3f}" if S.get("十二 V 比例") is not None else "", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L_) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report()
    else:
        main()
