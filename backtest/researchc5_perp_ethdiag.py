# -*- coding: utf-8 -*-
"""C5 永續價複核的 ETH 強平診斷（⛔ 只描述、不改判定、不進 N）：找觸發強平的那根，並把【只那一根】的永續 high 換成現貨 high 看其餘期間。"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
sys.argv = ["x"]
from backtest import researchc5_perp as P, researchc5 as C5, researchc2 as C2
import inspect
SHA = "2c37babc5c2e732702c962ac985630da0effcd31"
s = "ETH"
w = P.window(s); p = P.load_perp(s, SHA)
start = max(w["date"].iloc[0], p["date"].iloc[0]); w = w[w["date"] >= start].reset_index(drop=True)
pm = p.set_index("date").reindex(w["date"])
fbd, _ = C2.fund_days(s, w["date"].to_numpy(), P.man)
c, h = w["close"].to_numpy(float), w["high"].to_numpy(float)
rp, lp, a3, a4 = C5.engine(c, h, fbd, 0.02, pclose=pm["close"].to_numpy(float), phigh=pm["high"].to_numpy(float))
print("liq", lp)
k = lp if isinstance(lp, (int, np.integer)) else None
print(type(lp))
r = (pm["high"].to_numpy(float) / h - 1)
cc = (pm["close"].to_numpy(float) / c - 1)
d = pd.DataFrame({"date": w["date"], "spot_c": c, "perp_c": pm["close"].to_numpy(float), "spot_h": h, "perp_h": pm["high"].to_numpy(float), "h_basis": r, "c_basis": cc})
print(d.sort_values("h_basis", ascending=False).head(5).to_string())
print("close basis p1/p99:", np.nanpercentile(cc, [1, 50, 99]))
print(inspect.signature(C5.engine))
from backtest import researchc1 as C
ph = pm["high"].to_numpy(float).copy(); i = int(np.flatnonzero(w["date"].to_numpy() == "2020-03-13")[0]); ph[i] = h[i]
r2, l2, _, _ = C5.engine(c, h, fbd, 0.02, pclose=pm["close"].to_numpy(float), phigh=ph)
print("diag 只換 2020-03-13 一根：強平", l2, "年化", C.cagr(r2), "回落", C.mdd(r2))
rs, ls, _, _ = C5.engine(c, h, fbd, 0.02)
print("現貨版", C.cagr(rs), C.mdd(rs), ls)
print("perp 2020-03-13 row:", p[p.date == "2020-03-13"][["open", "high", "low", "close", "volume", "count"]].to_string())
print("spot 2020-03-13 row:", w[w.date == "2020-03-13"].to_string())
