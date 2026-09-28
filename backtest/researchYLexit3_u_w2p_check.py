# -*- coding: utf-8 -*-
"""使用者版 v1 ＋ W2′：簡短查核（⛔ 不 import researchYLexit3_u_w2p、researchYLexit3_u、researchYLexit3、researchYLexit、researchYLexit3_b）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLexit3_u_w2p_check.py

① 抽 30 檔營量訊號股（主窗），自己讀 D.load_stock（main 快照、traded 有效 K 棒）算原 W2 與 W2′ 的觸發日 ⇒ 對 w2_triggers.csv.gz（主）集合相同
② 5475 德宏 2025-12-04：自己算四個條件並列出；該根原 W2 成立、W2′ 不成立 ⇒ 且在 w2_dropped.csv
③ summary 的閘全為真；w2_dropped.csv 各（世界, H）筆數 ＝ summary
⇒ backtest/resultsYLexit3/user_v1_w2p/check.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D

OUT = "backtest/resultsYLexit3/user_v1_w2p"
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
TR_ = pd.read_csv(os.path.join(OUT, "w2_triggers.csv.gz"), dtype={"sid": str})
DR = pd.read_csv(os.path.join(OUT, "w2_dropped.csv"), dtype={"sid": str})
cal = D.load_calendar(); mk = D.load_universe().set_index("stock_id")["market"]
w0, w1 = int(cal.searchsorted(pd.Timestamp("2017-03-02"))), int(cal.searchsorted(pd.Timestamp("2026-08-24")))
errs = []; info = {}


def flags(sid):
    df = D.load_stock(sid, mk.get(sid, "twse"), cal).df
    idx = np.flatnonzero(df["traded"].to_numpy())
    o, h, c = (df[k].to_numpy(float)[idx] for k in ("open", "high", "close"))
    v = df["volume"].to_numpy(float)[idx]
    vs = pd.Series(v); vm = vs.shift(1).rolling(20, min_periods=20).mean().to_numpy()
    hh = pd.Series(h).shift(1).rolling(60, min_periods=60).max().to_numpy()
    ma60 = pd.Series(c).rolling(60, min_periods=60).mean().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        r1 = np.r_[np.nan, c[1:] / c[:-1] - 1]
        base = (c >= hh * 0.95) & (v >= vm * 2)
        old = base & ((c - o) / o <= -0.04)
        new = base & (c >= ma60 * 1.2) & (c < o) & (r1 <= -0.04)
    d = [str(x.date()) for x in cal[idx]]
    return idx, d, old, new, {"c": c, "o": o, "r1": r1, "hh": hh, "ma60": ma60, "v": v, "vm": vm}


# ①
A = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), dtype={"sid": str})
rng = np.random.default_rng(20260928)
sids = sorted(set(A["sid"]) & set(TR_.loc[TR_["世界"] == "主", "sid"]) | set(A["sid"]))
smp = sorted(rng.choice(sorted(set(A["sid"])), size=30, replace=False))
nb = 0
for s in smp:
    idx, d, old, new, _ = flags(s)
    m = (idx >= w0) & (idx <= w1)
    t = TR_[(TR_["世界"] == "主") & (TR_["sid"] == s)]
    t = t[(t["日期"] >= str(cal[w0].date())) & (t["日期"] <= str(cal[w1].date()))]
    for nm, f, col in (("W2", old, "W2"), ("W2′", new, "W2p")):
        mine = {d[j] for j in np.flatnonzero(f & m)}
        ref = set(t.loc[t[col].astype(str) == "True", "日期"])
        if mine != ref:
            nb += 1; errs.append(f"① {s} {nm} 自算 {len(mine)} 檔 {len(ref)}")
info["① 抽 30 檔 觸發日集合不同"] = nb

# ②
idx, d, old, new, X = flags("5475")
j = d.index("2025-12-04")
info["② 5475 2025-12-04"] = {"收": X["c"][j], "開": X["o"][j], "對前收": X["r1"][j], "60高×0.95": X["hh"][j] * 0.95, "MA60×1.2": X["ma60"][j] * 1.2, "量÷均量": X["v"][j] / X["vm"][j],
                             "原 W2": bool(old[j]), "W2′": bool(new[j]), "在 w2_dropped": bool(((DR["sid"] == "5475") & (DR["警訊根"] == "2025-12-04")).any())}
if not (old[j] and not new[j] and info["② 5475 2025-12-04"]["在 w2_dropped"]):
    errs.append("② 德宏")

# ③
if not all(S["閘"].values()):
    errs.append("③ 閘")
cnt = {f"{wk} H{H}": int(((DR["世界"] == wk) & (DR["H"] == H)).sum()) for wk in ("主", "早年") for H in (40, 60, 80)}
if cnt != S["逐筆（原 W2 判、W2′ 不判）筆數"]:
    errs.append("③ 逐筆筆數")
info["③ 逐筆筆數（自算）"] = cnt
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(info, ensure_ascii=False, default=float)); [print("  ⛔", e) for e in errs]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
