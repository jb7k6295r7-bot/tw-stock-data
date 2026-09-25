# -*- coding: utf-8 -*-
"""PREREG出場訊號 描述：剔除「近似相等」事件（|close−線| ≤ 1e-9·線，T 或 T−1 任一）後的 6 格 E 與 CI（⛔ 不判；只看 E2 的等號讀法會不會動到結論）。
⚠ 本體 summary.json 的「敏感度_剔除近似相等事件後」一欄有程式錯（object 欄位用 ~ 取反 ⇒ 沒剔到任何一筆），以本支為準。"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import exit_signal as XS

OUT = os.path.expanduser("~/tw-p17/backtest/resultsExit")
K = pd.read_csv(os.path.join(OUT, "events_kept.csv.gz"), dtype={"sid": str})
K = K[K["rule"] == "close"]
tie = K["near_tie"].astype(str).str.lower().eq("true")
res = {}
for g in XS.SIGS:
    for H in (20, 60):
        m = (K["g"] == g) & (K["H"] == H)
        for nm, sel in (("全部", m), ("剔除近似相等", m & ~tie)):
            k = K[sel]
            grp = k["month"].to_numpy() if H == 20 else k["blk60"].to_numpy()
            E, se, ng = XS.cr0(k["R"].to_numpy(float), grp)
            res["{}_H{}_{}".format(g, H, nm)] = {"n": int(len(k)), "E": E, "lo": E - 1.96 * se, "hi": E + 1.96 * se, "群數": ng}
            print("{}_H{} {}：n {:,}｜E {:+.3f}%｜CI {:+.3f} ～ {:+.3f}%".format(g, H, nm, len(k), E * 100, (E - 1.96 * se) * 100, (E + 1.96 * se) * 100))
json.dump(res, open(os.path.join(OUT, "tie_sensitivity.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
