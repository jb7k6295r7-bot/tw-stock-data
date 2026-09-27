# -*- coding: utf-8 -*-
"""稽核 ② 4 上升三角往上突破 獨立查核（⛔ 不 import researchAudit2_4、researchPatAll、researchPatAll_freq、patterns_all、research11）。
只 import backtest.data（讀檔、斷點規則）、backtest.tradability（漲跌停旗標、下市狀態）、backtest.universe_gate（gate3）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_4_check.py

C1 由 events.csv.gz 重算三段 × 四個 H 與早年合併：X ＝ R − 對照平均；CR0（自己寫；H60 以 (T−段起點)//60 分群，其餘曆月）、95% CI、n_eff、出口、結果、
   「95% CI 下緣 ＞ 0.585%」⇒ 與 summary.json 比（差 < 1e-12、標籤相同）
C2 每段抽 150 筆 H20（主窗、早年甲）／全部（早年乙）：全段逐檔自建 ⇒ R、對照平均、對照數：
   錨點 r60 ＝ 有效 K 棒 c[b−1]÷c[b−61]−1（first 那一根）；十分位 ＝ first 當天全 gate3（有效且可算）rank(first) 後等分 10（整數式）；
   對照 ＝ 同十分位、T 有效、T＋1 有成交且開盤有效且非漲跌停、T 當天無原始 S06（raw_events.csv.gz，任何狀態）、
   [first, T＋H] 無硬斷點（價格斷點 或 區間內連續 ≥5 個交易日沒成交且 5 天都在區間內；下市者最後成交後不算；逐日掃）、R 可算、非自己
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
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/4")
SEG = {"主窗": (SNAP, "2017-03-02", "2026-08-24"), "早年甲": (EARLY, None, "2014-12-31"), "早年乙": (SNAP, "2015-01-05", "2017-03-01")}
HS = (5, 10, 20, 60)
COST, TOL = 0.00585, 1e-12


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, np.sqrt((s ** 2).sum()) / n, len(s)


def lab(m, lo, hi, ne):
    if ne < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if ne < 100 else "出口③"
    return ex, ("結果①" if lo <= 0 <= hi else ("結果②" if m > 0 else "結果③"))


def dec10(v):
    m = len(v); order = np.argsort(v, kind="stable"); rank = np.empty(m, np.int64); rank[order] = np.arange(1, m + 1)
    return np.array([sum(10 * (r - 1) > j * (m - 1) for j in range(1, 10)) for r in rank], int)


def main():
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    E = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    RAW = pd.read_csv(os.path.join(OUT, "raw_events.csv.gz"), dtype={"sid": str})
    RES = {}; bad = []
    # C1
    for seg, (data, W0, W1) in SEG.items():
        D.DATA = data; cal = D.load_calendar()
        w0 = int(cal.searchsorted(pd.Timestamp(W0))) if W0 else 0
        pos = {str(d.date()): i for i, d in enumerate(cal)}
        for H in HS:
            x = E[(E["段"] == seg) & (E["H"] == H) & E["X"].notna()]
            if len(x) < 2:
                continue
            T = x["T"].map(pos).to_numpy(int)
            g = (T - w0) // 60 if H == 60 else x["月"].to_numpy()
            m, se, ng = cr0(x["X"].to_numpy(float), g)
            lo, hi = m - 1.96 * se, m + 1.96 * se
            ex, rs = lab(m, lo, hi, min(len(x), ng))
            ref = Sm[seg][f"H{H}"]
            if abs(m - ref["dX̄"]) > TOL or abs(lo - ref["lo"]) > TOL or rs != ref["結果"] or ex != ref["出口"] or (lo > COST) != ref["95%CI下緣 ＞ 0.585%"]:
                bad.append((seg, H))
    for H in HS:
        x = E[E["段"].isin(["早年甲", "早年乙"]) & (E["H"] == H) & E["X"].notna()]
        m, se, ng = cr0(x["X"].to_numpy(float), x["月"].to_numpy())
        lo = m - 1.96 * se; ex, rs = lab(m, lo, m + 1.96 * se, min(len(x), ng))
        ref = Sm["早年段合併（甲＋乙）"][f"H{H}"]
        if abs(m - ref["dX̄"]) > TOL or abs(lo - ref["lo"]) > TOL or rs != ref["結果"]:
            bad.append(("早年合併", H))
    RES["C1 三段 × 四 H＋早年合併 平均、CI、出口、結果、CI 下緣對成本"] = {"不符": bad, "過": not bad}
    print(RES, flush=True)
    # C2
    rng = np.random.default_rng(20260928); c2 = {}
    for seg, (data, W0, W1) in SEG.items():
        D.DATA = data; cal = D.load_calendar(); n = len(cal)
        w1 = int(cal.searchsorted(pd.Timestamp(W1)));  w1 -= 0 if str(cal[w1].date()) == W1 else 1
        pos = {str(d.date()): i for i, d in enumerate(cal)}
        U = UG.gate3(pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str))
        off = TR.load_official()
        sids, V, TRD1, A60, CFF, O, PB, VAL_UP = [], [], [], [], [], [], [], []
        for sid, mk in zip(U["stock_id"], U["market"]):
            st = D.load_stock(sid, mk, cal)
            if st is None:
                continue
            o = st.df["open"].to_numpy(float); c = st.df["close"].to_numpy(float); v = np.isfinite(c)
            if not v.any():
                continue
            b = np.flatnonzero(v); a = np.full(n, np.nan)
            if len(b) > 61:
                a[b[61:]] = c[b[60:-1]] / c[b[:-61]] - 1.0
            tb = TR.one(sid, cal)
            t1 = np.zeros(n, bool)
            t1[:-1] = np.asarray(tb["trd"], bool)[1:] & np.isfinite(o[1:]) & ~np.asarray(tb["up_o"], bool)[1:] & ~np.asarray(tb["dn_o"], bool)[1:]
            pb = np.zeros(n, bool)
            for b_ in D.breakpoints(st.df, st.event_dates):
                if b_["rule"] in ("price", "price+gap"):
                    pb[b_["pos"]] = True
            ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
            up = ds["last"] if (ds is not None and ds["status"].startswith("delisted")) else None
            sids.append(sid); V.append(v); TRD1.append(t1); A60.append(a); CFF.append(pd.Series(c).ffill().to_numpy()); O.append(o)
            PB.append(pb); VAL_UP.append(up)
        ix = {s: i for i, s in enumerate(sids)}
        V, TRD1, A60, CFF, O, PB = (np.column_stack(z) for z in (V, TRD1, A60, CFF, O, PB))
        raw = RAW[RAW["段"] == seg]
        RAWD = np.zeros(V.shape, bool)
        RAWD[raw["T"].map(pos).to_numpy(int), raw["sid"].map(ix).to_numpy(int)] = True

        def brk(j, a, b):
            if PB[a:b + 1, j].any():
                return True
            run = 0
            for t in range(a, b + 1):
                miss = (not V[t, j]) and (VAL_UP[j] is None or t <= VAL_UP[j])
                run = run + 1 if miss else 0
                if run >= 5:
                    return True
            return False
        e = E[(E["段"] == seg) & (E["H"] == 20) & E["X"].notna()].reset_index(drop=True)
        pick = e if len(e) <= 150 else e.iloc[np.sort(rng.choice(len(e), 150, replace=False))]
        mr = mc = 0.0; nbad = 0; H = 20
        for r in pick.itertuples():
            T, f, i = pos[r.T], pos[r.first], ix[r.sid]
            g = CFF[T + H, i] / O[T + 1, i] - 1.0
            base = V[f] & np.isfinite(A60[f]); idx = np.flatnonzero(base)
            dec = np.full(len(sids), -1); dec[idx] = dec10(A60[f, idx])
            cand = np.flatnonzero((dec == dec[i]) & V[T] & TRD1[T] & ~RAWD[T])
            vals = []
            for j in cand:
                if j == i:
                    continue
                gj = CFF[T + H, j] / O[T + 1, j] - 1.0 if (np.isfinite(O[T + 1, j]) and O[T + 1, j] > 0 and V[T + 1, j]) else np.nan
                if not np.isfinite(gj) or brk(j, f, T + H):
                    continue
                vals.append(gj)
            ctrl = float(np.mean(vals)) if vals else np.nan
            mr = max(mr, abs(g - r.R)); mc = max(mc, abs(ctrl - r.對照平均)); nbad += int(len(vals) != int(r.對照數))
        c2[seg] = {"筆數": int(len(pick)), "R 最大差": mr, "對照平均最大差": mc, "對照數不符": nbad}
        print(seg, c2[seg], flush=True)
    RES["C2 全段自建對照（H20 抽樣）"] = {**c2, "過": all(v["R 最大差"] <= TOL and v["對照平均最大差"] <= TOL and v["對照數不符"] == 0 for v in c2.values())}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
