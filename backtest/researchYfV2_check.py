# -*- coding: utf-8 -*-
"""PREREG營飆v2候選 主窗描述的獨立查核（⛔ 不 import researchYfV2）：只讀 resultsYfV2/main_seeds_arms.csv、main_cells.csv、
resultsN17/regime_t1/seeds.csv、resultsYfStop/body_seeds_arms.csv（a_M20）、resultsYfRank/seeds.csv（K4），
重驗三個逐位元閘、重算各臂年化中位／回落中位／標籤（描述）／對營飆 v1 與 C1 對候選一的配對計數，逐項比對。輸出 main_check.json；不符 ⇒ 結束碼 1。"""
import argparse
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
C50, R50 = 0.24020209886370614, 0.7073712681980713
RT = dict(float_precision="round_trip")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(HERE, "resultsYfV2"))
    a = ap.parse_args()
    A = pd.read_csv(os.path.join(a.dir, "main_seeds_arms.csv"), dtype={"eq_sha": str}, **RT)
    TB = pd.read_csv(os.path.join(a.dir, "main_cells.csv"), **RT).set_index("arm")
    arm = {k: g.set_index("r").sort_index() for k, g in A.groupby("arm")}
    ref = pd.read_csv(os.path.join(HERE, "resultsN17", "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, **RT)
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r").sort_index()
    rs = pd.read_csv(os.path.join(HERE, "resultsYfStop", "body_seeds_arms.csv"), dtype={"eq_sha": str}, **RT)
    rs = rs[rs["arm"] == "a_M20"].set_index("r").sort_index()
    rk = pd.read_csv(os.path.join(HERE, "resultsYfRank", "seeds.csv"), dtype={"eq_sha": str}, **RT)
    rk = rk[rk["arm"] == "K4"].set_index("r").sort_index()

    def same(D, R_):
        return bool(all(all(repr(float(D.loc[r, c])) == repr(float(R_.loc[r, c])) for c in ("cagr", "mdd", "vol")) and str(D.loc[r, "eq_sha"]) == str(R_.loc[r, "eq_sha"])
                        for r in D.index))
    out = {"閘": {"base": same(arm["base"], ref), "cand1＝a_M20": same(arm["cand1"], rs), "cand2＝K4": same(arm["cand2"], rk)}, "arms": {}, "bad": []}
    base = ref.loc[arm["base"].index]
    for k, g in arm.items():
        c, m = float(g["cagr"].median()), float(g["mdd"].median()); ratio = c / abs(m)
        lab = "合格" if (c > C50 and ratio >= R50) else ("另列" if c > C50 else "不合格")
        dc = g["cagr"] - base["cagr"]; dm = g["mdd"] - base["mdd"]
        q = TB.loc[k]
        ok = {"cagr_med": repr(c) == repr(float(q["cagr_med"])), "mdd_med": repr(m) == repr(float(q["mdd_med"])), "label": q["label_desc"] == lab,
              "pos": int(((dc > 0) & (dm > 0)).sum()) == int(q["vs_v1_both_pos"]), "neg": int(((dc < 0) & (dm < 0)).sum()) == int(q["vs_v1_both_neg"])}
        if k == "C1":
            c1 = arm["cand1"]; ec = g["cagr"] - c1["cagr"]; em = g["mdd"] - c1["mdd"]
            p_, n_ = int(((ec > 0) & (em > 0)).sum()), int(((ec < 0) & (em < 0)).sum())
            ok.update({"vs_cand1_pos": p_ == int(q["vs_cand1_both_pos"]), "vs_cand1_neg": n_ == int(q["vs_cand1_both_neg"]),
                       "C1≈候選一": (p_ < 190 and n_ < 190) == bool(q["C1≈候選一"])})
        out["arms"][k] = {"cagr_med": c, "mdd_med": m, "label": lab, "ok": ok}
        if not all(ok.values()):
            out["bad"].append(k)
    out["bad"] += [k for k, v in out["閘"].items() if not v]
    json.dump(out, open(os.path.join(a.dir, "main_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"閘": out["閘"], "不符": out["bad"]}, ensure_ascii=False))
    sys.exit(1 if out["bad"] else 0)


if __name__ == "__main__":
    main()
