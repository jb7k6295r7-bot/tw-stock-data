# -*- coding: utf-8 -*-
"""PREREG營飆時停 的獨立查核（⛔ 不 import 主程式）：只讀 seeds_arms.csv、cells.csv 與 resultsN17/regime_t1/seeds.csv，
重算每臂年化中位、回落中位、比值、對 0050 標籤、對營飆 v1 配對計數與判語，逐項比對。輸出同目錄 check.json；不符 ⇒ 結束碼 1。"""
import argparse
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
C50, R50 = 0.24020209886370614, 0.7073712681980713


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(HERE, "resultsYfTime"))
    a = ap.parse_args()
    A = pd.read_csv(os.path.join(a.dir, "seeds_arms.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    TB = pd.read_csv(os.path.join(a.dir, "cells.csv"), float_precision="round_trip").set_index("arm")
    ref = pd.read_csv(os.path.join(HERE, "resultsN17", "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r").sort_index()
    reps = int(A.groupby("arm").size().min()); base = ref.loc[range(reps)]
    b = A[A["arm"] == "base"].set_index("r").sort_index()
    out = {"base＝regime_t1": bool(all(repr(float(b.loc[r, k])) == repr(float(base.loc[r, k])) for r in b.index for k in ("cagr", "mdd", "vol"))
                                   and all(str(b.loc[r, "eq_sha"]) == str(base.loc[r, "eq_sha"]) for r in b.index)), "arms": {}, "bad": []}
    for arm, g in A.groupby("arm", sort=False):
        g = g.set_index("r").sort_index()
        c, m = float(g["cagr"].median()), float(g["mdd"].median()); ratio = c / abs(m)
        lab = "合格" if (c > C50 and ratio >= R50) else ("另列" if c > C50 else "不合格")
        dc = g["cagr"] - base["cagr"]; dm = g["mdd"] - base["mdd"]
        npos = int(((dc > 0) & (dm > 0)).sum()); nneg = int(((dc < 0) & (dm < 0)).sum())
        vs = "好" if npos >= 190 else ("差" if nneg >= 190 else "分不出")
        q = TB.loc[arm]
        ok = {"cagr_med": repr(c) == repr(float(q["cagr_med"])), "mdd_med": repr(m) == repr(float(q["mdd_med"])),
              "label": str(q["label"]).replace("（描述）", "") == lab, "both_pos": npos == int(q["vs_v1_both_pos"]),
              "both_neg": nneg == int(q["vs_v1_both_neg"]), "vs_v1": str(q["vs_v1"]).replace("（描述）", "") == vs}
        out["arms"][arm] = {"label": lab, "vs_v1": vs, "pos": npos, "neg": nneg, "ok": ok}
        if not all(ok.values()):
            out["bad"].append(arm)
    if not out["base＝regime_t1"]:
        out["bad"].append("base")
    json.dump(out, open(os.path.join(a.dir, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"base＝regime_t1": out["base＝regime_t1"], "臂數": len(out["arms"]), "不符": out["bad"],
                      "判定": {k: (v["label"], v["vs_v1"], v["pos"], v["neg"]) for k, v in out["arms"].items() if not k.startswith(("a_", "b_")) and k != "base"}},
                     ensure_ascii=False))
    sys.exit(1 if out["bad"] else 0)


if __name__ == "__main__":
    main()
