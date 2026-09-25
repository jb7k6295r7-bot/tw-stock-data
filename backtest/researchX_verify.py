# 本線獨立重算（⛔ 不 import researchX）：乙 X 平均＋月分群 CI；甲 D_A(60)＝達成率差＋月分群 CI
import os, numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
def cl(x, m):
    x = np.asarray(x, float); n = len(x); mu = x.mean(); g = pd.Series(x - mu).groupby(np.asarray(m)).sum(); G = len(g)
    se = np.sqrt(G / (G - 1) * (g ** 2).sum()) / n; return mu, mu - 1.96 * se, mu + 1.96 * se
for k in ("box", "cup", "w", "hs", "flag", "trend"):
    b = pd.read_csv(f"resultsX/B_{k}.csv.gz"); mu, lo, hi = cl(b["X"], b["month"])
    print("乙", k, len(b), "X {:+.2f} [{:+.2f}, {:+.2f}] pp".format(mu * 100, lo * 100, hi * 100))
for k in ("box", "cup", "w", "hs", "flag"):
    a = pd.read_csv(f"resultsX/A_{k}.csv.gz")
    for H in (60, 120):
        mu, lo, hi = cl(a[f"d_{H}"], a["month"])
        print("甲", k, len(a), f"D_A({H})", "{:+.2f} [{:+.2f}, {:+.2f}] pp".format(mu * 100, lo * 100, hi * 100))
