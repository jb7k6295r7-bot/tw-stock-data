# -*- coding: utf-8 -*-
"""PREREGI 有界檢查（裁定線 seq112 §一②，描述、⛔ 不改判定）：
把 Δ_stk 裡「排不了名」的持股（不在峰日前最近量測日的 eligible 母體、或 ret_120 缺）全當成前 5% ⇒ 也剔掉、剩下等權補回到 e。
⇒ 算 Δ_stk 的中位（上界）；若某段因此全被剔 ⇒ 照 §3-4：該段四個 Δ 都不計、少於一段整顆不進中位數（Δ_vol 也跟著重算）。
判準（裁定線逐字）：上界仍比 Δ_vol 小 ≥ 2.0 pp ⇒「排不了名的持股不影響順位」；否則「順位對排不了名的處理敏感」。"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchI as I
import researchI_delta as ID
from backtest import p4_features as P4F

cal, ncal, closes, opens, sigs = I.setup()
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
el = panel[panel["eligible"].astype(bool)]
mdates = np.array(sorted(el["measure_date"].unique()), dtype="datetime64[ns]")
by_md = {pd.Timestamp(d): g for d, g in el.groupby("measure_date")}
T = pd.read_csv(os.path.join(I.OUT, "deltas_by_segment.csv"))
H = pd.read_csv(os.path.join(I.OUT, "holdings_at_peak.csv"), dtype={"sid": str}, float_precision="round_trip")
Hg = {k: dict(zip(g["sid"], g["權重"])) for k, g in H.groupby(["seed", "段"])}
ub, dead, nrm = [], 0, 0
for r in T.itertuples():
    p, v = int(r.峰_pos), int(r.谷_pos)
    w = Hg[(r.seed, r.段)]; e = sum(w.values())
    k = int(np.searchsorted(mdates, np.datetime64(cal[p]), side="right")) - 1
    rk = by_md[pd.Timestamp(mdates[k])].set_index("stock_id")["ret_120"].rank(pct=True)
    unrk = {s for s in w if s not in rk.index or not np.isfinite(rk.get(s, np.nan))}
    top = {s for s in w if s in rk.index and np.isfinite(rk[s]) and rk[s] > ID.TOP}
    keep = [s for s in w if s not in top and s not in unrk]
    nrm += len(unrk)
    if keep:
        Dk = ID.static_depth({s: e / len(keep) for s in keep}, p, v, closes)
        ub.append((abs(r.D0) - abs(Dk)) * 100)
    else:
        ub.append(np.nan); dead += 1
T["Δ_stk上界"] = ub
ok = T[T["Δ_stk上界"].notna()]
agg = ok.groupby("seed")[["Δ_β", "Δ_ind", "Δ_stk上界", "Δ_vol"]].sum()
med = agg.median()
print("排不了名一併剔除：{} 筆（應為 629）｜因此全被剔的段 {}｜進中位數 {} 顆".format(nrm, dead, len(agg)))
print("中位：", med.round(3).to_dict())
gap = med["Δ_vol"] - med["Δ_stk上界"]
print("Δ_vol − Δ_stk上界 ＝ {:.3f} pp ⇒ {}".format(gap, "≥ 2.0 ⇒ 排不了名的持股不影響順位" if gap >= 2.0 else "< 2.0 ⇒ 順位對排不了名的處理敏感"))
T.to_csv(os.path.join(I.OUT, "deltas_by_segment_bound.csv"), index=False)
