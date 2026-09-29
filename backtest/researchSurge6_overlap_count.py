"""飆股 seq6 描述追加：同時有幾個特徵，5 個以上再拆開（0～14 逐個＋累計）。沿用 researchSurge6_overlap 的載入與格。"""
import os, numpy as np, pandas as pd
from backtest import researchSurge6_overlap as O
uni, cal, Qs, inseg, bar, h6, E = O.load()
code = np.array([c for _, _, c in O.FEATS], np.int8); K = len(O.FEATS)
ec, es, ed = E["cell"].astype(int), E["s"].astype(int), E["d"].astype(int)
cnt = np.bincount(ec, minlength=250); cells = [c for c in range(250) if cnt[c] >= O.MINEV]
dist = lambda q: np.bincount((q == code[None, :]).sum(1), minlength=K + 1) / len(q)
SUR = {c: dist(Qs[:, es[ec == c], ed[ec == c]].T) for c in cells}
GEN = {}
rows = bar & inseg[None, :]
for H in sorted({O.HS[c // 10] for c in cells}):
    ss, tt = np.nonzero(rows & (h6 >= H)); GEN[H] = dist(Qs[:, ss, tt].T)
R = []
for i in range(K + 1):
    x = [SUR[c][i] for c in cells]; y = [GEN[O.HS[c // 10]][i] for c in cells]
    xc = [SUR[c][i:].sum() for c in cells]; yc = [GEN[O.HS[c // 10]][i:].sum() for c in cells]
    R.append({"同時有": i, "飆股 中位": np.median(x), "一般 中位": np.median(y), "至少這麼多 飆股": np.median(xc), "至少這麼多 一般": np.median(yc),
              "至少 飆股 p10": np.percentile(xc, 10), "至少 飆股 p90": np.percentile(xc, 90)})
R = pd.DataFrame(R); R.to_csv(os.path.join(O.OUT, "count_dist_full.csv"), index=False, float_format="%.5g")
pd.set_option("display.width", 200); print(R.round(4).to_string(index=False))
