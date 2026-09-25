# -*- coding: utf-8 -*-
"""PREREGH L＝36 狀態重判：補上 0050 2012-01～2014-12（資料庫 1450，main 45c6fcbac1 data/extra/）後，判原本「缺」的 11 個月。

裁定線 seq154 §二 准用，兩條限制（逐字照做）：
  ① 程式只輸出閘門狀態（逐月開／關），⛔ 不印、不存 0050 2012～2014 的報酬數字 ⇒ 本支只印／只存 UP／DOWN 字樣與計數
  ② 驗收段（PREREGV）的 0050 基準另從早年日 K 算，⛔ 不沿用本支的中間量 ⇒ 本支不落任何價格或報酬中間檔
讀法（與 researchH_states.py 同一套）：0050 還原收盤；月 m 的狀態用「前一個完整月末」往回 36 個月末的報酬 < 0 ⇒ DOWN
  還原 ＝ data.cum_factor_series（事件日嚴格大於 d 的因子連乘）；早年三筆配息與 data/adj/0050.csv 串成同一條鏈
回歸：2015 以後的還原收盤不受早年事件影響 ⇒ 原本已知的 103 個月狀態必須與 researchH_states.py 逐月相同
"""
import os, sys, io, subprocess
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D = H2.D
EXTRA = "45c6fcbac1445bcb370d79d5892c9e7b1090fae0"


def gshow(path):
    r = subprocess.run(["git", "show", f"{EXTRA}:{path}"], cwd=os.path.expanduser("~/tw-stock-data"), capture_output=True, text=True, check=True)
    return pd.read_csv(io.StringIO(r.stdout), dtype={"stock_id": str})


cal = D.load_calendar()
st = D.load_stock("0050", "twse", cal)
c_new = st.df["close"].dropna()                                     # 2015 起還原收盤（原程式同一條）
ex = gshow("data/extra/0050_2012_2014.csv")
ea = gshow("data/extra/0050_adj_2012_2014.csv")
adj = pd.concat([ea, D.load_adj("0050")], ignore_index=True)
adj["date"] = pd.to_datetime(adj["date"]); adj = adj.sort_values("date").reset_index(drop=True)
assert adj["date"].is_monotonic_increasing and adj["date"].is_unique
# 鏈接檢查（只比因子，⛔ 不涉報酬）：早年最後一筆 cum ＝ 2015 第一筆 cum × 該筆 factor
i = int(np.flatnonzero(adj["date"] == pd.Timestamp("2014-10-24"))[0])
assert abs(adj.loc[i, "cum_factor"] - adj.loc[i + 1, "cum_factor"] * adj.loc[i, "factor"]) < 1e-7, "⛔ 早年還原鏈沒接上"
ex["date"] = pd.to_datetime(ex["date"])
ex = ex[ex["close"].notna()].set_index("date").sort_index()
assert ex.index.max() < c_new.index.min()
F = D.cum_factor_series(ex.index, adj)
c_old = ex["close"].astype(float) * F
c = pd.concat([c_old, c_new])
me = c.groupby(c.index.to_period("M")).last()
months = pd.period_range("2017-03", "2026-08", freq="M")
L = 36
s = pd.Series(["缺" if (m - 1 - L not in me.index or m - 1 not in me.index) else ("DOWN" if me[m - 1] / me[m - 1 - L] - 1 < 0 else "UP") for m in months], index=months)
# 回歸：原本已知月份逐月相同（用原程式同一條 2015 起序列重算，⛔ 不讀舊輸出檔的數字）
me0 = c_new.groupby(c_new.index.to_period("M")).last()
old = pd.Series(["缺" if (m - 1 - L not in me0.index or m - 1 not in me0.index) else ("DOWN" if me0[m - 1] / me0[m - 1 - L] - 1 < 0 else "UP") for m in months], index=months)
known = old != "缺"
assert (s[known] == old[known]).all(), "⛔ 原本已知月份的狀態變了"
newly = s[~known]
out = pd.DataFrame({"month": months.astype(str), "state_L36": s.values, "原本缺": (~known).values})
os.makedirs(os.path.expanduser("~/tw-p17/backtest/resultsH"), exist_ok=True)
out.to_csv(os.path.expanduser("~/tw-p17/backtest/resultsH/states_L36_with2012.csv"), index=False)
print("L＝36（含 0050 2012～2014）：UP {}｜DOWN {}｜缺 {}｜原本缺 {} 個月 ⇒ 現在 {}".format(
    int((s == "UP").sum()), int((s == "DOWN").sum()), int((s == "缺").sum()), int((~known).sum()), newly.value_counts().to_dict()))
print("原本缺的月：", {str(k): v for k, v in newly.items()})
print("回歸：原本已知 {} 個月逐月相同 ✅".format(int(known.sum())))
