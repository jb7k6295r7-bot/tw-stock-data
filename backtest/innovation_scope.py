import os, sys, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, universe_gate as UG
ub = D.load_universe()
ib = ub[ub["name"].str.contains("-創", na=False, regex=False)]
um = UG.universe_from_stocks(UG.main_stocks())
im = um[um["name"].str.contains("-創", na=False, regex=False)]
print("分支快照母體 {:,}｜名稱含 -創 {} 檔".format(len(ub), len(ib)))
print("main 母體   {:,}｜名稱含 -創 {} 檔".format(len(um), len(im)))
print("只在 main 的 -創：", sorted(set(im.stock_id) - set(ib.stock_id)))
print("只在分支的 -創：", sorted(set(ib.stock_id) - set(im.stock_id)))
pan = pd.read_csv("backtest/resultsp4/panel.csv.gz", dtype={"stock_id": str}, usecols=["stock_id", "eligible"])
p = pan[pan.stock_id.isin(set(ib.stock_id))]
e = p[p.eligible.astype(bool)]
print("P4 面板裡這些 -創：{} 檔有列、{:,} 股-月；eligible True {:,} 股-月／{} 檔".format(
    p.stock_id.nunique(), len(p), len(e), e.stock_id.nunique()))
tot = int(pan.eligible.astype(bool).sum())
print("  ⇒ 占 eligible 全體 {:,} 的 {:.3f}%".format(tot, len(e) / tot * 100))
print("  eligible 的 -創 逐檔：", dict(e.stock_id.value_counts()))
