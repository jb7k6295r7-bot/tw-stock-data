# -*- coding: utf-8 -*-
"""PREREGP9 12 格的獨立重算（硬性查核）。⛔ 不 import researchP9run（也不 import 任何 backtest 模組）；只讀逐種子檔。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchP9run_check.py [backtest/resultsP9run]

從 seeds_arms.csv／seeds_controls.csv／seeds_fake.csv（round_trip 讀）獨立重算：
  ① 每格 年化中位、回落中位、比值、年化波動中位 ⇒ 與 cells.csv 逐位元（repr）比
  ② 標籤（合格／另列／不合格）：0050 錨值手打常數（裁定 seq141／rerun17 ANCHOR），條件一嚴格 ＞、條件二 ≥
  ③ 對基準臂的逐種子配對差中位、種子合格比例
  ④ 對照臂：各版本的年化中位、比值與甲'／乙'／丙'
  ⑤ 假訊號臂：每次 50 顆的中位 ⇒ 標籤 ⇒ x／30 合格
  ⑥ 2-B 加成中位、現金不足中位
中位一律用 statistics.median（純 Python，⛔ 不用 pandas／numpy 的 median）⇒ 與主程式不同實作。
"""
import csv
import json
import os
import statistics as st
import sys

C50 = 0.24020209886370614
M50 = -0.3395700527611012
R50 = C50 / abs(M50)
D = sys.argv[1] if len(sys.argv) > 1 else "backtest/resultsP9run"


def rd(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fl(x):
    return float(x) if x not in ("", None) else float("nan")


def lab(c, m):
    r = c / abs(m)
    if c > C50:
        return "合格" if r >= R50 else "另列"
    return "不合格"


def main():
    arms = rd("seeds_arms.csv"); cells = {r["arm"]: r for r in rd("cells.csv")}
    by = {}
    for r in arms:
        by.setdefault(r["arm"], {})[int(r["r"])] = r
    out = {"cells": {}, "mismatch": []}
    base = by["base"]
    for k, g in by.items():
        c = st.median([fl(r["cagr"]) for r in g.values()]); m = st.median([fl(r["mdd"]) for r in g.values()])
        v = st.median([fl(r["vol"]) for r in g.values()])
        ratio = c / abs(m); L = lab(c, m)
        ref = cells[k]
        for nm, mine, theirs in (("cagr", c, ref["cagr"]), ("mdd", m, ref["mdd"]), ("ratio", ratio, ref["ratio"]), ("vol", v, ref["vol"])):
            if repr(mine) != repr(float(theirs)):
                out["mismatch"].append((k, nm, repr(mine), theirs))
        if L != ref["label_desc"]:
            out["mismatch"].append((k, "label", L, ref["label_desc"]))
        dc = st.median([fl(g[r]["cagr"]) - fl(base[r]["cagr"]) for r in g]); dm = st.median([fl(g[r]["mdd"]) - fl(base[r]["mdd"]) for r in g])
        qs = sum(lab(fl(r["cagr"]), fl(r["mdd"])) == "合格" for r in g.values()) / len(g)
        for nm, mine, theirs in (("d_cagr_med", dc, ref["d_cagr_med"]), ("d_mdd_med", dm, ref["d_mdd_med"]), ("seed_Q_share", qs, ref["seed_Q_share"])):
            if abs(mine - float(theirs)) > 1e-15:
                out["mismatch"].append((k, nm, mine, theirs))
        d = {"n": len(g), "年化中位": c, "回落中位": m, "比值": ratio, "波動中位": v, "標籤": L, "配對年化差中位": dc, "配對回落差中位": dm, "種子合格比例": qs}
        if k in ("Ba", "Bb", "Bc"):
            an = st.median([fl(r["x_add_n"]) for r in g.values()]); sh = st.median([fl(r["x_add_short"]) for r in g.values()])
            d.update({"加成中位": an, "現金不足中位": sh, "倍數": sh / an, "近乎不可得（中位≤2）": an <= 2})
        out["cells"][k] = d
    # 對照臂
    ctl = rd("seeds_controls.csv"); ctab = rd("controls.csv")
    grp = {}
    for r in ctl:
        grp.setdefault((r["cell"], r["version"]), []).append(r)
    out["controls"] = {}
    for row in ctab:
        g = grp[(row["cell"], row["version"])]
        c = st.median([fl(r["cagr"]) for r in g]); m = st.median([fl(r["mdd"]) for r in g]); ratio = c / abs(m)
        cc = out["cells"][row["cell"]]
        wc = cc["年化中位"] >= c; wr = cc["比值"] >= ratio
        cls = "甲'" if (wc and wr) else ("乙'" if (wc or wr) else "丙'")
        if repr(c) != repr(float(row["cagr"])) or repr(ratio) != repr(float(row["ratio"])) or cls != row["class"]:
            out["mismatch"].append(("control", row["cell"], row["version"], c, row["cagr"], cls, row["class"]))
        out["controls"][f"{row['cell']}|{row['version']}"] = {"n": len(g), "年化中位": c, "比值": ratio, "類": cls}
    # 假訊號
    fk = rd("seeds_fake.csv"); ftab = {r["cell"]: r for r in rd("fake.csv")}
    fg = {}
    for r in fk:
        fg.setdefault((r["cell"], int(r["j"])), []).append(r)
    out["fake"] = {}
    for cell in sorted({k for k, _ in fg}):
        labs = []
        for j in sorted(j for c_, j in fg if c_ == cell):
            g = fg[(cell, j)]
            labs.append(lab(st.median([fl(r["cagr"]) for r in g]), st.median([fl(r["mdd"]) for r in g])))
        x = sum(l == "合格" for l in labs)
        if x != int(ftab[cell]["x_Q"]):
            out["mismatch"].append(("fake", cell, x, ftab[cell]["x_Q"]))
        out["fake"][cell] = {"合格": x, "另列": sum(l == "另列" for l in labs), "次數": len(labs), "每次顆數": len(fg[(cell, 1)])}
    out["通過"] = not out["mismatch"]
    json.dump(out, open(os.path.join(D, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"通過": out["通過"], "不符": out["mismatch"][:20],
                      "標籤": {k: v["標籤"] for k, v in out["cells"].items()},
                      "假訊號": out["fake"]}, ensure_ascii=False, indent=1))
    return 0 if out["通過"] else 1


if __name__ == "__main__":
    sys.exit(main())
