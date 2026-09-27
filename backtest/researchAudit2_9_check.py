# -*- coding: utf-8 -*-
"""稽核 ② 9 攤平停利 甲 5、10 日 獨立查核（⛔ 不 import researchAudit2_9、researchAvg、avgdown、research11、researchH2）。
只 import backtest.data（讀檔）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_9_check.py

 ① 抽 300 筆（5、10 日）：自算 R ＝ 還原收盤(j_end) ÷ 還原開盤(s) − 1、R0 ＝ 0050 收盤(ffill，s＋H−1) ÷ 0050 開盤(s) − 1、
    X（跌：(R − 0.585%) − (R0 − 0.385%)；漲：(R0 − 0.385%) − R；登錄 甲 的式子自寫）⇒ ＝ events 檔
 ② 由 events_h5_h10.csv.gz 自算 X̄、曆月 CR0 CI、n_eff、出口、結果、X − y 的 CI ⇒ ＝ summary.json
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
D.DATA = SNAP
OUT = os.path.expanduser("~/tw-p17/backtest/resultsAudit2/9")
TOL = 1e-12


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, np.sqrt((s ** 2).sum()) / n, len(s)


def verdict(m, lo, hi, n, ne):
    if ne < 30:
        return "出口①", "—（樣本不足以分辨）"
    ex = "出口②" if ne < 100 else "出口③"
    return ex, ("結果①" if lo <= 0 <= hi else ("結果③" if m < 0 else "結果②"))


def main():
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    E = pd.read_csv(os.path.join(OUT, "events_h5_h10.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    cal = D.load_calendar()
    s50 = D.load_stock("0050", "twse", cal).df
    o50 = s50["open"].to_numpy(float); c50 = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy()
    RES = {}
    rng = np.random.default_rng(20260928); pick = E.iloc[np.sort(rng.choice(len(E), 300, replace=False))]
    mx = 0.0; cache = {}
    for r in pick.itertuples():
        if r.sid not in cache:
            cache[r.sid] = D.load_stock(r.sid, r.market, cal).df
        df = cache[r.sid]
        R = df["close"].to_numpy(float)[int(r.j_end)] / df["open"].to_numpy(float)[int(r.s)] - 1
        R0 = c50[int(r.s) + int(r.H) - 1] / o50[int(r.s)] - 1
        X = (R - 0.00585) - (R0 - 0.00385) if r.kind == "跌" else (R0 - 0.00385) - R
        mx = max(mx, abs(R - r.R), abs(R0 - r.R0), abs(X - r.X))
    RES["① 抽 300 筆 R、R0、X"] = {"最大差": mx, "過": mx <= TOL}
    bad = []
    for key, J in Sm["結果"].items():
        cell, h = key.split("_H"); H = int(h)
        if H not in (5, 10):
            continue
        kind = "跌" if cell == "攤平" else "漲"
        k = E[(E["kind"] == kind) & (E["H"] == H)]
        mon = np.array([str(cal[t])[:7] for t in k["T"]])
        m, se, ng = cr0(k["X"].to_numpy(float), mon); lo, hi = m - 1.96 * se, m + 1.96 * se
        ex, rs = verdict(m, lo, hi, len(k), min(len(k), ng))
        km = k[k["y_bar"].notna()]; mm = np.array([str(cal[t])[:7] for t in km["T"]])
        dm, dse, _ = cr0((km["X"] - km["y_bar"]).to_numpy(float), mm)
        if abs(m - J["X̄"]) > TOL or abs(lo - J["lo"]) > TOL or ex != J["出口"] or rs != J["結果"] or abs(dm - J["必附句_配對組"]["X−y"]["X̄"]) > TOL \
                or abs(km["y_bar"].mean() - J["必附句_配對組"]["y"]) > TOL:
            bad.append(key)
    RES["② 4 格（攤平／停利 × 5／10 日）X̄、CI、出口、結果、y、X − y"] = {"不符": bad, "過": not bad}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
