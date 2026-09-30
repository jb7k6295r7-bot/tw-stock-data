# 診斷（只看 2024 年）：第一～四款近似的誤報落在哪
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
sys.argv = ["x"]
import importlib.util
spec = importlib.util.spec_from_file_location("cb", "backtest/tradingview/calib.py"); cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)
S5, ED = cb.S5, cb.ED
uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
ATT, DISP = S5.SF.att_disp(S5.MAIN, cal)
a_raw = pd.read_csv(os.path.join(S5.MAIN, "meta", "attention.csv"), dtype={"stock_id": str, "date": str}, usecols=["stock_id", "date", "reason"])
a_raw = a_raw[(a_raw["date"] >= "2024-01-01") & (a_raw["date"] <= "2024-12-31")]
a_raw["p14"] = a_raw["reason"].fillna("").str.contains(r"第[一二三四]款")
ATT14 = {s: set(cal.searchsorted(pd.to_datetime(g.loc[g["p14"], "date"]))) for s, g in a_raw.groupby("stock_id")}
ATTall = {s: set(cal.searchsorted(pd.to_datetime(g["date"]))) for s, g in a_raw.groupby("stock_id")}
y0, y1 = cal.searchsorted(pd.Timestamp("2024-01-01")), cal.searchsorted(pd.Timestamp("2024-12-31"), side="right") - 1
cat = {}
def add(k): cat[k] = cat.get(k, 0) + 1
for s in range(len(uni)):
    sid, mk = uni.loc[s, "stock_id"], uni.loc[s, "market"]
    p_ = os.path.join(S5.ST, "stocks", sid + ".csv")
    if not os.path.exists(p_): continue
    raw = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "close", "volume", "amount", "shares"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float).copy(); rc[~(rc > 0)] = np.nan
    idx = np.flatnonzero(np.isfinite(rc) & bar[s])
    if len(idx) < 100: continue
    c = rc[idx]; v = pd.to_numeric(raw["volume"], errors="coerce").to_numpy(float)[idx]; amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)[idx]
    sh = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float)[idx].copy()
    A = cb.attention_approx(c, v, amt, sh, mk, 6)
    P = A[1] | A[2] | A[3] | A[4]
    rin = np.zeros(n, bool)
    for a_, b_ in DISP.get(sid, []): rin[max(a_, 0):min(b_, n - 1) + 1] = True
    r6 = c / cb.shift(c, 6) - 1
    for k in np.flatnonzero(P & (idx >= y0) & (idx <= y1)):
        d = idx[k]
        if d in ATT14.get(sid, ()):
            add("TP"); add("TP:真處置中") if rin[d] else None; continue
        tag = []
        if rin[d]: tag.append("真處置中")
        if d in ATTall.get(sid, ()): tag.append("真注意但別款")
        if r6[k] < 0: tag.append("跌")
        thr = cb.PAR[mk]["c34"]
        if abs(r6[k]) <= thr + 0.03: tag.append("r6在門檻+3%內")
        only = [j for j in (1, 2, 3, 4) if A[j][k]]
        tag.append("款" + "".join(map(str, only)))
        add("FP")
        for t_ in tag: add("FP:" + t_)
print({k: v for k, v in sorted(cat.items(), key=lambda x: -x[1])})
