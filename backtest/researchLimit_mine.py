# 本線獨立重算 PREREG限價 三格（⛔ 不 import researchLimit*）：D ＝ mean(r20_Lk) − mean(r20_M0)（放棄＝0 已在逐筆檔）；月分群 bootstrap
import os, numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
t = pd.read_csv("resultsLimit/trades.csv.gz", dtype={"sid": str})
t = t[t["r20_M0"].notna()]
print("筆數", len(t), "月數", t["month"].nunique(), "E(M0) {:+.3%}".format(t["r20_M0"].mean()))
rng = np.random.default_rng(20260925); months = np.array(sorted(t["month"].unique())); G = {m: g for m, g in t.groupby("month")}
idx = [rng.choice(months, len(months)) for _ in range(2000)]
for k in ("L1", "L2", "L3"):
    d = t[f"r20_{k}"] - t["r20_M0"]; D = d.mean()
    bs = [pd.concat([G[m] for m in ix]).pipe(lambda s: (s[f"r20_{k}"] - s["r20_M0"]).mean()) for ix in idx]
    print(k, "D {:+.3f}pp  月分群 bootstrap [{:+.3f}, {:+.3f}]".format(D * 100, *np.percentile(np.array(bs) * 100, [2.5, 97.5])))
