# -*- coding: utf-8 -*-
"""PREREG滑價 獨立查核（⛔ 不 import researchSlip；只讀輸出）。主窗。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSlip_check.py

 ① 臂的輸入自寫（σ20、ADV20、均價、一字漲跌停旗標從原始 CSV 自算；C1／C5 成本自算）⇒ 用共用引擎重跑營量 r＝0、營飆 r＝0～2 的
    C1 0.3%、C2 50 萬、C3、C4、C5 20 元、現實版、現實版＋C5 ⇒ 主窗年化／回落 ＝ seeds_main.csv.gz
 ② 零附加成本（原件）＝ rerun17／regime_t1 逐種子檔（由 seeds_main 讀、自己比）
 ③ 由 seeds_main 自算表格中位與標籤 ＝ table_main.csv
共用：rerun17.setup_and（AND 訊號、價格）、research11.simulate_mtm、tradability.one（漲跌停價的跳動單位規則）、research11.stop_force_days
"""
from __future__ import annotations
import json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
from backtest import research11 as R
from backtest import data as D
from backtest import tradability as TR

OUT = os.path.expanduser("~/tw-p17/backtest/resultsSlip")
C0 = R.COST


def extra(sid, cal):
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    st = D.load_stock(sid, "twse", cal)
    df = st.df; n = len(cal)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)
    avg = (o + h + l + c) / 4.0
    sig = np.full(n, np.nan); adv = np.full(n, np.nan)
    b = np.flatnonzero(np.isfinite(c))
    if len(b) > 21:
        rb = c[b][1:] / c[b][:-1] - 1.0                           # rb[j−1] ＝ 進 b[j] 的報酬
        SW = np.lib.stride_tricks.sliding_window_view(rb, 20)      # SW[k] ＝ rb[k..k+19] ＝ 進 b[k+1..k+20]
        sdv = np.std(SW, axis=1, ddof=1)
        AW = np.lib.stride_tricks.sliding_window_view(amt[b], 20)  # AW[k] ＝ b[k..k+19] 的金額
        amv = AW.mean(axis=1)
        for i in range(21, len(b) + 1):                            # 值來自 b[i−20..i−1] ⇒ 適用 t ∈ (b[i−1], b[i]]（最後一段到日曆尾）
            lo_t = b[i - 1] + 1; hi_t = b[i] if i < len(b) else n - 1
            sig[lo_t:hi_t + 1] = sdv[i - 21]; adv[lo_t:hi_t + 1] = amv[i - 20]
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close"]).drop_duplicates("date")
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.set_index("date").reindex(cal)
    ro, rh, rl, rc = (pd.to_numeric(raw[k], errors="coerce").to_numpy(float) for k in ("open", "high", "low", "close"))
    tb = TR.one(sid, cal)
    return {"avg": avg, "sig": sig, "adv": adv, "trd": tb["trd"], "up_o": tb["up_o"] & (rl == ro), "dn_o": tb["dn_o"] & (rh == ro), "dn_c": tb["dn_c"] & (rh == rc),
            "valid": np.isfinite(c)}


