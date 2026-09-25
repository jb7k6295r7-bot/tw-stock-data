# -*- coding: utf-8 -*-
"""PREREG營飆排名 判定段的獨立查核（⛔ 不 import researchYfRank）：只讀 resultsYfRank/seeds.csv、cells.csv 與
resultsN17/regime_t1/seeds.csv，重算每鍵的年化中位、逐顆比值中位、兩個百分位（中位秩）、判語、對 0050 標籤、同顆配對計數、買進差中位，逐項比對。

    python backtest/researchYfRank_check.py [--dir backtest/resultsYfRank]
輸出 check.json；任一項不符 ⇒ 結束碼 1。
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
C50, R50 = 0.24020209886370614, 0.7073712681980713
HI, LO = 98.75, 1.25
KEYS = ["K0", "K1", "K2", "K3", "K4"]


def pr(x, d):
    d = np.asarray(d, float)
    return float(((d < x).sum() + 0.5 * (d == x).sum()) / len(d) * 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(HERE, "resultsYfRank"))
    a = ap.parse_args()
    A = pd.read_csv(os.path.join(a.dir, "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    T = pd.read_csv(os.path.join(a.dir, "cells.csv"), float_precision="round_trip").set_index("key")
    ref = pd.read_csv(os.path.join(HERE, "resultsN17", "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r").sort_index()
    lot = A[A["arm"] == "lottery"].set_index("r").sort_index()
    out = {"抽籤版＝regime_t1": bool(all(repr(float(lot.loc[r, c])) == repr(float(ref.loc[r, c])) for r in lot.index for c in ("cagr", "mdd"))),
           "keys": {}, "bad": []}
    lc = lot["cagr"].to_numpy(); lr = (lot["cagr"] / lot["mdd"].abs()).to_numpy()
    for k in KEYS:
        g = A[A["arm"] == k].set_index("r").sort_index()
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        rs = float((g["cagr"] / g["mdd"].abs()).median()); rl = c / abs(m)
        pc, pp = pr(c, lc), pr(rs, lr)
        v = "比抽籤好" if (pc >= HI and pp >= HI) else ("比抽籤差" if (pc <= LO and pp <= LO) else "分不出")
        lab = "合格" if (c > C50 and rl >= R50) else ("另列" if c > C50 else "不合格")
        dc = g["cagr"] - lot["cagr"]; dm = g["mdd"] - lot["mdd"]
        q = T.loc[k]
        ok = {"n": len(g) == len(lot), "cagr_med": repr(c) == repr(float(q["cagr_med"])), "ratio_seed_med": repr(rs) == repr(float(q["ratio_seed_med"])),
              "ratio_label": repr(rl) == repr(float(q["ratio_label"])), "pctl_cagr": repr(pc) == repr(float(q["pctl_cagr"])),
              "pctl_ratio": repr(pp) == repr(float(q["pctl_ratio"])), "verdict": str(q["verdict"]).split("（")[0] == v, "label": q["label_0050"] == lab,
              "both_better": int(((dc > 0) & (dm > 0)).sum()) == int(q["pair_both_better"]), "both_worse": int(((dc < 0) & (dm < 0)).sum()) == int(q["pair_both_worse"]),
              "buy_diff_med": float(g["buy_diff"].median()) == float(q["buy_diff_med"])}
        out["keys"][k] = {"verdict": v, "label": lab, "pctl_cagr": pc, "pctl_ratio": pp, "ok": ok}
        if not all(ok.values()):
            out["bad"].append(k)
    if not out["抽籤版＝regime_t1"]:
        out["bad"].append("lottery")
    json.dump(out, open(os.path.join(a.dir, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"抽籤版＝regime_t1": out["抽籤版＝regime_t1"], "不符": out["bad"],
                      "判語": {k: (v["verdict"], v["label"], round(v["pctl_cagr"], 2), round(v["pctl_ratio"], 2)) for k, v in out["keys"].items()}},
                     ensure_ascii=False))
    sys.exit(1 if out["bad"] else 0)


if __name__ == "__main__":
    main()
