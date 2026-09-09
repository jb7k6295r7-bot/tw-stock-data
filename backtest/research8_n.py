"""研究八追加：N＝5/10/20 的種子離散度（K線線 11:05 Q2）。只算 H60 與 A3、H20，100 種子。"""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import data as D
from backtest.research8 import simulate, SETS, SPLIT, HERE

cal = D.load_calendar(); ncal = len(cal); split_pos = int(cal.searchsorted(pd.Timestamp(SPLIT)))
ex = pd.read_csv(os.path.join(HERE, "results5", "exits.csv.gz"), dtype={"stock_id": str})
REPS = 100
rows = []
t0 = time.time()
for set_code in SETS:
    sig = ex[ex["set"] == set_code]
    for n in (5, 10, 20):
        res = {}
        for rule in ("H60", "A3", "H20"):
            cs = np.array([simulate(sig, rule, n, np.random.default_rng(7000 + r), ncal, split_pos)[1]["cagr"] for r in range(REPS)])
            res[rule] = cs
            rows.append(dict(set=set_code, N=n, rule=rule, med=np.median(cs), p10=np.percentile(cs, 10), p90=np.percentile(cs, 90),
                             spread=np.percentile(cs, 90) - np.percentile(cs, 10)))
        d = res["A3"] - res["H60"]
        rows.append(dict(set=set_code, N=n, rule="A3-H60", med=np.median(d), p10=np.percentile(d, 10), p90=np.percentile(d, 90),
                         spread=np.percentile(d, 90) - np.percentile(d, 10),
                         same=float(np.mean(np.sign(d) == np.sign(np.median(d))))))
    print(set_code, f"{time.time()-t0:.0f}s", file=sys.stderr)
df = pd.DataFrame(rows)
for c in ("med", "p10", "p90", "spread", "same"):
    if c in df: df[c] = (df[c] * 100).round(1)
print(df.to_string(index=False))
df.to_csv(os.path.join(HERE, "results8", "dispersion_n.csv"), index=False)
