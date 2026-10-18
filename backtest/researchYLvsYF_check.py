# -*- coding: utf-8 -*-
"""researchYLvsYF 獨立查核（回測線計算子代理；⛔ 不改主程式結果、只寫 check.json／run_check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLvsYF_check [--procs 3]

 K1 直接呼叫 research11.simulate_mtm（不經 researchYL_integrate.eng）重跑營量 r0、營飆 r ∈ CHK ⇒ eq_sha ＝ seeds.csv.gz／營量 summary
 K2 持股逐日以「事件重放」重建（依 audit 時序：同日先賣後買、集合狀態 ＝ 當日收盤在簿上）⇒ 各段 ⓐⓑ 逐日平均、抽樣日 |F|／|Y|／|F∩Y|（＝ 手算）對 seeds
 K3 買進層 ±5／±0／買時持有：雙重迴圈重算
 K4 閘：0050 200 日均以逐日 Python 迴圈重算（不用 rolling）⇒ 各段閘關日數、被閘擋訊號數 ＝ summary
 K5 日報酬相關以公式手算、一半一半①以逐日迴圈累乘 ⇒ 對 seeds（≤ 1e−9）
 K6 營量閘關／閘開買進：逐筆配對迴圈重算 筆數、淨報酬平均、勝率 ⇒ 對 summary
 K7 績效表：cells 的營量年化／回落 ＝ 整合件 seeds；營飆中位 ＝ resultsYF_N；0050 ＝ 整合件 summary（repr）
 K8 照規則簿：csv 模組重讀 positions.csv ⇒ 交集數
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchYLvsYF as M                    # noqa: E402

OUT = M.OUT
CHK = (0, 1, 2, 57, 199)


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def run_yl(W):
    au = []
    o = R.simulate_mtm(W["SIG"][False], "H60", 20, np.random.default_rng(7000), W["closes"], W["opens"], W["NP"], return_equity=True,
                       log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=au)
    return o, au


def run_yf(W, r):
    au = []
    o = R.simulate_mtm(W["SIG"][True], "H120", 10, np.random.default_rng(1000 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                       stop_force=W["SF"], audit=au)
    return o, au


def replay(au, n):
    """事件重放 ⇒ list[set]：第 d 天收盤在簿上的檔。"""
    ev = {}
    for a in au:
        ev.setdefault(a["t"], []).append(a)
    cur, out = set(), []
    for d in range(n):
        for a in sorted(ev.get(d, []), key=lambda z: z["side"] != "sell"):
            if a["side"] == "sell":
                cur.discard(a["sid"])
            else:
                cur.add(a["sid"])
        out.append(frozenset(cur))
    return out


def buys(au):
    return [(a["sid"], a["t"]) for a in au if a["side"] == "buy"]


def pairs(au):
    op, T = {}, []
    for a in au:
        if a["side"] == "buy":
            op[a["sid"]] = a
        else:
            b = op.pop(a["sid"]); T.append((b, a))
    return T, op


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    log = M.log_to(os.path.join(OUT, "run_check.log"))
    log(f"[查核開始] {M.now_tpe()}（台北）")
    SUM = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip")
    CE = pd.DataFrame(SUM["表"])                               # 全精度（cells.csv 只存 10 位有效數字，不能拿來 repr 對）
    Wm, _ = IG.main_world(log); We, _ = IG.early_world(log, a.procs)
    Wm["bench"] = RR._G["bench"]; We["bench"] = RR.load_bench(We["cal"])
    WS = {"主": Wm, "早年": We}
    K = {}
    bad = {k: 0 for k in ("K1", "K2", "K2抽樣", "K3", "K4", "K5", "K6")}
    maxd = {"K2": 0.0, "K3": 0.0, "K5": 0.0, "K6": 0.0}
    for wn, W in WS.items():
        oY, auY = run_yl(W); eY = np.asarray(oY["equity"], float); n = len(eY)
        bad["K1"] += sha(eY) != SUM["營量"][wn]["eq_sha"]
        HY = replay(auY, n); BYl = buys(auY)
        # K4 閘：逐日迴圈 200 日均
        b = np.asarray(W["bench"], float); reg = np.zeros(len(b), bool)
        for t in range(199, len(b)):
            s = 0.0
            for j in range(t - 199, t + 1):
                s += b[j]
            reg[t] = b[t] > s / 200.0
        closed = np.zeros(n, bool)
        for e in range(1, n):
            closed[e] = (e - 1 < len(reg)) and (not reg[e - 1])
        ent = W["base"]["entry_pos"].to_numpy(int)
        for sg in M.SEGS[wn]:
            x, y = W["segp"][sg]
            g = SUM["大盤閘"][wn][sg]
            nd = sum(1 for d in range(x, y + 1) if closed[d])
            nb = sum(1 for e in ent if x <= e <= y and closed[e])
            bad["K4"] += (nd != g["閘關日"]) + (nb != g["被閘擋訊號"])
            # K6 營量閘關買進
            T, opn = pairs(auY)
            for lab, want in (("閘關", True), ("閘開", False)):
                nets = []
                for bb, ss in T:
                    if x <= bb["t"] <= y and closed[bb["t"]] == want:
                        nets.append(ss["px"] / bb["px"] - 1 - R.COST)
                for s_, bb in opn.items():
                    if x <= bb["t"] <= y and closed[bb["t"]] == want:
                        nets.append(float(W["closes"][s_][min(oY["end"], W["NP"]) - 1]) / bb["px"] - 1 - R.COST)
                bad["K6"] += len(nets) != g[f"營量{lab}買進數"]
                if nets:
                    maxd["K6"] = max(maxd["K6"], abs(float(np.mean(nets)) - g[f"營量{lab}淨報酬平均"]),
                                     abs(float(np.mean(np.array(nets) > 0)) - g[f"營量{lab}勝率"]))
        for r in CHK:
            oF, auF = run_yf(W, r); eF = np.asarray(oF["equity"], float)
            row = SE[(SE["世界"] == wn) & (SE["r"] == r)].iloc[0]
            bad["K1"] += sha(eF) != row["eq_sha"]
            HF = replay(auF, n); BF = buys(auF)
            for sg in M.SEGS[wn]:
                x, y = W["segp"][sg]
                fa, yb = [], []
                for d in range(x, y + 1):
                    it = len(HF[d] & HY[d])
                    if HF[d]:
                        fa.append(it / len(HF[d]))
                    if HY[d]:
                        yb.append(it / len(HY[d]))
                maxd["K2"] = max(maxd["K2"], abs(np.mean(fa) - row[f"{sg}_F中也在Y"]), abs(np.mean(yb) - row[f"{sg}_Y中也在F"]))
                # K3
                fb = [(s, t) for s, t in BF if x <= t <= y]
                yb_ = [(s, t) for s, t in BYl if x <= t <= y]
                m5 = sum(1 for s, t in fb if any(s2 == s and abs(t2 - t) <= 5 for s2, t2 in BYl))
                m0 = sum(1 for s, t in fb if any(s2 == s and t2 == t for s2, t2 in BYl))
                mh = sum(1 for s, t in fb if s in HY[t])
                r5 = sum(1 for s, t in yb_ if any(s2 == s and abs(t2 - t) <= 5 for s2, t2 in BF))
                maxd["K3"] = max(maxd["K3"], abs(m5 / len(fb) - row[f"{sg}_F買Y±5"]), abs(m0 / len(fb) - row[f"{sg}_F買Y±0"]),
                                 abs(mh / len(fb) - row[f"{sg}_F買時Y持有"]), abs(r5 / len(yb_) - row[f"{sg}_Y買F±5"]))
                # K5 相關、一半一半①
                ra = [eF[t] / eF[t - 1] - 1 for t in range(x + 1, y + 1)]; rb = [eY[t] / eY[t - 1] - 1 for t in range(x + 1, y + 1)]
                ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
                cov = sum((u - ma) * (v - mb) for u, v in zip(ra, rb)); va = sum((u - ma) ** 2 for u in ra); vb = sum((v - mb) ** 2 for v in rb)
                maxd["K5"] = max(maxd["K5"], abs(cov / np.sqrt(va * vb) - row[f"{sg}_日報酬相關"]))
                first, end = min(oF["first"], oY["first"]), min(oF["end"], oY["end"])
                eb = np.ones(n)
                for t in range(1, n):
                    rr = 0.0
                    if t < end:
                        rr = 0.5 * (eF[t] / eF[t - 1] - 1) + 0.5 * (eY[t] / eY[t - 1] - 1)
                    eb[t] = eb[t - 1] * (1 + rr)
                c1, m1, _ = RR.win_metrics(eb, first, end, x, y)
                maxd["K5"] = max(maxd["K5"], abs(c1 - row[f"{sg}_半半①年化"]), abs(m1 - row[f"{sg}_半半①回落"]))
            # 抽樣日手算
            for d in W.get("SAMPLE_CHK", [int(c[1:]) for c in SE.columns if c.startswith("d") and c[1:].isdigit() and pd.notna(row[c])]):
                it = len(HF[d] & HY[d])
                bad["K2抽樣"] += f"{len(HF[d])}/{len(HY[d])}/{it}" != row[f"d{d}"]
                if r == 0:
                    K.setdefault("抽樣日手算", []).append({"世界": wn, "日": str(W["cal"][d].date()), "營飆r0持股": sorted(HF[d]), "營量持股數": len(HY[d]),
                                                       "交集": sorted(HF[d] & HY[d]), "營飆中也在營量": it / len(HF[d]) if HF[d] else None,
                                                       "營量中也在營飆": it / len(HY[d]) if HY[d] else None})
        log(f"[{wn}] 查完 {bad}｜{maxd}")
    bad["K2"] = int(maxd["K2"] > 1e-12); bad["K3"] = int(maxd["K3"] > 1e-12); bad["K5"] = int(maxd["K5"] > 1e-9); bad["K6"] += int(maxd["K6"] > 1e-12)
    # K7
    refI = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    yfn = {(z["世界"], z["段"]): z for z in json.load(open("backtest/resultsYF_N/summary.json", encoding="utf-8"))["表"] if z["N"] == 10}
    s50 = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
    k7 = 0
    for _, c in CE.iterrows():
        b_ = refI[(refI["世界"] == c["世界"]) & (refI["格"] == IG.YL) & (refI["r"] == 0)].iloc[0]
        k7 += repr(float(c["營量_年化"])) != repr(float(b_[f"{c['段']}_年化"])) or repr(float(c["營量_回落"])) != repr(float(b_[f"{c['段']}_回落"]))
        z = yfn[(c["世界"], c["段"])]
        k7 += repr(float(c["年化_中位"])) != repr(float(z["年化_中位"])) or repr(float(c["回落_中位"])) != repr(float(z["回落_中位"]))
        k7 += repr(float(c["0050年化"])) != repr(float(s50[c["世界"]][c["段"]]["cagr"]))
    bad["K7"] = int(k7)
    # K8
    rows = list(csv.DictReader(open("backtest/forward/yl_rule/positions.csv", encoding="utf-8-sig")))
    A = {r["代號"] for r in rows if r["策略"] == "營量v1" and r["狀態"] == "持有中"}; B = {r["代號"] for r in rows if r["策略"] == "營飆v1" and r["狀態"] == "持有中"}
    bad["K8"] = int(len(A & B) != SUM["照規則簿"]["交集"] or len(B) != SUM["照規則簿"]["營飆持有中"] or len(A) != SUM["照規則簿"]["營量持有中"])
    K["不同"] = bad; K["最大差"] = maxd; K["查核種子"] = list(CHK); K["主程式閘"] = SUM["閘"]; K["完成（台北）"] = M.now_tpe()
    json.dump(K, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 不同 {bad}｜最大差 {maxd}")
    log("✅ 全過" if all(v == 0 for v in bad.values()) else "⛔ 有不同")


if __name__ == "__main__":
    main()
