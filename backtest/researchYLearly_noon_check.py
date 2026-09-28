# -*- coding: utf-8 -*-
"""researchYLearly_noon 簡短查核：挑 5 檔、逐日自己算名單、門檻價、盤中確認與買進（另一套寫法）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLearly_noon_check.py

另一套寫法：條件逐根迴圈；門檻價 ⛔ 不用公式，用條件字面定義對 T 日收盤二分（c2 用自己的升降單位算漲停價）；
中午量、均價、營收、去重、g 全部自己算；共用的只有 data.load_stock（還原價）與 research11.load_bars 的 skip／next_bad。
挑檔：主窗確認段，A 開盤觸發、B 靠價、B 只靠量、B 分數 1（量＋價）、B0 只看價 各取第一檔（不重複）。
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

OUT = "backtest/resultsYLearly/noon"
ARMS = [("A_開盤確認", "A", "open", None), ("B_中午確認", "B", "vw", 0.5), ("B_量0.4", "B", "vw", 0.4), ("B_量0.6", "B", "vw", 0.6),
        ("B_開收平均", "B", "oc", 0.5), ("B0_只看價", "B0", "vw", None)]


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
    Rc = R[R["T"] > t0c]
    sel = [Rc["買_A_開盤確認"], Rc["買_B_中午確認"] & (Rc["路徑_B_中午確認"] == "價"), Rc["買_B_中午確認"] & (Rc["路徑_B_中午確認"] == "量"),
           Rc["買_B_中午確認"] & (Rc["路徑_B_中午確認"] == "分數1：量＋價"), Rc["買_B0_只看價"]]
    pick = []
    for m in sel:
        g = Rc[m & ~Rc["sid"].isin(pick)]
        if len(g):
            pick.append(g["sid"].iloc[0])
    P = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    mk = D.load_universe().set_index("stock_id")["market"]
    rep = {"挑的 5 檔": pick, "逐檔": {}}; bad_all = 0
    for sid in pick:
        B = R11.load_bars(sid, mk.get(sid, "twse"), cal)
        idx, skip, nb = B["idx"], B["skip"], B["next_bad"]
        st = D.load_stock(sid, mk.get(sid, "twse"), cal).df
        c = st["close"].to_numpy(float)[idx]; o = st["open"].to_numpy(float)[idx]; hh = st["high"].to_numpy(float)[idx]; ll = st["low"].to_numpy(float)[idx]
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", sid + ".csv"), dtype={"date": str}).drop_duplicates("date")
        raw["date"] = pd.to_datetime(raw["date"]); raw = raw.set_index("date").reindex(cal[idx])
        rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float)
        amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float); vol = pd.to_numeric(raw["volume"], errors="coerce").to_numpy(float)
        n = len(idx); dates = cal[idx]
        up = np.zeros(n, bool)
        for k in range(1, n):
            if skip[k] or not (rc[k - 1] > 0) or np.isnan(rc[k]):
                continue
            up[k] = abs(rc[k] - up_price(rc[k - 1], 0.07 if dates[k] < pd.Timestamp("2015-06-01") else 0.10)) < 1e-6
        pp = P[P["stock_id"] == sid].sort_values("signal_pos")
        rows_p = list(zip(pp["signal_pos"], pp["rev_hi24"].astype("boolean").fillna(False)))

        def andf(pos):
            ok = False
            for a, b in rows_p:
                if a > pos:
                    break
                ok = (pos - a <= 45) and bool(b)
            return ok

        def conds(cc, k):
            return [cc[k] / cc[k - 20] - 1 >= 0.30, int(up[k - 19:k + 1].sum()) >= 3, amt[k] / np.mean(amt[k - 20:k]) >= 3.0,
                    cc[k] > np.mean(cc[k - 99:k + 1]), cc[k] >= np.max(cc[k - 249:k + 1])]

        def elig(k):
            return k >= 249 and not skip[k] and nb[max(0, k - 20)] > k and np.isfinite(amt[k - 21:k + 1]).all()

        O = R[R["sid"] == sid].set_index("j")
        mine = {}
        for j in range(250, n - 1):
            k = j + 1; T = int(idx[k])
            if not (int(O["T"].min()) <= T <= int(O["T"].max())):
                continue
            if not elig(j):
                continue
            cj = conds(c, j); sj = sum(cj)
            if sj not in (1, 2) or not andf(int(idx[j])):
                continue
            thr = {}
            for q in (0, 1, 3, 4):
                if cj[q]:
                    continue
                if q == 1:
                    if int(up[j - 18:j + 1].sum()) == 2:
                        thr["c2"] = c[j] * up_price(rc[j], 0.07 if dates[k] < pd.Timestamp("2015-06-01") else 0.10) / rc[j]
                    continue
                c2 = c.copy(); lo, hi = c[j] * 0.1, c[j] * 6

                def holds(p):
                    c2[k] = p; return conds(c2, k)[q]
                for _ in range(90):
                    m = (lo + hi) / 2
                    lo, hi = (lo, m) if holds(m) else (m, hi)
                thr[f"c{q + 1}"] = hi
            vw = amt[k] / vol[k] * c[k] / rc[k] if vol[k] > 0 else np.nan
            vw = min(max(vw, ll[k]), hh[k]) if np.isfinite(vw) else np.nan
            PX = {"open": o[k], "vw": vw, "oc": (o[k] + c[k]) / 2}
            ap20 = np.mean(amt[k - 20:k])
            e = k + 60; nbk = nb[max(0, k - 20)]
            cx = c[e] if (e < n and e < nbk) else (c[n - 1] if (e >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1) else np.nan)
            ck = conds(c, k)
            rec = {"thr": thr, "T成立": bool(elig(k) and sum(ck) >= 3 and andf(T))}
            for nm, kind, px, r in ARMS:
                p = PX[px]; pc = [z for z in thr if p >= thr[z] - 1e-7 * p]
                if kind == "A":
                    trig = sj == 2 and bool(thr) and p >= min(thr.values()) - 1e-7 * p
                elif kind == "B0":
                    trig = sj == 2 and bool(pc)
                else:
                    c3ok = (not cj[2]) and r * amt[k] >= 3 * ap20
                    trig = (bool(pc) or c3ok) if sj == 2 else ((not cj[2]) and c3ok and bool(pc))
                rec[nm] = (trig, cx / p - 1 if np.isfinite(cx) else np.nan)
            mine[j] = rec
        last = {nm: -10 ** 9 for nm, *_ in ARMS}
        buy = {nm: set() for nm, *_ in ARMS}
        for j in sorted(mine):
            for nm, *_ in ARMS:
                if mine[j][nm][0] and j - last[nm] > 20:
                    buy[nm].add(j); last[nm] = j
        common = sorted(set(mine) & set(O.index))
        d = {"本支列數": len(mine), "主程式列數": len(O), "列集合差": len(set(mine) ^ set(O.index)),
             "門檻價最大相對差": float(max([abs(mine[j]["thr"][z] / O.at[j, "thr_" + z] - 1) for j in common for z in mine[j]["thr"]] + [0.0])),
             "門檻有無不同": int(sum(set(mine[j]["thr"]) != {z for z in ("c1", "c2", "c4", "c5") if np.isfinite(O.at[j, "thr_" + z])} for j in common)),
             "T成立不同": int(sum(mine[j]["T成立"] != bool(O.at[j, "T成立"]) for j in common))}
        for nm, *_ in ARMS:
            d[f"{nm}：觸發不同"] = int(sum(mine[j][nm][0] != bool(O.at[j, "觸發_" + nm]) for j in common))
            d[f"{nm}：買進不同"] = int(sum((j in buy[nm]) != bool(O.at[j, "買_" + nm]) for j in common))
            d[f"{nm}：買進筆數"] = len(buy[nm])
            gg = [abs(mine[j][nm][1] - O.at[j, "g_" + nm]) for j in common if np.isfinite(O.at[j, "g_" + nm]) and not O.at[j, "R8截"]]
            d[f"{nm}：g 最大差"] = float(max(gg + [0.0]))
        b = d["列集合差"] + d["門檻有無不同"] + d["T成立不同"] + int(d["門檻價最大相對差"] > 1e-6)
        b += sum(d[f"{nm}：觸發不同"] + d[f"{nm}：買進不同"] + int(d[f"{nm}：g 最大差"] > 1e-6) for nm, *_ in ARMS)
        d["不符"] = b; bad_all += b
        rep["逐檔"][sid] = d
        print(sid, json.dumps(d, ensure_ascii=False), flush=True)
    rep["合計不符"] = bad_all
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("合計不符", bad_all)


if __name__ == "__main__":
    main()
