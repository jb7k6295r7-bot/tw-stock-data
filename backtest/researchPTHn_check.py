# -*- coding: utf-8 -*-
"""PTH 組合層「檔數 × 報酬分佈」描述【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsPTHn/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHn_check

C1 每個 N（主、滑價）：只用 trades_<世界>_N<n>[s] 表（買進日、金額、市值基準價、R用、賣出日）＋ 0050 開收盤 ＋ 快取收盤，自寫 N 槽迴圈重建淨值 ⇒ 對 eq npz；
   並驗 金額 ＝ min(前一日淨值 ÷ N, 0050 可撥)、持股 ≤ N、入帳 ＝ 金額×(1＋R用−0.585%)。
C2 由高往下：每個買進日，買到的 PTH ≥ 同日沒買到、未持有、非當日賣出的候選；有空槽且 0050 有餘卻留下候選 ＝ 0。
C3 N＝10 ＝ resultsPTHpf 10 檔版：npz 五陣列逐位元、交易檔全文逐字、隨機 200 次全文逐字。
C4 段指標：自寫年化與最大回落、0050 同窗、標籤字面另寫 ⇒ 對 PTHn.json 每一列（含主判、0050）。
C5 隨機：每個 N 重跑第 0、137 次（事件自讀、researchPTHpf.rand_job）⇒ 與 random 檔逐欄相同。
C6 單筆分布：由交易檔自算（依買進日歸段、已出場、R用−0.585%）⇒ 對 trade_dist。
C7 策略鎖 25 支相符；git 工作樹：本件只新增檔。
"""
from __future__ import annotations

import gzip
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTHpf_check as PC              # noqa: E402  rd、seg_metrics、lab、ev_light
from backtest import researchTurtleS2PF as TS               # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTHn"
SRC = M.OUT
NLIST = (5, 10, 15, 20, 30, 50)
COST = 0.00585; BUY = 0.001425; SELL = 0.002425


def rebuild(W, df, N, Bc, Bo):
    n0 = W["n0"]; CM = W["CM"]; ix = W["ix"]; dpos = {d: i for i, d in enumerate(W["dates"])}
    t_ = df["買進日"].map(dpos).to_numpy(); j_ = df["sid"].map(ix).to_numpy(); s_ = np.array([dpos[d] if d else -1 for d in df["賣出日"]])
    amt = df["金額"].to_numpy(float); ep = df["市值基準價"].to_numpy(float); R = df["R用"].to_numpy(float); proc = df["入帳"].to_numpy(float)
    by = {}
    for q, t in enumerate(t_):
        by.setdefault(int(t), []).append(q)
    units = 1.0 / Bc[0]; pend = 0.0; openp = []; eq = np.zeros(n0); nh = np.zeros(n0, int)
    bad = {"金額≠min(槽,可撥)": 0, "持股>N": 0, "入帳式": 0}
    for t in range(n0):
        if pend > 0:
            units += pend * (1 - BUY) / Bo[t]; pend = 0.0
        still = []
        for q in openp:
            if 0 <= s_[q] <= t:
                pr = amt[q] * (1 + R[q] - COST)
                if abs(pr - proc[q]) > 1e-12 * abs(pr):
                    bad["入帳式"] += 1
                pend += pr
            else:
                still.append(q)
        openp = still
        for q in by.get(t, []):
            slot = (eq[t - 1] if t > 0 else 1.0) / N; avail = units * Bo[t] * (1 - SELL)
            if abs(amt[q] - min(slot, avail)) > 1e-12 * max(amt[q], 1.0):
                bad["金額≠min(槽,可撥)"] += 1
            units -= amt[q] / ((1 - SELL) * Bo[t]); openp.append(q)
        still = []
        for q in openp:
            if s_[q] == t and t_[q] == t:
                pend += amt[q] * (1 + R[q] - COST)
            else:
                still.append(q)
        openp = still
        if len(openp) > N:
            bad["持股>N"] += 1
        nh[t] = len(openp)
        eq[t] = units * Bc[t] + pend + sum(amt[q] * CM[j_[q], t] / ep[q] for q in openp)
    return eq, nh, bad


