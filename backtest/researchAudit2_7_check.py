# -*- coding: utf-8 -*-
"""稽核 ② 7 出場訊號 獨立查核（⛔ 不 import researchAudit2_7、researchExit、exit_signal、researchH2、avgdown、research11）。
只 import backtest.data（讀檔、斷點規則）、backtest.tradability（漲跌停旗標、下市狀態）、backtest.universe_gate（gate3）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_7_check.py

 ① 由原件 events_kept.csv.gz（rule＝close）自算：Y ＝ −換0050減續抱、Y_c ＝ Y ＋ 0.2425%；原件 E ＝ R 平均 ⇒ 6 判定格 × 4 量的平均、CR0 CI（H20 曆月、H60 blk60）、
    n_eff、出口、結果 ⇒ ＝ summary.json（X2 從本件 events.csv.gz 取）
 ② 抽 400 筆（H20、H60 各 200）：全市場自建前 20 日報酬十分位（rank×10//n、同值依股票代號序）與配對股（同十分位、非同格事件股、T＋1 有成交且開盤有效且非開盤跌停、
    [T−60, T＋H] 無硬斷點（價格斷點 或 區間內連續 ≥5 個交易日沒成交且 5 天都在區間內，下市者最後成交後不算；逐日掃）、R 可算）⇒ X2 ＝ 本件 events.csv.gz
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
OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/7")
SRC = os.path.expanduser("~/tw-p17/backtest/resultsExit")
TOL = 1e-12


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, np.sqrt((s ** 2).sum()) / n, len(s)


def verdict(m, lo, hi, ne):
    if ne < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if ne < 100 else "出口③"
    return ex, ("結果①" if lo <= 0 <= hi else ("結果②" if m > 0 else "結果③"))


def main():
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    E = pd.read_csv(os.path.join(SRC, "events_kept.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    E = E[E["rule"] == "close"]
    M = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    RES = {}; bad = []
    for g in "甲乙丙":
        for H in (20, 60):
            x = E[(E["g"] == g) & (E["H"] == H)]; mm = M[(M["g"] == g) & (M["H"] == H)]
            grp = x["month"] if H == 20 else x["blk60"]; gm = mm["month"] if H == 20 else mm["blk60"]
            y = -x["換0050減續抱"].to_numpy(float)
            for nm, v, gg in (("原件 E（續抱原始報酬）", x["R"].to_numpy(float), grp), ("① Y 續抱 − 換 0050（原件口徑，0050 多付 0.1425%）", y, grp),
                              ("① Y_c 續抱 − 換 0050（0050 付一次來回 0.385%）", y + 0.00385 - 0.001425, grp),
                              ("② X2 續抱 − 基準②", mm["X2"].to_numpy(float), gm)):
                ok = np.isfinite(v); m, se, ng = cr0(v[ok], np.asarray(gg)[ok]); lo, hi = m - 1.96 * se, m + 1.96 * se
                ex, rs = verdict(m, lo, hi, min(int(ok.sum()), ng))
                ref = Sm["結果"][f"{g}_H{H}"][nm]
                if abs(m - ref["mean"]) > TOL or abs(lo - ref["lo"]) > TOL or ex != ref["出口"] or rs != ref["結果"]:
                    bad.append((g, H, nm))
    RES["① 6 格 × 4 量"] = {"不符": bad, "過": not bad}
    print(RES, flush=True)
    # ②
    cal = D.load_calendar(); n = len(cal)
    U = UG.gate3(pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str)); off = TR.load_official()
    sids, O, CF, V, S1, PB, UP, R20 = [], [], [], [], [], [], [], []
    for sid, mk in zip(U["stock_id"], U["market"]):
        st = D.load_stock(sid, mk, cal)
        if st is None:
            continue
        o = st.df["open"].to_numpy(float); c = st.df["close"].to_numpy(float); v = np.isfinite(c)
        if not v.any():
            continue
        tb = TR.one(sid, cal); ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
        pb = np.zeros(n, bool)
        for b_ in D.breakpoints(st.df, st.event_dates):
            if b_["rule"] in ("price", "price+gap"):
                pb[b_["pos"]] = True
        b = np.flatnonzero(v); r = np.full(n, np.nan)
        if len(b) > 20:
            r[b[20:]] = c[b[20:]] / c[b[:-20]] - 1
        sids.append(sid); O.append(o); CF.append(pd.Series(c).ffill().to_numpy()); V.append(v)
        S1.append(np.asarray(tb["trd"], bool) & np.isfinite(o) & ~np.asarray(tb["dn_o"], bool)); PB.append(pb)
        UP.append(ds["last"] if (ds is not None and ds["status"].startswith("delisted")) else None); R20.append(r)
    O, CF, V, S1, PB, R20 = (np.column_stack(z) for z in (O, CF, V, S1, PB, R20))
    ix = {s: i for i, s in enumerate(sids)}

    def brk(j, a, b_):
        if PB[a:b_ + 1, j].any():
            return True
        run = 0
        for t in range(a, b_ + 1):
            miss = (not V[t, j]) and (UP[j] is None or t <= UP[j])
            run = run + 1 if miss else 0
            if run >= 5:
                return True
        return False
    rng = np.random.default_rng(20260928); mx = 0.0; nb = 0; cnt = 0
    for H in (20, 60):
        cand = M[(M["H"] == H) & M["X2"].notna()].reset_index(drop=True)
        for k in rng.choice(len(cand), 200, replace=False):
            r = cand.iloc[k]; T = int(r["T"]); s = ix[r["sid"]]
            evs = set(M[(M["H"] == H) & (M["g"] == r["g"]) & (M["T"] == T)]["sid"])
            base = np.flatnonzero(V[T] & np.isfinite(R20[T]))
            order = base[np.lexsort((base, R20[T, base]))]
            dec = np.full(len(sids), -1); dec[order] = (np.arange(len(base)) * 10) // len(base)
            vals = []
            for j in np.flatnonzero(dec == dec[s]):
                if sids[j] in evs or not S1[T + 1, j]:
                    continue
                if not (np.isfinite(O[T + 1, j]) and O[T + 1, j] > 0):
                    continue
                gj = CF[T + H, j] / O[T + 1, j] - 1
                if not np.isfinite(gj) or brk(j, T - 60, T + H):
                    continue
                vals.append(gj)
            x2 = float(r["R"]) - float(np.mean(vals))
            mx = max(mx, abs(x2 - r["X2"])); nb += int(len(vals) != int(r["配對股數"])); cnt += 1
    RES["② 400 筆基準② 自建"] = {"筆數": cnt, "最大差": mx, "配對股數不符": nb, "過": mx <= TOL and nb == 0}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
