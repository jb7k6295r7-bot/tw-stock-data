# -*- coding: utf-8 -*-
"""researchHoldState 簡短查核（另一套寫法）。回測線，2026-09-29。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchHoldState_check.py

① 7 檔持股 t 日狀態：MA、方向、250 高、法人 5 日合計用切片／原始 CSV 自己算（營收旗標另從原始月營收自己判：最新已公布月 ＞ 前 24 期最大）
② 樣本抽 8 列（主窗 5、早年 3）：狀態碼與 R60、超額 60 自己重算
③ 2 檔持股的格：從明細 npz 自己篩、自己算 60 天上漲機率、中位、比 0050 好 ⇒ 比對 summary
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R11

OUT = "backtest/resultsHoldState"


def state(sid, mk, cal, data, inst=True):
    D.DATA = data
    B = R11.load_bars(sid, mk, cal); idx = B["idx"]; cb = B["c"]
    return idx, cb


def codes_at(cb, i):
    C = cb[i]; m60 = cb[i - 59:i + 1].mean(); m60p = cb[i - 79:i - 19].mean(); m20 = cb[i - 19:i + 1].mean(); hi = cb[i - 249:i + 1].max()
    A = (2 if C > m60 else 0) + (1 if m60 > m60p else 0); Bc = int(C > m20); d = C / hi - 1
    E = 0 if d >= -0.10 else (1 if d >= -0.30 else 2)
    return A, Bc, E


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    sha = S["main"]; MD = os.path.expanduser(f"~/h2data/{sha}/data"); ED = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
    D.DATA = MD; cal = D.load_calendar()
    mk = dict(pd.read_csv(os.path.join(MD, "meta", "stocks.csv"), dtype=str)[["stock_id", "market"]].to_numpy())
    rep = {"持股": {}, "樣本列": [], "格": {}}; bad = 0
    # 月營收（原始）
    fs = sorted(glob.glob(os.path.join(MD, "mops", "revenue_hist", "*.csv")))
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs]); rv["v"] = pd.to_numeric(rv["當月營收"], errors="coerce")
    for s, r in S["持股"].items():
        idx, cb = state(s, mk[s], cal, MD); i = len(cb) - 1
        A, Bc, E = codes_at(cb, i)
        it = pd.read_csv(os.path.join(MD, "stocks_inst", s + ".csv"), dtype={"date": str})
        last5 = [str(d.date()) for d in cal[-5:]]
        tot = pd.to_numeric(it[it["date"].isin(last5)]["total"], errors="coerce").sum()
        Dc = int(tot > 0)
        g = rv[rv["stock_id"] == s].dropna(subset=["v"]).sort_values("period")
        # 最新「已公布」月：9/24 時 ⇒ 8 月（次月 10 日後生效）
        g = g[g["period"] <= "2026-08"]
        Cc = int(g["v"].iloc[-1] > g["v"].iloc[-25:-1].max())
        st = r["狀態"]
        d = {"本支": [A, Bc, Cc, Dc, E], "主程式": [st["A"], st["B"], st["C"], st["D"], st["E"]], "最新月營收": [g["period"].iloc[-1], float(g["v"].iloc[-1]), float(g["v"].iloc[-25:-1].max())],
             "近 5 日法人合計（股）": float(tot)}
        b = int(d["本支"] != d["主程式"]); d["不符"] = b; bad += b; rep["持股"][s] = d
        print("[持股]", s, json.dumps(d, ensure_ascii=False), flush=True)
    # 樣本列
    rng = np.random.default_rng(20260929)
    b50 = {}
    for tag, data, npz in (("主窗", MD, "rows_main.npz"), ("早年", ED, "rows_early.npz")):
        Z = np.load(os.path.join(OUT, npz), allow_pickle=False)
        D.DATA = data; calw = D.load_calendar()
        mkw = dict(pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)[["stock_id", "market"]].to_numpy())
        bz = pd.Series(D.load_stock("0050", "twse", calw).df["close"].to_numpy(float)).ffill().to_numpy()
        ok = np.flatnonzero(np.isfinite(Z["R60"]))
        for j in rng.choice(ok, size=5 if tag == "主窗" else 3, replace=False):
            s = str(Z["sid"][j]); d_ = int(Z["d"][j])
            idx, cb = state(s, mkw.get(s, "twse"), calw, data); i = int(np.searchsorted(idx, d_))
            A, Bc, E = codes_at(cb, i)
            st = D.load_stock(s, mkw.get(s, "twse"), calw).df["close"].to_numpy(float); cff = pd.Series(st).ffill().to_numpy()
            r60 = cff[d_ + 60] / cff[d_] - 1; x60 = r60 - (bz[d_ + 60] / bz[d_] - 1)
            d = {"世界": tag, "sid": s, "日": str(calw[d_].date()), "本支 A B E": [A, Bc, E], "主程式": [int(Z["A"][j]), int(Z["B"][j]), int(Z["E"][j])],
                 "R60 差": float(abs(r60 - Z["R60"][j])), "X60 差": float(abs(x60 - Z["X60"][j]))}
            b = int(d["本支 A B E"] != d["主程式"]) + int(d["R60 差"] > 1e-6) + int(d["X60 差"] > 1e-6)
            d["不符"] = b; bad += b; rep["樣本列"].append(d); print("[樣本]", json.dumps(d, ensure_ascii=False), flush=True)
    # 格
    Z = np.load(os.path.join(OUT, "rows_main.npz"))
    for s in ("6282", "2609"):
        st = S["持股"][s]["狀態"]
        m = (Z["A"] == st["A"]) & (Z["B"] == st["B"]) & (Z["C"] == st["C"]) & (Z["D"] == st["D"]) & (Z["E"] == st["E"]) & np.isfinite(Z["R60"])
        r = Z["R60"][m].astype(float); x = Z["X60"][m].astype(float)
        mine = [int(m.sum()), float((r > 0).mean()), float(np.median(r)), float((x > 0).mean())]
        z = S["持股"][s]["主窗"]["60"]
        main_ = [z["n"], z["上漲機率"], z["中位"], z["贏0050"]]
        d = {"本支 n／上漲／中位／贏0050": mine, "主程式": main_}
        b = int(mine[0] != main_[0]) + sum(int(abs(p - q) > 1e-9) for p, q in zip(mine[1:], main_[1:]))
        d["不符"] = b; bad += b; rep["格"][s] = d; print("[格]", s, json.dumps(d, ensure_ascii=False), flush=True)
    rep["合計不符"] = bad
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("合計不符", bad)


if __name__ == "__main__":
    main()
