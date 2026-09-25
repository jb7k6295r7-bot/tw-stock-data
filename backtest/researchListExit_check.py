# -*- coding: utf-8 -*-
"""PREREG名單出場 乙 的獨立查核（⛔ 不 import researchListExit）：只讀 resultsListExit/seeds_arms.csv、cells.csv 與
resultsN17/regime_t1/seeds.csv，重算每一臂的年化中位、回落中位、比值、標籤、對營飆 v1 的配對計數與判語，逐項比對 cells.csv。

    python backtest/researchListExit_check.py [--dir backtest/resultsListExit]
輸出 check.json（同目錄）；任一項不符 ⇒ 結束碼 1。
"""
import argparse
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
C50, R50 = 0.24020209886370614, 0.7073712681980713
JUDGED = ["S1", "S2", "T1", "T2", "S1T1", "S2T1"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(HERE, "resultsListExit"))
    a = ap.parse_args()
    A = pd.read_csv(os.path.join(a.dir, "seeds_arms.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    TB = pd.read_csv(os.path.join(a.dir, "cells.csv"), float_precision="round_trip").set_index("arm")
    ref = pd.read_csv(os.path.join(HERE, "resultsN17", "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r").sort_index()
    out = {"arms": {}, "bad": []}
    reps = int(A.groupby("arm").size().min())
    base = ref.loc[range(reps)]
    b = A[A["arm"] == "base"].set_index("r").sort_index()
    same = all(repr(float(b.loc[r, k])) == repr(float(base.loc[r, k])) for r in b.index for k in ("cagr", "mdd", "vol")) and \
        all(int(b.loc[r, k]) == int(base.loc[r, k]) for r in b.index for k in ("first", "end", "trades")) and \
        all(str(b.loc[r, "eq_sha"]) == str(base.loc[r, "eq_sha"]) for r in b.index)
    out["base＝regime_t1 t1 #1"] = bool(same)
    if not same:
        out["bad"].append("base")
    for arm, g in A.groupby("arm", sort=False):
        g = g.set_index("r").sort_index()
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        ratio = c / abs(m)
        lab = "合格" if (c > C50 and ratio >= R50) else ("另列" if c > C50 else "不合格")
        dc = g["cagr"] - base["cagr"]; dm = g["mdd"] - base["mdd"]
        npos = int(((dc > 0) & (dm > 0)).sum()); nneg = int(((dc < 0) & (dm < 0)).sum())
        vs = "比原本好" if npos >= 190 else ("比原本差" if nneg >= 190 else "分不出")
        q = TB.loc[arm]
        ok = {"n": int(len(g)) == int(q["n"]), "cagr_med": repr(c) == repr(float(q["cagr_med"])), "mdd_med": repr(m) == repr(float(q["mdd_med"])),
              "label": q["label"].replace("（描述）", "") == lab, "both_pos": npos == int(q["vs_v1_both_pos"]), "both_neg": nneg == int(q["vs_v1_both_neg"]),
              "vs_v1": q["vs_v1"].replace("（描述）", "") == vs}
        out["arms"][arm] = {"label": lab, "vs_v1": vs, "both_pos": npos, "both_neg": nneg, "ok": ok}
        if not all(ok.values()):
            out["bad"].append(arm)
    good = [k for k in JUDGED if out["arms"][k]["vs_v1"] == "比原本好"]
    out["判定6格"] = {k: (out["arms"][k]["label"], out["arms"][k]["vs_v1"]) for k in JUDGED}
    out["比原本好格數"] = len(good)
    json.dump(out, open(os.path.join(a.dir, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"base＝regime_t1": out["base＝regime_t1 t1 #1"], "臂數": len(out["arms"]), "不符": out["bad"], "判定6格": out["判定6格"]},
                     ensure_ascii=False))
    sys.exit(1 if out["bad"] else 0)


if __name__ == "__main__":
    main()
