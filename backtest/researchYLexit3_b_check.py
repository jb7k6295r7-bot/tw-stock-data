# -*- coding: utf-8 -*-
"""PREREG營量出場 seq3 甲件 b 掃描描述臂：簡短查核（⛔ 不 import researchYLexit3_b、researchYLexit3、researchYLexit）。
甲件路徑用 researchYLexit3_check（seq3 的獨立查核，自寫）同一套 ⇒ 自重建 b10_H40、b15_H80（主世界）⇒ 種子 0 eq_sha ＝ bsweep/seeds.csv；
bcurve.csv 的 b0／3／5 列 ＝ resultsYLexit3 cells.csv；新列年化 ＝ seeds.csv。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLexit3_b_check.py
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import researchYLexit3_check as C3

OUT = "backtest/resultsYLexit3/bsweep"


def main():
    RES = {}
    SD = pd.read_csv(os.path.join(OUT, "seeds.csv"), dtype={"eq_sha": str})
    TB = pd.read_csv(os.path.join(OUT, "bcurve.csv"))
    old = pd.read_csv("backtest/resultsYLexit3/cells.csv").set_index("格")
    bad = []
    for r in TB[TB["來源"] != "本描述臂"].to_dict("records"):
        o = old.loc[r["格"]]
        if any(abs(r[f"{sg}_年化"] - o[f"{sg}_年化"]) > 1e-15 for sg in ("探索", "確認", "早年")):
            bad.append(r["格"])
    for r in TB[TB["來源"] == "本描述臂"].to_dict("records"):
        g = SD[(SD["世界"] == "主") & (SD["格"] == r["格"])].iloc[0]
        if abs(g["確認_年化"] - r["確認_年化"]) > 1e-15:
            bad.append(r["格"])
    RES["① bcurve ＝ resultsYLexit3（舊 b）／seeds（新 b）"] = {"不符": bad, "過": not bad}
    RR.use_snapshot()
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True); cal = ctx["cal"]; cl, op, NP = ctx["closes"], ctx["opens"], ctx["ncal"]; mk = ctx["mk"]; w1 = ctx["w1"]
    base = ctx["sig13"]; ALL = RR._G["AND"]
    rvd = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "yoy"])
    rev = {s: list(zip(g["signal_pos"].astype(int), g["yoy"].astype(float))) for s, g in rvd.groupby("stock_id")}
    B = {s: C3.load(s, mk, cal, rev) for s in sorted(set(base["sid"]))}
    newk = {s: set(g["k"].astype(int)) for s, g in ALL.groupby("sid")}
    SF = {}
    for s in sorted(cl):
        st_ = D.load_stock(s, mk.get(s, "twse"), cal)
        if st_ is None:
            continue
        v_ = np.flatnonzero(np.isfinite(st_.df["close"].to_numpy(float)))
        if len(v_) and v_[-1] < w1:
            SF[s] = int(v_[-1])
    bad2 = []
    for bb, H in ((0.10, 40), (0.15, 80)):
        sj = base if H == 60 else C3.exit_h(base, H, B, len(cal), {})
        TJ, ac, ao, hm, _ = C3.jia3(sj, H, bb, cl, op, NP, len(cal), B, newk)
        SFJ = {**SF, **{k_: SF[u] for k_, u in hm.items() if u in SF and k_ != u}}
        eq = C3.run(TJ, f"H{H}", {**cl, **ac}, {**op, **ao}, NP, SFJ, hm)
        nm = f"營量_甲3_b{int(round(bb * 100))}_H{H}"
        ref = SD[(SD["世界"] == "主") & (SD["格"] == nm)]["eq_sha"].iloc[0]
        if C3.h16(eq) != ref:
            bad2.append(nm)
    RES["② 自重建 b10_H40、b15_H80（主）⇒ eq_sha ＝ seeds.csv"] = {"不符": bad2, "過": not bad2}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES["③ 閘（主程式）"] = {**S["閘"], "過": all(S["閘"].values())}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(RES, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
