import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17")); sys.path.insert(0, "backtest")
import researchH2 as H2
from backtest import tradability as T
D = H2.D; cal = D.load_calendar()
ten = ["6211", "1256", "5266", "4703", "6135", "3126", "5395", "8462", "3452", "8913"]
stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str); U = set(H2.UG.gate3(stocks)["stock_id"])
trad = T.build(set(ten) & U, cal); st = T.delist_status(trad, cal, official=T.load_official())
for s in ten:
    print(s, "gate3" if s in U else "不在 gate3", st.get(s, {}).get("status"), st.get(s, {}).get("gap"))
# C5 BTC 永續版逐年（描述）
from backtest import researchc1 as C, researchc2 as C2, researchc5 as C5, researchc5_perp as P
PERP = "2c37babc5c2e732702c962ac985630da0effcd31"
w = P.window("BTC"); p = P.load_perp("BTC", PERP); pm = p.set_index("date").reindex(w["date"])
fbd, _ = C2.fund_days("BTC", w["date"].to_numpy(), P.man)
c, h = w["close"].to_numpy(float), w["high"].to_numpy(float)
rs, _, _, _ = C5.engine(c, h, fbd, 0.02); rp, _, _, _ = C5.engine(c, h, fbd, 0.02, pclose=pm["close"].to_numpy(float), phigh=pm["high"].to_numpy(float))
d = pd.to_datetime(w["date"].to_numpy()[1:])
out = {}
for nm, r in (("現貨版", rs), ("永續版", rp)):
    e = pd.Series(np.cumprod(1 + np.asarray(r)), index=d[:len(r)]); ye = e.groupby(e.index.year).last(); pv = ye.shift(1); pv.iloc[0] = 1.0
    out[nm] = {int(k): float(v) for k, v in (ye / pv - 1).items()}
print(json.dumps(out, ensure_ascii=False))
json.dump(out, open("backtest/resultsc5/perp_yearly_btc.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("年化 現貨", C.cagr(rs), "永續", C.cagr(rp))
