# -*- coding: utf-8 -*-
"""researchYFallin 獨立查核（回測線計算子代理；⛔ 不改既有檔、⛔ 不 import researchYFallin 的迴圈）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYFallin_check

 C1 另寫一支小引擎 mini()（dict 記部位、自己從 SIG 建每日候選；⛔ 不呼叫 researchYFallin.sim）
    ① W1／W2／W3 兩世界：逐日權益、逐日持股檔數 vs backtest/resultsYFallin/daily_W.csv.gz（權益相對差 ≤ 1e−12、持股 0 不同）
    ② 營飆 v1 r ∈ {0, 57, 199} 兩世界：mini 逐日權益 vs research11.simulate_mtm（相對差 ≤ 1e−12）、eq_sha vs resultsYFallin/seeds.csv.gz
 C2 抽樣日逐日重建持倉：每帳每世界抽 25 個交易日（rng 2026，窗內），只用 trades_W.csv.gz 的買賣紀錄與收盤價重建
    持有集合（買進日 ≤ t ＜ 賣出日）、現金（1 − 買進和 ＋ 賣出淨入帳和）、持股市值（金額 × 收盤 ÷ 買價）⇒ 權益 vs daily_W（相對差 ≤ 1e−9）、持股數 0 不同；
    並列出 2 個抽樣日的持倉明細（代號、買進日、占權益）
 C3 cells.csv 各格中位、比值、對 0050 由 seeds.csv.gz 重算（0 不同）
 C4 共用引擎未改：git diff 對 backtest/research11.py、backtest/rerun17.py 為空
輸出 backtest/resultsYFallin/check.json、run_check.log
"""
from __future__ import annotations

import hashlib
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

OUT = os.environ.get("YFA_OUT", "backtest/resultsYFallin")
COST = R.COST
N = 10
RS = (0, 57, 199)
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def cand_table(sig):
    by = {}; first = None; last = None
    for sid, e, x, g in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"], sig["g_H120"]):
        if pd.isna(sid) or pd.isna(e) or pd.isna(x) or pd.isna(g) or x < 0:
            continue
        e = int(e); x = int(x)
        by.setdefault(e, []).append((sid, x, float(g)))
        first = e if first is None else min(first, e); last = x if last is None else max(last, x)
    return by, first, last


def mini(W, mode, r=None):
    by, first, last = cand_table(W["SIG"][True])
    NP = W["NP"]; cl, op, SF = W["closes"], W["opens"], W["SF"]
    rng = np.random.default_rng(RR.P10_SEED0 + r) if mode == "v1" else None
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
        if rows and ((mode == "W3" and n0 == 0) or (mode != "W3" and n0 < N)):
            slot = eq[t - 1] / N
            if mode == "v1":
                perm = rng.permutation(len(rows))
                pick = [rows[i] for i in perm[:N - n0]]
                amts = []
                for z in pick:
                    a = min(slot, cash)
                    if a <= 1e-9:
                        break
                    amts.append(a); cash -= a
                pick = pick[:len(amts)]
            else:
                k = len(rows)
                if mode == "W1":
                    a = slot if cash >= slot * k else cash / k
                elif mode == "W2":
                    a = min(cash / k, slot)
                else:
                    a = cash / k
                if a > 1e-9:
                    pick = rows; amts = []
                    for _ in rows:
                        aa = min(a, cash); amts.append(aa); cash -= aa
                else:
                    pick, amts = [], []
            for (s, x, g), a in zip(pick, amts):
                ep = float(op[s][t])
                if not (np.isfinite(ep) and ep > 0):
                    ep = float(cl[s][t])
                pos[s] = [x, a, g, ep]
        hv = 0.0
        for s, (ex, amt, g, ep) in pos.items():
            hv += amt * float(cl[s][t]) / ep
        eq[t] = cash + hv; cnt[t] = len(pos)
    end = min(NP, last + 2)
    eq[:first] = 1.0; eq[end:] = eq[end - 1]
    return eq, cnt