def topdown(W, df, evd, N, U):
    dpos = {d: i for i, d in enumerate(W["dates"])}
    tb = df["買進日"].map(dpos).to_numpy(); ts = np.array([dpos[x] if x else W["n0"] + 1 for x in df["賣出日"]])
    viol = 0; nday = 0
    sid = df["sid"].to_numpy()
    for t, g in df.groupby(tb):
        nday += 1
        held = set(sid[(tb < t) & (ts > t)]); soldtoday = set(sid[(tb < t) & (ts == t)])
        cand = evd[(evd["t"] == t) & ~evd["sid"].isin(held | soldtoday | set(g["sid"]))]
        nheld = int(((tb < t) & (ts > t)).sum()) + len(g)
        if len(cand) and g["PTH"].min() < cand["PTH"].max() - 1e-15:
            viol += 1
        if len(cand) and nheld < N and U[t] > 1e-9:
            viol += 1
    return nday, viol


def dist(df, W, x, y):
    dpos = {d: i for i, d in enumerate(W["dates"])}
    tb = df["買進日"].map(dpos).to_numpy()
    m = (tb >= x) & (tb <= y) & (df["賣出日"] != "").to_numpy()
    v = (df["R用"].to_numpy(float) - COST)[m]; a_ = df["金額"].to_numpy(float)[m]
    k = max(1, math.ceil(0.1 * len(v))); top = np.argsort(-v, kind="stable")[:k]
    return {"筆數": len(v), "中位": float(np.median(v)), "平均": float(v.mean()), "勝率": float((v > 0).mean()), "p10": float(np.quantile(v, .1)),
            "p90": float(np.quantile(v, .9)), "前10%貢獻占比(等權)": float(v[top].sum() / v.sum()),
            "前10%貢獻占比(金額加權)": float((a_ * v)[top].sum() / (a_ * v).sum())}


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    T0 = time.time(); J = {"時間": M.now_tpe()}; ok = True
    PJ = json.load(open(os.path.join(OUT, "PTHn.json"), encoding="utf-8"))
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        Z = np.load(os.path.join(OUT, f"eq_{wn}.npz")); Z0 = np.load(os.path.join(SRC, f"eq_{wn}.npz"))
        Bc, Bo = Z0["Bc"], Z0["Bo"]
        ok &= np.array_equal(Z["Bc"], Bc) and np.array_equal(Z["Bo"], Bo)
        dpos = {d: i for i, d in enumerate(W["dates"])}
        ev = pd.read_csv(os.path.join(M.EVD, f"trades_{wn}_跳月.csv.gz"), dtype={"sid": str}, keep_default_na=False, float_precision="round_trip")
        evd = ev.assign(t=ev["進場日"].map(dpos))
        # C1、C2
        for N in NLIST:
            for sx in ("", "s"):
                df = PC.rd(os.path.join(OUT, f"trades_{wn}_N{N}{sx}.csv.gz"))
                eq, nh, bad = rebuild(W, df, N, Bc, Bo)
                d = float(np.max(np.abs(eq / Z[f"N{N}{sx}_eq"] - 1))); dn = int(np.sum(nh != Z[f"N{N}{sx}_nh"]))
                c = {"逐日淨值最大相對差": d, "持股筆數不同日": dn, **bad, "買進筆": int(len(df))}
                if not sx:
                    nday, viol = topdown(W, df, evd, N, Z[f"N{N}_u"])
                    c.update({"買進日": nday, "由高往下違反日": viol}); ok &= viol == 0
                J[f"C1C2_{wn}_N{N}{sx}"] = c; log(f"[C1C2 {wn} N{N}{sx}] {c}")
                ok &= d <= 1e-9 and dn == 0 and not any(bad.values())
        # C3
        c3 = {}
        for k in ("eq", "hv", "u", "pend", "nh"):
            c3[k] = bool(np.array_equal(Z[f"N10_{k}"], Z0[f"S10_{k}"]))
        with gzip.open(os.path.join(OUT, f"trades_{wn}_N10.csv.gz"), "rb") as f1, gzip.open(os.path.join(SRC, f"trades_{wn}_S10.csv.gz"), "rb") as f2:
            c3["交易檔全文"] = f1.read() == f2.read()
        RDF = pd.read_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), float_precision="round_trip")
        with gzip.open(os.path.join(SRC, f"random_{wn}.csv.gz"), "rt", encoding="utf-8") as fh:
            orig = fh.read()
        with gzip.open(os.path.join(OUT, f"random_{wn}.csv.gz"), "rt", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        hdr = lines[0].split(","); iN = hdr.index("N")
        mine = [",".join(c for k, c in enumerate(l.split(",")) if k != iN) for l in lines if l.split(",")[iN] == "10"]
        c3["隨機200次全文"] = "\n".join([orig.splitlines()[0]] + mine) == "\n".join(orig.splitlines())
        J[f"C3_{wn}"] = c3; log(f"[C3 {wn}] {c3}"); ok &= all(c3.values())
        # C4
        bad4 = []; nrow = 0
        for r in [z for z in PJ["表"] if z["世界"] == wn]:
            x = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[0]))); y = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[1])))
            if r["N"] == "0050":
                cg, md = PC.seg_metrics(Bc, x, y); want = (r["年化"], r["回落"])
                if abs(cg - want[0]) > 1e-9 or abs(md - want[1]) > 1e-9:
                    bad4.append(("0050", r["段"]))
                nrow += 1; continue
            key = ("M" if not r["滑價"] else "Mslip") if isinstance(r["N"], str) else f"N{r['N']}{'s' if r['滑價'] else ''}"
            E = Z0[f"{key}_eq"] if key.startswith("M") else Z[f"{key}_eq"]
            cg, md = PC.seg_metrics(E, x, y); bcg, bmd = PC.seg_metrics(Bc, x, y)
            if abs(cg - r["年化"]) > 1e-9 or abs(md - r["回落"]) > 1e-9 or abs(bcg - r["0050年化"]) > 1e-9 or PC.lab(cg, md, bcg, bmd) != r["標籤"]:
                bad4.append((key, r["段"], cg, r["年化"]))
            nrow += 1
        J[f"C4_{wn}"] = {"列": nrow, "不同": len(bad4), "例": [str(z) for z in bad4[:3]]}; log(f"[C4 {wn}] {J[f'C4_{wn}']}"); ok &= not bad4
        # C5
        evl = PC.ev_light(W, wn)
        o_ = np.lexsort((W["srank"][evl["j"]], evl["e"]))
        M._G[wn] = {"tr": M.slot_tr(evl, False, o_), "n0": W["n0"], "CM": W["CM"], "Bc": Bc, "Bo": Bo, "segp": W["segp"]}
        diff = 0
        for N in NLIST:
            TS.NS = N
            for i in (0, 137):
                r0 = M.rand_job((wn, i)); r1 = RDF[(RDF["N"] == N) & (RDF["i"] == i)].iloc[0]
                for k_, v_ in r0.items():
                    if k_ == "世界":
                        continue
                    if isinstance(v_, float) and abs(v_ - float(r1[k_])) > 1e-9 * max(1.0, abs(v_)):
                        diff += 1
                    elif not isinstance(v_, float) and int(v_) != int(r1[k_]):
                        diff += 1
        TS.NS = 10
        c5 = {"列": int(len(RDF)), "每N列": {int(k): int(v) for k, v in RDF["N"].value_counts().items()},
              "有限": bool(np.isfinite(RDF.select_dtypes("number").to_numpy()).all()), "重跑第0、137次不同欄": diff}
        J[f"C5_{wn}"] = c5; log(f"[C5 {wn}] {c5}"); ok &= diff == 0 and c5["有限"] and all(v == 200 for v in c5["每N列"].values())
        # C6
        bad6 = []
        for r in [z for z in PJ["單筆"] if z["世界"] == wn and z["臂"].startswith("N=")]:
            N = int(r["臂"][2:]); x, y = W["segp"][r["段"]]
            o = dist(PC.rd(os.path.join(OUT, f"trades_{wn}_N{N}.csv.gz")), W, x, y)
            for k_, v_ in o.items():
                if abs(v_ - r[k_]) > 1e-12 * max(1.0, abs(v_)):
                    bad6.append((r["臂"], r["段"], k_, v_, r[k_]))
        J[f"C6_{wn}"] = {"不同": len(bad6), "例": [str(z) for z in bad6[:3]]}; log(f"[C6 {wn}] {J[f'C6_{wn}']}"); ok &= not bad6
        del W, Z, Z0
    # C7
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    mod = [l for l in gs if not l.startswith("??")]
    new = [l for l in gs if l.startswith("??") and "PTHn" in l]
    c7 = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
          "既有追蹤檔有改動(工作樹，非本件)": mod, "本件新增": new}
    J["C7"] = c7; log(f"[C7] {c7}"); ok &= p.returncode == 0
    J["全部通過"] = bool(ok); J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全部通過 {ok}｜{J['耗時秒']}s")


if __name__ == "__main__":
    main()
