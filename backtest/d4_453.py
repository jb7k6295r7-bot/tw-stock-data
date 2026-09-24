# -*- coding: utf-8 -*-
"""seq17 §6-4：S1′ 在【新增那 453 檔】上被漲停擋掉的買單數／停牌延後的賣單數。
⛔ 引擎的 tr_* 計數是全池合計 ⇒ 這裡用 log 逐筆過濾出 453 檔那一部分。"""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F, research11 as R
from backtest import researchp1 as P1, researchp7 as P7, researchp12 as P12, tradability as T

cal = D.load_calendar(); ncal = len(cal)
uni = D.load_universe().set_index("stock_id")["market"]
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
panel["measure_date"] = pd.to_datetime(panel["measure_date"])
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
ed = pd.read_csv("backtest/results_d4/elig_d4.csv.gz", dtype={"stock_id": str})
ed["measure_date"] = pd.to_datetime(ed["measure_date"])
key = ed.set_index(["stock_id", "measure_date"])["elig_d4"]
p2 = panel.copy()
p2["eligible"] = list(zip(p2["stock_id"].astype(str), p2["measure_date"]))
p2["eligible"] = p2["eligible"].map(key).fillna(False).astype(bool)
sig = P7.build_sig_gate_b(p2, cal, closes, opens, start=P12.START, signal="B")
g = pd.read_csv("backtest/resultsd4_gate.csv", dtype=str)
n453 = set(g.loc[(g["direction"] == "新進來") & (g["fam2"].str.contains("沒過閘門", na=False)), "stock_id"])
print("S1′ sig {:,} 筆｜其中屬於新增 453 檔 ＝ {:,} 筆（{:.1f}%）".format(
    len(sig), sig["sid"].isin(n453).sum(), sig["sid"].isin(n453).mean() * 100))
trad = T.build(set(sig["sid"]), cal)
rows = []
t0 = time.time()
for r in range(40):                      # ⭐ 40 顆種子（log 很吃記憶體；⛔ 不需要 200 顆就看得出量級）
    lg = []
    R.simulate_mtm(sig, "H120", 8, np.random.default_rng(104000 + r), closes, opens, ncal,
                   tradable=trad, log=lg)
    d = pd.DataFrame(lg)
    d["is453"] = d["sid"].isin(n453)
    rows.append({
        "seed": 104000 + r,
        "limit_up_all": int((d["reason"] == "limit_up").sum()),
        "limit_up_453": int(((d["reason"] == "limit_up") & d["is453"]).sum()),
        "halt_in_all": int((d["reason"] == "halt_in").sum()),
        "halt_in_453": int(((d["reason"] == "halt_in") & d["is453"]).sum()),
        "in_all": int((d["reason"] == "in").sum()),
        "in_453": int(((d["reason"] == "in") & d["is453"]).sum()),
    })
df = pd.DataFrame(rows)
df.to_csv("backtest/results_d4/blocked_453.csv", index=False)
print("({:.0f}s，40 顆種子)".format(time.time() - t0))
print()
print("=== ⭐ seq17 §6-4 兩個數（中位／全距）===")
for k, lab in (("limit_up", "漲停擋掉的買單"), ("halt_in", "停牌擋掉的買單")):
    a, b = df[k + "_all"], df[k + "_453"]
    print("  {:<12} 全池 中位 {:.0f}（{}~{}）｜**453 檔上 中位 {:.0f}（{}~{}）**".format(
        lab, a.median(), a.min(), a.max(), b.median(), b.min(), b.max()))
print("  {:<12} 全池 中位 {:.0f}｜453 檔上 中位 {:.0f}（占 {:.1f}%）".format(
    "實際進場", df["in_all"].median(), df["in_453"].median(),
    df["in_453"].median() / df["in_all"].median() * 100))
print()
print("⚠ 停牌【延後的賣單】＝ 引擎的 tr_exit_delayed（出場側，⛔ log 只記進場側）")
print("  ⇒ 見 cells.csv：S1′ 附欄中位 1 筆／全池；⛔ 無法逐筆分到 453 檔（引擎未記出場 log）")
