"""T1 附：量 K線分析線 20260920 補件 §二 的【機制前提】本身。

補件押的機制逐字：「大型股的日波動普遍低於小型股 ⇒ 同一組門檻，在大型股上較容易成立」。
⭐ 那句話有兩段，要分開驗：
   (甲) 大型股日波動是否真的較低      ← 本檔量這個
   (乙) 波動較低是否讓門檻較容易成立   ← 要靠合成序列召回率（下一步）
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-stock-data"))
from backtest import data as D                  # noqa: E402
from backtest import patterns as P              # noqa: E402
from backtest.run import SIG_START, SIG_END     # noqa: E402

T1 = "/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/57a7a54c-a515-48e2-87ab-d32197791f42/scratchpad/t1"
cap = pd.read_csv(f"{T1}/mktcap.csv", dtype={"stock_id": str})
exp = pd.read_csv(f"{T1}/exposure.csv", dtype={"stock_id": str})

cal = D.load_calendar()
lo = int(cal.searchsorted(pd.Timestamp(SIG_START)))
hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)
ym_all = pd.Series(cal).dt.strftime("%Y-%m").to_numpy()

top = cap[cap["top50"]].set_index(["stock_id", "ym"]).index
top = set(top)

uni = D.load_universe()
mk = dict(zip(uni["stock_id"], uni["market"]))

rows = []
sids = sorted(exp["stock_id"].unique())
print(f"掃 {len(sids):,} 檔（曝險表裡的）", file=sys.stderr)
for i, sid in enumerate(sids):
    st = D.load_stock(sid, mk.get(sid, "twse"), cal)
    if st is None:
        continue
    c = st.df["close"].to_numpy(float)
    r = np.abs(np.diff(c, prepend=np.nan) / np.roll(c, 1))          # 日絕對報酬
    rng = (st.df["high"].to_numpy(float) - st.df["low"].to_numpy(float)) / c   # 日高低振幅
    for j in range(lo, hi + 1):
        if not np.isfinite(r[j]) or not np.isfinite(rng[j]):
            continue
        rows.append((sid, (sid, ym_all[j]) in top, r[j], rng[j]))
    if (i + 1) % 400 == 0:
        print(f"  {i + 1}/{len(sids)}", file=sys.stderr)

d = pd.DataFrame(rows, columns=["stock_id", "top50", "abs_ret", "hl_range"])
d["tier"] = d["top50"].map({True: "市值前50", False: "其餘"})

print()
print("═══ ⭐ 日波動：市值前 50 vs 其餘 ═══")
g = d.groupby("tier")[["abs_ret", "hl_range"]].agg(["median", "mean", "count"])
print("  " + g.to_string().replace("\n", "\n  "))
print()
a = d[d["tier"] == "市值前50"]
b = d[d["tier"] == "其餘"]
print("  日絕對報酬中位：前50 {:.4%}  其餘 {:.4%}  ⇒ 比值 {:.2f}x".format(
    a["abs_ret"].median(), b["abs_ret"].median(), a["abs_ret"].median() / b["abs_ret"].median()))
print("  日高低振幅中位：前50 {:.4%}  其餘 {:.4%}  ⇒ 比值 {:.2f}x".format(
    a["hl_range"].median(), b["hl_range"].median(), a["hl_range"].median() / b["hl_range"].median()))
print()
verdict = "✅ 成立" if a["abs_ret"].median() < b["abs_ret"].median() else "⛔ 不成立"
print("  ⇒ 機制前提 (甲)「大型股日波動較低」：{}".format(verdict))
d.groupby("tier")[["abs_ret", "hl_range"]].median().to_csv(f"{T1}/vol_by_tier.csv")
print("  （已寫出 vol_by_tier.csv，供合成序列用同一組波動校準）")
