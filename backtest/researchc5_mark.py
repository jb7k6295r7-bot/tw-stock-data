# -*- coding: utf-8 -*-
"""C5 標記價描述臂（裁定線 seq155 §二、seq156 §八；⛔ 只影響措辭、⛔ 不翻判定、⛔ 不計 N）。

定義（本線 1519 寫死、裁定 seq156 §八 收下）：只把「當日永續 high」換成「當日標記價 high」判空方強平，其餘照 C5 引擎
  ⇒ C5.engine(close=現貨 close, high=現貨 high, fbd, 0.02, pclose=永續 close, phigh=標記價 high)
  永續 close 釘 main 2c37babc5c（與 perp_recheck 同）；標記價釘 main 3e521f5416 data/crypto_mark/
  ⛔ 1h 不做；⛔ 不追加其他替代定義
閘門：G1 回歸（researchc5_perp.gates：不給永續價 ⇒ 與交件 summary.json 逐位同）先過；
      G3 本支：phigh 用永續 high 時，必須逐位重現 perp_recheck.json 的永續版（證明本支接線與複核同一條）
"""
import os, sys, io, json, subprocess
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C, researchc2 as C2, researchc5 as C5, researchc5_perp as P

PERP, MARK = "2c37babc5c2e732702c962ac985630da0effcd31", "3e521f5416"


def load_mark(sym):
    r = subprocess.run(["git", "show", f"{MARK}:data/crypto_mark/{sym}USDT.csv"], cwd=os.path.expanduser("~/tw-stock-data"), capture_output=True, text=True, check=True)
    d = pd.read_csv(io.StringIO(r.stdout))
    assert list(d.columns) == P.HDR, list(d.columns)
    assert (d["open_time"] % 86_400_000 == 0).all()
    d["date"] = pd.to_datetime(d["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    assert (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1 == len(d), "⛔ 標記價有缺日"
    return d


P.gates()
REF = json.load(open("backtest/resultsc5/perp_recheck.json", encoding="utf-8"))
out = {"永續 commit": PERP, "標記價 commit": MARK, "定義": "只把當日永續 high 換成當日標記價 high 判強平；其餘照 C5（⛔ 不翻判定）"}
for s in ("BTC", "ETH"):
    w = P.window(s); p = P.load_perp(s, PERP); m = load_mark(s)
    start = max(w["date"].iloc[0], p["date"].iloc[0], m["date"].iloc[0])
    w = w[w["date"] >= start].reset_index(drop=True)
    pm = p.set_index("date").reindex(w["date"]); mm = m.set_index("date").reindex(w["date"])
    assert pm["close"].notna().all() and mm["high"].notna().all()
    fbd, _ = C2.fund_days(s, w["date"].to_numpy(), P.man)
    c, h = w["close"].to_numpy(float), w["high"].to_numpy(float)
    rp, lp, _, _ = C5.engine(c, h, fbd, 0.02, pclose=pm["close"].to_numpy(float), phigh=pm["high"].to_numpy(float))
    assert C.cagr(rp) == REF[s]["永續版"]["年化"], "⛔ G3：接線與 perp_recheck 不同"
    rm, lm, _, _ = C5.engine(c, h, fbd, 0.02, pclose=pm["close"].to_numpy(float), phigh=mm["high"].to_numpy(float))
    ratio = (mm["high"] / pm["high"]).to_numpy(float)
    rec = {"窗": [start, w["date"].iloc[-1]], "永續版（複核值）": REF[s]["永續版"], "標記價版": {"年化": C.cagr(rm), "回落": C.mdd(rm), "強平": lm is not None, "強平根": None if lm is None else w["date"].iloc[int(lm)]},
           "標記high÷永續high": {"min": float(np.nanmin(ratio)), "p1": float(np.nanpercentile(ratio, 1)), "中位": float(np.nanmedian(ratio)), "p99": float(np.nanpercentile(ratio, 99)), "max": float(np.nanmax(ratio))}}
    if s == "ETH":
        i = int(np.flatnonzero(w["date"].to_numpy() == "2020-03-13")[0])
        rec["2020-03-13"] = {"永續 high": float(pm["high"].iloc[i]), "標記價 high": float(mm["high"].iloc[i]), "現貨 high": float(h[i])}
    out[s] = rec
    print(s, json.dumps(rec, ensure_ascii=False, default=float))
json.dump(out, open("backtest/resultsc5/mark_desc.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
