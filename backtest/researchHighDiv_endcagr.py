# -*- coding: utf-8 -*-
"""seq389：高股息描述補「期末總額換算年化」欄（⛔ 不改既有數字；只讀 resultsHighDiv/grid.csv 加欄另存）——回測線 2026-10-20。
口徑說明：
  稅後年化（既有欄）＝ 時間加權報酬（TWR）：每天把領出的現金當作仍屬報酬（淨值[t]＝淨值[t−1]×(市值[t]＋當日領現[t])÷市值[t−1]），
    等於「配息若照領現當天的價格繼續滾」的年化，故與再投入版幾乎相同；不反映領出的錢之後沒有再生息。
  期末總額換算年化（新欄）＝ ((期末市值＋累計領現，每 100 萬本金，單位元) ÷ 1,000,000)^(1／年數) − 1；領出的現金放著不生息、不再投入。
    兩者差 ＝ 領出現金沒有再投入的機會成本；領越多（高股息比例越高）差越大。
"""
import os, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsHighDiv")
g = pd.read_csv(os.path.join(D, "grid.csv"))
yrs = (pd.to_datetime(g["迄"]) - pd.to_datetime(g["起"])).dt.days / 365.25
g["期末總額換算年化（領現不生息）"] = (g["期末市值＋累計領現（每100萬）"] / 1_000_000) ** (1 / yrs) - 1
g["年數"] = yrs
g.to_csv(os.path.join(D, "grid_with_endcagr.csv"), index=False)
k = g[(g["窗"].astype(str).str.contains("全期")) & (g["稅版"].astype(str).str.contains("3.5")) & (g.get("本金", pd.Series(["50萬"] * len(g))).astype(str).str.contains("50")) & (g.get("配息", pd.Series(["領現"] * len(g))).astype(str).str.contains("領現"))]
print(k[["0050%", "稅後年化", "期末市值＋累計領現（每100萬）", "期末總額換算年化（領現不生息）"]].to_string(index=False))
