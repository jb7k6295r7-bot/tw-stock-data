# 甲 的獨立重算（向量化、不共用迴圈）：只在該股有效 K 棒日上，trust>0 的連續段長與段內累計
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17")); sys.path.insert(0, "backtest")
import researchH2 as H2
from backtest import researchp12 as P12, p4_features as P4F
D = H2.D; root = os.path.expanduser(f"~/h2data/{H2.SHA}/data")
cal = D.load_calendar(); uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsAFC/panel.csv.gz")
el = panel[(panel["eligible"].astype(bool)) & (panel["measure_date"] >= pd.Timestamp(P12.START))]
nA = 0; nabs = 0
for s, g in el.groupby("stock_id"):
    st = D.load_stock(s, uni.get(s, "twse"), cal)
    df = pd.DataFrame({"date": cal, "close": st.df["close"].to_numpy(float)})
    df = df[np.isfinite(df["close"])]                               # 只留有效 K 棒日
    fi = os.path.join(root, "stocks_inst", f"{s}.csv")
    a = pd.read_csv(fi, usecols=["date", "trust"]).drop_duplicates("date", keep="last") if os.path.exists(fi) else pd.DataFrame(columns=["date", "trust"])
    a["date"] = pd.to_datetime(a["date"])
    df = df.merge(a, on="date", how="left")
    pos_ = (df["trust"] > 0).astype(int)                             # NaN／absent ⇒ 0 ⇒ 斷
    grp = (pos_ == 0).cumsum()
    run = pos_.groupby(grp).cumsum()
    acc = df["trust"].where(pos_ == 1, 0).groupby(grp).cumsum()
    df["A"] = (run >= 4) & (acc / 1000 > 1000)
    m = df.set_index("date")["A"]
    nA += int(m.reindex(g["measure_date"]).fillna(False).sum())
print("獨立重算 甲成立：", nA)
