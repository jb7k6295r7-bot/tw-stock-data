# -*- coding: utf-8 -*-
"""sanity：舊快照（scan55，頻率表那次）對新快照（scan64，origin/main 9e1316ff3c）。只比因子值與母體、事件筆數，⛔ 不碰報酬。"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.join(os.path.dirname(HERE), "scan55", "factors"); NW = os.path.join(HERE, "factors")
Uo = pd.read_parquet(os.path.join(O, "universe.parquet")); Un = pd.read_parquet(os.path.join(NW, "universe.parquet"))
cols = Uo.columns.intersection(Un.columns); idx = Uo.index.intersection(Un.index)
print("universe cols old/new/common", len(Uo.columns), len(Un.columns), len(cols), "months old/new/common", len(Uo.index), len(Un.index), len(idx))
du = (Uo.loc[idx, cols] != Un.loc[idx, cols]).sum(1)
print("universe 母體檔數 old vs new（相異格）：", int(du.sum()), "；相異月份", du[du > 0].to_dict())
for code in sys.argv[1:] or ["S01", "S33", "S39", "S67", "S26"]:
    a = pd.read_parquet(os.path.join(O, f"{code}.parquet")).reindex(index=idx, columns=cols).where(Uo.loc[idx, cols])
    b = pd.read_parquet(os.path.join(NW, f"{code}.parquet")).reindex(index=idx, columns=cols).where(Un.loc[idx, cols])
    na, nb = a.notna().sum(1), b.notna().sum(1)
    both = a.notna() & b.notna()
    diff = (np.abs(a - b) > 1e-6 * np.maximum(1, np.abs(a))) & both
    dm = (na != nb)
    print(f"{code}: 有值檔數相異月 {int(dm.sum())}（{list(na.index[dm])[:6]}…）；值相異格 {int(diff.values.sum())}／{int(both.values.sum())}；相異月 {list(diff.index[diff.any(axis=1)])[:8]}")
for code in ["S63", "S37", "S20"]:
    eo = pd.read_csv(os.path.join(O, f"{code}_events.csv"), dtype=str); en = pd.read_csv(os.path.join(NW, f"{code}_events.csv"), dtype=str)
    ko = set(map(tuple, eo[["stock_id", "entry_date"]].values)); kn = set(map(tuple, en[["stock_id", "entry_date"]].values))
    only_o = sorted(ko - kn); only_n = sorted(kn - ko)
    print(f"{code}: old {len(ko)} new {len(kn)}；只在舊 {len(only_o)} {only_o[:5]}；只在新 {len(only_n)}（最早進場日 {min([x[1] for x in only_n]) if only_n else '-'}）")
