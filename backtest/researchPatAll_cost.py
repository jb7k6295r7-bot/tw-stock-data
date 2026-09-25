# -*- coding: utf-8 -*-
"""PREREG型態全量 可執行層（裁定 seq185 ②；⛔ 只決定措辭、⛔ 不改判定、⛔ 不計 N）。

可單獨引用的 12 格（bonf不含0）⇒ |d×X̄| 與來回成本 0.585%（evaluate.COST）並列：
  |d×X̄| ＜ 成本 ⇒「測得出，但扣成本後不夠付交易成本」
⚠ d×X̄ 是【型態組 − 事前走勢配對的對照組】的差（兩邊成本相減抵銷，本體未扣）⇒ 大於成本 ≠ 照型態交易會賺錢，
  只表示「這段差距比一次來回的摩擦大」；看跌方向（d＝−1）與反方向格要賺到差距須放空，借券費不在 0.585% 內。
假訊號 x／30：fake_reps.csv 新預設臂（只排除過去 20 日）裡該格結果＝結果② 的次數（〈二十六〉：≥15 ⇒ 過關不構成證據）。
描述欄：95% CI 靠近 0 的一端的絕對值是否也大於成本（⛔ 不進措辭判定）。
"""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import evaluate as E

B = "backtest/resultsPatAll/body"
COST = E.COST
assert COST == 0.00585
SIX = {("K14", 60), ("K44", 20), ("S06", 20), ("S09", 20), ("S26", 20), ("S27", 20)}   # seq185：無假訊號警語的 6 格

c = pd.read_csv(f"{B}/cells.csv")
k = c[c["bonf不含0"] == True].copy()
assert len(k) == 12, len(k)
f = pd.read_csv(f"{B}/fake_reps.csv")
f = f[f["版本"] == "新預設"]
assert f.groupby(["vid", "H"]).size().eq(30).all()
x = f.assign(p=f["結果"].eq("結果②")).groupby(["vid", "H"])["p"].sum()
rows = []
for _, r in k.iterrows():
    e = abs(float(r["dX̄"])); near = min(abs(float(r["lo"])), abs(float(r["hi"])))
    fx = int(x.loc[(r["vid"], int(r["H"]))])
    rows.append({"vid": r["vid"], "型態": r["型態"], "H": int(r["H"]), "結果": r["結果"], "n_eff": int(r["n_eff"]),
                 "d×X̄": float(r["dX̄"]), "|d×X̄|": e, "來回成本": COST, "|d×X̄|−成本": e - COST,
                 "夠付成本": e > COST, "CI近0端絕對值": near, "CI近0端也大於成本（描述）": near > COST,
                 "假訊號x／30": fx, "無假訊號警語6格": (r["vid"], int(r["H"])) in SIX,
                 "措辭": ("扣成本後差距大於一次來回成本" if e > COST else "測得出，但扣成本後不夠付交易成本")
                         + ("｜要賺到須放空（借券費不在 0.585% 內）" if (r["結果"] == "結果③" or r["d"] in ("-1", -1)) else "")})
o = pd.DataFrame(rows)
assert o["無假訊號警語6格"].sum() == 6
assert (o.loc[o["無假訊號警語6格"], "假訊號x／30"] < 2).all(), "⛔ 6 格應無假訊號警語"
o.to_csv(f"{B}/cost_vs_edge.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250)
v = o.copy()
for col in ("d×X̄", "|d×X̄|", "|d×X̄|−成本", "CI近0端絕對值"):
    v[col] = (v[col] * 100).map("{:+.2f}%".format)
print(v.drop(columns=["來回成本"]).to_string(index=False))
