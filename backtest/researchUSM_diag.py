# -*- coding: utf-8 -*-
"""USREG-M 假訊號臂診斷（⛔ 未改任何定義、⛔ 不改判定；只寫彙總到 resultsUSM/body_diag_fake.json）。
用本體同一套 Stk（S1 斷點、T+1 規則）與 ~/us_work/usm/body/ew20.csv，算：全體在指數股-日的平均 X；每檔等權；照各畫法每檔真事件數加權的平均 X。
跑法：PYTHONPATH=$HOME/tw-p17 python backtest/researchUSM_diag.py（需先跑 researchUSM_body）。"""
# 假訊號臂診斷（只彙總）：全體在指數股-日的平均 X、以及照各畫法「每檔真事件數」加權的平均 X（＝不排除版假訊號的期望）
import os, json, numpy as np, pandas as pd
from backtest import us_data as U
from backtest import researchUSM as RU
from backtest import researchUSM_body as B
calF = U.load_calendar(); cal = calF[calF >= B.CAL0]
w0 = int(cal.searchsorted(U.WINDOW[0])); w1 = int(cal.searchsorted(U.WINDOW[1])); wE = w1 - 21
ew = pd.read_csv(os.path.expanduser("~/us_work/usm/body/ew20.csv")).set_index("date")["EW20"].reindex([str(d.date()) for d in cal]).to_numpy()
W = {m: pd.read_csv(os.path.expanduser("~/us_work/usm/body/events_X_%s.csv" % m), dtype={"sid": str})["sid"].value_counts() for m in B.MAIN}
tot = []; per = {}
for t in [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]:
    df = U.load_ohlc(t, scope="panel"); A = RU.prep(df, cal)
    if not len(A["bars"]): continue
    S = B.Stk(t, A, B.low_aligned(df, cal), RU.member_array(t, cal), RU.span_start_array(t, cal), w0, wE)
    xs = []
    for T in range(w0, wE + 1):
        if not (S.member[T] and S.valid[T]) or S.brk(T, T + 21) or not S.valid[T + 1]: continue
        xs.append(S.px[T + 21] / S.o[T + 1] - 1 - ew[T + 1])
    if xs:
        per[t] = (float(np.mean(xs)), len(xs)); tot += xs
out = {"全體在指數股日_平均X": float(np.mean(tot)), "股日數": len(tot),
       "每檔等權_平均X": float(np.mean([v[0] for v in per.values()]))}
for m in B.MAIN:
    w = W[m]; k = [t for t in w.index if t in per]
    out["依%s每檔真事件數加權_平均X" % m] = float(sum(per[t][0] * w[t] for t in k) / sum(w[t] for t in k))
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open(os.path.expanduser("~/tw-p17/backtest/resultsUSM/body_diag_fake.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
