# -*- coding: utf-8 -*-
"""Δ_vol 的陷阱查核：被挑中的「低波動」股，是不是停牌／無成交（往前補值的收盤 ⇒ 報酬 0 ⇒ vol60 假低、回落假淺）。
⛔ 只看被挑中的股票的性質，⛔ 不改任何定義。"""
import bisect, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchI as I
from backtest import data as D
cal, ncal, closes, opens, sigs = I.setup()
sg = sigs[("S1", "T1", "*")]
ent = sorted(set(sg["entry_pos"]))
T = pd.read_csv("backtest/resultsI/deltas_by_segment.csv")
uni = D.load_universe().set_index("stock_id")["market"]
traded = {}
def trd(s):
    if s not in traded:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        traded[s] = st.df["traded"].to_numpy() if st is not None else np.zeros(ncal, bool)
    return traded[s]
rows = []
for r in T.itertuples():
    p, v, n_h = int(r.峰_pos), int(r.谷_pos), int(r.n_h)
    e_last = ent[bisect.bisect_right(ent, p) - 1]
    pool = sorted(set(sg.loc[sg["entry_pos"] == e_last, "sid"]))
    vol = {}
    for s in pool:
        x = np.asarray(closes[s][p - 60:p + 1], float); x = x[1:] / x[:-1] - 1
        vol[s] = float(np.std(x[np.isfinite(x)], ddof=1))
    pick = sorted(pool, key=lambda s: (vol[s], s))[:n_h]
    for s in pick:
        t = trd(s)
        rows.append({"seed": r.seed, "段": r.段, "sid": s, "vol60": vol[s],
                     "回看無成交日比": 1 - t[p - 59:p + 1].mean(), "段內無成交日比": 1 - t[p:v + 1].mean(),
                     "段內報酬": float(closes[s][v]) / float(closes[s][p]) - 1})
X = pd.DataFrame(rows)
print("被挑中的持股列數 {}（{} 檔不同）".format(len(X), X["sid"].nunique()))
print("vol60 分佈：", X["vol60"].describe(percentiles=[.05, .5]).round(4).to_dict())
print("vol60 == 0 的：{}｜回看窗無成交日 > 20% 的：{}｜段內無成交日 > 20% 的：{}".format(
    int((X["vol60"] == 0).sum()), int((X["回看無成交日比"] > .2).sum()), int((X["段內無成交日比"] > .2).sum())))
print("段內報酬 == 0（整段持平）的：{}".format(int((X["段內報酬"] == 0).sum())))
print("被挑最多次的前 10 檔：", X["sid"].value_counts().head(10).to_dict())
X.to_csv("backtest/resultsI/vol_picks_check.csv", index=False)
