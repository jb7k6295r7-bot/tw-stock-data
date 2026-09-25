# 獨立驗（甲）事件：⛔ 不呼叫 stop_fractal／trendline_m；只讀 T、T−1 當天收盤與取點 high（⛔ 不算任何報酬）
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); import researchH2 as H2
D = H2.D; cal = D.load_calendar(); uni = D.load_universe().set_index("stock_id")["market"]
e = pd.read_csv(os.path.expanduser("~/tw-p17/backtest/resultsM/events_甲.csv"), dtype={"sid": str})
e = e[e["狀態"] == "保留"].sample(12, random_state=20260925)
print("取點 範例：", e["取點"].iloc[0], "確認日", e["確認日"].iloc[0])
ok = 0
for r in e.itertuples():
    st = D.load_stock(r.sid, uni.get(r.sid, "twse"), cal); df = st.df
    v = df[np.isfinite(df["close"].to_numpy(float))]
    d = list(v.index); pos = {x: i for i, x in enumerate(d)}
    hi, cl, op = v["high"].to_numpy(float), v["close"].to_numpy(float), v["open"].to_numpy(float)
    p1, p2 = [pos[pd.Timestamp(x)] for x in str(r.取點).replace("|", ",").split(",")[:2]]
    t = pos[pd.Timestamp(r.T)]
    piv = lambda i: i >= 5 and i + 5 < len(hi) and all(hi[i] > hi[i - k] for k in range(1, 6)) and all(hi[i] > hi[i + k] for k in range(1, 6))
    line = lambda i: hi[p1] + (hi[p2] - hi[p1]) / (p2 - p1) * (i - p1)
    body = all(max(op[i] if np.isfinite(op[i]) else cl[i], cl[i]) <= line(i) + 1e-9 for i in range(p1 + 1, p2))
    conf = p2 + 5
    c = [piv(p1), piv(p2), hi[p2] < hi[p1], body, t > conf, t - conf <= 60, conf - p1 <= 120, cl[t] > line(t), cl[t - 1] <= line(t - 1),
         str(d[conf].date()) == str(pd.Timestamp(r.確認日).date())]
    ok += all(c)
    print(r.sid, r.T, "全過" if all(c) else f"⛔ {c}")
print("獨立驗（甲）", ok, "／", len(e))