def main():
    RR.use_snapshot()
    cal = D.load_calendar(); n = len(cal); w0, w1 = RR.win_bounds(cal)
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", print)
    G = RR._G; reg = G["regime"]; reg1 = np.zeros_like(reg); reg1[1:] = reg[:-1]
    AND = G["AND"]; e = AND["entry_pos"].to_numpy(); inw = (e >= w0) & (e <= w1)
    SIG = {1: AND[reg1[e] & inw], 13: AND[inw]}
    sids = sorted(set(SIG[1]["sid"]) | set(SIG[13]["sid"]))
    X = {s: extra(s, cal) for s in sids}
    print("[資料] 自算完成", flush=True)
    SF = {s: int(np.flatnonzero(v["valid"])[-1]) for s, v in X.items() if np.flatnonzero(v["valid"])[-1] < w1}
    off = TR.load_official()
    dl = TR.delist_status({s: {"trd": X[s]["trd"]} for s in X}, cal, official=off)
    SD = pd.read_csv(os.path.join(OUT, "seeds_main.csv.gz"), float_precision="round_trip")
    CF = {1: ("H120", 10, 1000, 25_000), 13: ("H60", 20, 7000, 12_500)}
    ARMS = {"C1 +0.3%": dict(s=0.003), "C2 50 萬": dict(cap=500_000), "C3 一字漲跌停": dict(c3=True), "C4 均價成交": dict(c4=True),
            "C5 低消 20 元（＋C4）": dict(c4=True, m5=20), "現實版（C1 0.3%＋C2 50 萬＋C3＋C4）": dict(s=0.003, cap=500_000, c3=True, c4=True),
            "現實版＋C5 低消 20 元": dict(s=0.003, cap=500_000, c3=True, c4=True, m5=20)}
    diffs = []
    for cell in (1, 13):
        rule, N, s0, A = CF[cell]; base = SIG[cell]
        for arm, sp in ARMS.items():
            sig = base.copy(); g = sig[f"g_{rule}"].to_numpy(float).copy()
            ee = sig["entry_pos"].to_numpy(int); xx = sig[f"xpos_{rule}"].to_numpy(int)
            op = G["opens"]
            if sp.get("c4"):
                op = dict(G["opens"]); op.update({s: X[s]["avg"] for s in X})
                for i, (s, a_, b_) in enumerate(zip(sig["sid"], ee, xx)):
                    va, vb = X[s]["avg"][a_], X[s]["avg"][b_]
                    if np.isfinite(va) and va > 0 and np.isfinite(vb):
                        g[i] = vb / va - 1
            if sp.get("cap"):
                Q = sp["cap"] / N
                for i, (s, a_, b_) in enumerate(zip(sig["sid"], ee, xx)):
                    def imp(t):
                        v = X[s]["sig"][t] * math.sqrt(Q / X[s]["adv"][t]) if (np.isfinite(X[s]["adv"][t]) and X[s]["adv"][t] > 0) else 0.0
                        return 0.0 if not np.isfinite(v) else v
                    g[i] = (1 + g[i]) * (1 - min(imp(b_), 0.99)) / (1 + imp(a_)) - 1
            sig[f"g_{rule}"] = g
            cost = C0 + 2 * sp.get("s", 0.0) + (2 * max(sp["m5"] / A - 0.001425, 0.0) if sp.get("m5") else 0.0)
            kw = {"stop_force": SF}
            if sp.get("c3"):
                kw["tradable"] = {s: {k: X[s][k] for k in ("trd", "up_o", "dn_o", "dn_c")} for s in set(sig["sid"])}
                kw["delist"] = {s: v for s, v in dl.items() if s in kw["tradable"]}
            for r in ((0, 1, 2) if cell == 1 else (0,)):
                R.COST = cost
                try:
                    if cell == 1:
                        o = R.simulate_mtm(sig, rule, N, np.random.default_rng(s0 + r), G["closes"], op, n, return_equity=True, **kw)
                    else:
                        o = R.simulate_mtm(sig, rule, N, np.random.default_rng(s0 + r), G["closes"], op, n, log=[], d_max=None, pick="relvol", queue_days=0, return_equity=True, **kw)
                finally:
                    R.COST = C0
                c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], w0, w1)
                ref = SD[(SD["cell"] == cell) & (SD["arm"] == arm) & (SD["r"] == r)].iloc[0]
                diffs.append((cell, arm, r, max(abs(c_ - ref["cagr"]), abs(m_ - ref["mdd"]))))
        print(f"[①] cell {cell} 完成", flush=True)
    mx = max(d[3] for d in diffs)
    RES = {"① 自寫臂輸入重跑": {"比對": len(diffs), "最大差": float(mx), "最差": [d for d in diffs if d[3] == mx][0][:3], "過": bool(mx < 1e-9)}}
    ref1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), float_precision="round_trip"); ref1 = ref1[(ref1["stage"] == "t1") & (ref1["cell"] == 1)].set_index("r")
    ref13 = pd.read_csv(os.path.join(RR.OUT, "rerun17_seeds.csv"), float_precision="round_trip"); ref13 = ref13[(ref13["stage"] == "main") & (ref13["cell"] == 13)].set_index("r")
    bad = 0; cnt = 0
    for cell, ref in ((1, ref1), (13, ref13)):
        g = SD[(SD["cell"] == cell) & (SD["arm"] == "原件（stop_force 關）")]
        for _, x in g.iterrows():
            cnt += 1; bad += int(float(x["cagr"]) != float(ref.at[int(x["r"]), "cagr"]) or float(x["mdd"]) != float(ref.at[int(x["r"]), "mdd"]))
    RES["② 零附加成本＝原件"] = {"比對": cnt, "不同": bad, "過": bad == 0}
    T = pd.read_csv(os.path.join(OUT, "table_main.csv")); S = json.load(open(os.path.join(OUT, "summary_main.json"), encoding="utf-8")); Z = S["0050"]["主窗"]
    bad = 0
    for _, t in T.iterrows():
        cell = 1 if t["策略"] == "營飆 v1" else 13
        x = SD[(SD["cell"] == cell) & (SD["arm"] == t["臂"])]
        c, m = float(x["cagr"].median()), float(x["mdd"].median())
        lab = "合格" if (c > Z[0] and c / abs(m) >= Z[0] / abs(Z[1])) else ("另列" if c > Z[0] else "不合格")
        bad += int(abs(c - t["主窗_年化"]) > 1e-12 or abs(m - t["主窗_回落"]) > 1e-12 or lab != t["主窗_標籤"])
    RES["③ 表格中位與標籤"] = {"不同": bad, "過": bad == 0}
    RES["全部過"] = all(v["過"] is True for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
