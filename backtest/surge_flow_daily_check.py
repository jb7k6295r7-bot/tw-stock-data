# -*- coding: utf-8 -*-
"""surge_flow_daily 的閘門 G3：W1、W2（再次處置、出關）、中段底分數，抽 topwarn／bottomjudge 已算過的筆重算（每日資料形態 vs 研究版），逐筆相同。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.surge_flow_daily_check
參照（研究版）：researchSurge6_topwarn.components（s5work 接合版面）的 W1 基本版、W2a、W2b；中段底分數 ＝ topwarn 完整一輪同式
   （bottomjudge.stock_ctx＋pull_feats＋topwarn.bj_has，Q 用 s5work）；對象 ＝ topwarn 的「起漲特徵 ≥7 個」逐筆（check_Bp_m7.csv.gz）W1 賣出後第一個回落 20% 跨越日
本程式：surge_feat_daily（每日 archive＋另 archive＋早年營收；main b53f5540a8）＋ surge_flow_daily.signals_for／bj_has／stock_ctx
"""
import json
import os

import numpy as np
import pandas as pd

from backtest import researchSurge5 as S5
from backtest import researchSurge6_end_desc as ED
from backtest import researchSurge6_topwarn as TW
from backtest import researchSurge6_bottomjudge as BJ
from backtest import researchSurge6_mid_desc as MD
from backtest import surge_feat_daily as SFD
from backtest import surge_flow_daily as SFL

OUT = "backtest/resultsDaily/surge_feat_G1"


