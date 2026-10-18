# -*- coding: utf-8 -*-
"""researchYLallin 獨立查核（回測線計算子代理；⛔ 不改既有檔、⛔ 不 import researchYFallin／researchYLallin 的迴圈）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLallin_check

 C1 另寫一支小引擎 mini()（dict 記部位、自己從 SIG[無閘] 建每日候選、自己排 relvol）：
    ① 營量 v1、V1 兩世界：逐日權益、逐日持股 vs backtest/resultsYLallin/daily.csv.gz（權益相對差 ≤ 1e−12、持股 0 不同）；營量 v1 另對 research11.simulate_mtm
    ② V1b 兩世界：本帳、備用金現金＋超額市值、超額檔數 vs daily_V1b_*.csv.gz；合併年化／回落 vs summary（相對差 ≤ 1e−10）
 C2 抽樣日逐日重建持倉：每帳每世界抽 25 個交易日（rng 2026，窗內），只用買賣紀錄與收盤價重建持有集合、現金、市值 ⇒ 權益 vs 逐日檔（相對差 ≤ 1e−9）、持股數 0 不同；
    V1b 分本帳與備用金兩邊各自重建；列 2 個抽樣日（V1 持股 ＞ 20 的日子優先）的持倉明細
 C3 cells.csv 的年化、回落、比值、對 0050 由 daily.csv.gz 重算（0 不同）
 C4 策略鎖 python -m backtest.strategy_lock --check 相符；git diff 對 researchYFallin.py、research11.py、rerun17.py 為空
輸出 backtest/resultsYLallin/check.json、run_check.log
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402

OUT = os.environ.get("YLA_OUT", "backtest/resultsYLallin")
COST = R.COST
N = 20
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}


def cand_table(sig):
    by = {}; first = None; last = None
    for sid, e, x, g, k in zip(sig["sid"], sig["entry_pos"], sig["xpos_H60"], sig["g_H60"], sig["relvol"]):
        if pd.isna(sid) or pd.isna(e) or pd.isna(x) or pd.isna(g) or x < 0:
            continue
        e = int(e); x = int(x)
        by.setdefault(e, []).append((sid, x, float(g), float(k)))
        first = e if first is None else min(first, e); last = x if last is None else max(last, x)
    return by, first, last


def by_relvol(rows):
    idx = sorted(range(len(rows)), key=lambda i: (0, -rows[i][3], i) if np.isfinite(rows[i][3]) else (1, 0.0, i))
    return [rows[i] for i in idx]


def entry_px(W, s, t):
    ep = float(W["opens"][s][t])
    return ep if (np.isfinite(ep) and ep > 0) else float(W["closes"][s][t])


def mini(W, mode):
    by, first, last = cand_table(W["SIG"][False])
    NP = W["NP"]; cl, SF = W["closes"], W["SF"]
    eq = np.ones(NP); cnt = np.zeros(NP, int); cash = 1.0; pos = {}
    for t in range(first, min(NP, last + 2)):
        for s in list(pos):
            L = SF.get(s)
            if L is not None and t == L + 1 and pos[s][0] > t:
                pos[s][0] = t; pos[s][2] = float(cl[s][L]) / pos[s][3] - 1.0
        for s in [s for s in pos if pos[s][0] <= t]:
            ex, amt, g, ep = pos.pop(s)
            cash += amt * (1 + g - COST)
        rows = [z for z in by.get(t, []) if z[0] not in pos]
        n0 = len(pos)
        if rows and n0 < N:
            slot = eq[t - 1] / N; pick, amts = [], []
            if mode == "YL":
                for z in by_relvol(rows)[:N - n0]:
                    a = min(slot, cash)
                    if a <= 1e-9:
                        break
                    pick.append(z); amts.append(a); cash -= a
            else:
                k = len(rows)
                a = slot if cash >= slot * k else cash / k
                if a > 1e-9:
                    for z in rows:
                        aa = min(a, cash); pick.append(z); amts.append(aa); cash -= aa
            for (s, x, g, _), a in zip(pick, amts):
                pos[s] = [x, a, g, entry_px(W, s, t)]
        eq[t] = cash + sum(amt * float(cl[s][t]) / ep for s, (ex, amt, g, ep) in pos.items()); cnt[t] = len(pos)
    end = min(NP, last + 2)
    eq[:first] = 1.0; eq[end:] = eq[end - 1]
    return eq, cnt, first, end


def mini_v1b(W):
    by, first, last = cand_table(W["SIG"][False])
    NP = W["NP"]; cl, SF = W["closes"], W["SF"]
    E = np.ones(NP); RC = np.zeros(NP); X = np.zeros(NP); NX = np.zeros(NP, int)
    cash = 1.0; rc = 0.0; pos = {}
    for t in range(first, min(NP, last + 2)):
        for s in list(pos):
            L = SF.get(s)
            if L is not None and t == L + 1 and pos[s][0] > t:
                pos[s][0] = t; pos[s][2] = float(cl[s][L]) / pos[s][3] - 1.0
        for s in [s for s in pos if pos[s][0] <= t]:
            ex, amt, g, ep, isx = pos.pop(s)
            if isx:
                rc += amt * (1 + g - COST)
            else:
                cash += amt * (1 + g - COST)
        rows = [z for z in by.get(t, []) if z[0] not in pos]
        if rows and len(pos) < N:
            free = N - len(pos); slot = E[t - 1] / N
            for j, (s, x, g, _) in enumerate(by_relvol(rows)):
                a = min(slot, cash) if j < free else 0.0
                if a > 1e-9:
                    cash -= a; isx = False
                else:
                    a = slot; rc -= a; isx = True
                pos[s] = [x, a, g, entry_px(W, s, t), isx]
        hm = hx = 0.0
        for s, (ex, amt, g, ep, isx) in pos.items():
            v = amt * float(cl[s][t]) / ep
            if isx:
                hx += v
            else:
                hm += v
        E[t] = cash + hm; RC[t] = rc; X[t] = hx; NX[t] = sum(1 for p in pos.values() if p[4])
    end = min(NP, last + 2)
    E[:first] = 1.0
    for A in (E, RC, X, NX):
        A[end:] = A[end - 1]
    return E, RC, X, NX, first, end


def lots_of(tl):
    bu = tl[tl["side"] == "buy"]; se = tl[tl["side"] == "sell"]
    sell_t = {}
    for s, t in zip(se["sid"], se["t"]):
        sell_t.setdefault(s, []).append(int(t))
    lots = []
    for s, t, amt, px, x in zip(bu["sid"], bu["t"], bu["amt"], bu["px"], bu["超額"]):
        ts = min([z for z in sell_t.get(s, []) if z > t], default=10 ** 9)
        lots.append((s, int(t), ts, float(amt), float(px), int(x)))
    return bu, se, lots


def log_to(path):
    f = open(path, "a", encoding="utf-8")

    def log(m):
        print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def main():
    log = log_to(os.path.join(OUT, "run_check.log"))
    log(f"[查核開始] {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）")
    Wm, _ = IG.main_world(log)
    We, _ = IG.early_world(log, 3)
    WW = {"主": Wm, "早年": We}
    DL = pd.read_csv(os.path.join(OUT, "daily.csv.gz"), float_precision="round_trip")
    TL = pd.read_csv(os.path.join(OUT, "trades.csv.gz"), float_precision="round_trip", dtype={"sid": str})
    SM = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = {}; FE = {}
    # C1 ①
    for wn, W in WW.items():
        for m in ("YL", "V1"):
            eq, cnt, f0, e0 = mini(W, m); FE[(wn, m)] = (f0, e0)
            d = DL[(DL["世界"] == wn) & (DL["帳"] == m)].sort_values("t")
            e2 = d["權益"].to_numpy(float); c2 = d["持股"].to_numpy(int)
            CK[f"C1① {wn} {m} 權益最大相對差"] = float(np.max(np.abs(eq - e2) / np.abs(e2)))
            CK[f"C1① {wn} {m} 持股不同天數"] = int((cnt != c2).sum())
        o = R.simulate_mtm(W["SIG"][False], "H60", N, np.random.default_rng(RR.P1_SEED0), W["closes"], W["opens"], W["NP"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"])
        eq, *_ = mini(W, "YL")
        CK[f"C1① {wn} YL mini vs simulate_mtm 最大相對差"] = float(np.max(np.abs(eq - o["equity"]) / o["equity"]))
    # C1 ② V1b
    CB = pd.DataFrame(SM["V1b"]["表"])
    for wn, W in WW.items():
        E, RC, X, NX, f0, e0 = mini_v1b(W)
        d = pd.read_csv(os.path.join(OUT, f"daily_V1b_{wn}.csv.gz"), float_precision="round_trip").sort_values("t")
        CK[f"C1② {wn} V1b 本帳權益最大相對差"] = float(np.max(np.abs(E - d["本帳"].to_numpy()) / d["本帳"].to_numpy()))
        CK[f"C1② {wn} V1b 備用金現金＋超額市值最大相對差"] = float(np.max(np.abs((RC + X) - (d["備用金現金"] + d["超額市值"]).to_numpy()) / d["本帳"].to_numpy()))
        CK[f"C1② {wn} V1b 超額檔數不同天數"] = int((NX != d["超額檔"].to_numpy()).sum())
        Q = float(CB[CB["世界"] == wn]["Q（本帳起始＝1）"].iloc[0])
        CK[f"C1② {wn} V1b Q 相對差（mini 重算）"] = abs(max(float(np.max(d["超額成本"])), float(max(0.0, -RC.min()))) - Q) / Q
        Cc = (E + Q + RC + X) / (1 + Q)
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]
            c_, m_, _ = RR.win_metrics(Cc, f0, e0, x, y)
            rr = CB[(CB["世界"] == wn) & (CB["段"] == sg)].iloc[0]
            CK[f"C1② {wn} {sg} V1b 合併年化相對差"] = abs(c_ - rr["合併年化"]) / abs(rr["合併年化"])
            CK[f"C1② {wn} {sg} V1b 合併回落相對差"] = abs(m_ - rr["合併回落"]) / abs(rr["合併回落"])
    # C2 抽樣日重建
    rng = np.random.default_rng(2026); SAMPLE = {}
    for wn, W in WW.items():
        cl = W["closes"]
        for m in ("YL", "V1", "YFW1"):
            tl = TL[(TL["世界"] == wn) & (TL["帳"] == m)].copy(); tl["超額"] = tl["超額"].fillna(0)
            d = DL[(DL["世界"] == wn) & (DL["帳"] == m)].set_index("t")
            bu, se, lots = lots_of(tl)
            ts_ = list(rng.choice(np.arange(W["w0"], W["w1"] + 1), 25, replace=False))
            if m == "V1":                                        # 加 2 個持股 > 20 的日子（有的話）
                big = d[(d["持股"] > N) & (d.index >= W["w0"]) & (d.index <= W["w1"])].index.to_numpy()
                ts_ += list(big[:: max(1, len(big) // 2)][:2]) if len(big) else []
            worst = 0.0; cdiff = 0
            for t in sorted(ts_):
                hold = [z for z in lots if z[1] <= t < z[2]]
                cash = 1.0 - float(bu[bu["t"] <= t]["amt"].sum()) + float((se[se["t"] <= t]["amt_out"] - se[se["t"] <= t]["cost"]).sum())
                e_ = cash + sum(a * float(cl[s][t]) / px for s, _, _, a, px, _ in hold)
                worst = max(worst, abs(e_ - d.loc[t, "權益"]) / d.loc[t, "權益"]); cdiff += int(len(hold) != int(d.loc[t, "持股"]))
                if m == "V1" and len(hold) > N and len(SAMPLE.get((wn, m), [])) < 2:
                    SAMPLE.setdefault((wn, m), []).append({"日期": str(W["cal"][t].date()), "權益": e_, "持股": len(hold), "現金": cash, "持倉": [
                        {"代號": s, "買進日": str(W["cal"][tb].date()), "占權益": a * float(cl[s][t]) / px / e_, "超額標記": x} for s, tb, _, a, px, x in hold]})
            CK[f"C2 {wn} {m} 抽 {len(ts_)} 日 權益最大相對差"] = float(worst)
            CK[f"C2 {wn} {m} 抽 {len(ts_)} 日 持股數不同"] = cdiff
        tl = pd.read_csv(os.path.join(OUT, f"trades_V1b_{wn}.csv.gz"), float_precision="round_trip", dtype={"sid": str})
        d = pd.read_csv(os.path.join(OUT, f"daily_V1b_{wn}.csv.gz"), float_precision="round_trip").set_index("t")
        bu, se, lots = lots_of(tl)
        worst = 0.0; cdiff = 0
        for t in sorted(rng.choice(np.arange(W["w0"], W["w1"] + 1), 25, replace=False)):
            for side in (0, 1):
                hold = [z for z in lots if z[1] <= t < z[2] and z[5] == side]
                b_ = bu[(bu["t"] <= t) & (bu["超額"] == side)]; s_ = se[(se["t"] <= t) & (se["超額"] == side)]
                c_ = (1.0 if side == 0 else 0.0) - float(b_["amt"].sum()) + float((s_["amt_out"] - s_["cost"]).sum())
                hv = sum(a * float(cl[s][t]) / px for s, _, _, a, px, _ in hold)
                ref = d.loc[t, "本帳"] if side == 0 else d.loc[t, "備用金現金"] + d.loc[t, "超額市值"]
                worst = max(worst, abs(c_ + hv - ref) / d.loc[t, "本帳"])
                if side == 1:
                    cdiff += int(len(hold) != int(d.loc[t, "超額檔"]))
        CK[f"C2 {wn} V1b 抽 25 日 本帳／備用金重建最大相對差"] = float(worst)
        CK[f"C2 {wn} V1b 抽 25 日 超額檔數不同"] = cdiff
    # C3
    C = pd.read_csv(os.path.join(OUT, "cells.csv"), encoding="utf-8-sig")
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    MN = {"營量 v1": "YL", "V1 營量同日全買·可超過20檔": "V1", "營飆 W1（重算）": "YFW1"}
    bad = 0
    for _, row in C.iterrows():
        if row["帳"] not in MN:
            continue
        m = MN[row["帳"]]; W = WW[row["世界"]]; x, y = W["segp"][row["段"]]
        d = DL[(DL["世界"] == row["世界"]) & (DL["帳"] == m)].sort_values("t")["權益"].to_numpy(float)
        s_ = SE[(SE["世界"] == row["世界"]) & (SE["帳"] == m)].iloc[0]
        c_, m_, _ = RR.win_metrics(d, int(s_["first"]), int(s_["end"]), x, y)
        b = {"cagr": row["0050年化"], "mdd": row["0050回落"]}
        if abs(c_ - row["年化"]) > 1e-9 or abs(m_ - row["回落"]) > 1e-9 or abs(c_ / abs(m_) - row["比值"]) > 1e-8 or IG.label(c_, m_, b) != row["對0050"]:
            bad += 1
    CK["C3 cells 重算不同格數"] = bad
    # C4
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    CK["C4 策略鎖 --check 不符（exit code）"] = int(lk.returncode)
    df_ = subprocess.run(["git", "diff", "--stat", "--", "backtest/researchYFallin.py", "backtest/research11.py", "backtest/rerun17.py"], capture_output=True, text=True).stdout.strip()
    CK["C4 researchYFallin／research11／rerun17 有改動"] = int(bool(df_))
    log(json.dumps(CK, ensure_ascii=False, indent=1))
    log(f"[策略鎖] {lk.stdout.strip()[-400:]}")
    for k, v in SAMPLE.items():
        log(f"[抽樣持倉] {k}：{json.dumps(v, ensure_ascii=False)[:2500]}")
    tol = {"C1①": 1e-12, "C1②": 1e-10, "C2": 1e-9}
    fail = [k for k, v in CK.items() if (v > tol[k.split()[0]] if "相對差" in k else v != 0)]
    json.dump({"結果": CK, "不過": fail, "策略鎖": lk.stdout.strip(), "抽樣持倉": {f"{a}·{b}": v for (a, b), v in SAMPLE.items()}},
              open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] {'全過' if not fail else '不過 ' + str(fail)}")


if __name__ == "__main__":
    main()
