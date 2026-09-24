# -*- coding: utf-8 -*-
"""批2 結算備用（⛔ 結算由裁定線做；本支只算數）：C5 出口② 的兩格（BTC、ETH）在批2 N＝13 下的 Bonferroni 調整 CI。
照台帳 §六：捷徑不成立 ⇒ B ＝ 2,000 × N ＝ 26,000 次重抽；同一方法（stationary bootstrap、Politis–White L）、種子 20260923；
雙尾 α＝0.05／13 ⇒ 取 0.1923% 與 99.8077% 百分位。"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C, researchc2 as C2, researchc5 as C5, funding as F
N_CELLS = 13
B = 2000 * N_CELLS
a = 0.05 / N_CELLS
man = F.load_manifest(path=os.path.join(C2.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
R = {r["coin"]: r for r in json.load(open("backtest/resultsc5/summary.json", encoding="utf-8"))}
out = {}
for s in ("BTC", "ETH"):
    d = C2.load_px(s); da = d["date"].to_numpy()
    i0 = int(np.flatnonzero(da == R[s]["窗首（建倉日）"])[0]); i1 = int(np.flatnonzero(da == R[s]["窗尾"])[0])
    close, high, dates = d["close"].to_numpy(float)[i0:i1 + 1], d["high"].to_numpy(float)[i0:i1 + 1], da[i0:i1 + 1]
    fbd, _ = C2.fund_days(s, dates, man)
    r, liq, _, _ = C5.engine(close, high, fbd, 0.02)
    L = C.politis_white_block(r); assert L == R[s]["主格"]["L"]
    smp = C5.boot_cagr(r, L, np.random.default_rng(C.SEED), B)
    lo, hi = float(np.percentile(smp, 100 * a / 2)), float(np.percentile(smp, 100 * (1 - a / 2)))
    out[s] = {"B": B, "α（雙尾）": a, "L": L, "調整後 CI": [lo, hi], "下界 > 0": lo > 0}
    np.save(f"backtest/resultsc5/bonf_samples_{s}.npy", smp)
    print("{}：B＝{:,}、L＝{}｜Bonferroni（N＝13）CI [{:+.2%}, {:+.2%}] ⇒ 下界 {} 0".format(s, B, L, lo, hi, ">" if lo > 0 else "≤"))
json.dump(out, open("backtest/resultsc5/bonferroni_prep.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
