# -*- coding: utf-8 -*-
"""C4 同曝險對照欄（⇐ 裁定線 1926 §二；加密策略線 2202 追問）—— ⛔ 不進判定、不改出口，只是描述。

裁定線逐字：「閘門依構造只降曝險（五幣低 5～11 個百分點）⇒ 回落變淺可能只是曝險變少
           ⇒ ETH／XRP／DOGE 各補『C1 原始 × 閘門版逐日實際曝險比』的同曝險對照：年化／回落」

⚠ 實作讀法（⛔ 本線不自訂，⇒ 兩種讀法都寫出來、只算得出意義的那一種）：
   (讀法一) 【逐日】比 ＝ 閘門曝險_t ÷ C1 曝險_t
            ⇒ 閘門 ＝ C1 ∧ BTC regime ⇒ 閘門在場的日子 C1 必在場 ⇒ 比值只會是 1 或 0
            ⇒ C1 × 逐日比 ＝ 閘門本身 ⇒ ⛔ 退化（對照臂等於被測臂），不可用
   (讀法二) 【全期】比 ＝ 閘門平均曝險 ÷ C1 平均曝險（常數 k）
            ⇒ 對照臂 r_t ＝ k × r_c1_t（C1 的擇時全保留，只把部位按比例縮到同曝險）
            ⇒ ⭐ 這才是「同曝險、但沒有 BTC regime 擇時」的對照 ⇒ 本支算這一種
            ⇒ 形狀同 C3 的現金對照臂（基準① × 策略逐日曝險）：拿走擇時、留下曝險
⭐ 錨：先用 daily.csv.gz 的 r_gate／r_c1 重算年化與回落，必須對上 per_coin.csv 交件值（⛔ 對不上不往下報）。
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
D = pd.read_csv("resultsc4/daily.csv.gz", parse_dates=["date"], float_precision="round_trip")
P = pd.read_csv("resultsc4/per_coin.csv", float_precision="round_trip").set_index("coin")


def stats(r, year_days):
    eq = np.cumprod(1.0 + np.asarray(r, float))
    yrs = len(r) / year_days
    cagr = eq[-1] ** (1.0 / yrs) - 1.0
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    mdd = float((eq / peak - 1.0).min())
    return float(cagr), mdd


print("=== ① ⭐ 錨：用 daily 重算，必須對上交件的 per_coin.csv ===")
best = None
for yd in (365.0, 365.25):
    err = 0.0
    for c in ("ETH", "XRP", "DOGE"):
        d = D[D.coin == c]
        cg, mg = stats(d.r_gate, yd)
        cc, mc = stats(d.r_c1, yd)
        err = max(err, abs(cg - P.loc[c, "cagr_gate"]), abs(mg - P.loc[c, "mdd_gate"]),
                  abs(cc - P.loc[c, "cagr_c1"]), abs(mc - P.loc[c, "mdd_c1"]))
    print("  年化用 {} 日：與交件的最大差 {:.3e}".format(yd, err))
    if best is None or err < best[1]:
        best = (yd, err)
YD, ERR = best
assert ERR < 1e-9, "⛔ 重算對不上交件（最大差 {:.3e}）⇒ 不可往下報".format(ERR)
print("  ⇒ ✅ 採 {} 日；閘門與 C1 的年化／回落都對上交件（最大差 {:.1e}）".format(YD, ERR))

print()
print("=== ② 讀法一（逐日比）為什麼退化：閘門在場日 C1 是否必在場 ===")
for c in ("ETH", "XRP", "DOGE"):
    d = D[D.coin == c]
    gate_in = d.r_gate != 0
    c1_in = d.r_c1 != 0
    bad = int((gate_in & ~c1_in).sum())
    same = int((gate_in & (d.r_gate == d.r_c1)).sum())
    print("  {:4s} 閘門在場 {:4d} 日，其中 C1 不在場 {} 日；在場日報酬與 C1 逐位相同 {}／{}".format(
        c, int(gate_in.sum()), bad, same, int(gate_in.sum())))
print("  ⇒ 逐日比只有 1 或 0 ⇒ C1 × 逐日比 ＝ 閘門本身 ⇒ ⛔ 讀法一退化，不算")

print()
print("=== ③ ⭐⭐ 讀法二：同曝險對照 r ＝ k × r_c1（k ＝ 閘門平均曝險 ÷ C1 平均曝險）===")
rows = []
for c in ("ETH", "XRP", "DOGE"):
    d = D[D.coin == c]
    k = float(P.loc[c, "expo_gate"] / P.loc[c, "expo_c1"])
    cg, mg = stats(d.r_gate, YD)
    cc, mc = stats(d.r_c1, YD)
    cs, ms = stats(k * d.r_c1, YD)
    rows.append(dict(幣=c, k=round(k, 4),
                     閘門_年化=cg, 閘門_回落=mg, 同曝險對照_年化=cs, 同曝險對照_回落=ms,
                     C1原始_年化=cc, C1原始_回落=mc,
                     閘門回落比對照淺=bool(abs(mg) < abs(ms)),
                     回落差_pp=(abs(ms) - abs(mg)) * 100,
                     年化差_pp=(cg - cs) * 100))
T = pd.DataFrame(rows)
fmt = T.copy()
for col in ("閘門_年化", "閘門_回落", "同曝險對照_年化", "同曝險對照_回落", "C1原始_年化", "C1原始_回落"):
    fmt[col] = (fmt[col] * 100).map(lambda x: "{:+.2f}%".format(x))
fmt["回落差_pp"] = fmt["回落差_pp"].map(lambda x: "{:+.2f}".format(x))
fmt["年化差_pp"] = fmt["年化差_pp"].map(lambda x: "{:+.2f}".format(x))
print(fmt.to_string(index=False))
print()
print("  回落差_pp ＝ |對照回落| − |閘門回落|（正 ⇒ 閘門比同曝險對照淺）")
print("  年化差_pp ＝ 閘門年化 − 對照年化")

print()
print("=== ④ 照 C3 ①句型的判讀（⛔ 描述，未做 CI；措辭歸加密策略線／裁定線）===")
for _, r in T.iterrows():
    if r["閘門回落比對照淺"]:
        print("  {}：閘門回落比同曝險對照淺 {:.2f} pp ⇒ 回落的改善【不能】全用曝險較低解釋（描述，未做 CI）".format(
            r["幣"], r["回落差_pp"]))
    else:
        print("  {}：同曝險對照回落更淺（或一樣）⇒ 回落的改善用曝險較低就能解釋，看不到擇時的貢獻（描述，未做 CI）".format(r["幣"]))

# ⛔ 鑑別力自測：k＝1 時對照必須逐位等於 C1 原始；k 變小回落必須變淺（單調）
d = D[D.coin == "ETH"]
assert stats(1.0 * d.r_c1, YD) == stats(d.r_c1, YD), "⛔ k＝1 卻不等於 C1"
m_hi = abs(stats(0.9 * d.r_c1, YD)[1]); m_lo = abs(stats(0.5 * d.r_c1, YD)[1])
assert m_lo < m_hi, "⛔ 縮部位回落卻沒變淺 ⇒ 對照臂算法有問題"
print()
print("✅ 自測：k＝1 ⇒ 逐位等於 C1 原始；k 由 0.9 降到 0.5 ⇒ 回落單調變淺")
T.to_csv("results_step2/c4_same_exposure.csv", index=False, encoding="utf-8")
print("⇒ 落檔 results_step2/c4_same_exposure.csv")
