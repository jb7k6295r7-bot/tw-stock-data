import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17")); sys.path.insert(0, "backtest")
import researchH2 as H2
from backtest import p4_features as P4F, tradability as T, researchp12 as P12
D = H2.D; cal = D.load_calendar()
# ── G0：主窗內 inst_ok 單獨擋掉的股-月比例（⛔ 不看報酬）
p = P4F.read_panel("backtest/resultsAFC/panel.csv.gz")
w0, w1 = P12.win_bounds(cal, "全窗")
p = p[(p["measure_date"] >= cal[w0]) & (p["measure_date"] <= cal[w1])]
base = p["liq_ok"].astype(bool) & p["bars_ok"].astype(bool)
only_inst = base & ~p["inst_ok"].astype(bool)
print("G0 主窗股-月：liq∧bars {:,}｜其中 inst_ok 單獨擋掉 {:,} ⇒ {:.3%}（門檻 ≤ 1%）".format(int(base.sum()), int(only_inst.sum()), only_inst.sum() / base.sum()))
print("   逐年：", (only_inst.groupby(p["measure_date"].dt.year).sum() / base.groupby(p["measure_date"].dt.year).sum()).round(4).to_dict())
# 若另以門檻B 訊號層看：rev_hi24∧ma60_up∧¬ma_stack 的股-月裡，inst_ok 單獨擋掉幾個
sig = base & (p["rev_hi24"] == 100) & (p["ma60_up"] == 100) & (p["ma_stack"] == 0)
print("   門檻B 三條件成立且 liq∧bars 的股-月 {:,}｜inst_ok 單獨擋掉 {:,} ⇒ {:.3%}".format(int(sig.sum()), int((sig & ~p["inst_ok"].astype(bool)).sum()), (sig & ~p["inst_ok"].astype(bool)).sum() / max(1, sig.sum())))
# ── 名冊誤收轉上市：官方名冊上、但最後成交日在名冊下市日之後 ≥ 20 個交易日 ⇒ 疑誤收（轉上市）
off = T.load_official()
stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str); U = set(H2.UG.gate3(stocks)["stock_id"])
ids = sorted(set(off) & U); trad = T.build(set(ids), cal); st = T.delist_status(trad, cal, official=off)
pos = {d: i for i, d in enumerate(cal)}
rows = []
for s in ids:
    dd = pd.Timestamp(off[s]); lp = st[s]["last"]
    di = cal.searchsorted(dd)
    if lp is not None and lp - di >= 20:
        rows.append((s, str(dd.date()), str(cal[lp].date())))
print("官方名冊上但下市日後仍交易 ≥ 20 日（疑轉上市誤收）：", len(rows))
late = [r for r in rows if pd.Timestamp(r[2]) <= cal[w1]]
print("   其中最後成交日在主窗尾 2026-08-24 以前：", late)
