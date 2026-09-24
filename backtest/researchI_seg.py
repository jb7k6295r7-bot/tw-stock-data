# -*- coding: utf-8 -*-
"""PREREGI 第二步之一（無解讀空間的部分）：§3-1 分段、段起點持股重建、必報②④⑦。⛔ 不算任何 Δ。

分段（登錄 §3-1 逐字）：第 1 段 ＝ 最大回落的峰→谷；之後把各段 [峰, 谷] 挖掉 ⇒ 剩下的連續區間各自內部算最大回落，
   取最深者；峰與谷必須在同一塊；某顆不足三段 ⇒ 有幾段算幾段。
   ⭐ 第 1 段必須與第一步重現的 (peak_pos, trough_pos, 深度) 逐位相同（同一支 research13.dd_episodes 的定義）
持股重建：引擎 audit（買賣逐筆）⇒ 第 t 日收盤持有 ＝ 買在 ≤ t 且賣在 > t；市值 ＝ amt × close[t] ／ ep
   ⭐ 逐日 Σ 市值 對 引擎 hold_val 驗（相對誤差 ≤ 1e-12），⛔ 對不上就停
"""
from __future__ import annotations
import os, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchI as I
from backtest import research11 as R
from backtest import researchp12 as P12

OUT = I.OUT
NSEG = 3


def block_mdd(E, a, b):
    """[a, b] 內部的最大回落 ⇒ (峰, 谷, 深度)；深度 0 ⇒ None。峰 ＝ 谷之前最後一個「等於區內前高」的日子（同 dd_episodes）。"""
    seg = E[a:b + 1]
    if len(seg) < 2:
        return None
    run = np.maximum.accumulate(seg); dd = seg / run - 1
    k = int(np.argmin(dd))
    if dd[k] >= 0:
        return None
    j = k
    while j > 0 and dd[j] < 0:
        j -= 1
    return a + j, a + k, float(dd[k])


def segments(E, first, end):
    blocks = [(first, end - 1)]; segs = []
    for _ in range(NSEG):
        cands = [(blk, block_mdd(E, *blk)) for blk in blocks]
        cands = [(blk, r) for blk, r in cands if r is not None]
        if not cands:
            break
        blk, (p, v, d) = min(cands, key=lambda x: x[1][2])
        segs.append((p, v, d))
        blocks.remove(blk)
        if p - 1 >= blk[0]:
            blocks.append((blk[0], p - 1))
        if v + 1 <= blk[1]:
            blocks.append((v + 1, blk[1]))
    return segs


def holdings_at(audit, t, closes):
    """第 t 日收盤仍持有的部位 ⇒ {sid: 市值}（同一 sid 同時只會有一筆，引擎用 held 集合擋）。"""
    open_ = {}
    for a in audit:
        if a["t"] > t:
            break
        if a["side"] == "buy":
            open_[a["sid"]] = (a["amt"], a["px"])
        else:
            open_.pop(a["sid"], None)
    return {s: amt * float(closes[s][t]) / ep for s, (amt, ep) in open_.items()}


def _one(seed):
    au = []
    R.COST = P12.COST_STD
    out = R.simulate_mtm(P12._S["sigs"][("S1", "T1", "*")], P12.RULE, P12.N_C1, np.random.default_rng(seed), P12._S["closes"],
                         P12._S["opens"], P12._S["ncal"], return_equity=True, pick=None, cap_fn=None, d_max=None,
                         queue_days=0, cash_mode="zero", audit=au)
    E, hv, first, end = out["equity"], out["hold_val"], out["first"], out["end"]
    au = sorted(au, key=lambda a: (a["t"], 0 if a["side"] == "sell" else 1))   # 同日先賣後買（引擎順序）
    # 逐日驗重建（抽 segs 的每一個峰與谷＋每 20 日一點）
    segs = segments(E, first, end)
    check = sorted(set([p for p, _, _ in segs] + [v for _, v, _ in segs] + list(range(first, end, 20))))
    worst = 0.0
    for t in check:
        h = holdings_at(au, t, P12._S["closes"])
        s = sum(h.values())
        worst = max(worst, abs(s - hv[t]) / max(abs(hv[t]), 1e-12))
    rows, hold, drin = [], [], []
    names = P12._S["names"]
    for i, (p, v, d) in enumerate(segs, 1):
        h = holdings_at(au, p, P12._S["closes"])
        rows.append({"seed": seed, "段": i, "峰_pos": p, "谷_pos": v, "實際深度": d, "檢查": E[v] / E[p] - 1,
                     "峰日曝險": hv[p] / E[p], "峰日檔數": len(h)})
        for s_, val in h.items():
            hold.append({"seed": seed, "段": i, "sid": s_, "權重": val / E[p]})
        ws = []
        for t in range(p, v + 1):
            ht = holdings_at(au, t, P12._S["closes"])
            ws.append(sum(val for s_, val in ht.items() if ("-DR" in names.get(s_, "") or "-創" in names.get(s_, ""))) / E[t])
        drin.append({"seed": seed, "段": i, "日數": len(ws), "DR創_中位": float(np.median(ws)), "DR創_最大": float(np.max(ws))})
    return rows, hold, drin, worst


