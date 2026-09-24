# -*- coding: utf-8 -*-
"""批2 結算用：C6（新段）與 C7（六幣）每一判定格的 bootstrap 差值樣本存檔（同 C2 的做法）。
⭐ 用與交件完全相同的方法與種子重跑 C1.paired_ci 的迴圈，並斷言百分位與已交的 CI 逐位相同 ⇒ 存下來的就是那一組樣本。"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C
from backtest import researchc6 as C6
from backtest import researchc7 as C7


def samples(a, b, L):
    rng = np.random.default_rng(C.SEED); dc, dm = [], []
    for _ in range(C.N_BOOT):
        i = C.stationary_idx(len(a), L, rng); x, y = a[i], b[i]
        dc.append(C.cagr(x) - C.cagr(y)); dm.append(abs(C.mdd(x)) - abs(C.mdd(y)))
    return np.array(dc), np.array(dm)


q = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
out = {}
# C6 新段
d, _ = C6.load(True)
_, (rr, rb, *_), _, _ = C6.analyse(d, "主格")
R6 = json.load(open("backtest/resultsc6/summary.json", encoding="utf-8"))["新段CI"]
for tag, L in (("L", R6["L"]), ("2L", 2 * R6["L"])):
    dc, dm = samples(rr, rb, L)
    if tag == "L":
        assert q(dc) == tuple(R6["年化差"]) and q(dm) == tuple(R6["回落深度差"]), "⛔ C6 重算的 CI 與交件不同"
    else:
        assert q(dm) == tuple(R6["回落深度差_2L"])
    out[f"C6_newseg_{tag}_dcagr"] = dc; out[f"C6_newseg_{tag}_dmdd"] = dm
np.savez_compressed("backtest/resultsc6/bootstrap_diff_samples.npz", **{k: v for k, v in out.items() if k.startswith("C6")})
# C7
R7 = {r["coin"]: r for r in json.load(open("backtest/resultsc7/summary.json", encoding="utf-8"))}
o7 = {}
for s in C7.COINS:
    _, (r_rule, r_base, ci1, ci2) = C7.coin(s)
    for tag, L in (("L", R7[s]["L"]), ("2L", 2 * R7[s]["L"])):
        dc, dm = samples(r_rule, r_base, L)
        if tag == "L":
            assert q(dc) == tuple(R7[s]["CI年化差"]) and q(dm) == tuple(R7[s]["CI回落深度差"]), f"⛔ C7 {s} 重算 CI 與交件不同"
        else:
            assert q(dm) == tuple(R7[s]["CI回落深度差_2L"])
        o7[f"C7_{s}_{tag}_dcagr"] = dc; o7[f"C7_{s}_{tag}_dmdd"] = dm
np.savez_compressed("backtest/resultsc7/bootstrap_diff_samples.npz", **o7)
print("✅ C6 新段 2 組 × 2、C7 六幣 × 2 組 × 2 已存；百分位與交件 CI 逐位相同")
