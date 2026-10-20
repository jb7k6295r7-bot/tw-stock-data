# -*- coding: utf-8 -*-
"""PTH 組合層「N 格補空位 × 持有月數」描述【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsPTHhold/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHhold_check

C1 每個 (持有月, N)（主、滑價）：只用交易檔（買進日、金額、市值基準價、R用、賣出日）＋ 0050 開收盤 ＋ 快取收盤，
   以 researchPTHn_check.rebuild 自寫 N 槽迴圈重建淨值 ⇒ 對 eq npz；並驗 金額 ＝ min(前一日淨值 ÷ N, 0050 可撥)、持股 ≤ N、入帳式。
C2 由高往下（researchPTHn_check.topdown）：候選 ＝ 該持有月數的事件檔（自讀）；違反日 ＝ 0。
C3 抱 6 月 ＝ resultsPTHn：npz 五陣列逐位元、交易檔全文逐字、隨機 N＝10、15 各 200 次全文逐字。
C4 段指標：自寫年化與最大回落、0050 同窗、標籤字面另寫 ⇒ 對 PTHhold.json 每一列（含 0050）。
C5 隨機：每個 (持有月, N) 重跑第 0、137 次（事件自讀，⛔ 不呼叫 load_events；researchPTHpf.rand_job）⇒ 與 random 檔逐欄相同。
C6 單筆分布：由交易檔自算（researchPTHn_check.dist）⇒ 對 trade_dist。
C7 策略鎖 25 支相符；git 工作樹：本件只新增檔。
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTHpf_check as PC              # noqa: E402  rd、seg_metrics、lab
from backtest import researchPTHn_check as NC               # noqa: E402  rebuild、topdown、dist
from backtest import researchTurtleS2PF as TS               # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTHhold"
SRCN = "backtest/resultsPTHn"
HOLDS = {3: "跳月_3月", 6: "跳月"}
NLIST = (10, 15)


def ev_light_h(W, wn, h):
    """事件（持有 h 月）⇒ 隨機臂用陣列（自讀事件檔與快取開盤；researchPTHpf_check.ev_light 同式、只把格與到期表換成 h）。"""
    fr = pd.read_csv(os.path.join(M.EVD, f"trades_{wn}_{HOLDS[h]}.csv.gz"), dtype=str, keep_default_na=False)
    dpos = {d: i for i, d in enumerate(W["dates"])}; jm_of = {W["dates"][p]: j for j, p in enumerate(W["ME"])}
    tinv = {v: k for k, v in M.TYPN.items()}
    j = np.array([W["ix"][s] for s in fr["sid"]]); e = np.array([dpos[d] for d in fr["進場日"]])
    jm = np.array([jm_of[d] for d in fr["形成月底"]]); typ = np.array([tinv[x] for x in fr["出場種類"]])
    R = np.array([float(x) if x else np.nan for x in fr["R"]]); sd = np.array([dpos[x] if x else -1 for x in fr["出場日"]])
    X = W["XP"][(2, h)][jm]
    sale = np.where(np.isin(typ, (1, 2)), X, np.where(np.isin(typ, (3, 4)), sd, -1))
    P = np.asarray(W["O"], float)[j, e]
    return {"j": j, "e": e, "sale": sale, "P": P, "px": P * (1 + R), "R": R}


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    T0 = time.time(); J = {"時間": M.now_tpe()}; ok = True
    PJ = json.load(open(os.path.join(OUT, "PTHhold.json"), encoding="utf-8"))
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        Z = np.load(os.path.join(OUT, f"eq_{wn}.npz")); Zn = np.load(os.path.join(SRCN, f"eq_{wn}.npz"))
        Bc, Bo = Zn["Bc"], Zn["Bo"]
        ok &= bool(np.array_equal(Z["Bc"], Bc) and np.array_equal(Z["Bo"], Bo))
        dpos = {d: i for i, d in enumerate(W["dates"])}
        # C1、C2
        for h in HOLDS:
            ev = pd.read_csv(os.path.join(M.EVD, f"trades_{wn}_{HOLDS[h]}.csv.gz"), dtype={"sid": str}, keep_default_na=False, float_precision="round_trip")
            evd = ev.assign(t=ev["進場日"].map(dpos))
            for N in NLIST:
                for sx in ("", "s"):
                    key = f"H{h}_N{N}{sx}"
                    df = PC.rd(os.path.join(OUT, f"trades_{wn}_{key}.csv.gz"))
                    eq, nh, bad = NC.rebuild(W, df, N, Bc, Bo)
                    d = float(np.max(np.abs(eq / Z[f"{key}_eq"] - 1))); dn = int(np.sum(nh != Z[f"{key}_nh"]))
                    c = {"逐日淨值最大相對差": d, "持股筆數不同日": dn, **bad, "買進筆": int(len(df))}
                    if not sx:
                        nday, viol = NC.topdown(W, df, evd, N, Z[f"{key}_u"])
                        c.update({"買進日": nday, "由高往下違反日": viol}); ok &= viol == 0
                    J[f"C1C2_{wn}_{key}"] = c; log(f"[C1C2 {wn} {key}] {c}")
                    ok &= d <= 1e-9 and dn == 0 and not any(bad.values())
        # C3
        c3 = {}
        for N in NLIST:
            for sx in ("", "s"):
                for k in ("eq", "hv", "u", "pend", "nh"):
                    c3[f"N{N}{sx}_{k}"] = bool(np.array_equal(Z[f"H6_N{N}{sx}_{k}"], Zn[f"N{N}{sx}_{k}"]))
                with gzip.open(os.path.join(OUT, f"trades_{wn}_H6_N{N}{sx}.csv.gz"), "rb") as f1, \
                        gzip.open(os.path.join(SRCN, f"trades_{wn}_N{N}{sx}.csv.gz"), "rb") as f2:
                    c3[f"N{N}{sx}_交易檔全文"] = f1.read() == f2.read()
        with gzip.open(os.path.join(SRCN, f"random_{wn}.csv.gz"), "rt", encoding="utf-8") as fh:
            ol = fh.read().splitlines()
        with gzip.open(os.path.join(OUT, f"random_{wn}.csv.gz"), "rt", encoding="utf-8") as fh:
            ml = fh.read().splitlines()
        iN = ol[0].split(",").index("N"); iH = ml[0].split(",").index("持有月")
        want = [l for l in ol[1:] if int(l.split(",")[iN]) in NLIST]
        mine = [",".join(c for k, c in enumerate(l.split(",")) if k != iH) for l in ml[1:] if l.split(",")[iH] == "6"]
        hdr = ",".join(c for k, c in enumerate(ml[0].split(",")) if k != iH)
        c3["隨機N10、15各200次全文"] = hdr == ol[0] and mine == want
        J[f"C3_{wn}"] = c3; log(f"[C3 {wn}] {c3}"); ok &= all(c3.values())
        # C4
        bad4 = []; nrow = 0
        for r in [z for z in PJ["表"] if z["世界"] == wn]:
            x = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[0]))); y = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[1])))
            if r["N"] == "0050":
                cg, md = PC.seg_metrics(Bc, x, y)
                if abs(cg - r["年化"]) > 1e-9 or abs(md - r["回落"]) > 1e-9:
                    bad4.append(("0050", r["段"]))
                nrow += 1; continue
            key = f"H{r['持有月']}_N{r['N']}{'s' if r['滑價'] else ''}"
            cg, md = PC.seg_metrics(Z[f"{key}_eq"], x, y); bcg, bmd = PC.seg_metrics(Bc, x, y)
            nh = Z[f"{key}_nh"][x:y + 1]
            if (abs(cg - r["年化"]) > 1e-9 or abs(md - r["回落"]) > 1e-9 or abs(bcg - r["0050年化"]) > 1e-9 or PC.lab(cg, md, bcg, bmd) != r["標籤"]
                    or abs((1 - nh.mean() / r["N"]) - r["空位率"]) > 1e-12):
                bad4.append((key, r["段"], cg, r["年化"]))
            nrow += 1
        J[f"C4_{wn}"] = {"列": nrow, "不同": len(bad4), "例": [str(z) for z in bad4[:3]]}; log(f"[C4 {wn}] {J[f'C4_{wn}']}"); ok &= not bad4
        # C5
        RDF = pd.read_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), float_precision="round_trip")
        diff = 0
        for h in HOLDS:
            evl = ev_light_h(W, wn, h)
            o_ = np.lexsort((W["srank"][evl["j"]], evl["e"]))
            M._G[wn] = {"tr": M.slot_tr(evl, False, o_), "n0": W["n0"], "CM": W["CM"], "Bc": Bc, "Bo": Bo, "segp": W["segp"]}
            for N in NLIST:
                TS.NS = N
                for i in (0, 137):
                    r0 = M.rand_job((wn, i)); r1 = RDF[(RDF["持有月"] == h) & (RDF["N"] == N) & (RDF["i"] == i)].iloc[0]
                    for k_, v_ in r0.items():
                        if k_ == "世界":
                            continue
                        if isinstance(v_, float) and abs(v_ - float(r1[k_])) > 1e-9 * max(1.0, abs(v_)):
                            diff += 1
                        elif not isinstance(v_, float) and int(v_) != int(r1[k_]):
                            diff += 1
        TS.NS = 10; M._G.pop(wn, None)
        c5 = {"列": int(len(RDF)), "每(持有月,N)列": {f"{a_}|{b_}": int(v) for (a_, b_), v in RDF.groupby(["持有月", "N"]).size().items()},
              "有限": bool(np.isfinite(RDF.select_dtypes("number").to_numpy()).all()), "重跑第0、137次不同欄": diff}
        J[f"C5_{wn}"] = c5; log(f"[C5 {wn}] {c5}"); ok &= diff == 0 and c5["有限"] and all(v == 200 for v in c5["每(持有月,N)列"].values())
        # C6
        bad6 = []
        for r in [z for z in PJ["單筆"] if z["世界"] == wn]:
            N = int(r["臂"][2:]); x, y = W["segp"][r["段"]]
            o = NC.dist(PC.rd(os.path.join(OUT, f"trades_{wn}_H{r['持有月']}_N{N}.csv.gz")), W, x, y)
            for k_, v_ in o.items():
                if abs(v_ - r[k_]) > 1e-12 * max(1.0, abs(v_)):
                    bad6.append((r["持有月"], r["臂"], r["段"], k_, v_, r[k_]))
        J[f"C6_{wn}"] = {"不同": len(bad6), "例": [str(z) for z in bad6[:3]]}; log(f"[C6 {wn}] {J[f'C6_{wn}']}"); ok &= not bad6
        del W, Z, Zn
    # C7
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    mod = [l for l in gs if not l.startswith("??")]
    new = [l for l in gs if l.startswith("??") and "PTHhold" in l]
    c7 = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
          "既有追蹤檔有改動(工作樹，非本件)": mod, "本件新增": new}
    J["C7"] = c7; log(f"[C7] {c7}"); ok &= p.returncode == 0
    J["全部通過"] = bool(ok); J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全部通過 {ok}｜{J['耗時秒']}s")


if __name__ == "__main__":
    main()