if __name__ == "__main__":
    t0 = time.time()
    cal, ncal, closes, opens, sigs = I.setup()
    from backtest import data as D
    names = D.load_universe().set_index("stock_id")["name"].to_dict()
    P12._init(sigs, {}, closes, opens, ncal, {}, {}, cal); P12._S["names"] = names

    def init2(*a):
        P12._init(*a); P12._S["names"] = names
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 200
    with Pool(4, initializer=init2, initargs=(sigs, {}, closes, opens, ncal, {}, {}, cal)) as pool:
        res = pool.map(_one, [P12.SEED0 + r for r in range(reps)])
    S = pd.DataFrame([r for x in res for r in x[0]]); H = pd.DataFrame([r for x in res for r in x[1]])
    DR = pd.DataFrame([r for x in res for r in x[2]]); worst = max(x[3] for x in res)
    print("[重建] 持股市值 vs 引擎 hold_val 最大相對誤差 {:.2e}".format(worst))
    assert worst <= 1e-12, "⛔ 持股重建對不上引擎 ⇒ 停"
    rp = pd.read_csv(os.path.join(OUT, "repro_p12_w1.csv"), float_precision="round_trip")
    s1 = S[S["段"] == 1].merge(rp[["seed", "peak_pos", "trough_pos", "深度"]], on="seed")
    bad = int(((s1["峰_pos"] != s1["peak_pos"]) | (s1["谷_pos"] != s1["trough_pos"]) | (s1["實際深度"] != s1["深度"])).sum())
    print("[第 1 段 vs 第一步重現] {} 顆不同（⛔ 應為 0）".format(bad))
    assert bad == 0, "⛔ 分段第 1 段與 P12 最深回落不一致 ⇒ 停"
    S["峰日"] = [str(cal[i].date()) for i in S["峰_pos"]]; S["谷日"] = [str(cal[i].date()) for i in S["谷_pos"]]
    S.to_csv(os.path.join(OUT, "segments.csv"), index=False); H.to_csv(os.path.join(OUT, "holdings_at_peak.csv"), index=False)
    DR.to_csv(os.path.join(OUT, "dr_innovation_weight.csv"), index=False)
    print("[段數] 每顆：", S.groupby("seed").size().value_counts().to_dict())
    print("[段深度] 中位／p10／p90 按段：")
    print(S.groupby("段")["實際深度"].describe(percentiles=[.1, .5, .9])[["count", "10%", "50%", "90%"]].to_string())
    print("[峰日曝險] 中位 {:.4f}｜最小 {:.4f}｜<0.999 的段 {} / {}".format(S["峰日曝險"].median(), S["峰日曝險"].min(), int((S["峰日曝險"] < 0.999).sum()), len(S)))
    print("[峰日檔數] ", S["峰日檔數"].value_counts().sort_index().to_dict())
    print("[必報④ DR＋創新板權重（日×權重）] 按段 中位的中位／最大的最大：")
    print(DR.groupby("段").agg(中位的中位=("DR創_中位", "median"), 最大的最大=("DR創_最大", "max")).to_string())
    print("[峰日] 前五名：", S["峰日"].value_counts().head().to_dict())
    print("[必報⑦] 產業欄：data/meta/industry.csv 的 industry_code／industry_name（只有一層 ⇒ 用那一層）")
    print("{:.0f}s".format(time.time() - t0))
