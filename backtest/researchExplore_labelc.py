# -*- coding: utf-8 -*-
"""裁定 seq186 §四：探索批運氣基準改用 (丙) 假訊號條件標記；逐字寫「讀法是看過甲、乙結果後補定的」。

⛔ 不改 clues.csv／ranking_171.csv／summary.json（留原樣＝讀法甲的紀錄）；另出 clues_label_c.csv。
⚠ 標記只影響探索段措辭；線索照登錄全送確認段，⛔ 不因標記淘汰或加入。
丙的比值 ＝ fakecond_171.csv 的 ratio_cell（年化中位 ÷ |回落中位|，與格同形）；最好一次 ＝ 171 次的最大值。
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
B = "backtest/resultsExplore"
RTP = dict(float_precision="round_trip")
CL = pd.read_csv(f"{B}/clues.csv", **RTP)
FC = pd.read_csv(f"{B}/fakecond/fakecond_171.csv", **RTP)
assert len(FC) == 171 and FC["fake_i"].tolist() == list(range(171))
fmax = float(FC["ratio_cell"].max()); imax = int(FC.loc[FC["ratio_cell"].idxmax(), "fake_i"])
v = np.sort(FC["ratio_cell"].to_numpy(float))
NOTE = "運氣基準讀法丙（假訊號條件 171 次）；⚠ 讀法是看過甲、乙結果後補定的（裁定 seq186 §四）"
out = CL[["clue", "cell", "rank", "A", "D", "ratio"]].copy()
out["丙_171次最好一次比值"] = fmax
out["丙_最好一次是第幾次"] = imax
out["丙_分位（171 個比值中 ≤ 本條的比例）"] = [float(np.searchsorted(v, r, side="right") / len(v)) for r in out["ratio"]]
out["丙_高於最好一次"] = out["ratio"] > fmax
out["丙_標記"] = np.where(out["丙_高於最好一次"], "高於隨機挑條件的最好一次", "與隨機挑條件的運氣分不開")
out["甲_標記（描述）"] = CL["luck_tag"].fillna("").replace("", "（未標）")
out["甲_分位（描述）"] = CL["luck_q"]
out["乙_標記（描述）"] = "高於 99 分位"
out["讀法註"] = NOTE
out["性質"] = "探索，非結論；照登錄全送確認段，⛔ 不因標記淘汰或加入"
out.to_csv(f"{B}/clues_label_c.csv", index=False, encoding="utf-8-sig")
print(f"丙最好一次 {fmax!r}（第 {imax} 次）")
print(out[["clue", "cell", "ratio", "丙_高於最好一次", "丙_標記", "甲_標記（描述）"]].to_string(index=False))