def main():
    uni5, cal5, n5, inseg, bar5, h6, E, cells, cnt = ED.load()
    t1 = int(cal5.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    W5, _ = S5.world(print)
    C, O, SIG, base1, START, EXIT, NEAR, STARTS, HI20, OUTC = TW.components(uni5, cal5, n5, bar5, t1, W5, print)
    price = os.path.expanduser(f"~/h2data/{S5.MAIN_SHA}/data"); aux = SFD.ensure_aux(S5.MAIN_SHA)
    Wd, unid = SFD.world(price, aux, SFD.EARLY); cal = Wd["cal"]; n = len(cal)
    d0 = int(cal.searchsorted(pd.Timestamp("2025-01-02"))); d1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    R = SFD.compute(price, aux, d0, d1, W=Wd, uni=unid)
    idd = {s: i for i, s in enumerate(unid["stock_id"])}; p5 = {d: int(cal5.get_loc(d)) for d in cal[d0:d1 + 1]}
    rng = np.random.default_rng(20260930); info = {}; errs = []
    # ── W1、W2
    names = {"W1": TW.W1N[0], "W2a": "W2a 再次進入處置", "W2b": "W2b 處置出關"}
    samp = []
    for k, nm in names.items():
        ss, dd = np.nonzero(SIG[nm][:, p5[cal[d0]]:p5[cal[d1]] + 1]); dd = dd + p5[cal[d0]]
        pick = rng.choice(len(ss), min({"W1": 20, "W2a": 15, "W2b": 15}[k], len(ss)), replace=False)
        samp += [(k, uni5.loc[ss[j], "stock_id"], cal5[dd[j]]) for j in pick]
    for j in range(300):                                   # 另抽 300 個隨機股-日（看有沒有多出來的訊號）
        s = int(rng.integers(len(uni5))); d = cal[int(rng.integers(d0, d1 + 1))]
        samp.append(("隨機", uni5.loc[s, "stock_id"], d))
    FL = {}; nb = {"W1": 0, "W2a": 0, "W2b": 0}; ncmp = 0
    for k, sid, d in samp:
        if sid not in idd:
            continue
        if sid not in FL:
            i = idd[sid]; disp = np.zeros(n, bool)
            for a_, b_ in Wd["DISP"].get(sid, []):
                disp[max(a_, 0):min(b_, n - 1) + 1] = True
            X_ = SFL.stock_ctx(sid, unid.loc[i, "market"], cal, n, price, aux, Wd["DISP"], disp)
            FL[sid] = SFL.signals_for(R, i, X_, Wd["DISP"], sid)
        t = int(cal.get_loc(d)) - d0; s5 = int(uni5.index[uni5["stock_id"] == sid][0]); q = p5[d]
        for kk, j in (("W1", 0), ("W2a", 1), ("W2b", 2)):
            nb[kk] += int(bool(FL[sid][j][t]) != bool(SIG[names[kk]][s5, q]))
        ncmp += 1
    info["W1／W2 比對股-日數"] = ncmp; info["不同"] = nb
    if sum(nb.values()):
        errs.append(f"W 訊號不同 {nb}")
    # ── 中段底分數
    TR = pd.read_csv("backtest/resultsSurge6/topwarn/check_Bp_m7.csv.gz")
    col = f"{TW.W1N[0]}|日"; TR = TR[TR[col].notna()].sample(frac=1, random_state=3)
    names_bj = SFL.bj_scorer(); bnames, mstar, bounds = names_bj
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r")
    from backtest import researchSurge5_feat as FT
    LVN = {f"{l[4]}｜{l[3]}": l for l in FT.levels()}
    disp5 = np.load(os.path.join(S5.WORK, "disp.npy")); tdcc = np.asarray(np.load(os.path.join(S5.WORK, "F.npy"), mmap_mode="r")[S5.FIX["tdcc_20"]])
    got = []; CTXr = {}; CTXd = {}
    for r in TR.to_dict("records"):
        if len(got) >= 50:
            break
        s5 = int(r["s"]); e5 = int(r["e"]); sid = uni5.loc[s5, "stock_id"]; d1_ = int(r[col])
        if sid not in idd:
            continue
        c = C[s5].astype(float); o = O[s5].astype(float); okop = np.isfinite(o) & (o > 0) & bar5[s5]
        ex1 = next((p for p in range(d1_ + 1, n5) if okop[p]), None); stop = int(r["stop"])
        if ex1 is None or cal5[e5] < cal[d0]:
            continue
        rmx = np.maximum.accumulate(c[e5:stop + 1]); below = c[e5:stop + 1] <= rmx * 0.8 * (1 + 1e-9)
        cross = [e5 + k for k in np.flatnonzero(below[1:] & ~below[:-1]) + 1 if e5 + k > ex1 and e5 + k < stop]
        if not cross or cal5[cross[0]] > cal[d1]:
            continue
        d2 = cross[0]
        # 研究版
        if s5 not in CTXr:
            CTXr[s5] = BJ.stock_ctx(sid, uni5.loc[s5, "market"], cal5, n5, W5, disp5[s5])
        A = e5 + int(np.argmax(c[e5:d2 + 1]))
        cuts = [(e5 + a, e5 + b) for a, b, lo, hi in MD.pullbacks(c[e5:A + 1]) if a > 0 and lo <= hi * 0.8 * (1 + 1e-9)] if A - e5 > 2 else []
        Lp = cuts[-1][1] if cuts else e5
        f = {k_: float(v_[0]) for k_, v_ in BJ.pull_feats(CTXr[s5], np.array([A]), np.array([d2]), np.array([Lp]), np.array([e5]), np.array([len(cuts)]), np.array([tdcc[s5, d2]])).items()}
        qv5 = lambda nm, s5=s5, d2=d2: np.asarray(Qm[LVN[nm][0], s5, d2]) == LVN[nm][2]
        ref = sum(TW.bj_has(nm_, f, {f"{k}": v for k, v in bounds.items()}, 0.20, qv5) for nm_ in bnames)
        # 每日版
        i = idd[sid]; ed_ = int(cal.get_loc(cal5[e5])); dd2 = int(cal.get_loc(cal5[d2]))
        if sid not in CTXd:
            disp = np.zeros(n, bool)
            for a_, b_ in Wd["DISP"].get(sid, []):
                disp[max(a_, 0):min(b_, n - 1) + 1] = True
            CTXd[sid] = SFL.stock_ctx(sid, unid.loc[i, "market"], cal, n, price, aux, Wd["DISP"], disp)
        cd = CTXd[sid]["c"]; Ad = ed_ + int(np.argmax(cd[ed_:dd2 + 1]))
        cutsd = [(ed_ + a, ed_ + b) for a, b, lo, hi in MD.pullbacks(cd[ed_:Ad + 1]) if a > 0 and lo <= hi * 0.8 * (1 + 1e-9)] if Ad - ed_ > 2 else []
        Lpd = cutsd[-1][1] if cutsd else ed_
        fd = {k_: float(v_[0]) for k_, v_ in BJ.pull_feats(CTXd[sid], np.array([Ad]), np.array([dd2]), np.array([Lpd]), np.array([ed_]), np.array([len(cutsd)]), np.array([np.nan])).items()}
        mine = sum(SFL.bj_has(nm_, fd, bounds, lambda nm, i=i, dd2=dd2: SFL._qv(R, i, dd2, nm)) for nm_ in bnames)
        got.append({"代號": sid, "進場": str(cal5[e5].date()), "跨越日": str(cal5[d2].date()), "研究版分數": int(ref), "每日版分數": int(mine)})
    G = pd.DataFrame(got); nbs = int((G["研究版分數"] != G["每日版分數"]).sum()) if len(G) else -1
    info["中段底分數 比對筆數"] = len(G); info["中段底分數 不同"] = nbs; info["分數分佈（研究版）"] = G["研究版分數"].value_counts().sort_index().to_dict() if len(G) else {}
    if nbs:
        errs.append(f"分數不同 {nbs}")
    out = {"G3": info, "錯誤": errs, "分數明細": got}
    json.dump(out, open(os.path.join(OUT, "G3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("G3", json.dumps(info, ensure_ascii=False, default=str), "錯誤", errs)


if __name__ == "__main__":
    main()
