# -*- coding: utf-8 -*-
"""高10 同分種子敏感度【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 resultsPTH10seed/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10seed_check

C1 種子編碼：default_rng([20261021＋k·2³², j]) ＝ default_rng([20261021, k, j])（k＝1…200、j＝全部形成月）。
C2 rk 另一條路：直接讀事件檔（resultsPTH/events/trades_<世界>_跳月），依檔案列序逐月自生 rk（原種子 [20261023, j]），以 (代號, 形成月底) 對到
   load_events 的 ev ⇒ 與 ev["rk"] 逐位元相同；再對 k＝1、137、200 自生 [20261021, k, j] ⇒ researchPTHn.run_slot ⇒ 段年化／回落／平均持股、
   買進筆 與 seeds_<世界>.csv（%.10g）逐字相同。原種子路徑 eq ⇒ resultsPTHn eq npz N10_eq 逐位元。
C3 摘要：由 seeds_<世界>.csv、resultsPTHn/random_<世界>.csv.gz（N＝10）、PTHn_main.csv 0050 列 自算 中位／p5／p95／最小最大、原種子百分位、
   對 0050 兩項都勝比例 ⇒ 與 summary.csv（%.6g）逐字相同。
C4 同分：由事件檔自算每個進場日 PTH＝1 檔數 ⇒ 與 ties_<世界>.csv「PTH=1組」相同；買進格數 ＝ resultsPTHn trades_<世界>_N10 依買進日計數。
C5 策略鎖 25 支相符；git 工作樹：本件只新增 researchPTH10seed*.py 與 resultsPTH10seed/。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTHn as PN                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10seed"
SRC = "backtest/resultsPTHn"
BASE = 20261021; SEED0 = 20261023; NSEED = 200
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}


def g10(x):
    return "%.10g" % x


def g6(x):
    return "%.6g" % x


def rk_from_file(W, wn, seedf):
    fr = pd.read_csv(os.path.join(M.EVD, f"trades_{wn}_跳月.csv.gz"), dtype=str, keep_default_na=False)
    jm_of = {W["dates"][p]: j for j, p in enumerate(W["ME"])}
    jm = np.array([jm_of[d] for d in fr["形成月底"]], np.int64)
    rk = np.zeros(len(fr))
    for j in np.unique(jm):
        q = np.flatnonzero(jm == j)
        rk[q] = np.random.default_rng(seedf(int(j))).random(len(q))
    return {(s, f): v for s, f, v in zip(fr["sid"], fr["形成月底"], rk)}, fr


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    J = {"C1": None, "C2": {}, "C3": {}, "C4": {}, "C5": {}}
    bad = 0
    # C1
    for k in range(1, NSEED + 1):
        for j in range(0, 260, 13):
            if not np.array_equal(np.random.default_rng([BASE + (k << 32), j]).random(4), np.random.default_rng([BASE, k, j]).random(4)):
                raise SystemExit(f"⛔ C1 k={k} j={j}")
    J["C1"] = "k＝1…200 × j＝0..259 步 13：兩式逐位元相同"; log("✅ C1 " + J["C1"])
    PREF = pd.read_csv(os.path.join(SRC, "PTHn_main.csv"), dtype=str, encoding="utf-8-sig")
    SUMF = pd.read_csv(os.path.join(OUT, "summary.csv"), dtype=str, encoding="utf-8-sig", keep_default_na=False)
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        RES = {}
        with Pool(4) as pool:
            for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
                if r is not None:
                    RES[sid] = r
        ev0, _ = M.load_events(W, wn, "跳月", RES)
        del RES
        key = list(zip(ev0["sid"], ev0["form"]))
        mp0, fr = rk_from_file(W, wn, lambda j: [SEED0, j])
        rk0 = np.array([mp0[k_] for k_ in key])
        ok = np.array_equal(rk0, ev0["rk"]); bad += not ok
        J["C2"][f"{wn}|原種子 rk 自生 vs load_events"] = "逐位元相同" if ok else "⛔ 不同"
        S0 = PN.run_slot(dict(ev0, rk=rk0), W, 10, False)
        Z = np.load(os.path.join(SRC, f"eq_{wn}.npz"))
        ok = np.array_equal(S0["eq"], Z["N10_eq"]); bad += not ok
        J["C2"][f"{wn}|原種子（自生 rk）eq vs resultsPTHn N10_eq"] = "逐位元相同" if ok else "⛔ 不同"
        SD = pd.read_csv(os.path.join(OUT, f"seeds_{wn}.csv"), encoding="utf-8-sig")
        SDs = pd.read_csv(os.path.join(OUT, f"seeds_{wn}.csv"), encoding="utf-8-sig", dtype=str)
        for k in (1, 137, 200):
            mp, _ = rk_from_file(W, wn, lambda j, k=k: [BASE, k, j])
            S = PN.run_slot(dict(ev0, rk=np.array([mp[k_] for k_ in key])), W, 10, False)
            ref = SDs[SDs["k"] == str(k)].iloc[0]
            got = {"買進筆": str(len(S["buys"]))}
            for sg in SEGS[wn]:
                x, y = W["segp"][sg]
                c_, m_, _ = RR.win_metrics(S["eq"], 0, W["n0"], x, y)
                got[f"{sg}_年化"] = g10(float(c_)); got[f"{sg}_回落"] = g10(float(m_)); got[f"{sg}_平均持股"] = g10(float(np.mean(S["nh"][x:y + 1])))
            diff = [c for c in got if got[c] != ref[c]]
            bad += bool(diff)
            J["C2"][f"{wn}|k={k} 自生 rk 重跑 vs seeds 檔"] = "逐字相同" if not diff else f"⛔ 不同 {diff}"
        # C3
        RD = pd.read_csv(os.path.join(SRC, f"random_{wn}.csv.gz")); RD = RD[RD["N"] == 10]
        D = SD[SD["k"] > 0]; r0 = SD[SD["k"] == 0].iloc[0]
        for sg in SEGS[wn]:
            b = PREF[(PREF["世界"] == wn) & (PREF["N"] == "0050") & (PREF["段"] == sg)].iloc[0]
            x, y = W["segp"][sg]
            bb = RR.bench_row(W["cal"], W["bench"], x, y + 1)
            bc, bm = float(bb["cagr"]), float(bb["mdd"]); br = bc / abs(bm)
            if g6(bc) != b["年化"] or g6(bm) != b["回落"]:
                bad += 1; J["C3"][f"{wn}|{sg}|0050 vs PTHn_main"] = "⛔ 不同"
            for src, X in (("同分換種子", D), ("前30%完全隨機", RD)):
                c = X[f"{sg}_年化"].to_numpy(float); m = X[f"{sg}_回落"].to_numpy(float); r = c / np.abs(m)
                ref = SUMF[(SUMF["世界"] == wn) & (SUMF["段"] == sg) & (SUMF["來源"] == src)].iloc[0]
                got = {}
                for nm, v in (("年化", c), ("回落", m), ("比值", r)):
                    got[f"{nm}_中位"] = np.median(v); got[f"{nm}_p5"] = np.quantile(v, .05); got[f"{nm}_p95"] = np.quantile(v, .95)
                    got[f"{nm}_最小"] = v.min(); got[f"{nm}_最大"] = v.max()
                    if src == "同分換種子":
                        o = float(r0[f"{sg}_{nm}"]) if nm != "比值" else float(r0[f"{sg}_年化"]) / abs(float(r0[f"{sg}_回落"]))
                        got[f"{nm}_原種子百分位(≤)"] = np.mean(v <= o)
                got["年化勝0050"] = np.mean(c > bc); got["比值勝0050"] = np.mean(r > br)
                diff = [k_ for k_, v in got.items() if g6(float(v)) != ref[k_]]
                both = np.mean((c > bc) & (r >= br))
                if g6(both) != ref["對0050兩項都勝(合格:年化>且比值≥)"]:
                    diff.append("兩項都勝")
                if g6(bc) != ref["0050年化"] or g6(br) != ref["0050比值"]:
                    diff.append("0050 值")
                bad += bool(diff)
                J["C3"][f"{wn}|{sg}|{src}"] = "逐字相同（%d 欄）" % (len(got) + 2) if not diff else f"⛔ 不同 {diff}"
        # C4
        T = pd.read_csv(os.path.join(OUT, f"ties_{wn}.csv"), encoding="utf-8-sig", dtype={"進場日": str})
        n1 = fr[fr["PTH"].astype(float) == 1.0].groupby("進場日").size()
        mine = T.set_index("進場日")["PTH=1組"]
        ok1 = all(int(n1.get(d, 0)) == int(v) for d, v in mine.items())
        tr = pd.read_csv(os.path.join(SRC, f"trades_{wn}_N10.csv.gz"), dtype=str).groupby("買進日").size()
        ok2 = all(int(tr.get(d, 0)) == int(v) for d, v in T.set_index("進場日")["買進格數"].items()) and int(tr.sum()) == int(T["買進格數"].sum())
        bad += (not ok1) + (not ok2)
        J["C4"][wn] = {"PTH=1組": "相同" if ok1 else "⛔ 不同", "買進格數": "相同" if ok2 else "⛔ 不同"}
        log(f"[{wn}] C2 {J['C2']}｜C4 {J['C4'][wn]}")
        del W, ev0
    # C5
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    J["C5"]["strategy_lock"] = (p.stdout.strip().splitlines() or [p.stderr.strip()[-200:]])[-1]; J["C5"]["rc"] = p.returncode
    bad += p.returncode != 0
    J["C3"] = J["C3"]; J["不符"] = int(bad)
    log(f"[C3] {json.dumps(J['C3'], ensure_ascii=False)}")
    log(f"[C5] {J['C5']}｜不符 {bad}")
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    if bad:
        raise SystemExit(f"⛔ 對帳不符 {bad}")


if __name__ == "__main__":
    main()
