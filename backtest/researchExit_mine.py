# 本線獨立重算 PREREG出場訊號 6 格（⛔ 不 import researchExit*）＋把 events_kept 依訊號拆檔（GitHub 單檔 ＜ 100MB）
import os, numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
e = pd.read_csv("resultsExit/events_kept.csv.gz", dtype={"sid": str})
print("列", len(e), "rule", e["rule"].value_counts().to_dict(), "H", sorted(e["H"].unique()))
def cr0(x, g):
    x = np.asarray(x, float); n = len(x); mu = x.mean(); s = pd.Series(x - mu).groupby(np.asarray(g)).sum()
    return mu, np.sqrt((s ** 2).sum()) / n, s.size
for g in ("甲", "乙", "丙"):
    for H, cl in ((20, "month"), (60, "blk60")):
        d = e[(e["rule"] == "close") & (e["g"] == g) & (e["H"] == H)]
        mu, se, G = cr0(d["R"], d[cl])
        print("{} H{} n={} E {:+.2%} CI [{:+.2%}, {:+.2%}] 群 {}".format(g, H, len(d), mu, mu - 1.96 * se, mu + 1.96 * se, G))
for g in ("甲", "乙", "丙"):
    e[e["g"] == g].to_csv(f"resultsExit/events_kept_{g}.csv.gz", index=False, compression="gzip")
print({g: os.path.getsize(f"resultsExit/events_kept_{g}.csv.gz") for g in ("甲", "乙", "丙")})
