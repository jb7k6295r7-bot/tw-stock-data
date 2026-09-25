# 本線獨立重算 PREREG攤平停利 甲 4 格（⛔ 不 import researchAvg*、avgdown）
import os, numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
e = pd.read_csv("resultsAvg/A_events_kept.csv.gz")
print(e.columns.tolist())
print(e["kind"].unique(), sorted(e["H"].unique()))
def cr0(x, g):
    x = np.asarray(x, float); n = len(x); mu = x.mean(); s = pd.Series(x - mu).groupby(np.asarray(g)).sum()
    return mu, np.sqrt((s ** 2).sum()) / n, s.size
for k in e["kind"].unique():
    for H in (20, 60):
        d = e[(e["kind"] == k) & (e["H"] == H)]
        mu, se, G = cr0(d["X"], d["cl"])
        dd = d[d["d"].notna()]; m2, s2, _ = cr0(dd["d"], dd["cl"])
        print("{} H{} n={} X̄ {:+.3%} CI [{:+.3%}, {:+.3%}] 群 {}｜X−y {:+.3%} [{:+.3%}, {:+.3%}]".format(k, H, len(d), mu, mu - 1.96 * se, mu + 1.96 * se, G, m2, m2 - 1.96 * s2, m2 + 1.96 * s2))
