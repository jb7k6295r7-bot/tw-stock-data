import os, numpy as np, pandas as pd, json
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
for k in ("甲", "乙", "丙"):
    e = pd.read_csv(f"resultsM_body/events_X_{k}.csv", dtype={"sid": str})
    xc = [c for c in e.columns if c in ("X", "x")][0]; tc = "T_date"
    x = e[xc].to_numpy(float); m = pd.to_datetime(e[tc]).dt.to_period("M")
    n = len(x); mu = x.mean()
    # 月分群 SE（群和的變異）
    g = pd.Series(x - mu).groupby(m.values).sum(); G = len(g)
    se = np.sqrt(G / (G - 1) * (g ** 2).sum()) / n
    print(k, n, "平均 X {:+.4%}  CI [{:+.4%}, {:+.4%}]  群 {}".format(mu, mu - 1.96 * se, mu + 1.96 * se, G))
f = pd.read_csv("resultsM_body/fake_arm.csv"); print(f.columns.tolist()); print(f.head(3).to_string())
