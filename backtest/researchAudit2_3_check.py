# -*- coding: utf-8 -*-
"""稽核 ② 3 上升趨勢線跌破 5／10／20／60 日＋基準② 獨立查核（⛔ 不 import researchAudit2_3、researchUT、researchM、avgdown、researchH2）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_3_check.py

共用只到資料層：backtest.data（快照讀檔、breakpoints）、tradability（one、delist_status、load_official）、universe_gate.gate3。其餘自寫：
 ① 每個視窗抽 300 筆：R_H、gate3 等權 EW_H(T＋1)、X ⇒ ＝ events.csv.gz
 ② 每個視窗抽 150 筆：配對母體（T 有效、T＋1 可買、[T, T＋1＋H] 無硬斷點、r20 與 R_H 可算）、十分位、ȳ ⇒ X2 ＝ events.csv.gz
 ③ 由 events.csv.gz 自算四個視窗 X、X2 的平均、月分群 CR0 CI、n_eff（H 日區段）、出口結果、K3 ⇒ ＝ summary.json
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
D.DATA = SNAP
OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/3")
W0, W1, WIN, COST = "2017-03-02", "2026-08-24", 2313, 0.00585
HS = (5, 10, 20, 60)


def g5(valid, upto):
    run = 0; out = np.zeros(len(valid), bool)
    for i, v in enumerate(valid):
        miss = (not v) and (upto is None or i <= upto)
        run = run + 1 if miss else 0
        out[i] = run >= 5
    return out


def main():
    cal = D.load_calendar(); n = len(cal)
    w0, w1 = int(cal.searchsorted(pd.Timestamp(W0))), int(cal.searchsorted(pd.Timestamp(W1)))
    U = UG.gate3(pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str))
    off = TR.load_official()
    sids, O, PX, OK, V, TB, CP, CG, R20 = [], [], [], [], [], [], [], [], []
    for sid, mk in zip(U["stock_id"], U["market"]):
        st = D.load_stock(sid, mk, cal)
        if st is None:
            continue
        o = st.df["open"].to_numpy(float); c = st.df["close"].to_numpy(float); v = np.isfinite(c)
        if not v.any():
            continue
        ok = v & np.isfinite(o) & (np.nan_to_num(o) > 0)
        cff = pd.Series(c).ffill().to_numpy()
        pb = np.zeros(n, bool)
        for b_ in D.breakpoints(st.df, st.event_dates):
            if b_["rule"] in ("price", "price+gap"):
                pb[b_["pos"]] = True
        tb = TR.one(sid, cal); ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
        up = ds["last"] if (ds is not None and ds["status"].startswith("delisted")) else None
        bars = np.flatnonzero(v); r = np.full(n, np.nan)
        if len(bars) > 20:
            r[bars[20:]] = c[bars[20:]] / c[bars[:-20]] - 1.0
        sids.append(sid); O.append(o); PX.append(np.where(ok, o, cff)); OK.append(ok); V.append(v)
        TB.append(np.asarray(tb["trd"], bool) & np.isfinite(o) & ~np.asarray(tb["up_o"], bool))
        CP.append(np.cumsum(pb)); CG.append(np.cumsum(g5(v, up))); R20.append(r)
    O, PX, OK, V, TB, CP, CG, R20 = (np.column_stack(z) for z in (O, PX, OK, V, TB, CP, CG, R20))
    ix = {s: i for i, s in enumerate(sids)}
    E = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES = {}; rng = np.random.default_rng(20260928)
    m1 = m2 = 0.0; nbad = 0
    for H in HS:
        e = E[E["H"] == H].reset_index(drop=True)
        for k in rng.choice(len(e), size=300, replace=False):
            T, s = int(e.at[k, "T"]), ix[e.at[k, "sid"]]
            g = PX[T + 1 + H, s] / O[T + 1, s] - 1.0
            okm = OK[T + 1]; rr = PX[T + 1 + H, okm] / O[T + 1, okm] - 1.0
            ew = float(np.nanmean(rr))
            m1 = max(m1, abs(g - e.at[k, "R"]), abs(g - ew - e.at[k, "X"]))
        for k in rng.choice(np.flatnonzero(e["X2"].notna().to_numpy()), size=150, replace=False):
            T, s = int(e.at[k, "T"]), ix[e.at[k, "sid"]]
            with np.errstate(invalid="ignore", divide="ignore"):
                G = PX[T + 1 + H] / np.where(OK[T + 1], O[T + 1], np.nan) - 1.0
            hb = ((CP[T + H + 1] - CP[T - 1]) > 0) | ((CG[T + H + 1] - CG[T + 3]) > 0)
            el = V[T] & TB[T + 1] & ~hb & np.isfinite(R20[T]) & np.isfinite(G)
            idx = np.flatnonzero(el); rv = R20[T, idx]
            order = idx[np.lexsort((idx, rv))]
            dec = np.full(len(sids), -1); dec[order] = (np.arange(len(idx)) * 10) // len(idx)
            peer = el & (dec == dec[s]); peer[s] = False
            x2 = (PX[T + 1 + H, s] / O[T + 1, s] - 1.0) - float(G[peer].mean())
            m2 = max(m2, abs(x2 - e.at[k, "X2"]))
            nbad += int(dec[s] < 0)
    RES["① 四視窗各 300 筆：R、EW、X"] = {"最大差": m1, "過": m1 <= 1e-12}
    RES["② 四視窗各 150 筆：基準② X2"] = {"最大差": m2, "事件股不在母體": nbad, "過": m2 <= 1e-12 and nbad == 0}
    print(RES, flush=True)
    bad = []
    for H in HS:
        e = E[E["H"] == H]
        for col, key in (("X", "X（對 gate3 等權，原件量）"), ("X2", "X2（基準②：前 20 日同十分位）")):
            x = e[col].to_numpy(float); T = e["T"].to_numpy(int); ok = np.isfinite(x); x, T = x[ok], T[ok]
            mon = np.array([str(cal[t])[:7] for t in T]); m = x.mean()
            s_ = pd.Series(x - m).groupby(mon).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(x)
            lo, hi = m - 1.96 * se, m + 1.96 * se
            nb = len(set(np.minimum((T - w0) // H, WIN // H - 1))); ne = min(len(x), nb)
            ex = "出口①" if ne < 30 else ("出口②" if ne < 100 else "出口③")
            rs = "結果①（測不出）" if lo <= 0 <= hi else ("結果②（測得出（＋））" if m > 0 else "結果③（測得出（−））")
            k3 = "可執行（CI 上緣 ＜ −0.585%）" if hi < -COST else "扣成本後不可執行"
            ref = Sm["結果"][f"H{H}"][key]
            if abs(m - ref["平均"]) > 1e-12 or abs(lo - ref["lo"]) > 1e-12 or ne != ref["n_eff"] or [ex, rs] != list(ref["出口結果"]) or k3 != ref["K3"]:
                bad.append((H, col))
    RES["③ 平均、CI、n_eff、出口、K3"] = {"不符": bad, "過": not bad}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
