# -*- coding: utf-8 -*-
"""讀法丙（假訊號條件）小查核——重算部分 ⛔ 不 import 主程式／假訊號程式；重跑部分以子行程呼叫 researchExplore_fakecond --only 0。

    python3 backtest/researchExplore_fakecond_check.py [--no-rerun]

① 從 fakecond_seeds.csv 重算每次的年化中位、回落中位、甲式比值（中位÷|中位|）、乙式比值（逐種子比值的中位）⇒ 對 fakecond_171.csv
② 重算 171 個值的 p5～p99、max、每條線索的分位與「是否大於最大」⇒ 對 fakecond_summary.json
③ i＝0 在 SEED_F＝103000 下重跑（子行程、獨立輸出目錄）⇒ 200 列逐欄（含權益曲線 sha1）與 fakecond_seeds.csv 相同
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

O = "backtest/resultsExplore/fakecond"
QS = (0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)


def med(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return x[n // 2] if n % 2 else (x[n // 2 - 1] + x[n // 2]) / 2.0


def main():
    os.chdir(os.path.expanduser("~/tw-p17"))
    fails = []
    S = pd.read_csv(os.path.join(O, "fakecond_seeds.csv"), dtype={"cell": str}, float_precision="round_trip")
    X = pd.read_csv(os.path.join(O, "fakecond_171.csv"), float_precision="round_trip").set_index("fake_i")
    J = json.load(open(os.path.join(O, "fakecond_summary.json"), encoding="utf-8"))
    CL = pd.read_csv("backtest/resultsExplore/clues.csv", dtype={"cell": str}, float_precision="round_trip")
    # ①
    if sorted(S["fake_i"].unique()) != list(range(171)):
        fails.append("次數")
    mine = {}
    for i, g in S.groupby("fake_i"):
        if sorted(g["seed"]) != list(range(102000, 102200)) or (g["seed_f"] != 103000 + i).any():
            fails.append(f"種子 {i}")
        A, D = med(g["cagr"]), med(g["mdd"])
        mine[int(i)] = (A, D, A / abs(D), med(g["cagr"] / g["mdd"].abs()))
    d = max(max(abs(mine[i][0] - X.loc[i, "A"]), abs(mine[i][1] - X.loc[i, "D"]), abs(mine[i][2] - X.loc[i, "ratio_cell"]),
                abs(mine[i][3] - X.loc[i, "ratio_seedmed"])) for i in mine)
    print(f"① 171 次的中位與兩式比值重算：最大差 {d:.2e}")
    if d > 1e-12:
        fails.append("中位")
    # ②
    for j, tag in ((2, "甲式 年化中位÷|回落中位|（與格同形，主）"), (3, "乙式 逐種子比值的中位（字面）")):
        v = np.array([mine[i][j] for i in range(171)])
        mx = v.max(); js = J[tag]
        dq = max(abs(float(np.quantile(v, q)) - js[f"p{int(q * 100)}"]) for q in QS)
        dq = max(dq, abs(mx - js["max"]), abs(mx - js["171次取最大"]))
        cl_ok = True
        for r, c in zip(CL.itertuples(), js["線索"]):
            q = float((v <= r.ratio).mean())
            cl_ok &= (c["cell"] == r.cell and abs(q - c["在171個中的分位（≤它的比例）"]) < 1e-15 and bool(r.ratio > mx) == c["大於171次取最大"])
        print(f"② {tag[:2]}：分位與 max 最大差 {dq:.2e}｜線索分位與「大於最大」全同 {cl_ok}")
        if dq > 1e-12 or not cl_ok:
            fails.append(f"分位 {tag[:2]}")
    # ③
    if "--no-rerun" not in sys.argv:
        chk = os.path.join(O, "_chk_i0")
        if os.path.exists(chk):
            shutil.rmtree(chk)
        r = subprocess.run([sys.executable, "backtest/researchExplore_fakecond.py", "--only", "0", "--out", chk],
                           env=dict(os.environ, PYTHONPATH=os.path.expanduser("~/tw-p17")), capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:]); fails.append("重跑失敗")
        else:
            A = pd.read_csv(os.path.join(O, "fakecond_seeds.csv"), dtype=str)
            A = A[A["fake_i"] == "0"].reset_index(drop=True)
            B = pd.read_csv(os.path.join(chk, "fakecond_seeds.csv"), dtype=str)
            same = A.equals(B)
            print(f"③ i＝0（SEED_F 103000）重跑 200 列逐欄相同 {same}（權益曲線 sha1 例 {B['eq_sha'].iloc[0]}）")
            if not same:
                fails.append("重跑不同")
            shutil.rmtree(chk)
    print("查核結果：" + ("✅ 全部一致" if not fails else f"⛔ {fails}"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
