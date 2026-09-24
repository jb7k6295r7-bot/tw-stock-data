# -*- coding: utf-8 -*-
"""C4 必報欄（裁定線 seq92 §三、seq94 §三）：判定格過了 ⇒ 附【同窗假訊號臂的判定格通過率（聯合、兩腳）】。

⭐ C4 的判定格是「閘門 vs 該幣自己的 C1 原始」⇒ 假訊號臂也對【C1 原始】比（⛔ 不是買進持有）。
⭐ resultsc4 沒存逐組假訊號結果 ⇒ 照原呼叫、原種子重跑：C1.placebo_dist(g["held"], rb, rng(C1.SEED))
   ⛔ 不是新分析：同一個函式、同一個種子 ⇒ 必須先重現交件已印的兩個百分位（錨），對上才往下算。
⛔ 不改 runc4.py、不改 researchc1.py；只 import。
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchc1 as C1
from backtest import runc4 as R4

P = pd.read_csv("resultsc4/per_coin.csv", float_precision="round_trip").set_index("coin")
raw = {s: R4.load(s) for s in C1.COINS}
reg = R4.regime_map(raw["BTC"])

rows = []
for s in ("ETH", "XRP", "DOGE"):
    d = raw[s]; c = d["close"].to_numpy(float); dates = d["date"].to_numpy()
    base = C1.rule_series(c, C1.N_MAIN)
    g = R4.gated_series(c, dates, reg)
    rg, rr, rb = g["r_gate"], base["r_rule"], base["r_bh"]
    cg_g, md_g = C1.cagr(rg), C1.mdd(rg)
    cg_r, md_r = C1.cagr(rr), C1.mdd(rr)
    ok_g, _, _ = C1.judge(cg_g, md_g, cg_r, md_r)
    assert ok_g == bool(P.loc[s, "pass_vs_c1"]), "⛔ {} 判定格重算與交件不同".format(s)
    pcg, pmd = C1.placebo_dist(g["held"], rb, np.random.default_rng(C1.SEED))
    pcg, pmd = np.asarray(pcg, float), np.asarray(pmd, float)
    #  ⭐ 錨：交件印的兩個百分位必須逐位重現
    a1 = float((pcg < cg_g).mean() * 100); a2 = float((pmd > abs(md_g)).mean() * 100)
    a3 = float((pcg < cg_r).mean() * 100)
    assert a1 == P.loc[s, "plc_cagr_pctl_gate"] and a2 == P.loc[s, "plc_mdd_pctl_gate"] \
        and a3 == P.loc[s, "plc_cagr_pctl_c1"], "⛔ {} 假訊號分布沒重現交件（{} {} {}）".format(s, a1, a2, a3)
    #  ⭐ 聯合：每一組假訊號臂用【同一個 judge】對 C1 原始判
    res = [C1.judge(float(x), -float(y), cg_r, md_r) for x, y in zip(pcg, pmd)]
    ok = np.array([r[0] for r in res]); sc = np.array([r[1] for r in res]); sm = np.array([r[2] for r in res])
    leg_c = pcg >= cg_r; leg_m = pmd <= abs(md_r)
    rows.append(dict(幣=s, 組數=len(pcg), 閘門判定格=ok_g,
                     年化腳成立=int(leg_c.sum()), 回落腳成立=int(leg_m.sum()),
                     判定格過_judge=int(ok.sum()), 通過率=round(ok.mean() * 100, 1),
                     兩腳都嚴格=int((sc & sm).sum()), 兩腳嚴格率=round((sc & sm).mean() * 100, 1),
                     邊際相乘=round(leg_c.mean() * leg_m.mean() * 100, 1)))
    print("[{}] 錨 ✅（{:.1f}／{:.1f}／{:.1f} 與交件逐位相同）⇒ 假訊號臂判定格過 {}／{} ＝ {:.1f}%".format(
        s, a1, a2, a3, int(ok.sum()), len(pcg), ok.mean() * 100))

T = pd.DataFrame(rows)
print()
print(T.to_string(index=False))
print()
print("⚠ 邊際相乘欄只是提醒：它 ≠ 聯合（兩腳不獨立），⛔ 不可拿來代替通過率")

# ⛔ 鑑別力自測：拿 C1 原始自己當假訊號臂 ⇒ 兩腳都只是相等 ⇒ judge 必須判不過（無嚴格優）
ok_self, _, _ = C1.judge(cg_r, md_r, cg_r, md_r)
assert ok_self is False or ok_self == False, "⛔ 自己比自己竟然過 ⇒ judge 的『嚴格優』沒在算"
print("✅ 自測：C1 原始對自己 ⇒ judge 判不過（⇒ 『至少一腳嚴格優』真的在算）")
T.to_csv("results_step2/c4_null_passrate.csv", index=False, encoding="utf-8")
print("⇒ 落檔 results_step2/c4_null_passrate.csv")
