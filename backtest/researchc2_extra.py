# -*- coding: utf-8 -*-
"""C2 補兩項必報（主格 N200、E3、MMR 2%；⛔ 不改判定）：
① §五之二 損益兩平成本（C1 同法：二分搜尋來回成本，到「嚴格優」那一腳消失為止）—— 只對嚴格優的腳
② 資金費拖累（先驗③）：在場期間逐日「當日資金費 ／ 前一日保證金」的平均 × 365.25 ⇒ 年化、對保證金的百分比；另報在場期間平均費率 × E"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc2 as C2
from backtest import funding as F
C = C2.C
man = F.load_manifest(path=os.path.join(C2.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
out = {}
for sym in C2.COINS:
    d = C2.load_px(sym)
    c_all = d["close"].to_numpy(float); lo_all = d["low"].to_numpy(float); da = d["date"].to_numpy()
    sig = c_all > C.sma(c_all, 200)
    i0 = int(np.flatnonzero(da == C2.W_START[sym])[0]); i1 = int(np.flatnonzero(da == C2.W_END)[0])
    close, low, dates = c_all[i0:i1 + 1], lo_all[i0:i1 + 1], da[i0:i1 + 1]; held = sig[i0:i1]
    fbd, _ = C2.fund_days(sym, dates, man)
    r_bh = close[1:] / close[:-1] - 1
    # ② 資金費拖累：逐日 −Σrate × E（＝ 當日資金費 ／ 當日開頭的保證金，當保證金＝權益、名目＝E×權益時）
    daily = [float(fbd[k + 1].sum()) for k in range(len(held)) if held[k]]
    rec = {"在場天數": len(daily), "在場期間平均日費率合計": float(np.mean(daily)) if daily else None,
           "年化資金費對保證金（名目＝E×保證金近似）": float(-np.mean(daily) * 365.25 * C2.E_MAIN) if daily else None,
           "費率為正的在場天數比例": float(np.mean([x > 0 for x in daily])) if daily else None}
    # ① 損益兩平
    r0, liq, _ = C2.engine(held, close, low, fbd, C2.E_MAIN, 0.02)
    cg_b, md_b = C.cagr(r_bh), C.mdd(r_bh)
    ok, sc, sm = C.judge(C.cagr(r0), C.mdd(r0), cg_b, md_b)
    for leg, flag in (("CAGR", sc), ("MDD", sm)):
        if not flag or liq is not None:
            continue
        def strict_at(cs):
            rr, lq, _ = C2.engine(held, close, low, fbd, C2.E_MAIN, 0.02, cost_side=cs)
            if lq is not None:
                return False
            return C.cagr(rr) > cg_b if leg == "CAGR" else abs(C.mdd(rr)) < abs(md_b)
        lo_, hi_ = C2.COST_SIDE, 0.25
        if strict_at(hi_):
            rec[f"損益兩平來回成本_{leg}"] = "≥ 50%"
        else:
            for _ in range(50):
                mid = (lo_ + hi_) / 2
                lo_, hi_ = (mid, hi_) if strict_at(mid) else (lo_, mid)
            rec[f"損益兩平來回成本_{leg}"] = 2 * (lo_ + hi_) / 2
    out[sym] = rec
    print(sym, rec, flush=True)
json.dump(out, open("backtest/resultsc2/extra.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
