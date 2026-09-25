# 本線獨立抽驗 PREREG型態全量（⛔ 不 import researchPatAll*）：抽 6 格從逐筆檔重算 dX̄、CI、Bonferroni；全表重數族彙總
import os, numpy as np, pandas as pd
os.chdir(os.path.expanduser("~/tw-p17/backtest/resultsPatAll/body"))
c = pd.read_csv("cells.csv", encoding="utf-8-sig")
j = c[c["身分"] == "判定格"]
print("判定格", len(j), "｜H20", int((j.H == 20).sum()), "H60", int((j.H == 60).sum()))
print(j.groupby(["H", "族"])["結果"].value_counts().unstack(fill_value=0).to_string())
print("Bonferroni 不含 0：", int(j["bonf不含0"].sum()))
z = 3.6348
rng = np.random.default_rng(20260925)
pick = j.sample(6, random_state=7)
for r in pick.itertuples():
    e = pd.read_csv(f"events/events_{r.vid}.csv.gz", usecols=["H", "dX", "分群", "配對"])
    e = e[(e.H == r.H) & (e["配對"] == "有")]
    x = e["dX"].to_numpy(float); n = len(x); mu = x.mean()
    s = pd.Series(x - mu).groupby(e["分群"].to_numpy()).sum(); se = np.sqrt((s ** 2).sum()) / n
    print(r.vid, r.H, "n", n, "vs", int(r.n), "dX̄ {:+.6f} vs {:+.6f}".format(mu, r._18 if False else getattr(r, "dX̄") if hasattr(r, "dX̄") else float("nan")),
          "CI [{:+.5f}, {:+.5f}] vs [{:+.5f}, {:+.5f}]".format(mu - 1.96 * se, mu + 1.96 * se, r.lo, r.hi), "bonf [{:+.5f}, {:+.5f}] vs [{:+.5f}, {:+.5f}]".format(mu - z * se, mu + z * se, r.bonf_lo, r.bonf_hi))
