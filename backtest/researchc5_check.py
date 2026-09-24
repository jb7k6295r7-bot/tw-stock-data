# -*- coding: utf-8 -*-
"""C5 出口② 交件前的獨立粗估（⛔ 不經 researchc5.engine）：
對總權益的年化 ≈ 0.5 × Σ(當日費率合計) × 365.25／天數 − 成本拖累；成本拖累 ≈ 每日 0.5×|r_t|×(0.1%＋0.05%)＋建倉平倉
⇒ 與引擎年化比；差距應在 1 pp 以內（粗估忽略複利與名目隨權益變動）"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc2 as C2, funding as F
man = F.load_manifest(path=os.path.join(C2.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
R = {r["coin"]: r for r in json.load(open("backtest/resultsc5/summary.json", encoding="utf-8"))}
for s in ("BTC", "ETH", "BNB", "SOL"):
    d = C2.load_px(s); da = d["date"].to_numpy()
    i0 = int(np.flatnonzero(da == R[s]["窗首（建倉日）"])[0]); i1 = int(np.flatnonzero(da == R[s]["窗尾"])[0])
    c = d["close"].to_numpy(float)[i0:i1 + 1]; dates = da[i0:i1 + 1]
    fbd, _ = C2.fund_days(s, dates, man)
    n = len(c) - 1
    fund_rate = sum(float(fbd[k + 1].sum()) for k in range(n))
    gross = 0.5 * fund_rate * 365.25 / n
    absr = np.abs(c[1:] / c[:-1] - 1)
    drag = 0.5 * absr.mean() * (0.001 + 0.0005) * 365.25 + 2 * 0.5 * (0.001 + 0.0005) * 365.25 / n
    print("{}：資金費毛（對總權益）{:+.2%}／年｜成本拖累 {:.2%}／年｜粗估淨 {:+.2%}｜引擎 {:+.2%}｜差 {:+.2f} pp".format(
        s, gross, drag, gross - drag, R[s]["主格"]["年化"], (R[s]["主格"]["年化"] - (gross - drag)) * 100))
