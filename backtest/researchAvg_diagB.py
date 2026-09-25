# -*- coding: utf-8 -*-
"""診斷：攤平乙 Ci（賣得現金買下一檔）曝險反而比 Ci0（閒置）低 ⇒ 拆部位數、部位大小、現金比例。⛔ 不改任何檔，只印。"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchP9run as P
from backtest import researchAvg as A

P.setup(lambda x: None)
G = P._G; w0, w1 = G["w0"], G["w1"]
for key in ("base", "Ci0", "Ci", "Ci8"):
    res = []
    for r in range(5):
        au = []
        o = P.sim(A._b_engine_kw(key), P.SEED0 + r, audit=au)
        eq, hv = o["equity"], o["hold_val"]
        cashf = 1 - hv[w0:w1 + 1] / eq[w0:w1 + 1]
        # 逐日部位數：以 audit 買進／排程賣出重建
        npos = np.zeros(len(eq)); sizes = []; normal = []; nx = []
        opened = {}
        for a in au:
            if a["side"] == "buy":
                (nx if a.get("kind") == "nx" else normal).append(a["target_w"])
        res.append((float(np.mean(cashf)), len(normal), len(nx), float(np.median(normal)) if normal else np.nan,
                    float(np.median(nx)) if nx else np.nan, float(np.nanmean(o.get("x_nx_waits", [np.nan])) if o.get("x_nx_waits") else np.nan),
                    o.get("x_nx_pending_amt_end", np.nan)))
    m = np.array(res, float)
    print(f"{key:5s} 現金比例均 {m[:,0].mean():.3f}｜一般買進 {m[:,1].mean():.0f} 筆、中位 target_w {np.nanmean(m[:,3]):.3f}｜待買買進 {m[:,2].mean():.0f} 筆、中位 target_w {np.nanmean(m[:,4]):.3f}｜期末待買金額 {np.nanmean(m[:,6]):.3f}")
