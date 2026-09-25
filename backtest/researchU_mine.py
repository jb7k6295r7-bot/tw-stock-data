# 本線獨立重算 PREREGU 判定格 D（⛔ 不 import researchU*）：b(x)＝分勝負事件中反彈比例；D ＝ 費氏位平均 − 鄰位平均；月分群 CI（delta 法：按月聚合）
import os, numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
e = pd.read_csv("resultsU/events_body_k5_H20.csv", dtype={"sid": str})
print(e["y"].value_counts(dropna=False).to_dict())
d = e[e["y"].isin([0, 1])].copy()
fib, nb = [38.2, 61.8], [30.0, 45.0, 55.0, 70.0]
b = d.groupby("pos")["y"].mean(); n = d.groupby("pos").size()
print("b(x)%", (b * 100).round(2).to_dict()); print("n", n.to_dict())
D = b[fib].mean() - b[nb].mean(); print("D pp", round(D * 100, 3))
# 月分群 bootstrap（B＝2000）
rng = np.random.default_rng(20260925); months = np.array(sorted(d["mon"].unique()))
G = {m: g for m, g in d.groupby("mon")}
bs = []
for _ in range(2000):
    s = pd.concat([G[m] for m in rng.choice(months, len(months))])
    bb = s.groupby("pos")["y"].mean(); bs.append(bb[fib].mean() - bb[nb].mean())
print("月分群 bootstrap 95% [{:+.3f}, {:+.3f}] pp".format(*np.percentile(np.array(bs) * 100, [2.5, 97.5])))
