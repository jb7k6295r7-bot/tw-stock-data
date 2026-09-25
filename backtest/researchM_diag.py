# -*- coding: utf-8 -*-
"""PREREGM 本體：假訊號臂 30／30 的【診斷】（⛔ 不是判定、⛔ 不改任何登錄的臂；只查「基準有沒有算錯」與「偏離從哪來」）。
 D1 全部 gate3 股票日（d＝T+1 有效開盤、T 有效 K 棒、T ∈ 判定窗）的平均 X ⇒ 應 ≈ 0（每天 X 的橫斷面平均恆為 0 的必要條件）
 D2 同檔、【全窗】隨機抽（不限曆月）、同筆數 ⇒ 平均 X
 D3 同檔同曆月隨機抽，按「抽到的日子在真事件 T 之前／之後」分組 ⇒ 平均 X（曆月條件是否把月內走勢帶進來）
 D4 真事件股的「整個曆月」月內報酬（該月第一根收盤 → 最後一根收盤）與同月 gate3 等權的差 ⇒ 平均
 ⛔ D1～D4 都不經合併／剔除（只要求 T 有效、T+1 開盤有效）；種子 20260925。
"""
import os, sys, json
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D, UG = H2.D, H2.UG
import researchM as M

_G = {}


def _init(cal):
    _G["cal"] = cal


def ld(a):
    sid, mk = a
    st = D.load_stock(sid, mk, _G["cal"])
    if st is None:
        return None
    o = st.df["open"].to_numpy(float); c = st.df["close"].to_numpy(float)
    v = np.isfinite(c)
    if not v.any():
        return None
    okO = v & np.isfinite(o) & (o > 0)
    px = np.where(okO, o, pd.Series(c).ffill().to_numpy())
    return sid, o, c, v, okO, px


def main():
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(H2.W0))); w1 = int(cal.searchsorted(pd.Timestamp(H2.W1))); wE = w1 - 21
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    with Pool(2, initializer=_init, initargs=(cal,)) as p:
        res = [r for r in p.map(ld, list(zip(U["stock_id"], U["market"])), chunksize=16) if r]
    sids = [r[0] for r in res]; si = {s: i for i, s in enumerate(sids)}
    O = np.column_stack([r[1] for r in res]); C = np.column_stack([r[2] for r in res]); V = np.column_stack([r[3] for r in res])
    OK = np.column_stack([r[4] for r in res]); PX = np.column_stack([r[5] for r in res])
    EW = M.ew_open(O, OK, PX, 20)
    G = np.full((n, len(sids)), np.nan)
    G[:n - 21] = PX[21:] / np.where(OK[1:n - 20], O[1:n - 20], np.nan) - 1.0      # 以 T 為列：px(T+21)／open(T+1) − 1
    Xm = np.full((n, len(sids)), np.nan)
    Xm[:n - 21] = G[:n - 21] - EW[1:n - 20][:, None]
    elig = V.copy(); elig[:w0] = False; elig[wE + 1:] = False
    Xe = np.where(elig, Xm, np.nan)
    out = {"D1_全部股票日平均X": float(np.nanmean(Xe)), "D1_股票日數": int(np.isfinite(Xe).sum()),
           "D1_逐日橫斷面平均X_的最大絕對值": float(np.nanmax(np.abs(np.nanmean(Xe, axis=1)[w0:wE + 1])))}
    rng = np.random.default_rng(20260925)
    MON = np.array([str(d)[:7] for d in cal])
    for m in M.MAIN:
        E = pd.read_csv(os.path.join(M.OUT, "events_X_{}.csv".format(m)), dtype={"sid": str})
        E["mon"] = MON[E["T"].to_numpy()]
        # D2 全窗隨機
        xs = []
        for s, k in E["sid"].value_counts().items():
            j = si[s]; days = np.flatnonzero(np.isfinite(Xe[:, j]))
            if len(days) == 0:
                continue
            pick = rng.choice(days, size=min(k, len(days)), replace=False)
            xs.extend(Xe[pick, j].tolist())
        # D3 同檔同月，按在真 T 之前／之後
        pre, post, same = [], [], []
        for (s, mo), g in E.groupby(["sid", "mon"]):
            j = si[s]; Ts = g["T"].to_numpy()
            b = np.flatnonzero(V[:, j]); b = b[(b >= w0) & (b <= wE)]
            b = b[MON[b] == mo]
            for t in b:
                x = Xe[t, j]
                if not np.isfinite(x):
                    continue
                if t < Ts.min():
                    pre.append(x)
                elif t in Ts:
                    same.append(x)
                else:
                    post.append(x)
        # D4 事件股整月月內報酬 − 同月 gate3 等權月內報酬
        mr = []
        mons = pd.Series([str(d)[:7] for d in cal])
        first = mons.groupby(mons).apply(lambda s: s.index.min()); last = mons.groupby(mons).apply(lambda s: s.index.max())
        Cf = pd.DataFrame(C).ffill().to_numpy()
        cache = {}
        for (s, mo) in sorted(set(zip(E["sid"], E["mon"]))):
            a, b_ = int(first[mo]), int(last[mo])
            if mo not in cache:
                ok = V[a] & np.isfinite(Cf[b_])
                cache[mo] = float(np.nanmean(Cf[b_][ok] / C[a][ok] - 1))
            j = si[s]
            if V[a, j] and np.isfinite(Cf[b_, j]):
                mr.append(Cf[b_, j] / C[a, j] - 1 - cache[mo])
        out[m] = {"真事件_平均X": float(E["X"].mean()), "D2_同檔全窗隨機_平均X": float(np.mean(xs)), "D2_n": len(xs),
                  "D3_同檔同月_真T之前的日子_平均X": float(np.mean(pre)), "D3_n前": len(pre),
                  "D3_同檔同月_真T當天_平均X": float(np.mean(same)), "D3_n當天": len(same),
                  "D3_同檔同月_真T之後的日子_平均X": float(np.mean(post)), "D3_n後": len(post),
                  "D4_事件股該月月內報酬減同月等權_平均": float(np.mean(mr)), "D4_n": len(mr)}
        print(m, json.dumps(out[m], ensure_ascii=False), flush=True)
    print(json.dumps({k: v for k, v in out.items() if k.startswith("D1")}, ensure_ascii=False))
    json.dump(out, open(os.path.join(M.OUT, "diag_fake.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
