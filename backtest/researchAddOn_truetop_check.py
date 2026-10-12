# -*- coding: utf-8 -*-
"""researchAddOn_truetop 獨立查核（另一種寫法：逐日迴圈；⛔ 不呼叫 truetopT 的 signals_row／surge_world、⛔ 不呼叫 researchAddOn 的 account）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_truetop_check

 K1 抽 50 筆（唯一持股 × 格、有加碼；random_state 20261012）：逐日從頭重算起漲點（迴圈版）、處置起日／出關日（直接讀 disposal.csv）、NEAR（飆股 stitch 收盤＋bar.npy 逐根）、
    W2a／W2b ⇒ 加碼日起第一個訊號日；次一有效開盤（research11.load_bars K 棒 ∧ 開盤 ＞ 0）；與主臂（逐筆檔的 S 出場）比刻度取早 ⇒ T 出場日、價 ⇒ 0 不同才算過
 K2 組合：從 trades_T.csv.gz 逐路徑、逐日迴圈重記帳（讀法 A／B／C、臂 S／T），RR.win_metrics ⇒ 與 seeds_T.csv.gz 逐列差 ≤ 1e−9；中位重算 ⇒ 與 truetop_main.csv 差 ≤ 1e−9
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                  # noqa: E402
from backtest import research11 as R            # noqa: E402
from backtest import rerun17 as RR              # noqa: E402

OUT = "backtest/resultsAddOn/truetop"
WORK = os.path.expanduser("~/addonwork")
COST = R.COST
SEGJ = ("探索", "確認", "主窗")


def anchor_loop(c, T, eb):
    def a_of(T_):
        lo = max(T_ - 249, 0); P0 = lo
        for d in range(lo, T_ + 1):                      # np.argmax 語意：NaN 視為最大、同值取第一個
            if np.isnan(c[P0]):
                break
            if np.isnan(c[d]) or c[d] > c[P0]:
                P0 = d
        t_ = lo
        for d in range(lo, P0 + 1):                      # np.argmin 語意
            if np.isnan(c[t_]):
                break
            if np.isnan(c[d]) or c[d] < c[t_]:
                t_ = d
        return t_
    t = a_of(T)
    if eb < t:
        t = a_of(eb)
    for _ in range(50):
        rm = -np.inf; st_ = None
        for d in range(t, T + 1):
            if np.isnan(rm) or np.isnan(c[d]):
                rm = np.nan
            else:
                rm = max(rm, c[d])
            if not np.isnan(rm) and c[d] <= rm * 0.7:
                st_ = d; break
        if st_ is None or st_ >= eb:
            break
        m_ = st_
        for d in range(st_, eb + 1):
            if c[d] < c[m_]:
                m_ = d
        t = m_
    return t


def k1(W, TD, log):
    from backtest import researchSurge5 as S5
    cal = W["cal"]; n0 = len(cal)
    U = TD.drop_duplicates(["策略", "sid", "tb", "格"]).sample(50, random_state=20261012)
    D.DATA = S5.ST; cal_s = D.load_calendar(); pos_s = {d: j for j, d in enumerate(cal_s)}
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    bar_s = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r")
    dsp = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    SG = {}
    for sid in sorted(set(U["sid"])):
        if sid not in s2i:
            SG[sid] = None; continue
        s = s2i[sid]; c0 = D.load_stock(sid, uni.loc[s, "market"], cal_s).df["close"].to_numpy(float)
        bars = [d for d in range(len(cal_s)) if np.isfinite(c0[d]) and bar_s[s, d]]
        g = dsp[dsp["stock_id"] == sid]
        starts = sorted(int(cal_s.searchsorted(pd.Timestamp(x))) for x in g["start_date"])
        ends = [int(cal_s.searchsorted(pd.Timestamp(y), side="right")) - 1 for y in g["end_date"]]
        SG[sid] = (c0, bars, {d: j for j, d in enumerate(bars)}, starts, ends)
    RR.use_snapshot()
    nd = 0; errs = []; cnt = {"提早賣": 0, "有訊號": 0, "W2a": 0, "W2b": 0}
    for r in U.itertuples():
        sid, tb, ta = r.sid, int(r.tb), int(r.ta)
        c = np.asarray(W["closes"][sid], float)[:n0]; o = np.asarray(W["opens"][sid], float)[:n0]
        B = R.load_bars(sid, W["uni"].get(sid, "twse"), cal)
        isb = np.zeros(n0, bool)
        if B is not None:
            isb[B["idx"][B["idx"] < n0]] = True
        # 主臂刻度（逐筆檔 S）
        if r.S_出場日 < 0:
            mt = np.inf
        else:
            pb = int(r.S_出場日) - (1 if r.S_種類 == "同原持股（停止交易強制）" else 0)
            mt = 2 * pb + 1
        # hi ＝ 原持股出場根（triggers 的 xbar）與 n0 取小
        hi = min(int(r.xbar), n0)
        sig = None; src = None
        sg = SG[sid]
        if sg is not None:
            c0, bars, bpos, starts, ends = sg
            for d in range(ta, hi):
                ds = pos_s.get(cal[d])
                if ds is None or ds not in bpos:
                    continue
                j = bpos[ds]
                near = len(bars) >= 25 and j >= 19 and c0[ds] >= 0.9 * max(c0[bars[k]] for k in range(j - 19, j + 1))
                if not near:
                    continue
                t = anchor_loop(c, d, tb); ts = pos_s[cal[t]]
                w2a = (ds in starts) and any(ts <= x <= ds - 1 for x in starts)
                w2b = any(ds == b + 1 for b in ends)
                if w2a or w2b:
                    sig = d; src = "W2a" if w2a else "W2b"; break
        u = None
        if sig is not None:
            x = sig + 1
            while x < n0 and not (isb[x] and np.isfinite(o[x]) and o[x] > 0):
                x += 1
            u = x if x < n0 else None
        if u is not None and 2 * u < mt:
            sd, px, early = u, float(o[u]), True
        else:
            sd, px, early = int(r.S_出場日), float(r.S_價), False
        cnt["提早賣"] += int(early); cnt["有訊號"] += int(sig is not None)
        if src:
            cnt[src] += 1
        why = []
        if (-1 if sig is None else sig) != int(r.訊號日):
            why.append(f"訊號日 {sig}/{r.訊號日}")
        if (src or "") != (r.訊號來源 if isinstance(r.訊號來源, str) else ""):
            why.append(f"來源 {src}/{r.訊號來源}")
        if sd != int(r.T_出場日) or bool(early) != bool(r.提早賣) or not (np.isclose(px, float(r.T_價), rtol=1e-12) or (np.isnan(px) and np.isnan(float(r.T_價)))):
            why.append(f"T 出場 {sd},{px},{early} / {r.T_出場日},{r.T_價},{r.提早賣}")
        if why:
            nd += 1; errs.append(f"{r.策略} {sid} tb{tb} {r.格}：{'；'.join(why)}")
    out = {"抽樣": "唯一持股×格（有加碼）抽 50（random_state 20261012）", "不同": nd, "不同的筆": errs[:20], "事件": cnt}
    log(f"[K1] {out}")
    return out


def nav3(E, a, y, P, cl_of):
    """逐日迴圈記帳 ⇒ NAV A、B、C。P：[(ta, A, ep, sid, sd, px)]（ta ∈ (a, y]）。"""
    L = y - a + 1; K = 0.0
    navA = np.empty(L); navC = np.empty(L); Wt = np.empty(L); Fc = np.empty(L)
    navA[0] = navC[0] = E[a]; Fsum = 0.0
    act = []
    mv_prev = 0.0; W_prev = E[a]
    Wt[0] = E[a]; Fc[0] = 0.0
    byday = {}
    for p in P:
        byday.setdefault(p[0], []).append(p)
    for i in range(1, L):
        day = a + i; add = 0.0; proc = 0.0; F = 0.0
        for p in byday.get(day, ()):
            add += p[1]
            act.append(p)
        if add > 0:
            use = min(K, add); K -= use; F = add - use
        keep = []
        mv = 0.0
        for p in act:
            ta, A, ep, sid, sd, px = p
            if sd is not None and sd == day:
                proc += A * (px / ep - COST)
            else:
                mv += A * float(cl_of(sid)[day]) / ep; keep.append(p)
        act = keep
        K += proc
        Wd = E[day] + K + mv
        navA[i] = navA[i - 1] * Wd / (W_prev + F)
        navC[i] = navC[i - 1] * (1.0 + (E[day] - E[day - 1] + mv + proc - mv_prev - add) / (E[day - 1] + mv_prev + add))
        Fsum += F; Wt[i] = Wd; Fc[i] = Fsum
        W_prev = Wd; mv_prev = mv
    WB = Wt + (Fsum - Fc)
    navB = E[a] * WB / WB[0]
    return {"A": navA, "B": navB, "C": navC}


def k2(W, TD, log):
    ENG = pickle.load(open(os.path.join(WORK, "engine_200.pkl"), "rb"))
    SE = pd.read_csv(os.path.join(OUT, "seeds_T.csv.gz"), float_precision="round_trip").set_index(["策略", "r", "格", "段"])
    MT = pd.read_csv(os.path.join(OUT, "truetop_main.csv"), float_precision="round_trip")
    cl_of = lambda s: W["closes"][s]
    md = 0.0; rows = []
    G = {k: g for k, g in TD.groupby(["策略", "r", "格"])}
    for key in sorted(k for k in ENG if k[0] == "主"):
        _, sn, r = key; E = ENG[key]; eq = np.asarray(E["eq"], float); first, end = E["first"], E["end"]
        for c in ("A1", "A2"):
            g = G.get((sn, r, c))
            for sg in SEGJ:
                x, y = W["segp"][sg]; a = max(x, first); yy = min(y, end - 1)
                c0, m0, _ = RR.win_metrics(eq, first, end, x, y)
                row = {"策略": sn, "r": r, "格": c, "段": sg, "原_年化": c0, "原_回落": m0}
                for arm in ("S", "T"):
                    P = []
                    if g is not None:
                        for z in g.itertuples():
                            if a < z.ta <= yy:
                                sd = getattr(z, f"{arm}_出場日")
                                P.append((int(z.ta), float(z.金額), float(z.加碼價), z.sid, None if sd < 0 or sd > yy else int(sd), float(getattr(z, f"{arm}_價"))))
                    navs = nav3(eq, a, yy, P, cl_of)
                    for rd in ("A", "B", "C"):
                        full = eq.copy(); full[a:a + len(navs[rd])] = navs[rd]
                        cc, mm, _ = RR.win_metrics(full, first, end, x, y)
                        row[f"{arm}_{rd}_年化"] = cc; row[f"{arm}_{rd}_回落"] = mm
                        ref = SE.loc[(sn, r, c, sg)]
                        md = max(md, abs(cc - float(ref[f"{arm}_{rd}_年化"])), abs(mm - float(ref[f"{arm}_{rd}_回落"])))
                rows.append(row)
    X = pd.DataFrame(rows); mm2 = 0.0
    for z in MT.itertuples():
        g = X[(X["策略"] == z.策略) & (X["格"] == z.格) & (X["段"] == z.段)]
        for arm, col in (("原", "原"), ("S", "S"), ("T", "T")):
            ya = g["原_年化"].median() if arm == "原" else g[f"{arm}_{z.讀法}_年化"].median()
            yb = g["原_回落"].median() if arm == "原" else g[f"{arm}_{z.讀法}_回落"].median()
            mm2 = max(mm2, abs(ya - getattr(z, f"{col}_年化")), abs(yb - getattr(z, f"{col}_回落")))
    out = {"路徑×格×段": len(X), "逐列 S／T 三讀法年化回落最大差": md, "主表中位最大差": mm2}
    log(f"[K2] {out}")
    return out


def main():
    T0 = time.time()
    log = lambda m: print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)
    W = pickle.load(open(os.path.join(WORK, "world_主.pkl"), "rb"))
    TD = pd.read_csv(os.path.join(OUT, "trades_T.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    TR = pd.read_csv("backtest/resultsAddOn/triggers.csv.gz", dtype={"sid": str})
    TR = TR[(TR["世界"] == "主") & (TR["格"] == "A1")][["策略", "sid", "tb", "xbar"]]
    TD = TD.merge(TR, on=["策略", "sid", "tb"], how="left")
    o1 = k1(W, TD, log)
    o2 = k2(W, TD, log)
    ok = o1["不同"] == 0 and o2["逐列 S／T 三讀法年化回落最大差"] <= 1e-9 and o2["主表中位最大差"] <= 1e-9
    out = {"K1": o1, "K2": o2, "通過": ok, "秒": round(time.time() - T0)}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 通過 {ok}")


if __name__ == "__main__":
    main()
