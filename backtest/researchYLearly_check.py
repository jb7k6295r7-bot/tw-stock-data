# -*- coding: utf-8 -*-
"""researchYLearly 簡短查核：挑 5 檔、逐日重算可執行臂的條件值（另一套寫法）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLearly_check.py

另一套寫法：
  ・條件逐根用迴圈算（不用 rolling）；漲停旗標用自己寫的升降單位重算
  ・「所需隔日漲幅」⛔ 不用公式：把 T 日收盤設成 收[T−1]×(1＋r)、用條件的字面定義二分找最小 r（c2 直接用漲停價）
  ・營收 AND 自己讀面板逐根判；均價自己讀原始 CSV 的 成交額÷成交量 × 還原因子
  ・共用的只有：data.load_stock（還原價、有效 K 棒）與 research11.load_bars 的 skip／next_bad（壞根、事件根）
比對 rows_主.csv.gz 在這 5 檔的每一列：列集合、未達條件、最容易那條、所需漲幅、去重後選入（x＝5%）、T 日均價、T 收盤是否成立、g
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11

OUT = "backtest/resultsYLearly"
CNS = ("c1", "c2", "c3", "c4", "c5")   # rows 存到 %.9g ⇒ 均價、g 的容許差 1e−8；所需漲幅（二分）1e−6


def tick(p):
    for lim, t in ((10, 0.01), (50, 0.05), (100, 0.1), (500, 0.5), (1000, 1.0)):
        if p < lim:
            return t
    return 5.0


def up_price(ref, lim):
    raw = ref * (1 + lim); t = tick(raw)
    return np.floor(raw / t + 1e-9) * t


def main():
    RR.use_snapshot()
    cal = D.load_calendar(); n0 = len(cal)
    R = pd.read_csv(os.path.join(OUT, "rows_主.csv.gz"), dtype={"sid": str})
    t0c = int(cal.searchsorted(pd.Timestamp("2022-01-03")))
    cand = R[R["sel_x5"] & (R["T"] > t0c)].sort_values(["T", "sid"])
    pick = []
    for ez in ("c1", "c2", "c4", "c5"):
        g = cand[(cand["最容易"] == ez) & ~cand["sid"].isin(pick)]
        if len(g):
            pick.append(g["sid"].iloc[0])
    g = cand[cand["T成立"] & ~cand["sid"].isin(pick)]
    if len(g):
        pick.append(g["sid"].iloc[0])
    for s in cand["sid"]:
        if len(pick) >= 5:
            break
        if s not in pick:
            pick.append(s)
    P = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    mk = D.load_universe().set_index("stock_id")["market"]
    rep = {"挑的 5 檔": pick, "逐檔": {}}
    tot_bad = 0
    for sid in pick:
        B = R11.load_bars(sid, mk.get(sid, "twse"), cal)
        idx, skip, nb = B["idx"], B["skip"], B["next_bad"]
        st = D.load_stock(sid, mk.get(sid, "twse"), cal).df
        c = st["close"].to_numpy(float)[idx]
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", sid + ".csv"), dtype={"date": str}).drop_duplicates("date")
        raw["date"] = pd.to_datetime(raw["date"]); raw = raw.set_index("date").reindex(cal[idx])
        rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float)
        amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float); vol = pd.to_numeric(raw["volume"], errors="coerce").to_numpy(float)
        hi_ = st["high"].to_numpy(float)[idx]; lo_ = st["low"].to_numpy(float)[idx]
        n = len(idx); dates = cal[idx]
        up = np.zeros(n, bool)
        for k in range(1, n):
            if skip[k] or not (rc[k - 1] > 0) or np.isnan(rc[k]):
                continue
            lim = 0.07 if dates[k] < pd.Timestamp("2015-06-01") else 0.10
            up[k] = abs(rc[k] - up_price(rc[k - 1], lim)) < 1e-6
        pp = P[P["stock_id"] == sid].sort_values("signal_pos")
        sp = pp["signal_pos"].to_numpy(); hh = pp["rev_hi24"].astype("boolean").fillna(False).to_numpy(bool)

        def andf(pos):
            ok = False
            for a, b in zip(sp, hh):
                if a <= pos:
                    ok = (pos - a <= 45) and b
                else:
                    break
            return ok

        def conds(cc, k):          # cc：收盤序列（可能換過第 k 根）
            r20 = cc[k] / cc[k - 20] - 1
            nup = int(up[k - 19:k + 1].sum())
            ar = amt[k] / np.mean(amt[k - 20:k])
            ma = np.mean(cc[k - 99:k + 1]); hmax = np.max(cc[k - 249:k + 1])
            return [r20 >= 0.30, nup >= 3, ar >= 3.0, cc[k] > ma, cc[k] >= hmax]

        def elig(k):
            return k >= 249 and not skip[k] and nb[max(0, k - 20)] > k and np.isfinite(amt[k - 21:k + 1]).all()

        mine = []
        for j in range(250, n - 1):
            if not elig(j):
                continue
            cj = conds(c, j)
            if sum(cj) != 2 or not andf(int(idx[j])):
                continue
            k = j + 1; rq = {}
            for q in range(5):
                if cj[q]:
                    continue
                nm = f"c{q + 1}"
                if q == 2:
                    rq[nm] = np.inf; continue
                if q == 1:
                    cnt = int(up[j - 18:j + 1].sum())
                    lim = 0.07 if dates[k] < pd.Timestamp("2015-06-01") else 0.10
                    rq[nm] = up_price(rc[j], lim) / rc[j] - 1 if cnt == 2 else np.inf; continue
                lo, hi = -0.9, 5.0
                c2 = c.copy()

                def holds(r):
                    c2[k] = c[j] * (1 + r); return conds(c2, k)[q]
                if not holds(hi):
                    rq[nm] = np.inf; continue
                for _ in range(80):
                    m = (lo + hi) / 2
                    if holds(m):
                        hi = m
                    else:
                        lo = m
                rq[nm] = hi
            ez = min(rq, key=lambda z: (rq[z], z))
            with np.errstate(invalid="ignore", divide="ignore"):
                vw = amt[k] / vol[k] * c[k] / rc[k] if vol[k] > 0 else np.nan
            vw = min(max(vw, lo_[k]), hi_[k]) if np.isfinite(vw) else np.nan
            ck = conds(c, k) if k >= 250 else [False] * 5
            conf = bool(elig(k) and sum(ck) >= 3 and andf(int(idx[k])))
            e = k + 60; nbk = nb[max(0, k - 20)]
            g = c[e] / vw - 1 if (e < n and e < nbk) else (c[n - 1] / vw - 1 if (e >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1) else np.nan)
            mine.append({"j": j, "未達": "+".join(f"c{q + 1}" for q in range(5) if not cj[q]), "最容易": ez, "所需漲幅": float(rq[ez]), **{f"rq_c{q + 1}": float(rq.get(f"c{q + 1}", np.nan)) for q in range(5)}, "vw": vw, "成立": conf, "g": g})
        last = -10 ** 9
        for r in mine:
            r["sel"] = r["所需漲幅"] <= 0.05 + 1e-12 and r["j"] - last > 20
            if r["sel"]:
                last = r["j"]
        M = pd.DataFrame(mine).set_index("j")
        O = R[R["sid"] == sid].set_index("j")
        common = sorted(set(M.index) & set(O.index))
        # rows 只存了窗內（T ∈ [w0−5, w1+1]）的列 ⇒ 只比 O 的列集合是否都在 M、且 M 在 O 的 T 範圍內也都在 O
        Tlo, Thi = int(O["T"].min()), int(O["T"].max())
        M_in = [j for j in M.index if Tlo <= int(idx[j + 1]) <= Thi]
        d = {"本支列數（同範圍）": len(M_in), "主程式列數": len(O), "列集合差": len(set(M_in) ^ set(O.index)),
             "未達不同": int(sum(M.at[j, "未達"] != O.at[j, "未達"] for j in common)),
             "最容易不同": int(sum(M.at[j, "最容易"] != O.at[j, "最容易"] for j in common)),
             "所需漲幅最大差": float(max([abs(M.at[j, "所需漲幅"] - O.at[j, "所需漲幅"]) for j in common if np.isfinite(O.at[j, "所需漲幅"])] + [0.0])),
             "各條所需漲幅最大差（有限值）": {z: float(max([abs(M.at[j, "rq_" + z] - O.at[j, "rq_" + z]) for j in common if np.isfinite(O.at[j, "rq_" + z])] + [0.0])) for z in ("c1", "c2", "c4", "c5")},
             "各條有限值筆數": {z: int(np.isfinite(O.loc[common, "rq_" + z]).sum()) for z in ("c1", "c2", "c4", "c5")},
             "有限值集合不同": int(sum(np.isfinite(M.at[j, "rq_" + z]) != np.isfinite(O.at[j, "rq_" + z]) for j in common for z in CNS)),
             "選入(x5)不同": int(sum(bool(M.at[j, "sel"]) != bool(O.at[j, "sel_x5"]) for j in common)),
             "均價最大相對差": float(np.nanmax([abs(M.at[j, "vw"] / O.at[j, "vw_T"] - 1) for j in common] + [0.0])),
             "T成立不同": int(sum(bool(M.at[j, "成立"]) != bool(O.at[j, "T成立"]) for j in common)),
             "g最大差": float(np.nanmax([abs(M.at[j, "g"] - O.at[j, "g"]) for j in common if np.isfinite(O.at[j, "g"]) and O.at[j, "R8截"] == False] + [0.0])),
             "選入(x5)筆數": int(O["sel_x5"].sum()), "例（第一筆選入）": None}
        s1 = O[O["sel_x5"]]
        if len(s1):
            j = int(s1.index[0])
            d["例（第一筆選入）"] = {"T−1": str(cal[int(idx[j])].date()), "未達": M.at[j, "未達"], "最容易": M.at[j, "最容易"], "本支所需漲幅": round(float(M.at[j, "所需漲幅"]), 6),
                                 "主程式": round(float(O.at[j, "所需漲幅"]), 6), "T 當天漲": round(float(c[j + 1] / c[j] - 1), 4), "T成立": bool(M.at[j, "成立"])}
        bad = d["列集合差"] + d["未達不同"] + d["最容易不同"] + d["選入(x5)不同"] + d["T成立不同"] + int(d["所需漲幅最大差"] > 1e-6) + int(d["均價最大相對差"] > 1e-8) + int(d["g最大差"] > 1e-8)
        bad += d["有限值集合不同"] + sum(int(v > 1e-6) for v in d["各條所需漲幅最大差（有限值）"].values())
        d["不符"] = bad; tot_bad += bad
        rep["逐檔"][sid] = d
        print(sid, json.dumps(d, ensure_ascii=False, default=str), flush=True)
    rep["合計不符"] = tot_bad
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("合計不符", tot_bad)


if __name__ == "__main__":
    main()
