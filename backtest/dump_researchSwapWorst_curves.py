# -*- coding: utf-8 -*-
"""換掉最差那檔正式跑：主世界逐日權益曲線（畫圖用）——回測線計算子代理，2026-11-15。
⛔ 不另寫引擎：原版 ＝ researchGroupRevUp_freq.run_engine、換股版／滿 20 日版 ＝ researchSwapWorst.sim_swap（都經 researchSwapWorst 匯入）；
   訊號表 ＝ researchGroupRevUp.attach_g（產業版族群旗標）；成本 ＝ 引擎 0.585%；大盤報酬指數、0050 ＝ 正式跑同源。
輸出 backtest/resultsSwapWorst/formal/curves_r0.csv：2017-03-02～資料尾逐日一列，各欄 ÷ 2017-03-02 那天的值（＝ 1）。
   另加 營飆_換股版_p10／中位／p90（200 顆種子逐日分位；⚠ 是逐日分位、不是某一顆的曲線）。
驗收：從 csv 讀回的各欄，探索、確認兩段年化與最大回落 ＝ cells.csv（r0 欄、大盤、0050）到小數 4 位。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.dump_researchSwapWorst_curves [--procs 3]
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchSwapWorst as SW   # noqa: E402

M, GR, R, RR, BR, AO = SW.M, SW.GR, SW.R, SW.RR, SW.BR, SW.AO
OUT = os.path.join(SW.OUT if SW.NSEED == 200 else "backtest/resultsSwapWorst/formal", "curves_r0.csv")
X0 = "2017-03-02"
_C: dict = {}


def curves_of(st, r):
    """(原版, 換股版, 滿20日版) 權益；原版走既有引擎、另兩版走 sim_swap。"""
    C = _C
    sig = M.cell_sig(C["S"], st, "原版", dry=False)
    _, _, o, _ = M.run_engine(sig, st, "原版", r, C["cl"], C["NP"], C["SF"], opens=C["op"], full=True)
    on = SW.sim_swap(sig, st, r, C["cl"], C["op"], C["NP"], C["SF"], swap=True)
    on20 = SW.sim_swap(sig, st, r, C["cl"], C["op"], C["NP"], C["SF"], swap=True, min_hold=SW.MIN_HOLD)
    return np.asarray(o["equity"], float), on["equity"], on20["equity"]


def seed_swap(r):
    return curves_of("營飆", r)[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    if abs(R.COST - SW.COST) > 1e-15:
        raise SystemExit(f"⛔ 引擎成本 {R.COST} ≠ 0.585%")
    W = AO.worlds(print, a.procs)["主"]
    Gp = pickle.load(open(os.path.join(M.WORK, "groups_main_industry.pkl"), "rb"))
    S, _ = GR.attach_g(Gp["S"], W)
    cal = W["cal"]; NP = W["NP"]
    _C.update(S=S, cl=W["closes"], op=W["opens"], NP=NP, SF=W["SF"])
    x0 = int(np.flatnonzero(cal == pd.Timestamp(X0))[0]); xe = len(cal) - 1
    if (x0, ) != (W["segp"]["探索"][0], ):
        raise SystemExit("⛔ 起點不是探索段首")
    tri = BR.read_series(GR.TRI_SRC).reindex(cal).ffill().to_numpy(float)
    b50 = np.asarray(W["bench"], float)[:len(cal)]
    cols = {}
    for st in M.STRATS:
        tag = "" if st == "營量" else "(r0)"
        for v, eq in zip(SW.VERS, curves_of(st, 0)):
            cols[f"{st}_{v}{tag}"] = eq[x0:xe + 1] / eq[x0]
    with Pool(a.procs) as pool:
        E = np.array(pool.map(seed_swap, range(SW.NSEED), chunksize=4))[:, x0:xe + 1]
    E = E / E[:, :1]
    cols["營飆_換股版_p10"] = np.percentile(E, 10, axis=0)
    cols["營飆_換股版_中位"] = np.median(E, axis=0)
    cols["營飆_換股版_p90"] = np.percentile(E, 90, axis=0)
    cols["大盤報酬指數"] = tri[x0:xe + 1] / tri[x0]
    cols["0050"] = b50[x0:xe + 1] / b50[x0]
    df = pd.DataFrame({"日期": cal[x0:xe + 1].strftime("%Y-%m-%d"), **cols})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig", float_format="%.10g")
    print(f"[寫出] {OUT}｜{len(df)} 列｜{df['日期'].iloc[0]}～{df['日期'].iloc[-1]}｜種子 {len(E)}")
    verify(cal, x0, W["segp"])


def verify(cal, x0, segp):
    """從 csv 讀回，算兩段年化／最大回落，對 cells.csv 到小數 4 位。"""
    d = pd.read_csv(OUT, encoding="utf-8-sig")
    C = pd.read_csv(os.path.join(os.path.dirname(OUT), "cells.csv"), encoding="utf-8-sig")
    rows = []
    for sg in SW.JSEG:
        x, y = segp[sg]; a, b = x - x0, y - x0 + 1
        for col in d.columns[1:]:
            if col.startswith("營飆_換股版_"):
                continue
            arr = d[col].to_numpy(float)
            c, m = SW.RR.R13.window_stats(arr, 0, len(arr), a, b)
            if col in ("大盤報酬指數", "0050"):
                ref = C[(C["世界"] == "main") & (C["策略"] == "營量") & (C["版"] == "原版") & (C["段"] == sg)].iloc[0]
                rc, rm = (ref["大盤年化"], ref["大盤回落"]) if col == "大盤報酬指數" else (ref["0050年化"], ref["0050回落"])
            else:
                st, v = col.replace("(r0)", "").split("_", 1)
                ref = C[(C["世界"] == "main") & (C["策略"] == st) & (C["版"] == v) & (C["段"] == sg)].iloc[0]
                rc, rm = ref["年化_r0"], ref["回落_r0"]
            same = abs(c - rc) < 5e-5 and abs(m - rm) < 5e-5           # cells.csv 存 6 位有效數字 ⇒ 用 |差| ＜ 0.00005 當「到小數 4 位相同」
            rows.append((sg, col, c, rc, m, rm, same))
            print(f"{'OK ' if same else 'NG '} {sg} {col:<16} 年化 {c:.4f} vs {rc:.4f}｜回落 {m:.4f} vs {rm:.4f}")
    nok = sum(r[-1] for r in rows)
    print(f"[驗收] 相符 {nok}/{len(rows)}")
    if nok != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
