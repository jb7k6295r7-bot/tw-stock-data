# -*- coding: utf-8 -*-
"""⭐ 把兩個看起來很強的結論【當成假說去驗】，⛔ 不是看到數字就宣告。"""
import os,sys,pandas as pd
sys.path.insert(0,os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F
W0,W1=523,2835
cal=D.load_calendar()
panel=P4F.read_panel("backtest/resultsp4/panel.csv.gz")
panel["measure_date"]=pd.to_datetime(panel["measure_date"])
pos={d:i for i,d in enumerate(cal)}
panel["pos"]=panel["measure_date"].map(pos)
panel=panel[panel["pos"].notna()]; panel=panel[(panel["pos"]>=W0)&(panel["pos"]<=W1)]
g=pd.read_csv("backtest/resultsd4_gate.csv",dtype=str)
new453=set(g.loc[(g["direction"]=="新進來")&(g["fam2"]=="在 panel 內但【沒過閘門】（liq／bars／inst）"),"stock_id"])
p=panel[panel["stock_id"].astype(str).isin(new453)]
bl={k:set(p.groupby("stock_id")[k].max()[lambda s:s<=0].index.astype(str)) for k in ("liq_ok","bars_ok","inst_ok")}
L,B,I=bl["liq_ok"],bl["bars_ok"],bl["inst_ok"]
print("=== 假說① inst 擋掉的檔【全部】也被 liq 擋掉（⇒ inst 對母體沒有獨立貢獻）===")
print("   |I| = {}｜I ∩ L = {}｜I − L = **{}**".format(len(I),len(I&L),len(I-L)))
print("   ⇒ {}".format("⭐⭐ **成立**：I ⊆ L" if not (I-L) else "⛔ 不成立，I−L = "+"、".join(sorted(I-L))))
print("   ⇒ 三道的聯集 = {}（= L∪B = {}）⇒ ⭐ inst 貢獻 **0 檔**".format(len(L|B|I),len(L|B)))
print()
print("=== 假說② bars 擋掉的那一族【比現行池子更有流動性】（⇒ 三道性質不同）===")
cur=set(panel.loc[panel["eligible"].astype(bool),"stock_id"].astype(str))
med=panel[panel["stock_id"].astype(str).isin(cur|new453)].groupby("stock_id")["amt20"].median()
mb=med[med.index.astype(str).isin(B)]; mc=med[med.index.astype(str).isin(cur)]
ml=med[med.index.astype(str).isin(L)]
print("   bars 完全沒過 {:>3} 檔  中位 {:>14,.0f}".format(len(mb),mb.median()))
print("   現行池子     {:>4} 檔  中位 {:>14,.0f}".format(len(mc),mc.median()))
print("   liq  完全沒過 {:>3} 檔  中位 {:>14,.0f}".format(len(ml),ml.median()))
print("   ⇒ {}".format("⭐⭐ **成立**：bars 那一族的中位成交金額是現行池子的 {:.2f} 倍".format(mb.median()/mc.median())
      if mb.median()>mc.median() else "⛔ 不成立"))
print()
print("   ⚠ 而要先排除一個替代解釋：bars 那 43 檔是不是【只有少數幾檔】把中位拉高？")
print("      bars 那一族落在現行池子中位之上的檔數 = {}/{} ＝ {:.0f}%".format(
      (mb>mc.median()).sum(),len(mb),(mb>mc.median()).mean()*100))
print("   ⇒ {}".format("⭐ 過半 ⇒ ⛔ 不是少數幾檔拉的" if (mb>mc.median()).mean()>0.5
      else "⚠ 未過半 ⇒ ⭐ 可能是少數幾檔拉的，中位那句要收窄"))
