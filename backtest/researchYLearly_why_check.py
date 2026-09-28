# -*- coding: utf-8 -*-
"""researchYLearly_why 簡短查核：抽 5 筆訊號（x5 類 0／1／2／4／5 各一），逐根自己算 T−1 狀態再自己分類。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLearly_why_check.py

另一套寫法：條件逐根迴圈（不用 rolling）、漲停用自己的升降單位重算、營收自己讀面板逐列判、3/5 候選去重鏈自己從頭走、
所需漲幅用字面定義二分；共用的只有 data.load_stock（還原價）與 research11.load_bars 的 skip／next_bad。
名單去重（類 0 與「6 名單去重擋」）要看前 20 根有沒有選過 ⇒ 自己從該檔第一根走名單鏈。
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

OUT = "backtest/resultsYLearly/why"


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
    cal = D.load_calendar()
    R = pd.read_csv(os.path.join(OUT, "signals_why.csv.gz"), dtype={"sid": str})
    pick = []
    for c in (0, 1, 2, 4, 5):
        g = R[(R["類_x5"] == c) & ~R["sid"].isin([p[0] for p in pick])]
        if len(g):
            r = g.iloc[len(g) // 2]; pick.append((r["sid"], int(r["k"])))
    P = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    mk = D.load_universe().set_index("stock_id")["market"]
    rep = {"抽的 5 筆": [f"{s}@{k}" for s, k in pick], "逐筆": {}}; bad = 0
    for sid, K in pick:
        B = R11.load_bars(sid, mk.get(sid, "twse"), cal)
        idx, skip, nb = B["idx"], B["skip"], B["next_bad"]
        st = D.load_stock(sid, mk.get(sid, "twse"), cal).df
        c = st["close"].to_numpy(float)[idx]; amt = st["amount"].to_numpy(float)[idx]
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", sid + ".csv"), dtype={"date": str}).drop_duplicates("date")
        raw["date"] = pd.to_datetime(raw["date"]); rc = pd.to_numeric(raw.set_index("date").reindex(cal[idx])["close"], errors="coerce").to_numpy(float)
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

        def mreq(j):
            cj = conds(c, j); k = j + 1; best = np.inf
            for q in range(5):
                if cj[q] or q == 2:
                    continue
                if q == 1:
                    if int(up[j - 18:j + 1].sum()) == 2:
                        best = min(best, up_price(rc[j], 0.07 if dates[k] < pd.Timestamp("2015-06-01") else 0.10) / rc[j] - 1)
                    continue
                c2 = c.copy(); lo, hi = -0.9, 5.0

                def holds(r):
                    c2[k] = c[j] * (1 + r); return conds(c2, k)[q]
                if not holds(hi):
                    continue
                for _ in range(80):
                    m = (lo + hi) / 2
                    lo, hi = (lo, m) if holds(m) else (m, hi)
                best = min(best, hi)
            return best
        # 3/5 候選去重鏈、名單鏈（x5）從頭走
        last = -10 ** 9; chain = []
        for k in range(250, n):
            if elig(k) and sum(conds(c, k)) >= 3 and k - last > 20:
                chain.append(k); last = k
        lastL = -10 ** 9; listed = set()
        for j in range(250, min(K, n - 1)):
            if elig(j) and sum(conds(c, j)) == 2 and andf(int(idx[j])):
                if mreq(j) <= 0.05 + 1e-12 and j - lastL > 20:
                    listed.add(j); lastL = j
        j = K - 1; sj = sum(conds(c, j)); aj = andf(int(idx[j]))
        new = "+".join(f"c{q + 1}" for q in range(5) if conds(c, K)[q] and not conds(c, j)[q])
        if j in listed:
            cat = 0
        elif not aj:
            cat = 1
        elif sj <= 1:
            cat = 2
        elif sj == 2 and not elig(j):
            cat = 6
        elif sj == 2 and not np.isfinite(mreq(j)):
            cat = 3
        elif sj == 2 and mreq(j) > 0.05 + 1e-12:
            cat = 4
        elif sj == 2:
            cat = 6
        elif elig(j):
            cat = 5
        else:
            cat = 6
        o = R[(R["sid"] == sid) & (R["k"] == K)].iloc[0]
        d = {"T−1": str(dates[j].date()), "本支類": cat, "主程式類": int(o["類_x5"]), "本支 T−1 分數": sj, "主程式": int(o["T−1分數"]),
             "本支 T−1 營收": aj, "主程式營收": bool(o["T−1營收"]), "本支 T 新達成": new, "主程式 T 新達成": o["T新達成"] if isinstance(o["T新達成"], str) else "",
             "訊號根在本支 3/5 鏈": K in chain}
        if cat == 5:
            prv = [x for x in chain if x < K]
            d["本支：T−1 被擋（前一選入根距 T−1）"] = (j - prv[-1]) if prv else None
        if cat in (0, 4):
            d["本支所需漲幅"] = round(float(mreq(j)), 6)
        b = int(d["本支類"] != d["主程式類"]) + int(sj != d["主程式"]) + int(aj != d["主程式營收"]) + int(new != d["主程式 T 新達成"]) + int(not d["訊號根在本支 3/5 鏈"])
        d["不符"] = b; bad += b
        rep["逐筆"][f"{sid}@{K}"] = d
        print(sid, K, json.dumps(d, ensure_ascii=False, default=str), flush=True)
    rep["合計不符"] = bad
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("合計不符", bad)


if __name__ == "__main__":
    main()
