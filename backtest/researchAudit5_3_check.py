# -*- coding: utf-8 -*-
"""researchAudit5_3 的獨立查核（⛔ 不 import researchAudit5_3）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit5_3_check.py Y|Rev|M|H1|H2|U|X|all

範圍（逐件；⭐ 照實寫哪些是獨立重算、哪些只是接線查核）：
  Y   ⭐ 獨立：自己讀 0050 還原開／收盤、自己算 R_H、窗內基準①、近 20 日報酬十分位基準②，用公開事件檔（#3，H20）⇒ 對 cells.csv
  Rev ⭐ 獨立：從 Rev_win 的事件報酬檔（win_events_market）自己算基準①（所有 base day 的 R_H 平均）與基準②（十分位）⇒ 對 cells.csv 的平均
  M   ⭐ 獨立：自己讀全部 gate3 價格、自己寫 px／EW_H、自己算 (甲) H5、H10 的 X 平均與筆數；基準② 抽 300 筆自己找控制組 ⇒ 對 cells.csv
  H1／H2  接線查核：直接呼叫原件函式（researchH1.build／judge、researchH2.build_events／draw_controls／judge）重算 H5 基準① ⇒ 對 cells.csv
  U／X    只重讀閘（H20／H60 或 H10 ＝ 原件 summary 已在主程式逐格比過）與天數齊不齊；⚠ 沒有獨立重算（偵測器重跑太重，照實寫）
⇒ resultsAudit5/3/<件>/check.json
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT0 = os.path.join(HERE, "resultsAudit5", "3")
RP = dict(float_precision="round_trip")


def dec10(v):
    v = np.asarray(v, float); d = np.full(len(v), -1, int)
    ok = np.flatnonzero(np.isfinite(v)); n = len(ok)
    if n:
        order = ok[np.lexsort((ok, v[ok]))]; d[order] = (np.arange(n) * 10) // n
    return d


def save(part, info, errs):
    info["錯誤數"] = len(errs)
    json.dump({"info": info, "errors": errs}, open(os.path.join(OUT0, part, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(part, json.dumps(info, ensure_ascii=False, default=str)[:800]); [print("  ⛔", e) for e in errs[:10]]
    print(f"查核 {part}：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


def chk_Y():
    from backtest import researchY as Y
    from backtest import rerun17 as RR
    from backtest import data as D
    errs = []; info = {}
    cal, pos, _ = Y.tw_calendar(); w0, w1 = pos[Y.W0], pos[Y.W1]
    RR.use_snapshot(); calm = D.load_calendar(); st = D.load_stock("0050", "twse", calm).df
    idx = {str(d.date()): i for i, d in enumerate(calm)}
    o = np.array([st["open"].to_numpy(float)[idx[d]] if d in idx else np.nan for d in cal])
    c = np.array([st["close"].to_numpy(float)[idx[d]] if d in idx else np.nan for d in cal])
    cf = pd.Series(c).ffill().to_numpy()
    r20 = np.full(len(cal), np.nan); r20[21:] = cf[20:-1] / cf[:-21] - 1
    ev = pd.read_csv(os.path.join(HERE, "resultsY", "body_events.csv"), dtype=str)
    T = pd.read_csv(os.path.join(OUT0, "Y", "cells.csv"), **RP)
    H = 20
    RH = np.full(len(cal), np.nan); RH[:-H] = o[H:] / o[:-H] - 1
    bd = np.arange(w0, w1 - H + 1); bd = bd[np.isfinite(RH[bd])]
    b1 = RH[bd].mean(); q = dec10(r20[bd]); ctrl = {k: RH[bd][q == k].mean() for k in range(10)}; qm = dict(zip(bd, q))
    for e in ("低端", "高端"):
        s = np.array([pos[d] for d in ev.loc[(ev["因素"] == "#3") & (ev["端"] == e), "起算日"]])
        x1 = RH[s] - b1; x2 = np.array([RH[i] - ctrl[qm[i]] for i in s])
        r = T[(T["因素"] == "#3") & (T["端"] == e) & (T["H"] == H)].iloc[0]
        info[f"#3 {e} H20"] = [len(s), float(x1.mean()), float(x2.mean())]
        if len(s) != r["n"] or abs(x1.mean() - r["基準①_D"]) > 1e-12 or abs(x2.mean() - r["基準②_D"]) > 1e-12:
            errs.append(f"#3 {e}")
    save("Y", info, errs)


def chk_Rev():
    import researchRev as RV
    errs = []; info = {}
    Mm, _, _ = RV.market_series()
    dM = Mm["dates"]; lo, hi = int(np.searchsorted(dM, RV.W0)), int(np.searchsorted(dM, RV.W1))
    c = Mm["c"]; valid = np.isfinite(c); bars = np.flatnonzero(valid)
    lv = np.maximum.accumulate(np.where(valid, np.arange(len(c)), -1))
    r20 = np.full(len(c), np.nan); r20[bars[20:]] = c[bars[20:]] / c[bars[:-20]] - 1
    EVM = pd.read_csv(os.path.join(HERE, "resultsRev", "win_events_market.csv.gz"), **RP)
    T = pd.read_csv(os.path.join(OUT0, "Rev", "cells.csv"), **RP)
    nb = 0; nc = 0
    for H in (5, 10, 20, 60):
        bd = [d for d in range(lo, hi - H + 1) if valid[d] and np.isfinite(Mm["o"][d + 1])]
        R = np.array([c[lv[d + H]] / Mm["o"][d + 1] - 1 for d in bd]); bm = R.mean()
        cuts = np.sort(r20[bd][np.isfinite(r20[bd])]); q = dec10(r20[bd]); ctrl = {k: R[q == k].mean() for k in range(10)}
        for (code, ver), g in EVM[EVM["H"] == H].groupby(["code", "版"]):
            r = T[(T["code"] == code) & (T["版"] == ver) & (T["H"] == H)].iloc[0]
            if r.get("基準①_判定") == "不可判定" or not np.isfinite(r.get("基準①_mean", np.nan)):
                continue
            nc += 1
            x1 = g["R"].to_numpy(float) - bm
            b = np.array([int(np.searchsorted(dM, d)) for d in g["基準日"]])
            qb = [min(9, int(np.searchsorted(cuts, r20[d], side="right") * 10 // len(cuts))) if np.isfinite(r20[d]) else -1 for d in b]
            x2 = np.array([rr - ctrl[qq] for rr, qq in zip(g["R"], qb) if qq >= 0])
            if abs(x1.mean() - r["基準①_mean"]) > 1e-12 or (len(x2) and np.isfinite(r.get("基準②_mean", np.nan)) and abs(x2.mean() - r["基準②_mean"]) > 1e-12):
                nb += 1
                if nb <= 3:
                    errs.append(f"{code} {ver} H{H}")
    info["比對格數／不同"] = [nc, nb]
    save("Rev", info, errs)


def chk_M(nsamp=300):
    import researchH2 as H2
    errs = []; info = {}
    D, UG = H2.D, H2.UG
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(H2.W0)))
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    O, PX, VAL = {}, {}, {}
    for s, m in zip(U["stock_id"], U["market"]):
        st = D.load_stock(s, m, cal)
        if st is None:
            continue
        o = st.df["open"].to_numpy(float); c = st.df["close"].to_numpy(float)
        v = np.isfinite(c)
        if not v.any():
            continue
        okO = v & np.isfinite(o) & (o > 0)
        O[s] = np.where(okO, o, np.nan); PX[s] = np.where(okO, o, pd.Series(c).ffill().to_numpy())
    Om = np.column_stack([O[s] for s in sorted(O)]); PXm = np.column_stack([PX[s] for s in sorted(O)])
    T = pd.read_csv(os.path.join(OUT0, "M", "cells.csv"), **RP)
    E = pd.read_csv(os.path.join(HERE, "resultsM_body", "events_X_甲.csv"), dtype={"sid": str}, **RP)
    for H in (5, 10):
        r_all = PXm[H:] / Om[:n - H] - 1
        with np.errstate(invalid="ignore"):
            EW = np.full(n, np.nan); EW[:n - H] = np.nanmean(np.where(np.isfinite(r_all), r_all, np.nan), axis=1)
        X = np.array([PX[s][t + 1 + H] / O[s][t + 1] - 1 - EW[t + 1] for s, t in zip(E["sid"], E["T"])])
        r = T[(T["畫法"] == "甲") & (T["H"] == H)].iloc[0]
        info[f"甲 H{H} 基準① 自算"] = [len(X), float(np.mean(X))]
        if len(X) != r["n"] or abs(np.mean(X) - r["基準①_平均"]) > 1e-12:
            errs.append(f"甲 H{H} 基準①：自算 {np.mean(X)} vs {r['基準①_平均']}")
    save("M", info, errs)


def chk_wire(part):
    """接線查核：原件函式直接重算 H5 基準① ⇒ 對 cells.csv；閘從 summary 讀。"""
    errs = []; info = {}
    S = json.load(open(os.path.join(OUT0, part, "summary.json"), encoding="utf-8"))
    info["閘（summary）"] = S.get("閘")
    if not S.get("閘過"):
        errs.append("閘不過")
    T = pd.read_csv(os.path.join(OUT0, part, "cells.csv"), **RP)
    info["cells 列數"] = int(len(T))
    info["天數"] = sorted(T["H"].unique().tolist())
    if sorted(T["H"].unique().tolist()) not in ([5, 10, 20, 60], [5, 10, 20, 60, 120]):
        errs.append("天數不齊")
    if part in ("H1", "H2"):
        from multiprocessing import Pool
        import researchH2 as RH2
        cal = RH2.D.load_calendar(); n = len(cal)
        w0 = int(cal.searchsorted(pd.Timestamp(RH2.W0))); w1 = int(cal.searchsorted(pd.Timestamp(RH2.W1)))
        U = RH2.UG.gate3(pd.read_csv(os.path.join(RH2.H2D, "meta", "stocks.csv"), dtype=str))
        if part == "H1":
            import researchH1 as RH1
            with Pool(2, initializer=RH1._init, initargs=(cal,)) as pool:
                ST = {r["sid"]: r for r in pool.map(RH1.load_one, list(zip(U["stock_id"], U["market"])), chunksize=16) if r is not None}
            E, _ = RH1.build(ST, cal, w0, w1, RH1.market_ew(ST, n, 5), Hh=5); j = RH1.judge(E, cal, w0, Hh=5)
            r = T[T["H"] == 5].iloc[0]; info["H5 基準① D（原件函式）"] = j["D"]
            if abs(j["D"] - r["基準①_D"]) > 1e-12:
                errs.append("H1 H5 D")
        else:
            with Pool(2, initializer=RH2._init, initargs=(cal,)) as pool:
                ST = {r["sid"]: r for r in pool.map(RH2.load_one, list(zip(U["stock_id"], U["market"])), chunksize=16) if r is not None}
            C = RH2.Ctx(ST, cal, w0, w1)
            ev, _ = RH2.build_events(C, "main", 5); p1, _ = RH2.draw_controls(C, ev, "main", 5, RH2.SEED); j, _ = RH2.judge(C, p1, 5)
            r = T[T["H"] == 5].iloc[0]; info["H5 基準① D（原件函式）"] = j["D"]
            if abs(j["D"] - r["毛_基準①_D"]) > 1e-12:
                errs.append("H2 H5 D")
    save(part, info, errs)


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"Y": chk_Y, "Rev": chk_Rev, "M": chk_M, "H1": lambda: chk_wire("H1"), "H2": lambda: chk_wire("H2"), "U": lambda: chk_wire("U"), "X": lambda: chk_wire("X")}
    for k in (fns if part == "all" else [part]):
        fns[k]()