def mini_w1b(W):
    """W1b 獨立版：dict 記部位；回 本帳、備用金現金、超額市值、超額檔數。"""
    by, first, last = cand_table(W["SIG"][True])
    NP = W["NP"]; cl, op, SF = W["closes"], W["opens"], W["SF"]
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
            for j, (s, x, g) in enumerate(rows):
                a = min(slot, cash) if j < free else 0.0
                if a > 1e-9:
                    cash -= a; isx = False
                else:
                    a = slot; rc -= a; isx = True
                ep = float(op[s][t])
                if not (np.isfinite(ep) and ep > 0):
                    ep = float(cl[s][t])
                pos[s] = [x, a, g, ep, isx]
        hm = 0.0; hx = 0.0
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
    return E, RC, X, NX


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
    DL = pd.read_csv(os.path.join(OUT, "daily_W.csv.gz"), float_precision="round_trip")
    TL = pd.read_csv(os.path.join(OUT, "trades_W.csv.gz"), float_precision="round_trip", dtype={"sid": str})
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip")
    CK = {}
    # C1 ①
    for wn, W in WW.items():
        for m in ("W1", "W2", "W3"):
            eq, cnt = mini(W, m)
            d = DL[(DL["世界"] == wn) & (DL["帳"] == m)].sort_values("t")
            e2 = d["權益"].to_numpy(float); c2 = d["持股"].to_numpy(int)
            CK[f"C1① {wn} {m} 權益最大相對差"] = float(np.max(np.abs(eq - e2) / np.abs(e2)))
            CK[f"C1① {wn} {m} 持股不同天數"] = int((cnt != c2).sum())
    # C1 ③ W1b
    CBk = pd.DataFrame(json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))["W1b"]["表"])   # 全精度（cells_W1b.csv 只存 10 位）
    for wn, W in WW.items():
        E, RC, X, NX = mini_w1b(W)
        d = pd.read_csv(os.path.join(OUT, f"daily_W1b_{wn}.csv.gz"), float_precision="round_trip").sort_values("t")
        CK[f"C1③ {wn} W1b 本帳權益最大相對差"] = float(np.max(np.abs(E - d["本帳"].to_numpy()) / d["本帳"].to_numpy()))
        CK[f"C1③ {wn} W1b 備用金現金＋超額市值最大相對差"] = float(np.max(np.abs((RC + X) - (d["備用金現金"] + d["超額市值"]).to_numpy()) / d["本帳"].to_numpy()))
        CK[f"C1③ {wn} W1b 超額檔數不同天數"] = int((NX != d["超額檔"].to_numpy()).sum())
        Q = float(CBk[CBk["世界"] == wn]["Q（本帳起始＝1）"].iloc[0])
        Cc = (E + Q + RC + X) / (1 + Q)
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]
            _, f0, l0 = cand_table(W["SIG"][True])
            c_, m_, _ = RR.win_metrics(Cc, f0, min(W["NP"], l0 + 2), x, y)
            rr = CBk[(CBk["世界"] == wn) & (CBk["段"] == sg)].iloc[0]
            CK[f"C1③ {wn} {sg} W1b 合併年化相對差"] = abs(c_ - rr["合併年化"]) / abs(rr["合併年化"])
            CK[f"C1③ {wn} {sg} W1b 合併回落相對差"] = abs(m_ - rr["合併回落"]) / abs(rr["合併回落"])
    # C1 ②
    for wn, W in WW.items():
        for r in RS:
            eq, _ = mini(W, "v1", r)
            o = R.simulate_mtm(W["SIG"][True], "H120", N, np.random.default_rng(RR.P10_SEED0 + r), W["closes"], W["opens"], W["NP"],
                               return_equity=True, stop_force=W["SF"])
            CK[f"C1② {wn} v1 r{r} mini vs simulate_mtm 最大相對差"] = float(np.max(np.abs(eq - o["equity"]) / o["equity"]))
            s_ = SE[(SE["世界"] == wn) & (SE["帳"] == "v1") & (SE["r"] == r)]["eq_sha"].iloc[0]
            CK[f"C1② {wn} v1 r{r} simulate_mtm eq_sha ≠ seeds"] = int(sha(o["equity"]) != s_)
    # C2 抽樣日重建
    rng = np.random.default_rng(2026); SAMPLE = {}
    for wn, W in WW.items():
        cl = W["closes"]
        for m in ("W1", "W2", "W3", "v1", "YL"):
            tl = TL[(TL["世界"] == wn) & (TL["帳"] == m)]
            d = DL[(DL["世界"] == wn) & (DL["帳"] == m)].set_index("t")
            bu = tl[tl["side"] == "buy"]; se = tl[tl["side"] == "sell"]
            sell_t = {}
            for s, t in zip(se["sid"], se["t"]):
                sell_t.setdefault(s, []).append(int(t))
            lots = []
            for s, t, amt, px in zip(bu["sid"], bu["t"], bu["amt"], bu["px"]):
                ts = min([z for z in sell_t.get(s, []) if z > t], default=10 ** 9)
                lots.append((s, int(t), ts, float(amt), float(px)))
            ts_ = rng.choice(np.arange(W["w0"], W["w1"] + 1), 25, replace=False)
            worst = 0.0; cdiff = 0
            for t in sorted(ts_):
                hold = [z for z in lots if z[1] <= t < z[2]]
                cash = 1.0 - float(bu[bu["t"] <= t]["amt"].sum()) + float((se[se["t"] <= t]["amt_out"] - se[se["t"] <= t]["cost"]).sum())
                hv = sum(a * float(cl[s][t]) / px for s, _, _, a, px in hold)
                e_ = cash + hv
                worst = max(worst, abs(e_ - d.loc[t, "權益"]) / d.loc[t, "權益"]); cdiff += int(len(hold) != int(d.loc[t, "持股"]))
                if m in ("W1", "W3") and len(SAMPLE.get((wn, m), [])) < 2 and len(hold) >= 3:
                    SAMPLE.setdefault((wn, m), []).append({"日期": str(W["cal"][t].date()), "權益": e_, "持倉": [
                        {"代號": s, "買進日": str(W["cal"][tb].date()), "占權益": a * float(cl[s][t]) / px / e_} for s, tb, _, a, px in hold]})
            CK[f"C2 {wn} {m} 抽 25 日 權益最大相對差"] = float(worst)
            CK[f"C2 {wn} {m} 抽 25 日 持股數不同"] = cdiff
    # C3
    C = pd.read_csv(os.path.join(OUT, "cells.csv"), encoding="utf-8-sig")
    MN = {"營飆 v1（抽籤）": "v1", "營量 v1": "YL", "W1 同日全買·可超過10檔": "W1", "W2 同日全買·資金平分": "W2", "W3 一波只買第一天": "W3"}
    bad = 0
    for _, row in C.iterrows():
        g = SE[(SE["世界"] == row["世界"]) & (SE["帳"] == MN[row["帳"]])]
        c_ = float(g[f"{row['段']}_年化"].median()); m_ = float(g[f"{row['段']}_回落"].median())
        b = {"cagr": row["0050年化"], "mdd": row["0050回落"]}
        if abs(c_ - row["年化"]) > 1e-9 or abs(m_ - row["回落"]) > 1e-9 or abs(c_ / abs(m_) - row["比值"]) > 1e-8 or IG.label(c_, m_, b) != row["對0050"]:
            bad += 1
    CK["C3 cells 重算不同格數"] = bad
    # C4
    df_ = subprocess.run(["git", "diff", "--stat", "--", "backtest/research11.py", "backtest/rerun17.py"], capture_output=True, text=True).stdout.strip()
    CK["C4 research11／rerun17 有改動"] = int(bool(df_))
    log(json.dumps(CK, ensure_ascii=False, indent=1))
    for k, v in SAMPLE.items():
        log(f"[抽樣持倉] {k}：{json.dumps(v, ensure_ascii=False)[:1500]}")
    tol = {"C1①": 1e-12, "C1②": 1e-12, "C1③": 1e-10, "C2": 1e-9}
    fail = [k for k, v in CK.items() if (v > tol[k.split()[0]] if "相對差" in k else v != 0)]
    json.dump({"結果": CK, "不過": fail, "抽樣持倉": {f"{a}·{b}": v for (a, b), v in SAMPLE.items()}}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=float)
    log(f"[查核] {'全過' if not fail else '不過 ' + str(fail)}")


if __name__ == "__main__":
    main()
