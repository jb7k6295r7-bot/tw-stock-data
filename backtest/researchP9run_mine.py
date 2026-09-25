# 本線獨立重算 P9 12 格標籤（⛔ 不 import researchP9run*）
import os, numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
s = pd.read_csv("resultsP9run/seeds_arms.csv"); print(s.columns.tolist()[:12], len(s))
A = (0.24020209886370614, -0.3395700527611012); ar = A[0] / abs(A[1])
arm = [c for c in s.columns if c in ("arm", "格", "cell")][0]
cc = [c for c in s.columns if c.lower() in ("cagr", "年化")][0]; mc = [c for c in s.columns if c.lower() in ("mdd", "回落")][0]
for a, g in s.groupby(arm, sort=False):
    c, m = g[cc].median(), g[mc].median(); r = c / abs(m)
    lab = "不合格" if not c > A[0] else ("合格" if r >= ar else "另列")
    print("{:<14} n={} 年化 {:+.2%} 回落 {:+.2%} 比值 {:.4f} ⇒ {}".format(str(a), len(g), c, m, r, lab))
