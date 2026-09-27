# -*- coding: utf-8 -*-
"""W1、F 確認段補跑 獨立查核（⛔ 不 import researchAFCext／researchAFC；只讀輸出）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAFCext_check.py

 ① 門檻B 訊號自寫（panel_ext：eligible ∧ rev_hi24＝100 ∧ ma60_up＝100 ∧ ma_stack＝0、量測日 ≥ 2017-01-01、進場＝量測日＋1、出場＝進場＋119、
    進場開盤與出場收盤有限）⇒ ＝ sig_ext.csv.gz 逐列；F 剔除自寫（量測日 eligible 內 ret_120 百分位 ＞ 0.95）⇒ 剔除數 ＝ summary
 ② 停止交易日自寫（主窗尾前最後一根有效收盤）⇒ 檔數 ＝ summary
 ③ 引擎（research11.simulate_mtm，共用）用自寫的訊號與 stop_force 重跑 W1 種子 102000～102002 ⇒ 主窗年化／回落 ＝ seeds.csv.gz 的 V2 列
 ④ 由 seeds.csv.gz 自算三版的中位、主窗與確認段 K6 判準、假訊號 p ⇒ ＝ summary
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2
from backtest import research11 as R
from backtest import research13 as R13
from backtest import tradability as TR
D = H2.D
OUT = "backtest/resultsAFCext"


def lab(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES = {}
    cal = D.load_calendar(); n = len(cal); pos = {d: i for i, d in enumerate(cal)}
    p = pd.read_csv("backtest/resultsp9_engine/panel_ext.csv.gz", dtype={"stock_id": str}, parse_dates=["measure_date"])
    uni = D.load_universe().set_index("stock_id")["market"]
    C, O, V = {}, {}, {}
    for s in sorted(set(p["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float); C[s] = pd.Series(c).ffill().to_numpy(); O[s] = st.df["open"].to_numpy(float); V[s] = np.isfinite(c)
    q = p[(p["measure_date"] >= pd.Timestamp("2017-01-01")) & (p["eligible"].astype(str).isin(["True", "1", "1.0"]))]
    m = (q["rev_hi24"] == 100) & (q["ma60_up"] == 100) & (q["ma_stack"] == 0)
    rows = []
    for d, s in zip(q.loc[m, "measure_date"], q.loc[m, "stock_id"]):
        if d not in pos or s not in C:
            continue
        e = pos[d] + 1; x = e + 119
        if e >= n:
            continue
        o = O[s][e]
        if x >= n:                                   # 尾端截斷補回（V3）：出場設墊檔日 n、報酬照最後收盤
            if np.isfinite(o) and o > 0:
                rows.append((s, e, n, float(C[s][n - 1]) / o - 1.0))
            continue
        c = C[s][x]
        if not (np.isfinite(o) and o > 0 and np.isfinite(c)):
            continue
        rows.append((s, e, x, c / o - 1.0))
    mine = pd.DataFrame(rows, columns=["sid", "entry_pos", "xpos_H120", "g_H120"]).sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    sig = pd.read_csv(os.path.join(OUT, "sig_ext.csv.gz"), dtype={"sid": str})
    same = len(mine) == len(sig) and (mine["sid"].values == sig["sid"].values).all() and (mine["entry_pos"].values == sig["entry_pos"].values).all() \
        and np.allclose(mine["g_H120"].values, sig["g_H120"].values, rtol=0, atol=1e-12)
    el = p[p["eligible"].astype(str).isin(["True", "1", "1.0"])].copy(); el["rk"] = el.groupby("measure_date")["ret_120"].rank(pct=True)
    rk = {(d, s): v for d, s, v in zip(el["measure_date"], el["stock_id"], el["rk"])}
    fdrop = sum(1 for s, e in zip(mine["sid"], mine["entry_pos"]) if rk.get((cal[e - 1], s), np.nan) > 0.95)
    v2 = S["V3 補面板＋尾端截斷補回＋stop_force"]
    RES["① 訊號與 F 剔除"] = {"訊號筆（自算／主程式）": [len(mine), len(sig)], "逐列相同": bool(same), "F 剔（自算／主程式）": [fdrop, v2["F剔"]],
                           "過": bool(same and fdrop == v2["F剔"] and len(mine) == v2["S1筆"])}
    print(RES["① 訊號與 F 剔除"], flush=True)
    w0, w1 = int(cal.searchsorted(pd.Timestamp("2017-03-02"))), int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    SF = {s: int(np.flatnonzero(v)[-1]) for s, v in V.items() if v.any() and np.flatnonzero(v)[-1] < w1}
    RES["② 停止交易日"] = {"自算": len(SF), "主程式": S["停止交易日（主窗尾前停止）"], "過": len(SF) == S["停止交易日（主窗尾前停止）"]}
    # ③ 引擎
    tr = TR.build(set(mine["sid"]), cal); dl = TR.delist_status(tr, cal, official=TR.load_official())
    tr = {s: {k: np.r_[v[k], k == "trd"] for k in ("trd", "up_o", "dn_o", "dn_c")} for s, v in tr.items()}
    CP = {s: np.r_[v, v[-1]] for s, v in C.items()}; OP = {s: np.r_[v, np.nan] for s, v in O.items()}
    SD = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"))
    d3 = []
    for seed in (102000, 102001, 102002):
        o = R.simulate_mtm(mine, "H120", 8, np.random.default_rng(seed), CP, OP, n + 1, return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0,
                           cash_mode="zero", tradable=tr, delist=dl, stop_force=SF)
        lo = min(o["first"], w0)
        c_, m_ = R13.window_stats(o["equity"], lo, max(o["end"], w1 + 1), w0, w1 + 1)
        ref = SD[(SD["版"].str.startswith("V3")) & (SD["kind"] == "W1") & (SD["seed"] == seed)].iloc[0]
        d3.append(max(abs(c_ - ref["cagr"]), abs(m_ - ref["mdd"])))
    RES["③ 引擎重跑（V3 W1 三顆）"] = {"最大差": float(max(d3)), "過": bool(max(d3) < 1e-12)}
    print(RES["③ 引擎重跑（V3 W1 三顆）"], flush=True)
    # ④
    z = S["0050"]; bad = []
    for vn in ("V0 閘（截到 2026-03-02、stop_force 關）", "V1 補面板", "V2 補面板＋stop_force", "V3 補面板＋尾端截斷補回＋stop_force"):
        x = SD[SD["版"] == vn]
        for kind, nm in (("W1", "W1（1,000 顆中位）"), ("F", "F（200 顆中位）")):
            y = x[x["kind"] == kind]
            c, mm, cc, cm = y["cagr"].median(), y["mdd"].median(), y["c_cagr"].median(), y["c_mdd"].median()
            ref = S[vn][nm]
            if max(abs(c - ref["主窗"][0]), abs(mm - ref["主窗"][1]), abs(cc - ref["確認段"][0]), abs(cm - ref["確認段"][1])) > 1e-12:
                bad.append((vn, kind, "中位"))
            if lab(c, mm, *z["主窗"]) != ref["主窗判準"] or lab(cc, cm, *z["確認段"]) != ref["確認段判準"]:
                bad.append((vn, kind, "判準"))
    x = SD[SD["版"].str.startswith("V3")]
    fk = x[x["kind"] == "Ffake"].groupby("arm")["cagr"].median()
    pf = float((fk >= v2["F（200 顆中位）"]["主窗"][0]).mean())
    pw = float((x[x["kind"] == "W1fake"]["cagr"] >= v2["W1（1,000 顆中位）"]["主窗"][0]).mean())
    if abs(pf - v2["F 假訊號臂（30 次 × 200 顆）"]["p（假訊號中位年化 ≥ F）"]) > 1e-12 or abs(pw - v2["W1 假訊號臂（同進場日同筆數、閘門池隨機；200 次）"]["p（假訊號年化 ≥ W1 中位）"]) > 1e-12:
        bad.append(("V2", "假訊號 p"))
    RES["④ 中位、判準、假訊號 p"] = {"不同": bad, "過": not bad}
    RES["全部過"] = all(v["過"] is True for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
