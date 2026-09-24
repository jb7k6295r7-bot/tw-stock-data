import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F, researchp1 as P1, researchp7 as P7, researchp12 as P12, tradability as T
cal = D.load_calendar(); ncal = len(cal)
uni = D.load_universe()
mk = uni.set_index("stock_id")["market"]
nm = dict(zip(uni["stock_id"].astype(str), uni["name"].astype(str)))
ls = dict(zip(uni["stock_id"].astype(str), pd.to_datetime(uni["last_seen"])))
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, mk)
sg = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="ALL")
trad = T.build(set(sg["sid"]), cal)
rows=[]
for sid,e,x in zip(sg["sid"], sg["entry_pos"].astype(int), sg["xpos_H120"].astype(int)):
    if x<ncal and not trad[sid]["trd"][x]:
        k=x
        while k>0 and not trad[sid]["trd"][k]: k-=1
        # 出場日之後這檔還有沒有再成交過？
        later = trad[sid]["trd"][x+1:].any() if x+1<ncal else False
        rows.append({"sid":sid,"name":nm.get(sid,"?"),"gap":x-k,
                     "last_trade":str(cal[k].date()),"exit":str(cal[x].date()),
                     "之後還有成交":bool(later),
                     "last_seen":str(ls.get(sid,pd.NaT))[:10]})
b=pd.DataFrame(rows)
print("=== ⭐ 這 {} 筆是【永久下市】還是【暫時停牌】？ ===".format(len(b)))
vc=b["之後還有成交"].value_counts()
print("  出場日之後【再也沒有成交】＝ {} 筆（＝下市）".format(int(vc.get(False,0))))
print("  出場日之後【還有成交】　　＝ {} 筆（＝暫時停牌）".format(int(vc.get(True,0))))
print()
print("=== 暫時停牌那幾筆（⭐ 這才是真的用舊價賣）===")
t=b[b["之後還有成交"]]
print(t[["sid","name","last_trade","exit","gap"]].to_string(index=False) if len(t) else "  （無）")
print()
print("=== 下市那些的 gap 分佈 ===")
f=b[~b["之後還有成交"]]
print("  中位 {:.0f} 天｜max {} 天｜相異檔 {}".format(f["gap"].median(), f["gap"].max(), f["sid"].nunique()))
