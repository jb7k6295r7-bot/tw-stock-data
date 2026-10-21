# -*- coding: utf-8 -*-
"""researchBigRun5 對帳——回測線計算子代理。⛔ 不檢定。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun5_check [--dry]
 K1 逐段表的 6 欄與 乙_全表（本益比、5 年位置、ROE、合約負債、千張大戶）／researchBigRun4 A 新欄（營業利益率）逐格相同；組別由 對照D 重判。
 K2 近 4 季 EPS：抽 150 格由 fin_hist 原檔另寫解析（eps_ytd 差分）重算；產業中位抽 100 格由面板另算。
 K3 產業.csv、族群.csv、產業相對.csv、虧損.csv、本益比有值率.csv 由逐段表 pandas groupby 另算，逐格比。
 K4 策略鎖 --check；git status。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
SHA = "eeb5af5f8feca83d0702fa0423a0c58cdb77900d"
WORK = os.path.expanduser("~/bgrwork")
PTS = ("高點前6月", "高點")
FE = ["本益比", "本益比5年位置", "ROE", "營業利益率", "合約負債年增", "集保千張大戶比12月變化"]
LOG = []; RES = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def same(a, b, tol=1e-9):
    a = np.asarray(a, float); b = np.asarray(b, float)
    return len(a) == len(b) and np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], rtol=tol, atol=tol)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    tag = "dry" if a.dry else "full"; OD = os.path.join(WORK, "dry5") if a.dry else "backtest/resultsBigRun5"
    SRC3 = os.path.join(WORK, "dry3") if a.dry else "backtest/resultsBigRun3"; SRC4 = os.path.join(WORK, "dry4") if a.dry else "backtest/resultsBigRun4"
    rng = np.random.default_rng(20261026)
    S = pd.read_csv(os.path.join(OD, "逐段.csv.gz"), dtype={"代號": str}); Y = pd.read_csv(os.path.join(SRC3, "乙_全表.csv.gz"), dtype={"代號": str})
    YA = pd.read_csv(os.path.join(SRC4, "A", "乙_新舊欄.csv.gz"), dtype={"代號": str})
    PN = pickle.load(open(os.path.join(WORK, f"bgr3_panel_{tag}.pkl"), "rb")); B4 = pickle.load(open(os.path.join(WORK, f"bgr4_{tag}.pkl"), "rb"))
    SIDS = PN["SIDS"]; META = PN["META"]; INDM = PN["INDM"]; P = PN["P"]; K = len(PN["MEp"])
    # K1
    ok1 = []
    for pt in PTS:
        for f in FE:
            src = YA[f"{f}@{pt}(新)"] if f == "營業利益率" else Y[f"{f}@{pt}"]
            ok1.append(same(S[f"{f}@{pt}"], src))
    grp = Y["對照D"].map({"崩": "D崩", "未崩": "乙非D"}).fillna("不進兩組")
    ok1.append(bool((grp.values == S["組"].values).all()))
    RES["K1"] = {"欄": len(ok1), "相同": int(sum(ok1))}; log(f"K1 欄值與來源相同 {sum(ok1)}/{len(ok1)}")
    # K2
    eps = {}
    for f in sorted(glob.glob(os.path.join(WORK, f"mainE_{SHA[:12]}", "data", "mops", "fin_hist", "*.csv"))):
        per = os.path.basename(f)[:6]; qk = int(per[:4]) * 4 + int(per[5]) - 1
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "eps_ytd"])
        for s, v in zip(x["stock_id"], x["eps_ytd"]):
            try:
                eps[(s, qk)] = float(v)
            except (TypeError, ValueError):
                eps[(s, qk)] = np.nan

    def sq(s, qk):
        v = eps.get((s, qk), np.nan)
        if qk % 4 == 0 or not np.isfinite(v):
            return v
        pv = eps.get((s, qk - 1), np.nan)
        return v - pv if np.isfinite(pv) else np.nan
    ok2 = n2 = 0
    for j in rng.choice(len(Y), min(150, len(Y)), replace=False):
        r = Y.iloc[j]; i = int(r["_i"]); pt = PTS[int(rng.integers(2))]; k = int(r[f"_k{pt}"])
        mine = np.nan
        if 0 <= k < K and META["fs_qk"][i, k] >= 0:
            qk = int(META["fs_qk"][i, k]); q = [sq(SIDS[i], x) for x in range(qk - 3, qk + 1)]
            mine = float(sum(q)) if np.isfinite(q).all() else np.nan
        n2 += 1; ok2 += int(same([mine], [S.iloc[j][f"近4季EPS@{pt}"]], 1e-9))
    ok2m = n2m = 0
    for j in rng.choice(len(S), min(100, len(S)), replace=False):
        r = S.iloc[j]; pt = PTS[int(rng.integers(2))]; ind = r[f"月底產業@{pt}"]; k = int(Y.iloc[j][f"_k{pt}"])
        if not isinstance(ind, str) or not ind:
            continue
        mem = [i for i in range(len(SIDS)) if INDM[i, k] == ind]
        for f, arr in (("本益比", P["本益比"]), ("ROE", P["ROE"]), ("營業利益率", B4["OPM"]["營業利益率"])):
            v = pd.Series(arr[mem, k].astype(float)).dropna()
            n2m += 1; ok2m += int(same([v.median() if len(v) else np.nan], [r[f"{f}產業中位@{pt}"]], 1e-9))
    RES["K2"] = {"EPS抽": n2, "EPS相符": ok2, "產業中位抽": n2m, "產業中位相符": ok2m}; log(f"K2 EPS {ok2}/{n2}；產業中位 {ok2m}/{n2m}")
    # K3
    IND = pd.read_csv(os.path.join(OD, "產業.csv")); ok3 = n3 = 0
    S["_p"] = np.where(pd.to_datetime(S["起點"]).dt.year <= 2014, "2005～2014", "2015～")
    parts = {"全部": S, "全部(2005～2014起點)": S[S["_p"] == "2005～2014"], "全部(2015起起點)": S[S["_p"] == "2015～"]}
    for g, d in S.groupby("產業(併)"):
        parts[g] = d
    for _, r in IND.iterrows():
        d = parts[r["分組"]]
        n3 += 1; ok3 += int(len(d) == r["段數"] and (d["組"] == "D崩").sum() == r["崩"] and (d["組"] == "乙非D").sum() == r["未崩"])
        for pt in PTS:
            for f in FE:
                for gg in ("D崩", "乙非D"):
                    v = d.loc[d["組"] == gg, f"{f}@{pt}"].dropna()
                    n3 += 1; ok3 += int(len(v) == r[f"{f}@{pt}_{gg}_n"] and same([v.median() if len(v) else np.nan], [r[f"{f}@{pt}_{gg}_中位"]]))
    GRP = pd.read_csv(os.path.join(OD, "族群.csv"))
    for _, r in GRP.iterrows():
        d = S[S["族群(切0.7)"] == int(r["分組"][1:])]
        n3 += 1; ok3 += int(len(d) == r["段數"] and (d["組"] == "D崩").sum() == r["崩"])
        for f in FE:
            v = d.loc[d["組"] == "D崩", f"{f}@高點前6月"].dropna()
            n3 += 1; ok3 += int(same([v.median() if len(v) else np.nan], [r[f"{f}@高點前6月_D崩_中位"]]))
    REL = pd.read_csv(os.path.join(OD, "產業相對.csv"))
    pp = {"全期": S, "2005～2014": S[S["_p"] == "2005～2014"], "2015～": S[S["_p"] == "2015～"]}
    for _, r in REL.iterrows():
        d = pp[r["起點期"]]
        for gg in ("D崩", "乙非D"):
            v = d.loc[d["組"] == gg, f"{r['欄']}@{r['時點']}"].dropna()
            n3 += 1; ok3 += int(len(v) == r[f"{gg}_n"] and same([v.median() if len(v) else np.nan, v.quantile(0.25) if len(v) else np.nan],
                                                              [r[f"{gg}_中位"], r[f"{gg}_p25"]]))
    LO = pd.read_csv(os.path.join(OD, "虧損.csv")); PE = pd.read_csv(os.path.join(OD, "本益比有值率.csv"))
    for _, r in LO.iterrows():
        d = pp[r["起點期"]]; d = d[d["組"] == r["組"]]; v = d[f"虧損@{r['時點']}"].dropna()
        n3 += 1; ok3 += int(len(v) == r["近4季EPS有值"] and same([v.mean() if len(v) else np.nan], [r["虧損比例(EPS<0÷EPS有值)"]]))
    for _, r in PE.iterrows():
        d = pp[r["起點期"]]; d = d[d["組"] == r["組"]]; pe = d[f"本益比@{r['時點']}"]
        n3 += 1; ok3 += int(pe.notna().sum() == r["本益比有值"])
    RES["K3"] = {"格": n3, "相符": ok3}; log(f"K3 彙總表重算 {ok3}/{n3}")
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    RES["K4"] = {"策略鎖": (lk.stdout + lk.stderr).strip().splitlines()[-1:], "已追蹤檔改動": [x for x in st if not x.startswith("??")],
                 "本件新增": [x for x in st if "BigRun5" in x]}
    log(f"K4 策略鎖 {RES['K4']['策略鎖']}；已追蹤檔改動 {len(RES['K4']['已追蹤檔改動'])}；新增 {RES['K4']['本件新增']}")
    json.dump(RES, open(os.path.join(OD, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OD, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
