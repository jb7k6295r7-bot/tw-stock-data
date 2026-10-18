# -*- coding: utf-8 -*-
"""researchYLmerge 獨立查核（回測線計算子代理；⛔ 不改主程式結果、只寫 check.json／run_check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLmerge_check [--procs 3]

 K1 直接呼叫 research11.simulate_mtm（不經 researchYL_integrate.eng；參數照字面寫）重跑 營量 v1、M1～M5 r0、營飆 r ∈ CHK ⇒ eq_sha ＝ seeds.csv.gz
 K2 抽樣種子逐日重建持倉（事件重放：同日先賣後買、集合 ＝ 當日收盤在簿上）⇒
    持股檔數逐日平均、與營量 ⓐ（檔數）、ⓒ（金額：逐檔 amt×收盤÷進場價÷權益 迴圈）、現金（1 − 持股市值迴圈 ÷ 權益）、換手（買進金額迴圈）⇒ 對 seeds；
    逐日持股市值迴圈 ＝ 引擎 hold_val（最大相對差）
 K3 各半·年調以逐日迴圈重做（不用 researchp17.compose）、各半·日調逐日累乘 ⇒ 各段年化／回落（自寫公式）、持股聯集 ⇒ 對 seeds
 K4 cells：由 seeds 重算中位、比值、對 0050 標籤 ⇒ 對 summary 表（repr）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchYLmerge as M                   # noqa: E402

OUT = M.OUT
CHK = (0, 57, 199)
SPEC = {"營量v1": (60, 20, False, "relvol"), "M1": (60, 20, True, "relvol"), "M2": (120, 20, False, "relvol"), "M3": (120, 20, True, "relvol"),
        "M4": (120, 10, True, "relvol"), "M5": (90, 15, True, "relvol")}


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def run(W, H, S, G, P, r):
    au = []
    sig = W["SIG"][G]
    if P == "relvol":
        o = R.simulate_mtm(sig, f"H{H}", S, np.random.default_rng(7000 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=au)
    else:
        o = R.simulate_mtm(sig, f"H{H}", S, np.random.default_rng(1000 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                           stop_force=W["SF"], audit=au)
    return o, au


def replay(W, au, n):
    """⇒ sets[d]、value[d]（持股市值）、wts[d]（{sid: 權重}，權重須除權益，回傳市值）、buyamt[d]。"""
    ev = {}
    for a in au:
        ev.setdefault(a["t"], []).append(a)
    cur = {}; sets = []; val = np.zeros(n); mv = []; buy = np.zeros(n)
    for d in range(n):
        for a in sorted(ev.get(d, []), key=lambda z: z["side"] != "sell"):
            if a["side"] == "sell":
                cur.pop(a["sid"])
            else:
                cur[a["sid"]] = (a["amt"], a["px"]); buy[d] += a["amt"]
        sets.append(frozenset(cur))
        m = {}
        for s, (amt, px) in cur.items():
            m[s] = amt * float(W["closes"][s][d]) / px
        val[d] = sum(m.values()); mv.append(m)
    return sets, val, mv, buy


def ann(seq):
    yrs = len(seq) / 245.0
    c = (seq[-1] / seq[0]) ** (1 / yrs) - 1
    pk = seq[0]; mdd = 0.0
    for v in seq:
        pk = max(pk, v); mdd = min(mdd, v / pk - 1)
    return c, mdd


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    log = M.YV.log_to(os.path.join(OUT, "run_check.log"))
    log(f"[查核開始] {M.YV.now_tpe()}（台北）")
    SUM = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip")
    Wm, _ = IG.main_world(log); We, _ = IG.early_world(log, a.procs)
    WS = {"主": Wm, "早年": We}
    bad = {k: 0 for k in ("K1", "K2", "K3", "K4")}
    maxd = {"K2": 0.0, "K2_hold_val相對差": 0.0, "K3": 0.0}
    K = {"抽樣持倉": []}

    def cmp(k, x, y):
        maxd[k] = max(maxd[k], abs(float(x) - float(y)))

    for wn, W in WS.items():
        n = None
        legs = {}
        for nm, sp in SPEC.items():
            o, au = run(W, *sp, 0)
            legs[nm] = (o, au)
        oY, auY = legs["營量v1"]; eY = np.asarray(oY["equity"], float); n = len(eY)
        HY, valY, mvY, buyY = replay(W, auY, n)
        chk = [(nm, 0, legs[nm]) for nm in SPEC] + [("營飆v1", r, run(W, 120, 10, True, "抽籤", r)) for r in CHK]
        for nm, r, (o, au) in chk:
            eq = np.asarray(o["equity"], float)
            row = SE[(SE["世界"] == wn) & (SE["變體"] == nm) & (SE["r"] == r)].iloc[0]
            bad["K1"] += sha(eq) != row["eq_sha"]
            HX, val, mv, buy = replay(W, au, n)
            hv = np.asarray(o["hold_val"], float)
            nz = hv > 0
            maxd["K2_hold_val相對差"] = max(maxd["K2_hold_val相對差"], float(np.max(np.abs(val[nz] / hv[nz] - 1))) if nz.any() else 0.0,
                                         float(np.max(np.abs(val[~nz]))) if (~nz).any() else 0.0)
            for sg in M.SEGS[wn]:
                x, y = W["segp"][sg]
                cmp("K2", np.mean([len(HX[d]) for d in range(x, y + 1)]), row[f"{sg}_持股"])
                fa = [len(HX[d] & HY[d]) / len(HX[d]) for d in range(x, y + 1) if HX[d]]
                cmp("K2", np.mean(fa), row[f"{sg}_重疊a"])
                oc = []
                for d in range(x, y + 1):
                    s_ = 0.0
                    for s in HX[d] & HY[d]:
                        s_ += min(mv[d][s] / eq[d], mvY[d][s] / eY[d])
                    oc.append(s_)
                cmp("K2", np.mean(oc), row[f"{sg}_重疊c"])
                cmp("K2", 1 - np.mean([val[d] / eq[d] for d in range(x, y + 1)]), row[f"{sg}_現金"])
                cmp("K2", buy[x:y + 1].sum() / np.mean(eq[x:y + 1]) / ((y - x + 1) / 245.0), row[f"{sg}_換手每年"])
            if (nm in ("營飆v1", "M4") and r == 0) or nm == "營量v1":
                for sg in M.SEGS[wn]:
                    x, y = W["segp"][sg]; d = (x + y) // 2
                    K["抽樣持倉"].append({"世界": wn, "變體": nm, "r": r, "日": str(W["cal"][d].date()), "持股": sorted(HX[d]),
                                       "也在營量": sorted(HX[d] & HY[d]), "持股市值÷權益": float(val[d] / eq[d])})
            if nm != "營飆v1":
                continue
            # ── K3 各半·年調（自寫迴圈）──
            w0, w1 = W["w0"], W["w1"]; cal = W["cal"]
            V = np.full(n, np.nan); ve, vb = 0.5, 0.5; V[w0] = 1.0; cost = 0.0
            for t in range(w0 + 1, w1 + 1):
                ve *= eq[t] / eq[t - 1]; vb *= eY[t] / eY[t - 1]; v = ve + vb
                if cal[t].year != cal[t - 1].year:
                    c_ = abs(0.5 * v - ve) * 0.00585; cost += c_; v -= c_; ve = vb = 0.5 * v
                V[t] = v
            rA = SE[(SE["世界"] == wn) & (SE["變體"] == "各半·年調") & (SE["r"] == r)].iloc[0]
            rD = SE[(SE["世界"] == wn) & (SE["變體"] == "各半·日調") & (SE["r"] == r)].iloc[0]
            if wn == "主":
                cmp("K3", cost, rA["窗_cost_sum"])
            end = min(o["end"], oY["end"])
            eb = np.ones(n)
            for t in range(1, n):
                rr = 0.5 * (eq[t] / eq[t - 1] - 1) + 0.5 * (eY[t] / eY[t - 1] - 1) if t < end else 0.0
                eb[t] = eb[t - 1] * (1 + rr)
            for sg in M.SEGS[wn]:
                x, y = W["segp"][sg]
                c1, m1 = ann(V[x:y + 1]); cmp("K3", c1, rA[f"{sg}_年化"]); cmp("K3", m1, rA[f"{sg}_回落"])
                c2, m2 = ann(eb[x:y + 1]); cmp("K3", c2, rD[f"{sg}_年化"]); cmp("K3", m2, rD[f"{sg}_回落"])
                u = np.mean([len(HX[d] | HY[d]) for d in range(x, y + 1)])
                cmp("K3", u, rA[f"{sg}_持股"]); cmp("K3", u, rD[f"{sg}_持股"])
        log(f"[{wn}] 查完 {bad}｜{maxd}")
    bad["K2"] = int(maxd["K2"] > 1e-9 or maxd["K2_hold_val相對差"] > 1e-9)
    bad["K3"] = int(maxd["K3"] > 1e-9)
    # ── K4 cells ──
    CE = pd.DataFrame(SUM["表"]); k4 = 0
    for _, c in CE.iterrows():
        if c["變體"] == "0050":
            continue
        g = SE[(SE["世界"] == c["世界"]) & (SE["變體"] == c["變體"])]
        cg, mg = float(g[f"{c['段']}_年化"].median()), float(g[f"{c['段']}_回落"].median())
        b = SUM["0050"][c["世界"]][c["段"]]
        lab = "合格" if (cg > b["cagr"] and cg / abs(mg) >= b["cagr"] / abs(b["mdd"])) else ("另列" if cg > b["cagr"] else "不合格")
        k4 += (repr(cg) != repr(float(c["年化"]))) + (repr(mg) != repr(float(c["回落"]))) + (lab != c["對0050"])
        k4 += int(len(g) != (M.NSEED if c["變體"] in ("營飆v1", "各半·年調", "各半·日調") else 1))
    bad["K4"] = int(k4)
    K["不同"] = bad; K["最大差"] = maxd; K["查核種子"] = list(CHK); K["主程式閘"] = SUM["閘"]; K["完成（台北）"] = M.YV.now_tpe()
    json.dump(K, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 不同 {bad}｜最大差 {maxd}")
    log("✅ 全過" if all(v == 0 for v in bad.values()) else "⛔ 有不同")


if __name__ == "__main__":
    main()
